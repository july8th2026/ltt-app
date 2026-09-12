# 01 — Di sản Multi-Job: phân loại từng phần (Gate R1)

> Nguồn: nhánh `claude/ltt-llm-multijob-audit-43efd3` @ `b3b11dbc` (9 commit trên `9e73bf1f`) + WIP chưa
> commit ở cây `.claude/worktrees/ltt-llm-api-http-guide-a3e123`. Tài liệu gốc của chương trình đó:
> `docs/multijob/*` + `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` **trên nhánh đó**
> (chưa có trong nhánh này). Tài liệu này KHÔNG chép lại quyết định cũ — nó phân loại chúng.
>
> Nhãn: `KEEP` · `KEEP + GENERALIZE` · `MODIFY` · `SUPERSEDED` · `UNFINISHED` · `BROKEN` · `UNKNOWN`.

## 0. Ba sự thật đổi cách đọc mọi dòng dưới

1. **Nền cũ.** Toàn bộ Multi-Job nằm trên `master` 07/09, sau trunk `admin-mvp-v3` 450 commit, trong đó
   Scheduler V1 sửa `jobs.py`/`job_runner.py`/`models.py`. Không dòng nào dưới đây đã được kiểm trên trunk.
2. **Build cũ.** R-1/M-1/M-2 đo trên llama.cpp **b10689**; production đã là **b10883** từ 09-11.
3. **Test chưa chạy lại.** Phiên này không chạy lại test T1–T8 (lý do: `00_CURRENT_BASELINE.md` §7).
   Cột "Bằng chứng" dưới đây là commit + đọc mã, **không phải** kết quả test mới.

## 1. Quyết định đã khoá của Multi-Job

| ID | Nội dung (tóm) | Nhãn | Căn cứ / việc còn phải làm |
|---|---|---|---|
| D-01 B | Song song thật `--parallel N` + continuous batching | **KEEP + GENERALIZE** | Đích C4 cho **mỗi** model; áp cho pool 5060 Ti |
| D-02 | Ngân sách KV động + CHỜ (không cắt cứng mỗi slot) | **KEEP + GENERALIZE** | Một sổ ngân sách **mỗi pool**; engine vẫn không admission theo KV (kiểm lại ở b10883) |
| EC-1 | Số "1.000 tok/s @64" là vLLM, không phải llama.cpp | KEEP | Bài học bằng chứng |
| D-09a | Qwen3.8 **chỉ** chạy 3090; 5060 Ti để model khác | **KEEP** | Prompt mới điền "model khác" = Qwen3.5-9B (LTT-3.5) — nhất quán |
| P0-GPU-PIN | Ghim UUID 3090 trong yaml | **KEEP — UNFINISHED (chưa deploy)** | Cần thêm ghim UUID 5060 Ti cho LTT-3.5 |
| TD-4 | Engine `-np 4 -kvu`, pool 204.800, giữ draft-mtp | **MODIFY** | Số đo ở b10689, desktop còn trên 3090. Đích mới 262.144 trên 3090 chuyên dụng ⇒ đo lại ở b10883 |
| TD-5 | Admission ngân sách KV bắt buộc trước N>1 | **KEEP** | Điều kiện an toàn (đường "giết mọi slot") — kiểm lại mã b10883 |
| TD-6 | Whale = token prefill **mới** | **KEEP + GENERALIZE** | Ngưỡng phải theo model (9B prefill nhanh hơn 27B) |
| D-05 D | ≤1 whale, whale nhường ≤30 s rồi chặn; `-b` giữ mặc định | **KEEP + GENERALIZE** | Tham số theo pool |
| D-06 C | Stream: 200 + SSE ngay, nhịp tim, chờ ≤5 phút; giữ tiền **sau** nhận | **KEEP** | Áp nguyên cho cả hai model |
| TD-7 | Cửa đồng bộ: chờ trước header ≤60 s rồi 429 | **BROKEN (lệch khi code)** | WIP T9 **không chờ**: *"`idempotency.begin` giữ `pg_advisory_xact_lock` suốt giao dịch request… chờ ở đây là treo request trùng khoá"*. Lệch khỏi quyết định khoá mà chưa có REOPEN ⇒ cần chủ dự án chốt |
| D-03 A | Hai lớp TƯƠNG TÁC > NỀN, nền ≤ N−1 slot | **MODIFY** | Trunk có Scheduler V1: `priority_class internal > external` trên `jobs`. Hai thang ưu tiên khác nghĩa trên cùng hàng ⇒ phải hợp nhất |
| TD-8 | Trần tài khoản `ceil(N/2)` khi có người chờ | KEEP + GENERALIZE | Theo pool |
| TD-9 | Hủy = GPU dừng + nhả slot + nhả ngân sách + tiền chốt | **KEEP** | (c) hủy cứng job chưa làm (T11) |
| TD-10 | Quan sát qua `/metrics` + `/slots` + phòng chờ | KEEP + GENERALIZE | Theo pool + UUID |
| TD-11 | `--cache-ram` nâng khỏi 8.192 MiB ("máy B 128 GB") | **MODIFY** | Máy B **224 GB** (đo 09-11) |
| D-08 A | MỘT hồ sơ gộp text+vision, 4 slot, pool 204.800, biên 374 MiB | **KEEP hướng · SUPERSEDED số** | Khớp ưu tiên "A. unified VLM profile" của prompt. Biên 374 MiB đo khi desktop còn trên 3090 + b10689; đích 262.144 ⇒ đo lại |
| TD-12 | Hồ sơ dự phòng pool nhỏ + cảnh báo VRAM < 300 MiB | KEEP + GENERALIZE | Mỗi pool một bản |
| D-10 A | Rollout nhanh có kiểm soát, rollback = một con số | **KEEP** | Mở rộng: cờ tắt Dual-model ⇒ về đường cũ |
| TD-14 | Ngưỡng: C1 ≥ 54, C4 ≥ 100 tok/s, 0 tràn/OOM/thu hai lần… | **MODIFY** | Mốc C1 đổi theo b10883 (70–73 tok/s theo ghi nhận ship P6); thêm bộ ngưỡng LTT-3.5 |

