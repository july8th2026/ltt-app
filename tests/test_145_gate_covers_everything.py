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
    # ⛔ GO 2026-09-04 cung voi ca tinh nang. Chot nay dung khi no ton tai:
    #    no ngan mot buoc bien mat lang le. Lan nay viec go la CO Y (chu du an
    #    quyet), nen phai go luon chot — mot chot canh mot thu khong con la mot
    #    lan gate do ma khong ai sua duoc.
    #    Ly do va toan bo pham vi: docs/HO_SO_HE_THONG.md (nay la bia mo).
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


def _buoc_gia(ten: str, hong: bool, nhom: str):
    """Một `Step` thật, chạy một tiến trình con vài mili-giây."""
    import sys as _sys

    from tools.gate import ROOT as _ROOT
    from tools.gate import Step

    ma = "raise SystemExit(1)" if hong else "pass"
    return Step(ten, [_sys.executable, "-c", ma], _ROOT, nhom=nhom)


@pytest.mark.parametrize("tuan_tu", [True, False])
@pytest.mark.parametrize("hong_o", ["cong", "nang", "tinh-1"])
def test_gate_reports_every_step_instead_of_stopping_at_the_first_failure(
        tuan_tu, hong_o):
    """Dừng ở lỗi đầu buộc người sửa chạy lại cả bộ để thấy lỗi thứ hai — với
    pytest 20 phút thì mỗi vòng mất nửa giờ.

    ⭐ Phép kiểm này CHẠY bộ lập lịch, không đọc mã nguồn của nó.

       Bản trước so chuỗi `"for step in steps:"` rồi soi đoạn văn bản sau nó tìm
       `break`/`return`. Nó đúng suốt hai tháng vì gate chỉ có một vòng `for`
       phẳng — và **đỏ ngay lúc bất biến vẫn còn nguyên**, khi vòng đó được thay
       bằng `ThreadPoolExecutor` ngày 27/08.

       Đó là cái giá của việc đo một bất biến qua **hình dạng mã nguồn**: nó
       không phân biệt được "đã hỏng" với "đã viết khác". Và nguy hơn theo chiều
       ngược lại: một bộ lập lịch mới CÓ thoát sớm thật vẫn lọt, miễn là chữ
       `return` của nó không rơi vào đúng cửa sổ văn bản mà phép kiểm cắt ra.
    """
    from tools.gate import _chay_theo_lich

    steps = [_buoc_gia(t, t == hong_o, n) for t, n in
             (("cong", "cong"), ("nang", "nang"), ("tinh-1", "tinh"),
              ("tinh-2", "tinh"), ("frontend", "frontend"))]
    _chay_theo_lich(steps, j=4, tuan_tu=tuan_tu)

    chua_chay = [s.name for s in steps if s.ok is None]
    assert not chua_chay, f"bo lap lich bo qua {chua_chay} sau khi {hong_o} do"
    assert [s.name for s in steps if not s.ok] == [hong_o]


