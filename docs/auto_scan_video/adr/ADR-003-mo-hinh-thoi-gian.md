# ADR-003 — Mô hình thời gian: cho phép tràn vào khoảng lặng, và trả nợ trôi

- **Status:** ACCEPTED
- **Date:** 2026-09-01 (Phase 13)
- **Sửa đổi:** `MVP_CONTRACT.md` §6 (`timing_mode`) và §7 (T2, T7)
- **Đóng:** RISK-02-01

---

## Bối cảnh

`MVP_CONTRACT.md` §6 (Phase 02) định nghĩa `fit_original` là *"mỗi đoạn được ép vừa
khung thời gian của đoạn nguồn"*. Đó là một giả định, và nó **sai** ở hai chỗ:

**1. Nó bỏ qua khoảng lặng.** Người nói không nói liền mạch — giữa các câu luôn có
khoảng nghỉ. Ép mỗi đoạn vừa đúng *thời lượng nói* của nó là vứt đi toàn bộ ngân sách
thời gian nằm trong các khoảng lặng ấy.

**2. Tiếng Việt thường dài hơn.** RISK-02-01 đã ghi điều này từ Phase 02 và cả Phase 11
lẫn 12 đều **không đo được** (không gọi được model thật, không gọi được máy sinh tiếng
thật). Nên với `fit_original` như định nghĩa cũ, tràn sẽ là **thường lệ chứ không phải
ngoại lệ** — và cách xử lý duy nhất còn lại là cắt cụt, tức mất lời thoại.

---

## Cộng đồng giải bài này thế nào

Ba dự án, ba mức độ, đọc trực tiếp mã nguồn:

### `ThioJoe/Auto-Synced-Translated-Dubs` (1.7k ★)
Ép co giãn cho vừa đúng khung, hoặc tổng hợp lại lần hai với tốc độ đã tính.
Tràn thì **chỉ cảnh báo**:

> `WARNING: Audio clip {key} is {difference}ms longer than expected and may overlap`

⇒ Không có mô hình tràn. Đơn giản nhất, và mất chất lượng nhiều nhất khi ngôn ngữ đích
dài hơn.

### `R3gm/SoniTranslate` (1.4k ★) — `acceleration_rate_regulation`
Khi phải tăng tốc quá `1.3×`, nó **nhìn sang đoạn kế tiếp**:

```python
duration_with_next_start = next_start - start          # gồm cả khoảng lặng
if duration_with_next_start > duration_true:
    extra_time = duration_with_next_start - duration_true
    if speaker == next_speaker:
        smoth_duration = duration_true + (extra_time * 0.5)   # mượn 50%
    else:
        smoth_duration = duration_true + (extra_time * 0.7)   # mượn 70%
    acc_percentage = max(1.2, duration_tts / smoth_duration)
```

⭐ Hai điều đáng học: **mượn khoảng lặng** thay vì ép, và **chỉ mượn một phần** (50–70%)
để vẫn còn lại một khoảng nghỉ — vì một bản lồng tiếng không có khoảng nghỉ nghe như
đọc máy.

Và `avoid_overlap` cho phép **chồng lấn nhỏ có kiểm soát**: 0,2 s nếu cùng người nói,
0,5 s nếu khác người.

⛔ Nhưng `max_accelerate_audio = 2.1` là **quá mạnh tay** — nói nhanh gấp đôi thì không
còn là giọng người nữa. Và nó **không có trần cho độ trôi tích luỹ**.

### `lukaszliniewicz/Subdub` — `align_audio_blocks` ⭐ gần nhất với bài toán của ta
Đây là lời giải đầy đủ nhất, và điểm mấu chốt nằm ở **một dòng**:

```python
block_duration = next_block_start_ms - block_start_ms     # KHÔNG phải end - start
```

Ngân sách của một đoạn là **tới lúc đoạn sau bắt đầu**, nên khoảng lặng phía sau tự động
thuộc về nó. Rồi:

```python
total_shift = 0                       # độ trôi tích luỹ, mang theo suốt bài
...
if total_shift > 0 and speed_up > 100:            # đang nợ -> tăng tốc để TRẢ NỢ
    actual = min((dur + total_shift) / dur, speed_up / 100.0)
...
if actual_audio_duration > block_duration:        # tràn -> ghi nợ
    total_shift += actual_audio_duration - block_duration
else:                                             # dư -> TRẢ NỢ bằng khoảng lặng
    if silence_needed >= total_shift:
        total_shift = 0                           # trả hết
    else:
        total_shift -= silence_needed             # trả một phần
```

Mặc định: `delay_start = 1500–2000 ms`, `speed_up = 115` (tối đa nhanh hơn 15%).

⭐ **Độ trôi không bị chặn bằng số đoạn — nó được TRẢ liên tục bằng chính các khoảng
lặng.** Đó là một câu trả lời hay hơn "không quá 3 đoạn", vì nó tự thích nghi: video
nhiều khoảng nghỉ thì nợ tan nhanh, video nói dồn thì nợ giữ lâu.

⛔ Nhưng Subdub **không có trần cứng**. Trên một đoạn video nói liên tục không nghỉ, nợ
tăng đơn điệu và tới cuối phim tiếng lệch hình rất xa mà không có gì chặn lại.

---

## Quyết định

### D1 — Ngân sách của một đoạn kéo tới lúc đoạn sau bắt đầu

```
ngan_sach(i) = bat(i+1) - bat(i)          # đoạn cuối: het(i) - bat(i) + đuôi còn lại
```

Khoảng lặng phía sau một câu **thuộc về câu đó**. Đây là thay đổi nền tảng so với
`MVP_CONTRACT.md` §6 bản Phase 02, và nó trực tiếp phản ánh quan sát: người ta không nói
liền mạch.

