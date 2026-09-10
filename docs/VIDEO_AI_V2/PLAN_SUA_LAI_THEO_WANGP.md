> ⛔ **TỆP NÀY ĐÃ BỊ THAY** bởi `PLAN_V1_CHI_TIET.md` (07/09/2026).
> Giữ lại để tra lịch sử. Đừng thi hành theo nó — một số kết luận trong
> đây đã bị chính phiên sau bác bằng bằng chứng.

# PLAN SỬA LẠI — BÁM ĐÚNG CÁCH WanGP TRIỂN KHAI

Ngày 06/09/2026. Thay phần tham số của `FINAL_IMPLEMENTATION_PLAN.md`.
Nguyên tắc cưỡng chế: **triển khai như WanGP triển khai, hạn chế tự suy.**

Mọi dòng dưới đây neo vào mã nguồn WanGP tại SHA ghim
`1e1dd2757f24923f008593d9d4ec09062234be20`, đọc trực tiếp từ volume.

---

## 1. Chuỗi mặc định THẬT của WanGP — bốn tầng, đúng thứ tự

`wgp.get_factory_settings()` dựng settings theo bốn tầng chồng lên nhau:

| # | Nguồn | Bằng chứng |
|---|---|---|
| ① | `models/_settings.json` → `primary_settings` (**115 khoá**) | `wgp.py:2568-2569` |
| ② | ghi đè cứng `resolution`, `flow_shift` | `wgp.py:3219-3220` |
| ③ | `family_handler.update_default_settings()` | `wan_handler.py:1253` |
| ④ | `model_def["settings"]` = **mọi khoá ngoài `"model"`** của tệp JSON | `wgp.py:3313` |

⭐ Tầng ④ là mắt xích dễ đọc sót nhất: `refresh_model_defs` làm
`model_def = json_def.pop("model")` rồi `model_def["settings"] = json_def`.
Tức các khoá đặt ở **cấp cao nhất** của `defaults/*.json` — `guidance_scale`,
`flow_shift`, và với vài model là cả `resolution` — chính là settings.

### Quy tắc độ phân giải của WanGP

```python
"resolution": "1280x720" if "720" in base_model_type else "832x480",
```
`wgp.py:3219`

Đây là quy tắc về **tên model**, không phải về thẩm mỹ. Wan 2.1 có bản 480p và
bản 720p riêng (`sky_df_720p_14B`, `vista4d_720p`). `t2v_2_2` không mang "720"
⇒ WanGP định cho nó **832×480**.

---

## 2. Ta lệch WanGP ở đâu — đo, không đoán

Dựng lại bốn tầng ngoại tuyến rồi đối chiếu từng khoá với
`ho_so_data/ltt.video.chuan.v1.json` (`scratchpad/doi_chieu_ho_so.py`):

| Khoá | WanGP | Hồ sơ LTT | Phán |
|---|---|---|---|
| `resolution` | `832x480` | `1280x720` | ❌ **tôi tự đặt** |
| `num_inference_steps` | `30` | `20` | ❌ **tôi tự đặt** |
| 111 khoá còn lại | — | — | ✅ trùng khớp |

**Chỉ hai khoá lệch, và cả hai đều do tôi.** Lý do đã ghi lúc đó — *"để so được
với phép đo của V3"* — là lý do **đối chiếu nội bộ**, không phải khuyến nghị của
WanGP. Nó lọt qua vì tôi ghi chú thích thay vì đặt câu hỏi.

✅ **Model thì chọn đúng.** `docs/MODELS.md`: *"General text-to-video or
image-to-video → Wan 2.2 T2V (`t2v_2_2`), Wan 2.2 I2V — Mature general-purpose
video models with broad LoRA and WanGP feature support."*

✅ `Wan2GP/settings/` rỗng ⇒ bản trích 113 khoá là **factory thật**, không dính
trạng thái phiên trước. (`get_default_settings` **ghi tệp ra đĩa** rồi lần sau
đọc lại từ đó — `wgp.py:3233-3241`. Lần này ta thoát, nhưng đây là bẫy: phép
trích lặp lại trên máy đã chạy sẽ trả về **thứ ai đó lưu**, không phải factory.)

---

## 3. 🔴 Đường lên độ phân giải cao của WanGP KHÔNG phải sinh thẳng 720p

`README.md:234`:

> *"...generation can be slow, so a practical alternative is to generate at a
> lower resolution, such as 480p, and upscale the result afterward."*

Và `docs/MODELS.md`, mục *Choosing variants*, bước 3:

> *"Test a short clip or smaller image before increasing resolution or duration."*

⇒ Cách WanGP tự làm: **sinh 480p → nâng cấp**. Tôi đã làm ngược: ép 720p ngay
từ đầu rồi bù bằng cách **giảm bước 30→20** để kịp thời gian. Đó là đánh đổi
chất lượng mà không ai duyệt.

