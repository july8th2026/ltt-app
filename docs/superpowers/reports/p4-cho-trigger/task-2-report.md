# P4 Task 2 — `core.delay` bền

## Nguồn đã tra
- Spec §5.7: *"`core.delay` **không bao giờ** `sleep`… Delay ≤ 60 s vẫn đi cùng đường"*.
- activepieces `000015`: *"iteration 2 found iteration 1's COMPLETED row … and skipped its pause entirely."*

## Đỏ → xanh
```
8 failed          tests/test_1792_wf_core_delay.py
8 passed          tests/test_1792_wf_core_delay.py
```

## Đã làm
- `nut_loi/cho.py`: `chay_delay`, `mo_diem_cho`, `tiep_mot` (một node), `tiep_cho` (cấp run).
- `dong_co`: gọi `cho.tiep_cho(bo_qua=than_foreach)`; truyền `vong=()` **tường minh** cho bộ thi hành inline; đồng bộ `RUNNING ⇄ WAITING` của run (⛔ **không** đếm waitpoint `JOB` — đếm cả chúng thì mọi run đang chạy đều WAITING và chữ ấy hết phân biệt).
- `vong_lap`: node inline trả `WAITING` trong thân `foreach` là **"đang chờ"**, không phải "hỏng".
- `bien_dich`: luật lược đồ `mot_trong` — `core.delay` không có `duration_s` lẫn `until` là một điểm chờ **không bao giờ tới hạn**.

## Đo được
`test_KHOI_DONG_LAI_giua_chung_run_van_xong` chạy qua `dong_co.mot_vong(db_factory)` — **phiên CSDL MỚI mỗi lượt**, nên không byte trạng thái nào trong bộ nhớ sống sót.

## Chưa làm được
- Không đo "worker thật bị giữ" bằng một luồng thật; đo bằng **bảng `jobs` rỗng**. `core.delay` không có đường nào khác chiếm worker ngoài nộp job, nên hai câu trùng nhau — nhưng đó là một lập luận, không phải một phép đo.
