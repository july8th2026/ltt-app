# video_crawler — đánh giá chất lượng, nghiên cứu, khuyến nghị giá (22/09/2026)

Căn cứ: `SO_LOI.md` (lỗi + smoke thật), `FEATURE_PARITY.md` (76 dòng), 2 lượt review code độc lập, 2 nghiên cứu
(công cụ cộng đồng; điều khoản nền tảng + vận hành SaaS). Chỉ đạo chủ dự án 22/09: **không nối Auto Scan Video** —
sau này nối qua Workflow.

## 1. Điểm từng hạng mục (0–10)

| # | Hạng mục | Điểm | Căn cứ | Mục tiêu MVP |
|---|---|---|---|---|
| 1 | Kiến trúc, hợp đồng LTT | 8 | registry một nguồn; jobs/credit/storage nền tảng; `platform_core` chỉ 1 hàng governance | 9 — tách mô-đun vận hành, giữ một nguồn |
| 2 | Tiền / credit | 8 | test giữ/quyết toán/hoàn/huỷ/trùng id; ⚠ 2 job song song cùng video vẫn thu 2 lần | 10 — sổ "đã tải" bền chặn trùng |
| 3 | Bảo mật | 7,5 | SSRF+DNS, owner scope, CSRF, cookie mã hoá; ⚠ salt `secretbox` chung kho API key | 9 |
| 4 | Độ phủ nền × chế độ | 5 | 10 nền bật; tìm/kênh thật chỉ YouTube, TikTok (kênh, bộ), Weibo (kênh); 3 nền cần phiên chưa nghiệm thu | 7 — mọi nền bật nghiệm thu thật, có phiên |
| 5 | Độ tin cậy tải (chống bot) | 4 | IP datacenter; chưa EJS/PO token; smoke: Bilibili 412, Facebook "Cannot parse" | 8 — EJS + nhịp tải + giới hạn/giờ + tắt mềm khi hỏng |
| 6 | UX / parity donor | 6 | 28 ✅ · 20 ⚠ · 9 ⏸ · 19 ❌ | 8 — tốc độ/ETA, tải lại, theo dõi kênh |
| 7 | Hiệu năng, mở rộng | 5 | tải tuần tự; proxy ảnh trong request (đã có trần + đệm) | 7 |
| 8 | Vận hành, quan sát | 4 | không số liệu lỗi theo nền, không cảnh báo | 8 — bảng sức khoẻ + tự tắt mềm |
| 9 | Kiểm thử | 8 | ~760 test + smoke thật + GUI; chưa E2E prod | 9 — E2E prod + chạy tải |
| 10 | Pháp lý / ToS | 2 | chưa cam kết quyền, chưa quy trình gỡ | 8 — cam kết mỗi lượt + gỡ 72 h + giới hạn |
| 11 | Nối chuỗi LTT | — | **bỏ khỏi phạm vi** (chủ dự án 22/09: đi qua Workflow) | — |
| 12 | Sản phẩm, giá | 3 | giá tạm 1 credit/video, cờ tắt | 8 — giá theo thời lượng (mục 3) |

**Tổng: ~5,5/10 (bỏ mục 11).** Lõi kỹ thuật tốt; thiếu đúng các thứ làm nên MVP: pháp lý, độ tin cậy ở quy mô, vận hành, giá.

## 2. Nghiên cứu — phát hiện quyết định thiết kế

| # | Phát hiện | Nguồn | Hệ quả cho plan |
|---|---|---|---|
| N1 | Mọi nền cấm tải tự động; YouTube ToS + API policy III.E.1 cấm tải/lưu audiovisual | youtube.com/t/terms; developers.google.com/youtube/terms/developer-policies | Pháp lý là hạng mục **chặn MVP** |
| N2 | OpusClip/Kapwing: khách cam kết quyền, bảo đảm + bồi hoàn trong ToS, kênh gỡ, cấm tái phạm, nhật ký | opus.pro/terms-of-service; help.opus.pro copyright policy | Làm y khuôn: cam kết MỖI lượt tải |
| N3 | NĐ 17/2023 Điều 114: trung gian phải gỡ trong **72 giờ** khi chủ quyền yêu cầu; cookie là dữ liệu cá nhân (Luật 91/2025, hiệu lực 01/01/2026) | văn bản pháp luật VN (agent B) | Quy trình gỡ 72 h + xoá phiên cookie theo yêu cầu |
| N4 | YouTube từ IP datacenter đã sụp với bên lớn: cobalt ngừng YouTube 06/2025; Kapwing tắt YouTube link 10/2025 | github.com/imputnet/cobalt/issues/1356; Kapwing release notes | YouTube = "cố gắng tốt nhất", phải có tắt mềm + nói rõ với khách |
| N5 | yt-dlp: `yt-dlp-ejs` + JS runtime "highly recommended"; PO token cần cho YouTube | yt-dlp README; wiki PO-Token-Guide | Làn tin cậy: EJS + node (đã có v24) |
| N6 | `bgutil-ytdlp-pot-provider` là **GPLv3** — chỉ chạy như service HTTP tách tiến trình | Brainicism/bgutil-ytdlp-pot-provider LICENSE | Quyết định chủ dự án (cài service trên máy A) |
| N7 | Cookie của khách có thể làm tài khoản khách bị khoá; yt-dlp wiki: ~300 video/giờ khách vãng lai, ~2000/giờ có đăng nhập, nghỉ 5–10 s giữa lượt tải | yt-dlp wiki (agent B) | Giới hạn/giờ/tài khoản + cảnh báo trên UI phiên |
| N8 | Extractor hỏng liên tục: TikTok #17604 (01/09/2026), Bilibili #17465/#17254, XHS/RedNote #16519 | yt-dlp issues | Bảng sức khoẻ theo nền + quy trình cập nhật yt-dlp |
| N9 | `Nemo2011/bilibili-api` bị thư luật sư Bilibili (07/2026) buộc gỡ | github.com/Nemo2011/bilibili-api README | Không dùng; Bilibili chỉ qua yt-dlp |
| N10 | `f2` (Apache-2.0), `Douyin_TikTok_Download_API` (Apache-2.0), `ReaJason/xhs` (MIT) dùng thương mại được về LICENSE, nhưng đều dựa ký request dịch ngược ⇒ rủi ro ToS như N1/N9 | các repo trên | Douyin/XHS tìm+kênh, Kuaishou: **chờ quyết định pháp lý**, không làm trong MVP |
| N11 | cobalt (AGPLv3): tham chiếu kiến trúc (rate limit nhiều lớp, proxy qua `HTTPS_PROXY`), KHÔNG dùng mã | imputnet/cobalt docs | Rate limit 2 lớp: xem trước / tải |
| N12 | API chính thức chỉ cho tìm/metadata hoặc nội dung CỦA CHÍNH khách (YouTube Data API, TikTok Display, Meta Graph) | tài liệu API (agent B) | Pha sau: "nhập nội dung của chính bạn" qua OAuth |

