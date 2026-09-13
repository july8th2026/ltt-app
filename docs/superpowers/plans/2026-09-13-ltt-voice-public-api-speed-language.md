# LTT Voice Public API — Thêm `speed` và `language` (D01–D03)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm hai tham số `speed` (tốc độ hậu kỳ) và `language` (làn ngôn ngữ) vào Public API `speech.ltt`, với validation reject thay vì silent clamp, đồng thời nới `TOC_DO_MIN`/`TOC_DO_MAX` ra [0.5, 2.0] theo D01.

**Architecture:** Platform validation (`invocation.validate_public_input`) đã hỗ trợ `type:"number"` với `minimum`/`maximum` và `type:"string"` với `enum` — ta chỉ khai trong `params_schema`. `build_job_params` truyền param cùng tên, nên dùng `speed`/`language` làm tên công khai và cho `features.chuan_hoa` đọc cả hai tên (ưu tiên `toc_do`/`ngon_ngu` cho web, fallback `speed`/`language` cho API). `kiem_truoc_api.kiem` đã gọi `chuan_hoa` nên validation D03 tự có — chỉ cần đảm bảo `chuan_hoa` **reject** thay vì silent fallback khi nhận giá trị ngoài tập hợp từ Public API.

**Tech Stack:** Python, pytest, ffmpeg atempo

**Spec:** Decision Lock D01–D08 đã duyệt trong phiên trước

## Global Constraints

- `TOC_DO_MIN = 0.5`, `TOC_DO_MAX = 2.0` (D01 — nới từ [0.75, 1.50])
- `CAC_NAC` web UI giữ nguyên `(0.75, 0.85, 1.0, 1.15, 1.25, 1.5)` — API dùng continuous range
- `language` enum: `["auto", "vi", "en"]`, default `"auto"` (D02)
- Platform validation reject ngoài range/enum — không silent clamp (D03)
- `speed` là hậu kỳ time-stretch, KHÔNG phải tham số engine (Q119 không liên quan)
- `language` điều khiển lane enforcement `lan_ngon_ngu.quyet_dinh`, KHÔNG phải engine
- Không sửa `platform_core/` — chỉ sửa trong `apps/ltt_voice/`
- TDD: test trước, code sau
- Commit sau mỗi task
- `pytest -n 6` tối đa, kiểm `cua_so_yen` trước

---

## File Structure

| Hành động | Tệp | Trách nhiệm |
|---|---|---|
| Modify | `apps/ltt_voice/toc_do.py:103-104` | Nới `TOC_DO_MIN`/`TOC_DO_MAX` |
| Modify | `apps/ltt_voice/manifest.py:294-313` | Thêm `speed` + `language` vào `params_schema` |
| Modify | `apps/ltt_voice/manifest.py:350-390` | Thêm `api_contract.params` docs cho `speed`/`language` |
| Modify | `apps/ltt_voice/features.py:177,187` | `chuan_hoa` đọc cả `speed`/`language` fallback |
| Create | `tests/test_516_voice_speed_language_api.py` | Test regression cho D01–D03 |

---

### Task 1: Nới khoảng tốc độ [0.5, 2.0] (D01)

**Files:**
- Modify: `apps/ltt_voice/toc_do.py:103-104`
- Test: `tests/test_516_voice_speed_language_api.py`

**Interfaces:**
- Consumes: `toc_do.TOC_DO_MIN`, `toc_do.TOC_DO_MAX`, `toc_do.hop_le()`
- Produces: `TOC_DO_MIN = 0.5`, `TOC_DO_MAX = 2.0` — mọi nơi import sẽ thấy giá trị mới

- [ ] **Step 1: Viết test chốt khoảng mới**

