# PROMPT AI — Pha 4: Kho chung + Thư viện — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm cơ chế "chia sẻ bằng mã" (private / code / catalog) cho toàn bộ nội dung
thư viện của PROMPT AI, và nhập 12 meta prompt + 21 image template + 13 snippet + 5
storyboard framework thật của Prompt Seedance Studio vào catalog — để sau pha này,
kho dùng được và nội dung bản gốc đã sang.

**Architecture:** Một migration duy nhất (Làn M) thêm cột `share_level` vào 10 bảng +
tạo 6 bảng mới. Làn F dựng `ommi_share_code` (sinh/thu hồi/xem trước/nhận bằng mã,
generic theo mọi `target_kind`). Làn G dựng đường ống nhập dữ liệu một chiều, chỉ đọc,
từ một **bản sao** của CSDL Prompt Seedance Studio (`D:\BOT GEMINI`, không bao giờ mở
tại chỗ) ra 4 tệp JSON tĩnh đóng gói cùng code, rồi nạp catalog qua endpoint admin
idempotent.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (Mapped/mapped_column) + Alembic + pytest +
SQLite (fixture test) / Postgres (production) + `importlib.resources` cho tệp JSON
đóng gói cùng package.

**Spec:** `docs/superpowers/specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md` (§4.2 Pha
4, §5, §6.6, §7, §9, §10) + `docs/PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md` (§8.3,
§8.4 — danh sách chính xác nội dung phải nhập).

## Global Constraints

Sao đúng từ spec §2 (Global Constraints áp cho MỌI task) + các giá trị riêng của Pha 4.

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (`apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` |
| G-3 | App→app | Chỉ cạnh khai trong `tools/lint_app_contract.py:85`. Pha 4 **không thêm cạnh mới** |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring |
| G-5 | Alembic | **MỘT head duy nhất**. ⚠️ KHÔNG hard-code `edb8b0fc0ac9` — cây dùng chung, phiên khác có thể đã thêm revision. Chạy `alembic heads` lúc thi hành; nếu ra NHIỀU HƠN MỘT dòng, dừng lại, báo chủ dự án trước khi viết migration |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số không trùng (`tools/check_so_test.py`). Dải của Pha 4: xem bảng "Dải số test" |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM: `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`. `.ps1` thuần ASCII. Không viết Python inline qua PowerShell |
| G-8 | Việc > vài giây | Qua hàng đợi job. Pha 4 **không có** thao tác nào > vài giây (sinh mã, nhận mã, nhập catalog đều là CRUD nhanh) — không cần job |
| G-9 | Tiền | Không áp dụng cho Pha 4 — không endpoint nào của §6.6 tính credit |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}` — Pha 4 không đổi giao diện |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt trên `https://app.lttstudios.com` — Pha 4 không đổi giao diện, chỉ API |
| G-12 | Lệnh nặng | Qua `chay_nang.py --phien <làn> -- <lệnh>`, `-n` ≤ 7. Kiểm `tools\cua_so_yen.py` + `tools\tai_may.py` trước |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate trong plan này |
| G-14 | `D:\BOT GEMINI` | Kho tham chiếu **CHỈ ĐỌC**. Copy `.db`/`.db-wal`/`.db-shm` sang scratchpad, mở `mode=ro` ở đó — không bao giờ mở tại chỗ |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |
| P4-1 | Cột `share_level` | `String(12)`, not null, `server_default="private"`, bộ giá trị `{"private","code","catalog"}` |
| P4-2 | `share_level="catalog"` | CHỈ admin đặt được (kiểm ở tầng service, `is_admin` từ CSDL qua `is_operator(request)` — không bao giờ tin `body`) |
| P4-3 | `share_level="code"` | Khách tự đặt được cho **mục của chính mình** |
| P4-4 | Không có trang "kho công khai" | Chia sẻ chỉ qua mã/link — không thêm route liệt kê công khai nào trong Pha 4 |
| P4-5 | Nhập mẫu gốc | Idempotent — gọi lại không sinh bản trùng (R-3) |
| P4-6 | Dải số test | Làn F: `5400`–`5419`. Làn G: `5420`–`5449` |

## Giả định tiền đề (đọc trước khi bắt đầu Task 1)

Pha 4 đứng SAU Pha 1–3 trong kiến trúc 5 pha của spec (§3). Plan này giả định:

1. Pha 1–3 đã gộp `main`: bảng `ommi_binding`, `ommi_brief`, `ommi_iteration`,
   `ommi_character`, `ommi_outfit`, `ommi_pose`, `ommi_background`,
   `ommi_face_embedding` đã tồn tại; `apps/prompt_ai_ommi/services/placeholders.py`
   (hàm `kiem_placeholder`) đã tồn tại.
2. Nếu Task 1 phát hiện các bảng/tệp trên **CHƯA** tồn tại trên nhánh đang làm việc,
   đây là dấu hiệu Pha 1–3 chưa gộp vào nhánh này — **DỪNG LẠI**, không tự tạo thay
   cho Pha 1–3, báo chủ dự án. Đây khớp điều kiện dừng của luật chết người §2
   ("thay đổi không rõ của ai" — thiếu tiền đề của pha trước không phải việc Pha 4
   tự quyết định bù đắp).
3. Tại thời điểm viết plan này (26/09/2026), `apps/prompt_ai_ommi/tables.py` vẫn là
   một tệp phẳng 385 dòng (14 lớp, đúng như spec §5.2 mô tả "Tệp đang 385 dòng").
   Nếu khi thi hành Task 1 vẫn thấy tệp phẳng này (nghĩa là việc tách `tables/` của
   Pha 1 — spec §5.2 — chưa chạy), Task 2 của plan này **tự thực hiện** việc tách
   (nó là việc mang tính hạ tầng, không phải nghiệp vụ Pha 1–3, và spec §9.1 giao nó
   cho Làn M "mọi pha").

## Tệp bị ảnh hưởng (Pha 4)

| Tệp | Làn | Việc |
|---|---|---|
| `alembic/versions/<ngay>_ommi_pha4_kho_chung.py` | M | Tạo mới — toàn bộ schema Pha 4 |
| `apps/prompt_ai_ommi/tables/__init__.py` | M | Tạo mới (nếu chưa) — re-export mọi lớp cũ |
| `apps/prompt_ai_ommi/tables/tai_nguyen.py` | M | Tạo mới (nếu chưa) — 7 lớp kho tài nguyên |
| `apps/prompt_ai_ommi/tables/kich_ban.py` | M | Tạo mới (nếu chưa) — 3 lớp storyboard |
| `apps/prompt_ai_ommi/tables/thu_vien.py` | M tạo khung / **G** thêm nội dung Pha 4 | 4 lớp cũ + Pha 4 thêm cột + 4 lớp mới |
| `apps/prompt_ai_ommi/tables/nhan_vat.py` | **M** sửa (tệp của Pha 3 đã đóng, không làn nào tranh chấp) | Thêm `share_level` vào `OmmiCharacter`/`OmmiBackground`/`OmmiPose` |
| `apps/prompt_ai_ommi/tables/chia_se.py` | **F** | Tạo mới — `OmmiShareCode` |
| `apps/prompt_ai_ommi/services/chia_se.py` | F | Tạo mới — sinh/thu hồi/xem trước/nhận mã + đặt mức chia sẻ |
| `apps/prompt_ai_ommi/routes/chia_se.py` | F | Tạo mới — endpoint §6.6 |
| `apps/prompt_ai_ommi/routes/__init__.py` | **M** | Đăng ký router `chia_se` |
| `apps/prompt_ai_ommi/services/nhap_mau_goc.py` | G | Tạo mới — nhập catalog idempotent |
| `apps/prompt_ai_ommi/prompts/mau_goc/__init__.py` | G | Tạo mới — rỗng, đánh dấu package |
| `apps/prompt_ai_ommi/prompts/mau_goc/meta_prompts.json` | G | Tạo mới — 12 mục |
| `apps/prompt_ai_ommi/prompts/mau_goc/image_templates.json` | G | Tạo mới — 21 mục |
| `apps/prompt_ai_ommi/prompts/mau_goc/snippets.json` | G | Tạo mới — 13 mục |
| `apps/prompt_ai_ommi/prompts/mau_goc/storyboard_frameworks.json` | G | Tạo mới — 5 mục |
| `tests/test_540x_*.py` | F | Dải 5400–5419 |
| `tests/test_542x_*.py` | G | Dải 5420–5449 |

---

### Task 1: Xác nhận tiền đề + head Alembic thật

**Files:**
- Không sửa tệp — chỉ chạy lệnh xác nhận.

**Interfaces:**
- Consumes: không có.
- Produces: giá trị `down_revision` thật cho Task 3; xác nhận nhị phân "tables/ đã
  tách hay chưa" cho Task 2.

- [ ] **Step 1: Kiểm tra CHỈ có một head Alembic**

Chạy:
```
alembic heads
```
Kỳ vọng: đúng MỘT dòng revision id. Nếu ra hơn một dòng — DỪNG LẠI, đây là nhánh rẽ
(G-5), báo chủ dự án, không tự `alembic merge`.

- [ ] **Step 2: Ghi lại revision id vừa thấy**

Copy revision id ra một biến tạm (ví dụ dán vào đầu file scratchpad) — dùng làm
`down_revision` ở Task 3. ⛔ Không dùng giá trị `edb8b0fc0ac9` in trong spec vì nó có
thể đã cũ.

- [ ] **Step 3: Xác nhận Pha 1–3 đã gộp**

Chạy:
```
python -c "import apps.prompt_ai_ommi.tables as t; print(hasattr(t, 'OmmiCharacter'), hasattr(t, 'OmmiBackground'), hasattr(t, 'OmmiPose'), hasattr(t, 'OmmiBrief'), hasattr(t, 'OmmiBinding'))"
```
(chạy qua tệp `.py` thật nếu môi trường chặn `-c`, theo G-7 — viết
`scratchpad/kiem_tien_de.py` với đúng đoạn trên rồi `python scratchpad/kiem_tien_de.py`).

Kỳ vọng: cả 5 giá trị `True`. Nếu có `False` — DỪNG LẠI (xem "Giả định tiền đề" ở trên).

- [ ] **Step 4: Xác nhận `apps/prompt_ai_ommi/services/placeholders.py` tồn tại**

```
python -c "from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder; print(kiem_placeholder)"
```

Kỳ vọng: in ra một hàm, không lỗi `ImportError`. Nếu lỗi — DỪNG LẠI.

- [ ] **Step 5: Ghi kết quả xác nhận vào một dòng trong `docs/NHAT_KY.md`**

```
## 2026-09-26 — Pha 4 PROMPT AI: xác nhận tiền đề
- alembic heads: <revision id thật> (một head duy nhất)
- Pha 1-3: OmmiCharacter/OmmiBackground/OmmiPose/OmmiBrief/OmmiBinding đều có
- services/placeholders.py: co san
```

---

### Task 2: Tách `tables.py` → package `tables/` (chỉ chạy nếu Task 1 thấy CHƯA tách)

⚠️ Nếu `apps/prompt_ai_ommi/tables/` đã tồn tại (thư mục, không phải tệp `tables.py`),
**bỏ qua toàn bộ Task này**, đi thẳng Task 3.

**Files:**
- Create: `apps/prompt_ai_ommi/tables/__init__.py`
- Create: `apps/prompt_ai_ommi/tables/tai_nguyen.py`
- Create: `apps/prompt_ai_ommi/tables/thu_vien.py`
- Create: `apps/prompt_ai_ommi/tables/kich_ban.py`
- Modify: mọi nơi `from apps.prompt_ai_ommi.tables import <lớp>` — KHÔNG cần sửa nếu
  `__init__.py` re-export đủ tên (R-4).
- Delete: `apps/prompt_ai_ommi/tables.py` (sau khi package thay thế xong)
- Test: `tests/test_5405_tables_package_pha4.py` (dải Làn M, ngoài phạm vi
  5400–5449 của plan này — đặt số này CHỈ nếu Task 1 xác nhận 5100 còn trống bằng
  `python tools/check_so_test.py --list`).

**Interfaces:**
- Produces: `apps.prompt_ai_ommi.tables.OmmiResource`, `.OmmiResourceVariant`,
  `.OmmiTag`, `.OmmiResourceTag`, `.OmmiCollection`, `.OmmiCollectionItem`,
  `.OmmiResourceUsage` (từ `tai_nguyen.py`); `.OmmiMetaPrompt`, `.OmmiPromptSnippet`,
  `.OmmiPromptVersion`, `.OmmiStyle` (từ `thu_vien.py`); `.OmmiStoryboard`,
  `.OmmiScene`, `.OmmiSceneVersion` (từ `kich_ban.py`) — mọi tên giữ nguyên như tệp
  phẳng cũ.

