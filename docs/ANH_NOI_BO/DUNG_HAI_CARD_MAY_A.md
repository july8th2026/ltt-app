# Dùng hai card 5060 Ti của máy A — hướng nào, và vì sao

> # ⚠️ BẢN GHI 08/2026 — MÁY A NAY CÒN **MỘT** CARD
>
> Tiêu đề và mọi số trong tệp này thuộc thời máy A có **hai** card 5060 Ti. Máy A
> nay còn **một**. Đừng đọc tệp này như hiện trạng, và đừng sửa nó — nó là bản
> ghi có ngày. Cấu hình hôm nay: [`../HAI_MAY_A_VA_B.md`](../HAI_MAY_A_VA_B.md).

**2026-08-24.** Chủ sản phẩm: *"máy A có 2 card 5060 Ti 16 GB. Có phương án nào để
hai card đó cũng hỗ trợ được không — ví dụ để ComfyUI trên 1 card máy A, chia bớt
công việc? Mục tiêu tối ưu chất lượng, tốc độ."*

> # 🔴 §3 CỦA TÀI LIỆU NÀY ĐÃ BỊ **D-057** THAY — ĐỌC D-057 TRƯỚC
>
> Chủ sản phẩm quyết **không tải bản model thấp hơn** (FP8/GGUF), và nếu không có
> bản thấp hơn thì **ngừng kế hoạch dùng máy A để sinh ảnh**. Sinh ảnh **ở lại
> máy B**.
>
> Bỏ FP8 thì phép cộng không còn đường lách: HiDream `bf16` đỉnh **18.450 MB** so
> với card **16.311 MB**, và pha nặng nhất là **bốn bộ mã hoá** — riêng
> **Llama-3.1-8B ở bf16 (~16 GB) đã lấp kín một card**. Nên cả cách đặt encoder
> sang card khác cũng không đủ.
>
> **Giữ tài liệu này, không xoá.** Hai phần vẫn đúng và vẫn cần:
> **§1** (số đo phần cứng máy A đã kiểm) và **§2** (vì sao chuyển Qwen sang máy A
> là bẫy — 3090 nhanh gấp ~2 lần vì băng thông). Chúng là thứ phải đưa ra khi có
> người đề xuất lại.
>
> ⇒ Và hệ quả lớn nhất: **trọng tài VRAM ở
> [`CHIA_GPU_HAI_MODEL.md`](CHIA_GPU_HAI_MODEL.md) nay là việc BẮT BUỘC**, không
> còn là một trong hai lựa chọn.

Trả lời ngắn *(trước D-057)*: **có, và nó xoá luôn bài toán tranh card ở
[`CHIA_GPU_HAI_MODEL.md`](CHIA_GPU_HAI_MODEL.md).** Nhưng phải đi **đúng một
chiều** — chiều ngược lại là một cái bẫy mà số đo của cộng đồng đã đo hộ.

---

## 1. Phần cứng thật, kiểm hôm nay

| | Máy A (máy chủ) | Máy B |
|---|---|---|
| Card | **2 × RTX 5060 Ti** | 1 × RTX 3090 |
| VRAM mỗi card | **16.311 MiB** | 24.576 MiB |
| Kiến trúc | Blackwell (`sm_120`) | Ampere |
| Băng thông bộ nhớ | 448 GB/s | **936 GB/s** |
| FP8 | **tensor core gốc** | **giả lập** |
| Tính toán fp32 | **14,2 / 15,1 TFLOPS** | **~35,6 TFLOPS** |
| PCIe đo được | **4,2 / 3,3 GB/s** | (chưa đo, cao hơn hẳn) |
| **RAM hệ thống** | **31,9 GB** | **192 GB** |

✅ **Cả hai card máy A đều KHOẺ**: `ConfigManagerErrorCode = 0`, driver 596.21,
`nvidia-smi` thấy cả hai, và **đang rảnh** (435 / 858 MB). Card thứ hai đã chạy từ
06/08 sau khi ép gán driver — xem bộ nhớ dự án `gpu-thu-hai-code-43-va-ke-hoach-h23`.

