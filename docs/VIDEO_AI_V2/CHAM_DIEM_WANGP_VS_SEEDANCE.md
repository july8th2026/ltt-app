# Chấm điểm: WanGP so với Seedance 2.0 — và ta đang ở đâu

**07/09/2026.** Đọc `wgp.py` · `wan_handler.py` · `docs_API.md` · `docs_MODELS.md`
(WanGP SHA `1e1dd275`) đối chiếu `apps/taovideo` (Seedance 2.0 **đang bán thật**).

---

## 0. 🔴 Đính chính một sai lầm của chính tôi

Các phân tích trước của tôi lặp lại cụm **"hai model của ta"** (`t2v_2_2`,
`i2v_2_2`) tới mức biến một **lựa chọn khởi động của P00** thành một **giới hạn
kiến trúc**, rồi thiết kế giao diện theo cái giới hạn tự dựng ấy.

Số đo cho thấy nó sai tới mức nào:

| | Số thật | Nguồn |
|---|---|---|
| Handler họ model của WanGP | **28** | `wgp.py:2504` |
| Model type **riêng họ Wan** | **46** | `wan_handler.py:74-78` |
| Model type ta đã nối | **2** | `apps/lttvideo/ho_so.py` |

⇒ **Độ phủ hiện tại: 2/46 trong một họ, trên 28 họ.**

Và tôi đã kết luận *"WanGP không có tag ⇒ mô hình Seedance không ánh xạ sang
đây"* — rồi hai giờ sau tự tìm ra `image_ref_choices` của VACE, một **mảng có
thứ tự + vai trò**, gần Seedance hơn hẳn. Phép đo không sai; cái sai là **để một
phép đo hẹp làm khung cho cả sản phẩm**.

⭐ Và có một công cụ tôi **chưa từng gọi**, dù nó tồn tại sẵn để trả lời đúng câu
hỏi này (`docs_API.md:240`):

```python
session.list_model_defs(main_output="video", inputs="image")
session.get_model_schema(model_type)      # nang luc + vai tro media + gioi han
```

Tự khai báo, máy đọc được, không phải suy. Tôi đọc mã tay trong khi WanGP có
sẵn **API tra cứu năng lực**.

---

## 1. Seedance 2.0 khai gì — đo từ chính mã đang thu tiền

`apps/taovideo/models.py` + `modelark.py` + `refs.py`:

```python
# modelark.py:33 — toan bo be mat request
{"model": …, "content": [...], "ratio": …, "resolution": …,
 "duration": …, "generate_audio": bool, "watermark": False}

# refs.py:19 — vai tro anh HOP LE
VALID_IMAGE_ROLES = {"reference_image", "first_frame", "last_frame", "mask"}
#  + video_url -> role "reference_video"
#  + audio_url -> role "reference_audio"

# models.py
resolutions : 480p · 720p · 1080p · 4k        (seedance-2.0)
durations   : 4 5 6 8 10 12 15 giay
aspects     : 16:9 · 9:16 · 1:1 · 4:3 · 3:4 · 21:9
prompt_controls : camera · motion · visual_style
supports_seed   : True
```

⇒ **Đây là toàn bộ Seedance 2.0.** Bảng dưới chấm WanGP theo đúng danh sách này,
rồi chấm tiếp những gì WanGP có mà Seedance **không có**.

---

## 2. BẢNG CHẤM — phần Seedance có

Cột **Bằng chứng**: `M` = đọc thẳng trong mã · `D` = tài liệu WanGP ·
`?` = **phải đo trên máy thật** trước khi tin.

