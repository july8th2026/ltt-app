"""`tools/gate.py` phải phủ MỌI thứ cần chạy trước khi báo xong.

Vì sao có file này: trước 2026-08-06, `python -m pytest` không chạy test
frontend, nên "full regression xanh" bỏ sót 77 test vitest và người chạy gate
phải nhớ gõ thêm ba lệnh. Thêm một frontend thứ tư mà quên khai ở đây là lặp lại
đúng lỗ hổng đó — nên để test canh, đừng để trí nhớ canh.
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _frontends_on_disk() -> set[str]:
    folder = ROOT / "frontend"
    return {item.name for item in folder.iterdir()
            if item.is_dir() and (item / "package.json").exists()}


def test_gate_lists_every_frontend_that_exists():
    from tools.gate import FRONTENDS

    on_disk = _frontends_on_disk()
    missing = on_disk - set(FRONTENDS)
    assert missing == set(), (
        f"frontend chưa khai trong tools/gate.py: {sorted(missing)}")
    stale = set(FRONTENDS) - on_disk
    assert stale == set(), f"gate khai frontend không còn tồn tại: {sorted(stale)}"


def test_gate_runs_the_scanners_and_pytest():
    """Bốn thứ này là cổng tối thiểu; thiếu bất kỳ cái nào thì gate nói dối."""
    from tools.gate import _steps

    names = {step.name for step in _steps(quick=False)}
    assert "secret scan" in names
    assert "app contract lint" in names
    # Buoc nay bat loai loi test khong bat duoc: route khong co test ma thieu
    # import. Da tim thay mot cai that o POST /upscalevideo/queue (2026-08-06).
    assert "ten chua dinh nghia" in names
    assert "system profile" in names
    # DOI TEN 2026-08-26: buoc nay khong con goi `pytest` truc tiep. No di
    # qua `tools/test_nhanh.py` (hai pha: song song + noi tiep cho ba tep
    # ghi vao cay kho), cung tap pass/fail nhung 4 phut thay vi 2 gio.
    assert "bo test (song song)" in names
    for frontend in _frontends_on_disk():
        assert f"frontend {frontend}" in names


#: Những bước `--quick` được phép bỏ. Danh sách này là **hợp đồng**, không phải
#: một chỗ để nới ra mỗi lần thêm bước chậm: mỗi tên ở đây là một thứ mà người
#: chạy `--quick` sẽ KHÔNG được kiểm, và họ cần biết chính xác đó là gì.
BUOC_CHAM = {
    # Bộ test đầy đủ. ⭐ Nay chỉ còn **~4 phút** (trước: 2 giờ) nhờ
    # `tools/test_nhanh.py`. Vẫn để trong danh sách này vì `--quick` là vòng lặp
    # tính bằng giây, và 4 phút vẫn là một khoảng chờ có cảm nhận được.
    "bo test (song song)",
    # H36.9: đẻ tiến trình worker thật trên PostgreSQL, ~135 giây. Là bằng chứng
    # duy nhất cho việc webhook không gửi trùng và cảnh báo không nhân đôi khi
    # nhiều tiến trình chạy cùng lúc — nên nó BẮT BUỘC có trong gate đầy đủ,
    # nhưng quá chậm cho `--quick`.
    "bat bien da tien trinh",
}


def test_quick_mode_only_drops_the_declared_slow_steps():
    """`--quick` để lặp nhanh, nhưng không được lặng lẽ bỏ luôn scanner.

    Trước đây luật là "chỉ được bỏ pytest". Khi H36.9 thêm một bước chậm thứ
    hai, luật đó không còn mô tả đúng thực tế — nên nó được viết lại thành một
    **danh sách có tên**, chứ không nới thành "được bỏ vài bước". Khác biệt nằm
    ở chỗ: một danh sách buộc người thêm bước chậm tiếp theo phải khai ra và
    giải thích, còn một luật mờ thì không.
    """
    from tools.gate import _steps

    full = {step.name for step in _steps(quick=False)}
    quick = {step.name for step in _steps(quick=True)}
    assert full - quick == BUOC_CHAM
    assert quick - full == set(), "`--quick` không được có bước riêng"


def test_gate_failure_tail_is_safe_on_windows_cp1252_console():
    from tools.gate import _console_text

    rendered = _console_text("lỗi tiếng Việt — thất bại", "cp1252")
    rendered.encode("cp1252")
    assert "\\u" in rendered


def test_gate_reports_every_step_instead_of_stopping_at_the_first_failure():
    """Dừng ở lỗi đầu buộc người sửa chạy lại cả bộ để thấy lỗi thứ hai — với
    pytest 20 phút thì mỗi vòng mất nửa giờ."""
    source = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "for step in steps:" in source
    # Không được thoát sớm giữa vòng chạy.
    run_loop = source.split("for step in steps:", 1)[1].split("print(\"\\n\"", 1)[0]
    assert "break" not in run_loop and "return" not in run_loop


@pytest.mark.parametrize("doc", ["CLAUDE.md", "AGENTS.md"])
def test_the_gate_command_is_documented(doc):
    """Một lệnh gate mà không ai biết là không tồn tại."""
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert "tools/gate.py" in text or "tools\\gate.py" in text, (
        f"{doc} chưa nhắc tới tools/gate.py")


#: Tài liệu **chỉ dẫn người ta làm việc** — khác tài liệu ghi lịch sử. Chỉ những
#: tệp này bị soi: một bản audit cũ hay một mục nhật ký được phép nhắc lệnh cũ,
#: vì nó đang kể một chuyện đã xảy ra chứ không bảo ai làm gì.
TAI_LIEU_CHI_DAN = (
    "CLAUDE.md", "AGENTS.md",
    "docs/00_BAT_DAU_TU_DAY.md", "docs/01_COPY_LEN_SERVER.md",
    "docs/02_LENH_CHO_CLAUDE.md", "docs/03_THEM_APP_MOI.md",
)


@pytest.mark.parametrize("doc", TAI_LIEU_CHI_DAN)
def test_khong_tai_lieu_nao_con_bao_chay_pytest_TOAN_BO(doc):
    """⛔ `python -m pytest -q` cho TOÀN BỘ kho không còn là cách chạy đúng.

    Hai lý do, và lý do thứ hai mới là lý do thật:

    1. nó **không** chạy 77 test frontend ⇒ "full regression xanh" là câu nói sai;
    2. nó chạy **một luồng, 25 phút**, trong khi `tools/test_nhanh.py` cho **cùng
       tập pass/fail** trong 4 phút (đo 26/08: 4096 passed / 26 skipped ở cả hai).

    ⭐ Vì sao chốt điều này thay vì chỉ sửa tài liệu một lần: trước 26/08 bộ test
       mất **2 giờ**, và điều đó đổi cách người ta làm việc — `pytest` thôi là một
       vòng lặp và thành một sự kiện. Hệ quả đo được: H40 đóng mà **chưa lượt
       `pytest` đầy đủ nào chạy xong**, và lượt đầu tiên sau đó tìm ra **36 lỗi**.

       Sửa sáu dòng tài liệu chỉ chữa hôm nay. Phép kiểm này chữa ngày mai.

    ⚠️ Lệnh chạy **một tệp** (`pytest tests/test_60_...py`) vẫn đúng và vẫn được
       khuyến khích cho vòng lặp ngắn — nó không bị chặn ở đây.
    """
    import re

    text = (ROOT / doc).read_text(encoding="utf-8")
    # `pytest` + CHI cac co, roi het dong (khong duong dan tep nao theo sau).
    #
    # ⚠️ Da phai sua HAI lan, va ghi lai vi mot banh coc bat hut mot nua thi
    #    NGUY HIEM HON khong co — no tao cam giac da duoc canh:
    #      lan 1: `\s+-\w+`  bo sot `--tb=line`      (dau `=`)
    #      lan 2: them `=`   van bo sot `-p no:cacheprovider`
    #             (gia tri cua co la mot token KHONG co dau gach)
    #
    # ⭐ Cho phep mot token gia tri sau moi co, nhung KHONG chua `/` hay `\` —
    #    do chinh la thu phan biet "gia tri cua co" voi "duong dan mot tep test".
    #    Nho vay `pytest tests/test_60_....py -q` van im, dung nhu no nen the.
    xau = re.compile(
        r"python -m pytest(?:\s+-{1,2}[-\w=.:]+(?:\s+[\w=.:,]+)?)*\s*$", re.M)
    pham = [d.strip() for d in text.splitlines() if xau.search(d)]
    assert not pham, (
        f"{doc} van bao chay pytest TOAN BO: {pham}. "
        r"Dung `python tools\test_nhanh.py` (~4 phut) hoac `python tools\gate.py`.")


def test_banh_coc_nuot_loi_khong_cho_tang_them():
    """Không đòi 0 ngay (90 chỗ trong mã sống là một đợt sửa lớn, rủi ro cao,
    giá trị từng chỗ thấp) — nhưng tuyệt đối không được thêm chỗ mới."""
    import json
    import subprocess
    import sys

    moc = json.loads((ROOT / "tools" / "silent_except_baseline.json")
                     .read_text(encoding="utf-8"))["max"]
    r = subprocess.run([sys.executable, "tools/check_silent_except.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"số chỗ nuốt lỗi đã tăng quá mốc {moc}:\n{r.stdout}"


def test_phep_do_nuot_loi_khong_tinh_nham_cho_da_xu_ly_dung():
    """Handler biến ngoại lệ thành GIÁ TRỊ nhìn thấy được thì không phải nuốt.

    Thiếu điều kiện này, phép đo đếm thừa gấp đôi ở `platform_core` (18 thay vì
    8) và sẽ dẫn người đọc đi "sửa" những chỗ vốn đã đúng — như
    `registry.py` ghi lỗi vào `LoadedApp.error` để trang admin hiển thị.
    """
    import ast
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from check_silent_except import _co_dung_ngoai_le

    def _handler(src):
        return next(n for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.ExceptHandler))

    nuot = _handler("try:\n    x()\nexcept Exception:\n    y = 1\n")
    xu_ly = _handler("try:\n    x()\nexcept Exception as exc:\n    ghi(str(exc))\n")
    bat_ten_khong_dung = _handler("try:\n    x()\nexcept Exception as exc:\n    y = 1\n")

    assert _co_dung_ngoai_le(nuot) is False
    assert _co_dung_ngoai_le(xu_ly) is True, "chỗ đã xử lý đúng bị tính là nuốt lỗi"
    assert _co_dung_ngoai_le(bat_ten_khong_dung) is False, (
        "đặt tên cho ngoại lệ rồi bỏ đó vẫn là nuốt")


def test_platform_core_khong_con_cho_nuot_loi_nao():
    """Tầng nền tảng là chỗ mọi app đi qua — lỗi biến mất ở đây là tệ nhất."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "tools/check_silent_except.py", "--list"],
                       cwd=ROOT, capture_output=True, text=True)
    con = [l.strip() for l in r.stdout.splitlines() if "platform_core/" in l]
    assert not con, f"platform_core còn nuốt lỗi lặng lẽ: {con}"


