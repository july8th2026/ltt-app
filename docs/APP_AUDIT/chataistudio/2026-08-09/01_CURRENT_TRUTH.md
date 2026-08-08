# A1 — Current truth

- `chataistudio` public/development; SSE chạy trong web qua sidecar loopback,
  cố ý không khai `job_types` và không giả chat thành Job.
- `ChatConversation`/`ChatMessage` owner-scoped lưu title, model, instruction,
  thread, content/image, token và timestamp. Credit ledger append-only dùng ID
  tin user làm hold/settle/refund correlation.
- Giá: 3 credit/lượt chữ, 20 credit/ảnh, tối đa 4 ảnh/lượt.
- Upload: tối đa 3 tệp × 8 MB; ảnh được validate/normalize; text/PDF trích tối đa
  12.000 ký tự; storage key có user/conv và route ảnh kiểm owner.
- Lịch sử/search/export/branch đã có và có test owner isolation.
- Trước H26.10B chỉ giữ 3 credit; ảnh phát sinh được giao trước khi giữ thêm,
  nên settle có thể làm âm. Partial stream khi lỗi/ngắt cũng có thể không được
  lưu. Đây là G3/G5 blocker, không phải lỗi trang trí.
- Rollback: revert commit H26.10B; không migration/schema/provider change.

