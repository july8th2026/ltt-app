# DECISIONS — H37 model tạo ảnh nội bộ

Sổ quyết định kỹ thuật của hạng mục H37. Khuôn lấy từ bộ
`flux2_klein9b_claude_build_pack` (`START_HERE.md` §7):

```
Decision:
Reason:
Alternatives considered:
Trade-off:
Date:
```

**Quan hệ với `docs/QUYET_DINH_NEN_TANG.md`:** file kia giữ quyết định **nền tảng**
(Q102 là quyết định nền của H37). File này giữ quyết định **kỹ thuật cấp thi hành**
— chọn engine, chọn model, chọn profile, chọn ngưỡng. Khi một quyết định ở đây đủ
lớn để ràng buộc cả nền tảng, nó phải được nâng lên thành một số Q.

**Quy tắc:** một quyết định chưa ghi vào đây thì coi như chưa có. Đổi quyết định cũ
thì **không xoá** — thêm mục mới và ghi `Thay: D-xxx`.

---

## D-001 — Dùng ComfyUI làm engine, bọc sau cổng render tự viết

**Decision:** ComfyUI trên máy B là engine thực thi. Ta không tự viết engine
`diffusers`. Cổng render (`render_gateway/`) bọc nó lại thành một API sạch.

**Reason:** ComfyUI 0.30.0 đã cài, đã chạy, và **đã hỗ trợ FLUX.2/Klein ở cấp mã
nguồn** — `comfy/supported_models.py:794` có `class Flux2(Flux)`, kèm
`EmptyFlux2LatentImage`, `Flux2Scheduler`, và ba nhánh text-encoder tự dò
(`qwen3_4b` → `KleinTokenizer`, `qwen3_8b` → `KleinTokenizer8B`, `mistral3_24b` →
`Flux2Tokenizer`). Ba chế độ ảnh tham chiếu cũng đã có node sẵn (`ReferenceLatent`,
`FluxKontextImageScale`, `controlnet_aux`). Tự viết `diffusers` là bỏ một thứ đang
chạy để làm lại từ đầu.

**Alternatives considered:** (a) tự viết engine `diffusers` theo bước 06 của build
pack; (b) dùng thẳng ComfyUI API, không bọc.

**Trade-off:** nhận rủi ro *"nâng cấp ComfyUI làm vỡ workflow JSON"*. Chặn bằng ba
thứ: **ghim commit `6f7cd7f`** · mỗi template một smoke test · giữ lớp trừu tượng
`backend: comfy | diffusers` trong cổng render. Loại (b) vì ComfyUI không có xác
thực và hàng đợi của nó sẽ là hàng đợi thứ hai nằm ngoài CSDL.

**Date:** 2026-08-21

---

## D-002 — Không dựng API / queue / DB / storage / web / billing riêng

**Decision:** bỏ các bước 08, 09, 10, 17 của build pack. Dùng nguyên hàng đợi job,
sổ credit, PostgreSQL, R2, giao diện và sao lưu của LTTSTUDIOSAPP.

**Reason:** bộ pack được viết cho một máy chưa có sản phẩm nào. Nền tảng đã có tất
cả những thứ đó, đang chạy thật, đang phục vụ khách trả tiền. Làm theo pack nguyên
văn là dựng nền tảng thứ hai cạnh nền tảng thứ nhất — `CLAUDE.md` cấm thẳng.

**Alternatives considered:** (a) làm theo pack nguyên văn; (b) làm riêng rồi hợp
nhất sau.

**Trade-off:** máy B phụ thuộc máy A về mọi thứ ngoài GPU. Đổi lại: một sổ tiền,
một hàng đợi, một kho ảnh, một chỗ đăng nhập. Loại (b) vì "hợp nhất sau" trong
thực tế nghĩa là không bao giờ hợp nhất.

**Date:** 2026-08-21

---

## D-003 — Klein 9B là ứng viên số một, chưa phải kết luận cuối

