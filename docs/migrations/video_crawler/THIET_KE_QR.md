# Thiết kế đăng nhập bằng QR — `video_crawler` (làn L5, 22/09/2026)

> **Chủ của:** cách khách SaaS đăng nhập Douyin / Bilibili / Xiaohongshu / Kuaishou bằng quét QR thay cho tự xuất
> `cookies.txt`. Chỉ thiết kế — chưa có mã. Mọi dẫn chứng là `tệp:dòng` đọc tại `7b6ea889` (nhánh `phien/vcm-qr`).
> Quyết định cần chủ dự án: §9. Kế hoạch TDD: §10.

## 0. Tóm tắt một đoạn

Một app runtime anh em `apps/video_crawler_browser/` (`requires=("browser",)`, `surface="runtime"`) chạy job
`video_crawler_browser.dang_nhap_qr` trên một làn worker `browser` riêng. Job mở Chromium headless với **profile tạm
riêng của job** (không profile chung), chụp QR, đẩy ảnh vào storage dưới khoá riêng của job, rồi chờ khách quét. UI
poll một route của `video_crawler` có kiểm chủ. Khi thấy cookie xác thực (đọc 2 lần liên tiếp), worker gọi
`phien.luu` (mã hoá `secretbox`), xoá ảnh QR và profile. **Rủi ro lớn nhất không nằm ở mã** mà ở nền: IP datacenter
máy A + đăng nhập từ thiết bị lạ kích hoạt kiểm soát rủi ro (f2 đã **bỏ** tính năng QR Douyin vì lý do này, §8.1),
và một tính năng "quét QR để trao phiên" có thể bị lợi dụng làm QRLJacking (§7.2). Khuyến nghị: làm, nhưng coi QR là
**đường thuận tiện** bên cạnh `cookies.txt` (giữ nguyên), bật theo nền, đo tỉ lệ thành công thật trước khi mở rộng.

## 1. Hợp đồng LTT hiện có (đọc thật)

