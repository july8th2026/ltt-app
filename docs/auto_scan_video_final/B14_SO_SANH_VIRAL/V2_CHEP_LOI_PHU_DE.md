# V2 — Chép lời · chia đoạn · phát hiện dải chữ · OCR · phụ đề

**Làn V2**, thang chấm dùng chung ở `00_THANG_CHAM.md`. ⛔ Không sửa mã, ⛔ không
chạy gì — chỉ đọc `D:\Viral\resources\app-src` (CHỈ ĐỌC) + tra chéo phía ta.

🔴 **PHẠM VI CHỐT LẠI (điều phối, sau khi bảng dưới đã viết xong):** chỉ so
ASV với **module Render** của Viral — biên là *mọi thứ với tới được từ
`xu_ly_chon.main()`*. `_whisper_worker.py` và `_phan_tich_srt.py` **không ai
trong module Render gọi** → hai hàng dựng từ hai tệp này đã DỜI xuống mục
`## ⛔ NGOÀI module Render` ở cuối tệp, không tính điểm. Đường ASR **thật** của
module Render là `phu_de.py::_transcribe`, do `localize.py:31` gọi (`import
phu_de  # tái dùng WhisperModel + _ts + _dich_vi`) — đã xác minh trực tiếp
trong `localize.py` (đọc thêm ngoài 6 tệp được giao, chỉ để xác nhận đường gọi
thật, không đọc gì khác của tệp đó).

## Đã đọc / chưa đọc (thật)

- **Đọc kỹ, có neo:** `capcut_asr.py` (551, trọn), `dai_sub.py` (357, trọn), `phu_de.py`
  (~85%: toàn bộ khối GPU/model/khoá, thiếu khối `_dich_vi`/`_ts` chi tiết
  dòng 287–680), `diarize_pitch.py` (dòng 1–213 kỹ; phần `pyannote`/`ECAPA`/
  `_cluster2`/`_emb_camplus*`/`gan_gioi_tinh` :133–848 chỉ đọc mục lục hàm,
  ⛔ chưa đọc thân hàm).
- **Đọc một phần:** `dai_sub_rapid.py` (2.415 dòng — đọc kỹ :1–260 và
  :1470–1580, phần clustering track :260–1470 và pha đọc SRT :1580–2415 ⛔
  CHƯA đọc), `ocr_text.py` (2.521 dòng — đọc kỹ :1217–1276 và :1683–1730, còn
  lại (`_tien_xu_ly`, `_RapidV6`, `_doc_det_rec`, `_go_dau_duoi_lap`,
  `_go_chu_nen_tang`, `_loc_wm_lap`, `_loai_vung_tay`, `ocr_dong` lắp ráp
  cuối) ⛔ CHƯA đọc).
- Đối chiếu phía ta bằng grep + đọc đoạn liên quan trong `apps/auto_scan_video/
  do_vung.py`, `nguon_loi.py`, `ban_ghi.py`, `cat_doan.py`, `cao_do.py`,
  `apps/autosubvideo/whisperx_runner.py`, `transcription.py` — ⛔ chưa đọc
  trọn các tệp này, chỉ phần liên quan trực tiếp tới hàng đang chấm.

---

## Bảng

