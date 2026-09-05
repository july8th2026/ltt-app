# 02 — CHARACTER CONTRACT (2026-09-05)

## Hai trần, và chúng KHÔNG được gộp lại

| hằng số | giá trị | nó là trần **của cái gì** |
|---|---|---|
| `TRAN_MOI_LUOT_SINH` | 1.500 | **chất lượng** — chỗ giọng model bắt đầu trôi |
| `TRAN_KY_TU_CONG_KHAI` | 100.000 | **ngân sách** — một job giữ GPU bao lâu thì còn công bằng |

⛔ Trần thứ nhất **không được** nâng lên 100.000 để giao diện thôi hiện 1.500.
1.500 vẫn là con số đúng của một lượt inference; nó chỉ không còn **rò ra**
thành trần sản phẩm, vì `ban_doc_dai.py` chia bài dài thành nhiều lượt ≤ trần ấy
rồi ghép. Đo trên trình duyệt thật (dưới đây) xác nhận đường ấy đang chạy.

Nguồn chân lý: `apps/ltt_voice/tham_so_cong_khai.py`. **Không gõ lại hai con số
này ở đâu khác** — kể cả trong tài liệu này, ngoài bảng trên.

## OBSERVED — phép đếm hai phía nói hai con số khác nhau

`len()` của Python đếm **điểm mã**; `"...".length` của JS đếm **đơn vị mã
UTF-16**. Với ASCII và tiếng Việt NFC hai số bằng nhau — nên lệch này sống rất
lâu mà không ai thấy. Chúng tách nhau ở mọi ký tự ngoài BMP, tức mọi emoji.

⛔ Và lệch ấy **đẩy về phía sai**. Ô nhập có `maxlength="{{ tran_ky_tu }}"`, mà
`maxlength` cũng đếm đơn vị mã. Nên:

    50.001 emoji  =  50.001 ky tu voi may chu   (may chu NHAN)
                  = 100.002 don vi ma voi o nhap (o nhap CAT o 100.000)

Khách dán vào một văn bản máy chủ hoàn toàn chấp nhận, và trình duyệt lặng lẽ
vứt phần đuôi. Không lỗi nào báo.

## ROOT CAUSE

Một hợp đồng ("ký tự") được cưỡng chế bằng **hai thước đo khác nhau** ở hai đầu,
và không có phép kiểm nào so hai đầu với nhau. Mẫu thử duy nhất ai cũng dùng —
tiếng Việt NFC — là mẫu mà hai thước **trùng nhau**.

## DECISION

1. **Gỡ `maxlength` khỏi ô nhập.** Nó không diễn đạt được một trần tính bằng
   điểm mã, và một trần sai là một trần cắt nhầm.
2. **Chặn ở chỗ NỘP, không chặn ở chỗ GÕ.** `voice.js::demKyTu()` đếm bằng
   `Array.from` (điểm mã, khớp chính xác `len()`), và khi vượt thì **tắt nút
   Tạo** + hiện một dòng `role="alert"` nói thừa bao nhiêu. Văn bản **ở nguyên
   trong ô** để khách tự cắt chỗ họ chọn.
3. **Nhập TXT giữ nguyên cả tệp.** Bản trước làm `s.slice(0, tran)` — mất phần
   đuôi ngay lúc nhập, **không hoàn tác được**, và cảnh báo chỉ báo một việc đã
   rồi. Nay tệp vào nguyên vẹn (đã bỏ BOM), rồi rơi vào trạng thái vượt trần ở
   trên nếu dài quá.
4. **Máy chủ vẫn là nguồn chân lý cuối cùng** (`routes/_p_tao.py`). Phía trình
   duyệt là tiện ích, không phải hàng rào.

## VERIFIED — trình duyệt thật (**Playwright / Chromium**), `127.0.0.1:8127`

⚠️ **Chromium**, không phải WebKit — và nay điều đó phải ghi ra. Phiên Mobile V1
đo 05/09: **Playwright WebKit trên Windows không giải mã nổi audio**, kể cả một
WAV `data:` URI 0,1 giây không qua HTTP (`MediaError.code = 4`), trong khi
`canPlayType('audio/wav')` vẫn trả `"probably"`. Nên "trình duyệt thật" ở đây
**không** bao gồm Safari/WebKit.

Ô đếm so với `so_ky_tu_tho` mà `POST /ltt-voice/xem-truoc` trả về:

