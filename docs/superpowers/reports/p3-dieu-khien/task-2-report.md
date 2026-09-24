# P3 · Task 2 — Giá `foreach`: `max_items × Σ trần thân`

## Nguồn đã tra

- **Kết luận âm, và nó là kết quả tốt:** `platform_core/workflow/bao_gia.py` đầu
  tệp đã ghi khảo sát bảy kho (Activepieces, n8n, Node-RED, Kestra, Windmill,
  Trigger.dev, Temporal) — *"khong kho nao co tran chi phi; buoc cua ho gan nhu
  mien phi"*. Tôi kiểm lại đúng chỗ dễ có nhất: `activepieces/activepieces`
  không có khái niệm trần tiền cho một bước, `shouldReleaseBarrier`
  (`packages/core/execution/src/lib/flow-run/waitpoint/index.ts`) chỉ đếm tín
  hiệu. ⇒ **Không vay ai được**; luật lấy từ spec của ta.
- Spec `docs/superpowers/specs/2026-09-22-…-v2-design.md` §7.2 → *"ForEach:
  `max_items × trần thân`"*; §5.9 → `max_items` bắt buộc, ≤ 1000.

## Đỏ trước

```
$ python -m pytest tests/test_1781_wf_bao_gia_foreach.py -q
11 failed, 2 passed in 0.85s
```

Phép **passed** là đối chứng `test_doi_chung_do_thi_phang_khong_bi_nhan` — nếu
nó đỏ thì luật mới đang nhân cả những chỗ không có vòng lặp.

## Xanh sau

```
$ python -m pytest tests/test_1781_wf_bao_gia_foreach.py -q
14 passed in 0.65s
$ …chay_nang.py --phien p3 -- python -m pytest tests/test_171{5,6,7,8,9}… -q
51 passed in 8.68s          # bao_gia/publish/tao_run/cau_noi/dong_co khong doi
```

`bao_gia.he_so_lap(graph)`: thân = `tới-được-từ(foreach) ∩ tới-được-tới(foreach_end)`,
cặp khớp bằng `params.foreach` **khai tường minh** (không đoán theo vị trí).
`toi_da = Σ gia[node] × he_so[node]`.

## Hai quyết định đáng ghi

1. **`gia_tran` của từng node KHÔNG bị nhân.** `cau_noi.nop_job` so
   `gia_that > node["gia_tran"]` cho **mỗi lượt** nộp job; nhân nó lên
   `max_items` là nới đúng cổng ấy ra `max_items` lần. Hệ số thuộc về **tổng
   của run** (`graph["he_so_lap"]`), không thuộc trần của một lượt.
2. **`HE_SO_LAP_TOI_DA = 1_000_000`** (hai tầng 1000 vừa khít). Tầng thứ ba thì
   "trần" báo cho khách là 10⁹ lượt — một lời từ chối viết bằng chữ số;
   `KhongBaoGiaDuoc` trung thực hơn. Có phép kiểm kèm **đối chứng** hai tầng vẫn xanh.

## Chưa làm được

- Chạy trên **đồ thị dựng tay**: `bien_dich` chưa nhận `core.foreach` (Task 4–5).
  Phủ **luật giá**, không phủ **đường publish** — Task 5 phải nối vào.
- `call_workflow` (§7.2: `estimated_max` của version con) để Task 7.
- `if`/`switch`: §7.2 đòi **tổng mọi nhánh có thể chạy**, đã đúng sẵn vì tổng
  hiện là phép cộng phẳng — nhưng chưa có phép kiểm; Task 4 thêm.
