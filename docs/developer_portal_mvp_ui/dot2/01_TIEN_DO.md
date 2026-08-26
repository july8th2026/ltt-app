# Đợt 2 — Nhật ký thi hành

**2026-08-27** · nhánh `public-api-v2`

## Đã xong + đã kiểm trình duyệt

### Đợt 0 — Chốt
- `dot2/00_FREEZE.md`: 5 mục TỪ CHỐI + 2 HOÃN + ranh giới cứng.
- Baseline `test_197/300/303`: 63 passed, 1 skipped.

### Đợt 1 — Token + vỏ (PA C: scope `.khu-dev`)
- `ltt.css`: khối "ĐỢT 2 KHU API" — override token ngữ nghĩa (viền/nền trung
  tính) + họ `--dev-cyan*`, tất cả dưới `.khu-dev`. `:root` không đổi.
- Primitive mới: `.dev-dau` (đầu trang có nút), `.dev-topbar`, `.dev-luoi-2-1`,
  `.dev-sub` tab gạch chân, `.chi-so-icon`/`.chi-so-bt`, `.dev-panel`,
  `.dev-chip-mt`, `.dev-bac` (bậc thang), `.dev-ds`, `.dev-tao`, `.dev-bieu-do`.
- `developers_base.html`: khối thương hiệu sidebar, `.dev-topbar` (trạng thái
  hệ thống thật + chuông có số), `.dev-dau` + block `dev_phu_de`/`dau_hanh_dong`,
  scope `.khu-dev` trên `.app-shell`.
- `_chung.py`: `unread` vào base context (có log khi lỗi, không nuốt lặng).
- **Kiểm QA** (`dot2_p1`, 16 trang × 6 khung): nội dung 1318px@1920, **0 tràn
  ngang · 0 ô thô · 0 fieldset thô · 0 lỗi console · 0 lỗi mạng**. `check_silent_except`: PASS (63/63).

### Đợt 2 — Trang trục (đang làm)
- **overview** ✅ — bố cục 2 cột bám ảnh: 4 thẻ chỉ số có ô biểu tượng cyan,
  panel "Request gần đây" (bảng, `request_log.list_for(limit=5)`), panel "Bắt
  đầu"/checklist, panel "Thông báo" (`notifications`), panel "Tài nguyên".
  Route `trang.py` thêm `recent`/`notes` (đọc thẳng, không bảng mới).
  Kiểm: main_height 530→**845px**, 0 lỗi console.

### Đợt 2 — Trang trục ✅ XONG (4/4)
- **overview** ✅ (đã tả ở trên).
- **keys** ✅ — nút "+ Tạo khóa mới" ở `dau_hanh_dong`; bảng trong `.dev-panel`
  có tab lọc `?mode=live|test` (không thêm route → `test_197` vẫn 32); chip môi
  trường cyan `.dev-chip-mt`; biểu mẫu tạo khóa vào `<details class="dev-tao">`
  (mở sẵn khi chưa có khóa). Route `khoa_du_an.py` + `_keys_page` thêm
  `mode_filter`. Kiểm: 627px (gập), 376px (?mode=test), 0 lỗi.
- **cli** ✅ — bậc thang 4 bước `.dev-bac` (bước 1+4 mang trạng thái thật từ
  `da_co_khoa`/`da_goi_api`, hai bước giữa là nội dung). Route thêm hai cờ đó.
- **logs** ✅ — Phần lớn đã đúng từ Đợt 1 (mã màu trạng thái, filter, error
  code). Chỉ nâng phụ đề về `dev_phu_de`.

### i18n ✅ XONG
- Thêm tay **23 chuỗi** EN vào `.po` (17 + 6 topbar/sidebar), giữ LF, compile
  `.mo`. `test_299` (mọi chuỗi khu API có bản dịch EN): **PASS**.

## Cổng đã qua
- QA trình duyệt `dot2_p2` (16 trang × 6 khung): **0 tràn ngang · 0 ô thô · 0
  fieldset thô · 0 lỗi console · 0 lỗi mạng**; nội dung 1318px@1920.
- Tests: `191·197·199·200·201·202·207·208·299·300·301·302·303` — **tất cả PASS**
  (không hồi quy). `check_silent_except`: PASS.

### Đợt 3 — Biểu đồ ✅ XONG (overview)
- `platform_core/public_api/request_log.py::daily()` — gom theo ngày (UTC),
  **chỉ đọc**, bucket bằng Python (SQLite/PostgreSQL khác nhau ở `date()` trên
  cột tz-aware), **zero-fill** mọi ngày trong cửa sổ. Dùng index
  `ix_public_api_requests_owner_time`.
