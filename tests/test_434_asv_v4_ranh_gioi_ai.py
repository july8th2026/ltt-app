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

class _M:
    """Model gia cho registry — chi can `.id`."""

    def __init__(self, mid):
        self.id = mid


def _tiem_registry(monkeypatch, ban: dict):
    """`{id: {"vision": bool}}` → `models_for` + `model_capabilities`.

    ⛔ Phai tiem CA HAI: `model_cho` doc danh sach tu `models_for` roi hoi kha
       nang qua `model_capabilities`. Tiem mot nua thi phep do van sai — va no
       sai theo huong XANH, vi nua kia tra ve du lieu that.
    """
    from platform_core import providers

    monkeypatch.setattr(providers, "models_for",
                        lambda *a, **k: [_M(mid) for mid in ban])
    monkeypatch.setattr(providers, "model_capabilities",
                        lambda mid: dict(ban.get(mid) or {}))


def test_thao_tac_THI_GIAC_luon_ra_mot_model_co_thi_giac():
    """Rang buoc THAT, va no chi co mot chieu.

    🔴 BAN TRUOC DOI CA CHIEU NGUOC: *"van ban va thi giac phai ra HAI
       model khac nhau"*, kem `assert ...(van).get("vision") is not True`. Do la
       mot **bat bien giua hai con so cua hai may khac nhau** — tuc mot su trung
       hop dang cho lat, khong phai bat bien:

         * Truoc 11/09 no dung vi may B chay hai HO SO cua cung mot model, va ho
           so thi giac la mot ban rieng.
         * Tu Task 3.3 `qwen38-api` tu nap mmproj ⇒ CA HAI model cong khai deu
           khai `vision` ⇒ ve `is not True` do, va `model_cho` cu con nem
           `AiError` cho MOI thao tac van ban.

    ⭐ Thu ASV that su can: **thao tac doc anh khong bao gio duoc phuc vu boi
       model khong doc duoc anh.** "Van ban phai di model khac" thi khong —
       chay van ban tren mot model co mmproj chi la mmproj ngoi khong.
    """
    from platform_core import providers

    id_that = {m.id for m in providers.models_for("ltt_llm")}
    for t in ai.THAO_TAC:
        mid = ai.model_cho(t)
        assert mid in id_that, f"{t.ma}: {mid!r} khong co trong registry"
        if t.can_thi_giac:
            assert providers.model_capabilities(mid).get("vision") is True, (
                f"{t.ma} can thi giac ma {mid!r} khong khai `vision`")


def test_MOI_model_deu_co_thi_giac_thi_van_ban_VAN_chay(monkeypatch):
    """Ca hoi quy cho Task 3.3 — dung hinh dang lam ban truoc no.

    ⛔ Khong co ca nay, phep kiem o tren xanh tren registry hom nay va do o
       ngay `qwen38-api` bat mmproj. Tiem thang hinh dang cua ngay ay.
    """
    _tiem_registry(monkeypatch, {"qwen38-api": {"vision": True},
                                 "qwen35-api": {"vision": True}})
    assert ai.model_cho(ai.DICH_THUAT) in {"qwen38-api", "qwen35-api"}
    assert ai.model_cho(ai.DOC_CANH) in {"qwen38-api", "qwen35-api"}


def test_DOI_CHUNG_thi_giac_khong_nhan_model_KHONG_doc_duoc_anh(monkeypatch):
    """Model app khai khong co thi giac ⇒ phai di tim model khac, khong lang le
    tra ve no; va khong ai co thi giac ⇒ `AiError`, khong roi ve mac dinh.

    ⛔ Day la ca giu cho rang buoc con RANG. Neu `model_cho` doi thanh "cu tra
       ve thu app khai" thi hai ca tren van xanh — chi ca nay do.
    """
    import pytest as _pt
    from platform_core.llm import canonical

    khai = canonical.ALIAS_SANG_ID[canonical.model_noi_bo_cua(ai.SLUG)]
    khac = next(m for m in canonical.ALIAS_SANG_ID.values() if m != khai)

    _tiem_registry(monkeypatch, {khai: {}, khac: {"vision": True}})
    assert ai.model_cho(ai.DOC_CANH) == khac
    assert ai.model_cho(ai.DICH_THUAT) == khai      # van ban van theo ban khai

    _tiem_registry(monkeypatch, {khai: {}, khac: {}})
    with _pt.raises(ai.AiError):
        ai.model_cho(ai.DOC_CANH)


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


