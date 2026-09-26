"""Gia mot lan chay, va lua chon san pham cho giao dien.

## 🔑 GIA PHANG — mot cong thuc, khong cong don

Chu du an chot 25/09/2026, nguyen van:

  > *"ta tam thoi bo qua xay dung. ta cu dat tinh chi phi theo phut video xu ly.
  >  dat tam la **10 credit / 1 phut video**. cho gon thay vi combenh cac buoc
  >  phuc tap. ta an dinh nhu the. de tap trung chinh vao he thong pipeline van
  >  hanh da."*

⇒ `credit = 10 x so phut video NGUON`. Khong con cong don theo tung nang luc.

Bon dieu da chot cung con so, va ca bon nam **trong ma** — khong o mot bang nao
nguoi doc phai tin:

1. **Lam tron LEN theo phut bat dau, toi thieu 1 phut.** 3 ph 10 s -> 4 phut ->
   40 credit (`so_phut_tinh_tien`). Va luat lam tron duoc **noi ra TRUOC khi
   khach bam** (`LUAT_LAM_TRON`, tra ve trong `xem_truoc_chi_phi`): mot con so
   nhay ra sau khi da tru tien la cach nhanh nhat de mat long tin.
2. **Do dai NGUON, khong do dai BAN RA.** Preset "Rut gon co bien tap" lam ban
   ra ngan hon; khach khong duoc thuong cung khong bi phat vi may cat bao nhieu,
   va ho **biet truoc** do dai nguon vi do la tep ho vua chon.
3. **Giu cho khi tao run, thu that khi `done`.** Ca hai dua tren do dai do bang
   `ffprobe` TU TEP (`nhap_media.soi` luc nop; `media_prepare.tom_tat.thoi_luong`
   trong mach) — khong phai mot con so doan. Xem `features.quyet_toan`.
4. **Khong giao duoc hang thi KHONG thu mot credit nao.** Xem
   `features.CHI_THU_KHI_GIAO_DUOC` + `features.co_hien_vat_giao_duoc` — so loi
   `N-21` la dung ca nay.

   🔴 **`done` KHONG DU, va cho nay ⛔ dung don cho gon.** 25/09/2026, mot luot
      E2E **that** 49 phut: `run.status == "done"`, bao QC `dat == True`, va
      `render.outputs.khoa_asset` **RONG** — khong mot tep nao ve tay khach. Luat
      chi hoi `done` se thu tron tien cho mot lan **giao hang rong**.

   ⇒ Nen dieu kien thu tien co HAI ve: trang thai `done` **VA** co hien vat that.
     Ve thu hai trong nhu thua (*"da `done` roi con gi"*) — no khong thua, va dong
     nay la thu duy nhat ngan mot lan "don dep" xoa no. Ca that: so loi `N-57`.

## ⛔ Mot cho khai, mot cho tinh

`GIA_CREDIT_MOI_PHUT` xuat hien **dung mot lan** trong ca kho, va moi con so
credit cua ASV di qua `tinh_credit`. Kho nay co ca mot ho loi *"hai cho khai mot
dieu, khong ai bat khop"* — mot cong thuc thu hai o route, o mot template hay
trong trinh duyet la mot **bang gia thu hai**, va no se troi khoi bang gia that
ngay lan dau ai do sua mot con so.

## 🔴 GIA THIET cua gia phang, va BIEN nao dieu khien no

Gia phang dung khi **phan lon luot chay di duong re**. Hai duong:

    che_do_render.SAO_CHEP        luong hinh duoc **chep** (`-c:v copy`) — mot
                                 lan chay 30 phut gan nhu khong ton mot giay
                                 ma hoa nao
    che_do_render.CAT_MA_HOA_LAI  **toan bo** video duoc ma hoa lai

⭐ **Bien dieu khien la PRESET, khong phai tap tinh nang.** `che_do_render.che_do_cho`
   nhan **dung mot** tham so — `preset` — va co phep kiem chot chu ky do. Nen duoi
   gia phang, cau hoi chi phi dung la:

       ✅ *"bao nhieu % luot di duong dat, va PRESET nao?"*

⛔ **KHONG phai** *"co bao nhieu % luot bi mot CO TINH NANG day sang duong dat?"*
   — cau do sai ve co che. Cac co bien tap (`vung_che`, `lop_phu`, `logo`,
   `phu_de` dot hinh, `bien_tap`, va `lat_guong`/`dich_mau` cua lan `asv-hinh`) bi
   `ban_dung.kiem` **tu choi** tren duong `SAO_CHEP`; chung chi ton tai o
   `PRESET_CAT_THONG_MINH`, **noi da ma hoa lai san**. Mot co nhu vay chi them
   mot bo loc mot-vao-mot-ra tren mot duong **von da** dat ⇒ no khong doi duong.

🔴 **Ghi lai vi sao doan nay duoc viet lai:** ban dau no khai nguoc — *"moi co
   day luot sang `cat_ma_hoa_lai`, nen gia thiet yeu dan"*. Do la mot suy luan tu
   **ly le**, va nguoi doc MA bac bo no trong nam phut. Cung ho voi hai ca khac
   trong ngay 25/09 (`3,284 am tiet/giay` — hang so chua ai do; *"chua do VRAM"*
   — ma khong he dung VRAM). ⇒ Mot ghi chu SAI trong ma song lau hon nguoi viet
   no, va nguoi sau se tin no.

⚠️ **CAU HOI MO — chua ai kiem, va ⛔ dung gia dinh theo chieu nao.** Hai co sap
   them chua duoc chung minh la co cung tinh chat *"chi song o preset da ma hoa
   lai"*:

       nhac_nen   (V3, lan `asv-nhac`)    tron nhac doi LUONG TIENG; luong hinh
                                          co con `-c:v copy` duoc khong?
       dien_nen   (V5, lan `asv-vung2`)   che vung la mot phep tren KHUNG HINH;
                                          no co bi chan o `SAO_CHEP` nhu
                                          `vung_che` khong?

   ⇒ Lan nao mo hai co ay: tra loi cau tren **bang ma**, roi ghi ket qua vao day.
     ⛔ Dung ghi mot phan doan vao cho nay.

⇒ Va gia **khong** doi trong ca hai chieu — chu du an chot *"an dinh nhu the"*, va
  ho chot de **go su combenh**, khong phai de toi uu bien loi nhuan. ⛔ Dung them
  mot nhanh gia theo tinh nang: do dung la su combenh vua duoc xoa.

⭐ Thay vao do, `quan_sat.dong_thoi_gian(cho_van_hanh=True)["duong_render"]` ghi
  **preset + duong di** cho tung lan chay, o **nhat ky ky thuat** — ⛔ khong o hoa
  don cua khach (khach tra mot gia phang; duong render la viec cua ta).
"""
from __future__ import annotations

