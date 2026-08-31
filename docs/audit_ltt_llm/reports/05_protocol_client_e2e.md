# Prompt 05 — Protocol & Real Client End-to-End

**31/08/2026, 21:55–22:10.** Ownership: E01–E19.

---

## 1. Bề mặt được KHAI là hỗ trợ (E01–E04)

| Cửa | Hình dạng | Trạng thái |
|---|---|---|
| `POST /api/v1/jobs` (+ `/quotes`) | bất đồng bộ, có báo giá trước | **SUPPORTED** |
| `POST /api/v1/chat/completions` | OpenAI Chat, một JSON | **SUPPORTED** — `stream:true` bị **từ chối 400**, và lỗi chỉ sang hai cửa dưới |
| `POST /api/v1/messages` | Anthropic Messages, SSE | **SUPPORTED** — Claude Code nói giao thức này |
| `POST /api/v1/responses` | OpenAI Responses, SSE | **SUPPORTED** — Codex nói giao thức này |
| `GET /api/v1/models` | khám phá model | **SUPPORTED** |

⭐ Cửa đồng bộ **từ chối** `stream:true` thay vì im lặng bỏ qua, và thông điệp
400 **chỉ đường** sang hai cửa streaming. Đó là cách đúng: một tham số bị lờ đi
lặng lẽ là một hợp đồng nói dối.

---

## 2. Conformance — đo trên luồng THẬT (E05–E08)

### Anthropic `/v1/messages`

```
content-type: text/event-stream; charset=utf-8
message_start -> content_block_start -> content_block_delta x61
              -> content_block_stop -> message_delta -> message_stop
usage o su kien cuoi: {"output_tokens": 60}
```

Đúng thứ tự đặc tả Anthropic.

⚠️ Sự kiện **cuối** chỉ mang `output_tokens`; `input_tokens` nằm ở `message_start`
(đầu luồng). Đó là đặc tả Anthropic, không phải thiếu sót — và nó **giải thích
vì sao `DemToken` phải quét MỌI khối `usage` rồi giữ giá trị lớn nhất** thay vì
đọc khối cuối. Một bộ đếm chỉ đọc cuối luồng sẽ **mất `input_tokens`** trên cửa
này, tức tính thiếu tiền.

### OpenAI `/v1/responses`

```
content-type: text/event-stream; charset=utf-8
response.created -> response.in_progress -> response.output_item.added
  -> response.reasoning_text.delta x77 -> response.content_part.added
  -> response.output_text.delta x9 -> response.output_text.done
  -> response.content_part.done -> response.output_item.done
  -> response.completed
usage: {"input_tokens":23,"output_tokens":60,"total_tokens":83,
        "input_tokens_details":{"cached_tokens":19}}
```

Đầy đủ hơn cửa Anthropic: có cả vào lẫn ra **và** số token đã cache.

**Nhịp tim: 0** ở cả hai — đúng, vì phản hồi mất 2,3–2,6 s, dưới ngưỡng 15 s.

---

## 3. 🔴 Ngân sách nhỏ ⇒ khách nhận **KHÔNG MỘT CHỮ NÀO**, mà HTTP vẫn 200

Cùng một câu hỏi, chỉ khác `max_output_tokens`:

| ngân sách | reasoning delta | **text delta** |
|---:|---:|---:|
| 60 | 60 | **0** |
| 400 | 77 | 9 |

Model chạy `--reasoning-format deepseek` ⇒ nó **suy luận trước, trả lời sau**.
Với ngân sách hẹp, **toàn bộ** ngân sách bị tiêu vào phần suy luận và luồng kết
thúc bình thường mà **không có `output_text.delta` nào**.

⇒ Một client chỉ đọc `output_text.delta` sẽ hiển thị **ô trống**, không lỗi,
không cảnh báo. Với `max_tokens` mặc định của cửa đồng bộ (**1.024**) thì biên
còn rộng; nhưng client tự đặt `max_tokens=64` là chạm ngay.

⛔ **Và đây là chỗ tôi suýt báo cáo sai.** Lượt đo đầu (60 token) cho **100 %**
`reasoning_text.delta`, và tôi gần kết luận đó là một khuyết tật giao thức. Đo
lại với 400 thì `output_text.delta` có mặt. **Cái khác nhau là ngân sách, không
phải giao thức.**

**Quyết định: `DEFER`.** Đây là hành vi của model + hợp đồng giao thức, không
phải lỗi. Nhưng nó **phải được nói ra trong tài liệu cho khách** — hiện chưa có
chỗ nào nói.

---

## 4. Vòng tool đầy đủ (E06, E07) — **ĐẠT**

```
buoc 1  hoi "Con bao nhieu cai ma hang ABC-123 trong kho?"
        -> tool=tra_ton_kho  id=rpR0Lkx...  args={"ma_hang":"ABC-123"}
buoc 2  nap tool_result {"ma_hang":"ABC-123","ton":42} tro lai
        -> "Mat hang **ABC-123** hien co **42** cai trong kho."
        -> co so 42 trong cau tra loi: True
        usage: prompt 520 · completion 56 · cached 487
```

Bốn tính chất đều đúng: **chọn đúng tool** · **tham số là JSON hợp lệ và đúng
giá trị** · **`tool_call_id` khớp hai chiều** · **kết quả tool thật sự vào được
câu trả lời cuối** (số 42 không có trong câu hỏi).

⭐ **`cached_tokens: 487 / 520 = 94 %`** ở lượt thứ hai ⇒ **prefix cache đang
hoạt động**. Đó là lý do vòng tool nhiều bước không trả giá prefill lại từ đầu —
một con số chưa từng được đo trước hôm nay.

---

## 5. Còn nợ — và vì sao

| Mục | Trạng thái |
|---|---|
| E15–E17 canary client thật (Codex CLI · Claude Code · VS Code) | **PENDING** — cần một khoá API `/api/v1` của máy A. Tạo khoá là **cấp một credential thật**, không phải một thao tác audit |
| E10 huỷ / ngắt kết nối giữa luồng | **CHƯA** — cần client thật |
| E18 hành vi qua Cloudflare/WAF | **CHƯA** — mọi phép đo ở đây đi loopback trên máy B |
| E13/E14 công cụ tự ghi cấu hình (`cam_cli`) | **CHƯA** trong phase này |

⛔ Không đánh dấu `PASS`. Bốn cửa **conformance** đã chứng minh trên luồng thật,
nhưng *"client thật chạy được"* thì chưa — và đó chính là điều E15–E17 hỏi.

---

## Quyết định

| ID | Ứng viên | Quyết định | Vì sao |
|---|---|---|---|
| D-05-1 | Thứ tự sự kiện hai cửa SSE | **KEEP** | Đúng đặc tả cả hai, đo trên luồng thật |
| D-05-2 | `DemToken` quét **mọi** khối `usage` | **KEEP** | Cửa Anthropic đặt `input_tokens` ở **đầu** luồng; đọc khối cuối là tính thiếu tiền |
| D-05-3 | Cửa đồng bộ từ chối `stream:true` bằng 400 chỉ đường | **KEEP** | Lờ đi lặng lẽ là hợp đồng nói dối |
| D-05-4 | Ngân sách nhỏ ⇒ 0 text delta | **DEFER (tài liệu)** | Hành vi model, không phải lỗi — nhưng chưa ai nói cho khách |
| D-05-5 | Canary client thật | **BLOCKED** | Cần khoá API do chủ sản phẩm cấp |
