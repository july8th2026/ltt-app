# Ma trận khoảng trống — pha 15–34 (sản phẩm pha 04)

> Đo ngày 11/09/2026 trên `phien/asv-v6`, sau khi pha 14 đóng.
> Tài liệu này trả lời đúng một câu cho mỗi pha: **năng lực đã có chưa, và
> đường đi tới nó đã có chưa** — hai câu hỏi khác nhau, và tách chúng ra là bài
> học đắt nhất của chương trình này (`nang-luc-co-nhung-khong-ai-di-tren-duong`:
> bốn ca trong một ngày, mọi tầng đúng và mọi phép kiểm xanh, mà không ai đi
> trên đường).

⛔ **Đây là bản đồ, không phải lời hứa.** Cột "còn thiếu" ghi *việc*, không ghi
*thời gian* — ước lượng thời gian ở đây sẽ là một con số bịa.

## Cách đọc ba hạng

| hạng | nghĩa |
|---|---|
| **ĐƯỜNG** | năng lực đã có và đã được gọi; còn thiếu là giao diện / hợp đồng / bằng chứng |
| **CẦU** | năng lực đã có ở nơi khác nhưng **chưa có đường gọi** từ ASV |
| **MÓNG** | năng lực **chưa tồn tại** — cần engine mới, phụ thuộc mới, hoặc một ADR |

---

## Bảng

| Pha | Tên | Hạng | Đã có gì (đo được) | Còn thiếu |
|---|---|---|---|---|
| 15 | Hardsub/OCR routing | **MÓNG** | `0` tệp nào trong `apps/`, `platform_core/` nhắc tới OCR (`ocr\|tesseract\|paddle\|easyocr`). Nhánh *embedded subtitle → parse* thì `ffprobe` đã đọc được stream `s` | Chọn engine OCR (**cần ADR + một phụ thuộc mới**), ngân sách CPU/GPU, độ tin cậy + fallback. ⚠️ Pha 13 đã cho một tiền lệ: bộ dò watermark **đạt** cổng tài nguyên nhưng **trượt** cổng chất lượng, và kết luận là *để tắt*. OCR hardsub có cùng rủi ro và phải đo trước khi bật |
| 16 | Subtitle Studio UX | **ĐƯỜNG** | `style_registry` có **9** preset kèm `label`/`description`; `ass_builder` có `highlight_mode` (`word`/`underline`/`bg_flash`/`all_text`/`keyword`) + `keyword_highlights`; pha 14 đã mở bề mặt và dựng ô chọn kiểu | Mở `highlight_mode` ra giao diện; xem trước đúng cấu hình cuối; font/size/color/position tuỳ biến (hiện chỉ chọn **preset**, không sửa từng thuộc tính) |
| 17 | LTT Voice live catalog | **ĐƯỜNG** | `gia.giong_cho_giao_dien` đọc catalog **sống** (không snapshot), có ba nhãn lọc + đường nghe thử; `rang_giong` xử lý ràng buộc | 🔴 **Nợ đã ghi**: `rang_giong` **không lọc theo ngôn ngữ giọng**. Mở khoá khi `apps/ltt_voice/giong_mau.py::loc()` nhận tham số ngôn ngữ. Phải suy ngôn ngữ từ **đích của lần chạy**, không hardcode `"vi"` |
| 18 | Voice Browser UX | **ĐƯỜNG** | Ba ô lọc + nghe thử đã có trong `asv/giong.js` | Tách tab *My Voices* / *LTT Voices*; trạng thái "thiếu mẫu nghe"; cập nhật sống |
| 19 | VoiceBinding | **CẦU** | `cai_dat.v3` đã có `giong_id` + vân tay toàn hồ sơ; quyền sở hữu giọng được kiểm ở `ltt_voice.giai_giong` | Một `VoiceBinding` **canonical ở máy chủ** với version riêng; hiện ràng buộc nằm rải trong `settings` |
| 20 | Diarization + multi-speaker | **CẦU** | Đường gọi **đã có**: `giai_doan_chep_loi:131` gọi `diarize_file` + `assign_speakers`, có `can_phan_vai(run)` làm cổng | Danh sách người nói ra giao diện; ánh xạ **một giọng cho mỗi người nói**; ghi đè thủ công; lưu bền |
| 21 | Auto Voice Match thật | **CẦU** | `hop_dong_v4.CHE_DO_GIONG_TU_KHOP` tồn tại; bằng chứng người nói có từ pha 20 | Thuật toán xếp hạng ứng viên + độ tin cậy + fallback. ⛔ `ADR-V4-001 D-V4-04` cấm để "tự khớp" chỉ là "lấy giọng mặc định" |
| 22 | Dubbing adaptation + fit | **ĐƯỜNG** | `nan_cho_vua` đã có; `thoi_gian.lap_ke_hoach` có `he_so_toc`/`cat_bot_ms`/`troi_sau_ms`; từ điển phát âm đã có | Benchmark ngưỡng fit; `VoiceBinding` phải chốt **trước** khi viết lại lời |
| 23 | Audio Studio | **CẦU** | `loudnorm` + bản phối master đã có (pha 22 đã sửa lỗi render đọc nhầm `nen` thay vì `master`); demucs tách 4 stem | Ba thanh mức (gốc/nền/giọng) ra giao diện; giữ nhạc/SFX; ducking/fade |
| 24 | Multilingual fan-out | **CẦU** | Phân tích nguồn đã tách khỏi dịch (`content_process` riêng) | Nhiều ngôn ngữ đích rẽ nhánh sau một lần phân tích; billing + cache phải đúng cho từng nhánh |
| 25 | Shared artifact cache + leases | **ĐƯỜNG** | `platform_core/leases.py` + vân tay theo giai đoạn đã chạy; **46** tệp chạm tới lease | Tái dùng **xuyên lần chạy** (hiện vân tay gắn `run_id`); một-tính-nhiều-chờ; an toàn riêng tư giữa chủ sở hữu |
| 26 | Renderer fusion | **ĐƯỜNG** | 🔑 **Pha 14 vừa trả trước một phần**: `ass=` đi vào **chính** `-filter_complex` đã có, không phải một lượt encode thứ hai. Chuỗi hiện tại đã gộp `concat`→`che`→`logo`→`chu`→`ass` trong MỘT lần | Benchmark NVENC/QSV/AMF/x264; giữ `stream-copy` cho preset giữ hình |
| 27 | Technical QC expansion | **ĐƯỜNG** | `giai_doan_qc` + `ket_xuat.kiem_tep_ra` (ffprobe trước promote) đã có | Thêm: khung đen, hỏng tệp, **biên phụ đề**, tác dụng thật của vùng che, nhất quán chính sách render |
| 28 | Speech/semantic/visual QC | **CẦU** | `giai_doan_qc_ai` đã có và đã gọi model | ASR lượt cuối đối chiếu kịch bản; VLM kiểm liên tục cảnh; bằng chứng kèm độ tin cậy |
| 29 | Targeted RepairPlan | **CẦU** | Phục hồi **mức đoạn** đã có ở `giai_doan_giong` | Sửa đúng đơn vị nhỏ nhất cho từng hạng lỗi; không tính lại cả lần chạy |
| 30 | Billing + cost explainability | **ĐƯỜNG** | Giữ chỗ / thực chi / quyết toán / hoàn lại đã chạy (`quan_sat_chi_phi`, `test_446`) | Luật giá cho đa đích / đa người nói / cache / retry; bảng bóc tách chi phí trên giao diện |
| 31 | Product API | **CẦU** | `platform_core/public_api/` + `server/api/inventory.py` (24 route đóng băng) đã có | Bề mặt ASV chưa mở ở `/api/v1`; cần ToolSpec + hợp đồng lỗi |
| 32 | UX polish + mobile + a11y | **ĐƯỜNG** | Pha 06 đã tách 9 module JS; pha 10b đã kiểm trình duyệt thật một lượt | Bàn phím, ARIA, trạng thái rỗng/đang tải/lỗi, xác nhận huỷ, không tràn ngang |
| 33 | Real E2E + stress | **CẦU** | `test_448` là bộ khung E2E và **đã** chạy được sau khi nới trần token | Máy A+B thật, Voice thật, LLM/VLM thật, **cả hai preset**, khởi động lại/bận/huỷ/hỏng một phần |
| 34 | Independent audit + RC | — | — | Chạy sau cùng. **Vẫn không deploy** |

