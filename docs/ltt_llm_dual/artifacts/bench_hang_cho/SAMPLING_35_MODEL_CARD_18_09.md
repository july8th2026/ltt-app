# Thông số lấy mẫu theo model card — đối chiếu và A/B LTT-3.5 (18/09/2026, plan v2 Task 12)

Chỉ **đề xuất**. Không đổi cấu hình production, không deploy. Quyết định đổi thuộc phiên chính / chủ dự án (Step 3).

## 1. Nguồn (tra 18/09, không suy)

- HF `Qwen/Qwen3.5-9B` — model card, mục Best Practices.
- HF `Qwen/Qwen3.8-27B` — model card, mục Best Practices.
- Cờ engine: `H:\LTT_LLM\gateway\llama-swap.yaml` trên máy B, SHA-256 `168E23C9…5DFCA` = `llm_gateway/deploy/llama-swap.yaml` của kho (so khớp 18/09 14:5x).
- Tham số nền tảng gửi theo request: `apps/ltt_llm/features.py` (`kiem_tham_so_sinh`, `THAM_SO_CHUYEN_THANG`),
  `platform_core/runtime_noi_bo/luong.py` (`tien_kiem`/`chuan_bi`: `gui = dict(than)` + `chuan_hoa_suy_nghi`).
- llama.cpp ghim `91f6a6cf3`: `tools/server/server-common.cpp:1366-1369` (request ghi đè `reasoning_budget_tokens`),
  `:1308-1331` (`chat_template_kwargs` theo request).

## 2. Khuyến nghị của model card

| model · chế độ | temperature | top_p | top_k | min_p | presence_penalty | repetition_penalty | độ dài ra |
|---|---|---|---|---|---|---|---|
| **3.5-9B thinking — general** | 1.0 | 0.95 | 20 | 0 | **1.5** | 1.0 | 32.768 (81.920 cho toán/lập trình khó) |
| **3.5-9B thinking — precise coding** | **0.6** | 0.95 | 20 | 0 | **0.0** | 1.0 | như trên |
| 3.5-9B non-thinking — general | 0.7 | 0.8 | 20 | 0 | 1.5 | 1.0 | |
| 3.5-9B non-thinking — reasoning | 1.0 | 0.95 | 20 | 0 | 1.5 | 1.0 | |
| **3.8-27B thinking** (mọi effort `low/medium/xhigh`) | 1.0 | 0.95 | 20 | 0 | **0.0** | 1.0 | agent: suy nghĩ ≤ 262.144, trả lời ≤ 131.072 |
| 3.8-27B non-thinking | 0.7 | 0.8 | 20 | 0 | 1.5 | 1.0 | |

Khác về lịch sử suy nghĩ: card **3.5** nói lịch sử *"chỉ nên gồm phần trả lời cuối, không cần phần suy nghĩ"*;
card **3.8** có `preserve_thinking` bật mặc định (giữ khối suy nghĩ qua lịch sử). Template v22.5 dùng chung
(`chat_template_v22.5.jinja:8-14`) mặc định `preserve_thinking = true` cho **cả hai**.

## 3. Bảng lệch — card ↔ engine (yaml) ↔ nền tảng (theo request)

