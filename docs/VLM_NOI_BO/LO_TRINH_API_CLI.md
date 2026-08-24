# Lộ trình: cắm CLI qua API công khai, bỏ đường LAN

**2026-08-23.** Chủ sản phẩm chốt: **một cửa duy nhất — `app.lttstudios.com/api/v1`.**
Tham chiếu cách `api.nghimmo.com` triển khai cùng bài toán.

---

## 0. "Bỏ đường LAN" nghĩa là gì — và KHÔNG nghĩa là gì

| | |
|---|---|
| ✅ **Bỏ** | Máy khách (Codex, Claude Code, Claude Desktop) trỏ thẳng vào `192.168.2.66:8299`. Bỏ luôn việc mở tường lửa máy B cho nhiều IP, bỏ việc phát bearer token của cổng cho từng máy. |
| ⛔ **KHÔNG bỏ** | **Cổng VLM `llm_gateway` trên máy B.** Nó là **động cơ**, không phải một lối đi thay thế. `dieu_phoi` của máy A gọi nó cho **mọi** lượt, kể cả lượt đến từ API công khai. Gỡ nó là gỡ chỗ chạy model. |

Sau khi đổi, đường đi **duy nhất** của một lượt gọi:

```
Codex / Claude Code / Claude Desktop
   |  https + khoa ltt_sk_...
   v
app.lttstudios.com/api/v1        <- xac thuc, han muc, giu credit, quyet toan
   |  LAN, bearer token cua cong
   v
192.168.2.66:8299 (cong VLM)     <- ngan sach, trong tai, don card, nhip tim
   |  loopback
   v
llama-swap -> llama-server (RTX 3090)
```

Tường lửa máy B **thu lại còn đúng một IP** (`192.168.2.17`), như hiện nay. Đó
vừa là dọn dẹp vừa là siết bảo mật: bearer token của cổng thôi không nằm trên
nhiều máy nữa.

---

## 1. `api.nghimmo.com` giải bài này thế nào

| | Họ làm | Ta học được gì |
|---|---|---|
| Địa chỉ | `https://api.nghimmo.com` cho Claude · `https://api.nghimmo.com/v1` cho Codex | **Hai base URL, một host.** Không phải hai dịch vụ |
| Khoá | một chuỗi `sk-…` dùng cho cả hai | ta đã có `ltt_sk_…` — không cần khoá thứ hai |
| `Idempotency-Key` | **không đòi** | 🔴 xem §3.1 — đây là chỗ hợp đồng của ta đang chặn chính ta |
| Tên model | `nghi/claude-sonnet-5`, `nghi/gpt-5.6-sol` | tiền tố nhà cung cấp + tên model. Có chữ `claude` nên lọt bộ lọc tự-dò của Claude Code |
| Cài đặt | phát **công cụ nhỏ** (`ClaudeKeyTool`, `CodexKeyTool`) tự ghi cấu hình | ⭐ ý hay nhất ở đây. Xoá sạch một lớp lỗi "sửa `config.toml` sai chỗ" |
| Hạn mức | dán khoá vào trang kiểm, xem còn bao nhiêu | ta đã có `/developers/usage` + `/api/v1/credits/balance` |

**Bốn điều rút ra:**

1. Không ai đòi `Idempotency-Key` cho inference. OpenAI và Anthropic cũng không.
2. Một host, hai base URL là **đủ** — không cần tên miền riêng.
3. Thứ khách vấp không phải giao thức, mà là **điền cấu hình**. Công cụ tự ghi
   cấu hình đáng giá hơn một trang tài liệu dài.
4. Họ **không** làm cửa đồng bộ không-streaming cho CLI. Cả hai CLI đều streaming.

---

## 2. Kiến trúc URL — và một may mắn ta không phải thiết kế

Hai CLI ghép đuôi đường dẫn theo hai kiểu khác nhau, và cách ta đã mount
`/api/v1` từ trước **khớp cả hai** mà không phải thêm host hay route ngoài rìa:

| Client | Khách khai | Client tự ghép | Rơi vào |
|---|---|---|---|
| **Codex** | `…/api/v1` | `+ /responses` | `POST /api/v1/responses` ✅ |
| **Claude Code CLI** | `…/api` | `+ /v1/messages` | `POST /api/v1/messages` ✅ |
| **Claude Desktop** | `…/api` | `+ /v1/messages` | `POST /api/v1/messages` ✅ |
| Claude Code (dò model) | `…/api` | `+ /v1/models` | `GET /api/v1/models` ✅ đã có |
| Claude Code (đếm token) | `…/api` | `+ /v1/messages/count_tokens` | 404 — client **tự lùi**, không hỏng |
| Claude Code (thăm dò) | `…/api` | `HEAD /api/hello` | ngoài mount ⇒ 404, tài liệu cho phép |

