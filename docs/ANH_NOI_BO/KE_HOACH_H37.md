# H37 — Model tạo ảnh NỘI BỘ trên máy B (kế hoạch thi hành)

**Bản 2 — 2026-08-21.** Hợp nhất bộ `flux2_klein9b_claude_build_pack` với thực tế
hai máy và với nền tảng LTTSTUDIOSAPP đang chạy.
Phân tích bộ pack (giữ gì / bỏ gì / vì sao): [`PHAN_TICH_BUILD_PACK.md`](PHAN_TICH_BUILD_PACK.md).
**Máy B có chạy video** → chia GPU giữa hai loại việc: [`CHIA_GPU_VOI_VIDEO.md`](CHIA_GPU_VOI_VIDEO.md) (phụ lục bắt buộc).
**Bản thi hành từng bước, có cổng chấm điểm ≥ 9/10:** [`KE_HOACH_THI_HANH.md`](KE_HOACH_THI_HANH.md).

**Trạng thái: KẾ HOẠCH. Chưa tải model, chưa sửa mã, chưa đụng production.**

Mọi số về phần cứng là **đo thật** trên hai máy ngày 2026-08-21, không chép lại từ
tài liệu cũ. Chỗ nào chưa đo thì ghi rõ là chưa đo.

---

## 1. Hiện trạng đo được

| | **MÁY A** — `DESKTOP-H9AGFUQ` | **MÁY B** — `MAY-B` |
|---|---|---|
| LAN | 192.168.2.17 | 192.168.2.66 |
| Vai trò thật | **Production LTTSTUDIOSAPP** (`C:\LTTPlatform` có) | Máy dựng AI, không phục vụ khách |
| CPU | i9-10900K | Xeon E5-2678 v3 — 2015, **PCIe 3.0** |
| RAM | 32 GB | **192 GB** (118 GB rảnh) |
| GPU | 2× RTX 5060 Ti 16 GB | **RTX 3090 24 GB**, SM **8.6**, driver 610.88, idle 34 °C |
| Đĩa trống | C: 384 · D: 69 · G: 365 GB | C: 393 · **E: 341** · G: 374 · **H: 849** · I: 374 GB |
| Dịch vụ | LTTStudioWeb / Worker / Codex · postgresql-17 · NexusAgent/Controller | NexusAgent / Controller |
| Storage nền tảng | **R2** (`LTT_STORAGE=r2`) | — |

**Máy B đã là một máy ComfyUI hoàn chỉnh** — cắt bớt khoảng nửa khối lượng:

| | |
|---|---|
| `E:\AI\ComfyUI` | **v0.30.0**, git `6f7cd7f` (2026-08-05), đang chạy `127.0.0.1:8188`, `--cache-ram 24 64` |
| `E:\AI\venv` | Python 3.12.10 · **torch 2.13.0+cu130** · CUDA khả dụng |
| **Hỗ trợ FLUX.2 / Klein** | **CÓ SẴN** — `supported_models.py:794` `class Flux2(Flux)`; `EmptyFlux2LatentImage`; `Flux2Scheduler` |
| Text encoder Klein | tự dò: `qwen3_4b` → `KleinTokenizer` · `qwen3_8b` → `KleinTokenizer8B` · `mistral3_24b` → `Flux2Tokenizer` (đó là FLUX.2 [dev]) |
| Edit / reference | `ReferenceLatent` (`nodes_edit_model.py`) · `FluxKontextImageScale` · `FluxKontextMultiReferenceLatentMethod` |
| custom_nodes | KJNodes · WanVideoWrapper · **GGUF** · VideoHelperSuite · **controlnet_aux** · SAM2 · MMAudio · FrameInterpolation · Manager |
| Kho model | 342 GB — **toàn bộ là video**. `checkpoints/` chỉ có một file SAM. **Không có model ảnh nào** |
| Internet | có · SSH từ A: có (`~/.ssh/nexus_b`, user `lengo`) |

Ba thứ còn thiếu, cũng là lý do hạng mục này tồn tại:

1. **Không có model tạo ảnh.**
2. **ComfyUI chạy tay** — không service, không autostart, không firewall. Mất điện là mất.
3. **ComfyUI không có xác thực.** Đang an toàn vì chỉ nghe `127.0.0.1` — **phải giữ nguyên vĩnh viễn**.

**Hai số chưa đo** (giai đoạn 1 phải đo, đừng đoán): **PCIe link width** của 3090
(có sẵn `E:\AI\tools\pcie_check.py`) và **tốc độ đọc đĩa E:**. Nếu card đang chạy
x8/x4, hoặc E: là HDD, kết luận về profile và về "giữ model thường trú" đổi hẳn.

---

## 2. Kiến trúc (đề xuất **Q102**)

> **Máy B là một NHÀ CUNG CẤP API — không phải một phần của nền tảng.**
> Mã nguồn viết ở máy A, trong repo này. Model và dữ liệu nằm ở máy B.
> Máy B không biết CSDL, không biết credit, không biết người dùng, **không giữ một bí mật nào của nền tảng**.

