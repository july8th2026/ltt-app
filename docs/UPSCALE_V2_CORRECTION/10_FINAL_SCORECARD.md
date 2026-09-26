# 10 — FINAL SCORECARD

> Thang /100 theo mandate. **Before** = điểm bản cũ đã tự chấm trong
> `docs/UPSCALE_V2/13_FINAL_REPORT.md` (quy đổi từ thang /10 → /100), giữ lại
> để đối chiếu — bản thân các điểm Before phần lớn cũng là tự chấm, không phải
> đo. **After**: chỉ điền khi có bằng chứng (test/mã đọc được); mọi hàng về
> hiệu năng runtime ghi **CHƯA ĐO** — GPU máy A đang chạy job production thật,
> chưa benchmark trước/sau nào chạy được trong đợt sửa này. Không đoán số.

| Hạng mục | Before (tự chấm cũ) | After | Bằng chứng After |
|---|---|---|---|
| Core pipeline | 90/100 (`13_FINAL_REPORT.md` "Architecture 9/10") | 90/100 | Pipeline không đổi cấu trúc, chỉ sửa nội dung từng hàm — `09_FINAL_ARCHITECTURE.md` |
| GPU scheduling | 90/100 (khai "Shared GPU, 12x concurrent fast") | **40/100** | Đồng thời thật = 1, không đổi so với trước (chưa từng là >1) — `02_GPU_SCHEDULER_TRUTH.md`. Điểm hạ vì lời khai cũ sai hoàn toàn, không phải vì cơ chế tệ đi; cơ chế "1 job 1 GPU" là AN TOÀN (docstring `models.py:1028-1031`), chỉ SAI ở chỗ bị khai là 12 |
| GPU safety | CHƯA ĐO (không có điểm riêng ở bản cũ) | 70/100 | Warmup nay ghim đúng card (`gpu_index`+`env`) — `07_CORRECTION_PLAN.md` mục D/E/F. Chưa đo thực nghiệm trên máy có iGPU (`CHƯA ĐO`) |
| VRAM policy | CHƯA ĐO | 60/100 | `est_alloc` khớp `manifest.py` (không còn tự mâu thuẫn) — `tests/test_4904_upscale_correction.py` mục G. Chưa đo VRAM thật per-process (chỉ là hằng số cố định từ benchmark cũ, không tái đo) |
| Autotune | CHƯA ĐO | 65/100 | 3 chỗ tự mâu thuẫn (750 vs 1000 MB, dải Quality vượt sàn 95 MB, chú thích tile ngược mã) đã sửa và khoá bằng test — `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE C |
| Fast perf | 90/100 (khai "9/10") | **CHƯA ĐO** | Không có benchmark trước/sau nào chạy trong đợt sửa; GPU đang bận việc thật |
| Quality perf | CHƯA ĐO | **CHƯA ĐO** | như trên |
| Smooth Motion | 90/100 (khai "RIFE 5-10x") | **30/100** | RIFE KHÔNG tồn tại (chỉ `# TODO` chết), vẫn `minterpolate` CPU — `07_CORRECTION_PLAN.md` mục K. Điểm hạ vì lời khai sai, cơ chế bản thân không đổi |
| Disk I/O | CHƯA ĐO | CHƯA ĐO | Tỉ lệ I/O so với tầng SR chưa từng được đo, kể cả bản cũ — `00_CURRENT_TRUTH.md` "PNG I/O" |
| Encoder | CHƯA ĐO | 80/100 | Bất biến producer↔consumer khoá bằng test AST/behavior (`test_resolve_encoder_luon_tra_ten_ma_venc_args_hieu`, `test_venc_args_nem_valueerror_cho_encoder_la`); HEVC→CPU giờ ra `libx265` đúng, không còn giả `libx264` — `05_ENCODER_TRUTH.md` |
| Resume | 90/100 (khai "9/10 Full stage recovery") | **10/100** | Resume KHÔNG tồn tại, chưa từng tồn tại. 10 điểm cho "sổ tiến độ" (ghi được, dọn được) — không phải resume — `03_CHECKPOINT_TRUTH.md` |
| Reliability | 90/100 (khai "9/10") | 55/100 | Rò rỉ sổ tiến độ đã vá (cleanup + TTL sweep); rò rỉ temp dir + tiến trình mồ côi khi `os._exit` **CHƯA VÁ** (ngoài phạm vi app) — `09_FINAL_ARCHITECTURE.md` |
| Quality validation | CHƯA ĐO (bản cũ khai "COMPLETE" mâu thuẫn nội bộ) | 70/100 | Cổng kỹ thuật mới kiểm được khung/thời lượng/codec/audio, khoá bằng 6 test — `04_QUALITY_GATE_TRUTH.md`. Không chấm 100 vì chưa đo tỉ lệ bắt lỗi thật trên job production |
| AI model quality | 80/100 (khai "8/10") | **CHƯA ĐO** | PSNR/SSIM ở `06_MODEL_BENCHMARK.md` không có dataset/script dẫn nguồn kiểm chứng lại được; đo thật thuộc `apps/qualitylab`, không đổi trong đợt sửa này |
| Observability | CHƯA ĐO | 60/100 | `res["codec"]` vs `res["codec_requested"]` cho phép đối soát fallback; `quality_warning`/`tech_gate` trong kết quả job — `05_ENCODER_TRUTH.md`, `04_QUALITY_GATE_TRUTH.md` |
| Testing | CHƯA ĐO | 75/100 | `tests/test_4904_upscale_correction.py` — 24 test khoá 8 trong 13 khuyết tật bằng AST/behavior, không phải chạy GPU/ffmpeg thật (mock hoá) |
| Maintainability | CHƯA ĐO | 65/100 | Docstring mỗi tệp giờ nói rõ CÁI GÌ KHÔNG hoạt động (checkpoint, encoder, quality gate) thay vì chỉ nói cái hoạt động — giảm rủi ro lặp lại lời khai sai |
| **Overall** | **~88/100** (trung bình các mục tự chấm cũ) | **CHƯA CHẤM MỘT SỐ DUY NHẤT** | Trộn hàng CHƯA ĐO với hàng có bằng chứng vào một con số overall là đúng lỗi "hai trạng thái gộp thành một giá trị" (`MEMORY.md`) — xem ghi chú dưới |

## Vì sao không có một con số "Overall" duy nhất

Ít nhất 5/17 hàng là `CHƯA ĐO` (Fast perf, Quality perf, Disk I/O, AI model
quality, và một phần VRAM policy/Autotune). Tính trung bình các hàng còn lại
rồi gọi nó "Overall" sẽ ẩn đúng bên A: 0 (không có) hay 1: không đo được?
Một scorecard trung thực có lỗ hổng còn tốt hơn một scorecard đầy đủ nhưng
bịa — đúng tiêu chí trong brief.
