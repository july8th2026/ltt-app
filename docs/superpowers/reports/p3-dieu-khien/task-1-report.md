# P3 · Task 1 — Khoá `wakeup` theo đường thi hành đầy đủ

## Nguồn đã tra (không suy)

- `activepieces/activepieces@17e2ac0b` ·
  `brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`
  → *"Identity is path-keyed, and that needed no new column. The engine sends
  `loop_1:3/loop_2:0/approval` in the existing `stepName` field… fixes a live bug…
  a delay or approval **inside a loop** used to reuse one waitpoint row across every
  iteration, so iteration 2 found iteration 1's COMPLETED row … and skipped its pause."*
- `brain/knowledge/flows-execution/flow-runs.md` (cùng SHA) → khoá của họ là
  `Waitpoint UNIQUE(flow_run_id, step_name)` — cùng hạng với `UNIQUE(run_id,
  node_run_id, kind, due_at)` của ta (`platform_core/models.py:1471`).

## Đỏ trước

```
$ python -m pytest tests/test_1780_wf_wakeup_duong_thi_hanh.py -q
5 failed, 1 passed in 1.20s
```

Phép **passed** là đối chứng `test_doi_chung_node_id_tran_thi_vong_2_va_vong_1`:
với `node_run_id` trần, vòng 2 của một `foreach` (`foreach.mo_vong` hai phần tử)
hẹn `delay` cùng hạn ⇒ `IntegrityError`. Đó là bằng chứng lỗi CÓ THẬT và CSDL
thật sự cưỡng chế — không chỉ là một ràng buộc SQL được đọc ra.

## Xanh sau

```
$ python -m pytest tests/test_1780_wf_wakeup_duong_thi_hanh.py -q
6 passed in 1.19s
```

`platform_core/workflow/danh_thuc.py`: thêm `duong_thi_hanh(node_id, vong=…)`
(`f1:0/delay1`) + `hen_node(...)`. `hen()` trần giữ nguyên cho hai ca **không**
thuộc về một node: `tick`/`start` của cả run (`node_run_id=""`) và wakeup theo
job id (`cau_noi.bao_ket_thuc` — mỗi lượt thử một job nên khoá đã duy nhất).

## Lệch plan, có lý do

Plan ghi *"`models.py` + migration"*. **Không migration.** Quyết định 000015
nói thẳng *"that needed no new column"*, và cột rộng hơn vẫn là một trần: một
`foreach` lồng sáu tầng vượt mọi bề rộng cố định. Thay vào đó khoá **băm** khi
vượt `TRAN_NODE_RUN_ID = 64` (`#` + sha256[:40]; `#` không nằm trong tập id hợp
lệ nên không đụng khoá đường-thật). ⛔ Băm chứ **không** cắt cụt: cắt cụt là cách
im lặng nhất để hai đường khác nhau thành một khoá — đúng lỗi này, chỉ đổi
nguyên nhân. PostgreSQL ném ở ký tự 65, SQLite nuốt ⇒ không tự chặn thì chỉ lộ
trên production.

## Chưa làm được

- Phép chưa đi qua `dong_co.xu_ly_run` — node `foreach`/`delay` chỉ có ở Task 5.
  Nó phủ **khoá**, không phủ **lập lịch**. Task 5 phải nối `hen_node` vào thân
  vòng lặp và thêm một bánh cóc chặn `hen()` trần cho node.
- Chưa chạy trên PostgreSQL thật (Task 8).
