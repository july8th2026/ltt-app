# TÀI NGUYÊN CLOUD — DÙNG LẠI THẾ NÀO

Viết cho **phiên sau**. Đọc tệp này trước khi tạo bất cứ thứ gì trên RunPod —
phần lớn thứ bạn định tạo **đã có rồi**.

⛔ Đừng chép số tiền hay tồn kho vào đây. Chúng đổi hằng ngày và có lệnh để hỏi.

---

## 1. Ta đang sở hữu gì

| Tài nguyên | ID | Là gì | Tiền |
|---|---|---|---|
| Network volume | **`uizchbiet5`** (`lttv-models-v1`) | 300 GB, `US-KS-2`. **Chứa cả môi trường WanGP đã cài** | ~$21/tháng, chảy liên tục |
| Pod | **`bly29qwp5bum3r`** (`lttv-wangp-p01`) | A100 80 GB, mount `/data` | $1,59/giờ **khi RUNNING** |
| Endpoint Serverless | **`uwzftpd3utftfn`** (`lttv-worker`) | ảnh ComfyUI **của V3** — không dùng cho V2.1 | ~$0 (`workersMin=0`) |

### Trên volume có sẵn những gì

```
/data/Wan2GP/      ma nguon WanGP @ 1e1dd275... (v12.71)
/data/venv/        torch 2.10.0+cu128 · mmgp 3.7.14 · sageattention 2.2.0
/data/Wan2GP/ckpts/  ⭐ MODEL NAM O DAY — 44,8 GB, 113 tep (do 06/09)
/data/ckpts/         ⚠️ RONG. Toi tao nham; WanGP khong dung no
/data/hf/            ⚠️ RONG. HF_HOME co tro vao day nhung WanGP tai thang ve ckpts
/data/lttv/          script: cai_dat.sh · khoi_dong.sh · dich_vu_ccloud.py
/data/ket_qua/       ket qua do + log + vram*.csv
/data/config/        lttv_key.txt (khoa cau noi)
```

### Model thật sự gồm gì — đo, không ước

| Tệp | Cỡ |
|---|---|
| `wan2.2_text2video_14B_high_quanto_mbf16_int8` | **14,90 GB** |
| `wan2.2_text2video_14B_low_quanto_mbf16_int8` | **14,90 GB** |
| `umt5-xxl/…enc-quanto_int8` (text encoder) | 6,73 GB |
| `xlm-roberta-large/…clip…bf16` | 2,39 GB |
| `depth_anything_v2_vitl` · `sam_vit_h` | 1,34 + 1,28 GB |
| **tổng `ckpts/`** | **44,8 GB** |

⭐ Hai tệp 14,9 GB là **hai chuyên gia MoE** của Wan 2.2 (high-noise và
low-noise), không phải hai bản sao. `t2v_2_2.json` khai `URLs` và `URLs2` chính
là chúng, cộng `guidance_phases: 2` và `switch_threshold: 875` để đổi chuyên gia
giữa chừng.

🔴 Bản trước của tệp này ghi *"`/data/ckpts/` model WanGP tự tải về"* — **sai
hai lần**: model không ở `/data/ckpts/`, cũng không ở `/data/hf/`, mà ở
**`/data/Wan2GP/ckpts/`** (thư mục `ckpts` **bên trong kho**, đường tương đối từ
`cwd` của WanGP). Đừng suy vị trí model từ tên thư mục — đọc log nạp model.

🔑 **Cài đặt mất ~40 phút và phần lớn nằm trên volume — nhưng KHÔNG phải tất cả.**

### 🔴 Cài đặt trải trên HAI hệ tệp có tuổi thọ khác nhau

| Nửa | Ở đâu | Gồm gì | Sống bao lâu |
|---|---|---|---|
| **TẠM** | `/usr` — ổ container | `python3`, `ffmpeg`, `git`, `cmake` (apt) | **mất mỗi lần pod khởi động lại** |
| **BỀN** | `/data` — volume | venv, torch, WanGP, model | qua cả lần xoá pod |