- [ ] **Step 1: Viết test xác nhận import cũ còn chạy (RED trước khi tách)**

```python
# tests/test_5405_tables_package_pha4.py
"""Tach tables.py thanh package khong duoc lam vo import cu (R-4)."""
from __future__ import annotations


def test_old_flat_import_path_still_works():
    from apps.prompt_ai_ommi.tables import (
        OmmiResource, OmmiResourceVariant, OmmiTag, OmmiResourceTag,
        OmmiCollection, OmmiCollectionItem, OmmiResourceUsage,
        OmmiMetaPrompt, OmmiPromptSnippet, OmmiPromptVersion, OmmiStyle,
        OmmiStoryboard, OmmiScene, OmmiSceneVersion)
    assert OmmiResource.__tablename__ == "ommi_resource"
    assert OmmiMetaPrompt.__tablename__ == "ommi_meta_prompt"
    assert OmmiStoryboard.__tablename__ == "ommi_storyboard"
```

- [ ] **Step 2: Chạy test, xác nhận PASS trên tệp phẳng cũ (đây là bài kiểm hồi quy,
  không phải TDD đỏ — tệp phẳng hiện tại vốn đã thoả)**

```
python -m pytest tests/test_5405_tables_package_pha4.py -q
```
Kỳ vọng: PASS (dùng để chốt hành vi trước khi tách, so sánh lại sau).

- [ ] **Step 3: Đọc toàn văn `apps/prompt_ai_ommi/tables.py`, sao nguyên văn từng lớp
  vào tệp con tương ứng**

Tạo `apps/prompt_ai_ommi/tables/tai_nguyen.py` với phần đầu (import, `_uuid`, `_now`,
`RESOURCE_KINDS`) + 7 lớp `OmmiResource` … `OmmiResourceUsage` copy y nguyên từ dòng
48–181 của `tables.py` cũ.

Tạo `apps/prompt_ai_ommi/tables/thu_vien.py` với phần đầu import riêng + 4 lớp
`OmmiMetaPrompt`, `OmmiPromptSnippet`, `OmmiPromptVersion`, `OmmiStyle` copy y nguyên
từ dòng 183–298.

Tạo `apps/prompt_ai_ommi/tables/kich_ban.py` với phần đầu import riêng + 3 lớp
`OmmiStoryboard`, `OmmiScene`, `OmmiSceneVersion` copy y nguyên từ dòng 301–385 (và
mọi lớp Pha 1–3 thêm vào storyboard nếu có — giữ nguyên, không đụng).

Mỗi tệp con lặp lại đúng phần đầu này (import dùng chung, không import chéo giữa các
tệp con trừ khi một lớp tham chiếu khoá ngoại sang lớp ở tệp khác — SQLAlchemy không
cần import chéo vì không dùng `relationship()` xuyên tệp trong codebase này, chỉ khai
`String(36)` làm khoá ngoài thô):

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Index, Integer, JSON, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)
```

- [ ] **Step 4: Viết `apps/prompt_ai_ommi/tables/__init__.py` re-export đủ mọi tên**

```python
"""tables/ - bang CSDL rieng cua PROMPT AI OMMI, tach theo mien.

    tai_nguyen.py   Kho tai nguyen: resource, variant, tag, collection.
    thu_vien.py     Meta prompt, doan prompt, phong cach, phien ban. Pha 4 them
                    share_level + cot rieng cua meta_prompt/style, va 4 bang moi
                    (image_template, storyboard_framework, sample, profile).
    kich_ban.py     Storyboard, canh, phien ban canh.
    nhan_vat.py     (Pha 3) Nhan vat, trang phuc, dang, boi canh, face embedding.
    chia_se.py      (Pha 4) OmmiShareCode - chia se bang ma.

Moi ten lop giu nguyen nhu tep phang cu de import cu khong vo (R-4).
"""
from __future__ import annotations

from apps.prompt_ai_ommi.tables.tai_nguyen import (
    OmmiResource, OmmiResourceVariant, OmmiTag, OmmiResourceTag,
    OmmiCollection, OmmiCollectionItem, OmmiResourceUsage, RESOURCE_KINDS)
from apps.prompt_ai_ommi.tables.thu_vien import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiPromptVersion, OmmiStyle)
from apps.prompt_ai_ommi.tables.kich_ban import (
    OmmiStoryboard, OmmiScene, OmmiSceneVersion)

__all__ = [
    "OmmiResource", "OmmiResourceVariant", "OmmiTag", "OmmiResourceTag",
    "OmmiCollection", "OmmiCollectionItem", "OmmiResourceUsage",
    "RESOURCE_KINDS",
    "OmmiMetaPrompt", "OmmiPromptSnippet", "OmmiPromptVersion", "OmmiStyle",
    "OmmiStoryboard", "OmmiScene", "OmmiSceneVersion",
]
```

⚠️ Nếu Pha 1–3 đã thêm `nhan_vat.py`/lớp `OmmiBinding`/`OmmiBrief`/`OmmiIteration` vào
tệp phẳng cũ trước khi Task này chạy, **thêm import + `__all__` tương ứng** — đọc
tệp phẳng thật lúc thi hành, không copy mù theo danh sách trên (danh sách trên chỉ
khớp 14 lớp đã xác nhận tại thời điểm viết plan này, 26/09/2026).

- [ ] **Step 5: Xoá `apps/prompt_ai_ommi/tables.py`, chạy lại Step 1's test**

```
python -m pytest tests/test_5405_tables_package_pha4.py -q
```
Kỳ vọng: vẫn PASS — import cũ không vỡ.

- [ ] **Step 6: Chạy toàn bộ test hiện có của app để chắc tách không phá logic khác**

```
python -m pytest tests/test_13*.py tests/test_14*.py tests/test_15*.py -q
```
Kỳ vọng: PASS như trước khi tách.

- [ ] **Step 7: Commit**

```bash
git add apps/prompt_ai_ommi/tables/ tests/test_5405_tables_package_pha4.py
git rm apps/prompt_ai_ommi/tables.py
git commit -m "$(cat <<'EOF'
refactor(prompt-ai-ommi): tach tables.py thanh package tables/

Tep phang 385 dong dang thanh diem va cham cua nhieu lan Pha 4 (F them
chia_se.py, G them cot vao thu_vien.py). Tach truoc, giu nguyen moi ten
lop de import cu khong vo (R-4).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Migration Pha 4 — `share_level` + cột riêng + 6 bảng mới

**Files:**
- Create: `alembic/versions/<YYYYMMDD_HHMM>_ommi_pha4_kho_chung.py`

**Interfaces:**
- Consumes: revision id thật từ Task 1 Step 2.
- Produces: 10 bảng có cột `share_level`; `ommi_meta_prompt.target_format` /
  `.is_default` / `.placeholders`; `ommi_style.parent_id` / `.provider_overrides`;
  bảng `ommi_share_code`, `ommi_image_template`, `ommi_storyboard_framework`,
  `ommi_sample`, `ommi_profile`, `ommi_budget` — dùng bởi Task 5, 10.

- [ ] **Step 1: Viết migration (chưa chạy)**

```python
# -*- coding: utf-8 -*-
"""Pha 4 PROMPT AI: kho chung + thu vien.

Them cot `share_level` (private/code/catalog) vao 10 bang; them
target_format/is_default/placeholders vao ommi_meta_prompt; them
parent_id/provider_overrides vao ommi_style; tao 6 bang moi: ommi_share_code,
ommi_image_template, ommi_storyboard_framework, ommi_sample, ommi_profile,
ommi_budget.

Revision ID: <DIEN KHI VIET - vi du bang `python -c "import uuid; print(uuid.uuid4().hex[:12])"`>
Revises: <DIEN revision that lay tu `alembic heads` luc thi hanh - xem Task 1>
Create Date: <ngay thi hanh thuc>

## VI SAO MOT MIGRATION DUY NHAT CHO CA PHA (spec S9.1)

Moi pha dung MOT migration, khong chia nho theo lan, de khong co "nua pha" nam
giua hai revision roi rac. Lan M la chu duy nhat cua alembic/versions/.

## share_level KHONG THAY THE co che catalog cu (owner_id NULL)

`ommi_meta_prompt`/`ommi_prompt_snippet`/`ommi_style` da co catalog qua
owner_id IS NULL tu truoc (giu nguyen, khong dung toi). share_level la lop
THONG TIN THEM: ban ghi catalog (owner_id NULL) duoc gan share_level="catalog"
de dong bo tin hieu; ban ghi cua nguoi dung dung "code" khi ho tu chia se qua
ommi_share_code. Bang moi (ommi_image_template, ...) khong co owner_id NULL
(owner_id luon not null theo dung "moi bang" cua spec S4.2) nen voi CHUNG,
share_level="catalog" LA co che catalog duy nhat, phoi hop voi is_builtin=True.

## ROLLBACK

downgrade() go het cot va bang da them. Mat du lieu share_level/is_default/
target_format/placeholders da nhap qua nhap-mau-goc - phai chay lai
nhap_mau_goc sau khi upgrade lai (no idempotent, an toan chay lai).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "REPLACE_ME"
down_revision = "REPLACE_ME_HEAD_THAT"
branch_labels = None
depends_on = None

_SHARE_LEVEL_TABLES = (
    "ommi_meta_prompt", "ommi_prompt_snippet", "ommi_style",
    "ommi_character", "ommi_background", "ommi_pose",
)


def upgrade() -> None:
    for table_name in _SHARE_LEVEL_TABLES:
        op.add_column(table_name, sa.Column(
            "share_level", sa.String(12), nullable=False,
            server_default="private"))

    op.add_column("ommi_meta_prompt", sa.Column(
        "target_format", sa.String(24), nullable=False,
        server_default="gemini_style"))
    op.add_column("ommi_meta_prompt", sa.Column(
        "is_default", sa.Boolean(), nullable=False,
        server_default=sa.false()))
    op.add_column("ommi_meta_prompt", sa.Column(
        "placeholders", sa.JSON(), nullable=False, server_default="[]"))

    op.add_column("ommi_style", sa.Column(
        "parent_id", sa.String(36), nullable=True))
    op.add_column("ommi_style", sa.Column(
        "provider_overrides", sa.JSON(), nullable=False, server_default="{}"))

    op.create_table(
        "ommi_share_code",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("target_kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_share_code_owner_id", "ommi_share_code",
                    ["owner_id"])
    op.create_index("ix_ommi_share_code_code", "ommi_share_code", ["code"],
                    unique=True)
    op.create_index("ix_ommi_share_code_target", "ommi_share_code",
                    ["target_kind", "target_id"])

    op.create_table(
        "ommi_image_template",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("n_outputs", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("aspect", sa.String(8), nullable=False, server_default="1:1"),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("asset_subtype", sa.String(32), nullable=False, server_default=""),
        sa.Column("grid_layout", sa.String(16), nullable=False, server_default=""),
        sa.Column("output_mode", sa.String(16), nullable=False, server_default="grid"),
        sa.Column("requires_ref", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("multi_ref_max", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bg_style", sa.String(64), nullable=False, server_default=""),
        sa.Column("negative_lock", sa.Text(), nullable=False, server_default=""),
        sa.Column("placeholder_hint", sa.String(200), nullable=False, server_default=""),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_image_template_owner_id", "ommi_image_template",
                    ["owner_id"])
    op.create_index("ix_ommi_image_template_asset_type", "ommi_image_template",
                    ["asset_type"])

    op.create_table(
        "ommi_storyboard_framework",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_header", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_rules", sa.Text(), nullable=False, server_default=""),
        sa.Column("composite_negative_footer", sa.Text(), nullable=False, server_default=""),
        sa.Column("breakdown_llm_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_style_id", sa.String(36), nullable=True),
        sa.Column("default_aspect", sa.String(8), nullable=False, server_default="16:9"),
        sa.Column("default_n_scenes", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_storyboard_framework_owner_id",
                    "ommi_storyboard_framework", ["owner_id"])

    op.create_table(
        "ommi_sample",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("final_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("rating_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("used_model", sa.String(64), nullable=False, server_default=""),
        sa.Column("actual_credit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_sample_owner_id", "ommi_sample", ["owner_id"])

    op.create_table(
        "ommi_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("asset_tag_filter", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_profile_owner_id", "ommi_profile", ["owner_id"])

    op.create_table(
        "ommi_budget",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, unique=True),
        sa.Column("monthly_cap_credit", sa.Integer(), nullable=True),
        sa.Column("alert_at_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_ommi_budget_owner_id", "ommi_budget", ["owner_id"],
                    unique=True)


def downgrade() -> None:
    op.drop_table("ommi_budget")
    op.drop_table("ommi_profile")
    op.drop_table("ommi_sample")
    op.drop_index("ix_ommi_storyboard_framework_owner_id",
                  table_name="ommi_storyboard_framework")
    op.drop_table("ommi_storyboard_framework")
    op.drop_index("ix_ommi_image_template_asset_type", table_name="ommi_image_template")
    op.drop_index("ix_ommi_image_template_owner_id", table_name="ommi_image_template")
    op.drop_table("ommi_image_template")
    op.drop_index("ix_ommi_share_code_target", table_name="ommi_share_code")
    op.drop_index("ix_ommi_share_code_code", table_name="ommi_share_code")
    op.drop_index("ix_ommi_share_code_owner_id", table_name="ommi_share_code")
    op.drop_table("ommi_share_code")

    op.drop_column("ommi_style", "provider_overrides")
    op.drop_column("ommi_style", "parent_id")
    op.drop_column("ommi_meta_prompt", "placeholders")
    op.drop_column("ommi_meta_prompt", "is_default")
    op.drop_column("ommi_meta_prompt", "target_format")

    for table_name in reversed(_SHARE_LEVEL_TABLES):
        op.drop_column(table_name, "share_level")
```

