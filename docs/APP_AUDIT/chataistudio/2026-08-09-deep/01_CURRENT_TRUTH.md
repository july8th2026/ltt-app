# A1 — Current Truth

## Chuỗi thật

`browser → POST /send multipart → DB save user + credit hold 3 → sidecar thread/turn SSE → text/image event → incremental image hold 20 → DB/Storage save → settle/refund → reload/search/export/branch`.

## Năng lực LIVE

- Conversation/message per-user; search title/content; delete, branch, export MD/JSON.
- Hai public mode label, custom instruction/model stored ở conversation; engine ID được giấu khỏi UI.
- SSE streaming, Stop bằng AbortController; partial text được save/settle, zero-output refund.
- Tối đa 3 file × 8 MB: image được validate/normalize; text/JSON/PDF extract context; uploaded/generated image owner-scoped.
- Giá phẳng 3 credit/text + 20 credit/image; giữ thêm trước mỗi ảnh, cap 4; không cho balance âm.
- UI có suggestions, timestamps, token detail, live title/balance, responsive và privacy note.

## Sự thật bị che bởi happy-path

- `branch_conv` clone DB rows nhưng tạo thread sidecar mới và không replay/fork history: UI có quá khứ, AI không có quá khứ.
- `codex_thread_id` là state sidecar; khi mất/invalid không có rebuild từ DB dù UI gọi conversation “bền vững”.
- Mỗi turn chỉ hold 3; sidecar có thể phát tối đa 4 ảnh và tự hold thêm tới tổng 83 credit, không có quote/count/confirm trước send.
- Error/Stop sau partial settle tiền nhưng SSE error không trả receipt; frontend còn append `0 token · 0 credit`, balance/header stale.
- Streaming không có server deadline, idempotency key, per-conversation serialization hay chat-run record. Process crash có thể để hold không có Job/reconciler.
- Xóa conversation chỉ xóa DB, không xóa image object hay remote sidecar thread. Browser fixture đã chứng minh PNG còn trên disk sau confirm delete.
- Attachment text được lưu nguyên phần extracted vào `ChatMessage.content`; lúc submit UI chỉ hiện “Phân tích tệp”, reload bung nội dung file. Disclosure không nói rõ text/PDF được lưu trong transcript.
- Output sidecar image dùng `abs_path`; web mở/read toàn file mà không khóa root, magic, pixel/byte cap.
- App thương mại dùng một ChatGPT/Codex account chung. Tài liệu official phân biệt subscription và API; account policy nói tài khoản cá nhân dành cho người tạo; repo không có bằng chứng quyền dùng mô hình shared subscription cho end users.

Rollback audit: revert commit H27.7; runtime không đổi.
