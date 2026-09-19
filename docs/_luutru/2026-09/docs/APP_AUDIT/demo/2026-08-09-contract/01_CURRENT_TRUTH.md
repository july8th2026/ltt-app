# 01 — Current truth

`/demo` có hai đường: POST trực tiếp gọi handler và `/queue` dùng
`submit_with_credit`; handler đảo chuỗi, báo progress 50/100 và ném lỗi khi
input rỗng. Route dùng `require_operator`; middleware trả 404 cho customer.

Browser E3 customer `/demo` = 404 đúng. Registry/route/queue/credit/worker tests
nằm trong bộ targeted 186 test đều PASS. Điểm yếu: đường direct cố ý không tạo
Job, không hold/settle/refund, nên không thể dùng nó để tuyên bố full pipeline;
template/canary không có assertion artifact download hay worker heartbeat.
Production canary, P75 và rollback rehearsal riêng cho Demo: UNKNOWN.

