# PHÂN TÍCH QUY TRÌNH XÂY DỰNG — WanGP trên hạ tầng RunPod V3 đã dựng

Viết 2026-09-06 theo yêu cầu chủ dự án: *"phân tích sâu sắc quy trình xây dựng
mới, mục tiêu hướng tới WanGP là sử dụng card dung lượng lớn, dùng qua RunPod mà
V3 đã dựng."*

⛔ Mọi bảng dưới đây đo từ **mã nguồn và API thật**, không từ tài liệu.

---

## 0. Kết luận trước, chứng minh sau

**V3 không xây một cỗ máy ComfyUI. V3 xây một đường ống chạy job GPU từ xa, và
ComfyUI chỉ là thứ ngồi bên trong nó.**

Pack V2.1 viết ra khi chưa biết đường ống đó tồn tại, nên nó mô tả P01 như *"từ
tài khoản trống"*. Thực tế: **7 trên 8 tầng đã có và dùng lại được**. Thứ phải
thay là **ruột của worker** — và thay xong nó **đơn giản đi**, không phức tạp lên.

---

## 1. Đường ống V3 — đo từ mã

```
A-CONTROL  platform_core/video_gen/dieu_phoi.py
    | POST https://api.runpod.ai/v2/{endpoint}/run
    | poll  /status/{jid}
    v
RunPod Serverless worker   video_gateway/handler.py
    | khoi dong ComfyUI (subprocess) tai 127.0.0.1:8188
    | doi /object_info san sang
    | LAM PHANG workflow UI -> API, doi chieu voi /object_info THAT   <-- luc KHOI DONG
    | nhan job: thay tham so -> POST /prompt -> cho -> tra tep
    v
model doc bang he thong tep tu /runpod-volume   (khong giu khoa S3)
```

### Phân định từng tầng

| # | Tầng | V3 đã có | WanGP cần | Phán quyết |
|---|---|---|---|---|
| 1 | Tài khoản RunPod · khoá · cầu dao ngân sách | `platform_core/video_gen/ngan_sach.py` | y hệt | ✅ **DÙNG LẠI** |
| 2 | Client cloud (REST + GraphQL) | `cloud_api.py` | y hệt | ✅ **DÙNG LẠI** |
| 3 | Công cụ vận hành: kiểm kê · dừng · hoá đơn | `video_cloud.py` · `video_theo_doi.py` | y hệt | ✅ **DÙNG LẠI** |
| 4 | Network volume 300 GB `US-KS-2` | `uizchbiet5` | **cùng ổ, khác nội dung** | ⚠️ **giữ ổ, nạp lại** |
| 5 | Đường build ảnh: GitHub → RunPod tự build | kho `lttvideo-worker`, endpoint `version` tự tăng | kho/nhánh mới, `Dockerfile` mới | ✅ **DÙNG LẠI KHUÔN** |
| 6 | Vận chuyển A-CONTROL ↔ worker | `/run` + `/status` (+ `/cancel`) | y hệt | ✅ **DÙNG LẠI** |
| 7 | Phân tích cold start | `KE_HOACH_GO_COLD_START.md` — đo thật | **cùng bài toán** | ✅ **DÙNG LẠI PHÉP ĐO** |
| 8 | **Ruột worker** | ComfyUI subprocess + làm phẳng đồ thị | **WanGP Python API in-process** | 🔴 **THAY** |

---

## 2. 🔴 Phát hiện quan trọng nhất: thay engine làm worker ĐƠN GIẢN ĐI

Đây là chỗ trực giác dễ sai. "Đổi engine" nghe như thêm việc. Đo thì ngược lại.

**Vì sao V3 phải viết nhiều đến thế:** ComfyUI là **một server HTTP**, và đồ thị
của nó có hai dạng (dạng UI người dùng lưu, dạng API máy gửi). Nên worker phải:

| Việc V3 buộc phải làm | Dòng |
|---|---:|
| `handler.py` — khởi động subprocess, chờ health, gọi `/prompt`, gom tệp | 626 |
| `lam_phang.py` — dịch đồ thị UI → đồ thị API | **462** |
| `ap_cau_hinh.py` — áp tham số lên đồ thị, đối chiếu `/object_info` | 254 |
| 3 tệp workflow JSON (t2v/i2v/v2v) | **8.960** |
| | **≈ 10.300** |

