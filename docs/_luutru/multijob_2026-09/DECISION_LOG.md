# LTT_LLM đa job — DECISION LOG

> Mỗi quyết định hỏi MỘT lần, chốt rồi mới sang câu sau (§4). Đã LOCKED thì không
> tự đổi trong plan; muốn đổi phải mở `DECISION REOPEN REQUEST` (§9).
> Nền bằng chứng: `docs/multijob/00_EVIDENCE.md`.

## Trạng thái
- Audit: XONG (3 agent + đọc mã + tái dùng `docs/audit_ltt_llm/`).
- Brainstorming: đã invoke.
- Đang chờ: **D-01** (chế độ đồng thời engine máy B) — câu hỏi P0 chặn mọi thứ.

## Quyết định kỹ thuật (không cần hỏi user — §6)
- **TD-1 — Tái dùng business queue + admission plane hiện có, KHÔNG dựng queue/scheduler thứ hai.** Evidence: `jobs.py` fair-share+aging, `admission.py` slot lease đã hỗ trợ `slots>1`, `limits.py` backpressure. Đây đúng định nghĩa "plan tốt" §49.
- **TD-2 — Giữ tầng gateway `GioiHan`/trọng tài/dọn card làm fail-closed cuối.** Không gỡ như "trùng lặp" (`gioi_han.py:4-8` là phòng thủ theo tầng có chủ ý).
- **TD-3 — Không viết lại scheduler của llama.cpp bằng Python** (§15). Slot/batching/KV/MTP là việc engine.

## D-01 — Chế độ đồng thời engine máy B
**Selected: B — Đa slot song song thật** (`--parallel N` + continuous batching, `admission_slots=N`).
**Reason:** Xếp hàng (A) chỉ làm việc chờ công bằng, KHÔNG thêm năng lực; một lượt
ngữ cảnh dài chặn mọi user. Mục tiêu prompt nhấn mạnh throughput + nhiều user đồng
thời ⇒ cần song song thật ở engine. Cộng đồng RTX 3090 có bằng chứng số cho batch.
**Hệ quả LOCKED kèm theo:** (1) phải đo VRAM/`--parallel` trên máy B trước khi
chốt N; (2) chấp nhận độ trễ per-request tăng + spec-decode giảm; (3) `-c` tổng
chia cho N ⇒ ngữ cảnh mỗi slot giảm — mở D-02.
**Status: LOCKED.**

## D-02 — Ngữ cảnh dài vs đồng thời
**Selected: hướng D (do user khai, ngoài A/B/C) — Admission theo NGÂN SÁCH ngữ cảnh động + CHỜ.**
Không cắt cứng ngữ cảnh mỗi slot. Coi KV là ngân sách chung: request ngắn → nhiều
lượt chạy song song; một phiên ngữ cảnh dài đang chiếm phần lớn ngân sách → job kế
(không đủ chỗ) **CHỜ** tới khi phiên đó xong rồi mới nhận. "Nghiên cứu logic sâu
sắc để tối ưu."
**Đây là mô hình KV-budget của vLLM** (§14: max_num_batched_tokens/KV budget/backpressure).
**⚠️ Feasibility đang xác minh:** llama.cpp thường cấp N slot CỐ ĐỊNH (`n_ctx/N`)
lúc khởi động, khác PagedAttention động của vLLM. Phải chốt build 10689 làm được
gì trước khi thiết kế (§48). Có thể phải hiện thực budget-awareness ở tầng
admission máy A trên nền slot cố định, hoặc dùng lane dài riêng. → nghiên cứu R-1.
**Status: DIRECTION LOCKED, cơ chế chờ thiết kế sau R-1.**

