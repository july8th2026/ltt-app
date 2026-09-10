# KẾ HOẠCH GỠ COLD START — 300 giây nạp model mỗi lượt

> Chủ dự án 05/09/2026: *"Tại sao lại nạp qua network, ổ đĩa và card không cùng
> máy à mà cần network??? Nạp model mất nhiều time như thế mỗi lần tạo video tôi
> thấy quá sai quy trình nên check chuẩn vấn đề này."*

---

## 1. Chẩn đoán — anh nói đúng, và đây là vì sao

**Ổ đĩa và card KHÔNG cùng máy.** RunPod Serverless chạy worker trên một máy có
GPU; network volume là NVMe nằm ở **máy khác** trong cùng datacenter, nối qua
mạng.

| | Tốc độ | Nguồn |
|---|---|---|
| Network volume (Standard) | **200–400 MB/s** | `docs.runpod.io/serverless/storage/network-volumes` |
| NVMe cục bộ (để so sánh) | 3 000–7 000 MB/s | — |

68 GB ÷ 200–400 MB/s = **170–340 giây**. Đo được **~300 giây**.

⇒ Con số của ta **khớp giới hạn vật lý của kiến trúc đã chọn**. Không phải lỗi
cấu hình, không sửa được bằng tinh chỉnh — phải **đổi kiến trúc**.

Ở $4,79/giờ, mỗi cold start là **$0,40 chỉ để chép tệp**.

⛔ Và lỗi gốc là của tôi: `P05` nạp 170 GB lên network volume mà **chưa bao giờ
hỏi RunPod có sẵn cơ chế nào không**. Đúng lớp lỗi mà `V-011` sinh ra để chặn.

---

## 2. Ba đường, xếp theo GIÁ PHẢI TRẢ để thử

| | Đường | Cold start còn | Giá phải trả để thử |
|---|---|---|---|
| **③** | tăng `idleTimeout` | **0** *(chỉ khi job liên tiếp)* | **$0** — một lệnh `PATCH` |
| **②** | High-performance storage | ~100 s | tạo volume mới **+ nạp lại 170 GB** |
| **①** | kho HF riêng 68 GB + cached model | **vài giây** | upload 68 GB lên HF **+ đổi handler** |

⭐ **Luật thứ tự:** thử theo giá, không theo mức độ triệt để. ③ rẻ hơn hai đường
kia **hai bậc**; nếu nó đủ thì ① và ② thành thừa.

### ③ — tăng `idleTimeout` (đang đo)

`idleTimeout` hiện là **60 s**. Worker sống thêm bấy nhiêu sau mỗi job; job kế
tiếp trong cửa sổ đó **không cold start**.

⛔ **Nhưng có một mâu thuẫn phải giải trước.** `docs.runpod.io/serverless/pricing`
liệt kê **ba pha tính tiền**, pha ba là:

> *"**Idle timeout duration**: The time a worker remains active (running) after
> completing a request…"*

Tức tài liệu nói **idle CÓ tính tiền**. Nhưng đo 05/09 (7 mẫu / 12 phút, không
job nào): `ready=1 idle=1` mà `timeBilledMs` **không tăng một mili-giây**.

⭐ Hai điều này **không nhất thiết mâu thuẫn**: worker tôi đo đã qua 60 s từ lâu
(job xong 17:01, đo 18:45), nên nó ở trạng thái **FlashBoot giữ vỏ**, không phải
"idle đang đếm giờ".

⇒ `tools/video_do_idle.py` chạy một job `chi_kiem` (rẻ nhất, không sinh video)
rồi lấy mẫu **mỗi 15 giây** qua đúng cửa sổ 60 s.

**Quyết định theo kết quả:**
- Tăng > 5 000 ms ⇒ **idle có tính tiền** ⇒ ③ chết, đi ① hoặc ②.
- Không tăng ⇒ ③ sống, và nó **miễn phí**.

⚠️ **Giới hạn của ③ dù nó thắng:** nó chỉ xoá cold start **giữa các job liên
tiếp**. Khách dùng thật, rải rác trong ngày, vẫn cold start mỗi lần. Nên ③ là
**giảm đau**, không phải **chữa**.

### ② — High-performance storage

> *"up to 3x throughput and 4x IOPS"* · *"Cuts model load time from a central
> volume, lowering endpoint cold-start latency"*