## 2. Mã đã commit (T1–T8)

| Task | Commit | Tệp chính | Nhãn | Ghi chú |
|---|---|---|---|---|
| T1 ghim GPU | `8dbedd13` | `llm_gateway/deploy/llama-swap.yaml`, `tests/test_1200_ghim_gpu_may_b.py` | **KEEP** | Chưa deploy. Test số 950 (đổi thành 1200, Task 1.2) **trùng** `test_950_wf_dinh_nghia.py` trên trunk |
| T2 một nguồn số slot | `ab4d998e` | `apps/ltt_llm/{manifest,ngan_sach}.py`, `platform_core/{registry,public_api/catalog}.py`, `test_1201` | **KEEP + GENERALIZE** | `ToolSpec.admission_token_pool` là bổ sung hợp đồng app đúng luật. Hiện MỘT pool `POOL_KV_MAY_B` ⇒ phải theo model |
| T3 mô hình + migration | `fd9b41b3` | `platform_core/models.py` (4 cột lease + `llm_waiters`), `alembic/…20260911_1200_llm_multijob_ngan_sach.py`, `governance.py`, `restore_drill_schema.py`, `test_1202` | **KEEP · MODIFY khi hợp nhất** | Migration nối head cũ ⇒ multi-head trên trunk; `models.py` trunk +530 dòng |
| T4 `luat_nhan.xet()` | `1c5cb232` | `platform_core/llm/luat_nhan.py`, `tham_so_da_luot.py`, `test_1203` | **KEEP** | Hàm thuần tham số hoá `ThamSo(so_slot, pool)` ⇒ dùng lại nguyên cho pool thứ hai |
| T5 `admission.xet_va_giu()` | `a2518468` | `platform_core/llm/admission.py`, `test_1204` | **KEEP** | Advisory lock theo `resource` ⇒ hai resource = hai khoá độc lập |
| T6 phòng chờ | `739ba02d` | `platform_core/llm/phong_cho.py`, `test_1205` | **KEEP** | |
| T7 `uoc_moi` | `0e3305a7` | `platform_core/llm/uoc_moi.py`, `test_1206` | **KEEP** | Ước qua `executor.estimate_input` ⇒ kiểm tokenizer 9B vs 27B |
| T8 cửa stream D-06 | `b3b11dbc` | `runtime_noi_bo/luong.py` (+339), `server/api/streaming.py`, `su_kien_loi.py`, `llm/thanh_toan.py`, `test_272` | **KEEP** | Lệch nhỏ: test dự kiến `test_957_cua_stream_cho.py` không tạo, phủ vào `test_272`. `streaming.py` trunk đổi +10 |

