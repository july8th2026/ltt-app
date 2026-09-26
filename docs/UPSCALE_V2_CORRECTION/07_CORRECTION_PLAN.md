# 07 — CORRECTION PLAN (Phases A–I)

> DONE = có sửa trong `apps/upscalevideo/*.py`, khoá bởi
> `tests/test_4904_upscale_correction.py`. DEFERRED = quyết định KHÔNG làm bây
> giờ, với evidence-gate rõ ràng để mở lại.

## A — Đồng thời GPU (ISSUE A/B) — **DONE (lời khai)**, DEFERRED (cơ chế)

- **DONE**: xoá lời khai ⛔ SAI "4→12 concurrent" khỏi `manifest.py:60`, viết lại
  đúng cơ chế (`UniqueConstraint`, `_con_cho`) ngay tại chỗ khai sai. Khoá bằng
  `test_gpu_lease_unique_constraint_khoa_dong_thoi_ve_mot` +
  `test_doc_truth_gate_manifest_va_ban_sua_khong_khai_dong_thoi_gia`.
- **DEFERRED**: shared-GPU scheduling thật (kế toán VRAM thay UNIQUE) — xem
  `02_GPU_SCHEDULER_TRUTH.md` mục cuối. Evidence-gate để mở lại: (1) đo được
  VRAM thật một tiến trình NCNN chiếm (không chỉ suy luận từ tile/threads);
  (2) quan sát được hàng đợi job GPU dài thật trên production (chưa có bằng
  chứng này — `CHƯA ĐO`).

## B — VRAM reservation (ISSUE B) — **DONE**

Giữ nguyên `gpu_vram_mb.fast = 1000` (đúng với đỉnh đo được 848 MB + an toàn),
nhưng bỏ diễn giải sai "mua thêm throughput". Không cần đổi số, chỉ cần đổi
lời khai — đã làm trong `manifest.py`.

## C — Ngưỡng autotune (ISSUE C) — **DONE**

`autotune.py`: đồng bộ chú thích với `est_alloc=1000` (bỏ "750 MB"/"800 MB"),
sửa chú thích tile (mã chọn tile NHỎ hơn cho khung LỚN, không phải ngược lại),
sửa dải Quality để `budget >= 5095` khớp `est=5095` (không còn tự vượt sàn).
Khoá: `test_autotune_fast_est_alloc_1000_khi_budget_du`,
`test_autotune_fast_tut_ve_du_phong_khi_budget_thap`,
`test_autotune_quality_khong_bao_gio_khai_can_nhieu_hon_budget`.

## D/E/F — Warmup + numpy/cv2 (ISSUE D/E/F) — **DONE**

- Xoá `_model_cache` chết. Đổi khoá cache warmup từ f-string
  `{model}_tile{tile}_j{threads}` (gần như không bao giờ trúng) sang tên model
  trần (`_model_warmup_cache[model] = timestamp`).
- `_warmup_model` giờ nhận và truyền `gpu_index` + `env` giống job thật — hết
  rủi ro chạy sai card trên máy có iGPU.
- Xoá import `numpy`/`cv2`; dùng `vulkan_device._tiny_png` (stdlib thuần
  `struct`+`zlib`) đã có sẵn.
- Docstring nói rõ warmup **không** giữ model trong VRAM (tiến trình con thoát
  hẳn trước job thật) — lợi ích thật chỉ là cache tệp OS/shader driver, không
  còn tuyên bố "giữ model nóng".

Khoá: `test_warmup_model_truyen_g_va_env_giong_job_that`,
`test_engine_khong_import_numpy_cv2`, `test_engine_khong_con_bien_model_cache_chet`,
`test_engine_khoa_cache_ham_nong_la_ten_model_tran_khong_phai_fstring_tile`.

## G — Checkpoint / resume (ISSUE G) — **DONE (khung sự thật)**, DEFERRED (resume thật)

- **DONE**: đổi tên khái niệm từ "resume" sang "sổ tiến độ" trong toàn bộ
  docstring; nối `cleanup_job_checkpoints` vào `finally` của `jobs.handle`
  (rò rỉ vĩnh viễn được vá); thêm `don_so_cu(ttl_ngay=7)` làm lưới thứ hai cho
  đường rò `os._exit`.
