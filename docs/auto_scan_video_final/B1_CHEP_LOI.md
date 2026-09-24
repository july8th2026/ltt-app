# B1 — cổng NGHE CHÉP (`transcribe`)

> Làn `asvf-nghiem-thu-v2`, 24/09/2026. Mắt xích **đầu tiên** của thang cổng —
> mọi bước sau đứng trên văn bản nguồn nó tạo ra.

## ⚠️ ĐỌC TRƯỚC KHI ĐỌC BẤT KỲ CON SỐ NÀO Ở ĐÂY

**Bảng kết quả này BẤT ĐỐI XỨNG.** Chân lý nền là **hardsub**, và mọi sai lệch của
nó đều đẩy số sai **LÊN** (§2). Vì vậy:

| kết quả | kết luận được gì |
|---|---|
| **ĐẠT** | kết luận **ngay** — engine khớp cả một chân lý nền không hoàn hảo |
| **TRƯỢT** | ⛔ **chưa kết luận được gì** cho tới khi **soi tay** |

⛔ Một con số trượt **không** chứng minh engine sai. Người đọc trượt sẽ quy cho
engine — đó là lý do dòng này đứng ở đây chứ không nằm trong mục phương pháp.

## ⚠️ ĐƠN VỊ: `ti_le_don_vi_sai` KHÔNG phải WER

Đo 24/09, trên một dòng phụ đề Hán thật:

```
"深度解析跳伞慢了该怎么打"      -> jiwer thấy 1 "từ",  thật ra 12 KÝ TỰ
hai bản chép lệch ĐÚNG MỘT chữ -> tỉ lệ = 0,50   nhưng CER = 0,0417
```

`jiwer.wer` tách bằng **khoảng trắng**, và văn Hán **không có khoảng trắng** ⇒ mỗi
**dòng** thành một "từ". ⇒ Con số đó là **tỉ lệ DÒNG sai**, không phải WER.

⛔ Gọi nó là "WER" là **đặt tên rộng hơn thứ nó đo**, và người sau sẽ so nó với WER
của bảng xếp hạng thế giới — **hai thứ không cùng đơn vị**. Nên bản ghi luôn mang
`don_vi_ti_le` (`dong` | `tu`) cạnh con số, và đơn vị được xác định bằng **đếm chữ
Hán**, ⛔ không suy gián tiếp từ tỉ lệ ký tự/đơn vị (phép suy đó xếp nhầm cả
`"the quick brown fox jumps"` thành `dong`).

## ⚠️ GIỚI HẠN THỨ HAI: CER không phủ được MỐC THỜI GIAN

Sản phẩm là **lồng tiếng**. Một bản chép đúng **từng chữ** mà **sai mốc** cho CER đẹp
và tiếng **lệch môi** — tức hỏng ở đúng thứ khách mua.

`canh_chinh = "fallback_unaligned"` nghĩa là nhánh **căn chỉnh** không chạy; mốc thời
gian **không căn** đi thẳng vào `timing_align`, nơi quyết định mỗi câu rơi vào khe
nào. ⇒ **CER một mình không phủ được rủi ro này.** Bảng §4 phải đọc kèm cột `engine`
và `canh_chinh`.

⭐ Vì thế `fallback_unaligned` là **hạng A** (chủ dự án thu hẹp phạm vi 24/09), không
phải một ghi chú bên lề.

## 1b. ⛔ CÂU HỎI NGƯỠNG — đang chờ điều phối, KHÔNG tự quyết

`WER ≤ 0,25` ở §1 được viết cho một tỉ lệ **TỪ** sai. Trên văn Hán đơn vị là **DÒNG**
⇒ áp 0,25 cho nó là dùng một ngưỡng **chưa từng được hiệu chỉnh** cho đơn vị ấy: hai
dòng lệch một chữ đã cho 0,50.

⇒ Hiện tại `dat` **chỉ xét CER**; tỉ lệ dòng sai được **báo cáo nhưng không phán
xử**. ⛔ Đây **không phải** nới ngưỡng — ngưỡng CER giữ nguyên 0,12, và câu hỏi được
nêu **trước** khi đo phim nào.

## 1. NGƯỠNG — viết TRƯỚC khi đo, ⛔ không nới

```
ĐẠT khi:  WER ≤ 0,25  VÀ  CER ≤ 0,12
          trên ≥ 3 phim CÓ TIẾNG NÓI (món ăn · cắm trại · PUBG)
```

