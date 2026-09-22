# Feature parity — video_crawler (donor `D:\Viral` @ 368f8be, LTT `apps/video_crawler/`)

Thay tệp cũ (từng đánh ✅ toàn bộ không có bằng chứng). Mọi dòng dưới đây được kiểm bằng cách grep tên hàm
test trong `tests/test_19*_video_crawler_*.py` hoặc dòng smoke/GUI trong `SO_LOI.md` trước khi ghi ✅.

Cột: **donor evidence** (file:line, ký hiệu AUDIT: `W`=web_app.py, `H`=web/index.html, `Y`=tai_ytdlp.py,
`HG`=tai_honggo.py, `MC`=MediaCrawler) · **LTT status** (✅ done / ⚠ partial / ⏸ deferred / ❌ dropped) ·
**LTT evidence** (tên hàm test, đã grep; hoặc dòng SO_LOI.md) · **note**.

✅ chỉ được gắn khi có tên hàm test hoặc dòng smoke/GUI thật trong `SO_LOI.md` chứng minh. Nền cần phiên mà
chưa nghiệm thu bằng phiên thật (Bilibili, Instagram, Douyin, TikTok từ khoá) bị hạ xuống ⚠, dù registry đã bật.

## A. Khối UI "Cào ngay" (AUDIT_VIRAL_CAO_NGAY.md §1)

