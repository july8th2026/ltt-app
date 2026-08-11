# Quality Lab — production deployment 2026-08-11

## Kết quả

- Target: `C:\LTTPlatform`, public `https://app.lttstudios.com`.
- Release archive: `dist/release-20260811-h31/ltt-release-1.0.0.zip`.
- SHA-256: `ebd4a73156e2e31bf3ec9d90d17aa5d9f7ef15a3d7f1b84c4bfc192dac36f0ea`.
- Archive có 1.610 file, 83,5 MB; source secret scan 0 finding.
- Deploy `EXITCODE=0`; chưa cần rollback.

## Preflight và thay đổi production

- Full gate trước build PASS 9/9; pytest 1.831,4 giây.
- Trước deploy, Web/Worker/Codex đều Running và health local/public ready.
- `update.ps1` tạo backup, dừng service, giữ release cũ tại `app.previous`,
  giải nén release mới, giữ protected config, cập nhật dependency, giữ sidecar
  WhisperX CUDA khỏe, chạy Alembic và khởi động lại dịch vụ.
- Backup được tạo tại
  `C:\LTTPlatform\backups\ltt_data_20260811_083857.zip`.
- Alembic sau deploy: `f4a5b6c7d8e9 (head)`.

## Hậu kiểm

- `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioCodex`: Running/Automatic.
- Local và public `/health/ready`: ready, production, database ok.
- Local và public `/health/version`: `v1.0`.
- Hash production khớp source cho calibration, materializer, hai CLI và runbook
  dataset.
- Playwright desktop 1440 px và mobile 390 px: landing render đúng, horizontal
  overflow false, console error 0, request app thất bại 0.
- `/qualitylab` ở localhost trả 303 đến `/login?next=/qualitylab`, đúng boundary
  operator/auth. Public automation gặp Cloudflare challenge 403 tại trang login;
  các lỗi console/network ở bước đó thuộc challenge Cloudflare, không phải
  request handler LTT. Không tạo production user chỉ để vượt challenge.
- Log JSONL sau restart không có server error; worker ghi đúng sự kiện startup.

## Đường lùi

Nếu core smoke hoặc health phát sinh lỗi sau nghiệm thu, chạy
`deploy/windows/rollback.ps1`. Release trước còn ở
`C:\LTTPlatform\app.previous`; không restore database nếu chưa xác định migration
hoặc dữ liệu là nguyên nhân.

## Giới hạn không được hiểu thành PASS giả

Deployment chỉ phát hành code đã kiểm. H31.3d2b vẫn thiếu dataset thực tế có
license evidence và H31.3d3 vẫn thiếu ba rater thật/case; các metric chưa hiệu
chuẩn tiếp tục UNKNOWN và không được dùng làm release gate.
