# Audit "Cào ngay" — ViralCrawl (donor)

- Donor: `D:\Viral`, snapshot SHA **368f8be** (đọc bằng grep/read, không chạy mã donor).
- Đường dẫn trong tài liệu tương đối với `D:\Viral\resources\app-src\` (viết tắt: `W` = `web_app.py`, `H` = `web\index.html`, `Y` = `tai_ytdlp.py`, `HG` = `tai_honggo.py`, `MC` = `MediaCrawler\`).
- Mọi khẳng định có `file:line`. Chưa kiểm được thì ghi **CHƯA XÁC MINH**.
- `KB-CHUC-NANG.md` chỉ để đối chiếu. Nó **sai hoặc lỗi thời** ở ít nhất 3 chỗ: thiếu Kuaishou/Honggo/Instagram/Bilibili quốc tế, thiếu chế độ "Theo bộ", và ghi TikTok "không cần đăng nhập" trong khi xem trước tìm-kiếm TikTok lại đòi đăng nhập (xem §8).
- ⚠ MediaCrawler dùng giấy phép **NON-COMMERCIAL LEARNING LICENSE 1.1** (`MC\LICENSE:1`) ⇒ chỉ mô tả hành vi, **không chép mã**.

## 0. Kiến trúc tóm tắt

Máy chủ HTTP thuần `BaseHTTPRequestHandler` (`W:27`, `W:18275`). Phân tuyến bằng chuỗi `if p.path == ...` trong `do_GET` (`W:18328`) và `do_POST`.

Có đúng **3 bộ tải**, mỗi bộ là một tiến trình con Python riêng. Tiến trình cha đọc stdout của nó từng dòng (`W:4853`):

| Bộ tải | Nền tảng | Lệnh | cwd |
|---|---|---|---|
| yt-dlp (`tai_ytdlp.py`) | `NEN_TANG_YTDLP = ("yt","tt","tw","ig","fb","bilitv")` `W:1116` | `W:4545-4561` | `THU_MUC_GOC` |
| module riêng | `NEN_TANG_RIENG = {"hg": "tai_honggo.py"}` `W:1118` | `W:4530-4539` | `THU_MUC_GOC` |
| MediaCrawler `main.py` | còn lại: dy, bili, xhs, rednote, ks, wb | `W:4588-4630` | `THU_MUC_CRAWLER` (`W:4853`, `W:89`) |

Ngoại lệ: XHS/RedNote ở chế độ creator và detail **không** đi `main.py`. Chúng đi luồng trình duyệt (`_xhs_creator_browser_worker` `W:7016`, `_xhs_tai_links_worker` `W:7081`), rẽ nhánh tại `W:4485-4513`.

## 1. Các khối giao diện của "Cào ngay" (`<section id="v-cao">` `H:1071`)

| Khối | Dòng HTML | Hàm JS | Endpoint |
|---|---|---|---|
| Thống kê (5 ô: Video hôm nay / Đang tải / Đã hoàn thành / Lỗi / Thời gian chạy) + bộ lọc 📅 Ngày | `H:1074-1100` | `poll()` `H:17375`, 1,5 s/lần (`H:17424`) | `GET /api/stats` → `thong_ke()` `W:3156`. ⚠ "Đang tải"/"Lỗi" đếm **hàng đợi RENDER** (`_queue`), không phải cào (`W:3190-3194`). "Video hôm nay" = số file video trong `videos/`, tính theo mtime (`W:3163-3180`) |
| Đăng nhập nền tảng (thẻ, 🔄 Kiểm tra lại) | `H:1102-1115` | `renderLcards` `H:9782`, `loginKiemTra` `H:9858` | `GET /api/login_trangthai` `W:19200`; `POST /api/open_login` `W:22387`; `/api/open_browse` `W:22416`; `/api/logout_nentang` `W:22428`; `/api/login_kiemtra` `W:22442`; `/api/login_kiemtra_one` `W:22470` |
| Chọn nền tảng (lưới `.plat[data-p]`) | `H:1121-1174`; ẩn bằng CSS wb/tw/rd/th `H:242` | click handler `H:15555`, `_datNen` `H:15545`, `capNhatNenTang` `H:15573` | không có (chỉ ở client) |
| Cách cào: 🔍 Theo từ khóa / 🔗 Theo link / 👤 Theo kênh / 📦 Theo bộ (`search/detail/creator/chase`) | `H:1180-1186` | `updateMode` `H:15622`; ẩn/hiện theo nền tại `H:15573-15612` | `type` gửi lên `/api/crawl` |
| Từ khóa + ✨ Gợi ý (dịch sang Trung) | `H:1189-1195` | `goiYTuKhoa` `H:16700`, `kwForSearch` `H:16691` (nền Trung `_NEN_TRUNG` `H:16690` tự dịch) | `POST /api/translate` (`H:16675`) |
| Ô link/kênh + danh sách kênh (👁 riêng từng kênh) | `H:1197-1199` | `_tuNhanTuInput`, `_doanTuLink` `H:16763`, `renderKenhList` | — |
| Số lượng | `H:1202` | nhãn đổi theo chế độ `H:15665-15690` | `count` |
| Sắp xếp (Liên quan 0 / Nhiều like 1 / Mới nhất 2) | `H:1203`, giá trị `H:9921` | — | `sort` → env `DY_SORT_TYPE` (`W:4592`) — chỉ MediaCrawler đọc |
| Thời gian (0/1/7/180 ngày) | `H:1204`, `H:9922` | — | `publish_time` → env `DY_PUBLISH_TIME` (`W:4593`) — chỉ MediaCrawler đọc |
| Lấy video của kênh (newest/most_liked) | `H:1205`, `H:9923` | — | `creator_sort` → env `DY_CREATOR_SORT` (`W:4630`) |
| Ngôn ngữ (Giữ nguyên / zh-CN / zh-TW) | `H:1206-1210` | `kwForSearch` `H:16691-16698` | dịch ở client trước khi gửi `input` |
| 🆕 Cào không trùng | `H:1213-1218` | `_khongTrungVis` `H:15707` (chỉ dy search/creator, bili search) | `khong_trung` → env `MC_DEEP_NEW=1` (`W:4568-4574`) |
| Cookie YouTube (trình duyệt / file cookies.txt) | `H:1220-1236` | `_ytCookieVis` `H:15717`; lưu `localStorage` | `cookies` / `cookies_browser` (`H:17100-17104` → `W:4548-4553`) |
| Nhật ký hoạt động + 🗑 Xóa log | `H:1241-1245` | `poll()` | `GET /api/log` `W:18435` (200 dòng cuối + `running`); `POST /api/clear_log` `W:19898` |
| 👁 Xem trước & chọn | `H:1251` + modal `H:9336` | `xemTruoc` `H:16920`, `_xemBatDau` `H:16719`, `xemPoll`, `xemRender`, `xemCao` `H:17022` | `POST /api/anh_search` → `chay_tim_anh` `W:5596`; `GET /api/anh_search_get` `W:19194`; `POST /api/anh_cao` → `cao_anh_chon` `W:7142` |
| 🚀 Cào hết (không xem) | `H:1252` | `startCrawl` `H:17062` | `POST /api/crawl` `W:19507` → `chay_crawl` `W:4310` |
| 📋 Thêm vào hàng đợi | `H:1253` | `addToQueue` `H:17129` | `POST /api/task/add` `W:19526` |
| ■ Dừng tất cả | `H:1254` | `stopCrawl` `H:17125` | `POST /api/stop` `W:19773` → `dung_crawl` `W:17751` |
| Tiến trình (thanh %, n/m, tốc độ, ETA) | `H:1256-1271` | `capNhatProgress` `H:17238` (phân tích **dòng log** bằng regex) | gián tiếp qua `/api/log` |
| Hàng đợi tải (⏸ Dừng sau task này, ↻ Thử lại tất cả lỗi, 🧹 Xoá xong/lỗi, huỷ/thử lại từng task) | `H:1273-1287` | `tqLoad` `H:17152`, `tqCancel/tqRetry/...` `H:17194-17200` | `GET /api/task/list` `W:18454`; `POST /api/task/remove|clear|cancel|retry|retry_all|pause` `W:19535-19584` |
| Reddit/Threads (chụp bài + sub ảnh) | `H:1289+` | — | ẩn (`H:242`); **ngoài phạm vi** tải video |

Luật chặn ở client trước khi gọi backend:
- TikTok + từ khóa ⇒ ép vào Xem trước (`H:17064`, `H:17130`).
- XHS/RedNote + search/creator ⇒ ép vào Xem trước (`H:17068-17071`).
- `guardLogin` kiểm đăng nhập sống **2 lần** trước khi cào (`H:9882-9900`). Bỏ qua kiểm khi `_boQuaLogin`: yt/tt/bilitv luôn bỏ qua; fb chỉ kiểm khi Theo kênh (`H:9873-9880`).
- ⚠ `addToQueue` **không** gọi `guardLogin` và **không** gửi cookie YouTube (`H:17129-17147`). Task worker chỉ kiểm cookie trên đĩa (`W:11605-11614`).

## 2. Endpoint backend liên quan

| Method + path | Handler | Việc làm |
|---|---|---|
| POST `/api/crawl` | `W:19507` → `chay_crawl` `W:4310` | Cổng quota ⇒ cắt `count`. Chống chạy trùng (`busy`/`force`). Chuẩn hoá input. Rẽ nhánh 3 bộ tải. Mở thread `_crawl_worker` rồi trả `{ok:true}` **ngay**, trước khi cào xong |
| GET `/api/crawl_kq` | `W:18443` | Kết quả lượt cuối `{seq, trang_thai: dang/xong/loi, da_luu, msg}` (`W:4286`) |
| GET `/api/log` | `W:18435` | `{lines: 200 dòng cuối, running: _proc is not None}`; `lang=en` thì dịch |
| POST `/api/stop` | `W:19773` | `dung_crawl()`: `_kill_proc_tree` (taskkill /F /T) + dọn Chromium rò rỉ theo profile (`W:17751-17770`, `_don_crawl_ro_ri` `W:10688`) |
| POST `/api/anh_search` | `W:19590` → `chay_tim_anh` `W:5596` | Xem trước (chỉ nhận `search`/`creator`). Từ chối khi đang cào (`W:5606-5608`). Thread `_tim_anh_worker` `W:5518`: yt/tt/fb/ig chạy `tai_ytdlp.py --list`; dy/bili/xhs/rednote/wb chạy `tim_anh.py`, đọc dần jsonl mới |
| GET `/api/anh_search_get` | `W:19194` | `{running, items, msg}` cho lưới xem trước |
| POST `/api/anh_cao` | `W:19592` → `cao_anh_chon` `W:7142` | Tải các mục đã tick. yt/tt/fb/ig: `tai_ytdlp --type detail --input <url,...>`. xhs/rednote: trình duyệt theo href có `xsec_token`. Còn lại: `main.py --type detail --specified_id`. Đánh dấu `index_metadata.danh_dau` **ngay khi bắt đầu** (`W:7228-7232`), chưa đợi tải xong |
| POST `/api/task/add` | `W:19526` → `_task_them` `W:11580` | Thêm job `{id,kind,platform,type,input,count,opts,trang_thai:"cho"}` |
| GET `/api/task/list` | `W:18454` | Danh sách task + cờ `pause` |
| POST `/api/task/cancel` | `W:19550` | Task đang chạy: đặt `cancel=True` + `dung_crawl()`. Task đang chờ: đổi thành `loi / cancelled` |
| POST `/api/task/retry`, `/retry_all` | `W:19562`, `W:19571` | Chuyển `loi` về `cho`; lọc được theo `reason`/`platform` |
| POST `/api/task/pause` | `W:19583` | Dừng sau task hiện tại (`_task_pause` `W:4290`) |
| GET `/api/stats` | `W:18385` → `thong_ke` `W:3156` | Thống kê (xem ghi chú §1) |
| GET `/api/lich_su_cao` | `W:19033` → `lich_su_cao` `W:3594` | Lịch sử cào (§5) |
| POST `/api/lich_su_cao/xoa` | `W:19877` | Xoá metadata jsonl theo giờ; ledger "đã tải" giữ nguyên (`W:3685-3691`) |
| GET `/api/login_trangthai` | `W:19200` | in/out/unknown/na cho từng thẻ `NEN_TANG_LOGIN` (`W:17800`). Ưu tiên kết quả sống `_login_check.json` nếu cũ dưới 5 phút |
| POST `/api/open_login` | `W:22387` | `mo_dang_nhap(plats)` ⇒ `mo_dang_nhap.py` (whitelist `W:22410`) |
| POST `/api/login_kiemtra_one` | `W:22470` | Kiểm sống 1 nền (`kiem_tra_login.py`); whitelist `W:22480` |

## 3. Hàng đợi, tiến độ, huỷ — trạng thái toàn cục

- `_proc` (Popen đang chạy), `_crawl_lock`, `_dang_cao` (giữ chỗ trước khi có `_proc`) — `W:1162-1164`. Giữ chỗ ở `chay_crawl` `W:4344-4358`; hàm chung `_giu_cho_tac_vu` `W:1168`. **Mỗi lúc chỉ một lượt cào/xử lý nặng**. Preview cũng bị chặn trong lúc cào.
- `_tien_do_cao = {"msg","pct","moc"}` `W:4282`. `_eta_log` cập nhật (`W:4663+`); task worker chép sang task.
- `_crawl_kq` `W:4286`: `seq` tăng mỗi lượt, `trang_thai` là dang/xong/loi.
- `_plat_dang_cao` `W:4287`: dùng để dọn Chromium khi dừng.
- Giao thức stdout của tiến trình con, do `_crawl_worker` phân tích (`W:4890-5075`):
  - yt-dlp: `LOG:<text>`; `YTDLP_PROGRESS <idx> <n>` (`Y:1851`); `YTDLP_DONE <ok> <bo_qua>` (`Y:2643`). `da_luu` chỉ được cộng ở dòng DONE (`W:5033-5049`).
  - MediaCrawler: dòng chứa `save video … success` hoặc `save_video … success` ⇒ `da_luu += 1` (`W:5050-5062`). `update_*_aweme|video|note` ⇒ đếm metadata (`W:5063-5070`).
  - Quota cộng theo số video thật tải được: `kdb.usage_cong("cao", n)` (`W:5040`, `W:5058`).
- Hàng đợi task: `_tasks` + `_task_lock` `W:11543`. Lưu ra `DATA_DIR/_task_queue.json` (giữ 300 bản ghi cuối, `W:11547-11562`). Khi nạp lại, task `dang` được trả về `cho` (`W:11565-11578`). Một worker tuần tự `_task_worker` `W:11592`:
  - Nền cần login mà cookie trên đĩa = out ⇒ task lỗi `login_expired`, kéo theo mọi task cùng nền đang chờ (`W:11604-11614`).
  - Chờ trong vòng lặp `while _proc or _dang_cao`. Timeout khi im lặng quá `TASK_IM_MAX=2700 s` hoặc tổng thời gian quá `TASK_TRAN_MAX=43200 s` (`W:11700-11706`).
  - ⚠ Hết vòng chờ mà không huỷ/timeout ⇒ đánh **"xong"** kể cả khi 0 video (`W:11652-11653`). Task **không** đọc `_crawl_kq`.
- Thanh tiến độ ở client hoàn toàn **dựa vào regex trên log**: `Đã tải video (n/m)`, `📊 Đã tải a/b video`, mẫu số lấy từ `mục tiêu N video` trong dòng "▶ Bắt đầu" (`H:17238-17330`; backend in ở `W:4644-4651`).

## 4. Lỗi, thử lại, chẩn đoán (kiến thức nên giữ)

`loi_fetch` được chốt theo **dòng khớp đầu tiên** (`W:4677`, `W:4897-5004`). Bảng câu báo 0 video ở `W:5100+` (chuỗi `elif da_luu == 0 and ...`).

| Mã | Tín hiệu | Nguồn |
|---|---|---|
| `ip` / `fetch` | `DataFetchError`, `RetryError`, `IPBlockError`, `captcha appeared`, `未登录`/`登录已过期`; `300012` ⇒ ip | `W:4897-4903` |
| `risk_xhs` | `code -104`, `没有权限` (tài khoản bị hạn chế, **không** phải lỗi login) | `W:4910-4912` |
| `login_dy` | `DOUYIN_NEED_LOGIN` (API search trả 2483) | `W:4913-4915` |
| `login` | `Login.begin]`, `login_by_qrcode`… (headless không hiện được QR) | `W:4916-4920` |
| `yt_bot` | `Sign in to confirm` / `not a bot` | `W:4926-4927` |
| `yt_403` | `unable to download video data`, hoặc fragment 403 | `W:4930-4931` |
| `fb_link_sai` | fb + `Unsupported URL` (link Page dán vào ô link) | `W:4939-4940` |
| `chi_la_anh` | `No video formats found` (bài ảnh, không phải lỗi) | `W:4960-4963` |
| `ytdlp_loi` / `ytdlp_bug` | `Cannot parse data` (mạnh) / chỉ có câu boilerplate `confirm you are on the latest version` (yếu) | `W:4971-4976` |
| `dy_cdn_loi` | CDN trả trang lỗi thay vì MP4 | `W:4985-4986` |
| `platform` | `DOUYIN_EMPTY_RESULT` / `风控`, bỏ qua dòng "thu lai" | `W:5003-5005` |
| TikTok 0 video | có câu riêng: **đừng** khuyên đăng nhập, vì cookie login làm TikTok trả 403 | `W:4633-4660`, `Y:1734-1741` |

Thử lại:
- yt-dlp dùng `retries: 3`, `ignoreerrors: True`, `concurrent_fragment_downloads: 4` (`Y:2024-2030`).
- Thử lại cấp task là thao tác tay (`/api/task/retry*`).
- Honggo nghỉ `--delay` 1,5 s giữa request (`HG:26`).
- Retry của MediaCrawler (XHS `@retry(3)` lồng nhau ⇒ ~225 s/bài) ghi ở `W:4501-4506`: **CHƯA XÁC MINH** trong mã MC.

## 5. Lịch sử và bản ghi tải

- **Metadata/lịch sử**: `DATA_DIR/<leaf>/jsonl/{search|creator|detail}_contents_<YYYY-MM-DD>.jsonl`, mỗi dòng một JSON.
  - yt-dlp ghi bản ghi `{video_id,id,title,video_cover_url,cover_url,nickname,video_url,url,create_time,last_modify_ts,source_keyword}` (`Y:1771-1807`). Chỉ ghi sau khi xác nhận có file cuối (`_cho_xac_nhan` `Y:1773`).
  - MediaCrawler ghi jsonl qua store riêng (`--save_data_option jsonl` `W:4589`).
- `lich_su_cao()` `W:3594` gom mọi jsonl của `NEN_TANG_HO_TRO`. Khoá khử trùng là `url || id`. Thiếu url thì dựng lại: dy `douyin.com/video/<id>`, bili `bilibili.com/video/<bvid>`, xhs `xiaohongshu.com/explore/<id>` (`W:3634-3641`). ms được đổi ra s (`W:3647-3648`).
- **Sổ "đã tải"** gồm 4 nguồn độc lập:
  1. SQLite `metadata_index.db`, bảng `da_tai(platform TEXT, k TEXT, ts INTEGER, PK(platform,k))`, `k` = url hoặc id (`index_metadata.py:13-45`). DB đặt trong `KHACH_DB_DIR`/`LIC_CACHE_DIR`.
  2. `DATA_DIR/<leaf>/_da_tai_ids.txt`, ledger MediaCrawler, mỗi dòng một id: Douyin `aweme_id` (`MC\media_platform\douyin\core.py:300-325`); Bilibili `aid` + `bvid` + id tập (`MC\...\bilibili\core.py:1052-1124`); XHS `note_id` (`MC\...\xhs\core.py:103-125`). Được hợp nhất ở `_da_tai_keys` `W:5448`.
  3. yt-dlp `download_archive` = `DATA_DIR/<leaf>/_da_tai.txt`, **chỉ** dùng cho search/creator/bo, không dùng cho detail (`Y:1672-1673`, `Y:2034-2039`).
  4. File thật trên đĩa (xem §6).
- Queue task: `DATA_DIR/_task_queue.json` (§3).

## 6. Khoá khử trùng và quy tắc tên file

- **yt-dlp** (yt/tt/fb/ig/tw/bilitv):
  - Khoá = `info["id"]` của extractor. `match_filter=_match_bo_trung` (`Y:1930`) bỏ qua nếu **bất kỳ** file `.mp4/.mkv/.webm` dưới `videos/` có `[<id>]` trong tên.
  - File trung gian `.f137.mp4` không được tính (`Y:1901-1928`, `_RE_TRUNG_GIAN` `Y:1771`).
  - Cộng thêm `download_archive` (không dùng cho detail).
  - Tên: `%(title,uploader,id).80B [%(id)s].%(ext)s`; hashtag bị xoá khỏi title trước khi dựng tên (`MetadataParser` `Y:2144-2158`, chèn ở `Y:2152-2156`).
  - Thư mục: `videos/tu-khoa/<an_toan(kw)>` (search), `videos/kenh/%(channel,uploader,uploader_id)s` (yt creator `Y:2288`), `videos/link` (detail `Y:2491-2492`), `videos/bo/%(playlist_title,playlist_id,playlist)s` (`Y:2227`).
  - `an_toan()` bỏ `<>:"/\|?*`, xuống dòng và tab, cắt 60 ký tự (`Y:194-198`).
