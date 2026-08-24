# Public API — nhật ký thay đổi

Ghi **thay đổi mà một tích hợp có thể cảm nhận được**, không phải mọi commit.
Ai muốn biết code đổi gì thì đọc git; trang này trả lời một câu khác: *"tôi có
phải sửa gì không, và khi nào?"*

Mỗi mục nói ba điều: **cái gì đổi**, **có phá vỡ tương thích không**, và **phải
làm gì**. Mục nào không trả lời được cả ba thì chưa đáng viết ra.

Bề mặt công khai được đóng băng trong `CONTRACT_BASELINE.json` và
`tools/check_api_compat.py` chạy trong gate. Một thay đổi phá vỡ tương thích
**không thể** lên tàu mà không có người ghi lại nó ở đây và chạy `--accept` —
lần ghi lại đó hiện ra trong diff.

## Phân loại

| Nhãn | Nghĩa |
|---|---|
| **BREAKING** | Tích hợp đang chạy sẽ hỏng. Chỉ được phép kèm phiên bản mới hoặc lịch ngừng hỗ trợ đã công bố. |
| **ADDED** | Thứ mới. Client không hỏi tới thì không thấy. |
| **DEPRECATED** | Vẫn chạy, đã có ngày kết thúc. Header `Deprecation` + `Sunset` (RFC 8594) xuất hiện trên phản hồi. |
| **FIXED** | Hành vi đã sai so với tài liệu, nay đúng. |

---

## v1 — chưa phát hành ra ngoài

Toàn bộ bề mặt `v1` được xây trong Public API V2 + Extension Pack và **chưa mở
cho khách bên ngoài**, nên không có mục BREAKING nào ở đây: chưa có tích hợp nào
để phá. Danh sách dưới đây là những gì `v1` **hứa** kể từ khi đóng băng.

### ADDED — 2026-08-24 · `image.ltt` mở cho khách, và giá **giảm một phần ba**

**Cái gì đổi.** Tool `image.ltt` (model ảnh chạy trên máy của chúng tôi) nay có
trong `LTT_PUBLIC_API_TOOLS` và gọi được. Cùng lúc, giá giảm:

| | Trước | Nay |
|---|---|---|
| Ảnh từ mô tả (`t2i`) | 5 credit | **3 credit** |
| Ảnh có ảnh tham chiếu (`edit`, `subject`) | 15 credit | **9 credit** |

Phiên bản bảng giá: `ltt-image-2026-08-24b`. Giá công bố ở `/gia-api`, và kết quả
job kèm `phien_ban_gia` để bạn đối chiếu đúng bảng đã sinh ra hoá đơn đó.

**Có phá vỡ tương thích không.** Không. Thêm một tool và **giảm** giá.

**Phải làm gì.** Không phải làm gì. Nhưng hai điều nên biết trước khi dùng:

1. **Bạn trả cho ảnh nhận được, không phải ảnh đã xin.** Xin `count: 4` mà chỉ
   sinh được 2 thì trả tiền 2 — phần chênh hoàn ngay khi job xong. Trước bản này
   trường hợp đó **thu trọn phần đã giữ**; đó là một lỗi, và nó đã được sửa.
2. **`subject` giữ được *ai/cái gì*, không dựng lại được *đang làm gì*.** Model
   chép cả tư thế của ảnh tham chiếu. Prompt kiểu *"người ở ảnh 1 đang bế con mèo
   ở ảnh 2"* sẽ ra đúng người và đúng con mèo, nhưng có thể giữ nguyên tư thế cũ.

⚠️ **Nó không phải model đẹp nhất chúng tôi có, và chúng tôi không nói thế.** Nó
là model **của nhà**: rẻ hơn, chạy trên phần cứng của chúng tôi. Ảnh cần **chữ
tiếng Việt có dấu** thì dùng `image.thumbnail` — `image.ltt` vẽ sai dấu, và đó là
giới hạn đã biết chứ không phải lỗi sẽ sửa.

---

### ADDED — 2026-08-23 · hai cửa streaming cho CLI viết mã

**Cái gì đổi.** Bề mặt có thêm **hai route** và chế độ thi hành thứ tư,
`STREAM` (Q107):

| Route | Giao thức | Client |
|---|---|---|
| `POST /api/v1/messages` | Anthropic Messages (SSE) | Claude Code CLI, Claude Desktop |
| `POST /api/v1/responses` | OpenAI Responses (SSE) | Codex CLI, tiện ích Codex VS Code |

`GET /api/v1/capabilities` nay liệt kê thêm hai khu vực `messages` và `responses`.

**Có phá vỡ tương thích không.** **Không.** Client không hỏi tới thì không thấy,
và cả hai vẫn đứng sau đúng ba cổng của Q92.

