> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/developer_portal_mvp_ui/ (đợt ổn định UI khác, đang sống). Chỉ đọc để hiểu lịch sử.

# 02 — Bản đồ quyền quyết định kiểu

## Trả lời ngắn cho người sắp viết app mới

| Cần gì | Lấy ở đâu |
|---|---|
| Màu, nền, viền, bo góc, vòng tiêu điểm | **token** trong `ltt.css` (`--text-*`, `--surface-*`, `--brand-*`, `--border-*`, `--status-*`, `--radius*`, `--focus-ring`) |
| Nút | `.btn` (+ `.btn.ghost`) |
| Ô chọn tệp | **`_o_chon_tep.html` → `o_chon_tep()`** |
| Ẩn input file khi trang đã có chỗ bấm riêng | `.ltt-input-tep-an` |
| Input / textarea / select | dùng chung `min-height:44px` + token, xem `.im-field` làm mẫu |
| Vỏ trang | `base.html` (đã đăng nhập) · `base_public.html` (khách) · `base_plain.html` |
| Kiểu dùng chung cho **cả hai** vỏ | `_kieu_chung.html` |
| Breakpoint | **đã có, đừng thêm.** Đo 26/08: 768px và 390px không tràn |

## Thứ tự nạp, và vì sao nó quan trọng

```
ltt.css  (126 KB, mot tep, nap o moi trang)
   |
   +-- <style> trong base*.html / _kieu_chung.html   (~500 dong)
   |
   +-- style="" noi tuyen                            (470 lan)
   |
   +-- bundle React rieng (agent-canvas | autosub-studio | prompt-ai-ommi)
       chi nap o route cua no, KHONG ro ra ngoai
```

⛔ **Không có tầng nguồn.** `ltt.css` được gõ tay ở dạng nén — sửa là sửa thẳng
vào tệp phân phối. Đừng đi tìm SCSS; không có.

## Vùng có thẩm quyền riêng — biết để không đụng nhầm

| Vùng | Ai quyết |
|---|---|
| `agent-canvas`, `autosub-studio`, `prompt-ai-ommi` | CSS trong bundle React của chính nó |
| `--up-*`, `--tv-accent` | token riêng app, **giữ nguyên** |
| `--err/--ok/--warn` | thế hệ cũ, **giữ nguyên**, app mới dùng `--status-*` |

## Bài học về độ ưu tiên — đã trả giá ngày 26/08

`.ltt-input-tep-an` (0,1,0) bị `.clip-drop input{width:100%}` (0,1,1) đè, **im
lặng**. Tệp CSS không báo, phép kiểm tĩnh không báo — chỉ số đo trong trình duyệt
nói ra.

⇒ **Luật:** một tiện ích mà công việc duy nhất của nó là *đè* thì phải thắng chắc
(`!important`), và luật cũ đang tranh chấp thì **gỡ ở gốc** chứ đừng chồng thêm
một lớp đè nữa. Kho đã có tiền lệ: `.tv-file-input`.
