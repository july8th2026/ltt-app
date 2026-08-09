# Evidence index

- E1: source/manifests/routes/templates/models tại commit snapshot của audit.
- E3: Playwright session `ltt`, local/canary, 2026-08-08 đến 2026-08-09;
  authenticated journey theo phase app, desktop/mobile route matrix, console
  và failed application request bất ngờ = 0.
- E0/E4 input chủ sản phẩm: ảnh và `MoTa.txt` nằm ngoài repo tại
  `C:\Users\Thang Tuong\Desktop\AppLttStudio_Update_08082025`; không copy vào
  repo để tránh nhân đôi asset. Danh mục được ghi ở `01_CURRENT_TRUTH.md`.
- Hardware: `nvidia-smi` thấy 2 RTX 5060 Ti, mỗi card 16.311 MiB; không chứa dữ
  liệu nhạy cảm.
- E4: archive canary 22/22 route, output/credit Tạo ảnh, production
  health/build/service state, backup/restore/rollback và deploy `EXITCODE=0`;
  xem `H26_12C_RELEASE_PRODUCTION.md`.

Chưa có: authenticated browser journey **sau deploy trên production**, external
pentest, independent user study, trial trả phí toàn bộ benchmark và đủ mẫu
production SLO. Những mục này không được nâng evidence chỉ dựa trên roadmap.
