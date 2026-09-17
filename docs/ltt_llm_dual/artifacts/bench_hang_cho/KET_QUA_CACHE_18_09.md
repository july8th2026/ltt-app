# Kết quả đo prompt cache LTT-3.5 / LTT-3.8 — 18/09/2026

**Kết luận một dòng: prompt cache CHẠY TỐT trên cả hai model ở cấu hình production —
99,58–99,64 % token tiền tố được tái dùng, TTFT rơi từ 5,8–26,6 s xuống ~1,0–1,9 s.
Câu "3.5 prompt cache 0/30 hits" trong `KET_QUA_DO_17_09.md` §3 (m6) là **hiện vật của
phép đo**, không phải tính chất của model.**

## 0. Điều kiện đo — đọc trước khi dùng số

| mục | giá trị |
|---|---|
| Đường đo | production `https://app.lttstudios.com/api/v1`, khoá thử `khach3.thu` |
| Hai cửa | `POST /chat/completions` (non-stream, đọc `x_ltt.cached_prompt_tokens`) và `POST /messages` (SSE, đọc `usage.cache_read_input_tokens` của **chính llama.cpp**) |
| Đối chứng máy B | `http://127.0.0.1:8280/logs` — `slot print_timing ... prompt eval time = ... / N tokens` |
| Prompt | tài liệu tổng hợp ~9,8–10,0K token, cố định tuyệt đối (không nonce, không dấu thời gian); mỗi phép một `seed` riêng ⇒ lượt 1 **chắc chắn lạnh** |
| Mỗi lượt sau | cùng tiền tố + 1 cặp (user ngắn, assistant cố định) ⇒ delta 36–42 token |
| Cấu hình engine | `b10883-91f6a6cf3`, **không** `--no-cache-idle-slots`, `-kvu -np 3 --spec-type draft-mtp --spec-draft-n-max 2`, 3.5 `-c 262144` KV q8_0, 3.8 `-c 221184` KV q4_0, `ttl 1800` |
| Chi phí | **15 credit** (4977 → 4962), trần cho phép ~600 |
| ⛔ Đã KHÔNG làm | không restart dịch vụ, không unload model, không sửa `llama-swap.yaml`, không đụng máy A |

⚠️ **Lưu lượng nền:** lúc 02:21–02:47 có lưu lượng nội bộ thật (`runtime_noi_bo.luong`,
ChatLTT/phiên khác) chạy song song. Nó **không** làm hỏng số: mỗi lượt được engine tính
riêng. Nó chỉ làm TTFT lượt lạnh của 3.8 dao động 10,4–26,6 s (xếp hàng), nên cột TTFT
lạnh đọc là *khoảng*, không phải hằng số.

🔴 **Sự cố giữa phiên (không phải do phép đo):** 00:54:38–00:56:00 một phiên khác deploy
máy A (`C:\LTTPlatform\app` bị ghi lại 00:55:38, nssm + worker khởi động lại 00:55:46).
Production trả **502** ~90 giây rồi tự hồi. Xem §6 — nó để lại một hậu quả đáng sửa.

---

## 1. Hội thoại lặp lại (cùng tiền tố, +1 lượt ngắn) — CÓ tái dùng cache

### Cửa SSE (`/messages`) — TTFT thật, số của chính llama.cpp

**LTT-3.5** (`seed 91`, 5 lượt liên tiếp, không nghỉ):

| lượt | token prompt | **token phải nạp lại** | token trúng cache | tỷ lệ trúng | **TTFT** |
|---|---|---|---|---|---|
| 1 | 9.848 | **9.848** | 0 | 0 % | **5,808 s** |
| 2 | 9.882 | **38** | 9.844 | 99,62 % | **0,999 s** |
| 3 | 9.919 | **41** | 9.878 | 99,59 % | **1,019 s** |
| 4 | 9.957 | **42** | 9.915 | 99,58 % | **1,007 s** |
| 5 | 9.989 | **36** | 9.953 | 99,64 % | **1,045 s** |

**LTT-3.8** (`seed 31`, 5 lượt liên tiếp):

| lượt | token prompt | **token phải nạp lại** | token trúng cache | tỷ lệ trúng | **TTFT** |
|---|---|---|---|---|---|
| 1 | 9.886 | **9.886** | 0 | 0 % | **26,631 s** (có xếp hàng; lượt lạnh cô lập `seed 71`: 10,429 s) |
| 2 | 9.920 | **38** | 9.882 | 99,62 % | **1,306 s** |
| 3 | 9.957 | **41** | 9.916 | 99,59 % | **1,310 s** |
| 4 | 9.995 | **42** | 9.953 | 99,58 % | **1,527 s** |
| 5 | 10.027 | **36** | 9.991 | 99,64 % | **1,459 s** |