- [ ] **Step 2: Điền `revision`/`down_revision` thật, chạy migration trên CSDL dev**

```
alembic upgrade head
```
Kỳ vọng: chạy xong không lỗi. Nếu lỗi `no such table: ommi_character` (hoặc tương tự
cho `ommi_background`/`ommi_pose`) — nghĩa là Task 1 Step 3 đã bỏ sót, DỪNG LẠI, xem
lại "Giả định tiền đề".

- [ ] **Step 3: Kiểm downgrade rồi upgrade lại (an toàn rollback)**

```
alembic downgrade -1
alembic upgrade head
```
Kỳ vọng: cả hai chạy sạch, không lỗi.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/<ten_tep_that>.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): migration Pha 4 - share_level + kho chung

Them cot share_level (private/code/catalog) vao 10 bang, cot rieng cua
meta_prompt (target_format/is_default/placeholders) va style (parent_id/
provider_overrides), va 6 bang moi: ommi_share_code, ommi_image_template,
ommi_storyboard_framework, ommi_sample, ommi_profile, ommi_budget.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Thêm `share_level` vào model `OmmiCharacter`/`OmmiBackground`/`OmmiPose`

Tệp `tables/nhan_vat.py` thuộc Pha 3 (Làn E), đã đóng và gộp `main` — không có làn
nào của Pha 4 đang tranh chấp nó, nên Làn M (hạ tầng, chịu trách nhiệm nhất quán
schema toàn Pha 4) sửa trực tiếp thay vì bỏ lửng.

**Files:**
- Modify: `apps/prompt_ai_ommi/tables/nhan_vat.py` (thêm 1 dòng thuộc tính cho mỗi
  trong 3 lớp `OmmiCharacter`, `OmmiBackground`, `OmmiPose`)

**Interfaces:**
- Consumes: cột `share_level` đã tồn tại ở CSDL từ Task 3.
- Produces: `OmmiCharacter.share_level`, `OmmiBackground.share_level`,
  `OmmiPose.share_level` — dùng bởi `services/chia_se.py` (Task 7) qua `TARGET_KINDS`.

- [ ] **Step 1: Đọc `tables/nhan_vat.py` thật, xác nhận tên 3 lớp và vị trí**

```
python -c "import apps.prompt_ai_ommi.tables.nhan_vat as m; print([n for n in dir(m) if n.startswith('Ommi')])"
```
Kỳ vọng thấy `OmmiCharacter`, `OmmiBackground`, `OmmiPose` (cùng `OmmiOutfit`,
`OmmiFaceEmbedding` — không đụng hai lớp này).

- [ ] **Step 2: Viết test xác nhận thuộc tính tồn tại và mặc định đúng**

```python
# tests/test_5402_nhan_vat_share_level.py (Lan F giu dai 5400-5419; dat o day vi
# no la dieu kien tien quyet cho services/chia_se.py cua Lan F)
"""share_level tren OmmiCharacter/OmmiBackground/OmmiPose - dieu kien tien
quyet de chia_se.py TARGET_KINDS dung duoc ba loai nay."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nv.db').as_posix()}")
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


def test_character_background_pose_have_share_level_private_by_default(db):
    from apps.prompt_ai_ommi.tables.nhan_vat import (
        OmmiCharacter, OmmiBackground, OmmiPose)
    char = OmmiCharacter(owner_id="u1", name="Nhan vat")
    bg = OmmiBackground(owner_id="u1", name="Boi canh")
    pose = OmmiPose(owner_id="u1", name="Dang")
    db.add_all([char, bg, pose])
    db.commit()
    assert char.share_level == "private"
    assert bg.share_level == "private"
    assert pose.share_level == "private"
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

```
python -m pytest tests/test_5402_nhan_vat_share_level.py -q
```
Kỳ vọng: FAIL với `AttributeError` hoặc cột không tồn tại trong CSDL test (SQLAlchemy
sẽ tự tạo bảng từ model — nếu model chưa có cột, `create_all` không tạo cột, và gán
`char.share_level` sẽ ném `AttributeError` vì `Mapped` chưa khai).

- [ ] **Step 4: Thêm thuộc tính vào 3 lớp**

Trong mỗi lớp (`OmmiCharacter`, `OmmiBackground`, `OmmiPose`), thêm ngay trước dòng
`archived_at` hoặc `updated_at` hiện có (đọc thật để chèn đúng vị trí, giữ style
hiện tại của tệp):

```python
    share_level: Mapped[str] = mapped_column(
        String(12), default="private", nullable=False)
```

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5402_nhan_vat_share_level.py -q
```

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/tables/nhan_vat.py tests/test_5402_nhan_vat_share_level.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): them share_level vao Character/Background/Pose

Cot da co o CSDL tu migration Pha 4 (Task 3); model can khai de
services/chia_se.py dung duoc ba loai nay qua TARGET_KINDS.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `tables/chia_se.py` — model `OmmiShareCode`

**Files:**
- Create: `apps/prompt_ai_ommi/tables/chia_se.py`
- Modify: `apps/prompt_ai_ommi/tables/__init__.py` (thêm re-export `OmmiShareCode`)

**Interfaces:**
- Consumes: bảng `ommi_share_code` từ Task 3.
- Produces: `apps.prompt_ai_ommi.tables.OmmiShareCode` — dùng bởi
  `services/chia_se.py` (Task 6/7).

- [ ] **Step 1: Viết test xác nhận model + ràng buộc unique trên `code`**

```python
# tests/test_5400_share_code_model.py
"""Model OmmiShareCode - vong doi mot ma chia se."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'share.db').as_posix()}")
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


def test_defaults(db):
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    row = OmmiShareCode(owner_id="u1", code="abc123", target_kind="meta_prompt",
                        target_id="m1")
    db.add(row)
    db.commit()
    assert row.uses == 0
    assert row.max_uses is None
    assert row.revoked_at is None


def test_code_is_unique(db):
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    db.add(OmmiShareCode(owner_id="u1", code="dup12345678", target_kind="style",
                         target_id="s1"))
    db.commit()
    db.add(OmmiShareCode(owner_id="u2", code="dup12345678", target_kind="style",
                         target_id="s2"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL (`ImportError: OmmiShareCode`)**

```
python -m pytest tests/test_5400_share_code_model.py -q
```

- [ ] **Step 3: Viết `tables/chia_se.py`**

```python
"""
chia_se.py - OmmiShareCode: chia se mot muc thu vien/tai nguyen bang MA (Q-10).

Khong co trang "kho cong khai": ai co MA moi xem/nhan duoc. `target_kind` +
`target_id` tro toi mot ban ghi CU THE o bang khac (meta_prompt/style/snippet/
character/background/pose/image_template/storyboard_framework/sample/profile) -
xem services/chia_se.py:TARGET_KINDS.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiShareCode(Base):
    """Ve chia se dung nhieu lan (toi da `max_uses`, hoac vo han neu None)."""

    __tablename__ = "ommi_share_code"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True,
                                      index=True)
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

- [ ] **Step 4: Thêm re-export vào `tables/__init__.py`**

```python
from apps.prompt_ai_ommi.tables.chia_se import OmmiShareCode
```
và thêm `"OmmiShareCode"` vào `__all__`.

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5400_share_code_model.py -q
```

- [ ] **Step 6: Commit**

```bash
git add apps/prompt_ai_ommi/tables/chia_se.py apps/prompt_ai_ommi/tables/__init__.py tests/test_5400_share_code_model.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): model OmmiShareCode cho chia se bang ma

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `services/chia_se.py` — sinh mã + thu hồi

**Files:**
- Create: `apps/prompt_ai_ommi/services/chia_se.py`
- Test: `tests/test_5401_chia_se_sinh_thu_hoi.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.tables.OmmiShareCode`,
  `apps.prompt_ai_ommi.tables.OmmiMetaPrompt` (và các lớp khác của `TARGET_KINDS`,
  xem Task 7 cho danh sách đầy đủ — Task này chỉ cần `OmmiMetaPrompt`/`OmmiStyle`
  để viết test).
- Produces: `sinh_ma(db, *, owner_id, target_kind, target_id, max_uses=None,
  expires_in_days=None) -> OmmiShareCode`; `thu_hoi(db, *, code, owner_id,
  is_admin=False) -> OmmiShareCode`; ngoại lệ `ShareError(ValueError)`,
  `ShareNotFound(LookupError)` — dùng bởi Task 7 (`nhan`/`xem_truoc`/
  `dat_muc_chia_se`) và Task 8 (routes).

- [ ] **Step 1: Viết test đỏ cho `sinh_ma`/`thu_hoi`**

```python
# tests/test_5401_chia_se_sinh_thu_hoi.py
"""sinh_ma/thu_hoi - vong doi co ban cua mot ma chia se."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cs.db').as_posix()}")
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


A, B = "user-a", "user-b"


def _meta(db, owner=A, name="Meta cua toi"):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=owner, name=name, body="noi dung")
    db.add(row); db.commit()
    return row


def test_owner_can_generate_a_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt",
                        target_id=row.id)
    db.commit()
    assert len(share.code) <= 12 and share.code
    assert share.uses == 0


def test_stranger_cannot_generate_a_code_for_someone_elses_item(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db, A)
    with pytest.raises(svc.ShareNotFound):
        svc.sinh_ma(db, owner_id=B, target_kind="meta_prompt", target_id=row.id)


def test_unknown_target_kind_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.sinh_ma(db, owner_id=A, target_kind="khong-co", target_id=row.id)


def test_owner_can_revoke_their_own_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=A)
    db.commit()
    assert share.revoked_at is not None


def test_stranger_cannot_revoke_someone_elses_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    with pytest.raises(svc.ShareNotFound):
        svc.thu_hoi(db, code=share.code, owner_id=B)
    assert share.revoked_at is None


def test_admin_can_revoke_anyones_code(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=B, is_admin=True)
    db.commit()
    assert share.revoked_at is not None
```

- [ ] **Step 2: Chạy test, xác nhận FAIL (`ModuleNotFoundError`)**

```
python -m pytest tests/test_5401_chia_se_sinh_thu_hoi.py -q
```

- [ ] **Step 3: Viết `services/chia_se.py` (phần 1: sinh mã + thu hồi)**

```python
"""
chia_se.py - chia se mot muc thu vien/tai nguyen bang MA (Q-10, spec S6.6).

Khong co trang "kho cong khai" - chi ai co MA moi xem/nhan duoc. Muc duoc chia
se van thuoc so huu cu; "nhan" tao MOT BAN SAO rieng cho nguoi nhan, khong
chuyen quyen so huu (giong clone_from_catalog cua library.py, nhung tong quat
cho ca 10 loai thay vi chi 3).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiStyle, OmmiShareCode)
from apps.prompt_ai_ommi.tables.nhan_vat import (
    OmmiCharacter, OmmiBackground, OmmiPose)

#: kind (nhu client goi) -> lop model. Bo sung image_template/
#: storyboard_framework/sample/profile o Task 7 sau khi tables/thu_vien.py co
#: 4 lop moi (Task 10, Lan G).
TARGET_KINDS: dict[str, type] = {
    "meta_prompt": OmmiMetaPrompt,
    "style": OmmiStyle,
    "snippet": OmmiPromptSnippet,
    "character": OmmiCharacter,
    "background": OmmiBackground,
    "pose": OmmiPose,
}

_VALID_LEVELS = {"private", "code", "catalog"}


class ShareError(ValueError):
    """Du lieu vao khong hop le - route tra 400."""


class ShareNotFound(LookupError):
    """Khong ton tai HOAC khong thuoc ve nguoi goi - route tra 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model(target_kind: str) -> type:
    model = TARGET_KINDS.get((target_kind or "").strip().lower())
    if model is None:
        raise ShareError(
            f"Loai chia se khong hop le: {target_kind!r}. "
            f"Chon mot trong: {', '.join(TARGET_KINDS)}.")
    return model