| Hợp đồng | Dẫn chứng | Hệ quả cho QR |
|---|---|---|
| `requires` khai theo **APP**, không theo `job_type` | `platform_core/registry.py:569-576`; lọc `set(requires) ⊆ capabilities` ở `platform_core/jobs.py:242-252` | Không thể để `video_crawler` (`requires=("api",)`, `apps/video_crawler/manifest.py:47-50`) sinh job browser ⇒ **bắt buộc app anh em** |
| Tiền lệ app runtime anh em | `apps/asv_media/manifest.py:1-15` (lý do tách), `:85-109` (`catalog_parent`, `surface="runtime"`, `public=False`, `enabled=False`, `lifecycle="internal"`) | Sao y khuôn: `catalog_parent="video_crawler"` |
| Nộp job chéo app, `max_attempts=1` | `apps/auto_scan_video/jobs.py:450-459` (`jobs.submit`, **không** `submit_with_credit`) ; chữ ký `platform_core/jobs.py:139-145` | Nộp từ route `video_crawler` với `app_slug="video_crawler_browser"`, `max_attempts=1` (thử lại = QR mới cho người không còn nhìn) |
| Import mã app mẹ từ app runtime | `apps/asv_media/jobs.py:18` (`from apps.auto_scan_video...`) | Handler gọi thẳng `apps.video_crawler.phien.luu` |
| Làn worker `LTT_WORKER_POOLS` | `job_worker.py:83-133` (đọc env `:107`, làn = `{"api"} ∪ tên` `:124-125`, không đặt ⇒ một làn đa năng `:108-109`); cảnh báo app vô hình `job_worker.py:59-81` | Production (theo `docs/LTT_VOICE/GUI_DOI_SOAT_VA_PLAN_V2.md:306`) là `api:6, gpu+ffmpeg:1, voice:1` ⇒ **chưa có làn browser** ⇒ job QR sẽ `queued` mãi. Phải thêm `browser:N` (§9) |
| Trần runtime browser 1800 s | `platform_core/job_runner.py:63-68`; áp theo lớp `job_runner.py:533-544`; lớp từ `requires` `platform_core/public_api/limits.py:289-302` | QR cần ≤ ~7 phút ⇒ khai hẹp `max_runtime_s={"video_crawler_browser.dang_nhap_qr": 420}` như `video_crawler` khai `:50` |
| Huỷ hợp tác | `JobContext.progress` ném `JobCancelled` khi job đã huỷ `job_runner.py:110-117`; `is_cancelled()` `:169-174`; `jobs.cancel` `jobs.py:513` | Vòng chờ gọi `ctx.progress` mỗi ~1 s ⇒ huỷ có hiệu lực ≤ 1 s |
| Mồ côi | `ORPHAN_TIMEOUT = 5 phút` `jobs.py:35-36`; `reclaim_orphans` `jobs.py:574`; thử lại chỉ khi `attempts < max_attempts` `jobs.py:545` | Với `max_attempts=1` worker chết ⇒ job lỗi sau ≤ 5 phút, **không** dựng QR lại |
| Sự kiện job cho khách | `job_events.CUSTOMER/INTERNAL` `platform_core/job_events.py:20-21`; `append` `:85`; `timeline` `:146`; helper app `apps/video_crawler/jobs.py:125-128` | Trạng thái QR đi bằng mã sự kiện (§3.3), không bằng chuỗi tự do |
| Mã hoá phiên | `platform_core/secretbox.py:55` (`ma_hoa`), `:62` (`giai_ma`); ⚠ salt dùng chung kho API key `:28-29` (DANH_GIA §3 dòng 13) | Cookie QR đi đúng đường `phien.luu` (`apps/video_crawler/phien.py:75-98`), không đường riêng |
| Lọc cookie khi lưu | `phien._loc` `phien.py:39-72` (chỉ tên miền của nền, bắt buộc có `cookie_dang_nhap`) | Worker xuất cookie jar Playwright ⇒ chuyển sang Netscape ⇒ `phien.luu` — một cửa kiểm duy nhất |
| Storage | giao diện `platform_core/storage.py:64-74` (`put/open/delete/exists`), `url_for` `:103`; tiền tố cục bộ `LTT_STORAGE_LOCAL_PREFIXES` `:461-480` | Ảnh QR: khoá `video_crawler_browser/qr/<job_id>.png`, phục vụ qua route có kiểm chủ, **không** `url_for` (URL ký là bearer) |
| Route kiểm chủ + phục vụ bytes | `apps/video_crawler/routes.py:210-222` (ảnh bìa: 404 khi không phải của mình, `nosniff`) ; `features.job_cua` `apps/video_crawler/features.py:184-191` | ⚠ `job_cua` ép `app_slug == MANIFEST.slug` ⇒ không tìm được job QR (GAP-5) |
| Poll UI | htmx `every 1500ms` `apps/video_crawler/templates/vc_ket_qua.html:3` | Cùng khuôn cho khung QR |
| Nền nào dùng QR | `cach_dang_nhap="qr"`: douyin `nen_tang.py:93`, bilibili `:109`, xiaohongshu `:118`, rednote `:126`; kuaishou là `"cookie"` `:184` | Kuaishou cần đổi cờ (GAP-7) |
| Spec | `docs/superpowers/specs/2026-09-22-video-crawler-design.md:78-80` (Slice 2 = app anh em, S6), `:150-152` (profile theo owner, không chung) | Thiết kế này là S6 |

Máy: Python hệ thống có `playwright 1.63.0` + Chromium ở `%LOCALAPPDATA%\ms-playwright`; **venv production
`C:\LTTPlatform\venv` KHÔNG có `playwright`** (đo 22/09: `PackageNotFoundError`). `requirements.txt:5` đã có
`qrcode[pil]` (dùng được nếu tự vẽ QR từ URL, §4.2).

## 2. Kiến trúc

```
Trình duyệt khách ──POST /video-crawler/dang-nhap-qr (CSRF)──► video_crawler (web, api)
        │                                                        │ jobs.submit(app_slug="video_crawler_browser",
        │                                                        │   job_type="...dang_nhap_qr", params={nen_tang},
        │                                                        │   max_attempts=1, dedupe_key="qr:<owner>:<nen>")
        │                                                        ▼
        │                                               bảng jobs (queued)
        │                                                        │ claim bởi làn `browser` (LTT_WORKER_POOLS)
        │                                                        ▼
        │                                     video_crawler_browser.handle (worker)
        │                                       1 profile tạm <goc>/vcqr/<job_id>/  (xoá khi ra)
        │                                       2 Chromium headless → trang đăng nhập của nền
        │                                       3 chụp QR → storage.put("video_crawler_browser/qr/<job_id>.png")
        │                                         + event CUSTOMER `qr_san_sang`
        │                                       4 vòng ~1 s: ctx.progress (huỷ?) · QR hết hạn? · cookie xác thực?
        │                                       5 thấy cookie 2 lần liên tiếp → Netscape → phien.luu (mã hoá)
        │                                       6 finally: storage.delete, đóng context, rmtree profile
        │
        ├──GET /video-crawler/dang-nhap-qr/<job_id>       (htmx 1500 ms, kiểm chủ) → trạng thái từ timeline
        └──GET /video-crawler/dang-nhap-qr/<job_id>/anh   (kiểm chủ, no-store) → bytes PNG từ storage
```