### Cửa non-stream (`/chat/completions`) — cùng kết luận

`prompt_tokens` ở cửa này là prompt **đầy đủ**; `x_ltt.cached_prompt_tokens` là phần trúng.
Hai model cho **con số trùng khít nhau** (cùng tài liệu, cùng khuôn chat):

| lượt | prompt | cached (3.5 `seed 11`) | cached (3.8 `seed 81`) | nạp lại | giây cả lượt 3.5 / 3.8 |
|---|---|---|---|---|---|
| 1 | 9.874 | 0 | 0 | **9.874** | 12,203 / 14,212 |
| 2 | 9.908 | 9.870 | 9.870 | **38** | 7,514 / 3,257 |
| 3 | 9.945 | 9.904 | 9.904 | **41** | 6,703 / 2,480 |
| 4 | 9.983 | 9.941 | 9.941 | **42** | 1,526 / 2,760 |
| 5 | 10.015 | 9.979 | 9.979 | **36** | 8,147 / 3,566 |

### Đối chứng engine (`/logs` máy B) — khớp từng token

```
prompt eval time =  8229.06 ms /  9874 tokens (0.83 ms/tok, 1199.89 tok/s)   <- lượt 1 lạnh
prompt eval time =   498.88 ms /    38 tokens                                 <- lượt 2
prompt eval time =   539.45 ms /    41 tokens                                 <- lượt 3
prompt eval time =   596.52 ms /    42 tokens                                 <- lượt 4
prompt eval time =   635.88 ms /    36 tokens                                 <- lượt 5
slot get_availabl: selected slot by LCP similarity, f_sim_best = 0.996 (> 0.100 thold), f_keep = 0.950
```

⇒ `f_sim_best` **0,996–1,000** (không phải 0,59 như 17/09), và số token thật sự nạp lại
đúng bằng delta của lượt. **Không một dòng `do_reset` / `erasing old context checkpoint` nào.**

---

## 2. Có sống sót khi request khác chiếm hai slot kia không? — **CÓ**

Kịch bản: lượt A → 2 prompt lạ 7,1K token (chiếm slot 1 và 0) → lượt A tiếp.

**LTT-3.5** (`seed 41`):

| bước | slot engine | token nạp lại | trúng cache | TTFT |
|---|---|---|---|---|
| A lượt 1 | 2 | 9.848 | 0 | 15,848 s |
| lạ #1 | 1 (LRU, mới) | 7.085 | 0 | 4,199 s |
| lạ #2 | 0 (LRU, mới) | 7.085 | 0 | 4,150 s |
| **A lượt 2** | **2 (về đúng slot cũ)** | **38** | **9.844 (99,62 %)** | **1,321 s** |
| lạ #1 lần 2 | 1 | **4** | 7.081 | 1,158 s |
| lạ #2 lần 2 | 0 | **4** | 7.081 | 1,057 s |
| **A lượt 3** | 2 | **41** | **9.878 (99,59 %)** | **1,273 s** |

**LTT-3.8** (`seed 51`): cùng hình dạng — A lượt 2 nạp lại **38** (trúng 9.882, TTFT 1,812 s),
hai prompt lạ lần hai nạp lại **4** token, A lượt 3 nạp lại **41** (trúng 9.916, TTFT 1,703 s).

⇒ Với `-np 3`, **ba hội thoại giữ ba slot riêng và không cái nào đạp cái nào**. Không có
"slot stealing" ở mức ba hội thoại.

### 2b. Nhiều hội thoại HƠN số slot — vẫn trúng (đây là chỗ 17/09 hiểu nhầm)

Xoay vòng N hội thoại **khác hẳn nhau** trên 3 slot, mỗi hội thoại 3 vòng (LTT-3.5):

| N hội thoại | vòng 1 (bắt buộc lạnh) | vòng 2 | vòng 3 |
|---|---|---|---|
| **5** (> 3 slot) | 0/5 trúng — 0 % | **5/5 trúng — 99,6 %** | **5/5 trúng — 99,6 %** |
| **8** (> 2× slot) | 0/8 trúng — 0 % | **8/8 trúng — 99,6 %** | **8/8 trúng — 99,6 %** |

