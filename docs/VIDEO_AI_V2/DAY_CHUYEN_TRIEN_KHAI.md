# DÂY CHUYỀN TRIỂN KHAI — bốn đường, đừng trộn

Viết 2026-09-06. Cùng khuôn với `docs/16_CAP_NHAT_VA_DEPLOY.md`, và cùng nguyên
tắc mà §6 của tệp đó đã đặt ra: **mỗi đích tính toán có dây chuyền riêng, và nói
thẳng nó KHÔNG đi đường của đích khác.**

---

## 0. Bốn dây chuyền

| # | Dây chuyền | Đi từ | Tới | Nhịp đổi | Luật ở đâu |
|---|---|---|---|---|---|
| ① | **Nền tảng LTT** (A-CONTROL) | máy A · trunk | `C:\LTTPlatform` | mỗi hạng mục | `docs/16` |
| ② | **Máy B** (LAN) | riêng | máy B | riêng | `docs/16` §6 — ⛔ V2.1 **không chạm** |
| ③ | **Ảnh C-CLOUD** | `Dockerfile` | ảnh → RunPod | khi đổi engine/thư viện | **tệp này** |
| ④ | **Model** | HuggingFace | network volume | khi đổi tập model | **tệp này** |

🔴 **Sai lầm cần chặn: trộn ③ với ④.** Chúng có nhịp khác nhau, cách hoàn tác
khác nhau, và chi phí khác nhau **hai bậc**:

| | ③ Ảnh | ④ Model |
|---|---|---|
| Đổi khi | nâng SHA WanGP · đổi torch · đổi attention kernel | thêm/bớt chế độ · đổi lượng tử hoá |
| Kích thước | vài GB | **hàng chục tới hàng trăm GB** |
| Dựng lại mất | ~40 phút *(đo P01)* | ~15–30 phút tải |
| Hoàn tác | quay về version ảnh trước | tải lại theo bảng kê |

⇒ Nếu buộc chúng vào nhau thì **sửa một dòng `Dockerfile` sẽ kéo theo tải lại
66 GB**, và ngược lại. Tách ra là toàn bộ nội dung của chuẩn hoá này.

---

## 1. Dây chuyền ③ — ảnh C-CLOUD

### Hiện tại (P01): chưa có ảnh, cài thẳng lên volume

Vì `deepbeepmeep` **không phát hành ảnh chính chủ** (Docker Hub chỉ có ảnh bên
thứ ba — không dùng cho tài khoản production), P01 chạy các bước trong
`Dockerfile` **của WanGP** dưới dạng script, cài vào `/data`.

⭐ Điều này **không phải đường vòng** — nó là cách rẻ nhất để soạn đúng ảnh:
`cai_dat.sh` ghi thời gian và mã thoát từng lệnh, nên `install.log` **chính là
bản nháp `Dockerfile`**, đã được chứng minh chạy trên đúng nền Linux/CUDA đích.

Đo được ở P01 (Pod A100, venv trên network volume):

| Bước | Giây |
|---|---:|
| `apt install` | 38 |
| `git clone` + `checkout` | 43 |
| `venv` + `pip upgrade` | 91 |
| **`torch==2.10.0+cu128`** | **645** |
| **`requirements.txt`** | **1.413** |
| SageAttention (clone + vá) | 2 |

⚠️ Hai bước lớn chậm vì **venv nằm trên ổ mạng**. Trong một ảnh Docker thật,
chúng ghi vào ổ cục bộ của máy build và sẽ nhanh hơn nhiều. Đừng lấy hai con số
này làm ước lượng cho thời gian build ảnh.

### Đích (P04+): ảnh dựng từ GitHub

Khuôn V3 đã chạy được: kho riêng → **RunPod GitHub integration** → đẩy `main` là
RunPod tự build → `version` của endpoint tự tăng.

⛔ Đường này chỉ áp dụng cho **Serverless endpoint**. **Pod** cần một ảnh đã có
trong registry — Pod không build từ GitHub.

### Nghiệm thu ③

Theo đúng tinh thần `docs/16`: *"đối chiếu băm, đừng tin `EXITCODE`."*

- `moi_truong.json` phải khai đúng `torch`, `cuda`, `sm`, `mmgp`, `sageattention`;
- `git rev-parse HEAD` **trong ảnh** phải bằng SHA ghim;
- một lượt sinh thật phải chạy được **trước khi** gọi ảnh là tốt.

---

## 2. Dây chuyền ④ — model

### Nguồn chân lý: `defaults/*.json` của WanGP, KHÔNG phải bảng kê chép tay

