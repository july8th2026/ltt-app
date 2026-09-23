"""Bang CSDL rieng cua Auto Scan Video. Tien to `asv_` theo `MANIFEST.table_prefix`.

Hai bang, va ranh gioi giua chung la thu giu bat bien I18.

* `asv_run`   — mot lan chay. **Mot nguoi ghi duy nhat**: job dieu phoi
                `asv.advance`, luon lay `SELECT ... FOR UPDATE` truoc.
* `asv_stage` — MOT DONG cho MOI `(run_id, stage)`. Moi stage tu ghi dong cua
                minh, khong ai ghi dong cua ai.

## Vi sao KHONG dung mot khoi JSON `checkpoint`

Tien le trong kho la `AgentRun.checkpoint` (`platform_core/models.py:468`) — mot
tai lieu JSON bi doc-sua-ghi o moi tick cua `agent/executor.py`. No **dang chay
dung**, nhung chi vi moi nguoi ghi deu di qua `runs.get_owned(..., lock=True)`
(`executor.py:227`). Tuc tinh dung dan nam o mot ky luat ma khong gi cuong che:
them mot duong ghi quen khoa la mat cap nhat, im lang.

Mot dong cho moi stage **xoa bo** nguy co thay vi canh no: hai stage xong cung
mot luc ghi hai dong khac nhau va khong the dam nhau. Do la khac biet giua
"an toan neu ai cung nho" va "an toan vi khong con cho de sai".

Xem `docs/auto_scan_video/adr/ADR-001-execution-billing-resource.md` D2.

## Vi sao van co `revision` du da tach dong

Mot stage co the bi ghi tu hai cho trong dung mot tinh huong: worker cu chua
chet han (mat dap nhip) va worker moi da nhat lai job mo coi. `UPDATE ... WHERE
revision = :r` bien cuoc dua do thanh mot xung dot **nhin thay duoc**, thay vi
mot ban ghi de. Khuon lay tu `platform_core/app_projects.py:85`.

⛔ `owner_id` la `String(36)`, KHONG phai so. `User.id` cua nen tang la UUID
   chuoi. Khai `BigInteger` o `voice_profile` da tung lam MOI khach chung mot
   chu so huu — xem `alembic/versions/20260831_1000_voice_owner_uuid.py`. Day la
   cai bay da co that trong chinh kho nay, khong phai mot lo ngai ly thuyet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

# ── Trang thai cua mot lan chay ──────────────────────────────────────────────
RUN_QUEUED = "queued"
RUN_RUNNING = "running"
RUN_DONE = "done"
RUN_ERROR = "error"
RUN_CANCELLED = "cancelled"
RUN_TERMINAL = frozenset({RUN_DONE, RUN_ERROR, RUN_CANCELLED})

# ── Trang thai cua mot giai doan ─────────────────────────────────────────────
#
# Day la mot PHEP CHIEU cua trang thai job nen tang, khong phai mot may trang
# thai cong khai thu hai (EXECUTION_GUARDRAILS muc 5). Anh xa o `ADR-001` D3.
STAGE_PENDING = "pending"            # chua co job con (phu thuoc chua du)
STAGE_QUEUED = "queued"              # job con dang xep hang
STAGE_RUNNING = "running"            # job con dang chay
STAGE_SUCCEEDED = "succeeded"        # job xong VA output da ben + hop le
STAGE_FAILED_RETRYABLE = "failed_retryable"
STAGE_FAILED_TERMINAL = "failed_terminal"
STAGE_CANCELLED = "cancelled"
STAGE_INVALIDATED = "invalidated"    # van tay lech hoac output da bien mat
STAGE_TERMINAL = frozenset({STAGE_SUCCEEDED, STAGE_FAILED_TERMINAL,
                            STAGE_CANCELLED})


def _now() -> datetime:
    return datetime.now(timezone.utc)


#: 🔴 **31, khong phai 32 — va mot ky tu la ca ly do.**
#:
#:    `"asvr_" + 32 hex` = **37** ky tu, va `credit_entries.job_id` cung
#:    `jobs.plan_id` cua nen tang deu la `VARCHAR(36)`. PostgreSQL cuong che do
#:    dai cot; SQLite coi no la mot goi y. Moi bai test cua app nay chay tren
#:    SQLite, production chay PostgreSQL, va app nay chua tung chay o production
#:    — nen luot chay TRA TIEN dau tien se chet o `credit.giu_cho`, TRUOC khi he
#:    thong lam bat cu viec gi (A29-06).
#:
#: ⭐ Sua o DAY chu khong noi cot nen tang: cot do la vung chung cua moi app va
#:    noi no doi mot migration tren BANG TIEN cua production. Doi mot dong o day
#:    thi khong cham gi ca — va no mien phi **hom nay** vi chua co hang nao mang
#:    id cu trong so tien. Cua so do dong lai vinh vien vao luot tra tien dau.
#:
#: ⚠️ 31 hex = **124 bit**, va tien le nam ngay trong app nay: `assets.py` dung
#:    `asvr_` + 19 hex (76 bit) cho pham vi mot chu so huu. Da do: khong cho nao
#:    phan tich nguoc id nay — moi cho dung no deu chi lay `[:8]` de ghi log.
DAI_HEX_MA_RUN = 31


def sinh_id() -> str:
    """`asvr_<31 hex>` = 36 ky tu. Tien to co chu y — cung loi `vc_`/`upl_`.

    Mot id co tien to tu noi no la gi trong log va trong bao loi, va no chan
    viec vo tinh truyen mot id khac vao dung cho nay.
    """
    return "asvr_" + uuid.uuid4().hex[:DAI_HEX_MA_RUN]


# ── Trang thai mot luot goi nang luc (ADR-001 D9) ────────────────────────────
#
# 🔑 Ba trang thai, va HAI trong so do khong duoc thu lai mu:
#
#     DA_GIAO   provider tra ket qua       -> tinh tien, dung lai duoc
#     TU_CHOI   provider tu choi ro rang   -> khong tinh tien, thu lai duoc
#     MO_HO     mat ket noi SAU khi gui    -> **khong biet** da chay chua
#
# `MO_HO` la trang thai dat nhat trong ca he: co the provider da chay va da tinh
# tien ta, co the chua. Thu lai mu la co the tra tien hai lan cho mot viec; bo
# qua la co the mat mot ket qua da tra tien. Nen no khong tu dong lam gi ca.
DUNG_DA_GIAO = "da_giao"
DUNG_TU_CHOI = "tu_choi"
DUNG_MO_HO = "mo_ho"
DUNG_TRANG_THAI = (DUNG_DA_GIAO, DUNG_TU_CHOI, DUNG_MO_HO)


class AsvRun(Base):
    """Mot lan chay Auto Scan Video. Chu so huu tien cua ca chuoi chin giai doan."""

    __tablename__ = "asv_run"

    id: Mapped[str] = mapped_column(String(48), primary_key=True, default=sinh_id)
    #: ⛔ CHUOI, khong phai so. Xem ghi chu dau tep.
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(16), default=RUN_QUEUED,
                                        nullable=False, index=True)
    #: Phien ban hop dong san pham da dung de chay. Giu lai vi mot lan chay cu
    #: phai doc duoc bang dung luat cua thoi diem no chay, ke ca khi
    #: `auto_scan_mvp_v1` da len v2.
    contract_version: Mapped[str] = mapped_column(
        String(32), default="auto_scan_mvp_v1", nullable=False)

    #: Cai dat cap san pham (`MVP_CONTRACT.md` muc 6). KHONG chua bi mat.
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    #: Khoa artifact nguon, do khach tai len va da promote.
    source_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    #: 🔑 Tien. `credit_held` la so da giu luc nop; `credit_actual` la tong
    #: **DO DUOC** cua cac giai doan — khong bao gio tinh lai tu bang gia.
    #: Xem ADR-001 D4 va vi sao `agent/executor.actual_cost` bi tu choi.
    credit_held: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_asv_run_owner_created", "owner_id", "created_at"),
    )


class AsvStage(Base):
    """Mot giai doan cua mot lan chay. MOT dong cho MOI `(run_id, stage)`."""

    __tablename__ = "asv_stage"

    id: Mapped[str] = mapped_column(String(48), primary_key=True,
                                    default=lambda: "asvs_" + uuid.uuid4().hex)
    run_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    #: Lap lai chu so huu tu `asv_run`. Co y KHONG chuan hoa: mot phep loc quyen
    #: khong nen phu thuoc vao mot phep JOIN ma nguoi viet truy van co the quen.
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=STAGE_PENDING,
                                        nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: Van tay hieu luc (ADR-001 D8). Rong = chua tinh.
    fingerprint: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    #: Tham chieu artifact ben vung do giai doan nay sinh ra.
    outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    #: Job con dang/da thi hanh giai doan nay. Rong khi `pending`.
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                        index=True)
    #: Chi phi **DO DUOC** cua giai doan nay. Cong don len `asv_run.credit_actual`.
    credit_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        #: 🔑 Bat bien I18 nam o day. Mot giai doan chi co MOT dong, nen hai
        #: worker khong the tao hai ban ghi cho cung mot viec.
        UniqueConstraint("run_id", "stage", name="ux_asv_stage_run_stage"),
        Index("ix_asv_stage_run_status", "run_id", "status"),
    )


# ── Trang thai toan ven cua mot artifact ─────────────────────────────────────
ASSET_OK = "ok"                # da kiem: co that, dung co, dung checksum
ASSET_MISSING = "missing"      # tham chieu con, tep da bien mat
ASSET_CORRUPT = "corrupt"      # tep con nhung cham/co lech
ASSET_EXPIRED = "expired"      # qua han luu tru theo chinh sach

#: Loai artifact. Quyet dinh phep kiem hop le nao duoc chay.
KIND_VIDEO = "video"
KIND_AUDIO = "audio"
KIND_JSON = "json"
KIND_TEXT = "text"
#: 🔴 Them o V6 pha 11b (logo cua khach). Mot loai artifact MOI mang mot nghia
#:    vu: `assets.kiem_hop_le` phai biet kiem no. Them ma nay ma khong them phep
#:    kiem la mo mot loai artifact **khong ai soi noi dung** — tuc bat bien I8
#:    ("DONE nghia la co mot ket qua HOP LE") mat hieu luc cho dung loai do.
KIND_ANH = "image"
#: 🔴 Them o asv-final 23/09. `giai_doan_ket_xuat.chay` DA phat ma nay tu pha 14
#:    (`kind: "subtitle"` cho tep `.srt` khach tai ve), nhung no chua bao gio
#:    nam trong `KINDS` — nen `assets.kiem_hop_le` nem
#:    `loai artifact khong biet: 'subtitle'` va `render` chet han.
#:
#: ⛔ Do duoc o nghiem thu cuoi, luot C (smart_localize + phu de `dich` +
#:    `xuat_srt: true` + toc do 1,25): chin giai doan xanh, `compose` xanh, roi
#:    `render failed_terminal`. Tuc lua chon "xuat tep phu de roi" **chua bao
#:    gio chay duoc dau-cuoi** — mot tinh nang chet, khong phai mot tinh nang
#:    hong.
#:
#: ⭐ Va theo dung canh bao o `KIND_ANH` ngay tren: them ma nay DI KEM mot phep
#:    kiem noi dung o `assets.kiem_hop_le` (`_kiem_srt`), khong chi them chuoi.
KIND_PHU_DE = "subtitle"
KINDS = frozenset({KIND_VIDEO, KIND_AUDIO, KIND_JSON, KIND_TEXT, KIND_ANH,
                   KIND_PHU_DE})


class AsvAsset(Base):
    """Mot artifact BEN VUNG do mot giai doan sinh ra, kem lineage va toan ven.

    ## Vi sao khong dung lai `UploadSession`

    `UploadSession` la **ve tai len cua khach**: no lo duong staging -> confirm ->
    promote cho tep NGUON, va no lam viec do tot (co kiem chu ky magic byte, co
    quet don, co doi soat). Nhung no khong co — va khong nen co — thu ma tam
    artifact trung gian can:

      * `created_by_stage` : giai doan nao sinh ra no
      * `parent_keys`      : no dan xuat tu artifact nao (LINEAGE)
      * `checksum`         : co sở de tra loi "tep nay con dung khong"
      * `integrity`        : cau tra loi da luu cua phep kiem tren
      * `schema_version`   : hinh dang cua artifact JSON, doi theo thoi gian

    Mot lan chay sinh ra tam artifact; ep chung vao mo hinh ve tai len se lam
    hong nghia cua `UploadSession` cho moi app khac dang dung no.

    ⇒ Dung lai `UploadSession` cho tep NGUON, them bang nay cho phan con lai.
      Dung dieu ma muc 2 cua Prompt 06 doi: chi them khi ngu nghia con thieu.

    ## Vi sao co `expires_at`, va day KHONG phai mot cot cho co

    🔴 Kho nay da co san mot lo do dung kieu do. `voice_block.audio_key` song
       mai cung du an, con tep no tro toi song **30 ngay** theo han cua `jobs` —
       nen sau 30 ngay khach mo du an cu thay mot trinh phat 404 khong loi giai
       thich (CLAUDE.md, hang LTT VOICE).

       Mot tham chieu khong biet han cua chinh no la mot loi hua se het han. Cot
       nay cong voi `integrity` cho phep tra loi "tep da het han" thay vi de
       trong mot o.
    """

    __tablename__ = "asv_asset"

    id: Mapped[str] = mapped_column(String(48), primary_key=True,
                                    default=lambda: "asva_" + uuid.uuid4().hex)
    #: ⛔ String(36). Xem ghi chu dau tep.
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    #: Giai doan sinh ra no. Rong = tep nguon do khach tai len.
    created_by_stage: Mapped[str] = mapped_column(String(32), default="",
                                                  nullable=False)

    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: sha256 hex. Co so cua moi phep kiem "tep nay con dung khong".
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    #: LINEAGE. Danh sach `storage_key` cua cac artifact dan xuat ra no.
    #:
    #: ⭐ Luu KHOA chu khong luu id: mot khoa tu no da noi ro chu so huu, run va
    #:    giai doan (`asv/{owner}/{run}/{stage}/{van_tay}`), nen mot dong lineage
    #:    doc duoc ma khong phai JOIN nguoc lai bang nay.
    parent_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    #: Hinh dang cua artifact JSON. `transcript.json` v1 va v2 khong doc chung
    #: mot ham duoc, va bo qua dieu do la mot loi phan tich im lang.
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    integrity: Mapped[str] = mapped_column(String(16), default=ASSET_OK,
                                           nullable=False, index=True)
    #: Han luu tru. NULL = khong het han (tep nguon con song theo run).
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        #: Mot khoa luu tru chi duoc ghi nhan MOT LAN. Hai dong cung tro mot tep
        #: la hai cau tra loi cho cung mot cau hoi ve toan ven.
        UniqueConstraint("storage_key", name="ux_asv_asset_storage_key"),
        Index("ix_asv_asset_run_stage", "run_id", "created_by_stage"),
        Index("ix_asv_asset_owner_run", "owner_id", "run_id"),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Checkpoint theo DON VI VIEC — ADR-V4-002 D-V4-10
# ══════════════════════════════════════════════════════════════════════════════

#: Trang thai cua mot don vi viec. Co y **trung ten** voi `STAGE_*`: mot item la
#: mot giai doan thu nho, va dat hai bo tu vung cho cung mot vong doi la buoc
#: nguoi doc phai dich qua lai.
ITEM_PENDING = "pending"
ITEM_RUNNING = "running"
ITEM_SUCCEEDED = "succeeded"
ITEM_FAILED_RETRYABLE = "failed_retryable"
ITEM_FAILED_TERMINAL = "failed_terminal"
ITEM_INVALIDATED = "invalidated"
ITEM_TERMINAL = frozenset({ITEM_SUCCEEDED, ITEM_FAILED_TERMINAL})


class AsvWorkItem(Base):
    """MOT don vi viec ben trong mot giai doan: mot doan tieng, mot canh.

    ## Vi sao bang nay ton tai

    V2 theo doi tien do sinh tieng bang **su ton tai cua tep tren dia**. No chay
    duoc, va no thieu bon thu ma mot checkpoint can:

      * khong co van tay  -> nang phien ban model xong van dung lai tieng cu
      * khong co chi phi  -> khong the cong len thanh so tien cua giai doan
      * khong co so lan thu -> "vong lap co chan" phai dem trong bo nho, va mot
                            worker chet lam bo dem ve 0
      * khong co cot chu so huu -> quyen so huu chi nam trong duong dan

    ## ⛔ DAY KHONG PHAI MOT HANG DOI, va dieu do duoc cuong che bang SU VANG MAT

    `V4_OPERATING_CONTRACT` A.5: `platform_core.jobs` la hang doi SSOT duy nhat.
    Mot bang checkpoint khac mot bang hang doi o **dung nhung cot cho phep mot
    worker tu chon viec**: `claimed_by`, `worker_id`, `locked_by`, `lease_until`,
    `visible_at`, `available_at`, `priority`, `heartbeat_at`.

    Khong cot nao trong so do co o day, va `tests/test_427` chot dieu do — kem
    mot phep tu kiem chay bo do tren mot bang gia CO chung, de "khong co cot xau"
    khong bi nham voi "bo do hong".

    ⭐ Chieu khang dinh: dong item duoc ghi boi chinh handler cua giai doan, ma
       handler do **da dang giu mot `Job` cua nen tang**. Khong cho nao doc bang
       nay de quyet dinh chay gi tiep theo. `jobs._nop_giai_doan_san_sang` van la
       noi duy nhat viec duoc phat, va no phat theo GIAI DOAN.

    ## `revision` — cung ly do nhu `AsvStage`

    Mot item co the bi ghi tu hai cho khi worker cu mat dap nhip va job mo coi
    duoc nhat lai. `UPDATE ... WHERE revision = :r` bien cuoc dua thanh mot xung
    dot **nhin thay duoc** thay vi mot ban ghi de.
    """

    __tablename__ = "asv_work_item"

    id: Mapped[str] = mapped_column(String(48), primary_key=True,
                                    default=sinh_id)
    run_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)

    #: ⛔ Chu so huu nam o COT, khong chi trong khoa luu tru. Mot phep tra
    #:    "item nay co phai cua nguoi dang hoi khong" phai tra loi duoc bang mot
    #:    dieu kien WHERE, khong bang cach phan tich mot duong dan.
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    #: Giai doan so huu item nay. Khop `pipeline.TEN_GIAI_DOAN`.
    stage: Mapped[str] = mapped_column(String(32), nullable=False)

    #: Dinh danh cua don vi viec BEN TRONG giai doan — id doan, id canh.
    #: Duy nhat trong pham vi `(run_id, stage)`, khong duy nhat toan cuc.
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(24), default=ITEM_PENDING,
                                        nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: Cung cach dung nhu `AsvStage.fingerprint`: giai doan + hop dong + phien
    #: ban engine + thiet lap + hash thuong nguon. Mot item hop le va con van tay
    #: khop thi dung lai duoc, va lan dung lai do ton **0** credit.
    fingerprint: Mapped[str] = mapped_column(String(64), default="",
                                             nullable=False)

    outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    #: 🔑 DO DUOC, khong tinh lai tu bang gia (ADR-001 D4, ADR-V4-002 D-V4-12).
    #:
    #: ⛔ Mot giai doan CO item thi `AsvStage.credit_actual` cua no la TONG cua
    #:    cac item, va giai doan do khong duoc tu ghi them mot so nao nua. Cong
    #:    ca hai la tinh tien khach hai lan cho mot viec.
    credit_actual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        #: 🔑 Rang buoc chiu luc. Hai worker khong the tao hai dong cho cung mot
        #:    don vi viec, nen "doan 47 da sinh tieng chua" co dung MOT cau tra loi.
        UniqueConstraint("run_id", "stage", "item_key",
                         name="ux_asv_work_item_run_stage_key"),
        Index("ix_asv_work_item_run_stage_status", "run_id", "stage", "status"),
        Index("ix_asv_work_item_owner_run", "owner_id", "run_id"),
    )


class AsvUsage(Base):
    """MOT luot goi nang luc, **do duoc**. So cai cua lan chay.

    ## Vi sao mot bang rieng, khi da co `AsvWorkItem.credit_actual`

    `credit_actual` tra loi "het bao nhieu". No khong tra loi duoc ba cau hoi ma
    mot lan doi soat tien can:

        nang luc nao da chay        -> khach hoi "toi tra cho cai gi"
        do bang don vi gi           -> 1.200 token va 12 giay la hai the gioi khac
        lan goi do co CHAC da chay  -> ADR-001 D9: dispatch mo ho, xem tren

    Mot don vi viec co the goi NHIEU nang luc (doc canh bang VLM roi sinh tieng
    bang TTS), nen quan he la mot-nhieu va mot cot khong dien dat duoc.

    ## ⛔ BANG NAY KHONG PHAI MOT DUONG TIEN THU HAI

    🔴 Day la cho de sai nhat trong ca pha 06. Neu `features.tong_da_dung` cong
       ca `AsvUsage.credit`, ta co **ba** noi mang tien cho cung mot viec —
       stage, item, va so cai — va `_kiem_khong_tinh_hai_lan` da ton tai chinh
       vi hai noi da la mot noi qua nhieu.

    ⇒ Tien di qua DUNG MOT cot: `AsvWorkItem.credit_actual`. Bang nay la **bang
      chung** giai thich con so do, khong phai mot nguon cong thu hai. Bat bien:

          item.credit_actual == tong credit cua cac dong DA_GIAO cua item do

      `su_dung.doi_soat` kiem dieu do, va `features.quyet_toan` goi no truoc khi
      chot tien — vi mot con so khong giai thich duoc thi khong duoc thu.

    ## An toan khi may chet giua chung

    `su_dung.ghi` viet dong nay VA cong `credit_actual` cua item trong **mot
    giao dich**. May chet truoc commit thi khong co gi; chet sau commit thi ca
    hai deu co. Khong co khe cua so nao de mot ban ghi da giao ton tai ma tien
    chua duoc cong, hoac nguoc lai.

    `UNIQUE(run_id, ma_dispatch)` lo phan con lai: neu tang goi cung cap mot ma
    dispatch **on dinh cua provider**, thi mot lan phat lai cung ma do se bi CSDL
    tu choi thay vi tinh tien lan hai.

    ⚠️ Chinh xac ve pham vi cua loi hua do: no bao ve khi ma dispatch **on dinh**.
       Neu tang goi sinh mot ma moi moi lan thi do la mot lan gui KHAC, va tinh
       tien no la dung. Bang nay khong biet — va khong the biet — hai lan gui
       khac ma co phai cung mot viec hay khong.
    """

    __tablename__ = "asv_usage"

    id: Mapped[str] = mapped_column(String(48), primary_key=True, default=sinh_id)
    run_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)

    #: ⛔ Chu so huu o COT — cung ly do nhu `AsvWorkItem.owner_id`: mot phep tra
    #:    "cua ai" phai la mot dieu kien WHERE.
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    stage: Mapped[str] = mapped_column(String(32), nullable=False)

    #: Don vi viec da sinh ra lan goi nay. Luon co: xem `su_dung.ghi`.
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Lan thu thu may cua item. 🔑 Giu lai de tra loi "vi sao lan chay nay ton
    #: nhieu the" — mot item thu ba lan co ba dong, va hai dong dau van la tien
    #: that neu chung DA_GIAO.
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: Nang luc da goi: `text.chat`, `speech.ltt`, `autosubvideo.transcribe`.
    nang_luc: Mapped[str] = mapped_column(String(64), nullable=False)

    #: App CHU cua nang luc do. ⛔ Khong phai ten vendor ben ngoai: ta khong ban
    #:    ten nha cung cap cho khach (`ltt_llm.ALIAS_SANG_ID` giu lop dem do).
    app_chu: Mapped[str] = mapped_column(String(32), nullable=False)

    trang_thai: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    #: Don vi do. Rong voi `tu_choi`/`mo_ho` — do la mot su that, khong phai mot
    #: cho trong can dien.
    don_vi: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    so_luong: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    #: Credit DO DUOC. Bang 0 tru khi `trang_thai == da_giao`.
    credit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: Danh tinh lan gui, de doi soat khi mo ho va de chong tinh hai lan.
    ma_dispatch: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Vet giai quyet mot dong `mo_ho`: ai quyet, khi nao, ket luan gi.
    ghi_chu: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        #: 🔑 Rang buoc chiu luc. Xem docstring — pham vi loi hua co gioi han.
        UniqueConstraint("run_id", "ma_dispatch", name="ux_asv_usage_run_dispatch"),
        Index("ix_asv_usage_run_stage_item", "run_id", "stage", "item_key"),
        Index("ix_asv_usage_run_trang_thai", "run_id", "trang_thai"),
    )
