# CapCut và cộng đồng giải bài "dịch rồi lồng tiếng cho vừa khe" thế nào?

Làn `nc-capcut`, 25/09/2026. **Việc nghiên cứu + đo, không sửa mã `apps/`.**

Bối cảnh: lượt chạy thật của ta (phim 275 s, 106 đoạn) tốn **67 lượt LLM, 67/67 là
`rut_ngan_cho_vua`**, 59/106 đoạn (55,7 %) phải viết lại, LLM chiếm ~1.126 s = 52 % cả
giai đoạn GIỌNG. Gốc đã tìm ra: `DUNG_SAI_DAI` 8 % × khe trung vị 1,71 s = **137 ms**,
trong khi một âm tiết tiếng Việt ở `ngon_ngu.NHIP[vi] = 3,35` âm tiết/giây là
**299 ms** ⇒ **100/106 đoạn (94 %) bị phán quyết ở độ chính xác hệ không có**.

> ⚠️ Số 299 ms tính từ chính hằng số của ta (`1 / 3,35`). Brief ghi 256 ms (≈ 3,9 âm/s).
> Hai cách tính cho **0,46** và **0,54** âm tiết — kết luận không đổi: dung sai **hẹp
> hơn một nửa lượng tử nhỏ nhất của hệ**.

---

## 1. CapCut làm gì ở khâu này?

### 🔴 Câu trả lời: **KHÔNG LÀM GÌ.** CapCut không có khâu này.

Đây là kết luận ngược với kỳ vọng, nên nói bằng nguồn trước.

**(a) CapCut không có mô-đun dịch dùng được.**

`D:\Viral\resources\app-src\capcut_asr.py:7-8` (kho của chủ dự án, chỉ đọc):

> ⚠ KHÔNG dùng `translation_text` của CapCut để DỊCH — đã đo: sai nghĩa
> (洋气→"đi nước ngoài", 搭包→"đóng gói"). Dịch LUÔN bằng Gemini ở tầng trên.
> Module này chỉ trả TEXT NGUỒN + thời gian.

`capcut_tts.py:71-98` ghi lại một cuộc dò cạn kiệt: `audio_translate` và
`video_translate` đều trả `vid source only (30001)`; đã thử **11 biến thể tên phương
thức** (`translate` · `text_translate` · `sami_translate` · `lv_translate` ·
`machine_translate` · `subtitle_translate` · `auto_translate` · `translation` ·
`sami_translation` · `text_to_text` · `text_polish`) và **8 đường dẫn** (`/lv/v1/translate`,
`text/translate`, `ai/translate`, `nlp/translate`, `common_task/translate`…). Không cái
nào cho dịch văn bản.

ASR có tham số `"translation_language": "vi-VN", "use_translation": bool`
(`capcut_asr.py:512`) nhưng mặc định `use_translation=False` ở cả hai chỗ gọi
(`:429`, `:483`) — chính vì lý do ở `:7`.

**(b) CapCut không điều khiển được tốc độ đọc.** `capcut_tts.py` ghi: *server BỎ QUA
SSML* (dẫn lại ở `localize.py:12711`). Đo thật 21/08, n=6: thêm dấu phẩy nối ý vào cuối
mảnh cho CapCut đổi **0,0 %** F0 (236,6 → 236,6 Hz), thời lượng trùng tới 0,01 s —
server tự chuẩn hoá văn bản, nuốt sạch dấu câu.

⇒ **CapCut là một máy đọc thuần.** Nó nhận chữ, trả mp3, không biết khe thời gian là gì.

### Vậy "CapCut làm rất tốt vấn đề này" là cái gì?

Là **chính con bot của chủ dự án** (`D:\Viral`, đang phục vụ thật, cổng 8000), dùng
CapCut **chỉ cho ASR + TTS**, còn toàn bộ việc nắn-cho-vừa nằm ở `localize.py` và
`dich_gemini_web.py`. Đó là hệ tham chiếu đáng giá nhất tìm được — cùng một chủ dự án,
cùng cặp ngôn ngữ zh→vi, và **đã đo trên hàng vạn cue của khách thật**. Phần còn lại
của mục này nói về nó.

### Bốn câu hỏi cụ thể, trả lời cho bot Viral

**Họ có ép độ dài câu dịch không?** Có cơ chế, nhưng **đã đo là gần như vô dụng và
MẶC ĐỊNH TẮT cho tiếng Việt.**

`dich_gemini_web.tran_tu_dich():155` — trần = `min(giây × wps, số_âm_nguồn × 0,75)`,
nhúng vào prompt dạng `[1.4s ≤6 từ]`. Số đo phản bác nó (`localize.py:15066-15080`), trên
**12.626 cue THẬT** (ghép cặp `.zh.srt`/`.vi.srt` của khách):

| Phép đo | Kết quả |
|---|---|
| Cue nằm trong trần | **43,0 %** |
| Tỉ lệ từ/N trung vị | **1,14×** (p90 1,67×) |
| Phân bố quanh 1,0 | **không có vách** — bậc 1,2 đông hơn bậc 0,9 |
| Độ nhạy (cần ≈1,0 nếu model tuân N) | **0–0,5** |
| Nhóm đông nhất (2.768 cue, nguồn 11-13 chữ) | N tăng 5→9, trung vị số từ **đứng yên ở 8** ⇒ **≈0** |
| Giá | **+7.090 ký tự / lô 400 câu (+31 % prompt)** |

Và một A/B đắt tiền đóng đinh chuyện đó (`dich_gemini_web.py:1523-1545`) — khối này mở
đầu bằng *"⛔ ĐỪNG THỬ LẠI. Dưới đây là toàn bộ số đo, để đời sau khỏi tốn thêm 36 lô
Gemini."*:

