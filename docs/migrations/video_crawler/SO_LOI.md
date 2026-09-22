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
