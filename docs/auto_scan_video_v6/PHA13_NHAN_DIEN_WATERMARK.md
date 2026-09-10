# PHA 13 — Nhận diện watermark/logo, và cái cổng không ai ngờ sẽ hỏng

> `tools/do_watermark.py` · `tests/test_470_asv_v6_watermark.py`. Nhánh `phien/asv-v6`.

## 0. Kết luận trước, số sau

Đề bài: *"Auto-detect watermark/logo; benchmark CPU/GPU; remove/inpaint **chỉ
bật nếu quality/resource gate đạt**."*

| cổng | phán quyết | vì sao |
|---|---|---|
| **tài nguyên** | ✅ **ĐẠT** | `delogo` tốn **8,9e-5 s/khung** → video 30 phút mất **4,8 s** trên ngân sách **540 s** |
| **chất lượng** | ⛔ **KHÔNG ĐẠT** | bộ dò không tìm *watermark*, nó tìm **vùng TĨNH** — và vùng tĩnh bao gồm cả nội dung |

⇒ **`remove`/`inpaint` để TẮT.** Không phải vì đắt — nó rẻ hơn dự đoán một bậc —
mà vì **không chỉ đúng được chỗ cần xoá**.

🔑 Đó là kết quả đáng giá nhất của pha này. Trước khi đo, cổng ai cũng nghĩ sẽ
chặn là **tài nguyên**: `CHAN_DOAN_TEST_448.md` §10 đã ghi trần job 60 phút nằm
dưới sàn nhu cầu, nên thêm một lượt sửa từng khung nghe như chắc chắn vỡ ngân
sách. Đo ra thì ngược lại. Cái chặn là **chất lượng nhận diện** — thứ không ai
đặt câu hỏi.

## 1. Ba trục đã thử, ba phép đo

Chân lý nền: video 720p/30fps dựng bằng `lavfi`, watermark `drawtext
white@0.55` ở góc trên phải (x 0,766–0,961 · y 0,056–0,136). Không tệp nào có
bản quyền.

### Trục 1 — phương sai theo THỜI GIAN (`on_dinh` thấp)

Giả định: watermark **đứng im**. Đúng cho dấu **đục**.

```
canh dong + logo duc (mang tong hop, chan ly nen day du)   -> 1 dau, dung cho
canh dong khong dau                                        -> 0 dau
letterbox (hai thanh den)                                  -> 0 dau  (rao ②)
canh von di tinh                                           -> TU CHOI canh_tinh
canh toi it tuong phan                                     -> TU CHOI tuong_phan_thap
```

⛔ Nhưng **mù với dấu bán trong suốt** — mà đó mới là dạng phổ biến, vì điểm của
watermark là không che mất nội dung. Đo trên ba nguồn động thật:

| nguồn | `on_dinh` trong hộp / trung vị khung |
|---|---|
| mandelbrot | **1,46** |
| life | **0,92** |
| smptebars+xoay | **1,24** |
| | *bộ dò cần **< 0,35** mới bắt được* |

Điểm ảnh lớp phủ là `0,55·trắng + 0,45·nền`: biên độ bị nén còn 45%, nhưng nếu
vùng nền vốn đã động **hơn** trung vị thì 45% của một số lớn vẫn lớn hơn trung
vị. Tín hiệu bị chính nội dung bên dưới nhấn chìm.

⚠️ Cả ba nguồn đều `do_duoc=True` và đều trả **0 dấu** — một **âm tính giả im
lặng**, dạng tệ nhất.

### Trục 2 — độ dốc của ẢNH TRUNG BÌNH

Nền chuyển động trung bình hoá về một mảng mượt; lớp phủ tĩnh sống sót nguyên
biên. Đo trước khi dựng (độ dốc trong hộp / trung vị khung): **5,80 · 1,84 ·
10,35 · 23,67** — tín hiệu rõ.

Dựng xong thì nó **tìm được** watermark ở cả ba nguồn. Nhưng:

```
mandelbrot       2 dau — mot hop 125 o phu gan het khung
life             2 dau — dung cho nhung vo manh
smptebars+xoay   17 dau
```

⛔ Một bộ dò đề nghị **17 vùng che sai** còn tệ hơn một bộ dò không tìm thấy gì.
Vùng che là năng lực **đổi điểm ảnh**: một đề nghị sai không phiền hà, nó **phá
hình** của khách vĩnh viễn trong tệp ra.

### Trục 3 — biên có ĐỨNG YÊN không

`doc(mean_t) / mean_t(doc)`. Biên đứng yên → tỉ số → 1; biên di chuyển → → 0.
Dùng để lọc bớt dương tính giả của trục 2. **Không tách được:**

```
                trong hop   trung vi   cach biet   p90 khung
mandelbrot          0,867      0,620        1,40       0,825
life                0,763      0,725        1,05       0,918
smptebars+xoay      0,973      0,946        1,03       1,000
testsrc2            0,987      0,813        1,21       1,000
```

Một phần mười khung hình đã nằm ngang mức của chính cái dấu ta muốn tìm.

⇒ Trục 2 **đã gỡ** khỏi đường phán quyết. Hằng số `TI_LE_DOC_TOI_THIEU` và toàn
bộ số đo **giữ lại** trong chú thích: người đọc sau sẽ có cùng ý tưởng ấy — nó
là ý tưởng tự nhiên nhất — và xoá dấu vết là mời họ đi lại đúng ba vòng đo này.

### Và giới hạn cuối cùng của trục 1, đo được sau khi trải đều mẫu

```
life (co vung noi dung tinh lau)  ->  10 dau, KHONG dau nao o cho watermark
```

Trục 1 không tìm *watermark*, nó tìm **vùng tĩnh**. Trong phim thật, vùng tĩnh
gồm cả logo đài, bảng tỉ số, viền đen, và nền của một cú máy cố định.

