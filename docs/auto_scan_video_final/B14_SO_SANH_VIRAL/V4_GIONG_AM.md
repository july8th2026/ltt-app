# V4 — Sinh giọng · nắn thời lượng · trộn âm · độ to · tách nhạc nền

Thang chấm dùng chung: `00_THANG_CHAM.md` (không sửa, không thêm cột).

**Phạm vi (chốt lại giữa phiên, xem điều phối):** CHỈ so ASV với **module Render**
của Viral — mọi thứ với tới được từ `xu_ly_chon.main()`.

## 🔴 Một chỗ lệch với hướng dẫn điều phối — cần ghi lại

Điều phối bảo bỏ `_demucs_worker.py` vì *"⛔ KHONG ai goi"* (dò bằng
`grep "import <m>"`). **Đã kiểm lại và KHÔNG đúng**: `localize.py:13776-13780`
(`_tach_demucs_1lan`) dựng đường dẫn `os.path.join(THU_MUC_GOC, "_demucs_worker.py")`
rồi SPAWN nó bằng `subprocess` — gọi bằng đường dẫn tệp, không phải `import`, nên
`grep "import _demucs_worker"` không bắt được. `_tach_demucs_1lan` được gọi từ
nhiều nhánh trong `localize.chay()` (dòng 14022/14033/14052/14120/14125), và
`localize.chay()` được `xu_ly_chon.py:1108` gọi trực tiếp. ⇒ **`_demucs_worker.py`
NẰM TRONG module Render**, và các hàng so sánh với nó vẫn giữ trong bảng chính.

Hai tệp còn lại điều phối bảo bỏ thì ĐÚNG, đã tự kiểm lại:
- `cai_omnivoice.py` — KHÔNG được gọi; nó là trình CÀI ĐẶT venv (`_uv`/`uv pip install`),
  runtime OmniVoice của `localize.py` chạy qua một tệp KHÁC (`omnivoice_synth.py`,
  `localize.py:10213`, ngoài 5 tệp giao cho V4) — dời xuống mục "NGOÀI module Render".
- `long_tieng/long_tieng.py` — KHÔNG được gọi; các hàm `long_tieng_piper`/
  `long_tieng_edge`/`long_tieng_capcut`/`long_tieng_omnivoice` mà `localize.py`
  thực dùng là hàm **định nghĩa NGAY TRONG `localize.py`** (trùng tiền tố tên,
  khác hẳn tệp `long_tieng/long_tieng.py` mà tôi đọc — một prototype/CLI độc lập
  không ai gọi từ Render) — dời xuống mục "NGOÀI module Render".
- `mix.py` (`DUNGVIDEO-FULL`) — xác nhận thuộc kho khác hẳn, dời xuống cùng mục.

## Đã đọc / chưa đọc

**Đã đọc (Viral, CHỈ ĐỌC), TRONG module Render:**
`capcut_tts.py` (2.055 dòng, toàn bộ theo khối — auth/RSA đọc lướt, xác nhận lớp
NỐI thuần) · `cat_giong_clone.py` (145 dòng, toàn bộ) · `_demucs_worker.py`
(161 dòng, toàn bộ) · `localize.py` — ĐỌC CÓ MỤC TIÊU (không đọc hết 20.644 dòng):
đầu tệp (chuẩn hoá văn bản TTS, dòng 1-110), khối phát hiện "chưa dịch"/chữ Hán lọt
(dòng 40-110), toàn bộ `_ghep_track_khop` và các hằng số `DUB_*` xung quanh (dòng
~8750-9150, ~11240-11340, ~12640-12990 — nơi gộp câu CapCut và `_ghep_track_khop`
đọc `DUB_GOP_*`), khối gọi `cat_giong_clone`/OmniVoice (~10700-10760), khối trộn âm
cuối + loudnorm (~8378-8460, ~14780-14860, ~19830-19870).

