# VIRAL_HARVEST_DECISIONS — thu hoạch gì, đưa đi đâu, và vì sao

> Artifact 4/5. Đây là **cổng chặn implementation**: §20 của prompt V5 cấm viết
> mã trước khi tệp này hoàn tất, và §16 cấm implement bất kỳ mục nào chưa trả lời
> đủ tám câu hỏi.

---

## 1. Bảng quyết định tổng

| Viral feature | Decision | Destination |
|---|---|---|
| Preview nguồn trước khi chạy | `ADAPT` | GUI ASV + `storage.url_for` |
| Tải lên bền vững (client) | `REUSE` | `platform_core.upload_sessions` — chỉ thiếu JS |
| Ước giá + ước thời gian trước khi bấm | `REIMPLEMENT` | ASV `gia.py` + route mới |
| Trình sửa vùng kéo-thả | `REIMPLEMENT` | **GUI ASV** (chỉ sinh dữ liệu toạ độ) |
| Toạ độ chuẩn hoá 0..1 + luật biến đổi | `REIMPLEMENT` | `ban_dung` (RenderManifest) — trường `vung[]` |
| Luật "hộp ra ngoài khung ⇒ LOẠI, không CLAMP" | `ADAPT` | đặc tả hình học của `ban_dung` + test |
| Vùng che ↔ vùng chữ tránh nhau | `ADAPT` | quy tắc trong `ban_dung` |
| Định tuyến nguồn lời (sub nhúng → hardsub → ASR) | `ADAPT` | `asv_media`/`asv_gpu`, **không** ở orchestrator |
| Đọc phụ đề nhúng | `REIMPLEMENT` | `asv_media` qua `media.probe` |
| OCR hardsub | `DEFER` | (tương lai) app/job có khai VRAM |
| Làm sạch bản chép (ảo giác/lặp/chồng đè) | `ADAPT` | ASV `van_ban.py` |
| Nhãn nam/nữ theo **cụm nói**, không theo từng câu | `ADAPT` | `autosubvideo.ai_workflows` (chủ sở hữu phân vai) |
| Lọc giọng theo giới/vùng/phong cách | `REUSE` | `ltt_voice.giong_mau.loc` — **đã khai sẵn**, chỉ thiếu GUI |
| Nghe thử giọng | `REUSE` | `ltt_voice.features.goi_cong` |
| Style phụ đề | `REUSE` | `apps/autosubvideo` (`video.subtitle`) |
| Từ điển tên riêng | `ADAPT` | ASV `ContentProfile` |
| Phân tích nguồn 1 lần → fan-out N ngôn ngữ | `ADAPT` | hình dạng `RenderPlan` (thiết kế nay, bật sau) |
| Cache artifact theo khoá nội dung | `ADAPT`→`EXTEND` | **`platform_core`**, không phải ASV |
| Chống giẫm chân khi hai run cùng cần một artifact | `EXTEND` | `platform_core.leases` (**không** lock tệp) |
| Chẩn đoán FFmpeg (encoder/×realtime/lý do chậm) | `ADAPT` | bề mặt operator; `ket_xuat.ho_so_chan_doan` đã có |
| Tiến độ render % + ETA | `REIMPLEMENT` | `quan_sat.py` → UI |
| Ảnh bìa tự động | `REUSE` | `apps/thumbnail` |
| Zoom · tỉ lệ khung · tốc độ · logo · watermark chữ | `DEFER` | cần **ADR-V5**; `CAM_TRONG_MVP`/`HAU_MVP` |
| Đa ngôn ngữ đích · đa giọng | `DEFER` | `HAU_MVP`; IA chừa chỗ sẵn |
| Xoá logo bằng điền nền · tự dò logo | `DEFER` | chưa đo VRAM |
| Nhạc nền thay thế | `REJECT` | `CAM_TRONG_MVP: music_replace` |
| Lật gương · chỉnh màu · vân tay `--uniq` | `REJECT` | né phát hiện bản quyền — quyết định thương hiệu |
| Hàng đợi tệp · env toàn cục · lock tiến trình | `REJECT` | `platform_core.jobs` / `leases` / `ban_dung` |
| License/HWID · crawler · đăng bài | `REJECT` | auth+credit · phi thương mại · `HAU_MVP` |
| Monolith `web_app.py` / `localize.py` | `REJECT` | kiến trúc app của nền tảng |

---

## 2. Tám câu hỏi — trả lời cho từng mục SẼ làm