⇒ **Không cần tên miền mới, không cần reverse proxy thứ hai.** Chỉ cần thêm
**hai route** vào đúng sub-app đang có.

---

## 3. Ba quyết định phải chốt TRƯỚC khi viết dòng mã nào

### 3.1 🔴 `Idempotency-Key` — hợp đồng của ta đang chặn chính ta

`SYNC_BILLED` (Q106) **bắt buộc** header này vì nó không có quote. Nhưng đo thật
23/08: **không CLI nào gửi nó.** SDK OpenAI tự sinh rồi vứt đi; Codex và Claude
Code không gửi. Giữ nguyên hợp đồng = tính năng không tồn tại.

✅ **CHỐT 23/08 (Q107):** chế độ `STREAM` **không đòi** `Idempotency-Key`; khách
có gửi thì tôn trọng, không gửi thì vẫn chạy.

**Cái gì thay nó giữ tiền:** **thu theo token đã thật sự sinh ra.** Khách ngắt
giữa chừng ⇒ thu phần đã sinh. Thử lại ⇒ một lượt sinh mới ⇒ một khoản thu mới,
và khách **thật sự nhận** hai lượt sinh. Đó là cách OpenAI và Anthropic tính, và
là điều khách đã quen.

⚖️ Đánh đổi nói thẳng: một vòng thử lại hỏng ở phía khách sẽ tốn tiền của họ.
Hàng rào còn lại là hạn mức chi tiêu ngày (`limits.enforce_daily_credit`) và
trần ngân sách của chính khách — cả hai đã có.

### 3.2 Thu tiền khi luồng bị cắt giữa chừng

Ba tình huống, ba cách xử:

| | Xử |
|---|---|
| Khách đóng kết nối | thu **phần đã sinh**, đọc từ sự kiện `usage` cuối cùng |
| Máy B bận (429) trước khi sinh chữ nào | **hoàn đủ**, trả 503 + `Retry-After` |
| Không đọc được `usage` | **hoàn đủ, thu 0** — cùng luật `quyet_toan_hoac_hoan` |

⛔ Điều này buộc cổng phải **đếm token trong lúc luồng chạy**, không thể đợi tới
cuối. Đây là phần khó nhất về mã của cả lộ trình.

### 3.3 Tên model khách nhìn thấy

Hôm nay alias là `ltt_llm` → `qwen38-api`. Với CLI thì tên model đi thẳng vào
`ANTHROPIC_MODEL` / `model`, nên khách **phải gõ đúng**.

**Đề xuất giữ nguyên `ltt_llm`** — ngắn, đã có lớp đệm, đã có test chốt.

⛔ **Không** bắt chước `nghi/claude-…`. Tiền tố có chữ `claude` giúp lọt bộ lọc
tự-dò, nhưng model của ta **không phải Claude**, và dán nhãn đó lên hàng của
mình là tự tạo một câu hỏi khó trả lời về sau. Khai tay `ANTHROPIC_MODEL` là đủ,
và tài liệu đã ghi.

---

## 4. Vì sao streaming GỠ được trần 100 giây

`SYNC_BILLED` phải kẹp `max_tokens ≤ 4.095` vì Cloudflare cắt request ở 100 giây.
**Streaming không chịu trần đó**: đồng hồ 524 của Cloudflare đếm thời gian chờ
origin trả **byte đầu tiên**; byte bắt đầu chảy là hết đếm.

Ta đã có sẵn hai mảnh cần thiết:

- **nhịp tim SSE** (`llm_gateway/nhip_tim.py`) — chèn chú thích mỗi 15 giây khi
  luồng lặng, nên khoảng prefill không bao giờ im đủ lâu để bị cắt;
- **đo thật**: prompt 22k token ⇒ token đầu tiên sau **15,7 giây**.

⚠️ **Chưa đo qua Cloudflare thật.** Quy tắc 5b của dự án: loopback đẹp không
chứng minh gì. Đây là **việc đo bắt buộc ở Đợt 1**, không phải giả định mang
sang Đợt 3.

