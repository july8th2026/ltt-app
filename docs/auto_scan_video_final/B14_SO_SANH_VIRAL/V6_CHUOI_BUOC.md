# V6 — CHUỖI BƯỚC: `localize.chay()` ↔ 13 giai đoạn của ASV

## Tôi đọc được bao nhiêu, và ⛔ chưa đọc gì

- **Chiến lược:** ⛔ không đọc tuyến tính. Tôi trích **bộ xương** của `chay()`
  (`localize.py:15021-20576`, 5.556 dòng) bằng cách liệt kê **mọi câu lệnh thụt 4
  dấu cách** (= mọi bước cấp 1, 150 câu), rồi trích tiếp **thụt 8/12 dấu cách**
  của bốn khối lớn nhất: nhánh scan `:16381-18102`, dò dải che `:18204-19136`,
  lồng tiếng `:19186-20464`, ghép/encode `:19836-20464`.
- **Phủ:** ⭐ **100 % câu lệnh cấp 1 của `chay()`** và ~100 % cấp 2 của bốn khối
  trên ⇒ tôi trả lời được về **HÌNH DẠNG CHUỖI**. Đọc **nguyên văn** chỉ ≈ **650 /
  20.644 dòng (~3 %)**: `:15021-15200` · `:5221-5260` · `:6560-6600` · `:7262-7268`,
  cộng `xu_ly_chon.py` (grep thứ tự biến đổi hình).
- ⛔ **CHƯA đọc thân:** `burn_phude` (`:6560-8533`, chỉ đọc chữ ký + docstring +
  dòng thứ tự filter) · `_ghep_track_khop` (`:8965-9835`) · bốn `long_tieng_*` ·
  ruột khối dịch Gemini (`:16955-17763`) · `_srt_to_ass_pos`. V1/V3/V4 lo các vùng đó.
- ⛔ **Không chạy gì**, ⛔ không sửa mã. `D:\Viral` chỉ đọc.

---

## Phần 1 — BẢNG ĐỐI CHIẾU CHUỖI

Thứ tự dưới đây là **thứ tự thực thi thật** của `chay()`. `⛔ KHÔNG CÓ` ở cột thứ
hai nghĩa là **⛔ không có bước tương ứng trong `pipeline.CHUOI`** (13 giai đoạn),
⛔ không nghĩa là ta thiếu hẳn cơ chế.