- **MediaCrawler Douyin**:
  - `file_base = "<tiêu đề ĐÃ DỊCH, ≤60>_<aweme_id đầy đủ>.mp4"`.
  - Thư mục `tu-khoa/<kw ≤40>`, `kenh/<nick ≤40>_<8 ký tự cuối sec_uid>`, hoặc `link` (`MC\...\douyin\core.py:181-205`).
  - Chống trùng bằng glob `*_<aweme_id>.mp4` (`…:1344-1347`) + ledger.
  - `_safe_name` (`…:59-67`) xử lý tên dành riêng của Windows.
- **MediaCrawler Bilibili**: `"<title>_<6 số cuối aid>"`, thư mục `kenh/<nick>_<mid[-8:]>` (`MC\...\bilibili\core.py` quanh 1075-1101, **CHƯA XÁC MINH** đủ dòng).
- **Honggo**: `videos/<tên bộ ≤60>/<tên bộ> - Tap NN.mp4`; bỏ qua nếu file đã có và > 100 KB (`HG:442-446`, `HG:406-409`).

## 7. Chuẩn hoá URL và nhận diện nền tảng

- **Nhận diện nền theo domain** `_LINK_DOM` (`H:16748-16753`), tóm tắt:
  - dy: `douyin.com | v.douyin.com | iesdouyin`
  - bilitv: `bilibili.tv`; bili: `bilibili.com | b23.tv`
  - xhs: `xiaohongshu.com | xhslink`; rednote: `rednote.com`
  - wb: `weibo.com | weibo.cn`
  - tt: `tiktok.com`; yt: `youtube.com | youtu.be`; fb: `facebook.com | fb.watch`
  - ig: `instagram.com`; tw: `twitter.com | x.com`
  - ks: `kuaishou.com`; hg: `hongguoapp.cn | hongguoduanju.com`
