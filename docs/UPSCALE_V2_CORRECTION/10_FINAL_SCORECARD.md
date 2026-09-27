# 10 — FINAL SCORECARD

> Thang /100 theo mandate. **Before** = điểm bản cũ đã tự chấm trong
> `docs/UPSCALE_V2/13_FINAL_REPORT.md` (quy đổi từ thang /10 → /100), giữ lại
> để đối chiếu — bản thân các điểm Before phần lớn cũng là tự chấm, không phải
> đo. **After**: chỉ điền khi có bằng chứng (test/mã đọc được/benchmark thật).
> Cập nhật 2026-09-27: cửa sổ GPU đã mở, benchmark thật đã chạy (§F–K của
> `08_BENCHMARK_RESULTS.md`) — các hàng hiệu năng nay có dữ liệu, nhưng phạm vi
> **hẹp** (một nguồn 836×576, không stabilize/smooth_motion — ghi rõ ở cột
> Bằng chứng). Hàng nào chưa có phép đo thật vẫn ghi `CHƯA ĐO`. Không đoán số.

| Hạng mục | Before (tự chấm cũ) | After | Bằng chứng After |
|---|---|---|---|
| Core pipeline | 90/100 (`13_FINAL_REPORT.md` "Architecture 9/10") | 90/100 | Pipeline không đổi cấu trúc, chỉ sửa nội dung từng hàm — `09_FINAL_ARCHITECTURE.md` |
| GPU scheduling | 90/100 (khai "Shared GPU, 12x concurrent fast") | **40/100** | Đồng thời thật = 1, không đổi so với trước (chưa từng là >1) — `02_GPU_SCHEDULER_TRUTH.md`. Điểm hạ vì lời khai cũ sai hoàn toàn, không phải vì cơ chế tệ đi; cơ chế "1 job 1 GPU" là AN TOÀN (docstring `models.py:1028-1031`), chỉ SAI ở chỗ bị khai là 12 |
| GPU safety | CHƯA ĐO (không có điểm riêng ở bản cũ) | 70/100 | Warmup nay ghim đúng card (`gpu_index`+`env`) — `07_CORRECTION_PLAN.md` mục D/E/F. Chưa đo thực nghiệm trên máy có iGPU (`CHƯA ĐO`) |
| VRAM policy | CHƯA ĐO | 65/100 | `est_alloc` khớp `manifest.py` (không còn tự mâu thuẫn) — `tests/test_4904_upscale_correction.py` mục G. ĐÃ ĐO đỉnh VRAM thật theo cấu hình: Fast 1080/1440/2160 = 2 378/6 389/4 771 MiB, Quality 1080/2160 ≈ 13 267/13 266 MiB (`08_BENCHMARK_RESULTS.md` §G/§H/§I) — nhưng cột VRAM đỉnh của Fast **không đơn điệu**, tài liệu tự cảnh báo đừng dùng để kết luận xu hướng; VRAM per-process theo tile: 1 665→13 135 MiB (§J/§K) |
| Autotune | CHƯA ĐO | 70/100 | 3 chỗ tự mâu thuẫn (750 vs 1000 MB, dải Quality vượt sàn 95 MB, chú thích tile ngược mã) đã sửa và khoá bằng test — `00_CURRENT_TRUTH.md` ISSUE C. Quyết định tile cuối (Fast giữ nguyên do 2,4% nằm trong nhiễu; Quality giữ 512 dù đo được 256 nhanh hơn 8,7% vì đổi chất lượng đo được) — `08_BENCHMARK_RESULTS.md` §J, §K; `autotune.py:127-148` |
| Fast perf | 90/100 (khai "9/10") | **ĐÃ ĐO — không chấm điểm tuyệt đối** | Baseline thật: 1080/1440/2160 = 321,4/345,4/330,7 s, 9,97/9,28/9,69 khung·s⁻¹ (`08_BENCHMARK_RESULTS.md` §G). Không có before/after cùng điều kiện để so sánh cải thiện — chỉ có SỐ HIỆN TẠI, không có % thay đổi (mục 16 của `13_TRA_LOI_27_CAU.md`). Phạm vi: 1 nguồn 836×576, không stabilize/smooth_motion |
| Quality perf | CHƯA ĐO | **ĐÃ ĐO — không chấm điểm tuyệt đối** | Baseline thật 1080: 472,2 s, 0,64 khung·s⁻¹ — chậm hơn Fast **15,7×**, tính tiền gấp **2,5×** (`08_BENCHMARK_RESULTS.md` §H). 2160 gần như bằng 1080 (471,4 s, dự đoán ĐÚNG: đích không tốn thêm thời gian GPU vì `ENGINE_SCALE=4` luôn upscale từ NGUỒN — §I). Cùng lý do như Fast perf: không có % cải thiện vì không tối ưu tốc độ |
| Smooth Motion | 90/100 (khai "RIFE 5-10x") | **30/100** | RIFE KHÔNG tồn tại (chỉ `# TODO` chết), vẫn `minterpolate` CPU — `07_CORRECTION_PLAN.md` mục K. Điểm hạ vì lời khai sai, cơ chế bản thân không đổi |
| Disk I/O | CHƯA ĐO | 85/100 | ĐÃ ĐO: tầng SR+encode chiếm 96,7% tổng thời gian, tách khung PNG chỉ 3,1% (`08_BENCHMARK_RESULTS.md` §F) ⇒ PNG I/O KHÔNG phải bottleneck, bác lời khai cũ "2-3× nhanh hơn nếu viết lại". Không chấm 100 vì phạm vi hẹp: 1 cấu hình (Fast, 836×576, không stabilize/smooth_motion) — với smooth_motion tỉ lệ CHƯA ĐO |
| Encoder | CHƯA ĐO | 80/100 | Bất biến producer↔consumer khoá bằng test AST/behavior (`test_resolve_encoder_luon_tra_ten_ma_venc_args_hieu`, `test_venc_args_nem_valueerror_cho_encoder_la`); HEVC→CPU giờ ra `libx265` đúng, không còn giả `libx264` — `05_ENCODER_TRUTH.md` |
| Resume | 90/100 (khai "9/10 Full stage recovery") | **10/100** | Resume KHÔNG tồn tại, chưa từng tồn tại. 10 điểm cho "sổ tiến độ" (ghi được, dọn được) — không phải resume — `03_CHECKPOINT_TRUTH.md` |
| Reliability | 90/100 (khai "9/10") | 65/100 | Rò rỉ sổ tiến độ đã vá (cleanup + TTL sweep). Rò rỉ hết-giờ có HAI phần: tiến trình engine mồ côi **ĐÃ VÁ 27/09** (`fbdc7a3c` — `taskkill /T /F` cây con trước `os._exit`, 4 test tiêm lỗi, 353 passed); thư mục temp cỡ GB **VẪN CHƯA VÁ**, cố ý để lại cho một sweeper định kỳ — `09_FINAL_ARCHITECTURE.md` mục 1/2 |
| Quality validation | CHƯA ĐO (bản cũ khai "COMPLETE" mâu thuẫn nội bộ) | 70/100 | Cổng kỹ thuật mới kiểm được khung/thời lượng/codec/audio, khoá bằng 6 test — `04_QUALITY_GATE_TRUTH.md`. Không chấm 100 vì chưa đo tỉ lệ bắt lỗi thật trên job production |
| AI model quality | 80/100 (khai "8/10") | **CHƯA ĐO** | PSNR/SSIM ở `06_MODEL_BENCHMARK.md` không có dataset/script dẫn nguồn kiểm chứng lại được; đo thật thuộc `apps/qualitylab`, không đổi trong đợt sửa này. (Phép so PSNR/SSIM tile 256 vs 512 ở §K đo SAI KHÁC giữa hai cấu hình engine, không đo chất lượng mô hình so với ảnh gốc — không lấp được hàng này) |
| Observability | CHƯA ĐO | 60/100 | `res["codec"]` vs `res["codec_requested"]` cho phép đối soát fallback; `quality_warning`/`tech_gate` trong kết quả job — `05_ENCODER_TRUTH.md`, `04_QUALITY_GATE_TRUTH.md` |
| Testing | CHƯA ĐO | 75/100 | ≥ 85 hàm test chạm app (`test_4904`=45 + `test_4905`=5 + `test_82`=19 + `test_171`=7 + `test_116`=7 + `test_4906`=2, đếm tĩnh bằng grep — số ca pytest thật cao hơn vì `test_4904` có 5 chỗ `parametrize`, chưa chạy pytest trong phiên viết tài liệu). Khoá 8+/13 khuyết tật bằng AST/behavior, nghiệm thu bằng tiêm lỗi (11 lần hoàn nguyên, mỗi lần làm ĐÚNG phép kiểm đỏ) — không phải chạy GPU/ffmpeg thật trên phần lớn test (mock hoá), trừ `test_4905` chạy trên tệp thật qua `testsrc` |
| Maintainability | CHƯA ĐO | 65/100 | Docstring mỗi tệp giờ nói rõ CÁI GÌ KHÔNG hoạt động (checkpoint, encoder, quality gate) thay vì chỉ nói cái hoạt động — giảm rủi ro lặp lại lời khai sai |
| **Overall** | **~88/100** (trung bình các mục tự chấm cũ) | **CHƯA CHẤM MỘT SỐ DUY NHẤT** | Trộn hàng CHƯA ĐO với hàng có bằng chứng vào một con số overall là đúng lỗi "hai trạng thái gộp thành một giá trị" (`MEMORY.md`) — xem ghi chú dưới |

