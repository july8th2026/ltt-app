# Hợp đồng shared vs app-owned — bảy năng lực

Chốt 2026-09-05, Phase B. Mỗi quyết định phải đi kèm **số consumer đo được**;
quy tắc của pack: chỉ lên shared khi có **≥2 consumer thật**, hoặc khi đó là hợp
đồng browser/security mà nền tảng nên sở hữu.

⛔ `platform_core` không được biết tên app nào (`AGENTS.md` mục 8.4, chốt bởi
`test_60`). Mọi thứ dưới đây đều không cần biết slug.

| # | Năng lực | Consumer đo được | Quyết định |
|---|---|:--:|---|
| B1 | Viewport / `viewport-fit` | 19/19 route | **SHARED** |
| B2 | Safe area | 4 thanh dính đáy | **SHARED** |
| B3 | Vùng chạm + cỡ chữ ô nhập | toàn nền tảng | **SHARED** |
| B4 | Media transport (Range) | **7** | **SHARED** — ưu tiên cao nhất |
| B5 | Media controller (`play()`) | 2 tệp / 3 trình phát | **APP-OWNED + khuôn có test** |
| B6 | Vòng đời job dài | 4 nơi polling, 1 bản đúng sẵn có | **SHARED** |
| B7 | Upload/download lớn | đã có kiến trúc direct/R2 | **KHÔNG ĐỘNG** |

---

## B1 · Viewport — SHARED

**Bằng chứng.** Cả 19 route dùng đúng một chuỗi:
`width=device-width, initial-scale=1`. Bốn base template
(`base.html`, `base_plain.html`, `base_public.html`, `admin/_vo.html`) là nơi
duy nhất khai nó.

**Làm gì.** Thêm `viewport-fit=cover` vào base template của khách hàng.

**Vì sao bắt buộc, không phải tuỳ chọn.** `env(safe-area-inset-*)` trả **0** khi
thiếu `viewport-fit=cover`. Nghĩa là toàn bộ hạng mục B2 sẽ *biên dịch được, chạy
được, và không làm gì cả* — dạng hỏng tệ nhất: im lặng.

**Không làm.**
- ⛔ Không đặt `user-scalable=no` hay `maximum-scale=1`. MDN cảnh báo thẳng, và
  nó chỉ **giấu** triệu chứng của B3, không chữa.
- ⛔ Không thay hàng loạt `100vh` → `100dvh` bằng regex. Chỉ 10 tệp có `100vh`;
  xét từng chỗ, vì `dvh` ở một trang cuộn bình thường làm layout *giật* khi thanh
  địa chỉ trình duyệt thu vào.
- ⛔ Không dùng `interactive-widget=resizes-content` ở phase này: chưa đo được
  hành vi thật, và pack đòi có fallback trước.

## B2 · Safe area — SHARED

**Bằng chứng.** `env(safe-area-inset-*)` = **0 lần** toàn kho. Bốn thanh hành động
`position:sticky` chạm mép dưới ở 390×844: `lv-st-nut` (Voice, `padding-bottom:0`),
`im-actions` (taoanh), `th-actions` (thumbnail), `clip-actions` (taoclipngan).

**Làm gì.** Một biến CSS ở `ltt.css`, dùng lại ở cả bốn:

```css
:root{ --ltt-day-an-toan: env(safe-area-inset-bottom, 0px); }
```

Trên desktop `env()` trả `0px` ⇒ **không đổi một pixel nào**, đúng yêu cầu
"Desktop zero-impact" của pack.

**Không làm.** Không viết `padding-bottom: calc(10px + env(...))` rời rạc ở bốn
chỗ — đó là bốn bản chép sẽ lệch, đúng cơ chế đã sinh ra năm bản Range.

## B3 · Vùng chạm + cỡ chữ ô nhập — SHARED

**Bằng chứng.** `ltt.css:44-46` đã có luật `@media(pointer:coarse)` nhưng
**thiếu `a`**; hệ quả là `a.hdr-logo` 40×30 và liên kết nav 200×37 lọt trên mọi
trang. Và **mọi** ô nhập đang hiện đều < 16px (13px là phổ biến nhất, 18 lần).