```python
# tests/test_516_voice_speed_language_api.py
"""D01–D03: speed và language trên Public API `speech.ltt`."""
from __future__ import annotations

from apps.ltt_voice import toc_do


class TestD01_KhoangTocDo:
    """D01: khoảng [0.5, 2.0], continuous."""

    def test_bien_duoi(self):
        assert toc_do.TOC_DO_MIN == 0.5

    def test_bien_tren(self):
        assert toc_do.TOC_DO_MAX == 2.0

    def test_hop_le_trong_khoang(self):
        assert toc_do.hop_le(0.5) == 0.5
        assert toc_do.hop_le(1.0) == 1.0
        assert toc_do.hop_le(2.0) == 2.0
        assert toc_do.hop_le(1.37) == 1.37

    def test_hop_le_clamp_duoi(self):
        assert toc_do.hop_le(0.3) == 0.5

    def test_hop_le_clamp_tren(self):
        assert toc_do.hop_le(2.5) == 2.0

    def test_hop_le_nan_ve_1(self):
        assert toc_do.hop_le(float("nan")) == 1.0

    def test_hop_le_inf_ve_tran(self):
        assert toc_do.hop_le(float("inf")) == 1.0

    def test_cac_nac_web_khong_doi(self):
        """CAC_NAC là discrete steps cho web UI — không đổi khi nới API."""
        assert toc_do.CAC_NAC == (0.75, 0.85, 1.0, 1.15, 1.25, 1.5)

    def test_cac_nac_nam_trong_khoang(self):
        for nac in toc_do.CAC_NAC:
            assert toc_do.TOC_DO_MIN <= nac <= toc_do.TOC_DO_MAX
```

- [ ] **Step 2: Chạy test — phải đỏ ở `test_bien_duoi` và `test_bien_tren`**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD01_KhoangTocDo -v`
Expected: FAIL — `assert 0.75 == 0.5` và `assert 1.5 == 2.0`

- [ ] **Step 3: Sửa hằng số trong `toc_do.py`**

Sửa `apps/ltt_voice/toc_do.py` dòng 103–104:

```python
TOC_DO_MIN = 0.5
TOC_DO_MAX = 2.0
```

- [ ] **Step 4: Chạy test — phải xanh**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD01_KhoangTocDo -v`
Expected: PASS

- [ ] **Step 5: Chạy test hiện có liên quan để đảm bảo không hồi quy**

Run: `pytest tests/ -k "toc_do or speed" -v -n 6`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/ltt_voice/toc_do.py tests/test_516_voice_speed_language_api.py
git commit -m "feat(voice): D01 — nới khoảng tốc độ [0.5, 2.0] cho Public API

CAC_NAC web UI giữ nguyên (0.75–1.5). API dùng continuous range.
atempo ffmpeg hỗ trợ 0.5–2.0 trong một bộ lọc duy nhất, ngoài khoảng
thì _chuoi_atempo đã nối chuỗi sẵn.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Thêm `speed` và `language` vào `params_schema` (D01, D02)

**Files:**
- Modify: `apps/ltt_voice/manifest.py:294-391`
- Test: `tests/test_516_voice_speed_language_api.py` (thêm class)

**Interfaces:**
- Consumes: `MANIFEST.tools[0].params_schema`, `platform_core.public_api.invocation.validate_public_input`, `toc_do.TOC_DO_MIN`, `toc_do.TOC_DO_MAX`
- Produces: `params_schema` có `speed` (number, min 0.5, max 2.0, required False) và `language` (string, enum ["auto","vi","en"], required False). `api_contract.params` có docs cho cả hai.

- [ ] **Step 1: Viết test chốt schema và api_contract**

Thêm vào `tests/test_516_voice_speed_language_api.py`:

```python
from apps.ltt_voice.manifest import MANIFEST


def _tool():
    return next(t for t in MANIFEST.tools if t.name == "speech.ltt")


class TestD01D02_ParamsSchema:
    """params_schema phải khai speed và language."""

    def test_speed_trong_schema(self):
        schema = _tool().params_schema
        assert "speed" in schema

    def test_speed_type_number(self):
        s = _tool().params_schema["speed"]
        assert s["type"] == "number"

    def test_speed_minimum(self):
        s = _tool().params_schema["speed"]
        assert s["minimum"] == 0.5

    def test_speed_maximum(self):
        s = _tool().params_schema["speed"]
        assert s["maximum"] == 2.0

    def test_speed_khong_bat_buoc(self):
        s = _tool().params_schema["speed"]
        assert s.get("required") is not True

    def test_language_trong_schema(self):
        schema = _tool().params_schema
        assert "language" in schema

    def test_language_type_string(self):
        s = _tool().params_schema["language"]
        assert s["type"] == "string"

    def test_language_enum(self):
        s = _tool().params_schema["language"]
        assert set(s["enum"]) == {"auto", "vi", "en"}

    def test_language_khong_bat_buoc(self):
        s = _tool().params_schema["language"]
        assert s.get("required") is not True

    def test_api_contract_co_speed(self):
        contract = _tool().api_contract
        assert "speed" in contract["params"]
        assert "description" in contract["params"]["speed"]

    def test_api_contract_co_language(self):
        contract = _tool().api_contract
        assert "language" in contract["params"]
        assert "description" in contract["params"]["language"]
```

