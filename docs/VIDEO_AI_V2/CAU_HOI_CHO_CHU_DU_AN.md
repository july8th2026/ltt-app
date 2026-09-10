# CÂU HỎI CHỜ CHỦ DỰ ÁN — để khoá plan code

Ngày 06/09/2026. Đọc kèm `PLAN_TOAN_DIEN_THEO_TAI_LIEU_WANGP.md`.

⭐ **Nguyên tắc lọc câu hỏi.** Chỉ hỏi những gì **WanGP không quyết được thay**.
Mọi thứ WanGP đã có lời giải (độ phân giải mặc định, số bước, cờ dòng lệnh, cách
đặt cờ media…) đã lấy về dùng, không đưa vào đây.

Đã chốt, không hỏi lại: **profile 1** · **30 credit/giây video** · `t2v_2_2` ·
`832x480` · `30 bước` · `sage2`.

---

## A — PHẠM VI SẢN PHẨM

### A1. V1 nhận những loại đầu vào nào?

**WanGP đã chốt:** mỗi model tự công bố `metadata.media_inputs`. `t2v_2_2` nhận
**text**; ảnh/video cần model khác (`i2v_2_2`, `vace_14B`…).

**Phần anh quyết:** V1 mở tới đâu.

| | Phương án | Đổi lại |
|---|---|---|
| a | **Chỉ prompt** (text→video) | xong ngay; 44,8 GB model đã có |
| b | prompt **+ ảnh** (ảnh đầu) | thêm `i2v_2_2` ≈ **+30 GB** tải và đĩa |
| c | prompt + ảnh + video (control) | thêm `vace_14B`, phức tạp hơn nhiều |

*Đề xuất: **(a)** cho V1.* Composer phẳng vẫn thiết kế sẵn chỗ cho ảnh — thêm
model sau là **thêm dữ liệu, không sửa mã**.

---

### A2. Video dài tối đa bao nhiêu?

**WanGP đã chốt:** `t2v_2_2` chạy **16 fps**; số khung hợp lệ là
`5, 9, 13, … (bước 4)`. Một cửa sổ ~81 khung = **5,06 giây**. Dài hơn thì WanGP
**có** `sliding_window` cho model này.

**Phần anh quyết:** V1 có mở quá một cửa sổ không.

| | Phương án | Đổi lại |
|---|---|---|
| a | **≤ 1 cửa sổ (~5 giây)** | ~13 phút/video, đường đơn giản nhất |
| b | tới ~10 giây (2 cửa sổ) | ~26 phút/video, thêm tham số nối cửa sổ |

⚠️ GUI hiện cho chọn **5 và 10 giây**. Nếu chọn (a) thì phải bỏ mục 10 giây —
hiện nó **hứa thứ chưa dựng**.

*Đề xuất: **(a)**, và sửa GUI cho khớp.*

---

### A3. Có mở lựa chọn "nét hơn" không?

**WanGP đã chốt:** `README.md:234` — sinh 480p rồi nâng cấp. `wan_handler.py:341`
cho biết `t2v_2_2` có sẵn `vae_upsampler: [1, 2]` ⇒ nâng **×2** →
**`1664x960`**, và hai khoá `spatial_upsampling` / `temporal_upsampling` đã nằm
trong 115 khoá settings.

**Phần anh quyết:** người dùng có thấy nút này không.

| | Phương án | Đổi lại |
|---|---|---|
| a | **luôn 480p**, không hỏi | rẻ nhất, ít lựa chọn nhất |
| b | thêm công tắc "Nét hơn" | tốn thêm thời gian GPU (chưa đo) |
| c | luôn nâng ×2 | mọi video đắt hơn |

*Đề xuất: **(a)** cho V1; (b) khi đã có job thật để so.*

---

### A4. Người dùng được chỉnh những gì?

**Hiện tại** `KHOA_NGUOI_DUNG_DOI_DUOC` = `prompt`, `negative_prompt`, `seed`,
`resolution`, `video_length`. GUI mới lộ **prompt · tỉ lệ · độ dài**.

**Phần anh quyết:** có mở thêm `negative_prompt` và `seed` ra GUI không?

*Đề xuất: **không** — trái tinh thần composer phẳng. `seed` để hệ thống sinh;
`negative_prompt` để mặc định.*