**Phải làm gì.** Trỏ công cụ của bạn vào — **hai địa chỉ khác nhau bốn ký tự**:

```
Codex          base_url = https://app.lttstudios.com/api/v1   (no ghep them /responses)
Claude Code    ANTHROPIC_BASE_URL = https://app.lttstudios.com/api   (no ghep them /v1/messages)
```

Cấu hình sẵn cho cả ba công cụ ở **`/developers/cli`**.

**Ba điều khác cửa `chat/completions`:**

1. **Bắt buộc `"stream": true`.** Muốn một cục JSON thì dùng
   `POST /api/v1/chat/completions`.
2. **Không đòi `Idempotency-Key`.** Đo thật: không CLI nào gửi nó — Codex không,
   Claude Code không, SDK OpenAI tự sinh rồi vứt đi. Đòi nó nghĩa là tính năng
   không tồn tại.
3. **Không có trần `max_tokens` theo thời gian.** Trần 4.095 của cửa đồng bộ
   sinh ra từ giới hạn 100 giây của Cloudflare, mà đồng hồ đó đếm thời gian chờ
   **byte đầu tiên** — luồng đang chảy thì không bị đếm.

⚠️ **Tính tiền khác, và bạn nên biết trước.** Không có khoá idempotency thì thứ
giữ tiền là **thu theo token đã thật sự sinh ra**: bỏ luồng giữa chừng thì trả
đúng phần đã sinh, và **thử lại là sinh mới, tức là trả thêm**. Đó là cách OpenAI
và Anthropic tính. Hàng rào còn lại là hạn mức chi tiêu ngày và trần ngân sách
của chính bạn.

---

### ADDED — 2026-08-23 · cửa đồng bộ `POST /api/v1/chat/completions`

**Cái gì đổi.** Bề mặt có thêm một route và một **chế độ thi hành thứ ba**,
`SYNC_BILLED` (Q106): trả lời ngay trong request, **có thu tiền**, **bắt buộc
`Idempotency-Key`**, **không có quote**, không đẩy vào hàng đợi, trần 90 giây.
`GET /api/v1/capabilities` nay liệt kê thêm khu vực `chat`.

**Có phá vỡ tương thích không.** **Không.** Client không hỏi tới thì không thấy.
Route đứng sau đúng ba cổng của Q92 như mọi thứ khác — `LTT_PUBLIC_API_TOOLS`
chưa có `text.chat` thì gọi vào vẫn bị từ chối.

**Phải làm gì.** Không ai phải làm gì. Ai muốn dùng thì trỏ `base_url` của SDK
OpenAI vào `/api/v1` và thêm header `Idempotency-Key` cho **từng lượt gọi** —
SDK của OpenAI **không tự gửi** nó. Chi tiết ở `DEVELOPER_GUIDE.md` §1b.

---

### FIXED — 2026-08-23 · `text.chat` khai `messages` là mảng, không phải object

**Cái gì đổi.** `contract_hash` của `text.chat` đổi từ `f6ff632ee8371fa9` sang
`32d617ca0c0130d2`. Trong lược đồ công khai, `messages` và `tools` đổi kiểu từ
`object` sang `array`, và `tool_calls` ở đầu ra cũng vậy.

**Có phá vỡ tương thích không.** Nhãn hình thức là BREAKING vì `contract_hash`
đổi, nhưng thực chất đây là **sửa một thứ chưa từng dùng được**. Cửa job của
`text.chat` **từ chối mọi input hợp lệ** kể từ lúc dựng — kể cả đúng ví dụ mà
trang tài liệu in ra:

    POST /api/v1/jobs  {"tool": "text.chat", "input": {"messages": [...]}}
    -> 400 invalid_request: messages must be an object.

**Vì sao.** Bảng kiểu của `ToolSpec` không có cách nào nói *"một mảng JSON"*:
chỉ có `json`, và `json` phơi ra công khai là `object`, rồi bộ kiểm đòi một
`dict`. `messages` là một **list**. Đã thêm kiểu `json[]` vào bảng, **không** nới
lỏng `object` cho nhận cả list — nới lỏng sẽ làm yếu bộ kiểm của **mọi** tool
khác để chiều một tool.

**Phải làm gì.** Không ai phải làm gì: `LTT_PUBLIC_API_TOOLS` trên production vẫn
rỗng, nên chưa từng có khách gọi được `text.chat`. Lỗi này lọt qua vì không có
test nào đối chiếu **ví dụ đã công bố** với **bộ kiểm thật**; nay `test_199` và
`test_256` làm đúng việc đó.

---

### BREAKING — 2026-08-23 · alias model `pro` của `image.generate` bị gỡ

**Cái gì đổi.** `image.generate` không còn nhận `model: "pro"`. Ba alias còn lại
(`standard`, `standard-lite`, `enhanced`) không đổi.

