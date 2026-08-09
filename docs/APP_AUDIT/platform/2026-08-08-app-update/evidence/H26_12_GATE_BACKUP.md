# H26.12 — Release gate, backup và rollback

Ngày kiểm: 2026-08-09.

## Backup/restore

- Tạo backup production trước deploy tại `D:\LTTBackups`, gồm file cấu hình,
  state cục bộ, `pg_dump -Fc` và file môi trường bảo vệ.
- Kiểm ZIP đọc được: 4 entry; có database dump và protected environment file.
- Chính sách giữ 14 bản đã tự prune bản cũ nhất ngày 2026-08-02.
- `restore.ps1` rehearsal giải nén đủ 4 entry vào thư mục test dưới
  `C:\LTTPlatform`; không dùng `-Live`, không sửa dữ liệu đang chạy.

Không ghi giá trị secret hoặc nội dung dump vào evidence.

## Rollback release

- Audit bắt gap: update dừng Web/Worker/Codex nhưng rollback bỏ Codex và chỉ
  cần HTTP trả lời, chưa bắt `status=ready`.
- Rollback nay điều khiển đủ ba service và xác minh readiness chính xác.
- Thêm `-SkipServiceControl` chỉ cho rehearsal xoay thư mục cô lập.
- Rehearsal trong `tmp`: bản tốt về `app`, bản lỗi giữ ở `app.failed`,
  `app.previous` không còn; 3/3 assertion PASS.
- Deploy script regression: 48 PASS, bao gồm ASCII/no-BOM contract.

## Full release gate

`python tools\gate.py` được chạy đúng một lần sau mọi thay đổi H26.12B, log giữ
ở `tmp/h26-final-gate.out.log`:

- secret scan: PASS;
- app contract lint: PASS;
- undefined-name scan: PASS;
- silent-exception scan: PASS;
- i18n ratchet: PASS;
- Agent Canvas frontend: PASS;
- AutoSub frontend: PASS;
- Prompt AI frontend: PASS;
- pytest: PASS trong 1.596,9 giây;
- tổng: **PASS 9/9**.

H26.12B đủ điều kiện chuyển sang build/canary. Chưa deploy tại thời điểm ghi.
