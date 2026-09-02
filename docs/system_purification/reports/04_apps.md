# BAO CAO 04 — APP LAYER

Ngay: 2026-09-02 · 15 app · Cay `D:/LTTSTUDIOSAPP-p01`

---

## 1. Bang diem 15 app

| App | Route (dong) | Tang nghiep vu | jobs | gia | bang | Test cham toi |
|---|---:|---:|:-:|:-:|:-:|---:|
| `prompt_ai_ommi` | 2.051 (**10 tep**) | 8 | Y | - | Y | 9 |
| `ltt_voice` | 1.632 (**8 tep**) | 1 | Y | Y | Y | 27 |
| `agent` | 1.491 (**10 tep**) | 0 | Y | - | - | 3 |
| `vps` | **900** (1 tep) | 14 | Y | Y | Y | 17 |
| `autosubvideo` | **899** (1 tep) | 3 | Y | Y | - | 4 |
| `upscalevideo` | **882** (1 tep) | 0 | Y | Y | - | 8 |
| `taovideo` | 645 (1 tep) | 0 | Y | Y | - | 8 |
| `chataistudio` | 595 (1 tep) | 1 | - | Y | - | 3 |
| `taoclipngan` | 542 (1 tep) | 1 | Y | Y | - | 2 |
| `nexus` | 451 (1 tep) | 0 | - | - | - | 3 |
| `thumbnail` | 430 (1 tep) | 1 | Y | - | - | 19 |
| `taoanh` | 319 (1 tep) | 1 | Y | - | - | 5 |
| `qualitylab` | 209 (1 tep) | 6 | Y | - | - | 7 |
| `anhnoibo` | 0 (chi job) | 1 | Y | Y | - | 3 |
| `ltt_llm` | 0 (chi job) | 1 | Y | - | - | 9 |

---

## 2. ⚠️ MOT DIEU TOI DA KET LUAN SAI, va vi sao no dang ghi lai

Nhin cot dau, ba app trong nhu vuot xa tran 900: `prompt_ai_ommi` 2.051,
`ltt_voice` 1.632, `agent` 1.491.

**Sai.** Toi cong tong thu muc `routes/`. Linter do **TUNG TEP**, va no co ly do
duoc ghi ngay tai cho (`lint_app_contract.py:317-320`):

> *"Nguong tinh theo TUNG FILE, khong theo tong. Tach dung thi tong con to hon
> ban dau (them docstring + import cho moi module) — do chinh la muc dich: moi
> file nho lai. Do tong se phat dung cai minh muon khuyen khich."*

Do lai tung tep: ba app do **da tach thanh package route**, tep lon nhat la
`prompt_ai_ommi/routes/resources.py` 532 dong / 15 handler — duoi ca hai nguong.

⇒ Chung la **vi du lam DUNG**, khong phai vi pham. Va bai hoc rong hon: mot
phep do co the dung ve so lieu ma sai ve **don vi**, va don vi la thu quyet dinh
ket luan.

---

## 3. 🔴 Ba tep SAT TRAN — va lich su cho thay chuyen gi da xay ra

```
apps/vps/routes.py           900 dong   (DUNG BANG tran)
apps/autosubvideo/routes.py  899 dong   (kem 1)
apps/upscalevideo/routes.py  882 dong
```

Ba tep nam trong 18 dong cua mot tran 900 la dieu phai hoi. Lich su tung tep:

| Tep | Duong di |
|---|---|
| `vps` | 698 → 771 → 856 → 889 → **900** |
| `autosubvideo` | 847 → 848 → 876 → 881 → **899** |
| `upscalevideo` | 665 → 666 → 721 → **882** |

⭐ **Khong tep nao bi CAT cho vua tran.** Ca ba **tang dan roi dung lai**. Tuc
banh coc dang lam dung viec no sinh ra de lam: no chan da phinh.

⛔ **Nhung he qua la ba app dang o sat tuong.** Tinh nang tiep theo o bat ky app
nao trong ba se tao ap luc **nang tran** thay vi tach — dung cai vong
`bug → luat → ngoai le` ma `OPERATING_CONTRACT` §8 cam.

⇒ Va kho nay **da co khuon tach dung**, dang chay o ba app khac. Khong phai
phat minh gi ca.

### Vi sao Phase nay KHONG tu tach

- Prompt 04 noi thang: *"Don't split solely for line count."*
- `apps/vps/routes.py` **dang phuc vu khach tra tien** (`/vps` tra 200 cho khach
  an danh, bieu mau dang thu credit).
