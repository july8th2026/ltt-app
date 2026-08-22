# workflows/ — template ComfyUI của cổng render

Mỗi file `.json` là một workflow **định dạng API** của ComfyUI. `catalog.json` khai
model nào dùng template nào cho chế độ nào.

**Thêm model mới = thêm một file JSON + một mục trong `catalog.json`. Không sửa mã.**

## Thẻ thay giá trị

Chỗ cần thay thì viết chuỗi `"@ten"`. `workflows.thay()` duyệt cây JSON và chỉ thay
đúng những chuỗi **bằng** thẻ — không thay-chuỗi trên văn bản, nên một prompt của
khách có chứa `@` cũng không làm hỏng gì. Muốn viết một chuỗi bắt đầu bằng `@` thật
thì gõ `"@@..."`.

Thiếu giá trị cho một thẻ là **lỗi chặn**, không phải cảnh báo: một workflow còn
nguyên `"@seed"` sẽ được ComfyUI nhận rồi hỏng ở giữa, sau khi đã tiêu trọn thời
gian nạp model.

## ✅ `hidream_o1_t2i.json` — ĐÃ XÁC MINH BẰNG ẢNH THẬT (2026-08-21)

Template này được dựng từ **đọc mã nguồn ComfyUI 0.30.0** trên máy B
(`comfy/supported_models.py:1638`, `comfy_extras/nodes_hidream_o1.py`), chứ **không**
từ một bản mẫu chính thức — gói `comfyui_workflow_templates` đã cài chứa **0 file
JSON** (đã kiểm). Nên nó từng mang nhãn DRAFT với bốn chỗ nghi ngờ.

**Chạy thật trên máy B đã gỡ nhãn đó. Cả bốn chỗ nghi ngờ đều đúng, không sửa một
khoá nào:**

| Nghi ngờ | Kết quả |
|---|---|
| `CheckpointLoaderSimple` trả `[0]=MODEL`, `[1]=CLIP`, `[2]=VAE`? | ✅ đúng, kể cả với model pixel-space (ComfyUI chèn `PixelspaceConversionVAE`) |
| `CLIPTextEncode` có phải node mã hoá văn bản đúng? | ✅ đúng |
| `sampling_settings` (`shift 3.0`, `noise_scale 8.0`) có cần node trung gian? | ✅ không — ComfyUI áp tự động |
| Có cần text encoder rời `gemma4_*` 9 GB như tài liệu ComfyUI ghi? | ✅ **KHÔNG** — tài liệu đó sai với model này, mã đúng (D-009) |

Số đo lượt đầu (fp8, 2560×1440, 20 bước, CFG 5,0): **48,4 giây** · VRAM đỉnh
**11.742 MB** · nhiệt đỉnh **77 °C** · công suất đỉnh **368,93 W / trần 370 W** ·
throttle **SW Power Cap**. Chi tiết: `bench/G3_smoke.json`, quyết định **D-016**.

## `hidream_o1_edit.json` và `hidream_o1_subject.json` — đã viết, CHƯA chạy thật

Dựng từ schema đọc trong `comfy_extras/nodes_hidream_o1.py`. **G5 phải xác minh
bằng chạy thật** y như đã làm với `t2i`.

Bốn chi tiết lấy từ mã, mỗi cái đều đủ sức làm workflow bị từ chối nếu đoán sai:

| Chi tiết | Sự thật trong mã |
|---|---|
| `HiDreamO1ReferenceImages` nhận gì | **IMAGE trực tiếp**, không phải latent đã mã hoá |
| Tên input | input tự nở: `image_1` … `image_10` (`io.Autogrow`) |
| Trả về gì | **hai** conditioning: `[0]=positive`, `[1]=negative` — phải nối **cả hai** vào KSampler |
| `upscale_method` hợp lệ | `nearest-exact · bilinear · area · bicubic · bislerp` — **không có `lanczos`** |

Dùng `area` (đúng cho việc **thu nhỏ**, mà ảnh tham chiếu thường lớn hơn 4 MP) và
`resolution_steps: 32` để khớp `PATCH_SIZE = 32` của model.

## ⛔ Không có template `structure` — và đó là một phát hiện, không phải thiếu sót

`grep controlnet comfy/ldm/hidream_o1/*.py` → **không dòng nào**. HiDream-O1 là DiT
pixel-space hợp nhất, **không có đường nhận điều kiện không gian kiểu ControlNet**.

Đây là chỗ nó thua phương án Qwen đã bị loại ở D-009: `Qwen-Image-Edit-2509` **có**
ControlNet gốc (depth, edge, keypoint). Khi chọn D-009 tôi dựa vào mô tả *"unified:
t2i + editing + subject-driven personalization"* — mô tả đó **không nhắc ControlNet**,
và tôi đã suy rộng ra chế độ `structure` mà không kiểm.

G5 sẽ thử đạt `structure` bằng `edit` + lời nhắc giữ bố cục. Không đạt thì **ghi rõ
là không bán được**, hoặc thêm Qwen-Image-Edit-2511 riêng cho chế độ đó. Chi tiết:
**D-017**.

Cách sửa đúng quy trình nếu một template sai: mở ComfyUI trên máy B, dựng workflow
bằng giao diện, xuất ra **API format**, rồi thay các giá trị thành thẻ `@ten`.
Đừng sửa mò từng khoá.

## Vì sao độ phân giải mặc định là 2560×1440 chứ không phải 1920×1080

Mô tả node `EmptyHiDreamO1LatentImage` viết thẳng: model huấn luyện ở **~4 MP**, và
*"lower resolutions go off-distribution and quality regresses noticeably"*.
1920×1080 chỉ 2,07 MP và không nằm trong danh sách bucket đã huấn luyện.

**Công thức giao hàng: sinh ở bucket ~4 MP rồi thu nhỏ về kích thước cần.**
Danh sách bucket nằm trong `catalog.json`, chép từ chính mô tả node đó.

G3 có một thí nghiệm riêng để **chứng minh bằng số** điều này, thay vì tin lời
khuyên — xem `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` §4.

## ⛔ Node tham chiếu dùng khuôn CÓ DẤU CHẤM

`HiDreamO1ReferenceImages` nhận input tên **`images.image_1`**, `images.image_2` —
**không phải** `image_1` phẳng.

Cạm bẫy đã dính thật 22/08/2026: ComfyUI báo lỗi

```
node 10: required_input_missing -> image_1
```

nên bản mẫu viết `image_1` **trông như đúng** — trong khi chính nó là thứ bị từ
chối. Lý do ở `execution.py:903`: khi hiện thông điệp nó làm `x.split(".")[-1]`,
tức **cắt mất tiền tố**. Tên thật nằm ở `extra_info.input_name`.

Đã thử **sáu** khuôn với ComfyUI thật (`image_1` phẳng · `images` là dict · `images`
là list · dict lồng hai lớp · `images.image_1` · hai ảnh có chấm). **Chỉ dạng có dấu
chấm được chấp nhận.**

⚠️ Và **đừng thêm khoá ghi chú vào tệp workflow JSON.** ComfyUI coi **mọi khoá cấp
cao nhất là một node**, `workflows.nap()` không lọc gì cả — một khoá `_ghi_chu` sẽ
thành một node không hợp lệ. Ghi chú để ở tệp này.

Xem `docs/ANH_NOI_BO/DECISIONS.md` D-031.