| HẠNG MỤC | BƯỚC ASV | VIRAL CÓ GÌ | TA CÓ GÌ | TRẠNG THÁI | GIÁ TRỊ | GIÁ | ĐỀ NGHỊ |
|---|---|---|---|---|---|---|---|
| Kích thước chunk cho ASR batched | chép lời (`giai_doan_chep_loi`) | `phu_de.py:713-722` — ép `chunk_length=10` khi bật `BatchedInferencePipeline` (mặc định thư viện 30s). Đo thật: mặc định 30s dính bug `faster-whisper#1270` (gộp đoạn sai khi VAD vượt max_speech) → **mất 5,6% chữ THẬT** (860/15428 ký tự); `chunk_length=10` → 109% chữ so với non-batched, ảo giác 0,6% | `apps/autosubvideo/whisperx_runner.py:104-107,121,127` — `chunk_size` **không khai**, chạy mặc định `whisperx/asr.py:204 chunk_size=30`; chính ASV tự ghi trong bản ghi tham số: *"chính con số đó là thứ đã sinh ra khối ~30 giây"* | THIẾU | 5 +đo (đúng khiếm khuyết đã báo: mất 24 giây thoại) | 1 (một tham số, không phụ thuộc mới) | LẤY NGAY |
| `repetition_penalty` chống lặp câu khi batched | chép lời | `phu_de.py:723-731` — `WHISPER_REP_PEN=1.1` mặc định khi batched bật (batched không có context-pass giữa chunk 30s → dễ kẹt lặp). Đo thật: số lần lặp 10→3 (−70%), giữ 106% chữ, không chậm thêm | không thấy `repetition_penalty` trong `whisperx_runner.py`/`transcription.py` | THIẾU | 3 +đo (khách thấy được nếu gặp — chưa ai báo lặp câu trên ASV) | 1 | LẤY SAU (đi kèm hàng chunk ở trên, cùng lớp gọi) |
| ASR cloud CapCut phân biệt "không lời" (kết luận) khác "lỗi tạm thời" (thử lại được) | chép lời | `capcut_asr.py:24-61,428-479` — `CapCutKhongLoi` (empty_reason cố định, KHÔNG thử lại) tách khỏi `CapCutLoi` (mạng/API, thử lại 2 lần). Đo thật trên audio câm: đường ép Whisper ra **1 cue BỊA** (`优优独播剧场——YoYo Television Series Exclusive` — bản hiệu kênh) → **mất sạch 51 phụ đề** đúng lẽ có, trong khi đường CapCut kết luận "không lời" đúng và không dịch/dub nhầm nhạc nền | `apps/auto_scan_video/nguon_loi.py:1-44` — quyết định 26/09 (có nguồn): **một đường duy nhất** `voice→voice` qua whisperx, không đọc chữ, không thêm nguồn ASR thứ hai. Hallucination-trên-im-lặng phía ta được bắt **sau khi chạy** bằng `ban_ghi.py:305-343 nghi_ao_giac` (CPS>30 + zero mốc từ, đo trên 187 đoạn thật: 0 đoạn chạm, ca ảo giác đo được 294,1 kt/s) | KHÁC THIẾT KẾ | — | — | ⛔ KHÔNG LẤY (thêm nguồn ASR thứ hai trái quyết định 26/09) — nhưng ca đo của Viral là bằng chứng độc lập cho ĐÚNG cơ chế hallucination mà `nghi_ao_giac` đang chặn |
| Dải phụ đề vs bảng tên HUD/texture — lọc chữ THẬT bằng hình học nét | phát hiện dải chữ (`do_vung`) | `dai_sub_rapid.py:97-148` — lọc 2 lớp trước khi nhận 1 cụm cột là "chữ": (a) Stroke Width Transform xấp xỉ (`connectedComponentsWithStats`+`distanceTransform`, hệ số biến thiên bề rộng nét ≤0,6, ≥3 connected-component) loại texture/vải dính liền; (b) trong các cụm đã qua lọc, ưu tiên cụm có **tâm ngang gần 0,5** (đo thật: tâm phụ đề = 0,500, tâm chữ trên áo = 0,167) | `apps/auto_scan_video/do_vung.py:1-46,240-289` — chỉ Laplacian-edge × std theo thời gian (V4b), KHÔNG SWT, KHÔNG lọc tâm-ngang. Nghiệm thu 25/09 trên 2 phim thật tự ghi: **không phân biệt được** dải phụ đề với bảng tên HUD ("cả hai đều là chữ trắng viền đen, đổi theo thời gian"); tăng khung mẫu 18→48 KHÔNG sửa được — tự nhận là **giới hạn phương pháp** → vì vậy `do_vung` chỉ GỢI Ý, không tự động che | THIẾU | 4 +đo (khiếm khuyết TA đã đo — nghiệm thu 25/09 — khách chưa báo) | 2 (hàm thuần thêm vào V4b sẵn có, `connectedComponentsWithStats`/`distanceTransform` đã có trong `cv2`, không phụ thuộc mới) | LẤY NGAY |
| Bù biên dải OpenCV hẹp hơn dải thật | phát hiện dải chữ | `dai_sub.py:153-165` — `CHE_OPENCV_BU=0.015`, đo trên video H=1280: RapidOCR 73,5–82,1% vs OpenCV (bản thô) 74,9–80,7% | `apps/auto_scan_video/do_vung.py:253-259` — hằng `BU_MOI_DAU=0.015`, comment dẫn thẳng số đo của Viral | ĐÃ MƯỢN | — | — | — |
| Ôm sát dải che vào chữ thật (viền trắng-cạnh-đen) | phát hiện dải chữ | `dai_sub.py:188-252` `_om_sat_vien` — ngưỡng thích nghi 20% đỉnh mật độ nét, đo: hộp sub 1 dòng 154px→90px | `apps/auto_scan_video/do_vung.py:264-289,543` — cùng tên hàm `_om_sat_vien`, hằng số khớp gần 1:1 (`NGUONG_TRANG=190/NGUONG_DEN=70`, `SAN_MAT_DO/TI_LE_DINH_VIEN=0,015/0,20`) | ĐÃ MƯỢN | — | — | — |
| Tách đoạn theo TEXT ĐỔI (so khớp OCR liên tiếp) khi dò dải động | chia đoạn / phát hiện đổi đoạn (bối cảnh 28/09) | `dai_sub_rapid.py:190-213` (`_norm_txt`/`_txt_giong` — chuẩn hoá theo hệ chữ nguồn, so khớp tiền/hậu tố hoặc `SequenceMatcher≥0,6`) + `:1523-1528` (tách segment khi `not _txt_giong`). Đo thật: sửa bug gộp NHẦM 6 câu khác nhau (cùng căn giữa X) thành 1 khối "che dài 13,5s" | ⛔ KHÔNG tìm thấy cơ chế tương ứng trong phạm vi đã đọc — `do_vung.py` tự xác nhận "đọc CHỮ là việc đã bỏ" (`nguon_loi.py:43`); chưa thấy tệp nào triển khai quyết định 28/09 "bật lại `use_rec` để phát hiện đổi đoạn" | THIẾU | 4 +đo (đúng thuật toán lõi cho quyết định 28/09, tự nó khách không thấy nhưng ngăn sai-nhóm-đoạn) | 2 (hàm thuần, ăn theo OCR engine nếu 28/09 đã bật `use_rec`) | LẤY NGAY (nếu/khi có nơi triển khai 28/09) |
| Đồng thuận đa khung cho 1 dòng OCR (majority vote) | OCR | `ocr_text.py:1683-1728` `_chot_bo_phieu` — đa số theo CHUỖI (không theo ký tự — đã thử+gỡ vì "bịa chữ": vote ký tự sửa 4 câu nhưng làm SAI 1). Hoà phiếu → phân biệt bằng VỊ TRÍ phần thừa (đầu=rác/watermark giữ ngắn, đuôi=đọc dần giữ dài) | ⛔ không thấy (chưa có nơi đọc OCR nhiều khung cho 1 dòng trong phạm vi đã đọc) | THIẾU | 3 +đo (chất lượng đầu vào cho quyết định đổi đoạn; khách không thấy trực tiếp) | 2 | LẤY SAU (phụ thuộc có đọc nhiều khung/dòng hay không) |
| Lọc watermark/tên kênh theo HÌNH DẠNG cue (không theo tần suất) | OCR | `ocr_text.py:1217-1276` `_la_ten_kenh`/`_go_ten_kenh` — bắt cue chỉ còn ký tự vô nghĩa sau khi gỡ @handle/tên nền tảng (bắt được cả watermark chỉ xuất hiện 0,5% số cue — dưới ngưỡng tần suất 20% của tầng khác); có "van an toàn": không bao giờ bỏ quá nửa số cue (nghi hiểu sai video) | ⛔ không thấy | THIẾU | 3 +đo | 2 | LẤY SAU |
| Phân vai (diarization) nhiều giọng nam/nữ trong 1 video | — | `diarize_pitch.py` toàn bộ (`phan_da_giong`, pyannote segmentation+embedding+cluster :133-777) — nền cho tính năng "1 video 2 giọng" | — | CỐ Ý KHÔNG | — | — | ⛔ KHÔNG LẤY — nguồn: rút 22/09, sản phẩm là MỘT giọng thuyết minh (đã chốt, nêu trong brief điều phối B14) |
| Xác định giới tính giọng qua F0 (chọn giọng TTS) | — | `diarize_pitch.py:32-77` — đo F0 **theo từng câu** (cho đa giọng), highpass 85Hz cắt BGM, dải hợp lệ [70,450]Hz, median, ngưỡng thích ứng qua k-means 2 cụm trên toàn video hoặc 165Hz cứng, hysteresis theo câu liền trước | `apps/auto_scan_video/cao_do.py:96-227` — đo F0 **một lần** trên cả stem `vocals` (đủ cho sản phẩm 1-giọng), **giữ dải tìm mặc định thư viện 85–3400Hz** (đo thật 23/09: bó hẹp làm thuật toán khoá nhầm hoạ âm/ước số — kết luận NGƯỢC với việc Viral thu hẹp dải), lọc bằng CỬA NĂNG LƯỢNG (phân vị 95 tự chuẩn theo mức thu) thay vì cắt tần số, median, vùng chồng 165–180Hz để TRỐNG (không đoán), nguồn Baken & Orlikoff | KHÁC THIẾT KẾ | — | — | ⛔ KHÔNG LẤY — khác bài toán (đa giọng theo câu vs một giọng theo cả video) và cách ta chọn dải tần đã có đo riêng, ngược hướng với Viral, không có bằng chứng Viral đúng hơn cho ĐÚNG bài toán của ta |
| Khoá liên-tiến-trình quanh bước GPU Whisper (multi-lane) | — | `phu_de.py:920-1038` `gpu_serialize_gate` — file-lock + heartbeat 30s + dò mồ côi qua PID + token chống cướp nhầm lock | `platform_core/gpu_lease.py` — lease qua CSDL, có sổ sách thật | KHÔNG ÁP DỤNG | — | — | ⛔ KHÔNG LẤY — luật kho cấm đề nghị đổi `gpu_lease.py` (CLAUDE.md, brief B14) |
| `ocr_text` nạp MUỘN (import trong hàm, không ở tầng module) trong module Render | OCR / kiến trúc | `localize.py:2595` — dòng comment tường minh: *"PHẢI import tại đây: localize KHÔNG import ocr_text ở tầng module"* (trong `_khoa_gpu_neu_can`, chỉ import khi `VC_GPU_SERIALIZE=1` VÀ thật sự cần dò `ocr_se_dung_gpu()`); 3 lời gọi khác (`:1229`, `:2561`, `:2803`) cũng import cục bộ trong hàm, không ở đầu tệp. `ocr_text.py` là module NẶNG (nạp RapidOCR/onnxruntime/CUDA dll) — nạp muộn = chỉ trả giá tải khi bước đó THẬT SỰ chạy (video không hardsub/không cần khoá GPU thì không đụng `ocr_text` bao giờ), và né vòng import nếu `ocr_text` từng nhập ngược lại thứ gì đó ở `localize` | ⛔ chưa kiểm — cần biết `apps/auto_scan_video` có import OCR-engine (RapidOCR tương đương) ở tầng module hay theo yêu cầu; không có trong 6 tệp Viral được giao nên không tự xác nhận phía ta ở đây | ⛔ chưa kiểm được | — | — | — |

