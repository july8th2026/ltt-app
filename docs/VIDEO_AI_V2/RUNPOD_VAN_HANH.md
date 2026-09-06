# SỔ TAY VẬN HÀNH RUNPOD — để phiên sau không phải dò lại

Viết 2026-09-06. Mục đích: **mọi thứ cần để thao tác với RunPod nằm ở một chỗ**,
kèm đoạn mã chạy được. Phiên sau đọc tệp này thay vì thử từng đường dẫn.

⛔ **Tệp này chứa CÁCH LÀM, không chứa GIÁ TRỊ SỐNG.** Số dư, giá GPU, tồn kho
đều đổi hằng ngày — chúng có lệnh để hỏi, và lệnh nằm ở đây. Đừng chép số vào.

---

## 0. V3 đã ghi gì rồi — đọc trước, đừng viết lại

Trên nhánh `claude/ltt-video-ai-v3-p00-3f5713`, thư mục `docs/VIDEO_AI/`:

| Cần biết | Đọc ở |
|---|---|
| RunPod thu tiền ở **ba** chỗ; bảng giá **Serverless** đầy đủ | `VAN_HANH_MAY_C.md` §2 |
| Ba giai đoạn đều tính tiền; phép tính chọn `idleTimeout` | §3 |
| Từng tham số endpoint và **vì sao** đặt giá trị đó | §4 |
| Cái **không** mất tiền | §5 |
| Chọn datacenter bằng phép đo 11 DC × 8 GPU | §6 |
| Bẫy endpoint tự co lại khi để không | §7 |
| `GET /billing/endpoints` là nguồn chân lý về tiền | §8 |
| **23 đường dẫn REST**, không hơn | §9 |
| Cold start ~300 s và ba đường gỡ | `KE_HOACH_GO_COLD_START.md` |
| Chuỗi model và dung lượng từng mắt xích | `CHUOI_MODEL_VA_VAN_HANH.md` |

✅ Đối chiếu 06/09: §9 vẫn **đúng** — `openapi.json` hôm nay vẫn trả **23** đường.

⚠️ Nhánh đó **đã dừng phát triển** (`P00-D-07`) nhưng tài liệu vẫn đúng và vẫn là
nguồn. Đừng chép sang đây; đọc tại chỗ.

---

## 1. Bảy chỗ V3 KHÔNG ghi — đo và bổ sung 06/09

Đây là phần mới. Mỗi mục kèm cách kiểm lại.

### 1.1 🔑 Ổ đĩa mạng đọc/ghi được từ máy A qua S3 — KHÔNG cần GPU

Đây là năng lực quan trọng nhất mà không tài liệu nào nói tới, và nó đổi cách
thiết kế mọi phép đo: **đưa tệp lên ổ đĩa trước, rồi mới bật máy tính tiền.**

Khoá nằm ở `secrets/app.env` (cây V3): `RUNPOD_S3_ENDPOINT` ·
`RUNPOD_S3_REGION` · `RUNPOD_S3_ACCESS_KEY` · `RUNPOD_S3_SECRET_KEY`.
**Tên bucket = ID của volume.**

```python
import os, boto3
from botocore.config import Config
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["RUNPOD_S3_ENDPOINT"],
    region_name=os.environ["RUNPOD_S3_REGION"],      # trung voi dataCenterId
    aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
)
s3.list_objects_v2(Bucket="<volume_id>", MaxKeys=50)
s3.put_object(Bucket="<volume_id>", Key="x.json", Body=b"...")
s3.get_object(Bucket="<volume_id>", Key="x.json")["Body"].read()
s3.delete_object(Bucket="<volume_id>", Key="x.json")
```

✅ Kiểm 06/09: **liệt kê, ghi, đọc, xoá — cả bốn đều được.** `boto3` đã có sẵn
trên máy A (1.43.72).

⇒ Hệ quả vận hành: script đo, cấu hình, và **kết quả** đều để trên `/workspace`.
Pod xoá đi thì kết quả **vẫn còn**, và đọc về từ máy A không tốn một giây GPU.

### 1.2 `POST /pods` — trường nào có, và ba mặc định NGUY HIỂM

`required` là **rỗng** — API nhận hết mặc định, và mặc định không hợp với ta.

