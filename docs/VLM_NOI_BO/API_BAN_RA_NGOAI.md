# API model bán ra ngoài — thiết kế lại theo mục tiêu thật

**2026-08-22.** Chủ dự án đính chính: **không dùng Codex hay Claude Code trên
LTTSTUDIOSAPP.** Mục tiêu là **một API model bán ra ngoài**, để khách cắm vào và
xây bot, y như họ đang cắm API của Gemini/OpenAI.

Đính chính này **đổi trọng tâm công việc**, và nó làm một quyết định trước đó
(mốc ngữ cảnh 200K) trở thành **tối ưu sai hướng**. Tài liệu này ghi lại vì sao.

---

## 1. Cái gì đổi, cái gì không

| | Trước (tưởng là Codex/Claude Code) | Sau (API bán ra ngoài) |
|---|---|---|
| Khách hàng | 1–2 người, trong LAN | **nhiều, ngoài Internet, qua Cloudflare** |
| Giao thức bắt buộc | `/v1/responses` (Codex) + `/v1/messages` (Claude Code) | **`/v1/chat/completions`** — thứ mọi SDK nói |
| Xác thực | một bearer token trong LAN | **khoá API theo từng khách**, hạn mức, sổ credit |
| Ngữ cảnh cần | rất dài (phiên agent) | **vừa phải** — xem §3 |
| Nút thắt | VRAM | **Cloudflare 100 giây** |
| Tính tiền | không cần | 🔴 **bắt buộc, theo token** |

**Không đổi:** máy B, llama.cpp, hai hồ sơ model, trọng tài GPU, template đã vá.
`llm_gateway` vẫn đúng nguyên — nó vốn đã phơi cả ba giao thức. Hai đường
`/v1/responses` và `/v1/messages` giờ chỉ là **tương thích tặng kèm**, không mất
gì để giữ.

---

## 2. 🔴 Ràng buộc mới, và nó cứng: **Cloudflare cắt ở 100 giây**

`CLAUDE.md` ghi rõ: chờ phản hồi quá **100 giây** thì Cloudflare trả **524**, dù
máy vẫn chạy tốt. Với API ảnh/video ta né bằng hàng đợi job. **Với API chat thì
không né được** — khách gọi `/v1/chat/completions` và chờ tại chỗ.

Ghép với số prefill đo được của cộng đồng trên card cùng lớp
(`llama-bench pp512 = 1.132 tok/s`; cấu hình thường trú prefill **842–1.083 tok/s**):

| Token đầu vào | Thời gian prefill ước tính | Qua được Cloudflare? |
|---:|---:|---|
| 4.000 | ~4 s | ✅ |
| 16.000 | ~16 s | ✅ |
| 50.000 | ~50 s | ⚠️ sát |
| 100.000 | ~100 s | ❌ **524** |
| 200.000 | **~200 s** | ❌ **524 chắc chắn** |

⇒ **Trần đầu vào cho lời gọi đồng bộ qua Cloudflare: ~50.000 token**, và đó là con
số phải đo lại chứ không phải chốt luôn.

Ba đường xử lý phần vượt trần, chọn ở P5 sau khi đo:

1. **Chặn thẳng** — trả 413 kèm thông báo rõ. `ngan_sach.py` đã làm sẵn việc này.
2. **Nhịp tim SSE** — cổng phát một dòng bình luận SSE ngay lập tức để Cloudflare
   thấy phản hồi đã bắt đầu, rồi mới tới token thật. Cần kiểm CF có chấp nhận không.
3. **Đường job không đồng bộ** — ngữ cảnh rất dài đi qua `POST /api/v1/jobs` như
   ảnh/video. Hạ tầng đã có sẵn.

---

## 3. ⚠️ Mốc 200K: đúng cho Codex, **sai cho API bán ra ngoài**

Chủ dự án chốt 200K khi mục tiêu còn là phiên agent dài. Với mục tiêu mới, ba lý
do khiến nó thành tối ưu sai hướng:

### (a) Con số 200K của cộng đồng được đo với prompt **400 token**