- 36 lô · 3 video khác mật độ (5,09 / 6,07 / 7,99 âm/giây) · lô 300 dòng như production ·
  xen kẽ cùng browser · đảo thứ tự · so cặp.
- Mục tiêu nhịp có số vs base: **+0,019 từ/giây · 6/12 cặp có lợi** = đúng tung đồng xu.
- Thêm neo `≤N từ`: **−0,069 · 7/12**.
- 🔑 **Vì sao không ăn:** biến động giữa các VÒNG của CÙNG một nhánh là **0,13–0,67
  từ/giây**, lớn hơn mọi chênh lệch giữa các nhánh (0,02–0,09). *"Model viết ~5,3–6,8
  từ/giây bất kể dặn gì; mật độ bản dịch do NỘI DUNG NGUỒN quyết định."*

Hai hướng "chuẩn ngành" cũng đã thử và trượt:

- **Nhãn độ cứng** kiểu verbosity token của Amazon (Isometric MT, arXiv **2110.03847**,
  tài liệu gốc báo >90 % bản dịch lọt ±10 %): A/B n=3 trên video thật,
  **6/6 chỉ số chồng lấn** ⇒ không phân biệt được với nhiễu (`dich_gemini_web.py:~200-215`).
- **Cơ chế đếm CAPEL** (arXiv **2508.13805**): đo được model **tự khai số từ SAI 38/59
  dòng = 64 %** ⇒ bỏ (`localize.py:3806`).

**Họ có gộp khe không?** **CÓ, và đã chạy thật trên 40 % cue.**

`localize._nhom_gop_capcut():12648` — *"NGUỒN SỰ THẬT DUY NHẤT"*, luật gộp:

| Tham số | Giá trị | Nghĩa |
|---|---|---|
| `gmax` (`DUB_GOP_MAX`) | **4** | tối đa 4 cue một nhóm |
| `gkhe` (`DUB_GOP_KHE`) | **0,6 s** | khe giữa hai cue phải ≤ 0,6 s |
| `gkytu` (`DUB_GOP_KYTU`) | **220** ký tự | trần tổng ký tự nhóm |
| `_con_tiep(...)` | — | chỉ gộp khi câu **chưa kết thúc** |
| liền chỉ số | `_i == _p + 1` | không nhảy cue |

Đo thật 26/08 trên video 55 phút: **gộp 708/1755 cue = 40 %**.

🔴 **Nhưng MẶC ĐỊNH TẮT từ 01/09 (`DUB_CAPCUT_GOP=0`) — và lý do là bài học đắt nhất
của cả tệp này.** `localize.py:11258-11268`: họ gộp để **tổng hợp** (prosody chảy suốt
câu) rồi **CẮT TRẢ VỀ** từng cue theo mốc từ mà server trả. `end_time` của server đánh
dấu **hết NGUYÊN ÂM**, phần buông phụ âm nằm sau đó nên **bị xén ở 100 % câu gộp** —
khớp đúng lời khách *"đoạn sub nào cũng bị"* và *"khoảng bản 1.8.0 mới bị"* (dấu vết:
25/08 10:05 thêm cờ · 10:27 publish v1.8.1). Bản vá 70 ms không đủ; đo 13 giọng Piper,
mức cần nới: 0 ms (5 giọng) · ~80 ms (`ngochuyen`) · ~180 ms (`calmwoman3688`) ·
**>250 ms** (`lacphi`) ⇒ phụ thuộc giọng, không vá được bằng một hằng số.

Một lần gộp TRƯỚC đó (`_gop_cue_cung_cau`) đặt nguyên khối từ mốc cue đầu ⇒ **trôi
5,80 s** ⇒ cũng tắt.

⭐ **Cả hai ca hỏng đều nằm ở việc CẮT TRẢ VỀ, không ở việc GỘP.** Giữ điều này cho mục 3.

**Dung sai của họ là bao nhiêu, tính theo gì?** Nhiều tầng, và **có cả tuyệt đối lẫn
tỉ lệ** — đây là khác biệt lớn nhất so với ta:

| Hằng số | Giá trị | Đơn vị | Nguồn |
|---|---|---|---|
| `DUB_FIT_TOL` | **0,12** | tỉ lệ | `localize.py:9033` — *"Tai người không nhận ra tràn nhẹ < ~12 % nhưng rất nhạy với nén đột ngột"* |
| `DUB_TRAN_MAX` | **0,2 s** | ⭐ **TUYỆT ĐỐI** | `localize.py:9041` — BẬT mặc định 24/08, *"thay gộp-câu"*; *"Đổi ràng buộc từ 'giới hạn tốc độ' sang 'giới hạn tràn'"* — "tràn 0,1 s rồi mới nén" |
| `VOICE_CAP` | **1,12** | tỉ lệ | `localize.py:9259` — dưới mức này không chậm video |
| `DUB_MAX_SPEED` | **1,2** | tỉ lệ | `localize.py:9024` — lịch sử 1,6→1,3→2,0→1,6→1,25→**1,2** |
| `DUB_LEAD` / `DUB_TAIL` | **0,25 s** mỗi đầu | tuyệt đối | `localize.py:9077` |
| `DUB_NEN2_DUNGSAI` | **1,25** | tỉ lệ | `localize.py:3800` |

🔑 `DUB_TRAN_MAX = 0,2 s` là con số đáng chú ý nhất của cả tài liệu: nó **thay thế**
đường gộp câu, và nó chuyển ràng buộc từ *tỉ lệ* sang *giây tuyệt đối*.

