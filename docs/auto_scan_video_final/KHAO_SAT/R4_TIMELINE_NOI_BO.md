# R4 — Timeline các đoạn: đối chiếu ASV với **app phiên âm của ta**

> Ngày 25/09/2026 · làn `phien/timeline` · **điều tra + đối chiếu**, ⛔ không sửa mã.
> Mọi khẳng định kèm tệp + số dòng hoặc SHA. Câu không nguồn ⛔ không vào tệp này.

---

# 🔴 ĐÍNH CHÍNH 25/09 (cùng ngày, sau khi soi ĐĨA chứ không chỉ soi `main`)

> ⛔ **§3.1 dưới đây SAI.** Nó đúng cho `main`, và `main` ⛔ **không phải** cây đã
> sinh ra con số 0,903/0,909. Đọc mục này trước, rồi mới đọc tiếp.

**ASV CÓ một bộ phân đoạn tự viết** — `apps/auto_scan_video/cat_doan.py`, **323 dòng**,
commit **`de3a1d4c`** (24/09): *"fix(ASV N-17 lan 2)+feat(B1): … va CAT LAI doan theo CAU"*.
⛔ Nó **không có trên `main`**; nó sống trên `phien/asvf-nghiem-thu-v2` và `phien/gop-asv`
(`git branch --contains de3a1d4c`). ⇒ ⭐ **Nghi vấn của chủ dự án ĐÚNG.** Tôi sai vì đọc
`main` rồi tưởng đã đọc thứ được đo — đúng bẫy *"đọc thứ đại diện thay vì đọc thứ thật"*.

Bằng chứng đo được, `bang_chung/b1_chep_loi_moi/v2.json` khoá `cat_lai`:

```
so_doan_truoc: 8   ->   so_doan_sau: 74      khe_toi_da_s 7,0 · khe_toi_thieu_s 0,8333
so_doan_qua_dai: 0 · so_doan_khong_cho_ngat: 0 · so_doan_khong_co_moc_tu: 0
nguon_luat: whisperX PR #1466 (CJKSentenceSplitter) · Netflix TTSG 215758617 + 215986007
```

### Vì sao nó tồn tại — ⭐ và đây là một lý do RẤT mạnh

`cat_doan.py:9-27` + thân commit `de3a1d4c` §2, đo trên gói đã cài (whisperx 3.8.6,
`D:\LTTWhisperX`): nhánh `aligned` trả **~24 giây một đoạn** trên cả ba phim Hán, trong
khi hardsub của chính phim ấy cho **2,4 giây**.

⛔ **Không phải `chunk_size=30`.** WhisperX **đã** chia khối VAD thành câu trong `align()`
bằng **NLTK Punkt**, nhưng `whisperx/utils.py:130-150 PUNKT_LANGUAGES` ⛔ **không có `zh`**,
và `alignment.py:190` rơi về `'english'`. Đo thật:

```
văn Hán 44 ký tự, 3 câu ngắt bởi 。   ->  Punkt en cho  1  span
văn Anh 3 câu                         ->  Punkt en cho  3  span
```

⇒ ⭐ Hạ `chunk_size` ⛔ **không chữa được**, và mất 3,6× tốc độ đường batched.

### 🔴 Hệ quả ĐỔI CHIỀU câu 6: app phiên âm (A) mắc **ĐÚNG cùng một bệnh**

`apps/transcript/services/engine/segment/constants.py:14`:

```python
SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?…。！？])\s+")
```

⭐ Lớp ký tự **có** `。！？` — trông như đã lo cho tiếng Hán. Nhưng nó đòi **`\s+` ngay
sau**, mà văn Hán ⛔ không có dấu cách. Chạy thật (⛔ không suy đoán):

| văn | `SENT_SPLIT_RE.split()` |
|---|---|
| 3 câu Hán ngắt bởi `。` | 🔴 **1 span** |
| 3 câu Anh | ✅ **3 span** |

Và `CUT_HINT_RE` (`constants.py:15`, `[,\.\!\?\;\:…]+$`) ⛔ **không khớp** `生活。`
— ⛔ không có `。` trong lớp. Chỉ `STRONG_PUNCT` (`:21`) có `。`, và nó ⛔ không phải nơi cắt.

> 🔑 **Hai hằng số khai một điều, hằng số thứ ba phản lại — và cơ học thắng giao ước.**
> Nhìn `STRONG_PUNCT` thì (A) *"có hỗ trợ CJK"*; chạy `SENT_SPLIT_RE` thì ⛔ không.

⇒ ⭐ **Dùng lại lớp cắt câu của (A) sẽ TÁI TẠO đúng lỗi mà `cat_doan.py` sinh ra để chữa.**
⛔ Đừng bỏ `cat_doan.py` để lấy (A). Bảng ở §7 và lựa chọn **II-2** ở §8 phải đọc lại
theo đính chính này: phần còn dùng lại được của (A) thu về **`vad.py`** và **lớp gộp/đệm
theo mốc từ**, ⛔ **không** gồm lớp cắt câu.

### Ba đính chính nhỏ hơn, cùng nguồn

1. §3.3 **dòng 7** (`initial_prompt`) ⛔ **sai** cho nhánh đã đo: có
   `以下是中文普通话句子。`, nguồn whisperX issue #645 (`v2.json::tham_so_tai_lap`).
2. §3.3 **dòng 8** (`chunk_size`) — đúng là *"không truyền ⇒ mặc định 30"*, nhưng
   ⛔ **không** phải nguyên nhân đoạn dài. `cat_doan.py:29-30` bác bỏ thẳng.
3. §3.3 **dòng 9-11** (*"không có hậu xử lý / không cưỡng chế trần"*) ⛔ **sai** cho nhánh
   đã đo: `cat_doan.py` cưỡng chế **7,0 s** / **5/6 s**, và **khai ra** khi không cắt được.

### ⭐ Câu 3 đọc lại: khác biệt này **CỐ Ý**, ⇒ **GIỮ**