| # | Khối donor | Donor evidence | LTT status | LTT evidence | Note |
|---|---|---|---|---|---|
| A1 | Thống kê 5 ô + bộ lọc ngày | `H:1074-1100`, `poll()` `H:17375` | ⚠ | `apps/video_crawler/features.py:thong_ke`, `templates/vc_thong_ke.html` | Chỉ 4/5 ô (video hôm nay/đang chạy/xong/lỗi), đếm JOB THẬT (sửa lỗi donor đếm nhầm hàng đợi render `W:3190`). Thiếu ô "Thời gian chạy" và bộ lọc ngày |
| A2 | Đăng nhập nền tảng (thẻ + 🔄 Kiểm tra lại) | `H:1102-1115`, `mo_dang_nhap.py` (QR) | ⚠ | `test_1908_video_crawler_phien.py::test_luu_chi_giu_cookie_cua_nen_va_ma_hoa`, `test_1906_video_crawler_web.py::test_nhap_phien_hien_trang_thai_khong_lo_gia_tri`, `::test_xoa_phien_can_csrf` | Reimplement khác cơ chế: khách tự dán `cookies.txt` (mã hoá `secretbox`), không có QR/browser login. "Kiểm tra lại" (kiểm sống) chưa có — chỉ hiện trạng thái đã lưu |
| A3 | Chọn nền tảng (lưới) | `H:1121-1174` | ✅ | `apps/video_crawler/nen_tang.py:cac_nen_bat`, `test_1906::test_trang_sinh_tu_registry` | Sinh từ registry, không có mã HTML rời như donor |
| A4 | Cách cào 4 kiểu (từ khoá/link/kênh/bộ) | `H:1180-1186`, `updateMode` `H:15622` | ✅ | `test_1900_video_crawler_nen_tang.py::test_che_do_moi_nen_dung_bang_chung`, `test_1906::test_trang_sinh_tu_registry` | Ẩn/hiện theo `NenTang.che_do`, không phải CSS tay theo nền như donor |
| A5 | Từ khoá + ✨ Gợi ý dịch sang Trung | `H:1189-1195`, `goiYTuKhoa` `H:16700` | ⚠ | `test_1903_video_crawler_youtube.py::test_kham_pha_tu_khoa_dung_ytsearch` | Ô từ khoá có (cho nền hỗ trợ `tu_khoa`); gợi ý dịch tự động sang Trung **không** làm — `CODE_REUSE_MATRIX.md` DEFER |
| A6 | Ô link/kênh + danh sách nhiều kênh (👁 riêng từng kênh) | `H:1197-1199`, `renderKenhList` | ⚠ | `apps/video_crawler/features.py:_kiem_nguon` | LTT nhận MỘT `dau_vao` mỗi job (một link/kênh/từ khoá); danh sách nhiều kênh cùng lúc với xem riêng từng kênh của donor không có — cào nhiều kênh = nộp nhiều job |
| A7 | Số lượng | `H:1202` | ✅ | `test_1906::test_dau_vao_sai_bao_loi_co_ten_khong_tao_job` | Giới hạn theo `NenTang.so_luong_toi_da` và trần `SO_MUC_TOI_DA=20` |
| A8 | Sắp xếp (liên quan/nhiều like/mới nhất) | `H:1203`, `H:9921` | ⏸ | — | Spec §4: chỉ MediaCrawler đọc `DY_SORT_TYPE`; YouTube (release 1) không dùng |
| A9 | Thời gian (0/1/7/180 ngày) | `H:1204`, `H:9922` | ⏸ | — | Cùng lý do A8 (`DY_PUBLISH_TIME`) |
| A10 | Lấy video kênh (newest/most_liked) | `H:1205`, `H:9923` | ⏸ | — | `DY_CREATOR_SORT`, chỉ MediaCrawler đọc |
| A11 | Ngôn ngữ (giữ nguyên/zh-CN/zh-TW) | `H:1206-1210` | ⏸ | — | Gắn với A5 (dịch từ khoá), chưa cần cho slice YouTube |
| A12 | 🆕 Cào không trùng | `H:1213-1218`, `_khongTrungVis` | ✅ | `test_1905_video_crawler_job.py::test_khong_trung_chi_bo_muc_chinh_user_da_tai`; SO_LOI L13 (GUI: lượt 2 không tải lại, credit hoàn) | Scope = user (spec §17), không phải máy chung như donor `MC_DEEP_NEW` |
| A13 | Cookie YouTube (browser/cookies.txt) | `H:1220-1236` | ❌ | `test_1903::test_tuy_chon_khong_co_khoa_cam` | Bỏ theo chủ đích: spec §21 cấm nhận `cookiefile` từ khách cho YouTube (an ninh). Cơ chế phiên chung (A2) áp cho nền KHÁC, không áp cho YouTube |
| A14 | Nhật ký hoạt động | `H:1241-1245`, `poll()` | ⚠ | `test_1905::test_moi_muc_deu_trung_thi_bao_ro_cho_khach_khong_tru_tien` (kiểm `job_events.timeline` có mã `bo_qua_trung`); `jobs.py:_su_kien` phát `muc_xong`/`muc_loi` | Thay bằng event trên trang job của nền tảng, không phải 200 dòng log riêng của app |
| A15 | 🗑 Xoá log | `H:1241-1245` | ❌ | — | Không có khái niệm log chung để xoá tay; lịch sử là job theo owner, tự purge 30 ngày (spec §13, CONTRACT GAP-1) |
| A16 | 👁 Xem trước & chọn | `H:1251` + modal `H:9336` | ✅ | `test_1905::test_muc_lay_tu_ket_qua_xem_truoc_cua_chinh_minh`; `test_1906::test_tai_muc_da_chon_lay_tu_xem_truoc_bo_url_cua_form` | Mục tải lấy từ kết quả xem trước ĐÃ XONG của chính khách — không tin URL/tiêu đề trong form (sửa BLOCKER L16) |
| A17 | 🚀 Cào hết (không xem) | `H:1252`, `startCrawl` | ✅ | `test_1906::test_cao_het_theo_nguon`; `test_1905::test_tai_hai_muc_luu_storage_va_tru_dung_hai_credit` | |
| A18 | 📋 Thêm vào hàng đợi | `H:1253`, `addToQueue` | ✅ | `apps/video_crawler/routes.py:tai` → `submit_with_credit` | Không cần nút riêng: MỌI job LTT đã nộp vào hàng đợi (`JOB_QUEUED`) trước khi worker claim — donor phải phân biệt "cào ngay" và "thêm hàng đợi" vì chỉ có 1 tiến trình cào; LTT không có giới hạn đó |
| A19 | ■ Dừng tất cả | `H:1254`, `stopCrawl` | ⚠ | `test_1905::test_huy_giua_chung_thi_cancelled_va_don_tep` | Huỷ ĐƯỢC từng job qua `/jobs/{id}/cancel` của nền tảng (đã kiểm chủ); không có nút "dừng tất cả của tôi" một lần |
| A20 | Tiến trình (%, n/m, tốc độ, ETA) | `H:1256-1271`, `capNhatProgress` | ⚠ | `test_1905::test_tien_do_chi_tang_va_luong_tu_hoa`, `::test_tien_do_kiem_huy_theo_thoi_gian_khong_doi_buoc_5`; SO_LOI (GUI: 2 video tải thật, artifacts 200) | % đơn điệu bước 5% có; tốc độ/ETA (donor suy từ regex log) KHÔNG tính |
| A21 | Hàng đợi tải (⏸ dừng sau task, ↻ thử lại tất cả lỗi, 🧹 xoá xong/lỗi, huỷ/thử lại từng task) | `H:1273-1287` | ⚠ | `apps/video_crawler/features.py:lich_su`; `test_1905::test_lich_su_chi_thay_job_cua_minh` | Xem lịch sử + huỷ từng job có; retry là TỰ ĐỘNG (`max_attempts=2` của nền tảng) thay nút tay; không có "dừng sau task này"/"thử lại tất cả lỗi"/"xoá xong-lỗi" thủ công |
| A22 | Reddit/Threads (chụp bài + sub ảnh) | `H:1289+`, ẩn `H:242` | ❌ | — | `CODE_REUSE_MATRIX.md`: DROP — ngoài phạm vi tải video |

