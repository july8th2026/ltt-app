"""706 — bộ đo mobile phải giữ bốn bài học đã trả giá để có.

`tools/mobile_quet.js` + `tools/mobile_qa.py quet` là thứ dựng lại được mọi con
số trong `docs/MOBILE/`. Nhưng một bộ đo cũng là mã, và mã thì trôi — nên bốn
mệnh đề dưới đây được chốt lại.

⭐ Cả bốn đều đến từ một lần bộ đo **nói dối**, không phải từ lý thuyết:

1. `getBoundingClientRect().right` báo cả phần đã bị một tổ tiên `overflow-x:auto`
   **hấp thụ**. Không lọc theo tổ tiên cuộn thì bộ đo chỉ nhầm thủ phạm — đã xảy
   ra **ba lần** trong một phiên (khối `<pre>`, `nav.apptabs`, và bảng ở `/jobs`).

2. Cỡ chữ ô nhập phải đọc `getComputedStyle`: luật 16px nằm trong
   `@media(pointer:coarse)`, thuộc tính HTML không thấy nó.

3. Vùng chạm **trong** một canvas React Flow phải chia lại cho zoom. Đo 05/09:
   `.react-flow__handle` đo 29px ở zoom 0,648 nhưng CSS là **44px** — đã đạt sàn.
   Không chia thì ta "sửa" một thứ chỉ nhỏ vì người dùng đang thu nhỏ canvas.

4. Dòng `const CAU_HINH = {...};` là **giao diện** giữa Python và JS. `quet()`
   thay đúng dòng ấy; đổi cách viết nó thì lệnh gãy — và gãy ở chỗ thông báo
   lỗi không nói gì về nguyên nhân.

Không mở trình duyệt, không cần máy chủ.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
JS = GOC / "tools" / "mobile_quet.js"
PY = GOC / "tools" / "mobile_qa.py"


def boc_chu_thich(s: str) -> str:
    """Bỏ `/* */` và `//`, giữ độ dài. Tệp này thuần JS nên không cần lọc HTML."""
    ra = list(s)
    i, n = 0, len(s)
    while i < n:
        mo = next((c for c in (("/*", "*/"), ("//", "\n")) if s.startswith(c[0], i)), None)
        if mo:
            j = s.find(mo[1], i + len(mo[0]))
            j = n if j < 0 else j + len(mo[1])
            for k in range(i, j):
                if ra[k] != "\n":
                    ra[k] = " "
            i = j
        else:
            i += 1
    return "".join(ra)


def test_bo_boc_chu_thich_that_su_boc():
    """Chính phần giải thích ở đầu tệp JS nhắc cả bốn từ khoá dưới đây."""
    vao = "a /* coToTienCuon */ b // getComputedStyle\nc"
    ra = boc_chu_thich(vao)
    assert "coToTienCuon" not in ra and "getComputedStyle" not in ra
    assert len(ra) == len(vao)


@pytest.fixture(scope="module")
def js() -> str:
    assert JS.exists(), "tools/mobile_quet.js biến mất"
    return boc_chu_thich(JS.read_text(encoding="utf-8"))


# ── Bốn bài học ────────────────────────────────────────────────────────────

def test_loc_theo_to_tien_cuon_truoc_khi_goi_la_TRAN(js):
    assert "coToTienCuon" in js, (
        "bộ đo không còn lọc theo tổ tiên cuộn — nó sẽ báo mọi phần tử trong một "
        "vùng `overflow-x:auto` là tràn, và chỉ nhầm thủ phạm")
    assert "overflowX" in js
    i_ham = js.find("coToTienCuon")
    i_dung = js.find("coToTienCuon(el)")
    assert i_dung > i_ham, "hàm lọc có mặt nhưng không được gọi"


def test_co_chu_o_nhap_doc_COMPUTED_chu_khong_doc_thuoc_tinh(js):
    assert "getComputedStyle(el).fontSize" in js, (
        "cỡ chữ đọc từ thuộc tính HTML sẽ không bao giờ thấy luật 16px trong "
        "`@media(pointer:coarse)` — phép đo sẽ xanh giả trên mọi trang")


def test_vung_cham_trong_canvas_duoc_chia_lai_cho_zoom(js):
    assert "react-flow__viewport" in js and "zoom" in js, (
        "bộ đo không còn biết canvas đang thu phóng")
    assert re.search(r"b\.height\s*/\s*zoom", js), (
        "chiều cao trong canvas không được chia lại cho zoom — `.react-flow__handle` "
        "đo 29px ở zoom 0,648 nhưng CSS là 44px, tức đã đạt sàn")


def test_dong_CAU_HINH_dung_khuon_ma_python_thay_duoc():
    """Giao diện Python↔JS. Đổi cách viết thì `quet` gãy, và gãy khó hiểu."""
    tho = JS.read_text(encoding="utf-8")
    assert re.search(r"const CAU_HINH = \{.*?\};", tho, re.S), (
        "không còn dòng `const CAU_HINH = {...};` — `mobile_qa.py quet` thay đúng "
        "dòng này bằng cấu hình thật trước khi gọi playwright-cli")
    py = PY.read_text(encoding="utf-8")
    assert "const CAU_HINH = " in py, "phía Python không còn thay dòng ấy"


# ── Hai cái bẫy nền tảng, đã trả giá ──────────────────────────────────────

def test_khong_dung_HEAD_de_do_route_con_song():
    """FastAPI trả **405** cho `HEAD` ở route chỉ khai `GET`.

    Một bộ lọc "bỏ mọi thứ >= 400" khi ấy vứt sạch cả 23 route rồi báo
    *"quét 0 route"* — rất tự tin, và hoàn toàn vô nghĩa. Đã xảy ra ở lượt chạy
    đầu tiên của chính lệnh này.
    """
    py = PY.read_text(encoding="utf-8")
    m = re.search(r"def route_khach.*?(?=\ndef )", py, re.S)
    assert m, "không còn `route_khach`"
    assert 'method="HEAD"' not in m.group(0), (
        "`route_khach` quay lại dùng HEAD — FastAPI trả 405 và bộ lọc sẽ vứt sạch route")


def test_tim_playwright_cli_bang_which_chu_khong_goi_thang():
    """Trên Windows, npm cài `playwright-cli` thành bộ ba tệp (không đuôi, `.cmd`,
    `.ps1`), và `subprocess` **không** tự chọn `.cmd` — nó báo `WinError 2`.
    `shutil.which` thì biết, vì nó đọc `PATHEXT`."""
    py = PY.read_text(encoding="utf-8")
    assert 'shutil.which("playwright-cli")' in py, (
        "gọi thẳng `playwright-cli` trong subprocess sẽ hỏng trên Windows")


# ── 320px phải nằm trong bộ khung mặc định ────────────────────────────────

def test_khung_mac_dinh_co_320px():
    """320px bắt được **hai** lỗi mà 390px bỏ lọt, và một trong hai do chính bản
    vá vùng chạm 44px sinh ra. Một bộ đo chỉ chạy ở khổ "chuẩn" không thấy mép."""
    py = PY.read_text(encoding="utf-8")
    m = re.search(r"KHUNG_MAC_DINH = \(([^)]*)\)", py, re.S)
    assert m, "không còn `KHUNG_MAC_DINH`"
    assert "p320" in m.group(1)
    js = JS.read_text(encoding="utf-8")
    assert re.search(r"p320:\s*\{\s*w:\s*320", js), "`mobile_quet.js` không còn khổ 320"

def test_bo_quet_PHAI_bao_khi_bi_day_ve_login():
    """🔴 Một phép đo trên trang đăng nhập KHÔNG phải một kết quả.

    Đo 06/09: ba route `prompt-ai-ommi` báo *"0 tràn, 0 lỗi console"* — và cả
    ba đều là `/login`. Cookie của phép dò không có tác dụng, và bộ quét
    **không hề biết**: nó đo bất cứ thứ gì nhận được.

    ⛔ Nó hỏng theo hướng **dễ chịu**: một trang đăng nhập thì ngắn, không tràn
       ngang, không có ô nhập nhỏ, không có video. **Mọi** con số đều đẹp —
       nên không ai đi kiểm lại.

    ⭐ Ghi **URL thực tế** chứ không ghi URL đã yêu cầu. Hai thứ ấy khác nhau
       đúng ở chỗ quan trọng nhất, và chỉ một trong hai nói thật.

    ⚠️ Hoá ra bộ quét **không** hỏng — phép dò tay của tôi truyền cả chuỗi
       `session=eyJ...` làm *giá trị* cookie. Nhưng lỗ thì có thật: trước bản
       vá này **không có gì** kiểm rằng phiên còn hiệu lực.
    """
    js = (GOC / "tools" / "mobile_quet.js").read_text(encoding="utf-8")
    assert "url_thuc" in js, (
        "bo quet khong ghi URL THUC TE - khong the biet no da do trang nao")
    assert "CHUA_DANG_NHAP" in js, "bo quet khong danh dau luot bi day ve /login"

    py = (GOC / "tools" / "mobile_qa.py").read_text(encoding="utf-8")
    assert "CHUA_DANG_NHAP" in py, (
        "ban tom tat khong doc co ay - no se in mot bang toan so dep")
    assert "VO NGHIA" in py, "canh bao phai KEU TO, khong phai mot dong lang le"


def test_do_nhanh_thay_CHAN_dung_ba_loi_da_xay_ra_that(tmp_path):
    """`tools/do_nhanh.thay` phải chặn cả ba, vì cả ba đã xảy ra trong một buổi.

    🔴 Ngày 06/09 một phiên tự kê 13 lỗi mình gây ra; **9/13** nằm ở **công cụ
       dùng để đo**, không nằm ở thứ được giao. Kỷ luật sống trong mã sản phẩm
       và được miễn trừ cho script tạm — trong khi chính script tạm quyết định
       ta **nhìn thấy gì**.

    ⭐ Một luật *"hãy cẩn thận hơn"* không sửa được cái nào trong ba. Một hàm
       thì có.
    """
    import sys                                   # noqa: PLC0415
    sys.path.insert(0, str(GOC / "tools"))
    import do_nhanh                              # noqa: PLC0415

    CR_LF = chr(13) + chr(10)
    LF = chr(10)

    # (1) Neo khong khop -> `str.replace` im lang khong thay gi.
    t1 = tmp_path / "a.txt"
    t1.write_bytes(b"xin chao")
    try:
        do_nhanh.thay(str(t1), "khong-co-chuoi-nay", "x")
        raise AssertionError("neo sai ma khong keu - loi se di qua im lang")
    except AssertionError as e:
        assert "neo khop 0 lan" in str(e)
    assert t1.read_bytes() == b"xin chao", "tep bi doi du neo khong khop"

    # (2) Kieu ket dong CRLF phai duoc giu.
    t2 = tmp_path / "b.txt"
    t2.write_bytes(("mot" + CR_LF + "hai" + CR_LF).encode("utf-8"))
    do_nhanh.thay(str(t2), "hai", "ba")
    d = t2.read_bytes()
    assert d.count(CR_LF.encode()) == 2 and d.count(LF.encode()) == 2, (
        f"kieu ket dong bi doi: {d!r} - ca tep thanh mot diff khong ai doc duoc")

    # (3) `.py` sai cu phap -> phai no TRUOC khi cham tep.
    t3 = tmp_path / "c.py"
    goc = ("def f():" + LF + "    return 1" + LF).encode("utf-8")
    t3.write_bytes(goc)
    try:
        do_nhanh.thay(str(t3), "    return 1", "return 1")   # lech thut le
        raise AssertionError("ghi mot tep .py hong ma khong keu")
    except (SyntaxError, IndentationError):
        pass
    assert t3.read_bytes() == goc, "tep bi ghi hong du `ast.parse` da that bai"


def test_do_nhanh_tien_trinh_KHONG_khop_chinh_no():
    """⛔ Điều kiện phải là thứ tiến trình đang hỏi **không thể tự thoả**.

    Đo 06/09, hai phiên cùng dính: một bộ lọc theo `cmdline` khớp vào **chính
    công cụ đo**, vì vỏ `bash -c` mang cả mã nguồn được truyền cho nó. Một phiên
    dùng bộ lọc ấy để `kill`, và lệnh giết đi **ngược lên cây cha của chính nó**
    — script thoát mã 15.

    ⚠️ Lọc theo `cwd` **không** cứu được ca này: shell của người đang hỏi cũng có
       `cwd` đúng bằng cây ấy.
    """
    import os                                    # noqa: PLC0415

    import sys                                   # noqa: PLC0415
    sys.path.insert(0, str(GOC / "tools"))
    import do_nhanh                              # noqa: PLC0415

    # Tien trinh dang chay phep kiem nay CO chuoi "pytest" trong cmdline.
    ds = do_nhanh.tien_trinh("pytest")
    assert os.getpid() not in [p.pid for p in ds], (
        "bo loc khop vao CHINH tien trinh dang hoi - mot che do giet se di "
        "nguoc len cay cha cua no")


def test_moc_timeout_KHONG_duoc_la_chu_thich_chet():
    """🔴 `@pytest.mark.timeout` chỉ có tác dụng khi `pytest-timeout` **có mặt**.

    Đo 06/09: `tests/test_616:106` khai `@pytest.mark.timeout(240)` trong khi
    plugin **không có trong máy**. Pytest chỉ cảnh báo `PytestUnknownMarkWarning`
    rồi **chạy tiếp** — nên mốc ấy là một **chú thích chết**, và một test treo sẽ
    treo mãi thay vì đỏ.

    ⛔ Đây là lớp lỗi *"biết mà không làm"* ở tầng phụ thuộc: mã **nói** nó có
       một giới hạn, môi trường thì **không** thi hành giới hạn ấy, và không có
       gì đỏ. Bộ test dài 8 phút mà một test treo được thì lượt gate không bao
       giờ kết thúc.

    ⭐ Đo sau khi cài: một test `sleep(20)` với `timeout(2)` cho `returncode 1`
       và in `Timeout`. Trước đó nó ngủ đủ 20 giây rồi **xanh**.

    ⚠️ Phép kiểm này canh **môi trường**, không canh mã — cố ý. Một mốc timeout
       trong mã không tự biết plugin của nó có mặt hay không.
    """
    import importlib.util                          # noqa: PLC0415

    assert importlib.util.find_spec("pytest_timeout") is not None, (
        "moc `@pytest.mark.timeout` trong bo test dang la CHU THICH CHET - "
        "cai `pytest-timeout` (xem requirements-dev.txt)")


def test_moi_goi_trong_requirements_dev_deu_CO_MAT():
    """Một phụ thuộc không được khai sẽ biến mất **im lặng** ở máy khác.

    🔴 Trước 06/09 bộ công cụ test không được khai ở **đâu cả** —
    `requirements.txt` lẫn `requirements-server.txt` đều không có `pytest`, và
    `setup/2-cai-dat.ps1` **cố ý** không cài (production không chạy pytest).
    Bộ test chạy bằng **Python hệ thống** với những gói ai đó đã cài bằng tay.

    ⇒ Phép kiểm này biến `requirements-dev.txt` từ một tờ khai thành một **ràng
      buộc đo được**: khai mà không cài, hoặc cài mà quên khai, đều đỏ.
    """
    import importlib.metadata as md                # noqa: PLC0415

    tep = GOC / "requirements-dev.txt"
    assert tep.exists(), "khong con requirements-dev.txt"

    thieu = []
    for dong in tep.read_text(encoding="utf-8").splitlines():
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        ten = d.split("==")[0].split("#")[0].strip()
        if not ten:
            continue
        try:
            md.version(ten)
        except md.PackageNotFoundError:
            thieu.append(ten)

    assert not thieu, (
        f"khai trong requirements-dev.txt nhung KHONG co trong may: {thieu} - "
        "moi dong o do la mot thu bo test DANG dua vao")


def test_do_nhanh_tien_trinh_KHONG_khop_ke_chi_NHAC_ten():
    """🔴 Lo thu TU cua ho bay "bo loc khop chinh minh", do 06/09/2026.

       Phien LTTCHAT V3 do duoc, va toi tai hien lai tren may nay:

           loc ca dong lenh   4 tien trinh  (3 la `bash.exe` ANH EM)
           loc kich ban       1 tien trinh

       Ba cai thua la shell cua nhung lenh nen TRUOC DO trong cung phien.
       Chung KHONG phai to tien, nen `parents()` khong cham toi — ba ban va
       truoc deu di theo quan he cha-con nen deu khong bit duoc cho nay.

    ⛔ Va rao `ten_tien_trinh="python.exe"` chi THU HEP chu khong dong: mot
       script PYTHON chi NHAC chuoi ay trong ma nguon van bi dem. Da dung mot
       tien trinh moi de xac nhan truoc khi sua — no bi dem that.

    ⇒ Phep khop phai hoi KICH BAN DANG CHAY, khong hoi ca dong lenh.
    """
    import subprocess
    import sys
    import time

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "do_nhanh_kt", GOC / "tools" / "do_nhanh.py")
    do_nhanh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(do_nhanh)

    # Ba dang phai phan biet duoc, khong can mo tien trinh nao.
    assert do_nhanh._kich_ban(["python", "tools/gate.py", "--quick"]) == "gate.py"
    assert do_nhanh._kich_ban(["python", "-m", "pytest", "-q"]) == "pytest"
    assert do_nhanh._kich_ban(["python", "-c", "x='gate.py'"]) == "", (
        "mot tien trinh chi NHAC ten van duoc coi la dang CHAY no")
    assert do_nhanh._kich_ban(["bash", "-c", "python tools/gate.py"]) == ""

    # Doi chung SONG: mot tien trinh that, chi nhac ten, khong duoc dem.
    moi = subprocess.Popen(
        [sys.executable, "-c",
         "import time; _ = 'tools/gate.py chi la mot chuoi'; time.sleep(20)"])
    try:
        time.sleep(1.5)
        pids = [p.pid for p in do_nhanh.tien_trinh("gate.py")]
        assert moi.pid not in pids, (
            f"tien trinh {moi.pid} chi NHAC 'gate.py' ma bi dem la dang chay no "
            f"— bo loc dang hoi CA DONG LENH chu khong hoi kich ban")
    finally:
        moi.terminate()
        moi.wait(timeout=10)
