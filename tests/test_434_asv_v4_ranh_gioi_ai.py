"""Auto Scan Video V4 — MOT cua goi model, van ban lan thi giac (pha 08).

**§1 mot cua duy nhat** — khong tep nao khac cua ASV duoc goi `dieu_phoi.goi`.
     Hai duong toi cung mot provider la hai duong se lech nhau ve tran token, ve
     chon model, va ve cach doc loi.

**§2 chon model theo NGU NGHIA** — 🔴 va day la cho mot loi da song. Docstring
     cua `dieu_phoi.goi` canh bao rang `{"ltt_llm": "ltt_llm"}` la SAI: `ltt_llm`
     la **bi danh cong khai cua app**, khong phai id model. Truyen no vao thi
     `chon_key` nem `ThieuKeyError` va `goi` **bo qua provider trong im lang**.
     Docstring do ke ten hai nan nhan; `dich_thuat.py:45` la nan nhan thu BA.

**§3 tham quyen tran token** — mot nguon duy nhat: `ltt_llm.ngan_sach`. CLAUDE.md
     ghi mot loi da xay ra that vi go lai con so thu hai.

**§4 dau ra co cau truc** — thieu mot truong bat buoc phai thanh LOI, khong duoc
     thanh `None` di tiep roi no ra o mot giai doan khac duoi mot thong bao
     khong lien quan gi.

**§5 khong co van chuyen AI thu hai** — khong `requests`, khong `httpx`, khong
     `urllib`, khong endpoint may B.

⛔ Khong phep kiem nao goi model that.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import ai

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


def _cay(tep: pathlib.Path) -> ast.Module:
    return ast.parse(tep.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Mot cua duy nhat
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_ai_py_duoc_goi_dieu_phoi():
    """⛔ Moi tep khac phai di qua `ai.goi`.

    ⭐ Quet AST chu khong quet chuoi: chinh docstring cua `ai.py` nhac ten
       `dieu_phoi.goi` nhieu lan de giai thich, va mot phep quet chuoi se bao
       dong tren doan van giai thich no — loi do da xay ra bon lan trong du an.
    """
    xau = []
    for tep in sorted(APP.glob("*.py")):
        if tep.name == "ai.py":
            continue
        for n in ast.walk(_cay(tep)):
            if isinstance(n, ast.Attribute) and n.attr == "goi" and \
                    isinstance(n.value, ast.Name) and n.value.id == "dieu_phoi":
                xau.append(f"{tep.name}:{n.lineno}")
            # ⚠️ Cam DUNG `dieu_phoi`, khong cam ca `platform_core.llm`.
            #
            # 🔴 Ban dau phep kiem nay cam ca goi `platform_core.llm`, va no bat
            #    `loi.py:182` — noi nhap `cong_vlm.AmbiguousProviderError` va
            #    `BanError` de DICH mot ngoai le sang loai cua nen tang. Do la
            #    mot phep doc kieu, khong phai mot duong van chuyen thu hai.
            #
            # ⭐ Mot phep kiem qua rong khong chi bao dong gia — no day nguoi ta
            #    di vong qua chinh no, va luc do no khong con bao ve gi.
            if isinstance(n, ast.ImportFrom):
                mod = n.module or ""
                ten_nhap = {a.name for a in n.names}
                # 🔴 **Hai dang, va ban dau toi chi chan MOT.** Kiem dot bien
                #    chen `from platform_core.llm import dieu_phoi` va phep kiem
                #    van XANH — vi luc do no chi so `mod == "...dieu_phoi"`.
                #    Mot cua chi khoa mot canh la mot cua khong khoa.
                if mod == "platform_core.llm.dieu_phoi" or (
                        mod == "platform_core.llm" and "dieu_phoi" in ten_nhap):
                    xau.append(f"{tep.name}:{n.lineno} import {mod}")
    assert xau == [], f"goi thang dieu phoi thay vi qua `ai.goi`: {xau}"


def test_nam_thao_tac_deu_co_trong_bang():
    """Nam thao tac ma pha 08 yeu cau, khong thieu cai nao."""
    can = {"doc_canh", "ho_so_noi_dung", "chuyen_loi_thoai",
           "rut_ngan_cho_vua", "qc_ngu_nghia"}
    assert can <= set(ai.THEO_MA), sorted(can - set(ai.THEO_MA))


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Chon model theo ngu nghia — va chot lai loi bi danh
# ══════════════════════════════════════════════════════════════════════════════

def test_thao_tac_van_ban_va_thi_giac_ra_HAI_model_khac_nhau():
    van = ai.model_cho(ai.DICH_THUAT)
    thi = ai.model_cho(ai.DOC_CANH)
    assert van != thi, "van ban va thi giac phai ra hai model khac nhau"

    from platform_core import providers
    assert providers.model_capabilities(thi).get("vision") is True
    assert providers.model_capabilities(van).get("vision") is not True


def test_KHONG_go_bi_danh_lam_id_model():
    """🔴 Loi thu BA cua cung mot khuon, chot lai o day.

    `ltt_llm` la bi danh cong khai cua app. Truyen no lam id model thi
    `chon_key` nem `ThieuKeyError`, va `dieu_phoi.goi` doc do la "provider nay
    khong phuc vu duoc, di tiep" — **bo qua provider trong im lang**.
    """
    from platform_core import providers

    id_that = {m.id for m in providers.models_for("ltt_llm")}
    assert "ltt_llm" not in id_that, (
        "neu registry bat dau khai `ltt_llm` la mot id model that thi doc lai "
        "docstring cua `dieu_phoi.goi` — phep chot nay dua tren viec no KHONG la")

    for t in ai.THAO_TAC:
        ban_do = ai.ban_do_model(t)
        for pid, mid in ban_do.items():
            assert mid != pid, (
                f"{t.ma}: truyen bi danh {pid!r} lam id model — dung khuon sai "
                f"ma docstring cua `dieu_phoi.goi` canh bao")
            assert mid in id_that, f"{t.ma}: id {mid!r} khong co trong registry"


def test_khong_tep_nao_cua_ASV_con_go_id_model_noi_bo():
    """⛔ Id noi bo la viec cua registry. Go no o ben goi la mot ban sao se troi.

    ⚠️ `ai.py` duoc mien vi no NHAC hai id trong doan van giai thich loi bi danh
       — nhung no khong duoc GAN chung cho bien nao, va phep kiem duoi day doc
       AST nen no phan biet duoc hai dieu do.
    """
    xau = []
    for tep in sorted(APP.glob("*.py")):
        for n in ast.walk(_cay(tep)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and \
                    n.value in ("qwen38-api", "qwen38-vision"):
                xau.append(f"{tep.name}:{n.lineno}")
    assert xau == [], f"go id model noi bo o ben goi: {xau}"


def test_model_cho_KHONG_roi_ve_mac_dinh_khi_khong_tim_thay(monkeypatch):
    """⛔ Roi ve model van ban cho mot thao tac CAN thi giac se cho ra mot cau
    tra loi trong nhu that ve mot buc anh model chua bao gio nhin thay."""
    from platform_core import providers

    monkeypatch.setattr(providers, "models_for", lambda *a, **k: [])
    with pytest.raises(ai.AiError):
        ai.model_cho(ai.DOC_CANH)


def test_chon_model_ON_DINH_giua_hai_lan_goi():
    """Van tay phu thuoc id model; mot id nhay lam cache truot vo co."""
    assert ai.model_cho(ai.DOC_CANH) == ai.model_cho(ai.DOC_CANH)


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Tham quyen tran token va cua so ngu canh
# ══════════════════════════════════════════════════════════════════════════════

def test_tran_token_lay_tu_ngan_sach_cua_app_CHU():
    from apps.ltt_llm import ngan_sach

    assert ai.tran_token_ra() == int(ngan_sach.mac_dinh_cho("job"))


def test_ASV_khong_go_lai_mot_con_so_token_nao():
    """🔴 CLAUDE.md ghi mot loi da xay ra that: mot hang `1_024` go tay lam
    **moi cau tra loi dai bi cat**. Chot bang su vang mat."""
    xau = []
    for tep in sorted(APP.glob("*.py")):
        for n in ast.walk(_cay(tep)):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, int) and n.value.value >= 1024:
                ten = [t.id for t in n.targets if isinstance(t, ast.Name)]
                if any("token" in x.lower() for x in ten):
                    xau.append(f"{tep.name}:{n.lineno} {ten}")
    assert xau == [], f"go lai hang so token: {xau}"


def test_cua_so_ngu_canh_THI_GIAC_nho_hon_van_ban():
    """🔴 Mot lo khung hinh sap theo tran cua model VAN BAN se thanh 413 luc chay.

    ⚠️ Con so o day la cai registry KHAI. `docs/audit_ltt_llm/STATE.md` tung do
       duoc mot tran THAP HON NHIEU cho ban thi giac; pha 11 phai do lai truoc
       khi sap lo khung hinh theo no.
    """
    assert 0 < ai.cua_so_ngu_canh(ai.DOC_CANH) < ai.cua_so_ngu_canh(ai.DICH_THUAT)


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Dau ra co cau truc
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_duoc_JSON_boc_trong_markdown():
    ra = ai.doc_json('day la ket qua:\n```json\n{"doan": [1, 2]}\n```', ai.DICH_THUAT)
    assert ra == {"doan": [1, 2]}


@pytest.mark.parametrize("xau", [
    "", "   ", "khong co json gi ca", "{ hong", "[1,2,3]", "null",
])
def test_phan_hoi_hong_thi_NEM_chu_khong_tra_ve_rong(xau):
    with pytest.raises(ai.LuocDoSai):
        ai.doc_json(xau, ai.DICH_THUAT)


def test_THIEU_truong_bat_buoc_thi_nem(monkeypatch):
    """⛔ Mot truong thieu thanh `None` di tiep se lo ra o mot giai doan khac,
    duoi mot thong bao khong lien quan gi — va nguoi doc se di tim o nham cho."""
    with pytest.raises(ai.LuocDoSai) as e:
        ai.doc_json('{"khac": 1}', ai.HO_SO_NOI_DUNG)
    assert "the_loai" in str(e.value)


def test_moi_thao_tac_deu_khai_truong_bat_buoc():
    """Mot thao tac khong khai luoc do la mot thao tac khong kiem duoc dau ra."""
    thieu = [t.ma for t in ai.THAO_TAC if not t.truong_bat_buoc]
    assert thieu == [], f"chua khai truong bat buoc: {thieu}"


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Dispatch mo ho
# ══════════════════════════════════════════════════════════════════════════════

class _Gia:
    """Doi tuong `dieu_phoi` gia — khong cham mang."""

    def __init__(self, loi=None, noi_dung='{"doan": []}'):
        self.loi = loi
        self.noi_dung = noi_dung
        self.da_goi = {}

    def goi(self, db, **k):
        self.da_goi = dict(k)
        if self.loi is not None:
            raise self.loi
        class _Kq:
            content = self.noi_dung
            provider = "ltt_llm"
            model = "x"
        return _Kq()


def _tiem(monkeypatch, gia):
    import platform_core.llm.dieu_phoi as dp
    monkeypatch.setattr(dp, "goi", gia.goi)


class AmbiguousProviderError(RuntimeError):
    """Cung TEN voi lop cua nen tang — `ai._la_mo_ho` nhan dien theo ten."""


def test_dispatch_MO_HO_thanh_AiMoHo_chu_khong_phai_loi_thuong(monkeypatch):
    """🔑 Hai loai that bai, hai so phan: `tu choi` thu lai duoc, `mo ho` thi
    khong — vi provider co the da chay va da tinh tien.

    🔴 **Thong diep co y KHONG chua tu khoa nao.** Ban dau no la "mat ket noi
       sau khi gui", va kiem dot bien cho thay phep kiem van XANH khi tat han
       nhanh nhan dien theo TEN LOP — vi nhanh do chuoi bat duoc no. Tuc phep
       kiem dang do lop du phong chu khong do lop chinh.

    ⇒ Mot thong diep trung tinh ep no phai di qua dung nhanh can chot.
    """
    gia = _Gia(loi=AmbiguousProviderError("khong noi gi ca"))
    _tiem(monkeypatch, gia)
    with pytest.raises(ai.AiMoHo):
        ai.goi(None, ai.DICH_THUAT, [{"role": "user", "content": "x"}])


def test_nhanh_du_phong_theo_CHUOI_van_bat_duoc_mo_ho(monkeypatch):
    """Chieu con lai: mot lop khong quen ten nhung thong diep noi ro.

    ⚠️ Nhanh nay la lop CUOI. No ton tai cho ngoai le cua thu vien duoi ma ta
       khong biet ten, va no co the doi nghia ngay khi ai do sua mot thong bao.
    """
    gia = _Gia(loi=RuntimeError("read timeout khi doi phan hoi"))
    _tiem(monkeypatch, gia)
    with pytest.raises(ai.AiMoHo):
        ai.goi(None, ai.DICH_THUAT, [{"role": "user", "content": "x"}])


def test_that_bai_THUONG_thanh_AiError(monkeypatch):
    gia = _Gia(loi=RuntimeError("provider tu choi"))
    _tiem(monkeypatch, gia)
    with pytest.raises(ai.AiError):
        ai.goi(None, ai.DICH_THUAT, [{"role": "user", "content": "x"}])
    # ⛔ Va no KHONG duoc la `AiMoHo` — nham chieu nay se lam mot lan tu choi
    #    bi treo lai cho nguoi quyet dinh, con nham chieu kia thi tra tien hai lan.
    gia2 = _Gia(loi=RuntimeError("provider tu choi"))
    _tiem(monkeypatch, gia2)
    try:
        ai.goi(None, ai.DICH_THUAT, [{"role": "user", "content": "x"}])
    except ai.AiError as exc:
        assert not isinstance(exc, ai.AiMoHo)


def test_goi_truyen_dung_id_model_va_tran_token(monkeypatch):
    gia = _Gia()
    _tiem(monkeypatch, gia)
    ai.goi(None, ai.DOC_CANH, [{"role": "user", "content": "x"}])

    assert gia.da_goi["model_theo_provider"] == {"ltt_llm": ai.model_cho(ai.DOC_CANH)}
    assert gia.da_goi["max_tokens"] == ai.tran_token_ra()
    assert gia.da_goi["thu_tu_provider"] == ai.THU_TU_PROVIDER


def test_HUY_thi_khong_goi_model(monkeypatch):
    """⛔ Bam huy roi ma van goi la tieu tien cho mot ket qua se bi vut."""
    gia = _Gia()
    _tiem(monkeypatch, gia)

    class Ctx:
        def is_cancelled(self):
            return True

    with pytest.raises(ai.AiError):
        ai.goi(None, ai.DICH_THUAT, [{"role": "user", "content": "x"}], ctx=Ctx())
    assert gia.da_goi == {}, "da huy ma van goi model"


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Khong co van chuyen AI thu hai
# ══════════════════════════════════════════════════════════════════════════════

def test_ASV_khong_import_thu_vien_HTTP_nao():
    """⛔ Khong `requests`, `httpx`, `urllib`, `aiohttp`, `socket`.

    ⚠️ `subprocess` duoc phep — `demucs_runner`/ffmpeg la tien trinh con cuc bo,
       khong phai mot van chuyen AI thu hai.
    """
    cam = {"requests", "httpx", "urllib", "urllib3", "aiohttp", "http.client",
           "socket", "websocket", "websockets"}
    xau = []
    for tep in sorted(APP.rglob("*.py")):
        for n in ast.walk(_cay(tep)):
            ten = []
            if isinstance(n, ast.Import):
                ten = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                ten = [n.module or ""]
            for t in ten:
                goc = (t or "").split(".")[0]
                if goc in cam or t in cam:
                    xau.append(f"{tep.name}:{n.lineno} {t}")
    assert xau == [], f"van chuyen AI thu hai: {xau}"


def test_ASV_khong_go_endpoint_may_B():
    """Dia chi may B la viec cua registry, khong phai cua mot app."""
    xau = []
    for tep in sorted(APP.rglob("*.py")):
        van = tep.read_text(encoding="utf-8")
        for dau in ("192.168.2.66", ":8299", ":8199", "http://192.168"):
            if dau in van:
                xau.append(f"{tep.name}: {dau}")
    assert xau == [], f"go endpoint may B: {xau}"


def test_bo_do_HTTP_that_su_bat_duoc():
    """⭐ Chung minh phep kiem tren khong phai mot den xanh noi vao khong."""
    mau = "import requests\nx = requests.get('http://a')\n"
    cay = ast.parse(mau)
    thay = [a.name for n in ast.walk(cay) if isinstance(n, ast.Import)
            for a in n.names]
    assert "requests" in thay


# ══════════════════════════════════════════════════════════════════════════════
#  §7  Phien ban prompt/luoc do di vao van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_co_phien_ban_prompt_va_luoc_do():
    """⛔ Thieu no thi doi mot cau prompt xong, cache van khop, va lan chay dung
    lai ket qua sinh boi prompt CU — mot thay doi san pham khong bao gio toi
    khach."""
    assert isinstance(ai.PHIEN_BAN_PROMPT, int) and ai.PHIEN_BAN_PROMPT >= 1
    assert isinstance(ai.PHIEN_BAN_LUOC_DO, int) and ai.PHIEN_BAN_LUOC_DO >= 1

# =============================================================================
#  BAN khong duoc bien thanh HONG tren duong AI
# =============================================================================

def test_provider_BAN_di_het_duong_thanh_resource_wait(monkeypatch):
    """🔴 **Bai nay noi BON tang, va do la ly do no ton tai.**

    Ngay 05/09 va 06/09, hai luot nghiem thu THAT chet vi may B tra "ban":
    `content_process failed_terminal`, roi chin bai do voi nhung cau nhu
    `assert 404 == 200`. Khong cau nao nhac toi may B.

    Nguyen nhan: `ai.goi` boc MOI ngoai le thanh `AiError`, lam mat lop
    `KhongCoProviderNao`. Tu do ba tang duoi deu doc sai, va job **khong bao
    gio duoc hoan**.

    ⛔ Da co mot chot cho dieu nay o `test_448`, va no **xanh trong khi san
       pham hong**: no dung `KhongCoProviderNao` TU DUNG BANG TAY, tuc no bo qua
       dung cai lop da lam mat tin hieu. Mot bai kiem tu dung dau vao chi kiem
       duoc phia tieu thu.

    ⭐ Nen bai nay bat dau tu **ranh gioi that** (`dieu_phoi.goi`) va di het
       duong toi phan quyet cua nen tang. No khong duoc phep biet ten lop trung
       gian nao.
    """
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.llm.dieu_phoi import KhongCoProviderNao

    from apps.auto_scan_video import ai, loi

    def ban(*a, **kw):
        raise KhongCoProviderNao(["ltt_llm: ban"])

    # `ai.goi` nhap `dieu_phoi` BEN TRONG ham, nen va vao chinh module do
    #  — do cung la ranh gioi that: moi thu ben trong no la thu ta dang do.
    from platform_core.llm import dieu_phoi
    monkeypatch.setattr(dieu_phoi, "goi", ban)

    with pytest.raises(Exception) as ei:
        ai.goi(None, ai.QC_NGU_NGHIA, [{"role": "user", "content": "x"}])
    exc = ei.value

    assert loi.phan_loai(exc) == loi.BAN, (
        f"ASV phan loai mot provider BAN thanh {loi.phan_loai(exc)!r} — "
        "'ban' se di tiep nhu mot lan chay hong")

    nen = loi.dich_sang_loi_nen_tang(exc)
    assert _provider_failure_kind(nen, provider_state="") == ("resource_wait", 20), (
        "nen tang khong doc ra 'cho tai nguyen' — job se tieu luot thu va "
        "chet thay vi ve hang doi")


def test_ban_MOT_PHAN_khong_duoc_tinh_la_ban(monkeypatch):
    """⚠️ Nua khong the thieu: chi `busy_only` moi la ban.

    Neu mot provider ban con mot cai thieu `base_url`, do la mot loi **cau
    hinh** dang nap minh sau chu "ban". Hoan lai mai se khong bao gio sua duoc
    no — lan chay se treo den het ngan sach roi chet, va thong bao se do loi
    cho mot may dang ranh.
    """
    from platform_core.llm.dieu_phoi import KhongCoProviderNao

    from apps.auto_scan_video import ai, loi

    def lung_tung(*a, **kw):
        raise KhongCoProviderNao(["ltt_llm: ban",
                                  "gemini: thieu base_url (ca o khoa lan o registry)"])

    from platform_core.llm import dieu_phoi
    monkeypatch.setattr(dieu_phoi, "goi", lung_tung)

    with pytest.raises(Exception) as ei:
        ai.goi(None, ai.QC_NGU_NGHIA, [{"role": "user", "content": "x"}])

    assert loi.phan_loai(ei.value) != loi.BAN, (
        "mot loi cau hinh duoc doc thanh 'ban' — lan chay se cho mai mot thu "
        "khong bao gio tu het")

