# 02_GAP_MATRIX — mỗi khoảng cách một NGUYÊN NHÂN GỐC

Luật §10: mỗi hạng mục dưới 98 phải nhận **một** PRIMARY GAP. Phân loại sai
dẫn tới sửa sai — ví dụ điển hình nằm ngay dòng đầu bảng này.

## Bảng phân loại — chỉ cho hạng mục đã có bằng chứng

| ID | Hạng mục | PRIMARY GAP | Nguyên nhân gốc (không phải triệu chứng) | Việc ĐÚNG | Việc SAI phải tránh |
|---|---|---|---|---|---|
| 39 | Per-voice runtime profile | **DATA_GAP** | `ho_so_giong.py` (143 dòng) đọc đúng, `tools/do_ho_so_giong.py` đo đúng, `giong: {}` vì **chưa ai bấm nút chạy**. Không có dòng mã nào sai | Chạy công cụ đo ≥3 lượt, kiểm σ, ghi snapshot | ⛔ Sửa `ho_so_giong.py` cho "hoàn thiện hơn". §18 cấm đúng việc này |
| 40 | ETA accuracy | **DATA_GAP** | Hệ quả trực tiếp của 39: mọi giọng dùng chung hằng số 18 ký tự/giây | Đo xong 39 rồi đo lệch ETA | ⛔ Viết bộ ETA thứ hai |
| 38 | Fallback EN | ~~DATA_GAP~~ **CODE_GAP** | 🔴 **ĐỔI PHÂN LOẠI 09/09.** Tôi xếp DATA_GAP vì tưởng *"kho rỗng"*. Đo lại: kho chung có **25 giọng (8 VI + 17 EN)** từ 01/09, đã curate, đang sống trên production. Nguyên nhân thật: `tu_giong_mau()` gán **cứng** `ngon_ngu="vi"` và chỉ đọc 20 preset engine — 17 giọng EN không bao giờ được nhìn thấy | Thêm một nguồn ứng viên thứ hai (`tu_kho_chung()`) đổ vào `cac`. Đúng thuật § `lui_giong.py` đã viết sẵn | ⛔ Nới bậc thang cho lùi `en`→`vi` (ca khách thật 26/08). ⛔ Và đừng đi mua giọng EN mới — ta đã có 17 |
| 20 | Streaming | **CODE_GAP** (kèm quyết định thiết kế) | `/v1/stream` có ở sidecar; không hàm bọc, không cửa web, không JS | Quyết SSE hay chunked TRƯỚC, rồi nối; giữ nguyên admission/ownership/billing/cancel | ⛔ Coi "đã nối được endpoint" là xong. §21 đòi benchmark stream vs thường |
| 14 | Priority scheduling | **ARCH_GAP** | 🔴 ĐÍNH CHÍNH: `Job` **không có** cột `priority`. Dòng `models.py:723` mà baseline trích là của **`ApiKey`** (lớp bắt đầu dòng 690), và `api_pool.py:192` đọc nó thật ⇒ nó **không** phải cột chết | Quyết ở `05_DECISIONS.md` **cùng lúc** với U-20: thêm trục ưu tiên là **đổi lược đồ + migration**, nên nó phải được biện minh bởi phương án thắng, không phải bởi "cột đã có sẵn" | ⛔ Dựng trục ưu tiên vì tưởng cột đã có — chi phí thật cao hơn hẳn |
| 11 | GPU correctness (CPU-side) | **OPS_GAP** | 🔴 `voice_sidecar` **không đặt** `torch.set_num_threads`. Đo: lõi **vật lý 10**, `torch.get_num_threads()` = **10** trong `vieneu-venv` ⇒ một lượt sinh lấy **trọn 10 lõi** cho phần CPU. Cùng khuyết tật CLAUDE.md ghi cho `apps/auto_scan_video/demucs_runner.py` | Đặt trần luồng trong `engine.nap()`; và **trước** mọi lượt benchmark Wave A1 phải cấu hình trần luồng, không chỉ xin `cua_so_yen` | ⛔ Chạy 120 lượt sinh (~15 phút) nguyên trạng. `cua_so_yen` + cây tiến trình **không** thấy được phần này — tiến trình con không nằm trong ngân sách |
| 13 | GPU fairness | **ARCH_GAP** | `admission_slots=1` + không có điểm nhả giữa chừng ⇒ job 100k ký tự giữ card tới lúc xong. Công bằng hiện có là giữa **tài khoản**, không giữa **việc ngắn/dài** | Thiết kế U-20 theo §20: A/B/C/D, chọn có căn cứ | ⛔ Sửa bằng cách hạ `TRAN_KY_TU_CONG_KHAI`. Phanh đặt dưới nhu cầu bình thường biến thất bại thành mặc định |
| 30 | VI acoustic quality | **BENCHMARK_GAP** | Corpus 6 câu. `lech_giua_cau` 0,1044 ≈ `cer.tb` 0,1249 ⇒ phương sai giữa câu áp đảo phương sai giữa vòng | Mở corpus lên 30 câu VI, giữ 3 vòng | ⛔ Kết luận "CER 12,5 %" là chất lượng của engine |
| 31 | EN acoustic quality | **BENCHMARK_GAP** | Một câu, một lượt | 30 câu EN × 3 vòng | ⛔ Suy từ "model song ngữ" ra "tiếng Anh xong" (§22) |
| 32 | Mixed VI/EN | **BENCHMARK_GAP** | Không có corpus mixed | 15 câu mixed × 3 vòng | — |
| 12 | GPU admission | **BENCHMARK_GAP** | Cơ chế đúng và có lớp giành thật; chưa ai chạy load test | 1 dài + 1 ngắn · 1 dài + 5 ngắn · nhiều dài | ⛔ Đọc mã rồi kết luận công bằng |
| 62 | Public API contract | **PRODUCT_DECISION_GAP** | `ltt_voice.enroll` có job type, không có ToolSpec ⇒ nhân bản giọng không mở qua API. Có thể là **cố ý** (dữ liệu sinh trắc + consent) | Hỏi: mở hay khai rõ là đóng và vì sao | ⛔ Tự mở một cửa API nhận giọng người thật |
| 67 | Frontend maintainability | ~~MAINTAINABILITY_GAP~~ **KHÔNG PHẢI GAP** | Đã vẽ bản đồ (A0-6): màn đã cô lập (1 tham chiếu mỗi màn), nguyên thuỷ dùng chung 4–12 chỗ. Coupling **thấp**, chỉ có tệp **dài** | Để nguyên. §24 đã lường trước: *"không ép nếu phân tích thực nghiệm chứng minh tệp chung hiện vẫn tốt hơn"* | ⛔ Tách. Nó làm **tăng** coupling ở nền không bundler |