Ảnh container là `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` — **không có
Python**. Python chỉ tồn tại vì `apt-get install` đặt nó vào nửa tạm. Mà
`venv/bin/python3` là symlink **tuyệt đối** tới `/usr/bin/python3` ⇒ nửa bền
**phụ thuộc** nửa tạm.

⛔ Mốc `_CAI_DAT_XONG` (bản cũ) nằm ở nửa bền nên nó khẳng định một tính chất mà
nó **chỉ nhìn thấy một nửa**. Pod khởi động lại → nửa tạm bay hơi → mốc vẫn còn
→ cổng bỏ qua cài đặt → `python` thành symlink treo, và bash báo dangling
symlink đúng bằng câu `No such file or directory`, nên lỗi **trông như venv bị
xoá** trong khi venv còn nguyên. Đã đốt một buổi ngày 06/09.

⇒ Mốc đã **bỏ hẳn**. `cai_dat.sh` nay có hai cổng, mỗi nửa một cổng, và cả hai
đều kiểm **thứ chạy được** (`command -v python3`, `-x venv/bin/python`,
`import torch, mmgp`) chứ không kiểm một tệp mốc.

---

## 2. Bật lại máy — ba lệnh

```powershell
cd D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-api-http-guide-a3e123
python tools\video_cloud.py kiem-ke      # pods phai RONG truoc khi bat dau
python tools\video_cloud.py trang-thai   # so du va cau dao
```

Rồi bật pod:

```python
api._rest("POST", "/pods/bly29qwp5bum3r/start")
```

⚠️ Khoá RunPod nằm ở `secrets/app.env` của **worktree V3**
(`ltt-llm-api-http-guide-a3e123`), không phải cây V2. Công cụ
`tools/video_cloud.py` và `platform_core/video_gen/cloud_api.py` cũng chỉ có ở
đó — `P00-D-04` cấm merge cả nhánh, nên lấy **từng tệp** nếu cần.

---

## 3. 🔴 Bài học đắt nhất: `gpuTypeIds` là MỘT DANH SÁCH ƯU TIÊN

Tài liệu V3 (`VAN_HANH_MAY_C.md` §4) đã ghi rõ:

> *"ưu tiên theo thứ tự. Dưới 5 worker, RunPod **luôn lấy loại ưu tiên cao nhất
> còn hàng** ⇒ H100 chỉ dùng khi A100 hết."*

Tôi tạo pod với **một** loại (`["NVIDIA A100-SXM4-80GB"]`), nên khi A100 hết là
kẹt cứng — thử 6 lượt đều `not enough free GPU`.

⇒ **Tạo pod/endpoint mới thì truyền cả danh sách**, xếp rẻ trước:

```python
"gpuTypeIds": ["NVIDIA A100-SXM4-80GB", "NVIDIA H100 PCIe", "NVIDIA H100 NVL"]
```

⛔ `PATCH /pods/{id}` **không nhận** `gpuTypeIds` — đã thử, trả 400 *"key
provided in request body which is not in input schema"*. Chỉ đặt được **lúc
tạo**. Muốn đổi danh sách ⇒ xoá pod, tạo lại (môi trường trên volume không mất).

---

## 3b. ⭐ `restart` KHÔNG nhả card — dùng nó, đừng `stop`/`start`

Đo ngày 06/09:

```python
api._rest("POST", "/pods/bly29qwp5bum3r/restart")   # 200, giu nguyen may
api._rest("POST", "/pods/bly29qwp5bum3r/reset")     # 200, tuong tu
```

Pod khởi động lại, nạp lại `dockerEntrypoint`, **giữ nguyên chỗ GPU đã thuê**.
Đây là cách đúng để nạp script mới lên pod đang chạy.

