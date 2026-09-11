# V6 pha 08 — Nhập tệp bền vững + đường nhập ảnh

> Trạng thái: **08a XONG** (video) · **08b XONG** (ảnh/logo → mở khoá 11b)
> Commit: `ef7b3425` (08a) · `d78d1804` + `cc9b1e8d` (08b/11b)

---

## 1. 🔴 Phát hiện chính: đường tải lên 2 GiB **chưa bao giờ chạy được**

Auto Scan có hai đường nhận tệp:

| đường | tệp đi qua | trần |
|---|---|---|
| multipart | Cloudflare → tiến trình app | **90 MB** |
| bền vững | thẳng lên kho (presigned PUT) | **2 GiB** |

Đường bền vững tồn tại **chính vì** trần 90 MB — Cloudflare cắt ở 100 MB trên
đường vào máy chủ, và đường bền vững không đi qua đó.

⛔ Nhưng lúc khách **chọn** tệp, `moTep` đo kích thước với `data-tran-mb` = 90 —
   trần của đường *kia* — rồi **khoá nút Bắt đầu**.

⇒ Mọi tệp trên 90 MB bị chặn ngay ở cửa, và cả tính năng tải lên trực tiếp
  **không ai đi tới được từ giao diện**, đúng cho những tệp nó sinh ra để phục
  vụ.

Đo thật trên trình duyệt, MP4 nằm giữa hai trần:

```
trước:  nut_KHOA = true    "vượt quá 90 MB"
sau  :  nut_KHOA = false
```

⭐ Hình dạng lỗi kho đã đặt tên — *"năng lực có, không ai đi trên đường"*.
   Khác bốn ca trước ở một điểm đáng ghi: ở đây **không phải thiếu người gọi**,
   mà là một **hàng rào dùng sai con số đang chặn người gọi**.

⚠️ Và không phép kiểm nào thấy được: hai hằng số đều đúng, cả hai đường đều
   chạy, chỉ có ô đo là đo nhầm cái. Chỉ trình duyệt thấy.

## 2. Đường lui im lặng ở phía sau nó

Khi đường bền vững hỏng, bản cũ `form.submit()` **vô điều kiện** — kể cả khi
tệp lớn hơn trần multipart. Với một tệp 1,5 GB vừa PUT hỏng ở 90%:

```
đẩy lại 1,5 GB qua Cloudflare → bị cắt ở 100 MB
→ "Video vượt quá 90 MB. Hãy cắt ngắn hoặc giảm chất lượng trước."
```

⛔ Câu ấy là một lời khuyên **sai**. Tệp của khách không hề quá lớn; thứ hỏng là
   đường tải lên. Ta gửi họ đi sửa nhầm thứ, sau khi đã bắt họ chờ hai lần.

Bản mới:

| tình huống | hành vi |
|---|---|
| PUT hỏng, dưới trần multipart | lui về multipart — và **nói ra** |
| PUT hỏng, trên trần multipart | nói thật + nút **Thử tải lên lại** |
| PUT hỏng vì mạng | thử lại **cùng một vé** tối đa 3 lần |

⚠️ Nút thử lại dùng `requestSubmit`, không `submit`: `submit()` **không** phát sự
   kiện `submit`, nên nó bỏ qua chính đoạn xử lý bền vững và đẩy tệp qua đường
   multipart — đúng cái vừa từ chối.

⭐ Ba lần, không nhiều hơn: một lỗi **có hệ thống** hỏng y hệt cả ba lần, và bắt
   khách chờ ba lượt cho cùng một câu trả lời là đúng cái giá `loi.py` từ chối
   trả ở tầng job.

## 3. Hai lane nhận hai tập kiểu — nên trần phụ thuộc TỆP

```
ô chọn tệp     mp4, quicktime, x-matroska, webm
đường bền vững mp4, quicktime, x-m4v
```

Một `.mkv` 500 MB **không có đường nào**. Câu từ chối cũ (*"cắt ngắn video"*)
không giải quyết gì — cắt tới đâu cũng vẫn là `.mkv`. Câu mới chỉ đường sang
MP4/MOV.

⚠️ Chiều ngược lại được **ghi lại chứ không sửa cho khớp**: `x-m4v` có trong
   hằng số mà ô chọn không mời. Hai danh sách trả lời hai câu khác nhau — *"mời
   khách thứ gì"* và *"nhận thứ gì nếu nó tới"* — và một client tự viết vẫn gửi
   `.m4v` được.

## 4. Đường nhập ảnh (08b) — và một câu hỏi BIẾN MẤT

Logo cần một đường nhập ảnh. Thiết kế chọn: **ảnh đi cùng POST tạo lần chạy**,
không có cửa tải lên riêng.

🔑 Một cửa riêng cấp ra một **khoá** khách cầm theo, rồi lần chạy sau nhắc lại
   khoá đó — tức máy chủ phải trả lời *"khoá này có thật sự của người đang gọi
   không"* ở **mọi** lần dùng. Đó đúng là bề mặt IDOR mà
   `upload_sessions.owned(...)` phải lọc trong truy vấn để đóng lại.

