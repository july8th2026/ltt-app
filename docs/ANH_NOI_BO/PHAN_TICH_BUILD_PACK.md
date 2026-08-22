# Phân tích bộ `flux2_klein9b_claude_build_pack`

**Đọc 2026-08-21.** Nguồn: `G:\My Drive\AI\A LTT AII\flux2_klein9b_claude_build_pack`
— 23 file, đọc hết. Tài liệu này chấm bộ pack đó: **giữ gì, bỏ gì, sửa gì**, và vì
sao. Kế hoạch thi hành nằm ở [`KE_HOACH_H37.md`](KE_HOACH_H37.md).

Bộ pack tự cho phép việc này. `START_HERE.md` §2 và §6 viết rõ: các đề xuất kỹ
thuật là **"gợi ý ưu tiên, không phải mệnh lệnh tuyệt đối"**, và khi tìm được
phương án tốt hơn thì phải *giải thích lý do → so sánh → chọn → ghi lại quyết
định*. Toàn bộ phần dưới đi theo đúng bốn bước đó.

---

## 1. Bộ pack làm đúng những gì

Đây là một bộ prompt được viết cẩn thận. Sáu nguyên tắc của nó tôi giữ nguyên,
không sửa một chữ:

| Nguyên tắc | Vì sao đáng giữ |
|---|---|
| **Không giả định phần cứng** — mọi thứ phải audit thật | Đã chứng minh là đúng ngay lập tức: pack ghi RAM 128 GB, máy thật có **192 GB**; CPU/OS pack để trống, thật là Xeon E5-2678 v3 + Win 11 Pro |
| **Không kết luận model fit 24 GB bằng lý thuyết — phải benchmark** | Đúng tuyệt đối. Xem §4 dưới: fp8 trên 3090 tiết kiệm VRAM nhưng **không** nhanh hơn, một kết luận chỉ đo mới ra |
| **Không hy sinh chất lượng trước khi đo** | Chống đúng cái bẫy "giảm precision cho chạy được" rồi bán ảnh xấu |
| **Không khoá sản phẩm vào một model** | Trùng với `providers.py` của nền tảng — hai bên gặp nhau ở cùng một kết luận |
| **Một GPU = concurrency 1** | Đúng, và đúng gấp đôi ở đây vì 3090 còn phải chia với việc video |
| **`DECISIONS.md`: Decision / Reason / Alternatives / Trade-off / Date** | Khuôn ghi quyết định chặt hơn cái repo này đang dùng cho quyết định cấp kỹ thuật. **Lấy** |

Và bốn bước phương pháp mà kế hoạch H37 bản đầu của tôi **thiếu** — pack đúng, tôi thiếu:

1. **Benchmark có kỷ luật** (bước 05): ≥30 prompt cố định, cùng seed, đo `model
   load` / `first latency` / `warm latency` / `peak VRAM` / `RAM` / `GPU util` /
   `temp` / `OOM rate`, gallery so sánh cạnh nhau, chọn theo **4 tiêu chí**
   (quality, latency, memory, stability). Bản của tôi có 20 prompt và ít chỉ số hơn.
2. **Stress test** (bước 14): 100 generation liên tục, đo **memory drift**, P95,
   jobs/hour, và thử đường hỏng (invalid image, OOM, restart queue/worker). Bản
   của tôi hoàn toàn không có. Rò rỉ bộ nhớ trong vòng lặp sinh ảnh là có thật.
3. **Benchmark edit/reference cụ thể** (bước 07): color change · clothing change ·
   background change · identity preservation · object edit · reference combination,
   kèm gallery before/after. Cụ thể hơn mô tả của tôi.
4. **Blind A/B với model thương mại** (bước 19): vote A/B/Tie **rồi mới lộ tên
   model**. Đây là cách duy nhất để chấm chất lượng mà không tự lừa mình.

Một câu trong bước 07 đáng in ra dán tường:

> *"Nếu một khả năng không đủ ổn định, ghi rõ thay vì che giấu bằng UI."*

---

## 2. Giả định của bộ pack **không còn đúng** với thực tế

Bộ pack được viết cho **một máy trống, chưa có sản phẩm nào**. Cả hai vế đều sai
với tình hình hiện tại, và đó là toàn bộ lý do phải viết lại kế hoạch chứ không
chạy tuần tự 20 bước.

### 2.1 Máy B không trống

