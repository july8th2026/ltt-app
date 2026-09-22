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
| L-A hop-dong | nguồn {zh,en,vi} → đích {vi,en}; rút phân vai; lọc làn giọng | 2000–2009 | **XONG** `90cfa3f8` (cây asv-final) |
| L-M e2e-nen | lượt thật NỀN (v3 zh→vi) trên mã gốc | — | đang chạy (cây asv-final, chỉ đọc) |
| ky-thuat | blackdetect/freezedetect/decode, VMAF, benchmark cắt cảnh, xoá do_watermark | 2010–2019 | đang chạy |
| giong | bước đo GPU mới; ASR lượt cuối + JiWER; SQUIM_OBJECTIVE; bỏ Dice; sửa đoạn | 2020–2029 | đang chạy |
| dich | MetricX-24 QE (năng lực `do_luong/metricx.py`), benchmark 4 chiều | 2030–2039 | đang chạy |
| ocr | định tuyến nguồn lời: nhúng → OCR hardsub → ASR, provenance | 2040–2049 | đang chạy |
| video-dai | chia lô + checkpoint + resume mọi giai đoạn dài | 2050–2059 | đang chạy |
| bien-tap | speed/zoom/crop/aspect/reframe (ADR gỡ CAM_TRONG_MVP) | 2060–2069 | đang chạy |
| phu-de | OFF/AUTO/SOURCE/TRANSLATED/CUSTOM qua AutoSub | 2070–2079 | đang chạy |
| cache-lease | một tính, nhiều chờ | 2080–2084 | đang chạy |
| cong-noi-bo | cổng workflow nội bộ submit/status/cancel/retry/result | 2085–2089 | đang chạy |
| tai-len | resume tải lên (multipart) | 2090–2094 | đang chạy |
| giong-en | giọng thuyết minh tiếng Anh (kho giọng dùng chung, không lộ cho khách LTT Voice) | 2095–2099 | đang chạy |
| gui | Studio: mọi điều khiển nối tới tệp ra | — | sau khi gộp |
| nghiem-thu | lượt thật cuối A/B/C/D, zh→vi + en→vi + vi→en, báo cáo cuối | — | sau khi gộp |

Hạ tầng dùng chung: `C:\LTTPlatform\qc-venv` (`setup/cai_qc_models.ps1`), giao thức `apps/asv_gpu/do_luong/venv.py`.

## Sổ lỗi + độ phủ

`LOI_TONG.md` cùng thư mục. Mỗi lượt thật ghi: phép nào có kết quả THẬT, phép nào bị che.
