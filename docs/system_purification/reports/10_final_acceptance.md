# BAO CAO 10 — NGHIEM THU CUOI, COMMIT & PUSH

Ngay: 2026-09-02 · Nhanh `admin-mvp-v3` · HEAD `ea81c7a`
Vai tro cua phase nay: **nguoi nghiem thu doc lap**, khong them y tuong moi.

---

## 1. Trang thai luc bat dau nghiem thu

| Muc | Gia tri |
|---|---|
| Nhanh | `admin-mvp-v3` (khong phai `master`) |
| HEAD | `ea81c7a` — cay chinh va cay `p01` **trung nhau** |
| Cay ban | chi `?? docs/auto_scan_video/` — **cua phien khac**, khong dung toi |
| So voi `origin` | **truoc 12 commit** (7 cua chuong trinh nay, 5 cua phien khac) |

---

## 2. Bang chung — va lan nay **khong con buoc nao khong chung minh duoc**

### 2.1 Gate day du

```
RESULT: PASS   [4 BUOC TU BO QUA]
        bo test (song song)  285.4s
        test-results/gates/20260902T135643Z-9884.json
```

### 2.2 ⭐ Bon buoc "tu bo qua" — da dong RIENG, khong de treo

Moi luot gate truoc deu ket thuc voi bon buoc khong chay duoc trong cay rieng.
Chung **tu khai** ra dieu do (dung thiet ke), nhung mot ban nghiem thu cuoi ma
bon buoc quan trong nhat khong co bang chung thi khong phai nghiem thu.

| Buoc | Vi sao bo qua | Chay lai o dau | Ket qua |
|---|---|---|---|
| frontend `agent-canvas` | `node_modules` ngoai git | cay chinh | **52 pass** |
| frontend `autosub-studio` | nt | cay chinh | **15 pass** |
| frontend `prompt-ai-ommi` | nt | cay chinh | **24 pass** |
| bat bien da tien trinh (`test_214`) | `secrets/` ngoai worktree; ACL chan `C:\LTTPlatform\secrets` | **CSDL PostgreSQL vut di** | **7 pass** (134s) |

⭐ `test_214` la thu duy nhat chung minh **webhook khong gui trung, canh bao
khong nhan doi, va so credit khop khi nhieu tien trinh worker chay cung luc**.
No da bo qua o **moi** luot gate tu truoc toi nay. Day la lan dau no xanh trong
chuong trinh nay.

⛔ CSDL `ltt_p10_test_20260902205943` da **xoa o `finally`**; production
`lttplatform` khong bi dung toi.

### 2.3 Bo kiem trong diem theo mien

| Mien | Tep | Ket qua | CPU dinh |
|---|---:|---|---:|
| `server:auth` (xac thuc, cach ly) | 4 | **85 pass** | 14 % |
| `core:tien` (credit, billing, thanh toan) | 9 | **111 pass** | 33 % |
| `core:job` (hang doi, idempotency, huy, lease) | 35 | **593 pass**, 7 skip | 28 % |
| trien khai (cai dat, release, rollback) | 10 | **250 pass** | 17 % |

*(7 skip cua `core:job` chinh la nhom PostgreSQL da chung minh rieng o §2.2.)*

### 2.4 Kiem TRINH DUYET that — `/gia-api`

`server/routes/dashboard.py` doi cach lay bang gia, va `/gia-api` la **trang
cong khai khach chua dang nhap xem duoc**. `CLAUDE.md` quy tac 5/5b doi kiem
tren trinh duyet.

⛔ Khong kiem duoc tren production: production dang chay ban **cu**, chua co
thay doi nay. Nen: dung mot ban **co lap** (sqlite tam, `LTT_DATA_DIR` tam,
cong 8123) theo dung cong thuc cua `tests/test_274`, roi mo bang Playwright.

