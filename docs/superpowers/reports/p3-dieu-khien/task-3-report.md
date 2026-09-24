# P3 · Task 3 — Retry cấp node: lớp mỏng, không cơ chế thứ hai

## Nguồn đã tra

- **Mã của chính ta trước** (luật "dùng lại trước, tự viết sau"):
  `platform_core/jobs.py` — `fail()` đã có backoff mũ `base * 2**(n-1)` chặn
  `_RETRY_MAX_S`, `max_attempts`, `dedupe_key` (`submit`), `reclaim_orphans`.
  ⇒ **Kết luận âm là kết quả tốt**: không cần vay của ai, chỉ cần đừng viết lại.
- Spec §5.6 → ranh giới chính xác: *"Job giữ nguyên retry của nó… **Retry node**
  chỉ xảy ra khi job đã kết thúc ERROR: `settings.retry = {max ≤ 5, backoff_s}`,
  mặc định `{max: 0}`"*; và *"`irreversible` ⇒ `ABANDONED`… **không bao giờ tự thử**"*.
- `may_trang_thai.NODE_CHUYEN` đã có sẵn `RETRY_SCHEDULED` (`QUEUED|RUNNING →
  RETRY_SCHEDULED → READY`) — chưa ai dùng. Không thêm trạng thái mới.

## Đỏ trước

```
$ python -m pytest tests/test_1782_wf_thu_lai_node.py -q
12 failed, 3 passed in 2.86s
```

Ba phép **passed** là đối chứng: mặc định `{max: 0}` ⇒ FAILED ngay, `CANCELLED`
và `ABANDONED` không thử lại — nếu chúng đỏ thì lớp mới đang thử lại những node
không xin thử lại.

## Xanh sau

```
$ python -m pytest tests/test_1782_wf_thu_lai_node.py -q
15 passed in 2.60s
$ …chay_nang.py --phien p3 -- pytest <11 tep wf + job> -q -n 6
152 passed, 6 warnings in 12.97s
```

## Bánh cóc CẮN THẬT (tiêm lỗi rồi đo)

`test_banh_coc_thu_lai_khong_tu_tinh_backoff` đọc AST `thu_lai.py`: cấm mọi
`ast.Pow`, đòi có lời gọi `jobs.gian_cach_retry`.

```
# thay jobs.gian_cach_retry(...) bang min(600, backoff_s * (2 ** (lan - 1)))
$ pytest …::test_banh_coc_thu_lai_khong_tu_tinh_backoff -q
E   assert not [<ast.BinOp object at 0x…>]
1 failed in 0.39s
# phuc hoi
1 passed in 0.27s
```

Đối chứng đường dẫn nằm trong chính phép (`len(nguon) > 500 and "def hen" in
nguon`) — tệp sai đường thì tập rỗng và mọi `assert not …` xanh giả.

## Việc đã làm

- `platform_core/jobs.py`: `RETRY_BASE_S`/`RETRY_MAX_S` công khai +
  `gian_cach_retry(lan, base=…)`; `fail()` gọi chính hàm đó (một công thức, một chỗ).
- `platform_core/workflow/thu_lai.py` (mới, đã khai `core:wf_dong_co` trong
  `tools/thanh_phan.toml`): `doc_chinh_sach` (từ chối rác, không lặng lẽ lấy mặc
  định), `quyet_dinh` (`KHONG_THU_LAI` **thắng** `settings.retry`), `hen`
  (wakeup `kind="retry"` khoá qua `danh_thuc.hen_node` — Task 1), `den_han`.
- `cau_noi.ap_ket_qua`: nhánh hỏng đi qua `thu_lai.quyet_dinh`; RETRY_SCHEDULED
  ghi `attempt_number = lan + 1` nên `nop_job` dựng `_khoa_idem` mới cho
  `side_effect="none"` và **giữ nguyên** khoá cho `external` (§5.6 đòi đúng thế).
- `dong_co.xu_ly_run`: `thu_lai.den_han` chạy **trước** vòng lan truyền ⇒ node
  tới hạn được nộp lại ngay trong cùng lượt.

## Tiền: vì sao retry không phá trần

Một lượt hỏng **không** ghi `cost_credit` (`ap_ket_qua` chỉ cộng `actual_cost` ở
nhánh SUCCEEDED, `test_1718::test_job_loi_khong_tinh_tien`, và phép mới
`test_het_luot_thi_FAILED` đo lại `run.actual_cost == 0`). Node thành công nhiều
nhất một lần ⇒ `bao_gia.he_so_lap` **không** phải nhân thêm `retry.max`. Điều
kiện ấy được ghi ngay trong docstring `thu_lai.py`: ngày nào lượt hỏng bị thu
tiền thì câu này hết đúng.

## Chưa làm được

- `vong` (ngữ cảnh foreach) của `thu_lai.hen` hiện luôn `()` — Task 5 phải
  truyền `(tên_vòng, chỉ_số)` vào, nếu không hai vòng lặp cùng hẹn một khoá.
- `reclaim_orphans` (worker chết giữa chừng) vẫn hoàn toàn là việc của `jobs.py`;
  phép kiểm này **không phủ** ca đó.
- Chưa chạy trên PostgreSQL thật (Task 8).
