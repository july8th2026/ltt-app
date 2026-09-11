# LTT_LLM đa job — Design Spec (V3)

> **Trạng thái:** DESIGN LOCKED 2026-09-11 (chủ dự án duyệt từng phần 1/4–4/4 + bảng khoá cuối).
> **Nhánh:** `claude/ltt-llm-multijob-audit-43efd3` (HEAD lúc viết `9e73bf1f`).
> **Nguồn:** mã hiện tại + đo thật trên máy B + thượng nguồn/cộng đồng + quyết định chủ dự án.
> Mọi quyết định và căn cứ: `docs/multijob/DECISION_LOG.md`. Bằng chứng: `docs/multijob/00_BASELINE.md`
> (M-1, M-2, tải thật), `04_RUNTIME_CAPABILITY_MAP.md` (llama.cpp b10689), `05_COMMUNITY_EVIDENCE.md`.
> Tài liệu này **không chép số chân lý của hệ** — nó trỏ về `apps/ltt_llm/ngan_sach.py` và mã.

---

## 1. Mục tiêu và phi mục tiêu

**Mục tiêu.** Máy B (RTX 3090, Qwen3.8-27B, llama.cpp b10689) phục vụ **nhiều lượt đồng thời thật**
cho ChatLTT, Public API (sync/stream/job), agent (Codex/Claude Code) và việc nền — với ưu tiên, công
bằng, bảo vệ ngữ cảnh dài, backpressure có trần, hủy thật, quan sát được, không OOM, không thu hai lần,
rollback bằng một giá trị cấu hình.

**Phi mục tiêu (đợt này).** Không migrate vLLM/SGLang. Không viết bộ lập lịch GPU bằng Python (slot,
batching, KV, MTP là việc của engine). Không preemption (llama.cpp không hỗ trợ an toàn). Không bộ
phân bổ token theo từng bước. Không dùng RTX 5060 Ti cho Qwen (D-09a). Không đổi trần ngữ cảnh công bố
cho vision (quyết định sản phẩm, để sau). Không vá C++ llama.cpp (patch 0011 của lab là tham chiếu).

## 2. Hai đính chính giả định (§48)

1. **Control plane đa job đã có** — hàng `jobs` bền đa-worker, fair-share + aging, trần 429 nhiều tầng,
   `ExecutionLease` đã hỗ trợ `slots>1`, credit hold/settle/refund idempotent (H41.9 Q0–Q3). Việc thật là
   **mở rộng có mục tiêu**, không xây mới.
2. **"1 job" không phải trần vật lý.** M-1: `-np 4 -kvu -c 204800` vừa 22.965/24.576 MiB, C1 không đổi
   (59,9→62,7 tok/s), C4 tổng 59→121 tok/s. Chú thích "`--parallel 2` −20 %" đo trên RTX 5090, không phải 3090.

## 3. Kiến trúc

```
CỬA VÀO (máy A)                              ADMISSION PLANE (máy A · CSDL · liên tiến trình)
 ChatLTT stream        runtime_noi_bo/luong.py:202 ─┐   ┌──────────────────────────────────────────┐
 /messages /responses  server/api/streaming.py:215 ─┤──►│ Phòng chờ (bảng mới `llm_waiters`)        │
 /chat/completions     server/api/chat.py:188 ──────┤   │ Sổ ngân sách = `ExecutionLease` mở rộng   │
 job nền               platform_core/job_runner.py:229 ┤ │ Luật nhận trong advisory lock resource     │
 planner (không chờ)   platform_core/agent/planner.py:144┘└───────────────────┬──────────────────────┘
                                                                 nhận ⇒ giữ tiền ⇒ gọi
GATEWAY máy B (`llm_gateway/`): chốt fail-closed — sổ token riêng (ước dư + biên), N slot, ≤1 whale, 429 nhanh, KHÔNG xếp hàng
ENGINE: llama-swap MỘT hồ sơ `qwen38-api` = llama-server -np 4 -kvu -c 204800 --mmproj, draft-mtp,
        CUDA_VISIBLE_DEVICES=<UUID 3090>
```