`wgp.py::download_models` đọc định nghĩa model, chọn biến thể theo
`transformer_quantization` (mặc định `int8`), tìm tệp cục bộ trước, và kéo theo
cả `preload_URLs` · `VAE_URLs` · LoRA đi kèm.

⛔ **Không dựng bảng kê bằng tay.** Bản nháp đầu của P01 làm thế và **đã bỏ sót**
`preload_URLs`/`VAE_URLs`. Một danh sách chép tay là một danh sách sẽ sai, và nó
sai **âm thầm**.

### Bảng kê thật sinh SAU khi tải, không TRƯỚC

```
WanGP tu tai  ->  doc lai /data/ckpts qua S3  ->  DO la bang ke
```

Đó là bảng kê dùng cho: đối chiếu toàn vẹn · ước lượng cold start · quyết định
kích thước volume (`O-007`).

### Đích: `/data/ckpts` trên network volume

Đặt bằng cơ chế của chính WanGP — khoá `checkpoints_paths` trong
`wgp_config.json`, cộng `HF_HOME` trỏ vào volume. **Không symlink, không vá.**

### Hoàn tác ④

Xoá tệp trên volume qua S3 rồi để WanGP tải lại. Bảng kê cũ giữ trong
`docs/VIDEO_AI_V2/khoi_phuc/` — ví dụ bộ ComfyUI của V3 đã xoá 06/09 vẫn tái tạo
được chính xác nhờ `repo` + `revision` ghim + `sha256`.

---

## 3. Ranh giới bí mật — thứ KHÔNG được lên C-CLOUD

| Được | Không bao giờ |
|---|---|
| khoá endpoint RunPod của chính job đó | khoá R2 gốc |
| đường truyền media có phạm vi, sống ngắn | mật khẩu CSDL |
| tham số sinh video | khoá ký phiên của LTT |
| | khoá API của nhà cung cấp khác |

V3 đã làm đúng và ghi lại: *"Worker **không** giữ khoá S3 của volume. Nó đọc
model bằng hệ thống tệp qua `/runpod-volume`."* Giữ nguyên luật đó.

---

## 4. Thay đổi loại gì thì chạm dây chuyền nào

| Thay đổi | ① Nền tảng | ③ Ảnh | ④ Model |
|---|:--:|:--:|:--:|
| Sửa GUI / route / giá credit của app | ✅ | — | — |
| Nâng SHA WanGP | — | ✅ | *chỉ khi định nghĩa model đổi* |
| Đổi `transformer_quantization` | — | — | ✅ |
| Thêm chế độ (control, upscale) | *có thể* | — | ✅ |
| Đổi attention kernel / torch | — | ✅ | — |
| Đổi `profile` bộ nhớ | — | — | — *(cờ lúc chạy)* |
| Đổi GPU / datacenter | — | — | ⚠️ *volume không di chuyển được* |

⭐ Hàng cuối là hàng đắt nhất: `dataCenterId` của volume **không sửa được**, nên
đổi datacenter = tạo volume mới + chạy lại toàn bộ ④.

---

## 5. Trình tự chuẩn cho một lượt chạy C-CLOUD

```
0. video_cloud.py kiem-ke        -> `pods` phai RONG truoc khi bat dau
1. day script/cau hinh len volume qua S3      (0 dong)
2. tao Pod  ->  GHI SO ID NGAY, khong `print` chen giua
3. theo doi qua S3  (khong can shell)
4. doc ket qua ve
5. XOA pod
6. kiem-ke lai  ->  `pods` phai RONG
7. sau 20-60 phut: doc hoa don that
```

⛔ Bước 6 không được bỏ. Và ⛔ bước 7 là nguồn số tiền **duy nhất** đáng tin —
dòng `Muc chi` mù trong lúc worker khởi động, đúng giai đoạn đắt nhất.

---

## 6. Ba luật rút ra từ chính P01

**① Mọi việc làm được ở $0 phải xong trước khi bật máy.** P01 tìm ra **hai lỗi
sẽ làm cháy một lượt boot** — `/workspace` đụng nhau, và model rơi vào ổ container
— bằng cách **đọc mã**, không tốn một giây GPU.

**② Ghi sổ tài nguyên phải là câu lệnh NGAY SAU khi có id.** V3 từng tạo pod
thành công rồi chết ở dòng `print` kế tiếp vì stdout cp1252, để lại một pod đang
tính tiền mà **không có trong sổ**.

**③ Một phép đo hỏng không được giết cả lượt.** Mọi hạng mục trong `do_luong.py`
bọc `try/except`, ghi lại rồi đi tiếp — vì lượt chạy này tốn tiền và không lặp
lại rẻ được. Và các phép đo **xếp theo giá trị giảm dần**, nên dừng sớm vẫn còn
số quan trọng nhất.
