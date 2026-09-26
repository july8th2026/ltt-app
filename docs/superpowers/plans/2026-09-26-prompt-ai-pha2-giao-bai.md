# PROMPT AI OMMI — Pha 2: Giao bài sang taovideo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khách bấm "Giao bài" trên một cảnh trong PROMPT AI OMMI, hệ thống dựng
đúng payload (prompt renumber + ảnh/video tham chiếu + tham số) đằng sau một vé
dùng-một-lần, và trang `taovideo` tự điền form từ vé đó để khách sửa rồi tự
chạy — không còn `refs: []` (N-1) và không còn thẻ `@IMAGE_k` bị sinh rồi quên
(N-2).

**Architecture:** `apps/prompt_ai_ommi/services/handoff_stage.py` đọc
`ommi_binding` (Pha 1) + `ommi_resource_variant`, đánh số lại thẻ theo quy tắc
đã đo từ bản gốc, gọi `apps.taovideo.refs` để chuẩn hoá/inline ảnh, gọi bất biến
biên `bat_bien_giao_bai()` (Pha 1 tạo), rồi cất `payload` vào một dòng
`ommi_handoff` hết hạn 30 phút. `apps/taovideo` không bao giờ import
`apps.prompt_ai_ommi` (cạnh một chiều): trình duyệt tự gọi
`GET /prompt-ai-ommi/api/handoff/{id}/payload` bằng JS, rồi POST kết quả đó
(một dict JSON thuần, không phải một lời gọi Python) sang route mới
`POST /taovideo/prefill` của chính `taovideo`, nơi `apps/taovideo/prefill.py`
snap giá trị vào enum hợp lệ và `apps/taovideo/routes.py` stage ảnh/video vào
`upload_sessions` để `/queue` nộp như một job bình thường.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (Postgres/SQLite), Jinja2 +
HTMX + JS thuần (không framework), pytest + `fastapi.testclient.TestClient`.

**Spec:** `docs/superpowers/specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md`
(đọc cùng plan này — đặc biệt §4.2 Pha 2, §5, §6.2, §6.2b, §6.3, §8, §9).

## Global Constraints

