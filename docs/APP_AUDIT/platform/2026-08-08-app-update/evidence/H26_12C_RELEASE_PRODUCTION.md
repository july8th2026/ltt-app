# H26.12C — Canary và phát hành production

**Ngày:** 2026-08-09  
**Public URL:** `https://app.lttstudios.com`  
**Kết quả:** PASS, release class `PUBLIC`

## Artifact

- File: `dist/ltt-release-1.0.0.zip`
- Số file: 1.404
- Kích thước: 78,7 MB
- SHA-256:
  `8148becd1342a6685caa6fa93069d7dae8d9ce502f289d37d2b6731501890750`
- Source secret scan: 0 finding.

## Canary từ đúng archive phát hành

Archive được giải nén vào thư mục cô lập, dùng database/storage/provider giả và
chạy tại cổng 8122. Không dùng source checkout để thay thế canary artifact.

| Kiểm tra | Kết quả |
|---|---|
| 11 route customer desktop | 11/11 status 200, không overflow, console/network app error 0 |
| 11 route customer mobile | 11/11 status 200, không overflow, console/network app error 0 |
| Tạo ảnh live polling | queued → done + ảnh sau 3 poll |
| Credit Tạo ảnh | 100 → 95, đúng quote/settle |

Canary process được dừng sau khi PASS; dữ liệu cô lập không đưa vào production.

## Deploy

- Chạy wrapper hai lớp theo quy tắc Windows: lớp ngoài nâng quyền; lớp trong
  redirect stdout/stderr và ghi `EXITCODE`.
- `EXITCODE=0`; hash artifact trong deploy summary khớp SHA-256 ở trên.
- Deploy đã backup local production, dừng đủ service, rotate app, giải nén,
  giữ protected config, cài dependency, kiểm WhisperX, chạy Alembic và khởi
  động lại service.
- `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioCodex`: `RUNNING` qua
  `sc.exe query`, exit code 0.
- Local và public `/health/ready`: `status=ready`, `environment=production`.
- Public build version: `v1.0`.
- Hash production khớp source cho image template, `ltt.css` và rollback script.

## Browser sau deploy

- Landing public mở thật, không horizontal overflow.
- Register trả 200, widget Turnstile render và sinh response token. Console có
  WebGL/PAT 401 từ iframe Cloudflare; đây là request third-party của challenge,
  không phải request app hỏng và widget vẫn hoàn thành.
- Public profile không có authenticated test session lưu sẵn nên không tạo hay
  sửa production user chỉ để tăng evidence. Authenticated A-Z được chứng minh
  trên đúng archive canary; production hash của các file thay đổi khớp archive.

Giới hạn trên làm E giữ ở 80 và release class giữ `PUBLIC`, không nâng giả lên
`COMMERCIAL`.

## Gate và đường lùi

- Full `python tools/gate.py`: PASS 9/9 trước khi build; pytest 1.596,9 giây.
- Backup predeploy:
  `D:\LTTBackups\ltt_data_h26_predeploy_20260809_113515.zip`; 4 entry, có DB
  dump và protected environment. Retention đã prune bản cũ ngày 2026-08-02.
- Restore rehearsal cô lập: PASS 4 entry, không chạm live data.
- Rollback rehearsal: PASS 3/3; script điều khiển đủ Web/Worker/Codex và chỉ
  chấp nhận readiness `status=ready`.
- Nếu production health hoặc core smoke thất bại: dùng artifact/backup trên và
  `deploy/windows/rollback.ps1`; không restore live database nếu chưa xác định
  migration/data là nguyên nhân.
