"""Phan loai loi cua Auto Scan -> phan loai cua NEN TANG (Prompt 17 muc 1).

## Van de ma tep nay lap

`platform_core/job_runner.py:573 _provider_failure_kind` da co mot phan loai
day du va tot: `loi_nguoi_goi` · `resource_wait` · `rejected` · `ambiguous` ·
`retry`. Nhung no nhan dien bang **isinstance tren cac lop ngoai le cua provider
LLM**, va moi thu khac roi xuong nhanh mac dinh `"retry"`.

Auto Scan nem chin loai ngoai le co kieu cua rieng no. Khong loai nao trong so
do duoc nhan dien, nen **tat ca** deu roi vao `"retry"`. Ba hau qua that:

  🔴 `MediaError` / `ThieuNguon` — "tep nguon khong co luong tieng", "video dai
     hon tran". Day la du lieu khach gui len. Thu lai **ba lan** mot viec khong
     bao gio thanh cong: ba suat xep hang, ba lan cho, cung mot ket qua.

  🔴 `GiongMoHo` / `DichMoHo` — da co the goi toi may sinh tieng hay model roi
     mat ket noi. `_provider_failure_kind` chi coi la `ambiguous` khi
     `provider_state == dispatched`, ma `giong_noi` goi mot DICH VU cuc bo chu
     khong qua `dieu_phoi`, nen no khong bao gio dat co do. ⇒ Thu lai mot lan
     goi **co the da tinh tien**. Dung dieu ma I5/G7 sinh ra de chan.

  🔴 `MayBan` — may sinh tieng dang ban. **Ban khong phai hong.** Roi vao
     `"retry"` nghia la dot mot lan thu cho mot dieu kien se tu het, va sau ba
     lan thi job hong han — trong khi dung ra no chi can xep lai hang doi.
     `apps/ltt_voice/features.py:219` da ghi bai hoc nay bang chu.

⇒ Tep nay khong dung mot phan loai thu hai. No **dich** loai cua ta sang loai
  cua nen tang, ngay tai bien, de mot loi da co kieu dung khong bi tut xuong
  nhanh mac dinh chi vi nen tang chua tung nghe ten no.

## Vi sao dich o BIEN chu khong nem thang loai cua nen tang

Engine (`nhap_media`, `giong_noi`, …) nem loai cua **mien cua chung**. Bat chung
nem `jobq.LoiNguoiGoi` la buoc moi module engine phai biet ve hang doi job — tuc
doi dung ranh gioi ma hop dong app dung len de giu. `thi_hanh` la cho duy nhat
da biet ca hai phia, nen phep dich thuoc ve no.
"""
from __future__ import annotations

#: ⛔ KHONG thu lai. Nguyen nhan la du lieu nguoi dung gui len.
NGUOI_DUNG = "nguoi_dung"
#: ⛔ KHONG thu lai. Mot artifact thuong nguon dang can lai vang mat.
#:
#: ⭐ Tach rieng khoi `NGUOI_DUNG` du **hanh vi giong het** (ca hai deu khong
#:    thu lai), vi goi day la "loi cua nguoi dung" la noi sai: khach khong lam
#:    gi ca. Do la mot trang thai khong nhat quan cua chinh he thong — vd
#:    COMPOSE chay khi TIMING chua co ket qua.
#:
#: ⚠️ No van duoc dich thanh `LoiNguoiGoi` o bien, vi nen tang **khong co** loai
#:    "trang thai khong nhat quan" va `LoiNguoiGoi` la loai duy nhat cho dung
#:    hanh vi (khong thu lai). Ghi ro o day de mot nguoi doc log khong ket luan
#:    nham rang khach da gui gi do sai.
THIEU_THUONG_NGUON = "thieu_thuong_nguon"
#: Xep lai hang doi sau mot khoang. **Khong phai loi**, khong dot mot lan thu.
BAN = "ban"
#: Da co the goi ra ngoai roi mat ket noi. ⛔ KHONG BAO GIO tu dong thu lai.
MO_HO = "mo_ho"
#: Truot thoang qua. Thu lai la dung.
TAM_THOI = "tam_thoi"