## B. Endpoint backend donor (AUDIT_VIRAL_CAO_NGAY.md §2)

| # | Endpoint donor | Donor evidence | LTT status | LTT evidence | Note |
|---|---|---|---|---|---|
| B1 | `POST /api/crawl` (`chay_crawl`) | `W:19507`, `W:4310` | ✅ | = A17 | |
| B2 | `GET /api/crawl_kq` (kết quả lượt cuối) | `W:18443`, `W:4286` | ✅ | trang job nền tảng `/jobs/{id}` (ARCHITECTURE_MAP §1) | LTT không có khái niệm "lượt cuối" toàn cục — mỗi job giữ kết quả riêng, nhiều job song song được |
| B3 | `GET /api/log` | `W:18435` | ⚠ | = A14 | |
| B4 | `POST /api/stop` (`taskkill /F /T` + dọn Chromium) | `W:19773`, `W:17751` | ⚠ | = A19 | Không cần dọn Chromium: slice 1 không có worker trình duyệt |
| B5 | `POST /api/anh_search` (xem trước) | `W:19590`, `W:5596` | ✅ | `test_1905::test_kham_pha_mien_phi_tra_danh_sach` | Job `video_crawler.kham_pha`, miễn phí |
| B6 | `GET /api/anh_search_get` (poll xem trước) | `W:19194` | ✅ | `/jobs/{id}/progress` của nền tảng | |
| B7 | `POST /api/anh_cao` (tải mục đã tick) | `W:19592`, `W:7142` | ✅ | = A16 | Donor đánh dấu "đã tải" TRƯỚC khi xong (`W:7228`, lỗi) — LTT chỉ ghi key sau khi `storage.put` thành công |
| B8 | `POST /api/task/add` | `W:19526`, `W:11580` | ✅ | = A18 | |
| B9 | `GET /api/task/list` | `W:18454` | ✅ | `test_1905::test_lich_su_chi_thay_job_cua_minh` | |
| B10 | `POST /api/task/cancel` | `W:19550` | ⚠ | = A19 | |
| B11 | `POST /api/task/retry`, `/retry_all` | `W:19562`, `W:19571` | ❌ | `apps/video_crawler/features.py:SO_LAN_THU=2` | Thay bằng retry TỰ ĐỘNG của nền tảng (`max_attempts=2`); không có nút retry theo lô |
| B12 | `POST /api/task/pause` (dừng sau task hiện tại) | `W:19583`, `W:4290` | ❌ | — | Không có "hàng đợi chung" để tạm dừng — mỗi job độc lập |
| B13 | `GET /api/stats` | `W:18385`, `W:3156` | ✅ | = A1 | Cùng giới hạn A1 (thiếu 1 ô + filter) |
| B14 | `GET /api/lich_su_cao` | `W:19033`, `W:3594` | ✅ | `test_1905::test_lich_su_chi_thay_job_cua_minh`, `::test_job_cua_chi_tra_job_cua_chu` | |
| B15 | `POST /api/lich_su_cao/xoa` | `W:19877` | ❌ | — | = A15, thay bằng purge tự động |
| B16 | `GET /api/login_trangthai` | `W:19200`, `W:17800` | ⚠ | `routes.py:_trang` (`phien_cua_toi`) | Chỉ hiện trạng thái ĐÃ LƯU; donor có kiểm sống refresh 3 phút (`_login_check.json`), LTT không có probe sống |
| B17 | `POST /api/open_login` (mở QR) | `W:22387` | ⏸ | — | Cần worker trình duyệt — spec §16/§8 slice 2, chờ chủ dự án chốt S6 |
| B18 | `POST /api/login_kiemtra_one` (kiểm sống 1 nền) | `W:22470` | ⏸ | — | Cùng lý do B17 |