| Do | Ket qua |
|---|---|
| Bang gia LLM | ✅ hien, co `1 credit = 100đ` + phien ban gia |
| Bang gia **anh** | ✅ t2i **3** credit / 300đ · edit **9** / 900đ · vi du 4 anh **12** / 1.200đ |
| Bang gia **tieng** | ✅ **12 / phut** · nhan ban giong **2** · ma gia `ltt-voice-2026-08-30a` |
| Loi console | **0** |
| Request that bai | **0** (5/5 tra 200) |
| `?v=` cua tai san | `a2502280` — **khong** phai `"0"` |

⭐ Dong cuoi la mot phep do ngoai du dinh: no chung minh ban va
`_tinh_asset_ver` cua bao cao 08 **dang song trong trinh duyet that**, khong chi
trong test.

🔴 Va day la cho nguy hiem nhat cua thay doi nay, nen phai noi ro no da duoc do:
neu `bang_gia_cong_khai()` tra rong cho mot app thi trang **van 200, van dep**,
chi mat mot bang gia. `assert status_code == 200` khong bao gio thay dieu do.
Con so `3 / 9 / 12` o tren la thu thay duoc.

---

## 3. Dong phan loai

| Class | So | Trang thai cuoi |
|---|---:|---|
| ACTIVE | 30 | — |
| FROZEN | 1 | `cutclipshort/` — bien gioi **sach**: 7 cho nhac toi deu la **loai tru** (`build_release`, `check_bien_dich`, `scan_source_secrets`, `thanh_phan.toml`), **khong** cho nao `import` |
| HISTORICAL | 6 | chi con trong **chu thich giai thich vi sao da go** |
| COMPAT | 1 | `taovideo → upscalevideo`, khai o linter |
| **DEAD** | **0** | ⛔ khong muc nao du bang chung de xoa — **khong xoa gi** |
| UNKNOWN | **0** | — |

### Quet mau thuan cuoi: **0**

| Ten he con da go | Tham chieu trong ma SONG |
|---|---:|
| `apps.demo` / `apps/demo` | 0 (4 tep chi la chu thich lich su) |
| `socialbot`, `kichban`, `mediatools` | **0** |
| `core/` | thu muc **khong ton tai** |
| `check_cay_chinh` | 0 (1 cho la chu thich ghi lai chinh loi do) |
| Migration | 65 ban, **1 head**, khong doi |
| Hop dong app | 15 app · **0 ERROR · 0 WARN** |

---

## 4. TRUOC / SAU ca chuong trinh

| Do | Dau | Cuoi |
|---|---:|---:|
| Gate day du | **430 s**, treo may 2 lan | **291–303 s**, CPU dinh 52 % |
| Luong dinh / 20 loi | ~61 | **≤ 14** |
| Nuot loi lang le | 63 | **62** |
| Tep route server vuot nguong | 2 | **1** |
| App-contract WARN | 1 | **0** |
| i18n chua boc | 774 | 774 *(294 lo ra voi khach — viec noi dung)* |
| Trung so tep test | 22 | 22 *(goc da dong; khong doi ten cu)* |
| `CLAUDE.md` | 496 dong, bang chep tay | **263 dong**, tro ve mot **lenh** |
| Buoc gate khong co bang chung | 4 | **0** *(da chung minh rieng)* |

⚠️ **Khong mot moc banh coc nao bi NANG.**

---

## 5. Red-team — 13 cau, tra loi bang phep do

