# Prompt 02 — Execution, Admission & Billing (phần đã kiểm)

**31/08/2026.** Ownership: B01–B25.

⚠️ **Phase này CHƯA đóng.** Đã kiểm bằng đọc mã + bằng chứng sống có sẵn; **chưa
tiêm lỗi** vào các cửa sổ sự cố. Xem §5.

---

## 1. 🔴 Câu hỏi Prompt 01 chuyển sang — và câu trả lời NGƯỢC với lo ngại

Prompt 01 nêu: *"cửa stream đếm token tại chỗ ⇒ hai nguồn sự thật cho một đại
lượng tính tiền"*. **Sai, và đây là lý do.**

`dem_token_luong.DemToken` **không ước lượng gì cả**. Nó quét **mọi khối `usage`
bắt gặp** trong luồng SSE và giữ giá trị lớn nhất từng thấy. Tức nó đọc **đúng
`usage` của thượng nguồn**, chỉ khác ở chỗ đọc **dọc đường** thay vì đọc ở cuối.

⇒ **Một nguồn sự thật, đọc hai cách.** Không có drift.

**Bằng chứng sống**, từ `ltt-server.jsonl` production:

```
STREAM XONG  khoi=64    token_ra=67
STREAM XONG  khoi=1471  token_ra=1549
```

`token_ra ≠ khoi` ở cả hai ⇒ đó là `usage` thật, không phải phép đếm khối.

### ⛔ Và một chỗ tôi phải tự sửa trong `reports/04`

Prompt 04 tôi ghi *"thượng nguồn **không gửi** `usage` trong luồng SSE"*. Đó là
**giới hạn của bộ đo tôi viết**, không phải của nền tảng: tôi gọi cửa
`/v1/chat/completions` mà **không xin `stream_options.include_usage`** — kiểu
OpenAI chỉ gửi `usage` khi được xin. Ba cửa thật của nền tảng (`/messages`,
`/responses`, và cửa đồng bộ) **có** nhận được.

Hệ quả: `decode_tok_s` trong `reports/04` là **ước**, và nó ước vì tôi đo thiếu
một tham số — không vì hệ thống thiếu dữ liệu.

⭐ Bài học lặp lại lần thứ ba hôm nay: **một con số có thật, gán cho một tập hợp
khác với tập hợp đang mô tả.**

---

## 2. Vì sao đếm dọc đường là lựa chọn ĐÚNG

Chú thích của `dem_token_luong.py` nói ra bài toán, và nó đúng:

> Với streaming thì **luồng có thể không bao giờ tới cuối**: khách bấm Ctrl-C,
> mạng đứt, Cloudflare rớt. Mà GPU thì **đã đốt rồi**.

Hai lựa chọn tồi và một lựa chọn đúng:

| | Hệ quả |
|---|---|
| thu trọn phần đã giữ | lỗi tiền im lặng |
| không thu gì | cho không một lượt đã tốn điện và GPU |
| **đếm dọc đường** | **thu đúng phần đã sinh ra** |

⛔ Và nó là **ống nhòm, không phải bộ lọc**: không sửa, không cắt, không dựng lại
byte nào. Có đệm cho tới khi thấy đủ một dòng, vì `iter_raw()` trả byte theo
nhịp mạng — một `data: {...}` hoàn toàn có thể tới làm ba khối, và phân tích
từng khối rời rạc là **hỏng ngẫu nhiên theo tải**.

---

## 3. Tiền — bất biến đã xác minh

| Bất biến | Cơ chế | Bằng chứng |
|---|---|---|
| `request_id` là khoá idempotency của **cả** giữ chỗ lẫn quyết toán | `giu_cho_luot` ném nếu thiếu | mã, `test_253` |
| Không đọc được `usage` ⇒ **hoàn đủ, thu 0** | `quyet_toan_hoac_hoan` bắt `KhongDoDuocError` | mã + `test_252` |
| Bận ⇒ không thu | ba nhánh `BanError` → `hoan_luot` | **sự cố 31/08: 89 lượt, `credit=+0` mọi dòng** |
| Quyết toán chạy trong **phiên CSDL mới** | `_quyet_toan` mở `get_session()` riêng | mã |
| Khoản giữ chỗ treo được tự hoàn | `credit.tu_hoan_treo` dưới `_mot_luot_bao_tri` | H41.3 |
| Nhiều worker không nhân đôi | `test_214` | **7 passed / 134,61 s** (31/08) |

