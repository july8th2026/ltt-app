> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# BAO CAO 05 — PLATFORM CORE

Ngay: 2026-09-02 · 122 tep / 29.657 dong · do tren `admin-mvp-v3`

---

## 0. Ket qua mot dong

**Khong hop nhat gi, khong xoa gi.** Nam bat bien nguy hiem nhat cua
`platform_core` deu **da co chu so huu duy nhat va da co phep kiem**. Bai hoc
cua H36/H37/H38 da duoc the che hoa, khong con nam trong tri nho ai.

---

## 1. Ban do kich thuoc

| Muc | Dong | Ghi chu |
|---|---:|---|
| `public_api/` (43 tep) | **12.233** | he con lon nhat |
| `agent/` (11 tep) | 1.824 | |
| `nexus/` (10 tep) | 1.780 | |
| **`job_runner.py`** | **1.640** | tep don lon nhat; noi H36 tim ra ba loi P0 |
| `llm/` (8 tep) | 1.560 | |
| `registry.py` | 1.039 | kham pha app (dong) |
| `models.py` | 923 | |
| `image_gen/` (5 tep) | 786 | |
| `credit.py` | 678 | **duong tien** |
| `jobs.py` · `storage.py` · `admin_console.py` | 437 · 428 · 413 | |
| `payments/` (2 tep) | 171 | |

---

## 2. 🔴 Cau hoi trung tam: MOI viec nen co nam sau lease khong?

H36 (2026-08-16) sua ba loi P0 **cung mot goc**: moi vong nen duoc viet nhu the
chi co mot tien trinh chay no, trong khi so tien trinh worker mac dinh bang **so
GPU**. He qua: webhook gui trung, canh bao trung, viec don chay N lan.

### Do lai hom nay — va cau tra loi chinh xac hon "co"

Kho co **ba** loai viec nen, va chung duoc xu ly **khac nhau, dung cach**:

| Loai | O dau | Bao ve bang gi |
|---|---|---|
| **Phai chay MOT lan** | trong `_mot_luot_bao_tri` (dong 1.473–1.532): don du lieu het han · giao webhook · ghi metrics · bao tri app · quet canh bao · quet giu cho treo · tu hoan giu cho treo · quet so GPU | `leases.MAINTENANCE`, lay truoc vong (dong 1.566), **dap nhip moi luot**, mat lease thi **dung viec nen** (1.578) |
| **Phai chay MOI tien trinh** | `_xa_metrics()` (1.325) | ⭐ **CO Y nam ngoai lease**, ly do viet ngay trong docstring |
| **Nhieu tien trinh cung dung mot bang** | `jobq.reclaim_orphans()` (jobs.py:379) | `with_for_update(skip_locked=True)` |

### ⭐ Hai cho "ngoai lease" khong phai lo hong — chung la thiet ke

`_xa_metrics` (job_runner.py:1326-1331), nguyen van:

> *"Co y **khong** nam trong vong bao tri: vong do chi chay o mot tien trinh,
> con bo dem thi moi tien trinh mot ban. De leader xa ho nghia la mat so cua
> moi tien trinh con lai — va mat mot cach **im lang**, vi tong van ra mot con
> so trong hop ly."*

`reclaim_orphans` (jobs.py:388-390):

> *"SKIP LOCKED: hai worker cung reclaim khong duoc nhat trung mot orphan (neu
> khong, ca hai `fail()` no → attempts += 2, dem sai luot)."*

⇒ Ca hai deu tra loi dung cau hoi "N tien trinh thi sao", **truoc khi** ai hoi.
Do la khac biet giua mot he thong da hoc va mot he thong may man.

### Cac luong khac — deu dung pham vi

| Luong | Pham vi | Dung? |
|---|---|---|
| `job_runner.py:303` nhip GPU | **mot job** | ✅ |
| `job_runner.py:449` dong ho qua gio | **mot job** | ✅ |
| `llm/admission.py:156` `keep_alive` | **mot lease cu the** (theo `lease_id`) | ✅ |
| `job_runner.py:1616` vong worker | **moi tien trinh** — dung y do | ✅ |

---

## 3. Trung chu so huu — kiem hai vung nghi ngo nhat, ca hai deu SACH

### 3.1 Tinh tien: `registry` vs `public_api/pricing.py`

Nghi van hop ly, vi ca hai deu noi ve credit. Nhung chung tra loi **hai cau hoi
khac nhau**:

| | So huu gi |
|---|---|
| `registry.py:226` `credit_cost` tren **manifest** | **app** so huu gia cua chinh no |
| `public_api/pricing.py` | **che do gia da CONG BO** cho `/api/v1`: tao ban, dang, len lich, thu hoi, `apply_bounds` |

Va `pricing.py` **tu noi** ai la chu (dong 7): *"`credit_cost(params)` in its
manifest, and `registry.credit_for()` is the..."*.

⭐ **Bat bien tu hai vu that duoc cuong che o dung mot cho.** Loi "xin 4 anh,
tra 2, van thu tien 4" xay ra **hai lan** (H38 23/08, roi H37 24/08), ca hai
cung goc: handler khong bao `credit_cost`. Nay `registry.py:835-840` **fail
SOM ngay luc discover**:

> *"app sinh job ma KHONG khai `credit_cost`"* → nem loi luc nap app, khong doi
> toi luc mot khach bi thu nham.

⇒ Mot bat bien da hong hai lan nay khong the hong lan ba **ma khong ai biet**:
no chan o buoc nap, truoc moi request.

### 3.2 Backoff / cooldown: **mot chu so huu**, khong phai ba

`grep` cho tam bon tep. Doc tung cho:

| Tep | Thuc su lam gi |
|---|---|
| `api_pool.py` | ⭐ **CHU SO HUU**: 401/403 → cooldown ngan + `disable` sau nguong; 429 → cooldown theo `retry-after`; tu hoi cooldown het han |
| `image_gen/cong_render.py:10` | **chu thich canh bao** |
| `llm/dieu_phoi.py:27` | **chu thich canh bao** |
| `llm/cong_vlm.py:10` | **chu thich canh bao** |

Ba cho sau khong cai dat gi — chung nhac luat **"Ban ≠ hong"**: khi may B ban,
tuyet doi khong goi `api_pool.danh_dau_loi()`, vi cooldown roi `disable` sau 5
lan se lam **mot toi chay video tu tat vinh vien model nha** (D-005).

### ⭐ Va luat do **KHONG chi song bang chu thich**

`tests/test_255_dieu_phoi.py` neo bon tinh chat, doc nguyen van:

1. *"Ban ⇒ di tiep provider sau, va KHONG `danh_dau_loi`"* — kem so hieu su co
2. *"Loi that ⇒ CO `danh_dau_loi`, roi moi di tiep"*
3. *"Vuot ngan sach ⇒ nem ngay, KHONG cascade"*
4. *"Thu tu do ben goi khai"*

⇒ Day la khuon dung: **mot chu so huu · nhieu chu thich chi ve no · mot bo test
neo hanh vi**. Khong phai thu de hop nhat.

---

## 4. Ket qua doi chieu voi muc tieu cua Phase 05

| Muc tieu prompt | Ket qua |
|---|---|
| hop nhat helper trung | **khong tim thay** trung nao trong hai vung nghi ngo nhat |
| dua logic rieng cua app ve lai app | `platform_core → apps` = **0** import (do o Phase 02) |
| xoa export khong ai dung | ⏳ chua do — can phan tich rieng, xem §5 |
| gop chinh sach canh tranh | khong co chinh sach nao canh tranh |
| lap SSOT o cho deploy cho phep | da co: manifest so huu gia, `api_pool` so huu cooldown, `leases` so huu viec nen |

---

## 5. Con no cua Phase 05

| Muc | Vi sao chua lam |
|---|---|
| Export khong ai dung trong `public_api/` (12.233 dong) | Can phan tich AST rieng. ⚠️ Va phai **doi chieu 5 co che nap dong** truoc — `public_api` co dispatch tool bang chuoi |
| `job_runner.py` 1.640 dong | Lon, nhung **khong co bang chung no dat sai cho**. Prompt 05 canh: *"large file alone ≠ reason to split"* |
| `models.py` 923 dong | nhu tren |

⛔ **Khong tach gi trong phase nay.** Prompt 05 doi *"behavior-first tests before
structural change"* cho job/credit/billing/storage/provider — va cac bo test do
**da co san va da xanh**. Tach ma khong co ly do ngoai so dong la them rui ro
doi lay mot con so dep hon.

---

## 6. Phan loai sau Phase 05

| Class | Ghi chu |
|---|---|
| ACTIVE | toan bo `platform_core` |
| DUPLICATE | **0** |
| DEAD | **0** (chua do het `public_api/` — ghi thanh no, khong doan) |
| UNKNOWN | export cua `public_api/` |