⛔ **Không đạt ⇒ sửa rồi đo lại. KHÔNG nới ngưỡng.** Nếu ngưỡng sai thì phải nói ra
là ngưỡng sai *trước* khi nhìn số, không phải sau.

**Vì sao mức đó.** CER đo được trước đây là **0,018** trên **1 clip 33 dòng** ở một
đường **KHÁC** (faster-whisper CPU, văn bản đối chiếu **tay**). Hardsub có thể **rút
gọn** so với lời nói, nên ngưỡng phải lỏng hơn số cũ — nhưng 0,25/0,12 vẫn là một
**ngưỡng**, không phải một mô tả.

⛔ **Phim súng hơi (`真人气枪游戏…`) KHÔNG dùng** — B0 ghi *"không chắc có giọng"*.
Một phim không có tiếng nói không đo được đường nghe chép, và đưa nó vào sẽ cho một
con số trông như thất bại của engine.

## 2. ⚠️ GIỚI HẠN CỦA CHÂN LÝ NỀN — đọc cùng lúc với mọi con số ở §4

Hardsub **không phải** bản ghi lời nói. Nó là **bản chữ do người làm phim viết**, và
nó có thể:

| | hệ quả lên WER |
|---|---|
| **rút gọn** lời nói (bỏ từ đệm, gộp câu) | WER **cao giả** — ASR chép đúng thứ người nói, hardsub không có |
| viết lại cho gọn màn hình | WER cao giả |
| bỏ hẳn đoạn không quan trọng | WER cao giả |
| sai chính tả / thiếu dấu | WER cao giả, **không** phải lỗi ASR |

⇒ **Mọi con số WER ở §4 phải đọc kèm dòng này.** Một WER 0,3 ở đây **không** chứng
minh ASR sai 30 % — nó nói *"ASR và hardsub khác nhau 30 %"*, và phần nào thuộc về ai
thì phép đo này **không tách được**.

⭐ Chiều lệch là **một phía**: các nguyên nhân trên đều đẩy WER **lên**. Nên một WER
**thấp** là bằng chứng mạnh (ASR khớp cả một chân lý nền không hoàn hảo); một WER
**cao** là bằng chứng **yếu**, và phải soi tay trước khi quy cho engine.

## 3. Cách chuẩn hoá trước khi so — ghi ra, ⛔ không để trong mã

`tools/bench_b1_chep_loi.chuan_hoa` — **bỏ HÌNH THỨC, giữ NỘI DUNG**:

| bỏ | giữ |
|---|---|
| dấu câu (`[^\w\s]`) | mọi chữ |
| khoảng trắng thừa | khoảng trắng **có nghĩa** (Latin) |
| khác biệt NFC/NFKC | |
| hoa/thường | |

⛔ **Không tự chế phép tách từ tiếng Trung.** Văn bản Hán không có khoảng trắng, nên
**WER theo "từ" trên tiếng Trung ít nghĩa hơn CER**. Cả hai đều được báo cáo, và
**CER mới là số đáng tin** ở đây. Một bộ tách từ tự chế sẽ tạo ra một đơn vị đo
không ai kiểm được — cùng họ với công thức Dice tự chế mà M-01 đã phải xoá.

⛔ **Không dùng OpenCC** (giản↔phồn): máy này **chưa cài** (`ModuleNotFoundError`),
và cài thêm một phép biến đổi **chưa đo** vào giữa chân lý nền là thêm một biến.
Nếu số cuối lệch vì giản/phồn thì việc đó phải hiện ra ở **soi tay**, rồi mới thêm.

### Đối chứng của chính bộ đo — ĐÃ CHẠY

```
giống hệt          WER 0,0000   CER 0,0000
làm hỏng 30 % từ   WER 0,2857   CER 0,2857     RESULT: PASS
```

⭐ Không có bước này thì một WER thấp có thể chỉ là **bộ đo hỏng**, và nó sẽ **im
lặng** cho mọi engine đạt (*"số 0 cần đối chứng"*).

## 4. Kết quả

*(điền sau Bước 4 — mỗi dòng kèm: engine thật, card có được cấp không)*

⚠️ Đọc cùng lúc với §2 (giới hạn chân lý nền) và mục *ĐƠN VỊ* ở đầu tệp.

Cả ba lượt: nhánh **whisperx `aligned`**, **card được cấp**, `media_prepare` thật,
ép `nguon_loi=asr` (đọc lại từ `outputs`, không từ form).

