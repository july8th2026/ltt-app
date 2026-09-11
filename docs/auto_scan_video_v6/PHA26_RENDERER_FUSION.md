# Pha 26 — Renderer fusion + performance

**Trạng thái: XONG.** Ngày 11/09/2026. Không đổi dòng mã sản phẩm nào — pha này
**đo** rồi **chốt**.

Đề bài: *một lần encode cho mọi biến đổi điểm ảnh · giữ stream-copy · benchmark
NVENC/QSV/AMF/x264.*

---

## 1. "Một lần encode" đã được các pha trước làm dần — chưa ai chốt khi CẢ BỐN cùng bật

Mỗi biến đổi điểm ảnh đã có bài riêng: `test_457` vùng che, `test_466` lớp phủ +
logo, `test_471` phụ đề. Nhưng mỗi bài kiểm **một mình nó**. Không bài nào hỏi
điều gì xảy ra khi cả bốn cùng có mặt — và một lần sửa sau thêm một lượt ffmpeg
thứ hai cho một biến đổi (cách đọc tự nhiên nhất của `autosubvideo/burn.py`) sẽ
xanh ở cả bốn bài riêng trong khi video bị mã hoá lại **hai** lần.

Đo trên **ffmpeg thật**, bản dựng bật cả bốn, qua đúng các hàm chuẩn hoá của sản
phẩm:

```
[0:v]trim…[v0] ; [v0]concat…[noi] ; [noi]split[c0][g0]
[c0]crop…,boxblur…[m0] ; [g0][m0]overlay…[sau_che]          ← vùng che
[2:v]scale…,colorchannelmixer…[lg0] ; [sau_che][lg0]overlay…[sau_logo]   ← logo
[sau_logo]drawtext…[sau_chu]                                  ← lớp phủ chữ
[sau_chu]ass='…'[ra]                                          ← phụ đề (CUỐI)
```

**1** `-filter_complex` · **1** `-c:v` · **1** tệp ra · `returncode 0`.

`test_474` chốt mệnh đề đó bằng khẳng định **dương**: mỗi mắt xích phải **có mặt**
trong chuỗi lọc duy nhất, không chỉ "không quá một `-c:v`" — một bài đếm sẽ xanh
khi ai đó lặng lẽ bỏ một biến đổi đi.

⚠️ **Đối chứng của chính bài kiểm bắt một lỗi trong nó.** Bản đầu đánh dấu logo
bằng `overlay`. Nhưng vùng che **cũng** dùng `overlay` để dán mảng làm mờ trở lại
(`[g0][m0]overlay`), nên bỏ logo đi mà `overlay` vẫn còn. Nhãn luồng `[lg0]` mới
là dấu hiệu riêng của logo.

---

## 2. Benchmark bốn bộ mã hoá — và câu hỏi thật không phải "cái nào nhanh nhất"

`che_do_render.THAM_SO` dùng **bốn núm chất lượng khác nhau**: NVENC `-cq 28`, QSV
`-global_quality 28`, AMF `-qp_i 28`, x264 `-crf 23`. Bốn con số trên bốn thang đo
khác nhau. Nếu chúng không tương đương, khách nhận chất lượng khác nhau **tuỳ máy
có GPU hay không** — một lùi-về-im-lặng.

**Ngưỡng ghi TRƯỚC khi đọc kết quả** (nằm trong chính tệp bằng chứng):
|ΔSSIM| ≤ 0,010 và kích thước ∈ [0,5× ; 2,0×] so với libx264. Nguồn **FFV1 không
mất mát** (`bo-ma-hoa-mat-mat-lam-ban-phep-do-tung-diem-anh`), đi qua chính
`ket_xuat.dung_lenh`.

