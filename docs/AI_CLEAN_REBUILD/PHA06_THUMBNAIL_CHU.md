# Pha 06.3 — `thumbnail` mất tính năng **chữ trong ảnh**

**Ngày:** 2026-09-09 · chiến dịch **LTT AI CLEAN REBUILD V2** · pha 06.3
**Trạng thái:** đã thi hành. Mục cuối là thứ chỉ chủ sản phẩm quyết được.

---

## 1. Câu chuyện ngắn

Chiến dịch này xoá Gemini khỏi nền tảng, tuyệt đối, không giữ lại làm dự phòng.
`thumbnail` là app cuối cùng còn chạy Gemini Image, nên nó phải đổi động cơ sang
`LTT_IMAGE` (`hidream-o1`, máy B).

Nhưng `thumbnail` **sinh ra để viết chữ tiếng Việt lên ảnh**, và model nhà không
làm được việc đó. Đó là một va chạm giữa **hai quyết định của cùng một chủ sản
phẩm**, không phải một chi tiết kỹ thuật:

```
D-048 (24/08)   "HiDream khong ho tro tieng Viet trong anh, toi cung khong can."
                "Neu sau nay co khach hoi tool sinh anh co chu, cau tra loi la
                 GEMINI, va do la cau tra loi cuoi cung."

Chien dich (09/09)   Gemini phai bien mat het. Khong duoc giu vi:
                     du phong · tuong thich · dung sau nay · da co API key.
```

⇒ Chiến dịch xoá đúng **câu trả lời** mà D-048 đã chỉ định.

---

## 2. Bằng chứng, không phải phỏng đoán

Hai nguồn độc lập, cả hai đều nằm trong kho, cả hai đều nói cùng một điều.

**(a) Năng lực khai báo của chính model** — `platform_core/providers.py`:

```python
"canh_bao": [N_("prompt phải là tiếng Anh — nền tảng tự dịch"),
             N_("chữ tiếng Việt CÓ DẤU vẽ trong ảnh bị sai dấu")],
```

Cùng khối ấy mở đầu bằng luật của nó: *"CHỈ khai thứ ĐÃ ĐO THẬT."*

**(b) Quyết định D-048** (`docs/ANH_NOI_BO/DECISIONS.md:2446`) — trích ở mục 1.

### ⛔ Và một lập luận đã bị bác

> *"Chỉ tiếng Việt hỏng thôi; còn English/日本語/한국어/中文 thì cứ để đó."*

Bốn thứ tiếng kia **chưa ai đo**. Thứ tiếng duy nhất đã đo thì hỏng. Bán một
năng lực chưa đo là hứa một thứ ta không biết mình có — và đó đúng là điều luật
`capabilities` ngay bên trên cấm. Nên cả năm lựa chọn cùng đi.

---

## 3. Đã làm gì

### Gỡ khỏi sản phẩm

| Thứ | Số | Ghi chú |
|---|---|---|
| Tham số `title`, `subtitle` | 2 | gửi lên ⇒ **từ chối có tên**, không bỏ qua im lặng |
| Nhóm `text_style` | 6 kiểu chữ | thư mục prompt bị **xoá khỏi đĩa** |
| Nhóm `ngon_ngu` | 5 thứ tiếng | thư mục prompt bị **xoá khỏi đĩa** |
| Bố cục `listicle_numbered`, `text_heavy_chu_lon` | 2 / 9 | cả hai **đòi** chữ vẽ ra |
| Ô nhập + ô chọn trên hai template | 4 | `thumbnail.html`, `thumbnail_fragment.html` |

`base_prompt.txt` nay **cấm chữ tường minh**: *"No text, no lettering, no
captions, no numbers and no watermark anywhere in the image."* Không cấm thì
model vẽ chữ giả — và chữ giả trông tệ hơn không có chữ.

### Giữ lại

`topic` · `phong_cach` (11 phong cách) · `kieu_trend` (7 bố cục) · `aspect_ratio`
(5 tỉ lệ, cả năm đều có khung máy B khai được) · `count` · Brand Kit · remix từ
một output cũ · chấm điểm kỹ thuật.

⇒ Sản phẩm còn lại là **máy sinh ảnh nền thumbnail**: bố cục, phong cách, chủ
thể. Khách thêm chữ ở bước sau, bằng công cụ của họ.

### ⚠️ Một chỗ còn rủi ro, ghi ra để không ai bất ngờ

`brand_directive()` vẫn đưa **tên thương hiệu** vào prompt
(`brand=LTT Studios; font=Barlow…`). Nó là chỉ dẫn *phong cách*, nhưng model có
thể hiểu thành "vẽ chữ này". Chưa đo. Nếu ảnh ra có chữ thương hiệu méo mó thì
đây là chỗ cần xử lý — không phải một lỗi mới.

---

## 4. Vì sao KHÔNG chọn hai phương án còn lại

| Phương án | Vì sao bỏ |
|---|---|
| **Cứ vẽ, chữ méo thì thôi** | Đúng cái mà pha 06.2 đã từ chối làm với `taoanh`: một tính năng hỏng lặng lẽ đắt hơn một tính năng bị gỡ tử tế. Khách gõ tiêu đề, trả tiền, nhận về chữ sai dấu — và không gì trong hệ thống nói cho họ vì sao. |
| **Gỡ hẳn cả app `thumbnail`** | Phần còn lại **vẫn là một sản phẩm**: 11 phong cách × 7 bố cục × 5 tỉ lệ + Brand Kit + remix. Gỡ một app là quyết định thương mại, và nó không bắt buộc để hoàn thành pha này. |

Luật áp dụng là luật của chính gói prompt chiến dịch: *"feature LTT_IMAGE không
hỗ trợ ⇒ **disable/remove**, không fallback."* Thứ bị disable là **tính năng
chữ**, không phải cả app.

---

## 5. 🔴 Việc của chủ sản phẩm — một quyết định, ba lối

Tôi **không** tự quyết mục này, và pha 06 **không** chờ nó.

1. **Giữ nguyên như đang làm.** `thumbnail` là máy sinh ảnh nền; ai cần chữ thì
   tự thêm. Chi phí: 0. Mất: lời hứa "AI viết tiêu đề cho bạn".
2. **Mua lại năng lực chữ.** Cần một động cơ ảnh biết dựng chữ. Đây là quyết
   định **chi tiền**, và nó nằm ngoài phạm vi chiến dịch dọn dẹp này.
3. **Đo `hidream-o1` cho bốn thứ tiếng chưa đo.** Nếu một thứ tiếng nào đó đạt,
   mở lại đúng thứ tiếng ấy — và lúc đó nó là một năng lực **đã đo**, khai được.

⚠️ Lối 3 phải là **một lô đo có đối chứng**, không phải "thử vài tấm thấy được".
D-048 chính là bài học ấy: một phép đo đúng vẫn vô dụng nếu thứ nó đo không phải
thứ khách trả tiền.

---

## 6. Dấu vết

- Mã: `apps/thumbnail/jobs.py` (khối đầu tệp), `manifest.py`, `routes.py`
- Hợp đồng công khai: `docs/PUBLIC_API/CHANGELOG.md` mục **BREAKING 2026-09-09**
- Phép kiểm: `tests/test_71_thumbnail.py::test_tieu_de_bi_TU_CHOI_CO_TEN_…`,
  `tests/test_77_thumbnail_parity.py::test_hai_nhom_CHU_da_bi_go_han_khoi_dia`
- Nguồn bằng chứng: `platform_core/providers.py` (`canh_bao`),
  `docs/ANH_NOI_BO/DECISIONS.md` (D-048)
