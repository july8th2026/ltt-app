# 02 — Thiết kế lại giao diện theo style tham chiếu

**Đầu vào:** ảnh giao diện tổng quan do chủ sản phẩm cung cấp (E0).
**Chuẩn ràng buộc:** `docs/DESIGN_SYSTEM_LTT.md`, Q61 (chiều rộng trang),
`docs/QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md`.

## 1. Điều cần nói trước

Ảnh tham chiếu **không phải một style mới**. `DESIGN_SYSTEM_LTT.md` mục 1 đã
chốt từ trước: *"nền carbon gần đen, điểm nhấn đỏ LTT, chữ trung tính"*. Ảnh của
chủ sản phẩm chính là hệ thống thiết kế đó được áp đúng.

Điều đó đổi bản chất công việc: đây **không phải "đổi theo ý thích"** mà là
**sửa một vi phạm chuẩn**. App OMMI hiện tại dùng nền sáng — lệch khỏi chính
design system của nền tảng. Lập luận này quan trọng vì nó cho phép làm ngay,
không cần một quyết định Q mới về thẩm mỹ.

Cái *thật sự* mới trong ảnh là **kiến trúc thông tin**: sidebar phân nhóm +
dashboard, thay cho wizard 5 bước. Phần đó cần khóa bằng quyết định.

## 2. Đọc ảnh tham chiếu — cái gì suy ra được, cái gì không

| Thấy trong ảnh | Suy ra được gì | Cảnh báo |
|---|---|---|
| Sidebar 4 nhóm, 13 mục | IA đích | — |
| 6 ô số (Dự án 9, Tài nguyên 178, Kịch bản 97, Video 2, Meta Director 10, Thư mục 1) | Cần API đếm theo `owner_id` | Số trong ảnh là **giả lập**, không phải dữ liệu thật |
| "Tổng chi phí team hôm nay $10.40 / $0.00", "Team tháng này $144.29 / $1,000" | Cần màn chi phí | **Đơn vị USD và khái niệm "team" trái Q31** (1 credit = 100đ, tính theo user). Phải đổi sang credit và theo cá nhân |
| "LTT Studios Team Pro · ID: TEAM-LTT-001" | — | Khái niệm team/gói chưa tồn tại trong nền tảng. **Không dựng.** |
| "Nhật ký vận hành (toàn team)" | Cần activity feed | "toàn team" phải thành "của tôi" |
| Thanh tiến trình ngân sách | Có ích | Map sang credit đã dùng/hạn mức tự đặt |

**Ba chỗ trong ảnh không được sao chép nguyên**: đơn vị tiền USD, khái niệm
team, và dữ liệu "toàn team". Sao chép nguyên sẽ tạo một mô hình kinh doanh thứ
hai mâu thuẫn Q31 và làm rò rỉ dữ liệu giữa khách hàng.

## 3. Kiến trúc thông tin đích

Ảnh có 13 mục. Tôi giữ nguyên bố cục nhưng sửa 3 chỗ nói trên, và ghép "Kịch
bản" + "Studio kịch bản" vì trong module nguồn chúng là một miền (brief →
director).

```
┌─ WORKSPACE ─────────────────┐
│  Tổng quan          (mới)   │
│  Dự án                      │
├─ DỰ ÁN GẦN ĐÂY ─────────────┤
│  <5 project mở gần nhất>    │
├─ LÀM VIỆC ──────────────────┤
│  Kho tài nguyên     (mới)   │
│  Brief & Director           │
│  Storyboard                 │
│  Tạo ảnh            (đặt hàng)
│  Xuất prompt                │
├─ THƯ VIỆN ──────────────────┤
│  Prompt Library     (mới)   │
│  Phong cách         (mới)   │
│  Meta Director      (mới)   │
├─ TÀI KHOẢN ─────────────────┤
│  Chi phí & credit   (mới)   │
│  Cài đặt                    │
└─────────────────────────────┘
```

Chiều rộng theo Q61: mode `immersive` 1800px cho Storyboard và Kho tài nguyên;
`wide` 1600px cho Dashboard/Library; `standard` 1180px cho Cài đặt.

## 4. Từng màn — nội dung cụ thể (phần bạn chưa nghiên cứu được)

Mỗi màn dưới đây suy ra từ **năng lực có thật trong module nguồn**, không phải
bịa cho đầy.

