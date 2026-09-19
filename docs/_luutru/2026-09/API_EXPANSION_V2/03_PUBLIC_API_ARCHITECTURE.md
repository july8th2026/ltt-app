> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/PUBLIC_API/. Chỉ đọc để hiểu lịch sử.

# Phase 02 — Kiến trúc Public API

Tiếp `01_CURRENT_TRUTH.md` và `02_OPTIONS_AND_RECOMMENDATION.md`.

> **Kết luận sớm, vì nó đổi khối lượng công việc:** thứ Prompt 02 yêu cầu tôi
> *thiết kế* thì **đã tồn tại trong mã**. Phase này chủ yếu là **tìm ra điều
> đó** và chốt cách dùng, chứ không phải thêm cơ chế.

---

## 1. Capability matrix

| Năng lực | Phân loại | Căn cứ |
|---|---|---|
| `text.chat` · `image.ltt` · `video.upscale` · `video.subtitle` | **LIVE_PUBLIC** | `GET /api/v1/tools` trả 4 dòng (30/08) |
| `image.thumbnail` · `image.generate` · `image.upscale` · `text.prompt_package` · `story.storyboard` | **READY_TO_EXPOSE** | `api_exposed=True`, hợp đồng có; chỉ chờ operator bật cờ |
| **`video.generate`** | **NEEDS_MIGRATION** | `api_contract` **rỗng** |
| `image.batch_generate` · `video.short_clips` | **NEEDS_MIGRATION** | hợp đồng rỗng |
| `chataistudio` (Codex) | **DEFER_NON_JOB_PRODUCT** | `job_types=()`; chờ quyết định chính sách (`02_OPTIONS` §6) |
| `agent` | **DEFER_NON_JOB_PRODUCT** | cần sandbox + trần chi phí trước khi bàn hợp đồng |
| `vps` · `nexus` · `qualitylab` | **INTERNAL_ONLY** | sản phẩm web/native, không khai ToolSpec nào |

⛔ Không ép `vps`/`nexus`/`agent` vào job API chỉ để danh sách trông đầy —
Prompt 02 §1 nói thẳng, và nó đúng.

---

## 2. 🔴 Phát hiện quyết định: ô cho ràng buộc theo model **đã có**

Prompt 03 §1 hỏi: *"chọn một representation machine-readable, additive và phù
hợp với catalog/model system hiện tại"*.

Đã có. `platform_core/public_api/catalog.py`:

```python
class PublicModel:
    constraints: dict = field(default_factory=dict)   # dong 173

    def to_public_dict(self):
        return {..., "constraints": dict(self.constraints)}   # dong 187 — CONG BO
```

và `build_models` đọc nó từ manifest:

```python
"constraints": dict(spec.get("constraints") or {})            # dong 347
```

**Chưa app nào dùng ô này.** Nó đã được công bố, và rỗng ở mọi nơi. Seedance là
người dùng đầu tiên — **không cần cơ chế mới, không có nguồn chân lý thứ hai.**

### 2.1 Và luật rò id nhà cung cấp — tôi đã hiểu sai ở Phase 01, nay sửa

Phase 01 tôi viết *"phải bỏ `provider_model_id` + `endpoint`"*. **Sai cơ chế**,
dù đúng ý định. Sự thật tốt hơn:

* `api_contract["models"][alias]["id"]` **được khai có chủ ý** — `test_212`
  `test_no_vendor_model_id_reaches_a_customer_surface` **đọc nó để biết phải
  săn chuỗi nào**;
* `ToolView.to_public_dict()` là **danh sách trắng** (`name`, `capability`,
  `description`, `execution_mode`, `input_schema`, `output_schema`,
  `required_scopes`, `aliases`, `deprecated`, `contract_hash`) — `id` **không có
  đường ra**, theo thiết kế chứ không theo phòng thủ.

⇒ Cách đúng là **khai** `id`, không phải giấu nó. Khai thì phép kiểm rò bảo vệ
nó ở năm bề mặt; giấu thì phép kiểm **không biết phải săn gì** — và
`test_212:623` từ chối chạy nếu không alias nào khai id: *"no aliases declared,
so this proves nothing"*.

⭐ Đây là một ví dụ đẹp của luật "khai ra để được canh", ngược với trực giác
"giấu đi cho an toàn". Ghi lại vì phiên sau rất dễ đi vào bẫy đó.

---

## 3. Hợp đồng Seedance — hình dạng chốt

```python
api_contract["models"]["seedance-2.0-mini"] = {
    "id": <provider_model_id>,        # NOI BO — de test ro san lung
    "description": ...,
    "stability": "stable",
    "constraints": {                  # CONG BO qua PublicModel
        "resolutions":   [...],
        "durations":     [...],
        "aspect_ratios": [...],
        "supports_seed": bool,
        "prompt_controls": [...],
    },
}
```