def test_gate_chay_buoc_cong_TRUOC_moi_thu_khac():
    """`bien dich duoc` là cổng gác — song song hoá nó là bỏ mất ý nghĩa của nó.

    Một tệp không biên dịch được thì mọi phép đo phía sau đều vô nghĩa: các chốt
    khác **bỏ qua** tệp không parse được vì chúng đếm xu hướng. Nên bước này phải
    xong, và phải xong **trước**, chứ không phải xong cùng lúc.
    """
    from tools.gate import _steps

    cong = [s.name for s in _steps(quick=False) if s.nhom == "cong"]
    assert cong == ["bien dich duoc"], cong


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

    ⭐ Ban truoc dem so lan chu `_dau_van_tay_cay()` xuat hien trong ma nguon
       (">= 3"). No do ngay 27/08 khi ham do duoc doi ten — trong khi bat bien
       van nguyen ven. Day la lan thu HAI trong mot ngay mot phep kiem o tep nay
       do vi ma duoc **viet lai** chu khong phai vi no **hong**.

       Nen bay gio no chay that: sua mot tep trong cay giua hai anh chup, roi
       doi hoi gate nhin ra.
    """
    import os
    import tempfile

    from tools.gate import _anh_chup_cay

    ma = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "CAY DA DOI TRONG LUC CHAY" in ma

    truoc = _anh_chup_cay()
    fd, ten = tempfile.mkstemp(suffix=".py", dir=ROOT / "tools")
    os.close(fd)                    # Windows khong xoa duoc tep dang mo
    tam = pathlib.Path(ten)
    try:
        assert _anh_chup_cay() != truoc, "them mot tep ma anh chup khong doi"
    finally:
        tam.unlink()
    assert _anh_chup_cay() == truoc, "xoa di roi ma anh chup van khac"


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


# ─────────────────────────────────────────────────────────────────────────────
#  Chế độ `--vong-lap` (2026-08-27)
#
#  ⭐ Vì sao nó tồn tại: ngày 27/08 gate đầy đủ được chạy **sáu lần** để *chẩn
#     đoán*, mỗi lần ~5 phút, và bốn trong sáu lượt đỏ vì một thứ mà một bước
#     con lẻ trả lời trong nửa giây. Gate là công cụ ra **phán quyết**; dùng nó
#     để dò là trả 5 phút cho một câu trả lời đã có sẵn.
# ─────────────────────────────────────────────────────────────────────────────

def test_vong_lap_giu_TOAN_BO_nhom_tinh():
    """Cắt bớt phần rẻ là cắt nhầm chỗ.

    16 chốt tĩnh tốn **7 giây** khi chạy song song, và chính chúng bắt bốn trong
    sáu lỗi hôm 27/08. Thứ đáng cắt là bộ test đầy đủ (255s), không phải chúng.
    """
    from tools.gate import _rut_gon_vong_lap, _steps

    day_du = _steps(quick=False)
    vong_lap = _rut_gon_vong_lap(list(day_du))

    tinh_day_du = {s.name for s in day_du if s.nhom == "tinh"}
    tinh_vong_lap = {s.name for s in vong_lap if s.nhom == "tinh"}
    assert tinh_day_du == tinh_vong_lap
    assert {s.name for s in vong_lap if s.nhom == "cong"} == {"bien dich duoc"}


def test_vong_lap_thay_bo_test_bang_lf_VA_chan_bay_lfnf():
    """`--lf` một mình **chạy tất cả** khi lượt trước không có gì đỏ.

    Tài liệu pytest nói đúng như vậy, và nó là lý do lượt đo đầu tiên của chế độ
    này mất **4 phút 26** thay vì ~15 giây. `--lfnf=none` là thứ đổi hành vi đó,
    nên nó phải nằm trong argv chứ không nằm trong trí nhớ người dùng.
    """
    from tools.gate import _rut_gon_vong_lap, _steps

    vong_lap = _rut_gon_vong_lap(_steps(quick=False))
    ten = {s.name for s in vong_lap}
    assert "bo test (song song)" not in ten
    (buoc,) = [s for s in vong_lap if s.name == "bo test --lf"]
    assert "--lf" in buoc.argv and "--lf-rong-thi-khong-chay" in buoc.argv


def test_cache_lastfailed_co_BA_trang_thai_khong_phai_hai(monkeypatch, tmp_path):
    """*Vắng mặt*, *rỗng* và *không đọc được* là ba chuyện khác nhau.

    ⛔ Gộp chúng lại đã hỏng theo **cả hai chiều** trong cùng một ngày:

       · gộp "không đọc được" vào "rỗng" → bộ lọc pha 2 bỏ qua cả ba tệp mãi mãi;
       · gộp "vắng mặt" vào "không đọc được" → sau **mỗi** lượt gate xanh,
         `--vong-lap` chạy lại toàn bộ 4143 test (đo 27/08: 3 phút 35) đúng
         bằng việc nó sinh ra để tránh.

    ⚠️ Và pytest nhầm ở cùng chỗ: `--lfnf=none` chỉ áp khi cache **có mà rỗng**.
       Cache vắng mặt thì nó coi là "không biết gì về lượt trước" và chạy hết.
       Nên `test_nhanh` phải tự kết luận, không được nhờ cờ đó.
    """
    import tools.test_nhanh as tn

    monkeypatch.setattr(tn, "GOC", tmp_path)
    assert tn._da_do() is None, "chua tung chay pytest => khong biet"

    goc = tmp_path / ".pytest_cache" / "v" / "cache"
    goc.mkdir(parents=True)
    assert tn._da_do() == (set(), set()), "tep vang mat => luot truoc xanh het"

    (goc / "lastfailed").write_text("{}", encoding="utf-8")
    assert tn._da_do() == (set(), set())

    (goc / "lastfailed").write_text("khong-phai-json", encoding="utf-8")
    assert tn._da_do() is None, "doc hong => khong biet => phai chay het"

    (goc / "lastfailed").write_text(
        '{"tests/test_209_versioning_status.py::a": true}', encoding="utf-8")
    assert tn._da_do() == ({"tests/test_209_versioning_status.py::a"},
                           {"tests/test_209_versioning_status.py"})


def test_moi_dong_print_cua_gate_song_duoc_khi_dau_ra_bi_HUNG():
    """`python tools/gate.py > gate.log` phải chạy được, không chỉ gọi tay.

    ⛔ Hứng đầu ra làm stdout thôi là console, Python rơi về `cp1252` trên
       Windows, và **một** dấu tiếng Việt ném `UnicodeEncodeError`. Nó vỡ ở chỗ
       ít người nhìn nhất — và vỡ sớm nhất trong CI.

    Ngày 27/08 lỗi này xảy ra hai lần trong một buổi: một emoji trong
    `check_multiproc.py` (làm ĐỎ một bước gate, với stack trace không liên quan
    gì tới thứ nó đang kiểm), rồi một chữ "bắn" trong chính dòng giải thích rằng
    không có gì hỏng.

    ⭐ Chỉ soi dòng `print(` — chú thích và docstring tiếng Việt là cố ý và
       không bao giờ tới stdout.
    """
    nguon = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    xau = [(i, dong.strip()) for i, dong in enumerate(nguon.splitlines(), 1)
           if "print(" in dong and any(ord(c) > 127 for c in dong)]
    assert not xau, f"dong print co ky tu ngoai ASCII: {xau}"


def test_anh_chup_cay_phu_MA_DEPLOY_DI_XA_khoi_kho():
    """🔴 CHỐT "CÂY ĐỨNG YÊN" TỪNG KHÔNG SOI BA THỨ QUAN TRỌNG NHẤT.

    Trước 03/09, `_anh_chup_cay()` chỉ chụp bảy thư mục và **bỏ qua**
    `llm_gateway/` (mã cổng máy B), `sdk/` (bộ cài chạy trên máy khách) và
    `frontend/`.

    ⛔ Nghĩa là sửa mã cổng máy B ngay giữa một lượt gate thì `CAY DA DOI
       TRONG LUC CHAY` **không kêu**, và dòng `RESULT: PASS` nói về một cây đã
       không còn tồn tại. Với hai phiên làm việc song song trên cùng một kho,
       đó không phải rủi ro lý thuyết.

    ⭐ Ba thư mục ấy đáng canh **hơn** phần còn lại, không kém: mã trong chúng
       **rời khỏi kho này** — chạy trên máy B, hoặc tải về máy khách. Một lần
       sai ở đó không lộ ra trong bất kỳ phép kiểm nào chạy tại chỗ.
    """
    from tools.gate import THU_MUC_CHUP

    for phai_co in ("llm_gateway", "sdk", "frontend"):
        assert phai_co in THU_MUC_CHUP, (
            f"`{phai_co}` khong nam trong anh chup cay. Ma o do DEPLOY DI XA "
            f"khoi kho nay, nen sua no giua mot luot gate se khong bi phat hien.")


def test_anh_chup_cay_CAT_node_modules_nhung_GIU_bundle_da_commit():
    """Cắt phải cắt đúng thứ vô nghĩa, và **chỉ** thứ vô nghĩa.

    ⭐ Cắt `node_modules` là lý do ảnh chụp rộng gấp đôi mà lại **nhanh hơn**:
       `os.walk` cắt `dirnames` tại chỗ nên nó không đi xuống 12.255 tệp, khác
       hẳn `rglob` (đi xuống rồi mới lọc). Đo 03/09: 1.321 tệp/0,143 s → 1.491
       tệp/0,047 s.

    ⛔ NHƯNG `.vite`, `dist`, `coverage` thì KHÔNG được cắt. Bốn tệp
       `server/static/*/.vite/manifest.json` là bundle production **đã commit**
       — chúng chính là thứ máy chủ phục vụ. Cắt chúng khỏi ảnh chụp là mất
       đúng thứ cần canh, và mất một cách im lặng.
    """
    from tools.gate import _BO_QUA_THU_MUC, _anh_chup_cay

    assert "node_modules" in _BO_QUA_THU_MUC
    for khong_duoc_cat in (".vite", "dist", "coverage"):
        assert khong_duoc_cat not in _BO_QUA_THU_MUC, (
            f"`{khong_duoc_cat}` bi cat khoi anh chup — bundle da commit nam "
            f"trong do, va mat chung la mat dung thu can canh")

    cay = _anh_chup_cay()
    assert not [p for p in cay if "node_modules" in p], "node_modules lot vao anh chup"
    manifest = [p for p in cay if p.endswith(".vite/manifest.json")]
    assert manifest, "khong con manifest bundle nao trong anh chup"


def test_canh_bao_cay_doi_phai_KE_TEN_chu_khong_chi_bao_co_doi():
    """Một cảnh báo không nói được cái gì đổi thì không dùng để làm gì.

    Bản trước in hai chuỗi băm. Ngày 27/08 nó bắn ở **mọi** lượt gate đầy đủ, và
    nguyên nhân hoá ra là ba chỗ khôi phục trong `test_306` trả lại đúng từng
    byte nhưng quên `os.utime` — **kích thước y hệt, mtime khác**. Hai chuỗi băm
    không cách nào nói ra điều đó.

    Và đó là dòng quyết định lượt chạy có tính làm **bằng chứng** hay không, nên
    một cảnh báo luôn bắn ở đây đắt hơn hẳn một cảnh báo luôn bắn ở chỗ khác.
    """
    from tools.gate import _ke_cho_da_doi

    import io
    import contextlib

    ra = io.StringIO()
    with contextlib.redirect_stdout(ra):
        _ke_cho_da_doi({"a.py": (10, 1), "b.py": (10, 1), "c.py": (9, 1)},
                       {"a.py": (10, 2), "b.py": (11, 1)})
    out = ra.getvalue()
    assert "a.py" in out and "chi mtime" in out, "khong phan biet doi mtime"
    assert "b.py" in out and "10 -> 11 byte" in out, "khong neu doi noi dung"
    assert "c.py" in out, "khong neu tep bi xoa"


def test_ba_tep_ghi_vao_cay_deu_tra_lai_CA_DAU_THOI_GIAN():
    """Khôi phục đúng nội dung mà sai mtime vẫn làm hỏng dấu vân tay của gate.

    Phép kiểm này **chạy** ba tệp đó rồi so ảnh chụp cây trước/sau, chứ không
    đọc mã nguồn tìm chữ `os.utime` — vì cách viết đúng có nhiều hình dạng, và
    thứ ta cần đảm bảo là **kết quả**, không phải cách gõ.
    """
    import subprocess
    import sys

    from tools.gate import _anh_chup_cay
    from tools.test_nhanh import TEP_NOI_TIEP

    truoc = _anh_chup_cay()
    subprocess.run([sys.executable, "-m", "pytest", "-q", *TEP_NOI_TIEP],
                   cwd=ROOT, capture_output=True)
    sau = _anh_chup_cay()

    doi = {k for k in set(truoc) | set(sau) if truoc.get(k) != sau.get(k)}
    assert not doi, (
        f"ba tep pha 2 lam ban cay: {sorted(doi)}. Xem `finally:` cua chung — "
        f"khoi phuc phai co ca `os.utime`, khong chi noi dung.")
def test_moi_buoc_NANG_deu_phai_khai_tai_nguyen():
    """`nhom="nang"` ma khong khai `tai_nguyen` la tu chon ra khoi khoa, IM LANG.

    🔴 Do 06/09/2026: tren 29 `Step()` trong `gate.py`, chi 3 khai tai nguyen —
       va HAI trong so cac buoc `nang` khong khai gi ca:

           bat bien da tien trinh   -> dung PostgreSQL, goi `drop_all()`
           bo test --lf             -> KHONG khai gi, ke ca `cpu_nhieu`

       Hai luot gate o hai worktree cung do trong mot dem, hai trieu chung khac
       nhau, mot nguyen nhan: mot ben xoa schema giua luc ben kia dang ghi.

           relation "api_metric_samples" does not exist
           assert 0 == 9   (9 job bien mat khoi bang)

    ⛔ `bo test --lf` la ca te nhat vi no **doi lot mot buoc nhanh**:
       `gate --vong-lap` duoc quang cao la vong lap 15 giay, nhung `--lf` chay
       TOAN BO bo test khi cache `lastfailed` rong hoac toan id chet (do that:
       393 giay). Mot luot nang vo hinh hoan toan voi khoa.

    ⭐ Khoa **khong doan duoc** buoc lam gi; no chi giu thu duoc KHAI. Nen them
       mot buoc nang ma quen `tai_nguyen=` la tu chon ra khoi khoa — khong co gi
       do, khong co gi vang mat, chi co mot cai ten khong duoc nhac toi.

    ⚠️ Phep kiem nay doc AST va menh de cua no noi ve **hinh dang ma**, nen AST
       la cong cu DUNG o day — khac han truong hop
       `test_main_cua_test_nhanh_THUC_SU_chay_pha_1`, noi menh de noi ve **hanh vi**
       va AST mu voi no.
    """
    import ast

    cay = ast.parse((ROOT / "tools" / "gate.py").read_text(encoding="utf-8"))
    thieu = []
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Step"):
            continue
        kw = {k.arg: k.value for k in n.keywords}
        nhom = getattr(kw.get("nhom"), "value", "tinh")
        if nhom != "nang" or "tai_nguyen" in kw:
            continue
        ten = (n.args[0].value if n.args and isinstance(n.args[0], ast.Constant)
               else "?")
        thieu.append(f"dong {n.lineno}: {ten}")

    assert not thieu, (
        "buoc nhom=\"nang\" KHONG khai tai_nguyen => vo hinh voi cua_so_yen: "
        + "; ".join(thieu))
