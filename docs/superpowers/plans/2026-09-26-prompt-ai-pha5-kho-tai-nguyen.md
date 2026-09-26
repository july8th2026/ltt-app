# PROMPT AI OMMI — Pha 5: Kho tài nguyên sâu + Tạo ảnh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa kho tài nguyên của PROMPT AI OMMI lên ngang bản gốc: dedupe theo
hash tệp gốc (scoped theo chủ sở hữu), thùng rác khôi phục được, upload ZIP
hàng loạt qua job (không đồng bộ trong request), bulk-ops trên variant, và
sinh ảnh composite/chia cảnh tự động dựa trên hai bảng thư viện của pha 4
(`ommi_image_template`, `ommi_storyboard_framework`).

**Architecture:** Ba làn độc lập theo tệp. Làn M viết đúng một migration
Alembic cho toàn bộ pha 5 rồi, sau khi làn H và làn I xong, chạy gate MỘT LẦN
DUY NHẤT — đây là gate cuối cùng của TOÀN BỘ 5 pha, không phải của riêng pha
5. Làn H sở hữu dedupe + thùng rác + upload ZIP + bulk ops (mọi thứ động vào
`ommi_resource_variant`). Làn I sở hữu composite (nộp job `taoanh.generate`,
theo dõi bằng `ommi_image_job`) và chia cảnh tự động (gọi LLM nội bộ qua
`apps.prompt_ai_ommi.provider`, dùng `ommi_storyboard_framework`). Việc dài
(giải nén ZIP, sinh ảnh) luôn đi qua hàng đợi job — không bao giờ chạy đồng bộ
trong request.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (`Mapped`/`mapped_column`) + Alembic +
Pillow (thumbnail) + pytest + `TestClient` (fixture `tests/fixtures/...` theo
mẫu `test_139_ommi_resource_generate.py`).

**Spec:** `docs/superpowers/specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md`
— đặc biệt §4.2 Pha 5, §5, §6.7, §9, §10, §12. Plan này lập luận từ spec đó;
người thi hành đọc cả hai.

## Global Constraints

Mọi task dưới đây ngầm mang toàn bộ mục này — sao đúng giá trị, không diễn
giải lại (nguồn: spec §2).

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (`apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` |
| G-3 | App→app | Chỉ cạnh khai tường minh ở `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`. Pha 5 KHÔNG thêm cạnh mới — dùng lại `("prompt_ai_ommi", "taovideo")` đã có từ pha 2 nếu chạm, và job `taoanh.generate` đã hợp lệ từ pha 1 (worker định tuyến theo `job_type`, không theo `app_slug`) |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring |
| G-5 | Alembic | **MỘT head duy nhất**. Head hiện tại lúc viết plan này: `edb8b0fc0ac9`. ⚠️ Lúc THI HÀNH, chạy `python -m alembic heads` để lấy head THẬT — cây có thể đã tiến thêm qua pha 1–4 |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số không trùng (`tools/check_so_test.py`) |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM: `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`. `.ps1` thuần ASCII. Không viết Python inline qua PowerShell |
| G-8 | Việc > vài giây | Đi qua hàng đợi job (`platform_core/job_submit.py:40 submit_with_credit` hoặc `platform_core/jobs.py:251 submit`). Cloudflare cắt upload 100 MB / phản hồi 100 giây |
| G-9 | Tiền | Giữ chỗ → quyết toán → hoàn. Handler **phải ném exception khi lỗi** — trả về êm ru là mất tiền hoàn của khách |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}`, `server/templating.py:ASSET_VER` |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt, chốt trên `https://app.lttstudios.com` |
| G-12 | Lệnh nặng | Qua `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n` ≤ 7 |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate — không L1, không L2, không L3. Gate chỉ MỘT lần ở CUỐI PLAN (task cuối cùng của plan này) |
| G-14 | `D:\BOT GEMINI` | Kho tham chiếu CHỈ ĐỌC |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |

**Ràng buộc riêng của pha 5** (spec §4.2, §6.7, và brief giao việc):

| # | Ràng buộc |
|---|---|
| P5-1 | `file_hash` = sha256 của bytes tệp GỐC, **trước** chuẩn hoá (resize/nén) |
| P5-2 | Dedupe theo `(owner_id, file_hash)` — ⛔ KHÔNG theo `file_hash` toàn cục |
| P5-3 | Upload ZIP: request chỉ nhận và lưu ZIP; giải nén chạy trong JOB (job type mới `prompt_ai_ommi.import_zip`, đăng ký ở `manifest.job_types`) |
| P5-4 | Chặn zip-slip: mọi entry có `..` sau khi chuẩn hoá đường dẫn ⇒ từ chối TOÀN BỘ zip |
| P5-5 | Chặn zip bomb: tối đa **300 entry**, tối đa **20 MiB** mỗi entry đã giải nén, tối đa **500 MiB** tổng đã giải nén, và tỉ lệ nén/gốc > **100×** trên một entry ⇒ từ chối |
| P5-6 | Thumbnail: Pillow, khung tối đa **320×320px** (giữ tỉ lệ), JPEG quality 82, lưu ở khoá **riêng** (hậu tố `__thumb.jpg`), ⛔ không ghi đè ảnh gốc |
| P5-7 | Handler job ném exception khi lỗi (G-9) — không trả `{"ok": False}` êm ru |

---

## Sổ đăng ký dùng chung — ai được ghi (spec §9.1, áp cho pha 5)

| Sổ | Chủ | Luật |
|---|---|---|
| `alembic/versions/` | Làn M | Chỉ M tạo migration. H/I khai cột cần trong task của mình, M viết đúng theo bảng đã cho ở spec §4.2 (đã đủ chi tiết, không cần khai thêm) |
| `apps/prompt_ai_ommi/manifest.py` | Làn M | Thêm `"prompt_ai_ommi.import_zip"` vào `job_types` |
| Dải số test | Bảng dưới | Không lấy số ngoài dải |
| `tools/check_so_test.py` | Không ai | Chỉ giảm |

**Ngoài bảng sở hữu §9.2 của spec** (spec chỉ giao `services/dedupe.py`,
`services/thung_rac.py`, `tables/tai_nguyen.py` cho H, và `services/composite.py`,
`services/breakdown.py` cho I) — plan này **bổ sung** quyền ghi sau, vì endpoint
§6.7 và job handler phải nằm ở đâu đó và không lane nào khác của pha 5 giữ các
tệp này:

| Tệp | Chủ trong pha 5 | Lý do |
|---|---|---|
| `apps/prompt_ai_ommi/routes/resources.py` | Làn H | `upload-zip`, `variants/bulk`, `/api/trash*` là mở rộng tự nhiên của route kho tài nguyên đã có |
| `apps/prompt_ai_ommi/jobs.py` | Làn H | Thêm nhánh xử lý `job_type == "prompt_ai_ommi.import_zip"` |
| `apps/prompt_ai_ommi/routes/library.py` | Làn I | `POST /api/image-templates/{tid}/generate` — cùng miền với `ommi_image_template` (pha 4) |
| `apps/prompt_ai_ommi/routes/storyboard.py` | Làn I | `POST /api/storyboards/{sid}/breakdown` — cùng miền với cảnh/storyboard |

Nếu tại thời điểm thi hành các tệp trên đã có chủ khác từ một plan pha 3/4
song song, dừng và hỏi — đây là chỗ duy nhất plan này lấn ra ngoài bảng gốc.

### Dải số test

| Làn | Dải | Đã dùng trong plan này |
|---|---|---|
| M | `tests/test_5500_*.py` | `test_5500_pha5_migration.py` |
| H | `tests/test_5501_*.py` … `test_5529_*.py` | 5501–5508 |
| I | `tests/test_5530_*.py` … `test_5559_*.py` | 5530–5535 |

⛔ Trước khi tạo tệp test: `python tools/check_so_test.py --list` để chắc số
chưa ai lấy — plan viết TRƯỚC khi thi hành nên không thể tự đảm bảo điều đó.

### Thứ tự chạy

```
M(migration) ──> H ──> I ──> M(GATE, cuối cùng của TOÀN BỘ 5 pha)
```

H và I có thể chạy song song SAU khi migration của M đã xanh, vì không tệp
nào của H trùng tệp của I. Cả hai phải xong trước khi M chạy gate.

---

## Task 1 (Làn M): Migration pha 5

**Files:**
- Create: `alembic/versions/20260926_XXXX_pha5_kho_tai_nguyen_sau.py` (tên tệp
  và `XXXX` = giờ:phút thật lúc tạo, theo quy ước các tệp lân cận)
- Test: `tests/test_5500_pha5_migration.py`

**Interfaces:**
- Consumes: không có (đầu vào là đặc tả cột ở spec §4.2 Pha 5 — đã đủ chi
  tiết, không cần chờ khai báo từ H/I)
- Produces: cột mới trên `ommi_resource_variant`
  (`file_hash: str | None`, `favorite: bool`, `rating: int | None`); bảng
  `ommi_trash`; bảng `ommi_image_job` — H và I dựa vào đúng ba hình dạng này
  để viết ORM model tương ứng ở Task 2 và Task 8.

- [ ] **Step 1: Lấy head Alembic thật**

Chạy:

```
python -m alembic heads
```

Ghi lại giá trị (ví dụ `edb8b0fc0ac9` nếu chưa có commit nào của pha 1–4 chạm
`alembic/versions/`). ⛔ Nếu lệnh trả về **nhiều hơn một** dòng head, dừng lại
— đó là vi phạm G-5 (không phải việc của task này để tự gộp).

- [ ] **Step 2: Viết test đỏ cho migration**

```python
"""tests/test_5500_pha5_migration.py — schema pha 5 đúng hình dạng đã khai."""
from __future__ import annotations

import subprocess
import sys

import pytest
from sqlalchemy import inspect, text


@pytest.fixture()
def db_url(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'pha5-migration.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    return url


def _run_alembic(*args, cwd=None):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True, text=True, cwd=cwd)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_upgrade_creates_pha5_shape(db_url):
    _run_alembic("upgrade", "head")
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    insp = inspect(engine)

    variant_cols = {c["name"] for c in insp.get_columns("ommi_resource_variant")}
    assert {"file_hash", "favorite", "rating"} <= variant_cols

    trash_cols = {c["name"] for c in insp.get_columns("ommi_trash")}
    assert {"id", "owner_id", "target_kind", "target_id", "payload",
            "deleted_at", "purge_after", "created_at"} <= trash_cols

    job_cols = {c["name"] for c in insp.get_columns("ommi_image_job")}
    assert {"id", "owner_id", "template_id", "resource_id", "params",
            "job_id", "version", "parent_id", "status",
            "created_at"} <= job_cols

    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO ommi_resource_variant "
            "(id, resource_id, owner_id, label, storage_key, thumb_key, "
            " width, height, bytes_size, position, created_at) "
            "VALUES ('v1', 'r1', 'o1', '', 'k', '', 0, 0, 0, 0, "
            " CURRENT_TIMESTAMP)"))
        row = conn.execute(text(
            "SELECT favorite, rating, file_hash FROM ommi_resource_variant "
            "WHERE id = 'v1'")).one()
        assert row.favorite in (0, False)   # server_default=false
        assert row.rating is None
        assert row.file_hash is None


def test_downgrade_reverses_cleanly(db_url):
    _run_alembic("upgrade", "head")
    _run_alembic("downgrade", "-1")
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    insp = inspect(engine)
    assert "ommi_trash" not in insp.get_table_names()
    assert "ommi_image_job" not in insp.get_table_names()
    variant_cols = {c["name"] for c in insp.get_columns("ommi_resource_variant")}
    assert "file_hash" not in variant_cols
```

