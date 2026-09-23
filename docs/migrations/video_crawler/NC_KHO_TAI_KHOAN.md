# Nghiên cứu: kho tài khoản hệ thống cho video_crawler (Douyin/XHS/Bilibili/TikTok/Instagram/Kuaishou)

Chỉ đọc. Nguồn code chỉ dùng MIT/Apache-2.0/BSD/Unlicense; nguồn GPL/AGPL (gallery-dl,
seiuna/bilibili-api, Nemo2011/bilibili-api) và MediaCrawler (NON-COMMERCIAL) chỉ trích
từ README/docs, không đọc mã. "Chưa có nguồn" = không tìm được, không suy đoán.

## 0. Rủi ro pháp lý cần biết trước (mới nhất)

- **Nemo2011/bilibili-api** (GPL-3.0) và **SocialSisterYi/bilibili-API-collect** (tài
  liệu, không rõ license) đã **ngừng bảo trì và đóng kho vĩnh viễn** sau thư cảnh cáo
  pháp lý từ luật sư đại diện Bilibili (SocialSisterYi: 28/01/2026; Nemo2011: thư ngày
  06/07/2026), cáo buộc thu thập/phổ biến kỹ thuật vượt xác thực, bỏ qua chống-bot, và
  cào nội dung trả phí là xâm phạm quyền + cạnh tranh không lành mạnh theo luật Trung
  Quốc. Nguồn: README hiện tại của hai kho (đọc trực tiếp qua GitHub MCP, 23/09/2026).
  → Tài liệu API Bilibili vẫn tồn tại qua fork `pskdje/bilibili-API-collect` và bản
  GitHub Pages (`socialsisteryi.github.io/bilibili-API-collect`), nhưng bản gốc đã gỡ.
- Ý nghĩa cho LTTSTUDIOSAPP: rủi ro pháp lý của việc vận hành pool cookie Bilibili ở quy
  mô SaaS thương mại là **thật, đã xảy ra với nhiều kho lớn**, không phải giả định.

## 1. Bảng theo nền

