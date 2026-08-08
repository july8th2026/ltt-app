# H26.8 — Prompt AI release audit

Ngày bắt đầu: 2026-08-09
Trạng thái: code, browser và full gate PASS; chưa deploy.

## Finding đã đóng

- Public copy đổi thành **Prompt AI**; slug `/prompt-ai-ommi`, job, provider,
  credit formula và bảng giữ nguyên.
- Tổng quan không còn một card nhỏ giữa vùng trống: có credit cá nhân, 6 tile
  và 3 panel dùng dữ liệu owner-scoped thật.
- Catalog tích hợp Q81: 8 style, 4 meta, 4 snippet; read-only, clone tạo bản
  private có `cloned_from_id`; catalog admin publish trong DB vẫn giữ.
- Fixture browser đăng ký `ommi_*` trước `create_all`, hết lỗi overview 500.
- Mobile rail từ 174px thành 60px, target tương tác 44px.

## Browser A-Z cô lập

Fixture SQLite/local storage tại cổng 8114, user 200 credit; không worker/provider.

- Desktop 1920×1080: app 1752×892, dashboard 3 cột, document 1920=1920,
  1080=1080; không scroll/overflow ngoài ý muốn.
- Catalog UI: Meta 4, Style 8, Snippet 4. Clone Meta tạo bản private và lịch sử
  `v1 Clone từ mẫu`; tạo resource thật làm dashboard chuyển sang 6 tile + 3 panel.
- Mobile 390×844: document width 375=375; rail 60px, active target 44px.
- Console cuối 0 error/0 warning; request mới của app 200/201. Lỗi 500 đầu phiên
  thuộc fixture cũ, đã tái hiện, tìm traceback và sửa trước audit cuối.

## Test

| Lệnh | Kết quả |
|---|---|
| Targeted backend H26.8 | PASS 41 test; 1 warning TestClient cũ |
| Frontend Vitest | PASS 22 test |
| Frontend typecheck/build | PASS |
| `python tools/gate.py --quick` lượt đầu | FAIL đúng 5 chuỗi i18n mới; đã sửa |
| `python tools/gate.py --quick` sau sửa | PASS 8/8 trong 25,5 giây |
| `python tools/gate.py` lượt đầu | FAIL 8/9: 3 kỳ vọng catalog cũ trong `test_140`; 2.557 test khác pass |
| Targeted `test_catalog_is_separate_from_private` sau sửa | PASS 3/3 |
| `python tools/gate.py` lượt sạch cuối | PASS 9/9 trong 1.630,2 giây; pytest PASS trong 1.604,5 giây |

## Ranh giới và rollback

- Không sao chép DB/file user hay import runtime từ BOT GEMINI.
- Không dựng team, USD, folder, video gần đây hoặc số minh họa.
- Rollback bằng revert commit H26.8; không xóa project/resource/library/job/ledger.
