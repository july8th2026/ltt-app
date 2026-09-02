# NGAN SACH CPU CHO GATE — chan doan va sua tan goc

Ngay: 2026-09-02 · Sau **HAI** lan may treo phai reset cung
Nguoi bao: chu san pham (*"moi lan chay dot cpu kha cang… nghi ngo dan den qua tai treo may"*)

---

## 0. Nghi ngo DUNG. Va nguyen nhan la mot phep dem sai don vi.

---

## 1. Chan doan

### 1.1 Lich chay cu dem TIEN TRINH, nhung thu bi tranh la LOI

`gate._chay_theo_lich` ban cu:

```python
with ThreadPoolExecutor(max_workers=len(nang) + max(1, j)) as ex:   # 2 + 8 = 10
    cho  = [ex.submit(chay_va_in, s) for s in nang]   # bo test, da tien trinh
    cho += [ex.submit(chay_va_in, s) for s in nhe]    # tinh + frontend
```

Tac gia suy: *"10 tien trinh con tren 20 loi la vua."* Phep suy do **dung cho
nhom `tinh`** — moi buoc do that su la MOT tien trinh doc tep roi in mot dong.

No **sai cho hai loai khac**, va sai rat lon: moi tien trinh con o do lai la
mot **be tien trinh** tu no.

### 1.2 So do duoc

| Nguon | Cong thuc | Tren may 20 loi |
|---|---|---:|
| `bo test` | pytest `-n auto` | **20** worker |
| `frontend` x3 | vitest 4: `Math.min(12, numCpus - 1)` | **36** worker |
| nhom `tinh` | phan con lai cua `j` | ~5 |
| | | **~61 luong** |

⇒ **~61 luong tren 20 loi** = qua tai **3 lan**.

Cong thuc vitest doc thang tu goi da cai
(`frontend/agent-canvas/node_modules/vitest/dist`):

```js
const maxThreadsCount = Math.min(12, numCpus - 1)
```

Va ba thu muc frontend **khong cai nao** cau hinh gioi han worker.

### 1.3 ⛔ Va cai gia khong phai "gate cham"

May nay **LA production**. Bon dich vu dang phuc vu khach that tren dung 20 loi
do:

```
LTTStudioWeb   LTTStudioWorker   LTTStudioVoice   LTTStudioCodex
```

Do luc may **RANH**: CPU nen da **27%** (~5 loi) — bon dich vu + cac phien
Claude. Nen so loi that su tu do chi con ~15, khong phai 20.

### 1.4 Vi sao ba buoc frontend chay CUNG LUC voi bo test

Chung nam trong nhom `nhe`, va `nhe` duoc nop vao **cung mot**
`ThreadPoolExecutor` voi `nang`. Khong co gi tach chung ra.

Chu thich cu bien minh cho viec do: *"nhom `tinh` (7s) va `frontend` (~20s) bien
mat khoi dong ho"* — nap vao bong cua `bo test`. Lap luan ay **dung cho nhom
`tinh`** (moi buoc mot tien trinh, 7 giay) va **sai cho `frontend`** (moi buoc
mot be 12 worker).

---

## 2. Goc: **khong ai so huu ngan sach CPU**

Khong phai "song song hoa la sai". Ba cong cu, moi cong cu tu do minh theo **ca
may**, va khong tang nao biet ve hai tang kia:

- pytest hoi `os.cpu_count()` → 20
- vitest hoi `availableParallelism()` → 20 → lay 12
- gate dem tien trinh con → 10

Ba phep do dung, mot ket qua sai. Do la dinh nghia cua mot tai nguyen **vo chu**.

---

## 3. Sua

### 3.1 Mot chu so huu duy nhat cho ngan sach loi

```python
LOI_DE_DANH_CHO_MAY = 6          # bon dich vu production + he dieu hanh
LOI_TOI_DA_MOI_CONG_CU = 12      # tran vitest tu dat — khong co ly do di xa hon

def ngan_sach_loi() -> int:
    return max(2, (os.cpu_count() or 4) - LOI_DE_DANH_CHO_MAY)
```

⚠️ `6` khong phai so cho dep: no do tu CPU nen **27% luc may ranh**. Va dat 6
chu khong 5 vi mot phep do luc ranh la san cua truong hop **tot nhat**, con thu
dang bao ve la truong hop **xau nhat**.