| # | Cau hoi | Tra loi |
|---|---|---|
| 1 | He con cu con voi toi duoc khong? | Khong — quet 0 tham chieu song |
| 2 | Co hai chu so huu cho mot thu khong? | Da **bot** mot: bang gia tung co o app **va** o route; nay chi app so huu |
| 3 | Lich su con hoat dong? | Khong — chi con chu thich |
| 4 | Chot loi thoi khoa nham? | `test_362` da sua (hoi git thay vi suy tu `__file__`); `test_369` da **hoan thanh loi hua trong docstring** |
| 5 | Banh coc dang che loi? | Ca 4 dung **dung moc**; `check_server_routes` truoc chi GHI so luong — **da sua** de so gia tri |
| 6 | Nguon cau hinh mau thuan? | Khong thay; `LTT_*` doc qua mot duong |
| 7 | App di vong hop dong? | Linter: 0 ERROR 0 WARN |
| 8 | Server chua nghiep vu trung? | Da go: `dashboard.py` thoi import app theo ten |
| 9 | Retry/backoff chong tang? | 10 cho khai retry, **chua kiem ke** → ghi thanh no |
| 10 | Tien / kho / xac thuc bi yeu di? | **Khong cham mot tep nao** trong nhom do — `git diff --name-only` xac nhan |
| 11 | Cai dat / cap nhat / rollback con dung? | 250 phep kiem xanh |
| 12 | Xoa mat phu thuoc migration/du lieu? | 1 head, khong xoa migration nao |
| 13 | Gate co the don gian hon ma khong mat do phu? | Da don: `-n auto` → `-n 11` **nhanh hon 31 %** |

---

## 6. 🔴 HAI phat hien ve chinh cong cu cua chuong trinh nay

### 6.1 Canh gac CPU **bao thanh cong trong khi khong lam gi**

Tu sau lan may treo thu hai, moi luot gate deu chay kem mot "canh gac CPU" ngat
o 96 %. Luot gate cuoi cung in:

```
CANH GAC: luot gate da xong. CPU dinh 0%.
```

⛔ **CPU dinh 0 % la khong the** — do tay giua luot thay 31 %. Canh gac khong do
gi ca: no nhan PID tu `$!` cua bash, ma **`$!` la PID cua bash, khong phai PID
cua Windows**. `os.kill(pid, 0)` nem `OSError` ngay vong dau, canh gac ket luan
"da xong" va thoat — trong 2 giay dau cua mot luot 300 giay.

Da chung minh bang phep do:

```
PID that (Popen): 16220 -> os.kill = song
PID gia 116220    -> OSError => canh gac tuong "da xong"
```

⭐ Va day la dang hong te nhat: **no in ra mot dong nghe nhu bao cao tot**. Neu
no im lang, ai do se hoi. Vi no noi "da xong", khong ai hoi.

**Da sua**: canh gac **tu khoi dong** tien trinh no canh (`subprocess.Popen`),
nen PID la that. Bang chung no thuc su do: bon luot sau deu bao CPU dinh khac 0
(4 %, 8 %, 14 %, 17 %, 28 %, 33 %).

⚠️ Va phai noi cho dung: **thu bao ve may khong phai canh gac** — la ngan sach
loi + `BELOW_NORMAL_PRIORITY_CLASS` cua bao cao 08b. Canh gac chi la lop thu ba,
va lop thu ba do da khong ton tai suot ca ngay hom nay.

### 6.2 So dang ky thanh phan **mu** dung cho nguy hiem nhat

`tools/thanh_phan.py --test trien_khai` tra **0 tep test**. Nhung co **10 tep**
test trien khai that, va chung vua chay **250 phep kiem xanh**.

Vi so dang ky suy quan he tu **`import` trong AST** — mot lua chon dung, va bao
cao Phase -1 co bang chung cho no (khop ten tep sai: `agent` khop nham 21 tep,
thuc su import 4). Nhung script cai dat la **`.ps1`**, va test cua chung **doc
`.ps1` nhu van ban**, khong import gi.

⇒ Do thi import khong the thay canh ay. Va no mu dung o cho `CLAUDE.md` ghi la
**da that su lam sap production** (BOM trong tep cau hinh).

⛔ Khong sua trong dot nay: sua dung la cho `[[canh_dong]]` khai canh
`trien_khai → test doc .ps1`, tuc mot muc du lieu chu khong phai mot co che moi.
Ghi thanh no **co ten**, khong de no la mot con so 0 im lang.

---