| tham số | card 3.5 (thinking gen / coding) | engine 3.5 (yaml) | card 3.8 thinking | engine 3.8 (yaml) | nền tảng gửi theo request | lệch |
|---|---|---|---|---|---|---|
| temperature | 1.0 / **0.6** | 1.0 | 1.0 | 1.0 | cửa đồng bộ: chỉ khi client gửi (0..2); cửa stream: nguyên thân client | **3.5 coding** (0.6 ↔ 1.0) |
| top_p | 0.95 | 0.95 | 0.95 | 0.95 | đồng bộ: client (0..1]; stream: client | không |
| top_k | 20 | 20 | 20 | 20 | đồng bộ: **rơi**; stream: client | không (trừ client tự gửi) |
| min_p | 0 | 0 | 0 | 0 | đồng bộ: rơi; stream: client | không |
| presence_penalty | **1.5** / 0.0 | **không đặt (0)** — cố ý, L-16 | 0.0 | không đặt (0) | đồng bộ: **rơi**; stream: client | **3.5 general** (1.5 ↔ 0) |
| repetition_penalty | 1.0 | mặc định llama.cpp 1.0 | 1.0 | 1.0 | — | không |
| suy nghĩ | bật | `--reasoning on` | bật, effort xhigh mặc định | `--reasoning-effort xhigh` | L-26: gỡ mọi ghi đè; 3.8 chuẩn hoá effort | không |
| budget suy nghĩ | card không đặt budget | `--reasoning-budget 2048` | card: ≤ 262.144 | `--reasoning-budget 4096` | L-26: gỡ; đồng bộ 3.5 tự đặt `max_tokens − 512` (≤ 2048) | **lệch lớn (trần vận hành L-20, không phải số Qwen)** |
| độ dài ra | 32.768 | `TOKEN_RA_TRAN` 32.768; mặc định sync 1.024 / stream·job 32.768 | 131.072 | như 3.5 | client | 3.5 đúng card ở stream/job; **sync 1.024** thấp hơn card |
| suy nghĩ trong lịch sử | **bỏ** | template `preserve_thinking=true` | giữ | giữ | L-26: gỡ `preserve_thinking` của client ⇒ luôn giữ | **3.5** (R-17) |

Ghi chú lệch:
- **presence_penalty 3.5** là lệch có chủ ý: L-16 (12/09) đo trên 3.8 — thêm 1.5 tốn ~11 % decode (56,61 → 63,01 tok/s)
  mà bộ đề 60 bài không đổi (59/60). Chưa từng đo **riêng 3.5**, và bộ đề khi đó bão hoà (59/60) ⇒ không phân biệt được.
- **temp coding 3.5**: engine chỉ có MỘT bộ lấy mẫu mỗi hồ sơ; card tách general/coding. Nền tảng không biết một
  request là "coding" hay không ⇒ muốn theo card phải gửi theo request (client/app), không đổi được bằng cờ engine
  mà không làm lệch chế độ general.
- Nền tảng **không tự gửi** tham số lấy mẫu nào. Cửa stream (`/messages`, `/responses`) chuyển nguyên thân client
  (`gui = dict(than)`, chỉ gỡ trường suy nghĩ theo L-26) ⇒ Claude Code/Codex/SDK gửi gì engine nhận nấy; cửa đồng bộ
  chỉ chuyển `temperature`, `top_p` (`presence_penalty`, `top_k`, `min_p` bị rơi).

## 4. A/B trên bộ đề cố định (Step 1–2) — KẾT QUẢ (18/09 16:17–17:58)

**Không nạp lại model nào.** Mọi biến gửi THEO REQUEST thẳng llama-swap của B (`ssh -L`), xác minh trước khi đo:
- `reasoning_budget_tokens: 64` ⇒ suy nghĩ 3.772 → 263 ký tự (engine nhận ghi đè budget theo request).
- ⚠️ `chat_template_kwargs.preserve_thinking: false` **không có tác dụng**: `/apply-template` ra 235 ký tự như mặc định.
  llama.cpp (`common/arg.cpp:958-960`) tự nạp `preserve_reasoning="true"` vào kwargs mặc định, và template v22.5:8-14 đọc
  `preserve_reasoning` TRƯỚC `preserve_thinking` ⇒ khoá sau bị che. `preserve_reasoning: false` ⇒ 137 ký tự (mất khối
  suy nghĩ). Công cụ dùng `preserve_reasoning` (commit a4f03331). Hệ quả phụ: gỡ `preserve_thinking` của khách ở L-26
  vốn không đổi gì; muốn máy chủ quyết điều này phải dùng `--no-reasoning-preserve` (cờ engine) hoặc khoá `preserve_reasoning`.

