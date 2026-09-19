> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/developer_portal_mvp_ui/ (đợt ổn định UI khác, đang sống). Chỉ đọc để hiểu lịch sử.

# 04 — Quyết định kiến trúc UI

## Câu hỏi phải trả lời được sau tài liệu này

> *"Tôi làm app mới. Nút / input / file upload / khoảng cách / breakpoint lấy ở đâu?"*

---

## Quyết định 1 — Authority là `ltt.css` + 64 token hiện có. **Không dựng hệ thứ hai.**

Audit không tìm thấy hai framework đánh nhau. Có **một** CSS toàn cục, một bộ token
ngữ nghĩa đủ dùng, và ba bundle React đóng gói riêng không rò ra ngoài.

⛔ Vì vậy **bác bỏ** mọi phương án kiểu "dựng design system mới", "thêm Tailwind",
"chuyển sang CSS modules". Chúng giải quyết một vấn đề mà kho này **không có**, và
đổi lại tạo đúng cái vấn đề đề bài cấm: một authority thứ hai cạnh tranh.

**Chuẩn:** `--text-*`, `--surface-*`, `--brand-*`, `--border-*`, `--status-*`,
`--radius*`, `--focus-ring`.
**Không chuẩn nhưng GIỮ NGUYÊN:** `--err/--ok/--warn`, `--up-*`, `--tv-accent`.
Không xoá — xoá là một đợt regression không đổi lấy gì.

---

## Quyết định 2 — File picker: **nâng khuôn đã có, không phát minh khuôn mới**

`/taovideo` đã giải xong bài toán này và **đang chạy production**:

```html
<label for="x"><span>▧</span><strong>Ảnh</strong><small>PNG, JPG, WEBP</small>
  <input class="tv-file-input" id="x" type="file" accept="image/*" multiple></label>
```
```css
.tv-file-input{position:absolute!important;width:1px!important;height:1px!important;
               opacity:0;pointer-events:none}
```

Input native vẫn **là** input native — chỉ ẩn khỏi mắt. `<label for>` giữ nguyên
liên kết, nên chọn tệp, validate, `multipart`, và mọi móc JS đọc `input.files` đều
không đổi.

⭐ **Vì sao đây là phương án ít rủi ro nhất:** nó không phải một ý tưởng. Nó là một
khuôn đã chạy thật trên máy này, với người dùng thật, đủ lâu để nếu nó phá
`multipart` thì ta đã biết.

⛔ **Nhưng KHÔNG sao chép nguyên si.** Khuôn gốc dùng 6 màu viết cứng
(`#6e302d`, `#141315`, `#251213`, `#ff635b`, `#78797e`, `#ddd`) và chỉ báo tiêu
điểm yếu hơn phần còn lại của hệ (đổi màu viền, trong khi 16 luật khác dùng
`outline:2px solid var(--focus-ring)`).

Sao chép nguyên si = nhân bản 6 màu cứng và một lỗ accessibility ra 10 app.

⇒ **Dựng lại cấu trúc đó trên token, với vòng tiêu điểm chuẩn.** Tên trung lập
`.ltt-file*` (không mang tên app), đặt trong `ltt.css`.

---

## Quyết định 3 — Sửa gốc theo tầng, không vá theo trang

```
UI-001 file picker  ->  primitive dung chung  ->  doi noi goi  (batch 1 + 2)
UI-002 overflow     ->  sua 3 luat trong ltt.css                (batch 1)
UI-003 chip tran    ->  chi bao con noi dung, KHONG doi layout  (batch 3, rieng)
UI-004 mau cung     ->  chi ap dung cho primitive MOI           (khong quet hang loat)
```

---

## Quyết định 4 — **Không đụng breakpoint**

Đo cho thấy 768px và 390px **không tràn**. Responsive đang đúng. Mọi thay đổi
breakpoint ở đợt này là rủi ro không đổi lấy gì.

---

## Quyết định 5 — Không tạo primitive cho thứ chưa chứng minh là đang hỏng

Đề bài liệt kê 19 primitive ứng viên. Audit chỉ chứng minh được **một** đang gây
lỗi đo được: **FilePicker**.

`.btn` đã là một primitive (28 luật mở rộng, không mâu thuẫn). Input/select/textarea
dùng chung `min-height:44px` + token. Chưa có bằng chứng chúng hỏng.

⛔ Tạo 19 primitive lúc này là dựng abstraction cho nhu cầu chưa tồn tại — đúng thứ
mục T của đề bài cấm.

⇒ **Batch 1 chuẩn hoá đúng một primitive.** Cái tiếp theo chỉ làm khi có số đo.