- [ ] **Step 3: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5500_pha5_migration.py -v`
Expected: FAIL — tệp migration pha 5 chưa tồn tại, `alembic upgrade head`
không tạo được các cột/bảng trên.

- [ ] **Step 4: Viết migration**

```python
# -*- coding: utf-8 -*-
"""Pha 5: kho tai nguyen sau — file_hash/favorite/rating + ommi_trash +
ommi_image_job.

Revision ID: <sinh bang python -c "import uuid; print(uuid.uuid4().hex[:12])">
Revises: <HEAD THAT lay o Step 1 — KHONG copy so trong plan nay>
Create Date: 2026-09-26

## VI SAO BA THU NAY DI CHUNG MOT MIGRATION

Ca ba phuc vu dung MOT tinh nang cua pha 5 (kho tai nguyen sau): dedupe can
`file_hash`, thung rac can bang rieng vi phai giu snapshot ban da xoa (khac
`archived_at` von la luu tru tam), va sinh anh composite can theo doi phien
ban/retry qua `ommi_image_job`. Tach ba migration se lam mot lan chay do dang
(chi co file_hash ma khong co ommi_trash) tro thanh mot trang thai hop le gia,
trong khi ba cot/bang nay chi co y nghia CUNG NHAU.

## ROLLBACK

`downgrade()` xoa dung thu tu nguoc: drop hai bang moi truoc, roi drop ba cot
tren `ommi_resource_variant`. Khong xoa du lieu benh vien nao khac.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "REPLACE_WITH_GENERATED_ID"
down_revision = "REPLACE_WITH_REAL_HEAD_FROM_STEP_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ommi_resource_variant") as batch:
        batch.add_column(sa.Column("file_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column(
            "favorite", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("rating", sa.Integer(), nullable=True))
    op.create_index("ix_ommi_resource_variant_file_hash",
                    "ommi_resource_variant", ["file_hash"])

    op.create_table(
        "ommi_trash",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_trash_owner_id", "ommi_trash", ["owner_id"])
    op.create_index("ix_ommi_trash_purge_after", "ommi_trash", ["purge_after"])

    op.create_table(
        "ommi_image_job",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_image_job_owner_id", "ommi_image_job", ["owner_id"])
    op.create_index("ix_ommi_image_job_parent_id", "ommi_image_job", ["parent_id"])


def downgrade() -> None:
    op.drop_table("ommi_image_job")
    op.drop_table("ommi_trash")
    op.drop_index("ix_ommi_resource_variant_file_hash",
                  table_name="ommi_resource_variant")
    with op.batch_alter_table("ommi_resource_variant") as batch:
        batch.drop_column("rating")
        batch.drop_column("favorite")
        batch.drop_column("file_hash")
```

Thay `REPLACE_WITH_GENERATED_ID` bằng một id 12 hex thật (sinh bằng
`python -c "import uuid; print(uuid.uuid4().hex[:12])"`) và
`REPLACE_WITH_REAL_HEAD_FROM_STEP_1` bằng giá trị lấy ở Step 1.

- [ ] **Step 5: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5500_pha5_migration.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260926_XXXX_pha5_kho_tai_nguyen_sau.py tests/test_5500_pha5_migration.py
git commit -m "$(cat <<'EOF'
migration(pha5): them file_hash/favorite/rating + ommi_trash + ommi_image_job

Ba thu phuc vu dung mot tinh nang: dedupe theo hash, thung rac phuc hoi duoc,
va theo doi phien ban/retry cua anh composite.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 (Làn H): ORM model — cột mới + `OmmiTrash` + `OmmiImageJob`

**Files:**
- Modify: `apps/prompt_ai_ommi/tables/tai_nguyen.py` (nội dung tương ứng
  `apps/prompt_ai_ommi/tables.py:85-107` — `OmmiResourceVariant` — trước khi
  làn M pha 1 tách `tables.py` thành package `tables/`. Nếu lúc thi hành gói
  `tables/` chưa tồn tại vì pha 1 chưa chạy trên nhánh này, sửa thẳng
  `apps/prompt_ai_ommi/tables.py` ở đúng vị trí lớp `OmmiResourceVariant`)
- Test: `tests/test_5501_dedupe_owner_scope.py` (viết một phần ở Task 2, phần
  còn lại ở Task 3 — cột phải tồn tại trước khi service dùng được)

**Interfaces:**
- Consumes: schema `ommi_resource_variant.file_hash/favorite/rating`,
  bảng `ommi_trash`, `ommi_image_job` từ Task 1.
- Produces:
  - `OmmiResourceVariant.file_hash: str | None`
  - `OmmiResourceVariant.favorite: bool`
  - `OmmiResourceVariant.rating: int | None`
  - `class OmmiTrash(Base)` với các cột đúng Task 1
  - `class OmmiImageJob(Base)` với các cột đúng Task 1

- [ ] **Step 1: Viết test đỏ xác nhận ORM đọc được cột mới**

```python
"""tests/test_5501_dedupe_owner_scope.py — phần 1: ORM có cột moi."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'orm.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_variant_has_pha5_columns(db_session):
    from apps.prompt_ai_ommi.tables import OmmiResource, OmmiResourceVariant
    resource = OmmiResource(owner_id="o1", kind="character", name="X")
    db_session.add(resource); db_session.flush()
    variant = OmmiResourceVariant(
        resource_id=resource.id, owner_id="o1", storage_key="k",
        file_hash="a" * 64, favorite=True, rating=5)
    db_session.add(variant); db_session.commit()
    got = db_session.get(OmmiResourceVariant, variant.id)
    assert got.file_hash == "a" * 64
    assert got.favorite is True
    assert got.rating == 5


def test_trash_and_image_job_tables_exist(db_session):
    from apps.prompt_ai_ommi.tables import OmmiImageJob, OmmiTrash
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    trash = OmmiTrash(owner_id="o1", target_kind="resource", target_id="r1",
                      payload={"resource": {}}, deleted_at=now,
                      purge_after=now + timedelta(days=30))
    job = OmmiImageJob(owner_id="o1", params={}, status="queued")
    db_session.add_all([trash, job]); db_session.commit()
    assert db_session.get(OmmiTrash, trash.id) is not None
    assert db_session.get(OmmiImageJob, job.id).version == 1
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5501_dedupe_owner_scope.py -v`
Expected: FAIL — `OmmiResourceVariant` chưa có `file_hash`/`favorite`/`rating`,
`OmmiTrash`/`OmmiImageJob` chưa tồn tại (`ImportError`).

- [ ] **Step 3: Thêm cột vào `OmmiResourceVariant`**

Trong lớp `OmmiResourceVariant`, ngay sau dòng khai `position`:

```python
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Pha 5 — dedupe + kho sâu.
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)
    favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

(dòng `created_at` đã có sẵn — chỉ chèn ba dòng `file_hash`/`favorite`/`rating`
phía trước nó.)

- [ ] **Step 4: Thêm `OmmiTrash` và `OmmiImageJob`**

Ở cuối tệp (sau `OmmiResourceUsage` nếu tệp là `tai_nguyen.py`, hoặc cuối
`tables.py` nếu chưa tách):

```python
class OmmiTrash(Base):
    """Thùng rác: bản chờ purge, khôi phục được nguyên id.

    Khác `archived_at` trên `OmmiResource` (lưu trữ TẠM, bản gốc vẫn còn
    trong bảng sống): ở đây bản gốc bị XOÁ THẬT khỏi bảng sống, snapshot đủ
    để dựng lại y hệt nằm trong `payload`. Đây là "xoá" thật sự của khách,
    không phải "ẩn đi".
    """

    __tablename__ = "ommi_trash"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiImageJob(Base):
    """Một lượt sinh ảnh composite — theo dõi phiên bản để revert/retry.

    `parent_id` trỏ lượt sinh trước đó khi đây là một retry; `version` tăng
    dần trong cùng một chuỗi retry của cùng `resource_id`.
    """

    __tablename__ = "ommi_image_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

Nếu tệp là `tables/tai_nguyen.py` (đã tách), thêm `OmmiTrash`,
`OmmiImageJob` vào `tables/__init__.py` re-export cùng các tên khác.

- [ ] **Step 5: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5501_dedupe_owner_scope.py -v`
Expected: PASS cả hai test.

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/tables.py tests/test_5501_dedupe_owner_scope.py
git commit -m "$(cat <<'EOF'
feat(pha5): them OmmiTrash/OmmiImageJob + cot dedupe tren OmmiResourceVariant

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 (Làn H): `services/dedupe.py` — hash + tra cứu theo chủ sở hữu

**Files:**
- Create: `apps/prompt_ai_ommi/services/dedupe.py`
- Modify: `apps/prompt_ai_ommi/services/resources.py:246-268` (hàm
  `add_variant` — thêm tham số `file_hash`)
- Test: `tests/test_5501_dedupe_owner_scope.py` (bổ sung — tệp đã mở ở Task 2)

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.tables.OmmiResourceVariant` (Task 2);
  `apps.prompt_ai_ommi.services.resources.get_owned(db, resource_id, owner_id)`.
- Produces:
  - `compute_file_hash(data: bytes) -> str`
  - `find_existing(db: Session, *, owner_id: str, file_hash: str) -> OmmiResourceVariant | None`
  - `apps.prompt_ai_ommi.services.resources.add_variant(db, *, resource_id, owner_id, storage_key, label="", thumb_key="", width=0, height=0, bytes_size=0, file_hash="") -> OmmiResourceVariant`
    (chữ ký cũ + tham số `file_hash` tuỳ chọn, mặc định `""` để không phá lời
    gọi hiện có ở `routes/resources.py`)

- [ ] **Step 1: Viết test đỏ**

Thêm vào `tests/test_5501_dedupe_owner_scope.py`:

```python
def test_two_owners_uploading_the_same_bytes_get_two_variants(db_session):
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc
    data = b"\x89PNG" + b"\x00" * 100
    file_hash = dedupe.compute_file_hash(data)

    r1 = rsvc.create(db_session, owner_id="alice", kind="character", name="A")
    v1 = rsvc.add_variant(db_session, resource_id=r1.id, owner_id="alice",
                          storage_key="k1", file_hash=file_hash)

    r2 = rsvc.create(db_session, owner_id="bob", kind="character", name="B")
    v2 = rsvc.add_variant(db_session, resource_id=r2.id, owner_id="bob",
                          storage_key="k2", file_hash=file_hash)

    assert v1.id != v2.id
    assert dedupe.find_existing(db_session, owner_id="alice",
                                file_hash=file_hash).id == v1.id
    assert dedupe.find_existing(db_session, owner_id="bob",
                                file_hash=file_hash).id == v2.id