| phim | CER | đoạn asr | đoạn hardsub | `lech_doan` | s/đoạn asr | giây ASR |
|---|---|---|---|---|---|---|
| 1 · món ăn | **0,0349** ✅ | 11 | 102 | **0,8922** ⛔ | 23,3 | 99,7 |
| 2 · cắm trại | **0,0245** ✅ | 8 | 107 | **0,9252** ⛔ | ~23,8 | 43,5 |
| 3 · PUBG | 0,2551 → **0,0574** ✅ ¹ | 6 | 95 | **0,9368** ⛔ | ~24 | 48,1 |

¹ **Chân lý nền của phim 3 bị NHIỄM, đo được:** hardsub chứa **13 dòng chữ UI game**
(kill-feed — `你使用M416突击步枪击倒了…` = *"bạn hạ gục X bằng M416"*). Không ai **nói**
chúng, nên ASR đúng khi không chép. Bỏ 13 dòng đó: **CER 0,2551 → 0,0574**, và số ký
tự khớp hẳn (hardsub 831 → 628 · asr 646).

⛔ **Đây không phải nới ngưỡng.** Ngưỡng `0,12` không đổi; thứ được sửa là **chân lý
nền**, và việc nó nhiễm đã được ghi **trước khi đo** — `PLAN.md` kiểm kê B0 ghi phim
v3 *"có hardsub + chữ UI game"*. ⚠️ **Đó là cái tôi đã có trong tay và vẫn chọn phim
này** — lẽ ra phải loại như đã loại phim súng hơi, hoặc lọc UI ngay từ đầu.
⇒ Cả hai con số đều ghi ở đây; ⛔ không thay số thô bằng số sạch.

⭐ Và nó minh hoạ đúng **luật bất đối xứng ở đầu tệp**: một CER **cao** là bằng chứng
**yếu** — soi tay xong thì nguyên nhân nằm ở chân lý nền, không ở engine.

## 5. Phán quyết

```
CER        3/3 ĐẠT   (0,0349 · 0,0245 · 0,0574   — ngưỡng 0,12)
lech_doan  0/3 ĐẠT   (0,8922 · 0,9252 · 0,9368   — ngưỡng 0,20)
```

# ⛔ **B1 KHÔNG ĐẠT** — một nguyên nhân duy nhất: **gộp đoạn**

**Chất lượng nội dung xuất sắc** (CER ≤ 0,058 trên cả ba). Thứ hỏng là **phân đoạn**.

### Nguyên nhân — đọc từ gói đã cài, ⛔ không suy

```
whisperx  FasterWhisperPipeline.transcribe(..., chunk_size=30, ...)
whisperx_runner.py:23   model.transcribe(audio, batch_size=8, language=…)
                        ⇒ `chunk_size` KHÔNG khai ⇒ mặc định 30 giây
```

Đo khớp: **~24 giây/đoạn** trên cả ba phim ≤ 30. WhisperX gom theo **khối VAD ~30 s**
cho suy luận theo lô — "segment" của nó là **khối**, không phải **câu**.

⭐ **Không phải lỗi của WhisperX — đó là thiết kế đường batched. Lỗi là TA dùng khối
30 giây làm khe lồng tiếng.**

### Vì sao 24 s/đoạn là hỏng, không phải "khác"

Với sản phẩm **lồng tiếng**, **phân đoạn CHÍNH LÀ sản phẩm**: mỗi đoạn là một **khe**
để đặt câu tiếng Việt. Một khe 24 giây liền mạch thì `timing_align` **không còn gì để
canh** — nó phải nhét 24 giây lời Việt vào một khối không có điểm ngắt, và khách nghe
tiếng **trôi so với miệng**.

⚠️ Mốc tham chiếu không phải do ta nghĩ ra: **hardsub cho 2,4 s/đoạn** — phân đoạn do
**người làm phim** chọn cho chính nội dung này.

### Task 7 — nửa câu trả lời đã có

Nhánh mặc định (whisperx `aligned`) **nhanh hơn 3,6×** nhánh lui (99,7 s vs 362,0 s
trên phim 1) và CER tốt. ⇒ Nghiêng hẳn về nhánh mặc định. Nửa còn lại — *"nó có cắt
đoạn dùng được không"* — là việc kế tiếp.

### Đường sửa: cắt lại bằng MỐC TỪNG TỪ