`de3a1d4c` §3 tra cộng đồng **trước** khi tự soạn, và ghi cả thứ **đã từ chối**:
`whisperx/SubtitlesProcessor.py` (⛔ cắt ở **điểm giữa** khi không có dấu phẩy ⇒ cắt giữa
câu — với lồng tiếng là khe chứa **nửa ý**) và `jianfch/stable-ts` (MIT, nhưng gói chưa
cài, và PR #1466 làm cùng việc bằng ~60 dòng không phụ thuộc). Ngưỡng lấy từ **quy chuẩn
công bố** (Netflix TTSG), ⛔ không tự đặt. ⇒ ⭐ Đây là *"dùng lại trước, tự viết sau"* làm
**đúng**, ⛔ không phải một chỗ trôi.

⚠️ Nhưng chính `de3a1d4c` tự khai: *"CHƯA được gọi là 'đã sửa': phép kiểm đơn vị dùng dữ
liệu TỰ DỰNG sẽ xanh bất kể engine thật trả gì."*

---

## 0. Ba app, ⛔ đừng lẫn hai cái đầu

| | App | Vai |
|---|---|---|
| **(A)** | `apps/transcript` — *"Phiên âm có dòng thời gian"* | ⭐ **app phiên âm của ta**, `manifest.py:36-40`. Migrate từ `bot_transcript`. |
| **(B)** | `apps/autosubvideo` — App phụ đề / AutoSub | Chủ của `transcription.transcribe_file` + `segmenter.py` (cắt **dòng hiển thị**) |
| **(C)** | `apps/auto_scan_video` (ASV) | Lồng tiếng. Gọi ASR của (B). ⛔ Chưa bao giờ chạm (A). |

⚠️ Vế *"app phiên âm của ta"* của chủ dự án là **(A)**, ⛔ không phải (B). Đây là chỗ
dễ trả lời nhầm nhất, vì (B) mới là app ASV **đang** mượn mã.

---

## 1. 🔴 CÂU 5 — CHÂN LÝ NỀN. Có, và nó nằm trong chính kho này.

### 1.1 Trần 0,606 đến từ đâu

Chân lý nền hiện dùng là `docs/auto_scan_video_final/l_ocr_gt_v2.json`:
33 dòng, cửa sổ 0–60 s của một phim 190 s, trường `cach_lam` ghi nguyên văn:

> *"Doc tay dai phu de cat moi 0,5 s (khong qua OCR) … Moc = luoi 0,5 s."*

`tools/do_luong.py:868` (`LUOI_CHAN_LY_NEN_S = 0.5`) và `B2_KTC_VA_PHAN_QUYET.md:159-175`
rút ra hệ quả: một hệ **hoàn hảo** chỉ đạt độ nhạy **0,606 [0,424 ; 0,758]** ở dung sai
0,3 s, trong khi ngưỡng đã viết (`NGUONG_PHAN_DOAN["onset_do_nhay_toi_thieu"]`,
`tools/do_luong.py:858`) là **0,80**.

### 1.2 ⭐ Bản mốc **mịn hơn 5 lần** ĐÃ TỒN TẠI, trên **đúng phim v2 ấy**

`docs/auto_scan_video_final/L_OCR.md:98-102` — bảng quét fps của chính lần đo OCR:

> *"Do tren ca 4 clip, lay dong thoi gian **10 fps** lam moc so sanh"*
>
> | fps đọc | v1 | **v2** | v3 | v4 | CER v2 (60 s đối chiếu tay) |
> |---|---|---|---|---|---|
> | **10** | 105 dòng | **107 dòng** | 99 | 120 | **0,003** |

⇒ Trên phim **v2** — đúng phim duy nhất có chân lý nền (`B2:215-219`) — ta đã dựng một
dòng thời gian **10 fps**, tức lưới **0,1 s**, **107 dòng**. Nó được dùng làm *"mốc gốc"*
để chấm các mức fps thấp hơn, rồi ⛔ **không ai dùng nó làm chân lý nền cho phép (c)**.

⭐ Lưới 0,1 s ⇒ sai số lượng tử hoá ≤ ±0,05 s, **dưới** dung sai 0,3 s một bậc.
⇒ 🔴 **Trần 0,606 biến mất.** Nó là trần của *lưới 0,5 s*, ⛔ không phải trần của ta.

### 1.3 ⚠️ NHƯNG nó đo **mốc HIỆN PHỤ ĐỀ**, ⛔ không phải **mốc BẮT ĐẦU NÓI**

`L_OCR.md:132-134` đã đo chính độ lệch ấy, trên 33/33 dòng khớp:

> *"OCR bat dau **cham hon ASR trung binh 0,34 s** (p95 |lech| 0,46 s) — phu de hien
> sau khi bat dau noi, dung nhu nguoi bien tap lam."*

Và cùng đoạn ấy đã nói trước `B2` **ba ngày** rằng lưới 0,5 s là thứ chặn:

> *"Do lech nay … khong doi chieu duoc tot hon: **chinh ban doi chieu tay cung chi co
> luoi 0,5 s**."* (`L_OCR.md:134`)

🔑 Hai tệp tìm ra **cùng một giới hạn**, ba ngày cách nhau, và ⛔ không tệp nào biết tệp
kia. Đây là ca *"hai chỗ khai cùng một điều, không ai bắt khớp"*.

⇒ Kết luận câu 5, chia làm hai, ⛔ đừng gộp:

| Trục | Có chân lý nền mịn hơn 0,5 s không? |
|---|---|
| **mốc hiện phụ đề** | ✅ **CÓ** — OCR 10 fps, lưới 0,1 s, 107 dòng, CER 0,003, đã chạy trên đúng v2 |
| **mốc bắt đầu nói** (thứ khớp môi cần) | ⛔ **CHƯA** — mốc phụ đề lệch **+0,34 s** có hệ thống; trừ bias thì còn p95 0,46 s chưa giải thích |

### 1.4 Ba nguồn mốc mịn khác trong kho — và vì sao **không** nguồn nào thay được

| Nguồn | Độ phân giải | 🔴 Vì sao không dùng làm chân lý nền cho ASV |
|---|---|---|
| Luồng phụ đề **nhúng** → SRT · `apps/auto_scan_video/nguon_loi.py:147-186` | **1 ms** (`_giay()`:142-144, `confidence=1.0`) | Chỉ có khi video **có** luồng phụ đề chữ. Phim v2 là hardsub đốt vào hình ⇒ ⛔ không có luồng. |
| Kho vàng `tests/golden/parity_transcript/` (5 cặp) | **0,01 s** (đo: `mau_02` `start/end` 2 chữ số) | ⛔ **Không còn tệp audio** — `30_PARITY_VOI_BOT_THAT.md:157-158` nói thẳng *"nó đọc từ chính tệp audio, thứ ta không còn"*. Chỉ dùng được để đối soát `make_timeline_v2`, ⛔ không dùng để chấm onset trên phim của ASV. |
| Dự án khách đã sửa tay · `apps/autosubvideo/schemas.py:181-207` (`StudioWord`/`StudioCue`, float, có `words`), lưu ở `platform_core/models.py:225 app_projects`, ghi qua `routes.py:228 PUT /api/projects/{id}` | float, không lượng tử hoá | ⭐ **Đây là chân lý nền THẬT duy nhất** (người sửa tay). Nhưng là **dữ liệu production của khách** ⇒ ⛔ chưa được phép dùng, và chưa ai đếm có bao nhiêu bản đã sửa. **Cần chủ dự án quyết.** |

---

## 2. CÂU 1 — App phiên âm (A) cắt đoạn bằng gì

Sáu bước, `apps/transcript/services/phien_am.py:8-15` và thân hàm `chay()` (dòng 295-374):

```
1 VAD    engine/vad.py::vad_speech_segments        (phien_am.py:312)
2 STT    platform_core.stt.service, hồ sơ `moc_tu_vad_ngoai`   (phien_am.py:266)
3 sửa chữ V5   sua_chu_v5()                        (phien_am.py:327)
4 DỰNG DÒNG THỜI GIAN  make_timeline_v2()          (phien_am.py:336-343)
5 chiếu schema 6 khoá  _chieu_schema()             (phien_am.py:177-204)
6 hai bộ kiểm  _kiem_khong_trung_lien_tiep / _kiem_schema_nghiem_ngat
```

**Tham số ASR** (`platform_core/stt/ho_so.py:82-101`) — ⭐ đây là một **hồ sơ có tên**,
⛔ không có mặc định (`KhongCoHoSo`, dòng 68-70):

| | `moc_tu_vad_ngoai` (tự dò / en) | `moc_tu_vad_ngoai_vi` (ép `vi`) |
|---|---|---|
| `word_timestamps` | `True` (*"HARD RULE"*) | `True` |
| `vad_filter` | ⛔ **KHÔNG CÓ KHOÁ** — cố ý | ⛔ không có |
| `beam_size` / `best_of` | 1 / 1 | **5 / 3** |
| `temperature` | 0.0 | 0.0 |
| `condition_on_previous_text` | `False` | `False` |
| `initial_prompt` | ⛔ không (`ho_so.py:96`, *"`use_initial_prompt` tắt"*) | ⛔ không |

⭐ `ho_so.py:37-38` nêu lý do cấm `vad_filter`: *"`transcript` **cấm** `vad_filter`: nó
chạy VAD riêng … Bật thêm là VAD hai lần, và **ranh giới đoạn đổi**."*

**VAD riêng** (`apps/transcript/services/engine/vad.py:88-96`): năng lượng, khung 30 ms,
`min_speech_s=0.3`, `min_silence_s=0.8`, `pad_s=0.15`, ngưỡng = phân vị 20 của dBFS + 12 dB.

**Hậu xử lý cắt/gộp**: ✅ **CÓ, rất nhiều** — `services/engine/segment/`, **3.161 dòng /
15 mô-đun** (`merging.py` 273, `splitting.py` 289, `silence.py` 256, `padding.py` 114,
`repair.py` 140, `seamless.py` 170, `word_scene_builder.py` 892 …).
Hai tầng giới hạn độ dài, ⛔ không được gộp (`phien_am.py:28-34`):

* cấu hình: `target_min=1.5` (`MIN_S_MAC_DINH`, `phien_am.py:74-76` — *"Mặc định mã 3.0 là SAI"*), `target_max=6.0`;
* cứng: `HARD_MIN=2.0` / `HARD_MAX=6.0` (`segment/constants.py:28-29`, *"NON-NEGOTIABLE"*).

Trọng số chọn ranh giới từ (`constants.py:38-40`): `W_PUNCT=3.0`, `W_PAUSE=3.0`, `W_LEN=1.0`.
Khoảng lặng ≥ 2,0 s được giữ thành đoạn `silence` (`YeuCau.nguong_khoang_lang`, `phien_am.py:93`).

⚠️ `segment/silence.py::split_silence_segments_random_2_5` gọi `random.uniform`
(`30_PARITY_VOI_BOT_THAT.md:39-46`) ⇒ **đầu ra của (A) KHÔNG tất định** trong vùng lặng.

---

## 3. CÂU 2 — ASV (C) cắt đoạn bằng gì, và ⭐ từng điểm khác

### 3.1 ⛔ MỤC NÀY SAI — xem ĐÍNH CHÍNH ở đầu tệp. (Giữ nguyên để thấy tôi sai ở đâu.)

> ⛔ Đúng cho `main`. ⛔ **Sai** cho nhánh đã sinh ra con số. `cat_doan.py` tồn tại.

#### ~~Phát hiện thứ nhất: ASV ⛔ KHÔNG hề có bộ phân đoạn~~

Nghi vấn của chủ dự án (*"ASV tự viết lại phần cắt đoạn"*) — ⛔ **BÁC BỎ**, nhưng bác bỏ
theo hướng **xấu hơn**:

* `apps/auto_scan_video/ban_ghi.py:66-134 chuan_hoa()` — vòng lặp duy nhất: bỏ đoạn rỗng
  (dòng 78-80), ép `float` (82), sao chép `words → tu` (88-99), `sort` (112), đánh mã
  `seg_0001` (113-114). ⛔ **Không gộp, không tách, không ngưỡng độ dài, không khoảng lặng.**
* Hạ nguồn ⛔ cũng không: `apps/auto_scan_video/van_ban.py:17-19` — *"Mỗi mục trong
  `content.json` mang **đúng** `ma` của đoạn trong bản ghi. **Không đánh số lại, không sắp
  xếp lại, không gộp**."*
* Thước B1 đọc đúng artifact ấy: `tools/do_luong.py:871-875 doc_doan_b1` →
  `b1_chep_loi_moi/*.json`, khoá `doan` / `bat` / `ket` — chính hình dạng `ban_ghi`.

⇒ ⭐ *"Bản phân đoạn của ta"* đạt 0,903 / 0,909 ở B2 §6.4 **chính là đầu ra thô của
WhisperX**, chưa qua một luật LTT nào. Bốn đối chứng ở `B2:200-205` so WhisperX với
*"gộp tất"* / *"băm 2 s"* / *"khối 30 s"* — ⛔ **không** so với bộ phân đoạn của (A).

### 3.2 Đường ASR của ASV

`apps/auto_scan_video/giai_doan_chep_loi.py:86` bọc `apps.autosubvideo.transcription.transcribe_file`.
Đường đó có **hai** nhánh (`apps/autosubvideo/transcription.py:259-277`):

* **WhisperX sidecar** (mặc định) — `whisperx_runner.py:21-27`: `load_model(...)`,
  `transcribe(audio, batch_size=8)`, rồi `whisperx.align(...)`. ⛔ Không truyền `chunk_size`,
  ⛔ không `vad_options`, ⛔ không `beam_size`, ⛔ không `initial_prompt` ⇒ **mặc định thư viện**.
* **faster-whisper** (lùi về) — `transcription.py:232-234`:
  `word_timestamps=True, vad_filter=True, beam_size=5`.

⚠️ Hai nhánh cắt đoạn **khác nhau** và ASV giữ nguyên nhãn phân biệt
(`ban_ghi.py:120-124`, `canh_chinh` = `aligned` | `fallback_unaligned`) — ⭐ tốt, nhưng
⛔ thước B1 **không phân tầng theo nhãn ấy**.

### 3.3 ⭐ Bảng khác biệt — từng điểm

| # | Điểm | (A) `apps/transcript` | (C) ASV | Nguồn |
|---|---|---|---|---|
| 1 | Engine ASR | faster-whisper, hồ sơ **có tên** | **WhisperX** (+ align), lùi về faster-whisper | `ho_so.py:82` · `whisperx_runner.py:17-27` |
| 2 | VAD | **ngoài** whisper, `vad.py` 30 ms, `min_silence 0.8` | WhisperX: VAD **trong** thư viện, mặc định · fallback: `vad_filter=True` mặc định | `phien_am.py:312` · `transcription.py:233` |
| 3 | `beam_size` | **1** (auto/en) · **5** (vi) | WhisperX: mặc định thư viện · fallback: **5** | `ho_so.py:85,97` · `transcription.py:234` |
| 4 | `best_of` | 1 / **3** | ⛔ không đặt | như trên |
| 5 | `temperature` | **0.0** ghim | ⛔ không đặt (thư viện tự rơi bậc) | `ho_so.py:87` |
| 6 | `condition_on_previous_text` | **False** ghim | ⛔ không đặt (mặc định `True`) | `ho_so.py:88` |
| 7 | `initial_prompt` | ⛔ cố ý không | ⛔ không | `ho_so.py:96` |
| 8 | `chunk_size` | *không áp dụng* | ⛔ **không truyền** ⇒ mặc định WhisperX | `whisperx_runner.py:23` |
| 9 | **Hậu xử lý cắt/gộp** | **3.161 dòng**, 15 mô-đun | 🔴 **KHÔNG CÓ** | `segment/` · `ban_ghi.py:66-134` |
| 10 | Trần độ dài đoạn | `HARD_MAX=6.0` cưỡng chế | ⛔ không cưỡng chế; chỉ **đo** ở B1 (`do_dai_toi_da_s=7.0`) | `constants.py:29` · `do_luong.py:854` |
| 11 | Sàn độ dài đoạn | `target_min=1.5` / `HARD_MIN=2.0` | ⛔ không có | `phien_am.py:76` · `constants.py:28` |
| 12 | Đoạn `silence` | ✅ sinh ra, nhãn `[B-ROLL / PAUSE]` | ⛔ không có khái niệm | `phien_am.py:341-342` · `ban_ghi.py:67` |
| 13 | Mốc từ (`words`) ở **đầu ra** | 🔴 **BỊ VỨT** (`_chieu_schema`) | ✅ **GIỮ** (`tu`), có bất biến kiểm | `phien_am.py:181-186` · `ban_ghi.py:173-177` |
| 14 | Tất định | ⛔ **không** (`random.uniform` trong vùng lặng) | ✅ có (vân tay `ban_ghi.py:180-199`) | `30_PARITY…:39-46` |
| 15 | Sửa chữ theo ngôn ngữ | V5 + từ điển **vi/en** | ⛔ không | `sua_chu.py:14` |
| 16 | Ngôn ngữ phục vụ | vi / en | **zh** (hardsub Hán) | `L_OCR.md:15-20` |
| 17 | Đối soát với bản gốc | ✅ 1.932 cặp (§5) | ⛔ không có bản gốc để đối soát | `30_PARITY…` |

---

## 4. 🔴 CÂU 3 — Mỗi điểm khác là CỐ Ý hay TAI NẠN?

⭐ **Cả hai đều không.** Nó là một **tai nạn về THỨ TỰ THỜI GIAN**, và đó là một hạng mục
riêng — ⛔ đừng xếp nhầm vào "trôi".

| SHA | Ngày | Việc |
|---|---|---|
| `e3cdbabe` | **02/09/2026** | `feat(auto_scan_video): pha 00-14 …` — sinh ra `ban_ghi.py`, `thoi_gian.py`, `giai_doan_thoi_gian.py`, `giai_doan_chep_loi.py` |
| `4940c833` | **10/09/2026** | `Phase 08: App \`transcript\` …` — sinh ra `phien_am.py` và `engine/segment/core.py` |

⇒ Khi ASV chọn đường phân đoạn, **(A) chưa tồn tại — còn tám ngày nữa**.
⛔ Không phải ASV từ chối (A). ⛔ Cũng không phải ASV trôi khỏi (A).

### 4.1 ⭐ Và ASV **đã** khảo sát tái dụng — chỉ là khảo sát một kho khác

`docs/auto_scan_video/DEPENDENCY_MAP.md` (thêm trong `e3cdbabe`) có hẳn mục
**"3.1 Already inside the platform (highest-value reuse)"**, và mục ấy chỉ có
`apps/autosubvideo/`. Bộ phân đoạn của `bot_transcript` nằm ở mục
**"3.2 External legacy trees (reference only)"**, dòng
`BOT_TRANSCRIPT/Bot_Whisper_FULL/engine/… + segment/ (13 modules)`, gắn cờ *dính
`gpu_arbiter`*. `FULL_AUTO_VIDEO` ghi **"NO — reference only"**.

⇒ 🔑 Ngày 02/09, *"13 mô-đun segment"* là **mã legacy ngoài kho, dính GPU arbiter** ⇒
loại là **đúng**. Ngày 10/09 nó thành **mã nền tảng, sạch arbiter, có 1.932 cặp đối
soát** ⇒ lý do loại **hết hiệu lực**, và ⛔ **không ai rà lại**.

### 4.2 Bốn khẳng định về sự VẮNG MẶT (đã tra, ⛔ không tìm thấy)

* `git log -S"apps.transcript" -- apps/auto_scan_video/` → **rỗng**.
* `git log -S"make_timeline" -- apps/auto_scan_video/` → **rỗng**.
* `grep "apps.transcript|phien_am|make_timeline"` trong `apps/auto_scan_video/` → **rỗng**.
* ⛔ **Không một commit message nào** trong kho bàn việc ASV có nên dùng lại (A).
  (`--grep` cho `tái dụng` / `ủy quyền` / `bọc mã` → 0; `ADR-001` → toàn bài toán tiền.)
  ⚠️ `git log --all` **hỏng** (`fatal: bad object refs/codex/…`); đã dùng `--branches --tags`.

### 4.3 Riêng hai điểm **CỐ Ý** — ⛔ đừng bỏ

* **Bọc `autosubvideo` thay vì uỷ quyền job** (điểm 1): `giai_doan_chep_loi.py:7-23` giải
  thích theo ADR-001 D5 — `apps/autosubvideo/manifest.py:47,51` khai `requires=("ffmpeg",)`
  mà vẫn khai `gpu_vram_mb` (RISK-00-11) ⇒ uỷ quyền là thừa kế một bản khai sai. Chốt bằng
  test AST ở `587bbfd6` (03/09).
* **Mô hình thời gian lồng tiếng**: `docs/auto_scan_video/adr/ADR-003-mo-hinh-thoi-gian.md`,
  Status ACCEPTED, 01/09/2026. `e3cdbabe` ghi *"xay lai theo dan chung cong dong"* —
  hằng số mượn SoniTranslate / Subdub, `TRAN_TROI_SO_DOAN = 3` là *"CUA TA"*
  (`thoi_gian.py:43-62`). ⇒ **Cố ý, có ADR.** ⛔ Đây ⛔ không phải phân đoạn (xem §7).

⇒ ⭐ Phán quyết: **điểm 9–12, 15 (vắng mặt hoàn toàn lớp cắt/gộp/khoảng lặng) là TAI NẠN
THỨ TỰ — đáng xét bỏ. Điểm 1, và toàn bộ `thoi_gian.py`, là CỐ Ý — giữ.**
Điểm 3–8 (tham số ASR không ghim) ⛔ **chưa ai quyết** — nó là mặc định thư viện, không
phải lựa chọn; xem §6, lựa chọn 0.

---

## 5. CÂU 4 — App phiên âm được đối soát bằng gì? ✅ Có số.

`docs/migration/workflow_apps/30_PARITY_VOI_BOT_THAT.md`, đo 10/09/2026,
bộ đối chiếu `tests/test_1108_parity_transcript.py`.

**Kho vàng**: `Bot_Whisper_FULL/output/<drive_folder_id>/` — **1.932 cặp** job thật đã
giao, mỗi cặp `transcript_raw_temp.json` (vào, có `words`) + `transcript.json` (ra)
(`:13-22`). ⛔ Không cần GPU, không cần audio.

**Tiêu chí ban đầu đổ** (`:26-46`): *"trùng khớp từng byte"* là **bất khả về nguyên tắc** —
`segment/silence.py::split_silence_segments_random_2_5` cố ý gọi `random.uniform`; chính
bot gốc chạy lại cũng không tái hiện được đầu ra của nó (3 lượt → 3 kết quả).

**Tiêu chí đúng** (`:52-58`): T1 đoạn `speech` trùng tuyệt đối (`start`,`end`,`text`) ·
T2 **vùng** lặng trùng tuyệt đối · T3 liên tục, không hở không chồng.

| Toàn kho 1.932 cặp | Đạt T1+T2+T3 |
|---|---|
| engine **GỐC** so với đầu ra của **chính nó** | **1850/1932 = 95,76 %** |
| bản **CHUYỂN** so với cùng đầu ra ấy | **1845/1932 = 95,50 %** |

Bốn lượt rút mỗi bên (`:66-71`): gốc `95,76 / 95,60 / 95,24 / 95,19` · chuyển
`95,50 / 94,93 / 95,65 / 95,70` — ⭐ ở lượt 2 **bản chuyển vượt bản gốc**.

> `:76` — *"Nếu bỏ cột 'engine GỐC', báo cáo sẽ đọc ra là 'thiếu 4,5 %' và sẽ có người đi
> sửa một thứ không hỏng."*

**Ba thứ chỉ lộ khi đối chiếu** (`:80-104`): `__init__.py` rơi 5 tên tái xuất · tham số
thật `segment.min_s = 1.5` ≠ mặc định mã `3.0` · một *"đứt quãng"* thật ra là dung sai sai
(0,02 s do hai tầng `round(...,2)`; nới `0.021` ⇒ **1932/1932**).

**Bộ mẫu trong kho**: `tests/golden/parity_transcript/` — 5 cặp, 356 KB, byte nguyên vẹn,
**chọn** trong nhóm engine chạy **20/20 lượt ra cùng kết quả** ⇒ phép kiểm gate là khẳng
định chính xác, ⛔ không chớp (`:106-112`).

**Con số EN 98/98 mà kho nhớ ghi**: ⛔ **không tìm thấy** trong `docs/` lẫn `tests/`.
`apps/transcript/manifest.py:56-57` có chép lại (*"khớp tuyệt đối trên EN 98/98 đoạn"*)
nhưng ⛔ không trỏ nguồn. ⚠️ Đây là một khẳng định **chưa có chỗ đỡ trong kho** —
`95,50 %` mới là con số có tệp.

⚠️ **Lỗ độ phủ chính**, `:159-160`: *"**Chưa đo `vad_speech_segments` và tầng STT** — kho
vàng bắt đầu *sau* STT."* ⇒ ⭐ Phần (A) được đối soát là **bước 3–6** (dựng dòng thời gian
+ kiểm). Bước 1–2 (VAD + tham số whisper) ⛔ **chưa từng đo**.