Chú thích của chính hàng đó: *"clean probe, 3×400 tokens, medians of 3"*. Tức
**54,2 tok/s ở "ngữ cảnh 200K" là tốc độ khi cửa sổ gần như RỖNG.**

Một người đóng góp khác đã cảnh báo đúng cái bẫy này, thành một mục riêng:

> *"How much context this card can actually hold, and why the allocation number
> flatters it."* … *"a row's context column — mine included — is an allocation
> number."*

Người đó **đổ đầy ngữ cảnh thật** rồi đo lại, và kết luận cho card của họ là
**"the usable answer for this card is 64K"**, không phải con số cấp phát.

⚠️ **Trung thực về nguồn:** nghiên cứu đó chạy trên **RTX 3080 10 GB** với
`UD-IQ2_XXS`, **không phải 3090 24 GB**. Con số 64K của họ **không chuyển thẳng
sang máy ta**. Cái chuyển được là **bài học**: cột ngữ cảnh trong mọi bảng là con
số *cấp phát*, và **chưa ai trong bảng chứng minh 200K ngữ cảnh ĐƯỢC ĐỔ ĐẦY trên
card 24 GB**.

### (b) Khách xây bot không gửi 200K token

Bot gọi API gửi 1–10K token mỗi lượt. Cửa sổ 200K cấp phát sẵn **~6 GB VRAM cho
một cái kho gần như luôn rỗng** — VRAM đó đáng lẽ là biên an toàn.

### (c) 200K và Cloudflare loại trừ nhau

Xem §2: một prompt lấp đầy cửa sổ 200K **không bao giờ trả lời kịp trước khi
Cloudflare cắt**. Cấu hình một cửa sổ mà khách không dùng nổi là bán một lời hứa
không giữ được.

### ✅ ĐÃ CHỐT 22/08/2026 — ba hồ sơ

| Hồ sơ | Ngữ cảnh | KV | VRAM ước | Phục vụ ai |
|---|---|---|---|---|
| **`ltt_llm`** ← **MẶC ĐỊNH** | **64K** | q8_0 | ~19,0 GB | **khách ngoài qua Cloudflare.** Prefill nhanh, biên VRAM dày |
| `ltt_llm_ops` | 200K | q4_0 | ~23,3 GB | **chỉ trong LAN.** Không mở ra Internet |
| `ltt_llm_vision` | 64K | q8_0 | ~19,9 GB | đọc ảnh |

Đã cắm vào `llm_gateway/deploy/llama-swap.yaml` và `llm_gateway/catalog.py`; cấu
hình đã đối chiếu `config-schema.json` thật và test 26/26 vẫn xanh.

Mốc 200K **không bị vứt đi** — nó chỉ chuyển sang đúng chỗ dùng được: việc nội bộ
không đi qua Cloudflare.

---

## 4. Hạ tầng bán API: **phần lớn ĐÃ CÓ**, nhiều hơn tôi tưởng

`platform_core/public_api/` có **40 module** đã xây: `keys · limits · pricing ·
costing · quotes · usage · webhooks · idempotency · scopes · sandbox · budgets ·
principal · projects · request_log · security_log · error_registry`…

Ba thứ đọc được từ mã, quan trọng cho ta:

1. **Giá do app khai, không do bảng tra.** `costing.py`: *"Price is computed by the
   app… `registry.credit_for()` is the only thing that turns a call into a number"*
   — cấm động cơ tính giá thứ hai.
2. **Báo giá được KÝ** (`itsdangerous`), mang theo cả số credit lẫn nhãn phiên bản
   giá ⇒ không sửa giá hồi tố được, về mặt cấu trúc.
3. ⭐ **Đã lường trước token theo job**: *"A per-job token figure appears here only
   when a handler reports one in its result."* — chỗ cắm đã có sẵn.

Và llama-server trả `usage {prompt_tokens, completion_tokens, total_tokens}` cùng
`timings.cache_n`. Ghép hai đầu lại là đủ để tính tiền.

---

## 5. 🔴 Ngã ba phải chọn: chat nằm ở đâu trên `/api/v1`

