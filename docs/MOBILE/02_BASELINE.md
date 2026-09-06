# Baseline mobile — đo được, không đoán

Đo 2026-09-05 trên `phien/mobile-v1` @ `911cd142`.
Máy chủ đo: `python tools\studio_dev.py --cong 8123` (sqlite dùng một lần dưới
`tmp/studio_dev/`, **không chạm CSDL/kho thật**).
Trình duyệt: Playwright Chromium + **WebKit 26.5**.
Phạm vi: **19 route × 5 khung nhìn × 2 trình duyệt = 190 ô đo.**

⚠️ **Một sửa chữa phải ghi lại, vì nó suýt thành một kết luận sai.** Lượt đo đầu
báo `500` ở `/chatltt` và `/prompt-ai-ommi`. Nó **không phải lỗi sản phẩm**:
`studio_dev.py` chỉ nạp bảng của `ltt_voice`, nên sqlite dùng một lần thiếu
`ommi_resource`. Đã dựng đủ bảng bằng `registry.load_app_tables()` (đường
registry, không gõ cứng slug nào) rồi đo lại → cả hai `200`, console sạch.
Bài học cho Phase G: harness phải nạp bảng theo registry, không theo danh sách tay.

---

## 1. Media transport — P0

### 1a. `ltt_voice` và `chatltt` phục vụ media **không có HTTP Range**

`apps/ltt_voice/routes/_p_audio.py:90`

```python
with get_storage().open(key) as f:
    data = f.read()                       # toàn tệp vào RAM
...
return StreamingResponse(io.BytesIO(data), media_type=kieu)
```

Không `Accept-Ranges`, không `Content-Length`, không 206, không 416.
`apps/chatltt/routes/_p_media.py:143` cùng hình dạng.

Đây khớp đúng chế độ hỏng mà `RESEARCH_BASELINE.md` của pack mô tả: WebKit bug
211323 và Starlette #950 — Safari từ chối phát media từ máy chủ không hỗ trợ
Range, trong khi **tải xuống vẫn chạy**. Đó chính là triệu chứng người dùng báo:
*"tải về được nhưng bấm Play trên điện thoại không chạy"*.

🔴 Chưa xác nhận bằng phát thật trên WebKit — đó là việc của Phase C, và nó phải
là một phép **đo**, không phải một suy luận. Ở đây mới chỉ chốt: **đường này
không phát ra Range, chấm hết.**

### 1b. Năm bản chép của cùng một bộ phân tích Range, cùng bốn khiếm khuyết

`taovideo:621` · `taoclipngan:521` · `upscalevideo:780` · `agent/workspace:149` ·
`autosubvideo:858` — gần như giống nhau từng dòng.

Đọc `apps/taovideo/routes.py:621-644`, bốn khiếm khuyết:

1. **Không bao giờ trả 416.** Range không hợp lệ bị nắn thành `start=0` và trả
   206 với dải sai. `QUALITY_GATES.md` đòi 416.
2. **Suffix range sai nghĩa.** `bytes=-500` nghĩa là *500 byte cuối*. Bộ này đọc
   `s=""` → `start=0`, `e="500"` → `end=500`, tức trả **501 byte đầu**. Sai dữ liệu,
   không phải sai định dạng.
3. **`bytes=0-` nuốt cả tệp vào RAM.** Chrome hay gửi đúng dạng này. `end=total-1`
   ⇒ `f.read(total)`. Với một video vài trăm MB đó là vài trăm MB RSS mỗi lượt.
   (`autosubvideo` là bản duy nhất không dính, nhờ `_iter_storage_range`.)
4. **`start > end` xử lý mỗi nơi một kiểu**: 4 app đặt `start = 0` và **giữ**
   `end`; `agent` đặt `start, end = 0, total - 1`. Cùng một đầu vào, hai kết quả.

⭐ Nghĩa là bản "tham chiếu" mà pack bảo cân nhắc migrate sang **tự nó đang hỏng**.
Lớp shared của Phase B phải viết đúng chuẩn, không phải chuẩn hoá cái sai này.

---

## 2. Viewport / safe-area

- `meta[name=viewport]` **chỉ một giá trị duy nhất trên toàn bộ 19 route**:
  `width=device-width, initial-scale=1`.
  → **không có `viewport-fit=cover`** ở đâu cả (trừ `server/admin_templates/sqladmin/base.html`,
  là trang admin của thư viện).
- `env(safe-area-inset-*)`: **0 lần** trong toàn bộ `server/ apps/ frontend/`.