**Đã đọc (ta):** `nan_thoi_luong.py`, `nan_cho_vua.py`, `thoi_gian.py` toàn bộ ·
`am_thanh.py` toàn bộ · `am_master.py` phần lớn · `cao_do.py` toàn bộ ·
`demucs_runner.py` phần lõi (thiết bị/luồng/segment/overlap) ·
`giai_doan_giong.py` phần `_nan_lo` + đường gọi TTS (`doc_mot_doan`, `chu_se_doc`) ·
`giong_noi.py` toàn bộ (mới đọc thêm, lộ ra `text_pipeline.chuan_hoa` ĐÃ được gọi) ·
`apps/ltt_voice/text_pipeline.py` — đọc có mục tiêu (chuẩn hoá số/ngày/tiền/%,
KHÔNG đọc hết 824 dòng) · `apps/ltt_voice/sidecar_client.py` (đường gọi TTS) ·
`ngon_ngu.py` (NHIP + `ty_le_chu_han`).

**⛔ Chưa đọc kỹ / ngoài phạm vi thời gian của V4:** `localize.py` phần còn lại
(~20.500/20.644 dòng — chỉ đọc các khối liên quan trực tiếp tới câu hỏi trung tâm);
`omnivoice_synth.py` (script chạy OmniVoice thật, không nằm trong 5 tệp giao V4,
dù `localize.py:10213` cho thấy nó mới là runtime thật, không phải `cai_omnivoice.py`);
`giai_doan_giong.py` phần còn lại (~1200/1325 dòng); `xu_ly_chon.py`,
`render_worker.py` — chỉ grep để xác nhận biên module, không đọc nội dung.

---

## Bảng — TRONG module Render