- `_chung.py::_chart_points()` — dựng hình học SVG (hai đường chung một thang Y),
  trả `None` khi không có gì để vẽ ⇒ template hiện `.dev-trong`, KHÔNG vẽ đường
  phẳng qua số 0. Nhãn trục X neo start/end ở hai đầu để không bị cắt.
- `dev_overview.html` — biểu đồ SVG (không JS, không thư viện) ở cột trái hàng
  đầu, checklist về cột phải; hàng hai: Request gần đây | Thông báo. `.dev-bieu-do`
  + chú thích cyan/đỏ.
- **Test**: `test_201::test_daily_buckets_by_day_and_fills_gaps` +
  `test_daily_is_empty_list_when_no_traffic` — kiểm bucket, gap-fill, đếm lỗi,
  cô lập theo tài khoản, ca rỗng. PASS.
- **Kiểm**: overview main_height 530→**925px**; biểu đồ vẽ đúng (cyan Request +
  đỏ Credit, trục 7 ngày). QA `dot2_p3` (16×6): **0/0/0/0/0**.

### i18n (Đợt 2+3)
- Tổng **28 chuỗi** EN thêm tay (23 + 4 biểu đồ + "LTT API"). `test_299` PASS,
  `check_dich_thieu.py` **PASS ở mốc 344**.

## Cổng đã qua (cập nhật)
- QA trình duyệt `dot2_p3` (16 trang × 6 khung): **0 tràn ngang · 0 ô thô · 0
  fieldset thô · 0 lỗi console · 0 lỗi mạng**; nội dung 1318px@1920.
- Tests: `191·197·199·200·201(+2 mới)·202·207·208·299·300·301·302·303` — PASS.
  `check_silent_except`: PASS. `check_dich_thieu`: PASS.

## Phối hợp đa phiên
- Giao ước với phiên VPS (`lttstudiosapp-d6`): ranh giới tệp rõ; `ltt.css` chỉ
  Edit (không Write) — khối `.khu-dev` nằm sau khối VPS, tách rời; `.po` nối
  cuối, đọc lại trước mỗi ghi. Derived files để người commit sau cùng sinh.

### Đợt 4 — Trang có bố cục demo riêng ✅ (3 trang trục) + phần còn lại kế thừa Đợt 1
- **pricing** ✅ — 2 cột (Soạn lời gọi | Kết quả ước tính); số credit to màu hổ
  phách + `≈ VND` (1 credit = 100đ, Q31); phiên bản giá + cờ `bounded`; hộp lưu
  ý hổ phách 3 gạch. **KHÔNG bảng bóc giá theo dòng** (freeze — `Simulation` trả
  một số). Giữ nguyên hai chốt test: lỗi hiện bằng `b-err`, câu "mô phỏng ≠ báo
  giá" luôn hiện.
- **usage** ✅ — biểu đồ **30 ngày** (tái dùng `request_log.daily()` +
  `_chart_points(width=1040)`), thẻ chỉ số + ngân sách + sao kê giữ nguyên.
- **webhooks** ✅ — 4 thẻ chỉ số (Giao thành công %, Tổng sự kiện, Điểm nhận,
  Cần chú ý) từ `webhook_console.health()`, tỉ lệ tính tại chỗ; thẻ "Cần chú ý"
  đỏ khi có dead/failed. Bảng giao + mã màu trạng thái giữ nguyên.
- **tools** — đã card-based sẵn (`.tool-the` + bảng tham số sinh từ schema +
  badge THẬT `execution_mode`/`capability`), Đợt 1 làm đẹp thêm. Không đụng.
- 9 trang còn lại (docs/settings/privacy/projects/jobs/notifications/quickstart/
  playground/tool_detail/log_detail) — kế thừa vỏ+token Đợt 1, đều qua QA
  0/0/0/0/0; chỉ nâng phụ đề về `dev_phu_de` khi cần (làm dần).

### i18n (Đợt 4)
- Thêm **25 chuỗi** EN (pricing/usage/webhooks). Tái dùng câu "mô phỏng KHÔNG
  sinh báo giá…" đã có sẵn. `test_299` PASS.

## Cổng đã qua (Đợt 4)
- QA `dot2_p4` (16×6): **0/0/0/0/0**.
- `test_207_pricing` **31 PASS** (đã khôi phục hai chốt markup thay vì sửa test).
- `check_dich_thieu`: đỏ 6 chuỗi — **của phiên VPS** (Đổi tên máy, hạn mức băng
  thông…), KHÔNG phải khu API; sẽ xanh khi phiên đó xong i18n của họ.

## Còn lại (Đợt 5)
- QA đầy đủ + hồi quy bảo mật + `gate.py` + đóng băng `10_FINAL.md`.
- (Tùy chọn) nâng phụ đề/panel cho 9 trang phụ để đồng bộ tuyệt đối.