**Sinh từ `apps/taovideo/models.py`, không chép.** Đổi `MODELS` là hợp đồng đổi
theo, và `contract_hash` chuyển — đúng thứ `contract_hash` sinh ra để làm.

⚠️ `endpoint` **không** vào hợp đồng ở bất kỳ dạng nào: nó là địa chỉ hạ tầng,
không phải thuộc tính sản phẩm.

---

## 4. Protocol decision từng năng lực

| Năng lực | Chế độ | Route | Model alias | ToolSpec | Credit | Admission | Idempotency |
|---|---|---|---|---|---|---|---|
| `video.generate` | `ASYNC_JOB` | `/quotes` → `/jobs` → `/jobs/{id}` → `/artifacts` | **có** (3) | có | quote → hold → settle/refund | (chưa khai — provider ở xa) | `Idempotency-Key` bắt buộc |
| Codex *(hoãn)* | `STREAM` | `/v1/responses` + `/v1/messages` | có | có | phẳng, `chataistudio/cost.py` | dùng `/rate-limits` của sidecar | theo luồng |

**Vì sao Seedance không cần route mới:** đường `quote → job → artifact` đã phục
vụ ba tool video khác. Prompt 02 cho phép đề xuất route mới *"nếu contract hiện
tại không thể giữ semantics"* — nó giữ được.

---

## 5. Nguồn chân lý duy nhất cho tài liệu API

| Thứ | Nguồn | Sinh bởi |
|---|---|---|
| routes | `server/api/inventory.py` (24 route đóng băng) | so hai chiều với route thật + OpenAPI |
| tools | `AppManifest.tools` qua `build_catalog` | `tools/build_public_api_docs.py` |
| models + **constraints** | `api_contract["models"]` qua `build_models` | như trên |
| errors · scopes | `platform_core/public_api/` | như trên |
| examples | `platform_core/public_api/examples.py` | một nguồn cho web + `.exe` + tài liệu |
| limits | `apps/ltt_llm/ngan_sach.py` | đối chiếu bằng `test_334` |

⛔ Không thêm nguồn thứ hai nào. `USER_DECISIONS.md` §7.

---

## 6. Bảng quyết định

| Decision | Recommendation | Evidence | Alternative | Why not chosen |
|---|---|---|---|---|
| Biểu diễn ràng buộc theo model | dùng `PublicModel.constraints` **đã có** | `catalog.py:173,187,347`; chưa app nào dùng | schema hợp nhất + resolver riêng | sinh nguồn thứ hai; khách không thấy ràng buộc trước khi gọi |
| Nguồn của constraints | sinh từ `apps/taovideo/models.py` | `MODELS` giữ đủ 5 trường | chép vào manifest | hai bản sao sẽ lệch |
| `provider_model_id` | **khai** `id`, để danh sách trắng lọc | `test_212:611–634`; `to_public_dict` allowlist | giấu không khai | phép kiểm rò **mất mục tiêu để săn** |
| `endpoint` | **không** vào hợp đồng | địa chỉ hạ tầng | khai như constraint | không phải thuộc tính sản phẩm |
| Route cho Seedance | `/quotes`→`/jobs` **đã có** | 3 tool video khác đang dùng | route `/video` riêng | contract hiện tại giữ được semantics |
| Thứ tự kiểm | theo model, **trước** quote | Q84 + H35.10a+b | kiểm ở worker | báo giá đã ký vẫn quyết toán cao hơn |
| Hình dạng Codex | ToolSpec `STREAM` qua `require_tool` | `streaming.py:486`; `MODES_IN_USE` | bridge thẳng | mất ba cổng fail-closed + mất cô lập tiến trình |
| Codex backend | giữ **Auth** | `USER_DECISIONS.md` §2 | provider API-key | không phải target chính |

---

## 7. Contract delta trước khi code Phase 03

| Thay đổi | Ảnh hưởng |
|---|---|
| `video.generate` có `api_contract` | tool mới xuất hiện ở `/api/v1/tools` **khi operator bật** |
| 3 model mới ở `/api/v1/models` kèm `constraints` | phần thêm; client không hỏi thì không thấy |
| `contract_hash` của `video.generate` | tool **chưa từng mở** ⇒ không có tích hợp nào để phá |

⭐ Đổi hợp đồng của một tool **chưa bao giờ mở** là thay đổi rẻ nhất có thể có.
Đó là lý do làm Seedance **trước** khi mở nó, chứ không phải sau.