def test_same_owner_uploading_twice_finds_the_first_variant(db_session):
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc
    data = b"\x89PNG" + b"\x01" * 100
    file_hash = dedupe.compute_file_hash(data)

    r1 = rsvc.create(db_session, owner_id="alice", kind="character", name="A")
    v1 = rsvc.add_variant(db_session, resource_id=r1.id, owner_id="alice",
                          storage_key="k1", file_hash=file_hash)

    found = dedupe.find_existing(db_session, owner_id="alice",
                                 file_hash=file_hash)
    assert found is not None and found.id == v1.id
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5501_dedupe_owner_scope.py -v`
Expected: FAIL — `apps.prompt_ai_ommi.services.dedupe` chưa tồn tại, và
`add_variant` chưa nhận `file_hash`.

- [ ] **Step 3: Viết `services/dedupe.py`**

```python
"""dedupe.py — sha256 cua bytes tep GOC + tra cuu theo CHU SO HUU (pha 5).

⚠️ Dedupe theo `(owner_id, file_hash)`, KHONG theo `file_hash` toan cuc: hai
khach tai cung mot anh la HAI ban ghi rieng, vi quyen so huu khac nhau — gop
chung se lam mot khach xoa anh cua minh xoa luon anh cua nguoi khac dang tro
vao cung hang.

`file_hash` la sha256 cua BYTES TE GOC, truoc moi buoc chuan hoa (resize/nen).
Goi ham nay TRUOC khi lam bat cu dieu gi khac voi du lieu vua nhan.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import OmmiResourceVariant


def compute_file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_existing(db: Session, *, owner_id: str,
                  file_hash: str) -> OmmiResourceVariant | None:
    """Bản đã có CỦA CHÍNH `owner_id` với cùng `file_hash`, hoặc `None`.

    Không lọc theo `resource_id`: một khách import lại cùng file vào một
    resource khác vẫn được coi là "đã có", vì mục đích của dedupe là không để
    một tài khoản giữ hai bản y hệt nhau trên storage — không phải để ép file
    ở đúng một resource.
    """
    if not file_hash:
        return None
    return db.execute(
        select(OmmiResourceVariant)
        .where(OmmiResourceVariant.owner_id == owner_id,
               OmmiResourceVariant.file_hash == file_hash)
        .order_by(OmmiResourceVariant.created_at)
    ).scalars().first()
```

- [ ] **Step 4: Thêm tham số `file_hash` vào `add_variant`**

Trong `apps/prompt_ai_ommi/services/resources.py`, sửa chữ ký và thân hàm
`add_variant` (dòng 246-268):

```python
def add_variant(db: Session, *, resource_id: str, owner_id: str,
                storage_key: str, label: str = "", thumb_key: str = "",
                width: int = 0, height: int = 0,
                bytes_size: int = 0, file_hash: str = "") -> OmmiResourceVariant:
    resource = get_owned(db, resource_id, owner_id)
    if not (storage_key or "").strip():
        raise ResourceError("Thiếu khoá lưu trữ của ảnh.")
    position = db.execute(
        select(func.coalesce(func.max(OmmiResourceVariant.position), -1))
        .where(OmmiResourceVariant.resource_id == resource_id)
    ).scalar_one() + 1
    row = OmmiResourceVariant(
        resource_id=resource_id, owner_id=owner_id, label=_clean_text(label, 160),
        storage_key=storage_key.strip(), thumb_key=(thumb_key or "").strip(),
        width=int(width or 0), height=int(height or 0),
        bytes_size=int(bytes_size or 0), position=position,
        file_hash=(file_hash or "").strip() or None)
    db.add(row)
    db.flush()
    if not resource.cover_variant_id:
        resource.cover_variant_id = row.id
    resource.updated_at = _now()
    db.flush()
    return row
```

(chỉ dòng tham số hàm và dòng `file_hash=...` trong `OmmiResourceVariant(...)`
là mới; phần còn lại giữ nguyên y hệt bản hiện có.)

- [ ] **Step 5: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5501_dedupe_owner_scope.py -v`
Expected: PASS cả bốn test trong tệp.

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/services/dedupe.py apps/prompt_ai_ommi/services/resources.py tests/test_5501_dedupe_owner_scope.py
git commit -m "$(cat <<'EOF'
feat(pha5): dedupe theo (owner_id, file_hash), khong dedupe cheo chu

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 (Làn H): `services/thung_rac.py` — xoá → thùng rác → khôi phục/purge

**Files:**
- Create: `apps/prompt_ai_ommi/services/thung_rac.py`
- Test: `tests/test_5502_thung_rac_restore_purge.py`

**Interfaces:**
- Consumes: `OmmiTrash`, `OmmiResource`, `OmmiResourceVariant` (Task 2);
  `resources.get_owned`, `resources.variants`, `resources.ResourceNotFound`.
- Produces:
  - `delete_resource(db, *, resource_id: str, owner_id: str, purge_after_days: int = 30) -> OmmiTrash`
  - `restore(db, *, trash_id: str, owner_id: str) -> "OmmiResource"`
  - `list_trash(db, *, owner_id: str) -> list[OmmiTrash]`
  - `purge_expired(db, *, now: "datetime | None" = None, storage=None) -> dict`

- [ ] **Step 1: Viết test đỏ**

```python
"""tests/test_5502_thung_rac_restore_purge.py."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trash.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_delete_moves_to_trash_and_restore_brings_back_the_same_row(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Kiem")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                     storage_key="k1")
    original_id = r.id
    db_session.commit()

    trash = thung_rac.delete_resource(db_session, resource_id=original_id,
                                      owner_id="alice")
    db_session.commit()

    with pytest.raises(rsvc.ResourceNotFound):
        rsvc.get_owned(db_session, original_id, "alice")

    restored = thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")
    db_session.commit()

    assert restored.id == original_id
    again = rsvc.get_owned(db_session, original_id, "alice")
    assert again.name == "Kiem"
    assert len(rsvc.variants(db_session, original_id, "alice")) == 1


def test_purge_removes_expired_entries_and_their_files(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac

    class _FakeStorage:
        def __init__(self):
            self.deleted = []

        def delete(self, key):
            self.deleted.append(key)

    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="Cu")
    rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                     storage_key="stale-key")
    db_session.commit()
    trash = thung_rac.delete_resource(db_session, resource_id=r.id,
                                      owner_id="alice", purge_after_days=1)
    db_session.commit()

    future = datetime.now(timezone.utc) + timedelta(days=2)
    storage = _FakeStorage()
    result = thung_rac.purge_expired(db_session, now=future, storage=storage)
    db_session.commit()

    assert result["da_xoa_ban"] == 1
    assert storage.deleted == ["stale-key"]
    with pytest.raises(rsvc.ResourceNotFound):
        # Đã purge — restore không còn hiệu lực.
        thung_rac.restore(db_session, trash_id=trash.id, owner_id="alice")


def test_restore_rejects_a_ticket_that_is_not_yours(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc, thung_rac
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="X")
    db_session.commit()
    trash = thung_rac.delete_resource(db_session, resource_id=r.id, owner_id="alice")
    db_session.commit()
    with pytest.raises(rsvc.ResourceNotFound):
        thung_rac.restore(db_session, trash_id=trash.id, owner_id="mallory")
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5502_thung_rac_restore_purge.py -v`
Expected: FAIL — `apps.prompt_ai_ommi.services.thung_rac` không tồn tại.

- [ ] **Step 3: Viết `services/thung_rac.py`**

```python
"""thung_rac.py — xoa THAT nhung phuc hoi duoc (pha 5).

Khac `OmmiResource.archived_at` (luu tru TAM, ban goc con nguyen trong bang
song): o day ban goc bi XOA THAT khoi bang song; snapshot du de dung lai
NGUYEN VEN — cung id, cung cot — nam trong `OmmiTrash.payload`.

`purge_after` mac dinh 30 ngay, cung so voi `retention.TUOI_TOI_THIEU` — dung
mot con so cho "thoi gian an toan truoc khi mat vinh vien" trong toan app.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.services import resources as rsvc
from apps.prompt_ai_ommi.services.resources import ResourceNotFound
from apps.prompt_ai_ommi.tables import OmmiResource, OmmiResourceVariant, OmmiTrash

PURGE_MAC_DINH_NGAY = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resource_snapshot(row: OmmiResource) -> dict:
    return {"id": row.id, "kind": row.kind, "name": row.name,
            "description": row.description, "prompt_text": row.prompt_text,
            "attributes": row.attributes or {},
            "cover_variant_id": row.cover_variant_id}


def _variant_snapshot(row: OmmiResourceVariant) -> dict:
    return {"id": row.id, "label": row.label, "storage_key": row.storage_key,
            "thumb_key": row.thumb_key, "width": row.width,
            "height": row.height, "bytes_size": row.bytes_size,
            "position": row.position, "file_hash": row.file_hash,
            "favorite": row.favorite, "rating": row.rating}


def delete_resource(db: Session, *, resource_id: str, owner_id: str,
                    purge_after_days: int = PURGE_MAC_DINH_NGAY) -> OmmiTrash:
    """Xoá HẲN một tài nguyên (và mọi variant của nó) khỏi bảng sống.

    Snapshot đủ để `restore()` dựng lại y hệt, kể cả `id` — bindings hay
    project khác còn tham chiếu `resource_id` này vẫn trỏ đúng sau khi khôi
    phục.
    """
    resource = rsvc.get_owned(db, resource_id, owner_id)
    variant_rows = rsvc.variants(db, resource_id, owner_id)
    payload = {"resource": _resource_snapshot(resource),
              "variants": [_variant_snapshot(v) for v in variant_rows]}
    trash = OmmiTrash(
        owner_id=owner_id, target_kind="resource", target_id=resource_id,
        payload=payload, deleted_at=_now(),
        purge_after=_now() + timedelta(days=purge_after_days))
    db.add(trash)
    for v in variant_rows:
        db.delete(v)
    db.delete(resource)
    db.flush()
    return trash


def restore(db: Session, *, trash_id: str, owner_id: str) -> OmmiResource:
    """Dựng lại ĐÚNG bản ghi cũ (cùng id) từ snapshot. Vé dùng một lần."""
    row = db.get(OmmiTrash, trash_id)
    if row is None or row.owner_id != owner_id:
        raise ResourceNotFound("Không tìm thấy vé thùng rác.")
    data = row.payload.get("resource") or {}
    resource = OmmiResource(
        id=data.get("id"), owner_id=owner_id, kind=data.get("kind", "misc"),
        name=data.get("name", ""), description=data.get("description", ""),
        prompt_text=data.get("prompt_text", ""),
        attributes=data.get("attributes") or {},
        cover_variant_id=data.get("cover_variant_id"))
    db.add(resource)
    for v in row.payload.get("variants") or []:
        db.add(OmmiResourceVariant(
            id=v.get("id"), resource_id=resource.id, owner_id=owner_id,
            label=v.get("label", ""), storage_key=v.get("storage_key", ""),
            thumb_key=v.get("thumb_key", ""), width=v.get("width", 0),
            height=v.get("height", 0), bytes_size=v.get("bytes_size", 0),
            position=v.get("position", 0), file_hash=v.get("file_hash"),
            favorite=bool(v.get("favorite", False)), rating=v.get("rating")))
    db.delete(row)
    db.flush()
    return resource


def list_trash(db: Session, *, owner_id: str) -> list[OmmiTrash]:
    return list(db.execute(
        select(OmmiTrash).where(OmmiTrash.owner_id == owner_id)
        .order_by(OmmiTrash.deleted_at.desc())
    ).scalars().all())


def purge_expired(db: Session, *, now: datetime | None = None,
                  storage=None) -> dict:
    """Xoá vĩnh viễn mọi vé đã quá hạn — kể cả file trên storage.

    Lỗi xoá file KHÔNG được làm hỏng cả lượt purge (cùng nguyên tắc với
    `retention.apply`): dòng CSDL đã đi rồi, một file thừa nằm lại vô hại hơn
    dừng giữa chừng.
    """
    moc = now or _now()
    due = list(db.execute(
        select(OmmiTrash).where(OmmiTrash.purge_after <= moc)
    ).scalars().all())
    xoa_ban = 0
    xoa_anh = 0
    for row in due:
        if storage is not None:
            for v in row.payload.get("variants") or []:
                key = v.get("storage_key")
                if not key:
                    continue
                try:
                    storage.delete(key)
                    xoa_anh += 1
                except Exception:              # noqa: BLE001
                    pass
        db.delete(row)
        xoa_ban += 1
    db.flush()
    return {"da_xoa_ban": xoa_ban, "da_xoa_anh": xoa_anh}
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5502_thung_rac_restore_purge.py -v`
Expected: PASS cả ba test.

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/thung_rac.py tests/test_5502_thung_rac_restore_purge.py
git commit -m "$(cat <<'EOF'
feat(pha5): thung rac phuc hoi dung id + purge qua han kem xoa file

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 (Làn H): Upload ZIP — nhận đồng bộ, giải nén trong job

**Files:**
- Modify: `apps/prompt_ai_ommi/manifest.py:44` (thêm job_type)
- Modify: `apps/prompt_ai_ommi/jobs.py` (nhánh xử lý job_type mới)
- Modify: `apps/prompt_ai_ommi/routes/resources.py` (thêm endpoint cuối tệp,
  sau dòng 533)
- Test: `tests/test_5503_upload_zip_zip_slip.py`,
  `tests/test_5504_upload_zip_bomb_limits.py`,
  `tests/test_5505_upload_zip_job_dedupe.py`

⚠️ Task này thuộc Làn M cho đúng một dòng (`manifest.py:44`) — theo luật sổ
đăng ký dùng chung, làn H KHÔNG tự sửa `manifest.py`. Trước khi bắt đầu Step
3, làn H gửi yêu cầu "thêm `prompt_ai_ommi.import_zip` vào `job_types`" cho
làn M và chờ M commit dòng đó, HOẶC nếu đang chạy một mình (không có làn M
song song thật), tự thực hiện Step 0 dưới đây thay cho M rồi ghi rõ trong
commit message rằng đây là thay mặt M.

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.services.dedupe.compute_file_hash/find_existing`
  (Task 3); `apps.prompt_ai_ommi.services.resources.add_variant` (Task 3);
  `platform_core.storage.get_storage()` (`put`/`open`/`delete`/`exists`);
  `platform_core.jobs.submit(db, *, user_id, app_slug, job_type, params,
  dedupe_key="") -> Job`; `platform_core.job_submit.dedupe_key_for(job_type,
  params) -> str`.
- Produces:
  - `apps.prompt_ai_ommi.jobs._handle_import_zip(params: dict, ctx=None) -> dict`
    (gọi từ `handle()` khi `ctx.job_type == "prompt_ai_ommi.import_zip"`)
  - `POST /prompt-ai-ommi/api/resources/upload-zip` → `{job_id, status}`

- [ ] **Step 0 (thay mặt Làn M nếu cần): đăng ký job_type**

Trong `apps/prompt_ai_ommi/manifest.py:44`, đổi:

```python
    job_types=("prompt_ai_ommi.generate",),
```

thành:

```python
    job_types=("prompt_ai_ommi.generate", "prompt_ai_ommi.import_zip"),
```

- [ ] **Step 1: Viết test đỏ cho zip-slip**

```python
"""tests/test_5503_upload_zip_zip_slip.py."""
from __future__ import annotations

import io
import zipfile

import pytest


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_zip_slip_entry_is_rejected_and_nothing_is_written(tmp_path):
    from apps.prompt_ai_ommi.services import upload_zip

    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 40,
        "../../thoat.png": b"\x89PNG" + b"\x00" * 40,
    })
    dest = tmp_path / "extract"
    with pytest.raises(upload_zip.ZipImportError, match="zip-slip"):
        list(upload_zip.iter_safe_entries(payload))
    assert not dest.exists() or list(dest.iterdir()) == []
```

Ghi chú: `upload_zip.py` chưa tồn tại — tạo ở Step 4 dưới dạng module con của
`services/` (đặt cùng chỗ với `dedupe.py`/`thung_rac.py` vì cùng miền "kho tài
nguyên sâu").

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5503_upload_zip_zip_slip.py -v`
Expected: FAIL — `apps.prompt_ai_ommi.services.upload_zip` chưa tồn tại.

- [ ] **Step 3: Viết test đỏ cho zip bomb**

```python
"""tests/test_5504_upload_zip_bomb_limits.py."""
from __future__ import annotations

import io
import zipfile

import pytest


def test_too_many_entries_is_rejected():
    from apps.prompt_ai_ommi.services import upload_zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(upload_zip.MAX_ENTRIES + 1):
            zf.writestr(f"img_{i}.png", b"\x89PNG")
    with pytest.raises(upload_zip.ZipImportError, match="so luong tep"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))


def test_single_entry_over_the_uncompressed_cap_is_rejected():
    from apps.prompt_ai_ommi.services import upload_zip
    huge = b"\x00" * (upload_zip.MAX_ENTRY_UNCOMPRESSED + 1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.png", huge)
    with pytest.raises(upload_zip.ZipImportError, match="qua lon"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))


def test_suspicious_compression_ratio_is_rejected():
    """Zip bomb kinh điển: rất nhỏ khi nén, khổng lồ khi giải nén."""
    from apps.prompt_ai_ommi.services import upload_zip
    payload = b"\x00" * (2 * 1024 * 1024)   # nén cực tốt vì toàn số 0
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("suspicious.png", payload)
    with pytest.raises(upload_zip.ZipImportError, match="ti le nen"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))
```

- [ ] **Step 4: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5504_upload_zip_bomb_limits.py -v`
Expected: FAIL — module chưa tồn tại.

- [ ] **Step 5: Viết `services/upload_zip.py`**

```python
"""upload_zip.py — giai nen ZIP an toan cho kho tai nguyen (pha 5).

