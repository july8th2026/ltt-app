"""So cai SU DUNG DA GIAO — bang chung dang sau moi con so credit.

## Vi sao khong dung thang `credit_actual`

`AsvWorkItem.credit_actual` tra loi "het bao nhieu". No khong tra loi duoc ba cau
hoi ma mot lan doi soat tien can:

    nang luc nao da chay        -> khach hoi "toi tra cho cai gi"
    do bang don vi gi           -> 1.200 token va 12 giay la hai the gioi khac nhau
    lan goi do co CHAC da chay  -> ADR-001 D9: dispatch mo ho khong duoc thu lai mu

Va quan he la MOT-NHIEU: tu pha 11 mot don vi viec doc canh bang VLM **roi** sinh
tieng bang TTS. Hai nang luc, hai don vi do, mot item — mot cot khong dien dat
duoc chuyen do.

## 🔑 DA GIAO, khong phai DA YEU CAU

ADR-001 D4: `actual = tong do duoc`, **khong bao gio** tinh lai tu bang gia. Mot
ban ghi da giao bat buoc phai co don vi do va so luong; `SuDung` tu choi mot ban
ghi thieu chung.

⛔ Ly do khong phai su nghiem khac ve hinh thuc. `agent/executor.actual_cost`
   tinh tien theo thu **da yeu cau**, va no da gay hai loi tien that trong du an
   nay. Mot ban ghi mang ten "da giao" ma so lieu lay tu tham so dau vao thi
   mang dung cai ten no khong xung.

## ⛔ SO CAI NAY KHONG PHAI MOT DUONG TIEN THU HAI

🔴 Cho de sai nhat trong ca pha 06. Neu `features.tong_da_dung` cong them bang
   nay, ta co **ba** noi mang tien cho cung mot viec — stage, item, so cai —
   trong khi `features._kiem_khong_tinh_hai_lan` da ton tai chinh vi hai noi da
   la mot noi qua nhieu.

⇒ Tien di qua DUNG MOT cot: `AsvWorkItem.credit_actual`. So cai giai thich con
  so do. `doi_soat` chot bat bien, va `features.quyet_toan` goi no truoc khi chot
  tien — vi mot con so khong giai thich duoc thi khong duoc thu.

## Ba trang thai dispatch, va vi sao hai trong so do khong duoc thu lai

    DA_GIAO    provider tra ket qua      -> tinh tien, dung lai duoc
    TU_CHOI    provider tu choi ro rang  -> khong tinh tien, thu lai duoc
    MO_HO      mat ket noi SAU khi gui   -> **khong biet** da chay chua

`MO_HO` la trang thai dat nhat: co the provider da chay va da tinh tien ta, co
the chua. Thu lai mu la co the tra tien hai lan cho mot viec; bo qua la co the
mat mot ket qua da tra tien. Nen no **khong tu dong** lam gi ca — no cham mot
dau, chan duong thu lai tu dong, va de tang tren quyet dinh (`giai_quyet_mo_ho`).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t

from .tables import (DUNG_DA_GIAO, DUNG_MO_HO, DUNG_TRANG_THAI, DUNG_TU_CHOI,
                     ITEM_INVALIDATED, ITEM_PENDING, ITEM_SUCCEEDED, AsvRun,
                     AsvUsage, AsvWorkItem)

# ⭐ Tai xuat tu `tables`, KHONG khai lai. Ba hang so nay quyet dinh cai gi duoc
#    tinh tien; hai ban sao cua chung la hai cau tra loi cho mot cau hoi tien.
#    Kho nay da co mot loi that dung khuon do — CLAUDE.md ghi lai vu tran token
#    bi nhan doi lam moi cau tra loi dai bi cat o 1.024 token.
DA_GIAO = DUNG_DA_GIAO
TU_CHOI = DUNG_TU_CHOI
MO_HO = DUNG_MO_HO
TRANG_THAI = DUNG_TRANG_THAI

#: Chi trang thai nay moi duoc tinh tien.
TINH_TIEN = frozenset({DA_GIAO})

#: ⛔ Trang thai nay khong duoc tu dong thu lai. Xem docstring dau tep.
KHONG_TU_DONG_THU_LAI = frozenset({MO_HO})

# ── Don vi do ────────────────────────────────────────────────────────────────
#: Don vi phai di KEM so. "1.200" khong noi len dieu gi; "1.200 token" thi co.
TOKEN = "token"
GIAY = "giay"
KY_TU = "ky_tu"
KHUNG_HINH = "khung_hinh"

#: MOT luot goi. Dung khi provider **khong tra so do**.
#:
#: 🔴 Them o pha 11, va ly do dang ghi lai vi no la mot mau thuan that giua luat
#:    cua pha 06 va thuc te cua nen tang.
#:
#:    `platform_core.llm.cong_vlm.SuDung` co co `dang_tin`, va docstring cua no
#:    ghi: *"False khi thuong nguon khong tra `usage`. Ben goi PHAI xu ly rieng.
#:    Dung coi 0 token la mien phi."*
#:
#:    Luat cua pha 06 doi mot ban ghi DA_GIAO phai co don vi do va so luong > 0.
#:    Khi `dang_tin=False` ta khong co so token. Hai cach gian nhat deu la noi
#:    doi mot chieu:
#:
#:      · ghi `DA_GIAO` voi `so_luong=0`   -> bia rang no mien phi
#:      · ghi `TU_CHOI`                    -> bia rang no chua chay
#:
#: ⭐ Nhung co MOT thu van do duoc va van dung: **mot luot goi da duoc giao**.
#:    Do la mot phep do that, kiem duoc, va no khong gia vo biet so token.
#:    Bang gia cho don vi nay thuoc pha 21; o day no ghi dung cai no biet.
LUOT = "luot"

DON_VI = (TOKEN, GIAY, KY_TU, KHUNG_HINH, LUOT)


class SuDungError(ValueError):
    """Ban ghi su dung khong hop le. LUON la loi lap trinh, khong phai loi khach."""


class XungDotDonVi(RuntimeError):
    """Mot tien trinh khac da ghi don vi viec nay giua chung.

    ⛔ Cung ngu nghia voi `features.XungDot` nhung la mot LOP RIENG: mot xung
       dot o cap giai doan va mot xung dot o cap don vi doi hai cach xu ly khac
       nhau (mot cai lam hong ca giai doan, mot cai chi bo qua mot doan), va gop
       chung lai la buoc nguoi bat phai doan xem no dang bat cai nao.

    🔴 **Va no CO Y khong ke thua `SuDungError`.** Docstring cua lop do noi
       thang: *"LUON la loi lap trinh, khong phai loi khach"*, va `loi.py` phan
       loai ca ho do thanh `NGUOI_DUNG` — tuc **that bai cuoi cung, dung thu
       lai**. Mot cuoc dua thua thi khong phai loi lap trinh va **phai** thu
       lai duoc.

    ⚠️ Neu ai do cho no ke thua `SuDungError` cho "gon", `loi.phan_loai` se bat
       no o nhanh SuDungError o TREN va tra `NGUOI_DUNG` — nhanh danh rieng cho
       no o duoi tro thanh ma chet, va mot va cham tam thoi thanh mot lan chay
       hong han. `tests/test_418` chot ca hai chieu nay.
    """


class DaGhiRoi(SuDungError):
    """Ma dispatch nay da co trong so cai cua lan chay.

    ⭐ Day la mot **thanh cong**, khong phai mot su co: no la luc rang buoc
       `UNIQUE(run_id, ma_dispatch)` chan mot lan tinh tien thu hai cho cung mot
       lan gui. Nguoi goi bat no va di tiep.
    """


class DoiSoatLech(SuDungError):
    """Tien cua mot item khong khop voi bang chung cua chinh no."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SuDung:
    """MOT luot goi nang luc, do duoc. Gia tri thuan, chua cham CSDL.

    Bat bien o cap doi tuong: mot ban ghi da giao khong duoc sua sau khi ghi.
    Muon sua nghia la lan goi do khac di, tuc la mot ban ghi KHAC.
    """

    #: Nang luc nao — `text.chat`, `speech.ltt`, `autosubvideo.transcribe`...
    nang_luc: str
    #: Chu so huu nang luc do. Khong phai ten provider ben ngoai: ta khong ban
    #: ten vendor cho khach (`ltt_llm.ALIAS_SANG_ID` giu lop dem do).
    app_chu: str
    trang_thai: str
    don_vi: str = ""
    #: 🔑 So DO DUOC. Rong voi TU_CHOI/MO_HO — va do la mot su that, khong phai
    #:    mot cho trong can dien.
    so_luong: float = 0.0
    #: Credit DO DUOC. Khong bao gio tinh lai tu bang gia (ADR-001 D4).
    credit: int = 0
    #: Danh tinh lan gui. Rong => `ghi` sinh mot ma. Xem `ghi` ve pham vi.
    ma_dispatch: str = ""
    ghi_chu: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trang_thai not in TRANG_THAI:
            raise SuDungError(f"trang thai khong biet: {self.trang_thai!r}")
        if not self.nang_luc or not self.app_chu:
            raise SuDungError("thieu nang_luc hoac app_chu")
        if self.credit < 0 or self.so_luong < 0:
            raise SuDungError("so am")

        if self.trang_thai in TINH_TIEN:
            # ⛔ Mot ban ghi DA GIAO ma khong co don vi do la mot con so khong
            #    kiem duoc. Doi soat sau nay se khong biet no den tu dau.
            if not self.don_vi or self.don_vi not in DON_VI:
                raise SuDungError(
                    f"{self.nang_luc}: da giao thi phai khai don vi do "
                    f"({'/'.join(DON_VI)}), nhan duoc {self.don_vi!r}")
            if self.so_luong <= 0:
                raise SuDungError(f"{self.nang_luc}: da giao ma so luong = 0")
        elif self.credit:
            # 🔴 Cho de sai nhat trong ca tep: mot lan TU_CHOI/MO_HO khong duoc
            #    mang credit. Neu no mang, tong cua lan chay se cong ca nhung
            #    viec **chua chac da chay** — va no cong am tham.
            raise SuDungError(
                f"{self.nang_luc}: trang thai {self.trang_thai} khong duoc mang "
                f"credit (nhan {self.credit})")

    @property
    def duoc_tinh_tien(self) -> bool:
        return self.trang_thai in TINH_TIEN

    @property
    def duoc_tu_dong_thu_lai(self) -> bool:
        return self.trang_thai not in KHONG_TU_DONG_THU_LAI


