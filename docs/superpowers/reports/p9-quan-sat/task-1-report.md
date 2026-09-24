# P9 Task 1 — SSE cho run đang chạy

## Nguồn đã tra
- `pip show sse-starlette` → not found; grep `requirements*.txt` → không có. Plan chốt "dùng lại sse-starlette" nhưng gói chưa từng được cài trong kho này.
- Kho ĐÃ có 2 cửa `StreamingResponse(..., media_type="text/event-stream")` thuần chạy thật: `apps/agent/routes/assistant.py:130` (SSE phân tích Assistant) và `server/api/streaming.py:949,1081` (SSE chat LLM) → dùng lại NGUYÊN khuôn đó thay vì thêm dependency mới cho cùng một việc (xem docstring đầu `runs_v3.py`, mục "SSE (P9 task 1)").
- MDN `EventSource`: gửi `Last-Event-ID` khi tự nối lại — dùng thẳng cơ chế này thay vì tự viết logic reconnect ở frontend.

## Đỏ → xanh
```
tests/test_3420_wf_v3_run_sse.py       404 Not Found (route chưa có) → 2 passed, 9.47s
```
Đối chứng thời gian thật: writer thread ghi `su_kien` mới + chuyển `RUNNING`→`SUCCEEDED` ở các mốc 1.3s/2.6s — server poll 1s/lần, tick thật, không giả lập đồng hồ.

## Đã làm
- `GET /agent/api/v3/runs/{run_id}/su-kien`: poll DB 1s, đóng chủ động ở 90s (dưới trần Cloudflare 100s), đóng NGAY khi run vào `RUN_KET_THUC` thay vì chờ hết 90s.
- `Last-Event-ID` (header EventSource tự gắn) thắng `?sau=` khi cả hai có mặt.
- Cửa CỐ Ý là `GET` thuần để frontend dùng `EventSource` gốc, né đúng nợ đã khai (`previewAssistant` tự `fetch()` qua `apiFetch()` gắn sai `Accept: application/json` cho luồng SSE).

## Đo được (môi trường)
`starlette.testclient.TestClient` (khuôn httpx cũ, cảnh báo deprecated) KHÔNG stream progressively tới client — đo bằng app 3-khung/1s: khung đầu chỉ tới sau ~3.03s (gộp cả 3). Test phải dựa vào *server chạy real-time* + đọc buffer cuối, không dựa vào "client thấy khung ngay".

## Chưa làm được
- Frontend (`CanvasShell.tsx`) VẪN dùng polling `setTimeout`+`loadRunV3` cũ, CHƯA chuyển sang `EventSource`. Cân nhắc rồi hoãn có chủ ý: effect polling hiện tại có backoff (`soHong`)/race-guard (`active`) tinh vi, một lần viết lại xứng đáng phép kiểm trình duyệt riêng — ngân sách phiên này ưu tiên task 3 (🔴). Backend SSE độc lập, đã test đầy đủ, sẵn sàng để lần sau nối dây.