| Pack giả định | Thực tế đo được trên `MAY-B` |
|---|---|
| Chưa có môi trường AI, bước 03 dựng Python/CUDA sạch | Đã có `E:\AI\venv`: Python 3.12.10, **torch 2.13.0+cu130**, CUDA khả dụng |
| Chưa có engine | Đã có **ComfyUI 0.30.0** (git `6f7cd7f`) đang chạy `127.0.0.1:8188` |
| Máy dành riêng cho hạng mục này | Đang giữ **342 GB model video** (Wan 2.1/2.2, VACE, Animate, Ovi, SeedVR2…) và một bộ công cụ vận hành hoàn chỉnh |
| RAM 128 GB | **192 GB** (118 GB rảnh) |
| CPU/OS "để audit" | Xeon E5-2678 v3 (2015, **PCIe 3.0**) · Windows 11 Pro |

Hệ quả trực tiếp: **bước 03 của pack, làm nguyên văn, là việc nguy hiểm.** "Chuẩn
hoá lại CUDA/Python" trên một máy đang có stack video chạy tốt là cách chắc chắn
nhất để đánh đổi một thứ đang chạy lấy một thứ chưa chạy. Chính pack cũng cấm điều
đó ở §6: *"không làm hỏng môi trường hiện tại"*. Hai câu này mâu thuẫn nhau, và
tôi chọn theo câu cấm.

→ **Sửa**: venv **riêng** cho cổng render (`E:\AI\ltt_render\venv`, chỉ
fastapi/uvicorn/httpx). Tuyệt đối không `pip install` gì vào `E:\AI\venv`.

### 2.2 Bạn đã có nền tảng — pack tưởng là chưa

Đây là phát hiện quan trọng nhất của cả bản phân tích.

Bộ pack dành **9 trong 20 bước** để dựng: API, job queue, database, storage,
history, web UI, security/auth, monitoring, service deployment, backup, và
(giai đoạn 3) authentication + quota + billing + object storage.

**LTTSTUDIOSAPP đã có tất cả những thứ đó, đang chạy thật, đang phục vụ khách trả
tiền.** Hàng đợi job (H2), sổ credit giữ-chỗ→quyết-toán→hoàn (H3), PostgreSQL 17,
R2 + presigned URL (H10), trang admin, thanh toán PayOS (H9), API công khai (H35),
giám sát + cảnh báo email, sao lưu, và cả `gpu_lease` nguyên tử để hai worker
không giành cùng một card.

Làm theo pack nguyên văn = **dựng nền tảng thứ hai bên cạnh nền tảng thứ nhất**.
Hai hàng đợi, hai sổ tiền, hai kho ảnh, hai chỗ đăng nhập. `CLAUDE.md` của repo
này cấm thẳng: *"đừng dựng hàng đợi, sổ tiền hay pool thứ hai"*.

→ **Sửa**: xem bảng ánh xạ §3. Khoảng **60 % khối lượng của pack được xoá** vì đã
có sẵn — đây là tin tốt, không phải tin xấu.

### 2.3 Pack không biết có hai máy

Không có một dòng nào về: máy nào giữ bí mật, cổng nào mở ra đâu, ai gọi ai. Với
kiến trúc hai máy thì đó là phần **quan trọng nhất**, vì ComfyUI không có xác thực
— mở nhầm một cổng là cho người lạ chạy mã tuỳ ý trên máy B.

→ **Bổ sung**: toàn bộ §2 và mục "Rủi ro" của `KE_HOACH_H37.md`.

### 2.4 Pack ngầm định engine là `diffusers`

Bước 03 liệt kê Diffusers/Transformers/Accelerate; bước 06 bảo tự viết *model
manager · inference service · memory monitor · config loader*; bước 02 bảo tự chọn
*BF16 + offload · quantization · sequential offload*.

Nhưng **ComfyUI đã làm sẵn toàn bộ những việc đó** và đang chạy trên chính máy đó.
Đây là một ngã ba thật, phải quyết dứt điểm — xem §5.

### 2.5 Pack coi đích đến là một web app riêng

Bước 10 vẽ ra trang Generate, trang Edit, Gallery, history, download, delete.
Bạn **đã có** những trang đó trong `apps/taoanh` và `apps/thumbnail`, kèm tài
khoản, credit và lịch sử.

→ **Sửa**: web UI của pack rút xuống thành **trang thử nghiệm nội bộ trên B** cho
việc chấm ảnh ở bước benchmark — và thậm chí có thể dùng thẳng giao diện ComfyUI
sẵn có. Nó **không bao giờ** ra Internet.