⇒ Ảnh đến từ chính yêu cầu này. Câu hỏi quyền sở hữu **biến mất** thay vì được
  trả lời — và một câu hỏi không tồn tại thì không thể trả lời sai.

⭐ Đó cũng là lý do `logo.chuan_hoa_mot` có thể thuần hình học: nó không có
   `db`, không có kho, không biết ai đang gọi. Một phép kiểm quyền ở đó sẽ
   **trong veo** — nó nhìn một chuỗi và nói "có".

### Và `khoa` không bắt buộc ở đầu vào — một hợp đồng tôi đã tự sửa

Bản đầu đòi client gửi `khoa`, nên giao diện phải gửi `"se-thay-o-may-chu"` rồi
máy chủ ghi đè. ⛔ Một hợp đồng **đẩy client tới chỗ bịa dữ liệu** là một hợp
đồng sai. Khoá do máy chủ đặt sau khi `run.id` tồn tại; hình dạng của nó vẫn
được kiểm **khi có mặt** (đọc lại từ `run.settings`).

## 5. Một loại artifact mới mang một nghĩa vụ

`KIND_ANH` vào `KINDS` **kèm một nhánh trong `assets.kiem_hop_le`**.

⛔ Thêm mã mà không thêm phép kiểm là mở một loại artifact **không ai soi nội
   dung** — tức bất biến I8 (*"DONE nghĩa là có một kết quả HỢP LỆ"*) mất hiệu
   lực cho đúng loại đó, và mất im lặng.

## 6. `hinh_hoc.py` — gom hai quy tắc đang bị chép ba lần

`_so` (đọc phân số 0..1) và khối đọc `tu_giay`/`den_giay` có **ba** bản:
`vung_che`, `cat_dau_cuoi`, `lop_phu`. Bản thứ tư sẽ ra đời cùng `logo`.

⛔ Ba bản của một quy tắc là ba bản sẽ lệch **im lặng**: một bản quên chặn `NaN`
   vẫn xanh ở mọi phép kiểm của chính nó, vì `float("nan")` đọc được và **mọi**
   phép so sánh với nó đều False.

⚠️ `vung_che`/`cat_dau_cuoi` **chưa** chuyển — mã V5 đang chạy, và một lần di
   trú phải đi cùng đối chứng của chính nó. Còn **hai** bản chép, và chúng được
   **ghi tên** trong `REBASE_MAP_V4.md` để là một món nợ chứ không phải một sự
   trùng lặp không ai để ý.

## 7. Bằng chứng engine cho logo (FFV1, không mất mát)

```
t=1,0s NGOÀI   inf        t=3,0s TRONG   19,74 dB     t=5,0s NGOÀI   inf
đường chéo     13,23 dB
bề rộng px = 128  (đúng 20% của khung 640)
```

## 8. Bốn phép tiêm cho 08a, cả bốn làm bộ kiểm ĐỎ

```
A  moTep đo bằng trần multipart      ĐỎ
B  đường lui vô điều kiện            ĐỎ
C  thử lại không có trần             ĐỎ
D  thử lại xin vé mới                ĐỎ
```

## 9. Ba lỗi của chính tôi trong pha này

1. **Hai bài kiểm sai, không phải mã sai.** `test_soi_TRUOC_khi_promote` so vị
   trí hai **chuỗi** trong `getsource(...)` và đỏ trên mã đúng — docstring nhắc
   `kho.promote()` trước lời gọi `soi` thật. Viết lại bằng AST: *grep khớp cách
   người ta VIẾT, AST khớp cái người ta LÀM.*
2. **Một `zip` không `strict`** trong `_gan_logo_vao_run` — ở đúng chỗ tôi vừa
   viết một bài kiểm **cấm** việc ấy. `ruff B905` bắt được. ⭐ Một bộ lint đọc
   **cú pháp** thấy được thứ một bài kiểm đọc **hành vi** bỏ sót.
3. **Commit `d78d1804` khai một việc nó không làm** — nói đã chuyển `logo_image`
   khỏi `HAU_MVP` trong khi `hop_dong_v4.py` không nằm trong danh sách tệp. Đã
   đính chính ở `cc9b1e8d`, và bài kiểm được viết lại để chốt **cả hai vế** (có
   mặt ở bảng mới **và** vắng mặt ở bảng cũ) — bản cũ chỉ chốt một vế, và đó là
   lý do nó vẫn xanh trong khi lỗ khai kia đang mở.

## 10. Còn nợ của pha 08

| Mục | Ghi chú |
|---|---|
| **Resume thật** (tải tiếp từ byte đã gửi) | Hiện là *thử lại cả tệp* 3 lần. Resume thật cần multipart upload của R2 và một bản ghi tiến độ — một pha riêng |
| `vung_che`/`cat_dau_cuoi` chưa dùng `hinh_hoc` | Hai bản chép còn lại, đã ghi tên |
| Xem trước logo trên khung hình | Khách đặt toạ độ bằng số; `vung_che` kéo thả được, logo thì chưa |
