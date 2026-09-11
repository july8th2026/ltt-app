"""Uoc gia mot lan chay, va lua chon san pham cho giao dien.

## Vi sao uoc theo THOI LUONG chu khong theo so ky tu

Luc khach bam "Bat dau", ta chua co ban chep loi. Chua co ban chep loi thi chua
biet so ky tu TTS lan so token LLM — hai thu chiem gan het chi phi. Nen uoc luon
phai dua tren thu **duy nhat** da biet: do dai video.

⚠️ Uoc thua la binh thuong va co chu dinh. `features.quyet_toan` tra lai phan du,
   nen mot uoc rong rai chi lam khach thay so giu cho lon hon so thu — no khong
   lam ho mat tien. Uoc THIEU thi nguoc lai: `features.kiem_tran_chi` se **danh
   hong mot lan chay dang giua chung**, va do la trai nghiem te nhat trong ca
   san pham (RISK-12-03).

⇒ Khi phan van, uoc cao hon.

## Ba con so nay CHUA DUOC DO

⛔ Chung duoc chon de an toan, khong de dung. Chung se duoc thay bang so do that
   o pha 21 (nghiem thu dau-cuoi). Ghi ro o day de khong ai doc chung nhu mot
   bang gia da chot.
"""
from __future__ import annotations

import logging

from platform_core.i18n import N_

log = logging.getLogger(__name__)

#: Credit moi PHUT video, cho phan **may** (tach nguon, chep loi, render).
#: ⚠️ CHUA DO. Chon theo thoi gian may chay chu khong theo gia von.
GIA_MOI_PHUT_MAY = 2

#: Credit moi PHUT video, cho phan **model** (dich + sinh tieng).
#: ⚠️ CHUA DO. Day la phan lon chi phi that, va no ti le voi **luong noi** chu
#:    khong voi do dai video — mot video 10 phut im lang gan nhu khong ton gi.
#:    Uoc theo do dai la mot xap xi rong rai co chu y.
GIA_MOI_PHUT_MODEL = 6

#: San toi thieu. Mot video 20 giay van ton mot lan khoi dong model.
GIA_TOI_THIEU = 5


def uoc_credit(thoi_luong_giay: float) -> int:
    """Uoc chi phi mot lan chay tu do dai video. Luon >= `GIA_TOI_THIEU`."""
    phut = max(0.0, float(thoi_luong_giay or 0)) / 60.0
    return max(GIA_TOI_THIEU,
               int(round(phut * (GIA_MOI_PHUT_MAY + GIA_MOI_PHUT_MODEL))))


#: Che do thoi gian, dong bang o `MVP_CONTRACT.md` §6 va sua boi ADR-003.
#:
#: ⭐ Nhan viet cho NGUOI DUNG, khong phai cho ky su: khach khong can biet
#:    "fit_original" nghia la gi, ho can biet ban long tieng se nghe ra sao.
CHE_DO_THOI_GIAN = (
    ("fit_original", N_('Bám sát câu gốc'),
     N_('Mỗi câu bắt đầu đúng lúc người nói bắt đầu. Phù hợp khi hình có khẩu '
        'hình hoặc chữ chạy theo lời.')),
    ("natural", N_('Nghe tự nhiên'),
     N_('Ưu tiên nhịp đọc dễ nghe, chấp nhận lệch nhẹ so với câu gốc. Phù hợp '
        'với video kể chuyện hoặc thuyết minh.')),
)

CHE_DO_MAC_DINH = "fit_original"