Nhánh `aligned` cho **mốc từng từ**. ⇒ Tự cắt khối dài tại chỗ ngắt câu / khoảng lặng
bằng chính mốc đó. **Không phụ thuộc tham số engine** ⇒ sống sót khi nâng cấp
WhisperX, và giữ nguyên tốc độ (batching là lý do nó nhanh).

⛔ Hạ `chunk_size` là **sửa nhầm chỗ**: bắt engine làm việc nó không sinh ra để làm,
và trả giá bằng chính cái làm nó nhanh.

⚠️ **Rủi ro của việc cắt lại: cắt GIỮA CÂU — tệ hơn gộp.** Gộp cho khe quá dài; cắt
giữa câu cho một khe chứa **nửa ý**, và bản dịch của nửa ý đó **sai nghĩa**. ⇒ Chỉ cắt
tại **dấu câu hoặc khoảng lặng đủ dài**; khối nào không có chỗ ngắt hợp lệ thì **để
nguyên và khai ra**, ⛔ không chẻ bừa để đạt số đoạn.

⚠️ **Và khi đo bản cắt lại, `lech_doan` một mình KHÔNG đủ:** nó so **số đoạn**, không
so **chỗ ngắt**. Hai cách cắt cùng cho 102 đoạn mà lệch hết chỗ ngắt thì cổng **xanh**
trong khi khe vẫn sai. ⇒ Báo thêm **tỉ lệ ranh giới khớp** (±0,3 s so với hardsub) —
⛔ **chỉ báo**, không thành cổng.

## 6. ⚠️ Nếu bench hỏng: ghi TRIỆU CHỨNG trước, quy nguyên nhân sau

Đây là lượt **đầu tiên** đường `asr` chạy thật (Task 5 vừa đổi mặc định), nên xác
suất gặp một **tiền đề chưa khai** là cao.

⛔ **Đừng kết luận *"đường `asr` hỏng"*.** Lượt A ngày 24/09 là tiền lệ: một tiền đề
chưa ai khai (AUTO_MATCH đòi nguồn **có tiếng nói**) bị đọc thành *"AUTO_MATCH là
đường chết"*, và mất ba vòng mới tách ra được. Ghi đúng cái **thấy** — mã lỗi, giai
đoạn, số — rồi mới đi tìm **vì sao**.

---

# 7. Làn `b1-cắt-lại` (24/09) — cắt lại bằng mốc từ

## 7.1 ⛔ Tiền đề của §6 SAI: mốc từng từ **chưa bao giờ tới nơi**

Việc được giao là *"cắt lại bằng mốc từng từ nhánh `aligned` **đã** cho"*. Mốc đó
**không tồn tại** ở biên ASV:

```
whisperx/alignment.py:354   word_segment = {"word": word_text}        khoá "word"
ban_ghi.py:89 (cũ)          chu = _lam_sach(t.get("text"))            đọc  "text"
ban_ghi.py:91 (cũ)          if not chu: continue                      BỎ, im lặng
```

| nhánh | khoá engine dùng | `so_tu` |
|---|---|---|
| faster-whisper (lui) | `{"start","end","text"}` | **1031** |
| whisperx (**mặc định**) | `{"word","start","end"}` | **0** |

⭐ Ta trả tiền cho `load_align_model` + `align` — **bước đắt nhất** của nhánh —
rồi ném kết quả đi. Nhánh `aligned` cho ra **đúng thứ `unaligned` cho, chỉ chậm
hơn**. Ghi ở **N-17** (hệ quả thứ hai của cùng một gốc). Sửa: `de3a1d4c`.

## 7.2 ⛔ Và nguyên nhân đoạn dài ở §5 cũng **không phải** `chunk_size=30`

WhisperX **đã** chia khối VAD thành **câu** ngay trong `align()` — nó gọi NLTK
Punkt. Thứ hỏng là Punkt **không có mô hình cho tiếng Hán**:

```
whisperx/utils.py:130-150   PUNKT_LANGUAGES  — không có 'zh', không có 'ja'
whisperx/alignment.py:190   punkt_lang = PUNKT_LANGUAGES.get(model_lang, 'english')
```

Đo trên gói đã cài (whisperx 3.8.6, `D:\LTTWhisperX`):

```
văn Hán 44 ký tự, 3 câu ngăn bởi 。  ->  Punkt en cho  1  span
văn Anh 3 câu                        ->  Punkt en cho  3  span
```

