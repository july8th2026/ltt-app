# P01 — KẾT QUẢ ĐO THẬT trên C-CLOUD

Đo 2026-09-06 trên Pod `bly29qwp5bum3r` (A100 SXM 80 GB, `US-KS-2`, 251 GB RAM,
32 vCPU, $1,59/giờ). **Tổng chi 106 phút = ~$2,81** trên trần duyệt $6,00.

Dữ liệu thô: `do_luong_P01/`. Mọi con số dưới đây đọc từ đó, không ước lượng.

---

## 1. 🔴 Con số đắt nhất: VRAM đỉnh **14,08 GB**

Lấy mẫu `nvidia-smi` 1 Hz suốt 41 phút, **1.863 mẫu** (`vram_luot1.csv`):

| | Đo được |
|---|---|
| **VRAM đỉnh** | **14,08 GB** / 85,09 GB có sẵn |
| GPU trung bình lúc sinh | **86%** · đỉnh **100%** |
| Giai đoạn nạp model (10 phút đầu) | VRAM 3,00 GB · GPU **0%** |
| Giai đoạn sinh | VRAM 14,08 GB · GPU **99%** |

**Đối chiếu:** ComfyUI của V3 đo đỉnh **59,8 GB** (`V-008`, fp16 720P).
⇒ **WanGP dùng ít hơn 4,2 lần** cho cùng độ phân giải và số khung.

### Hệ quả tiền — `O-006` đã có câu trả lời

Card 80 GB là **thừa rất nhiều**. Ở `profile 4`, 14,08 GB **vừa một card 24 GB**.

| Card | VRAM | $/giờ Pod | So với A100 |
|---|---:|---:|---|
| A100 SXM *(đang thuê)* | 80 GB | **1,390** | — |
| A40 | 48 GB | **0,350** | rẻ **4,0×** |
| RTX 4090 | 24 GB | **0,340** | rẻ **4,1×** |
| RTX A5000 | 24 GB | **0,160** | rẻ **8,7×** |

⚠️ **Một dè dặt phải giữ:** 14,08 GB là số của **`profile 4`**, hồ sơ *"nạp từng
phần khi cần"* — nó **cố ý** giữ VRAM thấp bằng cách đánh đổi tốc độ.
`profile 3` (đã chốt ở `P01-D-12`) nạp **trọn** model vào VRAM nên sẽ dùng
**nhiều hơn**: ước chừng 14,90 GB × 2 tầng + hoạt hoá ≈ **35–45 GB**.

⇒ Card đích nhiều khả năng là lớp **48 GB (A40, $0,350/giờ)**, không phải 80 GB.
Con số chính xác phải đo ở `profile 3` — nhưng ngay cả ước lượng bi quan nhất
cũng đã loại A100 khỏi danh sách.

⛔ Đừng chốt lớp card bằng bảng này. Chốt bằng **một phép đo `profile 3`**.

---

## 2. Tốc độ và giá vốn — ở `profile 4`

| | |
|---|---|
| Cấu hình | 1280×720 · 81 khung · 20 bước · INT8 · SageAttention 2.2.0 |
| **Thời gian mỗi bước** | **79,8 giây** |
| Sinh (20 bước) | ~26,6 phút |
| Nạp model lần nguội | ~8,3 phút |
| **Tổng một lượt nguội** | **2.101,7 giây = 35,0 phút** |
| Giá vốn trên A100 Pod | **~$0,93/video** |

⚠️ Đây là số **xấu nhất có thể**: `profile 4` là hồ sơ chậm nhất, và lượt này
gồm cả nạp model nguội. `profile 3` sẽ nhanh hơn — chưa biết bao nhiêu.

📌 Để so: V3 ước ~8,7 phút/video trên H100 (là **ước tính** từ bảng của tác giả
model, không phải phép đo của V3). fal.ai **bán** cùng model $0,41 (`V-018`).

---

## 3. Hợp đồng engine — thứ P04 cần để viết client

### Tệp đầu ra

```
/data/Wan2GP/outputs/2026-09-06-09h58m58s_seed1001_A large orange octopus is
seen resting on the bottom of the ocean floor, blending in with the sandy.mp4
```

| | |
|---|---|
| Thư mục | `outputs/` dưới gốc WanGP (`save_path` trong `wgp_config.json`) |
| Dung lượng | **16.176.321 byte = 16,18 MB** cho video 5,06 giây 720P |
| Định dạng | `.mp4` |