Ba tầng không lẫn nhau (§15): **nghiệp vụ** (lớp, tài khoản, công bằng, tiền, chờ) ở máy A; **an toàn**
(sức chứa đúng token, GPU, trọng tài, dọn card) ở gateway; **thực thi** (slot, batching, KV) ở engine.
Gateway không bao giờ giữ request thứ hai trong hàng ẩn (giữ KEEP D-07-2 của audit).

## 4. Mô hình dữ liệu

### 4.1 `ExecutionLease` (`platform_core/models.py`) — thêm cột
| Cột | Kiểu | Nghĩa |
|---|---|---|
| `lop` | str | `tuong_tac` \| `nen` \| `noi_bo` |
| `token_dat_truoc` | int | `prompt_ước + max_tokens_hiệu_lực + đệm` — **toàn bộ ngữ cảnh**, không chỉ phần mới (phần cache trúng vẫn chiếm ô KV) |
| `token_prefill_moi` | int | ước token cần prefill mới (TD-6) |
| `la_whale` | bool | `token_prefill_moi ≥ NGUONG_WHALE` |

Giữ nguyên `UNIQUE(resource, slot)`, heartbeat, `ORPHAN_TIMEOUT`. Migration alembic mới.

### 4.2 `llm_waiters` (mới) — phòng chờ của cửa tương tác
`id, resource, lop, user_id, request_id (duy nhất), token_dat_truoc, token_prefill_moi, la_whale,
created_at, heartbeat_at, trang_thai (cho|nhan|roi|het_han), ly_do_cho, lease_id`.
Không chứa prompt, payload, token bí mật. Dòng hết nhịp tim (> `HAN_NHIP_CHO`) bị dọn.
Việc nền **không** có dòng ở đây — hàng bền của nó vẫn là `jobs`.

### 4.3 Một nguồn cho mọi con số (`apps/ltt_llm/ngan_sach.py`)
Thêm `SO_SLOT_MAY_B` (thay `DONG_THOI_MAY_B = 1`); pool = `CUA_SO_MODEL` đã có. Dẫn xuất từ đó:
`manifest.py:197` `admission_slots`, env gateway `LTT_LLM_MAX_DONG_THOI`, `--parallel` trong yaml.
Nền tảng nhận pool qua **trường mới của `ToolSpec`** `admission_token_pool` (cạnh `admission_slots`,
`platform_core/registry.py:151-154`; mặc định 0 = không áp ngân sách token ⇒ tool khác không đổi hành vi).
Đây là một bổ sung **hợp đồng app** có chủ đích (CLAUDE.md: thiếu hợp đồng thì bổ sung hợp đồng,
không đi vòng) — manifest khai, nền tảng đọc, không import ngược.
`tests/test_334_ngan_sach_ltt_llm.py` mở rộng: chốt khớp `--parallel`, `-kvu`, `--mmproj`, UUID GPU.

## 5. Luật nhận (admission) — một hàm, chạy trong advisory lock của resource

Nhận request R khi **tất cả** đúng:
1. có slot trống (`count(lease) < SO_SLOT_MAY_B`);
2. `Σ token_dat_truoc(lease sống) + R.token_dat_truoc ≤ POOL` (204.800);
3. nếu `R.lop = nen`: `count(lease nen) < N−1` **và** không có người `tuong_tac` nào đang chờ
   (dù người đó đang chờ slot hay chờ ngân sách — nền không được chen vào phần họ đang đợi);
4. trần tài khoản (TD-8): nếu có người khác đang chờ, lease đang chạy của tài khoản R `< ceil(N/2)`;
5. whale (D-05): tối đa 1 lease `la_whale`; whale R chỉ vào khi không còn lease `tuong_tac` nào
   đang chạy — hoặc R đã chờ > `CHO_WHALE_TOI_DA` (30 s), khi đó R thành **chặn**: không nhận lượt
   mới nào khác tới khi R vào được;