## Vì sao không có một con số "Overall" duy nhất

Ít nhất 3/17 hàng vẫn `CHƯA ĐO` hoàn toàn (AI model quality, và một phần VRAM
policy/Autotune vẫn thiếu đo VRAM per-process thật ngoài mẫu benchmark hẹp);
hai hàng nữa (Fast perf, Quality perf) nay **có số đo thật** nhưng cố ý không
được gán điểm /100 vì mandate hỏi "cải thiện bao nhiêu %" chứ không hỏi "chạy
nhanh hay chậm" — và câu trả lời trung thực cho "cải thiện %" là **không áp
dụng tối ưu tốc độ nào** (xem mục 16-17 của `13_TRA_LOI_27_CAU.md`). Tính
trung bình các hàng còn lại rồi gọi nó "Overall" sẽ ẩn đúng bên: 0 (không có)
hay 1: không đo được? Một scorecard trung thực có lỗ hổng còn tốt hơn một
scorecard đầy đủ nhưng bịa — đúng tiêu chí trong brief.

## ⭐ Mục tiêu ≥ 90/100 của mandate — KHÔNG THỂ khẳng định đạt được

Ba lý do, mỗi lý do đủ để tự nó chặn khẳng định:

1. **Không có một con số duy nhất để so với 90** — xem mục trên. "Đạt ≥90" là
   một phát biểu về MỘT con số; tài liệu này cố ý không tạo ra con số đó.