Bề mặt công khai hiện có **24 route đóng băng**, và **chỉ một route tính tiền**:
`POST /api/v1/jobs` (`ASYNC_JOB`). Mọi route khác đọc hoặc sắp xếp.

Hình dạng đó là **báo giá → job → hỏi trạng thái → lấy artifact**. Đúng cho ảnh và
video. **Không đúng cho chat**, vì khách xây bot mong `POST /v1/chat/completions`
đồng bộ, có streaming, và trỏ SDK OpenAI vào là chạy.

| | **PA-A: chat là một "tool" trên `/jobs`** | **PA-B: bề mặt tương thích OpenAI** |
|---|---|---|
| Route mới | ❌ không | ✅ có — **phải nới bảng 24 route đóng băng** |
| SDK OpenAI cắm thẳng | ❌ **không** | ✅ **có** |
| Streaming | ❌ không | ✅ có |
| Governance/limit/webhook/usage | ✅ dùng nguyên | ✅ dùng lại được, phải nối tay |
| Cloudflare 100 s | ✅ né được (async) | ⚠️ phải xử theo §2 |
| Công phải làm | ít | nhiều hơn |

**Khuyến nghị: PA-B.** Vì PA-A **không đạt được mục tiêu đã nêu** — khách không
"cắm vào dùng như API của model khác" được nếu phải học hình dạng job của ta.

### 5b. Model phục vụ CẢ coding lẫn chat lẫn việc khác — điều đó đổi gì?

Chủ dự án làm rõ: đây không phải model chat, mà là model cho **coding, chat, và
các việc khác**. Điều đó **làm PA-B đúng hơn nữa**, vì một lý do dễ bị bỏ qua:

> `/v1/chat/completions` **không phải "hình dạng chat"**. Nó là **hình dạng chung
> của mọi việc LLM**: coding, agent, tóm tắt, phân loại, trích xuất, RAG, đọc ảnh.
> Tất cả đều là *text + tool + ảnh vào → text + tool-call ra*.

Hệ quả cụ thể:

| | PA-A (tool trên `/jobs`) | PA-B (tương thích OpenAI) |
|---|---|---|
| Thêm một loại việc mới | phải khai **một tool mới**, đổi contract, đổi inventory | **không phải làm gì** — khách tự đổi prompt/tool |
| Agent gọi vòng lặp tool | không có chỗ đặt | `tools` + `tool_calls` là **cơ chế sẵn có** |
| Khách dùng LangChain / n8n / Dify / SDK OpenAI | ❌ | ✅ chạy thẳng |

⇒ **Càng nhiều loại việc thì PA-A càng đắt và PA-B càng rẻ.** PA-A bắt ta khai một
tool cho mỗi tác vụ; PA-B khai **một lần** rồi khách tự dùng vào việc gì tuỳ họ.

**Đề xuất trình tự (không làm cả hai cùng lúc):**

1. **PA-B trước** — phủ gần hết nhu cầu, kể cả coding và agent.
2. **Đường job bất đồng bộ sau**, và **chỉ khi** có nhu cầu thật cho ngữ cảnh vượt
   trần Cloudflare. Hạ tầng job đã sẵn, thêm sau không phải làm lại.

### 5c. Một quyết định kỹ thuật mà "cả coding lẫn chat" chốt luôn giúp ta

Cộng đồng đo trên đúng 3090 hai đầu tăng tốc, và kết quả **rẽ theo loại việc**:

| Cách drafting | code (py) | prose | bash | tổng |
|---|---:|---:|---:|---:|
| tắt spec | 44,2 | 44,3 | 44,1 | 44,2 |
| **MTP dựng sẵn, n=2** | 86,5 | **63,1** | **76,0** | **76,0** ← 1,72× |
| DSpark n=5 | **97,5** | 47,4 | 67,3 | 67,3 |

Kết luận của họ, nguyên văn: *"Pick DSpark if your traffic is math or long
reasoning. **Keep the built in head for mixed or prose heavy traffic**, where it
wins and costs no VRAM."*

⇒ Vì lưu lượng của ta là **hỗn hợp** (coding **và** chat **và** việc khác), chọn
**MTP dựng sẵn, `n-max 2`** — đúng thứ đã cấu hình. DSpark còn tốn thêm **2 GB**
VRAM cho draft head, thứ ta không có để cho.

