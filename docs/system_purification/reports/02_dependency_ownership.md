# BAO CAO 02 — DEPENDENCY & OWNERSHIP GRAPH

Ngay: 2026-09-02 · Do tren cay chinh `admin-mvp-v3` @ `65aef31`
Che do: **PHAN TICH. Khong xoa gi.**

---

## 0. Phase nay khac ke hoach ban dau o mot cho, va do la thay doi tot

Ke hoach goc du kien Phase 02 dung "cong cu do thi tu viet dat trong `tools/`
(tam, khong vao gate)". Thuc te: Phase -1 da phai xay do thi do **that** de lam
`gate.py --pham-vi`, nen no khong con la mot cong cu tam.

⇒ `tools/thanh_phan.py` la san pham cua Phase 02, **da co test** (`test_394`),
**da nam trong duong chay cua gate**, va **chay lai duoc bat cu luc nao**. Mot
ban do so huu chay duoc thi khong troi; mot ban do ve tay thi co.

```powershell
python tools/thanh_phan.py                      # 37 thanh phan
python tools/thanh_phan.py --do-thi core:tien   # phu thuoc + nguoi tieu thu
python tools/thanh_phan.py --test app:vps       # test nao canh no
```

---

## 1. Ban do so huu — 37 thanh phan

| Nhom | So | Ghi chu |
|---|---:|---|
| `app:*` | 15 | suy tu `apps/*/manifest.py`, khong khai tay |
| `core:*` | 7 | `tien` · `job` · `kho` · `nguoi_dung` · `provider` · `api_cong_khai` · `nen` |
| `server:*` | 4 | `auth` · `admin` · `api` · `web` |
| ngoai may A | 5 | `gateway:render` · `gateway:llm` · `sidecar:voice` · `sidecar:codex` · `agent:nexus` |
| khac | 6 | `sdk` · `frontend` · `engine:cutclipshort` · `csdl:migration` · `cong_cu` · `trien_khai` |

### Phan bo test theo thanh phan (suy tu IMPORT)

| Thanh phan | Tep test cham toi | Doc gi tu con so nay |
|---|---:|---|
| `core:nen` | **206** | `models.py`/`db.py`/`registry.py` bi ca kho dung ⇒ doi chung la doi tat ca |
| `server:web` | **132** | vo web cham moi trang |
| `core:nguoi_dung` | 123 | auth/quyen nam duoi gan het |
| `core:api_cong_khai` | 84 | |
| `core:kho` · `core:job` | 57 · 35 | |
| `app:ltt_voice` · `app:thumbnail` · `app:vps` | 27 · 19 · 17 | |
| `core:tien` | **9** | ⭐ **so nay dang chu y** — xem §4 |

---

## 2. 🔴 VI PHAM CHIEU — `server` biet ten app cu the

Hop dong app cho phep chieu `app -> server` (danh sach trang o
`lint_app_contract.py:58-61`: `server.deps`, `server.auth.session`,
`server.auth.csrf`, `server.templating`). No **khong noi gi** ve chieu nguoc lai,
va thuc te co **nam** cho:

| Tu | Toi | Lay gi |
|---|---|---|
| `server/api/streaming.py:48` | `apps.ltt_llm.ngan_sach` | ngan sach token |
| `server/api/streaming.py:509` | `apps.ltt_llm.features.ALIAS_SANG_ID` | anh xa ten model |
| `server/api/streaming.py:980` | `apps.ltt_llm.ngan_sach.mac_dinh_cho` | token ra mac dinh |
| `server/routes/dashboard.py:134` | `apps.anhnoibo.gia` | gia moi anh |
| `server/routes/dashboard.py:150` | `apps.ltt_voice.gia` | gia moi lan doc |

### Vi sao dieu nay **do duoc** chu khong chi la mot y kien kien truc

No la ly do mot thay doi trong mot app nho van keo **41% bo test**:

```
python tools/thanh_phan.py --pham-vi app:anhnoibo
  -> 2 thanh phan: app:anhnoibo, server:web
  -> 134 tep test
```

`app:anhnoibo` chi co 3 tep test cua rieng no. 131 tep con lai den tu
`server:web`, va canh do ton tai **chi vi mot dong `import`** o
`dashboard.py:134`.

⇒ No dinh kien truc nay **khong phai mot loi dep**: no la thue tra bang thoi
gian moi lan ai do sua mot app.

### ⛔ Nhung DUNG voi "sua" bang cach cat canh

Ca nam cho deu dang lam mot viec **that**: bang dieu khien phai hien gia, va
cong streaming phai biet ngan sach token cua model. Cat canh ma khong chuyen
trach nhiem la day logic sang cho khac roi goi do la sach.

Duong dung co ve la: **gia va ngan sach cong khai la mot HOP DONG cua app**, nen
`AppManifest` phai khai chung, va `server` doc qua registry thay vi
`import apps.<ten>`. Do la mot thay doi hop dong app — Phase 04/06 quyet, khong
phai Phase 02.

