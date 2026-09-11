# LTT_LLM đa job — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> ⚡ **Bản RÚT GỌN theo yêu cầu chủ dự án (2026-09-11):** "cứ xây dựng code, xây log lưu; sau phiên
> tôi mở vận hành thật; một thời gian sau phân tích để tối ưu". Plan liệt kê task · file · giao diện ·
> phép kiểm; mã chi tiết nằm trong commit của từng task. Hai thứ KHÔNG cắt: ngân sách KV trước N>1,
> và bất biến tiền.

**Goal:** Máy B phục vụ 4 lượt Qwen song song thật, có phòng chờ công bằng, ưu tiên tương tác, bảo vệ
prompt dài, hủy thật, và sổ từng lượt bền 30 ngày để phân tích sau.

**Architecture:** Một mặt phẳng admission ở máy A (hàm luật thuần `luat_nhan` + sổ `ExecutionLease`
mở rộng + phòng chờ/sổ lượt `llm_waiters`), gateway máy B là chốt fail-closed có sổ token riêng,
llama-swap một hồ sơ gộp `-np 4 -kvu --mmproj` ghim UUID 3090.

**Tech Stack:** Python 3.13, FastAPI/Starlette, SQLAlchemy + Alembic (PostgreSQL prod, SQLite test),
httpx, llama.cpp b10689 + llama-swap v250 trên Windows.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` · quyết định: `docs/multijob/DECISION_LOG.md`

## Global Constraints

- `platform_core` **không import `apps/`**; app → nền tảng qua `ToolSpec` (thêm `admission_token_pool`).
- Cấu hình ghi **không BOM**; `.ps1` **ASCII thuần**; không Python inline qua PowerShell (CLAUDE.md 1–3).
- Không `pytest` toàn kho. Một tệp test: `python -m pytest tests/<tệp> -q`. Vòng lặp: `python tools\gate.py --doi`.
  Trước khi báo xong: `python tools\cua_so_yen.py trang-thai` rồi `python tools\gate.py`. Trần `-n 6`.
- Dải test mới của chương trình: **1200–1249** (đổi 2026-09-11: 950–969 trùng chương trình Workflow trên trunk) (ghi vào bảng cấp phát `docs/KE_HOACH_TRIEN_KHAI.md`).
- Mọi con số (N, pool, ngưỡng) dẫn xuất từ `apps/ltt_llm/ngan_sach.py`; bản sao phía máy B có phép kiểm đối chiếu.
- Bận = 429/chờ, không bao giờ đánh dấu khoá hỏng (INV-004/013). Hủy do người dùng = 499, không phải 502.
- Bảng mới: `Store(...)` trong `platform_core/public_api/governance.py` + hàm dọn thật + tên UNIQUE vào
  `tools/restore_drill_schema.py`.

## File map

| File | Trách nhiệm | Task |
|---|---|---|
| `llm_gateway/deploy/llama-swap.yaml` | ghim UUID 3090; một hồ sơ gộp `-np N -kvu --mmproj`; `--metrics` | 1, 13 |
| `apps/ltt_llm/ngan_sach.py` | `SO_SLOT_MAY_B`, `POOL_KV_MAY_B`, ngưỡng whale/chờ | 2 |
| `platform_core/registry.py`, `public_api/catalog.py` | `ToolSpec.admission_token_pool` + chiếu (không lộ ra khách) | 2 |
| `platform_core/models.py` + `alembic/versions/…_llm_multijob.py` | cột lease mới; bảng `llm_waiters` (phòng chờ + sổ lượt) | 3 |
| `platform_core/llm/luat_nhan.py` (mới) | hàm thuần quyết định nhận | 4 |
| `platform_core/llm/admission.py` | `xet_va_giu()` trong advisory lock; `acquire()` tương thích ngược | 5 |
| `platform_core/llm/phong_cho.py` (mới) | vào/chờ/rời/dọn; sổ lượt | 6 |
| `platform_core/llm/uoc_moi.py` (mới) | ước token prefill mới (nhận diện lượt tiếp) | 7 |
| `platform_core/llm/thanh_toan.py` | `du_so_du()` (kiểm trước 200, không giữ) | 8 |
| `platform_core/runtime_noi_bo/luong.py`, `server/api/streaming.py`, `server/api/su_kien_loi.py` (mới) | cửa stream D-06 | 8 |
| `server/api/chat.py` | cửa đồng bộ TD-7 | 9 |
| `platform_core/job_runner.py`, `platform_core/agent/planner.py` | lớp `nen`/`noi_bo` + token | 9 |
| `llm_gateway/gioi_han.py`, `api.py`, `config.py`, `upstream.py` | sổ token + whale + `/v1/huy` + log từng lượt | 10 |
| `platform_core/llm/cong_vlm.py`, `dieu_phoi.py`, `luong_vlm.py`, `huy_luot.py` (mới), `apps/ltt_llm/jobs.py`, `features.py` | hủy cứng job (TD-9c) | 11 |
| `platform_core/job_metrics.py`, `job_runner.py` (bảo trì) | quan sát + dọn | 12 |
| `docs/QUYET_DINH_NEN_TANG.md`, `docs/KE_HOACH_TRIEN_KHAI.md`, `docs/NHAT_KY.md`, `docs/multijob/RUNBOOK.md` | giao thức đổi quyết định + runbook | 14 |

## Tasks

- [ ] **Task 1 — P0 ghim GPU (Pha 0).** Đồng bộ `llama-swap.yaml` với bản đang chạy trên máy B (khối
  `--metrics`), thêm `env: ["CUDA_VISIBLE_DEVICES=GPU-26623278-4fa5-82db-4306-237651b03e78"]` cho mọi
  hồ sơ. Test `tests/test_1200_ghim_gpu_may_b.py`: mọi model có env UUID; `--metrics` có mặt.
- [ ] **Task 2 — Một nguồn cho số slot.** `SO_SLOT_MAY_B`, `DONG_THOI_MAY_B` = bí danh, `POOL_KV_MAY_B`;
  `ToolSpec.admission_token_pool`; manifest đọc ngan_sach; chiếu catalog không lộ khoá mới. Test
  `tests/test_1201_mot_nguon_so_slot.py`; sửa `test_313:33-43` so với `SO_SLOT_MAY_B`.
- [ ] **Task 3 — Mô hình + migration.** 4 cột mới trên `ExecutionLease`; bảng `llm_waiters` (phòng chờ +
  sổ lượt: cửa, lớp, token, whale, `created_at/heartbeat_at/admitted_at/finished_at`, `trang_thai`,
  `ly_do_cho`, `so_nhip`, `ket_qua`, `lease_id`); governance `Store` OPERATIONAL 30 ngày; drill UNIQUE.
  Test `tests/test_1202_so_ngan_sach_mo_hinh.py`.
- [ ] **Task 4 — `luat_nhan.xet()` thuần.** Luật §5 spec: slot · ngân sách · nền ≤ N−1 & nhường tương
  tác · trần tài khoản khi có người chờ · ≤1 whale, whale nhường ≤30 s rồi chặn · FCFS chặt (bỏ qua
  người chỉ bị trần tài khoản / whale đang nhường). Test `tests/test_1203_luat_nhan.py` (mỗi luật một ca +
  đối chứng).
- [ ] **Task 5 — `admission.xet_va_giu()`.** Advisory lock `llm-admission:<resource>` (PostgreSQL), chụp
  lease + người chờ, gọi `luat_nhan`, INSERT; `acquire()` giữ nguyên hành vi khi `token_pool=0` và
  không có `lop`. `hold_persisted(**kw)` chuyển tiếp. `xoa_co_whale(lease_id)`. Test
  `tests/test_1204_admission_ngan_sach.py`; hồi quy `test_313`, `test_363`, `test_389`.
- [ ] **Task 6 — `phong_cho`.** `kiem_phong` (PhongDay trước 200), `vao`, `cho_nhan` (generator: yield lý
  do mỗi nhịp, `return lease_id`; HetCho; đóng ⇒ `roi`), `cho_nhan_chan`, `ghi_ket_thuc`, `don_het_han`.
  Đồng hồ tiêm được. Test `tests/test_1205_phong_cho.py`.
- [ ] **Task 7 — `uoc_moi.uoc_token_moi()`.** Chuỗi băm tiền tố tin nhắn theo tài khoản (LRU trong tiến
  trình). Test `tests/test_1206_uoc_token_moi.py`.
- [ ] **Task 8 — Cửa stream (D-06).** `thanh_toan.du_so_du`; `luong.tien_kiem` (alias/đầu vào/413/402/
  phòng đầy — trước 200), `luong.vao_va_cho` (chờ → nhận → **giữ tiền sau nhận**), `luong.luong_co_cho`
  (nhịp tim `: ltt-cho` 15 s, lỗi đúng khuôn giao thức sau 200, xoá cờ whale ở byte đầu);
  `streaming.py` facade dùng nó; `chuan_bi()` giữ nguyên ngữ nghĩa cũ cho các test ghim; `mo_luong`
  (ChatLTT) phát `response.queued`. Test `tests/test_957_cua_stream_cho.py` (HTTP thật qua `TestClient`:
  402/413/429 trước 200; đang chờ ⇒ 0 dòng giữ tiền; hết chờ ⇒ sự kiện lỗi, 0 khoản treo).
- [ ] **Task 9 — Cửa đồng bộ + job + planner.** `chat.py`: chờ trước header trong ngân sách thời gian còn
  lại (≤60 s) rồi 429. Worker: lớp `nen` + token ước qua executor. Planner: lớp `noi_bo`, không chờ. Test
  `tests/test_958_cua_dong_bo_job_planner.py`.
- [ ] **Task 10 — Gateway máy B.** `GioiHan(token_pool=…)`: `cap_suat(token_dat_truoc, la_whale)`,
  ≤1 whale, `Suat.xoa_whale()`; api đọc `X-LTT-Request-Id`/`X-LTT-Whale`; `/v1/huy` ⇒ đóng thượng
  nguồn, trả **499**; `upstream.json` hủy được; một dòng log có cấu trúc mỗi lượt; env
  `LTT_LLM_TOKEN_POOL`. Test `tests/test_959_gateway_ngan_sach.py`; hồi quy `test_250`, `test_363`.
- [ ] **Task 11 — Hủy cứng job.** `cong_vlm`: 499 ⇒ `HuyError` (không phải `CongVlmError`); `dieu_phoi`:
  không cascade, không đánh lỗi khoá; header `X-LTT-Request-Id`; `huy_luot.huy(ma_luot)`; `jobs.py` luồng
  canh `is_cancelled()` 1 s ⇒ huỷ ⇒ `JobCancelled`. Test `tests/test_960_huy_cung_job.py`.
- [ ] **Task 12 — Quan sát + dọn.** `job_metrics.snapshot` thêm khối `llm_phong_cho`; bảo trì gọi
  `phong_cho.don_het_han`; gateway `/health` thêm `token_dat/pool/whale`. Test `tests/test_961_quan_sat_phong_cho.py`.
- [ ] **Task 13 — Pha 2: engine 4 slot.** `SO_SLOT_MAY_B = 4`; yaml một hồ sơ `qwen38-api` + `--parallel 4
  -kvu --mmproj … --cache-ram 32768`, `aliases: [qwen38-vision]`; gateway mặc định `LTT_LLM_MAX_DONG_THOI`
  = 4, `LTT_LLM_TOKEN_POOL` = 204800; `test_334` + `test_250` đối chiếu. Test `tests/test_962_ho_so_gop_da_slot.py`.
- [ ] **Task 14 — Tài liệu + runbook.** Q mới trong `QUYET_DINH_NEN_TANG.md` (đổi D-03-7 của audit),
  dải test 950–969, `NHAT_KY.md`, `docs/multijob/RUNBOOK.md` (deploy A+B, restart llama-swap, tải tổng
  hợp M-3, canary, truy vấn phân tích sổ lượt, rollback một con số). Gate đầy đủ. Commit.

## Rollback
`SO_SLOT_MAY_B = 1` (+ yaml trước) — xem `10_ROLLBACK_PLAN.md`. Pha 1 đúng ở N = 1.