## Ba gap KHÔNG phải gap — ghi ra để lượt sau khỏi "sửa"

1. **`/v1/stream` không có client** — `test_504` ghim cả hai chiều, kèm dòng
   hướng dẫn gỡ phép kiểm khi nào nối. Đây là **bề mặt để sẵn có chủ ý**, không
   phải rác. Nó vẫn là việc phải làm (U-07), chỉ là đừng dọn nhầm nó.

2. **`lui_giong` không lùi được làn `en`** — trả `None` là **hành vi đúng đã
   thiết kế**: *"Một lỗi 'không đọc được' thành thật tốt hơn một bản đọc bằng
   giọng người khác."* Gap nằm ở kho, không ở nhánh mã.

3. **Không có tab "Chạy lô"** — `manifest.py` ghi rõ đã bỏ có chủ ý, vì đường
   tài liệu dài lấy mất nhu cầu ấy, và cấm dựng lại chỉ để một chú thích
   "sáu tab" thành đúng.

## Ưu tiên xử lý — theo §36, không theo độ dễ

Thứ tự của §36 là: **đúng đắn → tiền của khách → sở hữu/bảo mật → toàn vẹn dữ
liệu → chất lượng âm thanh → …**. Nên thứ tự làm việc **không** phải thứ tự của
bảng U-.

Hạng mục 41/42/43 (giá · giữ chỗ · quyết toán/hoàn tiền) **chưa được đo lần
nào** và đứng ở bậc 2 của §36. `credit.py` đang chạy thật với 5.500 bút toán.
⇒ Chúng phải được đọc **trước** mọi việc thuộc streaming hay kho giọng, và
chúng **không cần GPU**.