| mẫu | ô đếm (JS) | máy chủ (`len`) | `.length` cũ | khớp |
|---|---|---|---|---|
| `Hello world` | 11 | 11 | 11 | ✅ |
| `Xin chào Việt Nam` | 17 | 17 | 17 | ✅ |
| `Chào 😀` | 6 | 6 | *7* | ✅ |
| `Xin chào 😀 hello` | 16 | 16 | *17* | ✅ |
| 50.001 × 😀 | 50.001 | 50.001 | *100.002* | ✅ |

Cột `.length` cũ là con số bản trước hiện ra — ba mẫu cuối lệch, và mẫu cuối là
mẫu bị `maxlength` cắt mất một nửa.

Biên, đo trên chính cửa `/xem-truoc`:

| ký tự | HTTP | số đoạn | ghi chú |
|---|---|---|---|
| 1.501 | 200 | **2** | ⭐ mốc quan trọng nhất — trước 31/08 bị **từ chối** |
| 3.000 | 200 | 2 | |
| 100.000 | 200 | 67 | |
| 100.001 | 400 | — | *"Văn bản dài 100.001 ký tự, vượt giới hạn 100.000…"* |

Trạng thái giao diện ở biên: 100.000 → nút Tạo **bật**; 100.001 → nút Tạo
**tắt**, dòng cảnh báo hiện.

## FILES CHANGED

- `server/static/voice.js` — `demKyTu()`, `soViet()`, trạng thái vượt trần,
  nhập TXT không cắt, bỏ BOM.
- `apps/ltt_voice/templates/ltt_voice_studio.html` — gỡ `maxlength`, thêm
  `#lv-vuot` (`role="alert"`), hai chuỗi mới, dùng filter `|so`.
- `server/static/ltt.css` — `.vuot-tran`, `.lv-vuot`.
- `platform_core/dinh_dang.py` — mới. `so_viet()`: **một** quy ước đọc số cho cả
  nền tảng. Trước đó `100000` hiện ra `100.000` ở ô đếm nhưng `100000` trong
  thông điệp lỗi của **chính cửa ấy**.
- `server/templating.py` — filter `|so` gọi `dinh_dang.so_viet`.
- `apps/ltt_voice/routes/_chung.py`, `_p_tao.py`, `_p_du_an.py`,
  `dieu_khoan.py` — thông điệp lỗi dùng `so_viet`.
- `locale/en/LC_MESSAGES/messages.po` (+ `.mo`).

## TESTS

`tests/test_397_ltt_voice_bien_ky_tu.py` — 32 phép kiểm.

⭐ Chốt mạnh nhất **không nhắc con số nào**:
`TRAN_KY_TU_CONG_KHAI > TRAN_MOI_LUOT_SINH`. Mệnh đề ấy bất biến với mọi lần
nới trần sau này, trong khi một con số chép lại sẽ đỏ ở đúng lượt commit nâng
trần — tức nó phạt việc làm đúng.

⚠️ Bộ test không chạy JavaScript. Nó chốt hai điều kiện **cần** (máy chủ đếm
điểm mã; `maxlength` và `.length` không quay lại) bằng cách đọc mã. Điều kiện
**đủ** — `demKyTu` chạy đúng trong trình duyệt — là bảng VERIFIED ở trên.

⛔ `_bo_chu_thich()` tồn tại vì bản đầu của phép kiểm tìm `s.slice(0, tran)`
trong cả tệp và **đỏ ngay** — chính chú thích giải thích cái bẫy đã trích dẫn
đoạn mã ấy. Một phép kiểm trừng phạt việc ghi lại lý do là một phép kiểm sẽ bị
làm xanh bằng cách xoá lời giải thích. Hàm ấy có `test__bo_chu_thich_tu_kiem`
kèm theo: một bộ dò quét không tự chứng minh được thì một bản hỏng sẽ làm mọi
phép kiểm dùng nó xanh vĩnh viễn.

## REMAINING RISK

- `soViet()` trong `voice.js` là **bản sao thứ hai thật** của quy ước đọc số.
  Phương án còn lại — hỏi máy chủ mỗi lần gõ một phím — tệ hơn hẳn. Chú thích ở
  cả hai đầu trỏ vào nhau; chưa có phép kiểm nào so hai bản.
- Ô đếm không `.strip()` trước khi đếm, còn máy chủ thì có. Lệch chỉ xuất hiện
  khi có khoảng trắng ở hai đầu, và nó lệch về phía **đếm thừa** — tức cảnh báo
  sớm hơn cần, không bao giờ để khách nộp rồi bị từ chối bất ngờ.

## STATUS

✅ Hai phía nói cùng một con số ở cả năm mẫu, xác minh trên trình duyệt thật.