⇒ Cả khối ~30 s về làm **một** `aligned_subsegment`. Đó chính là con số ~24 s.
⭐ Hạ `chunk_size` **không** sửa được bệnh này — Punkt vẫn không thấy ranh giới
câu nào trong văn Hán — mà mất 3,6× tốc độ của đường batched. §5 nói đúng *"đừng
hạ `chunk_size`"*, nhưng nói đúng **vì một lý do khác**.

## 7.3 ⛔ Rồi cả hai chỗ ngắt hợp lệ đều **KHÔNG tồn tại** — đo, không suy

Lượt thật đầu tiên sau khi sửa `ban_ghi` (phim 3, 646 mốc từ **thật**):

```
dấu câu trong 646 ký tự ASR trả về:   。0   ，0   ！0   ？0   、0   . 0
khe im lặng giữa hai ký tự liên tiếp: 640/640 = 0,000 s   (max 0,000)
```

Whisper trả về văn Hán **không một dấu câu nào**, và WhisperX gán span ký tự
**liên tiếp** nên im lặng bị nuốt vào **độ dài của chính ký tự** (một ký tự dài
2,782 s). ⇒ Không dấu câu **và** không khoảng lặng = **không còn một chỗ ngắt hợp
lệ nào**. Bộ cắt chạy đúng và báo đúng: `so_doan 6 -> 6`,
`so_doan_khong_cho_ngat=5`.

⭐ Đó là lý do bộ cắt **phải** trả về chẩn đoán. Một bộ cắt *"luôn đạt"* ở đây sẽ
đã cắt giữa câu 5 lần và cho một `lech_doan` đẹp.

## 7.4 Nguồn đã tra — ⛔ ta không là người đầu tiên

| nguồn | là gì | dùng/không |
|---|---|---|
| whisperX **#1310** (MỞ) | *"Why WhisperX's sentence segmentation not working for Chinese?"* — trỏ đúng `alignment.py` dòng 195-200 | ⭐ xác nhận §7.2, **không** phải ta suy ra |
| whisperX **PR #1466** (MỞ, đóng #1310) | *"Split Chinese and Japanese into sentences during alignment"* — thêm `CJKSentenceSplitter` | ⭐ **luật cắt chép theo PR này** (BSD-2-Clause) |
| whisperX **#645** (`leexinxu`, 17/08/2024, 3 👍) | `asr_options={"initial_prompt": "以下是中文普通话句子。"}` | ⭐ **cách sửa §7.3** — Whisper bám **văn phong** của prompt |
| whisperX **#519** (MỞ); **#829** đóng làm **trùng** #519 (collaborator 16/02/2026) | sổ cái về cắt phụ đề theo dấu câu | upstream **chưa chốt** ⇒ ta không chờ |
| `whisperx/SubtitlesProcessor.py` (**có sẵn** trong gói đã cài) | cắt theo `，`/liên từ, zh `max_line_length=30` | ⛔ **KHÔNG**: vượt `max_line_length` thì nó cắt ở **ĐIỂM GIỮA** (`midpoint = normal_round((last_split_point + i) / 2)`) — **cắt giữa câu**. Kèm lỗi **#1089** (`save()` không ghi gì khi `advanced_splitting=False`) |
| `jianfch/stable-ts` **MIT** | `WhisperResult('audio.json')` — **nhận kết quả có sẵn**, không bắt chạy lại whisper | ⛔ **KHÔNG**: gói **chưa cài**, để làm việc mà PR #1466 làm bằng ~60 dòng không phụ thuộc. Thêm một gói = thêm một biến, không đổi lấy gì |

### Ngưỡng — tra từ quy chuẩn CÔNG BỐ, ⛔ không tự đặt

Netflix Timed Text Style Guide (đọc 24/09):

| số | nguồn |
|---|---|
| khe **tối đa 7,0 s** · **tối thiểu 5/6 s** | *General Requirements*, bài **215758617** |
| **16 ký tự/dòng**, tối đa 2 dòng · **9 ký tự/giây** (người lớn) | *Chinese (Simplified)*, bài **215986007** |

⚠️ Bài **215346638** là *Russian*, **không phải** tiếng Trung — kiểm tiêu đề trang
trước khi trích. (Đã suýt trích nhầm 42 ký tự/dòng và 17 kt/s.)

## 7.5 Kết quả — ba phim, cùng bộ dữ liệu cũ

Nhánh `aligned` · card được cấp · `media_prepare` thật · `nguon_loi=asr` ép.