| Nền | Cách lấy cookie khuyến nghị | Cookie xác thực chính | Endpoint kiểm phiên sống | Hạn sống điển hình | Làm mới tự động | Ngưỡng/khoá tài khoản cộng đồng báo |
|---|---|---|---|---|---|---|
| **Bilibili** | (a) QR login chính chủ `passport.bilibili.com/x/passport-login/web/qrcode/generate` → poll; (b) xuất cookie trình duyệt sau đăng nhập tay | `SESSDATA`, `bili_jct` (CSRF), `DedeUserID`, `DedeUserID__ckMd5`, `sid` | `GET api.bilibili.com/x/web-interface/nav` — trả `isLogin`; không đăng nhập → code `-101` "账号未登录" | Vài ngày đến ~1 tháng theo báo cộng đồng (không có số chính thức) | **Có** — cơ chế `refresh_token`/`cookie_refresh`: lấy `CorrespondPath` từ timestamp hiện tại → gọi `https://www.bilibili.com/correspond/1/{correspondPath}` lấy `refresh_csrf` (SSR trong HTML) → gọi API refresh xác nhận → cấp `SESSDATA`/`refresh_token` mới. Nguồn: `SocialSisterYi/bilibili-API-collect/docs/login/cookie_refresh.md` (qua fork `pskdje/bilibili-API-collect`, và bản GitHub Pages) | Không có số ngưỡng công khai; risk thực tế lớn nhất là **pháp lý** (mục 0), không phải rate-limit kỹ thuật |
| **Douyin** | QR login riêng của Douyin (`sso.douyin.com/get_qrcode` cũ hay lỗi trả HTML → cộng đồng chuyển sang `www.douyin.com/passport/web`) hoặc xuất cookie trình duyệt (`browser_cookie3`, f2 dùng `get_cookie_from_browser(browser, "douyin.com")`) | Cookie đăng nhập đầy đủ (không có 1 field đơn lẻ công khai xác nhận); f2 yêu cầu `cookie` không rỗng, cảnh báo "dùng cookie chưa đăng nhập sẽ không tải ổn định lâu dài" | Không thấy endpoint "nav" nhẹ tương đương Bilibili trong f2/Evil0ctal (repo chỉ raise lỗi khi response trống/parse lỗi, không có lệnh check riêng) — **chưa có nguồn** cho endpoint kiểm phiên chuyên dụng | Chưa có nguồn số cụ thể | Chưa có nguồn (không thấy cơ chế refresh_token như Bilibili trong f2/Evil0ctal) | Evil0ctal issue #195 "Cookie失效了" (cookie hết hạn) và #495 (response rỗng dù cookie "bình thường") — cookie Douyin/TikTok âm thầm hết hạn/bị risk-control chặn mà không báo lỗi rõ ràng |
| **TikTok** | Xuất cookie trình duyệt (`--auto-cookie edge/chrome`, f2 `f2/apps/tiktok/cli.py`) — cần cookie đã đăng nhập, kèm `msToken`, `device_id`, `X-Bogus`/`ttwid` sinh kèm | Cookie đăng nhập TikTok web (`sessionid`, `ttwid`, …, không thấy field đơn lẻ được xác nhận công khai trong 2 repo) | Chưa có nguồn (không thấy endpoint kiểm phiên nhẹ riêng) | Chưa có nguồn | Chưa có nguồn | yt-dlp wiki + issue #15724: dùng cookie tài khoản cho tool tải tự động **có rủi ro bị khoá tài khoản** (tạm thời hoặc vĩnh viễn); khuyến nghị chính thức là dùng **tài khoản phụ riêng cho việc này**, không dùng tài khoản chính; một số báo cáo "cookie thay thế" (cookie exchange) dẫn tới khoá tài khoản |
| **Xiaohongshu (XHS)** | (a) QR login chính chủ: `POST edith.xiaohongshu.com/api/sns/web/v1/login/qrcode/create` (`{"qr_type":1}`) → `GET .../qrcode/status?qr_id=&code=` để chờ xác nhận trên app; (b) Playwright lấy `a1` khi mở `xiaohongshu.com` (`ReaJason/xhs`) | `a1` (device/browser fingerprint cookie, dùng để ký request) + `web_session` (cookie phiên đăng nhập) | Chưa có nguồn cho endpoint "nav"/kiểm phiên nhẹ riêng của XHS trong `ReaJason/xhs` | Chưa có nguồn | Chưa có nguồn | `ReaJason/xhs` issue #47 "多账法体系" (đa tài khoản): hạn chế kỹ thuật — service ký request (`basic_sign_server.py`, dùng Playwright) chỉ khởi tạo được **một** trình duyệt toàn cục, nên nhiều tài khoản dùng chung 1 service ký phải giữ cùng field `a1` để tránh lỗi ký; issue #66 "发布接口报错：无登录信息" (thiếu thông tin đăng nhập) cho thấy cookie/`web_session` hết hiệu lực gây lỗi khi gọi API ghi (đăng bài) |
| **Instagram** | (a) `instaloader --load-cookies` / import cookie từ Firefox (`docs/codesnippets/615_import_firefox_session.py`, MIT) hoặc EditThisCookie; (b) `instagrapi` (MIT) — login 1 lần rồi `cl.dump_settings("session.json")`, các lần sau `cl.load_settings(...)` để tái dùng **cả cookie + device fingerprint + header** | instaloader: cookie phiên trình duyệt (sessionid…); instagrapi: session blob JSON (cookies + device id + headers), không phải "1 cookie" đơn lẻ | instagrapi: không có endpoint "check nhẹ" riêng — lỗi lộ qua exception `LoginRequired` khi gọi API thật | Chưa có nguồn số cụ thể | **Có, theo kiểu khác** — instagrapi không "refresh cookie" mà **tái sử dụng session đã lưu** (device + cookie) qua `dump_settings`/`load_settings`, tránh đăng nhập lại bằng mật khẩu mỗi lần (đăng nhập lại từ đầu dễ bị hệ thống Instagram coi là thiết bị mới → dính `challenge_required`) | `ChallengeRequired` (checkpoint mềm, cần mã SMS/email) và `CheckpointRequired` (checkpoint cứng, chỉ chủ tài khoản gỡ được) — instagrapi docs khuyến nghị: **1 proxy/IP cố định cho mỗi tài khoản** (không đổi IP giữa các lần), giữ nguyên session/device fingerprint, tránh đăng nhập lại bằng mật khẩu liên tục |
| **Kuaishou** | Xuất cookie trình duyệt qua `browser_cookie3` nhắm domain `.kuaishou.com` (cộng đồng, ví dụ bài Aliyun developer) | `did` (device id), `kuaishou.server.web_ph`, và với app: `kuaishou.api_st` | Chưa có nguồn cho endpoint kiểm phiên nhẹ chính thức | Chưa có nguồn | Chưa có nguồn | Cộng đồng (CSDN, `oGsLP/kuaishou-crawler` issue #7) nhấn mạnh: **mỗi thiết bị/tài khoản phải dùng `did` riêng biệt**, dùng chung `did` giữa nhiều tài khoản dễ bị soi là bất thường; request cần đi kèm `did`, `didv`, `kpf`, `clientid`, `kpn` nhất quán |

## 2. Mẫu vận hành pool tài khoản/cookie từ cộng đồng

- **Kiến trúc 3 tiến trình độc lập (Python3WebSpider/CookiesPool, README — không thấy
  file LICENSE, coi là "chưa rõ license", chỉ tham khảo mô hình không copy code):**
  Generator (đăng nhập tự động, sinh cookie mới) + Validator (vòng lặp `CYCLE` giây,
  gọi `TEST_URL_MAP` mỗi nền, cookie chết thì xoá khỏi Redis) + API server (client mượn
  cookie qua REST). Tài khoản nạp qua `importer.py` (danh sách user/pass), pool lưu
  trong Redis. Đây đúng hình dạng "kho tài khoản hệ thống, job mượn" mà chủ dự án muốn.
- **Rotation/scoring (jhao104/proxy_pool, MIT — mô hình proxy nhưng áp dụng được cho
  account pool):** mỗi mục có điểm; kiểm tra định kỳ **cộng điểm khi thành công, trừ
  điểm khi thất bại**, chỉ loại khỏi pool khi điểm dưới ngưỡng — tránh xoá nhầm tài
  khoản chỉ vì một lần lỗi mạng thoáng qua (khác với xoá ngay khi thất bại 1 lần).
  Nguồn: kết quả tổng hợp WebSearch từ tài liệu proxy-pool 2025/2026 (chưa xác minh
  từng dòng code cụ thể trong repo — ghi nhận ở mức nguyên lý).
- **Cooldown/rotation kiểu round-robin + "tuổi nghỉ hưu" (retirement age):** nguồn
  chung mô hình proxy pool — mỗi mục có tuổi tối đa trước khi bị đưa ra khỏi pool và
  thay bằng mục mới, kết hợp round-robin để chia đều lượt dùng — áp dụng tương tự cho
  cooldown giữa các lượt mượn của một tài khoản.
- **instagrapi (MIT) — khoá theo tài khoản, không khoá theo pool chung:** best-practice
  docs khuyến nghị **1 proxy/IP cố định/tài khoản**, tránh 2 tiến trình cùng ghi
  `session.json` của cùng 1 tài khoản (race condition → cookie/fingerprint lệch nhau →
  bị buộc đăng nhập lại → dễ dính challenge). Gợi ý: dùng Redis, khoá theo từng
  tài khoản (per-account lock) khi đọc/ghi session.
- **Đa tài khoản dùng chung service ký (ReaJason/xhs, MIT):** khi nhiều tài khoản XHS
  cùng dùng 1 sign-server (Playwright chỉ khởi tạo 1 lần), phải giữ cookie `a1` nhất
  quán giữa các tài khoản dùng chung service đó — nếu không sẽ lỗi ký request. Gợi ý
  cho kiến trúc: có thể cần **N service ký riêng** (N context Playwright) nếu muốn N
  tài khoản độc lập hoàn toàn về fingerprint.
- **f2 (Apache-2.0) — cách lấy cookie thực dụng, đa nền:** hàm chung
  `f2/utils/utils.py::get_cookie_from_browser(browser_choice, domain)` dùng để tự động
  rút cookie đã đăng nhập từ trình duyệt cho Douyin/TikTok/Twitter/Weibo (CLI cờ
  `--auto-cookie edge|chrome|...`), thay cho việc dán tay cookie — đúng mô hình
  "xuất cookie từ trình duyệt" mà câu hỏi (2) đề cập.

## 3. Cách lấy cookie — tổng hợp theo phương thức (không lặp lại bảng trên)

1. **QR login chính chủ của nền tảng** — tốt nhất về độ "sạch"/giống người dùng thật:
   - Bilibili: `passport.bilibili.com/x/passport-login/web/qrcode/{generate,poll}`.
   - XHS: `edith.xiaohongshu.com/api/sns/web/v1/login/qrcode/{create,status}`.
   - Douyin: không ổn định — endpoint `sso.douyin.com/get_qrcode` từng đổi hành vi trả
     HTML thay vì JSON; cộng đồng (PR `incubator4/dynamic-bot-tiktok`) phải chuyển sang
     `www.douyin.com/passport/web` và coi phản hồi HTML là dấu hiệu bị chặn.
2. **Xuất cookie từ trình duyệt (browser_cookie3 / EditThisCookie / Get cookies.txt
   LOCALLY)** — nhanh, dùng được ngay cho mọi nền có cookie web, nhưng cookie gắn với
   phiên trình duyệt của máy admin, không có device fingerprint riêng cho pool.
3. **Playwright `storage_state()`** — không thấy trong 2 repo Apache/MIT đã đọc mã
   (f2 dùng `browser_cookie3`, không dùng Playwright để lấy cookie); ReaJason/xhs dùng
   Playwright nhưng để **ký request** (`a1`/`x-s`), không phải để export storage_state
   làm cookie pool — **chưa có nguồn** trực tiếp cho "Playwright storage_state làm kho
   cookie" trong các repo đã đọc; đây là kỹ thuật Playwright chuẩn (biết từ kiến thức
   nền, không có trích dẫn repo cụ thể — cần tự xác minh nếu áp dụng).
