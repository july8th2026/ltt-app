# 02 — Đường request, hợp đồng model, tiền, hủy, đầu vào (máy A)

> Audit tĩnh trên `9e73bf1f`, 2026-09-11. Trunk `admin-mvp-v3` đi trước 450 commit (Scheduler V1
> đổi `jobs.py`/`job_runner.py`) — kiểm lại trên trunk trước khi sửa. `[INFERRED]` = suy luận.
> Bản cũ hơn cùng chủ đề: `docs/multijob/01_REQUEST_TRACE.md` (nhánh Multi-Job).

## 1. Hợp đồng model công khai hôm nay

| Tầng | Tên | Chỗ khai |
|---|---|---|
| Bí danh công khai | `ltt_llm` → `qwen38-api` · `ltt_llm_vision` → `qwen38-vision` | `apps/ltt_llm/manifest.py:202,235-262`; lặp ở `apps/ltt_llm/features.py:41-46` (`ALIAS_SANG_ID`, `MODEL_MAC_DINH`) |
| Tool / job | `text.chat` / `ltt_llm.chat` | `manifest.py:193` |
| Tên cho Claude Desktop | `ltt-llm-claude-compat` → `ltt_llm` | `server/api/streaming.py:82` |
| Provider | `ltt_llm` (models `qwen38-api`, `qwen38-vision`) | `platform_core/providers.py:213-260` |
| Gateway / engine | `HO_SO` | `llm_gateway/catalog.py:93-106`, `llama-swap.yaml` |
| Mẫu / CLI | `CHAT_MODEL="ltt_llm"` | `platform_core/public_api/examples.py:236,525` |

`/v1/models`, `/tools`, bộ chọn model ChatLTT đều **dẫn xuất từ manifest** (`catalog.py:353`,
`server/api/tools.py:141`, `runtime_noi_bo/danh_muc.py:176-179`, `frontend/chatltt/src/App.tsx:178,408-415`).
Ánh xạ: bí danh → `executor.model_id()` (`apps/ltt_llm/executor.py:50`) → `dieu_phoi.goi(...)`
(`features.py:258-264`); stream đặt `gui["model"]` (`luong.py:192-193`, `streaming.py:570`).
Text/vision chỉ khác **id nội bộ**; hôm nay khách phải **chọn** giữa hai bí danh.

Số lệch đã thấy: `ngan_sach.CUA_SO_MODEL_VISION = 131_072` nhưng `providers.py:251` còn `65_536`.

## 2. Mọi cửa tới model nhà

| Cửa | Kiểu | Tầng đi qua | Khi bận |
|---|---|---|---|
| `/chat/completions` (`server/api/chat.py:188-231`) | sync | idempotency → rate → `admission.acquire(mode="sync")` → giữ tiền → gateway `GioiHan` | lease hết ⇒ **429** (`limits.py:138`); máy B `BanError` ⇒ hoàn + **503** |
| `/messages`, `/responses` không stream (`streaming.py:174-360` `_mot_cuc`) | sync | như trên | 429 / 503 |
| `/messages`, `/responses` stream (`streaming.py:642-707` → `luong.chuan_bi`/`mo_thuong_nguon`) | SSE | acquire(stream) → giữ tiền → `luong_vlm.mo` | slot hết ⇒ 429; máy B 429 ⇒ 503 + Retry-After; 413 giữ 413 |
| ChatLTT (`apps/chatltt/services/luot.py:259`, `luot_v3.py`, `chon_giong.py:156`) qua `luong.mo_luong` | stream | như stream | `response.failed code="ban"` |
| Job ChatLTT nghiên cứu (`apps/chatltt/jobs.py:190-219`) | job gọi stream | `jobs` rồi lease mỗi vòng | [INFERRED] đường retry worker |
| `POST /jobs` → `apps/ltt_llm/jobs.py:22` | job | trần hàng (`limits.py:303-366`) → `jobs.claim` fair-share (`jobs.py:206-224`) → `hold_persisted` (`job_runner.py:228-238`) → gateway | lease hết ⇒ trả về hàng có trễ; `BanError` ⇒ `resource_wait` |
| Planner (`platform_core/agent/planner.py:133-169`) | sync nội bộ | `acquire` không chờ → cascade | **rơi sang Gemini** (`PLANNER_PROVIDERS`, `:20`) |

Đường khách **không bao giờ** rơi provider khác (`features.THU_TU_PROVIDER=("ltt_llm",)`,
`luong_vlm.py:10-12`) — khớp luật "không silent fallback" của đích. Không app video/voice/ASV nào gọi
model nhà (ASV dùng Gemini, `apps/autosubvideo/ai_workflows.py:109`).