⇒ Nếu điều này đúng, `STREAM` là chế độ **hợp hơn** `SYNC_BILLED` cho việc agent,
và cửa đồng bộ ở Q106 lùi về vai trò "gọi ngắn, không streaming".

---

## 5. Lộ trình — sáu đợt

| Đợt | Mục tiêu | Việc | Chặn bởi | Ước |
|---|---|---|---|---:|
| **1** | Biết chắc nền móng chịu được | ~~C1~~ 🟡 trả lời từ hợp đồng · **C1b nhịp tim trước khi chạm thượng nguồn** · C2 không đệm SSE | — | 0,5 ngày |
| **2** ✅ | Hợp đồng | C3 **Q107**: mở `STREAM`, bỏ đòi `Idempotency-Key`, luật thu khi ngắt · C4 `protocol.py` + `check_mode_rules` + `test_194` | chủ sản phẩm | 1,0 ngày |
| **3** ✅ | Đường ống streaming | C5 đếm token **trong lúc** luồng chảy · C6 giữ chỗ → chuyển tiếp SSE → quyết toán từ sự kiện `usage` cuối · C7 huỷ-khi-ngắt | Đợt 2 | 2,0 ngày |
| **4** ✅ | Hai route | C8 `POST /api/v1/messages` (Anthropic) · C9 `POST /api/v1/responses` (Codex) · C10 inventory + OpenAPI + SDK + Postman | Đợt 3 | 2,0 ngày |
| **5** ✅ | Mở cửa | C11 bật `LTT_PUBLIC_API_TOOLS=text.chat` · C12 kiểm **qua Cloudflare thật** bằng cả ba client · C13 xoay khoá provider | Đợt 4 | 1,0 ngày |
| **6** ◐ | Để khách tự cắm được | C14 trang "Cắm vào CLI" trong cổng dev, sinh sẵn cấu hình kèm khoá · C15 công cụ nhỏ tự ghi `config.toml` / `settings.json` · C16 thu tường lửa máy B về một IP | Đợt 5 | 1,5 ngày |

**Tổng ≈ 8 ngày công.**

### Vì sao thứ tự này

**Đợt 1 trước tất cả** vì nó có thể **giết cả lộ trình**. Nếu Cloudflare không
giữ được luồng dài, toàn bộ thiết kế phải đổi — và biết điều đó ở ngày 1 rẻ hơn
biết ở ngày 6. Nửa ngày này mua về quyền không phải làm lại bảy ngày.

**Đợt 2 trước Đợt 3** vì `check_mode_rules` sẽ **chặn thẳng** một route khai
`STREAM` khi `MODES_IN_USE` chưa có nó. Viết mã trước rồi mới sửa hợp đồng là
đúng cái bẫy Q106 đã dạy: chốt đó đang làm đúng việc, đừng lách.

**C5 tách khỏi C6** vì đếm token giữa luồng là phần dễ sai nhất và phải **đo
được riêng**. Trộn nó vào route là làm cho một lỗi tiền chỉ lộ ra khi chạy thật.

**Đợt 6 sau cùng** nhưng **không phải phần thưởng**: bài học từ nghimmo là thứ
khách vấp không phải giao thức mà là điền cấu hình. Không có C14/C15 thì mọi
việc trên chỉ dùng được bởi người đã đọc hết tài liệu này.

---

## 6. Bảng việc chi tiết

### Đợt 1 — đo nền móng

| # | Việc | Đạt khi |
|---|---|---|
| ~~**C1**~~ | ~~Đo Cloudflare giữ luồng SSE~~ | 🟡 **TRẢ LỜI TỪ HỢP ĐỒNG 23/08, chưa đo sống** — xem dưới |
| **C1b** | ⚠️ **ĐÃ SỬA LẠI 23/08 — xem dưới.** Mở thượng nguồn TRƯỚC, với ngân sách 75 giây, để giữ được mã trạng thái đúng | thượng nguồn chậm quá 75s ⇒ **503 sạch của ta**, không phải 524 mù của Cloudflare |

#### C1b — tôi đã đề xuất ngược, và số đo lật lại

Bản đầu tôi viết: *"phát nhịp tim trước khi chạm thượng nguồn"*. Nghe hợp lý,
nhưng nó **đánh đổi mất một thứ đắt hơn**: gửi header SSE đi rồi thì trạng thái
HTTP đã chốt ở `200`, và ta **không còn cách nào** trả `503` khi máy B bận hay
`502` khi nó hỏng. Mà Claude Code và Codex **cư xử khác nhau theo mã trạng thái**
— 5xx thì thử lại, 4xx thì dừng. Bịt mất kênh đó là bịt mất cách duy nhất nói
cho client biết chuyện gì đang xảy ra.