**Có phá vỡ tương thích không.** Về hình thức **có** — `contract_hash` của
`image.generate` đổi từ `f6fd70a8e5a91489` sang `d8d957479035c7c8`. Trên thực tế
**không có tích hợp nào hỏng**: `LTT_PUBLIC_API_TOOLS` trên production vẫn rỗng,
nên chưa từng có khách gọi được `image.generate`. Ghi nhãn BREAKING vì hình thức
mới là thứ bánh cóc đo được, và hạ nhãn cho vừa hoàn cảnh là cách một lần sau
người ta hạ nhãn cho một thứ **có** khách.

**Phải làm gì.** Không ai phải làm gì hôm nay. Khi mở `image.generate` cho khách,
tài liệu sẽ chỉ liệt kê ba alias.

**Vì sao gỡ — lý do kinh tế, không phải kỹ thuật.** Đo 23/08/2026: giá vốn
`gemini-3-pro-image` là **$0,134/ảnh = 35,2 credit**, trong khi nền tảng bán
**16 credit** ở `taoanh` và **5 credit** ở `thumbnail` (app đó tính giá phẳng bất
kể model). Lỗ **1.924đ** và **3.024đ** mỗi ảnh, và lỗ lớn dần theo doanh số.

Chủ dự án chốt: **giữ giá các bậc rẻ như chi phí thu hút khách, đóng đúng bậc lỗ
nặng nhất.** Ba bậc còn lại vẫn dưới giá vốn và điều đó nay được **khai tường
minh** trong `tests/test_261_khong_ban_duoi_gia_von.py`, kèm hạn rà lại 15/09.

Model bị đặt `is_active=False` trong `platform_core/providers.py` nên nó biến khỏi
**cả** bộ chọn model của giao diện web — đó mới là chỗ lỗ thật sự chạy, vì đường
API của `thumbnail` đã ẩn tham số `model` từ trước.

⭐ Mở lại được: ngày nào giá bán ≥ giá vốn thì bật lại `is_active`.
`tests/test_261` kiểm hộ điều kiện đó.

### ADDED — 2026-08-15 (EXT-17)

- `CONTRACT_BASELINE.json` + bước gate `hop dong API`. Từ nay mọi thay đổi hợp
  đồng phải đi qua đây.
- Payload webhook có `payload_version` (bắt đầu từ `1`) và danh sách trường được
  khai tường minh. Trong một phiên bản, trường có thể **thêm** nhưng không được
  bỏ hay đổi tên.
- Trang trạng thái công khai `/status/api`, nhóm theo **năng lực** chứ không
  theo hạ tầng.

### ADDED — 2026-08-15 (EXT-15)

- Báo giá và job mang `pricing_version`. Giá vẫn do công thức của app tính;
  nhãn ghi lại chế độ giá đang có hiệu lực để đối soát về sau.
- `GET /api/v1/quotes` trả thêm trường `pricing_version`.

### FIXED — 2026-08-15 (EXT-15)

- Job giữ **đúng** số credit đã báo giá. Trước đó khoản giữ được tính lại từ
  công thức app và **bỏ qua sàn/trần đã công bố**, nên khách có thể được báo một
  số rồi bị trừ một số khác.

### ADDED — 2026-08-14 (EXT-12)

- Chế độ **test**: khoá tiền tố `ltt_tk`, chạy hết chuỗi thật nhưng không gọi
  nhà cung cấp và **không chạm sổ credit**.
- Mọi job và mọi payload webhook mang trường `mode` (`live` | `test`).
- `GET /api/v1/me` trả thêm `mode`.

### ADDED — 2026-08-14 (EXT-09 … EXT-11)

- Nhật ký request cho khách, console webhook (gửi lại, xoay secret, test), ngân
  sách + cảnh báo.

### ADDED — 2026-08-13 (EXT-02 … EXT-08)

- Bảng mã lỗi ổn định kèm ngữ nghĩa thử lại; `execution_mode` công bố trên mọi
  operation; project cho khoá; catalog model/tool; playground.

---

## Cách một thay đổi phá vỡ tương thích được phép xảy ra

1. Đặt cho nó một **phiên bản mới** (`/api/v2`), **hoặc** công bố lịch ngừng hỗ
   trợ trên bề mặt cũ (`deprecated_on` + `sunset_on` trong
   `server/api/inventory.py` — hai header sẽ tự xuất hiện).
2. Viết một mục **BREAKING** ở đây, kèm việc khách phải làm.
3. Cập nhật `docs/PUBLIC_API/MIGRATION.md`.
4. Chạy `python tools/check_api_compat.py --accept`.

Bỏ bước nào cũng được — gate sẽ chặn ở bước 4, và đó là chủ ý.