---

## 3. Bảng ánh xạ 20 bước của pack → việc thật

| # | Bước của pack | Phán quyết | Việc thật |
|---|---|---|---|
| 01 | Audit hệ thống | **✅ ĐÃ XONG** | Đã audit thật cả hai máy 2026-08-21. Còn thiếu 2 số: **PCIe link width** của 3090 và **tốc độ đĩa E:** — đã có sẵn `E:\AI\tools\pcie_check.py` |
| 02 | Kiến trúc + kế hoạch | **⚠️ THAY** | Kiến trúc đã chốt: B = provider nội bộ, không phải hệ thống độc lập. Xem `KE_HOACH_H37.md` §2 |
| 03 | Dựng môi trường AI | **⚠️ THU HẸP** | KHÔNG đụng `E:\AI\venv`. Chỉ tạo venv riêng cho cổng render. Giữ `diagnostics/gpu_check.py` của pack — nó rẻ và hữu ích |
| 04 | Baseline Klein 9B | **✅ GIỮ** | Giữ gần như nguyên vẹn. Đây là bước then chốt |
| 05 | Benchmark 3090 | **✅ GIỮ, NÂNG CẤP** | Giữ 30 prompt + 4 tiêu chí; thêm cột **license** và **giá điện/ảnh** |
| 06 | Inference engine | **⚠️ THAY** | ComfyUI đã là engine. Việc thật là viết **cổng render** bọc nó — mỏng hơn nhiều so với tự viết engine |
| 07 | Edit và reference | **✅ GIỮ** | Giữ nguyên bộ test. Khớp đúng ba chế độ bạn đã chốt |
| 08 | API + job queue | **⚠️ THU HẸP MẠNH** | Hàng đợi đã có ở máy A. Chỉ giữ phần **hợp đồng API** của cổng render. Không Redis, không Celery, không RQ |
| 09 | Database + storage | **❌ BỎ** | PostgreSQL + R2 + retention + orphan cleanup đã có và đang chạy |
| 10 | Web app | **⚠️ THU HẸP MẠNH** | Chỉ là trang chấm ảnh nội bộ trên B. Sản phẩm dùng giao diện đã có của nền tảng |
| 11 | Prompt intelligence | **⚠️ HOÃN + TÁI DÙNG** | Nền tảng đã có `prompt_fragments.py` và app agent. Mặc định **TẮT**; bật sau khi đo raw-vs-enhanced |
| 12 | Profiles và routing | **✅ GIỮ, MỞ RỘNG** | Giữ QUALITY/BALANCED/FAST. Mở rộng: định tuyến **local ↔ Gemini** bằng cascade sẵn có của `api_pool` |
| 13 | Security / privacy / license | **✅ GIỮ, ĐỔI TRỌNG TÂM** | Phần upload/CORS/rate-limit đã có ở A. Trọng tâm chuyển sang **bảo mật LAN hai máy** + **xác minh giấy phép Klein** |
| 14 | Stress test | **✅ GIỮ** | Giữ nguyên. Bản kế hoạch cũ của tôi thiếu bước này |
| 15 | Monitoring | **⚠️ THU HẸP** | Nền tảng đã có log/cảnh báo. Chỉ thêm: `/health` của cổng render + cảnh báo khi B chết |
| 16 | Service deployment | **✅ GIỮ, ĐỔI CÔNG CỤ** | Không systemd (Windows). Dùng **NSSM**, đúng khuôn `LTTStudioWeb/Worker` đang chạy trên A |
| 17 | Backup / recovery | **⚠️ THU HẸP** | Sao lưu đã có. Chỉ thêm: bảng kê model `(tên, nguồn, sha256)` để tải lại được |
| 18 | Final audit | **✅ GIỮ** | Giữ phân loại CRITICAL/HIGH/MEDIUM/OPTIONAL |
| 19 | Benchmark vs GPT Image 2 | **✅ GIỮ, ĐỔI ĐỐI CHỨNG** | Đối chứng chính phải là **Gemini 3 Pro Image / Flash Image** — thứ bạn đang bán. GPT Image 2 là phụ |
| 20 | Roadmap scale | **⚠️ THU HẸP** | Nền tảng đã có `LTT_WORKER_POOLS` + `gpu_lease`. Chỉ cần một trang roadmap ngắn |

**Tổng kết: giữ nguyên 7 bước · thu hẹp/thay 12 bước · bỏ hẳn 1 bước.**

