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
/data/ckpts/       model WanGP tu tai ve
/data/lttv/        script: cai_dat.sh · khoi_dong.sh · do_luong*.py
/data/ket_qua/     ket qua do + log + vram*.csv
```

🔑 **Cài đặt mất ~40 phút và nó nằm trên volume.** `cai_dat.sh` có cổng bỏ qua:
thấy `/data/ket_qua/_CAI_DAT_XONG` là thoát ngay. ⇒ **Đừng cài lại.**

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
