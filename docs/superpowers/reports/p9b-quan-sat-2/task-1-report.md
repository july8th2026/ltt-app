# P9b Task 1 - Thu lai mot node (XONG)

**Cua:** `POST /agent/api/v3/runs/{id}/nodes/{node}/thu-lai` -
`apps/agent/routes/runs_v3.py` (`v3_thu_lai_node`, `_kiem_hold_con_du`,
`_node_trong_do_thi`) + `platform_core/workflow/thu_lai.py::thu_cong`.

## Nguon
- Spec Sec14: *"Thu lai node (phase 13): run dang FAILED => POST ... tao
  attempt moi (can hold con du; khong thi 402)"*.
- `platform_core/workflow/tien.py` + `ket_so.py`: **mot khoan giu moi run**
  (`hold_id = run.id`), va `may_trang_thai.chuyen_run` goi thang
  `ket_so.ket_so()` khi run vao trang thai ket thuc => khoan giu DA NHA.
- `platform_core/agent/supervisor.py` (da gop `main`) da thu hep dung cho nay
  cho Sec12.4, ma `run_da_ket_so`. Cua nay **dung lai nguyen ma do**.

## 🔴 Mot cho SPEC TU MAU THUAN - da khai
Sec14 viet *"run dang FAILED => thu lai"*. Nhung `FAILED in RUN_KET_THUC`, va
run ket thuc la run **da ket so**: `hold_id` da xoa, so cua khach da chot.
Neu lam dung chu Sec14 thi dieu kien "can hold con du" **khong bao gio dat** -
tuc cua nay 402 vinh vien, hoac nen tang chay tiep mot node **khong con tien
bi giam** (lam khong cong). Chon: thu lai chi khi run **chua ket so**
(`QUEUED`/`RUNNING`/`WAITING`), tra 402 `run_da_ket_so` khi da ket so. Day la
cung mot thu hep ma supervisor da chot va da qua review.

## Ba cong ve tien (theo thu tu)
1. run chua ket so -> 402 `run_da_ket_so`
2. `estimated_max > 0` ma `hold_id` rong -> 402 `khong_con_hold`
3. `estimated_max - tong_chi_phi_hop_le(run)` >= `node.gia_tran` -> nguoc lai
   402 `hold_khong_du`  (chu "can hold con du" cua Sec14, tinh tu so da co)

⛔ Cua **khong** goi `tien.giu_cho_run`: khong co khoan giu thu hai.
⛔ Cua **khong** nop job: no dua node ve `RETRY_SCHEDULED` han *bay gio* roi
hen wakeup; `thu_lai.den_han` + `cau_noi.nop_job` van la duong nop DUY NHAT,
nen chinh sach side effect / tran bao gia / `_khoa_idem` khong bi di vong.

## Quyet dinh: `retry.max` KHONG gac cua nay
`retry.max` (mac dinh **0**) la tran cua retry **TU DONG** - Sec12.4 gan no cho
supervisor vi supervisor cung la may. Sec14 gan cho cua NGUOI BAM dung mot dieu
kien, va dieu kien ay la **tien**. Gac them `retry.max` lam nut "Thu lai" chet
theo mac dinh (`max = 0` => moi lan bam 409). Cai KHONG noi:
`thu_lai.KHONG_THU_LAI` (ABANDONED/CANCELLED/SUCCEEDED/SKIPPED) -> 409.

## Dong do / dong xanh
```
12 failed, 1 warning in 28.97s     (tests/test_3451_wf_v3_thu_lai_node.py)
12 passed, 1 warning in 25.36s
123 passed, 8 warnings in 30.21s   (cum 13 tep v3/workflow, qua chay_nang.py)
```

## Doi chung
- **Dem but toan `CREDIT_HOLD` truoc va sau** => KHONG DOI. Day la phep dat
  nhat cua tep: mot cai dat "tien tay giu them cho chac" van xanh o moi phep
  chi doc trang thai.
- `hold_khong_du` co doi chung duong: cung do thi, chi phi nho hon => 200.
- 404 cho run cua nguoi khac co doi chung: chinh chu van 200.
- Co wakeup `retry` that (`Wakeup.kind == "retry"`, dung 1). Thieu phep nay,
  mot cai dat chi doi trang thai van xanh - va node nam do toi han `TRAN_RUN`
  20 gio.

## 🔴 Loi tim duoc o ma NGUOI KHAC (da bao, khong sua o lan nay)
`platform_core/agent/supervisor.py::thu_lai_node` ghi `attempt_number=lan`
(giu nguyen), trong khi duong tu dong `cau_noi.ap_ket_qua` ghi `lan + 1`.
Hau qua: (a) `retry.max` khong bao gio can tren duong supervisor -
`con_luot(node, lan)` luon nhan cung mot `lan`; (b) `cau_noi._khoa_idem` bam
theo `[run.id, duong, lan]` o nhanh `side_effect == "none"` => cung khoa khu
trung. Hom nay chua sap vi `jobs.submit` chi khu trung job dang QUEUED/RUNNING
(`jobs.py:232-241`) va job cu da ket thuc ERROR - nhung do la trung hop ve thoi
diem, khong phai bao dam. Da tao chip viec rieng.

## Chua lam duoc
Nut "Thu lai" tren Canvas (giao dien) - cua may da xong, man hinh chua dung.
