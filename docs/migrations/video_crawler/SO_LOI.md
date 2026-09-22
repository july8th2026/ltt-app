# Sổ lỗi + độ phủ — video_crawler (phiên 22/09/2026)

Một sổ cho cả phiên. Mỗi dòng: tìm thấy ở đâu, bằng chứng, xử lý, trạng thái.

## Lỗi

| # | Nguồn phát hiện | Lỗi | Xử lý | Trạng thái |
|---|---|---|---|---|
| L1 | Rà soát plan cũ | Plan v1 đặt registry vào `platform_core`, L3 mỗi pha, audit Viral chết, parity ✅ bịa | Plan v2 + spec v1.1 | ✅ `8d1c5f12`, `8083d179` |
| L2 | Phản biện spec (BLOCKER) | `requires=("ffmpeg",)` ⇒ chỉ 1 worker gpu+ffmpeg nhận | `requires=("api",)` + `max_runtime_s` | ✅ spec §8, manifest |
| L3 | Phản biện spec (BLOCKER) | yt-dlp nuốt exception của hook khi `ignoreerrors` ⇒ huỷ không dừng | lớp con `DownloadCancelled`, `ignoreerrors` tắt | ✅ `dd80072c` (test đổi lớp ⇒ đỏ) |
| L4 | Phản biện spec | `jobs.result` bị xoá sau 30 ngày ⇒ "không trùng" chỉ nhớ 30 ngày | ghi rõ trên UI; bảng bền = CONTRACT GAP-1 | ⏸ chờ chủ dự án |
| L5 | Phản biện spec | artifacts chỉ 20 tệp | trần `so_luong` 20 | ✅ |
| L6 | Phản biện spec | tệp mồ côi khi huỷ/lỗi | dọn trong `except BaseException` | ✅ test huỷ |
| L7 | Phản biện spec | spec nói donor phân giải DNS (sai); donor `nocheckcertificate` | allowlist + DNS + `allowed_extractors`, không chép `nocheckcertificate` | ✅ |
| L8 | Review làn A | `nhan_dien` so chuỗi con: `netflix.com` ⇒ twitter (lỗi donor) | so hostname | ✅ `ce6f1974` |
| L9 | Review làn A | tên miền thiếu đuôi `iesdouyin`, `xhslink` | `.com` | ✅ |
| L10 | Kiểm GUI | CSP chặn ảnh bìa `i.ytimg.com` | bỏ ảnh ngoài; proxy ảnh có allowlist = S8 | ⏸ S8 |
| L11 | Kiểm GUI | tiến độ giật lùi (luồng hình rồi tiếng), lịch sử job ngập mỗi % | đơn điệu + bước 5% | ✅ `1f356123` |
| L12 | Kiểm GUI | thống kê không tự cập nhật; thông điệp cuối "đang tải" | OOB swap; `progress(100, "Xong…")` | ✅ |
| L13 | Kiểm GUI | mọi mục trùng ⇒ Done im lặng, không tệp | sự kiện + thông điệp rõ, credit 0 | ✅ |
| L14 | Kiểm GUI | poll hàng đợi 4 s cả khi không có job chạy | chỉ poll khi còn job chạy | ⏸ S8 |
| L15 | Làn B | Không có runtime JS/EJS ⇒ yt-dlp cảnh báo "some formats may be missing" | đo ở D1 trên máy A | ⏸ D1 |
| L16 | Review code (BLOCKER) | `url_<id>` từ form ⇒ một id tải cả playlist giá 1 credit | URL dựng lại từ id bởi adapter; mục lấy từ kết quả xem trước của chính user | ✅ `256d4c08`, `5d80b1d1`+ |
| L17 | Review code | id trùng tính 2 lần; huỷ chậm 30 s; `_het_gio` giết tiến trình trước khi dọn; lỗi HTMX 4xx không hiện | dedupe id; kiểm huỷ 5 s; ngân sách 6600 s; HTMX trả 200 | ✅ `256d4c08` |
| L18 | Review code | nhịp tim phụ thuộc hook; livestream; không trần dung lượng | luồng nhịp tim 20 s, lọc live, `max_filesize` 4 GiB | ✅ `5544692f` |
| L19 | Smoke thật | Twitter: `id` = id media ≠ id tweet ⇒ tải sai URL, rồi "không thấy tệp" | dùng `display_id`; tìm tệp cuối duy nhất trong thư mục mục | ✅ |
| L20 | Smoke thật | Instagram "login required", Douyin "Fresh cookies", Bilibili HTTP 412 rơi vào `loi_khac` (retry vô ích) | mã `can_dang_nhap` / `nen_chan`, không retry, thông điệp chỉ tới phiên | ✅ |
| L21 | Smoke thật | Máy prod thiếu `curl_cffi` ⇒ impersonate (bilibili.tv, Facebook) hỏng | thêm `curl_cffi>=0.10,<0.15` vào requirements-server.txt (yt-dlp chỉ nhận dải này) | ✅ `3b384c7c` — cần cài khi deploy |
| L22 | Kiểm test | `test_211::test_a_decade_of_retention…` đỏ khi chạy RIÊNG, cả trên cây trước B0 | có sẵn, ngoài phạm vi (fixture `portal` create_all trước load_app_tables) | ⏸ báo phiên chủ |

