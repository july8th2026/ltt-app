# 03 — LONGFORM FRONTEND (2026-09-05)

## OBSERVED — sóng âm giải mã cả tệp

`veSong()` trong `server/static/voice.js` làm đúng ba bước:

    fetch(url) -> arrayBuffer() -> AudioContext.decodeAudioData(ca tep)

Đầu ra sidecar là **WAV 48 kHz mono 16-bit** (`voice_sidecar/chot_sinh.py` mục ①)
= 96 KB mỗi giây tiếng. `decodeAudioData` giải ra float32, tức gấp đôi lần nữa:

| độ dài yêu cầu | giây tiếng | tải về | PCM giải mã | **đỉnh** |
|---|---|---|---|---|
| 1.500 ký tự *(trần cũ)* | ~75 | 7 MB | 14 MB | ~21 MB |
| 10.000 | ~503 | 48 MB | 97 MB | ~145 MB |
| **100.000** *(trần nay)* | **~5.035** | **483 MB** | **967 MB** | **~1,4 GB** |

⭐ Và chú thích cũ ngay trên `veSong` **đã dự báo đúng chuyện này**:

> *"Voi mot luot doc 1.500 ky tu (~90 giay …) thi on. Neu tran ky tu duoc noi
> nhieu lan thi cho nay phai doi sang doc dan — nhung do la mot van de chua ton
> tai."*

Trần được nới ngày 03/09. Chỗ ấy thì không. Vấn đề "chưa tồn tại" đã tồn tại
được hai ngày trước khi ai đó quay lại đọc câu ấy.

## ROOT CAUSE

Một chú thích ghi đúng điều kiện làm nó hết đúng, nhưng **không có gì cưỡng chế
điều kiện ấy**. Người nới trần ở `tham_so_cong_khai.py` không có lý do nào để mở
`voice.js`, và không phép kiểm nào nối hai tệp đó lại.

## DECISION — phương án A (trần thời lượng), không phải B (peaks phía worker)

Bốn phương án đã cân:

| | mô tả | chi phí | vì sao không / có |
|---|---|---|---|
| A | trần thời lượng, dài thì vẽ track phẳng | ~40 dòng JS | ✅ **chọn** |
| B | worker sinh sẵn mảng đỉnh cạnh tệp tiếng | bảng/kho mới, migration, job cũ không có | đúng hướng, nhưng là một hạng mục riêng |
| C | Range request + tự đọc PCM | `/audio` trả `StreamingResponse`, **không** nhận `Range` | không khả thi hôm nay |
| D | sóng giả + tiến độ thật | là một lời nói dối nếu khách đọc nó như dữ liệu | ⛔ |

⭐ Và trần này có **hai** lý do độc lập, không phải một:

1. **Bộ nhớ** — bảng trên.
2. **Mật độ thông tin.** Canvas rộng ~600 px, mỗi cột 3 px ⇒ ~200 cột. Với 5.035
   giây thì một cột là **25 giây tiếng**. Hình sóng ấy không còn nói gì về bản
   đọc; nó là nhiễu. Sóng thật ngừng có ích từ rất lâu **trước** khi nó thành
   nguy hiểm — nên cái trần không phải một sự hy sinh.

`TRAN_GIAY_SONG = 600`. 600 × 288 KB ≈ **173 MB đỉnh**, tương đương ~11.900 ký
tự — gần hết mọi lượt Studio thật; và ở 600 giây một cột đã là 3 giây.

## ⛔ Chỗ dễ sinh ra một lời nói dối, và cách tránh

`songGia()` vẽ một hình sóng **ngẫu nhiên suy từ URL** làm chỗ giữ trước khi
sóng thật tải xong. Nó trung thực **chỉ vì nó bị thay** ngay khi bấm phát.

Nếu trần chỉ đơn giản là "đừng gọi `veSong`", thì với bản đọc dài `songGia` sẽ
**nằm lại vĩnh viễn** — và khách sẽ đọc nhiễu ngẫu nhiên như dữ liệu thật của
bản thu. Đó đúng là thứ mục 8 của bản yêu cầu cấm.

⇒ Nên phương án A đi kèm `songDeu()`: một dãy cột **đều nhau**. Nó không giả vờ
mô tả âm thanh — nó là một thanh tiến độ có đốt, và `veLaiSong` vẫn tô màu theo
tiến độ phát nên nó vẫn làm đúng việc khách thực sự dùng ở đó.

## Dọn residue "Chạy lô"