> ⛔ **ĐÃ BỊ THAY BỞI [D-008](#d-008--qwen-image-thay-klein-9b-làm-ứng-viên-số-một-thay-d-003)**
> (2026-08-21, cùng ngày). G2 xác minh Klein 9B mang **FLUX Non-Commercial License
> v2.1** — không bán ảnh được. Giữ mục này để truy nguồn, **đừng làm theo nó.**
> Ghi chú: chính D-003 đã dự liệu tình huống này ở phần Trade-off, và cửa thoát đó
> đã dùng đến thật.

**Decision:** ưu tiên FLUX.2 Klein 9B ở G3. Phương án thay thế đã chuẩn bị sẵn:
Qwen-Image + Qwen-Image-Edit.

**Reason:** ComfyUI trên B đã đỡ sẵn; text encoder của Klein là **Qwen3-4B** chứ
không phải Mistral-24B của FLUX.2 [dev], nên gánh nặng là 9B + 4B — vừa 3090 thoải
mái (ước bf16 đỉnh ~21 GB, fp8 ~13 GB, phải đo lại ở G4). Là bản distilled nên ít
bước, hợp với việc bán theo credit.

**Alternatives considered:** Qwen-Image + Qwen-Image-Edit (Apache-2.0, mạnh về chữ
tiếng Việt, phủ cả `edit` lẫn `subject`); SDXL + IP-Adapter + ControlNet (nhẹ, rẻ,
phủ `subject`/`structure` tốt nhất); FLUX.2 [dev] (TE Mistral-24B — quá nặng).

**Trade-off:** **phải xác minh giấy phép trước** (G2 là cổng chặn). Nếu Klein không
cho bán ảnh thì Qwen-Image lên thay ngay — kiến trúc không đổi một dòng, vì toàn bộ
thiết kế là model-agnostic: thêm model = thêm một file workflow JSON + một dòng
`ModelInfo`.

**Date:** 2026-08-21

---

## D-004 — Hai profile, không phải ba, cho tới khi số đo nói khác

> ⚠️ **ĐÃ SỬA ĐỔI BỞI D-010** (2026-08-21): chủ dự án chốt **chất lượng là tiêu chí
> duy nhất**, nên bậc `FAST` **không còn là mục tiêu sản phẩm** — chỉ đo để biết bỏ
> lỡ gì. Phần lý luận về FP8 trên Ampere dưới đây **vẫn đúng** và vẫn áp dụng.

**Decision:** làm `QUALITY` và `FAST`. Chỉ thêm `BALANCED` nếu G4 chứng minh nó
khác thật về cấu hình.

**Reason:** RTX 3090 là Ampere, compute capability **8.6** — **không có FP8 tensor
core** (chỉ có từ Ada 8.9). Nên fp8/GGUF trên máy này chỉ tiết kiệm VRAM chứ không
tăng tốc: trọng số lưu fp8 nhưng phải giải nén về bf16 lúc tính. Nếu bf16 vừa 24 GB
thì bf16 vừa đẹp nhất vừa nhanh nhất, và `QUALITY` với `BALANCED` sẽ trùng cấu hình.

**Alternatives considered:** giữ đủ ba profile như build pack gợi ý.

**Trade-off:** ít lựa chọn hơn cho người dùng — nhưng chính build pack cấm tạo
profile chỉ để marketing khi cấu hình giống nhau.

**Date:** 2026-08-21

---

## D-005 — Tranh chấp GPU giải bằng ETA + cascade, không bằng hàng đợi FIFO

> ⚠️ **ĐÃ SỬA ĐỔI BỞI D-010** (2026-08-21) ở hai điểm: (1) cascade sang Gemini
> **không còn là mặc định ngầm** — nó là lựa chọn tường minh của khách, vì thay
> model sau lưng khách là đánh tráo sản phẩm; (2) `NGƯỠNG_CHỜ` 45 giây **vô nghĩa**
> khi một ảnh vốn mất ~3 phút — ngưỡng phải tính theo *thời gian chờ thêm so với
> thời gian chạy*, không phải hằng số tuyệt đối.
> Phần "không xếp hàng FIFO" và toàn bộ số đo về tranh chấp GPU **vẫn đúng**.

**Decision:** job ảnh **không xếp hàng sau job video**. Luật: `eta_s ≤ NGƯỠNG_CHỜ`
(khởi điểm 45 giây) thì chờ rồi chạy ở nhà; lớn hơn thì cascade sang Gemini.

**Reason:** máy B chạy video trên cùng card. Một lượt video từng chạy **72,5 phút**
(`E:\LTT AI\src\ltt\executor.py:193`) và đỉnh VRAM đo được là **24.251 / 24.576 MiB**
— 98,7 % card. FIFO nghĩa là khách chờ tới 72 phút. Không cắt ngang được lượt video
đã tiêu 40 phút GPU, và không chạy song song được vì không còn VRAM.

**Alternatives considered:** (a) một hàng đợi FIFO chung; (b) chỉ báo bận/rảnh nhị
phân; (c) hai instance ComfyUI, mỗi bên một cổng.

**Trade-off:** mỗi job rơi sang Gemini tốn 500–1.600 đồng thay vì ~20 đồng tiền
điện. Chấp nhận: đổi ~1.500 đồng lấy việc không có ai chờ 72 phút. Loại (b) vì nó
lỗi thời ngay khi lượt video nhanh lên — sẽ đẩy job sang cloud cả khi chỉ cần chờ
8 giây. Loại (c) vì hai tiến trình cùng đòi VRAM sẽ OOM thật, trong khi một
instance được ComfyUI tự nối đuôi miễn phí.

**Hệ quả kiến trúc:** 3090 là cách để **rẻ đi**, không phải chỗ dựa để **chạy
được**. Nhờ vậy "máy B chết" và "ComfyUI chạy tay" tụt từ sự cố xuống tốn thêm tiền.

**Date:** 2026-08-21

---

## D-006 — Được phép sửa `E:\LTT AI` khi cần; vẫn làm trọng tài bản A trước

**Decision:** chủ dự án đã cho phép (2026-08-21) sửa dự án video `E:\LTT AI` nếu
cần. Nhưng thứ tự vẫn là: **bản A trước** (cổng render tự dò bận, không đụng gì),
nâng lên **bản B** (giấy phép thật, gắn vào `cong_gpu.py` + `ltt/chay_job.py`) khi
có va chạm thật hoặc khi việc video thành dịch vụ tự động.

**Reason:** `cong_gpu.py` tự đặt ra luật cho chính nó: *"CỔNG NÀY KHÔNG ĐOÁN. Mỗi
câu hỏi phải trỏ về MỘT SỰ CỐ THẬT. Thêm câu mới chỉ khi có lần hỏng mới — không
thêm vì 'nghe hợp lý'."* Có quyền sửa không có nghĩa là nên sửa ngay. Bản A đủ
dùng và triển khai trong nửa ngày.

**Alternatives considered:** làm bản B ngay từ G7, tận dụng quyền vừa được cấp.

**Trade-off:** bản A có cửa sổ đua ~2 giây. Hậu quả xấu nhất khi đua: lượt video
72 phút bị lùi ~40 giây (0,9 %). Chiều ngược lại đã được tầng cascade xử lý.
**Lưu ý kỹ thuật cho bản B:** giấy phép phải do `ltt/chay_job.py` **giữ suốt lượt**,
không phải do `cong_gpu.py` lấy rồi nhả ngay — `cong_gpu.py` chỉ là kiểm tra trước.

**Date:** 2026-08-21

---

## D-007 — G0–G6 làm ngay; mọi việc chạm máy B chờ GPU rảnh

**Decision:** triển khai G0 ngay. G1, G3, G4, G5, G7 (mọi việc cần máy B) **xếp
lịch sau**, chờ máy B rảnh. G6 (viết cổng render) chạy song song vì nó test bằng
ComfyUI giả lập trên máy A, không cần GPU.

**Reason:** chủ dự án cho biết (2026-08-21) một phiên Claude khác **đang dọn rác dự
án trên máy B**. Hai tác nhân cùng sửa một máy là cách chắc chắn để tạo ra một lỗi
mà không ai truy được nguồn.

**Alternatives considered:** chạy G1 (chỉ đọc) ngay, vì nó không ghi gì.

**Trade-off:** chậm hơn vài ngày. Đổi lại không có xung đột, và **số đo của G1
không bị bẩn** bởi việc dọn rác đang chạy — chính G4 sẽ đòi hỏi máy sạch.

**Cảnh báo tự đặt ra:** mọi thứ tôi đã đọc từ `E:\LTT AI` (đường dẫn tệp, ngưỡng
RAM 48 GB, `cong_gpu.py`, `executor.py`) **có thể lỗi thời sau đợt dọn rác**. Phải
đọc lại trước khi dựa vào, không dùng lại trí nhớ của phiên này.

**Date:** 2026-08-21

---

## D-008 — Qwen-Image thay Klein 9B làm ứng viên số một *(thay D-003)*

**Thay:** D-003.

**Decision:** bộ model đích của H37 đổi thành — **QUALITY: Qwen-Image 20B** ·
**QUALITY-EDIT: Qwen-Image-Edit-2509** · **FAST: FLUX.2 Klein 4B**. Cả ba đều
**Apache 2.0**. Bỏ FLUX.2 Klein 9B.

**Reason:** G2 xác minh được (2026-08-21) rằng **Klein 9B mang FLUX Non-Commercial
License v2.1**, không phải Apache 2.0 — chỉ bản **4B** mới là Apache 2.0. Giấy phép
NC cấm *"commercial use, production deployments, revenue-generating activity"*, và
FAQ của chính nhà phát hành nói rõ: *"If you're generating images for products you
charge for … you need a commercial license."* Nền tảng này bán credit.

Có một cách đọc dung hoà (mục 2(d) của giấy phép cho phép dùng đầu ra thương mại,
mục 4(a) lại cấm hoạt động thương mại) — nhưng **ngay cả cách đọc đó cũng cấm ta**,
vì ta không chỉ bán ảnh mà còn **tự vận hành model trong dịch vụ có thu tiền**. Và
không có ai từ nhà phát hành trả lời để gỡ mâu thuẫn, cả trên model card lẫn trên
issue của kho mã chính thức.

Thêm một phát hiện làm quyết định này dễ hơn: **Qwen-Image-Edit-2509 khớp gần như
một-một với ba chế độ đã chốt** — ghép nhiều ảnh *"person + person / person +
product / person + scene"* với **giữ nhân dạng khuôn mặt** (chế độ `subject`),
**ControlNet gốc** depth/edge/keypoint (chế độ `structure`), và sửa nội dung/font/
màu/chất liệu chữ (chế độ `edit`). Phương án dự phòng phủ yêu cầu **tốt hơn** phương
án gốc.

**Alternatives considered:** (a) mua giấy phép thương mại của nhà phát hành cho
Klein 9B — có bốn bậc nhưng **không công bố giá**, và hai bậc đầu **có trần số
ảnh/tháng**, thứ triệt tiêu chính lợi thế chi phí đã nêu ở Q102; (b) chỉ dùng Klein
4B cho cả hai bậc — mất bậc chất lượng cao; (c) đọc dung hoà rồi cứ dùng 9B.

**Trade-off:** Qwen-Image 20B nặng hơn Klein 9B, và **phải tính lại VRAM từ đầu** —
text encoder của nó là Qwen2.5-VL-7B chứ không phải Qwen3-4B, nên mọi con số ước
tính ở `KE_HOACH_H37.md` §5 **không dùng lại được**. Đổi lại: không còn rủi ro pháp
lý, không trần ảnh/tháng, và phủ yêu cầu tốt hơn. Loại (c) vì xây sản phẩm có thu
tiền trên một mâu thuẫn chưa được giải trong giấy phép của người khác là rủi ro
không có mặt lợi.

**Kiểm chứng phụ:** kiến trúc **không đổi một dòng nào** khi đổi model — đúng như
nguyên tắc model-agnostic đặt ra ở `KE_HOACH_H37.md` §2. Đây là lần thử thật đầu
tiên của nguyên tắc đó, và nó đứng vững.

**Date:** 2026-08-21 · Chi tiết và trích dẫn nguồn: `LICENSE_NOTES.md`

---

## D-009 — HiDream-O1-Image là model đích; Qwen xuống hàng hai; Klein 9B là thước đo trần

**Thay:** D-008 (phần chọn model). Giữ nguyên phần loại Klein 9B khỏi đường bán.

**Decision:** model đích của H37 là **HiDream-O1-Image** (MIT, ~8B). Cấu hình sản
phẩm: **`base` bf16, sinh ở bucket đã huấn luyện ~4 MP** (16:9 → **2560×1440**),
rồi thu nhỏ về kích thước giao hàng. Qwen-Image-2512 / Edit-2511 giữ làm **ứng
viên đối chứng**, không phải đích. Klein 9B tải về **chỉ để đo trần chất lượng**,
không bao giờ nối vào đường phục vụ khách.

**Reason — năm bằng chứng, ba trong số đó đọc thẳng từ mã trên máy B:**

1. **Chất lượng sửa ảnh cao nhất trong nhóm trọng số mở.** Bảng xếp hạng vote mù
   của Artificial Analysis: HiDream-O1 **Elo 1191** > Klein 9B **1165** = Qwen-Image-
   Edit-Plus-2511 **1165** > Edit-Max-2601 **1159** > Edit-Plus-2509 **1141**.
   Đối chứng thương mại: GPT Image 2 (high) **1256** — chênh 65 Elo, tức thắng
   khoảng 59/41 trong so mù.
2. **Giấy phép MIT** — dễ hơn cả Apache 2.0.
3. **Một model phủ trọn bốn chế độ**: t2i + edit + subject-driven personalization,
   tới 2048×2048. Không phải ghép hai model như hướng Qwen.
4. **ComfyUI 0.30.0 trên máy B đã đỡ sẵn**: `class HiDreamO1`
   (`supported_models.py:1638`), ba node riêng `EmptyHiDreamO1LatentImage`,
   `HiDreamO1ReferenceImages`, `HiDreamO1PatchSeamSmoothing`.
5. **Nó CHÍNH LÀ Qwen3** — điều chủ dự án yêu cầu. Header `comfy/ldm/hidream_o1/
   model.py`: *"Pixel-space DiT built on **Qwen3-VL**: the vision tower
   (Qwen35VisionModel) encodes ref images, the **Qwen3-VL-8B decoder** processes a
   unified text+image sequence, and 32×32 patch embed/unembed shims map raw RGB in
   and out of LLM hidden space."* `HiDreamO1TextConfig` khớp kích thước Qwen3-VL-8B-
   Instruct (hidden 4096, 36 tầng, 32 head). Trong khi **mọi bản Qwen-Image trọng số
   mở vẫn dùng Qwen2.5-VL** — `QwenImage.clip_target()` neo cứng `qwen25_7b.transformer.`,
   không có nhánh Qwen3 nào.

**Alternatives considered:** (a) Qwen-Image-2512 + Edit-2511 (D-008) — Apache 2.0,
mạnh về chữ, nhưng thua Elo sửa ảnh, nặng gấp hơn hai lần, và cần **hai** model cho
các chế độ; (b) Qwen-Image 3.0 — dùng Qwen3-VL thật nhưng **không phát hành trọng
số, không giấy phép, chỉ chạy qua dịch vụ của họ**; (c) mua giấy phép thương mại
Klein 9B — giá không công bố, hai bậc đầu có **trần ảnh/tháng**.

**Trade-off:** HiDream-O1 mới (5/2026) nên hệ sinh thái LoRA/công cụ mỏng hơn Qwen
và FLUX. Kiến trúc pixel-space không VAE là đường ít người đi, ít kinh nghiệm cộng
đồng khi gặp sự cố. Đổi lại: giấy phép dễ nhất, chất lượng sửa ảnh cao nhất, nhẹ
nhất (quan trọng vì chia card với video), và **một model thay hai**.

**Hai đính chính so với những gì tôi nói trước đó** — ghi lại để không ai lặp lại:

- **KHÔNG cần text encoder rời.** Trang tài liệu ComfyUI liệt kê
  `gemma4_e4b_it_fp8_scaled.safetensors` 9,06 GB — **sai với model này**. Mã:
  *"HiDream-O1-Image **tokenizer-only** text encoder. The real Qwen3-VL backbone
  runs inside `diffusion_model.*` **every step**."* Chữ "gemma" duy nhất trong mã
  HiDream-O1 là `q_norm/k_norm: "gemma3"` — tên kiểu chuẩn hoá, không phải model.
  ⇒ **Chỉ một file checkpoint.**
- **Không-có-VAE KHÔNG làm activation bùng nổ.** `PATCH_SIZE = 32` trên pixel ≈
  VAE 8× + patch 2 trên latent. 2560×1440 → 80×45 = **3.600 token**, ngang FLUX ở
  1024². VRAM không phải nút thắt; **thời gian** mới là.

**Date:** 2026-08-21 · Chi tiết: `LICENSE_NOTES.md`, `KE_HOACH_THI_HANH.md` §6–8

---

## D-010 — CHẤT LƯỢNG là tiêu chí duy nhất để chọn; thông lượng chỉ là ràng buộc khả thi

**Sửa đổi:** D-004 (bỏ bậc FAST khỏi mục tiêu sản phẩm) và D-005 (bỏ cascade ngầm).

**Decision:** chủ dự án chốt (2026-08-21): **"tập trung về chất lượng ảnh, không
đánh về số lượng"**. Hệ quả ràng buộc cả kế hoạch:

1. **Cấu hình sản phẩm là cấu hình chất lượng cao nhất chạy được**, không phải cấu
   hình cân bằng. Mặc định: `base` bf16, bucket ~4 MP, số bước cao.
2. **Thời gian mỗi ảnh KHÔNG phải tiêu chí chọn** — nó là **ràng buộc khả thi**:
   ghi lại, đặt một trần chấp nhận được, nhưng **không** dùng để loại cấu hình đẹp
   hơn. Ước tính hiện tại: base ~2,5–3,5 phút/ảnh ở 4 MP (phải đo ở G4).
3. **Không sinh ở độ phân giải ngoài bucket huấn luyện.** Mô tả node ghi rõ model
   huấn luyện ở **~4 MP** và *"lower resolutions go off-distribution and quality
   regresses noticeably"*. Ảnh giao 1920×1080 ⇒ **sinh 2560×1440 rồi thu nhỏ**.
4. **Không thay model ngầm sau lưng khách.** D-005 cho phép cascade sang Gemini khi
   GPU bận. Với chất lượng là trên hết, việc đó **đổi sản phẩm mà khách không biết**
   — hai lần bấm ra hai phong cách khác nhau. Cascade nay là **lựa chọn tường minh
   của khách** ("máy nhà đang bận, dùng đám mây ngay?"), không phải mặc định.
   ⇒ Giao diện **đường 2** của `CHIA_GPU_VOI_VIDEO.md` §7 được chốt.
5. **Chấm chất lượng phải là so mù có kỷ luật**, không phải cảm nhận. Và phải biết
   khoảng cách tới trần: đối chứng với **Klein 9B** (trần trọng số mở) và
   **Gemini 3 Pro Image** (thứ đang bán) **trước khi mở bán**, không phải sau.
   ⇒ Bước đối chứng được **kéo lên trước G10** thay vì nằm cuối.
6. **Bậc FAST không còn là mục tiêu.** Bản `dev` chỉ đo để biết mình bỏ lỡ gì; chỉ
   mở nếu G4 chứng minh chất lượng của nó **không phân biệt được** với `base` trong
   so mù.

**Alternatives considered:** giữ hai bậc QUALITY/FAST và cascade ngầm để tối ưu chi
phí và độ trễ (kế hoạch cũ).

**Trade-off:** thông lượng thấp — ở ~3 phút/ảnh, máy B ra khoảng **20 ảnh/giờ**, và
còn chia với việc video. Chi phí điện vẫn không đáng kể (~50 đồng/ảnh). Cái mất
thật là: khi GPU bận, khách **phải chờ hoặc phải tự chọn** đám mây, thay vì được
phục vụ ngầm. Chấp nhận có ý thức — đó là cái giá của việc không đánh tráo sản phẩm.

**Hệ quả không hiển nhiên, ghi ra để không quên:** ở chế độ chất lượng, **thời gian
chờ dài là bình thường**, nên `NGƯỠNG_CHỜ` 45 giây của D-005 vô nghĩa — một ảnh vốn
đã mất 3 phút. Ngưỡng phải tính theo **thời gian chờ THÊM so với thời gian chạy**,
không phải một hằng số tuyệt đối.

**Date:** 2026-08-21

---

## D-011 — Ba mốc sản phẩm chủ dự án chốt theo khuyến nghị

**Decision** (chủ dự án chốt 2026-08-21, "3 hạng mục theo khuyến nghị của bạn"):

1. **Trần thời gian mỗi ảnh: 6 phút.** Cấu hình vượt trần bị loại ở G4 **dù đẹp
   hơn**. Dưới trần thì thời gian không được dùng để loại (D-010).
2. **Tỉ lệ khung giao hàng, mỗi tỉ lệ neo vào một bucket đã huấn luyện ~4 MP:**

   | Giao hàng | Sinh ở bucket | Ghi chú |
   |---|---|---|
   | 16:9 (1920×1080) | **2560×1440** | mặc định — thumbnail, ảnh bìa |
   | 1:1 | **2048×2048** | ảnh sản phẩm, avatar |
   | 9:16 | **1440×2560** | dọc, cho điện thoại |
   | 4:3 · 3:4 | 2304×1728 · 1728×2304 | mở sau nếu cần |

   **Luôn sinh ở bucket rồi thu nhỏ.** Không sinh thẳng ở kích thước giao hàng.
3. **Cách chấm ảnh: theo lô nhỏ, bất đồng bộ.** Tôi dựng bộ so mù, xáo trộn, gắn
   mã, rồi giao thành lô ~20 cặp một lần. Chủ dự án chấm khi rảnh; không phase nào
   chờ một buổi ngồi chấm liên tục. Lô nào chưa đủ 50 cặp thì kết luận ghi
   **"chưa phân biệt được"** chứ không kết luận non.

**Reason:** ba mốc này chặn G3/G4, và chúng là **quyết định sản phẩm**, không phải
kỹ thuật — chỉ chủ dự án quyết được.

**Trade-off:** trần 6 phút có thể loại mất một cấu hình đẹp hơn ở 8 phút. Chấp nhận:
phải có một trần nào đó, và 6 phút đã gấp đôi ước tính hiện tại cho bản `base`.

**Date:** 2026-08-21

---

## D-012 — Cổng render KHÔNG dùng websocket; ETA việc lạ suy từ lịch sử thời lượng

**Sửa lỗi trong:** `CHIA_GPU_VOI_VIDEO.md` §3–4 (thiết kế ước tính ETA bằng
websocket) — **thiết kế đó không chạy được**, và đây là một lần tôi tự suy ra sai.

**Decision:** cổng render **không mở websocket tới ComfyUI**. Trạng thái job của
chính ta đọc từ `GET /history/{prompt_id}`; "máy có bận không" đọc từ `GET /queue`;
**ETA cho việc lạ (video) suy từ trung vị thời lượng mà cổng tự đo được**.

**Reason — đọc từ mã nguồn ComfyUI 0.30.0 trên máy B:**

`progress` (`main.py:450`), `executing` / `executed` / `execution_error`
(`execution.py:436/496/536/578`) đều gửi kèm **`server.client_id`** — tức chỉ tới
**client đã gửi prompt đó**. Chỉ `status` là quảng bá (`server.py:1397`).

⇒ Cổng render **không bao giờ nhận được** tiến độ của lượt video do dự án
`E:\LTT AI` gửi. Kế hoạch "nghe websocket để ước tính `eta_s` của việc video" là
bất khả thi, không phải khó.

Cách thay: cổng thấy một `prompt_id` lạ xuất hiện trong `/queue` thì bấm giờ; thấy
nó biến mất thì ghi lại thời lượng; trung vị của các lần trước là ước tính cho lần
sau. Chưa có lịch sử ⇒ trả `None` = **"không biết"**, và bên gọi phải coi không
biết là **lâu** — không bao giờ ước lượng lạc quan.

**Alternatives considered:** (a) websocket như thiết kế cũ — bất khả thi; (b) làm
trọng tài bản B ngay (dự án video tự khai job qua giấy phép) — cho ETA chính xác,
nhưng D-006 đã chốt bản A trước; (c) đọc log của ComfyUI để suy tiến độ — mong manh
và phụ thuộc định dạng log.

**Trade-off:** ETA cho việc video **thô** (trung vị lịch sử, không phải tiến độ
thật). Chấp nhận được vì D-010 đã bỏ cascade ngầm: ta chỉ cần hiện "bận, ước tính
còn ~X phút" cho khách tự quyết, không cần con số chính xác để máy tự động chuyển.
Lợi thêm: bỏ được một phụ thuộc (`websocket-client`) và cả một lớp lỗi kết nối lại.

**Ba phát hiện khác cùng lượt đọc mã, đã đưa vào `render_gateway/`:**

- **Client được tự đặt `prompt_id`** khi `POST /prompt`
  (`script_examples/websockets_api_example.py`). Nhờ vậy `prompt_id = uuid5(job_id)`
  ổn định ⇒ idempotency sống sót qua cả lần khởi động lại cổng: kết quả cũ vẫn tra
  được trong `/history`.
- **`POST /interrupt` nhận `prompt_id`** để huỷ đúng một lượt (`server.py:1160`).
  ⇒ `ComfyClient.interrupt()` **bắt buộc** truyền id. Gọi trống sẽ giết lượt đang
  chạy — trên máy B đó có thể là lượt video 70 phút của dự án khác.
- **Mục `/history` xuất hiện CẢ KHI HỎNG**, kèm
  `status: {status_str: "success"|"error", completed, messages}`
  (`execution.py:1282`). ⇒ "có bản ghi" ≠ "thành công". Đây đúng là cạm bẫy Gate 0,
  và có một test chốt riêng cho nó.

**Date:** 2026-08-21

---

## D-013 — VRAM đọc bằng `nvidia-smi`, KHÔNG bằng `/system_stats` hay `torch`

**Sửa lỗi trong:** `render_gateway/busy.py` bản đầu.

**Decision:** mọi câu hỏi *"card đang bị dùng bao nhiêu VRAM"* đi qua **`nvidia-smi`**
(`busy.vram_dung_mb_qua_smi`, trần 8 giây). ComfyUI `/system_stats` chỉ dùng cho
**RAM**. `torch.cuda.mem_get_info()` chỉ dùng để kiểm rò rỉ **trong tiến trình**.

**Reason — đo thật trên máy B, 2026-08-21.** Cho một tiến trình torch khác giữ 8 GB
rồi hỏi ba nguồn *"VRAM còn trống bao nhiêu"*:

| Nguồn | Trả lời | |
|---|---|---|
| `nvidia-smi` | **15.308 MiB** | ✅ đúng |
| ComfyUI `/system_stats` | 23.165 MiB | ❌ mù |
| `torch.cuda.mem_get_info()` | 23.217 MiB | ❌ mù |

Trên Windows/WDDM hai nguồn sau **chỉ thấy tiến trình của chính mình**.

**Lỗi thật nó gây ra:** `busy.py` bản đầu đọc `/system_stats` cho chốt *"VRAM đang
bị giữ bởi tiến trình khác"*. Chốt đó **không bao giờ bắn**. Nó là lưới duy nhất bắt
được một lượt torch chạy **ngoài** ComfyUI — mà máy B có sẵn nhiều script như vậy
(`E:\AI\tools\vlm_worker.py`, `test_*.py`…). Hậu quả: cổng nhận job trong khi card
đã đầy ⇒ OOM giữa job của khách.

**Tìm ra thế nào:** bước **BÁC BỎ** của G1 — *"chạy `gpu_check.py` hai lần, một lần
khi có tiến trình khác giữ VRAM"*. Lần đầu nó **báo đỏ** và trông như `gpu_check.py`
sai; phải điều tra tiếp (kiểm tiến trình giữ có sống thật không, đối chiếu
`nvidia-smi`) mới ra thủ phạm thật. Nếu bỏ qua vì "chắc do script test", lỗi này sẽ
sống tới tận G9 hoặc tới lúc khách gặp.

**Alternatives considered:** (a) `pynvml` trong venv cổng render — thêm một phụ
thuộc để lấy đúng thứ `nvidia-smi` đã cho; (b) hỏi Nexus `/metrics` — chính xác
nhưng thêm phụ thuộc và một credential nữa cho cổng.

**Trade-off:** một tiến trình con mỗi vòng dò. Chấp nhận: vòng dò 2 giây và
`nvidia-smi` chạy vài chục mili-giây. Trần 8 giây vì **`nvidia-smi` treo được**
(driver lỗi, card kẹt) — cùng trần với `platform_core/gpu.py`.

**Điểm đáng ghi:** `platform_core/gpu.py` của nền tảng **đã** chọn hỏi `nvidia-smi`
thay vì dùng thư viện. Trước đây đó là lựa chọn không kèm giải thích; nay có số đo
giải thích vì sao nó đúng.

**Date:** 2026-08-21 · Bằng chứng: `bench/G1_phan_cung.json` §`phat_hien_lon_nhat`

---

## D-014 — Model ảnh đặt trên H: (NVMe), không đặt cùng kho video trên E: (SATA)

**Decision:** trọng số của H37 tải về **`H:\LTT_MODELS\`** (NVMe 970 EVO Plus,
849 GB trống), không vào `E:\AI\models\`. ComfyUI đọc được cả hai nhờ thêm **một
base path thứ hai** vào `extra_model_paths.yaml` — thay đổi **thuần cộng thêm**,
không đụng đường dẫn cũ.

**Reason — đo thật 2026-08-21:**

| Ổ | Đĩa | Ghi | Đọc tuần tự |
|---|---|---|---|
| **E:** (kho model hiện tại) | Samsung 860 EVO **SATA** | 373 MB/s | **476 MB/s** |
| **H:** (849 GB trống) | Samsung 970 EVO Plus **NVMe** | **1.070 MB/s** | ~6× theo thông số |

Nạp nguội một checkpoint 16,4 GB: **~33 giây từ E:** so với **~5–7 giây từ H:**.
ComfyUI ghim model trong RAM nên đó là chi phí một lần mỗi lần khởi động máy —
**nhưng G4 nạp đi nạp lại nhiều lần** khi quét cấu hình (base↔dev, bf16↔fp8), nên
nó cộng dồn thành hàng chục phút.

Thêm một lý do độc lập: E: chỉ còn **341 GB**, còn H: còn **849 GB**.

**Alternatives considered:** (a) để chung `E:\AI\models\` cho gọn — chậm hơn và ăn
vào chỗ trống của kho video; (b) dời cả kho video sang H: — đụng vào thứ đang chạy,
không có lý do gì để làm.

**Trade-off:** H: đang có một máy ảo VMware chạy trên đó (`PVE-Nested`). Đọc model
và I/O của VM dùng chung một NVMe. Chấp nhận: NVMe thừa băng thông, và việc nạp
model là đợt ngắn chứ không liên tục. **G4 phải ghi vào biên bản đo là VM có đang
chạy hay không** — nếu số nạp model dao động mạnh thì đây là nghi phạm đầu tiên.

**Date:** 2026-08-21 · Bằng chứng: `bench/G1_phan_cung.json` §`dia`

---

## D-015 — Đường đích của `scp` sang máy B phải dùng gạch chéo XUÔI

**Decision:** mọi lời gọi `scp` tới máy B dùng đường đích dạng
`E:/AI/ltt_render/scripts/ten.py`, **không** dùng `E:\AI\...`. `deploy.ps1` tự đổi
bằng `-replace '\', '/'` ngay trước khi gọi.

**Reason — sự cố thật 2026-08-21, và nó IM LẶNG.** Chép hai tệp sang B:

```
scp ... "lengo@192.168.2.66:E:\AI\ltt_render\scripts\tai_model.py"     -> tra ve 0
scp ... "lengo@192.168.2.66:E:\AI\ltt_render\scripts\gpu_check.py"     -> tra ve 0
```

Cả hai **báo thành công**. Nhưng chỉ `gpu_check.py` thật sự tới nơi. `tai_model.py`
**không tồn tại ở đích, và cũng không nằm lạc ở đâu** — tôi đã quét cả `C:\`, `E:\`
và thư mục home. Nó biến mất.

Thủ phạm: shell mặc định của OpenSSH trên máy B là **`cmd.exe`**, và nó diễn giải
dấu gạch ngược trong đường dẫn từ xa. Chuỗi `\t` trong `\tai_model.py` bị nuốt.
`\g` trong `\gpu_check.py` thì không phải ký tự thoát nào, nên tệp đó qua được.

⇒ **Lỗi này ẩn theo TÊN TỆP.** Nó chỉ hiện với tên bắt đầu bằng `t`, `n`, `b`, `r`…
Đúng loại lỗi mà một lần thử tay sẽ kết luận nhầm là *"đường deploy chạy được"* —
và nó sẽ ngồi im trong `deploy.ps1` tới tận G7, rồi làm thiếu một tệp ngẫu nhiên
trên máy B mà không ai hiểu vì sao.

**Cách nó lộ ra:** không phải nhờ quan sát tinh, mà nhờ **bước tiếp theo thất bại
một cách cụ thể** — tiến trình tải chết ngay với stdout/stderr đều 0 byte. Chính sự
im lặng bất thường đó (một traceback Python cũng phải in ra gì đó) buộc phải đi tìm,
và `Test-Path` trả `False` mới lòi ra.

**Alternatives considered:** (a) đổi `DefaultShell` của OpenSSH trên B sang
PowerShell — sửa cấu hình toàn máy để chiều một công cụ, và đụng vào thứ dự án video
cũng dùng; (b) escape mỗi dấu gạch ngược thành `\` — phụ thuộc vào việc đoán đúng
quy tắc thoát của cmd.exe, thứ tôi vừa đoán sai một lần.

**Trade-off:** không có. Windows chấp nhận gạch chéo xuôi ở mọi API tệp.

**Lưới an toàn đã có sẵn và nó sẽ bắt được:** bước 4 của `deploy.ps1` **so hash hai
bên**. Nếu `scp` lại nuốt tệp lần nữa, bước đó báo `THIEU <tên tệp>` và dừng. Bài
học rút ra: **`scp` trả về 0 không có nghĩa là tệp đã tới nơi** — phải so hash, và
`deploy.ps1` vốn đã làm.

**Date:** 2026-08-21 · Test chốt: `test_deploy_dung_gach_cheo_xuoi_cho_duong_dich_scp`

---

## D-016 — Template `t2i` ĐÃ XÁC MINH bằng ảnh thật; và card bị chặn bởi CÔNG SUẤT

**Decision:** `render_gateway/workflows/hidream_o1_t2i.json` **hết trạng thái
DRAFT**. Nó đã sinh ra ảnh thật trên máy B, 2560×1440, không sửa một khoá nào.

**Bằng chứng — lượt chạy thật 2026-08-21** (`bench/G3_smoke.json`), fp8, 20 bước,
CFG 5,0, seed 101, lấy mẫu `nvidia-smi` **46 lần** trong lúc chạy:

| | |
|---|---|
| Thời gian | **48,4 giây** (gồm cả nạp model) |
| Ảnh ra | 1 ảnh PNG **4,48 MB** |
| VRAM đỉnh / trung vị | **11.742 / 10.487 MB** — thoải mái trên 24 GB |
| Nhiệt đỉnh / trung vị | **77 / 71 °C** |
| **Công suất đỉnh** | **368,93 W / trần 370 W** |
| Throttle quan sát | `0x1` (idle) và **`0x4` = SW Power Cap** |
| RAM trống trước/sau | 124,8 → 114,0 GB (model vào cache RAM ~10,8 GB) |

**Bốn chỗ tôi ghi là "nghi ngờ nhất" trong `workflows/README.md` đều ĐÚNG:**

1. `CheckpointLoaderSimple` trả `[1,0]=MODEL`, `[1,1]=CLIP`, `[1,2]=VAE` — đúng, kể
   cả với model pixel-space không VAE (ComfyUI chèn `PixelspaceConversionVAE`).
2. `CLIPTextEncode` **là** node mã hoá văn bản đúng cho model này.
3. `sampler=euler` / `scheduler=normal` chạy được; `sampling_settings`
   (`shift 3.0`, `noise_scale 8.0`) ComfyUI áp tự động, không cần node trung gian.
4. **KHÔNG cần text encoder rời.** Trang tài liệu ComfyUI liệt kê
   `gemma4_e4b_it_fp8_scaled.safetensors` 9,06 GB — **sai với model này**, đúng như
   D-009 đã đọc từ mã. Đã tải 0 byte cho nó và mọi thứ vẫn chạy.

**Phát hiện vận hành mới — card bị chặn bởi CÔNG SUẤT, chưa phải bởi nhiệt:**

Đỉnh **368,93 W trên trần 370 W** và throttle `SW Power Cap` xuất hiện ngay trong
lượt 48 giây. Hai tác vụ `LTTAI_GPU_PowerLimit` và `LTT_GPU_PowerLimit_250W` đang
**Disabled**, nên card chạy ở trần mặc định 370 W.

Hệ quả cho các phase sau, **phải đo chứ không được đoán**:

- Nhật ký sự cố 19/08 của dự án video ghi *"trần 250 W / đỉnh 249 W / nhiệt 71 °C"*.
  Ở 370 W ta đã **77 °C sau 48 giây**. Mốc 71 °C đó **không còn dùng được**.
- 3090 tiết lưu vì nhiệt quanh **83 °C**. Lượt 50 bước dài gấp ~2,5 lần; chạy liên
  tiếp trong G4/G9 sẽ đẩy nhiệt lên. **G9 phải đo nhiệt theo thời gian**, không chỉ
  đo đỉnh của một lượt.
- **G4 phải thêm một trục quét: 370 W ↔ 250 W.** Nếu hạ trần công suất chỉ mất ít
  thời gian mà mát hơn nhiều thì đó là lựa chọn đúng cho một máy chạy liên tục —
  và nó cũng trả lại mốc 71 °C mà dự án video đang dựa vào.

**Alternatives considered:** không có — đây là số đo, không phải lựa chọn. Việc chọn
trần công suất thì hoãn tới khi G4 có số.

**Trade-off:** chưa có. Nhưng ghi trước một rủi ro: nếu cuối cùng chọn 250 W thì
mọi số thời gian đo ở 370 W phải **đo lại**, không được quy đổi.

**Date:** 2026-08-21 · Bằng chứng: `bench/G3_smoke.json`

---

## D-017 — HiDream-O1 KHÔNG có ControlNet; chế độ `structure` chưa có đường thi hành

**Decision:** không khai chế độ `structure` trong `catalog.json`. Chỉ có `t2i`,
`edit` (1 ảnh tham chiếu) và `subject` (2 ảnh). G5 phải **thử đạt `structure` bằng
`edit` + lời nhắc giữ bố cục**, và nếu không đạt thì **ghi rõ là không bán được** —
không che bằng giao diện.

**Reason:** grep `comfy/ldm/hidream_o1/*.py` tìm `controlnet|control_net|ControlNet`
trả về **không dòng nào**. Model này là một DiT pixel-space hợp nhất, không có
đường nhận điều kiện không gian kiểu ControlNet.

Đây là chỗ khác biệt thật giữa HiDream-O1 và phương án Qwen bị loại ở D-009:
**Qwen-Image-Edit-2509 có ControlNet gốc** (depth, edge, keypoint), HiDream-O1 thì
không. Khi chọn D-009 tôi đã ghi *"một model phủ trọn bốn chế độ"* dựa trên mô tả
"unified: t2i + editing + subject-driven personalization" — mô tả đó **không nhắc
ControlNet**, và tôi đã suy rộng ra chế độ `structure` mà không kiểm. Nay đã kiểm.

**Ba đường có thể đi, quyết sau khi G5 có số:**

1. **`edit` + lời nhắc** ("giữ nguyên bố cục và tư thế, chỉ đổi phong cách"). Rẻ
   nhất, thử trước. Model nhận ảnh tham chiếu qua conditioning nên có cơ sở để làm được.
2. **Bỏ chế độ `structure`.** Nếu (1) không đạt và hai chế độ kia đủ tốt thì bán hai
   chế độ, nói thẳng là không có chế độ thứ ba. Bộ build pack nói đúng:
   *"Nếu một khả năng không đủ ổn định, ghi rõ thay vì che giấu bằng UI."*
3. **Thêm model thứ hai chỉ cho `structure`** — Qwen-Image-Edit-2511 (Apache 2.0,
   ControlNet gốc). Kiến trúc đã đỡ sẵn nhiều model; giá phải trả là thêm ~20 GB và
   một lần đổi model nữa trên card đã chia với việc video.

**Alternatives considered:** khai `structure` rồi để nó âm thầm chạy như `edit` —
loại thẳng, đó là hứa một thứ không có.

**Trade-off:** người dùng mất một trong ba chế độ đã chốt ở đầu hạng mục, cho tới
khi G5 trả lời. Thà biết bây giờ còn hơn biết ở G10.

**Date:** 2026-08-21 · Test chốt:
`test_khong_khai_che_do_structure_vi_model_khong_co_controlnet`

---

## D-018 — "Có bản ghi `/history`" ≠ "job của ta đã xong"; và `prefix` không được đụng `output/ltt/`

**Sửa hai lỗi thật trong `render_gateway/`**, cả hai lộ ra khi chạy thật trên máy B
ngày 2026-08-21.

### Lỗi 1 — runner tuyên bố xong rồi vẫn xếp hàng lại, đốt GPU cho không

**Triệu chứng:** lượt baseline báo **0,6 giây/ảnh** ở 50 bước 2560×1440 — bất khả
thi — và báo `OK` cả 5 ca. Đồng thời `queue_remaining = 5`, GPU **100 %**, nhiệt
77 °C. Hai điều đó không thể cùng đúng.

**Nguyên nhân:** `prompt_id` sinh **tất định** từ `job_id` (đó là nền của
idempotency, D-012). Nên khi cùng một `job_id` chạy lại, ComfyUI **đã có sẵn** bản
ghi `/history` với `status_str: "success"` từ lượt trước. Runner đọc mỗi bản ghi đó
⇒ tuyên bố xong ngay ⇒ tải về **ảnh cũ** ⇒ **rồi vẫn `POST /prompt` lần nữa**.
Kết quả: trả kết quả cũ *và* đốt thêm ~100 giây GPU mỗi ảnh.

**Bằng chứng dứt điểm:** một prompt **đang CHỜ trong hàng đợi, chưa chạy một bước
nào**, vẫn trả về `/history` với `status_str: "success"`, `completed: true`,
1 output.

**Sửa:** thêm `ComfyClient.da_xong(prompt_id)` — đòi **HAI** điều kiện:
bản ghi `success` **và** `prompt_id` không còn trong `queue_running`/`queue_pending`.
Và thêm **bước tra `/history` TRƯỚC khi xếp hàng**: đã xong thì lấy lại kết quả,
không vẽ lần hai. Đó chính là điều `KE_HOACH_H37.md` §3 đã **hứa** ("kết quả cũ vẫn
tra được trong `/history`") nhưng mã **chưa làm**.

### Lỗi 2 — `filename_prefix` ghi vào thư mục của dự án video

`prefix` mặc định là `ltt/hidream_o1`, mà `E:\AI\ComfyUI\output\ltt\` **đã có sẵn**
kết quả của dự án video (`TEST1_CUOI.mp4`, `TEST5_UP.mp4`, …). Ảnh của ta trộn thẳng
vào đó. Đã đổi sang `ltt_h37/`.

### Cách hai lỗi này lộ ra — đáng ghi vì nó là bài học về quy trình

Không phải nhờ test. Nhờ **đọc con số và thấy nó vô lý**: 0,6 giây cho 50 bước ở
2560×1440. Nếu tôi tin dòng `OK` mà runner in ra, cả G3 đã "đạt" với số đo giả, và
G4 sẽ xây tiếp trên nền đó.

Đây đúng là lỗi Gate 0 mà `CHAM_DIEM.md` §1.1 mô tả — chỉ khác là lần này **máy** in
ra phán quyết sai, và **người** phải đọc thứ máy in ra.

**Ba test chốt đã thêm:** `test_da_xong_doi_HAI_dieu_kien_khong_phai_mot` ·
`test_runner_KHONG_xep_hang_lai_job_da_chay_xong` ·
`test_prefix_khong_dung_thu_muc_output_cua_du_an_video`. Kèm đó, `FakeTransport`
được sửa cho **trung thực hơn**: bản ghi `/history` chỉ xuất hiện **sau** khi prompt
được xếp hàng — gieo sẵn history trong test nay có nghĩa là *"job đã chạy ở kiếp trước"*.

**Date:** 2026-08-21

---

## D-019 — Thời gian tỉ lệ THUẬN với số token; và card tiết lưu vì NHIỆT ở 4 MP

**Số đo, cùng prompt cùng seed, chỉ khác độ phân giải** (bf16, 50 bước, CFG 5,0):

| Độ phân giải | Token ảnh (÷32) | Thời gian | VRAM đỉnh | Nhiệt đỉnh | Throttle |
|---|---|---|---|---|---|
| 1920×1088 | 2.040 | **51,8 s** | 16.303 MB | 78 °C | SW Power Cap |
| 2560×1440 | 3.600 | **~97 s** *(lượt sạch 21:31)* | ~17.200 MB | — | SW Power Cap |
| 2048×2048 | 4.096 | **107,4 s** | 17.071 MB | **83 °C** | Power Cap + **SW Thermal Slowdown** |

**Hai kết luận:**

1. **Thời gian ∝ số token**, rất chặt: 0,0254 · 0,0272 · 0,0262 giây/token. Nên ước
   tính thời gian cho một bucket mới chỉ cần nhân `(W/32)·(H/32)` — không phải đo lại
   từ đầu. *(Con số 2560×1440 lấy từ lượt sạch lúc 21:31, không lấy từ lượt trúng
   cache 1,8 giây — xem D-018.)*
2. ⚠️ **Card CHẠM TIẾT LƯU VÌ NHIỆT ở 4 MP**: 83 °C và cờ `0x20 SW Thermal Slowdown`
   xuất hiện **ngay trong một lượt đơn lẻ**, chưa phải chạy liên tục.

**Hệ quả — đây là ràng buộc thật của sản phẩm, không phải chi tiết vận hành:**

- G9 sẽ chạy **100 lượt liên tiếp** ở cấu hình đích. Nếu một lượt đơn đã 83 °C thì
  chạy liên tục **chắc chắn** tiết lưu, và khi đó **thời gian phình ra** trong khi
  chất lượng không đổi — ta sẽ hứa với khách một con số mà máy không giữ được.
- Trục **370 W ↔ 250 W** thêm ở G4 (D-016) nay **không còn là tuỳ chọn để thử cho
  biết** — nó là đường thoát khả dĩ duy nhất chưa cần đụng phần cứng.
- Nếu 250 W vẫn nóng thì phải nói thẳng: bài toán là **tản nhiệt**, không phải phần
  mềm, và nó nằm ngoài phạm vi H37.

**Về độ phân giải:** 1920×1088 nhanh hơn **47 %** so với 2560×1440. Nhưng mô tả node
cảnh báo dưới ~4 MP là *"off-distribution, quality regresses noticeably"*, và
**tôi không được phép tự chấm** chất lượng (§1.5.3). Một prompt không đủ để kết
luận — theo luật §1.5.5 cần **≥ 50 cặp**. Việc chốt công thức giao hàng vì vậy
**chuyển sang G4** với một lô so mù thật.

**Date:** 2026-08-21 · Bằng chứng: `bench/G3_res_*.json`

---

## D-020 — GIỮ 370 W. Không hạ công suất để hạ nhiệt

**Sửa đổi:** D-016 và D-019 (bỏ trục quét công suất khỏi G4).

**Decision** (chủ dự án chốt 2026-08-21): **không** hạ trần công suất GPU. Card chạy
ở **370 W** mặc định. Hai tác vụ `LTTAI_GPU_PowerLimit` và `LTT_GPU_PowerLimit_250W`
giữ nguyên trạng thái **Disabled**. Trục quét `370 W ↔ 250 W` **bỏ khỏi G4**.

**Reason:** hạ công suất là đánh đổi **chất lượng-trên-hết lấy nhiệt độ**, mà D-010
đã chốt chất lượng là tiêu chí duy nhất. Ở 250 W, mỗi ảnh chậm đi và **không đẹp
hơn một chút nào** — ta trả bằng thời gian để mua một con số trên cảm biến.

**Và quyết định này đứng vững được nhờ trần 6 phút của D-011.** Số đo G3: **92–93
giây/ảnh** ở cấu hình đích. Kể cả khi tiết lưu nhiệt làm chậm **gấp đôi**, ta vẫn ở
~3 phút — **vẫn dưới trần**. Biên đó là thứ cho phép chịu nhiệt thay vì né nhiệt.

**Alternatives considered:** (a) hạ 250 W — chậm hơn, mát hơn, chất lượng không đổi;
(b) giãn cách job để card nguội giữa các lượt — giảm thông lượng, mà thông lượng
không phải mục tiêu (D-010) nên đây là **đường lui nếu G9 cho thấy nhiệt thành vấn
đề thật**; (c) cải thiện tản nhiệt — nằm ngoài phạm vi H37, là việc phần cứng.

**Trade-off — nhận có ý thức, không giấu:** card **sẽ** tiết lưu vì nhiệt khi chạy
liên tục. Đã quan sát `0x20 SW Thermal Slowdown` ở **82–83 °C ngay trong một lượt
đơn lẻ**. Hệ quả: dưới tải liên tục, **thời gian mỗi ảnh phình ra trong khi chất
lượng không đổi**.

**Vì vậy G9 đổi câu hỏi.** Nó không còn hỏi *"có tiết lưu không"* — ta đã biết là
có. Nó hỏi:

1. Chạy 100 lượt liên tiếp thì thời gian mỗi ảnh **phình lên bao nhiêu**, và có
   **chạm trần 6 phút** không?
2. Nhiệt có **ổn định ở một mức** hay cứ leo tới khi máy tự bảo vệ?
3. Có dấu hiệu hỏng nào **ngoài** chậm đi không — sai số tính toán, ảnh lỗi, treo?

Nếu (1) trả lời "không chạm trần" và (3) trả lời "không" thì **chịu nhiệt là lựa
chọn đúng** và không cần làm gì thêm. Nếu chạm trần thì quay lại đường lui (b).

**Date:** 2026-08-21

---

## D-021 — fp8 BỊ LOẠI: trên máy này nó vừa CHẬM HƠN vừa TỐN VRAM HƠN bf16

**Sửa đổi:** D-004 (phần "fp8 để vừa VRAM"). Lý luận cũ đúng một nửa; số đo cho
thấy nửa còn lại **sai theo hướng ngược**.

**Số đo — G4, 3 prompt (chân dung · sản phẩm · **chữ tiếng Việt**), 2560×1440,
cùng seed, trung vị bỏ lượt nạp model:**

| Cấu hình | Bước | CFG | Giây/ảnh | **s/bước** | **VRAM đỉnh** | Nhiệt |
|---|---|---|---|---|---|---|
| bf16 | 30 | 5,0 | **57,7** | 1,92 | **16.784 MB** | 83 °C |
| bf16 | 50 | 5,0 | **96,3** | 1,93 | **16.860 MB** | 84 °C |
| bf16 | 70 | 5,0 | **133,4** | 1,91 | **16.864 MB** | 84 °C |
| bf16 | 90 | 5,0 | **173,4** | 1,93 | **16.903 MB** | 84 °C |
| **fp8** | 50 | 5,0 | **102,1** | **2,04** | **23.992 MB** ⚠️ | 84 °C |
| dev (fp8) | 28 | 1,0 | **30,5** | 1,09 | 23.988 MB | 84 °C |

**Decision:** **bỏ fp8 khỏi mọi cấu hình.** Model đích chạy **bf16**. Bản `dev` giữ
lại chỉ để đối chứng chất lượng ở G6b, không phải để bán.

**Reason — fp8 thua trên CẢ HAI trục, không có trục nào thắng:**

1. **Chậm hơn 6 %**: 2,04 s/bước so với 1,93. Đúng như D-004 dự đoán (Ampere SM 8.6
   không có FP8 tensor core, trọng số phải giải nén về bf16 lúc tính).
2. **Tốn VRAM hơn 42 %**: **23.992 MB so với 16.860 MB** — gần chạm trần 24 GB. Đây
   là điều **ngược hoàn toàn** với lý do người ta dùng fp8. `HiDreamO1` khai
   `optimizations = {"fp8": False}` trong `supported_models.py`, nên nhiều khả năng
   ComfyUI giữ **cả bản fp8 lẫn bản bf16 đã giải nén** trong VRAM.

⇒ Câu "fp8 để **vừa VRAM**, không phải để nhanh hơn" của D-004 **không còn đúng với
model này**: ở đây fp8 **không giúp vừa VRAM, nó làm ngược lại**. Và 23,9 GB trên
card 24 GB là biên **quá mỏng** để chạy sản phẩm — chỉ cần một tiến trình khác chạm
vào card là OOM.

**Ba điều khác cùng rút ra từ bảng trên:**

- **Thời gian tuyến tính theo bước, hằng số 1,91–1,93 s/bước** qua bốn mức. Cùng với
  D-019 (tuyến tính theo token), giờ **ước tính được thời gian cho bất kỳ cấu hình
  nào** mà không phải đo lại: `giây ≈ 1,92 × bước × (W·H)/(2560·1440)`.
- **VRAM bf16 gần như không đổi theo số bước** (16,78 → 16,90 GB). Số bước mua thời
  gian, không mua bộ nhớ.
- **Nhiệt bão hoà ở 84 °C**, không leo tiếp — quan trọng cho D-020: card **tự ổn
  định** chứ không chạy tới mức tự bảo vệ.

**Cả bốn cấu hình bf16 đều dưới trần 6 phút** (D-011): 58 s · 96 s · 133 s · 173 s.
Nên **thời gian không loại được cấu hình nào** — đúng tinh thần D-010: chọn bằng
chất lượng, và **chất lượng phải do chủ dự án chấm mù**, không phải tôi.

**Bước tiếp theo, thiết kế thí nghiệm hai đầu mút:** sinh **cả 30 prompt** ở
**bf16 s30** và **bf16 s90** — hai đầu mút của dải. Nếu so mù không phân biệt được
hai đầu mút thì số bước **không quan trọng** và ta lấy s30 (nhanh nhất, mát nhất).
Nếu phân biệt được thì mới chia đôi tiếp. Rẻ hơn quét cả bốn mức mà kết luận chặt
hơn.

**Date:** 2026-08-22 · Bằng chứng: `bench/G4_*.json`

---

## D-022 — Dò bận đổi từ NGƯỠNG VRAM sang ĐẾM TIẾN TRÌNH python trên card

**Sửa đổi:** D-013 (một nửa). D-013 đúng ở chỗ "hỏi nvidia-smi, không hỏi
`/system_stats`". Nó **sai ở chỗ dùng con số VRAM để kết luận bận**.

**Vì sao lộ ra:** lô 30 ảnh liên tiếp (thí nghiệm hai đầu mút của D-021) là lần đầu
cổng chạy **nhiều job nối nhau**, thay vì 3 lượt rời rạc. Số đo đổi hẳn:

| Kiểu chạy | VRAM đỉnh | Ghi chú |
|---|---|---|
| 3 prompt rời (G4) | **16.784 MB** | ComfyUI nhả bớt giữa các lượt |
| **30 ảnh liên tiếp** | **23.764 MB trung vị · 23.967 MB đỉnh (97,5 %)** | model **thường trú** giữa các job |

⇒ Chốt cũ *"VRAM đang dùng > 4 GB mà ta không giữ job nào ⇒ có kẻ khác"* sẽ **báo
bận vĩnh viễn ngay sau lô đầu tiên**. Nó không phân biệt được *cache của chính
ComfyUI* với *một tiến trình lạ đang chiếm card* — mà đó chính xác là câu hỏi nó
được đặt ra để trả lời.

**Đã thử quy VRAM theo tiến trình và KHÔNG được:**
`nvidia-smi --query-compute-apps=pid,used_memory` trả **`[N/A]` cho MỌI PID** trên
máy B — khớp với `per_process_vram_available: false` mà Nexus vẫn báo. Trên WDDM
không có đường nào lấy được VRAM theo tiến trình.

**Cái đếm được:** `--query-compute-apps=pid,process_name` **có** tên tiến trình. Đo
thật: **26 PID compute** (WDDM tính cả `dwm.exe`, trình duyệt…), trong đó **đúng 1
là python — PID 6736, chủ cổng 8188, tức ComfyUI**.

**Decision:**

- `so_python_tinh_tren_gpu()` là chốt bận mới: `1 python` = chỉ ComfyUI → **rảnh**;
  `≥ 2` = **có việc khác đang tính trên card** → bận.
- `vram_dung_mb_qua_smi()` **giữ nguyên** nhưng **chỉ để báo cáo** trong `/health`.
  Nó không còn quyết định gì.
- Núm `LTT_RENDER_VRAM_BAN_MB` / `Config.vram_ban_mb` **xoá hẳn**. Một núm còn đó mà
  không còn tác dụng là cái bẫy cho phiên sau.
- `None` (không hỏi được nvidia-smi) vẫn là **không né** — không đọc được thì không
  bịa ra "bận", giống D-013.

**Được thêm một thứ mà chốt VRAM không có:** nó bắt được việc chạy **NGOÀI**
ComfyUI. Máy B có sẵn nhiều script torch chạy trực tiếp (`E:\AI\tools\vlm_worker.py`
và tương tự) — hàng đợi ComfyUI không thấy chúng, danh sách tiến trình thì thấy.

**Bằng chứng:** `tests/test_245_render_gateway.py` — 5 test mới, trong đó
`test_vram_gan_day_nhung_chi_co_comfyui_thi_KHONG_ban` neo đúng cảnh 23,9 GB sau lô.

**Ghi chú nhiệt (không phải quyết định, là số đo):** chủ dự án cài phần mềm chỉnh
quạt ngày 22/08. Card **84 °C → 75–76 °C**, quạt 92 %, và **`SW Thermal Slowdown`
chuyển sang "Not Active"** — chỉ còn `SW Power Cap`. Xung ổn định 1830–1860 MHz.
Điều này **củng cố D-020** (giữ 370 W, không hạ W): nguyên nhân bóp xung đã bị gỡ
bằng đường tản nhiệt chứ không bằng đường cắt điện.

**Date:** 2026-08-22

---

## D-023 — Số bước KHÔNG phải núm "mài cho mịn": nó đổi hẳn bức ảnh

**Đo được thế nào:** `tools/do_bo_cuc.py` (mới, G5) so bản đồ cạnh giữa hai ảnh.
Kiểm trên **ảnh thật** trước khi tin: cùng prompt + cùng seed, chỉ khác số bước.

| Cặp (s30 ↔ s90, cùng seed) | Tương quan cạnh |
|---|---|
| p01 chân dung | 0,527 |
| p02 | 0,519 |
| p03 chân dung hồ sơ | **0,747** |
| **p04 bát phở** | **0,142** ⚠️ |
| p05 mèo | 0,431 |
| **sàn** (20 cặp prompt khác nhau) | trung bình **0,017**, cao nhất **0,053** |

Sàn tách bạch hoàn toàn (0,053 < 0,142), nên thước **đọc được** trên ảnh thật chứ
không chỉ trên hình hộp tổng hợp.

**Điều số 0,142 nói ra, xem tận mắt thì rõ:** ở p04, s30 cho **một bát trên bàn gỗ**;
s90 cho **thêm hẳn một người phụ nữ đang bưng bát**. Cùng seed. Cùng prompt.

⇒ **Không thể coi s30 và s90 là "cùng một ảnh, khác độ mịn".** Chúng là **hai bức
ảnh khác nhau**. Điều này đổi cách đọc kết quả so mù sắp tới: cuộc so ấy **không**
trả lời "bao nhiêu bước thì đủ mịn", nó trả lời "**đầu mút nào cho ảnh dùng được
nhiều hơn**". Câu hỏi thứ hai mới là câu đáng hỏi, nhưng phải gọi đúng tên nó.

**Hệ quả cho thiết kế thí nghiệm:** nghĩ rằng chia đôi (s50, s70) sẽ "nội suy" giữa
hai đầu mút là **sai**. Không có dải liên tục nào để chia. Mỗi mức bước là một rút
thăm khác. Nên nếu so mù không tách được s30 và s90 thì kết luận đúng là **"số bước
không đổi tỉ lệ ảnh dùng được"** → lấy s30 vì rẻ hơn ba lần, chứ **không phải**
"chất lượng bão hoà ở 30 bước".

**Một điều thứ hai, chưa phải quyết định nhưng phải ghi lại:** ở p04 **cả hai** ảnh
đều không ra *phở bò tái* — không có nước dùng, không có bánh phở, không có thịt bò
tái. Đây là dấu hiệu **bám prompt với chủ đề Việt Nam** có thể yếu, và nó thuộc
**cổng chọn model (G6b)**, không thuộc cổng số bước. Đưa vào danh mục phải soi khi
so với Gemini 3 Pro Image. **Tôi không chấm — chủ dự án chấm mù** (D-010).

**Bằng chứng:** `tools/do_bo_cuc.py` + `tests/test_248_do_bo_cuc.py` (11 test, trong
đó có test chốt "không có sàn thì KHÔNG được kết luận").

**Date:** 2026-08-22

---

## D-024 — ⚠️ CHẨN ĐOÁN SAI, ĐÃ THAY BẰNG D-025. *(Phần trần VRAM vẫn đứng)*

> 🔴 **ĐÍNH CHÍNH 22/08, sau khi đọc được nhật ký Windows:** máy B **KHÔNG sập**.
> Nó **tự khởi động lại để cài cập nhật Windows** — sự kiện `1074`,
> `MoUsoCoreWorker.exe`, lý do *"Operating System: Service pack (Planned)"*,
> `Reason Code 0x80020010`. Tắt sạch, có chủ đích. **Không** `Kernel-Power 41`,
> **không** `BugCheck`, **không** lỗi `nvlddmkm`; minidump mới nhất từ 14/08.
> Nguyên nhân thật và bài học thật ở **D-025**.
>
> **Cái vẫn đứng nguyên** trong mục này: trần VRAM 97,5 % là biên quá mỏng, và
> việc xếp một cấu hình **chưa ai đo** vào chuỗi tự động là một sai lầm thật.
> Chốt `ngan_sach.py` giữ nguyên, vì nó được biện minh bằng **con số**
> (11.412 token so với 4.096 đã đo), không phải bằng vụ khởi động lại này.
>
> **Cái SAI:** mọi câu quy nguyên nhân cho VRAM ở dưới. Đọc để biết tôi đã lập
> luận sai thế nào, đừng đọc để lấy kết luận.

## D-024 *(bản gốc, giữ lại nguyên văn)* — Máy B SẬP lúc 01:29 22/08. Trần VRAM 97,5 % là lỗi thiết kế của tôi

**Chuyện gì xảy ra:** máy B khởi động lại đột ngột trong lúc chạy lô s90, ở ảnh 21/30.

**Bằng chứng, và một lần suýt kết luận sai:**

| Nguồn | Nói gì |
|---|---|
| `chuoi_h37.log` | chờ từ 01:18:41, **chưa từng chạy lượt nào**, bị giết 01:29:42 |
| `comfy.log` (đuôi thật) | dừng giữa **bước 27/90**. **Không OOM, không traceback, không lỗi** |
| 14 ảnh ngay trước đó | 164–167 giây/ảnh, đều tăm tắp |
| Tiến trình còn lại | **không còn gì** của H37 |

⛔ **Lần đọc log đầu bị CẮT ÂM THẦM.** API `files/read` của Nexus trả **2000/4958
dòng tính từ ĐẦU tệp** kèm cờ `truncated: true`. Tôi đọc "đuôi" ấy, thấy một model
lượng tử hoá lạ (`int8_tensorwise, convrot_w4a4`) và suýt kết luận **"có dự án khác
đang dùng chung ComfyUI"** — một kết luận sai hoàn toàn, dựng trên khúc GIỮA của
log. Chỉ đọc cờ `truncated` mới lộ ra. **Đọc phân trang thì phải đọc cả cờ phân
trang**, cùng một họ với D-018 ("có bản ghi ≠ đã xong").

**Không OOM Python + máy chết đột ngột** ⇒ cạn VRAM ở **tầng driver**, không phải
tầng torch. Trên Windows/WDDM, hết VRAM thì driver đổ sang bộ nhớ chia sẻ và
thrash; torch không bao giờ thấy một `CUDA out of memory` nào để in ra.

**Vì sao cạn — và đây là lỗi của tôi, không phải rủi ro trời cho:**

1. Cấu hình tôi chọn chạy ở **23,9 / 24,6 GB = 97,5 %**, và D-022 đã đo được rằng
   nó **ở lì mức đó giữa các job** vì ComfyUI giữ model thường trú. **Không còn chỗ
   cho ai khác** — mà máy B là máy để bàn có Edge, CocCoc, VS Code, Zalo, và dự án
   video dùng chung.
2. **Bản sửa quạt gỡ mất thứ duy nhất đang ghìm tải.** Trước đó `SW Thermal
   Slowdown` bật liên tục nên card không giữ nổi xung tối đa. Sau khi sửa: 1845 MHz
   và 368 W **liên tục không nghỉ** — tải bền cao hơn mọi thời điểm trước. Tôi đã
   ghi điều đó vào D-022 như một tin tốt mà **không xét mặt còn lại**.
3. **Lượt kế tiếp còn tệ hơn.** Chuỗi sắp chạy G5 `edit`/`subject` với ảnh tham
   chiếu **4 MP** — mỗi ảnh cộng ~4.000 token lên trên 3.600 token của 2560×1440.
   Tôi xếp nó vào chuỗi **tự động, không người canh**, mà **chưa bao giờ đo VRAM cho
   chế độ tham chiếu**. Nếu máy không sập trước thì nó sập ở đó.

**Decision — ba thay đổi, thi hành trước khi sinh thêm một tấm ảnh nào:**

- **Khởi động ComfyUI với `--reserve-vram 3`.** Đã kiểm trong `comfy/cli_args.py`
  trên máy B: cờ có thật, nghĩa đúng là "chừa VRAM cho hệ điều hành và phần mềm
  khác". Trần của ta xuống ~21,5 GB. Giá phải trả là chậm hơn chút do đẩy ra đẩy
  vào — **rẻ hơn một lần reset máy dùng chung**.
- **Chế độ tham chiếu đo THEO BẬC, có người canh**: 1 ảnh @ 1 MP → đo → mới lên.
  Không bao giờ xếp `subject` hai ảnh 4 MP vào chuỗi tự động nữa.
- **Không chạy chuỗi tự động dài trên máy dùng chung khi biên VRAM dưới 2 GB.**

**Cái đã làm ĐÚNG, giữ nguyên:** chốt hai điều kiện của `chuoi_h37.ps1` (hàng đợi
rỗng **và** hết `chay_baseline`) đã giữ đúng — chuỗi không chen vào. Nay có test
chốt nó, cùng test chốt `Start-Transcript` và test chốt `dung_het.ps1` giết cả vỏ.

**Mất mát:** 10 ảnh s90 (~28 phút GPU). s30 còn đủ 30/30 kèm JSON; s90 còn 20/30.
Không mất kết quả G3/G4 nào.

**Còn chờ một mảnh:** nhật ký Windows (`Kernel-Power 41` = mất điện/trip phần cứng,
so với `BugCheck`/`nvlddmkm` = màn hình xanh do driver). Hai nguyên nhân đó đòi hai
cách sửa khác nhau và **tôi không đoán**. Credential Nexus hiện có không mang
`command.run`, `sshd` trên máy B không tự chạy sau khởi động lại ⇒ **cần chủ dự án
chạy giúp một lệnh**.

**Date:** 2026-08-22

---

## D-025 — Máy B tự khởi động lại vì Windows Update. Tôi đã chẩn đoán sai D-024

**Thay:** D-024 (phần nguyên nhân). Phần "trần VRAM mỏng" và chốt `ngan_sach.py`
của D-024 **vẫn đứng** — chúng được biện minh bằng con số, không bằng vụ này.

**Nguyên nhân thật, đọc từ nhật ký Windows trên chính máy B:**

```
01:29:31  Id=1074  User32
  The process C:\WINDOWS\uus\AMD64\MoUsoCoreWorker.exe has initiated the restart
  of computer DESKTOP-MR9CFK0 on behalf of user NT AUTHORITY\SYSTEM for the
  following reason: Operating System: Service pack (Planned)
  Reason Code: 0x80020010   Shutdown Type: restart
```

Khởi động lại lúc **01:30:44**. **Active Hours của máy B là 07:00 → 01:00** — Windows
chờ đúng đến khi hết khung giờ cấm rồi khởi động lại **29 phút sau đó**. Lô s90 cán
qua mốc 01:00 nên bị cuốn theo ở ảnh 21/30.

**Bốn kiểm chứng, tất cả đều phủ định giả thuyết VRAM:**

| Kiểm | Kết quả |
|---|---|
| `Kernel-Power 41` ngày 22/08 | **không có** *(có 13 lần từ 13–21/08, nhưng không lần này)* |
| `BugCheck 1001` | **không có** |
| Lỗi `nvlddmkm` / Display 24 giờ | **không có** |
| Minidump mới nhất | **14/08** — không phải lần này |

⇒ ComfyUI dừng giữa bước 27/90 vì tiến trình **bị tắt đàng hoàng**, không vì hết
bộ nhớ. "Log dừng đột ngột không kèm lỗi" **cũng là dấu vết của một lần tắt máy sạch**
— tôi đã coi nó là dấu vết riêng của tai nạn.

### Tôi đã lập luận sai thế nào

1. Chủ dự án nói *"vram quá tải máy bị reset"*. Tôi lấy đó làm **tiền đề** rồi đi tìm
   bằng chứng ủng hộ, thay vì lấy làm **giả thuyết** rồi đi tìm bằng chứng bác bỏ.
2. Tôi có sẵn một con số nghe rất thuyết phục (97,5 % VRAM) và nó **khớp câu chuyện
   quá gọn**. Sự vừa khít đó lẽ ra phải làm tôi nghi ngờ hơn chứ không phải tin hơn.
3. Tôi **viết cả một mục quyết định trước khi có mảnh bằng chứng quyết định**. Tôi
   có nói "còn chờ nhật ký Windows, tôi không đoán" — rồi vẫn đặt tên mục là
   "Máy B SẬP … là lỗi thiết kế của tôi". Câu rào đón không cứu được một tiêu đề đã
   kết luận.
4. Tôi bỏ qua một cách giải thích **đơn giản hơn nhiều**: máy để bàn chạy Windows thì
   tự khởi động lại để cập nhật, và đó là việc nó vẫn làm.

**Decision — hai thay đổi thật, không liên quan gì tới VRAM:**

- **Việc dài trên máy B phải kết thúc trước 01:00**, hoặc phải hoãn cập nhật trong
  lúc chạy. Một lô 30 ảnh s90 mất ~85 phút; bắt đầu sau 23:30 là đánh cược.
- **Mọi lô dài phải ghi kết quả TỪNG ẢNH ngay khi xong**, không đợi cuối lô mới ghi
  JSON. Lô s90 mất toàn bộ số đo của 20 ảnh đã chạy chỉ vì tệp tổng kết viết ở cuối.
  *(20 ảnh vẫn còn trên đĩa; chỉ số đo thời gian/VRAM/nhiệt là mất.)*

**Bài học chung, đắt hơn cả hai điều trên:** một chẩn đoán nghe hợp lý, có số liệu
đi kèm, và **khớp với điều người dùng vừa nói**, vẫn có thể sai hoàn toàn. Thứ phân
biệt được chỉ có một: **đi lấy cho bằng được mảnh bằng chứng quyết định** — ở đây là
một dòng trong Event Viewer — **trước khi viết ra kết luận**, không phải sau.

**Date:** 2026-08-22

---

## D-026 — `exec` của Nexus GIAM CẢ CÂY TIẾN TRÌNH. Việc dài phải thoát ra bằng WMI

**Bối cảnh:** từ 22/08, Nexus là kênh chính vào máy B; SSH chỉ còn là kênh cứu hộ
(`Ket_noi.md` sinh lúc 13:51 hôm đó).

**Sự cố:** khởi động ComfyUI bằng `POST /exec` → ComfyUI lên tới bước nạp custom
node rồi **biến mất**. Phản hồi của Nexus có sẵn câu trả lời mà tôi đọc lướt qua:

```json
"contained": true
```

`exec` chạy lệnh trong một **job object**. Lệnh kết thúc — hoặc phía gọi hết giờ —
là **cả cây tiến trình con bị giết theo**, kể cả thứ phóng bằng `Start-Process`.

**Decision:** việc phải **sống lâu hơn lời gọi** (ComfyUI, lô đo dài) thì phóng bằng
`Invoke-CimMethod Win32_Process Create`. Nó chạy qua WMI provider host nên **không
nằm trong job object** của `exec`.

⛔ **Và WMI Create KHÔNG có shell**, nên `*> tep.log` trên dòng lệnh chỉ là một tham
số văn bản — **mọi script phóng kiểu này phải tự `Start-Transcript`**. Đây là lần
thứ hai cùng một cái bẫy (lần đầu ở `chuoi_h37.ps1`), nên nay nó nằm trong nhận xét
đầu mỗi script phóng.

**Ba cái bẫy nháy/escape dính trong cùng một buổi**, tất cả cùng một gốc — dựng
lệnh bằng cách nối chuỗi thay vì ghi ra tệp:

| Chỗ | Hỏng thế nào |
|---|---|
| `powershell -Command "... $_.Id ..."` gọi từ trong PowerShell | lớp ngoài nuốt `$_`, lớp trong chỉ còn `.Id` |
| Nối lệnh WMI có nháy lồng qua `exec` | vỡ ở char 215 |
| `"E:\ai\logs\..."` viết trong chuỗi Python không phải raw | `\a` thành BEL → `E:‹BEL›i\logs` |

⇒ **Quy tắc 3 của CLAUDE.md ("đừng viết Python inline qua PowerShell") áp dụng
nguyên vẹn cho Nexus `exec`:** ghi ra `.ps1` bằng `files/write` rồi gọi `-File`.

**Một điều tốt xác nhận được nhân tiện:** ComfyUI hiện ra **hai** PID —
`E:\ai\venv\Scripts\python.exe` (stub) và `...Python312\python.exe` (thật). Chỉ PID
thật có trong `nvidia-smi --query-compute-apps`. Nên luật "1 python trên GPU = chỉ
có ComfyUI" của **D-022 đúng trên hệ thật**, stub không làm nhiễu.

**Date:** 2026-08-22

---

## D-027 ⭐ — HiDream-O1 KHÔNG HIỂU PROMPT TIẾNG VIỆT. Model không yếu, đường vào mới yếu

**Đây là phát hiện quan trọng nhất của H37 tới giờ, và nó lớn hơn mọi câu hỏi về
cấu hình.**

**Triệu chứng, thấy khi soi từng ảnh trong lô so mù:** hàng loạt prompt tiếng Việt
cho ra ảnh **không liên quan gì đến prompt**, và tất cả rơi về **cùng một thứ** —
"người Việt trong một khung cảnh đời thường":

| Prompt tiếng Việt | Ra gì (cả s30 lẫn s90) |
|---|---|
| *"con mèo tam thể ngủ trên bậu cửa sổ"* | người phụ nữ trên giường, **không có mèo** |
| *"bốn người bạn quanh bàn cà phê vỉa hè"* | **một** người |
| *"đội bóng chuyền nữ, tám người xếp hai hàng, cầm cúp"* | **một** người |
| *"ba quyển sách trái, tách trà phải, kính đặt trên"* | hai người cầm khung ảnh |
| *"quả táo đỏ TRONG bát thuỷ tinh TRÊN tờ báo"* | người cầm hộp quà |
| *"rồng đá khổng lồ ngủ trên đỉnh núi tuyết"* | người cầm đèn lồng, **không có rồng** |
| *"thư viện cổ vô tận, cầu thang xoắn"* | hiệu sách hiện đại |
| *"chân dung cận mặt cụ ông, ĐEN TRẮNG"* | người đàn ông đi phố, **ảnh màu** |
| **tiếng Anh:** *"Ship it on Friday" trên bảng trắng* | **hoàn hảo, cả mũi tên** |

**PHÉP THỬ QUYẾT ĐỊNH — dịch đúng prompt sang tiếng Anh, GIỮ NGUYÊN SEED:**

| seed | tiếng Việt | tiếng Anh |
|---|---|---|
| 105 | người phụ nữ trên giường | **mèo tam thể ngủ cuộn tròn trên bậu cửa sổ, nắng qua rèm, thấy rõ từng sợi lông** |
| 109 | một người | **bốn người bạn quanh bàn cà phê, đang cười, thấy rõ cả bốn mặt** |
| 110 | một người cầm bóng | **cả đội xếp hai hàng, cầm cúp** |

**Ba trên ba.** Cùng model, cùng seed, cùng số bước, cùng mọi thứ — **chỉ khác ngôn
ngữ của prompt.**

⇒ **Model KHÔNG yếu.** HiDream-O1 dựng được bố cục phức tạp, đếm được người, hiểu
được quan hệ vị trí — **bằng tiếng Anh**. Bộ mã hoá văn bản của nó bắt được "hơi
hướng Việt Nam" từ ký tự có dấu rồi **vứt bỏ phần ngữ nghĩa**.

**Dấu vết phụ củng cố điều đó:** bản tiếng Anh của "đội bóng chuyền" cho ra cầu thủ
**da trắng** (prompt không nói sắc tộc), còn bản tiếng Việt cho ra người **châu Á**.
Chữ tiếng Việt có tác dụng — nhưng chỉ ở tầng "phong vị", không ở tầng nghĩa.

### Hệ quả — ba điều phải đổi

1. **Nền tảng phải DỊCH prompt sang tiếng Anh trước khi gửi cho model.** Đây là
   một lớp trong `platform_core/image_gen/`, không phải việc của app. Nền tảng đã
   có sẵn LLM (Gemini) để làm việc này. Đây là bản sửa **rẻ nhất và hiệu quả nhất**
   của toàn bộ H37.
2. **Bộ 30 prompt của G3/G4 KHÔNG dùng để so cấu hình được nữa.** Với đa số prompt,
   cả s30 lẫn s90 đều sinh ra "ảnh sai" — so hai cái sai thì không nói lên điều gì
   về số bước. Phải chạy lại benchmark **bằng tiếng Anh** rồi mới so được.
3. ⚠️ **Dịch KHÔNG cứu được chữ tiếng Việt TRONG ảnh.** Nếu khách cần biển hiệu
   "CƠM TẤM SƯỜN BÌ" đúng dấu thì chuỗi ký tự đó buộc phải là tiếng Việt. Đo được:
   biển hiệu ra `CỜM TẤM` / `CỜM TÀM`, poster ra `KUIG MÂN`, `HỐM NAY`, bìa sách ra
   `NHỮNG NHUGẨN THỜ ẤU`. Trong khi **tiếng Anh thì hoàn hảo** ("Ship it on Friday",
   "LTT STUDIOS" gần đúng). Phép thử `e06` (viết không dấu) đang chạy để biết ranh
   giới nằm ở **dấu** hay ở **tiếng Việt nói chung**.

### Điều này nói gì về cách tôi làm việc

Tám lượt chạy, hàng nghìn giây GPU, ba mục quyết định về VRAM/nhiệt/số bước — mà
**không ai nhìn một tấm ảnh nào cho tới hôm nay**. Tôi đo thời gian, VRAM, nhiệt độ,
tính tái lập byte-identical — toàn những thứ đo được tự động — và bỏ qua câu hỏi
duy nhất quan trọng: **ảnh có đúng thứ người ta yêu cầu không.**

Luật §1.5.3 ("người chấm là chủ dự án, không phải tôi") đúng cho việc **chấm thẩm
mỹ**. Nhưng nó đã bị tôi dùng như cái cớ để **không nhìn ảnh chút nào** — trong khi
"ảnh có bám prompt không" là câu hỏi **khách quan**, kiểm được, và lẽ ra phải kiểm
ngay từ G3. **Bổ sung vào §1.5: mọi lô benchmark phải có một bước ĐỌC ẢNH đối chiếu
prompt trước khi báo cáo bất kỳ số đo nào.**

**Date:** 2026-08-22

---

## D-028 — Phần nền tảng của H37: một mục provider + hai module, không sửa app nào

**Thi hành đúng lời hứa của Q102:** model ảnh nội bộ là **một provider**, không phải
một app. Toàn bộ phần thêm vào nền tảng:

| Thêm gì | Ở đâu | Vì sao ở đó |
|---|---|---|
| `ltt_image` | một mục trong `providers.py::REGISTRY` | đúng điểm mở rộng CLAUDE.md hứa |
| `prompt_dich.py` | `platform_core/image_gen/` | năng lực dùng chung, không phải việc của app |
| `cong_render.py` | `platform_core/image_gen/` | client gọi máy B |

**Không sửa `platform_core/` chỗ nào khác. Không sửa `server/`. Không sửa app nào.**

### Bốn quyết định trong mục provider, mỗi cái chặn một lỗi cụ thể

- **`base_url` lấy từ `LTT_RENDER_BASE_URL`, không viết cứng IP LAN.** Thư mục này
  vừa là mã nguồn vừa là **bộ cài** được chép sang máy khác; một địa chỉ nội bộ
  viết cứng sẽ đi theo sang máy không có nó và hỏng ở nơi khó truy nhất. Chưa đặt
  biến ⇒ rỗng ⇒ adapter từ chối chạy. Có test quét `192.168.` trong mã nguồn.
- **Model `is_active=False`.** Nó chỉ bật ở G10, **sau** cổng G6b. Khai một model
  chưa qua cổng chất lượng là mở bán trước khi biết nó có đáng bán không. Đã kiểm:
  `model_options("image")` **không** trả nó về.
- **`capabilities` CHỈ khai `modes: ["t2i"]`.** Chế độ `edit`/`subject` chưa đo được
  VRAM (đang bị `ngan_sach.py` chặn, D-024). Khai trước khi đo là đúng lỗi đã mắc.
- **`canh_bao` nằm ngay trong bản khai**: *"prompt phải là tiếng Anh — nền tảng tự
  dịch"* và *"chữ tiếng Việt CÓ DẤU vẽ trong ảnh bị sai dấu"*. Giới hạn phải nói ra
  cho giao diện dùng, **không giấu sau UI** (blocker của G5).

### `cong_render.py` mang ba luật đã trả giá để học

1. **429 ném `BanError`, KHÔNG ném `CongRenderError`.** Hai lớp ngoại lệ riêng, có
   test chốt `not isinstance(BanError, CongRenderError)`. Gộp làm một là
   `api_pool.danh_dau_loi()` → cooldown → **`disable` sau 5 lần** → model nhà tự tắt
   vĩnh viễn vì hàng xóm chạy video.
2. **Không tự chuyển sang đám mây.** Bận thì báo bận **kèm ETA**; chọn chờ hay dùng
   Gemini là quyền của khách (D-010).
3. **Thiếu `job_id` hoặc `put_urls` thì từ chối NGAY, không chạm vào mạng.** Cái đầu
   là khoá idempotency (D-018); cái sau là hệ quả của Q102 — máy B không giữ khoá R2
   nào nên không có `put_urls` là chắc chắn hỏng giữa chừng.

### `prompt_dich.py` khác `apps/taovideo/translate.py` ở đâu

Nền tảng **đã có** một lớp dịch, nhưng nó nằm trong một app — đúng thứ quy tắc dự án
cấm chép lại. Bản dùng chung này khác ở hai điểm **bắt buộc với ảnh**:

- **Tách chuỗi trong ngoặc kép ra khỏi bản dịch.** `"CƠM TẤM SƯỜN BÌ"` không phải
  câu cần dịch — nó là **chữ sẽ được vẽ vào ảnh**. Dịch đi là biển hiệu ra tiếng
  Anh, tức giao sai hàng. Cơ chế: thay bằng thẻ `@@LTT_TEXT_n@@`, ghép lại sau; thẻ
  nào LLM nuốt mất thì **nối lại vào cuối** chứ không im lặng bỏ.
- **Cảnh báo khi chữ cần vẽ có dấu tiếng Việt** (D-027).

Và một luật: **dịch hỏng thì hỏng job, không gửi bản tiếng Việt.** Gửi bản gốc không
phải phương án dự phòng — nó là giao một tấm ảnh sai mà khách vẫn trả tiền.

**Việc còn nợ, ghi ra để không quên:** `apps/taovideo/translate.py` nay trùng chức
năng với `platform_core/image_gen/prompt_dich.py`. Chưa gộp vì taovideo đang chạy
thật và gộp lúc này là rủi ro không cần thiết. Đây là một việc riêng.

**Bằng chứng:** `tests/test_249_prompt_dich.py` (16 test) ·
`tests/test_250_cong_render.py` (19 test).

**Date:** 2026-08-22

---

## D-029 ⭐ — ĐẾM ĐƯỢC RỒI: tiếng Việt 1/28, tiếng Anh 27/28

D-027 dựa trên 5 cặp. Nay đã soi **cả 30 prompt**, từng ảnh một, đối chiếu từng
prompt — đúng luật §1.5b vừa đặt ra. Cùng seed, cùng model, cùng 30 bước, khác duy
nhất **ngôn ngữ prompt**.

*(28 chứ không phải 30: `p19` và `p20` vốn đã viết bằng tiếng Anh ở cả hai bộ nên
không so được — chúng là đối chứng.)*

| | prompt TIẾNG VIỆT | prompt TIẾNG ANH |
|---|---|---|
| Đúng chủ thể & bố cục | **1 / 28** | **27 / 28** |
| Đúng một phần | 4 / 28 | 1 / 28 *(p03 nhân đôi chủ thể)* |
| **Sai hoàn toàn chủ thể** | **23 / 28** | **0 / 28** |

**Một prompt tiếng Việt duy nhất thành công là `p01`** — *"chân dung người phụ nữ
Việt Nam, ánh sáng cửa sổ buổi sáng"*. Nó thành công vì **nó chính là thứ model rơi
về khi không hiểu gì**: "người Việt trong khung cảnh đời thường". Thành công do
trùng khớp, không do hiểu.

### Vài cặp tiêu biểu, để thấy khoảng cách

| Prompt | Tiếng Việt | Tiếng Anh |
|---|---|---|
| *bát phở bò tái nghi ngút khói* | tô gì đó không phải phở | **đúng bát phở: nước dùng, bánh phở, thịt bò tái hồng, hành, ớt, khói** |
| *chân dung cận cụ ông, ĐEN TRẮNG* | người trung niên đi phố, **ảnh màu** | **đúng: cận mặt, da nhăn, sáng bên hông, đen trắng** |
| *card đồ hoạ đặt chéo, chữ "RTX 3090" góc trên trái* | cô gái cầm **thẻ ngân hàng** | **đúng card đồ hoạ + chữ "RTX 3090" chuẩn** |
| *nhân vật anime tóc xanh dài* | **ảnh chụp thật**, tóc nâu | **đúng anime, tóc xanh dài** |
| *rồng đá khổng lồ ngủ trên đỉnh núi tuyết* | người cầm đèn lồng | **đúng con rồng đá** |
| *thư viện cổ vô tận, cầu thang xoắn* | hiệu sách hiện đại | **đúng, cả tia sáng bụi bay** |
| *ly cà phê sữa đá, nhãn dán TRƠN KHÔNG CHỮ* | rót vào lọ thuỷ tinh, nhãn có chữ | **đúng cốc mang đi, nhãn trắng trơn thật** |

### Ranh giới thứ hai: dịch cứu NGỮ NGHĨA, không cứu CON CHỮ

Bốn prompt có chữ tiếng Việt trong ảnh (`p16` biển hiệu · `p17` poster · `p18` bìa
sách · `p21` thumbnail). Bản tiếng Anh **sửa được toàn bộ bố cục** — biển hiệu nay
là chủ thể, poster gọn gàng, bìa sách xanh đậm chữ trắng ở giữa, thumbnail đúng bên
trái/phải — **nhưng dấu vẫn sai**:

| Cần | Ra |
|---|---|
| `CƠM TẤM SƯỜN BÌ` | `CỘM TÀM SUÔN BÌ` |
| `NHỮNG NGÀY THƠ ẤU` | `NHÙNG NGÃY THỎ ÂU` |
| `GIẢM 50% HÔM NAY` | `GIẤM 50% HÔM NAY` *(gần đúng nhất)* |
| `BẤT NGỜ!` | `BÂT NGỖ!` |

Trong khi chữ **Latin không dấu thì hoàn hảo**: `LTT STUDIOS`, `RTX 3090`,
`COM TAM SUON BI`, `Ship it on Friday` — đúng từng ký tự.

⇒ **Hai lớp hỏng khác nhau, hai cách sửa khác nhau:**

| Lớp | Sửa bằng |
|---|---|
| Model không hiểu ngữ nghĩa tiếng Việt | **dịch prompt** — đã làm, `prompt_dich.py` |
| Model không vẽ đúng dấu tiếng Việt | **ghép chữ sau bằng phông thật** — chưa làm |

**Đề xuất cho lớp thứ hai:** sinh ảnh **không có chữ**, rồi ghép chữ tiếng Việt lên
bằng phông chữ thật ở tầng nền tảng. Đây không phải giải pháp chắp vá — nó là **cách
làm thumbnail chuyên nghiệp vẫn dùng**: chữ sắc nét, đúng dấu, đúng phông thương
hiệu, và **sửa lại được** mà không phải sinh lại ảnh. Cần một quyết định nền tảng
trước khi làm.

### Một điều nhỏ nhưng phải ghi

Bản tiếng Anh **mất neo văn hoá khi prompt không nói rõ**: "đội bóng chuyền nữ" ra
cầu thủ da trắng, "đầu bếp" ra đầu bếp Âu, "cụ ông" ra cụ ông Âu. Nhưng khi chủ thể
tự nó mang tính bản địa (*ruộng bậc thang, người gánh lúa, phở, cơm tấm*) thì **giữ
nguyên rất tốt**. ⇒ Lớp dịch nên **giữ lại từ chỉ bản địa** khi ngữ cảnh khách hàng
là Việt Nam. `LOI_NHAC` trong `prompt_dich.py` đã dặn LLM giữ chủ đề bản địa; cần bổ
sung: khi prompt gốc là tiếng Việt mà **không nói sắc tộc**, thêm gợi ý *Vietnamese*
cho chủ thể người.

**Bằng chứng:** 30 ảnh ghép ở `scratchpad/doi_chieu/`, mỗi tệp một prompt, VI trái
EN phải, cùng seed. Số đo lô: `bench/EN_s30.json` trên máy B.

**Date:** 2026-08-22

---

## D-030 — Số đo lô tiếng Anh, và một dấu hỏi về nhiệt chưa giải thích được

**Lô `EN_s30`, 30 ảnh liên tiếp, bf16, 2560×1440, `--reserve-vram 3`:**

| | |
|---|---|
| Thành công | **30/30** |
| Giây/ảnh | 56,1 · **57,8** (trung vị) · 59,4 |
| VRAM đỉnh | **17.611 MB** = 71,7 % của 24.576 |
| Nhiệt lõi đỉnh | **72 °C** (trung vị cũng 72) |
| RAM trống trước → sau | 113,0 → 112,0 GB — **không rò rỉ** |

Đối chiếu với lô tiếng Việt cùng cấu hình (D-021): 57,7 s/ảnh. **Dịch prompt không
làm chậm đi** — đúng như mong đợi, vì độ dài prompt gần như không đổi số token ảnh.

### ⚠️ Dấu hỏi: `SW Thermal Slowdown` bật ở 13/30 ảnh, trong khi lõi chỉ 72 °C

`0x24` = `0x20` (SW Thermal Slowdown) + `0x4` (SW Power Cap). Nó xuất hiện ở **13
trong 30 ảnh**, nhưng nhiệt **lõi** đỉnh chỉ 72 °C — dưới xa ngưỡng ~83 °C của
GA102. **Con số đó không giải thích được hiện tượng.**

Giả thuyết hàng đầu: **nhiệt mối nối bộ nhớ (memory junction)**, không phải nhiệt
lõi. RTX 3090 dùng GDDR6X, và trên card 3090 thì bộ nhớ nằm cả hai mặt bảng mạch,
nổi tiếng nóng hơn lõi rất nhiều; ngưỡng bóp xung của nó là ~105 °C.

⛔ **KHÔNG đo được để xác nhận:** `nvidia-smi --query-gpu=temperature.memory` trả
`N/A` trên driver 610.88 với card này. Cần công cụ khác (HWiNFO64 đọc được cảm biến
này) — đó là việc cần chủ dự án cài, không làm từ xa được.

**Vì sao ghi lại thay vì bỏ qua:** đây **chưa** là vấn đề (30/30 thành công, thời
gian ổn định trong 3 giây). Nhưng **G9 chạy 100 lượt liên tiếp**, và nếu nguyên nhân
đúng là bộ nhớ thì bản sửa quạt — vốn thổi vào lõi — **không giúp gì cho nó**. Ghi ra
để G9 biết cần soi cái gì, thay vì đến lúc đó mới đi tìm.

**Date:** 2026-08-22

---

## D-031 — Node tham chiếu dùng khuôn CÓ DẤU CHẤM. Và vì sao tôi kết luận sai một lần

**Khuôn dây đúng:**

```json
"10": {"class_type": "HiDreamO1ReferenceImages",
       "inputs": {"positive": ["2",0], "negative": ["3",0],
                  "images.image_1": ["9",0], "images.image_2": ["12",0]}}
```

**`images.image_1`, không phải `image_1`.**

### Cạm bẫy: thông điệp lỗi CẮT MẤT tiền tố

ComfyUI từ chối bằng:

```
node 10: required_input_missing -> image_1
```

Nên bản mẫu viết `image_1` **trông như đúng** — trong khi chính nó là thứ bị từ
chối. Nguyên nhân ở `execution.py:903`:

```python
details = f"{x}" if not v3_data else x.split(".")[-1]
```

Với node V3 thì thông điệp **cắt tiền tố**. Tên thật nằm ở `extra_info.input_name`,
mà bản dò đầu tiên của tôi **không in ra**.

### Tôi đã sai thế nào

Sáng 22/08 tôi đọc `comfy_api/latest/_io.py` §`_expand_schema_for_dynamic`
(dòng 1143–1156), thấy `expected_id = finalize_prefix(curr_prefix, name)` và
`out_dict["required"][expected_id] = template_input`, rồi kết luận:

> *"khuôn dây API là **phẳng**: `image_1`…`image_10`. Bản mẫu hiện tại **viết đúng**."*

Câu đó **sai**, và tôi đã viết nó ra với giọng chắc chắn, kèm số dòng, ngay sau khi
vừa nói *"bắt được lỗi thật"*. `finalize_prefix` **có** nối tiền tố — tôi đọc lướt
qua đúng cái hàm quyết định.

**Cách tìm ra sự thật không phải đọc thêm mã, mà là thử sáu khuôn với ComfyUI thật:**

| Khuôn | Kết quả |
|---|---|
| `image_1` phẳng | từ chối |
| `images` là dict `{image_1: ...}` | từ chối |
| `images` là list `[[...]]` | từ chối |
| dict lồng hai lớp | từ chối |
| **`images.image_1`** | **chấp nhận** |
| **`images.image_1` + `images.image_2`** | **chấp nhận** |

Mỗi lượt thử tốn dưới một giây (ComfyUI từ chối ở khâu kiểm hợp lệ, chưa chạm GPU).
**Sáu lượt thử rẻ hơn một lần đọc mã sai.**

### Bẫy thứ hai, suýt dính ngay sau đó

Tôi chèn một khoá ghi chú `_khuon_day` vào chính tệp workflow JSON cho dễ đọc.
**ComfyUI coi MỌI khoá cấp cao nhất là một node**, và `workflows.nap()` không lọc gì
cả — khoá đó sẽ thành một node không hợp lệ và làm hỏng cả workflow. Hai test hiện
có bắt được ngay (`'str' object has no attribute 'get'`). Ghi chú đã chuyển sang
`workflows/README.md`, và có test mới chốt: **mọi khoá trong workflow JSON phải là
số**.

**Bằng chứng:** `tests/test_245_render_gateway.py` — hai test mới
(`..._KHUON_CO_DAU_CHAM`, `..._chi_chua_NODE_khong_chua_ghi_chu`).

**Date:** 2026-08-22

---

## D-032 — Chế độ tham chiếu ĐẠT, trần nâng lên 7.506 token, và thông số theo tài liệu

### Số đo G5 — chế độ tham chiếu chạy được, nhưng đắt

| Cấu hình | token | VRAM đỉnh | giây (30 bước) |
|---|---|---|---|
| t2i 2560×1440 | 3.600 | 17,6 GB | **57,8** |
| edit 1 ảnh @2 MP | 5.553 | 19,8 GB | 190,6 |
| edit 1 ảnh @4 MP | **7.506** | 19,8 GB | 190,1 |
| subject 2 ảnh @2 MP | **7.506** | **20,0 GB** | 210,8 |

**Hai điều trái trực giác:**

- **Token tham chiếu KHÔNG nhân thời gian theo attention.** 5.553 và 7.506 token đều
  ~190 giây. Chi phí ảnh tham chiếu là **một lần**, không theo bậc. ⇒ dùng thẳng
  4 MP (mức tài liệu khuyến nghị), đừng hạ xuống 2 MP để tiết kiệm — không tiết
  kiệm được gì.
- **Nhưng chế độ tham chiếu đắt gấp 3,3 lần** ảnh thường cùng số bước. Con số phải
  nói với khách, không giấu.

⇒ `TOKEN_DA_DO_TOI_DA` nâng **4.096 → 7.506**, bằng số đo. Cấu hình 2 ảnh @4 MP
(11.412 token) **vẫn bị chặn** vì chưa đo.

### Chất lượng — xem tận mắt

**`edit`**: prompt *"giữ nguyên người, chỉ thay nền thành Hội An đêm đèn lồng"* →
giữ đúng **khuôn mặt, tóc, áo, tư thế, hai tay, cái cốc, mặt bàn**, nền thay hoàn
toàn. 2 MP và 4 MP gần như không khác.

**`subject` 2 ảnh**: người từ ảnh 1 + con mèo tam thể từ ảnh 2 → ảnh ra có **cả
hai**, đúng khuôn mặt và đúng hoa văn lông mèo, đặt trong quán cà phê như prompt.

⭐ **Và đó cũng là bằng chứng ảnh tham chiếu THẬT SỰ có tác dụng** — điều mà issue
#15667 cảnh báo là có thể hỏng im lặng (dạng lồng được chấp nhận nhưng không tác
dụng). Ảnh ra chứa **hai chủ thể riêng biệt từ hai ảnh tham chiếu**; điều đó không
xảy ra ngẫu nhiên. Không cần phép so byte nữa.

### Ba thông số sửa theo TÀI LIỆU, không theo phỏng đoán

| | Trước | Nay | Nguồn |
|---|---|---|---|
| Sampler | `euler` | **`uni_pc`** | model card + bộ node cộng đồng |
| Shift | **không đặt** | **3,0** qua `ModelSamplingSD3` | model card |
| Khử vệt nối ô vá | không có | **`HiDreamO1PatchSeamSmoothing`** | node native |
| Số bước mặc định | 30 | **50** | model card (bản Full) |

Node khử vệt nối đáng nói riêng: kiến trúc này **không có VAE**, làm việc thẳng trên
điểm ảnh theo ô vá 32×32 — vệt nối lưới là vấn đề **của riêng nó**, không phải tuỳ
chọn trang trí.

**Sửa xong thì 12 test cùng đỏ**, tất cả vì `_req` của bộ test khai cứng danh sách
giá trị. Sửa gốc: nó **lấy từ catalog**. Bản mẫu và test không lệch nhau được nữa.

**Date:** 2026-08-22

---

## D-033 — A6 + A7: đường đi một job đã liền mạch, và ba chỗ dễ giao sai hàng

### A6 — lớp dịch nối vào Gemini thật (`dich_gemini.py`)

Dùng lại `api_pool`, **không dựng pool thứ hai** — cùng bài học Public API.

Phần khó không phải gọi HTTP mà là **báo đúng loại lỗi**, vì `api_pool.danh_dau_loi`
phân nhánh theo mã và **báo sai là tự tắt key**:

| Tình huống | Báo gì | `api_pool` làm |
|---|---|---|
| 429 | `429` + `Retry-After` **thật** | cooldown đúng số giây, xoay key, thử lại |
| 401/403 | `401` | đếm lỗi xác thực → `disable` sau 3 lần |
| **400 — prompt của TA sai** | `400`, và **hỏng ngay** | **không phạt key**; và không đốt key thứ hai vì thử nữa cũng hỏng y hệt |
| Lỗi mạng | **không kèm mã** | tính là 5xx/mạng |
| **200 nhưng rỗng** | **không báo lỗi** | thường là bộ lọc an toàn chặn — phạt key là **phạt oan** |

Hai hàng cuối là chỗ dễ sai nhất. Gộp mọi thứ thành "lỗi" thì một prompt sai cú
pháp của ta, hay một lần bộ lọc chặn, cũng làm key tốt bị tắt dần.

### A7 — bộ điều phối (`dieu_phoi.py`)

```
prompt khách
  ① prompt_dich   dịch phần mô tả, giữ nguyên chữ-cần-vẽ
  ② storage       presigned PUT để ra, presigned GET cho ảnh tham chiếu
  ③ cong_render   gửi máy B, chờ, nhận khoá ảnh
```

**Ba ràng buộc, mỗi cái chặn một kiểu "giao sai hàng":**

1. **Prompt gửi đi phải là bản ĐÃ DỊCH.** Gửi bản tiếng Việt thì model vẫn vẽ ra
   một tấm ảnh — chỉ là **không liên quan gì tới yêu cầu**, và **không có lỗi nào
   báo**. Có test chốt bằng cách đọc thân yêu cầu thật sự gửi đi.
2. **`BanError` đi THẲNG ra ngoài, không bị bọc.** App phải phân biệt được "máy nhà
   đang bận, còn N phút" với "sinh ảnh thất bại" — hai câu dẫn tới hai hành động
   khác hẳn của khách. Và tầng này **không tự chuyển sang đám mây** (D-010); có test
   quét mã nguồn để chốt.
3. **Hạn vé PUT phải DÀI HƠN trần chờ.** Vé hết hạn giữa lúc máy B đang vẽ thì ảnh
   vẽ xong rồi mà không đẩy lên được — công sức đổ sông. Có test so hai hằng số.

**Hai chi tiết nhỏ mà thiếu là hỏng:**

- Vé presigned của R2 **ràng buộc `Content-Type`**; máy B gửi sai header là R2 trả
  403. Điều phối luôn xin vé với `image/png`.
- Backend lưu trữ **cục bộ trả `None`** chứ không ném. Gặp `None` mà vẫn gửi job là
  gửi một thứ **chắc chắn hỏng giữa chừng** — nay báo thẳng ngay từ đầu.

**Hết giờ thì HUỶ**, không bỏ mặc: bỏ mặc là máy B vẽ tiếp một thứ không ai còn chờ,
chiếm GPU của việc sau.

**Bằng chứng:** `tests/test_251_dich_gemini.py` (10) · `tests/test_252_dieu_phoi.py` (15).

### Còn lại của giai đoạn A

**A8** — deploy cổng render thành dịch vụ trên máy B (tường lửa chỉ mở cho
192.168.2.17, tự khởi động, thử khởi động lại). Đây là việc **chạm vào máy B** nhưng
**không chạm GPU**.

**Date:** 2026-08-22


---

## D-034 — Bán model nội bộ bằng MỘT APP MỚI (`apps/anhnoibo`), không sửa app nào đang chạy

**Date:** 2026-08-22 · **Trạng thái:** đã thi hành

**Bối cảnh.** Chủ dự án chốt: *"ta chỉ dựng chưa đổi Gemini … mục tiêu khác là sẽ
dùng API cho bên ngoài gọi."* Điều đó **loại bỏ** khuyến nghị "đường B" ở
`DE_XUAT_NOI_VAO_APP.md`: tầng định tuyến chung `sinh_anh.py` chỉ đáng dựng khi có
**từ hai nhánh trở lên**. Không đổi Gemini thì nó có đúng một nhánh — đó là khái
quát hoá non, và `dieu_phoi.py` đã làm trọn việc.

**Quyết định.** Model nội bộ vẫn là **một provider** (`ltt_image`) — điều đó không
đổi. Nhưng **bán** nó ra `/api/v1` thì cần một `ToolSpec`, mà `ToolSpec` chỉ khai
được trong manifest của **một app**. Nên: thêm `apps/anhnoibo/`, tool `image.ltt`.

**Vì sao không nhét vào `taoanh`/`thumbnail`:** hai app đó đang phục vụ khách trả
tiền qua Gemini. Thêm một thư mục vào `apps/` **không đụng ai**; sửa manifest của
chúng thì có. Có test chốt điều này: nếu ai đó đổi `providers` của hai app kia khỏi
`["gemini"]`, test đỏ.

**Bốn cổng, không phải ba.** Ngoài ba cổng fail-closed của Q92 (`api_exposed` ·
`LTT_PUBLIC_API` · `LTT_PUBLIC_API_TOOLS`), H37 có cổng thứ tư: `hidream-o1` vẫn
`is_active=False` cho tới khi qua cổng chất lượng. `api_exposed=True` nghĩa là
**hợp đồng đã đóng băng**, KHÔNG phải **khách gọi được**.

**Hai thứ tôi phải sửa lại sau khi thử với nền tảng thật, không phải theo suy đoán:**

1. Tôi khai `ref_keys: string[]`. Kiểu đó **không tồn tại**. Nền tảng chỉ có
   `image[]`. Sửa xong lại phát hiện điều thật hơn: tầng public API giải **một**
   phiên tải lên cho **một** tham số (`invocation.promote_media`, `sessions: dict`),
   nên phơi một mảng ra API là **hứa một thứ gọi vào sẽ hỏng** — hỏng *sau khi* đã
   giữ credit. `taoanh` đã phải ẩn `image_keys` vì đúng lý do đó. Nay: `image_key`
   (một ảnh) công khai, `image_keys` (tối đa hai) ẩn, dành cho giao diện web.
2. Tôi để mô tả nói *"up to two reference images"* trong khi schema nhận **một**.
   Khách đọc mô tả rồi viết code theo mô tả. Có test cấm cụm đó xuất hiện.

**SÁU bánh cóc đóng băng phải cập nhật trong cùng thay đổi.** Đây là chỗ tốn thời
gian nhất của cả hạng mục, và **cả sáu đều đỏ** khi tôi quên. Danh sách này là thứ
đáng đọc nhất trong tài liệu — người thêm tool thứ bảy sẽ gặp đúng sáu cái này:

| # | Bánh cóc | Phải làm gì |
|---|---|---|
| 1 | `tests/golden/public_api_catalog_v1.json` | sinh lại; **kiểm 5 hợp đồng cũ không đổi một chữ** trước khi ghi đè |
| 2 | `tests/test_190` + `APP_DISPOSITION_V1.md` | khai disposition ở mức app |
| 3 | `tests/test_212` + `APP_API_COVERAGE_FINAL.md` | khai ở mức app **và** mức tool |
| 4 | `tests/test_193` (kê khai bản phát hành) | thêm tên vào danh sách viết cứng |
| 5 | `tests/test_88` (bảng tool của Agent) | `discover_tools()` lấy **mọi** ToolSpec job-based, nên tool mới tự vào |
| 6 | `docs/PUBLIC_API/CONTRACT_BASELINE.json` + `DEVELOPER_GUIDE.md` | `python tools/check_api_compat.py --accept` rồi `python tools/build_public_api_docs.py` |

Cộng thêm **hai cái sinh lại được**, đừng sửa tay: `ho_so_he_thong.txt`
(`tools/build_system_profile.py`) và bộ tài liệu API ở mục 6.

Và **`test_189`** cũng đỏ, nhưng vì một lý do khác nên tôi sửa **chính test** chứ
không sửa dữ liệu: nó so ảnh chụp của 5 tool wave-3 với **toàn bộ** tệp golden. Hai
tập đó trùng nhau **do tình cờ** cho tới hôm nay. Điều nó thật sự muốn khẳng định là
"hợp đồng của wave 3 không trôi", nên nay nó so với **đúng 5 mục đó** trong golden.

**`test_60` cũng đỏ, và đó không phải lỗi của app này** — nó đã đỏ từ trước, vì
`platform_core/image_gen/` và `platform_core/llm/` có **docstring** nhắc tên app
(`apps/taovideo/translate.py`…). Tôi làm bộ quét chính xác hơn thay vì miễn trừ
theo tên app: nay nó bỏ qua **chú thích và docstring**, giữ nguyên phần mã chạy
được. Miễn trừ theo tên sẽ làm mù phép kiểm với chuỗi đó ở mọi nơi; cách này thì
không — có ba test chốt rằng slug trong lệnh, trong điều kiện và trong **chuỗi ký
tự thường** vẫn bị bắt.

`test_189` cũng đỏ, nhưng vì một lý do khác và tôi sửa **chính test** chứ không sửa
dữ liệu: nó so ảnh chụp của 5 tool wave-3 với **toàn bộ** tệp golden. Hai tập đó
trùng nhau **do tình cờ** cho tới hôm nay. Điều nó thật sự muốn khẳng định là "hợp
đồng của wave 3 không trôi", nên nay nó so với **đúng 5 mục đó** trong golden.

**Giá là TẠM.** 5 credit/ảnh, nhân 3 khi có ảnh tham chiếu (đo thật: ~190 giây so
với ~58 giây). Model nhà không tốn tiền provider nhưng **chiếm GPU**, nên giá phải
phản ánh **thời gian máy**. Chốt lại sau khi có số dùng thật.

**Bằng chứng:** `tests/test_253_app_anhnoibo.py` (29) · `tests/test_254_anhnoibo_e2e.py`
(15, gọi HTTP thật — xem D-036). Và `test_252` (15) — vốn **chưa từng chạy lần nào**
— nay đã chạy và xanh.

### ⚠️ Một việc KHÔNG phải của H37 nhưng chặn gate

`apps/vps` tồn tại trong `apps/` nhưng **chưa từng được commit** và **chưa ai phân
loại**. Nó làm `test_190` và `test_212` đỏ — mỗi tệp đúng một test — và đã đỏ như
vậy **từ trước** việc này. Nó khai **không `ToolSpec` nào** và `app_may_be_public()`
trả `False`, nên **không có rủi ro lọt ra API**. Phân loại nó là một quyết định sản
phẩm, không phải một dòng tài liệu — tôi không tự điền hộ.


---

## D-035 — Bốn thứ tôi khai sai vì suy đoán hình dạng của nền tảng thay vì đọc nó

**Date:** 2026-08-22 · **Trạng thái:** đã sửa, có test chốt từng cái

Cả bốn đều **không làm test đỏ khi viết**, và ba trong bốn sẽ hỏng **chỉ khi chạy
thật trên production**. Ghi lại vì cùng một nguyên nhân: tôi viết theo hình dạng
tôi *tưởng* nền tảng có.

**① `ref_keys: string[]` — kiểu không tồn tại.** Nền tảng chỉ có `image[]`.
`registry.discover()` bắt ngay, nhưng nó **không làm sập nền tảng**: app bị thay
bằng một bản rỗng kèm lý do. Tôi đã suýt đọc `tools: []` thành "app chạy tốt".
*Đọc `LoadedApp.error`, đừng đọc `tools`.*

**② `nav` trỏ tới một trang không tồn tại.** App không có `routes.py`, nên
`/anhnoibo` là **404 với mọi người đã đăng nhập**. Hai cách sửa hiển nhiên đều
không chạy: `public=False` chỉ ẩn với khách vãng lai
(`visible_on_surface` trả `authenticated or public`), còn `nav=()` bị
`nav_entries()` **tự sinh lại** một dòng. Cách đúng là `catalog_parent` — cơ chế
hợp đồng đã có sẵn, và `thumbnail` chứng minh nó không chặn đường API.

**③ `ctx.db` / `ctx.storage` / `ctx.owner_id` — `JobContext` không có thứ nào
trong ba.** Nó chỉ cấp `job_id`, `gpu_uuid`, `progress()`. `owner_id` đến từ
`params`; `storage` từ `get_storage()`; `db` từ `get_session()`. Lỗi này **chỉ nổ
lúc chạy thật**: mọi test dùng ctx giả đều cho qua. Nay có test đọc **AST** (so
chuỗi bắt nhầm cả chú thích), cộng một test thứ hai chốt rằng danh sách thuộc tính
"có thật" vẫn khớp `JobContext` — không thì test thứ nhất thành lời hứa cũ.

**④ Thiếu vòng kiểm chủ sở hữu ảnh tham chiếu.** Khoá lưu trữ là **chuỗi khách gửi
lên**. Không kiểm thì khách A đọc được ảnh của khách B bằng cách đoán khoá.
`apps/thumbnail/jobs.py` đã kiểm đúng như vậy — tôi chỉ không đọc nó trước.
Kiểm **đoạn thứ hai** của khoá (`{app}/{user_id}/…`), không phải tiền tố app: một
artifact từ job cũ ở app khác **của cùng người dùng** là hợp lệ.

**Và một thứ không sai nhưng suýt sai:** phiên CSDL. Một lượt vẽ có thể mất 15
phút. Bản đầu của tôi nhận `ctx.db` và dùng nó xuyên suốt — tức giữ một transaction
mở trong lúc chờ mạng. Nay mọi lần chạm CSDL đi qua một phiên **ngắn**, và phiên
được **đóng trước** lượt gọi HTTP. Có test so vị trí hai lệnh đó trong mã nguồn.


---

## D-036 — `image.ltt` đã chạy thật từ ngoài vào, bằng khoá chế độ thử

**Date:** 2026-08-22 · **Bằng chứng:** `tests/test_254_anhnoibo_e2e.py` (15)

`test_253` đọc manifest và catalog — nó **không** chứng minh khách gọi được.
`test_254` thì có: nó cấp một **khoá lập trình viên chế độ thử** (`mode="test"`,
EXT-12) rồi gọi HTTP thật. **Không cần GPU, không cần máy B, không cần credit.**

Đã chạy được, từ ngoài vào:

| | |
|---|---|
| `GET /tools`, `GET /tools/image.ltt` | tool hiện ra, hợp đồng đầy đủ |
| `POST /quotes` | báo giá trước khi chạy; giá nhân đúng theo `count` và theo chế độ |
| `POST /jobs` | job vào hàng đợi, `GET /jobs/{id}` đọc lại được |
| `POST /uploads` → `/content` → `/confirm` | **nhánh ảnh tham chiếu chạy trọn** |
| gọi lại cùng `Idempotency-Key` | trả đúng job cũ, **không** tính tiền hai lần |

Và từ chối đúng thứ phải từ chối: tham số viết sai chính tả · tham số **ẩn** đặt
từ ngoài · `count` vượt trần · thiếu `prompt` · khoá thiếu scope · **upload của tài
khoản khác**.

**Ba chỗ tôi đoán sai hình dạng API rồi mới đọc** — ghi lại vì người sau sẽ đoán y
hệt: đường báo giá là `POST /quotes` chứ không phải `/jobs/quote`; phong bì phân
trang dùng khoá **`items`** chứ không phải `data`; và `POST /jobs` **bắt buộc kèm
`quote` token** — không có thì không tạo được job.

⛔ Nhắc lại cho khỏi hiểu nhầm: `LTT_PUBLIC_API_TOOLS` trong tệp test **chỉ mở
trong tiến trình test**. Production đọc `secrets/app.env`, nơi biến đó vẫn **rỗng**.
Khách thật vẫn chưa gọi được, và đó là đúng.


---

## D-037 — Chốt dò bận HỞ với tiến trình không phải python; máy B có BA hộ dùng chung GPU

**Date:** 2026-08-22 22:27 · **Trạng thái:** đã sửa, 6 test mới

**Phát hiện thế nào.** Chủ dự án thấy GPU máy B đang hoạt động và hỏi *"có phải dự
án của ta không"*. Đo thật:

| | |
|---|---|
| `nvidia-smi` | **19.977 / 24.576 MiB** dùng, tải **0–6 %**, 32 °C, 18 W |
| ComfyUI `/system_stats` | còn trống **22.767 MB** ⇒ nó **tự** dùng có 1.809 MB |
| Thủ phạm | `llama-server.exe` PID 32292, `Qwen3.8-27B-UD-Q4_K_M.gguf`, RAM 15,9 GB |

**Không phải dự án của ta, và cũng không phải dự án video.** Đó là một **dự án thứ
ba**: `H:\LTT_LLM` — dịch vụ `LTTLlamaSwap` + `LTTLlmGateway`, cổng 8280/8299, lên
lúc 21:29. `CLAUDE.md` mới chỉ cảnh báo về dự án video.

### Lỗ trong `busy.py`

`so_python_tinh_tren_gpu()` đếm tiến trình có tên chứa `python`. `llama-server.exe`
**không phải python** ⇒ phép đếm trả về **1** (chỉ ComfyUI) ⇒ cổng báo **RẢNH** trong
khi card chỉ còn **4,6 GB**, mà một lượt vẽ cần **17,6–20 GB**. Nhận job lúc đó là
hết VRAM giữa chừng, **im lặng**.

Tiền đề đã viết thẳng trong docstring — *"26 PID compute, đúng 1 là python, và nó
chính là ComfyUI"* — **đúng lúc đo**, và **sai từ lúc dự án LLM lên**. Đây là loại
lỗi tệ nhất: một phép đo đúng bị dùng làm một quy luật.

### Chốt mới — và nó đến từ chỗ không ngờ: **sự "mù" của ComfyUI**

    ngoại nhân giữ  =  (nvidia-smi dùng)  −  (ComfyUI tự dùng)

Trên Windows/WDDM `/system_stats` chỉ thấy bộ nhớ của **chính nó**, `nvidia-smi`
thấy **toàn card**. Chính điều làm `/system_stats` vô dụng cho câu hỏi cũ lại làm nó
thành **đúng mảnh còn thiếu** cho câu hỏi này.

Số thật tối nay: 19.977 − 1.809 = **18.168 MB người khác giữ**, còn dùng được
**6.408 MB** < ngưỡng **20.500** ⇒ **bận**. Đúng.

**Vì sao công thức này không dính lại cái bẫy đã giết ngưỡng VRAM cũ:** phần ComfyUI
tự giữ **bị trừ đi**. Lô 30 ảnh làm VRAM ở lì 23,9 GB thì `ngoại nhân = 0` ⇒ **rảnh**.
Có test cho đúng cảnh đó.

**Giữ CẢ HAI chốt**, chúng bắt hai thứ khác nhau:

| Chốt | Bắt được | Mù với |
|---|---|---|
| đếm tiến trình python | việc **đang tính**, kể cả chiếm ít bộ nhớ | tiến trình không phải python |
| hiệu hai nguồn VRAM | việc **đang giữ bộ nhớ**, kể cả không tính gì | việc tính toán mà không giữ bộ nhớ |

**Ngưỡng 20.500 MB lấy từ số đo thật** (đỉnh chế độ ảnh tham chiếu 20.000 + đệm), có
test cấm hạ xuống dưới 20.000 — hạ cho lọt là chọn một con số chưa ai đo (D-026).

**Bằng chứng:** `tests/test_245_render_gateway.py` (nay 130 test, 6 cái mới cho chốt
này, một trong đó chạy đúng bộ số thật của 22:27).

⚠️ **Cổng render đang chạy trên máy B là bản CŨ** (khởi động 19:30, trước bản sửa
này). Phải deploy lại trước khi chạy phiên đo GPU.


---

## D-038 — Tách G6b làm hai nửa: nửa Gemini chạy được **khi GPU đang bận**

**Date:** 2026-08-22 · **Bằng chứng:** `tools/doi_chung_gemini.py`,
`tests/test_255_doi_chung_gemini.py` (14)

**Bối cảnh.** Chủ dự án dành GPU máy B cho một dự án khác. Kế hoạch cũ coi G6b là
**một** việc phải chờ GPU. Đó là một giả định chứ không phải một ràng buộc: G6b so
model nhà với **Gemini 3 Pro Image**, và nửa Gemini là **API đám mây**.

**Quyết định.** Tách G6b:

| Nửa | Cần GPU? | Chạy được lúc nào |
|---|---|---|
| Ảnh của **Gemini** (30 prompt) | **không** | ngay bây giờ |
| Ảnh của **model nhà** (30 prompt) | có | khi card rảnh |
| Dựng lô so mù + chấm | không | sau khi có cả hai |

⇒ Khi tới lượt GPU rảnh, **phiên đo ngắn đi một nửa**.

**Bốn thứ cưỡng chế bằng mã, không bằng trí nhớ:**

1. **Mặc định KHÔNG tiêu tiền.** Không có `--that` thì chỉ in kế hoạch. Một lệnh gõ
   nhầm không được phép thành một hoá đơn. Chạy thử cũng **không lấy khoá** — lấy
   khoá là chạm CSDL và ghi telemetry.
2. **Cùng một văn bản cho cả hai bên** (`bench/prompts_30_en.json`, đúng bộ phía ta
   dùng) và **cùng tỉ lệ 16:9** như G3. So hai model bằng hai prompt khác nhau thì
   con số đo được là khác biệt giữa hai *prompt*.
3. **Ghi kích thước thật từng ảnh.** Ảnh to hơn trông "nét hơn" bất kể model; bản kê
   tự nói ra cái bẫy đó để bước dựng lô biết phải chuẩn hoá.
4. **Chạy lại được.** Ảnh đã có thì bỏ qua; một prompt hỏng không làm hỏng cả lô —
   29 ảnh kia đã trả tiền rồi.

Và **không in thân lỗi của Gemini ra log**: nó có thể vọng lại chính khoá vừa gửi.
Có test chốt bằng một khoá giả trong thân phản hồi 400.

### ⚠️ Điều tệp này KHÔNG giải, ghi ra để không ai tưởng là đã giải

Cả hai bên nhận prompt **tiếng Anh**, vì đó là so sánh *cùng đầu vào*. Nhưng sản
phẩm thật thì khách gõ **tiếng Việt**: đường của ta là *dịch → model nhà*, còn
Gemini **hiểu thẳng tiếng Việt**. Nên lô này trả lời *"model nào vẽ đẹp hơn với cùng
một câu tiếng Anh"* — **không** trả lời *"khách gõ tiếng Việt thì bên nào ra ảnh
đúng ý hơn"*. Câu thứ hai cần một lô riêng, và nó đo **cả lớp dịch** chứ không chỉ
model. Đó là câu quyết định việc mở bán, nên đừng nhầm hai câu với nhau.

**Chi phí:** ~3,90 USD cho 30 ảnh (ước tính, in ra trước khi gọi). Chưa chạy thật —
chờ chủ dự án đồng ý vì đây là tiêu tiền.


---

## D-039 — Nửa Gemini đã có 30 ảnh, và nó lộ ra một thiên lệch **có lợi cho ta**

**Date:** 2026-08-22 23:30 · 30/30 ảnh, 0 hỏng, ~3,90 USD

### Số thật, và vì sao nó quan trọng

| | Gemini 3 Pro Image | Phía ta (G3) |
|---|---|---|
| Kích thước | **1376 × 768** | **2560 × 1440** |
| Định dạng | **JPEG** (nén mất mát) | **PNG** (không mất mát) |

Chênh **1,86 lần chiều dài**, và nó lệch **về phía có lợi cho ta**: ảnh to hơn,
không nén mất mát, thì trông nét hơn **bất kể model nào vẽ**. Nếu dựng lô so mù từ
hai bộ này y nguyên, kết luận *"model nhà đẹp hơn"* sẽ **đúng về mặt số liệu và sai
về mặt sự thật** — ta đo độ phân giải chứ không đo model.

⇒ **Chuẩn hoá là bắt buộc trước khi dựng lô**: hạ cả hai về cùng cạnh dài và cùng
định dạng. Đã ghi vào `bench/G6b_gemini/ban_ke.json` để bước sau không phải nhớ.

### Lỗi tôi mắc, và vì sao nó suýt không ai thấy

Bản đầu **giả định Gemini trả PNG**: đặt đuôi `.png` cho cả 30 tệp và đọc kích
thước bằng `kich_thuoc_png`. Gemini trả **JPEG**. Hai hậu quả:

1. 30 tệp mang đuôi sai — công cụ nào tin vào đuôi sẽ hỏng.
2. **Cái chốt "ghi kích thước để bước sau biết mà chuẩn hoá" không chạy một lần
   nào.** Nó chỉ in *"không rõ kích thước"* 30 lần.

Nó lộ ra **chỉ vì dòng in có in kích thước**. Nếu tôi in "xong" thay vì in số đo
được, lô này đã trông như thành công hoàn hảo, và cái thiên lệch 1,86 lần đã đi
thẳng vào kết luận cuối. **Bài học chung: in thứ ĐO ĐƯỢC, đừng in thứ mình mong.**

Đã sửa: `nhan_dang()` đọc **byte thật** (PNG/JPEG/WebP), đặt đuôi theo đó, đọc kích
thước JPEG từ khung SOF. Phép kiểm *"đã có ảnh chưa"* nay dò **mọi đuôi** — dò một
đuôi là lần chạy sau tưởng chưa có rồi **trả tiền lại một lần nữa**.

**Bằng chứng:** `tests/test_255_doi_chung_gemini.py` (18). Bản giả trong test nay
mặc định là **JPEG 1376×768** — đúng thứ nhà cung cấp trả thật, không phải thứ tôi
đoán.


---

## D-040 — Đã deploy lên production và nghiệm thu; fail-closed giữ nguyên

**Date:** 2026-08-22 23:5x · commit `58c0b15` + `157ec2a` · `alembic c1f4a2b70e51`

Máy chủ chưa phục vụ khách nên chủ dự án cho deploy dù cây mã đang có ba luồng việc
của ba phiên. Nghiệm thu, **kiểm trên URL công khai chứ không chỉ loopback** (quy
tắc 5b):

| Kiểm | Kết quả |
|---|---|
| 3 dịch vụ | Running · `deploy exit rc=0` |
| `/health/ready` loopback **và** `https://app.lttstudios.com` | `200 {"status":"ready","database":"ok"}` |
| App đã deploy | **18**, không app nào lỗi; `anhnoibo` nạp với tool `image.ltt` |
| `alembic` | `5a3a13144782` → **`c1f4a2b70e51`**, tạo **5 bảng** của dự án VPS — đúng như đã báo trước |
| `LTT_RENDER_BASE_URL` | bản chạy đọc được `http://192.168.2.66:8199` |
| `hidream-o1.is_active` | **False** — cổng chất lượng vẫn khoá |
| `LTT_PUBLIC_API_TOOLS` | **rỗng** ⇒ catalog công khai **rỗng**, `/api/v1/tools` trả **401** |
| Giao diện công khai | 9 thẻ app, **0 lỗi console, 0 request hỏng**, CSS đã cache-bust `?v=b545037b` |
| `/anhnoibo` | **404 sạch** (đúng: app chưa có UI, và `catalog_parent` giữ nó khỏi header) |
| Cổng render từ máy A | TCP 8199 mở + **401**; ComfyUI 8188 **đóng** với LAN |

⭐ **Điểm đáng ghi nhất: thêm một tool `api_exposed=True` vào production KHÔNG mở
thêm gì cho khách.** Đó là Q92 làm đúng việc, và nay đã kiểm trên máy thật chứ không
chỉ trong test.

### Việc còn lại duy nhất không chặn bởi GPU

**Chưa có khoá `ltt_image` trong APIKEYS** (`0` khoá; phiên kia đã thêm `ltt_llm`).
Không có nó thì `apps/anhnoibo/http_cong.py` không lấy được bearer token. Token nằm
trên máy B ở `C:\ProgramData\LTTRender\gateway.env`. **Chủ dự án tự thêm** — token
là bí mật, không đi qua phiên trò chuyện.
