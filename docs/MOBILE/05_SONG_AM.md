# Hình sóng LTT Voice — phép đo, và cái cổng suy ra từ nó

Đo 2026-09-05 trên `phien/mobile-v1`. Máy chủ `tools\studio_dev.py --cong 8123`,
Chromium qua `playwright-cli`. Dựng lại:

```powershell
python tools\mobile_qa.py wav-dai <uid-seed>
```

⛔ Tệp sinh ra **không** im lặng (sin 220 Hz + nhiễu). Một tệp toàn `\x00` nén
rất tốt và có thể đi đường tắt trong bộ giải mã — phép đo sẽ đẹp hơn sự thật.

---

## 1. Chi phí một lần vẽ sóng — tuyến tính, đo được

`veSong` làm đúng ba việc: `fetch(url)` → `arrayBuffer()` → `decodeAudioData()`.

| độ dài | tải (ms) | giải mã (ms) | tải (MB) | PCM float32 (MB) | **đỉnh (MB)** |
|---:|---:|---:|---:|---:|---:|
| 10s | 18 | 41 | 0,9 | 1,8 | 2,7 |
| 60s | 34 | 24 | 5,5 | 11,0 | 16,5 |
| 180s | 65 | 64 | 16,5 | 33,0 | 49,5 |
| 300s | 62 | 111 | 27,5 | 54,9 | 82,4 |
| **600s** | 101 | 238 | 54,9 | **109,9** | **164,8** |

⇒ **~275 KB cho mỗi giây tiếng.** WAV 48 kHz mono 16-bit = 96 KB/s tải, và PCM
float32 nhân đôi thành 192 KB/s.

⚠️ Đây là số trên **desktop, máy chủ cục bộ**. Trên điện thoại: 55 MB đi qua dữ
liệu di động, 110 MB cấp phát trên máy có 2–4 GB dùng chung, và 238 ms giải mã
thành vài giây. Không đo được ở đây — cần thiết bị thật.

⚠️ `performance.memory` **không dùng làm bằng chứng** trong bảng này: ở mốc 600s
nó báo 4,6 MB vì GC chạy giữa phép đo. Cột PCM là số học chính xác lấy từ chính
`AudioBuffer` trả về (`length × numberOfChannels × 4`), không phải ước lượng.

## 2. Và phần lớn chi phí ấy vẽ cho một chỗ không ai nhìn

Đếm canvas thật sự hiện (`display !== none` **và** `clientWidth > 0`):

| trang | 390px | 430px | 768px | 1440px |
|---|---|---|---|---|
| Studio | **1/5** | **1/5** | **1/5** | **1/5** |
| Lịch sử | 5/5 | 5/5 | 5/5 | 5/5 |

Trên màn Studio, **bốn trong năm** trình phát có canvas `display:none` — đó là
danh sách "Gần đây" thu gọn. Nhưng `veSong` chạy cho cả năm.

**Đo bằng mạng.** Bấm ▶ một dòng "Gần đây" ở 390px, cùng một tệp 401.324 byte:

```
206  bytes=0-        401.324 byte   <- the <audio>, hop le
200  (khong Range)   401.324 byte   <- fetch cua veSong
```

Tệp được tải **hai lần**, bản thứ hai giải mã ra PCM rồi vẽ vào một canvas
`display:none`. Ở trần 600 giây, bản thứ hai ấy là **165 MB cho không**.

## 3. Cổng — hình học, không phải một hằng số mới

Bề ngang canvas **thật sự** đo được (px → số cột, mỗi cột 3 px):

| | 390px | 430px | 768px | 1440px |
|---|---|---|---|---|
| Studio | 106 → **35 cột** | 146 → 48 | 476 → 158 | 190 → 63 |
| Lịch sử | 240 → **80 cột** | 268 → 89 | 525 → 175 | 112 → **37 cột** |

Hai điều rơi ra từ bảng này:

**a. Canvas rộng 0 px vẽ được 0 cột.** Nên câu hỏi *"có đáng giải mã không"*
chính là câu hỏi *"vẽ được bao nhiêu cột"* — một luật xử lý luôn cả trường hợp
`display:none`, không cần phép kiểm thứ hai.

**b. Ở 35 cột và trần 600 giây, MỘT cột gánh 17 giây tiếng.** Âm tiết tiếng Việt
dài ~0,2 giây, nên một cột 17 giây luôn chạm đỉnh — hình sóng thành một khối đặc.
Nó không còn mô tả gì, nó chỉ tốn 165 MB.

⇒ Cổng trên cảm ứng: **`au.duration <= soCotVe(canvas)`** — mỗi cột gánh không
quá một giây. Không có hằng số giây thứ hai nào ra đời; con số tự suy từ bố cục
và tự đổi theo bố cục.

`server/static/voice.js::soCotVe` cố ý **không** có mặc định `|| 300`, khác
`songGia`/`songDeu`: hai hàm kia chỉ *vẽ*, hàm này *quyết định*.

## 4. Kết quả sau khi đặt cổng

| ca | số cột | độ dài | kết quả | `fetch` vẽ sóng |
|---|---:|---:|---|---:|
| 390px cảm ứng | 80 | 10s | sóng thật | 1 |
| 390px cảm ứng | 80 | 600s | track phẳng | **0** |
| 1440px chuột | 37 | 10s | sóng thật | 1 |
| 1440px chuột | 37 | 600s | sóng thật | 1 |
| 390px, canvas `display:none` | 0 | 4s | track phẳng | **0** |

Chốt bởi `tests/test_902_voice_song_khong_ve_cho_khong.py`.

## 5. Hai thứ **không** làm, và vì sao

**a. Không đổi `TRAN_GIAY_SONG = 600`.** Đó là quyết định của phiên Voice, dựa
trên chi phí bộ nhớ. Phép đo mật độ thông tin ở mục 3 là một lập luận **mới** —
đã báo cho họ kèm số. Đổi hay không là quyết định của chủ hệ con, không phải của
một lượt soát mobile. `test_902` chốt luôn điều này: nếu 600 đổi, phép kiểm đỏ và
người đổi phải nói rõ đó là quyết định của ai.

**b. Không dựng peaks tiền tính.** Chính `voice.js` đã ghi đường nâng cấp đúng:
*"để worker ghi sẵn một mảng đỉnh (peaks) cạnh tệp tiếng, rồi chỗ này tải một tệp
vài KB thay vì cả bản tiếng — khi ấy không còn trần nào cả."* Việc đó chạm vào
worker và định dạng lưu trữ, tức nằm ngoài phạm vi một lượt soát mobile. Bảng ở
mục 1 là **con số mà bản peaks phải đánh bại**: 275 KB/giây → vài KB cố định.

## 6. Một lỗi tiềm ẩn tìm được trên đường

`songDeu` mở đầu bằng `if (!canvas) { songDeu(canvas); return; }` — **tự gọi lại
chính nó với cùng một `canvas` rỗng**, tức đệ quy vô hạn.

Nó chưa bao giờ nổ, vì mọi nơi gọi đều truyền canvas thật. Nhưng đường **duy
nhất** kích hoạt nó lại chính là nhánh phòng thủ `if (!canvas)` trong `veSong` —
nghĩa là dòng viết ra để tự bảo vệ sẽ là dòng giết cả handler bằng
`RangeError: Maximum call stack size exceeded`. Sửa 05/09.