🔴 Trước khi biết đường này, tôi tưởng đổi script bắt buộc phải `stop` rồi
`start` — tức nhả card rồi cầu may thuê lại (§4). Sáu lượt thất bại ngày 06/09
là hệ quả của giả định đó, không phải của tồn kho.

---

## 4. ⚠️ `stop` nhả card, và có thể không lấy lại được

`US-KS-2` tồn kho thường xuyên **Low**. Ngày 06/09 tôi `stop` pod rồi **không
`start` lại được suốt hơn một giờ** — sáu lượt thử đều hết GPU, tới lượt thứ bảy
mới được.

| Muốn gì | Làm gì | Hệ quả |
|---|---|---|
| Ngừng tính tiền GPU **và chắc lấy lại được** | ❌ không có cách nào | tồn kho là của RunPod |
| Ngừng tính tiền GPU | `POST /pods/{id}/stop` | **nhả card**, có thể không thuê lại |
| Bỏ hẳn | `DELETE /pods/{id}` | mất pod, **môi trường trên volume vẫn còn** |

⇒ **Đang làm dở thì đừng `stop`.** Chi phí giữ máy chạy ($1,59/giờ) có thể rẻ
hơn việc mất nửa buổi chờ card.

---

## 5. Ba cái bẫy đã trả giá

**① `lowestPrice` báo có ≠ thuê được.** GraphQL trả giá $1,39 cho A100 trong khi
`POST /pods/{id}/start` vẫn `not enough free GPU`. Bảng giá là **chỉ dấu**, phép
thuê mới là sự thật.

**② Giá thật khác giá bảng.** `lowestPrice` nói $1,39; `costPerHr` lúc tạo pod
trả về **$1,59**. Dùng `costPerHr`, đừng dùng bảng.

**③ Ba mặc định nguy hiểm của `POST /pods`:**

| Trường | Mặc định | Vì sao phải đổi |
|---|---|---|
| `containerDiskInGb` | **50** | tính tiền; đặt **20** là đủ vì mọi thứ ở trên volume |
| `minRAMPerGPU` | **8** | quá ít cho `profile 1/2` của WanGP (giữ model ở RAM). Đặt **64** |
| `dataCenterIds` | **cả 28 DC** | không ghim ⇒ đặt nhầm nơi ⇒ **không gắn được volume** |

---

## 6. Đọc/ghi volume từ máy A — **không cần GPU**

Đây là năng lực quan trọng nhất và không tài liệu V3 nào nói tới.

```python
import os, boto3
from botocore.config import Config
s3 = boto3.client("s3",
    endpoint_url=os.environ["RUNPOD_S3_ENDPOINT"],
    region_name=os.environ["RUNPOD_S3_REGION"],      # = dataCenterId
    aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_KEY"],
    config=Config(signature_version="s3v4"))
# Ten bucket = ID volume
s3.list_objects_v2(Bucket="uizchbiet5", Prefix="ket_qua/")
```

Liệt kê · đọc · ghi · xoá — **cả bốn đều được**, đã kiểm.

⇒ Hệ quả vận hành: **đẩy script lên trước, rồi mới bật máy.** Kết quả cũng đọc
về theo đường này **sau khi pod đã xoá**.

⚠️ Lượt `list_objects_v2` có thể timeout khi pod đang ghi nặng vào volume. Đặt
`read_timeout` và bắt lỗi; đừng coi timeout là "không có gì".

---

## 6b. ⛔ Cổng mạng: chỉ **8888** gọi được từ ngoài

```
ports: ['8888/http', '22/tcp']      portMappings: {'22': 11191}
```

Cổng phải khai **lúc tạo pod**. Dịch vụ nghe ở cổng không khai vẫn chạy bình
thường, log vẫn sạch, và máy A vẫn không gọi tới được — hỏng mà **không để lại
dấu vết nào ở phía máy chủ**. Đường công khai:

```
https://<pod-id>-8888.proxy.runpod.net
```

⚠️ `22/tcp` có ánh xạ nhưng **chưa nạp khoá SSH** ⇒ chưa dùng được (xem §7).

