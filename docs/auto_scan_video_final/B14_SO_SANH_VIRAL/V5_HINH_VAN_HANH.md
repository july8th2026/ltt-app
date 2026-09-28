# V5 — xử lý video/ffmpeg · chọn cảnh · watermark · cache artifact · chất lượng · chẩn đoán · GPU

**Đã đọc đầy đủ:** `xu_ly_chon.py` (1754d) · `cat_nho.py` (346d) · `cache_artifact.py`
(673d) · `chan_doan_loi.py` (230d) · `bam_watermark.py` (782d) · `chat_luong.py`
(252d) · `chan_doan_gpu.py` (145d) · `bench_toc_do.py` (193d) · `_do_ffsplit.py`
(26d). Phía ta đọc đối chiếu: `ke_cat.py`, `canh.py`, `hieu_canh.py`,
`giai_doan_hinh_anh.py`, `giai_doan_ban_bien_tap.py`, `logo.py`, `lop_phu.py`,
`cache_chung.py`, `thi_hanh.py`, `loi.py`, `ma_loi.py`, `ban_ghi.py`, `pipeline.py`.

**⛔ Chưa đọc / chỉ đọc header + defs (KHÔNG đủ để chấm điểm chi tiết, chỉ đủ để
xếp hạng ưu tiên):** `xu_ly_video.py` (2716d — đọc phần đầu + các hàm được gọi
chéo qua `cat_nho`/`xu_ly_chon`, KHÔNG đọc trọn) · `cai_gpu.py` (1542d, chỉ đọc
header) · `kiem_thu_vien.py` (565d, chỉ đọc header + danh sách hàm).

---

## Phát hiện quan trọng nhất — không nằm gọn trong một hàng bảng

**`xu_ly_chon.py` KHÔNG phải mã chọn/loại CẢNH.** Tên tệp gây hiểu lầm: "chọn"
ở đây là **khách TICK CHECKBOX hiệu ứng** (lật, tăng tốc, watermark, màu, cắt
đầu/cuối — `xu_ly_chon.py:1-11,130-264`). Đã grep toàn bộ 1754 dòng cho
`rung|shake|freeze|blur.*detect|scene|Laplacian|optical` — **không một dòng
nào** liên quan chất lượng cảnh (`xu_ly_chon.py` không match gì ngoài chữ
"Trung" trong "chữ Trung").

Mã dò CẢNH thật của Viral nằm ở `cat_nho.py:57-90` (`phat_hien_canh`) —
PySceneDetect `ContentDetector(threshold=27.0)`, và nó **chỉ dò RANH GIỚI**
(để băm video dài thành clip ngắn cho reup, cắt không giữa cảnh), **không có
khái niệm "cảnh xấu"** — không nhãn hỏng/tốt, không điểm số, không tín hiệu
rung/chuyển-cảnh-lỗi/camera-bất-ổn ở bất kỳ đâu trong 12 tệp phạm vi.

⇒ **Không có gì để "mượn" cho đúng khiếm khuyết chủ dự án báo 28/09.** Cả
Viral lẫn ta (xem hàng 1 bảng dưới) đều thiếu tín hiệu "rung/chuyển cảnh lỗi/
camera bất ổn ở đuôi cảnh" — Viral vì nó chưa từng cần (app một người dùng,
dùng PySceneDetect chỉ để CẮT KHÚC, không để LỌC XẤU); ta vì tín hiệu hiện có
(`blackdetect`+`freezedetect`) đo đúng hai thứ khác (đen/đứng hình).

---

## Bảng