# ── Hai bay cua chinh gate, do 25/08/2026 ──────────────────────────────────

def test_gate_NOI_RA_khi_cay_doi_trong_luc_chay():
    """🔴 Mot luot gate day du mat 2,9-4,4 gio. Kho nay co hai phien lam viec
    song song, nen cay doi vai phut mot lan — va luot 4,4 gio ngay 25/08 bao
    loi o mot tep **da doi ten tu nhieu gio truoc**.

    Ket qua ay khong sai luc no do. No tra loi ve QUA KHU, va doc no nhu bang
    chung cho hien tai la cach sinh ra ba vong sua nhung thu khong con hong.
    """
    ma = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "_dau_van_tay_cay" in ma, "gate khong biet cay co doi hay khong"
    assert "CAY DA DOI TRONG LUC CHAY" in ma
    assert ma.count("_dau_van_tay_cay()") >= 3, (
        "phai lay van tay CA hai dau (truoc + sau), khong chi mot dau")


def test_quick_PHAI_noi_no_khong_chay_gi():
    """⛔ `--quick` dung khi bo pytest — do la muc dich no khai. Loi nam o cho
    dong ket qua in Y HET gate day du, nen nguoi doc hieu no la "moi thu xanh".

    Ca hai phien Claude lam viec trong kho nay ngay 25/08 deu doc nhu vay — va
    MOI loi that hom do deu nam o dung buoc `pytest` ma che do nay bo qua:
    migration vo tren SQLite, lien ket dieu khoan 404, trung so tep test.
    """
    ma = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "BO_QUA_KHI_QUICK" in ma
    assert "KHONG chay" in ma, "dong RESULT cua --quick phai ke ten thu bi bo"
    assert "Chua phai bang chung day du" in ma