- **Đoán chế độ** `_doanTuLink` (`H:16763-16798`), xét theo thứ tự:
  1. `?vid=` hoặc `?modal_id=` ⇒ detail.
  2. `/voddetail/`, `/collection/`, `/playlist/`, `list=` ⇒ chase.
  3. `/search/`, `q=`, `keyword=` ⇒ search.
  4. Các dạng bài lẻ (`/video/`, `/videos/<số>`, `/note/`, `/explore/<≥6 ký tự>`, `/discovery/item/`, `/status/`, `/reel/`, `/p/`, `watch/?v=`, `fb.watch/`, `/share/[vrp]/`, `/posts/`, `youtu.be/`, `/shorts/`, `b23.tv/`, `v.douyin.com/`) ⇒ detail.
  5. `/user/`, `/space/`, `/profile/`, `/channel/`, `/c/`, `/@`, hoặc tab `/videos`/`/reels` ở cuối ⇒ creator.
  6. fb còn lại ⇒ creator.
  7. Ép cứng: hg ⇒ chase, bilitv ⇒ detail.
- `_validLinks` (`H:16862-16918`):
  - Chặn link một video dán vào ô "Theo kênh" (trừ ig).
  - Chặn yt/tt "Theo bộ" khi không có `/collection/`, `/playlist/`, `list=`.
  - Chặn trộn link nhiều nền trong một lượt.
  - `@handle` được chấp nhận cho tt/yt/fb ở chế độ creator.
