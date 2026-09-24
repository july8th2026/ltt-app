# P9b Task 4 - Chay lai tu node: LAM PHAN KHONG CAN COT, DUNG va BAO

## Trang thai: XONG (cot da co tren `main`, route da mo)

> **Cap nhat.** Luc viet lan dau, cot `chay_lai_tu_run_id` chua co nen route bi
> giu lai. Lan `p6-connector` da them dung dac ta duoi day (revision
> `3d5c07e2ba91`); sau `git merge main` (`4f7249ae`, alembic MOT head) route da
> mo. Muc "Chua lam" cu nay o lai lam lich su, phan lam duoc ghi o cuoi tep.

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

## (Lich su) ⛔ Vi sao tung DUNG o day
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


---

# Phan lam NOT sau khi co cot

`POST /agent/api/v3/runs/{id}/chay-lai-tu/{node}` -
`apps/agent/routes/runs_v3.py` (`v3_chay_lai_tu_node`, `_sao_output`),
`platform_core/workflow/tao_run.py` (+`ghim_version_id`, +`chay_lai_tu_run_id`),
`platform_core/workflow/thi_hanh.py` (+`chay_lai_tu_run_id`).

## 🔴 Ba manh de ve tien - do bang SO

| | Cach do | Ket qua |
|---|---|---|
| Run moi la run DOC LAP, hold RIENG | dem but toan `CREDIT_HOLD` truoc/sau | **+1 dung mot**; `hold_id == id run moi` ≠ hold run cu; `parent_run_id == ""` |
| Node TAI DUNG khong tinh tien lan hai | doc `cost_credit` cua anh chup da sao | **0**, va `output_ref` giu NGUYEN tham chieu artifact |
| ⭐ Phep do PHAN BIET duoc | chay het ba luot toi luc KET SO | run moi tinh **6** · chay lai tu `a` (khong tai dung gi) **6** · chay lai tu `b` (tai dung `a`) **3** |

Dong thu ba la doi chung ma dieu phoi doi: mot luot chay lai **khong** tai dung
duoc gi ton **dung bang** mot run moi tinh. Thieu no, mot cai dat ghi
`cost_credit = 0` cho MOI node van xanh o hai dong tren - va no cho khong ca
luot chay.

## Hai quyet dinh khac, deu co ly do doc duoc
- **Ghim version CU** (`ghim_version_id`), ⛔ khong phai ban publish moi nhat.
  Chay lai tren mot do thi da doi la sao output cua nhung node **co the khong
  con ton tai** sang mot do thi **co the khong co chung** - va khong ai bao.
  `tao_run` kiem `ver.workflow_id == workflow.id`: khong kiem la mo mot cua
  ghim do thi cua NGUOI KHAC vao run cua minh.
- **`inputs` cua run cu di theo**: bieu thuc cua do thi doc `inputs.*`, nen mot
  luot chay lai khong mang chung la chay lai **mot bai toan khac**.
- Sao **ca** `output_ref`, ke ca khoa noi bo `_nhanh`: `dong_co._nhanh_da_chon`
  doc dung khoa ay de biet mot `core.if`/`core.switch` da re duong nao. Loc no
  di la sao mot node re nhanh ma **khong** sao quyet dinh re - lan truyen sau do
  dung im, khong co loi nao.
- Giu `job_id` CUA RUN CU tren anh chup da sao: do la job da that su sinh ra
  artifact, va la con tro duy nhat di nguoc ve no.

## Dong do / dong xanh + doi chung (tiem loi)
```
9 failed, 1 warning in 21.83s   ->   9 passed, 1 warning in 19.86s
```
| Tiem | Bai do |
|---|---|
| node tai dung BI tinh tien lan hai (`cost_credit=anh.cost_credit`) | `test_node_tai_dung…`, `test_khong_tai_dung_duoc…` (2 failed, 7 passed) |
| sao CA hau due (cho khong ca luot chay) | `test_node_tai_dung…`, `test_chay_lai_tu_node_DAU…`, `test_khong_tai_dung_duoc…` (3 failed, 6 passed) |

## Chua lam duoc
Nut "Chay lai tu day" tren Canvas - cua may da xong, man hinh chua dung.