⚠️ Nhưng nhớ: **32 GB đó là hai bể 16 GB, không phải một bể 32 GB.** Không có
NVLink ⇒ không có bể chung.

### 🔴 Bốn con số ở bảng trên sửa lại đề xuất, và phải đọc trước khi đi tiếp

1. **Tính toán: mỗi 5060 Ti chỉ có ~40 % fp32 của 3090** (14–15 so với 35,6 TFLOPS).
   Sinh ảnh bị chặn bởi **tính toán**, nên bf16 trên 5060 Ti sẽ **chậm hơn đáng kể**
   — thô sơ là ~2,4 lần. FP8 gốc phải bù được khoảng đó mới đáng chuyển.
2. **RAM hệ thống chỉ 31,9 GB**, không phải 192 GB như máy B. Nên đường lùi
   *"đẩy 4 bộ mã hoá sang CPU"* ở §3 **chật hơn nhiều** so với khi đọc tài liệu
   ComfyUI-MultiGPU, và page cache **không** giữ nổi thoải mái cả HiDream + encoder.
3. **PCIe đo được chỉ 4,2 và 3,3 GB/s.** Nên tính chất *"nạp lại chỉ 0,8 giây"* của
   máy B **KHÔNG chuyển sang máy A** — nạp ~16 GB ở 3,3 GB/s là **~5 giây**.
4. **Liên kết driver của card 2 MONG MANH**: nó dùng `oem3.inf` mà INF đó **không
   liệt kê nó** (`SUBSYS_8A111043` không có trong bất kỳ driver NVIDIA nào). Một lần
   cập nhật driver hoặc Windows Update có thể trả nó về Basic Display Adapter, **im
   lặng**. Đặt hàng bán cho khách lên card đó mà không có chốt kiểm là mời một sự cố.
   ⇒ Phải có chốt: `nvidia-smi -L` **phải thấy 2 GPU**, kiểm sau mỗi lần đổi driver.

---

## 2. Hướng SAI: chuyển Qwen sang máy A

Nghe hợp lý: Qwen cần 19,2 GB, hai card cộng lại 32 GB, `llama.cpp` chia được model
qua nhiều card. **Vừa.**

Nhưng cộng đồng đã đo đúng cặp này, trên đúng loại model (dense ~30B, Q4):

| Qwen3-32B dense | 4K ngữ cảnh | 16K ngữ cảnh |
|---|---|---|
| **1 × RTX 3090** | **35,1 t/s** | **30,3 t/s** |
| **2 × RTX 5060 Ti** | 18,2 t/s | 14,4 t/s |

⇒ **3090 nhanh gấp ~1,9–2,1 lần.** Lý do đơn giản: **sinh token là bài toán bị
chặn bởi băng thông bộ nhớ**, và 936 GB/s so với 448 GB/s là toàn bộ câu chuyện.
Chia model qua PCIe (không có NVLink trên card tiêu dùng) còn cộng thêm phí liên
lạc giữa hai card.

Và nó **không mua được gì**: cái mà 32 GB cho là **ngữ cảnh dài hơn**, nhưng Qwen
64K đã vừa trên 3090 rồi (đo được 19.237 MB / 24.576).

⇒ **Đừng chuyển LLM sang máy A.** Trả một nửa tốc độ cho một thứ ta không cần.

*(Nếu vẫn làm: dùng `--split-mode layer`, KHÔNG dùng `row`. `row` chia từng
tensor và chỉ nhanh khi có NVLink; trên PCIe nó làm ngập bus và **chậm hơn** —
có báo cáo tụt 8–10 lần.)*

---

## 3. Hướng ĐÚNG: chuyển sinh ảnh sang máy A

### Vướng đầu tiên, và cách cộng đồng đã giải

HiDream `bf16` đo trên máy B đỉnh **18.450 MB** — **không vừa** một card 16.311 MB.

Nhưng: **`HiDream-O1-Image-FP8` có thật** trên HuggingFace — bản FP8 của **đúng
model ta đang chạy**. Và tài liệu HiDream ghi cả ba biến thể (Full 50 bước / Dev 28 /
Fast 16) ở mức **~16 GB**, kèm các bản GGUF Q8…Q2.

