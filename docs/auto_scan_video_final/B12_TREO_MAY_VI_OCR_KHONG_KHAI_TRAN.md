# B12 — Treo máy vì một hộ tiêu thụ CPU ⛔ không khai trần

**Ngày:** 2026-09-28 · **Sự cố:** máy treo **hai lần** trong một buổi chiều.
**Thủ phạm:** `rapidocr-onnxruntime` tôi thêm ở B10-4 cùng ngày.

---

## 1. Bằng chứng — hộp đen, ⛔ không suy luận

```
12:37:26 -> 12:59:43   TRỐNG 22,3 phút · cpu 99 % · 577 tiến trình · RAM trống 21,0 GiB
13:12:56 -> 13:21:19   TRỐNG  8,4 phút · cpu 91 % · 338 tiến trình · RAM trống 38,1 GiB

cả hai lần, tiến trình dẫn đầu:  `-c inline` **1075 %** và **1164 %**
```

🔑 **Khoảng TRỐNG mới là dấu vết của treo máy, ⛔ không phải CPU cao.** Bộ giám
sát lấy mẫu mỗi 17 giây mà im **22 phút** — nó ⛔ không còn được xếp lịch CPU.

⚠️ Mọi giai đoạn `CPU ≥ 85 %` hôm nay đều **cực ngắn** (phần lớn **một** mẫu 15
giây, dài nhất 2 phút). Nhìn riêng cột CPU thì ⛔ **không** thấy gì bất thường.
⇒ Hai đại lượng khác nhau: **CPU cao** nói máy *bận*; **khoảng trống** nói máy
*⛔ không chạy nổi cả bộ giám sát*. Chủ dự án hỏi cái thứ hai.

## 2. Nguyên nhân, đo trên chính máy này

```
RapidOCR mặc định  ->  67 luồng · **1519 % = 15,2 LÕI / 20** · 1,2 giây
```

`onnxruntime` đặt `intra_op_num_threads = 0` = **tự chọn = số lõi vật lý**, và
`rapidocr_onnxruntime.utils.OrtInferSession` dựng `SessionOptions()` mà ⛔
**không bao giờ** đặt lại — thư viện cũng ⛔ không nhận tham số đó.

## 3. ⛔ Cần gạt hiển nhiên nhất KHÔNG ăn

| cách | lõi | thời gian |
|---|---|---|
| mặc định | **15,2** | 1,2 s |
| `OMP_NUM_THREADS = 4` | **12,9** | 1,4 s |
| `cpu_affinity([0..3])` | **4,2** | 7,3 s |

Bản `onnxruntime` này ⛔ không dựng theo OpenMP. ⭐ Chỉ phép chặn lõi ở tầng
**hệ điều hành** mới cưỡng chế được — cùng lý lẽ với *"chỉ giết thứ mình khởi
động"*: luật do OS thi hành, ⛔ không phải do ta nhớ.

⇒ **Đo cần gạt trước khi tin nó.** Một cần gạt mang đúng tên việc ta muốn
(`OMP_NUM_THREADS`) vẫn có thể ⛔ không nối vào đâu cả.

## 4. Chuỗi nhân quả đầy đủ — ba mắt xích, ⛔ không phải một

```
[1] RapidOCR ăn 15,2 lõi và ⛔ KHÔNG khai trần
[2] `test_4301` dựng clip THẬT rồi gọi `de_xuat(clip)` nhiều lần
    ⇒ sau B10-4, mỗi lời gọi NẠP MODEL THẬT
[3] gate chạy 8 bước song song; ngân sách lõi đếm ở tầng BƯỚC
    ⇒ nó ⛔ KHÔNG thấy tiến trình CHÁU
```

🔴 Mắt xích **[2] là lỗi nặng nhất của tôi**: tôi **biến một phép kiểm vốn NHẸ
thành phép kiểm NẶNG mà ⛔ không khai báo**. `test_4301` viết từ trước, chạy
nhẹ, và B10-4 đổi nghĩa của nó mà ⛔ không đổi một dòng nào trong nó.

⭐ Kho **đã có** đúng cơ chế cho việc này: `tests/rao_chan_nang.py`
(`LTT_TEST_NANG`, `CHI_KHI_BAT`, và các fixture `gia_lap_*`). Luật ghi rõ:
*"Mọi phép kiểm nạp model thật phải nằm sau rào."* Tôi ⛔ không theo.

## 5. 🔴 Và bài học này ĐÃ ĐƯỢC ĐO, 25 ngày trước

`apps/video_assembly/services/dung_video.py:35` ghi:

> Ngày 03/09 đo được **12 tiến trình `demucs`, mỗi cái 460–984 % CPU**, vì
> `demucs_runner` ⛔ không đặt `torch.set_num_threads`. Ngân sách `-n` **⛔
> không đếm tiến trình cháu**.

