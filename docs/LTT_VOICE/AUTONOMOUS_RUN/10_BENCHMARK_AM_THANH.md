# BENCHMARK ÂM THANH — đo bằng ASR, không bằng cảm nhận

Ngày 2026-09-02 · giọng `Ngọc Huyền` · engine VieNeu-TTS v3 Turbo trên RTX 5060 Ti
Yêu cầu: prompt 10 của gói V4, mục *Audio benchmark*.

---

## 1. Phương pháp, và giới hạn của nó

```
văn bản  →  chuan_hoa()  →  engine sinh WAV  →  faster-whisper `small`  →  CER
```

CER = Character Error Rate = khoảng cách Levenshtein chia độ dài bản gốc.

⛔ **CON SỐ NÀY LÀ TRẦN TRÊN CỦA LỖI TTS, KHÔNG PHẢI LỖI TTS.** Nó gộp cả lỗi
của ASR. `whisper small` tự nó nghe sai — và ta thấy điều đó trực tiếp: cùng một
chuỗi `RTX 3090`, nó nghe đúng ở một câu ngắn và nghe thành `otx` ở một câu dài.

⇒ Dùng nó để **so sánh giữa các hạng mục** và để **so trước/sau một thay đổi**.
Đừng đọc "14,4%" thành "engine đọc sai 14,4% số ký tự".

Muốn tách hết nhiễu ASR thì cần một bản ghi **người đọc** cùng câu làm đối
chứng — ngoài phạm vi vòng này, và là việc của cổng V10.

### 1.1 🔴 Phép đo lần đầu BỊ NHIỄM, và nó nhiễm đúng ở ba hạng mục tệ nhất

Lượt chấm đầu so bản ASR với **văn bản đã chuẩn hoá** — nghe thì đúng, nhưng:

| hạng mục | CER lượt đầu | ASR viết | engine đọc |
|---|---|---|---|
| `ngay` | 39,6 % | `20 tháng 5 2025` | `hai mươi tháng năm…` |
| `tien` | 26,0 % | `1 tỷ 250 triệu` | `một tỷ hai trăm năm mươi triệu` |
| `so` | 15,9 % | `1 234` | `một nghìn hai trăm ba mươi bốn` |

Cả ba **đúng nghĩa**. Thứ khác nhau là **chính tả của ASR**: whisper viết chữ
số, engine đọc ra chữ. Chấm như vậy là chấm *ASR viết số thế nào*, không phải
*TTS đọc có đúng không*.

⭐ Sửa: đưa **cả hai phía** qua cùng `text_pipeline.chuan_hoa()` rồi mới so.
Sau đó `so` tụt từ 15,9 % xuống **3,4 %** — tức 12,5 điểm trong con số cũ là
nhiễu thuần tuý.

⚠️ Bài học chung: **một phép đo sai chỗ vẫn cho ra số, và số đó trông rất
thuyết phục.** Nếu dừng ở lượt đầu, kết luận sẽ là "hạng mục tiền/ngày/số hỏng
nặng" và ai đó sẽ đi sửa một thứ không hỏng.

---

## 2. Kết quả

| hạng mục | ký tự | tiếng (s) | RTF | CER lượt đầu | **CER công bằng** |
|---|---:|---:|---:|---:|---:|
| `vi_thuong` tiếng Việt thường | 120 | 6,72 | 1,233 | 1,7 % | **1,7 %** |
| `en_thuong` tiếng Anh thuần | 115 | 7,44 | 1,449 | 2,6 % | **0,0 %** |
| `tron_lan` trộn Anh–Việt | 127 | 7,84 | 1,274 | 8,0 % | **6,9 %** ¹ |
| `ten_rieng` tên riêng có dấu | 109 | 5,52 | 1,316 | 1,9 % | **1,9 %** |
| `so` số kiểu Việt | 92 | 6,80 | 1,312 | 15,9 % | **3,4 %** |
| `tien` tiền tệ | 105 | 7,36 | 1,072 | 26,0 % | **17,3 %** ² |
| `ngay` ngày/giờ | 90 | 8,32 | 1,400 | 39,6 % | **39,6 %** ³ |
| `thuat_ngu` viết tắt kỹ thuật | 100 | 9,52 | 1,315 | 22,2 % | **14,4 %** ¹ |
| `cau_dai` một hơi 353 ký tự | 353 | 17,80 | 1,009 | 5,2 % | **5,2 %** |
| `toc_do` 0,85× | 76 | 3,84 | 1,280 | 1,3 % | **1,3 %** |
| `toc_do` 1,0× | 76 | 3,84 | 1,296 | 0,0 % | **0,0 %** |
| `toc_do` 1,25× | 76 | 3,68 | 1,317 | 2,5 % | **2,5 %** |