Số đo lật lại cán cân: **nạp lại model đo được ~25 giây** (nghiệm thu 23/08:
`chat -> 200 sau 14.6s` đã gồm cả nạp). 25 giây nằm **gọn** trong trần 100 giây
của Cloudflare, nên khoảng chết đó không thật sự nguy hiểm ở đường thường.

⇒ **Mở thượng nguồn trước, có đồng hồ 75 giây.** Chậm hơn thế thì ta **tự** trả
`503` — một cái 503 sạch của ta tốt hơn một cái 524 mù của Cloudflare, vì client
đọc được nó.

⭐ **Và không cần lớp nhịp tim thứ hai.** Cổng VLM đã chèn nhịp mỗi 15 giây
(`llm_gateway/nhip_tim.py`), nên từ lúc thượng nguồn trả header trở đi, byte về
tới Cloudflare đều đặn. Chồng thêm một lớp nữa chỉ thêm nhiễu.

⚠️ **Rủi ro còn lại, nói thẳng:** nạp model từ **đĩa lạnh** có thể lâu hơn 75
giây. Giảm nhẹ bằng `ttl: 1800` của `llama-swap` (model ở lại 30 phút) chứ không
bằng cách nới đồng hồ — nới nó chỉ đổi 503 của ta lấy 524 của Cloudflare.
| **C2** | Kiểm `/api/v1` không đệm SSE | byte tới client **ngay**, không dồn cục cuối |

#### C1 — cái gì đã biết chắc, cái gì chưa

Tài liệu Cloudflare chốt: **100 giây là đồng hồ chờ BYTE ĐẦU TIÊN**, không phải
tổng thời gian. *"If the origin can start the response quickly and stream it
safely, send chunks often enough that Cloudflare doesn't sit idle."* Nhịp tim 15
giây của ta nằm gọn trong mọi ngưỡng nhàn rỗi hợp lý.

⚠️ **Nhưng nhịp tim hiện tại KHÔNG che hết khoảng nguy hiểm.** `upstream.stream()`
gọi `ctx.__enter__()`, và lời gọi đó **chặn cho tới khi thượng nguồn trả header**.
`llama-server` trả header SSE ngay — nhưng nếu `llama-swap` phải **nạp lại model**
trước, cả khoảng đó **không có byte nào rời máy chủ**:

```
khach --> /api/v1/messages
             |
             |  <-- KHOANG CHET: llama-swap nap GGUF, do duoc toi 25 giay,
             |      va co the lau hon khi dia lanh. KHONG BYTE NAO RA.
             |      Nhip tim chua chay vi no boc luong CUA thuong nguon.
             v
          header SSE  --> tu day tro di nhip tim moi che duoc
```

⇒ **C1b:** route công khai phải mở `StreamingResponse` **ngay khi nhận request**,
phát nhịp đầu, **rồi mới** gọi thượng nguồn bên trong generator. Đảo thứ tự này
là đổi một cái 524 mù lấy một luồng khoẻ.

🟡 **Còn nợ phép đo sống.** Hôm nay không đo qua Cloudflare thật được: `/api/v1`
chưa có route streaming nào, và `text.chat` chưa mở trên bản chạy thật nên không
mượn được cửa nào sẵn có. Dựng một route thử **chỉ để đo** thì phải deploy vào
bản chạy thật rồi gỡ ra — đắt hơn giá trị nó mang lại.

⇒ Phép đo sống **gộp vào lần deploy của Đợt 4**, và là **chốt nghiệm thu đầu
tiên** ở đó: một luồng 5 phút qua `https://app.lttstudios.com`, không 524.

⚠️ C2 dễ bị bỏ qua và rất đắt nếu sai: một tầng trung gian đệm cả phản hồi sẽ làm
mọi thứ **vẫn chạy** nhưng client treo cho tới khi xong — đúng cái Claude Code
gọi là *"a gateway that buffers complete responses before relaying them stalls
the client"*.

### Đợt 2 — hợp đồng

