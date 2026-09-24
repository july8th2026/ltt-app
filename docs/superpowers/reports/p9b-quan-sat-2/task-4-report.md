# P9b Task 4 - Chay lai tu node: LAM PHAN KHONG CAN COT, DUNG va BAO

## Trang thai: MOT NUA XONG - phan con lai cho dieu phoi chot COT

Spec §14: *"tao run **moi** cung version, sao output cac node **khong phai hau
due** cua node chon tu run cu (tham chieu artifact, khong chep byte), chay tu
node do. `workflow_run.chay_lai_tu_run_id` ghi nguon goc."*

Cau hoi **"node nao khong phai hau due"** la mot cau hoi ve DO THI - tra loi
duoc hom nay. Cau hoi **"run nay chay lai tu run nao"** can mot COT.

## Da lam (khong cham luoc do)
`platform_core/workflow/bao_gia.py`:
- `hau_due(graph, node_id) -> frozenset[str]` - chinh no + moi node toi duoc.
- `co_the_tai_dung(graph, node_id) -> tuple[str, ...]` - phan bu, theo `thu_tu`.

⭐ Dung lai `_ke`/`_lan` - **cung mot phep duyet** ma `than_foreach` da dung.
Mot BFS thu hai cho cung cau hoi "toi duoc tu dau" la mot ban sao se troi.

⛔ **Than `foreach` (va chinh cap `foreach`/`foreach_end`) khong bao gio nam
trong tap tai dung.** Anh chup cua node than khoa theo DUONG THI HANH (`f:0/x`,
`f:1/x`… - `thi_hanh.khoa_node`), va duong ay bi **bam** khi vuot 64 ky tu
(`danh_thuc.duong_thi_hanh`), luc do khong suy nguoc duoc (P9 task 3). Sao
output cua mot node chay N lan duoi N khoa, co khoa khong doc nguoc duoc, la
mot phep sao **khong xac dinh** - va tai dung sai mot output nghia la tra cho
khach ket qua cua mot lan chay khac.

```
5 failed in 0.80s   ->   5 passed in 0.65s    (tests/test_3452_…)
```
Doi chung: chay lai tu node DAU ⇒ tap tai dung KHONG rong nhung KHONG chua node
dau (mot cai dat tra "moi node tru node chon" se do); chu trinh khong treo;
node khong co trong do thi thi NEM.

## ⛔ Chua lam - va vi sao DUNG o day
Route `POST /runs/{id}/chay-lai-tu/{node}` **chua mo**. No tao mot run MOI, tuc
mot **khoan giu moi** (dung: run moi thi giu moi), va mot run tao ra ma **khong
ghi duoc nguon goc** la mot but toan khong doi soat duoc: khong tra loi duoc
"tien nay tieu cho lan chay lai cua run nao". Brief cam lan nay them cot/
migration (lan `p6` so huu; `main` hom nay da co mot lan **hai head alembic**
chan deploy cua moi phien). Nen: **dung va bao**.

### DAC TA COT - de dieu phoi giao cho lan giu `models.py`

| | |
|---|---|
| Bang | `workflow_run` (`platform_core/models.py::WorkflowRun`) |
| Ten cot | `chay_lai_tu_run_id` |
| Kieu | `String(36)`, `nullable=False`, `default=""`, `server_default=""` |
| Nghia | id cua run NGUON. `""` = khong phai mot lan chay lai. |
| Chi muc | `Index("ix_wfrun_chay_lai_tu", "chay_lai_tu_run_id")` - cua "cac lan chay lai cua run X" doc theo cot nay |
| Khoa ngoai | ⛔ KHONG. Cung khuon `parent_run_id` (da co, cung bang, cung kieu, khong FK): run nguon co the bi don theo TTL 90 ngay truoc run con, va mot FK se bien mot lan don thanh mot lan xoa day chuyen hoac mot loi rang buoc. |
| `downgrade` | `op.drop_index("ix_wfrun_chay_lai_tu", "workflow_run")` roi `op.drop_column("workflow_run", "chay_lai_tu_run_id")`. An toan: khong bang nao tro toi, khong du lieu nao khac suy ra tu no. |
| Rui ro di tru | Khong. Cot moi co `server_default=""`, moi hang cu doc ra `""` = "khong phai lan chay lai" - dung nghia. |

⚠️ ⛔ **Khong dung `parent_run_id` thay cho no.** `parent_run_id` la quan he
CHA-CON cua subworkflow (`run_con.py`), va quan he ay keo theo **mot loat
nghia vu ve tien**: run con KHONG co `hold_id` rieng, chi phi that cua no cong
len run cha (`ket_so.ket_so` -> `run_con.bao_cha`). Mot lan chay lai la mot run
DOC LAP, co khoan giu cua chinh no. Muon hai nghia vao mot cot la bien mot lan
chay lai thanh mot run con khong tra tien - va moi phep kiem ve hold van xanh.

### Phuong an NE COT ma lan truoc de xuat - da can nhac, KHONG chon
Ghi nguon goc vao `WorkflowStarted.du_lieu["chay_lai_tu_run_id"]` thay vi mot
cot. Khong chon vi hai ly do doc duoc:
1. `workflow_event` co **TTL 90 ngay** (`su_kien.RETENTION_DAYS`) - nguon goc
   bien mat con run thi o lai. Mot quan he doi soat tien khong duoc het han
   truoc thu no doi soat.
2. Truy van nguoc ("cac lan chay lai cua run X") phai quet JSON cua mot bang
   chi-them lon, khong chi muc duoc - trong khi day la truy van CHINH cua tinh
   nang.

## Viec con lai sau khi co cot
1. `tao_run.tao_run(..., chay_lai_tu_run_id=...)` ghi cot (mot cua tao run duy
   nhat, khong mo duong thu hai).
2. Route `POST /runs/{id}/chay-lai-tu/{node}`: `co_the_tai_dung` -> loc lay
   node DA `SUCCEEDED` o run cu -> ghi anh chup `SUCCEEDED` vao run moi voi
   **cung `output_ref`** (tham chieu artifact, ⛔ khong chep byte) -> danh thuc
   dong co. Ba cua an ninh phai giu: `artifact_ref` kiem `owner_id` khi doc
   (§15.2), va ca hai run phai cung `owner_id` va cung `version_id`.