## ⚠️ EVIDENCE CORRECTION EC-1 (2026-09-11) — ảnh hưởng bằng chứng của D-01
Câu hỏi D-01 dẫn "cộng đồng ~1.000 tok/s @ 64 đồng thời" mà **không nói đó là
vLLM**. Đọc `D:\LTT_VLM_REFS\qwen38-27b-rtx3090\batch\README.md`: `vllm bench
serve`, model W4A16-AutoRound (không GGUF), vLLM vá, Linux. Máy B = llama.cpp GGUF
trên Windows ⇒ **hiệu năng đa slot llama.cpp trên card này CHƯA CÓ SỐ**.
Cùng nguồn: dưới ~C8 spec-decode một luồng nhanh hơn (2,5× ở C1); batch vượt từ
C8. C4 batch = 153,8 tok/s tổng.
Chú thích `llama-swap.yaml:89-91` ("--parallel 2 thấp ~20%, mất lợi thế ở 4") là
số **cộng đồng**, chưa đo trên máy B.
**D-01 CHƯA mở lại:** hướng (song song thật) vẫn hiện thực được bằng `--parallel N`;
cái đổi là **độ lớn lợi ích**. Nếu R-1 chứng minh D-01 mất hiệu lực → DECISION
REOPEN REQUEST.

## D-09a — Quyền sở hữu GPU trên máy B (chủ dự án khai trực tiếp, 2026-09-11)
**Selected:** Qwen3.8-27B **CHỈ chạy trên RTX 3090**. RTX 5060 Ti 16 GB (vừa lắp) **dành
cho model khác về sau** — không dùng để chia/mở rộng Qwen.
**Hệ quả:** loại mọi phương án "chia lớp 3090+5060 Ti" để tăng pool KV. Trần năng lực
đa slot = VRAM của một mình 3090. Kiến trúc vẫn phải chừa làn thứ hai (5060 Ti, model
khác) theo §35 mà không viết lại control plane.
**Status: LOCKED** (ràng buộc phần cứng của chủ dự án).

## 🔴 P0-GPU-PIN (phát hiện 2026-09-11, KHÔNG do phiên này gây ra)
`llama-server --list-devices` trên máy B: `CUDA0 = RTX 3090`, `CUDA1 = RTX 5060 Ti`.
Không chỗ nào ghim thiết bị: `llm_gateway/**` không có `CUDA_VISIBLE_DEVICES`/`-dev`/`-sm`/`-ts`;
`llama-swap.yaml` đã deploy trên máy B (sha `9c1f58…`, = kho + `--metrics`) cũng không;
dịch vụ `LTTLlamaSwap` không có biến môi trường nào. ⇒ Với `-ngl 999`, **lần nạp
production tới sẽ tự chia model qua cả hai card** — trái D-09a.
Bản vá bền phải ở **kho** (`env: CUDA_VISIBLE_DEVICES=<UUID 3090>` mỗi hồ sơ trong
`llama-swap.yaml`): biến môi trường cấp dịch vụ sẽ mất ở nhánh gỡ-cài-lại của
`llm_gateway/deploy/cai_dat_dich_vu.ps1:50-53`. UUID 3090:
`GPU-26623278-4fa5-82db-4306-237651b03e78`.
Lưu ý deploy: `llama-swap.yaml` trên máy B đang **đi trước** nhánh này (`--metrics`),
nên deploy từ nhánh này sẽ **lùi** `--metrics` — phải vá trên bản đang chạy/trunk.
**Status: OPEN — ưu tiên P0, độc lập với đa slot.**

## ~~PROMPT ASSUMPTION INVALID — "C4 initial ceiling"~~ → ĐÃ BÁC BỎ BẰNG ĐO (EC-2)
~~Suy từ lab: C4 trên 3090 một mình gần như chắc chắn không vừa; mức thực tế 2 slot.~~
**EC-2 (M-1, 2026-09-11): SAI.** Đo thật: `-np 4 -kvu -c 204800` nạp **22.965 MiB**,
đỉnh 22.993, còn ~1,6 GiB. Lab OOM vì drafter **DFlash2 là model riêng** ăn VRAM;
`draft-mtp` của ta dùng lớp nextn có sẵn. Mỗi slot thêm ~448 MiB cố định.
Bài học: lấy số của một cấu hình **gần giống** để kết luận về cấu hình của ta là
đúng lớp lỗi "gán một con số có thật cho một tập hợp khác" — đo mới biết.
⇒ **C4 là mục tiêu ban đầu khả thi.** Chi tiết `00_BASELINE.md`.

## R-1 (nghiên cứu) — llama.cpp build 10689 slot/KV semantics — **XONG**
Kết quả: `04_RUNTIME_CAPABILITY_MAP.md` + `05_COMMUNITY_EVIDENCE.md`. Tóm tắt quyết định:
cơ chế D-02 **bắt buộc** nằm ngoài engine stock (engine không admission theo KV; tràn
pool unified = giết mọi slot). Lab đã hiện thực đúng cơ chế này (patch 0011) và đo +54%
C4 ở 2 slot.

