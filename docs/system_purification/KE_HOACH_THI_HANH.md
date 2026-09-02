# KE HOACH THI HANH — LTTSTUDIOSAPP SYSTEM PURIFICATION V1

Nguon goi prompt:
`G:\My Drive\AI\A LTT AII\LTTSTUDIOSAPP_System_Purification_V1\LTTSTUDIOSAPP_System_Purification_V1`

Tai lieu nay **khong thay** goi prompt. Goi prompt la hop dong; tai lieu nay la
**ban do thi hanh tren repo THAT**, do ngay 2026-09-02, kem cac cho goi prompt
da lech so voi thuc te.

---

## 0. Khao sat da lam (bang chung, khong phai tri nho)

| Do | Gia tri | Lenh |
|---|---:|---|
| Nhanh / HEAD | `admin-mvp-v3` / `6b25ada` | `git rev-parse` |
| Remote | `origin` = `giaitritruyenthongltt-spec/LTTSTUDIOSAPP`, `backup` = `D:/LTTBackups` | `git remote -v` |
| Working tree ban | ` M tools/cam_cli.py`, `?? docs/auto_scan_video/` | `git status --short` |
| `.py` theo doi | 1.169 tep | `git ls-files` |
| `apps/` | 16 app, 197 tep, 35.944 dong | |
| `platform_core/` | 122 tep, 29.657 dong | |
| `server/` | 62 tep, 14.001 dong | |
| `tools/` | 148 tep, 29.841 dong | |
| `tests/` | 360 tep, 91.282 dong | |
| `cutclipshort/` | 136 tep, 30.776 dong | |
| `docs/` | 1.297 tep | |
| `ho_so_he_thong.txt` | 303.573 dong | `wc -l` |
| `docs/NHAT_KY.md` | 15.859 dong | |
| `docs/KE_HOACH_TRIEN_KHAI.md` | 3.668 dong | |
| Ratchet nuot loi lang le | `max: 63` | `tools/silent_except_baseline.json` |
| Ratchet i18n | 774 chuoi / 114 tep | `tools/i18n_baseline.json` |
| Ratchet kich thuoc route | 2 tep: `server/admin.py` 1388, `server/admin_api.py` 1897 | `tools/server_routes_baseline.json` |
| Ratchet chuong treo | 1 muc | `tools/chuong_baseline.json` |
| Buoc trong gate | 23 buoc | `tools/gate.py:_steps` |

---

## 1. Sau cho GOI PROMPT DA LECH so voi repo — phai sua truoc khi chay

Goi prompt duoc soan tu mot anh chup cu. `REPO_RESEARCH_NOTES.md` tu noi
*"live checkout thang ghi chu nay"*. Day la nhung cho no thang:

1. **`core/` KHONG CON TON TAI.** `ls -d core` → khong co; `git ls-files core` → 0 tep.
   Nhung `AUDIT_MATRIX` muc 03, `START_HERE` scope, Prompt 02 va Prompt 03 deu
   coi `core/` la trong tam ("audit `core/` module-by-module", "active new platform
   importing `core/`"). ⇒ **Toan bo trong tam Prompt 03 phai duoc tro lai muc tieu.**
2. **`socialbot`, `demo`, `kichban`, `mediatools` da bi go han** (Q108/Q109,
   2026-08-25). Prompt 03 dat chung o dong dau danh sach uu tien. ⇒ Con lai chi
   la **du chan**: co `LTT_SOCIALBOT_ROUTES` trong `secrets/app.env`, tham chieu
   trong docs, test giu import chet.
3. **Ratchet nuot loi lang le da la 63**, khong phai "131 trong code scanned,
   78 o frozen core" nhu ghi chu. Con so cu di kem `core/` — ma `core/` da khong con.
4. **Ratchet i18n la 774 chuoi / 114 tep**, khong phai "khoang 1.800".
5. **Goi prompt khong biet ve 6 he con moi**: `cutclipshort/` (30.776 dong,
   engine vendor), `render_gateway/`, `llm_gateway/`, `voice_sidecar/`,
   `codex_sidecar/`, `nexus_agent/`. Chung nam TRONG repo nhung **deploy sang may
   khac** (may B, sidecar NSSM). Day la nhom "workers/sidecars/gateways co trong
   repo" cua scope — nhung khoi luong lon hon goi prompt hinh dung.
6. **Nhanh lam viec la `admin-mvp-v3`, khong phai `master`.** Prompt 10 noi
   "push normal len intended branch" ma khong chot nhanh nao. Phai chot truoc.

⇒ Cac lech nay **khong lam goi prompt sai**. Chung lam **Phase 00 quan trong hon
du kien**: census phai la thu dinh nghia pham vi, khong phai ghi chu cu.

---

## 2. Ba xung dot giua GOI PROMPT va LUAT DU AN (`CLAUDE.md` / `AGENTS.md`)

Phai giai quyet bang van ban truoc khi chay, neu khong moi phase se cai nhau.

| # | Goi prompt noi | Luat du an noi | Xu ly de nghi |
|---|---|---|---|
| X1 | `OPERATING_CONTRACT` §13: "Phase 00-09 co the commit checkpoint" | Thoi quen du an: commit sau khi gate xanh | Cho phep commit checkpoint **chi khi** `gate.py --vong-lap` xanh; **khong** push cho toi Phase 10 |
| X2 | Prompt 00 §4: "Run baseline `python tools/gate.py`" | `CLAUDE.md` §4: gate la cong cu **PHAN QUYET**, khong phai chan doan; day du ~5 phut | Dung — Phase 00 chay gate **day du dung MOT lan** de dong bang. Cac phase sau dung `--vong-lap` (~15s) trong vong lap, gate day du **mot lan** cuoi moi phase |
| X3 | `PURIFICATION_GATES` khong nhac browser | `CLAUDE.md` §5/§5b: **bat buoc** kiem tren URL cong khai that sau moi doi giao dien | Bo sung: G9 phai kiem tren `https://app.lttstudios.com`, **khong** chi loopback. Doi static thi phai cache-bust (§6) |

Ngoai ra hai ranh gioi cua du an **thang** goi prompt trong moi truong hop:
- **Khong deploy** trong chuong trinh nay. Purification cham `app\` tren may chu
  la vi pham (`CLAUDE.md`: "Dung bao gio sua file truc tiep trong `app\`").
- **Khong cham but toan tien** va **khong tu chay lenh can UAC**.

---

## 3. Bon quyet dinh can chu san pham chot TRUOC Phase 00

| ID | Cau hoi | Vi sao chan | Mac dinh neu khong tra loi |
|---|---|---|---|
| **QD-1** | Chay tren `admin-mvp-v3` hay nhanh moi `purification-v1`? Prompt 10 push vao dau? | Prompt 10 la buoc push that len GitHub | Tao nhanh `purification-v1` tu `admin-mvp-v3`; Phase 10 push nhanh do, **khong** dung vao `master` |
| **QD-2** | ` M tools/cam_cli.py` va `?? docs/auto_scan_video/` la cua ai? | `OPERATING_CONTRACT` §4 cam dung cham user work khong ro chu | Ghi ca hai vao `STATE.md -> DO_NOT_TOUCH`, khong commit, khong xoa |
| **QD-3** | `cutclipshort/`, 4 gateway/sidecar, `nexus_agent/` co IN scope khong? | 30.776 + ~13.000 dong; chung deploy o may khac nen "dead" o may A khong co nghia la dead | IN scope cho **phan tich va phan loai** (Phase 02/03), **OUT** cho xoa — tru khi chung minh duoc khong con nguoi tieu thu o CA HAI may |
| **QD-4** | `ho_so_he_thong.txt` 303.573 dong co tiep tuc nam trong git? | No la tep lon nhat repo, sinh tu dong, va la mot buoc gate | Giu nguyen o Phase 00-09; **de xuat** o Phase 09, chu san pham quyet |

---

## 4. Chuan bi truoc khi chay (Phase P-1, ~1 phien ngan)

1. Chot QD-1..QD-4.
2. Tao nhanh lam viec theo QD-1.
3. Tao khung: `docs/system_purification/STATE.md` (tu `STATE_TEMPLATE.md`) +
   `docs/system_purification/reports/`.
4. **Giao uoc file** (bat buoc, vi da tung co hai phien cung cay): chuong trinh
   nay **so huu** `docs/system_purification/**`. Moi tep chung (`CLAUDE.md`,
   `AGENTS.md`, `tools/gate.py`, cac baseline) **chi sua bang Edit, khong bao gio
   Write de**.
5. Kiem xem co phien Claude nao khac dang chay tren cay nay khong (`ListAgents`,
   nhip ghi tep) truoc khi bat dau Phase 00.

---

## 5. Ke hoach tung phase

Ky hieu:
**DAU VAO** → can co truoc · **VIEC** → lam gi tren repo NAY · **CHUNG CU** → lenh
phai chay · **CONG RA** → dieu kien roi phase · **SAN PHAM** → tep de lai.

---

### Phase 00 — Frozen Baseline & Repository Census
**Che do: CHI DOC/DO. Khong sua mot dong code nao de gate xanh.**

**DAU VAO:** QD-1..QD-4 da chot.

**VIEC**
1. Chup `git status --short`, HEAD, nhanh, 20 commit gan nhat. Moi thay doi
   khong thuoc chuong trinh → `DO_NOT_TOUCH`.
2. Census day du. Muc phai co ma so 0 cua tai lieu nay chua co:
   - 16 app: ten, trang thai (song / sau co / da go), co manifest khong;
   - dem entrypoint: `server/`, `job_worker.py`, `codex_sidecar_main.py`,
     `voice_sidecar_main.py`, 4 dich vu NSSM, `tools/*.py` co `main()`;
   - 66 tep migration Alembic: bao nhieu head, co nhanh khong;
   - 1.297 tep docs: phan theo thu muc, danh dau thu muc nao la **luu tru**;
   - 20 tep PNG + `nuitka-crash-report.xml` dang **theo doi o thu muc goc** —
     ghi nhan, chua xoa.
3. **Chay `python tools\gate.py` DAY DU dung mot lan.** Ghi lai: verdict tung
   buoc trong 23 buoc, thoi gian, so test pass/skip/fail, moi warning.
   ⛔ Neu do — **khong sua**. Ghi "BASELINE PARTIAL" + ly do.
4. Chay rieng va ghi so tung ratchet: `check_silent_except`, `check_i18n`,
   `lint_app_contract`, secret scan, `system profile` freshness.
5. Ve so do chuoi chi dan: ai doc gi truoc — `CLAUDE.md` → `AGENTS.md` →
   `QUYET_DINH_NEN_TANG` → `KE_HOACH_TRIEN_KHAI` → `NHAT_KY` → `ho_so_he_thong`.
   Do **do lon** tung tep (da co o muc 0) va danh dau tep nao **tu mau thuan**.
6. Do co che kham pha app (`platform_core/registry.py`, 1.039 dong) — no tim app
   bang gi: quet thu muc, danh sach cung, hay import dong?

**CHUNG CU**
```
python tools\gate.py
python tools\check_silent_except.py
python tools\check_i18n.py
python tools\lint_app_contract.py
```

**CONG RA:** `BASELINE FROZEN` (gate chay het, moi so ghi lai) hoac
`BASELINE PARTIAL` + ly do cu the. **Khong** duoc `BLOCKED` vi luoi.

**SAN PHAM:** `reports/00_baseline_census.md`, `STATE.md` (dien het bang
"Frozen baseline").

**Uoc luong:** 1 phien. **Rui ro:** thap. **Bay:** cam do gate xanh — cam.

---

### Phase 01 — Truth / Rules / Docs Purification
**Day la phase NANG NHAT va co gia tri cao nhat cua ca chuong trinh.**

Vi sao: `CLAUDE.md` **tu ghi lai ba lan** cung mot hang trang thai noi sai, ba
lan **ve phia nguy hiem** (Public API "chua mo" trong khi dang thu tien that;
`/vps` "dang TAT" trong khi dang cong khai). Do khong phai loi cua nguoi viet —
do la **loi kien truc tai lieu**: trang thai runtime dang duoc chep tay vao mot
tep khong ai kiem chung.

**DAU VAO:** `reports/00_baseline_census.md`.

**VIEC**
1. **Phan loai moi luat** trong `CLAUDE.md` (496 dong), `AGENTS.md` (697 dong),
   `README.md`, `docs/QUYET_DINH_NEN_TANG.md` (382 dong),
   `docs/KE_HOACH_TRIEN_KHAI.md` (3.668 dong), `docs/ANH_NOI_BO/DECISIONS.md`,
   va **chu thich trong code dang dong vai luat**.
   Nhan: `CURRENT` / `SUPERSEDED` / `CONFLICTING` / `ORPHAN_RULE`.
2. **Tach TRANG THAI ra khoi LUAT.** De xuat cot loi cua phase nay:
   - `CLAUDE.md` chi giu **luat** (thu bat bien, khong het han);
   - moi **trang thai** (tool nao mo, app nao song, gia bao nhieu) chuyen sang
     mot bang **sinh tu may chu**, hoac bi xoa va thay bang **lenh de hoi**.
   - Da co tien le dung: `tools/api_prod_canary.py`. Mo rong no thanh nguon
     trang thai duy nhat.
3. Truy moi **gia tri lap lai**: cong (8100 / 8120 / 8199 / 8280 / 8299 / 9444),
   duong (`C:\LTTPlatform`, `D:\LTTPlatform-runtime`), gioi han Cloudflare
   (100 MB / 100 s), tran token (131.072 / 32.768 / 96.256 / 11.412), gia credit.
   Moi gia tri → **mot chu so huu**, cho con lai tro toi.
4. **Co lap lich su**: `docs/_luutru/` (33 tep), cac thu muc `APP_AUDIT/**`
   (hang tram tep), `NHAT_KY.md` (15.859 dong). Chung phai co **nhan ro** va
   **khong nam trong duong doc mac dinh cua agent**.
5. Grep gia tri cu sau khi hop nhat; sua tham chieu chet.
6. Cap nhat test **chi khi** quyet dinh da xac nhan la SUPERSEDED.

**CHUNG CU**
```
python tools\gate.py --vong-lap
python tools\api_prod_canary.py
```
+ grep gia tri cu tren toan repo (`8100`, `LTT_SOCIALBOT_ROUTES`, `apps/demo`,
`socialbot`, `mediatools`, `kichban`).

**CONG RA:** `CONFLICTING = 0` trong tap luat **dang hieu luc**. Moi bat bien co
dung mot chu so huu. Lien ket tai lieu khong gay.

**SAN PHAM:** `reports/01_truth_rules_docs.md` + bang `Rule → owner → class`.

**Uoc luong:** 2-3 phien. **Rui ro:** trung binh (de sa da vao viet lai tai lieu).
**Bay:** **dung sinh them luat de sua luat cu** (`OPERATING_CONTRACT` §8).

---

### Phase 02 — Dependency & Ownership Graph
**Che do: chu yeu phan tich. Khong xoa dien rong.**

**DAU VAO:** Phase 01 xong.

**VIEC**
1. Dung do thi import tinh cho: `apps/*` → `platform_core` → `server`, va nguoc
   lai. Tim **vi pham chieu**: `app → server`, `platform_core → apps`.
2. Do thi **dong** (grep khong thay): kham pha app trong `registry.py`, dispatch
   tool cua Public API, discovery job handler, plugin/manifest.
3. Voi tung moi quan tam, ghi `owner → contract → callers → persistence → tests`:
   job, credit, storage, provider/`api_pool`, auth/access, `upload_sessions`,
   `leases`, admission/GPU, metrics/alerts, agent, frontend bundle.
4. Tim **hai chu so huu trong giong nhau**. Nghi van tu khao sat:
   - gia: `apps/anhnoibo/gia.py` vs bang gia trong `platform_core` vs `/gia-api`;
   - ngan sach token: `apps/ltt_llm/ngan_sach.py` vs `llm_gateway` vs `gateway.env`;
   - hai gateway (`render_gateway`, `llm_gateway`) co logic backoff/busy trung nhau?
5. Tim vong tron phu thuoc, helper duoc chep lai, app goi thang provider/storage/DB.

**CHUNG CU:** cong cu do thi tu viet dat trong `tools/` (tam, khong vao gate),
+ `grep` callers, + doc `registry.py`.

**CONG RA:** ban do so huu day du trong `STATE.md`. Moi module co nhan.
**Khong** module nao bi goi `DEAD` neu chua kiem discovery dong.

**SAN PHAM:** `reports/02_dependency_ownership.md`.

**Uoc luong:** 2 phien. **Rui ro:** thap (khong sua code).

---

### Phase 03 — Legacy / Frozen / Dead Code Purification
**⚠️ Phase nay phai duoc TRO LAI MUC TIEU** — danh sach uu tien cua goi prompt
(`core`, `socialbot`, `demo`) da khong con ton tai.

**Muc tieu MOI, theo repo that:**

| Ung vien | Kich thuoc | Cau hoi phai tra loi |
|---|---:|---|
| `cutclipshort/` | 30.776 dong | Engine vendor cho `taoclipngan`. Con dong bo voi upstream khong? Bao nhieu % duoc goi that? |
| `codex_sidecar/` + `codex_sidecar_main.py` | 587 dong | Dich vu `LTTStudioCodex` con chay? `chataistudio` con dung? |
| `nexus_agent/` | 1.284 dong | Nexus co doi da commit **chua deploy** (`docs/nexus/N8_CHO_DEPLOY.md`) — day la COMPAT hay ACTIVE? |
| `render_gateway/` `llm_gateway/` `voice_sidecar/` | ~11.000 dong | Deploy o **may khac**. "Khong caller o may A" **khong** = dead |
| Du chan da go | — | `LTT_SOCIALBOT_ROUTES` trong `secrets/app.env`, tham chieu `apps/demo` trong docs/test |
| 20 PNG + `nuitka-crash-report.xml` o goc | — | Bang chung audit da commit vao goc repo |
| `apps/nexus` (web-broker) | — | Q101 noi **da dong bang**. Con route song khong? |
| `apps/qualitylab`, `apps/prompt_ai_ommi` | — | Trang thai chua ro trong bang tien do — phai xac dinh |

**VIEC:** voi **tung** ung vien, chung minh du 8 dieu cua `OPERATING_CONTRACT` §5
(caller · discovery dong · env/config · du lieu/migration · deploy/rollback ·
test · tuong thich ngoai · phu thuoc dong bang). Thieu mot dieu → **giu**.

Phan loai roi hanh dong: ACTIVE/SHARED giu · COMPAT co lap + ghi dieu kien go ·
FROZEN cach ly + chan import moi · HISTORICAL tach khoi runtime · DUPLICATE di tru
callers roi xoa · DEAD xoa co bang chung · UNKNOWN **giu**.

**CHUNG CU:** sau **moi lo xoa**: `python tools\gate.py --vong-lap`; cuoi phase:
`python tools\gate.py` day du.

**CONG RA:** moi ung vien co nhan + bang chung. Gate day du xanh.

**SAN PHAM:** `reports/03_legacy_frozen_dead.md`.

**Uoc luong:** 2-3 phien. **Rui ro:** CAO — day la phase de pha nhat.
**Bay:** `cutclipshort` va cac gateway **khong** duoc do bang "co ai import o may A khong".

---

### Phase 04 — App Layer Purification
16 app: `agent`, `anhnoibo`, `autosubvideo`, `chataistudio`, `ltt_llm`,
`ltt_voice`, `nexus`, `prompt_ai_ommi`, `qualitylab`, `taoanh`, `taoclipngan`,
`taovideo`, `thumbnail`, `upscalevideo`, `vps`.

**VIEC**
1. **Bang diem tung app**: manifest · routes · services/features · jobs · cost ·
   tables · storage · provider · templates/frontend · auth/CSRF/isolation · tests.
2. Tim **nghiep vu nam trong route**. Ba tep vuot/gan tran 900 dong:
   `apps/vps/routes.py` 900 · `apps/autosubvideo/routes.py` 899 ·
   `apps/upscalevideo/routes.py` 882. Ba con so nay **sat tran mot cach dang ngo**
   — phai kiem xem chung bi cat cho vua tran hay that su la 900.
3. Tim logic trung: kiem anh tai len, dung URL nghe/xem, tinh gia, nop job.
   Hai vi du that da duoc ghi lai:
   - loi **thu tien khi tra thieu anh** xay ra **hai lan** (H38 roi H37) — cung goc:
     handler khong bao `credit_cost`. ⇒ day la **bat bien thieu chu so huu**, khong
     phai hai bug.
   - `du_an.duong_tieng()` moi gom **nam cho tu dung URL** trong `ltt_voice`.
   ⇒ Phase 04 phai tim **con bao nhieu cho nhu vay**.
4. Kiem tra tung app co bypass `platform_core` khong.

**CHUNG CU:** test theo app + `lint_app_contract` + test frontend cua app do.

**CONG RA:** bang diem 16 app. Moi divergence hoac duoc sua hoac duoc ghi ly do.
**Khong** tach tep chi vi dai.

**SAN PHAM:** `reports/04_apps.md` + scorecard.

**Uoc luong:** 3-4 phien (nang nhat sau Phase 01). **Rui ro:** trung binh.

---

### Phase 05 — Platform Core Purification
122 tep / 29.657 dong. Kiem tra tung module: `models.py` (923) · `registry.py`
(1.039) · `job_runner.py` (1.640) · credit · billing · `api_pool` · `public_api/`
(`examples.py` 930) · storage · users/access · anti-fraud · agent · provider ·
`leases.py` · admission · metrics/alerts · `upload_sessions.py` · `templating.py`.

**VIEC:** voi tung module — ton tai de lam gi · ai goi · hop dong · luu tru ·
co chu so huu trung khong · co logic rieng cua mot app lot vao khong · export
khong ai dung · duong tuong thich · no nuot loi.

**Uu tien dieu tra:** `job_runner.py` 1.640 dong la tep logic lon nhat cua nen
tang va la noi H36 da tim ra ba loi P0 cung mot goc (vong nen viet nhu the chi
co mot tien trinh). Kiem: **moi** viec nen co nam sau lease khong?

**CHUNG CU:** ⚠️ voi job/credit/billing/storage/provider — **viet test hanh vi
TRUOC khi doi cau truc**. `test_214` (da tien trinh) chay tay sau moi thay doi
worker/outbox.

**CONG RA:** khong module nao vua la chu so huu vua la ban sao. Gate xanh.

**SAN PHAM:** `reports/05_platform_core.md`.

**Uoc luong:** 3 phien. **Rui ro:** CAO (dung vao tien va job).

---

### Phase 06 — Server / API / Auth / Admin Purification
62 tep / 14.001 dong. Hai tep lon nhat da nam trong ratchet:
`server/admin_api.py` 1.897 · `server/admin.py` 1.622 (⚠️ **baseline ghi 1.388**
— lech 234 dong; phai xac dinh checker dem gi truoc khi ket luan la drift).
Them `server/api/streaming.py` 1.015.

**VIEC**
1. `server` phai so huu **van chuyen + lap ghep**, khong so huu luat nghiep vu.
2. Tim: nghiep vu trong route/admin · chinh sach auth/access trung ·
   duong admin/auth cu (admin-tu-bien-moi-truong da vo hieu — con code khong?) ·
   route tuong thich chet · middleware chet.
3. **Auth la vung nguy hiem**: dang ky · dang nhap · phien · xac thuc email ·
   dat lai mat khau · quyen admin · cach ly nguoi dung. **Khong doi ngu nghia**
   neu khong co quyet dinh ro.
4. Tep lon **khong** tu no la ly do tach.

**CHUNG CU:** test auth/security/route/admin + **canary trinh duyet tren URL
cong khai** neu co doi giao dien (`CLAUDE.md` §5b) + cache-bust neu doi static (§6).

**CONG RA:** G1 (auth/isolation) + G7 (security) xanh. Gate xanh.

**SAN PHAM:** `reports/06_server_auth_admin.md`.

**Uoc luong:** 2-3 phien. **Rui ro:** CAO.

---

### Phase 07 — Execution / Money / Storage / Provider Purification
**VIEC:** dung **may trang thai that** (khong phai theo tai lieu) cho 6 mach:
1. `job → hold → worker → terminal → settle/refund`
2. `payment → webhook/reconcile → credit`
3. `upload → ownership → job → artifact`
4. `provider select → call → busy/error → telemetry/cooldown`
5. GPU/admission
6. Public API: job / sync / stream (3 cua cua `ltt_llm`)

**Diem nghi van da biet tu tai lieu du an — phai kiem chung:**
- **"Ban ≠ hong"**: khi may B ban, **khong** duoc goi `api_pool.danh_dau_loi()`.
  Kiem xem luat nay duoc cuong che o **mot** cho hay duoc lap lai o nhieu cho.
- **Thu tien khi tra thieu**: `credit_cost` — bat bien nay co chu so huu chua?
- Backoff/cooldown: `api_pool` · `render_gateway` · `llm_gateway` — ba he thong
  hay mot?
- 429/503: ba cua Public API co tra cung ngu nghia khong?

**CHUNG CU:** ⚠️ **test truoc khi refactor** cho: double-spend · webhook idempotency ·
hold mo coi · hoan tien khi huy/loi · cach ly nguoi dung · quyen so huu tep ·
provider ban/loi. Tiem loi o cho an toan.

**CONG RA:** G2 (money) + G3 (jobs) + G4 (storage) + G5 (provider) xanh.

**SAN PHAM:** `reports/07_execution_money_provider.md`.

**Uoc luong:** 3 phien. **Rui ro:** CAO NHAT ca chuong trinh — day la tien that.

---

### Phase 08 — Errors / Config / Deployment / Runtime Debt
**VIEC**
1. **Nuot loi lang le**: liet ke tung cho trong 63, phan loai (fallback co y ·
   suy giam nhin thay duoc · nen log · nen nem · loi thoi · dong bang).
   ⛔ **Khong** log may moc moi exception. Sua goc, roi **ha** baseline.
   ⛔ **Khong bao gio nang** baseline de gate xanh.
2. **So dang ky env/config**: `key → owner → reader → default → secret? → docs →
   deploy source`. Bat dau tu `secrets/app.env` (production co
   `LTT_PUBLIC_API=1`, `LTT_PUBLIC_API_TOOLS=...`, `LTT_VPS=1`,
   `LTT_SOCIALBOT_ROUTES` da chet, `LTT_WORKER_POOLS`).
   ⚠️ **Khong dua gia tri secret vao report.**
3. Tim: bien chet · alias · default trung · cong/ten cu · duong tuong doi ·
   workaround ma hoa da loi thoi.
   ⚠️ **Khong go workaround Windows** truoc khi kiem chung hanh vi goc —
   luat "ghi cau hinh KHONG BOM" **da that su lam sap production**.
4. Kiem: cai moi · cap nhat · migration · restart dich vu · release · rollback ·
   bao toan `data\` va `secrets\`.
   ⚠️ Bay da biet: `LTTStudioVoice` giu handle tren `app\` — `update.ps1` phai
   dung no **dau tien**. Va thieu lan `voice` trong `LTT_WORKER_POOLS` thi job
   nam `queued` **mai mai, khong bao loi**.
   ⚠️ `render_gateway/deploy/deploy.ps1` da tung co hai loi khien no **chua bao
   gio deploy thanh cong lan nao** — kiem cac script deploy con lai cung kieu loi.
5. `.ps1` phai thuan ASCII (86 tep `.ps1`).

**CHUNG CU:** `python tools\gate.py` + secret scan + doc `4-nghiem-thu.ps1`.
⛔ **Khong chay deploy that.**

**CONG RA:** ratchet nuot loi < 63 **vi no that su giam**. So dang ky env day du.
G6 (deployment) co bang chung (doc script, khong chay).

**SAN PHAM:** `reports/08_errors_config_deploy.md`.

**Uoc luong:** 2-3 phien. **Rui ro:** trung binh.

---

### Phase 09 — Frontend / i18n / Tests / Tooling Purification
**VIEC**
1. **Frontend**: 3 thu muc (`agent-canvas`, `autosub-studio`, `prompt-ai-ommi`),
   47 tep ts/js. Kiem: co duoc mount khong · so huu bundle · cache-bust
   (`ASSET_VER`) · JS/CSS/template chet · client API trung · danh sach frontend
   **ma cung** trong `gate.py` co day du khong.
   ⛔ **Khong** viet lai framework.
2. **i18n**: 774 chuoi / 114 tep. Phan loai theo **do lo ra voi nguoi dung that**.
   Sua nguon co he thong truoc. Ha baseline **chi khi** no that su giam.
   ⚠️ Ha moc bang **DICH**, khong bang **TRICH LAI**.
3. **Tests**: 360 tep / 91.282 dong. Phan loai CONTRACT / SAFETY / REGRESSION /
   IMPLEMENTATION_LOCK / LEGACY / DUPLICATE_TEST / DEAD_TEST.
   Tim: bat bien lap lai · test giu import chet song · khoa cach lam · fixture
   chep · test cham khong che them gi · bang chung trinh duyet cu.
   ⛔ **Khong "xoa test de xoa code"**.
4. **Tooling/gate**: 23 buoc. Kiem tung buoc con dung viec khong; ratchet nao da
   thua; loai tru cua scanner nao da khong con ly do.
   ⚠️ Kiem tinh chay **song song** voi bo test nen chinh gate co the tu nhieu vao
   phep do (Errno 22, rac fixture). Kiem lai.
   ⚠️ So noi dung cam **khong soi f-string trong .py** — kiem lo hong nay.
   ⚠️ Doc `docs/BAY_TRONG_CONG_CHAT_LUONG.md` truoc khi tin mot dong `RESULT: PASS`.
   **Phai chung minh: che phu gate MOI >= che phu tot han cu.**
5. Quyet dinh QD-4 (`ho_so_he_thong.txt` 303.573 dong).
6. Don goc repo: 20 PNG + `nuitka-crash-report.xml`.

**CHUNG CU:** moi checker + 3 frontend + pytest lien quan + `python tools\gate.py`.

**CONG RA:** **dong bang release candidate**. Khong duoc chay Phase 10 truoc buoc nay.

**SAN PHAM:** `reports/09_frontend_tests_tooling.md`.

**Uoc luong:** 2-3 phien. **Rui ro:** trung binh.

---

### Phase 10 — Integrated Deletion, Final Acceptance, Commit & Push
**Che do: nguoi ra soat DOC LAP. Khong y tuong kien truc moi tru khi go blocker.**

**VIEC**
1. So HEAD hien tai voi baseline Phase 00 va RC Phase 09. Phat hien thay doi
   khong thuoc chuong trinh.
2. **Dong moi phan loai**: DEAD xoa (du bang chung) · DUPLICATE di tru hoac
   `DEFER` ro rang · COMPAT co nguoi tieu thu + dieu kien go · FROZEN co bien ·
   HISTORICAL ngoai duong runtime · UNKNOWN ghi thanh **no cong khai**, khong bao
   gio xoa lang le.
3. **Quet mau thuan lan cuoi**: cong · duong · ten · quyet dinh · hang so · env ·
   provider · luat tinh tien. Dich: `CONFLICTING = 0`.
4. `python tools\gate.py` **day du** + cac bo test co the doc cho: auth/isolation ·
   credit/billing/payment · jobs/idempotency/cancel · storage/artifacts ·
   provider/Public API · setup/update/release/rollback · kham pha app.
   + canary trinh duyet tren **URL cong khai** neu co doi giao dien.
   + secret scan lai.
5. Bao cao **TRUOC/SAU** cho moi so o muc 0 cua tai lieu nay.
6. **Red-team** 13 cau hoi cua Prompt 10.
7. Phan quyet **dung mot trong ba chu**: `FINAL PASS` / `CONDITIONAL PASS` /
   `NOT READY`. ⛔ `NOT READY` → **khong push**.

**Commit & Push**
- Chi khi `FINAL PASS`, hoac `CONDITIONAL PASS` co chu san pham duyet **va**
  khong cong critical nao do.
- Doc **toan bo** diff truoc khi commit. Kiem khong co secret / du lieu runtime /
  rac sinh ra.
- Push **binh thuong**. ⛔ Khong `--force`, khong `--force-with-lease`,
  khong amend lich su khong lien quan.
- Sau push: lay SHA local, xac minh remote branch HEAD **chua** SHA do, ghi lai
  repo/branch/SHA.
- Neu bi chan (auth/network/branch protection): ghi `PUSH BLOCKED`,
  **khong gia vo da push**, giu commit local.

**SAN PHAM:** `reports/10_final_acceptance.md` · scorecard cuoi · no con lai ·
tom tat kien truc/so huu · `STATE.md` → `CLOSED` / `CONDITIONAL` / `BLOCKED`.

**Uoc luong:** 1-2 phien. **Rui ro:** trung binh (buoc push la buoc that).

---

## 6. Tong hop lich chay

| Phase | Ten | Phien | Rui ro | Sua code? |
|---|---|---:|---|---|
| P-1 | Chuan bi + chot QD-1..4 | 0,5 | thap | khong |
| 00 | Baseline & census | 1 | thap | **KHONG** |
| 01 | Truth / rules / docs | 2-3 | TB | it |
| 02 | Dependency & ownership | 2 | thap | **KHONG** |
| 03 | Legacy / frozen / dead | 2-3 | **cao** | co |
| 04 | App layer | 3-4 | TB | co |
| 05 | Platform core | 3 | **cao** | co |
| 06 | Server / auth / admin | 2-3 | **cao** | co |
| 07 | Execution / money / provider | 3 | **cao nhat** | co |
| 08 | Errors / config / deploy | 2-3 | TB | co |
| 09 | Frontend / i18n / tests / tooling | 2-3 | TB | co |
| 10 | Final acceptance + push | 1-2 | TB | it |
| | **Tong** | **~24-31 phien** | | |

⛔ **Khong chay song song.** Moi phase phai cap nhat `STATE.md` truoc khi sang phase sau.

---

## 7. Bang so phai do TRUOC/SAU (dien o Phase 00, doi chieu o Phase 10)

| So do | Baseline (Phase 00) | Sau (Phase 10) |
|---|---:|---:|
| `gate.py` verdict + thoi gian | | |
| pytest passed / skipped / failed | | |
| Test frontend (3 bo) | | |
| Nuot loi lang le | 63 | |
| No i18n | 774 / 114 tep | |
| Canh bao app-contract | | |
| Phat hien secret | | |
| Mau thuan luat dang hieu luc | | |
| Tep DEAD da xoa | | |
| Duong COMPAT khong giai thich duoc | | |
| Duong env/config chet | | |
| Tep/fixture test trung | | |
| Tep .py theo doi | 1.169 | |
| Tep docs | 1.297 | |

⛔ **Khong dung "so dong da xoa" lam thuoc do thanh cong** (`PURIFICATION_GATES`).

---

## 8. Nam bay lon nhat cua chuong trinh nay

1. **Xoa vi "trong cu"** — `OPERATING_CONTRACT` §3. Trang thai `UNKNOWN` la mot
   ket qua hop le; xoa lang le thi khong.
2. **Sinh luat moi de chua luat cu** — §8. Neu dinh them mot linter/whitelist,
   phai chung minh truoc rang luat cu **khong the** bi xoa hoac lam thanh chinh chu.
3. **Coi gate la cong cu chan doan** — `CLAUDE.md` §4. Gate day du chi chay o
   Phase 00, cuoi moi phase, va Phase 10. Vong lap dung `--vong-lap` (~15s).
4. **Sua tai lieu ma khong sua NGUON trang thai** — Phase 01 se that bai neu no
   chi viet lai `CLAUDE.md`. Ba lan truoc da chung minh: chep trang thai bang tay
   **luon** troi, va **luon troi ve phia nguy hiem**.
5. **Ket luan tu su vang mat** — `cutclipshort` va 4 gateway/sidecar deploy o may
   khac; "khong ai import o may A" khong phai bang chung.

---

## 9. Ranh gioi cung — khong vuot trong ca chuong trinh

- ⛔ Khong deploy. Khong cham `C:\LTTPlatform\app\`.
- ⛔ Khong cham `D:\BOT GEMINI` (kho tham chieu chi doc, dang phuc vu nguoi dung that).
- ⛔ Khong sua but toan credit / du lieu tien.
- ⛔ Khong doi secret production.
- ⛔ Khong force push, khong rewrite lich su git.
- ⛔ Khong xoa file untracked khong ro chu (xem QD-2).
- ⛔ Khong chay lenh can UAC — chuan bi san roi de nguoi dung bam.