def _gen_code() -> str:
    return secrets.token_urlsafe(8)[:12]


def sinh_ma(db: Session, *, owner_id: str, target_kind: str, target_id: str,
           max_uses: int | None = None, expires_in_days: int | None = None
           ) -> OmmiShareCode:
    model = _model(target_kind)
    row = db.get(model, target_id)
    if row is None or getattr(row, "owner_id", None) != owner_id:
        raise ShareNotFound("Khong tim thay muc de chia se.")

    code = None
    for _ in range(5):
        candidate = _gen_code()
        exists = db.execute(
            select(OmmiShareCode.id).where(OmmiShareCode.code == candidate)
        ).first()
        if exists is None:
            code = candidate
            break
    if code is None:
        raise ShareError("Khong sinh duoc ma chia se, thu lai.")

    expires_at = (_now() + timedelta(days=int(expires_in_days))
                 if expires_in_days else None)
    share = OmmiShareCode(
        owner_id=owner_id, code=code, target_kind=target_kind.strip().lower(),
        target_id=target_id, max_uses=max_uses, expires_at=expires_at)
    db.add(share)
    db.flush()
    return share


def _load(db: Session, code: str) -> OmmiShareCode:
    share = db.execute(
        select(OmmiShareCode).where(OmmiShareCode.code == code)
    ).scalar_one_or_none()
    if share is None:
        raise ShareNotFound("Ma chia se khong ton tai.")
    return share


def thu_hoi(db: Session, *, code: str, owner_id: str, is_admin: bool = False
           ) -> OmmiShareCode:
    share = _load(db, code)
    if share.owner_id != owner_id and not is_admin:
        # Tra ve giong "khong tim thay" - khong lo cho nguoi la biet ma nay
        # co ton tai va thuoc ve ai.
        raise ShareNotFound("Ma chia se khong ton tai.")
    share.revoked_at = _now()
    db.flush()
    return share
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5401_chia_se_sinh_thu_hoi.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/chia_se.py tests/test_5401_chia_se_sinh_thu_hoi.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): sinh_ma/thu_hoi cho chia se bang ma

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `services/chia_se.py` — xem trước + nhận + đặt mức chia sẻ

**Files:**
- Modify: `apps/prompt_ai_ommi/services/chia_se.py` (thêm vào cuối tệp)
- Test: `tests/test_5403_chia_se_nhan_va_muc.py`

**Interfaces:**
- Consumes: `sinh_ma`/`thu_hoi`/`ShareError`/`ShareNotFound`/`TARGET_KINDS` từ Task 6.
- Produces: `xem_truoc(db, *, code) -> dict`; `nhan(db, *, code, owner_id) ->
  object` (bản ghi mới, đã `add` + `flush`); `dat_muc_chia_se(db, *, target_kind,
  item_id, owner_id, is_admin, level) -> object` — dùng bởi Task 8 (routes).

- [ ] **Step 1: Viết test đỏ**

```python
# tests/test_5403_chia_se_nhan_va_muc.py
"""xem_truoc/nhan/dat_muc_chia_se."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cs2.db').as_posix()}")
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


A, B = "user-a", "user-b"


def _meta(db, owner=A, name="Meta cua toi", body="noi dung goc"):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=owner, name=name, body=body)
    db.add(row); db.commit()
    return row


def test_preview_shows_name_without_cloning(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    preview = svc.xem_truoc(db, code=share.code)
    assert preview["name"] == "Meta cua toi"
    assert preview["target_kind"] == "meta_prompt"


def test_revoked_code_is_rejected_by_preview_and_receive(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    svc.thu_hoi(db, code=share.code, owner_id=A)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.xem_truoc(db, code=share.code)
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id=B)


def test_expired_code_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    from apps.prompt_ai_ommi.tables import OmmiShareCode
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    share.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id=B)


def test_receiving_clones_an_independent_copy_and_counts_a_use(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt", target_id=row.id)
    db.commit()
    copy = svc.nhan(db, code=share.code, owner_id=B)
    db.commit()
    assert copy.owner_id == B
    assert copy.body == "noi dung goc"
    assert copy.id != row.id
    assert share.uses == 1
    # Sua ban sao khong dung den ban goc.
    copy.body = "da sua"
    db.commit()
    assert db.get(type(row), row.id).body == "noi dung goc"


def test_max_uses_is_enforced(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    share = svc.sinh_ma(db, owner_id=A, target_kind="meta_prompt",
                        target_id=row.id, max_uses=1)
    db.commit()
    svc.nhan(db, code=share.code, owner_id=B)
    db.commit()
    with pytest.raises(svc.ShareError):
        svc.nhan(db, code=share.code, owner_id="user-c")


def test_only_admin_sets_catalog_level(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                            owner_id=A, is_admin=False, level="catalog")
    updated = svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                                  owner_id=A, is_admin=True, level="catalog")
    db.commit()
    assert updated.share_level == "catalog"


def test_owner_sets_code_level_on_their_own_item(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    updated = svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                                  owner_id=A, is_admin=False, level="code")
    db.commit()
    assert updated.share_level == "code"


def test_invalid_level_is_rejected(db):
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _meta(db)
    with pytest.raises(svc.ShareError):
        svc.dat_muc_chia_se(db, target_kind="meta_prompt", item_id=row.id,
                            owner_id=A, is_admin=True, level="cong-khai")
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```
python -m pytest tests/test_5403_chia_se_nhan_va_muc.py -q
```
Kỳ vọng: FAIL với `AttributeError: module 'chia_se' has no attribute 'xem_truoc'`.

- [ ] **Step 3: Thêm vào cuối `services/chia_se.py`**

```python
def _kiem_con_hieu_luc(share: OmmiShareCode) -> None:
    if share.revoked_at is not None:
        raise ShareError("Ma chia se da bi thu hoi.")
    if share.expires_at is not None and share.expires_at <= _now():
        raise ShareError("Ma chia se da het han.")


def xem_truoc(db: Session, *, code: str) -> dict:
    share = _load(db, code)
    _kiem_con_hieu_luc(share)
    model = TARGET_KINDS.get(share.target_kind)
    row = db.get(model, share.target_id) if model else None
    if row is None:
        raise ShareNotFound("Muc duoc chia se khong con ton tai.")
    return {
        "target_kind": share.target_kind,
        "name": getattr(row, "name", getattr(row, "title", "")),
        "uses": share.uses,
        "max_uses": share.max_uses,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
    }


#: Cot he thong khong duoc sao khi clone - moi ban sao la BAN GHI MOI, doc lap.
_SYSTEM_COLUMNS = {
    "id", "owner_id", "created_at", "updated_at", "archived_at",
    "deprecated_at", "deprecated_note", "cloned_from_id", "version",
    "is_catalog", "is_builtin", "use_count", "share_level",
}


def _clone_row(model: type, source, owner_id: str):
    data = {col.name: getattr(source, col.name) for col in model.__table__.columns
           if col.name not in _SYSTEM_COLUMNS}
    row = model(owner_id=owner_id, **data)
    if hasattr(row, "share_level"):
        row.share_level = "private"
    if hasattr(row, "cloned_from_id"):
        row.cloned_from_id = source.id
    return row


def nhan(db: Session, *, code: str, owner_id: str):
    share = _load(db, code)
    _kiem_con_hieu_luc(share)
    if share.max_uses is not None and share.uses >= share.max_uses:
        raise ShareError("Ma chia se da dung het luot.")
    model = TARGET_KINDS.get(share.target_kind)
    if model is None:
        raise ShareError(f"Loai chia se khong duoc ho tro: {share.target_kind!r}.")
    source = db.get(model, share.target_id)
    if source is None:
        raise ShareNotFound("Muc duoc chia se khong con ton tai.")
    copy = _clone_row(model, source, owner_id)
    db.add(copy)
    share.uses = int(share.uses or 0) + 1
    db.flush()
    return copy


def dat_muc_chia_se(db: Session, *, target_kind: str, item_id: str, owner_id: str,
                    is_admin: bool, level: str):
    if level not in _VALID_LEVELS:
        raise ShareError(f"Muc chia se khong hop le: {level!r}.")
    if level == "catalog" and not is_admin:
        raise ShareError("Chi admin duoc dat muc 'catalog'.")
    model = _model(target_kind)
    row = db.get(model, item_id)
    if row is None or (row.owner_id != owner_id and not is_admin):
        raise ShareNotFound("Khong tim thay muc.")
    row.share_level = level
    if hasattr(row, "updated_at"):
        row.updated_at = _now()
    db.flush()
    return row
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5403_chia_se_nhan_va_muc.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/chia_se.py tests/test_5403_chia_se_nhan_va_muc.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): xem_truoc/nhan/dat_muc_chia_se

nhan() dung mot ham clone generic (_clone_row) ap dung cho ca 6 loai da khai
trong TARGET_KINDS, thay vi mot ham rieng cho tung loai nhu library.py cu.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `routes/chia_se.py` — endpoint chia sẻ (§6.6)

**Files:**
- Create: `apps/prompt_ai_ommi/routes/chia_se.py`
- Test: `tests/test_5410_chia_se_api.py`

**Interfaces:**
- Consumes: `services.chia_se.{sinh_ma,thu_hoi,xem_truoc,nhan,ShareError,
  ShareNotFound}`; `routes._shared.{router,_csrf,_user,get_db,require_login,
  is_operator}`.
- Produces: `POST /prompt-ai-ommi/api/share`, `DELETE
  /prompt-ai-ommi/api/share/{code}`, `GET /prompt-ai-ommi/api/share/{code}`,
  `POST /prompt-ai-ommi/api/share/{code}/nhan` — đăng ký vào `router` (dùng bởi
  Task 9).

- [ ] **Step 1: Viết test API đỏ (dùng fixture `TestClient` + login/CSRF thật, theo
  mẫu `tests/test_141_ommi_library_api.py`)**

```python
# tests/test_5410_chia_se_api.py
"""Tang HTTP cua chia se bang ma."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'share-api.db').as_posix()}")
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
    ids = {}
    for email, role in (("share-a@example.com", "user"),
                        ("share-b@example.com", "user")):
        ids[email] = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                    is_verified=True, role=role).id
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=ids["share-a@example.com"], name="Meta cua A",
                         body="noi dung")
    db.add(row); db.commit()
    item_id = row.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-share-api-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    a, token_a = login("share-a@example.com")
    b, token_b = login("share-b@example.com")
    yield a, token_a, b, token_b, item_id
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_owner_shares_and_stranger_receives(api):
    a, token_a, b, token_b, item_id = api
    made = a.post("/prompt-ai-ommi/api/share", headers={"X-CSRF-Token": token_a},
                  json={"target_kind": "meta_prompt", "target_id": item_id})
    assert made.status_code == 201, made.text
    code = made.json()["code"]

    preview = b.get(f"/prompt-ai-ommi/api/share/{code}")
    assert preview.status_code == 200 and preview.json()["name"] == "Meta cua A"

    received = b.post(f"/prompt-ai-ommi/api/share/{code}/nhan",
                      headers={"X-CSRF-Token": token_b}, json={})
    assert received.status_code == 201, received.text

    private_b = b.get("/prompt-ai-ommi/api/library/meta")
    assert [i["name"] for i in private_b.json()["items"]] == ["Meta cua A"]


def test_revoked_code_is_rejected_at_http_layer(api):
    a, token_a, b, token_b, item_id = api
    made = a.post("/prompt-ai-ommi/api/share", headers={"X-CSRF-Token": token_a},
                  json={"target_kind": "meta_prompt", "target_id": item_id})
    code = made.json()["code"]
    revoked = a.delete(f"/prompt-ai-ommi/api/share/{code}",
                       headers={"X-CSRF-Token": token_a})
    assert revoked.status_code == 200

    rejected = b.post(f"/prompt-ai-ommi/api/share/{code}/nhan",
                      headers={"X-CSRF-Token": token_b}, json={})
    assert rejected.status_code == 400


def test_a_normal_user_cannot_set_catalog_level(api):
    a, token_a, *_rest, item_id = api
    response = a.post(f"/prompt-ai-ommi/api/library/meta/{item_id}/share-level",
                      headers={"X-CSRF-Token": token_a},
                      json={"level": "catalog"})
    assert response.status_code == 403
```

