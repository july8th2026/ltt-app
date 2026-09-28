# VISION PLAN LOCK — đường ảnh của LTT (28/09/2026)

> **Phạm vi:** chỉ đường ảnh/vision. Không đụng đường chữ, không triển khai, không deploy.
> **Trạng thái:** bản thiết kế chờ chủ dự án khoá. Bốn câu hỏi ở §7.

---

## 0. Kết luận một dòng

> Trần `4 ảnh` **không phải** thứ đang chặn ta, và nâng nó lên `10` sẽ **không** cho khách gửi
> thêm ảnh nào. Thứ đang chặn là **trần thân 4 MiB** — và ba trong bốn con số đang cai quản
> đường ảnh đều **không kết nối với con số duy nhất đúng**: chi phí token thật của một ảnh,
> vốn là **một hàm thuần của (rộng, cao)** tính được **không cần chạm GPU**.

---

## 1. SỰ THẬT ĐANG CHẠY — đo từ mã, không suy

### 1.1 Chuỗi cưỡng chế, xếp theo thứ tự ai chặn trước

| # | Tầng | Trần | Nơi cưỡng chế |
|---|---|---|---|
| 1 | **Máy A — thân request** | **4 MiB toàn bộ thân** | `platform_core/public_api/config.py:134` `DEFAULT_MAX_BODY_BYTES`; chạy ở `server/api/deps.py::enforce_body_limit`, **trước cả xác thực** |
| 2 | Client LTTCODE — mỗi ảnh | ≤ 2048×2048 px **và** ≤ 1 MiB mã hoá | `plugins/llm-ltt/src/adapter.ts:234` `IMAGE_BUDGET` |
| 3 | Client — cả request | ≤ 20 MiB base64 | `adapter.ts:261` `MAX_REQUEST_IMAGE_BYTES` |
| 4 | Harness DSH — nhận ảnh | 20 ảnh/tin, 20 MiB/ảnh, 64 Mpx, cạnh 8192 | `dsh-attachment-local/lib/index.js:997-1009` |
| 5 | **Cổng máy B — số ảnh** | **4** | `llm_gateway/config.py:169` (`LTT_LLM_MAX_IMAGES`) → `ngan_sach.py:234` |
| 6 | Cổng máy B — byte/ảnh | 12 MiB (sau giải base64) | `config.py:170` → `ngan_sach.py:255` |
| 7 | Cổng máy B — SSRF | chỉ `data:…;base64,` | `ngan_sach.py:101,249` (`_DATA_URL`, `url_tu_xa`) |
| 8 | Cổng máy B — KV | `chữ + N × 2048 + ra ≤ cửa sổ` | `ngan_sach.py:204` `token_anh = len(anh) * TOKEN_GIU_MOI_ANH` |
| 9 | Máy A — đặt chỗ | `vào_ước + xin_ra + dem_uoc + N × 2048 ≤ pool` | `platform_core/llm/tham_so_da_luot.py:143` |
| 10 | llama.cpp b10883 | **không có trần số ảnh**; mỗi ảnh kẹp `[8, 4096]` token | `tools/mtmd/clip.cpp:1651-1667` `set_limit_image_tokens(8, 4096)` |

### 1.2 Engine thật sự đang chạy

`llm_gateway/deploy/llama-swap.yaml` — hai hồ sơ, **cả hai đều `in: ["text","image"]`**:

```
qwen38-api  LTT-3.8  RTX 3090      -c 221184 -np 3  KV q4_0  --mmproj mmproj-F16.gguf
qwen35-api  LTT-3.5  RTX 5060 Ti   -c 262144 -np 4  KV q8_0  --mmproj mmproj-9B-F16-unsloth.gguf
chung: --jinja -fa 1 -ngl 999 -kvu --metrics
```

⛔ **KHÔNG hồ sơ nào truyền `--image-min-tokens` / `--image-max-tokens` / `--mtmd-batch-max-tokens`.**
Cả ba cờ **đều có** ở build 10883 (PR #16921 gộp 2025-11-03; #24384 gộp 2026-06-12 — đều là
tổ tiên của `91f6a6cf3`). Ta đang chạy **mặc định**.

Bản ghim: `llm_gateway/deploy/phien_ban_ghim.json` → llama.cpp **b10883 = `91f6a6cf3`**,
ngày commit **2026-09-09**.

### 1.3 Hoá đơn ĐÃ đúng theo độ phân giải — chỉ đặt chỗ là sai

`llm_gateway/so_luot.py:165` và `platform_core/llm/cong_vlm.py:257` đọc **`usage.prompt_tokens`
thật của llama-server**, và `prompt_tokens` **có tính token ảnh**
(`tools/server/server-task.cpp:368` + `server-common.cpp:504-524`, một `LLAMA_TOKEN_NULL`
cho mỗi token ảnh).

⇒ `TOKEN_MOI_ANH = 770` (`apps/ltt_llm/ngan_sach.py:112`) **không** nằm trên đường tính tiền.
`grep` cho thấy nó chỉ được `apps/auto_scan_video` dùng để **ước trước**, cộng tài liệu và test.
Chú thích *"con số này đi thẳng vào hoá đơn"* ở `ngan_sach.py:68` **nói quá** — sửa chú thích,
không sửa mã.

---

## 2. BỐN CON SỐ, KHÔNG CON NÀO BUỘC VÀO CON NÀO

Đây là chẩn đoán chính. Cùng một lớp bệnh đã ghi ở `docs/NHAT_KY.md` 25/09
(*"một giá trị khai ở hai nơi mà không có gì buộc chúng"*), lần này **bốn** nơi:

| Con số | Giá trị | Nó được chọn thế nào | Sự thật |
|---|---|---|---|
| `max_images` | **4** | không có phép đo nào đứng sau; `test_1259` chỉ chứng minh *"A công bố đúng cái B cưỡng chế"*, **không** chứng minh 4 là đúng | llama.cpp **không** có trần số ảnh |
| `max_image_bytes` | **12 MiB** | chép từ env máy B | **KHÔNG BAO GIỜ ĐẠT TỚI** — xem §2.1 |
| `TOKEN_GIU_MOI_ANH` | **2.048** | *"1080p rơi vào khoảng 1.000–1.600, lấy 2.048 cho chắc"* (`llm_gateway/ngan_sach.py:93`) | đúng cho 1080p, **thiếu 2×** ở đỉnh, **thừa 8–130×** ở đáy |
| chi phí thật | `f(w,h)` kẹp `[8, 4096]` | **không ai tính** | con số **duy nhất đúng**, và tính được **miễn phí** |

### 2.1 🔴 `max_image_bytes = 12 MiB` là một lời hứa không thể thực hiện

Ảnh đi trong thân JSON dưới dạng base64 (`plugins/llm-ltt/src/messages.ts:95`), nở **4/3**.

```
trần thân                4 MiB          = 4.194.304 B
1 ảnh 12 MiB  -> base64  16.777.220 B   = 4,0× trần thân
```

