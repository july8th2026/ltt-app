# 31 — Dữ liệu test job có thật cho từng App, và cách đối chiếu khả dĩ

Khảo sát `D:\FULL AUTO VIDEO` (chỉ đọc) ngày 2026-09-10. Kết luận ngắn: **mức
đối chiếu khả dĩ khác nhau rất nhiều giữa bốn App**, và nó do *dữ liệu còn lại*
quyết định chứ không do ta chọn.

| App | Hiện vật thật còn lại | Mức đối chiếu đạt được | Trạng thái |
|---|---|---|---|
| `transcript` | **1.932 cặp vào/ra** | đối chiếu đầu ra thật | ✅ xong |
| `video_assembly` | 8 bộ **đầu vào** job thật + 1 bộ E2E đủ | tầng khớp clip + phụ đề | 🟡 làm được |
| `audio_pause` | **không còn hiện vật nào** | đối chứng vi sai với hàm gốc | 🟡 làm được |
| `prompt_canh` | không (đầu ra là LLM) | cấu trúc, không phải chữ | 🔴 khác loại |

---

## 1. `transcript` — xong

Xem `30_PARITY_VOI_BOT_THAT.md`. Gốc 95,76 % · chuyển 95,50 % trên 1.932 cặp;
5 mẫu đã commit vào `tests/golden/parity_transcript/`.

---

## 2. `video_assembly` — có đầu vào thật, không có đầu ra thật

### Cái đang có

`DUNGVIDEO-FULL/_bot_downloads/{CONG_GIAO, KETRUYEN-FULL, PHATGIAO-FULL}/` —
**8 thư mục job thật**, mỗi thư mục:

```
transcript.json    VIDEO/<clip>.mp4    VOICE/<nhac>.mp3    manifest_rename.json
```

`DUNGVIDEO-FULL/_test_job/` — **một bộ E2E đủ và nhỏ**: 5 clip + `voice.mp3` +
`transcript.json` (5 đoạn) + `output.mp4` + 13 tệp `.ass` (h01…h13).

### 🔑 Hai điều đo được, đáng giá hơn cả bộ dữ liệu

**(a) Sáu khoá được xác nhận chéo.** Cả 8 `transcript.json` đầu vào ở đây đều có
**đúng** `{start, end, text, type, scene_id, index}`, không thừa không thiếu.
Đây là chứng cứ **độc lập** cho hợp đồng schema tôi vừa ghim ở App `transcript`
— nó đến từ *phía tiêu thụ*, một bot khác, chứ không từ cùng một nguồn.

**(b) Một clip **không** ứng một cảnh.** `row196` có **240 clip cho 125 cảnh**,
với tên kiểu `002-scene_id-2-2.mp4` — hậu tố `-2` là clip thứ hai của cùng cảnh.

⚠️ Điều này khẳng định lại quyết định lúc vá lỗi path traversal: **không** được
thay tên tệp bằng UUID, vì chế độ `sequential` đọc tiền tố tên để khớp cảnh.
Bản vá đã dùng `safe_name(PurePosixPath(name).name)` chính vì lý do đó, và bây
giờ có dữ liệu thật chứng minh nó.

### Cách đối chiếu

Hai tầng **tất định, văn bản, không cần GPU và không cần ffmpeg**:

1. **Khớp clip ↔ cảnh** (`sequential`): đầu vào là danh sách tên tệp thật +
   `transcript.json` thật; đầu ra là ánh xạ cảnh → clip. So với ánh xạ suy ra từ
   chính tên tệp. Trường hợp bắt buộc phải phủ: nhiều clip một cảnh, cảnh thiếu
   clip (`row142` có 59 cảnh **0 clip**), clip thừa.
2. **Sinh phụ đề `.ass`**: `transcript.json` → `.ass`, so từng dòng với tệp `.ass`
   của `_test_job` ứng với kiểu đang dùng trên production.

⛔ Không đối chiếu `output.mp4` — đầu ra ffmpeg phụ thuộc phiên bản, không phải
   một phép đo về mã của ta.

---

## 3. `audio_pause` — không còn hiện vật, phải đổi phương pháp

### Vì sao không có

`Bot_PausePipeline/workdir_bot/` **rỗng**: bot tải lên Drive rồi xoá cục bộ.
`state_pause.json` ghi **3.099 chu kỳ**. Trong log: **1.398 lượt `job_done`**,
nhưng bản ghi chỉ mang `elapsed_s` và một liên kết Drive — **không** có số mốc
khớp/trượt, không có tệp kết quả.

⇒ Không có cặp vào/ra nào để đối chiếu. Nói thẳng ra như vậy, thay vì dựng một
  bộ dữ liệu tự chế rồi gọi nó là parity.

### Cách khả dĩ: đối chứng vi sai với chính hàm gốc

Đúng kỹ thuật đã cho kết quả ở App `transcript`: chạy **hàm legacy** và **bản
chuyển** cạnh nhau trên cùng đầu vào, đòi hai bên ra **giống hệt**. Khác một
điểm quan trọng: ở đây bản gốc là *lời phán quyết*, không phải *đối chứng* — nên
đầu vào phải là thật, không phải bịa:

- **bản ghi lời**: lấy từ kho vàng `transcript` đã có (thật, có `words`);
- **danh sách mốc**: `sample_pause_plan.json` của chính bot, cộng các mốc trích
  từ chữ trong bản ghi lời đó.

Hai hàm phải phủ: `_ghep_voi_khoang_lang` (điểm cắt, và luật **hai mốc cùng một
giây thì lấy khoảng lặng LỚN HƠN chứ không cộng dồn**) và tầng khớp mốc.

⚠️ Giới hạn phải khai: cái này chứng minh **bản chuyển == bản gốc**, nó **không**
chứng minh *"kết quả như bot đã giao"*. Với App này thì mệnh đề thứ hai hiện
**không kiểm được**, và sẽ vẫn thế trừ khi lấy lại được tệp kết quả từ Drive.

---

## 4. `prompt_canh` — khác loại, đừng ép vào cùng một khuôn

Đầu ra là văn bản của LLM. Không tất định, và **không có** một đầu ra "đúng" để
so. Đối chiếu ở đây chỉ có nghĩa ở tầng **cấu trúc**, và đó là những thứ đã ghim
trong `tests/test_1105_app_prompt_canh.py`: nguyên văn prompt, `LICH_SU_CANH=5`,
`LO_BUOC2=10`, `LO_BUOC3=5`, và việc `dien()` dùng `str.replace()` tuần tự chứ
không `format()` (giá trị chứa `{ }`).

⇒ Đừng viết một phép kiểm so chữ đầu ra với một mẫu — nó sẽ chớp chớp, rồi ai đó
  sẽ nới nó cho tới lúc nó không còn đo gì.

---

## 5. Thứ tự nên làm

1. `video_assembly` tầng khớp clip — dữ liệu đã sẵn, tất định, và nó gác đúng
   chỗ bản vá bảo mật vừa chạm.
2. `video_assembly` sinh `.ass` — cần chốt kiểu phụ đề nào là kiểu production.
3. `audio_pause` đối chứng vi sai — cần chép hàm gốc ra chỗ chạy được.
4. `prompt_canh` — không thêm gì, đã đủ.