## Độ phủ (slice 1 — YouTube)

| Chuỗi §R | Bằng chứng |
|---|---|
| UI | Playwright pane, dev server cô lập 22/09: trang, xem trước, chọn, tải, thống kê, mobile 375 px |
| validate | `test_1905::test_validate_theo_registry_tu_choi_co_ten`, `test_1906::test_dau_vao_sai…` |
| submit + credit | `test_1905` (giữ 2 / quyết toán 2 / hoàn phần lỗi / hoàn đủ) |
| worker claim → adapter | `test_1905` qua `_chay_mot_job` thật; GUI: worker thật + YouTube thật |
| discovery/resolve | `test_1903` (fake YoutubeDL); GUI: 3 kết quả thật |
| download + progress | GUI: 2 video tải thật, `/jobs/{id}/artifacts/0` → 200 `video/mp4` |
| metadata + storage + history | `test_1905` keys `video_crawler/<owner>/<job>/<id>.mp4`; `lich_su` owner-scoped |
| cancel | `test_1905::test_huy_giua_chung…`, `test_1903` cancel propagation |
| dedup | `test_1905::test_khong_trung…`; GUI lượt 2 không tải lại, credit hoàn |
| multi-user | `test_1905::test_lich_su…`, `test_1906::test_nguoi_khac…`, owner lấy từ phiên |
| production (`app.lttstudios.com`) | ⏸ D1 |

## Smoke mạng thật từng nền (máy A, 22/09, URL mẫu công khai từ `_TESTS` của extractor yt-dlp 2026.03.17)

| Nền | Kết quả | Quyết định registry |
|---|---|---|
| YouTube | khám phá + tải (GUI dev) | bật; 4 chế độ ẩn danh |
| TikTok | khám phá + tải 2,7 MB | bật; từ khoá cần phiên (donor); không gửi cookie khi tải |
| Facebook | 1/3 URL tải 7,7 MB; 2 URL "Cannot parse data" (lỗi extractor đã biết) | bật; chỉ link |
| Twitter/X | sau sửa L19: tải 0,5 MB | bật; chỉ link |
| Weibo | tải 1,8 MB (m.weibo.cn) | bật; link + kênh |
| bilibili.tv | tải 13,4 MB (`/video/2045730385`) | bật; chỉ link video độc lập |
| Xiaohongshu | trích xuất chạy; mẫu đều là bài ảnh ⇒ `chi_la_anh` đúng | bật; chỉ link có xsec_token — CHƯA nghiệm thu một bài VIDEO |
| Bilibili | HTTP 412 ẩn danh | bật; MỌI chế độ cần phiên — CHƯA nghiệm thu có phiên |
| Instagram | "login required" | bật; cần phiên — CHƯA nghiệm thu có phiên |
| Douyin | "Fresh cookies needed" | bật; cần phiên — CHƯA nghiệm thu có phiên |
| RedNote | yt-dlp không hỗ trợ (yt-dlp/yt-dlp#16519 mở) | tắt |
| Kuaishou, Honggo | không có extractor yt-dlp; donor: CAPTCHA / CDN chặn IP datacenter | tắt (DEFER — cần client riêng + máy IP dân dụng) |
| Douyin/XHS tìm kiếm + kênh | cần client riêng ký request (X-Bogus/a_bogus) — MediaCrawler cấm thương mại | DEFER, việc lớn riêng |

Nghiệm thu có phiên (Bilibili, Instagram, Douyin, TikTok từ khoá) cần cookies.txt của CHÍNH chủ dự án/tài khoản test
nhập qua giao diện — tác tử không được nhập thông tin đăng nhập.