---

## 6. CÂU 6 — Dùng lại thì giá bao nhiêu: **trường nào đi qua, trường nào rơi**

### 6.1 🔴 Cổng cao nhất, và nó đúng hình dạng **N-17**

`apps/transcript/services/phien_am.py:177-204 _chieu_schema()` ép đầu ra về **đúng sáu
khoá** `{start, end, text, type, scene_id, index}` — và docstring nói thẳng (`:181-186`):

> *"Bản đầu của hàm này **giữ `words`** … Cả hai đều **sai** … 6.934/6.934 đoạn ở đó có
> đúng tập khoá … và **0 đoạn** có `words`."*

`_kiem_schema_nghiem_ngat` (`:236-240`) **ném lỗi nếu có khoá thừa**.

⇒ 🔴 Nếu ASV tiêu thụ **đầu ra app-level** của (A):

| Trường | Số phận |
|---|---|
| `start` / `end` | ✅ đi qua (0,01 s) |
| `text` | ✅ đi qua |
| `type` / `scene_id` / `index` | ✅ thêm (ASV chưa dùng) |
| 🔴 **`words` / `tu`** (mốc từng từ) | ⛔ **RƠI TOÀN BỘ** |
| `language` / `engine` / `alignment_status` | ⛔ rơi (nằm ngoài `transcript`, ở `KetQua`) |
| `confidence` (`do_tin`, nhánh OCR) | ⛔ rơi |

