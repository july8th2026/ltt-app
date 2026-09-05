# Báo cáo Mobile Release Gate — LTT Studios

Nhánh `phien/mobile-v1`, fork từ `admin-mvp-v3` @ `911cd142` (2026-09-05).
Nguồn quy trình: `LTT_MOBILE_AUTONOMOUS_PROMPT_PACK_V1`.

---

## 1. Phán quyết

> **AUTOMATED MOBILE GATE PASS / REAL-DEVICE GATE PENDING**

⛔ **Không** gọi là `FULL MOBILE RELEASE PASS`, và lý do không phải "chưa có
thời gian": **bản WebKit của Playwright trên máy này không giải mã nổi audio** —
kể cả một WAV `data:` URI tự sinh, không qua mạng (`MediaError.code = 4`,
`networkState = 3`), trong khi vẫn báo `canPlayType('audio/wav') = "probably"`.
Chromium giải mã đúng tệp đó.

⇒ Vế *"Safari phát được tiếng"* của bug P0 **chưa ai đo được**, và không thiết bị
thật thì không đo được. Ghi PASS ở đó sẽ là bịa.

## 2. Phạm vi

| | |
|---|---|
| app trong registry | 16 |
| bề mặt khách hàng có UI | 11 app + 7 route chrome nền tảng |
| loại trừ, có lý do đo được (HTTP 404) | `anhnoibo`, `ltt_llm` (capability-only) · `nexus`, `vps` (`enabled=False`) · `qualitylab` (`surface=admin`) |
| route quét tự động | **23** (tự tìm từ registry + nav) |
| khung nhìn | 320 · 390 · 430 · 768 · ngang 844 · desktop 1440 |
| trình duyệt | Chromium + WebKit 26.5 |

## 3. Kiến trúc trước → sau

```
TRUOC                                   SAU
-----                                   ---
5 ban chep bo phan tich Range           platform_core/phat_media.py
  trong apps/, cung 4 khiem khuyet         · 1 ban, dung RFC 9110
2 app phuc vu media KHONG co Range        · 7 app dung chung
                                          · 0 ban chep con lai

khong co lop safe-area                  --ltt-day-an-toan trong ltt.css
meta viewport khong co viewport-fit     3 base template co viewport-fit=cover

5 vong hoi job khong biet tab an        server/static/nhip_job.js (2 trang)
                                        + khiHien() trong 2 app React
```

## 4. Ma trận đo — trước → sau

| chỉ số | trước | sau |
|---|---:|---:|
| route tràn ngang @390 | 1 | **0** |
| route tràn ngang @**320** | 2 | **0** |
| ô nhập < 16px, cảm ứng | 55 | **0** |
| ô nhập < 16px, **desktop** | 57 | **56** ✅ có chủ ý không đổi |
| vùng chạm < 44px @390 | 468 | 245 |
| vùng chạm < 44px, **desktop** | 747 | 906 ✅ không đổi (số tăng do seed thêm dữ liệu) |
| bản chép bộ Range trong `apps/` | 5 | **0** |
| `<video>` thiếu `playsinline` | 7 | **0** |
| ô nhập số thiếu `inputmode` | 11 | **4** (đều là `type=search`, cố ý) |
| console error | 0 | **0** |
| composer ChatLTT dưới màn hình | có | **không** |
| tải thừa mỗi lần vẽ sóng | tới 165 MB | **0** |

⚠️ **`target_be` là danh sách ỨNG VIÊN, không phải danh sách lỗi.** WCAG 2.2 SC
2.5.8 miễn trừ liên kết văn bản trong dòng, và phần lớn 245 là loại đó. Con số
đáng kể là hai kẻ tái phạm ở chrome nền tảng (`a.hdr-logo` 40×30, liên kết nav
200×37) — đã sửa — và các nút React (`run-primary`, nút chọn trang) — đã sửa.

## 5. P0 — nguyên nhân gốc và bằng chứng

**Triệu chứng người dùng báo:** *"tải về được nhưng bấm Play trên điện thoại
không chạy"*.

**Nguyên nhân gốc có HAI nửa, không phải một:**

*Nửa máy chủ* — `apps/ltt_voice/routes/_p_audio.py:90` đọc toàn tệp vào RAM rồi
trả `StreamingResponse` **không** `Accept-Ranges`, **không** `Content-Length`.
Safari/WebKit quyết định một nguồn âm thanh có tua được hay không từ chính lượt
200 đầu tiên; không thấy `Accept-Ranges` thì nó bỏ phát — trong khi `<a download>`
vẫn tải bình thường, vì tải xuống không cần tua.

