# 01 — REGRESSION AUDIT (Upscale Video V2)

> Nguồn: `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` (13 khuyết tật, mỗi
> dòng có `tệp:dòng`). Bảng dưới: mỗi hàng là MỘT khuyết tật — khai gì, mã làm
> gì, ẩn hay lộ, khách có thấy không. "Ẩn" = không có triệu chứng runtime rõ
> ràng cho tới khi điều kiện cụ thể xảy ra (driver khác, GPU khác, job dài).

| # | Khuyết tật | Lời khai (docs cũ) | Mã LÀM (trước sửa) | Ẩn/Lộ | Khách thấy? |
|---|---|---|---|---|---|
| A | Đồng thời GPU | "4→12 concurrent", "GPU util ~90%" — 9 vị trí, `manifest.py:60` (`00_CURRENT_TRUTH.md` dòng 73-78) | `GpuLease.UniqueConstraint("host","gpu_uuid")` (`models.py:1037`) khoá đồng thời = **1**, không phụ thuộc `gpu_vram_mb` | **Ẩn** — không lỗi runtime, chỉ là con số sai trong comment/docs | Không trực tiếp; gián tiếp nếu vận hành lập kế hoạch công suất theo con số sai |
| B | VRAM reservation | Hạ `gpu_vram_mb.fast` 2000→1000 để "tăng throughput" | Chỉ đổi sàn `_con_cho` (`gpu_lease.py:166`) nhận **một** job; không mua job thứ hai | Ẩn | Không |
| C | Ngưỡng autotune | 3 chú thích nói "750 MB"/"800 MB", hàm dùng `est_alloc=1000` | `budget < est_alloc` với `est_alloc=1000` (`autotune.py:99,103`) — chú thích và dải Quality (`>=5000` nhưng khai `est=5095`) tự mâu thuẫn với chính mã cạnh nó | Ẩn — hành vi runtime đúng theo số 1000/dải đã sửa; chỉ tài liệu/chú thích từng sai | Không |
| D | Warmup giữ model | "Model warmup COMPLETE", `_model_cache` | `subprocess.run` (đồng bộ, chờ thoát) rồi job thật spawn `Popen` MỚI ⇒ không giữ gì trong VRAM; `_model_cache` khai rồi không đọc/ghi (mã chết); khoá cache theo `model_tile_threads` gần như không bao giờ trúng | Ẩn — job vẫn chạy đúng, chỉ mất lợi ích warmup đã hứa | Không (chỉ chậm hơn hứa, không sai kết quả) |
| E | Warmup không ghim GPU | (không có tuyên bố, nhưng ngầm định warmup "an toàn") | `subprocess.run` warmup **không** truyền `-g`/`env` trong khi job thật có; máy có iGPU Intel ⇒ warmup có thể chạy nhầm card | **Ẩn cho tới khi có iGPU/nhiều GPU** — đúng lớp sự cố `vulkan_device.py` đã ghi ngày 2026-09-11 | Không trực tiếp; rủi ro thật nếu tái diễn |
| F | numpy/cv2 thừa | (không có tuyên bố) | Import 2 dependency nặng chỉ để tạo 1 PNG xám 512×512; `vulkan_device.py:83-97` đã có `_tiny_png` (stdlib) | Lộ nhẹ — tăng thời gian cài đặt/kích thước vendor, không ảnh hưởng hành vi | Không |
| G | Checkpoint = resume | "Resume logic implemented", "Full stage recovery 9/10" (`PROGRESS_REPORT.md:81`, `13_FINAL_REPORT.md:63-64`) | Chỉ có `save_checkpoint` fire-and-forget; `load_checkpoint`/`get_job_checkpoints` **0 caller** trong cả kho; retry giữ nguyên `job_id` nhưng làm lại 100% | **Ẩn cho tới khi worker chết giữa chừng** — lúc đó khách chờ lâu hơn tưởng (không có gì được "tiếp tục") | Gián tiếp — retry sau sự cố chậm hơn khách tưởng, không mất tiền/dữ liệu |
| G' | Rác checkpoint | (không có tuyên bố) | `cleanup_job_checkpoints` khai nhưng **0 caller** ⇒ mỗi job để lại vài trăm B–1 KB vĩnh viễn dưới `tmp/upscale/<job_id>/` | Ẩn — rò rỉ chậm, cần hàng chục nghìn job mới đáng kể | Không |
| H | Quality gate PSNR/SSIM/VMAF | "Quality Gate Runner ✅ COMMITTED", "integration COMPLETE" (`COMMIT_SUMMARY.md:42`) — nhưng `PROGRESS_REPORT.md:94` cùng đợt lại ghi PENDING | `ffprobe` không có filter PSNR/SSIM/VMAF (đó là filter `ffmpeg`); không video tham chiếu (đo với chính nó); truyền khoá R2 làm đường dẫn local; đọc cả MP4 vào RAM cho PIL (không giải mã được) | **LỘ — mọi job khách** | **Có** — mọi job thành công đều mang `quality_warning` báo "kiểm chất lượng thất bại" (phản ánh lỗi mã, không phản ánh video), cộng chi phí đọc R2 vô ích mỗi job |
| I | Encoder QSV/AMF | "NVENC fallback chain (QSV→AMF)" (`COMMIT_SUMMARY.md:32`) | `_resolve_encoder` từng trả `h264_qsv`/`hevc_qsv`/`h264_amf`/`hevc_amf`; `ff._venc_args` chỉ hiểu `*_nvenc`; 4 tên đó rơi âm thầm về `libx264` | **Ẩn hôm nay** (máy có NVENC nên đường QSV/AMF chưa từng chạy) — thức khi NVENC vắng | Có, nhưng chỉ khi driver NVENC lỗi/host chỉ có iGPU — đúng lúc có sự cố khác |
| J | HEVC → H.264 âm thầm | Kết quả job khai `codec: "hevc"` | Đường CPU cũ trả thẳng chuỗi `"libx264"` cho MỌI codec (bỏ tham số `codec`); `jobs.py` ghi `"codec": codec.value` (yêu cầu của khách), không phải codec thật | Ẩn (chỉ lộ khi so khớp file thật) | **Có** — khách xin HEVC, nhận H.264, API vẫn báo `codec:"hevc"` |
| K | Smooth motion = RIFE | "RIFE 5-10x" (`13_FINAL_REPORT.md:60`) | `minterpolate` CPU thật sự chạy; RIFE chỉ là `# TODO` chết, không binary, không vendor | Lộ nhẹ — tốc độ smooth-motion chậm hơn tài liệu hứa | Có, gián tiếp (thời gian xử lý) |
| L | Rò rỉ khi hết giờ cứng | (không nằm trong A–L gốc, phát hiện mới) | `job_runner.py:641-672` `_het_gio` gọi `os._exit(3)` khi vượt `RUNTIME_LIMIT_S` (2h) ⇒ bỏ qua `finally`, `jobs.py` `shutil.rmtree(tmp)` không chạy | **Ẩn cho tới khi job vượt 2h** | Không trực tiếp; rác đĩa + tiến trình mồ côi giữ GPU |
| M | Không xác minh đầu ra | (không nằm trong A–L gốc, phát hiện mới) | Thành công chỉ dựa `os.path.isfile()`; không kiểm khung/thời lượng/codec so với hứa — cộng ISSUE H vô dụng ⇒ đầu ra hỏng-mà-khác-rỗng vẫn `SUCCEEDED` | Ẩn cho tới khi encode hỏng theo cách để lại file khác-rỗng | Có thể — khách nhận file hỏng mà vẫn bị trừ tiền |

