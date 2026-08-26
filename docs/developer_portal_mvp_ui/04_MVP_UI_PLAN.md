# 04 — Kế hoạch giao diện MVP

Sáu đợt. Mỗi đợt: sửa → `test_nhanh --lf` → soi trình duyệt → chỉ khi xanh mới
sang đợt sau.

## Nguyên tắc quyết định trong công việc này

1. **Dùng lại trước khi dựng.** `.page--wide`, `.badge`, `.tablewrap`,
   `.chip`, `.row`, `.field`, `.khoi-ma` đều đã có. Bốn trong sáu nguyên nhân
   gốc là "primitive có sẵn nhưng không ai dùng", không phải "thiếu primitive".
2. **Lỗ hổng cấp nền tảng thì vá ở nền tảng; cấu trúc riêng khu API thì đặt
   trong lớp `.dev-*`.** RC-2 là loại thứ nhất (năm app đã tự vá quanh nó);
   dải lọc / thẻ khoá / trạng thái là loại thứ hai.
3. **Không thêm route, không đổi context của handler.** Mọi con số trên trang
   tiếp tục đến từ nguồn chân lý ở tài liệu 02 §F.
4. **Không `!important`, không `body{overflow-x:hidden}`, không hệ token thứ
   hai, không chép CSS vào template.**

## Quyết định bề rộng (RC-1)

Khai `{% block page_mode %}wide{% endblock %}` trong `developers_base.html` —
**dùng lại token có sẵn**, đúng thứ khu VPS đã dùng, thay vì đặt một con số
mới ở một chỗ mới.

```
                       trước    sau
main.page              1180  →  1600
.app-main (@1920)       898  →  1318   (+47 %)
```

Không dựng "dev shell" riêng, không đổi 210px của thanh bên: bản giao việc gợi
ý 240–260px, nhưng `.app-side` là **primitive dùng chung với khu VPS**
(`ltt.css:577` nói thẳng điều đó), nên đổi bề ngang là chạm cả hai khu — đúng
cái §34 bảo phải xem lại. 210px đang đủ cho nhãn dài nhất ("Cài đặt & bảo mật").

**Không** dùng bề rộng khác nhau cho trang tài liệu vs trang bảng ở MVP này:
nó thêm một trục quyết định cho mỗi trang mới mà chưa có bằng chứng nào nói
1600px làm hại trang văn xuôi (`dev_docs`, `dev_cli` vốn đã bọc `<pre>` và văn
bản trong `.card`, tự giới hạn dòng). Ghi vào **hoãn sau MVP**.

## Đợt 1 — Vỏ · bề rộng · nhịp chữ

- `developers_base.html`: khai `page_mode = wide`.
- `.dev-h1` lên 24px + một dòng dẫn (`.dev-dan`) dưới tiêu đề, để trang có
  phân cấp thay vì bắt đầu bằng một dòng chữ 20px.
- `.dev-sub` giữ nguyên hình dạng markup (test đọc nó).

**Chốt:** `.app-main` ≥ 1300px @1920 trên cả 16 trang; không trang nào tràn
ngang thêm so với mốc.

## Đợt 2 — Primitive dùng chung

**(a) Vá lỗ hổng cấp nền tảng — `_kieu_chung.html`, ~10 dòng:**

| Thêm | Vì sao an toàn |
|---|---|
| `input:not([type])`, `[type=search]`, `[type=url]`, `[type=date]` vào danh sách đã có | chỉ **mở rộng** một luật đang chạy; các ô này hiện không khớp gì cả, nên không thể "mất" kiểu nào |
| `input[type=checkbox],[type=radio]{accent-color:var(--accent);width:16px;height:16px}` | thuần thẩm mỹ, không đụng ngữ nghĩa native |
| `fieldset{border:0;padding:0;margin:0}` + `legend` | 5 lớp app hiện có (`.tv-fieldset`, `.th-group`, `.im-group`, `.clip-group`, `.clip-package fieldset`) **đều đã tự đặt `border:0`** ⇒ luật chung khớp thứ chúng đang làm |
| `.btn-ghost{border:1px solid var(--line2)}` (thêm `border-style`) | sửa đúng chỗ `border:none` của `.btn` đang nuốt viền |

**(b) Lớp semantic riêng khu API — `ltt.css`, khối `dev-*`:**

`.dev-field` / `.dev-row` (hàng form) · `.dev-loc` (dải lọc ngang, cuộn được ở
mobile) · `.dev-bang` (vỏ cuộn cho bảng — **sửa RC-3**) · `.dev-nhom` (nhóm
trường thay `fieldset` trần) · `.dev-chon` (checkbox/radio dạng chip) ·
`.dev-trong` (empty state có bước tiếp) · `.dev-ma` (khối mã) ·
`.dev-canh-bao` (khối secret hiện một lần).

**Chốt:** không control nào trên `/developers` còn `border-style:inset` hay
`groove`; 0 trường hợp tràn ngang tài liệu ở mọi khung.

## Đợt 3 — Tổng quan

Cấu trúc lưới chỉ số đã đúng; sửa **phân cấp hành động**: 5 nút đỏ đặc thành
1 chính + 4 phụ. Không thêm biểu đồ (backend không có chuỗi thời gian).

**Cổng dừng:** nếu sau đợt này Tổng quan vẫn trông thô hoặc bố cục chưa ổn thì
**dừng, quay lại nền**, không migrate hàng loạt.

## Đợt 4 — Khoá API + Hoạt động

- **Khoá**: bảng → vỏ cuộn + trạng thái bằng `.badge`; `Thu hồi` thành nút
  nguy hiểm **viền** (không đỏ đặc) + xác nhận; form tạo khoá dùng
  `.dev-nhom`/`.dev-chon` thay `fieldset` trần; khối secret-một-lần nổi bật hơn
  và nói rõ "không lấy lại được".
- **Hoạt động**: dải lọc thành một hàng; `status` thành badge có màu ngữ nghĩa;
  `request_id` mono + nút chép; empty state nói bước tiếp.

Sau đợt này chạy **hồi quy bảo mật** (tài liệu 07), không chỉ QA thị giác.

## Đợt 5 — Cắm vào công cụ · Công cụ · Chạy thử · Giá · Tài liệu

Golden Outcome A + B. Giữ nguyên mọi nội dung sinh từ hợp đồng. Việc ở đây
gần như chỉ là bọc lại: khối mã, nút chép, phân cấp bước.
Trang Giá phải nói to hơn: **đây là mô phỏng, không gọi nhà cung cấp, không trừ
credit.**

## Đợt 6 — Sử dụng · Webhook · Cài đặt · Dữ liệu · Thông báo

Đưa về cùng ngôn ngữ. Không đụng logic sản phẩm.

## Hoãn sau MVP (ghi ra để khỏi tranh luận lại)

- Bề rộng khác nhau theo loại trang (văn xuôi vs bảng).
- Biểu đồ ở Sử dụng — backend chưa có chuỗi thời gian, và nó không phục vụ
  Golden Outcome nào.
- Đổi `.app-side` 210 → 240px (chạm khu VPS, cần đo cả hai).
- Tìm kiếm trong Tài liệu.
- Gộp `dev_jobs` vào `dev_logs` thành một trang Hoạt động duy nhất — hấp dẫn,
  nhưng đụng route và `test_303` chốt cả hai đường sống riêng.