⭐ **Vì sao "phiên CSDL mới" quan trọng**: generator `_phat` chạy **sau khi phản
hồi đã bắt đầu**, lúc đó `get_db` của request đã đóng. Dùng lại phiên cũ là
`DetachedInstanceError` — hoặc tệ hơn: **một giao dịch không bao giờ được
commit**, tức tiền treo mãi.

### ⭐ Một lỗi production-only đã được neo đúng cách

`ma_luot()` mang một bài học đắt: `credit_entries.job_id` là `VARCHAR(36)`.
**SQLite không ép độ dài, PostgreSQL thì có** — nên hai cửa thu tiền chạy sạch
qua **toàn bộ** bộ test rồi trả `500` ngay lượt gọi thật đầu tiên (23/08).

> Bài học không phải "đếm ký tự cẩn thận hơn", mà là: **một ràng buộc chỉ tồn
> tại ở production là một ràng buộc chưa được test.**

`test_273` neo nó bằng cách **đo thẳng độ dài**, không cần PostgreSQL. Đó là
cách đúng: đưa ràng buộc production về nơi test chạm được.

---

## 4. Nhận vào / lease (B05–B08) — **VERIFIED-KEEP**

Thứ tự trong cửa stream, đọc từ mã:

```
580  admission.acquire(...)         ve nhan vao
633  thanh_toan.giu_cho_luot(...)   giu tien
650  db.commit()                    CHOT GIAO DICH truoc khi cham model
655  luong_vlm.mo(...)              mo luong toi may B
690  StreamingResponse(..., background=BackgroundTask(release))
```

* **Nhận vào trước tiền** — từ chối không tốn một bút toán nào.
* **Chốt giao dịch trước khi chạm model** — giữ giao dịch mở suốt lượt gọi là
  giữ luôn một kết nối CSDL, và tiến trình chết giữa chừng sẽ **cuộn mất phần
  giữ chỗ**.
* **Nhả vé bằng `BackgroundTask`** — chạy khi phản hồi kết thúc, kể cả khi thân
  chưa từng được đọc. *(Đây chính là khuôn mà máy B thiếu và đã gây sự cố rò
  suất sáng 31/08 — xem `SU_CO_2026-08-31_RO_SUAT.md`.)*
* **Không có hàng đợi ẩn**: đầy ⇒ 429 + `Retry-After` trong 0,05 s (đo Prompt 03).

---

## 5. Còn nợ

| Mục | Trạng thái |
|---|---|
| B18 tiêm lỗi vào **bảy cửa sổ sự cố** (trước giữ · sau giữ trước commit · sau commit trước dispatch · sau dispatch trước token đầu · giữa chừng · sau khi xong trước quyết toán · sau quyết toán trước khi client nhận) | **CHƯA** |
| B16/B17 huỷ và ngắt kết nối — kiểm bằng client thật | **CHƯA** |
| B14/B15 phạm vi idempotency khi **thử lại** | mới đọc mã, chưa đo |
| B24 tool-call streaming | **CHƯA** |

⛔ Không đánh dấu phase này `PASS`. Bảy cửa sổ sự cố là phần **khó nhất** của
B01–B25, và chúng chưa được chạm.

---

## Quyết định

| ID | Ứng viên | Quyết định | Vì sao |
|---|---|---|---|
| D-02-1 | `DemToken` đếm dọc đường | **KEEP** | Đọc `usage` thật; một nguồn, hai cách đọc |
| D-02-2 | `reports/04` nói "upstream không gửi usage" | **SỬA** | Giới hạn của bộ đo tôi viết, không của nền tảng |
| D-02-3 | Thứ tự nhận-vào → giữ tiền → commit → dispatch | **KEEP** | Mỗi bước có lý do ghi rõ và đã trả giá |
| D-02-4 | `request_id` là khoá idempotency | **KEEP** | Thiếu thì ném, không lặng lẽ đi tiếp |