| # | Việc | Đạt khi |
|---|---|---|
| **C3** ✅ | Q107 đã chốt 23/08, đã ghi vào `QUYET_DINH_NEN_TANG.md` | ghi rõ **vì sao** bỏ đòi khoá, không chỉ ghi là bỏ |
| **C4** | `STREAM` vào `MODES_IN_USE`; `check_mode_rules` đòi đủ: kiểu sự kiện khai sẵn, nhịp tim, sự kiện `usage` cuối mang credit **thật**, huỷ-khi-ngắt | `test_194` xanh, và có test **chặn** một khai báo `STREAM` thiếu các thứ đó |

### Đợt 3 — đường ống

| # | Việc | Đạt khi |
|---|---|---|
| **C5** | Bộ đếm token đọc lướt luồng SSE, lấy `usage` từ `message_delta` (Anthropic) và `response.completed` (Responses) | test: luồng cắt giữa chừng vẫn ra đúng số token đã sinh |
| **C6** | Giữ chỗ trần → chuyển tiếp → quyết toán từ số đã đếm | test: sinh ít trả ít; bận thì hoàn đủ; không đo được thì thu 0 |
| **C7** | Khách ngắt ⇒ đóng luồng thượng nguồn ⇒ quyết toán phần đã sinh | test: `close()` giữa chừng vẫn có đúng một lần quyết toán |

⛔ C6 phải **chốt giao dịch trước khi gọi model**, đúng bài học đã học ở
`server/api/chat.py`: giữ giao dịch mở suốt lượt gọi làm khoá idempotency treo,
giữ kết nối CSDL, và mất cả phần giữ chỗ nếu tiến trình chết.

### Đợt 4 — route

| # | Việc | Đạt khi |
|---|---|---|
| **C8** | `POST /api/v1/messages` | Claude Code CLI chạy trọn **một việc thật có gọi tool** |
| **C9** | `POST /api/v1/responses` | Codex chạy trọn **một việc thật có gọi tool** |
| **C10** | inventory + OpenAPI + hai SDK + Postman | `gate.py` xanh |

### Đợt 5 — mở cửa

| # | Việc | Đạt khi |
|---|---|---|
| **C11** | `LTT_PUBLIC_API_TOOLS=text.chat` trên bản chạy thật | `GET /api/v1/tools` liệt kê nó |
| **C12** | Ba client, qua Cloudflare thật, mỗi client một việc thật | Codex · Claude Code CLI · Claude Desktop |
| **C13** | Xoay bearer token của cổng VLM | token cũ hết hiệu lực |

### Đợt 6 — để khách tự cắm

| # | Việc | Đạt khi |
|---|---|---|
| **C14** | Trang `/developers/cli` sinh sẵn ba khối cấu hình **kèm khoá của chính họ** | copy–dán là chạy |
| **C15** | Công cụ nhỏ tự ghi `~/.codex/config.toml`, `~/.claude/settings.json` | không cần mở editor |
| **C16** | Thu tường lửa máy B về một IP | `Set-NetFirewallRule ... -RemoteAddress 192.168.2.17` |

---

## 7. Rủi ro, và cách phát hiện sớm

| Rủi ro | Sớm nhất phát hiện được ở | Nếu xảy ra |
|---|---|---|
| Cloudflare cắt luồng dài | **C1** | đổi sang cửa job + webhook; lộ trình đổi hẳn |
| Có tầng đệm SSE | **C2** | tìm và tắt đệm; nếu không được thì như trên |
| Đếm token giữa luồng sai | **C5** | đây là **lỗi tiền**; test phải quét cả ca cắt giữa chừng |
| Trần 2 lượt đồng thời quá chật cho subagent | **C12** | V7 (đo `--parallel`) trở thành việc chặn |
| Codex/Claude Code đổi giao thức | bất cứ lúc nào | ghim phiên bản đã kiểm vào tài liệu; đo lại mỗi bản mới |

---

## 8. Cái gì KHÔNG làm, và vì sao

| Không làm | Vì sao |
|---|---|
| Tên miền riêng `api.lttstudios.com` | `app.lttstudios.com/api` đã đủ cho cả hai kiểu ghép đuôi (§2). Thêm host là thêm chứng chỉ, thêm tunnel, thêm một chỗ hỏng |
| Đặt tên model có chữ `claude` | Model của ta không phải Claude. Lọt bộ lọc tự-dò không đáng đổi bằng một nhãn sai |
| `anthropic_family_tier` trong `/v1/models` | cùng lý do |
| Cửa đồng bộ **không** streaming cho CLI | không CLI nào dùng. `SYNC_BILLED` ở Q106 vẫn giữ cho khách gọi SDK thường |
| Bỏ cổng VLM máy B | nó là **động cơ**, không phải một lối đi (§0) |
| Cho khách chọn `qwen38-api` (id nội bộ) | phá lớp đệm alias mà `test_212` chốt |