⚠️ Đây **đúng** ca N-17 lần thứ tư: một chỗ nối vứt trường **im lặng**. Và lần này nó vứt
thứ **đắt nhất** — mốc từng từ do `whisperx.align` sinh ra, thứ ASV đã trả một lượt GPU để
có, và là thứ **duy nhất** đỡ được khớp môi.

⭐ **Cửa rẻ**: nhập **hàm** `make_timeline_v2` (`engine/segment/core.py`) chứ ⛔ không nhập
**đầu ra app**. `words` sống trong ống của (A) và chỉ chết ở `_chieu_schema` — bỏ qua
bước 5 thì nó không chết.

### 6.2 Hai thứ sẽ **vỡ ngay**, ⛔ không phải rơi âm thầm

1. **Đoạn `silence` thành lời thoại giả.** (A) sinh đoạn `type="silence"`,
   `text="[B-ROLL / PAUSE]"` (`phien_am.py:92`). `ban_ghi.kiem` (`ban_ghi.py:170-171`) bắt
   mọi đoạn phải có `chu` ⇒ đoạn lặng **lọt** thành đoạn hợp lệ, rồi được **dịch** và
   **đọc thành tiếng**. ⇒ Phải lọc `type != "silence"` tại biên — (A) đã có sẵn công tắc
   `include_silence` (`phien_am.py:344-345`).
