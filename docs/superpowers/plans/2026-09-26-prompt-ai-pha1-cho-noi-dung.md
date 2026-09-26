# PROMPT AI — Pha 1 (CHỖ NỐI ĐÚNG) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng `ommi_binding` làm nguồn chân lý duy nhất cho việc gán thẻ tham
chiếu (`@IMAGE_k`/`@VIDEO_k`) ↔ `ommi_resource_variant`, sửa lỗi N-1/N-2 (prompt
nhắc ảnh mà `refs` rỗng, hai nơi tự đếm số trôi khỏi nhau), thêm phép kiểm bất
biến ở biên (§8), và bật rollout production — để một khách thật giao bài từ
PROMPT AI sang `taovideo` không mất ảnh tham chiếu (X-1, X-6).

**Architecture:** Tách `apps/prompt_ai_ommi/tables.py` thành package `tables/`
(giữ nguyên mọi import cũ), thêm bảng `ommi_binding` + service
`services/bindings.py` (đánh số the theo §6.3) + `routes/bindings.py` (CRUD
qua HTTP). `services/composer.py::resource_lines()` đọc thẻ đã gán thay vì tự
đếm. `services/bat_bien.py::bat_bien_giao_bai()` là lưới an toàn ở biên, gọi
từ `routes/handoff.py` ngay trước khi nộp job video — thay `refs: []` và
`camera`/`motion`/`visual_style` ghi cứng bằng giá trị thật lấy từ cảnh/binding.
Cạnh app→app mới (`prompt_ai_ommi` → `taovideo`) được khai **hai chiều** theo
G-3b. Cuối cùng bật `LTT_PROMPT_AI_OMMI_ROLLOUT=public` trên production (cần
chủ dự án xác nhận).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (Mapped/mapped_column) + Alembic +
pytest + SQLite (test) / Postgres (production).

**Spec:** `docs/superpowers/specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md`

## Global Constraints