def test_cua_so_ngu_canh_LAY_DUNG_MODEL_CUA_TUNG_THAO_TAC():
    """Mỗi thao tác phải đọc cửa sổ của **đúng model nó sẽ gọi**.

    🔴 PHÉP KIỂM NÀY THAY MỘT PHÉP KIỂM ĐÃ LẬT CHIỀU (12/09/2026, dual-model).

       Bản trước khẳng định *cửa sổ thị giác ≤ cửa sổ văn bản*, và nó canh một
       mối nguy có thật **của thời đó**: hai hồ sơ là hai bản của **cùng một
       model** (`qwen38-api` 131.072 so với `qwen38-vision` 65.536), nên xếp một
       lô khung hình theo trần của bản văn bản sẽ thành 413 lúc chạy.

       Nay hai thao tác đi tới **hai model khác nhau trên hai card khác nhau**,
       và quan hệ giữa hai cửa sổ **đã lật** — mối nguy cũ biến mất cùng nó.

    ⚠️ Và đừng viết *thao tác nào đi model nào* vào đây: bản trước của chú
       thích này ghi "thị giác → `ltt-3.5`, văn bản → `ltt-3.8`" và câu ấy sống
       đúng **một ngày**. Phép chia ấy là hệ quả của một bộ lọc `vision` đã bị
       bỏ (§2): từ D09, **cả hai** thao tác đi model mà app **khai**, và chỉ
       thao tác thị giác mới rẽ sang model khác khi model ấy không đọc được ảnh.

    ⛔ Cách sai là đảo dấu cho nó xanh lại. Một phép đo lệch chiều thì phải BỎ,
       không phải sửa — đảo dấu chỉ ghim ngược lại đúng một quan hệ ngẫu nhiên
       giữa hai con số, và nó sẽ lật lần nữa ngày ai đó đổi ngữ cảnh một model.

    ⭐ Thứ **luôn** đúng, và là thứ mối nguy cũ thật sự nói tới: đừng đo một
       thao tác bằng cửa sổ của model **khác**. Nên phép kiểm nay hỏi thẳng điều
       đó cho TỪNG thao tác, và nó bất biến với việc model nào lớn hơn.
    """
    from platform_core import providers

    for tt in (ai.DOC_CANH, ai.DICH_THUAT):
        model = ai.model_cho(tt)
        khai = (providers.model_capabilities(model) or {}).get("context_window")
        assert khai, f"{tt.ma}: registry khong khai context_window cho {model!r}"
        assert ai.cua_so_ngu_canh(tt) == int(khai), (
            f"{tt.ma} doc cua so cua mot model KHAC: "
            f"{ai.cua_so_ngu_canh(tt)} != {khai} cua {model!r}")


def test_DOI_CHUNG_hai_thao_tac_di_hai_model_thi_ra_HAI_cua_so(monkeypatch):
    """Đối chứng cho phép kiểm trên: `cua_so_ngu_canh` phải đi **theo** model
    của từng thao tác, chứ không đọc một model cố định.

    Không có ca này thì phép kiểm trên vẫn xanh cả khi `cua_so_ngu_canh` bỏ
    tham số `thao_tac` và luôn hỏi một model — lúc đó nó chỉ so một con số
    với chính nó.

    🔴 BẢN TRƯỚC ĐÒI HAI THAO TÁC **THẬT SỰ** TRỏ HAI MODEL, và đó là một
       điều kiện nó không có quyền đòi. Phép chia ấy đến từ bộ lọc
       `bool(vision) == can_thi_giac` — thứ §2 vừa bỏ vì nó tự vỡ ở Task 3.3.
       Từ D09 cả hai thao tác đi model app **khai**, nên bản trước đỏ — và nó
       đỏ vì **đề bài sai**, không vì mã sai.

    ⭐ Nên đối chứng nay **tự dựng** hình dạng "hai model, hai cửa sổ" thay
       vì chờ registry hôm nay tình cờ chia như thế. Hai con số dưới đây là
       số **tiêm**, không phải số đo — đừng đọc chúng như cấu hình thật.
    """
    from platform_core.llm import canonical

    khai = canonical.ALIAS_SANG_ID[canonical.model_noi_bo_cua(ai.SLUG)]
    khac = next(m for m in canonical.ALIAS_SANG_ID.values() if m != khai)
    _tiem_registry(monkeypatch, {
        khai: {"context_window": 111_111},
        khac: {"vision": True, "context_window": 222_222},
    })

    assert ai.model_cho(ai.DICH_THUAT) == khai
    assert ai.model_cho(ai.DOC_CANH) == khac
    assert ai.cua_so_ngu_canh(ai.DICH_THUAT) == 111_111
    assert ai.cua_so_ngu_canh(ai.DOC_CANH) == 222_222


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