2. **Bất tất định vào vân tay.** `random.uniform` trong `silence.py` ⇒ cùng tiếng, hai lượt,
   hai bản ghi khác nhau, mà `van_tay_ban_ghi` (`ban_ghi.py:180-199`) băm **tham số** chứ
   không băm **kết quả** ⇒ cache trả sai bản. Tắt `include_silence` thì hết — nhánh ngẫu
   nhiên chỉ chạm vùng lặng.

### 6.3 Đường nhập, và nó **chưa mở**

`apps/auto_scan_video/giai_doan_chep_loi.py:17-20` nói cạnh phụ thuộc liên-app được khai ở
`tools/lint_app_contract.py` + `apps/autosubvideo/__init__.py`. Cơ chế là
`BE_MAT_CONG_KHAI` (`lint_app_contract.py:312-318, 353-378`).

* `apps/autosubvideo/__init__.py` ✅ có, khai 12+ tên (`BE_MAT_CONG_KHAI`, dòng 17-65).
* 🔴 `apps/transcript/__init__.py` ⛔ **chỉ có một dòng docstring** — ⛔ không có
  `BE_MAT_CONG_KHAI`. ⇒ Mọi `from apps.transcript...` **bị linter chặn** cho tới khi (A)
  khai bề mặt. Rẻ (một tuple), nhưng là một **quyết định nhìn thấy được** — đúng ý đồ.