---

## 3. Cheo app — dung mot cho, va no co ly do

```
app:taovideo -> app:upscalevideo
  apps/taovideo/routes.py:548  from apps.upscalevideo import cost
  apps/taovideo/routes.py:577  from apps.upscalevideo.service import submit_upscale_job
```

⭐ **Cho nay da duoc khai tuong minh** trong `tools/lint_app_contract.py:87-88`
nhu mot ngoai le co ten:

```python
("apps.upscalevideo", "cost"),                        # bao gia nang cap
("apps.upscalevideo.service", "submit_upscale_job"),  # nop job nang cap
```

⇒ Day la `COMPAT` co chu, khong phai no ky thuat. Chinh chu thich o do da noi
ro gioi han: *"`from apps.upscalevideo import bat_cu_gi` van lot"*.

---

## 4. ⚠️ `core:tien` chi co **9** tep test — con so dang chu y nhat bao cao nay

`core:tien` la so credit: giu cho -> quyet toan -> hoan, cong voi thanh toan.
Do la **thu duy nhat trong kho dung toi tien that cua khach**.

| Thanh phan | Test | He trong |
|---|---:|---|
| `core:nen` | 206 | nen |
| `core:nguoi_dung` | 123 | an ninh |
| **`core:tien`** | **9** | **tien** |

⛔ **Dung doc con so nay thanh "thieu test".** No la so tep test **import truc
tiep** `platform_core/credit.py` hay `billing.py`. Mot phep kiem di qua mot job
that van cham toi tien ma khong import module tien.

⇒ Nhung no la mot **cau hoi phai tra loi bang bang chung** o Phase 07:
*bat bien "khong tieu hai lan" duoc canh o dau, va bang phep kiem nao?* Neu cau
tra loi la "trong 9 tep do" thi ty le bao ve so voi rui ro la lech.

---

## 5. Thanh phan khong ai tieu thu — 8 muc, va KHONG muc nao la DEAD

```
app:nexus · app:prompt_ai_ommi · app:taovideo · csdl:migration
frontend · gateway:llm · sidecar:codex · trien_khai
```

🔴 **Danh sach nay la mot cai bay, va no phai duoc doc nguoc.**

| Muc | Vi sao "0 nguoi tieu thu" la BINH THUONG |
|---|---|
| 3 `app:*` | App duoc nap **DONG** (`registry.py:894` `iterdir()` + `importlib`). Mot app **dung** khi khong ai import no — do la hop dong app hoat dong dung |
| `gateway:llm`, `sidecar:codex` | deploy o **may khac**. Khong caller o may A la dieu du kien |
| `frontend` | chay bang `npm`, khong bang `import` Python |
| `csdl:migration` | Alembic goi bang CLI |
| `trien_khai` | `.ps1`, khong ai import |

⇒ **Khong muc nao trong danh sach nay duoc mang sang Phase 03 nhu "ung vien
xoa".** Chung o day de ghi rang phep do tinh **da nhin** va **da giai thich**,
chu khong phai de bi xoa.

---

## 6. God-module

| Thanh phan | Phu thuoc | Doc the nao |
|---|---:|---|
| `cong_cu` (`tools/`) | 20 | ⚪ **binh thuong**: 140/148 tep la CLI, chung phai cham moi khu |
| `server:web` | 15 | 🟡 dang xem: gom ca `sdk` (canh dong `GOI_TAI`) va **2 app** |
| `server:api` | 7 | 🟡 gom `app:ltt_llm` |
| `app:taoanh` | 7 | ⚪ binh thuong: app dung 4 dich vu nen + 2 duong `server` trong danh sach trang |

---

## 7. Ket qua giao cho phase sau

| Muc | Giao cho | Viec cu the |
|---|---|---|
| 5 canh `server -> app` | **06** (va hop dong app o **04**) | dua gia/ngan sach vao `AppManifest`, doc qua registry |
| `core:tien` chi 9 tep test import truc tiep | **07** | chung minh bat bien tien duoc canh o dau |
| `app:taovideo -> app:upscalevideo` | **04** | giu (COMPAT co khai) hay dua len `platform_core` |
| `server:web` phu thuoc 15 | **06** | tach theo trach nhiem, khong theo so dong |
| 8 muc "khong ai tieu thu" | — | ⛔ **da giai thich, khong mang sang 03** |

---

## 8. Trang thai phan loai sau Phase 02

| Class | So | Ghi chu |
|---|---:|---|
| ACTIVE | 37 | moi thanh phan deu co duong song hoac ly do ro |
| DEAD | **0** | ⛔ chua muc nao du bang chung |
| COMPAT | 1 | `taovideo -> upscalevideo` (khai o linter) |
| UNKNOWN | 0 | moi "0 nguoi tieu thu" deu da giai thich duoc |

⇒ Vao Phase 03 voi **khong** ung vien xoa nao san co. Do la ket qua dung: Phase
03 phai tu tim bang chung, khong duoc thua ke mot danh sach doan.