### 4.1 Tổng quan

- Dải credit: đã dùng hôm nay / tháng này, hạn mức tự đặt, nút `Nạp thêm`.
  **Đơn vị credit, phạm vi cá nhân.**
- 5 ô đếm: Dự án · Tài nguyên · Cảnh · Storyboard · Meta prompt. (Bỏ ô "Thư mục"
  vì Q65 đã DEFER cây thư mục; bỏ "Video" cho tới khi handoff video chạy thật.)
- `Phân loại tài nguyên`: character / background / prop / vehicle / misc —
  đúng 5 `kind` trong lược đồ.
- `Dự án gần đây` (bảng: tên, revision, số cảnh, sửa lần cuối).
- `Hoạt động của tôi`: feed từ job + revision, **không phải "toàn team"**.
- Empty state thật: người mới thấy 3 bước bắt đầu, không thấy ô số 0 vô nghĩa.

### 4.2 Kho tài nguyên — màn quan trọng nhất

Nguồn có 1.828 dòng cho miền này; app hiện có **một nút text**.

- Lưới thẻ ảnh, lọc theo `kind`, tag, và "đang dùng ở project nào".
- Mỗi tài nguyên: nhiều `variant` ảnh, tag, mô tả, ghi chú prompt.
- Upload nhiều file; ảnh lớn đi **presigned R2**, không qua origin (giới hạn
  Cloudflare 100 MB).
- `Collection` để gom bộ nhân vật/bối cảnh dùng lại.
- Panel chi tiết: xem variant, đặt variant chính, xem "dùng ở 4 cảnh".
- **Tất cả PRIVATE.** Không có kho chung.

### 4.3 Brief & Director

Giữ gần như bước 01+03 hiện tại (phần này codex làm đúng), thêm:
- Chọn tài nguyên từ Kho thay vì gõ text.
- Chọn meta prompt và phong cách từ Thư viện.
- Lịch sử iteration: chạy lại một cảnh mà không chạy lại cả gói.

### 4.4 Storyboard

- Lưới cảnh, mỗi cảnh có ảnh, prompt, camera, continuity, phiên bản.
- Chọn `framework` (khung storyboard) từ CATALOG.
- Đặt hàng ảnh cho từng cảnh hoặc hàng loạt → job, quote trước.
- So sánh phiên bản cảnh.

### 4.5 Prompt Library / Phong cách / Meta Director

Ba màn cùng khuôn: danh sách PRIVATE của tôi + tab CATALOG mẫu (chỉ đọc) với
nút `Dùng mẫu này` tạo bản sao riêng. Có version + diff.

### 4.6 Chi phí & credit

Không dựng sổ tiền thứ hai. Đọc từ sổ credit nền tảng, hiển thị theo app/job/
thời gian. Đây là chỗ ảnh tham chiếu dễ dẫn ta đi sai nhất.

## 5. Cách làm giao diện — quyết định kỹ thuật cần khóa

App hiện tại là template Jinja + JS thuần (189 dòng HTML). Kho tài nguyên,
storyboard và dashboard là giao diện trạng thái nặng.

| Phương án | Ưu | Nhược |
|---|---|---|
| **A. Giữ Jinja + JS thuần** | không thêm hạ tầng | 13 màn trạng thái nặng bằng JS thuần sẽ thành mớ khó bảo trì |
| **B. React + Vite như agent-canvas / autosub-studio** *(đề xuất)* | đã có khuôn mẫu, có build gate, prebuilt bundle, không cần Node trên máy chủ | thêm một bundle nữa |

Đề xuất **B**: nền tảng đã có **hai** tiền lệ (`frontend/agent-canvas`,
`frontend/autosub-studio`) với đủ typecheck/test/build-meta/verify. Làm cái thứ
ba là đi theo lối đã mòn, không phải phát minh.

## 6. Gate nghiệm thu giao diện

Theo `QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md` và LTT-AQA:
- Token lấy từ design system, **không hardcode màu**.
- 390 / 768 / 1366 / 1920 không tràn ngang.
- Mọi control có empty / loading / error / disabled / success.
- WCAG 2.2 AA cho luồng lõi; focus nhìn thấy được; touch ≥ 44px.
- Browser thật desktop + mobile, console 0 error, network 2xx.
- **Kiểm trên URL công khai**, không chỉ loopback (CLAUDE.md 5b).