2. **Ít nhất 3 hàng vẫn `CHƯA ĐO`** (AI model quality hoàn toàn; VRAM
   policy/Autotune còn thiếu đo VRAM per-process thật ngoài mẫu hẹp đã có).
   Một hạng mục chưa đo không thể được tính là "đạt" — vắng mặt phép đo không
   được đọc thành đạt (`MEMORY.md`, `12_PLAN_TRIEN_KHAI.md` §5.3).
3. **Bốn hàng đang ở dưới 90** sau khi sửa lời khai: GPU scheduling 40/100,
   Smooth Motion 30/100, Resume 10/100, Reliability 65/100 — mỗi hàng này
   từng được bản cũ tự chấm 90/100 bằng lời khai sai; điểm sau khi đối chiếu
   với mã + runtime thấp hơn nhiều so với ngưỡng 90, và đây là những khuyết
   tật **có chủ đích không vá trong đợt này** (deferred, không phải bỏ sót) —
   xem điều kiện mở khoá ở `12_PLAN_TRIEN_KHAI.md` mục 3. (Reliability là
   ngoại lệ một phần: nửa "tiến trình mồ côi" đã vá 27/09 ngoài đợt sửa app
   này, ở `platform_core/`; nửa "temp dir" vẫn deferred như ba hàng kia.)

⇒ Đợt sửa này đạt được mục tiêu **trung thực hoá** scorecard (lời khai khớp
mã + runtime, mỗi con số có `tệp:dòng`/benchmark) — không đạt mục tiêu số học
≥90/100 của mandate, vì đó chưa từng là một mục tiêu có thể đạt bằng sửa lời
khai: nó đòi hỏi vá cả GPU scheduling thật, resume thật, và đo đủ AI model
quality — những việc bị DEFERRED có chủ đích trong đợt này.