| phim | CER trước | **CER sau** | đoạn trước → **sau** | hardsub | `lech_doan` trước | **sau** | ranh giới khớp ±0,3 s |
|---|---|---|---|---|---|---|---|
| 1 · món ăn | 0,0349 | **0,0434** ✅ | 11 → **83** | 102 | 0,8922 | **0,1863** ✅ | 0,9255 |
| 2 · cắm trại | 0,0245 | **0,0275** ✅ | 8 → **74** | 107 | 0,9252 | **0,3084** ⛔ | **1,0000** |
| 3 · PUBG | 0,0574 ¹ | **0,0526** ¹ ✅ | 6 → **31** | 95 (82 sạch) | 0,9368 | **0,6737** ⛔ | 0,9730 |

¹ Chân lý nền phim 3 bị nhiễm (§4): **13 dòng** chữ UI game. Số **thô** sau khi
cắt lại: CER **0,2515**. Bỏ đúng 13 dòng đó ⇒ **0,0526**. ⛔ Ghi **cả hai**, không
thay số thô bằng số sạch.

```
so_tu        0 -> 646 · 1125 · 1157      tu_bi_bo  toàn 0 trên cả ba phim
so_doan_qua_dai          0/0/0           (mọi đoạn <= 7,0 s — ngưỡng Netflix)
so_doan_khong_cho_ngat   0/0/0           (không đoạn nào phải để nguyên)
```

## 7.6 Phán quyết

```
CER        3/3 ĐẠT   (0,0434 · 0,0275 · 0,0526   — ngưỡng 0,12)
lech_doan  1/3 ĐẠT   (0,1863 ✅ · 0,3084 ⛔ · 0,6737 ⛔  — ngưỡng 0,20)
```

# ⛔ **B1 VẪN KHÔNG ĐẠT** — nhưng ⛔ **không phải vì bộ cắt sai**

⭐ **Chỉ báo ranh giới nói thẳng điều đó:** 0,9255 · **1,0000** · 0,9730. Trên phim
2, **82/82** ranh giới ASR trùng một ranh giới hardsub thật trong ±0,3 s. Ta
**không cắt sai chỗ** — ta cắt **ít chỗ hơn**. Ranh giới của ta là một **tập con**
của hardsub, không phải một tập **khác**.

⚠️ **Và đó là chỗ `lech_doan <= 0,20` hỏi sai câu.** Hardsub dài **0,97 s/dòng**
(phim 2: min 0,50 · max 1,75) — đó là **dòng HIỂN THỊ**, cắt theo **bề ngang màn
hình** (quy chuẩn zh: **16 ký tự/dòng**), không phải theo **câu nói**. Đoạn của ta
dài 3,15 s — một **câu**, đúng khe để đặt một câu tiếng Việt.

⇒ Muốn 31 → 95 thì phải cắt **~3 nhát trong mỗi câu**, tức đúng cái **cắt giữa
câu** mà ràng buộc cấm, và với sản phẩm **lồng tiếng** thì nó vô nghĩa: không ai
đọc một câu thành ba khe rồi ghép lại.

⛔ **KHÔNG nới ngưỡng 0,20** — và ⛔ cũng **không** dùng chỉ báo ranh giới để che
con số 0,3084/0,6737. Câu hỏi để điều phối quyết, ⛔ làn này **không tự quyết**:

> `lech_doan` đang so số đoạn ASR với số **dòng hiển thị** hardsub. Với sản phẩm
> lồng tiếng, **khe là câu**, không phải dòng. Cổng này có nên so với **số câu**
> của hardsub (gộp các dòng liên tiếp không kết câu) thay vì số **dòng** không?

⚠️ Đó là một câu hỏi về **cổng đo sai đối tượng**, ⛔ **không phải** một đề nghị
nới ngưỡng — con số 0,20 giữ nguyên trong cả hai trường hợp.

## 7.7 Bài học đo lường của lượt này

⭐ **Một thay đổi "đã áp dụng" mà kết quả không đổi MỘT KÝ TỰ là dấu hiệu nó
chưa bao giờ chạy — ⛔ không phải dấu hiệu nó vô dụng.** Bản vá `initial_prompt`
đầu tiên đọc `args.language`, mà ASV gọi runner với `--language` **rỗng** khi
khách để "tự đoán". Lượt chạy tốn 25,3 giây trên card, `khoa_chung` **khác** lượt
trước (nên **không** phải cache) — và bản chép ra **y hệt từng chữ**. Suýt nữa
kết luận nhầm rằng #645 không ăn thua cho tiếng Hán. Sửa: nhận ngôn ngữ
(`model.detect_language`) **trước**, rồi mới đặt prompt (`edbcbd57`).