6. thứ tự xét: lớp → công bằng tài khoản + aging (luật `platform_core/jobs.py:206-224`) → FIFO;
   **FCFS chặt trong một lớp** — người đứng đầu chưa vừa thì người sau chờ (chống bỏ đói phiên dài).

`noi_bo` (planner): thử **một lần**, không chờ, không lấy slot chừa (xử như `nen` ở luật 3); hết chỗ ⇒
Gemini như F-06. PostgreSQL: `pg_advisory_xact_lock` theo namespace resource (khuôn `public_api/limits.py:249-270`);
SQLite chỉ kiểm logic đơn luồng; race kiểm bằng PostgreSQL thật (khuôn `test_73`).

**Ước token.** Máy A ước **dư**, qua cầu hợp đồng app có sẵn `executor.estimate_input`
(`apps/ltt_llm/executor.py:31`) — `platform_core` **không import `apps/`** (hợp đồng app; audit D-07-1). `max_tokens_hiệu_lực` = giá trị client
gửi, bị chặn bởi trần ra hiện có; thiếu thì dùng mặc định theo cửa (`ngan_sach.mac_dinh_cho`). Token mới
(TD-6): tin nhắn đã có trong lượt trước **của cùng tài khoản** (khớp tiền tố danh sách tin nhắn) coi là
cache trúng. Gateway giữ sổ **riêng** bằng **cùng phép ước dư** (`KY_TU_MOI_TOKEN`, cố ý nghiêng cao) +
~1.500 token mỗi ảnh + biên an toàn `DEM_AN_TOAN`; `/tokenize` giữ đúng vai hiện nay (chỉ khi ước vượt
trần 413) để không thêm round-trip vào mọi lượt. Ước sai ⇒ engine xếp hàng ẩn ⇒ `requests_deferred > 0`
⇒ báo động (§11). *(Sửa chữ 2026-09-11 khi viết plan: bản đầu ghi "đếm đúng", sai với đường nhanh
của gateway; không đổi quyết định nào.)*

## 6. Vòng đời theo cửa

**Stream** (`/messages`, `/responses`, ChatLTT) — D-06:
`kiểm tham số → kiểm trần đầu vào theo model (413 TRƯỚC 200) → kiểm số dư đủ (402 TRƯỚC 200) →
phòng chờ đầy? (429 TRƯỚC 200) → gửi 200 + SSE →
chờ (nhịp tim 15 s, mã lý do) → nhận ⇒ GIỮ TIỀN → mở luồng máy B → quyết toán theo DemToken →
nhả lease (finally + BackgroundTask)`. Hết `CHO_STREAM_TOI_DA` (5 phút) ⇒ sự kiện lỗi đúng khuôn:
Anthropic `event: error` + `overloaded_error`; OpenAI Responses `response.failed`; ChatLTT sự kiện riêng.

**Đồng bộ** (`/chat/completions`) — TD-7: chờ **trước header** trong ngân sách thời gian còn lại
(`features.tran_token_ra_dong_bo`, ≤ ~60 s) → quá thì 429 + `Retry-After`. Thứ tự tiền giữ nguyên.

**Job** — không đổi: submit giữ tiền; worker claim → `hold_persisted` (lớp `nen`) → không nhận thì
`_tra_ve_hang_doi` (không tính attempt) → chạy → quyết toán.

**Gateway từ chối vì ngân sách/slot** khi máy A đã nhận ⇒ máy A coi là **bận**: nhả lease, đưa request
**về phòng chờ** (tối đa `SO_LAN_QUAY_LAI`), không phải lỗi. Không đánh dấu khoá hỏng (INV-004/013).