# ══════════════════════════════════════════════════════════════════════════════
#  Hai preset — thu khach THUC SU chon
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Truoc pha 21 khach khong co cach nao chon giua hai preset.** Chuoi `preset`
#    khong xuat hien mot lan nao trong `routes.py` lan giao dien, nen moi lan chay
#    deu roi ve mac dinh `localize_preserve_picture` — va ca duong `smart_localize`
#    (pha 12 den 18 dung nen) la mot duong khong ai voi toi duoc.
#
# ⭐ Mo ta o day viet cho **khach**, khong phai cho lap trinh vien: khong "stream
#    copy", khong "re-encode", khong ten giai doan. Khach quyet dinh dua tren
#    dieu HO quan tam — hinh co bi cat khong — chu khong dua tren cach ta lam.
#
# ⚠️ Va no phai noi that ca **cai gia**: preset cat ma hoa lai luong hinh, nen
#    ban ra khong con giong het ban goc tung diem anh. Giau dieu do di la ban mot
#    thu khac voi thu minh giao.
def _preset_bang():
    from .hop_dong_v4 import PRESET_CAT_THONG_MINH, PRESET_GIU_HINH

    return (
        (PRESET_GIU_HINH, N_('Giữ nguyên hình ảnh'),
         N_('Chỉ thay tiếng. Hình ảnh được sao chép nguyên vẹn, không cắt cảnh '
            'nào và không giảm chất lượng. Video ra dài đúng bằng video vào.')),
        # 🔴 **Cau cuoi la dinh chinh cua pha 27 (A26-05), va no la mot cau
        #    ve SAN PHAM chu khong phai mot cau rao truoc.**
        #
        #    Do duoc o pha 22, tren mot ban nguon co han mot canh **khong co
        #    mot cau thoai nao**: `so_canh 4, so_giu 4, so_cat 0`. Khach doc
        #    "bo bot nhung canh it noi dung", chap nhan mot cai gia chat luong
        #    doi lay dieu do, va nhan ve mot video dai y nguyen da bi ma hoa
        #    lai — tra tien cho mot thu khong xay ra.
        #
        # ⭐ Pha 27 da noi VLM vao mach nen viec cat GIO DA XAY RA duoc. Nhung
        #    no van co dieu kien: khong co bang chung thi **giu** (cat mu nguy
        #    hiem hon giu thua), va `SAN_GIU_LAI` chan khong cho cat qua nua
        #    thoi luong. Nen mot video ma moi canh deu dang gia van ra dung do
        #    dai cu — va khach phai biet dieu do TRUOC khi chon, khong phai sau
        #    khi nhan tep.
        (PRESET_CAT_THONG_MINH, N_('Rút gọn có biên tập'),
         N_('Bỏ bớt những cảnh ít nội dung để video ngắn lại. Vì phải ghép lại '
            'các đoạn được giữ nên hình ảnh sẽ được mã hoá lại — chất lượng gần '
            'như bản gốc nhưng không còn giống hệt từng điểm ảnh. Nếu không cảnh '
            'nào đủ căn cứ để bỏ thì video giữ nguyên độ dài, và vẫn được mã hoá '
            'lại.')),
    )


PRESET_BANG = _preset_bang()


def preset_hop_le(ma: str) -> bool:
    return any(ma == x[0] for x in PRESET_BANG)


def preset_mac_dinh() -> str:
    from .hop_dong_v4 import PRESET_MAC_DINH

    return PRESET_MAC_DINH


# ══════════════════════════════════════════════════════════════════════════════
#  Hai cach chon giong
# ══════════════════════════════════════════════════════════════════════════════
#
# ⚠️ `AUTO_MATCH` duoc bay ra nhung **noi that rang no chua san sang**: pha 19 ghi
#    lai rang khong giai doan nao sinh `HoSoNoiDung`, nen tu khop se hoan lai chu
#    khong chon bua mot giong. Bay mot lua chon khong chay duoc ma khong noi gi la
#    dung thu `V4_MVP_PRODUCT_CONTRACT` goi la "false feature".
def _giong_bang():
    from .hop_dong_v4 import CHE_DO_GIONG_TU_CHON, CHE_DO_GIONG_TU_KHOP

    return (
        (CHE_DO_GIONG_TU_CHON, N_('Tôi tự chọn giọng'),
         N_('Bạn chọn một giọng trong danh sách bên dưới.')),
        (CHE_DO_GIONG_TU_KHOP, N_('Để hệ thống gợi ý giọng'),
         N_('Hệ thống chọn giọng hợp với nội dung. Tính năng này đang được hoàn '
            'thiện — hiện tại hãy tự chọn giọng.')),
    )


