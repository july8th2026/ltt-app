# BAO CAO 08 — ERRORS, CONFIG, DEPLOYMENT & RUNTIME DEBT

Ngay: 2026-09-02 · Kem `08b_ngan_sach_cpu_gate.md` (chan doan qua tai CPU)

---

## 1. Nuot loi lang le — 63 cho, va **khong** log may moc cai nao

Prompt 08 noi thang: *"Do not mechanically log every exception."* Nen viec dau
tien la phan loai, khong phai sua.

### 1.1 Phan bo

| Tep | So cho | Ty le |
|---|---:|---:|
| **`server/templating.py`** | **14** | **22 %** |
| `apps/taovideo/jobs.py` + `assets.py` | 10 | 16 % |
| `server/deps.py` · `access_middleware.py` | 6 | |
| 20 tep khac | 33 | |

### 1.2 Cum lon nhat: `server/templating.py` — 14 cho, **KHONG mot dong log**

Tep khong he co logger. Ca 14 khoi deu tra ve mot gia tri lanh:

```
:67  -> "0"      :263 -> loaded   :356 -> ""     :407 -> pass
:219 -> ""       :295 -> None     :369 -> False  :446 -> None
:236 -> []       :314 -> None     :379 -> {}     :466 -> []
:325 -> False    :392 -> sid=None
```

### 1.3 ⭐ Phan loai — va 13/14 la ĐÚNG khi im lang

Cau hoi khong phai *"co nuot khong"* ma *"nuot ve phia nao"*:

| Cho | Suy giam ve phia | Ket luan |
|---|---|---|
| `_is_admin` → `False` | **AN TOAN** — coi nhu khong phai admin | im lang OK |
| `_da_dang_nhap` → `False` | **AN TOAN** — coi nhu chua dang nhap | im lang OK |
| sidebar → `[]` | **AN TOAN** — hien it hon that co | im lang OK |
| `_VER` → `""` | tham my | im lang OK |
| … 9 cho con lai | deu tra gia tri rong/None | im lang OK |
| 🔴 **`_tinh_asset_ver` → `"0"`** | **NGUY HIEM** | **phai keu** |

⇒ *"Hong thi khach thay **it hon**"* la mot chuyen. *"Hong thi khach thay **sai
hon**"* la mot chuyen khac han.

### 1.4 🔴 Mot cho: co che chan su co lai co duong hong dan ve chinh su co do

`_tinh_asset_ver()` bam noi dung 6 tai san tinh → `?v=<hash>`. Doi tep = doi
hash = doi URL = Cloudflare tai moi ngay.

Thieu **mot** tep thi hash thanh hang so `"0"`, va tu do **moi khach nhan ban
tai san CU** cho toi khi het TTL. Trang van render dep, khong loi nao o dau ca.

⛔ Va do **dung la su co `CLAUDE.md` quy tac 6 ghi lai**: sau khi sua `ltt.css`,
CF phuc vu ban cu 4 tieng, chip hien thanh radio tho du origin da dung.

⇒ Co che sinh ra de chan su co do co mot duong hong **lang le** dan thang ve
chinh su co do.

Da chung minh bang phep do, khong bang suy dien:

```
asset_ver hien tai : a2502280
neu thieu 1 tep    : 0        <- hang so, khong con la bam
```

### 1.5 Sua: **nuot CO TIENG**, khong phai "nem thay vi nuot"

Ham nay chay luc `import`; nem thi may chu khong khoi dong. Nen duong lui phai
giu — chi la no phai noi ra.

⚠️ Va cho nay dang chu y: `tests/test_369` **da co** mot chot ten
`test_ham_tinh_khong_bao_gio_nem_ra_ngoai`, docstring viet *"nhung phai noi
ra"* — nhung phep khang dinh chi doi co `except` va `return "0"`. **Loi hua
nam trong docstring, khong nam trong phep kiem.**

⇒ Nen viec lam khong phai them mot luat moi ma **hoan thanh mot loi hua da co**.
Chot moi `test_khi_MAT_duong_lui_thi_phai_KEU` goi that ham do voi mot tai san
thieu roi doi thay tieng keu — **do hanh vi, khong do chuoi ma nguon**.

### 1.6 Ket qua

```
Nuot loi lang le: 63 -> 62   (`--update` da ha moc)
```

⚠️ Ha moc **sau khi** no giam that, dung `OPERATING_CONTRACT` §9. Va chi giam 1
— vi 13 cho con lai duoc **giu co chu y**, moi cho co ly do ghi ngay tai do.

---

## 2. Qua tai CPU — xem `08b_ngan_sach_cpu_gate.md`

Muc nay dang le la mot dong trong bao cao 08, nhung no lon hon the: **hai lan
may treo phai reset cung**. Tom tat:

| | TRUOC | SAU |
|---|---:|---:|
| Luong dinh / 20 loi | ~61 | ≤ 14 |
| CPU dinh, gate day du | *treo may* | 52 % |
| Gate day du | 430 s | 291–303 s |

Goc: gate dem **tien trinh**, thu bi tranh la **loi**. Khong ai so huu ngan
sach CPU — pytest hoi `os.cpu_count()`, vitest hoi `availableParallelism()`,
gate dem tien trinh con. Ba phep do dung, mot ket qua sai.

---

## 3. Cau hinh · trien khai — da kiem, khong sua

| Do | Ket qua |
|---|---|
| `secrets/app.env` tren **production** | ⛔ ACL chan doc — lop bao ve hoat dong dung |
| `secrets/` trong **kho** | doc duoc; chua `LTT_DATABASE_URL` + mat khau superuser |
| Danh sach `/XD` cua `robocopy` | co `data secrets logs .git test-results tmp node_modules .claude` — `test-results/` **da** duoc loai tru, nen kho ket qua gate khong len production |
| Deploy chep **ca tep chua theo doi** | ✅ da ghi vao `cay_rieng.py` va `DEVELOPMENT_WORKFLOW.md` |
| PostgreSQL | dang chay :5432, `scram-sha-256` cho moi ket noi |
| CSDL test co san | `lttplatform_test`, `ltt_multiproc_test`, `lttplatform_multiproc_test` |

### 🔴 Ha tang co, day noi thi khong

Ba CSDL test **da ton tai** — ai do da dung chung cho dung muc dich nay. Nhung
`LTT_TEST_DATABASE_URL` khong duoc dat o dau ca, nen `test_73` (7 phep kiem
dong thoi) va `check_multiproc` deu bo qua o **moi** luot gate.

⇒ Bon chu `BO QUA` o dong RESULT la thu duy nhat noi ra dieu do. Xem bao cao 07.

---

## 4. Con no cua Phase 08

| Muc | Vi sao chua lam |
|---|---|
| 10 cho nuot loi o `apps/taovideo` | can doc tung cho; chua co bang chung cho nao nguy hiem |
| So dang ky env/config day du (`key → owner → reader → default`) | ⛔ doi doc `secrets/app.env` production — **ACL chan**, va do la dieu dung |
| Dien tap `update.ps1` / rollback | ⛔ ngoai pham vi: chuong trinh nay **khong deploy** |