import logging
import math

from platform_core.i18n import N_

log = logging.getLogger(__name__)

#: 🔑 Credit moi PHUT video NGUON. Chu du an an dinh 25/09/2026.
#:
#: ⛔ Con so nay xuat hien **dung mot lan** trong ca kho. Moi noi khac goi
#:    `tinh_credit` hoac doc chinh hang nay — ⛔ dung go lai `10`.
GIA_CREDIT_MOI_PHUT = 10

#: San toi thieu, tinh bang PHUT. Mot video 3 giay van la mot lan chay day du:
#: van khoi dong model, van tach nguon, van ket xuat.
PHUT_TOI_THIEU = 1

#: Cau noi LUAT LAM TRON cho khach, hien **TRUOC** khi ho bam.
#:
#: 🔴 Chu du an chot cung luc voi con so: *"phai hien cho khach thay luat lam
#:    tron truoc khi ho bam — mot con so nhay ra sau khi tru tien la cach nhanh
#:    nhat de mat long tin."*
#:
#: ⛔ `N_` chu khong `_t`: hang so cap MODULE. `_t` o day dong bang ngon ngu cua
#:    request DAU TIEN vao mot bien toan cuc — xem `routes.NHAN_GIAI_DOAN`.
#:
#: ⭐ `{don_gia}` duoc dien tu `GIA_CREDIT_MOI_PHUT` luc chay (`luat_lam_tron()`),
#:    ⛔ khong go so trong cau: mot con so go trong mot cau la mot ban khai thu hai.
LUAT_LAM_TRON = N_('Tính theo độ dài video gốc: {don_gia} credit mỗi phút, làm '
                   'tròn lên phút bắt đầu, tối thiểu 1 phút. Ví dụ video 3 phút '
                   '10 giây tính là 4 phút.')


def so_phut_tinh_tien(giay_video: float) -> int:
    """So phut tinh tien: lam tron **LEN**, toi thieu `PHUT_TOI_THIEU`.

    ⭐ Lam tron LEN chu khong lam tron GAN, va do la mot quyet dinh ve long tin
       chu khong ve doanh thu: khach tu nhan lai duoc con so tu do dai video ho
       dang nhin. Lam tron gan cho ra mot con so ho **phai tin** thay vi kiem.

        59 s -> 1 phut      60 s -> 1 phut      61 s -> 2 phut
        3 ph 10 s -> 4 phut
    """
    giay = max(0.0, float(giay_video or 0))
    return max(PHUT_TOI_THIEU, math.ceil(giay / 60.0))


