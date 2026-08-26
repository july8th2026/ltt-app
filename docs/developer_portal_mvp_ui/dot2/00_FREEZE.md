# Đợt 2 — ĐÓNG BĂNG (đọc trước khi code)

**2026-08-27** · nhánh `public-api-v2`

Mục tiêu Đợt 2: giao diện khu `/developers` **sát ảnh demo nhất có thể**, mà
KHÔNG bịa dữ liệu, KHÔNG viết lại, KHÔNG chạm hợp đồng bảo mật, KHÔNG dựng hệ
thiết kế thứ hai.

## Quyết định kiến trúc màu (vấn đề khó)

**Chọn PA C:** một lớp phạm vi `.khu-dev` trên `.app-shell` của khu API.
Bên trong nó **override giá trị** của token ngữ nghĩa hiện có (viền/nền → trung
tính) và thêm họ `--dev-cyan*` (accent vận hành). `:root` **không đổi một byte**
⇒ khu VPS và 14 app khác bất biến, và phép so ảnh trước/sau của Đợt 1 vẫn dùng
được. Xác nhận bởi tài liệu cộng đồng: two-tier tokens (global `:root` +
scoped section overrides) là cách chuẩn; reserve saturation for meaning.

## NĂM THỨ TRONG ẢNH — TỪ CHỐI, kèm lý do

Không phiên nào được "làm nốt cho giống ảnh" năm mục này:

1. **Badge `Stable`/`Beta`/`Alpha` trên thẻ công cụ** — `ToolSpec`
   (`platform_core/registry.py:78`) KHÔNG có trường độ ổn định. Bịa = một nhãn
   sai về chính sản phẩm. Thay bằng badge THẬT: `execution_mode` (sync/async),
   `capability`, số model, `deprecated`.
2. **Bảng bóc tách giá theo dòng** (Model 10 · Steps 1 · …) — `pricing.simulate`
   trả MỘT số; bóc tách phải mổ `invocation.price` = chạm quyền uy giá. Thay
   bằng `pricing_version` + cờ `bounded` + `detail`.
3. **Menu `⋮` gộp hành động khoá** — giấu thu hồi/xoay (không hoàn tác) sau một
   menu, trái Prompt 07 ("danger actions rõ"). Giữ nút hiện.
4. **Thẻ người dùng cuối sidebar** — trùng avatar header nền tảng.
5. **H1 tô đỏ nửa câu** ("**Kết nối** LTT API…") — vỡ khi dịch sang EN (trật tự
   từ khác). Dùng `.dev-h1` + phụ đề.

## HAI THỨ — HOÃN (không phải từ chối)

- **Ô chọn Project ở sidebar lọc chéo trang** — là tính năng mới (cần tham số
  lọc cho keys/logs/usage + test), ngoài 4 Golden Outcome.
- **Phân trang khoá** — khoá thường < 20; làm ở Đợt 4 cùng phân trang nhật ký.

## Ranh giới cứng (không đổi cả đợt)

- 32 route (`test_197`) · 12 mục trần sidebar (`test_303`) · đúng một
  `aria-current="page"`.
- Không sửa `platform_core/public_api/*` TRỪ Đợt 3 (ba hàm **chỉ đọc** + test).
- Không sửa `:root`. Mọi override màu nằm dưới `.khu-dev`.
- `.app-side` dùng chung khu VPS: đổi bề rộng phải chụp `/vps` trước/sau.
- Bí mật hiện một lần · CSRF · lọc theo `user.id` · không in khoá thật vào ví dụ.

## Trạng thái bắt đầu (đã xác minh 2026-08-27)

- `test_197` + `test_300` + `test_303`: **63 passed, 1 skipped**.
- `ltt.css`: 1271 dòng, khối `.dev-*` Đợt 1 ở cuối, khối `--vps-teal*` ở 1162.
- `/api/v1` đang bán thật: `text.chat`, `image.ltt`.
