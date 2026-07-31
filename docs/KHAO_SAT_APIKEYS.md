# Khảo sát APIKEYS (từ D:\BOT GEMINI) + phương án bộ máy APIKEYS — 2026-07-31

> Khảo sát sâu 4 luồng trên `D:\BOT GEMINI` (chỉ đọc) để dựng **bộ máy quản lý
> API key** cho nền tảng LTTSTUDIOSAPP, kèm menu quản trị **APIKEYS**. File này
> là ảnh chụp nghiên cứu + phương án; plan triển khai chi tiết viết SAU khi
> người dùng duyệt phương án.

## 1. Danh sách API/provider đang có trong BOT GEMINI

Có **6 key thật** trong `D:\BOT GEMINI\data\api_keys.json` (mã hoá Fernet):
gemini×1, byteplus×1, apiai×1, cheapkeyai×2, plenx×1. Hai HỌ xác thực tách biệt:

**A. Key CHÍNH THỨC (có trong pool, xoay vòng, tính tiền được):**

| Provider | Auth | Base URL | Năng lực | Kiểu gọi | Giá |
|---|---|---|---|---|---|
| `gemini` | query `?key=` | generativelanguage.googleapis.com/v1beta | chat, ảnh, (liệt kê model) | đồng bộ 1 POST | theo `usageMetadata` token |
| `apiai` (gateway OpenAI-compat) | `Authorization: Bearer` | api.apiai.vn/api/v1 | chat, ảnh | đồng bộ | phẳng VND/ảnh; chat theo token |
| `cheapkeyai` (gateway) | `Authorization: Bearer` | cheapkeyai.shop/v1 | chat, ảnh | đồng bộ | theo token |
| `byteplus` (ModelArk) | `Authorization: Bearer` | ark.ap-southeast.bytepluses.com/api/v3 | **video** | **async: submit→poll** | token (px×fps×giây) × rate/model |
| `plenx` | header `X-API-Key: pk_...` | api.plenxai.com/api/v1/developer | **video** (Seedance/Kling) | **async: submit→poll** | theo model/quality |

**B. Credential COOKIE/BROWSER (KHÔNG phải API key — không vào pool):**
Veo/`gemini_video`, ChatGPT web, các module `veo3`/`flow_*`/`taoanh_flow` (đã gỡ)
— chạy bằng phiên trình duyệt/`auth.json`, quota "browser", không có key HTTP.
→ **LTTSTUDIOSAPP phải coi đây là loại credential KHÁC, không nhét vào bộ máy key.**

## 2. Ánh xạ "4 loại KEY" người dùng nêu → mô hình thực

Nghiên cứu cho thấy: một key gắn với **PROVIDER**, và provider cung cấp một hoặc
nhiều **NĂNG LỰC**. "4 loại" của người dùng chính là **4 năng lực/category**, một
key có thể có nhiều (Gemini = chat + ảnh + liệt-kê-model). Đề xuất mô hình:
**key = provider + tập category** (`model_control | chat | image | video`).

| Loại người dùng nêu | Bản chất | Provider phục vụ (hiện có) | Quy tắc |
|---|---|---|---|
| 1. Điều khiển model (liệt kê) | Nguồn **catalog model** của provider | mọi provider | Gemini/ModelArk/plenx: catalog **cà tay** (đã "verify live" một lần rồi chép vào code). Chỉ OpenAI-compat (`/v1/models`) + Codex liệt kê **live**. → LTTSTUDIOSAPP: giữ **Model Registry** trong `platform_core`; nút "Làm mới model" gọi endpoint list (nếu provider có) để GỢI Ý, admin duyệt. |
| 2. Chat | sinh văn bản | gemini (`?key=`), apiai/cheapkeyai (`Bearer`) | body Gemini `contents[]` / OpenAI `messages[]`; SSE khác khung; timeout 120s |
| 3. Tạo ảnh | sinh ảnh | gemini (`?key=`), apiai/cheapkeyai (`Bearer`) | **đồng bộ** 1 POST; Gemini `responseModalities+imageConfig`; giá theo usage/phẳng |
| 4. Tạo video | sinh video | byteplus (`Bearer`), plenx (`X-API-Key`) | **async submit→poll** (task id → status → url); duration/resolution; **không huỷ được = tính tiền đủ**; poll 5s, timeout co giãn |

