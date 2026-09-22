# Code reuse matrix — video_crawler

Quyết định chỉ trong: KEEP · PORT · WRAP · REIMPLEMENT · REPLACE · DROP · DEFER.
Nguồn Viral viết tắt như AUDIT_VIRAL_CAO_NGAY.md (`W`, `H`, `Y`, `HG`, `MC`).

| Năng lực Viral | Nguồn | Quyết định | Đích LTT | Lý do |
|---|---|---|---|---|
| Danh sách nền rải rác `NEN_TANG`, `NEN_TANG_YTDLP`, `COOKIE_AUTH`, `NEN_TANG_LOGIN`, `_LINK_DOM`, `capNhatNenTang` | `W:1090-1120`, `W:17772-17850`, `H:16748`, `H:15573` | REPLACE | `apps/video_crawler/nen_tang.py` (một registry) | 6+ nơi khai cùng một nền ⇒ một nguồn chân lý |
| Nhận diện nền theo domain + đoán chế độ từ link | `H:16748-16798`, `W:4376-4460` | PORT (characterization test trước) | `nen_tang.nhan_dien`, `nen_tang.doan_che_do` | Kiến thức đúng, mã JS/py rải rác |
| Chuẩn hoá kênh YouTube | `Y:231-252` | PORT | adapter youtube | |
| Chống SSRF `_url_an_toan`, `enable_file_urls=False` | `Y:1608-1626`, `Y:2031` | PORT | `an_toan_url.py` | Bảo mật, giữ nguyên hành vi |
| Tuỳ chọn yt-dlp YouTube (format, retries, fragments, client, sleep) | `Y:1995-2159` | PORT (bỏ cookiefile người dùng, bỏ `remote_components`) | adapter youtube | Donor đã đo; bỏ phần nguy hiểm |
| Tiến trình con + phân tích stdout `YTDLP_DONE` | `W:4853-5075` | REPLACE | yt-dlp Python API + `progress_hooks` → `ctx.progress` | Tiến độ thật, không regex log |
| Hàng đợi `_tasks`/`_task_queue.json`, `_proc`, `_dang_cao`, `_crawl_kq`, `_tien_do_cao` | `W:1162`, `W:4282-4290`, `W:11543-11706` | DROP → dùng LTT jobs | `platform_core.job_submit` / `job_runner` | Cấm state toàn cục (SUPER PROMPT A.14) |
| Stop = `taskkill /F /T` | `W:17751` | REPLACE | `jobs.cancel` + `ctx.is_cancelled()` trong hook | Huỷ theo job/user |
| Sổ "đã tải" 4 nguồn (SQLite, ids.txt, archive, `[id]` trong tên) | `W:5448`, `index_metadata.py` | REIMPLEMENT | một khoá `(owner, nền, video_id)` tra từ kết quả job đã xong | Bốn sổ lệch nhau; đánh dấu trước khi tải xong là lỗi |
| Lịch sử jsonl theo ngày | `W:3594`, `Y:1771-1807` | REPLACE | bảng `jobs` (owner-scoped) + `result` | Postgres, đa người dùng |
| Bảng lỗi `loi_fetch` | `W:4897-5005` | PORT (bảng phân loại) | `loi.py` | Kiến thức vận hành quý |
| Thống kê 5 ô (đếm hàng đợi RENDER) | `W:3156-3194` | REIMPLEMENT | đếm job video_crawler của user | Donor đếm sai đối tượng |
| Xem trước `tai_ytdlp --list` (extract_flat) | `W:5518`, `Y:1468-1606` | PORT | job `video_crawler.kham_pha` | |
| Cào hết / thêm hàng đợi | `W:4310`, `W:11580` | REIMPLEMENT | job `video_crawler.tai` (hàng đợi = LTT jobs) | |
| Login/profile Chromium chung máy, cookie SQLite | `W:113-117`, `W:17967-18019`, `mo_dang_nhap.py` | DEFER (S6) → REIMPLEMENT | worker `browser`, session mã hoá theo user | Profile chung cho mọi user là cấm (§P) |
| MediaCrawler client dy/bili/xhs/ks | `MC\` | REIMPLEMENT (S6/S7) | adapter riêng | License non-commercial |
| Honggo | `HG` | DEFER | — | Cloudflare/CDN chặn IP datacenter |
| Dịch từ khoá sang Trung (`/api/translate`) | `H:16675-16700` | DEFER | — | Không cần cho slice 1 (YouTube) |
| Reddit/Threads chụp bài | `H:1289+` | DROP | — | Ngoài phạm vi tải video |
| Quota/license Viral | `kdb.usage_cong` `W:5040` | DROP → credit LTT | `manifest.credit_cost` | SUPER PROMPT A.7 |
