# video_crawler — Plan nâng lên MVP tối ưu (v3, 22/09/2026)

> Đầu vào: `docs/migrations/video_crawler/DANH_GIA_MVP.md` (điểm, nghiên cứu N1–N12, giá, định nghĩa "tối ưu").
> Chỉ đạo chủ dự án 22/09: KHÔNG nối Auto Scan Video (đi qua Workflow sau); "theo dõi kênh/tự động cào" cũng thuộc
> Workflow — nền tảng không có lịch chạy định kỳ cho app (`platform_core/job_scheduler.py` chỉ xếp hàng).
> Nhánh gốc của mọi làn: `phien/video-crawler` SAU khi phiên hiện tại khép L3 + gộp main (W0).

## A. Luật chạy (một nguồn: CLAUDE.md dự án + mục ⭐ CLAUDE.md toàn cục — không chép thêm)

- Mỗi làn một worktree + nhánh `phien/vcm-<làn>` tách từ `main` đã có W0; **không hai làn sửa cùng tệp** (bảng C chốt
  quyền sở hữu tệp); điều phối review + gộp tuần tự, giải xung đột, không để làn tự gộp.
- Model: việc theo khuôn đã khoá ⇒ `sonnet`; thiết kế/pháp lý/gỡ lỗi khó ⇒ Opus (ghi trong bảng).
- Brief dán `C:\Users\Thang Tuong\.claude\ltt\QUY_TAC_AGENT_VA_TOKEN.md` mục B; báo ≤ 250 từ; TDD RED→GREEN bắt buộc,
  ca characterization lấy từ donor/nguồn có trích dẫn.
- Lệnh nặng của làn (≥ 3 tệp test) qua `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- …`,
  `-n ≤ 6`; điều phối kiểm `cua_so_yen.py` + `tai_may.py` trước gate.
- Gate: làn chỉ test nhắm. Điều phối: L1/L2 khi gộp một đợt nếu thu hẹp được; **L3 MỘT lần cuối phiên**. Lưu ý:
  `requirements-server.txt` thuộc DUNG_CHUNG ⇒ làn nào đụng nó thì không deploy giữa phiên được (chỉ sau L3).
- Chỉ `apps/video_crawler/**`, `tests/test_19xx_*`, `docs/**`. Buộc sửa `platform_core`/`server` ⇒ CONTRACT GAP
  (8 mục) trình chủ dự án. Mỗi làn cập nhật `SO_LOI.md` (bảng lỗi + độ phủ) qua báo cáo — điều phối ghi.
- Dừng chỉ khi: gate đỏ · thao tác không đảo được · thay đổi không rõ của ai · rủi ro bảo mật · quyết định chủ dự án (Q).

## B. Quyết định cần chủ dự án (không chặn các làn khác)

| Mã | Quyết định | Khuyến nghị | Chặn |
|---|---|---|---|
| Q1 | Giá theo thời lượng (DANH_GIA §3) | 0 / 3 / 6 / 10 / 15 credit, giữ chỗ 15/mục | bật `released` |
| Q2 | Văn bản cam kết quyền + điều khoản bảo đảm/bồi hoàn + email/kênh gỡ 72 h | dùng bản nháp của làn L1 | mở cho khách |
| Q3 | Cài service PO token (GPLv3, tiến trình riêng, cổng 4416) trên máy A | có, nếu YouTube < 95% sau L3 (EJS) | L3b |
| Q4 | Bảng `vc_da_tai` (dedup bền + chặn 2 job cùng video) — 1 hàng `governance.STORES` | có (tiền lệ `vc_phien`) | W2-L6 |
| Q5 | Douyin/XHS tìm+kênh, Kuaishou (ký request dịch ngược — N9/N10) | chưa làm trong MVP | W3 |
| Q6 | Bật cờ `LTT_VIDEO_CRAWLER=1` production + nhập cookies.txt tài khoản test để nghiệm thu nền cần phiên | sau W2 | W3 |

## C. Đợt, làn, quyền sở hữu tệp

