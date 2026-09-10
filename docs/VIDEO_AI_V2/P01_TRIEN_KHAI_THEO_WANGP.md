# TRIỂN KHAI THEO ĐÚNG ĐƯỜNG CỦA WanGP

Chủ dự án chốt 06/09: *"ta cứ triển khai tất cả như WanGP triển khai để tránh
lỗi, hạn chế tự suy."*

⇒ Luật của tài liệu này: **mỗi lựa chọn phải chỉ ra được một cơ chế WanGP tự
cung cấp.** Chỗ nào buộc phải tự quyết thì ghi rõ *vì sao không tránh được*.

---

## 1. Kho có sẵn bản triển khai chính chủ

`Dockerfile` + `entrypoint.sh` nằm ngay gốc kho tại SHA ghim. **Không phải tự
viết `Dockerfile`** — đây là điều tôi đã định làm và nó thừa.

```dockerfile
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04
ARG CUDA_ARCHITECTURES="8.0;8.6"
...
RUN pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 \
    --index-url https://download.pytorch.org/whl/cu128
RUN pip install -r requirements.txt
# SageAttention build tu git, kem ban va phat hien GPU
ENTRYPOINT ["/workspace/entrypoint.sh"]
```

`entrypoint.sh` kết thúc bằng:

```bash
exec su -p user -c "python3 wgp.py --listen $*"
```

⇒ Tham số truyền qua `dockerStartCmd` **đi thẳng vào `wgp.py`**. Không cần lớp
bọc nào.

### Kiến trúc CUDA cho A100

Bảng trong chính `Dockerfile`: **`8.0` = A100**. Mặc định `"8.0;8.6"` **đã bao
gồm A100** ⇒ build không cần đổi `--build-arg`.

