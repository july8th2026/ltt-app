# 03 — Lộ trình triển khai

Nguyên tắc LTT-AQA A7: không build-all. Thứ tự
`Repair → Parity chọn lọc → Differentiation`.

## Điều phải quyết trước khi viết dòng code nào

Audit không được tự chuyển thành BUILD (quy tắc mục 1 và A8). Bốn câu hỏi khóa
logic nằm ở cuối tài liệu này.

## R0 — Chặn rủi ro và dọn nền (bắt buộc trước tiên)

- Kiểm production đã có project OMMI thật nào chưa. Có thì viết migration; không
  thì được phép đổi lược đồ tự do.
- Viết test cross-user 404 làm **khuôn mẫu** trước, áp cho mọi endpoint sau này.
- Chốt lược đồ 12 bảng + migration alembic đầu tiên.

**PASS:** migration lên/xuống chạy sạch; test cross-user đỏ khi cố tình bỏ
`owner_id`.

## R1 — Kho tài nguyên riêng (giá trị lớn nhất, rủi ro lớn nhất)

Đây là thứ chủ sản phẩm nhấn mạnh và là thứ nguồn **chưa từng có**.

- `ommi_resource` + `variant` + `tag` + `collection`, tất cả PRIVATE.
- Upload qua presigned R2; thumbnail sinh bằng job.
- Màn Kho tài nguyên: lưới, lọc, chi tiết, collection.
- Nối vào Brief & Director thay cho ô text hiện tại.

**PASS:** user B không thấy/không sửa được gì của user A (test + browser thật);
upload 1 ảnh 60 MB không đụng giới hạn Cloudflare; kho 200 tài nguyên phân trang
mượt.

## R2 — Thư viện prompt / phong cách / meta riêng

- Ba bảng PRIVATE + tầng CATALOG do admin publish.
- Version + diff.
- Nút `Dùng mẫu này` → clone thành bản riêng.

**PASS:** clone tạo bản mới thuộc về người dùng; sửa bản clone không đụng
catalog; user thường không publish được vào catalog.

## R3 — Storyboard workspace thật

- `ommi_scene` / `ommi_storyboard` + version.
- Chạy lại một cảnh, so sánh phiên bản.
- Đặt hàng ảnh theo cảnh hoặc hàng loạt qua job + quote.

**PASS:** chạy lại 1 cảnh không tính tiền cả gói; hủy giữa chừng hoàn credit
đúng; reload giữ nguyên tiến độ.

## R4 — Giao diện theo design system

- Chuyển sang React/Vite theo khuôn `agent-canvas`.
- Sidebar 4 nhóm + Dashboard + 13 màn.
- Nền carbon, đỏ LTT, token từ design system.

**PASS:** gate mục 6 của `02_THIET_KE_GIAO_DIEN.md`.

## R5 — Chi phí, vận hành, phát hành

- Màn Chi phí đọc từ sổ credit (không dựng sổ thứ hai).
- Runbook, log, rollback.
- LTT-AQA G0–G8 + full gate + kiểm URL công khai.

## Ước lượng và thứ tự

| Phase | Khối lượng tương đối | Phụ thuộc |
|---|---|---|
| R0 | nhỏ | — |
| R1 | **lớn nhất** | R0 |
| R2 | trung bình | R0 |
| R3 | lớn | R1, R2 |
| R4 | lớn | R1 (làm song song từng màn) |
| R5 | nhỏ | tất cả |

Không hứa ngày. Mỗi phase có gate riêng và chỉ tick khi gate xanh — đúng bài học
từ H19.3/H19.4 đã tick nhưng phạm vi thực tế hẹp hơn tên gọi.

## Quan hệ với H19 đang có trong kế hoạch

Lộ trình này **không thay** H19 mà làm rõ nó. Ánh xạ:

| H19 hiện có | Tương ứng |
|---|---|
| H19.5 P3 consistency/iteration/storyboard/version | R3 |
| H19.6 P4 private library + published Admin catalog | **R1 + R2** — phần lớn nhất, đang `[ ]` |
| H19.8 P6 batch/recovery/metrics/retention | R5 |
| H19.9 P7 Carbon Red immersive UI | R4 |
| H19.10 P8 parity ≥90% + G0–G8 | R5 |

Đề xuất: giữ nguyên số hiệu H19.x, viết lại phần mô tả cho khớp phạm vi thật.

## Bốn câu hỏi cần chủ sản phẩm khóa

1. **Kho tài nguyên có tầng dùng chung không?** Đề xuất: KHÔNG ở v1 — chỉ
   PRIVATE + CATALOG do admin. Thêm team sau nếu cần.
2. **Giao diện: React/Vite (như agent-canvas) hay giữ Jinja+JS?** Đề xuất:
   React/Vite.
3. **"Tạo ảnh" trong app là đặt hàng qua `image.generate`, hay OMMI tự sinh?**
   Đề xuất: đặt hàng — đúng Q65, không dựng engine thứ hai.
4. **Có giữ khái niệm "team/gói Pro" như trong ảnh không?** Đề xuất: KHÔNG —
   nền tảng chưa có mô hình team, và ảnh dùng USD trái Q31 (credit).