## 7. ⚠️ "Chuong trinh nay khong deploy" la mot loi hua **yeu hon** no nghe

Phien `ltt-voice` hoi truoc khi deploy, va cau hoi do lam lo ra dieu nay:

> `setup/deploy_nang_quyen.ps1` chay tu `D:\LTTSTUDIOSAPP` — **cay chinh**,
> nhanh `admin-mvp-v3`. De dua LTT Voice len production, ho phai merge vao
> `admin-mvp-v3` roi deploy **ca cay**.

⇒ Toi khong deploy. Nhung toi **commit vao dung cai nhanh ma nguoi khac deploy
tu do**. Nen ma cua toi van len production — chi la qua tay nguoi khac.

⭐ Loi hua "khong deploy" bao ve duoc **hanh dong** cua toi, khong bao ve duoc
**hau qua** cua toi. No chi lo ra vi mot phien khac di hoi. Da tra loi ho: chua
nen, cho xong Phase 10.

---

## 8. Con no — co ten, khong im lang

| Muc | Muc do | Ghi chu |
|---|---|---|
| 🔴 Treo tai `test_agent_executor_hai_scheduler_khong_submit_trung` | **P0 mo** | tai hien duoc (>180s). Nghi deadlock khi hai scheduler tick cung mot agent run. **Chuong trinh nay tim ra, khong sua** — no nam ngoai pham vi don dep va can mot quyet dinh |
| 12 commit chua len `origin` | **rui ro sao luu** | gom ca `89eb46c` **da deploy len production**; `git branch -r --contains 89eb46c` rong |
| 294 chuoi i18n khach thay | viec noi dung | khong dich may |
| `thanh_phan` mu voi test doc `.ps1` | cong cu | §6.2 |
| 10 cho retry/backoff chua kiem ke | khao sat | §5 cau 9 |
| Ngan sach CPU la **per-run**, khong per-may | thiet ke | 08b §7 — hai phien "dung luat" van cong don |
| 140 diem vao CLI trong `tools/` | kiem ke | — |
| 22 so tep test trung san co | ⛔ khong doi ten | goc da dong bang dai so |

---

## 9. PHAN QUYET

```
CONDITIONAL PASS
```

**Vi sao khong phai FINAL PASS.** Moi phep do deu xanh, khong moc nao bi nang,
khong bi mat nao lo, khong buoc nao thieu bang chung. Nhung con **mot P0 mo** —
mot cho treo tai hien duoc trong bo dieu phoi agent, do chinh chuong trinh nay
tim ra o Phase 07 va **co y khong sua**.

⛔ Mot ban "FINAL PASS" kem mot P0 mo la mot cau noi sai. Dieu kien de len
FINAL PASS la mot **quyet dinh** ve cho treo do — sua, hoac khai no la duong
chet co bien gioi.

**Vi sao khong phai NOT READY.** P0 do **khong do chuong trinh nay gay ra** va
khong nam tren duong ma chuong trinh nay dong. No la mot loi da co, chi vua lo
ra vi lan dau co nguoi chay phep kiem ay.

### Push

⛔ **CHUA PUSH.** Theo dung Prompt 10: `CONDITIONAL PASS` chi duoc push khi
**chu du an dong y**. Commit da xac minh duoc giu nguyen tai `ea81c7a`.

---

## 10. Tom tat cuoi

| | |
|---|---|
| **Da go / gop** | bang trang thai chep tay trong `CLAUDE.md` (280 dong) → mot **lenh**; hai canh `server → app` khong khai trong hop dong; mot canh bao sai cua linter; mot cong gac di lac vao cay phien khac |
| **Con lai, va vi sao** | `cutclipshort` (vendor, bien gioi sach) · 6 muc HISTORICAL (chu thich giai thich) · **0 DEAD** — khong muc nao du bang chung, nen **khong xoa gi** |
| **Kiem tra** | gate day du **PASS** · 4 buoc bo qua **da dong rieng** (91 + 7 phep kiem) · 4 mien trong diem **1.039 phep kiem** · trinh duyet that tren `/gia-api` |
| **SHA** | `ea81c7a` |
| **Nhanh xa** | `origin/admin-mvp-v3` — **truoc 12 commit, CHUA push** |
| **Xac minh push** | ⛔ chua thuc hien — phan quyet `CONDITIONAL` |
| **STATE** | `CONDITIONAL` |

