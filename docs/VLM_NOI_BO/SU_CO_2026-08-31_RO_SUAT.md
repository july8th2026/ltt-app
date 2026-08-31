# Sự cố 31/08/2026 — một suất bị rò, sáu giờ ngừng dịch vụ

**Trạng thái:** nguyên nhân đã chứng minh · đã sửa ba lớp · **chưa deploy**.

---

## 1. Chuyện gì đã xảy ra

Một khách (`dungnv.forwork@gmail.com`) gọi **117** lượt qua `/api/v1/responses`.
**89 lượt hỏng.** Đo từ `public_api_requests`:

```
71x  503 service_unavailable  /api/v1/responses   14:02 -> 15:59
26x  200                      /api/v1/responses   09:33 -> 11:23
16x  429 concurrency_limited  /api/v1/responses   09:38 -> 11:27
```

Lượt thành công cuối cùng **11:23**. Đo lúc 17:24 — hơn sáu giờ sau, không còn
lưu lượng nào:

```
POST /v1/responses  ->  429   {"ly_do": "cong dang day",
                               "chi_tiet": "dang chay 1/1 luot"}
gioi_han : dang_chay=1 / max=1        trong_phut_qua=0
gpu      : co_model_nap=false, vram_dung_mb=null
trong_tai: ban=false, ram_trong_gb=120.1
```

**Một suất bị giữ. Không việc nào chạy. Model còn chưa nạp. GPU rảnh hoàn toàn.**

---

## 2. Nguyên nhân

`boc_luong` trả suất trong `finally`. Nhưng nó là một **generator**: gọi nó chỉ
*tạo* generator, chưa chạy dòng nào. Nếu Starlette không bao giờ lặp qua nó —
khách ngắt trước byte đầu tiên — thì khối `try` **chưa từng được vào**, nên
`finally` không tồn tại về mặt thực thi. Suất giữ vĩnh viễn.

Tái hiện được, trên chính `gioi_han.py`:

```
A) luồng chạy hết                    -> suất được trả  ✓
B) khách đóng GIỮA CHỪNG             -> suất được trả  ✓
C) tạo generator, KHÔNG chạy lần nào -> suất KHÔNG trả ✗
D) (không chạy nổi: cap_suat() trả None — sự cố tự tái hiện trong bàn thử)
```

Với `max_dong_thoi = 1`, **một** lần rò là mất sạch năng lực.

🔴 **Và đây là ba generator lồng nhau, cùng một khuyết tật:**

```
upstream.stream()._di()   finally: ctx.__exit__ + client.close()
  └ nhip_tim._di()        finally: luong.close()
      └ boc_luong()       finally: suat.tra()
```

Không lặp cái ngoài cùng thì **không `finally` nào chạy**. Suất là thiệt hại nặng
nhất; socket thượng nguồn và `llama-server` sinh chữ cho một yêu cầu không ai đọc
là thiệt hại thứ hai.

⭐ **Khuôn đúng đã có sẵn trong kho, một tầng phía trên.** Máy A nhả vé nhận vào
bằng `BackgroundTask` (`server/api/streaming.py:694`) — thứ Starlette chạy khi
phản hồi kết thúc, kể cả khi thân chưa từng được đọc. Máy B chưa được mang sang.

---

## 3. Chấm điểm chất lượng hệ thống

Chấm theo **hành vi đã đo được trong sự cố này**, không theo ý định của mã.

| Chiều | Trước | Sau | Bằng chứng |
|---|:--:|:--:|---|
| Đúng đắn khi hỏng (tiền) | **9** | 9 | 89 lượt hỏng, `credit=+0` **mọi dòng**; `Retry-After: 15` gửi đủ; khoá `ltt_image`/`ltt_llm` vẫn `active` — bẫy D-005 đã tránh được |
| Cách ly lỗi | **3** | 5 | `max_dong_thoi=1` ⇒ một suất rò = **100%** ngừng dịch vụ. Không có mức suy giảm nào ở giữa |
| Tự phục hồi | **1** | 8 | Trước: không có; cần người khởi động lại. Sau: thu hồi sau `han_giu_s`, chặn trên 20 phút |
| Khả năng phát hiện | **2** | 8 | Sáu giờ, **0 dòng log**; cảnh báo nói `responses_5xx` (= "nền tảng hỏng") trong khi `CAPACITY_REFUSED` đứng im ở 0; `/health` báo `dang_chay: 1` — không phân biệt được với trạng thái khoẻ |
| Kiểm thử | **6** | 8 | 22 phép kiểm cho hàng rào, 3 cho vòng đời generator, lập luận rất kỹ — nhưng **cả ba đều gọi `next(g)` trước** |
| Chất lượng lập luận trong mã | **9** | 9 | Chính mã đã cảnh báo đúng sự cố này **ba lần**, kèm triệu chứng chính xác (*"429 vĩnh viễn trong khi GPU rảnh hoàn toàn"*, *"rất khó lần ra"*) và bịt 3/4 đường |
| Nhất quán khuôn giữa hai máy | **4** | 8 | Máy A dùng `BackgroundTask` (đúng); máy B dùng `finally` của generator (rò) |
| **Tổng** | **4,9** | **7,9** | |

