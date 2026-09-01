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

from sqlalchemy import (JSON, DateTime, Index, Integer, String, Text,
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


def sinh_id() -> str:
    """`asvr_<32 hex>`. Tien to co chu y — cung loi `vc_`/`upl_` trong kho.

    Mot id co tien to tu noi no la gi trong log va trong bao loi, va no chan
    viec vo tinh truyen mot id khac vao dung cho nay.
    """
    return "asvr_" + uuid.uuid4().hex


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
KINDS = frozenset({KIND_VIDEO, KIND_AUDIO, KIND_JSON, KIND_TEXT})


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