- **DEFERRED**: resume thật (đọc checkpoint để bỏ qua chặng). Evidence-gate:
  cần (1) workspace bền thay `tempfile.mkdtemp()` bị `rmtree`; (2) dấu tay
  (fingerprint tham số + model + phiên bản pipeline) để tái dùng an toàn. Cả
  hai **chưa xây** — xem `03_CHECKPOINT_TRUTH.md`. Mở lại khi có ca thật cần
  (job dài bị hết giờ lặp lại, đo được chi phí làm lại đáng kể).

## H — Quality gate (ISSUE H) — **DONE**

Bỏ hẳn cổng PSNR/SSIM/VMAF cũ (gọi sai công cụ, không tham chiếu, sai không
gian tên, PIL không đọc được MP4). Thay bằng cổng KỸ THUẬT chạy trên tệp local
trước upload: kiểm tồn tại/kích thước, mở được, đúng khung, đúng họ codec,
đúng thời lượng trong dung sai, có audio nếu yêu cầu. Cờ `LTT_UPSCALE_TECH_GATE`
(mặc định bật). Chất lượng MÔ HÌNH (PSNR/VMAF thật) ở `apps/qualitylab`, ngoại
tuyến, không đổi.

## I/J — Encoder + HEVC (ISSUE I/J) — **DONE (NVENC+CPU)**, DEFERRED (QSV/AMF thật)

- **DONE**: `_venc_args` ném `ValueError` cho tên nó không biết thay vì rơi
  âm thầm; đường CPU tôn trọng `codec` (`ENCODER_CPU` map H.264→`libx264`,
  HEVC→`libx265`); kết quả job tách `codec` (thật) khỏi `codec_requested` (ý
  khách); cổng kỹ thuật bắt lệch codec runtime.
- **DEFERRED**: hỗ trợ QSV/AMF THẬT (tham số `-c:v` đúng cho từng loại). Chốt
  2026-09-26: app chỉ hỗ trợ NVENC/CPU vì máy production không có phần cứng
  QSV/AMF để đo/test thật. Evidence-gate: có host QSV hoặc AMF thật trong hạ
  tầng để viết test không giả lập.

## K — Smooth motion / RIFE (ISSUE K) — **DEFERRED**

Không đổi: vẫn `minterpolate` (CPU). RIFE cần binary `rife-ncnn-vulkan.exe`
đóng gói vào `vendor/engine/` — **chưa có** vendor reference, chưa có lớp trừu
tượng gọi nó. Evidence-gate để mở lại: (1) có binary RIFE hợp pháp để đóng gói
(giấy phép, dung lượng); (2) đo được lợi ích tốc độ/CHẤT lượng thật so với
`minterpolate` trên bộ video test — hiện **CHƯA ĐO**, không dùng con số "5-10x"
đã bị xoá khỏi tài liệu vì chưa từng đo.

## L — Rò rỉ hết giờ cứng (MỚI, ngoài A–L gốc) — **DEFERRED (ngoài phạm vi app)**

`platform_core/job_runner.py:641-672` `_het_gio` dùng `os._exit(3)`, bỏ qua
`finally` của `jobs.py` (temp dir + checkpoint không được dọn ngay; tiến trình
con `realesrgan-ncnn-vulkan.exe`/`ffmpeg.exe` có thể mồ côi). Đây là mã dùng
chung cho MỌI app GPU/ffmpeg trên nền tảng, không riêng `upscalevideo` — sửa
tại `job_runner.py` cần đo tác động lên mọi app khác, ngoài phạm vi phiên sửa
này. `don_so_cu()` (mục G) là giảm nhẹ một phần (dọn sổ), không dọn temp dir
hay tiến trình mồ côi.

## M — Xác minh đầu ra (MỚI, ngoài A–L gốc) — **DONE**

Đã gộp vào cổng kỹ thuật (mục H): thành công không còn chỉ dựa `os.path.isfile()`
— cổng kiểm khung/thời lượng/codec/audio trước khi cho phép upload + thu tiền.

## Tổng kết

| Phase | Trạng thái |
|---|---|
| A (lời khai) | DONE |
| A (cơ chế shared-GPU) | DEFERRED |
| B | DONE |
| C | DONE |
| D/E/F | DONE |
| G (khung sự thật) | DONE |
| G (resume thật) | DEFERRED |
| H | DONE |
| I/J (NVENC+CPU) | DONE |
| I (QSV/AMF thật) | DEFERRED |
| K (RIFE) | DEFERRED |
| L (os._exit) | DEFERRED, ngoài phạm vi app |
| M | DONE |
