# P9b Task 2 — So sánh hai run (XONG)

**Cửa:** `GET /agent/api/v3/runs/{id}/so-sanh?voi={id2}` —
`apps/agent/routes/runs_v3.py` (`v3_so_sanh_run`, `_nodes_so_sanh`,
`_tom_tat_so_sanh`, `_inputs_cua`).

## Nguồn
- Spec §14 *"So sánh run: API trả hai danh sách node với tham số/output/chi
  phí; UI diff"*.
- ⛔ Không cột mới. Ba nguồn dẫn xuất: `workflow_version.graph` (tham số KHAI),
  `node_run_snapshot` (`execution_status`/`attempt`/`cost_credit`/`output_ref`/
  `error`), `workflow_event` `WorkflowStarted.du_lieu["inputs"]`
  (`platform_core/workflow/tao_run.py:232`).
- `NodeRunSnapshot` (`models.py:1317`) **không có cột `params`** — tham số đã
  giải chỉ sống trong `Job.params`, nơi `cau_noi.nop_job` tiêm `owner_id`,
  `_idem` **và credential đã giải** (§9.4). ⇒ trả tham số **KHAI**, và có phép
  kiểm chốt rằng một bí mật trong `Job.params` không lọt ra.

## Dòng đỏ / dòng xanh
```
6 failed, 1 warning in 16.61s      (tests/test_3450_wf_v3_so_sanh_run.py)
6 passed, 1 warning in 13.88s
123 passed, 8 warnings in 30.21s   (cụm 13 tệp v3/workflow, qua chay_nang.py)
```

## Đối chứng
- **So một run VỚI CHÍNH NÓ ⇒ `khac == []`.** Không có phép này, một cài đặt
  trả "mọi node" vẫn xanh ở phép so hai run khác nhau.
- `job_id` CỐ Ý không nằm trong `_TRUONG_SO_SANH`: nó khác nhau ở mọi cặp run,
  đưa vào thì `khac` = "mọi node đã chạy".
- Ranh giới chủ sở hữu kiểm ở **cả hai** phía (`path` và query `voi`) — cửa
  này nhận id thứ hai từ query, nên chỉ lọc `path` là một máy dò id.

## Chưa làm được
UI diff trên Canvas (spec §14 nói *"UI diff"*) — cửa máy đã xong, màn hình
chưa dựng.
