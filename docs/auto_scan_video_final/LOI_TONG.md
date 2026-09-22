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
| M-01 | cao | Nói–khớp–kịch bản dùng công thức Dice tự chế (ngưỡng 0,80) **và không được nối** vào dây chuyền | `sua_chua.khop_van_ban` | L-C | **ĐÃ SỬA** — giai đoạn `qc_do_luong` (ASR large-v3 + jiwer WER/CER), ngưỡng hiệu chỉnh trên 50 đoạn tiếng thật; Dice đã xoá; vòng sửa nối `qc_giong` (L_GIONG.md) |
| M-07 | cao | Giai đoạn giọng dùng lại tệp cũ theo vân tay ⇒ vòng sửa "đọc lại" trả về **đúng bản vừa bị báo sai** (đúng cả với `KHONG_VUA`) | `giai_doan_giong._van_tay` | L-C | **ĐÃ SỬA** — muối vân tay bằng số vòng sửa đã đẩy đoạn về `voice_synthesis` |
| M-08 | trung | `COMPOSE` ghi trạng thái toàn vẹn (`flush`) rồi gọi `ctx.progress` khi chưa commit ⇒ SQLite `database is locked`, chỉ lộ ở lượt chạy lại sau vòng sửa | `giai_doan_ban_dung.chay` | L-C | **ĐÃ SỬA** — `db.commit()` sau `_khoa_con_dung` |
| M-02 | cao | QC liên tục cảnh bằng VLM định nghĩa nhưng **không ai gọi** | `qc_ai.py:115` | L-B/L-C | MỞ |
| M-03 | trung | Cắt cảnh = ffmpeg `select=gt(scene,0.4)`, ngưỡng "CHƯA ĐƯỢC ĐO" | `canh.py:214` | L-B | MỞ — benchmark PySceneDetect |
| M-04 | trung | Khung đen T13 = YAVG tự đặt ngưỡng 2/255 | `qc.py:162` | L-B | MỞ — `blackdetect`/`freezedetect` chuẩn |
| M-05 | trung | Không có đo chất lượng hình sau mã hoá lại (VMAF), không có đo chất lượng dịch, không có đo chất lượng tiếng | — | L-B/L-C/L-D | MỞ |
| F-08 | trung | `expected_size` cua phien tai len la `int4` ⇒ kep o 2 GiB−1; sua that = BigInteger + migration | `platform_core/upload_sessions.py` | tai-len | MỞ |
| F-09 | trung | Nghia vu ghi cong CC BY 4.0 (SQUIM) chua co cho hien tren san pham | trang Gioi thieu/Giay phep | dieu phoi | MỞ |
| F-10 | trung | `hieu_canh.van_tay_canh` khoá cache cảnh theo `ma_canh`, KHÔNG theo `[bắt,kết]` ⇒ đổi bộ dò cảnh (PySceneDetect) làm `c1` mang mốc khác nhưng vân tay không đổi | `hieu_canh.py` | điều phối | MỞ — lane ky-thuat phát hiện, không sửa (tệp của lane khác) |
| M-01b | cao | Dice tự chế ĐÃ XOÁ; WER/CER thật thay thế, ngưỡng đo trên 50 đoạn thật | `sua_chua.NGUONG_DOC_SAI` | giong | **ĐÃ ĐÓNG** |
| M-03b | trung | Cắt cảnh: PySceneDetect ContentDetector(35) F1 0,95 vs 0,73 của `scdet` cũ | `canh.py` | ky-thuat | **ĐÃ ĐÓNG** |
| M-04b | trung | Khung đen/đóng băng: `blackdetect`+`freezedetect` so với NGUỒN; thêm T17 giải mã cả tệp, T18 VMAF (ngưỡng 75) | `qc.py` | ky-thuat | **ĐÃ ĐÓNG** |
| M-06 | thấp | `tools/do_watermark.py` heuristic tự chế, không app nào gọi | `tools/` | ky-thuat | **ĐÃ XOÁ** (cùng `test_470`, `PHA13_*.md`) |

## Độ phủ lượt thật

| lượt | video | cặp | preset | model_that | giong_that | kết quả | ghi chú |
|---|---|---|---|---|---|---|---|
| L-M nền | v3 | zh→vi | cả hai | ? | ? | đang chạy | mã gốc `5f936d01` |