| HẠNG MỤC | BƯỚC ASV | VIRAL CÓ GÌ | TA CÓ GÌ | TRẠNG THÁI | GIÁ TRỊ | GIÁ | ĐỀ NGHỊ |
|---|---|---|---|---|---|---|---|
| Xén khoảng lặng ĐẦU/CUỐI/GIỮA ngay trong audio TTS, TRƯỚC khi đo độ dài để quyết định nén | VOICE_SYNTHESIS | `localize.py:9136-9144` (`DUB_TRIM_SIL`, mặc định BẬT) — "như HeyGen/Rask Truncate Silence"; xén nghỉ đầu/cuối + rút gọn nghỉ GIỮA câu của giọng vừa synth, giữ `TRIM_PAD=0,06s` hai đầu chống cụt; mục đích ghi rõ: *"giảm tràn từ NGUỒN → atempo nén nhẹ hơn → giọng tự nhiên hơn"* | ⛔ KHÔNG — đã kiểm `giai_doan_giong.py` (không có `silenceremove`/hàm trim nào) và `giong_noi.doc_mot_doan` (trả thẳng `wav_bytes` từ `sidecar_client.noi`, không lọc); `nan_thoi_luong.py:98-105` CHỈ TRÍCH DẪN ý tưởng của open-dubbing (`_convert_text_to_speech_without_end_silence`), CHƯA implement | THIẾU | 5 | 2 | LẤY NGAY — đây là cơ chế **đứng trước** mọi phép nắn khác trong chuỗi: nếu tệp tiếng của TA có khoảng lặng thừa ở mép, nó tự thổi phồng `giay` đo được đưa vào `nan_cho_vua.ket_luan`/`co_gian_du_khong`, tức RA THÊM đúng loại khiếm khuyết chủ dự án đã báo cho V4 ("một số câu TTS tăng tốc quá nhiều") — mà không cần đổi engine hay đổi bản dịch; hàm thuần (đo RMS + cắt biên), không phụ thuộc mới, không đốt thêm GPU |
| Bậc thang xử lý câu tràn khe: ① nén ≤`DUB_MAX_SPEED`=1,2× → ② (Video Assist) làm chậm VIDEO tới 20% → ③ trôi + đồng bộ phụ đề theo giọng — KHÔNG BAO GIỜ cắt bỏ hẳn một câu | TIMING_ALIGN | `localize.py:9018-9022` — chủ dự án chốt 28/08, nguyên văn: *"sau tăng tốc lên 1,2 không được thì giảm tốc video xuống 20% để giọng có 20% thời gian nói nữa, không được nữa thì trôi nhưng vẫn phải giữ sub, giữ tiếng đồng bộ"*; dòng lịch sử đo A/B đầy đủ ngay phía trên (trần 1,3/1,6/1,25/1,2, đo trên video khách thật, cap-hit giảm từ 46%→5%) | `thoi_gian.py:268-306` (`lap_ke_hoach`) — nén tới `TRAN_TANG_TOC=1,15`, rồi nếu `troi > tran(3 đoạn kế tiếp)` thì **BỎ HẲN tiếng của đoạn đó** (`cat = dai_sau; dai_sau = 0`) — mất một câu để mua lại ngân sách, KHÔNG có tầng "chậm video" (video được COPY nguyên, `D-ASV-03`) và KHÔNG có tầng "trôi mà giữ nguyên nội dung" | KHÁC THIẾT KẾ | 5 | — | ⛔ Không tính điểm mượn (đổi tầng "chậm video" đụng bất biến `D-ASV-03` — copy luồng hình, GIÁ chắc chắn ≥5) — nhưng **ghi rõ cho chủ dự án**: Viral coi "mất câu thoại" là điều KHÔNG được phép ngay cả ở bậc cuối cùng ("trôi... vẫn phải giữ sub, giữ tiếng"), còn `TRAN_TROI_SO_DOAN=3` của ta chọn CẮT HẲN câu khi hết ngân sách — đây là câu hỏi **đánh đổi sản phẩm** (mất câu vs lệch đồng bộ nhẹ), đúng loại câu hỏi phải HỎI theo `CLAUDE.md` luật 2 |
| Mượn khe LẶNG ở CẢ HAI đầu câu (trước lẫn sau), không chỉ đầu sau | TIMING_ALIGN | `localize.py:9044-9083` (`DUB_LEAD`/`DUB_TAIL`, mặc định 0,25s mỗi bên) — đo QUÉT 200 cue thật + bản dịch thật + tốc độ đọc đo thật: LEAD=TAIL từ 0→0,25s giảm tỉ lệ "câu vượt cả trần nén" từ **33,0%→14,0% (−35%)**, đường cong gãy khúc đúng ở 0,25s (qua đó lợi thêm rất ít) | `thoi_gian.py:239-245` (`ngan_sach_doan`) — CHỈ mượn khoảng lặng PHÍA SAU (`ngan_sach = mốc bắt đầu đoạn KẾ TIẾP − mốc bắt đầu đoạn này`), qua `TY_LE_MUON_KHOANG_LANG=0,7`; KHÔNG mượn phía trước | THIẾU | 4 +đo | 4 | LẤY SAU — số đo trực tiếp trả lời một phần câu hỏi trung tâm ("có mượn khoảng lặng không" — Viral mượn RỘNG hơn ta); nhưng đụng bất biến `dat_tai_ms`/mốc trục nguồn của `lap_ke_hoach` (đoạn có thể bắt đầu SỚM hơn `bat` gốc) — cần đối chiếu lại `test_4801`/hợp đồng mốc trước khi đổi, và ảnh hưởng cả giai đoạn 2 (`ke_cat.py`, cắt cảnh) |
| Tách trần nén "THƯỜNG" (mọi câu) khỏi trần nén khi ĐANG ĐUỔI NỢ (chỉ khi đã trễ) | TIMING_ALIGN | `localize.py:9090-9117` — `DUB_MAX_SPEED=1,2` áp cho câu bình thường; `DUB_CATCHUP_MAX=1,4` áp RIÊNG khi trễ tích luỹ vượt `DUB_CATCHUP_THRESHOLD=0,3s`; ghi rõ lý do tách (đo 28/08): gộp hai núm làm cấu hình êm nhất (1,25/1,25) hồi quy về đúng số câu méo như gộp — *"CATCHUP gánh 2 vai nên vô ích"* | `thoi_gian.py:250-258` — DÙNG CHUNG một `TRAN_TANG_TOC=1,15` cho mọi tình huống nén, không phân biệt "câu tự nó tràn" và "đang trả nợ trôi tích luỹ" | THIẾU | 3 | 2 | LẤY SAU — giá trị nằm ở việc TÁCH RÕ hai khái niệm để đo/chỉnh riêng (Viral đã đo A/B rằng gộp chung gây hồi quy), không phải ở việc nới trần; áp cho ta cần đo lại vì hướng ngược khiếm khuyết đã báo (Viral CHO PHÉP nén nhiều hơn lúc đuổi nợ, còn brief V4 muốn ta nén ÍT hơn) |
| Đo độ to bằng `ebur128` (đo) + `volume` (áp) + `alimiter` (chặn đỉnh) thay vì `loudnorm` một lượt cho bước ĐO | COMPOSE / RENDER | `localize.py:19851-19861` — đo thật: `loudnorm` một lượt 52,0s/38,2s cho cùng kết quả (-16,0/-16,1 LUFS) mà `ebur128+volume+alimiter` ra **3,0s/3,0s** — nhanh **12-17×**; cùng đích LUFS/TP | `am_master.py:585-600,827-910` (`_do_am_luong`) — đã ĐÚNG HƯỚNG (đo trước áp sau, `loudnorm print_format=json` cho lượt đo) nhưng lượt ĐO vẫn dùng `loudnorm` (không phải `ebur128`) — tức đã bỏ MỘT lượt `loudnorm` (so với 1 lượt), chưa bỏ CẢ HAI | KHÁC THIẾT KẾ | 2 | 2 | LẤY SAU — vận hành thuần (khách không thấy), nhưng đáng thử vì bước ĐO âm lượng có thể chạy trên MỖI lô (`DOAN_MOI_LO=24`) của một video dài; nếu đổi, cần đo lại độ chính xác `ebur128` so với `loudnorm=print_format=json` trên chính bản phối của ta trước khi thay |
| Chuẩn hoá số/ngày/giờ/tiền/% cho TTS đọc đúng, có PHIÊN ÂM tiếng Anh→Việt | VOICE_SYNTHESIS | `localize.py:44-66` ưu tiên gói `vietnormalizer` (MIT, pip, transliterate: "iPhone→ai-phôn"), lùi `tts_chuan_hoa.py` (175 dòng, port NghiTTS — số/ngày/giờ/tiền/%/số La Mã/số điện thoại → chữ) khi lỗi, lùi no-op khi cả hai lỗi | `apps/ltt_voice/text_pipeline.py` (824 dòng, `chuan_hoa`/`_khoi_doc_so`) — **CÓ tương đương**, gọi THẬT qua `giong_noi.chuan_hoa_van_ban` (dòng 202-227) → `chu_se_doc` → `doc_mot_doan` (dòng 291-306); đọc số/ngày/giờ/%/đồng-VNĐ-USD, có `phien_am` (transliterate, dòng 548-613); SỬA đúng một khiếm khuyết thật ghi trong docstring `chuan_hoa_van_ban` ("bản pha 12": ngày đọc từng ký tự, URL đọc từng chữ, "CPU" đọc từng chữ) | KHÁC THIẾT KẾ (đã có tương đương) | — | — | Không hành động cho phần đã có — ta KHÔNG "đưa bản dịch vào ltt_voice gần như thô" như giả định ban đầu của điều phối; đã tự kiểm và sửa nhận định này |
| … cùng hạng mục trên — HAI khoảng trống cụ thể: số La Mã và số điện thoại | VOICE_SYNTHESIS | `tts_chuan_hoa.py:86-100,151-152` — số La Mã ≥2 ký tự (`XXI`→"hai mươi mốt", tránh nhầm "I"/"V"/"X" lẻ trong tên riêng) và số điện thoại 10-11 số (đọc TỪNG SỐ, không đọc thành một số nguyên khổng lồ) | `text_pipeline.py` — đã grep (`roman`, `\d{9`, `\d{10`, "La Mã"): KHÔNG có nhánh nào cho số La Mã hoặc số điện thoại; một chuỗi La Mã hay SĐT sẽ rơi vào nhánh "số nguyên còn lại" và bị đọc sai (số La Mã) hoặc đọc thành một số cực lớn khó nghe (SĐT) | THIẾU | 3 +đo | 1 | LẤY NGAY — hai hàm thuần, không phụ thuộc mới (có sẵn mã tham khảo để dịch logic, `tts_chuan_hoa.py:90-100,151-152`); rủi ro thấp vì regex hẹp (La Mã ≥2 ký tự, SĐT bắt đầu bằng 0 + 9-10 số) |
| Phát hiện bản dịch "còn chữ nguồn" bằng tỉ lệ ký tự Hán/CJK còn sót | CONTENT_PROCESS | `localize.py:39-46,72-108` (`_ty_le_han`, `_han_la_loi`) — đếm dải CJK, ngưỡng cấu hình qua env (`HAN_GO_NGUONG`), loại trừ đích `zh`/`ja` vì Hán là HỢP LỆ ở đó (`_HAN_HOP_LE`); có ca bug thật đã sửa (06/08): đích `ja` lẫn Kanji hợp lệ nhưng ngưỡng cũ coi là lỗi → xoá trắng bản dịch | `ngon_ngu.py:297-362` (`ty_le_chu_han`, `NGUONG_CHU_HAN=0,15`, `chua_dich_sang`) — CÙNG kỹ thuật (đếm dải Unicode CJK/Hiragana/Katakana/Hangul), ngưỡng ĐÃ ĐO trên dữ liệu thật của ta (đoạn hỏng G17 = 1,00 vs câu Việt lẫn 1 chữ Hán = 0,011 — hai bậc độ lớn, nên ngưỡng không nhạy cảm) | KHÁC THIẾT KẾ (hội tụ độc lập) | — | — | Không hành động — XÁC NHẬN hai bên tự đi tới cùng một giải pháp cho cùng vấn đề (bản dịch còn sót ký tự nguồn); đáng ghi vào bảng để chủ dự án thấy đã có đối chiếu chéo, không phải vì đây là chỗ thiếu |
| Cắt giọng MẪU clone tránh đứt giữa từ (lùi về khoảng lặng gần nhất bằng `silencedetect`) | — (đường OmniVoice, không có bước ASV tương ứng) | `localize.py:10750-10754` gọi `cat_giong_clone.cat(ref, _rc, target=10.0, maxs=12.0)` trước khi đưa mẫu vào OmniVoice; `cat_giong_clone.py:49-128` — ca khách thật: cắt phẳng giữa từ "became" ⇒ giọng CLONE đọc dư âm "came" ở đầu MỌI câu (~250 lần/video); vá bằng lùi cắt về `silence_start` gần nhất + đệm 0,15s | ⛔ KHÔNG — đã tìm `apps/ltt_voice/giong_mau.py`, `apps/auto_scan_video/giong_noi.py`, `rang_giong.py`: không có đường khách TỰ TẢI mẫu giọng để clone (chỉ chọn từ catalog có sẵn) | KHÔNG ÁP DỤNG | 3 | — | Để chủ dự án quyết theo §9 — nhu cầu "khách tải mẫu giọng để clone" chưa tồn tại ở ta; nếu thêm sau, đây là bài học đáng mượn thẳng |
| Bảng tốc độ đọc **riêng từng giọng** để chọn giọng / ước lượng ngân sách | VOICE_SYNTHESIS | `TOC_DOC` (`capcut_tts.py:1280-1360`) — đo THẬT ≥61 giọng; lý do đo (`capcut_tts.py:1266-1278`): *"chênh 53% giữa nhanh nhất và chậm nhất — lớn hơn cả trần nén `DUB_MAX_SPEED=1,3×`"* (số cũ, nay `DUB_MAX_SPEED` đã hạ còn 1,2 — xem hàng bậc thang ở trên); ca khách thật (`capcut_tts.py:1273`): *"dùng sai tốc độ nói của cái khác nên phải nén"* | `nan_thoi_luong.py:123-156` (`AM_TIET_MOI_GIAY`) — MỘT hằng số cho MỌI giọng (`ngon_ngu.NHIP[VI]=3,35`), khoảng đo riêng của ta hẹp hơn nhiều: [3,04;3,51] (~15%, `nan_thoi_luong.py:130`) | THIẾU | 4 +đo | 3 | LẤY SAU — cùng LỚP khiếm khuyết đã báo cho V4, nhưng khoảng đo hẹp của TA (15% so với 53%) làm giảm mức khẩn; cần đo lại trên catalog giọng ASV thực dùng trước khi kết luận |
| Retry lô TTS: phân biệt lỗi TOÀN CỤC (mạng/chặn/từ chối) và CỤC BỘ (lô nặng), chỉ chia đôi lô ở lỗi cục bộ | VOICE_SYNTHESIS | `doc_lo()` (`capcut_tts.py:1720-1822`) — chia đôi CHỈ khi lý do `"hong"`; lỗi `"mang"`/`"chan"`/`"tuchoi"` KHÔNG chia (đo thật: chia lúc mất mạng "kẹt 72% suốt >10 phút"); hạn giờ gốc `_han` truyền xuyên đệ quy | `_nan_lo()` (`giai_doan_giong.py:1055-1171`) — retry PHẲNG tối đa `LAN_XIN_NAN_LO=3` cho MỌI loại lỗi gộp một nhánh `except` (dòng 1144-1154), không phân loại, không chia lô | THIẾU | 2 | 3 | LẤY SAU — đối tượng gọi khác (CapCut cloud rate-limit vs LLM nội bộ), cần đo lỗi thật của `ai.goi_tinh_tien` trước khi mượn nguyên khuôn |
| Đo giới tính giọng bằng YIN thay tự-tương-quan (NCCF) — né lỗi quãng tám | AUDIO_PREPARE | `capcut_tts.py:930-953` — tự-tương-quan trần đo "nam" ra 326Hz (=2×F0 thật); chuyển YIN sửa đúng lỗi; ngưỡng 175Hz hiệu chuẩn trên 100 giọng, sai 7/100 | `cao_do.py:121-124,194-210` — dùng `torchaudio.functional.detect_pitch_frequency` (chính NCCF); TỰ ghi nhận rủi ro lỗi quãng tám (`cao_do.py:51-56`, đo 23/09: sin 440Hz→~219Hz), giảm nhẹ bằng cửa năng lượng chứ chưa đổi thuật toán | THIẾU | 4 +đo | 3 | LẤY SAU — rủi ro đã tự đo, nhưng `gioi` chỉ là một mặt trong ba của `AUTO_MATCH`, có đường lui (`ho_so_noi_dung`) |
| `--overlap` demucs hạ xuống 0,1 để tăng tốc 15-20% | AUDIO_PREPARE | `_demucs_worker.py:54-56,63-64` — opt-in qua `DEMUCS_OVERLAP` env, mặc định giữ hành vi cũ; đánh giá định tính "không nghe ra seam", không phải đo khách quan mù | `demucs_runner.py:200-203` (`CHONG_LAP=0,25` cố định, không đọc env); `buoc_phan_doan()` dùng chính hằng số này để căn lưới khối tách (đã đo 03/09: lệch lưới → lệch -42,7 dBFS ở ranh khối) | THIẾU | 2 +đo | 2 | LẤY SAU (lệch công thức — máy A production đã treo 2 lần do CPU/GPU quá tải; giảm 15-20% ở bước nặng nhất đáng thử, nhưng cần đo lại vì đánh giá "không seam" của Viral là định tính) |
| `--segment` nhỏ để chặn OOM RAM/VRAM khi tách nhạc bài dài | AUDIO_PREPARE | `_demucs_worker.py:46-53` — `--segment 7` mặc định qua CLI demucs (`DEMUCS_SEGMENT` env) | `demucs_runner.py:417-540` (`tach_theo_khoi`) — TA tự chia FILE ở lớp NGOÀI (không đụng tham số nội bộ model), đệm `PHU_GIAY=10` mỗi khối | KHÁC THIẾT KẾ | — | — | Không hành động — hai cách giải cùng nhu cầu, khác kiến trúc (Viral: CLI subprocess; ta: `apply_model` trong tiến trình) |
| GPU OOM tự động lùi CPU, âm thầm chạy tiếp | AUDIO_PREPARE | `_demucs_worker.py:85-121` — bắt lỗi chứa "out of memory"/"cuda", tự gọi lại `_run("cpu")`, KHÔNG dừng job | `demucs_runner.py:339-390` (`ThieuCard`, `chon_thiet_bi`) — CẤM lùi CPU im lặng khi đã cấp GPU cho job, ném lỗi tường minh | KHÁC THIẾT KẾ | — | — | CỐ Ý KHÔNG — nguồn: docstring dẫn `V4_RESOURCE_CPU_GPU_POLICY` ("no silent CPU fallback in production if GPU is required"); đúng cho ta vì máy dùng CHUNG (nhiều job tranh 1 GPU qua lease), sai giả định một-người-dùng của Viral không còn đúng ở SaaS |

