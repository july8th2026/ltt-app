# 05 — API / NAV / COPY AUDIT (2026-09-05)

## OBSERVED — cùng một con số, hai quy ước đọc

| chỗ | trước | sau |
|---|---|---|
| ô đếm Studio | `100.000` | `100.000` |
| màn API, "Mỗi lượt gọi" | **`100000`** | `100.000` |
| thông điệp lỗi `/xem-truoc` | **`100000`** | `100.000` |
| thông điệp lỗi `/tao` | **`100000`** | `100.000` |
| khối lỗi Dự án | **`1500`** | `1.500` |
| trang Điều khoản | `100.000` (formatter chép tay) | `100.000` (filter chung) |

⛔ Ba dòng đậm nằm **trên cùng một luồng người dùng**: khách thấy `100.000` ở ô
đếm, bấm nút, và nhận về một câu nói `100000`. `server/templating.py::_so` được
dựng ra chính vì lớp lỗi này (đo 25/08: khu API hiện `50000 credit` trong khi
trang VPS hiện `149.000`), nhưng **filter chỉ tới được nơi có Jinja** — thông
điệp lỗi thì không.

## DECISION

Tách thân hàm ra `platform_core/dinh_dang.py::so_viet()`. `_so` của
`templating.py` gọi nó. Một định nghĩa, ba nơi dùng: filter khuôn mẫu, thông
điệp lỗi phía máy chủ, và `soViet()` trong `voice.js` (bản sao có ghi chú — xem
"rủi ro còn lại").

Đã gỡ hết formatter chép tay trong app Voice: không còn `"{:,}".format(...)`
nào trong `apps/ltt_voice/`.

## Nav — NĂM tab, và điều đó nay đúng ở mọi nơi

Nav thật (`manifest.py`) và nav đo trên trình duyệt khớp nhau:

    Tạo tiếng nói · Giọng của tôi · Dự án · Lịch sử · API

Residue "Chạy lô" đã dọn:

| chỗ | trước | sau |
|---|---|---|
| `manifest.py` | *"⭐ SÁU TAB, và từ P8 cả sáu đều đã xây"* | **NĂM**, kèm lý do tab thứ sáu không quay lại |
| `voice.js` | `taoLo()` + `motLo()` — **236 dòng**, export, **không ai gọi** | gỡ, thay bằng chú thích |
| `routes/_chung.py` | `NHAN_NGUON["lo"] = 'Chạy lô'` | gỡ |
| `doc_man_lich_su.py` | `NGUON = (…, "lo", …)` | gỡ |
| `du_an.py::duong_tieng` | *"Có NĂM chỗ dựng đường nghe (… ba ở Chạy lô)"* | năm là **lịch sử**; nay còn hai |
| `_voice_chon.html` | *"Dự án và Chạy lô khi chúng được xây"* | *"Studio và Dự án"* |
| `_voice_vo.html` | *"trang con (Dự án · Chạy lô)"* | *"trang con (Dự án)"* |

⭐ **Không dựng lại Chạy lô để một chú thích thành đúng.** Màn ấy sinh ra khi một
lượt sinh trần ở 1.500 ký tự: muốn đọc nhiều hơn thì phải nộp nhiều dòng. Đường
tài liệu dài lấy mất chính nhu cầu đó. Điều kiện để nó *được phép* quay lại đã
ghi trong `manifest.py`: một năng lực lô **thật** như `infer_batch` (gộp nhiều
đoạn vào MỘT lượt GPU — đo 01/09 cho 3,47× thông lượng, xem `tables_du_an.py`),
chứ không phải "mỗi dòng một job".

⚠️ **Giữ nguyên** những chỗ nhắc Chạy lô ở **thì quá khứ có ghi ngày**:
`tables_du_an.py` (ADR vì sao Dự án ≠ Chạy lô), `vo.py:106` và
`ltt_voice_thongbao.html` (tường thuật hai sự cố thật). Viết lại lịch sử cho
khớp hiện tại là xoá mất chính thứ khiến tài liệu ấy có giá.

## Copy 1.500 — phân loại từng chỗ

| loại | ví dụ | xử lý |
|---|---|---|
| A · sự thật engine nội bộ | `tham_so_cong_khai.py`, `text_pipeline.py`, `gia.py` | **giữ** — 1.500 vẫn là trần một lượt sinh |
| C · giao diện khách | ô đếm Studio | đã là `100.000` |
| D · hợp đồng API | màn API | đã là `100.000` |
| E · chú thích cũ | `du_an.py:228`, `doc_man_api.py:16` | **sửa** |

Hai chỗ loại E:
- `du_an.py:228` ghi *"VÌ SAO NÓ KHÁC `TRAN_KY_TU_CONG_KHAI` (1.500)"* — đúng khi
  hai trần còn là một số, sai từ 31/08. Đối chiếu đúng là `TRAN_MOI_LUOT_SINH`.
- `doc_man_api.py:16` ghi *"Trần 1.500 ký tự là trần gì? Nó là trần chất lượng"*
  — nay trần của một lượt **gọi** là trần **ngân sách**; trần chất lượng vẫn còn
  nhưng không còn rò ra thành trần sản phẩm.

## Ngôn ngữ · tốc độ · voice_id — KHÔNG đổi

Ba mục này (Phase 10/11/12 của bản yêu cầu) đã **audit và không tìm thấy điều
khiển giả**:

- **Ngôn ngữ** — chú thích dưới bộ chọn nói thẳng: *"Chỉ dùng để nhắc khi văn bản
  lệch làn của giọng. Máy đọc được cả hai thứ tiếng dù bạn chọn gì."* Đúng với
  `lan_ngon_ngu.py`. Không khiến ai hiểu là đổi model.
- **Tốc độ đọc** — chú thích nói *"Đổi sau khi tạo xong, giữ nguyên cao độ. Tiền
  tính theo bản gốc, không theo bản đã tăng tốc."* Đúng với `toc_do.py` và với
  cách `gia.py` tính tiền.
- **`voice_id`** — danh tính giọng vẫn tách khỏi biểu diễn engine; không đụng tới.
  Không tạo bảng cấu hình mới: thiết kế A (voice_id + tham số mỗi lượt) đang đủ,
  và bản yêu cầu nói rõ đừng tạo bảng chỉ vì nó được nhắc tới.

## STATUS

✅ Một quy ước đọc số cho cả nền tảng, có nơi giữ duy nhất.
✅ Năm tab, và mọi chú thích/nhãn/mã đều nói năm.
✅ Không điều khiển chết, không điều khiển giả.