### D2 — Chỉ mượn một PHẦN khoảng lặng, không mượn hết

Mượn tối đa **70 %** khoảng lặng (`TY_LE_MUON_KHOANG_LANG = 0.7`), lấy theo
SoniTranslate. Mượn hết thì bản lồng tiếng không còn nhịp nghỉ — nghe như đọc máy, và
người xem mất luôn cái mốc để bám theo hình.

### D3 — Nợ trôi được mang theo và TRẢ ở mọi khoảng lặng

Một biến `troi` (ms) đi suốt bài. Đoạn tràn thì cộng nợ; đoạn còn dư khoảng lặng thì
trừ nợ, ưu tiên trả hết trước khi thêm im lặng.

### D4 — Tăng tốc là công cụ TRẢ NỢ, không phải công cụ ép vừa

Chỉ tăng tốc khi **đang có nợ**, và trần là **1,15×** (`TRAN_TANG_TOC`), theo Subdub.

⛔ Cố ý **không** lấy `2.1` của SoniTranslate: nhanh gấp đôi thì không còn là giọng
người. 1,15× nằm trong vùng `atempo` gần như không nghe ra.

⚠️ **Đây là ngưỡng MƯỢN, chưa đo trên tiếng Việt.** Kho này có luật: mượn ngưỡng thì
phải đo lại. `TestChoBangChungNgoai` giữ món nợ đó.

### D5 — Trần cứng cho độ trôi: **ba đoạn**

Đây là chỗ ta đi xa hơn cả ba dự án tham chiếu, và lý do là một bất biến ta đã tự đặt:
`MVP_CONTRACT.md` §6 nói `natural` **không bao giờ được kéo dài luồng video**, còn D-ASV-03
nói luồng hình được **sao chép** — nên tổng thời lượng là một con số cố định, không co giãn.

Không có trần thì trên một video nói dồn, nợ tăng đơn điệu tới khi tiếng lệch hình cả
chục giây. Nên:

```
TRAN_TROI_SO_DOAN = 3
```

Nợ vượt quá tổng ngân sách của **ba đoạn kế tiếp** thì dừng tích luỹ và **cắt tại biên
đoạn** — mất một câu, được lại đồng bộ. Và QC **phải ghi lại** mỗi lần cắt, vì mất lời
thoại là một khiếm khuyết chất lượng, không phải một chi tiết kỹ thuật.

⭐ Vì sao là **ba** chứ không phải một con số khác: một đoạn quá chặt (một câu dài hơn
bình thường đã đủ vượt), còn quá nhiều thì trần mất tác dụng. Ba đoạn ≈ 6–10 giây, tức
vẫn trong khoảng người xem chưa thấy tiếng rời khỏi hình. **Đây là một lựa chọn có lý
lẽ, chưa phải một phép đo** — và nó được ghi ra đúng như thế.

### D6 — Chồng lấn nhỏ được chấp nhận, có trần

Tối đa **200 ms** (`TRAN_CHONG_LAN_MS`), theo `avoid_overlap` của SoniTranslate cho
trường hợp cùng người nói. Hai câu liền nhau chồng nhau 0,2 s nghe tự nhiên; 0,5 s thì
thành hai người cùng nói.

---

## Sửa đổi hợp đồng MVP

| Mục | Bản Phase 02 | Bản này |
|---|---|---|
| §6 `fit_original` | mỗi đoạn ép vừa khung thoại của nó | mỗi đoạn có ngân sách **tới lúc đoạn sau bắt đầu**; tràn được phép, nợ được trả ở khoảng lặng, trần ba đoạn |
| §7 T2 | ±0,50 s tổng thời lượng | **giữ nguyên** — trần ba đoạn cộng phép cắt biên bảo đảm điều này |
| §7 T7 | lệch điểm bắt đầu ≤ 0,30 s | **đổi**: ≤ 0,30 s **so với vị trí đã lập kế hoạch**, không phải so với đoạn gốc. Lệch so với gốc nay là *thiết kế* chứ không phải lỗi, và nó được đo bằng chính `troi`. |
| §7 mới | — | **T11**: `troi` không bao giờ vượt ngân sách của `TRAN_TROI_SO_DOAN` đoạn kế tiếp |
| §7 mới | — | **T12**: mỗi lần cắt vì vượt trần phải được ghi vào báo cáo QC |

---

## Bất biến được bảo vệ

| Bất biến | Cơ chế |
|---|---|
| I8 durable DONE | kế hoạch thời gian là artifact có vân tay, kiểm được |
| I17 mô hình cố định | không thêm chế độ mới; `fit_original`/`natural` vẫn là hai lựa chọn duy nhất |
| D-ASV-03 sao chép luồng hình | trần trôi + cắt biên giữ tổng thời lượng cố định |

---

## Phương án bị loại

| Phương án | Vì sao loại |
|---|---|
| Ép co giãn cho vừa từng đoạn (ThioJoe) | với tiếng Việt dài hơn, mọi đoạn đều phải nén — chất lượng giọng hỏng đều |
| Tăng tốc tới 2,1× (SoniTranslate) | nhanh gấp đôi không còn là giọng người |
| Không trần trôi (Subdub) | video nói dồn làm nợ tăng đơn điệu; và nó phá D-ASV-03 |
| Kéo dài video cho vừa tiếng | phá D-ASV-03 (sao chép luồng hình) và đổi thời lượng sản phẩm khách giao |
| Cắt bớt bản dịch cho ngắn lại | mất nội dung mà khách không được biết; và đó là quyết định của tầng CONTENT chứ không phải TIMING |
