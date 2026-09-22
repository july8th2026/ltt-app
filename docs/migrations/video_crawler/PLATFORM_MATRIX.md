# Ma trận nền tảng — ViralCrawl "Cào ngay" (donor SHA 368f8be)

Viết tắt: `W` = `web_app.py`, `H` = `web\index.html`, `Y` = `tai_ytdlp.py`, `HG` = `tai_honggo.py`, `MC` = `MediaCrawler\` (thư mục gốc `D:\Viral\resources\app-src\`).

Các nguồn dùng chung cho mọi dòng trong bảng:
- Danh sách nền: `NEN_TANG` `W:1090-1114`; `NEN_TANG_HO_TRO` `W:1120`.
- Ẩn/hiện trên lưới: CSS `H:242`.
- Luật ẩn chế độ theo nền: `capNhatNenTang` `H:15573-15612`.
- Xem trước: `_tim_anh_worker` `W:5518-5529`; `tim_anh.DATA_FOLDER` `tim_anh.py:35`.
- Luật bỏ qua kiểm đăng nhập: `_boQuaLogin` `H:9873`.
- Tên cookie auth: `COOKIE_AUTH` `W:17772`.
- Thẻ đăng nhập: `NEN_TANG_LOGIN` `W:17800`.
- Nhận diện link: `_LINK_DOM` `H:16748`.

Ký hiệu: ✅ có, ❌ không/ẩn, ⚠ có nhưng bị ép hoặc giới hạn, ❓ CHƯA XÁC MINH.

| platform_id | Tên hiển thị | Hiện/ẩn | search | link | channel | collection ("Theo bộ") | preview | login_required + cách | browser_required | Bộ tải | Khoá dedup | Anti-bot / lỗi đã biết | Bằng chứng |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `dy` | Douyin | hiện | ✅ (dịch từ khoá sang Trung) | ✅ (tự chuẩn hoá `modal_id`/`vid`/`note` ⇒ `/video/<id>`) | ✅ | ✅ (đoán theo "Tập N" trong tiêu đề) | ✅ `tim_anh.py` | **Có**, QR qua Playwright, profile `dy_user_data_dir`, cookie `sessionid`/`sid_tt` | có (Playwright headless khi cào) | MediaCrawler | `aweme_id` (ledger `_da_tai_ids.txt` + glob `*_<aweme_id>.mp4`) | `DOUYIN_NEED_LOGIN` (2483), `风控`/`DOUYIN_EMPTY_RESULT`, CDN trả trang lỗi thay MP4, `IPBlockError` | `W:4397-4443`, `W:4913-4915`, `W:4985`, `W:5003`; `MC\...\douyin\core.py:300-325`, `:181-205`, `:1344-1347` |
| `bili` | Bilibili (bilibili.com) | hiện | ✅ | ✅ (b23.tv ⇒ redirect ⇒ BV) | ✅ (có lỗi `Failed to parse creator URL`) | ✅ (API `ugc_season`) | ✅ `tim_anh.py` | **Có**, QR, cookie `SESSDATA`/`DedeUserID` | có | MediaCrawler | `aid` + `bvid` (+ id tập) trong ledger | `-101` ẩn danh vẫn cào được (đừng coi là lỗi login); chỉ "không trùng" khi search | `W:4448-4460`, `W:4890`, `W:5010`; `MC\...\bilibili\core.py:83-101`, `:1052-1124` |
| `bilitv` | Bilibili quốc tế (bilibili.tv) | **không có thẻ** (tự nhận từ link) | ❌ | ✅ duy nhất | ❌ | ❌ | ❌ | Không (video công khai) | không | yt-dlp (BiliIntl) + `impersonate=chrome` | yt-dlp `id` (file `[id]`) | Không impersonate thì bị reset kết nối (0/9 lượt) | `H:1130-1134`, `H:15584-15590`; `Y:1655-1661`, `Y:2126-2135` |
| `ks` | Kuaishou | hiện ("cần đăng nhập") | ✅ (UI không ẩn) | ✅ | ✅ | ❌ | ❓ `tim_anh` thiếu `ks` ⇒ có vẻ không chạy | **Có**, cookie `passToken` (chưa đo) | có | MediaCrawler `--platform ks` | ❓ | CAPTCHA trượt `ANTICRAWL_DEFAULT` khi ẩn danh; code ghi "chưa hứa cào ra video" | `W:1105-1112`, `W:17788-17790`, `W:17808`; `tim_anh.py:35` |
| `hg` | Honggo (phim ngắn) | hiện | ❌ (search dính Cloudflare) | ✅ (1 tập, `--mot-tap`) | ❌ | ✅ chế độ chính (`--count` = số tập) | ❌ | Không (`khong_login`) | không | custom HTTP + ffmpeg (`tai_honggo.py`) | file `<bộ> - Tap NN.mp4` > 100 KB | CDN trang gương chặn IP datacenter (502); trang chính chủ chỉ cho 3 tập/bộ; nghỉ 1,5 s giữa request | `W:4524-4539`, `W:17819`; `HG:1-27`, `HG:406-409` |
| `xhs` | Xiaohongshu (nội địa) | hiện | ⚠ ép sang Xem trước | ✅ bắt buộc có `xsec_token` | ⚠ ép Xem trước; backend đi trình duyệt | ❌ | ✅ `tim_anh.py` | **Có**, QR, profile **chung** `xhs_user_data_dir`, cookie `id_token` | **có** (tải bằng trình duyệt) | MediaCrawler (search) + luồng trình duyệt (`xhs_browser`) | `note_id` | API 461/300017/`-104` (风控); IP ngoài TQ bị tự đổi sang domain rednote.com trừ khi `MC_XHS_NOIDIA=1` | `W:1123-1142`, `W:4485-4513`, `W:4910`; `H:17068-17071`; `W:7142-7210` |
| `rednote` | RedNote (quốc tế) | hiện | ⚠ như xhs | ✅ (`xsec_token`) | ⚠ như xhs | ❌ | ✅ | **Có**, dùng chung profile xhs | có | như xhs (`--platform xhs`, `MC_XHS_INTL=1`) | `note_id` | như xhs | `W:1130-1131`, `W:1144-1151` |
| `yt` | YouTube | hiện | ✅ (`ytsearchN:`) | ✅ (`noplaylist`) | ✅ (`/@h/videos`) | ✅ chỉ nhận link playlist `list=` | ✅ `--list` extract_flat | **Tuỳ chọn**: Chrome thật (không CDP), profile `yt_chrome_profile`; hoặc cookies.txt / cookie trình duyệt | không (chỉ Node ≥ 22 cho EJS) | yt-dlp | yt-dlp `id` (file `[id]`) + `_da_tai.txt` (trừ detail) | "Sign in to confirm you're not a bot" ⇒ sleep 1 s/request, 3-8 s/video; 403 PO Token ⇒ client `web_embedded,default`; giới hạn tuổi / cấm nhúng ⇒ `yt_403` | `Y:231-252`, `Y:1995-2159`, `Y:2165-2171`; `W:4926-4931`; `mo_dang_nhap.py:157-189` |
| `tt` | TikTok | hiện | ⚠ chỉ qua Xem trước (hashtag, **cần cookie login**); tải search trực tiếp ❌ | ✅ (tiền kiểm; fallback trình duyệt khi yt-dlp chỉ thấy audio) | ✅ | ✅ (link collection **hoặc** 1 tập có `dramaID`) | ✅ | Thẻ "na". ⚠ Xem trước search đòi cookie; tải thì **cấm** tự nhét cookie (gây 403) | có (fallback tải, liệt kê kênh, phim bộ) | yt-dlp + Playwright fallback | yt-dlp `id` | Thiếu `Referer` ⇒ "Unexpected response"; `Unable to extract universal data`; slideshow ảnh; cookie login ⇒ 403 | `Y:1541-1544`, `Y:2181-2184`, `Y:2053-2054`, `Y:2387-2490`, `Y:713`; `W:4633-4660`; `H:17064` |
| `fb` | Facebook | hiện | ❌ | ✅ | ✅ Page (Playwright cuộn); **ép login** | ❌ | ⚠ chỉ creator | Link: không; Kênh: **có**, cookie `c_user`/`xs` | có (liệt kê Page) | yt-dlp (`impersonate=chrome`) + Playwright | yt-dlp `id` | `Cannot parse data` khi không impersonate; `Unsupported URL` nếu dán link Page vào ô link; Page ẩn danh bị chặn sau ~1 video | `Y:1155-1320`, `Y:1477-1489`, `Y:2126-2135`; `W:4939-4940`, `W:17841`; `H:9878` |
| `ig` | Instagram | hiện (mở 28/08) | ❌ | ✅ (bài lẻ tự nhận `_ig_bai_le`) | ✅ (trình duyệt `_ig_liet_ke_kenh`) | ❌ | ⚠ chỉ creator | **Có**, cookie `sessionid`/`ds_user_id` xuất sang cookies.txt | có | yt-dlp + Playwright | yt-dlp `id` | Bài ảnh ⇒ `No video formats found` (không phải lỗi); query `?igsi` làm dừng phân trang | `H:239-242`; `Y:89` (`NEN_CAN_COOKIE`), `Y:205-228`, `Y:1017-1150`, `Y:1490-1528`; `W:4960`, `W:17848` |
| `wb` | Weibo (ảnh) | **ẩn** (CSS) | ❓ | ❓ | ❓ | ❌ | backend có `tim_anh` wb | Có, cookie `SUB`/`SUBP` (thẻ login bị comment) | có | MediaCrawler | ❓ | chưa đo | `H:242`; `W:1098`, `W:17846`; `tim_anh.py:35` |
| `tw` | Twitter (X) | **ẩn** | ❌ | ✅ (backend) | ✅ user (backend) | ❌ | ❌ | Có (`auth_token`/`ct0`, `NEN_CAN_COOKIE`) | có (xuất cookie) | yt-dlp | yt-dlp `id` | chưa đo | `H:242`; `Y:89`, `Y:2280-2285`; `W:17847` |
| `rd` | Reddit | **ẩn**; trong UI là "chụp + sub ảnh", không phải tải video | (tai_ytdlp có) | (có) | (có sub) | ❌ | ❌ | không | không | yt-dlp + JSON Reddit (`tai_ytdlp`); **không có** trong `NEN_TANG` của web_app | yt-dlp `id` | — | `H:1167-1169`, `H:242`; `Y:76`, `Y:1322-1390` |
| `th` | Threads | **ẩn**; chụp bài | ❌ | ❌ | ❌ | ❌ | ❌ | chụp (`chup`) | có | `chup_bai.py` (không tải video) | — | — | `H:1170-1172`, `H:242`; `W:17850` |
| `zhihu`, `tieba` | Zhihu / Tieba | **ẩn hoàn toàn** (chỉ có `TEN_NEN` + module MC) | ❌ | ❌ | ❌ | ❌ | ❌ | — | — | module MC có sẵn, không nối | — | — | `H:9728`; `MC\media_platform\{zhihu,tieba}` |

## Khuyến nghị lát cắt

**Lát 1 (không cần trình duyệt): YouTube.**
1. Chỉ cần yt-dlp + ffmpeg + Node (EJS). Ẩn danh vẫn tải được link công khai. Login là tuỳ chọn (`W:17834`).
2. Đủ 4 chế độ + xem trước, tất cả trên một bộ tải: search `ytsearchN:`, link, kênh `/videos`, playlist (`Y:2165-2171`, `Y:2286-2290`, `Y:1468-1606`).
3. Dedup rõ ràng theo `id` với 2 lớp: file `[id]` và archive (`Y:1901-1936`, `Y:2034-2039`). Tuỳ chọn yt-dlp đã được ghi đầy đủ (AUDIT §9) nên dùng làm characterization được.
4. Rủi ro đã được donor đo và ghi lại, có sẵn cách giảm nhẹ: bot-check ⇒ sleep; PO Token ⇒ `web_embedded` (`Y:2069-2104`).

Phương án thay: bilibili.tv. Đơn giản hơn nhưng chỉ có chế độ link, nên độ phủ thấp.

**Lát 2 (cần đăng nhập): Douyin** (Bilibili là phương án dự phòng).
1. Đây là nền chủ lực: đủ search/link/kênh/bộ + "cào không trùng" (`W:4568-4574`).
2. Đăng nhập QR đi qua Playwright bình thường (khác YouTube, không bị Google chặn CDP).
3. Kiểm đăng nhập bằng cookie SQLite rõ ràng (`W:17773`).
4. Dedup bằng một khoá duy nhất `aweme_id`.
5. Chẩn đoán lỗi đã rõ và tách bạch (`DOUYIN_NEED_LOGIN`, CDN lỗi).
6. ⚠ Donor dựa vào MediaCrawler, giấy phép NON-COMMERCIAL ⇒ **phải tự viết lại** client Douyin (ký request, phân trang). Chi phí lớn nhất nằm ở đây.

Nếu muốn giảm rủi ro chi phí đó: làm Bilibili trước. API công khai hơn, `-101` ẩn danh vẫn cào được, và có collection chính thức `ugc_season`.

Không chọn XHS/RedNote làm lát 2: bắt buộc tải bằng trình duyệt + `xsec_token`, và API bị 风控.
Không chọn Kuaishou: bị CAPTCHA, chính code donor ghi "chưa hứa cào ra video" (`W:1105-1112`).