*Nửa trình duyệt* — `server/static/voice.js:263` gọi `au.play()` trần. Khi bị từ
chối thì **không có gì xảy ra**: nút không đổi (trạng thái nút đến từ sự kiện
`play`, mà sự kiện đó không bắn), không lỗi console, không dòng nào trong log.
⭐ Cùng tệp ấy, dòng ~395 (nghe thử giọng) **đã bắt Promise đúng từ đầu** — một
tệp, hai cách, và chỗ bị bỏ sót là trình phát kết quả/lịch sử/dự án.

**Bằng chứng đã sửa** (máy chủ thật, cổng 8123):

```
khong Range   -> 200  accept-ranges: bytes   content-length: 401324
bytes=0-99    -> 206  content-range: bytes 0-99/401324
bytes=-100    -> 206  content-range: bytes 401224-401323/401324   (100 byte CUOI)
bytes=1e8-    -> 416  content-range: bytes */401324
```

**Phát thật trên Chromium**: bấm ▶ → `currentTime` 0 → 2,35s → tua bằng canvas
sóng → 3,57s / 4,18s; `paused=false`, `readyState=4`, `error=null`. Request đầu
là `bytes=0-` → **206**.

**Trên WebKit**: không đo được (mục 1). Đường lui `<audio controls>` mới thêm đã
kích hoạt đúng khi WebKit từ chối — tức nửa trình duyệt hoạt động như thiết kế.

## 6. Bốn khiếm khuyết của bộ Range cũ, và bằng chứng từng cái

Năm bản chép mang **cùng** bốn lỗi. Đo trên máy chủ thật sau khi gộp:

| lỗi cũ | bằng chứng đã sửa |
|---|---|
| không bao giờ trả `416` | `bytes=999999-` → **416** + `bytes */102400` |
| `bytes=-500` trả 501 byte **đầu** | đối chiếu byte: khớp 100 byte **cuối** = True, khớp 101 byte đầu = False |
| `bytes=0-` nuốt cả tệp vào RAM | phát theo khối 1 MiB, `test_900` chốt `read()` không quá `KHOI` |
| `start > end` mỗi nơi một kiểu | `bytes=500-100` → **416** ở cả ba app |

## 7. Kiểm thử

| lệnh | kết quả |
|---|---|
| `python tools\test_nhanh.py` | **6097 passed / 32 skipped / 0 failed** + 67 test frontend |
| `python tools\gate.py` | ✅ **PASS 26/26** — gồm cả 4 bộ test frontend |
| test mới | `test_900`…`test_906` — 7 tệp, ~90 phép kiểm |

**Ma trận trình duyệt sau lần build cuối** — 23 route:

| khung | Chromium tràn | WebKit tràn | console |
|---|---|---|---|
| 320 · 390 · 430 · 768 · ngang · desktop | **0** | **0** | **0** |

## 8. Bảy lần một luật/phép đo **tồn tại mà không làm gì**

Tất cả đều biên dịch được, đúng cú pháp, không lỗi ở đâu cả. Đây là phát hiện
có giá trị lâu dài nhất của lượt soát này:

1. `:where()` độ đặc hiệu **0** → luật 16px thua mọi luật thành phần. Đo lại mới
   thấy **52/55** ô nhập vẫn nhỏ.
2. `env(safe-area-inset-*)` trả **0** khi meta viewport thiếu `viewport-fit=cover`.
3. `Cache-Control` của `chatltt` bị `server/app.py:253` ghi đè — chết từ trước.
4. `overflow-y:auto` trên hàng grid cao `auto` (vỏ ChatLTT mobile) — không bị
   giới hạn chiều cao thì không có gì để tràn.
5. `<script defer>` cho tệp mà script nội tuyến gọi **ngay** → `TypeError`.
6. `songDeu` tự gọi lại chính nó — đệ quy vô hạn, và đường **duy nhất** kích hoạt
   nó là chính nhánh phòng thủ trong `veSong`.
7. `:where()` lần **thứ hai**: `.canvas-top-actions button{min-height:38px}`
   thắng luật 44px của nền tảng.

Và **bốn lần bộ đo tự nói dối**: `getBoundingClientRect().right` báo cả phần đã
bị `overflow-x:auto` hấp thụ (3 lần) · bộ bóc chú thích coi `accept="image/*"`
là `/*` rồi nuốt 31.605 ký tự · `HEAD` trả 405 làm bộ lọc vứt sạch 23 route ·
canvas **rỗng** không pan được cho **bất kỳ** đầu vào nào nên phép đo không
phân biệt được gì.

## 9. Rủi ro còn lại