Ghi chép đầy đủ: `NC_A_cong_cu.md`, `NC_B_nen_tang.md` (cùng thư mục).

## 3. Giá — phân tích và khuyến nghị

**Đơn vị:** 1 credit = 100đ (Q31).

**Chi phí thật mỗi video** (máy A, không proxy):
- **Băng thông vào:** gói cố định, chi phí biên ≈ 0.
- **Lưu trữ R2:** 0,015 USD/GB-tháng, không tính egress. Một video 200 MB giữ 7 ngày ≈ 0,0007 USD ≈ **20đ**.
- **CPU ghép ffmpeg:** vài giây, ≈ 0.
- **Chi phí ẩn (lớn nhất):** công sửa khi extractor hỏng (N8) và rủi ro pháp lý (N1). Đây là chi phí cố định, cần biên lợi nhuận để gánh.
- **Nếu phải mua proxy dân dụng** (3–8 USD/GB) ⇒ 100 MB ≈ 7.500–20.000đ, tức đắt gấp 25–70 lần giá bán dưới. ⇒ **KHÔNG mua proxy băng thông cho tải đầy đủ trong MVP**. Nếu sau này cần, đó là gói trả phí riêng, có báo giá trước.

**Thị trường:** công cụ tải miễn phí có quảng cáo (SnapTik…); OpusClip/Kapwing gói nhập link vào thuê bao (Kapwing đã tắt YouTube).
Khách của LTT là người làm nội dung, trả tiền cho cả chuỗi (dịch, lồng tiếng, dựng). Crawler là **cửa vào**, nên giá phải thấp đủ để không cản đường vào, và cao đủ để chặn lạm dụng và gánh chi phí sửa chữa.

**Khuyến nghị (thay giá tạm 1 credit/video):**

| Việc | Giá | Ghi chú |
|---|---|---|
| Xem trước (khám phá) | **0 credit** | giữ trần 10 lượt/phút/tài khoản (đã có) |
| Tải video ≤ 10 phút | **3 credit** (300đ) | phần lớn clip ngắn TikTok/Douyin/Shorts |
| 10–30 phút | **6 credit** (600đ) | |
| 30–60 phút | **10 credit** (1.000đ) | |
| 60 phút – 3 giờ | **15 credit** (1.500đ) | > 3 giờ: từ chối (đã có lọc `qua_dai`) |
| Giữ chỗ khi nộp | **15 credit/mục** | quyết toán theo thời lượng THẬT (`credit_cost` do handler báo); mục lỗi/trùng hoàn đủ |
| Nền cần phiên | **không phụ phí** | khách tự chịu rủi ro tài khoản (cảnh báo N7) |

Kiểm tra thuế luỹ thoái (bài học memory "tiền và giá"): 20 clip ngắn = 60 credit = 6.000đ; một video 2 giờ = 15 credit.
Không có sàn ẩn ở tầng quyết toán; `credit_cost` = tổng giá theo từng mục đã tải thật.
**Cần chủ dự án chốt trước khi `lifecycle="released"`.**

## 4. Định nghĩa "tối ưu" (đo được, dùng làm tiêu chí xong của plan)

- Tỉ lệ tải thành công 7 ngày ≥ 95% cho các nền bật ẩn danh; nền dưới 80% trong 24 giờ ⇒ tự tắt mềm và báo.
- Video ≤ 10 phút: từ lúc nộp tới lúc có tệp ≤ 90 s (p90) trên máy A.
- 0 sai lệch tiền: đối soát giữ = quyết toán + hoàn cho mọi job 7 ngày.
- Mọi lượt tải có cam kết quyền; yêu cầu gỡ xử lý ≤ 72 giờ; khách xoá được phiên cookie.
- Nền cần phiên: nghiệm thu thật với phiên của tài khoản test trước khi mở cho khách.