---

## 4. Ba sự thật kỹ thuật mà bộ pack không thể biết

Đọc thẳng từ mã nguồn trên máy B, ngày 2026-08-21.

### 4.1 ComfyUI trên máy B **đã hỗ trợ FLUX.2 và Klein sẵn**

`E:\AI\ComfyUI\comfy\supported_models.py:794` — `class Flux2(Flux)` với
`image_model: "flux2"`, `latent_formats.Flux2`, `model_base.Flux2`. Kèm
`EmptyFlux2LatentImage` (latent **128 kênh**, chia 16) và `Flux2Scheduler` trong
`comfy_extras/nodes_flux.py`.

Nghĩa là: **không cần viết một dòng mã inference nào để chạy Klein.** Bước 04 và
06 của pack (baseline + engine) rút xuống còn "tải đúng file, dựng đúng workflow,
đo".

### 4.2 Klein dùng text encoder **Qwen3-4B**, không phải Mistral-24B

`clip_target()` của `Flux2` tự dò state-dict và rẽ ba nhánh:

| Khoá trong checkpoint | Tokenizer | Nghĩa |
|---|---|---|
| `qwen3_4b.transformer.` | `KleinTokenizer` | **Klein bản thường** |
| `qwen3_8b.transformer.` | `KleinTokenizer8B` | Klein bản TE lớn |
| `mistral3_24b.transformer.` | `Flux2Tokenizer` | FLUX.2 [dev]/[pro] — có cả cờ `pruned` |

Đây là tin tốt lớn nhất trong cả bản phân tích. Hôm qua tôi lo FLUX.2 không vừa
3090 vì text encoder 24B. Với Klein thì gánh nặng là **9B + 4B**, không phải
9B + 24B. Phép tính thô (phải đo lại):

| Cấu hình | DiT | TE | Đỉnh ước tính |
|---|---|---|---|
| bf16 toàn phần | ~18 GB | ~8 GB | ~21 GB — vừa 24 GB nhưng sát |
| fp8/GGUF-Q8 | ~9 GB | ~4 GB | ~13 GB — **giữ được cả hai thường trú** |

ComfyUI mã hoá văn bản trước rồi mới nạp DiT, nên đỉnh ≈ `max(TE, DiT + activation)`
chứ không phải tổng. Với 192 GB RAM, offload sang CPU gần như miễn phí về dung lượng
— chỉ tốn băng thông PCIe.

### 4.3 3090 **không có FP8 tensor core** — và điều đó đổi cách chọn profile

RTX 3090 là Ampere, compute capability **8.6** (đã xác nhận qua `/metrics/gpu`).
FP8 tensor core chỉ có từ Ada (8.9) trở lên. Nên trên máy này:

> **fp8 và GGUF là công cụ để VỪA VRAM, không phải để NHANH HƠN.**
> Trọng số lưu ở fp8/int nhưng phải giải nén về bf16 lúc tính — có khi còn chậm hơn bf16 thuần.

Đây chính là điều bước 05 của pack cảnh báo: *"Không dùng tính năng low-precision
chỉ vì nó mới nếu RTX 3090 không hỗ trợ hiệu quả."* Pack nói đúng nguyên tắc; ba
dòng trên là con số cụ thể để thi hành nguyên tắc đó.

**Hệ quả cho profile:** nếu bf16 vừa 24 GB thì bf16 vừa **đẹp nhất vừa nhanh nhất**
— và khi đó `QUALITY` với `BALANCED` sẽ **giống hệt nhau**. Pack đã lường trước:
*"Không tạo profile chỉ để marketing nếu config giống nhau."* Nên rất có thể kết
luận đúng là **hai profile, không phải ba**.

### 4.4 Còn hai số chưa đo, và chúng có thể đổi kết luận

- **PCIe link width của 3090.** Xeon E5-2678 v3 là PCIe **3.0**. Nếu card đang
  chạy x16 3.0 (~12 GB/s thực tế) thì offload TE mỗi job tốn ~1 giây — chấp nhận
  được. Nếu vì lý do nào đó nó đang chạy **x8 hoặc x4**, offload thành nút cổ chai
  và kết luận về profile đổi hẳn. Máy B đã có sẵn `E:\AI\tools\pcie_check.py`.
- **Tốc độ đọc đĩa E:.** Quyết định thời gian nạp nguội (18 GB weights). Trên NVMe
  ~15 s; trên HDD ~5 phút — và khi đó "giữ model thường trú" chuyển từ tối ưu hoá
  thành bắt buộc.

