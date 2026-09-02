# Phase 09 — Ảnh và tiếng ngay trong hội thoại

## Source
- worktree/branch: như Phase 02 · base: `1abeffc`
- canonical rules read: kế hoạch §6 (hàng H43.9), Q84 (không thu quá số đã báo), Q87 (nhịp poll 2 s), Q102/Q117 (ảnh máy B, tiếng máy A), `AUTONOMOUS_OPERATING_CONTRACT` mục Deferred (không planner tự động), báo cáo Phase 01 §9 và AC-14/15

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| Ai quyết định tạo ảnh/tiếng | model tự gọi tool · **người dùng bấm** | người dùng | MVP không chạy planner (hợp đồng gói). Một lượt ảnh 3–12 credit, một lượt tiếng tính theo giây — để model tự quyết là để nó tiêu tiền khách chưa đồng ý | có |
| Xác nhận giá | nộp thẳng · **báo giá → xác nhận → nộp**, gửi kèm số đã nhìn | xác nhận | Q84: khách không bao giờ trả khác số đã báo. Số client gửi lên được máy chủ **tính lại và so**; lệch ⇒ từ chối, không âm thầm trừ số khác | — |
| Tiến độ | worker đẩy · **client hỏi 2 s** (Q87) | hỏi | worker chạy ở tiến trình khác; `dong_bo()` an toàn gọi nhiều lần | có |
| Nút Dừng cho job | có · **không** | không | huỷ một job đang chạy trên GPU máy B không phải thao tác nền tảng hỗ trợ đồng đều; tiền quyết toán theo sản phẩm **thật** nên chờ không tốn thêm | có |
| Nút "Tạo lại" trên lượt job | có · **không** | không | tạo lại một ảnh là **một lần trả tiền nữa** — phải đi qua ô xác nhận giá, không phải một nút một chạm | có |
| Phục vụ tài sản | `/static` · **một cửa `/chatltt/tai-san/{key}` có kiểm sở hữu** | cửa riêng | ảnh/tiếng của khách không bao giờ là tệp tĩnh công khai. `anhnoibo` không có route nào, nên ChatLTT phải tự có cửa | — |
| Kiểm sở hữu | tra CSDL · **theo hình dạng khoá** | hình dạng | cùng lối `apps/thumbnail/routes.py` và `_p_audio.py`: khoá đã mang chủ sở hữu trong đường dẫn; không thêm một vòng CSDL cho mỗi tấm ảnh | có |

## Evidence

| Finding | Source/test | Result |
|---|---|---|
| Báo giá **không** giữ tiền; 4 ảnh đắt hơn 2 ảnh (giá theo tham số, không phẳng); tham số sai ⇒ 400 | `test_624::test_bao_gia_khong_giu_tien…` | pass |
| Năng lực ngoài allowlist (`image.generate`, `video.subtitle`, tên lạ) ⇒ **403 fail-closed** | `test_624::test_nang_luc_ngoai_allowlist…` | pass |
| Tạo ⇒ 202 + job thật (`app_slug=anhnoibo`, `job_type=anhnoibo.generate`), `owner_id` **ép từ phiên**; giữ đúng số đã báo | `test_624::test_tao_anh_giu_dung_so_da_bao…` | pass |
| Đang chạy ⇒ tiến độ, chưa thu; xong 2/4 ảnh ⇒ thu **6** theo `credit_cost` thật, hoàn phần dư; khối `image` vào message | cùng test | pass |
| Tiếng ⇒ khối `audio`; trần **1.500 ký tự** vẫn chặn ở cửa báo giá — không nới | `test_624::test_tao_tieng_sinh_khoi_audio` | pass |
| Job hỏng **và** job huỷ ⇒ hoàn **đủ**, khối `error`, số dư về nguyên | `test_624::test_job_hong_hoac_huy…` | pass |
| Giá đổi giữa chừng ⇒ **từ chối**, không trừ số khác | `test_624::test_gia_doi_thi_tu_choi…` | pass |
| Hết credit ⇒ 402 và **không** tạo job | `test_624::test_thieu_credit…` | pass |
| Cửa tài sản: chủ đọc được, đúng MIME; **người khác và khoá bịa trả CÙNG một 404** (không rò khoá nào có thật); chưa đăng nhập không vào được | `test_625` | pass |
| `kiem_so_huu_khoa` fail-closed: chỉ hai hình; clip **gốc** của khách (`voice/{uid}/`) **không** thuộc cửa này | `test_625` | pass |
| Giao diện: ô xác nhận giá hiện "3 credit" → đồng ý → tiến độ → ảnh về và **tải được**; tiếng ra trình phát | trình duyệt thật, ảnh `reports/anh/chatltt-media.png` | pass |

