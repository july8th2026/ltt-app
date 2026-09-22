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

## Làn (mỗi làn một worktree + nhánh `phien/asv-final-<làn>`)

| làn | việc | tệp sở hữu chính | trạng thái |
|---|---|---|---|
| L-A hop-dong | đích {vi,en} + nguồn {zh,en,vi}; bỏ phân vai khỏi đường sản phẩm; `rang_giong` lọc làn theo đích | `hop_dong_v4.py`, `cai_dat.py`, `rang_giong.py`, `giai_doan_chep_loi.py`, chỗ hardcode `"vi"` | mở |
| L-M e2e-nen | lượt thật NỀN trên mã hiện tại (v3, zh→vi) — lấy danh sách hỏng thật | chỉ đọc mã; ghi `bang_chung/` | mở |
| L-B do-ky-thuat | VMAF/blackdetect/freezedetect/decode-check; PySceneDetect vs `scdet` benchmark | `qc.py`, `canh.py` | chờ L-A |
| L-C do-giong | ASR lượt cuối + jiwer WER/CER thay Dice; chất lượng tiếng (model license sạch) | `qc_ai.py`, `sua_chua.py`, capability mới | chờ nghiên cứu |
| L-D do-dich | QE dịch không cần bản tham chiếu, license thương mại | capability mới | chờ nghiên cứu |
| L-E ocr | phụ đề nhúng → hardsub OCR → ASR, kèm provenance | module mới + định tuyến nguồn lời | chờ L-A |
| L-F video-dai | chia lô + checkpoint + resume cho mọi giai đoạn gọi mạng/model | `giai_doan_noi_dung.py`, `dich_thuat.py`, `hieu_canh.py` | chờ L-A |
| L-G bien-tap | crop/zoom/aspect/reframe/speed (ADR gỡ `CAM_TRONG_MVP`) | `che_do_render.py`, `ket_xuat.py` | chờ L-A |
| L-H phu-de | OFF/AUTO/SOURCE/TRANSLATED + style qua AutoSub | `phu_de.py` | chờ L-A |
| L-I cache-lease | một tính, nhiều chờ | `cache_chung.py` | chờ L-A |
| L-J tai-len | resume tải lên | `platform_core/storage.py`?, `assets.py` | nghiên cứu |
| L-K cong-noi-bo | cổng workflow nội bộ submit/status/cancel/retry/result | module mới | chờ L-A |
| L-L gui | Studio: mọi điều khiển nối tới tệp ra | `server/static/asv/`, templates | cuối |

## Sổ lỗi + độ phủ

`LOI_TONG.md` cùng thư mục. Mỗi lượt thật ghi: phép nào có kết quả THẬT, phép nào bị che.