**WanGP không phải server, nó là THƯ VIỆN.** `docs/API.md` gọi `init(...)` là
*"the normal entrypoint for standalone / CLI-style third-party integrations"*:

```python
session = init(...)                     # nap runtime mot lan
job = session.submit_task(settings)     # settings la mot dict
job.cancel()                            # huy hop tac
```

⇒ Trong worker WanGP, **biến mất**: subprocess ComfyUI · chờ health · hop HTTP
nội bộ · làm phẳng đồ thị · đối chiếu `/object_info` · ba tệp JSON 8.960 dòng.

⭐ **~10.300 dòng dễ vỡ nhất của V3 đổi thành một lời gọi hàm.** Và không phải
tình cờ: `lam_phang.py` sinh ra vì ComfyUI **không có** hợp đồng API ổn định;
WanGP **có**.

### Cái mất đi khi bỏ ComfyUI

⚠️ Công bằng mà nói, không phải chỉ được: V3 để dành một ưu thế là ba mode chạy
với **0 gói custom node**. Đổi sang WanGP thì ta phụ thuộc vào tập model mà
WanGP hỗ trợ — rộng hơn (Wan 2.1/2.2, LTX-2, Qwen Image, Hunyuan, Flux) nhưng do
**thượng nguồn** quyết định, không do ta ghép đồ thị.

---

## 3. Card dung lượng lớn — và một ràng buộc đắt tiền ít ai thấy

Mục tiêu chủ dự án: **card VRAM lớn qua RunPod**. Ràng buộc thật:

**`dataCenterId` của volume KHÔNG sửa được.** Volume `uizchbiet5` ở `US-KS-2`.
Pod/worker muốn gắn nó thì **phải** ở đúng đó. Mà `US-KS-2` đo hôm nay chỉ còn:

| GPU | VRAM | $/giờ | Tồn kho |
|---|---:|---:|---|
| A100 SXM | 80 GB | **1,390** | Low |
| H100 NVL | 94 GB | 2,590 | Low |

Toàn cầu thì có 40/48 loại; **A40 48 GB $0,350** · RTX 4090 24 GB $0,340 ·
A5000 24 GB $0,160.

### 🔴 Cái ổ đĩa đang định giá con GPU

`V-008` đo Wan 2.2 fp16 720P đỉnh **59,8 GB** ⇒ cần lớp 80 GB ⇒ **A100 80GB là
đích, và cũng là lựa chọn rẻ nhất ở `US-KS-2`**. Tới đây mọi thứ hợp lý.

**Nhưng phép đo 59,8 GB đó là của ComfyUI, không phải của WanGP.** Toàn bộ lý do
WanGP tồn tại là *"for the GPU Poor"* — lượng tử hoá, offload, quản lý VRAM. Nếu
WanGP chạy được 720P trong **48 GB**, thì A40 ở datacenter khác rẻ hơn **4 lần**
($0,35 so với $1,39).

⇒ Khi đó bài toán đổi hẳn: **giữ volume $21/tháng để được dùng card đắt gấp 4**,
hay **bỏ volume, dựng lại ở DC rẻ**? Volume không di chuyển được, chỉ tạo mới.

⛔ **Đừng đoán con số này.** Nó phải là một phép đo của **P02** (VRAM đỉnh thật
của WanGP ở 720P), và nó là một trong những phép đo có đòn bẩy tiền lớn nhất của
cả chương trình. Ghi thành `O-006`.

---

## 4. Cold start — bài toán V3 đã đo, và WanGP thừa hưởng nguyên vẹn

`KE_HOACH_GO_COLD_START.md` đo thật:

```
68,78 GB doc tu network volume  =>  ~300 giay  =>  $0,13-0,26 moi lan khoi dong nguoi
```