---

## ⛔ NGOÀI module Render (giữ lại tham khảo, ⛔ không tính điểm)

Ba tệp sau ĐÃ đọc (trước khi biết phạm vi thu hẹp) nhưng KHÔNG với tới được từ
`xu_ly_chon.main()` — không đối chiếu điểm, chỉ ghi lại phát hiện đáng chú ý:

- **`long_tieng/long_tieng.py`** (605 dòng) — một pipeline lồng tiếng ĐƠN GIẢN/CŨ,
  đứng độc lập, KHÔNG được `localize.py`/`xu_ly_chon.py`/`render_worker.py` gọi.
  Đáng chú ý: `dung_track()` (dòng 432-472) dùng trần tăng tốc CỨNG `tempo =
  min(1.6, dur/slot)` — KHÔNG có mô hình nợ/mượn khoảng lặng nào (chỉ đặt nối
  tiếp `gap = start - cursor`), lỏng hơn nhiều so với cả `DUB_MAX_SPEED=1,2` hiện
  hành của Render LẪN `TRAN_TANG_TOC=1,15` của ta. Bằng chứng: một tệp mang ĐÚNG
  TÊN việc ASV làm (lồng tiếng) vẫn có thể KHÔNG nằm trên đường Render chạy thật —
  bài học cho chính cách đọc mã tham khảo, không riêng bảng này.