- **Backend** `chay_crawl`:
  - Tự tách URL khỏi đoạn văn bản chia sẻ (`W:4376-4381`).
  - Link tìm kiếm Douyin `/search/<kw>` ⇒ chế độ search với từ khoá đã giải mã (`W:4397-4406`).
  - Douyin `modal_id`/`vid`/`/note/<id>` ⇒ `douyin.com/video/<id>`, khử trùng giữ thứ tự (`W:4408-4436`).
  - Douyin creator: cắt query `?...` (`W:4439-4443`).
  - `b23.tv` ⇒ HEAD theo redirect ⇒ `bilibili.com/video/BV…|av…` (`W:4448-4460`).
  - Link bilibili.tv dán vào nút bili ⇒ nền `bilitv` (`W:4518`, `W:4545`).
  - XHS detail bắt buộc có `xsec_token=` (`W:4495-4513`).
- **yt-dlp**:
  - `chuan_hoa_kenh_youtube`: handle trần ⇒ `youtube.com/@h/videos`; URL kênh ⇒ bỏ query/fragment rồi thêm `/videos` nếu chưa trỏ tab (`Y:231-252`).
  - `chuan_hoa_user` (ig/tw): bỏ `?igsi`/`?s=` (`Y:205-228`).
  - Chống SSRF `_url_an_toan`: chỉ http(s), chặn loopback/private/reserved/link-local (`Y:1608-1626`).
  - `enable_file_urls: False` (`Y:2031`).

