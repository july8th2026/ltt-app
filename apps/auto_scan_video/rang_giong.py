"""RANG GIONG — Auto Scan quyet dinh CHON giong nao; LTT Voice so huu giong do.

## Ranh gioi, viet ra de khong ai phai doan

    ASV so huu        chinh sach chon: che do, dac diem mong muon, luc nao chot
    LTT VOICE so huu  chinh giong, quyen so huu, tong hop, GPU, chuan hoa van ban

⇒ Tep nay **khong sinh mot mili-giay tieng nao**. No tra loi dung mot cau hoi:
  *lan chay nay se doc bang giong nao, va can cu vao dau.*

## 🔴 `AUTO_MATCH` khong duoc thoai hoa thanh "giong mac dinh"

`ADR-V4-001` D-V4-04 cam dieu do bang ten, va V2 da mac dung loi ay:
`routes.py:135` khai `giong_id: str = Form("")` roi de trong thi lay mac dinh.
Do la mot thu KHAC han: mot gia tri mac dinh **khong doc gi tu video ca**.

Cho nen o day, `AUTO_MATCH` ma chua co `HoSoNoiDung` thi ket qua la
**`CHUA_RANG`** — mot trang thai hop le, khong phai mot that bai va cung khong
phai mot giong. Tang tren phai hoi lai sau khi pha 11 dung xong ho so.

⭐ **23/09/2026 — nguoi dung ho so do CUOI CUNG cung ton tai.**
   `ho_so_noi_dung.py` sinh `HoSoNoiDung` tu bang chung lan chay DA tra tien
   (F0 cua stem `vocals` + ban chep loi), o CA HAI preset, va ghi no vao
   `run.settings["dac_diem_giong"]`. `CHUA_RANG` **khong** bi lam nhe di mot
   chut nao: no van la ket qua khi khong do duoc va model khong tra loi duoc.
   Thu doi la: tu cho "luon luon" no tro thanh "khi that su khong co can cu".

⛔ Va `ma_giong()` **nem** neu goi tren mot rang buoc chua chot. Mot ham tra ve
   `""` o day se cho ra mot lan tong hop bang giong mac dinh ma khong ai bam
   nut — tuc dung ket qua ma ca thiet ke nay dung de tranh.

## Vi sao "hoan lai" chu khong "chon tam roi sua"

Chon tam mot giong roi doi sau nghe co ve mem hon, nhung no tao ra mot cua so
trong do lan chay **da co mot giong** va bat cu buoc nao chay som deu dung phai
giong tam do. Pha 14 (chuyen loi thoai) phu thuoc vao giong that — no doi do dai
cau theo toc do doc cua giong — nen mot giong tam se sinh ra mot ban chuyen loi
phai lam lai. Mot trang thai "chua co" doc duoc thi chan viec do; mot gia tri
tam thi khong.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from platform_core.i18n import _ as _t

from . import ngon_ngu

from .hop_dong_v4 import (CHE_DO_GIONG, CHE_DO_GIONG_MAC_DINH,
                          CHE_DO_GIONG_TU_CHON, CHE_DO_GIONG_TU_KHOP)

#: Trang thai cua mot rang buoc giong.
CHUA_RANG = "chua_rang"
DA_RANG = "da_rang"
TRANG_THAI: tuple[str, ...] = (CHUA_RANG, DA_RANG)

#: Nguon cua quyet dinh — de hoa don va man ho tro noi duoc "vi sao giong nay".
NGUON_KHACH_CHON = "khach_chon"
NGUON_TU_KHOP = "tu_khop"


class RangGiongError(ValueError):
    """Yeu cau rang giong khong hop le."""


class ChuaRangError(RangGiongError):
    """Doc giong tu mot rang buoc chua chot.

    ⛔ La mot loi, khong phai mot chuoi rong. Xem docstring dau tep.
    """


@dataclass(frozen=True)
class DacDiemMongMuon:
    """Dac diem nguoi noi ma `AUTO_MATCH` muon khop.

    ⭐ Ba mat nay **khong phai do ASV nghi ra** — chung la dung ba mat ma
       `ltt_voice.giong_mau` da phan loai catalog cua no (`NHAN_GIOI`,
       `NHAN_VUNG`, `NHAN_PHONG_CACH`). Bia them mot mat thu tu se cho ra mot bo
       loc khong bao gio khop.

    ⚠️ Chuoi rong = **khong rang buoc mat do**, khong phai "khong biet". Hai
       nghia do khac nhau, va `co_du_de_khop` phan biet chung.
    """

    gioi: str = ""
    vung: str = ""
    phong_cach: str = ""

    @property
    def co_du_de_khop(self) -> bool:
        """It nhat MOT mat co rang buoc.

        ⛔ Khong mat nao rang buoc thi `loc()` tra ve ca catalog, va "lay cai
           dau tien" cua ca catalog chinh la giong mac dinh doi ten.
        """
        return bool(self.gioi or self.vung or self.phong_cach)


@dataclass(frozen=True)
class YeuCau:
    """Yeu cau rang giong. ASV dung xong pha 09; pha 11 dien not `dac_diem`."""

    che_do: str = CHE_DO_GIONG_MAC_DINH
    #: Chi cho `USER_SELECTED`. Ma giong cua khach hoac ma giong mau.
    giong_id: str = ""
    #: Chi cho `AUTO_MATCH`. Rong o pha 09; pha 11 dien tu `HoSoNoiDung`.
    dac_diem: DacDiemMongMuon = field(default_factory=DacDiemMongMuon)
    #: Ngon ngu ban long tieng se doc (22/09). Giong phai o CUNG lan: Q121 cua
    #: LTT Voice tu choi van ban lech lan o GIONG — tuc sau khi da tra LLM.
    ngon_ngu_dich: str = ngon_ngu.DICH_MAC_DINH

    def __post_init__(self) -> None:
        if self.che_do not in CHE_DO_GIONG:
            raise RangGiongError(f"che do giong khong biet: {self.che_do!r}")
        if self.che_do == CHE_DO_GIONG_TU_CHON and not self.giong_id:
            raise RangGiongError(
                "USER_SELECTED phai kem ma giong — de trong roi lay mac dinh la "
                "dung loi ma ADR-V4-001 D-V4-04 cam")


@dataclass(frozen=True)
class KetQua:
    """Ket qua rang giong. `trang_thai == CHUA_RANG` la mot ket qua HOP LE."""

    trang_thai: str
    giong_id: str = ""
    nguon: str = ""
    #: Vi sao lai la giong nay — cho man ho tro va cho hoa don.
    can_cu: dict = field(default_factory=dict)

    @property
    def da_chot(self) -> bool:
        return self.trang_thai == DA_RANG

    def ma_giong(self) -> str:
        """⛔ Nem neu chua chot. Xem docstring dau tep."""
        if not self.da_chot:
            raise ChuaRangError(
                _t('Chưa chọn được giọng cho lần chạy này — cần hồ sơ nội dung '
                   'trước khi tự khớp.'))
        return self.giong_id


def tu_thiet_lap(settings: dict) -> YeuCau:
    """Doc yeu cau tu `AsvRun.settings`. Khong cham CSDL."""
    s = dict(settings or {})
    che_do = str(s.get("che_do_giong") or CHE_DO_GIONG_MAC_DINH)
    dd = s.get("dac_diem_giong") or {}
    # 🔴 **Hai khoa cho cung mot thu, va chung da song song ma khong ai noi.**
    #
    #    Pha 09 dung `giong_id`; nhung `giai_doan_giong.py` — da chay tu truoc —
    #    doc `settings["voice_id"]`. Nen mot lan chay co the viet loi thoai CHO
    #    mot giong roi **doc len bang mot giong khac**, va khong cho nao bao loi:
    #    ca hai deu tim thay mot gia tri hop le cua rieng minh.
    #
    # ⭐ Nhan CA HAI o day, uu tien `giong_id`. Day khong phai chieu long mot ten
    #    khoa cu — do la mot lan hop nhat: mot cau hoi ("giong nao?") phai co MOT
    #    cho tra loi. Pha 15 se lam not phia con lai: `giai_doan_giong` phai lay
    #    giong tu `ma_giong` da dong bang trong ban long tieng chu khong tu doc
    #    `settings` nua.
    return YeuCau(
        che_do=che_do,
        giong_id=str(s.get("giong_id") or s.get("voice_id") or ""),
        dac_diem=DacDiemMongMuon(
            gioi=str(dd.get("gioi") or ""),
            vung=str(dd.get("vung") or ""),
            phong_cach=str(dd.get("phong_cach") or "")),
        ngon_ngu_dich=ngon_ngu.chuan_dich(s.get("ngon_ngu_dich")))


def rang(db, *, owner_id: str, yeu_cau: YeuCau) -> KetQua:
    """Chot giong neu chot duoc. Tra `CHUA_RANG` neu con thieu can cu.

    🔑 **Quyen so huu do LTT VOICE kiem, khong phai o day.**
       `features.giai_giong` da loc `owner_id`, da xu ly kho giong dung chung, va
       da bo giong khong con `active`. Viet lai ba phep do o ASV la ba cho de
       lam sai, va cai thu nhat lam sai thi hau qua la mot khach doc video bang
       **giong nhan ban cua nguoi khac**.

    ⛔ Nen o nhanh `USER_SELECTED`, ta goi thang ham cua ho va de no nem.
    """
    if yeu_cau.che_do == CHE_DO_GIONG_TU_CHON:
        return _rang_khach_chon(db, owner_id=owner_id, giong_id=yeu_cau.giong_id,
                                ngon_ngu_dich=yeu_cau.ngon_ngu_dich)
    return _rang_tu_khop(yeu_cau.dac_diem, yeu_cau.ngon_ngu_dich, db=db)


def _rang_khach_chon(db, *, owner_id: str, giong_id: str,
                     ngon_ngu_dich: str = ngon_ngu.DICH_MAC_DINH) -> KetQua:
    from apps.ltt_voice.giong_mau import hop_le as la_giong_mau, tim

    # Giong MAU thi ai cung dung duoc — khong co chu so huu de kiem.
    if la_giong_mau(giong_id):
        lan = str(getattr(tim(giong_id), "ngon_ngu", "") or "")
        if lan and lan != ngon_ngu_dich:
            raise RangGiongError(_t('Giọng này đọc {lan}, không đọc được bản {dich}.').format(
                lan=_t(ngon_ngu.NHAN.get(lan, lan)),
                dich=_t(ngon_ngu.NHAN.get(ngon_ngu_dich, ngon_ngu_dich))))
        return KetQua(DA_RANG, giong_id, NGUON_KHACH_CHON,
                      {"loai": "giong_mau"})

    # Con lai la giong CUA KHACH: de app chu kiem quyen so huu.
    from . import giong_noi

    # ⭐ `ngon_ngu` = lan ban long tieng KHAI: `ltt_voice` la tham quyen duy nhat
    #    chot lan (`lan_ngon_ngu.quyet_dinh`), ta chi dua dung loi khai.
    ref, preset = giong_noi.giai_giong(db, owner_id=owner_id, voice_id=giong_id,
                                       ngon_ngu=ngon_ngu_dich)
    return KetQua(DA_RANG, giong_id, NGUON_KHACH_CHON,
                  {"loai": "giong_cua_khach", "preset": preset,
                   "co_ref": bool(ref)})


def _rang_tu_khop(dac_diem: DacDiemMongMuon,
                  ngon_ngu_dich: str = ngon_ngu.DICH_MAC_DINH,
                  *, db=None) -> KetQua:
    """`AUTO_MATCH`. Thieu dac diem => CHUA_RANG, khong phai giong mac dinh.

    Hai tang, theo thu tu:
      1. giong MAU cua lan dich (`giong_mau.loc`) — y nguyen truoc 22/09;
      2. **chi khi lan dich KHONG co mot giong mau nao** (hom nay: `en`) —
         kho CHUNG cua LTT Voice (`_rang_kho_chung`). Xem docstring ham do.
    """
    if not dac_diem.co_du_de_khop:
        # 🔴 Day la ca diem cua pha nay. Xem docstring dau tep.
        return KetQua(CHUA_RANG, can_cu={"ly_do": "chua co ho so noi dung"})

    from apps.ltt_voice.giong_mau import loc

    # 🔑 Lan lay tu DICH cua lan chay, khong go cung `"vi"` (TRANG_THAI_V6 no).
    ung_vien = loc(gioi=dac_diem.gioi, vung=dac_diem.vung,
                   phong_cach=dac_diem.phong_cach, ngon_ngu=ngon_ngu_dich)
    if not ung_vien and not loc(ngon_ngu=ngon_ngu_dich):
        # ⭐ Lan nay giong mau KHONG phu (khong phai "phu ma khong khop"). Chi
        #    khi do moi xuong kho chung — nen duong `vi` giu nguyen tung ket
        #    qua da nghiem thu (`ngon_ngu.CUM` cung mot luat).
        return _rang_kho_chung(db, dac_diem, ngon_ngu_dich)
    if not ung_vien:
        # ⚠️ Khong ung vien nao thi cung la CHUA_RANG, khong phai "lay dai mot
        #    cai". Noi long dieu kien la viec cua tang tren — no biet mat nao
        #    dang gia nhat, con o day ta khong biet.
        return KetQua(CHUA_RANG, can_cu={
            "ly_do": "khong giong nao khop",
            "ngon_ngu": ngon_ngu_dich,
            "dac_diem": {"gioi": dac_diem.gioi, "vung": dac_diem.vung,
                         "phong_cach": dac_diem.phong_cach}})

    # ⭐ On dinh: sap theo ma roi lay cai dau. Hai lan chay cung dac diem phai
    #    ra cung mot giong, neu khong van tay nhay va cache truot vo co.
    chon = sorted(ung_vien, key=lambda g: g.ma)[0]
    return KetQua(DA_RANG, chon.ma, NGUON_TU_KHOP, {
        "loai": LOAI_GIONG_MAU,
        "so_ung_vien": len(ung_vien),
        "dac_diem": {"gioi": dac_diem.gioi, "vung": dac_diem.vung,
                     "phong_cach": dac_diem.phong_cach}})


#: Nguon ung vien trong `can_cu["loai"]` — hoa don / man ho tro doc no.
LOAI_GIONG_MAU = "giong_mau"
LOAI_KHO_CHUNG = "giong_kho_chung"

#: 🔑 Thu tu UU TIEN trong kho chung, THEO SO DO — khong phai theo cam tinh.
#:
#:    `docs/auto_scan_video_final/L_GIONG_EN.md` do ca 17 giong kho chung lan
#:    `en` tren may sinh tieng THAT (cung mot kich ban thuyet minh, CER/WER bang
#:    faster-whisper large-v3 + jiwer, do to EBU R128). 15/17 CER = 0, nen
#:    phan dinh bang nhip gan ~156 tu/phut (`ngon_ngu.CUM`) + du dinh; mot moi gioi.
#:
#: ⭐ `public_id` cua LTT Voice "khong bao gio doi" (`tables.VoiceProfile`),
#:    nen ghim no la ghim mot danh tinh, khong phai mot vi tri trong bang.
#: ⚠️ Giong nao KHONG con la ung vien (bi tat, bi rut khoi kho chung, license
#:    doi) thi don gian khong co mat — thu tu roi ve `public_id`, van tat dinh.
#: ⛔ Day KHONG phai "giong mac dinh": no chi SAP cac ung vien DA khop lan +
#:    gioi. Khong khop gioi thi khong bao gio duoc chon.
UU_TIEN_KHO_CHUNG: tuple[str, ...] = (
    "vc_1b65a9e636a54ab59c6a69b8046d3d0a",  # Douglas — nam, thuyet minh
    "vc_a55b2ad1646349469d5c5a39d4d20dc0",  # Clara — nu, thuyet minh
)


def _rang_kho_chung(db, dac_diem: DacDiemMongMuon, ngon_ngu_dich: str) -> KetQua:
    """Tang 2 cua `AUTO_MATCH`: kho CHUNG cua LTT Voice, cho lan giong mau
    khong phu (asv-final F-03 — 20/20 preset la `vi`, dich `en` khong co ai).

    🔑 Doc qua `tham_chieu.ung_vien_kho_chung` — be mat KHAI cua LTT Voice. Ham
       do da qua cong license U-05, da bo giong khong `active` va giong chua ro
       gioi. Chi giong DA o kho chung (khach da thay trong bo chon) moi toi day;
       ASV khong mo them giong nao cho ai.

    🔴 **GIOI la mat DUY NHAT kho chung khai** (`VoiceProfile.gioi`). `vung` la
       giong vung mien tieng Viet; `phong_cach` khong phai mot cot cua giong
       nhan ban. Nen:
         · thieu `gioi` => CHUA_RANG. Khop "ca lan" roi lay cai dau la dung
           giong mac dinh doi ten ma D-V4-04 cam;
         · `vung`/`phong_cach` KHONG rang buoc duoc, va ta GHI ra la da bo qua
           (`mat_khong_ap_dung`) thay vi im lang gia vo da khop.

    ⛔ Khong phien CSDL (`db is None`) => CHUA_RANG, khong phai "bo qua tang 2
       roi coi nhu da xet". Duong that luon co `db` (`giai_doan_noi_dung`).
    """
    dd = {"gioi": dac_diem.gioi, "vung": dac_diem.vung,
          "phong_cach": dac_diem.phong_cach}
    if not dac_diem.gioi:
        return KetQua(CHUA_RANG, can_cu={
            "ly_do": "kho chung chi khai gioi — can gioi de khop",
            "ngon_ngu": ngon_ngu_dich, "dac_diem": dd})
    if db is None:
        return KetQua(CHUA_RANG, can_cu={
            "ly_do": "khong co phien CSDL de doc kho chung",
            "ngon_ngu": ngon_ngu_dich, "dac_diem": dd})

    from apps.ltt_voice.tham_chieu import ung_vien_kho_chung

    cac = [u for u in ung_vien_kho_chung(db)
           if u.ngon_ngu == ngon_ngu_dich and u.gioi == dac_diem.gioi]
    if not cac:
        return KetQua(CHUA_RANG, can_cu={
            "ly_do": "khong giong nao khop", "nguon": LOAI_KHO_CHUNG,
            "ngon_ngu": ngon_ngu_dich, "dac_diem": dd})

    hang = {ma: i for i, ma in enumerate(UU_TIEN_KHO_CHUNG)}
    chon = sorted(cac, key=lambda u: (hang.get(u.ma, len(hang)), u.ma))[0]
    return KetQua(DA_RANG, chon.ma, NGUON_TU_KHOP, {
        "loai": LOAI_KHO_CHUNG,
        "so_ung_vien": len(cac),
        "dac_diem": dd,
        "mat_khong_ap_dung": [m for m in ("vung", "phong_cach") if dd[m]]})


#: 🔑 Thu tu NOI LONG cua `AUTO_MATCH` — mat nao duoc bo TRUOC khi bo cuoc.
#:
#:    `_rang_tu_khop` co y **khong** tu noi long: docstring cua no viet *"noi
#:    long dieu kien la viec cua tang tren — no biet mat nao dang gia nhat"*.
#:    Day la tang tren do, va thu tu duoi day la cau tra loi cho cau hoi ay:
#:
#:      1. `phong_cach` — `giong_mau` ghi ro no la **nhan mo ta giong, khong phai
#:         nut van** (*"Style is deprecated on v3 Turbo"*). No la mat model doan
#:         yeu nhat, va bo no khong lam khach nghe thay mot giong sai nguoi.
#:      2. `vung`       — giong vung mien TIENG VIET. Mot phim tieng Trung khong
#:         mang thong tin nao ve no, nen no gan nhu luon la mot rang buoc bia.
#:
#: ⛔ `gioi` KHONG BAO GIO bi bo. No la mat duy nhat **do duoc** (`cao_do.py`,
#:    tren chinh giong dang noi) va la mat duy nhat kho chung khai. Bo not no
#:    thi phep loc tra ve ca catalog, va "lay cai dau tien cua ca catalog" chinh
#:    la giong mac dinh doi ten — dung dieu `ADR-V4-001` D-V4-04 cam.
THU_TU_NOI_LONG: tuple[str, ...] = ("phong_cach", "vung")


def rang_noi_long(db, *, owner_id: str, yeu_cau: YeuCau) -> KetQua:
    """Nhu `rang`, nhung `AUTO_MATCH` duoc bo dan mat it cu nhat khi khong khop.

    ⭐ Vi sao can: ho so cho ra ba mat, nhung catalog **khong co** du moi to hop
       (20 giong mau phu 13 to hop). Mot ho so dung tuyet doi — "nu, mien Trung,
       tin tuc" — van co the tra ve khong ung vien nao, va khi do bo cuoc la
       vut di mot rang buoc CO GIA (`gioi`) chi vi mot rang buoc khong co gia.

    ⛔ Va no van khong phai "lay dai mot cai": vong cuoi cung con dung `gioi`,
       va `gioi` rong thi `co_du_de_khop` sai ⇒ `CHUA_RANG`, khong phai mot
       giong. Xem `THU_TU_NOI_LONG`.
    """
    if yeu_cau.che_do != CHE_DO_GIONG_TU_KHOP:
        return rang(db, owner_id=owner_id, yeu_cau=yeu_cau)

    dac_diem = yeu_cau.dac_diem
    da_bo: list[str] = []
    kq = _rang_tu_khop(dac_diem, yeu_cau.ngon_ngu_dich, db=db)
    for mat in THU_TU_NOI_LONG:
        if kq.da_chot or not getattr(dac_diem, mat):
            break
        dac_diem = replace(dac_diem, **{mat: ""})
        da_bo.append(mat)
        if not dac_diem.co_du_de_khop:
            # Bo them nua thi khong con rang buoc nao — dung lai voi ket qua
            # CHUA_RANG da co, de `can_cu` van noi ro thieu gi.
            break
        kq = _rang_tu_khop(dac_diem, yeu_cau.ngon_ngu_dich, db=db)
    if not da_bo:
        return kq
    return KetQua(kq.trang_thai, kq.giong_id, kq.nguon,
                  {**dict(kq.can_cu or {}), "mat_da_noi_long": da_bo})


def vi_sao_chua_rang(kq: KetQua) -> str:
    """Cau loi CU THE cho mot `CHUA_RANG`. Cho khach doc, khong phai cho log.

    🔴 `KetQua.ma_giong()` nem mot cau chung ("can ho so noi dung truoc khi tu
       khop") vi no khong duoc phep biet ho so den tu dau. Nhung o cho goi thi
       ta BIET, va mot khach doc "khong giong nao khop" se lam mot viec khac han
       khi doc "chua co ho so noi dung".
    """
    ly_do = str((kq.can_cu or {}).get("ly_do") or "")
    if ly_do.startswith("khong giong nao khop"):
        return _t('Không có giọng nào hợp với nội dung này. Hãy tự chọn một giọng.')
    if ly_do.startswith("kho chung chi khai gioi"):
        return _t('Chưa nhận ra giọng người nói trong video nên không tự khớp được. '
                  'Hãy tự chọn một giọng.')
    return _t('Chưa đủ căn cứ từ nội dung để tự khớp giọng. Hãy tự chọn một giọng.')


def kiem_o_cua(db, *, owner_id: str, che_do: str, giong_id: str,
               ngon_ngu_dich: str = ngon_ngu.DICH_MAC_DINH) -> None:
    """Tu choi mot yeu cau giong KHONG THE chot, O CUA — truoc khi giu credit.

    🔴 **Truoc pha 19 cua chi hoi mot cau: "USER_SELECTED co kem ma giong
       khong"**. Quyen so huu chi duoc kiem o `giai_doan_noi_dung` — tuc SAU
       khi khach bi giu credit va sau tach nguon + ASR, hai giai doan dat nhat
       cua chuoi. Mot ma giong cua nguoi khac, mot giong da tat, mot ma go sai:
       ca ba di het doan dat tien roi moi hong.

    ⭐ Kiem bang **chinh** `_rang_khach_chon` — cung duong ma giai doan noi dung
       dung. Khong viet phep kiem so huu thu hai: docstring cua `rang` noi ro
       ly do, va cai sai dau tien cua mot ban sao la mot khach doc video bang
       **giong nhan ban cua nguoi khac**.

    ⚠️ **Cung MOT cau cho "khong co" va "khong phai cua ban"** — LTT Voice da
       co y noi vay (`features.giai_giong`): phan biet hai cau la cho phep do
       xem ma giong nao ton tai. Ta chuyen nguyen cau cua ho, khong viet lai.

    ⛔ `AUTO_MATCH` khong kiem gi o day: giong cua no chot SAU, tu ho so noi
       dung. Doi mot ma giong o cua cho che do nay la dung loi D-V4-04 cam.
    """
    if che_do != CHE_DO_GIONG_TU_CHON:
        return
    if not str(giong_id or "").strip():
        raise RangGiongError(_t('Hãy chọn một giọng đọc.'))

    from .giong_noi import GiongKhongHopLe

    try:
        _rang_khach_chon(db, owner_id=owner_id, giong_id=str(giong_id).strip(),
                         ngon_ngu_dich=ngon_ngu.chuan_dich(ngon_ngu_dich))
    except GiongKhongHopLe as exc:
        # (`giong_noi.giai_giong` boc `ltt_voice.LoiGiongNoi` thanh lop nay.)
        # ⭐ Chi bat dung lop loi CUA KHACH. Mot loi CSDL hay mang di thang len
        #    tren: bien no thanh "giong khong hop le" la bao khach sua mot thu
        #    ho khong he lam sai.
        raise RangGiongError(str(exc)) from exc


def can_cho_ho_so(yeu_cau: YeuCau) -> bool:
    """Lan chay nay co phai dung `HoSoNoiDung` truoc khi chot giong khong?

    🔑 **Cau hoi van y nguyen, nguoi tra loi thi doi.** Truoc 23/09/2026 ham nay
       mo ta mot lan "hoan lai" ma khong ai thuc hien duoc: khong giai doan nao
       sinh ho so, nen mot lan `AUTO_MATCH` chi hoan lai cho toi khi chet o
       `content_process`.

    ⭐ Nay `giai_doan_noi_dung._giong_da_chot` hoi cau nay NGAY TRUOC khi viet
       loi thoai, va tra loi "co" nghia la: goi `ho_so_noi_dung.bao_dam` di,
       roi hoi lai. Cho dung la day chu khong som hon — do dai cau phu thuoc
       toc do doc cua giong, nen giong phai chot TRUOC ban long tieng va khong
       can chot truoc bat cu thu gi khac.

    ⚠️ Van la mot ham doc-thiet-lap thuan tuy: `dac_diem` da co (ho so da ghi o
       mot luot truoc) thi tra `False`, va do la cai khien ca duong nay luy dang.
    """
    return (yeu_cau.che_do == CHE_DO_GIONG_TU_KHOP
            and not yeu_cau.dac_diem.co_du_de_khop)
