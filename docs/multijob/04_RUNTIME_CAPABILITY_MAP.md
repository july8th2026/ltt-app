# 04 — Năng lực runtime: llama.cpp b10689 làm được gì cho đa slot

> Đọc từ mã nguồn ở **đúng tag `b10689` = commit `57291f264`** (trùng build máy B),
> bản clone `D:\LTT_VLM_REFS\llama.cpp` (ngoài kho). Đường dẫn dưới đây tương đối
> từ gốc clone đó. `[SUY LUẬN]` = rút ra từ mã, mã không nói thẳng.
> Nguồn: nghiên cứu R-1a, 2026-09-11.

## 1. Chia ngữ cảnh khi `--parallel N`

| Chế độ | Ngữ cảnh mỗi slot | Bằng chứng |
|---|---|---|
| mặc định (không unified) | **cứng `n_ctx/N`**, làm tròn bội 256 | `src/llama-context.cpp:290-304`; `src/llama-kv-cache.cpp:85,234-235` |
| `-kvu` / `--kv-unified` | **một pool chung**; một chuỗi đi tới toàn bộ `n_ctx` (chặn bởi `n_ctx_train`); ai tới trước dùng trước, **không đặt chỗ** | `llama-context.cpp:290-291`; `llama-kv-cache.cpp:899-1089`; `tools/server/server-context.cpp:1295,3999-4008` |
| `--kv-unified-per-slot N` | trần tĩnh mỗi slot trong pool chung | `common/arg.cpp:1646-1653`; `tools/server/server.cpp:160-170` |

- `kv_unified` mặc định `false` (`common/common.h:573`). Server **chỉ tự bật** khi `-np`
  để auto (-1 → 4 slot + unified, `server.cpp:152-157`). Truyền `-np N` tường minh
  thì **phải tự thêm `-kvu`**.

## 2. 🔴 Hết KV giữa lúc decode — đường "giết sạch"

`server-context.cpp:3661-3708`: `try_clear_idle_slots()` (chỉ khi unified) → giảm
`n_batch` một nửa → tới `n_batch == 1` vẫn hỏng thì **MỌI slot đang xử lý nhận lỗi
"Context size has been exceeded", bị nhả và bị xoá KV**, kể cả một phiên 200K.
Dòng TODO `:3666` thừa nhận chưa có "chỉ giết slot lớn nhất".
Xác nhận bằng thực nghiệm ở lab 3090 (xem `05` §B): 2×70K + 8.192 output ⇒ HTTP 500.

⇒ **Bật `-kvu` mà không có admission theo ngân sách = một lần tràn giết mọi phiên.**

## 3. Engine KHÔNG có admission theo ngân sách KV

- Hoãn (deferred) **chỉ theo số slot**, không bao giờ theo KV (`server-context.cpp:2371-2398`;
  `server-queue.cpp:76-113`).
- Kiểm độ dài chỉ so với `slot.n_ctx`, không so với chỗ trống thật của pool
  (`server-context.cpp:3169-3188,1874-1882`).
- ⇒ Cơ chế D-02 ("ngân sách chung + chờ") **phải** nằm ngoài engine stock, hoặc
  vá engine (patch 0011 của lab, `05` §B).

## 4. Chi phí bộ nhớ tăng theo N (ngoài KV)

- Trạng thái recurrent (GDN): **1 ô mỗi slot** (`src/llama-model.cpp:2535`), mỗi ô
  `1 + n_rs_seq` hàng F32; với MTP `n_rs_seq = draft.n_max` ⇒ `--spec-draft-n-max 2`
  = **3 hàng mỗi slot**, cấp lúc khởi động (`src/llama-memory-recurrent.cpp:101-103,133`).
- Context MTP có **KV riêng cho lớp nextn, cùng `n_ctx`, kiểu F16 mặc định** —
  `--cache-type-k q4_0` **không** áp cho nó; chỉnh bằng `-ctkd`/`-ctvd`
  (`common/speculative.cpp:2572-2573`; `common/arg.cpp:4090-4099`; `common/common.h:341-342`).