- [ ] **Step 2: Chạy test, xác nhận FAIL (`404 Not Found` — route chưa tồn tại)**

```
python -m pytest tests/test_5410_chia_se_api.py -q
```

- [ ] **Step 3: Viết `routes/chia_se.py`**

```python
"""
chia_se.py - be mat HTTP cho chia se bang ma (spec S6.6).

Muc dinh gia tri admin luon doc tu CSDL qua is_operator(request), khong bao
gio tin bat cu truong nao trong body - giong het luat da ap dung cho
publish/deprecate cua library.py (routes/library.py).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _user, get_db, is_operator, require_login, router)


def _share_error(exc: Exception) -> HTTPException:
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    if isinstance(exc, ssvc.ShareNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ssvc.ShareError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/api/share", status_code=201)
async def create_share(request: Request,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.sinh_ma(
            db, owner_id=user.id,
            target_kind=str(body.get("target_kind") or ""),
            target_id=str(body.get("target_id") or ""),
            max_uses=body.get("max_uses"),
            expires_in_days=body.get("expires_in_days"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"code": row.code, "expires_at": row.expires_at.isoformat()
           if row.expires_at else None}


@router.delete("/api/share/{code}")
async def revoke_share(request: Request, code: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    _csrf(request); user = _user(request)
    try:
        ssvc.thu_hoi(db, code=code, owner_id=user.id,
                    is_admin=is_operator(request))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"revoked": True}


@router.get("/api/share/{code}")
def preview_share(code: str, db: Session = Depends(get_db),
                  _identity: str = Depends(require_login)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    try:
        return ssvc.xem_truoc(db, code=code)
    except Exception as exc:
        raise _share_error(exc) from exc


@router.post("/api/share/{code}/nhan", status_code=201)
async def receive_share(request: Request, code: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = ssvc.nhan(db, code=code, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"id": row.id, "name": getattr(row, "name", getattr(row, "title", ""))}


@router.post("/api/library/{kind}/{item_id}/share-level")
async def set_share_level(request: Request, kind: str, item_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    """Dat muc chia se cho MOT muc thu vien. Dung kind cua library.py (meta/
    snippet/style) - anh xa sang target_kind day du cua chia_se.py."""
    from apps.prompt_ai_ommi.services import chia_se as ssvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    target_kind = {"meta": "meta_prompt", "snippet": "snippet",
                  "style": "style"}.get(kind, kind)
    level = str(body.get("level") or "")
    is_admin = is_operator(request)
    if level == "catalog" and not is_admin:
        raise HTTPException(status_code=403,
                            detail=_t('Chỉ admin được đặt mức "catalog".'))
    try:
        row = ssvc.dat_muc_chia_se(db, target_kind=target_kind, item_id=item_id,
                                   owner_id=user.id, is_admin=is_admin,
                                   level=level)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _share_error(exc) from exc
    return {"id": row.id, "share_level": row.share_level}
```

⚠️ Endpoint `POST /api/library/{kind}/{item_id}/share-level` không nằm trong danh
sách §6.6 của spec theo tên, nhưng §4.2 yêu cầu "share_level='catalog' CHỈ admin đặt
được" mà không cho một đường HTTP nào set nó — nếu không có endpoint này, cột tồn
tại nhưng không ai gọi được `dat_muc_chia_se`. Đây là quyết định bổ khuyết, ghi
trong báo cáo cuối plan là điểm cần chủ dự án xác nhận.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5410_chia_se_api.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/routes/chia_se.py tests/test_5410_chia_se_api.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): endpoint chia se bang ma (S6.6)

POST/DELETE/GET /api/share(/{code}) + POST .../nhan. Them
POST /api/library/{kind}/{item_id}/share-level de co duong dat muc chia se -
S4.2 yeu cau "catalog chi admin dat" nhung khong khai endpoint nao lam viec do.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Đăng ký router `chia_se` (Làn M)

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/__init__.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.routes.chia_se` (module, đã tồn tại từ Task 8).
- Produces: các route của `chia_se.py` hoạt động trong app thật (không chỉ trong
  test import trực tiếp module).

- [ ] **Step 1: Thêm import**

```python
from apps.prompt_ai_ommi.routes import (  # noqa: F401  (import de dang ky route)
    pages, projects, handoff, assets_catalog, resources, library, storyboard,
    overview, chia_se)
```
và thêm dòng mô tả vào docstring đầu tệp:
```
    chia_se.py        Chia se bang ma + dat muc chia se (Pha 4).
```

- [ ] **Step 2: Chạy lại toàn bộ test của Task 8 qua app thật (không chỉ import
  module) để xác nhận đăng ký đúng**

```
python -m pytest tests/test_5410_chia_se_api.py -q
```
Kỳ vọng: vẫn PASS (test này đã dùng `create_app()` thật nên nếu Task 8 làm test
PASS rồi thì bước này là xác nhận lại, không phải lần đầu chạy được).

- [ ] **Step 3: Commit**

```bash
git add apps/prompt_ai_ommi/routes/__init__.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): dang ky router chia_se

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: `tables/thu_vien.py` — cột Pha 4 + 4 lớp mới (Làn G)

**Files:**
- Modify: `apps/prompt_ai_ommi/tables/thu_vien.py` (thêm cột vào
  `OmmiMetaPrompt`/`OmmiPromptSnippet`/`OmmiStyle`, thêm 4 lớp mới)
- Modify: `apps/prompt_ai_ommi/tables/__init__.py` (re-export 4 lớp mới)
- Test: `tests/test_5420_thu_vien_pha4_model.py`

**Interfaces:**
- Consumes: cột/bảng từ Task 3 (migration).
- Produces: `OmmiMetaPrompt.target_format/.is_default/.placeholders`,
  `OmmiMetaPrompt.share_level`, `OmmiPromptSnippet.share_level`,
  `OmmiStyle.parent_id/.provider_overrides/.share_level`,
  `apps.prompt_ai_ommi.tables.{OmmiImageTemplate,OmmiStoryboardFramework,
  OmmiSample,OmmiProfile}` — dùng bởi Task 11–13 (`nhap_mau_goc.py`) và Task 6/7
  (`chia_se.py.TARGET_KINDS`, mở rộng ở Task 12).

- [ ] **Step 1: Viết test đỏ cho cột mới trên 3 lớp cũ + 4 lớp mới**