### 🔴 Proxy RunPod nằm sau Cloudflare — `urllib` bị chặn thẳng

```
HTTP 403   error code: 1010        <- Cloudflare chan theo chu ky trinh duyet
```

Đo ngày 06/09: **bốn** biến thể header xác thực (`Authorization: Bearer`,
`x-runpod-api-key`, …) đều 403. Đổi **mỗi** `User-Agent` sang chuỗi của trình
duyệt thì **200 ngay**. `curl` không dính vì UA mặc định của nó không bị chặn.

⭐ Vì sao đây là kiểu hỏng khó lần nhất trong cả tuyến: dịch vụ **đang chạy
đúng**, log phía C-CLOUD **sạch không một dòng** — vì yêu cầu chưa từng tới nơi
— nên mọi bằng chứng ở phía máy chủ đều nói "không có gì sai". Chỉ có phía gọi
mới thấy.

⇒ `apps/lttvideo/wangp_client.py` gửi `UA_TRINH_DUYET` trên **mọi** lời gọi.

---

## 7. Chạy việc trên pod mà không cần shell

`/sshkeys` **không tồn tại** trong REST của RunPod (trả 400) ⇒ không dựng được
đường SSH chỉ bằng khoá API. Đường thay thế đã dùng và chạy được:

```python
"dockerEntrypoint": ["bash", "-lc", "bash /data/lttv/khoi_dong.sh"]
```

Pod boot → chạy script trên volume → ghi kết quả ra `/data/ket_qua/` → máy A đọc
về qua S3. Không cần người ngồi chờ.

⛔ **Ghi mọi thứ vào `/data`, đừng ghi vào ổ container** — ổ container biến mất
khi xoá pod.

---

## 8. Tiền — hỏi ở đâu

```powershell
python tools\video_cloud.py trang-thai   # so du · muc chi · cau dao
python tools\video_theo_doi.py tom-tat   # hoa don — chi tin dong `Hoa don`
```

🔴 Ba điều đã trả giá:
- dòng `Muc chi` **mù trong lúc worker khởi động** — đúng giai đoạn đắt nhất;
- **hoá đơn trễ 20–60 phút**, số cuối cùng phải đọc lại sau;
- dòng *"Giờ GPU mua được"* chia cho hằng số giá **Serverless** ($4,79/giờ). Thuê
  **Pod** thì con số đó sai về phía **bi quan ~3 lần**.

⛔ **Sàn credit $31,50**: số dư RunPod về $0 ⇒ RunPod **xoá volume, không khôi
phục được**. Đó là khoản không được tiêu.

---

## 9. Sau mỗi lượt — bốn bước, không bỏ bước nào

```
1. doc ket qua ve qua S3
2. POST /pods/{id}/stop   HOAC  DELETE /pods/{id}
3. video_cloud.py kiem-ke  ->  `pods` phai RONG
4. sau 20-60 phut: video_theo_doi.py tom-tat  -> doc hoa don that
```

⚠️ Bước 3 là bước hay bị bỏ nhất, và nó là bước duy nhất chứng minh máy đã tắt.

---

## 10. Nếu `US-KS-2` hết hàng lâu

Ba đường, xếp theo mức phá:

| | Đường | Đổi lại |
|---|---|---|
| ① | chờ, thử `start` lại theo giờ | $0, không hẹn được |
| ② | tạo pod mới với **cả danh sách** GPU (§3) | rơi xuống H100 $1,99–2,59/giờ |
| ③ | bỏ volume, dựng lại ở DC khác | mở ra card **$0,35/giờ**, nhưng **xoá 300 GB** và nạp lại model |

Đường ③ là thứ `O-007` dự đoán sẽ đáng làm, **nhưng nó phá tài nguyên** ⇒ phải
có chủ dự án duyệt.

⭐ Ngày 06/09 đường ① đủ: lượt `start` thứ bảy thành công sau hơn một giờ.
