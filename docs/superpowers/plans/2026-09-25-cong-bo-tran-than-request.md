# Công bố trần thân request — kế hoạch

> **Bài toán:** client không có cách biết trần byte của máy chủ, nên phải **đâm vào tường mới
> biết tường ở đâu**. Sáng 25/09 điều đó làm một khách kẹt cứng.

**Nguồn nghiên cứu:** RFC 9457 · RFC 9110 §15.5.14 · draft `ietf-wg-httpapi/ratelimit-headers` ·
`deepseek-harness` (`http-bridge.ts`, `assertImageBodyCapacity`) · MCP `schema/2025-11-25`.

---
## Đây KHÔNG phải năm đầu việc

Danh sách "5 mục" là ánh xạ **giải pháp ↔ ràng buộc**, không phải khối lượng. Đếm lại:

| Mục | Thực chất | Trạng thái |
|---|---|---|
| Kẹp `≤ 100 MB` (Cloudflare) | `config.py` **đã** tự kẹp | ✅ **xong từ trước** |
| Bất biến trần ≥ cửa sổ | `test_4200` | ✅ **xong 25/09** |
| Khách API trực tiếp | **hệ quả** của việc dùng HTTP thường, không phải việc riêng | — |
| **Header trên mọi phản hồi** | cơ chế chính | 🔨 **việc 1** |
| **Client đọc header** | | 🔨 **việc 2** |
| **413 không phân tích được** | lỗ hổng phát hiện thêm | 🔨 **việc 3** |
| Trường ở gốc `GET /models` | tiện nghi | 🟡 tuỳ chọn |

⇒ **Ba đầu việc thật**, cộng một tuỳ chọn. Hai mục đã xong.

---
## Vì sao HEADER, không phải một trường đọc-một-lần

Ràng buộc khó nhất không phải *"client không biết trần"* mà là ***"client biết một trần đã cũ"***.
Sáng nay trần đổi 1 MiB → 4 MiB; mọi client cache con số cũ đều sai từ giây đó.

**Tiền lệ IETF gần nhất** — draft `ratelimit-headers` — công bố hạn mức **trên MỌI phản hồi** đúng
vì lý do này. Không có draft tương đương cho **kích thước thân**; đó là khoảng trống thật, đã tra.

⭐ **Và kho này đã học đúng bài học đó rồi**, ở `server/api/guard.py::_stamp`: correlation-id từng
chỉ đóng lên phản hồi **lỗi**, và docstring ghi *"khách có request thành công rồi hỏng bí ẩn thì
không có gì để trích dẫn"*. Cùng một hình dạng. Hook đã sẵn.

---
## Việc 1 — header trên mọi phản hồi `/api/v1/*` (nền tảng)

**Files:** `platform_core/public_api/protocol.py` (hằng tên header) · `server/api/guard.py::_stamp`

- [ ] Thêm hằng tên header vào `protocol.py`, **cạnh** `HEADER_CORRELATION_ID`/`HEADER_API_VERSION`.
      ⛔ Đừng gõ chuỗi thẳng vào `guard.py` — cả bốn header hiện có đều đi qua hằng số.
      ⚠️ **Không dùng tiền tố `X-`** (RFC 6648 đã bỏ).
- [ ] Đóng dấu trong `_stamp`, tức **mọi** phản hồi kể cả `2xx` — đó là toàn bộ điểm của việc này.
- [ ] Phép kiểm: header có mặt trên **phản hồi thành công**, không chỉ trên 413. Đối chứng âm:
      **đổi `max_body_bytes` trong cấu hình ⇒ header đổi theo**, không phải một hằng số thứ hai.

⚠️ **Giá phải trả, nêu rõ:** thêm ~40 byte cho **mọi** phản hồi API. Nhỏ, nhưng là thật.

---
## Việc 2 — client đọc header (LTTCODE)

**Files:** `plugins/llm-ltt/src/adapter.ts`

- [ ] Đọc header ở **mọi** phản hồi; cập nhật trần đã biết.
- [ ] **Thứ tự ưu tiên:** header (mới nhất) > trần học từ 413 > hằng dự phòng.
      ⛔ Đừng bỏ đường học-từ-413 — xem Việc 3.

⭐ **Đây là chỗ trả tiền:** sau việc này, *"một 413 mỗi lần mở app"* **gần như biến mất** — client
biết trần từ **lượt trao đổi đầu tiên**.

### ⛔ ĐÍNH CHÍNH (25/09, làn nghiệm thu bắt được)

Bản đầu của mục này — và ghi chú phát hành 0.2.16 tôi viết theo nó — nói *"biết trần ngay từ
**phản hồi** đầu tiên"*. **Hứa nhiều hơn thứ bản vá làm được.**