## 8. Đăng nhập, phiên, cookie

- **Gốc profile**: `BROWSER_DATA_DIR = MC_BROWSER_DATA_DIR || LIC_CACHE_DIR/browser_data || MediaCrawler/browser_data` (`W:113-117`). Mỗi nền một profile Chromium persistent `<plat>_user_data_dir`. XHS và RedNote **dùng chung** `xhs_user_data_dir` (`_xhs_alias` `W:1123-1142`).
- **Mở đăng nhập**: `mo_dang_nhap.py` dùng Playwright `launch_persistent_context(headless=False)` + `stealth.min.js`. URL đăng nhập theo nền ở `mo_dang_nhap.py:51-69`; cửa sổ mở ở `:387`. Douyin/Bili/XHS đăng nhập bằng QR; `--lt qrcode` được truyền cho `main.py` (`W:4588`).
- **YouTube**: Google chặn CDP ⇒ mở **chrome.exe thật** bằng subprocess với profile `browser_data/yt_chrome_profile` (`mo_dang_nhap.py:157-189`). `tai_ytdlp` sao file Cookies sang thư mục tạm rồi dùng `cookiesfrombrowser=("chrome", mirror)` (`Y:1714-1726`).
- **Xuất cookie cho yt-dlp** (ig/tw/fb/yt/tt-search): mở profile headless bằng Playwright, `ctx.cookies()` ⇒ `cookies.txt` Netscape trong thư mục tạm, chmod 600, dọn khi thoát (`Y:1393-1437`). TikTok **không** tự nhét cookie khi tải (`Y:1734-1741`).
- **Kiểm trạng thái từ đĩa**: copy `Default/Network/Cookies` (+ `-wal`/`-shm`) rồi đọc SQLite `cookies`, lọc theo `host_key` và tên cookie auth `COOKIE_AUTH` (`W:17772-17796`, `W:17967-18019`):
  - dy/tt: `sessionid`, `sessionid_ss`, `sid_tt`
  - bili: `SESSDATA`, `DedeUserID`
  - xhs/rednote: `id_token` (chỉ có `web_session` thì coi là unknown)
  - fb: `c_user`, `xs`; ig: `sessionid`, `ds_user_id`; tw: `auth_token`, `ct0`
  - yt: `SAPISID`, `LOGIN_INFO`; ks: `passToken`, `kuaishou.server.web_st` (chưa đo, `W:17788-17790`)