### Và đây là chỗ hai card 5060 Ti **hơn** 3090

> **3090 (Ampere) KHÔNG có FP8 gốc — nó giả lập.
> 5060 Ti (Blackwell) có tensor core FP8 gốc.**

Nên FP8 trên 5060 Ti vừa **nhỏ hơn** vừa **nhanh hơn**, còn FP8 trên 3090 chỉ nhỏ
hơn. Đó là lý do một card yếu hơn về giấy tờ vẫn có thể thắng ở đúng định dạng này.

⚠️ **Đây là suy luận từ tài liệu, CHƯA ĐO.** Nó là lý do để đo, không phải kết luận.

### Hai card ⇒ hai làn, không phải một card to

Cách chuẩn của cộng đồng cho nhiều card trong ComfyUI **không** phải chia một ảnh
qua hai card — mà là **một tiến trình ComfyUI cho mỗi card**:

```
python main.py --cuda-device 0 --port 8188 --user-directory user-gpu0
python main.py --cuda-device 1 --port 8189 --user-directory user-gpu1
```

(`--user-directory` riêng là bắt buộc, nếu không hai tiến trình tranh trạng thái
trình duyệt và tab workflow.)

Được gọi là **multi-instance fan-out**: N làn song song, phức tạp tối thiểu. Tốc
độ **mỗi ảnh không đổi**, nhưng **số ảnh mỗi phút gấp đôi**.

⇒ Khớp thẳng với ta: khách xin `count: 2..4` thì hai làn chạy song song. Và
`render_gateway` chỉ cần đổi từ một upstream `max_concurrent=1` thành hai upstream.

### Nếu FP8 vẫn không vừa 16 GB

HiDream dùng **bốn** bộ mã hoá văn bản: CLIP-L, CLIP-G, T5-XXL, **Llama-3.1-8B**.
Chúng chiếm phần lớn dung lượng. `ComfyUI-MultiGPU` có node
**`QuadrupleCLIPLoaderMultiGPU`** cho phép đặt bốn bộ đó lên **card khác** hoặc
**CPU**, giữ UNet + VAE một mình trên card chính.

Đó là đường lùi có thật, nhưng nó **đổi làn song song lấy dung lượng** (card #1
thành nơi chứa encoder chứ không còn là làn thứ hai).

⚠️ Và đường lùi *"đẩy encoder sang CPU"* thì **chật**: máy A chỉ có **31,9 GB RAM**,
không phải 192 GB như máy B. T5-XXL + Llama-3.1-8B ở fp16 đã là hàng chục GB.

---

## 4. Điều quan trọng nhất: nó xoá bài toán tranh card

Hiện tại trên máy B, mỗi model chiếm 75–78 % card và **không bao giờ cùng lúc
được** — nên phải có trọng tài đuổi qua đuổi lại (xem `CHIA_GPU_HAI_MODEL.md`).

Nếu ảnh chuyển sang máy A:

| | Trước | Sau |
|---|---|---|
| Máy B / 3090 | HiDream **và** Qwen tranh nhau | **Qwen một mình**, 19,2 / 24,6 GB |
| Máy A / 2 × 5060 Ti | rảnh | **HiDream, hai làn song song** |
| Trọng tài đuổi model | **phải xây** | **không cần** |
| Phí nạp lại mỗi lượt | 0,8 s (ảnh) / 18 s (LLM) | **0** |
| ComfyUI máy B | ta **và** dự án video | **dự án video một mình** |

Cái cuối đáng giá riêng: D-037 ghi máy B có **ba hộ** dùng chung card. Chuyển ảnh
đi thì còn **hai**, và cái hộ ta không điều khiển được (video) không còn đè lên
hàng bán cho khách.

---

## 5. ⛔ Ba rủi ro phải nói ra trước

### ① Máy A là **MÁY CHỦ ĐANG PHỤC VỤ KHÁCH**

