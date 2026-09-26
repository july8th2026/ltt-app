"""Nan mot doan loi thoai cho VUA khe thoi gian cua no.

## Bai toan, noi bang mot cau

Cau tieng Viet doc ra dai bao nhieu giay thi **khong biet truoc**. Pha 14 da noi
cho model biet ngan sach, va phan lon cau ra vua — nhung "phan lon" khong phai
"tat ca", va cai khong vua thi phai sua **rieng no**.

## Bac thang bon nac, va thu tu la mot phan cua chinh sach

    1. Doc ra, DO tren tep that                    (khong tin header may sinh tieng)
    2. Ngoai dung sai -> nho model VIET LAI cho vua, doc lai **rieng doan do**
    3. Het so vong -> cho phep CO GIAN nhe trong tran da khai
    4. Van khong duoc -> danh dau CAN SUA, khong giao bua

⛔ Nac 2 chi lam lai **mot doan**. Sinh lai ca kich ban vi mot cau khong vua la
   dieu `V4_RESOURCE_CPU_GPU_POLICY` cam dich danh, va no cung vo ly ve tien:
   mot cau hong lam hong hoa don cua ca tram cau con lai.

⛔ Nac 3 KHONG duoc dat truoc nac 2. Co gian am thanh lam giong meo di; viet lai
   mot cau cho ngan hon thi khong. Uu tien sua **noi dung** truoc khi sua **tin
   hieu** — mot cau khac mot chut van la giong nguoi, mot cau bi ep 1,3 lan thi
   khong.

## Vi sao dung sai KHONG doi xung

    dai hon khe  -> cau tran sang canh sau, hoac de len loi thoai ke tiep
    ngan hon khe -> mot khoang lang, ma `thoi_gian.py` von da biet cach nuot

Hai hau qua khong ngang nhau, nen hai nguong khong ngang nhau. Mot ban long tieng
hoi thua khoang lang van xem duoc; mot ban long tieng noi de len nhau thi khong.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from platform_core.i18n import _ as _t

#: Doi bat cu thu gi o duoi thi tang so nay. Vao van tay cua doan.
#:
#: 2 (23/09/2026): loi nhac nan mang `do_dai_toi_da` (tran DEM DUOC, cung nguon
#: voi pha viet dau) va `muc_tieu_giay` lay `ngon_ngu.HE_SO_MUC_TIEU`.
#:
#: 3 (25/09/2026): `SAN_DUNG_SAI_GIAY` (mot am tiet) duoi dung sai chieu DAI, va
#: chieu NGAN khong con goi model viet lai (`nen_viet_lai`).
#:
#: 4 (26/09/2026): `loi_nhac_nan_lo` — MOT loi nhac cho NHIEU doan, va phep do
#: khong con la TTS ma la `nan_thoi_luong.Khe.giay_can` (xem `giai_doan_giong`
#: khoi `[B]`). Doi chinh sach, nen tang theo dung hop dong cua hang so nay.
#:
#: ⚠️ Chu thich "vao van tay cua doan" o tren KHONG dung hom nay: `_van_tay` cua
#:    `giai_doan_giong` bam `ma + chu + giong + preset + tu_dien`, khong bam con
#:    so nay (do duoc 25/09 bang `grep`). Ghi lai, khong sua o day — ngoai pham vi.
PHIEN_BAN_NAN = 4

#: Vuot bao nhieu phan khe thi phai nan. Xem ghi chu dau tep ve tinh khong doi xung.
#:
#: 🔴 **Phai NHO HON `tran_co_gian() - 1`, va do khong phai mot y thich.**
#:
#:    Ban dau con so nay la 0,15 — dung bang tran co gian (1,15). Hau qua: nac 3
#:    cua bac thang **khong bao gio voi toi duoc**. Mot doan hoac nam trong dung
#:    sai (`VUA`), hoac da vuot ca tran co gian (`CAN_SUA`); khong co khoang nao
#:    de "khong vua nhung co gian nhe la du" ton tai. Bac thang bon nac tren
#:    giay chi con ba nac khi chay.
#:
#: ⭐ Va no khong hong ra loi nao: moi doan van co mot trang thai hop le, bao cao
#:    van day du, chi la mot nhanh chinh sach chua bao gio chay. Tim ra khi mot
#:    phep kiem co dung mot doan vao trang thai `CO_GIAN` va khong dat duoc.
#:
#: ⇒ 0,08: duoi 8% thi de yen; 8-15% thi thu viet lai, va neu viet lai khong an
#:   thi co gian van cuu duoc; tren 15% thi viet lai la co hoi that su duy nhat.
#:
#: ⚠️ Ban than con so 0,08 CHUA DO tren du lieu that — chon theo huong an toan.
#:    Pha 21 do lai. Nhung QUAN HE giua no va tran co gian thi da duoc chot.
DUNG_SAI_DAI = 0.08

#: SAN TUYET DOI cua dung sai chieu DAI, tinh bang GIAY.
#:
#: 0,256 s = mot am tiet, do tren giong san pham (hoi quy `giay = 0,188 + n x
#: 0,256`, R2 = 0,927, n = 47 doan cua luot `asvr_9fc9cc89`).
#:
#: 🔑 **Day la mot loi tinh KHONG NHAT QUAN duoc chua, khong phai mot ti le xau
#:    duoc noi ra.** `DUNG_SAI_DAI x khe` tren khe trung vi 1,71 s cho 137 ms,
#:    trong khi don vi thay doi NHO NHAT ma mot lan viet lai co the tao ra la
#:    mot am tiet = 256 ms. Doi `±137 ms` la dat mot cau hoi khong tra loi duoc
#:    — bat ke no cham bao nhieu doan (do duoc: 100/106, tuc 94 %).
#:
#: ⭐ Nguon ngoai, ca hai dat SAN TUYET DOI thay vi ti le: VideoLingo
#:    `tolerance: 1,5 s` (`config.yaml`); bot Viral `DUB_TRAN_MAX = 0,2 s`, bat
#:    mac dinh 24/08, ghi ro *"doi rang buoc tu 'gioi han toc do' sang 'gioi han
#:    tran'"* (`localize.py:9041`). Khao sat:
#:    `docs/auto_scan_video_final/NC_CAPCUT_VA_CONG_DONG.md` §D1.
#:
#: ⛔ **Dung ha xuong duoi mot am tiet**: duoi luong tu thi phan quyet la tung
#:    dong xu — ta tra tien cho mot lan viet lai khong the nham trung dich.
#:
#: ⚠️ KHONG phai `1 / ngon_ngu.NHIP[dich]` (= 299 ms voi `vi`), va khac biet la
#:    co y: `NHIP` la nhip TRUNG BINH, tuc no gom ca doan chan 0,188 s cua cau.
#:    San nay hoi CHI PHI BIEN cua mot am tiet — "them/bo mot am tiet doi do dai
#:    bao nhieu" — va do la 0,256 s. Lay `1/NHIP` se noi san rong hon su that.
SAN_DUNG_SAI_GIAY = 0.256

#: Ngan hon bao nhieu phan khe thi moi dang nan.
#:
#: ⭐ Rong hon gap doi phia kia, co y: `thoi_gian.lap_ke_hoach` da biet cach nuot
#:    khoang lang, nen mot cau ngan la mot van de no giai duoc. Goi model de keo
#:    dai mot cau chi vi no ngan 20% la tra tien cho mot thu khong ai nghe ra.
#:
#: 🔴 **Tu 25/09 con so nay chi con de PHAN LOAI / BAO CAO.** Lap luan ngay tren
#:    la dung, va tu 25/09 `nen_viet_lai` thi hanh no: mot doan qua NGAN khong
#:    goi model nua. Nguon: 0/5 he da khao sat (VideoLingo, SoniTranslate,
#:    open-dubbing, CapCut, bot Viral) co ve "viet lai cho DAI ra" —
#:    `NC_CAPCUT_VA_CONG_DONG.md` §D5. SoniTranslate kep 0,8-1,15 ve 1,0 (cau
#:    ngan toi 20 % thi KHONG lam gi); Viral `_nen_cau_tran` chi chon cue TRAN.
DUNG_SAI_NGAN = 0.35

#: So lan VIET LAI toi da cho mot doan (khong ke lan doc dau tien).
#:
#: 🔴 Con so nay la mot **tran cung**, khong phai mot goi y. Mot vong lap "sua
#:    cho toi khi vua" tren mot dich vu tra tien la mot hoa don khong co day, va
#:    `V4_RESOURCE_CPU_GPU_POLICY` cam "no infinite loop" bang chu.
#:
#: 🔑 **1 tu 26/09/2026** (truoc: 2). Ba can cu, ⛔ khong phai mot linh cam:
#:    - chu thich cua chinh `loi_nhac_nan` noi *"do la ly do vong thu hai
#:      thuong khong can den"* — vi loi nhac da dua mot muc tieu DO DUOC;
#:    - `VideoLingo` (18,5k★, Apache-2.0) da bo han vong hai: `##! No longer
#:      perform secondary trim`;
#:    - do 26/09: mot loi goi nan mat **15,6-17,7 giay**, nen vong hai la 16
#:      giay cho mot xac suat nho.
VONG_TOI_DA = 1

#: Tran co gian thoi gian o nac 3. Muon nguyen tu `thoi_gian.TRAN_TANG_TOC` —
#: mot con so, mot cho khai.
def tran_co_gian() -> float:
    from .thoi_gian import TRAN_TANG_TOC

    return float(TRAN_TANG_TOC)


#: Trang thai cua mot doan sau khi nan.
VUA = "vua"                 #: doc ra vua khe (hoac trong dung sai)
CO_GIAN = "co_gian"         #: khong vua nhung co gian nhe la du — nac 3

#: Doan NGAN hon khe qua `DUNG_SAI_NGAN` — ⛔ va ⛔ KHONG co gi duoc co gian ca.
#:
#: 🔴 **Truoc 25/09 chieu NGAN bi xep vao `CO_GIAN` voi `he_so = 1.0` va ghi chu
#:    *"khong vua nhung co gian nhe la du"*. Nhan ay SAI NGHIA**: `co_gian_du_khong`
#:    tra `(True, 1.0)` cho moi cau NGAN hon khe — duong tat o dau ham, dung y
#:    (*"mot cau NGAN hon khe khong can co gian gi ca"*) — nen "co gian nhe la du"
#:    thuc ra ke ve mot phep co gian ⛔ CHUA TUNG chay. Nguoi doc bao cao thay
#:    `so_co_gian` va tuong ta da xu ly bang xu ly tin hieu.
#:
#: ⭐ Su that la: `thoi_gian.lap_ke_hoach` **nuot khoang lang** — cau ngan chi
#:    de lai mot khoang im ⛔ khong ai de y (`nan_cho_vua.py` §DUNG_SAI_NGAN,
#:    SoniTranslate kep 0,8-1,15 ve 1,0). ⇒ Dung trang thai NAY, ⛔ dung `CO_GIAN`.
#:
#: ⚠️ Loi co san, ⛔ nhung bo ve viet-lai-cho-DAI (25/09, `nen_viet_lai`) lam no
#:    PHO BIEN han: truoc do mot phan cac doan ngan con di qua vong viet lai va
#:    doi trang thai; nay chung ⛔ khong con duong nao khac.
NGAN = "ngan"

CAN_SUA = "can_sua"         #: het bac thang ma van khong vua — nac 4
TRANG_THAI = (VUA, CO_GIAN, NGAN, CAN_SUA)


def _kiem_chinh_sach() -> None:
    """No luc NAP MODULE neu bac thang tu mau thuan.

    ⛔ Dat o cap module, co chu y: mot chinh sach tu mau thuan phai chan viec nap
       app chu khong doi mot phep kiem chay den. Cung khuon voi
       `hop_dong_v4._kiem_tra_hop_dong`.

    ⛔ **`SAN_DUNG_SAI_GIAY` KHONG duoc dua vao khang dinh nay.** `DUNG_SAI_DAI`
       va `tran_co_gian() - 1` la hai TI LE khong don vi; san la GIAY tuyet doi.
       So chung voi nhau la dung mot cai bay moi: bat dang thuc se doc duoc va
       luon "dung" o mot khe nao do, va luon "sai" o mot khe khac.
    """
    if DUNG_SAI_DAI >= tran_co_gian() - 1.0:
        raise AssertionError(
            "DUNG_SAI_DAI (%.3f) >= tran co gian - 1 (%.3f): nac CO_GIAN cua bac "
            "thang khong bao gio voi toi duoc" % (DUNG_SAI_DAI, tran_co_gian() - 1.0))


class NanError(ValueError):
    """Ban nan khong dung hop dong."""


@dataclass(frozen=True)
class KetQuaNan:
    """Ket qua nan MOT doan. `chu` la van ban CUOI CUNG da dung."""

    ma: str
    trang_thai: str
    chu: str
    giay: float
    khe: float
    so_vong: int = 0
    he_so_co_gian: float = 1.0
    ghi_chu: dict = field(default_factory=dict)

    @property
    def dat(self) -> bool:
        return self.trang_thai in (VUA, CO_GIAN, NGAN)


def khe_cua(m: dict) -> float:
    """Khe thoi gian cua mot doan = do dai cua chinh no trong ban goc.

    ⭐ Khong phai mot ngan sach do pha 16 chia: pha 16 chay SAU va no can biet
       doan nao vua doan nao khong de chia cho khon. Lay khe goc o day giu hai
       pha doc lap — va khe goc cung la thu khan gia thay: cau thoai phai khop
       voi cai mieng dang nhep tren man hinh.
    """
    try:
        return max(0.0, float(m.get("ket") or 0.0) - float(m.get("bat") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def lech(giay: float, khe: float) -> float:
    """Lech tuong doi so voi khe. Duong = dai hon khe."""
    if khe <= 0:
        return 0.0
    return (float(giay) - float(khe)) / float(khe)


def dung_sai_giay(khe: float) -> float:
    """Dung sai chieu DAI cua mot khe, tinh bang GIAY — ti le, nhung co SAN.

    🔑 `max(ti le, san)`: ti le giu dung y ban dau (khe dai thi duoc phep tran
       nhieu hon theo do dai), san chan viec doi mot do chinh xac nho hon mot am
       tiet — xem `SAN_DUNG_SAI_GIAY`.
    """
    if khe <= 0:
        return 0.0
    return max(DUNG_SAI_DAI * float(khe), SAN_DUNG_SAI_GIAY)


def can_nan(giay: float, khe: float) -> bool:
    """Doan nay co ngoai dung sai khong.

    ⚠️ Chieu DAI do bang GIAY (`dung_sai_giay`), chieu NGAN van do bang TI LE
       (`DUNG_SAI_NGAN`) — chieu ngan chi con dung de PHAN LOAI (`ket_luan`,
       `tom_tat`), khong con mo duong goi model: xem `nen_viet_lai`.
    """
    if khe <= 0:
        return False
    if float(giay) - float(khe) > dung_sai_giay(khe):
        return True
    return lech(giay, khe) < -DUNG_SAI_NGAN


def nen_viet_lai(giay: float, khe: float) -> bool:
    """Co duoc phep TRA TIEN cho mot lan model viet lai doan nay khong?

    🔴 **Chi chieu DAI.** Mot doan qua NGAN khong bao gio vao day (chot 25/09):
       `thoi_gian.lap_ke_hoach` da biet nuot khoang lang, nen cau ngan la van de
       no giai duoc — va 0/5 he da khao sat co ve "viet lai cho dai ra".

    ⭐ Tach khoi `can_nan` chu khong sua `can_nan`: `can_nan` tra loi *"doan nay
       co vua khong"* (phan loai, bao cao), ham nay tra loi *"co dang goi model
       khong"* (tien). Gop hai cau hoi vao mot ham la cach chac chan de mot ngay
       nao do mot ben keo ben kia di theo.
    """
    return can_nan(giay, khe) and float(giay) > float(khe)


def co_gian_du_khong(giay: float, khe: float) -> tuple[bool, float]:
    """Nac 3: co gian nhe co keo duoc doan nay ve khe khong, va he so bao nhieu.

    ⛔ Chi tang toc (cau DAI hon khe) moi bi tran chan. Mot cau NGAN hon khe
       khong can co gian gi ca — `thoi_gian.py` chen khoang lang, va do la cach
       dung: keo dai mot cau bang xu ly tin hieu nghe ra ngay, con mot khoang
       lang thi khong ai de y.
    """
    if khe <= 0 or giay <= 0:
        return True, 1.0
    if giay <= khe:
        return True, 1.0
    he_so = float(giay) / float(khe)
    return he_so <= tran_co_gian(), he_so


# ══════════════════════════════════════════════════════════════════════════════
#  Loi nhac viet lai
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac_nan(m: dict, *, chu_hien_tai: str, giay_do_duoc: float,
                 khe: float, ngon_ngu_dich: str = "vi") -> list[dict]:
    """Loi nhac cho `ai.RUT_NGAN_CHO_VUA`. MOT doan, khong phai mot lo.

    🔑 Dua vao ca **do dai da DO DUOC**, khong chi khe muc tieu. Do la khac biet
       giua "hay viet ngan hon" va "cau nay doc ra 4,8 giay, khe co 3,2 giay, hay
       viet lai cho khoang 3,0 giay": cai sau cho model mot muc tieu kiem duoc,
       va no la ly do vong thu hai thuong khong can den.

    🔴 **BAT BIEN O BIEN (25/09): chi RUT NGAN.** Ve "viet lai cho DAI ra" da bo
       (`nen_viet_lai`), va cho nay NEM chu khong am tham soan mot loi nhac keo
       dai: mot cai chan o vong lap ma khong co chan o bien la mot cai chan mot
       nguoi goi moi se di vong qua ma khong ai thay. Nem o day thi hoa don noi
       ra ngay — con nuot thi no chi hien len o bang gia cuoi thang.
    """
    if float(giay_do_duoc) <= float(khe):
        raise NanError(
            "loi_nhac_nan chi RUT NGAN: doc ra %.3fs <= khe %.3fs. Ve viet lai "
            "cho dai ra da bo 25/09 — xem `nen_viet_lai`"
            % (float(giay_do_duoc), float(khe)))
    viec = "RUT NGAN"
    from . import ngon_ngu
    c = ngon_ngu.cum(ngon_ngu_dich)
    he_thong = (
        f"Ban la bien tap vien long tieng {c['tieng']}. Mot cau da viet **khong vua**"
        " khe thoi gian cua no.\n"
        f"Viec cua ban: {viec} cau do, giu NGUYEN y nghia va thai do.\n"
        "Quy tac:\n"
        "- Khong bo mat thong tin nao trong cau.\n"
        "- Khong them thong tin khong co trong cau.\n"
        f"- Van phai la {c['tieng']} noi tu nhien, khong phai van viet rut gon.\n"
        f"- Nham dung `muc_tieu_giay`; {c['nhip_moi_giay']}.\n"
        # 🔑 Cung mot TRAN DEM DUOC voi pha viet dau (`long_tieng.loi_nhac`).
        #    Hai pha nham hai dich khac nhau tren cung mot khe la cach chac chan
        #    nhat de vong hai khong hoi tu.
        f"- **KHONG QUA `do_dai_toi_da` {c['don_vi']}** — dem lai truoc khi tra ve.\n"
        'Tra ve DUY NHAT: {"doan": {"chu": "..."}}')
    nguoi_dung = json.dumps({
        "ma": str(m.get("ma") or ""),
        "goc": str(m.get("goc") or ""),
        "chu_hien_tai": str(chu_hien_tai or ""),
        "doc_ra_het_giay": round(float(giay_do_duoc), 2),
        "khe_giay": round(float(khe), 2),
        # Nham thap hon khe mot chut: vua khit la vua **du** de mot dao dong nho
        # cua may sinh tieng lam no tran ra lai.
        #
        # 🔴 `ngon_ngu.HE_SO_MUC_TIEU`, khong phai mot `0.92` go tay. Truoc
        #    23/09 con so nay chi ton tai o day, va pha viet dau khong he co no.
        "muc_tieu_giay": round(max(0.3, float(khe) * ngon_ngu.HE_SO_MUC_TIEU), 2),
        "do_dai_toi_da": ngon_ngu.ngan_sach_do_dai(khe, ngon_ngu_dich),
    }, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def loi_nhac_nan_lo(cac: list[dict], *, ngon_ngu_dich: str = "vi") -> list[dict]:
    """MOT lời nhắc cho NHIỀU đoạn cần rút ngắn.

    🔴 **Bản cũ `loi_nhac_nan` là MỘT đoạn một lời gọi**, và đo 26/09: mỗi lời gọi
       **15,6–17,7 giây**. Hàng chục đoạn ⇒ hàng chục lần khứ hồi.

    ⭐ Mỗi mục mang `truoc`/`sau` để model thấy ngữ cảnh: rút một câu mà ⛔ không
       biết câu kế nói gì thì dễ rút mất chủ ngữ mà câu sau đang trỏ tới.

    ⚠️ Khoá JSON là **mã đoạn**, và người gọi phải kiểm `set(cần) − set(nhận)` —
       mượn ba lớp chống lẫn id của `VideoLingo` (Apache-2.0).
    """
    bang = {d["ma"]: {"chu": d["chu"],
                      "doc_ra_giay": round(float(d["giay_doc"]), 2),
                      "khe_giay": round(float(d["khe"]), 2),
                      "cau_truoc": d.get("truoc", ""),
                      "cau_sau": d.get("sau", "")}
            for d in cac}
    return [
        {"role": "system", "content": (
            "Moi muc duoi day la mot cau tieng Viet doc ra DAI HON khe thoi gian "
            "cua no. Viet lai NGAN hon de doc vua `khe_giay`, giu nguyen y.\n"
            "Tra ve DUY NHAT mot doi tuong JSON, khoa la ma doan, gia tri la cau "
            "moi. Phai co DU moi ma. Khong them ma moi, khong giai thich.\n"
            "`cau_truoc` va `cau_sau` chi de hieu ngu canh — KHONG dich chung.")},
        {"role": "user", "content": json.dumps(bang, ensure_ascii=False)},
    ]


def doc_nan_lo(goi: dict, *, can: set[str]) -> dict[str, str]:
    """Doc phan hoi LO cua `loi_nhac_nan_lo` -> `{ma: cau moi}`. ⛔ Khong nem.

    ⭐ Song sinh cua `doc_nan`, va no o canh `loi_nhac_nan_lo` co y: loi nhac va
       nguoi doc phan hoi cua no phai nam CANH NHAU, vi chung khai cung mot hinh
       dang. Hai tep xa nhau la cach `DOC_CANH` tung khai `("canh",)` cho mot loi
       nhac chua bao gio co khoa `canh` (xem `ai.py`).

    ⛔ **Loc theo `can`, ⛔ khong nhan bua moi khoa model tra ve.** Mot `ma` la
       xuoc, mot `ma` bia ra, hay mot khoa cua lo KHAC deu se ghi de len cau cua
       mot doan ta ⛔ khong he xin nan — tuc doi loi thoai cua khach o mot cho
       khong ai nhin. Ba lop chong lan id cua `VideoLingo`, lop thu nhat.

    ⛔ Va ⛔ khong nem: mot ma thieu ⛔ khong dang lam chet ca luot chay — nguoi
       goi giu cau goc cho ma do va ghi `log.warning`. `set(can) - set(ra)` la
       cach nguoi goi biet phai xin lai lo nao.
    """
    ra: dict[str, str] = {}
    for khoa, gt in (goi or {}).items():
        ma = str(khoa)
        if ma not in can:
            continue
        # ⭐ Chiu ca hai hinh dang model hay tra: chuoi tran, hoac `{"chu": ...}`
        #    (no vua doc mot loi nhac dung khoa `chu` cho van ban dau vao).
        chu = gt.get("chu") if isinstance(gt, dict) else gt
        chu = str(chu or "").strip()
        if chu:
            ra[ma] = chu
    return ra


def doc_nan(goi: dict) -> str:
    """Lay cau da viet lai. Nem neu model khong tra ve gi dung duoc."""
    doan = (goi or {}).get("doan")
    chu = ""
    if isinstance(doan, dict):
        chu = str(doan.get("chu") or "").strip()
    elif isinstance(doan, str):
        chu = doan.strip()
    if not chu:
        raise NanError(_t('Model không trả về câu đã viết lại.'))
    return chu


def ket_luan(ma: str, *, chu: str, giay: float, khe: float,
             so_vong: int) -> KetQuaNan:
    """Xep mot doan vao mot trong ba trang thai, sau khi da het bac thang."""
    if not can_nan(giay, khe):
        return KetQuaNan(ma, VUA, chu, float(giay), float(khe), so_vong)
    # 🔴 Chieu NGAN truoc chieu DAI, va do la ca ban sua: `co_gian_du_khong` tra
    #    `(True, 1.0)` cho moi cau ngan hon khe, nen de no roi vao `CO_GIAN` la
    #    khai mot phep co gian ⛔ CHUA TUNG chay. Xem `NGAN`.
    if float(giay) <= float(khe):
        return KetQuaNan(ma, NGAN, chu, float(giay), float(khe), so_vong,
                         he_so_co_gian=1.0,
                         ghi_chu={"ly_do": "ngan hon khe — khoang lang duoc "
                                           "nuot, khong co gian gi",
                                  "dung_sai_ngan": DUNG_SAI_NGAN})
    duoc, he_so = co_gian_du_khong(giay, khe)
    if duoc:
        return KetQuaNan(ma, CO_GIAN, chu, float(giay), float(khe), so_vong,
                         he_so_co_gian=round(he_so, 4),
                         ghi_chu={"ly_do": "khong vua nhung co gian nhe la du"})
    return KetQuaNan(ma, CAN_SUA, chu, float(giay), float(khe), so_vong,
                     he_so_co_gian=round(he_so, 4),
                     ghi_chu={"ly_do": "vuot ca tran co gian",
                              "tran": tran_co_gian()})


def ban_ghi_luot_doc(ma: str, *, vong: int, giay: float, khe: float) -> dict:
    """MOT ban ghi cho MOT LUOT DOC — ⛔ khong phai cho mot doan.

    🔴 **Vi sao phai co (do duoc 25/09).** Luot `asvr_9fc9cc89` (275 s, 106 doan)
       cho 59 doan vao nac 2 va 65 luot goi may B, LLM chiem ~52 % giai doan. Nhung
       `tung_doan` chi cat giay CUOI CUNG (sau nan), va giay LAN DOC DAU cua 59
       doan ay bi ghi de trong thu muc tam moi vong — khong log, khong persist.
       ⇒ ⛔ **khong ai tinh duoc mot ban sua nguong tiet kiem bao nhieu luot goi.**

    ⭐ Ghi vao `outputs` de TRUY VAN duoc, giong `cat_doan.chan` — mot dong log
       dang chu thi luot sau khong ai doc.

    ⛔ KHONG mang `chu`: cung ly do voi `tung_doan` — loi thoai la noi dung cua
       khach, con day la sieu du lieu cua giai doan.

    `vong` = so vong NAN da chay TRUOC luot doc nay. `0` = lan doc dau tien.
    """
    return {"ma": str(ma), "vong": int(vong),
            "giay": round(float(giay), 3), "khe": round(float(khe), 3),
            "lech": round(lech(giay, khe), 4),
            # ⭐ Phan quyet CUA CHINH LUOT DOC AY, dong hang voi giay cua no. Mot
            #    luot sau doi `SAN_DUNG_SAI_GIAY` roi doc lai so cu se tinh ra
            #    mot phan quyet KHAC — va khong biet minh dang doi nguong.
            "can_nan": bool(can_nan(giay, khe)),
            "nen_viet_lai": bool(nen_viet_lai(giay, khe))}


def tom_tat(cac: list[KetQuaNan], *,
            tung_luot_doc: list[dict] | None = None) -> dict:
    """Bao cao cua giai doan. `tung_luot_doc` = ban ghi TUNG LUOT DOC (buoc 0.5).

    ⚠️ `tung_doan` (mot dong moi DOAN, giay CUOI CUNG) va `tung_luot_doc` (mot
       dong moi LUOT DOC, giay DO DUOC luc ay) tra loi hai cau khac nhau. Doan
       khong phai nan co dung mot dong o ca hai; doan nan hai vong co mot dong o
       `tung_doan` va ba dong o `tung_luot_doc`.
    """
    dem = {t: 0 for t in TRANG_THAI}
    for k in cac:
        dem[k.trang_thai] = dem.get(k.trang_thai, 0) + 1
    return {
        # 🔴 **Tu 25/09 con so nay la so KHE DOC, ⛔ khong con la so `ma` cua
        #    `content.json`** — `nan_thoi_luong.gop_khe` dieu khien that, nen MOT
        #    luot doc (mot `KetQuaNan`) phu 2-4 `ma`. Hai con so nay tach doi tai
        #    day, va bao cao khai CA HAI: `so_doan` (day) va `so_ma_noi_dung`
        #    (`giai_doan_giong`). ⛔ Ten giu nguyen co y: `test_476`/`test_4600`
        #    chot rang khoa gop cu ⛔ khong bao gio bien mat khoi bao cao.
        "so_doan": len(cac),
        **{f"so_{t}": dem.get(t, 0) for t in TRANG_THAI},
        "so_vong_tong": sum(k.so_vong for k in cac),
        "lech_lon_nhat": round(max((abs(lech(k.giay, k.khe)) for k in cac),
                                   default=0.0), 4),
        # ⭐ V6 pha 22. Tung doan, de NGUONG `DUNG_SAI_DAI` do duoc tren du lieu
        #    that. Truoc day chi co con so gop (so_vua / so_can_sua / lech lon
        #    nhat), va con so gop khong tra loi duoc *"bao nhieu doan nam gan
        #    nguong 0,08"* — tuc khong tra loi duoc chinh cau hoi ma chu thich
        #    cua hang so do tu khai la CHUA DO.
        #
        # ⛔ KHONG ghi `chu`: day la sieu du lieu cua giai doan, con loi thoai
        #    la noi dung cua khach. Mot con so thi du de do nguong.
        #
        # ⚠️ Khong nang `PHIEN_BAN_NAN`: day la hinh dang BAO CAO, khong phai
        #    chinh sach nan — khong mot doan nao doi trang thai hay doi am thanh.
        "tung_doan": [{"ma": k.ma, "trang_thai": k.trang_thai,
                       "giay": round(k.giay, 3), "khe": round(k.khe, 3),
                       "lech": round(lech(k.giay, k.khe), 4),
                       "so_vong": k.so_vong,
                       "he_so_co_gian": k.he_so_co_gian} for k in cac],
        # ⭐ Buoc 0.5 (25/09). Xem `ban_ghi_luot_doc` ve vi sao.
        #
        # ⚠️ `so_luot_do` KHAC `so_luot_doc` cua `giai_doan_giong.tom_tat`: cai
        #    sau dem moi lan goi may sinh tieng trong LAN CHAY NAY, cai nay dem
        #    ban ghi thu ve duoc — mot doan dung lai tep cu (`tu_cu`) khong co
        #    luot doc nao nen khong co ban ghi nao. ⛔ Dung lay hai so nay tru
        #    nhau ma khong doc hai chu thich.
        "tung_luot_doc": list(tung_luot_doc or []),
        "so_luot_do": len(tung_luot_doc or []),
    }


_kiem_chinh_sach()
