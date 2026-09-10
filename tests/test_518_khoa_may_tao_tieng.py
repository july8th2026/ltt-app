r"""KHOÁ `may_tao_tieng` — và chốt thật nằm ở chỗ BỎ CUỘC, không ở cái khoá.

## Ca thật sinh ra tệp này

10/09/2026, cổng giọng `:8120` — `_Cong` (`voice_sidecar/engine.py:112`) là
semaphore **một suất, KHÔNG chờ**: hết chỗ thì ném 429 ngay.

    11:39-11:47  khong khoa  -> ASV mat mot canh `voice_synthesis`,
                                lo `ho-so-giong` mat 19/20 giong
    12:26-12:49  CO khoa     -> 11/11 va 11/11, khong mot 429 nao

Cùng đường ống, cùng cổng, cùng hai phiên, khác đúng **một** biến. (Số của phiên
`asv-v6`; lượt 11:39–11:47 thì cả hai bên cùng đo được.)

## 🔑 Vì sao không ai "tham lam", và vì sao semaphore không cứu được

`DangBanTam` mang `retry_after_s`, nên worker đưa job về `resource_wait` và
**lùi** — đo được: 20 s · 20 s · **167 s** · 20 s · 10 s. Trong quãng lùi cổng
**rảnh**, một vòng lặp chặt lấy được ngay; job kia quay lại thì cổng đầy.

⇒ **Một vòng lặp chặt luôn thắng một job biết lùi**, và càng lùi lâu càng thua.
Bên lịch sự thua **có hệ thống**.

⛔ **Semaphore ở tầng runtime không PHÂN XỬ được — nó chỉ TỪ CHỐI.** Nó không
biết ai đã chờ bao lâu, nên nó không thể công bằng. Chỉ một khoá ở tầng trên —
xin trước, không có thì **bỏ cuộc sạch** — mới biến *"ai nhanh tay"* thành
*"ai tới trước"*.

## ⛔ Và cái khoá KHÔNG phải phần khó

`CuaSoYen` hết giờ chờ thì **VẪN CHẠY** (docstring của chính nó nói thế). Đó là
mặc định **đúng** cho `cpu_nhieu` — chen chỉ làm **chậm**, và *"một cổng chất
lượng từ chối chạy vì bận là một cổng không ai dùng"*. Nhưng với tài nguyên
**một suất** thì chen làm **hỏng cả hai phía**, không phải làm chậm.

⇒ Bên gọi phải đọc `chay_khong_khoa` và **bỏ cuộc**. Thiếu chốt ấy thì khoá chỉ
là một dòng chữ đẹp: nó in cảnh báo rồi đâm vào người kia y như cũ.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile
import time

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))

import cua_so_yen as cy  # noqa: E402

TEN = "may_tao_tieng"


@pytest.fixture
def khoa_rieng(tmp_path, monkeypatch):
    """⛔ HAI đòn bẩy, không phải một — và đây là bài học của chính sáng nay.

    `cua_so_yen` lấy đường dẫn từ **hai** nguồn độc lập: hằng số `TEP_KHOA`
    (đọc lúc **import**) và `tempfile.gettempdir()` (đọc lúc **gọi**, cho tài
    nguyên có tên). Vá một cái thì bài kiểm vẫn **xanh** mà vẫn chạm khoá THẬT
    của máy — `dang_giu()` glob thư mục tạm thật.

    Đòn bẩy thư mục phải là `tempfile.tempdir`, **không** phải biến môi trường:
    `gettempdir()` cache sau lần gọi đầu.
    """
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(cy, "TEP_KHOA", tmp_path / "ltt_cua_so_yen.json")
    yield tmp_path


def _dat_khoa_cua_phien_khac(ten: str) -> pathlib.Path:
    """Khoá của một phiên KHÁC, pid còn sống (dùng pid của chính test).

    ⭐ HAI điều kiện, và thiếu cái nào cũng làm bài kiểm đo nhầm đường:

    - `pid` phải **còn sống** — `_treo()` coi pid chết là treo rồi đoạt khoá.
    - Tên trường phải đúng **`bat_dau_epoch`**. Lượt đầu tôi viết `bat_dau`,
      `_treo()` đọc ra `0`, tính tuổi khoá thành **496.950 giờ** và đoạt luôn.
      Bài kiểm khi ấy đo đường *đoạt-khoá-treo* chứ không đo đường *tranh chấp*
      — và nó **đỏ**, đúng như một phép kiểm tử tế phải làm với một fixture sai.
    """
    tep = cy._tep(ten)
    tep.write_text(json.dumps({
        "phien": "phien-khac", "pid": os.getpid(), "lenh": "gia lap",
        "tai_nguyen": ten, "bat_dau_epoch": time.time()}), encoding="utf-8")
    return tep


def test_khoa_rieng_KHONG_cham_khoa_that(khoa_rieng):
    """Chốt chính cái fixture — nếu nó rò thì mọi bài dưới đều nguy hiểm."""
    assert str(khoa_rieng) in str(cy._tep(TEN))
    assert str(khoa_rieng) in str(cy.TEP_KHOA)


def test_xin_duoc_khi_RANH(khoa_rieng):
    with cy.CuaSoYen("toi", "lenh", cho_toi_da_s=2.0,
                     tai_nguyen=(TEN,)) as k:
        assert not k.chay_khong_khoa, "may ranh ma van bao dang chen"


def test_HET_GIO_CHO_thi_bao_dang_chen_chu_KHONG_nem(khoa_rieng):
    """🔑 Mệnh đề nền: `CuaSoYen` **vẫn chạy** khi hết giờ chờ.

    Bài này chốt đúng cái hành vi mà bên gọi phải tự phòng. Nếu một bản vá sau
    làm `CuaSoYen` tự ném, bài này đỏ — và người sửa phải quay lại đọc vì sao
    `do_ho_so_giong` có nhánh bỏ cuộc riêng.
    """
    _dat_khoa_cua_phien_khac(TEN)
    t0 = time.time()
    with cy.CuaSoYen("toi", "lenh", cho_toi_da_s=1.0,
                     tai_nguyen=(TEN,)) as k:
        assert k.chay_khong_khoa, (
            "khoa dang bi phien khac giu ma `chay_khong_khoa` van False")
    assert time.time() - t0 >= 1.0, "khong he cho du `cho_toi_da_s`"


def test_do_ho_so_giong_BO_CUOC_bang_ma_75(khoa_rieng):
    """⛔ Chốt CƠ CHẾ trong mã nguồn, không chốt tính chất.

    Không gọi `main()` được ở đây: nó đòi `LTT_VOICE_SIDECAR_TOKEN` (cửa ấy
    chạy **trước** khoá, và thứ tự đó đúng — đừng giành khoá cả máy chỉ để phát
    hiện mình không có token). Nên bài này đọc AST.

    Một bài chỉ assert `CuaSoYen` cư xử đúng sẽ **vẫn xanh** nếu ai đó gỡ nhánh
    `return 75` — vì nó không đo `do_ho_so_giong`.
    """
    nguon = (GOC / "tools/do_ho_so_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)

    # ⛔ KHONG `assert "may_tao_tieng" in nguon`. Chuoi ay con nam trong CHU
    #    THICH, nen mot dot bien go no khoi `tai_nguyen=` van lam bai kiem
    #    XANH — do duoc 10/09 bang chinh phep dot bien. Phai doc AST.
    ten_khoa = [
        kw.value for n in ast.walk(cay)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "CuaSoYen"
        for kw in n.keywords if kw.arg == "tai_nguyen"]
    assert ten_khoa, "`CuaSoYen(...)` khong con nhan `tai_nguyen=`"
    hang = [x.value for t in ten_khoa for x in ast.walk(t)
            if isinstance(x, ast.Constant)]
    assert "may_tao_tieng" in hang, (
        f"`tai_nguyen=` phai chua 'may_tao_tieng', thay: {hang}")

    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    assert ham is not None

    # Tim `if <...>.chay_khong_khoa:` va doi trong than no co `return 75`.
    nhanh = [n for n in ast.walk(ham)
             if isinstance(n, ast.If)
             and any(isinstance(x, ast.Attribute) and x.attr == "chay_khong_khoa"
                     for x in ast.walk(n.test))]
    assert nhanh, "`main()` khong con doc `chay_khong_khoa`"

    ma = [x.value.value for n in nhanh for x in ast.walk(n)
          if isinstance(x, ast.Return) and isinstance(x.value, ast.Constant)]
    assert 75 in ma, (
        f"nhanh `chay_khong_khoa` phai `return 75` (bo cuoc sach), thay: {ma}. "
        f"Chen vao mot tai nguyen MOT SUAT lam hong CA HAI phia, khong phai "
        f"lam cham.")


def test_KHONG_lam_viec_gi_truoc_khi_bo_cuoc(khoa_rieng):
    """⭐ Bỏ cuộc mà đã sinh vài lượt rồi thì vẫn đã phá lượt của người kia.

    Chốt: nhánh `chay_khong_khoa` phải nằm **trước** vòng đo. Đo bằng vị trí
    dòng — thô, nhưng nó bắt đúng kiểu hỏng "dời chốt xuống dưới cho gọn".
    """
    nguon = (GOC / "tools/do_ho_so_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    dong_bo_cuoc = min(
        n.lineno for n in ast.walk(ham)
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
        and n.value.value == 75)
    dong_do = [n.lineno for n in ast.walk(ham)
               if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "_do_het"]
    assert dong_do, "`main()` khong con goi `_do_het`"
    assert dong_bo_cuoc < min(dong_do), (
        "nhanh bo cuoc phai nam TRUOC loi goi vong do")