*(H100 = `9.0`; chú thích của chính tác giả nói thêm 8.9/9.0 "may cause
compilation issues on some setups" — thêm lý do chọn A100.)*

⚠️ Lệch nhỏ đáng biết: `README` phần cài tay ghi torch **cu130**, còn
`Dockerfile` dùng **cu128**. Chạy container thì `Dockerfile` là bản chính chủ —
theo nó.

---

## 2. 🔴 Hai xung đột với RunPod — và cả hai gỡ bằng cơ chế của chính WanGP

Đây là phần đáng giá nhất của lượt đọc mã này: **hai lỗi sẽ làm cháy một lượt
boot trả tiền, tìm ra bằng cách đọc, $0.**

### Xung đột ① — `/workspace` đụng nhau

| | |
|---|---|
| WanGP | `WORKDIR /workspace`, và `ENTRYPOINT ["/workspace/entrypoint.sh"]` |
| RunPod | `volumeMountPath` **mặc định `/workspace`** |

⇒ Gắn volume vào `/workspace` sẽ **che toàn bộ** thứ ảnh đặt ở đó — kể cả
`entrypoint.sh`. Container **không khởi động nổi**.

**Gỡ:** đặt `volumeMountPath` thành **`/data`**. Đây là trường của RunPod, không
phải chế thêm gì.

### Xung đột ② — model rơi vào ổ container rồi biến mất

`entrypoint.sh` đặt `HF_HOME=/home/user/.cache/huggingface`, và
`files_locator.py:7` đặt `default_checkpoints_paths = ["ckpts", "."]` — tức
`/workspace/ckpts`. **Cả hai đều nằm trên ổ container**, nên:

- xoá pod là **mất sạch model**, phải tải lại từ đầu mỗi lượt;
- ổ container ta đặt 20 GB — **không chứa nổi 66 GB model**.

**Gỡ — bằng đúng cơ chế WanGP cung cấp, không symlink, không vá:**

```jsonc
// /data/config/wgp_config.json
{ "checkpoints_paths": ["/data/ckpts", "ckpts", "."] }
```

`wgp.py:2683-2685` đọc khoá `checkpoints_paths` từ `wgp_config.json` rồi gọi
`fl.set_checkpoints_paths(...)`. Thư mục cấu hình chọn bằng cờ **`--config`**
(chính cờ mà `docs/API.md` dùng cho MCP).

Và đặt `HF_HOME=/data/hf` qua `env` của pod, đè biến trong `entrypoint.sh`.

⇒ Sau hai chỉnh này, **model nằm trên volume**, sống qua mọi lần xoá pod.

---

## 3. Bảng kê model: KHÔNG tự viết — để WanGP tự tải

Kế hoạch trước của tôi là tự dựng danh sách URL HuggingFace rồi nạp bằng
`video_nap_model.py` của V3. **Bỏ.** Đó đúng là "tự suy": một danh sách chép tay
là một danh sách sẽ sai, và nó sẽ sai **âm thầm**.

WanGP có `wgp.py::download_models` tự giải quyết: nó đọc `defaults/*.json`, chọn
đúng biến thể theo cấu hình, tìm tệp cục bộ trước, chỉ tải thứ còn thiếu, và kéo
theo cả `preload_URLs` · `VAE_URLs` · LoRA đi kèm — những thứ **danh sách chép
tay của tôi đã bỏ sót**.

### WanGP tự chọn biến thể nào

`wgp.py:2618` — mặc định của chính nó:

```python
"transformer_quantization": "int8",
```

⇒ Mặc định WanGP tải **INT8**, tức **14,90 GB** mỗi tầng nhiễu.

⭐ Nên con số **66,58 GB** cho `t2v_2_2 + i2v_2_2` **không phải lựa chọn của
tôi** — nó là thứ WanGP tự làm khi không ai can thiệp. Đó đúng là điều chủ dự án
yêu cầu.

📌 Đổi sang bf16 vẫn làm được sau, **không cần tải lại từ đầu**: đó là khoá
`transformer_quantization` trong cùng tệp cấu hình.

### Hệ quả: tải model chạy trên chính Pod, không tách ra Pod CPU

Kế hoạch 6 bước trước tách **B4 (Pod CPU tải)** khỏi **B5 (Pod A100 đo)** để tiết
kiệm ~$0,50. Bỏ luôn bước tách đó: nó bắt ta tự dựng bảng kê, tức đánh đổi
**$0,50 lấy một lớp tự chế**. Sai hướng so với luật của phase này.

⇒ Một Pod A100, WanGP tự tải rồi tự chạy. Đắt thêm khoảng **$0,50**.

---

## 4. Cấu hình Pod — mọi trường đều có lý do

```python
{
  "name": "lttv-wangp-p01",
  "imageName": "<anh build tu Dockerfile cua WanGP>",
  "gpuTypeIds": ["NVIDIA A100-SXM4-80GB"],
  "gpuCount": 1,
  "dataCenterIds": ["US-KS-2"],       # PHAI ghim = DC cua volume
  "networkVolumeId": "uizchbiet5",
  "volumeMountPath": "/data",         # KHONG /workspace — xung dot ①
  "containerDiskInGb": 20,            # mac dinh 50, ha xuong
  "minRAMPerGPU": 64,                 # mac dinh 8 — qua it cho profile 1/2
  "minVCPUPerGPU": 8,
  "env": {"HF_HOME": "/data/hf"},     # xung dot ②
  "dockerStartCmd": ["--config", "/data/config", "--profile", "4"]
}
```

`dockerStartCmd` là **tham số cho `wgp.py`**, vì `entrypoint.sh` nối `$*` vào
sau `python3 wgp.py --listen`.

---

## 5. Thứ vẫn phải tự quyết — và vì sao không tránh được

| Việc | Vì sao WanGP không quyết hộ |
|---|---|
| Chọn A100 80 GB | WanGP chạy trên card nào cũng được; ràng buộc đến từ **volume ở `US-KS-2`** |
| `volumeMountPath = /data` | WanGP không biết gì về RunPod |
| `minRAMPerGPU = 64` | tham số của RunPod; WanGP chỉ nói profile 1/2 *cần* RAM |
| `containerDiskInGb = 20` | tham số của RunPod |
| Ghim SHA thượng nguồn | quyết định vận hành của ta |
| Chạy 1280×720 · 81 khung · 20 bước | **để so được với phép đo của V3** |

⭐ Sáu dòng. Trước lượt đọc mã này danh sách "tự quyết" dài gấp mấy lần — phần
lớn đã được thay bằng một cơ chế có sẵn.

---

## 6. Kế hoạch thực thi — bản rút gọn sau khi bỏ phần tự chế

| # | Việc | Máy | Tiền |
|---|---|---|---|
| B1 | ✅ **xong** — WanGP không dùng lại được tệp ComfyUI | máy A | $0 |
| B2 | ✅ **xong** — WanGP tự chọn INT8; không cần ta chốt bf16/INT8 | máy A | $0 |
| B3 | xoá 8 tệp ComfyUI khỏi volume qua S3 | máy A | $0 |
| B4 | tạo `/data/config/wgp_config.json` (`checkpoints_paths`) qua S3 | máy A | $0 |
| B5 | build ảnh từ `Dockerfile` **của WanGP** qua GitHub → RunPod | RunPod build | $0 |
| **B6** | **Pod A100**: WanGP tự tải model, rồi chạy ma trận đo | A100 | **~$2,70** |
| B7 | đọc kết quả qua S3 · xoá pod · `kiem-ke` phải trả `pods: []` | máy A | $0 |

**Tổng ~$2,70, trần cứng $6,00.**

Ma trận đo và sáu cái bẫy: `P01_KE_HOACH_THUC_THI.md` mục 5–6 — giữ nguyên,
chỉ bỏ phần Pod CPU riêng.

⛔ Điều kiện dừng không đổi: không thuê được GPU ở `US-KS-2` → dừng và báo, không
tự đổi sang card đắt hơn.