- Tach mot tep route 900 dong cua duong tien la mot thay doi co rui ro that,
  va no khong thuoc muc tieu "giam entropy ma khong pha behavior dung".

⇒ Ghi thanh **no co ten**, giao cho chu san pham quyet. Mot khoan no da do duoc
thi khong con la entropy.

---

## 4. ✅ DA SUA: canh bao DUY NHAT cua linter la DUONG TINH GIA

Truoc: `[WARN] qualitylab: routes.py khong thay require_login`.

Doc ma that:

| Do | Ket qua |
|---|---|
| `apps/qualitylab/manifest.py:25-26` | `public=False`, `surface="admin"` |
| moi route | `Depends(require_operator)` |
| `server/deps.py:99-106` | `require_operator` **goi chinh `require_login`** roi them 403 neu khong phai quan tri vien |

⇒ No duoc canh **CHAT HON** `require_login`, khong phai long hon. Chot chi khop
mot chuoi nen khong thay.

### Sua the nao, va vi sao khong sua kieu khac

⛔ **Khong** them `qualitylab` vao danh sach mien tru. Chinh tep do da tu canh:

> *"moi mien tru la mot app khong bi hop dong soi, va ly do mien tru thi song
> lau hon hoan canh sinh ra no"* (`SKIP_APPS`, dong 29-31)

✅ Day chot **biet them mot guard**: `GUARD_DOI_DANG_NHAP = ("require_login",
"require_operator")` o cap module.

⭐ Va chot moi (`test_308::test_guard_doi_dang_nhap_khong_chi_la_MOT_ten_ham`)
**do** dieu lam `require_operator` hop le chu khong tin loi: no doc than ham va
doi thay `require_login(request)` trong do. Ngay ma ai do bo lien ket ay,
chot do — thay vi mot lo hong an ninh im lang.

**Ket qua: 15 app · 0 ERROR · 0 WARN.**

### Vi sao dieu nay dang ke hon mot dong canh bao

Do la canh bao **duy nhat** linter phat ra tren ca 15 app. Mot cong cu chi noi
mot cau, va cau do sai, thi lan sau khong ai doc no nua. Cung bai hoc voi:
`test_362` do trong worktree · frontend do vi thieu `node_modules` · cong gac
do vi tep cua phien khac. **Bon lan trong mot ngay, cung mot lop loi:** *mot
phep kiem do vi ly do sai se day nguoi ta bo qua chinh no.*

---

## 5. Logic nghiep vu nam trong route — bon app khong co tang nghiep vu

`agent` (1.491 dong route, 0 module nghiep vu) · `upscalevideo` (882, 0) ·
`taovideo` (645, 0) · `nexus` (451, 0).

⚠️ Nhung **khong ket luan voi**: `agent` da tach route thanh 10 tep va co
`_shared.py` 338 dong — do la mot tang nghiep vu tren thuc te, chi la khong
mang ten `services/` hay `features.py`. Prompt 04 noi ro: *"Do not require
identical folder structure; require coherent ownership."*

⇒ Muc nay can **doc ma** chu khong dem thu muc. Giao cho mot dot ra soat rieng
theo app, khong lam bang mot phep dem.

---

## 6. Nam canh `server → app` (tu Phase 02) thuoc muc nay

```
server/api/streaming.py:48,509,980  -> apps.ltt_llm   (ngan sach token, alias model)
server/routes/dashboard.py:134      -> apps.anhnoibo  (gia moi anh)
server/routes/dashboard.py:150      -> apps.ltt_voice (gia moi lan doc)
```

Hop dong app khai chieu `app → server` (4 module, `SERVER_APP_CO_THE_DUNG`) va
khai ca chieu `app → app` (`APP_DUOC_DUNG_APP`), nhung **khong khai chieu
`server → app`**. Do la mot lo trong hop dong, khong phai mot vi pham cua ai.

⇒ De xuat cho Phase 06: gia va ngan sach cong khai la **hop dong cua app**, nen
`AppManifest` khai chung va `server` doc qua registry. Khi do canh bien mat ma
khong ai phai chuyen logic di dau.

---

## 7. Ket qua Phase 04

| Viec | Trang thai |
|---|---|
| Bang diem 15 app | ✅ |
| Sua dương tinh gia cua linter + chot | ✅ 0 ERROR / 0 WARN |
| Ba tep sat tran — do lich su, ghi thanh no co ten | ✅ ghi nhan, **khong tu tach** |
| Nam canh `server → app` | → Phase 06 |
| "Logic trong route" o 4 app | → can doc ma, khong dem thu muc |
