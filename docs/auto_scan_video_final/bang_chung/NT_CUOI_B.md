# NT_CUOI lượt B — giữ hình · USER_SELECTED `Minh Đức` · zh→vi

Nhánh `phien/asvf-nghiem-thu-v2` · 24/09/2026 08:50–09:57 (UTC+7) · **67 ph 35**
Phim: `深度解析丨跳伞…` 106,835 s. Nguồn định nghĩa: `bang_chung/NEN_V3.md` lượt B.

⚠️ **Số liệu ở tệp này CỨU TỪ `asv_stage`, không từ bản ghi JSON của khuôn.** Lượt
chạy đi hết chuỗi rồi khuôn chết ở mã đo của chính nó (`OSError [Errno 22]` trên
`ra_B::zh->vi….mp4`). Đã sửa (`f18cca12`) nhưng lượt này không có JSON.

## Độ trung thực

| | |
|---|---|
| `LTT_ASV_QC_AI` | **BẬT** |
| model · giọng | THẬT (pool → máy B · LTT Voice :8120) |
| **card** | ✅ **ĐƯỢC CẤP** cho `asv_gpu.audio_prepare` |
| `python_tach` | ✅ venv worker |

## Kết quả: `run.status = done` · **12/12 giai đoạn `succeeded`**

Lần đầu chuỗi ASV đi hết trên phim khách thật, có card, trên đúng venv production.

### ⭐ Vòng sửa `dich_sai` chạy ĐẦU-CUỐI — bằng chứng đầu tiên

`qc_ai` chấm bản dịch là sai → `sua_chua(dich_sai)` → `content_process` lần 2
(09:29→09:36) → `voice_synthesis` lần 2, rev 7 (09:36→09:43) → `qc_do_luong` lần 2
(09:44→09:45) → `qc_ai` lần 2 (09:45→09:57) → `done`. 42 job, 22 `advance`.

⛔ `M-09a` ghi *"chưa ai có phép kiểm đầu-cuối cho nó"*. Làn `sua-khoa` đã sửa cái
chết `database is locked` nhưng đo trên khuôn `test_402` (video sin 0,4 s, 3 đoạn).
**Đây là lần đầu trên phim thật, có card, với phán quyết QC thật đẩy lần chạy ngược.**

### ⛔ Bảng vòng sửa — tổng KHÔNG ĐỔI

| | trước sửa | sau sửa |
|---|---|---|
| `dich_sai` | 60 | **44** |
| `doc_sai` | 10 | **14** |
| `khong_vua` | 15 | **27** |
| **tổng đáng tin** | **85** | **85** |

Dịch lại giảm `dich_sai`, nhưng **đọc lại bản dịch mới sinh thêm** `doc_sai` và
`khong_vua`. ⇒ Vòng sửa **di chuyển** khiếm khuyết chứ không giảm. `VONG_SUA_TOI_DA
= 1`; nâng lên 2–3 chưa chắc hội tụ (`sua_chua.py:69` đã cảnh báo đúng điều đó).
⛔ **n = 1** — cần bảng của C/D/E trước khi gọi đây là kết luận. `LOI_TONG.md` N-02.

### Số QC — đọc từ `outputs`, không từ cột `status`

| phép | số | ghi chú |
|---|---|---|
| `qc` T1–T18 (**kỹ thuật**) | `qc_ky_thuat_dat = true`, 0 mục hỏng | **T3/T5 của `NEN_V3` KHÔNG tái hiện** |
| `qc_ai` ngữ nghĩa | **44/95 không đạt** (46%) | sau vòng sửa |
| `qc_ai` hình | 0 chỗ nối | *"bản đồ chỉ có một khoảng giữ"* |
| `qc_do_luong` giọng | **14/95** vượt ngưỡng WER/CER | sau vòng sửa |
| cảnh báo tiếng | 8 đoạn PESQ < 2,0 | |
| `compose` | `cach_render="sao_chep"`, `che_do_hinh="copy"` | |
| `render` | 22.957.458 B · 106,833 s · h264 · aac | |

⚠️ **T3/T5 không tái hiện ≠ R-02/R-03 đã đóng.** Một lượt trên một phim. R-02/R-03
do làn `fix-qc-am` đóng bằng phép kiểm riêng (`test_2014`, `test_2015`); lượt này
chỉ **không phản chứng** chúng.

### Thời gian — đo thật, và phần suy ra được gọi là suy ra

`voice_synthesis`: **TTS 60,8 s · LLM nắn 391,5 s** · 15 vòng · 79/95 vừa khe ·
68/95 sinh mới · 27 dùng lại.

⚠️ **R-04 chưa đạt dự phóng.** `NEN_V3` đo 937 s; R-04 **dự phóng** ~190 s; **đo
thật 452 s** (391,5 + 60,8). Giảm 2,1× nhưng bằng ~2,4× dự phóng. Và **80% vẫn là
LLM viết lại, không phải TTS** — đúng chẩn đoán gốc của R-04, nên R-04 đã **giảm**
chứ chưa **giải quyết**.

### Nguồn lời thoại

`nguon_loi = "ocr"` · `rapidocr/3.9.2+PP-OCRv6_small` · phủ sóng **92,0** ·
`ly_do = ["khong_co_phu_de_nhung"]`. ⭐ Đường OCR hardsub chạy **thật** trên phim
khách — làn `ocr` có bằng chứng vận hành.

## ⛔ Ba khiếm khuyết lượt B phát hiện — xem `LOI_TONG.md`

* **N-01** (chặn mở khách) — về `done` với 85 mục còn lại, và `qc.py` **không đọc**
  phán quyết ngữ nghĩa/giọng. **CHỜ CHỦ DỰ ÁN.**
* **N-02** — `qc_dat` nói quá phạm vi ⇒ đổi tên `qc_ky_thuat_dat`. **ĐÃ SỬA.**
* **N-03** — 44 và 85 không hiện cho khách. **ĐÃ SỬA** + chốt trên Chromium thật.