🔴 **Bẫy cho P04: tên tệp chứa nguyên văn prompt.** Prompt có dấu, dấu phẩy,
dấu nháy, ký tự lạ — tất cả rơi vào tên tệp. LTT **phải đặt lại tên** khi đẩy
lên R2, không được dùng tên gốc làm khoá đối tượng. Và tên tệp **rò rỉ prompt**,
là dữ liệu của người dùng.

### Sự kiện tiến độ — đủ giàu để làm thanh tiến độ thật

Đếm được trong một lượt sinh 20 bước:

| Loại | Số sự kiện | Dùng làm gì |
|---|---:|---|
| `progress` | **786** | ~39 sự kiện mỗi bước — thanh tiến độ mượt |
| `preview` | **20** | **một ảnh xem trước mỗi bước** — xem trực tiếp trên GUI |
| `stream` | 217 | dòng log |
| khác | 7 | |

Trạng thái cuối: `['decoding', 20, 20]` ⇒ có **phase**, và phase cuối là
`decoding` — tức thanh tiến độ nên hiển thị theo phase, không chỉ theo %.

### Huỷ giữa chừng — ĐẠT

```json
{"thanh_cong": false, "tep": [], "loi": ["Generation was cancelled"]}
```

`job.cancel()` gọi ở giây 75. Đúng như `docs/API.md` mô tả.

⚠️ **Chưa trả lời được: huỷ xong GPU có nhả VRAM không.** Lượt kiểm huỷ bắt job
**trong lúc còn nạp model** (VRAM đỉnh cả lượt chỉ 0,6 GB, GPU 0%), nên chưa có
VRAM nào để nhả. ⇒ Đã chứng minh **huỷ được cả khi đang nạp** — trường hợp hay
gặp hơn — nhưng phần nhả VRAM còn nợ.

---

## 4. Môi trường đã dựng (còn nguyên trên volume)

| | |
|---|---|
| Ảnh gốc | `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` |
| torch | **2.10.0+cu128** |
| `mmgp` | **3.7.14** |
| `sageattention` | **2.2.0** *(biên dịch từ nguồn, `TORCH_CUDA_ARCH_LIST=8.0`)* |
| GPU | A100-SXM4-80GB · sm **8.0** · 85,09 GB |
| WanGP | SHA ghim `1e1dd275…`, `WanGP_version = 12.71` |

Thời gian cài (venv **trên ổ mạng**, nên chậm hơn build ảnh thật):

| Bước | Giây |
|---|---:|
| apt | 38 |
| clone + checkout | 43 |
| venv + pip | 91 |
| torch | **645** |
| requirements | **1.413** |
| SageAttention (clone + vá + build) | ~600 |

⇒ `install.log` là **bản nháp `Dockerfile`** đã chứng minh chạy được.

---

## 5. Còn nợ

| # | Việc | Vì sao chưa xong |
|---|---|---|
| **N1** | VRAM + tốc độ ở **`profile 3`** | `init()` chỉ gọi được một lần mỗi tiến trình (`P01-D-13`); script tạo ba phiên trong một tiến trình nên phiên 2–3 bị từ chối |
| **N2** | Huỷ xong GPU có nhả VRAM không | lượt huỷ bắt job lúc đang nạp, chưa có VRAM để nhả |
| **N3** | Hoá đơn RunPod cuối cùng | trễ 20–60 phút |

⛔ **N1 là thứ duy nhất còn chặn quyết định tiền.** Nó quyết card 24 GB hay 48 GB
— chênh lệch **4–8 lần** trên mọi giờ GPU về sau.

---

## 6. Trạng thái tài nguyên

| | |
|---|---|
| Pod `bly29qwp5bum3r` | **EXITED** — đã dừng, không còn tính tiền GPU |
| Volume `uizchbiet5` | 300 GB · chứa WanGP + venv + model + kết quả |
| Endpoint `uwzftpd3utftfn` | `workersMin=0` — $0 |
| Số dư | **$42,47** |

⚠️ Pod dừng vẫn giữ ổ container 20 GB (~$0,07/ngày). Giữ lại vì tồn kho A100 ở
`US-KS-2` đang **Low** — xoá đi có thể không thuê lại được. Xoá khi P01 đóng.
