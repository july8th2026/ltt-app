# 00 — Audit charter: Socialbot maintenance

- **Ngày snapshot:** 2026-08-09
- **Mode:** DEEP, audit-only; không sửa app đã đóng băng theo Q10.
- **Phiên bản/phạm vi:** `apps/socialbot`, các route lịch sử ở `server/routes/*`,
  runner riêng, token store Facebook/TikTok và giao diện web local fixture.
- **Persona hợp lệ:** operator nội bộ quản lý tài khoản/kênh của LTT; **không**
  phải mọi khách hàng SaaS đã đăng nhập.
- **JTBD:** kết nối tài khoản; chuẩn bị/đăng nội dung; vận hành queue và chẩn
  đoán lỗi token/API.
- **Môi trường/dữ liệu:** local cô lập `127.0.0.1:8112`, tài khoản customer test,
  token store rỗng; không gọi provider, không dùng production data.
- **Trọng số:** chuyển 8 điểm AI sang Security +4, Operations +4 vì đây là
  automation không sinh AI. Tổng vẫn 100.
- **Budget:** browser desktop 1440×900; latency/load/provider production là
  UNKNOWN.
- **Ranh giới:** benchmark theo công cụ social publishing/approval, nhưng Q10
  chỉ cho phép maintenance/security, không mở feature build.

**G0 PASS.** Sản phẩm này chỉ hợp lệ khi là công cụ operator cô lập.

