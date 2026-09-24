# P3 · Task 7 — `core.call_workflow`: run con, MỘT khoản giữ cho cả cây

## Nguồn đã tra

- **Mã của chính ta là nguồn chính, và nó đã viết sẵn luật:** `tien.py` —
  *"Nếu run cũng giữ và node cũng giữ thì khách trả **hai lần** cho cùng một
  việc."* Run con là đúng bẫy ấy ở một tầng khác.
- Spec §5.10 (`version_id` **ghim lúc publish cha**, `parent_run_id`/
  `parent_node_id`/`do_sau`), §7.2 (*"subworkflow: `estimated_max` của version
  con"*), §10 (*"độ sâu subworkflow 5"*).
- `activepieces/activepieces@17e2ac0b` — subflow của họ (`FlowRun.parentRunId`,
  `brain/knowledge/flows-execution/flow-runs.md`) **không** mang khái niệm tiền,
  nên không có gì để port ở phần sổ sách. Kết luận âm, và nó là kết quả: phần
  khó của việc này là của riêng ta.

## Đỏ trước

```
$ python -m pytest tests/test_1786_wf_call_workflow.py -q
12 failed in 4.93s
```

## Xanh sau

```
$ python -m pytest tests/test_1786_wf_call_workflow.py -q
12 passed in 4.76s
$ …chay_nang.py --phien p3 -- pytest <25 tep wf> -q -n 6
395 passed, 6 warnings in 39.90s
```

## 🔴 MỘT LỖI SỔ SÁCH TỰ TIÊM, TỰ BẮT — đáng ghi nguyên văn

Bản đầu cộng `con.actual_cost` vào `cha.actual_cost` ngay khi con kết sổ. Nó
**không sống nổi một dòng**: `ket_so` của cha sau đó ghi đè `actual_cost` bằng
`tong_chi_phi_hop_le` của **riêng** cha, và phần tiền của con biến mất. Phép
kiểm đo được `0 == 3`.

⚠️ Chỗ nguy hiểm: mọi phép kiểm về *"run con không giữ khoản thứ hai"* vẫn
**xanh**. Nếu chỉ viết phép kiểm cho luật (1) thì nền tảng lặng lẽ **cho không**
toàn bộ phần việc chạy trong run con.

⇒ Sửa về một hàm **dẫn xuất**: `chi phí(run) = tong_chi_phi_hop_le(run) +
Σ actual_cost(con)`. Một chỗ tính, không hai. Lồng nhiều tầng tự đúng vì con
luôn kết sổ trước cha (cha đang WAITING chờ nó).

## Ba luật, phải đi cùng nhau

1. **Run con không giữ chỗ** — `run_con.tao_run_con` không gọi
   `tien.giu_cho_run`, và `estimated_max = 0` để không ai gọi nhầm được.
   Bánh cóc AST `test_banh_coc_MOT_khoan_giu_cho_CA_CAY` ghim rằng **chỉ**
   `tao_run.py` gọi hàm ấy (đối chứng: khẳng định tập lời gọi khác rỗng trước).
2. **Trần con nằm trong trần cha** — `dinh_nghia._ghim_subworkflow` ghi
   `gia_con` từ `WorkflowVersion.estimated_max`; `bao_gia._gia_node` đọc nó.
   ⛔ Client **không khai được** `gia_con` (`additionalProperties: false` từ
   chối nó trong draft) — *"một trường trong body của người gọi không thể là
   nguồn của một con số nền tảng dùng để giữ tiền của chính người gọi ấy"*.
3. **Chi phí con nằm trong chi phí cha** — xem trên.

## Chặn ở PUBLISH, không lúc chạy

`_ghim_subworkflow` ghim `version_id` (`"latest"` → id thật) và từ chối:
`goi_de_quy` · `workflow_con_khong_ton_tai` (kể cả của người khác) ·
`workflow_con_chua_publish` · `qua_sau_subworkflow`. Độ sâu tính **tĩnh** được
vì mọi `version_id` đã ghim và version là **bất biến** ⇒ cây gọi hữu hạn.
`graph["do_sau_goi"]` mang kết quả lên tầng trên.

## Migration — đã chạy thật, không chỉ viết ra

`alembic/versions/20260924_1500_wf_run_con.py` (`b7d2e9c41a03`, revises
`8f1c6a4d2b90`): ba cột có `server_default` + NOT NULL ⇒ trên PostgreSQL ≥ 11 là
thao tác **chỉ sửa catalog**, không viết lại bảng đang chạy thật. Chỉ số
`ix_workflow_run_parent` là **bộ phận** (`parent_run_id <> ''`).

```
$ alembic heads          -> b7d2e9c41a03 (head)      # MOT head, khong re nhanh
$ alembic upgrade head   -> 8f1c6a4d2b90 -> b7d2e9c41a03
$ PRAGMA table_info      -> ['parent_run_id', 'parent_node_id', 'do_sau']
$ sqlite_master          -> ['ix_workflow_run_parent']
```

## Chưa làm được

- `wait = false` (bắn rồi quên) — spec §5.10 mặc định `true`, bản này chỉ làm
  `true`. Tham số `wait` **chưa** được khai, nên không có lời hứa suông nào.
- `huy_run` của cha **không** huỷ các run con đang chạy (`run_con.con_dang_chay`
  đã có sẵn để nối, nhưng chưa nối và chưa có phép kiểm). ⚠️ Đây là một lỗ
  **tiền thật**: một run cha bị huỷ để lại con chạy tiếp và cộng chi phí vào
  một cha đã kết sổ. Phải làm trước khi mở cho khách.
- `inputs` được tính và ghi vào sự kiện `WorkflowStarted` nhưng chưa có
  `workflow.input` để con đọc — `moi_truong_run` vẫn truyền `workflow_input={}`.
- Chưa chạy trên PostgreSQL thật (Task 8).
