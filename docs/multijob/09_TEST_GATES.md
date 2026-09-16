# 09 — Cổng kiểm (không cần GPU trước, GPU sau)

> Tuân `CLAUDE.md` quy tắc 4 + trần `-n 6` + `cua_so_yen` trước lệnh nặng. Phép kiểm mới nằm trong dải
> test được cấp (xem `docs/` bảng cấp phát — **đọc bảng, đừng suy từ số tệp đang có**). Mỗi phép kiểm
> bất biến phải có **đối chứng: tiêm bản cũ xem có ĐỎ không** (memory "số 0 cần đối chứng").

## A. Không GPU (SQLite + PostgreSQL thật cho race + provider giả)

| Ca | Bất biến | Đối chứng |
|---|---|---|
| A1 Σ đặt chỗ | không bao giờ nhận khi `Σ token_dat_truoc + mới > POOL` | tiêm luật bỏ vế ngân sách ⇒ đỏ |
| A2 slot | không quá N lease sống | — |
| A3 lớp nền | nền ≤ N−1; có người tương tác chờ ⇒ nền bị từ chối | tiêm bỏ vế 3 ⇒ đỏ |
| A4 whale | ≤1 whale; whale chờ tương tác tối đa `CHO_WHALE_TOI_DA` rồi thành chặn; không bỏ đói | đồng hồ tiêm (không `sleep` thật — memory "tiêm nửa đối tượng") |
| A5 tài khoản | trần `ceil(N/2)` chỉ khi có người khác chờ | — |
| A6 FCFS chặt | đầu hàng lớn chưa vừa ⇒ người sau chờ | — |
| A7 race | 100 request đồng thời nhiều tiến trình (PostgreSQL, khuôn `test_73`/`test_214`) ⇒ không vượt pool/slot | — |
| A8 tiền — INV-MJ-1 | request đang chờ **không** có dòng giữ tiền | tiêm giữ-trước-chờ ⇒ đỏ |
| A9 tiền — INV-MJ-2 | hết trần chờ / client ngắt khi chờ ⇒ 0 khoản treo, 0 thu | — |
| A10 HTTP stream thật (`TestClient`, khuôn `test_272`) | 402 và 429-phòng-đầy trả **trước** 200; hết trần ⇒ sự kiện lỗi đúng khuôn Anthropic/OpenAI | — (bài học `test_385`: kiểm qua HTTP, không hàm thuần) |
| A11 hủy job | `POST /cancel` ⇒ kết nối tới provider giả bị **đóng** trong ≤ 2 s | — |
| A12 gateway | `GioiHan` N slot + sổ token đúng + ≤1 whale; 429 ≠ 502; **không** gửi `X-Conversation-Id` | — |
| A13 một nguồn | `test_334` mở rộng: `--parallel`/`-kvu`/`--mmproj`/UUID trong yaml khớp `ngan_sach.py` | đổi một bên ⇒ đỏ |
| A14 hồi quy | `test_313`, `test_363`, `test_389`, `test_250`, `test_252`, `test_68`, `test_272` xanh | — |

Nhịp test/gate: `docs/00_LTT_OPERATING_CONTRACT.md` §4 — không chép lại ở đây.
Trước lượt L3: kiểm `loi_cho_bo_test` có trong `tools\gate.py` của cây.

## B. Có GPU — máy B, qua ĐƯỜNG PRODUCTION (pha 2, D-10 A)

Khuôn đo = `docs/multijob/artifacts/m1/m1_bench.py` (Scheduled Task + pythonw + nhịp tim + nhường production).

| Ca | Ngưỡng (TD-14) |
|---|---|
| B1 C1 | decode ≥ 54 tok/s |
| B2 C4 | tổng ≥ 100 tok/s |
| B3 whale 60K + 3 người mới | người mới được nhận sau whale theo luật; không ai bị 5xx |
| B4 cố tình vượt ngân sách (2 × 90K + max_tokens lớn) | **0** "Context size has been exceeded"; lượt thứ hai **chờ** rồi chạy |
| B5 ảnh + 3 text | 200, trả lời đúng; VRAM đỉnh ghi lại |
| B6 hủy giữa chừng (stream + job) | slot trống lại ≤ 2 s (`/slots`) |
| B7 soak 30 phút tải hỗn hợp | 0 OOM/crash; `requests_deferred` = 0; 0 khoản treo |
| B8 canary client thật | Codex CLI + Claude Code qua Cloudflare: một vòng tool khép kín; một lần hết-trần-chờ được client xử lý có nghĩa |