⇒ Trần byte **thật** mỗi ảnh là ~2,9 MiB (và đó là khi conversation rỗng). Con số `12 MiB`
ta **đang công bố ra `/api/v1/models`** (`server/api/tools.py:88`) là **sai với thực tế**,
đúng lớp lỗi *"trần đo đại lượng khách không trải nghiệm"*.

### 2.2 🔴 Và 3 ảnh cỡ tối đa của chính client ta **đã** vượt trần thân

```
1 ảnh 1 MiB   -> base64  4*ceil(1048576/3) = 1.398.104 B
3 ảnh                                      = 4.194.312 B
trần thân                                  = 4.194.304 B
                                             ---------- vượt 8 B, chưa có một ký tự hội thoại
```

⇒ **Hôm nay LTTCODE chỉ gửi lọt 2 ảnh cỡ tối đa**, còn lại ~1,33 MiB cho toàn bộ hội thoại.
Trần `4 ảnh` **chưa bao giờ là thứ chặn khách** — nó chỉ là thứ ta đổ lỗi.

Và `MAX_REQUEST_IMAGE_BYTES = 20 MiB` ở client là **mã chết**: nó đứng sau một cửa 4 MiB.

### 2.3 Đặt chỗ phẳng sai **cả hai chiều**

Giả định chi phí (xác minh ở §6, Đ-1): **1 token = 32×32 px**, cộng 2 token dấu vision.
Suy ra từ đúng phép đo ta đã có: `TOKEN_MOI_ANH = 770` đo bằng **hiệu** `n_prompt_tokens`
(17 → 787) cho ảnh **1024×768** — và `1024/32 × 768/32 + 2 = 32×24 + 2 = **770**`, **khớp
tuyệt đối**. (Họ 28 px/token của Qwen2.5-VL sẽ cho 1.001 — loại.)

| Ảnh | Token thật | Đặt chỗ hiện tại | Lệch |
|---|---|---|---|
| 400×300 (biểu tượng, ô cắt nhỏ) | 15 | 2.048 | **thừa 136×** |
| 512×512 | 258 | 2.048 | thừa 7,9× |
| 1024×768 | **770** ✅ đã đo | 2.048 | thừa 2,7× |
| 1920×1080 (ảnh chụp màn hình) | 2.042 | 2.048 | ≈ đúng |
| 2048×2048 (**cỡ tối đa client gửi**) | 4.098 | 2.048 | 🔴 **THIẾU 2,0×** |
| 3840×2160 | kẹp về 4.098 | 2.048 | 🔴 **THIẾU 2,0×** |

⇒ Con số 2.048 được hiệu chuẩn cho **1080p** và chỉ đúng ở 1080p. Ở đỉnh nó **thiếu**,
và thiếu đúng vào chiều nguy hiểm — chiều mà `DatChoVuotPool` sinh ra để chặn, chiều mà
llama.cpp b10689 đã cho thấy **một lần tràn `-kvu` giết MỌI slot**.

**⭐ Đây là lập luận quyết định cho câu hỏi của chủ dự án:** chuyển sang ngân sách
**không phải** là nới lỏng đổi lấy rủi ro. Nó **siết** đúng chỗ đang hở (4.098 > 2.048)
trong khi nhả đúng chỗ đang phí (15 ≪ 2.048). Nó **an toàn hơn** thứ đang chạy.

---

## 3. HAI PHÁT HIỆN NGOÀI ĐỀ BÀI — phải nói ra

### 3.1 🔴 BẢO MẬT: lá chắn SSRF đi mượn **đã mất**, và không ai biết

`tests/test_373_ssrf_anh_tu_xa.py` ghi:

> *"Đo 22/08: `llama-server` hiện **cũng** từ chối URL http. Nhưng đó là một bảo đảm **đi mượn**
> — nó phụ thuộc hành vi của thượng nguồn và có thể đổi ở một bản nâng cấp mà không ai báo."*

**Câu cảnh báo ấy đã thành sự thật.** Ở đúng commit ta đang chạy, `handle_media`
(`tools/server/server-common.cpp:1062-1087`, gọi ở 1223/1238/1252) **TẢI** mọi URL bắt đầu
bằng `http` qua `common_remote_get_content()` — trần 10 MB, hết giờ 10 s, **không cờ, không
danh sách trắng**.

⇒ Kiểm tra `url_tu_xa` ở `llm_gateway/ngan_sach.py:249` **không còn là lớp thứ hai**. Nó là
**lớp duy nhất** đứng giữa khách và `http://127.0.0.1:8188` (ComfyUI, không xác thực).

**Hệ quả cho plan này:** mọi phương án ở §5 **phải giữ nguyên** luật *"chỉ `data:` URL"*.
Và `test_373` phải sửa chú thích — nó đang dạy người đọc sau một điều **đã sai**.

### 3.2 🟠 ĐỊNH DẠNG: client có thể gửi WebP, engine **không** đọc được WebP

* Harness mã hoá ảnh request theo bậc thang: `hasAlpha ? "image/webp" : "image/jpeg"`
  (`dsh-attachment-local/lib/index.js:84`). **Ảnh có kênh alpha ⇒ WebP.**
  Ảnh chụp màn hình từ trình duyệt/Playwright mặc định là **RGBA**.
* `ImageMediaType` của DSH = `png | jpeg | webp | gif`
  (`dsh-attachment/lib/types/types.d.ts:5`).
* llama.cpp b10883 giải mã bằng **stb_image** = `JPEG · PNG · BMP · GIF · TGA · PSD · HDR ·
  PIC · PNM`. **KHÔNG có WebP.** Đường WebP duy nhất là `decode_webp_with_ffmpeg()`, nằm
  **trọn trong `#ifdef MTMD_VIDEO`** và gọi một **`ffmpeg` ngoài `PATH` lúc chạy**
  (`mtmd-helper.cpp:366-368, 409, 419-425`).
* Cổng máy B **không kiểm định dạng**: `_DATA_URL` bắt được `mime` nhưng **không dùng** —
  nó chỉ phân biệt `data:` với URL từ xa.

⇒ Một ảnh PNG có alpha đi qua LTTCODE hôm nay **có thể** biến thành WebP trên dây và chết ở
máy B với một lỗi thượng nguồn không ai dịch. **Chưa đo** (Đ-3 ở §6) — nhưng đây đúng là hình
dạng *"xanh ở mọi phép kiểm, hỏng ở khách"* mà kho này đã gặp nhiều lần.

### 3.3 🟢 Tin tốt: ba nỗi lo lớn nhất **không tồn tại** ở build của ta