CHE_DO_GIONG_BANG = _giong_bang()


def che_do_giong_hop_le(ma: str) -> bool:
    return any(ma == x[0] for x in CHE_DO_GIONG_BANG)


def che_do_hop_le(ma: str) -> bool:
    return any(ma == x[0] for x in CHE_DO_THOI_GIAN)


def giong_cua_toi(db, owner_id: str) -> list[dict]:
    """Giong ma CHINH chu so huu duoc dung.

    🔑 Danh sach nay do `ltt_voice` so huu, va ta hoi no thay vi tu truy van
       bang cua no — `test_421` chot dieu do. Mot phep loc `WHERE owner_id` viet
       tay o day la mot cho de quen menh de do, va quen no la mo duong dung
       giong nhan ban cua nguoi khac.
    """
    try:
        from apps.ltt_voice.doc_man_api import ma_giong_cua_toi
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        log.warning("khong nap duoc danh sach giong cua ltt_voice (%s: %s)",
                    type(exc).__name__, exc)
        return []

    # ⭐ `ma_giong_cua_toi` da loc `owner_id`, da xu ly kho giong dung chung, va
    #    da bo giong `active=False`. Ba viec do deu de lam sai neu tu viet lai,
    #    va cai thu nhat lam sai thi hau qua la khach dung giong cua nguoi khac.
    ra = []
    for g in ma_giong_cua_toi(db, owner_id) or []:
        # ⛔ Chi lay HAI truong. Chep nguyen doi tuong cua app kia sang day la de
        #    mot truong noi bo cua ho lot ra giao dien cua ta o lan doi sau.
        ma = str((g or {}).get("ma") or "")
        if ma:
            ra.append({"ma": ma, "ten": str(g.get("ten") or "") or "—"})
    return ra


def giong_chon_duoc(db, owner_id: str) -> list[dict]:
    """Moi giong khach duoc chon: giong CUA HO, cong giong MAU.

    🔴 **Truoc pha 21 giao dien moi khach chon "Giong mac dinh" — mot lua chon ma
       engine TU CHOI phuc vu.**

       Pha 09 da bo giong mac dinh im lang: `rang_giong` nem khi `USER_SELECTED`
       khong kem ma giong, vi "de trong roi lay mac dinh" la dung loi ma
       ADR-V4-001 D-V4-04 cam. Nhung o giao dien no van con, nen mot khach chon
       no se di qua bon giai doan, bi giu credit, roi hong o giua chuoi.

    ⭐ `V4_MVP_PRODUCT_CONTRACT` goi dung ten cho viec do: mot **false feature**.
       Cach sua khong phai lam engine de dai hon — la thoi moi mot thu khong co.

    ⇒ Danh sach nay LUON co giong mau, nen mot khach chua nhan ban giong nao van
      co thu de chon. Do la mot lua chon CO THAT, khac han mot o trong.
    """
    ra = list(giong_cua_toi(db, owner_id))
    da_co = {g["ma"] for g in ra}
    # ⛔ `loc()` chu khong `THEO_MA`. Ban dau toi lay thang cai dict noi bo, va
    #    `test_435::test_ASV_chi_cham_nhung_ten_da_khai` chan lai — dung. Mot dict
    #    noi bo la thu app kia duoc phep doi hinh dang bat cu luc nao; mot ham da
    #    khai la mot loi hua ho giu.
    try:
        from apps.ltt_voice.giong_mau import loc
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        log.warning("khong nap duoc giong mau (%s: %s)", type(exc).__name__, exc)
        return ra
    for g in loc() or []:
        ma = str(getattr(g, "ma", "") or "")
        if ma and ma not in da_co:
            # ⛔ Chi HAI truong, cung ly do nhu `giong_cua_toi`: chep nguyen doi
            #    tuong cua app kia la de mot truong noi bo cua ho lot ra giao dien
            #    cua ta o lan doi sau.
            ra.append({"ma": ma, "ten": str(getattr(g, "ten", "") or ma)})
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  V5 — thu giao dien can, va chi giao dien can
# ══════════════════════════════════════════════════════════════════════════════
#
# ⚠️ Ba ham duoi day **khong** tham gia mach tinh tien. Chung dung `uoc_credit`
#    o tren lam nguon duy nhat, va viec cua chung la BAY con so do ra cho khach
#    nhin thay truoc khi bam. Mot cong thuc thu hai o day se la mot bang gia thu
#    hai, va no se troi khoi bang gia that.