def tinh_credit(giay_video: float) -> int:
    """Credit cua mot lan chay, tu do dai video **NGUON**.

    ⛔ Cong thuc DUY NHAT. Moi con so credit cua ASV — giu cho, quyet toan, xem
       truoc, hoa don — di qua ham nay.
    """
    return so_phut_tinh_tien(giay_video) * GIA_CREDIT_MOI_PHUT


def luat_lam_tron() -> str:
    """`LUAT_LAM_TRON` da dich va da dien don gia. Goi trong mot request."""
    from platform_core.i18n import _ as _t

    return _t(LUAT_LAM_TRON).format(don_gia=GIA_CREDIT_MOI_PHUT)


def hoa_don(giay_video: float) -> dict:
    """MOT dong hoa don cua khach: `<n> phut x 10 = <credit>`.

    ⭐ Thay cho bang nam dong theo nang luc (`quan_sat.chi_phi_theo_nang_luc`
       truoc 25/09): voi mot gia phang, **mot dong la toan bo su that**, va mot
       bang nam dong cho mot con so phang la mot bang noi doi ve **cach tinh**.

    ⚠️ Phan do luong theo nang luc **van con** — no chi khong o hoa don cua khach
       nua. `su_dung.so_ke` va `quan_sat.dong_thoi_gian(cho_van_hanh=True)` giu
       nguyen no, vi no tra loi cau *"cho nao dang dot tien"* cua nguoi van hanh.
    """
    return {
        "giay_nguon": round(max(0.0, float(giay_video or 0)), 3),
        "so_phut": so_phut_tinh_tien(giay_video),
        "don_gia": GIA_CREDIT_MOI_PHUT,
        # ⛔ `so_phut * don_gia` go lai o day la cong thuc thu hai. Goi `tinh_credit`.
        "credit": tinh_credit(giay_video),
    }


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
# ⭐ **23/09/2026 — `AUTO_MATCH` chay that, nen cau mo ta doi theo.**
#
#    Cau cu la *"tinh nang nay dang duoc hoan thien — hien tai hay tu chon
#    giong"*, va no dung luc viet: pha 19 ghi lai rang khong giai doan nao sinh
#    `HoSoNoiDung`, nen tu khop chi biet hoan lai roi chet o `content_process`.
#    `ho_so_noi_dung.py` dong lo hong do (F0 cua giong goc + ban chep loi), nen
#    giu cau cu lai la noi doi theo chieu nguoc lai.
#
# ⚠️ Cau moi van **khong hua** la luon chon duoc: khong du can cu thi lan chay
#    dung lai voi `rang_giong.vi_sao_chua_rang`, va khach phai tu chon. Mot cau
#    hua chac chan o day se bien mot trang thai hop le thanh mot loi hua bi be.
def _giong_bang():
    from .hop_dong_v4 import CHE_DO_GIONG_TU_CHON, CHE_DO_GIONG_TU_KHOP

    return (
        (CHE_DO_GIONG_TU_CHON, N_('Tôi tự chọn giọng'),
         N_('Bạn chọn một giọng trong danh sách bên dưới.')),
        (CHE_DO_GIONG_TU_KHOP, N_('Để hệ thống gợi ý giọng'),
         N_('Hệ thống nghe giọng người nói trong video và đọc lời thoại để chọn '
            'giọng hợp nhất. Nếu không đủ căn cứ, hệ thống sẽ báo để bạn tự chọn.')),
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
        # ⛔ Chi lay BA truong da khai. Chep nguyen doi tuong cua app kia sang
        #    day la de mot truong noi bo cua ho lot ra giao dien cua ta o lan
        #    doi sau.
        #
        # 🔴 `ngon_ngu` la truong THU BA, va no o day vi mot loi THAT: thieu no,
        #    `giong_cho_giao_dien` phat `data-lan=""` cho ca kho giong dung
        #    chung, `giong.js` doc "" la *chua ro lan ⇒ khong loc*, va khach
        #    bam "Bat dau" voi mot giong `en` trong khi dich la `vi` — an 400 o
        #    `giong_noi.giai_giong`. Cong chan DUNG; danh muc danh roi lan.
        ma = str((g or {}).get("ma") or "")
        if ma:
            ra.append({"ma": ma, "ten": str(g.get("ten") or "") or "—",
                       "ngon_ngu": str(g.get("ngon_ngu") or "")})
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
# ⚠️ Cac ham duoi day **khong** tham gia mach tinh tien. Chung dung `tinh_credit`
#    o tren lam nguon duy nhat, va viec cua chung la BAY con so do ra cho khach
#    nhin thay truoc khi bam. Mot cong thuc thu hai o day se la mot bang gia thu
#    hai, va no se troi khoi bang gia that.
#
# 🔴 **Truoc 25/09 cho nay la mot KHOANG (`uoc_khoang`, `BIEN_DO_UOC = 0.20`)**, va
#    ly do cua khoang ay dung luc no duoc viet: gia cu cong don theo tung nang luc,
#    nen chi phi that ti le voi **luong noi** trong khi ta chi biet **do dai** — mot
#    con so don noi doi o it nhat mot trong hai truong hop.
#
# ⭐ Gia phang xoa han ly do do: gia **la** mot ham cua do dai, va do dai thi da do
#    duoc bang `ffprobe` truoc khi khach bam. ⇒ Mot con so CHINH XAC, khong phai
#    mot khoang. Mot "khoang" quanh mot con so chinh xac la mot khoang bia ra.


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


def xem_truoc_chi_phi(giay_video: float) -> dict:
    """⭐ **HAM CHO LOP GUI** — moi thu mot man "truoc khi bam" can, mot lan goi.

    `hoa_don` + cau luat lam tron da dich + uoc thoi gian cho:

        {"giay_nguon", "so_phut", "don_gia", "credit",
         "luat_lam_tron", "thoi_gian_giay"}

    🔑 **`credit` la mot con so CHINH XAC, khong phai mot uoc.** Khach se bi giu
       dung so nay (`features.tao_run`) va bi thu dung so nay khi lan chay ve
       `done` (`features.quyet_toan`) — khong hon. Nen giao dien noi *"se tru N
       credit"*, ⛔ khong phai *"khoang N"*.

    ⛔ Giao dien **khong** duoc tu tinh lai bat cu so nao trong day, ke ca
       `so_phut x don_gia`. Do la ly do ham nay ton tai thay vi de route xuat ba
       hang so ra cho JavaScript ghep.

    ⭐ Va `luat_lam_tron` di **kem** con so, khong o mot trang tro giup khac: luat
       lam tron chi lam duoc viec cua no neu no o ngay canh con so no giai thich.
    """
    ra = hoa_don(giay_video)
    ra["luat_lam_tron"] = luat_lam_tron()
    ra["thoi_gian_giay"] = uoc_thoi_gian_giay(giay_video)
    return ra


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
                # 🔑 LAN cua giong mau. `rang_giong._rang_khach_chon` tu choi o
                #    CUA mot giong lech lan voi `ngon_ngu_dich`, nen giao dien
                #    phai loc truoc — nguoc lai khach doi dich sang `en`, thay
                #    nguyen 20 giong `vi`, bam Gui va an mot cau tu choi.
                #
                # 🔴 **SUA 26/09/2026.** Dong cu o day noi giong NHAN BAN
                #    "khong co truong nay, va do la co y". Menh de do SAI, va
                #    no da tra gia: hang `voice_profile` CO cot `ngon_ngu`, va
                #    `giong_noi.giai_giong` doc dung cot do de TU CHOI. Bo
                #    trong lan o danh muc khong lam cua nop de dai hon — no chi
                #    day cau tu choi tu luc CHON xuong luc BAM.
                #
                # ⇒ Lan cua giong khach di qua `giong_cua_toi` (truong thu ba).
                #    `""` con lai la *that su chua ro* — va MOT giong chua ro
                #    lan thi khong bi an, dung nhu truoc.
                "ngon_ngu": str(getattr(g, "ngon_ngu", "") or ""),
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
               "phong_cach": tt.get("phong_cach", ""),
               # ⭐ HAI nguon, mot thu tu: giong MAU lay lan tu `giong_mau`,
               #    giong cua khach / kho chung lay tu chinh hang CSDL
               #    (`voice_profile.ngon_ngu`) — dung cot ma `lan_ngon_ngu`
               #    doc de phan quyet. `""` con lai nghia la *that su chua ro*,
               #    ⛔ khong con nghia "giong nhan ban" nhu truoc 26/09.
               "ngon_ngu": (tt.get("ngon_ngu", "")
                            or str(muc_goc.get("ngon_ngu") or ""))}
        if ma in duong:
            muc["duong_nghe"] = duong[ma]
        ra.append(muc)
    return ra