### 6.4 Ba khác biệt **ngữ nghĩa** phải trả giá, ⛔ không phải chi phí nhập

| | Vấn đề | Giá |
|---|---|---|
| **zh** | Hồ sơ STT của (A) chỉ có nhánh *tự dò/en* (beam 1) và *vi* (beam 5) — ⛔ **không có `zh`** (`ho_so.py:82-101`). `sua_chu_v5` chỉ có từ điển `vi_corrections` / `en_corrections` (`sua_chu.py:14`). Phim của ASV là **tiếng Trung** (`L_OCR.md:15`). | Phải thêm một hồ sơ `zh`, **và đo lại** — ⛔ ngưỡng mượn phải đo lại. |
| **VAD hai lần** | (A) **cấm** `vad_filter` vì nó chạy VAD riêng (`ho_so.py:37-38`). ASV đang chạy WhisperX, có VAD **trong**. Ghép thẳng = **VAD hai lần** ⇒ *"ranh giới đoạn đổi"*. | Phải chọn **một** đường: hoặc WhisperX (bỏ `vad.py`), hoặc faster-whisper + `vad.py`. ⛔ Không có đường ở giữa. |
| **mốc từ** | (A) dùng `words` của faster-whisper (`_kiem_co_mocs_tu`, `phien_am.py:162-174`); ASV có `words` của **`whisperx.align`** (mịn hơn). `make_timeline_v2` nhận `doan_tho` có `words` ⇒ ⭐ **ăn được mốc WhisperX**. | ⭐ **Giá 0** — đây là chỗ khớp tốt nhất giữa hai app. |

---

## 7. ⭐ Mục đích khác nhau — **dùng lại được BAO NHIÊU**

⛔ Ba bài toán, ⛔ đừng gộp:

```
(A) transcript   : chia đoạn để NGƯỜI ĐỌC theo dõi + cắt B-ROLL   → 1,5–6,0 s, có khoảng lặng
(B) autosubvideo : chia đoạn để HIỂN THỊ                          → theo ký tự/dòng
(C) ASV          : chia đoạn để DỊCH và ĐỌC THÀNH TIẾNG           → khe thoại đủ dài
```

**(B) cắt theo dòng hiển thị**, ⛔ không theo tiếng: `segmenter.py:27-28`
`max_chars_per_line=42`, `max_lines=2`; `_segment_short_form` (`:204-254`) và
`_segment_punchline` (`:262-300`) **chia lại thời gian theo TỈ LỆ KÝ TỰ**
(`ratio = len(chunk)/total_chars`) ⇒ 🔴 **mốc sinh ra ở đó là mốc BỊA**, không đo gì.
⛔ Tuyệt đối không dùng nhánh ấy làm nguồn thời gian. ⭐ ASV đã dùng (B) **đúng phần**:
chỉ `wrap_lines`, `SubtitleEvent`, `SegmentMode`, `build_ass` (`apps/auto_scan_video/phu_de.py:677,715,141`)
— tức **chỉ phần trình bày**.

**(C) khác (A) ở chỗ nào là THẬT**: `thoi_gian.py:1-33` — ASV cần **khe thoại**, mượn 70 %
khoảng lặng (`TY_LE_MUON_KHOANG_LANG=0.7`, `:48`), mang **nợ** sang đoạn sau, trần tăng
tốc `1.15` (`:55`), trần nợ 3 đoạn (`:62`). ⇒ Với lồng tiếng, một đoạn **dài** là *ngân
sách*; với phụ đề, một đoạn dài là *lỗi*. ⭐ Đây là lý do `HARD_MAX=6.0` của (A) ⛔ **không
được** bê nguyên sang ASV — nó sẽ băm nhỏ ngân sách ngay trước khi `thoi_gian.py` cần gom.

⇒ ⭐ **Trả lời phân tầng:**