def test_ban_thang_mo_ho_khi_than_429_co_chu_timeout(monkeypatch):
    """🔑 TIN HIEU MANH (lop) phai thang TIN HIEU YEU (chuoi con).

    `_la_ban` thuan LOP: `BanError` chi sinh ra tu `ma == 429`, tuc may B **da
    tu choi** — khong gi chay, khong gi bi tinh tien. Dut khoat.

    `_la_mo_ho` co mot lop cuoi la do CHUOI ("timeout" / "mat ket noi"). Neu no
    duoc hoi truoc, mot than 429 nhu `"upstream timeout, dang ban"` — hoan toan
    hop ly voi mot `llama-server` dang tai — se bi doc thanh MO HO.

    ⛔ Va hau qua lech ve phia SAI: mo ho thi **dung lan chay** va cho nguoi
       quyet dinh, trong khi viec dung la **doi roi chay tiep**. Mot lan chay bi
       dung vi mot chu trong thong bao cua ben kia.
    """
    from platform_core.llm import dieu_phoi
    from platform_core.llm.cong_vlm import BanError

    from apps.auto_scan_video import ai, loi

    def ban(*a, **kw):
        raise BanError("upstream timeout, dang ban")

    monkeypatch.setattr(dieu_phoi, "goi", ban)

    with pytest.raises(Exception) as ei:
        ai.goi(None, ai.QC_NGU_NGHIA, [{"role": "user", "content": "x"}])

    assert loi.phan_loai(ei.value) == loi.BAN, (
        "mot than 429 co chu 'timeout' bi doc thanh mo ho — lan chay se dung "
        "lai va doi nguoi, thay vi doi may B roi chay tiep")


def test_MAT_KET_NOI_that_van_la_MO_HO(monkeypatch):
    """⚠️ Nua khong the thieu cua bai tren: dao thu tu khong duoc nuot mo ho.

    Mat ket noi SAU khi gui la truong hop **that su** khong biet model da chay
    chua. Doc no thanh "ban" roi thu lai la co the tra tien hai lan cho mot viec.
    """
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, loi

    def mo_ho(*a, **kw):
        raise dieu_phoi.AmbiguousProviderError("mat ket noi sau khi bat dau gui")

    monkeypatch.setattr(dieu_phoi, "goi", mo_ho)

    with pytest.raises(ai.AiMoHo):
        ai.goi(None, ai.QC_NGU_NGHIA, [{"role": "user", "content": "x"}])



# ══════════════════════════════════════════════════════════════════════════════
#  §6  "Model tra ve rong" phai NOI RA vi sao no rong
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Do that 09/09: lan chay nghiem thu `giu_hinh` chet BA lan lien tiep voi
#    dung mot dong — `chuyen_loi_thoai: model tra ve rong` — va **bon phien**
#    lien tiep doc dong do thanh "may B hong". Buoc do (1) sau do goi 30 luot
#    that vao may B: 0/30 hong. May B khong hong.
#
# ⛔ Cho hong that la o RANH GIOI NAY. `cong_vlm.KetQuaChat` DA boc san ca
#    `finish_reason` lan `suy_nghi` (khoi think, vi cong chay
#    `--reasoning-format deepseek`), va `ai.goi` **vut ca hai di** khi dong goi
#    lai thanh dict. Nen mot phan hoi bi cat vi HET NGAN SACH TOKEN — model
#    tieu het `max_tokens` vao khoi suy nghi roi khong con cho de tra loi —
#    den tay nguoi doc duoi dang mot cau khong phan biet duoc voi "may B chet".
#
# ⭐ Dau vet ton tai o tang duoi; no chi khong di qua duoc cua nay. Mot thong
#    diep loi khong noi duoc `finish_reason` la mot thong diep bat nguoi doc
#    di do lai thu ma he thong DA do roi.


