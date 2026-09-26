# PROMPT AI — Pha 3 (LÕI STUDIO) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Brief ra khỏi `AppProject.payload` thành thực thể CSDL riêng (`ommi_brief`), thêm vòng lặp iterate có 2 lượt miễn phí đếm trong CSDL, gộp bước khoá nhân vật của `apps/prompt_canh` vào PROMPT AI rồi xoá app đó, và đổi lối vào mặc định sang 2-pane Studio Kịch bản.

**Architecture:** Năm làn song song, một tệp một chủ. Làn **M** sở hữu mọi thứ dùng chung (migration, model CSDL, `manifest.py`, `routes/__init__.py`, `jobs.py`); làn **C** brief + bundle + placeholder; làn **D** vòng lặp iterate + tiền; làn **E** nhân vật/bối cảnh + xoá `prompt_canh`; làn **J** frontend. Mọi việc gọi LLM đi qua hàng đợi job của nền tảng; `bundle` và `preflight` **không** gọi LLM nên miễn phí.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 (`Mapped`/`mapped_column`) · Alembic · PostgreSQL (production) / SQLite (test) · pytest · React 19 + Vite 8 + vitest · Playwright (opt-in)

**Spec:** [`docs/superpowers/specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md`](../specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md)

---

## Global Constraints