## Failures found and repaired — cả hai do chính phép kiểm của phase này bắt

1. 🔴 **Path traversal lọt phép kiểm sở hữu.** `anhnoibo/<uid>/../../secrets/app.env`
   **được phép**, vì phép kiểm chỉ so hai đoạn đầu còn phần thoát nằm ở sau.
   `test_625` bắt ngay lượt chạy đầu. Sửa: từ chối mọi khoá có đoạn rỗng, `.`,
   `..` hay `\` **trước** khi so hình dạng. `storage._safe_key` cũng chặn `..`,
   nhưng dựa vào nó là đặt an toàn của cửa này vào một tầng khác — đổi kho (R2,
   CDN) là tầng đó có thể không còn ở giữa.
2. 🔴 **Ô soạn tràn ra ngoài khung cha và đè lên chân trang** (đo 1280×900: đáy
   `.ltc` 758px, ô soạn 801–900px). Một vùng grid mặc định `min-height: auto`
   nên **không co nhỏ hơn nội dung của nó**; khi tổng các hàng vượt chiều cao đã
   đặt, chúng trào ra. Sửa: gỡ ràng buộc ở **từng tầng** (`.ltc` → `.ltc-chinh`
   → `.ltc-luong` → `.ltc-ben`) và tính lại chiều cao theo header/chân trang đo
   thật. Đo lại: ô soạn nằm gọn (787 ≤ 787), chân trang 819, không tràn ngang ở
   cả 390 px và 1440 px.

## Changes
- **Mới** `apps/chatltt/services/tao_media.py` (`bao_gia`, `tao`, `dong_bo`,
  `kiem_so_huu_khoa`, `_khoi_artifact` đọc **cổng ra đã khai** chứ không đoán),
  `apps/chatltt/routes/_p_media.py` (4 route).
- `frontend/chatltt`: `TaoMedia.tsx`, khối `KhoiTaiSan` trong `ThongDiepView`,
  nhịp hỏi job trong `App.tsx`, `api.ts` (+`baoGia`/`taoMedia`/`trangThai`/
  `duongTaiSan`), CSS.
- Tests: `test_624` (8), `test_625` (7), frontend `TaiSan.test.tsx` (5).

## Tests
| Command | Result |
|---|---|
| `pytest test_624 test_625 -n 0` | **15 passed** |
| `npm test` (frontend) | **35 passed / 6 tệp** |
| Trình duyệt thật (cổng 8130, model + worker giả) | ảnh về và tải được, tiếng ra trình phát, 0 lỗi console, không tràn ngang ở 390/1440 px |

## External unknown/blocker
- LIVE với máy B (ảnh thật) và sidecar giọng (tiếng thật): Phase 12. Ở đây worker
  là bản giả trong `tmp/` (gitignore), model là bản giả.
- Chưa kiểm trên URL công khai (quy tắc 5b) — cần deploy, việc của chủ sản phẩm.

## Giao cho phase sau
- **Phase 10**: nút "Đọc to" ngay trên một câu trả lời (hiện mới có "Tạo giọng" ở
  thanh chung); hiện số dư credit cập nhật không cần tải lại trang.
- **Phase 12**: `anhnoibo.suc_khoe` (Phase 06 giao lại) — catalog chưa nói được
  ảnh có sẵn sàng không, nên nút "Tạo ảnh" luôn bật.

## Verdict
**PASS**

## Next
Autocontinue to phase: **10** (UX LibreChat-class, Carbon LTT, desktop + mobile).