---

## 5. Ngã ba phải quyết: ComfyUI hay `diffusers`

Bộ pack ngầm định `diffusers`. Máy đã có ComfyUI. Đây là quyết định lớn nhất về
kỹ thuật, nên so sánh sòng phẳng:

| | **ComfyUI làm engine** | **Tự viết engine bằng `diffusers`** |
|---|---|---|
| Công phải bỏ ra | Đã cài, đã chạy, đã có model video dùng chung | Viết model manager, offload, VRAM guard, profile loader — đúng bước 06 của pack |
| Hỗ trợ Klein | **Có sẵn** (§4.1) | Phụ thuộc phiên bản `diffusers` có kịp không |
| Edit / reference | `ReferenceLatent` + `FluxKontextImageScale` có sẵn | Tự viết |
| ControlNet / IP-Adapter | `controlnet_aux` đã cài | Tự tích hợp |
| Lượng tử hoá | Node **GGUF đã cài** | Tự làm |
| Thêm model mới | Thêm **một file JSON** | Thêm **mã** |
| Tái lập kết quả (seed) | Tốt, nhưng phụ thuộc phiên bản ComfyUI | Kiểm soát tuyệt đối |
| Rủi ro lớn nhất | **Nâng cấp ComfyUI làm vỡ workflow JSON** (node đổi schema) | Tụt lại phía sau: model mới ra mà `diffusers` chưa đỡ |
| Bảo mật | Không có xác thực, chạy mã tuỳ ý qua custom node | Bề mặt nhỏ hơn nhiều |
| Mã trong tay ta | Ít — phần lớn là dữ liệu JSON | Nhiều — và phải tự bảo trì |

**Chọn: ComfyUI làm engine, bọc sau cổng render của ta.** Ba lý do:

1. Nó **đã chạy được Klein** trên chính máy đó. Tự viết `diffusers` là bỏ đi một
   thứ đang hoạt động để làm lại từ đầu — đúng phản nguyên tắc của pack.
2. Ba chế độ bạn cần (`edit`, `subject`, `structure`) đều đã có node sẵn. Tự viết
   là viết lại cả ba.
3. Máy B **cũng đang chạy video bằng ComfyUI**. Một engine cho cả hai nghĩa là một
   nơi để vá, một nơi để theo dõi VRAM, một nơi để tranh chấp GPU — thay vì hai.

**Ba điều kiện bắt buộc đi kèm**, vì rủi ro ở dòng "nâng cấp làm vỡ workflow" là thật:

- **Ghim commit ComfyUI** (`6f7cd7f`). Nâng cấp là một quyết định có chủ ý, có
  chạy lại test — không phải một lần `git pull` tiện tay.
- **Workflow JSON nằm trong repo, có phiên bản**, mỗi template một smoke test.
  Nâng ComfyUI mà template vỡ thì test đỏ **trước** khi khách gặp.
- **Cổng render giữ một lớp trừu tượng backend** (`backend: comfy | diffusers`).
  Hôm nay chỉ có `comfy`. Ngày nào ComfyUI cản đường, viết `diffusers` cho **một**
  model mà không phải động vào máy A. Đây chính là *"model abstraction"* mà pack
  đòi ở §3 — chỉ là đặt ranh giới ở chỗ khác: **ở hợp đồng API, không ở lớp Python**.

---

## 6. Điều bộ pack bỏ sót hoàn toàn: bài toán kinh tế

Cả 20 bước không có một dòng nào về **chi phí mỗi tấm ảnh**. Với một hệ thống
nghiên cứu thì không sao. Với hệ thống **bán theo credit** thì đó là con số quyết
định có nên làm hay không.

Ước tính thô để thấy độ lớn (phải thay bằng số đo thật ở bước benchmark):

| | Ảnh local (Klein trên 3090) | Ảnh qua Gemini (đang bán) |
|---|---|---|
| Chi phí biên | ~350 W × ~30 s ≈ 3 Wh ≈ **10–30 đồng** tiền điện | **500 – 1.600 đồng** (5–16 credit × 100 đ) |
| Trần công suất | Hàng đợi 1 job — khoảng **100–200 ảnh/giờ** | Gần như không trần, tuỳ hạn mức key |
| Rủi ro | Máy hỏng, model kém, giấy phép | Nhà cung cấp đổi giá, đổi model, khoá key |

