> ⛔ **TỆP NÀY ĐÃ BỊ THAY** bởi `PLAN_V1_CHI_TIET.md` (07/09/2026).
> Giữ lại để tra lịch sử. Đừng thi hành theo nó — một số kết luận trong
> đây đã bị chính phiên sau bác bằng bằng chứng.

# PLAN TOÀN DIỆN — DỰNG TỪ TÀI LIỆU WanGP

Ngày 06/09/2026. Thay `PLAN_SUA_LAI_THEO_WANGP.md` và phần tham số của
`FINAL_IMPLEMENTATION_PLAN.md`.

⭐ **Cách tệp này được dựng, và vì sao nó khác các bản trước.** Các bản trước
dựng kiến trúc trước rồi mới đọc WanGP để đối chiếu. Bản này đi ngược lại: đọc
**26 tài liệu** trong `docs/` cộng ba tệp triển khai ở gốc kho (`Dockerfile`,
`entrypoint.sh`, `run-docker-cuda-deb.sh`), rồi mới hỏi *"còn lại gì cho ta
xây?"*.

Kết quả: **phần lớn thứ tôi định xây thì WanGP đã công bố sẵn**, và ba hạng mục
tôi từng ghi là "ẩn số phải đo" thì có hẳn một tệp trả lời.

---

## 1. Những gì WanGP QUYẾT ĐỊNH THAY TA — không cần đo, chỉ cần lấy

| Hạng mục | Tài liệu | Giá trị |
|---|---|---|
| Model cho general T2V | `MODELS.md` | **`t2v_2_2`** (Wan 2.2 T2V 14B) |
| Độ phân giải mặc định | `wgp.py:3219` | **`832x480`** (720p chỉ khi tên model chứa "720") |
| Số bước mặc định | `models/_settings.json` | **30** |
| Số bước cho **chất lượng** | `TROUBLESHOOTING.md:247` | *"Increase number of steps (25-30+)"* |
| Đường lên độ phân giải cao | `README.md:234` | **sinh 480p rồi nâng cấp**, không sinh thẳng |
| Cấu hình cho **lớp card Ampere** | `TROUBLESHOOTING.md:92` | `--compile --attention sage2 --profile 3 --teacache 2.0` |
| Biến môi trường lúc chạy | `entrypoint.sh` | TF32 ×2 · 4 biến luồng · `PYTHONUNBUFFERED` |
| Ảnh nền + torch | `Dockerfile` | `cuda:12.8.1-cudnn-devel-ubuntu22.04` + `torch 2.10.0+cu128` |

🔴 **A100 là Ampere — cùng thế hệ RTX 30XX.** Dòng khuyến nghị của WanGP cho lớp
card ấy là dòng trên. Ta đang chạy **thiếu `--compile`**, **thiếu `--teacache`**,
và **profile 1 thay vì 3**.

### Về profile 1 và profile 3 — bằng chứng, chưa phải quyết định

`CLI.md:147-150`:

> Profile 1: *"Load entire current model in VRAM and **keep all unused models in
> reserved RAM** for fast VRAM transfers"*
> Profile 3: *"Load entire current model in VRAM (requires 24GB for 14B model)"*

Khác biệt là mệnh đề **"unused models"**. Đo được ngày 06/09: khởi động ở
profile 1 mất **~7 phút** ghim `transformer` · `transformer2` · `vae` ·
`text_encoder` (~37 GB) vào RAM dành riêng, đọc từ **ổ mạng**.

⇒ Ưu thế của profile 1 là **đổi model nhanh**. Dịch vụ của ta phục vụ **một
model**, nên nó trả cái giá mà không dùng cái lợi. WanGP khuyến nghị **3** cho
lớp card này.

⛔ `P01-D-15` chốt profile 1 sau khi anh hỏi thẳng về nó. **Không tự đổi.** Đây
là bằng chứng để anh quyết, không phải một thay đổi tôi được làm một mình.

---

## 2. 🔑 WanGP CÔNG BỐ khả năng của từng model — thay hẳn lớp tôi định xây

`SETTINGS.md` mục *API Metadata About Models*: mỗi model mang sẵn một khối
`metadata`:

```json
"metadata": {
  "inputs": ["text", "image", "video", "audio"],
  "capabilities": { "text_to_video": true, "image_to_video": true, "audio_output": true },
  "media_inputs": {
    "image": { "start": true, "end": true, "reference": true, "control": false, "mask": false },
    "video": { "continue": true, "control": true, "mask": false },
    "audio": { "prompt": true, "output": true }
  },
  "setting_values": { "image_prompt_type": { "allowed": "TVSE" } },
  "frames_maximum": 97
}
```

⭐ Đây **chính xác** là câu hỏi mà `IntentResolver` / `CapabilityResolver` /
`ModelRegistry` tôi từng phác sẽ trả lời. Chúng đã bị xoá ở lượt audit vì trùng
lặp — nhưng lúc đó tôi **chưa biết WanGP công bố sẵn dữ liệu này**. Nay biết thì
kết luận mạnh hơn: không chỉ "đừng xây", mà là **có sẵn một nguồn để đọc**.

