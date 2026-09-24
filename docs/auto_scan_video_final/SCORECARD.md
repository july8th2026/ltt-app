# SCORECARD — Auto Scan Video final closure (§23 đề bài)

> Tám trục cho mỗi hạng mục; **≥ 98/100 mới PASS**. ⛔ Luật của bảng này: **điểm
> phải dẫn tới bằng chứng**, và *"bộ kiểm xanh"* KHÔNG phải bằng chứng cho trục
> *Real-engine proof*. Ô nào chưa có bằng chứng thì ghi `—`, không ghi số.
>
> Chấm độc lập (rà soát thù địch) chạy SAU cùng, trên nhánh đã gộp, và người
> chấm không được là làn đã viết hạng mục đó.

## Tám trục

| trục | câu hỏi nó hỏi | bằng chứng chấp nhận được |
|---|---|---|
| Correctness | làm đúng thứ đã hứa chưa | test nhắm + đối chứng tiêm lỗi |
| Product usefulness | khách dùng được chưa, có điều khiển chết không | đường UI → cài đặt → manifest → tệp ra khác đi |
| Real-engine proof | đã chạy với engine THẬT chưa | lượt chạy thật: `model_that` · `giong_that` · `thay_the=[]` |
| Quality | kết quả có đạt ngưỡng đo được không | số đo của bộ đo đã thành danh (VMAF/WER/SQUIM/MetricX) |
| Reliability | hỏng giữa chừng thì sao | huỷ · worker chết · chạy lại · trần job |
| Performance | tốn bao nhiêu, có nghẽn ai không | CPU/RAM/GPU/VRAM/độ trễ đo được |
| Maintainability | một nguồn mỗi luật, không bộ đo song song | AST/lint/bánh cóc |
| License safety | weights + mã đều thương mại được | `THIRD_PARTY_METRICS.md` §1 đầy đủ |

## Bảng chấm

⏳ = làn chưa nộp · `—` = chưa có bằng chứng.

| hạng mục | Corr | Useful | Real | Qual | Rel | Perf | Maint | Lic | tổng | chốt |
|---|---|---|---|---|---|---|---|---|---|---|
| Hợp đồng ngôn ngữ zh/en/vi → vi/en | — | — | — | — | — | — | — | — | — | chờ lượt thật |
| Một giọng thuyết minh (bỏ phân vai) | — | — | — | — | — | — | — | — | — | |
| Giọng tiếng Anh (kho chung) | — | — | — | — | — | — | — | — | — | ⚠️ chặn: cột `gioi` chờ chủ dự án |
| Phụ đề 5 chế độ (qua AutoSub) | — | — | — | — | — | — | — | — | — | |
| Điều khiển biên tập (tốc độ/zoom/crop/tỉ lệ) | — | — | — | — | — | — | — | — | — | |
| Âm thanh (nền/ducking/fade/loudness) | — | — | — | — | — | — | — | — | — | chưa có làn riêng — kiểm ở lượt thật |
| OCR / hardsub / định tuyến nguồn lời | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | |
| Video dài (chia lô, chạy tiếp) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | |
| Tải lên chạy tiếp | — | — | — | — | — | — | — | — | — | ⚠️ R2 thật chỉ kiểm được sau deploy |
| Cache dùng chung (một tính, nhiều chờ) | — | — | — | — | — | — | — | — | — | chưa chạy qua worker thật |
| QC kỹ thuật (khung đen/decode/VMAF/cắt cảnh) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | |
| QC giọng (ASR lượt cuối + WER/CER + SQUIM) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | |
| QC dịch (MetricX QE) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | |
| QC hình/ngữ nghĩa bằng VLM | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | — | M-02 **đã nối** (`L_QC_HINH.md`) — ⚠️ lớp hình đang **TƯ VẤN**, chưa gate |
| Sửa đúng chỗ (targeted repair) | — | — | — | — | — | — | — | — | — | `cat_sai` → `edit_plan` đã nối (`jobs._qc_hinh`), nhưng ⚠️ tắt vì tư vấn |
| Cổng workflow nội bộ | — | — | — | — | — | — | — | — | — | |
| Giao diện Studio | — | — | — | — | — | — | — | — | — | làn `gui` chưa chạy |

## Hạng mục release-critical

Phải ≥ 98 mới được tuyên bố hoàn thành (§26): hợp đồng ngôn ngữ · một giọng ·
phụ đề · điều khiển biên tập · âm thanh · OCR · video dài · QC bốn lớp · sửa
đúng chỗ · cổng nội bộ · giao diện · giấy phép.

⛔ Tải lên chạy tiếp và cache-lease **không** chặn release nếu bằng chứng cuối
ghi rõ phần chưa kiểm được trên hạ tầng thật (R2 / worker) — nhưng phải ghi ra,
không được lặng lẽ tính là đạt.