## 2. 🔴 Một khiếm khuyết im lặng trong chính bộ lấy mẫu

Bản đầu dùng `-skip_frame nokey ... -frames:v 12`. `-frames:v` làm ffmpeg **dừng
ngay khi đủ 12 khung ra** — với `g=60` ở 30fps đó là 12 khung khoá đầu tiên, tức
toàn bộ mẫu đến từ **~24 giây đầu**.

⇒ Một watermark xuất hiện từ phút thứ 5 **không bao giờ được nhìn thấy**; một
video mở đầu bằng thẻ tiêu đề tĩnh làm rào ① bắn nhầm.

⚠️ Và nó **trông như đang chạy đúng**: 12 khung, 0,171 giây, kết quả hợp lý.

**Bản sửa:** N lần `-ss <t> -i <tệp> -frames:v 1`, mốc trải đều và tránh hai đầu
mút (khung đầu hay là thẻ tiêu đề, khung cuối hay là màn hình đen).

⭐ `-ss` **trước** `-i` là tìm-đến-đầu-vào: chi phí là một hằng số, **không phụ
thuộc thời lượng**. Đặt sau `-i` thì ffmpeg giải mã từ đầu tệp rồi vứt — cùng
một cờ, hai bên của `-i`, hai hạng độ phức tạp, và không lỗi nào báo ra.

Giá phải trả, đo được: 0,171 s → **1,1–1,5 s** (12 lần khởi tạo tiến trình thay
vì một). Một đánh đổi có số.

## 3. Số đo engine

```
dung nguon 60s 720p                        3,79 s
lay khung — duong khung khoa               0,171 s   (12 khung)
lay khung — duong day du (fps=)            0,516 s
                                           -> khung khoa nhanh gap 3,02x
encode 60s KHONG delogo                    2,99 s
encode 60s CO delogo                       3,15 s
                                           -> bien 0,16 s / 1.800 khung
                                           -> 8,9e-5 s/khung
cong_xoa cho video 30 phut (54.000 khung)  uoc 4,8 s / tran 540 s -> MO
```

⚠️ `giay_bien_delogo = 0,16 s` nằm trong nhiễu của một lượt đo đơn (n=1). Kết
luận **"delogo là một phần nhỏ của một lượt encode vốn đã xảy ra"** thì vững;
con số chính xác thì không. Ai cần độ chính xác hơn thì chạy nhiều lượt.

⛔ Và `delogo` chỉ tồn tại được ở preset **cắt/mã hoá lại**. Ở
`localize_preserve_picture` (`-c:v copy`) không khung nào được giải mã — cùng
ràng buộc **vật lý** với `vung_che`, không phải một chính sách ta chọn.

## 4. Vì sao module nằm ở `tools/` chứ không ở `apps/`

`test_453` bắt `watermark` là **năng lực mồ côi** — đúng. Có hai cách làm nó
xanh, và chỉ một cách trung thực:

| | |
|---|---|
| ⓐ nối vào `media_prepare` cho có người gọi | **sai** — đó là bật một tính năng mà cổng chất lượng vừa từ chối, và bày cho khách những vùng che sai |
| ⓑ **phân loại lại** | đây không phải năng lực sản phẩm, đây là **công cụ đo đã tạo ra một quyết định** |

⭐ Và phép phân loại ấy có hệ quả thật: `tools/` không vào hợp đồng app, không
lên đường ống, không tốn một giây nào của khách. Nếu sau này có ai tìm ra bộ dò
tách được lớp phủ bán trong suốt, việc chuyển ngược lại là một **quyết định có ý
thức**, không phải một dòng import.

## 5. Bánh cóc

`test_470` — 22 bài. Ba bài đáng chú ý vì chúng chốt **kết quả âm**:

- `test_duong_phan_quyet_CHI_dung_truc_mot` — ai muốn mở lại trục 2 phải **xoá**
  bài này, và để xoá được thì phải đọc ba con số ở docstring của nó.
- `test_hang_so_cua_truc_2_van_CON_va_van_mang_so_do` — nửa đối chứng: xoá sạch
  hằng số + số đo sẽ làm bài trên xanh.
- `test_dau_BAN_TRONG_SUOT_tren_nen_dong_la_gioi_han_DA_BIET` — cấy một lớp phủ
  `0,55·trắng + 0,45·nền` và chốt rằng bộ dò **không** bắt được. Bài này sẽ **đỏ**
  nếu ai đó làm nó bắt được mà quên cập nhật tài liệu phạm vi — và đó là một cái
  đỏ **đúng**.

## 6. Còn nợ

| mục | vì sao chưa đóng |
|---|---|
| Nhận diện lớp phủ **bán trong suốt** | Ba thống kê rẻ tiền đều không tách được. Đường tiếp theo là học máy (một mô hình phát hiện logo), tức một phụ thuộc mới và một khoản chi GPU — phải đi qua chính cổng tài nguyên của pha này |
| Phân biệt **watermark** với **nội dung tĩnh** | Trục 1 không phân biệt được. Một tiên nghiệm miền (dấu nằm ở góc, chiếm phần nhỏ) sẽ lọc được, nhưng nó **hiệu chỉnh trên bốn nguồn tổng hợp** — chưa đủ để đưa vào sản phẩm |
| `8,9e-5 s/khung` là n=1 | Đủ để trả lời câu hỏi của pha (rẻ hay đắt), không đủ để làm một hằng số ngân sách |
| Ngưỡng hiệu chỉnh trên nguồn **tổng hợp** | `lavfi` không có nhiễu nén thật của phim quay. Trước khi bật bất cứ thứ gì cho khách, phải đo lại trên nội dung thật |
