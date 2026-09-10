# PHA 06 — Kiến trúc frontend của màn Studio

> `server/static/asv.js` — **1.154 dòng, một IIFE** — thành **tám module** dưới
> `server/static/asv/`. Nhánh `phien/asv-v6`.
>
> ⛔ Pha 06 là một pha **nền** bị bỏ qua: 08–12 đã xây lên trên nó. Nên đây
> không phải dọn dẹp cho đẹp, mà là trả một khoản nợ mà năm pha sau đã vay.

## 1. Ranh giới cắt, và vì sao cắt ở đó

| module | dòng | sở hữu |
|---|---|---|
| `asv/nen.js` | 150 | vỏ: `t()`, `chu()`, `phutGiay()`, `pt()`, hai chỗ nối, `hopPreset()` |
| `asv/xem_truoc.js` | 113 | chọn tệp · khung hình · ước giá `/uoc-tinh` |
| `asv/giong.js` | 112 | luật `required` · lọc · nghe thử |
| `asv/vung.js` | 237 | vẽ vùng che + danh sách + khoảng thời gian |
| `asv/cat.js` | 96 | cắt đầu/cuối (giây → phân số) |
| `asv/lop_phu.js` | 193 | lớp phủ chữ |
| `asv/logo.js` | 172 | logo ảnh |
| `asv/tai_len.js` | 229 | tải lên bền vững + `submit` |

Ranh giới là **khối trên màn hình**, không phải tầng kỹ thuật. Một người sửa ô
"lớp phủ" mở đúng một tệp.

## 2. 🔑 Một nguồn cho ba nơi từng có thể trôi khỏi nhau

`server/templating.py:ASV_STUDIO_JS` là danh sách duy nhất, và **ba** thứ đọc nó:

```
· thứ tự thẻ <script> mà asv_trang_chinh.html phát ra
· tập tệp được băm vào asset_ver          (cache-bust, quy tắc 6 CLAUDE.md)
· tập tệp mà test_468 + tests/asv_js.py đọc
```

⛔ Trước đó ba nơi ấy là ba danh sách chép tay. Thêm một module mà quên một
trong ba là một lỗi **im lặng**: tệp vẫn được phục vụ, chỉ là `?v=` không đổi
khi nội dung đổi — khách nhận bản CŨ từ Cloudflare tới hết TTL.

⭐ `test_468::test_KHONG_co_module_mo_coi_trong_thu_muc` chốt chiều ngược lại:
một tệp `.js` nằm trong thư mục mà **không** ai nạp thì tính năng của nó đơn
giản là không tồn tại, và mã nguồn vẫn nằm đó trông như đang chạy.

## 3. 🔑 Một ràng buộc thứ tự bị **xoá**, không phải bị chép sang chỗ khác

Trước pha 06:

```js
// ⚠️ `batCat` TRUOC `veLai`: no dat `thoiLuongVideo`, va danh sach vung
//    doc bien do de dat `max` cho hai o gio.
batCat(giay);
veLai();
```

Một chú thích giữ được thứ tự **chừng nào hai dòng còn nằm cạnh nhau trong một
tệp**. Tách ra tám tệp thì nó không giữ được gì nữa.

⇒ Luật đổi chỗ: `ASV.phatCoVideo(giay)` đặt `ASV.thoiLuongVideo` **trước khi gọi
bất kỳ người đăng ký nào**. Sau đổi này thứ tự đăng ký không còn ý nghĩa — tức
ràng buộc **biến mất** thay vì được chép sang một chú thích mới.

Đo trên trình duyệt: một người đăng ký chèn thêm đọc được `120` ngay tại lượt
gọi, và hai ô cắt nhận `max="120"`, `placeholder="120.0"`.

## 4. Bốn bản sao của một phép hỏi gom làm một

Bốn khối điều khiển từng chép **nguyên** ba dòng đọc `data-preset-can`. Nay tất
cả hỏi `ASV.hopPreset(nhom)`. `test_468` chốt cả hai chiều: không module nào còn
tự đọc thuộc tính đó, **và** ít nhất bốn module gọi hàm chung.

## 5. Bánh cóc chống mọc lại

`TRAN_DONG = 320`. Module lớn nhất hiện 237 dòng.

⛔ Thiếu nó thì "tách làm tám tệp" chỉ là một trạng thái nhất thời: một pha sau
thêm 200 dòng, pha nữa thêm 300, và sau năm pha ta có lại đúng một tệp phình —
chỉ là nó không còn tên `asv.js`.

Bốn đối chứng đã tiêm, **cả bốn đỏ đúng chỗ**:

| tiêm | bài đỏ |
|---|---|
| thêm một module không ai nạp | `test_KHONG_co_module_mo_coi_trong_thu_muc` |
| một module phình vượt 320 dòng | `test_KHONG_module_nao_vuot_tran_dong` |
| đảo thứ tự, `nen.js` không còn đầu | `test_nen_js_nap_TRUOC_moi_module_khac` |
| gỡ phép nối cache-bust | `test_moi_module_deu_duoc_CACHE_BUST` |