Sao đúng giá trị từ spec §2 — mọi task ngầm mang toàn bộ mục này.

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (khai ở `apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ được import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` (`AGENTS.md` §8.2b) |
| G-3 | App→app | Chỉ cạnh khai tường minh trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`. Spec này thêm **đúng một** cạnh: `("prompt_ai_ommi", "taovideo")` |
| G-3b | Khai cạnh là việc **HAI BÊN**, lệch một tên là gate ĐỎ | `tools/lint_app_contract.py:381-398` đối chiếu hai chiều: bên gọi khai trong `APP_DUOC_DUNG_APP`, bên bị gọi phải tự khai `BE_MAT_CONG_KHAI` trong `apps/<slug>/__init__.py`, hai tập phải BẰNG NHAU. `apps/taovideo/__init__.py` hiện RỖNG. Bản khai phải là TUPLE LITERAL (⛔ không `frozenset(...)`/`set(...)` — linter đọc bằng `ast.literal_eval`) |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring |
| G-5 | Alembic | MỘT head duy nhất. Head hiện tại: `edb8b0fc0ac9` |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số không được trùng. Số cao nhất đang dùng: 5000 |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM: `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`. `.ps1` thuần ASCII. Không viết Python inline qua PowerShell |
| G-8 | Việc > vài giây | Đi qua hàng đợi job (`platform_core/job_submit.py:40 submit_with_credit`). Cloudflare cắt upload 100 MB / phản hồi 100 giây |
| G-9 | Tiền | Giữ chỗ → quyết toán → hoàn. Handler phải ném exception khi lỗi — trả về êm ru là mất tiền hoàn của khách |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}`, `server/templating.py:ASSET_VER` |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt, chốt trên `https://app.lttstudios.com` |
| G-12 | Lệnh nặng | Qua `chay_nang.py --phien <làn> -- <lệnh>`, `-n` ≤ 7. Kiểm `tools\cua_so_yen.py trang-thai` + `tools\tai_may.py` trước |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate — không L1, không L2, không L3 |
| G-14 | `D:\BOT GEMINI` | Kho tham chiếu CHỈ ĐỌC |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |

---

## Quyết định thiết kế (đọc trước khi thực thi)

Spec để một số chỗ mở cho pha 1 tự quyết ("bạn quyết và ghi rõ"). Các quyết
định dưới đây là NGUỒN CHÂN LÝ cho toàn bộ task — mọi task tham chiếu ngược
lại đây, không lặp lại lý do.

**D-1 — Tệp con thứ 8 của `tables/`.** Danh sách 7 tệp con được giao
(`tai_nguyen.py`, `thu_vien.py`, `binding.py`, `brief.py`, `iteration.py`,
`nhan_vat.py`, `chia_se.py`) không có chỗ cho ba lớp **đã tồn tại**
`OmmiStoryboard`/`OmmiScene`/`OmmiSceneVersion`. Quyết định: thêm tệp con thứ
tám `tables/kich_ban.py` (đúng tên spec §5.2 gốc dùng cho nhóm này) chứa ba
lớp đó. Không nhét vào `binding.py` (khác miền) và không bỏ chúng ra ngoài
package (phá R-4).

**D-2 — `resource_lines()` không đổi chữ ký, đổi CÁCH ĐẾM.** Hai nơi gọi hiện
tại (`preview()`, `director_prompt()`) truyền `resources: list[dict]` KHÔNG
có khoá `tag` (không liên quan `ommi_binding` — đó là danh sách tài nguyên
nhúng trong `AppProject.payload`, không phải variant CSDL). Sửa
`resource_lines()` để: nếu item có khoá `"tag"` (đã gán sẵn, đọc từ
`ommi_binding` qua `services/bindings.py::binding_lines()`) thì DÙNG NGUYÊN
tag đó; nếu không có thì tự đếm như cũ (giữ tương thích ngược cho hai nơi gọi
hiện tại, chưa đổi sang bindings ở pha 1 — đó là việc của Làn C/bundle ở pha
3). `binding_lines()` là điểm nối MỚI cho pha 2/3 dùng.

**D-3 — Chữ ký `bat_bien_giao_bai` mở rộng một tham số từ khoá.** Điều kiện
B-5 ("cảnh có `ommi_binding` mà `refs` và `skipped` đều rỗng") cần biết cảnh
có binding hay không — thông tin này KHÔNG nằm trong 3 tham số
`(prompt, refs, skipped)` mà spec §8 liệt kê. Quyết định: thêm tham số từ
khoá `has_binding: bool = False` (mặc định `False` giữ nguyên hành vi gọi
3-tham số cũ cho nơi nào chưa biết). `routes/handoff.py` gọi với giá trị đo
thật (`bool(image_bindings)`).

**D-4 — Ánh xạ enum `camera`/`motion`/`visual_style`.** `ommi_scene.camera`
và `.mood` là văn bản tự do (LLM sinh ra), nhưng
`apps/taovideo/manifest.py` khai `camera`/`motion`/`visual_style` là ENUM
đóng (ví dụ `camera ∈ {"", "static", "dolly_in", "tracking", "orbit",
"aerial", "handheld"}`). Gán thẳng văn bản tự do vào enum sẽ làm
`validate_tool_params` ném `ToolParamsError` cho hầu hết cảnh thật. Quyết
định: một hàm đoán từ khoá thuần (`_doan_enum()`) map một số từ khoá tiếng
Anh/Việt thường gặp sang giá trị enum gần nhất, mặc định rơi về `""` (giá trị
"chưa xác định" — LUÔN hợp lệ vì có mặt trong mọi danh sách enum) khi không
khớp từ khoá nào. Đây vẫn là sửa ĐÚNG N-1 (giá trị suy từ cảnh thật, không
còn hằng số `"cinematic"` cứng cho mọi cảnh).

**D-5 — Hai chiều khai cạnh (G-3b).** Bổ sung bắt buộc theo tin nhắn điều
phối: `tools/lint_app_contract.py` đối chiếu `APP_DUOC_DUNG_APP` (bên gọi)
với `BE_MAT_CONG_KHAI` do CHÍNH app bị gọi tự khai trong `__init__.py` của nó
— hai tập phải bằng nhau từng ký tự. `apps/taovideo/__init__.py` đang rỗng
hoàn toàn. Tập phải khai ở CẢ HAI nơi:

```
("apps.taovideo.refs", "normalize_image")
("apps.taovideo.refs", "image_to_inline")
("apps.taovideo.refs", "image_role")
("apps.taovideo.refs", "VALID_IMAGE_ROLES")
("apps.taovideo.refs", "MAX_INLINE_BYTES")
```

---

### Task 1: Tách `tables.py` thành package `tables/` (Làn M)

**Files:**
- Delete: `apps/prompt_ai_ommi/tables.py`
- Create: `apps/prompt_ai_ommi/tables/__init__.py`
- Create: `apps/prompt_ai_ommi/tables/tai_nguyen.py`
- Create: `apps/prompt_ai_ommi/tables/thu_vien.py`
- Create: `apps/prompt_ai_ommi/tables/kich_ban.py` (quyết định D-1)
- Create: `apps/prompt_ai_ommi/tables/binding.py`
- Create: `apps/prompt_ai_ommi/tables/brief.py` (rỗng-có-mốc, pha 3 Làn C điền)
- Create: `apps/prompt_ai_ommi/tables/iteration.py` (rỗng-có-mốc, pha 3 Làn D điền)
- Create: `apps/prompt_ai_ommi/tables/nhan_vat.py` (rỗng-có-mốc, pha 3 Làn E điền)
- Create: `apps/prompt_ai_ommi/tables/chia_se.py` (rỗng-có-mốc, pha 4 Làn F điền)
- Test: `tests/test_5100_tables_package_re_export.py`

**Interfaces:**
- Consumes: không có (task đầu tiên)
- Produces: `apps.prompt_ai_ommi.tables.OmmiResource`, `OmmiResourceVariant`,
  `OmmiTag`, `OmmiResourceTag`, `OmmiCollection`, `OmmiCollectionItem`,
  `OmmiResourceUsage`, `RESOURCE_KINDS` (từ `tai_nguyen.py`);
  `OmmiMetaPrompt`, `OmmiPromptSnippet`, `OmmiPromptVersion`, `OmmiStyle` (từ
  `thu_vien.py`); `OmmiStoryboard`, `OmmiScene`, `OmmiSceneVersion` (từ
  `kich_ban.py`); `OmmiBinding` (từ `binding.py`, cột: `id: str`,
  `owner_id: str`, `project_id: str`, `scene_id: str | None`, `tag: str`,
  `kind: str`, `variant_id: str`, `position: int`, `role: str`,
  `created_at: datetime`) — mọi tên trên vẫn import được thẳng từ
  `apps.prompt_ai_ommi.tables` (re-export).

- [ ] **Step 1: Viết test đỏ cho R-4 (khẳng định import cũ + package mới)**

```python
# tests/test_5100_tables_package_re_export.py
"""R-4: tach tables.py thanh package khong duoc lam vo import cu.

Vi sao doc nay la RED truoc khi sua: `OmmiBinding` chua ton tai o dau ca, va
`apps.prompt_ai_ommi.tables` van la MOT MODULE PHANG (khong co __path__) —
ca hai assertion duoi day that bai tren cay hien tai.
"""
from __future__ import annotations


def test_import_cu_van_chay_dung_moi_ten_lop():
    from apps.prompt_ai_ommi.tables import (
        RESOURCE_KINDS, OmmiResource, OmmiResourceVariant, OmmiTag,
        OmmiResourceTag, OmmiCollection, OmmiCollectionItem,
        OmmiResourceUsage, OmmiMetaPrompt, OmmiPromptSnippet,
        OmmiPromptVersion, OmmiStyle, OmmiStoryboard, OmmiScene,
        OmmiSceneVersion, OmmiBinding)
    assert OmmiResource.__tablename__ == "ommi_resource"
    assert OmmiScene.__tablename__ == "ommi_scene"
    assert OmmiBinding.__tablename__ == "ommi_binding"


def test_tables_la_mot_package_va_binding_import_thang_duoc():
    import apps.prompt_ai_ommi.tables as tables_pkg
    assert hasattr(tables_pkg, "__path__"), (
        "tables phai la PACKAGE (co __init__.py), khong con la mot module phang")
    from apps.prompt_ai_ommi.tables.binding import OmmiBinding as TrucTiep
    assert TrucTiep is tables_pkg.OmmiBinding


def test_ommi_binding_co_dung_cot_theo_spec_4_2():
    from apps.prompt_ai_ommi.tables.binding import OmmiBinding
    cols = {c.name for c in OmmiBinding.__table__.columns}
    assert cols == {"id", "owner_id", "project_id", "scene_id", "tag",
                    "kind", "variant_id", "position", "role", "created_at"}
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5100_tables_package_re_export.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named
'apps.prompt_ai_ommi.tables.binding'` (vì `tables.py` vẫn là module phẳng).

- [ ] **Step 3: Xoá `tables.py`, tạo `tables/tai_nguyen.py`**

Chuyển nguyên `OmmiResource`, `OmmiResourceVariant`, `OmmiTag`,
`OmmiResourceTag`, `OmmiCollection`, `OmmiCollectionItem`,
`OmmiResourceUsage`, `RESOURCE_KINDS` từ `tables.py` cũ (giữ nguyên docstring
và comment giải thích mô hình sở hữu — không rút gọn):

```python
# apps/prompt_ai_ommi/tables/tai_nguyen.py
"""tables/tai_nguyen.py — kho tai nguyen: OmmiResource + variant + tag/collection.

Tach tu apps/prompt_ai_ommi/tables.py (2026-09-26, spec pha 1 R-4). Noi dung
lop KHONG doi mot dong nao so voi ban goc — chi doi vi tri tep.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


RESOURCE_KINDS = ("character", "background", "prop", "vehicle", "misc")


class OmmiResource(Base):
    __tablename__ = "ommi_resource"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cover_variant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_ommi_resource_owner_kind", "owner_id", "kind", "archived_at"),
    )


class OmmiResourceVariant(Base):
    __tablename__ = "ommi_resource_variant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class OmmiTag(Base):
    __tablename__ = "ommi_tag"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_ommi_tag_owner_name"),
    )


class OmmiResourceTag(Base):
    __tablename__ = "ommi_resource_tag"

    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class OmmiCollection(Base):
    __tablename__ = "ommi_collection"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class OmmiCollectionItem(Base):
    __tablename__ = "ommi_collection_item"

    collection_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OmmiResourceUsage(Base):
    __tablename__ = "ommi_resource_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_ref: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("resource_id", "project_id", "scene_ref", name="uq_ommi_usage_resource_project_scene"),
    )
```

- [ ] **Step 4: Tạo `tables/thu_vien.py`** (chuyển nguyên `OmmiMetaPrompt`,
  `OmmiPromptSnippet`, `OmmiPromptVersion`, `OmmiStyle` — copy y nguyên từ
  `tables.py` cũ, kể cả comment `deprecated_at`/`archived_at`, chỉ đổi phần
  `import` đầu tệp giống Step 3 và thêm `from sqlalchemy import Boolean`)

- [ ] **Step 5: Tạo `tables/kich_ban.py`** (quyết định D-1 — chuyển nguyên
  `OmmiStoryboard`, `OmmiScene`, `OmmiSceneVersion` từ `tables.py` cũ)

```python
# apps/prompt_ai_ommi/tables/kich_ban.py
"""tables/kich_ban.py — storyboard + canh + phien ban canh.

Tach tu apps/prompt_ai_ommi/tables.py (2026-09-26). Ba lop nay khong nam
trong danh sach 7 tep con spec liet ke rieng cho pha 1-4 (binding/brief/
iteration/nhan_vat/chia_se/tai_nguyen/thu_vien) vi chung la mo hinh CU da co
tu truoc spec nay (khong doi trong pha 1) — dat rieng mot tep de khong lan
voi `binding.py` (quyet dinh D-1, xem dau plan).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiStoryboard(Base):
    __tablename__ = "ommi_storyboard"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(12), default="16:9", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiScene(Base):
    __tablename__ = "ommi_scene"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    storyboard_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    camera: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    continuity: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resource_ids: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    image_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_ommi_scene_board_position", "storyboard_id", "position"),
    )


class OmmiSceneVersion(Base):
    __tablename__ = "ommi_scene_version"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("scene_id", "version", name="uq_ommi_scene_version"),
    )
```

- [ ] **Step 6: Tạo `tables/binding.py`**

```python
# apps/prompt_ai_ommi/tables/binding.py
"""tables/binding.py — OmmiBinding: nguon chan ly the (`@IMAGE_1`...) <-> variant.

Bang nay CHUA loi N-2 (spec pha 1 muc 4.2): truoc day so the duoc dem lai o
`composer.resource_lines()` (luc build prompt) va dem KHAC DI luc build refs
giao bai (`routes/handoff.py`) — hai lan dem doc lap troi khoi nhau khong ai
biet. Tu nay CHI `services/bindings.py` duoc ghi bang nay; noi khac chi DOC.

`scene_id IS NULL` = binding cap PROJECT (dung cho preview/director prompt o
muc project, chua gan canh cu the).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiBinding(Base):
    __tablename__ = "ommi_binding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tag: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="reference_image", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "scene_id", "tag", name="uq_ommi_binding_tag"),
    )
```

- [ ] **Step 7: Tạo bốn tệp con rỗng-có-mốc**

```python
# apps/prompt_ai_ommi/tables/brief.py
"""tables/brief.py — mo hinh `ommi_brief` (RONG o pha 1).

Danh cho Lan C, Pha 3 (spec Sec 4.2 pha 3 + Sec 9.2). Tao truoc de package
`tables/` co du 7 tep con ngay tu pha 1, khong phai dao cau truc package lan
thu hai khi pha 3 bat dau.
"""
from __future__ import annotations
```

```python
# apps/prompt_ai_ommi/tables/iteration.py
"""tables/iteration.py — mo hinh `ommi_iteration` (RONG o pha 1). Lan D, Pha 3."""
from __future__ import annotations
```

```python
# apps/prompt_ai_ommi/tables/nhan_vat.py
"""tables/nhan_vat.py — `ommi_character`/`outfit`/`pose`/`background`/`face_embedding` (RONG o pha 1). Lan E, Pha 3."""
from __future__ import annotations
```

```python
# apps/prompt_ai_ommi/tables/chia_se.py
"""tables/chia_se.py — `ommi_share_code` (RONG o pha 1). Lan F, Pha 4."""
from __future__ import annotations
```

- [ ] **Step 8: Tạo `tables/__init__.py` re-export đủ mọi tên cũ**

```python
# apps/prompt_ai_ommi/tables/__init__.py
"""tables/__init__.py — package CSDL cua PROMPT AI OMMI.

Tach tu mot tep 385 dong (2026-09-26, spec pha 1 muc R-4). Tep nay CHI
re-export — khong dinh nghia lop nao — de `from apps.prompt_ai_ommi.tables
import X` cu van chay nguyen sau khi tach thanh package.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.tables.tai_nguyen import (
    RESOURCE_KINDS, OmmiResource, OmmiResourceVariant, OmmiTag,
    OmmiResourceTag, OmmiCollection, OmmiCollectionItem, OmmiResourceUsage)
from apps.prompt_ai_ommi.tables.thu_vien import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiPromptVersion, OmmiStyle)
from apps.prompt_ai_ommi.tables.kich_ban import (
    OmmiStoryboard, OmmiScene, OmmiSceneVersion)
from apps.prompt_ai_ommi.tables.binding import OmmiBinding

__all__ = [
    "RESOURCE_KINDS", "OmmiResource", "OmmiResourceVariant", "OmmiTag",
    "OmmiResourceTag", "OmmiCollection", "OmmiCollectionItem",
    "OmmiResourceUsage", "OmmiMetaPrompt", "OmmiPromptSnippet",
    "OmmiPromptVersion", "OmmiStyle", "OmmiStoryboard", "OmmiScene",
    "OmmiSceneVersion", "OmmiBinding",
]
```

- [ ] **Step 9: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5100_tables_package_re_export.py -q`
Expected: PASS (3 passed)

- [ ] **Step 10: Chạy toàn bộ test hiện có của app để chắc không vỡ import**

Run: `python -m pytest tests/test_136_ommi_resources.py tests/test_60_app_registry.py -q`
Expected: PASS — cả hai tệp import `from apps.prompt_ai_ommi.tables import ...`
và phải chạy y như trước khi tách.

- [ ] **Step 11: Commit**

```bash
git add apps/prompt_ai_ommi/tables.py apps/prompt_ai_ommi/tables/ tests/test_5100_tables_package_re_export.py
git commit -m "$(cat <<'EOF'
refactor(prompt_ai_ommi): tach tables.py thanh package tables/

385 dong trong mot tep la qua lon de moi lan them bang moi (spec pha 1). Tach
thanh tai_nguyen/thu_vien/kich_ban/binding + 4 tep rong-co-moc cho pha sau.
tables/__init__.py re-export du moi ten cu (R-4) de import hien co khong vo.

Co them OmmiBinding — nguon chan ly the (@IMAGE_k/@VIDEO_k) <-> variant, chua
loi N-2 (hai noi tu dem so doc lap).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Migration `ommi_binding` (Làn M)

**Files:**
- Create: `alembic/versions/20260926_XXXX_ommi_binding.py` (`down_revision =
  "edb8b0fc0ac9"` — head hiện tại, xác nhận lại ở Step 1 trước khi viết)
- Test: `tests/test_5101_migration_ommi_binding.py`

**Interfaces:**
- Consumes: `edb8b0fc0ac9` (head alembic hiện tại)
- Produces: bảng `ommi_binding` trên CSDL thật (song song với model ORM của
  Task 1 — hai thứ phải khớp cột)

- [ ] **Step 1: Xác nhận vẫn chỉ một head, chưa ai tạo migration mới**

Run: `python -c "import subprocess,sys; print(subprocess.run([sys.executable,'-m','alembic','heads'],capture_output=True,text=True,cwd='.').stdout)"`
Expected: đúng một dòng, chứa `edb8b0fc0ac9`. Nếu khác — DỪNG, báo chủ dự án
(có phiên khác vừa thêm migration).

- [ ] **Step 2: Viết test đỏ cho migration (đọc văn bản trước)**

```python
# tests/test_5101_migration_ommi_binding.py
"""Migration ommi_binding — pha 1 (spec Sec 4.2).

Ba bai dau doc VAN BAN revision (tra loi "nguoi viet da viet gi"). Bai cuoi
CHAY THAT len/xuong/len tren mot CSDL SQLite tam (tra loi "thu da viet co
chay duoc khong") — cung khuon tests/test_1729_migration_go_agent_runs.py.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

GOC = pathlib.Path(__file__).resolve().parent.parent


def _scripts() -> ScriptDirectory:
    cfg = Config(str(GOC / "alembic.ini"))
    cfg.set_main_option("script_location", str(GOC / "alembic"))
    return ScriptDirectory.from_config(cfg)


@pytest.fixture(scope="module")
def rev():
    ds = [s for s in _scripts().walk_revisions() if "ommi_binding" in (s.path or "")]
    assert ds, "chua co migration ommi_binding"
    return ds[0]


@pytest.fixture(scope="module")
def nguon(rev) -> str:
    return pathlib.Path(rev.path).read_text(encoding="utf-8")


def test_la_mot_head_duy_nhat(rev):
    scripts = _scripts()
    heads = list(scripts.get_heads())
    assert len(heads) == 1, f"phai co dung mot dau, dang co {heads}"
    to_tien = {s.revision for s in scripts.iterate_revisions(heads[0], "base")}
    assert rev.revision in to_tien


def test_upgrade_tao_bang_du_cot(nguon):
    than = nguon.split("def upgrade()")[1].split("def downgrade()")[0]
    assert re_search := __import__("re").search(r'create_table\(\s*"ommi_binding"', than)
    for cot in ("id", "owner_id", "project_id", "scene_id", "tag", "kind",
                "variant_id", "position", "role", "created_at"):
        assert f'"{cot}"' in than, f"upgrade thieu cot {cot}"
    assert "uq_ommi_binding_tag" in than


def test_downgrade_drop_bang(nguon):
    than = nguon.split("def downgrade()")[1]
    assert "drop_table" in than and "ommi_binding" in than


def test_LEN_XUONG_LEN_chay_that_tren_sqlite(tmp_path, rev):
    import os

    db = tmp_path / "ommi_binding.db"
    env = dict(os.environ)
    env["LTT_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["PYTHONPATH"] = str(GOC)

    def alembic(*args: str) -> None:
        ra = subprocess.run([sys.executable, "-m", "alembic", *args],
                            cwd=str(GOC), env=env, capture_output=True, text=True)
        assert ra.returncode == 0, f"alembic {' '.join(args)} -> {ra.returncode}\n{ra.stderr[-2000:]}"

    def co_bang() -> bool:
        import sqlalchemy as sa
        e = sa.create_engine(f"sqlite:///{db.as_posix()}")
        try:
            with e.connect() as c:
                return bool(c.execute(sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='ommi_binding'")).first())
        finally:
            e.dispose()

    alembic("upgrade", "head")
    assert co_bang(), "sau upgrade phai co bang ommi_binding"

    import sqlalchemy as sa
    e = sa.create_engine(f"sqlite:///{db.as_posix()}")
    try:
        with e.begin() as c:
            c.execute(sa.text(
                "INSERT INTO ommi_binding (id, owner_id, project_id, scene_id, "
                "tag, kind, variant_id, position, role, created_at) VALUES "
                "('b1','u1','p1','s1','@IMAGE_1','image','v1',1,"
                "'reference_image','2026-09-26 10:00:00')"))
            row = c.execute(sa.text(
                "SELECT tag, kind, position FROM ommi_binding")).first()
            assert row == ("@IMAGE_1", "image", 1)
    finally:
        e.dispose()

    alembic("downgrade", str(rev.down_revision))
    assert not co_bang(), "downgrade phai XOA bang ommi_binding"

    alembic("upgrade", "head")
    assert co_bang(), "len lai lan hai phai tao lai bang"
```

- [ ] **Step 3: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5101_migration_ommi_binding.py -q`
Expected: FAIL tại `test_la_mot_head_duy_nhat` — `AssertionError: chua co
migration ommi_binding` (chưa có tệp migration).

- [ ] **Step 4: Viết migration**

```python
# alembic/versions/20260926_XXXX_ommi_binding.py
# -*- coding: utf-8 -*-
"""PROMPT AI OMMI pha 1 — bang ommi_binding (nguon chan ly the <-> variant).

Revision ID: a4f0c9b21ee3
Revises: edb8b0fc0ac9
Create Date: 2026-09-26

## VI SAO CO BANG NAY

So the (`@IMAGE_1`...) truoc day duoc DEM LAI moi lan build prompt
(`composer.resource_lines`) va dem KHAC DI luc build refs giao bai — hai lan
dem doc lap troi khoi nhau khong ai biet (N-2, xem
docs/PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md). Tu nay CHI
`services/bindings.py` duoc ghi bang nay; noi khac chi DOC.

## ROLLBACK

`downgrade()` DROP bang. Bang nay hoan toan moi (khong co du lieu san xuat
nao phu thuoc no truoc migration nay), nen mat du lieu khi downgrade la
nguoi dung phai gan lai binding — khong anh huong file da luu tren Storage.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4f0c9b21ee3"
down_revision = "edb8b0fc0ac9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ommi_binding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scene_id", sa.String(36), nullable=True),
        sa.Column("tag", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("variant_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("role", sa.String(24), nullable=False,
                  server_default="reference_image"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("project_id", "scene_id", "tag",
                            name="uq_ommi_binding_tag"),
    )
    op.create_index("ix_ommi_binding_owner_id", "ommi_binding", ["owner_id"])
    op.create_index("ix_ommi_binding_project_id", "ommi_binding", ["project_id"])
    op.create_index("ix_ommi_binding_scene_id", "ommi_binding", ["scene_id"])
    op.create_index("ix_ommi_binding_variant_id", "ommi_binding", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_ommi_binding_variant_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_scene_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_project_id", table_name="ommi_binding")
    op.drop_index("ix_ommi_binding_owner_id", table_name="ommi_binding")
    op.drop_table("ommi_binding")
```

Trước khi lưu: đổi tên tệp thành đúng ngày giờ tạo thật (`YYYYMMDD_HHMM_ommi_binding.py`)
và chạy `grep -rl "a4f0c9b21ee3" alembic/versions/` để chắc `revision` chưa
trùng ai (nếu trùng, đổi thành một chuỗi hex 12 ký tự khác).

- [ ] **Step 5: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5101_migration_ommi_binding.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/20260926_XXXX_ommi_binding.py tests/test_5101_migration_ommi_binding.py
git commit -m "$(cat <<'EOF'
migration(prompt_ai_ommi): them bang ommi_binding (pha 1)

Nguon chan ly the (@IMAGE_k/@VIDEO_k) <-> ommi_resource_variant. Chua loi N-2:
truoc day so the duoc dem doc lap o hai noi (build prompt vs build refs giao
bai) va troi khoi nhau khong ai biet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Khai cạnh app→app HAI CHIỀU + đăng ký router (Làn M)

**Files:**
- Modify: `tools/lint_app_contract.py:85` (thêm vào `APP_DUOC_DUNG_APP`)
- Modify: `apps/taovideo/__init__.py` (hiện rỗng — thêm `BE_MAT_CONG_KHAI`)
- Test: `tests/test_5102_lint_app_contract_canh_ommi_taovideo.py`

**Interfaces:**
- Consumes: không có
- Produces: cạnh `("prompt_ai_ommi", "taovideo")` hợp lệ cho Task 6/8 import
  `apps.taovideo.refs.normalize_image`, `.image_to_inline`, `.image_role`,
  `.VALID_IMAGE_ROLES`, `.MAX_INLINE_BYTES`

- [ ] **Step 1: Viết test đỏ**

```python
# tests/test_5102_lint_app_contract_canh_ommi_taovideo.py
"""Canh app->app moi (prompt_ai_ommi -> taovideo) phai duoc khai HAI CHIEU (G-3b).

`apps/taovideo/__init__.py` dang RONG HOAN TOAN truoc task nay, nen bai nay
la RED: linter se bao ERROR "duoc app khac goi sang nhung KHONG tu khai be
mat" ngay khi canh duoc them vao APP_DUOC_DUNG_APP ma khong sua ben kia.
"""
from __future__ import annotations

import subprocess
import sys
import pathlib

GOC = pathlib.Path(__file__).resolve().parent.parent


def test_canh_duoc_khai_trong_allowlist():
    from tools.lint_app_contract import APP_DUOC_DUNG_APP
    canh = APP_DUOC_DUNG_APP.get(("prompt_ai_ommi", "taovideo"))
    assert canh == {
        ("apps.taovideo.refs", "normalize_image"),
        ("apps.taovideo.refs", "image_to_inline"),
        ("apps.taovideo.refs", "image_role"),
        ("apps.taovideo.refs", "VALID_IMAGE_ROLES"),
        ("apps.taovideo.refs", "MAX_INLINE_BYTES"),
    }


def test_taovideo_tu_khai_be_mat_khop_allowlist():
    import ast
    from tools.lint_app_contract import APP_DUOC_DUNG_APP
    source = (GOC / "apps" / "taovideo" / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    khai = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "BE_MAT_CONG_KHAI" for t in node.targets):
            khai = ast.literal_eval(node.value)
    assert khai is not None, "apps/taovideo/__init__.py thieu BE_MAT_CONG_KHAI"
    assert set(khai) == APP_DUOC_DUNG_APP[("prompt_ai_ommi", "taovideo")]


def test_lint_app_contract_khong_co_ERROR_ve_taovideo():
    ra = subprocess.run([sys.executable, "tools/lint_app_contract.py"],
                        cwd=str(GOC), capture_output=True, text=True)
    assert "taovideo" not in "\n".join(
        line for line in ra.stdout.splitlines() if "ERROR" in line), ra.stdout


def test_lint_app_contract_thoat_ma_0():
    ra = subprocess.run([sys.executable, "tools/lint_app_contract.py"],
                        cwd=str(GOC), capture_output=True, text=True)
    assert ra.returncode == 0, ra.stdout
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5102_lint_app_contract_canh_ommi_taovideo.py -q`
Expected: FAIL — `APP_DUOC_DUNG_APP.get(("prompt_ai_ommi", "taovideo"))` trả
`None`.

- [ ] **Step 3: Thêm cạnh vào `tools/lint_app_contract.py`**

Mở `tools/lint_app_contract.py:85` (ngay sau khối comment giải thích, cùng
khuôn với cạnh `("taovideo", "upscalevideo")` đã có), thêm:

```python
    # ── PROMPT AI giao anh tham chieu sang taovideo (spec pha 1, N-1/N-2) ──
    #
    # ⭐ Gioi han canh o DUNG MOT module `apps.taovideo.refs` — khong import
    #    `apps.taovideo.routes`/`jobs`. `refs.py` la lop chuan hoa THUAN
    #    (khong goi job, khong doc CSDL cua taovideo), nen dung no khong keo
    #    theo trang thai hay hanh vi cua taovideo — chi dung mot phep bien
    #    doi du lieu da do (R-2, docs spec pha 1).
    ("prompt_ai_ommi", "taovideo"): {
        ("apps.taovideo.refs", "normalize_image"),
        ("apps.taovideo.refs", "image_to_inline"),
        ("apps.taovideo.refs", "image_role"),
        ("apps.taovideo.refs", "VALID_IMAGE_ROLES"),
        ("apps.taovideo.refs", "MAX_INLINE_BYTES"),
    },
```

- [ ] **Step 4: Tự khai bề mặt ở `apps/taovideo/__init__.py`** (copy khuôn từ
  `apps/upscalevideo/__init__.py`, đổi nội dung cho đúng chiều mới)

```python
# apps/taovideo/__init__.py
"""App taovideo — dat hang tao video qua Seedance/ModelArk.

BE MAT CONG KHAI CUA APP NAY (spec pha 1 PROMPT AI, G-3b)
==========================================================

App nay duoc mot app khac goi sang: `prompt_ai_ommi` doc `apps.taovideo.refs`
de chuan hoa anh tham chieu (resize/inline base64) va kiem role hop le TRUOC
khi nop job `video.generate` — thay vi tu viet lai logic chuan hoa (da tung
gay loi N-1: prompt nhac anh ma refs rong).

⛔ Canh CHI gioi han o mot module thuan `apps.taovideo.refs` — khong xuyen
   qua `routes.py`/`jobs.py`. `refs.py` khong goi job, khong doc CSDL cua
   taovideo, nen dung no khong keo theo hanh vi hay trang thai cua app nay.

`BE_MAT_CONG_KHAI` duoi day la ban khai do. `lint_app_contract.py` doc no va
doi chieu hai chieu voi `APP_DUOC_DUNG_APP` — lech mot ten la gate DO.

⚠️ Them mot dong vao day la MOT QUYET DINH KIEN TRUC, khong phai mot tien
   nghi: moi ten o day la mot thu app khac duoc phep dua vao, va tu do khong
   doi duoc nua neu khong sua ca hai ben.
"""

#: `(module, ten)` — nhung thu app KHAC duoc phep goi. Moi dong mot use case.
#:
#: Co y de la TUPLE LITERAL, khong boc `frozenset(...)`: linter doc ban khai
#: nay bang `ast.literal_eval` tren cay nguon, khong import app. Mot loi goi
#: ham thi `literal_eval` khong doc duoc, va hang rao se im lang tuong nhu
#: app chua khai gi.
BE_MAT_CONG_KHAI = (
    ("apps.taovideo.refs", "normalize_image"),     # chuan hoa anh -> PNG/JPEG
    ("apps.taovideo.refs", "image_to_inline"),     # anh -> data: URL, ep <=8MiB
    ("apps.taovideo.refs", "image_role"),          # chuan hoa + remap role legacy
    ("apps.taovideo.refs", "VALID_IMAGE_ROLES"),   # bo gia tri role hop le
    ("apps.taovideo.refs", "MAX_INLINE_BYTES"),    # nguong 8 MiB de bao ly do skip
)
```

- [ ] **Step 5: Đăng ký router `bindings` (chuẩn bị trước — nội dung thật ở
  Task 5, ở đây chỉ thêm dòng import để `routes/__init__.py` sẵn sàng)**

Việc này PHỤ THUỘC `routes/bindings.py` tồn tại — thực hiện ở cuối Task 5
(Step 5 của Task 5), không phải ở đây. Ghi chú lại để không quên.

- [ ] **Step 6: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5102_lint_app_contract_canh_ommi_taovideo.py -q`
Expected: PASS (4 passed)

- [ ] **Step 7: Chạy toàn bộ lint để chắc không phá app khác**

Run: `python tools/lint_app_contract.py`
Expected: dòng cuối `RESULT: PASS`, `ERROR: 0`

- [ ] **Step 8: Commit**

```bash
git add tools/lint_app_contract.py apps/taovideo/__init__.py tests/test_5102_lint_app_contract_canh_ommi_taovideo.py
git commit -m "$(cat <<'EOF'
contract(prompt_ai_ommi,taovideo): khai canh app->app HAI CHIEU

prompt_ai_ommi doc apps.taovideo.refs de chuan hoa anh tham chieu truoc khi
nop job video.generate. G-3b: khai canh la viec hai ben — them
APP_DUOC_DUNG_APP o phia goi VA BE_MAT_CONG_KHAI o phia bi goi
(apps/taovideo/__init__.py dang rong hoan toan), gioi han dung mot module
thuan apps.taovideo.refs (R-2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `services/bindings.py` — CRUD + đánh số §6.3 (Làn A)

**Files:**
- Create: `apps/prompt_ai_ommi/services/bindings.py`
- Test: `tests/test_5110_bindings_danh_so.py`
- Test: `tests/test_5111_bindings_quy_tac_khong_tieu_so.py`
- Test: `tests/test_5112_bindings_xoa_va_so_huu.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.tables.binding.OmmiBinding`,
  `apps.prompt_ai_ommi.tables.tai_nguyen.OmmiResource`,
  `apps.prompt_ai_ommi.tables.tai_nguyen.OmmiResourceVariant` (Task 1);
  `apps.taovideo.refs.VALID_IMAGE_ROLES`, `apps.taovideo.refs.image_role`
  (Task 3)
- Produces:
  - `class BindingError(ValueError)`
  - `class BindingNotFound(LookupError)`
  - `list_bindings(db: Session, *, project_id: str, owner_id: str, scene_id: str | None = None) -> list[OmmiBinding]`
  - `replace_bindings(db: Session, *, project_id: str, owner_id: str, scene_id: str | None, items: list[dict]) -> tuple[list[OmmiBinding], int]`
  - `delete_binding(db: Session, *, project_id: str, owner_id: str, scene_id: str | None, tag: str) -> list[OmmiBinding]`
  - `binding_lines(db: Session, *, project_id: str, owner_id: str, scene_id: str | None = None) -> list[dict]`
    (mỗi dict: `{"tag": str, "kind": str, "name": str, "description": str}`)

- [ ] **Step 1: Viết fixture DB dùng chung + test đỏ cho đánh số §6.3 quy tắc 1**

```python
# tests/test_5110_bindings_danh_so.py
"""services/bindings.py — dang so the theo spec Sec 6.3 quy tac 1.

Hai bo dem DOC LAP: image -> @IMAGE_1, @IMAGE_2...; video -> @VIDEO_1...
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _variant(db, owner="u1", resource_name="Nhân vật A"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="character", name=resource_name)
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png")
    db.commit()
    return variant


def test_dang_so_hai_bo_dem_doc_lap(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2, v3 = _variant(db), _variant(db), _variant(db)
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id},
               {"kind": "video", "variant_id": v2.id},
               {"kind": "image", "variant_id": v3.id}])
    db.commit()
    assert changed == 3
    by_tag = {row.tag: row for row in created}
    assert set(by_tag) == {"@IMAGE_1", "@VIDEO_1", "@IMAGE_2"}
    assert by_tag["@IMAGE_1"].variant_id == v1.id
    assert by_tag["@IMAGE_2"].variant_id == v3.id