| Nỗi lo | Sự thật ở `91f6a6cf3` |
|---|---|
| Nhiều ảnh liền nhau bị gộp âm thầm, ảnh thứ 2 bị mất, `prompt_tokens` không đổi (#27313 / "super-frame" #24303) | **ĐÃ VÁ** — PR #27348 gộp 2026-08-19 (`95c409c1`), là **tổ tiên** của build ta. `mtmd_bitmap_set_mergeable`. |
| mmproj tốn VRAM theo từng slot | **KHÔNG** — một `mtmd_context` **dùng chung** gán cho mọi slot (`server-context.cpp:1173,1308`). Nhiều ảnh ⇒ **0 MiB VRAM thêm**. Giá duy nhất là **KV**. |
| Gửi lại cùng một ảnh phải mã hoá lại | **KHÔNG** — tiền tố KV so khớp bằng **SHA-256 của khối ảnh** (`server-common.cpp:697-735`); ảnh giống hệt ở cùng vị trí tiền tố được **dùng lại**. (⚠️ `--cache-reuse` thì bị **tắt cưỡng bức** khi có multimodal — `server-context.cpp:1190-1192`.) |

⇒ **Rào an toàn mà đề bài lo (VRAM, concurrency) không phải rào thật.** Rào thật chỉ có hai:
**KV** (đã có cơ chế — chỉ cần tính đúng) và **byte thân** (§2.1).

---

## 4. BÀI TOÁN THẬT — phân loại từng trần

| Trần | Của ai | Phán quyết |
|---|---|---|
| 1 ảnh ≤ 4.096 token | **llama.cpp** (`clip.cpp:1660`) | nới được bằng `--image-max-tokens`; trả bằng KV |
| 1 ảnh ≥ 8 token (mặc định) | **llama.cpp** | 🔴 **nên nâng** — xem §5.4 |
| kích thước → token | **model** (32 px/token) | bất biến vật lý, chỉ để **tính**, không để sửa |
| `max_images = 4` | **LTT tự đặt** | **GỠ** — thay bằng ngân sách (+ một trần chống lạm dụng theo **độ trễ**, không theo KV) |
| `max_image_bytes = 12 MiB` | **LTT tự đặt** | **GỠ** — nó là mã chết dưới trần thân |
| `TOKEN_GIU_MOI_ANH = 2048` | **LTT tự đặt** | **GỠ** — thay bằng `f(w,h)` |
| trần thân 4 MiB | **LTT tự đặt** | nới được — nhưng xem §5.3, có đường tốt hơn |
| chỉ `data:` URL | **LTT tự đặt** | 🔴 **GIỮ NGUYÊN** — §3.1, nay là lớp duy nhất |
| trần tải URL xa 10 MB | llama.cpp | không liên quan (ta chặn URL xa) |

---

## 5. KIẾN TRÚC ĐỀ XUẤT

### Nguyên tắc: **một phép tính, hai bản sao, một phép kiểm buộc chúng**

Kho này **đã có** đúng khuôn ấy và nó đã chạy tốt: `platform_core/llm/uoc_token.py` ≡
`llm_gateway/uoc_token.py`, giống nhau **từng byte**, `test_1470` canh. Đường ảnh dùng lại
y hệt khuôn đó — ⛔ không phát minh khuôn mới.

### 5.1 `anh_token.py` — hàm thuần, không I/O, hai bản sao byte-identical

```
kich_thuoc(bytes) -> (rong, cao)      # đọc HEADER PNG/JPEG/WebP/GIF, KHÔNG giải mã ảnh
token_anh(rong, cao, *, toi_thieu, toi_da, px_moi_token) -> int
```

`token_anh` **chép lại đúng** `calc_size_preserved_ratio()` của llama.cpp
(`tools/mtmd/mtmd-image.cpp:122-157`, chính là `smart_resize` của transformers) — không
tự nghĩ công thức.

⭐ Điểm cốt lõi: **phép này không chạm GPU, không đánh thức model, không giải nén ảnh.**
Nó đọc ~32 byte đầu. Tức nó dùng được ở **cả** máy A (trước khi đặt chỗ) **lẫn** máy B
(trước khi chạm GPU) — đúng tính chất mà `llm_gateway/ngan_sach.py` dựng cả tệp để bảo vệ.

### 5.2 Buộc hằng số vào engine, không gõ số lần thứ hai

`toi_thieu` / `toi_da` / `px_moi_token` **không được gõ tay**. Chúng phải:

1. được **khai tường minh** ở `llama-swap.yaml` bằng `--image-min-tokens N --image-max-tokens M`
   (hôm nay đang **ngầm**, và ngầm nghĩa là không ai buộc được gì vào nó);
2. được **đọc ngược** từ yaml ấy trong một phép kiểm — đúng khuôn `HO_SO[m]` đang đọc `-c`/`-np`.

⛔ Không dùng khoá GGUF `clip.vision.image_min_pixels` / `image_max_pixels`: chúng **tồn tại**
(`clip-impl.h:53-54`) nhưng **KHÔNG được đọc cho họ Qwen2VL/25VL/3VL** (`clip.cpp:1416,1651-1667`
— không có `get_u32` nào trong khối ấy). Với họ model của ta, **cờ CLI là cần gạt duy nhất**.

### 5.3 Ngân sách thay cho đếm

**Cổng máy B** (`llm_gateway/ngan_sach.py`):
```
token_anh = Σ token_anh(w_i, h_i)          # thay len(anh) * 2048
gỡ: image_count_exceeded theo max_images
giữ: image_url_not_allowed  (§3.1 — nay là lớp duy nhất)
đổi: image_too_large  ->  nói bằng TOKEN, và nói con số thật
```

**Máy A** (`platform_core/runtime_noi_bo/luong.py`, `platform_core/llm/tham_so_da_luot.py`):
```
dem_anh(than) -> int                       ->  do_anh(than) -> (so_anh, token_anh_tong)
luat_cho(..., so_anh=N)                    ->  luat_cho(..., token_anh=T)
dat = vao_uoc + xin_ra + dem_uoc + N*2048  ->  dat = vao_uoc + xin_ra + dem_uoc + T
```

`DatChoVuotPool` **không đổi** — nó vẫn là thứ ném khi một lượt xin nhiều hơn cả pool, và nay
nó ném **đúng lúc** thay vì muộn 2×.

**Công bố** (`server/api/tools.py::_gioi_han_model`):
```
GỠ   max_images            (số bịa)
GỠ   max_image_bytes       (mã chết dưới trần thân)
THÊM max_image_tokens      = toi_da của engine
THÊM min_image_tokens      = toi_thieu của engine
THÊM image_pixels_per_token
THÊM accepted_image_media_types   (§3.2 — đo rồi mới công bố)
GIỮ  accepted_image_schemes = ["data"]
```

⇒ Client tính được **trước** đúng con số máy chủ sẽ tính. Cùng một bài học với
`X-LTT-Max-Body-Bytes` ngày 25/09: **công bố con số, đừng bắt khách đâm vào tường.**

**Client** (`plugins/llm-ltt/src/adapter.ts`): `requiredImageOffload` chuyển từ nhả ảnh theo
**số lượng** sang nhả theo **ngân sách token** — và nhả **ảnh đắt nhất**, không phải ảnh **cũ nhất**.

### 5.4 Trần đếm mới — dựa trên ĐỘ TRỄ, không dựa trên KV

Gỡ `max_images` không có nghĩa là bỏ mọi trần. Ngân sách KV **không** chặn được
*"200 ảnh 64×64"*: chúng chỉ tốn ~3.000 token KV nhưng là **200 lượt mã hoá mmproj** nối
tiếp trên một slot dùng chung.

⇒ Vẫn cần một trần đếm — nhưng **lý do của nó đổi**, và **con số phải đo**:
`trần = ngân_sách_độ_trễ_prefill / độ_trễ_mã_hoá_một_ảnh`. Hôm nay lý do ấy không được viết
ra ở đâu, nên `4` không thể bảo vệ và cũng không thể phản bác. (Đ-4 ở §6.)

### 5.5 Trần thân — hai đường, đường thứ hai là đường thật

| | Đường A — nâng trần thân | Đường B — **ảnh theo tham chiếu** |
|---|---|---|
| Làm gì | `LTT_PUBLIC_API_MAX_BODY_BYTES` 4 MiB → N MiB | thân mang **id ảnh mờ**; máy A nở thành base64 ngay trước khi chuyển cho B |
| Chi phí | mỗi request nở RAM ở A cho **mọi** khách, kể cả khách chữ | một bước nở ở A |
| Trần cứng | Cloudflare 100 MB | biến mất khỏi thân |
| Thuế base64 1,33× | khách vẫn trả trên đường lên | **biến mất** |
| Gửi lại ảnh cũ mỗi lượt agent | vẫn gửi lại toàn bộ byte | gửi lại **id** |
| Đã có sẵn gì | env + header `X-LTT-Max-Body-Bytes` đã có | `platform_core/public_api/media.py` **đã có** vé tải lên, kiểm magic-byte, hạn ngạch, quét dọn |
| SSRF | không đổi | **không mở** — A lấy từ kho **của A**, không phải URL khách đưa |

⭐ Đường B là câu trả lời thật cho *"tăng số lượng ảnh trong một request"*. Với một phiên agent
gửi lại 6 ảnh chụp màn hình qua 30 lượt, đường A tốn **180 lần** truyền byte; đường B tốn **6**.
Và nó bắt tay đúng với cơ chế tiền tố KV theo SHA-256 mà llama.cpp **đã** có (§3.3).

**Đề xuất:** đường A là **bản vá tức thời** (một env, rủi ro thấp, gỡ ngay mâu thuẫn §2.2);
đường B là **hướng kiến trúc**. Không phải chọn một.

### 5.6 Chất lượng đọc ảnh — cần gạt chưa ai bật

`clip.cpp:1662-1667` ở **đúng build của ta** in cảnh báo rằng Qwen-VL *cần tối thiểu 1.024
token ảnh để hoạt động đúng trên tác vụ định vị* (dẫn issue #16842), và đề nghị
`--image-min-tokens 1024`. Mặc định là **8**.

Ta **chưa bao giờ truyền cờ này**. Nghĩa là mọi ảnh nhỏ — ô cắt giao diện, biểu tượng, đoạn
văn bản crop — đang được đưa vào model ở độ phân giải **model không đọc nổi**, và **không có
lỗi nào phát ra**: nó chỉ trả lời sai.

| Ảnh | Không cờ (nay) | `--image-min-tokens 1024` |
|---|---|---|
| 400×300 | **15 token** | 1.024 token |
| 512×512 | 258 token | 1.024 token |
| 1024×768 | 770 token | 1.024 token |
| 1920×1080 | 2.042 token | 2.042 token (không đổi) |

Đây là **đánh đổi sản phẩm**, không phải quyết định kỹ thuật: độ chính xác đổi lấy KV và credit.
⇒ Câu hỏi 1 ở §7.

---

## 6-BIS. PHA 0 — ĐÃ ĐO XONG 28/09/2026

### 6b.1 Công thức: chốt từ CHÍNH TỆP MODEL, không suy từ một điểm

Đọc siêu dữ liệu GGUF của hai tệp mmproj trên máy B (SSH chỉ đọc, `tools/` script,
không chạy inference, không đánh thức GPU):

```
clip.projector_type              = 'qwen3vl_merger'     ← CẢ HAI tệp
clip.vision.patch_size           = 16
clip.vision.spatial_merge_size   = 2      ⇒ 1 token = (16*2)² = 32×32 điểm ảnh
clip.vision.block_count          = 27
clip.vision.image_size           = 768
clip.vision.image_min_pixels     ← VẮNG MẶT
clip.vision.image_max_pixels     ← VẮNG MẶT     (khớp: họ Qwen không đọc khoá này)
```

⇒ Giả định *"32 px/token"* ở §2.3 **không còn là giả định**. Và nó đúng cho **cả hai model**,
xác nhận câu `ngan_sach.py:111` *"giống nhau ở cả hai model"* — vốn trước nay chưa ai kiểm.

### 6b.2 Đo thật: `tools/do_token_anh.py` — **14/14 ô khớp**

Đo bằng **hiệu** `usage.prompt_tokens` giữa cùng một câu hỏi có ảnh và không ảnh, gọi
**thẳng cổng máy B** (không qua sổ tiền, không qua lớp đặt chỗ của A).

| Ảnh | 3.8 | 3.5 | Dự đoán | Lệch |
|---|---|---|---|---|
| 320×240 | 82 | 82 | 82 | 0 |
| 512×512 | 258 | 258 | 258 | 0 |
| 1024×768 | **770** | **770** | 770 | 0 |
| 1280×720 | 922 | 922 | 922 | 0 |
| 1920×1080 | 2.042 | 2.042 | 2.042 | 0 |
| 2048×2048 | 4.098 | 4.098 | 4.098 | 0 |
| 3840×2160 | **4.082** | **4.082** | 4.082 | 0 |

**Công thức chốt** (`tools/do_token_anh.py::du_doan`, đã đối chiếu 14/14):

```
o = round_nua_len(w/32) * round_nua_len(h/32)
nếu o > 4096:                                   # KHÔNG kẹp — THU NHỎ giữ tỉ lệ
    β = sqrt(w*h / (4096*32*32))
    o = floor(w/β/32) * floor(h/β/32)
token_ảnh = max(8, o)          # sàn 8 của set_limit_image_tokens
token_thấy_trên_hoá_đơn = token_ảnh + 2         # <|vision_start|> + <|vision_end|>
```

### 6b.3 🔴 HAI CON BỌ BẮT ĐƯỢC NGAY TRONG LÚC ĐO — cả hai lệch về chiều NGUY HIỂM

**Bọ 1 — `round()` của Python làm tròn VỀ SỐ CHẴN.** Bản chuyển ngữ đầu của tôi cho
1280×720 ra 882; máy trả 922. `720/32 = 22,5`; `std::round` của C++ cho **23**, `round()`
của Python cho **22**. Lệch **40 token**.
⚠️ Và 1280×720 là một trong những cỡ ảnh chụp màn hình phổ biến nhất — con bọ này nằm
**đúng trên đường đi nhiều nhất**, và lệch về phía **đặt chỗ ÍT hơn thực**.
⇒ `anh_token.py` **phải** dùng `floor(x + 0,5)`. Phép kiểm phải có ô `1280×720`.

**Bọ 2 — nhánh vượt trần KHÔNG phải phép kẹp.** Dự đoán đầu kẹp về 4.096; máy trả 4.080.
Vượt trần thì `smart_resize` **thu nhỏ giữ tỉ lệ rồi `floor`**. Kẹp thẳng sẽ ước **cao hơn**
thực 16 token mỗi ảnh 4K — sai hướng an toàn, nhưng nó **che mất việc ảnh ĐÃ bị thu nhỏ**,
và đó chính là điều §7.1 phải công bố.

> ⭐ Cả hai bọ đều **không thể** bắt được bằng đọc mã. Chúng chỉ lộ ra vì bảng đo có ô ở
> **cạnh nửa** và ô ở **trên trần**. Một bảng dừng lại ở 1080p sẽ xanh và sai.

### 6b.4 🔴 Đ-3 + Đ-6 — WebP CHẾT trên production, và đường sửa là một cờ

| Sự thật | Bằng chứng |
|---|---|
| Client LTTCODE mã hoá `hasAlpha ? webp : jpeg` | `dsh-attachment-local/lib/index.js:84` |
| Ảnh chụp màn hình trình duyệt/Playwright mặc định **RGBA** | — |
| Gửi WebP tới máy B ⇒ **400**, `upstream_status: 400`, `provider_type: invalid_request_error` | đo 28/09 `do_token_anh.py --webp`; lỗi đến từ **llama-server**, không phải cổng |
| `llama-server.exe` b10883 **CÓ** `--video-ffmpeg-dir` ⇒ build **có** `MTMD_VIDEO` | `--help` trên máy B |
| `ffmpeg` có ở `C:\Users\lengo\…\WinGet\Links` — **PATH của người dùng** | `Get-Command ffmpeg` |
| PATH **máy** không có ffmpeg | `[Environment]::GetEnvironmentVariable('Path','Machine')` |
| Dịch vụ chạy **`SERVICE_START_NAME : LocalSystem`** | `sc qc LTTLlamaSwap` |

⇒ llama-server chỉ thấy PATH máy ⇒ **không thấy ffmpeg** ⇒ WebP chết.
⚠️ Và `nssm` **nướng ENV lúc cài** (bộ nhớ, `nssm-nuong-env-luc-cai`), nên sửa PATH máy
**cũng không** ăn nếu không cài lại dịch vụ.
⭐ Đường sạch là **`--video-ffmpeg-dir <thư mục máy đọc được>`** trong `llama-swap.yaml` —
một cờ, đi đúng đường `git` của cấu hình, không đụng PATH, không cài lại dịch vụ.

> 🔴 Đây đúng là bẫy bộ nhớ đã ghi 23/09 (`worker-chay-localsystem-khac-moi-truong`):
> *"PATH khác phiên người dùng (thiếu ffmpeg)"*. Lần đầu tôi hỏi `where ffmpeg` qua SSH và
> nhận được **câu trả lời cho một câu hỏi khác** — PATH của `lengo`, không phải của dịch vụ.

### 6b.5 Còn lại

| # | Trạng thái |
|---|---|
| Đ-1 công thức | ✅ **XONG** — GGUF + 14/14 ô |
| Đ-2 hai model | ✅ **XONG** — giống hệt nhau |
| Đ-3 WebP đầu client | 🟡 mã nói `hasAlpha ⇒ webp`; **nửa máy chủ đã xác nhận chết**. Còn thiếu: một ảnh RGBA thật đi hết đường LTTCODE |
| Đ-4 độ trễ mã hoá/ảnh | ⬜ chưa — là mẫu số của §7.2, không chặn Pha 1-5 |
| Đ-5 `--image-min-tokens` | ⬜ chưa — C1 đã khoá là **hoãn** |
| Đ-6 ffmpeg | ✅ **XONG** — không có, và có đường sửa |

---

## 6. PHÉP ĐO (bản gốc — giữ để đối chiếu)

⛔ Không mục nào dưới đây được thay bằng suy luận. Mỗi mục ghi **cách phân biệt đúng/sai**.

| # | Câu hỏi | Cách đo | Nếu sai thì sao |
|---|---|---|---|
| **Đ-1** | 1 token = 32×32 px, có đúng không? | Gửi **ba** ảnh đặc — 512×512, 1024×768, 1920×1080 — đo **hiệu** `usage.prompt_tokens` với cùng câu hỏi không ảnh. Dự đoán **258 / 770 / 2042**. | 770 hiện tại là **một điểm**; một điểm khớp cả công thức đúng lẫn công thức trùng hợp. Sai ⇒ toàn bộ §2.3 và §5.1 phải tính lại. |
| **Đ-2** | Đo lại **trên cả hai model** (3.8 và 3.5) | như trên, hai alias | `ngan_sach.py:111` khẳng định *"giống nhau ở cả hai model"* — nhưng hai tệp mmproj **khác nhau** (`mmproj-F16` vs `mmproj-9B-F16-unsloth`) |
| **Đ-3** | Ảnh PNG **có alpha** đi qua LTTCODE hôm nay có sống không? | chụp một PNG RGBA thật, gửi qua LTTCODE, xem mediaType trên dây + phản hồi B | Nếu chết ⇒ §3.2 là **lỗi đang chạy**, không phải rủi ro |
| **Đ-4** | Độ trễ mã hoá **một** ảnh trên GPU | `-np 1`, 1/2/4/8 ảnh nhỏ, đo prefill | đây là **mẫu số** của trần đếm mới (§5.4). Chưa có nó thì con số mới cũng chỉ là `4` đổi tên |
| **Đ-5** | `--image-min-tokens 1024` có thực sự nâng chất lượng đọc không? | một bộ ảnh OCR/giao diện nhỏ, chấm **trước/sau**, **cùng ảnh, cùng câu hỏi** | ⛔ Không được suy từ cảnh báo của upstream. Cảnh báo cho biết *có cần gạt*, không cho biết *nó đáng giá bao nhiêu ở ta* |
| **Đ-6** | mmproj có đọc được WebP không (ffmpeg có trên PATH máy B không)? | `ffmpeg -version` trên máy B; gửi 1 ảnh WebP | quyết định giữa "bật WebP" và "cấm WebP ở client" |

⭐ **Đ-1 và Đ-5 phải có nền đo trên cấu hình CŨ.** Bài học 25/09 vừa rồi:
*"phép kiểm viết theo niềm tin về mã sẽ xác nhận niềm tin đó, không xác nhận mã"* — nền
so sánh đo trên bản cũ là thứ duy nhất tách được hai điều ấy.

---

## 7. BỐN QUYẾT ĐỊNH — ĐÃ KHOÁ 28/09/2026 (chủ dự án)

| | Quyết định | Hệ quả cho plan |
|---|---|---|
| **C1** | **Giữ mặc định 8**; đo **Đ-5** trước rồi mới quyết sàn chi tiết | ⛔ Pha 1 khai `--image-min-tokens 8` **tường minh** (khai đúng thứ đang chạy, không đổi hành vi) — mục đích là để có chỗ **buộc** hằng số vào, không phải để đổi số. Sàn thật thành một plan riêng sau Đ-5. |
| **C2** | **Cả hai theo pha**: nâng env ngay, ảnh-theo-tham-chiếu sau | Pha 4a = một env + phép kiểm. Pha 4b = plan riêng dựng trên `media.py`. |
| **C3** | **Máy chủ tự hạ độ phân giải cho vừa** | §7.1 — có một mâu thuẫn với bất biến đã ghi, phải xử đúng cách. |
| **C4** | **Gỡ hẳn trần đếm**, chỉ còn ngân sách KV | §7.2 — còn một rủi ro tồn dư, ghi ra để không ai tưởng đã kín. |

### 7.1-BIS ⭐ PHÁN QUYẾT C3 (tôi tự duyệt, 28/09) — **GIỮ**, bằng HEADER, và quyết định **chuyển về máy A**

Chủ dự án cấp quyền tự duyệt. Tôi tra tài liệu vận hành, sổ quyết định, giao thức và mã client.
Kết quả **lật ngược hai mảnh** trong thiết kế tôi vừa đề xuất ở §7.1 bên dưới — giữ nguyên bản cũ
để thấy chỗ sai.

#### Phán quyết

> **GIỮ công bố. Hình thức: một header `X-LTT-Anh-Thu-Nho` trên CẢ BA CỬA. Và vì thế,
> phép hạ ảnh phải quyết ở `tien_kiem` của MÁY A — không phải ở cổng máy B.**

#### Bốn bằng chứng, xếp theo sức nặng

**1. Kho đã xử ĐÚNG ca này một lần rồi — L-26.**
`docs/ltt_llm_dual/DECISION_LOG.md:837-859`: `reasoning_effort` được *"nhận, gỡ trước máy B,
cửa trả `X-LTT-Effort-Bo-Qua: 1`"*, và `:858` ghi *"Header … có ở **cả ba cửa**"*. Dòng `:859`
liệt kê việc một tham số *"trước bị rơi im lặng"* là một **khuyết tật ĐÃ SỬA**.
⇒ *"nhận, sửa, và nói ra bằng header ở cả ba cửa"* là **hình dạng đã có**. Dùng lại nó tốn
một hằng số và một cờ, và làm hai cơ chế đọc lên như **một luật**.

**2. L-2 cấm âm thầm đổi.** `DECISION_LOG.md:35` — *"không âm thầm đổi 3.8 → 3.5"*.
Hạ ảnh không báo là cùng một hình dạng, đổi đơn vị.

**3. 🔴 Ý "thêm trường vào `usage`" của tôi ĐÃ BỊ CẤM TỪ TRƯỚC.**
`server/api/chat.py:764-766`: *"TIỀN NẰM TRONG `x_ltt`, KHÔNG NHÉT VÀO `usage`. `usage` là
hình dạng khách đã có mã đọc sẵn; thêm khoá lạ vào đó là mời client nghiêm ngặt vỡ."*
⇒ Bỏ hẳn ý đó. Tôi đề xuất một thứ luật nhà đã cấm.

**4. 🔴 VÀ ĐÂY LÀ MẢNH LẬT NGƯỢC THIẾT KẾ: trên đường STREAM, header KHÔNG THỂ mang phán
quyết của B.**
`platform_core/runtime_noi_bo/luong.py:1291-1293`: *"Bên gọi dựng `StreamingResponse` **trước**
khi generator này chạy dòng đầu."* Header cố định ở `server/api/streaming.py:1088-1091`, còn B
chỉ được gọi **bên trong** generator (`luong.py:1796`).
`X-LTT-Effort-Bo-Qua` làm được **chỉ vì** nó quyết ở A, trong `tien_kiem` (`luong.py:775`).
⇒ Muốn công bố bằng header thì **quyết định phải ở A**. Không có đường vòng.

#### Vì sao đặt ở A KHÔNG phá luật "một người cưỡng chế"

Tôi đã lập luận ngược lại ở §7.1 — và lập luận ấy **gộp hai việc khác loại**:

| | Ai làm | Đổi không? |
|---|---|---|
| **Chuẩn hoá đầu vào** (hạ ảnh) | **máy A**, trong `tien_kiem` — đúng chỗ đã có `chuan_hoa_suy_nghi` và phép gỡ `TRUONG_DINH_DANH_KHACH` | **CHUYỂN VỀ A** |
| **Cưỡng chế / từ chối** | **cổng máy B**, `kiem_tra` | **KHÔNG ĐỔI** |

A **đã và đang** viết lại thân request trước khi chuyển tiếp. Hạ ảnh là **cùng một lớp việc,
cùng một chỗ**. B vẫn là người từ chối duy nhất; hạ chưa đủ thì B vẫn chặn.

⭐ Và đặt ở A **sửa luôn một lỗi mà phương án "B hạ" sẽ tạo ra**: `luat_cho` đặt chỗ KV ngay
trong `tien_kiem`. Nếu B hạ, A sẽ giữ chỗ theo ảnh **gốc** rồi B đổi ảnh **dưới chân** — hai
sổ lệch nhau, đúng lớp bệnh này đang dẹp. A hạ ⇒ A đặt chỗ đúng thứ A gửi đi.

#### Giá phải trả, nói thẳng

Máy A phải giải nén + thu nhỏ + mã hoá lại ảnh trên tiến trình web production (~50–150 ms cho
một ảnh 4 Mpx). Tôi **đã từng lấy chính điều này làm lý do gạt A** — và tôi đổi ý vì:
* nó chỉ chạy khi request **không vừa**, mà sau Pha 3 + Pha 5 thì rất hiếm;
* A **đã** phân tích cả thân JSON nhiều MB mỗi request;
* đổi lại là **mất hẳn khả năng công bố trên đường stream** — đường chính của Claude Code,
  Codex và LTTCODE.

**Nếu sai thì sao:** nếu ~150 ms ấy hoá ra đắt trên production, đường lui là để B quyết và
công bố bằng `x_ltt` trên đường **đồng bộ** (headers của B có trong tầm ở `cong_vlm.py:351`),
chấp nhận rằng đường stream **không** công bố được. Đó là công bố yếu hơn L-26 đã đạt — nên
chỉ lùi khi có **số đo**, không lùi vì e ngại.

#### Làm gì, cụ thể

- [ ] `HEADER_ANH_THU_NHO` vào `platform_core/public_api/protocol.py`, **cạnh** các `HEADER_*`
      hiện có. ⛔ Không gõ chuỗi thẳng.
- [ ] Đóng dấu ở **đúng ba chỗ** `X-LTT-Effort-Bo-Qua` đang đóng: `server/api/chat.py:338`,
      `server/api/streaming.py:936`, `server/api/streaming.py:1091`.
- [ ] Cờ quyết ở `tien_kiem` (`luong.py`), cạnh `effort_bo_qua`.
- [ ] Tài liệu ở cả ba nơi L-26 đã ghi: `apps/ltt_llm/manifest.py`,
      `docs/PUBLIC_API/DEVELOPER_GUIDE.md`, `docs/PUBLIC_API/CHANGELOG.md`.
- [ ] ⭐ Thêm **cả hai** header vào `expose_headers` (`server/api/__init__.py:87-89`) —
      `X-LTT-Effort-Bo-Qua` hiện **KHÔNG** có trong đó, tức khuyết tật của L-26 vẫn hở.
      ⚠️ Nói thật: `cors_origins` rỗng ở production nên CORSMiddleware **không được cài**,
      ⇒ sửa này **đúng nhưng hiện chưa ăn**. Không được báo cáo nó như một bản vá cho trình duyệt.

---

### 7.1 C3 — bản đề xuất ĐẦU (giữ để đối chiếu; §7.1-BIS thay thế phần "ở đâu")

🔴 **Quyết định này đụng một bất biến đã ghi.** `DatChoVuotPool`
(`platform_core/llm/tham_so_da_luot.py:95-106`) tồn tại **chính là để THAY phép kẹp im lặng**
`min(pool, dat)` — phương án C bất biến 1. Docstring của nó viết: *"Kẹp che lỗi… và nó che
luôn chính lỗi cấu hình gây ra nó."*

⇒ Tôi **làm theo quyết định**, nhưng **không** làm nó im lặng. Hai điều đó không xung đột:
điều bị bỏ năm xưa là **kẹp âm thầm**, không phải **kẹp**. Thiết kế:

1. **Hạ ở cổng máy B**, không ở máy A. Lý do: B là **người cưỡng chế duy nhất** (`kiem_tra`),
   và giữ đúng luật ấy là có chủ ý. Hạ ở A nghĩa là hai nơi cùng quyết — đúng cái bệnh này
   đang dẹp. Thêm nữa, A là tiến trình web production; giải nén + resize + mã hoá lại một ảnh
   4 Mpx ở đó là đặt ~100 ms CPU vào đường của **mọi** khách.
2. **Bất biến `A ⊆ B` không đổi, thậm chí được củng cố.** Máy A đặt chỗ theo kích thước
   **gốc** (cận trên); B hạ xuống nếu cần ⇒ `usage` thật **luôn ≤** chỗ A đã giữ. Đúng hướng
   an toàn, đúng khuôn `uoc_token.py` hiện có.
3. **Nói ra.** Phản hồi mang một trường ghi: ảnh nào bị hạ, từ bao nhiêu token xuống bao nhiêu.
   ⭐ Đây là phần tôi **thêm** so với chữ của quyết định, và nêu rõ để chủ dự án bác được:
   không có nó, khách nhận câu trả lời dựa trên **ảnh mờ hơn thứ họ gửi mà không biết** —
   và đó là lớp lỗi kho này đã ghi nhiều lần (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`).
   Nếu chủ dự án muốn im lặng hoàn toàn, nói một câu là tôi gỡ trường ấy.
4. **Hạ là "cố hết sức, rồi vẫn từ chối".** Có hai ca *"không vừa"* khác loại:
   * **ảnh** làm vượt ⇒ hạ được, và hạ tới sàn `--image-min-tokens` là hết đường;
   * **chữ** làm vượt ⇒ hạ ảnh **không cứu được** ⇒ vẫn `context_window_exceeded`.
   ⛔ Gộp hai ca này thành một nhánh là lớp lỗi *"một nhánh gánh hai tình huống khác loại"*.

### 7.2 C4 — gỡ trần đếm: rủi ro tồn dư, ghi ra

Ngân sách KV **không** chặn *"200 ảnh 64×64"*: ~3.000 token KV nhưng **200 lượt mã hoá mmproj
nối tiếp** trên `mtmd_context` dùng chung.

Và **cơ chế whale không đỡ hộ**: cờ whale bật theo `token_prefill_moi ≥ nguong_whale`
(`tham_so_da_luot.py:148`). Với ngân sách đúng, 200 ảnh nhỏ = ~3.000 token ⇒ **không phải
whale** ⇒ không bị hãm. Rủi ro này **mở và chưa được đỡ**.

⇒ Ghi vào sổ như một **rủi ro đã nhận**, kèm thuốc rẻ nhất nếu nó xảy ra thật: **Đ-4** cho
mẫu số, rồi dựng trần theo **độ trễ** (§5.4) — không phải dựng lại `max_images = 4`.
⚠️ Điều kiện phát hiện phải viết ra chứ không chờ khách phàn nàn: quan trắc **độ trễ prefill
theo SỐ ẢNH** ở `--metrics`, không chỉ theo số token.

---

## 7-TER. TIẾN ĐỘ THẬT (cập nhật 28/09/2026, nhánh `phien/vision-plan-lock`)

| Pha | Trạng thái | Commit |
|---|---|---|
| **0 — ĐO** | ✅ xong (§6-BIS) | `a79da8f0` |
| **1 — SỰ THẬT** (cờ engine tường minh, sửa 2 chú thích sai) | ✅ xong | `a79da8f0` |
| **2 — TÍNH** (`anh_token.py` ×2 byte-identical) | ✅ xong | `a6dd4be3` |
| **3(B) — cổng máy B tính ngân sách, gỡ `max_images`** | ✅ xong | `a6dd4be3` |
| **4a — trần thân 4 → 32 MiB** | ✅ xong | `a6dd4be3` |
| **3(A) — máy A ĐO ảnh, công bố ra catalog** | ✅ xong | `546ab376` |
| **5 — client nhả theo ngân sách** | 🔨 đang làm (kho `LTTCODEAPP`) | — |
| **6 — tự hạ + header `X-LTT-Anh-Thu-Nho`** | ⬜ chưa | — |
| **DEPLOY** | 🔴 **CHẶN — cần chủ dự án** | §7-TER.3 |

### 7-TER.1 Ba lỗ hổng THẬT tìm thấy trong lúc làm (không có trong plan gốc)

**(a) 🔴 `server/api/chat.py` — cửa sync CHƯA TỪNG đặt chỗ cho ảnh.**
`so_anh` không bao giờ được truyền vào `cho_suat_dong_bo`, nên một lượt sync mang
ảnh giữ thiếu **đúng toàn bộ phần ảnh**. Không phải hồi quy của plan này — nó có
sẵn. Sửa cùng lúc, vì sửa một cửa mà bỏ cửa kia là dựng lại đúng lỗi "hai chỗ
khai một điều".

**(b) 🔴 Thứ tự kiểm tra của tôi che phép chặn SSRF.** Bản đầu đặt phép kiểm cấu
hình engine **trước** `image_url_not_allowed`, nên một `image_url` trỏ vào
`127.0.0.1:8188` trả về *"thiếu cờ engine"*. `test_1701` bắt ngay. Luật đã ghi vào
mã: **khách nghe lỗi CỦA KHÁCH trước; lỗi CỦA TA chỉ nói khi yêu cầu đã hợp lệ
mọi mặt khách kiểm soát được.**

**(c) 🔴 `test_1223` bắt được A ⊆ B gãy — và nó gãy vì một BẢN GIẢ THIẾU THAM SỐ.**
`_b_giu` gọi `do_yeu_cau` **không truyền** hai trần token ảnh, nên bản giả rơi về
hằng phẳng: *"B giữ 39.209, A giữ 43.309"* — B đặt chỗ **ít hơn** A đúng một ảnh
(4.098 thật vs 2.048 phẳng). Bài học: **một bản giả của đường chạy mà thiếu một
tham số sẽ đo ra một con số KHÁC**, và không phép kiểm nào thấy nếu nó không đối
chiếu hai bên.

### 7-TER.2 Hai phép tiêm nghịch của TÔI từng RỖNG, và cách phát hiện

* **`test_4200`**: dùng `cửa sổ rộng nhất × 2` — một hệ số gõ tay. Trần lên 32 MiB
  thì model "gấp đôi" **vừa**, phép thử rỗng. Nay hệ số **suy từ chính trần**.
* **`test_250`**: 3 ảnh 1080p = 6.126 đo thật, mà hằng phẳng cho 6.144 — **cả hai
  đều vượt 5.000**, nên vế ấy xanh trên cả mã đúng lẫn mã sai. Thêm vế **30 ảnh
  320×240** (2.460 đo thật vs 61.440 phẳng) mới có sức phân biệt. Đã chứng minh
  bằng **đột biến**: thay `f(w,h)` bằng hằng ⇒ 2 phép đỏ.
* **`test_4203`** (làn agent): ô `1440×240` không phân biệt được gì vì
  `round(7.5) == 8` trùng `floor(7.5+0.5)`. Chỉ ô có **phần nguyên CHẴN** mới bắt
  được (`round(22.5) == 22`). Đã đổi sang `1440×208`.

> ⭐ Ba ca, một hình dạng: **một phép tiêm nghịch chỉ đo được khi hai nhánh cho
> hai KẾT QUẢ KHÁC NHAU ở đúng ô đang dùng.** Viết xong phải chạy đột biến.

### 7-TER.3 🔴 DEPLOY — ba việc chỉ chủ dự án quyết được

`test_1259::test_BAN_SAO_khop_may_B` **ĐỎ có chủ ý**: máy B đang chạy vẫn cưỡng
chế trần đếm 4 ảnh trong khi máy A đã gỡ. Đó là **sự thật**, không phải phép kiểm
hỏng — và nó là **cửa deploy**. Hai máy phải deploy **cùng nhau**: nếu A lên trước,
khách đọc catalog (không còn trần đếm), gửi 10 ảnh, và ăn 400 mà không chỗ nào báo.

| # | Việc | Vì sao cần chủ dự án |
|---|---|---|
| **D1** | Deploy cổng LLM **máy B** (`llm_gateway/deploy/deploy.ps1`) + nạp lại `llama-swap.yaml` | **khởi động lại engine trên GPU production** ⇒ cắt mọi lượt đang chạy của khách |
| **D2** | Deploy **máy A** để trần thân 32 MiB có hiệu lực | deploy giữa plan (hợp đồng §5) |
| **D3** | Bật WebP: chép `ffmpeg`+`ffprobe` sang một thư mục **máy đọc được** trên máy B rồi thêm `--video-ffmpeg-dir` | ghi tệp lên máy B + khởi động lại engine |

⚠️ **D1 và D2 phải cùng lúc.** D3 độc lập, làm sau được.
⛔ Và `check_mypy` báo `assignment 56 → 57` — đo lại trên **`main`** thấy `main`
   **tự nó** đã vỡ bánh cóc ấy. Không phải của plan này, và ⛔ không `--accept`
   (làm thế là che hồi quy của phiên khác).

---

## 8. THỨ TỰ TRIỂN KHAI (sau khi khoá)

```
Pha 0  ĐO        Đ-1 … Đ-6. Không viết mã. ⛔ Không con số nào vào mã trước Pha 0.
Pha 1  SỰ THẬT   Khai tường minh `--image-min-tokens 8 --image-max-tokens 4096` ở
                 llama-swap.yaml — ĐÚNG giá trị đang chạy, 0 thay đổi hành vi — cộng phép
                 kiểm đọc ngược yaml. Đây là bước tạo CHỖ BUỘC, không phải bước đổi số (C1).
                 Sửa hai chú thích đang dạy sai: test_373 (§3.1) và ngan_sach.py:68 (§1.3).
Pha 2  TÍNH      anh_token.py hai bản byte-identical + phép kiểm buộc chúng (khuôn test_1470).
                 ⛔ Chưa cưỡng chế gì — chỉ TÍNH và GHI, đối chiếu với usage.prompt_tokens
                 thật trên lưu lượng thật cho tới khi khớp.
Pha 3  NGÂN SÁCH Thay 2048 phẳng bằng Σf(w,h) ở B rồi ở A. Gỡ max_images (C4) và
                 max_image_bytes. Công bố trường mới ra /api/v1/models.
Pha 4a THÂN      Nâng LTT_PUBLIC_API_MAX_BODY_BYTES (C2) + phép kiểm buộc nó ≥ ngân sách
                 ảnh công bố, cùng khuôn BODY_BYTES_TOI_THIEU đã có.
Pha 5  CLIENT    adapter.ts nhả ảnh theo ngân sách (nhả ảnh ĐẮT nhất, không phải CŨ nhất);
                 gỡ MAX_REQUEST_IMAGE_BYTES đã chết.
Pha 6  HẠ        Tự hạ độ phân giải ở cổng B (C3, §7.1) + trường báo cáo.
                 ⭐ SAU Pha 3 và Pha 5 là có chủ ý: khi ngân sách đã đúng và client đã tự
                    nhả theo ngân sách, số ca phải hạ còn rất ít. Làm trước thì ta đang
                    dựng một cái kẹp để che một phép tính sai.
sau đó           Ảnh-theo-tham-chiếu (C2 vế 2) và sàn chi tiết ảnh (C1 sau Đ-5) —
                 HAI plan riêng, không nhét vào plan này.
```

⛔ Pha 3 **không** được đi trước Pha 2: cưỡng chế bằng một công thức chưa đối chiếu với
`usage.prompt_tokens` thật chính là lớp lỗi *"xanh trên một thứ đã hỏng"*.

---

## 9. NHỮNG GÌ KHÔNG LÀM

- ⛔ **Không** nới luật *"chỉ `data:` URL"*. §3.1 — lá chắn đi mượn đã mất, đây là lớp duy nhất.
- ⛔ **Không** nâng `max_images` từ 4 lên một số khác mà giữ nguyên `TOKEN_GIU_MOI_ANH = 2048`.
  Đó là nhân đôi đúng cái lỗ ở §2.3 lên N lần.
- ⛔ **Không** đọc khoá GGUF `image_min/max_pixels` — họ Qwen không đọc chúng (§5.2).
- ⛔ **Không** nâng llama.cpp để lấy bản vá multi-image: **đã có** trong b10883 (§3.3).
  Các bản vá sau `91f6a6cf3` chỉ chạm đường **speculative + mmproj** (#28587, #28715) —
  đáng xem riêng vì ta **có** chạy `--spec-type draft-mtp`, nhưng không thuộc plan này.
- ⛔ **Không** tin `TOKEN_MOI_ANH = 770` là con số hoá đơn. Hoá đơn đọc `usage` thật (§1.3).