```
Người dùng ─ Cloudflare ─► MÁY A (production)                LAN riêng        MÁY B (GPU)
                          ├─ web + hàng đợi job + sổ credit  ═══════════►  cổng render :8199
                          ├─ providers.py  + 1 dòng "ltt_image"            (FastAPI + bearer token,
                          ├─ platform_core/image_gen/  ◄─ adapter chung      service LTTRenderGateway)
                          └─ apps/taoanh · thumbnail · agent…                      │ loopback
                                    │                                              ▼
                                    └──► R2 ◄── presigned GET/PUT ───► ComfyUI :8188 (CHỈ 127.0.0.1)
```

### Vì sao không phải hai phương án kia

**Không chạy model trên máy A.** Card 3090 ở B. A chỉ có 2× 16 GB VRAM **và đang
phục vụ khách trả tiền** — web, worker, Postgres, sidecar Codex cùng chạy trên
32 GB RAM. Nạp model 20 GB vào đó là đem rủi ro OOM vào giữa job của khách.

**Không đem worker nền tảng sang B.** Cái giá: sao chép mã nguồn + venv sang máy
thứ hai, **bê khoá bí mật sang đó** (mật khẩu CSDL, khoá R2, `LTT_TOKEN_ENCRYPTION_KEY`),
mở cổng 5432 ra LAN, nuôi một đích deploy thứ hai. Đổi lại gần như không được gì,
vì storage đã là R2 nên A tự xử lý ảnh được.

### Vì sao là "provider", không phải "app", không phải "hệ thống riêng"

`platform_core/providers.py` đã chừa sẵn cửa này. Docstring của chính nó:

> *"Thêm loại API mới về sau = thêm MỘT dòng ở REGISTRY (+ tuỳ 1 adapter gọi HTTP),
> KHÔNG sửa app, KHÔNG sửa nơi khác."*

Nên đây **không phải** đổi hợp đồng nền tảng. Hệ quả đi kèm, miễn phí:

- **APIKEYS**: token cổng render cất như một API key thường (provider `ltt_image`,
  category `image`), mã hoá trong CSDL → thừa hưởng allocator, telemetry rpm/tpm,
  phân loại lỗi 401/429/5xx, cooldown, **và cascade đa-provider**.
- **Chọn model trong app**: sửa **một dòng** manifest —
  `providers: ["gemini"]` → `["gemini", "ltt_image"]`.
- **Định tuyến theo chi phí**: hết hạn mức Gemini → rơi sang model nhà, hoặc ngược
  lại. Cơ chế đã có ở `api_pool.chon_key(category=..., thu_tu_provider=[...])`.

### Chỗ hợp đồng đang thiếu — nói rõ theo `CLAUDE.md`

`providers.py` nói "tuỳ 1 adapter gọi HTTP" — **adapter đó chưa từng tồn tại**.
Thực tế: `apps/taoanh/jobs.py` và `apps/thumbnail/jobs.py` **mỗi nơi tự viết lại
lời gọi Gemini** (docstring của `taoanh/jobs.py` tự thừa nhận là "L2 copy"). Hai
bản sao của cùng một logic gọi API, lấy key, báo lỗi, tính tiền theo ảnh.

H37 thêm **`platform_core/image_gen/`** — adapter sinh ảnh dùng chung, dispatch
theo provider lấy từ REGISTRY:

```python
from platform_core import image_gen

anh = image_gen.generate(
    model="anh-tieu-chuan",     # id catalog, không phải tên model thật
    mode="edit",                 # t2i | edit | subject | structure
    prompt="...", refs=[storage_key, ...],
    aspect="16:9", n=2, seed=None, profile="quality",
    job_id=ctx.job_id,           # idempotency
)                                # -> [StoredFile] đã nằm trên R2
```

Đây là **thêm** module vào `platform_core`, không sửa hợp đồng app. Nhưng nói
thẳng: đúng ra nó phải có từ H5, và việc nó không có là lý do hôm nay có hai bản
sao Gemini. H37 trả món nợ đó **từng phần** — giai đoạn đầu adapter **chỉ** phục
vụ `ltt_image`, đường Gemini đang phục vụ khách **không bị đụng một dòng nào**.

---

## 3. Hợp đồng cổng render

Mã nguồn nằm trong repo này, thư mục `render_gateway/` ở gốc — **cùng khuôn với
`codex_sidecar/` đã có và đang chạy**. Viết ở A, test ở A trong gate, deploy sang
B bằng script. B không có "mã nguồn của riêng nó" để mà lệch phiên bản.

### Endpoint

