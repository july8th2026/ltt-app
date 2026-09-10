# THIẾT KẾ GUI — nghiên cứu trước, dựng sau

Ngày 07/09/2026. Nghiên cứu **ba nguồn** trước khi viết dòng giao diện nào:
nền tảng LTT · giao diện của chính WanGP · cái đang có.

---

## 1. 🔑 Phát hiện lớn nhất: nền tảng **đã có** phần lớn thứ tôi định xây

`server/routes/jobs.py` cung cấp sẵn, cho **mọi** app:

| Đường | Cho cái gì |
|---|---|
| `GET /jobs?app=lttvideo` | **lịch sử** — lọc theo người dùng · app · trạng thái · ngày, có phân trang |
| `GET /jobs/{id}` | trang chi tiết một job |
| `GET /jobs/{id}/progress` | mảnh tiến độ, **tự điều nhịp dò** |
| `POST /jobs/{id}/cancel` | **huỷ** |
| `POST /jobs/{id}/retry` | thử lại |
| `GET /jobs/{id}/artifacts/{i}` | tải kết quả, ưu tiên URL trực tiếp của kho |

Và `platform_core.models.Job` đã có `params` (JSON) · `result` (JSON) ·
`progress` · `progress_msg` · `dedupe_key` (chống bấm hai lần) · `JobEvent`
(dòng thời gian công khai).

⇒ **`C3` (lưu prompt) xong bằng cách gửi `prompt` vào `params`** — không cần
cột mới, không cần bảng mới.
⇒ **T6 gần như biến mất.** Không dựng bảng lịch sử riêng, không dựng đường tiến
độ riêng, không dựng nút huỷ riêng.

⭐ Đây là lần thứ hai trong chương trình mà *"đọc trước khi xây"* xoá nguyên một
hạng mục. Lần đầu là `metadata` của WanGP xoá `IntentResolver`.

### 🔴 Và nó lộ ra một lỗi mà một trang lịch sử tự viết sẽ **che mất**

`server/routes/jobs.py:_artifacts()` chỉ nhặt khoá có tên kết thúc bằng `_key`
(chuỗi) hoặc `_keys` (danh sách). `lttvideo.jobs.handle` trả `"tep": [...]`.

⇒ Job báo **XONG**, video nằm trong R2, và **người dùng không tải được** — một
thất bại **không để lại dấu hiệu nào ở phía máy chủ**. Đã đổi thành
`"video_keys"` và chốt bằng phép kiểm đọc AST.

⚠️ Nếu tôi dựng trang lịch sử riêng như plan cũ, trang ấy sẽ đọc `tep` và chạy
đúng — còn trang của nền tảng vẫn hỏng, âm thầm, cho tới lần đầu có người dùng
đường chuẩn.

---

## 2. WanGP tự chia giao diện thế nào

`GETTING_STARTED.md` §*Understanding the Interface*:

> **Main Generation Panel**: Model Selection · Prompt · Generate Button
> **Advanced Settings (click checkbox to enable)**: Steps, guidance, seeds ·
> Loras · Sliding Window

⇒ Ngay **chính WanGP** cũng chỉ để **ba** thứ ở panel chính. Mọi tham số kỹ
thuật nằm sau một ô tick.

⭐ Composer phẳng của ta = panel chính của WanGP **trừ đi Model Selection**, vì
`A1` nói người dùng không được thấy tên model. Nghĩa là thiết kế của ta không
phải một phát minh — nó là hình dạng của thượng nguồn, bớt đúng một ô.

---

## 3. Quy ước nhà LTT — dùng lại, đừng chế

| Mảnh dùng chung | Ở đâu | Dùng cho |
|---|---|---|
| `_job_progress.html` | `server/templates/` | thanh tiến độ + huy hiệu trạng thái |
| `_o_chon_tep.html` | `server/templates/` | ô chọn tệp — **`A1` đính media** |
| `_nap_trangthai.html` | `server/templates/` | trạng thái đang tải |
| `platform_core.image_input.validate_reference` | | kiểm ảnh tải lên |
| `platform_core.frontend_bundle.bundle_assets` | | đường dẫn bundle React |

### ⚠️ Một chỗ `lttvideo` đang lệch hợp đồng app

