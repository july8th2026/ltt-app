# GUI_BROWSER_ACCEPTANCE — LTT Voice (16/09/2026)

Biên bản kiểm trên **trình duyệt render thật**. Hai phần, hai mức bằng chứng khác nhau:

| Phần | Máy chủ | Mức bằng chứng | Trạng thái |
|---|---|---|---|
| A. Dev | `tools/studio_dev.py --cong 8127` (SQLite tạm, không model, nhánh `phien/ltt-voice-gui-v2`) | code nhánh chạy thật trong trình duyệt; dữ liệu seed | **Đã làm** |
| B. Production | `https://app.lttstudios.com` (qua Cloudflare) | code đã deploy `d5bd7b07`, dữ liệu thật, worker thật | **Đã làm** — 3 tài khoản: thường, chủ giọng, khách thứ hai |

⛔ Phần A **không** chứng minh được gì về Cloudflare (cache, CSP biên), worker, R2
hay 25 giọng thật. Mọi dòng A ghi `PROVEN (dev)`, không phải `PROVEN`.

## A. Dev — 16/09/2026

**Công cụ:** Browser pane (Chromium) + `playwright-cli` session riêng `voicev2`.
Đăng nhập bằng cookie lấy qua `studio_dev.py --cookie` (HTTP), không gõ mật khẩu.

**Seed bổ sung** (`9085eee0`): giọng kho chung **của tài khoản khác**, đã duyệt license,
thiếu nhãn giới (hình dạng 29/29 hồ sơ production) · giọng `dung_chung` **chưa duyệt**
của chính tài khoản dev (hình dạng 25 giọng production) · một job `queued` đã 3 phút.

| # | Kiểm | Cách | Kết quả |
|---|---|---|---|
| V01 | Số đếm trên nút lọc màn Giọng | đọc trang | Tất cả **23** · Mẫu **20** · Kho chung **1** · Của tôi **2** — giọng chung chưa duyệt đếm vào "Của tôi" ✅ |
| D001 | Nhãn loại trên thẻ | đọc trang | 2 giọng dev → "My voices"; giọng người khác → "Shared library" ✅ |
| V06 | Khung chi tiết giọng kho chung của người khác | bấm "Chi tiết" | chỉ còn "Use this voice"; **không** Disable/Delete; khối thống kê/clip ẩn; HTML không chứa `source.wav` hay UUID dạng `voice/<uuid>/` ✅ |
| V06 | Khung chi tiết giọng của tôi | bấm "Chi tiết" | có "Disable this voice" + "Delete permanently" ✅ |
| — | **Nút "Chi tiết" bấm chuột không mở gì** | Browser pane | 🔴 lỗi **có sẵn trên `main`** (nút là `<button>` trong thẻ, bị `BEN_TRONG` nuốt). Sửa `0821cd52` + test_532 (đối chứng HEAD: 0 khớp ⇒ đỏ) |
| — | Nút "Chi tiết" sau sửa | Playwright: click · focus+Enter · focus+Space | cả ba mở đúng giọng; khối quản lý ẩn/hiện đúng loại; 0 lỗi console ✅ |
| D004 | Lọc "Male" | bấm nút lọc | 12 giọng: 6 giọng mẫu nam + giữ 3 giọng thiếu nhãn, kèm câu *"keeping 3 voices without a gender, region or style label…"*; không lẫn giọng nữ ✅ |
| D015 | Badge Lịch sử cho job queued 3 phút | đọc trang | "Pending · **Unusually long wait**" chỉ ở đúng hàng ấy ✅ |
| D005 | Câu chờ Studio khi hàng đợi > 60 s | bấm "Generate speech"; **chỉ** phản hồi `POST /tao` được giả lập trả `job_id` của job seed — vòng theo dõi gọi `/ket-qua` **thật** | "Waiting for a machine to process…" + *"The queue is taking longer than usual…"* + liên kết `/jobs/devjobkett` ✅ |
| D003-B | Nghe thử văn bản lệch làn | `fetch` POST `/ltt-voice/nghe-thu-van-ban` (preset VI + câu EN, CSRF của trang) | **400** `voice_language_mismatch` + câu đã dịch ✅ |
| W5' | Thanh kéo tốc độ, responsive 6 kích thước × 2 màn | lượt trước cùng ngày (ghi ở `GUI_AUDIT_MATRIX.md`) | 0 tràn ngang, CTA trong khung nhìn, bàn phím 1→1,25→1→2 ✅ |

