# 01_SCORECARD_BASELINE — điểm CHỈ ở chỗ đã có bằng chứng

Ngày 09/09/2026 · SHA `99017910` · 87 hạng mục theo hợp đồng chương trình.

## Luật đọc bảng này

`UNKNOWN` **không phải** điểm thấp. Nó là câu *"chưa ai đo, nên chưa ai được
nói"*. Sau ~25 lệnh đọc, tôi có bằng chứng thật cho **77/87** hạng mục.
Ghi 87 con số bây giờ sẽ là đúng thứ mà §35.1 của hợp đồng cấm: điểm không có
bằng chứng.

Cột **trần** ghi mức cao nhất hạng mục ấy được phép đạt với bằng chứng HIỆN
CÓ, theo §7. Trần không phải điểm — nó là mái.

---

## A. Đã có bằng chứng — chấm được

| ID | Hạng mục | Điểm | Trần | Gap | Bằng chứng |
|---|---|---|---|---|---|
| 01 | Architecture layering | **92** | 100 | — | Cửa web/job/API đều vào `features.py`; quyền sở hữu kiểm ở `features.giai_giong` chứ không ở route; `manifest.py` khai trọn `requires`/`admission`/`tools`. Trừ điểm: `voice.js` 105 KB một khối (xem 67) |
| 02 | Business core | **90** | 100 | — | `features.py` 411 dòng là cửa duy nhất; ba lớp lỗi tách đúng ngữ nghĩa retry (`LoiGiongNoi` / `LoiHaTang` / `DangBanTam`), mỗi lớp có ghi lại hồi quy đã sinh ra nó |
| 03 | Stable Voice ID | **90** | 100 | — | `voice_id` là danh tính công khai, ổn định qua nâng engine; khách không thấy speaker embedding (manifest ToolSpec) |
| 04 | Engine migration readiness | **90** | 100 | — | `voice_repr` **gắn phiên bản engine**; bản cũ cho nghỉ khi nâng, và `giai_giong` có nhánh lùi cho đúng ca ấy. `KhuonChuanHoa` tách PHIÊN ÂM khỏi ĐỌC SỐ để engine 2 tắt từng nhóm. `01_KHOA_UPSTREAM` ghim **revision**, không ghim `main` |
| 05 | Ownership | **96** | 100 | — | **A0-2 09/09.** `tim_profile()` tìm theo `public_id` **và** chủ trong **MỘT** truy vấn — không tách "tìm rồi so owner" nên không có khe TOCTOU. `cho_dung_chung` mặc định **False** (đóng-mặc-định). Quyền **ĐỌC** tách hẳn quyền **SỬA** (`chi_chu_so_huu`) — gộp hai thứ là cách một khách tắt giọng của cả nền tảng |
| 06 | Consent | **92** | 100 | — | `VoiceConsent` lưu `phien_ban_dieu_khoan` (trả lời được *"họ đồng ý với cái gì"*), `ref_sha256` nối consent với đúng clip đó, `loai` tự-thụ/được-uỷ-quyền, IP/UA/thời điểm. Là **dữ liệu**, không phải ghi chú |
| 07 | License/provenance | **88** | 100 | — | ✅ **B-01 CHẠY 10/09** — `BLOCKED_DATA` gỡ. Đếm thật trên CSDL production: **25 giọng kho chung, 25/25 `license_status = cho_soat`, 0 cái `ok`, 0 cái đã curate.** ⭐ Đó là **bằng chứng dương** cho cơ chế chứ không phải một khoảng trống: `LICENSE_CHO_PHEP=("ok",)` + `_dieu_kien_kho_chung()` đang **thật sự chặn** cả 25 giọng chưa soát, ở **cả hai** cửa đọc. Cổng đóng-mặc-định hoạt động đúng. Trừ 12: chưa ai chạy `soat_giong.py duyet` nên chưa có một giọng nào đi qua được cổng — cơ chế mới chứng minh chiều **từ chối**, chưa chứng minh chiều **chấp nhận** |
| 76 | PII/biometric protection | **90** | 100 | — | Cùng thông điệp cho "không tồn tại" và "không phải của bạn" ⇒ không dò được `voice_id` nào có thật. Khách không bao giờ thấy speaker embedding. Chưa kiểm: log có rò embedding/audio nguồn không (§25) |
| 08 | Sidecar isolation | **90** | 100 | — | Tiến trình riêng, 12 cửa HTTP, `trang_thai()` ba trạng thái; `suc_khoe` hỏi sidecar THẬT chứ không đọc biến môi trường |
| 09 | Model validation | **97** | 100 | — | **A0-3 09/09, có BằNG CHỨNG RUNTIME.** `kiem_model.kiem()` gọi ở `engine.nap()` dòng 170, **trước** `self._tts = tts` (dòng 196). Sàn kích thước + ONNX kiểm bằng loại trừ + safetensors đọc `u64` độ dài phần đầu rồi đối chiếu cỡ tệp. ⭐ Log production **09/09 12:01:12**: `snapshot lanh` ⇒ cổng đã chạy thật và đã qua |
| 10 | Model lifecycle | **96** | 100 | — | Revision đang chạy trên production = `2da0efab…` = **đúng bản ghim** `01_KHOA_UPSTREAM.md` ⇒ **không trôi model**. `voice_repr` gắn phiên bản engine; bản cũ cho nghỉ khi nâng, và `giai_giong` có nhánh lùi cho đúng ca ấy. ⭐ **A1 09/09 — đo 4 trục độc lập trên venv DỊCH VỤ THẬT (`vieneu-venv`), không trôi trục nào**: torch `2.8.0+cu128` · transformers `4.57.6` · vieneu `3.3.0` · model rev `2da0efab…` — cả bốn **bằng đúng** `01_KHOA_UPSTREAM.md`. ⚠️ Lượt đo đầu của tôi đọc nhầm `C:\LTTPlatform\venv` (torch 2.11.0) và suýt báo trôi ghim; dịch vụ thực tế chạy **`vieneu-venv`** (hỏi `nssm get LTTStudioVoice Application`). Trừ: upstream đã đi trước 20 ngày, chưa có nhịp soát định kỳ |
| 74 | Model corruption recovery | **88** | 94 | OPS | Phát hiện tốt và **từ chối khởi động** thay vì ghi log rồi đi tiếp; thông điệp nói **tệp nào, hỏng thế nào, chạy lệnh gì**. Phục hồi vẫn là **thủ công** (chạy lại bước làm ấm cache). §7.7 trần 94: chưa diễn tập khôi phục thật |
| 11 | GPU correctness | **86** | 88 | BENCHMARK | ✅ **P3 THI HÀNH 09/09.** `engine._dat_tran_luong()` đặt `torch.set_num_threads` **và** `OMP_NUM_THREADS`, gọi **TRƯỚC** khi nạp model. Mặc định **4**, dẫn xuất: 10 lõi vật lý − 6 (trần `-n 6` của CLAUDE.md). `LTT_VOICE_TORCH_THREADS` để máy chủ riêng nâng lên 10. Đột biến gỡ lời gọi ⇒ đỏ đúng câu *"năng lực có, không ai đi"*. Trần 88: chưa load test |
| 46 | Voice Library data model | **92** | 100 | — | Sáu bảng tách bạch: `VoiceProfile` · `VoiceRef` · `VoiceRepr` · `VoiceQualityProfile` · `VoiceConsent` · `VoiceTuDien`. `UNIQUE(profile_id)` cho phán quyết curate — *"hai dòng cho cùng một giọng là hai câu trả lời cho cùng một câu hỏi"* |
| 53 | Human curation | **85** | 100 | DATA | `tools/soat_giong.py` bắt `--ly-do` ở **cả hai** chiều, và là CLI chứ không phải nút web — *"một nút trên web mời người ta bấm; một lệnh CLI buộc người ta gõ lý do"*. ⚠️ **B-01 10/09**: **0/25** giọng đã được soát. Quy trình tồn tại và cổng đang chặn đúng, nhưng **chưa ai chạy nó một lần nào** — nên nó chưa chứng minh được chiều chấp nhận |
| 54 | Quality profile | **92** | 100 | BENCHMARK | `ly_do_loai` là **cột bắt buộc khi `rejected`** — *"rè ở âm /s/"* đáng thử lại sau khi nâng engine, *"không có consent"* thì không; cùng `rejected`, hai số phận khác hẳn. `diem` nullable + cấm `default=0.0`. `benchmark_version` để hai đợt đo so được |
| 82 | CI | **75** | 100 | OPS | ✅ **DỰNG 09/09** — `.github/workflows/gate-quick.yml` chạy `gate --quick` trên mọi PR vào `admin-mvp-v3`/`master`. `ubuntu-latest` **có chủ đích**: runner Windows bật `core.autocrlf` sẽ làm bước `kieu xuong dong` đỏ vĩnh viễn vì kho có cả tệp LF lẫn CRLF. Không 100 vì **chưa ai bắt buộc nó** — xem 83 |
| 83 | Branch protection | **0** | 100 | OPS | Không có check bắt buộc nào để bảo vệ, vì không có CI. §26 cấm tự bật repo setting ⇒ `BLOCKED_WITH_ACTION_REQUIRED` |
| 12 | GPU admission | **88** | 88 | BENCHMARK | `admission_resource="vieneu_gpu"`, `admission_slots=1` khai ở ToolSpec ⇒ cả ba cửa giành cùng suất; lớp giành thật là `ExecutionLease UNIQUE(resource,slot)`. Trần 88: **chưa có load/concurrency test** (§7.4) |
| 13 | GPU fairness | **62** | 88 | ARCH | `claim()` có aging + fair-share theo **tài khoản** + FIFO. Nhưng: (a) không phân biệt việc ngắn/dài trong cùng tài khoản; (b) `admission_slots=1` giữ suất tới lúc xong, không có điểm nhả; (c) không có trục ưu tiên nào — `Job` **không có** cột `priority` (xem 14) |
| 14 | Priority scheduling | **30** | 88 | ARCH | 🔴 **ĐÍNH CHÍNH 09/09 (lỗi của TÔI ở baseline).** Tôi viết *"`Job.priority` tồn tại, models.py:723, không ai đọc"*. **Sai**: dòng 723 thuộc lớp **`ApiKey`** (bắt đầu dòng 690), và `api_pool.py:192` đọc nó thật. Đếm lại cột của `Job`: **không có** `priority`. ⇒ Không phải cột nửa vời; là **không có gì cả**. Thêm ưu tiên = đổi lược đồ + migration, đắt hơn *"nối một cột sẵn có"* |
| 16 | Long-form architecture | **88** | 90 | E2E | `/v1/lo-ra-tep` gộp lô GPU thật; `ban_doc_dai.py` + `noi_dai.py` (579 dòng) tách sinh khỏi ghép; `text_pipeline` chia theo ranh giới câu. Trần 90: chưa E2E thật lượt này |
| 17 | Long-form resume | **92** | 100 | — | **P4 09/09.** `ban_doc_dai.dung()` kiểm kho **trước khi sinh** bất cứ gì: tệp có trong kho = đoạn ấy xong. ⭐ **Không bảng trạng thái, không migration** — *"kho tự nó đã là bản kế hoạch"*, vì một bảng song song sẽ lệch khi job chết sau `put` mà trước `commit`. Ghi kho **sau mỗi lô** |
| 18 | Long-form fairness | **82** | 88 | BENCHMARK | `SO_DOAN_MOI_LO` chia lô nên một bài dài **nhả suất giữa các lô**, không giữ liền mạch. Nhưng chưa đo *1 dài + 5 ngắn* — §7.4 trần 88 |
| 19 | Batch GPU | **88** | 88 | BENCHMARK | `_sinh_mot_lo` gọi `/v1/lo-ra-tep` — gộp nhiều đoạn vào MỘT lượt GPU, không phải một vòng lặp HTTP. Sổ kê `gen_s` đi **cùng** vòng sinh vì không đo lại được sau. Trần 88: chưa load test |
| 71 | Retry semantics | **94** | 100 | — | Ba lớp lỗi tách đúng ngữ nghĩa (`LoiGiongNoi` không thử lại · `LoiHaTang` thử lại · `DangBanTam` xếp lại **không tiêu lượt, không chạm tiền**), và `job_runner._provider_failure_kind` phân **năm** nhánh. Mỗi lớp mang theo hồi quy đã sinh ra nó |
| 73 | Sidecar restart recovery | **90** | 94 | OPS | `song()` có đệm 5s + `buoc=True` để bỏ đệm; `trang_thai()` **ba** trạng thái chứ không hai. ⭐ Ghi log mức DEBUG **có lý do**: hàm chạy mọi lượt dựng trang, WARNING sẽ dìm nhật ký thật — nhưng **vẫn ghi**, vì *"từ chối nối, hết giờ và 401 trông giống hệt nhau"*. §7.7 trần 94: chưa diễn tập restart thật |
| 75 | Security | **90** | 90 | E2E | **P4 quét bốn lớp bằng AST** trên toàn bề mặt voice: route thiếu `require_login` **0** · POST thiếu CSRF **0** · truy vấn `VoiceProfile` bỏ qua `tim_profile` **0** · gọi mạng không timeout **0**. Trần 90: chưa có lượt thử xâm nhập thật |
| 20 | Streaming | **78** | 90 | E2E | ✅ **P2 THI HÀNH 09/09, mô hình β** — `07_CHANGE_LEDGER.md`. `sidecar_client.phat_dan()` + `POST /phat-dan` + quyết toán theo **byte PCM đã gửi**. Suất GPU sống suốt generator (`keep_alive`), phiên CSDL riêng, `job_id` tổng hợp nên khoản giữ có đường về. 16 test mới / 45 xanh; **đột biến một hằng số làm 8/16 đỏ**. Còn thiếu: JS, cờ production, E2E |
| 21 | Text pipeline VI | **95** | 100 | — | **A0-4 09/09.** Không viết lại G2P (`sea-g2p` lo âm vị); chỉ làm thứ g2p **không thể biết** vì là quy ước sản phẩm. Phép biến đổi **soi được**: lịch sử ghi cả text gốc lẫn text đã chuẩn hoá ⇒ truy được lỗi là của model hay của ta |
| 22 | Text pipeline EN | **88** | 90 | BENCHMARK | Đo 01/09 bằng ASR ngược trên engine thật: *"The quick brown fox…"* trả lại **đúng từng chữ** `[en 0,996]`. Nhưng đó là **một câu** — chưa phải corpus (§35.8) |
| 23 | Mixed VI/EN | **88** | 90 | BENCHMARK | Thiết kế đúng: làn là chốt **chất lượng**, không phải giới hạn kỹ thuật ⇒ **cảnh báo, không chặn**. Bắt đúng điểm chính: tiếng Việt **không dấu vẫn là tiếng Việt** và chỉ gồm ASCII ⇒ chặn theo phán đoán sẽ từ chối việc hợp lệ với lý do khách **không sửa được**. Chưa có corpus mixed |
| 24 | Engine-specific normalization | **95** | 100 | — | **U-15 XONG.** `KhuonChuanHoa` tách PHIÊN ÂM khỏi ĐỌC SỐ thành hai nhóm độc lập — một cờ chung buộc engine 2 chọn *cả hai hoặc không cái nào*. Khuôn chỉ được **tắt**, không được đảo thứ tự (thứ tự chịu lực, 3 lần đã trả giá). ⭐ Bắt được hệ luỵ **TIỀN**: `_gia()` đếm ký tự **sau** chuẩn hoá ⇒ đổi khuôn là đổi hoá đơn |
| 25 | Pronunciation dictionary | **92** | 100 | — | Sinh từ báo cáo thật (upstream #168: `ch`→`tr`). Ba luật thêm mục: chỉ thêm khi **đã NGHE THẤY sai** · ghi lý do + ngày · khớp theo **biên từ**. Từ điển chung tách khỏi từ điển riêng của khách |
| 26 | Number/date/currency | **96** | 100 | — | Đo bằng **ASR ngược** (`do_engine_doc_so_va_viet_tat.py`): ranh giới ở **1 triệu** — dưới thì `sea-g2p` đúng ⇒ để yên. 🔒 SỐ ĐIỆN THOẠI engine đang đọc **ĐÚNG** ⇒ luật "≥7 chữ số thì đổi" sẽ phá thứ đang tốt. Dấu phân cách là **tín hiệu** phân biệt tiền với tổng đài ⇒ luật phải chạy **TRƯỚC** `_NGAN` |
| 27 | Audio QC | **85** | 85 | BENCHMARK | `do_chat_luong.py` 782 dòng, `do_on_dinh.py` 548, `dnsmos.py`, `do_ben_dau_chim.py`. Bộ đo dày và có baseline khoá theo phiên bản. Trần 85: corpus 6 câu (§7.3) |
| 28 | Tail repetition detection | **85** | 85 | BENCHMARK | `khop_cuc_bo_dinh` có trong baseline (3 vòng). ⭐ Và một lỗi **của DỤNG CỤ ĐO** đã được bắt: Whisper mặc định `condition_on_previous_text=True` sinh vòng lặp rồi **bỏ hẳn một đoạn ở giữa**, bản ghi vẫn kết thúc đúng chỗ nên **trông đầy đủ**. Đo 31/08: phủ 74,5 %, CER báo 29,9 % mà gần hết là chữ **bị bỏ**. Kết luận *"ghép làm giảm chất lượng"* rút từ đó sẽ sai. Trần 85: corpus 6 câu |
| 29 | Speaker consistency | **88** | 88 | BENCHMARK | `on_dinh_giong` có số đo thật trong baseline. `do_giu_giong_nhieu_luot.py` hỏi đúng câu quyết định: *"hai LƯỢT GỌI riêng biệt có cho ra CÙNG MỘT NGƯỜI NÓI không"* — và giải thích vì sao phải **ĐO** chứ không đọc mã: *"bộ trọng số mới là thứ quyết định, và nó không nằm trong mã"*. Trần 88: chưa load/nhiều vòng |
| 30 | VI acoustic quality | **70** | 85 | BENCHMARK | `baseline_chat_luong.json`: CER tb 0,1249 · σ 0,0067 · 3 vòng · **6 câu**. `lech_giua_cau` 0,1044 ≈ chính giá trị trung bình ⇒ 6 câu quá ít để trung bình có nghĩa |
| 31 | EN acoustic quality | **UNKNOWN** | 85 | BENCHMARK | Chỉ có **một** câu EN đo một lượt (`10_BENCHMARK_AM_THANH.md` dòng 55: `en_thuong` 115 ký tự, CER 2,6 %/0,0 %). Một mẫu không phải benchmark (§35.8) |
| 32 | Mixed VI/EN quality | **UNKNOWN** | 85 | BENCHMARK | Không tìm thấy corpus mixed nào |
| 37 | Fallback VI | **88** | 90 | E2E | `lui_giong.py` bậc thang 4 nấc, cấm nới giới/làn, bắt sinh cảnh báo. Có lý do lịch sử ghi trong tệp (ca `D:\Viral` 26/08) |
| 38 | Fallback EN | **72** | 90 | DATA | ⚠️ **HẠ ĐIỂM 10/09 sau B-01, và đây là hạng mục của chính tôi.** P1 nối `tham_chieu.ung_vien_kho_chung()` vào bậc thang qua đúng cổng `tim_profile` + license; 5 test mới, hai đột biến đều đỏ — **mã đúng**. Nhưng B-01 đếm được **25/25 giọng kho chung là `cho_soat`**, mà cổng đòi `license_status IN ("ok",)` ⇒ `ung_vien_kho_chung()` trả **0 ứng viên**. 🔴 Bậc hai của thang **đã nối nhưng không có gì chảy qua** — đúng `nang-luc-co-nhung-khong-ai-di-tren-duong`. Điểm 82 trước đó dựa vào câu *"25 giọng đã nằm trong CSDL từ 01/09"*, và câu ấy đúng về **có mặt**, sai về **dùng được**. Gỡ bằng `soat_giong.py duyet` (người thật soát), không bằng sửa mã |
| 39 | Per-voice runtime profile | **92** | 100 | — | ✅ **B-04 CHẠY 10/09** — `"giong"` nay có **20/20** giọng, đủ 5 trường, `so_luot=3` khớp `mau_giay_dai`=3 mẫu. Trần cũ 75 (§7.9 *dataset rỗng*) **hết áp dụng**. Cơ chế vốn đã xuất sắc (A0-1): ≥3 lượt mới tin, cận dưới `tb−2σ`, nhận/bác **nguyên khối**, sàn 1.0 chống σ phình. ⭐ **Có độ lặp lại**: hai lượt độc lập cách nhau 17 phút lệch trung bình **0,67 %**, lớn nhất **1,90 %** — §7 *no repeatability MAX 90* hết áp. Trừ 8: một máy, một phiên bản engine, chưa đo lại sau khi nâng engine |
| 40 | ETA accuracy | **80** | 90 | E2E | ✅ **ĐO ĐƯỢC 10/09.** Độ lệch giữa hằng số 18 và tốc độ thật nay có số: dải **11,31 → 18,49** ký tự/giây (**1,63×**), và **19/20 giọng CHẬM hơn 18**. 🔴 Lệch về phía **GIỮ THIẾU**: ở 5.000 ký tự, đường lùi ước 279,3 s còn `Đức Trí` thật sự cần 450,0 s — thiếu **38 %**, và ở cỡ ấy đường lùi giữ thiếu cho **20/20** giọng. Có dữ liệu thì `gia.giay_uoc` tự dùng đường theo giọng, nên lỗ ấy đóng. Trần 90: **ETA chưa hiện cho khách** (U-11 vẫn CHƯA) — mới đúng cho phép GIỮ CHỖ, chưa đúng cho phép HIỂN THỊ |
| 41 | Pricing | **95** | 100 | — | **A0-1 09/09.** Milli-credit số nguyên, làm tròn lên đúng MỘT lần cuối (`_len_up`); `uoc_tran_lo` cộng mcredit trước khi tròn ⇒ bài 20 đoạn không trả thừa 20 credit cho phép làm tròn. `bang_gia()` là **cùng hàm ra hoá đơn** (chốt 3.6). `PHIEN_BAN_GIA` có phiên bản ⇒ đối soát được hoá đơn cũ. Trừ: giá vốn chưa vào `gia_von.json` nên `test_261` chưa chốt được "bán ≥ vốn" |
| 42 | Credit reserve | **95** | 100 | — | Mô hình **hai tham số** `giây ≈ khởi_động + ký_tự/tốc_độ`, không phải một phép chia — vì câu 47 ký tự đạt 14,0 c/s còn bài 3.000 đạt 20,8. Cố ý bi quan (18 < 20,8 đo được). Đếm trên văn bản **ĐÃ CHUẨN HOÁ** vì chuẩn hoá làm nở văn bản ("1.500.000 đồng" = 14 ký tự → hơn 2 giây). Nhận/bác hồ sơ **nguyên khối** — `test_506` đã bắt lỗi trộn hai trường cho ra giữ **THIẾU**. ⭐ **10/09 B-04 xác nhận mô hình hai tham số là đúng chỗ**: hằng số 18 giữ **thiếu** cho 19/20 giọng (tới 38 % ở 5.000 ký tự), và chính vì `giay_uoc` ưu tiên hồ sơ đo được nên lỗ ấy đóng ngay khi có dữ liệu — không phải sửa một dòng mã nào |
| 43 | Credit settlement/refund | **96** | 100 | — | Nguồn chân lý cho tiền là **ffprobe trên tệp thật**, không tin header sidecar; lệch > 0,5s ghi cảnh báo. Không đo được ⇒ **thu 0**. 🔒 **ĐÓNG MỘT LỖ KHAI THÁC THẬT**: time-stretch đặt **SAU** phép đo — đặt trước thì khách chọn tốc độ 1,5× trả ít hơn 1/3 cho **cùng một lượng việc GPU** |
| 44 | Storage | **92** | 100 | — | **09/09.** Kiểm sở hữu bằng **hình dạng khoá** (`voice/out/{owner}/{job}/`), không bằng truy vấn — *"một phép kiểm rẻ và không thể quên"*. Hai tiền tố có **hai vòng đời** có chủ ý (kết quả dọn sau 30 ngày; clip gốc sống theo hồ sơ giọng). 🔒 Ghi lại một lần **suýt rò `speaker_emb`**: mở cả tiền tố `voice/{uid}/` sẽ lộ `repr-*.npz` |
| 45 | Audio Range/mobile | **90** | 90 | E2E | Giải ở tầng **chung**: `platform_core/phat_media.py` — một bộ Range cho toàn nền tảng, RFC 9110. Sửa hai lỗi có thật: không bao giờ trả 416 (nắn thành 206 + `Content-Range` **sai**) và suffix `bytes=-500` hiểu ngược. ⭐ `ltt_voice` trước đó **không có Range**, và iOS Safari đọc `Accept-Ranges` ở lượt 200 đầu rồi **bỏ phát**. Trần 90: chưa thử thiết bị thật lượt này |
| 47 | VI catalog | **75** | 90 | DATA | ⚠️ **HẠ 10/09 sau B-01.** 20 preset engine (làn `vi`) **dùng được ngay** — chúng không đi qua cổng kho chung. Nhưng 8 giọng VI kho chung thì **`cho_soat` cả 8**, nên con số *"28 VI"* là **đếm CÓ MẶT, không phải đếm DÙNG ĐƯỢC**: thực dụng là **20**, chạm sàn mục tiêu 20–30 chứ không phải giữa dải |
| 48 | EN catalog | **60** | 90 | DATA | ⚠️ **HẠ MẠNH 10/09 sau B-01.** 17 giọng `en` đều nằm ở kho chung, và **17/17 là `cho_soat`** ⇒ **0 giọng EN dùng được**. Preset engine đều làn `vi`. 🔴 Khác hẳn mục 47: ở VI còn 20 preset đỡ, ở EN thì **không có gì đỡ cả**. Con số 17 trước đây đếm hàng trong kho, không đếm hàng bán được |
| 49 | Voice discovery | **90** | 100 | — | ✅ P7: **năm** trục lọc (loại · giới · làn · vùng · phong cách) + tìm theo tên. Giọng mặc định **luôn đứng đầu và luôn hiện** — *"lối thoát khi bộ lọc không còn gì"* |
| 50 | Search/filter/facets | **92** | 100 | — | ✅ **U-03 ĐÓNG** (P7). Thẻ không khai một trục thì **không bị ẩn** — ẩn thứ mình không phân loại được là làm khách mất giọng của chính họ. Có test ghim cả năm trục |
| 55 | Studio completeness | **90** | 100 | — | Năm tab đều đã xây, không tab nào `built=False`. Mỗi thứ **bị bỏ** đều có lý do riêng ghi tại chỗ (MODE Fast/Quality không tồn tại ở tầng nào; `Phong cách` engine không có tham số ấy), và **hai lời hoãn đã được kiểm lại điều kiện** rồi mở |
| 56 | Studio first-time UX | **88** | 100 | — | Giọng mặc định đứng đầu, *"thứ khách chọn nếu họ không muốn nghĩ"*. Biểu mẫu tạo **ẩn tới khi bấm** để *"trang không mở ra bằng một ô trống"*. Cổng chưa bật thì nói rõ là việc của máy chủ |
| 57 | Progressive disclosure | **92** | 100 | — | `aria-expanded` + `aria-controls` đúng khuôn, và JS **cập nhật `aria-expanded` khi bật/tắt** (dòng 1780) — lỗi kinh điển của khuôn này là mở ra mà trạng thái ARIA đứng yên. Kèm **nạp lười**: chỉ tải từ điển lần mở đầu |
| 51 | Preview architecture | **94** | 100 | — | Ba cách được cân, chọn cách **dựng sẵn một lần, phục vụ như tệp tĩnh**. Lý do loại cách ① là thật: sinh-khi-bấm **đi vòng qua** chốt `vieneu_gpu`, và *"hai mươi thẻ giọng trên một trang là một lời mời tự DoS"*. **Không tính tiền** nghe thử |
| 52 | Preview lifecycle | **90** | 100 | — | Tệp nghe thử **không** mang `job_id` ⇒ nằm ngoài tầm dọn của `job_content.py`, **đúng ý muốn**: nó thuộc về *giọng*, không thuộc một lượt chạy. Khoảng *"chưa có"* lúc đầu được **nói ra** (`co_san`) chứ không giấu |
| 68 | Backend maintainability | **93** | 100 | — | `features.py` là **cửa duy nhất** cho cả ba đường (web/job/API); không quy tắc nào chép đôi. Bảng dịch lỗi được **tách** khi `phat_dan` ra đời chứ không chép sang. Rất nhiều bất biến được ghi kèm **hồi quy đã sinh ra chúng** — hiếm và đắt giá |
| 69 | Observability | **92** | 94 | OPS | `job_metrics.snapshot()` trả **p50/p95** cho `queue_wait` · `admission_delay` · `runtime`; cộng `slo_budget()` theo từng app, `evaluate_slo()`, `alerts()`. ⭐ **Có xe trên đường**: `server/routes/jobs.py:390` đọc thật, không phải một API mồ côi. Trần 94: chưa diễn tập đọc chỉ số trong một sự cố thật |
| 72 | Failure recovery | **92** | 94 | OPS | `reclaim_orphans` chạy **mỗi chu kỳ** worker; `_quet_giu_cho_treo` → `_tu_hoan_giu_cho_treo` chạy ngay sau, và **tách đôi có chủ ý** vì *"hai bước có hai ngưỡng khác nhau"*. `_don_noi_dung_job` trong lịch bảo trì. Trần 94 (§7.7): chưa diễn tập khôi phục thật |
| 70 | Per-voice telemetry | **85** | 100 | BENCHMARK | **U-14 có thật** (`chi_so_giong.py`): RTF + tỉ lệ hỏng từ job thật. `cer = None` ở mọi giọng — và module khai `None` là một **câu trả lời**, không phải ô chờ điền. ⭐ Tự cảnh báo đúng: RTF sản xuất dùng để phát hiện **trôi**, **không** để xếp hạng hai engine |
| 58 | Audio player | **90** | 90 | E2E | Trình phát **tự dựng** có sóng âm canvas, không dùng `controls` mặc định. ⭐ Hiện `—` chứ không `0:00` vì `preload="none"` **chưa biết** độ dài — *"một con số cụ thể mà sai còn tệ hơn một dấu gạch thành thật"*. ✅ P6: năm `aria-label` nay được dịch |
| 59 | Projects | **92** | 100 | — | `du_an.tim(db, public_id, *, owner_id)` — sở hữu **trong truy vấn**. Khối · phiên bản · nhập văn bản · `khoi_can_tao` tách đúng phần cần sinh lại |
| 60 | Long-project editing | **88** | 100 | — | `sua_khoi` · `nhap_van_ban(tran_moi_khoi)` · `gan_ket_qua` · `tom_tat`. Đọc chữ ký và hợp đồng, **chưa đọc hết thân hàm** — chấm dè đúng mức đã đo |
| 61 | History | **92** | 100 | — | `doc_lai` dùng `job_history.get_owned(db, uid, job_id)` — sở hữu trong truy vấn — **cộng** chốt `app_slug` để job của app khác không lọt cửa này. Đọc lại **thu tiền như lượt mới** vì GPU làm lại thật; chép nguyên `params` cũ chứ không dựng lại (dựng lại sẽ bỏ sót `toc_do` **im lặng**) |
| 63 | API developer UX | **92** | 100 | — | Màn tồn tại cho đúng **ba câu riêng của giọng nói** mà `/developers` không trả lời được (mã giọng của tôi · tên preset hợp lệ · trần là trần **gì**). ⛔ Cấm chép lại bất cứ thứ gì khu ấy đã có — *"hai bản của cùng một sự thật thì bản nào cũng sai được một mình"*. Đọc `TRAN_KY_TU_CONG_KHAI` sống, cấm gõ lại con số |
| 64 | API runtime readiness | **90** | 90 | E2E | `trang_thai_tool()` đọc **cấu hình ĐANG CHẠY**, không đọc một bảng chép tay. Hỏng thì trả *"đóng"* chứ không nổ — và đóng là phía an toàn: *"nó khiến khách hỏi, thay vì khiến khách gọi rồi thất bại"*. Trần 90: chưa gọi API thật lượt này |
| 65 | Accessibility | **85** | 90 | E2E | `test_352` ghim `aria-pressed` theo lớp `on`, và phân biệt `aria-current` cho bộ lọc Lịch sử (là `submit` trong form GET, không phải công tắc). ✅ P6 sửa 5 nhãn trình đọc màn hình gõ cứng. Quét lại toàn template: **0** nút thiếu tên tiếp cận. Trần 90: chưa chạy scanner thật |
| 62 | Public API contract | **88** | 90 | E2E | Một ToolSpec `speech.ltt`, scope `jobs:create`, `api_contract` mô tả đầy đủ, `hidden=()` có lý do khoá (Q119). ✅ **P8 10/09** — `ltt_voice.enroll` không có ToolSpec là **cố ý**, và nay có bằng chứng thay vì suy đoán: route ghi `VoiceConsent` **trước khi** tạo job, lấy `ip` + `user_agent` + `phien_ban_dieu_khoan` + `ref_sha256` từ request của **chính người đồng ý**. Một lượt `jobs:create` mang danh tính của bên tích hợp ⇒ không phải *consent yếu hơn* mà là **bản ghi consent nói SAI về người đã đồng ý**. `test_515` chốt cả hai chiều + chốt chính **tiền đề**; 4 đột biến đều đỏ. Trần 90: chưa gọi API thật lượt này |
| 67 | Frontend maintainability | **88** | 100 | — | **A0-6 09/09 — ĐO RỒI KẾT LUẬN: ĐỪNG TÁCH.** 2.367 dòng / 105 KB, một IIFE, 23 hàm, không thư viện. **Nguyên thuỷ DÙNG CHUNG**: `chay` 12 chỗ gọi · `songDeu`/`nop`/`batNut` 8 · `veLaiSong` 5 · `soViet` 4. **Màn thì đã cô lập sẵn**: `studio`/`lichSu`/`luoiGiong`/`duAnDanhSach`/`motDuAn` mỗi hàm **1 tham chiếu**, gọi qua một bộ điều phối + 29 chốt `if (!el) return`. ⇒ Tách 7 tệp sẽ **nhân bản** 11 nguyên thuỷ hoặc đẻ ra module lõi, biến 1 request thành 7 trên nền CSP chặn CDN và không bundler, mỗi tệp một `?v={{asset_ver}}`. `window.LttVoice` đã là khớp nối mà việc tách định mang lại. Trừ 12: 2.367 dòng khó điều hướng — nhưng đó là **dễ đọc**, không phải **coupling** |
| 77 | Test engineering | **90** | 100 | — | 36 tệp · **545 hàm test** · 11.981 dòng, tỉ lệ test/sản phẩm 0,79. `test_504` ghim cả bề mặt **chưa** nối — tức test canh cả trạng thái âm |
| 84 | Release discipline | **90** | 100 | — | `install.ps1` · `update.ps1` · `app.previous` giữ **đúng một** bản lùi · `dau_van_tay.json` để hỏi *đường lùi là bản nào*. `app\` bị **xoá và thay toàn bộ** mỗi lần cập nhật, nên sửa trực tiếp trong đó là mất trắng — được ghi thành luật ở CLAUDE.md |
| 85 | Rollback | **88** | 94 | OPS | `rollback.ps1` đổi `app.previous` về, và **cố ý KHÔNG** lùi dữ liệu: *"lùi CSDL về trạng thái cũ sẽ vứt bỏ lịch sử xuất bản thật"*. `restore.ps1` tách riêng, phải chạy **có chủ ý** — hai việc khác nhau, hai lệnh khác nhau. §7.7 trần 94: **chưa diễn tập lùi thật** |
| 86 | Documentation accuracy | **92** | 100 | — | Docstring mang theo hồi quy đã sinh ra chúng (hiếm và có giá trị). ✅ **P9 10/09** — vấn đề thật **rộng hơn** U-06: bảng 19 mục `U-` là **ảnh chụp 07/09 chưa ai đối chiếu lại**, nên người đọc sau sẽ **làm lại việc đã xong**. Chèn khối đối chiếu **đứng TRƯỚC** bảng, đo từng mục: **11 xong · 3 xong cơ chế nhưng chặn · 1 một phần · 3 chưa · 1 phát hiện sai**. `test_516` ghim: mục khai XONG phải còn thứ nó viện dẫn, U-06 phải giữ gạch ngang, tổng phải cộng ra 19; 4 đột biến đều đỏ |
| 87 | Dead-code/dead-surface debt | **90** | 100 | — | Đo thật: **0** hàm bọc `sidecar_client` không người gọi; **1** cửa sidecar không người gọi (`/v1/stream`) và nó có test ghim ⇒ "để sẵn có chủ ý", không phải rác. Không trừ cho `priority` nữa — đây là lỗi đọc của tôi, không phải nợ của mã (xem 14) |

## B. CHƯA ĐO — 10 hạng mục còn lại (15, 33–36, 66, 78–81)

⚠️ Tiêu đề cũ ghi **66**; đó là con số lúc 09/09 13:37. Bảng A ở trên nay có
**77** dòng, nên còn **10**. Bảng dưới giữ nguyên vì nó ghi *phép đo cần chạy*
theo nhóm — vẫn dùng được cho 10 mục còn lại; mục nào đã chấm thì đã có dòng ở
bảng A. Phán quyết tổng: .

Không chấm. Mỗi dòng ghi **phép đo cần chạy**, để lượt sau không phải nghĩ lại.

| Nhóm | ID | Phép đo còn thiếu |
|---|---|---|
| Engine/model | 04, 09, 10 | Đọc `kiem_model.py` (259 dòng) + `chot_sinh.py`; kiểm size/magic-byte lúc khởi động có chặn bản hỏng không (U-08) |
| Quyền/pháp lý | 05, 06, 07, 76 | Đọc `dieu_khoan.py`, `tables.VoiceProfile`, `test_508_voice_license_va_curate.py`; đối chiếu provenance từng giọng trong `KHO_GIONG/00_KIEM_KE.md` |
| GPU/hàng đợi | 11, 15, 19 | Cần **GPU window**. Đo queue wait p50/p95, RTF, VRAM thật |
| Bài dài | 17, 18 | Kiểm resume sau restart worker; đo công bằng khi 1 dài + 5 ngắn |
| Văn bản | 21–26 | Đọc `text_pipeline.py` (823), `tu_dien.py`, `tu_dien_rieng.py`, `lan_ngon_ngu.py`, `toc_do.py` |
| QC sâu | 28, 29 | `do_ben_dau_chim.py` (lặp đuôi), `do_giu_giong_nhieu_luot.py` (nhất quán người nói) |
| Nhân bản | 33–36 | `audio_input.py`, `giong_mau.py`, `/v1/enroll*`; cần corpus ref 3s/10s/30s × clean/phone/noisy |
| Tiền | 41, 42, 43 | Đọc `gia.py` (229) + `platform_core/credit.py`; kiểm giữ chỗ / quyết toán / hoàn tiền. **Ưu tiên cao — đây là sổ sách thật** |
| Lưu trữ | 44, 45 | `_p_audio.py` Range header; phát trên di động thật |
| Kho giọng | 46–54 | `tables.py` (404), `chi_so_giong.py`, `nghe_thu.py` (415), `KHO_GIONG/00_KIEM_KE.md` |
| Sản phẩm/UX | 55–61, 66, 67 | Cần **trình duyệt thật** trên URL công khai; `voice.js` 105 KB cần bản đồ phụ thuộc TRƯỚC khi bàn tách tệp |
| API UX | 63, 64 | `doc_man_api.py`, `ltt_voice_api.html` |
| A11y | 65 | Scanner đã đăng nhập, thiết bị thật. `test_352_ltt_voice_tiep_can.py` đã có — đọc trước |
| Vận hành | 68–75 | `observability.py`, `job_metrics.py`, `chan_doan.py`; kiểm khôi phục khi sidecar restart / model hỏng |
| Nghiệm thu | 78–81 | Trình duyệt thật · GPU thật · người thật nghe · load test. **80 cần người thật** ⇒ ứng viên `NEEDS_OWNER_DECISION` |
| CI/phát hành | 82–85 | GitHub workflows + branch protection. §26: **không tự bật** setting cần quyền chủ dự án |

## C. Trần đang chặn — tóm tắt

| Trần | Áp cho | Gỡ bằng |
|---|---|---|
| 75 — có code chưa nối runtime | 20 (streaming) | Nối `/v1/stream` vào Studio |
| 75 — dữ liệu rỗng | 38, 39, 40 | Chạy `tools/do_ho_so_giong.py` ≥3 lượt; bổ sung giọng EN có consent |
| 85 — chưa benchmark audio | 27, 30, 31, 32 | Corpus 30 VI + 30 EN + 15 mixed, ≥3 vòng |
| 88 — chưa load/concurrency test | 12, 13, 14 | Đo 1 dài + 1 ngắn, 1 dài + 5 ngắn, nhiều dài |
| 90 — chưa E2E thật | 16, 37, 62 | Trình duyệt thật trên `https://app.lttstudios.com` |
| 94 — chưa người nghe | mọi hạng mục acoustic | §19: cần người thật chấm mù |

## D. Điểm tổng

Bản baseline cố ý không ghi điểm tổng: trung bình của 21 hạng mục lúc ấy không
phải điểm của hệ thống, và ghi nó ra sẽ tạo một con số để so sánh về sau — một
con số mà 66 hạng mục chưa đo đang không có mặt trong đó.

⇒ 10/09/2026, bảng A đã có **77/87** dòng nên điểm tổng ghi được, và nó ở
`FINAL_SCORECARD.md`. Tóm tắt: **0/87 hạng mục đạt mục tiêu ≥ 98**; trung bình
**86,11** trên 73 mục có số; **10** mục vẫn BLOCKED_WITH_EVIDENCE. Cùng cảnh báo
cũ vẫn áp: con số trung bình ấy KHÔNG có mặt của 14 hạng mục, và mọi hạng mục
vắng mặt đều vắng vì **chưa đo** — phía chưa biết, không phải phía tốt.