`taoLo()` và `motLo()` — **236 dòng**, export qua `window.LttVoice`, và **không
khuôn mẫu nào gọi**. Không có `ltt_voice_lo*.html`; màn ấy chưa bao giờ được xây.
Chúng đi kèm mọi lượt tải `voice.js` của mọi trang Voice.

Đã gỡ, thay bằng một khối chú thích ghi **vì sao** màn ấy không quay lại: đường
tài liệu dài lấy mất chính nhu cầu sinh ra nó; phần còn lại là định nghĩa của Dự
án. Và ghi rõ điều kiện để nó *được phép* quay lại — một năng lực lô thật như
`infer_batch` gộp nhiều đoạn vào một lượt GPU, chứ không phải "mỗi dòng một job".

Cùng lượt: `manifest.py` sửa "SÁU TAB" → **NĂM**, gỡ nhãn `NHAN_NGUON["lo"]` và
`doc_man_lich_su.NGUON` `"lo"`.

## FILES CHANGED

- `server/static/voice.js` — `TRAN_GIAY_SONG`, `songDeu()`, `veSong(canvas, url, au)`
  chờ `loadedmetadata` nếu chưa biết độ dài; gỡ 236 dòng Chạy lô.
- `apps/ltt_voice/manifest.py`, `routes/_chung.py`, `doc_man_lich_su.py`.

## TESTS

`test_397::test_song_am_co_tran_thoi_luong` — chốt `TRAN_GIAY_SONG` và `songDeu`
tồn tại. Đây là **chốt mạnh hơn thứ nó đo**: nó không chứng minh được ngưỡng
đúng, nhưng nó làm bản sửa không thể lặng lẽ biến mất.

## VERIFIED — trình duyệt thật, hai phía của ngưỡng

Dựng một `<audio>` với WAV thật 0,1 giây, ghi đè `duration` để đứng hai bên
`TRAN_GIAY_SONG`, rồi bấm phát và đọc lại `canvas.__dinh`:

| `duration` | số cột | mọi cột bằng nhau | đổi sau khi phát | có gọi mạng |
|---|---|---|---|---|
| **700 s** (> 600) | 605 | ✅ **có** | ✅ có | ⛔ **KHÔNG** |
| 10 s, **gỡ `AudioContext`** | 605 | ✅ **có** | ✅ có | ⛔ **KHÔNG** |
| 0,1 s (< 600) | 605 | không | không | ✅ có |

⭐ Ba điều được chứng minh, và điều thứ ba là điều quan trọng nhất:

1. Trên ngưỡng, `songDeu()` chạy — **mọi cột bằng nhau**, tức một track phẳng,
   không phải một hình sóng.
2. Nó **thay** `songGia` (`doiSauKhiPhat: true`) ⇒ nhiễu ngẫu nhiên suy từ URL
   **không** nằm lại vĩnh viễn. Đây đúng là cái bẫy mô tả ở trên, và nó đóng.
3. Trên ngưỡng **không có lượt gọi mạng nào**. Bằng chứng đến từ một chỗ bất
   ngờ: CSP của nền tảng chặn `blob:` (`connect-src 'self' …`), nên ca 0,1 giây
   để lại **hai** dòng lỗi console — còn ca 700 giây **không để lại dòng nào**.
   Tức nhánh dài thoát ra **trước** `fetch`, chứ không phải tải cả tệp rồi mới
   bỏ. Với một tệp 483 MB thì khác biệt ấy là toàn bộ vấn đề.

⚠️ Vì `blob:` bị CSP chặn, ca 0,1 giây **không** chạy trọn `decodeAudioData` —
   nó chỉ chứng minh nhánh ngắn *có* gọi mạng. Đường giải mã thật là mã **không
   đổi** trong lượt này.

## 🔴 MỘT LỖI TÔI TỰ TẠO RA, VÀ TỰ BẮT KHI SOÁT DIFF

Bản đầu của cái trần chỉ xử lý **hai** nhánh: dài hơn trần, và không có `au`.
Nhánh thứ ba — `!window.AudioContext` — vẫn `return` trần như mã cũ.

⭐ Ở mã **cũ** điều đó vô hại: `songGia` sắp bị sóng thật thay. Sau khi thêm
trần thì **không còn gì thay nó**, nên trên một trình duyệt không có
`AudioContext` (Safari cũ, vài WebView) nhiễu ngẫu nhiên suy từ URL sẽ nằm lại
**vĩnh viễn** — đúng thứ cái trần này sinh ra để tránh.

