> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# BAO CAO 09 — FRONTEND, I18N, TESTS & TOOLING

Ngay: 2026-09-02

---

## 1. i18n — 774 chuoi, va **62% khong ai thay**

Phan loai theo **do lo ra voi khach**, khong theo so luong:

| Nhom | Chuoi | Ty le | Khach co thay khong |
|---|---:|---:|---|
| `job/service` cua app | 233 | 30 % | ❌ noi bo |
| `platform_core` | 229 | 29 % | ❌ noi bo |
| **route cua app** | 149 | 19 % | ✅ **CO** |
| **template `.html`** | 145 | 18 % | ✅ **CO** |
| `server` | 18 | 2 % | ❌ |

⇒ **294/774 (38 %) that su den tay khach.** Con lai la thong diep loi cho admin,
log, va van ban noi bo.

### ⛔ Va Phase nay KHONG dich chuoi nao

Dich 294 chuoi la **viec noi dung**, khong phai viec don dep. Mot ban dich may
lam ra se ha duoc con so ma khong ai doc lai — dung kieu "ha moc bang TRICH LAI
thay vi bang DICH" ma bo nho du an da ghi la mot cach lam sai.

⇒ San pham cua Phase 09 o muc nay la **thu tu uu tien do duoc**, de nguoi lam
noi dung biet 294 cho nao dang lam khach thay tieng Viet trong ban tieng Anh.

---

## 2. 🔴 Trung so tep test — chot da chan tuong lai, nhung goc van mo

### 2.1 Hien trang

```
So tep test bi trung so: 22 | moc: 22
```

Cac cum nang nhat nam lien nhau — `151`…`164` — moi so hai hoac **ba** tep.

### 2.2 Goc da duoc ghi tu 23/08, va no dung

`tools/check_so_test.py` viet:

> *"Nguyen nhan khong phai ai cau tha. Repo nay dang co **nhieu phien lam viec
> song song**, moi phien chon so tiep theo dua tren thu no nhin thay luc bat
> dau — nen hai phien bat dau cung buoi chieu se chon trung nhau, **deu dung
> theo cach ho nhin**."*

Va quyet dinh luc do cung dung: **khong di doi ten 24 tep**, vi *"doi ten la
chay theo duoi — ba tep toi vua tao da bi trung lai trong cung buoi"*.

### 2.3 Nhung chot chi chan TANG, khong dong GOC

Hai phien van chon trung. Hau qua chi **doi cho**: tu "trung ngay luc tao" sang
"gate do luc merge", roi mot nguoi phai di doi ten tep cua nguoi khac.

Va no vua xay ra **trong luc chuong trinh nay chay**:

| Cay | Tep | |
|---|---|---|
| `admin-mvp-v3` | `test_394_nen_da_phien.py` | (cua chuong trinh nay) |
| `.claude/worktrees/ltt-voice-…` | `test_394_ltt_voice_nghe_thu.py` | **trung** |

⇒ Khi ho merge: 23 > moc 22 ⇒ **RESULT: FAIL**. Da nhan bao truoc cho phien do.

⭐ Va phien `asv` **tu giai duoc** bang cach lay dai `400+` — dung loi giai, chi
la no phai duoc nghi ra lai moi lan.

### 2.4 Sua: cap DAI SO luc TAO CAY

`cay_rieng.py tao <ten>` nay in ra:

```
DAI SO TEST cua cay nay: 500-599
  (so cao nhat dang dung tren MOI cay: 424)
```

⚠️ **Dem tren MOI cay, khong chi cay chinh** — dem mot cay la lap lai dung cai
loi "chon theo tam nhin rieng". Chot `test_cap_dai_so_test_dem_tren_MOI_cay`
cuong che dieu do.

⭐ Day khong phai mot luat moi de nho: **cong cu tu noi ra, dung luc nguoi ta
can biet**. Va no khong dong quy uoc cu — `check_so_test.py` van giu moc.

---

## 3. Frontend

| Do | Ket qua |
|---|---|
| So thu muc | 3 (`agent-canvas`, `autosub-studio`, `prompt-ai-ommi`), 47 tep ts/js |
| `gate.FRONTENDS` co day du khong | ✅ 3/3; `test_145` cuong che |
| Cache-bust | ✅ `ASSET_VER` bam noi dung 6 tai san; `test_369` doi moi tep mang `?v=` phai tham gia bam |
| Gioi han worker | ✅ **da them** `--maxWorkers=2` (Phase 08b) — truoc do moi bo tu lay 12 |
| `vitest.config` rieng | khong co, **co y**: han muc den tu gate, mot chu so huu |

### ⚠️ Mot han che that, ghi ro

Ba buoc frontend **khong chay duoc trong cay rieng** (`node_modules` khong nam
trong git). Chung tu khai `BO QUA` va hien o dong `RESULT` — khong im lang.
Muon chung minh frontend thi chay tren cay chinh.

---

## 4. Tests

| Do | Ket qua |
|---|---|
| Tep | 360 (`tests/*.py`), 323 so phan biet |
| Khoang trong so | 38 — khop dot go `socialbot`/`demo`, khong phai bo quen |
| Trung so | **22** (xem §2) |
| Bo qua im lang | ✅ `check_bo_qua` PASS — 2 muc da khai (`test_73`, `test_74`) |

