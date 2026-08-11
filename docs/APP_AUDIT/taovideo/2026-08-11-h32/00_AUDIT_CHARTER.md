# H32.5 — Audit charter: Tạo Video Seedance

- **Ngày:** 2026-08-11.
- **Mode:** STANDARD giới hạn visual/control; kế thừa deep audit 2026-08-09.
- **Persona:** khách hàng sáng tạo nội dung, không phải developer.
- **JTBD:** mô tả và gắn tài sản tham chiếu; hiểu model/thiết lập/chi phí; theo
  dõi, xem, tải, remix hoặc chuyển output sang Upscale.
- **Nguồn yêu cầu:** `TaoVideoSeedance/MoTa.txt` và `GiaoDien.png` 1.586×992,
  SHA-256 `D3F691FE...4DA2032`.
- **Môi trường:** fixture cô lập `127.0.0.1:8144`, SQLite/storage/user/credit
  riêng. Production 8100 không bị tác động.
- **Ranh giới bắt buộc:** không start worker, không submit job, không gọi
  BytePlus/ModelArk, không tiêu credit. MP4 fixture chỉ để kiểm player/layout,
  không phải output Seedance.
- **Viewports:** 1.586×992 và 390×844; VI/EN.

## Tiêu chí PASS H32.5

1. Chỉ giữ CTA có backend thật; không sao chép nút Delete/Retry/template từ ảnh
   nếu contract chưa tồn tại.
2. Model/prompt/reference/setup/quote và history có hierarchy rõ; CTA trả phí
   không khuất khỏi panel.
3. Grid/list/filter/status/error/empty/loading hoạt động trên UI thật.
4. Mobile không overflow; composer đóng không nhận focus; có đường mở/đóng rõ.
5. Console sạch và request app không lỗi trong vòng final; negative quote 500
   phải khóa CTA và hiện lỗi an toàn.

Rollback: revert commit H32.5; xóa fixture/evidence 8144. Không có migration hay
thay đổi dữ liệu production.