## 6. 🔴 Kiểm trình duyệt bắt một lỗi mà không phép kiểm nào thấy

**Lần thứ năm trong kho này** việc mở trình duyệt bắt được thứ bộ kiểm mù.

Ba phần tử mang `hidden` mà **vẫn render** trên màn Studio:

```
#asv-tai      <- .asv-tai{display:flex}       khoi tien do tai len
#asv-tai-lai  <- .btn{display:inline-flex}    nut "Thu tai len lai"
#asv-lop      <- svg lop ve vung che
```

⇒ Khách mở trang là thấy ngay một nút **"Thử tải lên lại"** — một nút giải thích
một sự cố chưa hề xảy ra — cộng một thanh tiến độ rỗng.

Markup **đúng** (`hidden` có thật), JS **đúng** (không ai bật nó hiện), chỉ CSS
lật ngược ý định: `hidden` là thuộc tính ở bảng kiểu của **trình duyệt**, nên
bất kỳ luật `display` nào của ta cũng đè bẹp nó.

### ⭐ Và bẫy này đã có người dính, đã rút ra đúng bài học, rồi vẫn tái diễn

Chú thích của màn Voice trong `ltt.css` viết nguyên văn:

> *"Ban đầu ở đây liệt kê bốn lớp cụ thể. Đó là sửa TỪNG CA thay vì sửa CẢ LỚP
> LỖI — và nó tái diễn trong vòng một giờ, ở nút 'Tải cả lô (ZIP)' (`.btn` có
> `display:inline-flex`), với đúng triệu chứng cũ. Một danh sách chỉ bảo vệ
> những gì đã từng hỏng."*

Tôi vừa gặp lại **đúng triệu chứng đó, ở đúng `.btn`**, trên một màn khác. Trong
`ltt.css` hiện có **sáu** bản vá một-phía cho cùng lỗi này: `.market-card`,
`.market-empty`, `.up-job`, `.clip-source-summary`, `#stopbtn/#sendbtn`,
`.vps-the`.

### Bản vá, và vì sao nó KHÔNG toàn cục

```css
.asv-trang [hidden],
.asv-trang[hidden]{display:none!important}
```

Một luật **chung cho cả màn**, không phải một danh sách lớp — đúng hình dạng mà
màn Voice đã rút ra. Phạm vi giới hạn trong `.asv-trang` vì chú thích của họ nói
rõ họ giới hạn trong `.lv-man` *"để không đổi hành vi của app khác"*.

⛔ Một dòng `[hidden]{display:none!important}` toàn cục sẽ gỡ cả sáu bản vá kia
cùng lúc và là việc **đúng** về kỹ thuật — nhưng nó đổi hành vi render của mọi
app của mọi phiên, và đó không phải việc của một pha ASV. Ghi lại thành một phát
hiện cho chủ `ltt.css`, không tự quyết ở đây.

Đo sau khi vá: **10 phần tử `hidden`, 0 còn render**, ở cả 1280 lẫn 375.

## 7. Bằng chứng trình duyệt

Máy chủ cách ly `tools/asv_browser_server.py` (:8199), tài khoản
`asv-ui@example.com`.

```
8/8 module nap 200 OK, dung thu tu, cung ?v=          console: 0 loi
doi preset -> ca BON khoi doi trang thai tu MOT su kien
phatCoVideo(120) -> hai o cat mo, max=120, ph=120.0
them lop phu + go chu -> o an: [{"chu":"Xin chao","x":0.08,"y":0.8,
                                 "co_chu":0.06,"mau":"trang","vien":true}]
them logo -> mot <input type=file name=logo_anh> rieng cho hang do
cat 12s..60s / video 120s -> o an: [0.1,0.5]        <- PHAN SO, khong phai giay
375px: khong tran ngang; hang lop phu 113px x4 xuong dong 2x2
```

## 8. Còn nợ

| mục | vì sao chưa đóng |
|---|---|
| Sáu bản vá `[hidden]` một-phía trong `ltt.css` | Gỡ chúng bằng một luật toàn cục là việc của chủ `ltt.css`, không phải của pha ASV |
| `routes.py` 855/900 dòng | Pha 06 chỉ chạm frontend. Trần 900 dòng / 30 handler của `lint_app_contract` còn cách 45 dòng — pha sau thêm route sẽ chạm |
| Không có bộ chạy test cho JS | Mọi phép kiểm phía client hiện là **đọc văn bản** ma nguồn. Chúng chốt được *"mã có nói X"*, không chốt được *"mã làm X"*. Cái sau hiện chỉ trình duyệt trả lời được, và trình duyệt thì chạy bằng tay |