## Ghi chú về đường "ẩn"

Không khuyết tật nào trong 13 khuyết tật làm job đỏ hàng loạt — đó là lý do
chúng sống sót qua một đợt "hoàn thành 100%" mà không ai phát hiện: ISSUE H bị
`jobs.py` (bản cũ) chỉ log cảnh báo thay vì raise; ISSUE G/D không có test nào
chạm tới; ISSUE I/J ngủ yên vì máy production có NVENC. Bài học đo lường
tương ứng: `docs/BAY_TRONG_CONG_CHAT_LUONG.md` — một cổng chất lượng luôn-fail
mà không đỏ job là tệ hơn không có cổng, vì nó tạo cảm giác an toàn giả.

## Trạng thái SAU sửa (đối chiếu `git diff main -- apps/upscalevideo/`)

Tất cả 13 khuyết tật đã có sửa tại chỗ trong `apps/upscalevideo/*.py` (khoá bởi
`tests/test_4904_upscale_correction.py`), TRỪ:
- **K (RIFE)** — vẫn `minterpolate` CPU; RIFE bị hoãn có chủ đích (`07_CORRECTION_PLAN.md`).
- **L (os._exit)** — nằm ở `platform_core/job_runner.py`, ngoài phạm vi app này; vẫn rò rỉ.
- **I (QSV/AMF thật)** — không dựng đường QSV/AMF thật; chốt chỉ hỗ trợ NVENC/CPU
  (quyết định sản phẩm, không phải nợ kỹ thuật).