4. **API private/instagrapi kiểu "device session"** — không phải cookie thuần mà là
   trọn bộ (cookie + device id + header) lưu 1 file JSON, tái dùng liên tục.

## 4. Rủi ro tổng hợp

- **Pháp lý (cao nhất, đã có tiền lệ thật):** hai kho lớn nhất về Bilibili API
  (Nemo2011/bilibili-api, SocialSisterYi/bilibili-API-collect) bị luật sư của Bilibili
  gửi thư cảnh cáo và đóng kho 2026. Vận hành pool tài khoản Bilibili ở quy mô SaaS thu
  tiền là rủi ro pháp lý thật, không chỉ rủi ro kỹ thuật.
- **Khoá tài khoản khi dùng cho tool tải tự động:** yt-dlp wiki + issue #15724 khuyến
  nghị dùng tài khoản phụ, không dùng tài khoản chính, vì cookie dùng cho downloader dễ
  bị nền tảng gắn cờ và khoá (tạm thời hoặc vĩnh viễn).
- **Cookie/API "im lặng hỏng"**: Douyin/TikTok (Evil0ctal issue #195, #495) cho thấy
  cookie hết hạn hoặc bị risk-control không trả lỗi rõ ràng mà trả response rỗng — hệ
  thống giám sát pool cần coi "response rỗng lặp lại" là dấu hiệu tài khoản chết, không
  chỉ dựa vào status code.
- **Checkpoint/challenge Instagram**: đăng nhập lại từ đầu (thay vì tái dùng session đã
  lưu) làm tăng khả năng bị coi là thiết bị mới → dính challenge/checkpoint; đổi IP
  giữa các lần dùng cùng 1 tài khoản cũng làm tăng rủi ro này.
- **Chia sẻ fingerprint giữa nhiều tài khoản (XHS `a1`, Kuaishou `did`)**: nếu kiến
  trúc dùng chung 1 service ký/1 device id cho nhiều tài khoản phụ, một số nền tảng có
  thể coi đó là dấu hiệu bất thường (nhiều tài khoản cùng 1 "thiết bị") — nên cấp
  fingerprint riêng theo từng tài khoản nếu có thể.
- **Không tìm được endpoint kiểm phiên nhẹ ("nav"-style) cho Douyin/TikTok/XHS/Kuaishou**
  trong các repo đã đọc — chỉ Bilibili có endpoint `nav` xác nhận rõ trong tài liệu còn
  sống (qua fork). Với các nền khác, việc "còn sống" thường được suy ra gián tiếp từ
  một lệnh gọi API thực tế thất bại/thành công, không có endpoint nhẹ chuyên dụng đã
  xác nhận.

## Nguồn đã dùng (giấy phép)

| Nguồn | Giấy phép | Vai trò |
|---|---|---|
| github.com/Johnserf-Seed/f2 | Apache-2.0 | đọc mã (get_cookie_from_browser, --auto-cookie) |
| github.com/Evil0ctal/Douyin_TikTok_Download_API | Apache-2.0 | đọc issue (#195, #495) |
| github.com/ReaJason/xhs | MIT | đọc issue (#47, #66), doc sign server |
| github.com/instaloader/instaloader | MIT | đọc doc/code snippet import Firefox session |
| github.com/subzeroid/instagrapi | MIT | đọc LICENSE + docs (challenge, session, best practices) |
| github.com/jhao104/proxy_pool | MIT | mô hình scoring (đọc README/doc qua WebSearch, không đọc sâu mã) |
| github.com/Python3WebSpider/CookiesPool | không thấy LICENSE trong repo | mô hình generator/validator/API, mua account (chỉ đọc README) |
| github.com/Nemo2011/bilibili-api | GPL-3.0 (thực tế: README hiện là thông báo đóng kho) | chỉ đọc README (thông báo pháp lý) |
| github.com/SocialSisterYi/bilibili-API-collect | không rõ license, kho gốc đã rút | chỉ đọc README (thông báo đóng kho) + nội dung qua fork/GitHub Pages cho cookie_refresh, QR login |
| github.com/seiuna/bilibili-api | GPL-3.0 | chỉ đọc LICENSE, không đọc mã |
| github.com/NanmiCoder/MediaCrawler | NON-COMMERCIAL LEARNING LICENSE 1.1 | chỉ đọc LICENSE, không đọc mã (theo đúng giới hạn được giao) |
| yt-dlp wiki + issue #15724 | (dự án yt-dlp, Unlicense) | WebSearch, không đọc mã |
| gallery-dl (mikf/gallery-dl) | GPL-2.0 | chỉ đọc LICENSE + docs cookie qua WebSearch, không đọc mã |