| # | BƯỚC CỦA VIRAL (neo `localize.py` nếu không ghi khác) | GIAI ĐOẠN TA | ĐIỀU KIỆN CHẠY | NẤC LUI |
|---|---|---|---|---|
| 0 | **Pre-encode cắt đầu/cuối** (+ zoom nếu đi cùng cắt) — `xu_ly_chon.py:757-808` | ⛔ **KHÔNG CÓ ở đầu chuỗi** — ta cắt ở `image_finish` (GD2, **sau** `render`) | `co_cat and not _cat_cuoi_gop`, hoặc `co_zoom and not _zoom_gop` | ⛔ không có — encode lỗi thì dừng |
| 1 | Reset **11 side-channel toàn cục** + env `DUB_*`/`OCR_*` đầu mỗi video — `:15039-15311` | `thi_hanh.chay_giai_doan` (`thi_hanh.py:436`) — mỗi giai đoạn là **job riêng**, ⛔ không có trạng thái rò | vô điều kiện | — |
| 2 | Mở **sổ kế toán câu** `_sk_bat_dau` + `_ResMon` + đồng hồ `_tg` + `STAGE:batdau` — `:15312-15358` | `AsvStage` + cột `do=` của từng `GiaiDoan` (`pipeline.py:168`) | vô điều kiện | — |
| 3 | Chốt cặp ngôn ngữ: `target_lang()`, `platform_tu_duong_dan`, dò `src_lang` — `:15362-15479` | `transcribe`, tiền quyết *"cặp ngôn ngữ hợp lệ"* (`ngon_ngu.py:37,38`) | `src_lang is None` ⇒ tự dò (nói + chữ trên hình) | `cung_ngon_ngu` ⇒ **bỏ hẳn bước dịch** (`:15473-15481`) |
| 4 | 🔀 **KICK NỀN demucs xoá nhạc** — `:15567-15648`, luồng `:15611` | `audio_prepare` — **tuần tự**, một suất `tach_nguon_cuc_bo` | RAM tổng ≥ **15,0 GB** (`:15633`) + VRAM ≥ **8 GB** (`:15639`) + ⛔ không `chi_asr`/`chi_dich` | `_xn_kq[0] = None` ⇒ tách **tuần tự** ở nhánh ghép (`:20470-20494`) |
| 5 | 🔀 **KICK NỀN tách nhạc** (`lam_tach_nhac`) — `:15652-15710` | `audio_prepare` | `lam_tach_nhac and not tach_truoc` | tuần tự sau |
| 6 | 🔀 **KICK NỀN quét vị-trí che ĐỘNG** — `:15756-15783` | ⛔ **KHÔNG CÓ** | `CHE_DONG=1` **ép cứng** + nguồn ⛔ không phải tiếng Trung | nhánh quét **tuần tự** ngay trước burn |
| 7 | 🔀 **KICK NỀN dò dải che TĨNH sớm** — `:15866-15881` | ⛔ **KHÔNG CÓ** | `che_chu` + (`dich_lai` hoặc cache dải thiếu) | `join(timeout=180 s)` (`:18287-18289`) ⇒ dò tuần tự |
| 8 | Tính **bảy khoá cache** có khai phiên bản: scan `s5` `:15911,15943` · ocrbox `o1` `:15983` · dịch `h11` `:16067,16068` · srt `:16110` · dải `:15799` · hộp `x1` `:18701` · dub `:19213` | `van_tay()` (`thi_hanh.py:249`) — **một** vân tay/giai đoạn, ⛔ không phải bảy khoá tay | `_vhash` đọc được | *"NGHI NGỜ → MISS"* (`:15719`) |
| 9 | Thử **cache SRT đã dịch** ⇒ bỏ cả nghe lẫn dịch — `:16197-16231` | `giai_doan_lech_van_tay` (`thi_hanh.py:310`) | `_trans_key and not dich_lai and not chi_asr` | MISS ⇒ đi nhánh scan |
| 10 | **NGHE/ĐỌC** (ASR hoặc OCR) dưới **khoá scan CHIA SẺ giữa job** — `:16385-16788`, khoá `:16543-16605`, nhả ở `finally` `:16788` | `transcribe` | ⛔ không có `srt_co_san` | `_khe_asr_tre` · subprocess `_whisper_worker` **giết được** · `_asr_tiep_tu_moc` |
| 11 | **Bốn lượt lọc trùng nối tiếp**: `_gop_trung`→`_dedup_lap`→`_bo_manh_trung`→`_bo_lap_lien` — `:16731-16758` | `ban_ghi.kiem` + `content_process` | vô điều kiện sau ASR | — |
| 12 | `chi_asr` ⇒ **RETURN SỚM** (ghi `.zh.srt`, dừng) — `:16790-16811` | ⛔ **KHÔNG CÓ** chế độ chỉ-ASR | `chi_asr` | — |
| 13 | **DỊCH** — ba nhánh: `vi_co_san` `:16867` / `cung_ngon_ngu` `:16908` / Gemini web `:16955-17763` | `content_process` | `dung_gemini` (`:16411-16431`) | `_dich_hong` ⇒ ⛔ không lưu cache; dịch lại phần sót |
| 14 | **Chia nhịp** cue quá dài `_chia_nhip` — `:17778-17816` | `nan_thoi_luong` / `phu_de` (bên ta ở `voice_synthesis`/`compose`) | `SUB_CHIA_NHIP` **và** job ⛔ không đi đường OCR (`_OCR_JOB_NAY`, `:17781`) | bỏ qua |
| 15 | Ghi `.zh.srt` + `.vi.srt`, có `_bak_truoc_ghi_de` — `:17865`, `:17940-17948` | artifact của `transcribe`/`content_process` | vô điều kiện | sao lưu trước khi ghi đè |
| 16 | **IN SỔ KẾ TOÁN CÂU ở ĐIỂM HỘI TỤ** `_sk_xuat` — `:18102-18112` | ⛔ **KHÔNG CÓ** (V1 đã ghi hàng 8 cột) | vô điều kiện, **sau** `if srt_co_san/else`, **trước** mọi `return` | — |
| 17 | `chi_dich` ⇒ **RETURN** (prefetch dịch) — `:18123-18136` | ⛔ **KHÔNG CÓ** | `chi_dich` | — |
| 18 | **XẢ VRAM Whisper** `phu_de._MODEL=None` + `gc.collect()` — `:18137-18147` | ⛔ không cần: mỗi giai đoạn là tiến trình riêng, VRAM trả khi job thoát | vô điều kiện | — |
| 19 | **Phân vai NAM/NỮ** (diarize) ở điểm hội tụ — `:18149-18199` | `CỐ Ý KHÔNG` — rút 22/09, sản phẩm là MỘT giọng | `da_giong` | `doc_giong_json` (`:18164`) |
| 20 | **DÒ DẢI CHE chữ gốc** — bốn nấc + guard tổng + fallback hộp OCR — `:18204-19136` | ⛔ **KHÔNG CÓ trong `CHUOI`** (mã có ở `de_xuat_vung.py`/`do_vung_ocr.py`, ⛔ không là giai đoạn) | `che_chu` | cache → hộp OCR → dò tĩnh → `dai_sub_rapid`; guard tổng `:19040-19052` chặn dải quá to |
| 21 | **DỊCH BANNER — SAU CÙNG**, bằng **chính phiên Gemini** đã dịch phụ đề — `:19130-19184` | ⛔ **KHÔNG CÓ** | `banner_boxes` | — |
| 22 | **LỒNG TIẾNG**: thử `_dub_key` → **sáu nhánh engine** (`:19377-19699`) → `_ghep_track_khop` → join TỔNG HỢP SỚM `:19701` | `voice_synthesis` **+** `timing_align` — ta tách làm **HAI** giai đoạn | `lam_long_tieng` | độ phủ ra tiếng < 50 % ⇒ lùi engine khác (V1 đã ghi) |
| 23 | `chi_dub` ⇒ **RETURN** — `:19807-19814` | ⛔ **KHÔNG CÓ** | `chi_dub` | trả `None` |
| 24 | **CHUẨN ÂM giọng** (`ebur128` đo trước, `loudnorm` khi ép) — `:19842-19942` | `am_master`/`compose`, `do=("lufs_tich_hop","dinh_that_dbtp")` | `DUB_LOUDNORM` / `giong_vol` | `returncode != 0` ⇒ dùng track **chưa chuẩn**, ghi cờ `_dub_chua_chuan` |
| 25 | **TRỘN nền — bảy nhánh**: ⛔ không audio gốc / `_xn_dub_only` / `_xn_giu_giong` / `lam_tach_nhac` / `goc_vol` / `tat_tieng_goc` / mặc định — `:19957-20187` | `timing_align` (trộn bản phối master) | — | mỗi nhánh tự có đường lui về nhánh mặc định |
| 26 | Lọc âm `af_loc` + **chốt âm** `DUB_CHOT_AM` — `:20188-20256` | `compose` | `af_loc` / `DUB_CHOT_AM=1` | giữ `mix_wav` cũ |
| 27 | ⭐ **CĂN LẠI PHỤ ĐỀ theo ONSET THẬT của giọng** — `:20263-20336` + `_canh_sub_theo_dub` `:5221-5440`, onset xuất ở `:9783` | ⛔ **KHÔNG CÓ** — `phu_de.su_kien_tu_ke_hoach` (`phu_de.py:1025,1066`) đọc `dat_tai_ms` của **KẾ HOẠCH** | `_du_phu`: số onset ≥ **0,7 × số câu** (`DUB_SYNC_MIN_PHU`, `:20270`) | ⛔ không đủ phủ ⇒ giữ `vi_srt` gốc **và ghi lý do** (`:20275`, `:20330`) |
| 28 | Chốt dải che + guard `CHE_MAX_OFF` + cờ `da_che`/`dub_that` — `:20362-20380` | `render`/`qc` | `che_chu` | — |
| 29 | ⭐ **MỘT LẦN ENCODE CUỐI** `burn_phude`: `[biến đổi hình] → [watermark] → [che + burn sub] → [setpts tăng tốc]` (`:7263`; docstring `:6572`) | **HAI** giai đoạn, **hai** lần mã hoá: `render` rồi `image_finish` | `burn` / `co_extra_hinh` / `_vs<0.999` / `_tw` / `ratio` (`:20381-20438`) | `_tham_so_goi` chụp đủ 25 tham số ở dòng đầu (`:6588`) ⇒ **gọi lại chính hàm bằng LÀM MỜ** nếu nhánh KÉO làm ffmpeg chết |
| 30 | ⛔ Không lồng tiếng ⇒ `elif burn:` xuất `_phude.mp4` — `:20464-20513` | `render` | `burn` | tách nhạc tuần tự nếu luồng nền còn sống (`:20471-20494`) |
| 31 | **Tự kiểm sau xuất bản** `_kiem_lo_sau_render` — OCR lại bản RA (`:8533`, gọi trong `burn_phude`) | `qc` (V1 đã ghi hàng) | `che_chu` | báo cáo, ⛔ không chặn |
| 32 | Dọn stem demucs/CapCut + ghi **PROFILE jsonl** + `LOCALIZE_DONE` — `:20514-20576` | checkpoint của `thi_hanh` | vô điều kiện | — |
| — | ⛔ **KHÔNG CÓ Ở PHÍA HỌ** | `edit_plan` · `image_finish` · `qc` · `qc_do_luong` · `qc_ai` — **5/13 giai đoạn của ta** | grep toàn `app-src`: ⛔ **không** `blackdetect`/`freezedetect`/`scdet`, ⛔ **không** `libvmaf`/`pesq`/`squim` | — |