Mã thật chỉ đọc header từ phản hồi **`/api/v1/messages`**, **không** đọc từ lượt gọi catalog lúc
khởi động. ⇒ Lượt **đầu tiên của một tiến trình mới** mà đã vượt trần thì **vẫn ăn một 413 thật**.

🔴 **Và nó suýt làm hỏng cả phép nghiệm thu.** Tôi viết phép kiểm theo **điều tôi tin bản vá làm**
thay vì **điều mã làm**: *"phiên mới tinh, gửi ngay một lượt vượt trần"*. Trên một tiến trình mới
thì **cả bản cũ lẫn bản mới đều phải ra mạng** ⇒ phép kiểm **xanh trên cả hai**, và bản vá sẽ được
phát hành kèm một lời hứa không ai kiểm.

**Phép đúng là HAI LƯỢT** (lượt 1 nhỏ dạy trần, lượt 2 vượt trần), **kèm nền so sánh đo trên chính
bản cũ**: 0.2.15 lượt 2 → 413 mạng thật **1,4 s, có `requestId`**. Dấu hiệu phân biệt chắc nhất là
**`requestId`** — chỉ máy chủ sinh ra nó, nên có `requestId` nghĩa là **đã ra mạng**.

> Bài học, cùng họ với cả ngày hôm nay: **phép kiểm viết theo niềm tin về mã sẽ xác nhận niềm tin
> đó, không xác nhận mã.** Nền so sánh trên bản cũ là thứ duy nhất tách được hai điều ấy.

- [ ] **Việc kế (nhỏ):** đọc header **ở mọi phản hồi `/api/v1/*`**, kể cả lượt gọi catalog lúc khởi
      động — khi đó lời hứa *"biết trần từ khi mở app"* mới đúng theo nghĩa đen.

---
## Việc 3 — 413 KHÔNG phân tích được (LTTCODE)

🔴 **Lỗ hổng chưa ai xử.** Trần của ta ≤ 100 MB nên app không bao giờ là tầng chặn thấp nhất — nhưng
**một tầng trung gian có thể hạ thấp hơn** (proxy công ty, Cloudflare đổi chính sách). Khi đó:

- 413 **không đến từ app ta**;
- 413 của Cloudflare là **HTML**, không phải `problem+json`;
- ⇒ nó **không mang** `limit_name`/`limit_value` ⇒ client "học" được **rỗng**.

Lưới đỡ có lỗ **đúng ở tình huống nó cần nhất**.

- [ ] Gặp 413 **không phân tích được** ⇒ hạ ước lượng trần một bậc thận trọng rồi thử lại.
- [ ] **Chặn vòng lặp**: số lần hạ có trần cứng; hết thì báo lỗi rõ ràng, ⛔ đừng thử mãi.
- [ ] Phép kiểm: 413 **HTML không có thân JSON** ⇒ vẫn học được *một điều gì đó*, không im lặng bỏ qua.

---
## Việc 4 (tuỳ chọn) — trường ở gốc `GET /models`

- [ ] Đặt ở **cấp gốc**, cạnh `capabilities`. ⛔ **KHÔNG** vào `constraints` từng model: nó là hằng
      của **điểm cuối**, không của model — lặp N lần và ngụ ý nó đổi theo model là **sai hình dạng**.

⚠️ **Giá trị thấp**, nói thẳng: client **đã** gọi `/models` rồi, nên nó chỉ tiết kiệm được đúng một
vòng — mà Việc 1 đã xoá vòng đó. Làm nếu tiện, không làm cũng không sao.

---
## Những gì KHÔNG làm

- ⛔ **Không** bỏ đường học-từ-413. Nó là thứ **duy nhất** đúng khi một tầng trung gian hạ trần, và
  là thứ duy nhất phục vụ client **chưa cập nhật**.
- ⛔ **Không** nhét `max_body_bytes` vào `constraints` từng model.
- ⛔ **Không** chờ một chuẩn IETF — đã tra, **không có** draft nào cho kích thước thân.
- ⛔ **Không** dùng MCP capability negotiation: nó là cờ **bật/tắt tính năng**, không phải kênh
  công bố **con số** (`modelcontextprotocol` `schema/2025-11-25`).

---
## Thứ tự

**1 → 2** (client không đọc được thứ chưa gửi) · **3 song song** (độc lập) · **4 sau cùng, nếu tiện**.

Sau **1 + 2**, cái giá *"một 413 mỗi lần mở app"* chỉ còn cho client **chưa cập nhật** — và với
họ thì lưới đỡ vẫn chạy y như hôm nay.