## M-1 (đo trên máy B) — **XONG** 10:35–10:41 (chủ dự án chạy bước tạo task)
Kết quả đầy đủ: `00_BASELINE.md`; dữ liệu thô + dụng cụ: `artifacts/m1/`.
Scheduled Task đã gỡ sau khi đo; không còn tiến trình sót.

## Quyết định kỹ thuật rút từ M-1 (không cần hỏi — §6)
- **TD-4 — Engine: `-np 4 -kvu`, giữ pool `-c 204800`, giữ `draft-mtp`.** Evidence:
  C1 không đổi (59,9→62,7), C4 +105 % (59→121 tok/s), người cuối 34,6→16,9 s, VRAM
  22.965/24.576. N là **tham số cấu hình**, 4 là giá trị khởi đầu đã đo (§35).
  ⚠️ Chỉ bật SAU khi có tầng admission ngân sách (TD-5) — thiếu nó, một lần tràn pool
  giết mọi slot (`04` §2).
- **TD-5 — Admission ngân sách KV bắt buộc**, đặt trước `prompt + max_tokens + đệm`
  trên pool 204.800; không đủ ⇒ CHỜ (hiện thực D-02). Vị trí đặt → xem thiết kế.
- **TD-6 — "Whale" = số token cần prefill MỚI**, không phải tổng ngữ cảnh (M-1 §2.5).

## D-05 — Chính sách prompt DÀI (prefill)
**Question:** Khi một request cần prefill dài, người khác chờ ~55 s hoặc bò 1,4 tok/s bất kể số
slot (M-1). Chính sách?
**Selected: D — Nhường tương tác + chia nhỏ prefill.**
- Tầng admission: **tối đa 1 whale prefill tại một thời điểm**; whale **chờ** các lượt đang
  sinh chữ xong, có **trần chờ** (giá trị khởi đầu đề xuất 30 s) rồi vẫn chạy — không bỏ đói.
- Engine: giảm cỡ lô prefill (`-b`/`-ub`) để phần chồng lấn còn lại ít đau; **giá trị chốt bằng
  phép đo M-2 (~10 phút)** trước rollout, không đoán.
- "Whale" = **token cần prefill MỚI** (TD-6), không phải tổng ngữ cảnh; ngưỡng khởi đầu là tham số.
**Reason:** B một mình không cứu người đến trong lúc whale đang prefill; C một mình không ngăn hai
whale chồng nhau. vLLM đo: lô 2048→512 ⇒ TTFT người mới 63-70 s → 4,5-7,6 s, whale +15 %.
**Status: LOCKED.**
**Kết quả M-2 cho vế engine (2026-09-11):** không cỡ lô nào thắng rõ — hiệu ứng chính phụ thuộc
thứ tự slot engine chọn (thay đổi giữa các lượt cùng cấu hình), và tốc độ trong lúc whale prefill
luôn 1,5–2,3 tok/s. ⇒ **Giữ `-b` mặc định**; vế **admission** của D-05 là vế chịu tải. Đây là kết
quả của chính phép đo mà D-05 chỉ định, không phải mở lại D-05. (`00_BASELINE.md` §4.1)

## D-06 — Cửa đồng bộ/stream khi đầy
**Question:** Hết slot / hết ngân sách KV / đang nhường whale — cửa stream làm gì?
**Selected: C — Mở 200 + SSE ngay, gửi nhịp tim trong lúc chờ, chờ được vài phút.**
**Hệ quả BẮT BUỘC (không được bỏ khi thiết kế):**
1. **Giữ tiền dời vào SAU admission**, bên trong generator. Kiểm số dư đủ (402) vẫn trước 200.
   Giữ nguyên INV-003 (bận ⇒ không thu) và INV-011/012 (idempotency theo `request_id`).
2. Hết trần chờ ⇒ **sự kiện lỗi đúng khuôn giao thức** (Anthropic `event: error` /
   `overloaded_error`; OpenAI Responses `response.failed`; Chat Completions: khối lỗi cuối).
   Phản ứng của Codex/Claude Code phải kiểm bằng **client thật** trước rollout.