300 s → **~100 s**. Nhưng **tier không đổi được tại chỗ**: phải tạo volume mới,
nạp lại 170 GB (bằng CPU pod như `P05`), rồi trỏ endpoint sang.

⚠️ `dataCenterId` cũng không sửa được — phải xác nhận **US-KS-2 có hỗ trợ tier
này** trước khi làm bất cứ gì.

### ① — kho HF riêng + cached model

Đường sạch nhất về nguyên lý:

> *"reduce cold start times to **just a few seconds**"*
> *"**You aren't billed for worker time while your model is being downloaded**"*

🔴 **Nhưng KHÔNG dùng được với kho hiện tại**, và tài liệu nói rõ vì sao:

> *"If a Hugging Face repository contains multiple quantization versions, the
> system currently **downloads all quantization versions**."*
> *"Each endpoint is currently limited to **one cached model** at a time."*

Đo kho thật:

| Kho | Số tệp | Tổng |
|---|---|---|
| `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` | 45 | **678,6 GB** |
| `Comfy-Org/Wan_2.1_ComfyUI_repackaged` | 38 | **454,0 GB** |

Ta cần **68 GB / 8 tệp**. Cached model sẽ kéo **1,1 TB**, và ta cần **hai** kho
(VAE nằm ở kho 2.1) trong khi mỗi endpoint chỉ được **một**.

⇒ Hai giới hạn, mỗi cái đủ để loại — **trừ khi ta tự dựng một kho HF chỉ chứa 8
tệp cần**. Wan2.2 là Apache-2.0 nên đăng lại hợp lệ.

**Việc phải làm cho ①:**
1. Tạo kho HF (riêng tư + token, hoặc công khai).
2. Đẩy 8 tệp — **nguồn hiện chỉ nằm trên network volume**, nên phải qua một CPU
   pod trong DC, giống `P05`.
3. Bật cached model cho endpoint (**console**; REST không có trường này).
4. Đổi `extra_model_paths.yaml` trỏ vào
   `/runpod-volume/huggingface-cache/hub/models--<org>--<ten>/snapshots/<hash>/`.
5. Giữ network volume thêm một thời gian làm đường lui, rồi mới thu.

---

## 3. Thứ tự triển khai

| Bước | Việc | Chi phí | Chặn bước sau? |
|---|---|---|---|
| **B1** | `video_do_idle.py` — idle có tính tiền không | **$0**¹ | ✅ quyết định ③ |
| **B2** | Nếu ③ sống: `PATCH idleTimeout` | **$0** | — |
| **B3** | Kiểm US-KS-2 có high-perf storage | **$0** | ✅ quyết định ② |
| **B4** | Quyết ① hay ② hay dừng ở ③ | **$0** | — |
| **B5** | Triển khai đường đã chọn | ①/② | — |

¹ B1 tốn một job `chi_kiem` (~$0,05) — rẻ hơn hai bậc so với thứ nó quyết định.

⛔ **Không làm B5 trước khi có B1 và B3.** Cả ① và ② đều đòi nạp lại 68–170 GB;
làm nhầm đường là mất một buổi và một khoản tiền không lấy lại được.

---

## 4. Điều phải nói thẳng về mức độ cấp bách

Cold start **không** nằm trên đường tới hạn của `P14a` (cổng thương mại) hay
`P09`/`P10`. Nó là **chi phí biến đổi trên mỗi job rời rạc**, và nó chỉ thành vấn
đề khi có khách thật dùng rải rác.

⇒ Nếu B1 cho thấy ③ đủ cho giai đoạn nội bộ, **hoãn ① và ② tới sau `P15`** và ghi
lại quyết định đó — thay vì tiêu một buổi nạp lại 170 GB cho một vấn đề chưa cắn.

---

## 5. Kết quả triển khai B1 và B3 — 05/09 chiều

### B1 · Idle có tính tiền không — **HAI PHÉP ĐO ĐỀU VÔ HIỆU**