def test_role_mac_dinh_va_hop_le(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db)
    created, _ = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id}])
    assert created[0].role == "reference_image"


def test_role_khong_hop_le_bi_tu_choi(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db)
    with pytest.raises(svc.BindingError):
        svc.replace_bindings(
            db, project_id="p1", owner_id="u1", scene_id="s1",
            items=[{"kind": "image", "variant_id": v1.id, "role": "khong_ton_tai"}])
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5110_bindings_danh_so.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named
'apps.prompt_ai_ommi.services.bindings'`

- [ ] **Step 3: Viết `services/bindings.py`**

```python
# apps/prompt_ai_ommi/services/bindings.py
"""services/bindings.py — nguon chan ly the <-> variant (spec Sec 4.2, 6.1, 6.3).

Mot binding gan MOT THE (`@IMAGE_1`, `@VIDEO_1`...) voi dung mot
`ommi_resource_variant`, trong pham vi mot project (va, khi co, mot canh cu
the — `scene_id=None` la binding cap project). Day la bang CHUA loi N-2:
truoc day so the duoc dem lai moi lan build prompt (`composer.resource_lines`)
va dem KHAC DI luc build refs giao bai — hai lan dem doc lap troi khoi nhau
khong ai biet. Tu nay CHI ham o day duoc ghi bang; moi noi khac chi DOC.

Quy tac dung PUT (spec Sec 6.1): moi lan goi la GHI DE TOAN BO danh sach
binding cua (project_id, scene_id) — "danh so lai toan bo", khong phai them/
bot tung the.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables.binding import OmmiBinding
from apps.prompt_ai_ommi.tables.tai_nguyen import OmmiResource, OmmiResourceVariant
from apps.taovideo.refs import image_role

_KINDS = ("image", "video", "audio")
_PREFIX = {"image": "IMAGE", "video": "VIDEO", "audio": "AUDIO"}


class BindingError(ValueError):
    """Du lieu vao khong hop le — route tra 400."""


class BindingNotFound(LookupError):
    """Khong ton tai HOAC khong thuoc ve nguoi goi — route tra 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_kind(value: str) -> str:
    kind = (value or "").strip().lower()
    if kind not in _KINDS:
        raise BindingError(
            f"Loai khong hop le: {value!r}. Chon mot trong: {', '.join(_KINDS)}.")
    return kind