---

# 8. Ba cửa cho việc định nghĩa lại chân lý nền — ⛔ **KHÔNG QUA**

Điều phối đồng ý **về nguyên tắc** rằng dòng hiển thị là tạo tác của việc render,
với điều kiện qua **cả ba** cửa. Kết quả: **cửa 1 và cửa 2 không qua**, và cửa 3
lộ một lỗ thủng trong **chính cổng hiện hành**.

⇒ ⛔ **Làn này KHÔNG định nghĩa lại `lech_doan`.** Phán quyết giữ nguyên trên
cổng cũ, và con số duy nhất được báo là con số so với **dòng hiển thị**.

## 8.1 Cửa 1 — luật gộp cơ học từ quy chuẩn công bố: ⛔ **KHÔNG DỰNG ĐƯỢC**

Ba sự thật đo được, ⛔ không suy:

**(a) Phụ đề cứng gần như KHÔNG có dấu câu.**

```
v1 món ăn    102 dòng · 1059 ký tự  ->  0 dấu câu
v2 cắm trại  107 dòng · 1020 ký tự  ->  0 dấu câu
v3 PUBG       95 dòng ·  831 ký tự  ->  1 dấu (？)
ký tự/dòng: tb 10,4 / 9,5 / 8,7   max 16 / 17 / 28
```

⇒ *"Số câu trong phụ đề cứng"* **không có sẵn ở đó**. Và trần 16–17 ký tự/dòng
khớp đúng *Chinese (Simplified)* **215986007** (*"16 characters per line"*) —
tức các dòng này **đúng là** sản phẩm của việc render, như lập luận §7.6.

**(b) Không có hằng số KHE THỜI GIAN nào để trích.** Netflix TTSG *General
Requirements* (**215758617**) ghi trong chính nhật ký sửa đổi của nó:

> `2020-07-24  Timing and frame gap sections removed`

⇒ Bộ quy chuẩn ta đang dùng **đã bỏ** phần khe/frame gap. Một luật gộp dựa vào
khe thời gian sẽ phải **tự đặt** hằng số ⇒ ⛔ đúng thứ cửa 1 cấm. (Và dữ liệu cũng
không ủng hộ: v2 có **98/106** khe giữa dòng = **0,000 s**.)

**(c) Luật dựng từ các hằng số CÒN LẠI thì lật phán quyết theo CẢ HAI CHIỀU.**
Luật G1 — gộp dòng liên tiếp chừng nào khối còn hợp lệ như **một** subtitle event
(≤ 16×2 = **32** ký tự, ≤ **7,0 s**; cả hai đều có nguồn):

| phim | dòng hiển thị | khe G1 | đoạn của ta | `lech` vs **dòng** | `lech` vs **G1** |
|---|---|---|---|---|---|
| v1 | 102 | 44 | 83 | **0,1863** ✅ | **0,8864** ⛔ |
| v2 | 107 | 39 | 74 | **0,3084** ⛔ | **0,8974** ⛔ |
| v3 | 95 | 31 | 31 | **0,6737** ⛔ | **0,0000** ✅ |

⛔ G1 **đổi v1 từ ĐẠT sang TRƯỢT** và **đổi v3 từ TRƯỢT sang ĐẠT hoàn hảo**. Một
thước làm phán quyết nhảy theo cả hai chiều không phải một chân lý nền — nó là
một thước **khác**, đo một thứ **khác** (G1 là phép **nhồi ký tự** tham lam, cho
khe trung bình 5,81 / 4,81 / 3,27 s).

⇒ **Cửa 1 KHÔNG QUA.** Không có luật cơ học nào dựng được từ quy chuẩn công bố mà
khôi phục được *câu nói* từ phụ đề cứng này.

## 8.2 Cửa 2 — đối chứng độc lập với engine: ⛔ **KHÔNG QUA**

Chạy lại phim 3 trên nhánh **faster-whisper** (engine khác, đường mã khác, không
căn chỉnh), áp **đúng** luật cắt của `cat_doan`:

| nhánh | đoạn thô | **câu** (cùng một luật) | đoạn sau cắt | `lech` vs 95 dòng |
|---|---|---|---|---|
| whisperx `aligned` | 6 | **33** | **31** | 0,6737 |
| faster-whisper (lui) | 16 | **17** | **40** | 0,5789 |

