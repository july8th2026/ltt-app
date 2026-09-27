# 13 — TRẢ LỜI 27 CÂU HỎI CỦA MANDATE (§50)

> Lập 2026-09-27 · nhánh `claude/upscale-video-v2-correction-5fa61a`. Mỗi câu
> dưới đây trả lời **thẳng**, kèm bằng chứng (`tệp:dòng`, mục benchmark, hoặc
> commit). Nhãn bắt buộc trên mọi con số: **ĐÃ ĐO** / **ƯỚC LƯỢNG** / **CHƯA ĐO**.
> Nguồn gốc: `00_CURRENT_TRUTH.md` (13 khuyết tật A–M), `08_BENCHMARK_RESULTS.md`
> (mục F–K, các phép **ĐÃ ĐO** duy nhất của đợt sửa này), `12_PLAN_TRIEN_KHAI.md`.

---

## 1. Bugs mà bản cập nhật trước đã tạo ra

13 khuyết tật độc lập, mỗi cái có `tệp:dòng`, liệt kê A–M trong
`00_CURRENT_TRUTH.md`: (A) lời khai đồng thời GPU sai (4→12, sự thật là 1),
(B) đổi VRAM reservation tưởng mua throughput nhưng không, (C) 3 chú thích
autotune lệch nhau + 1 dải tự vượt sàn, (D) warmup không giữ được gì (tiến
trình thoát hẳn trước job thật), (E) warmup không ghim card trên máy có iGPU,
(F) import numpy/cv2 thừa, (G) checkpoint là ghi sổ chứ không phải resume (0
caller đọc), (H) cổng chất lượng PSNR/SSIM/VMAF luôn thất bại trên mọi job
khách, (I) encoder QSV/AMF rơi âm thầm về `libx264`, (J) HEVC trên CPU trả
H.264 mà vẫn khai "hevc", (K) smooth motion vẫn `minterpolate` CPU dù tài liệu
gợi ý RIFE, (L) `os._exit(3)` khi hết giờ bỏ qua `finally` ⇒ rò temp + tiến
trình mồ côi, (M) không xác minh nội dung đầu ra, chỉ `isfile()`.

## 2. Bugs nào là ÂM THẦM (không hiện lỗi, không hiện log rõ)

H (cổng chất lượng luôn fail nhưng job vẫn `SUCCEEDED`, chỉ gắn một
`quality_warning` mà khách/vận hành dễ bỏ qua), G (checkpoint ghi xong không
ai đọc — không có triệu chứng nào cho tới khi cần resume thật), J (trường
`codec` trong kết quả job nói dối — `{"codec":"hevc","encoder":"libx264"}`,
không exception nào bắn ra), D (warmup chạy "thành công" mỗi lần nhưng không
mua được gì), M (đầu ra hỏng mà khác rỗng vẫn `SUCCEEDED`) — `00_CURRENT_TRUTH.md`
ISSUE D/G/H/J/M.

## 3. Bugs nào có khả năng phá sản xuất (production-breaking)

Không cái nào đã **thực sự** phá sản xuất trong đợt trước (không có báo cáo sự
cố), nhưng ba cái mang **rủi ro thật**: (L) `os._exit` rò tiến trình
`realesrgan-ncnn-vulkan.exe` mồ côi giữ GPU — **đã chứng kiến tận mắt** một ca
thật ngày 26/09 (`12_PLAN_TRIEN_KHAI.md` mục 2, tiến trình mồ côi bị dọn có
rào chắn); (E) warmup có thể chạy sai card trên máy có iGPU — đúng lớp sự cố
`vulkan_device.py` đã từng vá một lần (commit `7cde3c9d`); (H) egress R2 +
RAM đọc toàn bộ MP4 trên **mọi** job khách là một khoản phí thật, không phải
lỗi logic đơn thuần. ISSUE L **vẫn CHƯA VÁ** (nằm ở `platform_core/job_runner.py`,
ngoài phạm vi app, việc của chủ khu khác — `12_PLAN_TRIEN_KHAI.md` mục 4).

## 4. Tối ưu giả đã bị gỡ