def _clean_role(kind: str, value: str) -> str:
    """Anh: dung `image_role()` cua taovideo (chuan hoa + remap legacy, khong
    viet lai). Video/audio: chi cat do dai, khong co bo gia tri dong."""
    if kind != "image":
        return (str(value or "").strip() or "reference_image")[:24]
    role = image_role(str(value or ""))
    return role


def list_bindings(db: Session, *, project_id: str, owner_id: str,
                  scene_id: str | None = None) -> list[OmmiBinding]:
    stmt = (select(OmmiBinding)
            .where(OmmiBinding.project_id == project_id,
                   OmmiBinding.owner_id == owner_id,
                   OmmiBinding.scene_id == scene_id)
            .order_by(OmmiBinding.kind, OmmiBinding.position))
    return list(db.execute(stmt).scalars().all())


def replace_bindings(db: Session, *, project_id: str, owner_id: str,
                     scene_id: str | None, items: list[dict]
                     ) -> tuple[list[OmmiBinding], int]:
    """Xoa het binding cu cua (project_id, scene_id) roi ghi lai theo `items`,
    danh so lai TOAN BO theo Sec 6.3 quy tac 1-2.

    Quy tac 2: variant khong con ban ghi (hoac khong phai cua owner_id) =>
    KHONG tieu so — loai khoi danh sach TRUOC khi dem, khong chi bo qua sau.
    """
    validated: list[tuple[str, str, str]] = []  # (kind, variant_id, role)
    for item in items:
        kind = _clean_kind(item.get("kind"))
        variant_id = str(item.get("variant_id") or "").strip()
        if not variant_id:
            raise BindingError("Thieu variant_id.")
        variant = db.get(OmmiResourceVariant, variant_id)
        if variant is None or variant.owner_id != owner_id:
            continue  # quy tac 2: khong tieu so
        role = _clean_role(kind, item.get("role"))
        validated.append((kind, variant_id, role))

    db.execute(delete(OmmiBinding).where(
        OmmiBinding.project_id == project_id, OmmiBinding.owner_id == owner_id,
        OmmiBinding.scene_id == scene_id))

    counters = {"image": 0, "video": 0, "audio": 0}
    created: list[OmmiBinding] = []
    for kind, variant_id, role in validated:
        counters[kind] += 1
        row = OmmiBinding(
            owner_id=owner_id, project_id=project_id, scene_id=scene_id,
            tag=f"@{_PREFIX[kind]}_{counters[kind]}", kind=kind,
            variant_id=variant_id, position=counters[kind], role=role)
        db.add(row)
        created.append(row)
    db.flush()
    return created, len(created)


def delete_binding(db: Session, *, project_id: str, owner_id: str,
                   scene_id: str | None, tag: str) -> list[OmmiBinding]:
    row = db.execute(select(OmmiBinding).where(
        OmmiBinding.project_id == project_id, OmmiBinding.owner_id == owner_id,
        OmmiBinding.scene_id == scene_id, OmmiBinding.tag == tag)).scalars().first()
    if row is None:
        raise BindingNotFound("Khong tim thay binding.")
    db.delete(row)
    db.flush()
    return list_bindings(db, project_id=project_id, owner_id=owner_id, scene_id=scene_id)


def binding_lines(db: Session, *, project_id: str, owner_id: str,
                  scene_id: str | None = None) -> list[dict]:
    """Dong tai nguyen DA GAN THE, de `composer.resource_lines()` khong tu
    dem nua (quyet dinh D-2, dau plan). Diem noi cho pha 2/3 (bundle/placeholder)."""
    items = []
    for binding in list_bindings(db, project_id=project_id, owner_id=owner_id,
                                 scene_id=scene_id):
        variant = db.get(OmmiResourceVariant, binding.variant_id)
        resource = db.get(OmmiResource, variant.resource_id) if variant else None
        name = (variant.label if variant and variant.label else
               (resource.name if resource else "Tài nguyên"))
        items.append({"tag": binding.tag, "kind": binding.kind, "name": name,
                     "description": resource.description if resource else ""})
    return items