⛔ **33 so với 17 — lệch gần gấp đôi.** Hai nhánh của chính sản phẩm ta không
đồng ý được *"phim này có bao nhiêu câu"*.

⭐ Lý do, và nó là một sự thật về bản chất chứ không phải một lỗi: **dấu câu là
PHỎNG ĐOÁN CỦA BỘ GIẢI MÃ**, không phải thuộc tính của âm thanh. Ta vừa tự tạo ra
nó bằng `initial_prompt` (§7.3). ⇒ Một chân lý nền dựng trên nó sẽ **thừa hưởng**
sự dao động của nó, và số câu sẽ đổi theo model/prompt/phiên bản.

⚠️ **Nhưng đối chứng này cũng nói một điều theo chiều ngược lại:** cả hai engine
cho **31–40 đoạn**, ⛔ không engine nào tới gần **95**. Hai đường mã độc lập đều
nói phim này có ~1/3 số đơn vị lời nói so với số dòng hiển thị. Điều đó **ủng hộ**
lập luận §7.6 — nhưng ⛔ nó **không** cho ta một con số đủ ổn định để làm cổng.

## 8.3 Cửa 3 — tiêm lỗi: ⛔ **cổng HIỆN HÀNH có một lỗ thủng**

Không có cổng mới để tiêm, nên tiêm vào **cổng đang dùng** (`lech_doan` vs số
dòng hiển thị, ngưỡng 0,20). Ba cách cắt cố tình tồi:

| phim | dòng HS | **ta (theo câu)** | gộp tất = 1 | **máy móc mỗi 2,0 s** | mỗi 30 s |
|---|---|---|---|---|---|
| v1 | 102 | 83 · **0,1863** ✅ | 1 · 0,9902 ⛔ | 133 · 0,3039 ⛔ | 9 · 0,9118 ⛔ |
| v2 | 107 | 74 · **0,3084** ⛔ | 1 · 0,9907 ⛔ | **95 · 0,1121 ✅** ⬅ | 7 · 0,9346 ⛔ |
| v3 | 95 | 31 · **0,6737** ⛔ | 1 · 0,9895 ⛔ | 54 · 0,4316 ⛔ | 4 · 0,9579 ⛔ |

# ⛔ Trên phim 2, **cắt máy móc mỗi 2 giây — bất kể nội dung — XANH**, trong khi **cắt theo câu TRƯỢT**

⭐ Cổng đang **thưởng** cho đúng cái kiểu cắt giữa câu mà ràng buộc sản phẩm
**cấm**, và **phạt** cách cắt đúng. Đó là bằng chứng **cơ học** cho điều §7.6 mới
chỉ lập luận: `lech_doan` đếm **số đoạn** thì không phân biệt được *cắt đúng chỗ*
với *cắt đủ số*.

⚠️ Ghim bằng mã, ⛔ không chỉ bằng đoạn văn này:
`tests/test_3008_asv_bench_b1.py::test_TIEM_cat_may_moc_moi_2_giay_LO_MOT_LO_tren_v2`
là một phép kiểm **đặc tả hiện trạng** — nó **sẽ đỏ** khi cổng được sửa, và lúc
đó **xoá nó** là hành động đúng.

## 8.4 Phán quyết cuối của làn

```
CER        3/3 ĐẠT   (0,0434 · 0,0275 · 0,0526   — ngưỡng 0,12, KHÔNG đổi)
lech_doan  1/3 ĐẠT   (0,1863 · 0,3084 · 0,6737   — ngưỡng 0,20, KHÔNG đổi)
```

# ⛔ **B1 KHÔNG ĐẠT** — và ⛔ **làn này không định nghĩa lại chân lý nền**

Ba cửa đã hỏi đúng câu cần hỏi, và câu trả lời là **không**: chân lý nền mới
không dựng được bằng máy (8.1) và không độc lập với engine (8.2). ⇒ ⛔ Không thay
thước. **KHÔNG ĐẠT là một kết quả hợp lệ**, và nó ở lại.

⚠️ Thứ **đã** thay đổi và ⛔ không được lẫn vào phán quyết trên: cổng hiện hành
vừa bị chứng minh là có lỗ thủng (8.3). Đó là một khiếm khuyết của **dụng cụ đo**,
để điều phối xử lý — ⛔ **không phải** một lý do để B1 được tính là đạt.