**Đọc bảng này thế nào.** Hệ thống **hỏng an toàn** (9/10 về tiền — không khách
nào bị thu một credit cho 89 lượt hỏng) nhưng **hỏng vô hình và không tự dậy
được**. Đó là hai chiều khác nhau, và chiều thứ hai mới biến một lỗi nhỏ thành
sáu giờ.

⭐ Điểm 9 cho *chất lượng lập luận* không mâu thuẫn với sự cố — nó là phần đau
nhất của bài học: **mã đã biết trước cái bẫy này, viết nó ra ba lần, bịt ba
đường, và trượt đường thứ tư.** Vấn đề không phải thiếu cẩn thận. Vấn đề là một
danh sách các đường rò **do người liệt kê** thì không bao giờ có cách nào biết nó
đã đủ chưa.

---

## 4. Cách sửa — ba lớp, cố ý chồng nhau

| Lớp | Sửa gì | Bảo vệ trước |
|---|---|---|
| 1. `BackgroundTask` trong `api.py` | trả suất khi **phản hồi** kết thúc, không phụ thuộc generator có chạy | đúng đường rò đã biết |
| 2. `LuongUpstream.dong()` | đóng được **mà không cần lặp** | socket + `llama-server` bị bỏ lại |
| 3. **Hạn giữ suất** trong `gioi_han.py` | thu hồi suất giữ quá `han_giu_s` (1.200 s) | **mọi** đường rò, kể cả đường thứ năm chưa ai nghĩ ra |

Lớp 3 là thứ làm bản vá này "triệt để" chứ không phải "vá". Hai lớp đầu sửa cái
đã biết; **lớp 3 không đoán gì cả** — nó chỉ khẳng định một điều yếu hơn nhưng
đúng với mọi đường: *không lượt nào chạy lâu hơn `han_giu_s`*.

Kèm hai số mới ở `/health`:

* `giu_lau_nhat_giay` — biến một suất treo thành **hiển nhiên**, thay vì trông
  y hệt một lượt đang chạy. Đây là số lẽ ra đã cắt sáu giờ xuống vài phút.
* `da_thu_hoi` — khác 0 nghĩa là **có bug**, chỉ là bug đó không còn gây sự cố.
  Việc thu hồi cũng ghi `log.warning`. **Tự lành mà im lặng chỉ đổi một sự cố
  nhìn thấy được lấy một sự cố vô hình.**

⛔ **Đừng hạ `han_giu_s` để phát hiện sớm hơn.** Thu hồi một suất *đang chạy
thật* là cho hai lượt vào một GPU `--parallel 1` — đổi một sự cố tự khỏi lấy một
sự cố tệ hơn. Muốn sớm thì đọc `giu_lau_nhat_giay`; nó báo ngay mà không đụng
vào lượt nào.

### Phía máy A (đã sửa cùng ngày, trong cùng sự cố)

* `luong_vlm.py` — máy B phân biệt **ba** kiểu bận và gửi kèm lý do; máy A đọc
  vào một biến rồi **vứt đi**, thay bằng chuỗi cứng. Nay lý do đi theo.
* `streaming.py` · `chat.py` — ba nhánh bận không tăng `CAPACITY_REFUSED` và
  không ghi log. Nay có cả hai.

---

## 5. Việc còn phải làm

1. **Khôi phục:** khởi động lại `LTTLlmGateway` trên máy B (suất nhả ngay).
2. **Deploy** `llm_gateway/` xuống máy B — `llm_gateway/deploy/deploy.ps1`.
3. Deploy máy A cho phần `luong_vlm`/`streaming`/`chat`.

⚠️ Thứ tự không quan trọng với đúng đắn, nhưng ① là thứ khách đang chờ.

---

## 6. Bài học mang đi được

**Một `finally` trong generator không phải một bảo đảm.** Nó chỉ tồn tại sau khi
generator chạy dòng đầu tiên. Tài nguyên lấy *ngoài* generator mà trả *trong*
generator là một đường rò, luôn luôn — bất kể `finally` viết kỹ đến đâu.

**Một bộ test bao kín "sau khi bắt đầu" vẫn có thể để trống "chưa bắt đầu bao
giờ".** Ba phép kiểm vòng đời ở `test_258` đều mở đầu bằng `next(g)`.

**Tự lành phải ồn ào.** Một lưới cứu im lặng chỉ chuyển sự cố từ chỗ nhìn thấy
được sang chỗ không ai thấy.

**Cảnh báo phải trỏ đúng loại nguyên nhân.** Thư gửi người trực nói
`responses_5xx` — *"nền tảng hỏng"* — trong khi nền tảng làm đúng và thứ hết là
năng lực. Sai ngay ở dòng tiêu đề thì mọi phút điều tra sau đó đi sai hướng.