Phép tính `idleTimeout` của V3 vẫn đúng nguyên: giữ ấm 1 giây $0,00076, khởi
động nguội $0,13–0,26 ⇒ **giữ ấm có lãi nếu job kế tiếp tới trong 171–342 giây**.
V3 chốt `idleTimeout = 60`.

⚠️ **Nhưng giới hạn V3 tự chỉ ra vẫn còn:** giữ ấm chỉ xoá cold start **giữa các
job liên tiếp**. Khách dùng rải rác trong ngày thì **lượt nào cũng nguội**.

Ba đường V3 xếp sẵn, và với WanGP thì thứ tự ưu tiên **đổi**:

| | Đường | Cold start | Với WanGP |
|---|---|---|---|
| ③ | tăng `idleTimeout` | xoá giữa các job liên tiếp | vẫn đúng, vẫn rẻ nhất để thử |
| ② | High-performance storage | ~100 s | phải tạo volume mới + nạp lại |
| ① | kho HF riêng + **cached model** của RunPod | **vài giây** | 🔴 **giờ hấp dẫn hơn hẳn** |

⭐ **Vì sao ① đổi thứ hạng:** với ComfyUI, model nằm ở layout riêng của ComfyUI
nên đẩy lên HF là việc thêm. WanGP **vốn đã tải model từ HuggingFace** — đó là
đường nạp tự nhiên của nó. Nên ① không còn là "đổi handler", nó gần như là
"để WanGP làm việc nó vẫn làm".

🔴 **Và ① có thể xoá luôn nhu cầu volume 300 GB** ⇒ tiết kiệm **$21/tháng vĩnh
viễn**, đồng thời **gỡ ràng buộc `US-KS-2`** ở mục 3 — tức mở đường dùng card rẻ
gấp 4. Hai vấn đề đắt nhất của chương trình có **chung một lời giải**.

⇒ Ghi thành `O-007`, đo ở **P02**, quyết ở **P08**.

---

## 5. Serverless hay Pod — hình dạng worker

| | **Serverless** (V3 đang dùng) | **Pod** |
|---|---|---|
| Rảnh thì tốn | **$0** (`workersMin=0`) | tính tiền liên tục |
| Cổng vào thường trực | ❌ không | ✅ có (WebUI, MCP) |
| Streaming tiến độ | có (`/stream`) | có |
| Huỷ | `/cancel/{id}` | trực tiếp |
| Hợp với | job sản xuất | **vận hành, gỡ lỗi, benchmark** |

**Kết luận: cả hai, mỗi cái một việc — và pack đã nói đúng điều này.**

- **Đường sản phẩm = Serverless.** `D-V2-003` nói WanGP WebUI không nằm trên
  đường người dùng; `dieu_phoi.py` của V3 đã nói đúng giao thức. Ghép lại:
  A-CONTROL → `/run` → worker → `session.submit_task()`. **Không cần MCP trên
  đường sản phẩm.**
- **Pod = bàn làm việc của người vận hành**, dựng lên khi cần rồi tắt: WebUI,
  Deepy, benchmark, và — quan trọng nhất — **soạn `Dockerfile`**.

### `O-001` gần như đã tự trả lời

Câu hỏi ban đầu là *"MCP trực tiếp hay cầu HTTP mỏng"*. Đo xong thì **cả hai đều
không phải**: đường sản phẩm không cần cầu mới, vì **RunPod Serverless CHÍNH LÀ
cầu**, và khoá endpoint chính là lớp xác thực mà MCP thiếu.

MCP vẫn có chỗ, nhưng là chỗ khác: **Deepy và agent**, chạy trên Pod vận hành.
Chốt chính thức ở P02 theo lịch.

---

## 6. Vì sao vẫn nên thuê Pod một lượt — lý do đắt hơn "để xem thử"

Không phải POC cho vui. **Phiên Pod tương tác là cách rẻ nhất để SOẠN ĐÚNG
`Dockerfile`.**

Đường còn lại là build ảnh mù rồi đẩy lên RunPod xem nó chết ở đâu — mỗi vòng
là một lần build + một lần khởi động tính tiền + không có shell để nhìn. V3 đã
trả học phí cho đúng chuyện này và tự viết ra bài học:

> *"Kiểm ở nơi nó sẽ chạy. Không dựng bậc kiểm trung gian ở máy A... Lượt khói
> trên cloud vừa chứng minh worker dựng được vừa bắt bẫy subgraph (`V-009`)."*

Trên Pod, trong một phiên có shell, ta làm được cả sáu việc cùng lúc:

1. cài WanGP tại SHA ghim trên **đúng nền Linux/CUDA sẽ chạy** → từng lệnh chạy
   được chính là từng dòng `Dockerfile`;
2. để WanGP tải model theo **layout của chính nó** vào volume;
3. mở WebUI riêng tư → nghiệm thu `private operator WebUI`;
4. gọi `submit_task` + `job.cancel()` → nghiệm thu progress/cancel;
5. `list_model_defs()` → **rút Verified Baseline Profile** (`D-V2-006`);
6. `nvidia-smi` lúc chạy → **đo VRAM đỉnh thật** → trả lời `O-006` ở mục 3.

⭐ Việc **6** một mình đã đáng tiền: nó quyết định ta trả $1,39 hay $0,35 mỗi giờ
cho mọi giờ GPU về sau.

---

## 7. Quy trình xây dựng đề xuất — bản viết lại theo thực tế

Pack giữ nguyên khung P01→P09; thứ đổi là **nội dung từng pha**, vì 7/8 tầng đã có.

| Pha | Pack viết | **Thực tế nên làm** | GPU |
|---|---|---|---|
| **P01** | dựng cloud từ tài khoản trống | ✅ ghim + giấy phép + kiểm kê **XONG**. Còn: **một phiên Pod** để soạn `Dockerfile` + rút baseline + **đo VRAM đỉnh** | ~2 h, **~$2,80** |
| **P02** | nghiệm thu engine | chạy đủ ma trận T2V/I2V/control trên **ảnh đã build**; chốt `O-006` (VRAM) và `O-007` (bỏ volume?) | thật sự tốn |
| **P03** | khoá một engine + điểm phục hồi | hợp đồng đã biết: `settings dict → submit_task`. Tag `video-legacy-final-pre-wangp` | 0 |
| **P04** | dựng app LTT + client | **dùng lại khuôn `dieu_phoi.py`**, đổi ruột. Không viết lại vận chuyển | 0 |
| **P05** | E2E thật + R2 + cancel | `/cancel` đã có sẵn ở tầng RunPod | ít |
| **P06** | cutover + xoá legacy | = **không merge** nhánh V3 (`P00-D-03`) + quyết số phận volume/endpoint cũ | 0 |
| **P07** | chất lượng + Deepy | dùng lại `KE_HOACH_DO_LUONG.md` (VBench) của V3 | thật sự tốn |
| **P08** | vòng đời cloud + chặn chi | dùng lại `ngan_sach.py` + cầu dao; áp kết quả `O-007` | ít |
| **P09** | E2E nội bộ cuối | | ít |

### Ba việc P01 còn nợ, xếp theo thứ tự

1. 🔴 **duyệt chi ~$2,80 (trần $5,00)** — chặn mọi thứ còn lại;
2. phiên Pod: sáu việc ở mục 6;
3. biến bản ghi phiên đó thành `Dockerfile` + kho ảnh (khuôn `lttvideo-worker`).

---

## 8. Câu hỏi mở mới sinh ra ở P01

| # | Câu hỏi | Đo ở | Đòn bẩy |
|---|---|---|---|
| **O-006** | VRAM đỉnh **thật của WanGP** ở 720P là bao nhiêu? | P01 phiên Pod → xác nhận P02 | 48 GB thì giờ GPU rẻ đi **4 lần** |
| **O-007** | Cached-model từ HF có xoá được cold start **và** nhu cầu volume không? | P02 | **$21/tháng** + gỡ khoá `US-KS-2` |
| **O-008** | Serverless giữ được `WanGPSession` ấm giữa các request tới mức nào? | P02 | quyết `idleTimeout` |

⛔ Cả ba đều là **phép đo**, không phải quyết định. Đừng chốt bằng suy luận.