- **`cai_omnivoice.py`** (142 dòng) — script CÀI ĐẶT (`.venv_omnivoice`, GPU pin
  theo compute capability), không phải dây chuyền. Runtime OmniVoice thật của
  Render là `omnivoice_synth.py` (`localize.py:10213`), KHÔNG nằm trong 5 tệp
  giao cho V4 — chưa đọc.
- **`D:\FULL AUTO VIDEO\DUNGVIDEO-FULL\engine\audio\mix.py`** (174 dòng, kho khác
  hẳn) — cố ý KHÔNG loudnorm giọng, chỉ loudnorm nhạc nền rồi duck theo giọng
  (`sidechaincompress threshold=-24dB:ratio=12:attack=15:release=600`), `amix
  normalize=0` (giống cách `am_master.py` của ta tránh ffmpeg tự chia trung bình).
  Không so điểm vì không phải Viral / không phải module Render.

---

## ⛔ Chưa kiểm được

- **`omnivoice_synth.py`** — runtime OmniVoice thật (`localize.py:10213`), ngoài
  5 tệp giao V4; `long_tieng_omnivoice` (`localize.py:10705`) gọi nó nhưng nội
  dung file chưa đọc.
- **`giai_doan_giong.py` phần còn lại** (~1200/1325 dòng) — chỉ đọc phần liên
  quan trực tiếp tới so sánh với `_ghep_track_khop`/`capcut_tts.doc_lo`.
- **`apps/ltt_voice/text_pipeline.py` phần còn lại** (~750/824 dòng) — chỉ đọc
  khối đọc số/ngày/%/tiền để so với `tts_chuan_hoa.py`; chưa đối chiếu khối
  `phien_am`/từ điển riêng với phần "iPhone→ai-phôn" của `vietnormalizer` (gói
  pip, KHÔNG vendor trong `app-src`, không đọc được source từ đây).
- **`noi_lo`/`noi_dai`** trong `apps/ltt_voice/sidecar_client.py` (dòng 272, 280)
  tồn tại nhưng `giai_doan_giong.py` chỉ gọi `sidecar_client.noi` đơn lẻ từng
  đoạn — chưa rõ vì sao hai hàm lô không được dùng ở ASV, và chưa biết sidecar
  nội bộ có giới hạn kiểu "shark block" của CapCut hay không.
- **Giá trị số hiện hành của `HAN_GO_NGUONG`** (ngưỡng chữ Hán lọt phía Viral) —
  đọc thấy tên biến và cách tắt (`HAN_GO_NGUONG=0`) nhưng không tìm được dòng
  gán giá trị mặc định bằng `grep` trực tiếp trong thời gian cho phép.