### 3.2 Moi buoc khai so LOI, khong phai so tien trinh

`Step.so_loi`, mac dinh **1**. Chi thu nao tu sinh be tien trinh moi khai lon
hon: `bo test` = 11, `frontend` = 2, `bat bien da tien trinh` = 2.

### 3.3 Lich nhan viec theo LOI

Bo dem `con_lai` + `threading.Condition`. Hai tran cung luc, ca hai deu can:

| Tran | Han che gi |
|---|---|
| `j` | bao nhieu **BUOC** chay cung luc |
| `ngan_sach_loi()` | bao nhieu **LOI** duoc dung cung luc |

⚠️ Mot buoc lon hon ca ngan sach van chay — **mot minh** (`can = min(so_loi,
ngan_sach)`). Tu choi chay thi cong chat luong thanh vo dung tren may nho, va do
la kieu hong te hon han cham.

### 3.4 Truyen han muc XUONG cong cu con

```
bo test   -> tools/test_nhanh.py -n 11      (thay cho `-n auto`)
frontend  -> npm test -- --run --maxWorkers=2
```

⭐ Day moi la phan quan trong. Tinh ra mot ngan sach roi khong noi cho cong cu
con biet thi no van tu do minh theo ca may — ngan sach chi la mot con so trong
dau gate.

### 3.5 Lop bao ve THU HAI: uu tien thap

```python
UU_TIEN_THAP = 0x00004000        # BELOW_NORMAL_PRIORITY_CLASS
subprocess.run(..., creationflags=UU_TIEN_THAP)
```

Lop thu nhat (ngan sach) la mot **phep tinh**, va phep tinh thi co the sai. Uu
tien thi khong: du gate co nham bao nhieu, he dieu hanh van cho `LTTStudioWeb`
chay truoc.

⭐ Va gan nhu mien phi: tren may **ranh**, tien trinh uu tien thap van dung 100%
CPU. No chi nhuong khi co ai do **can** — tuc dung luc ta muon no nhuong.

---

## 4. Do TRUOC / SAU

| Phep do | TRUOC | SAU |
|---|---:|---:|
| Luong dinh tren 20 loi | **~61** | **≤ 14** (chan cung) |
| CPU dinh, gate day du | *treo may, phai reset cung* | **52 %** |
| CPU dinh, `--quick` (co 3 frontend) | — | 87 % |
| CPU dinh, `--vong-lap` | — | 34 % |
| **Gate day du, tong** | **430 s** | **291–303 s** |
| trong do `bo test` | 430 s | 287–299 s |

### ⭐ Va day la ket qua lat nguoc mot gia dinh

**Giam worker tu 20 xuong 11 lam gate NHANH HON ~31%** (430 s → 295 s).

Do la ket qua kinh dien cua qua tai: vuot diem bao hoa thi them worker chi them
tranh chap va chuyen ngu canh, **thong luong giam**. Nen `-n auto` khong chi
nguy hiem — no con **cham hon** chinh cai gioi han ma no bo qua.

⇒ Khong co danh doi nao o day. Ban cu vua nguy hiem hon vua cham hon.

---

## 5. Chot giu ket qua

`tests/test_394_nen_da_phien.py`:

| Chot | Canh dieu gi |
|---|---|
| `test_gate_khong_duoc_dat_qua_NGAN_SACH_LOI` | khong buoc nao xin qua tran; `-n` phai tuong minh; `auto` khong duoc quay lai; frontend phai co `--maxWorkers` |
| `test_tien_trinh_con_chay_o_uu_tien_THAP` | `_run` con ha uu tien |

⛔ Ca hai do **phep tinh**, khong chay gate: mot chot ve qua tai ma tu no lam
qua tai la mot chot khong ai dam chay.

---

## 6. Con lai

| Muc | Ghi chu |
|---|---|
| `LOI_DE_DANH_CHO_MAY = 6` do tren may **nay** (20 loi) | may khac thi con so nen do lai; cong thuc thi khong doi |
| `check_multiproc` khai 2 loi | dung: `test_214` dung hai tien trinh worker |
| Ba thu muc frontend van khong co `vitest.config` gioi han | co y — han muc den tu **gate**, mot chu so huu, khong rai ra ba tep cau hinh |