| # | Hạng mục | Seedance 2.0 | WanGP — model + cờ | BC | Ta đã nối |
|---|---|---|---|---|---|
| 1 | Chữ → video | ✅ | `t2v_2_2`, `ltx2_*`, `k5_pro_t2v`, `hunyuan_1_5_t2v`, `longcat_video` | M | ✅ |
| 2 | Khung mở đầu | `first_frame` | `image_start` + `image_prompt_type="S"` | M | ✅ |
| 3 | Khung kết thúc | `last_frame` | `image_end` + `"E"` ⚠️ **`E` một mình bị gỡ âm thầm** (`wgp.py:1458`) | M | ❌ |
| 4 | Ảnh tham chiếu (nhiều) | `reference_image` ×N, trỏ bằng `@IMG_n` | `image_refs[]` + `"I"` — `vace_14B`, `ltx2_22B_msr_v2` (2–5 ảnh), `phantom_14B`, `standin`, `lynx` | M/D | ❌ |
| 5 | Mặt nạ | `mask` (1 kiểu) | `video_mask`/`image_mask` + `"A"` — VACE khai **11 chế độ**: `"" A NA XA XNA YA YNA WA WNA ZA ZNA` | M | ❌ |
| 6 | Video tham chiếu | `reference_video` (1 vai trò) | `video_guide` + `"V"` — VACE khai **16 chế độ** điều khiển | M | ❌ |
| 7 | Âm thanh tham chiếu | `reference_audio` | `audio_guide` + `"A"` — `multitalk`, `infinitetalk`, `fantasy` | M/D | ❌ |
| 8 | Sinh nhạc nền | `generate_audio: bool` | **hai đường**: model tự sinh (`ltx2_*`, `ovi_1_1`, `magi_human`) *hoặc* hậu kỳ `mmaudio`/`prismaudio` | D | ❌ |
| 9 | Độ phân giải tới 4K | 480p→4k | `3840x2176`, cả `5440x3072` (`resolutions.py`) + `spatial_upsampling` `lanczos*2`/`flashvsr*2`/`coz*4` | M | 🟡 chỉ 720p |
| 10 | Thời lượng 4–15s | 7 mốc rời | `video_length` số khung **hoặc chuỗi giây `"10s"`**; `normalize_output_frame_count` **không có trần trên**; cửa sổ trượt cho video dài hơn | M/D | 🟡 |
| 11 | Tỉ lệ khung | 6 tỉ lệ | 54 cặp `WxH` rời (`resolutions.py`) — phủ cả 6 | M | 🟡 |
| 12 | Seed | ✅ | `seed` | M | ✅ |
| 13 | Điều khiển máy quay | qua **prompt** (`prompt_controls`) | qua **model**: `k5_pro_t2v` *"controllable camera motion"*, `vista4d` *"reshoot from a new camera trajectory"*, `recam_1.3B` | D | ❌ |
| 14 | Trỏ ảnh từ prompt | `@IMG_n` — **địa chỉ theo vị trí** | ❌ **không có** — prompt vào thẳng T5 ⇒ tag thành **chữ thật**, gây nhiễu. Thay bằng **vị trí + chữ vai trò** (`I`/`KI`/`FI`) | M | — |

### 🔑 Đọc bảng trên ra một câu

**13/14 hạng mục Seedance có, WanGP có — và 5 trong số đó WanGP làm RỘNG HƠN**
(mặt nạ 11 vs 1, điều khiển video 16 vs 1, độ dài không trần, độ phân giải tới
5440px, máy quay bằng model chứ không bằng lời).

Hạng mục **duy nhất** Seedance có mà WanGP không: `@IMG_n`. Và đó **không phải
thiếu sót cần vá** — nó là hệ quả của kiến trúc: Seedance nhận cả prompt lẫn ảnh
trong **một mảng `content[]`**, nên nó phải có cách trỏ; WanGP nhận ảnh qua **khe
riêng**, nên vị trí trong mảng `image_refs` **đã là** địa chỉ.

Bản dịch trực tiếp:

```
Seedance:  role="reference_image"  + "@IMG_2 cam chiec den"
WanGP  :   image_refs[1]           + video_prompt_type chua "I"
```

---

## 3. BẢNG CHẤM — phần WanGP CÓ mà Seedance KHÔNG

Đây là phần trả lời câu *"khai thác sức mạnh của nó"*.