- [ ] **Step 2: Chạy test — phải đỏ**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD01D02_ParamsSchema -v`
Expected: FAIL — `assert "speed" in schema`

- [ ] **Step 3: Thêm `speed` và `language` vào `params_schema` trong `manifest.py`**

Sửa `apps/ltt_voice/manifest.py`, thêm vào `params_schema` dict (sau `"preset"` entry):

```python
                # D01 (2026-09-13): tốc độ HẬU KỲ cho Public API.
                # Continuous range [0.5, 2.0]; platform validate_public_input
                # reject ngoài khoảng bằng minimum/maximum. Web UI vẫn dùng
                # CAC_NAC discrete.
                "speed": {"type": "number", "required": False,
                          "minimum": toc_do.TOC_DO_MIN,
                          "maximum": toc_do.TOC_DO_MAX},
                # D02 (2026-09-13): làn ngôn ngữ cho Public API.
                # "auto" = máy đoán (mặc định). Platform validate_public_input
                # reject giá trị ngoài enum.
                "language": {"type": "string", "required": False,
                             "enum": ["auto", "vi", "en"]},
```

Thêm import `toc_do` ở đầu `manifest.py` (sau dòng `from . import gia, nghe_thu, sidecar_client`):

```python
from . import gia, nghe_thu, sidecar_client, toc_do
```

Thêm vào `api_contract["params"]` (sau `"preset"` entry):

```python
                    "speed": {
                        "description": (
                            "Playback speed. 1.0 is normal. Range 0.5 (half "
                            "speed) to 2.0 (double speed). Applied as a "
                            "post-synthesis time-stretch — it does not change "
                            "how the model speaks, only how fast the output "
                            "plays. Billing is based on the original duration "
                            "before speed change. Omit or send 1.0 for normal "
                            "speed."),
                        "example": 1.0,
                    },
                    "language": {
                        "description": (
                            "Language lane for quality enforcement. 'auto' "
                            "(default) detects language from the text. 'vi' "
                            "or 'en' overrides detection. If the detected or "
                            "declared language does not match the voice's "
                            "lane, the request is rejected with "
                            "voice_language_mismatch."),
                        "example": "auto",
                    },
```

- [ ] **Step 4: Chạy test — phải xanh**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD01D02_ParamsSchema -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/ltt_voice/manifest.py tests/test_516_voice_speed_language_api.py
git commit -m "feat(voice): D01+D02 — khai speed/language trong params_schema

Platform validate_public_input tự reject ngoài range/enum nhờ
minimum/maximum (number) và enum (string) đã có sẵn.

speed: [0.5, 2.0] continuous, default bỏ qua = 1.0
language: auto|vi|en, default bỏ qua = auto

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: `features.chuan_hoa` đọc cả tên công khai `speed`/`language` (D03)

**Files:**
- Modify: `apps/ltt_voice/features.py:177,187`
- Modify: `apps/ltt_voice/kiem_truoc_api.py` (không thay đổi logic, chỉ thêm docstring)
- Test: `tests/test_516_voice_speed_language_api.py` (thêm class)

**Interfaces:**
- Consumes: `features.chuan_hoa(params)` — params dict từ web (`toc_do`/`ngon_ngu`) hoặc từ Public API (`speed`/`language`)
- Produces: `YeuCau` với `toc_do` và `ngon_ngu` đã chuẩn hoá, bất kể tên đầu vào

- [ ] **Step 1: Viết test cho dual-name resolution**

Thêm vào `tests/test_516_voice_speed_language_api.py`:

```python
from apps.ltt_voice import features


