# Evidence index

- E1: source/manifests/routes/templates/models tại commit snapshot của audit.
- E3: Playwright session `ltt`, local 8100, 2026-08-08; catalog public render,
  console 0 error/0 warning, không có failed request bất ngờ.
- E0/E4 input chủ sản phẩm: ảnh và `MoTa.txt` nằm ngoài repo tại
  `C:\Users\Thang Tuong\Desktop\AppLttStudio_Update_08082025`; không copy vào
  repo để tránh nhân đôi asset. Danh mục được ghi ở `01_CURRENT_TRUTH.md`.
- Hardware: `nvidia-smi` thấy 2 RTX 5060 Ti, mỗi card 16.311 MiB; không chứa dữ
  liệu nhạy cảm.

Chưa có: authenticated browser journey từng app, competitor benchmark, user
test và production telemetry của scope H26. Những mục này không được nâng từ
UNKNOWN thành PASS chỉ dựa trên roadmap.
