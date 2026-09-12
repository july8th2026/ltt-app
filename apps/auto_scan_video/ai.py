"""MOT cua duy nhat de Auto Scan goi model — van ban lan thi giac.

## Vi sao mot tep rieng thay vi moi giai doan tu goi

Tu pha 11 tro di co **nam** thao tac AI khac nhau: doc canh, dung ho so noi
dung, chuyen loi thoai, rut ngan cho vua, va kiem chat luong ngu nghia. Neu moi
giai doan tu dung mot loi goi thi ta co nam ban sao cua cung mot quyet dinh —
chon model, tran token, doc ket qua co cau truc, xu ly dispatch mo ho — va nam
ban sao la nam cho de chung lech nhau.

⭐ Ranh gioi trach nhiem, ghi ro de khong ai doan:

    ASV  so huu    prompt · lu?c do dau ra · phien ban cua ca hai
    NEN TANG so huu provider · id model · van chuyen · ngan sach · dispatch mo ho

## 🔴 Loi THU BA cua cung mot khuon, tim ra o pha 08

`platform_core/llm/dieu_phoi.goi` co mot vi du trong docstring:

    model_theo_provider={"ltt_llm": "ltt_llm"}

va chinh docstring do ghi rang vi du nay **SAI**: `ltt_llm` la **bi danh cong
khai cua app**, khong phai id model. Provider chi khai `qwen38-api` va
`qwen38-vision` (do duoc: `providers.models_for("ltt_llm")` tra dung hai id do,
khong co `ltt_llm`). Truyen bi danh vao thi `chon_key` nem `ThieuKeyError`, va
`goi` doc do la *"provider nay khong phuc vu duoc, di tiep"* — tuc **bo qua
provider trong im lang** roi nem `KhongCoProviderNao`.

Docstring do ke ten hai nan nhan da biet: `platform_core/agent/planner.py` (moi
luot lap ke hoach roi xuong Gemini du khai "model nha di truoc") va
`tools/kiem_ltt_llm.py`. Ca hai hong **suot nhieu thang**.

`apps/auto_scan_video/dich_thuat.py:45` la nan nhan **thu ba**, va no khong bi
phat hien vi giai doan dich van la engine gia tu pha 05 — no chua tung goi that
mot lan nao.

⇒ ⛔ **Khong gõ id model o ben goi.** Tep nay hoi nen tang
  (`providers.model_capabilities`) xem model nao co thi giac, roi truyen dung id
  do. Ngay ai do doi GGUF ben duoi, registry doi va ta di theo.

## ⛔ Khong co van chuyen AI thu hai

Khong `requests`, khong `httpx`, khong `urllib`, khong doc endpoint may B.
`tests/test_434` chot dieu do bang AST tren ca thu muc app.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

#: Provider duy nhat. Xem `dich_thuat` dau tep: doi model la doi san pham.
THU_TU_PROVIDER = ("ltt_llm",)

#: Slug cua chinh app nay, de hoi `canonical.model_noi_bo_cua`. ⛔ Khong go lai
#: chuoi nay o `model_cho`: hai ban sao cua mot ten se troi khoi nhau.
SLUG = "auto_scan_video"

#: 🔑 **Phien ban PROMPT + LU?C DO, di vao van tay.**
#:
#: ⛔ Thieu no thi doi mot cau prompt xong, cache van khop, va lan chay dung lai
#:    ket qua sinh boi prompt CU — mot thay doi san pham khong bao gio toi khach.
#:    Cung lop loi voi `thi_hanh.PHIEN_BAN_ENGINE_GIA`, o mot tang khac.
PHIEN_BAN_PROMPT = 1
PHIEN_BAN_LUOC_DO = 1


# 🔑 Nhap tu `giong_noi`: `MayBan` la lop DUNG CHUNG cho "may dang
#    ban" cua ca app, va `loi.phan_loai` doc dung no. Dinh nghia mot lop
#    ban thu hai o day se tao ra mot duong ban ma `phan_loai` khong biet.
from .giong_noi import MayBan  # noqa: E402


class AiError(RuntimeError):
    """Loi khi goi model. Bao gom ca ket qua sai hinh dang."""


class AiMoHo(RuntimeError):
    """Mat ket noi SAU khi da gui — khong biet model da chay chua.

    ⛔ Cung nghia voi `su_dung.MO_HO` (ADR-001 D9), va phai duoc doi xu y het:
       khong thu lai mu, khong tinh tien, cham mot dau de nguoi quyet dinh.
    """


class LuocDoSai(AiError):
    """Model tra ve JSON hop le nhung THIEU truong bat buoc, hoac sai kieu."""


# ══════════════════════════════════════════════════════════════════════════════
#  Thao tac co kieu — nam cai, mot bang
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ThaoTac:
    """MOT thao tac AI cua Auto Scan.

    ⭐ `can_thi_giac` la thu DUY NHAT quyet dinh model. Khong giai doan nao duoc
       tu chon id model; chung chon mot THAO TAC, va bang nay chon phan con lai.
       Do la khac biet giua "chon theo ngu nghia" va "go mot chuoi".
    """

    ma: str
    can_thi_giac: bool
    #: Truong bat buoc trong JSON model phai tra ve. Rong = khong ep luoc do.
    truong_bat_buoc: tuple[str, ...] = ()
    #: Pha nao la nguoi goi dau tien. Chi de tra cuu.
    pha: str = ""


DICH_THUAT = ThaoTac("dich_thuat", False, ("doan",), pha="14")
#: 🔴 **Truoc pha 27 truong bat buoc o day la `("canh",)`, va no mo ta mot hinh
#:    dang phan hoi ma khong ai bao gio yeu cau.**
#:
#:    `hieu_canh.loi_nhac_canh` bao model tra ve mot doi tuong PHANG — `loai`,
#:    `chu_the`, `de_xuat`, `do_tin`, ... — khong co khoa `canh` nao. Nen mot
#:    phan hoi lam **dung y nguyen loi dan** bi `doc_json` tu choi voi "thieu
#:    truong bat buoc ['canh']". Khai bao va loi dan mo ta hai luoc do khac
#:    nhau, va khong ai phat hien vi khong nguoi goi nao ton tai de chay no.
#:
#: ⭐ Hai truong duoi day la hai truong `_quyet_dinh_mot_canh` THUC SU doc.
#:    `loai`/`chu_the`/`ly_do` la thu de nguoi doc bao cao hieu quyet dinh, nen
#:    thieu chung khong lam quyet dinh sai — con thieu `de_xuat` hay `do_tin`
#:    thi lam.
DOC_CANH = ThaoTac("doc_canh", True, ("de_xuat", "do_tin"), pha="11")
HO_SO_NOI_DUNG = ThaoTac("ho_so_noi_dung", True, ("the_loai", "nhip"), pha="11")
CHUYEN_LOI_THOAI = ThaoTac("chuyen_loi_thoai", False, ("doan",), pha="14")
RUT_NGAN_CHO_VUA = ThaoTac("rut_ngan_cho_vua", False, ("doan",), pha="15")
#: 🔴 **`("doan",)`, khong phai `("dat", "ly_do")` — va do la B22-01 lan hai.**
#:
#:    `qc_ai.loi_nhac_ngu_nghia` doi dung mot hinh dang:
#:
#:        {"doan": {"<ma>": {"dat": true, "do_tin": 0.9, "ly_do": ""}}}
#:
#:    `dat` va `ly_do` nam o tang TRONG, moi ma mot ban. Nhung `doc_json`
#:    kiem `truong_bat_buoc` o **tang ngoai cung** (`t not in ra`), nen mot
#:    phan hoi tuan thu DUNG loi nhac cua chinh ta bi CHINH TA tu choi:
#:
#:        LuocDoSai: qc_ngu_nghia: phan hoi thieu truong bat buoc
#:                   ['dat', 'ly_do']
#:
#: ⭐ Do dung la khiem khuyet pha 27 vua sua cho `DOC_CANH` (khai `("canh",)`
#:    — mot hinh dang khong ai san xuat). Lan nay no nam san trong duong QC
#:    ngu nghia, chua tung chay, nen no doi den luot goi TRA TIEN dau tien.
#:
#: ⚠️ Bat duoc TRUOC khi noi vao mach, bang cach cho mot phan hoi tuan thu
#:    di qua `doc_json` — khong bang cach doc hai tep roi so trong dau.
QC_NGU_NGHIA = ThaoTac("qc_ngu_nghia", False, ("doan",), pha="19")

THAO_TAC: tuple[ThaoTac, ...] = (
    DICH_THUAT, DOC_CANH, HO_SO_NOI_DUNG, CHUYEN_LOI_THOAI,
    RUT_NGAN_CHO_VUA, QC_NGU_NGHIA)

THEO_MA = {t.ma: t for t in THAO_TAC}


# ══════════════════════════════════════════════════════════════════════════════
#  Chon model — HOI nen tang, khong go id
# ══════════════════════════════════════════════════════════════════════════════

def model_cho(thao_tac: ThaoTac, *, provider: str = "") -> str:
    """Id model that cho mot thao tac. Hoi BAN KHAI, doi chieu REGISTRY.

    🔑 Ngu nghia la `can_thi_giac`; id la viec cua nen tang. Ngay may B doi
       GGUF ben duoi, registry doi va ta di theo — khong tep nao cua Auto Scan
       phai sua.

    🔴 D09 (dual-model 2.3 con sot, sua o 3.3) DOI CACH CHON, KHONG DOI
       BAT BIEN. Ban truoc loc `bool(kn["vision"]) == thao_tac.can_thi_giac`,
       tuc thao tac VAN BAN doi mot model **khong** co thi giac. Phep loc ay
       hong o hai chieu, va ca hai deu that:

       (a) **No tu vo o Task 3.3.** Khi `qwen38-api` nap mmproj va khai
           `vision: True` thi CA HAI model cong khai deu co co ⇒ tap `hop`
           rong cho moi thao tac van ban ⇒ `AiError`, va nam thao tac AI cua
           ASV chet han. Day khong phai suy doan: `planner._model_nha` mang y
           nguyen khuyet tat nay, da sua o 2.4, va docstring cua no **goi ten
           tep nay** la cho con lai.

       (b) **No khong tra loi dung cau hoi.** "Model nao khong doc anh" khong
           phai cau ASV can hoi. Van ban chay tot tren mot model co thi giac —
           mmproj chi ngoi khong. Cau dung la *"model nao app nay khai cho viec
           LLM noi bo cua no"*, va tu D09 nen tang co dung mot cho tra loi:
           `canonical.model_noi_bo_cua(slug)` doc `manifest.model_llm_noi_bo`.

       ⛔ Nen ĐỪNG doc `MODEL_MAC_DINH` o day: do la mac dinh **cua khach**
          goi `text.chat`, khong phai lua chon noi bo cua mot app.
          `tests/test_1212` co banh coc AST cho dung dieu do — tep nay nay nam
          trong danh sach nguoi goi noi bo cua no.

    ⚠️ Thi giac thi VAN la rang buoc cung: mot thao tac `can_thi_giac` khong
       bao gio duoc phuc vu boi model khong khai `vision`. Neu model app khai
       khong doc duoc anh thi ta **di tim mot model khac** (va ghi mot dong
       canh bao — bo dieu huong am tham di nguoc lai chinh ban khai la thu
       nguoi van hanh can biet), chu khong lang le tra ve no.

    ⛔ Nem `AiError` neu khong con ai phuc vu duoc, thay vi roi ve mot mac
       dinh. Roi ve model khong thi giac cho mot thao tac CAN thi giac se cho ra
       mot cau tra loi trong nhu that ve mot buc anh model chua bao gio nhin
       thay.
    """
    from platform_core import providers
    from platform_core.llm import canonical

    pid = provider or THU_TU_PROVIDER[0]
    kha_nang = {m.id: (providers.model_capabilities(m.id) or {})
                for m in providers.models_for(pid)}

    def phuc_vu_duoc(mid: str) -> bool:
        if mid not in kha_nang:
            return False
        return bool(kha_nang[mid].get("vision")) or not thao_tac.can_thi_giac

    khai = canonical.ALIAS_SANG_ID.get(canonical.model_noi_bo_cua(SLUG), "")
    if phuc_vu_duoc(khai):
        return khai

    # ⚠️ On dinh: sap xep de hai lan goi cung cho ra mot id, neu khong van tay
    #    se nhay va cache truot vo co.
    hop = sorted(mid for mid in kha_nang if phuc_vu_duoc(mid))
    if not hop:
        raise AiError(
            f"{pid} khong co model nao phuc vu duoc thao tac {thao_tac.ma!r}"
            f" (can thi giac: {thao_tac.can_thi_giac}; khai: {khai!r};"
            f" registry: {sorted(kha_nang)})")
    if khai:
        log.warning(
            "app %r khai model noi bo %r nhung no %s cho thao tac %r; dung %r",
            SLUG, khai,
            "khong co trong registry" if khai not in kha_nang
            else "khong khai thi giac",
            thao_tac.ma, hop[0])
    return hop[0]


def ban_do_model(thao_tac: ThaoTac) -> dict:
    """`model_theo_provider` cho `dieu_phoi.goi`. Xem loi thu BA o dau tep."""
    return {pid: model_cho(thao_tac, provider=pid) for pid in THU_TU_PROVIDER}


def tran_token_ra() -> int:
    """Tran token DAU RA. ⛔ Doc tu `ltt_llm.ngan_sach`, khong go lai con so.

    `apps/ltt_llm/ngan_sach.py` la mot nguon chan ly cho moi ngan sach token cua
    model nha. CLAUDE.md ghi mot loi da xay ra that vi go lai con so thu hai: cua
    stream lay nham mot hang `1_024` va **moi cau tra loi dai deu bi cat**.
    """
    try:
        from apps.ltt_llm import ngan_sach
        return int(ngan_sach.mac_dinh_cho("job"))
    except Exception as exc:  # noqa: BLE001
        log.warning("khong doc duoc ngan sach ltt_llm (%s)", type(exc).__name__)
        raise AiError("khong doc duoc ngan sach token cua model nha") from exc


# ══════════════════════════════════════════════════════════════════════════════
#  Ngan sach RIENG cua tung thao tac — V6
# ══════════════════════════════════════════════════════════════════════════════

#: `(tran token ra, tran thoi gian giay)` cho nhung thao tac **da do** va thay
#: mac dinh cua nen tang khong du. Thao tac khong co o day di theo
#: `tran_token_ra()` va mac dinh cua `dieu_phoi`.
#:
#: 🔴 **Vi sao khai o day chu khong nang `ltt_llm.ngan_sach`.**
#:
#:    Cua `job` cua `ltt_llm` la mac dinh cho **moi** app dung model nha. Nang no
#:    len vi mot lo 12 doan cua Auto Scan la bat moi app khac mang mot tran ma
#:    khong ai do cho ho. Nhu cau la cua ta, nen ta khai no.
#:
#: ⭐ Va khai theo THAO TAC chu khong truyen o tung cho goi: bon cho goi
#:    `goi_tinh_tien` hom nay, va cho thu nam viet ngay mai se **tu** nhan dung
#:    ngan sach thay vi phai nho.
#:
#: 🔑 CON SO DAT THE NAO — va cho nay quan trong hon con so.
#:
#:    `docs/auto_scan_video_v4/evidence/20260909_tran_token_ra_chuyen_loi_thoai.md`
#:    do voi ca hai rao da noi, 3 vong moi co lo:
#:
#:        lo 6 : 5.039 · 5.278 · 7.915 token   |  75,7 · 78,8 · 117,3 giay
#:        lo 12: 10.248 · 9.642 · 6.948 token  | 151,0 · 142,6 · 102,3 giay
#:
#:    ⛔ Ban dau bao cao ay rut ra `ra(n) ~ 310 + 828n` tu HAI vong, roi vong
#:       thu ba lat no: `max(lo 6) = 7.915` **lon hon** `min(lo 12) = 6.948`.
#:       Hai phan bo chong len nhau, tuc do doc theo co lo khong tach duoc khoi
#:       nhieu. Chinh bao cao do ket luan: **dat tran theo GIA TRI LON NHAT QUAN
#:       SAT DUOC kem bien, dung dat theo cong thuc tuyen tinh chua du mau.**
#:
#:    ⇒ lon nhat quan sat: 10.248 token / 151,0 giay.
#:      Dat 16.384 (~1,6x) va 300 giay (~2,0x).
#:
#: ⛔ **BAT BIEN — bao cao ay ghim lai, va bang nay ep no thanh CO HOC:**
#:    *"Khong bao gio giao tran token ma khong giao tran timeout cung luot."*
#:
#:    Vi hau qua khong phai "sua duoc it hon" ma **sua xong he TE DI**: hong it
#:    lan hon, nhung moi lan hong dat hon nhieu — `LuocDoSai` chi thu lai, con
#:    cham tran thoi gian cho ra `AiMoHo`, thu DUNG lan chay va doi nguoi.
#:
#:    Mot `tuple` hai o lam mot nua khong the giao mot minh. Khong phai giao uoc.
#:
#: ⚠️ `qc_ngu_nghia` (lo 10) **chua tung chay voi model that**, nen no o day
#:    khong phai vi da do — ma vi no la **cung mot hinh dang**: cung mot khoi
#:    suy nghi chiem ~93% token ra, cung mot co lo hai chu so. Doi no hong mot
#:    lan roi moi cho ngan sach la doi mot lan chay cua khach de phat hien mot
#:    thu da biet truoc.
NGAN_SACH_RA: dict[str, tuple[int, float]] = {
    CHUYEN_LOI_THOAI.ma: (16_384, 300.0),
    QC_NGU_NGHIA.ma: (16_384, 300.0),
}


def ngan_sach_cho(thao_tac: ThaoTac) -> tuple[int, float | None]:
    """`(max_tokens, timeout_s)` cho mot thao tac. `0`/`None` = theo mac dinh."""
    tra = NGAN_SACH_RA.get(thao_tac.ma)
    return (0, None) if tra is None else (int(tra[0]), float(tra[1]))


def cua_so_ngu_canh(thao_tac: ThaoTac) -> int:
    """Cua so ngu canh THAT cua model se dung.

    🔴 Van ban va thi giac **khong bang nhau**: do duoc tu registry, `qwen38-api`
       co 131 072 con `qwen38-vision` chi **65 536**. Mot lo khung hinh sap theo
       tran cua model van ban se thanh mot loi 413 luc chay.

    ⚠️ Va `docs/audit_ltt_llm/STATE.md` tung do duoc mot tran **thap hon nhieu**
       cho ban thi giac (28 262 token). Con so o day la cai registry KHAI; pha 11
       phai do lai truoc khi sap lo khung hinh theo no.
    """
    from platform_core import providers

    kn = providers.model_capabilities(model_cho(thao_tac)) or {}
    return int(kn.get("context_window") or 0)


# ══════════════════════════════════════════════════════════════════════════════
#  Doc ket qua co cau truc
# ══════════════════════════════════════════════════════════════════════════════

def _vi_sao_rong(finish_reason: str, suy_nghi: str) -> str:
    """Phan duoi cua thong diep "model tra ve rong" — thu NOI RA vi sao.

    🔴 Do that 09/09: lan chay `giu_hinh` chet ba lan voi dung mot dong
       *"chuyen_loi_thoai: model tra ve rong"*, va **bon phien** lien tiep doc
       dong ay thanh "may B hong". Buoc do sau do goi 30 luot that vao may B:
       0/30 hong.

    ⛔ Ca hai manh cua cau tra loi DA nam san trong `cong_vlm.KetQuaChat` —
       `finish_reason` va `suy_nghi` (khoi think, vi cong chay
       `--reasoning-format deepseek`). Chung chi khong di qua duoc cua nay.
       `finish_reason == "length"` kem mot khoi suy nghi dai la mot cau chuyen
       khac han "may B chet": model tieu het `max_tokens` vao viec nghi roi
       khong con cho de tra loi.

    ⚠️ Va do la ly do khong duoc go tat phan nay khi `finish_reason` rong: mot
       chuoi rong o day nghia la *cong khong noi*, khong phai *cong noi la binh
       thuong*. Hai thu do dan toi hai cho sua khac nhau.
    """
    manh = []
    if finish_reason:
        manh.append(f"finish_reason={finish_reason}")
    else:
        manh.append("finish_reason=(cong khong noi)")
    n = len(suy_nghi or "")
    if n:
        manh.append(f"khoi suy nghi {n} ky tu")
        if str(finish_reason).lower() == "length":
            manh.append("=> HET NGAN SACH TOKEN trong luc dang nghi, "
                        "khong phai may B hong")
    return " [" + "; ".join(manh) + "]"


def doc_ket_qua(kq: dict, thao_tac: ThaoTac) -> dict:
    """Duong DUY NHAT di tu mot ket qua `goi()` sang mot dict da kiem luoc do.

    ⛔ `ai.doc_json(kq.get("noi_dung") or "", ...)` vut mat `finish_reason` va
       `suy_nghi` **ngay tai cho goi**, nen loi bao len tren la mot cau khong
       phan biet duoc "model nghi qua tay" voi "may B chet".
       `test_434::test_KHONG_giai_doan_nao_con_boc_noi_dung_ra_khoi_kq_bang_tay`
       chot rang khong tep nao cua ASV con lam vay.
    """
    kq = kq or {}
    return doc_json(str(kq.get("noi_dung") or ""), thao_tac,
                    finish_reason=str(kq.get("finish_reason") or ""),
                    suy_nghi=str(kq.get("suy_nghi") or ""))


def doc_json(noi_dung: str, thao_tac: ThaoTac, *,
             finish_reason: str = "", suy_nghi: str = "") -> dict:
    """Doc JSON tu phan hoi model va kiem luoc do. Nem `LuocDoSai` neu khong dat.

    ⭐ Model hay boc JSON trong ```json ... ```, hoac them mot cau dan truoc no.
       Cat den dau ngoac nhon dau tien va dau ngoac nhon cuoi cung la cach chiu
       duoc ca hai ma khong doan.

    ⛔ Mot truong thieu **phai** thanh loi, khong duoc thanh `None` di tiep. Mot
       `None` di tiep se lo ra o mot giai doan khac, duoi mot thong bao khong
       lien quan gi — va nguoi doc se di tim o nham cho.
    """
    s = (noi_dung or "").strip()
    if not s:
        raise LuocDoSai(f"{thao_tac.ma}: model tra ve rong{_vi_sao_rong(finish_reason, suy_nghi)}")

    dau, cuoi = s.find("{"), s.rfind("}")
    if dau < 0 or cuoi <= dau:
        raise LuocDoSai(f"{thao_tac.ma}: phan hoi khong chua doi tuong JSON nao")
    try:
        ra = json.loads(s[dau:cuoi + 1])
    except ValueError as exc:
        raise LuocDoSai(f"{thao_tac.ma}: JSON hong ({exc})") from exc
    if not isinstance(ra, dict):
        raise LuocDoSai(f"{thao_tac.ma}: mong mot doi tuong, nhan {type(ra).__name__}")

    thieu = [t for t in thao_tac.truong_bat_buoc if t not in ra]
    if thieu:
        raise LuocDoSai(
            f"{thao_tac.ma}: phan hoi thieu truong bat buoc {thieu}")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Goi
# ══════════════════════════════════════════════════════════════════════════════

def goi(db, thao_tac: ThaoTac, messages: list, *, ctx=None,
        max_tokens: int = 0, temperature: float | None = None,
        timeout_s: float | None = None,
        on_dispatch=None, on_rejected=None) -> dict:
    """MOT cua goi model. Tra ve `{"noi_dung", "provider", "model", "su_dung"}`.

    🔴 **`timeout_s` la RAO THU HAI, va no nguy hiem hon rao token.**

       Do that 09/09, sau luot THANH CONG cua `chuyen_loi_thoai` voi mot lo
       **6** doan (`long_tieng.DOAN_MOI_LO` = 12, tuc lo that co the gap doi):

           65,8 · 75,3 · 84,6 · 94,4 · 94,9 · **107,7** giay
           4.517 · 5.201 · 5.868 · 6.406 · 6.422 · **7.526** token ra

       Tuyen tinh sach, ~70 token/giay. Va `dieu_phoi.goi` co
       `timeout_s: float = 120.0`. Luot cham nhat cach tran thoi gian **10 %**.

    ⛔ Nen nang `max_tokens` MA KHONG nang `timeout_s` la doi mot that bai xau
       lay mot that bai TE HON:

           het token     -> `LuocDoSai`              -> `TAM_THOI`, thu lai duoc
           het thoi gian -> `AmbiguousProviderError` -> `AiMoHo`, DUNG lan chay
                                                        va cho nguoi quyet dinh

       Tien da tieu o ca hai, nhung ca thu hai con khong ai biet model da chay
       chua. Hai rao dat canh nhau, ca hai duoi nhu cau binh thuong; go mot cai
       roi de nguyen cai kia la lam moi thu te di.

    ⚠️ `None` = **khong khai**, va `dieu_phoi` giu mac dinh cua no. Khong go lai
       mot con so o day: CLAUDE.md ghi mot loi da xay ra that vi go lai mot
       hang so thu hai cho cung mot thu.

    ⛔ Khong tep nao khac cua Auto Scan duoc goi `dieu_phoi.goi` truc tiep.
       `tests/test_434` chot dieu do — hai duong toi cung mot provider la hai
       duong se lech nhau ve tran token, ve chon model, va ve cach doc loi.

    🔑 **Dispatch mo ho khong duoc nuot.** `dieu_phoi` phan biet "provider tu
       choi" (thu lai duoc) voi "mat ket noi sau khi gui" (khong biet da chay
       chua). Cai thu hai doi thanh `AiMoHo`, va `su_dung` ghi no o trang thai
       `mo_ho` — khong tinh tien, khong tu dong thu lai.
    """
    from platform_core.llm import dieu_phoi

    huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    if huy is not None and huy():
        raise AiError(_t('Lần chạy đã bị hủy.'))

    # 🔑 `on_dispatch`/`on_rejected` la ngu nghia dispatch ben vung cua nen tang
    #    (I5): chung ghi `provider_state` xuong CSDL **ngay truoc** khi goi ra
    #    ngoai, nen mot lan sap sau do doc ra duoc la "co the da goi" chu khong
    #    phai "chua goi". Lay tu `ctx` khi ben goi khong tu truyen.
    if on_dispatch is None and ctx is not None:
        on_dispatch = getattr(ctx, "provider_dispatched", None)
    if on_rejected is None and ctx is not None:
        on_rejected = getattr(ctx, "provider_rejected", None)

    # ⚠️ Chi them khoa khi ben goi KHAI. Truyen `timeout_s=None` xuong se de len
    #    mac dinh cua `dieu_phoi` mot gia tri khong hop le.
    them: dict = {}
    if timeout_s is not None:
        them["timeout_s"] = float(timeout_s)

    try:
        kq = dieu_phoi.goi(
            db, messages=messages,
            thu_tu_provider=THU_TU_PROVIDER,
            model_theo_provider=ban_do_model(thao_tac),
            max_tokens=int(max_tokens) or tran_token_ra(),
            temperature=temperature,
            on_dispatch=on_dispatch, on_rejected=on_rejected, **them)
    except Exception as exc:  # noqa: BLE001
        # 🔑 **BAN hoi TRUOC MO HO, va thu tu nay co ly do.**
        #
        #    `_la_ban` thuan LOP: `BanError` chi sinh ra tu `ma == 429`, tuc may
        #    B **da tu choi** — khong co gi chay, khong co gi bi tinh tien. Do la
        #    mot su that dut khoat.
        #
        #    `_la_mo_ho` co mot lop cuoi la DO CHUOI ("timeout" / "mat ket noi").
        #    De no chay truoc thi mot tin hieu YEU (chuoi con) thang mot tin hieu
        #    MANH (lop chinh xac) — va do la nghich the.
        #
        # ⛔ Do duoc: `BanError("upstream timeout, dang ban")` — mot than 429
        #    hoan toan hop ly cua mot `llama-server` dang tai — bi doc thanh MO
        #    HO. Hau qua lech ve phia SAI: mo ho thi dung lan chay va cho nguoi
        #    quyet dinh, trong khi viec dung la **doi roi chay tiep**.
        if _la_ban(exc):
            raise MayBan(str(exc)) from exc
        if _la_mo_ho(exc):
            raise AiMoHo(str(exc)) from exc
        # 🔴 **BAN phai hoi TRUOC `AiError`.** `giong_noi.MayBan` da ghi
        #    thang bai hoc nay cho duong GIONG: *"boc `DangBanTam` thanh mot loi
        #    hong la bien 'may dang ban' thanh 'job hong'"*. Duong AI hoc no
        #    muon hon — dong duoi day tung la `raise AiError(...)` cho MOI thu.
        #
        # ⛔ Hau qua do duoc, hai lan (05/09 13:44 va 06/09 09:14/09:20):
        #    may B tra "ban" vi mot phien khac dang dung `ltt_llm`,
        #    `KhongCoProviderNao(busy_only=True)` bi lam phang thanh `AiError`,
        #    va tu do moi tang duoi deu doc sai:
        #
        #      `loi.phan_loai`            -> TAM_THOI (khong phai BAN)
        #      `loi.dich_sang_loi_nen_tang` -> tra ve nguyen `AiError`
        #      `job_runner._provider_failure_kind` -> "retry", khong "resource_wait"
        #
        #    tuc job **khong bao gio duoc hoan**. Lan chay chet o giai doan 5, va
        #    bay muoi phan tram bo nghiem thu do voi nhung cau nhu `assert 404 ==
        #    200` — khong cau nao nhac toi may B.
        #
        # ⭐ Thong diep van giu nguyen, chi LOP doi. Phan loai di theo lop; mot
        #    ban va doi chuoi se hong lai ngay lan sau ai do sua mot thong bao.
        raise AiError(str(exc)) from exc

    return {
        "noi_dung": getattr(kq, "noi_dung", "") or getattr(kq, "content", ""),
        "provider": getattr(kq, "provider", "") or THU_TU_PROVIDER[0],
        "model": getattr(kq, "model", ""),
        "su_dung": getattr(kq, "su_dung", None) or getattr(kq, "usage", None),
        # 🔑 Hai truong CHAN DOAN, va chung khong phai trang tri: mot phan hoi
        #    rong voi `finish_reason="length"` kem mot khoi suy nghi dai la
        #    "model tieu het ngan sach token vao viec nghi", con mot phan hoi
        #    rong voi `finish_reason=""` la mot chuyen khac han. Bo chung o day
        #    lam ca hai truong hop toi tang tren duoi CUNG MOT cau — va do la
        #    cau da lam bon phien lien tiep di do nham may B (09/09).
        "finish_reason": getattr(kq, "finish_reason", "") or "",
        "suy_nghi": getattr(kq, "suy_nghi", "") or "",
    }


def goi_tinh_tien(db, run, thao_tac: ThaoTac, messages: list, *,
                  stage: str, item_key: str, uoc_credit: int = 0,
                  ctx=None, temperature: float | None = None) -> dict:
    """`goi` + cua chan ngan sach TRUOC + ghi so cai SAU. Duong tra tien duy nhat.

    🔑 **Day la cho pha 06 va pha 08 cung ghi no.** Ca hai deu ket luan rang ghi
       mot but toan vao mot duong khong bao gio chay la mot loi khai khong co
       nguoi lam chung; pha 11 la nguoi goi tra tien dau tien, nen no la cho nay.

    Bon buoc, va thu tu la mot phan cua hop dong:

        1. `cua_chan_truoc_khi_tieu`   truoc khi gui — het ngan sach thi hong
                                       SACH SE, khong phai mot hoa don bat ngo
        2. `goi`                       goi that
        3. ghi so cai                  **du ket qua the nao**
        4. tra ket qua / nem lai

    ⛔ Buoc 3 chay o CA ba nhanh (da giao / tu choi / mo ho). Chi ghi khi thanh
       cong la de mot lan mo ho bien mat khoi so sach — dung luc no can duoc
       nhin thay nhat.

    ⚠️ `su_dung.ghi` co the nem `DaGhiRoi` neu ma dispatch trung. Do la RANG BUOC
       LAM DUNG VIEC, khong phai su co: no vua chan mot lan tinh tien thu hai.
       Ta bat va di tiep voi ket qua da co.
    """
    from . import su_dung as sd

    # ── 1. Cua chan TRUOC khi tieu ─────────────────────────────────────────
    if run is not None and uoc_credit:
        sd.cua_chan_truoc_khi_tieu(db, run, uoc_them=int(uoc_credit))

    ma_dispatch = f"{thao_tac.ma}:{stage}:{item_key}"

    def _ghi(trang_thai: str, don_vi: str = "", so_luong: float = 0.0,
             credit: int = 0, **ghi_chu) -> None:
        if db is None or run is None:
            return
        try:
            sd.ghi(db, run, stage=stage, item_key=item_key,
                   su_dung=sd.SuDung(
                       nang_luc=thao_tac.ma, app_chu="ltt_llm",
                       trang_thai=trang_thai, don_vi=don_vi, so_luong=so_luong,
                       credit=credit, ma_dispatch=ma_dispatch,
                       ghi_chu=dict(ghi_chu)))
        except sd.DaGhiRoi:
            # ⭐ Rang buoc `UNIQUE(run_id, ma_dispatch)` vua chan mot lan tinh
            #    tien thu hai. Do la thanh cong, khong phai loi.
            log.info("so cai da co %s - bo qua lan ghi trung", ma_dispatch)

    # ── 2. Goi ────────────────────────────────────────────────────────────
    try:
        # 🔴 Duong TRA TIEN phai mang theo ngan sach cua thao tac.
        #
        #    `goi` da nhan `max_tokens`/`timeout_s` tu 09/09, nhung `goi_tinh_tien`
        #    — **cua duy nhat cua moi lan goi co tinh tien**, va la cua ma bon
        #    giai doan that su di qua — khong truyen chung xuong. Duong co, khong
        #    ai di tren duong: mot lo 12 doan cham tran 4.096 cua nen tang va
        #    `chuyen_loi_thoai` hong 6/6, trong khi mot tham so da san sang o
        #    ham ngay duoi.
        tran, cho = ngan_sach_cho(thao_tac)
        kq = goi(db, thao_tac, messages, ctx=ctx, temperature=temperature,
                 max_tokens=tran, timeout_s=cho)
    except AiMoHo as exc:
        _ghi(sd.MO_HO, ly_do=str(exc)[:200])
        raise
    except AiError as exc:
        _ghi(sd.TU_CHOI, ly_do=str(exc)[:200])
        raise

    # ── 3. Ghi so cai voi thu DO DUOC ─────────────────────────────────────
    do = kq.get("su_dung")
    tin = bool(getattr(do, "dang_tin", False))
    chan_doan = _chan_doan(kq)
    if tin:
        tong = int(getattr(do, "token_vao", 0)) + int(getattr(do, "token_ra", 0))
        _ghi(sd.DA_GIAO, sd.TOKEN, float(max(1, tong)), 0,
             token_vao=int(getattr(do, "token_vao", 0)),
             token_ra=int(getattr(do, "token_ra", 0)),
             model=kq.get("model", ""), **chan_doan)
    else:
        # 🔴 Provider khong tra so do. Xem ghi chu dai o `su_dung.LUOT`: bia mot
        #    so token la noi doi, ghi `TU_CHOI` cung la noi doi. Thu do duoc la
        #    **mot luot da giao**, va ta ghi dung cai do.
        _ghi(sd.DA_GIAO, sd.LUOT, 1.0, 0, khong_do_duoc=True,
             model=kq.get("model", ""), **chan_doan)
    return kq


def _chan_doan(kq: dict) -> dict:
    """Ba truong CHAN DOAN cho so cai. Khong doi mot quyet dinh nao.

    🔑 **Hai trieu chung khac han nhau, cung bieu hien ra ngoai la "lo hong":**

        finish = "length"              -> TRAN CON THAP   -> noi tran
        finish = "stop" + content rong -> CHE DO RONG     -> thu lai

    Hai bo sua khac nhau, va khong co truong nao khac phan biet duoc chung. Do
    duoc 10/09 (phien `ltt-llm-api-http-guide`, 1.891 token vao):

        luot 1   pred_n  9.831   stop     content 0        <- che do rong
        luot 4   pred_n 10.508   stop     content 978      <- binh thuong
        (ngu canh dai)  pred_n 12.000  length              <- cham tran

    ⛔ `ai.goi` da tra ve `finish_reason` va `suy_nghi` tu 09/09 — nhung khong
       cho nao LUU chung. Nang luc co, khong ai di tren duong: sau nay, khi
       khong con ai ngoi do, khong co cach nao phan biet hai che do tu du lieu
       van hanh.

    ⚠️ Ghi DO DAI chu khong ghi noi dung: `suy_nghi` cua model dai hang chuc
       nghin ky tu va co the mang nguyen van doan hoi thoai cua khach. So cai
       khong phai cho de no nam.
    """
    return {
        "finish_reason": str(kq.get("finish_reason") or ""),
        "noi_dung_ky_tu": len(str(kq.get("noi_dung") or "")),
        "suy_nghi_ky_tu": len(str(kq.get("suy_nghi") or "")),
    }


def _la_ban(exc: BaseException) -> bool:
    """Provider dang BAN — khong phai hong, va tuyet doi khong phai that bai.

    ⚠️ Nhan dien theo LOP, chuoi la lop cuoi — cung nguyen tac voi
       `_la_mo_ho`, va vi cung mot ly do: mot phep do chuoi doi nghia trong im
       lang ngay khi ai do sua mot thong bao loi.

    ⭐ `KhongCoProviderNao` chi tinh la ban khi `busy_only` — tuc **moi**
       provider trong danh sach deu ban. Neu mot cai ban con mot cai thieu
       `base_url` thi do la mot loi cau hinh dang nap minh sau mot chu "ban",
       va hoan lai mai se khong bao gio sua duoc no.
    """
    ten = type(exc).__name__
    if ten in ("BanError", "DangBan"):
        return True
    if ten == "KhongCoProviderNao":
        return bool(getattr(exc, "busy_only", False))
    return False


def _la_mo_ho(exc: BaseException) -> bool:
    """Mat ket noi SAU khi gui — khong biet model da chay chua.

    ⚠️ Nhan dien theo LOP truoc, chuoi sau. Mot phep nhan dien chi dua vao chuoi
       se doi nghia ngay khi ai do sua mot thong bao loi, va no doi trong im
       lang ve phia nguy hiem: mot lan mo ho bi doc nham thanh "tu choi" se
       duoc thu lai — tuc co the tra tien hai lan cho mot viec.
    """
    # ⭐ `AmbiguousProviderError` la TIN HIEU CHINH THUC cua nen tang cho tinh
    #    huong nay — `dieu_phoi` nem no khi da goi `on_dispatch` roi moi hong.
    #    Nhan dien theo TEN LOP thi khong the doc nham; mot phep do chuoi thi co.
    ten = type(exc).__name__
    if ten == "AmbiguousProviderError":
        return True
    if ten in ("Timeout", "ReadTimeout", "ConnectionError", "ChunkedEncodingError"):
        return True
    # ⚠️ Nhanh chuoi la lop CUOI, khong phai lop dau: no ton tai cho nhung lop
    #    ngoai le cua thu vien duoi ma ta khong biet ten, va no co the doi nghia
    #    ngay khi ai do sua mot thong bao. Mot lan mo ho bi doc nham thanh "tu
    #    choi" se duoc thu lai — tuc co the tra tien hai lan cho mot viec.
    return "timeout" in str(exc).lower() or "mat ket noi" in str(exc).lower()
