# H32.6 — Options và quyết định

| Phương án | Giá trị | Rủi ro | Time-to-value | Điểm | Quyết định |
|---|---:|---:|---:|---:|---|
| A — chỉ polish UI | 2/5 | 2/5 | 5/5 | 55/100 | REJECT: không đóng security/quality |
| B — Repair → parity chọn lọc | 5/5 | 3/5 | 4/5 | **86/100** | KHUYẾN NGHỊ |
| C — sao chép full restoration suite leader | 5/5 | 5/5 | 1/5 | 48/100 | DEFER |

## Logic khóa theo khuyến nghị B

1. Đóng upload/lifecycle và hiệu chuẩn quality trước quảng bá thương mại.
2. Tách job type Fast/Quality để scheduler dùng VRAM hiệu quả.
3. Thêm live progress/retry/preflight confirmation; không đưa tham số dev ra
   khách hàng.
4. Chỉ BUILD denoise/deblur/temporal khi benchmark thắng baseline với cost/P95
   có thể bán được.
5. 8K, object removal, full editor và model picker chuyên sâu tiếp tục DEFER.

Không có quyết định nền tảng mới cần ghi Q-table trong phase này.

