# A0 — Audit Charter: Tạo Clip ngắn

- **Mã hồ sơ:** H27.6 / LTT-AQA v1.0 / DEEP
- **Snapshot:** 2026-08-09, development fixture cô lập tại `127.0.0.1:8132`
- **App/version:** `taoclipngan`, source hiện tại của `D:\LTTSTUDIOSAPP`
- **Persona:** creator/marketing Việt Nam cần biến video dài thành Shorts/Reels/TikTok mà không phải dựng thủ công.
- **JTBD 1:** đưa video dài vào và nhận các highlight dọc có caption, framing và chất lượng xem được.
- **JTBD 2:** hiểu trước chi phí, theo dõi xử lý, xử lý lỗi/hủy và không bị trừ tiền sai.
- **JTBD 3:** rà soát, sửa metadata/transcript, so sánh và xuất package đúng cho nền tảng.
- **Thiết bị:** desktop 1440×1000; mobile 390×844; VI và EN.
- **Dữ liệu:** file test repo `tools/3video/pages_show_list.mp4`; DB/storage fixture. Không gọi provider/GPU production, không dùng dữ liệu khách.
- **Benchmark:** OpusClip, CapCut, Adobe Premiere Pro, Descript và YouTube Shorts; chỉ claim chính thức tại ngày snapshot.
- **Ngưỡng:** core outcome thật, credit không âm/sai, upload có giới hạn xác thực, output MP4/SRT dùng được, mobile không overflow, console/network sạch; performance production giữ UNKNOWN khi không có telemetry.
- **Ranh giới:** audit/read-only; không sửa runtime, không deploy trước Decision Gate.

## Kết luận phạm vi

Charter PASS. Đây là công cụ khách hàng, không phải giao diện kỹ thuật cho dev. Hồ sơ H26 tại `../2026-08-09/` là lịch sử phát triển; hồ sơ này chấm lại độc lập theo A0–A10 và không kế thừa điểm cũ.
