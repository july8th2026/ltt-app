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

### ✅ Đã làm — và nó lộ ra một chỗ phải **cố ý lệch** khỏi bản gốc

`tests/test_1109_parity_video_khop_clip.py` + 4 bộ mẫu job thật (110 KB: chỉ
`transcript.json` và **tên** clip — tầng này không mở video).

🔴 **Đầu ra của bot phụ thuộc thứ tự thư mục của hệ tệp.** Đo trên `row196`
(240 clip / 125 cảnh): ba thứ tự đầu vào cho **ba kết quả khác nhau**, và
**115/125 cảnh đổi clip**. Nguồn: `clip_sampling.py:75` dùng `os.listdir()`
**không** `sorted()`.

⭐ Khác `random.uniform` của App `transcript`. Cái kia ngẫu nhiên **có chủ đích**.
Cái này thì mã **đã có** cơ chế phân định — biến `suffix` — và chú thích của nó
nói rõ ý định:

> `001-scene_id-1.mp4 (suffix=0) > 001-scene_id-1-2.mp4 (suffix=2)`

Nhưng `suffix` chỉ được tính khi `parse_source == "scene_id"`. Tên thật trên
production **đều có tiền tố** (`002-scene_id-2-2.mp4`) nên đi nhánh `prefix`, và
`suffix` **luôn bằng 0**. Luật `suffix < current_priority` không bao giờ cắn —
người thắng là **người đến trước**.

⇒ Đây là **khiếm khuyết**, không phải thiết kế. Bản sửa sắp xếp đầu vào theo
`(số cảnh, hậu tố, tên)` ngay trong `build_sequential_timeline`: kết quả hết phụ
thuộc thứ tự, **và** clip gốc thắng biến thể — đúng ý định chú thích đã viết.

⚠️ Đây là thay đổi **duy nhất** trong engine chuyển nguyên vẹn của App này, và
   nó được khai ở đây vì "parity" với một bản gốc không tất định là một mệnh đề
   không có nghĩa: không tồn tại **một** đầu ra hợp lệ để so.

Ba mệnh đề khác cũng ghim được, đều đo trên job thật:

| | Mệnh đề |
|---|---|
| thiếu clip cho một cảnh | **ném lỗi nêu đích danh** cảnh (`S0069`), không im lặng dựng video hụt |
| không có clip nào | ném lỗi |
| `safe_name` | **giữ nguyên tiền tố** — nối tầng bảo mật với tầng khớp clip |

Mệnh đề cuối là ràng buộc thật: bản vá path traversal **không** được thay tên
bằng UUID, vì `sequential` khớp cảnh bằng tiền tố. Giờ có phép kiểm giữ nó.

### ✅ Tầng sinh phụ đề `.ass` — chốt theo cấu hình đang chạy

Bốn mô-đun `subtitle/` **giống hệt** bản gốc (0 dòng khác), nên đối chứng vi sai
vô nghĩa ở đây. Giá trị nằm ở việc chốt **cấu hình thật** và bất biến đầu ra.

Kiểu production đọc từ `configs/pipeline.yaml` đang chạy: `style_preset: default`
(Arial 48, trắng, viền đen 2, bóng 1, đậm, `alignment=2`, lề 20/20/30),
`segment_mode: sentence`, `max_chars_per_line: 42`, `max_lines: 2`.

⚠️ `font_family: ''` và `font_size: 0` **không** phải "đặt thành rỗng" mà là
"dùng mặc định preset" — GUI dùng `0` làm ô trống. `runner.py:585` lọc chúng ra,
và chú thích nói rõ hậu quả nếu quên: *"font_size=0 sẽ override preset
font_size=48 → render lỗi"*.

⛔ Phép lọc ấy **cố ý bất đối xứng**: `outline_width` và `shadow_offset` bị loại
khỏi luật "0 = mặc định", vì `0` ở đó là lựa chọn hợp lệ (không viền / không
bóng). Trước `tests/test_1110_...` thì thứ **duy nhất** giữ sự bất đối xứng ấy là
một dòng chú thích — và cả hai chiều hỏng đều **im lặng**.

Đối chứng đã chạy: tiêm `outline_width` vào tập, và bỏ `font_size` khỏi tập —
phép kiểm bắt được **cả hai**.