---

## 11. ⚠️ DINH CHINH — nhanh da DI TIEP, va viec nay DA LEN PRODUCTION

Bao cao tren viet luc HEAD la `ea81c7a` va ket luan "CHUA PUSH". Ca hai deu
dung **luc do**. Trong luc viet, hai su kien xay ra:

| Luc | Viec |
|---|---|
| 21:0x | phien `ltt-voice` merge viec cua ho vao `admin-mvp-v3` |
| **21:11** | chu du an quyet *"deploy full, khong lo code phien khac"* → **deploy** |
| 21:1x | `1ad85c6` — merge bao cao cuoi cua ho |

```
deploy-20260902-211112     EXITCODE=0   (2 phut 06)
nghiem thu co nang quyen   EXITCODE=0   "he thong hoan chinh"
15 app nap · ban chay khop git 536/0/0/0
```

⇒ **Viec cua chuong trinh nay dang chay tren production.** Loi hua "chuong
trinh nay khong deploy" o §7 vua duoc chung minh la yeu dung nhu da mo ta —
chi khac o cho: no yeu vi **chu du an quyet the**, khong phai vi ai so suat.

### ⭐ Quy tac 5b — **DA DONG**, va do bang phep do cua chinh toi

`https://app.lttstudios.com/gia-api` (qua Cloudflare, khong phai loopback):

```
HTTP 200
300đ · 900đ                  <- bang gia anh, di qua registry.bang_gia_cong_khai()
ltt-voice-2026-08-30a        <- ma phien ban gia tieng
```

⇒ Cai hong toi lo o §2.4 — `bang_gia_cong_khai()` tra rong, trang **van 200 van
dep** nhung mat mot bang gia — **khong xay ra o khach that**.

⚠️ Va nen ghi ro thu tu: §2.4 do tren **mot ban co lap o cong 8123**, muc nay do
tren **URL cong khai that**. Chi muc nay moi dong duoc quy tac 5b. Loopback la
buoc soi nhanh, khong phai buoc chot.

### Mot phat hien cua phien `ltt-voice`, dang cho vao day

Chay `4-nghiem-thu.ps1` **khong nang quyen** bao *"1 loi"* — nhung do la
`PermissionDenied` khi doc `secrets/app.env`, tuc loi cua **cach chay**. Chay
lai co nang quyen: 0 loi, va chot quan trong nhat moi doc duoc:

```
[OK] LTT_WORKER_POOLS khong dat - worker da nang, job voice nhat duoc
```

⭐ Hai kieu sai **nguoc chieu trong cung mot luot chay**: bao mot loi **gia**, va
bo sot chot **that**. Cung ho hang voi §6.1 — mot cong cu kiem tra noi sai ve
chinh no.

### Trang thai cuoi (thay cho §10)

| | |
|---|---|
| HEAD | `1ad85c6` |
| Chua len `origin` | **29 commit** — trong do co ban **dang chay production** |
| Deploy | ✅ 21:11, EXITCODE=0, nghiem thu 0 loi |
| Quy tac 5b | ✅ **dong** tren URL cong khai |
| Phan quyet | **CONDITIONAL PASS** giu nguyen — P0 agent-executor van mo |
| STATE | `CONDITIONAL` |

🔴 **Va con no lon nhat gio doi cho:** 29 commit chua day len `origin`, gom ca
ban **dang phuc vu khach that**. Ma nguon production hien chi ton tai tren **mot
o dia**. Day khong con la rui ro sao luu chung chung — no la rui ro cu the.