**Console / network:** 0 lỗi do trang. Lỗi 404 duy nhất là `GET /health` do chính người
kiểm mở để đặt cookie — không phải route của app.

### Giới hạn đã biết của phần A

- **Nghe thử văn bản không có nút GUI nào gọi tới** (`grep` 0 khớp trong `*.js`/`*.html`).
  Kiểm ở mức request là mức cao nhất làm được; ghi nhận, không sửa trong phạm vi này.
- **Phím Enter của Browser pane không kích hoạt `<button>`** (keydown tới, `defaultPrevented=false`,
  không sinh `click`) — giới hạn công cụ, đã đối chứng bằng Playwright `keyboard.press`.
  Đừng đọc lượt Browser pane ấy thành lỗi bàn phím của trang.
- D005 giả lập đúng MỘT phản hồi (`/tao`) vì dev không có worker; đường worker thật đã
  PROVEN riêng ở G01 (Chrome thật, production, 16/09 16:37).

## B. Production — 16/09/2026 23:2x (sau deploy `d5bd7b07`)

**Công cụ:** `playwright-cli` phiên Chrome `voice` (hồ sơ riêng, chủ dự án tự đăng nhập từ lượt G01 — không gõ mật khẩu).
**URL:** `https://app.lttstudios.com` (qua Cloudflare). **Tài khoản:** thường (không admin, ~6.767 credit).

| # | Kiểm | Kết quả |
|---|---|---|
| 1 | Cache-bust | `ltt.css` + `voice.js` đều `?v=aa4194b6` (= `asset_ver` của `/health/version` mới) ✅ |
| 2 | V01 số đếm màn Giọng | Tất cả **45** = Mẫu **20** + Kho chung **25** + Của tôi **0** ✅ (trước deploy: Kho chung 0) |
| 3 | V06 chi tiết giọng kho chung ("Duy Khang") | nhãn "Kho chung"; khối quản lý ẩn (không Tắt/Xoá/clip); HTML không có `voice/<uuid>/` ✅ |
| 4 | D004 lọc "Nam" | câu *"giữ 25 giọng chưa có nhãn giới tính, vùng miền hay phong cách…"*; 0 thẻ nữ ✅ |
| 5 | Studio tạo thật bằng giọng kho chung, thanh kéo bàn phím 1,0 → **1,25** | request `/tao` gửi `toc_do=1.25` + `voice_id=vc_8dc2…`; kết quả sau **11 s**; WAV `200 audio/wav` 434.766 B; MP3 `200 audio/mpeg` 110.060 B; job `a4052648…` ✅ |
| 6 | Nghe ngay khai `ngon_ngu=en` + giọng VI | **400** `voice_language_mismatch`, câu tiếng Việt đã dịch — chặn trước credit ✅ |
| 7 | Console / network | 0 lỗi ngoài đúng phản hồi 400 cố ý ở #6; 0 request hỏng khác ✅ |

**Hai tài khoản thử thêm (16/09 23:5x)** — cookie lấy bằng `tools/tai_khoan_thu.py --cookie` (không gõ mật khẩu),
mỗi tài khoản một browser context riêng:

| Tài khoản | Số đếm (Tất cả / Mẫu / Kho chung / Của tôi) | Chi tiết giọng đầu tiên | Console / network |
|---|---|---|---|
| **chủ 25 giọng** `thu.giongnoi@…local` | 49 / 20 / **0** / **29** (25 kho chung + 4 giọng thử cũ) | "Giọng của tôi"; khối quản lý HIỆN: **Tắt giọng này · Xoá vĩnh viễn** ✅ | 0 / 0 |
| `khach2.thu@…local` | 45 / 20 / **25** / 0 | "Adrian" — "Kho chung"; khối quản lý ẩn; chỉ "Dùng giọng này" ✅ | 0 / 0 |

⇒ D001/V06 PROVEN trên production từ cả hai phía.