---

### A5. Có bật Prompt Enhancer của WanGP không?

**WanGP đã có:** `PROMPTS.md:406` — bộ mở rộng prompt tích hợp, nhiều backend
(Qwen…), bật tự động hoặc theo yêu cầu.

**Phần anh quyết:** có dùng không. Nó **sửa prompt của người dùng** trước khi
sinh, và cần **tải thêm model LLM**.

*Đề xuất: **không** cho V1 — thêm model, thêm bất ngờ cho người dùng.*

---

## B — VẬN HÀNH VÀ TIỀN

### B1. 🔴 Pod bật 24/7 hay bật theo nhu cầu? *(câu đắt nhất)*

**Đo được hôm nay:** nạp + ghim model ở profile 1 mất **~7,5 phút**. Sau đó model
nằm nóng, job tiếp theo bỏ qua bước này.

| | Phương án | Tiền | Người dùng chờ |
|---|---|---|---|
| a | bật 24/7 | **$1,59/giờ ≈ $1.145/tháng** | ~13 phút |
| b | bật khi có job, tắt khi rảnh | chỉ trả lúc chạy | ~13 + **7,5** phút, **và có thể không thuê được card** |
| c | bật theo giờ làm việc | ~1/3 của (a) | như (a) trong giờ |

⚠️ `TAI_NGUYEN_VA_CACH_DUNG_LAI.md` §4: ngày 06/09 `stop` rồi **hơn một giờ**
mới `start` lại được — `US-KS-2` thường xuyên hết A100. Phương án (b) mang rủi
ro đó vào **mỗi** job.

*Đề xuất: **(c)**, và tắt bằng tay khi hết việc.*

---

### B2. Bao nhiêu job chạy cùng lúc?

**WanGP đã chốt:** `init()` chỉ gọi được **một lần mỗi tiến trình**
(`P01-D-13`); `submit_task` xếp hàng trong chính WanGP ⇒ **một pod xử lý tuần
tự**.

**Phần anh quyết:** hàng đợi LTT sâu bao nhiêu, và người dùng có thấy vị trí
trong hàng không.

*Đề xuất: hàng đợi **không giới hạn**, GUI hiện "đang chờ / thứ N".*

---

### B3. Khi máy tắt hoặc không thuê được GPU thì sao?

| | Phương án | |
|---|---|---|
| a | job **xếp hàng chờ**, chạy khi máy lên | credit đã giữ chỗ nằm chờ theo |
| b | **báo lỗi ngay**, hoàn credit | người dùng biết ngay, phải bấm lại |

*Đề xuất: **(b)** cho V1 — đơn giản và trung thực. Không có gì tệ hơn một job
nằm im không rõ bao giờ chạy.*

---

## C — DỮ LIỆU VÀ QUYỀN

### C1. Ai được dùng?

**Hiện tại:** `surface="admin"`, `public=False`, vai `nhan_vien` + `admin`.
Giấy phép WanGP **cấm bán lại** nên cổng thương mại đóng **bằng giấy phép**,
không phải bằng cấu hình.

**Phần anh quyết:** giữ nguyên, hay thu hẹp về chỉ `admin`?

*Đề xuất: giữ nguyên.*

---

### C2. Video lưu trong R2 bao lâu?

Mỗi video ~16 MB. Chưa có luật dọn.

*Đề xuất: giữ **90 ngày** rồi xoá, có báo trước trong GUI.*

---

### C3. Lịch sử có lưu prompt không?

⚠️ WanGP **nhúng prompt vào tên tệp** (thấy rõ ở lượt E2E hôm nay). Ta đã đổi
tên khi đẩy lên R2 (`lttvideo/<user>/<uuid>.mp4`) nên prompt **không rò qua tên
tệp**.

**Phần anh quyết:** có lưu prompt vào bảng lịch sử để người dùng xem lại không?

*Đề xuất: **có** — người dùng cần biết mình đã yêu cầu gì.*

---

## Tóm tắt: chỉ cần trả lời 11 chữ cái

```
A1: a / b / c        B1: a / b / c        C1: giu / chi admin
A2: a / b            B2: dong y / khac    C2: 90 ngay / khac
A3: a / b / c        B3: a / b            C3: co / khong
A4: dong y / khac
A5: khong / co
```