¹ sau bản sửa từ điển ở §3 · ² xem §2.1 · ³ xem §2.2

**RTF** (thời gian sinh / thời lượng tiếng): min **1,009** · trung bình **1,273**
· max **1,449**. Tức engine sinh chậm hơn thời gian thực khoảng 1,3 lần trên card
này. Câu càng dài RTF càng tốt (`cau_dai` = 1,009) — chi phí nạp/khởi động được
chia đều ra nhiều hơn.

### 2.1 `tien` 17,3 % — phần lớn vẫn là nhiễu

```
engine đọc : doanh thu tháng này đạt một tỷ hai trăm năm mươi triệu đồng…
ASR nghe   : dành  thu tháng này đạt 1 tỷ 250 triệu đồng…
```

Lỗi **thật** duy nhất là `doanh → dành` (một từ). Phần còn lại là ASR viết
`1 tỷ 250 triệu` thay vì đọc thành chữ — `chuan_hoa` không đổi `1 tỷ 250 triệu`
thành chữ vì nó vốn đã lẫn chữ với số.

### 2.2 `ngay` 39,6 % — KHÔNG phải lỗi phát âm, mà là bất đối xứng của chuẩn hoá

```
engine đọc : ngày 20 tháng 5 năm 2025 … ngày hai tháng chín năm hai nghìn…
ASR nghe   : ngày 20 tháng 5     2025 … ngày 2 tháng 9 năm 2026
```

⭐ Nhìn kỹ: `chuan_hoa` đổi `02/09/2026` thành chữ, nhưng để nguyên `20 tháng 5
năm 2025` ở dạng số. Engine tự đọc số ấy — **và đọc đúng** (ASR nghe ra `20
tháng 5`). Nên hạng mục này không có lỗi phát âm nào; nó chỉ cho thấy
`chuan_hoa` **không đồng nhất** giữa hai cách viết ngày.

⚠️ Không sửa trong vòng này: đổi hành vi chuẩn hoá ngày là đổi thứ **khách nghe
được** và đổi cả **cơ sở tính tiền** (`manifest._gia()` đếm trên bản đã chuẩn
hoá). Nó xứng đáng một quyết định riêng, không phải một sửa tiện tay.

---

## 3. Một phát hiện THẬT, và hai "bản sửa" bị loại

`thuat_ngu` và `tron_lan` hỏng vì **viết tắt không có trong `VIET_TAT`**:

```
HTTPS  ->  "hat TTFS"      MP3  ->  "muu phe 3"      WAV  ->  "5v kep AV"
```

Nhưng luật 1 của `tu_dien.py` là *"chỉ thêm khi đã NGHE THẤY sai"*. Nên thay vì
đoán cách đọc rồi thêm, tôi làm **A/B**: sinh cùng một câu hai lần — một lần để
nguyên viết tắt, một lần tự tay giải ra — rồi cho ASR nghe cả hai.

