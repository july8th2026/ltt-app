# License / provenance — video_crawler

Donor: `D:\Viral` @ `368f8be`. Đã xác minh 22/09/2026, chỉ đọc.

| COMPONENT | SOURCE | LICENSE | COMMERCIAL OK? | COPY? | REIMPLEMENT? | REPLACEMENT | RISK |
|---|---|---|---|---|---|---|---|
| MediaCrawler (dy, bili, xhs, ks, wb, zhihu, tieba) | `D:\Viral\resources\app-src\MediaCrawler`, upstream github.com/NanmiCoder/MediaCrawler | NON-COMMERCIAL LEARNING LICENSE 1.1 (`MediaCrawler\LICENSE` dòng 1, 13, 18: "may not be used for any commercial purposes") | ❌ | ❌ | ✅ chỉ tái hiện HÀNH VI (endpoint công khai, luồng login) — không đọc mã để chép cấu trúc/thuật toán ký | client tự viết cho từng nền (S6/S7), hoặc yt-dlp nếu extractor hỗ trợ | CAO: ký request Douyin/XHS là phần tốn nhất; cần xác minh lại pháp lý trước khi bán |
| yt-dlp | PyPI `yt-dlp`, github.com/yt-dlp/yt-dlp | **The Unlicense** (public domain) — GitHub `LICENSE` @ c7fb478d, đọc 22/09 | ✅ | dùng như thư viện (không vendor) | — | — | THẤP. ⚠ Kết luận cũ "GPL-3.0" là sai. Đã có trong `requirements-server.txt:20` |
| yt-dlp EJS (giải JS YouTube) | `remote_components=["ejs:github"]` (donor `Y:2066`) hoặc gói `yt-dlp-ejs` | chưa xác minh | ❓ | ❌ không tải mã từ GitHub lúc chạy | — | gói pip cố định phiên bản (xác minh license ở S3) | TRUNG BÌNH: tải mã ngoài lúc chạy là rủi ro chuỗi cung ứng |
| Node.js ≥ 22 (runtime JS cho EJS) | máy A có v24.17.0 | MIT | ✅ | — | — | — | THẤP |
| Playwright (slice 2) | PyPI `playwright` | Apache-2.0 | ✅ | thư viện | — | — | THẤP |
| `tai_ytdlp.py`, `tai_honggo.py`, `web_app.py`, `web/index.html` | mã của chủ dự án (Viral) | sở hữu nội bộ | ✅ | ❌ (không import chéo; không copy khối) | ✅ viết lại theo hợp đồng LTT; kiến thức (tuỳ chọn yt-dlp, bảng lỗi, luật URL) lấy làm characterization | — | THẤP |
| `stealth.min.js` (donor dùng khi login) | kèm MediaCrawler | theo MediaCrawler | ❌ | ❌ | — | quyết định ở S6 | TRUNG BÌNH |
| `cutclipshort/adapters/downloader.py` | kho LTT | nội bộ | ✅ | tham khảo | — | video_crawler tự viết wrapper hẹp hơn (chặn SSRF, huỷ hợp tác, không nuốt lỗi) | — |
