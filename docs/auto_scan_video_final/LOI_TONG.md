# Sổ lỗi hợp nhất — ASV final closure

> Mỗi dòng: mã · mức · hiện trạng · nơi · việc/làn · trạng thái. Chỉ ghi điều
> ĐO/THẤY được; giả thuyết ghi rõ là giả thuyết.

| mã | mức | hiện trạng | nơi | làn | trạng thái |
|---|---|---|---|---|---|
| F-01 | cao | Phân vai (pyannote, GPU) chạy ở mọi lần AUTO_MATCH, kết quả `nguoi_noi` không ai đọc | `giai_doan_chep_loi.can_phan_vai` | L-A | **ĐÃ SỬA** — rút khỏi đường sản phẩm + bề mặt liên-app |
| F-02 | cao | `rang_giong` không lọc giọng theo làn ngôn ngữ đích | `rang_giong._rang_tu_khop` | L-A | **ĐÃ SỬA** — lọc theo `ngon_ngu_dich` của lần chạy; giọng mẫu lệch làn bị từ chối ở cửa; giọng khách đưa lời khai làn cho `ltt_voice` chốt |
| F-03 | cao | ASV chỉ khớp 20 giọng mẫu engine (đều `vi`), bỏ qua **17 giọng `en` đã có** trong kho giọng dùng chung | `rang_giong._rang_tu_khop` | giong-en | **ĐÃ SỬA mã** `c871e36b` — ⚠️ còn CHỜ CHỦ DỰ ÁN: cột `gioi` trống ở cả 25 giọng kho chung ⇒ AUTO_MATCH `en` vẫn `CHUA_RANG` trên production tới khi được duyệt điền (16/17, trừ Robin) |
| F-04 | cao | Không có phép chốt ngôn ngữ nguồn: video ngoài hợp đồng (vd. tiếng Nhật) chạy tiếp tới LLM + giọng | `giai_doan_chep_loi.chay` | L-A | **ĐÃ SỬA** — `ngon_ngu.kiem_nguon_da_doan` ngay sau ASR |
| F-05 | cao | Lời nhắc hiểu cảnh ghi cứng "video tiếng Việt" (sai với mọi nguồn zh/en) | `hieu_canh.py` | L-A | **ĐÃ SỬA** — `PHIEN_BAN_HIEU_CANH` 2→3, `HO_SO` 1→2 |
| F-06 | trung | Khoá cache chung của TRANSCRIBE thiếu ngôn ngữ đích ⇒ dùng lại chéo đích bỏ qua phép chốt F-04 | `cache_chung.dau_vao_noi_dung` | L-A | **ĐÃ SỬA** |
| F-07 | — | `test_448` đỏ: báo cáo nghiệm thu ghi `chep_loi/1`, mã nay `chep_loi/2` | `tests/test_448` | L-M | CHỜ — lượt thật mới tái sinh báo cáo (đúng thiết kế) |
| M-01 | cao | Nói–khớp–kịch bản dùng công thức Dice tự chế (ngưỡng 0,80) **và không được nối** vào dây chuyền | `sua_chua.khop_van_ban` | L-C | MỞ — thay bằng ASR lượt cuối + jiwer WER/CER |
| M-02 | cao | QC liên tục cảnh bằng VLM định nghĩa nhưng **không ai gọi** | `qc_ai.py:115` | L-B/L-C | MỞ |
| M-03 | trung | Cắt cảnh = ffmpeg `select=gt(scene,0.4)`, ngưỡng "CHƯA ĐƯỢC ĐO" | `canh.py:214` | L-B | MỞ — benchmark PySceneDetect |
| M-04 | trung | Khung đen T13 = YAVG tự đặt ngưỡng 2/255 | `qc.py:162` | L-B | MỞ — `blackdetect`/`freezedetect` chuẩn |
| M-05 | trung | Không có đo chất lượng hình sau mã hoá lại (VMAF), không có đo chất lượng dịch, không có đo chất lượng tiếng | — | L-B/L-C/L-D | MỞ |
| M-06 | thấp | `tools/do_watermark.py` heuristic tự chế, không app nào gọi (pha 13 đã "để tắt") | `tools/` | L-B | MỞ — xoá hoặc thay |

## Độ phủ lượt thật

| lượt | video | cặp | preset | model_that | giong_that | kết quả | ghi chú |
|---|---|---|---|---|---|---|---|
| L-M nền | v3 | zh→vi | cả hai | ? | ? | đang chạy | mã gốc `5f936d01` |