---

## 9. Thi hành 23/08 — Đợt 2, 3, 4 xong; Đợt 6 xong phần không cần GPU

### Đợt 2 — hợp đồng

`STREAM` vào `MODES_IN_USE`, và **bốn lời hứa của nó nay phải được KHAI**
(`STREAM_PHAI_KHAI`): kiểu sự kiện · nhịp tim · sự kiện mang credit thật ·
huỷ-khi-ngắt. `check_mode_rules` từ chối một khai báo thiếu bất kỳ cái nào, từ
chối `requires_quote`, và từ chối một luồng có thu tiền mà **không** khai
`settles_from_measured_usage`.

⭐ Và nó **chạy trên đường thật**: `server/api/streaming.py` dựng
`PublicOperationContract` ở **cấp module**, nên bỏ mất một lời hứa là **app không
khởi động được**. Trước hôm nay hợp đồng đó chỉ được dựng trong test — có bộ kiểm
mà bộ kiểm không bao giờ chạy lúc phục vụ.

### Đợt 3 — đếm token giữa luồng

`platform_core/llm/dem_token_luong.py`. Ba quyết định đáng ghi:

| | |
|---|---|
| **Đệm cho tới khi trọn dòng** | `iter_raw()` trả byte theo nhịp **mạng**, không theo nhịp dòng. Phân tích từng khối rời rạc là hỏng ngẫu nhiên theo tải — lỗi chỉ hiện ra ở production, dưới dạng hoá đơn sai |
| **Quét cây JSON, không ghim đường dẫn** | Anthropic để `usage` ở hai chỗ khác nhau giữa `message_start` và `message_delta`; Responses để trong `response`. Ghim đường dẫn nghĩa là mỗi lần một giao thức đổi chỗ là một lần thu sai **mà không ai biết** |
| **Lấy LỚN NHẤT, không lấy cái cuối** | `message_start` mang `output_tokens: 0`. Lấy cái cuối chỉ đúng khi luồng chạy tới cuối; một luồng bị cắt có thể để lại số 0 đó, và ta thu 0 cho một lượt đã sinh vài trăm token |

### Đợt 4 — hai route

`server/api/streaming.py`. Chỗ khó nhất **không** phải giao thức mà là **vòng đời
giao dịch**: generator chạy **sau khi** phản hồi đã bắt đầu, lúc đó phiên CSDL của
request đã đóng. Nên phần giữ chỗ phải `commit` trước khi chạm model, và quyết
toán phải mở **một phiên mới** trong `finally`.

⛔ `finally` chứ không phải "sau vòng lặp": khách đóng kết nối thì Starlette ném
`GeneratorExit` vào ngay chỗ `yield`, và nhánh sau vòng lặp **không bao giờ
chạy** — nghĩa là một lượt đã đốt GPU sẽ không bao giờ được quyết toán, và phần
giữ chỗ nằm lại trên tài khoản khách mãi.

### Đợt 6 — phần không cần GPU

Trang **`/developers/cli`** sinh sẵn cấu hình cho cả ba công cụ, kèm bảng "hai
địa chỉ lệch nhau bốn ký tự" và bảy chỗ hay vấp. ⛔ Nó **không** chèn khoá thật:
khoá chỉ hiện một lần lúc tạo, cùng luật mọi ví dụ khác đã theo.

Còn lại của Đợt 6: **C15** (công cụ tự ghi cấu hình) và **C16** (thu tường lửa
máy B về một IP) — cả hai làm sau khi Đợt 5 xác nhận đường công khai chạy.

### Kiểm chứng

| | |
|---|---|
| `test_269`–`test_272` + bộ H38 + hợp đồng nhân | **739 xanh** |
| `tools\gate.py --quick` | **13/13 PASS** |
| Hợp đồng API | 2 route **cộng thêm**, không phá vỡ tương thích |

⚠️ Đổi số file test **hai lần** vì phiên khác chiếm trước. Gate nay có chốt
`trung so test` bắt việc này — dùng số **≥ 269** cho phiên sau.


---

## 10. Đợt 5 — đo được nửa đầu, nửa sau vấp một chốt vận hành

### ✅ Đường ống chạy thật, đo trên bản dev nối tới máy B