Chênh lệch **một đến hai bậc độ lớn**. Nhưng nó chỉ thành lợi nhuận nếu chất
lượng đủ dùng — nên bước 19 (blind A/B) **không phải bước cuối cho vui**, nó là
bước quyết định **định giá và định tuyến**. Vì vậy trong kế hoạch thi hành, tôi
kéo nó lên sớm, ngay sau benchmark, và đổi đối chứng chính thành Gemini.

---

## 7. Bốn quyết định rút ra (khuôn của pack)

```
Decision:     Dùng ComfyUI làm engine, bọc sau cổng render tự viết.
Reason:       Đã cài sẵn, đã hỗ trợ Flux2/Klein ở cấp mã nguồn, đã có node edit/
              reference/ControlNet/GGUF. Tự viết diffusers là làm lại thứ đang chạy.
Alternatives: (a) tự viết engine diffusers theo bước 06 của pack;
              (b) dùng thẳng ComfyUI API, không bọc.
Trade-off:    Nhận rủi ro "nâng cấp ComfyUI làm vỡ workflow JSON" → chặn bằng ghim
              commit + smoke test cho từng template + lớp trừu tượng backend.
              Loại (b) vì ComfyUI không có xác thực và hàng đợi của nó là hàng đợi thứ hai.
Date:         2026-08-21
```

```
Decision:     KHÔNG dựng API/queue/DB/storage/web/billing riêng như bước 08–10, 17.
Reason:       LTTSTUDIOSAPP đã có tất cả, đang chạy thật, đang phục vụ khách trả tiền.
Alternatives: (a) làm theo pack nguyên văn; (b) làm riêng rồi hợp nhất sau.
Trade-off:    Máy B phụ thuộc máy A về mọi thứ ngoài GPU. Đổi lại: một sổ tiền,
              một hàng đợi, một kho ảnh, một chỗ đăng nhập. (b) bị loại vì
              "hợp nhất sau" trong thực tế nghĩa là không bao giờ hợp nhất.
Date:         2026-08-21
```

```
Decision:     Klein 9B là ứng viên số một, nhưng chưa phải quyết định cuối.
Reason:       ComfyUI trên B đã đỡ sẵn; TE là Qwen3-4B nên vừa 3090 thoải mái;
              là bản distilled nên ít bước → hợp với việc bán theo credit.
Alternatives: Qwen-Image + Qwen-Image-Edit (Apache-2.0, mạnh về chữ tiếng Việt);
              SDXL + IP-Adapter (nhẹ, rẻ); FLUX.2 [dev] (Mistral-24B — nặng).
Trade-off:    Phải XÁC MINH GIẤY PHÉP Klein trước khi mở bán. Nếu giấy phép không
              cho thương mại thì Qwen-Image lên thay ngay — kiến trúc không đổi.
Date:         2026-08-21
```

```
Decision:     Ba profile của pack rút xuống hai, cho tới khi số đo nói khác.
Reason:       3090 không có FP8 tensor core (SM 8.6), nên fp8/GGUF chỉ tiết kiệm
              VRAM chứ không tăng tốc. Nếu bf16 vừa 24 GB thì QUALITY và BALANCED
              trùng nhau về cấu hình.
Alternatives: Giữ đủ ba profile như pack gợi ý.
Trade-off:    Ít lựa chọn hơn cho người dùng — nhưng chính pack cấm tạo profile
              chỉ để marketing khi cấu hình giống nhau.
Date:         2026-08-21
```

---

## 8. Việc bộ pack yêu cầu mà tôi **chưa** làm, và vì sao

| Pack đòi | Trạng thái |
|---|---|
| `docs/SYSTEM_AUDIT.md` | Nội dung đã có trong `KE_HOACH_H37.md` §1, không tách file riêng để tránh hai chỗ ghi cùng một sự thật |
| `docs/DECISIONS.md` | Sẽ tạo tại `docs/ANH_NOI_BO/DECISIONS.md` khi thi hành. Bốn quyết định ở §7 là hạt giống |
| `diagnostics/gpu_check.py` | Chưa viết — thuộc giai đoạn 1 của kế hoạch thi hành |
| Đo PCIe link + tốc độ đĩa | **Chưa đo.** Ghi rõ ở §4.4 là số còn thiếu, không lấp bằng phỏng đoán |
| 12 file `docs/*.md` khác | Gộp lại còn 4 file, vì repo này đã có sẵn hệ tài liệu 3 tầng riêng |
