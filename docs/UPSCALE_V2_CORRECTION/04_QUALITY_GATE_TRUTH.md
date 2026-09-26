# 04 — QUALITY GATE TRUTH

> Nguồn: `apps/upscalevideo/quality_gate.py` (bản sau sửa), `apps/upscalevideo/jobs.py`,
> `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE H.

## 5 khuyết tật của cổng cũ — vì sao mỗi cái là "impossible-by-construction"

| # | Khuyết tật | Vì sao KHÔNG THỂ hoạt động, không phải "có bug" |
|---|---|---|
| 1 | Gọi `ffprobe` để lấy PSNR/SSIM/VMAF | `ffprobe` không có filter graph. PSNR/SSIM/VMAF là filter của **`ffmpeg`** (`-lavfi psnr\|ssim\|libvmaf`). Không có cách nào gọi `ffprobe` để nó tính ba đại lượng này — không phải cú pháp sai, mà là **sai công cụ**. |
| 2 | Không có video tham chiếu | `video_key = test_video if test_video else output_key`, và caller (`jobs.py`) **không truyền** `test_video` ⇒ đo full-reference **với chính đầu ra**. PSNR/SSIM/VMAF full-reference so một tín hiệu với chính nó luôn cho điểm tối đa hoặc lỗi — con số này không đo được gì có ý nghĩa dù công cụ đúng. |
| 3 | Truyền khoá R2 như đường dẫn local | `out_key` (dạng `upscalevideo/<owner>/<job>/output_1080p.mp4`) được đưa thẳng vào `subprocess` như thể là đường dẫn tệp trên đĩa. Không `subprocess` nào mở được một khoá đối tượng R2 như tệp — đây không phải lỗi đường dẫn, mà là **hai không gian tên khác nhau bị lẫn**. |
| 4 | Đọc cả MP4 vào RAM cho PIL | `image_data = f.read()` rồi `Image.open(image_data)` — PIL cần path hoặc file-like object, `bytes` không có `.read()` ⇒ `AttributeError` ngay cả khi sửa lỗi đọc; và PIL **không giải mã được container MP4** dù sửa cách gọi. Đây là ghép sai công cụ cho định dạng, không sửa được bằng cách "gọi đúng API". |
| 5 | `UnboundLocalError` tiềm ẩn thoát ra ngoài | `_ffprobe` có thể `return psnr, ssim, vmaf` khi ba biến **chưa từng được gán** trên nhánh lỗi; `except` chỉ bắt `TimeoutExpired, ValueError, IndexError` — không bắt `UnboundLocalError`. Annotation kiểu trả `Tuple[float,float,float]` trong khi thực tế có thể trả `None` là khai sai chữ ký ngay từ đầu. |

## Cái giá đánh lên MỌI job khách (trước sửa)

`jobs.py` (bản cũ) gọi `run_quality_gates` **vô điều kiện**, mặc định **bật**,
không cờ tắt, ở progress 98%. Vì (1)-(5) ở trên, `check_quality` **luôn** trả
lỗi "ffprobe failed to parse quality metrics" và `check_blur` **luôn** trả
chuỗi exception — nhưng `jobs.py` chỉ log cảnh báo (dòng `raise` bị chú thích),
nên:

- **mọi** job thành công của khách mang `quality_warning` báo kiểm chất lượng
  thất bại — phản ánh lỗi trong mã cổng, không phản ánh video thật;
- mỗi job **đọc toàn bộ tệp đầu ra từ R2 vào RAM rồi ném đi** — tốn thời gian,
  RAM (video 4K ⇒ hàng trăm MB), và **egress R2 thật trả tiền**.

⇒ Đây không phải "một cổng vô hại bị lỗi" — đây là **thuế bắt buộc trên mọi
job + nhiễu lời khai gửi tới khách qua API/UI** (`routes.py:872` cũ).

## Cổng KỸ THUẬT mới — hợp đồng

Đổi hướng hoàn toàn: cổng mới **không** chấm chất lượng mô hình, chỉ trả lời
MỘT câu — *"tệp ta vừa tạo có đúng là video ta đã hứa không?"*

- **Chạy Ở ĐÂU**: trên tệp **local**, **trước khi upload** (`jobs.py:403-420`,
  chỗ duy nhất đường dẫn thật còn tồn tại — sau upload chỉ còn khoá R2).
- **Bật/tắt**: cờ môi trường `LTT_UPSCALE_TECH_GATE`, mặc định **BẬT**
  (`quality_gate.bat_cong()`). Tắt bằng `LTT_UPSCALE_TECH_GATE=0` — dùng khi
  cần cứu một job đang gấp; ⛔ tắt âm thầm là mất lưới duy nhất.
- **Kiểm gì (6 bước, `kiem_tra_dau_ra`)**:
  1. Tệp tồn tại và ≥ `MIN_BYTES` (10 KB) — không gọi `ffprobe` cho tệp quá nhỏ.
  2. Mở được bằng `ff.probe_video` (dùng lại, không viết lại logic đọc video).
  3. Khung hình đúng `(expect_w, expect_h)` ta đã tự tính.
  4. Codec THẬT khớp họ codec của `expect_encoder` qua bảng `HO_CODEC` — đây là
     lưới runtime bắt trực tiếp ISSUE J (xin HEVC, nhận H.264).
  5. Thời lượng trong dung sai 5% (tối thiểu 1.0 s) so với kỳ vọng.
  6. Có audio nếu khách yêu cầu giữ tiếng.
- **Fail hard vs warn**: mục 1-4 → `loi` (list khác rỗng ⇒ `ok=False`, job phải
  đỏ, **không upload, không thu tiền** một tệp không mở được hoặc sai hợp đồng
  codec). Mục 5-6 → `canh_bao` (ghi log + trả về `res["quality_warning"]`,
  không đánh đỏ — lệch thời lượng nhỏ do làm tròn GOP/keyframe là bình thường).
- **Không bao giờ tự sập làm hỏng job tốt**: mọi lỗi bất ngờ của chính cổng
  (không phải lỗi 1-6) phải rơi vào `canh_bao`, không ném ra ngoài.

## Chất lượng MÔ HÌNH (PSNR/SSIM/VMAF) thuộc về đâu

**Không thuộc đường job khách.** Đo chất lượng mô hình cần video **tham
chiếu** thật và một bộ dữ liệu chuẩn — hai điều kiện ISSUE H chứng minh không
thể có trong đường chạy production. Phép đo này đã tồn tại và chạy **ngoại
tuyến** ở `apps/qualitylab` (`materializer.py`, `evaluator_assets.py`,
`calibration.py`), với test thật: `tests/test_164_quality_lab_upscale.py`,
`tests/test_166_quality_lab_upscale_video.py`. ⛔ Đừng dựng lại phép đo PSNR/VMAF
trong `apps/upscalevideo/` — đó đúng là con đường đã tạo ra ISSUE H.