### 1. Bước nào họ có mà ta ⛔ không — và ngược lại

**Họ có, ta ⛔ không** (xếp theo giá trị, chi tiết ở Phần 2):

1. **Căn lại phụ đề theo onset THẬT của giọng** (`:5221`, `:20263`) — đo được lệch
   tích luỹ **0,5–0,9 s, đỉnh 2,2 s**. ⭐ Ta **dễ trúng đúng lỗi này**: `gop_khe`
   (`nan_thoi_luong.py:330`) gộp 2–4 `ma` vào **một** tệp tiếng, và
   `ban_dung.py:127-147` chỉ đặt **một** lớp cho `ma` **dẫn** (`di_theo` bị
   `continue`), trong khi `phu_de.py:1066` vẫn sinh sự kiện cho **từng** `ma` theo
   `dat_tai_ms` **kế hoạch**. Cue "đi theo" ⇒ chữ chạy trước/sau tiếng.
2. **Che chữ gốc như MỘT BƯỚC của chuỗi** (`:18204-19136`) — ta có mã đo vùng
   nhưng ⛔ không có giai đoạn nào trong `CHUOI` chịu trách nhiệm việc này.
3. **Dịch banner sau cùng, cùng phiên dịch** (`:19130`) — lý do họ ghi: hai phiên
   khác nhau cho ra **văn phong lệch** trên cùng video.