### 🔴 Mot phat hien tu phien khac, dang ghi lai

Phien `asv` bao: `test_406_asv_tach_tieng.py` goi **demucs that** tu ben trong
mot worker pytest.

⇒ `-n auto` × demucs la phep **NHAN**, khong phai phep **CONG**. Do la manh con
thieu trong phep tinh qua tai o bao cao 08b.

⚠️ Nhung do **truoc khi xay**: `test_nhanh.py:219` chay `--dist loadfile` —
tron mot tep di vao MOT worker, va cac test trong tep chay noi tiep. Neu do la
tep duy nhat sinh viec ML nang thi phep nhan **khong xay ra**, va them mot co
che se khong doi gi.

⇒ Da bao lai phien do: **do truoc, xay sau**. Tep cua lane ho.

### ⛔ Va mot duong sua CUA HO ma toi da can

Ho dinh cho `test_406` xin khoa `cua_so_yen`. Nhung `gate.py:491` khai buoc
`bo test` giu dung khoa `cpu_nhieu` **suot ca luot**:

```
gate.py (GIU cpu_nhieu) -> test_nhanh -> pytest -n 11 -> worker -> test_406 -> xin cpu_nhieu
```

Mot phep kiem doi mot khoa ma **ong noi cua chinh no dang giu**. Co
`cho_toi_da_s` nen khong treo vinh vien, nhung thanh thu te nhat: **luon** doi
tron N giay roi chay **khong co khoa**.

---

## 5. Tooling / gate

| Do | Ket qua |
|---|---|
| Buoc | 26, 5 nhom, 21 checker |
| Ngan sach CPU | ✅ **moi** — 14/20 loi, xem 08b |
| Uu tien tien trinh con | ✅ **moi** — `BELOW_NORMAL_PRIORITY_CLASS` |
| Ho so | 5 (`nhanh`/`vong-lap`/`pham-vi`/`doi`/`day-du`), **moi ho so khai no KHONG chung minh gi** |
| Kho ket qua | ✅ `test-results/gates/<id>.json` — ngoai git VA ngoai deploy |
| Cong gac di lac vao cay phien khac | ✅ **da sua** (`.claude` vao `BO_QUA`) |
| Banh coc chi GHI con so | ✅ **da sua** (`check_server_routes` nay so gia tri) |

### Ratchet: truoc / sau ca chuong trinh

| Banh coc | Dau | Cuoi |
|---|---:|---:|
| Nuot loi lang le | 63 | **62** |
| Kich thuoc route server | 2 tep | **1 tep** |
| App-contract WARN | 1 | **0** |
| i18n | 774 | 774 (xem §1) |
| Trung so test | 22 | 22 |

⚠️ **Khong moc nao bi NANG.** Ba moc giam that; hai moc giu nguyen va ghi ro ly do.

---

## 6. Con no

| Muc | Phase / chu |
|---|---|
| 294 chuoi i18n khach thay | viec **noi dung**, khong phai don dep |
| 22 so test trung san co | ⛔ khong doi ten (chay theo duoi); dai so chan tuong lai |
| `test_406` × xdist | lane `asv` — **do truoc, xay sau** |
| 140 diem vao CLI trong `tools/` | chua kiem ke |
| `public_api/` 12.233 dong — export mo coi | ⚠️ phai doi chieu 5 co che nap dong truoc |

---

## 7. ⭐ Mot co che nhan thuc, do duoc HAI lan trong cung mot ngay

Phien `ltt-voice` dat ten cho no chinh xac hon toi:

> *"O worktree, `.git` **DUNG LA** mot tep — nen 'phep kiem nay chi dung o cay
> chinh' la mot loi giai thich **vua van** toi muc khong ai di kiem tiep."*

Do khong phai cau tha. Mot gia thuyet **SAI** khop **HOAN HAO** voi trieu chung
thi no khong moi ai kiem tiep — no **ket thuc** viec dieu tra. Cho do trong
giong dich den.

### Hai lan, cung mot ngay, cung mot co che

| Loi giai thich "vua van" | Dung o dau | Sai o dau | Gia phai tra |
|---|---|---|---|
| *"phep kiem nay chi dung o cay chinh"* | `.git` o worktree that su la mot TEP | that ra la `GOC` suy tu `__file__` | **BA phien** cung xep nham `test_362` vao nhom "khong the xanh trong worktree" |
| *"frontend nap vao bong cua bo test"* | dung cho nhom `tinh` (7s, mot tien trinh) | sai cho frontend (mot **be** 12 worker) | **HAI lan** may treo phai reset cung |

### Vi sao dang ghi

Ca hai loi giai thich deu **nam san trong chu thich**, deu **nghe hop ly**, va
deu **dung mot phan**. Do la dang nguy hiem nhat: mot chu thich sai hoan toan se
bi nghi ngo, con mot chu thich dung-mot-nua thi duoc tin.

⇒ Cach thoat khong phai "doc ky hon". La **do**:

- `test_362` lo ra khi chay gate day du **trong** mot worktree — viec chua ai lam;
- qua tai CPU lo ra khi **dem luong** thay vi dem tien trinh con.

Ca hai deu can mot phep do ma **hinh dang cua chu thich khong goi y ra**.