🔑 Và đường nâng cấp **không cần kiến trúc mới**: `spatial_upsampling` +
`temporal_upsampling` đã nằm sẵn trong **chính 115 khoá settings**. Không thêm
lớp, không thêm dịch vụ — chỉ là hai khoá trong hồ sơ.

⚠️ **Ẩn số phải đo, không được đoán:** danh sách bộ nâng cấp phụ thuộc bản cài —
`wgp.py:1208` trả lỗi *"is not supported by the current WanGP install"*. Phải
gọi `upsampler_api` trên chính máy rồi mới chốt giá trị.

---

## 4. Hai lỗi hạ tầng phát hiện cùng lượt

### 4.1 Cổng HTTP là **8888**, không phải 8188

```
ports: ['8888/http', '22/tcp']      portMappings: {'22': 11191}
```

`dich_vu_ccloud.py` đang ghi `--port 8188`. Pod **không mở** 8188 ⇒ máy A không
gọi tới được. Sửa sang 8888; đường công khai là
`https://bly29qwp5bum3r-8888.proxy.runpod.net`.

### 4.2 Ảnh container **không có Python** — và đó là gốc của sự cố vòng lặp

```
imageName: nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04
```

Python chỉ tồn tại vì `cai_dat.sh` chạy `apt-get install python3`, tức nó nằm ở
**ổ container (tạm)**. `venv/bin/python3` là symlink **tuyệt đối** tới
`/usr/bin/python3`, nên nửa **bền** trên volume phụ thuộc nửa **tạm**.

Mốc `_CAI_DAT_XONG` nằm ở nửa bền ⇒ pod khởi động lại: nửa tạm bay hơi, mốc còn,
cổng bỏ qua cài đặt, symlink treo. Bash báo dangling symlink đúng bằng câu
`No such file or directory` nên loi trông như venv bị xoá — trong khi venv còn
nguyên.

**Đã sửa** (`tools/wangp/cai_dat.sh`): hai nửa, hai cổng, và **cả hai cổng kiểm
thứ thật** — `command -v python3`, `-x venv/bin/python`, và `import torch, mmgp`
chạy được. Mốc đã bỏ hẳn.

⭐ Bài học tổng quát hơn "mốc là lời khẳng định, artefact là sự thật":
**một mốc chỉ đúng khi nó nhìn thấy toàn bộ hệ mà nó khẳng định.** Mốc này
khẳng định một tính chất của hệ hai-tuổi-thọ mà nó chỉ nhìn thấy một nửa.

---

## 4b. 🔴 WanGP CÓ tài liệu và CÓ bộ triển khai — tôi đã bỏ qua chúng

Kho WanGP chứa **26 tài liệu** trong `docs/`, và ở gốc kho có **`Dockerfile`**,
**`entrypoint.sh`**, **`run-docker-cuda-deb.sh`**, `wgp_config.json`.

Tôi viết `cai_dat.sh` và `khoi_dong.sh` bằng tay **trước khi** đọc chúng, và
đánh dấu vài thứ là "ẩn số phải đo" trong khi WanGP đã có hẳn một tệp trả lời:

| Thứ tôi tự làm / gọi là ẩn số | Tài liệu đã trả lời sẵn |
|---|---|
| bộ nâng cấp — *"phải đo trên máy"* | `docs/SPATIAL_UPSAMPLERS.md` · `docs/TEMPORAL_UPSAMPLERS.md` |
| sổ đăng ký hồ sơ 113 khoá | `docs/SETTINGS.md` (mô tả **từng** khoá) |
| `cai_dat.sh` viết tay | `Dockerfile` |
| `khoi_dong.sh` viết tay | `entrypoint.sh` |
| cờ dòng lệnh | `docs/CLI.md` · `run-docker-cuda-deb.sh` |

### Đối chiếu: chỗ nào tôi bám đúng, chỗ nào lệch

✅ **`cai_dat.sh` bám `Dockerfile` sát** — cùng ảnh nền
`nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04`, cùng danh sách gói apt, cùng
`torch==2.10.0+cu128`, cùng bản vá SageAttention, cùng `TORCH_CUDA_ARCH_LIST=8.0`
(A100).

⚠️ Đừng nhầm hai tuyến: `INSTALLATION.md` mô tả tuyến **conda** và chỉ ghi hai
cặp (`cu130`+torch 2.10.0+py3.11 · `cu128`+torch 2.7.1+py3.10). Cặp
`torch 2.10.0 + cu128` ta đang dùng **không** nằm trong đó — nó là tuyến
**Docker**, và tuyến Docker mới là tuyến ta đi.

❌ **`khoi_dong.sh` bỏ sót chín biến môi trường của `entrypoint.sh`**, trong đó:

```bash
export TORCH_ALLOW_TF32_CUBLAS=1     # TF32 tren Ampere — thang vao toc do matmul
export TORCH_ALLOW_TF32_CUDNN=1
export OMP_NUM_THREADS=$(nproc)      # va MKL / OPENBLAS / NUMEXPR
export PYTHONUNBUFFERED=1
```

⇒ Phép đo **79,8 giây/bước** ngày 06/09 chạy **thiếu TF32**. Con số ấy không
phải "tốc độ của WanGP trên A100"; nó là tốc độ của bản cấu hình thiếu của tôi.

❌ **Thiếu `--compile`.** `run-docker-cuda-deb.sh` chính chủ truyền nó, và
`docs/CLI.md:225` xếp nó vào ví dụ *Best Performance*
(`--compile --attention sage2 --profile 3`).

⚠️ **`--perc-reserved-mem-max`: hai nguồn của WanGP mâu thuẫn nhau.**
`docs/CLI.md:156` ghi `< 0.5`; `run-docker-cuda-deb.sh` truyền `1`. **Chưa đặt**,
có chủ ý — đo rồi mới chốt, không sao chép mù bên nào.

✅ **`--attention sage2` hợp lệ** (`CLI.md:283`: cần Triton + SageAttention 2.x,
ta có 2.2.0). Script docker dùng `sage` là lựa chọn thủ, không phải giới hạn.

✅ **Profile 1 được tài liệu xác nhận** — `CLI.md:147`: *"Load entire current
model in VRAM and keep all unused models in reserved RAM for fast VRAM
transfers"*. Đúng điều đã chốt ở `P01-D-15`.

⭐ Bài học: **đọc bộ triển khai của thượng nguồn trước khi viết bộ triển khai của
mình.** Một tệp `Dockerfile` là câu trả lời cho câu hỏi "cài thế nào", và nó
không trôi như một ghi chú.

---

## 5. Việc phải làm, theo thứ tự

### E0 — sửa hồ sơ về đúng factory *(không cần GPU)*

- [ ] `ho_so_data/ltt.video.chuan.v1.json`: `resolution` → `832x480`,
      `num_inference_steps` → `30`.
- [ ] `ho_so.py`: bỏ chú thích "để so với V3"; thêm phép kiểm chốt rằng hồ sơ
      **không lệch factory quá N khoá đã liệt kê tên** — chốt theo *tập hợp*,
      không theo *số lượng*.
- [ ] `tools/wangp/dich_vu_ccloud.py`: cổng 8188 → **8888**.
- [ ] `TAI_NGUYEN_VA_CACH_DUNG_LAI.md` §1: sửa dòng `/data/ckpts/` — **đo được
      là rỗng**, model không nằm ở đó.
- [ ] `cost.py`: `GIAY_GPU_MOI_GIAY_VIDEO = 316.0` đo ở **profile 4 + 720p +
      20 bước** ⇒ **vô hiệu**. Đánh dấu là chưa đo lại, đừng để nó im lặng sai.

### E1 — đo lại ở đúng cấu hình WanGP *(cần GPU, ~25 phút)* — ĐANG CHẠY

Một lượt, `832x480 / 30 bước / 81 khung / profile 1`, **chưa** có TF32 và
**chưa** `--compile` — cố ý, để làm **mốc gốc** cho phép so A/B ở `E1b`.

### E1b — bật đúng môi trường của `entrypoint.sh`, đo lại, so

Đổi **một lần một thứ**: (1) chín biến môi trường của WanGP; (2) `--compile`.
Một phép đo đổi hai thứ cùng lúc không trả lời được thứ nào.

### E2 — chốt đường 480p→720p bằng số, không bằng ý kiến

Đọc `docs/SPATIAL_UPSAMPLERS.md` **trước**, rồi so ba lượt:
`480p thô` · `480p + spatial_upsampling` · `720p thô`. Chốt theo **giá mỗi giây
video** và ảnh so sánh.

### E3 — đọc `docs/SETTINGS.md` đối chiếu toàn bộ 113 khoá hồ sơ

Sổ đăng ký hồ sơ dựng từ phép trích thời-chạy, chưa từng đối chiếu với tài liệu
mô tả từng khoá. Việc này **không cần GPU**.

### E4–E7 — như `FINAL_IMPLEMENTATION_PLAN.md`, sau khi E1 xanh

---

## 6. Điều KHÔNG đổi

Kiến trúc tối giản đã khoá vẫn đứng. Audit này **không** phát hiện lớp thừa nào
mới, cũng không đòi thêm lớp nào: đường nâng cấp đi bằng hai khoá settings có
sẵn, đúng tinh thần *REUSE BEFORE BUILD*.

Cái sai nằm ở **giá trị tham số**, không ở **hình dạng hệ thống**.