**Họ có vòng LLM viết lại không?** **Có, nhưng MỘT LƯỢT, THEO LÔ, và MẶC ĐỊNH TẮT.**

`localize._nen_cau_tran():3780` — `DUB_NEN2=1` mới bật. Không phải vòng lặp: một lượt
Gemini trên **tập con** các cue tràn, hỏng ở bất kỳ khâu nào thì rơi về bản cũ
(*"fail-safe BY CONSTRUCTION"*). Ba lý do TẮT, ghi nguyên văn ở `:3855-3862`:

1. **Mất nghĩa ĐO ĐƯỢC** — đọc tay 73 câu, nhận 55. Ca thật: *"…tiếp xúc Thẩm Nghiên
   ĐỂ LẤY VẬN KHÍ"* → *"Hoàn toàn không dựa vào Thâm Nghiên"* (mất ý chính);
   *"NHÀ HỌ LÂM VÀ HỌ THÂM đã CHẠY CHỌT nhét bọn tớ vào đây"* → *"Lâm Thẩm nhét bọn tớ
   vào đây"* (hai gia tộc thành tên một người). *"4 cổng an toàn KHÔNG lọc được chất
   lượng."*
2. 🔑 **Khảo sát 56 video giao khách thật (22.094 cue): % cue tràn p10 0,0 · p25 0,4 ·
   **p50 1,9 %** · p75 3,3 · p90 5,0 · max 17,9.** Bật mặc định là bắt ~75 % khách trả
   ~15 s để sửa trung vị ~5 câu.
3. Ưu tiên số 1 là thời gian tới video đầu tiên.

Và ba thứ quyết định thành/bại của prompt nén (`:3801-3806`) — trong đó **dung sai
1,25 là điều kiện cần**: *"đích KHÔNG phải need=1,0 mà là 'khỏi kích trần
DUB_MAX_SPEED'. Đặt trần vừa khít + ví dụ cực đoan ⇒ nén −65 % nhưng ra
`'disaster day one'`, `'just chassis'` — TTS đọc lên vô nghĩa. Vách là CÓ THẬT."*

### Bậc thang mà bot Viral thực sự dùng

