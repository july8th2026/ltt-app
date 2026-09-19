# A2–A3 — Journey và Control Registry

| Screen/control | Verdict trước | Contract sau H26.10B |
|---|---|---|
| Chế độ + hội thoại mới | PARTIAL | LIVE; nhãn kết quả High quality/Fast, ID chỉ là value backend |
| Search/open/delete | LIVE | owner-scoped; delete có confirm; title cập nhật sau lượt đầu |
| Empty state | PARTIAL | ba gợi ý có thể nạp thẳng composer |
| Attach | LIVE | hiện số lượng + tên tệp; giới hạn/MIME giữ nguyên |
| Send SSE | PARTIAL | LIVE; busy/success/warning/error, title/credit cập nhật |
| Stop | MISSING | LIVE; AbortController; backend settle partial hoặc refund zero output |
| Image output | MISLEADING/G3 | giữ thêm 20 credit trước mỗi ảnh; thiếu thì bỏ ảnh, giữ text, không âm |
| Lịch sử lượt | PARTIAL | timestamp; assistant trace token/credit ở lượt mới; DB + ledger bền |
| Export/branch | LIVE nhưng dày | gom trong menu thao tác, contract giữ nguyên |
| Admin sidecar | LIVE operator-only | không đưa credential/capability kỹ thuật ra customer UI |

Browser 2026-08-09: fixture 8112, provider giả nhưng route/SSE/DB/credit thật.
Desktop send 200, 100→97, 12 token; reload còn 2 message và trace. Mobile 390
không overflow. Console 0 error/0 warning; failed network 0. Dừng có contract
source/regression; stream fixture kết thúc quá nhanh nên chưa timing-test nút này.