| Lớp của (A) | Dùng lại được? | Vì sao |
|---|---|---|
| **VAD ngoài** (`engine/vad.py`, 224 dòng, thuần hàm, 30 ms) | ✅ **DÙNG ĐƯỢC NGUYÊN** | ⛔ không phụ thuộc ngôn ngữ, ⛔ không phụ thuộc mục đích. Chỉ cần audio. ⭐ Cho ASV một **kênh đo onset độc lập với whisper** — xem §8, lựa chọn 2. |
| **Mốc từ + `word_scene_builder`** (892 dòng) | ✅ **DÙNG ĐƯỢC**, ăn thẳng `words` của WhisperX | Ranh giới từ ⛔ không phụ thuộc mục đích |
| **Chấm điểm ranh giới** (`W_PUNCT/W_PAUSE/W_LEN`, `merging`/`splitting`) | ⚠️ **DÙNG ĐƯỢC PHẦN CƠ CHẾ, ⛔ ĐỔI THAM SỐ** | Cơ chế trung lập; `HARD_MIN/HARD_MAX = 2.0/6.0` là của **phụ đề + B-ROLL** ⇒ phải đo lại cho lồng tiếng |
| **Khoảng lặng → đoạn `silence`** (`silence.py`) | 🔴 **⛔ KHÔNG** cho đường bản ghi | Đẻ lời thoại giả (§6.2) **và** bất tất định. ⭐ Nhưng **danh sách vùng lặng** thì ASV **rất cần** — nó là đầu vào ngân sách của `thoi_gian.py` (`:26-31`) và hiện ASV ⛔ **không hề có** |
| **6 khoá + `_chieu_schema`** | 🔴 **⛔ KHÔNG BAO GIỜ** | Vứt `words` (§6.1) |
| **`sua_chu_v5`** | ⛔ không (vi/en) | ⛔ không có zh |

---

## 8. Lựa chọn kèm giá — ⛔ không khuyến nghị

> ⭐ Hai trục **độc lập**: (I) chân lý nền, (II) bộ phân đoạn. Ghép tự do.

### Trục I — chân lý nền (gỡ trần 0,606)

| # | Làm gì | Giá | Được gì |
|---|---|---|---|
| **I-0** | Giữ nguyên, báo B1 **chỉ ở ±0,5 s** | 0 | Hiện trạng `B2:192-196`. 🔴 ⛔ Không đo được gì dưới 0,5 s — **mãi mãi** |
| **I-1** | Chạy lại OCR v2 ở **10 fps** làm chân lý nền mới | ⚠️ **một lượt OCR nặng** (CPU, venv đo lường; `L_OCR.md:162`: `40×0,41 s + 10×190×0,066 s` ≈ **142 s**). ⛔ Phải qua `chay_nang.py`. Bản 10 fps **đã từng chạy** (`L_OCR.md:102`) nhưng ⛔ tệp không còn trong kho | Lưới **0,1 s**, **107 dòng** (gấp 3,2× số mục ⇒ KTC hẹp lại), CER 0,003. ⭐ Trần 0,606 → **~1,0** |
| **I-2** | I-1 **+ trừ bias +0,34 s** (`L_OCR.md:133`) | thêm 0 (số đã có) | Chuyển từ *mốc hiện phụ đề* sang **ước lượng mốc nói**. ⚠️ Còn p95 0,46 s chưa giải thích ⇒ ⛔ **không** phải chân lý nền thật cho onset nói |
| **I-3** | Dùng **dự án khách đã sửa tay** (`app_projects`, `StudioCue`) | 🔴 **cần chủ dự án cho phép dùng dữ liệu production**; chưa ai đếm có bao nhiêu bản sửa | ⭐ Chân lý nền **thật** duy nhất (người sửa), float, có `words`, nhiều phim. ⭐ Gỡ luôn *"một phim, một chân lý nền"* (`B2:215`) |
| **I-4** | Mở rộng chân lý nền tay sang phim **v3/v4** | công đọc tay; ⛔ **v4 không có bằng chứng phân đoạn ở bất kỳ cây nào** (`B2:217-219`) | Chống *"một phim"* — nhưng vẫn lưới tay |

### Trục II — bộ phân đoạn

| # | Làm gì | Giá | Được gì |
|---|---|---|---|
| **II-0** | Giữ WhisperX thô. ⭐ **Nhưng GHIM tham số** (điểm 3–8) vào một hồ sơ có tên | rẻ; ⛔ phải đo lại vì `condition_on_previous_text` đang là mặc định `True` | ⭐ Biến 6 mặc định thư viện **vô danh** thành một quyết định có tên. ⛔ Hiện B1 đang chấm một thứ **chưa ai ký** |
| **II-1** | Mượn **`engine/vad.py`** làm kênh onset thứ hai (⛔ không đổi bản ghi) | thấp: thuần hàm + `ffmpeg`; cần `BE_MAT_CONG_KHAI` ở (A) | ⭐ Phân biệt *"WhisperX cắt sai"* với *"chân lý nền lệch"* — hai thứ B1 hiện **gộp làm một**. ⭐ Và cho `thoi_gian.py` danh sách vùng lặng nó đang thiếu |
| **II-2** | Nhập **`make_timeline_v2`** làm hậu xử lý sau WhisperX | vừa: `BE_MAT_CONG_KHAI`; **bắt buộc** `include_silence=False` (§6.2); ⛔ **không** đi qua `_chieu_schema`; phải đo lại `HARD_MIN/MAX` cho lồng tiếng (§7) | Sàn/trần độ dài được **cưỡng chế** thay vì chỉ **đo**. ⭐ Kéo theo 1.932 cặp đối soát của (A) |
| **II-3** | Uỷ quyền cả job sang (A) | 🔴 **cao** — vứt `words` (§6.1), vứt `canh_chinh`, vứt `do_tin` OCR, bất tất định, ⛔ không có zh | ⛔ Không thấy lợi nào mà II-2 không có |

### ⚠️ Ba việc ⛔ **không** trả tiền mà vẫn phải làm

1. **Thước B1 ⛔ không phân tầng theo `canh_chinh`** — WhisperX (`aligned`) và
   faster-whisper (`fallback_unaligned`) cắt khác nhau (§3.2) mà 0,903 / 0,909 gộp cả hai.
   `ban_ghi.py:120-124` đã giữ sẵn nhãn.
2. **`L_OCR.md:134` và `B2:159-175` kết luận cùng một điều, ⛔ không tệp nào trỏ tệp kia** —
   ba ngày, hai làn, cùng một phát hiện trả tiền hai lần.
3. **`manifest.py:56-57` khai *"EN 98/98 đoạn"* ⛔ không nguồn** (§5) — hoặc tìm ra tệp,
   hoặc sửa thành `95,50 %` là con số **có** tệp.

---

## 9. Một câu, nếu chỉ đọc một câu

