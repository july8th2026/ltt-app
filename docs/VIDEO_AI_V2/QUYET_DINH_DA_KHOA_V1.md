# QUYẾT ĐỊNH ĐÃ KHOÁ — V1

Chủ dự án trả lời 06/09/2026. Đây là nguồn chân lý cho plan code; nơi nào
`CAU_HOI_CHO_CHU_DU_AN.md` khác tệp này thì tệp này đúng.

| | Quyết định |
|---|---|
| A1 | **Cơ chế đầy đủ kiểu Seedance** — không rút gọn về text-only |
| A2 | **15 giây** |
| A3 | **Có nút Upscale**, là một tính năng riêng |
| A4 | Không mở `negative_prompt` / `seed` ra GUI |
| A5 | Có bộ mở rộng prompt, **đi đường LLM nội bộ của LTT** như `lttchat` |
| B1 | **Bật pod theo nhu cầu**, tắt khi rảnh |
| B2 | Như WanGP triển khai — tuần tự, dùng chính hàng đợi của nó |
| B3 | Không thuê được GPU ⇒ **báo lỗi ngay + hoàn credit** |
| C1 | Giữ `admin` + `nhan_vien` |
| C2 | Giữ video **3 ngày** |
| C3 | Lịch sử **có** lưu prompt |

Đã chốt từ trước: profile 1 · 30 credit/giây video · `t2v_2_2` · `832x480` ·
30 bước · `sage2`.

---

## 1. A2 — WanGP **có** cơ chế nối video: *sliding windows*

`PROCESSING.md` §*Long Videos Workflows*. Hai cách dựng video nhiều cửa sổ:

| Cách | Ưu | Nhược |
|---|---|---|
| **Lên lịch cả loạt trong MỘT lượt sinh** (mỗi dòng prompt một cửa sổ) | *"best technical quality"* — WanGP giữ các cửa sổ trong bộ nhớ, **mã hoá đúng một lần** | tốn RAM hơn, phải quyết trước |
| Nối tiếp video đã có, lặp lại | ứng biến được | mỗi lần nối là **một lần mã hoá lại có mất mát** |

⇒ **Chọn cách 1.** Composer phẳng chỉ có một prompt, mà WanGP quy định *"nếu số
cửa sổ nhiều hơn số dòng prompt thì dòng cuối lặp lại"* — nên một prompt tự trải
ra mọi cửa sổ, không cần ta xử lý gì.

### Số khung cho 15 giây

`t2v_2_2` chạy **16 fps**; khung hợp lệ là `5 + 4k`. 15 giây ⇒ **241 khung**.

```
Generated Frames = [So cua so - 1] x [Window Size - Overlap - Discard] + Window Size
```

⛔ **KHÔNG tự tính rồi truyền số cửa sổ.** `apply_video_length_duration()` của
WanGP nhận thẳng `"15s"` và tự quy ra khung hợp lệ. Ta truyền `"15s"`.

### ⚠️ Cảnh báo của chính WanGP phải đưa lên GUI

> *"The longer the video, the more likely quality is to degrade over time:
> artifacts can accumulate and character identity may progressively drift."*

15 giây ≈ 3–4 cửa sổ. Đây là **đánh đổi có thật**, không phải chi tiết kỹ thuật
giấu đi được. GUI phải nói ra khi người dùng chọn độ dài lớn.

---

## 2. A3 — Upscale **đúng là một tính năng riêng**

`API.md` §*Late Postprocessing And Media Editing*:

```python
job = session.submit_media_postprocessing(
    "input.mp4", spatial_upsampling="lanczos*2", return_media=True)
```

*"Postprocessing is applied after media exists. It can run immediately after
generation or later from the Media Info / Late Post Processing area."*

⇒ Đúng hình dung của anh: một nút trên **video đã có**, không phải một tuỳ chọn
lúc sinh.

🔴 **Sửa một điều tôi nói sai trước đó.** Tôi từng nêu `vae_upsampler: [1,2]` của
`t2v_2_2` như đường nâng ×2. Tài liệu nói ngược:

> *"**VAE upsamplers** are model-pipeline features and **are not accepted for
> late postprocessing**."*

VAE upsampler là tuỳ chọn **lúc sinh**. Nút Upscale phải dùng bộ hậu kỳ đã đăng
ký: `lanczos*2` · `flashvsr*2` · `coz*4`, và `temporal_upsampling` (`rife*2`) nếu
muốn tăng fps.

⇒ **Cầu nối cần thao tác thứ 7**: `/hau_ky`. Sáu thao tác hiện có không làm được
việc này.

---

## 3. A5 — bộ mở rộng prompt: đi đường LTT, **không** đi đường remote của WanGP

`REMOTE_LLMS.md` cho biết đường remote của WanGP là:

- chỉ ba engine: **Codex · Claude Code · OpenCode**, đều là **CLI cài trên máy
  chạy WanGP**;
- đều **bắt buộc `Deepy Prime`**;
- *"Remote engines can send prompts, attached images, sampled video frames…
  over the internet"* — tức prompt đi ra ngoài **từ C-CLOUD**.

Ba hệ quả đụng thẳng vào ranh giới đã khoá ở *Phần 7 — security*: phải cài thêm
phần mềm lên C-CLOUD, phải đặt credential ở đó, và dữ liệu người dùng rời máy
từ phía C-CLOUD chứ không phải từ LTT.

### ⇒ Đường đã chọn: mở rộng prompt **trên máy A**, trước khi gửi