#: Giay cho mac dinh khi may sinh tieng bao ban ma khong noi cho bao lau.
#: ⚠️ So nay CHUA DO. Chon de an toan: du dai de mot lan sinh tieng ngan kip
#: xong, du ngan de khach khong thay lan chay dung hinh. Pha 21 co the do lai.
CHO_KHI_BAN_S = 20


def phan_loai(exc: BaseException) -> str:
    """Mot ngoai le cua Auto Scan -> mot trong bon loai o tren.

    ⚠️ Thu tu quan trong. `MayBan` phai duoc hoi TRUOC cac loai chung hon, va
       `ThieuNguon` truoc `MediaError` (no la lop con). Doi thu tu la lam mot
       nhanh khong bao gio chay toi, va nhanh chet do trong y het mot nhanh dang
       lam viec.
    """
    from .ban_dung import BanDungError
    from .ban_ghi import BanGhiError
    from .dich_thuat import DichError, DichMoHo
    from .giong_noi import GiongError, GiongMoHo, MayBan
    from .giai_doan_media import ThieuNguon
    from .ket_xuat import KetXuatError
    from .nhap_media import MediaError
    from .thoi_gian import ThoiGianError
    from .van_ban import VanBanError

    # ── Ban: hoi TRUOC moi thu, va no khong phai loi ────────────────────────
    if isinstance(exc, MayBan):
        return BAN

    # ── Mo ho: da co the goi ra ngoai. Khong bao gio tu dong thu lai ────────
    if isinstance(exc, (GiongMoHo, DichMoHo)):
        return MO_HO

    # ── Loi cua nguoi dung: dau vao khong hop le, hoac ket qua khong dung
    #    hop dong. Thu lai khong doi duoc gi.
    #
    # ⚠️ `KetXuatError` KE THUA `MediaError` nhung KHONG thuoc nhom nay — mot
    #    lan render hong thuong la truot thoang qua (het cho dia, mot tien
    #    trinh con bi giet), khong phai dau vao sai. Nen phai hoi no truoc.
    if isinstance(exc, KetXuatError):
        return TAM_THOI

    # ── Thieu thuong nguon: hoi TRUOC `MediaError` vi `ThieuNguon` la lop con
    #    cua no, va ca bay lop `Thieu*` deu ke thua `ThieuNguon`.
    if isinstance(exc, ThieuNguon):
        return THIEU_THUONG_NGUON

    # ⛔ QC hong la loi cua KET QUA, khong phai truot thoang qua: chay lai cung
    #    mot ban render cho cung mot phep do. Thu lai ba lan mot phep do tat dinh
    #    la ba lan cho vo ich.
    from .thi_hanh import QcChan
    if isinstance(exc, QcChan):
        return NGUOI_DUNG

    # ⛔ `TinhHaiLan` la mot lech SO SACH, khong phai mot truot thoang qua.
    #
    # 🔴 Neu no roi xuong nhanh mac dinh `TAM_THOI`, nen tang se **THU LAI** —
    #    va thu bi thu lai la mot lan chay ma so tien cua no da duoc phat hien
    #    la sai. Chay lai khong sua duoc mot giai doan vua co don vi viec vua tu
    #    ghi `credit_actual`; no chi lam viec do them mot lan nua.
    #
    # ⭐ `NGUOI_DUNG` o day khong co nghia "khach lam sai" — trong bang nay no
    #    la nhan cua *that bai cuoi cung, dung thu lai*, va do la dieu can noi.
    #    `test_418` vua bat duoc dung cho nay: mot lop ngoai le moi khong duoc
    #    phan loai se im lang thua ke hanh vi nguy hiem nhat trong bang.
    from .features import TinhHaiLan
    if isinstance(exc, TinhHaiLan):
        return NGUOI_DUNG

    # ⛔ Ba lop cua so cai su dung (pha 06) — CUNG mot ly do, va `SuDungError` la
    #    lop cha nen mot dong bat het ca ba.
    #
    # 🔑 `SuDungError` la **loi lap trinh**, khong phai loi khach: mot ban ghi
    #    "da giao" thieu don vi do, mot trang thai mo ho mang credit, mot con so
    #    am. Chay lai cung mot ma se dung y het.
    #
    # 🔴 `DoiSoatLech` con nguy hiem hon khi bi thu lai: no la luc **tien cua
    #    mot don vi viec khong khop voi bang chung cua chinh no**. Thu lai mot
    #    lan quyet toan da phat hien lech la thu chot lai dung con so sai do.
    #
    # ⭐ `DaGhiRoi` thi nguoc lai — no la mot **thanh cong**: rang buoc
    #    `UNIQUE(run_id, ma_dispatch)` vua chan mot lan tinh tien thu hai. Nguoi
    #    goi phai bat no va di tiep; neu no len toi day thi ai do da khong bat,
    #    va thu lai chi lam CSDL tu choi them mot lan nua.
    from .su_dung import SuDungError
    if isinstance(exc, SuDungError):
        return NGUOI_DUNG

    # ── Rang giong (pha 09) ─────────────────────────────────────────────────
    #
    # 🔑 Ca hai deu la that bai CUOI CUNG, dung thu lai:
    #
    #    `RangGiongError` — yeu cau khong hop le (che do bia ra, USER_SELECTED
    #      de trong ma giong). Chay lai cung mot thiet lap se hong y het.
    #
    #    `ChuaRangError` — doc giong tu mot rang buoc chua chot. Do la mot loi
    #      LAP TRINH o tang goi, khong phai mot truot thoang qua: thu lai khong
    #      lam `HoSoNoiDung` xuat hien.
    from .rang_giong import RangGiongError
    if isinstance(exc, RangGiongError):
        return NGUOI_DUNG

    # ── Vung che (V5) ───────────────────────────────────────────────────────
    #
    # 🔑 `VungLoi` la toa do khong hop le: sai dinh dang, ngoai khoang 0..1, ve
    #    nguoc, hay qua nho. Chay lai cung mot bo toa do se hong y het.
    #
    # ⚠️ Hom nay no chi duoc nem trong `routes.tao` va bat ngay tai do, nen no
    #    **chua bao gio** toi duoc ham nay. Van phan loai, va do la co y: neu mot
    #    pha sau goi `vung_che.chuan_hoa` tu ben trong mot job, no phai roi vao
    #    nhanh dung chu khong roi xuong `retry` — dung dieu `test_418` goi la
    #    "im lang thua ke hanh vi nguy hiem nhat trong bang".
    from .vung_che import VungLoi
    if isinstance(exc, VungLoi):
        return NGUOI_DUNG

    # ── Tu dien ten rieng (V5) ────────────────────────────
    #
    # Cung ly do voi `VungLoi` ngay tren: hom nay no chi duoc nem trong
    # `routes.tao` va bat ngay tai do, nen chua bao gio toi duoc ham nay.
    # Van phan loai — chay lai cung mot tu dien sai se hong y het, nen no
    # khong duoc roi xuong nhanh `retry`.
    from .tu_dien import TuDienLoi
    if isinstance(exc, TuDienLoi):
        return NGUOI_DUNG

    # ── Cat dau/cuoi (V6 pha 10) ────────────────────────────────────────────
    #
    # ⚠️ **Khac hai muc tren o mot cho, va cho do la ly do muc nay quan trong
    #    hon ca hai.** `VungLoi` va `TuDienLoi` chi duoc nem o `routes.tao` roi
    #    bat ngay tai do — chung phan loai o day cho tuong lai.
    #
    #    `CatLoi` thi **that su di toi day hom nay**: `giai_doan_ban_dung` goi
    #    `cat_dau_cuoi.giao`, va `giao` nem khi cua so khong cham khoang giu nao.
    #    Do la mot job, khong phai mot request.
    #
    # ⛔ Nen thieu dong nay khong phai mot thieu sot ly thuyet: mot cua so cat
    #    khong con lai gi se roi xuong nhanh `retry`, va lan chay lai se hong y
    #    het — vi cung mot cua so, cung mot ban do. Khach cho ba lan de nhan
    #    cung mot ket qua, va tra tien cho ca ba.
    from .cat_dau_cuoi import CatLoi
    if isinstance(exc, CatLoi):
        return NGUOI_DUNG

    # ── Lop phu chu (V6 pha 11) ─────────────────────────────────────────────
    #
    # ⚠️ Nam cung nhom voi `CatLoi` chu khong voi `VungLoi`: no **that su di toi
    #    day**, va qua HAI duong khac nhau.
    #
    #      `routes.tao`            -> bat ngay tai cho, chua toi ham nay
    #      `lop_phu.duong_font()`  -> goi tu `che_do_render._loc_chu`, tuc tu
    #                                 trong mot JOB, luc dung chuoi loc
    #      `lop_phu.vien_px()`     -> nhu tren
    #
    # ⛔ Va hai duong sau moi la ly do dong nay ton tai. Mot may chu khong co
    #    phong chu nao se nem `LopPhuLoi` giua giai doan ket xuat; roi xuong
    #    nhanh `retry` thi lan chay lai hong y het — vi may van khong co phong
    #    chu — va khach cho ba lan de nhan cung mot ket qua.
    #
    # ⭐ `NGUOI_DUNG` o day khong noi "loi cua khach". No noi **that bai cuoi
    #    cung, dung thu lai** — dung nghia ma bang nay dung cho ca `CatLoi`.
    from .lop_phu import LopPhuLoi
    if isinstance(exc, LopPhuLoi):
        return NGUOI_DUNG

    # ── Logo (V6 pha 11b) ───────────────────────────────────────────────────
    #
    # Cung nhom voi `LopPhuLoi`, va cung ly do: `logo.rong_px()` duoc goi tu
    # `che_do_render._loc_logo`, tuc tu trong mot JOB, dung luc dung chuoi loc.
    #
    # ⛔ Mot ban dung co logo ma thieu `rong_khung` se nem giua giai doan ket
    #    xuat. Roi xuong `retry` thi ba luot deu hong y het — cung mot ban dung,
    #    cung mot truong thieu.
    # ── Phu de (V6 pha 14) ──────────────────────────────────────────────────
    #
    # Cung nhom voi `LopPhuLoi`/`LogoLoi`, va cung mot ly do CO HOC: `phu_de`
    # duoc goi ca o bien HTTP lan **trong mot job** (khi `ket_xuat` dung chuoi
    # loc `ass=`). Duong thu hai moi la ly do dong nay ton tai.
    #
    # ⛔ Mot kieu phu de khong con ton tai — `autosubvideo` doi ten mot preset —
    #    se nem `PhuDeLoi` giua giai doan ket xuat. Roi xuong nhanh `retry` thi
    #    ba luot deu hong y het: cung mot ho so, cung mot id da bien mat.
    #
    # ⭐ `NGUOI_DUNG` o day khong noi "loi cua khach". No noi **that bai cuoi
    #    cung, dung thu lai** — dung nghia ma bang nay dung cho `CatLoi`.
    from .phu_de import PhuDeLoi
    if isinstance(exc, PhuDeLoi):
        return NGUOI_DUNG

    from .logo import LogoLoi
    if isinstance(exc, LogoLoi):
        return NGUOI_DUNG

    # ── Am thanh (V6 pha 23) ────────────────────────────────────────────────
    #
    # Cung nhom, cung ly do co hoc: `am_thanh.tu_cai_dat` chay ca o bien HTTP
    # lan **trong job** `timing_align` (duyet lai ho so da luu truoc khi tron).
    # Mot ho so da luu ma khong con hop le thi ba luot `retry` hong y het.
    from .am_thanh import AmThanhLoi
    if isinstance(exc, AmThanhLoi):
        return NGUOI_DUNG

    # ── QC bang AI va ke hoach sua (pha 19) ─────────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — that bai cuoi cung. Ca hai deu la mau thuan trong du lieu
    #    hoac trong phan hoi cua model: mot loai khiem khuyet khong co that, mot
    #    bang phan doan sai hinh dang. Thu lai cho ra dung mau thuan do.
    #
    # ⚠️ Khac `AiMoHo`: mo ho la "co the da goi, khong biet ket qua". Day la "da
    #    co ket qua, va ket qua khong dung hop dong".
    from .qc_ai import QcAiError
    from .sua_chua import SuaChuaError
    if isinstance(exc, (SuaChuaError, QcAiError)):
        return NGUOI_DUNG

    # ── Va cham o cap DON VI VIEC (pha 27) ──────────────────────────────────
    #
    # ⛔ `TAM_THOI` — thu lai duoc, va **phai** thu lai duoc. `XungDotDonVi` co
    #    nghia la mot tien trinh khac vua ghi dong nay giua chung: khong co gi
    #    sai trong du lieu, chi la ta thua cuoc dua. Lan sau doc lai se thay
    #    trang thai moi va thuong la khong con gi de lam.
    #
    # ⚠️ Khac `XungDot` cua `features` (cap GIAI DOAN) o cho lop kia khong bao
    #    gio len toi bien — no bi bat o tang route. Lop nay nem tu than mot giai
    #    doan, nen no PHAI co mot phan loai.
    from .su_dung import XungDotDonVi
    if isinstance(exc, XungDotDonVi):
        return TAM_THOI

    # ── Cach render (pha 17) ────────────────────────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — that bai cuoi cung. Mot ban dung khai preset mot dang va
    #    xin cach render mot dang khac la mau thuan trong chinh du lieu; lan thu
    #    hai cho ra dung mau thuan do.
    from .che_do_render import CheDoError
    if isinstance(exc, CheDoError):
        return NGUOI_DUNG

    # ── Ban do thoi gian va ban phoi am (pha 16) ────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — tuc **that bai cuoi cung, dung thu lai**. Ca hai lop deu
    #    la ket luan cua mot phep tinh TAT DINH tren du lieu da co: mot ban do
    #    khong hop le hay mot ban phoi lech thoi luong se cho ra dung ket qua do
    #    o lan thu hai. Thu lai chi ton them mot suat ffmpeg.
    #
    # ⭐ Khac han `MayBan`/`ThieuCard`: nhung cai do la truot cua moi truong.
    #    Day la mau thuan trong chinh du lieu, va no khong tu lanh.
    from .am_master import MasterError
    from .ban_do_thoi_gian import BanDoError
    if isinstance(exc, (BanDoError, MasterError)):
        return NGUOI_DUNG

    # ── Nan cho vua (pha 15) ────────────────────────────────────────────────
    #
    # ⭐ `TAM_THOI` — va o day thu lai la viec dung chu khong phai mot cho hong
    #    ve phia an toan: `NanError` chi xay ra khi model tra ve mot cau viet lai
    #    khong doc duoc. Model la ngau nhien, nen lan sau thuong duoc.
    #
    # ⚠️ Nhung trong duong chay that no gan nhu khong bao gio len toi day:
    #    `giai_doan_giong._viet_lai` bat no ngay tai cho va **dung bac thang**,
    #    vi mot lan xin viet lai hong khong duoc phep lam hong ca giai doan —
    #    cau hien tai van doc duoc, chi la khong vua, va con mot nac (co gian)
    #    nua truoc khi phai bo cuoc.
    from .nan_cho_vua import NanError
    if isinstance(exc, NanError):
        return TAM_THOI

    # ── Ban long tieng (pha 14) ───────────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — tuc **that bai cuoi cung, dung thu lai**. Mot ban long
    #    tieng khong phu dung phan giu lai, hay mot bang tu vung sai, la mot loi
    #    HOP DONG giua ta va model: thu lai chi tra tien lan hai cho cung mot cau
    #    tra loi sai.
    #
    # ⚠️ `ThieuDoan` (model bo sot doan) la truong hop RANH GIOI, va no duoc xep
    #    vao day co y: mot lo thieu doan thuong la loi nhac qua dai hoac model tra
    #    ve cat ngan — ca hai deu KHONG tu khoi phuc o lan thu hai, va lan thu hai
    #    do tra tien day du. Nguoi van hanh chia nho lo roi chay lai thi hon.
    from .long_tieng import LongTiengError
    if isinstance(exc, LongTiengError):
        return NGUOI_DUNG

    # ── Cap card GPU (pha 13) ───────────────────────────────────────────────
    #
    # ⭐ `TAM_THOI` — tuc **THU LAI**, va o day thu lai la viec dung chu khong
    #    phai mot cho hong ve phia an toan: nen tang giu cho card qua
    #    `gpu_lease`, nen lan sau no co the cap mot card KHAC. Mot card vua bi
    #    reset driver, mot lease dap vao card dang bao tri — deu la nhung thu
    #    lan thu hai giai quyet duoc.
    #
    # 🔴 Va day la ly do lop nay ton tai tach khoi `MediaError`. Truoc pha 13,
    #    tien trinh con thieu card thi **im lang chay CPU**; sua thanh nem ra
    #    nhung san vao `MediaError` thi nen tang lai khong phan biet duoc "cap
    #    card hong" (thu card khac) voi "tieng hong" (thu bao nhieu lan cung
    #    the). Mot loi keu to ma khong noi duoc gi thi chua phai da sua xong.
    from .demucs_runner import ThieuCard
    if isinstance(exc, ThieuCard):
        return TAM_THOI

    # ── Tach canh (pha 10) ──────────────────────────────────────────────────
    #
    # ⭐ `TAM_THOI`, khac han hai lop tren: `CanhError` gan nhu luon la mot lan
    #    ffmpeg khong chay duoc (het cho dia, tien trinh con bi giet, tep dang
    #    duoc ghi do) — dung loai truot thoang qua ma mot lan thu lai chua duoc.
    #
    # ⚠️ No CUNG duoc dung cho "chi muc sai hinh dang", va truong hop do thu lai
    #    vo ich. Nhung hai truong hop khong tach duoc bang mot lop, va chon
    #    `TAM_THOI` la chon hong ve phia TON THEM MOT LAN THU chu khong phai ve
    #    phia lam khach mat viec — dung huong ma `test_ngoai_le_la_hoac_mac_dinh`
    #    da chot cho mac dinh cua ca bang.
    from .canh import CanhError
    if isinstance(exc, CanhError):
        return TAM_THOI

    # ── Hieu canh (pha 11) ──────────────────────────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — tuc **that bai cuoi cung, dung thu lai**.
    #
    # 🔴 Va day la cho de xep nham nhat trong ca bang. `HieuCanhError` nghia la
    #    model DA CHAY, DA tinh tien, va tra ve mot phan hoi sai luoc do. Thu lai
    #    la goi model LAN NUA cho cung mot canh — tuc **tra tien lan hai cho mot
    #    canh da tra tien**, va lan nay cung khong co gi bao dam ket qua khac.
    #
    # ⚠️ Khac han `ai.LuocDoSai` (pha 08), von la `TAM_THOI`: o do phep doc JSON
    #    that bai o tang VAN CHUYEN, truoc khi ta biet noi dung co nghia gi. O
    #    day ta da doc duoc JSON va no **mang mot gia tri sai** — vd `de_xuat`
    #    la mot tu bia ra. Hai tinh huong khac nhau, hai so phan khac nhau.
    from .hieu_canh import HieuCanhError
    if isinstance(exc, HieuCanhError):
        return NGUOI_DUNG

    # ── Ban bien tap (pha 12) ───────────────────────────────────────────────
    #
    # ⛔ `NGUOI_DUNG` — that bai cuoi cung, dung thu lai.
    #
    # 🔑 `BanBienTapError` nem khi ban KHONG DAT chinh sach an toan: cat sach moi
    #    canh, giu duoi san, hoac mot thao tac cat lot vao che do giu nguyen
    #    hinh. Ba dieu do la ket luan cua mot phep tinh TAT DINH tren cung du
    #    lieu — chay lai cho ra dung ket qua cu.
    #
    # ⚠️ `ThieuChiMuc` khong can mot nhanh rieng o day: no ke thua `ThieuNguon`
    #    nen nhanh `THIEU_THUONG_NGUON` o tren da bat. Nhung no VAN phai co
    #    trong bang cua `test_418` — bang do chot TAP HOP, khong chot hanh vi.
    from .ban_bien_tap import BanBienTapError
    if isinstance(exc, BanBienTapError):
        return NGUOI_DUNG

    # ── Cua goi model (pha 08) ──────────────────────────────────────────────
    #
    # ⛔ `AiMoHo` va `AiError` KHONG ke thua nhau, va do la co y: mot phep
    #    `isinstance` nham khong the bien mot lan mo ho thanh mot lan thu lai.
    from .ai import AiError, AiMoHo
    if isinstance(exc, AiMoHo):
        return MO_HO
    if isinstance(exc, AiError):
        # ⭐ `LuocDoSai` (model tra JSON sai hinh dang) la con cua `AiError` va
        #    co CHU Y roi vao day: model la ngau nhien, nen mot lan sinh hong
        #    thuong het o lan sau. Do la khac biet that voi `QcChan` — mot phep
        #    do tat dinh chay lai cho ra dung ket qua cu.
        return TAM_THOI

    if isinstance(exc, (MediaError, BanGhiError, VanBanError, ThoiGianError,
                        BanDungError)):
        return NGUOI_DUNG

    # ── Con lai: truot thoang qua ───────────────────────────────────────────
    # ⛔ `ltt_voice` tu choi giong (khong phai cua ban, da tat, lech lan voi
    #    kich ban — W4'). Chay lai cung giong + cung kich ban hong y het.
    from .giong_noi import GiongKhongHopLe
    if isinstance(exc, GiongKhongHopLe):
        return NGUOI_DUNG

    if isinstance(exc, (GiongError, DichError)):
        return TAM_THOI
    return TAM_THOI


def dich_sang_loi_nen_tang(exc: BaseException) -> BaseException:
    """Tra ve ngoai le NEN TANG hieu, hoac chinh `exc` neu de nguyen la dung.

    Giu nguyen thong diep goc: no da qua `_t()` va la thu khach doc duoc.
    ⛔ Va giu nguyen **chuoi nguyen nhan** (`from exc`) de nguoi doc log van
       thay loai goc — dich khong duoc lam mat dau vet.
    """
    from platform_core import jobs as jobq
    from platform_core.llm.cong_vlm import AmbiguousProviderError, BanError

    loai = phan_loai(exc)
    if loai in (NGUOI_DUNG, THIEU_THUONG_NGUON):
        moi: BaseException = jobq.LoiNguoiGoi(str(exc))
    elif loai == BAN:
        moi = BanError(str(exc), retry_after_s=CHO_KHI_BAN_S)
    elif loai == MO_HO:
        moi = AmbiguousProviderError(str(exc))
    else:
        return exc
    moi.__cause__ = exc
    return moi