#: Bien do cua khoang hien cho khach, quanh `uoc_credit`.
#:
#: 🔴 Vi sao la mot KHOANG chu khong phai mot so.
#:
#:    `uoc_credit` uoc theo **do dai video**, vi luc bam ta chua co ban chep loi.
#:    Chi phi that ti le voi **luong noi**: mot video 10 phut im lang gan nhu
#:    khong ton gi, mot video 10 phut noi lien mach ton nhieu hon han. Mot con so
#:    don cho hai truong hop do la mot con so noi doi o it nhat mot trong hai.
#:
#: ⭐ Va no phai la mot khoang CO CAN TREN, khong phai "khoang 120". Khach can
#:    biet **toi da** mat bao nhieu de quyet dinh, va `features.tao_run` giu cho
#:    theo `uoc_credit` roi hoan phan du — nen can tren la thu ho thuc su doi mat.
BIEN_DO_UOC = 0.20


def uoc_khoang(thoi_luong_giay: float) -> tuple[int, int]:
    """`(thap, cao)` credit de hien cho khach. `cao` la thu ho doi mat."""
    giua = uoc_credit(thoi_luong_giay)
    thap = max(GIA_TOI_THIEU, int(giua * (1.0 - BIEN_DO_UOC)))
    cao = max(thap, int(round(giua * (1.0 + BIEN_DO_UOC))))
    return thap, cao


#: Boi so thoi gian xu ly so voi do dai video — cho DONG CHU "khoang bao lau".
#:
#: ⛔ CHUA DO, giong ba con so gia o dau tep. No o day de mot khach biet minh
#:    doi vai phut hay vai chuc phut, khong phai de ai tin no la mot cam ket.
#:
#: ⚠️ Va no **khong** duoc dung lam ETA cua mot lan chay dang chay:
#:    `V5_UI_INFORMATION_ARCHITECTURE.md` §7 cam gia ETA. ETA luc dang chay phai
#:    do tu chinh lan chay do; con so nay chi tra loi "co nen bat dau bay gio
#:    khong".
BOI_SO_THOI_GIAN = 3.0
THOI_GIAN_TOI_THIEU_S = 60


def uoc_thoi_gian_giay(thoi_luong_giay: float) -> int:
    return max(THOI_GIAN_TOI_THIEU_S,
               int(round(max(0.0, float(thoi_luong_giay or 0)) * BOI_SO_THOI_GIAN)))


def _nhan_loc() -> dict:
    """Ba mat de loc giong. Nhan lay TU `ltt_voice`, khong go tay o day.

    ⛔ Go tay ba bang nay la tao mot ban sao thu hai cua mot danh muc app khac
       so huu — va ngay ho them mot vung hay mot phong cach, ban sao o day im
       lang cu di.
    """
    try:
        # ⚠️ MOT dong, khong ngoac xuong dong.
        #
        #    `tools/lint_app_contract.py:427` doc import bang mot regex MOT
        #    DONG. Voi dang ngoac xuong dong, no doc ten dau thanh `(NHAN_GIOI`
        #    va **khong kiem chut nao** nhung ten nam o dong tiep theo.
        from apps.ltt_voice.giong_mau import NHAN_GIOI, NHAN_PHONG_CACH, NHAN_VUNG
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        log.warning("khong nap duoc nhan giong (%s: %s)", type(exc).__name__, exc)
        return {"gioi": {}, "vung": {}, "phong_cach": {}}
    return {"gioi": dict(NHAN_GIOI), "vung": dict(NHAN_VUNG),
            "phong_cach": dict(NHAN_PHONG_CACH)}


