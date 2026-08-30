# Phase 01 — Current truth

**Đo 2026-08-30.** Mọi bảng dưới đây **sinh từ registry**, không gõ tay:

```powershell
python tools\do_current_truth.py          # bang Markdown
python tools\do_current_truth.py --json   # cho may doc
```

> ⛔ `USER_DECISIONS.md` §7 cấm một danh sách tài liệu thứ hai khi source đã sinh
> được dữ liệu động. Dự án này đã trả giá đúng cho điều đó: `CLAUDE.md` hàng H35
> nói sai số tool đang mở **hai lần**, cùng một hướng nguy hiểm. Nên bảng ở đây
> là **đầu ra của một lệnh**, không phải một bản chép.

---

## 1. Danh mục — 17 dòng, sinh từ `discover()`

| app | tool | trạng thái | chế độ | job_type | models | admission |
|---|---|---|---|---|---|---|
| `agent` | *(không khai ToolSpec)* | HOP_DONG_RONG | - | `agent.advance` | — | — |
| `anhnoibo` | `image.ltt` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `anhnoibo.generate` | — | — |
| `autosubvideo` | `video.subtitle` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `autosubvideo.render` | — | — |
| `chataistudio` | *(không khai ToolSpec)* | HOP_DONG_RONG | - | — | — | — |
| `ltt_llm` | `text.chat` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `ltt_llm.chat` | `ltt_llm`, `ltt_llm_vision` | `llm_remote` ×1 |
| `nexus` | *(không khai ToolSpec)* | HOP_DONG_RONG | - | — | — | — |
| `prompt_ai_ommi` | `text.prompt_package` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `prompt_ai_ommi.generate` | — | — |
| `prompt_ai_ommi` | `story.storyboard` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `prompt_ai_ommi.generate` | — | — |
| `qualitylab` | *(không khai ToolSpec)* | HOP_DONG_RONG | - | `qualitylab.evaluate` | — | — |
| `taoanh` | `image.generate` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `taoanh.generate` | `enhanced`, `standard`, `standard-lite` | — |
| `taoanh` | `image.batch_generate` | HOP_DONG_RONG | ASYNC_JOB | `taoanh.generate` | — | — |
| `taoclipngan` | `video.short_clips` | HOP_DONG_RONG | ASYNC_JOB | `taoclipngan.render` | — | — |
| **`taovideo`** | **`video.generate`** | **HOP_DONG_RONG** | ASYNC_JOB | `taovideo.generate` | — | — |
| `thumbnail` | `image.thumbnail` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `thumbnail.generate` | — | — |
| `upscalevideo` | `video.upscale` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `upscalevideo.render` | — | — |
| `upscalevideo` | `image.upscale` | DA_KHAI_CHUA_BAT | ASYNC_JOB | `upscalevideo.render` | — | — |
| `vps` | *(không khai ToolSpec)* | HOP_DONG_RONG | - | `vps.provision,…` | — | — |

**Tổng: `DA_KHAI_CHUA_BAT` = 9 · `HOP_DONG_RONG` = 8**

⭐ **Ba nhãn, không phải hai.** Bản đầu của công cụ chỉ có "chưa mở", và nó gộp
ba tình huống rất khác nhau — đó chính là cách người ta kết luận sai:

| Nhãn | Nghĩa | Việc phải làm để mở |
|---|---|---|
| `HOP_DONG_RONG` | `api_contract` **rỗng** — chưa ai viết hợp đồng công khai | viết hợp đồng |
| `DA_KHAI_CHUA_BAT` | hợp đồng có, `api_exposed=True`, **operator chưa bật cờ** | bật `LTT_PUBLIC_API_TOOLS` |
| `DANG_MO` | qua đủ ba cổng Q92 | — |

⚠️ Cột `DANG_MO` đọc từ biến của **tiến trình chạy lệnh**. Muốn biết production
đang mở gì thì **hỏi máy chủ**: `GET /api/v1/tools`. Đo 30/08: **bốn** —
`text.chat`, `image.ltt`, `video.upscale`, `video.subtitle`.

---

## 2. Hai mục tiêu của gói

### 2.1 `video.generate` (Seedance)

| | |
|---|---|
| App | `apps/taovideo/` — `manifest.py`, `modelark.py`, `models.py`, `cost.py`, `quotes.py`, `refs.py`, `assets.py` |
| Provider | BytePlus ModelArk, qua APIKEYS (provider `byteplus`, category `video`) |
| Chạy | async submit→poll, `job_type="taovideo.generate"` |
| Tham số | `prompt`, `model`, `resolution`, `duration`, `aspect_ratio`, `generate_audio`, `camera`, `motion`, `visual_style`, `seed`, `image_key`, `image_keys`, `video_key`, `audio_key`, `refs` — **15** |
| Trạng thái API | 🔴 `api_contract` **rỗng hoàn toàn** |