---

## ⛔ Chưa kiểm được

- **`no_speech_threshold`/`compression_ratio_threshold`/`hallucination_silence_threshold`/`initial_prompt` trên đường Whisper thật của module Render**: `phu_de.py::_transcribe(model, audio, log=None, **kw)` chỉ NHẬN kwargs qua `**kw`; nơi GỌI thật với các tham số này (`localize.py::_transcribe_thu`, được `localize.py:31` gọi qua `import phu_de`) nằm **ngoài** 6 tệp được giao. Grep xác nhận **không tệp nào trong 6 tệp Viral được giao** có chuỗi `initial_prompt`/`no_speech`/`compression_ratio`/`vad_filter` — các tham số này (nếu có) chỉ được đặt ở `localize.py`, ⛔ không đủ neo để ghi hàng dù đây chính là đường ASR thật của module Render.
- **`without_timestamps=False` (bắt buộc khi dùng `BatchedInferencePipeline` gốc)**: không rõ có áp dụng được cho kiến trúc `whisperx.FasterWhisperPipeline` của ta hay không (whisperx tự quản batch khác cách Viral gọi `faster_whisper.BatchedInferencePipeline` trực tiếp) — cần đọc `whisperx/asr.py` (thư viện ngoài, không thuộc phạm vi 6 tệp) để xác nhận trước khi ghi thành hàng.
- **75% `dai_sub_rapid.py`** (clustering track :260–1470, pha đọc SRT hoàn chỉnh :1580–2415) và **90% `ocr_text.py`** (`_tien_xu_ly`, `_RapidV6`, `_doc_det_rec`/`_doc_rec`, `_go_dau_duoi_lap`, `_go_chu_nen_tang`, `_loc_wm_lap`, `_loai_vung_tay`, lắp ráp cuối `ocr_dong`) chưa đọc — có thể còn phát hiện khác trong đó.
- **Phần thân các hàm `pyannote`/`ECAPA`/`_emb_camplus*`/`_cluster2` sử dụng thế nào trong `gan_gioi_tinh`** (`diarize_pitch.py:647-848`) — chỉ đọc mục lục hàm, không đọc thân; không cần cho việc phân biệt "phân vai (CỐ Ý KHÔNG)" khỏi "cao độ (KHÁC THIẾT KẾ)" ở trên nhưng có thể còn chi tiết kỹ thuật khác.
- **Nơi triển khai quyết định 28/09 "bật lại `use_rec` để phát hiện đổi đoạn"** phía ta: không tìm thấy trong `apps/auto_scan_video/do_vung.py` (tự xác nhận không đọc chữ) hay bất kỳ tệp nào grep được (`use_rec`, `RapidOCR` chỉ xuất hiện trong comment dẫn nguồn Viral, không phải lời gọi thật) — có thể việc này thuộc phạm vi một làn khác hoặc chưa viết mã.