| HẠNG MỤC | BƯỚC ASV | VIRAL CÓ GÌ | TA CÓ GÌ | TRẠNG THÁI | GIÁ TRỊ | GIÁ | ĐỀ NGHỊ |
|---|---|---|---|---|---|---|---|
| Tín hiệu "cảnh xấu" (rung/chuyển-cảnh-lỗi/camera bất ổn) | `edit_plan`/`image_finish` | ⛔ KHÔNG — `xu_ly_chon.py` là tick-chọn hiệu ứng khách, không liên quan cảnh; `cat_nho.py:57-90` chỉ dò RANH GIỚI cảnh (PySceneDetect ContentDetector, không chấm điểm xấu/tốt) | `giai_doan_ban_bien_tap.py:306` `NGUON_BANG_CHUNG = "phep do ffmpeg (blackdetect+freezedetect)"`; `giai_doan_hinh_anh.py:157-165` `diem_kem` = tỉ lệ khung ĐEN/ĐỨNG HÌNH — 2 tín hiệu, không bắt rung/camera bất ổn | KHÁC THIẾT KẾ (cả hai bên đều thiếu ĐÚNG tín hiệu khách cần; Viral không có gì để mượn) | 5 +đo (khiếm khuyết chủ dự án ĐÃ BÁO 28/09, đo được `so_canh_hong=0` trên 127 cảnh thật) | — (không áp dụng "mượn"; đây là XÂY MỚI, không phải porting) | ⛔ KHÔNG LẤY (không có nguồn để lấy) — cần đề xuất kỹ thuật riêng (vd optical-flow/độ lệch khung liên tiếp đo RIÊNG ở cửa sổ ĐUÔI cảnh, `cv2` đã có sẵn trong kho qua `canh.py`/`do_vung.py` nên không thêm dep mới, nhưng vẫn cần khai trần CPU theo `check_khai_tran_cpu.py`) |
| Dò RANH GIỚI cảnh (bộ tách + ngưỡng) | `edit_plan` | `cat_nho.py:57-90`: PySceneDetect `ContentDetector`, `threshold=27.0` (mặc định thư viện, KHÔNG đo riêng — không có ghi chú benchmark) | `canh.py:16-45`: cùng bộ tách, nhưng `NGUONG_DOI_CANH=35.0` **đã benchmark F1=0,95** trên 9 clip tổng hợp + 2 video thật gán nhãn tay (`docs/auto_scan_video_final/L_KY_THUAT.md`), so với AdaptiveDetector (0,93) và `select=gt(scene,0.4)` cũ (0,73) | ĐÃ MƯỢN (độc lập, và bản của ta đo kỹ hơn — ngưỡng 27 mặc định của Viral thấp hơn ngưỡng đã đo của ta) | 1 (mã gọn, không thêm gì) | 1 | ⛔ KHÔNG LẤY — ta đã có bản tốt hơn (có đo), không có lý do hạ ngưỡng xuống 27 |
| Bám/che watermark CHUYỂN ĐỘNG của người khác | `image_finish` (cạnh `logo.py`/`lop_phu.py`) | `bam_watermark.py:332-519` (`tu_do`) tự dò bằng OCR (RapidOCR) + gradient-matching (đo thật: ngưỡng gradient bắt watermark mờ tới alpha 0,12, thô chỉ tới 0,50) + RANSAC tách "trôi đều" khỏi "đứng yên"/banner; `:542-783` (`bam`) bám mẫu khách khoanh qua tới 400 khung, sinh biểu thức ffmpeg đa-đoạn qua Douglas-Peucker (đo thật: trần 60 chặng, 160 chặng ffmpeg GÃY — `:180-201`) | `logo.py:1-60` chèn logo **CỦA MÌNH** (khách tải lên), toạ độ **TĨNH** theo phân số khung; `lop_phu.py` chữ tĩnh — KHÔNG có khái niệm bám vật THỨ BA di chuyển | THIẾU (nếu ASV cần xoá watermark nguồn TQ) — ⛔ chưa xác định được khách của TA có cần không (theo §9 thang chấm) | 3 (chưa đo được khách có cần; theo luật §9 không cho 5) | 4 (đốt CPU: đọc hàng trăm khung qua ffmpeg + OCR + `matchTemplate` mỗi video, dù `cv2` và `RapidOCR` đã có sẵn trong kho qua `do_vung.py`/`canh.py` nên không thêm dependency MỚI — vẫn phải khai trần theo `check_khai_tran_cpu.py`) | LẤY SAU (giá trị 3 giá 4 → theo công thức) — hỏi chủ dự án trước: nguồn TQ ASV xử lý có thường mang watermark nền tảng cần che không? |
| Cache tái dùng nội bộ 1 lần chạy (OCR/dịch/TTS lặp lại) | (không map 1-1 vào 1 giai đoạn — xuyên `content_process`→`render`) | `cache_artifact.py`: file cache TTL(7d)+LRU(cap 3GB) trên đĩa, khoá = `video_hash` THÔ (basename+size+mtime, KHÔNG hash nội dung — `:118-133`) + tham số + `CACHE_VERSION`; khoá tranh chấp liên-tiến-trình bằng `.lock` + PID-liveness kiểu Windows AN TOÀN (`:265-303`, tự cảnh báo `os.kill(pid,0)` GIẾT tiến trình trên Windows) + heartbeat + trần cứng chờ (1200s) | `cache_chung.py`: khoá = **checksum NỘI DUNG** thật (không phải mtime) + chủ sở hữu trong khoá (chống rò rỉ qua thời gian phản hồi, I19); dùng lại bằng CHÉP artifact qua `promote_va_ghi`, không TRỎ; chỉ 2 giai đoạn chia sẻ (`AUDIO_PREPARE`, `TRANSCRIBE`) có "đầu vào nội dung xác định được" | KHÁC THIẾT KẾ — hai bài toán khác nhau: Viral cache XUYÊN NHIỀU LẦN CHẠY của MỘT người dùng desktop (rủi ro rò rỉ giữa người dùng không tồn tại); ta cache XUYÊN NHIỀU KHÁCH của một SaaS (rủi ro rò rỉ LÀ trọng tâm thiết kế, I19) | 2 (vận hành nhanh hơn, khách không thấy) | 5 (đổi mô hình sở hữu cache multi-tenant — chạm bất biến bảo mật) | ⛔ KHÔNG LẤY nguyên khối — nhưng 1 ý đáng ghi riêng: `_pid_song` (`cache_artifact.py:265-303`, Windows `OpenProcess`+`WaitForSingleObject` thay vì `os.kill(pid,0)`) là một BUG THẬT của Windows đã bị Viral đo và vá — nếu kho ta có chỗ nào dùng `os.kill(pid,0)` để kiểm tiến trình trên Windows thì đó là một lỗi tương tự, đáng một lượt `grep` riêng (không thuộc phạm vi B14) |
| Dọn khoá mồ côi lúc khởi động | — | `cache_artifact.py:345-383` (`don_lock_mo_coi`) — ca thật 27/07: lock 16 tiếng tuổi sống sót qua việc CẬP NHẬT app (bản cũ bị đóng cưỡng bức, `finally` không chạy); dọn dựa trên PID-chết HOẶC tuổi lock > 1h | Không tìm thấy tương đương trong phạm vi đã đọc (`thi_hanh.py`/`leases.py` không thuộc phạm vi V5) | ⛔ chưa kiểm được (ngoài phạm vi đọc của làn này — `platform_core.leases` không nằm trong 12 tệp phạm vi V5) | — | — | — |
| Chẩn đoán lỗi máy khách → thông báo tiếng Việt | (không map — đây là lớp NỐI theo §2, "log cho người đang ngồi xem") | `chan_doan_loi.py:17-142`: 11 nhóm mẫu regex thứ tự cụ thể→chung (WDAC · Douyin chặn bot · vcredist · hết RAM/đĩa · CUDA · quyền · uv hỏng), MỖI mẫu có nguồn (ca khách thật, ngày tháng); `:160-182` có một lượt KIỂM SỐNG (`co_vc_runtime`, nạp thật 3 DLL) để không đổ lỗi sai khi log chứa "dll load failed" nhưng máy đã có VC++ | `loi.py:70-130` (`phan_loai`) phân loại theo KIỂU EXCEPTION (không phải regex chuỗi) → 4 nhãn ngữ nghĩa RETRY cho nền tảng (`nguoi_dung`/`ban`/`mo_ho`/`tam_thoi`); `ma_loi.py` dịch SANG mã ổn định → câu tiếng Việt cho khách + chính sách hoàn credit | KHÁC THIẾT KẾ — đúng như §2 cảnh báo: Viral chẩn đoán từ CHUỖI LỖI TỰ DO (không kiểm soát được kiểu ngoại lệ, vì lỗi tới từ thư viện C/DLL ngoài); ta có kiểm soát kiểu ngoại lệ (tự định nghĩa) nên không cần đoán từ chuỗi | 2 (vận hành — không phải khách thấy trực tiếp, họ thấy câu lỗi VN đã có qua `ma_loi`) | 3 (gói mới nhỏ — chỉ `re`, nhưng cần một sổ mẫu VÀ MỘT nguồn/ca thật cho mỗi mẫu, thứ ta CHƯA CÓ) | LẤY SAU, hẹp: chỉ 1 Ý ĐÁNG XÉT — mẫu regex làm TẦNG THỨ HAI cho lỗi từ THƯ VIỆN NGOÀI (ffmpeg/onnxruntime/torch) mà exception tự định nghĩa của ta KHÔNG bọc được (vd traceback CUDA/DLL lọt thẳng ra ngoài `try` của `loi.phan_loai`) — cần đo trước: bao nhiêu % lỗi thật của ASV là loại này, chưa đo nên KHÔNG cho GIÁ TRỊ cao hơn |
| Đo chất lượng phụ đề (CPS/ngắt dòng) theo mốc ngành | `qc`/`giai_doan_giong` | `chat_luong.py:88-127,130-197`: chấm `.srt` theo Netflix/BBC (≤42 ô/dòng, ≤17 CPS mục tiêu, cue 0,833-7s) + NGƯỠNG THỨ HAI đo thật (`CPS_KHONG_KIP=25`, vì trung vị THẬT của 18.048 cue đã ĐÚNG BẰNG 17 → "%>17" luôn ~50%, vô nghĩa — `:88-104`) + phát hiện "ngắt xấu" (cue kết bằng từ bổ nghĩa tiếng Việt) | `ban_ghi.py:325-341`: CPS (`ky_tu_moi_giay`) đã có, nhưng dùng cho MỘT mục đích hẹp khác — phát hiện ca "không mốc từ + tốc độ bất khả" (`ly_do="zero_moc_tu_va_toc_do_bat_kha"`), không phải báo cáo tổng hợp toàn file | KHÁC THIẾT KẾ (ta đã có CPS, khác mục đích — không phải THIẾU) | 2 (vận hành/chẩn đoán nội bộ khi khách báo lỗi, không phải tính năng khách thấy) | 2 (hàm thuần, tái dùng logic CPS đã có) | LẤY SAU nếu cần báo cáo tổng hợp chất lượng phụ đề cho vận hành — không cấp bách, ta đã có CPS ở đúng chỗ cần |
| Kiểm thư viện runtime CHẠY THẬT (không chỉ import) | — (vận hành/CI, không map giai đoạn) | `kiem_thu_vien.py:1-19` — bảng đối chiếu "kiểm YẾU (import/`.dist-info`/`is_available()`) vs kiểm ĐÚNG (gọi hàm thật/chạy 1 kernel GPU thật)", đúc kết từ 6 máy khách hỏng cùng buổi mà import vẫn xanh | ⛔ chưa kiểm được (không tìm bánh cóc tương đương trong phạm vi V5; có thể đã có ở `tools/` ngoài phạm vi làn này) | ⛔ chưa kiểm được | — | — | Không chấm — cần một làn khác kiểm `tools/` có bánh cóc "kiểm chạy thật" cho `onnxruntime`/`torch` trên máy A/B chưa, trước khi so |
| Cài/sửa tăng tốc GPU cho máy khách | — | `cai_gpu.py:1-8` — cài `nvidia-cuda-runtime`/`cublas`/`cudnn` qua `uv pip install` (CỘNG THÊM, không `uv sync` — tránh prune nhầm `torch`/`yt-dlp`) vào venv của TỪNG MÁY KHÁCH desktop | KHÔNG ÁP DỤNG trực tiếp — máy A/B là hạ tầng TA quản lý tập trung (`docs/HAI_MAY_A_VA_B.md`), không phải venv cài lẻ trên máy khách | KHÔNG ÁP DỤNG (khác hình thái sản phẩm — desktop cài-lẻ vs SaaS hạ tầng tập trung, đúng §2 bảng khác biệt nền tảng) | 1 | — | ⛔ KHÔNG LẤY — nhưng bài học "uv pip install cộng thêm, không uv sync" đáng ghi vào vận hành máy A/B nếu ta cũng dùng `uv` quản GPU deps (chưa xác minh, ngoài phạm vi V5) |
| Chẩn đoán GPU không chạy (script thủ công cho máy khách) | — | `chan_doan_gpu.py` — script CHẠY MODULE-LEVEL (không có hàm), kiểm từng mắt xích nạp CUDA DLL trên máy khách có GPU NVIDIA, KẾT LUẬN rõ nguyên nhân (thiếu gói/driver cũ/DLL fail) | KHÔNG ÁP DỤNG — cùng lý do hàng trên (`docs/HAI_MAY_A_VA_B.md` đã có "máy nào có card gì"; chẩn đoán driver là việc vận hành máy A/B, không phải việc chẩn đoán MÁY KHÁCH VÔ DANH) | KHÔNG ÁP DỤNG | 1 | — | ⛔ KHÔNG LẤY |
| Benchmark tốc-độ-giọng/time-warp qua preset | — | `bench_toc_do.py` — script cá nhân, đường dẫn cứng máy tác giả (`C:\Users\vannh\...`), đo "tỉ lệ cứu" (% câu vượt 1,3× được video-time-warp kéo về ≤1,3×) qua 3 preset — phương pháp đo hay (baseline vs biến thể, median qua nhiều video), nhưng KHÔNG phải module tái dùng được (hard-code đường dẫn/video ID) | ⛔ chưa kiểm được có cơ chế "cứu tốc độ giọng bằng video-time-warp" tương đương hay không (ngoài phạm vi 12 tệp V5, có thể ở `nan_thoi_luong.py`/`thoi_gian.py`) | ⛔ chưa kiểm được | — | — | Không chấm mã (nó là script debug, không phải logic sản phẩm) — nếu ASV có time-warp tương tự, PHƯƠNG PHÁP đo "tỉ lệ cứu" (không phải mã) đáng tham khảo cho một lượt đo riêng |
| Đo tách filter/encode (debug hiệu năng) | — | `_do_ffsplit.py` — 26 dòng, script debug MỘT LẦN của tác giả (đường dẫn cứng `C:\Users\vannh\...`), không phải logic sản phẩm | — | KHÔNG ÁP DỤNG (không phải mã sản phẩm, là log điều tra một sự cố cụ thể của Viral) | — | — | ⛔ KHÔNG LẤY |