**12 app** giữ template ở `apps/<slug>/templates/`. `lttvideo` để ở
`server/templates/lttvideo.html`. Theo `CLAUDE.md` — *"Thêm một thư mục vào
`apps/`. **Không sửa** `server/`"* — chỗ hiện tại là sai. Chuyển về
`apps/lttvideo/templates/`.

---

## 4. Màn hình — đặc tả

### 4.1 Composer *(một màn hình, không tab chế độ)*

```
┌──────────────────────────────────────────────────────────┐
│  Tao video                                    [Lich su →]│
├──────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐  │
│  │ Mo ta video ban muon...                            │  │
│  │                                                    │  │
│  │  [📎 Them anh hoac video]        <- keo tha duoc   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Ti le  [16:9 ▾]   Do dai  [5s ▾]        ~150 credit     │
│                                                          │
│  ⚠️ Video tren 10 giay: chat luong co the troi dan       │
│                                                          │
│                                        [  Tao video  ]   │
└──────────────────────────────────────────────────────────┘
```

**Quy tắc**
- Không có ô nào tên `model`, `t2v`, `i2v`, `vace`, `steps`, `seed`,
  `guidance`. `test_724` đã chốt điều này trên nội dung kết xuất.
- Đính media **đổi model bên trong**, không đổi màn hình. Người dùng chỉ thấy
  một dòng: *"Sẽ dùng ảnh của bạn làm khung mở đầu."*
- Giá cập nhật khi đổi độ dài — công thức phẳng `30 credit/giây` nên tính được
  ở client, không cần gọi máy chủ.
- Cảnh báo trôi chất lượng chỉ hiện khi chọn ≥10 giây — **câu chữ lấy ý từ
  `PROCESSING.md` của WanGP**, không tự nghĩ mức độ.

### 4.2 Sau khi gửi

**Không** dựng màn chờ riêng. Chuyển thẳng tới `/jobs/{id}` của nền tảng — nơi
đã có tiến độ tự dò nhịp, nút huỷ, dòng thời gian, và ô tải kết quả.

⇒ Người dùng đóng trang rồi quay lại vẫn thấy đúng chỗ ấy. Đây là lý do
`A1`-lịch sử không cần code mới.

### 4.3 Lịch sử

Liên kết `Lịch sử →` trỏ `/jobs?app=lttvideo`. Hết.

### 4.4 Nút **Nâng nét**

Trên một job đã xong, nút gửi **job `upscalevideo`** với
`video_key` = khoá R2 của video.

```
lttvideo job xong -> result.video_keys[0]
        |
        v
   [Nang net] -> submit job `upscalevideo` {video_key, target_height: 1080}
```

⭐ Chạy trên **GPU máy A** (`realesrgan-ncnn-vulkan`), **không** đụng C-CLOUD.
Điều này xoá luôn lỗ hổng đã ghi ở `PLAN_V1_CHI_TIET.md` §5 — không còn cần đẩy
ngược tệp từ R2 lên C-CLOUD, và không cần thao tác thứ 7 ở cầu nối.

---

## 5. Vậy còn phải xây gì

| # | Việc | Lý do không tái dùng được |
|---|---|---|
| G1 | Chuyển template về `apps/lttvideo/templates/` | hợp đồng app |
| G2 | Ô đính media trong composer | dùng `_o_chon_tep.html`, nhưng luồng là của app |
| G3 | `chon_model()` đọc `metadata` | không ai có |
| G4 | Nút **Nâng nét** nối sang `upscalevideo` | dây nối giữa hai app |
| G5 | Cảnh báo trôi chất lượng ≥10 giây | nội dung sản phẩm |
| G6 | Ước giá ở client | công thức phẳng |

Sáu việc. Plan cũ có mười ba.

---

## 6. Điều đã **không** làm, và vì sao

- **Không** dựng trang lịch sử riêng — nền tảng đã có, và bản riêng sẽ che lỗi
  `_artifacts()`.
- **Không** dựng đường tiến độ riêng — `/jobs/{id}/progress` đã tự điều nhịp.
- **Không** dựng bảng CSDL riêng — `Job.params` giữ prompt, `Job.result` giữ
  khoá.
- **Không** dựng engine upscale — `apps/upscalevideo` đã có, chạy GPU máy A.