class TestD03_ChuanHoaDualName:
    """chuan_hoa phải đọc cả tên nội bộ lẫn tên công khai."""

    def test_toc_do_tu_ten_noi_bo(self):
        yc = features.chuan_hoa({"text": "xin chào", "toc_do": 1.5})
        assert yc.toc_do == 1.5

    def test_toc_do_tu_ten_cong_khai(self):
        yc = features.chuan_hoa({"text": "xin chào", "speed": 1.5})
        assert yc.toc_do == 1.5

    def test_toc_do_noi_bo_uu_tien(self):
        """Nếu cả hai có mặt, tên nội bộ thắng (web gửi cả hai là lỗi
        nhưng phải an toàn)."""
        yc = features.chuan_hoa({"text": "xin chào", "toc_do": 0.8,
                                  "speed": 1.5})
        assert yc.toc_do == 0.8

    def test_toc_do_mac_dinh_1(self):
        yc = features.chuan_hoa({"text": "xin chào"})
        assert yc.toc_do == 1.0

    def test_ngon_ngu_tu_ten_noi_bo(self):
        yc = features.chuan_hoa({"text": "xin chào", "ngon_ngu": "vi"})
        assert yc.ngon_ngu == "vi"

    def test_ngon_ngu_tu_ten_cong_khai(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "en"})
        assert yc.ngon_ngu == "en"

    def test_ngon_ngu_noi_bo_uu_tien(self):
        yc = features.chuan_hoa({"text": "xin chào", "ngon_ngu": "vi",
                                  "language": "en"})
        assert yc.ngon_ngu == "vi"

    def test_ngon_ngu_mac_dinh_auto(self):
        yc = features.chuan_hoa({"text": "xin chào"})
        assert yc.ngon_ngu == "auto"

    def test_language_auto_la_hop_le(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "auto"})
        assert yc.ngon_ngu == "auto"

    def test_language_gia_tri_la_ve_auto(self):
        yc = features.chuan_hoa({"text": "xin chào", "language": "fr"})
        assert yc.ngon_ngu == "auto"

    def test_speed_ngoai_khoang_bi_clamp(self):
        """chuan_hoa vẫn clamp (cho web). Platform reject trước cho API."""
        yc = features.chuan_hoa({"text": "xin chào", "speed": 5.0})
        assert yc.toc_do == 2.0

    def test_speed_0_3_bi_clamp_len_0_5(self):
        yc = features.chuan_hoa({"text": "xin chào", "speed": 0.3})
        assert yc.toc_do == 0.5
```

- [ ] **Step 2: Chạy test — phải đỏ ở test `_tu_ten_cong_khai`**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD03_ChuanHoaDualName -v`
Expected: FAIL — `assert 1.0 == 1.5` (speed default khi `speed` key không được đọc)

- [ ] **Step 3: Sửa `features.chuan_hoa` để đọc cả hai tên**

Sửa `apps/ltt_voice/features.py` dòng 177, thay:

```python
    ngon_ngu = str(p.get("ngon_ngu") or "auto").strip().lower()
```

bằng:

```python
    ngon_ngu = str(p.get("ngon_ngu") or p.get("language") or "auto").strip().lower()
```

Sửa dòng 187, thay:

```python
                  toc_do=_toc_do.hop_le(p.get("toc_do", 1.0)))
```

bằng:

```python
                  toc_do=_toc_do.hop_le(p.get("toc_do", p.get("speed", 1.0))))
```

- [ ] **Step 4: Chạy test — phải xanh**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD03_ChuanHoaDualName -v`
Expected: PASS

- [ ] **Step 5: Chạy toàn bộ test file mới**

Run: `pytest tests/test_516_voice_speed_language_api.py -v`
Expected: PASS

- [ ] **Step 6: Chạy test hiện có liên quan**

Run: `pytest tests/ -k "voice" -v -n 6`
Expected: PASS — không hồi quy

- [ ] **Step 7: Commit**

```bash
git add apps/ltt_voice/features.py tests/test_516_voice_speed_language_api.py
git commit -m "feat(voice): D03 — chuan_hoa đọc cả speed/language từ Public API

build_job_params truyền param cùng tên (speed/language), trong khi web
routes truyền tên nội bộ (toc_do/ngon_ngu). chuan_hoa nay đọc cả hai,
ưu tiên tên nội bộ khi cả hai có mặt.

Platform validation đã reject ngoài range/enum trước khi tới đây.
chuan_hoa vẫn clamp/fallback cho web (backward compatible).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Test tích hợp end-to-end qua platform validation

**Files:**
- Test: `tests/test_516_voice_speed_language_api.py` (thêm class)