**Cùng lớp lỗi. Cùng máy. Cùng hậu quả.** Nó được vá — nhưng **chỉ cho
`demucs`**. ⛔ Không ai hỏi *"còn thư viện nào cũng mặc định lấy hết lõi?"*

⇒ Cùng họ *"luật hẹp ru ngủ"*: một bản vá **đúng và cụ thể** làm người đọc tin
rằng **cả lớp lỗi** đã được xử.

⚠️ Và câu ấy nay là một **tham chiếu chết**: nó viết ở thì hiện tại (*"⛔ không
đặt"*) trong khi `demucs_runner.py:324` **đã đặt** `set_num_threads(4)`. Ai đọc
hôm nay sẽ kết luận trần còn thiếu.

## 6. Rà soát toàn kho — ai còn hở

| nhóm | có trần ⛔ không | che bởi |
|---|---|---|
| `demucs_runner` | ✅ | `torch.set_num_threads(4)`, mở bằng `LTT_DEMUCS_LUONG` |
| `cao_do.py` | ✅ **gián tiếp** | chạy **bên trong tiến trình con demucs** |
| `apps/asv_gpu/do_luong/*` | ✅ **gián tiếp** | `platform_core.gpu_lease`, ghim vào tiến trình con |
| `apps/video_assembly/*` | ✅ **gián tiếp** | `ToolSpec.admission_resource` + `slots` |
| `apps/autosubvideo/*`, `platform_core/stt` | GPU | thuê GPU |
| **`do_vung_ocr`** | 🔴 **⛔ KHÔNG GÌ CẢ** | — |

⇒ RapidOCR là hộ tiêu thụ CPU **duy nhất** nằm ngoài mọi cơ chế: ⛔ không trần
luồng, ⛔ không thuê GPU, ⛔ không slot, ⛔ không rào test.

## 7. Bản vá — ba lớp, vì một lớp ⛔ không đủ

| # | lớp | trạng thái |
|---|---|---|
| 1 | `CPU_TRAN_LOI = 6` + `chan_loi()` bọc phần TÍNH | ✅ **đã làm, đã đo** |
| 2 | fixture giả lập OCR cho phép kiểm nhẹ | ⏳ chưa làm |
| 3 | **bánh cóc** cho cả lớp lỗi | ⏳ chưa làm |

### 7.1 Trần lõi — đã đo trên đường sản phẩm

```
N=2  2,1 lõi · 13,1 s      N=6  6,3 lõi · 4,9 s   <- CHỌN
N=4  4,2 lõi ·  6,5 s      N=8  8,4 lõi · 3,1 s

xác minh qua `do_vung._dai_chu_nhieu_tang`:
  CPU đỉnh 684 % = 6,8 lõi   (trước: 15,2)
  tập lõi SAU: 20 lõi ⭐ ĐÃ TRẢ LẠI
  số đoạn trả về: 4 — kết quả ⛔ KHÔNG đổi
```

⚠️ `6 + 5,45` (Windows Defender, đo 25/09, **ngoài mọi khoá**) `≈ 11,5 / 20`.
`N = 8` nhanh hơn 1,8 giây nhưng `≈ 13,5` thì gate 8 bước lại chạm trần.

⚠️ `finally` trả lại **đúng tập lõi cũ**, ⛔ không phải `range(cpu_count())`:
tiến trình có thể **đã** bị chặn từ trước, và trả "toàn bộ lõi" là **nới** giới
hạn của người khác.

### 7.2 Vì sao lớp 1 ⛔ KHÔNG đủ

Trần 6 lõi × N worker pytest vẫn là `6N`. Lớp 2 chặn ở chỗ khác: phép kiểm nhẹ
⛔ **không nạp model** chút nào.

### 7.3 Vì sao cần lớp 3

Nếu ⛔ không có bánh cóc thì lần sau ai thêm một thư viện mặc-định-lấy-hết-lõi
sẽ **lặp lại y hệt**, và ⛔ không ai nối được nguyên nhân — đúng như 03/09 đã
lặp lại thành 28/09.

⭐ *Với mỗi bẫy môi trường đã biết, hỏi: **"cái gì sẽ NỔ nếu nó xảy ra lần
nữa?"*** — nếu câu trả lời là *"tôi sẽ nhớ"*, thì chưa có gì cả.

## 8. ⛔ Chưa chạy gì để thử

Chủ dự án đang phân tích video và dặn ⛔ **không chạy thử nghiệm** vì xung đột.
Mục 7.2 và 7.3 **chưa viết, chưa chạy, chưa xác minh**. Mục 7.1 **đã đo** trước
khi có yêu cầu đó.