Công cụ `tools/ab_lay_mau_35.py` (test_1451 — mỗi bài có lời giải tham chiếu mà bộ chấm phải cho đạt; test bắt được một
bài sai đề (c09) trước khi đo). 30 bài: `code` 10 (chấm bằng chạy thật), `vi` 10, `tool` 6, `agent` 6 kịch bản 3 lượt
(kịch bản + hàm chấm của `ab_lich_su_suy_nghi.py`, giữ `reasoning_content` trong lịch sử như client). 3 lượt × mỗi cặp,
A và B xen kẽ ngay sau nhau, `--song-song 2` (một slot để khách), `max_tokens` 8.192. 402 lượt, 0 lỗi HTTP.
Thô: `kiem_dinh_ky_18_09/ab_lay_mau_35.jsonl`, phán quyết: `ab_lay_mau_35_phan_quyet.json`. Luật khoá trước khi đo
(docstring công cụ): **thắng rõ** = McNemar chính xác p < 0,05, b > c và không nhóm nào tụt dưới Wilson 95 % của A.

| phép (một biến) | A đúng | B đúng | chỉ B / chỉ A | p | theo nhóm (A → B) | token ra p50 | giây p50 | phán quyết |
|---|---:|---:|:-:|---:|---|---|---|---|
| presence_penalty 0 → **1,5** | 87/96 | 90/96 | 5 / 2 | 0,45 | code 22→25 · vi 29→29 · tool 18→18 · agent 18→18 | 550 → 625 (+14 %) | 13,2 → 18,3 (+39 %) | không thắng rõ, không tụt |
| temp coding 1,0 → **0,6** | 22/30 | 25/30 | 3 / 0 | 0,25 | code 22→25 | 2.192 → 2.171 | 39,9 → 40,8 | không thắng rõ (nghiêng B), không tụt |
| budget 2.048 → **4.096** | 87/96 | 88/96 | 3 / 2 | 1,00 | code 22→24 · vi 29→28 · tool/agent = | 550 → 580 | 13,2 → 15,7 (+19 %) | không thắng rõ, không tụt |
| **R-10** system = base instructions mặc định Codex | 58/66 | **47/66** | 2 / **13** | **0,007** | code 22→**17** · tool 18→18 · agent 18→**12** (dưới Wilson A) | 455 → 211 | 10,8 → 5,3 | **B TỤT rõ** |
| **R-17** `preserve_reasoning` true → false | 18/18 | 18/18 | 0 / 0 | 1,00 | agent 18→18 | 281 → 265 | 6,7 → 5,8 | không phân biệt (xem dưới) |

Đọc đúng phạm vi:
- **Bộ đề chạm trần ở `tool`, `agent`, `vi`** (A 18/18, 18/18, 29/30) ⇒ phần phân biệt gần như chỉ ở `code` (22/30). Hai bài
  0/3 ở mọi biến thể (`c10` đọc số tiếng Việt — hết 8.192 token; `c08` bộ phân tích biểu thức chỉ `pp15` 2/3, `t06` 1/3).
  n = 30 cặp code không đủ để một khác biệt 3 bài có ý nghĩa.
- `presence_penalty` 1,5 **không mua được gì đo được** và tốn +39 % thời gian trung vị trên 3.5 — cùng chiều với L-16 (đo trên
  3.8). Giữ vắng mặt. `lap` (vòng lặp chữ) 1 lượt ở cả A lẫn pp15 ⇒ không có vòng lặp để nó chữa trên bộ đề này.
- Budget 4.096 không thắng và chậm hơn 19 %. 4 lượt `length` 8.192 của rb4096: sau khi budget cắt, model **tiếp tục suy
  nghĩ trong `content`** (ví dụ c08: content mở đầu bằng "Wait, left recursion…") — đúng lỗi *truncated thinking* đã ghi ở
  yaml (G3c). Budget lớn hơn không chữa, chỉ dời chỗ.
