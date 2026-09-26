# 09 — FINAL ARCHITECTURE (sự thật, sau sửa)

> Đường ống thật của `apps/upscalevideo/jobs.py::handle`, từng chặng, đánh dấu
> nghẽn tài nguyên. Không có số hiệu năng nào trong tệp này — mọi thời gian
> chặng là **CHƯA ĐO** (GPU máy A đang chạy job production thật lúc viết).

## Pipeline, chặng theo chặng

| # | Chặng | Tài nguyên | Ghi chú |
|---|---|---|---|
| 1 | Tải video R2/local → tệp tạm | **IO** (mạng/đĩa) | `storage.open` stream 1 MB/lượt, kiểm `cancel_check` mỗi khối |
| 2 | `ff.probe_video` (ffprobe) | **CPU** (nhẹ) | Đọc w/h/fps/duration/audio/vfr |
| 3 | Giữ chỗ credit (`_dam_bao_giu_cho`) | DB | Theo `duration` thật, không theo ước lượng trước |
| 4 | `_guard_disk` | tính toán | Chặn trước khi tách frame nếu đĩa tạm không đủ (ước lượng ×3 × 0.5 × 1.3 trên diện tích đích) |
| 5 | (tuỳ chọn) `ff.stabilize_video` | **CPU** (libvidstab, 2-pass) | Ghi checkpoint `stabilize_completed` |
| 6 | `ff.extract_frames` | **CPU** (ffmpeg) + **IO** (ghi PNG) | KHÔNG chunk — cả video ra PNG một lượt; `smooth_motion` nhân đôi số khung qua `minterpolate` (CPU, không phải RIFE — xem `07_CORRECTION_PLAN.md` mục K) |
| 7 | `autotune.pick` | tính toán, đọc `nvidia-smi` | Chọn tile/threads theo VRAM **sống** của ĐÚNG GPU đã lease (`ctx.gpu_uuid`) |
| 8 | `engine.run_upscale` (đơn hoặc `_upscale_batched`, chunk `_BATCH_SIZE=360`) | **GPU** (NCNN Vulkan, độc chiếm) | Warmup một lần/model/vòng đời worker trước job thật (không giữ VRAM giữa hai tiến trình — xem `03`); mỗi batch ghi checkpoint `upscale_batch_NNN` |
| 9 | `ff.encode_full`/`encode_segment` + `concat_and_mux` | **GPU** (NVENC) hoặc **CPU** (libx264/libx265) | Encoder chọn bởi `_resolve_encoder` — xem `05_ENCODER_TRUTH.md` |
| 10 | Cổng KỸ THUẬT (`quality_gate.kiem_tra_dau_ra`) | **CPU** (ffprobe, nhẹ) | Trên tệp LOCAL, TRƯỚC upload — xem `04_QUALITY_GATE_TRUTH.md` |
| 11 | Upload R2 (`storage.put`) | **IO** (mạng) | Chỉ chạy nếu cổng kỹ thuật `ok=True` |
| 12 | Checkpoint `output_uploaded` + dọn `tmp` + `cleanup_job_checkpoints` | IO (đĩa) | Trong `finally` |

Chặng 6 (tách frame, IO nặng PNG ×N khung) và chặng 8 (upscale GPU) là hai nơi
duy nhất `00_CURRENT_TRUTH.md` gọi là "PNG I/O — chưa phải bottleneck đã đo":
tách frame KHÔNG chunk trong khi upscale CÓ chunk (`_BATCH_SIZE=360`, cố ý chặn
đỉnh đĩa của PNG đã ×4 diện tích). Tỉ lệ thời gian I/O so với tầng SR là
**CHƯA ĐO** — không tối ưu trước khi đo.

## Hai rò rỉ CÒN LẠI đã biết (chưa vá trong đợt sửa này)

1. **Hard-timeout `os._exit` bỏ qua cleanup — `platform_core/job_runner.py:641-672`.**
   Khi job vượt `RUNTIME_LIMIT_S` (2 giờ cho làn `gpu`/`ffmpeg`,
   `job_runner.py:114`), `_het_gio` ghi trạng thái job vào DB rồi gọi
   `os._exit(3)` để giết cả tiến trình worker (không có cách đáng tin để dừng
   code C/CUDA đang giữ GIL từ Python). `os._exit` bỏ qua mọi `finally` ⇒
   `jobs.py`'s `shutil.rmtree(tmp)` và `checkpoint.cleanup_job_checkpoints`
   **không chạy**. Giảm nhẹ một phần: `checkpoint.don_so_cu(ttl_ngay=7)` dọn sổ
   tiến độ mồ côi, nhưng KHÔNG dọn thư mục temp khung/segment (có thể tới vài
   GB) hay tiến trình con.
2. **Tiến trình engine mồ côi.** Cùng nguyên nhân (1): `realesrgan-ncnn-vulkan.exe`
   (`engine.py:127`, `subprocess.Popen`) và `ffmpeg.exe` (`ff.py:41`) là tiến
   trình CON của worker bị `os._exit`. Trên Windows, không có `atexit`, không
   Job Object nào ràng buộc vòng đời con vào cha (đã grep, không có) ⇒ tiến
   trình con có thể tiếp tục chạy mồ côi, **giữ GPU** cho tới khi tự kết thúc
   hoặc bị dọn tay. Huỷ **hợp tác** (khách bấm huỷ, `cancel_check`) thì AN
   TOÀN: `engine.py:118-141` và `ff.py:36-58` đều poll rồi `kill()+wait()` chủ
   động — chỉ đường hết-giờ-CỨNG mới rò.

Cả hai nằm ở `platform_core/job_runner.py`, dùng chung cho mọi app GPU/ffmpeg
trên nền tảng — sửa tại đó ngoài phạm vi app `upscalevideo`
(xem `07_CORRECTION_PLAN.md` mục L).

## Không còn tồn tại (đã xoá khỏi kiến trúc, không phải "chưa tới lượt")

- Cổng PSNR/SSIM/VMAF chạy trên job khách (ISSUE H) — chuyển hẳn sang
  `apps/qualitylab` ngoại tuyến.
- `_model_cache` chết ở `engine.py` (ISSUE D).
- Đường QSV/AMF "hỗ trợ" nhưng rơi âm thầm (ISSUE I) — chốt chỉ NVENC/CPU.