def tong_credit(cac_su_dung) -> int:
    """Tong credit cua nhung luot **da giao**. Bo qua tu choi/mo ho."""
    return sum(int(s.credit) for s in cac_su_dung if s.duoc_tinh_tien)


# ══════════════════════════════════════════════════════════════════════════════
#  Ghi vao so cai
# ══════════════════════════════════════════════════════════════════════════════

def mo_don_vi(db: Session, run: AsvRun, *, stage: str, item_key: str,
              fingerprint: str = "") -> AsvWorkItem:
    """Lay hoac tao dong don vi viec. Idempotent.

    ⚠️ `UNIQUE(run_id, stage, item_key)` bao ve o cap CSDL, nhung hai worker
       chay dong thoi van co the ca hai thay "chua co" roi ca hai `INSERT`. Ham
       nay doc lai sau khi va cham thay vi de `IntegrityError` noi len goi —
       nguoi goi dang o giua mot lan dispatch va khong co gi de lam voi no.
    """
    from sqlalchemy.exc import IntegrityError

    cu = db.execute(select(AsvWorkItem).where(
        AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
        AsvWorkItem.item_key == item_key)).scalar_one_or_none()
    if cu is not None:
        return cu
    # 🔴 SAVEPOINT, khong phai `db.rollback()`. Ban dau doan nay bat
    #    `IntegrityError` roi goi `db.rollback()` — va no cuon theo **ca giao
    #    dich**, tuc moi dong so cai da ghi truoc do trong cung luot dispatch
    #    bien mat. Mot ham "lay hoac tao" khong duoc pha huy cong viec cua nguoi
    #    goi khi no chon nhanh "lay".
    try:
        with db.begin_nested():
            it = AsvWorkItem(run_id=run.id, owner_id=run.owner_id, stage=stage,
                             item_key=item_key, status=ITEM_PENDING,
                             fingerprint=str(fingerprint or ""))
            db.add(it)
            db.flush()
    except IntegrityError:
        return db.execute(select(AsvWorkItem).where(
            AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
            AsvWorkItem.item_key == item_key)).scalar_one()
    return it