## 3. `ApiKey` — bộ trường (học từ BOT GEMINI, rút gọn cho LTTSTUDIOSAPP)

Định danh: `id`, `owner_user_id` (rỗng = pool dùng chung), `name`, `provider`,
`categories` (tập trong 4 loại), `tags`, `notes`.
Credential: `credential` (mã hoá **Fernet bằng `LTT_TOKEN_ENCRYPTION_KEY`** — một
khoá at-rest của nền tảng), `base_url`, `auth_style` (suy từ provider).
Định tuyến model: `supported_models[]` (rỗng = mọi model của provider),
`default_model`.
Trạng thái: `status` (active/exhausted/cooldown/error/disabled), `enabled`,
`last_used`, `last_error`, `error_count`, `auth_error_count`, `cooldown_until`,
`health_score`, `priority`.
Hạn mức/thống kê: `rpm_limit`, `tpm_limit`, `max_daily_requests`, `quota_*`,
`total_requests/success/failed`, `total_tokens`, `avg_latency_ms`.
DTO an toàn: chỉ lộ `key_preview` (4 số cuối), KHÔNG bao giờ trả `credential`.

## 4. Bài học kiến trúc (điều NÊN và KHÔNG nên chép)

**Nên chép (khái niệm):** bộ trường `ApiKey`; enum trạng thái + chuyển trạng thái
(mark_success/cooldown/error/auth_error); chọn key **idle-first → priority →
round-robin**; phân loại lỗi (401/403→disable sau 5 lần; 429→exhausted/cooldown
theo retry-after; **4xx KHÔNG phạt key**; 5xx→error); mẫu lease/in-use; DTO không
lộ secret; probe `test key` (gọi `/v1/models` hoặc 1 call rẻ để kiểm sống).

**KHÔNG chép (sai với LTTSTUDIOSAPP):**
- **File JSON + dict trong RAM + khoá `threading.Lock`** → đa-worker/đa-tiến-trình
  của ta sẽ lệch. Thay bằng **bảng SQLAlchemy** + chọn key bằng `SELECT … FOR
  UPDATE SKIP LOCKED` / UPDATE nguyên tử (giống `jobs.claim`).
- **`FERNET_KEY` riêng** → dùng `LTT_TOKEN_ENCRYPTION_KEY` sẵn có (một khoá).
- **3 registry model rời + config tĩnh + engine stub** → gom thành **một Model
  Registry** trong `platform_core`, tách rõ 3 ID (id-catalog / provider-model-id /
  account-endpoint-id — bài học từ `VideoModelInfo`/ModelArk).

## 5. Giá & credit
BOT GEMINI: `cost.py` per-module — video token `(px×fps×giây)/1024 × rate/model`,
ảnh theo `usageMetadata`, chat per-token; `markup_percent` + `usd_to_vnd(26000)`.
→ LTTSTUDIOSAPP đã có **sổ credit** (H3): mỗi model có `credit_cost(params)` (đã
làm ở thumbnail). Bộ máy key **quyết toán credit theo usage thật** provider trả
về (đã có đường `result["credit_cost"]` ở worker) — không cần cost.py song song.

## 6. Import 6 key từ BOT GEMINI
Key nằm ở `D:\BOT GEMINI\data\api_keys.json`, mã hoá bằng `FERNET_KEY` của BOT
GEMINI. Script import **một lần**: giải mã bằng khoá của BOT GEMINI → mã hoá lại
bằng `LTT_TOKEN_ENCRYPTION_KEY` → INSERT vào bảng `api_keys`. Mang theo `base_url`
+ `supported_models` (gateway cần). **Rủi ro:** secret ở dạng thô trong RAM lúc
chuyển — KHÔNG ghi ra đĩa/log/scratch, chỉ log 4-số-cuối. (Người dùng đã cho phép
nhập toàn bộ key sang.)