## C. Nền × chế độ (PLATFORM_MATRIX.md)

Chỉ liệt các cặp (nền, chế độ) mà donor HOẶC LTT có gì để báo cáo; ô donor ❌ ở cả hai phía được bỏ qua.

| # | Nền × chế độ | Donor evidence | LTT status | LTT evidence | Note |
|---|---|---|---|---|---|
| C1 | Douyin / từ khoá | `PLATFORM_MATRIX.md:19` (search ✅ qua MediaCrawler) | ❌ | — | REIMPLEMENT S6/S7 (ký request Douyin, MediaCrawler cấm) — chưa làm |
| C2 | Douyin / link | `PLATFORM_MATRIX.md:19`; `AUDIT §7 W:4408-4436` | ⚠ | `test_1918_video_crawler_douyin.py::test_kham_pha_link_tra_mot_muc` | Registry bắt buộc có phiên (`che_do_can_dang_nhap={'link'}`); smoke thật 22/09 "Fresh cookies needed" — CHƯA nghiệm thu có phiên |
| C3 | Douyin / kênh | `PLATFORM_MATRIX.md:19` | ❌ | — | Chưa làm (như C1) |
| C4 | Douyin / bộ | `PLATFORM_MATRIX.md:19` | ❌ | — | Chưa làm (như C1) |
| C5 | Bilibili / từ khoá | `PLATFORM_MATRIX.md:20` | ⚠ | `test_1913_video_crawler_bilibili.py::test_kham_pha_tu_khoa_dung_bilisearch` | Registry bắt buộc phiên cho MỌI chế độ; smoke thật "HTTP 412 ẩn danh" — CHƯA nghiệm thu có phiên |
| C6 | Bilibili / link | `PLATFORM_MATRIX.md:20` | ⚠ | `test_1913::test_kham_pha_link_tra_mot_muc` | như C5 |
| C7 | Bilibili / kênh | `PLATFORM_MATRIX.md:20` | ⚠ | `test_1913::test_kham_pha_kenh_chuan_hoa_va_playlistend` | như C5 |
| C8 | Bilibili / bộ | `PLATFORM_MATRIX.md:20` (API `ugc_season`) | ⚠ | `test_1913::test_kham_pha_bo_dung_url_bo_nguyen_van` | như C5 |
| C9 | Bilibili quốc tế (bilitv) / link | `PLATFORM_MATRIX.md:21` | ✅ | `test_1910_video_crawler_bilibili_tv.py::test_kham_pha_link_tra_mot_muc`; SO_LOI smoke "tải 13,4 MB (`/video/2045730385`)" | Không cần phiên; duy nhất chế độ donor hỗ trợ |
| C10 | Kuaishou / từ khoá, link, kênh | `PLATFORM_MATRIX.md:22` | ⏸ | — | `bat=False`, không có adapter; CAPTCHA + cần IP dân dụng, donor tự ghi "chưa hứa cào ra video" |
| C11 | Honggo / link, bộ | `PLATFORM_MATRIX.md:23` | ⏸ | — | `bat=False`, không có adapter; Cloudflare/CDN chặn IP datacenter |
| C12 | Xiaohongshu / link | `PLATFORM_MATRIX.md:24`; `W:4495-4513` (bắt buộc `xsec_token`) | ⚠ | `test_1916_video_crawler_xiaohongshu.py::test_kham_pha_link_gan_token_tu_webpage_url` | Smoke thật 22/09: trích xuất chạy nhưng mẫu đều là bài ẢNH (`chi_la_anh` đúng) — CHƯA nghiệm thu MỘT bài VIDEO |
| C13 | Xiaohongshu / từ khoá | `PLATFORM_MATRIX.md:24` (ép Xem trước, qua trình duyệt) | ❌ | `adapters/xiaohongshu.py` docstring: chỉ `CHE_DO={"link"}` | Donor đi trình duyệt (`_xhs_creator_browser_worker`), ngoài phạm vi adapter yt-dlp — chưa làm |
| C14 | Xiaohongshu / kênh | `PLATFORM_MATRIX.md:24` | ❌ | — | như C13 |
| C15 | RedNote / từ khoá, link, kênh | `PLATFORM_MATRIX.md:25` | ⏸ | — | `bat=False`; yt-dlp không hỗ trợ RedNote (`yt-dlp/yt-dlp#16519` mở) |
| C16 | YouTube / từ khoá | `PLATFORM_MATRIX.md:26` | ✅ | `test_1903_video_crawler_youtube.py::test_kham_pha_tu_khoa_dung_ytsearch`; SO_LOI (GUI: 3 kết quả thật) | |
| C17 | YouTube / link | `PLATFORM_MATRIX.md:26` | ✅ | `test_1903::test_kham_pha_link_tra_mot_muc`; SO_LOI (GUI: 2 video tải thật) | |
| C18 | YouTube / kênh | `PLATFORM_MATRIX.md:26` | ✅ | `test_1903::test_kham_pha_kenh_chuan_hoa_va_playlistend`, `::test_chuan_hoa_kenh_ve_tab_videos` | |
| C19 | YouTube / bộ | `PLATFORM_MATRIX.md:26` | ✅ | `test_1903::test_kham_pha_bo_dung_url_playlist` | |
| C20 | TikTok / từ khoá | `PLATFORM_MATRIX.md:27` (chỉ qua Xem trước, cần cookie) | ⚠ | `test_1911_video_crawler_tiktok.py::test_kham_pha_tu_khoa_dung_tag` | Registry: `che_do_can_dang_nhap={'tu_khoa'}`; smoke thật xác nhận "từ khoá cần phiên" — CHƯA nghiệm thu có phiên |
| C21 | TikTok / link | `PLATFORM_MATRIX.md:27` | ✅ | `test_1911::test_kham_pha_link_tra_mot_muc`; SO_LOI smoke "khám phá + tải 2,7 MB" | Không gửi cookie khi tải (donor: cookie làm TikTok trả 403) — `test_1900::test_tiktok_khong_gui_cookie_khi_tai` |
| C22 | TikTok / kênh | `PLATFORM_MATRIX.md:27` | ✅ | `test_1911::test_kham_pha_kenh_chuan_hoa_va_playlistend` | Không cần phiên theo registry |
| C23 | TikTok / bộ | `PLATFORM_MATRIX.md:27` | ✅ | `test_1911::test_kham_pha_bo_dung_url_collection` | Chỉ nhận link collection thật, không nhận `dramaID` (ngoài giao donor∩yt-dlp) |
| C24 | Facebook / link | `PLATFORM_MATRIX.md:28` | ✅ | `test_1912_video_crawler_facebook.py::test_kham_pha_link_tra_mot_muc`; SO_LOI smoke "1/3 URL tải 7,7 MB; 2 URL lỗi extractor đã biết" | |
| C25 | Facebook / kênh | `PLATFORM_MATRIX.md:28` (ép login, Playwright cuộn) | ❌ | — | Cần trình duyệt liệt kê Page — ngoài phạm vi adapter yt-dlp, chưa làm |
| C26 | Instagram / link | `PLATFORM_MATRIX.md:29` | ⚠ | `test_1915_video_crawler_instagram.py::test_kham_pha_link_tra_mot_muc` | Registry `che_do_can_dang_nhap={'link'}`; smoke thật "login required" — CHƯA nghiệm thu có phiên |
| C27 | Instagram / kênh | `PLATFORM_MATRIX.md:29` (trình duyệt `_ig_liet_ke_kenh`) | ❌ | — | Không qua yt-dlp ở donor, chưa làm |
| C28 | Weibo / link | `PLATFORM_MATRIX.md:30` (donor ẩn UI, chỉ ảnh qua MediaCrawler) | ✅ | `test_1917_video_crawler_weibo.py::test_kham_pha_link_tra_mot_muc`; SO_LOI smoke "tải 1,8 MB (m.weibo.cn)" | Adapter viết MỚI từ đặc tả yt-dlp, không port donor/MediaCrawler (donor không có đường video cho weibo) |
| C29 | Weibo / kênh | `PLATFORM_MATRIX.md:30` | ✅ | `test_1917::test_kham_pha_kenh_anh_xa_danh_sach_video_that` | `WeiboUserIE` liệt kê video thật, không phẳng |
| C30 | Weibo / từ khoá | — (yt-dlp không có `WeiboSearch`) | ❌ | `adapters/weibo.py` docstring | Không có extractor thật; donor cũng không hỗ trợ đường này |
| C31 | Twitter/X / link | `PLATFORM_MATRIX.md:31` | ✅ | `test_1914_video_crawler_twitter.py::test_kham_pha_link_tra_mot_muc`, `::test_id_la_id_tweet_khong_phai_id_media` (sửa L19); SO_LOI smoke "sau sửa L19: tải 0,5 MB" | |
| C32 | Twitter/X / kênh | `PLATFORM_MATRIX.md:31` (backend, UI ẩn) | ❌ | — | Không port, ngoài phạm vi slice 1 |
| C33 | Reddit | `PLATFORM_MATRIX.md:32` | ❌ | — | Donor: chụp bài + sub ảnh, không phải tải video; `NEN_TANG` của `web_app` không có `rd`. DROP |
| C34 | Threads | `PLATFORM_MATRIX.md:33` | ❌ | — | Chụp bài, không tải video. DROP |
| C35 | Zhihu | `PLATFORM_MATRIX.md:34` | ❌ | — | Ẩn hoàn toàn ở donor, chỉ có module MediaCrawler chưa nối. DROP |
| C36 | Tieba | `PLATFORM_MATRIX.md:34` | ❌ | — | như C35. DROP |

## Tổng số (tính trên các dòng ở trên, A+B+C = 22+18+36 = 76 dòng)

| Trạng thái | Số dòng |
|---|---|
| ✅ done | 28 |
| ⚠ partial | 20 |
| ⏸ deferred | 9 |
| ❌ dropped | 19 |
| **Tổng** | **76** |
