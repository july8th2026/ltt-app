# LTT_LLM đa job — nền bằng chứng (đọc từ mã + audit đã có)

> Ngày 2026-09-11. Nhánh `claude/ltt-llm-multijob-audit-43efd3`, HEAD `9e73bf1f`.
> Tệp này **không chép số** từ nơi khác — nó trỏ tới nguồn chân lý. Số sống ở mã
> và ở `docs/audit_ltt_llm/`; chép lại là mời trôi (xem MEMORY: *"con số không kèm
> cây là con số sẽ bị cãi nhau"*).

## 0. Hai đính chính giả định của prompt (§48 PROMPT ASSUMPTION INVALID)

**AS-1 — "Hệ đang ở chế độ MỘT job, cần xây queue/fairness/priority/cancel/
observability."** ❌ Phần lớn control plane **đã tồn tại và đã được kiểm**:

- Hàng đợi bền đa-worker (`platform_core/jobs.py:185-224`, `SELECT … FOR UPDATE
  SKIP LOCKED`), **không** consumer=1.
- Fairness: aging 5 phút → fair-share theo `(user_id, admission_resource)` → FIFO,
  **không xếp theo tiền** (`jobs.py:206-224`).
- Backpressure 429 nhiều tầng global/resource/account/lane (`public_api/limits.py:289-366`).
- Admission slot lease theo resource, nguyên tử, **đã hỗ trợ `slots>1`**
  (`platform_core/llm/admission.py:59-104`, `for slot in range(slots)`).
- Credit hold/settle/refund idempotent + tự hoàn tiền treo (`job_runner.py:556-825`).
- Hợp đồng admission/queue đã **thiết kế + triển khai** H41.9 Q0-Q3 (2026-08-28):
  `docs/VLM_NOI_BO/ADMISSION_QUEUE_LTT_LLM.md`.

⇒ Việc thật **không phải** "xây control plane", mà là **mở rộng có mục tiêu** một
control plane đã chín, và **quyết định chế độ đồng thời của engine máy B**.

**AS-2 — "1 job là giới hạn phần mềm."** ❌ Nó là **hai tầng cùng đặt = 1** vì lý
do kỹ thuật đo được:

- `--parallel 1` trên `llama-server` (`llm_gateway/deploy/llama-swap.yaml:116`).
  Lý do ghi tại chỗ (`:89-91`): **speculative decoding (MTP draft)** tối ưu một
  luồng — `--parallel 2` chậm ~20%, `--parallel 4` mất hẳn lợi thế spec-decode.
- Phản chiếu ở nền tảng: `admission_slots=1` (`apps/ltt_llm/manifest.py:197`, **một
  chỗ** điều khiển cả sync/stream/job) và gateway `max_dong_thoi=1`
  (`llm_gateway/config.py:136`, env `LTT_LLM_MAX_DONG_THOI`).
- VRAM là ràng buộc phụ: model ~15,3 GB + KV cho ngữ cảnh lớn ⇒ ~22/24,6 GiB khi
  nạp (`docs/audit_ltt_llm/reports/03` §3). `-c 204800` (api) / `131072` (vision),
  KV `q4_0` (`llama-swap.yaml`).

## 1. Ba tầng — đừng nhầm (khớp §15)

```
LTT BUSINESS CONTROL   jobs (durable) + admission ExecutionLease + credit + fairness
        ↓              → ĐÃ CÓ, tái dùng
GATEWAY SAFETY (máy B)  llm_gateway: 413→429→trọng tài→dọn card→chạy; 429≠502;
        ↓              hủy propagate xuống engine bằng đóng httpx → ĐÃ CÓ
ENGINE GPU SCHEDULER    llama-server --parallel/slots/continuous batching/KV/MTP
                        → ĐANG = 1 slot + spec-decode
```

## 2. Đường đi thật của một lượt chat qua máy B

`server/api/{chat,streaming}.py` **hoặc** `platform_core/runtime_noi_bo/luong.py`
(stream nội bộ ChatLTT) **hoặc** worker job (`job_runner.py:229`)
→ `admission.acquire(resource="llm_remote", slots=1)`
→ `credit.giu_cho` → `db.commit()`
→ `platform_core/llm/luong_vlm.mo()` (SSE nguyên xi) hoặc `dieu_phoi.goi()` (nội bộ, có cascade Gemini)
→ HTTP bearer tới `llm_gateway :8299` → `llama-swap :8280` → `llama-server`.

Vượt suất: **sync/stream → 429 + Retry-After 15**; **job → DEFER về queue, không
tốn attempt** (`test_313_llm_admission.py`).

## 3. Khoảng trống THẬT cho đa job (từ audit 3 agent 2026-09-11)

| # | Khoảng trống | Bằng chứng | Hạng |
|---|---|---|---|
| G-1 | **Không có priority / interactive-vs-background.** Chat tương tác không chen được trước batch dài. `mode` chỉ là live/test. | `jobs.py:219-220`, `invocation.py:430` | P1 — lớn nhất |
| G-2 | **Hủy không propagate CỨNG ở tầng job.** Worker chỉ polling hợp tác; stream đang chạy không abort thật khi user hủy job. *(Lưu ý: tầng gateway stream CÓ propagate hủy khi client ngắt — `upstream.close()`.)* | `job_runner.py:110-174` vs `llm_gateway/upstream.py:101-170` | P1 |
| G-3 | **Không preemption** trong business queue (chỉ có ở `gpu_claims` cấp máy). | `gpu_claims.py:113-120` | P2 |
| G-4 | **Per-user quota thô**: chỉ `max_active_jobs`/`class_concurrency`; không theo token/throughput, không đếm stream đồng thời. | `limits.py:311-366` | P2 |
| G-5 | **`admission_slots` tĩnh** theo tool spec, không co giãn theo năng lực GPU. | `invocation.py:472-487` | P2 |
| G-6 | **Engine 1 slot + spec-decode** ⇒ throughput tổng ~1 lượt; đa user = xếp hàng, không song song thật. | `llama-swap.yaml:116,89-91` | **P0 — quyết định D-01** |

## 4. Bằng chứng cộng đồng (đã tải `D:\LTT_VLM_REFS\`, chưa cần clone lại)

- `qwen38-27b-rtx3090/batch/` — **chế độ batch**: ~1.000–1.094 tok/s tổng @ 64
  đồng thời (128 in/512 out), `MAX_SEQS=64`, ngữ cảnh 150K; đối lại single ~46 tok/s.
  ⇒ Có bằng chứng số cho nhánh "đa slot throughput cao".
- `qwen38-mtp/` — sweep RTX 3090, MTP/spec-decode một luồng (nhánh độ trễ thấp hiện tại).
- `bench/conc_ladder.py` — thang đo đồng thời sẵn có (giảm không gian test, §32).
- `llama-swap/` — schema, `/metrics`, `/running`, unload, `groups`.

⇒ Không cần đo lại: single-user spec-decode ≈ hiện trạng đã có mốc; batch-mode đã
có số cộng đồng. Cần đo trên MÁY B thật chỉ khi chọn nhánh đổi engine (§41 Need
local test = chỉ cho nhánh được chọn).

## 5. Nguồn chân lý để không chép lại

- Audit đầy đủ 8 pha (CONDITIONAL PASS 81/100): `docs/audit_ltt_llm/STATE.md` +
  `reports/00-08`.
- Hợp đồng admission/queue: `docs/VLM_NOI_BO/ADMISSION_QUEUE_LTT_LLM.md`.
- Sự cố rò suất 31/08 (bài học cancel/lease): `docs/VLM_NOI_BO/SU_CO_2026-08-31_RO_SUAT.md`.
- Ngữ cảnh dài đo 03/09: `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md`.
