# P9 Task 2 — Inspector run: trạng thái từng node, ảnh chụp, lỗi

## Đã có sẵn (trước lượt này, không phải việc mới)
`GET /agent/api/v3/runs/{id}` (`runs_v3.py::_nodes_json`) đã trả, cho MỌI node của đồ thị đã ghim: `status`, `attempt`, `cost_credit`, `job_id`, `error`. `RunV3Panel.tsx` render một bảng phẳng từ đó.

## Đã làm thêm trong lượt này
- `waiting_kind` (spec §14 + yêu cầu coordinator khi mở lại `main`/phase 5+6): phân biệt một node `WAITING` vì `HUMAN` (chờ người duyệt) với `WAITING` vì `WEBHOOK`/`DELAY`/`JOB`/`CHILD_RUN`/`BARRIER` — đọc từ `Waitpoint.kind` qua `cho_doi.waitpoint_cua_node`. Test `test_3422_wf_v3_waiting_kind.py` (đỏ `KeyError` → xanh 2 passed). Frontend: `NHAN_WAITING_KIND`, nhãn "(chờ người duyệt)"/"(chờ webhook)" cạnh trạng thái; test `RunV3Panel.test.tsx` (3 passed, DOM thật qua React Testing Library).
- `KHONG_XAC_DINH` (xem báo cáo task 3) là một phần của "trạng thái từng node" — không còn nói dối `PENDING`.

## Chưa làm được (thật sự chưa động tới)
- **"Ảnh chụp"** theo đúng nghĩa spec §14 ("output (ref artifact xem trước), tham số đã tính, lịch sử thử lại = chuỗi snapshot") — `_nodes_json` hiện KHÔNG trả `output_ref`/tham số đã tính/chuỗi `previous_snapshot_id`. Cần thêm: (a) endpoint `GET /agent/api/v3/runs/{id}/nodes/{node_id}/lich-su` đọc `NodeRunSnapshot` theo `previous_snapshot_id`, (b) UI: click một node mở panel chi tiết (hiện `RunV3Panel.tsx` chỉ có bảng phẳng, không có node nào bấm được).
- Không có thời gian kiểm bằng trình duyệt việc CLICK-THROUGH một node để xem chi tiết, vì tính năng đó chưa được xây — chỉ mới browser-verify được rằng Canvas load sạch (0 lỗi console, mọi request 200) với bundle đã build.

## Đề nghị
Việc còn lại là công sức thuần (một endpoint + một panel UI), không có nút thắt kiến trúc như task 3/4 — làm được trong một lượt kế nếu chủ dự án giao tiếp.