## 7. Engine (`llm_gateway/deploy/llama-swap.yaml`)

Một hồ sơ `qwen38-api`: cờ hiện có + `--parallel <SO_SLOT_MAY_B> -kvu --mmproj mmproj-F16.gguf
--cache-ram <TD-11>`; `env: [CUDA_VISIBLE_DEVICES=<UUID 3090>]`; `aliases: [qwen38-vision]`.
Xoá hồ sơ `qwen38-vision` riêng ⇒ không còn đổi hồ sơ, không cần máy trạng thái xả/đổi.
Hồ sơ dự phòng `qwen38-api-duphong` (pool nhỏ hơn, chốt bằng một lần nạp đo) — chỉ dùng khi hồ sơ
chính nạp hỏng (TD-12, runbook ở pha 2, tự động hoá ở pha 3). `-b` giữ mặc định (M-2).
Gateway **không bao giờ** gửi `X-Conversation-Id` (llama.cpp sinh tiếp sau khi client ngắt nếu có).

## 8. Hủy (TD-9)

HỦY = GPU dừng + nhả slot + nhả ngân sách + trạng thái chốt + tiền chốt.
- Đang chờ + client ngắt ⇒ ghi nhịp tim thất bại ⇒ `roi`; chưa giữ tiền.
- Stream đang chạy + client ngắt ⇒ chuỗi hiện có (gateway `upstream.close()` ⇒ llama.cpp nhả ≤ 1 s).
- Job `POST /cancel` ⇒ **mới**: luồng canh `is_cancelled()` ~1 s **đóng kết nối HTTP tới máy B**; tiền theo
  hợp đồng hiện có (hủy ⇒ trừ 0).

## 9. Backpressure

Không hàng vô hạn. Phòng chờ có hai trần: `SO_NGUOI_CHO_TOI_DA[lop]` và `TOKEN_PREFILL_CHO_TOI_DA`
(≈ 60 s × tốc độ prefill đo được). Job giữ trần `global/resource/account` hiện có. Ngữ nghĩa lỗi giữ
nguyên: 429 bận · 502 hỏng · 413 đầu vào quá lớn (không thử lại) · timeout sau khi gửi = `ambiguous`.

## 10. Tiền — bất biến

Chờ miễn phí. Ngân sách KV không phải tiền. Stream: giữ tiền **chỉ sau khi được nhận**.
**INV-MJ-1** request đang chờ không có dòng giữ tiền nào. **INV-MJ-2** hết trần chờ không để lại khoản
treo. Giữ INV-003 (bận ⇒ không thu), INV-011/012 (idempotency theo `request_id`), cột `credit_delta` (F-01).

## 11. Quan sát (TD-10)

- Engine: `/metrics` (đã bật trên máy B) — `requests_processing`, **`requests_deferred` (phải = 0)**,
  `n_busy_slots_per_decode`, `prompt_tokens_cached_total`, spec acceptance; `/slots`.
- Gateway `/health`: `dang_chay/N`, `token_dat/pool`, `whale_dang_chay`, `vram_trong_3090`.
- Máy A `/ops/jobs-metrics`: độ sâu phòng chờ theo lớp, tuổi lâu nhất, nhận/từ chối/hết hạn theo lý do,
  ngân sách đã đặt — ghi **bền** vào mẫu CSDL (khuôn `api_metric_samples`).
- Nối `request_id → job_id → lease_id → header X-LTT-Request-Id ở gateway → task/slot llama.cpp`.
- `LTT_Soi_CongLLM` báo động: VRAM trống 3090 < 300 MiB · `requests_deferred > 0` · log có
  "Context size has been exceeded".

## 12. Tham số khởi đầu (đều là cấu hình, không hằng số rải rác)