3. Client ngắt khi đang chờ ⇒ rời hàng ngay (chưa giữ tiền ⇒ không có gì hoàn).
4. Hàng chờ là **một** hàng liên tiến trình trong admission plane (nhiều web worker cùng thấy),
   không phải hàng ẩn trong một tiến trình, không phải hàng thứ hai ở gateway.
**Status: LOCKED.** Trần chờ là tham số (đề xuất khởi đầu ở thiết kế).

- **TD-7 — Cửa ĐỒNG BỘ** (`/api/v1/chat/completions` không stream): C không áp được (không
  có luồng để giữ). Chờ **trước header** trong ngân sách thời gian sẵn có của cửa
  (`features.tran_token_ra_dong_bo`, trần Cloudflare ~100 s), quá thì 429 + `Retry-After`
  như hiện tại. Suy ra từ D-02 + D-06 + ràng buộc Cloudflare; chủ dự án có thể mở lại.

## D-03 — Ưu tiên giữa các lớp request
**Question:** llama.cpp không preempt được; mỗi lượt p50 39 s / p90 ~4 phút (tải thật). Ưu tiên thế nào?
**Selected: A — Hai lớp, TƯƠNG TÁC > NỀN, chừa slot.**
- TƯƠNG TÁC = ChatLTT (web) + Public API sync/stream (`/chat/completions`, `/messages`, `/responses`).
- NỀN = Public API `/jobs` + job của các app khác gọi model nhà.
- Nền dùng **tối đa N−1 slot** (luôn chừa ≥1 cho tương tác); không có tương tác thì nền dùng
  phần còn lại (work-conserving trong giới hạn N−1).
- Trong mỗi lớp: công bằng theo tài khoản + aging — **tái dùng** luật `jobs.py:206-224`.
- Việc nội bộ nền tảng qua `dieu_phoi` (planner, tóm tắt): **giữ như nay** — hết chỗ ⇒ rơi sang
  Gemini (F-06), không xếp hàng, không chiếm slot chừa.
**Reason:** không preempt + lượt dài ⇒ thứ tự hàng một mình không cứu người đang chờ màn hình;
đòn bẩy thật là chừa slot.
**Status: LOCKED.**

## Quyết định kỹ thuật suy ra (không hỏi — §6/§22; chủ dự án mở lại được khi duyệt thiết kế)
- **TD-8 (D-04 công bằng)** — Trần **đang chạy** mỗi tài khoản = `ceil(N/2)` **chỉ khi có người
  khác đang chờ** (work-conserving: một mình thì dùng hết phần lớp mình được phép). Lý do: 4 phiên
  Claude Code của một người không được chiếm cả 4 slot khi người khác đang chờ; nhưng không phạt
  khi hệ rảnh. Tái dùng `max_active_jobs`/`class_concurrency` sẵn có cho phần hàng đợi.
- **TD-9 (D-07 hủy)** — HỦY = GPU dừng + nhả slot + nhả ngân sách + quyết toán theo số đo.
  (a) stream: đã propagate (gateway `upstream.close()` ⇒ llama.cpp nhả ≤1 s, `04` §8) — GIỮ;
  (b) đang chờ trong phòng chờ: rời hàng ngay, chưa giữ tiền; (c) **job nền: bổ sung hủy CỨNG** —
  worker đóng kết nối HTTP tới máy B khi `is_cancelled()` (hiện chỉ hợp tác, `job_runner.py:110-174`);
  (d) gateway **không bao giờ** gửi `X-Conversation-Id` (`04` §8).
- **TD-10 (quan sát)** — tái dùng `/metrics` của llama-server (đã bật trên máy B) + `/slots` +
  `/ops/jobs-metrics`; thêm số của phòng chờ (độ sâu theo lớp, tuổi lâu nhất, ngân sách đã đặt/còn,
  whale đang prefill). Nối `request_id → job_id → lượt gateway → id slot`.
- **TD-11** — `--cache-ram` nâng khỏi mặc định 8.192 MiB (máy B 128 GB RAM, cache trúng 54 %) —
  giá trị chốt ở M-2/rollout.