def danh_dau_xong(db: Session, run: AsvRun, *, stage: str, item_key: str,
                  fingerprint: str = "", outputs: dict | None = None) -> AsvWorkItem:
    """Danh dau MOT don vi viec la xong, kem van tay da sinh ra no.

    🔑 Van tay la thu bien mot dong checkpoint tu "da lam roi" thanh "da lam roi
       **cho dung cai nay**". Khong co no, mot lan nang phien ban ma hay doi
       giong se dung lai ket qua cu ma khong ai biet — dung cai `AsvWorkItem` da
       ke ten khi giai thich vi sao V2 (theo doi tien do bang su ton tai cua tep)
       la khong du.

    ⛔ Chi tien LEN: mot don vi da `succeeded` khong bi keo ve `running` boi mot
       lan chay lai. Lan chay lai chi di qua nhung don vi CHUA xong — do la ca y
       nghia cua viec cham diem tung doan thay vi tung giai doan.

    🔴 **`revision` o day tung la mot lo`i hua khong ai giu.** `tables.py:327` noi
       ve chinh cot nay: *"`UPDATE ... WHERE revision = :r` bien mot cuoc dua
       thanh mot xung dot NHIN THAY DUOC thay vi mot ban ghi de."*
       `features.cap_nhat_giai_doan` thuc hien dung dieu do cho `AsvStage` — con
       o day dong cu la mot phep gan ORM tran: doc `it.revision`, cong mot, ghi
       de. Tuc kich ban cot nay sinh ra de xu ly — mot job mo coi bi worker thu
       hai nhat trong khi worker dau con song — ket thuc bang "ai ghi sau thi
       thang", va bo dem tang hai lan ma khong ai duoc bao.

    ⚠️ No chua bao gio gay hai VI hai rang buoc UNIQUE che cho:
       `UNIQUE(run_id, stage, item_key)` va `UNIQUE(run_id, ma_dispatch)` cua so
       cai. Nhung "chua gay hai" khong phai "da duoc thi hanh", va bat bien duoc
       viet ra o `tables.py` thi phai co mot cho thi hanh no.
    """
    it = mo_don_vi(db, run, stage=stage, item_key=item_key,
                   fingerprint=fingerprint)
    rev = int(it.revision or 1)
    ket_qua = db.execute(
        update(AsvWorkItem)
        .where(AsvWorkItem.id == it.id, AsvWorkItem.revision == rev)
        .values(revision=rev + 1, status=ITEM_SUCCEEDED,
                fingerprint=str(fingerprint or it.fingerprint or ""),
                finished_at=_now(),
                **({"outputs": dict(outputs)} if outputs else {})))
    if ket_qua.rowcount != 1:
        # ⭐ Nem, khong ghi de. Nguoi goi dang o giua mot lan dispatch va can
        #    biet rang mot tien trinh khac da cham don vi nay — day dung la thu
        #    cot `revision` duoc them vao de lam cho nhin thay duoc.
        raise XungDotDonVi(
            _t('Đơn vị việc đã được cập nhật ở tiến trình khác.'))
    db.flush()
    db.expire(it)
    return it


