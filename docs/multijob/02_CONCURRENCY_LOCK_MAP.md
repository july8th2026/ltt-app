# 02 — Bản đồ khoá đồng thời (REMOVE / MODIFY / KEEP)

> Không đổi đồng loạt `1 → 4`. Mỗi chốt được phân loại theo việc nó bảo vệ.

| Chốt | Nơi | Bảo vệ gì | Phân loại | Vì sao |
|---|---|---|---|---|
| `admission_slots=1` | `apps/ltt_llm/manifest.py:197` | số lượt đồng thời tới máy B (cả sync/stream/job) | **MODIFY** → dẫn xuất `SO_SLOT_MAY_B` | một chỗ điều khiển cả 3 cửa; phải cùng nguồn với engine |
| `DONG_THOI_MAY_B = 1` | `apps/ltt_llm/ngan_sach.py` | bản sao (C-02 của audit) | **MODIFY** → `SO_SLOT_MAY_B` (một nguồn) | "hai chỗ khai cùng một điều" |
| `ExecutionLease` `UNIQUE(resource, slot)` | `platform_core/models.py:369-388`, `admission.py:59-104` | cấp slot nguyên tử liên tiến trình | **KEEP** + **MODIFY** (thêm `lop`, `token_dat_truoc`, `token_prefill_moi`, `la_whale`; luật nhận trong advisory lock) | đã hỗ trợ `slots>1`; thiếu ngân sách token |
| `ORPHAN_TIMEOUT` 20 phút + heartbeat 60 s | `admission.py:22-23` | lease mồ côi | **KEEP** | lưới cuối, càng nhiều slot càng cần |
| `GioiHan` `max_dong_thoi=1` | `llm_gateway/gioi_han.py:101-104`, `config.py:136` | máy B khỏi chính máy A (retry, worker nhân đôi, script tay) | **MODIFY** → N + sổ token **đúng** (`/tokenize`) + ≤1 whale | phòng thủ theo tầng có chủ ý (`gioi_han.py:4-8`); không gỡ |
| Thu hồi suất treo `HAN_GIU_MAC_DINH_S=1200` | `gioi_han.py:47,184-217` | sự cố 31/08 | **KEEP** | `test_363` |
| `--parallel 1` | `llm_gateway/deploy/llama-swap.yaml:116` | lý do ghi tại chỗ: spec-decode một luồng | **MODIFY** → `--parallel N -kvu` | M-1: lý do không đúng trên 3090 |
| Không khai `groups` (một model một lúc) | `llama-swap.yaml:206-208` | chống OOM 43 GB | **KEEP** | vẫn một model; nay chỉ còn một hồ sơ |
| Hai hồ sơ `qwen38-api` / `qwen38-vision` | `llama-swap.yaml` | text 200K vs vision | **REMOVE** hồ sơ vision riêng → `aliases` | D-08 A; đổi hồ sơ giết lượt đang chạy |
| Trọng tài GPU (`trong_tai.py`), dọn card (`don_dep.py`), `tren_gpu.py` | `llm_gateway/` | chia card với ComfyUI/app khác | **KEEP** | quy chủ VRAM bất khả (`used_memory=[N/A]`, D-03-3) |
| `gpu_claims` PRIORITY cấp máy | `platform_core/gpu_claims.py:113-120` | điều phối liên hệ thống chống TDR | **KEEP** (không dùng cho LLM lane) | khác tầng |
| `gpu_lease` độc chiếm card | `platform_core/gpu_lease.py` | GPU **máy A** cho job cục bộ | **KEEP** (không liên quan máy B) | — |
| `threading.BoundedSemaphore(so_suat)` | `voice_sidecar/engine.py:93-94` | LTT Voice | **KEEP** — ngoài phạm vi | khác tài nguyên |
| Trần hàng `global_queue_limit=100`, `resource_queue_limits`, `max_active_jobs=5`, `class_concurrency` | `platform_core/public_api/config.py:148-184`, `limits.py:303-366` | backpressure cửa job | **KEEP** | đã đúng |
| Phép kiểm cứng số 1 | `tests/test_313_llm_admission.py:33-43`, `tests/test_363_suat_khong_ro.py` (`GioiHan(max_dong_thoi=1)`) | ghim hành vi | **MODIFY** → đọc `SO_SLOT_MAY_B` | đổi số mà không đổi test là gate đỏ |