## D-08 — Text + vision trên cùng 3090
**Question:** Hồ sơ gộp (mmproj) pool 200K đo được: chạy tốt, đúng, nhưng còn 374 MiB. Chọn?
**Selected: A — MỘT hồ sơ gộp text+vision, 4 slot `-kvu`, GIỮ pool 204.800.**
Không còn đổi hồ sơ ⇒ không còn "llama-swap giết lượt đang chạy" (186 lần nạp/20 ngày), không cần
máy trạng thái drain/switch. Ngữ cảnh tối đa đang bán giữ nguyên.
**Rủi ro chủ dự án chấp nhận:** biên VRAM ~374 MiB (đỉnh 24.202/24.576 khi 1 ảnh + 3 text).
**Status: LOCKED.**
- **TD-12 (giảm nhẹ trong phạm vi A)** — llama.cpp cấp KV + buffer tính toán **lúc nạp**; lúc chạy
  M-2 chỉ tăng thêm ~96 MiB (ảnh). ⇒ Điểm gãy thật là **lúc nạp**: nếu app desktop đang giữ thêm
  VRAM thì nạp hỏng ⇒ không có model. Biện pháp: (a) llama-swap giữ một **hồ sơ dự phòng** cùng mọi
  cờ nhưng pool nhỏ hơn, chỉ dùng khi hồ sơ chính nạp hỏng — chốt bằng một lần nạp đo; (b) telemetry
  **VRAM trống của 3090** + cảnh báo khi < 300 MiB; (c) `ttl` dài để giảm số lần nạp.
- **Khuyến nghị vận hành (việc của chủ dự án, không phải mã):** cắm màn hình vào **5060 Ti** để 3090
  chạy headless — các app desktop (Edge, Zalo, game) sẽ vẽ trên card kia, trả biên cho 3090.
  ⚠️ Cần xác nhận card nào đang xuất hình (cả hai đều có `dwm.exe`).

## D-10 — Nhịp rollout
**Selected: A — Nhanh có kiểm soát.** Gate xanh → tải tổng hợp trên máy B **qua đường production**
(C4, whale, ảnh, cố tình vượt ngân sách, hủy giữa chừng) → canary **client thật** (Codex + Claude
Code) qua Cloudflare → bật thẳng 4 slot → theo dõi 24 h. Rollback = một giá trị cấu hình (về 1 slot).
**Reason:** tải thật ~180 lượt/ngày ⇒ soak từng bậc thu được rất ít lần đồng thời; tải tổng hợp mới
chứng minh được an toàn.
**Status: LOCKED.**
- **TD-14 — Ngưỡng chấp nhận (suy từ số đo, chủ dự án duyệt ở thiết kế):** C1 decode ≥ 54 tok/s
  (90 % mốc 59,9) · **0** "Context size has been exceeded" · **0** llama-server OOM/crash ·
  **0** thu hai lần · TTFT tương tác ngắn khi còn chỗ p95 ≤ 3 s (đo 0,5 s) · chờ phòng chờ lúc tải
  bình thường p95 ≤ 60 s · C4 tổng ≥ 100 tok/s (đo 121–125).

## ✅ DECISION LOCK — không còn quyết định P0/P1 mở (2026-09-11)
D-01 B · D-02 ngân sách động + chờ · D-03 A · D-05 D · D-06 C · D-08 A · D-09a · D-10 A ·
TD-1…TD-14. Mở: **P0-GPU-PIN** (vận hành, độc lập — vào Phase 0 của plan).
Tiếp theo: trình bày thiết kế từng phần (§27), rồi DESIGN LOCK.

## R-1 (câu hỏi gốc)
Câu hỏi phải trả lời bằng MÃ NGUỒN b10689 (không phải HEAD):
1. `--parallel N` + `-c`: mỗi slot n_ctx/N hay dùng chung? Có `--kv-unified` không, mặc định?
2. Hết KV giữa lúc decode thì server làm gì (lỗi request? giết slot? defer?)
3. Model hybrid (GDN recurrent + attention): trạng thái hồi quy cấp theo slot thế nào?
4. `draft-mtp` + `--parallel >1` có chạy không?
5. `/slots`, `/metrics`: lộ ra những gì (kv usage, deferred, busy)?
6. b10689→b10901: commit nào chạm server/KV/MTP liên quan?
*(đang chạy)*