class _KqDay:
    """Ket qua GIONG `cong_vlm.KetQuaChat` — co ca finish_reason lan suy_nghi."""

    def __init__(self, noi_dung="", finish_reason="", suy_nghi=""):
        self.noi_dung = noi_dung
        self.finish_reason = finish_reason
        self.suy_nghi = suy_nghi
        self.provider = "ltt_llm"
        self.model = "qwen38-api"
        self.su_dung = None


def test_goi_MANG_THEO_finish_reason_va_suy_nghi(monkeypatch):
    """Hai truong nay di duoc toi day thi moi tang tren moi noi ra duoc vi sao."""
    import platform_core.llm.dieu_phoi as dp
    monkeypatch.setattr(dp, "goi", lambda db, **k: _KqDay(
        noi_dung="", finish_reason="length", suy_nghi="nghi rat nhieu"))

    kq = ai.goi(None, ai.CHUYEN_LOI_THOAI, [{"role": "user", "content": "x"}])
    assert kq["finish_reason"] == "length"
    assert kq["suy_nghi"] == "nghi rat nhieu"


def test_RONG_vi_HET_NGAN_SACH_thi_thong_diep_phai_noi_ra():
    """⛔ Doi chung nam ngay trong phep kiem: cung mot chuoi rong, hai nguyen
    nhan khac nhau, va hai thong diep phai KHAC NHAU. Neu chung giong nhau thi
    phep kiem nay khong do gi ca."""
    kq = {"noi_dung": "", "finish_reason": "length", "suy_nghi": "a" * 900}
    with pytest.raises(ai.LuocDoSai) as e:
        ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI)
    thong_diep = str(e.value)
    assert "length" in thong_diep
    assert "900" in thong_diep, "phai noi ra khoi suy nghi dai bao nhieu"

    with pytest.raises(ai.LuocDoSai) as e2:
        ai.doc_ket_qua({"noi_dung": "", "finish_reason": "stop"},
                       ai.CHUYEN_LOI_THOAI)
    assert str(e2.value) != thong_diep


def test_doc_ket_qua_van_doc_duoc_JSON_binh_thuong():
    ra = ai.doc_ket_qua({"noi_dung": '{"doan": {}}', "finish_reason": "stop"},
                        ai.CHUYEN_LOI_THOAI)
    assert ra == {"doan": {}}