| Method | Đường | Việc |
|---|---|---|
| `GET` | `/health` | GPU · VRAM trống · ComfyUI sống không · độ dài hàng đợi · model đang nạp · phiên bản gateway |
| `GET` | `/v1/models` | Model + profile + chế độ mỗi model đỡ được |
| `POST` | `/v1/images/generations` | Nhận việc, trả `{job_id}` **ngay** |
| `GET` | `/v1/jobs/{id}` | `queued`/`preparing`/`generating`/`saving`/`succeeded`/`failed`/`cancelled` + tiến độ |
| `POST` | `/v1/jobs/{id}/cancel` | Huỷ |

Trạng thái job lấy đúng bộ của bước 08 trong pack — không phát minh tên mới.

**Async submit → poll.** Không phải vì trần 100 giây của Cloudflare (job đã chạy
nền), mà vì sinh ảnh mất 5–60 giây và một kết nối HTTP giữ mở lâu vậy qua LAN là
thứ đứt lặng lẽ. Khuôn này nền tảng đã dùng cho video (`Provider.async_poll=True`
của `byteplus`, `plenx`) — đi theo, đừng phát minh lại.

### Thân yêu cầu

```json
{ "model": "klein-9b", "profile": "quality", "mode": "edit",
  "prompt": "...", "negative_prompt": "",
  "refs": [{"url": "https://<presigned GET R2>", "role": "edit"}],
  "output": {"put_urls": ["https://<presigned PUT R2>"], "keys": ["..."]},
  "aspect": "16:9", "n": 1, "seed": null, "steps": null, "guidance": null,
  "idempotency_key": "job:<job_id>" }
```

Ba điểm phải quyết đúng ngay, vì sửa sau rất đắt:

1. **Ảnh vào bằng presigned URL, không base64.** Base64 phồng 33 %; tám ảnh 8 MB
   thành ~85 MB nhồi vào một thân JSON. B có Internet nên tải thẳng từ R2. Chỉ cho
   base64 khi ảnh ≤ 2 MB, làm đường lui.
2. **Ảnh ra bằng presigned PUT, B đẩy thẳng lên R2.** Không cần khoá R2 trên B, và
   A không phải trung chuyển từng byte. `Storage.upload_target()` đã có từ H10/P1 —
   dùng lại. Đường lui: A kéo về qua `/v1/files/{token}`.
3. **`idempotency_key` là `job_id` của nền tảng.** Worker chết rồi job chạy lại thì
   cổng trả **đúng kết quả cũ**, không vẽ lần hai. Không có nó, một lần retry là
   một lần đốt GPU và có thể một lần tính tiền.

### Chỉ MỘT hàng đợi

ComfyUI có hàng đợi riêng. **Không dùng nó.** Cổng render nhận tối đa `N` việc
song song (`N=1` mặc định, theo đúng khuyến nghị "một GPU = concurrency 1" của
pack), quá thì trả **429 + `Retry-After`**, và A giữ việc trong hàng đợi của mình.
Lý do: trạng thái job phải nằm trong CSDL của A — để phình ở ComfyUI là có hai
nguồn chân lý, và cái thứ hai biến mất mỗi lần B khởi động lại.

### Chính sách hỏng (bước 06 + `ARCHITECTURE_LOGIC.md` §G của pack)

Phân biệt và trả mã lỗi khác nhau cho: yêu cầu sai · ảnh tham chiếu hỏng · ComfyUI
không phản hồi · model nạp lỗi · **OOM** · quá giờ · lỗi đẩy R2. Với OOM: ghi
metric, `torch.cuda.empty_cache()` qua ComfyUI, đánh dấu job hỏng, **không** tự
thử lại vô hạn — tối đa một lần thử lại với profile tiết kiệm hơn, rồi dừng.

---

## 4. Bố cục trên máy B

Giữ nguyên `E:\AI` đang chạy tốt. Thêm một nhánh riêng:

```
E:\AI\
├── ComfyUI\            GIỮ NGUYÊN — chỉ nghe 127.0.0.1:8188 · ghim commit 6f7cd7f
├── venv\               GIỮ NGUYÊN — TUYỆT ĐỐI không pip install gì vào đây
├── models\             kho chung, extra_model_paths.yaml đã trỏ tới
│   ├── diffusion_models\   ← model ẢNH tải mới, cạnh model video
│   ├── text_encoders\      ← qwen3_4b cho Klein
│   ├── vae\  loras\  controlnet\  clip_vision\
│   └── ipadapter\          ← chỉ tạo nếu chọn hướng IP-Adapter cho chế độ `subject`
└── ltt_render\         ← MỚI — toàn bộ H37 nằm gọn trong đây
    ├── gateway\        mã cổng render (deploy từ repo, KHÔNG sửa tay tại chỗ)
    ├── venv\           venv RIÊNG: fastapi · uvicorn · httpx · pillow
    ├── workflows\      *.json — mỗi (model × chế độ × profile) một template
    ├── bench\          bộ prompt chuẩn · kết quả · gallery so sánh
    ├── work\           ảnh tham chiếu tải về + ảnh ra — tự xoá sau 24 h
    ├── logs\           gateway.log · comfy_run.log — xoay vòng, chặn trần dung lượng
    └── scripts\        cai_dat.ps1 · tai_model.ps1 · kiem_tra.ps1 · pcie_check
```