def mo_lai_don_vi(db: Session, run: AsvRun, *, stage: str,
                  item_key: str, y_canh: dict | None = None) -> bool:
    """Mo lai MOT don vi da xong de no duoc lam lai. Tra ve co doi gi khong.

    🔴 **Day la ngoai le DUY NHAT cua luat "chi tien len" o `danh_dau_xong`.**

       Luat do noi: *"mot don vi da `succeeded` khong bi keo ve `running` boi mot
       lan chay lai"*, va no dung — no la thu lam cho viec cham diem tung doan co
       nghia. Nhung no duoc viet cho mot lan chay lai **mu**: mot luot advance
       chay lai ca giai doan va khong biet doan nao con dung.

    ⭐ Vong sua thi biet. No cam ten mot doan cu the va mot ly do cu the, nen no
       khong phai "chay lai" — no la "**cai nay** sai, lam lai **cai nay**". Hai
       viec do trong y het nhau o cap giai doan va khac han nhau o cap don vi.

    ⛔ Vi vay ham nay **khong** nhan `stage` roi mo tat: no doi dung mot
       `item_key`. Mot ham mo lai theo giai doan se lam dung cai ma pha 19 cam
       bang chu — *"No full-run automatic rerun"* — chi la o mot cap thap hon va
       kho nhin thay hon.

    🔑 Trang thai la `ITEM_INVALIDATED`, khong phai `ITEM_PENDING`. Hai thu chay
       giong nhau (`da_xong` loc theo `ITEM_SUCCEEDED` nen ca hai deu bi lam
       lai), nhung chung tra loi hai cau khac nhau khi co nguoi doc so sau su co:
       `pending` noi *"chua bao gio chay"*, `invalidated` noi *"da chay, va ta
       da bo ket qua do"*. Cau thu hai la cau giai thich duoc hoa don.
    """
    it = db.execute(select(AsvWorkItem).where(
        AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
        AsvWorkItem.item_key == item_key)).scalar_one_or_none()
    if it is None or it.status == ITEM_INVALIDATED:
        return False

    # 🔴 **`UPDATE ... WHERE revision = :r`, cung khuon voi `danh_dau_xong`.**
    #
    #    Ban dau doan nay la mot phep gan ORM tran: doc `it`, dat `status`, roi
    #    `flush`. No **di vong qua** dung lop bao ve ma ham anh em ngay ben duoi
    #    co — va `tables.py:327` noi ro cot `revision` sinh ra de lam gi: *"bien
    #    mot cuoc dua thanh mot xung dot NHIN THAY DUOC thay vi mot ban ghi de"*.
    #
    # ⛔ Cuoc dua that: mot tien trinh khac vua `danh_dau_xong` don vi nay (doc
    #    lai xong, van tay moi), con ta cam mot ban doc CU roi ghi `invalidated`
    #    de len. Mot lan doc lai da tra tien bien mat, va khong ai thay.
    #
    # ⭐ Tim ra bang cach doi chieu HAI DUONG GHI cua cung mot bang, chu khong
    #    bang mot phep kiem: ca hai deu xanh rieng le, va cho hong la **moi noi**
    #    — thu duy nhat biet ca hai ben.
    rev = int(it.revision or 1)
    # ⭐ **`y_canh` di THEO don vi, chu khong theo giai doan.** Vong sua cam ten
    #    MOT doan va MOT ly do; giai doan chay lai thi doc lai chinh cho nay de
    #    biet *vi sao* doan nay bi lam lai (`giai_doan_noi_dung`).
    # 🔴 Truoc 25/09 ly do ay bi VUT: giai doan chay lai bang loi nhac y het lan
    #    dau, nen vong sua chi la mot lan RUT THAM LAI (`B2_DICH.md` §7.10).
    gia_tri: dict = {"revision": rev + 1, "status": ITEM_INVALIDATED}
    if y_canh:
        # ⛔ GOP vao `outputs`, ⛔ khong ghi de: `outputs` con giu ban cu, va
        #    ban cu la thu `trich_ban_cu` noi toi.
        gia_tri["outputs"] = {**(it.outputs or {}), "y_canh": dict(y_canh)}
    ket_qua = db.execute(
        update(AsvWorkItem)
        .where(AsvWorkItem.id == it.id, AsvWorkItem.revision == rev)
        .values(**gia_tri))
    if ket_qua.rowcount != 1:
        raise XungDotDonVi(
            _t('Đơn vị việc đã được cập nhật ở tiến trình khác.'))
    db.flush()
    db.expire(it)
    return True