def test_KHONG_giai_doan_nao_con_boc_noi_dung_ra_khoi_kq_bang_tay():
    """⛔ Banh coc: boc `noi_dung` ra khoi ket qua lam mat `finish_reason` va
    `suy_nghi` **ngay tai cho goi**. Duong duy nhat di tu MOT KET QUA sang MOT
    DICT la `ai.doc_ket_qua`, va no la ham duy nhat nhin thay ca ba truong.

    ⚠️ Chot theo TAP HOP tep, khong theo so luong: them mot giai doan moi ma
       lai boc bang tay thi phep kiem nay phai do.

    🔴 **Ban dau phep kiem nay chi soi doi so cua `doc_json`, va no HEP hon
       chinh menh de no tuyen bo.**

       `giai_doan_ban_bien_tap.py:211` viet
       `hc.doc_hieu_canh(kq.get("noi_dung") or "", c.ma)` — cung mot cach boc,
       cung mot mat mat, nhung ten ham la `doc_hieu_canh` nen no di qua. Mot
       banh coc chi bao ve thu no nhin thay, va cai no nhin thay o day la MOT
       TEN HAM chu khong phai MOT HANH VI.

    ⇒ Menh de dung la: **khong tep nao cua ASV duoc go `kq.get("noi_dung")`**,
      bat ke sau do dua cho ai. Ban viet lai nay KHO xanh hon ban cu — no bat
      duoc ban cu cong them mot cho nua.
    """
    xau = []
    for tep in sorted(APP.glob("*.py")):
        # ⭐ `ai.py` la NGOAI LE DUY NHAT, va cung ly do voi §1 ("chi ai.py duoc
        #    goi dieu_phoi"): no la cua, nen no la noi duy nhat duoc mo goi.
        #    `ai.doc_ket_qua` boc `noi_dung` **cung voi** `finish_reason` va
        #    `suy_nghi` — do la ca dinh nghia cua no. Moi tep khac boc mot minh
        #    `noi_dung` la boc thieu.
        if tep.name == "ai.py":
            continue
        for nut in ast.walk(_cay(tep)):
            if (isinstance(nut, ast.Call)
                    and isinstance(nut.func, ast.Attribute)
                    and nut.func.attr == "get"
                    and nut.args
                    and isinstance(nut.args[0], ast.Constant)
                    and nut.args[0].value == "noi_dung"):
                xau.append(f"{tep.name}:{nut.lineno}")
    assert xau == [], (
        "boc noi_dung ra khoi ket qua bang tay lam mat finish_reason/suy_nghi: "
        f"{xau}. Dung ai.doc_ket_qua(kq, ...) — hoac truyen ca `kq` di tiep.")


# ══════════════════════════════════════════════════════════════════════════════
#  §7  HAI trần, không phải một — và cái thứ hai nguy hiểm hơn
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Do that 09/09, sau tran token: sau luot THANH CONG o tran token rong mat
#
#        65,8 · 75,3 · 84,6 · 94,4 · 94,9 · **107,7** giay
#
#    va `dieu_phoi.goi` co `timeout_s: float = 120.0`. Tuc luot cham nhat cach
#    tran thoi gian **10 %** — voi mot lo 6 doan, trong khi
#    `long_tieng.DOAN_MOI_LO` = 12.
#
# ⛔ Hai rao dat canh nhau, ca hai deu duoi nhu cau binh thuong. Va go MOT cai
#    lam moi thu TE HON:
#
#      tran token cu  -> `LuocDoSai`              -> `TAM_THOI`, thu lai duoc
#      tran thoi gian -> `AmbiguousProviderError` -> `AiMoHo`, DUNG lan chay
#                                                    va cho nguoi quyet dinh
#
#    Nang `max_tokens` ma khong nang `timeout_s` la doi mot that bai thu lai
#    duoc lay mot that bai treo lai — voi tien da tieu va khong ai biet model
#    da chay chua.
#
# ⭐ Nen `ai.goi` phai co duong truyen `timeout_s`. Khong co no thi ngay ca mot
#    PHEP DO ve nhu cau that cung khong thuc hien duoc: lo 12 doan se het gio
#    truoc khi het token, va ta lai do cai phanh thay vi do nhu cau — dung loi
#    da lam `token_ra = 4096` tro thanh mot con so vo nghia.


def test_goi_TRUYEN_DUOC_timeout_s_xuong_dieu_phoi(monkeypatch):
    """Khong co duong nay thi khong the do duoc nhu cau that cua mot lo day."""
    gia = _Gia()
    _tiem(monkeypatch, gia)
    ai.goi(None, ai.CHUYEN_LOI_THOAI, [{"role": "user", "content": "x"}],
           timeout_s=300.0)
    assert gia.da_goi["timeout_s"] == 300.0


def test_KHONG_truyen_thi_dieu_phoi_giu_mac_dinh_cua_no(monkeypatch):
    """⛔ Doi chung: neu `ai.goi` **luon** gui mot con so thi no da go lai mot
    mac dinh cua nen tang, va hai ben se lech nhau ngay lan dau ai do sua
    `dieu_phoi`. Khong khai thi khong gui — de mot nguon chan ly duy nhat."""
    gia = _Gia()
    _tiem(monkeypatch, gia)
    ai.goi(None, ai.CHUYEN_LOI_THOAI, [{"role": "user", "content": "x"}])
    assert "timeout_s" not in gia.da_goi, (
        "ASV go lai mac dinh timeout cua `dieu_phoi` — mot con so thu hai cho "
        "cung mot thu, va CLAUDE.md ghi mot loi da xay ra that vi dung do")