**Và một hệ quả vui:** MTP tăng mạnh nhất ở **code** (86,5 so với 44,2 = **+96 %**).
Phần lưu lượng coding của khách chính là phần được lợi nhiều nhất.

Nếu chọn PA-B thì phải theo đúng thủ tục H35, không được đi tắt:

- thêm route vào `server/api/inventory.py` (`test_178` so **hai chiều** với route
  thật **và** với OpenAPI — quên một bên là gate đỏ);
- cập nhật `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` (`test_212` đọc bảng đó
  **như dữ liệu**);
- ⚠️ `test_194` **từ chối mọi route `SYNC` chạm vào hàng đợi** — nên route chat
  đồng bộ **không được** đi qua `jobs`. Đây là ràng buộc tốt, nó ép ta tách đúng.

---

## 6. Tính tiền theo token — bốn câu cần chủ dự án chốt

Cơ chế đã có (`credit.giu_cho → quyet_toan → hoan`, khoá theo `job_id`). Mẫu chuẩn
cho LLM là **giữ chỗ theo trần rồi quyết toán theo thực tế**, và nền tảng đã có
đúng ba hàm đó.

Thiếu **chính sách**:

1. Một triệu token **vào** / **ra** = bao nhiêu credit?
2. Token prompt **lấy lại từ cache** (`timings.cache_n`) tính rẻ hơn bao nhiêu?
   *(Bot gọi lặp cùng system prompt — tính đủ giá là tính tiền hai lần cho cùng
   một thứ.)*
3. Token **reasoning** có tính tiền không? *(Template đã vá đặt mặc định `medium`;
   ở `xhigh` phần suy nghĩ có thể nhiều hơn câu trả lời.)*
4. Khách **ngắt kết nối giữa stream** thì tính tiền phần đã sinh, hay hoàn hết?

---

## 7. Trình tự đã sắp lại theo mục tiêu mới

**Đợt 1 — không cần GPU**

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Chủ dự án chốt **PA-A hay PA-B**, và **64K hay 200K** | 🔴 chặn mọi thứ sau |
| 2 | Chốt 4 câu chính sách giá (§6) | 🔴 chặn phần tính tiền |
| 3 | Nghiên cứu: mẫu tính tiền token cho cổng OpenAI-compatible · `stripParams` của llama-swap · `/metrics` + `/running` | |
| 4 | `platform_core/llm/cong_vlm.py` + test | mảnh còn thiếu lớn nhất |
| 5 | Provider `ltt_local_llm` | ⏸️ chờ phiên khác đóng `providers.py` |
| 6 | Nếu PA-B: route + inventory + OpenAPI + coverage doc + test | theo đúng thủ tục H35 |

**Đợt 2 — khi card trống:** P0-4 → P2 → P3 → P4 → **P5 (đo prefill THẬT ở 4K/16K/50K
để chốt trần Cloudflare)** → P6.

**Đợt 3:** mở khoá API cho một khách thử → sandbox → mở thật.

---

## 8. Một điều tôi đã làm sai và sửa ở đây

Tôi đã dựng cả kế hoạch quanh Codex và Claude Code mà **không hỏi lại xem chúng có
phải khách hàng thật không**. Chủ dự án nói mục tiêu là "cắm API vào codex để hỗ
trợ vận hành" ở phiên đầu, và tôi đã suy từ đó ra rằng chúng là **đích đến**, trong
khi thực ra chúng chỉ là **một cách dùng thử**.

Hậu quả cụ thể: mốc 200K được chọn để phục vụ phiên agent dài — một nhu cầu
**không có thật** trong sản phẩm. Và nó xung đột với Cloudflare 100 giây, thứ đáng
lẽ phải là ràng buộc số một ngay từ đầu vì nó nằm sẵn trong `CLAUDE.md`.

Cái **không** mất: `llm_gateway`, template đã vá, hai hồ sơ, trọng tài GPU, và toàn
bộ nghiên cứu cộng đồng — đều đúng nguyên với mục tiêu mới.