- Checkpoint ngữ cảnh ≤32/slot `[SUY LUẬN: ở RAM host]` (`common/common.h:629`).

## 5. MTP + nhiều slot

Có hỗ trợ, không chỗ nào tắt spec vì nhiều slot (`server-context.cpp:1261,2953-3021`;
`common/speculative.cpp:1400-1478`). Lợi ích giảm khi GPU chuyển sang giới hạn tính
toán `[SUY LUẬN]` — phải đo. Lab thấy exception spec-decode khi KV gần đầy (`05` §B).

## 6. Lịch trong engine — nguồn của "đói do prefill"

`update_slots`: token decode (+draft) của các slot đang sinh vào batch trước
(`:3072-3074`), rồi lấp prompt tới `n_batch` (2048 mặc định) **theo chỉ số slot,
không theo thứ tự đến** (`:3083-3108,3497`). `[SUY LUẬN]` Trong lúc một prompt dài
prefill, mỗi bước các slot khác được 1 token nhưng bước kéo dài ≈ thời gian prefill
2.048 token (~2 s ở ~1.000 tok/s) ⇒ **user tương tác bị kéo xuống ~0,5 tok/s**; và
prompt mới ở slot khác chờ prefill kia xong (TTFT kéo dài).
Không có ưu tiên theo request. Chọn slot: `id_slot` → độ giống prompt (LCP>0,1) → LRU
(`:1540-1623`).

## 7. Quan sát

- `/slots` bật mặc định: `id, n_ctx, is_processing, id_task, n_prompt_tokens,
  n_prompt_tokens_processed, n_prompt_tokens_cache, next_token{n_remain,n_decoded}`
  (`:686-720`); `?fail_on_no_slot=1`.
- `/metrics` **cần `--metrics`** (mặc định TẮT — production hiện không có). Tên thật:
  `llamacpp:requests_processing`, `requests_deferred`, `n_busy_slots_per_decode`,
  `prompt_tokens_total`, `prompt_tokens_cached_total`, `tokens_predicted_total`,
  `spec_decode_num_accepted_tokens_total`… **Không có** `kv_cache_usage_ratio`
  (chỉ còn trong `tools/server/bench/bench.py:119`).

## 8. Hủy

Ngắt kết nối được poll mỗi 1 s → task CANCEL lên đầu hàng → `slot.release()`
(`server-http.cpp:595`; `server-queue.cpp:550-617`; `server-context.cpp:2427-2436`).
Nhả slot **không** xoá KV (giữ làm cache). ⛔ Header `X-Conversation-Id` đổi ngữ
nghĩa: server **sinh tiếp sau khi client ngắt** (`server-stream.cpp:578-653`) —
gateway không được gửi header này.

## 9. Upstream b10689 → b10901 (212 commit) — ứng viên, KHÔNG tự nâng (§42)

| Commit | Vì sao liên quan |
|---|---|
| `5fdfa6282` | **Sửa chuẩn hoá L2 của lớp GDN trong `qwen35.cpp`** — độ đúng tính toán cho chính lớp DeltaNet của model này. Ứng viên mạnh nhất; cần A/B chất lượng. |
| `5d806aa25` | Checkpoint hybrid chỉ bị loại khi danh sách đầy — ảnh hưởng cache prompt mỗi slot |
| `2d8d612e4`, `b356fa262`, `62acc89c2` | KV không liền kề / tra cứu kv-cells theo chuỗi — có ích khi nhiều chuỗi chung một pool |
| `e750b887a` | `preserve_reasoning` mặc định BẬT ⇒ prompt nhiều lượt dài hơn; công thức ngân sách phải tính |
| `dc7aecf70` | cpp-httplib 0.54.0 — `[SUY LUẬN]` có thể đổi cách phát hiện ngắt kết nối |

Không commit nào thêm admission theo KV, metric KV, hay "chỉ giết một slot".