# ─────────────────────────────────────────────────────────────────────────────
# KHAI ĐÈ MODEL THEO THAO TÁC — họ N-15: một hằng làm nhiều việc
# ─────────────────────────────────────────────────────────────────────────────


def test_thao_tac_KHONG_khai_de_thi_di_theo_BAN_KHAI_nhu_cu():
    """(a) Vắng mặt trong bảng = **giữ nguyên hành vi cũ**.

    ⚠️ Bài này một mình chỉ **chép lại hiện trạng** — nó không bắt được cái bẫy.
       Bài dưới mới bắt.
    """
    from platform_core.llm import canonical

    khai = canonical.ALIAS_SANG_ID[canonical.model_noi_bo_cua(ai.SLUG)]
    for t in ai.THAO_TAC:
        if t.ma in ai.MODEL_THEO_THAO_TAC or t.can_thi_giac:
            continue
        assert ai.model_cho(t) == khai, f"{t.ma} lệch khỏi bản khai"


def test_DOI_MAC_DINH_thi_qc_ngu_nghia_KHONG_doi(monkeypatch):
    """🔴 **(b) Đây là vế bắt được cái bẫy.**

    Ngày ai đó đổi `manifest.model_llm_noi_bo`, **bộ chấm ngữ nghĩa không được
    bị kéo đi theo**. Một giá trị trùng mặc định **vì tình cờ** và một giá trị
    trùng **vì được khai** là hai trạng thái khác nhau, và ⛔ chỉ cái thứ hai
    sống sót qua một lần sửa chỗ khác.

    ⇒ Tiêm đúng ngày đó: đổi mặc định sang model kia, rồi đòi `qc_ngu_nghia`
      **không nhúc nhích**.
    """
    from platform_core.llm import canonical

    cu = canonical.model_noi_bo_cua(ai.SLUG)
    moi = next(a for a in canonical.ALIAS_SANG_ID if a != cu)
    ghim = canonical.ALIAS_SANG_ID[ai.MODEL_THEO_THAO_TAC["qc_ngu_nghia"]]

    _tiem_registry(monkeypatch, {mid: {"vision": True}
                                 for mid in canonical.ALIAS_SANG_ID.values()})
    truoc = ai.model_cho(ai.QC_NGU_NGHIA)
    assert truoc == ghim

    monkeypatch.setattr(canonical, "model_noi_bo_cua", lambda _s: moi)
    # ⛔ Mặc định ĐÃ đổi — chứng minh bằng một thao tác KHÔNG ghim.
    assert ai.model_cho(ai.HO_SO_NOI_DUNG) == canonical.ALIAS_SANG_ID[moi], (
        "phép tiêm không có tác dụng — bài này đang đo chính nó")
    # ⭐ ...và bộ chấm vẫn đứng yên.
    assert ai.model_cho(ai.QC_NGU_NGHIA) == ghim, (
        "⛔ đổi mặc định đã KÉO THEO bộ chấm — đúng cái bẫy N-15")


def test_khai_de_KHONG_vuot_duoc_rang_buoc_THI_GIAC(monkeypatch):
    """⛔ Một khai đè trỏ vào model không đọc được ảnh, cho thao tác CẦN ảnh,
    phải bị **bỏ qua** như một bản khai hỏng — ⛔ không được trả về nó."""
    from platform_core.llm import canonical

    mu = next(iter(canonical.ALIAS_SANG_ID))
    sang = next(a for a in canonical.ALIAS_SANG_ID if a != mu)
    _tiem_registry(monkeypatch, {canonical.ALIAS_SANG_ID[mu]: {},
                                 canonical.ALIAS_SANG_ID[sang]: {"vision": True}})
    monkeypatch.setitem(ai.MODEL_THEO_THAO_TAC, ai.QC_HINH.ma, mu)
    assert ai.model_cho(ai.QC_HINH) == canonical.ALIAS_SANG_ID[sang]