**Nếu E: xuống dưới 100 GB trống**, thêm base path thứ hai trỏ sang `H:\` (849 GB)
trong `extra_model_paths.yaml` — ComfyUI đỡ nhiều base path. Đừng dời cả kho.

**Model là dữ liệu, không phải mã**: không commit, không sao lưu vào git. Ghi vào
`.gitignore`, và `tai_model.ps1` giữ bảng kê `(tên file, nguồn, sha256, ngày)` để
tải lại được từ đầu bằng một lệnh — đúng ý bước 17 của pack.

---

## 5. Model — ĐÃ CHỐT LẠI SAU G2

> ⛔ **Cập nhật 2026-08-21 sau khi G2 xác minh giấy phép.**
> **FLUX.2 Klein 9B mang FLUX Non-Commercial License v2.1 — KHÔNG bán ảnh được.**
> Chỉ bản **4B** là Apache 2.0.
>
> **Và sau khi nghiên cứu tiếp (D-009), model đích KHÔNG phải Qwen mà là:**
>
> | Vai | Model | Giấy phép |
> |---|---|---|
> | **Model đích** | **HiDream-O1-Image** ~8B | **MIT** |
> | Đối chứng | Qwen-Image-2512 · Qwen-Image-Edit-2511 · Klein 4B | Apache 2.0 |
> | Thước đo trần — **chỉ để đo** | FLUX.2 Klein 9B | NC v2.1 ⛔ |
>
> Bốn lý do: Elo sửa ảnh **1191** (cao nhất nhóm trọng số mở; Klein 9B 1165, Qwen
> Edit 2511 1165) · giấy phép **MIT** · **một model phủ cả bốn chế độ** · và nó
> **chính là Qwen3-VL-8B** cải biên thành DiT pixel-space, trong khi mọi bản
> Qwen-Image trọng số mở vẫn dùng Qwen2.5-VL.
>
> **Cấu hình sản phẩm** (D-010, chất lượng trên hết): `base` bf16, sinh ở bucket
> huấn luyện **~4 MP** (16:9 → **2560×1440**) rồi thu nhỏ về kích thước giao hàng.
> **Chỉ một file checkpoint, không có text encoder rời.**
>
> Chứng cứ, trích dẫn và nguồn: [`LICENSE_NOTES.md`](LICENSE_NOTES.md) ·
> quyết định: `DECISIONS.md` **D-008 → D-009 → D-010**.
>
> **Phần §5 dưới đây giữ nguyên để truy nguồn.** Phép tính VRAM của nó là cho
> Klein 9B + Qwen3-4B và **không dùng lại được** cho Qwen-Image — text encoder của
> Qwen-Image là **Qwen2.5-VL-7B**, phải đo lại từ đầu ở G4.
>
> **Kiến trúc không đổi một dòng nào** khi đổi model. Đó là lần thử thật đầu tiên
> của nguyên tắc model-agnostic ở §2, và nó đứng vững.

### Vì sao Klein đứng đầu *(bản trước G2 — đã lỗi thời)*

| Bằng chứng | Nguồn |
|---|---|
| ComfyUI trên B **đã đỡ sẵn** `flux2` | `comfy/supported_models.py:794` |
| Klein dùng TE **Qwen3-4B**, không phải Mistral-24B | `clip_target()` dò `qwen3_4b.transformer.` → `KleinTokenizer` |
| Là bản distilled → ít bước → hợp bán theo credit | thiết kế của dòng Klein |
| Edit/reference có node sẵn | `ReferenceLatent`, `FluxKontextImageScale` |

Phép tính VRAM thô (**phải đo lại ở giai đoạn 4**) — ComfyUI mã hoá văn bản trước
rồi mới nạp DiT, nên đỉnh ≈ `max(TE, DiT + activation)` chứ không phải tổng:

| Cấu hình | DiT 9B | TE Qwen3-4B | Đỉnh ước tính |
|---|---|---|---|
| bf16 toàn phần | ~18 GB | ~8 GB | **~21 GB** — vừa 24 GB nhưng sát |
| fp8 / GGUF-Q8 | ~9 GB | ~4 GB | **~13 GB** — giữ được cả hai thường trú |

### Điều phải nhớ khi chọn profile: 3090 KHÔNG có FP8 tensor core

RTX 3090 là Ampere, compute capability **8.6** (xác nhận qua `/metrics/gpu`). FP8
tensor core chỉ có từ Ada (8.9). Nên trên máy này:

> **fp8 và GGUF là công cụ để VỪA VRAM, không phải để NHANH HƠN.** Trọng số lưu
> fp8/int nhưng phải giải nén về bf16 lúc tính — có khi còn chậm hơn bf16 thuần.

Đúng cảnh báo của bước 05 trong pack. Hệ quả: **nếu bf16 vừa 24 GB thì bf16 vừa
đẹp nhất vừa nhanh nhất**, và khi đó `QUALITY` với `BALANCED` trùng nhau — pack đã
cấm tạo profile chỉ để marketing. Rất có thể kết luận đúng là **hai profile**:

- `QUALITY` — bf16, nhiều bước, dùng khi khách chọn bậc cao
- `FAST` — fp8/GGUF, ít bước, hoặc một model nhẹ hơn hẳn

### Ứng viên dự phòng — và cảnh báo phải đọc

ComfyUI 0.30 trên B khai báo đỡ hàng loạt kiến trúc mà **tôi chưa xác minh**:
`krea2`, `joyimage`, `ideogram4`, `mage_flow`, `pixeldit`, `anima`, `boogu`,
`ernie`, `lens`, `hidream`, `chroma`, `omnigen`, `qwen_image`. Việc đầu tiên của
giai đoạn 3 là **đọc `comfy/ldm/*` và trang model gốc để lập bảng thật**, không
chép bảng dưới đây.

| Ứng viên | Giấy phép | VRAM 3090 | Vì sao trong danh sách |
|---|---|---|---|
| **FLUX.2 Klein 9B** | **PHẢI XÁC MINH** ⚠️ | thoải mái | Ưu tiên số một; ComfyUI đã đỡ sẵn |
| Qwen-Image + Qwen-Image-Edit | Apache-2.0 → bán được | fp8 ~20 GB sát trần; GGUF thoải mái | Chữ tiếng Việt tốt nhất nhóm; Edit đỡ nhiều ảnh tham chiếu → phủ cả `edit` lẫn `subject`. **Phương án thay thế nếu Klein vướng giấy phép** |
| FLUX.2 [dev] | Non-Commercial ⚠️ | TE Mistral-24B — rất nặng | Chỉ để đối chứng chất lượng, không để bán |
| SDXL + IP-Adapter + ControlNet | OpenRAIL++ → bán được | ~7 GB | Bậc FAST rẻ; phủ `subject`+`structure` tốt nhất; kho LoRA khổng lồ |

**Giấy phép là tiêu chí LOẠI TRỪ, không phải cộng điểm.** Bạn bán dịch vụ này lấy
credit. Bước 13 của pack nói đúng: *"không kết luận commercial-use nếu chưa xác
minh"*. Việc xác minh giấy phép Klein là **cổng chặn của giai đoạn 3** — chưa xong
thì không tải, không đo, không xây tiếp.

---

## 6. Bốn chế độ phải chạy được

| Chế độ | Nghĩa | Đường thi hành trên ComfyUI |
|---|---|---|
| `t2i` | Thuần prompt | `UNETLoader` → `CLIPLoader(klein)` → `CLIPTextEncode` → `EmptyFlux2LatentImage` → sampler → `VAEDecode` |
| `edit` | 1 ảnh + câu lệnh: "đổi nền thành bãi biển", "xoá người bên trái" | thêm `LoadImage` → `FluxKontextImageScale` → `VAEEncode` → **`ReferenceLatent`** vào conditioning |
| `subject` | Giữ đúng khuôn mặt / đúng sản phẩm ở bối cảnh mới | nhiều `ReferenceLatent` nối chuỗi (+ `FluxKontextMultiReferenceLatentMethod`); nếu model không đủ → IP-Adapter |
| `structure` | Giữ bố cục / tư thế, thay phong cách | ⚠️ **HiDream-O1 KHÔNG có ControlNet** (đã grep, không dòng nào). G5 thử bằng `edit` + lời nhắc; không đạt thì **ghi rõ là không bán được** hoặc thêm Qwen-Image-Edit-2511 riêng cho chế độ này — xem **D-017** |

Sơ đồ node trên là **phác thảo**, phải xác minh bằng cách chạy thật ở giai đoạn 4.
Không có template chính thức nào kèm theo gói `comfyui_workflow_templates` đã cài
(đã kiểm: 0 file JSON) — nên workflow là tài sản ta tự viết và tự giữ phiên bản.

---

## 7. Mười một giai đoạn thi hành

Nguyên tắc xuyên suốt: **đường Gemini đang phục vụ khách không bị đụng tới** cho
tới khi đường nội bộ đã chạy ổn định. Món nợ gộp hai bản sao Gemini trả sau, ở G11.

### G1 — Đo nốt hai số còn thiếu · *nửa buổi* · **không đụng gì**

Chạy `E:\AI\tools\pcie_check.py`; đo tốc độ đọc tuần tự của E:; viết
`ltt_render/scripts/gpu_check.py` theo bước 03 của pack (tên GPU, VRAM, CUDA, torch,
compute capability, khả năng BF16/FP16, **một phép tensor thật**, cấp phát/giải phóng).

**Xong =** một bảng có PCIe link width, băng thông đĩa, và một phép tính CUDA thật
chạy được. Nếu PCIe là x8/x4 hoặc E: là HDD → **dừng, báo, tính lại profile.**

### G2 — Xác minh giấy phép · *nửa buổi* · **cổng chặn**

Đọc giấy phép thật của FLUX.2 Klein tại thời điểm triển khai, ghi vào
`docs/ANH_NOI_BO/LICENSE_NOTES.md`: cho phép gì, cấm gì, có được bán ảnh sinh ra
không, có phải ghi công không, có giới hạn doanh thu không.

**Xong =** một câu kết luận có trích dẫn nguồn: *được bán* hoặc *không được bán*.
Nếu không được bán → chuyển ứng viên số một sang **Qwen-Image**, kiến trúc không đổi.

### G3 — Tải model + chạy baseline · *1 buổi*

Tải Klein (DiT + TE `qwen3_4b` + VAE) vào `E:\AI\models\…`, ghi sha256 vào bảng kê.
Dựng workflow `t2i` tối thiểu. Chạy 5 ca của bước 04 trong pack: **portrait ·
cinematic · landscape · product · complex scene/text**.

Mỗi lần chạy ghi: prompt · seed · resolution · steps · **load time · generation
time · peak VRAM · RAM · nhiệt độ** · đường dẫn ảnh.

**Xong =** 5 tấm ảnh thật + `bench/baseline.json`. Nếu OOM: ghi log, dọn, thử
chiến lược an toàn kế tiếp — **không âm thầm giảm chất lượng** (quy tắc của pack).

### G4 — Benchmark chọn profile · *1 ngày*

Bộ **30 prompt cố định**, cùng seed, phủ: portrait · photorealistic · cinematic ·
nhiều người · đặt vật thể · sản phẩm · **chữ (typography)** · kiến trúc · anime ·
fantasy · **tiếng Việt phức tạp** · tiếng Anh phức tạp.

Chạy qua các chiến lược thực tế trên 3090: bf16 · bf16+offload · fp8_scaled ·
GGUF-Q8/Q6. Đo: model load · first latency · warm latency · peak VRAM · RAM ·
GPU util · nhiệt · tỉ lệ hỏng/OOM. Dựng gallery cạnh nhau.

Chọn theo **4 tiêu chí của pack** (quality · latency · memory · stability), cộng
**tiêu chí thứ 5 mà pack thiếu**: **đồng/ảnh** (điện năng đo được × giá điện).

**Xong =** `configs/profile_quality.yaml`, `configs/profile_fast.yaml` (chỉ tạo
`balanced` nếu số đo chứng minh nó khác thật), + `docs/ANH_NOI_BO/BENCHMARK.md`.

### G5 — Edit và reference · *1 ngày*

Dựng workflow cho `edit`, `subject`, `structure`. Chạy bộ test của bước 07 trong
pack: **đổi màu · đổi trang phục · đổi nền · giữ nhân dạng · sửa vật thể · ghép
nhiều tham chiếu**, mỗi loại 10 ca, kèm gallery before/after.

Pipeline ảnh vào phải: kiểm MIME · phát hiện file hỏng · chuẩn hoá EXIF · resize/crop
hợp lý · **giữ bản gốc, làm việc trên bản sao**. Dùng lại
`platform_core/image_input.validate_reference` ở phía A.

**Xong =** `docs/ANH_NOI_BO/EDIT_REFERENCE.md` ghi rõ **chế độ nào đủ ổn định để
bán, chế độ nào chưa** — ghi thẳng, không che bằng UI.

### G6 — Cổng render · *1 ngày* · **mã ở máy A**

Viết `render_gateway/` theo §3. Test bằng ComfyUI giả lập — **chạy được trên máy A,
không cần GPU**.

**Xong =** `pytest tests/test_245_render_gateway.py` xanh trên A.

### G7 — Deploy sang B + dịch vụ · *nửa ngày*

`E:\AI\ltt_render\` + venv riêng + hai service NSSM (`LTTComfyUI`,
`LTTRenderGateway`) tự khởi động, tự bật lại khi chết, **có trần số lần restart**
(pack: "tránh restart loop vô hạn"). Tường lửa mở 8199 **chỉ cho 192.168.2.17**.
Đo tốc độ LAN A↔B. Ghim commit ComfyUI.

**Xong =** khởi động lại B → cả hai service tự lên; `curl /health` từ A trả 200;
từ máy khác trong LAN **bị chặn**; `kiem_tra.ps1` so hash gateway trên B với repo.

### G8 — Nối vào nền tảng · *1 ngày*

Máy A: thêm provider `ltt_image` vào `REGISTRY`; viết `platform_core/image_gen/`;
cất token cổng render vào APIKEYS (mã hoá); đặt `LTT_RENDER_ENDPOINT` vào
`app.env`; thêm pool `render` vào `LTT_WORKER_POOLS`.

**Xong =** `pytest tests/test_246_provider_local.py` xanh; adapter gọi thật qua
LAN sinh được ảnh và ảnh nằm trên R2.

### G9 — Stress test · *nửa ngày* · **bước pack đúng mà tôi từng thiếu**

Theo bước 14: 100 generation tuần tự · nhiều người gửi cùng lúc · trộn
generate/edit/reference · prompt rất dài · ảnh hỏng · đường OOM · **restart worker
giữa chừng** · **restart cổng render giữa chừng**.

Đo: jobs/hour · latency trung vị · **P95** · peak VRAM · RAM · util · nhiệt ·
tỉ lệ hỏng · tỉ lệ OOM · **memory drift** (VRAM/RAM sau ảnh thứ 100 so với ảnh đầu).

**Xong =** `docs/ANH_NOI_BO/PERFORMANCE.md`. **Có memory drift rõ rệt = không mở
bán**, sửa trước.

### G10 — Mở cho khách · *1 ngày*

Thêm model nội bộ vào `model_ref` của `taoanh` (+ `thumbnail` nếu hợp) — **chỉ
thêm lựa chọn**, không đổi logic cũ. Đặt giá credit từ số đo ở G4. Cảnh báo khi B
chết. Vòng đời file `work\`. Runbook.

**Xong =** `python tools\gate.py` **toàn xanh**; kiểm bằng trình duyệt trên
**`https://app.lttstudios.com`** (không chỉ loopback — quy tắc 5b của `CLAUDE.md`);
`live_check_render.py` **fail đúng** khi rút B ra.

### G11 — Đối chứng mù với model đang bán · *nửa ngày*

Bước 19 của pack, nhưng **đổi đối chứng**: đấu chính là **Gemini 3 Pro Image /
Flash Image** — thứ bạn đang bán và đang trả tiền. GPT Image 2 là phụ nếu có key.

100 prompt, giữ nguyên ngữ nghĩa và tỉ lệ khung. Vote **A / B / Hoà** *rồi mới lộ
tên model*. Chấm: chất lượng thị giác · bám prompt · giải phẫu · **chữ** · bố cục ·
giữ tham chiếu · độ chính xác khi sửa.

**Xong =** `docs/ANH_NOI_BO/DOI_CHUNG_GEMINI.md` trả lời đúng một câu hỏi:
**loại yêu cầu nào nên đi model nhà, loại nào nên đi Gemini** — và đó thành luật
định tuyến trong `api_pool`.

### G12 *(sau, tuỳ chọn)* — Trả nợ kiến trúc

Rút đường Gemini của `taoanh`/`thumbnail` vào `image_gen` chung, xoá bản sao L2.
**Xong =** hai app dùng chung một đường; test cũ vẫn xanh.

---

## 8. Rủi ro và cách chặn

| Rủi ro | Vì sao đáng sợ | Chặn thế nào |
|---|---|---|
| **ComfyUI không có xác thực** | Ai gọi được 8188 là chạy được mã tuỳ ý trên B | Giữ nguyên `--listen 127.0.0.1`. Chỉ cổng render nghe LAN, có token, tường lửa chỉ cho `.17`. **Không bao giờ** ra Cloudflare |
| **custom_node = mã tuỳ ý** | Cài node lạ là cho nó chạy tự do trên B | Chỉ node từ nguồn đã biết, ghim commit; **không** để ComfyUI-Manager cài từ xa |
| **Nâng cấp ComfyUI làm vỡ workflow JSON** | Node đổi schema là template chết lặng | **Ghim commit `6f7cd7f`**; mỗi template một smoke test; nâng cấp là quyết định có chủ ý |
| **Phá `E:\AI\venv`** | Mất luôn cả stack video 342 GB | Venv **riêng** cho gateway. Tuyệt đối không `pip install` vào venv ComfyUI |
| **B tắt / mất điện** | Job treo, khách mất tiền | A gọi `/health` trước khi nhận; B offline → job fail nhanh, hoàn credit (đã có), cảnh báo `LTT_OPS_ALERT_EMAIL` |
| **ComfyUI đang chạy tay** | Khởi động lại B là mất dịch vụ, không ai biết | NSSM 2 service, tự khởi động, có trần restart |
| **Hai hàng đợi** | Trạng thái job phân mảnh, mất khi B restart | Cổng trả 429 khi bận; hàng đợi thật chỉ ở CSDL của A |
| **OOM 24 GB** | Job chết giữa chừng | `N=1`; đo VRAM đỉnh ở G4 trước khi mở bán; GGUF làm đường lui; tối đa một lần thử lại |
| **Memory drift** | Chạy 3 ngày rồi mới OOM — lỗi khó nhất để tìm | G9 bắt buộc, đo drift sau 100 ảnh |
| **Nạp nguội 20 GB** | Ảnh đầu tiên chậm bất thường | Giữ ComfyUI nóng (`--cache-ram 24 64`); 192 GB RAM đủ giữ nhiều model thường trú |
| **GPU tranh chấp với việc video** | ĐÃ XÁC NHẬN có video. Một lượt video từng chạy **72,5 phút** và ăn **98,7 % VRAM** — job ảnh xếp sau là khách chờ 72 phút | **KHÔNG xếp chung FIFO.** Trọng tài + **rơi về Gemini** khi B bận. Chi tiết: [`CHIA_GPU_VOI_VIDEO.md`](CHIA_GPU_VOI_VIDEO.md) |
| **Bận bị hiểu nhầm là hỏng** | `danh_dau_loi()` cho key `ltt_image` khi B bận → cooldown → `disable` sau 5 lần ⇒ một tối chạy video **tự tắt vĩnh viễn** model nhà | G8: bận trả mã riêng, **không** đụng tới trạng thái key |
| **Lệch đồng hồ hai máy** | Đã làm đứt cụm Nexus một lần (B lệch 83 phút) | `NexusClockSync` đã có; thêm vào `kiem_tra.ps1` |
| **Deploy lệch phiên bản** | Sửa tay trên B rồi quên — lỗi kinh điển của repo này | Mã ở repo, deploy bằng script, `kiem_tra.ps1` so hash |
| **Giấy phép model** | Bán ảnh từ model non-commercial | **G2 là cổng chặn** — chưa xác minh thì không đi tiếp |

---

## 9. Việc KHÔNG làm

- **Không** mở cổng render ra Internet, không qua Cloudflare Tunnel. Khách gọi
  **API công khai của A**; A gọi B.
- **Không** mở model nội bộ ra `/api/v1` ở bước này. Public API đang tạm dừng có
  chủ ý; mở tool là quyết định riêng và phải cập nhật `server/api/inventory.py`
  + `APP_API_COVERAGE_FINAL.md`.
- **Không** dựng API/hàng đợi/CSDL/storage/web/billing riêng như bước 08–10, 17
  của pack. Nền tảng đã có.
- **Không** đụng kho model video và workflow Wan trên B.
- **Không** tạo app mới. Đây là provider.
- **Không** bật prompt enhancer ở MVP. Mặc định TẮT, đo raw-vs-enhanced trước.
- **Không** hợp nhất cơ chế kiểm VRAM/RAM toàn hệ trong H37. Cổng render chỉ phải
  **phát đúng khuôn** đo sẵn có và **tôn trọng ngưỡng 48 GB**. Việc hợp nhất thật
  là **H38**, làm sau — xem [`CHIA_GPU_VOI_VIDEO.md`](CHIA_GPU_VOI_VIDEO.md) §10.

---

## 10. Còn phải chốt

1. **Giấy phép** — G2 trả lời. Nếu Klein không cho bán: chuyển sang Qwen-Image,
   kiến trúc giữ nguyên. Bạn có muốn tôi chuẩn bị sẵn cả hai đường không?
2. ~~Máy B có chạy việc video không?~~ **ĐÃ TRẢ LỜI: có.** Dự án `E:\LTT AI`,
   dùng chung đúng ComfyUI đó. Cách chia GPU đã thiết kế ở
   [`CHIA_GPU_VOI_VIDEO.md`](CHIA_GPU_VOI_VIDEO.md) — còn 4 câu con cần bạn chốt
   ở §9 của tài liệu đó (cửa sổ giờ · có sửa dự án video không · khách thấy gì ·
   ai chạy video).
3. **Số bậc giá**: một hay hai? Quyết sau G4 cũng được, nhưng sớm thì workflow đỡ
   phải làm lại.
4. **Thứ tự ưu tiên**: H37 trước, hay mở tool Public API / H35.10 trước?

---

## 11. Tài liệu sẽ sinh ra

> Kiểm 19/09/2026: `BENCHMARK.md`, `EDIT_REFERENCE.md`, `PERFORMANCE.md`, `DOI_CHUNG_GEMINI.md`,
> `RUNBOOK.md` (G4–G11) **chưa từng tồn tại** trong `docs/ANH_NOI_BO/` — các tham chiếu tới chúng ở
> §G2 trở đi là tài liệu dự kiến chưa viết, không phải con trỏ vỡ.

| File | Khi nào |
|---|---|
| `docs/ANH_NOI_BO/DECISIONS.md` | ngay từ G1 — khuôn Decision/Reason/Alternatives/Trade-off/Date của pack |
| `docs/ANH_NOI_BO/LICENSE_NOTES.md` | G2 |
| `docs/ANH_NOI_BO/BENCHMARK.md` | G4 |
| `docs/ANH_NOI_BO/EDIT_REFERENCE.md` | G5 |
| `docs/ANH_NOI_BO/PERFORMANCE.md` | G9 |
| `docs/ANH_NOI_BO/DOI_CHUNG_GEMINI.md` | G11 |
| `docs/ANH_NOI_BO/RUNBOOK.md` | G10 |
| `docs/QUYET_DINH_NEN_TANG.md` | **Q102** khi bắt đầu thi hành |
| `docs/KE_HOACH_TRIEN_KHAI.md` · `CLAUDE.md` · `NHAT_KY.md` | theo quy tắc 3 tầng |