⇒ Hội thoại bị đẩy khỏi slot **được khôi phục từ prompt cache trong RAM** (`--cache-ram`
mặc định 8192 MiB), kể cả với model lai. Đây là bằng chứng trực tiếp bác bỏ câu
*"trạng thái hồi quy không cắt lùi được ⇒ cache không mua gì cho LTT-3.5"*.

---

## 3. Có sống sót qua khoảng im lặng không? — **CÓ, cả 3 phút và 10 phút**

Trong `ttl = 1800 s`, một hội thoại, không lưu lượng của chính nó ở giữa:

| model | lượt 1 (lạnh) | **nghỉ 180 s** → lượt 2 | **nghỉ 600 s** → lượt 3 |
|---|---|---|---|
| **LTT-3.5** (`seed 61`) | 9.848 nạp lại · TTFT 6,022 s | **38** nạp lại · trúng 9.844 (**99,62 %**) · TTFT **1,319 s** | **41** nạp lại · trúng 9.878 (**99,59 %**) · TTFT **1,228 s** |
| **LTT-3.8** (`seed 71`) | 9.886 nạp lại · TTFT 10,429 s | **38** nạp lại · trúng 9.882 (**99,62 %**) · TTFT **1,629 s** | **41** nạp lại · trúng 9.916 (**99,59 %**) · TTFT **1,854 s** |

⇒ Im lặng 10 phút **không** làm mất cache. (Chưa đo mốc vượt `ttl` 1800 s — khi llama-swap
nhả model thì cả VRAM lẫn prompt cache RAM của tiến trình đó mất theo, đó là thiết kế.)

---

## 4. LTT-3.5 có lý do cấu trúc nào để trượt không? — **KHÔNG, ở cấu hình hiện tại**

Đo thật nói **không trượt** (mục 1–3). Tra nguồn upstream để biết *vì sao* và *khi nào thì trượt*:

| nghi can | phán quyết | bằng chứng |
|---|---|---|
| `--spec-type draft-mtp` | **Không phải thủ phạm — nó là thứ CHO PHÉP cắt lùi.** `n_rs_seq` (cơ chế duy nhất để model hồi quy lùi một phần) chỉ khác 0 khi bật spec-decoding; `n_rs_seq = --spec-draft-n-max` ⇒ cửa sổ lùi hiện tại là **2 token**. Tắt MTP sẽ làm cache **tệ hơn**. | ggml-org/llama.cpp **#28425** (mở), **#24320** (đóng not_planned) |
| `--cache-type-k/v q8_0` (3.5) và `q4_0` (3.8) | **Không phải.** Cả `q8_0` lẫn `q4_0` đều nằm trong bộ kernel FA mặc định của CUDA. (⚠️ `q4_1/q5_0/q5_1` mới là loại rơi về attention CPU — **đừng đổi sang chúng**.) | **#28455** (đóng, completed); **#27109** (mở, sập với q4_1 trên đúng arch `qwen35`) |
| Qwen3.5 lai / Gated DeltaNet | **Là rủi ro thật nhưng KHÔNG khai hoả ở đây.** Sâu hơn 2 token phải nhờ *context checkpoint*; khi checkpoint thiếu/bị đuổi thì `do_reset` ⇒ nạp lại toàn bộ. Log của ta **không có** dòng đó, và phép 2b cho thấy khôi phục từ RAM cache chạy. Mặc định đang dùng: `--ctx-checkpoints 32`, `--checkpoint-min-step 8192`. (Cờ `--swa-checkpoints` **không tồn tại**.) | **#21831**, **#24055**, **#28194**, **#25913**, **#28280** (đều mở); PR sửa cấu trúc **#24785** mở từ 18/06, **chưa merge** |
| `-kvu` | Khuếch đại, không chặn: dưới `-kvu`, KV của slot rảnh bị xoá khỏi VRAM và **đẩy sang prompt cache RAM** ⇒ mọi lượt quay lại đều phụ thuộc RAM cache còn giữ entry hay không. Đó chính là biến số ở §5. | `server-context.cpp` `[TAG_IDLE_SLOT_CLEAR]`; **#27148** (mở) |
| `--no-cache-idle-slots` | **Đây là thứ đã làm hỏng phép m6 ngày 17/09.** Nó **tắt việc đẩy slot rảnh vào prompt cache RAM**. Production **không** có cờ này; server thử 17/09 **có** (chép từ `/running` lúc phiên Serving V2 còn đang đo ma trận C1 — xem O-19 trong `RUNBOOK.md`). Với 11 hội thoại trên 3 slot mà không có RAM cache, mọi lượt quay lại đều mất tiền tố ⇒ đúng **0/30**, và `f_sim ≈ 0,59` là dấu vết của "rơi vào slot người khác". | `RUNBOOK.md` §O-19; `KET_QUA_DO_17_09.md` §3 |