| Tham số | Khởi đầu | Căn cứ |
|---|---|---|
| `SO_SLOT_MAY_B` | 4 | M-1 |
| `POOL` | 204.800 (= `CUA_SO_MODEL`) | D-08 |
| Slot tối đa lớp `nen` | N−1 = 3 | D-03 |
| Trần tài khoản khi có người chờ | ceil(N/2) = 2 | TD-8 |
| `NGUONG_WHALE` (token mới) | 16.384 | tải thật: 7,6 % lượt |
| `CHO_WHALE_TOI_DA` | 30 s | D-05 |
| `CHO_STREAM_TOI_DA` | 300 s | D-06 |
| `SO_NGUOI_CHO_TOI_DA[tuong_tac]` | 32 | backpressure |
| `TOKEN_PREFILL_CHO_TOI_DA` | ~57.000 | 60 s × ~950 tok/s (M-2) |
| `--cache-ram` | chốt ở pha 2 | TD-11 |
| đệm đặt chỗ | `n_batch` (2.048) | patch 0011 của lab |

## 13. Ngưỡng chấp nhận (TD-14)

C1 decode ≥ 54 tok/s · C4 tổng ≥ 100 tok/s · **0** "Context size has been exceeded" · **0** OOM/crash
llama-server · **0** thu hai lần · TTFT tương tác ngắn khi còn chỗ p95 ≤ 3 s · chờ lúc tải bình thường
p95 ≤ 60 s · `requests_deferred` = 0 suốt tải tổng hợp.

## 14. Rollout (D-10 A) và rollback

| Pha | Nội dung |
|---|---|
| 0 (P0, độc lập) | Ghim Qwen vào 3090 (UUID) trên **bản yaml đang chạy** (có `--metrics`) |
| 1 (N vẫn 1) | Sổ ngân sách + phòng chờ + giữ tiền sau nhận + hủy cứng job + quan sát — không đổi engine |
| 2 (N=4) | Hồ sơ gộp + chốt gateway → tải tổng hợp qua đường production trên máy B → canary Codex + Claude Code thật → bật → theo dõi 24 h |
| 3 (P2) | `-b`, tự chuyển hồ sơ dự phòng, `Retry-After` theo ước lượng hàng — chỉ khi telemetry đòi |

**Rollback:** `SO_SLOT_MAY_B = 1` + yaml trước (`deploy.ps1` chụp-trước-khi-đè, lui đã diễn tập 18,9 s).
Pha 1 đúng ở N = 1 nên lui pha 2 không kéo lùi pha 1.

## 15. Rủi ro còn lại (đã chấp nhận hoặc có biện pháp)

| Rủi ro | Mức | Biện pháp |
|---|---|---|
| Biên VRAM 374 MiB (D-08 A) | chủ dự án chấp nhận | TD-12: hồ sơ dự phòng, cảnh báo VRAM, khuyến nghị cắm màn hình vào 5060 Ti |
| Ước token máy A thiếu | trung bình | ước dư + gateway đếm đúng + `requests_deferred` báo động |
| Client xử lý lỗi giữa luồng khác nhau (D-06) | trung bình | canary Codex/Claude Code thật trước bật |
| Exception spec-decode khi KV gần đầy (lab) | thấp–trung | đệm đặt chỗ + tải tổng hợp có ca gần đầy |
| Nhận diện "lượt tiếp" sai ⇒ whale nhầm | thấp | chỉ ảnh hưởng thứ tự, không ảnh hưởng an toàn KV |
| 413 dời lên máy A theo phép **ước** (D-06: sau 200 thì không còn 413) ⇒ yêu cầu sát trần có thể bị 413 dù máy B nhận được | thấp (tải thật: ngữ cảnh p99 113K, max 165K < trần 169.984) | giữ 413 **trước 200** để Codex/Claude Code vẫn tự nén hội thoại (`streaming.py:679-682`); đếm ca 413-trước-200 ở telemetry |
| Số đo n = 1 mỗi ô | đã khai | ngưỡng TD-14 kiểm lại ở tải tổng hợp pha 2 |
