"""test_1242 — bo do TROI BAN may B doc tuyen dung. L-07, 13/09/2026.

`tools/soi_troi_may_b.py` tra loi mot cau: *"duong nao CAY co ma MAY B khong?"*.
Cau ay khong ai hoi trong bon ngay, va het bon ngay do la mot su co 32 phut.

Bo nay chi canh **mot nua** cua cong cu ay: phan doc tuyen tu cay. Nua kia (hoi
may B) khong chot duoc o day va khong nen chot — no doi mang va doi may B bat,
va mot phep kiem doi hai thu do la mot phep kiem se bi tat.

## Vi sao doc bang AST, va vi sao dieu do dang mot phep kiem

⛔ `import` khong dung duoc: `api.py` dung app tu cau hinh, nen mot lan import
   hong vi thieu bien moi truong bien bo do thanh bo do khong chay duoc.
⛔ `regex` khong dung duoc: mot chuoi `@app.post(` trong CHU THICH cung khop, va
   khi ay bo do bao thieu mot duong chua bao gio ton tai.

Hai menh de ay la thu bo nay do.
"""
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))

from soi_troi_may_b import CAC_CONG, tuyen_trong_cay  # noqa: E402


@pytest.mark.parametrize("ten", sorted(CAC_CONG))
def test_doc_duoc_tuyen_that_cua_tung_cong(ten):
    """Moi cong khai phai doc ra duoc mot tap KHONG RONG.

    Mot tap rong khong lam bo do do — no lam bo do bao "khop" voi moi thu, tuc
    mot phep kiem luon xanh. Do la kieu hong te nhat cua mot bo do.
    """
    tep = CAC_CONG[ten][0]
    duong = tuyen_trong_cay(tep)
    assert duong, f"{tep}: khong doc duoc tuyen nao"
    assert all(d.startswith("/") for d in duong), duong


def test_duong_da_gay_L07_co_trong_tap_doc_duoc():
    """Chot dung duong da 404 va gay su co.

    Neu mot lan doi cau truc lam bo doc tuyen bo sot `/v1/nha_comfy`, bo do se
    im lang **dung o cho no sinh ra de canh**.
    """
    assert "/v1/nha_comfy" in tuyen_trong_cay("render_gateway/api.py")


def test_khong_khop_vao_chuoi_trong_chu_thich(tmp_path):
    """⛔ Doi chung cho lua chon AST: mot `@app.post("/bay")` nam trong chu thich
    hoac trong mot chuoi KHONG duoc tinh la tuyen.

    Mot ban regex se dem no, roi bao may B "thieu /bay" — mot bao dong gia cho
    mot duong chua bao gio ton tai.
    """
    import soi_troi_may_b as M

    tep = tmp_path / "gia_api.py"
    tep.write_text(
        'def dung(app):\n'
        '    # @app.post("/bay-trong-chu-thich")\n'
        '    _ = """@app.get("/bay-trong-chuoi")"""\n'
        '    @app.post("/that")\n'
        '    def f():\n'
        '        return 1\n', encoding="utf-8")
    goc_cu = M.GOC
    try:
        M.GOC = tmp_path
        ra = M.tuyen_trong_cay("gia_api.py")
    finally:
        M.GOC = goc_cu
    assert ra == {"/that"}, ra


def test_bo_qua_chi_chua_duong_cua_framework():
    """Danh sach `BO_QUA` la cho mot phep kiem chet dan: moi ten them vao la
    bot mot cau hoi. Chot lai kich thuoc de viec noi rong no phai co y thuc."""
    import soi_troi_may_b as M

    assert M.BO_QUA <= {"/openapi.json", "/docs", "/redoc",
                        "/docs/oauth2-redirect"}, (
        "them duong vao BO_QUA la bot mot cau hoi — phai co ly do, va ly do "
        "phai la 'duong nay KHONG BAO GIO o tren may B'")