---

## Ba điều bảng này nói ra mà bảng trạng thái không nói

**1. Chỉ pha 15 là MÓNG.** Mười chín pha còn lại đều đứng trên năng lực đã tồn
tại. Đó là tin tốt và cũng là cảnh báo: hạng **CẦU** là đúng cái hạng mà
`nang-luc-co-nhung-khong-ai-di-tren-duong` mô tả — mọi tầng đúng, mọi phép kiểm
xanh, và không khách nào chạm được tính năng.

⇒ Nghiệm thu mỗi pha CẦU phải hỏi **hai** câu, không phải một: *"có đường
không"* rồi *"có xe trên đường không"*.

**2. Pha 17 có một chặn đã biết tên.** Nợ `rang_giong` không lọc theo ngôn ngữ
giọng đã được ghi lại từ trước. Nó mở khoá bằng một điều kiện **kiểm được**:
`grep -n "ngon_ngu" apps/ltt_voice/giong_mau.py` cho thấy `loc()` nhận tham số
ngôn ngữ. Không phải một ước lượng.

**3. Pha 19 phải xong trước pha 22.** Prompt pha 22 ghi thẳng *"VoiceBinding
trước rewrite"*: viết lại lời thoại cho vừa thời lượng phụ thuộc vào giọng nào
sẽ đọc nó. Làm ngược thứ tự là đo `he_so_toc` cho một giọng rồi đổi giọng.

Thứ tự phụ thuộc thật, không theo số:

```
20 ─► 21 ─► 19 ─► 22
17 ─► 18 ─► 19
14 ─► 16
25 ─► 24 ─► 30
```