### W0 — khép phiên hiện tại (điều phối)
Khép L3 (`gate.py --doi --tu 41120e46`) → hoà main → `merge --ff-only` → báo phiên khác (ListAgents) → deploy (app tắt sau cờ;
`curl_cffi` cài theo requirements) → nghiệm thu: `/video-crawler` trả 404 khi cờ tắt, migration `9c3e5a1d7f20` đã chạy.

### W1 — song song (5 làn, tệp tách biệt)

| Làn | Model | Tệp SỞ HỮU | Việc (TDD) | Test mới | Xong khi |
|---|---|---|---|---|---|
| L1 PHÁP LÝ | Opus | `features.py`, `routes.py`, `templates/*.html` (trừ tệp mới của L4) | (a) ô **cam kết quyền** bắt buộc cho MỌI lượt tải (xem trước không cần); lưu `cam_ket={phien_ban, luc}` vào params; thiếu ⇒ LoiDauVao. (b) khối điều khoản ngắn + liên kết chính sách + kênh báo vi phạm (hiển thị, lấy từ hằng trong app). (c) giới hạn tải theo tài khoản: ≤ 60 video/giờ, ≤ 300/ngày (N7) — đếm từ `jobs`. (d) bản nháp văn bản Q2 ở `docs/migrations/video_crawler/PHAP_LY_NHAP.md` | `test_1921_video_crawler_phap_ly.py` | không tải được nếu chưa cam kết; vượt trần ⇒ thông báo rõ; UI kiểm trên trình duyệt |
| L2 GIÁ | sonnet | `manifest.py`, `jobs.py`, MỚI `gia.py` | bảng giá theo thời lượng một nguồn (`gia.py`); `_gia` giữ 15/mục; handler báo `credit_cost` = Σ giá theo `thoi_luong_s` THẬT của mục đã tải (thiếu thời lượng ⇒ bậc ≤ 10 phút); UI hiện ước tính (L1 gọi `gia.bang()` — giao diện đọc, không sửa `gia.py`) | `test_1922_video_crawler_gia.py` | đối soát giữ = quyết toán + hoàn trên các ca: ngắn, dài, lỗi, trùng, huỷ |
| L3 TIN CẬY | Opus | `adapters/_ytdlp.py`, `adapters/youtube.py`, `requirements-server.txt` (dòng `yt-dlp-ejs`) | (a) `yt-dlp-ejs` + `js_runtimes={"node":…}` (node v24 có sẵn), không `remote_components`; (b) nhịp giữa các lượt tải cùng job 5–10 s ngẫu nhiên (N7) + `sleep_interval_requests` giữ; (c) mã lỗi riêng cho "Cannot parse data"/"Unexpected response" (hiện `loi_khac`) ⇒ tạm thời, tối đa 1 lượt thử lại; (d) smoke thật tập trung trước/sau, ghi tỉ lệ | `test_1923_video_crawler_tin_cay.py` | smoke YouTube 10 URL công khai ≥ 9 thành công; ⚠ `loi.py` thuộc L3 |
| L4 SỨC KHOẺ | sonnet | MỚI `suc_khoe.py`, MỚI `routes_van_hanh.py`, MỚI `templates/vc_van_hanh.html`, `nen_tang.py` | (a) tỉ lệ thành công/lỗi theo nền × mã lỗi trong 24 h từ `jobs` (đọc, không bảng mới); (b) trang `/video-crawler/van-hanh` chỉ `require_operator`; (c) **tắt mềm** nền qua cờ env `LTT_VIDEO_CRAWLER_TAT=<id,…>` (registry đọc) + khuyến nghị tắt khi < 80%/24 h (không tự ghi env); (d) quy trình cập nhật yt-dlp `docs/…/VAN_HANH.md` | `test_1924_video_crawler_suc_khoe.py` | trang hiện đúng số trên dữ liệu giả; nền bị tắt biến khỏi UI + validate |
| L5 PHIÊN QR (thiết kế) | Opus | chỉ `docs/migrations/video_crawler/THIET_KE_QR.md` | thiết kế đăng nhập QR qua worker `browser` (app runtime anh em, làn `browser` trong `LTT_WORKER_POOLS`, cô lập profile theo user, luồng ảnh QR qua storage, hết hạn, dọn); chi phí + rủi ro; CONTRACT GAP nếu có | — | tài liệu đủ để chủ dự án quyết |

