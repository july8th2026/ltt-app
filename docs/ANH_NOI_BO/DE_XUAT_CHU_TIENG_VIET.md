# Đề xuất: xử lý chữ tiếng Việt trong ảnh

**22/08/2026 · cần chủ dự án quyết · chưa động vào mã**

Đây là đề xuất, không phải quyết định đã chốt. Nó mô tả một vấn đề **đã đo được**,
ba đường đi, và một khuyến nghị kèm cái giá của nó.

---

## 1. Vấn đề, bằng số

HiDream-O1 vẽ chữ **Latin không dấu** rất tốt, và vẽ chữ **có dấu tiếng Việt** thì
sai — kể cả khi prompt đã là tiếng Anh và bố cục đã đúng hoàn toàn.

| Yêu cầu | Model vẽ ra |
|---|---|
| `CƠM TẤM SƯỜN BÌ` | `CỘM TÀM SUÔN BÌ` |
| `NHỮNG NGÀY THƠ ẤU` | `NHÙNG NGÃY THỎ ÂU` |
| `BẤT NGỜ!` | `BÂT NGỖ!` |
| `GIẢM 50% HÔM NAY` | `GIẤM 50% HÔM NAY` ← gần nhất, vẫn sai 1 dấu |

Trong khi cùng model, cùng lô:

| Yêu cầu | Model vẽ ra |
|---|---|
| `LTT STUDIOS` | `LTT STUDIOS` ✅ |
| `RTX 3090` | `RTX 3090` ✅ |
| `COM TAM SUON BI` *(không dấu)* | `COM TAM SUON BI` ✅ |
| `Ship it on Friday` | `Ship it on Friday` ✅ **kèm cả mũi tên vẽ tay** |

**Ranh giới nằm chính xác ở dấu, không ở tiếng Việt nói chung.** Cùng một biển hiệu:
viết có dấu thì sai, viết không dấu thì đúng từng chữ.

**Vì sao chuyện này lớn:** ba trong bốn ca dùng chính của khách là thumbnail YouTube
tiếng Việt, poster khuyến mãi, và biển hiệu — **chữ là nội dung chính**, không phải
trang trí. Một thumbnail ghi `BÂT NGỖ!` là không dùng được, dù ảnh đẹp đến đâu.

⚠️ **Đây KHÔNG phải vấn đề riêng của model nhà.** Mọi model khuếch tán đều vẽ chữ
bằng cách "đoán hình dạng", không bằng cách sắp chữ. Cần đo Gemini 3 Pro Image ở
G6b trên đúng bốn prompt này trước khi kết luận model nhà thua ở khoản này.

---

## 2. Ba đường đi

### A. Sinh ảnh KHÔNG chữ, rồi ghép chữ bằng phông thật *(khuyến nghị)*

Nền tảng bỏ phần chữ ra khỏi prompt, sinh ảnh với **vùng trống dành cho chữ**, rồi
ghép chữ lên bằng thư viện vẽ chữ (`Pillow` — đã có sẵn trong nền tảng).

**Được:**
- **Chữ luôn đúng dấu**, 100 %, không phụ thuộc may rủi.
- **Đúng phông thương hiệu** — khách chọn phông, cỡ, màu, viền, đổ bóng.
- **Sửa được chữ mà không phải sinh lại ảnh.** Sai chính tả thì sửa trong 1 giây
  thay vì 60–170 giây GPU. Đây là cái lợi lớn nhất mà ít ai nghĩ tới ngay.
- Đây **là cách làm thumbnail chuyên nghiệp vẫn dùng** — không ai để Photoshop
  đoán chữ hộ mình.

**Mất:**
- Chữ **không hoà vào ảnh**: không có phản chiếu trên kính, không cong theo mặt vải,
  không bị che một phần bởi vật thể. Với thumbnail/poster thì **chữ nổi lên trên là
  đúng ý đồ**; với biển hiệu trong cảnh thì trông sẽ giả.
- Cần một trình soạn thảo tối thiểu ở giao diện (vị trí, cỡ, màu) — thêm việc UI.

**Ước lượng:** một module `platform_core/image_gen/ghep_chu.py` + phần UI. Không
cần GPU, test được hoàn toàn trên máy A.

### B. Viết không dấu, chấp nhận mất dấu

Prompt tự động bỏ dấu: `CƠM TẤM SƯỜN BÌ` → `COM TAM SUON BI`. Model vẽ đúng.

**Được:** gần như miễn phí, làm trong một buổi, chữ hoà vào ảnh tự nhiên.
**Mất:** **chữ Việt không dấu trông rẻ tiền.** Với thương hiệu thì đây là mất mát
thật, không phải chuyện thẩm mỹ vặt. Chỉ hợp vài ca (biển hiệu kiểu retro, chữ
trang trí ở hậu cảnh).

### C. Thêm một model chuyên vẽ chữ

Có model khuếch tán vẽ chữ tốt hơn hẳn (dòng có bộ mã hoá glyph riêng). Thêm một
model nữa cho riêng khâu chữ.

**Được:** chữ hoà vào ảnh **và** đúng dấu — nếu tìm được model làm được tiếng Việt.
**Mất:** thêm 10–20 GB VRAM trên một card **đã dùng 73 %**; thêm một model phải
đánh giá, cấp phép, bảo trì; và **chưa ai chứng minh** có model mã nguồn mở nào vẽ
đúng dấu tiếng Việt. Đây là đường **đắt nhất và rủi ro nhất**.

---

## 3. Khuyến nghị

**Chọn A, và làm B như một tuỳ chọn phụ.**

Lý do quyết định không phải "A đẹp hơn" — mà là: **A biến một thứ ngẫu nhiên thành
một thứ chắc chắn.** Với B và C, mỗi lần khách bấm sinh ảnh là một lần rút thăm xem
dấu có đúng không. Với A thì không có rút thăm nào cả.

Và cái lợi **sửa chữ không cần sinh lại ảnh** đáng giá hơn nó thoạt nghe: khách làm
thumbnail sẽ đổi chữ 5–10 lần cho một ảnh. Với A, chín lần trong số đó **không tốn
một giây GPU nào**.

**Không chọn C bây giờ.** Card đã ở 73 % VRAM với một model; thêm model thứ hai là
đụng đúng cái trần đã làm hỏng việc một lần. Để lại nếu A không đủ.

---

## 4. Nếu chọn A thì cần quyết thêm ba điều

1. **Ai đặt vị trí chữ?** Khách kéo thả (linh hoạt, cần UI), hay nền tảng tự đặt
   theo khuôn thumbnail (nhanh, ít việc, kém linh hoạt)?
2. **Bộ phông nào?** Cần phông có **đủ dấu tiếng Việt** và **giấy phép thương mại**
   (không phải phông Google nào cũng đủ dấu — phải kiểm từng phông).
3. **Prompt có nên nói "chừa chỗ cho chữ" không?** Nếu có, ảnh sinh ra sẽ có vùng
   trống hợp lý; nếu không, chữ có thể đè lên mặt người.

---

## 5. Việc phải làm trước khi quyết

- [ ] **G6b đo Gemini 3 Pro Image trên đúng bốn prompt chữ tiếng Việt này.** Nếu
      Gemini cũng sai dấu thì đây là hạn chế của cả ngành, không phải điểm yếu
      riêng — và điều đó đổi hẳn cách nói với khách.
- [ ] Thử một lượt: sinh ảnh không chữ + ghép chữ bằng Pillow, cho chủ dự án xem
      **trông có dùng được không** trước khi làm UI.

**Không viết một dòng mã nào cho hạng mục này trước khi có hai thứ trên.**