### Và tài liệu cấm luôn cách làm sai

`SETTINGS.md`, cuối mục `video_prompt_type`:

> *"Always prefer a value from the selected model's exposed choices instead of
> composing a string by hand."*

⇒ **Không tự ghép chuỗi cờ.** Đính media rồi gọi `apply_media_flag_defaults()`
của WanGP; nó đọc `image_prompt_types_allowed` / `image_ref_choices` của model
và đặt cờ. Ta chỉ chuyển tiếp.

### Composer phẳng, dựng hoàn toàn trên hợp đồng của WanGP

```
nguoi dung: prompt + (0..n media) + ti le + do dai
      |
      v
[1] doc `metadata.capabilities` + `metadata.media_inputs` cua cac model
    -> model nao NHAN duoc dung bo media nay
[2] settings = ho so da duyet cua model do
[3] apply_media_flag_defaults(settings, media)     <- WanGP dat co
[4] apply_video_length_duration(settings, ...)     <- WanGP quy giay ra khung
[5] submit_task(settings)
```

Bốn trong năm bước là **gọi hàm của WanGP**. Bước duy nhất của LTT là `[1]`, và
nó là một phép **lọc trên dữ liệu WanGP công bố** — không phải một taxonomy tự
nghĩ. Người dùng không bao giờ thấy chữ `t2v` / `i2v` / `vace`.

---

## 3. Ba thứ tôi từng ghi "ẩn số phải đo" mà tài liệu đã trả lời

| Tôi ghi | Tệp trả lời |
|---|---|
| *"danh sách bộ nâng cấp — phải đo trên máy"* | `SPATIAL_UPSAMPLERS.md` · `TEMPORAL_UPSAMPLERS.md` |
| *"113 khoá hồ sơ — chưa đối chiếu"* | `SETTINGS.md` mô tả **từng** khoá |
| *"A/B xem TF32 và `--compile` đáng bao nhiêu"* | `TROUBLESHOOTING.md` đã khuyến nghị cả hai |

🔴 Cái thứ ba là lỗi nguyên tắc, không phải lỗi công sức: **A/B để xem khuyến
nghị của thượng nguồn có đúng không là đang thẩm định lại thượng nguồn**, trong
khi luật đã đặt là *bám theo*. Đã bỏ khỏi plan.

---

## 4. Cái gì THỰC SỰ còn phải đo, và khi nào

Chỉ **một**: `GIAY_GPU_MOI_GIAY_VIDEO` trong `cost.py`.

WanGP không thể trả lời hộ — nó phụ thuộc card của ta, độ phân giải của ta, cấu
hình của ta. Nhưng:

- Nó **không chặn việc xây**: quyết toán đi theo **giây GPU thật**
  (`quyet_toan_credit`); hằng số chỉ định cỡ khoản **giữ chỗ**.
- Nó chỉ cần đúng **trước khi bán**, không phải trước khi chạy.
- Lượt E2E đang chạy **tự sinh ra số đó** mà không cần một lượt đo riêng.

Số đo được tới lúc này (832x480 / 30 bước / profile 1, chưa `--compile`, chưa
`--teacache`): **27,45 giây/bước** — so với 79,8 giây/bước ở 1280x720 / profile 4.

---

## 5. Việc còn lại, theo thứ tự — phần lớn KHÔNG cần GPU

### N1 — hoàn tất E2E đang chạy *(đang chạy)*
Nhận tệp, tải về, đẩy R2, dọn tạm. Chứng minh cả sáu thao tác của cầu nối.

### N2 — áp trọn cấu hình WanGP khuyến nghị *(không đo, chỉ lấy)*
`--compile`, `--teacache 2.0`, chín biến của `entrypoint.sh`. Profile để anh
quyết (§1).

### N3 — đọc `metadata` của model thay vì tự phân loại *(không cần GPU)*
Gọi `get_model_schema()` / `list_model_defs()`, lưu ảnh chụp tại SHA ghim làm
fixture, dựng bước `[1]` của composer trên đó.

### N4 — đối chiếu 113 khoá hồ sơ với `SETTINGS.md` *(không cần GPU)*

### N5 — nâng cấp 480p→720p theo `SPATIAL_UPSAMPLERS.md` *(không cần GPU để chốt)*
Hai khoá `spatial_upsampling` / `temporal_upsampling` đã nằm trong 115 khoá.

### N6 — nối GUI ↔ job ↔ credit ↔ R2, rồi nghiệm thu

---

## 6. Điều không đổi

Kiến trúc tối giản đã khoá vẫn đứng, và lượt đọc tài liệu này **củng cố** nó:
mỗi lần đọc thêm một tệp của WanGP, số lớp LTT cần xây lại **giảm**, chưa lần
nào tăng.