**Interfaces:**
- Consumes: `platform_core.public_api.invocation.validate_public_input`, `MANIFEST.tools[0]`
- Produces: Bằng chứng platform reject đúng giá trị ngoài khoảng/enum

- [ ] **Step 1: Viết test tích hợp platform validation**

Thêm vào `tests/test_516_voice_speed_language_api.py`:

```python
import pytest

from platform_core.public_api.invocation import validate_public_input
from platform_core.public_api.catalog import project_tool


def _public_tool():
    """Dựng PublicTool từ manifest — cùng cách catalog.project_tool làm."""
    tool = _tool()
    # validate_public_input nhận PublicTool hoặc ToolSpec; cần kiểm cả hai
    return tool


class TestD03_PlatformReject:
    """Platform phải reject giá trị ngoài khoảng/enum — D03."""

    def test_speed_qua_tran_bi_reject(self):
        tool = _public_tool()
        with pytest.raises(Exception, match="speed"):
            validate_public_input(tool, {"text": "xin chào", "speed": 2.5})

    def test_speed_duoi_san_bi_reject(self):
        tool = _public_tool()
        with pytest.raises(Exception, match="speed"):
            validate_public_input(tool, {"text": "xin chào", "speed": 0.1})

    def test_speed_trong_khoang_khong_loi(self):
        tool = _public_tool()
        result = validate_public_input(tool, {"text": "xin chào", "speed": 1.5})
        assert result  # không ném

    def test_language_gia_tri_la_bi_reject(self):
        tool = _public_tool()
        with pytest.raises(Exception, match="language"):
            validate_public_input(tool, {"text": "xin chào", "language": "fr"})

    def test_language_auto_khong_loi(self):
        tool = _public_tool()
        result = validate_public_input(tool, {"text": "xin chào",
                                               "language": "auto"})
        assert result

    def test_language_vi_khong_loi(self):
        tool = _public_tool()
        result = validate_public_input(tool, {"text": "xin chào",
                                               "language": "vi"})
        assert result

    def test_language_en_khong_loi(self):
        tool = _public_tool()
        result = validate_public_input(tool, {"text": "hello world",
                                               "language": "en"})
        assert result
```

⚠️ **Lưu ý**: `validate_public_input` có thể cần `PublicTool` thay vì `ToolSpec`. Nếu chữ ký không khớp, executor phải đọc `invocation.py` để xác nhận interface và điều chỉnh test helper `_public_tool()` cho phù hợp — có thể cần dựng `PublicTool` bằng `catalog.project_tool()` hoặc mock.

- [ ] **Step 2: Chạy test — phải xanh (platform đã hỗ trợ minimum/maximum/enum)**

Run: `pytest tests/test_516_voice_speed_language_api.py::TestD03_PlatformReject -v`
Expected: PASS nếu `validate_public_input` nhận `ToolSpec` trực tiếp. Nếu cần `PublicTool`, sửa helper rồi chạy lại.

- [ ] **Step 3: Commit**

```bash
git add tests/test_516_voice_speed_language_api.py
git commit -m "test(voice): D03 — chốt platform reject speed/language ngoài khoảng

Xanh = platform validation đã cưỡng chế minimum/maximum cho speed
và enum cho language TRƯỚC khi tới kiem_truoc hay worker.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Gate regression — toàn bộ test voice phải xanh

**Files:** không sửa file nào
**Interfaces:**
- Consumes: toàn bộ test suite liên quan đến voice
- Produces: bằng chứng không hồi quy

- [ ] **Step 1: Kiểm `cua_so_yen`**

Run: `python tools\cua_so_yen.py trang-thai`
Expected: không phiên nào đang giữ

- [ ] **Step 2: Chạy toàn bộ test voice**

Run: `pytest tests/ -k "voice or ltt_voice or lan_ngon or toc_do or giong" -v -n 6`
Expected: ALL PASS

- [ ] **Step 3: Nếu có test đỏ — sửa và quay lại Step 2**

Đọc lỗi, sửa đúng file nguồn (không sửa test hiện có trừ khi test kiểm sai), commit riêng với prefix `fix(voice):`.

- [ ] **Step 4: Ghi kết quả**

Ghi stdout của lượt chạy xanh cuối cùng vào `test-results/voice-acceptance/d01-d03-regression.txt` (tạo thư mục nếu chưa có).