🔴 **Hồ sơ cũ mô tả chưa đủ chính xác.** `APP_API_COVERAGE_FINAL.md` ghi lý do
chặn là *"tập tuỳ chọn hợp lệ đổi theo model, chưa publish được một hợp đồng
đúng"* — đọc như thể vấn đề là **thiết kế cách biểu diễn**. Đo thật thì
`api_contract` **rỗng**, tức chưa ai viết hợp đồng, chấm hết.

⭐ **Và cách biểu diễn thì đã có sẵn.** `apps/taovideo/models.py` giữ ràng buộc
theo **từng model**, đúng dạng máy đọc được mà Prompt 03 §1 yêu cầu:

```
DEFAULT_MODEL = "seedance-2.0-mini"
MODELS = { "seedance-2.0-mini" | "seedance-2.0" | "seedance-2.0-fast" }
  moi model khai: aspects · durations · resolutions · supports_seed
                  prompt_controls · active · label
                  provider_model_id · endpoint     <-- NOI BO
```

⇒ Việc còn lại **không phải** "thiết kế một representation" mà là ba việc nhỏ,
rõ ràng: **công bố** dữ liệu đã có (bỏ `provider_model_id` + `endpoint`), **kiểm
tra** theo nó trước quote/hold/dispatch, và **sinh tài liệu** từ nó.

### 2.2 Codex bridge

| | |
|---|---|
| Runtime | `codex_sidecar/server.py` + `runtime.py` — chỉ nghe `127.0.0.1`, bearer `LTT_CODEX_SIDECAR_TOKEN` |
| Endpoint đã có | `/health` `/models` `/account` `/capabilities` `/rate-limits` `/login/api-key` `/login/device/start` … |
| App dùng nó | `apps/chataistudio/` — `job_types=()`, chat **stream trong tiến trình web** |
| Giá | `apps/chataistudio/cost.py` — **giá bán phẳng ta đặt**, vì provider tính theo quota tuần chứ không đưa chi phí token |

🔴 **Lý do chặn trong hồ sơ đã LỖI THỜI.** `APP_API_COVERAGE_FINAL.md` ghi *"cần
một hợp đồng chạy mới, không phải một tool mới"* — viết **trước H38**.

Đo lại hôm nay:

* `platform_core/public_api/protocol.py` — `STREAM` nằm trong `MODES_IN_USE`;
* `server/api/streaming.py:486` gác luồng bằng **chính ba cổng của tool**:
  `require_tool(build_catalog(config), TOOL_CHAT, principal)`;
* qua Cloudflare: `/v1/messages` và `/v1/responses` trả `text/event-stream`
  (66 và 63 khối SSE).

⇒ **Hợp đồng chạy streaming đã tồn tại, đã sống, và khoá theo một ToolSpec** —
không hardcode cho `ltt_llm`. Rào cản còn lại của Codex bridge là **chính sách**,
không phải kiến trúc.

⭐ Và giá của `chataistudio` **đã đúng khuôn gói đòi**: Prompt 04 §5 cấm *"giả
token count để thu tiền"*; `cost.py` đã ghi rõ nó là giá bán phẳng vì upstream
không đưa chi phí token. Không phải xây lại.

---

## 3. Bất biến đã xác minh còn đúng

| Bất biến | Bằng chứng |
|---|---|
| Fail-closed | `LTT_PUBLIC_API_TOOLS` rỗng ⇒ 0 tool; `api_exposed` là điều kiện **cần**, không đủ |
| Một hàng đợi | `job_types` của mọi app đổ về `jobs`; không app nào tự dựng vòng lặp |
| Một sổ tiền | `credit` giữ chỗ → quyết toán → hoàn |
| 24 route đóng băng | `server/api/inventory.py`, so hai chiều với route thật + OpenAPI |
| Bảng phủ sóng là dữ liệu | `test_212` đọc `APP_API_COVERAGE_FINAL.md` hai chiều |

---

## 4. Baseline gate

```
python tools\gate.py   ->  RESULT: PASS      (30/08, truoc khi bat dau phase 03)
python tools\so_deploy.py -> khop: 500 | lech: 0
```

---

## 5. Deviations

**`DEVIATION_WITH_EVIDENCE`** — hai chỗ hồ sơ cũ nói không đúng, đã sửa ở trên:

1. Lý do chặn của `video.generate` là **hợp đồng rỗng**, không phải "chưa thiết
   kế được cách biểu diễn"; và dữ liệu ràng buộc theo model **đã có sẵn**.
2. Lý do chặn của `chataistudio` (*"cần một hợp đồng chạy mới"*) **đã lỗi thời**
   từ H38 — hợp đồng `STREAM` đã có và đã sống.