---

## ⛔ Chưa kiểm được (ngoài những dòng đã đánh dấu trong bảng)

- `xu_ly_video.py` (2716 dòng) — chỉ đọc phần đầu + các hàm được gọi chéo
  (`tu_tim_ffmpeg`, `nap_config`, `bien_doi_khung`, `lay_thoi_luong`, `co_video`,
  `KHUNG_RATIO`) qua `cat_nho.py`/`xu_ly_chon.py`. **Không đọc trọn** — có thể
  còn tín hiệu hình ảnh (vd đo độ nét/exposure) chưa lộ ra qua các điểm gọi đã
  xem. Đáng một lượt đọc riêng nếu B14 cần đào sâu xử lý-hình-ảnh-mức-khung-hình.
- `cai_gpu.py` (1542 dòng) — chỉ đọc header, chưa đọc phần cài đặt/sửa lỗi chi
  tiết.
- `kiem_thu_vien.py` (565 dòng) — chỉ đọc header + chữ ký 21 hàm kiểm-từng-gói,
  chưa đọc nội dung từng hàm (vd `_wav_thu`, `_ort_gpu` có thể có ngưỡng đo được
  đáng trích).
- Phía ta: `platform_core/leases.py` (cơ chế "giữ chỗ" nhắc trong `cache_chung.py`
  docstring) không nằm trong phạm vi 12 tệp V5 — không đối chiếu được với
  `don_lock_mo_coi` của Viral.

---

**SHA:** làm việc trên nhánh `worktree-agent-ac65202167da7e259` (worktree
`agent-ad5256b791ce7ff9c`), tệp này commit riêng — xem `git log -1` trên chính
tệp để lấy SHA chính xác sau khi commit.