Hệ quả: safe-area **chưa tồn tại**, không phải "chưa nhất quán". Và nó không thể
tồn tại chừng nào meta viewport chưa có `viewport-fit=cover`.

**4 thanh hành động dính đáy đang cần nó** (đo ở 390×844, `position:sticky`,
`bottom` chạm mép dưới):

| route | phần tử | `padding-bottom` hiện tại |
|---|---|---|
| `/ltt-voice` | `div.lv-st-nut` | `0px` |
| `/taoanh` | `div.im-actions` | `10px` |
| `/taoanh/thumbnail` | `div.th-actions` | `10px` |
| `/taoclipngan` | `div.clip-actions` | `10px` |

4 consumer ⇒ vượt ngưỡng "≥2" của pack cho shared layer.

---

## 3. Cỡ chữ ô nhập — nguy cơ iOS auto-zoom

**Mọi ô nhập đang hiện trên nền tảng đều dưới 16px.** `input_nho == input_hien`
ở cả 19 route.

| font-size đo được | số lần (mẫu) |
|---|---|
| 13px | 18 |
| 12px | 4 |
| 14px | 3 |
| 9px | 3 |
| 11px | 2 |
| 13.33px | 1 |

Tổng theo khung nhìn: 55 ô ở 390px, 57 ô ở 768px.

Theo `RESEARCH_BASELINE.md` (Hermes WebUI #630, Claude Code #76896), Safari iOS
tự phóng to trang khi focus vào ô có computed font-size < 16px. Và cách chữa
**không** được là `user-scalable=no` — MDN cảnh báo thẳng.

---

## 4. Vùng chạm

Đếm phần tử tương tác đang hiện có chiều cao < 44px, ở 390×844: **468**.

⚠️ **Con số này là danh sách ỨNG VIÊN, không phải danh sách lỗi.** WCAG 2.5.8 có
ngoại lệ cho liên kết văn bản trong dòng, và phần lớn 468 là liên kết ở footer/nội
dung. Đừng báo cáo nó như "468 lỗi".

Cái **thật sự** là lỗi: phân loại theo thẻ cho ra **`a` = 55, `button` = 2**. Và
`server/static/ltt.css:44-46` giải thích chính xác vì sao:

```css
@media(pointer:coarse){
  :where(button,.btn,summary,input:not([type=hidden]),select){min-height:44px}
  :where(button,.btn,summary){min-width:44px}
}
```

**Luật này không có `a`.** Nên mọi liên kết-đóng-vai-nút đều lọt. Hai kẻ tái phạm
xuất hiện trên **mọi** trang, tức là hai lỗi ở chrome nền tảng chứ không phải lỗi
của app nào:

- `a.hdr-logo` — **40×30**
- liên kết app trong menu điều hướng — **200×37**

---

## 5. Tràn ngang

**Chỉ một route tràn**, và chỉ ở 390px:

| route | Chromium | WebKit | thủ phạm |
|---|---|---|---|
| `/huong-dan` | 12px | **28px** | ba khối `<code>`, khối rộng nhất chạm x=1015 |

18 route còn lại: **0px** ở cả 5 khung nhìn, cả hai trình duyệt.

⭐ Đây là tin tốt và nó **đảo ngược một giả định của pack**: nền tảng này không có
vấn đề tràn ngang diện rộng. Ngân sách Phase F nên dồn sang chỗ khác.

*(Thanh tab của app ở `/ltt-voice` cuộn ngang trong chính nó — có chủ ý, và
`document.scrollWidth` đo được 0, nên nó không phải lỗi.)*

---

## 6. `playsinline`

Quét toàn bộ thẻ `<video>` render thật: **1 thẻ thiếu `playsinline`**, ở
`/taoclipngan`, ở cả 5 khung nhìn. `upscalevideo` đã có.

Theo chính sách media iOS của WebKit, thiếu thuộc tính này thì iPhone ép phát
toàn màn hình thay vì phát tại chỗ.

---

## 7. Console / mạng

Sau khi sửa lỗi harness ở đầu tệp: **0 console error, 0 request hỏng, 19/19 route
trả 200**, trên cả Chromium lẫn WebKit, cả 5 khung nhìn.

---

## Ảnh bằng chứng

`docs/MOBILE/anh/baseline-390-{huong-dan,ltt-voice,chatltt,taovideo}.png`
(390×844, DPR 2, có dữ liệu seed — không phải trang rỗng).
