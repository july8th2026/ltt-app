"""V6 — ngan sach token/thoi gian cua tung thao tac, va duong tra tien mang no.

## Loi that, va no la mot ca "duong co, khong ai di tren duong"

09/09 `chuyen_loi_thoai` hong **6/6** o mot lo 12 doan. Bon phien lien tiep doc
dong `"model tra ve rong"` thanh "may B hong"; do 30 luot goi that vao may B thi
**0/30 hong**. Nguyen nhan la mot tran nam DUOI san nhu cau:

    tran token   4.096  vs  lon nhat quan sat 10.248   vuot 2,5x
    timeout       120s  vs  lon nhat quan sat  151,0s  vuot 1,26x

Va cai lam no song lau la o tang **noi day**: `ai.goi` DA nhan `max_tokens` va
`timeout_s`, nhung `ai.goi_tinh_tien` — cua duy nhat cua moi lan goi co tinh
tien, va la cua ma ca bon giai doan di qua — **khong truyen chung xuong**. Tham
so co san o mot ham ngay ben duoi va khong ai voi toi.

## Bon nhom, va nhom §2 la nhom giu bat bien

  §1  bang ngan sach co dung khong          — con so, va CACH dat con so
  §2  bat bien "token va timeout di doi"    — ep thanh CO HOC, khong phai giao uoc
  §3  duong tra tien co MANG ngan sach khong — AST
  §4  co ai DANG di tren duong do khong      — goi that, bat tham so tai cho

⛔ §4 la nhom duy nhat khong the xanh-rong. Ba nhom kia doc ma; nhom nay chan
   mot loi goi that va doc con so **den tay `dieu_phoi`**.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from apps.auto_scan_video import ai

#: Lon nhat quan sat duoc, tu
#: `docs/auto_scan_video_v4/evidence/20260909_tran_token_ra_chuyen_loi_thoai.md`
#: (lo 12, 3 vong, ca hai rao da noi).
DA_DO_TOKEN = 10_248
DA_DO_GIAY = 151.0
#: ~70 token/giay, do duoc va tuyen tinh sach trong cung bao cao do.
TOKEN_MOI_GIAY = 70.0


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Bang ngan sach
# ══════════════════════════════════════════════════════════════════════════════

def test_thao_tac_DA_DO_co_ngan_sach_rieng():
    """`chuyen_loi_thoai` la thao tac da hong that va da duoc do."""
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    assert tran > 0 and cho is not None


def test_tran_VUOT_gia_tri_lon_nhat_QUAN_SAT_duoc():
    """🔑 Va day la cho dat con so, khong phai con so.

    Bao cao 09/09 ban dau rut ra `ra(n) ~ 310 + 828n` tu HAI vong, roi vong thu
    ba lat no: `max(lo 6) = 7.915` **lon hon** `min(lo 12) = 6.948`. Hai phan bo
    chong len nhau ⇒ do doc theo co lo khong tach duoc khoi nhieu.

    ⇒ Ket luan cua chinh bao cao: dat tran theo **gia tri lon nhat quan sat
      duoc kem bien**, khong theo mot cong thuc tuyen tinh chua du mau.
    """
    tran, _ = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    assert tran > DA_DO_TOKEN, (
        f"tran {tran} khong vuot gia tri lon nhat quan sat {DA_DO_TOKEN}")
    assert tran >= DA_DO_TOKEN * 1.3, "vuot roi nhung khong con bien nao"


def test_timeout_VUOT_gia_tri_lon_nhat_QUAN_SAT_duoc():
    _, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    assert cho > DA_DO_GIAY and cho >= DA_DO_GIAY * 1.5


def test_thao_tac_CHUA_do_thi_theo_mac_dinh_nen_tang():
    """⛔ Khong khai bua cho moi thao tac. Mot con so khong ai do la mot con so
    se duoc tin — va `doc_canh` chi ton ~1.258 token mot luot."""
    tran, cho = ai.ngan_sach_cho(ai.DOC_CANH)
    assert (tran, cho) == (0, None)


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Bat bien: token va timeout khong duoc giao le
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_muc_deu_khai_DU_HAI_rao():
    """⛔ Bat bien bao cao 09/09 ghim lai:

        "Khong bao gio giao tran token ma khong giao tran timeout cung luot."

    Vi hau qua khong phai "sua duoc it hon" ma **sua xong he TE DI**: hong it lan
    hon, nhung moi lan hong dat hon — `LuocDoSai` chi thu lai, con cham tran thoi
    gian cho ra `AiMoHo`, thu DUNG lan chay va doi nguoi.

    ⭐ Mot `tuple` hai o lam mot nua **khong the** giao mot minh. Bai nay chot
       rang khuon do khong bi noi long thanh hai bang roi rac.
    """
    for ma, muc in ai.NGAN_SACH_RA.items():
        assert isinstance(muc, tuple) and len(muc) == 2, f"{ma}: khong phai cap"
        tran, cho = muc
        assert tran > 0, f"{ma}: khai tran token nhung khong khai timeout"
        assert cho > 0, f"{ma}: khai timeout nhung khong khai tran token"


def test_timeout_DU_CHO_tran_token_chay_het():
    """🔑 Hai rao KHONG doc lap — bao cao do ~70 token/giay, tuyen tinh sach.

    Mot tran token 16.384 can ~234 giay de sinh het. Neu timeout dat 200 giay
    thi ta vua **tao ra lai** rao thu hai o dung cho vua go rao thu nhat, va lan
    nay no ra `AiMoHo` — hang loi NANG hon.
    """
    for ma, (tran, cho) in ai.NGAN_SACH_RA.items():
        can = tran / TOKEN_MOI_GIAY
        assert cho >= can, (
            f"{ma}: tran {tran} token can ~{can:.0f}s de sinh het, "
            f"nhung timeout chi {cho}s — rao thu hai se cham truoc")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Duong tra tien co MANG ngan sach khong
# ══════════════════════════════════════════════════════════════════════════════

def test_goi_tinh_tien_TRUYEN_ngan_sach_xuong_goi():
    """⛔ Day la phep kiem bat dung ca da song 09/09.

    `ai.goi` da nhan `max_tokens`/`timeout_s`. `ai.goi_tinh_tien` thi khong
    truyen — va no la cua ma bon giai doan that su di qua. Nang luc dung, phep
    kiem xanh, khong ai di tren duong.
    """
    cay = ast.parse(inspect.getsource(ai.goi_tinh_tien))
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name)
                and nut.func.id == "goi"):
            ten = {k.arg for k in nut.keywords}
            assert {"max_tokens", "timeout_s"} <= ten, (
                f"`goi_tinh_tien` goi `goi` ma khong mang ngan sach: {sorted(ten)}")
            return
    pytest.fail("khong tim thay loi goi `goi` trong `goi_tinh_tien`")


def test_KHONG_go_lai_con_so_cua_nen_tang():
    """⛔ `ai.tran_token_ra` phai van doc `ltt_llm.ngan_sach`, khong duoc thay
    bang mot hang so cua rieng ASV. Bang §1 la ngan sach RIENG cho vai thao tac
    da do; no khong duoc bien thanh mot ban sao thu hai cua mac dinh nen tang."""
    ma = inspect.getsource(ai.tran_token_ra)
    assert "ngan_sach.mac_dinh_cho" in ma


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Co ai DANG di tren duong do khong — bat tham so tai cho
# ══════════════════════════════════════════════════════════════════════════════

def test_dieu_phoi_NHAN_dung_hai_con_so(monkeypatch):
    """Goi that qua `ai.goi`, chan o `dieu_phoi.goi` va doc con so den tay no.

    ⭐ Ba bai o §1–§3 deu doc MA. Bai nay doc thu **den tay nguoi nhan** — no la
       bai duy nhat khong the xanh khi mot khau noi o giua lam roi mat tham so.
    """
    from platform_core.llm import dieu_phoi

    da_nhan: dict = {}

    def _gia(db, **kw):
        da_nhan.update(kw)
        return {"noi_dung": "{}", "provider": "ltt_llm", "model": "m",
                "su_dung": {"so_luong": 1}, "finish_reason": "stop"}

    monkeypatch.setattr(dieu_phoi, "goi", _gia)
    monkeypatch.setattr(ai, "ban_do_model", lambda t: {"ltt_llm": "m"})

    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    ai.goi(None, ai.CHUYEN_LOI_THOAI, [{"role": "user", "content": "x"}],
           max_tokens=tran, timeout_s=cho)

    assert da_nhan.get("max_tokens") == tran
    assert da_nhan.get("timeout_s") == cho


def test_thao_tac_KHONG_khai_thi_dieu_phoi_giu_mac_dinh(monkeypatch):
    """⛔ Doi chung cho bai tren. Neu `timeout_s` luon duoc gui thi bai kia xanh
    ma khong chung minh duoc rang bang §1 co tac dung — no chi chung minh rang
    ta luon gui mot con so nao do.

    ⚠️ Va vang mat phai la VANG MAT, khong phai `None`: `ai.goi` chi them khoa
       khi ben goi KHAI, vi truyen `timeout_s=None` xuong se de len mac dinh cua
       `dieu_phoi` mot gia tri khong hop le.
    """
    from platform_core.llm import dieu_phoi

    da_nhan: dict = {}

    def _gia(db, **kw):
        da_nhan.update(kw)
        return {"noi_dung": "{}", "provider": "ltt_llm", "model": "m",
                "su_dung": {"so_luong": 1}, "finish_reason": "stop"}

    monkeypatch.setattr(dieu_phoi, "goi", _gia)
    monkeypatch.setattr(ai, "ban_do_model", lambda t: {"ltt_llm": "m"})

    tran, cho = ai.ngan_sach_cho(ai.DOC_CANH)
    ai.goi(None, ai.DOC_CANH, [{"role": "user", "content": "x"}],
           max_tokens=tran, timeout_s=cho)

    assert "timeout_s" not in da_nhan, "gui `timeout_s` cho ca thao tac chua do"
    assert da_nhan.get("max_tokens") == ai.tran_token_ra()
# ══════════════════════════════════════════════════════════════════════════════
#  §5  SO CAI phai giu duoc thu phan biet HAI che do hong
# ══════════════════════════════════════════════════════════════════════════════

def test_so_cai_GHI_finish_reason_va_hai_do_dai(monkeypatch):
    """🔑 Hai trieu chung khac han nhau, cung bieu hien ra ngoai la "lo hong":

        finish = "length"               -> TRAN CON THAP   -> noi tran
        finish = "stop" + content rong  -> CHE DO RONG     -> thu lai

    Hai ban sua khac nhau, va **khong truong nao khac phan biet duoc chung**.

    ⛔ `ai.goi` da tra ve `finish_reason` va `suy_nghi` tu 09/09 — nhung truoc
       pha 11 khong cho nao LUU chung. Nang luc co, khong ai di tren duong: sau
       nay, khi khong con ai ngoi do, khong co cach nao phan biet hai che do tu
       du lieu van hanh.

    ⭐ Bai nay chan `sd.ghi` va doc **but toan that su duoc ghi**, khong doc AST:
       cau can hoi la *"dong ma do co CHAY khong"*, khong phai *"co dong ma do
       khong"* — bai hoc `test_465` da tra gia.
    """
    from apps.auto_scan_video import su_dung as sd

    da_ghi: dict = {}

    def _ghi_gia(db, run, *, stage, item_key, su_dung):
        da_ghi["su_dung"] = su_dung

    monkeypatch.setattr(sd, "ghi", _ghi_gia)
    monkeypatch.setattr(ai, "goi", lambda *a, **k: {
        "noi_dung": "", "provider": "ltt_llm", "model": "m", "su_dung": None,
        "finish_reason": "length", "suy_nghi": "x" * 22016})

    class _Run:
        id = "r1"
        owner_id = "u1"

    ai.goi_tinh_tien(object(), _Run(), ai.CHUYEN_LOI_THOAI, [],
                     stage="content_process", item_key="lo1")

    gc = dict(getattr(da_ghi["su_dung"], "ghi_chu", None) or {})
    assert gc.get("finish_reason") == "length", gc
    assert gc.get("noi_dung_ky_tu") == 0, gc
    assert gc.get("suy_nghi_ky_tu") == 22016, gc


def test_so_cai_KHONG_luu_NGUYEN_VAN_khoi_suy_nghi(monkeypatch):
    """⛔ Doi chung cho bai tren, va no la mot chot RIENG TU.

    `suy_nghi` cua model dai hang chuc nghin ky tu va co the mang nguyen van
    doan hoi thoai cua khach. So cai — thu duoc doc lai de doi soat tien — khong
    phai cho de no nam. Ghi **do dai**, khong ghi noi dung.
    """
    from apps.auto_scan_video import su_dung as sd

    BI_MAT = "doan hoi thoai rieng tu cua khach hang"
    da_ghi: dict = {}

    def _ghi_gia(db, run, *, stage, item_key, su_dung):
        da_ghi["su_dung"] = su_dung

    monkeypatch.setattr(sd, "ghi", _ghi_gia)
    monkeypatch.setattr(ai, "goi", lambda *a, **k: {
        "noi_dung": BI_MAT, "provider": "ltt_llm", "model": "m",
        "su_dung": None, "finish_reason": "stop", "suy_nghi": BI_MAT})

    class _Run:
        id = "r1"
        owner_id = "u1"

    ai.goi_tinh_tien(object(), _Run(), ai.CHUYEN_LOI_THOAI, [],
                     stage="content_process", item_key="lo1")

    import json
    goi = json.dumps(dict(getattr(da_ghi["su_dung"], "ghi_chu", None) or {}),
                     ensure_ascii=False)
    assert BI_MAT not in goi, "so cai dang giu nguyen van noi dung cua khach"