- **R-10 — giữ `base_instructions: ""`.** Prompt mặc định của Codex (`openai/codex@7498521d` `codex-rs/models-manager/prompt.md`,
  20.903 byte, sha256 `ac8ae107…`) làm 3.5-9B tụt rõ: code −5, agent −6/18 (bỏ bước, trả lời chữ thay vì gọi tool), prompt
  ×10 (51K → 511K token tổng). Giới hạn: prompt đó nói tới `shell`/`apply_patch` mà bộ đề không khai — trong Codex thật các
  tool đó có mặt; nhưng chiều tụt đủ lớn (p = 0,007) để không nên đổi mà không có phép đo Codex thật.
- **R-17 — phép này vô hiệu do cấu trúc, không phải "không khác".** Template v22.5:332 giữ suy nghĩ của mọi lượt assistant
  **sau tin nhắn user cuối** bất kể cờ; vòng agent (Codex/Claude Code: một câu hỏi, nhiều lượt tool) chỉ có một tin user ⇒
  cờ không đổi prompt. Nó chỉ có tác dụng từ tin nhắn user thứ hai trở đi. Đo cơ chế bằng `/apply-template` + `/tokenize`
  (hội thoại tổng hợp, ~700 token suy nghĩ/lượt): prompt ở lượt user thứ 4 = **2.504 token (giữ) vs 449 (bỏ)**; tiền tố
  chung với prompt lượt trước: giữ 1.679/1.679, bỏ 307/309 ⇒ cache tiền tố vẫn trúng gần hết phần prompt cũ, nhưng KV của
  phần suy nghĩ model vừa sinh không dùng lại được (phải prefill lại câu trả lời cuối, ~140 token). Chất lượng qua nhiều lượt
  user **chưa đo** — cần kịch bản nhiều câu hỏi nối tiếp.
- Tỉ lệ trúng cache trong bảng phụ (`ti_le_cache`) **lệch theo thứ tự** (A luôn chạy trước trên prompt mới, B hưởng cache của
  A) — không dùng để so A/B; chỉ `prompt_tong` so được.

## 5. Đề xuất (Step 3 — chỉ đổi khi thắng rõ ⇒ KHÔNG đổi production)

1. **Không đổi `llama-swap.yaml`.** Không phép nào "thắng rõ"; không cần nạp lại model. B giữ nguyên SHA `168E23C9…`
   (kiểm 18:0x), hai model trả lời, `/health` 200.
2. `presence_penalty`: giữ 0 cho 3.5 — lệch card có chủ ý, nay có số đo riêng 3.5 (không lợi, +39 % thời gian). Ghi vào L-mới.
3. Temp 0,6 cho coding (card): tín hiệu dương nhẹ (3/0), không thể đặt ở engine mà không làm lệch chế độ general. Nếu muốn
   theo card: gửi `temperature: 0.6` **theo request** từ client coding (preset LTTCODE / cấu hình Codex–Claude do bộ cài
   sinh) — cửa stream đã chuyển nguyên thân. Cần thêm mẫu (≥ 100 cặp code) trước khi chốt.
4. Budget 2.048 cho 3.5: giữ.
5. R-10: giữ `base_instructions: ""` (tụt rõ khi dùng prompt Codex).
6. R-17: card 3.5 khuyên **bỏ** suy nghĩ khỏi lịch sử; engine hiện giữ. Đo thêm bằng kịch bản nhiều tin user (chất lượng +
   token) rồi mới quyết `--no-reasoning-preserve` cho `qwen35-api` (cờ engine ⇒ nạp lại model, cửa sổ bảo trì). Sửa
   hiểu lầm: khoá hiệu lực là `preserve_reasoning`, không phải `preserve_thinking`.