| # | Năng lực | Model | BC |
|---|---|---|---|
| 15 | Ảnh **bối cảnh/nền** tách riêng khỏi ảnh nhân vật | `"KI"` — ảnh #1 giữ nền, #2..N **cắt bỏ nền** tự động | M |
| 16 | Neo ảnh vào **thời điểm** trên dòng thời gian | `"FI"` + `frames_positions` (`1`=đầu, `L`=cuối cửa sổ) | M |
| 17 | Truyền chuyển động: pose · depth · scribble · canny · flow · gray · inpaint · identity | `process_map_video_guide` (`wgp.py:4656`); ghép đôi được (`PDV` = pose+depth) | M |
| 18 | Inpaint / outpaint trong video | VACE + `video_guide_outpainting` | M |
| 19 | Thay diễn viên · hoạt hoá nhân vật | `animate`, `animate2`, `scail2_14B`, `steadydancer`, `mocha` | M/D |
| 20 | Giữ nguyên gương mặt (face swap) | `lynx`, `lynx_lite`, `vace_lynx_14B`, `standin` | M/D |
| 21 | Nhân vật nói theo audio (talking head) | `multitalk`, `infinitetalk`, `fantasy`, `longcat_avatar_v1_5`, `magi_human` | M/D |
| 22 | **Nối dài video** vô hạn bằng cửa sổ trượt | `video_source` + `"V"`, `sliding window` | D |
| 23 | Cắt đoạn nguồn **không cần xuất clip trung gian** | `file.mp4\|start_frame=57542,end_frame=57782,audio_track_no=2` | M |
| 24 | Nâng nét / nội suy khung / film grain **trong cùng hàng đợi** | `submit_media_postprocessing`: `rife*2`, `dlssg*4`, `flashvsr*2`, `h3facerefine` | M |
| 25 | Thay giọng nói trong video | `seedvc_one_speaker` / `seedvc_two_speakers` | M |
| 26 | Tách nhạc nền khỏi thoại | `remove_background` (audio) | M |
| 27 | Thay/sinh nhạc nền cho video có sẵn | `submit_audio_remux`: `custom`, `mmaudio`, `prismaudio` | M |
| 28 | Chỉnh sáng lại cảnh (relighting) | VACE `custom_video_selection` → `"Apply Relighting"` | M |
| 29 | Quay lại cảnh 4D từ góc máy mới | `vista4d` | D |
| 30 | LoRA — phong cách/nhân vật riêng của từng khách | `get_lora_dir(model_type)`, mỗi họ một thư mục | M |
| 31 | Trả tensor thẳng vào RAM, không qua đĩa | `_api={"return_media": True}` → `video_tensor_uint8 [C,F,H,W]` | M |
| 32 | Sinh **ảnh** (không chỉ video) | 6 họ: `flux`, `qwen`, `krea2`, `ideogram4`, `z_image`, `hidream` | M |
| 33 | Sinh **giọng/nhạc** | 10 handler TTS: `ace_step`, `chatterbox`, `omnivoice`, `index_tts2`, `minimax_music3`… | M |

---

## 4. ĐIỂM SỐ

Chấm **độ phủ của ta** so với mục tiêu *"làm được mọi tác vụ Seedance 2.0 làm
được"*, rồi so với *"khai thác WanGP"*.

| Thước đo | Điểm | Cách tính |
|---|---|---|
| **Ngang Seedance 2.0** | **4 / 14** | mục 1,2,12 xanh + 9,10,11 vàng (nửa điểm ×3 ≈ 1,5) ⇒ **≈ 29%** |
| **Khai thác WanGP** | **0 / 19** | không mục nào trong bảng 3 được nối. **0%** |
| **Model type đã nối** | **2 / 46** | trong riêng họ Wan ⇒ **4,3%** |
| **Chất lượng phần ĐÃ làm** | 🟢 | đường job · credit · hoàn tiền · thư viện · huỷ · CSP · cache-bust đều có phép kiểm canh |