def y_canh_dang_cho(db: Session, run: AsvRun, *, stage: str) -> dict[str, dict]:
    """`{item_key: y_canh}` cua cac don vi DA BI MO LAI va chua lam lai xong.

    ⭐ Chi `ITEM_INVALIDATED`: mot don vi `succeeded` ⛔ khong duoc mang `y_canh`
       vao luot sau: no **da** duoc lam lai roi, va dua lai cung mot nghi ngo la
       bat model sua mot thu no vua sua.
    """
    dong = db.execute(select(AsvWorkItem).where(
        AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
        AsvWorkItem.status == ITEM_INVALIDATED)).scalars().all()
    ra: dict[str, dict] = {}
    for it in dong:
        y = (it.outputs or {}).get("y_canh")
        if isinstance(y, dict) and y:
            ra[str(it.item_key)] = dict(y)
    return ra


def da_xong(db: Session, run: AsvRun, *, stage: str,
            fingerprint: str = "") -> set[str]:
    """Cac `item_key` DA xong cua mot giai doan, **dung van tay nay**.

    ⭐ Loc theo van tay chu khong chi theo trang thai: sau khi doi giong hay doi
       ban bien tap, nhung doan da viet la ket qua cua mot cau hoi KHAC — coi
       chung la "da lam roi" thi khach nhan mot ban long tieng nua cu nua moi.
    """
    dk = [AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
          AsvWorkItem.status == ITEM_SUCCEEDED]
    if fingerprint:
        dk.append(AsvWorkItem.fingerprint == str(fingerprint))
    return {r.item_key for r in db.execute(select(AsvWorkItem).where(*dk)).scalars()}