Khác App `transcript` ở một điểm đáng ghi: tầng này **tất định**, không có nguồn
ngẫu nhiên nào, nên phép kiểm đòi **đúng từng byte** giữa hai lần sinh.

### ⛔ Nợ mở: giai đoạn "tự chấm điểm" chưa có đường lấy khoá

Bot legacy lấy khoá Gemini từ **một trường văn bản thuần** trong
`configs/pipeline.yaml` (`evaluation.gemini_api_key`). Nền tảng này không có
trường ấy và **không được** có — bí mật đi qua `platform_core/api_pool`, nơi đã
sẵn provider `gemini`.

Vấn đề là engine chuyển nguyên vẹn **không ném lỗi** khi thiếu khoá
(`engine/runner.py:677`): nó ghi `api_key="missing (env GEMINI_API_KEY)"` rồi vẫn
gọi `evaluate_video(gemini_api_key="")`, dựa vào biến môi trường — thứ không
được đặt ở đây.

⇒ Không chặn thì khách bật công tắc, **trả credit cho cả lượt**, và nhận lại một
giai đoạn không thể chạy. Đã thêm **cổng chặn ở `chuan_hoa()`**: bật
`bat_cham_diem` mà không có khoá thì từ chối ngay, kèm câu nói rõ lý do.

⚠️ Đó **không** phải bản sửa cuối. Bản sửa thật là nối `evaluation` vào
`api_pool`, và nó cần ba quyết định chưa có: phiên DB bên trong `chay()`,
`category` nào cho một lời gọi Gemini **thị giác** (pool hiện đăng ký
`gemini-2.5-flash-image` ở `APIKEY_CAT_IMAGE`), và ứng xử khi pool cạn giữa job.
Cho tới lúc đó, ràng buộc **nhìn thấy được** thay cho một công tắc giả.

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

### ✅ Đã làm — tách phần QUYẾT ĐỊNH ra khỏi phần gọi ffmpeg

`ke_hoach_ghep(thoi_luong, ke_hoach_chen)` tách khỏi `_ghep_voi_khoang_lang`:
trả về dãy thao tác `("lang", i, ms, 0)` / `("doan", i, đầu, cuối)`, không đụng
đĩa. Bốn quyết định giờ kiểm được mà **không cần audio**, đối chiếu từng dòng với
`bot/worker.py:999-1043`:

| | Quyết định | Dòng gốc |
|---|---|---|
| 1 | điểm cắt = `{0.0} ∪ {at_sec} ∪ {thời lượng}`, khử trùng rồi sắp | 1006-1007 |
| 2 | hai mốc trùng `at_sec` → **gộp lấy cái LỚN HƠN**, không cộng dồn | 1018 |
| 3 | đoạn < 0,001 s → bỏ | 1029-1030 |
| 4 | khoảng lặng đặt **TRƯỚC** đoạn bắt đầu tại mốc đó | 1032-1039 |

⚠️ Quyết định 2 là chỗ dễ "sửa cho hợp lý" nhất: cộng dồn nghe đúng hơn
(800 + 1800 = 2600) và **không phải** hành vi đã chạy một năm.

Và hai biên kế thừa, **ghi lại chứ không sửa**:

- mốc rơi **đúng cuối tệp** → bị bỏ im lặng (vòng lặp chạy tới `len-1`);
- mốc **vượt thời lượng** → sinh một đoạn quá đuôi audio.

⭐ Không sửa vì **đường thật không chạm tới**: `at_sec` sinh từ việc khớp văn bản
với mốc thời gian của chính bản ghi lời ấy. Khác hẳn ca `sequential_timeline`
bên `video_assembly` — ở đó khiếm khuyết **đo được là đang xảy ra** trên 115/125
cảnh của một job thật, nên sửa. Ở đây không có phép đo nào nói nó từng xảy ra,
và sửa một thứ chưa từng hỏng là đổi hành vi mà không có căn cứ.

⛔ Nhắc lại giới hạn: bốn bài này chứng minh **thuật toán khớp bản gốc**, chúng
**không** chứng minh *"kết quả như bot đã giao"*. Mệnh đề đó ở App này vẫn không
kiểm được — không có hiện vật nào.

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