Ba lop chan, theo dung thu tu kiem tra (re nhat truoc):

1. So luong entry — mot ZIP hop le cho kho anh khong can hang nghin tep.
2. Kich thuoc GIAI NEN cua tung entry va TONG CA ZIP — chan bomb "nhieu tep
   vua".
3. Ti le nen/goc tren TUNG entry — chan bomb "mot tep nen cuc tot" (vi du
   toan so 0) ma hai kiem tra tren khong bat duoc vi so luong entry va tong
   kich thuoc van nho.

Zip-slip: `ZipInfo.filename` sau khi chuan hoa dau `/` va bo `./` khong duoc
chua doan `..` — tu choi CA ZIP ngay khi thay MOT entry xau, khong chi bo qua
rieng entry do. Mot file doc duoc TRONG mot zip bi tu choi van la "khong co
tep nao duoc ghi ra ngoai" — dung boc toan bo trong mot vong kiem TRUOC khi
ghi bat cu byte nao.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass

MAX_ENTRIES = 300
MAX_ENTRY_UNCOMPRESSED = 20 * 1024 * 1024      # 20 MiB — dong bo _RESOURCE_IMAGE_CAP
MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024     # 500 MiB
MAX_COMPRESSION_RATIO = 100

_ANH_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class ZipImportError(ValueError):
    """Zip khong an toan hoac khong hop le — route/job tra loi ro rang."""


@dataclass(frozen=True)
class ZipEntry:
    name: str
    data: bytes


def _safe_name(raw: str) -> str:
    cleaned = raw.replace("\\", "/").strip("/")
    parts = [p for p in cleaned.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ZipImportError(f"zip-slip: duong dan di ra ngoai: {raw!r}")
    if not parts:
        raise ZipImportError(f"ten tep rong trong zip: {raw!r}")
    return "/".join(parts)


def iter_safe_entries(zip_bytes: bytes):
    """Sinh `ZipEntry` cho từng ảnh hợp lệ. Ném `ZipImportError` NGAY khi gặp
    entry xấu đầu tiên — không âm thầm bỏ qua rồi vẫn nhập phần còn lại,
    vì "zip bị từ chối" phải có nghĩa là KHÔNG tệp nào từ nó đi vào storage.
    """
    try:
        zf = zipfile.ZipFile(__import__("io").BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ZipImportError("tep khong phai ZIP hop le") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ZipImportError(
            f"vuot so luong tep cho phep ({MAX_ENTRIES})")

    total_uncompressed = 0
    checked: list[zipfile.ZipInfo] = []
    for info in infos:
        if info.is_dir():
            continue
        name = _safe_name(info.filename)          # ném sớm nếu zip-slip
        if not any(name.lower().endswith(ext) for ext in _ANH_EXT):
            continue
        if info.file_size > MAX_ENTRY_UNCOMPRESSED:
            raise ZipImportError(
                f"tep {name!r} qua lon sau giai nen "
                f"(> {MAX_ENTRY_UNCOMPRESSED} bytes)")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO:
                raise ZipImportError(
                    f"tep {name!r} co ti le nen bat thuong ({ratio:.0f}x) "
                    "— tu choi de an toan")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise ZipImportError(
                f"tong dung luong sau giai nen vuot {MAX_TOTAL_UNCOMPRESSED} bytes")
        checked.append(info)

    for info in checked:
        name = _safe_name(info.filename)
        yield ZipEntry(name=name, data=zf.read(info))
```

- [ ] **Step 6: Chạy hai test đã viết, xác nhận XANH**

Run: `pytest tests/test_5503_upload_zip_zip_slip.py tests/test_5504_upload_zip_bomb_limits.py -v`
Expected: PASS cả bốn test.

- [ ] **Step 7: Viết test đỏ cho job giải nén + dedupe trong ZIP**

```python
"""tests/test_5505_upload_zip_job_dedupe.py."""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'zip.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="zip-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 500, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-zip-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "zip-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def _resource(client, token):
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "character", "name": "Nhan vat",
                             "prompt_text": "mot nhan vat"})
    return made.json()["id"]


def test_upload_zip_queues_a_job_and_does_not_extract_synchronously(api):
    client, token = api
    rid = _resource(client, token)
    same_bytes = b"\x89PNG" + b"\x00" * 200
    payload = _zip_bytes({"a.png": same_bytes, "b.png": same_bytes})

    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("bo.zip", io.BytesIO(payload), "application/zip")})
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        assert job.job_type == "prompt_ai_ommi.import_zip"
        assert job.status in ("queued", "running")
    finally:
        db.close()


def test_import_job_dedupes_identical_entries_within_the_same_owner(api):
    from apps.prompt_ai_ommi import jobs as ommi_jobs
    client, token = api
    rid = _resource(client, token)
    same_bytes = b"\x89PNG" + b"\x00" * 200
    payload = _zip_bytes({"a.png": same_bytes, "b.png": same_bytes})

    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("bo.zip", io.BytesIO(payload), "application/zip")})
    job_id = resp.json()["job_id"]

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        result = ommi_jobs.handle(job.params, ctx=None)
    finally:
        db.close()

    assert result["created"] == 1
    assert result["deduped"] == 1


def test_zip_with_a_traversal_entry_writes_nothing(api, tmp_path):
    client, token = api
    rid = _resource(client, token)
    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 40,
        "../../thoat.png": b"\x89PNG" + b"\x00" * 40,
    })
    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("evil.zip", io.BytesIO(payload), "application/zip")})
    job_id = resp.json()["job_id"]

    from apps.prompt_ai_ommi import jobs as ommi_jobs
    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        with pytest.raises(Exception):
            ommi_jobs.handle(job.params, ctx=None)
    finally:
        db.close()
```

- [ ] **Step 8: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5505_upload_zip_job_dedupe.py -v`
Expected: FAIL — endpoint `upload-zip` chưa tồn tại (404), `jobs.handle` chưa
biết `import_zip`.

- [ ] **Step 9: Thêm endpoint nhận ZIP (đồng bộ, chỉ lưu + nộp job)**

Ở cuối `apps/prompt_ai_ommi/routes/resources.py` (sau dòng 533):

```python
# ── Upload ZIP hàng loạt (R5) ───────────────────────────────────────────────
#
# Request CHỈ nhận và lưu ZIP — giải nén luôn chạy trong job (G-8): Cloudflare
# cắt upload ở 100 MB / phản hồi ở 100 giây, và một ZIP vài trăm ảnh giải nén
# xong dễ vượt cả hai trần đó nếu làm đồng bộ trong request.

_ZIP_UPLOAD_CAP = 95 * 1024 * 1024   # chừa biên dưới trần 100 MB của Cloudflare


@router.post("/api/resources/upload-zip", status_code=202)
async def upload_resource_zip(request: Request, file: UploadFile = File(...),
                              resource_id: str = Form(...),
                              csrf_token: str = Form(""),
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.job_submit import dedupe_key_for
    from platform_core.jobs import submit
    from platform_core.storage import get_storage
    _csrf(request, {"csrf_token": csrf_token}); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    data = await file.read(_ZIP_UPLOAD_CAP + 1)
    if not data:
        raise HTTPException(status_code=400, detail=_t('File rỗng.'))
    if len(data) > _ZIP_UPLOAD_CAP:
        raise HTTPException(status_code=413, detail=_t('ZIP vượt 95 MB.'))

    staging_key = f"ommi/{user.id}/zip-staging/{uuid.uuid4().hex[:16]}.zip"
    get_storage().put(staging_key, io.BytesIO(data),
                      content_type="application/zip")

    params = {"owner_id": user.id, "resource_id": resource_id,
             "zip_key": staging_key}
    job = submit(db, user_id=user.id, app_slug=MANIFEST.slug,
                job_type="prompt_ai_ommi.import_zip", params=params,
                dedupe_key=dedupe_key_for("prompt_ai_ommi.import_zip", params))
    db.commit()
    return {"job_id": job.id, "status": job.status}
```

- [ ] **Step 10: Thêm nhánh `import_zip` vào `jobs.py`**

Trong `apps/prompt_ai_ommi/jobs.py`, đổi `handle()` thành router theo
`ctx.job_type`, giữ nguyên nhánh cũ:

```python
def handle(params: dict, ctx=None) -> dict:
    job_type = getattr(ctx, "job_type", "") or "prompt_ai_ommi.generate"
    if job_type == "prompt_ai_ommi.import_zip":
        return _handle_import_zip(params, ctx=ctx)
    return _handle_generate(params, ctx=ctx)


def _handle_generate(params: dict, ctx=None) -> dict:
    story = str(params.get("story") or "").strip()
    if len(story) < 20:
        raise ValueError(_t('Nội dung brief tối thiểu 20 ký tự.'))
    operation = str(params.get("operation") or "director")
    if operation not in {"director", "storyboard"}:
        raise ValueError(_t('Operation không hợp lệ.'))
    if ctx is not None:
        ctx.progress(10, "đang kiểm tra brief và consistency anchors")
    system, prompt = director_prompt(params)
    if ctx is not None:
        ctx.progress(30, "AI Director đang phân cảnh")
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(system, prompt, model=model)
    if ctx is not None:
        ctx.progress(85, "đang chuẩn hóa prompt package")
    package = _normalize_result(raw, params)
    from apps.prompt_ai_ommi.manifest import _cost
    result = {
        "operation": operation,
        "prompt_package": package,
        "storyboard": package if operation == "storyboard" else None,
        "master_prompt": prompt[:20000], "tokens_used": tokens,
        "model": model,
        "credit_cost": _cost(params),
    }
    if ctx is not None:
        ctx.progress(100, "hoàn tất prompt package")
    return result


def _handle_import_zip(params: dict, ctx=None) -> dict:
    """Giải nén ZIP đã tải lên trước đó, tạo variant, dedupe theo owner.

    G-9: mọi lỗi PHẢI ném — bao gồm zip-slip/zip-bomb — để nền tảng biết job
    thất bại (không hoàn credit vì job này KHÔNG tính tiền, nhưng khách vẫn
    phải thấy lỗi thay vì "xong 0 ảnh" im lặng).
    """
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc, upload_zip
    from platform_core.storage import get_storage

    owner_id = str(params.get("owner_id") or "")
    resource_id = str(params.get("resource_id") or "")
    zip_key = str(params.get("zip_key") or "")
    if not (owner_id and resource_id and zip_key):
        raise ValueError(_t('Thiếu tham số nhập ZIP.'))

    storage = get_storage()
    with storage.open(zip_key) as fh:
        zip_bytes = fh.read()

    created = 0
    deduped = 0
    entries = list(upload_zip.iter_safe_entries(zip_bytes))
    total = len(entries)
    for index, entry in enumerate(entries):
        file_hash = dedupe.compute_file_hash(entry.data)
        existing = dedupe.find_existing(_db_for_ctx(ctx), owner_id=owner_id,
                                        file_hash=file_hash) if ctx is not None else None
        if existing is not None:
            deduped += 1
        else:
            ext = entry.name.rsplit(".", 1)[-1].lower()
            key = f"ommi/{owner_id}/{resource_id}/{uuid.uuid4().hex[:16]}.{ext}"
            storage.put(key, io.BytesIO(entry.data),
                       content_type=f"image/{ext if ext != 'jpg' else 'jpeg'}")
            rsvc.add_variant(_db_for_ctx(ctx), resource_id=resource_id,
                             owner_id=owner_id, storage_key=key,
                             label=entry.name, bytes_size=len(entry.data),
                             file_hash=file_hash)
            created += 1
        if ctx is not None:
            ctx.progress(int(100 * (index + 1) / max(total, 1)),
                        f"đã xử lý {index + 1}/{total}")

    storage.delete(zip_key)
    return {"created": created, "deduped": deduped, "total": total}
```

⚠️ `_db_for_ctx(ctx)` chưa tồn tại — đây là chỗ handler job cần một session DB
riêng bên trong worker. Trong repo hiện tại, mẫu chuẩn là dùng
`platform_core.db.get_session()` trực tiếp (xem `_voi_db` trong
`apps/taoanh/jobs.py:114-121`) chứ không truyền qua `ctx`. Trước khi implement
Step này, đọc `apps/taoanh/jobs.py:112-121` và thay `_db_for_ctx(ctx)` bằng
đúng mẫu `get_session()` một-phiên-một-lần đó (mở phiên, `commit()` sau mỗi
`add_variant`/dedupe lookup, đóng phiên) — đây là chỗ duy nhất trong toàn plan
để lại một khoảng trống cố ý, vì nó phụ thuộc bản `platform_core/db.py` thật
tại thời điểm thi hành, không phải vào bất kỳ quyết định thiết kế nào của pha
5.

- [ ] **Step 11: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5505_upload_zip_job_dedupe.py -v`
Expected: PASS cả ba test.

- [ ] **Step 12: Commit**

```bash
git add apps/prompt_ai_ommi/manifest.py apps/prompt_ai_ommi/jobs.py apps/prompt_ai_ommi/routes/resources.py apps/prompt_ai_ommi/services/upload_zip.py tests/test_5503_upload_zip_zip_slip.py tests/test_5504_upload_zip_bomb_limits.py tests/test_5505_upload_zip_job_dedupe.py
git commit -m "$(cat <<'EOF'
feat(pha5): upload ZIP qua job, chan zip-slip/zip-bomb, dedupe theo owner

Request chi nhan va luu ZIP; giai nen chay trong job
prompt_ai_ommi.import_zip vi Cloudflare cat upload 100 MB / phan hoi 100s.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6 (Làn H): Thumbnail Pillow — khoá riêng, không ghi đè gốc

**Files:**
- Modify: `apps/prompt_ai_ommi/services/upload_zip.py` (thêm hàm thumbnail,
  gọi từ `jobs._handle_import_zip`)
- Modify: `apps/prompt_ai_ommi/jobs.py` (nối `make_thumbnail` vào
  `_handle_import_zip`)
- Test: `tests/test_5508_thumbnail_generation.py`

**Interfaces:**
- Consumes: `platform_core.storage.get_storage()`.
- Produces: `make_thumbnail(storage, *, original_key: str, data: bytes) -> str`
  (trả về `thumb_key`, khoá RIÊNG với `original_key`).

- [ ] **Step 1: Viết test đỏ**

```python
"""tests/test_5508_thumbnail_generation.py."""
from __future__ import annotations

import io

import pytest
from PIL import Image


@pytest.fixture()
def storage(tmp_path):
    import platform_core.storage as storage_mod
    s = storage_mod.LocalStorage(str(tmp_path / "files"))
    yield s


def _png_bytes(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 50, 50)).save(buf, format="PNG")
    return buf.getvalue()


def test_thumbnail_is_stored_under_a_different_key_and_fits_the_box(storage):
    from apps.prompt_ai_ommi.services import upload_zip
    original_key = "ommi/o1/r1/big.png"
    data = _png_bytes(1600, 900)
    storage.put(original_key, io.BytesIO(data), content_type="image/png")

    thumb_key = upload_zip.make_thumbnail(storage, original_key=original_key,
                                          data=data)

    assert thumb_key != original_key
    assert thumb_key.endswith("__thumb.jpg")
    assert storage.exists(original_key)
    assert storage.exists(thumb_key)

    with storage.open(original_key) as fh:
        original_still_full_size = Image.open(fh)
        original_still_full_size.load()
        assert original_still_full_size.size == (1600, 900)

    with storage.open(thumb_key) as fh:
        thumb = Image.open(fh)
        thumb.load()
        assert thumb.width <= 320 and thumb.height <= 320
        assert thumb.format == "JPEG"
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5508_thumbnail_generation.py -v`
Expected: FAIL — `make_thumbnail` chưa tồn tại.

- [ ] **Step 3: Thêm `make_thumbnail` vào `services/upload_zip.py`**

```python
THUMB_MAX_PX = 320
THUMB_JPEG_QUALITY = 82


def _thumb_key_for(original_key: str) -> str:
    base = original_key.rsplit(".", 1)[0]
    return f"{base}__thumb.jpg"


def make_thumbnail(storage, *, original_key: str, data: bytes) -> str:
    """Sinh thumbnail JPEG, khung tối đa 320x320, lưu ở khoá RIÊNG.

    ⛔ Không bao giờ ghi đè `original_key`: ảnh gốc là thứ khách tải lên và có
    quyền tải lại nguyên vẹn; thumbnail chỉ để hiển thị nhanh trong lưới kho.
    """
    import io as _io
    from PIL import Image

    image = Image.open(_io.BytesIO(data))
    image = image.convert("RGB")
    image.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
    out = _io.BytesIO()
    image.save(out, format="JPEG", quality=THUMB_JPEG_QUALITY)
    out.seek(0)

    thumb_key = _thumb_key_for(original_key)
    storage.put(thumb_key, out, content_type="image/jpeg")
    return thumb_key
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5508_thumbnail_generation.py -v`
Expected: PASS.

- [ ] **Step 5: Nối vào `_handle_import_zip`**

Trong `_handle_import_zip` (Task 5, Step 10), ngay sau dòng
`storage.put(key, io.BytesIO(entry.data), ...)`, thêm:

```python
            from apps.prompt_ai_ommi.services.upload_zip import make_thumbnail
            thumb_key = make_thumbnail(storage, original_key=key, data=entry.data)
```

và truyền `thumb_key=thumb_key` vào lời gọi `rsvc.add_variant(...)` ngay sau
đó.

- [ ] **Step 6: Chạy lại `test_5505_upload_zip_job_dedupe.py`, xác nhận vẫn XANH**

Run: `pytest tests/test_5505_upload_zip_job_dedupe.py tests/test_5508_thumbnail_generation.py -v`
Expected: PASS toàn bộ.

- [ ] **Step 7: Commit**