```python
# tests/test_5420_thu_vien_pha4_model.py
"""Cot Pha 4 tren thu vien cu + 4 bang moi (image_template, storyboard_framework,
sample, profile)."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tv4.db').as_posix()}")
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


def test_meta_prompt_has_pha4_columns(db):
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id="u1", name="X", body="Y")
    db.add(row); db.commit()
    assert row.target_format == "gemini_style"
    assert row.is_default is False
    assert row.placeholders == []
    assert row.share_level == "private"


def test_style_has_pha4_columns(db):
    from apps.prompt_ai_ommi.tables import OmmiStyle
    row = OmmiStyle(owner_id="u1", name="X")
    db.add(row); db.commit()
    assert row.parent_id is None
    assert row.provider_overrides == {}
    assert row.share_level == "private"


def test_snippet_has_share_level(db):
    from apps.prompt_ai_ommi.tables import OmmiPromptSnippet
    row = OmmiPromptSnippet(owner_id="u1", name="X")
    db.add(row); db.commit()
    assert row.share_level == "private"


def test_image_template_defaults(db):
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    row = OmmiImageTemplate(owner_id="u1", name="Mau", prompt_text="{SUBJECT}",
                            asset_type="character")
    db.add(row); db.commit()
    assert row.aspect == "1:1"
    assert row.output_mode == "grid"
    assert row.is_builtin is False
    assert row.share_level == "private"


def test_storyboard_framework_defaults(db):
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    row = OmmiStoryboardFramework(owner_id="u1", name="Khung")
    db.add(row); db.commit()
    assert row.default_aspect == "16:9"
    assert row.default_n_scenes == 3


def test_sample_and_profile_exist(db):
    from apps.prompt_ai_ommi.tables import OmmiSample, OmmiProfile
    sample = OmmiSample(owner_id="u1", title="Mau ket qua")
    profile = OmmiProfile(owner_id="u1", name="Ho so")
    db.add_all([sample, profile]); db.commit()
    assert sample.actual_credit == 0
    assert profile.asset_tag_filter == []
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```
python -m pytest tests/test_5420_thu_vien_pha4_model.py -q
```

- [ ] **Step 3: Sửa `OmmiMetaPrompt` — thêm 4 thuộc tính (trước dòng
  `created_at`)**

```python
    target_format: Mapped[str] = mapped_column(
        String(24), default="gemini_style", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False,
                                             nullable=False)
    placeholders: Mapped[list] = mapped_column(JSON, default=list,
                                               nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
```

- [ ] **Step 4: Sửa `OmmiPromptSnippet` — thêm `share_level`**

```python
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
```

- [ ] **Step 5: Sửa `OmmiStyle` — thêm `parent_id`/`provider_overrides`/
  `share_level`**

```python
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider_overrides: Mapped[dict] = mapped_column(JSON, default=dict,
                                                      nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
```

- [ ] **Step 6: Thêm 4 lớp mới vào cuối `tables/thu_vien.py`**

```python
class OmmiImageTemplate(Base):
    """Mau composite anh (character/prop/background). Ban that cua PROMPT AI
    la 21 mau nhap tu Prompt Seedance Studio (xem services/nhap_mau_goc.py)."""

    __tablename__ = "ommi_image_template"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    n_outputs: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    aspect: Mapped[str] = mapped_column(String(8), default="1:1", nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    asset_subtype: Mapped[str] = mapped_column(String(32), default="",
                                               nullable=False)
    grid_layout: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    output_mode: Mapped[str] = mapped_column(String(16), default="grid",
                                             nullable=False)
    requires_ref: Mapped[bool] = mapped_column(Boolean, default=False,
                                               nullable=False)
    multi_ref_max: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bg_style: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    negative_lock: Mapped[str] = mapped_column(Text, default="", nullable=False)
    placeholder_hint: Mapped[str] = mapped_column(String(200), default="",
                                                   nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False,
                                             nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiStoryboardFramework(Base):
    """Khung storyboard (composite header/rules/footer + prompt chia canh).
    5 khung that nhap tu Prompt Seedance Studio."""

    __tablename__ = "ommi_storyboard_framework"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    composite_header: Mapped[str] = mapped_column(Text, default="", nullable=False)
    composite_rules: Mapped[str] = mapped_column(Text, default="", nullable=False)
    composite_negative_footer: Mapped[str] = mapped_column(Text, default="",
                                                            nullable=False)
    breakdown_llm_prompt: Mapped[str] = mapped_column(Text, default="",
                                                       nullable=False)
    default_style_id: Mapped[str | None] = mapped_column(String(36),
                                                          nullable=True)
    default_aspect: Mapped[str] = mapped_column(String(8), default="16:9",
                                                nullable=False)
    default_n_scenes: Mapped[int] = mapped_column(Integer, default=3,
                                                   nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False,
                                             nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiSample(Base):
    """Ket qua da tao (snapshot), dung de khoe/tham khao. Bat bien - khong co
    archived_at/updated_at vi khong ai sua mot sample sau khi tao."""

    __tablename__ = "ommi_sample"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    final_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_reasons: Mapped[list] = mapped_column(JSON, default=list,
                                                  nullable=False)
    used_model: Mapped[str] = mapped_column(String(64), default="",
                                            nullable=False)
    actual_credit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    iter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiProfile(Base):
    """Ho so cau hinh nhanh (style + meta_prompt + bo loc asset thuong dung)."""

    __tablename__ = "ommi_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    asset_tag_filter: Mapped[list] = mapped_column(JSON, default=list,
                                                    nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private",
                                             nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

- [ ] **Step 7: Re-export 4 lớp mới trong `tables/__init__.py`**

```python
from apps.prompt_ai_ommi.tables.thu_vien import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiPromptVersion, OmmiStyle,
    OmmiImageTemplate, OmmiStoryboardFramework, OmmiSample, OmmiProfile)
```
và thêm 4 tên vào `__all__`.

- [ ] **Step 8: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5420_thu_vien_pha4_model.py -q
```

- [ ] **Step 9: Mở rộng `TARGET_KINDS` của `services/chia_se.py` (Task 6/7) với 4
  loại mới — sửa nhỏ, KHÔNG phải việc của Làn G (tệp thuộc Làn F); ghi yêu cầu này
  và để Làn F thực hiện ở Task 14 khi cả hai đã sẵn sàng. Bỏ qua bước này ở Task 10.**

- [ ] **Step 10: Commit**

```bash
git add apps/prompt_ai_ommi/tables/thu_vien.py apps/prompt_ai_ommi/tables/__init__.py tests/test_5420_thu_vien_pha4_model.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): cot Pha 4 + 4 bang moi trong thu_vien.py

target_format/is_default/placeholders/share_level tren OmmiMetaPrompt;
parent_id/provider_overrides/share_level tren OmmiStyle; share_level tren
OmmiPromptSnippet; 4 bang moi: OmmiImageTemplate, OmmiStoryboardFramework,
OmmiSample, OmmiProfile.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Script xuất dữ liệu từ bản sao Studio (Làn G)

⛔ KHÔNG mở `D:\BOT GEMINI\app\modules\seedance\data\app.db` tại chỗ. Toàn bộ Task
này thao tác trên **bản sao** trong scratchpad phiên đang thi hành.

**Files:**
- Create: `<scratchpad>/xuat_mau_goc.py` (script vận hành một lần — KHÔNG vào repo)
- Create (kết quả chạy script): `apps/prompt_ai_ommi/prompts/mau_goc/__init__.py`
  (rỗng), `meta_prompts.json`, `image_templates.json`, `snippets.json`,
  `storyboard_frameworks.json`

**Interfaces:**
- Consumes: không có (đọc trực tiếp SQLite bản sao).
- Produces: 4 tệp JSON — dùng bởi Task 12 (`nhap_mau_goc.py`).

- [ ] **Step 1: Copy CSDL nguồn sang scratchpad (không đụng bản gốc)**

```
mkdir -p "<scratchpad>/botgemini_ro"
cp "/d/BOT GEMINI/app/modules/seedance/data/app.db" "<scratchpad>/botgemini_ro/app.db"
cp "/d/BOT GEMINI/app/modules/seedance/data/app.db-wal" "<scratchpad>/botgemini_ro/app.db-wal"
cp "/d/BOT GEMINI/app/modules/seedance/data/app.db-shm" "<scratchpad>/botgemini_ro/app.db-shm"
```

- [ ] **Step 2: Viết `<scratchpad>/xuat_mau_goc.py`**

```python
"""xuat_mau_goc.py - xuat 12 meta prompt + 21 image template that + 13 snippet
that + 5 storyboard framework tu BAN SAO (chi doc) cua Prompt Seedance Studio
thanh 4 tep JSON dong goi cung PROMPT AI.

CHAY MOT LAN, THU CONG boi nguoi thi hanh plan - day KHONG phai ma san pham,
khong duoc dua vao repo. Doc app.db da COPY sang scratchpad
(mode=ro) - khong bao gio mo file trong D:\\BOT GEMINI truc tiep (G-14).

Bo loc: prompt_snippets co ten LIKE 'snippet-%' va image_gen_templates co
is_builtin=0 la BAN TU SINH (khong phai noi dung nghiep vu that) - KHONG xuat.
"""
from __future__ import annotations

import json
import sqlite3
import sys

DB_PATH = sys.argv[1]
OUT_DIR = sys.argv[2]


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def xuat_meta_prompts(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT name, content, target_format, is_default, placeholders "
        "FROM meta_prompts ORDER BY target_format, name").fetchall()
    out = []
    for name, content, target_format, is_default, placeholders_json in rows:
        out.append({
            "name": name.strip(),
            "body": content,
            "target_format": target_format,
            "is_default": bool(is_default),
            "placeholders": json.loads(placeholders_json or "[]"),
        })
    return out


def xuat_snippets(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT name, content, category FROM prompt_snippets "
        "WHERE name NOT LIKE 'snippet-%' ORDER BY name").fetchall()
    return [{"name": n, "body": c, "category": cat or ""} for n, c, cat in rows]


def xuat_image_templates(conn: sqlite3.Connection) -> list[dict]:
    cols = ["name", "icon", "description", "prompt_text", "n_outputs", "aspect",
           "asset_type", "asset_subtype", "grid_layout", "output_mode",
           "requires_ref", "multi_ref_max", "bg_style", "negative_lock",
           "placeholder_hint"]
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM image_gen_templates "
        "WHERE is_builtin = 1 ORDER BY asset_type, name").fetchall()
    out = []
    for row in rows:
        item = dict(zip(cols, row))
        item["requires_ref"] = bool(item["requires_ref"])
        item["n_outputs"] = int(item["n_outputs"])
        item["multi_ref_max"] = int(item["multi_ref_max"])
        out.append(item)
    return out


def xuat_storyboard_frameworks(conn: sqlite3.Connection) -> list[dict]:
    cols = ["name", "icon", "description", "composite_header", "composite_rules",
           "composite_negative_footer", "breakdown_llm_prompt", "default_aspect",
           "default_n_scenes"]
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM storyboard_frameworks "
        "WHERE is_builtin = 1 ORDER BY name").fetchall()
    return [dict(zip(cols, row)) for row in rows]


def main() -> None:
    conn = _conn()
    try:
        meta = xuat_meta_prompts(conn)
        snip = xuat_snippets(conn)
        tmpl = xuat_image_templates(conn)
        frame = xuat_storyboard_frameworks(conn)
    finally:
        conn.close()

    assert len(meta) == 12, f"ky vong 12 meta prompt, duoc {len(meta)}"
    assert len(snip) == 13, f"ky vong 13 snippet that, duoc {len(snip)}"
    assert len(tmpl) == 21, f"ky vong 21 image template that, duoc {len(tmpl)}"
    assert len(frame) == 5, f"ky vong 5 storyboard framework, duoc {len(frame)}"

    for filename, items in (
            ("meta_prompts.json", meta), ("snippets.json", snip),
            ("image_templates.json", tmpl),
            ("storyboard_frameworks.json", frame)):
        path = f"{OUT_DIR}/{filename}"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=False, indent=2)
        print(f"da ghi {path} ({len(items)} muc)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Chạy script, ghi thẳng vào thư mục đích trong repo**

```
mkdir -p apps/prompt_ai_ommi/prompts/mau_goc
python "<scratchpad>/xuat_mau_goc.py" "<scratchpad>/botgemini_ro/app.db" "apps/prompt_ai_ommi/prompts/mau_goc"
```
Kỳ vọng in ra 4 dòng `da ghi ... (N muc)` với N lần lượt 12/13/21/5. Nếu một `assert`
ném lỗi — nghĩa là dữ liệu nguồn đã đổi kể từ 26/09/2026 (khi plan này được viết và
xác nhận số liệu qua bản sao thật) — dừng lại, đối chiếu lại với
`docs/PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md` §8.1/§8.3 trước khi tiếp tục.

⚠️ Số liệu đã đo trực tiếp trên bản sao lúc viết plan này (26/09/2026):
`image_gen_templates` thật chia đều **7 character / 7 prop / 7 background** (is_builtin=1,
tổng 21) — KHÁC với con số "character 7 · prop 8 · background 9" ghi trong
`DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md` §8.3. Tổng 21 và số snippet/meta khớp đúng; chỉ
riêng cách chia theo `asset_type` của báo cáo đối chiếu là sai. Dùng số đo trực tiếp
(7/7/7) làm chuẩn — báo lại chủ dự án để sửa §8.3.

- [ ] **Step 4: Tạo `apps/prompt_ai_ommi/prompts/mau_goc/__init__.py` rỗng**

```python
"""mau_goc/ - du lieu tinh xuat tu Prompt Seedance Studio (chi doc, dong goi
cung code). Xem services/nhap_mau_goc.py de nhap vao catalog."""
```

- [ ] **Step 5: Kiểm bằng mắt một mục của mỗi tệp JSON (không phải chạy lệnh — mở
  và đọc), xác nhận không còn ký tự thay thế (mojibake) sau khi ghi UTF-8**

Mở `apps/prompt_ai_ommi/prompts/mau_goc/meta_prompts.json`, tìm mục tên
`"Anh Thang"`; xác nhận `body` chứa đúng `{TITLE}`, `{BRIEF_VI}`… không bị hỏng dấu.

- [ ] **Step 6: Commit (4 tệp JSON — dữ liệu, không phải mã)**

```bash
git add apps/prompt_ai_ommi/prompts/mau_goc/
git commit -m "$(cat <<'EOF'
data(prompt-ai-ommi): xuat 12 meta prompt + 21 template + 13 snippet + 5 khung tu Studio

Xuat tu ban SAO (khong dung) cua D:\BOT GEMINI qua script scratchpad, loc bo
9 image_gen_templates va 8 prompt_snippets tu sinh (ten "snippet-*"). So lieu
da xac nhan truc tiep: 12/21/13/5 dung nhu chu du an yeu cau 26/09.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: `services/nhap_mau_goc.py` — nhập idempotent

**Files:**
- Create: `apps/prompt_ai_ommi/services/nhap_mau_goc.py`
- Test: `tests/test_5425_nhap_mau_goc_service.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.tables.{OmmiMetaPrompt,OmmiPromptSnippet,
  OmmiImageTemplate,OmmiStoryboardFramework}`; 4 tệp JSON từ Task 11.
- Produces: `nhap(db, *, admin_owner_id) -> dict` — dùng bởi Task 14 (route admin).

- [ ] **Step 1: Viết test đỏ — nhập lần đầu tạo đủ số lượng, nhập lần hai không
  trùng**

```python
# tests/test_5425_nhap_mau_goc_service.py
"""nhap_mau_goc.nhap() - phai idempotent (R-3)."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nmg.db').as_posix()}")
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


def test_first_import_inserts_everything(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import (
        OmmiMetaPrompt, OmmiPromptSnippet, OmmiImageTemplate,
        OmmiStoryboardFramework)
    summary = nhap_mau_goc_result = nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    assert summary["meta_prompt"] == {"them": 12, "bo_qua": 0}
    assert summary["snippet"] == {"them": 13, "bo_qua": 0}
    assert summary["image_template"] == {"them": 21, "bo_qua": 0}
    assert summary["storyboard_framework"] == {"them": 5, "bo_qua": 0}

    assert db.query(OmmiMetaPrompt).count() == 12
    assert db.query(OmmiPromptSnippet).count() == 13
    assert db.query(OmmiImageTemplate).count() == 21
    assert db.query(OmmiStoryboardFramework).count() == 5


def test_second_import_is_a_no_op(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    summary = nsvc.nhap(db, admin_owner_id="admin-2")
    db.commit()
    assert summary["meta_prompt"] == {"them": 0, "bo_qua": 12}
    assert summary["image_template"] == {"them": 0, "bo_qua": 21}
    assert db.query(OmmiMetaPrompt).count() == 12


def test_imported_meta_prompts_are_catalog_owned_by_no_one(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    anh_thang = db.query(OmmiMetaPrompt).filter_by(name="Anh Thang").one()
    assert anh_thang.owner_id is None
    assert anh_thang.is_catalog is True
    assert anh_thang.share_level == "catalog"
    assert anh_thang.is_default is True
    assert anh_thang.target_format == "gemini_style"


def test_imported_image_templates_are_owned_by_the_importing_admin(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    row = db.query(OmmiImageTemplate).filter_by(
        name="\U0001f464 Nhân vật — Chỉ nhân vật (8 góc)").one()
    assert row.owner_id == "admin-1"
    assert row.is_builtin is True
    assert row.share_level == "catalog"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```
python -m pytest tests/test_5425_nhap_mau_goc_service.py -q
```

- [ ] **Step 3: Viết `services/nhap_mau_goc.py`**

```python
"""
nhap_mau_goc.py - nhap 12 meta prompt + 21 image template + 13 snippet + 5
storyboard framework tu Prompt Seedance Studio vao catalog PROMPT AI.

Nguon la 4 tep JSON tinh dong goi cung code (prompts/mau_goc/*.json) - khong
doc CSDL/dia cua BOT GEMINI luc chay (tach hoan toan khoi kho CHI DOC do,
xem Task 11 - xuat_mau_goc.py chay MOT LAN thu cong, ket qua la du lieu tinh).

Idempotent (R-3), theo khoa rieng cho tung loai:
  - meta_prompt: (owner_id IS NULL, target_format, name) - dung dung khoa
    R-3 ghi trong spec.
  - snippet: (owner_id IS NULL, name) - snippet khong co target_format nen
    khong ap dung duoc khoa nguyen van cua R-3; dung ten thay the (ten la
    duy nhat trong 13 muc that).
  - image_template / storyboard_framework: (is_builtin=True, name) - KHONG
    dua owner_id vao khoa, vi hai admin khac nhau goi lai khong duoc tao hai
    ban ghi khac nhau cho CUNG mot mau he thong.
"""
from __future__ import annotations

import json
from importlib.resources import files

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiImageTemplate,
    OmmiStoryboardFramework)

_PACKAGE = "apps.prompt_ai_ommi.prompts.mau_goc"


def _load(filename: str) -> list[dict]:
    raw = files(_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
    payload = json.loads(raw)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError(f"{filename}: khong doc duoc danh sach 'items'.")
    return items


def _nhap_meta_prompts(db: Session) -> dict:
    them = bo_qua = 0
    for item in _load("meta_prompts.json"):
        target_format = str(item["target_format"])
        name = str(item["name"])
        exists = db.execute(select(OmmiMetaPrompt.id).where(
            OmmiMetaPrompt.owner_id.is_(None),
            OmmiMetaPrompt.target_format == target_format,
            OmmiMetaPrompt.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiMetaPrompt(
            owner_id=None, name=name, body=str(item["body"]),
            target_format=target_format,
            is_default=bool(item.get("is_default", False)),
            placeholders=list(item.get("placeholders") or []),
            is_catalog=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_snippets(db: Session) -> dict:
    them = bo_qua = 0
    for item in _load("snippets.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiPromptSnippet.id).where(
            OmmiPromptSnippet.owner_id.is_(None),
            OmmiPromptSnippet.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiPromptSnippet(
            owner_id=None, name=name, body=str(item["body"]),
            category=str(item.get("category") or ""),
            is_catalog=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_image_templates(db: Session, admin_owner_id: str) -> dict:
    them = bo_qua = 0
    for item in _load("image_templates.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiImageTemplate.id).where(
            OmmiImageTemplate.is_builtin.is_(True),
            OmmiImageTemplate.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiImageTemplate(
            owner_id=admin_owner_id, name=name,
            icon=str(item.get("icon") or ""),
            description=str(item.get("description") or ""),
            prompt_text=str(item["prompt_text"]),
            n_outputs=int(item.get("n_outputs") or 1),
            aspect=str(item.get("aspect") or "1:1"),
            asset_type=str(item["asset_type"]),
            asset_subtype=str(item.get("asset_subtype") or ""),
            grid_layout=str(item.get("grid_layout") or ""),
            output_mode=str(item.get("output_mode") or "grid"),
            requires_ref=bool(item.get("requires_ref", False)),
            multi_ref_max=int(item.get("multi_ref_max") or 1),
            bg_style=str(item.get("bg_style") or ""),
            negative_lock=str(item.get("negative_lock") or ""),
            placeholder_hint=str(item.get("placeholder_hint") or ""),
            is_builtin=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_storyboard_frameworks(db: Session, admin_owner_id: str) -> dict:
    them = bo_qua = 0
    for item in _load("storyboard_frameworks.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiStoryboardFramework.id).where(
            OmmiStoryboardFramework.is_builtin.is_(True),
            OmmiStoryboardFramework.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiStoryboardFramework(
            owner_id=admin_owner_id, name=name,
            icon=str(item.get("icon") or ""),
            description=str(item.get("description") or ""),
            composite_header=str(item.get("composite_header") or ""),
            composite_rules=str(item.get("composite_rules") or ""),
            composite_negative_footer=str(
                item.get("composite_negative_footer") or ""),
            breakdown_llm_prompt=str(item.get("breakdown_llm_prompt") or ""),
            default_aspect=str(item.get("default_aspect") or "16:9"),
            default_n_scenes=int(item.get("default_n_scenes") or 3),
            is_builtin=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def nhap(db: Session, *, admin_owner_id: str) -> dict:
    """Nhap ca 4 loai mot luot. Idempotent - goi lai chi bao cao them=0."""
    ket_qua = {
        "meta_prompt": _nhap_meta_prompts(db),
        "snippet": _nhap_snippets(db),
        "image_template": _nhap_image_templates(db, admin_owner_id),
        "storyboard_framework": _nhap_storyboard_frameworks(db, admin_owner_id),
    }
    db.flush()
    return ket_qua
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5425_nhap_mau_goc_service.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/nhap_mau_goc.py tests/test_5425_nhap_mau_goc_service.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): nhap_mau_goc.nhap() - idempotent theo tung loai

meta_prompt/snippet khoa theo (owner_id IS NULL, ten); image_template/
storyboard_framework khoa theo (is_builtin=True, ten) de khong tao trung khi
mot admin KHAC goi lai (R-3).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: T-2 — kiểm placeholder toàn tập (12 meta + 21 template)

**Files:**
- Test: `tests/test_5440_kiem_placeholder_toan_tap.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.services.placeholders.kiem_placeholder(body: str,
  khai_bao: list[str], co_gia_tri: dict) -> list[str]` (Pha 3, đã xác nhận tồn tại
  ở Task 1 Step 4); `nhap_mau_goc.nhap()` (Task 12).

⚠️ **Quyết định thiết kế cần chủ dự án xác nhận** (ghi trong báo cáo cuối plan):
bảng quy đổi placeholder ở spec §7 chỉ định nghĩa nguồn giá trị cho 15 tên dùng
trong **meta prompt** (`TITLE`, `BRIEF_VI`, …) + 4 tên tự do của "Ông Ngoại". Nó
**không** định nghĩa nguồn giá trị cho các placeholder thật sự xuất hiện trong 21
**image template** (`SUBJECT`, `STYLE`, `EXTRA`, `EQUIPMENT` — xác nhận trực tiếp
trên dữ liệu thật, không phải suy đoán). Những placeholder này là ô người dùng gõ
tay lúc sinh ảnh (Pha 5, `services/composite.py`), không phải giá trị hệ thống suy
ra từ brief/style. Vì `ommi_image_template` (spec §4.2) không có cột `placeholders`
lưu sẵn, T-2 cho nhóm này được thiết kế lại thành: tự suy `khai_bao` từ chính
`prompt_text` (regex `\{[A-Z][A-Z0-9_]*\}`), rồi cấp `co_gia_tri` tổng hợp cho đúng
các tên đó — bài kiểm xác nhận **cú pháp placeholder trong 21 template nhập vào là
hợp lệ và tự khai đủ**, KHÔNG xác nhận nguồn giá trị nghiệp vụ (việc đó thuộc Pha
5). Với 12 meta prompt, `khai_bao` lấy từ cột `placeholders` thật đã nhập, và
`co_gia_tri` dùng đúng 19 tên của §7 (15 + 4 tự do).

- [ ] **Step 1: Viết test (không cần bước RED riêng — đây là bài kiểm xác nhận dữ
  liệu đã nhập ở Task 12, tự nhiên RED cho tới khi Task 12 chạy trong cùng fixture)**

```python
# tests/test_5440_kiem_placeholder_toan_tap.py
"""T-2 (spec S10.2): kiem_placeholder tren CA 12 meta prompt va CA 21 image
template da nhap - khong phai mau dai dien."""
from __future__ import annotations

import re

import pytest

#: 15 ten cua bang quy doi S7 + 4 ten tu do cua "Ong Ngoai".
_TEN_HE_THONG = {
    "TITLE", "PROJECT_NAME", "BRIEF_VI", "DURATION", "SCENES", "ASPECT_RATIO",
    "ASPECT", "STYLE_FULL", "STYLE_POSITIVE", "STYLE_NEGATIVE", "ASSET_LIST",
    "VIDEO_LIST", "PROMPT", "REF_NOTE", "CHARACTER_DESCRIPTION",
    "FACTION_A", "FACTION_B", "MIN_COMBAT_DISTANCE", "NEUTRAL_LIST",
}
_TOKEN_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'kp.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    nsvc.nhap(session, admin_owner_id="admin-t2")
    session.commit()
    yield session
    session.close()
    dbmod.reset_engine()


def test_all_12_meta_prompts_declare_every_placeholder_they_use(db):
    from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    rows = db.query(OmmiMetaPrompt).filter(
        OmmiMetaPrompt.owner_id.is_(None)).all()
    assert len(rows) == 12, "T-2 doi hoi CA 12 meta, khong phai mau dai dien"
    co_gia_tri = {ten: f"<gia tri thu {ten}>" for ten in _TEN_HE_THONG}
    for row in rows:
        missing = kiem_placeholder(row.body, list(row.placeholders), co_gia_tri)
        assert missing == [], f"{row.name!r} ({row.target_format}): thieu {missing}"


def test_all_21_image_templates_have_well_formed_placeholders(db):
    from apps.prompt_ai_ommi.services.placeholders import kiem_placeholder
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    rows = db.query(OmmiImageTemplate).filter(
        OmmiImageTemplate.is_builtin.is_(True)).all()
    assert len(rows) == 21, "T-2 doi hoi CA 21 template, khong phai mau dai dien"
    for row in rows:
        khai_bao = sorted(set(_TOKEN_RE.findall(row.prompt_text)))
        co_gia_tri = {ten: f"<{ten.lower()}>" for ten in khai_bao}
        missing = kiem_placeholder(row.prompt_text, khai_bao, co_gia_tri)
        assert missing == [], f"{row.name!r}: thieu {missing}"
```

- [ ] **Step 2: Chạy test, xác nhận PASS ngay (đây là bài kiểm xác nhận, dữ liệu đã
  đúng từ Task 11/12 — nếu FAIL, nghĩa là dữ liệu xuất ở Task 11 có placeholder
  không khớp quy ước CHỮ HOA, hoặc `placeholders` JSON nhập thiếu tên; sửa lại
  Task 11's script hoặc dữ liệu nguồn, không sửa test)**

```
python -m pytest tests/test_5440_kiem_placeholder_toan_tap.py -q
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_5440_kiem_placeholder_toan_tap.py
git commit -m "$(cat <<'EOF'
test(prompt-ai-ommi): T-2 - kiem_placeholder tren CA 12 meta + CA 21 template

Meta prompt dung dung 19 ten cua bang quy doi S7. Image template khong co cot
placeholders (S4.2 khong khai) nen tu suy khai_bao tu prompt_text - xac nhan
cu phap hop le, nguon gia tri nghiep vu (SUBJECT/STYLE/EXTRA/EQUIPMENT) thuoc
Pha 5 (composite.py), khong phai Pha 4.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Route admin nhập mẫu gốc + mở rộng `TARGET_KINDS` (Làn F, sau khi Task 12 xong)

**Files:**
- Modify: `apps/prompt_ai_ommi/routes/chia_se.py` (thêm route admin)
- Modify: `apps/prompt_ai_ommi/services/chia_se.py` (mở rộng `TARGET_KINDS` với 4
  loại của Task 10)
- Test: `tests/test_5415_nhap_mau_goc_api.py`

**Interfaces:**
- Consumes: `nhap_mau_goc.nhap()` (Task 12); `OmmiImageTemplate`,
  `OmmiStoryboardFramework`, `OmmiSample`, `OmmiProfile` (Task 10).
- Produces: `POST /prompt-ai-ommi/api/admin/nhap-mau-goc` — admin only, idempotent
  ở tầng HTTP.

- [ ] **Step 1: Viết test đỏ**

```python
# tests/test_5415_nhap_mau_goc_api.py
"""POST /api/admin/nhap-mau-goc - chi admin, idempotent o tang HTTP."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nmg-api.db').as_posix()}")
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
    tao_nguoi_dung(db, email="admin@example.com", password="Strong-pass-123",
                   is_verified=True, role="admin")
    tao_nguoi_dung(db, email="user@example.com", password="Strong-pass-123",
                   is_verified=True, role="user")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-nhap-mau-goc-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    admin, admin_token = login("admin@example.com")
    user, user_token = login("user@example.com")
    yield admin, admin_token, user, user_token
    admin.close(); user.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_normal_user_cannot_import(api):
    _admin, _at, user, user_token = api
    response = user.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                         headers={"X-CSRF-Token": user_token}, json={})
    assert response.status_code == 403


def test_admin_import_is_idempotent(api):
    admin, admin_token, *_ = api
    first = admin.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                       headers={"X-CSRF-Token": admin_token}, json={})
    assert first.status_code == 200, first.text
    assert first.json()["meta_prompt"]["them"] == 12

    second = admin.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                       headers={"X-CSRF-Token": admin_token}, json={})
    assert second.status_code == 200
    assert second.json()["meta_prompt"] == {"them": 0, "bo_qua": 12}

    catalog = admin.get("/prompt-ai-ommi/api/library/meta?catalog=true&limit=100")
    names = [item["name"] for item in catalog.json()["items"]]
    assert names.count("Anh Thang") == 1
```

- [ ] **Step 2: Chạy test, xác nhận FAIL (`404 Not Found`)**

```
python -m pytest tests/test_5415_nhap_mau_goc_api.py -q
```

- [ ] **Step 3: Thêm vào cuối `services/chia_se.py` — mở rộng `TARGET_KINDS`**

```python
def _mo_rong_target_kinds() -> None:
    """Goi sau khi tables/thu_vien.py co 4 lop Pha 4 (Task 10) - tach rieng
    khoi khai bao dict o dau tep de import-time khong phu thuoc thu tu module
    nap giua thu_vien.py va nhan_vat.py."""
    from apps.prompt_ai_ommi.tables import (
        OmmiImageTemplate, OmmiStoryboardFramework, OmmiSample, OmmiProfile)
    TARGET_KINDS.update({
        "image_template": OmmiImageTemplate,
        "storyboard_framework": OmmiStoryboardFramework,
        "sample": OmmiSample,
        "profile": OmmiProfile,
    })


_mo_rong_target_kinds()
```

⚠️ Đặt lời gọi `_mo_rong_target_kinds()` ngay dưới định nghĩa `TARGET_KINDS` gốc (đầu
tệp), KHÔNG ở cuối tệp — Python thực thi module theo thứ tự dòng, để ở cuối vẫn chạy
đúng vì đây là top-level code, nhưng đặt gần định nghĩa gốc giúp người đọc thấy ngay
`TARGET_KINDS` có 10 mục chứ không phải 6. Sửa vị trí thật khi áp dụng.

- [ ] **Step 4: Thêm route vào `routes/chia_se.py`**

```python
@router.post("/api/admin/nhap-mau-goc")
async def nhap_mau_goc_route(request: Request,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    """Nhap 12 meta prompt + 21 image template + 13 snippet + 5 khung
    storyboard tu Prompt Seedance Studio vao catalog. Idempotent (R-3)."""
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    body = await request.json(); _csrf(request, body)
    if not is_operator(request):
        raise HTTPException(status_code=403,
                            detail=_t('Chỉ admin được nhập mẫu gốc.'))
    user = _user(request)
    try:
        summary = nsvc.nhap(db, admin_owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise exc
    return summary
```

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

```
python -m pytest tests/test_5415_nhap_mau_goc_api.py -q
```

- [ ] **Step 6: Chạy TOÀN BỘ test của Pha 4 một lượt cuối**

```
python -m pytest tests/test_540*.py tests/test_542*.py tests/test_544*.py -q
```
Kỳ vọng: tất cả PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/prompt_ai_ommi/routes/chia_se.py apps/prompt_ai_ommi/services/chia_se.py tests/test_5415_nhap_mau_goc_api.py
git commit -m "$(cat <<'EOF'
feat(prompt-ai-ommi): POST /api/admin/nhap-mau-goc + TARGET_KINDS du 10 loai

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Gộp `main` + `pre-commit`

Theo luật chết người §1 ("GỘP main: test nhắm xanh là ĐỦ. Gộp xong -> `pre-commit
run --all-files`") — ⛔ KHÔNG chạy gate trong plan này (G-13).

- [ ] **Step 1: Chạy lại toàn bộ test Pha 4 một lần nữa trên nhánh sạch**

```
python -m pytest tests/test_5405_tables_package_pha4.py tests/test_540*.py tests/test_542*.py tests/test_544*.py tests/test_5402_nhan_vat_share_level.py -q
```

- [ ] **Step 2: Gộp `main` vào nhánh làm việc**

```
git fetch origin main
git merge origin/main
```
Giải xung đột nếu có (dùng skill `resolving-merge-conflicts` nếu cần) — Pha 4 chỉ
thêm tệp mới + 3 tệp sửa nhỏ (`tables/thu_vien.py`, `tables/nhan_vat.py`,
`routes/__init__.py`), rủi ro xung đột thấp.

- [ ] **Step 3: Chạy `pre-commit`**

```
pre-commit run --all-files
```
Sửa tại chỗ nếu đỏ, chạy lại tới khi xanh.

- [ ] **Step 4: Báo cáo — KHÔNG xin duyệt (luật chết người §2)**

Ghi một dòng vào `docs/NHAT_KY.md`:
```
## <ngay thi hanh> — Pha 4 PROMPT AI gop main
- 15 task, dai test 5100/5400-5419/5420-5449 da chay xanh
- Da gop main + pre-commit xanh
- Cho DEPLOY: can hoi chu du an (luat chet nguoi #5, deploy giua plan)
```

---

## Tự soát

**1. Spec coverage:**

| Yêu cầu spec | Task phủ |
|---|---|
| §4.2 Pha 4 — 10 bảng `share_level`, alter meta_prompt/style, 6 bảng mới | Task 3 |
| §6.6 — 4 endpoint share + 1 endpoint admin nhập | Task 8, Task 14 |
| §7 — bảng quy đổi placeholder (dùng trong T-2, không viết lại `placeholders.py`
  vì thuộc Pha 3) | Task 13 |
| §8.3/§8.4 báo cáo đối chiếu — danh sách chính xác 12/21/13/5 | Task 11 (đo trực
  tiếp qua bản sao, phát hiện sai lệch nhỏ trong báo cáo — ghi chú lại) |
| §9.1 — sổ đăng ký dùng chung (`alembic/versions/`, `manifest.py`,
  `routes/__init__.py` chỉ Làn M ghi) | Task 3, 9 (M); Task 5–8 (F không đụng
  `routes/__init__.py`); Task 10 (G không đụng `chia_se.py`) |
| §9.4 — thứ tự M(pha4)→F→G | Task 1–5 (M) → Task 6–9 (F phần 1) → Task 10–13 (G)
  → Task 14 (F phần 2, phụ thuộc G) |
| §10.2 T-2 — "cả 12", "cả 21", không phải mẫu đại diện | Task 13, dùng
  `len(rows) == 12`/`== 21` như một `assert` trong chính test |
| R-3 — idempotent theo natural key | Task 12 (`them`/`bo_qua` counters) |
| Q-10 — không trang kho công khai | Không Task nào thêm route liệt kê công khai;
  `GET /api/share/{code}` yêu cầu biết mã, không liệt kê |
| Dải số test 5400–5419 (F) / 5420–5449 (G) | Task 5,6,7,8,14 dùng
  5400/5401/5403/5410/5415; Task 10,12,13 dùng 5420/5425/5440 — cả hai trong
  dải, chừa khoảng cho việc phát sinh khi thi hành thật |

**2. Placeholder scan:** Không còn "TBD"/"tương tự Task N" nào trong 15 task — mỗi
Step có code Python/bash thật. Hai điểm CỐ Ý để executor tự điền lúc thi hành (không
phải placeholder bỏ sót, mà là giá trị KHÔNG THỂ biết trước khi viết plan): (a)
`revision`/`down_revision` thật của migration (Task 1 Step 2, Task 3 Step 2 — vì
G-5 cấm hard-code); (b) đường dẫn scratchpad cụ thể của phiên thi hành (Task 11).

**3. Type consistency:** `sinh_ma`/`thu_hoi`/`xem_truoc`/`nhan`/`dat_muc_chia_se`
dùng cùng chữ ký xuyên Task 6/7/8/14. `TARGET_KINDS` được định nghĩa ở Task 6 (6
loại), rồi Task 14 gọi `_mo_rong_target_kinds()` thêm 4 loại — không tạo dict thứ
hai trùng tên. `nhap(db, *, admin_owner_id) -> dict` dùng đúng chữ ký xuyên Task 12
và Task 14. `kiem_placeholder(body, khai_bao, co_gia_tri)` dùng đúng thứ tự tham số
đã khai ở đầu bài (Interfaces: Consumes của Task 13) xuyên cả hai test trong đó.

---

## PHÁN QUYẾT bốn điểm trên (điều phối, 27/09/2026) — ⛔ làn KHÔNG hỏi lại

Cả bốn đều do **bằng chứng** hoặc do **chính spec này** quyết, ⛔ không thuộc ba loại
phải hỏi chủ dự án (đánh đổi sản phẩm · hai đường đều đúng · việc chỉ chủ dự án làm
được). Ghi ở đây để làn đọc và đi tiếp.

1. **Số liệu 21, ⛔ không phải 24.** Phép đo trực tiếp trên bản sao Studio thật thắng
   con số trong báo cáo. Dùng **7/7/7 = 21**. ⚠️ Làn phải **tự đếm lại** khi nhập và
   **báo số đếm được**, ⛔ đừng tin con số trong plan này — đó chính là cách sai số
   24 sống sót tới hôm nay.
2. **`SUBJECT`/`STYLE`/`EXTRA`/`EQUIPMENT` kiểm CÚ PHÁP, ⛔ không kiểm nguồn giá trị.**
   Đúng ý spec: đây là ô **người dùng gõ tay** lúc sinh ảnh, nên ⛔ không có "nguồn
   giá trị hệ thống" nào để đối chiếu — một phép kiểm đòi nguồn cho chúng sẽ **luôn
   đỏ** và người ta sẽ tắt nó đi. Kiểm được: tên nằm trong tập đã khai, cú pháp
   `{TEN}` đúng, ⛔ không có tên lạ. Bảng quy đổi 15 tên của §7 ⇒ **mở rộng thành 19**
   và ghi rõ nhóm nào là *giá trị hệ thống*, nhóm nào là *ô người dùng gõ*.
3. **⛔ KHÔNG viết `library.dat_mac_dinh()` trong pha 4.** Nhập catalog tự kiểm soát
   `is_default` bằng dữ liệu nguồn, và ⛔ không endpoint nào gọi hàm đó ⇒ viết nó là
   **mã không bao giờ chạy**, mua sự yên tâm bằng tín dụng giả. Ghi **nợ D-7**: khi
   khách được tự đặt mặc định cho bản clone riêng, hàm này cần một chủ **và** một
   phép kiểm cho bất biến *"chỉ một `is_default` mỗi `(owner_id, target_format)`"*.
4. **Chốt tên đường: `POST /api/library/{kind}/{item_id}/share-level`.** Theo đúng
   khuôn đường dẫn đã có trong app. ⚠️ Cột `share_level` **phải** có một đường HTTP
   đặt được, nếu không nó là **cột chết** (ghi được mà không ai ghi) — đúng lớp lỗi
   nợ D-2 (`ommi_binding.scene_id IS NULL` do không ai sinh, không ai đọc).
   ⛔ Làn phải thêm một phép kiểm rằng đường này **thật sự được đăng ký** trong
   `routes/__init__.py`, không chỉ tồn tại trong tệp.

---

## Điểm cần chủ dự án xác nhận (không phải lỗi chặn thi hành, nhưng ảnh hưởng thiết kế)

1. **§8.3 sai số liệu**: "character 7 · prop 8 · background 9" (tổng 24) không khớp
   phép đo trực tiếp trên bản sao Studio thật (26/09/2026): **7/7/7 = 21**. Tổng 21
   và 9 mẫu tự sinh vẫn đúng — chỉ cách chia theo `asset_type` trong báo cáo sai.
   Task 11 dùng số đo trực tiếp.
2. **§7 không phủ placeholder của image template**: `SUBJECT`, `STYLE`, `EXTRA`,
   `EQUIPMENT` (đo trực tiếp trong `prompt_text` của cả 21 mẫu) không nằm trong bảng
   quy đổi 15 tên của §7. Đây là các ô người dùng gõ tay lúc sinh ảnh (Pha 5), không
   phải giá trị hệ thống. Task 13 thiết kế lại T-2 cho nhóm này thành kiểm cú pháp,
   không kiểm nguồn giá trị nghiệp vụ — cần xác nhận đây đúng là ý định spec.
3. **`library.dat_mac_dinh()`** được §4.2 nhắc tên (ràng buộc "chỉ một `is_default`
   mỗi `(owner_id, target_format)`") nhưng không lane nào trong §9.2 sở hữu việc viết
   nó, và không endpoint nào trong §6 gọi nó. Plan này không cần nó (nhập catalog tự
   kiểm soát `is_default` bằng dữ liệu nguồn), nhưng khi USER được phép tự đặt mặc
   định cho bản clone riêng của họ (pha sau?), hàm này cần một chủ.
4. **Endpoint đặt `share_level` không có tên trong §6.6** — spec chỉ nói "catalog chỉ
   admin đặt được" mà không khai đường HTTP nào làm việc đó. Task 8 tự thêm
   `POST /api/library/{kind}/{item_id}/share-level` để cột không trở thành chết
   (viết được nhưng không ai gọi). Cần xác nhận tên/đường dẫn này.