NHAN_LOC = _nhan_loc()


def giong_cho_giao_dien(db, owner_id: str) -> list[dict]:
    """`giong_chon_duoc` + ba nhan de loc + duong nghe thu.

    🔑 Vi sao khong sua thang `giong_chon_duoc`: ham do da co nguoi goi va da
       duoc chot o `test_447`. Mot ham RIENG cho giao dien giu cho mach cu khong
       doi hinh dang, va lam ro rang phan "nhan + duong nghe" la nhu cau cua
       **man hinh**, khong phai cua mach xu ly.

    ⚠️ Giong NHAN BAN cua khach khong co ba nhan — chung khong phai giong mau.
       Chung tra ve `gioi=""` va giao dien xep chung vao nhom rieng, thay vi bia
       ra mot nhan.

    ⭐ Giong khong co tep nghe thu thi **vang mat khoi `duong_nghe`**, khong phai
       mot chuoi rong. Do la hop dong cua `nghe_thu.duong_cho_trang`, va no co
       ly do: mot URL 404 cho ra mot nut phat bam duoc ma khong keu — dung thu
       te nhat.
    """
    co_ban = giong_chon_duoc(db, owner_id)

    thuoc_tinh: dict = {}
    try:
        from apps.ltt_voice.giong_mau import loc
        for g in loc() or []:
            thuoc_tinh[str(getattr(g, "ma", ""))] = {
                "gioi": str(getattr(g, "gioi", "") or ""),
                "vung": str(getattr(g, "vung", "") or ""),
                "phong_cach": str(getattr(g, "phong_cach", "") or ""),
            }
    except Exception as exc:      # noqa: BLE001
        log.warning("khong nap duoc thuoc tinh giong mau (%s: %s)",
                    type(exc).__name__, exc)

    duong: dict = {}
    try:
        # ⛔ KHONG doc `ltt_voice.manifest`. Mot manifest la thu ca nen tang
        #    doc — xuat no cho mot app khac la xuat ca `job_types`,
        #    `credit_cost`, `bao_tri`, `tables`, chi de lay mot chuoi duong dan.
        #    `test_435` chan dung viec do, va no chan dung.
        from apps.ltt_voice.nghe_thu import duong_cho_app_khac
        ma_mau = [m for m in thuoc_tinh]
        rieng = [g["ma"] for g in co_ban if g["ma"] not in thuoc_tinh]
        duong = duong_cho_app_khac(
            owner_id=owner_id, ma_mau=ma_mau, rieng=rieng) or {}
    except Exception as exc:      # noqa: BLE001 - kho co the chua san sang
        log.warning("khong dung duoc duong nghe thu (%s: %s)",
                    type(exc).__name__, exc)

    # ⚠️ Ten bien KHAC `g` o vong lap tren. Dung lai `g` khong sai luc chay,
    #    nhung `mypy` da suy `g: GiongMau` tu vong truoc va bao ba loi o day —
    #    `dict` khong gan duoc vao `GiongMau`, va `GiongMau` khong index duoc.
    #    Mot ten rieng noi dung thu no dang la, va lam ba loi do bien mat.
    ra = []
    for muc_goc in co_ban:
        ma = muc_goc["ma"]
        tt = thuoc_tinh.get(ma) or {}
        muc = {"ma": ma, "ten": muc_goc["ten"], "la_mau": ma in thuoc_tinh,
               "gioi": tt.get("gioi", ""), "vung": tt.get("vung", ""),
               "phong_cach": tt.get("phong_cach", "")}
        if ma in duong:
            muc["duong_nghe"] = duong[ma]
        ra.append(muc)
    return ra