⇒ **Tổng: hạ tầng tốt, độ phủ năng lực kém.** Ta xây một cái ống dẫn chắc chắn
rồi chỉ cho hai giọt đi qua.

---

## 5. Vì sao độ phủ kém — và cái sai KHÔNG nằm ở chỗ dễ đoán

Không phải vì WanGP khó. Vì **cách ta mở một model**:

```
hiện tại:  1 model  =  1 hồ sơ JSON rút tay  =  1 lần chạy công cụ  =  1 lần đo pod
           ⇒ chi phí TUYẾN TÍNH theo số model ⇒ 46 model = 46 lần
```

Trong khi WanGP **tự khai năng lực của mình** (`get_model_schema`) và **tự điền
cờ**. Nguyên văn `docs_API.md:330`:

> *"At task normalization, WanGP fills missing media-mode flags when the supplied
> model definition allows them: start images add `S`, end images add `E` without
> removing `S`, source-video continuation adds `V`, reference images use the
> first declared reference mode containing `I`."*

🔴 **Tức là phần lớn việc xử lý cờ chữ cái tôi làm tay là việc WanGP đã làm.**
Tôi dựng một tầng dịch cờ ở phía ta, trong khi engine tự dịch được — và tầng ấy
chính là thứ khiến mỗi model mới tốn một hồ sơ rút tay.

Đường đúng:

```
đúng:  1 lần gọi list_model_defs()  ->  bảng năng lực CỦA CẢ 46 MODEL
       hồ sơ = SINH RA từ bảng ấy, không gõ
       ⇒ chi phí HẰNG SỐ
```

---

## 6. Việc phải làm, xếp theo giá trị trên mỗi đơn vị công

| | Việc | Mở ra | Phụ thuộc |
|---|---|---|---|
| **A** | Gọi `list_model_defs()` + `get_model_schema()` trên pod, **sinh** sổ hồ sơ thay vì gõ | biến 2/46 thành một bảng đầy đủ, một lần | 🔴 pod |
| **B** | Bỏ tầng dịch cờ tay, để WanGP tự điền | xoá nguồn lỗi `E`-bị-gỡ, và xoá chi phí mỗi model | A |
| **C** | Mở `vace_14B` | mục 4,5,6,15,16,17,18,28 — **tám** hạng mục một lần | A |
| **D** | Mở `ltx2_*` | mục 8 (nhạc nền gốc) + 4 (2–5 ảnh ref) | A |
| **E** | Nối `submit_media_postprocessing` | mục 9 (4K), 24 — và **thay** đường nâng nét vòng qua máy A | A |
| **F** | GUI: gallery **kéo-thả có thứ tự** + ô chọn 4 chế độ đúng như WanGP khai | điều kiện cần của C và D | C |
| **G** | Bảng giá theo model | 46 model = 46 giá vốn; `gia.py` hiện chỉ biết 2 | A |

**Chặn duy nhất của A→G là pod.** Stack `py3.11/cu130` chết ở cuBLAS
(bf16/fp16/fp32, **ngoài** WanGP). Dựng lại `cu128/py310` không còn là "một việc
song song" — nó là **điều kiện tiên quyết của toàn bộ bảng này**.

⚠️ Mọi ô `?`/`D` phải đo lại bằng `get_model_schema()` trước khi lên bảng giá
hay lên nhãn giao diện. Một hạng mục đọc từ tài liệu chưa phải một hạng mục
bán được.

---

## 7. Kết luận một câu

**WanGP là tập cha của Seedance 2.0 ở gần như mọi trục** (rộng hơn rõ rệt ở mặt
nạ, điều khiển chuyển động, độ dài, hậu kỳ, âm thanh, LoRA). Khoảng cách giữa ta
và Seedance **không phải khoảng cách năng lực của engine — nó là khoảng cách nối
dây**, và nó rộng đúng bằng 44 model type ta chưa chạm tới.