Bốn: warmup (`_warmup_model`, đo được KHÔNG lợi ích, XOÁ hẳn — commit
`9f05648d`); "resume" (chưa từng tồn tại, đổi khái niệm thành "sổ tiến độ",
không giả vờ resume nữa); cổng chất lượng PSNR/SSIM/VMAF giả (luôn fail, gọi
sai công cụ — bỏ, thay bằng cổng kỹ thuật thật); hỗ trợ QSV/AMF (khai hỗ trợ
nhưng cả 4 combo chết lúc chạy — bỏ khỏi `schemas.py` + `quality_gate.HO_CODEC`).
Nguồn: `12_PLAN_TRIEN_KHAI.md` mục 1 (Pha B), `07_CORRECTION_PLAN.md` mục D/E/F,
G, H, I/J.

## 5. Sự thật đồng thời GPU

**1** (không phải 4→12 như lời khai cũ). `UniqueConstraint("host","gpu_uuid")`
(`platform_core/models.py:1037`) khoá một GPU-một máy tối đa một `GpuLease`
sống; `gpu_lease.py:130-134,179` loại GPU đã có lease khỏi ứng viên **bất kể**
`need_mb`. Hạ `gpu_vram_mb.fast` chỉ đổi **sàn nhận một job**, không mua job
thứ hai — ĐÃ ĐO bằng đọc mã, khoá bằng test
`test_gpu_lease_unique_constraint_khoa_dong_thoi_ve_mot`. `00_CURRENT_TRUTH.md`
ISSUE A.

## 6. Chính sách VRAM cuối cùng

Giữ nguyên `gpu_vram_mb.fast = 1000` (khớp đỉnh đo được 848 MB + 152 MB an
toàn — `autotune.py:111-115`). Không đổi số, chỉ đổi **lời khai**: bỏ diễn
giải "giảm VRAM mua thêm throughput" (sai, vì `UniqueConstraint` không đổi).
`07_CORRECTION_PLAN.md` mục B.

## 7. Fast — tile/thread cuối cùng

`tile = 256` khi cạnh dài nguồn ≥ 1100px, else `384`; `threads = "4:4:4"`; tụt
về `tile=200, threads="2:2:2"` khi `budget < 1000` MB (`autotune.py:103-121`).
Tile sweep §J (836×576, 3 lượt, trung vị) đo tile 200/256/384 lệch **2,4 %**
toàn dải — nằm trong nhiễu (một lượt tile 256 lệch tới 33,09 s) ⇒ **giữ
nguyên**, không đổi mặc định. ĐÃ ĐO — `08_BENCHMARK_RESULTS.md` mục J.

## 8. Quality — tile/thread cuối cùng

`tile ∈ {512,448,384,320,256}` theo dải `budget`, mặc định **512** khi
`budget ≥ 10524` MB; `threads = "1:2:2"` luôn (`autotune.py:149-178`). Tile
sweep §K đo tile 256 **nhanh hơn 8,7 %** và tốn ít VRAM hơn 64 % — nhưng đầu ra
**khác nhau đo được** (PSNR 45,15–46,46 dB, SSIM 0,9898–0,9922, 0/12 khung
giống hệt bit). Chủ dự án chốt 27/09: **GIỮ tile 512**, ưu tiên chất lượng
trong chính preset tên "Quality" — đánh đổi tốc độ ở đây tự mâu thuẫn với lý
do tồn tại của preset. Khoá bằng `tests/test_4906_upscale_chot_tile_quality.py`.
ĐÃ ĐO — `08_BENCHMARK_RESULTS.md` mục K, `autotune.py:127-148`.

## 9. Warmup — cuối cùng

**Đã XOÁ** khỏi `engine.py` (commit `9f05648d`). Lý do kép: (a) lập luận kiến
trúc — `subprocess.run` chờ tiến trình con thoát hẳn, job thật spawn `Popen`
mới, model không thể còn trong VRAM; (b) ĐO ĐƯỢC không lợi ích — xen kẽ
on/off/on/off, n=13/nhánh, mọi chênh lệch dưới 1 % và **đổi dấu** giữa các đại
lượng (ttff/tổng nghiêng "on", upscale nghiêng "off") — dấu hiệu của nhiễu,
không phải hiệu ứng thật. `08_BENCHMARK_RESULTS.md` mục A.