def ghi(db: Session, run: AsvRun, *, stage: str, item_key: str,
        su_dung: SuDung) -> AsvUsage:
    """Ghi MOT luot goi vao so cai, va cong tien cua no vao don vi viec.

    🔑 **Mot giao dich cho ca hai.** Dong so cai va `item.credit_actual` duoc
       viet trong cung mot `flush`. May chet truoc commit thi khong co gi; chet
       sau commit thi ca hai deu co. Khong con khe cua so nao de mot ket qua da
       giao ton tai ma tien chua duoc cong, hoac nguoc lai — do la yeu cau
       "crash between delivered result and checkpoint" cua pha 06.

    ⛔ **Khong bao gio tu choi ghi mot viec DA GIAO vi ly do ngan sach.** Tien
       da tieu roi; khong ghi lai chi lam no bien mat khoi so sach chu khong lam
       no chua tieu. Cua chan ngan sach nam **truoc** luc dispatch
       (`cua_chan_truoc_khi_tieu`), va `features.quyet_toan` van chan tren o muc
       da giu. Mot so cai giau bot chi tieu la mot so cai vo dung.

    ⚠️ Pham vi loi hua chong-tinh-hai-lan: `UNIQUE(run_id, ma_dispatch)` chan
       khi ma dispatch **on dinh cua provider**. Neu goi ham nay khong dua ma,
       moi lan la mot ma moi — va do la dung, vi mot lan gui khong co danh tinh
       thi khong ai chung minh duoc no trung voi lan nao.
    """
    from sqlalchemy.exc import IntegrityError

    if not stage or not item_key:
        raise SuDungError("thieu stage hoac item_key")

    it = mo_don_vi(db, run, stage=stage, item_key=item_key)
    ma = str(su_dung.ma_dispatch or "").strip() or f"tu-sinh:{uuid.uuid4().hex}"

    dong = AsvUsage(
        run_id=run.id, owner_id=run.owner_id, stage=stage, item_key=item_key,
        attempt=int(it.attempt or 0), nang_luc=su_dung.nang_luc,
        app_chu=su_dung.app_chu, trang_thai=su_dung.trang_thai,
        don_vi=su_dung.don_vi, so_luong=float(su_dung.so_luong),
        credit=int(su_dung.credit), ma_dispatch=ma,
        ghi_chu=dict(su_dung.ghi_chu or {}))
    # SAVEPOINT — cung ly do nhu `mo_don_vi`: mot lan ghi bi CSDL tu choi la
    # mot thanh cong cua rang buoc, khong phai co de vut bo giao dich cua nguoi
    # goi. Nguoi goi bat `DaGhiRoi` va di tiep voi nhung gi da ghi con nguyen.
    try:
        with db.begin_nested():
            db.add(dong)
            db.flush()
    except IntegrityError as exc:
        raise DaGhiRoi(
            f"ma dispatch {ma!r} da co trong so cai cua lan chay {run.id}") from exc

    if su_dung.duoc_tinh_tien:
        # ⭐ CONG, khong GAN. Mot item co the goi nhieu nang luc (VLM roi TTS),
        #    va gan se lam luot sau xoa luot truoc — mot loi tien am tham, vi
        #    lan chay van xong va video van dung.
        it.credit_actual = int(it.credit_actual or 0) + int(su_dung.credit)
        db.flush()
    return dong


# ══════════════════════════════════════════════════════════════════════════════
#  Doc so cai
# ══════════════════════════════════════════════════════════════════════════════

def cac_dong(db: Session, run: AsvRun, *, stage: str = "",
             item_key: str = "") -> list[AsvUsage]:
    dk = [AsvUsage.run_id == run.id]
    if stage:
        dk.append(AsvUsage.stage == stage)
    if item_key:
        dk.append(AsvUsage.item_key == item_key)
    return list(db.execute(select(AsvUsage).where(*dk)
                           .order_by(AsvUsage.created_at, AsvUsage.id)).scalars())


def so_ke(db: Session, run: AsvRun) -> dict:
    """Tom tat so cai cho quan sat va giao dien (yeu cau 8 cua pha 06).

    Tra ve so lieu, khong tra ve cau chu: tang tren tu dat ten. Gom theo
    `(app_chu, nang_luc, don_vi)` vi cong 1.200 token voi 12 giay la mot phep
    cong vo nghia, va mot bang tom tat khong duoc lam phep do.
    """
    ra: dict[str, dict] = {}
    tong = {"credit": 0, "da_giao": 0, "tu_choi": 0, "mo_ho": 0}
    for d in cac_dong(db, run):
        khoa = f"{d.app_chu}:{d.nang_luc}"
        m = ra.setdefault(khoa, {"app_chu": d.app_chu, "nang_luc": d.nang_luc,
                                 "don_vi": d.don_vi or "", "so_luong": 0.0,
                                 "credit": 0, "da_giao": 0, "tu_choi": 0,
                                 "mo_ho": 0})
        # ⚠️ Don vi cua mot nang luc phai on dinh. Neu khong, ta dang cong hai
        #    thang do khac nhau — nen ghi nhan bang chuoi rong thay vi im lang
        #    lay cai cuoi cung.
        if d.don_vi and m["don_vi"] and d.don_vi != m["don_vi"]:
            m["don_vi"] = ""
        elif d.don_vi and not m["don_vi"]:
            m["don_vi"] = d.don_vi
        m[d.trang_thai] = m.get(d.trang_thai, 0) + 1
        tong[d.trang_thai] = tong.get(d.trang_thai, 0) + 1
        if d.trang_thai == DA_GIAO:
            m["so_luong"] += float(d.so_luong or 0)
            m["credit"] += int(d.credit or 0)
            tong["credit"] += int(d.credit or 0)
    return {"run_id": run.id, "theo_nang_luc": list(ra.values()), "tong": tong,
            "mo_ho_chua_giai_quyet": len(cac_mo_ho(db, run))}