Đặt một việc GPU 110 giây lên đúng cái máy đang trả lời web cho khách là một thay
đổi thật, không phải "dùng phần cứng rảnh". Ba điều đỡ lại, nhưng phải kiểm chứ
không được giả định:

- hai card **đang rảnh thật** (435 / 858 MB — đã đo);
- phục vụ web bị chặn bởi I/O và CSDL, không bởi GPU;
- nền tảng **đã có** `platform_core/gpu_lease.py` + bảng `gpu_leases`, và
  `LTT_WORKER_POOLS` khai đội hình worker theo GPU (H36).

⚠️ Nhưng `taoclipngan` (whisper + YOLO) và `upscalevideo` **đã dùng GPU máy A**.
Thêm ComfyUI vào đó là **thêm hộ thứ ba trên máy A** — đúng cái bài học vừa học ở
máy B, chỉ đổi chỗ. Phải khai vào `gpu_leases`, không được chạy ngoài sổ.

### ② Chất lượng FP8 so với bf16 — **CHƯA ĐO, và ta BÁN cái này**

Đây là thay đổi **một biến** trên **cùng một model**, tức là đúng loại phép đo
D-046 cho phép và `tools/cham_mu.py` nay làm đúng (bẫy cùng-đề-bài-khác-seed từ
D-052). **Không được mở bán FP8 trước khi có lô so mù.**

⛔ Và đừng lặp lại lỗi cũ: chấm **HiDream FP8 đấu HiDream bf16**, cùng prompt cùng
seed, không đấu Gemini.

### ③ Tốc độ mỗi ảnh trên 5060 Ti — **CHƯA ĐO**

Sinh ảnh bị chặn bởi **tính toán**, không bởi băng thông như LLM — nên bài toán
khác hẳn mục 2, và **không được suy ra từ đó**.

Nhưng số fp32 đã đo thì **không nghiêng về máy A**: 14,2 / 15,1 TFLOPS so với
~35,6 của 3090. Nghĩa là **FP8 gốc phải bù được khoảng 2,4 lần** mới hoà. Đó là
một đòi hỏi lớn, không phải một khả năng nhẹ nhàng — và nó là lý do việc ③ ở dưới
là **cổng chặn**, không phải một phép đo cho vui.

Mốc so: **109,7 giây/ảnh** (t2i, 50 bước, 2560×1440, bf16, 3090 — trung vị 100 lượt).

---

## 6. Việc cần làm, theo thứ tự

| # | Việc | Đạt khi |
|---|---|---|
| **1** | Tải `HiDream-O1-Image-FP8`, dựng **một** ComfyUI trên máy A `--cuda-device 0` | sinh được một ảnh, ghi **VRAM đỉnh** |
| **2** | Nếu > 16.311 MB ⇒ dùng `QuadrupleCLIPLoaderMultiGPU` đẩy 4 encoder sang card 1 hoặc CPU | vừa, có số đo |
| **3** | Đo **tốc độ**: 30 ảnh, cùng bộ prompt seed 1, so với 109,7 s của 3090 | có bảng giây/ảnh |
| **4** | **Lô so mù FP8 đấu bf16**, cùng prompt cùng seed, `cham_mu.py` + bẫy `--bay-tu` | KTC tách khỏi 0,5, **hoặc** kết luận "không phân biệt được" |
| **5** | Nếu ③④ đạt: dựng làn thứ hai `--cuda-device 1 --port 8189`, `render_gateway` hai upstream | 2 ảnh song song, thông lượng gấp đôi |
| **6** | Khai GPU máy A vào `gpu_leases`; ComfyUI **không** chạy ngoài sổ | `taoclipngan`/`upscalevideo` không bị bỏ đói |
| **6b** | Chốt `nvidia-smi -L` **phải thấy 2 GPU**, chạy trong vòng bảo trì | liên kết driver card 2 mong manh — mất nó là mất một làn, **im lặng** |
| **7** | Chỉ khi ①–⑥ xong: chuyển `LTT_RENDER_BASE_URL` sang máy A, trả 3090 cho Qwen | không còn trọng tài, không còn phí nạp lại |