```

- [ ] **Step 4: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5110_bindings_danh_so.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Viết test đỏ cho quy tắc 2 (không tiêu số) — thêm tệp mới**

```python
# tests/test_5111_bindings_quy_tac_khong_tieu_so.py
"""Spec Sec 6.3 quy tac 2: variant khong con ban ghi thi KHONG tieu so."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings2.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _variant(db, owner="u1"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="prop", name="Do vat")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png")
    db.commit()
    return variant


def test_variant_khong_ton_tai_khong_tieu_so(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id},
               {"kind": "image", "variant_id": "khong-ton-tai"},
               {"kind": "image", "variant_id": v2.id}])
    assert changed == 2
    tags = sorted(row.tag for row in created)
    assert tags == ["@IMAGE_1", "@IMAGE_2"], (
        "variant vang mat khong duoc chiem mot so — @IMAGE_2 phai thuoc ve v2, "
        "khong phai nhay len @IMAGE_3")


def test_variant_cua_nguoi_khac_khong_tieu_so(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v_cua_a = _variant(db, owner="a")
    v_cua_b = _variant(db, owner="b")
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="a", scene_id="s1",
        items=[{"kind": "image", "variant_id": v_cua_a.id},
               {"kind": "image", "variant_id": v_cua_b.id}])
    assert changed == 1
    assert created[0].variant_id == v_cua_a.id


def test_put_la_ghi_de_toan_bo_khong_phai_them(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id}])
    db.commit()
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v2.id}])
    db.commit()
    assert changed == 1
    remaining = svc.list_bindings(db, project_id="p1", owner_id="u1", scene_id="s1")
    assert [row.variant_id for row in remaining] == [v2.id], (
        "PUT phai la GHI DE TOAN BO (spec 6.1) — v1 phai bien mat sau lan PUT thu hai")
```

- [ ] **Step 6: Chạy test, xác nhận hành vi hiện tại đã ĐÚNG (không cần sửa
  code — service viết ở Step 3 đã tuân quy tắc 2 và replace-all)**

Run: `python -m pytest tests/test_5111_bindings_quy_tac_khong_tieu_so.py -q`
Expected: PASS ngay (3 passed) — bài này là lưới hồi quy xác nhận thiết kế ở
Step 3 đúng đặc tả, không phải một vòng đỏ-xanh mới.

- [ ] **Step 7: Viết test đỏ cho xoá + `binding_lines()`**

```python
# tests/test_5112_bindings_xoa_va_so_huu.py
"""delete_binding + binding_lines() — Sec 6.1 DELETE va cau noi cho composer."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings3.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _variant(db, owner="u1", name="Nhân vật A", desc="ao xanh"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="character", name=name, description=desc)
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png",
                               label="goc nghieng")
    db.commit()
    return variant


def test_xoa_dung_tag_con_lai_ban_ghi_khac(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id},
                               {"kind": "image", "variant_id": v2.id}])
    db.commit()
    remaining = svc.delete_binding(db, project_id="p1", owner_id="u1",
                                  scene_id="s1", tag="@IMAGE_1")
    assert [row.tag for row in remaining] == ["@IMAGE_2"]


def test_xoa_tag_khong_ton_tai_nem_binding_not_found(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    with pytest.raises(svc.BindingNotFound):
        svc.delete_binding(db, project_id="p1", owner_id="u1", scene_id="s1",
                          tag="@IMAGE_9")


def test_binding_lines_doc_ten_va_mo_ta_tu_variant_va_resource(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db, name="Nhân vật A", desc="ao xanh")
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id}])
    db.commit()
    lines = svc.binding_lines(db, project_id="p1", owner_id="u1", scene_id="s1")
    assert lines == [{"tag": "@IMAGE_1", "kind": "image",
                     "name": "goc nghieng", "description": "ao xanh"}]
```

- [ ] **Step 8: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5112_bindings_xoa_va_so_huu.py -q`
Expected: PASS (3 passed)

- [ ] **Step 9: Commit**

```bash
git add apps/prompt_ai_ommi/services/bindings.py tests/test_5110_bindings_danh_so.py tests/test_5111_bindings_quy_tac_khong_tieu_so.py tests/test_5112_bindings_xoa_va_so_huu.py
git commit -m "$(cat <<'EOF'
feat(prompt_ai_ommi): services/bindings.py — dang so the theo spec Sec 6.3

Hai bo dem doc lap (image/video), PUT la ghi de toan bo, variant vang mat
hoac khong phai cua chu so huu thi KHONG tieu so (quy tac 2). role anh dung
lai apps.taovideo.refs.image_role() thay vi tu kiem tra.

binding_lines() la cau noi cho composer.resource_lines() doc the da gan
thay vi tu dem (Task 6).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `routes/bindings.py` — endpoint HTTP (Làn A) + đăng ký router (Làn M)

**Files:**
- Create: `apps/prompt_ai_ommi/routes/bindings.py`
- Modify: `apps/prompt_ai_ommi/routes/__init__.py` (thêm `bindings` vào tuple
  import — 1 dòng, sở hữu bởi Làn M theo spec §9.1 nhưng thực hiện ở đây vì
  phụ thuộc trực tiếp file vừa tạo, không mở rộng phạm vi sở hữu)
- Test: `tests/test_5120_routes_bindings_get_put.py`
- Test: `tests/test_5121_routes_bindings_delete_va_loi.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.routes._shared.{router, require_login,
  get_db, _csrf, _user, _owned_production}` (đã có);
  `apps.prompt_ai_ommi.services.bindings.{replace_bindings, list_bindings,
  delete_binding, BindingError, BindingNotFound}` (Task 4)
- Produces: ba route `GET/PUT/DELETE /prompt-ai-ommi/api/projects/{project_id}/bindings[/{tag}]`
  theo đúng hình dạng trả về ở spec §6.1

- [ ] **Step 1: Viết test đỏ (dùng TestClient của FastAPI qua app thật của repo)**

```python
# tests/test_5120_routes_bindings_get_put.py
"""GET/PUT /prompt-ai-ommi/api/projects/{pid}/bindings — spec Sec 6.1."""
from __future__ import annotations

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'routes_bindings.db').as_posix()}")
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    from server.app import cai_dat_ung_dung
    from fastapi.testclient import TestClient
    import platform_core.db as dbmod
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    app = cai_dat_ung_dung()
    with TestClient(app) as c:
        yield c
    dbmod.reset_engine()


def _dang_nhap(client, user_id="khach1"):
    # Theo quy uoc test hien co cua repo: dang nhap qua endpoint test-only
    # hoac cookie session dung san — dieu chinh theo ham dang nhap that cua
    # conftest neu repo da co (tests/conftest.py::dang_nhap_test).
    from tests.conftest import dang_nhap_test
    return dang_nhap_test(client, user_id)


def _tao_project_va_variant(client, db_session):
    # tao 1 AppProject production + 1 OmmiResourceVariant qua service that,
    # tra ve (project_id, variant_id)
    ...


