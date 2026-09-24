# ASV FINAL CLOSURE — kế hoạch điều phối (nguồn trạng thái duy nhất)

> Phiên `asv-final`, cây `D:\LTTSTUDIOSAPP-asv-final`, nhánh `phien/asv-final`,
> gốc `5f936d01` (22/09/2026). Đề bài: *MASTER PROMPT — AUTO SCAN VIDEO FINAL
> CLOSURE* (chủ dự án, 22/09). ⛔ Không deploy, không `public=True`: đích là
> `READY_FOR_OWNER_REVIEW`.

## Quyết định chủ dự án trong phiên

| Ngày | Quyết định |
|---|---|
| 22/09 | Hợp đồng ngôn ngữ: **nguồn ∈ {zh, en, vi}**, **đích ∈ {vi, en}**, nguồn ≠ đích. Nghiệm thu chính **zh→vi** trên video `Desktop\TEST VIDEO` (4 clip Douyin tiếng Trung, 3/4 có hardsub chữ Hán). en→vi và vi→en kiểm bằng clip phụ dựng từ giọng LTT Voice thật. |

## Kiểm kê video nghiệm thu (ffprobe 22/09, không sửa tệp nguồn)

| mã | tệp (rút gọn) | khung | fps | thời lượng | tiếng | phụ đề nhúng | hardsub |
|---|---|---|---|---|---|---|---|
| v1 | 廉价的牛肠…#美食.mp4 | 1024×576 h264 | 30 | 265,0 s | aac 44,1k st | không | không thấy ở 40 s (chỉ logo góc 中国一味) |
| v2 | 暴雨天野外露营…mp4 | 864×576 h264 | 30 | 190,0 s | aac 44,1k st | không | có (chữ Hán trắng, đáy) |
| v3 | 深度解析丨跳伞…mp4 | 836×576 h264 | 30 | 106,8 s | aac 44,1k st | không | có + chữ UI game |
| v4 | 真人气枪游戏红蓝双方对决.mp4 | 1024×576 h264 | 29,97 | 275,0 s | aac 44,1k st | không | có + lower-third |

PRIMARY_REAL_ACCEPTANCE_VIDEO: **v2** (hardsub rõ, lời thuyết minh, cảnh thật,
190 s) — chốt lại sau lượt nền (L-M).

## Làn (mỗi làn một worktree `D:\LTTSTUDIOSAPP-asvf-<làn>` + nhánh `phien/asv-final-<làn>`, gốc `e84b22a2`)

| làn | việc | dải test | trạng thái |
|---|---|---|---|
| L-A hop-dong | nguồn {zh,en,vi} → đích {vi,en}; rút phân vai; lọc làn giọng | 2000–2009 | **ĐÃ GỘP** |
| L-M e2e-nen | lượt thật NỀN (v3 zh→vi) trên mã gốc | — | **ĐÃ GỘP** — đẻ ra R-01…R-05, cả năm đã sửa |
| ky-thuat | blackdetect/freezedetect/decode, VMAF, benchmark cắt cảnh, xoá do_watermark | 2010–2019 | **ĐÃ GỘP** |
| giong | bước đo GPU mới; ASR lượt cuối + JiWER; SQUIM_OBJECTIVE; bỏ Dice; sửa đoạn | 2020–2029 | **ĐÃ GỘP** |
| dich | MetricX-24 QE, benchmark 4 chiều | 2030–2039 | **ĐÃ GỘP** |
| ocr | định tuyến nguồn lời: nhúng → OCR hardsub → ASR, provenance | 2040–2049 | **ĐÃ GỘP** |
| video-dai | chia lô + checkpoint + resume mọi giai đoạn dài | 2050–2059 | **ĐÃ GỘP** |
| bien-tap | speed/zoom/crop/aspect/reframe | 2060–2069 | **ĐÃ GỘP** |
| phu-de | OFF/AUTO/SOURCE/TRANSLATED/CUSTOM qua AutoSub | 2070–2079 | **ĐÃ GỘP** |
| cache-lease | một tính, nhiều chờ | 2080–2084 | **ĐÃ GỘP** |
| cong-noi-bo | cổng workflow nội bộ submit/status/cancel/retry/result | 2085–2089 | **ĐÃ GỘP** |
| tai-len | resume tải lên (multipart) | 2090–2094 | **ĐÃ GỘP** |
| giong-en | giọng thuyết minh tiếng Anh | 2095–2099 | **ĐÃ GỘP** |
| gui | Studio: mọi điều khiển nối tới tệp ra | 2100–2101 | **ĐÃ GỘP** — G-01…G-05 |
| do-giong | đo giới tính giọng bằng model, thay cho điền tay | 2141–2145 | **ĐÃ GỘP** |
| qc-hinh | QC hình bằng VLM | — | **ĐÃ GỘP** — hạ xuống TƯ VẤN (M-10) |
| sua-khoa | vòng sửa chết `database is locked` (M-09) | 2160 | **ĐÃ GỘP** — đo cả SQLite và PostgreSQL |
| toc-do-gpu · fix-toc-do · fix-qc-am · fix-auto-match · no-ky-thuat | các bản sửa sau lượt nền | 2150, 2014–2015 | **ĐÃ GỘP** |
| bang-prod | 5 bảng `asv_*` thiếu trên production (P-01) | — | **XONG 24/09** — đã tạo trên production, hậu kiểm bằng catalog |
| nghiem-thu-v2 | khuôn xin cấp card + khoá theo pha; lượt thật A/B/C/D + chiều ngược | 3000–3001 | **ĐANG CHẠY** — phần 1 xong (12 phép + đối chứng); lượt B đang chạy |

⛔ **Việc CÒN LẠI của cả phiên, tính tới 24/09:**

1. **Lượt thật A/B/C/D + một lượt chiều ngược** (làn `nghiem-thu-v2`) — đây là cái chặn mọi
   thứ còn lại. ⚠️ Mọi con số thời gian của các lượt TRƯỚC 24/09 đều **đo khuôn, không đo sản
   phẩm**: khuôn không xin cấp card nên demucs và ASR chạy CPU.
2. **Sinh lại `docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json`** từ lượt thật ⇒
   `test_448` (2 đỏ) xanh lại. ⛔ Không sửa phép kiểm cho khớp số cũ.
3. **Chấm bảng điểm** (`SCORECARD.md`) — chưa ô nào được chấm; mỗi ô phải dẫn bằng chứng.
4. **Một lượt soát đối nghịch độc lập** trước khi tuyên bố `READY_FOR_OWNER_REVIEW`.
5. **M-11** — dọn lần chạy mồ côi trong CSDL test (cần khoá `postgres_test`).
6. **L3 MỘT lần** khi hết mọi pha, rồi gộp `main`. ⛔ Không deploy (§24 của đề bài).

Hạ tầng dùng chung: `C:\LTTPlatform\qc-venv` (`setup/cai_qc_models.ps1`), giao thức `apps/asv_gpu/do_luong/venv.py`.

## Sổ lỗi + độ phủ

`LOI_TONG.md` cùng thư mục. Mỗi lượt thật ghi: phép nào có kết quả THẬT, phép nào bị che.
