r"""
test_387 — chốt tĩnh `tools/check_ps_bien_trung_tham_so.py` bắt đúng thứ nó
sinh ra để bắt.

## Vì sao một chốt tĩnh cũng cần bánh cóc

Chốt này viết ra sau lần đầu bị dính: một trình bọc `.ps1` có tham số `-Ten` và
một biến cục bộ `$ten`, PowerShell **không phân biệt hoa thường**, nên giá trị
người dùng truyền vào bị xoá — và một giọng bị đặt tên `HF_HOME`.

⛔ Rồi nó **bỏ sót lần tái diễn thứ hai của chính con bug ấy**, và lần này hậu
   quả nặng hơn nhiều: `setup/nap_credit_tai_khoan_thu.ps1` có tham số `-So`
   (số credit nạp) và một bộ đếm biến môi trường `$so` tăng bằng `$so++`. Lệnh
   `-So 100` đi vào công cụ thành **70** — số biến đã nạp từ `app.env` — và
   công cụ ghi một **bút toán credit sai số** vào một cuốn sổ **append-only**,
   không lời cảnh báo nào.

Hai lỗ, mỗi lỗ một bài học:

  ① `_GAN` chỉ khớp `$x = ...`, bỏ qua `$x++` / `$x--` / `$x += ...`.
     **Một phép tăng cũng là một phép gán.**
  ② Nó chỉ soi trong **thân vòng lặp**. Nhưng `$so = 0` ở cấp ngoài đã xoá tham
     số rồi; vòng lặp chỉ là nơi giá trị rác được bồi thêm.

⭐ Và khi mở rộng thì phép miễn trừ cho mẫu hợp lệ (`if (-not $Repo) { $Repo =
   ... }`) phải đúng ngay, nếu không chốt sẽ báo nhầm và người ta sẽ tắt nó.
   Bản đầu của phép miễn ấy neo `^` trên một chuỗi đã nối nhiều dòng nên không
   bao giờ khớp — nó báo nhầm `cai_dich_vu_giong.ps1` ngay lượt chạy đầu.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "tools" / "check_ps_bien_trung_tham_so.py"


#: Giữ MÃI những `TextIOWrapper` mà module đo tạo ra. Xem `_nap()`.
_GIU: list = []
_MODULE = []


def _nap():
    """Nạp module đo mà không giết `sys.stdout` của pytest.

    🔴 Hai tầng, và tầng thứ hai không hiển nhiên chút nào.

       ① Module này — như mọi công cụ đo trong `tools/` — thay `sys.stdout`
          bằng `TextIOWrapper(sys.stdout.buffer, line_buffering=True)` ngay ở
          cấp module. Nên sau khi import, `sys.stdout` không còn là của pytest.
          Khôi phục tham chiếu là đủ để sửa việc ấy.

       ② **Nhưng `TextIOWrapper` NHẬN QUYỀN SỞ HỮU cái buffer nó bọc.** Khi
          wrapper bị thu gom rác, nó **đóng buffer** — tức đóng luôn stdout thật
          của tiến trình. Khôi phục tham chiếu KHÔNG cứu được: cái đã khôi phục
          trỏ tới một buffer sắp bị đóng bởi một đối tượng khác đang chờ chết.

    ⛔ Triệu chứng: pytest chạy hết mọi phép kiểm rồi vỡ ở `terminal.py` khi in
       dòng tổng kết — `ValueError: I/O operation on closed file` ở
       `pytest_sessionfinish`, tức **sau** khi mọi thứ đã xong. Dấu vết không
       nhắc gì tới module đang được kiểm, và nó trông y hệt một lỗi của pytest.

    ⇒ Nên phải GIỮ tham chiếu tới wrapper cho tới hết phiên, và nạp module đúng
      MỘT lần.
    """
    if _MODULE:
        return _MODULE[0]
    cu_out, cu_err = sys.stdout, sys.stderr
    try:
        sp = importlib.util.spec_from_file_location("check_ps_bien", TEP)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _MODULE.append(m)
        return m
    finally:
        # Giữ wrapper module vừa tạo, RỒI mới trả stdout về cho pytest.
        for o in (sys.stdout, sys.stderr):
            if o is not cu_out and o is not cu_err:
                _GIU.append(o)
        sys.stdout, sys.stderr = cu_out, cu_err


def _kiem(tmp_path, noi_dung: str) -> list:
    """Chấm một đoạn `.ps1` tổng hợp.

    ⛔ Tệp phải nằm TRONG kho: `kiem()` dựng thông điệp lỗi bằng
       `tep.relative_to(GOC)`, nên một đường dẫn ngoài kho ném `ValueError` —
       và nó ném ở chỗ **định dạng thông điệp**, tức chỉ ném khi CÓ lỗi để báo.
       Một khuôn thử đặt tệp ở `tmp_path` của pytest sẽ xanh ở mọi phép kiểm
       "không được báo nhầm" và đỏ ở mọi phép kiểm "phải bắt được" — đúng chiều
       khiến người đọc tưởng chốt đã hỏng.

    ⭐ `tmp/` của kho nằm trong `.gitignore`, nên rác sót lại nếu một lượt bị
       giết giữa chừng cũng không vào git — khác bài học của
       `vps_dieu_khoan.html`, nơi dấu tiêm rơi vào một tệp ĐƯỢC theo dõi và
       lượt gate sau đọc nó thành một thay đổi thật.
    """
    thu = GOC / "tmp" / "test387"
    thu.mkdir(parents=True, exist_ok=True)
    p = thu / (tmp_path.name + ".ps1")
    p.write_text(noi_dung, encoding="ascii", newline="\r\n")
    try:
        return _nap().kiem(p)
    finally:
        try:
            p.unlink()
        except OSError:
            pass


DAU = "param(\n    [string]$Root = 'C:\\LTTPlatform',\n    [int]$So = 0\n)\n"


def test_bat_phep_TANG_trong_vong_lap(tmp_path):
    """`$so++` — đúng dạng đã ghi một bút toán credit sai số."""
    loi = _kiem(tmp_path, DAU + "$so = 0\nforeach ($d in $x) {\n    $so++\n}\n")
    assert loi, "khong bat duoc `$so++` — `_GAN` co gom `++` khong?"


def test_bat_phep_GAN_o_CAP_NGOAI(tmp_path):
    """`$so = 0` ngoài mọi vòng lặp đã xoá tham số rồi.

    Vòng lặp chỉ là nơi giá trị rác được bồi thêm — nó không phải nguyên nhân,
    nên giới hạn phép soi vào thân vòng lặp là soi sai chỗ.
    """
    loi = _kiem(tmp_path, DAU + "$so = 0\nWrite-Host $so\n")
    assert loi, "khong bat duoc phep gan o cap ngoai"


def test_bat_cong_don(tmp_path):
    for phep in ("$so += 1", "$so -= 1", "$so--"):
        loi = _kiem(tmp_path, DAU + f"{phep}\n")
        assert loi, f"khong bat duoc `{phep}`"


def test_KHONG_bao_nham_mau_dien_mac_dinh(tmp_path):
    """`if (-not $Root) { $Root = ... }` là cách hợp lệ để bỏ trống một tham số.

    🔴 Một chốt tĩnh hay báo nhầm là một chốt tĩnh sẽ bị tắt, và khi nó bị tắt
       thì nó cũng không còn bắt được thứ nó bắt đúng. Phép miễn trừ này quan
       trọng ngang phép bắt.
    """
    loi = _kiem(tmp_path, DAU + "if (-not $Root) {\n    $Root = 'C:\\x'\n}\n")
    assert not loi, loi


def test_KHONG_bao_nham_khi_if_nam_o_giua_doan(tmp_path):
    """Phép miễn phải khớp cả khi `if` không đứng đầu đoạn nhìn lui.

    ⛔ Bản đầu neo `^` trên một chuỗi đã NỐI nhiều dòng, nên `^` chỉ khớp đầu
       chuỗi và phép miễn không bao giờ nổ. Nó báo nhầm ngay
       `setup/cai_dich_vu_giong.ps1:42` — một mẫu hoàn toàn hợp lệ.
    """
    ma = (DAU + "Write-Host 'a'\nWrite-Host 'b'\n"
          "if (-not $Root) { $Root = $env:X }\n")
    assert not _kiem(tmp_path, ma), _kiem(tmp_path, ma)


def test_khong_bat_phep_DOC(tmp_path):
    """Đọc `$So` thì không sao — chỉ ghi đè mới là lỗi."""
    assert not _kiem(tmp_path, DAU + "Write-Host \"$So\"\n$x = $So + 1\n")


def test_kho_that_sach(tmp_path):
    """Toàn kho phải sạch — đây là bánh cóc, không phải một phép đo."""
    m = _nap()
    loi = []
    for thu in m.THU_MUC:
        for p in (GOC / thu).rglob("*.ps1"):
            loi += m.kiem(p)
    assert not loi, "\n".join(loi)