| bộ | 720p tốc độ | SSIM | kích thước | so libx264 |
|---|---|---|---|---|
| **h264_nvenc** | **21,7×** | 0,97500 | ×1,07 | tương đương (Δ 0,00036) |
| libx264 | 14,3× | 0,97536 | — | — |
| h264_qsv | 7,9× | 0,97341 | ×0,78 | tương đương (Δ 0,00195) |
| h264_amf | không chạy trên máy này | | | |

⇒ Bốn núm **tương đương** trên máy này. Không có lùi-về-im-lặng về chất lượng.

## 3. Thứ tự ưu tiên: đo cả CPU, không chỉ tốc độ

Tốc độ là đại lượng đề bài **đặt tên**; CPU là thứ các job khác phải **chờ** trên
một máy production (`do-dai-luong-de-bai-dat-ten-thay-vi-dai-luong-khach-phai-cho`).
Đo bằng `ffmpeg -benchmark`, luật quyết định ghi trước:

| 1080p | thời gian | giây CPU | ≈ lõi bận | thời gian / x264 | CPU / x264 |
|---|---|---|---|---|---|
| **h264_nvenc** | 1,53 s | 5,50 | 3,6 | **0,67** | **0,21** |
| h264_qsv | 4,63 s | 10,94 | 2,4 | 2,03 | 0,43 |
| libx264 | 2,28 s | 25,61 | **11,2** | — | — |

⇒ **Luật A: giữ "phần cứng trước".** NVENC vừa nhanh hơn vừa tốn 1/5 CPU.

🔴 **Con số đáng ghi nhất nằm ở đường lùi:** libx264 ăn **~11 lõi** ở 1080p — cả máy
production 10 lõi vật lý. Một lần render lùi về CPU làm chậm mọi dịch vụ khác đang
phục vụ khách.

⚠️ **Phép đo bị dời vì một lỗi của chính nó:** `dung_lenh` đặt `-loglevel error`,
mà dòng `bench:` in ở mức info — lượt đầu trả **rỗng** cho mọi bộ, trông y hệt
render hỏng. Chỉ nâng mức log trong **bản sao lệnh** của phép đo.

## 4. Một chế độ hỏng có thật, đo được trước khi khởi động lại máy

Trước khi chủ máy khởi động lại và rút bớt một card 5060 Ti, driver NVIDIA không
phản hồi (`nvidia-smi` lỗi). Khi đó NVENC **không chạy**, và
`detect_gpu_encoder()` lùi về **QSV** — bộ **chậm hơn cả libx264** (2,03× thời gian
ở 1080p), dù chỉ tốn 0,43× CPU. Lượt đo đó được **thay** bằng lượt sau khởi động
lại, không được dùng làm kết luận; nhưng chế độ hỏng thì có thật: *driver rơi ⇒ máy
chọn bộ chậm nhất còn lại.*

## 5. Bằng chứng

* `tests/test_474_asv_v6_mot_lan_ma_hoa.py` — **10 bài**.
* Đối chứng: bỏ mắt xích `ass=` → **đỏ** (2 bài); đặt libx264 lên đầu `UU_TIEN` →
  **đỏ** (1 bài). `che_do_render.py` trả lại nguyên vẹn.
* `bang_chung/bo_ma_hoa_20260911.json` — chất lượng, tốc độ, giá CPU 720p/1080p,
  luật ghi trước, phán quyết, và kết quả một-lần-encode trên ffmpeg thật.

## 6. Còn nợ

* **Tài nguyên khai cho đường CPU.** libx264 dùng ~11 lõi nhưng `dung_gpu(LUI_VE)`
  là `False` và job render không khai số lõi — nền tảng không biết một render lùi
  về CPU sẽ chiếm cả máy (`khoa-khai-thieu-tai-nguyen`).
* **QSV làm đường lùi thứ hai** khi NVENC rơi: chậm hơn libx264 nhưng rẻ CPU hơn —
  một đánh đổi chưa có luật. Cần một quyết định chính sách, không phải một hằng số.
* Benchmark mới đo nguồn tổng hợp 720p/1080p; 4K và nguồn thật chưa đo.
