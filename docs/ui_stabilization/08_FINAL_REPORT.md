# 08 — Báo cáo cuối: ổn định giao diện AppStudios (2026-08-26)

## Kết quả một dòng

Bốn triệu chứng trong ảnh chụp ban đầu quy về **một gốc đo được**, và sửa gốc đó
làm trang tham chiếu đi từ **6 chỗ tràn xuống 0** ở mọi viewport.

## Gốc, đo bằng trình duyệt thật trên URL công khai

```text
nut file native can ~263px
  -> `.im-two{1fr 1fr}` dat HAI cai trong panel minmax(340,430) => moi o 185px
     -> luoi thua 77px -> fieldset thua 77px -> form thua 61px
        -> `.im-controls{overflow:auto}` bien phan thua thanh THANH CUON NGANG
```

⭐ Bốn triệu chứng, một chuỗi. Sửa mắt đầu thì cả chuỗi sập.

⛔ Nhưng **đừng khái quát quá tay**: cùng file input đó ở `/taoanh/thumbnail`
rộng 368px và **vừa khít**. Mệnh đề đúng là *"native cần ~263px; khung hẹp hơn sẽ
vỡ"*, không phải *"file input luôn hỏng"*. Chỉ đo mới tách được hai mệnh đề đó.

## Trước → sau

| Trang | Trước | Sau |
|---|---|---|
| `/taoanh` @1876·1440·1280 | 6 tràn, có thanh cuộn ngang | **0** |
| `/taoanh` @390 | 1 | **0** |
| `/taoanh/thumbnail` @1440 | 5, hàng chip **1322/391** | **0** |
| `/taoclipngan` | 1, input native 371px | **0** |
| `/upscalevideo` | input native 405px | input ẩn, 0 |
| Lỗi console ứng dụng | — | **0** |

## Kiến trúc: giữ nguyên, không dựng hệ thứ hai

Audit **không** tìm thấy hai framework đánh nhau. Có một `ltt.css`, một bộ 64
token ngữ nghĩa đủ dùng, ba bundle React đóng gói riêng không rò.

⇒ Bác bỏ mọi phương án "dựng design system mới". Chúng giải quyết một vấn đề kho
này không có, và tạo đúng vấn đề đề bài cấm.

**Một primitive được chuẩn hoá**, vì đúng một cái chứng minh được là đang gây lỗi.

⭐ Và nó **không phải phát minh**: `/taovideo` đã giải xong bài này và đang chạy
production. Việc cần làm là **nâng khuôn đã có lên dùng chung**, dựng lại trên
token thay vì 6 màu cứng của bản gốc.

## Ba lần sai, và điều đáng giữ lại từ mỗi lần

1. **Sửa một nửa.** Vá `.im-controls` xong thì trang bên cạnh vẫn tràn 1322/391 —
   có **bốn** bản sao của cùng luật chip, không phải một. *Đếm hết bản sao trước
   khi sửa.*
2. **Suýt làm đẹp bằng cách phá chức năng.** `/upscalevideo` có dropzone bắt
   `dragover`/`drop` nhưng **không có handler `click`**; ẩn input mà không kiểm là
   cắt mất đường vào của người dùng bàn phím. May là trang đã có `#choosebtn` —
   *nhưng ta biết vì đã đọc, không phải vì đã đoán.*
3. **Bản vá "đã xong" mà chưa chạy.** Class ẩn bị `.clip-drop input{width:100%}`
   đè im lặng. *Bản vá đã xong và bản vá thực sự chạy trông y hệt nhau trong git
   diff.*

## Định nghĩa hoàn thành — trạng thái trung thực

| Điều kiện | |
|---|---|
| Hết tràn ngang hệ thống trên trang đại diện | ✅ đo |
| File upload thống nhất ở luồng khách cần thiết | ✅ 5/5 app Jinja |
| Không còn primitive mâu thuẫn nghiêm trọng | ✅ nút/input đã lành từ trước |
| Responsive dùng được | ✅ 768 và 390 không tràn |
| CTA không bị cắt / ra ngoài màn | ✅ 44px, trong màn ở 390 |
| Control native ngoài ý muốn | ✅ đã xử lý |
| Hành vi sản phẩm giữ nguyên | ✅ đo trên trang thật |
| Credit / job / API không regression | ✅ **không chạm dòng nào** |
| Accessibility không giảm | ✅ `label[for]` nguyên vẹn, focus dùng `--focus-ring` |
| Console không lỗi mới | ✅ 0 |
| Không dùng hack toàn cục để che gốc | ✅ `test_310` chặn `overflow-x:hidden` |
| Không tạo design system thứ hai | ✅ tái dùng 64 token có sẵn |
| Tài liệu cho người viết app mới | ✅ `02_STYLE_AUTHORITY_MAP.md` |
| Kiểm trình duyệt + mobile | ✅ 1876·1440·1280·768·390 |

### ⚠️ Điều kiện CHƯA đóng, và tôi không tuyên bố khác đi

**Cổng chất lượng đầy đủ chưa xanh trên một cây đứng yên.** Lượt gate cuối tự báo:

```text
CAY DA DOI TRONG LUC CHAY (a8f28934... -> ff5d6694...)
```

Nguyên nhân **không phải** đợt sửa này: một **phiên Claude khác** (`lttstudiosapp-b4`)
đang làm cổng developer trong **cùng cây kho**, và sửa `developers_base.html`,
`_kieu_chung.html`, `tools/qa/dev_portal_qa.js` trong lúc gate chạy.

Đã đo và đã sửa hai lỗi **thật** mà lượt đó tìm ra:

- `tools/gui/ltt.css` (bản sao phải khớp) đã trôi → chạy `tools/dong_goi_gui.py`;
- `ho_so_he_thong.txt` lạc hậu → sinh lại.

⛔ **Cố ý không commit `ho_so_he_thong.txt`**: nó là ảnh chụp *cả cây*, nên sinh
lại lúc này sẽ nhúng việc đang dở của phiên kia vào ảnh chụp của tôi. `test_177`
sẽ đỏ tới khi cây đứng yên và một bên chạy lại nó.

⇒ **Việc còn lại duy nhất:** chờ cây đứng yên, chạy `python tools/build_system_profile.py`,
rồi `python tools/gate.py` một lượt sạch.