⇒ Bài học, và nó tổng quát hơn cái lỗi: **một bất biến mới không tự lan sang
những nhánh có sẵn.** Ba nhánh ấy đều đúng theo luật cũ (*"rồi sẽ có sóng
thật"*), nên chúng không trông như lỗi khi đọc lướt. Chỉ khi phát biểu bất biến
ra thành lời — *mọi đường thoát đều phải vẽ* — thì nhánh thiếu mới lộ.

Nay cả **bốn** đường thoát đều vẽ, kể cả nhánh hoãn lại chờ `loadedmetadata`:
nếu metadata không bao giờ về thì cái `return` hoãn ấy **trở thành** một đường
thoát thật. Vẽ trước không mất gì — metadata về và bài đủ ngắn thì `veSong` chạy
lại và ghi đè bằng sóng thật.

`test_397::test_moi_duong_thoat_cua_veSong_deu_ve_song_deu` chốt luật này bằng
cách đếm `return` trong thân hàm và đòi mỗi cái đi kèm `songDeu`.

## REMAINING RISK

⚠️ **Bảng bộ nhớ là TÍNH TOÁN, không phải ĐO.** Không có sidecar GPU trong lượt
này nên không sinh được một bản thu 84 phút để cân. Con số 96 KB/giây thì chắc
chắn (48.000 × 2 byte); phần nhân đôi khi giải mã là hành vi tài liệu hoá của
`decodeAudioData`. Thứ **đã** đo là hành vi của cái ngưỡng (bảng VERIFIED trên),
không phải độ lớn của tai hoạ nó tránh.

⚠️ Nhánh `loadedmetadata` — khi `duration` còn `NaN` lúc bấm phát — **chưa chạy
thật**: phép kiểm trên ghi đè `duration` nên nó luôn hữu hạn ngay.

⚠️ `/audio` đọc **cả tệp vào RAM máy chủ** (`StreamingResponse(io.BytesIO(data))`).
Với một tệp 483 MB đó là 483 MB RSS mỗi lượt tải. Ngoài phạm vi lượt này, nhưng
nó là cùng một lớp lỗi ở phía máy chủ và **chưa được xử lý**.

### 🔴 VÀ TÔI ĐÃ ĐỌC RỦI RO ẤY THIẾU MỘT NỬA — phiên Mobile V1 chỉ ra (05/09)

Tôi đọc `f.read()` thành **một vấn đề bộ nhớ**. Nó còn là một vấn đề **giao thức**:
không đọc theo luồng thì cũng **không có `Accept-Ranges`**, và Safari/WebKit
**từ chối phát** một nguồn audio mà máy chủ không hỗ trợ `Range`.

    grep -c "Range|accept-ranges" apps/ltt_voice/routes/_p_audio.py  ->  0

⭐ Hai cách đọc dẫn tới hai mức ưu tiên khác hẳn nhau:

  · *"tốn RAM"*      ⇒ máy chủ chậm khi có bài dài — khó chịu, chưa chết ai;
  · *"thiếu Range"*  ⇒ **khách mobile bấm Play không chạy** — hỏng tính năng.

Và triệu chứng đã được báo từ trước: *"tải về được nhưng bấm Play trên mobile
không chạy"*. Tôi có cả hai mảnh — dòng `f.read()` và triệu chứng — mà không nối
chúng lại, vì tôi đã dán nhãn "bộ nhớ" cho dòng mã ấy ngay từ đầu và không đọc
lại nó nữa.

⇒ Bài học, hẹp và dùng được: **một dòng mã có thể hỏng theo nhiều đường độc lập.
  Dán nhãn nguyên nhân cho nó là đóng cửa với những đường còn lại.**

Đang sửa ở `phien/mobile-v1` (media transport dùng chung ở `platform_core`, giữ
nguyên phép kiểm sở hữu của app).

⚠️ Khi bản ấy vào, chú thích ở `server/static/voice.js` (~dòng 849) nói *"`/audio`
   … không nhận `Range`"* sẽ **thành sai** và phải dọn theo. Bản vá sóng âm của
   lượt này vẫn chạy đúng — nó lấy độ dài từ `au.duration`, không từ
   `Content-Length` — nhưng lý do ghi cạnh nó thì hết đúng.

## STATUS

✅ Bẫy treo tab đã chặn — đo được rằng nhánh dài **không gọi mạng**.
✅ Bản thay thế không bịa dữ liệu: track phẳng, và nó thay `songGia`.
⚠️ Độ lớn của tai hoạ tránh được là TÍNH TOÁN; hành vi của ngưỡng là ĐO.