Chủ dự án chốt 28/08 (`localize.py:9021`, nguyên văn *"sau tăng tốc lên 1,2 không được
thì giảm tốc video xuống .20 để giọng có 20 % thời gian nói nữa, không được nữa thì trôi
nhưng vẫn phải giữ sub, giữ tiếng đồng bộ"*):

```
0. mượn khe HAI ĐẦU  LEAD = TAIL = 0,25 s
1. nén giọng         ≤ DUB_MAX_SPEED 1,2
2. ⭐ CHẬM VIDEO      Video Assist, DUB_VIDEO_MAXSLOW = 0,20, per-segment
3. trôi              + DUB_SUB_SYNC = 1 (sub bám giọng)
(–) viết lại bằng LLM  _nen_cau_tran — TẮT mặc định, ngoài bậc thang
```

**Nấc 2 là nấc ta không có.** `localize.py:9259` — mỗi câu `need_i = dur_i/slot_i`; nếu
`need_i > VOICE_CAP (1,12)` thì **giãn hình đoạn đó** `f_i = max(1−MAXSLOW, VOICE_CAP/need_i)`.
Bảng đo 21/08 (60 cue thật, giọng thật, LEAD/TAIL 0,25):

| `MAXSLOW` | 0 | 0,08 | 0,10 | 0,15 | 0,40 |
|---|---|---|---|---|---|
| nén trung bình | 1,194 | 1,151 | ~1,14 | 1,122 | 1,064 |
| **cue > 1,3×** | **35,0 %** | 23,3 % | ~21 % | **18,3 %** | 6,7 % |
| video dài thêm | +0 % | +4,7 % | ~+6 % | +8,4 % | +17,1 % |

Nâng lên 0,20 ngày 27/08 sau khi đo 39 video thật: **15/39 video cần giãn >5 %, cao
nhất 1,26×**. Và câu kết luận của cả đợt đó (`localize.py:9294`):

> ⭐ *"Cùng đợt đó đã đo và LOẠI mọi hướng chỉnh PROMPT (36 lô A/B, 6/12 = tung đồng xu)
> ⇒ **Video Assist là đòn bẩy DUY NHẤT đo được có tác dụng.**"*

Thêm một nấc cơ học nữa, `_chia_deu_nen_manh():8822` — câu nén mạnh **mượn thời gian
của MỘT cue kề**. Đo trên **14.868 cue** (65 SRT đích-vi), 647 cue cần nén >1,6:

| Kiểu | Trần dời | Cứu được | dời p50 | dời p90 | dời MAX |
|---|---|---|---|---|---|
| CẢ CỤM | không | 100 % | 0,76 s | 3,35 s | **10,57 s** ← trôi, bị tắt |
| **CẶP** | **0,5 s** | **76 %** | 0,29 s | 0,45 s | 0,50 s ← chọn |
| CẶP | 1,0 s | 89 % | 0,35 s | 0,71 s | 0,98 s |

Nền cùng bộ đo: **chỉ 4,4 % cue cần nén >1,6 · 0,9 % cần >2,2 · slack toàn cục 10,9 %.**
Và câu chốt: *"Cứu 76 % ⇒ còn ~1,1 % — **đó mới là phần cần tới `_nen_cau_tran`**"*.

Vì sao CẶP hơn CỤM là **tính chất hình học, không phụ thuộc phép ước lượng nào**: chia
cụm thì độ dời cộng dồn dọc cụm (cụm 215 cue ⇒ cue cuối trôi 10 s); chia cặp thì hai
mép ngoài được ghim, chỉ một ranh giới giữa nhúc nhích.

### Tài liệu ngành mà bot Viral đã tra (dùng lại được, không phải tra lại)

- **Federico/Amazon, "Prosodic Alignment for off-screen automatic dubbing"** — tách hai
  chế độ: ON-SCREEN (thấy miệng) buộc isochrony nghiêm ngặt từng cụm; OFF-SCREEN thì
  *"less stringent synchronization constraints"*. Ghi ở `localize.py:9064-9068, arXiv 2204.02530 ghi ở :4032` kèm nhận
  xét: nội dung tool gần 100 % off-screen ⇒ *"ép khít từng cue là đang áp chuẩn LIP-SYNC
  lên nội dung THUYẾT MINH, và đó chính là lý do phải nén tới 1,6×"*.
- **Netflix: 17–20 ký tự/giây** là trần đọc cho phép. Giọng mặc định đã 19,8 cps; nén
  1,6× thành **31,7 cps = ~1,7× trần ngành** (`localize.py:9069-9070`).
- **TACL 2023, 319,57 giờ phim lồng tiếng NGƯỜI THẬT** — tốc độ đọc của diễn viên chỉ
  giải thích **~3 % biến thiên thời lượng (r² = 0,027)** ⇒ **không ủng hộ isometric**
  (`localize.py:17334-17335, 13458-13459`). 🔑 Tức: người thật lồng tiếng **không** giải bài này bằng cách
  nói nhanh hơn/chậm hơn.
- Amazon Isometric MT **arXiv 2110.03847** · CAPEL **arXiv 2508.13805** — đã thử, đã
  trượt (trên).

---

## 2. Bảng đối chiếu

Bốn dự án mã nguồn mở + bot Viral + ta. Mọi ô có nguồn; ô không tìm được ghi rõ.

| Dự án | Ép độ dài câu dịch? | Gộp khe? | Dung sai — bao nhiêu, theo gì | Vòng LLM viết lại? |
|---|---|---|---|---|
| **R3gm/SoniTranslate** | **KHÔNG** (không tìm thấy trần nào trong prompt) | **KHÔNG** | **Tỉ lệ.** `max_accelerate_audio = 2.1` (mặc định, `app_rvc.py`); vùng chết **0,8–1,15 → 1,0**; ≤0,79 → 0,8. Mượn khe cue sau khi `acc ≥ 1.3`: `0,5×` khe nếu cùng người nói, **`0,7×` nếu khác** (`acceleration_rate_regulation`) | **KHÔNG** — chỉ `ffmpeg atempo` |
| **lukaszliniewicz/Subdub** | **KHÔNG** — prompt chỉ nói *"choose concise translations suitable for dubbing"* (`src/subdub/prompts/translation.py`) | **KHÔNG** | **Tỉ lệ.** `speed_up: int = 115` ⇒ **1,15×** (`src/subdub/config.py`). Phần tràn thành `total_shift` mang sang block sau, hấp thụ bằng khoảng lặng đuôi | **KHÔNG** — một lượt dịch |
| **Softcatala/open-dubbing** | **KHÔNG** (đã đọc hết `translation.py`: không có ràng buộc độ dài nào) | **KHÔNG** | **Tỉ lệ.** `MAX_SPEED = 1.3` (`open_dubbing/text_to_speech.py`). Mượn khe **ngầm**: dùng mốc bắt đầu của utterance kế làm mốc kết thúc hiệu lực | **KHÔNG** — TTS đọc nhanh sẵn hoặc ffmpeg, một lượt |
| **Huanshere/VideoLingo** | **CÓ** — `subtitle.max_length: 75` ký tự · `target_multiplier: 1.2` · `max_split_length: 20` từ (`config.yaml`) | ⭐ **CÓ** — `merge_rows()` nối các dòng phụ đề liền nhau, `MAX_MERGE_COUNT = 5` (`core/_8_2_dub_chunks.py`) | **Cả hai.** Tỉ lệ `speed_factor: {accept: 1.2, max: 1.4}`; ⭐ **tuyệt đối `tolerance: 1.5 s`** và ⭐ **`min_subtitle_duration: 2.5 s`** | **KHÔNG** cho thời lượng. Chỉ retry 3 lần khi **lệch SỐ DÒNG** (`core/translate_lines.py::retry_translation`) — lỗi cấu trúc, không phải thời lượng |
| **Bot Viral** (chủ dự án, chạy thật) | Có cơ chế, **TẮT** cho `vi` — đo 43 % lọt trần, độ nhạy ≈0 | **CÓ** (`gmax 4`, khe ≤0,6 s, ≤220 ký tự) — **TẮT vì CẮT TRẢ VỀ xén phụ âm**, không vì gộp sai | **Cả hai.** `DUB_FIT_TOL 0,12` · ⭐ **`DUB_TRAN_MAX 0,2 s`** · `VOICE_CAP 1,12` · `DUB_MAX_SPEED 1,2` · LEAD/TAIL 0,25 s | **Có, TẮT mặc định.** Một lượt theo LÔ, dung sai **1,25**, chỉ cho cue tràn |
| ⚠️ **TA (`nan_cho_vua`)** | **CÓ** — `ngan_sach_do_dai()` trần đếm được + `HE_SO_MUC_TIEU 0,92` | **KHÔNG** | **Chỉ TỈ LỆ.** `DUNG_SAI_DAI 0,08` · `DUNG_SAI_NGAN 0,35` · `TRAN_TANG_TOC 1,15` (*"chỉ dùng để TRẢ NỢ, không dùng để ép vừa"*) | ⭐ **CÓ — vòng thật, `VONG_TOI_DA = 2`, MỖI ĐOẠN RIÊNG, BẬT** |

### Ba chỗ ta là ngoại lệ của cả bảng

1. **Dung sai 8 % là chặt nhất trong bảng**, và là dung sai duy nhất **không có sàn
   tuyệt đối**. Ba dự án khác + bot Viral + VideoLingo đều có một con số **giây**
   (0,2 s · 1,5 s) hoặc một vùng chết rộng hơn (12 %, hoặc 0,8–1,15 kẹp về 1,0).
2. **`TRAN_TANG_TOC = 1,15` là trần tốc độ chặt nhất trong bảng** — và ta còn tự khoá
   nó lại (*"chỉ để TRẢ NỢ"*). So sánh: Subdub 1,15 · VideoLingo accept 1,2 / max 1,4 ·
   Viral 1,2 · open-dubbing 1,3 · SoniTranslate 2,1. ⇒ **ta gần như không có đòn bẩy
   tín hiệu nào để ép vừa**, nên toàn bộ áp lực dồn vào LLM.
3. **Ta là dự án DUY NHẤT trong bảng chạy vòng LLM viết lại theo thời lượng, và là dự án
   duy nhất bật nó mặc định.** 0/4 dự án mã nguồn mở có; bot Viral có nhưng tắt, theo
   lô, và chỉ sau khi hai nấc cơ học đã cứu 76 %.

### Đối chiếu hai hằng số ta đã mượn

| Hằng số của ta | Ta ghi là mượn từ | Số thật ở nguồn | Nhận xét |
|---|---|---|---|
| `TY_LE_MUON_KHOANG_LANG = 0,7` | SoniTranslate `acceleration_rate_regulation` | **Đúng** — 0,5 cùng người nói / **0,7 khác người nói** | ⚠️ Nhưng ở nguồn nó **chỉ kích khi `acc ≥ 1,3`**, còn ta mượn **luôn**. Và `thoi_gian.py:186-193` chỉ mượn **phía SAU** (`ngan_sach_doan` = tới lúc đoạn sau bắt đầu); `dat_tai` không bao giờ sớm hơn `bat_goc` quá 200 ms ⇒ **ta không có `DUB_LEAD`** |
| `TRAN_TANG_TOC = 1,15` | Subdub | **Đúng** — `speed_up: int = 115` | Khớp chính xác. Nhưng Subdub dùng nó **để ép vừa**, ta tự hạn chế *"chỉ để trả nợ"* |

Ghi chú của ta ở `thoi_gian.py:52` — *"Cố ý KHÔNG lấy 2.1 của SoniTranslate: nhanh gấp
đôi thì không còn là giọng người"* — vẫn đúng: 2,1 là **trần kẹp cuối** của họ, không
phải mức làm việc.

### Khiếu nại thật của người dùng (để biết cái giá của mỗi nấc)

SoniTranslate: issue **#19** *"Speech too fast and out of sync"* (đã đóng) · **#89**
*"Speed of the translated audio is slowed down"* (còn mở) · **#84** giọng RVC lệch pha
(*"too much faster"*) · ⭐ **#77** — **đề nghị làm chậm VIDEO thay vì tăng tốc giọng**
(đúng nấc 2 của bot Viral) · **#57** treo sau bước tăng tốc.

---

## 3. Đề nghị

Mỗi đề nghị kèm **một con số hoặc một nguồn**. Xếp theo tỉ lệ (lợi ích đã đo) / (rủi ro).

### Đ1 — Cho `DUNG_SAI_DAI` một **SÀN TUYỆT ĐỐI bằng một âm tiết**

> ✅ **ĐÃ LẮP 25/09** — `nan_cho_vua.SAN_DUNG_SAI_GIAY = 0,256` + `dung_sai_giay()`.
> ⚠️ Sàn chốt là **0,256 s**, ⛔ **không** phải `1/NHIP` = 299 ms như đề nghị này viết:
> `NHIP` là nhịp **trung bình** nên nó gồm cả đoạn chặn 0,188 s của câu, còn câu hỏi ở
> đây là **chi phí BIÊN** của một âm tiết — hồi quy `giay = 0,188 + n × 0,256`
> (R² = 0,927, n = 47). Bằng chứng đo được: `tom_tat()["tung_luot_doc"]`
> (`tests/test_4600_asv_san_dung_sai.py`).

**Số:** `0,08 × 1,71 s = 137 ms`, còn `1 / NHIP[vi] 3,35 = 299 ms`. Dung sai hiện tại là
**0,46 âm tiết** ⇒ 100/106 đoạn (94 %) bị phán quyết ở độ chính xác hệ không có.

**Nguồn:** bot Viral chuyển **đúng** ràng buộc này từ tỉ lệ sang tuyệt đối —
`DUB_TRAN_MAX = 0,2 s`, BẬT mặc định 24/08, *"Đổi ràng buộc từ 'giới hạn tốc độ' sang
'giới hạn tràn'"* (`localize.py:9041`). VideoLingo cũng có `tolerance: 1.5` giây
(`config.yaml`). **Hai hệ độc lập, cả hai đều có một con số giây; ta không có.**

**Hình dạng:** `dung_sai = max(DUNG_SAI_DAI × khe, MỘT_ÂM_TIẾT)` với
`MỘT_ÂM_TIẾT = 1 / ngon_ngu.NHIP[dich]` (⭐ tính ra, không gõ tay — cùng luật
"một con số, một chỗ khai" mà `ngon_ngu.py` đã chốt).

⚠️ **Chưa đo:** sàn nên là **1** âm tiết hay **2**. Viral chọn 0,2 s ≈ 0,67 âm tiết
tiếng Việt; VideoLingo chọn 1,5 s ≈ 5 âm tiết. Khoảng cách quá rộng để nội suy.
Phép đo rẻ: chạy lại `tom_tat()["tung_doan"]` của lượt 275 s với sàn 1 / 1,5 / 2 âm
tiết, đếm `so_can_nan`. **Dữ liệu đã có, không cần chạy ASV** (điều chủ dự án đã dừng).

### Đ2 — `gop_khe` ĐÁNG LÀM, và ta tránh được đúng cái làm Viral phải tắt nó

> ✅ **ĐÃ LẮP 25/09** (làn `b2-gop-khe`) — `gop_khe` điều khiển **đường sinh tiếng
> thật**: `giai_doan_giong` đọc **một lượt cho cả nhóm**, `nan_thoi_luong.no_ban_ke`
> trả lại **một dòng `ban_ke` cho MỌI `ma` gốc** nên bất biến
> `giai_doan_thoi_gian.py:88-89` ⛔ không bị phá và `content.json` ⛔ không bị chạm.
> Luật gộp mượn nguyên của Viral: `≤ 4` đoạn · khe `≤ 0,6 s` · `≤ 220` ký tự ·
> `con_tiep`.
>
> **Đo lại trên 3 phim (188 khe), với luật Viral — chặt hơn phép đo dưới đây:**
> khe `188 → 126` · khe bị phán quyết dưới một âm tiết `119 (63,3 %) → 44 (34,9 %)`
> · **số** lượt gọi model `135 → 85 (−37 %)`. ⚠️ **Tỉ lệ** khe không vừa thì gần như
> không đổi (`71,8 % → 67,5 %`) — cái mua được là **ít khe hơn để phán quyết**, ⛔
> không phải một tỉ lệ đẹp hơn.
>
> 🔴 **Cái giá KHÔNG nằm ở ký tự/giây** (p95 `16,45`, `0/188` vượt trần 20 — và
> **không đổi** trước/sau, vì ô phụ đề dài đúng bằng thời gian máy đọc chính văn
> bản của ô đó). Nó nằm ở **bố cục ô**: trần của ta là `2 × 42 = 84` ký tự, còn
> trần gộp 220 của Viral là trần của một **lượt đọc**. Gộp cả ô đẩy tỉ lệ ô vượt
> trần từ `15,4 %` lên `42,9 %` ⇒ ⛔ **không gộp ở phụ đề**, chỉ gộp cái **đọc**.
> ⚠️ Và `15,4 %` **trước** gộp là khiếm khuyết **có sẵn** — ghi lại, chưa sửa.
>
> ⚠️ **Hai trong bốn hằng số mượn về chặn `0/185` cặp** trên dữ liệu ta
> (`TRAN_KHE_GIUA_S`, `TRAN_KY_TU_GOP`): `cat_doan` cho `ket[i] == bat[i+1]` nên
> khe giữa luôn `0,000 s`, khác hẳn cue của CapCut. Điều kiện có hiệu lực nhất là
> `con_tiep` (`64/185`). Bằng chứng: `bang_chung/b2_gop_khe/`.

**Số của ta:** 106 → 59 khe · khe trung vị 1,71 → 2,24 s · đoạn bị phán quyết ở độ chính
xác không có: **100/106 (94 %) → 39/59 (66 %)**.

**Hai nguồn độc lập ủng hộ:**

- VideoLingo `merge_rows()`, `MAX_MERGE_COUNT = 5` — và ⭐ `min_subtitle_duration: 2.5 s`.
  🔑 **Khe trung vị của ta là 1,71 s, dưới sàn đó; sau `gop_khe` là 2,24 s, VẪN dưới.**
  Tức một dự án đã chạy thật coi khe ngắn hơn 2,5 s là thứ cần gộp lại, còn ta đang
  phán quyết trên khe 1,71 s.
- Viral `_nhom_gop_capcut` — gộp thật **708/1755 cue = 40 %** trên video 55 phút.

⭐ **Và đây là chỗ then chốt:** Viral tắt gộp **không phải vì gộp sai**, mà vì họ gộp để
tổng hợp rồi **CẮT TRẢ VỀ** từng cue theo mốc từ của server — `end_time` đánh dấu hết
nguyên âm nên phụ âm buông bị xén ở **100 % câu gộp**, cần tới **>250 ms** với giọng
`lacphi` (`localize.py:11258-11268`). Ca gộp trước đó (`_gop_cue_cung_cau`) trôi
**5,80 s**.

**`gop_khe` của ta gộp CHÍNH KHE** — một khối tiếng nằm trong một khe dài, **không cắt
trả về** ⇒ **miễn nhiễm về mặt cấu trúc** với cả hai ca hỏng đó. Đây là lý do kỹ thuật
để `gop_khe` được phép sống ở ta trong khi nó phải chết ở Viral.

**Mượn luật gộp đã chạy thật, đừng tự phát minh** (`localize.py:12648`): ≤ **4** đoạn ·
khe giữa hai đoạn ≤ **0,6 s** · tổng ≤ **220** ký tự · **chỉ gộp khi câu chưa kết thúc**
(`_con_tiep`) · chỉ số liền nhau.

⚠️ **Cái giá phải đo, và nó là cái giá SẢN PHẨM:** gộp khe làm **phụ đề** dài ra theo.
Netflix cho 17–20 ký tự/giây (`localize.py:9069-9070`) — một khe 2,24 s chứa nhiều nhất
~38–45 ký tự. Đo được từ dữ liệu đã có: phân bố ký tự/giây của 59 khe sau gộp.

### Đ3 — Đặt một nấc **CƠ HỌC** trước LLM, và đó là nơi ta thiếu hẳn một đòn bẩy

**Số:** bot Viral đo trên **14.868 cue**: mượn-khe-theo-CẶP với trần dời 0,5 s cứu
**76 %** các cue cần nén >1,6, để lại **~1,1 %** — *"đó mới là phần cần tới
`_nen_cau_tran`"* (`localize.py:8851`). Ta đang gọi LLM cho **55,7 %**.

**Nguồn cho đòn bẩy ta không có:** *"Video Assist là đòn bẩy DUY NHẤT đo được có tác
dụng"* (`localize.py:9294`, sau 36 lô A/B). `DUB_VIDEO_MAXSLOW = 0,20`, per-segment,
`f_i = max(0,8, VOICE_CAP/need_i)` với `VOICE_CAP = 1,12`. Bảng đo: cue >1,3× giảm
**35,0 % → 18,3 %** ở `MAXSLOW = 0,15`, giá là video dài thêm **+8,4 %**. Và SoniTranslate
issue **#77** là chính người dùng đề nghị điều đó.

`grep` trên `apps/auto_scan_video/` cho **0 kết quả** với `MAXSLOW` / `video_slow` /
`keo_gian_video` ⇒ **ta không có nấc "chậm hình" nào.**

⚠️ **Nhưng đừng đề xuất lắp nó vội** — có một ràng buộc kiến trúc của ta phải trả lời
trước: `nan_cho_vua.khe_cua()` lấy khe **gốc** và ghi rõ lý do *"khe gốc cũng là thứ
khán giả thấy — câu thoại phải khớp với cái miệng đang nhép trên màn hình"*. Đổi khe =
đổi luồng hình. Viral trả giá đó bằng **hàng nghìn đoạn trim+concat** (đo máy khách:
GPU 16 %, ghép 393/1795 s) và phải cap `VC_WARP_MAX_DOAN` 400→150
(`localize.py:9287-9290`). **Đây là một đề nghị KHẢO SÁT, không phải một đề nghị LẮP.**

### Đ4 — ⛔ ĐỪNG đầu tư thêm vào việc chỉnh lời nhắc cho model viết ngắn

**Nguồn:** ba phép đo độc lập, tất cả đều trượt, tổng cộng **36 lô Gemini + 2 A/B n=3**:

- 12.626 cue: 43 % lọt trần, độ nhạy **0–0,5** (cần ≈1,0), nhóm đông nhất **≈0**.
- 36 lô A/B: **6/12** = tung đồng xu; **nhiễu lượt-qua-lượt 0,13–0,67 từ/giây nuốt trọn
  hiệu ứng 0,02–0,09**.
- Nhãn độ cứng (arXiv 2110.03847): **6/6 chỉ số chồng lấn**. Đếm CAPEL (arXiv 2508.13805):
  model **tự khai sai 64 %**.

**Áp vào ta:** `ngon_ngu.ngan_sach_do_dai()` là **đúng họ cơ chế đã trượt ba lần** — một
trần đếm được nhúng vào prompt. Docstring của nó lập luận rất hay (*"một trần ĐẾM ĐƯỢC
thì model tự kiểm được"*) nhưng lập luận đó **chính là giả thuyết mà 36 lô đã bác bỏ**.

⛔ ⇒ **Không đề nghị bỏ nó** (chi phí giữ ≈ 0, và Viral đo được neo **CÓ** ràng buộc thật
với đích không phải `vi`, nơi trần 2,0 từ/s chặt hơn tốc tự nhiên). ⇒ Đề nghị: **đừng
trông nó hạ được 55,7 %**, và ⛔ đừng tiêu một lượt A/B nào nữa để chỉnh chữ trong lời
nhắc trước khi Đ1 + Đ2 đã chạy.

### Đ5 — Bỏ vế VIẾT LẠI CHO DÀI RA (`DUNG_SAI_NGAN`)

> ✅ **ĐÃ LẮP 25/09** — `nan_cho_vua.nen_viet_lai()` chặn đường gọi LLM cho chiều ngắn,
> và `loi_nhac_nan()` **ném** nếu bị gọi cho một đoạn không dài hơn khe (bất biến ở
> BIÊN, không chỉ ở vòng lặp). ⛔ `DUNG_SAI_NGAN = 0,35` **giữ nguyên** — nó còn dùng để
> phân loại/báo cáo: một đoạn quá ngắn vẫn đọc ra là "không vừa" trong `tom_tat`.

**Số:** 15/59 đoạn vào nấc 2 vì **quá NGẮN** (brief). `can_nan()` trả `True` khi
`lech < −0,35`, và `loi_nhac_nan()` khi đó yêu cầu *"VIET DAY DAN HON"*
(`nan_cho_vua.py:174`).

**Nguồn:** **0/4 dự án mã nguồn mở, và cả bot Viral, có vế này.** Cách xử lý của họ:

- SoniTranslate **kẹp 0,8–1,15 về 1,0** — tức câu ngắn tới **20 %** thì **không làm gì**;
  chỉ dưới 0,79 mới giãn, và giãn **tiếng**, không viết lại chữ.
- Viral `_nen_cau_tran` **chỉ chọn cue TRÀN** (`if (len(_tu(vi))/wps)/khe > _tran`,
  `localize.py:3866`) — câu ngắn không bao giờ vào. Khoảng lặng do `_xen_nghi` nuốt.
- `nan_cho_vua.py:76-80` của chính ta đã lập luận đúng hướng ấy: *"`thoi_gian.lap_ke_hoach`
  đã biết cách nuốt khoảng lặng, nên một câu ngắn là một vấn đề nó giải được. Gọi model
  để kéo dài một câu chỉ vì nó ngắn 20 % là trả tiền cho một thứ không ai nghe ra."*
  ⇒ **Lập luận đã có sẵn và đúng; con số 0,35 thì mâu thuẫn với nó.**

⭐ Và một hệ quả đã đo được ghi ở brief: **nới khe làm 15 đoạn này TỆ HƠN.** Nghĩa là
Đ2 (`gop_khe`) và vế `DUNG_SAI_NGAN` **đánh nhau** — bỏ vế ngắn là điều kiện để `gop_khe`
không tự bắn vào chân.

### Đ6 — Xét `DUB_LEAD`: mượn khoảng lặng phía TRƯỚC (đề nghị YẾU, nói rõ là yếu)

**Số của Viral:** LEAD = TAIL = 0,25 s, đường cong **gãy khúc đúng ở 0,25**; cue >1,6×
giảm **21,5 % → 14,0 % (−35 %)** (`localize.py:9077`). Trước đó họ **chỉ mượn được phía
SAU** — đúng tình trạng của ta (`thoi_gian.py:186-193`, `ngan_sach_doan` = tới lúc đoạn
sau bắt đầu; `dat_tai` không sớm hơn `bat_goc`, chỉ có `TRAN_CHONG_LAN_MS = 200`).

⚠️ **Nhưng đây là đề nghị YẾU, và phải nói rõ vì sao:** brief đã đo rằng nới khe bằng
khoảng lặng chỉ cứu **6/59**, khoảng lặng thêm trung vị **84 ms**. Viral cũng đo **khe
trung vị = 0,000 s** và vẫn được −35 % — nhưng **−35 % đó là trên nhóm `>1,6×`, tức CÁI
ĐUÔI**, không phải trên trung vị. Hai phép đo **không mâu thuẫn**: LEAD ăn ở đuôi phân
bố, và đuôi không phải chỗ 55,7 % của ta nằm.

⇒ Đ6 **không phải bản sửa cho bài toán này.** Xếp vào sổ nợ, làm sau Đ1/Đ2, và ⛔ đừng
để nó chiếm chỗ của Đ2.

### Xếp hạng

| # | Đề nghị | Số/nguồn chống lưng | Rủi ro |
|---|---|---|---|
| **Đ1** | Sàn tuyệt đối 1 âm tiết cho `DUNG_SAI_DAI` | 137 ms < 299 ms; Viral `DUB_TRAN_MAX 0,2 s`; VideoLingo `tolerance 1.5` | Thấp — một hằng số, đo lại được trên dữ liệu đã có |
| **Đ2** | `gop_khe`, mượn luật gộp của Viral | 94 %→66 % (ta đo); VideoLingo `min_subtitle_duration 2.5`; Viral gộp 40 % | Trung bình — phải đo ký tự/giây của phụ đề |
| **Đ5** | Bỏ vế viết-lại-cho-dài | 0/5 hệ tham chiếu có; lập luận đã có trong chính `nan_cho_vua.py:76` | Thấp — và là **điều kiện** để Đ2 không tự bắn vào chân |
| **Đ4** | Ngừng đầu tư chỉnh prompt | 36 lô, 6/12; độ nhạy ≈0; 6/6 chồng lấn | Không — đây là đề nghị **không làm gì** |
| Đ3 | Khảo sát nấc "chậm hình" | *"đòn bẩy DUY NHẤT đo được"*; 35 %→18,3 % | **Cao** — đổi luồng hình, chi phí render; **khảo sát, chưa lắp** |
| Đ6 | `DUB_LEAD` | −35 % nhưng **ở đuôi**; ta đo chỉ cứu 6/59 | Thấp, **lợi ích cũng thấp** cho bài này |

⭐ **Đ1 + Đ2 + Đ5 đi với nhau thành một gói**: Đ1 bỏ những đoạn bị phán quyết dưới một
âm tiết, Đ2 làm khe rộng đủ để phán quyết có nghĩa, Đ5 chặn tác dụng phụ đã đo của Đ2.
Cả ba đều **chỉ đụng hằng số và một bước tiền xử lý**, và cả ba **đo lại được trên đúng
lượt chạy 275 s đã có** — ⛔ không cần một lượt ASV nào.

---

## Phụ lục — những gì ⛔ KHÔNG tìm thấy

Nói ra để đời sau khỏi tìm lại:

- **Tài liệu công khai của CapCut/Jianying về khâu nắn-cho-vừa: không tìm thấy.** Bằng
  chứng duy nhất về hành vi của CapCut trong khâu này là **phép đo trong kho của chủ dự
  án** (dò 11 biến thể + 8 đường dẫn API, và phép đo SSML bị bỏ qua) — cả hai đều cho kết
  quả **âm**.
- **AutoCut**: không khảo sát trong lượt này.
- Trần độ dài trong prompt của SoniTranslate · Subdub · open-dubbing: **đã tìm, không
  có** (với open-dubbing đã đọc hết `translation.py` và xác nhận rỗng).
- Sàn tuyệt đối nên là 1 hay 2 âm tiết (Đ1): **chưa đo** — Viral 0,2 s ≈ 0,67 âm tiết,
  VideoLingo 1,5 s ≈ 5 âm tiết, quá rộng để nội suy.
- Hai repo mới cùng tên "subdub" (`vikasdimaniya/subdub`, `kokiaugust24th-coder/subdub`,
  tạo 08–09/2026): **chưa kiểm** — có vẻ là dự án cá nhân nhỏ, không xác thực.
- ⛔ `MediaCrawler/` trong `D:\Viral` là phi thương mại — **không đụng** (đúng brief).
