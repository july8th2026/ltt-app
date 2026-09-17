# Trang công khai LTTCODE — giới thiệu + hướng dẫn + tải (design)

Ngày: 2026-09-17 · Trạng thái: **DUYỆT** (chủ dự án, 17/09) · Kho: LTTSTUDIOSAPP (`apps/lttcode`)
+ LTTCODEAPP (menu Trợ giúp).

## Quyết định đã chốt

| # | Câu hỏi | Chốt |
|---|---|---|
| Q1 | Trang phục vụ ai | **Công khai** — khách tải dùng thử, đăng nhập tài khoản LTT, trả bằng credit |
| Q2 | Dạng tài liệu | **Một trang dài kiểu Nexus** (`/lttcode`), không bộ trang hướng dẫn riêng |
| Q3 | Nút tải phát kênh nào | **`stable`** — cần bản dựng riêng `release.ps1 -Channel stable` |
| Q4 | Cách dựng | **A** — mọi thứ trong `apps/lttcode` (luật "thêm app = một thư mục"); không sửa `server/` |

## Thay đổi

### 1. Manifest (`apps/lttcode/manifest.py`)
`surface="customer"`, `public=True`, `lifecycle="released"`, `group=N_("Ứng dụng")`,
`nav=(NavEntry("LTTCODE", "/lttcode", <icon>, "lttcode"),)`. Giữ `table_prefix`, `bao_tri`.
Hệ quả phải kiểm: `test_190`/`APP_DISPOSITION_V1.md`/`APP_API_COVERAGE_FINAL.md` (vẫn không
`ToolSpec` ⇒ disposition giữ `INTERNAL_ONLY` về **API**, ghi rõ web công khai), lint hợp đồng app
(`surface=customer` cần `routes.py` — đã có), thẻ catalog.

### 2. Trang `/lttcode` (`apps/lttcode/templates/lttcode_download.html` → viết lại)
Mở rộng `base_public.html`, CSS nội tuyến lớp `lc-*` trên token `ltt.css` (theo
`nexus_gioi_thieu.html`). Không ảnh chụp (lộ tên máy/đường dẫn) — minh hoạ bằng HTML/CSS, icon
SVG nội tuyến. Mọi chuỗi `_()`, link nội bộ qua `u()`.

Các mục (neo `id` cố định để ứng dụng mở đúng chỗ):
1. `#tai` — hero: tên, câu giá trị, nút **Tải cho Windows** + phiên bản + dung lượng + SHA-256;
   không có bản stable ⇒ "Sắp phát hành", không nút.
2. Minh hoạ cửa sổ ứng dụng (HTML/CSS).
3. `#tinh-nang` — làm được gì: đọc/sửa mã trong thư mục đã chọn, chạy lệnh có phê duyệt, tìm web,
   model LTT, khôi phục phiên.
4. `#bat-dau` — 4 bước: tải → cài (SmartScreen: *Thông tin thêm → Vẫn chạy*) → đăng nhập tài
   khoản LTT (trình duyệt, bấm Cho phép) → mở thư mục dự án.
5. `#an-toan` — khoá trong Windows Credential Manager, lệnh ngoài workspace phải duyệt, không gửi
   mã đi đâu ngoài LTT, cập nhật kiểm chữ ký, đăng xuất thu hồi khoá.
6. `#chi-phi` — trừ credit theo lượt dùng model; link `/gia-api` (không chép số).
7. `#cap-nhat` — tự báo bản mới, "Cập nhật ngay"; gỡ cài qua Windows Settings › Apps.
8. `#su-co` — FAQ/xử lý sự cố: runtime không khởi động (mở nhật ký), đăng nhập quá 5 phút,
   SmartScreen, thu hồi khoá ở Developers › Keys, yêu cầu hệ thống (Windows 10/11 x64).
9. Cuối trang — nhắc nút tải.

### 3. Route (`apps/lttcode/routes.py`)
`GET /lttcode` giữ đường; context thêm `kich_thuoc` (byte của tệp trong `lttcode_dist`, `None`
nếu thiếu). Không đổi `/update`, `/dl`, đăng nhập, tìm kiếm.

### 4. Ứng dụng (LTTCODEAPP)
Menu **Trợ giúp › Hướng dẫn sử dụng** mở `https://app.lttstudios.com/lttcode#bat-dau` bằng
trình duyệt hệ thống (opener).

### 5. Phát hành stable
Sau E2E 0.1.3 trên dev: `release.ps1 -Version 0.1.3 -Channel stable` (bản dựng riêng, kênh gắn
lúc build) → trang hiện nút tải.

## Kiểm
- `tests/test_1304_lttcode_trang_cong_khai.py`: 200 không đăng nhập; đủ 8 neo; nút tải + phiên
  bản + SHA khi có stable; "Sắp phát hành" khi trống; bản dev không lộ ra trang; `/en/lttcode`
  200 và không chuỗi tiếng Việt ở tiêu đề mục; link `/gia-api` qua `u()`; không `<img` ngoài.
- Test hiện có phải xanh: `test_1301`, `test_190`, `test_212`, `test_85`, `test_126`, i18n.
- Trình duyệt thật: khổ 375 px và 1280 px, không tràn ngang, console sạch; chốt trên
  `https://app.lttstudios.com/lttcode`.
- Gate L1 → deploy → nghiệm thu.

## Kế hoạch triển khai (song song với E2E 0.1.3)
| Việc | Ai | Phụ thuộc |
|---|---|---|
| T1 manifest + disposition docs + test | agent (worktree `phien/lttcode-updater`) | — |
| T2 template trang + route kích thước + EN msgstr + test_1304 | agent | T1 |
| T3 menu Trợ giúp › Hướng dẫn (LTTCODEAPP) | phiên chính | — |
| T4 E2E 0.1.3 dev (đăng nhập lại → "Đã đăng nhập: email") | phiên chính | build 0.1.3 |
| T5 kiểm trình duyệt local (uvicorn cây worktree) | agent | T2 |
| T6 L1 → gộp main → deploy → nghiệm thu công khai | phiên chính | T1–T5 |
| T7 phát 0.1.3 stable (+ menu T3 nằm trong bản stable nếu kịp: 0.1.4) | phiên chính | T4, T6 |