**Hai cảnh báo độc lập với cache, vẫn áp dụng cho `-np 3 --spec-type draft-mtp`:**
**#28286** (MTP + `--parallel > 1` lẫn nội dung giữa các slot) và **#26425** (MTP giữ trạng
thái giữa các request ⇒ đầu ra không tất định). Cả hai đang **mở**.

---

## 5. Con số "trúng cache" mà client thấy có đáng tin không? — **CÓ trên cửa SSE; KHÔNG có trên hai cửa khác**

| cửa | client thấy gì | có khớp engine không |
|---|---|---|
| **`/api/v1/messages` SSE** (LTTCODE dùng) | `usage.cache_read_input_tokens` — gateway chuyển tiếp SSE **nguyên xi**, nên đây là số của **chính llama.cpp** | ✅ **Khớp tuyệt đối.** `input_tokens=38` (chỉ phần chưa cache) + `cache_read=9.844` = 9.882; engine nạp lại đúng **38** token. LTTCODE tính `cacheRead / (uncached + cacheRead + cacheWrite)` = **99,62 %** — đúng |
| **`/api/v1/chat/completions`** | `usage` **không** có `prompt_tokens_details`; số nằm ở khối riêng **`x_ltt.cached_prompt_tokens`** | ✅ Số đúng (9.870/9.908 = 99,62 %) nhưng ⚠️ **client OpenAI chuẩn đọc `usage.prompt_tokens_details.cached_tokens` sẽ thấy RỖNG** |
| **`/api/v1/messages` non-stream** | 🔴 **Mất hẳn** — `_dang_anthropic` chỉ trả `input_tokens`/`output_tokens` | ❌ Client thấy "không có cache" dù nền tảng đã đo được và đã dùng nó để tính tiền |

**Kết luận Q5:** con số phần trăm LTTCODE hiển thị **đáng tin** — nó đi thẳng từ llama.cpp
và khớp từng token với `prompt eval time` của engine. Nhưng nó chỉ đáng tin **vì LTTCODE
đi cửa SSE**. Cùng một lượt qua `/messages` non-stream sẽ báo 0 %, và qua `/chat/completions`
sẽ báo 0 % với bất kỳ client OpenAI chuẩn nào.

*(Mã liên quan: `platform_core/llm/cong_vlm.py:195-224` đọc `timings.cache_n` rồi mới tới
`prompt_tokens_details.cached_tokens`; `server/api/chat.py:715-749` dựng `x_ltt`;
`server/api/streaming.py:558-616` là chỗ làm rơi số; `llm_gateway/api.py:1060-1063` +
`upstream.py:110-150` xác nhận gateway không sửa một byte.)*

---

## 6. 🔴 Phát hiện ngoài đề: lease `mode='sync'` mồ côi khoá 3090 suốt 20 phút

Khi phiên khác deploy lúc 00:55, worker bị giết **giữa** một lượt `/chat/completions` của
3.8. Dòng `execution_leases` còn lại:

```
resource='ltt_38_3090'  slot=0  mode='sync'  token_dat_truoc=14457
acquired_at = heartbeat_at = 00:54:55.896   (nhịp tim KHÔNG BAO GIỜ tiến thêm)
```

Hậu quả đo được: **mọi** lượt 3.8 trả `429 concurrency_limited / reason=het_cho` trong
**20 phút** (00:55 → 01:14:55), 10 lượt của phép đo này dính, mỗi lượt chờ đủ 60 s.

Nguyên nhân: `platform_core/llm/admission.py` đặt hạn mồ côi **riêng** cho `stream` (180 s)
và `job` (300 s), nhưng `mode='sync'` rơi vào mặc định **`ORPHAN_TIMEOUT = 20 phút`**.
Một lượt sync chết giữa chừng vì thế khoá tài nguyên lâu gấp 6,7 lần một lượt stream chết
giữa chừng — dù nó là loại lượt **ngắn nhất** (trần 90 s, xem thông điệp lỗi của chính cổng).

**Đề nghị:** thêm `ORPHAN_TIMEOUT_SYNC` cỡ **120 s** vào `_han` trong `reclaim_expired`.
Không thuộc phạm vi phiên đo này nên **chưa sửa**.