Sao đúng bảng §2 của spec. **Mọi task ngầm mang toàn bộ mục này.**

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (khai ở `apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ được import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` (`AGENTS.md` §8.2b) |
| G-3 | App→app | Chỉ cạnh khai tường minh trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`. Spec này thêm **đúng một** cạnh: `("prompt_ai_ommi", "taovideo")` |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring (`test_no_app_slug_is_hardcoded_in_the_platform`) |
| G-5 | Alembic | **MỘT head duy nhất**. Head hiện tại: `edb8b0fc0ac9` (`alembic/versions/20260925_1800_marketplace_piece.py`). 116 revision, chuỗi thẳng |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số **không được trùng** (`tools/check_so_test.py` là bánh cóc). Số cao nhất đang dùng: **5000** |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM: `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`. `.ps1` thuần ASCII. Không viết Python inline qua PowerShell (`AGENTS.md` §5) |
| G-8 | Việc > vài giây | Đi qua hàng đợi job (`platform_core/job_submit.py:40 submit_with_credit`). Cloudflare cắt upload 100 MB / phản hồi 100 giây |
| G-9 | Tiền | Giữ chỗ → quyết toán → hoàn. `credit.giu_cho()` khi nộp; `credit.quyet_toan(db, user_id, job_id, actual)`; handler **phải ném exception khi lỗi** — trả về êm ru là mất tiền hoàn của khách |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}`, `server/templating.py:ASSET_VER` |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt, chốt trên `https://app.lttstudios.com` (loopback bỏ qua Cloudflare) |
| G-12 | Lệnh nặng | Qua `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n` ≤ 7. Kiểm `tools\cua_so_yen.py trang-thai` + `tools\tai_may.py` trước |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate — không L1, không L2, không L3. Gate chỉ một lần ở CUỐI PLAN |
| G-14 | `D:\BOT GEMINI` | Kho tham chiếu **CHỈ ĐỌC**. Đọc `.db` phải copy sang scratchpad rồi mở `mode=ro` |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |

**Commit message**: tiếng Việt **không dấu**, kết bằng dòng trống rồi

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Quyết định thi hành — chỗ spec chưa nói hoặc nói hai giọng

Đọc mục này **trước** Task đầu tiên. Bảy quyết định dưới đây là của plan này, không phải của spec; mỗi quyết định ghi cái giá nếu sai.

| # | Chỗ spec hở | Quyết định của plan | Giá nếu sai |
|---|---|---|---|
| **P-1** | §9.1 cho làn M sở hữu `alembic/versions/`; §9.2 lại cho C/D/E sở hữu thân model (`tables/kich_ban.py` phần `OmmiBrief`…) | **Làn M sở hữu CẢ model CSDL lẫn migration.** C/D/E chỉ sở hữu `services/` + `routes/`. Hai chủ cho một schema là đúng bẫy `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop` | Nếu sai: C/D/E phải chờ M thêm cột. Rẻ — một yêu cầu một dòng |
| **P-2** | §5.2 đòi tách `tables.py` thành 5 tệp; việc đó là task đầu **pha 1** của làn M, có thể chưa gộp | Task **M0** chỉ tách TỐI THIỂU: `tables.py` → `tables/tai_nguyen.py` (nguyên văn) + `tables/__init__.py` re-export `*`. Nếu pha 1 đã tách rồi thì M0 là no-op. ⛔ Không tách tiếp `thu_vien.py`/`chia_se.py` trong pha 3 | Nếu sai: pha 4 tách tiếp, `__init__.py` giữ mọi tên cũ nên không ai vỡ (R-4) |
| **P-3** | §5.3 nói "migration `drop` bảng của `prompt_canh`" | **`apps/prompt_canh` KHÔNG có bảng nào** — đo được: `grep -rn "__tablename__\|table_prefix" apps/prompt_canh/` trả **rỗng**. ⇒ Không có migration drop. Task xoá chỉ xoá mã + dọn 10 tệp test | Nếu sai (có bảng ẩn ở chỗ khác): migration drop là việc của làn M, thêm sau, không chặn |
| **P-4** | `platform_core/jobs.py:784 resolve_handler` bắt **mọi** job_type của một app về đúng `apps/<slug>/jobs.py::handle`. §9.2 không cấp `jobs.py` cho làn nào | **`jobs.py` là của làn M.** ⛔ Không thêm `job_types` mới; thêm **giá trị `operation`** mới (`iterate`, `character_lock`) vào `_cost` (manifest) + nhánh dispatch trong `handle`. Thân xử lý nằm ở tệp của làn D/E | Nếu sai: đổi sang job_type riêng vẫn phải sửa đúng hai tệp ấy — cùng chủ, cùng chỗ |
| **P-5** | §4.2 đặt `ommi_meta_prompt.placeholders` ở **pha 4**, nhưng `bundle.py` (pha 3) cần đọc khai báo placeholder | Pha 3 đọc khai báo qua **một** hàm `bundle.khai_bao_cua(meta)`: `getattr(meta, "placeholders", None) or (meta.variables or {}).get("placeholders") or []`. Pha 4 thêm cột thật ⇒ `getattr` bắt được, ⛔ không sửa chỗ gọi | Nếu sai: một hàm một dòng phải sửa |
| **P-6** | §1.1 X-4 trỏ `tests/test_5312_*`, X-5 trỏ `tests/test_5321_*`; §9.3 lại cấp 5300–5319 cho C, 5320–5339 cho D, 5340–5369 cho E | **Dải §9.3 thắng.** T-3 (lượt miễn phí) là `test_5321_*` (làn D); khoá nhân vật là `test_5342_*` (làn E) | Nếu sai: đổi tên tệp test, không đổi mã |
| **P-7** | Q-11 (chưa có khách thật) vs. brief cũ đang nằm trong `AppProject.payload["brief"]` | **KHÔNG di trú.** `ommi_brief` là đường mới; `AppProject.payload["brief"]` giữ nguyên và `/classic` + `ProjectScreen` cũ vẫn đọc nó. Test `test_5310` khẳng định app **không vỡ** khi payload còn brief cũ | Nếu sai (có khách thật): viết một migration data ở pha 4; dữ liệu chưa mất đi đâu |
| **P-8** | §4.3 thêm bảng `ommi_canh` nhưng §5.1/§9.2 **không** cấp tệp service nào cho nó | Model `ommi_canh` ở `tables/canh.py` (**làn M**, theo P-1). CRUD cảnh nằm trong **`services/briefs.py`** (làn C) — cảnh kịch bản thuộc về brief, tách thành `services/canh.py` là chia một thực thể cho hai chủ | Nếu sai (`briefs.py` phình): tách `services/canh.py` ở pha 4, vẫn một chủ (C) |
| **P-9** | §4.3 nói `ommi_canh.id` "**không** dùng `default=_uuid` bắt buộc" | Giữ `default=_uuid` trong model **và** cho `services/briefs.py::dat_canh()` nhận `id` tường minh. SQLAlchemy chỉ áp `default` khi cột **chưa** được đặt, nên hai điều này không xung đột. `test_5305` khẳng định id truyền vào được giữ nguyên | Nếu sai: bỏ `default`, chỗ tạo phải tự sinh — một dòng |

⚠️ **`ommi_face_embedding`**: §4.2 khai bảng nhưng §6.5 **không** có endpoint nào cho nó. Pha 3 **chỉ tạo bảng** (làn M), ⛔ không viết service/route — đúng bài học `ma-phong-thu-cho-ca-khong-the-xay-ra`. Người ghi đầu tiên là `services/composite.py` ở pha 5.

### Hai thứ cùng tên "cảnh" — điều pha 3 PHẢI giữ (spec §4.3 + §6.2b)

| # | Luật | Task thi hành |
|---|---|---|
| S-1 | Cảnh **kịch bản** là nguồn chân lý duy nhất của prompt đi ra ngoài | C5, C6 |
| S-2 | `ommi_scene` là **KHUNG HÌNH** storyboard, không phải cảnh ⇒ pha 3 thêm `canh_id String(36) nullable index` | **M2** |
| S-3 | `ommi_binding.scene_id` **luôn** là id cảnh kịch bản; từ pha 3 là `ommi_canh.id` | C4, C5 |
| S-4 | ⭐ `ommi_canh.id` **tái dùng ĐÚNG id cũ** (`payload["scenes"][].id`) ⇒ bindings pha 1 sống sót, ⛔ không cần di trú | **C4** + `test_5305`, `test_5308` |
| S-5 | ⛔ **Không** đổi tên `ommi_binding.scene_id` | mọi task — ⛔ đừng chạm |
| §6.2b-1 | `camera`/`lighting`/`mood` của `ommi_canh` là **chữ tự do**. Chi tiết đầy đủ đi vào `prompt`: ghép cuối prompt `Camera: <camera>. Lighting: <lighting>. Mood: <mood>.` | **C6** + `test_5309` |
| §6.2b-2 | ⛔ Pha 3 **KHÔNG** ép `camera`/`mood` về enum đóng của `taovideo`. Việc suy ra enum là của **pha 2** (`handoff_stage`, làn B) | ⛔ không task nào của pha 3 |

⚠️ **T-2 ở pha 3 chỉ đo 12 meta prompt** (spec §7.2). 21 `image_gen_template` dùng bộ placeholder **khác** (`SUBJECT`/`STYLE`/`EXTRA`/`EQUIPMENT`) và nguồn giá trị của chúng ở **pha 5** — ⛔ đừng ghi "đã kiểm 21 template" trong báo cáo pha 3.

---

## Thứ tự làn — cái gì chặn cái gì

```
[pha 1 + pha 2 da gop main]
        |
        v
   M0 -> M1 -> M2 ------> M3
                |          ^
                +--> C ----+
                |    | \
                |    |  +--> D
                |    |
                +--> E --> [E5: xoa prompt_canh]
                     ^
                     +--- chi sau khi E3 (khoa nhan vat) XANH
                                |
                                v
                          J (theo sau C, D, E)
```

| Làn | Chặn bởi | Chặn ai | Chạy song song được với |
|---|---|---|---|
| **M** (M0→M1→M2) | pha 1 đã gộp `main` (cần `tables/`, `ommi_binding`, `services/bindings.py`) | C, D, E, J | — (làn đầu tiên, một mình) |
| **M3** | C, D, E đã có tệp `routes/*.py` để đăng ký | J | chạy **cuối** các làn backend |
| **C** | M2 | D (cần `bundle.dung_bundle`), J | **E** |
| **D** | M2 **và** C4 (`bundle.dung_bundle`) | J | **E** |
| **E** | M2 | J, và E5 chặn "deploy pha 3" | **C**, **D** |
| **E5** | **E3 xanh** (spec X-5) | deploy pha 3 | — |
| **J** | C3, C4, D3, E2 (cần endpoint thật) | deploy pha 3 | — |

⛔ Hai làn **không** được sửa cùng một tệp. Cần tệp của làn khác ⇒ đọc `**Interfaces:**` của task đó và chờ, ⛔ không tự sửa.

⛔ Trước khi tạo bất kỳ tệp test: `python tools/check_so_test.py --list` để chắc số chưa ai lấy.

---

## Bản đồ tệp — ai tạo, ai sửa

| Tệp | Làn | Tạo / Sửa |
|---|---|---|
| `apps/prompt_ai_ommi/tables/__init__.py` | M | Sửa (re-export thêm tên mới) |
| `apps/prompt_ai_ommi/tables/brief.py` | M | Tạo — `OmmiBrief` |
| `apps/prompt_ai_ommi/tables/canh.py` | M | Tạo — `OmmiCanh` |
| `apps/prompt_ai_ommi/tables/iteration.py` | M | Tạo — `OmmiIteration` |
| `apps/prompt_ai_ommi/tables/nhan_vat.py` | M | Tạo — `OmmiCharacter`, `OmmiOutfit`, `OmmiPose`, `OmmiBackground`, `OmmiFaceEmbedding` |
| `alembic/versions/<ts>_ommi_pha3.py` | M | Tạo — một migration duy nhất cho cả pha |
| `apps/prompt_ai_ommi/manifest.py` | M | Sửa — `_cost` nhận `operation` mới |
| `apps/prompt_ai_ommi/jobs.py` | M | Sửa — nhánh dispatch `iterate`, `character_lock` |
| `apps/prompt_ai_ommi/routes/__init__.py` | M | Sửa — đăng ký router mới |
| `apps/prompt_ai_ommi/services/placeholders.py` | C | Tạo |
| `apps/prompt_ai_ommi/services/bundle.py` | C | Tạo |
| `apps/prompt_ai_ommi/services/briefs.py` | C | Tạo — gồm CRUD cảnh (P-8) |
| `apps/prompt_ai_ommi/routes/briefs.py` | C | Tạo |
| `apps/prompt_ai_ommi/services/iterate.py` | D | Tạo |
| `apps/prompt_ai_ommi/routes/iterate.py` | D | Tạo |
| `apps/prompt_ai_ommi/services/nhan_vat.py` | E | Tạo |
| `apps/prompt_ai_ommi/routes/nhan_vat.py` | E | Tạo |
| `apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt` | E | Tạo — chuyển từ `apps/prompt_canh/prompts/step1_character_lock.txt` |
| `apps/prompt_canh/**` | E | **XOÁ** (E5) |
| `frontend/prompt-ai-ommi/src/StudioShell.tsx` | J | Tạo |
| `frontend/prompt-ai-ommi/src/BriefPane.tsx` | J | Tạo |
| `frontend/prompt-ai-ommi/src/OmmiShell.tsx` | J | Sửa — lối vào mặc định |
| `frontend/prompt-ai-ommi/src/ommiApi.ts` | J | Sửa — hàm gọi endpoint mới |

---

# LÀN M — hạ tầng dùng chung

## Task M0: Bảo đảm `tables/` là package (no-op nếu pha 1 đã tách)

**Files:**
- Modify: `apps/prompt_ai_ommi/tables/__init__.py`
- Test: `tests/test_5300_pha3_schema.py`

**Interfaces:**
- Consumes: pha 1 đã tách `tables.py` → `tables/` (P-2). Nếu chưa, task này tách tối thiểu.
- Produces: `apps.prompt_ai_ommi.tables` là package, re-export **mọi** tên lớp cũ.

- [ ] **Step 1: Kiểm hiện trạng trước khi sửa gì**

```bash
python -c "import pathlib; p=pathlib.Path('apps/prompt_ai_ommi'); print('PACKAGE' if (p/'tables/__init__.py').exists() else 'MODULE')"
```

`PACKAGE` ⇒ pha 1 đã tách, sang Step 3. `MODULE` ⇒ làm Step 2.

- [ ] **Step 2: Tách tối thiểu (chỉ khi in ra `MODULE`)**

```bash
mkdir -p apps/prompt_ai_ommi/tables
git mv apps/prompt_ai_ommi/tables.py apps/prompt_ai_ommi/tables/tai_nguyen.py
```

Rồi tạo `apps/prompt_ai_ommi/tables/__init__.py`:

```python
"""Bang CSDL cua PROMPT AI — tach thanh package de moi lan mot tep.

⛔ Tep nay CHI re-export. Khong dinh nghia model o day: mot model hai cho khai
la dung bay `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`.
"""
from apps.prompt_ai_ommi.tables.tai_nguyen import *  # noqa: F401,F403
```

- [ ] **Step 3: Viết test đỏ — mọi tên lớp cũ vẫn import được (spec R-4)**

`tests/test_5300_pha3_schema.py`:

```python
"""Pha 3 — schema: tach package khong lam vo import cu, va bang moi co du cot."""
from __future__ import annotations

import pytest

TEN_CU = (
    "OmmiResource", "OmmiResourceVariant", "OmmiTag", "OmmiResourceTag",
    "OmmiCollection", "OmmiCollectionItem", "OmmiResourceUsage",
    "OmmiMetaPrompt", "OmmiPromptSnippet", "OmmiStyle", "OmmiPromptVersion",
    "OmmiStoryboard", "OmmiScene", "OmmiSceneVersion",
)


@pytest.mark.parametrize("ten", TEN_CU)
def test_ten_lop_cu_van_import_duoc(ten):
    """Tach `tables.py` thanh package KHONG duoc lam vo mot import nao."""
    import apps.prompt_ai_ommi.tables as t
    assert hasattr(t, ten), f"mat {ten} sau khi tach package"
```

- [ ] **Step 4: Chạy test, phải XANH ngay (đây là lưới an toàn, không phải tính năng mới)**

```bash
python -m pytest tests/test_5300_pha3_schema.py -q
```

Đỏ ⇒ `__init__.py` thiếu re-export. Sửa rồi chạy lại.

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/tables tests/test_5300_pha3_schema.py
git commit -m "pha3(M0): bao dam tables la package, luoi an toan ten lop cu

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task M1: Model CSDL của pha 3

**Files:**
- Modify (làn M₁ pha 1 đã tạo sẵn dạng rỗng-có-mốc): `apps/prompt_ai_ommi/tables/brief.py`, `tables/iteration.py`, `tables/nhan_vat.py`
- Create: `apps/prompt_ai_ommi/tables/canh.py` (⭐ pha 1 KHÔNG tạo tệp này)
- Modify: `apps/prompt_ai_ommi/tables/__init__.py`
- Test: `tests/test_5300_pha3_schema.py` (thêm vào tệp của M0)

**Interfaces:**
- Produces:
  - `OmmiBrief` — cột theo spec §4.2 Pha 3, gồm `free_iterations_used: int`
  - `OmmiCanh` — cột theo spec §4.3, `UniqueConstraint("brief_id", "position")`
  - `OmmiIteration` — `UniqueConstraint("brief_id", "seq")`
  - `OmmiCharacter`, `OmmiOutfit`, `OmmiPose`, `OmmiBackground`, `OmmiFaceEmbedding`
  - Mọi lớp trên re-export qua `apps.prompt_ai_ommi.tables`

- [ ] **Step 1: Viết test đỏ — bảng mới phải có đúng cột spec đòi**

Thêm vào `tests/test_5300_pha3_schema.py`:

```python
COT_BAT_BUOC = {
    "OmmiBrief": ("id", "owner_id", "project_id", "title", "story_vi", "goal",
                  "audience", "target_duration_sec", "target_scenes",
                  "aspect_ratio", "language", "style_id", "meta_prompt_id",
                  "character_id", "background_id", "referenced_variants",
                  "status", "free_iterations_used", "archived_at",
                  "created_at", "updated_at"),
    "OmmiCanh": ("id", "brief_id", "position", "title", "duration_seconds",
                 "summary", "prompt", "negative_prompt", "camera", "lighting",
                 "mood", "continuity", "selected_version", "created_at"),
    "OmmiIteration": ("id", "brief_id", "seq", "feedback", "prompt_sent",
                      "output", "job_id", "credit_charged", "was_free",
                      "verdict", "created_at"),
    "OmmiCharacter": ("id", "owner_id", "name", "gender", "age_range",
                      "face_description", "body_description",
                      "hair_description", "outfit_description", "personality",
                      "expression_style", "movement_style",
                      "fixed_prompt_block", "negative_notes",
                      "reference_variant_ids", "share_level", "archived_at",
                      "created_at", "updated_at"),
    "OmmiBackground": ("id", "owner_id", "name", "location_type",
                       "environment_description", "lighting_description",
                       "color_palette", "camera_feel", "important_objects",
                       "fixed_prompt_block", "negative_notes",
                       "reference_variant_ids", "share_level", "archived_at",
                       "created_at", "updated_at"),
}


@pytest.mark.parametrize("ten_lop,cot", sorted(COT_BAT_BUOC.items()))
def test_bang_moi_co_du_cot(ten_lop, cot):
    import apps.prompt_ai_ommi.tables as t
    lop = getattr(t, ten_lop, None)
    assert lop is not None, f"chua co model {ten_lop}"
    co = set(lop.__table__.columns.keys())
    thieu = [c for c in cot if c not in co]
    assert not thieu, f"{ten_lop} thieu cot: {thieu}"


def test_canh_khong_trung_vi_tri_trong_mot_brief():
    """Hai canh cung `position` trong mot brief la mot thu tu KHONG xac dinh."""
    import apps.prompt_ai_ommi.tables as t
    rang_buoc = {tuple(sorted(c.columns.keys()))
                 for c in t.OmmiCanh.__table__.constraints
                 if c.__class__.__name__ == "UniqueConstraint"}
    assert ("brief_id", "position") in rang_buoc


def test_iteration_khong_trung_seq_trong_mot_brief():
    import apps.prompt_ai_ommi.tables as t
    rang_buoc = {tuple(sorted(c.columns.keys()))
                 for c in t.OmmiIteration.__table__.constraints
                 if c.__class__.__name__ == "UniqueConstraint"}
    assert ("brief_id", "seq") in rang_buoc
```

- [ ] **Step 2: Chạy test để thấy nó ĐỎ**

```bash
python -m pytest tests/test_5300_pha3_schema.py -q
```

Kỳ vọng: FAIL — `chua co model OmmiBrief`.

- [ ] **Step 3: Tạo `tables/brief.py`**

```python
"""Brief — kich ban la mot THUC THE, khong con nhet trong `AppProject.payload`.

Vi sao tach ra: loi vao moi la 2-pane (danh sach brief ⟷ khung soan). Mot danh
sach doc tu JSON long trong mot cot thi khong loc, khong sap, khong phan trang
duoc — va moi lan sua mot brief la ghi lai ca payload cua du an.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiBrief(Base):
    """Mot kich ban. `free_iterations_used` la SO DEM LUOT MIEN PHI (Q-7).

    ⛔ Bo dem PHAI o day, khong o phien: bo dem trong phien nghia la khach mo
       tab moi la duoc 2 luot mien phi nua — LLM mien phi vo han.
    """

    __tablename__ = "ommi_brief"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    story_vi: Mapped[str] = mapped_column(Text, default="", nullable=False)
    goal: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    audience: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    target_duration_sec: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    target_scenes: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(8), default="16:9", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="vi", nullable=False)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    background_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    referenced_variants: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    free_iterations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
```

⚠️ `Base` đến từ **`platform_core.db`** — MỘT `Base` dùng chung cho cả nền tảng (đo được 26/09 sau khi làn M₁ thi hành). `_uuid()` và `_now()` từ `tables/tai_nguyen.py`. ⛔ Đừng `from ...tables.tai_nguyen import Base`: nó chạy được nhưng là import gián tiếp, và một ngày ai đó dọn import ở tệp đó là vỡ.

- [ ] **Step 4: Tạo `tables/canh.py`**

```python
"""Canh KICH BAN — nguon chan ly duy nhat cua prompt di ra ngoai (spec S-1).

⛔ KHONG lan voi `ommi_scene`: cai do la KHUNG HINH storyboard, co
   `storyboard_id`/`position`/`image_key`, va `prompt`/`camera` cua no chi la
   ban SAO phuc vu viec sinh anh (spec S-2).

⭐ `id` phai tai dung duoc id cu (`payload["scenes"][].id`) de binding cua pha 1
   song sot qua pha 3 ma khong can di tru (spec S-4). SQLAlchemy chi ap `default`
   khi cot CHUA duoc dat, nen giu `default=_uuid` van cho truyen id vao.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


class OmmiCanh(Base):
    __tablename__ = "ommi_canh"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    brief_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Chu TU DO, giau chi tiet. ⛔ Dung ep ve enum dong cua `taovideo` o day —
    # viec quy doi la cua pha 2 (`handoff_stage`), va chi tiet goc phai di vao
    # `prompt` chu khong bi bo (spec §6.2b).
    camera: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lighting: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mood: Mapped[str] = mapped_column(Text, default="", nullable=False)
    continuity: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selected_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("brief_id", "position", name="uq_ommi_canh_vitri"),
    )
```

- [ ] **Step 5: Tạo `tables/iteration.py`**

```python
"""Mot luot goi LLM de sua kich ban, va phan quyet cua khach ve luot do."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


class OmmiIteration(Base):
    """`was_free` ghi lai luot NAY co thu tien hay khong — de sau con doi soat.

    ⛔ `verdict="rejected"` KHONG hoan credit. Hoan thi khach bam rejected moi
       lan la LLM mien phi vo han (spec §6.4).
    """

    __tablename__ = "ommi_iteration"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    brief_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prompt_sent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    credit_charged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    was_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("brief_id", "seq", name="uq_ommi_iteration_seq"),
    )
```

- [ ] **Step 6: Tạo `tables/nhan_vat.py`**

```python
"""Nhan vat / trang phuc / dang / boi canh — goc cua viec nhat quan xuyen canh.

⚠️ Do duoc tren CSDL cua ban goc 26/09: bon bang tuong duong o do co 0 dong —
   thiet ke cong phu ma chua ai nhap mot dong. Chu du an chot 26/09 van xay
   (Q-14). Neu sau nay do duoc la khach cung khong dung, day la cho cat truoc.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from apps.prompt_ai_ommi.tables.tai_nguyen import _uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiCharacter(Base):
    __tablename__ = "ommi_character"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    gender: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    age_range: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    face_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    body_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hair_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    outfit_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personality: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expression_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    movement_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Khoi chu CHEN NGUYEN VAN vao moi canh — day la thu giu nhan vat khong doi.
    fixed_prompt_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiOutfit(Base):
    __tablename__ = "ommi_outfit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiPose(Base):
    __tablename__ = "ommi_pose"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pose_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)


class OmmiBackground(Base):
    __tablename__ = "ommi_background"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    location_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    environment_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lighting_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    color_palette: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    camera_feel: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    important_objects: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fixed_prompt_block: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference_variant_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    share_level: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiFaceEmbedding(Base):
    """⚠️ Pha 3 CHI tao bang. ⛔ Khong service, khong route — §6.5 khong co
    endpoint nao cho no. Nguoi ghi dau tien la `services/composite.py` o pha 5.
    """

    __tablename__ = "ommi_face_embedding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    vector_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    backend: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
```

- [ ] **Step 7: Re-export trong `tables/__init__.py`**

```python
from apps.prompt_ai_ommi.tables.brief import OmmiBrief  # noqa: F401
from apps.prompt_ai_ommi.tables.canh import OmmiCanh  # noqa: F401
from apps.prompt_ai_ommi.tables.iteration import OmmiIteration  # noqa: F401
from apps.prompt_ai_ommi.tables.nhan_vat import (  # noqa: F401
    OmmiBackground, OmmiCharacter, OmmiFaceEmbedding, OmmiOutfit, OmmiPose)
```

- [ ] **Step 8: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5300_pha3_schema.py -q
```

- [ ] **Step 9: Commit**

```bash
git add apps/prompt_ai_ommi/tables tests/test_5300_pha3_schema.py
git commit -m "pha3(M1): model CSDL pha 3 — brief, canh, iteration, nhan vat

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task M2: Migration pha 3 (một tệp duy nhất) + `ommi_scene.canh_id`

**Files:**
- Create: `alembic/versions/<YYYYMMDD_HHMM>_ommi_pha3.py`
- Modify: `apps/prompt_ai_ommi/tables/tai_nguyen.py` (thêm `canh_id` vào `OmmiScene`)
- Test: `tests/test_5300_pha3_schema.py` (thêm)

**Interfaces:**
- Consumes: model của M1.
- Produces: schema thật trong CSDL; `OmmiScene.canh_id` (spec S-2).

- [ ] **Step 1: Lấy head THẬT — ⛔ đừng gõ lại giá trị trong spec**

```bash
python -m alembic heads
```

Phải in ra **đúng MỘT** head. In ra nhiều ⇒ **DỪNG**, báo chủ dự án: có phiên khác vừa thêm migration, gộp head là việc cần biết bối cảnh. Ghi giá trị đó lại, gọi là `<HEAD>`.

- [ ] **Step 2: Viết test đỏ — `ommi_scene` phải có `canh_id`**

Thêm vào `tests/test_5300_pha3_schema.py`:

```python
def test_khung_hinh_storyboard_biet_no_ve_cho_canh_nao():
    """`ommi_scene` la KHUNG HINH; `canh_id` noi no ve cho canh kich ban nao.

    Khong co cot nay thi hai thu cung ten "canh" van khong lien ket duoc voi
    nhau — dung con bo spec §4.3 dang chua.
    """
    import apps.prompt_ai_ommi.tables as t
    assert "canh_id" in t.OmmiScene.__table__.columns.keys()
    assert t.OmmiScene.__table__.columns["canh_id"].nullable is True
```

- [ ] **Step 3: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5300_pha3_schema.py::test_khung_hinh_storyboard_biet_no_ve_cho_canh_nao -q
```

Kỳ vọng: FAIL — `assert 'canh_id' in [...]`.

- [ ] **Step 4: Thêm cột vào model `OmmiScene`**

Trong `apps/prompt_ai_ommi/tables/tai_nguyen.py`, lớp `OmmiScene`, ngay dưới `storyboard_id`:

```python
    # Khung hinh nay ve cho CANH KICH BAN nao (spec S-2). `nullable` vi khung
    # hinh cu tao truoc pha 3 khong biet canh nao — va vi khach van duoc ve mot
    # khung hinh roi moi gan vao canh.
    canh_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
```

- [ ] **Step 5: Tạo migration**

`alembic/versions/20260926_1200_ommi_pha3.py` (đổi timestamp cho khớp lúc chạy):

```python
"""ommi pha3: brief, canh, iteration, nhan vat; ommi_scene.canh_id

Revision ID: a1c3e5f70b92
Revises: <HEAD>
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1c3e5f70b92"
down_revision = "<HEAD>"   # <- thay bang gia tri Step 1 in ra
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ommi_brief",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("project_id", sa.String(36), nullable=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("story_vi", sa.Text(), nullable=False, server_default=""),
        sa.Column("goal", sa.String(300), nullable=False, server_default=""),
        sa.Column("audience", sa.String(300), nullable=False, server_default=""),
        sa.Column("target_duration_sec", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("target_scenes", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("aspect_ratio", sa.String(8), nullable=False, server_default="16:9"),
        sa.Column("language", sa.String(8), nullable=False, server_default="vi"),
        sa.Column("style_id", sa.String(36), nullable=True),
        sa.Column("meta_prompt_id", sa.String(36), nullable=True),
        sa.Column("character_id", sa.String(36), nullable=True),
        sa.Column("background_id", sa.String(36), nullable=True),
        sa.Column("referenced_variants", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("free_iterations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ommi_canh",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("brief_id", sa.String(36), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("camera", sa.Text(), nullable=False, server_default=""),
        sa.Column("lighting", sa.Text(), nullable=False, server_default=""),
        sa.Column("mood", sa.Text(), nullable=False, server_default=""),
        sa.Column("continuity", sa.Text(), nullable=False, server_default=""),
        sa.Column("selected_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("brief_id", "position", name="uq_ommi_canh_vitri"),
    )
    op.create_table(
        "ommi_iteration",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("brief_id", sa.String(36), nullable=False, index=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt_sent", sa.Text(), nullable=False, server_default=""),
        sa.Column("output", sa.Text(), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("credit_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("was_free", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verdict", sa.String(10), nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("brief_id", "seq", name="uq_ommi_iteration_seq"),
    )
    op.create_table(
        "ommi_character",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("gender", sa.String(32), nullable=False, server_default=""),
        sa.Column("age_range", sa.String(32), nullable=False, server_default=""),
        sa.Column("face_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hair_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("outfit_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("personality", sa.Text(), nullable=False, server_default=""),
        sa.Column("expression_style", sa.Text(), nullable=False, server_default=""),
        sa.Column("movement_style", sa.Text(), nullable=False, server_default=""),
        sa.Column("fixed_prompt_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ommi_outfit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("character_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ommi_pose",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("pose_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ommi_background",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("location_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("environment_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("lighting_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("color_palette", sa.String(200), nullable=False, server_default=""),
        sa.Column("camera_feel", sa.String(200), nullable=False, server_default=""),
        sa.Column("important_objects", sa.Text(), nullable=False, server_default=""),
        sa.Column("fixed_prompt_block", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_variant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("share_level", sa.String(12), nullable=False, server_default="private"),
        sa.Column("archived_at", _TS, nullable=True),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "ommi_face_embedding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("character_id", sa.String(36), nullable=False, index=True),
        sa.Column("variant_id", sa.String(36), nullable=False),
        sa.Column("vector_json", sa.JSON(), nullable=False),
        sa.Column("backend", sa.String(32), nullable=False),
        sa.Column("created_at", _TS, nullable=False, server_default=sa.func.now()),
    )
    op.add_column("ommi_scene", sa.Column("canh_id", sa.String(36), nullable=True))
    op.create_index("ix_ommi_scene_canh_id", "ommi_scene", ["canh_id"])


def downgrade() -> None:
    op.drop_index("ix_ommi_scene_canh_id", table_name="ommi_scene")
    op.drop_column("ommi_scene", "canh_id")
    for ten in ("ommi_face_embedding", "ommi_background", "ommi_pose",
                "ommi_outfit", "ommi_character", "ommi_iteration",
                "ommi_canh", "ommi_brief"):
        op.drop_table(ten)
```

- [ ] **Step 6: Khẳng định vẫn MỘT head sau khi thêm**

```bash
python -m alembic heads
```

Phải in đúng một head, và là `a1c3e5f70b92`. In ra hai ⇒ `down_revision` sai.

- [ ] **Step 7: Chạy migration lên rồi xuống rồi lên lại**

```bash
python -m alembic upgrade head && python -m alembic downgrade -1 && python -m alembic upgrade head
```

⚠️ `downgrade` phải chạy được. Một migration không xuống được là một migration không rollback được lúc deploy hỏng.

- [ ] **Step 8: Chạy test schema, phải XANH**

```bash
python -m pytest tests/test_5300_pha3_schema.py -q
```

- [ ] **Step 9: Commit**

```bash
git add alembic/versions apps/prompt_ai_ommi/tables tests/test_5300_pha3_schema.py
git commit -m "pha3(M2): migration pha 3 + ommi_scene.canh_id

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task M3: `manifest._cost` nhận việc mới · `jobs.handle` dispatch · đăng ký router

⚠️ Chạy **sau** khi C, D, E đã có tệp `routes/*.py`, nếu không `routes/__init__.py` import tệp chưa tồn tại và cả app vỡ.

**Files:**
- Modify: `apps/prompt_ai_ommi/manifest.py:18-31` (hàm `_cost`)
- Modify: `apps/prompt_ai_ommi/jobs.py:52-57` (hàm `handle`, phần kiểm `operation`)
- Modify: `apps/prompt_ai_ommi/routes/__init__.py:21-23`
- Test: `tests/test_5301_gia_va_dispatch.py`

**Interfaces:**
- Consumes: `apps.prompt_ai_ommi.services.iterate.chay_iterate(params, ctx)` (làn D), `apps.prompt_ai_ommi.services.nhan_vat.chay_khoa_nhan_vat(params, ctx)` (làn E).
- Produces: `_cost(params)` hiểu `operation in {"director","storyboard","batch","iterate","character_lock"}`; `handle` dispatch đúng.

⭐ Vì sao **không** thêm `job_types` mới: `platform_core/jobs.py:784 resolve_handler` map mọi `job_type` của một app về đúng `apps/<slug>/jobs.py::handle`. Thêm job_type mới nghĩa là thêm giá vào `manifest` **và** thêm nhánh vào `handle` — đúng hai tệp ấy. Dùng `operation` thì chỉ một tên job, ít mặt hơn (P-4).

- [ ] **Step 1: Viết test đỏ — giá và dispatch**

`tests/test_5301_gia_va_dispatch.py`:

```python
"""Pha 3 — gia cho viec moi, va `handle` dispatch dung nhanh."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.manifest import _cost


@pytest.mark.parametrize("op", ["iterate", "character_lock"])
def test_viec_moi_co_gia_duong(op):
    """Mot `operation` khong co gia se bi registry tu choi luc nop job."""
    assert _cost({"operation": op, "scene_count": 6}) > 0


def test_luot_iterate_khong_dat_hon_mot_luot_director():
    """Iterate la sua mot kich ban da co, khong dung lai tu dau."""
    assert _cost({"operation": "iterate", "scene_count": 6}) <= _cost(
        {"operation": "director", "scene_count": 6})


def test_khoa_nhan_vat_gia_khong_phu_thuoc_so_canh():
    """Khoa nhan vat sinh MOT khoi chu, khong lien quan so canh."""
    assert (_cost({"operation": "character_lock", "scene_count": 1})
            == _cost({"operation": "character_lock", "scene_count": 20}))


def test_operation_la_khoa_cua_gia_va_cua_dispatch_khop_nhau():
    """⭐ Hai cho khai cung mot dieu: `_cost` biet op nao, `handle` nhan op nao.

    Lech nhau thi hoac khach nop duoc viec khong co gia (registry tu choi, 500),
    hoac co gia ma khong ai chay. Ep khop bang may, khong bang giao uoc.
    """
    import inspect

    from apps.prompt_ai_ommi import jobs
    nguon = inspect.getsource(jobs.handle)
    for op in ("director", "storyboard", "iterate", "character_lock"):
        assert f'"{op}"' in nguon, f"`handle` khong nhac op {op!r}"
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5301_gia_va_dispatch.py -q
```

Kỳ vọng: `test_khoa_nhan_vat_gia_khong_phu_thuoc_so_canh` FAIL (hiện `_cost` rơi về `_director_cost` phụ thuộc `scene_count`), và `test_operation_la_khoa...` FAIL.

- [ ] **Step 3: Sửa `_cost`**

Trong `apps/prompt_ai_ommi/manifest.py`, thêm vào `_cost` **trước** dòng `return _director_cost(params)`:

```python
    if kind == "iterate":
        # Sua mot kich ban DA CO: gui lai brief + feedback, khong dung lai tu
        # dau. Dat bang mot nua director, san 3..9.
        return max(3, min(9, math.ceil(_director_cost(params) / 2)))
    if kind == "character_lock":
        # Sinh MOT khoi chu co dinh cho nhan vat. Khong lien quan so canh.
        return 3
```

- [ ] **Step 4: Sửa `jobs.handle`**

Trong `apps/prompt_ai_ommi/jobs.py`, thay khối kiểm `operation` (dòng ~55-57):

```python
    operation = str(params.get("operation") or "director")
    if operation not in {"director", "storyboard", "iterate", "character_lock"}:
        raise ValueError(_t('Operation không hợp lệ.'))
    if operation == "iterate":
        from apps.prompt_ai_ommi.services.iterate import chay_iterate
        return chay_iterate(params, ctx)
    if operation == "character_lock":
        from apps.prompt_ai_ommi.services.nhan_vat import chay_khoa_nhan_vat
        return chay_khoa_nhan_vat(params, ctx)
```

⚠️ Đặt hai nhánh này **trước** dòng `if ctx is not None: ctx.progress(10, ...)`, nhưng **sau** phép kiểm `len(story) < 20`? ⛔ **Không** — `character_lock` không có `story`. Chuyển phép kiểm `story` vào **sau** hai nhánh trên:

```python
def handle(params: dict, ctx=None) -> dict:
    operation = str(params.get("operation") or "director")
    if operation not in {"director", "storyboard", "iterate", "character_lock"}:
        raise ValueError(_t('Operation không hợp lệ.'))
    if operation == "iterate":
        from apps.prompt_ai_ommi.services.iterate import chay_iterate
        return chay_iterate(params, ctx)
    if operation == "character_lock":
        from apps.prompt_ai_ommi.services.nhan_vat import chay_khoa_nhan_vat
        return chay_khoa_nhan_vat(params, ctx)
    story = str(params.get("story") or "").strip()
    if len(story) < 20:
        raise ValueError(_t('Nội dung brief tối thiểu 20 ký tự.'))
    ...  # phan con lai giu nguyen
```

- [ ] **Step 5: Đăng ký router mới**

Trong `apps/prompt_ai_ommi/routes/__init__.py`, sửa dòng import và bổ sung mô tả trong docstring:

```python
from apps.prompt_ai_ommi.routes import (  # noqa: F401  (import de dang ky route)
    pages, projects, handoff, assets_catalog, resources, library, storyboard,
    overview, bindings, briefs, iterate, nhan_vat)
```

Thêm vào docstring:

```
    bindings.py       The @IMAGE_k/@VIDEO_k ↔ variant (pha 1).
    briefs.py         Brief, canh kich ban, preflight, bundle, bao gia.
    iterate.py        Vong lap sua kich ban va phan quyet tung luot.
    nhan_vat.py       Nhan vat, trang phuc, dang, boi canh va buoc khoa.
```

- [ ] **Step 6: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5301_gia_va_dispatch.py -q
```

- [ ] **Step 7: Khẳng định app vẫn nạp được vào registry**

```bash
python -c "from platform_core.registry import discover; m=[x for x in discover() if x.manifest.slug=='prompt_ai_ommi'][0]; print('OK', m.error)"
```

`OK None` ⇒ đúng. Có `error` ⇒ sửa trước khi commit.

- [ ] **Step 8: Commit**

```bash
git add apps/prompt_ai_ommi/manifest.py apps/prompt_ai_ommi/jobs.py apps/prompt_ai_ommi/routes/__init__.py tests/test_5301_gia_va_dispatch.py
git commit -m "pha3(M3): gia cho iterate va character_lock, dispatch, dang ky router

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# LÀN C — Brief · cảnh kịch bản · bundle · placeholder

## Task C1: `services/placeholders.py` — bảng quy đổi và bộ kiểm

**Files:**
- Create: `apps/prompt_ai_ommi/services/placeholders.py`
- Test: `tests/test_5302_placeholders.py`

**Interfaces:**
- Produces:
  - `NGUON_GIA_TRI: dict[str, str]` — 15 tên CHỮ HOA → mô tả nguồn (spec §7)
  - `tim_placeholder(body: str) -> list[str]` — các tên `{TEN}` xuất hiện trong `body`
  - `kiem_placeholder(body: str, khai_bao: list[str], co_gia_tri: dict) -> list[str]` — trả tên **thiếu**
  - `render(body: str, co_gia_tri: dict) -> str`

- [ ] **Step 1: Viết test đỏ — ba phép của spec §7.1**

`tests/test_5302_placeholders.py`:

```python
"""Pha 3 — placeholder: ba phep cua spec §7.1, khong thieu phep nao."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services.placeholders import (
    kiem_placeholder, render, tim_placeholder)


def test_chi_bat_chu_hoa_khong_bat_vi_du_json():
    """Mau chua vi du JSON `{"scenes": []}` — ⛔ do khong phai placeholder."""
    body = 'Tra ve {"summary": "", "scenes": []} cho {TITLE}'
    assert tim_placeholder(body) == ["TITLE"]


def test_bat_ten_co_gach_duoi_va_so():
    body = "{BRIEF_VI} {STYLE_NEGATIVE} {FACTION_A} {MIN_COMBAT_DISTANCE}"
    assert set(tim_placeholder(body)) == {
        "BRIEF_VI", "STYLE_NEGATIVE", "FACTION_A", "MIN_COMBAT_DISTANCE"}


def test_phep_1_bien_dung_ma_khong_khai_thi_thieu():
    """Mau co bien ma khong ai biet de HOI khach — phai bao thieu."""
    thieu = kiem_placeholder("{TITLE} {BI_AN}", ["TITLE"], {"TITLE": "x"})
    assert "BI_AN" in thieu


def test_phep_2_bien_khai_ma_khong_ai_cap_gia_tri_thi_thieu():
    """Khong co phep nay thi mau render ra `{BRIEF_VI}` nguyen van gui LLM."""
    thieu = kiem_placeholder("{TITLE} {BRIEF_VI}", ["TITLE", "BRIEF_VI"],
                             {"TITLE": "x"})
    assert "BRIEF_VI" in thieu


def test_phep_3_chuoi_da_render_khong_con_cap_chu_hoa_nao():
    """Luoi cuoi — bat ca hai ca tren."""
    ra = render("{TITLE}: {BRIEF_VI}", {"TITLE": "A", "BRIEF_VI": "B"})
    assert tim_placeholder(ra) == []
    assert ra == "A: B"


def test_du_gia_tri_thi_khong_thieu_gi():
    assert kiem_placeholder("{TITLE}", ["TITLE"], {"TITLE": "x"}) == []


def test_gia_tri_rong_VAN_la_thieu():
    """⭐ Khach de trong o nhap la mot ca THAT (mau `Ong Ngoai` co 4 bien tu do).

    Coi rong la "co gia tri" thi mau render ra cau cut dau roi gui LLM.
    """
    assert kiem_placeholder("{FACTION_A}", ["FACTION_A"],
                            {"FACTION_A": "  "}) == ["FACTION_A"]


def test_bang_nguon_gia_tri_co_du_15_ten_spec_doi():
    from apps.prompt_ai_ommi.services.placeholders import NGUON_GIA_TRI
    can = {"TITLE", "PROJECT_NAME", "BRIEF_VI", "DURATION", "SCENES",
           "ASPECT_RATIO", "ASPECT", "STYLE_FULL", "STYLE_POSITIVE",
           "STYLE_NEGATIVE", "ASSET_LIST", "VIDEO_LIST", "PROMPT", "REF_NOTE",
           "CHARACTER_DESCRIPTION"}
    assert can <= set(NGUON_GIA_TRI)
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5302_placeholders.py -q
```

Kỳ vọng: `ModuleNotFoundError: No module named 'apps.prompt_ai_ommi.services.placeholders'`.

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Placeholder cua meta prompt: bang quy doi + bo kiem.

⭐ VI SAO CO TEP NAY. Ban goc (`D:\\BOT GEMINI`) dung placeholder CHU HOA khai
   tuong minh (`{BRIEF_VI}`, `{DURATION}`...); ben ta truoc day dung chu thuong
   TINH trong `prompts/director_user.txt`. Chuyen 12 mau cua ban goc sang ma
   khong co bang quy doi thi mau se render ra chuoi `{BRIEF_VI}` NGUYEN VAN roi
   gui cho LLM — khach tra tien cho mot loi nhac hong.

⛔ Chi khop `\\{[A-Z][A-Z0-9_]*\\}`. Mau chua vi du JSON (`{"scenes": []}`) va do
   KHONG phai placeholder: khop rong tay se coi moi dau ngoac nhon la bien.
"""
from __future__ import annotations

import re

#: `{TEN}` -> nguon gia tri ben ta. Mo ta de nguoi doc biet HOI AI cap gia tri,
#: khong phai de may doc.
NGUON_GIA_TRI: dict[str, str] = {
    "TITLE": "ommi_brief.title",
    "PROJECT_NAME": "AppProject.name (rong neu brief chua gan project)",
    "BRIEF_VI": "ommi_brief.story_vi",
    "DURATION": "ommi_brief.target_duration_sec",
    "SCENES": "ommi_brief.target_scenes",
    "ASPECT_RATIO": "ommi_brief.aspect_ratio",
    "ASPECT": "dong nghia ASPECT_RATIO (mau storyboard dung ten nay)",
    "STYLE_FULL": "composer.style_description(style)",
    "STYLE_POSITIVE": "ommi_style.body",
    "STYLE_NEGATIVE": "ommi_style.negative",
    "ASSET_LIST": "ommi_binding kind=image",
    "VIDEO_LIST": "ommi_binding kind=video",
    "PROMPT": "prompt cua canh (mau storyboard)",
    "REF_NOTE": "ghi chu anh tham chieu cua canh",
    "CHARACTER_DESCRIPTION": "ommi_character.fixed_prompt_block",
}

_MAU = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def tim_placeholder(body: str) -> list[str]:
    """Ten cac placeholder xuat hien trong `body`, giu thu tu, khong trung."""
    ra: list[str] = []
    for ten in _MAU.findall(str(body or "")):
        if ten not in ra:
            ra.append(ten)
    return ra


def _co_gia_tri_that(gia_tri) -> bool:
    """Rong hoac chi khoang trang KHONG phai co gia tri.

    Khach de trong o nhap la ca THAT (mau `Ong Ngoai` co 4 bien tu do). Coi rong
    la co gia tri thi mau render ra cau cut dau roi gui LLM.
    """
    if gia_tri is None:
        return False
    if isinstance(gia_tri, str):
        return bool(gia_tri.strip())
    return True


def kiem_placeholder(body: str, khai_bao: list[str],
                     co_gia_tri: dict) -> list[str]:
    """Ten con THIEU. Rong nghia la mau nay render duoc.

    Ba phep, thieu phep nao cung de lot mot dang loi rieng:
      1. bien DUNG trong body ma khong KHAI  -> khong ai biet de hoi khach;
      2. bien KHAI ma khong ai CAP gia tri   -> render ra `{TEN}` nguyen van;
      3. sau render con cap chu hoa nao       -> luoi cuoi, bat ca hai ca tren.
    """
    khai = list(khai_bao or [])
    dung = tim_placeholder(body)
    thieu: list[str] = [t for t in dung if t not in khai]           # phep 1
    for ten in khai:                                               # phep 2
        if not _co_gia_tri_that(co_gia_tri.get(ten)) and ten not in thieu:
            thieu.append(ten)
    if not thieu:                                                  # phep 3
        for ten in tim_placeholder(render(body, co_gia_tri)):
            if ten not in thieu:
                thieu.append(ten)
    return thieu


def render(body: str, co_gia_tri: dict) -> str:
    """Thay `{TEN}` bang gia tri. Ten khong co gia tri thi GIU NGUYEN.

    ⛔ Giu nguyen chu khong thay bang rong: phep 3 cua `kiem_placeholder` dua vao
       viec ten thieu con hien ra de bat duoc. Thay bang rong la xoa bang chung.
    """
    def _the(m: re.Match) -> str:
        ten = m.group(1)
        gia_tri = co_gia_tri.get(ten)
        return str(gia_tri) if _co_gia_tri_that(gia_tri) else m.group(0)

    return _MAU.sub(_the, str(body or ""))
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5302_placeholders.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/placeholders.py tests/test_5302_placeholders.py
git commit -m "pha3(C1): bang quy doi placeholder va bo kiem ba phep

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C2: T-2 — chạy bộ kiểm trên CẢ 12 bộ placeholder của bản gốc

⭐ Đây là phép **T-2** của spec §10.2. ⛔ Không test mẫu đại diện — test **cả tập**. Bài học `vi-du-trong-loi-nhac-la-menh-lenh-ngam`: sửa theo vài ví dụ làm tụt cái vốn đúng.

**Files:**
- Create: `tests/fixtures/ommi_mau_goc_placeholders.json`
- Test: `tests/test_5303_t2_du_12_mau.py`

**Interfaces:**
- Consumes: `kiem_placeholder`, `NGUON_GIA_TRI` (C1).
- Produces: fixture 12 bộ placeholder; pha 4 sẽ chạy lại phép này trên **nội dung thật** đã nhập.

- [ ] **Step 1: Tạo fixture — đúng 12 bộ đo được từ bản gốc 26/09**

`tests/fixtures/ommi_mau_goc_placeholders.json`:

```json
[
  {"ten": "Anh Thang", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "SCENES", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE", "VIDEO_LIST"]},
  {"ten": "Character reference sheet 4x2", "target_format": "gemini_style",
   "placeholders": ["CHARACTER_DESCRIPTION"]},
  {"ten": "Seedance - video phan canh", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "SCENES", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE"]},
  {"ten": "Storyboard - luoi phan canh (mac dinh)", "target_format": "storyboard",
   "placeholders": ["ASPECT", "PROMPT", "REF_NOTE"]},
  {"ten": "Storyboard - thumbnail nhanh (rough)", "target_format": "storyboard",
   "placeholders": ["ASPECT", "PROMPT", "REF_NOTE"]},
  {"ten": "Storyboard - dien anh chi tiet", "target_format": "storyboard",
   "placeholders": ["ASPECT", "PROMPT", "REF_NOTE"]},
  {"ten": "Ong Ngoai", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "FACTION_A", "FACTION_B", "MIN_COMBAT_DISTANCE",
                    "NEUTRAL_LIST", "PROJECT_NAME", "SCENES", "STYLE_FULL",
                    "STYLE_NEGATIVE", "STYLE_POSITIVE", "TITLE", "VIDEO_LIST"]},
  {"ten": "Flow Omni - Phan canh co timecode", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "SCENES", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE"]},
  {"ten": "Flow Omni - Don canh lien mach", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE"]},
  {"ten": "Seedance - Phan canh co timecode", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "SCENES", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE"]},
  {"ten": "Seedance - Phan canh co timecode + VIDEO", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "SCENES", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE", "VIDEO_LIST"]},
  {"ten": "Seedance - Don canh lien mach", "target_format": "gemini_style",
   "placeholders": ["ASPECT_RATIO", "ASSET_LIST", "BRIEF_VI", "DURATION",
                    "PROJECT_NAME", "STYLE_FULL", "STYLE_NEGATIVE",
                    "STYLE_POSITIVE", "TITLE"]}
]
```

- [ ] **Step 2: Viết test đỏ — cả 12, không mẫu đại diện**

`tests/test_5303_t2_du_12_mau.py`:

```python
"""T-2 (spec §10.2) — bo kiem placeholder chay tren CA 12 mau cua ban goc.

⛔ Khong test mau dai dien. Bai hoc `vi-du-trong-loi-nhac-la-menh-lenh-ngam`:
   sua theo vai vi du lam tut mot cai von dung.

⚠️ Pham vi phep do nay: no do BO PLACEHOLDER (do duoc tu CSDL ban goc 26/09),
   chua do NOI DUNG that cua 12 mau — noi dung duoc nhap o pha 4, va pha 4 PHAI
   chay lai phep nay tren noi dung that.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from apps.prompt_ai_ommi.services.placeholders import (
    NGUON_GIA_TRI, kiem_placeholder)

MAU = json.loads(
    (pathlib.Path(__file__).parent / "fixtures"
     / "ommi_mau_goc_placeholders.json").read_text(encoding="utf-8"))

#: 4 bien TU DO cua mau `Ong Ngoai` — khong co nguon he thong, khach tu nhap.
BIEN_TU_DO = {"FACTION_A", "FACTION_B", "MIN_COMBAT_DISTANCE", "NEUTRAL_LIST"}


def test_fixture_dung_12_mau():
    """Dem cung la mot phep kiem: 12 la so do duoc, khong phai so uoc."""
    assert len(MAU) == 12


def _gia_tri_day_du(placeholders: list[str]) -> dict:
    return {ten: f"<{ten}>" for ten in placeholders}


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_moi_mau_render_duoc_khi_du_gia_tri(mau):
    body = " ".join("{%s}" % ten for ten in mau["placeholders"])
    thieu = kiem_placeholder(body, mau["placeholders"],
                             _gia_tri_day_du(mau["placeholders"]))
    assert thieu == [], f"{mau['ten']} con thieu: {thieu}"


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_moi_placeholder_he_thong_deu_co_nguon(mau):
    """Bien khong phai bien tu do thi PHAI co trong bang nguon gia tri."""
    khong_nguon = [t for t in mau["placeholders"]
                   if t not in NGUON_GIA_TRI and t not in BIEN_TU_DO]
    assert khong_nguon == [], (
        f"{mau['ten']}: bien khong co nguon va khong phai bien tu do: "
        f"{khong_nguon}")


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_thieu_mot_gia_tri_thi_PHAI_bao_thieu(mau):
    """Doi chung: bo mot gia tri di, bo kiem phai bat duoc.

    Khong co phep nay thi `thieu == []` o tren co the chi vi ham luon tra rong
    — bai hoc `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    body = " ".join("{%s}" % ten for ten in mau["placeholders"])
    gia_tri = _gia_tri_day_du(mau["placeholders"])
    bo = mau["placeholders"][0]
    gia_tri.pop(bo)
    assert bo in kiem_placeholder(body, mau["placeholders"], gia_tri)
```

- [ ] **Step 3: Chạy test, phải XANH (C1 đã cài đặt đủ)**

```bash
python -m pytest tests/test_5303_t2_du_12_mau.py -q
```

Đỏ ở `test_moi_placeholder_he_thong_deu_co_nguon` ⇒ `NGUON_GIA_TRI` thiếu tên, bổ sung ở C1.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/ommi_mau_goc_placeholders.json tests/test_5303_t2_du_12_mau.py
git commit -m "pha3(C2): T-2 chay bo kiem placeholder tren ca 12 mau ban goc

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C3: `services/bundle.py` — render meta-prompt KHÔNG gọi LLM (miễn phí)

**Files:**
- Create: `apps/prompt_ai_ommi/services/bundle.py`
- Test: `tests/test_5304_bundle.py`

**Interfaces:**
- Consumes: `placeholders.kiem_placeholder`, `placeholders.render` (C1); `bindings.list_bindings` (pha 1, làn A).
- Produces:
  - `khai_bao_cua(meta) -> list[str]` — đọc khai báo placeholder chịu được cả pha 3 và pha 4 (P-5)
  - `gia_tri_cho(db, brief, *, project_name: str = "") -> dict`
  - `dung_bundle(db, brief, meta, style) -> dict` → `{"rendered", "asset_list", "video_list", "bindings", "missing_placeholders"}`

⭐ **Bundle MIỄN PHÍ** (Q-6): nó chỉ ghép chữ, không gọi LLM. Khách copy đem sang ChatGPT/Gemini riêng cũng được — chủ dự án chốt 26/09 đổi lấy việc khách tin ta dựng prompt thế nào.

- [ ] **Step 1: Viết test đỏ**

`tests/test_5304_bundle.py`:

```python
"""Pha 3 — bundle: render meta-prompt KHONG goi LLM."""
from __future__ import annotations

from types import SimpleNamespace

from apps.prompt_ai_ommi.services.bundle import (
    dung_bundle, khai_bao_cua)


def _meta(body: str, **kw):
    return SimpleNamespace(id="m1", body=body, variables=kw.pop("variables", {}),
                           target_format="gemini_style", **kw)


def test_khai_bao_doc_duoc_o_pha_3_khi_CHUA_co_cot_placeholders():
    """Cot `placeholders` la cua pha 4. Pha 3 phai doc duoc tu `variables`."""
    meta = _meta("{TITLE}", variables={"placeholders": ["TITLE"]})
    assert khai_bao_cua(meta) == ["TITLE"]


def test_khai_bao_uu_tien_cot_thuc_khi_pha_4_da_them():
    meta = _meta("{TITLE}", variables={"placeholders": ["CU"]})
    meta.placeholders = ["TITLE"]
    assert khai_bao_cua(meta) == ["TITLE"]


def test_khai_bao_rong_thi_tra_list_rong_khong_ném_loi():
    assert khai_bao_cua(_meta("{TITLE}")) == []


def test_bundle_bao_thieu_thay_vi_gui_chuoi_hong(db, brief_co_du_lieu):
    """⛔ Thieu gia tri thi KHONG render im lang — phai bao `missing`."""
    meta = _meta("{TITLE} {BIEN_KHONG_CO_NGUON}",
                 variables={"placeholders": ["TITLE", "BIEN_KHONG_CO_NGUON"]})
    ra = dung_bundle(db, brief_co_du_lieu, meta, None)
    assert "BIEN_KHONG_CO_NGUON" in ra["missing_placeholders"]


def test_bundle_du_gia_tri_thi_missing_rong_va_rendered_khong_con_the(
        db, brief_co_du_lieu):
    meta = _meta("Tieu de: {TITLE}. Noi dung: {BRIEF_VI}. {SCENES} canh.",
                 variables={"placeholders": ["TITLE", "BRIEF_VI", "SCENES"]})
    ra = dung_bundle(db, brief_co_du_lieu, meta, None)
    assert ra["missing_placeholders"] == []
    assert "{" not in ra["rendered"] or "{TITLE}" not in ra["rendered"]
    assert brief_co_du_lieu.title in ra["rendered"]


def test_bundle_KHONG_goi_LLM(monkeypatch, db, brief_co_du_lieu):
    """⭐ Doi chung cho viec 'mien phi': neu no goi provider thi no khong mien phi.

    Tiem mot provider no bom — goi la test do.
    """
    from apps.prompt_ai_ommi import provider

    def _no(*a, **k):
        raise AssertionError("bundle KHONG duoc goi LLM")

    monkeypatch.setattr(provider, "generate_json", _no)
    meta = _meta("{TITLE}", variables={"placeholders": ["TITLE"]})
    dung_bundle(db, brief_co_du_lieu, meta, None)
```

⚠️ Fixture `db` và `brief_co_du_lieu`: dùng khuôn fixture CSDL sẵn có của repo. Tìm khuôn đúng bằng:

```bash
grep -rln "def db(" tests/conftest.py tests/*/conftest.py 2>/dev/null; grep -rn "prompt_ai_ommi" tests/conftest.py | head -5
```

Nếu repo chưa có fixture `db` dùng chung, thêm `brief_co_du_lieu` vào `tests/test_5304_bundle.py` dưới dạng fixture cục bộ tạo `OmmiBrief(title="Phim thu", story_vi="x"*40, target_scenes=3, target_duration_sec=15, owner_id="u1")`. ⛔ Không tạo `conftest.py` mới ở gốc `tests/` — đó là tệp dùng chung của mọi phiên.

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5304_bundle.py -q
```

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Bundle — render meta-prompt + danh sach asset, KHONG goi LLM.

⭐ Mien phi (chu du an chot 26/09, Q-6). Khach xem/copy duoc khoi chu ta gui cho
   LLM. Doi lai: khach tin ta dung prompt the nao, va co duong tu lam.

⛔ Tep nay KHONG duoc import `provider`. Mot lan goi LLM o day la mot lan khach
   dung tien cua ta ma khong tra — va `test_bundle_KHONG_goi_LLM` se do.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services import placeholders as ph


def khai_bao_cua(meta) -> list[str]:
    """Danh sach placeholder mau NAY khai.

    Doc duoc o CA hai doi schema: pha 3 chua co cot `placeholders` (no o pha 4),
    nen roi ve `variables["placeholders"]`. ⛔ Dung sua cho goi khi pha 4 them
    cot — `getattr` bat duoc ngay (P-5).
    """
    thuc = getattr(meta, "placeholders", None)
    if thuc:
        return [str(x) for x in thuc]
    bien = getattr(meta, "variables", None) or {}
    return [str(x) for x in (bien.get("placeholders") or [])]


def _dong_asset(bindings, kind: str) -> list[str]:
    """Mot dong mot the, dung the DA LUU trong `ommi_binding`.

    ⛔ Khong tu danh so lai o day: `ommi_binding` la nguon chan ly cua the
       (spec N-2). Danh so hai cho la hai ket qua khac nhau cho cung mot canh.
    """
    return [f"- {b.tag} [{b.kind}] variant={b.variant_id}"
            for b in bindings if b.kind == kind]


def gia_tri_cho(db, brief, *, project_name: str = "", style=None,
                canh=None) -> dict:
    """Gia tri cho tung placeholder he thong (bang spec §7)."""
    from apps.prompt_ai_ommi.services import bindings as bd
    from apps.prompt_ai_ommi.services.composer import style_description

    ds = bd.list_bindings(db, project_id=brief.project_id, owner_id=brief.owner_id) if brief.project_id else []
    mo_ta_style = style_description(getattr(style, "id", "") or "cinematic",
                                   getattr(style, "body", "") or "")
    return {
        "TITLE": brief.title,
        "PROJECT_NAME": project_name,
        "BRIEF_VI": brief.story_vi,
        "DURATION": brief.target_duration_sec,
        "SCENES": brief.target_scenes,
        "ASPECT_RATIO": brief.aspect_ratio,
        "ASPECT": brief.aspect_ratio,
        "STYLE_FULL": mo_ta_style,
        "STYLE_POSITIVE": getattr(style, "body", "") or "",
        "STYLE_NEGATIVE": getattr(style, "negative", "") or "",
        "ASSET_LIST": "\n".join(_dong_asset(ds, "image")),
        "VIDEO_LIST": "\n".join(_dong_asset(ds, "video")),
        "PROMPT": getattr(canh, "prompt", "") or "",
        "REF_NOTE": getattr(canh, "continuity", "") or "",
        "CHARACTER_DESCRIPTION": "",
    }


def dung_bundle(db, brief, meta, style, *, project_name: str = "",
                gia_tri_them: dict | None = None, canh=None) -> dict:
    """Ghep chu. Tra ca `missing_placeholders` — ⛔ KHONG im lang render hong."""
    khai = khai_bao_cua(meta)
    gia_tri = gia_tri_cho(db, brief, project_name=project_name, style=style,
                          canh=canh)
    gia_tri.update(gia_tri_them or {})
    body = getattr(meta, "body", "") or ""
    thieu = ph.kiem_placeholder(body, khai, gia_tri)
    from apps.prompt_ai_ommi.services import bindings as bd
    ds = bd.list_bindings(db, project_id=brief.project_id, owner_id=brief.owner_id) if brief.project_id else []
    return {
        "rendered": ph.render(body, gia_tri),
        "asset_list": _dong_asset(ds, "image"),
        "video_list": _dong_asset(ds, "video"),
        "bindings": [{"tag": b.tag, "kind": b.kind, "variant_id": b.variant_id}
                     for b in ds],
        "missing_placeholders": thieu,
    }
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5304_bundle.py -q
```

- [ ] **Step 5: Khẳng định bằng máy rằng tệp này không import provider**

Thêm vào `tests/test_5304_bundle.py`:

```python
def test_bundle_khong_he_import_provider():
    """Bánh cóc: doc AST, khong cho ai them `import provider` vao tep nay.

    Phep `test_bundle_KHONG_goi_LLM` chi bat duong chay hien tai; phep nay bat
    ca duong chay TUONG LAI ma chua ai viet test cho.
    """
    import ast
    import pathlib

    nguon = pathlib.Path("apps/prompt_ai_ommi/services/bundle.py").read_text(
        encoding="utf-8")
    ten = set()
    for node in ast.walk(ast.parse(nguon)):
        if isinstance(node, ast.Import):
            ten |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            ten.add(node.module or "")
            ten |= {a.name for a in node.names}
    assert not any("provider" in t for t in ten), f"bundle import provider: {ten}"
```

- [ ] **Step 6: Chạy lại rồi commit**

```bash
python -m pytest tests/test_5304_bundle.py -q
git add apps/prompt_ai_ommi/services/bundle.py tests/test_5304_bundle.py
git commit -m "pha3(C3): bundle render meta-prompt khong goi LLM, co banh coc AST

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C4: `services/briefs.py` — CRUD brief + cảnh kịch bản, TÁI DÙNG id cũ

**Files:**
- Create: `apps/prompt_ai_ommi/services/briefs.py`
- Test: `tests/test_5305_briefs.py`

**Interfaces:**
- Produces:
  - `tao_brief(db, owner_id: str, du_lieu: dict) -> OmmiBrief`
  - `doc_brief(db, brief_id: str, owner_id: str) -> OmmiBrief` (ném `KeyError` nếu không thuộc chủ)
  - `liet_ke(db, owner_id: str, *, archived: bool = False, q: str = "") -> list[OmmiBrief]`
  - `sua_brief(db, brief, du_lieu: dict) -> OmmiBrief`
  - `nhan_ban(db, brief) -> OmmiBrief`
  - `dat_canh(db, brief, canh: list[dict]) -> list[OmmiCanh]` — ⭐ **giữ `id` truyền vào** (S-4)
  - `doc_canh(db, brief) -> list[OmmiCanh]`
  - `preflight(brief) -> dict` → `{"checklist": [...], "passed": bool}`

- [ ] **Step 1: Viết test đỏ — trọng tâm là S-4**

`tests/test_5305_briefs.py`:

```python
"""Pha 3 — brief va canh kich ban. Trong tam: id canh phai TAI DUNG duoc."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import briefs as bf


def test_tao_va_doc_brief(db):
    b = bf.tao_brief(db, "u1", {"title": "Phim thu", "story_vi": "x" * 40})
    db.flush()
    assert bf.doc_brief(db, b.id, "u1").title == "Phim thu"


def test_doc_brief_cua_nguoi_khac_bi_tu_choi(db):
    b = bf.tao_brief(db, "u1", {"title": "Phim thu", "story_vi": "x" * 40})
    db.flush()
    with pytest.raises(KeyError):
        bf.doc_brief(db, b.id, "u2")


def test_dat_canh_GIU_NGUYEN_id_truyen_vao(db):
    """⭐ S-4: binding cua pha 1 tro vao id canh cu.

    Sinh id moi o day nghia la MOI binding pha 1 tro vao hu khong — anh tham
    chieu mat sach, dung con bo N-1 ma ca spec nay dang chua.
    """
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [
        {"id": "scene_abc123", "title": "Canh 1", "prompt": "p1"},
        {"id": "scene_def456", "title": "Canh 2", "prompt": "p2"},
    ])
    db.flush()
    assert [c.id for c in canh] == ["scene_abc123", "scene_def456"]


def test_dat_canh_khong_co_id_thi_tu_sinh(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": "Canh 1", "prompt": "p"}])
    db.flush()
    assert canh[0].id and len(canh[0].id) >= 8


def test_dat_canh_danh_lai_vi_tri_lien_tuc_tu_0(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": f"C{i}"} for i in range(4)])
    db.flush()
    assert [c.position for c in canh] == [0, 1, 2, 3]


def test_dat_canh_lan_hai_THAY_canh_cu_khong_cong_don(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    bf.dat_canh(db, b, [{"title": "C0"}, {"title": "C1"}])
    db.flush()
    bf.dat_canh(db, b, [{"title": "Moi"}])
    db.flush()
    con_lai = bf.doc_canh(db, b)
    assert len(con_lai) == 1 and con_lai[0].title == "Moi"


def test_preflight_bat_brief_thieu(db):
    b = bf.tao_brief(db, "u1", {"title": "", "story_vi": "ngan"})
    ra = bf.preflight(b)
    assert ra["passed"] is False
    that_bai = {c["id"] for c in ra["checklist"] if not c["passed"]}
    assert {"title", "story"} <= that_bai


def test_preflight_KHONG_goi_LLM_va_khong_ghi_CSDL(db):
    """Preflight mien phi ⇒ khong duoc lam gi ton tien hay doi trang thai."""
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    truoc = b.updated_at
    bf.preflight(b)
    assert b.updated_at == truoc


def test_nhan_ban_khong_keo_theo_so_dem_luot_mien_phi(db):
    """⭐ Neu nhan ban reset bo dem thi khach nhan ban de co 2 luot free nua.

    Ban sao la mot kich ban MOI ⇒ dung 0 la DUNG; nhung phai co phep kiem noi ro
    day la quyet dinh, khong phai tinh co.
    """
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    b.free_iterations_used = 2
    db.flush()
    ban_sao = bf.nhan_ban(db, b)
    db.flush()
    assert ban_sao.free_iterations_used == 0
    assert ban_sao.id != b.id
```

⚠️ Phép cuối cùng ghi lại một **rủi ro sản phẩm đã biết**: nhân bản brief là đường lách 2 lượt miễn phí. Plan chọn `0` cho bản sao (đúng nghĩa "kịch bản mới"). Nếu đo được khách lạm dụng, chỗ sửa là **một dòng** trong `nhan_ban`. ⛔ Đừng âm thầm đổi — ghi vào `docs/NHAT_KY.md`.

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5305_briefs.py -q
```

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Brief va canh kich ban.

⭐ Canh kich ban nam o day, khong o `services/canh.py` rieng: canh THUOC VE
   brief, tach ra la chia mot thuc the cho hai chu (P-8). Neu tep nay phinh qua
   ~400 dong thi tach o pha 4, van mot chu.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select

from apps.prompt_ai_ommi.tables import OmmiBrief, OmmiCanh

MAX_CANH = 20
_SO_CANH = (1, 20)
_THOI_LUONG = (3, 600)


def _id_moi(tien_to: str) -> str:
    return f"{tien_to}_{uuid.uuid4().hex[:12]}"


def tao_brief(db, owner_id: str, du_lieu: dict) -> OmmiBrief:
    b = OmmiBrief(owner_id=owner_id, title=str(du_lieu.get("title") or "")[:200])
    return sua_brief(db, b, du_lieu, _them=True)


def sua_brief(db, brief: OmmiBrief, du_lieu: dict, *,
              _them: bool = False) -> OmmiBrief:
    if "title" in du_lieu:
        brief.title = str(du_lieu["title"] or "")[:200]
    if "story_vi" in du_lieu:
        brief.story_vi = str(du_lieu["story_vi"] or "")
    for ten, gioi_han in (("goal", 300), ("audience", 300)):
        if ten in du_lieu:
            setattr(brief, ten, str(du_lieu[ten] or "")[:gioi_han])
    if "target_scenes" in du_lieu:
        brief.target_scenes = max(_SO_CANH[0], min(
            _SO_CANH[1], int(du_lieu["target_scenes"] or 3)))
    if "target_duration_sec" in du_lieu:
        brief.target_duration_sec = max(_THOI_LUONG[0], min(
            _THOI_LUONG[1], int(du_lieu["target_duration_sec"] or 15)))
    for ten in ("aspect_ratio", "language", "style_id", "meta_prompt_id",
                "character_id", "background_id", "project_id"):
        if ten in du_lieu:
            setattr(brief, ten, du_lieu[ten] or None
                    if ten.endswith("_id") else str(du_lieu[ten] or ""))
    if "referenced_variants" in du_lieu:
        brief.referenced_variants = [
            str(x) for x in list(du_lieu["referenced_variants"] or [])[:60]]
    if _them:
        db.add(brief)
    return brief


def doc_brief(db, brief_id: str, owner_id: str) -> OmmiBrief:
    """⛔ Tra `KeyError` chung cho ca "khong ton tai" va "khong phai cua anh".

    Phan biet hai ca nay la mot ro ri: ke goi biet duoc id nao TON TAI.
    """
    b = db.get(OmmiBrief, str(brief_id or ""))
    if b is None or b.owner_id != owner_id:
        raise KeyError(brief_id)
    return b


def liet_ke(db, owner_id: str, *, archived: bool = False,
            q: str = "") -> list[OmmiBrief]:
    cau = select(OmmiBrief).where(OmmiBrief.owner_id == owner_id)
    cau = cau.where(OmmiBrief.archived_at.is_not(None) if archived
                    else OmmiBrief.archived_at.is_(None))
    if str(q or "").strip():
        cau = cau.where(OmmiBrief.title.ilike(f"%{q.strip()}%"))
    return list(db.execute(cau.order_by(OmmiBrief.updated_at.desc())).scalars())


def nhan_ban(db, brief: OmmiBrief) -> OmmiBrief:
    """Ban sao la mot kich ban MOI ⇒ so dem luot mien phi ve 0.

    ⚠️ Day la duong lach 2 luot mien phi neu khach nhan ban lien tuc. Do duoc
       lam dung thi sua MOT dong o day (mang theo so dem cua ban goc).
    """
    ban_sao = OmmiBrief(
        owner_id=brief.owner_id, project_id=brief.project_id,
        title=f"{brief.title} (ban sao)"[:200], story_vi=brief.story_vi,
        goal=brief.goal, audience=brief.audience,
        target_duration_sec=brief.target_duration_sec,
        target_scenes=brief.target_scenes, aspect_ratio=brief.aspect_ratio,
        language=brief.language, style_id=brief.style_id,
        meta_prompt_id=brief.meta_prompt_id, character_id=brief.character_id,
        background_id=brief.background_id,
        referenced_variants=list(brief.referenced_variants or []),
        status="draft", free_iterations_used=0)
    db.add(ban_sao)
    for c in doc_canh(db, brief):
        db.add(OmmiCanh(
            brief_id=ban_sao.id, position=c.position, title=c.title,
            duration_seconds=c.duration_seconds, summary=c.summary,
            prompt=c.prompt, negative_prompt=c.negative_prompt,
            camera=c.camera, lighting=c.lighting, mood=c.mood,
            continuity=c.continuity))
    return ban_sao


def doc_canh(db, brief: OmmiBrief) -> list[OmmiCanh]:
    return list(db.execute(
        select(OmmiCanh).where(OmmiCanh.brief_id == brief.id)
        .order_by(OmmiCanh.position)).scalars())


def dat_canh(db, brief: OmmiBrief, canh: list[dict]) -> list[OmmiCanh]:
    """THAY toan bo canh cua brief. ⭐ GIU NGUYEN `id` neu duoc truyen vao.

    Vi sao giu id (spec S-4): `ommi_binding.scene_id` cua pha 1 tro vao id canh
    trong `AppProject.payload`. Pha 3 chuyen canh sang bang nay; sinh id moi
    nghia la MOI binding tro vao hu khong va anh tham chieu mat sach.
    """
    db.execute(delete(OmmiCanh).where(OmmiCanh.brief_id == brief.id))
    ra: list[OmmiCanh] = []
    for vi_tri, item in enumerate(list(canh or [])[:MAX_CANH]):
        item = item if isinstance(item, dict) else {}
        row = OmmiCanh(
            id=str(item.get("id") or "").strip() or _id_moi("scene"),
            brief_id=brief.id, position=vi_tri,
            title=str(item.get("title") or "")[:200],
            duration_seconds=max(1, min(60, int(item.get("duration_seconds") or 5))),
            summary=str(item.get("summary") or ""),
            prompt=str(item.get("prompt") or ""),
            negative_prompt=str(item.get("negative_prompt") or ""),
            camera=str(item.get("camera") or ""),
            lighting=str(item.get("lighting") or ""),
            mood=str(item.get("mood") or ""),
            continuity=str(item.get("continuity") or ""),
            selected_version=max(0, int(item.get("selected_version") or 0)))
        db.add(row)
        ra.append(row)
    return ra


def preflight(brief: OmmiBrief) -> dict:
    """Kiem brief truoc khi goi LLM. MIEN PHI ⇒ ⛔ khong ghi CSDL, khong goi LLM."""
    muc = [
        {"id": "title", "label": "Ten kich ban", "passed": bool(brief.title.strip())},
        {"id": "story", "label": "Noi dung toi thieu 20 ky tu",
         "passed": len(str(brief.story_vi or "").strip()) >= 20},
        {"id": "scene_count", "label": f"So canh {_SO_CANH[0]}-{_SO_CANH[1]}",
         "passed": _SO_CANH[0] <= brief.target_scenes <= _SO_CANH[1]},
        {"id": "duration", "label": f"Thoi luong {_THOI_LUONG[0]}-{_THOI_LUONG[1]} giay",
         "passed": _THOI_LUONG[0] <= brief.target_duration_sec <= _THOI_LUONG[1]},
    ]
    return {"checklist": muc, "passed": all(m["passed"] for m in muc)}
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5305_briefs.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/briefs.py tests/test_5305_briefs.py
git commit -m "pha3(C4): brief va canh kich ban, giu nguyen id canh cho binding pha 1

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C5: Binding của pha 1 sống sót qua pha 3 — phép kiểm cầu nối

⭐ Đây là phép kiểm **quan trọng nhất** của làn C. Nó là đối chứng cho S-4.

**Files:**
- Test: `tests/test_5308_binding_song_sot.py`

**Interfaces:**
- Consumes: `bindings.replace_bindings`, `bindings.list_bindings`, `bool(bindings.list_bindings(...))` (pha 1); `briefs.dat_canh` (C4).

- [ ] **Step 1: Viết test đỏ**

```python
"""S-4 — binding pha 1 phai song sot khi canh chuyen tu payload sang `ommi_canh`.

Neu phep nay do, nghia la moi anh tham chieu khach da gan o pha 1/2 tro thanh
hu khong ngay khi pha 3 len production. Khong ai bao loi vi chang ai xem lai
prompt cu — dung dang loi `cho-noi-hai-module-vut-truong-im-lang`.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services import bindings as bd
from apps.prompt_ai_ommi.services import briefs as bf

ID_CANH_CU = "scene_9f1c2ab30de4"


def test_binding_tro_vao_id_canh_cu_van_tim_ra_canh_sau_pha_3(db, du_an, variant):
    # Pha 1/2: canh nam trong payload, binding tro vao id do.
    bd.replace_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                        scene_id=ID_CANH_CU,
                        items=[{"kind": "image", "variant_id": variant.id}])
    db.flush()

    # Pha 3: chuyen canh sang bang, TAI DUNG dung id cu.
    b = bf.tao_brief(db, du_an.user_id,
                     {"title": "T", "story_vi": "x" * 40, "project_id": du_an.id})
    db.flush()
    bf.dat_canh(db, b, [{"id": ID_CANH_CU, "title": "Canh 1", "prompt": "p"}])
    db.flush()

    canh = bf.doc_canh(db, b)
    assert canh[0].id == ID_CANH_CU
    ds = bd.list_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                     scene_id=ID_CANH_CU)
    assert len(ds) == 1 and ds[0].variant_id == variant.id
    assert bool(bd.list_bindings(db, project_id=du_an.id,
                                 owner_id=du_an.user_id,
                                 scene_id=ID_CANH_CU)) is True


def test_doi_chung_sinh_id_moi_thi_binding_MAT(db, du_an, variant):
    """Tiem loi: neu `dat_canh` sinh id moi thi binding khong con tro vao dau.

    Khong co phep doi chung nay thi phep tren co the xanh chi vi `list_bindings`
    luon tra rong — `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    bd.replace_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                        scene_id=ID_CANH_CU,
                        items=[{"kind": "image", "variant_id": variant.id}])
    db.flush()
    b = bf.tao_brief(db, du_an.user_id,
                     {"title": "T", "story_vi": "x" * 40, "project_id": du_an.id})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": "Canh 1"}])   # ⛔ KHONG truyen id
    db.flush()
    assert canh[0].id != ID_CANH_CU
    assert bd.list_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                            scene_id=canh[0].id) == []
```

- [ ] **Step 2: Chạy, XANH (C4 đã làm đúng) hoặc ĐỎ nếu `dat_canh` sinh id mới**

```bash
python -m pytest tests/test_5308_binding_song_sot.py -q
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_5308_binding_song_sot.py
git commit -m "pha3(C5): phep kiem cau noi — binding pha 1 song sot qua pha 3

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C6: Chi tiết `camera`/`lighting`/`mood` phải vào `prompt`, ⛔ không bị bỏ

**Files:**
- Modify: `apps/prompt_ai_ommi/services/briefs.py` (thêm hàm `prompt_day_du`)
- Test: `tests/test_5309_chi_tiet_khong_bi_bo.py`

**Interfaces:**
- Produces: `prompt_day_du(canh: OmmiCanh) -> str`

⭐ Spec §6.2b: `taovideo` khai `camera`/`motion`/`visual_style` là **enum ĐÓNG**. Chi tiết chữ tự do của Director **phải** đi vào `prompt`; enum chỉ là gợi ý thô, và việc suy ra enum là của **pha 2**.

- [ ] **Step 1: Viết test đỏ**

```python
"""§6.2b — chi tiet camera/lighting/mood PHAI vao prompt, ⛔ khong bi bo.

Con bo nay dang o `routes/handoff.py:44`: ghi de cung `motion="cinematic"` roi
bo `scene.camera`. Sua N-1 bang cach chi khop enum roi bo chu goc la VUT TRUONG
IM LANG LAN THU HAI.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.briefs import prompt_day_du
from apps.prompt_ai_ommi.tables import OmmiCanh

CHI_TIET = "medium shot, 35mm, slow push in"


def test_camera_chu_tu_do_nam_NGUYEN_VAN_trong_prompt():
    c = OmmiCanh(brief_id="b", prompt="Nhan vat buoc vao phong",
                 camera=CHI_TIET, lighting="golden hour, rim light",
                 mood="tram lang")
    ra = prompt_day_du(c)
    assert CHI_TIET in ra
    assert "golden hour, rim light" in ra
    assert "tram lang" in ra
    assert "Nhan vat buoc vao phong" in ra


def test_truong_rong_thi_khong_them_nhan_trong():
    c = OmmiCanh(brief_id="b", prompt="P", camera="", lighting="", mood="")
    assert prompt_day_du(c).strip() == "P"


def test_chi_mot_truong_co_thi_chi_them_nhan_do():
    c = OmmiCanh(brief_id="b", prompt="P", camera=CHI_TIET, lighting="", mood="")
    ra = prompt_day_du(c)
    assert "Camera:" in ra and "Lighting:" not in ra and "Mood:" not in ra


def test_tat_dinh_goi_hai_lan_ra_cung_mot_chuoi():
    """⚠️ `camera` nam trong `idempotency.key_fields` cua taovideo.

    Khong tat dinh thi hai lan giao bai cung mot canh tach doi job dedupe.
    """
    c = OmmiCanh(brief_id="b", prompt="P", camera=CHI_TIET,
                 lighting="L", mood="M")
    assert prompt_day_du(c) == prompt_day_du(c)
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5309_chi_tiet_khong_bi_bo.py -q
```

- [ ] **Step 3: Thêm hàm vào `services/briefs.py`**

```python
def prompt_day_du(canh) -> str:
    """Prompt cua canh + chi tiet camera/lighting/mood GHEP NGUYEN VAN.

    ⭐ `taovideo` khai `camera`/`motion`/`visual_style` la enum DONG
       (`apps/taovideo/manifest.py:196-198`), ma Director sinh chu tu do giau chi
       tiet. Cho thong tin THAT song la `prompt` (chu tu do, 10 000 ky tu); enum
       chi la goi y tho, va viec suy ra enum la cua pha 2 (spec §6.2b).

    ⛔ Chi khop enum roi BO chu goc = vut truong im lang lan thu hai.
    ⭐ Tat dinh: thu tu nhan co dinh, khong duyet `dict`.
    """
    phan = [str(getattr(canh, "prompt", "") or "").strip()]
    for nhan, ten in (("Camera", "camera"), ("Lighting", "lighting"),
                      ("Mood", "mood")):
        gia_tri = str(getattr(canh, ten, "") or "").strip()
        if gia_tri:
            phan.append(f"{nhan}: {gia_tri}.")
    return " ".join(p for p in phan if p)
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5309_chi_tiet_khong_bi_bo.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/briefs.py tests/test_5309_chi_tiet_khong_bi_bo.py
git commit -m "pha3(C6): chi tiet camera/lighting/mood ghep nguyen van vao prompt

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task C7: `routes/briefs.py` — endpoint spec §6.4 (phần của làn C)

**Files:**
- Create: `apps/prompt_ai_ommi/routes/briefs.py`
- Test: `tests/test_5310_routes_briefs.py`

**Interfaces:**
- Consumes: `briefs.*` (C4), `bundle.dung_bundle` (C3), `_shared.router/_csrf/_user/require_login/get_db/_require_run_enabled`.
- Produces: `GET/POST /api/briefs`, `GET/PUT/DELETE /api/briefs/{bid}`, `POST /api/briefs/{bid}/clone`, `POST /api/briefs/{bid}/preflight`, `POST /api/briefs/{bid}/bundle`, `POST /api/briefs/{bid}/quote`.

⛔ `POST /api/briefs/{bid}/generate` và `/iterations/*` **KHÔNG** ở đây — chúng là của **làn D** (Task D2). Hai làn không sửa cùng tệp.

- [ ] **Step 1: Viết test đỏ — trọng tâm: preflight/bundle KHÔNG cần `_require_run_enabled`**

```python
"""Pha 3 — routes brief. Trong tam: cai gi MIEN PHI thi khong bi rollout chan.

⚠️ `_run_mode()` mac dinh "off" tren production (do 26/09). Neu `preflight` va
   `bundle` cung goi `_require_run_enabled` thi khach vao trang thay 503 ngay o
   buoc mien phi — va se ket luan app hong.
"""
from __future__ import annotations

import inspect


def test_preflight_va_bundle_KHONG_goi_require_run_enabled():
    from apps.prompt_ai_ommi.routes import briefs as r
    for ten in ("preflight", "bundle"):
        ham = getattr(r, ten)
        assert "_require_run_enabled" not in inspect.getsource(ham), (
            f"{ten} la buoc MIEN PHI, ⛔ khong duoc chan boi rollout")


def test_quote_va_cac_buoc_ton_tien_CO_goi_require_run_enabled():
    from apps.prompt_ai_ommi.routes import briefs as r
    assert "_require_run_enabled" in inspect.getsource(r.quote)


def test_moi_endpoint_ghi_du_lieu_deu_kiem_csrf():
    """Banh coc: mot route POST/PUT/DELETE thieu `_csrf` la mot lo CSRF."""
    from apps.prompt_ai_ommi.routes import briefs as r
    for ten in ("tao", "sua", "xoa", "nhan_ban", "preflight", "bundle", "quote"):
        nguon = inspect.getsource(getattr(r, ten))
        assert "_csrf(" in nguon, f"{ten} thieu _csrf"
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5310_routes_briefs.py -q
```

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Brief va canh kich ban — be mat web.

⚠️ `preflight` va `bundle` la buoc MIEN PHI (Q-6) ⇒ ⛔ KHONG goi
   `_require_run_enabled`. Goi no nghia la khach gap 503 ngay o buoc khong ton
   tien, va se ket luan app hong.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _require_run_enabled, _user, get_db, require_login, router)
from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services.bundle import dung_bundle


def _ra(b) -> dict:
    return {"id": b.id, "title": b.title, "story_vi": b.story_vi,
            "goal": b.goal, "audience": b.audience,
            "target_duration_sec": b.target_duration_sec,
            "target_scenes": b.target_scenes, "aspect_ratio": b.aspect_ratio,
            "language": b.language, "style_id": b.style_id,
            "meta_prompt_id": b.meta_prompt_id,
            "character_id": b.character_id, "background_id": b.background_id,
            "status": b.status,
            "free_iterations_used": b.free_iterations_used,
            "project_id": b.project_id,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None}


def _lay(db, bid: str, user):
    try:
        return bf.doc_brief(db, bid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy brief.'))


@router.get("/api/briefs")
def liet_ke(request: Request, archived: bool = False, q: str = "",
            _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    user = _user(request)
    rows = bf.liet_ke(db, user.id, archived=archived, q=q)
    return {"briefs": [_ra(b) for b in rows], "total": len(rows)}


@router.post("/api/briefs", status_code=201)
async def tao(request: Request, _identity: str = Depends(require_login),
              db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    b = bf.tao_brief(db, user.id, body); db.commit()
    return {"brief": _ra(b)}


@router.get("/api/briefs/{bid}")
def doc(request: Request, bid: str, _identity: str = Depends(require_login),
        db: Session = Depends(get_db)):
    b = _lay(db, bid, _user(request))
    return {"brief": _ra(b),
            "canh": [{"id": c.id, "position": c.position, "title": c.title,
                      "prompt": c.prompt, "camera": c.camera,
                      "lighting": c.lighting, "mood": c.mood,
                      "duration_seconds": c.duration_seconds}
                     for c in bf.doc_canh(db, b)]}


@router.put("/api/briefs/{bid}")
async def sua(request: Request, bid: str,
              _identity: str = Depends(require_login),
              db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    bf.sua_brief(db, b, body)
    if isinstance(body.get("canh"), list):
        bf.dat_canh(db, b, body["canh"])
    db.commit()
    return {"brief": _ra(b)}


@router.delete("/api/briefs/{bid}")
async def xoa(request: Request, bid: str,
              _identity: str = Depends(require_login),
              db: Session = Depends(get_db)):
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — DELETE thuong khong co body
        body = {}
    _csrf(request, body)
    b = _lay(db, bid, _user(request))
    from datetime import datetime, timezone
    b.archived_at = datetime.now(timezone.utc); db.commit()
    return {"brief": _ra(b)}


@router.post("/api/briefs/{bid}/clone", status_code=201)
async def nhan_ban(request: Request, bid: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    ban_sao = bf.nhan_ban(db, b); db.commit()
    return {"brief": _ra(ban_sao)}


@router.post("/api/briefs/{bid}/preflight")
async def preflight(request: Request, bid: str,
                    _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    """MIEN PHI ⇒ ⛔ khong `_require_run_enabled`, khong ghi CSDL."""
    body = await request.json(); _csrf(request, body)
    return bf.preflight(_lay(db, bid, _user(request)))


@router.post("/api/briefs/{bid}/bundle")
async def bundle(request: Request, bid: str,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    """MIEN PHI (Q-6) ⇒ ⛔ khong `_require_run_enabled`."""
    body = await request.json(); _csrf(request, body)
    b = _lay(db, bid, _user(request))
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt, OmmiStyle
    meta_id = str(body.get("meta_prompt_id") or b.meta_prompt_id or "")
    meta = db.get(OmmiMetaPrompt, meta_id) if meta_id else None
    if meta is None:
        raise HTTPException(status_code=422,
                            detail=_t('Chưa chọn prompt meta.'))
    style = db.get(OmmiStyle, b.style_id) if b.style_id else None
    return dung_bundle(db, b, meta, style)


@router.post("/api/briefs/{bid}/quote")
async def quote(request: Request, bid: str,
                _identity: str = Depends(require_login),
                db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    b = _lay(db, bid, user)
    from platform_core.registry import credit_for
    gia = credit_for("prompt_ai_ommi.generate",
                     {"operation": "director", "scene_count": b.target_scenes})
    con_free = max(0, 2 - int(b.free_iterations_used or 0))
    return {"credit": gia, "free_left": con_free, "authoritative": True}
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5310_routes_briefs.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/routes/briefs.py tests/test_5310_routes_briefs.py
git commit -m "pha3(C7): endpoint brief — preflight va bundle mien phi khong bi rollout chan

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# LÀN D — vòng lặp iterate và luật tiền

## Task D1: `services/iterate.py` — 2 lượt đầu miễn phí, bộ đếm trong CSDL

**Files:**
- Create: `apps/prompt_ai_ommi/services/iterate.py`
- Test: `tests/test_5320_iterate.py`

**Interfaces:**
- Consumes: `briefs.doc_brief`, `briefs.doc_canh`, `bundle.dung_bundle` (C3/C4); `platform_core.job_submit.submit_with_credit`; `platform_core.registry.credit_for`.
- Produces:
  - `LUOT_MIEN_PHI: int = 2`
  - `con_mien_phi(brief) -> int`
  - `bao_gia(db, brief) -> dict` → `{"credit": int, "was_free": bool, "free_left": int}`
  - `mo_luot(db, brief, feedback: str, prompt_sent: str) -> OmmiIteration` — tạo iteration **và** tăng bộ đếm trong **cùng** transaction
  - `dat_phan_quyet(db, iteration, verdict: str) -> OmmiIteration`
  - `chay_iterate(params: dict, ctx=None) -> dict` — thân job, gọi từ `jobs.handle`

⭐ **Luật tiền (Q-7/H-7)**: `free_iterations_used < 2` ⇒ credit 0, `was_free=True`, **tăng bộ đếm cùng transaction** với việc tạo `OmmiIteration`. Lượt 3 trở đi qua `submit_with_credit`.
⛔ `verdict="rejected"` **không hoàn credit** — hoàn thì khách bấm rejected mọi lần là LLM miễn phí vô hạn.

- [ ] **Step 1: Viết test đỏ — T-3 của spec §10.2, gồm phép "đóng rồi mở lại session"**

`tests/test_5320_iterate.py`:

```python
"""T-3 (spec §10.2) — 2 luot dau mien phi, bo dem nam trong CSDL.

⭐ Phep quyet dinh la `test_bo_dem_song_qua_mot_session_moi`: bo dem trong phien
   nghia la khach mo tab moi la co 2 luot mien phi nua — LLM mien phi vo han.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services import iterate as it


@pytest.fixture()
def brief(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.commit()
    return b


def test_hai_luot_dau_mien_phi(db, brief):
    assert it.bao_gia(db, brief)["was_free"] is True
    it.mo_luot(db, brief, "sua canh 1", "prompt"); db.commit()
    assert it.bao_gia(db, brief)["was_free"] is True
    it.mo_luot(db, brief, "sua canh 2", "prompt"); db.commit()
    assert it.bao_gia(db, brief)["was_free"] is False


def test_luot_thu_ba_thu_tien_duong(db, brief):
    for i in range(2):
        it.mo_luot(db, brief, f"f{i}", "p")
    db.commit()
    gia = it.bao_gia(db, brief)
    assert gia["was_free"] is False and gia["credit"] > 0


def test_con_mien_phi_dem_dung_va_khong_bao_gio_am(db, brief):
    assert it.con_mien_phi(brief) == 2
    brief.free_iterations_used = 5
    assert it.con_mien_phi(brief) == 0


def test_bo_dem_tang_CUNG_transaction_voi_iteration(db, brief):
    """Neu hai viec khong cung transaction, mot lan crash giua chung se tao
    iteration ma khong tinh luot — hoac tinh luot ma khong co iteration.
    """
    it.mo_luot(db, brief, "f", "p")
    # Chua commit: ca hai thay doi phai cung nam trong session dang mo.
    assert brief.free_iterations_used == 1
    assert len(db.new) >= 1
    db.rollback()
    assert brief.free_iterations_used == 0


def test_bo_dem_song_qua_mot_session_moi(db_factory):
    """⭐ Phep quyet dinh cua T-3. Dong session, mo session MOI, van phai thu tien."""
    with db_factory() as db1:
        b = bf.tao_brief(db1, "u1", {"title": "T", "story_vi": "x" * 40})
        db1.commit()
        bid = b.id
        it.mo_luot(db1, b, "f1", "p"); it.mo_luot(db1, b, "f2", "p")
        db1.commit()

    with db_factory() as db2:
        b2 = bf.doc_brief(db2, bid, "u1")
        assert b2.free_iterations_used == 2
        assert it.bao_gia(db2, b2)["was_free"] is False


def test_seq_tang_lien_tuc_tu_1(db, brief):
    a = it.mo_luot(db, brief, "f1", "p")
    bb = it.mo_luot(db, brief, "f2", "p")
    db.commit()
    assert (a.seq, bb.seq) == (1, 2)


def test_phan_quyet_rejected_KHONG_hoan_credit(db, brief):
    """⛔ Hoan thi khach bam rejected moi lan la LLM mien phi vo han."""
    lt = it.mo_luot(db, brief, "f", "p")
    lt.credit_charged = 5
    db.commit()
    it.dat_phan_quyet(db, lt, "rejected"); db.commit()
    assert lt.verdict == "rejected"
    assert lt.credit_charged == 5      # ⛔ khong ve 0


def test_phan_quyet_chi_nhan_hai_gia_tri(db, brief):
    lt = it.mo_luot(db, brief, "f", "p"); db.commit()
    with pytest.raises(ValueError):
        it.dat_phan_quyet(db, lt, "maybe")
```

⚠️ Fixture `db_factory`: một hàm trả context manager mở **session mới**. Nếu repo chưa có, thêm fixture cục bộ trong tệp test này dựa trên engine mà fixture `db` đang dùng. ⛔ Không sửa `tests/conftest.py` gốc — tệp dùng chung của mọi phiên.

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5320_iterate.py -q
```

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Vong lap sua kich ban, va luat tien cua no.

⭐ LUAT TIEN (chu du an chot 26/09, Q-7): 2 luot dau moi KICH BAN mien phi, luot
   3 tro di thu credit. Dem theo KICH BAN — khong theo user, khong theo ngay.

⛔ BO DEM PHAI NAM TRONG CSDL. Bo dem trong phien nghia la khach mo tab moi la
   duoc 2 luot mien phi nua, tuc LLM mien phi vo han. Day khong phai lo hong ly
   thuyet: no la duong lach re nhat ma bat ky khach nao cung tim ra.

⛔ `verdict="rejected"` KHONG hoan credit. Hoan thi khach bam rejected moi lan
   cung dat duoc dieu tren.
"""
from __future__ import annotations

from sqlalchemy import func, select

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.tables import OmmiIteration

#: So luot dau mien phi MOI KICH BAN. Doi so nay la doi gia san pham ⇒ hoi chu
#: du an truoc, va ghi vao `docs/NHAT_KY.md`.
LUOT_MIEN_PHI = 2

_PHAN_QUYET = {"kept", "rejected"}


def con_mien_phi(brief) -> int:
    """So luot mien phi con lai. Khong bao gio am."""
    return max(0, LUOT_MIEN_PHI - int(getattr(brief, "free_iterations_used", 0) or 0))


def bao_gia(db, brief) -> dict:
    """Gia cho luot TIEP THEO. `authoritative` de frontend khong tu tinh lai."""
    from platform_core.registry import credit_for

    free = con_mien_phi(brief) > 0
    gia = 0 if free else credit_for(
        "prompt_ai_ommi.generate",
        {"operation": "iterate", "scene_count": int(brief.target_scenes or 6)})
    return {"credit": gia, "was_free": free, "free_left": con_mien_phi(brief),
            "authoritative": True}


def _seq_ke_tiep(db, brief_id: str) -> int:
    lon_nhat = db.execute(
        select(func.max(OmmiIteration.seq))
        .where(OmmiIteration.brief_id == brief_id)).scalar()
    return int(lon_nhat or 0) + 1


def mo_luot(db, brief, feedback: str, prompt_sent: str) -> OmmiIteration:
    """Tao mot luot VA tang bo dem — trong CUNG mot transaction.

    ⛔ Hai viec nay khong duoc tach: mot lan crash giua chung de lai hoac mot
       iteration khong tinh luot (khach duoc them mot luot free), hoac mot luot
       da tinh ma khong co iteration (khach mat mot luot free khong co gi doi lai).
       Caller tu `commit`.
    """
    free = con_mien_phi(brief) > 0
    gia = bao_gia(db, brief)
    lt = OmmiIteration(
        brief_id=brief.id, seq=_seq_ke_tiep(db, brief.id),
        feedback=str(feedback or "")[:4000],
        prompt_sent=str(prompt_sent or "")[:60000],
        credit_charged=0 if free else int(gia["credit"]), was_free=free)
    db.add(lt)
    if free:
        brief.free_iterations_used = int(brief.free_iterations_used or 0) + 1
    return lt


def dat_phan_quyet(db, iteration, verdict: str):
    """`kept` | `rejected`. ⛔ KHONG hoan credit trong ca hai ca."""
    v = str(verdict or "").strip().lower()
    if v not in _PHAN_QUYET:
        raise ValueError(_t('Phán quyết không hợp lệ.'))
    iteration.verdict = v
    return iteration


def chay_iterate(params: dict, ctx=None) -> dict:
    """Than job cho `operation="iterate"`. Goi tu `jobs.handle` (P-4).

    ⛔ PHAI nem exception khi loi — nen tang dua vao exception de hoan credit
       (G-9). Tra ve em ru la "thanh cong" gia va mat tien hoan cua khach.
    """
    from apps.prompt_ai_ommi import provider
    from apps.prompt_ai_ommi.services.composer import director_prompt

    feedback = str(params.get("feedback") or "").strip()
    if not feedback:
        raise ValueError(_t('Cần nội dung góp ý để sửa kịch bản.'))
    story = str(params.get("story") or "").strip()
    if len(story) < 20:
        raise ValueError(_t('Nội dung brief tối thiểu 20 ký tự.'))
    if ctx is not None:
        ctx.progress(15, "đang ghép góp ý vào brief")
    # Gop y di vao brief thay vi mot he thong prompt rieng: mot duong, mot cho sua.
    params = dict(params)
    params["story"] = f"{story}\n\n[GOP Y CAN SUA]\n{feedback}"
    system, prompt = director_prompt(params)
    if ctx is not None:
        ctx.progress(40, "AI Director đang sửa kịch bản")
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(system, prompt, model=model)
    if ctx is not None:
        ctx.progress(90, "đang chuẩn hóa kết quả")
    from apps.prompt_ai_ommi.jobs import _normalize_result
    from apps.prompt_ai_ommi.manifest import _cost
    ket_qua = {
        "operation": "iterate",
        "prompt_package": _normalize_result(raw, params),
        "master_prompt": prompt[:20000], "tokens_used": tokens, "model": model,
        "credit_cost": _cost(params),
    }
    if ctx is not None:
        ctx.progress(100, "hoàn tất")
    return ket_qua
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5320_iterate.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/services/iterate.py tests/test_5320_iterate.py
git commit -m "pha3(D1): vong lap iterate, 2 luot dau mien phi dem trong CSDL

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task D2: `routes/iterate.py` — generate · verdict · lịch sử

**Files:**
- Create: `apps/prompt_ai_ommi/routes/iterate.py`
- Test: `tests/test_5321_routes_iterate.py`

**Interfaces:**
- Consumes: `iterate.*` (D1), `briefs.doc_brief`/`doc_canh`/`prompt_day_du` (C4/C6), `bundle.dung_bundle` (C3).
- Produces: `POST /api/briefs/{bid}/generate`, `POST /api/iterations/{iid}/verdict`, `GET /api/briefs/{bid}/iterations`.

- [ ] **Step 1: Viết test đỏ**

```python
"""Pha 3 — routes iterate. Trong tam: bao gia truoc, va khong hoan khi rejected."""
from __future__ import annotations

import inspect


def test_generate_co_buoc_bao_gia_truoc_khi_thu_tien():
    """`confirmed=false` phai tra gia ma KHONG nop job — khach thay tien truoc."""
    from apps.prompt_ai_ommi.routes import iterate as r
    nguon = inspect.getsource(r.generate)
    assert "confirmed" in nguon
    assert nguon.index("confirmed") < nguon.index("submit_with_credit")


def test_verdict_KHONG_he_goi_hoan_credit():
    """Banh coc: doc nguon, ⛔ khong cho ai them `credit.hoan` vao day."""
    from apps.prompt_ai_ommi.routes import iterate as r
    nguon = inspect.getsource(r.verdict)
    assert "hoan" not in nguon, "verdict ⛔ khong duoc hoan credit"


def test_moi_route_ghi_deu_kiem_csrf_va_rollout():
    from apps.prompt_ai_ommi.routes import iterate as r
    for ten in ("generate", "verdict"):
        nguon = inspect.getsource(getattr(r, ten))
        assert "_csrf(" in nguon and "_require_run_enabled" in nguon
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5321_routes_iterate.py -q
```

- [ ] **Step 3: Viết cài đặt tối thiểu**

```python
"""Vong lap sua kich ban — be mat web.

⛔ `verdict` KHONG hoan credit (spec §6.4). Mot dong `credit.hoan(...)` o day
   bien app thanh LLM mien phi vo han, va `test_5321` se do.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _require_run_enabled, _user, get_db, require_login, router)
from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services import iterate as it
from apps.prompt_ai_ommi.tables import OmmiIteration

JOB_TYPE = "prompt_ai_ommi.generate"


def _lay(db, bid: str, user):
    try:
        return bf.doc_brief(db, bid, user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy brief.'))


@router.post("/api/briefs/{bid}/generate", status_code=201)
async def generate(request: Request, bid: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    brief = _lay(db, bid, user)
    kiem = bf.preflight(brief)
    if not kiem["passed"]:
        raise HTTPException(status_code=422, detail=_t('Brief chưa đủ điều kiện.'))
    gia = it.bao_gia(db, brief)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, **gia}, status_code=200)

    feedback = str(body.get("feedback") or "").strip()
    params = {"operation": "iterate" if feedback else "director",
              "story": brief.story_vi, "title": brief.title,
              "goal": brief.goal, "audience": brief.audience,
              "scene_count": brief.target_scenes,
              "duration": brief.target_duration_sec,
              "aspect": brief.aspect_ratio, "language": brief.language,
              "feedback": feedback}
    luot = it.mo_luot(db, brief, feedback, "")
    if gia["was_free"]:
        # Luot mien phi: ⛔ khong qua `submit_with_credit` (no se giu cho credit).
        from platform_core import jobs as job_api
        job = job_api.submit(db, user_id=user.id, app_slug="prompt_ai_ommi",
                             job_type=JOB_TYPE, params=params)
    else:
        from platform_core import credit
        from platform_core.job_submit import dedupe_key_for, submit_with_credit
        try:
            job = submit_with_credit(
                db, user_id=user.id, app_slug="prompt_ai_ommi",
                job_type=JOB_TYPE, params=params,
                dedupe_key=dedupe_key_for(JOB_TYPE, params))
        except credit.ThieuCreditError as exc:
            db.rollback()
            raise HTTPException(status_code=402, detail=str(exc)) from exc
    luot.job_id = job.id
    db.commit()
    return {"confirmed": True, "credit": luot.credit_charged,
            "was_free": luot.was_free, "iteration_id": luot.id,
            "job_id": job.id, "free_left": it.con_mien_phi(brief)}


@router.post("/api/iterations/{iid}/verdict")
async def verdict(request: Request, iid: str,
                  _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    """⛔ KHONG hoan credit. Xem docstring dau tep."""
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    luot = db.get(OmmiIteration, str(iid or ""))
    if luot is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy lượt.'))
    _lay(db, luot.brief_id, user)          # kiem chu so huu qua brief
    try:
        it.dat_phan_quyet(db, luot, str(body.get("verdict") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"iteration": {"id": luot.id, "verdict": luot.verdict,
                          "credit_charged": luot.credit_charged}}


@router.get("/api/briefs/{bid}/iterations")
def lich_su(request: Request, bid: str,
            _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    brief = _lay(db, bid, _user(request))
    rows = db.execute(
        select(OmmiIteration).where(OmmiIteration.brief_id == brief.id)
        .order_by(OmmiIteration.seq)).scalars()
    return {"iterations": [
        {"id": r.id, "seq": r.seq, "feedback": r.feedback,
         "credit_charged": r.credit_charged, "was_free": r.was_free,
         "verdict": r.verdict, "job_id": r.job_id,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows], "free_left": it.con_mien_phi(brief)}
```

- [ ] **Step 4: Chạy test, phải XANH**

```bash
python -m pytest tests/test_5321_routes_iterate.py -q
```

- [ ] **Step 5: Commit**

```bash
git add apps/prompt_ai_ommi/routes/iterate.py tests/test_5321_routes_iterate.py
git commit -m "pha3(D2): endpoint iterate — bao gia truoc, verdict khong hoan credit

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# LÀN E — nhân vật · bối cảnh · khai tử `prompt_canh`

## Task E1: Chuyển lời nhắc khoá nhân vật từ `prompt_canh`

**Files:**
- Create: `apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt`
- Test: `tests/test_5340_loi_nhac_khoa_nhan_vat.py`

**Interfaces:**
- Produces: tệp lời nhắc dùng placeholder CHỮ HOA khớp bộ của `services/placeholders.py`.

- [ ] **Step 1: Đọc bản gốc, đừng viết lại từ đầu**

```bash
cat apps/prompt_canh/prompts/step1_character_lock.txt
cat apps/prompt_canh/prompts/step1_character_lock_fallback.txt
```

⭐ Đây là **nội dung nghiệp vụ đã chạy thật**. Chuyển sang, ⛔ không "cải tiến" trong cùng một bước — cải tiến và di trú lẫn nhau thì không biết cái nào làm hỏng.

- [ ] **Step 2: Viết test đỏ — lời nhắc phải dùng bộ placeholder của ta**

```python
"""Loi nhac khoa nhan vat — chuyen tu `prompt_canh`, dung bo placeholder cua ta.

⛔ Ban goc dung ten bien rieng cua no. Giu ten cu nghia la co HAI bo placeholder
   trong mot app — dung bay `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`.
"""
from __future__ import annotations

import pathlib

from apps.prompt_ai_ommi.services.placeholders import tim_placeholder

TEP = pathlib.Path("apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt")

#: Bien loi nhac nay duoc dung. Them bien moi ⇒ them vao day VA vao
#: `services/nhan_vat.py::_gia_tri_khoa`.
BIEN_CHO_PHEP = {"NAME", "GENDER", "AGE_RANGE", "FACE", "BODY", "HAIR",
                 "OUTFIT", "PERSONALITY", "EXPRESSION", "MOVEMENT",
                 "NEGATIVE_NOTES"}


def test_tep_ton_tai_va_khong_rong():
    assert TEP.exists() and TEP.read_text(encoding="utf-8").strip()


def test_khong_dung_bien_ngoai_danh_sach_cho_phep():
    dung = set(tim_placeholder(TEP.read_text(encoding="utf-8")))
    la = dung - BIEN_CHO_PHEP
    assert not la, f"bien khong khai: {sorted(la)}"


def test_tep_khong_co_BOM():
    """BOM trong tep cau hinh da lam sap production (AGENTS.md §5)."""
    assert not TEP.read_bytes().startswith(b"\xef\xbb\xbf")
```

- [ ] **Step 3: Chạy để thấy ĐỎ, rồi tạo tệp**

```bash
python -m pytest tests/test_5340_loi_nhac_khoa_nhan_vat.py -q
```

Tạo `apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt` — chuyển nội dung Step 1 sang, đổi mọi biến về bộ `BIEN_CHO_PHEP`, kết bằng yêu cầu trả JSON:

```
NHIEM VU: dung mot KHOI CHU CO DINH mo ta nhan vat, de chen nguyen van vao moi
canh nham giu nhan vat khong doi giua cac canh.

TEN: {NAME}
GIOI: {GENDER}
TUOI: {AGE_RANGE}
MAT: {FACE}
THAN HINH: {BODY}
TOC: {HAIR}
TRANG PHUC: {OUTFIT}
TINH CACH: {PERSONALITY}
BIEU CAM: {EXPRESSION}
CHUYEN DONG: {MOVEMENT}
TRANH: {NEGATIVE_NOTES}

Tra ve dung JSON sau, khong them chu nao ngoai JSON:
{{
  "fixed_prompt_block": "khoi chu mo ta nhan vat, tieng Anh, 60-120 tu",
  "negative_notes": "nhung thu phai tranh khi ve nhan vat nay"
}}
```

- [ ] **Step 4: Chạy test, phải XANH. Commit**

```bash
python -m pytest tests/test_5340_loi_nhac_khoa_nhan_vat.py -q
git add apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt tests/test_5340_loi_nhac_khoa_nhan_vat.py
git commit -m "pha3(E1): chuyen loi nhac khoa nhan vat tu prompt_canh

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task E2: `services/nhan_vat.py` + `routes/nhan_vat.py`

**Files:**
- Create: `apps/prompt_ai_ommi/services/nhan_vat.py`, `apps/prompt_ai_ommi/routes/nhan_vat.py`
- Test: `tests/test_5341_nhan_vat.py`

**Interfaces:**
- Produces:
  - `tao(db, owner_id, du_lieu) -> OmmiCharacter`; `doc(db, cid, owner_id)`; `liet_ke(db, owner_id)`; `sua(db, row, du_lieu)`
  - `tao_boi_canh(db, owner_id, du_lieu) -> OmmiBackground` (+ `doc_boi_canh`, `liet_ke_boi_canh`)
  - `chay_khoa_nhan_vat(params: dict, ctx=None) -> dict` — thân job cho `operation="character_lock"` (M3 gọi)
  - Endpoint: `GET/POST /api/characters`, `GET/PUT/DELETE /api/characters/{cid}`, `POST /api/characters/{cid}/lock`, `GET/POST /api/characters/{cid}/outfits`, `GET/POST /api/poses`, `GET/POST /api/backgrounds`, `POST /api/backgrounds/{bid}/lock`

- [ ] **Step 1: Viết test đỏ — trọng tâm: khối chữ khoá phải ĐI VÀO prompt của mọi cảnh**

```python
"""Pha 3 — nhan vat. Trong tam: `fixed_prompt_block` la thu giu nhan vat khong doi.

Neu khoi chu do khong di vao prompt cua MOI canh thi ca tinh nang khoa nhan vat
khong lam gi ca — va khong test nao bao, vi khoi chu VAN duoc luu.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import nhan_vat as nv


def test_tao_va_doc(db):
    c = nv.tao(db, "u1", {"name": "Ong Ngoai", "face_description": "rau bac"})
    db.flush()
    assert nv.doc(db, c.id, "u1").name == "Ong Ngoai"


def test_doc_cua_nguoi_khac_bi_tu_choi(db):
    c = nv.tao(db, "u1", {"name": "A"}); db.flush()
    with pytest.raises(KeyError):
        nv.doc(db, c.id, "u2")


def test_chay_khoa_nhan_vat_nem_khi_thieu_mo_ta():
    """⛔ Phai NEM, khong tra rong: nen tang dua vao exception de hoan credit."""
    with pytest.raises(ValueError):
        nv.chay_khoa_nhan_vat({"name": "", "face_description": ""})


def test_chay_khoa_nhan_vat_khong_gui_placeholder_nguyen_van(monkeypatch):
    """⭐ Doi chung cho bo kiem placeholder: loi nhac gui di khong con `{NAME}`."""
    da_gui = {}

    def _gia(system, prompt, model=""):
        da_gui["prompt"] = prompt
        return ({"fixed_prompt_block": "an old man", "negative_notes": ""}, 10)

    from apps.prompt_ai_ommi import provider
    monkeypatch.setattr(provider, "generate_json", _gia)
    monkeypatch.setattr(provider, "model_mac_dinh", lambda: "m")
    nv.chay_khoa_nhan_vat({"name": "Ong Ngoai", "face_description": "rau bac",
                           "gender": "nam", "age_range": "70",
                           "body_description": "gay", "hair_description": "bac",
                           "outfit_description": "ao nau",
                           "personality": "diem tinh", "expression_style": "it noi",
                           "movement_style": "cham", "negative_notes": "khong kinh"})
    from apps.prompt_ai_ommi.services.placeholders import tim_placeholder
    assert tim_placeholder(da_gui["prompt"]) == []


def test_boi_canh_cung_khuon(db):
    b = nv.tao_boi_canh(db, "u1", {"name": "Phong khach",
                                   "environment_description": "am"})
    db.flush()
    assert nv.doc_boi_canh(db, b.id, "u1").name == "Phong khach"
```

- [ ] **Step 2: Chạy để thấy ĐỎ, rồi viết cài đặt tối thiểu**

```bash
python -m pytest tests/test_5341_nhan_vat.py -q
```

`apps/prompt_ai_ommi/services/nhan_vat.py`:

```python
"""Nhan vat / trang phuc / dang / boi canh, va buoc KHOA.

⭐ Buoc khoa la manh PROMPT AI dang thieu, va la goc cua viec nhat quan nhan vat
   xuyen canh. No den tu `apps/prompt_canh` (buoc 1: character_lock) — app do bi
   khai tu o Task E5 sau khi buoc nay chay dung (spec X-5).
"""
from __future__ import annotations

import pathlib

from sqlalchemy import select

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.services import placeholders as ph
from apps.prompt_ai_ommi.tables import (OmmiBackground, OmmiCharacter,
                                        OmmiOutfit, OmmiPose)

_LOI_NHAC = (pathlib.Path(__file__).resolve().parents[1]
             / "prompts" / "khoa_nhan_vat.txt")

_TRUONG_CHU = ("gender", "age_range", "face_description", "body_description",
               "hair_description", "outfit_description", "personality",
               "expression_style", "movement_style", "fixed_prompt_block",
               "negative_notes")


def tao(db, owner_id: str, du_lieu: dict) -> OmmiCharacter:
    row = OmmiCharacter(owner_id=owner_id,
                        name=str(du_lieu.get("name") or "")[:160])
    db.add(row)
    return sua(db, row, du_lieu)


def sua(db, row: OmmiCharacter, du_lieu: dict) -> OmmiCharacter:
    if "name" in du_lieu:
        row.name = str(du_lieu["name"] or "")[:160]
    for ten in _TRUONG_CHU:
        if ten in du_lieu:
            setattr(row, ten, str(du_lieu[ten] or ""))
    if "reference_variant_ids" in du_lieu:
        row.reference_variant_ids = [
            str(x) for x in list(du_lieu["reference_variant_ids"] or [])[:40]]
    return row


def doc(db, cid: str, owner_id: str) -> OmmiCharacter:
    row = db.get(OmmiCharacter, str(cid or ""))
    if row is None or row.owner_id != owner_id:
        raise KeyError(cid)
    return row


def liet_ke(db, owner_id: str) -> list[OmmiCharacter]:
    return list(db.execute(
        select(OmmiCharacter).where(OmmiCharacter.owner_id == owner_id,
                                    OmmiCharacter.archived_at.is_(None))
        .order_by(OmmiCharacter.updated_at.desc())).scalars())


def tao_boi_canh(db, owner_id: str, du_lieu: dict) -> OmmiBackground:
    row = OmmiBackground(owner_id=owner_id,
                         name=str(du_lieu.get("name") or "")[:160])
    db.add(row)
    for ten in ("location_type", "environment_description",
                "lighting_description", "color_palette", "camera_feel",
                "important_objects", "fixed_prompt_block", "negative_notes"):
        if ten in du_lieu:
            setattr(row, ten, str(du_lieu[ten] or ""))
    return row


def doc_boi_canh(db, bid: str, owner_id: str) -> OmmiBackground:
    row = db.get(OmmiBackground, str(bid or ""))
    if row is None or row.owner_id != owner_id:
        raise KeyError(bid)
    return row


def liet_ke_boi_canh(db, owner_id: str) -> list[OmmiBackground]:
    return list(db.execute(
        select(OmmiBackground).where(OmmiBackground.owner_id == owner_id,
                                     OmmiBackground.archived_at.is_(None))
        .order_by(OmmiBackground.updated_at.desc())).scalars())


def _gia_tri_khoa(params: dict) -> dict:
    """Bien cua `prompts/khoa_nhan_vat.txt`. Them bien ⇒ sua CA HAI cho."""
    return {
        "NAME": params.get("name"), "GENDER": params.get("gender"),
        "AGE_RANGE": params.get("age_range"),
        "FACE": params.get("face_description"),
        "BODY": params.get("body_description"),
        "HAIR": params.get("hair_description"),
        "OUTFIT": params.get("outfit_description"),
        "PERSONALITY": params.get("personality"),
        "EXPRESSION": params.get("expression_style"),
        "MOVEMENT": params.get("movement_style"),
        "NEGATIVE_NOTES": params.get("negative_notes") or "khong co",
    }


def chay_khoa_nhan_vat(params: dict, ctx=None) -> dict:
    """Than job cho `operation="character_lock"`.

    ⛔ PHAI nem exception khi loi — nen tang dua vao exception de hoan credit (G-9).
    """
    from apps.prompt_ai_ommi import provider

    if not str(params.get("name") or "").strip():
        raise ValueError(_t('Cần tên nhân vật.'))
    if not str(params.get("face_description") or "").strip():
        raise ValueError(_t('Cần mô tả khuôn mặt để khoá nhân vật.'))
    body = _LOI_NHAC.read_text(encoding="utf-8")
    gia_tri = _gia_tri_khoa(params)
    thieu = ph.kiem_placeholder(body, list(gia_tri), gia_tri)
    if thieu:
        raise ValueError(_t('Thiếu thông tin: ') + ", ".join(thieu))
    loi_nhac = ph.render(body, gia_tri)
    if ctx is not None:
        ctx.progress(30, "đang khoá nhân vật")
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(
        "Ban la chuyen gia thiet ke nhan vat cho phim.", loi_nhac, model=model)
    khoi = str((raw or {}).get("fixed_prompt_block") or "").strip()
    if not khoi:
        raise ValueError(_t('AI không trả khối mô tả nhân vật.'))
    if ctx is not None:
        ctx.progress(100, "hoàn tất")
    return {"operation": "character_lock", "fixed_prompt_block": khoi,
            "negative_notes": str((raw or {}).get("negative_notes") or ""),
            "tokens_used": tokens, "model": model}
```

`apps/prompt_ai_ommi/routes/nhan_vat.py` — theo đúng khuôn của `routes/briefs.py` (Task C7): mọi route ghi có `_csrf`, route tạo job có `_require_run_enabled`, đọc chủ sở hữu bằng `KeyError → 404`.

- [ ] **Step 3: Chạy test, phải XANH. Commit**

```bash
python -m pytest tests/test_5341_nhan_vat.py -q
git add apps/prompt_ai_ommi/services/nhan_vat.py apps/prompt_ai_ommi/routes/nhan_vat.py tests/test_5341_nhan_vat.py
git commit -m "pha3(E2): nhan vat, boi canh va buoc khoa nhan vat

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task E3: Khối chữ khoá phải ĐI VÀO prompt của mọi cảnh (spec X-5)

**Files:**
- Modify: `apps/prompt_ai_ommi/services/composer.py` (hàm `director_prompt`)
- Test: `tests/test_5342_khoa_vao_moi_canh.py`

⭐ Đây là phép **quyết định** của làn E. Lưu được `fixed_prompt_block` mà không chèn vào prompt thì tính năng khoá nhân vật **không làm gì cả**, và không test nào báo.

- [ ] **Step 1: Viết test đỏ**

```python
"""X-5 — khoi chu khoa nhan vat PHAI di vao prompt gui LLM.

⚠️ Day la ca "tinh nang co ma khong lam gi": `fixed_prompt_block` VAN duoc luu,
   VAN hien tren giao dien, chi khong di vao prompt. Khong phep kiem nao khac
   bat duoc — dung dang loi `pham-vi-phep-do-hep-hon-loi-tuyen-bo`.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.composer import director_prompt

KHOI = "an elderly Vietnamese man, silver beard, brown ao dai"


def test_khoi_chu_khoa_nam_nguyen_van_trong_prompt_gui_LLM():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15,
        "character_block": KHOI})
    assert KHOI in prompt


def test_khong_co_khoi_thi_prompt_van_dung_duoc():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15})
    assert "x" * 40 in prompt


def test_khoi_boi_canh_cung_vao_prompt():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15,
        "background_block": "a warm living room at dusk"})
    assert "a warm living room at dusk" in prompt
```

- [ ] **Step 2: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5342_khoa_vao_moi_canh.py -q
```

- [ ] **Step 3: Sửa `composer.director_prompt`**

Thêm hai khối vào phần `REFERENCES:` của lời nhắc, ngay trước danh sách tài nguyên:

```python
    khoi = []
    for nhan, ten in (("CHARACTER LOCK (must match in EVERY scene)",
                       "character_block"),
                      ("BACKGROUND LOCK", "background_block")):
        gia_tri = str(params.get(ten) or "").strip()
        if gia_tri:
            khoi.append(f"{nhan}:\n{gia_tri}")
    # ⭐ Khoi khoa di TRUOC danh sach tai nguyen: LLM doc tu tren xuong, va day
    #    la rang buoc phai giu o MOI canh, khong phai mot goi y.
    resources_text = "\n\n".join(khoi + ["\n".join(resource_lines_text)])
```

⚠️ Tên biến cục bộ (`resource_lines_text`) phải khớp với tên đang có trong `director_prompt`. Đọc hàm đó trước khi sửa:

```bash
grep -n "def director_prompt" -A 40 apps/prompt_ai_ommi/services/composer.py
```

- [ ] **Step 4: Chạy test, phải XANH. Commit**

```bash
python -m pytest tests/test_5342_khoa_vao_moi_canh.py -q
git add apps/prompt_ai_ommi/services/composer.py tests/test_5342_khoa_vao_moi_canh.py
git commit -m "pha3(E3): khoi chu khoa nhan vat va boi canh di vao prompt moi canh

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task E4: Đối chứng chất lượng trước khi xoá `prompt_canh`

⭐ ⛔ **Đừng xoá bản gốc trước khi đo.** Bài học `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`: không có đối chứng thì "bước khoá nhân vật mới chạy đúng" chỉ là một câu nói.

**Files:**
- Create: `docs/PROMPT_AI/DOI_CHUNG_KHOA_NHAN_VAT.md`
- Test: không có test tự động — đây là **phép đo tay có bản ghi**

- [ ] **Step 1: Chạy bước khoá nhân vật của `prompt_canh` trên MỘT nhân vật thật**

Dùng tài khoản thử `khach1.thu`. Ghi lại nguyên văn: đầu vào, `fixed_prompt_block` nhận về, model, số token.

- [ ] **Step 2: Chạy bước khoá nhân vật MỚI trên ĐÚNG nhân vật đó**

Cùng mô tả, cùng model. Ghi lại nguyên văn.

- [ ] **Step 3: Ghi bản đối chứng**

`docs/PROMPT_AI/DOI_CHUNG_KHOA_NHAN_VAT.md`: hai cột cạnh nhau (bản gốc ⟷ bản mới), cùng một nhân vật, và một dòng kết luận. Nếu bản mới **kém hơn rõ rệt** ⇒ ⛔ **DỪNG**, báo chủ dự án, ⛔ không xoá `prompt_canh`.

- [ ] **Step 4: Commit bản đối chứng**

```bash
git add docs/PROMPT_AI/DOI_CHUNG_KHOA_NHAN_VAT.md
git commit -m "pha3(E4): doi chung khoa nhan vat — ban goc va ban moi tren cung nhan vat

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task E5: Xoá `apps/prompt_canh` — và dọn 10 tệp test tham chiếu tới nó

⚠️ Chỉ chạy **sau khi E3 xanh và E4 có bản ghi kết luận đạt** (spec X-5).

**Files:**
- Delete: `apps/prompt_canh/` (toàn bộ), `tests/test_1105_app_prompt_canh.py`
- Modify: 9 tệp test còn lại (đo được 26/09, tổng **26** chỗ tham chiếu)
- Test: `tests/test_5343_prompt_canh_da_xoa.py`

⭐ **Đo trước khi xoá** — xoá app không phải xoá một thư mục:

| Tệp | Số chỗ | Xử lý |
|---|---|---|
| `tests/test_1105_app_prompt_canh.py` | 12 | **Xoá cả tệp** |
| `tests/test_1113_phase14_agent_danh_gia.py` | 3 | Mổ từng chỗ |
| `tests/test_1112_phase13_hai_ban_khai_vram.py` | 2 | Mổ từng chỗ |
| `tests/test_190_public_api_coverage.py` | 2 | Mổ từng chỗ |
| `tests/test_88_agent_toolspec_apps.py` | 2 | Mổ từng chỗ |
| `tests/test_1107_khoa_luu_tru_an_toan.py` | 1 | Mổ |
| `tests/test_1111_phase12_workflow_dai_dien.py` | 1 | Mổ |
| `tests/test_1271_golden_ui_apps.py` | 1 | Mổ |
| `tests/test_1284_golden_ui_c4_apps.py` | 1 | Mổ |
| `tests/test_1757_palette_v3.py` | 1 | Mổ |

⚠️ 5 tệp cuối là **test liên-app dùng chung của mọi phiên**. Sửa chúng là đụng vào lưới của người khác ⇒ sửa **tối thiểu**, chỉ bỏ đúng `prompt_canh`, ⛔ không tái cấu trúc.

- [ ] **Step 1: Đo lại trước khi xoá — con số có thể đã đổi**

```bash
grep -rc "prompt_canh" tests/ | grep -v ":0"
```

Số khác bảng trên ⇒ có phiên khác vừa thêm tham chiếu. Cập nhật bảng, ⛔ đừng xoá theo bảng cũ.

- [ ] **Step 2: Viết test đỏ — app đã đi khỏi cây và khỏi registry**

`tests/test_5343_prompt_canh_da_xoa.py`:

```python
"""`apps/prompt_canh` da bi khai tu (Q-4), va khong con dau vet trong registry.

⚠️ Vi sao phai kiem registry chu khong chi kiem thu muc: manifest cua app do tu
   canh bao rang `public=False` CHI an trang web — tool VAN bam duoc qua agent
   (`apps/prompt_canh/manifest.py:86-102`). Mot thu muc bi xoa ma registry con
   nho la mot tool chay duoc tro vao ma khong ton tai.
"""
from __future__ import annotations

import pathlib


def test_thu_muc_app_khong_con():
    assert not pathlib.Path("apps/prompt_canh").exists()


def test_registry_khong_con_biet_app_nay():
    from platform_core.registry import discover
    assert not [m for m in discover() if m.manifest.slug == "prompt_canh"]


def test_khong_con_job_type_nao_tro_vao_app_da_xoa():
    from platform_core.registry import job_type_owners
    assert "prompt_canh.run" not in job_type_owners()


def test_khong_con_tep_test_nao_nhac_ten_app():
    """Banh coc: mot tham chieu con lai la mot test se do o gate cuoi plan."""
    con = [p.name for p in pathlib.Path("tests").glob("test_*.py")
           if "prompt_canh" in p.read_text(encoding="utf-8", errors="replace")
           and p.name != "test_5343_prompt_canh_da_xoa.py"]
    assert con == [], f"con tham chieu o: {con}"
```

- [ ] **Step 3: Chạy để thấy ĐỎ**

```bash
python -m pytest tests/test_5343_prompt_canh_da_xoa.py -q
```

- [ ] **Step 4: Xoá app và tệp test riêng của nó**

```bash
git rm -r apps/prompt_canh
git rm tests/test_1105_app_prompt_canh.py
```

- [ ] **Step 5: Mổ 9 tệp test còn lại, từng tệp một**

```bash
grep -n "prompt_canh" tests/test_1107_khoa_luu_tru_an_toan.py tests/test_1111_phase12_workflow_dai_dien.py tests/test_1112_phase13_hai_ban_khai_vram.py tests/test_1113_phase14_agent_danh_gia.py tests/test_1271_golden_ui_apps.py tests/test_1284_golden_ui_c4_apps.py tests/test_1757_palette_v3.py tests/test_190_public_api_coverage.py tests/test_88_agent_toolspec_apps.py
```

Với mỗi chỗ: nếu `prompt_canh` nằm trong một danh sách app ⇒ bỏ đúng phần tử đó. Nếu nó là tham số `parametrize` ⇒ bỏ đúng ca đó. ⛔ Không xoá cả phép kiểm.

- [ ] **Step 6: Chạy test mới + 9 tệp vừa mổ**

```bash
python -m pytest tests/test_5343_prompt_canh_da_xoa.py tests/test_1107_khoa_luu_tru_an_toan.py tests/test_1111_phase12_workflow_dai_dien.py tests/test_1112_phase13_hai_ban_khai_vram.py tests/test_1113_phase14_agent_danh_gia.py tests/test_1271_golden_ui_apps.py tests/test_1284_golden_ui_c4_apps.py tests/test_1757_palette_v3.py tests/test_190_public_api_coverage.py tests/test_88_agent_toolspec_apps.py -q
```

- [ ] **Step 7: Ghi nhật ký rồi commit**

Thêm một dòng vào `docs/NHAT_KY.md`: ngày, việc (khai tử `prompt_canh`), lý do (gộp `character_lock` vào PROMPT AI, Q-4), và đường tới bản đối chứng E4.

```bash
git add -A tests docs/NHAT_KY.md
git commit -m "pha3(E5): khai tu apps/prompt_canh, don 10 tep test tham chieu

Buoc character_lock da chay trong PROMPT AI (E3 xanh, doi chung E4).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# LÀN J — frontend 2-pane Studio Kịch bản

## Task J1: `ommiApi.ts` — hàm gọi endpoint mới

**Files:**
- Modify: `frontend/prompt-ai-ommi/src/ommiApi.ts`
- Test: `tests/test_5560_api_frontend_du_ham.py`

**Interfaces:**
- Produces: `listBriefs`, `createBrief`, `getBrief`, `updateBrief`, `cloneBrief`, `archiveBrief`, `preflightBrief`, `bundleBrief`, `quoteBrief`, `generateBrief`, `setVerdict`, `listIterations`, `listCharacters`, `createCharacter`, `lockCharacter`, `listBackgrounds`, `createBackground`.

- [ ] **Step 1: Viết test đỏ — bánh cóc đối chiếu frontend ⟷ backend**

```python
"""Banh coc: moi endpoint pha 3 deu co mot ham goi o frontend.

⭐ Do duoc 26/09: workspace React hien KHONG goi handoff, snapshot, import,
   reorder, usage, admin/catalog — tinh nang co o backend ma khach khong bam
   duoc. Phep kiem nay chan viec do lap lai o pha 3.
"""
from __future__ import annotations

import pathlib
import re

API = pathlib.Path("frontend/prompt-ai-ommi/src/ommiApi.ts")

DUONG_BAT_BUOC = (
    "/api/briefs", "/preflight", "/bundle", "/quote", "/generate",
    "/iterations", "/verdict", "/api/characters", "/lock", "/api/backgrounds",
)


def test_frontend_co_goi_moi_duong_pha_3():
    nguon = API.read_text(encoding="utf-8")
    thieu = [d for d in DUONG_BAT_BUOC if d not in nguon]
    assert thieu == [], f"frontend chua goi: {thieu}"


def test_khong_ham_nao_tu_tinh_lai_gia():
    """⛔ Gia la cua backend (`authoritative: true`). Tinh lai o frontend la hai
    cho khai cung mot dieu, va cho sai se la cho khach nhin thay.
    """
    nguon = API.read_text(encoding="utf-8")
    assert not re.search(r"credit\s*[*+]\s*\d", nguon)
```

- [ ] **Step 2: Chạy để thấy ĐỎ, viết hàm, chạy lại XANH**

```bash
python -m pytest tests/test_5560_api_frontend_du_ham.py -q
```

Thêm vào `ommiApi.ts` theo đúng khuôn hàm đã có trong tệp (cùng cách lấy CSRF, cùng cách xử lý lỗi). ⛔ Không đặt khuôn mới.

- [ ] **Step 3: Commit**

```bash
git add frontend/prompt-ai-ommi/src/ommiApi.ts tests/test_5560_api_frontend_du_ham.py
git commit -m "pha3(J1): ommiApi goi du endpoint pha 3, co banh coc doi chieu

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task J2: 2-pane Studio Kịch bản thành lối vào mặc định

**Files:**
- Create: `frontend/prompt-ai-ommi/src/StudioShell.tsx`, `src/BriefPane.tsx`
- Modify: `frontend/prompt-ai-ommi/src/OmmiShell.tsx`
- Test: `tests/test_5561_studio_2pane.py` (kiểm tĩnh) + kiểm bằng **trình duyệt thật**

- [ ] **Step 1: Viết test tĩnh đỏ**

```python
"""Loi vao mac dinh la 2-pane Studio Kich ban (Q-3), va `/classic` con song."""
from __future__ import annotations

import pathlib

SRC = pathlib.Path("frontend/prompt-ai-ommi/src")


def test_co_studio_shell_va_brief_pane():
    assert (SRC / "StudioShell.tsx").exists()
    assert (SRC / "BriefPane.tsx").exists()


def test_ommi_shell_lay_studio_lam_man_mac_dinh():
    nguon = (SRC / "OmmiShell.tsx").read_text(encoding="utf-8")
    assert "StudioShell" in nguon


def test_duong_classic_khong_bi_xoa():
    """`/classic` la duong lui khi Studio moi co van de tren production."""
    nguon = pathlib.Path("apps/prompt_ai_ommi/routes/pages.py").read_text(
        encoding="utf-8")
    assert "classic" in nguon
```

- [ ] **Step 2: Chạy để thấy ĐỎ, viết component, chạy lại XANH**

```bash
python -m pytest tests/test_5561_studio_2pane.py -q
```

`StudioShell.tsx`: hai cột — trái là `BriefPane` (danh sách brief, tìm, tạo, nhân bản), phải là khung soạn (brief, cảnh, nút Preflight / Bundle / Báo giá / Chạy, lịch sử iterate). Theo đúng token màu và khuôn CSS của `ommi.css`, ⛔ không thêm thư viện UI mới.

- [ ] **Step 3: Dựng frontend**

```bash
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien pha3-J -- npm --prefix frontend/prompt-ai-ommi run build
```

⚠️ Kiểm `tools\cua_so_yen.py trang-thai` + `tools\tai_may.py` trước (G-12).

- [ ] **Step 4: Cache-bust**

Tăng `ASSET_VER` trong `server/templating.py`. ⚠️ Đổi `ASSET_VER` cần **khởi động lại** service mới có hiệu lực.

- [ ] **Step 5: ⭐ Kiểm bằng TRÌNH DUYỆT THẬT — ⛔ không tuyên bố xong khi chưa kiểm**

Trên `https://app.lttstudios.com/prompt-ai-ommi` (⛔ không loopback — loopback bỏ qua Cloudflare), đăng nhập `khach1.thu` bằng cookie:

1. Trang mở ra ở **2-pane**, danh sách brief bên trái.
2. Tạo brief mới → xuất hiện trong danh sách.
3. Bấm **Preflight** → checklist hiện, ⛔ **không** trừ credit, ⛔ không `503`.
4. Bấm **Bundle** → khối chữ hiện ra copy được, ⛔ không trừ credit.
5. Bấm **Báo giá** → thấy `free_left: 2`.
6. Bấm **Chạy** lượt 1 và 2 → `was_free: true`, credit **không** giảm.
7. Bấm **Chạy** lượt 3 → báo giá dương, credit giảm đúng số đó.
8. Bấm **rejected** trên lượt 3 → ⛔ credit **không** hoàn lại.
9. Console: **0 lỗi**. Network: **0 request đỏ**.
10. `/prompt-ai-ommi/classic` vẫn mở được.

Chụp ảnh từng bước, lưu vào `docs/APP_AUDIT/prompt-ai-ommi/2026-09-26-pha3/evidence/`.

- [ ] **Step 6: Commit**

```bash
git add frontend/prompt-ai-ommi/src server/templating.py tests/test_5561_studio_2pane.py docs/APP_AUDIT/prompt-ai-ommi
git commit -m "pha3(J2): 2-pane Studio Kich ban lam loi vao mac dinh, kiem tren trinh duyet that

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task J3: Gộp `main` và đóng pha 3

- [ ] **Step 1: Chạy test nhắm cả cụm pha 3**

```bash
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien pha3 -- python -m pytest tests/test_53*.py tests/test_5560_api_frontend_du_ham.py tests/test_5561_studio_2pane.py -q
```

- [ ] **Step 2: Gộp `main`**

```bash
git fetch origin && git merge origin/main
```

Xung đột ⇒ dùng skill `resolving-merge-conflicts`, `git add` **tường minh** từng tệp. ⛔ Không `git add .` — dòng `??` lạ là phiên khác.

- [ ] **Step 3: `pre-commit` toàn cây (lưới duy nhất — merge KHÔNG chạy bánh cóc)**

```bash
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien pha3 -- pre-commit run --all-files
```

- [ ] **Step 4: Kiểm số test không trùng**

```bash
python tools/check_so_test.py
```

- [ ] **Step 5: ⛔ KHÔNG chạy gate**

Gate chạy **một lần, một cấp, ở cuối pha 5** (G-13, và Task 12 của plan pha 5). Hết pha 3 **không phải** cuối plan.

- [ ] **Step 6: Báo, không xin duyệt**

Một dòng: pha 3 xong, đã gộp `main`, kèm đường tới ảnh chứng ở `docs/APP_AUDIT/prompt-ai-ommi/2026-09-26-pha3/`.

---

## Tự soát

### 1. Độ phủ spec — mục nào của spec thuộc task nào

| Mục spec | Task |
|---|---|
| §4.2 Pha 3 — `ommi_brief`, `ommi_iteration`, `ommi_character`, `ommi_outfit`, `ommi_pose`, `ommi_background`, `ommi_face_embedding` | M1, M2 |
| §4.3 — `ommi_canh`, `ommi_scene.canh_id`, S-1..S-5 | M1, M2, C4, C5 |
| §6.2b — enum đóng, chi tiết vào prompt | C6 |
| §6.4 — brief/preflight/bundle/quote | C7 |
| §6.4 — generate/verdict/iterations, luật 2 lượt miễn phí | D1, D2 |
| §6.5 — nhân vật/outfit/pose/background + `/lock` | E2 |
| §7 + §7.1 — bảng quy đổi + 3 phép | C1 |
| §7.2 — image template dùng bộ khác ⇒ pha 3 **không** đo | ghi rõ ở đầu plan; không task nào |
| §10.2 T-2 — cả 12 mẫu | C2 |
| §10.2 T-3 — bộ đếm trong CSDL | D1 (`test_bo_dem_song_qua_mot_session_moi`) |
| §10.4 — kiểm giao diện trên trình duyệt thật | J2 Step 5 |
| Q-3 — 2-pane là lối vào mặc định | J2 |
| Q-4 — gộp `character_lock`, xoá `prompt_canh` | E1, E2, E3, E4, E5 |
| Q-6 — Bundle miễn phí | C3, C7 |
| Q-7 — 2 lượt đầu miễn phí | D1, D2 |
| Q-14 — 8 tính năng "chưa ai dùng" vẫn xây | M1 (bảng), E2 (nhân vật/bối cảnh). ⚠️ Profiles, `share_level` đầy đủ, budget cap là **pha 4**; kế thừa style là **pha 4** |
| X-5 — `prompt_canh` đã xoá, `character_lock` chạy | E3, E4, E5 |
| R-4 — tách package không vỡ import cũ | M0 |
| G-9 — handler ném exception khi lỗi | D1 (`chay_iterate`), E2 (`chay_khoa_nhan_vat`) |
| G-13 — ⛔ không gate trong phiên | J3 Step 5 |

**Lỗ còn lại, nói thẳng:** `ommi_face_embedding` chỉ được **tạo bảng**, không service/route — spec §6.5 không có endpoint nào cho nó. Người ghi đầu tiên là `services/composite.py` ở **pha 5**. ⛔ Không viết mã phòng thủ cho nó ở pha 3.

### 2. Quét placeholder

Đã quét, **0** chỗ còn: `TBD`, `TODO`, `implement later`, `xử lý lỗi phù hợp`, `add validation`, `handle edge cases`, `tương tự Task N`.
Hai chỗ **cố ý** không có giá trị cứng, và cả hai đều kèm **lệnh lấy giá trị**:

| Chỗ | Vì sao | Lệnh lấy |
|---|---|---|
| `down_revision` của M2 | Pha 1/2 do làn khác viết, head thật chỉ biết lúc thi hành | `python -m alembic heads` (M2 Step 1) |
| Tên biến cục bộ trong `director_prompt` (E3 Step 3) | Phải khớp mã đang có, không đoán | `grep -n "def director_prompt" -A 40 …` |

### 3. Nhất quán kiểu và tên

| Tên | Định nghĩa ở | Dùng ở | Khớp |
|---|---|---|---|
| `bat_bien_giao_bai(prompt, refs, skipped, *, has_binding=False)` | pha 1 | pha 2 | ✅ (spec §8) |
| `list_bindings(db, *, project_id, owner_id, scene_id=None)` | pha 1 làn A | C3 `bundle`, C5 | ✅ |
| `bool(list_bindings(...))` — ⛔ KHONG co ham `co_binding` | pha 1 làn A | C5 | ✅ |
| `kiem_placeholder(body, khai_bao, co_gia_tri) -> list[str]` | C1 | C2, C3, E2, **pha 4 làn G** | ✅ |
| `render(body, co_gia_tri) -> str` | C1 | C3, E2 | ✅ |
| `khai_bao_cua(meta) -> list[str]` | C3 | C7 | ✅ |
| `dung_bundle(db, brief, meta, style, ...)` | C3 | C7 | ✅ |
| `dat_canh(db, brief, canh) -> list[OmmiCanh]` | C4 | C5 | ✅ |
| `prompt_day_du(canh) -> str` | C6 | **pha 2 `handoff_stage`** | ✅ |
| `bao_gia(db, brief) -> dict` | D1 | D2 | ✅ |
| `mo_luot(db, brief, feedback, prompt_sent)` | D1 | D2 | ✅ |
| `dat_phan_quyet(db, iteration, verdict)` | D1 | D2 | ✅ |
| `chay_iterate(params, ctx)` | D1 | M3 | ✅ |
| `chay_khoa_nhan_vat(params, ctx)` | E2 | M3 | ✅ |
| `LUOT_MIEN_PHI = 2` | D1 | C7 (`quote` dùng số `2`) | ⚠️ **Lệch** |

⭐ **Một chỗ lệch đã tìm ra và phải sửa khi thi hành:** `routes/briefs.py::quote` (C7) viết `max(0, 2 - ...)` với số `2` gõ tay, trong khi D1 khai `LUOT_MIEN_PHI = 2`. Hai chỗ khai cùng một điều. Khi thi hành C7 **sau** D1, sửa `quote` thành:

```python
from apps.prompt_ai_ommi.services.iterate import con_mien_phi
...
    con_free = con_mien_phi(b)
```

và thêm vào `tests/test_5310_routes_briefs.py`:

```python
def test_quote_khong_go_lai_so_luot_mien_phi():
    """Hai cho khai cung mot dieu: doi LUOT_MIEN_PHI phai doi CA HAI cho."""
    import inspect
    from apps.prompt_ai_ommi.routes import briefs as r
    nguon = inspect.getsource(r.quote)
    assert "con_mien_phi" in nguon, "quote phai dung con_mien_phi, khong go so 2"
```

⚠️ Vì C7 chạy **trước** D1 theo bảng thứ tự làn, mà `quote` cần `con_mien_phi` của D1: hoặc đổi thứ tự thành **D1 → C7**, hoặc C7 tạm gõ số rồi D2 sửa. **Chọn: đổi thứ tự — D1 chạy trước C7.** Bảng "Thứ tự làn" ở đầu plan cập nhật theo: `M2 → C1,C2,C3,C4,C5,C6 → D1 → C7 → D2 → …`.
