# Ma trận tính năng V6 — mỗi tính năng Viral có một pha

> Sản phẩm của **pha 01** (*"loại bỏ DEFER sai kiểu V5"*) và **pha 04** (*"mỗi
> feature Viral phù hợp phải có destination và phase; không để feature biến mất
> trong docs"*). Dựng ngày 11/09/2026 từ `docs/auto_scan_video_v5/FEATURE_PARITY_MATRIX.md`.

## Vì sao tệp này tồn tại

Ma trận V5 có **12 dòng `DEFER`**, và không dòng nào mang **pha V6**. Một `DEFER`
không kèm pha là cách một tính năng biến mất khỏi tài liệu mà không ai quyết định
bỏ nó. Nhiều dòng trong số đó V6 **đã làm xong** (*Logo của tôi*, *Watermark chữ*,
*Karaoke*, *Tự dò logo*) mà ma trận V5 vẫn ghi `DEFER`.

⭐ **Cột "Tính năng" lấy NGUYÊN VĂN từ ma trận V5 bằng máy**, không gõ lại.
`tests/test_477_asv_v6_ma_tran_tinh_nang.py` chốt: tập tên ở đây **bằng đúng**
tập tên ở ma trận V5 — không thiếu một dòng, không bịa thêm một dòng.

## Trạng thái

| trạng thái | nghĩa | số dòng |
|---|---|---|
| `XONG` | đã giao, có chỗ chứng minh | 31 |
| `MOT_PHAN` | có năng lực, thiếu một phần đề bài gọi tên | 5 |
| `CHUA` | chưa làm, pha đích đã rõ | 15 |
| `CAN_ADR` | nằm trong `CAM_TRONG_MVP` — mở cần một ADR, không phải một lượt code | 3 |
| `LOAI` | cố ý không làm, **kèm lý do** | 5 |

Cột "Pha V6": `00`–`34`, hoặc `V4`/`V5` khi đã giao trước V6, hoặc `LOAI`.

## Bảng

| Tính năng | Quyết định V5 | Pha V6 | Trạng thái | Căn cứ / lý do |
|---|---|---|---|---|
| Tải video lớn, bền vững | REUSE_LTT | 08 | XONG | `PHA08_TAI_LEN.md` — đường tải lên 2 GiB bền vững |
| Kiểm định dạng trước khi gửi | REIMPLEMENT_CLEAN (UI) | 08 | XONG | `PHA08_TAI_LEN.md` |
| Preview nguồn | ADAPT_VIRAL_IDEA | 08 | XONG | `PHA08_TAI_LEN.md` — 08b xem trước nguồn |
| Ước giá trước khi chạy | KEEP_ASV + REIMPLEMENT_CLEAN (UI) | 30 | XONG | `/uoc-tinh` trước khi chạy + khối Chi phí sau khi chạy (`quan_sat.tom_tat_cho_khach`), `test_482` |
| Ước thời gian | ADAPT_VIRAL_IDEA | 30 | MOT_PHAN | ước giờ đã có; giải thích chi phí/thời gian là việc pha 30 |
| Preset cấp sản phẩm | KEEP_ASV | 07 | XONG | `PHA07_CAI_DAT_CHUAN_TAC.md` — preset trong hồ sơ chuẩn |
| Hàng đợi / trạng thái bền | KEEP_ASV | V4 | XONG | hàng đợi job + trạng thái bền của nền tảng, `thi_hanh.py` |
| Cắt đầu/cuối | ADAPT_VIRAL_IDEA | 10 | XONG | `cat_dau_cuoi.py`, `test_461` |
| Tỉ lệ khung 9:16/16:9 | DEFER → ADR-V5 | 10 | CAN_ADR | `reframe` nằm trong `CAM_TRONG_MVP` — mở cần một ADR |
| Phóng to | DEFER → ADR-V5 | 10 | CAN_ADR | `zoom` nằm trong `CAM_TRONG_MVP` — mở cần một ADR |
| Quy tắc biến đổi toạ độ khi zoom | REIMPLEMENT_CLEAN (chỉ đặc tả + test) | 12 | CHUA | phụ thuộc pha 10 mở zoom/crop; không có zoom thì không có gì để biến đổi |
| Tốc độ | DEFER | 10 | CHUA | phần còn lại của pha 10 |
| Logo của tôi | DEFER (đã có chỗ trong IA) | 11 | XONG | `logo.py` (11b), `test_466` |
| Watermark chữ | DEFER | 11 | XONG | `lop_phu.py` (11a), `PHA11_LOP_PHU_CHU.md` |
| Nhạc nền | REJECT trong ASV | 23 | CAN_ADR | V5 loại khỏi ASV, nhưng pha 23 gọi tên *optional background music*; `music_replace` nằm trong `CAM_TRONG_MVP` |
| Ghép video | REJECT | LOAI | LOAI | ghép nhiều video là một sản phẩm khác, không phải lồng tiếng |
| Ảnh bìa | REUSE_LTT, hậu MVP | LOAI | LOAI | không pha V6 nào gọi tên; app `thumbnail` riêng đã phục vụ việc này |
| Lật gương · chỉnh màu · vân tay `--uniq` | REJECT — xem VIRAL_RENDER_FEATURE_MAP.md §10 | LOAI | LOAI | lật gương/đổi màu/vân tay `--unique` là né phát hiện nội dung — xem `VIRAL_RENDER_FEATURE_MAP.md` §10. Pha 10 có gọi tên *mirror*: mở lại cần một ADR |
| Chọn thư mục lưu | REJECT | LOAI | LOAI | ứng dụng web giao tệp qua tải về; không có thư mục máy khách để chọn |
| Trình sửa vùng kéo-thả trên khung hình | REIMPLEMENT_CLEAN — thuộc GUI của ASV | 12 | XONG | `8c4a1d35` + `8cd5b281`, `test_462` |
| Toạ độ chuẩn hoá 0..1 | EXTEND_LTT_CAPABILITY? Không — ban_dung là của ASV ⇒ KEEP_ASV + mở rộng | V5 | XONG | `vung_che.py` luật L1, `test_456` |
| Làm mờ vùng | ADAPT_VIRAL_IDEA | V5 | XONG | `vung_che.py`, `test_457` |
| Xoá logo bằng điền nền | DEFER — cần đo VRAM trước khi khai | 13 | LOAI | đo ở pha 13: đạt cổng tài nguyên, **trượt** cổng chất lượng ⇒ để tắt — `PHA13_NHAN_DIEN_WATERMARK.md` (đã xoá ở ASV final, xem lịch sử git `e84b22a2`) |
| Tự dò logo | DEFER (phụ thuộc job GPU mới) | 13 | XONG | `tools/do_watermark.py` — dựng xong nhưng **để tắt**; **ĐÃ XOÁ ở ASV final** (heuristic tự chế, không ai gọi — `docs/auto_scan_video_final/L_KY_THUAT.md`): bộ dò tìm vùng tĩnh, không tìm watermark |
| Tự dò dải phụ đề gốc | ADAPT_VIRAL_IDEA, hậu MVP | 15 | CHUA | chưa có bộ dò dải phụ đề gốc; đi cùng định tuyến nguồn lời của pha 15 |
| Vùng che ↔ vùng chữ tránh nhau | REIMPLEMENT_CLEAN (đặc tả) | 12 | CHUA | chưa có luật tránh nhau giữa vùng che và vùng chữ |
| **Định tuyến nguồn lời** (sub nhúng → hardsub OCR → ASR) | ADAPT_VIRAL_IDEA → đặt ở asv_media/asv_gpu, không ở orchestrator | 15 | CHUA | hạng MÓNG — `MA_TRAN_KHOANG_TRONG.md` |
| Đọc phụ đề nhúng | REIMPLEMENT_CLEAN | 15 | CHUA | `ffprobe` đã thấy luồng `s`; chưa có đường đọc |
| OCR hardsub | DEFER — nhưng nhánh định tuyến làm trước | 15 | CHUA | hạng MÓNG: chưa có engine OCR — cần ADR + một phụ thuộc mới |
| ASR | REUSE_LTT | V4 | XONG | `giai_doan_chep_loi.py`, `test_407` |
| Hợp nhất OCR + ASR | DEFER | 15 | CHUA | phụ thuộc OCR |
| Làm sạch bản chép (ảo giác, lặp, chồng đè) | ADAPT_VIRAL_IDEA | V4 | XONG | `ban_ghi.py` |
| Đốt phụ đề vào hình | REUSE_LTT, hậu MVP | 14 | XONG | `PHA14_PHU_DE.md`, `test_471` |
| Style phụ đề (font/cỡ/màu/viền) | REUSE_LTT | 16 | XONG | `PHA16_SUBTITLE_STUDIO.md`, `test_472` |
| Karaoke / chữ chuyển động | DEFER | 16 | XONG | `highlight_mode` + `animation`, `test_472` |
| Sửa SRT rồi render lại | ADAPT_VIRAL_IDEA, hậu MVP | 29 | CHUA | cần luồng sửa hậu kỳ trên lần chạy ĐÃ quyết toán (compose → render) = một luật tiền; chạy lại tự động ra đúng byte cũ — `PHA29_30_SUA_VA_CHI_PHI.md` |
| Gọi model dịch | KEEP_ASV / REUSE_LTT | V4 | XONG | `giai_doan_noi_dung.py`, `test_408` |
| Từ điển tên riêng | ADAPT_VIRAL_IDEA (thuộc ASV: ContentProfile) | V5 | XONG | `tu_dien.py`, `test_460` |
| Nhiều ngôn ngữ đích | DEFER — IA phải chừa chỗ | 24 | CHUA | hạng CẦU — `MA_TRAN_KHOANG_TRONG.md` |
| **Phân tích nguồn một lần, fan-out N ngôn ngữ** | ADAPT_VIRAL_IDEA — thiết kế RenderPlan ngay từ V5 để không phải mổ lại | 24 | CHUA | phân tích nguồn đã tách khỏi dịch; chưa rẽ nhánh N ngôn ngữ |
| Danh mục giọng của khách | REUSE_LTT | 17 | MOT_PHAN | catalog sống đã có; **chặn**: `giong_mau.loc()` chưa lọc theo ngôn ngữ |
| Lọc giọng theo giới/vùng/phong cách | REUSE_LTT | 18 | XONG | ba ô lọc giới/vùng/phong cách, `asv/giong.js` |
| Nghe thử giọng | REUSE_LTT + REIMPLEMENT_CLEAN (UI) | V5 | XONG | đường nghe thử, `gia.giong_cho_giao_dien` |
| Phân vai người nói | REUSE_LTT | 20 | MOT_PHAN | đường gọi `diarize_file` + `assign_speakers` đã có; chưa có ánh xạ ra giao diện |
| Nhãn nam/nữ cho cụm nói | ADAPT_VIRAL_IDEA | 21 | CHUA | hạng CẦU |
| Nhiều giọng cho nhiều người | DEFER | 20 | CHUA | hạng CẦU |
| Ràng buộc "OCR không có giọng ⇒ không diarize" | KEEP_ASV | 15 | CHUA | luật chỉ có nghĩa khi có nguồn OCR |
| Âm lượng gốc / giữ nhạc nền | KEEP_ASV | 23 | XONG | `am_thanh.py` — mức nền so với lời, tắt nền, hạ theo lời, fade; MỘT thanh vì sau `loudnorm` giọng/nền không phải hai bậc tự do — `test_479` |
| Trần nén thời lượng khi khớp | KEEP_ASV | 22 | XONG | `nan_cho_vua.tran_co_gian`, `PHA22_VUA_KHE.md` |
| Clone giọng | REUSE_LTT | V4 | XONG | giọng của khách qua LTT Voice, `rang_giong._rang_khach_chon` |
| Cache artifact theo khoá nội dung | ADAPT_VIRAL_IDEA → EXTEND_LTT_CAPABILITY (thuộc platform_core, không thuộc ASV) | 25 | XONG | `cache_chung.py` — khoá địa chỉ nội dung cho tách nguồn + chép lời, `test_478` |
| "Một tính, các bên kia chờ rồi dùng lại" | EXTEND_LTT_CAPABILITY dùng lease | 25 | CHUA | hai lần chạy cùng video nộp CÙNG LÚC vẫn tính hai lần — `PHA25_CACHE_CHUNG.md` §5 |
| Nguyên tắc NGHI NGỜ → MISS | ADAPT_VIRAL_IDEA | V4 | XONG | vân tay mang phiên bản engine: nghi ngờ thì trượt cache, `thi_hanh.phien_ban_engine` |
| Khoá cache gồm đủ tham số + `CACHE_VERSION` | KEEP_ASV + mở rộng | V4 | XONG | `PHIEN_BAN_CHE_DO`, `PHIEN_BAN_QC`, `phien_ban_engine` |
| Một lần encode duy nhất | KEEP_ASV | 26 | XONG | `PHA26_RENDERER_FUSION.md`, `test_474` |
| Chọn encoder GPU | REUSE_LTT | 26 | XONG | `bang_chung/bo_ma_hoa_20260911.json`, `test_474` |
| Tiến độ render % + ETA | KEEP_ASV + REIMPLEMENT_CLEAN (UI) | 32 | MOT_PHAN | tiến độ % đã có; **chưa có ETA** |
| Chẩn đoán chậm (encoder, ×realtime, filter) | KEEP_ASV + REIMPLEMENT_CLEAN (UI) | 32 | MOT_PHAN | hồ sơ chẩn đoán + log hạ bộ mã hoá đã có; chưa có trên giao diện |
| 2 lane render | REUSE_LTT | V4 | XONG | hai app thi hành `asv_media` / `asv_gpu` |

## Hai điều bảng này nói ra

**1. Ba mâu thuẫn giữa V5 và đề bài V6 đã được đặt tên, không bị làm mịn đi.**
*Nhạc nền* (V5 loại, pha 23 gọi tên), *lật gương* (V5 loại vì né phát hiện, pha 10
gọi tên), *ảnh bìa* (V5 hậu MVP, không pha nào gọi tên). Cả ba cần một quyết định
sản phẩm, không phải một lượt code.

**2. `CAN_ADR` là một trạng thái riêng, không phải `CHUA`.** Tỉ lệ khung và phóng to
chặn vì `CAM_TRONG_MVP` cấm chúng — chú thích của chính bảng đó nói *"một mục rời
khỏi đây là một quyết định sản phẩm, và nó cần một ADR"*. Gộp chúng vào `CHUA`
sẽ khiến người đọc nghĩ chỉ thiếu thời gian.