§16: chưa trả lời đủ tám thì **không được implement**. Thứ tự câu hỏi:
(1) người dùng cần thật? (2) Viral giải pain nào? (3) LTT đã có tương đương?
(4) thuộc ASV hay platform? (5) ảnh hưởng billing? (6) ảnh hưởng GPU/resource?
(7) ảnh hưởng cache/fingerprint? (8) có E2E chứng minh?

### H-01 · Client tải lên bền vững
1. Có — trần thật hôm nay là 90 MB, dưới một video 10 phút.
2. Viral không có pain này (đọc từ đĩa). Pain là **của ASV**.
3. **Có, đầy đủ** — `upload_sessions`, đã có caller production.
4. Platform sở hữu năng lực; **GUI ASV** sở hữu client.
5. Không — giữ credit vẫn ở `features.tao_run`, sau khi có tệp.
6. Không.
7. Không. ⚠️ Nhưng khoá lưu trữ là đầu vào của mọi khoá cache sau này.
8. Phải viết: tải 1 tệp > 90 MB → run tạo được. **Đây là E2E chứng minh trần cũ đã đi.**

### H-02 · Preview nguồn
1. Có — điều kiện tiên quyết của trim, vùng che, safe area.
2. Viral: "render 20 phút rồi mới biết sai". Preview 5s là câu trả lời của họ.
3. `storage.url_for` presigned — đủ để `<video>` phát trực tiếp.
4. GUI ASV.
5. Không (chỉ đọc tệp khách đã tải).
6. **Không** — cố ý: preview là `<video>` của trình duyệt, **không** phải một job ffmpeg. Đó là khác biệt then chốt với Viral và nó làm preview thành **miễn phí**.
7. Không.
8. E2E: tải lên → thẻ `<video>` có `src` hợp lệ, phát được.

### H-03 · Trình sửa vùng
1. Có — che logo/phụ đề gốc là nhu cầu thật của reup hợp pháp.
2. Viral: khách không có cách nói "che chỗ này".
3. **Không có gì tương đương.**
4. **Chia hai:** GUI ASV sinh **dữ liệu**; `asv_media` **thi hành** bằng ffmpeg. Không phần nào là năng lực nền tảng mới.
5. Không ở V5 (chỉ vẽ + lưu). ⚠️ Khi nối vào render, một vùng inpaint sẽ đổi giá — mục đó đang `DEFER`.
6. Vẽ: không. Làm mờ khi render: CPU filter, nằm trong lần encode đã có.
7. **CÓ** — vùng phải vào khoá băm `ban_dung`. Thiếu là serve nhầm kết quả cũ.
8. E2E bắt buộc (§22): vẽ → lưu → tải lại → **cùng toạ độ chuẩn hoá** → render → hiệu ứng đúng vùng.

### H-04 · Định tuyến nguồn lời
1. Có — ép Whisper cho video đã có phụ đề là lãng phí GPU và cho kết quả tệ hơn.
2. Viral đo được ca thật: dò sai → treo 34 phút máy khách.
3. ASR có (`autosubvideo`). **Nhánh quyết định** thì không.
4. Thuộc `asv_media`/`asv_gpu` — nó là **năng lực media**, không phải chính sách sản phẩm.
5. **CÓ, theo hướng tốt**: bỏ qua ASR khi có sub nhúng ⇒ ít giây GPU ⇒ hoàn lại nhiều hơn. Ước giá phải **ước theo trường hợp xấu nhất** rồi hoàn, không ước theo trường hợp tốt.
6. **CÓ** — bỏ được một job GPU 6.000 MB.
7. **CÓ** — nguồn lời phải nằm trong khoá cache bản chép.
8. E2E: video có sub nhúng **không** kích hoạt job ASR.
9. ⚠️ Ghi thêm: bước OCR hardsub đang `DEFER`, nên V5 chỉ làm **hai** nhánh (sub nhúng / ASR). Nhánh thứ ba để lại chỗ trong đặc tả.

### H-05 · Lọc + nghe thử giọng
1. Có — `<select>` phẳng không chọn được giọng phù hợp.
2. Viral bày 16 giọng chia nam/nữ + nghe thử.
3. **Có cả hai, và đã khai đủ.** `apps/ltt_voice/__init__.py:59-65` khai bảy tên: `loc`, `tim`, `hop_le`, `DANH_SACH`, `NHAN_GIOI`, `NHAN_VUNG`, `NHAN_PHONG_CACH`. Chỉ thiếu **route + GUI** phía ASV. ⚠️ Đối chiếu lại với mã, không với `CAPABILITY_INVENTORY_V4.md` — bản kiểm kê đó nói `EXTEND_OWNER_CONTRACT` và nó đã cũ.
4. `ltt_voice` sở hữu; GUI ASV tiêu thụ.
5. ⚠️ **CÓ** — nghe thử gọi TTS thật. Phải: giới hạn độ dài câu mẫu, chống spam theo người dùng, và **quyết định rõ tính tiền hay không**. Không được để một nút nghe thử thành đường TTS miễn phí không giới hạn.
6. `vieneu_gpu`×1 mỗi lần nghe thử ⇒ phải qua admission, không gọi thẳng.
7. Không.
8. E2E: lọc theo giới → danh sách đổi; bấm nghe thử → có audio.