> ⭐ ASV **CÓ** tự viết phần cắt đoạn (`cat_doan.py`, `de3a1d4c`, ⛔ chưa lên `main`), và
> nó **cố ý, có nguồn** — vì cả WhisperX lẫn app phiên âm đều **mù tiếng Hán** ở lớp cắt
> câu (Punkt không có `zh`; `SENT_SPLIT_RE` đòi `\s+`). App phiên âm ra đời **sau ASV tám ngày** (`e3cdbabe` 02/09 → `4940c833` 10/09) và lúc khảo
> sát tái dụng thì bộ phân đoạn còn là mã legacy ngoài kho. Và trần **0,606** ⛔ không cần
> một chân lý nền mới: một bản **10 fps của chính phim v2** đã từng được dựng và dùng làm
> *"mốc gốc"* ở `L_OCR.md:102` — nó chỉ chưa bao giờ được đem sang làm chân lý nền.

---

## 10. Ba việc điều phối giao 25/09 — trạng thái sau khi soi đĩa

### 10.1 🔴 `N-27` — tiền đề **KHÔNG ĐÚNG**, và sự thật đáng lo hơn

Điều phối mô tả N-27 là *"thước gộp WhisperX với faster-whisper làm một"*. Soi cả ba tệp
bằng chứng (`bang_chung/b1_chep_loi_moi/{v1,v2,v3}.json`, có ở
`LTTSTUDIOSAPP-{asvf-nghiem-thu-v2,gop,repro-3300}`, ⛔ **không có** ở `main`):

| tệp | `engine` | `canh_chinh` | số đoạn |
|---|---|---|---|
| `v1.json` | `whisperx` | `aligned` | 83 |
| `v2.json` | `whisperx` | `aligned` | 74 |
| `v3.json` | `whisperx` | `aligned` | 31 |

⇒ ⛔ **Không có gì để phân tầng.** Thước ⛔ chưa bao giờ chạm faster-whisper.
Khuyết tật thật là: **đo MỘT nhánh, khai như thể trung lập với engine**, và nhánh
`fallback_unaligned` có **0 bằng chứng**. Tách thành hai bảng sẽ cho một bảng có số và một
bảng **rỗng** — ⭐ và chính cái rỗng ấy mới là phát hiện.

⭐ Thuốc đúng ⛔ không phải "phân tầng", mà là **bắt thước KHAI nhánh nó đang đo** và
**từ chối** khi tập bằng chứng trộn hai `canh_chinh` — cùng họ với bất biến
`canh_chinh == "aligned"` ⇒ bắt buộc có mốc từ, mà `de3a1d4c` §1.3 vừa dựng.

### 10.2 🔴 Chặn `VIỆC 1`: thước ⛔ KHÔNG học được lưới từ dữ liệu

```python
# tools/do_luong.py:1009-1012
def doi_chung_he_hoan_hao(ref, dung_sai, luoi: float = LUOI_CHAN_LY_NEN_S, ...)
# tools/do_luong.py:1047-1049
def kiem_nguong_voi_toi(ref, dung_sai, nguong):
    tran = doi_chung_he_hoan_hao(ref, dung_sai)      # ⛔ KHÔNG truyền `luoi`
```

`LUOI_CHAN_LY_NEN_S = 0.5` là **hằng số mô-đun**, và `CHAN_LY_NEN_PHAN_DOAN` là một
**đường dẫn cứng** (`:1071`). ⇒ 🔴 **Thay chân lý nền bằng bản 0,1 s mà không sửa thước thì
trần vẫn tính theo lưới 0,5 s và vẫn in `0,606 — KHÔNG VỚI TỚI ĐƯỢC`.** Cổng sẽ nói dối
theo đúng chiều cũ, trên một chân lý nền ⛔ không còn khuyết tật ấy.

⇒ ⭐ **Lưới phải là thuộc tính CỦA TỆP chân lý nền, ⛔ không phải hằng số của thước.**
`l_ocr_gt_v2.json` đã có trường `cach_lam` nói lưới bằng **chữ**; nó cần một trường **số**
mà `doc_chan_ly_nen_ocr()` đọc lên và chuyền vào `kiem_nguong_voi_toi`.
⚠️ Đây đúng họ *"bánh cóc đo CÁCH GÕ"*: thước ghim cứng một tính chất của **dữ liệu** mà
nó đang đo.

### 10.3 `VIỆC 1` — chạy được, nguyên liệu đủ, ⛔ chưa chạy

| thứ cần | trạng thái |
|---|---|
| video v2 `暴雨天野外露营….mp4` (26 MB) | ✅ `C:\Users\…\Desktop\TEST VIDEO\` |
| bộ OCR `asv_gpu/do_luong/ocr_khung.py` + venv | ✅ (`nguon_loi.py:211-212`) |
| dòng thời gian 10 fps đã dựng 22/09 | 🔴 **⛔ KHÔNG CÒN** — quét `bang_chung/` cả ba cây: chỉ có `phu_de/dai_hardsub.json` (hình học dải, ⛔ không phải mốc). ⇒ **phải chạy lại** |
| giá | ~**142 s** CPU (`L_OCR.md:162`: `40×0,41 + 10×190×0,066`) ⇒ **lượt nặng**, qua `chay_nang.py`, nhả khoá ngay khi lệnh tính xong |

⛔ **Chưa chạy** vì §10.2 phải xong trước: chạy trước khi thước học được lưới là tiêu một
suất CPU để in lại đúng con số sai.

### 10.4 ⚠️ Hai thứ điều phối dặn, đã ghi sẵn để ⛔ không rơi

1. Nền mới đo **mốc hiện phụ đề**, lệch **+0,34 s** (p95 0,46 s) so với **mốc nói**
   (`L_OCR.md:133`) ⇒ khai độ lệch **cạnh mọi con số**.
2. Chỉ **v2** có nền mới ⇒ ⛔ **không gộp ba phim thành một con số**.
   ⚠️ Thêm một thứ ⛔ chưa ai nói: `v3.json::⚠️ gioi_han` tự khai *"Chan ly nen cua v3 bi
   nhiem 13 dong chu UI game"* ⇒ v3 ⛔ **không dùng được** làm nền, kể cả ở lưới 0,5 s.

### 10.5 `VIỆC 3` — đề xuất `vad.py`: ⭐ **giá trị TĂNG** sau đính chính

`cat_doan.py` cắt bằng **dấu câu + mốc từ** của engine. ⇒ Nó ⛔ **không có** tín hiệu
**âm học** nào. `engine/vad.py` (năng lượng, 30 ms, độc lập whisper hoàn toàn) cho đúng
thứ đang thiếu: một kênh **thứ hai** để hỏi *"chỗ ngắt này có khoảng lặng thật không"* —
và `so_doan_khong_cho_ngat` của `cat_doan` là chỗ nó trả lời được ngay.
⛔ `apps/transcript/__init__.py` vẫn chưa khai `BE_MAT_CONG_KHAI` ⇒ **báo điều phối**,
⛔ không tự sửa.