| | |
|---|---|
| **Safari thật** | vế "phát được" chưa ai đo. Cần iPhone. |
| **Bàn phím ảo thật** | phép đo thay thế (thu nhỏ khung nhìn) cho thấy composer vẫn hiện, nhưng iOS thu nhỏ `visualViewport` chứ không thu nhỏ layout viewport. |
| **Phóng to 200%** (195px CSS) | 15/15 route tràn. Đã thử sửa **ba lần**, không đổi một pixel, nên đã hoàn tác cả ba. WCAG 1.4.10 đòi 320px và ở đó **đạt**. `07_BE_MAT_CHUAN.md` ghi cái đã loại trừ. |
| **Tải lại / khoá máy giữa job** | môi trường đo không có provider nào `san_sang` nên không dựng được job thật. |
| **`prompt_ai_ommi` React** | chưa seed dữ liệu; mọi phép đo tương tác của nó vẫn ở mức "chưa đo". |

## 10. Rollback

- Toàn bộ nằm trên `phien/mobile-v1`, tách khỏi `admin-mvp-v3`. **Bỏ nhánh = bỏ hết.**
- Commit theo phase ⇒ revert được từng phase.
- `platform_core/phat_media.py` là **thêm mới**; mỗi app migrate độc lập, revert
  một app không kéo theo app khác.
- Không đụng `data/`, `secrets/`, `cloudflare/`; không migration Alembic nào.
- Sau deploy: `C:\LTTPlatform\app.previous\` giữ bản trước.

## 11. Deploy — ĐÃ CHẠY, 2026-09-05 23:41

| | |
|---|---|
| commit deploy | `1320e9d12f04` |
| `EXITCODE` | **0** (không rỗng — rỗng nghĩa là chưa chạy) |
| nghiệm thu băm | **510 tệp `.py`, 0 lệch, 0 thiếu** |
| bundle 4 frontend | `source_sha256` **khớp cả bốn** |
| `/health/ready` loopback | **200** |
| `/health/ready` công khai | **200** |
| `asset_ver` | `54914535` → **`9a4f4744`** — cache-bust chạy |

⭐ Phiên này **đã có quyền Administrator sẵn** (`ConsentPromptBehaviorAdmin = 0`),
nên `deploy_nang_quyen.ps1` chạy thẳng, không cần ai bấm UAC. Memory ghi "user
bấm UAC" — điều đó đúng ở thời điểm ghi, không đúng ở máy này hôm nay.

### Chốt trên URL công khai — cái đo được và cái không

Chạy harness thẳng vào `https://app.lttstudios.com` (qua Cloudflare):

| route | 320 · 390 · ngang · desktop |
|---|---|
| `/` · `/huong-dan` · `/gia-api` | **0 tràn, 0 console error** |
| `/login` | ⛔ **không đo được** |

`/login` trả **403** với `<title>Just a moment...</title>` và
`cdn-cgi/challenge-platform` — **trang chặn của Cloudflare**, không phải trang
của ta. `curl` cũng bị 403, tức đó là luật WAF trên đường đăng nhập chứ không
riêng trình duyệt tự động.

⚠️ Nên con số "tràn 89px ở `/login`" mà lượt quét in ra là của **trang chặn**.
Ghi nó vào báo cáo như một lỗi sản phẩm sẽ là một kết luận sai — cùng lớp lỗi
"đọc thứ đại diện thay vì đọc thứ thật" đã gặp bốn lần trong phiên này.

⇒ Mọi route **sau đăng nhập** trên URL công khai vẫn **chưa đo được bằng trình
duyệt tự động**. Chúng đã đo đầy đủ ở loopback (23 route × 6 khung × 2 trình
duyệt), và CSS mới đã xác nhận ra tới biên Cloudflare — nhưng đó là hai bằng
chứng khác nhau, đừng gộp làm một.

## 12. Đẩy mã

`git push origin admin-mvp-v3` → `0aa848ea..1320e9d1`; nhánh `phien/mobile-v1`
đẩy mới. Secret scan trước khi đẩy: **Findings: 0** / 490.300 dòng.

## 13. Điều kiện còn lại

`CLAUDE.md` quy tắc 5b bắt chốt trên `https://app.lttstudios.com`, mà tới đó phải
deploy. Deploy chép **cả cây**, nên phải ff-merge về `admin-mvp-v3` trước và hỏi
các phiên đang chạy.

⚠️ Và bản deploy hiện tại đang **đi sau kho 94 commit** (phiên Voice đo được).
Sau khi deploy, `curl -s https://app.lttstudios.com/health/version` trả `commit`
+ `asset_ver` — dùng nó để biết mình đang đo bản nào thay vì suy luận.
