# P9 Task 4 — Thử lại node · chạy lại từ node · so sánh hai run

## Trạng thái: CHƯA LÀM — không có mã, không có test

Ngân sách phiên đi hết vào task 1 (SSE, hoàn chỉnh) và task 3 (🔴, mitigation
trong ranh giới) sau khi hai việc đó nảy ra thêm việc thật (merge `main` giữa
chừng theo yêu cầu coordinator, phát sinh yêu cầu `waiting_kind` cho task 2/3).
Không muốn dựng vội task 4 — nó chạm `credit`/`jobs` (nghĩa vụ ngầm platform,
"có lưu lượng và bút toán thật... sửa được, nhưng giữ đúng sổ sách") và rush
đúng loại việc này là cách chắc nhất tạo lỗ tiền thứ hai.

## Đã tra, để lượt sau đỡ mất thời gian tra lại

- **"Thử lại node"**: KHÔNG cần schema mới. `platform_core/workflow/thu_lai.py` đã có toàn bộ chính sách retry (`doc_chinh_sach`, `con_luot`, `hen`) cho retry TỰ ĐỘNG khi job lỗi — nhưng đó khác "thử lại THỦ CÔNG" spec §14 đòi (`POST /runs/{id}/nodes/{node}/thu-lai`, kiểm hold còn đủ → 402 nếu không). Cần route mới gọi `may_trang_thai.chuyen_node(... sang="READY")` + `cau_noi.nop_job` lại, với kiểm tra hold TRƯỚC (đọc `credit.py`, chưa tra kỹ hàm kiểm hold còn lại).
- **"Chạy lại từ node"**: spec viết `workflow_run.chay_lai_tu_run_id` — tức MỘT CỘT MỚI trên `WorkflowRun`. Đây là việc thuộc `platform_core/models.py` + migration, **ngoài ranh giới** brief giao cho `p9` (⛔ "KHÔNG chạm models.py, mọi migration"). Phương án né schema: ghi nguồn gốc vào `workflow_event` (`WorkflowStarted.du_lieu["chay_lai_tu_run_id"]`) thay vì cột — CHƯA thử, cần bàn với chủ dự án trước vì đây là lệch khỏi đúng chữ spec, không phải một quyết định nhỏ.
- **"So sánh run"**: không cần schema — một route đọc hai run, trả hai danh sách node (cần thêm `params`/`output_ref` vào `_nodes_json`, xem báo cáo task 2). Việc thuần, chưa làm.

## Đề nghị
Giao lại nguyên vẹn cho lượt kế (cùng làn `p9` hoặc làn mới), ưu tiên "so sánh run" trước (không rủi ro tiền), rồi "thử lại node" (rủi ro tiền nhưng không cần schema), "chạy lại từ node" cuối (cần chủ dự án chốt phương án né cột mới trước khi viết).