## 10. Checkpoint — cuối cùng

Vẫn là **sổ tiến độ** (progress ledger), không phải resume. Đã vá rò rỉ vĩnh
viễn: `cleanup_job_checkpoints` nay được gọi trong `finally` của `jobs.handle`
khi job thành công; thêm `don_so_cu(ttl_ngay=7)` làm lưới thứ hai cho đường rò
`os._exit`. `07_CORRECTION_PLAN.md` mục G ("DONE khung sự thật, DEFERRED resume
thật").

## 11. Resume có thật không

**Không.** Chưa từng tồn tại, và vẫn chưa được xây trong đợt sửa này (quyết
định DEFERRED có chủ đích). Điều kiện mở khoá: (1) workspace **bền** thay
`tempfile.mkdtemp()` bị `rmtree`; (2) dấu tay (fingerprint tham số + model +
phiên bản pipeline) để tái dùng an toàn — thiếu dấu tay mà tái dùng chặng cũ
là giao hàng sai. Cả hai **chưa xây**. `07_CORRECTION_PLAN.md` mục G,
`03_CHECKPOINT_TRUTH.md`.

## 12. Cổng chất lượng — cuối cùng

Bỏ hẳn cổng PSNR/SSIM/VMAF cũ (gọi sai công cụ `ffprobe`, không tham chiếu,
truyền khoá R2 như đường dẫn local, PIL không đọc được MP4 — luôn fail).
Thay bằng **cổng kỹ thuật** chạy trên tệp **local trước khi upload**
(`quality_gate.kiem_tra_dau_ra`, `quality_gate.py:79-`): tồn tại + kích thước
tối thiểu (`MIN_BYTES=10KB`), mở được, đúng khung (dung sai `±2px`, do
`scale=-2:H` làm tròn chẵn), đúng họ codec (`HO_CODEC` — bắt ca "xin HEVC,
nhận H.264"), đúng thời lượng (dung sai 5 % hoặc ≥1,0 s), có audio nếu yêu
cầu (chỉ CẢNH BÁO, không đánh đỏ). Lỗi khung/thời lượng/codec ⇒ job **FAIL
thật** (`jobs.py:547` `raise RuntimeError`). Kill switch
`LTT_UPSCALE_TECH_GATE=0` (`quality_gate.py:71-76`). Chất lượng **mô hình**
(PSNR/VMAF thật) không đổi, vẫn ở `apps/qualitylab` ngoại tuyến.
`07_CORRECTION_PLAN.md` mục H, `04_QUALITY_GATE_TRUTH.md`.

## 13. Smooth motion — cuối cùng

Không đổi cơ chế: vẫn `minterpolate` (CPU), nhập trong cùng lệnh ffmpeg tách
khung (`ff.py:141-143`). RIFE **vẫn KHÔNG tồn tại** — chỉ còn docstring + một
`# TODO` chết, đã dọn lời khai để không còn ngụ ý RIFE đang chạy. Điều kiện mở
khoá RIFE: có binary sạch + giấy phép + đo được lợi ích so với `minterpolate`
— chưa có cái nào. `12_PLAN_TRIEN_KHAI.md` mục 3, `00_CURRENT_TRUTH.md` ISSUE K.

## 14. Encoder fallback — cuối cùng

`_venc_args` nay **ném `ValueError`** cho tên encoder nó không biết thay vì
rơi âm thầm về `libx264`. Đường CPU tôn trọng `codec` khách xin qua map
`ENCODER_CPU` (H.264→`libx264`, HEVC→`libx265`) thay vì luôn `libx264`. QSV/AMF
bị **bỏ hẳn** khỏi `schemas.py` và `quality_gate.HO_CODEC` — đã bác bằng đo:
`ffmpeg -encoders` liệt kê đủ 4 combo QSV/AMF nhưng **cả bốn chết lúc chạy**
trên máy production này (đo 2026-09-26). `07_CORRECTION_PLAN.md` mục I/J.

## 15. HEVC có đúng bây giờ không

**Đúng.** Đường CPU giờ mã hoá thật bằng `libx265` khi khách xin HEVC (không
còn âm thầm trả H.264). Kết quả job tách `codec` (codec **thật** của luồng,
qua `quality_gate.HO_CODEC.get(encoder, codec.value)`) khỏi `codec_requested`
(ý khách xin) — `jobs.py:575-581`, để API/UI đối soát được khi có fallback.
Cổng kỹ thuật bắt lệch codec runtime tại chỗ (mục 12).

## 16. Fast — cải thiện tốc độ bao nhiêu %

**Không có con số cải thiện — không áp dụng tối ưu tốc độ trước/sau nào cho
Fast.** Ba quyết định của đợt đo đều là "KHÔNG LÀM GÌ", có số đứng sau:
- PNG I/O: tầng SR chiếm **96,7 %** tổng thời gian, tách khung chỉ **3,1 %**
  (§F) ⇒ xoá sạch I/O cũng chỉ lời tối đa **3,3 %** — không đáng viết lại
  đường ống đang phục vụ khách. Bác thẳng lời khai cũ "2-3× nhanh hơn".
- Warmup: xoá vì đo được KHÔNG lợi ích (mục 9), không phải vì tăng tốc.
- Fast tile sweep: biên độ toàn dải chỉ **2,4 %**, trong nhiễu (mục 7) ⇒ giữ
  nguyên tile mặc định, không lấy khoản này.
⇒ Runtime Fast trước/sau đợt sửa **không đổi theo chủ đích**; benchmark chỉ
đo được baseline hiện tại (§G): 1080 = 321,4 s / 9,97 khung·s⁻¹ (v3, 836×576,
3205 khung).

## 17. Quality — cải thiện tốc độ bao nhiêu %

**Cũng không có con số cải thiện đã ÁP DỤNG.** Tile sweep Quality (§K) đo
được tile 256 nhanh hơn tile 512 mặc định **8,7 %** — nhưng đây là một khoản
**BỊ TỪ CHỐI**, không phải một khoản đã lấy: đầu ra khác nhau đo được (PSNR
~46 dB, SSIM ~0,990, 0/12 khung giống bit), và đánh đổi tốc độ lấy chất lượng
bên trong chính preset "Quality" tự mâu thuẫn với lý do tồn tại của nó. Chủ
dự án chốt giữ tile 512 (mục 8). ⇒ **0 %** cải thiện tốc độ được đưa vào sản
phẩm cho Quality; con số 8,7 % chỉ tồn tại như một lựa chọn đã cân nhắc và từ
chối, ghi lại để nếu sau này đổi ý thì có sẵn số + điều kiện (mục K.4 của
`08_BENCHMARK_RESULTS.md`).

## 18. GPU utilization

ĐÃ ĐO, theo từng cấu hình cụ thể (không phải một con số chung):
Fast × 1080/1440/2160 = 83,4 % / 86,1 % / 83,3 % (trung bình lấy mẫu, §G);
Quality × 1080/2160 = 98,0 % / 98,1 % (bão hoà, §H/§I); tile sweep Fast
74,4–90,6 % theo tile (§J); tile sweep Quality 96,6–97,2 % theo tile (§K).
Phạm vi: một nguồn 836×576 (v3), không stabilize/smooth_motion.

## 19. CPU utilization

Chỉ có **giây CPU** cho các lượt cụ thể, không có % CPU tổng quát cho toàn hệ
thống. Warmup on/off: ~10,4 giây CPU trung vị/lượt, n=13 (§A, đã sửa lỗi cộng
dồn — mục lịch sử "Lượt 2" cùng bảng). Phân rã pha §F: `cpu_giay_process_tree`
= 159,9 s trên toàn bộ lượt chạy 346,67 s tường (~46 % giây-CPU/giây-tường,
nhưng đây là quy trình một tiến trình chính + con, không phải % lõi CPU máy).
CPU% theo % lõi máy: **CHƯA ĐO** — bộ đo chỉ lấy `cpu_giay_process_tree` tích
luỹ, không lấy mẫu % core theo thời gian thực (`08_BENCHMARK_RESULTS.md` mục
E.2).

## 20. Peak VRAM

ĐÃ ĐO theo cấu hình: Fast × 1080/1440/2160 = 2 378 / 6 389 / 4 771 MiB (§G —
⚠️ tài liệu tự cảnh báo cột này KHÔNG đơn điệu, đừng dùng để kết luận xu
hướng); Quality × 1080/2160 ≈ 13 267 / 13 266 MiB (§H/§I, bão hoà, rất tất
định — lệch <0,1 %); tile sweep Fast 1 665→2 136 MiB theo tile 200→384 (§J,
đơn điệu, tile nhỏ tiết kiệm 22 % VRAM — nhưng VRAM không phải tài nguyên
đang thiếu vì đồng thời GPU = 1); tile sweep Quality 4 761→13 135 MiB theo
tile 256→512 (§K).

## 21. Disk I/O

ĐÃ ĐO — nhưng phạm vi hẹp: **một** cấu hình (Fast, nguồn 836×576/3205 khung,
đích 1080, không stabilize/smooth_motion). Tầng SR+encode chiếm **96,7 %**
tổng thời gian; `frame_extraction` (tách PNG) chỉ **3,1 %**; concat/upload/
probe/source_copy cộng lại <0,2 %. ⇒ PNG I/O **không phải bottleneck** — bác
lời khai cũ "2-3× nhanh hơn nếu viết lại đường PNG" (`04_BOTTLENECKS.md:103`
của tài liệu cũ). Với `smooth_motion` bật, tỉ lệ I/O **có thể khác** (nhân số
khung nguồn lên) — CHƯA ĐO. Với preset Quality, tỉ lệ I/O chỉ càng nhỏ hơn
(tầng SR chậm hơn 15,7×). `08_BENCHMARK_RESULTS.md` mục F.

## 22. P95 nếu đo được

**CHƯA ĐO.** Mọi benchmark của đợt sửa này dùng **3 lượt/cấu hình, lấy trung
vị** (đôi khi kèm min/max) — không đủ mẫu để tính P95 có ý nghĩa. Muốn có P95
thật cần chạy hàng chục lượt liên tục trên cùng cấu hình, tốn nhiều thời gian
GPU trên máy dùng chung production hơn mức đợt đo này được cấp (mỗi lượt
"tính" giữ khoá `cpu_nhieu`, luật giới hạn ~30 phút/lượt).

## 23. Số lượng test / tỉ lệ pass

**Đếm tĩnh (grep `def test_`, không chạy pytest — ngoài phạm vi phiên viết
tài liệu này):** `tests/test_4904_upscale_correction.py` = 45 hàm test (có
`@pytest.mark.parametrize` ở 5 chỗ ⇒ số ca pytest thực sự thu thập được **cao
hơn** 45, con số chính xác **CHƯA ĐO** vì không chạy pytest);
`tests/test_4905_upscale_cong_ky_thuat_that.py` = 5; `test_82_upscalevideo.py`
= 19; `test_171_upscale_h32.py` = 7; `test_116_upscale_motion_features.py` =
7; `tests/test_4906_upscale_chot_tile_quality.py` = 2. **Tổng ≥ 85 hàm test**
chạm app này. Tỉ lệ pass: **CHƯA CHẠY trong phiên viết tài liệu này** — brief
của phiên này cấm chạy pytest/GPU/ffmpeg (chỉ đọc/ghi tài liệu). `11_RELEASE_
GATE.md` xác nhận cùng tình trạng ("test nhắm cụm `upscalevideo` phải xanh…
CHƯA CHẠY trong phiên viết tài liệu này").

## 24. P0/P1 còn lại

- 🔴 **ISSUE L** (P0 theo rủi ro): `job_runner._het_gio` dùng `os._exit(3)` ⇒
  bỏ qua `finally` ⇒ rò temp cỡ GB + tiến trình engine mồ côi giữ GPU. Nằm ở
  `platform_core/job_runner.py` — **dùng chung nhiều app**, ngoài phạm vi sửa
  của nhánh này, cần chủ khu `platform_core` xử lý. `12_PLAN_TRIEN_KHAI.md`
  mục 4.
- `routes.py`: 10 phát hiện `ruff` cũ + 2 chuỗi tiếng Anh chưa dịch — P2, chưa
  vá, ngoài phạm vi nhánh.
- `tools/check_i18n.py` đếm cả chuỗi trong `log.*` ⇒ báo tăng oan — lỗi công
  cụ đo, không phải lỗi app; chưa sửa công cụ.
- Shared-GPU scheduler thật, resume thật, RIFE, QSV/AMF thật — tất cả
  **DEFERRED có điều kiện mở khoá rõ ràng**, không phải nợ ẩn (mục 3 của
  `12_PLAN_TRIEN_KHAI.md`).

## 25. Điểm cuối /100

**Không chấm được một con số duy nhất**, và mục tiêu **≥90/100 của mandate
KHÔNG THỂ khẳng định đạt được.** Lý do — trích `10_FINAL_SCORECARD.md`: ít
nhất 5/17 hàng vẫn `CHƯA ĐO` (Fast perf, Quality perf, Disk I/O đầy đủ ma
trận, AI model quality, một phần VRAM policy/Autotune); các hàng có bằng
chứng dao động 10/100 (Resume — tính năng chưa từng tồn tại) đến 90/100 (Core
pipeline — cấu trúc không đổi). Trộn hàng có bằng chứng với hàng `CHƯA ĐO`
thành một trung bình sẽ **che giấu** đúng câu hỏi "đo được hay chưa đo được"
— đúng lỗi "hai trạng thái gộp thành một giá trị" mà `MEMORY.md` đã ghi nhận.
Xem mục TASK 2 (`10_FINAL_SCORECARD.md`) để có bảng đầy đủ theo hạng mục.

## 26. Commit SHA

`git log --oneline -1` tại thời điểm viết tài liệu này: **`3350993a`**
(`bench(upscale): tile sweep — Fast khong co gi, Quality nhanh hon 8,7 %
NHUNG la danh doi`) trên nhánh `claude/upscale-video-v2-correction-5fa61a`.
⚠️ SHA này **chưa gộp vào `main`** (`git log main..HEAD` chỉ có đúng commit
này). Các commit trước đó của nhánh này (core fix `c365de02`, bộ test
`c87d8e92`/`0be80075`/`test_4906`, bộ đo `48e779a0`, xoá warmup `9f05648d`,
tài liệu) **đã** ở trên `main` và **đã** đi theo trong lượt deploy SHA
`47b277ca` của một phiên khác (xác nhận bằng
`git merge-base --is-ancestor c365de02 47b277ca` = đúng) — xem mục 27.

## 27. Release / rollback

Xem `11_RELEASE_GATE.md` (đã cập nhật trong đợt này) cho đầy đủ. Tóm tắt:
15 trong số các commit của nhánh này đã lên `main` và đã đi theo lượt deploy
`47b277ca` của một phiên khác (deploy xuất **toàn bộ HEAD cây chính**, không
lọc theo nhánh/app) — bao gồm commit sửa lõi `c365de02` (gỡ 10 tính năng giả
+ bug ngữ nghĩa). Trước khi các commit này rời worktree, phiên điều phối xác
nhận hàm tính credit **hành vi giống hệt** qua 960 tổ hợp tham số (không đổi
giá — chỉ đổi lời khai lý do trong docstring `cost.py`). Ba thay đổi hành vi
**khách nhìn thấy** đã lên production: (1) job có đầu ra hỏng nay **FAIL**
thay vì thành công-và-tính-tiền, kill switch `LTT_UPSCALE_TECH_GATE=0`; (2)
cảnh báo chất lượng giả trên mọi job đã biến mất; (3) HEVC không có phần cứng
nay báo lỗi rõ thay vì âm thầm trả H.264. Commit còn lại (`3350993a`, tile
sweep Quality) **chưa gộp `main`, chưa deploy**. Rollback: `docs/16_CAP_
NHAT_VA_DEPLOY.md` — khôi phục `C:\LTTPlatform\app.previous\` → `app\` (qua
`tools\nang_quyen.py`), rồi nghiệm thu lại bằng `tools/nghiem_thu_deploy.py`
+ `/health/ready` + `/health/version` đúng SHA bản lùi.