---

## 7. Đổi gì trong cửa sổ bảo trì

Xếp theo tỉ lệ *lợi ích / rủi ro*. ⚠️ Cả ba mục đầu đều cần **sửa `llama-swap.yaml` +
restart `LTTLlamaSwap`**, và restart = **unload cả hai model** (§7.4).

| # | đổi gì | vì sao (số đo) | rủi ro |
|---|---|---|---|
| **1** | **`--cache-ram 24576`** (24 GiB) cho **cả hai** model, thay mặc định 8192 | Log máy B đã ghi **8 lần** `making room for prompt cache entry, removing oldest entry` với **`size = 885.686 MiB`** (và 410,8 MiB) trong chính phiên này. Ở ~886 MiB/hội thoại, 8 GiB chỉ chứa **~9 hội thoại** — phép 2b (n=8) vừa khít, n=11 (đúng kịch bản m6 17/09) sẽ bắt đầu đuổi. Máy B còn **≥ 73 GB RAM trống** (đo 17/09). | Thấp — chỉ là RAM hệ thống, không đụng VRAM |
| **2** | **`--ctx-checkpoints 8`** (thay mặc định 32) | Một entry cache gói cả KV + trạng thái draft MTP + **mọi** checkpoint; checkpoint model lai đo được **112–150 MiB/cái** (#28194, #24055). 32 checkpoint ≈ 4,8 GiB **trước** phần KV ⇒ chính là lý do entry phình tới 886 MiB. Giảm còn 8 làm entry nhỏ đi nhiều, đổi lại mật độ điểm lùi thưa hơn. | Trung bình — cần đo lại mục 1–3 sau khi đổi |
| **3** | **`-watch-config`** cho `LTTLlamaSwap` | Tiến trình hiện chạy `llama-swap.exe --config ... --listen 127.0.0.1:8280` — **không có `-watch-config`** ⇒ mọi lần chỉnh yaml đều phải restart dịch vụ, tức **unload CẢ HAI model**. Bật một lần cờ này thì lần sau **chỉnh một model, nạp lại một model**, model kia không bị đụng. Nên làm **cùng** mục 1–2, vì đây là lần restart mà ta đằng nào cũng phải trả. | Thấp, nhưng phải đọc lại `/running` sau khi lưu yaml để xác nhận cấu hình mới đã có hiệu lực (bẫy "tệp đã chép mà chưa restart" — `RUNBOOK.md` §2.3) |
| **4** | Chuyển nhả GPU sang **`POST /api/models/unload/:model_id`** | Đang nối `LTT_HO_DUNG_CARD=llm=http://127.0.0.1:8280/unload` — `GET /unload` **đuổi TẤT CẢ**, nên một job ảnh xin 3090 nhả luôn **LTT-3.5** trên card không ai tranh (L-17). Endpoint theo từng model có sẵn. | Thấp; đã ghi sẵn trong `DECISION_LOG.md` L-17 |
| **5** | ⛔ **KHÔNG** thêm `--no-cache-idle-slots` | Chính nó đã tạo ra kết luận sai "0/30" ngày 17/09. | — |
| **6** | ⛔ **KHÔNG** đổi `--cache-type-k/v` sang `q4_1/q5_0/q5_1` | Rơi khỏi bộ kernel FA của CUDA ⇒ attention chạy CPU (#28455, #27109). | — |

**Chưa đo / còn nợ:**
- Mốc vượt `ttl = 1800 s` (model bị nhả) — chưa chạm, vì chạm là unload.
- Ngưỡng N hội thoại làm sập tỷ lệ trúng ở `--cache-ram` 8192 (đo tới N=8 vẫn 100 %).
- Ảnh hưởng của `--ctx-checkpoints 8` lên tỷ lệ trúng — **phải** đo lại sau khi đổi.
- Prompt > 20K token: phép này cố tình ở dải 8–20K theo yêu cầu.

**Dữ liệu thô:** mọi con số dùng để kết luận đã nằm nguyên trong các bảng trên (không có
bảng nào là trung bình che số lẻ — mỗi ô là **một lượt thật**). JSONL từng lượt
(`cached`, `eval_moi`, `ttft`, `usage_stream`, `x_ltt`) chỉ nằm ở scratchpad của phiên và
**cố ý không commit** — phiên này được yêu cầu commit đúng một tệp. Tái lập: mỗi phép chỉ
cần `seed` ghi trong bảng cộng với cấu hình ở §0.