# ══════════════════════════════════════════════════════════════════════════════
#  Doi soat: bang chung phai giai thich duoc con so
# ══════════════════════════════════════════════════════════════════════════════

def doi_soat(db: Session, run: AsvRun) -> None:
    """⛔ Nem `DoiSoatLech` neu tien cua mot item khong khop bang chung cua no.

    Bat bien:  `item.credit_actual == tong credit cua cac dong DA_GIAO cua item`

    ⚠️ Chi rang buoc nhung item **CO** dong so cai. Item khong co dong nao thi
       khong bi ket toi — do la truong hop cua moi lan chay tao truoc pha 06, va
       cua moi giai doan chua goi nang luc nao.

    🔑 Vi sao goi truoc khi quyet toan chu khong phai o cuoi moi lan ghi: `ghi`
       la duong duy nhat cong tien, nen no khong the tu lam lech. Cai ham nay
       thuc su bat la mot duong ghi **khac** — mot lan `item.credit_actual = ...`
       viet tay o pha sau. Do la thu chi lo ra khi doi chieu hai nguon, va no
       phai lo ra TRUOC khi tien duoc chot.
    """
    co_dong = db.execute(
        select(AsvUsage.item_key, AsvUsage.stage,
               func.coalesce(func.sum(AsvUsage.credit), 0))
        .where(AsvUsage.run_id == run.id, AsvUsage.trang_thai == DA_GIAO)
        .group_by(AsvUsage.stage, AsvUsage.item_key)).all()
    # Item co dong so cai nhung TOAN BO la tu_choi/mo_ho cung phai duoc soi:
    # tien cua no phai la 0. `GROUP BY` o tren bo qua chung, nen lay rieng.
    moi_khoa = {(d.stage, d.item_key) for d in cac_dong(db, run)}
    theo_khoa = {(st, ik): int(c or 0) for ik, st, c in co_dong}

    for stage, item_key in sorted(moi_khoa):
        it = db.execute(select(AsvWorkItem).where(
            AsvWorkItem.run_id == run.id, AsvWorkItem.stage == stage,
            AsvWorkItem.item_key == item_key)).scalar_one_or_none()
        if it is None:
            raise DoiSoatLech(
                f"so cai co dong cho ({stage}, {item_key}) nhung khong co don "
                f"vi viec nao mang khoa do")
        cho_doi = theo_khoa.get((stage, item_key), 0)
        thuc = int(it.credit_actual or 0)
        if thuc != cho_doi:
            raise DoiSoatLech(
                f"({stage}, {item_key}): credit_actual = {thuc} nhung so cai "
                f"chi giai thich duoc {cho_doi}")


# ══════════════════════════════════════════════════════════════════════════════
#  Dispatch mo ho (ADR-001 D9)
# ══════════════════════════════════════════════════════════════════════════════

def cac_mo_ho(db: Session, run: AsvRun, *, stage: str = "") -> list[AsvUsage]:
    """Nhung lan gui **chua biet** da chay hay chua, va chua ai ket luan."""
    dk = [AsvUsage.run_id == run.id, AsvUsage.trang_thai == MO_HO]
    if stage:
        dk.append(AsvUsage.stage == stage)
    return list(db.execute(select(AsvUsage).where(*dk)
                           .order_by(AsvUsage.created_at)).scalars())


