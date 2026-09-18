# 05 — Bằng chứng cộng đồng / thượng nguồn

> Nguồn đã clone NGOÀI kho ở `D:\LTT_VLM_REFS\` (không đưa vào `research/` trong
> cây: `research/` không bị gitignore và các bước quét tĩnh của gate sẽ quét cả mã
> vendor). Nghiên cứu R-1b, 2026-09-11.
> `rtx3090-llm-lab` @ `b3f2769` · `vllm` @ `07b7553` · `qwen38-27b-rtx3090` origin `123483f`
> (working tree cục bộ `3059e35` — CHỈ fetch, không checkout) · `qwen38-mtp`.

## A. Ma trận (§41)

| Vấn đề | LTT hiện tại | Bằng chứng thượng nguồn/cộng đồng | Tái dùng? | Cần đo cục bộ? |
|---|---|---|---|---|
| Đa slot trên 3090 + Qwen3.8-27B + llama.cpp | `--parallel 1` | Lab: p2 unified+patch C4 **113–124 tok/s** vs p1 **76** (+54%); 1 luồng gần như không đổi (102,45→102,11) — `rtx3090-llm-lab/benchmarks/qwen-speed-2026-09-04/` | Có (cấu hình) | **CÓ** — lab chạy Linux, DFlash2, pool 131K; ta Windows, draft-mtp, muốn 200K |
| Số slot trần trên 24 GB | — | Lab pool 131K ~23,3 GB; **p3 ubatch 512 OOM lúc nạp**, p3 ubatch 128 chạy (124,6) | Có (giới hạn) | **CÓ** — VRAM với 200K + KV draft F16 |
| Ngân sách KV + chờ (D-02) | không có | Lab **patch `0011-server-unified-kv-admission.patch`**: đặt trước `min(n_ctx_slot, prompt+n_predict+n_batch)`, tràn ⇒ hoãn | Có (thuật toán) | Không cho thuật toán; có cho chỗ đặt (xem D-03) |
| Tràn pool khi unified | — | Lab 2×70K+8.192 out, không patch ⇒ HTTP 500 + exception spec-decode; có patch ⇒ cả hai xong, tuần tự 101/204 s. Tiel 4 slot vượt pool ⇒ 500 cả 4 (`PARALLELIZATION.md:138-146`) | Có (bằng chứng rủi ro) | Không — mã (`04` §2) + thực nghiệm lab đủ |
| "`--parallel 2` −20%, mất lợi thế ở 4" (chú thích `llama-swap.yaml:89-91`) | là lý do giữ `-np 1` | Nguồn thật: −20% = **RTX 5090** spec-off (`qwen38-mtp/sweeps/rtx-5090.md:68-74`); "mất lợi thế ở 4" = **2×5060 Ti tensor-split** (`sweeps/multi-gpu.md:87-97`). **Không dòng nào đo trên 3090.** | **KHÔNG** — không áp cho 3090 | CÓ — C1 regression ở p2 |
| Đói do prefill (whale/minnow) | không đo | vLLM 4090: minnow ~1 tok/s khi whale prefill; budget 512 ⇒ TTFT minnow 63-70 s → 4,5-7,6 s, whale 62,6 → 72,2 s (`qwen38-27b-rtx3090 origin docs/wsl2-4090.md:322-356`). **Chưa nguồn nào đo trên llama.cpp.** | Có (nguyên tắc) | **CÓ** |
| Nhận ít làm nhiều | — | vLLM: 8 seat ⇒ 10 preempt 10,3 tok/s; 2 seat ⇒ 0 preempt 14,4 tok/s (+40%) (`README.md:343-348`); MAX_SEQS 4 nhanh hơn 8 +6,1% | Có | Không |
| Batch 64 đồng thời ~1.000 tok/s | (EC-1) | **vLLM**, W4A16, Linux — không phải llama.cpp | Chỉ tham chiếu | — |
| llama.cpp vs vLLM cho agent | llama.cpp | Lab: agent sửa file llama.cpp ~2× vLLM (230/194/219 vs 127/108/114); vLLM thắng decode đơn, prefill, 4 luồng (`engine-trial-2026-09-02/README.md:79-128`) | Giữ llama.cpp | Không |
| Ưu tiên theo request | không có | llama.cpp: không có (`04` §6). vLLM: `(priority, arrival, id)`, preempt theo priority chỉ khi running cần block | Nguyên tắc | Không |
| Trần hàng đợi | có (429) | vLLM `max_num_queued_reqs`/`max_num_queued_tokens` ⇒ 503; gợi ý token-cap = TTFT mục tiêu × tốc độ prefill | Nguyên tắc | Không |

## B. Nguyên tắc lịch mượn từ vLLM cho tầng admission trước llama.cpp

1. **Đặt trước prompt + `max_tokens` + đệm** trên ngân sách chung. vLLM chỉ đặt
   prompt vì có preemption; llama.cpp không có ⇒ phải đặt cả output. Không có
   `max_tokens` ⇒ ép trần hoặc đặt cả slot.
2. **FCFS chặt trong một lớp ưu tiên**: job lớn đứng đầu chưa vừa ⇒ các job sau chờ
   (`scheduler.py:1169-1176`) — chống bỏ đói phiên dài; muốn chen phải có aging.
3. **Hai trần độc lập**: số slot (≈`max_num_seqs`) và token (KV). Để số slot thấp.
4. **≤1 prompt "whale" prefill tại một thời điểm**; prompt ngắn chạy khi whale chờ.
5. **Hàng đợi có trần token** ≈ TTFT mục tiêu × tốc độ prefill đo được; vượt ⇒ 429/503 + `Retry-After`.
6. Sắp theo `(priority, arrival)`.

**Không chuyển được sang tầng proxy:** preemption bằng recompute (proxy chỉ huỷ-rồi-chạy-lại,
~76 s cho 70K); chia token từng bước (chỉ qua `-b`/`-ub`); admission biết prefix-cache hit.

## C. Chỉ đo trên máy B mới biết (đầu vào cho đo đạc M-1)

1. Build Windows b10689 có `--kv-unified-per-slot` không (mã có; binary?).
2. VRAM: pool 200K vs 131K, p2/p3, KV draft MTP F16.
3. `draft-mtp` + `-np 2` ổn định trên Windows không; gần đầy KV thì sao.
4. Minnow tok/s khi một prompt dài đang prefill **trên llama.cpp**.
5. Tốc độ mỗi luồng p2 + MTP trên 3090 (C1 regression).
6. Prompt cache có dùng lại qua slot không.