**Làm gì.**
1. Mở rộng luật coarse-pointer sang liên kết **đóng vai điều khiển** —
   `a.btn`, liên kết trong nav/tab — chứ không phải mọi `<a>`.
2. Trong cùng khối `@media(pointer:coarse)`, đặt `font-size:16px` cho
   `input/textarea/select`.

**Vì sao chỉ trong `pointer:coarse`.** Nâng ô nhập lên 16px trên desktop sẽ **phá
hệ thống chữ** của giao diện dày đặc (nhãn 10–11px là ngôn ngữ thị giác hiện có).
Rủi ro auto-zoom chỉ tồn tại trên cảm ứng, nên bản vá cũng chỉ nên tồn tại ở đó.

**Không làm.** ⛔ Không đặt `min-height:44px` cho **mọi** `<a>`. 468 phần tử đo
được dưới 44px phần lớn là liên kết văn bản trong dòng và footer — WCAG 2.5.8 có
ngoại lệ đúng cho chúng, và ép hết sẽ phá bố cục văn bản. **468 là danh sách ứng
viên, không phải danh sách lỗi.**

## B4 · Media transport — SHARED, ưu tiên cao nhất

**Bằng chứng.** 5 bản chép bộ phân tích Range + 2 app không có Range = **7 consumer**.
Bốn khiếm khuyết của bản đang được chép: xem `02_BASELINE.md` §1b.

### Ranh giới trách nhiệm

```
app                      shared
───                      ──────
kiem so huu khoa   ──►   phan tich Range
chon media_type          200 / 206 / 416
duong R2 direct          Accept-Ranges, Content-Range, Content-Length
                         phat byte theo khoi, KHONG doc toan tep
```

**App giữ nguyên phép kiểm sở hữu.** Chuyển nó lên shared là tạo bản chép thứ hai
của một phép kiểm bảo mật — và bản chép thứ hai là bản sẽ lệch.

### Hợp đồng phải đúng chuẩn, không chuẩn hoá cái sai

| tình huống | phải trả |
|---|---|
| không có `Range` | `200` + `Accept-Ranges: bytes` + `Content-Length` |
| `bytes=0-499` hợp lệ | `206` + `Content-Range: bytes 0-499/N` |
| `bytes=500-` mở đuôi | `206` tới hết tệp |
| `bytes=-500` **suffix** | `206` — **500 byte CUỐI** (bản hiện tại trả 501 byte đầu) |
| `start >= N` hoặc dải vô nghĩa | **`416`** + `Content-Range: bytes */N` |
| nhiều dải `bytes=0-9,20-29` | `200` toàn tệp (hợp lệ theo RFC 9110) |
| tệp rỗng | `200`, không `206` |

**Không đọc toàn tệp vào RAM.** Kể cả `bytes=0-` — nhất là `bytes=0-`, vì đó là
dạng Chrome hay gửi nhất.

### Trước khi dựa vào `FileResponse`

`starlette.__version__` phải được **in ra lúc runtime** và đối chiếu, không đọc
`requirements.txt`. Nhưng kho này lưu media qua `platform_core/storage.py` với
đối tượng file-like (kể cả R2), không phải đường dẫn hệ tệp — nên `FileResponse`
**không phủ được** đường chính. Lớp shared phải làm việc trên abstraction ấy.

### Test bắt buộc (dải 700–799) trước khi migrate consumer nào

no-range · start-end · open-ended · **suffix** · **invalid → 416** · tệp rỗng ·
tệp nhỏ · ownership · khoá của người khác · R2 redirect (mock).

## B5 · Media controller — APP-OWNED, nhưng có khuôn và có test

**Bằng chứng.** Chỉ 2 tệp có trình phát tự dựng: `server/static/voice.js`
(2 trình phát) và `apps/upscalevideo/templates/upscalevideo.html` (đồng bộ 2 video).

**Và trong chính `voice.js` đã có một bản đúng và một bản sai:**