def giai_quyet_mo_ho(db: Session, dong: AsvUsage, *, da_chay: bool,
                     don_vi: str = "", so_luong: float = 0.0, credit: int = 0,
                     boi: str = "") -> AsvUsage:
    """Ket luan mot dong mo ho. **Phai co nguoi/tang tren quyet dinh.**

    ⛔ Khong co duong tu dong nao goi ham nay. Do la ca diem cua no: mot lan
       gui mo ho ma he thong tu ket luan la mot lan he thong doan bang tien cua
       khach.

    `da_chay=True`  -> chuyen thanh DA_GIAO, cong tien vao item (nhu `ghi`)
    `da_chay=False` -> chuyen thanh TU_CHOI, khong tinh tien, mo lai duong thu lai
    """
    if dong.trang_thai != MO_HO:
        raise SuDungError(
            f"chi giai quyet duoc dong mo ho, dong nay la {dong.trang_thai!r}")

    if not da_chay:
        dong.trang_thai = TU_CHOI
        dong.credit = 0
        dong.don_vi = ""
        dong.so_luong = 0.0
    else:
        # Di qua `SuDung` de dung MOT bo luat hop le, thay vi mot ban sao mem
        # hon o day. Mot ban ghi da giao thieu don vi do la thu ta cam o tren.
        kiem = SuDung(nang_luc=dong.nang_luc, app_chu=dong.app_chu,
                      trang_thai=DA_GIAO, don_vi=don_vi, so_luong=so_luong,
                      credit=credit)
        dong.trang_thai = DA_GIAO
        dong.don_vi = kiem.don_vi
        dong.so_luong = float(kiem.so_luong)
        dong.credit = int(kiem.credit)
        it = db.execute(select(AsvWorkItem).where(
            AsvWorkItem.run_id == dong.run_id, AsvWorkItem.stage == dong.stage,
            AsvWorkItem.item_key == dong.item_key)).scalar_one()
        it.credit_actual = int(it.credit_actual or 0) + int(kiem.credit)

    dong.ghi_chu = {**(dong.ghi_chu or {}), "giai_quyet": {
        "da_chay": bool(da_chay), "boi": str(boi or ""),
        "luc": _now().isoformat(timespec="seconds")}}
    db.flush()
    return dong


# ══════════════════════════════════════════════════════════════════════════════
#  Cua chan ngan sach — TRUOC khi tieu
# ══════════════════════════════════════════════════════════════════════════════

def cua_chan_truoc_khi_tieu(db, run, *, uoc_them: int) -> None:
    """⛔ Goi TRUOC moi luot co the ton tien. Nem neu se vuot muc da giu.

    🔑 **Tu 25/09/2026 (gia phang) cong nay canh CHI PHI CUA TA, ⛔ khong con canh
       hoa don cua khach.** Khach tra `10 credit x so phut nguon`, va so do ⛔ khong
       phu thuoc vao `tong_da_dung` nua — nen mot lan chay vuot o day ⛔ khong bao
       gio thanh mot con so bat ngo tren hoa don. No chi noi: *lan chay nay dang dot
       nhieu hon gia ban*. Xem `features.kiem_tran_chi`.

    Mong hon `features.kiem_tran_chi` mot lop: no nhan **uoc** cua lan goi sap
    toi, con `kiem_tran_chi` chi biet nhung gi da tieu.

    🔑 Vi sao can mot cua o day thay vi de `quyet_toan` phat hien sau: `quyet_toan`
       chay khi lan chay da ket thuc. Luc do tien da tieu roi, va thu duy nhat
       con lam duoc la bao cho khach mot con so ho khong dong y.

    ⇒ Mot uoc luong te phai thanh mot **that bai chinh sach sach se** truoc khi
      tieu, khong phai mot hoa don bat ngo sau khi tieu.
    """
    from . import features

    features.kiem_tran_chi(db, run, max(0, int(uoc_them)))


def cua_chan_cho_lo(db, run, *, uoc_moi_don_vi: int, so_don_vi: int) -> None:
    """Cua chan cho mot LO — vd sinh tieng 200 doan, doc anh 40 canh.

    ⚠️ Cung nghia moi voi `cua_chan_truoc_khi_tieu`: duoi gia phang no canh **chi
       phi cua ta**, ⛔ khong canh hoa don cua khach.

    ⭐ Kiem CA LO truoc khi chay don vi dau tien, khong phai kiem tung cai mot.

       Kiem tung cai thi lo se chay toi doan thu 137 roi dung — khach da tra cho
       136 doan cua mot san pham **khong dung duoc**, vi mot ban long tieng thieu
       mot phan ba cuoi khong phai mot ban long tieng.

    ⇒ Het ngan sach thi hong TRUOC KHI bat dau, khong phai o giua.
    """
    cua_chan_truoc_khi_tieu(
        db, run, uoc_them=max(0, int(uoc_moi_don_vi)) * max(0, int(so_don_vi)))


def loi_khong_du_ngan_sach() -> str:
    return _t('Chi phí thực tế sẽ vượt mức đã giữ cho phiên chạy này.')


def loi_dispatch_mo_ho(so: int) -> str:
    return _t('Còn {n} lần gọi chưa rõ đã chạy hay chưa — cần xác nhận trước '
              'khi chạy lại để tránh trả tiền hai lần.').format(n=so)