| Trường | Mặc định | Ghi chú |
|---|---|---|
| `imageName` | — | ảnh Docker khởi điểm |
| `gpuTypeIds` | — | mảng, ví dụ `["NVIDIA A100-SXM4-80GB"]` |
| `gpuCount` | 1 | |
| `dataCenterIds` | **cả 28 DC** | ⚠️ **phải ghim** về DC của volume, nếu không nó đặt chỗ nơi khác và **không gắn được ổ đĩa** |
| `networkVolumeId` | — | ID volume |
| `volumeMountPath` | `/workspace` | |
| `containerDiskInGb` | **50** | 🔴 tính tiền — đặt nhỏ nhất đủ dùng |
| `minRAMPerGPU` | **8** | 🔴 **quá ít cho WanGP profile 1/2** — hai hồ sơ đó giữ model không dùng ở **RAM**. Phải nâng. |
| `minVCPUPerGPU` | 2 | nâng nếu có giải nén/ffmpeg |
| `ports` | `8888/http,22/tcp` | 22 mở sẵn, nhưng xem 1.3 |
| `dockerStartCmd` | `[]` | 🔑 **chạy được script không cần shell** |
| `dockerEntrypoint` | `[]` | |
| `env` | `{}` | |
| `cloudType` | `SECURE` | |
| `interruptible` | `false` | bật thì rẻ hơn nhưng bị cắt ngang |
| `volumeInGb` | 20 | |

🔴 **`minRAMPerGPU = 8` là cái bẫy đắt nhất trong bảng này.** Toàn bộ lời giải
"đổi model không phải đọc lại ổ đĩa" của WanGP dựa vào RAM hệ thống. Để mặc định
là tự tay vô hiệu hoá nó, rồi đo ra một con số sai và tin nó.

### 1.3 ⛔ `/sshkeys` KHÔNG tồn tại trong REST

`GET /v1/sshkeys` trả **HTTP 400**. Khoá SSH là **thiết lập tài khoản trong
console**, không cấp qua API.

⇒ **Không thể dựng đường vào shell chỉ bằng khoá API.** Hai đường thật:

| | Cách | Ai làm |
|---|---|---|
| **A** | chạy **không cần người**: `dockerStartCmd` chạy script, kết quả ghi ra `/workspace`, đọc về qua S3 (1.1) | ✅ Claude, không cần ai |
| **B** | shell tương tác: chủ dự án dán **khoá công khai SSH** vào console RunPod một lần | 🔴 chủ dự án, ~2 phút, **$0** |

⭐ **Đường A rẻ hơn đường B** vì đồng hồ GPU chỉ chạy đúng lúc script chạy —
không có thời gian máy đứng chờ người gõ.

### 1.4 `_graphql()` của V3 ĐÃ bóc lớp `data`

`platform_core/video_gen/cloud_api.py::_graphql` trả về **phần trong** rồi.
Viết `d.get("data")` là ra `None`, và `None` đó trông y hệt *"tài khoản không có
GPU nào"*.

```python
d = api._graphql("query { gpuTypes { id displayName memoryInGb securePrice } }")
rows = d["gpuTypes"]          # DUNG
rows = d["data"]["gpuTypes"]  # SAI — ra None, va no im lang
```

*(Tôi đã sập đúng bẫy này 06/09 và suýt kết luận "0 loại GPU".)*

### 1.5 Hỏi giá + tồn kho GPU theo từng datacenter

GraphQL introspection đã tắt, nên đây là khuôn truy vấn đã kiểm chạy được:

```graphql
query {
  gpuTypes {
    id displayName memoryInGb securePrice
    lowestPrice(input: {gpuCount: 1, dataCenterId: "US-KS-2"}) {
      uninterruptablePrice
      stockStatus
    }
  }
}
```

- Bỏ `dataCenterId` để hỏi **toàn cầu**.
- `uninterruptablePrice` **rỗng** ⇒ loại GPU đó **không mua được lúc này**.
- `stockStatus`: `High` / `Medium` / `Low`.

⚠️ Giá này là **giá Pod**. Giá **Serverless** khác hẳn và nằm ở bảng của
`VAN_HANH_MAY_C.md` §2. Lẫn hai bảng chính là `V-017`.

### 1.6 Kiểm kê và đo tiền — dùng công cụ V3, đừng viết lại

Công cụ chỉ có trên nhánh V3; chạy **từ cây đó**:

```
python tools\video_cloud.py kiem-ke      # liet ke volume/endpoint/pod + tai nguyen mo coi
python tools\video_cloud.py trang-thai   # so du, muc chi, gio GPU mua duoc, cau dao
python tools\video_theo_doi.py tom-tat   # hoa don — chi tin dong `Hoa don`
```

`kiem-ke` cảnh báo tài nguyên **không mang tiền tố `lttv-`** — tức thứ đang tính
tiền mà không ai khai.

🔴 Hai bẫy đã trả giá:
- dòng `Muc chi` **mù trong lúc worker khởi động**, đúng giai đoạn đắt nhất;
- **hoá đơn trễ 20–60 phút** ⇒ con số cuối cùng phải đọc lại sau, đừng chốt ngay.

⚠️ Dòng *"Giờ GPU mua được"* chia cho hằng số giá **Serverless**. Thuê **Pod**
thì con số đó sai về phía **bi quan** khoảng 2 lần.

### 1.7 Volume `uizchbiet5` đang chứa gì — đo 06/09

10 đối tượng, **≈183,1 GB** (= 170,5 GiB):