Điều phối gộp W1 theo thứ tự L2 → L1 → L3 → L4 (L1 cần `gia.bang()`), rồi thêm một dòng import `routes_van_hanh` vào
`routes.py`; test nhắm toàn app; kiểm GUI (luồng cam kết → xem trước → tải → giá hiển thị đúng; trang vận hành).

### W2 — sau khi W1 gộp (contract khoá)

| Làn | Model | Tệp SỞ HỮU | Việc | Test | Điều kiện |
|---|---|---|---|---|---|
| L6 DEDUP BỀN | Opus | `tables.py`, MỚI migration, `platform_core/public_api/governance.py` (1 hàng), `features.py` (`da_tai_ids`), `jobs.py` (giữ chỗ id trước khi tải) | bảng `vc_da_tai(owner, nen, video_id, job_id, tep, tao_luc)` UNIQUE; "không trùng" không còn giới hạn 30 ngày; 2 job cùng video ⇒ job sau bỏ qua, không thu tiền | `test_1925_video_crawler_dedup_ben.py` | Q4 |
| L7 UX | sonnet | `templates/*`, `routes.py` (route "tải lại mục lỗi"), `_ytdlp.py` (tốc độ/ETA vào thông điệp tiến độ) | tốc độ + ETA thật; tải lại các mục lỗi của một job; lọc lịch sử theo nền; hướng dẫn xuất cookies.txt theo trình duyệt; cảnh báo rủi ro tài khoản (N7) cạnh ô phiên | `test_1926_video_crawler_ux.py` | W1 gộp |
| L8 HIỆU NĂNG | sonnet | `jobs.py` (sau L6), `anh_bia.py` | tải song song ≤ 2 mục/job cho nền không cần phiên (vẫn giữ nhịp N7 theo nền); đo p90 thời gian tới tệp đầu; proxy ảnh: ghi ảnh vào storage ở bước khám phá thay vì tải trong request | `test_1927_video_crawler_hieu_nang.py` | L6 gộp |

### W3 — nghiệm thu + mở rộng có điều kiện

- Nghiệm thu production (Q6): tài khoản test `khach*.thu` (cookie, không gõ mật khẩu) trên `https://app.lttstudios.com`:
  mỗi nền bật một luồng xem trước → tải → tải về; nền cần phiên với cookies.txt của tài khoản test; 5 người dùng song song.
- L3b (Q3): service PO token nếu YouTube < 95%.
- Q5 (Douyin/XHS tìm+kênh, Kuaishou): chỉ khi chủ dự án chấp nhận rủi ro N9/N10 — làn riêng theo khuôn adapter.
- Tổng kết phiên: L3 MỘT lần → khép nếu đỏ → gộp main → deploy → NHAT_KY.

## D. Bảng theo dõi (cập nhật khi gộp từng làn)

| Làn | Nhánh | SHA | Test nhắm | GUI | Trạng thái |
|---|---|---|---|---|---|
| W0 | phien/video-crawler | 41120e46 (L3) | L3 + khép | — | ⏳ khép đang xếp hàng khoá |
| L1–L5 + Q5 (douyin/xhs tìm+kênh, kuaishou) | phien/vcm-* → phien/vcm-tich-hop | 4f0c3d81 | 1092 xanh, kiểm tĩnh sạch | cam kết, vận hành 403, bảng giá, tải thật 2 video | ✅ gộp |
| L6 dedup bền | phien/vcm-dedup | 07265224, 5927559e | test_1925 (+ ca tải lại video hết hạn mà lỗi ⇒ giữ dấu 'xong', sửa khi gộp) | — | ✅ gộp |
| L7 UX | phien/vcm-ux | | | | ⏳ đang chạy |
| L8 hiệu năng | phien/vcm-perf | | | | chờ L7 |