⛔ **Đừng làm việc 7 trước việc 4.** Chuyển hàng bán sang một định dạng chưa chấm
chất lượng là đúng thứ cổng G6b sinh ra để chặn.

### 🔴 Và một điểm thiết kế đã ghi từ H23, đừng phát minh lại

Bộ nhớ dự án (`gpu-thu-hai-code-43-va-ke-hoach-h23`) đã chốt điều then chốt cho
hai GPU, và nó **cùng họ với bài học "xác minh chứ đừng giả định"** ở
`CHIA_GPU_HAI_MODEL.md`:

> **Đọc "VRAM còn trống" thôi là SAI** — hai worker cùng thấy trống, cùng nhận
> GPU 0, cùng OOM. Phải **giữ chỗ nguyên tử trong CSDL** theo khuôn
> `claim → đập nhịp → reclaim_orphans` của hàng đợi job. **Giữ chỗ trước, chạy
> song song sau.**

Và nó đã chỉ ra **bốn chỗ sẽ hỏng ngầm** khi có 2 GPU, tất cả đều còn nguyên:

| Chỗ | Hỏng thế nào |
|---|---|
| `apps/upscalevideo/autotune.py` | `splitlines()[0]` ⇒ **chỉ thấy GPU 0**; `_TOTAL_MB_FALLBACK` viết cứng 16311 |
| `apps/autosubvideo/whisperx_runner.py` | `device="cuda"` ⇒ **luôn `cuda:0`** |
| `job_worker.py` | một tiến trình ⇒ một job một lúc ⇒ **GPU 2 nằm không** |
| — | **không có cơ chế giữ chỗ GPU nào** |

⇒ Việc 5 (làn thứ hai) **không** chỉ là bật thêm một tiến trình ComfyUI. Nó cần
phần giữ chỗ ở trên, nếu không hai làn sẽ tranh cùng một card và cùng OOM.

⚠️ **Chưa có việc nào ở đây được viết.** Đây là đề xuất.

---

## 7. Ba thứ đã loại

| Không dùng | Vì sao |
|---|---|
| Chia **một ảnh** qua hai card | Diffusion không chia tốt. Cách cộng đồng dùng là **nhân bản rồi chạy song song**, không phải phân mảnh. |
| `--split-mode row` cho LLM | Chỉ nhanh khi có NVLink. Trên PCIe làm ngập bus, có báo cáo chậm 8–10 lần. |
| Gộp 32 GB thành "một bể" | Không có NVLink ⇒ không có bể chung. Hai bể 16 GB. |

---

## Nguồn

- [Dual RTX 5060 Ti 16GB vs RTX 3090 for Local LLMs](https://www.hardware-corner.net/guides/dual-rtx-5060-ti-16gb-vs-rtx-3090-llm/) — số t/s Qwen3-32B dense
- [llama.cpp — docs/multi-gpu.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md) · [issue #4055](https://github.com/ggml-org/llama.cpp/issues/4055) — `layer` so với `row`
- [ComfyUI Multi GPU: --cuda-device hoặc hai tiến trình](https://wonderfullauncher.com/docs/comfyui-multi-gpu) · [Dual GPU discussion #836](https://github.com/Comfy-Org/ComfyUI/discussions/836)
- [pollockjj/ComfyUI-MultiGPU](https://github.com/pollockjj/ComfyUI-MultiGPU) — `QuadrupleCLIPLoaderMultiGPU`, Virtual VRAM
- [drbaph/HiDream-O1-Image-FP8](https://huggingface.co/drbaph/HiDream-O1-Image-FP8) — bản FP8 của đúng model đang chạy
- [ComfyUI Wiki — HiDream-I1 fp8/gguf/nf4](https://comfyui-wiki.com/en/tutorial/advanced/image/hidream/i1-t2i) — biến thể và mức VRAM
- [RTX 5060 Ti vs RTX 3090 benchmark](https://gigagpu.com/rtx-5060-ti-16gb-vs-rtx-3090-benchmark/) — băng thông, FP8 gốc so với giả lập
