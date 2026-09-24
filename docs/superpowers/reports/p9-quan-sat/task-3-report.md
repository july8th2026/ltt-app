# P9 Task 3 (🔴) — Đường thi hành bị BĂM không gộp được trên giao diện

## Nguồn đã tra
- Đọc thẳng mã (không suy từ trí nhớ): `platform_core/workflow/danh_thuc.py::duong_thi_hanh` (băm SHA256[:40] khi vượt `TRAN_NODE_RUN_ID=64`), `apps/agent/routes/runs_v3.py::_gop_than_foreach` (bản cũ: `if "/" not in khoa: continue` — bỏ NGẦM cả khoá băm lẫn node trần, không phân biệt).
- Tìm đường suy ngược hash: `platform_core/models.py::NodeRunSnapshot`/`NodeRun` không lưu `(node_id, vong)` gốc ở đâu khác — mất vĩnh viễn khi đã băm (hash một chiều, `platform_core/workflow/cau_noi.py::nop_job` không ghi lại cặp gốc vào `job.params`).
- `platform_core/workflow/bao_gia.py::than_foreach(graph)` — hàm ĐỌC ĐỒ THỊ TĨNH có sẵn (không phải engine), trả `{id foreach: (id foreach_end, than)}` bằng `tới-được-từ ∩ tới-được-tới`. Dùng lại được, không phải viết mới.

## Vì sao KHÔNG sửa được "đúng" trong ranh giới lượt này
Đã cân nhắc brute-force mọi tổ hợp `(tên_vòng, chỉ_số)` để dò khoá băm: chi phí là TÍCH `max_items` qua mọi tầng lồng (spec cho `foreach` tới 1000 phần tử) — không có trần trên, không chấp nhận được cho một endpoint bị gọi mỗi 1s (SSE task 1). Cách ĐÚNG cần một cột lưu đường gốc (chạm `platform_core/models.py` + migration) hoặc sửa ở động cơ ghi thêm siêu dữ liệu lúc `duong_thi_hanh` băm (chạm `dong_co.py`/`foreach.py`/`vong_lap.py`/`cau_noi.py`) — CẢ HAI ngoài ranh giới brief giao cho lượt `p9`. Báo cáo đúng yêu cầu "DỪNG và báo tôi kèm số đo" — số đo ở trên.

## Đỏ → xanh (mitigation trong ranh giới)
```
tests/test_3421_wf_v3_bam_khong_gop_duoc.py   TypeError (thiếu tham số `do_thi`) → 2 passed
```
Đối chứng hai chiều trong CÙNG tệp: `vong` dài ép băm (khẳng định `khoa.startswith("#")`) vs `vong` ngắn không băm vẫn gộp đúng như cũ (không hồi quy đường cũ).

## Đã làm
Đổi `PENDING` giả (nói dối) thành trạng thái tường minh `KHONG_XAC_DINH` cho MỌI node thân của MỌI `foreach` (đọc từ `bao_gia.than_foreach`, không đụng engine/schema) không có khoá chưa-băm nào khớp. Cố ý OVER-approximate (có thể đánh dấu cả node không hề bị băm) — giữa "thừa một cảnh báo" và "thiếu một cảnh báo", cái trước không bao giờ khiến người vận hành tin nhầm một việc đang chạy là chưa bắt đầu.

## Chưa làm được
Gộp trạng thái ĐÚNG (RUNNING/FAILED/SUCCEEDED thật) cho node bị băm — cần schema hoặc engine, đề nghị chủ dự án giao lại `p5c`/`p4` kèm số đo ở trên.