Trước khi deploy mã chưa từng chạy thật vào bản production, tôi dựng một bản dev
riêng (cổng 8137, CSDL tạm, khoá `ltt_llm` trỏ tới máy B) và gọi thật:

```
POST /api/v1/messages   ->  200  text/event-stream
     98 x content_block_delta · message_start · message_delta · message_stop
     token dau tien 17,7s (co nap model) · tong 24,9s
```

**Tiền khớp chính xác:**

```
quyet toan job stream:...  giu 2, thu 1
```

Kiểm lại số bằng tay: luồng mang `input_tokens: 21`, `output_tokens: 139`.
139 × 400 credit/1M = 0,056 ⇒ làm tròn lên **1** (luật C1, tối thiểu 1 credit).
Giữ chỗ theo `max_tokens=4000`: 4000 × 400/1M = 1,6 ⇒ **2**. Giữ 2, thu 1. Đúng.

⭐ **Đây là bằng chứng cho toàn bộ Đợt 3**: bộ đếm token đọc được `usage` từ luồng
thật của `llama-server`, và `quyet_toan_hoac_hoan` thu theo số đó chứ không theo trần.

Một lỗi nhỏ dọc đường, đáng ghi vì nó câm: bản dev đặt pepper vào
`LTT_DEV_API_KEY_PEPPER` trong khi hằng của module là `LTT_API_KEY_PEPPER`. Mọi
lời gọi API trả `401` mà không nói vì sao. ⇒ **Dùng hằng của module, đừng gõ tay
tên biến môi trường.**

### 🔴 Nửa sau chặn ở một chốt vận hành, không phải ở mã

Deploy **chép cả cây nguồn** rồi chạy `alembic upgrade head`. Lúc này trong repo
còn **việc đang dở của một phiên khác** (app `vps`), kèm **ba migration chưa
commit**:

| Migration | Làm gì |
|---|---|
| `20260822_1900_vps_tables` | tạo 5 bảng `vps_*`, 11 index |
| `20260823_1000_vps_gateway_mang` | thêm 3 cột |
| `20260823_1800_vps_dnat_da_nap` | thêm 1 cột |

Đã soi: phần `upgrade()` của cả ba **không có lệnh phá huỷ nào** — chỉ
`create_table`, `create_index`, `add_column`. Các lệnh `drop_*` chỉ nằm trong
`downgrade()`, đúng như mọi migration.

Nhưng **rủi ro không nằm ở tính phá huỷ**, nó nằm ở chỗ: deploy sẽ đẩy việc đang
dở của phiên khác lên bản chạy thật, và **tôi không kiểm chứng được việc đó**.
Đây đúng là điều bộ nhớ dự án đã ghi: *"Deploy chép cả cây + alembic head — không
tách được phần của một phiên."*

⇒ **Không tự deploy.** Ba đường ra, chủ sản phẩm chọn:

| | |
|---|---|
| **A** | Chờ phiên VPS chốt xong, rồi deploy **một lần** cho cả hai |
| **B** | Deploy ngay, chấp nhận đẩy cả việc VPS (migration additive, app `vps` gác sau cờ `LTT_VPS` mặc định tắt) |
| **C** | Tách nhánh: đưa việc H38 sang một cây riêng rồi deploy từ đó — sạch nhất, tốn thêm thời gian |

### Còn nợ sau khi deploy

1. 🟡 **Phép đo C1** — luồng 5 phút qua `https://app.lttstudios.com` thật, không 524.
2. Bật `LTT_PUBLIC_API_TOOLS=text.chat`.
3. Ba client thật: Codex CLI · Codex VS Code · Claude Desktop.
4. Xoay bearer token cổng VLM.
5. **C15** (công cụ tự ghi cấu hình) · **C16** (thu tường lửa máy B về một IP).


---

## 11. Đợt 5 — XONG 24/08. C1 đã trả nợ, và câu trả lời là "được"

### 🟢 Phép đo C1, thứ có thể đã lật cả lộ trình

```
POST https://app.lttstudios.com/api/v1/messages     (qua Cloudflare that)
  HTTP 200 OK
  token dau tien   1,8 giay
  luong song       119,4 giay        <-- VUOT moc 100 giay
  15.932 su kien content_block_delta
  ket thuc sach bang message_stop
  KHONG co 524
```

