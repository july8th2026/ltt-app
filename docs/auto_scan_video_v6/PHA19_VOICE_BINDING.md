# Pha 19 — VoiceBinding + single-speaker production

**Trạng thái: XONG.** Ngày 11/09/2026.

Đề bài: *VoiceBinding chuẩn ở máy chủ, quyền sở hữu, version/vân tay, retry;
không để giao diện chọn được giọng bất hợp lệ.*

---

## 0. Đo trước: cái gì đã có, lỗ nằm ở đâu

| đề bài | hiện trạng trước pha 19 |
|---|---|
| binding chuẩn ở máy chủ | **đã có** — `giai_doan_noi_dung` gọi `rang_giong.rang` một lần, ghi `ma_giong` vào bản lồng tiếng; `long_tieng.kiem` bắt buộc trường đó khi ghi |
| quyền sở hữu | **đã có**, nhưng **muộn** — chỉ kiểm ở giai đoạn nội dung |
| version / vân tay | **đã có** — `van_tay_doan` gồm mã giọng + preset; vân tay giai đoạn nội dung gồm `settings` |
| retry | **đã có** — `RangGiongError` xếp `NGUOI_DUNG` (không thử lại vô ích) |
| không chọn được giọng bất hợp lệ | **lỗ** — xem §1 |

Hai lỗ thật, cả hai đều nằm ở chỗ **thời điểm**, không ở chỗ thiếu năng lực.

## 1. 🔴 Cửa không kiểm quyền sở hữu

`routes.tao` chỉ hỏi *"USER_SELECTED có kèm mã giọng không"*. Quyền sở hữu được
kiểm ở `giai_doan_noi_dung` — tức **sau** khi khách bị giữ credit và sau tách
nguồn + ASR, hai giai đoạn đắt nhất của chuỗi. Một mã giọng của người khác, một
giọng đã tắt, một mã gõ sai: cả ba đi hết đoạn đắt tiền rồi mới hỏng.

⇒ `rang_giong.kiem_o_cua` chạy **trước khi giữ credit**, và kiểm bằng **chính**
`_rang_khach_chon` — cùng đường giai đoạn nội dung dùng. Không có phép kiểm sở hữu
thứ hai: bản sao đầu tiên làm sai sẽ cho một khách đọc video bằng giọng nhân bản
của người khác.

⚠️ **Cùng MỘT câu cho "không có" và "không phải của bạn".** LTT Voice đã cố ý nói
vậy — phân biệt hai câu là cho phép dò xem mã giọng nào tồn tại. ASV chuyển
nguyên câu của họ, không viết lại.

⭐ **Chỉ bắt đúng lớp lỗi của khách** (`features.LoiGiongNoi`). Một lỗi CSDL đổi
thành *"giọng không hợp lệ"* là bảo khách sửa một thứ họ không hề làm sai.
`test_475` chốt cả chiều này.

`AUTO_MATCH` không kiểm gì ở cửa: giọng của nó chốt **sau**, từ hồ sơ nội dung.
Đòi một mã giọng ở cửa cho chế độ này là đúng lỗi D-V4-04 cấm.

`routes.py` giữ nguyên **899/900** dòng: khối kiểm cũ (6 dòng) được thay bằng khối
mới cùng độ dài.

## 2. 🔴 Đường lùi đọc thẳng `settings` — và nó không vô hại

`giai_doan_giong` đọc `tai_lieu.get("ma_giong") or cai.giong_id`. Với
`AUTO_MATCH`, `settings.giong_id` **rỗng**. Nên một bản lồng tiếng thiếu
`ma_giong` rơi xuống `""`, và `giai_giong("")` trả `(None, …)`: không giọng tham
chiếu, tức **giọng mặc định của engine**, không ai bấm nút — đúng lỗi D-V4-04
cấm, ở đúng chỗ docstring của `rang_giong` hứa sẽ đóng.

⇒ Đóng. Thiếu `ma_giong` nay ném `ChuaRangError` (xếp `NGUOI_DUNG`: thử lại không
làm trường ấy xuất hiện).

⭐ **Không nâng `PHIEN_BAN` nào.** Mọi bản lồng tiếng hợp lệ đều có `ma_giong`, nên
với mọi đầu vào hợp lệ đầu ra không đổi một byte — chỉ đầu vào thiếu trường ấy
nay bị từ chối. Hệ quả có giá: báo cáo nghiệm thu E2E vừa tái sinh ở pha 27
**vẫn còn hiệu lực**, không cần thêm một lượt nâng quyền.

## 3. Fixture lệch production

Cửa mới đọc bảng `voice_profile` của LTT Voice. Fixture `moi_truong`
(`test_423`) chỉ tạo bảng nền tảng + ASV, nên lượt đầu của bài HTTP gặp
`no such table: voice_profile` — một lỗi hạ tầng (500) trông như lỗi sản phẩm.
Production luôn có bảng ấy; fixture nay nạp `apps.ltt_voice.tables`.

⚠️ `test_455` gửi `giong_id="mau-1"` làm giọng giữ chỗ — **không** phải giọng mẫu.
Nó vẫn xanh vì kiểm kích thước chạy trước kiểm giọng; nhưng nó là một mẫu thử
đang mô phỏng một khách mà cửa mới sẽ từ chối.

## 4. Bằng chứng

* `tests/test_475_asv_v6_voice_binding.py` — **10 bài**, gồm bài HTTP thật hai
  người dùng: mã giọng không thuộc tài khoản ⇒ **400**, **không** tạo lần chạy,
  **không** đổi số dư credit; và đối chứng dương: giọng mẫu ⇒ lần chạy được tạo.
* Đối chứng: tiêm ba lỗi, cả ba **đỏ** — cửa chỉ kiểm rỗng như trước · mở lại
  đường lùi `or cai.giong_id` · bắt `Exception` chung. Ba tệp trả lại nguyên vẹn.

## 5. Còn nợ

* Bài HTTP dùng một mã giọng **không tồn tại**, chưa dùng giọng nhân bản thật của
  người dùng B. LTT Voice đưa hai trường hợp qua cùng một nhánh và cùng một câu,
  nên phạm vi phủ là như nhau — nhưng một bài dựng giọng thật cho B sẽ chốt cả
  tầng dữ liệu của LTT Voice.
* Pha 17 (lọc giọng theo ngôn ngữ) vẫn chặn: `giong_mau.loc()` chưa nhận tham số
  ngôn ngữ.