**Nhiều hơn một quyền xếp hàng (hôm nay):** (a) job xếp theo bảng `jobs`, còn sync/stream **đua**
cùng `ExecutionLease` không xếp hàng ⇒ không gì sắp job so với lượt tương tác; (b) `GioiHan` của gateway
là cổng thứ hai trong bộ nhớ (`max_dong_thoi=1`); (c) nhánh Multi-Job thêm `llm_waiters` cạnh `jobs`
(có chủ ý — phòng chờ cho cửa tương tác, spec §4.2). Trên trunk còn thêm **Scheduler V1** xếp hạng
`jobs` theo `priority_class`.

[INFERRED, cần kiểm trên PostgreSQL] `planner.acquire` chèn lease trong session của caller mà không
commit; `release_by_id` (`:168-169`) mở session mới nên không thấy ⇒ lease có thể mồ côi tới
`ORPHAN_TIMEOUT` (20 phút, `admission.py:22`).

## 3. Tiền — bất biến (GIỮ NGUYÊN)

Giữ: `thanh_toan.giu_cho_luot` (`:79-94`, thiếu `request_id` ⇒ lỗi) · quyết toán `quyet_toan_hoac_hoan`
(`:238-258`, không đo được ⇒ hoàn trọn) · `credit.giu_cho/quyet_toan/hoan` (`credit.py:260,417,463`,
idempotent) · quét giữ treo 6 h / tự hoàn 24 h (`:537,660`). Bận ⇒ hoàn mọi cửa. Stream ngắt ⇒ `finally`
quyết toán theo token đo (`luong.py:345-360`). Job hủy ⇒ hoàn trọn (`job_runner.py:489-500`).
Bất biến: INV-003, INV-011/012 (`docs/audit_ltt_llm/STATE.md`), INV-MJ-1/2 (spec Multi-Job).
Test chốt: test_68, 259, 272, 273, 285, 292, 313, 331, 360, 363, 389, 390.

⚠️ Một bảng giá cho mọi model: `gia_token.py:47-54` (`tinh(su_dung)` không nhận model) — thêm LTT-3.5
buộc phải có giá theo model.

## 4. Hủy

| Giai đoạn | Hôm nay |
|---|---|
| Job đang xếp | cờ CSDL |
| Job đã nhận / prefill / decode | **chỉ hợp tác** (`is_cancelled` ở 5 % và 100 %, `apps/ltt_llm/jobs.py:27,43`); HTTP tới máy B chạy tiếp ⇒ GPU chạy tới hết |
| Stream ngắt | **có truyền**: `luong_vlm._di finally` đóng httpx → gateway `boc_luong` nhả slot → `upstream.close()` ⇒ llama.cpp nhả ≤ 1 s |
| Sync client ngắt | [INFERRED] không truyền (httpx chặn, `timeout_s=90`) |

## 5. Đầu vào / tệp

Ảnh: chỉ `image_url`/`input_image` data URL; ≤ 4 ảnh × 12 MB (`llm_gateway/config.py:126-127`); URL
ngoài bị từ chối; ảnh vào model không vision ⇒ 413. ChatLTT: png/jpeg/webp ≤ 4/lượt
(`apps/chatltt/services/anh_vao.py:44,55`).
Thư viện đã có (`requirements.txt`): `pypdf>=6.17,<7`, `markitdown[docx,pptx,outlook]`. **Không** có
docling/openpyxl/unstructured; **pymupdf bị loại vì AGPL**.
Đường tệp→chữ đã tồn tại: `apps/chatltt/services/trich_van_ban.py:40-67` (PDF theo trang, txt/md/csv/json,
docx/pptx/html qua markitdown, trần 2 M ký tự) chạy thành job `chatltt.trich_tep`
(`apps/chatltt/jobs.py:46,123-175`), rồi `chia_doan` + `tim_doan` (truy hồi). Thuộc app ChatLTT, chưa
phải năng lực nền tảng.

## 6. Chỗ giả định "một model / một pool" (phải chạm khi thêm LTT-3.5)

`DONG_THOI_MAY_B`/`SO_SLOT_MAY_B`/`POOL_KV_MAY_B` một pool (`ngan_sach.py:287`) · `tran_theo_ngu_canh`
dùng cửa sổ text cho mọi bí danh (`:300`), `NEN_CHO_CLIENT = nen_cua("qwen38-api")` (`:198`) · một
resource `"llm_remote"` (`manifest.py:197`, `planner._TAI_NGUYEN_MAC_DINH`, `planner.py:26`) · một bảng
giá (`gia_token.py`) · hằng thời gian 750/40 tok/s đo trên 27B (`features.py:66-67`) · provider id cứng
(`luong_vlm.PROVIDER`, `dieu_phoi.PROVIDER_OPENAI`) · một `LTT_LLM_BASE_URL` · gateway một bộ
`LTT_LLM_*` · `server/api/streaming.py` import thẳng `apps.ltt_llm` (`:48,515`) · `TOOL_CHAT="text.chat"`
· metric/alert khoá `ltt_llm:*` (`ops_alerts.py:92-124`).