```
nguoi dung go prompt
      -> LTT goi LLM NOI BO (nhu `lttchat`)      <- credential nam o LTT
      -> prompt cuoi cung
      -> gui sang C-CLOUD nhu mot prompt thuong  <- WanGP khong biet co LLM
```

Lợi: C-CLOUD không cần cài gì thêm, không giữ credential nào, không có dữ liệu
người dùng đi ra từ đó. Và `prompt_enhancer` của WanGP giữ nguyên **rỗng** —
đúng mặc định factory, không lệch hồ sơ.

📌 Đường dự phòng nếu LLM nội bộ bận (máy B chỉ có **một suất đồng thời**):
**bỏ qua bước mở rộng**, gửi prompt gốc. Mở rộng prompt là *thêm giá trị*, không
phải *điều kiện cần* — hỏng nó không được làm hỏng việc sinh video.

---

## 4. A1 — soát lại GUI: cái đang có **chưa phải** cơ chế Seedance

### Đang có
`prompt` (textarea) · `ti_le` (select) · `do_dai_s` (select) · nút gửi. Hết.

### Thiếu, và mỗi thiếu sót là một mảnh của cơ chế đầy đủ

| # | Thiếu | Vì sao bắt buộc |
|---|---|---|
| 1 | **Đính media** (ảnh/video) | Đây **chính là** Seedance: prompt + media, hệ thống tự hiểu. Không có nó thì mọi thứ khác chỉ là T2V |
| 2 | **Lịch sử / thư viện** | Job mất 13–40 phút; không có chỗ quay lại thì kết quả **mất** |
| 3 | **Tiến độ** | Đã có `/progress` chạy đúng, GUI chưa dùng |
| 4 | **Huỷ** | Đã có `/cancel`, GUI chưa dùng |
| 5 | **Nút Upscale** | A3 |
| 6 | Độ dài tới **15s** | A2 — và đang chào "10 giây" mà chưa dựng đường nối cửa sổ |
| 7 | Cảnh báo trôi chất lượng | §1 |

### Chọn model — đọc `metadata`, không tự phân loại

WanGP công bố `metadata.capabilities` + `metadata.media_inputs` cho từng model
(`SETTINGS.md`). Bước duy nhất của LTT là **lọc**: model nào nhận đúng bộ media
người dùng đính. Người dùng không bao giờ thấy `t2v` / `i2v` / `vace`.

⚠️ **Hệ quả về đĩa và tiền** phải nói trước:

| Đầu vào | Model | Tải thêm |
|---|---|---|
| chỉ chữ | `t2v_2_2` | đã có (44,8 GB) |
| + ảnh | `i2v_2_2` | **~30 GB** |
| + video | `vace_14B` | **~30 GB** |

Volume 300 GB còn dư. Tải một lần, nằm trên volume.

---

## 5. B1 + B3 — pod theo nhu cầu, và hai vế phải khớp nhau

**B1**: bật khi có job, tắt khi hàng đợi rỗng.
**B3**: không thuê được GPU ⇒ báo lỗi ngay, hoàn credit.

Hai quyết định này **ăn khớp**: vì không chờ dài, nên không cần hàng đợi treo.

### Chi phí thời gian mỗi lần bật — đo được, không ước

| Bước | Giây |
|---|---|
| `POST /pods/{id}/start` → container chạy | ~40 |
| `cai_dat.sh` tự lành nửa tạm (apt) | ~40 |
| nạp + ghim model (profile 1, từ ổ mạng) | **~450** |
| **tổng trước khi sinh được** | **~9 phút** |

⇒ Video 15 giây ≈ 9 phút khởi động + ~3× thời gian sinh của 5 giây. GUI phải
báo con số thật, không báo "vài phút".

⛔ Rủi ro đã trả giá ngày 06/09 và **B3 chính là bản vá cho nó**: `stop` rồi hơn
một tiếng không `start` lại được. Với B3, lượt đó thành *"báo lỗi + hoàn
credit"* thay vì *"job treo vô hạn"*.

### Điều phối viên — thành phần MỚI duy nhất

Máy A cần một tiến trình biết: có job ⇒ bật pod, chờ `/health`, gửi; hàng rỗng
⇒ tắt pod. Đây là **thành phần LTT mới thật sự cần**, khác với 12 lớp trùng lặp
đã xoá ở lượt audit — vì WanGP **không biết gì về RunPod**.

---

## 6. Việc phải làm — không việc nào cần GPU cho tới bước cuối

| # | Việc | GPU |
|---|---|---|
| V1 | Ảnh chụp `metadata` của model tại SHA ghim, làm fixture | ❌ |
| V2 | Composer: đính media → lọc model theo `metadata` → `apply_media_flag_defaults()` | ❌ |
| V3 | Điều phối viên pod (bật/chờ/tắt) + B3 báo lỗi & hoàn credit | ❌ |
| V4 | Lịch sử + tiến độ + huỷ trên GUI; giữ **3 ngày** (C2), lưu prompt (C3) | ❌ |
| V5 | Thao tác thứ 7 `/hau_ky` + nút Upscale | ❌ |
| V6 | Mở rộng prompt qua LLM nội bộ, có đường bỏ qua khi bận | ❌ |
| V7 | Độ dài tới 15s: truyền `"15s"`, để WanGP tự quy khung | ❌ |
| V8 | Tải `i2v_2_2` (+`vace_14B`) về volume | ⚠️ cần pod, không cần sinh |
| V9 | Nghiệm thu đầu-cuối | ✅ |