| dòng | trình phát | xử lý Promise |
|---|---|---|
| `voice.js:395` | nghe thử giọng | ✅ `hua.catch(dungNgheThu)` |
| **`voice.js:263`** | **kết quả / lịch sử / dự án** | ❌ `au.play();` trần |

⭐ Đây là nửa thứ hai của P0. Máy chủ không phát ra Range ⇒ WebKit từ chối phát;
`play()` trả Promise bị từ chối ⇒ **không ai bắt** ⇒ nút vẫn hiện "đang phát".
Người dùng thấy một trình phát *nói dối*, chứ không thấy một lỗi.

**Quyết định: không dựng module JS dùng chung.** Hai tệp không đủ để trả giá cho
một lớp trừu tượng, và pack cấm biến shared thành "god mobile module". Thay vào
đó sửa tại chỗ theo khuôn, và **chốt khuôn bằng test** thay vì bằng chú thích:

```js
var hua = au.play();
if (hua && hua.catch) hua.catch(function (e) { /* tra UI ve trang thai dung */ });
```

⛔ Không `catch(()=>{})` rỗng — `upscalevideo.html:135` đang làm vậy và đó là
"nuốt lỗi lặng lẽ", chính thứ gate có một phép kiểm riêng để bắt.

## B6 · Vòng đời job dài — SHARED

**Bằng chứng.** `server/templates/job_detail.html:20-38` **đã làm đúng**: backoff
luỹ thừa, `online` → thử lại, `visibilitychange` → hoà lại ngay, `beforeunload`
→ dừng. Bốn nơi khác có `setInterval` mà **không** có `visibilitychange`:
`prompt_ai_ommi`, `taoanh`, `upscalevideo`, `dev_playground`.

**Làm gì.** Rút bản đúng sẵn có thành một helper nhỏ trong `ltt.css`-cùng-cấp JS
dùng chung, rồi cho bốn nơi kia dùng. Đây là trường hợp lý tưởng: không phải
thiết kế mới, chỉ là **ngừng để một bản đúng nằm im một chỗ**.

**Ranh giới.** Trạng thái job ở máy chủ là chân lý. Tab ẩn **giảm** nhịp hỏi, không
quyết định job còn sống hay không. `navigator.onLine` chỉ là gợi ý — một request
thật mới là bằng chứng. Không phụ thuộc Background Sync.

## B7 · Upload/download lớn — KHÔNG ĐỘNG

**Bằng chứng.** `storage.try_url_for()` (presigned/direct R2) đã được dùng ở
`autosubvideo`, `chataistudio`, `chatltt`, `prompt_ai_ommi`, `taoanh`,
`taoclipngan`, `taovideo`. Kiến trúc né trần 100 MB của Cloudflare **đã có và
đang chạy**.

**Quyết định: không thêm gì.** Pack nói rõ "giữ direct object storage/upload
session nếu hệ thống đã có" và "progress/abort/retry/resume chỉ thêm khi backend
hỗ trợ thật". Backend hiện không có resume ⇒ thêm UI resume là **giả vờ**.

---

## Gate B — đối chiếu

| điều kiện | kết quả |
|---|---|
| Mỗi năng lực có quyết định Shared/App rõ ràng | ✅ 7/7 |
| Shared chỉ khi ≥2 consumer hoặc lý do nền tảng rõ | ✅ B5 bị **từ chối** lên shared vì chỉ 2 tệp; B7 từ chối vì không có nhu cầu |
| Không branching theo slug trong platform | ✅ không quyết định nào cần biết tên app |
| Có test cho primitive trước khi rollout | ⬜ **Phase C** — dải 700–799 |

## Thứ tự thi công Phase C

1. `platform_core` — bộ trả lời Range dùng chung + test 7xx (**chưa migrate ai**).
2. `ltt.css` — B1 + B2 + B3 (một lượt, vì cả ba cùng chạm base template/CSS).
3. Migrate consumer #1 = `chatltt` (`_p_media.py`).
4. Migrate consumer #2 = `ltt_voice` (`_p_audio.py`) + sửa `voice.js:263`.
5. Đo phát thật trên WebKit — **đây mới là chỗ P0-1 được phép gọi là đã sửa.**
