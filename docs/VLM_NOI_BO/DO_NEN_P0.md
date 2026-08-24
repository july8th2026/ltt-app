# P0 — Đo nền máy B trước khi triển khai VLM

**2026-08-22, 20:xx.** Chỉ đọc, không đổi gì trên máy B.
Cổng P0 của [`LO_TRINH_THI_HANH.md`](LO_TRINH_THI_HANH.md).

---

## 1. Trạng thái lúc đo — ⚠️ MÁY B ĐANG CHẠY DỞ MỘT LÔ ĐO CỦA H37

`GET /queue` của ComfyUI trả về một job **đang chạy**:

```
queue_running: [ 117, 9134d9fc-… ]
  CheckpointLoaderSimple : hidream_o1_image_bf16.safetensors
  LoadImage              : ref_nguoi.png
  ImageScaleToTotalPixels: megapixels 0.4, resolution_steps 32
  HiDreamO1ReferenceImages (che do EDIT, 1 anh tham chieu)
  EmptyHiDreamO1LatentImage: 2560 x 1440
  KSampler               : 30 buoc, cfg 5.0, euler/normal, seed 501
  SaveImage              : ltt_h37/G5a_edit_1anh_0p4mp/ed1
queue_pending: []
```

**Đây chính là phép đo theo bậc mà `CLAUDE.md` yêu cầu** trước khi mở chế độ `edit`:
*"đo theo bậc, có người canh (1 ảnh @ 0,4 MP → đo VRAM → tăng dần)"*. Một phiên khác
đang chạy nó.

⇒ **Không đụng vào.** Không gọi `/free`, không nạp gì lên card, không tắt gì.
Khung 2560×1440 = **3.600 token**, dưới trần `TOKEN_DA_DO_TOI_DA = 4096` — hợp lệ.

---

## 2. Số đo

### 2.1. GPU

| | Giá trị |
|---|---|
| Card | RTX 3090, 24.576 MiB |
| **Đang dùng** | **20.279 MiB (82,5 %)** — job H37 ở trên |
| Trống | 4.047 MiB |
| Util | 100 % |
| Nhiệt | **65 °C** |
| Điện | **358,65 W** |
| **PCIe** | **x16** ✅ (khớp lần đo trước) |

**Ghi chú:** 20,3 GB cho `edit` 1 ảnh @ 0,4 MP ở 2560×1440 — **thấp hơn** mốc 23,7–23,9 GB
mà D-022 đo cho lô 30 ảnh liên tiếp. Không mâu thuẫn: D-022 đo model **thường trú giữa
các job**; đây là một lượt đơn.

### 2.2. RAM — điều kiện của phương án "RAM giữ, VRAM luân phiên"

| | |
|---|---|
| Tổng | **196.488 MB** |
| Trống | **112.293 MB (112,3 GB)** |
| ComfyUI (`python.exe` PID 13912) | **17,4 GB** RAM |

⇒ Thừa sức giữ **cả** GGUF 15,33 GiB trong page cache **lẫn** ComfyUI, cùng lúc.
Đây là thứ làm cho việc nạp lại sau khi nhả VRAM nhanh — không phải đọc lại từ đĩa.

### 2.3. Đĩa `H:` (NVMe) — nơi sẽ đặt model

| | |
|---|---|
| Trống | **818,3 GB** / 1,1 TB |
| Cần cho VLM | **~16,2 GiB** (Q4_K_M 15,33 + mmproj 0,86) |

### 2.4. Cửa sổ giờ Windows Update

```
ActiveHoursStart = 0x7  -> 07:00
ActiveHoursEnd   = 0x1  -> 01:00
```

✅ Khớp đúng cảnh báo trong `CLAUDE.md`. **Sau 01:00 Windows được phép khởi động lại
bất cứ lúc nào.** Mọi lượt đo dài của ta phải kết thúc **trước 01:00**.

---

## 3. Cổng P0 — trạng thái

| # | Mục | Trạng thái |
|---|---|---|
| 1 | VRAM / ai đang giữ | ✅ đo xong |
| 2 | RAM trống | ✅ 112,3 GB |
| 3 | `H:` còn chỗ + là NVMe | ✅ 818,3 GB |
| 4 | **ComfyUI có nhả sạch VRAM sau `/free` không** | ⏸️ **CHƯA ĐO ĐƯỢC** — đang có job chạy, gọi `/free` lúc này là phá job |
| 5 | Cửa sổ giờ Windows Update | ✅ 07:00 → 01:00 |
| 6 | PCIe link | ✅ x16 |

**P0 chưa qua cổng.** Còn đúng một mục: **mục 4**.

Chủ dự án đã xác nhận *"các bot đều có cơ chế nhả sạch VRAM sau khi hoàn thành job"*.
Điều đó **rất có thể đúng** — nhưng nó là **giả định nền của toàn bộ P6**, và cả kế
hoạch 200K (biên VRAM chỉ 1,3 GB) đứng trên nó. Nên vẫn phải **đo một lần bằng
`nvidia-smi`** (D-013: không tin `/system_stats`, không tin `/health`), ngay khi hàng
đợi trống.

**Phép đo còn lại, mất ~2 phút:**

1. chờ `queue_running` rỗng;
2. `nvidia-smi` — ghi số A;
3. `POST /free` với `{"unload_models": true, "free_memory": true}`;
4. chờ 10 giây, `nvidia-smi` — ghi số B;
5. **Qua cổng nếu B ≤ ~1.500 MiB** (chỉ còn desktop/dwm).

---

## 4. Điều rút ra, đưa thẳng vào thiết kế

| Số đo | Nó ràng buộc gì |
|---|---|
| PCIe **x16**, RAM trống **112 GB** | Nạp lại model sau khi nhả sẽ nhanh — GGUF nằm trong page cache, chỉ còn tải qua PCIe. **Nhưng phải đo thật ở P6**, không suy ra |
| Job `edit` chỉ tốn **20,3 GB** | Khi H37 chạy `edit`/`subject`, VRAM còn trống ~4 GB — **không đủ** cho VLM 23,3 GB. Khẳng định lại: **luân phiên, không song song** |
| Active Hours kết thúc **01:00** | P5 (sweep) và P6 (đổi lượt 10 lần) là việc dài — **xếp lịch ban ngày** |
| Nhiệt **65 °C** ở 358 W | Còn xa mốc throttle 84 °C mà D-021 ghi nhận. Nhiệt không phải nút thắt |

---

## 5. Lệnh đã chạy

Script `p0_do_nen.cmd` chép sang `C:\Windows\Temp\` trên máy B rồi chạy. Chỉ gồm
`nvidia-smi`, `systeminfo`, `fsutil`, `curl` tới ComfyUI, `tasklist`, `reg query`.
Không có lệnh ghi nào.
