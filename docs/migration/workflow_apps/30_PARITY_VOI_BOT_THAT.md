# 30 — Parity đo trên 1.932 lượt job thật, và một phát hiện đổi cả tiêu chí

**Ngày đo:** 2026-09-10 · **Kho vàng:** `Bot_Whisper_FULL/output/<drive_folder_id>/`
(chỉ đọc) · **Bộ đối chiếu:** `tests/test_1108_parity_transcript.py`

Yêu cầu của chủ sản phẩm là *"file đầu vào và kết quả đầu ra phải đạt như nhau"*.
Tài liệu này trả lời câu đó bằng phép đo, và ghi lại **vì sao câu hỏi phải được
phát biểu lại** trước khi trả lời được.

---

## 1. Kho vàng là gì

Mỗi thư mục trong `output/` là một lượt job thật đã giao, chứa đúng một cặp:

| Tệp | Vai trò |
|---|---|
| `transcript_raw_temp.json` | **đầu vào** — kết quả STT thô, có `words` |
| `transcript.json` | **đầu ra** — bot đã giao thật cho kênh |

1.932 cặp đọc được. Không cần GPU, không cần tệp audio: cặp này đúng bằng phần
`make_timeline_v2` + chiếu schema + bộ kiểm — tức toàn bộ phần ta chuyển.

---

## 2. 🔴 Phát hiện làm đổ tiêu chí ban đầu: engine **cố ý ngẫu nhiên**

Lượt đo đầu cho **60,90 %** và tôi suýt đi săn một khiếm khuyết của bản chuyển.
Thứ chặn lại là một quan sát nhỏ: **ví dụ lệch đổi giữa hai lượt chạy trên cùng
một thư mục** (`189.39` rồi `186.94`). Đo thẳng:

```
cùng đầu vào, 3 lượt trong CÙNG một tiến trình → 3 kết quả KHÁC nhau
đầu vào không hề bị đổi tại chỗ
```

Nguồn: `engine/segment/silence.py::split_silence_segments_random_2_5` gọi
`random.uniform` để cắt khoảng lặng dài thành chunk 2–5 giây — **có chủ ý**, để
B-ROLL không đều đặn máy móc.

⇒ *"Đầu ra trùng khớp từng byte"* là mục tiêu **bất khả về nguyên tắc**. Không
phải khó, mà là không tồn tại. Chính bot, chạy lại trên cùng tệp, cũng không tái
hiện được đầu ra của chính nó.

---

## 3. Tiêu chí đúng, và **đối chứng** không thể thiếu

Thứ ngẫu nhiên hoá chỉ là ranh giới *bên trong* một vùng lặng; bản thân vùng
`[start, end]` được bảo toàn. Nên ba mệnh đề:

| | Mệnh đề |
|---|---|
| **T1** | đoạn `speech` trùng khớp tuyệt đối (`start`, `end`, `text`) |
| **T2** | các **vùng** lặng (gộp chunk liên tiếp) trùng khớp tuyệt đối |
| **T3** | dòng thời gian liên tục, không hở không chồng |

Đo bản chuyển theo ba mệnh đề đó ra **95,50 %**. Con số đó **một mình nó không
nói gì**. Nên chạy **chính engine gốc**, cùng dữ liệu, cùng tiêu chí:

| Toàn kho 1.932 cặp | Đạt cả T1+T2+T3 |
|---|---|
| **engine GỐC** so với đầu ra của **chính nó** | **1850/1932 = 95,76 %** |
| **bản CHUYỂN** so với cùng đầu ra đó | **1845/1932 = 95,50 %** |

Bốn lượt rút mỗi bên:

```
gốc     95,76  95,60  95,24  95,19 %
chuyển  95,50  94,93  95,65  95,70 %
```

Hai dải chồng lên nhau, và **ở lượt 2 bản chuyển vượt bản gốc**. Chênh 5 cặp là
nhiễu. ⇒ **Bản chuyển trung thành đúng bằng mức bản gốc trung thành với chính
nó.** Đó là mức trần khả dĩ, và ta đã ở đó.

> Nếu bỏ cột "engine GỐC", báo cáo sẽ đọc ra là *"thiếu 4,5 %"* và sẽ có người
> đi sửa một thứ không hỏng. Cột đối chứng là phần đắt nhất của phép đo này.

---

## 4. Ba thứ đã lộ ra nhờ đối chiếu, không lộ ra bằng đọc mã

### 4.1 `__init__.py` của gói `segment` bị đánh rơi phần tái xuất

Bản chuyển đầu của tôi rút nó xuống mỗi dòng docstring. Mã của App **không vỡ**,
vì nó nhập thẳng `from .engine.segment.core import ...`. Nên **không phép kiểm
nào chạm tới** — nó chỉ lộ khi bộ đối chiếu nhập theo lối tài liệu của bot gốc.
Đã khôi phục 5 tên công khai.

### 4.2 Tham số thật khác mặc định của mã