Sao đúng từ spec §2 — mọi Task dưới đây ngầm mang toàn bộ bảng này.

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (`apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ được import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` (`AGENTS.md` §8.2b) |
| G-3 | App→app | Chỉ cạnh khai tường minh trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`. Spec này thêm **đúng một** cạnh: `("prompt_ai_ommi", "taovideo")`. Xem G-3b |
| G-3b | ⭐ Khai cạnh là việc **HAI BÊN**, lệch một tên là **gate ĐỎ** | `tools/lint_app_contract.py:381-398` đối chiếu hai chiều: bên gọi khai trong `APP_DUOC_DUNG_APP`, bên bị gọi tự khai `BE_MAT_CONG_KHAI` (tuple literal, ⛔ không `frozenset(...)`/`set(...)`) trong `apps/<slug>/__init__.py`. `apps/taovideo/__init__.py` hiện RỖNG. Việc này thuộc **Làn M / Pha 1** — plan này chỉ **tiêu thụ** kết quả, không viết lại. Đúng 5 cặp phải khai ở CẢ HAI nơi: `("apps.taovideo.refs","normalize_image")`, `("apps.taovideo.refs","image_to_inline")`, `("apps.taovideo.refs","image_role")`, `("apps.taovideo.refs","VALID_IMAGE_ROLES")`, `("apps.taovideo.refs","MAX_INLINE_BYTES")` |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring |
| G-5 | Alembic | **MỘT head duy nhất**. Head ghi trong spec (`edb8b0fc0ac9`) là ảnh chụp lúc viết spec — **không dùng làm `down_revision` cứng** (xem Task 1) |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số không trùng (`tools/check_so_test.py`). Dải của plan này: **5132–5159** (`test_5130`/`test_5131` là của Pha 1 — `bat_bien_giao_bai` + test riêng — ⛔ không lấy) |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM, `.ps1` thuần ASCII, không viết Python inline qua PowerShell |
| G-8 | Việc > vài giây | Đi qua hàng đợi job. Không áp dụng trực tiếp cho các Task dưới (giao bài chỉ dựng payload, không tự chạy job) |
| G-9 | Tiền | Giữ chỗ → quyết toán → hoàn. Không áp dụng trực tiếp (Pha 2 không thu credit — job thật do khách tự nộp ở `taovideo/queue`, đã có giữ-chỗ/quyết-toán riêng) |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}`. Task 7 chỉ sửa `<script>` **inline** trong template, không tạo file tĩnh mới ⇒ không cần cache-bust |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt thật, chốt trên `https://app.lttstudios.com` |
| G-12 | Lệnh nặng | Qua `chay_nang.py --phien <làn> -- <lệnh>`, `-n` ≤ 7. Kiểm `cua_so_yen.py`/`tai_may.py` trước |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate |
| G-14 | `D:\BOT GEMINI` | Kho CHỈ ĐỌC. Không áp dụng trực tiếp |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |

## Giả định phụ thuộc Pha 1 (đọc trước khi bắt đầu)

Plan này **tiêu thụ**, không viết lại, ba thứ do Pha 1 (Làn M/A) tạo:

1. Bảng `ommi_binding` (cột đúng spec §4.2 Pha 1) và lớp ORM
   `apps.prompt_ai_ommi.tables.OmmiBinding` (`project_id`, `scene_id` nullable,
   `tag`, `kind`, `variant_id`, `position`, `role`).
2. Hàm bất biến biên (spec §8, đã sửa để thêm `has_binding`):

   ```python
   bat_bien_giao_bai(prompt: str, refs: list[dict], skipped: list[dict],
                     *, has_binding: bool = False) -> None
   ```

   ném `ValueError` khi vi phạm B-1..B-5, đặt sẵn trong
   `apps/prompt_ai_ommi/services/handoff_stage.py` — file này **đã tồn tại**
   khi Task 2 bắt đầu, chỉ chứa hàm đó và test riêng `test_5131_*` (của Pha 1).
   Task 2 **thêm** hàm vào cuối file, không sửa hàm đã có. `has_binding` là
   **bắt buộc truyền giá trị thật** ở chỗ gọi của Pha 2 (mặc định `False` chỉ
   để chỗ gọi cũ/Pha 1 không vỡ).
3. Hai bề mặt app→app đã khai đủ (G-3b): `APP_DUOC_DUNG_APP` +
   `apps/taovideo/__init__.py::BE_MAT_CONG_KHAI`, đúng 5 cặp (xem bảng G-3b).

Nếu khi thực thi plan này mà (1)/(2)/(3) chưa merge vào `main`: **dừng**, báo
Làn M — đây không phải lỗi của Pha 2.

⛔ Toàn bộ mã trong plan này chỉ được import **đúng 5 tên** ở mục (3) từ
`apps.taovideo` (qua `apps.taovideo.refs`). Không import
`apps.taovideo.routes`, `.jobs`, `.modelark`, `.cost`, `.models`, `.manifest`
từ phía `prompt_ai_ommi` — kể cả để lấy danh sách enum `camera`/`motion`/
`visual_style` (xem mục "Camera/motion/visual_style là enum đóng" dưới đây:
danh sách đó được **chép thành literal**, không import). (Chiều ngược lại —
`apps/taovideo/prefill.py` và `apps/taovideo/routes.py` gọi lẫn nhau trong
CHÍNH app `taovideo` — không bị giới hạn này, và **không được** import
`apps.prompt_ai_ommi` theo chiều nào.)

## Mô hình "cảnh" dùng trong Pha 2 — làm rõ một điểm spec không nói thẳng

`ommi_handoff.scene_id` tham chiếu tới **cảnh nhúng trong JSON**
(`AppProject.payload["scenes"][i]`, được làm sạch bởi
`apps/prompt_ai_ommi/project_schema.py::clean_scene()` — có sẵn `camera`,
`lighting`, `mood`, `prompt`), **không phải** bảng `ommi_scene` (đó là của tính
năng storyboard ảnh riêng, giữ nguyên ở §4.1). Đây đúng là mô hình
`routes/handoff.py` hiện tại (`_handoff_params`) đã dùng — Pha 2 giữ nguyên
điểm này, chỉ thay phần dựng `refs`/renumber.

## Camera/motion/visual_style là enum ĐÓNG ở `taovideo` — hai đường song song (spec §6.2b)

`apps/taovideo/manifest.py:196-198` khai ba trường này là enum đóng:

| Trường | Bộ giá trị hợp lệ |
|---|---|
| `camera` | `""`, `static`, `dolly_in`, `tracking`, `orbit`, `aerial`, `handheld` |
| `motion` | `""`, `subtle`, `dynamic`, `cinematic` |
| `visual_style` | `""`, `realistic`, `cinematic`, `anime`, `product` |

Nhưng `scene.camera`/`.lighting`/`.mood` (từ `project_schema.clean_scene()`) là
chữ tự do giàu chi tiết (`"medium shot, 35mm, slow push in"`). Nhét thẳng vào
enum ⇒ `422` ở `taovideo`. Luật bắt buộc, **hai đường song song**, cả hai đều
cài đặt ở `dung_payload()` (Task 2):

1. **Chi tiết đầy đủ đi vào `prompt`**: ghép cuối
   `Camera: <scene.camera>. Lighting: <scene.lighting>. Mood: <scene.mood>.`
   (chỉ ghép phần nào khác rỗng).
2. **Enum chỉ là gợi ý thô**, suy ra bằng khớp từ khoá **tất định** (không
   LLM, không dựa thứ tự `dict`/`set` không xác định) — khớp không được thì
   `""`.

⛔ Sai lầm phải tránh (và có test chặn ở Task 2): chỉ khớp enum rồi **bỏ** chữ
gốc — vứt trường im lặng lần thứ hai, đúng N-1 mà pha này đang chữa.

⚠️ `camera` nằm trong `idempotency.key_fields` của `taovideo` — hai lần giao
bài cùng cảnh phải suy ra **cùng một** enum (có test riêng ở Task 2).

---

### Task 1: Bảng `ommi_handoff` (migration + model)

**Files:**
- Create: `alembic/versions/20260926_1500_ommi_handoff.py`
- Create: `apps/prompt_ai_ommi/tables/handoff.py`
- Modify: `apps/prompt_ai_ommi/tables/__init__.py` (thêm một dòng re-export —
  xem cảnh báo sổ dùng chung bên dưới)
- Test: `tests/test_5138_ommi_handoff_table.py`

**Interfaces:**
- Produces: `apps.prompt_ai_ommi.tables.OmmiHandoff` (ORM model, cột đúng
  spec §4.2 Pha 2: `id`, `project_id`, `scene_id`, `target_app_slug`,
  `payload`, `used_at`, `expires_at`, `created_at`).

⚠️ **Sổ dùng chung**: `apps/prompt_ai_ommi/tables/__init__.py` là tệp Làn M sở
hữu (spec §9.1). Bước re-export dưới đây là **một dòng import duy nhất**; nếu
khi thực thi thấy tệp đang có sửa dở của làn khác (diff chưa commit không phải
của mình), dừng lại và hỏi thay vì tự gộp.

⚠️ **`down_revision` không có giá trị cứng** — đây là chỗ DUY NHẤT trong plan
này được phép vậy (spec §9.1: migration Pha 1 do làn khác viết, head sẽ khác
`edb8b0fc0ac9` ghi trong spec vào lúc plan này chạy). Lấy giá trị thật bằng:

```
python -m alembic heads
```

Kết quả PHẢI là **đúng một dòng** dạng `<hex> (head)` (G-5 — một head duy
nhất). Nếu ra ≥ 2 dòng: dừng lại, đây là nhánh migration chưa gộp, báo Làn
M/chủ dự án — không tự chọn một trong hai để đi tiếp.

- [ ] **Step 1: Lấy head thật**

Chạy: `python -m alembic heads`
Ghi lại chuỗi hex duy nhất trả về — gọi nó `<HEAD_THAT>` cho các bước dưới.

- [ ] **Step 2: Viết test đỏ cho bảng**

```python
# tests/test_5138_ommi_handoff_table.py
"""Bang `ommi_handoff` dung mot lan, het han 30 phut (spec Pha 2 §4.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine()


def test_roundtrip_insert_and_read_back(db_session):
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    now = datetime.now(timezone.utc)
    row = OmmiHandoff(project_id="proj_1", scene_id="scene_1",
                      target_app_slug="taovideo",
                      payload={"prompt": "xin chao", "refs": [], "skipped": [],
                               "skipped_over_limit": 0,
                               "params": {"model": "seedance-2.0-mini"},
                               "tag_map": {}},
                      expires_at=now + timedelta(minutes=30))
    db_session.add(row); db_session.commit()
    got = db_session.get(OmmiHandoff, row.id)
    assert got is not None
    assert got.used_at is None
    assert got.payload["prompt"] == "xin chao"
    assert got.target_app_slug == "taovideo"
```

- [ ] **Step 3: Chạy test, xác nhận đỏ vì thiếu bảng/model**

Chạy: `python -m pytest tests/test_5138_ommi_handoff_table.py -q`
Kỳ vọng: FAIL — `ModuleNotFoundError`/`ImportError: cannot import name
'OmmiHandoff'` hoặc `sqlalchemy.exc.OperationalError: no such table:
ommi_handoff`.

- [ ] **Step 4: Viết migration**

```python
# alembic/versions/20260926_1500_ommi_handoff.py
# -*- coding: utf-8 -*-
"""PROMPT AI OMMI Pha 2: `ommi_handoff` — ve giao bai dung mot lan, het han 30 phut.

Payload da renumber (@IMG_k/@VID_k), da inline anh, da qua bat bien bien
`bat_bien_giao_bai()` (Pha 1) truoc khi ghi. `used_at` khac NULL = ve da dung,
tu choi doc lan hai. Khong co cot `owner_id`: quyen so huu kiem qua
`project_id` (join sang `AppProject` cua nen tang), khong lap lai o day.

Revision ID: b7e21f9a4c68
Revises: <HEAD_THAT>
Create Date: 2026-09-26 15:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e21f9a4c68"
down_revision: Union[str, None] = "<HEAD_THAT>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ommi_handoff",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scene_id", sa.String(36), nullable=False),
        sa.Column("target_app_slug", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_ommi_handoff_project_id", "ommi_handoff", ["project_id"])
    op.create_index("ix_ommi_handoff_scene_id", "ommi_handoff", ["scene_id"])
    op.create_index("ix_ommi_handoff_expires_at", "ommi_handoff", ["expires_at"])


def downgrade() -> None:
    op.drop_table("ommi_handoff")
```

⚠️ Thay `<HEAD_THAT>` bằng chuỗi hex thật lấy ở Step 1 trước khi lưu tệp —
KHÔNG để nguyên placeholder trong tệp thật.

- [ ] **Step 5: Viết model ORM**

```python
# apps/prompt_ai_ommi/tables/handoff.py
"""Bang `ommi_handoff` — ve giao bai dung mot lan sang app khac (Pha 2).

Tach rieng khoi `kich_ban.py` vi day khong phai mot phan cua "kich ban"
(brief/scene/iteration) ma la mot HOP THU tam thoi giua hai app — vong doi
30 phut, khong lien quan gi toi vong doi cua project.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiHandoff(Base):
    """Ve giao bai: mot canh -> mot payload san sang cho app dich.

    `used_at` khac NULL sau lan doc dau tien (xem
    `services/handoff_stage.py::doc_va_tieu_ve`). Khong co `owner_id`: quyen
    kiem qua `project_id` (chu cua `AppProject` do), khong nhan doi o day.
    """

    __tablename__ = "ommi_handoff"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

- [ ] **Step 6: Re-export trong `tables/__init__.py`**

Thêm đúng một dòng (giữ nguyên mọi dòng khác):

```python
from apps.prompt_ai_ommi.tables.handoff import OmmiHandoff  # noqa: F401
```

- [ ] **Step 7: Chạy migration lên CSDL test rồi chạy lại test**

Chạy: `python -m alembic upgrade head`
Chạy: `python -m pytest tests/test_5138_ommi_handoff_table.py -q`
Kỳ vọng: PASS.

- [ ] **Step 8: Commit**

```bash
git add alembic/versions/20260926_1500_ommi_handoff.py \
       apps/prompt_ai_ommi/tables/handoff.py \
       apps/prompt_ai_ommi/tables/__init__.py \
       tests/test_5138_ommi_handoff_table.py
git commit -m "$(cat <<'EOF'
them bang ommi_handoff (ve giao bai dung mot lan, het han 30 phut)

Ve giu payload da renumber + da inline anh, phuc vu Pha 2 giao bai sang
taovideo. down_revision lay tu head that luc chay migration, khong chep
gia tri cu trong spec.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `handoff_stage.py` — dựng payload (renumber + trần + inline ảnh + enum tất định)

**Files:**
- Modify: `apps/prompt_ai_ommi/services/handoff_stage.py` (file đã tồn tại từ
  Pha 1 — chỉ chứa `bat_bien_giao_bai()`; thêm các hàm dưới vào CUỐI file)
- Test: `tests/test_5139_handoff_stage_missing_file.py`
- Test: `tests/test_5134_handoff_stage_deleted_variant.py`
- Test: `tests/test_5135_handoff_stage_renumber_and_limits.py`
- Test: `tests/test_5136_handoff_stage_oversize_after_normalize.py`
- Test: `tests/test_5137_handoff_stage_camera_prompt_and_enum.py`

**Interfaces:**
- Consumes:
  - `apps.taovideo.refs.normalize_image(data: bytes) -> tuple[bytes, str]`
  - `apps.taovideo.refs.image_to_inline(data: bytes) -> str` (ném `RefError`
    nếu ảnh vẫn > 8 MiB sau `normalize_image`)
  - `apps.taovideo.refs.image_role(role: str) -> str`
  - `apps.taovideo.refs.VALID_IMAGE_ROLES: set[str]`
  - `apps.taovideo.refs.MAX_INLINE_BYTES: int` (= 8 * 1024 * 1024)
  - ⛔ KHÔNG tên nào khác của `apps.taovideo` (kể cả `manifest.py` — enum
    camera/motion/visual_style dưới đây là literal chép tay, không import).
  - `apps.prompt_ai_ommi.services.handoff_stage.bat_bien_giao_bai(prompt: str, refs: list[dict], skipped: list[dict], *, has_binding: bool = False) -> None` (đã có trong file, Pha 1 viết — ném `ValueError`)
  - `apps.prompt_ai_ommi.tables.OmmiResourceVariant` (đã có — `id`, `owner_id`, `storage_key`)
  - `apps.prompt_ai_ommi.tables.OmmiBinding` (Pha 1 — `project_id`, `scene_id` nullable, `tag`, `kind`, `variant_id`, `position`, `role`)
  - `platform_core.storage.get_storage() -> Storage` (`.exists(key)`, `.open(key)`, `.try_url_for(key, ttl_s) -> str | None`)
- Produces:
  - `dung_payload(db: Session, *, project, scene: dict, overrides: dict | None = None) -> dict`
    — trả đúng hình dạng payload spec §6.2 (`prompt`, `params`, `refs`,
    `tag_map`, `skipped`, `skipped_over_limit`). Hàm THUẦN với DB/storage (đọc,
    không ghi `ommi_handoff`) — Task 3 dùng kết quả này để tạo vé.

- [ ] **Step 1: Viết test đỏ — 2 ảnh, 1 mất tệp (phép bắt buộc của brief)**

```python
# tests/test_5139_handoff_stage_missing_file.py
"""Anh mat tep van TIEU SO thu tu va vao `skipped` (spec Pha 2 §6.3 rule 3).

Day la phep KHONG duoc thieu theo brief: dung canh co 2 anh, mot anh mat tep,
khang dinh anh mat tep CO tieu so thu tu va co mat trong `skipped`.
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-missing.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db, storage_mod.get_storage()
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def _project(owner_id="user_1", project_id="proj_1"):
    from types import SimpleNamespace
    return SimpleNamespace(id=project_id, payload={"brief": {"aspect_ratio": "16:9",
                                                             "style_id": "cinematic"}})


def test_mat_tep_van_tieu_so_va_vao_skipped(bienh):
    db, storage = bienh
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    storage.put("ommi/user_1/res/keep.png", io.BytesIO(PNG), content_type="image/png")
    con = OmmiResourceVariant(id="var_con", resource_id="res_1", owner_id="user_1",
                              storage_key="ommi/user_1/res/keep.png")
    mat = OmmiResourceVariant(id="var_mat", resource_id="res_1", owner_id="user_1",
                              storage_key="ommi/user_1/res/da-xoa.png")
    db.add(con); db.add(mat); db.flush()
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_1",
                       kind="image", variant_id="var_con", position=0,
                       role="reference_image"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_2",
                       kind="image", variant_id="var_mat", position=1,
                       role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "Canh co @IMAGE_1 va @IMAGE_2",
            "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene)

    assert len(payload["refs"]) == 1
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["variant_id"] == "var_mat"
    assert payload["skipped"][0]["ly_do"] == "tep khong ton tai"
    # anh mat tep VAN tieu so: no chiem @IMG_2, khong bi bo qua trong tag_map
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_2"
    assert "@IMG_1" in payload["prompt"] and "@IMG_2" in payload["prompt"]
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Chạy: `python -m pytest tests/test_5139_handoff_stage_missing_file.py -q`
Kỳ vọng: FAIL — `AttributeError`/`ImportError: cannot import name 'dung_payload'`.

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
# them vao CUOI apps/prompt_ai_ommi/services/handoff_stage.py
# (file da co san `bat_bien_giao_bai` tu Pha 1 — KHONG sua ham do)

import re as _re
from sqlalchemy import select as _select

from apps.taovideo.refs import (RefError, image_role, image_to_inline)
from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant

TRAN_ANH = 9
TRAN_VIDEO = 3
_NHAN_NGOAC = {"image": "Image", "video": "Video"}
_TIEN_TO_TAG = {"image": "IMG", "video": "VID"}

# Danh sach nay la LITERAL chep tay tu apps/taovideo/manifest.py:196-198
# (khong import — G-3b chi cho phep 5 ten cua apps.taovideo.refs). Neu
# taovideo doi enum, phai sua CA HAI noi; ghi chu o ca hai (xem
# apps/taovideo/prefill.py cua Task 5).
_TU_KHOA_CAMERA = {
    "static": ("static", "tinh", "locked", "fixed", "tripod"),
    "dolly_in": ("dolly_in", "dolly in", "push in", "zoom in", "tien may"),
    "tracking": ("tracking", "bam theo", "follow"),
    "orbit": ("orbit", "xoay quanh", "arc shot"),
    "aerial": ("aerial", "drone", "flycam", "tren cao", "bird"),
    "handheld": ("handheld", "cam tay", "shaky"),
}
_TU_KHOA_MOTION = {
    "subtle": ("subtle", "tinh te", "cham rai"),
    "dynamic": ("dynamic", "nang dong", "nhanh"),
    "cinematic": ("cinematic", "dien anh"),
}
_TU_KHOA_VISUAL_STYLE = {
    "realistic": ("realistic", "photoreal", "chan thuc"),
    "cinematic": ("cinematic", "dien anh", "filmic"),
    "anime": ("anime", "hoat hinh"),
    "product": ("product", "quang cao", "commercial"),
}


def _doan_enum(text: str, tu_khoa: dict) -> str:
    """Suy enum tu chu tu do bang khop tu khoa — TAT DINH, khong LLM.

    Duyet theo THU TU CHEN cua dict literal (on dinh tu Python 3.7+): cung
    mot `text` luon ra cung mot enum, du text khop nhieu tu khoa cung luc.
    `camera` nam trong idempotency key cua taovideo — khong tat dinh la hai
    lan giao bai cung canh tach doi job dedupe.
    """
    low = str(text or "").lower()
    for gia_tri, tu in tu_khoa.items():
        if any(t in low for t in tu):
            return gia_tri
    return ""


def _hieu_luc_bindings(db, *, project_id: str, scene_id: str) -> list:
    """Doc `ommi_binding` cap du an (scene_id NULL) hop voi cap canh.

    Gia dinh giao dien Pha 1 (Lan A): bang `OmmiBinding` dung dung cot spec
    §4.2 Pha 1. Neu Lan A cung cap ham doc rieng trong `services/bindings.py`
    khi gop nhanh, doi noi goi trong ham nay — khong doi chu ky `dung_payload`.
    """
    rows = db.execute(_select(OmmiBinding).where(
        OmmiBinding.project_id == project_id,
        (OmmiBinding.scene_id == scene_id) | (OmmiBinding.scene_id.is_(None)),
    )).scalars().all()
    return list(rows)


def _so_cua_tag(tag: str) -> str:
    m = _re.search(r"_(\d+)$", tag)
    return m.group(1) if m else ""


def _doi_tag_trong_prompt(prompt: str, tag_map: dict, kind_by_tag: dict) -> str:
    """Thay ca `@IMAGE_k`/`@VIDEO_k` va `[Image k]`/`[Video k]` (§6.3 rule 4).

    Dung regex voi `(?!\\d)` de `@IMAGE_1` khong nuot nham `@IMAGE_10`.
    """
    out = prompt
    for old_tag, new_tag in tag_map.items():
        out = _re.sub(_re.escape(old_tag) + r"(?!\d)", new_tag, out)
        so = _so_cua_tag(old_tag)
        nhan = _NHAN_NGOAC.get(kind_by_tag.get(old_tag, ""))
        if so and nhan:
            out = _re.sub(_re.escape(f"[{nhan} {so}]") + r"(?!\d)", new_tag, out)
    return out


def dung_payload(db, *, project, scene: dict, overrides: dict | None = None) -> dict:
    """Dung payload giao bai (spec §6.2) tu mot canh cua project 'production'.

    Ham THUAN voi `ommi_handoff` — khong tao ve, khong commit. Goi
    `bat_bien_giao_bai()` ngay truoc khi tra ve (spec §8: dung MOT cho).
    """
    from platform_core.storage import get_storage

    storage = get_storage()
    bindings = _hieu_luc_bindings(
        db, project_id=project.id, scene_id=str(scene.get("id") or ""))
    has_binding = bool(bindings)
    anh = sorted([b for b in bindings if b.kind == "image"], key=lambda b: b.position)
    video = sorted([b for b in bindings if b.kind == "video"], key=lambda b: b.position)
    qua_tran = max(0, len(anh) - TRAN_ANH) + max(0, len(video) - TRAN_VIDEO)
    anh, video = anh[:TRAN_ANH], video[:TRAN_VIDEO]

    refs: list[dict] = []
    skipped: list[dict] = []
    tag_map: dict[str, str] = {}
    kind_by_tag: dict[str, str] = {}
    dem = {"image": 0, "video": 0}

    for kind, danh_sach in (("image", anh), ("video", video)):
        for binding in danh_sach:
            variant = db.get(OmmiResourceVariant, binding.variant_id)
            if variant is None:
                continue  # §6.3 rule 2: khong con ban ghi -> khong tieu so
            dem[kind] += 1
            tag_moi = f"@{_TIEN_TO_TAG[kind]}_{dem[kind]}"
            tag_map[binding.tag] = tag_moi
            kind_by_tag[binding.tag] = kind
            if not storage.exists(variant.storage_key):
                skipped.append({"variant_id": variant.id,
                                "ly_do": "tep khong ton tai"})
                continue
            if kind == "image":
                with storage.open(variant.storage_key) as fh:
                    raw = fh.read()
                try:
                    url = image_to_inline(raw)
                except RefError:
                    skipped.append({"variant_id": variant.id,
                                    "ly_do": "anh qua 8MiB sau chuan hoa"})
                    continue
                refs.append({"kind": "image", "url": url,
                            "role": image_role(binding.role), "handle": tag_moi})
            else:
                url = (storage.try_url_for(variant.storage_key, ttl_s=1800) or
                      f"/prompt-ai-ommi/f/{variant.storage_key}")
                refs.append({"kind": "video", "url": url,
                            "role": "reference_video", "handle": tag_moi})

    prompt = _doi_tag_trong_prompt(str(scene.get("prompt") or ""), tag_map, kind_by_tag)

    # SS6.2b: chi tiet day du -> prompt (chu tu do); enum -> chi la goi y tho.
    camera_tho = str(scene.get("camera") or "").strip()
    lighting_tho = str(scene.get("lighting") or "").strip()
    mood_tho = str(scene.get("mood") or "").strip()
    phu = []
    if camera_tho:
        phu.append(f"Camera: {camera_tho}.")
    if lighting_tho:
        phu.append(f"Lighting: {lighting_tho}.")
    if mood_tho:
        phu.append(f"Mood: {mood_tho}.")
    if phu:
        prompt = (prompt.rstrip() + "\n\n" + " ".join(phu))[:10000]

    bat_bien_giao_bai(prompt, refs, skipped, has_binding=has_binding)

    brief = (project.payload or {}).get("brief") or {}
    style_tho = str(brief.get("style_id") or "")
    params = {
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": 5,
        "aspect_ratio": str(brief.get("aspect_ratio") or "16:9"),
        "generate_audio": True,
        "camera": _doan_enum(camera_tho, _TU_KHOA_CAMERA),
        "motion": _doan_enum(mood_tho, _TU_KHOA_MOTION),
        "visual_style": _doan_enum(style_tho, _TU_KHOA_VISUAL_STYLE),
    }
    for chia_khoa in ("model", "resolution", "duration", "generate_audio"):
        if overrides and chia_khoa in overrides and overrides[chia_khoa] is not None:
            params[chia_khoa] = overrides[chia_khoa]

    return {"prompt": prompt, "params": params, "refs": refs,
           "tag_map": tag_map, "skipped": skipped,
           "skipped_over_limit": qua_tran}
```

- [ ] **Step 4: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5139_handoff_stage_missing_file.py -q`
Kỳ vọng: PASS.

- [ ] **Step 5: Test đỏ — variant bị xoá hẳn (không tiêu số)**

```python
# tests/test_5134_handoff_stage_deleted_variant.py
"""Variant khong con ban ghi -> KHONG tieu so (spec Pha 2 §6.3 rule 2)."""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-deleted.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_variant_xoa_han_khong_tieu_so(bienh):
    db = bienh
    from types import SimpleNamespace
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    import platform_core.storage as storage_mod
    storage_mod.get_storage().put(
        "ommi/user_1/res/a.png", io.BytesIO(PNG), content_type="image/png")
    con = OmmiResourceVariant(id="var_con", resource_id="res_1", owner_id="user_1",
                              storage_key="ommi/user_1/res/a.png")
    db.add(con); db.flush()
    # binding tro toi mot variant_id KHONG con ton tai (da bi xoa that su)
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_1",
                       kind="image", variant_id="var_da_xoa", position=0,
                       role="reference_image"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_2",
                       kind="image", variant_id="var_con", position=1,
                       role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    project = SimpleNamespace(id="proj_1", payload={"brief": {}})
    scene = {"id": "scene_1", "prompt": "Canh co @IMAGE_2",
            "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=project, scene=scene)

    # variant da xoa: khong xuat hien trong tag_map, khong tieu so @IMG_1
    assert "@IMAGE_1" not in payload["tag_map"]
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_1"
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert payload["skipped"] == []
```

- [ ] **Step 6: Chạy test, xác nhận xanh ngay (logic Step 3 đã bao ca này)**

Chạy: `python -m pytest tests/test_5134_handoff_stage_deleted_variant.py -q`
Kỳ vọng: PASS ngay (cài đặt Step 3 đã xử lý `variant is None: continue`). Nếu
FAIL, sửa lại vòng lặp ở Step 3 trước khi đi tiếp — đừng bỏ qua.

- [ ] **Step 7: Test đỏ — vượt trần 12 ảnh ⇒ `skipped_over_limit == 3`, và thẻ `@IMAGE_1`/`@IMAGE_10` không va chạm (phép bắt buộc của brief)**

```python
# tests/test_5135_handoff_stage_renumber_and_limits.py
"""Tran 9 anh: 12 binding anh -> skipped_over_limit == 3 (spec Pha 2 §6.2/6.3)."""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-limit.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_muoi_hai_anh_cat_con_chin_va_dem_ba(bienh):
    db = bienh
    from types import SimpleNamespace
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    import platform_core.storage as storage_mod
    storage = storage_mod.get_storage()
    for i in range(12):
        key = f"ommi/user_1/res/{i}.png"
        storage.put(key, io.BytesIO(PNG), content_type="image/png")
        db.add(OmmiResourceVariant(id=f"var_{i}", resource_id="res_1",
                                   owner_id="user_1", storage_key=key))
        db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1",
                           tag=f"@IMAGE_{i + 1}", kind="image",
                           variant_id=f"var_{i}", position=i,
                           role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    project = SimpleNamespace(id="proj_1", payload={"brief": {}})
    scene = {"id": "scene_1", "prompt": "canh nhieu anh",
            "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=project, scene=scene)

    assert payload["skipped_over_limit"] == 3
    assert len(payload["refs"]) == 9


def test_doi_tag_khong_nuot_nham_muoi_voi_mot(bienh):
    """`@IMAGE_1` va `[Image 10]` khong duoc va cham (bay tag/collision)."""
    db = bienh
    from types import SimpleNamespace
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    import platform_core.storage as storage_mod
    storage = storage_mod.get_storage()
    storage.put("ommi/user_1/res/a.png", io.BytesIO(PNG), content_type="image/png")
    storage.put("ommi/user_1/res/b.png", io.BytesIO(PNG), content_type="image/png")
    db.add(OmmiResourceVariant(id="var_1", resource_id="res_1", owner_id="user_1",
                               storage_key="ommi/user_1/res/a.png"))
    db.add(OmmiResourceVariant(id="var_10", resource_id="res_1", owner_id="user_1",
                               storage_key="ommi/user_1/res/b.png"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_1",
                       kind="image", variant_id="var_1", position=0,
                       role="reference_image"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_10",
                       kind="image", variant_id="var_10", position=1,
                       role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    project = SimpleNamespace(id="proj_1", payload={"brief": {}})
    scene = {"id": "scene_1",
            "prompt": "Dung @IMAGE_1 va [Image 10] trong cung canh",
            "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=project, scene=scene)

    assert payload["tag_map"]["@IMAGE_1"] == "@IMG_1"
    assert payload["tag_map"]["@IMAGE_10"] == "@IMG_2"
    assert "@IMG_1" in payload["prompt"]
    assert "@IMG_2" in payload["prompt"]
    assert "@IMAGE_1" not in payload["prompt"] and "@IMAGE_10" not in payload["prompt"]
    assert "[Image 10]" not in payload["prompt"]
```

- [ ] **Step 8: Chạy, xác nhận xanh (cài đặt Step 3 đã đủ — regex `(?!\d)` chặn va chạm)**

Chạy: `python -m pytest tests/test_5135_handoff_stage_renumber_and_limits.py -q`
Kỳ vọng: PASS. Nếu ca collision FAIL, kiểm lại `_doi_tag_trong_prompt` đã dùng
regex (không phải `str.replace`) như Step 3.

- [ ] **Step 9: Test đỏ — ảnh vẫn > 8 MiB sau chuẩn hoá (`RefError`) ⇒ vào `skipped`, VẪN tiêu số**

```python
# tests/test_5136_handoff_stage_oversize_after_normalize.py
"""Anh qua 8MiB SAU chuan hoa: image_to_inline() nem RefError.

Day la ca THAT (khach tai anh rat lon) — phai vao `skipped` voi ly do ro
rang, VA theo §6.3 rule 3 no CO tieu so thu tu (variant con ban ghi, chi
khong dung duoc).
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-oversize.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_anh_qua_8mib_sau_chuan_hoa_vao_skipped_va_tieu_so(bienh, monkeypatch):
    db = bienh
    from types import SimpleNamespace
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from apps.taovideo.refs import RefError
    import platform_core.storage as storage_mod
    storage_mod.get_storage().put(
        "ommi/user_1/res/khong.png", io.BytesIO(PNG), content_type="image/png")
    storage_mod.get_storage().put(
        "ommi/user_1/res/to.png", io.BytesIO(PNG), content_type="image/png")
    db.add(OmmiResourceVariant(id="var_nho", resource_id="res_1", owner_id="user_1",
                               storage_key="ommi/user_1/res/khong.png"))
    db.add(OmmiResourceVariant(id="var_to", resource_id="res_1", owner_id="user_1",
                               storage_key="ommi/user_1/res/to.png"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_1",
                       kind="image", variant_id="var_nho", position=0,
                       role="reference_image"))
    db.add(OmmiBinding(project_id="proj_1", scene_id="scene_1", tag="@IMAGE_2",
                       kind="image", variant_id="var_to", position=1,
                       role="reference_image"))
    db.commit()

    goc = hs.image_to_inline

    def _gia_lap(data: bytes) -> str:
        # Lan goi thu hai (variant "to") gia lap RefError; lan dau van chay
        # ham that.
        _gia_lap.dem += 1
        if _gia_lap.dem == 2:
            raise RefError("anh > 8MiB — can asset:// / URL cong khai")
        return goc(data)
    _gia_lap.dem = 0
    monkeypatch.setattr(hs, "image_to_inline", _gia_lap)

    project = SimpleNamespace(id="proj_1", payload={"brief": {}})
    scene = {"id": "scene_1", "prompt": "Dung @IMAGE_1 va @IMAGE_2",
            "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=project, scene=scene)

    assert len(payload["refs"]) == 1
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["variant_id"] == "var_to"
    assert payload["skipped"][0]["ly_do"] == "anh qua 8MiB sau chuan hoa"
    # var_to VAN tieu so @IMG_2 du khong co trong refs
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_2"
    assert "@IMG_2" in payload["prompt"]
```

- [ ] **Step 10: Chạy test, xác nhận xanh (cài đặt Step 3 đã bắt `RefError` quanh `image_to_inline`)**

Chạy: `python -m pytest tests/test_5136_handoff_stage_oversize_after_normalize.py -q`
Kỳ vọng: PASS.

- [ ] **Step 11: Test đỏ — camera/lighting/mood tự do vào prompt nguyên văn + enum tất định (spec §6.2b, bắt buộc)**

```python
# tests/test_5137_handoff_stage_camera_prompt_and_enum.py
"""SS6.2b: chi tiet tu do -> prompt nguyen van; enum chi la goi y THO, tat dinh.

Hai phep bat buoc theo yeu cau spec/coordinator:
1. scene.camera khac rong => prompt gui di PHAI CHUA scene.camera nguyen van
   (khong duoc chi khop enum roi bo chu goc — dung N-1 lan hai).
2. Goi hai lan cho CUNG MOT canh => CUNG MOT enum (camera nam trong
   idempotency key cua taovideo — khong tat dinh la tach doi job dedupe).
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-camera.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def _project():
    from types import SimpleNamespace
    return SimpleNamespace(id="proj_1", payload={"brief": {"style_id": "cinematic"}})


def test_camera_tu_do_giu_nguyen_van_trong_prompt(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1",
            "prompt": "Mot canh binh minh tren nui",
            "camera": "medium shot, 35mm, slow push in",
            "lighting": "anh sang vang buoi som",
            "mood": "yen binh, cham rai"}
    payload = hs.dung_payload(db, project=_project(), scene=scene)

    assert "medium shot, 35mm, slow push in" in payload["prompt"]
    assert "anh sang vang buoi som" in payload["prompt"]
    assert "yen binh, cham rai" in payload["prompt"]
    # goi y enum: "push in" -> dolly_in; "cham rai" -> subtle
    assert payload["params"]["camera"] == "dolly_in"
    assert payload["params"]["motion"] == "subtle"


def test_camera_khong_khop_tu_khoa_nao_ra_rong(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh don gian",
            "camera": "mot cau mo ta khong lien quan gi toi may quay",
            "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene)
    assert payload["params"]["camera"] == ""


def test_goi_hai_lan_cung_canh_ra_cung_mot_enum(bienh):
    """Tat dinh: khong LLM, khong phu thuoc thu tu khong xac dinh."""
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh",
            "camera": "dolly in tracking shot voi nhieu chuyen dong",
            "lighting": "", "mood": ""}
    lan_mot = hs.dung_payload(db, project=_project(), scene=dict(scene))
    lan_hai = hs.dung_payload(db, project=_project(), scene=dict(scene))
    assert lan_mot["params"]["camera"] == lan_hai["params"]["camera"]
    # khop tu khoa dau tien theo thu tu _TU_KHOA_CAMERA (dolly_in truoc tracking)
    assert lan_mot["params"]["camera"] == "dolly_in"
```

- [ ] **Step 12: Chạy test, xác nhận xanh (cài đặt Step 3 đã có `_doan_enum` + ghép prompt)**

Chạy: `python -m pytest tests/test_5137_handoff_stage_camera_prompt_and_enum.py -q`
Kỳ vọng: PASS.

- [ ] **Step 13: Chạy cả cụm Task 2**

Chạy: `python -m pytest tests/test_5139_handoff_stage_missing_file.py tests/test_5134_handoff_stage_deleted_variant.py tests/test_5135_handoff_stage_renumber_and_limits.py tests/test_5136_handoff_stage_oversize_after_normalize.py tests/test_5137_handoff_stage_camera_prompt_and_enum.py -q`
Kỳ vọng: 7 test PASS.

- [ ] **Step 14: Commit**

```bash
git add apps/prompt_ai_ommi/services/handoff_stage.py \
       tests/test_5139_handoff_stage_missing_file.py \
       tests/test_5134_handoff_stage_deleted_variant.py \
       tests/test_5135_handoff_stage_renumber_and_limits.py \
       tests/test_5136_handoff_stage_oversize_after_normalize.py \
       tests/test_5137_handoff_stage_camera_prompt_and_enum.py
git commit -m "$(cat <<'EOF'
them dung_payload(): renumber the + tran anh/video + inline anh + enum tat dinh

Doc ommi_binding, danh so lai @IMAGE_k/@VIDEO_k thanh @IMG_k/@VID_k theo
dung quy tac da do tu ban goc (hai bo dem doc lap, variant xoa han khong
tieu so, mat tep hoac qua 8MiB van tieu so va vao skipped, tran 9 anh + 3
video cat am tham). camera/lighting/mood tu do di nguyen van vao prompt;
camera/motion/visual_style cua taovideo chi la goi y enum suy tu khoa TAT
DINH, khop duoc thi dung, khong thi rong — khong bao gio bo chu goc. Goi
bat_bien_giao_bai(..., has_binding=...) cua Pha 1 truoc khi tra payload.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Vé dùng một lần — `tao_ve` / `tim_ve` / `doc_va_tieu_ve`

**Files:**
- Modify: `apps/prompt_ai_ommi/services/handoff_stage.py` (thêm cuối file, sau
  các hàm Task 2)
- Test: `tests/test_5140_handoff_stage_ticket_lifecycle.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.tables.OmmiHandoff` (Task 1)
- Produces:
  - `class HandoffError(RuntimeError)`, `class VeKhongHopLe(HandoffError)`,
    `class VeDaDung(HandoffError)`, `class VeHetHan(HandoffError)`
  - `tao_ve(db: Session, *, project_id: str, scene_id: str, payload: dict, target_app_slug: str = "taovideo") -> OmmiHandoff`
  - `tim_ve(db: Session, ticket_id: str) -> OmmiHandoff | None`
  - `doc_va_tieu_ve(db: Session, row: OmmiHandoff) -> dict` — ném `VeDaDung`
    nếu `used_at is not None`, `VeHetHan` nếu hết hạn; nếu hợp lệ, đặt
    `used_at = now()` và trả `dict(row.payload)`.

- [ ] **Step 1: Viết test đỏ — vòng đời vé (tạo → đọc lần 1 OK → đọc lần 2 bị từ chối; hết hạn bị từ chối)**

```python
# tests/test_5140_handoff_stage_ticket_lifecycle.py
"""Ve giao bai: dung mot lan, het han 30 phut (spec Pha 2 §4.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-ticket.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine()


def _payload():
    return {"prompt": "xin chao", "params": {"model": "seedance-2.0-mini"},
           "refs": [], "tag_map": {}, "skipped": [], "skipped_over_limit": 0}


def test_doc_lan_hai_bi_tu_choi(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1", payload=_payload())
    db.commit()

    row = hs.tim_ve(db, ve.id)
    lan_mot = hs.doc_va_tieu_ve(db, row)
    db.commit()
    assert lan_mot["prompt"] == "xin chao"

    row_lai = hs.tim_ve(db, ve.id)
    with pytest.raises(hs.VeDaDung):
        hs.doc_va_tieu_ve(db, row_lai)


def test_ve_khong_ton_tai_tra_none(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    assert hs.tim_ve(db, "khong-ton-tai") is None


def test_ve_het_han_bi_tu_choi(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1", payload=_payload())
    db.commit()
    row = db.get(OmmiHandoff, ve.id)
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    row_lai = hs.tim_ve(db, ve.id)
    with pytest.raises(hs.VeHetHan):
        hs.doc_va_tieu_ve(db, row_lai)
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Chạy: `python -m pytest tests/test_5140_handoff_stage_ticket_lifecycle.py -q`
Kỳ vọng: FAIL — thiếu `tao_ve`/`tim_ve`/`doc_va_tieu_ve`.

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
# them vao CUOI apps/prompt_ai_ommi/services/handoff_stage.py
from datetime import datetime, timedelta, timezone

from apps.prompt_ai_ommi.tables import OmmiHandoff

VE_HET_HAN_PHUT = 30


class HandoffError(RuntimeError):
    pass


class VeKhongHopLe(HandoffError):
    pass


class VeDaDung(HandoffError):
    pass


class VeHetHan(HandoffError):
    pass


def _co_mui_gio(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def tao_ve(db, *, project_id: str, scene_id: str, payload: dict,
          target_app_slug: str = "taovideo") -> OmmiHandoff:
    now = datetime.now(timezone.utc)
    row = OmmiHandoff(project_id=project_id, scene_id=scene_id,
                      target_app_slug=target_app_slug, payload=payload,
                      expires_at=now + timedelta(minutes=VE_HET_HAN_PHUT))
    db.add(row); db.flush()
    return row


def tim_ve(db, ticket_id: str) -> OmmiHandoff | None:
    return db.get(OmmiHandoff, ticket_id)


def doc_va_tieu_ve(db, row: OmmiHandoff) -> dict:
    if row.used_at is not None:
        raise VeDaDung("Ve giao bai da duoc dung.")
    if _co_mui_gio(row.expires_at) <= datetime.now(timezone.utc):
        raise VeHetHan("Ve giao bai da het han.")
    row.used_at = datetime.now(timezone.utc)
    db.flush()
    return dict(row.payload or {})
```

- [ ] **Step 4: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5140_handoff_stage_ticket_lifecycle.py -q`
Kỳ vọng: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/handoff_stage.py \
       tests/test_5140_handoff_stage_ticket_lifecycle.py
git commit -m "$(cat <<'EOF'
them ve giao bai dung mot lan: tao_ve/tim_ve/doc_va_tieu_ve

used_at khac NULL sau lan doc dau -> lan hai nem VeDaDung. Het han 30 phut
-> VeHetHan. Vong doi tach khoi dung_payload() de test khong can dung
payload that moi kiem duoc logic ve.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `routes/handoff.py` — endpoint giao bài + rút gọn đường cũ

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/handoff.py` (toàn bộ — xem diff dưới)
- Test: `tests/test_5141_handoff_route_video_ticket.py`
- Test: `tests/test_5142_handoff_route_ownership_and_single_use.py`

**Interfaces:**
- Consumes:
  - `apps.prompt_ai_ommi.services.handoff_stage.dung_payload(db, *, project, scene, overrides=None) -> dict` (Task 2)
  - `apps.prompt_ai_ommi.services.handoff_stage.tao_ve(db, *, project_id, scene_id, payload, target_app_slug="taovideo") -> OmmiHandoff` (Task 3)
  - `apps.prompt_ai_ommi.services.handoff_stage.tim_ve(db, ticket_id) -> OmmiHandoff | None` (Task 3)
  - `apps.prompt_ai_ommi.services.handoff_stage.doc_va_tieu_ve(db, row) -> dict`, và `VeDaDung`/`VeHetHan`/`VeKhongHopLe` (Task 3)
  - `apps.prompt_ai_ommi.routes._shared._owned_production(db, project_id, user_id)` (đã có)
- Produces:
  - `POST /prompt-ai-ommi/api/projects/{project_id}/handoff/video` → `{ticket_id, expires_at, open_url, skipped, skipped_over_limit}`
  - `GET /prompt-ai-ommi/api/handoff/{ticket_id}/payload` → payload (§6.2), 409 nếu vé đã dùng, 410 nếu hết hạn, 404 nếu sai/không phải chủ

⚠️ `handoff-batch/image` **giữ nguyên** (dùng cho render frame storyboard nội
bộ, không phải giao bài video) — không chạm hàm `handoff_image_batch`.
`POST /handoff/{kind}` (đường cũ, tổng quát) chỉ còn phục vụ `kind="image"`;
nhánh `video` bị xoá khỏi `_handoff_params` vì đã có đường riêng ở trên.

- [ ] **Step 1: Viết test đỏ — giao bài video trả vé, đọc payload lần đầu OK**

```python
# tests/test_5141_handoff_route_video_ticket.py
"""POST handoff/video tra ve; GET payload tra dung hinh dang SS6.2."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff-route.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    uid = tao_nguoi_dung(db, email="ho-a@example.com", password="Strong-pass-123",
                        is_verified=True).id
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-handoff-route-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "ho-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, uid
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def _du_an_co_canh(client, csrf):
    made = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": csrf}, json={"name": "Giao bai"}).json()
    body = made["payload"]
    body["scenes"] = [{"id": "scene_one", "title": "Canh", "duration_seconds": 5,
                       "prompt": "Mot canh khong co anh tham chieu",
                       "camera": "dolly in, slow push",
                       "lighting": "vang hoang hon", "mood": "cinematic"}]
    client.put(f"/prompt-ai-ommi/api/projects/{made['id']}",
              headers={"X-CSRF-Token": csrf},
              json={"revision": made["revision"], "payload": body})
    return made["id"]


def test_giao_bai_tra_ve_va_doc_payload_lan_dau(api):
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)

    ve = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                     headers={"X-CSRF-Token": csrf}, json={"scene_id": "scene_one"})
    assert ve.status_code == 201, ve.text
    data = ve.json()
    assert set(data.keys()) >= {"ticket_id", "expires_at", "open_url",
                               "skipped", "skipped_over_limit"}
    assert data["open_url"] == f"/taovideo/?tu_studio={data['ticket_id']}"
    assert data["skipped_over_limit"] == 0

    payload = client.get(f"/prompt-ai-ommi/api/handoff/{data['ticket_id']}/payload")
    assert payload.status_code == 200
    body = payload.json()
    assert body["prompt"]
    assert "dolly in, slow push" in body["prompt"]  # chi tiet tu do giu nguyen van
    assert body["params"]["camera"] == "dolly_in"   # goi y enum suy tu khoa
    assert body["params"]["aspect_ratio"] == "16:9"
    assert body["refs"] == []
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Chạy: `python -m pytest tests/test_5141_handoff_route_video_ticket.py -q`
Kỳ vọng: FAIL — route `/handoff/video` chưa tồn tại (404), hoặc lỗi 500 vì
`handoff_stage` chưa có hàm.

- [ ] **Step 3: Viết cài đặt — thay toàn bộ `apps/prompt_ai_ommi/routes/handoff.py`**

```python
# apps/prompt_ai_ommi/routes/handoff.py
"""Giao bai anh/video sang app khac.

Duong `video`: dung mot VE (`ommi_handoff`) roi dieu huong khach sang
`taovideo` tu dien form — KHONG con tu nop job thay khach (khac voi duong
`image` o duoi, van giu nguyen kieu cu: hoi bao gia roi nop thang qua
ToolSpec, dung cho frame storyboard noi bo).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _as_int, _csrf, _models, _owned_production, _require_run_enabled, _user, router, require_login, get_db)


def _tool(tool_name: str):
    from platform_core.agent.tools import discover_tools
    from platform_core.registry import discover
    loaded = discover(); spec = discover_tools(apps=loaded).get(tool_name)
    if spec is None:
        raise HTTPException(status_code=503, detail=_t('Công cụ handoff chưa khả dụng.'))
    owner = next((item for item in loaded if any(t.name == tool_name for t in item.manifest.tools)), None)
    if owner is None:
        raise HTTPException(status_code=503, detail=_t('Không xác định được app nhận handoff.'))
    return loaded, spec, owner


def _scene_or_404(project, scene_id: str) -> dict:
    scenes = list((project.payload or {}).get("scenes") or [])
    scene = next((item for item in scenes if item.get("id") == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy cảnh.'))
    return scene


# ── Duong image (frame storyboard noi bo) — GIU NGUYEN kieu cu ──────────────

def _handoff_params_image(project, scene: dict, body: dict) -> tuple[str, dict]:
    tool_name = "image.generate"
    params = {"prompt": str(scene.get("prompt") or "")[:4000],
             "model": str(body.get("model") or next(
                 (item["value"] for item in _models("image")), "hidream-o1")),
             "aspect_ratio": str((project.payload or {}).get("brief", {}).get(
                 "aspect_ratio") or "16:9"),
             "count": _as_int(body.get("count"), 1, 1, 4)}
    from platform_core import providers
    capabilities = providers.model_capabilities(params["model"])
    aspects = list(capabilities.get("aspects") or ["16:9", "9:16", "1:1", "4:3", "3:4"])
    if params["aspect_ratio"] not in aspects:
        params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    return tool_name, params


@router.post("/api/projects/{project_id}/handoff/{kind}", status_code=201)
async def handoff(request: Request, project_id: str, kind: str,
                  _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    if kind != "image":
        raise HTTPException(status_code=404, detail=_t('Loại handoff không hỗ trợ.'))
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    scene = _scene_or_404(project, str(body.get("scene_id") or ""))
    tool_name, params = _handoff_params_image(project, scene, body)
    loaded, spec, owner = _tool(tool_name)
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    try:
        clean = validate_tool_params(tool_name, params, apps=loaded)
    except ToolParamsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    clean["owner_id"] = user.id
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError, credit_for
    quote = credit_for(spec.job_type, clean)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": quote,
                             "tool": tool_name, "authoritative": True}, status_code=200)
    try:
        job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                 job_type=spec.job_type, params=clean,
                                 dedupe_key=dedupe_key_for(spec.job_type, clean))
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": quote, "id": job.id,
            "app_slug": owner.slug, "job_url": f"/jobs/{job.id}"}


@router.post("/api/projects/{project_id}/handoff-batch/image", status_code=201)
async def handoff_image_batch(request: Request, project_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    requested = set(str(value) for value in list(body.get("scene_ids") or [])[:20])
    scenes = [scene for scene in list((project.payload or {}).get("scenes") or [])
              if scene.get("id") in requested]
    if not scenes:
        raise HTTPException(status_code=422, detail=_t('Chưa chọn cảnh hợp lệ để tạo frame.'))
    loaded, spec, owner = _tool("image.generate")
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    prepared = []
    for scene in scenes:
        _, params = _handoff_params_image(project, scene, body)
        try:
            clean = validate_tool_params("image.generate", params, apps=loaded)
        except ToolParamsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        clean["owner_id"] = user.id; prepared.append((scene["id"], clean))
    from platform_core.registry import credit_for
    total = sum(credit_for(spec.job_type, params) for _, params in prepared)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": total,
                             "count": len(prepared), "authoritative": True}, status_code=200)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    jobs = []
    try:
        for scene_id, params in prepared:
            job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                     job_type=spec.job_type, params=params,
                                     dedupe_key=dedupe_key_for(spec.job_type, params))
            jobs.append({"scene_id": scene_id, "id": job.id, "status": job.status})
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": total, "count": len(jobs), "jobs": jobs}


# ── Duong video (giao bai that, Pha 2) ──────────────────────────────────────

@router.post("/api/projects/{project_id}/handoff/video", status_code=201)
async def handoff_video(request: Request, project_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    scene = _scene_or_404(project, str(body.get("scene_id") or ""))

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    overrides = {k: body.get(k) for k in
                ("model", "resolution", "duration", "generate_audio") if k in body}
    payload = hs.dung_payload(db, project=project, scene=scene, overrides=overrides)
    ve = hs.tao_ve(db, project_id=project.id, scene_id=str(scene.get("id") or ""),
                  payload=payload)
    db.commit()
    return {"ticket_id": ve.id, "expires_at": ve.expires_at.isoformat(),
           "open_url": f"/taovideo/?tu_studio={ve.id}",
           "skipped": payload["skipped"],
           "skipped_over_limit": payload["skipped_over_limit"]}


@router.get("/api/handoff/{ticket_id}/payload")
def handoff_payload(request: Request, ticket_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    row = hs.tim_ve(db, ticket_id)
    if row is None:
        raise HTTPException(status_code=404, detail=_t('Vé giao bài không hợp lệ.'))
    _owned_production(db, row.project_id, user.id)  # 404 neu khong phai chu
    try:
        payload = hs.doc_va_tieu_ve(db, row)
    except hs.VeDaDung:
        db.rollback()
        raise HTTPException(status_code=409, detail=_t('Vé giao bài đã được dùng.'))
    except hs.VeHetHan:
        db.rollback()
        raise HTTPException(status_code=410, detail=_t('Vé giao bài đã hết hạn.'))
    db.commit()
    return payload
```

- [ ] **Step 4: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5141_handoff_route_video_ticket.py -q`
Kỳ vọng: PASS.

- [ ] **Step 5: Test đỏ — người khác không đọc được vé; đọc lần hai bị 409**

```python
# tests/test_5142_handoff_route_ownership_and_single_use.py
"""Ve giao bai: chu moi doc duoc, va CHI doc duoc MOT LAN (409 lan hai)."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff-owner.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("owner-a@example.com", "owner-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-handoff-owner-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    a, ca = login("owner-a@example.com")
    b, cb = login("owner-b@example.com")
    yield a, ca, b, cb
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _du_an_co_canh(client, csrf):
    made = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": csrf}, json={"name": "Giao bai"}).json()
    body = made["payload"]
    body["scenes"] = [{"id": "scene_one", "title": "Canh", "prompt": "canh trong"}]
    client.put(f"/prompt-ai-ommi/api/projects/{made['id']}",
              headers={"X-CSRF-Token": csrf},
              json={"revision": made["revision"], "payload": body})
    return made["id"]


def test_nguoi_khac_khong_doc_duoc_ve(api):
    a, ca, b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = a.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
               headers={"X-CSRF-Token": ca}, json={"scene_id": "scene_one"}).json()
    resp = b.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert resp.status_code == 404


def test_doc_lan_hai_bi_tu_choi_409(api):
    a, ca, _b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = a.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
               headers={"X-CSRF-Token": ca}, json={"scene_id": "scene_one"}).json()
    lan_mot = a.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert lan_mot.status_code == 200
    lan_hai = a.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert lan_hai.status_code == 409
```

- [ ] **Step 6: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5142_handoff_route_ownership_and_single_use.py -q`
Kỳ vọng: PASS.

- [ ] **Step 7: Chạy toàn bộ Task 2/3/4 để chắc không phá đường cũ**

Chạy: `python -m pytest tests/test_130_prompt_ai_ommi.py tests/test_5139_handoff_stage_missing_file.py tests/test_5134_handoff_stage_deleted_variant.py tests/test_5135_handoff_stage_renumber_and_limits.py tests/test_5136_handoff_stage_oversize_after_normalize.py tests/test_5137_handoff_stage_camera_prompt_and_enum.py tests/test_5140_handoff_stage_ticket_lifecycle.py tests/test_5141_handoff_route_video_ticket.py tests/test_5142_handoff_route_ownership_and_single_use.py -q`
Kỳ vọng: tất cả PASS — đặc biệt
`test_image_handoff_normalizes_ultrawide_and_quotes_before_submit` trong
`test_130` (đường `image` cũ) vẫn xanh.

- [ ] **Step 8: Commit**

```bash
git add apps/prompt_ai_ommi/routes/handoff.py \
       tests/test_5141_handoff_route_video_ticket.py \
       tests/test_5142_handoff_route_ownership_and_single_use.py
git commit -m "$(cat <<'EOF'
them duong giao bai video qua ve, giu nguyen duong image cu

POST handoff/video khong con tu nop job thay khach — dung dung_payload() +
tao_ve() roi tra open_url sang taovideo. GET handoff/{id}/payload doc mot
lan, kiem quyen bang du an so huu, 409/410 cho ve da dung/het han.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `apps/taovideo/prefill.py` — chuyển payload thành giá trị điền form

**Files:**
- Create: `apps/taovideo/prefill.py`
- Test: `tests/test_5150_taovideo_prefill_values.py`

**Interfaces:**
- Consumes: **KHÔNG import `apps.prompt_ai_ommi` theo bất kỳ chiều nào** —
  hàm chỉ nhận `payload: dict` đã là JSON thô do JS gửi lên (Task 6). Đây là
  hợp đồng cứng của G-3 (cạnh một chiều). `apps.taovideo.models.MODELS`,
  `apps.taovideo.models.DEFAULT_MODEL` (đã có).

  ⚠️ `payload["params"]["camera"]`/`.motion`/`.visual_style"` đến từ
  `handoff_stage._doan_enum()` (Task 2) và đã LÀ một trong các giá trị enum
  hợp lệ (hoặc `""`) — `prefill.py` chỉ cần khớp lại phòng hờ payload bị sửa
  tay/gửi sai, KHÔNG cần tự suy enum từ chữ tự do (đó là việc của Task 2, một
  lần, phía `ommi`).
- Produces: `build_form_values(payload: dict) -> dict` — trả
  `{prompt, model, resolution, duration, aspect_ratio, generate_audio,
  camera, motion, visual_style}`.

- [ ] **Step 1: Viết test đỏ**

```python
# tests/test_5150_taovideo_prefill_values.py
"""prefill.build_form_values(): payload tho -> gia tri dien san form.

Ham THUAN — khong DB, khong storage, khong import apps.prompt_ai_ommi.
"""
from __future__ import annotations


def test_gia_tri_hop_le_duoc_giu_nguyen():
    from apps.taovideo import prefill
    payload = {"prompt": "Mot canh @IMG_1",
              "params": {"model": "seedance-2.0-mini", "resolution": "480p",
                        "duration": 5, "aspect_ratio": "16:9",
                        "generate_audio": True, "camera": "dolly_in",
                        "motion": "cinematic", "visual_style": "cinematic"}}
    values = prefill.build_form_values(payload)
    assert values["prompt"] == "Mot canh @IMG_1"
    assert values["model"] == "seedance-2.0-mini"
    assert values["camera"] == "dolly_in"
    assert values["motion"] == "cinematic"
    assert values["visual_style"] == "cinematic"
    assert values["generate_audio"] is True


def test_gia_tri_khong_thuoc_enum_bi_rong_hoa():
    from apps.taovideo import prefill
    payload = {"prompt": "canh khac",
              "params": {"model": "model-khong-ton-tai",
                        "camera": "medium shot, 35mm, slow push in",
                        "motion": "khong-hop-le", "visual_style": "khong-hop-le"}}
    values = prefill.build_form_values(payload)
    from apps.taovideo import models as _m
    assert values["model"] == _m.DEFAULT_MODEL
    # Payload lech chuan (chu tu do lot qua, du _doan_enum() cua Task 2 le ra
    # phai chan) -> prefill KHONG tu doan lai, chi rong hoa cho an toan form.
    assert values["camera"] == ""
    assert values["motion"] == ""
    assert values["visual_style"] == ""


def test_khong_import_prompt_ai_ommi():
    import ast
    import pathlib
    src = pathlib.Path("apps/taovideo/prefill.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    for node in ast.walk(cay):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("apps.prompt_ai_ommi")
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("apps.prompt_ai_ommi")
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Chạy: `python -m pytest tests/test_5150_taovideo_prefill_values.py -q`
Kỳ vọng: FAIL — `ModuleNotFoundError: apps.taovideo.prefill`.

- [ ] **Step 3: Viết cài đặt**

```python
# apps/taovideo/prefill.py
"""prefill.py — payload giao bai (da la dict JSON, JS mang tu prompt_ai_ommi
ve) -> gia tri dien san form taovideo.

⛔ KHONG import apps.prompt_ai_ommi (canh mot chieu prompt_ai_ommi ->
taovideo, spec G-3). Ham o day CHI nhan payload da la dict — khong tu di
lay, khong cham DB/storage. Viec stage anh/video vao upload_sessions nam o
`apps/taovideo/routes.py` (Task 6), khong o day, de file nay test duoc
khong can fixture DB/storage.

Payload["params"]["camera"/"motion"/"visual_style"] da duoc suy tu chu tu
do BANG khop tu khoa o phia ommi (`handoff_stage._doan_enum()`, spec §6.2b)
— o day chi khop LAI theo danh sach enum (phong hera payload sai/gui tay),
KHONG tu doan enum tu chu tu do (chuyen tu do chi lam MOT lan, phia
ommi, de test T-2 "cung canh -> cung enum" chi can dam bao o mot noi).
"""
from __future__ import annotations

# Ban sao CO CHU DICH cua enum trong apps/taovideo/manifest.py:196-198 —
# khong import chi de tranh vong import routes.py<->prefill.py. Neu doi
# enum o manifest.py, sua CA HAI noi (o day va trong
# apps/prompt_ai_ommi/services/handoff_stage.py cua Task 2).
_CAMERA = {"static", "dolly_in", "tracking", "orbit", "aerial", "handheld"}
_MOTION = {"subtle", "dynamic", "cinematic"}
_VISUAL_STYLE = {"realistic", "cinematic", "anime", "product"}


def _snap(value, allowed: set[str]) -> str:
    v = str(value or "").strip()
    return v if v in allowed else ""


def build_form_values(payload: dict) -> dict:
    from apps.taovideo import models as _m

    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    model = str(params.get("model") or "")
    return {
        "prompt": str(payload.get("prompt") or "")[:10000],
        "model": model if model in _m.MODELS else _m.DEFAULT_MODEL,
        "resolution": str(params.get("resolution") or ""),
        "duration": str(params.get("duration") or ""),
        "aspect_ratio": str(params.get("aspect_ratio") or ""),
        "generate_audio": bool(params.get("generate_audio", True)),
        "camera": _snap(params.get("camera"), _CAMERA),
        "motion": _snap(params.get("motion"), _MOTION),
        "visual_style": _snap(params.get("visual_style"), _VISUAL_STYLE),
    }
```

- [ ] **Step 4: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5150_taovideo_prefill_values.py -q`
Kỳ vọng: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add apps/taovideo/prefill.py tests/test_5150_taovideo_prefill_values.py
git commit -m "$(cat <<'EOF'
them apps/taovideo/prefill.py: payload giao bai -> gia tri dien form

Ham thuan, khong DB/storage, khong import apps.prompt_ai_ommi (canh mot
chieu). Enum lech chuan bi rong hoa (khong tu doan lai) — suy enum tu chu
tu do chi lam mot lan duy nhat, phia ommi (handoff_stage._doan_enum()).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `apps/taovideo/routes.py` — nhận vé, stage tham chiếu, nạp vào `/queue`

**Files:**
- Modify: `apps/taovideo/routes.py:179-188` (`page()` — thêm `tu_studio`)
- Modify: `apps/taovideo/routes.py:404-531` (`queue()` — thêm `prefill_upload_ids`)
- Modify: `apps/taovideo/routes.py` (thêm `_stage_prefill_refs` gần `_luu_refs`, và route `POST /prefill`)
- Test: `tests/test_5152_taovideo_prefill_route_and_queue.py`

**Interfaces:**
- Consumes: `apps.taovideo.prefill.build_form_values(payload: dict) -> dict`
  (Task 5); `platform_core.upload_sessions.stage_bytes/owned/promote` (đã có,
  dùng lại nguyên vẹn — xem `_luu_refs` cùng file).
- Produces: `POST /taovideo/prefill` → `{values: {...}, ref_keys: [{upload_id,
  kind, role, handle}]}`; `page()` context thêm `tu_studio_ticket_id: str`.

⚠️ Đây là **duy nhất** nơi payload thô của ommi được xử lý trong `taovideo` —
JS đã tự `fetch()` nó từ `GET /prompt-ai-ommi/api/handoff/{id}/payload` (cùng
gốc, cùng phiên đăng nhập, xem Task 7) và POST nguyên văn sang route này. File
này KHÔNG bao giờ tự gọi sang `/prompt-ai-ommi/...` — nếu thấy mình sắp viết
một lệnh `httpx.get("/prompt-ai-ommi/...")` ở đây, đó là dấu hiệu đang phá
ranh giới app→app, dừng lại.

- [ ] **Step 1: Viết test đỏ — POST /prefill stage ảnh, rồi /queue nạp đúng ref**

```python
# tests/test_5152_taovideo_prefill_route_and_queue.py
"""POST /taovideo/prefill stage anh tu payload; /queue nap dung ref (Pha 2)."""
from __future__ import annotations

import base64
import json
import re

import pytest
from fastapi.testclient import TestClient

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode("ascii")


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tv-prefill.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
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
    uid = tao_nguoi_dung(db, email="tv-prefill@example.com",
                        password="Strong-pass-123", is_verified=True).id
    credit.nap(db, uid, 100_000, ly_do="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "tv-prefill-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "tv-prefill@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/taovideo"}).status_code == 200
    home = client.get("/taovideo")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', home.text).group(1)
    yield client, csrf, uid
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_prefill_stage_anh_roi_queue_nap_dung_ref(api):
    client, csrf, uid = api
    payload = {"prompt": "Canh co @IMG_1", "params": {
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": 5,
        "aspect_ratio": "16:9", "generate_audio": True,
        "camera": "dolly_in", "motion": "cinematic", "visual_style": "cinematic"},
        "refs": [{"kind": "image", "url": PNG_DATA_URL,
                 "role": "reference_image", "handle": "@IMG_1"}],
        "tag_map": {}, "skipped": [], "skipped_over_limit": 0}

    resp = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf, "payload": payload})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["values"]["prompt"] == "Canh co @IMG_1"
    assert data["values"]["camera"] == "dolly_in"
    assert len(data["ref_keys"]) == 1
    upload_id = data["ref_keys"][0]["upload_id"]
    assert data["ref_keys"][0]["handle"] == "@IMG_1"

    submit = client.post("/taovideo/queue", data={
        "csrf_token": csrf, "prompt": "Canh co @IMG_1", "model": "seedance-2.0-mini",
        "resolution": "480p", "duration": "5", "aspect_ratio": "16:9",
        "camera": "dolly_in", "motion": "cinematic", "visual_style": "cinematic",
        "count": "1", "prefill_upload_ids": [upload_id],
        "prefill_roles": ["reference_image"], "prefill_handles": ["@IMG_1"]})
    assert submit.status_code in (200, 303)

    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        job = db.execute(select(Job).where(Job.user_id == uid)
                         .order_by(Job.created_at.desc())).scalars().first()
        assert job is not None
        refs = (job.params or {}).get("refs") or []
        assert any(r.get("handle") == "@IMG_1" and r.get("role") == "reference_image"
                  for r in refs)
    finally:
        try: next(gen)
        except StopIteration: pass
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Chạy: `python -m pytest tests/test_5152_taovideo_prefill_route_and_queue.py -q`
Kỳ vọng: FAIL — 404 trên `/taovideo/prefill`.

- [ ] **Step 3: Thêm `tu_studio` vào `page()`**

Sửa `apps/taovideo/routes.py:179-188`:

```python
@router.get("", response_class=HTMLResponse)
def page(request: Request, status: str = "all", sort: str = "newest",
         model: str = "", aspect: str = "", tu_studio: str = "",
         user: str = Depends(require_login)):
    status = status if status in {"all", "running", "done", "error", "cancelled"} else "all"
    sort = sort if sort in {"newest", "oldest"} else "newest"
    data = _jobs_cua_toi(request, status, sort, model, aspect)
    return _render(request, user, jobs=data["items"], job_counts=data["counts"],
                   prompt_history=data["history"], saved_assets=data["assets"],
                   active_status=status, active_sort=sort,
                   active_model=data["model_filter"], active_aspect=data["aspect_filter"],
                   tu_studio_ticket_id=tu_studio[:64])
```

- [ ] **Step 4: Thêm `_stage_prefill_refs` + route `POST /prefill`**

Thêm ngay sau `_luu_refs` (khoảng dòng 351 hiện tại, trước
`_saved_refs_for_user`):

```python
import base64 as _base64


def _stage_prefill_refs(u_id: str, refs: list) -> list:
    """Giai ma refs cua ve giao bai (anh: data URL) thanh upload_sessions.

    Chi xu ly `kind == "image"` voi `url` dang `data:` — day la duong duy
    nhat `handoff_stage.dung_payload()` (ben ommi) tao ra cho anh (§6.3 rule
    5: da qua `normalize_image`/`image_to_inline`). Video/audio (url dang
    http/duong dan app) khong duoc tu dong stage o Pha 2 — JS hien thong bao
    "mo lien ket de tai ve roi keo tha lai", vi tran chi 3 video va ca nay
    hiem hon nhieu so voi anh.
    """
    from platform_core import upload_sessions
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    storage = get_storage()
    staged = []
    gen = get_session(); db = next(gen)
    try:
        for index, ref in enumerate(refs or []):
            if str(ref.get("kind") or "") != "image":
                continue
            url = str(ref.get("url") or "")
            if not url.startswith("data:"):
                continue
            header, _, b64data = url.partition(",")
            try:
                data = _base64.b64decode(b64data)
            except (ValueError, TypeError):
                continue
            ct = (header.split(";")[0][5:] or "image/png")
            if len(data) > _CAP["image"]:
                continue
            session = upload_sessions.stage_bytes(
                db, storage, user_id=u_id, app_slug=MANIFEST.slug,
                filename=f"prefill-{index}.bin", content_type=ct, data=data,
                max_size=_CAP["image"],
                allowed_types=("image/png", "image/jpeg", "image/webp"))
            staged.append({"kind": "image", "upload_id": session.id,
                          "role": str(ref.get("role") or "reference_image"),
                          "handle": str(ref.get("handle") or "")[:32]})
        db.commit()
        return staged
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/prefill")
async def prefill_apply(request: Request, user: str = Depends(require_login)):
    body = await request.json()
    if not verify_csrf_token(request, str(body.get("csrf_token") or "")):
        return JSONResponse({"error": "Phiên đã hết hạn — tải lại trang."}, status_code=400)
    u = user_hien_tai(request)
    if u is None:
        return JSONResponse({"error": "Cần đăng nhập."}, status_code=403)
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    from apps.taovideo import prefill
    values = prefill.build_form_values(payload)
    ref_keys = _stage_prefill_refs(u.id, payload.get("refs") or [])
    return {"values": values, "ref_keys": ref_keys}
```

- [ ] **Step 5: Chạy lại test, xác nhận `/prefill` xanh nhưng `/queue` vẫn đỏ**

Chạy: `python -m pytest tests/test_5152_taovideo_prefill_route_and_queue.py -q`
Kỳ vọng: FAIL ở đoạn kiểm `job.params.refs` — `/queue` chưa biết
`prefill_upload_ids`.

- [ ] **Step 6: Mở rộng `/queue` để nhận ref đã stage từ prefill**

Sửa chữ ký `queue()` ở `apps/taovideo/routes.py:404-417`, thêm ba tham số
Form mới:

```python
@router.post("/queue", response_class=HTMLResponse)
async def queue(request: Request, csrf_token: str = Form(...), prompt: str = Form(""),
                model: str = Form(""), resolution: str = Form("480p"),
                duration: str = Form("5"), aspect_ratio: str = Form("16:9"),
                generate_audio: str = Form(""), count: str = Form("1"),
                camera: str = Form(""), motion: str = Form(""),
                visual_style: str = Form(""), seed: str = Form(""),
                ref_images: list[UploadFile] = File(default=[]),
                ref_videos: list[UploadFile] = File(default=[]),
                ref_audios: list[UploadFile] = File(default=[]),
                ref_roles: list[str] = Form(default=[]), ref_handles: list[str] = Form(default=[]),
                saved_ref_keys: list[str] = Form(default=[]),
                prefill_upload_ids: list[str] = Form(default=[]),
                prefill_roles: list[str] = Form(default=[]),
                prefill_handles: list[str] = Form(default=[]),
                quote_id: str = Form(""),
                user: str = Depends(require_login)):
```

Ngay sau đoạn `staged_ref_groups = await _luu_refs(...)` (trong khối `try` ở
giữa `queue()`, khoảng dòng 472-474 hiện tại), chèn một bước gộp refs đã
prefill vào **nhóm đầu tiên** — giao bài không hỗ trợ batch (n luôn = 1 ở
luồng này; nếu `count` > 1 khi có prefill, JS ép về 1 ở Task 7):

```python
            staged_ref_groups = await _luu_refs(
                u.id, actual_files, ref_roles, ref_handles,
                copies=n, grouped=True)
            if prefill_upload_ids:
                from platform_core import upload_sessions as _us
                for i, upload_id in enumerate(prefill_upload_ids):
                    session = _us.owned(db, session_id=upload_id, user_id=u.id,
                                        app_slug=MANIFEST.slug)
                    if session is None:
                        continue  # phien het han/da dung — bo qua, khong chan submit
                    role = (prefill_roles[i] if i < len(prefill_roles)
                           else "reference_image")
                    handle = (prefill_handles[i] if i < len(prefill_handles) else "")
                    staged_ref_groups[0].append({
                        "kind": "image", "storage_key": session.staging_key,
                        "upload_id": session.id, "role": role, "handle": handle,
                        "name": session.filename, "content_type": session.content_type,
                        "size": session.actual_size,
                    })
```

⚠️ Đoạn này CHÈN vào khối `try` đã có, KHÔNG tạo khối `try` mới — nếu
`upload_sessions.owned` ném ngoài `ValueError` (không nên, nhưng phòng hờ),
nó vẫn được `except ValueError` bao ngoài bắt như các lỗi refs khác.

- [ ] **Step 7: Chạy lại test, xác nhận xanh**

Chạy: `python -m pytest tests/test_5152_taovideo_prefill_route_and_queue.py -q`
Kỳ vọng: PASS.

- [ ] **Step 8: Chạy toàn bộ test hiện có của `taovideo` để chắc `/queue` cũ không vỡ**

Chạy: `python -m pytest tests/ -k taovideo -q`
Kỳ vọng: tất cả PASS (không có test nào trong `test_2xx`/`test_3xx` hiện có
của taovideo bị đỏ vì tham số Form mới — chúng đều có `default=[]`).

- [ ] **Step 9: Commit**

```bash
git add apps/taovideo/routes.py tests/test_5152_taovideo_prefill_route_and_queue.py
git commit -m "$(cat <<'EOF'
them POST /taovideo/prefill: giai ma ref anh cua ve giao bai, nap vao /queue

JS da tu fetch payload tu prompt_ai_ommi va POST nguyen van sang day —
route nay khong bao gio tu goi sang app khac. Anh data: URL duoc stage qua
upload_sessions nhu file upload thuong; /queue nhan them
prefill_upload_ids/roles/handles va gop vao nhom ref dau tien truoc khi
promote, khong doi hanh vi cua duong nop file/asset da luu cu.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `taovideo.html` — JS lấy vé, gọi prefill, điền form

**Files:**
- Modify: `apps/taovideo/templates/taovideo.html:88-106` (script inline cuối trang)

**Interfaces:**
- Consumes: `GET /prompt-ai-ommi/api/handoff/{id}/payload` (Task 4, gọi từ
  JS, KHÔNG từ Python); `POST /taovideo/prefill` (Task 6).

⚠️ Đây là thay đổi giao diện — theo G-11/CLAUDE.md, xác nhận bằng trình duyệt
thật (Playwright hoặc trình duyệt của phiên), không chỉ đọc mã. Không có test
pytest cho bước này; bước xác minh là Step 3 dưới.

- [ ] **Step 1: Thêm hằng số `data-tu-studio` vào `<body>` và khối JS**

Sửa đầu template (`taovideo.html`, thẻ `<form id="sdform">` ở dòng 22): thêm
thuộc tính dữ liệu để JS đọc được ticket mà không phải parse query string hai
lần:

```html
<form method="post" action="{{ app.route_prefix }}/queue" id="sdform"
      enctype="multipart/form-data" data-tu-studio="{{ tu_studio_ticket_id|default('') }}">
```

- [ ] **Step 2: Thêm khối JS ngay trước thẻ `</script>` đóng cuối cùng (dòng ~106)**

```javascript
(function(){
  var veId = document.getElementById('sdform').dataset.tuStudio || '';
  if (!veId) return;
  var csrfInput = document.querySelector('#sdform [name=csrf_token]') ||
                  document.querySelector('[name=csrf_token]');
  var csrf = csrfInput ? csrfInput.value : '';

  fetch('/prompt-ai-ommi/api/handoff/' + encodeURIComponent(veId) + '/payload',
       {credentials: 'same-origin'})
    .then(function(r){ if (!r.ok) throw new Error('ve khong hop le'); return r.json(); })
    .then(function(payload){
      return fetch('/taovideo/prefill', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({csrf_token: csrf, payload: payload}),
      }).then(function(r){ return r.json(); });
    })
    .then(function(data){
      var v = data.values || {};
      var set = function(name, value){
        var el = document.querySelector('#sdform [name=' + name + ']');
        if (el && value !== '' && value !== null && value !== undefined) el.value = value;
      };
      set('prompt', v.prompt); set('model', v.model);
      set('resolution', v.resolution); set('duration', v.duration);
      set('aspect_ratio', v.aspect_ratio); set('camera', v.camera);
      set('motion', v.motion); set('visual_style', v.visual_style);
      var audio = document.querySelector('#sdform [name=generate_audio]');
      if (audio) audio.checked = !!v.generate_audio;
      var countEl = document.querySelector('#sdform [name=count]');
      if (countEl) { countEl.value = '1'; countEl.dispatchEvent(new Event('change', {bubbles: true})); }
      (data.ref_keys || []).forEach(function(ref){
        var hidden = document.createElement('input');
        hidden.type = 'hidden'; hidden.name = 'prefill_upload_ids'; hidden.value = ref.upload_id;
        document.getElementById('sdform').appendChild(hidden);
        var role = document.createElement('input');
        role.type = 'hidden'; role.name = 'prefill_roles'; role.value = ref.role;
        document.getElementById('sdform').appendChild(role);
        var handle = document.createElement('input');
        handle.type = 'hidden'; handle.name = 'prefill_handles'; handle.value = ref.handle;
        document.getElementById('sdform').appendChild(handle);
      });
      var hint = document.getElementById('promptbox');
      if (hint && (data.ref_keys || []).length) {
        var note = document.createElement('p'); note.className = 'dim';
        note.textContent = 'Đã nạp ' + data.ref_keys.length + ' ảnh tham chiếu từ PROMPT AI — kiểm tra lại trước khi tạo video.';
        hint.appendChild(note);
      }
    })
    .catch(function(){ /* ve het han/da dung — im lang, khach vao tay binh thuong */ });
})();
```

- [ ] **Step 3: Xác minh trên trình duyệt thật (bắt buộc theo CLAUDE.md — GUI)**

Dùng `playwright-cli` skill hoặc Playwright MCP trên `https://app.lttstudios.com`
(sau khi Task 1–6 đã deploy tới môi trường kiểm):
1. Đăng nhập bằng tài khoản test (`khach1.thu`, qua cookie — không gõ mật khẩu).
2. Vào PROMPT AI OMMI, tạo một project có ít nhất một cảnh và một ảnh tham
   chiếu đã gắn binding (Pha 1).
3. Bấm giao bài (hoặc gọi trực tiếp `POST .../handoff/video` qua UI mới nếu
   Pha 3 chưa xong giao diện) và mở `open_url` trả về.
4. Trên trang `taovideo`, xác nhận: prompt (bao gồm đoạn `Camera:
   .../Lighting: .../Mood: ...` ghép cuối) và camera/motion/visual_style đã
   điền sẵn; chip ảnh tham chiếu xuất hiện; **console không có lỗi**;
   **không có network request thất bại**; tải lại trang với cùng
   `?tu_studio=` cũ ⇒ fetch payload trả 409/410 và form vẫn trống (không
   crash trang).
5. Không tuyên bố bước này xong nếu chưa thực sự mở trình duyệt và xem — quy
   tắc toàn cục `CLAUDE.md`.

- [ ] **Step 4: Commit**

```bash
git add apps/taovideo/templates/taovideo.html
git commit -m "$(cat <<'EOF'
them JS tu dien form taovideo tu ve giao bai (?tu_studio=)

Fetch payload tu prompt_ai_ommi, POST sang /taovideo/prefill, dien
prompt/camera/motion/visual_style va nap anh tham chieu da stage thanh
input an de /queue nhan nhu file thuong. Ve het han/da dung -> im lang,
khach van dung form tay duoc.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Hàng rào cơ học — cạnh app→app và dải số test

**Files:**
- Test: `tests/test_5155_handoff_stage_taovideo_imports_are_the_five_names.py`

**Interfaces:**
- Consumes: `apps/prompt_ai_ommi/services/handoff_stage.py` (nguồn, đọc bằng
  AST — không import).

- [ ] **Step 1: Viết test đỏ (thật ra sẽ xanh ngay nếu Task 2 làm đúng — đây là lưới hồi quy, không phải TDD dựng tính năng mới)**

```python
# tests/test_5155_handoff_stage_taovideo_imports_are_the_five_names.py
"""handoff_stage.py chi duoc dua vao DUNG 5 ten cua apps.taovideo.refs (G-3b).

Doc bang AST, khong import — mot import them ten thu sau la mot quyet dinh
kien truc phai khai lai o ca hai dau (tools/lint_app_contract.py +
apps/taovideo/__init__.py), khong phai mot tien nghi lam tro trong file nay.
"""
from __future__ import annotations

import ast
import pathlib

CHO_PHEP = {"RefError", "VALID_IMAGE_ROLES", "image_role", "image_to_inline",
           "MAX_INLINE_BYTES", "normalize_image"}


def test_chi_dua_vao_5_ten_da_khai():
    src = pathlib.Path("apps/prompt_ai_ommi/services/handoff_stage.py").read_text(
        encoding="utf-8")
    cay = ast.parse(src)
    dua_vao = set()
    for node in ast.walk(cay):
        if isinstance(node, ast.ImportFrom) and node.module == "apps.taovideo.refs":
            dua_vao |= {alias.name for alias in node.names}
    assert dua_vao, "handoff_stage.py phai import tu apps.taovideo.refs"
    ngoai_bang = dua_vao - CHO_PHEP
    assert not ngoai_bang, f"import ngoai bang cho phep (G-3b): {ngoai_bang}"


def test_khong_import_module_taovideo_khac():
    src = pathlib.Path("apps/prompt_ai_ommi/services/handoff_stage.py").read_text(
        encoding="utf-8")
    cay = ast.parse(src)
    for node in ast.walk(cay):
        module = getattr(node, "module", None) or ""
        if isinstance(node, (ast.Import, ast.ImportFrom)) and "taovideo" in (
                module or "".join(getattr(a, "name", "") for a in
                                  getattr(node, "names", []))):
            assert module in ("apps.taovideo.refs", "apps.taovideo"), (
                f"chi duoc dua vao apps.taovideo.refs, thay bang: {module}")
```

- [ ] **Step 2: Chạy test**

Chạy: `python -m pytest tests/test_5155_handoff_stage_taovideo_imports_are_the_five_names.py -q`
Kỳ vọng: PASS nếu Task 2 làm đúng interface đã khai. Nếu FAIL, sửa lại import
trong `handoff_stage.py` (không sửa test).

- [ ] **Step 3: Chạy hàng rào cơ học thật (không phải pytest) — cần Pha 1 đã merge**

Chạy: `python tools/lint_app_contract.py`
Kỳ vọng: `RESULT: PASS`, 0 ERROR liên quan tới `taovideo`/`prompt_ai_ommi`.

⚠️ Nếu ra ERROR dạng "app này được app khác gọi sang nhưng KHÔNG tự khai bề
mặt" nhắm vào `taovideo`: đó là dấu hiệu Task Pha 1 (G-3b, `APP_DUOC_DUNG_APP`
+ `apps/taovideo/__init__.py::BE_MAT_CONG_KHAI`) **chưa merge** — không sửa gì
ở nhánh Pha 2, quay lại mục "Giả định phụ thuộc Pha 1" đầu plan này, báo và
chờ.

- [ ] **Step 4: Chạy `check_so_test.py` xác nhận không trùng số**

Chạy: `python tools/check_so_test.py --list`
Xác nhận không có số nào ngoài {5132, 5133, 5134, 5135, 5136, 5137, 5140,
5141, 5142, 5150, 5152, 5155} bị trùng với test đã có trong cây (đặc biệt
KHÔNG đụng `5130`/`5131` — của Pha 1).

- [ ] **Step 5: Commit**

```bash
git add tests/test_5155_handoff_stage_taovideo_imports_are_the_five_names.py
git commit -m "$(cat <<'EOF'
them luoi AST: handoff_stage.py chi dua vao 5 ten cua apps.taovideo.refs

Bo sung cho tools/lint_app_contract.py (chay thu cong, khong phai pytest):
mot test nhanh, khong can Pha 1 da merge, bat duoc ngay trong phien mot
import them ten ma khong can cho toi luc chay lint that.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Chạy toàn bộ cụm sau khi xong 8 Task

```
python -m pytest tests/test_5138_ommi_handoff_table.py tests/test_5139_handoff_stage_missing_file.py tests/test_5134_handoff_stage_deleted_variant.py tests/test_5135_handoff_stage_renumber_and_limits.py tests/test_5136_handoff_stage_oversize_after_normalize.py tests/test_5137_handoff_stage_camera_prompt_and_enum.py tests/test_5140_handoff_stage_ticket_lifecycle.py tests/test_5141_handoff_route_video_ticket.py tests/test_5142_handoff_route_ownership_and_single_use.py tests/test_5150_taovideo_prefill_values.py tests/test_5152_taovideo_prefill_route_and_queue.py tests/test_5155_handoff_stage_taovideo_imports_are_the_five_names.py tests/test_130_prompt_ai_ommi.py -q
```

⛔ KHÔNG chạy `gate.py` sau plan này (G-13/hợp đồng §4 — gate chỉ chạy MỘT lần
ở cuối Pha 5). Gộp `main`: test nhắm xanh là đủ, rồi `pre-commit run --all-files`.

## Tự soát

**1. Phủ spec:** X-1 (đủ ảnh + camera/lighting/mood) → Task 2 (chi tiết tự do
ghép nguyên văn vào prompt) + Task 4 Step 1 (test khẳng định
`"dolly in, slow push" in body["prompt"]`). §6.2 hình dạng payload → Task 2
`dung_payload()` trả đúng 6 khoá. §6.2b enum đóng + hai đường song song →
Task 2 Step 11 (2 test bắt buộc: giữ nguyên văn + tất định qua hai lần gọi).
§6.3 5 quy tắc renumber → Task 2 Step 1/5/7/9 (rule 3 mất tệp, rule 2 xoá
hẳn, rule 1+4 renumber+bracket, rule 5 tái dùng `refs.py`). Trần 9+3 → Task 2
Step 7. §8 bất biến biên (đã thêm `has_binding`) → Task 2 tính
`has_binding = bool(bindings)` rồi truyền vào lời gọi. Vé dùng một lần/30
phút → Task 3. G-3b hai đầu → Task 8 + phần "Giả định phụ thuộc Pha 1".
`handoff-batch/image` giữ nguyên → Task 4 (không chạm hàm đó). Prefill không
import ngược → Task 5 test 3 + Global Constraints.

**2. Quét placeholder:** không còn "TBD"/"tương tự Task N"/"xử lý lỗi phù
hợp" trong plan này — mọi Step viết mã đều có khối mã Python/JS thật, kể cả
nhánh lỗi (409/410/404, `RefError`, `VeDaDung`, `VeHetHan`, enum rỗng khi
không khớp từ khoá). Chỗ duy nhất còn một giá trị chưa cứng (`<HEAD_THAT>` ở
Task 1) đã được đánh dấu và giải thích lý do (spec cho phép, migration Pha 1
làm head trôi) kèm lệnh lấy giá trị và bước nhắc thay thế trước khi lưu tệp.

**3. Nhất quán kiểu/tên qua các Task:** `dung_payload(db, *, project, scene,
overrides=None)` (Task 2) được Task 4 gọi đúng chữ ký; lời gọi
`bat_bien_giao_bai(prompt, refs, skipped, has_binding=has_binding)` khớp chữ
ký mới `(*, has_binding: bool = False)` khai ở phần "Giả định phụ thuộc Pha
1"; `tao_ve`/`tim_ve`/`doc_va_tieu_ve` (Task 3) khớp tên dùng ở Task 4;
`build_form_values(payload)` (Task 5) khớp tên Task 6 import; `_TU_KHOA_*`/
`_doan_enum` (Task 2, phía ommi) và `_CAMERA`/`_MOTION`/`_VISUAL_STYLE`/
`_snap` (Task 5, phía taovideo) là **hai bản chép độc lập có chủ đích** —
không phải trùng lặp lỗi, ghi rõ lý do (không import chéo app, không vòng
import module) ở cả hai nơi; `OmmiHandoff` (Task 1) khớp tên Task 3/4 dùng.

## Chỗ spec mâu thuẫn hoặc thiếu (báo lại, không tự quyết định thay chủ dự án)

1. **Không có hàm đọc `ommi_binding` được đặt tên sẵn.** Spec giao
   `services/bindings.py` cho Lane A với mô tả "Sinh/đọc/đồng bộ" nhưng không
   cho chữ ký. Plan này chọn đọc thẳng bảng `OmmiBinding` bằng `select()` ngay
   trong `handoff_stage.py` (ghi rõ là giả định ở Task 2), thay vì gọi qua một
   hàm chưa biết tên của Lane A — giảm khớp nối với một interface chưa tồn
   tại. Nếu Lane A đã có sẵn hàm đọc tương đương khi gộp, nên đổi
   `_hieu_luc_bindings()` sang gọi hàm đó (không đổi chữ ký `dung_payload`).
2. **`ommi_handoff.scene_id` tham chiếu "cảnh" nào không được spec nói rõ** —
   plan này xác định đó là scene NHÚNG trong `AppProject.payload["scenes"]`
   (mô hình `handoff.py` hiện tại đang dùng), không phải bảng `ommi_scene`
   (storyboard ảnh, §4.1). Đã ghi thành một mục riêng đầu plan; cần chủ dự án
   xác nhận trước khi Pha 3 định nghĩa `ommi_brief`/`ommi_scene` có thể đổi
   mô hình này.
3. **Video/audio ref trong payload giao bài không tự động stage ở Pha 2**
   (Task 6 Step 4) — chỉ ảnh (data URL) được tự động chuyển thành file đính
   kèm; video dùng URL (`try_url_for`/route `/f/{key}`) nhưng JS không tự tải
   xuống rồi đính lại. Trần vẫn cho 3 video nhưng trải nghiệm "tự động" chỉ
   đúng bản gốc cho ảnh. Đây là một cắt phạm vi có chủ đích (ảnh là ca chính,
   video hiếm và không có test bắt buộc nào yêu cầu) — nêu để chủ dự án quyết
   có cần nâng lên Pha 2 hay để lại Pha 3+.
4. **`POST /api/projects/{pid}/handoff/video` không thu credit/giữ chỗ**
   (không có `credit.giu_cho`) vì job thật do khách tự nộp ở `taovideo/queue`
   (đã có giữ-chỗ/quyết-toán riêng của `taovideo`). G-9 (giữ chỗ→quyết
   toán→hoàn) coi như không áp dụng cho hành động "dựng vé" — chỉ áp dụng ở
   nơi thật sự tạo job. Ghi rõ trong bảng Global Constraints để tránh hiểu
   nhầm là thiếu sót.
5. **Danh sách enum `camera`/`motion`/`visual_style` bị CHÉP THÀNH LITERAL ở
   hai nơi** (`handoff_stage.py` phía ommi để suy enum, `prefill.py` phía
   taovideo để khớp lại) thay vì có một nguồn chân lý duy nhất — hệ quả trực
   tiếp của G-3b (chỉ 5 tên của `apps.taovideo.refs` được phép import từ phía
   ommi, không được import `apps.taovideo.manifest`). Nếu `taovideo` đổi bộ
   enum, CẢ HAI nơi phải sửa tay và không có gate nào tự bắt lệch — đề xuất
   cho chủ dự án: cân nhắc thêm một test hồi quy ở Pha sau so sánh trực tiếp
   `apps.taovideo.manifest`'s `params_schema` enum với các literal này (test
   đó buộc phải nằm ở phía `taovideo` hoặc ở một tệp trung lập ngoài cả hai
   app, vì `ommi` không được import `manifest.py`).