## 7. Ba phương án + chấm điểm (thang 100)

Tiêu chí: khớp kiến trúc (Postgres/đa-worker/hợp đồng) 30 · giá trị dùng ngay 25 ·
rủi ro (thấp=điểm cao) 20 · công sức (ít=điểm cao) 15 · mở rộng tương lai 10.

| PA | Mô tả | Khớp KT | Giá trị | Rủi ro | Công sức | Mở rộng | **Tổng** |
|---|---|---|---|---|---|---|---|
| **A. Chép nguyên BOT GEMINI** (JSON + pool RAM) | Port gần như y nguyên | 6/30 | 18/25 | 8/20 | 13/15 | 5/10 | **50** |
| **B. Tối giản: chỉ Gemini + CRUD** | 1 bảng key, chỉ provider Gemini, không pool/cascade | 24/30 | 16/25 | 18/20 | 14/15 | 5/10 | **77** |
| **C. Port đầy đủ** (bảng + registry + pool + cascade + cost + telemetry) | Làm hết một lần | 27/30 | 24/25 | 9/20 | 5/15 | 10/10 | **75** |
| **D. Nền tảng theo pha (đề xuất)** | Bảng key + Model Registry + allocator gọn (SKIP LOCKED) + menu APIKEYS + import; hoãn telemetry/cascade | 29/30 | 24/25 | 17/20 | 11/15 | 9/10 | **90** |

**A** sai kiến trúc (đa-worker sẽ lệch). **B** đúng nhưng thiển cận (phải làm lại
khi thêm provider). **C** đúng nhưng ôm telemetry/cascade khi mới có ≤2 key/loại —
rủi ro + công sức cao, lợi ích chưa cần. **D** lấy phần lõi đúng đắn của C, cắt
phần chưa cần → tối ưu.

## 8. Phương án đề xuất: **D — Bộ máy APIKEYS theo pha**

**Pha 1 (xây sau khi duyệt) — nền tảng dùng được ngay:**
1. `platform_core/api_keys.py` + bảng `ApiKey` (mục 3), mã hoá bằng
   `LTT_TOKEN_ENCRYPTION_KEY`; migration.
2. `platform_core/providers.py` — **Provider Registry** (một chỗ): provider →
   {auth_style, base_url mặc định, categories, danh sách model, cách list-model}.
3. `platform_core/api_pool.py` — **allocator gọn**: `lay_key(provider, model)` chọn
   key active theo `priority`, bỏ key `cooldown/disabled`, khoá bằng UPDATE nguyên
   tử; `danh_dau_loi/thanh_cong` (401/403→disable sau 5, 429→cooldown, 4xx→không
   phạt). Chưa cần rpm/tpm/telemetry.
4. **Menu quản trị APIKEYS** (sqladmin ModelView + view tuỳ biến): danh sách theo
   4 category, thêm/sửa (chỉ `key_preview`), **Test key** (probe sống), bật/tắt,
   reset cooldown; view **Models** (registry) + nút "Làm mới model" (provider có
   list endpoint).
5. **Import 6 key** từ BOT GEMINI (mục 6) — script một lần.
6. **Đấu thumbnail** dùng bộ máy key thay cho env `GEMINI_API_KEY`.

**Pha 2 (sau, khi có nhiều key/loại):** telemetry rpm/tpm/token, cascade đa-provider
theo category, "làm mới model" tự động, quyết toán credit theo usage nâng cao.

**Kết quả Pha 1:** admin quản lý mọi key ở một chỗ, thêm loại API sau này chỉ là
thêm 1 dòng Provider Registry + (tuỳ) 1 adapter; app không giữ key nữa.
