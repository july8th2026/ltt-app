# 06 — Nhật ký thi hành

| Commit | Nội dung |
|---|---|
| `2aee53b` | Batch 1+2 — primitive `.ltt-file` + macro + `chon_tep.js`; `overflow-y` cho 3 panel; di trú `/taoanh` |
| `31d8df2` | Batch 3+4 — chip xuống dòng; ẩn input native ở `/upscalevideo`, `/taoclipngan` |
| `eb554de` | Sửa độ ưu tiên CSS — tiện ích ẩn phải thắng; gỡ luật đang tranh chấp |

## Tệp đã chạm

```
server/static/ltt.css              + primitive, + tien ich, 4 luat chip, 3 luat panel, -1 luat chet
server/static/chon_tep.js          MOI
server/templates/_o_chon_tep.html  MOI (macro)
server/templating.py               +1 muc cache-bust
apps/taoanh/templates/image.html   2 o upload -> macro
apps/upscalevideo/.../*.html       +1 class
apps/taoclipngan/.../*.html        +1 class
tests/test_310_o_chon_tep.py       MOI, 12 phep kiem
```

**Phạm vi:** 8 tệp, 4 app, 0 thay đổi backend/API/job/credit/route.

## Ba lần sai trong đợt này, và điều mỗi lần dạy

### 1. Bản vá đầu chỉ sửa được một nửa cái nó nhắm tới

Sửa `.im-controls` xong thì `.th-chips` vẫn tràn 1322/391 ở trang bên cạnh. Đo
mới thấy **bốn** bản sao của cùng một luật chip, không phải một.

⇒ Khi tìm thấy một luật bị sao chép, **đếm cho hết bản sao trước khi sửa**.

### 2. Suýt làm đẹp giao diện bằng cách phá chức năng

`/upscalevideo` có `<div class="up-drop">` bắt `dragover`/`drop` — nhìn qua tưởng
là dropzone đầy đủ. Nó **không có handler `click`**. Ẩn input mà không kiểm thì
trang chỉ còn kéo-thả và người dùng bàn phím mất hẳn đường vào.

Hoá ra trang đã có `#choosebtn` gọi `input.click()`, nên ẩn được — **nhưng ta
biết vì đã đọc, không phải vì đã đoán.**

⇒ `test_310::test_moi_input_bi_AN_deu_con_MOT_CHO_BAM` chốt lại vĩnh viễn.

### 3. Bản sửa "đã xong" mà thực tế chưa chạy

Gắn `.ltt-input-tep-an` cho `/taoclipngan` xong, đo lại: input **vẫn rộng 1425px**.
`.clip-drop input{width:100%}` (0,1,1) đè lên tiện ích (0,1,0), **im lặng**.

⭐ Đây là lý do không được kết luận UI PASS từ mã nguồn. Bản vá *"đã xong"* và bản
vá *"thực sự chạy"* trông **y hệt nhau trong git diff**.

## Việc cố ý KHÔNG làm

- **Không** `overflow-x:hidden` ở đâu cả — che lỗi không phải sửa lỗi.
- **Không** quét 316 màu cứng — regression lớn, cải thiện vô hình. Chỉ ràng buộc
  *cái mới* phải sạch.
- **Không** đụng breakpoint — đo cho thấy responsive đang đúng.
- **Không** dựng `FileDropzone` — đúng một nơi gọi Jinja.
- **Không** đổi backend, API, job, credit, route.
