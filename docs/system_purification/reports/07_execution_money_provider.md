# BAO CAO 07 — EXECUTION, MONEY, STORAGE & PROVIDER

Ngay: 2026-09-02 · Che do: **PHAN TICH. Khong sua duong tien.**

---

## 0. Ket qua mot dong

Ba may trang thai deu co chu so huu duy nhat va co phep kiem. **Nhung bat bien
dat nhat cua he thong — chong tieu hai lan — co phep kiem CHUA BAO GIO CHAY tren
may nay.**

---

## 1. Mach tien: `job → giu cho → worker → quyet toan / hoan`

`platform_core/credit.py` mo dau bang bon nguyen tac, nguyen van:

1. **So du = tong cua so.** Khong o `balance` nao bi sua de.
2. **Chi ghi them.** Sai thi ghi but toan bu.
3. **Giu cho → quyet toan → hoan** deu trong transaction cua caller.
4. **Quyet toan/hoan idempotent theo job.**

### Nguyen tac 4 duoc cuong che bang gi

```python
def _khoa_ket_so_job(db, job_id):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"credit-final:{job_id}"})
```

Khoa **cap CSDL that**, an toan da tien trinh, va docstring neu dung cuoc dua no
chan: *"Kiem tra `_da_ket_so` roi ghi la mot thao tac check-then-write. Hai
worker hoac mot worker va request huy co the cung vuot qua kiem tra neu khong co
khoa."*

⭐ Dung `pg_advisory_xact_lock` chu khong doi schema: so but toan la **append-only**,
va them mot rang buoc UNIQUE se pha tinh chat do.

---

## 2. 🔴 PHAT HIEN LON NHAT CUA CA CHUONG TRINH

Dong ngay tren khoa la:

```python
if db.bind.dialect.name == "postgresql":
```

**Tren SQLite — thu ma toan bo bo test dung — no la no-op.**

⇒ Bat bien chong tieu-hai-lan **khong he duoc bo test thuong kiem**.

### Kho CO dung phep kiem can — va no dang bi bo qua

`tests/test_73_dong_thoi_pg.py`, **bay phep kiem dong thoi**:

```
test_giu_cho_khong_double_spend_dong_thoi
test_global_queue_cap_dem_va_insert_nguyen_tu
test_claim_khong_nhac_trung_hai_worker
test_claim_bon_child_agent_khong_trung
test_agent_approve_dong_thoi_chi_mot_hold
test_agent_executor_hai_scheduler_khong_submit_trung
test_agent_workflow_hai_save_cung_revision_chi_mot_thanh_cong
```

```
LTT_TEST_DATABASE_URL: (chua dat)   ⇒ ca bay deu SKIP
```

### Va no khong don doc — HAI co che an toan cung tinh trang

| Co che | Trang thai moi luot gate hom nay |
|---|---|
| `test_73_dong_thoi_pg` (7 phep kiem dong thoi) | **SKIP** — thieu `LTT_TEST_DATABASE_URL` |
| `check_multiproc` / `test_214` (bat bien da tien trinh) | **BO QUA** — thieu CSDL test |

⇒ Hai thu canh **tien** va **da tien trinh** deu chua duoc xac minh o day.

### ⭐ He thong BIET dieu do va NOI RA — do la phan lam dung

- Ca hai deu tu khai o dong `RESULT`: *"4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG"*.
- `tests/pg_scratch.py` mo dau bang mot doan rat nghiem khac ve vi sao mot URL
  phai **chung minh** no la CSDL vut di truoc khi bi `drop_all()`:

  > *"Rule khong phai 'be careful'. Rule la mot URL phai chung minh no disposable:
  > ten CSDL phai chua `test`… va no phai khong phai URL ma deployment nay dang
  > chay. Mot URL khong qua duoc la HARD FAILURE, khong bao gio la skip —
  > skipping la cach mot sai lam thanh im lang."*

⇒ Day **khong** phai cho ai do giau. Day la cho ai do da dung hang rao roi chua
ai buoc qua.

### ⛔ Vi sao toi KHONG tu chay no

Chay `test_73` doi tro `LTT_TEST_DATABASE_URL` vao mot CSDL PostgreSQL **vut di**
tren **chinh may production**. `pg_scratch` co hai chot, nhung viec **tao mot
CSDL moi tren PostgreSQL cua production** la hanh dong ngoai pham vi mot dot don
dep. Ghi thanh viec **cho chu san pham quyet**.

---

## 3. Mach provider: `chon → goi → ban/loi → cooldown`

| Do | Ket qua |
|---|---|
| Chu so huu cooldown | **DUY NHAT** — `platform_core/api_pool.py` |
| Ba tep khac nhac cooldown | chi la **chu thich canh bao**, khong cai dat gi |
| Luat "Ban ≠ hong" | co phep kiem: `tests/test_255_dieu_phoi.py` neo **bon** tinh chat, kem so hieu su co D-005 |

Bon tinh chat, nguyen van:

1. *"Ban ⇒ di tiep provider sau, va KHONG `danh_dau_loi`"* — neu lan, key
   `ltt_llm` bi cooldown roi `disable` sau 5 lan, va **mot toi may B chay video
   se tu tat vinh vien model nha**.
2. *"Loi that ⇒ CO `danh_dau_loi`, roi moi di tiep."*
3. *"Vuot ngan sach ⇒ nem ngay, KHONG cascade."*
4. *"Thu tu do ben goi khai."*

⇒ Khuon dung: **mot chu so huu · nhieu chu thich chi ve no · mot bo test neo
hanh vi**.

---

## 4. Mach job: `queue → worker → terminal`

Do o Phase 05, nhac lai ket luan:

| Loai viec nen | Bao ve |
|---|---|
| phai chay MOT lan (8 viec) | `leases.MAINTENANCE` + dap nhip + mat lease thi dung |
| phai chay MOI tien trinh (`_xa_metrics`) | **co y** ngoai lease, ly do trong docstring |
| nhieu tien trinh mot bang (`reclaim_orphans`) | `with_for_update(skip_locked=True)` |

⚠️ Nhung phan `SKIP LOCKED` cung **chi co tac dung tren PostgreSQL** —
chu thich cua chinh no ghi: *"SQLite (test) bo qua menh de nay, vo hai."*

⇒ Cung mot khoang trong nhu §2: co che that chay tren PostgreSQL, phep kiem
thuong chay tren SQLite.

---

## 5. Ket qua Phase 07

| Muc tieu prompt | Ket qua |
|---|---|
| dung may trang thai that | ✅ ba mach: tien · job · provider |
| tim gia trung, hold/settle trung | **khong co** — mot chu so huu moi mach |
| nhieu he backoff | **khong** — `api_pool` la duy nhat |
| test double-spend truoc khi refactor | ⚠️ **da co, nhung dang SKIP** — §2 |
| tiem loi o cho an toan | ⛔ khong lam: duong tien dang phuc vu khach that |

## 6. Rui ro mo — **P0**

| Rui ro | Hanh dong tiep |
|---|---|
| **Bat bien chong tieu-hai-lan chua duoc xac minh tren may nay** | chu san pham quyet: tao mot CSDL PostgreSQL vut di, dat `LTT_TEST_DATABASE_URL`, chay `test_73` |
| Bat bien da tien trinh (`test_214`) cung tinh trang | nhu tren |

⭐ Ca hai **khong** phai lo hong moi do chuong trinh nay tao ra. Chung la khoang
trong **da co san**, va gia tri cua Phase 07 la lam cho no **nhin thay duoc va
co ten**, thay vi nam sau bon chu `BO QUA` ma khong ai doc.