### H-06 · Cache artifact
1. Có — thử ba giọng trên cùng video hôm nay chép lời **ba lần**.
2. Chính xác pain đó.
3. Không có cache theo khoá nội dung.
4. **`platform_core`.** ⛔ Đặt trong ASV là lặp lại đúng lỗi Viral.
5. **CÓ, mạnh** — cache HIT nghĩa là **không tiêu tài nguyên**. Quyết toán phải theo **cái thật sự chạy**, không theo ước tính. ADR-001 D4 ("đo được, không tính lại") đã đúng hướng.
6. Giảm.
7. **Chính nó là câu hỏi 7.** Nguyên tắc bắt buộc chép: *khoá gồm ĐỦ tham số ảnh hưởng output + `CACHE_VERSION`*, và *nghi ngờ → MISS*.
8. E2E: chạy hai lần cùng video khác giọng → lần hai **không** phát sinh job chép lời, và **hoá đơn phản ánh điều đó**.

### H-07 · Ước giá + ETA
1. Có — bán theo credit mà không hiện số là khiếm khuyết niềm tin.
2. Viral dùng hạn mức gói, không phải pain giống nhau.
3. `gia.py` có bảng; không có route.
4. ASV.
5. **CÓ — đây là mục nhạy cảm nhất.** Hai bẫy đã ghi thành văn trong kho:
   - `manifest.py` cảnh báo: ước TTS phải đếm trên **văn bản đã chuẩn hoá** (`giong_noi.chuan_hoa_van_ban`), không trên bản dịch thô. `"1.500.000 đồng"` là 14 ký tự nhưng đọc ra hơn **gấp đôi**.
   - Ước **thấp** làm `kiem_tran_chi` đánh hỏng một lần chạy **đang giữa chừng** — một thất bại chính sách sạch sẽ nhưng là trải nghiệm tệ hoàn toàn tránh được.
   ⇒ Số hiện cho khách phải là **khoảng có cận trên**, không phải một con số đơn.
6. Không.
7. Không.
8. E2E: số hiện ra ≥ credit thực giữ, với ít nhất một ca văn bản nhiều chữ số.

### H-08 · Tiến độ % + ETA + chẩn đoán operator
1. Có — 11 bước không %, không thời gian, đọc như log.
2. Viral có `/api/render_progress` và cả script "sửa GPU chậm".
3. `_chay_co_tien_do` và `ho_so_chan_doan` **đã có**; thiếu đường lên UI.
4. ASV (`quan_sat.py`).
5. Không.
6. Không.
7. Không.
8. E2E: run đang chạy → mảnh tiến độ có `%`; operator thấy encoder + ×realtime, khách **không** thấy.
9. ⛔ Ràng buộc §12: **không giả ETA.** Chưa đủ dữ liệu tin cậy thì không hiện ETA — hiện `elapsed` là đủ trung thực.

---

## 3. Ba luật cưỡng chế cho mọi mục thu hoạch

**L1 — Không sao chép nguyên văn.** `D:\Viral` là `UNLICENSED`/private. Mọi mục
`ADAPT`/`REIMPLEMENT` đi đường *hiểu hành vi → đặc tả → viết lại*. Con số mượn
(`n_frames=20`, `165 Hz`, `TTL 7 ngày`) là **bằng chứng của người khác** và §18
bắt đo lại trước khi dùng.

**L2 — Không mục nào được lách bảy ranh giới của §1.** Không LLM client riêng,
không VLM client riêng, không TTS sidecar riêng, không tự chọn GPU, không storage
riêng, không billing riêng, không queue riêng.

**L3 — `DEFER` không phải "quên".** Mỗi mục `DEFER` phải có chỗ dành sẵn trong
`V5_UI_INFORMATION_ARCHITECTURE.md` và, nếu là dữ liệu, một trường dành sẵn trong
`ban_dung`. Mở một mục `DEFER` sau này phải là **ký ADR + bật cờ**, không phải
thiết kế lại.