---

## ⛔ NGOÀI module Render (giữ lại tham khảo, ⛔ không tính điểm)

Điều phối chốt lại phạm vi SAU KHI hai hàng dưới đây đã viết xong (xem đầu
tệp): `_whisper_worker.py` và `_phan_tich_srt.py` không ai trong module Render
(mọi thứ với tới được từ `xu_ly_chon.main()`) gọi tới. Dời nguyên văn xuống
đây, không xoá công sức, không tính vào bảng điểm.

| HẠNG MỤC | VIRAL CÓ GÌ | TA CÓ GÌ | TRẠNG THÁI | GHI CHÚ |
|---|---|---|---|---|
| Subprocess cô lập + kill cứng khi Whisper treo (cuDNN/GPU deadlock) | `_whisper_worker.py` (87 dòng, trọn) — chạy trong tiến trình con RIÊNG vì "3668s cho video 4 phút = deadlock native, in-process KHÔNG kill nổi (hang trong C++ không nhả GIL, không raise nên fallback GPU→CPU cũ vô hiệu)"; giao thức heartbeat qua dòng log (`LOG:`/`SEG|`/`ASRDONE|`/`ASRERR|`), cha coi "không dòng nào > HB giây" = treo → kill | `apps/autosubvideo/transcription.py:29-42,142-159` — đã có `subprocess.Popen` cô lập + `taskkill /PID ... /T /F` khi timeout (kill cây tiến trình) | KHÁC THIẾT KẾ (đã có tương đương) | Module gọi hàm này (`localize.py` đường KHÔNG dùng `_whisper_worker.py` — xác nhận qua `localize.py:31` gọi thẳng `phu_de`) không thuộc module Render; giữ hàng vì công sức đọc đã bỏ ra và vì bài học "cô lập tiến trình khi ASR có thể deadlock" vẫn đúng nói chung. |
| Ngưỡng CPS (tốc độ đọc) cho phụ đề | `_phan_tich_srt.py:50` (62 dòng, trọn) — ngưỡng CPS>25, nhưng đây là **script scratch cá nhân** (đường dẫn cứng máy riêng `C:\Users\vannh\...`), không phải mã sản phẩm, không nằm trong module Render (không ai `import` nó), chỉ dùng đo thủ công một lần ngoài luồng | `apps/auto_scan_video/cat_doan.py:62,109` `KY_TU_MOI_GIAY=9` — nguồn ngành (Netflix/BBC "Adult programs: up to 9 characters/second"); `ban_ghi.py:305` `NGUONG_KY_TU_MOI_GIAY=30` riêng cho nghi ảo giác | KHÁC THIẾT KẾ | Ngay cả khi tính điểm, kết luận không đổi: ngưỡng của ta chặt hơn và có nguồn ngành; ngưỡng Viral chỉ là số đo tạm của một script cá nhân. |

---

*SHA sẽ ghi trong commit message.*