- **Kiểm sống**: `kiem_tra_login.py` ghi `DATA_DIR/_login_check.json` (`W:12143`), chạy lại mỗi 3 phút cho `_LOGIN_RECHECK_PLATS` (`W:12155`).
- `NEN_TANG_LOGIN` (`W:17800-17850`): yt `ytdlp+login_tuychon` (na nhưng có nút), tt `ytdlp` (na), hg `khong_login`, fb là thẻ thật.
- ⚠ **Mâu thuẫn**: thẻ TikTok hiện "na" (không cần đăng nhập), nhưng xem trước tìm-kiếm TikTok **đòi** cookie đăng nhập (`Y:1541-1544`). Đồng thời tải search TikTok trực tiếp **không được hỗ trợ** (`Y:2181-2184`).

## 9. yt-dlp — tuỳ chọn YouTube chính xác (đầu vào characterization)

Nguồn: `opts_cho()` `Y:1995-2159`, dùng ở `Y:2503` (`YoutubeDL(opts_cho(outtmpl, pe)).download(urls)`).

| Khoá | Giá trị | Dòng |
|---|---|---|
| `format` | `_CHUOI_FORMAT()`: mặc định `TAI_CODEC=tot` ⇒ `bv*[vcodec!*=hev][vcodec!*=hvc][vcodec!*=h265][vcodec!*=vvc][vcodec!*=bytevc]+ba/b<cùng bộ lọc>/bv*[vcodec~='^(avc1\|h264)']+ba[ext=m4a]/b[vcodec~='^(avc1\|h264)']/bv*+ba/b[vcodec!=none]`; `TAI_CODEC=h264` ⇒ chỉ chuỗi h264 | `Y:1237`, `Y:1240-1249`, `Y:2019` |
| `format_sort` | `["res","br"]` (h264 ⇒ `["vcodec:h264"]`) | `Y:2020-2021` |
| `merge_output_format` | `mp4` | `Y:2022` |
| `outtmpl` | `<DATA>/youtube/videos/{tu-khoa/<kw>\|kenh/%(channel,uploader,uploader_id)s\|link\|bo/%(playlist_title,playlist_id,playlist)s}/%(title,uploader,id).80B [%(id)s].%(ext)s` | `Y:2168`, `Y:2288-2289`, `Y:2491-2492`, `Y:2227-2228` |
| search URL | `ytsearch<count>:<kw>` + `playlistend=count` | `Y:2169` |
| `match_filter` | `_match_bo_trung` (id đã có file thì bỏ qua) | `Y:1998` |
| `download_archive` | `<DATA>/youtube/_da_tai.txt`, chỉ khi `type != detail` | `Y:1673`, `Y:2038-2039` |
| `noplaylist` | `True` khi detail | `Y:2141-2142` |
| `ignoreerrors`, `nocheckcertificate`, `quiet`, `no_warnings`, `noprogress` | True | `Y:2023-2027` |
| `retries` | 3 (không đặt `fragment_retries`, tức dùng mặc định yt-dlp) | `Y:2028` |
| `concurrent_fragment_downloads` | 4 | `Y:2030` |
| `enable_file_urls` | False | `Y:2031` |
| `progress_hooks` / `logger` | `hook` (in `YTDLP_PROGRESS`) / `_YDLLogger` | `Y:2029`, `Y:2032`, `Y:1838-1851` |
| `ffmpeg_location` | ffmpeg đóng gói (`xu_ly_video.tim_exe`), dự phòng PATH | `Y:1669-1678`, `Y:2040-2041` |
| cookie | ưu tiên `cookiefile` (người dùng nhập path, bỏ dấu nháy + mở `%VAR%`); rồi `cookiesfrombrowser=("chrome", mirror yt_chrome_profile)`; rồi `xuat_cookie_tu_phien("yt")` | `Y:1693-1701`, `Y:1710-1726`, `Y:1754-1758`, `Y:2042-2047` |
| `js_runtimes` | `{"node": {"path": <vendor/node hoặc PATH>}}`, Node tối thiểu 22 | `Y:2064-2065`, `Y:158` |
| `remote_components` | `["ejs:github"]` | `Y:2066` |
| `extractor_args.youtube.player_client` | `YT_PLAYER_CLIENT` hoặc `web_embedded,default` (né PO Token/403) | `Y:2081-2083` |
| `sleep_interval_requests` | `YT_SLEEP_REQ` hoặc 1.0 | `Y:2090-2095` |
| `sleep_interval` / `max_sleep_interval` | 3 / 8 s (env `YT_SLEEP_MIN/MAX`), chỉ khi không phải detail | `Y:2096-2104` |
| postprocessor | `MetadataParser pre_process` xoá `#hashtag` khỏi title | `Y:2150-2158` |