`configs/bot_config_whisper.json` **đang chạy**: `segment.min_s = 1.5`. Mặc định
trong `make_timeline_v2` là **3.0**. Đo trên cả năm mẫu: đổi `target_min` sang
3.0 hoặc `target_max` sang 5.5 thì **kết quả lệch ngay**. Đã ghim bằng phép kiểm.

### 4.3 Một "đứt quãng" là **ngưỡng sai**, không phải mã sai

Một job cho dòng thời gian hở tại đoạn 75. Nhưng **chính tệp vàng hở y hệt ở
đúng chỉ số đó**, và engine gốc tái hiện 10/10 lượt. Khe hở 0,02 s = hai tầng
`round(..., 2)` độc lập cộng dồn. Nới dung sai lên `0.021`: **1932/1932** cả bên
ta lẫn tệp vàng.

---

## 5. Bộ mẫu commit vào kho — và vì sao nó được **CHỌN**

`tests/golden/parity_transcript/` — 5 cặp, 356 KB, **byte nguyên vẹn** từ
production (không cắt, vì cắt là đổi đầu ra mong đợi).

Chúng nằm trong nhóm job mà engine chạy **20/20 lượt ra cùng một kết quả**, và
kết quả đó **trùng tuyệt đối** với tệp bot đã giao. Nhờ vậy phép kiểm trong gate
là khẳng định **chính xác**, không phải thống kê, và không chớp chớp.

| Mẫu | Ngôn ngữ | Kết bằng | Trục nó giữ |
|---|---|---|---|
| `mau_01` | en | nói | ngắn nhất (14 đoạn) |
| `mau_02` | vi | nói | tiếng Việt |
| `mau_03` | en | lặng | `audio_duration` thực sự làm việc |
| `mau_04` | vi | lặng | vi + lặng đuôi |
| `mau_05` | en | — | **đi qua nhánh chót `smart_silence_tag`** |

⚠️ `mau_05` được thêm **sau**: bốn mẫu đầu **đều trượt** nhánh dùng `silence_text`
của cấu hình, nên tham số ấy không được ghim bởi phép kiểm nào. Tôi đã nghi nó
"trơ" — **sai**. Đo toàn kho: nó chiếm **13,00 %** số đoạn lặng (2.417/18.595) ở
846/1937 job. Bốn mẫu kia chỉ là trượt.

⛔ Tên thư mục gốc là **Drive folder ID** — nằm trong danh sách cấm chép của
`CLAUDE.md`. Mẫu được đặt tên trung tính; `so_tay.json` chỉ giữ SHA-256, đủ để
truy ngược bằng cách quét lại cây production mà không xuất bản chính id.

---

## 6. Phân bố nhãn khoảng lặng trên toàn kho (18.595 đoạn)

| Nhãn | Số | Tỷ lệ |
|---|---:|---:|
| `[B-ROLL: TRANSITION]` | 6.488 | 34,89 % |
| `[B-ROLL: ENVIRONMENT]` | 6.453 | 34,70 % |
| `[B-ROLL / PAUSE]` | 2.417 | 13,00 % |
| `[B-ROLL: PAUSE]` | 1.370 | 7,37 % |
| `[B-ROLL: OUTRO]` | 875 | 4,71 % |
| còn lại | 992 | 5,33 % |

⚠️ `[B-ROLL: PAUSE]` (7,37 %) **không phải** giá trị trong cấu hình — nó là mặc
định trong chữ ký `make_timeline_v2`. Tức 1.370 đoạn được sinh bởi một đường gọi
**không** truyền giá trị cấu hình vào. Kho vàng trải một năm nên đây nhiều khả
năng là bản engine cũ hơn; chưa truy tiếp vì nó không chạm parity hôm nay.

---

## 7. Chỗ hổng còn lại, nói thẳng

- **`audio_duration` không có trong tệp đầu vào** (nó đọc từ chính tệp audio, thứ
  ta không còn). Đọc engine: nó chạm **duy nhất** đoạn lặng cuối
  (`_assemble_timeline`); mọi đoạn khác sinh từ `words`. Nên nó được lấy lại từ
  `vàng[-1]["end"]` — chỗ duy nhất nó quan sát được. Đây là **một mảnh của đáp án
  dùng để dựng đề bài**, và nó được khai ra ở đây chứ không giấu. Lượt đối chứng
  để `None` (engine tự tính `words[-1].end + 1.0`) cho **0,00 %**, tức phần nó
  gánh là có thật và đúng bằng đoạn cuối.
- **Chưa đo `vad_speech_segments` và tầng STT** — kho vàng bắt đầu *sau* STT.
  Muốn phủ hai tầng đó phải có tệp audio gốc.
- `transcript_raw_temp.json` **đã mang sẵn** `type`/`index`/`scene_id`/`duration`,
  tức nó không phải đầu ra thuần của Whisper. Chưa truy `_transcribe_to_file`.