4. **Bốn luồng nền** che chặng nghẽn (#4–#7) — đây là **hình dạng chuỗi**, ⛔ không
   phải cơ chế lẻ.
5. **Ba chế độ chạy PHẦN** `chi_asr`/`chi_dich`/`chi_dub` (#12, #17, #23).
6. **Khoá scan chia sẻ giữa job**: job sau **chờ** cache của job trước thay vì tính
   lại cùng một thứ (`:16543-16605`).

**Ta có, họ ⛔ không** — ⭐ và đây là **5/13 giai đoạn**:
`edit_plan` (chấm cảnh bằng `blackdetect`+`freezedetect`) · `image_finish` (cắt
cảnh + áp `toc_do`) · `qc` (T1–T18) · `qc_do_luong` (PESQ/SI-SDR/WER) · `qc_ai`
(MetricX). Grep `app-src`: ⛔ **không một** `blackdetect`, `freezedetect`, `scdet`,
`libvmaf`, `pesq`, `squim`. Họ đo chất lượng bằng `chat_luong.py` (252 dòng, đếm
cue/độ rộng) + `_kiem_lo_sau_render` (OCR lại bản ra) — ⛔ không có đại lượng
khách quan nào về **tiếng** hay **hình**. Cộng thêm: **vân tay + lineage +
checkpoint mỗi giai đoạn** (`thi_hanh.py:249,310,526`) — họ có bảy khoá cache tay,
⛔ không có sổ.

### 2. Thứ tự có khác ⛔ không — trục thời gian và hai trục khung hình

⭐ **B6/B8/B9 KHỚP với hệ đã chạy thật ở 4/5 trục.** Đây là **bằng chứng xác
nhận**, ⛔ không phải một khoảng trống:

| trục | Viral áp ở đâu | ta (B6/B8/B9) | khớp? |
|---|---|---|---|
| **thời gian** (`speed`) | **CUỐI CÙNG** của filtergraph — `setpts` + `atempo`. Docstring nói thẳng lý do: *"áp ở CUỐI (whisper đã nghe tốc độ gốc)"* (`:6572`, thứ tự `:7263`) | `toc_do` áp ở **CUỐI `image_finish`** | ⭐ **KHỚP** |
| **hai trục khung** — `zoom` | từ **26/08/2026** đẩy vào burn: chuỗi `che → zoom → sub` (`xu_ly_chon.py:684-695`, `localize.py:15266-15274`). Trước đó pre-encode riêng; bỏ được **một lượt encode** | đổi ở `compose`/`render`, ⛔ không pre-encode | ⭐ **KHỚP** (họ mới hội tụ về đây) |
| **hai trục khung** — `ratio` reframe | trong **cùng** lần encode cuối, trước sub (`:6972`) | `compose`/`render` | ⭐ **KHỚP** |
| **lật ngang** `hflip` | **CỐ Ý ⛔ không** ở pre-encode: *"lật TRƯỚC OCR thì OCR đọc chữ Trung NGƯỢC"* (`xu_ly_chon.py:812`) | — | ⭐ **KHỚP về nguyên tắc** |
| 🔴 **cắt đầu/cuối** | **ĐẦU TIÊN**, pre-encode **trước ASR** — lý do họ ghi: *"whisper phải nghe đúng khung đã cắt + cắt chính xác"* (`xu_ly_chon.py:757-808`) | **SAU CÙNG**: `image_finish` (GD2, sau `render`) | ⛔ **KHÁC** |

⭐ **Và họ đã tự lùi một nửa:** `_cat_cuoi_gop` (`xu_ly_chon.py:803`) đẩy **cắt
CUỐI** vào lượt burn khi ⛔ không cắt đầu và ⛔ không zoom. ⇒ Lý do *"whisper phải
nghe khung đã cắt"* chỉ đúng cho **cắt ĐẦU** (nó **dịch mốc thời gian**), ⛔ không
đúng cho cắt cuối. Ta cắt sau cùng ở **cả hai** đầu, và B6 giữ đúng trục nguồn ⇒
hệ ta **hẹp hơn** ở chỗ đáng hẹp.

### 3. Chỗ nào họ chạy SONG SONG mà ta tuần tự

| việc chạy nền của họ | neo | cổng | ta |
|---|---|---|---|
| demucs xoá nhạc ∥ ASR + dịch | `:15611` | RAM ≥ 15,0 GB **và** VRAM ≥ 8 GB — **đo được**, ⛔ không phải cờ | `audio_prepare` tuần tự, một suất `tach_nguon_cuc_bo` |
| tách nhạc | `:15710` | `lam_tach_nhac and not tach_truoc` | `audio_prepare` |
| quét vị-trí che động | `:15783` | `CHE_DONG=1` ép cứng | ⛔ không có bước |
| dò dải che tĩnh sớm | `:15880-15881` | đo 30/08: chặng này **12,1 s / 118,0 s = 10,3 %** tuần tự | ⛔ không có bước |
| dịch Gemini **STREAM** chồng lên ASR | `:16473-16538`, `_GeminiStream:3415` | video đủ dài + ⛔ không `dich_lai` | `content_process` **sau** `transcribe` |
| TỔNG HỢP SỚM: đọc tiếng ngay khi xong từng lô dịch | `_TongHopSom:12865`, join `:19701` | *"hai chặng nghẽn ở HAI tài nguyên"* | `voice_synthesis` **sau** `content_process` |

⇒ **Họ 5–6 nhánh nền trong MỘT video. Ta 0.** `CHUOI` là dây thẳng: mọi `sau=`
nối một mắt (`TIMING_ALIGN.sau=(VOICE_SYNTHESIS, AUDIO_PREPARE)` trông như rẽ
nhưng `AUDIO_PREPARE` đã nằm thượng nguồn qua `TRANSCRIBE→CONTENT_PROCESS`).
⭐ **Chỗ ta song song mà họ ⛔ không**: ở mức **LẦN CHẠY** (nhiều job cùng lúc, nền
tảng điều tiết bằng `tai_nguyen_suat`) và **TRONG** một giai đoạn (lô dịch, lô
TTS). Đó là một đánh đổi **có ý**: luồng nền trong một tiến trình làm checkpoint
mất nghĩa — một job chết giữa chừng ⛔ không biết luồng nền đã làm tới đâu.

### 4. Chỗ nào họ QUYẾT ĐỊNH BỎ QUA một bước, và dựa vào gì

| bỏ qua gì | dựa vào | neo |
|---|---|---|
| cả nghe **lẫn** dịch | HIT `_trans_key`/`_srt_key`; nguyên tắc *"NGHI NGỜ → MISS"* | `:16197`, `:15719` |
| nghe/OCR, **chờ** job khác tính hộ | khoá scan chia sẻ + nhịp tim, nhả ở `finally` | `:16543-16605`, `:16788` |
| **hẳn** phép dò dải TĨNH | OCR đã trả ≥ N hộp ⇒ *"đỡ tốn CPU"*; đặt `blur_band` **dummy khác None** để vượt cổng | `:18234-18238` |
| chia nhịp cue | job đi đường **OCR** (`_OCR_JOB_NAY`) — nguồn đã có nhịp | `:17781` |
| neo độ dài bản dịch cho `vi` | ⭐ **một phép đo**: 12.626 cue thật, độ nhạy đo được **0–0,5** thay vì ≈1,0 ⇒ neo vô dụng với `vi`; **BẬT lại** cho đích khác (A/B n=3) | `:15066-15105` |
| căn lại phụ đề theo giọng | độ phủ onset < **0,7 × số câu** ⇒ giữ srt gốc **và ghi lý do** | `:20270`, `:20275` |
| kick luồng nền | `chi_asr`/`chi_dich` sẽ return sớm ⇒ ⛔ không xuất video | `:15563-15566` |
| toàn bộ đuôi chuỗi | ba chế độ `chi_asr`/`chi_dich`/`chi_dub` | `:16790`, `:18123`, `:19807` |

⭐ Điểm chung: **mọi quyết định bỏ qua đều tựa vào một thứ ĐO ĐƯỢC** (khoá nội
dung, số hộp, độ phủ onset, độ nhạy đo trên 12.626 cue) — ⛔ không tựa vào một cờ
người dùng bật. ⚠️ Nhưng `:18238` là đúng bẫy **"hai trạng thái gộp thành một giá
trị"** của ta: `blur_band` dummy `(0.0,0.0,0,0.0,1.0)` mang nghĩa *"⛔ không cần dò"*
lẫn *"đây là một dải"* trong cùng một biến.

---

## Phần 2 — Hàng 8 cột (⛔ chỉ những gì Phần 1 làm lộ ra, V1 ⛔ chưa có)

| HẠNG MỤC | BƯỚC ASV | VIRAL CÓ GÌ | TA CÓ GÌ | TRẠNG THÁI | GIÁ TRỊ | GIÁ | ĐỀ NGHỊ |
|---|---|---|---|---|---|---|---|
| **Căn lại phụ đề theo ONSET THẬT của giọng**, ⛔ không theo mốc kế hoạch — con trỏ ghép trôi dần nên giọng đọc câu *i* ở vị-trí thực ≠ mốc gốc | `timing_align` → `compose` | `_canh_sub_theo_dub` `localize.py:5221-5440`; onset xuất ở `:9783`; gọi `:20263-20336`. ⭐ **Đo thật: lệch tích luỹ 0,5–0,9 s, đỉnh ~2,2 s** | `phu_de.su_kien_tu_ke_hoach` (`phu_de.py:1025,1066`) đọc `dat_tai_ms` **kế hoạch**; `qc.py:660-673` (T7) chỉ đối chiếu **kế hoạch ↔ bản dựng**, ⛔ không đối chiếu **kế hoạch ↔ tiếng THẬT**; khe GỘP chỉ có lớp cho `ma` dẫn (`ban_dung.py:127-147`) | **THIẾU** | **5 +đo** | 3 | **LẤY NGAY** — `gop_khe` của ta làm cue "đi theo" mất mốc thật, đúng ca họ đã đo |
| **Cổng độ phủ trước khi căn lại**: số onset đo được phải ≥ 0,7 × số câu, ⛔ không đủ thì **giữ nguyên** và **ghi lý do** | `timing_align` | `:20270` (`DUB_SYNC_MIN_PHU`), `:20275` dựng câu lý do, `:20330` in ra | ⛔ **KHÔNG** (ta chưa có phép căn lại nên chưa có cổng) | **THIẾU** | 4 | 1 | **LẤY NGAY** — đi kèm hàng trên; một phép sửa mốc **không có cổng phủ** là phép sửa mù |
| **Cắt đầu/cuối làm TRƯỚC khi nghe**, lý do nêu rõ: *"whisper phải nghe đúng khung đã cắt"* | `image_finish` | `xu_ly_chon.py:757-808`; và họ **đã lùi một nửa**: `_cat_cuoi_gop:803` đẩy cắt-CUỐI vào burn | ta cắt **sau** `render` (`giai_doan_hinh_anh._ke_cat`, `ke_cat.py:252`), B6 chốt **một** trục thời gian | **KHÁC THIẾT KẾ** | 3 | 5 | ⛔ **KHÔNG LẤY** — đổi lại là đổi hợp đồng giai đoạn; và lý do của họ chỉ đúng cho cắt **ĐẦU** (dịch mốc), thứ ta cũng ⛔ không làm giữa chuỗi |
| **Trục thời gian áp CUỐI CÙNG** vì ASR đã nghe tốc gốc | `image_finish` | `:6572` docstring + `:7263` thứ tự filter — *"áp ở CUỐI"* | B6: `toc_do` áp ở CUỐI `image_finish` (`pipeline.py`, tiền quyết `IMAGE_FINISH`) | **ĐÃ MƯỢN** (ta tới cùng kết luận **độc lập**) | 2 | 1 | ⛔ **KHÔNG LẤY** — đã có. ⭐ Giá trị nằm ở chỗ khác: nó là **bằng chứng ngoài** cho B6, một hệ chạy nhiều năm chọn đúng thứ tự ấy |
| **Che chữ gốc là MỘT BƯỚC của chuỗi**, có bốn nấc lui và một **guard tổng** chặn dải quá to | ⛔ — (⛔ không giai đoạn nào) | `:18204-19136`; guard tổng `:19040-19052` (ca thật: video ⛔ không có sub mà blur che ~50 % khung); tôn trọng dải khách chọn tay `:19044` | `de_xuat_vung.py` · `do_vung_ocr.py` có mã đo vùng, nhưng ⛔ **không** là giai đoạn trong `pipeline.CHUOI:168` | **THIẾU** (hình dạng chuỗi) | 4 | 5 | **LẤY SAU** — thêm một giai đoạn là đổi `CHUOI` + `test_402`; ⭐ **phải hỏi chủ dự án**, ⛔ không tự quyết |
| **Dịch banner SAU CÙNG bằng CHÍNH phiên đã dịch phụ đề** | `content_process` | `:19130-19184`; lý do ghi thẳng: hai phiên khác nhau ra *"Tam Tạng đại sư"/"Thất Tinh Kiếm"* ⇒ banner và phụ đề **lệch hẳn văn phong** | ⛔ **KHÔNG** | **THIẾU** | 3 | 3 | **LẤY SAU** — luật *"cùng phiên dịch cho cùng video"* áp được cho mọi văn bản phụ của ta, ⛔ không chỉ banner |
| **Khoá scan CHIA SẺ giữa các lần chạy**: job sau **CHỜ** cache của job trước thay vì tính lại cùng một thứ, có nhịp tim, nhả trong `finally` | ⛔ — | `:16543-16605`; nhịp tim `:16593-16598`; `_nha_lock_1lan` ở `finally` `:16788` — *"chống job anh em treo 1h"* | `tai_nguyen`/`tai_nguyen_suat` (`pipeline.py`) **xếp hàng** nhưng hai lần chạy cùng `van_tay` vẫn **tính lại từ đầu** | **THIẾU** | 3 | 4 | **LẤY SAU** — chạm hợp đồng giai đoạn; nhưng hai khách gửi **cùng** video là ca thật của SaaS, ⛔ không phải của app một người |
| **Bốn luồng nền che chặng nghẽn**, mỗi luồng một cổng ĐO ĐƯỢC và một nấc lui tuần tự | ⛔ — (hình dạng chuỗi) | `:15611` · `:15710` · `:15783` · `:15880`; `join(timeout=180)` `:18289`; cổng RAM 15,0 GB `:15633` / VRAM 8 GB `:15639`; đo 30/08 chặng dò dải **12,1 s / 118,0 s** | `CHUOI` tuần tự tuyệt đối; ta song song ở mức **lần chạy** và **trong** giai đoạn | **KHÁC THIẾT KẾ** | 2 | 5 | ⛔ **KHÔNG LẤY** — thêm hộ tiêu thụ CPU/GPU trong một job (GIÁ ≥ 4 theo §6) **và** phá nghĩa của checkpoint: job chết ⛔ không biết luồng nền tới đâu |
| **Ba chế độ chạy PHẦN** (`chi_asr`/`chi_dich`/`chi_dub`) return sớm giữa chuỗi | ⛔ — | `:16790-16811` · `:18123-18136` · `:19807-19814` | `da_xong` + `van_tay` + `giai_doan_lech_van_tay` (`thi_hanh.py:249,310,526`) — chạy lại **đúng** giai đoạn lệch | **KHÁC THIẾT KẾ** — ⭐ hệ ta **mạnh hơn**: 13 điểm dừng thay vì 3 | 1 | 1 | ⛔ **KHÔNG LẤY** — tiền đề của họ là *"một người ngồi đó bấm lại từng phần"*, ⛔ **không áp dụng** cho SaaS |
| **Bỏ HẲN một phép đo khi phép trước đã cho đủ dữ kiện** — OCR trả đủ hộp ⇒ ⛔ không dò dải tĩnh | ⛔ — | `:18234-18238`, *"đỡ tốn CPU"*. ⚠️ Nhưng cài bằng `blur_band` **dummy khác None** để *"vượt gate"* | ⛔ **KHÔNG** có cặp bước này | **THIẾU** | 2 | 2 | ⛔ **KHÔNG LẤY** phần cài đặt — ⭐ nhưng ghi lại **cái bẫy**: dummy ấy gộp *"⛔ không cần đo"* với *"đây là một dải"* vào một giá trị, đúng lớp [hai-trang-thai-gop-thanh-mot-gia-tri] của ta |
| **Xả VRAM ở ĐIỂM HỘI TỤ, trước chặng GPU kế** | `voice_synthesis` | `:18137-18147` — `phu_de._MODEL=None` + `gc.collect()`, lý do: *"Whisper giữ VRAM tới khi destructor chạy → Demucs/TTS nạp kế → 2 model tranh"* | mỗi giai đoạn là tiến trình riêng ⇒ VRAM trả khi job thoát; và ba giai đoạn GPU dùng **cùng** suất `tach_nguon_cuc_bo` (`pipeline.py`) | **KHÔNG ÁP DỤNG** | 1 | 1 | ⛔ **KHÔNG LẤY** — kiến trúc tiến trình của ta đã giải, ⛔ không cần mã |

---

## ⛔ Chưa kiểm được

1. **`_ghep_track_khop` (`:8965-9835`) sinh `_LAST_DUB_ONSETS` thế nào** — tôi đọc
   **chỗ xuất** (`:9783`) và **chỗ tiêu thụ** (`:5221`, `:20263`), ⛔ không đọc thân.
   ⇒ Hàng số 1 nêu **có phép đo onset** và **đại lượng lệch họ ghi**; nó ⛔ **không**
   khẳng định thuật toán tìm onset của họ.
2. **Bên ta: cue "đi theo" trong khe GỘP lệch bao nhiêu giây** — tôi chứng minh
   được **cấu trúc** cho phép lệch (`ban_dung.py:127-147` + `phu_de.py:1066` +
   `he_so_toc` áp ở render), ⛔ **không** đo được độ lệch. ⭐ Đó là **một phép đo, ⛔
   không phải một suy luận** — và theo luật 28/09 nó thuộc *"về cuối đo một lượt luôn"*.
3. **`burn_phude` có đúng một điểm `setpts` không** — tôi tin theo dòng thứ tự
   `:7263` + `_emit_speed` `:8214,8264,8271`; ⛔ chưa duyệt hết 2.000 dòng
   filtergraph nên ⛔ không loại trừ một `setpts` thứ hai ở nhánh hiếm.
4. **`chat_luong.py` (252 dòng) đo những gì** — tôi chỉ đọc danh sách hàm
   (`do_phu_de`, `bao_cao`). Kết luận *"họ ⛔ không có đại lượng khách quan về
   tiếng/hình"* tựa vào **grep vắng mặt** (`libvmaf`/`pesq`/`squim` = 0 hit trên
   260 tệp), ⛔ không tựa vào việc đọc trọn tệp đó.
5. **`xu_ly_chon.py` (1.754 dòng)** — tôi chỉ grep thứ tự biến đổi hình. Có thể còn
   bước nào của chuỗi nằm ở đó mà bảng này ⛔ không kể.