Xem trước YouTube (`liet_ke`, `Y:1468-1606`):
- Tuỳ chọn: `extract_flat="in_playlist"`, `skip_download`, `playlistend=count`, quiet/ignoreerrors.
- Ảnh bìa suy từ id: `https://i.ytimg.com/vi/<id>/hqdefault.jpg`.
- Trường `like` thực chất là `view_count` (`Y:1440-1450`).
- Kết quả in ra một dòng JSON `{ok, items, tong, kenh_nick, kenh_avatar}`.

## 10. Phụ thuộc runtime

- Python venv (`PYTHON_VENV` `W:108`).
- `yt-dlp>=2026.7.4`, `curl_cffi>=0.5` (impersonate cho fb/bili/bilitv `Y:2126-2135`), `playwright==1.62.0` (`MC\pyproject.toml:32,61,64`). ⚠ `MC\requirements.txt:3` lại ghim `playwright==1.45.0`, mâu thuẫn với pyproject.
- Chromium ms-playwright (`PLAYWRIGHT_BROWSERS_PATH` tự trỏ runtime, `Y:46-53`).
- ffmpeg/ffprobe đóng gói.
- Node ≥ 22 (`Y:158`) cho YouTube EJS.
- Chrome thật cho đăng nhập YouTube.
- SQLite (sqlite3 stdlib).
- Honggo: stdlib urllib + ffmpeg; cần IP dân dụng (`HG:19-21`).

## 11. Chưa xác minh

- Mã thật của retry/timeout MediaCrawler (`MC_XHS_TIMEOUT`, `@retry`). Tài liệu này chỉ dẫn lại comment trong `W`.
- Kuaishou: xem trước có chạy được không. `tim_anh.DATA_FOLDER/_PARSER` không có `ks` (`tim_anh.py:35`, `:239`), nên đường này có vẻ không tìm được thư mục/parser. Cookie `passToken` chưa được đo (`W:17788`).
- Tên file Bilibili đủ dòng; tên file Kuaishou/XHS trong MC.
- Luồng trình duyệt XHS (`xhs_browser.py`) và cách đặt tên file của nó.
- Cơ chế `mo_luot` (cửa sổ lướt).
- Chi tiết `_xhs_creator_browser_worker`.