| viết tắt | để nguyên | đã giải | quyết định |
|---|---|---|---|
| `HTTPS` | `hát TTFS` ✗ | **`HTTPS`** ✓ | **thêm** |
| `MP3` | `mưu phê 3` ✗ | **`MP3`** ✓ | **thêm** |
| `WAV` | `5v kép AV` ✗ | `Quap` ✓ | **thêm** |
| `HTTP` | `hát trở tìm bị` ✗ | `hát tê tê bề` ✓ | **thêm** |
| `RTX` | **`RTX 3090`** ✓ | `AZTX` ✗ | **LOẠI** |
| `HTML` | **`html`** ✓ | `hát, kềm L` ✗ | **LOẠI** |

🔴 **Hai trong năm ứng viên sẽ làm hỏng một thứ đang chạy tốt** — và cả hai
"trông cần sửa" y hệt bốn cái kia. Không có phép đo thì không cách nào phân
biệt. Đây chính xác là lý do luật 1 tồn tại, và là lần đầu nó được kiểm chứng
bằng số.

⚠️ Và một cái bẫy: trong bài `thuat_ngu` (câu dài), ASR nghe `RTX` thành `otx`.
Dừng ở đó thì đã kết tội RTX. Đo riêng một câu ngắn thì nó đúng. **Một lần nghe
sai trong câu dài không đủ để kết tội một từ.**

**Đo lại sau khi thêm bốn mục:**

| | trước | sau |
|---|---:|---:|
| `tron_lan` | 8,0 % | **6,9 %** |
| `thuat_ngu` | 16,7 % | **14,4 %** |

Cải thiện có thật nhưng **khiêm tốn** — phần còn lại là nhiễu ASR và cụm
`NVIDIA RTX 3090` mà whisper nghe sai bất kể ta làm gì.

---

## 4. Kết luận

✅ **Tiếng Việt thường, tên riêng, tiếng Anh, văn bản dài, cả ba mức tốc độ:
CER ≤ 5,2 %** — trong đó phần lớn là nhiễu ASR. Không tìm thấy lỗi phát âm hệ
thống nào ở các hạng mục này.

✅ **Không thấy trôi giọng ở câu 353 ký tự / 17,8 giây** (CER 5,2 %, ngang
tiếng Việt thường). Phù hợp với phép đo trôi tông độc lập ngày 01/09.

✅ **Tốc độ hậu kỳ không làm hỏng nội dung**: 0,85× → 1,3 %, 1,0× → 0,0 %,
1,25× → 2,5 %.

🔧 **Đã sửa**: bốn viết tắt (`HTTPS`, `HTTP`, `MP3`, `WAV`), có bằng chứng A/B.

⚠️ **Còn mở, không sửa trong vòng này**: `chuan_hoa` không đồng nhất giữa
`dd/mm/yyyy` và `ngày D tháng M năm Y` (§2.2). Không phải lỗi phát âm.

### Những gì phép đo này KHÔNG nói

- **Tương đồng người nói** (giọng nhân bản có giống người thật không) — cần
  embedding so sánh, không phải ASR.
- **Độ tự nhiên / ngữ điệu** — CER không thấy được một câu đọc đúng chữ nhưng
  vô hồn.
- **Clipping, méo, nhiễu nền** — cần đo tín hiệu (`do_chat_luong.py` của
  `voice_sidecar` có sẵn cho việc này).
- **Trôi giọng ở 3.000 ký tự** — trần hiện tại là 1.500, chưa đo ngoài trần.

Bốn mục đó là nội dung của cổng **V10**, không phải của vòng này.

---

## 5. Tái hiện

```bash
# Pha 1 — sinh (venv nen tang)
python do_am_thanh_1_sinh.py
# Pha 2 — ASR (whisperx-venv, co faster-whisper)
"C:/LTTPlatform/whisperx-venv/Scripts/python.exe" do_am_thanh_2_asr.py
# Pha 3 — cham cong bang (venv nen tang)
python do_am_thanh_3_cham.py
```

Dữ liệu thô: `D:\_lttvoice_dev\do_am_thanh\pha{1,2,3}.json` — giữ cả bản ASR
nghe được để ai đọc lại cũng tự chấm lại được, không phải tin bảng trên.