**Kết luận:** đồng hồ 100 giây của Cloudflare đúng là chỉ đếm **byte đầu tiên**.
Luồng đang chảy không bị cắt. Toàn bộ thiết kế `STREAM` đứng vững, và trần
`max_tokens` mà `SYNC_BILLED` phải chịu **không áp cho cửa này**.

⭐ **0 nhịp tim trong lượt đo**, và đó là **đúng**: model sinh chữ liên tục nên
không có khoảng lặng 15 giây nào. Nhịp tim là bảo hiểm cho lúc *có* khoảng lặng
(nạp model, prefill dài), không phải thứ chạy thường trực.

### 🔴 Và một lỗi tiền chỉ hiện ra ở production

Lượt gọi thật **đầu tiên** trả `500`:

```
psycopg.errors.StringDataRightTruncation: value too long for character varying(36)
job_id = 'stream:' + 32 hex  ->  39 ky tu
```

`credit_entries.job_id` là `VARCHAR(36)`. **SQLite không ép độ dài, PostgreSQL
thì có.** Bộ test chạy SQLite, bản thật chạy PostgreSQL — nên lỗi này đi qua
**739 test xanh, gate 13/13, và cả một lần deploy** rồi mới nổ.

Và **cả hai** cửa thu tiền đều dính: `chat/completions` dùng `chat:{uuid}` = 41
ký tự, còn dài hơn.

**Sửa:** `thanh_toan.ma_luot()` dùng chung, lấy trần **từ chính cột**
(`CreditEntry.__table__.c.job_id.type.length`) chứ không gõ `36` — ngày ai nới
cột, hàm đi theo. `test_273` kéo ràng buộc đó về chỗ đo được, kèm chốt chống tái
phát quét mã nguồn cấm tự ghép `request_id`.

⇒ **Bài học, và nó lớn hơn lỗi này: một ràng buộc chỉ tồn tại ở production là
một ràng buộc chưa được test.** SQLite trong test không phải bản sao của
PostgreSQL; nó chỉ giống ở những chỗ ta tình cờ chưa chạm tới.

### Tiền, đối chiếu bằng tay

| | |
|---|---|
| Số dư trước | 3.042 credit |
| Số dư sau | 3.037 credit |
| Lượt dài (chạm trần 8.000 token ra) | 8000 × 400/1M = 3,2 ⇒ **4** |
| Lượt ngắn (61 delta) | ⇒ **1** |
| Tổng | **5** ✓ khớp |

### Cả ba client, qua địa chỉ công khai

| Client | Kết quả |
|---|---|
| `POST /api/v1/messages` bằng curl | ✅ 200, SSE đúng chuẩn Anthropic |
| **Codex CLI** | ✅ `codex --profile ltt` trả đúng mã, 31 giây, 14.737 token |
| Claude Code CLI / Desktop | ⏳ chưa chạy phiên thật — máy này không có CLI, Desktop cần bạn |

Cấu hình Codex đã chuyển từ LAN sang `https://app.lttstudios.com/api/v1`, khoá
đọc từ `LTT_API_KEY`. Đúng hướng Q107: **một cửa duy nhất**.

⚠️ Codex vẫn cảnh báo *"Model metadata for `ltt_llm` not found"* — không chặn,
nhưng nghĩa là các con số nó tự suy (nén ngữ cảnh, ước chi phí) không chính xác.

### Tôi tự deploy được — cơ chế đã có sẵn, tôi tìm chưa ra

Chủ sản phẩm chỉ ra là hệ thống đã dựng đường cho việc này, và đúng: `AGENTS.md`
§9.3 ghi sẵn công thức hai lớp. Đã đóng gói thành
`setup/deploy_nang_quyen.ps1` — tôi khởi động, chủ sản phẩm bấm **một** hộp UAC,
và tôi đọc được `EXITCODE` thật từ file thay vì đoán.

```
BAT DAU=2026-08-24 01:17:05   ADMIN=True   EXITCODE=0   KET THUC=01:17:52
```

⛔ `EXITCODE` **rỗng** khác hẳn `EXITCODE=0` — rỗng nghĩa là tiến trình không
chạy. Không phân biệt được hai thứ đó thì sẽ báo "đã deploy xong" trong khi chưa
có gì xảy ra.

### Còn lại

| | |
|---|---|
| Claude Code CLI + Claude Desktop, phiên thật | cần bạn — máy này không có hai công cụ đó |
| Xoay bearer token cổng VLM (C13) | chưa |
| **C15** công cụ tự ghi cấu hình · **C16** thu tường lửa máy B về một IP | chưa |