Vì sao không chạy trình duyệt trong web request: `video_crawler` cấm (spec `:89`, S6), và luật 8 CLAUDE.md dự án
(việc > vài giây qua hàng đợi job; Cloudflare cắt phản hồi 100 s).

## 3. Luồng chi tiết

### 3.1 Nộp
- Route `POST /dang-nhap-qr` (thuộc `video_crawler`, CSRF như `luu_phien`): nhận `nen_tang`; từ chối nếu nền không
  `cach_dang_nhap == "qr"` hoặc cờ tính năng tắt.
- `owner_id` lấy từ phiên đăng nhập, **không** từ form. Params: `{"nen_tang": id}` — không owner, không cookie.
  Handler lấy chủ từ `Job.user_id` (đọc lại bản ghi job theo `ctx.job_id`), không tin params.
- `dedupe_key = f"qr:{owner}:{nen}"`: bấm lại khi đang có QR dở ⇒ trả job cũ (hợp đồng dedupe `jobs.py:139-150`).
- Hạn mức: tối đa 1 job QR đang chạy / người (dedupe cho cùng nền; thêm kiểm "có job QR nào đang chạy của người
  này" trước khi nộp nền khác) và ≤ 10 lượt / giờ / người (chống lạm dụng §7.2, chống đốt làn).
- **Không thu credit** (DANH_GIA_MVP §3: "nền cần phiên — không phụ phí") ⇒ `jobs.submit`, không `submit_with_credit`.

### 3.2 Worker
1. **Dọn trước**: xoá thư mục `vcqr/*` cũ hơn 30 phút (khuôn `phien.don_tam_cu` `phien.py:110`) — hốt xác của
   worker đã chết.
2. **Profile tạm theo job** `<goc>/vcqr/<job_id>/`. Ưu tiên `browser.new_context()` (không đĩa) — context
   Playwright vốn cô lập cookie/storage với nhau (playwright.dev/python/docs/browser-contexts); chỉ dùng
   `launch_persistent_context(user_data_dir=<profile job>)` nếu một nền cần IndexedDB/Service Worker bền trong lúc
   đăng nhập. Không bao giờ dùng lại profile giữa các job hay các người (spec `:150-152`; donor dùng profile chung
   `W:113-117` — cấm).
3. **Mở trang** đăng nhập (bảng URL theo nền — hành vi donor `D:\Viral\resources\app-src\mo_dang_nhap.py:50-69`:
   douyin/bilibili/xiaohongshu mở trang chủ, kuaishou mở trang chủ vì không có `/login` riêng `:62-65`). Douyin là
   SPA: chờ ~1,8 s sau `domcontentloaded` trước khi đọc DOM (donor `:427-432`).
4. **Chụp QR** — theo thứ tự tin cậy (bảng cấu hình mỗi nền, một chỗ):
   a. bắt phản hồi API sinh QR (`page.on("response")`) lấy URL/nội dung QR ⇒ tự vẽ bằng `qrcode[pil]`
      (sạch, không lộ giao diện nền; hỏng khi nền đổi endpoint);
   b. `locator(<selector QR>).screenshot()` (canvas/img trong hộp đăng nhập);
   c. hết cách ⇒ lỗi `qr_khong_thay` (không chụp cả trang: có thể lộ nội dung khác).
   PNG ≤ 64 KB ⇒ `storage.put("video_crawler_browser/qr/<job_id>.png")` ⇒ event CUSTOMER `qr_san_sang`
   (details: `{"lan": n, "het_han_sau_s": t}` — không URL, không khoá storage).
5. **Vòng chờ** (nhịp 1 s, tổng ≤ 300 s):
   - `ctx.progress(...)` mỗi vòng ⇒ nhịp tim + huỷ (`job_runner.py:110-117`);
   - QR hết hạn (DOM hiện "二维码已失效"/nút làm mới, hoặc API báo hết hạn) ⇒ làm mới trong trang, chụp lại, tăng
     `lan`, tối đa 3 lần ⇒ quá thì `qr_het_han` (kết thúc bình thường, không lỗi hệ thống);
   - đã quét, chờ xác nhận trên điện thoại ⇒ event `qr_da_quet` (một lần);
   - nền đòi xác minh thêm (SMS, slider, "身份验证") ⇒ event `can_xac_minh` rồi dừng: **không** tự giải captcha
     (luật an toàn + ToS); UI gợi ý dùng `cookies.txt`;
   - đọc `context.cookies()`: có đủ một tên trong `NenTang.cookie_dang_nhap` trên đúng tên miền **2 lần liên tiếp**
     (debounce — donor `mo_dang_nhap.py:509-521` từng báo xanh giả khi đọc giữa lúc chuyển trạng thái). Profile
     mới tinh nên không có bẫy "cookie cũ còn sót" của donor (`:191-200`).
6. **Lưu**: cookie jar ⇒ Netscape (lọc tên miền) ⇒ `phien.luu(db, owner_id=job.user_id, nen_tang=nen, cookies_txt=...)`
   trong một phiên DB, commit ⇒ event `dang_nhap_xong` (details: `{"so_cookie": n}`). Lỗi `PhienKhongHopLe` ⇒
   `phien_khong_hop_le` (thông điệp đã bọc `_()`).
7. **`finally`** (mọi nhánh, kể cả `JobCancelled`): `storage.delete(qr)`, `context.close()`, `browser.close()`,
   `shutil.rmtree(profile)`; nếu xoá lỗi (Windows khoá tệp) ⇒ để bước 1 của job sau dọn, log INTERNAL.

### 3.3 Máy trạng thái (khách thấy)

`cho_worker` (queued) → `qr_san_sang` ⇄ (làm mới ≤ 3) → `qr_da_quet` → `dang_nhap_xong` ✔
Nhánh kết thúc: `qr_het_han` · `can_xac_minh` · `qr_khong_thay` · `phien_khong_hop_le` · `da_huy` (job cancelled) ·
`loi` (job error/mồ côi). Route poll suy trạng thái = sự kiện CUSTOMER mới nhất trong `job_events.timeline` +
`Job.status`; ngừng poll (bỏ `hx-trigger`) khi ở trạng thái kết thúc.

`cho_worker` quá 60 s ⇒ UI nói thật "máy đăng nhập đang bận/chưa bật", kèm nút huỷ — không quay vô hạn (đây chính
là ca làn `browser` vắng mặt, `job_worker.py:59-81`).

### 3.4 Route (thuộc `video_crawler`)
- `GET /dang-nhap-qr/{job_id}`: job phải `user_id == owner` **và** `app_slug == "video_crawler_browser"` và
  `job_type == ...dang_nhap_qr`; sai ⇒ 404 (khuôn `features.job_cua` — cần mở rộng, GAP-5).
- `GET /dang-nhap-qr/{job_id}/anh`: như trên + job còn chạy; đọc `storage.open(khoá)`; header
  `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`. Không trả URL storage cho trình duyệt.
- `POST /dang-nhap-qr/{job_id}/huy` (CSRF): `jobs.cancel`.

## 4. Nhiều khách song song, dọn dẹp, hỏng hóc

| Tình huống | Cách xử |
|---|---|
| N khách cùng lúc | Mỗi job một context + profile riêng; song song tối đa = số tiến trình làn `browser`. Thừa ⇒ `queued`, UI hiện `cho_worker` |
| Khách đóng tab | Job tự hết sau ≤ 300 s chờ; không tốn gì ngoài slot |
| Khách bấm lại | dedupe trả job cũ; muốn QR mới ⇒ huỷ rồi nộp |
| Worker chết giữa chừng | `reclaim_orphans` ≤ 5 phút ⇒ `max_attempts=1` ⇒ lỗi; profile + ảnh QR mồ côi ⇒ dọn bởi (a) bước 1 của job QR kế tiếp, (b) quét storage `video_crawler_browser/qr/` theo tuổi > 30 phút trong cùng bước |
| Chromium mồ côi khi worker bị kill | Windows không tự giết cây con. Bước 1 kill tiến trình `chrome.exe` có dòng lệnh chứa `<goc>/vcqr/` **và** thư mục job đã quá tuổi (khuôn donor `_kill_profile_holders` `mo_dang_nhap.py:339`). Chỉ giết tiến trình của mình (luật máy chung) |
| Khoá `secretbox` xoay | `phien.hop_le` (`phien.py:100-107`) đã báo "phiên hỏng" — không đổi |
| Deploy giữa lúc chờ | worker dừng ⇒ job mồ côi ⇒ lỗi; khách bấm lại. Chấp nhận |

## 5. Chi phí vận hành (máy A)

- **RAM/CPU**: mỗi Chromium headless ~200–400 MB, CPU cao ~2–5 s lúc tải trang rồi gần 0 khi chờ (ước lượng, chưa
  đo — đo trong smoke T0). `browser:2` ⇒ ≤ ~1 GB, < 1 lõi trung bình; không đụng ngân sách 14/20 lõi.
- **Slot bị giữ bởi người**: một job chiếm slot tới 5 phút chủ yếu để chờ người quét ⇒ đó là lý do **phải** là làn
  riêng: đặt vào làn `api` sẽ làm job tải/khám phá xếp hàng sau người chưa quét.
- **Đĩa**: Chromium đã có trong `%LOCALAPPDATA%\ms-playwright` của tài khoản người dùng; dịch vụ nssm chạy dưới tài
  khoản khác ⇒ cần `PLAYWRIGHT_BROWSERS_PATH` trỏ thư mục chung đọc được (donor gặp đúng lỗi "Executable doesn't
  exist" khi thiếu biến này, `mo_dang_nhap.py:31-43`). ~150–200 MB/bản Chromium.
- **Phụ thuộc**: thêm `playwright` (Apache-2.0) vào `requirements-server.txt` + bước `playwright install chromium`
  trong `setup/2-cai-dat.ps1` (tệp dùng chung ⇒ điều phối).
- **IP**: máy A là IP datacenter/ISP VN; `registry.py:573` định nghĩa `browser` = "trình duyệt + IP dân dụng" —
  máy A **không** thoả nghĩa đó (GAP-1). Nền TQ có thể chặn/đòi xác minh với IP ngoài TQ.
- **Công sửa**: selector QR/endpoint đổi theo đợt phát hành của nền — chi phí cố định cùng lớp N8 (DANH_GIA_MVP).

## 6. Cookie dùng được sau khi có

- Phiên sinh ra trên máy A, dùng lại bởi yt-dlp **trên chính máy A** ⇒ cùng IP xuất — đúng nguyên tắc "không ghép lại
  các phần" (jar không bao giờ đổi proxy/User-Agent) mà Douyin_TikTok_Download_API ghi ở
  `documents/en/17-faq.md` (commit `9fa3e540`, bảng "Never recombining the parts").
- ⚠ **User-Agent**: jar đăng nhập bằng UA của Chromium Playwright nhưng yt-dlp gửi UA khác ⇒ tín hiệu rủi ro. Cần
  lưu UA cùng phiên và cho adapter dùng lại ⇒ cột mới ở `VcPhien` (GAP-6).
- XHS: donor coi đăng nhập web XHS = `web_session` (+ `id_token` ở rednote) (`mo_dang_nhap.py:90`); LTT khai
  xiaohongshu `cookie_dang_nhap=('id_token',)` (`nen_tang.py:121`). Nếu QR XHS nội địa chỉ sinh `web_session`,
  `phien._loc` sẽ từ chối phiên đúng ⇒ **đo trong smoke T0 rồi sửa `nen_tang.py`** (GAP-8).

## 7. Rủi ro

### 7.1 Bảng rủi ro

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | Nền phát hiện đăng nhập từ thiết bị/IP lạ ⇒ đá cả phiên app + web của khách (f2 FAQ, §8.1) | Cao | Cảnh báo trước khi hiện QR; khuyên tài khoản phụ (khuôn DTDA FAQ); `cookies.txt` vẫn là đường chính |
| R2 | Nền đòi SMS/slider sau quét ⇒ QR vô dụng từ IP máy A | Cao (Douyin) | `can_xac_minh` + gợi ý `cookies.txt`; đo tỉ lệ ở T0 trước khi mở cho khách |
| R3 | QRLJacking: kẻ xấu mở QR trên LTT rồi dụ nạn nhân quét ⇒ LTT lưu phiên nạn nhân vào tài khoản kẻ xấu (OWASP "QRLJacking") | Cao (pháp lý, uy tín) | Chỉ hiện QR trong trang chủ job (route kiểm chủ, no-store, không URL chia sẻ); hạn mức 10/giờ/người; nhật ký (owner, nền, lúc, IP web) cho quy trình gỡ 72 h (N3); điều khoản cấm; hiển thị tên tài khoản nền đã đăng nhập để khách xác nhận (nếu đọc được) |
| R4 | Ảnh QR lộ ⇒ người khác quét và cài tài khoản CỦA HỌ vào phiên của khách (đăng nhập chéo) | TB | Như R3; xoá ảnh ngay khi xong; khoá storage theo `job_id` (UUID) |
| R5 | Slot `browser` cạn khi đông | TB | Hạn mức 1 job/người; UI `cho_worker` trung thực; tăng N theo đo |
| R6 | Chromium/Playwright mồ côi ăn RAM máy production | TB | §4 dọn theo tuổi; trần runtime 420 s |
| R7 | Selector/endpoint QR đổi | Cao (thường xuyên) | Cấu hình một bảng/nền; `qr_khong_thay` có mã riêng ⇒ đếm được trên bảng sức khoẻ (N8) |
| R8 | ToS: tự động hoá đăng nhập | TB | Người thật quét, không tự nhập mật khẩu/giải captcha; chủ dự án đã chấp nhận rủi ro ToS N9/N10 (22/09) |

### 7.2 Điều thiết kế KHÔNG làm
Không nhập mật khẩu/số điện thoại hộ khách; không giải captcha; không giữ trình duyệt sống sau đăng nhập; không
dùng profile chung; không trả cookie cho trình duyệt khách.

## 8. Nghiên cứu cộng đồng

### 8.1 f2 (Johnserf-Seed/f2, Apache-2.0)
- Thêm `--sso-login` "dùng quét mã lấy cookie" cho Douyin ở `0.0.1-pw.1` (01/01/2024, `CHANGELOG.md:582`), rồi
  **bỏ** "douyin SSO quét mã" ở `0.0.1.6` (04/05/2024, `CHANGELOG.md:298`) và thêm cảnh báo bỏ ở `0.0.1.7`
  (`:167`).
- Lý do do tác giả ghi (`docs/en/faq.md`, commit `7dab3e2f`): cookie từ QR có thể mất hiệu lực vì kiểm soát rủi ro
  môi trường thiết bị, làm tài khoản bị đăng xuất ở cả web và app; khuyên `--auto-cookie` (đọc cookie từ trình
  duyệt đã đăng nhập trên máy người dùng) hoặc chép tay. Cũng ghi cookie Douyin web đầy đủ > 60 khoá — jar ngắn là
  dấu hiệu hỏng.
- ⇒ Bằng chứng mạnh nhất cho R1/R2. f2 là công cụ chạy trên máy **người dùng** (IP dân dụng) mà vẫn bỏ; máy A còn
  bất lợi hơn.

### 8.2 Douyin_TikTok_Download_API (Evil0ctal, Apache-2.0, commit `9fa3e540`)
- `documents/en/17-faq.md`: bản mới **không đăng nhập**: duy trì kho "danh tính khách" do trình duyệt headless tự đúc
  qua proxy (chỉ bắt buộc `ttwid`). Cookie đăng nhập chỉ cần cho nội dung bị chặn sau đăng nhập, và phải nhập tay,
  ghim theo danh tính.
- Kỷ luật đáng chép (ý tưởng, không mã): 1 request đang bay / danh tính; token bucket theo (danh tính, endpoint);
  cooldown 60 s nhân đôi, trần 6 giờ khi bị kiểm soát rủi ro; không đổi proxy/UA của một jar; cầu dao theo endpoint.
  Cảnh báo "jar đăng nhập tương đương mật khẩu — dùng tài khoản riêng cho việc này".
- ⇒ Gợi ý kiến trúc thay thế (§9 Q-QR4): với tìm kiếm/khám phá Douyin, danh tính **khách** có thể đủ, và
  không cần QR.

### 8.3 Playwright
- Context cô lập nhau (cookie, storage) trong cùng một browser — playwright.dev/python/docs/browser-contexts;
  `launch_persistent_context` gắn một `user_data_dir` và không được hai tiến trình dùng chung một thư mục
  (playwright.dev/python/docs/api/class-browsertype) ⇒ mỗi job một thư mục là bắt buộc nếu dùng persistent.
- `context.cookies()` / `storage_state()` đọc jar mà không cần đĩa — playwright.dev/python/docs/auth.

MediaCrawler **không** được đọc (NON-COMMERCIAL) — theo brief.

## 9. CONTRACT GAP và quyết định cần chủ dự án

### 9.1 CONTRACT GAP (8 mục)

| # | Khoảng trống | Nơi | Đề xuất |
|---|---|---|---|
| GAP-1 | `browser` được định nghĩa là "trình duyệt + **IP dân dụng**" (`registry.py:573`) nhưng làn sẽ chạy ở máy A (IP không dân dụng) | `platform_core/registry.py` (không sửa trong làn) | Chủ dự án chấp nhận nghĩa rộng "cần trình duyệt" hoặc tạo năng lực mới `browser_dc` — **không** đổi `platform_core` trong đợt này; ghi nhận ở manifest |
| GAP-2 | Production chưa có làn `browser` (`GUI_DOI_SOAT_VA_PLAN_V2.md:306`) ⇒ app vô hình | `app.env` production | Thêm `browser:2` vào `LTT_WORKER_POOLS` khi deploy; `setup/4-nghiem-thu.ps1` chỉ kiểm `voice` (`ARCHITECTURE_MAP.md:174`) ⇒ nên kiểm `app_vo_hinh == []`. ⚠ `ARCHITECTURE_MAP.md:174` lại ghi "production không đặt pool" — hai tài liệu lệch; xác minh bằng log worker trước deploy |
| GAP-3 | venv production thiếu `playwright` + Chromium, thiếu `PLAYWRIGHT_BROWSERS_PATH` cho tài khoản dịch vụ | `requirements-server.txt`, `setup/2-cai-dat.ps1` | Điều phối thêm phụ thuộc + bước cài |
| GAP-4 | Không có quét dọn định kỳ cho tài nguyên tạm của app runtime (profile, ảnh QR) | nền tảng | Dọn trong job kế tiếp (§4) — đủ cho MVP; không cần hook nền tảng |
| GAP-5 | `features.job_cua` khoá cứng `app_slug == MANIFEST.slug` (`features.py:187`) | `apps/video_crawler/features.py` (làn khác) | Thêm tham số `app_slug` hoặc hàm `job_qr_cua` |
| GAP-6 | `VcPhien` không lưu User-Agent của phiên | `apps/video_crawler/tables.py` + migration | Cột `ua` (nullable); adapter truyền cho yt-dlp khi có |
| GAP-7 | Kuaishou khai `cach_dang_nhap="cookie"`, `bat=False` (`nen_tang.py:182-184`) | `apps/video_crawler/nen_tang.py` | Đổi `"qr"` khi bật Kuaishou |
| GAP-8 | XHS `cookie_dang_nhap=('id_token',)` có thể sai với đăng nhập web nội địa (donor dùng `web_session`) | `apps/video_crawler/nen_tang.py:121` | Đo ở T0, sửa theo đo |

### 9.2 Câu hỏi cho chủ dự án

| # | Câu hỏi | Đề xuất của L5 |
|---|---|---|
| Q-QR1 | Bật làn `browser` trên máy A? | Có, sau khi T0 (smoke) cho thấy ≥ 1 nền đăng nhập được từ máy A không cần xác minh thêm |
| Q-QR2 | Số tiến trình làn | `browser:2` (≤ ~1 GB RAM); tăng theo đo hàng chờ |
| Q-QR3 | Nền nào mở QR trước | Bilibili (thường ít đòi xác minh nhất — cần đo) → XHS → Douyin → Kuaishou; mỗi nền một cờ, tắt được |
| Q-QR4 | Có đi đường "danh tính khách" (DTDA §8.2) cho khám phá Douyin thay vì bắt khách đăng nhập? | Tách thành việc riêng; giảm nhu cầu QR |
| Q-QR5 | Chấp nhận R3 (QRLJacking) với các giảm thiểu §7.1 và điều khoản cấm? | Cần chủ dự án chốt — đây là rủi ro pháp lý, không phải kỹ thuật |
| Q-QR6 | Tạo app thư mục thứ hai `apps/video_crawler_browser/` (luật 9: "thêm app = MỘT thư mục") | Có — tiền lệ ASV, spec `:78-80` đã nêu |

## 10. Kế hoạch TDD cho đợt sau

Thứ tự; mỗi bước test đỏ trước. Test không mở trình duyệt thật: tiêm một `TrinhDuyetGia` (giao thức nhỏ: `mo(url)`,
`chup_qr() -> bytes|None`, `trang_thai() -> "cho"|"da_quet"|"het_han"|"can_xac_minh"`, `cookies() -> list[dict]`,
`dong()`), đồng hồ giả, storage giả (`storage.set_storage`, `platform_core/storage.py:525`).

| # | Tệp mới/sửa | Test (tên gợi ý) | Nội dung |
|---|---|---|---|
| T0 | (ngoài bộ test, thư mục tạm) | smoke tay | Mở trang đăng nhập 4 nền từ máy A, chụp QR, **không quét**; ghi: chụp được không, thời hạn QR, có captcha trước QR không. Tuỳ chủ dự án: một lượt quét bằng tài khoản phụ **do chủ dự án tự quét** ⇒ đo R2 + GAP-8 |
| T1 | `apps/video_crawler_browser/manifest.py` | `test_manifest_runtime_anh_em` | `requires==("browser",)`, `surface="runtime"`, `catalog_parent="video_crawler"`, `public=False`, `max_runtime_s` 420 cho `dang_nhap_qr`; `jobs._app_hop_nang_luc({"api"})` không chứa app; `{"api","browser"}` có |
| T2 | `apps/video_crawler_browser/cookie_jar.py` | `test_jar_sang_netscape` | cookie Playwright (domain, path, secure, expires −1/số, httpOnly) ⇒ dòng Netscape 7 cột, `#HttpOnly_`; qua được `phien._loc`; loại tên miền lạ |
| T3 | `.../cau_hinh_nen.py` | `test_bang_nen_qr_khop_nen_tang` | mỗi nền `cach_dang_nhap=="qr"` có URL + chiến lược chụp; không nền thừa |
| T4 | `.../dang_nhap_qr.py` (vòng chờ) | `test_debounce_hai_lan`, `test_het_han_lam_moi_toi_da_3`, `test_can_xac_minh_dung`, `test_huy_giua_chung_ra_finally` | máy trạng thái §3.3 với `TrinhDuyetGia`; event đúng mã; `JobCancelled` vẫn xoá ảnh + profile |
| T5 | cùng tệp | `test_luu_phien_ma_hoa_khong_lo_cookie` | thành công ⇒ `VcPhien` có bản ghi đúng owner (từ `Job.user_id`, không params); cookie không có trong event/result/log (quét chuỗi giả) |
| T6 | cùng tệp | `test_don_profile_va_qr_mo_coi` | thư mục/khoá storage quá 30 phút bị xoá; mới hơn thì giữ; chỉ dưới gốc `vcqr/` |
| T7 | `apps/video_crawler/routes.py` + `features.py` (làn sở hữu) | `test_qr_route_kiem_chu`, `test_qr_anh_no_store`, `test_qr_nop_dedupe_va_han_muc` | người khác ⇒ 404; header `no-store`/`nosniff`; bấm lại trả job cũ; quá 10/giờ ⇒ 429; nền không QR ⇒ 400; CSRF |
| T8 | template `vc_dang_nhap_qr.html` | `test_qr_template_ngung_poll_khi_ket_thuc` + i18n | không `hx-trigger` ở trạng thái kết thúc; chuỗi bọc `_()` (`tools/check_i18n.py`) |
| T9 | `nen_tang.py` | theo T0 | GAP-7/GAP-8 |
| T10 | tích hợp tay trên `https://app.lttstudios.com` (luật 7) | Playwright | sau deploy với `browser:2`: nộp, thấy QR, huỷ, hết hạn; console/network sạch |

Điều phối cần (ngoài L5): `requirements-server.txt` (+`playwright`), `setup/2-cai-dat.ps1` (cài Chromium +
`PLAYWRIGHT_BROWSERS_PATH`), `app.env` production (`browser:2`), `features.py`/`routes.py`/`tables.py`/`nen_tang.py`
của `video_crawler` (GAP-5..8), `.po` cho msgid mới.
