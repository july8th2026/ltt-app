"""test_1248 — CHI MOT cua stream that, va moi bao ve gan MOT lan.

## Su co goc (L-08, 13/09/2026) — vi sao tep nay ton tai

`server/api/streaming.py` co BA `StreamingResponse`:

    1. sandbox   — khoa thu, khong cham GPU, khong cham so tien (co Y khac)
    2. phong cho — tool khai ngan sach KV  ⇒ **`ltt-3.8` di loi NAY**
    3. duong cu  — tool khong khai ngan sach KV

BA ban va lien tiep cua L-08 deu gan vao cua 3. Production di cua 2. Ca ba ban
va deu **dung ve ky thuat** va deu **khong cham vao luot that mot lan nao**.

⇒ Khuyet tat khong nam trong ban va. No nam o chuyen **co hai cua lam cung mot
  viec, va mot nguoi sua chi nhin thay mot cua**. Them lop bao ve thu tu cung se
  lap lai dung chuyen ay.

## Bo nay chot DIEU KIEN CAU TRUC, khong chot mot bang chep tay

Chep tay thi se cu. Nen moi ve o day doc THANG tu ma nguon:

| ve | no chan dieu gi |
|---|---|
| `test_chi_mot_cua_that` | them cua thu tu ma quen bao ve |
| `test_moi_cua_that_deu_co_BA_LOP` | gan bao ve le mot cua |
| `test_cat_luc_DANG_XEP_HANG_khong_nha_suat_cua_ai` | nha bua khi chua co suat |
"""
import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
STREAMING = GOC / "server" / "api" / "streaming.py"


def _cac_lenh_tra_stream() -> list[ast.Call]:
    """Moi `return StreamingResponse(...)` trong tep, doc bang AST."""
    cay = ast.parse(STREAMING.read_text(encoding="utf-8"))
    ra = []
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Return) or not isinstance(nut.value, ast.Call):
            continue
        if getattr(nut.value.func, "id", "") == "StreamingResponse":
            ra.append(nut.value)
    return ra


def _la_cua_sandbox(goi: ast.Call) -> bool:
    """Cua sandbox duoc mien: no khong cham GPU nen khong co suat de nha."""
    return "_luong_thu" in ast.dump(goi)


def test_chi_mot_cua_that():
    """🔴 Sau khi gop: dung MOT cua that (+ mot cua sandbox duoc mien).

    ⛔ Ve nay DO khi ai do them mot `return StreamingResponse(...)` moi. Do la
       co Y: them cua la viec lon, phai doc tep nay truoc, khong duoc lam len.
    """
    that = [g for g in _cac_lenh_tra_stream() if not _la_cua_sandbox(g)]
    assert len(that) == 1, (
        f"co {len(that)} cua stream THAT trong streaming.py, doi 1. "
        "Hai cua lam cung mot viec la dung khuon da de ra L-08: ba ban va gan "
        "vao cua nay trong khi production di cua kia. Gop lai, dung them lop.")


def test_cua_that_co_DU_BA_LOP():
    """Moi bao ve phai co mat NGAY TAI cho tra phan hoi, doc bang AST."""
    that = [g for g in _cac_lenh_tra_stream() if not _la_cua_sandbox(g)]
    assert that, "khong tim thay cua stream that nao"

    # ⛔ MOI cua, khong phai `that[0]`. Ban dau ve nay chi kiem cua dau tien va
    #    no XANH — vi cua dau tien tinh co la cua DA co bao ve, con cua production
    #    di thi khong. Mot phep kiem chi soi mot nua thi no bo sot dung nua kia.
    for i, goi in enumerate(that):
        van = ast.dump(goi)
        assert "bat_dong_bo_hoa" in van, (
            f"cua that #{i}: than phan hoi khong di qua `bat_dong_bo_hoa` ⇒ "
            "Starlette boc bang `iterate_in_threadpool`, generator dong bo bi bo "
            "roi khi khach cat, va `with keep_alive` khong bao gio thoat. L-08.")
        assert "background" in {kw.arg for kw in goi.keywords}, (
            f"cua that #{i}: khong co `background=` ⇒ KHONG co "
            "`dam_bao_quyet_toan` va KHONG co duong nha suat du phong. Cua phong "
            "cho da thieu dung thu nay.")


def test_khi_dut_duoc_truyen_vao_than_phan_hoi():
    """Lop 1 phai duoc NOI, khong chi ton tai.

    ⚠️ So tay du an co nguyen mot muc cho lop loi nay: *"nang luc co, nhung
       khong ai di tren duong"*. Mot `khi_dut` khong duoc truyen thi khong phai
       mot lop bao ve.
    """
    for i, goi in enumerate(g for g in _cac_lenh_tra_stream()
                            if not _la_cua_sandbox(g)):
        bat = next((a for a in goi.args
                    if isinstance(a, ast.Call)
                    and getattr(a.func, "attr", "") == "bat_dong_bo_hoa"), None)
        assert bat is not None, f"cua that #{i}: `bat_dong_bo_hoa` khong phai than"
        assert len(bat.args) >= 3, (
            f"cua that #{i}: `bat_dong_bo_hoa` chi nhan {len(bat.args)} doi so — "
            "thieu `khi_dut`. Khong co no thi viec nha suat lai treo vao `finally` "
            "cua generator, dung cho Starlette khong bao dam (`responses.py:250`).")