## 3. WIP chưa commit (Task 9)

Diff WIP nguyên bản đã được đối soát theo từng tệp trong `CMC_SOURCE_STATE.md`.
Bản patch lưu trữ không được đưa vào lịch sử canonical để tránh một nguồn sao
chép có thể bị áp lại về sau.

| Phần | Nhãn | |
|---|---|---|
| `tham_so_da_luot.luat_cho()` — một phép tính đặt chỗ cho mọi cửa | **KEEP** | Gom 5 bản sao ⇒ 1 |
| `job_runner._luat_cho_job` — lớp `nen` + ước token; ước hỏng ⇒ đặt chỗ CẢ POOL | **KEEP · MODIFY khi hợp nhất** | `job_runner.py` trunk đổi (Scheduler V1) |
| `chat.py`/`_mot_cuc` mang lớp + đặt chỗ, **không chờ** | **UNFINISHED + lệch TD-7** | Cần quyết định |
| Planner lớp `noi_bo` | **UNFINISHED** | Chưa chạm |
| `tests/test_958_cua_dong_bo_job_planner.py` | **UNFINISHED** | Chưa có (và số 958 trùng trunk) |

## 4. Chưa làm

| Task | Nhãn | Ảnh hưởng của đích Dual-Model |
|---|---|---|
| T10 gateway sổ token + whale + `/v1/huy` + log từng lượt | UNFINISHED | Phải thiết kế **theo model** ngay (gateway hôm nay một bộ đếm cho mọi model) |
| T11 hủy cứng job | UNFINISHED | Không đổi |
| T12 quan sát | UNFINISHED (một phần ở T3) | Thêm UUID/pool/residency |
| T13 engine 4 slot hồ sơ gộp | UNFINISHED · **số SUPERSEDED** | 262.144 + b10883 + hồ sơ LTT-3.5 |
| T14 tài liệu + runbook | UNFINISHED | Hợp nhất với tài liệu Dual |

## 5. Tài liệu & dụng cụ

| Thứ | Nhãn |
|---|---|
| `docs/multijob/00_BASELINE.md` (M-1/M-2) | **KEEP như lịch sử** — số là của b10689, desktop trên 3090, RAM ghi sai 128 GB |
| `docs/multijob/04_RUNTIME_CAPABILITY_MAP.md` (R-1 b10689) | **MODIFY** — kiểm lại ở b10883 (→ `05_COMMUNITY_EVIDENCE.md`) |
| `docs/multijob/05_COMMUNITY_EVIDENCE.md` | KEEP + bổ sung (Qwen3.5-9B, llama-swap đa model, Docling) |
| `docs/multijob/artifacts/m1/m1_bench.py`, `m2_bench.py` (Scheduled Task + pythonw + nhịp tim) | **KEEP + GENERALIZE** — khuôn đo máy B đã chạy được; tham số hoá GPU/model |
| `docs/multijob/DECISION_LOG.md` | **KEEP** — nguồn của quyết định cũ; quyết định MỚI ghi ở `docs/ltt_llm_dual/DECISION_LOG.md`, đổi quyết định cũ đi bằng `DECISION REOPEN REQUEST` |