```bash
git add apps/prompt_ai_ommi/services/upload_zip.py apps/prompt_ai_ommi/jobs.py tests/test_5508_thumbnail_generation.py
git commit -m "$(cat <<'EOF'
feat(pha5): thumbnail Pillow 320x320 o khoa rieng, khong ghi de anh goc

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7 (Làn H): Bulk ops trên variant

**Files:**
- Modify: `apps/prompt_ai_ommi/services/resources.py` (thêm hàm `bulk_update`
  sau `remove_variant`, dòng ~287)
- Modify: `apps/prompt_ai_ommi/routes/resources.py` (thêm endpoint sau phần
  Task 5/6)
- Test: `tests/test_5506_bulk_variant_ops.py`

**Interfaces:**
- Consumes: `OmmiResourceVariant` (Task 2); `resources.get_owned`;
  `thung_rac.delete_resource` (không dùng ở đây — bulk delete xoá VARIANT,
  không xoá cả resource, nên đi qua `remove_variant` đã có, không qua thùng
  rác: variant không có snapshot riêng trong thùng rác ở pha 5 này, chỉ
  resource có — ghi rõ giới hạn này trong docstring).
- Produces:
  - `bulk_update(db, *, resource_id: str, owner_id: str, action: str, ids: list[str], value=None) -> dict`
  - `POST /api/resources/{resource_id}/variants/bulk`

- [ ] **Step 1: Viết test đỏ**

```python
"""tests/test_5506_bulk_variant_ops.py."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bulk.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def _setup(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r = rsvc.create(db_session, owner_id="alice", kind="prop", name="X")
    v1 = rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                          storage_key="k1")
    v2 = rsvc.add_variant(db_session, resource_id=r.id, owner_id="alice",
                          storage_key="k2")
    db_session.commit()
    return r, v1, v2


def test_bulk_favorite_sets_the_flag_on_every_selected_id(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, v2 = _setup(db_session)
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="favorite", ids=[v1.id, v2.id], value=True)
    db_session.commit()
    assert result["updated"] == 2
    assert db_session.get(type(v1), v1.id).favorite is True
    assert db_session.get(type(v2), v2.id).favorite is True


def test_bulk_rating_rejects_out_of_range_values(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, _v2 = _setup(db_session)
    with pytest.raises(rsvc.ResourceError):
        rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                         action="rating", ids=[v1.id], value=6)


def test_bulk_delete_removes_the_variants(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, v2 = _setup(db_session)
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="delete", ids=[v1.id])
    db_session.commit()
    assert result["updated"] == 1
    assert db_session.get(type(v1), v1.id) is None
    assert db_session.get(type(v2), v2.id) is not None


def test_bulk_ignores_ids_belonging_to_someone_else(db_session):
    from apps.prompt_ai_ommi.services import resources as rsvc
    r, v1, _v2 = _setup(db_session)
    other = rsvc.create(db_session, owner_id="mallory", kind="prop", name="Y")
    stolen = rsvc.add_variant(db_session, resource_id=other.id, owner_id="mallory",
                              storage_key="kx")
    db_session.commit()
    result = rsvc.bulk_update(db_session, resource_id=r.id, owner_id="alice",
                              action="favorite", ids=[v1.id, stolen.id], value=True)
    assert result["updated"] == 1
    assert db_session.get(type(stolen), stolen.id).favorite is False
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5506_bulk_variant_ops.py -v`
Expected: FAIL — `bulk_update` chưa tồn tại.

- [ ] **Step 3: Viết `bulk_update` trong `services/resources.py`**

Thêm sau hàm `remove_variant` (dòng ~287):

```python
_BULK_ACTIONS = {"favorite", "rating", "delete", "rename"}


def bulk_update(db: Session, *, resource_id: str, owner_id: str, action: str,
                ids: list, value=None) -> dict:
    """Áp một hành động lên nhiều variant CỦA CÙNG MỘT resource.

    Mỗi id được kiểm `owner_id` NGAY TẠI ĐÂY (không chỉ qua `resource_id`):
    một id thuộc resource của người khác vô tình lọt vào body sẽ bị BỎ QUA,
    không được đếm vào `updated` — không ném lỗi, vì đây là dọn dẹp hàng loạt,
    một id lạ không nên làm hỏng cả lượt.
    """
    if action not in _BULK_ACTIONS:
        raise ResourceError(f"Hành động không hợp lệ: {action!r}.")
    get_owned(db, resource_id, owner_id)   # xác nhận resource là của người gọi

    rows = list(db.execute(
        select(OmmiResourceVariant)
        .where(OmmiResourceVariant.id.in_([str(i) for i in (ids or [])[:200]]),
               OmmiResourceVariant.resource_id == resource_id,
               OmmiResourceVariant.owner_id == owner_id)
    ).scalars().all())

    updated = 0
    if action == "favorite":
        flag = bool(value)
        for row in rows:
            row.favorite = flag
            updated += 1
    elif action == "rating":
        rating = value
        if rating is not None and not (1 <= int(rating) <= 5):
            raise ResourceError("Đánh giá phải từ 1 đến 5.")
        for row in rows:
            row.rating = int(rating) if rating is not None else None
            updated += 1
    elif action == "rename":
        label = _clean_text(str(value or ""), 160)
        for row in rows:
            row.label = label
            updated += 1
    elif action == "delete":
        for row in rows:
            db.delete(row)
            updated += 1
    db.flush()
    return {"updated": updated}
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5506_bulk_variant_ops.py -v`
Expected: PASS cả bốn test.

- [ ] **Step 5: Thêm endpoint**

Trong `apps/prompt_ai_ommi/routes/resources.py`:

```python
@router.post("/api/resources/{resource_id}/variants/bulk")
async def bulk_variant_update(request: Request, resource_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        result = rsvc.bulk_update(
            db, resource_id=resource_id, owner_id=user.id,
            action=str(body.get("action") or ""),
            ids=body.get("ids") or [], value=body.get("value"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return result
```

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/services/resources.py apps/prompt_ai_ommi/routes/resources.py tests/test_5506_bulk_variant_ops.py
git commit -m "$(cat <<'EOF'
feat(pha5): bulk ops tren variant (favorite/rating/rename/delete), loc theo owner

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8 (Làn H): Endpoint thùng rác

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/resources.py` (thêm endpoint sau Task 7)
- Test: `tests/test_5507_trash_routes_api.py`

**Interfaces:**
- Consumes: `thung_rac.delete_resource/restore/list_trash` (Task 4).
- Produces: `GET /api/trash`, `POST /api/trash/{id}/restore`,
  `DELETE /api/trash/{id}`, và `POST /api/resources/{resource_id}/delete`
  (route gọi `thung_rac.delete_resource` — chưa có endpoint xoá hẳn trước
  pha 5; `archive_resource` đã có chỉ đặt `archived_at`, không đưa vào
  thùng rác).

- [ ] **Step 1: Viết test đỏ**

```python
"""tests/test_5507_trash_routes_api.py."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trash-api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="trash-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 100, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-trash-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "trash-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_delete_then_list_then_restore(api):
    client, token = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "Kiem"})
    rid = made.json()["id"]

    deleted = client.post(f"/prompt-ai-ommi/api/resources/{rid}/delete",
                          headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200, deleted.text
    trash_id = deleted.json()["trash_id"]

    listed = client.get("/prompt-ai-ommi/api/trash")
    assert listed.status_code == 200
    assert any(item["id"] == trash_id for item in listed.json()["items"])

    restored = client.post(f"/prompt-ai-ommi/api/trash/{trash_id}/restore",
                           headers={"X-CSRF-Token": token})
    assert restored.status_code == 200, restored.text
    assert restored.json()["id"] == rid

    again = client.get(f"/prompt-ai-ommi/api/resources/{rid}")
    assert again.status_code == 200
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5507_trash_routes_api.py -v`
Expected: FAIL — endpoint chưa tồn tại (404).

- [ ] **Step 3: Thêm endpoint**

```python
@router.post("/api/resources/{resource_id}/delete")
async def delete_resource_to_trash(request: Request, resource_id: str,
                                   _identity: str = Depends(require_login),
                                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import thung_rac
    _csrf(request); user = _user(request)
    try:
        trash = thung_rac.delete_resource(db, resource_id=resource_id,
                                          owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return {"trash_id": trash.id, "purge_after": trash.purge_after.isoformat()}


@router.get("/api/trash")
def list_trash(request: Request, _identity: str = Depends(require_login),
              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import thung_rac
    user = _user(request)
    rows = thung_rac.list_trash(db, owner_id=user.id)
    return {"items": [{"id": r.id, "target_kind": r.target_kind,
                       "target_id": r.target_id,
                       "deleted_at": r.deleted_at.isoformat(),
                       "purge_after": r.purge_after.isoformat()}
                      for r in rows]}


@router.post("/api/trash/{trash_id}/restore")
async def restore_trash(request: Request, trash_id: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import thung_rac
    _csrf(request); user = _user(request)
    try:
        restored = thung_rac.restore(db, trash_id=trash_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(restored)


@router.delete("/api/trash/{trash_id}")
async def purge_one_trash_item(request: Request, trash_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    """Purge THỦ CÔNG một vé — khách bấm "xoá vĩnh viễn" trước hạn."""
    from datetime import datetime, timezone
    from apps.prompt_ai_ommi.services import thung_rac
    from apps.prompt_ai_ommi.tables import OmmiTrash
    from platform_core.storage import get_storage
    _csrf(request); user = _user(request)
    row = db.get(OmmiTrash, trash_id)
    if row is None or row.owner_id != user.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy vé thùng rác.'))
    row.purge_after = datetime.now(timezone.utc)
    db.flush()
    result = thung_rac.purge_expired(db, storage=get_storage())
    db.commit()
    return result
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5507_trash_routes_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/routes/resources.py tests/test_5507_trash_routes_api.py
git commit -m "$(cat <<'EOF'
feat(pha5): endpoint thung rac — xoa/liet ke/phuc hoi/purge thu cong

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9 (Làn I): `services/composite.py` — sinh ảnh composite

**Files:**
- Create: `apps/prompt_ai_ommi/services/composite.py`
- Test: `tests/test_5530_composite_generate_quote_confirm.py`,
  `tests/test_5531_composite_version_revert_retry.py`

**Interfaces:**
- Consumes (bảng do pha 4 tạo, cột dùng đúng theo brief giao việc):
  `ommi_image_template.prompt_text: str`, `.n_outputs: int`, `.aspect: str`,
  `.asset_type: str`, `.requires_ref: bool`, `.multi_ref_max: int`,
  `.negative_lock: str`; `OmmiImageJob` (Task 2);
  `apps.prompt_ai_ommi.services.resources.get_owned/add_variant`;
  `platform_core.job_submit.submit_with_credit`,
  `platform_core.job_submit.dedupe_key_for`; `platform_core.registry.credit_for`.
- Produces:
  - `quote(db, *, template, resource_id: str, owner_id: str, reference_variant_ids: list[str]) -> dict`
  - `generate(db, *, template, resource_id: str, owner_id: str, reference_variant_ids: list[str], confirmed: bool, app_slug: str) -> dict`
  - `revert(db, *, image_job_id: str, owner_id: str) -> "OmmiImageJob"`
  - `retry(db, *, image_job_id: str, owner_id: str, app_slug: str) -> dict`

⚠️ Vì `ommi_image_template` là bảng của pha 4 chưa tồn tại trong nhánh này,
task dùng một **stub tối thiểu** (`SimpleNamespace` hoặc một lớp giả trong
test) mang đúng bảy thuộc tính liệt kê ở "Consumes" — khi pha 4 đã merge thật,
thay `template` bằng instance ORM thật; chữ ký hàm không đổi vì `composite.py`
chỉ đọc thuộc tính, không import `OmmiImageTemplate` trực tiếp (tránh phụ
thuộc cứng vào một bảng có thể còn đang được lane G của pha 4 định hình).

- [ ] **Step 1: Viết test đỏ**

```python
"""tests/test_5530_composite_generate_quote_confirm.py."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _template(**over):
    base = dict(id="tpl1", prompt_text="Ve {NAME} dung {ASSET_TYPE}",
               n_outputs=2, aspect="1:1", asset_type="character",
               requires_ref=True, multi_ref_max=2, negative_lock="khong mau")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'composite.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="composite-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")
    db.commit()
    yield db, user.id
    db.close()
    dbmod.reset_engine()


def test_quote_never_creates_a_job(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    db.commit()

    result = composite.quote(db, template=_template(), resource_id=resource.id,
                            owner_id=owner_id, reference_variant_ids=[])
    assert result["credit"] > 0

    from platform_core.models import Job
    assert db.query(Job).filter(Job.user_id == owner_id).count() == 0


def test_confirmed_generate_submits_taoanh_job_and_records_image_job(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner_id,
                               storage_key="k1")
    db.commit()

    result = composite.generate(
        db, template=_template(), resource_id=resource.id, owner_id=owner_id,
        reference_variant_ids=[variant.id], confirmed=True,
        app_slug="prompt_ai_ommi")
    db.commit()

    from platform_core.models import Job
    job = db.query(Job).filter(Job.user_id == owner_id).one()
    assert job.job_type == "taoanh.generate"
    assert job.params["image_keys"] == ["k1"]

    from apps.prompt_ai_ommi.tables import OmmiImageJob
    image_job = db.get(OmmiImageJob, result["image_job_id"])
    assert image_job.version == 1
    assert image_job.parent_id is None
    assert image_job.template_id == "tpl1"


def test_requires_ref_template_rejects_generation_without_any_reference(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    db.commit()
    with pytest.raises(ValueError, match="anh tham chieu"):
        composite.generate(db, template=_template(requires_ref=True),
                           resource_id=resource.id, owner_id=owner_id,
                           reference_variant_ids=[], confirmed=True,
                           app_slug="prompt_ai_ommi")
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5530_composite_generate_quote_confirm.py -v`
Expected: FAIL — `apps.prompt_ai_ommi.services.composite` chưa tồn tại.

- [ ] **Step 3: Viết `services/composite.py`**

```python
"""composite.py — sinh anh composite theo ommi_image_template (pha 5).

OMMI khong dung engine rieng: dieu phoi (chon anh tham chieu, ghep prompt tu
mau) nam o day, loi goi provider di qua job `taoanh.generate` da co tu pha 1
— dung mau voi `resources.generate_resource_image` (xem
`apps/prompt_ai_ommi/routes/resources.py:444-487`).

`OmmiImageJob` khong PHAI la job cua nen tang (`platform_core.models.Job`) —
no la SO THEO DOI cua OMMI, tro toi job that qua `job_id`, va giu them
`version`/`parent_id` de lam duoc "quay lai ban truoc"/"thu lai" ma ban than
`Job` khong khai niem nao co san cho.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services import resources as rsvc
from apps.prompt_ai_ommi.tables import OmmiImageJob

_IMAGE_JOB_TYPE = "taoanh.generate"


def _reference_keys(db, *, resource_id: str, owner_id: str,
                    template, reference_variant_ids: list) -> list:
    wanted = {str(v) for v in (reference_variant_ids or [])[:template.multi_ref_max] if v}
    keys = []
    for variant in rsvc.variants(db, resource_id, owner_id):
        if variant.id in wanted:
            keys.append(variant.storage_key)
    if template.requires_ref and not keys:
        raise ValueError("Mẫu này cần ít nhất một anh tham chieu.")
    return keys


def _build_prompt(template, resource) -> str:
    return (template.prompt_text
            .replace("{NAME}", resource.name)
            .replace("{ASSET_TYPE}", template.asset_type))


def _params(db, *, template, resource_id: str, owner_id: str,
           reference_variant_ids: list) -> dict:
    resource = rsvc.get_owned(db, resource_id, owner_id)
    keys = _reference_keys(db, resource_id=resource_id, owner_id=owner_id,
                           template=template,
                           reference_variant_ids=reference_variant_ids)
    prompt = _build_prompt(template, resource)
    if template.negative_lock:
        prompt = f"{prompt}\n\nKHONG: {template.negative_lock}"
    params = {"prompt": prompt[:4000], "aspect_ratio": template.aspect,
             "count": max(1, min(4, int(template.n_outputs))),
             "owner_id": owner_id}
    if keys:
        params["image_keys"] = keys
    return params


def quote(db, *, template, resource_id: str, owner_id: str,
         reference_variant_ids: list) -> dict:
    """Báo giá — KHÔNG tạo job, KHÔNG tạo `OmmiImageJob`."""
    from platform_core.registry import credit_for
    params = _params(db, template=template, resource_id=resource_id,
                    owner_id=owner_id, reference_variant_ids=reference_variant_ids)
    return {"credit": int(credit_for(_IMAGE_JOB_TYPE, params)),
           "count": params["count"]}


def generate(db, *, template, resource_id: str, owner_id: str,
            reference_variant_ids: list, confirmed: bool,
            app_slug: str) -> dict:
    """Báo giá khi `confirmed=False`; nộp job + ghi `OmmiImageJob` khi
    `confirmed=True`. Cùng công thức giá ở cả hai nhánh — tách đôi là mở
    đường cho hai công thức lệch nhau (bài học ở `resources.py`).
    """
    params = _params(db, template=template, resource_id=resource_id,
                    owner_id=owner_id, reference_variant_ids=reference_variant_ids)
    from platform_core.registry import credit_for
    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not confirmed:
        return {"credit": estimate, "count": params["count"], "confirmed": False}

    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    job = submit_with_credit(
        db, user_id=owner_id, app_slug=app_slug, job_type=_IMAGE_JOB_TYPE,
        params=params, dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))
    image_job = OmmiImageJob(owner_id=owner_id, template_id=template.id,
                            resource_id=resource_id, params=params,
                            job_id=job.id, version=1, parent_id=None,
                            status="queued")
    db.add(image_job)
    db.flush()
    return {"credit": estimate, "confirmed": True, "job_id": job.id,
           "image_job_id": image_job.id}


def revert(db, *, image_job_id: str, owner_id: str) -> OmmiImageJob:
    """Đánh dấu một lượt sinh là 'reverted' — variant đã gắn (nếu có) KHÔNG bị
    xoá ở đây; xoá variant là việc của thùng rác/bulk-delete, việc của hàm này
    chỉ là dừng coi lượt này là bản hiện hành.
    """
    row = db.get(OmmiImageJob, image_job_id)
    if row is None or row.owner_id != owner_id:
        raise rsvc.ResourceNotFound("Không tìm thấy lượt sinh ảnh.")
    row.status = "reverted"
    db.flush()
    return row


def retry(db, *, image_job_id: str, owner_id: str, app_slug: str) -> dict:
    """Nộp lại CÙNG tham số, `version = cha.version + 1`, `parent_id = cha.id`."""
    parent = db.get(OmmiImageJob, image_job_id)
    if parent is None or parent.owner_id != owner_id:
        raise rsvc.ResourceNotFound("Không tìm thấy lượt sinh ảnh.")
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    job = submit_with_credit(
        db, user_id=owner_id, app_slug=app_slug, job_type=_IMAGE_JOB_TYPE,
        params=parent.params,
        dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE,
                                  {**parent.params, "_retry_of": parent.id}))
    child = OmmiImageJob(owner_id=owner_id, template_id=parent.template_id,
                        resource_id=parent.resource_id, params=parent.params,
                        job_id=job.id, version=parent.version + 1,
                        parent_id=parent.id, status="queued")
    db.add(child)
    db.flush()
    return {"job_id": job.id, "image_job_id": child.id, "version": child.version}
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5530_composite_generate_quote_confirm.py -v`
Expected: PASS cả ba test.

- [ ] **Step 5: Viết test đỏ cho version/revert/retry**

```python
"""tests/test_5531_composite_version_revert_retry.py."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _template():
    return SimpleNamespace(id="tpl1", prompt_text="Ve {NAME}", n_outputs=1,
                          aspect="1:1", asset_type="prop", requires_ref=False,
                          multi_ref_max=1, negative_lock="")


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'composite-retry.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="retry-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")
    db.commit()
    yield db, user.id
    db.close()
    dbmod.reset_engine()


def test_retry_creates_a_new_version_linked_to_its_parent(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    first = composite.generate(db, template=_template(), resource_id=resource.id,
                              owner_id=owner_id, reference_variant_ids=[],
                              confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()

    retried = composite.retry(db, image_job_id=first["image_job_id"],
                              owner_id=owner_id, app_slug="prompt_ai_ommi")
    db.commit()

    assert retried["version"] == 2
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    child = db.get(OmmiImageJob, retried["image_job_id"])
    assert child.parent_id == first["image_job_id"]


def test_revert_marks_the_image_job_as_reverted(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    made = composite.generate(db, template=_template(), resource_id=resource.id,
                             owner_id=owner_id, reference_variant_ids=[],
                             confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    composite.revert(db, image_job_id=made["image_job_id"], owner_id=owner_id)
    db.commit()

    from apps.prompt_ai_ommi.tables import OmmiImageJob
    assert db.get(OmmiImageJob, made["image_job_id"]).status == "reverted"


def test_retry_of_someone_elses_image_job_is_rejected(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    made = composite.generate(db, template=_template(), resource_id=resource.id,
                             owner_id=owner_id, reference_variant_ids=[],
                             confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    with pytest.raises(rsvc.ResourceNotFound):
        composite.retry(db, image_job_id=made["image_job_id"],
                        owner_id="mallory", app_slug="prompt_ai_ommi")
```

- [ ] **Step 6: Chạy test, xác nhận ĐỎ rồi XANH**

Run: `pytest tests/test_5531_composite_version_revert_retry.py -v`
Expected: PASS ngay (implementation đã có từ Step 3) — nếu FAIL, đọc lỗi và
sửa `composite.py` cho khớp; không sửa test để né lỗi.

- [ ] **Step 7: Commit**

```bash
git add apps/prompt_ai_ommi/services/composite.py tests/test_5530_composite_generate_quote_confirm.py tests/test_5531_composite_version_revert_retry.py
git commit -m "$(cat <<'EOF'
feat(pha5): composite.py - sinh anh theo ommi_image_template, version/revert/retry

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10 (Làn I): `services/breakdown.py` — chia cảnh tự động

**Files:**
- Create: `apps/prompt_ai_ommi/services/breakdown.py`
- Test: `tests/test_5532_breakdown_scene_count_matches_default.py`,
  `tests/test_5533_breakdown_uses_framework_prompt.py`

**Interfaces:**
- Consumes (bảng do pha 4 tạo, cột dùng đúng theo brief giao việc):
  `ommi_storyboard_framework.composite_header: str`,
  `.composite_rules: str`, `.composite_negative_footer: str`,
  `.breakdown_llm_prompt: str`, `.default_n_scenes: int`;
  `apps.prompt_ai_ommi.provider.generate_json(system: str, prompt: str, *,
  model: str) -> tuple[dict, int]`, `apps.prompt_ai_ommi.provider.model_mac_dinh() -> str`.
- Produces: `breakdown(db, *, framework, story_vi: str, n_scenes: int | None = None,
  model: str = "") -> list[dict]` — trả **đúng** `n_scenes` (hoặc
  `framework.default_n_scenes` nếu không truyền) phần tử, mỗi phần tử
  `{"title": str, "prompt": str}`.

⚠️ Bài học `sai-so-nho-o-nhip-thanh-sai-so-lon-o-nguong`: model có thể trả
thiếu/thừa cảnh so với số yêu cầu. `breakdown()` PHẢI tự cắt/bù cho khớp
CHÍNH XÁC số yêu cầu — không được trả "xấp xỉ đúng".

- [ ] **Step 1: Viết test đỏ (test bắt buộc theo brief)**

```python
"""tests/test_5532_breakdown_scene_count_matches_default.py."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _framework(**over):
    base = dict(composite_header="TIEU DE", composite_rules="LUAT",
               composite_negative_footer="KHONG", default_n_scenes=5,
               breakdown_llm_prompt="Chia cau chuyen sau thanh {N} canh: {STORY}")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'breakdown.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_returned_scene_count_matches_default_n_scenes_when_llm_gives_too_few(db_session):
    """Model tra thieu 2 canh so voi default_n_scenes=5 — dau ra VAN phai la 5."""
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=5)
    fake_raw = {"scenes": [{"title": "Canh 1", "prompt": "p1"},
                           {"title": "Canh 2", "prompt": "p2"},
                           {"title": "Canh 3", "prompt": "p3"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai")
    assert len(scenes) == 5


def test_returned_scene_count_matches_default_n_scenes_when_llm_gives_too_many(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=3)
    fake_raw = {"scenes": [{"title": f"Canh {i}", "prompt": f"p{i}"}
                          for i in range(1, 8)]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai")
    assert len(scenes) == 3


def test_explicit_n_scenes_overrides_the_framework_default(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=5)
    fake_raw = {"scenes": [{"title": f"Canh {i}", "prompt": f"p{i}"}
                          for i in range(1, 3)]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai", n_scenes=8)
    assert len(scenes) == 8
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5532_breakdown_scene_count_matches_default.py -v`
Expected: FAIL — `apps.prompt_ai_ommi.services.breakdown` chưa tồn tại.

- [ ] **Step 3: Viết `services/breakdown.py`**

```python
"""breakdown.py — chia canh tu dong theo ommi_storyboard_framework (pha 5).

⚠️ BAI HOC `sai-so-nho-o-nhip-thanh-sai-so-lon-o-nguong`: mot lech nho o NHIP
(vi du prompt xin "5 canh" nhung LLM hieu thanh khoang 5) tro thanh lech LON o
NGUONG khi khach dem SO CANH tra ve. Vi vay ham nay khong "co gang xin dung so
canh roi tin LLM" — no ep dung SO LUONG o tang HAU KY, bang cach cat bot hoac
bu them canh placeholder trung thuc (khong bia noi dung gia).
"""
from __future__ import annotations

from apps.prompt_ai_ommi import provider


def _system_prompt(framework) -> str:
    return "\n\n".join(filter(None, [
        framework.composite_header, framework.composite_rules,
        framework.composite_negative_footer]))


def _clean_scene(raw: dict, index: int) -> dict:
    title = str((raw or {}).get("title") or f"Cảnh {index + 1}")[:200]
    prompt = str((raw or {}).get("prompt") or "")[:4000]
    return {"title": title, "prompt": prompt}


def breakdown(db, *, framework, story_vi: str, n_scenes: int | None = None,
             model: str = "") -> list:
    """Chia `story_vi` thành ĐÚNG `n_scenes` (hoặc `framework.default_n_scenes`
    nếu không truyền) cảnh. Số cảnh trả về KHÔNG BAO GIỜ lệch so yêu cầu.
    """
    target = int(n_scenes) if n_scenes is not None else int(framework.default_n_scenes)
    target = max(1, min(20, target))

    system = _system_prompt(framework)
    prompt = framework.breakdown_llm_prompt.replace(
        "{N}", str(target)).replace("{STORY}", story_vi)
    chosen_model = model or provider.model_mac_dinh()
    raw, _tokens = provider.generate_json(system, prompt, model=chosen_model)

    raw_scenes = list((raw or {}).get("scenes") or [])
    scenes = [_clean_scene(item, i) for i, item in enumerate(raw_scenes[:target])]
    while len(scenes) < target:
        scenes.append(_clean_scene({
            "title": f"Cảnh {len(scenes) + 1}",
            "prompt": "Cảnh chưa được AI tạo; cần chỉnh hoặc chia lại.",
        }, len(scenes)))
    assert len(scenes) == target
    return scenes
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5532_breakdown_scene_count_matches_default.py -v`
Expected: PASS cả ba test.

- [ ] **Step 5: Viết test đỏ xác nhận prompt được dựng từ đúng cột framework**

```python
"""tests/test_5533_breakdown_uses_framework_prompt.py."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'breakdown2.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_system_prompt_is_built_from_composite_header_rules_and_footer(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = SimpleNamespace(
        composite_header="TIEU DE X", composite_rules="LUAT Y",
        composite_negative_footer="KHONG Z", default_n_scenes=2,
        breakdown_llm_prompt="Chia {STORY} thanh {N} canh")

    captured = {}

    def _fake_generate_json(system, prompt, *, model):
        captured["system"] = system
        captured["prompt"] = prompt
        return {"scenes": [{"title": "A", "prompt": "pa"},
                           {"title": "B", "prompt": "pb"}]}, 10

    with patch("apps.prompt_ai_ommi.provider.generate_json",
              side_effect=_fake_generate_json), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        bsvc.breakdown(db_session, framework=framework, story_vi="cau chuyen ABC")

    assert "TIEU DE X" in captured["system"]
    assert "LUAT Y" in captured["system"]
    assert "KHONG Z" in captured["system"]
    assert "cau chuyen ABC" in captured["prompt"]
    assert "2" in captured["prompt"]
```

- [ ] **Step 6: Chạy test, xác nhận XANH (không cần sửa `breakdown.py`)**

Run: `pytest tests/test_5533_breakdown_uses_framework_prompt.py -v`
Expected: PASS — nếu FAIL vì `_system_prompt`/thay thế `{STORY}`/`{N}` không
khớp, sửa `breakdown.py` cho đúng rồi chạy lại.

- [ ] **Step 7: Commit**

```bash
git add apps/prompt_ai_ommi/services/breakdown.py tests/test_5532_breakdown_scene_count_matches_default.py tests/test_5533_breakdown_uses_framework_prompt.py
git commit -m "$(cat <<'EOF'
feat(pha5): breakdown.py - chia canh tu dong, so canh luon dung yeu cau

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11 (Làn I): Nối route — `/api/image-templates/{tid}/generate` và `/api/storyboards/{sid}/breakdown`

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/library.py` (thêm endpoint cuối tệp,
  sau dòng 211 hiện tại — hình dạng tệp có thể khác sau pha 4, thêm vào cuối
  tệp lúc thi hành)
- Modify: `apps/prompt_ai_ommi/routes/storyboard.py` (thêm endpoint cuối tệp,
  sau dòng 309 hiện tại)
- Test: `tests/test_5534_image_template_generate_route.py`,
  `tests/test_5535_storyboard_breakdown_route.py`

⚠️ Cả hai endpoint đọc một hàng `ommi_image_template`/`ommi_storyboard_framework`
theo `id` từ URL. Vì bảng đó thuộc pha 4, task này viết truy vấn generic
(`db.get(...)`) và import tên lớp từ `apps.prompt_ai_ommi.tables` — nếu lớp đó
chưa tồn tại lúc thi hành (pha 4 chưa merge), dừng Task 11 và báo, không tự
suy đoán hình dạng bảng.

**Interfaces:**
- Consumes: `composite.quote/generate` (Task 9); `breakdown.breakdown`
  (Task 10); `apps.prompt_ai_ommi.tables.OmmiImageTemplate`,
  `OmmiStoryboardFramework` (pha 4).
- Produces: `POST /api/image-templates/{tid}/generate`,
  `POST /api/storyboards/{sid}/breakdown`.

- [ ] **Step 1: Viết test đỏ cho route composite**

```python
"""tests/test_5534_image_template_generate_route.py."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tpl-route.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="tpl-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")

    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    tpl = OmmiImageTemplate(name="Mau X", prompt_text="Ve {NAME}", n_outputs=1,
                           aspect="1:1", asset_type="prop", requires_ref=False,
                           multi_ref_max=1, negative_lock="", is_builtin=True)
    db.add(tpl); db.commit()
    tpl_id = tpl.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-tpl-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "tpl-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, tpl_id
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_generate_from_template_quotes_then_confirms(api):
    client, token, tpl_id = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "A"})
    rid = made.json()["id"]

    quoted = client.post(f"/prompt-ai-ommi/api/image-templates/{tpl_id}/generate",
                        headers={"X-CSRF-Token": token},
                        json={"resource_id": rid})
    assert quoted.status_code == 200
    assert quoted.json()["confirmed"] is False

    started = client.post(f"/prompt-ai-ommi/api/image-templates/{tpl_id}/generate",
                         headers={"X-CSRF-Token": token},
                         json={"resource_id": rid, "confirmed": True})
    assert started.status_code == 200, started.text
    assert started.json()["confirmed"] is True
```

- [ ] **Step 2: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5534_image_template_generate_route.py -v`
Expected: FAIL — endpoint chưa tồn tại (404) hoặc `OmmiImageTemplate` chưa có
(nếu pha 4 chưa merge — dừng và báo theo cảnh báo ở đầu Task 11).

- [ ] **Step 3: Thêm endpoint vào `routes/library.py`**

```python
@router.post("/api/image-templates/{template_id}/generate")
async def generate_from_image_template(request: Request, template_id: str,
                                       _identity: str = Depends(require_login),
                                       db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import composite
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    body = await request.json(); _csrf(request, body); user = _user(request)

    template = db.get(OmmiImageTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy mẫu.'))

    try:
        result = composite.generate(
            db, template=template, resource_id=str(body.get("resource_id") or ""),
            owner_id=user.id,
            reference_variant_ids=body.get("reference_variant_ids") or [],
            confirmed=bool(body.get("confirmed")), app_slug=MANIFEST.slug)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return result
```

- [ ] **Step 4: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5534_image_template_generate_route.py -v`
Expected: PASS.

- [ ] **Step 5: Viết test đỏ cho route breakdown**

```python
"""tests/test_5535_storyboard_breakdown_route.py."""
from __future__ import annotations

import json
import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sb-route.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="sb-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")

    from apps.prompt_ai_ommi.tables import OmmiStoryboard, OmmiStoryboardFramework
    framework = OmmiStoryboardFramework(
        name="Khung X", composite_header="TD", composite_rules="LU",
        composite_negative_footer="KH", default_n_scenes=4,
        breakdown_llm_prompt="Chia {STORY} thanh {N} canh", is_builtin=True)
    db.add(framework); db.flush()
    storyboard = OmmiStoryboard(owner_id=user.id, title="SB", story="cau chuyen")
    db.add(storyboard); db.commit()
    framework_id = framework.id
    storyboard_id = storyboard.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-sb-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "sb-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, storyboard_id, framework_id
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_breakdown_route_returns_default_n_scenes(api):
    client, token, sid, fid = api
    fake_raw = {"scenes": [{"title": "A", "prompt": "pa"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 5)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        resp = client.post(
            f"/prompt-ai-ommi/api/storyboards/{sid}/breakdown",
            headers={"X-CSRF-Token": token}, json={"framework_id": fid})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["scenes"]) == 4
```

- [ ] **Step 6: Chạy test, xác nhận ĐỎ**

Run: `pytest tests/test_5535_storyboard_breakdown_route.py -v`
Expected: FAIL — endpoint chưa tồn tại, hoặc `OmmiStoryboardFramework` chưa
có (dừng và báo nếu pha 4 chưa merge).

- [ ] **Step 7: Thêm endpoint vào `routes/storyboard.py`**

```python
@router.post("/api/storyboards/{storyboard_id}/breakdown")
async def breakdown_storyboard(request: Request, storyboard_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    body = await request.json(); _csrf(request, body); user = _user(request)

    story = ssvc.get_owned_storyboard(db, storyboard_id, user.id)
    framework = db.get(OmmiStoryboardFramework, str(body.get("framework_id") or ""))
    if framework is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy khung.'))

    try:
        scenes = bsvc.breakdown(
            db, framework=framework, story_vi=story.story,
            n_scenes=body.get("n_scenes"))
    except Exception as exc:
        raise _storyboard_error(exc) from exc
    return {"scenes": scenes}
```

⚠️ `ssvc.get_owned_storyboard` là tên GIẢ ĐỊNH theo mẫu
`ssvc.get_owned_scene` đã thấy ở `routes/storyboard.py` hiện tại — kiểm tên
hàm thật trong `services/storyboard.py` lúc thi hành (có thể là
`get_owned_storyboard`/`get_owned`/tên khác tuỳ pha 3 đặt) và sửa lời gọi cho
khớp.

- [ ] **Step 8: Chạy test, xác nhận XANH**

Run: `pytest tests/test_5535_storyboard_breakdown_route.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/prompt_ai_ommi/routes/library.py apps/prompt_ai_ommi/routes/storyboard.py tests/test_5534_image_template_generate_route.py tests/test_5535_storyboard_breakdown_route.py
git commit -m "$(cat <<'EOF'
feat(pha5): noi route composite (image-templates) va breakdown (storyboards)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12 (Làn M): GATE — MỘT LẦN DUY NHẤT, cuối TOÀN BỘ 5 pha

⚠️ Task này **không phải** "gate của pha 5" — nó là gate của **toàn bộ kế
hoạch 5 pha** (spec §3: "Gate (L1 hoặc L2) chạy một lần duy nhất ở cuối pha
5"). Không chạy task này cho tới khi Task 1–11 của plan này VÀ mọi task của
pha 1–4 đều đã test-nhắm-xanh và gộp `main`.

**Files:** không tạo/sửa tệp mã — chỉ chạy công cụ và, nếu đỏ, sửa tại chỗ.

**Interfaces:** không có (task vận hành, không phải task viết mã).

- [ ] **Step 1: Xác nhận không còn pha nào dở**

Kiểm `docs/superpowers/plans/` cho các plan pha 1–4 (nếu đã có) — mọi task
của chúng phải ở trạng thái xong (test nhắm xanh, đã gộp `main`). Nếu còn dở,
DỪNG — không chạy gate khi còn việc chưa làm (spec §3: "hết một phase/task
KHÔNG phải cuối plan").

- [ ] **Step 2: Kiểm máy trước lệnh nặng (G-12)**

```
python tools\cua_so_yen.py trang-thai
python tools\tai_may.py
```

Có người giữ khoá hoặc `QUÁ TẢI` ⇒ chờ, không tự ý chạy song song.

- [ ] **Step 3: Chạy gate — CHỌN ĐÚNG MỘT CẤP**

L1 (toàn cây, so với điểm rẽ nhánh):

```
python tools\gate.py --doi
```

HOẶC L2 (phạm vi thành phần, nếu plan pha 1–5 chỉ chạm một vài thành phần
kín):

```
python tools\gate.py --pham-vi prompt_ai_ommi
```

⛔ Không chạy cả hai. Không chạy L3 riêng — spec đã bỏ khái niệm "L3 tổng kết
phiên" (chốt 25/09, xem `CLAUDE.md` gốc mục "CHỐT 25/09").

- [ ] **Step 4: Gate đỏ ⇒ sửa tại chỗ, chạy lại ĐÚNG lệnh gate in ra**

Gate in sẵn lệnh tái hiện đúng phép đỏ. Sửa xong, chạy lại đúng lệnh đó (không
chạy lại toàn bộ gate) cho tới khi xanh, rồi khép:

```
python tools\gate.py --doi --tu <sha_cua_luot_gate_vua_chay>
```

- [ ] **Step 5: Gate xanh ⇒ gộp `main`**

```bash
git status
```

Xác nhận không còn thay đổi chưa commit. Gộp theo quy trình worktree của dự
án (`docs/QUY_TRINH_WORKTREE.md`) — KHÔNG `git merge`/`git rebase` tuỳ tiện
nếu dự án dùng script gộp riêng; kiểm tài liệu đó trước khi gộp tay.

- [ ] **Step 6: Báo cáo, không xin duyệt thêm**

Ghi vào `docs/NHAT_KY.md` (luật chết người #— nhật ký sống): ngày, gate đã
chạy (L1/L2), sha, kết quả. Không dừng chờ xác nhận thêm — hợp đồng vận hành
quy định "xong phiên → báo, không xin duyệt".

---

## Tự soát

**1. Phủ spec:** đối chiếu từng mục pha 5 của spec §4.2/§5/§6.7/§9/§10/§12 với
task trong plan này —

| Spec | Task |
|---|---|
| §4.2 alter `ommi_resource_variant` + `ommi_trash` + `ommi_image_job` | Task 1, 2 |
| §9.2 lane H: dedupe/thùng rác/tables | Task 2, 3, 4 |
| §6.7 `variants/bulk` | Task 7 |
| §6.7 `upload-zip` | Task 5, 6 |
| §6.7 `GET/POST/DELETE /api/trash*` | Task 8 |
| §6.7 `image-templates/{tid}/generate` | Task 9, 11 |
| §6.7 `storyboards/{sid}/breakdown` | Task 10, 11 |
| §10.2 T-1..T-3 | Ngoài phạm vi pha 5 (thuộc pha 1/3) — không lặp lại ở đây |
| Bốn phép bắt buộc của brief giao việc (hai-khách/hai-lần/zip-slip/trash/breakdown) | Task 3 (hai-khách, hai-lần), Task 5 (zip-slip), Task 4 (trash), Task 10 (breakdown count) |
| Gate một lần cuối 5 pha | Task 12 |

**2. Quét placeholder:** không còn "TBD"/"tương tự Task N"/"xử lý lỗi phù
hợp" trong plan — mọi step viết mã có block Python thật. Hai chỗ CỐ Ý để
khoảng trống có ghi rõ lý do (không phải placeholder che giấu): `_db_for_ctx`
ở Task 5 Step 10 (phụ thuộc mẫu `get_session()` thật của `platform_core/db.py`
lúc thi hành) và tên hàm `ssvc.get_owned_storyboard` ở Task 11 Step 7 (phụ
thuộc API thật của `services/storyboard.py` sau pha 3).

**3. Nhất quán kiểu:** `add_variant(..., file_hash: str = "")` (Task 3) khớp
với lời gọi ở Task 5/6; `OmmiImageJob.version/parent_id` (Task 2) khớp với
`composite.generate/retry` (Task 9); `breakdown(db, *, framework, story_vi,
n_scenes=None, model="")` (Task 10) khớp với lời gọi ở route Task 11.