| Tệp | GB |
|---|---:|
| `diffusion_models/wan2.2_{t2v,i2v,fun_control}_{high,low}_noise_14B` × 6 | 28,58 mỗi cái |
| `text_encoders/umt5_xxl_fp16.safetensors` | 11,37 |
| `vae/wan_2.1_vae.safetensors` | 0,25 |
| `_NAP_XONG.json`, `_NAP_TIEN_DO.json` | mốc nạp của V3 |

⭐ Cộng một chuỗi T2V: 28,58 × 2 + 11,37 + 0,25 = **68,78 GB** — **khớp chính
xác** con số cold start V3 đo. Hai nguồn độc lập, cùng một số.

⚠️ Bố cục thư mục là **của ComfyUI** (`diffusion_models/`, `text_encoders/`,
`vae/`). WanGP xếp model theo cách riêng ⇒ chưa chắc dùng lại được. **Đây là một
mục phải đo**, vì nó quyết định có phải tải lại 183 GB hay không.

---

## 2. Khuôn tạo Pod an toàn — dán và sửa

⛔ Bốn luật đi kèm, đã trả giá bằng tiền thật ở V3:

1. **Ghi ID vào sổ NGAY sau khi có `id`** — câu lệnh kế tiếp phải là ghi sổ,
   không được có `print` nào chen vào. V3 từng tạo pod thành công rồi chết ở
   dòng `print` kế tiếp vì stdout Windows là cp1252 ⇒ **một pod đang tính tiền
   mà không có trong sổ**.
2. **Tên phải mang tiền tố `lttv-`** để `kiem-ke` nhìn thấy.
3. **Ghim `dataCenterIds`** về đúng DC của volume.
4. **Hạ `containerDiskInGb`, nâng `minRAMPerGPU`.**

```python
than = {
    "name": "lttv-wangp-p01",
    "imageName": "<anh CUDA/PyTorch>",
    "gpuTypeIds": ["NVIDIA A100-SXM4-80GB"],
    "gpuCount": 1,
    "dataCenterIds": ["US-KS-2"],        # PHAI ghim = DC cua volume
    "networkVolumeId": "uizchbiet5",
    "volumeMountPath": "/workspace",
    "containerDiskInGb": 20,             # mac dinh 50 — ha xuong
    "minRAMPerGPU": 64,                  # mac dinh 8 — NANG LEN
    "minVCPUPerGPU": 8,
    "dockerStartCmd": ["bash", "-lc", "bash /workspace/lttv/chay_do.sh"],
    "env": {"LTTV_PHIEN": "p01"},
}
pod = api._rest("POST", "/pods", than)
ghi_so(pod["id"])                        # DONG NGAY SAU — khong chen gi vao giua
```

Vòng đời: `POST /pods/{id}/stop` (giữ máy, ngừng GPU) ·
`POST /pods/{id}/start` · `DELETE /pods/{id}` (xoá hẳn).

⚠️ **`stop` không phải `delete`.** Máy dừng vẫn có thể giữ ổ container. Muốn
chắc hết tốn thì `DELETE`, rồi **`kiem-ke` phải trả `pods: []`**.

---

## 3. Bảng tra nhanh

| Muốn gì | Làm gì |
|---|---|
| Có gì đang tính tiền không | `video_cloud.py kiem-ke` → `pods` phải rỗng |
| Số dư còn bao nhiêu | `video_cloud.py trang-thai` |
| Hoá đơn thật | `video_theo_doi.py tom-tat`, dòng `Hoa don`, chờ 20–60 phút |
| GPU nào mua được ở DC X | GraphQL ở 1.5 |
| Đưa tệp lên ổ đĩa | S3 ở 1.1 — **không cần GPU** |
| Lấy kết quả về sau khi xoá pod | S3 ở 1.1 — kết quả nằm trên `/workspace` |
| Chạy việc trên GPU không cần shell | `dockerStartCmd` ở 1.2 |
| Vào shell tương tác | chủ dự án dán khoá SSH vào console (1.3) |
| Danh sách đường dẫn REST | `VAN_HANH_MAY_C.md` §9 — vẫn đúng |

---

## 4. Điều tệ nhất có thể xảy ra, và cách chặn

| Rủi ro | Chặn bằng |
|---|---|
| Quên xoá pod → cháy tiền cả đêm | ghi sổ lúc tạo · `kiem-ke` sau khi xong · trần chi thoả thuận trước |
| Pod đặt nhầm DC → không gắn được ổ đĩa | ghim `dataCenterIds` |
| Đo ra số sai vì thiếu RAM | nâng `minRAMPerGPU` |
| Mất hết kết quả khi xoá pod | ghi mọi thứ vào `/workspace`, **không** vào ổ container |
| Đo lại lần hai vì thiếu số | dùng kế hoạch đo ở `P01_KE_HOACH_DO.md` |
| Số dư về $0 | **volume bị xoá vĩnh viễn** — sàn credit $31,50 là khoản không được tiêu |