| Cách | Kết quả | Vì sao vô hiệu |
|---|---|---|
| **Đo động** — lấy mẫu `timeBilledMs` mỗi 15 s qua 321 s | `+0 ms` ở cả 21 mẫu | Nó **không nhúc nhích kể cả khi `run=1`** — tức không cập nhật trong cửa sổ 5 phút |
| **Đo tĩnh** — trừ tổng job khỏi hoá đơn | chênh 2 405 s | `/requests` chỉ giữ **1 job**; thiếu 9 job kia ⇒ chênh là **ảo** |

⛔ **Cách thứ nhất là lỗi tôi tự gây.** Sáng cùng ngày tôi ghi *"hoá đơn tính bù
muộn"* vào `video_theo_doi.py`, rồi chiều dùng chính hoá đơn đó làm đồng hồ bấm
giây cho một cửa sổ 5 phút — **đo bằng cây thước mình vừa dán nhãn "chậm"**.

⭐ Còn lại một **lập luận gián tiếp**, và nó chỉ chứng minh được một nửa:

```
Worker `ready` ton tai it nhat : 6 gio = 21.600 giay
timeBilledMs THAT              :         2.425 giay  = 11%
```

⇒ Nếu `ready` tính tiền liên tục thì hoá đơn phải ~21 600 giây. Nó là 2 425.
**Không có chảy máu** — đủ chắc.
**Nhưng chưa đủ chắc** để kết luận *"tăng `idleTimeout` là miễn phí"*. Hai câu đó
khác nhau: câu đầu nói ta an toàn **bây giờ**; câu sau là cơ sở để **đổi cấu
hình**. Chỉ câu đầu được chứng minh.

**Phép đo đúng còn lại:** ghi mốc hoá đơn, **không chạy job nào trong ≥ 60 phút**,
đo lại. Mốc để phiên sau so:

```
MOC 05/09 ~18:55   timeBilledMs = 2 424 809 ms   amount = $3,2280
                   diskSpaceBilledGB = 380       worker ready=1 idle=1
```

### B3 · US-KS-2 có high-performance storage không — **KHÔNG KIỂM ĐƯỢC QUA API**

`GET /v1/datacenters` trả `400`. GraphQL `dataCenters{storageSupport}` có trả lời
— **US-KS-2 = `true`** — nhưng đó là *"DC có network volume"*, **không phải**
*"DC có tier high-performance"*.

Và schema REST không có chỗ để chọn tier:

```
NetworkVolumeCreateInput : dataCenterId · name · size      (het)
NetworkVolumeUpdateInput : name · size                      (het)
```

⇒ **High-performance volume chỉ tạo được qua console**, đúng như tài liệu mô tả
(*"look for the purple ⚡ icon"*). Không có đường API.

**Hệ quả cho đường ②:** phải mở console để biết US-KS-2 có hỗ trợ không, và nếu
có thì cũng phải tạo volume bằng tay. Không tự động hoá được.

---

## 6. Trạng thái ba đường sau B1 + B3

| | Đường | Trạng thái | Chặn bởi |
|---|---|---|---|
| **③** | tăng `idleTimeout` | ⏸ **chưa quyết được** | cần hoá đơn ổn định — mốc đã ghi ở §5 |
| **②** | high-perf storage | ⏸ **cần console** | không có API; chưa biết US-KS-2 có hỗ trợ |
| **①** | kho HF riêng 68 GB | ⏸ khả thi, đắt | upload 68 GB qua CPU pod trong DC |

⭐ **Không đường nào bị loại, và không đường nào sẵn sàng.** Đó là kết quả trung
thực của một buổi tra cứu — và nó vẫn hơn hẳn việc chọn bừa một đường rồi nạp
lại 170 GB.

## 7. Việc kế tiếp, theo đúng thứ tự giá

1. **$0** — để hoá đơn ổn định ≥ 60 phút, so với mốc §5 ⇒ chốt ③.
2. **$0** — mở console (cần đăng nhập lại phiên `runpod`), xem US-KS-2 có ⚡ không ⇒ chốt ②.
3. Chỉ khi ③ không đủ **và** có khách thật dùng rải rác: làm ① hoặc ②.

⛔ **Nhắc lại mức độ cấp bách:** cold start **không** chặn `P14a`, `P09`, `P10`.
Nó là chi phí biến đổi trên mỗi job rời rạc. Hoãn ① và ② tới sau `P15` là lựa
chọn hợp lý, miễn là ghi lại rằng ta hoãn **có ý thức**, không phải quên.