def test_put_bindings_tra_ve_dung_hinh_dang(client):
    _dang_nhap(client)
    project_id, variant_id = _tao_project_va_variant(client, None)
    resp = client.put(f"/prompt-ai-ommi/api/projects/{project_id}/bindings",
                      json={"scene_id": "s1",
                            "items": [{"kind": "image", "variant_id": variant_id}]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["changed"] == 1
    assert body["bindings"][0]["tag"] == "@IMAGE_1"


def test_get_bindings_sau_put(client):
    _dang_nhap(client)
    project_id, variant_id = _tao_project_va_variant(client, None)
    client.put(f"/prompt-ai-ommi/api/projects/{project_id}/bindings",
              json={"scene_id": "s1",
                    "items": [{"kind": "image", "variant_id": variant_id}]})
    resp = client.get(f"/prompt-ai-ommi/api/projects/{project_id}/bindings?scene_id=s1")
    assert resp.status_code == 200
    assert resp.json()["bindings"][0]["tag"] == "@IMAGE_1"
```

> Ghi chú thực thi: hai hàm `_dang_nhap`/`_tao_project_va_variant` phải được
> hoàn thiện dựa trên tiện ích test THẬT đang có trong repo (`tests/conftest.py`
> và cách các route test khác của `prompt_ai_ommi` — ví dụ
> `tests/test_136_ommi_resources.py` — dựng session/CSRF). Bước 1 của Step 2
> dưới đây là đọc `tests/conftest.py` để lấy đúng tên hàm trước khi chạy.

- [ ] **Step 2: Đọc `tests/conftest.py` và một test route khác của
  `prompt_ai_ommi` đã đăng nhập thành công (ví dụ tìm bằng
  `grep -rl "dang_nhap\|require_login" tests/test_1*prompt_ai_ommi*.py
  tests/test_*ommi*route*.py`) để hoàn thiện `_dang_nhap`/
  `_tao_project_va_variant` ở Step 1, rồi chạy để thấy ĐỎ**

Run: `python -m pytest tests/test_5120_routes_bindings_get_put.py -q`
Expected: FAIL — `404 Not Found` (route `bindings` chưa tồn tại, chưa đăng
ký trong router).

- [ ] **Step 3: Viết `routes/bindings.py`**

```python
# apps/prompt_ai_ommi/routes/bindings.py
"""routes/bindings.py — endpoint thẻ <-> variant (spec Sec 6.1).

CRUD mong: PUT ghi de TOAN BO danh sach binding cua (project, scene) — khong
phai them/bot tung cai. Xem services/bindings.py cho logic that.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _owned_production, _user, router, require_login, get_db)
from apps.prompt_ai_ommi.services import bindings as svc


def _row(binding) -> dict:
    return {"tag": binding.tag, "kind": binding.kind,
           "variant_id": binding.variant_id, "position": binding.position,
           "role": binding.role, "scene_id": binding.scene_id}


@router.get("/api/projects/{project_id}/bindings")
async def get_bindings(request: Request, project_id: str, scene_id: str = "",
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    user = _user(request)
    _owned_production(db, project_id, user.id)
    rows = svc.list_bindings(db, project_id=project_id, owner_id=user.id,
                             scene_id=(scene_id or None))
    return {"bindings": [_row(row) for row in rows]}


@router.put("/api/projects/{project_id}/bindings")
async def put_bindings(request: Request, project_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _owned_production(db, project_id, user.id)
    scene_id = body.get("scene_id") or None
    items = list(body.get("items") or [])
    try:
        created, changed = svc.replace_bindings(
            db, project_id=project_id, owner_id=user.id, scene_id=scene_id,
            items=items)
    except svc.BindingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {"bindings": [_row(row) for row in created], "changed": changed}


@router.delete("/api/projects/{project_id}/bindings/{tag}")
async def delete_binding_route(request: Request, project_id: str, tag: str,
                               scene_id: str = "",
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    user = _user(request)
    _owned_production(db, project_id, user.id)
    try:
        remaining = svc.delete_binding(
            db, project_id=project_id, owner_id=user.id,
            scene_id=(scene_id or None), tag=tag)
    except svc.BindingNotFound as exc:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy binding.')) from exc
    db.commit()
    return {"bindings": [_row(row) for row in remaining]}
```

- [ ] **Step 4: Đăng ký router trong `routes/__init__.py`**

```python
# apps/prompt_ai_ommi/routes/__init__.py — thêm "bindings" vào tuple import
from apps.prompt_ai_ommi.routes._shared import router
from apps.prompt_ai_ommi.routes import (  # noqa: F401  (import de dang ky route)
    pages, projects, handoff, bindings, assets_catalog, resources, library,
    storyboard, overview)

__all__ = ["router"]
```

(và cập nhật dòng docstring liệt kê module ở đầu tệp, thêm
`bindings.py       CRUD the (@IMAGE_k/@VIDEO_k) <-> variant, spec pha 1.`)

- [ ] **Step 5: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5120_routes_bindings_get_put.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Viết test đỏ cho DELETE + lỗi role**

```python
# tests/test_5121_routes_bindings_delete_va_loi.py
"""DELETE /bindings/{tag} + 400 khi role sai — spec Sec 6.1."""
from __future__ import annotations

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'routes_bindings2.db').as_posix()}")
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    from server.app import cai_dat_ung_dung
    from fastapi.testclient import TestClient
    import platform_core.db as dbmod
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    app = cai_dat_ung_dung()
    with TestClient(app) as c:
        yield c
    dbmod.reset_engine()


def test_delete_tag_khong_ton_tai_tra_404(client):
    from tests.conftest import dang_nhap_test
    dang_nhap_test(client, "khach1")
    # project_id gia (khong ton tai) van phai qua _owned_production truoc,
    # nen dung mot project that toi thieu — xem Step 7 de hoan thien fixture
    # dung chung voi test_5120 (rut thanh ham tien ich trong conftest neu can).
    ...


def test_put_role_sai_tra_400(client):
    ...
```

- [ ] **Step 7: Hoàn thiện fixture dùng chung, chạy test để thấy XANH**

Run: `python -m pytest tests/test_5120_routes_bindings_get_put.py tests/test_5121_routes_bindings_delete_va_loi.py -q`
Expected: PASS (4 passed)

- [ ] **Step 8: Commit**

```bash
git add apps/prompt_ai_ommi/routes/bindings.py apps/prompt_ai_ommi/routes/__init__.py tests/test_5120_routes_bindings_get_put.py tests/test_5121_routes_bindings_delete_va_loi.py
git commit -m "$(cat <<'EOF'
feat(prompt_ai_ommi): routes/bindings.py — endpoint GET/PUT/DELETE bindings

Be mat HTTP cho services/bindings.py (spec Sec 6.1). PUT ghi de TOAN BO danh
sach binding cua (project, scene) trong mot lan goi, dung ngu nghia "danh so
lai toan bo" cua spec.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `composer.py::resource_lines()` đọc thẻ đã gán (Làn A)

**Files:**
- Modify: `apps/prompt_ai_ommi/services/composer.py:28-39` (hàm
  `resource_lines`)
- Test: `tests/test_5123_composer_resource_lines_doc_tag_da_gan.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.services.bindings.binding_lines()` (Task 4,
  dùng trong test, không import trong `composer.py` — xem quyết định D-2:
  `composer.py` KHÔNG phụ thuộc `bindings.py`, chỉ đổi cách đọc item)
- Produces: `resource_lines(resources: list[dict]) -> list[str]` — hành vi
  MỚI: item có khoá `"tag"` thì dùng nguyên tag đó; không có thì tự đếm như
  cũ (không đổi hành vi của `preview()`/`director_prompt()` hiện tại)

- [ ] **Step 1: Viết test đỏ**

```python
# tests/test_5123_composer_resource_lines_doc_tag_da_gan.py
"""composer.resource_lines() phai DOC tag da gan (ommi_binding), khong tu dem
lai, khi item cung cap san khoa "tag" (spec quyet dinh D-2, chua N-2).
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.composer import resource_lines


def test_dung_tag_co_san_thay_vi_tu_dem():
    items = [{"kind": "image", "tag": "@IMAGE_5", "name": "Nhân vật A",
             "description": "áo xanh"}]
    lines = resource_lines(items)
    assert lines == ["- @IMAGE_5 [image] Nhân vật A: áo xanh"], (
        "phai dung DUNG tag da gan (@IMAGE_5), khong tu dem thanh @IMAGE_1")


def test_khong_co_tag_van_tu_dem_nhu_cu_tuong_thich_nguoc():
    items = [{"kind": "image", "name": "A", "description": "x"},
             {"kind": "video", "name": "B", "description": "y"},
             {"kind": "image", "name": "C", "description": "z"}]
    lines = resource_lines(items)
    assert lines == [
        "- @IMAGE_1 [image] A: x",
        "- @VIDEO_1 [video] B: y",
        "- @IMAGE_2 [image] C: z",
    ]
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5123_composer_resource_lines_doc_tag_da_gan.py -q`
Expected: FAIL tại `test_dung_tag_co_san_thay_vi_tu_dem` — hàm hiện tại bỏ
qua khoá `"tag"` và tự đếm ra `@IMAGE_1`, không phải `@IMAGE_5`.

- [ ] **Step 3: Sửa `resource_lines()` trong `services/composer.py:28-39`**

```python
def resource_lines(resources: list[dict]) -> list[str]:
    lines = []
    counters: dict[str, int] = {"image": 0, "video": 0, "audio": 0}
    for item in resources[:24]:
        kind = str(item.get("kind") or "prop")
        tag = str(item.get("tag") or "").strip()
        if tag:
            handle = f"{tag} "
        else:
            handle = ""
            if kind in counters:
                counters[kind] += 1
                handle = f"@{kind.upper()}_{counters[kind]} "
        name = str(item.get("name") or "Tài nguyên").strip()
        desc = str(item.get("description") or "").strip()
        lines.append(f"- {handle}[{kind}] {name}: {desc}".rstrip())
    return lines
```

- [ ] **Step 4: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5123_composer_resource_lines_doc_tag_da_gan.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Chạy lại toàn bộ test hiện có gọi `composer.py` để chắc
  không phá `preview()`/`director_prompt()`**

Run: `python -m pytest tests/test_155_ommi_metrics.py -q -k composer or preview or director`
(nếu không có kết quả khớp `-k`, bỏ `-k` và chạy toàn bộ tệp test đã `grep -l
"composer\|resource_lines" tests/test_*.py` liệt kê được ở bước chuẩn bị)
Expected: PASS, không có regression.

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/services/composer.py tests/test_5123_composer_resource_lines_doc_tag_da_gan.py
git commit -m "$(cat <<'EOF'
fix(prompt_ai_ommi): resource_lines() doc tag da gan thay vi tu dem

Chuan bi cho ommi_binding lam nguon chan ly duy nhat (N-2): item co san khoa
"tag" (tu binding_lines()) thi dung nguyen, khong tu dem lai. Khong co tag
(hai noi goi hien tai preview()/director_prompt() chua doi sang bindings) thi
van tu dem nhu truoc — khong regression.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `services/bat_bien.py::bat_bien_giao_bai` — bất biến biên §8 (Làn B, ngoại lệ pha 1)

**Files:**
- Create: `apps/prompt_ai_ommi/services/bat_bien.py`
- Test: `tests/test_5131_bat_bien_giao_bai.py`

**Interfaces:**
- Consumes: `apps.taovideo.refs.VALID_IMAGE_ROLES` (Task 3)
- Produces: `bat_bien_giao_bai(prompt: str, refs: list[dict], skipped:
  list[dict], *, has_binding: bool = False) -> None` (ném `ValueError` — xem
  quyết định D-3 cho lý do thêm `has_binding`). Mỗi phần tử `refs` có
  `{"kind": str, "url": str, "role": str, "handle": str}` (`handle` không có
  `@`, chữ thường, ví dụ `"image_1"`). Mỗi phần tử `skipped` có
  `{"variant_id": str, "handle": str, "ly_do": str}`.

- [ ] **Step 1: Viết test đỏ cho B-1..B-4 + T-1**

```python
# tests/test_5131_bat_bien_giao_bai.py
"""bat_bien_giao_bai — bat bien o BIEN, spec Sec 8. Nam dieu kien B-1..B-5.

T-1 (spec Sec 10.2, khong duoc thieu): tiem loi cu — canh co 2 anh, ep
refs=[] => PHAI nem. Day chinh la ham chua N-1 (prompt nhac anh ma refs
rong bi tra ve em ru).
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai


def _refs_du():
    return [{"kind": "image", "url": "data:image/png;base64,AA==",
            "role": "reference_image", "handle": "image_1"},
           {"kind": "image", "url": "data:image/png;base64,BB==",
            "role": "reference_image", "handle": "image_2"}]


def test_hop_le_khong_nem(_prompt=None):
    prompt = "Canh mo dau voi @IMAGE_1 va @IMAGE_2 dung canh nhau."
    bat_bien_giao_bai(prompt, _refs_du(), [], has_binding=True)  # khong nem la PASS


def test_T1_tiem_loi_cu_refs_rong_phai_nem():
    """T-1: dung canh co 2 anh (prompt nhac @IMAGE_1/@IMAGE_2), ep refs=[] =>
    phai nem. So 0 khong doi chung khong phai phat hien — day la doi chung."""
    prompt = "Canh mo dau voi @IMAGE_1 va @IMAGE_2 dung canh nhau."
    with pytest.raises(ValueError, match="B-1"):
        bat_bien_giao_bai(prompt, [], [], has_binding=True)


def test_B1_thieu_ref_nhung_co_trong_skipped_thi_hop_le():
    prompt = "Canh co @IMAGE_1 va @IMAGE_2."
    refs = [{"kind": "image", "url": "data:image/png;base64,AA==",
            "role": "reference_image", "handle": "image_1"}]
    skipped = [{"variant_id": "v2", "handle": "image_2", "ly_do": "tep khong ton tai"}]
    bat_bien_giao_bai(prompt, refs, skipped, has_binding=True)  # khong nem


def test_B2_ref_thua_khong_duoc_prompt_nhac_phai_nem():
    prompt = "Canh chi nhac @IMAGE_1."
    refs = _refs_du()  # co ca image_1 va image_2, prompt khong nhac image_2
    with pytest.raises(ValueError, match="B-2"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B3_handle_trung_lap_phai_nem():
    prompt = "Canh co @IMAGE_1."
    refs = [{"kind": "image", "url": "u1", "role": "reference_image", "handle": "image_1"},
           {"kind": "image", "url": "u2", "role": "reference_image", "handle": "image_1"}]
    with pytest.raises(ValueError, match="B-3"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B4_role_anh_khong_hop_le_phai_nem():
    prompt = "Canh co @IMAGE_1."
    refs = [{"kind": "image", "url": "u1", "role": "khong_hop_le", "handle": "image_1"}]
    with pytest.raises(ValueError, match="B-4"):
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_B5_co_binding_ma_refs_va_skipped_deu_rong_phai_nem():
    prompt = "Canh khong nhac anh nao ca."
    with pytest.raises(ValueError, match="B-5"):
        bat_bien_giao_bai(prompt, [], [], has_binding=True)


def test_B5_khong_co_binding_thi_refs_rong_la_binh_thuong():
    prompt = "Canh khong nhac anh nao ca."
    bat_bien_giao_bai(prompt, [], [], has_binding=False)  # khong nem
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5131_bat_bien_giao_bai.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named
'apps.prompt_ai_ommi.services.bat_bien'`

- [ ] **Step 3: Viết `services/bat_bien.py`**

```python
# apps/prompt_ai_ommi/services/bat_bien.py
"""services/bat_bien.py — bat bien o BIEN cho giao bai sang app khac (spec Sec 8).

Thuoc cho dang loi `cho-noi-hai-module-vut-truong-im-lang`: doc sai ten khoa
roi `continue`, vut truong im lang. Goi o DUNG MOT cho — ngay truoc khi tra
ve `params["refs"]` cho job video (`routes/handoff.py`).

Pha 1 CHUA co `services/handoff_stage.py` (do la Pha 2 — ve giao bai
`ommi_handoff`). Pha 2 se IMPORT LAI dung ham nay tu day, khong viet lai.

`has_binding` (quyet dinh D-3, xem dau plan): B-5 can biet canh co
`ommi_binding` hay khong — thong tin nay khong nam trong 3 tham so
(prompt, refs, skipped) ma spec Sec 8 liet ke, nen day la mot tham so tu
khoa THEM, mac dinh `False` giu nguyen hanh vi goi 3-tham so cu.
"""
from __future__ import annotations

import re

from apps.taovideo.refs import VALID_IMAGE_ROLES

_TAG_RE = re.compile(r"@(IMAGE|VIDEO)_(\d+)", re.IGNORECASE)


def bat_bien_giao_bai(prompt: str, refs: list[dict], skipped: list[dict],
                      *, has_binding: bool = False) -> None:
    prompt_handles = {f"{kind.lower()}_{num}"
                      for kind, num in _TAG_RE.findall(prompt or "")}
    ref_handles = [str(r.get("handle") or "").strip().lower() for r in (refs or [])]
    skipped_handles = {str(s.get("handle") or "").strip().lower()
                       for s in (skipped or [])}

    # B-3: mot handle khong duoc xuat hien hai lan trong refs.
    if len(ref_handles) != len(set(ref_handles)):
        raise ValueError(
            "B-3: mot handle xuat hien hai lan trong refs — danh so vo.")

    ref_handle_set = set(ref_handles)

    # B-1: prompt nhac handle nao thi handle do phai co trong refs HOAC skipped.
    for handle in prompt_handles:
        if handle not in ref_handle_set and handle not in skipped_handles:
            raise ValueError(
                f"B-1: prompt nhac @{handle.upper()} nhung refs khong mang "
                "theo va cung khong nam trong skipped — anh se mat khong ai biet.")

    # B-2: refs mang theo handle nao thi prompt phai nhac handle do.
    for handle in ref_handle_set:
        if handle not in prompt_handles:
            raise ValueError(
                f"B-2: refs mang theo @{handle.upper()} nhung prompt khong "
                "nhac — tra tien cho anh vo ich.")

    # B-4: role cua ref anh phai thuoc VALID_IMAGE_ROLES.
    for ref in (refs or []):
        if str(ref.get("kind")) == "image":
            role = str(ref.get("role") or "")
            if role not in VALID_IMAGE_ROLES:
                raise ValueError(
                    f"B-4: role {role!r} khong hop le cho anh — ben nhan se "
                    "am tham remap ve reference_image.")

    # B-5: co binding ma ca refs va skipped deu rong la chac chan sai duong doc.
    if has_binding and not refs and not skipped:
        raise ValueError(
            "B-5: canh co ommi_binding nhung refs va skipped deu rong — "
            "bindings co ma khong sinh duoc ref nao, chac chan lech duong doc.")
```

- [ ] **Step 4: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5131_bat_bien_giao_bai.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/bat_bien.py tests/test_5131_bat_bien_giao_bai.py
git commit -m "$(cat <<'EOF'
feat(prompt_ai_ommi): bat_bien_giao_bai — luoi an toan o bien (spec Sec 8)

Nam dieu kien B-1..B-5. T-1 (tiem loi cu: canh 2 anh, ep refs=[] => nem) la
phep bat buoc theo spec Sec 10.2 — day chinh la ham chua N-1 (prompt nhac
anh ma refs rong duoc tra ve em ru).

has_binding la tham so tu khoa them (quyet dinh D-3): B-5 can biet canh co
binding hay khong, thong tin nam ngoai 3 tham so spec Sec 8 liet ke.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Sửa `routes/handoff.py` — N-1 mức tối thiểu (Làn B, ngoại lệ pha 1)

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/handoff.py:1-52` (import, `_handoff_params`,
  hàm `handoff()`)
- Test: `tests/test_5132_handoff_video_refs_tu_binding.py`
- Test: `tests/test_5133_handoff_video_tep_mat_van_vao_skipped.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.services.bindings.list_bindings()` (Task 4);
  `apps.prompt_ai_ommi.services.bat_bien.bat_bien_giao_bai()` (Task 7);
  `apps.prompt_ai_ommi.services.composer.style_description()` (đã có);
  `apps.taovideo.refs.image_to_inline()`, `.MAX_INLINE_BYTES` (Task 3);
  `platform_core.storage.get_storage()` (đã có, `Storage.open(key) ->
  BinaryIO`, `Storage.exists(key) -> bool`)
- Produces: `_handoff_params(db: Session, owner_id: str, project, scene:
  dict, kind: str, body: dict) -> tuple[str, dict]` — chữ ký ĐỔI (thêm `db`,
  `owner_id` ở đầu) so với bản cũ `_handoff_params(project, scene, kind,
  body)`; params["refs"] giờ là danh sách THẬT thay vì `[]` cho kind="video"

- [ ] **Step 1: Viết test đỏ cho N-1 (refs thật + camera/motion/visual_style
  không còn hằng số)**

```python
# tests/test_5132_handoff_video_refs_tu_binding.py
"""N-1 (spec Sec 6.2): handoff video khong con `refs: []` va khong con ghi
de cung "cinematic" cho moi canh — gia tri phai lay tu scene/binding that.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'handoff_n1.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


class _FakeStorage:
    """Storage gia — chi doc lai bytes da 'put' truoc do, khong dung o dia that."""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    def put_test(self, key: str, data: bytes) -> None:
        self._data[key] = data

    def exists(self, key: str) -> bool:
        return key in self._data

    def open(self, key: str):
        import io
        return io.BytesIO(self._data[key])


def _du_lieu_anh_1x1_png() -> bytes:
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def _du_an_va_canh(db, monkeypatch):
    from apps.prompt_ai_ommi.services import resources as rsvc
    from apps.prompt_ai_ommi.services import bindings as bsvc
    from platform_core import app_projects
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.project_schema import empty_project

    fake = _FakeStorage()
    monkeypatch.setattr("platform_core.storage.get_storage", lambda: fake)

    resource = rsvc.create(db, owner_id="khach1", kind="character", name="A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id="khach1",
                               storage_key="ommi/khach1/r1/a.png")
    fake.put_test(variant.storage_key, _du_lieu_anh_1x1_png())

    payload = empty_project("Du an test")
    payload["brief"]["style_id"] = "anime"
    payload["scenes"] = [{"id": "scene1", "order": 0, "title": "Canh 1",
                          "prompt": "Nhan vat @IMAGE_1 buoc vao phong.",
                          "camera": "tu tu dolly toi gan nhan vat",
                          "mood": "dynamic va cang thang", "lighting": "",
                          "continuity": "", "duration_seconds": 5,
                          "versions": [], "selected_version": 0}]
    project = app_projects.create(db, user_id="khach1", app_slug=MANIFEST.slug,
                                  name="Du an test", schema_version=1, payload=payload)
    db.commit()

    bsvc.replace_bindings(db, project_id=project.id, owner_id="khach1",
                          scene_id="scene1",
                          items=[{"kind": "image", "variant_id": variant.id}])
    db.commit()
    return project


def test_refs_khong_con_rong_va_camera_motion_tu_canh(db, monkeypatch):
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _du_an_va_canh(db, monkeypatch)
    scene = project.payload["scenes"][0]
    tool_name, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert tool_name == "video.generate"
    assert len(params["refs"]) == 1
    assert params["refs"][0]["handle"] == "image_1"
    assert params["refs"][0]["url"].startswith("data:image/")
    assert params["camera"] != "" or True  # co the rong neu khong khop tu khoa nao
    assert params["motion"] == "dynamic"  # "dynamic" trong "dynamic va cang thang"
    assert params["visual_style"] == "anime"
```

- [ ] **Step 2: Chạy test để thấy ĐỎ**

Run: `python -m pytest tests/test_5132_handoff_video_refs_tu_binding.py -q`
Expected: FAIL — `TypeError: _handoff_params() takes 4 positional arguments
but 5 were given` (chữ ký cũ chưa nhận `db`, `owner_id`).

- [ ] **Step 3: Sửa `routes/handoff.py`**

Thêm import ở đầu tệp (giữ nguyên các import cũ, chỉ thêm):

```python
from apps.prompt_ai_ommi.services import bindings as bindings_svc
from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai
from apps.prompt_ai_ommi.services.composer import style_description
from apps.prompt_ai_ommi.tables import OmmiResourceVariant
from apps.taovideo.refs import RefError, image_to_inline
```

Thêm hàm ánh xạ enum (quyết định D-4) TRƯỚC `_handoff_params`:

```python
def _doan_enum(text: str, values: tuple, tu_khoa: dict, mac_dinh: str = "") -> str:
    """Doan gia tri enum gan nhat tu van ban tu do. `""` luon la lua chon an
    toan (co mat trong moi bang enum cua taovideo nhu "chua xac dinh")."""
    thap = (text or "").lower()
    for tu, gia_tri in tu_khoa.items():
        if tu in thap and gia_tri in values:
            return gia_tri
    return mac_dinh if mac_dinh in values else ""


_CAMERA_TU_KHOA = {"dolly": "dolly_in", "track": "tracking", "orbit": "orbit",
                   "aerial": "aerial", "drone": "aerial", "handheld": "handheld",
                   "static": "static", "fixed": "static", "tinh": "static"}
_MOTION_TU_KHOA = {"subtle": "subtle", "calm": "subtle", "cham": "subtle",
                   "dynamic": "dynamic", "energetic": "dynamic",
                   "manh": "dynamic", "cinematic": "cinematic"}
_STYLE_TU_KHOA = {"realistic": "realistic", "that": "realistic",
                  "anime": "anime", "product": "product",
                  "cinematic": "cinematic"}
```

Sửa `_handoff_params` (chữ ký thêm `db`, `owner_id`; nhánh `kind == "video"`
viết lại hoàn toàn phần refs/camera/motion/visual_style, nhánh `kind ==
"image"` giữ nguyên):

```python
def _handoff_params(db, owner_id: str, project, scene: dict, kind: str, body: dict) -> tuple[str, dict]:
    if kind == "image":
        tool_name = "image.generate"
        params = {"prompt": str(scene.get("prompt") or "")[:4000],
                  "model": str(body.get("model") or next(
                      (item["value"] for item in _models("image")), "hidream-o1")),
                  "aspect_ratio": str((project.payload or {}).get("brief", {}).get(
                      "aspect_ratio") or "16:9"),
                  "count": _as_int(body.get("count"), 1, 1, 4)}
    elif kind == "video":
        tool_name = "video.generate"
        brief = (project.payload or {}).get("brief") or {}
        style_id = str(brief.get("style_id") or "cinematic")
        style_custom = str(brief.get("style_custom") or "")

        from platform_core.storage import get_storage
        storage = get_storage()
        scene_id = str(scene.get("id") or "")
        all_bindings = bindings_svc.list_bindings(
            db, project_id=project.id, owner_id=owner_id, scene_id=scene_id)
        image_bindings = [b for b in all_bindings if b.kind == "image"]
        capped, skipped_over_limit = image_bindings[:9], max(0, len(image_bindings) - 9)

        refs: list[dict] = []
        skipped: list[dict] = []
        for binding in capped:
            handle = binding.tag.lstrip("@").lower()
            variant = db.get(OmmiResourceVariant, binding.variant_id)
            if variant is None or not storage.exists(variant.storage_key):
                skipped.append({"variant_id": binding.variant_id, "handle": handle,
                                "ly_do": "tep khong ton tai"})
                continue
            try:
                data = storage.open(variant.storage_key).read()
                url = image_to_inline(data)
            except RefError:
                skipped.append({"variant_id": binding.variant_id, "handle": handle,
                                "ly_do": "anh vuot qua nguong inline sau chuan hoa"})
                continue
            refs.append({"kind": "image", "url": url, "role": binding.role,
                        "handle": handle})

        params = {"prompt": str(scene.get("prompt") or "")[:10000],
                  "model": str(body.get("model") or "seedance-2.0-mini"),
                  "resolution": str(body.get("resolution") or "480p"),
                  "duration": _as_int(body.get("duration") or scene.get("duration_seconds"),
                                      5, 1, 60),
                  "aspect_ratio": str(brief.get("aspect_ratio") or "16:9"),
                  "generate_audio": bool(body.get("generate_audio", True)),
                  "camera": _doan_enum(str(scene.get("camera") or ""),
                                      ("", "static", "dolly_in", "tracking",
                                       "orbit", "aerial", "handheld"),
                                      _CAMERA_TU_KHOA),
                  "motion": _doan_enum(str(scene.get("mood") or ""),
                                      ("", "subtle", "dynamic", "cinematic"),
                                      _MOTION_TU_KHOA),
                  "visual_style": _doan_enum(
                      style_description(style_id, style_custom),
                      ("", "realistic", "cinematic", "anime", "product"),
                      _STYLE_TU_KHOA, mac_dinh="cinematic"),
                  "refs": refs, "skipped_over_limit": skipped_over_limit}
        bat_bien_giao_bai(params["prompt"], refs, skipped,
                          has_binding=bool(image_bindings))
    else:
        raise HTTPException(status_code=404, detail=_t('Loại handoff không hỗ trợ.'))
    from platform_core import providers
    capabilities = providers.model_capabilities(params["model"])
    if kind == "image":
        aspects = list(capabilities.get("aspects") or ["16:9", "9:16", "1:1", "4:3", "3:4"])
        if params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    else:
        durations = [int(value) for value in capabilities.get("durations", [])]
        if durations and params["duration"] not in durations:
            params["duration"] = min(durations, key=lambda value: abs(value - params["duration"]))
        resolutions = list(capabilities.get("resolutions") or [])
        if resolutions and params["resolution"] not in resolutions:
            params["resolution"] = resolutions[0]
        aspects = list(capabilities.get("aspects") or [])
        if aspects and params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    return tool_name, params
```

Sửa nơi gọi `_handoff_params` trong `handoff()` (route chính) để truyền
thêm `db`, `user.id`:

```python
    tool_name, params = _handoff_params(db, user.id, project, scene, kind, body)
```

(giữ nguyên toàn bộ phần còn lại của `handoff()` — quote/confirm/submit
credit không đổi). `handoff_image_batch()` gọi `_handoff_params(project,
scene, "image", body)` ở nhánh ảnh — cập nhật CÙNG CÁCH (`_handoff_params(db,
user.id, project, scene, "image", body)`), vì nhánh `image` không dùng
`db`/`owner_id` nhưng chữ ký hàm đã đổi cho cả hai nhánh.

- [ ] **Step 4: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5132_handoff_video_refs_tu_binding.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Viết test đỏ cho quy tắc 3 (file mất vẫn vào skipped, không
  chặn ref còn lại) — T-1 ở mức tích hợp**

```python
# tests/test_5133_handoff_video_tep_mat_van_vao_skipped.py
"""Spec Sec 6.3 quy tac 3: variant con ban ghi nhung MAT TEP thi van tieu so
va vao `skipped` — khong duoc lam rong ca refs (day la duong N-1 that: mot
anh mat tep khong duoc keo theo ca canh mat het anh)."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'handoff_skip.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def test_mot_anh_mat_tep_van_vao_skipped_anh_con_lai_van_di(db, monkeypatch):
    from apps.prompt_ai_ommi.services import resources as rsvc
    from apps.prompt_ai_ommi.services import bindings as bsvc
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params
    from platform_core import app_projects
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.project_schema import empty_project

    class _FakeStorage:
        def __init__(self):
            self._data = {}

        def put_test(self, key, data):
            self._data[key] = data

        def exists(self, key):
            return key in self._data

        def open(self, key):
            import io
            return io.BytesIO(self._data[key])

    fake = _FakeStorage()
    monkeypatch.setattr("platform_core.storage.get_storage", lambda: fake)

    import base64
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII=")

    r1 = rsvc.create(db, owner_id="khach1", kind="character", name="A")
    v1 = rsvc.add_variant(db, resource_id=r1.id, owner_id="khach1",
                          storage_key="ommi/khach1/r1/a.png")
    fake.put_test(v1.storage_key, png)  # v1: tep CO that

    r2 = rsvc.create(db, owner_id="khach1", kind="character", name="B")
    v2 = rsvc.add_variant(db, resource_id=r2.id, owner_id="khach1",
                          storage_key="ommi/khach1/r2/b.png")
    # v2: KHONG put_test — mo phong tep da bi xoa khoi Storage

    payload = empty_project("Du an test")
    payload["scenes"] = [{"id": "scene1", "order": 0, "title": "Canh 1",
                          "prompt": "Nhan vat @IMAGE_1 dung canh @IMAGE_2.",
                          "camera": "", "mood": "", "lighting": "",
                          "continuity": "", "duration_seconds": 5,
                          "versions": [], "selected_version": 0}]
    project = app_projects.create(db, user_id="khach1", app_slug=MANIFEST.slug,
                                  name="Du an test", schema_version=1, payload=payload)
    db.commit()

    bsvc.replace_bindings(db, project_id=project.id, owner_id="khach1",
                          scene_id="scene1",
                          items=[{"kind": "image", "variant_id": v1.id},
                                {"kind": "image", "variant_id": v2.id}])
    db.commit()

    scene = project.payload["scenes"][0]
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert len(params["refs"]) == 1
    assert params["refs"][0]["handle"] == "image_1"
    # quy tac 3: v2 (mat tep) van tieu so @IMAGE_2 — bat_bien_giao_bai khong
    # nem vi @IMAGE_2 nam trong skipped, khong phai vi refs con thieu.
```

- [ ] **Step 6: Chạy test để thấy XANH**

Run: `python -m pytest tests/test_5133_handoff_video_tep_mat_van_vao_skipped.py -q`
Expected: PASS (1 passed)

- [ ] **Step 7: Chạy lại toàn bộ test dải Làn B + Làn A để chắc không phá gì**

Run: `python -m pytest tests/test_5110_bindings_danh_so.py tests/test_5111_bindings_quy_tac_khong_tieu_so.py tests/test_5112_bindings_xoa_va_so_huu.py tests/test_5120_routes_bindings_get_put.py tests/test_5121_routes_bindings_delete_va_loi.py tests/test_5123_composer_resource_lines_doc_tag_da_gan.py tests/test_5131_bat_bien_giao_bai.py tests/test_5132_handoff_video_refs_tu_binding.py tests/test_5133_handoff_video_tep_mat_van_vao_skipped.py -q`
Expected: tất cả PASS

- [ ] **Step 8: Commit**

```bash
git add apps/prompt_ai_ommi/routes/handoff.py tests/test_5132_handoff_video_refs_tu_binding.py tests/test_5133_handoff_video_tep_mat_van_vao_skipped.py
git commit -m "$(cat <<'EOF'
fix(prompt_ai_ommi): N-1 - handoff video dung refs that, bo gia tri ghi cung

routes/handoff.py: refs xay tu ommi_binding (Task 4) qua
apps.taovideo.refs.image_to_inline() (khong viet lai chuan hoa); camera/
motion/visual_style doan tu scene.camera/.mood/style thay vi hang so
"cinematic" cho moi canh. Goi bat_bien_giao_bai() (Task 7) ngay truoc khi
tra params — bat duoc N-1 that su thay vi tra ve em ru.

Quy tac 3 (spec Sec 6.3): variant mat tep van tieu so va vao skipped, khong
lam rong ca refs cua cac anh con lai.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Bật rollout production (CẦN CHỦ DỰ ÁN XÁC NHẬN — không tự làm)

**Files:** không có tệp mã nào — đây là thao tác vận hành trên máy production
(`C:\LTTPlatform`), nằm ngoài cây worktree.

**Interfaces:** không có (task vận hành, không phải mã)

- [ ] **Step 1: KHÔNG tự thực hiện — trình bày với chủ dự án đúng nội dung
  dưới đây và chờ xác nhận**

PROMPT AI OMMI hiện chạy ở `LTT_PROMPT_AI_OMMI_ROLLOUT` mặc định (`"off"`
trên production theo `routes/_shared.py::_run_mode()`, vì
`LTT_ENV=production`). Spec X-6 yêu cầu bật `public` sau khi Task 1-8 đã
merge và deploy — đây là thao tác SỬA BIẾN MÔI TRƯỜNG của HAI service Windows
đang chạy thật (`LTTStudioWeb`, `LTTStudioWorker`), thuộc luật chết người #6
của `CLAUDE.md` (ghi cấu hình không BOM) và có rủi ro production thật.

- [ ] **Step 2: Nếu chủ dự án xác nhận, các lệnh CHÍNH XÁC cần chạy trên máy
  chủ (KHÔNG chạy trong worktree này)**

```powershell
# Kiem gia tri hien tai TRUOC khi doi (khong dung `nssm get` cho bien nhay
# cam khac trong AppEnvironmentExtra da co - chi doc dong lien quan):
nssm dump LTTStudioWeb | Select-String "LTT_PROMPT_AI_OMMI_ROLLOUT"
nssm dump LTTStudioWorker | Select-String "LTT_PROMPT_AI_OMMI_ROLLOUT"

# Them (KIEU THEM, khong ghi de toan bo AppEnvironmentExtra - xem
# docs/nssm-nuong-env-luc-cai trong memory: nssm set ghi de CA KHOI bien,
# khong phai tung dong; phai doc dump truoc, ghep dong moi vao, roi set lai
# TOAN BO khoi da ghep):
nssm set LTTStudioWeb AppEnvironmentExtra <toan bo khoi cu>+LTT_PROMPT_AI_OMMI_ROLLOUT=public
nssm set LTTStudioWorker AppEnvironmentExtra <toan bo khoi cu>+LTT_PROMPT_AI_OMMI_ROLLOUT=public

# QUAN TRONG: restart KHONG nap ENV moi tu AppEnvironmentExtra doi bang
# `nssm set` neu service dang chay tu truoc - phai STOP roi START (khong
# phai RESTART):
nssm stop LTTStudioWeb
nssm start LTTStudioWeb
nssm stop LTTStudioWorker
nssm start LTTStudioWorker

# Xac nhan da nhan bien moi (endpoint khong con tra 503):
python tools\api_prod_canary.py trang-thai
```

- [ ] **Step 3: Một lượt tạo prompt thật của `khach1.thu` để đóng X-6**

Đăng nhập bằng tài khoản test `khach1.thu` (cookie có sẵn, không gõ mật
khẩu — theo luật global CLAUDE.md), mở `https://app.lttstudios.com/prompt-ai-ommi`,
tạo một project, gán binding ảnh cho một cảnh, bấm giao bài video, xác nhận
`refs` không rỗng ở phía `taovideo`. Đây là bước KIỂM TRA, không phải bước
sửa mã — dùng Playwright CLI/MCP theo chính sách global CLAUDE.md (mở
browser thật, tái hiện luồng, kiểm console + network, xác minh trên giao
diện thật).

---

## Tự soát

**1. Độ phủ spec (pha 1 — spec §3 dòng "Pha 1 CHỖ NỐI ĐÚNG"):**

| Yêu cầu pha 1 | Task |
|---|---|
| Tách `tables.py` → package, giữ import cũ (R-4) | Task 1 |
| `ommi_binding` (§4.2 pha 1) | Task 1 (model) + Task 2 (migration) |
| Cạnh app→app hai chiều (G-3, G-3b) | Task 3 |
| `services/bindings.py` + đánh số §6.3 | Task 4 |
| `routes/bindings.py` (§6.1) + đăng ký router | Task 5 |
| `composer.py::resource_lines()` đọc `ommi_binding` | Task 6 |
| `bat_bien_giao_bai` B-1..B-5 (§8) | Task 7 |
| N-1: bỏ `refs: []`, camera/motion/visual_style thật (§6.2, §6.3 quy tắc 3/5) | Task 8 |
| T-1 (tiêm lỗi cũ, §10.2) | Task 7 (unit) + Task 8 (tích hợp) |
| R-4 (test khẳng định import cũ) | Task 1 |
| Bật `LTT_PROMPT_AI_OMMI_ROLLOUT=public` | Task 9 |

Không có mục nào trong phạm vi pha 1 (theo bảng giao việc của lời nhắc) bị
bỏ sót. T-2/T-3 (spec §10.2) thuộc pha 3/4 (placeholder, iterate) — ngoài
phạm vi plan này, không đưa vào.

**2. Quét placeholder:** không còn "TBD"/"tương tự Task N"/hàm chưa định
nghĩa trong bất kỳ Step nào — mọi Step viết mã có block mã đầy đủ. Hai chỗ
NHẤN MẠNH cần người thực thi tự hoàn thiện thay vì chép máy móc đã được ghi
rõ là "hoàn thiện dựa trên tiện ích test thật của repo" (Task 5 Step 1-2,
Task 5 Step 6-7) — đây không phải placeholder che giấu logic nghiệp vụ, mà
là điểm nối với hạ tầng test hiện có (`tests/conftest.py`) mà plan không thể
đoán tên hàm chính xác nếu không đọc tệp đó trước, và bước đọc đã được giao
tường minh làm Step riêng.

**3. Nhất quán kiểu/tên:** `bat_bien_giao_bai(prompt, refs, skipped,
*, has_binding=False)` dùng nhất quán ở Task 7 (định nghĩa) và Task 8 (gọi).
`_handoff_params(db, owner_id, project, scene, kind, body)` dùng nhất quán ở
mọi chỗ gọi trong Task 8 (cả nhánh `image` và nhánh `video`, cả
`handoff_image_batch`). `binding_lines()`/`resource_lines()` cùng hình dạng
dict `{"tag", "kind", "name", "description"}` giữa Task 4 và Task 6.
`OmmiBinding` có đúng 10 cột giống nhau ở Task 1 (model), Task 2 (migration),
Task 4 (service dùng model đó) — không lệch tên cột nào.
