> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# BAO CAO 00 — FROZEN BASELINE & REPOSITORY CENSUS

Chuong trinh: **LTTSTUDIOSAPP System Purification V1**
Ngay do: **2026-09-02**, khoang 13:30–14:05 (+07)
Che do: **CHI DOC / DO** — khong sua mot dong code nao.

Exit: **BASELINE PARTIAL** — ly do o §7.

---

## 1. Danh tinh chuong trinh

| Muc | Gia tri |
|---|---|
| Repo | `giaitritruyenthongltt-spec/LTTSTUDIOSAPP` (`origin`) |
| Remote phu | `backup` → `D:/LTTBackups/LTTSTUDIOSAPP.git` |
| Nhanh | `admin-mvp-v3` (**khong** phai `master`) |
| HEAD luc do | `6b25adaae2fd3e0b8dbfeb44510ea5d289b6f38c` |
| Vi tri so voi remote | truoc `origin/admin-mvp-v3` **2 commit** (chua day) |
| Cay lam viec | **BAN — va co phien khac dang ghi** (§2) |

---

## 2. 🔴 PHAT HIEN CHAN: mot phien Claude khac dang SONG tren cung cay

Day la dieu quan trong nhat cua Phase 00, va no khong nam trong goi prompt.

`ListAgents` → `lttstudiosapp-e6 [c841c5]`, interactive, bat dau truoc 57 phut.
Nhip ghi do duoc:

| Tep | mtime |
|---|---|
| `tools/cam_cli.py` | 13:31:33 |
| `tests/test_275_cai_dat_cli.py` | 13:36:31 |
| `sdk/ltt_cai_dat_cli.py` | 13:37:09 |
| `ho_so_he_thong.txt` | 13:42:45 |

Do la **nhip ghi cua mot phien dang lam viec**, khong phai tan du bo do.
Da lap giao uoc theo `AGENTS.md` §10.2. Phien kia tra loi:

- dang sua bo cong cu tu ghi cau hinh Codex (goc cua loi 429 hom nay);
- giu **dung 4 tep** tren + `ho_so_he_thong.txt`, con ~15 phut;
- **se commit trong phien nay, tren `admin-mvp-v3`**.

### 2.1 Mot hanh dong cua toi da hoan tac, khai bao day du

Luc 13:45 toi chay `git switch -c purification-v1` **truoc khi** biet phien kia
dang song ⇒ cay lam viec cua ho bi chuyen nhanh khoang 1 phut. Da
`git switch admin-mvp-v3` + `git branch -d purification-v1` ngay luc 13:46.
HEAD van `6b25ada`, khong tep nao doi, 4 tep sua do con nguyen. Phien kia xac
nhan khong chay lenh git nao trong phut do.

⇒ **Bai hoc dua vao quy trinh:** `ListAgents` phai chay **truoc** lenh git dau
tien, khong phai sau. Da bo sung vao `KE_HOACH_THI_HANH.md` §4 muc 5.

### 2.2 ⛔ LUAT CUNG rut ra tu canh bao cua phien kia — ap cho ca 11 phase

Phien kia canh bao ve `sdk/ltt_cai_dat_cli.py`: khong module nao import, khong
trang nao link, khong route nao goi ham trong no. **Moi phep do tinh se cham no
la CHET. No khong chet** — no la duong **DUY NHAT** cho khach macOS/Linux.

Toi da xac minh va **mo rong**: `server/routes/tai_lieu_api.py:124` khai
`GOI_TAI`, mot dict tra bang **CHUOI**, phuc vu **5 tep** o `/tai/<ten>`:

```
sdk/python/ltt_public_api.py
sdk/typescript/ltt-public-api.ts
sdk/ltt_cai_dat_cli.py
sdk/postman/ltt-public-api.postman_collection.json
sdk/postman/ltt-public-api.postman_environment.json
```

Va tim them **ba** ban do tra-bang-chuoi khac cung phuc vu noi dung ra ngoai:

| Nơi | Phuc vu |
|---|---|
| `server/templating.py:204` `BUILT_PAGES` | trang da dung san |
| `server/templating.py:119` `PUBLIC_LINKS` | lien ket cong khai |
| `server/nexus_download.py:30` `_CONTENT_TYPE` | tep tai Nexus |

Va **co che thu nam**: `platform_core/registry.py:894` nap app bang
`apps_dir.iterdir()` + `importlib.import_module(f"apps.{ten}.manifest")` —
nen **ten app khong bao gio xuat hien trong mot cau `import`**.

> ⛔ **LUAT:** truoc khi xoa BAT CU tep nao trong ca chuong trinh, doi chieu voi
> ca **nam** co che tren. Mot tep co mat trong do la `ACTIVE`, bat ke phep do
> tinh noi gi. Da ghi vao bo nho dai han.

---

## 3. Census kho

### 3.1 Ma nguon theo khu (tep `.py` **duoc theo doi**, `git ls-files`)

| Khu | Tep | Dong |
|---|---:|---:|
| `tests/` | 360 | 91.282 |
| `apps/` (15 app) | 197 | 35.944 |
| `cutclipshort/` | 136 | 30.776 |
| `tools/` | 148 | 29.841 |
| `platform_core/` | 122 | 29.657 |
| `server/` | 62 | 14.001 |
| `voice_sidecar/` | 19 | 5.090 |
| `alembic/` | 66 | 3.852 |
| `render_gateway/` | 19 | 3.473 |
| `llm_gateway/` | 15 | 2.570 |
| `nexus_agent/` | 8 | 1.284 |
| `sdk/` | 2 | 660 |
| `codex_sidecar/` | 3 | 587 |
| **Tong `.py` theo doi** | **1.169** | |
| `frontend/` | 47 tep ts/js | (3 thu muc) |
| `.ps1` | 86 | |

⚠️ **`core/` KHONG TON TAI** — 0 tep. Xem §6.

### 3.2 15 app — tat ca deu co `manifest.py`

`agent` · `anhnoibo` · `autosubvideo` · `chataistudio` · `ltt_llm` · `ltt_voice` ·
`nexus` · `prompt_ai_ommi` · `qualitylab` · `taoanh` · `taoclipngan` · `taovideo` ·
`thumbnail` · `upscalevideo` · `vps`

Moi app khai `slug` trung ten thu muc. Manifest tu 28 dong (`agent`) toi
296 dong (`ltt_llm`).

⚠️ `CLAUDE.md` va ban ke hoach cua toi truoc do ghi "16 app" — sai, do dem ca
`__init__.py`. **Con so dung la 15.**

### 3.3 Diem vao (`if __name__ == "__main__"`)

| Khu | So |
|---|---:|
| `tools/` | **140** |
| `voice_sidecar/` | 6 |
| `docs/` | **6** ⚠️ |
| `render_gateway/` | 4 |
| `llm_gateway/` | 3 |
| `apps/` | 2 |
| moi khu con lai | 1 |

Dich vu that (NSSM) tren may A — 4: `LTTStudioWeb` · `LTTStudioWorker` ·
`LTTStudioCodex` · `LTTStudioVoice`.

⚠️ **140 diem vao trong `tools/`** tren 148 tep — gan nhu moi tep trong `tools/`
la mot CLI. Day la mot be mat lon chua ai kiem ke. Muc tieu Phase 09.

⚠️ **6 script Python chay duoc nam trong `docs/`** — `docs/audit_ltt_llm/artifacts/`
(4), `docs/lttstudios-website/` (1), `docs/_luutru/` (1). Ma chay duoc trong khu
lich su. Muc tieu Phase 01.

### 3.4 Alembic — **sach**

65 revision, **dung 1 head**: `c7b91e4a2f80` (`20260901_2300_voice_tu_dien.py`).
Khong nhanh, khong head mo coi. ✅ Day la mot diem manh bat ngo — khong can lam gi.

### 3.5 Test

- 360 tep `.py` trong `tests/`, 91.282 dong;
- 323 so thu tu phan biet, tu `test_33` toi `test_393`;
- **38 khoang trong** trong day so: `34,36,38-42,47-59,120,121,128,132,152,239,267,268,314-316,335,351,355-359`.
  Cum `47-59` va `34-42` khop voi dot go `socialbot` (Q108) — tuc cac test da bi
  xoa cung app, khong phai bi bo quen;
- 6 fixture server: `clip_studio`, `image_studio`, `prompt_ai_ommi`,
  `qualitylab`, `seedance_studio`, `upscale_studio`.

### 3.6 `docs/` — 1.297 tep, va **75% khong phai su that van hanh**

| Thu muc | Tep | La gi |
|---|---:|---|
| `developer_portal_mvp_ui/` | **504** | 487 **PNG** + 15 md — bang chung audit |
| `APP_AUDIT/` | **406** | bao cao audit theo app, nhieu dot |
| `lttstudios-website/` | 69 | 41 HTML + tai san — mot **website** |
| `UI_REDESIGN/` | 48 | |
| `PUBLIC_API/` | 34 | |
| `_luutru/` | 33 | luu tru tuong minh |
| `audit_ltt_llm/` | 25 | |
| 12 thu muc khac | ~130 | |
| tep `.md` roi o goc `docs/` | ~50 | |

**979 / 1.297 tep (75%)** nam trong ba thu muc dau — deu la **bang chung lich su
hoac nguyen mau**, khong phai luat dang hieu luc.

### 3.7 🔴 Nhung `docs/` **khong** thuan lich su — ranh gioi chua duoc ve

Ba tham chieu tu **ma song** vao `docs/`:

| Tu | Toi | Ban chat |
|---|---|---|
| `tools/audit_public_web.py:13` | `docs/lttstudios-website/route-map.json` | **doc lam HOP DONG** |
| `server/templates/developers_base.html:24` | `docs/developer_portal_mvp_ui/03_...md` | chu thich bang chung |
| `server/templates/dev_keys.html:14` | `docs/developer_portal_mvp_ui/02_...md` | chu thich bang chung |
| `tools/vps_kiem_cau_hinh.py:203-204` | `docs/lttstudios-website/legal/vps-terms.html` | duong tep in ra |
| `apps/vps/dieu_khoan.py:5` | `docs/lttstudios-website/` | ghi chu "truoc 26/08 o day" |

⇒ `docs/` vua chua lich su, vua chua **du lieu hop dong dang duoc doc luc chay
kiem**. Day chinh xac la dieu Prompt 01 goi ten:
*"archived docs referenced as normal guidance"* va *"historical incident comments
controlling current code"*. **Khong duoc xoa `docs/lttstudios-website/` truoc khi
di tru `route-map.json`.**

### 3.8 Rac o thu muc goc **da duoc theo doi**

38 muc goc duoc theo doi, trong do:
- **20 tep `.png`** (`audit_768.png`, `nexus_*.png`, `vm200-*.png`, ...);
- `nuitka-crash-report.xml`.

⇒ 21/38 muc goc la **bang chung/rac**. Ung vien Phase 09.

---

## 4. Baseline: ratchet & checker (da chay, doc-thuan)

| Do | Gia tri | Moc | Bien |
|---|---:|---:|---|
| Nuot loi lang le | **63** | 63 | **0** |
| Chuoi chua dich (i18n) | **774** (114 tep) | 774 | **0** |
| App contract lint | 15 app · 0 ERROR · **1 WARN** | — | |
| Kich thuoc route (`server/admin.py`) | moc 1.388 | | ⚠️ §7.2 |
| Kich thuoc route (`server/admin_api.py`) | moc 1.897 | | |
| Chuong chua treo | 1 muc (`platform_core/upload_sessions.py::reconcile`) | | |

⚠️ **Ca hai ratchet lon dang nam DUNG tren moc, bien bang 0.** Bat ky dong ma
moi nao cung lam gate do. Do vua la ky luat tot, vua la ap luc — no giai thich
vi sao no tich luy.

**WARN duy nhat:** `qualitylab: routes.py khong thay require_login`. Ghi nhan
lam ung vien **an ninh** cho Phase 04/06, khong ket luan voi.

### 4.1 Cau truc gate

`tools/gate.py` — 23 buoc, 5 nhom (`cong`, `nang`, `tinh`, `frontend`, `sau_test`),
goi **21 checker** rieng biet trong `tools/`. Moi buoc sinh tep deu chay o che do
`--check`/`--kiem` ⇒ gate **khong** ghi vao cay. ✅

`FRONTENDS` **ma cung** o `tools/gate.py:61` = 3 thu muc, khop dung 3 thu muc
thuc te trong `frontend/`. Hien tai **khong thieu**; nhung day la mot danh sach
tay, se troi khi them frontend thu tu. Muc tieu Phase 09.

---

## 5. Kien truc — phac hoa baseline

### 5.1 Chuoi chi dan cho agent

```
CLAUDE.md (496 dong)  →  AGENTS.md (697)  →  docs/QUYET_DINH_NEN_TANG.md (382)
                      →  docs/KE_HOACH_TRIEN_KHAI.md (3.668)
                      →  docs/NHAT_KY.md (15.859)
                      →  ho_so_he_thong.txt (303.573)
```

✅ Khong co lien ket `docs/*.md` gay tu `CLAUDE.md` hay `AGENTS.md`.

🔴 Nhung `CLAUDE.md` **tu ghi nhan bon lan noi sai**, ba trong so do la **cung
mot hang**, va **ca bon deu sai ve phia nguy hiem**:

| Dong | Noi dung |
|---:|---|
| 296 | `SUA 2026-08-26 — DOAN NAY TRUOC DO NOI SAI, VA NOI SAI VE PHIA NGUY HIEM` |
| 317 | `SUA LAN HAI 2026-08-30 — LAI LECH, LAI VE PHIA NGUY HIEM` |
| 382 | `SUA LAN BA 2026-09-01 — VA DAY LA LAN THU BA CUNG MOT HANG` |
| 226 | `(VPS) DANG SONG VA CONG KHAI — SUA 2026-08-26, TRUOC DO HANG NAY NOI SAI VE PHIA NGUY HIEM` |

⇒ Day la **bang chung do duoc** cho luan diem trung tam cua Phase 01: trang thai
runtime dang duoc **chep tay** vao mot tep khong ai kiem chung, va no **luon
troi ve phia nguy hiem** (bao "tat" khi dang bat, bao "chua mo" khi dang thu
tien). Sua bang cach viet lai tai lieu se that bai lan thu tu.

### 5.2 Kham pha app — **dong, khong tinh**

`platform_core/registry.py`:
- dong 894: `for entry in sorted(apps_dir.iterdir())` → `importlib.import_module(f"apps.{entry.name}.manifest")`
- dong 927: nap `routes` cung cach
- dong 966-980: nap `tables` cung cach

⇒ **Mot thu muc trong `apps/` LA mot app**, khong can ai import. Moi phan tich
phu thuoc tinh o Phase 02/03 phai cong them co che nay.

### 5.3 Hinh dang trien khai

- 49 script `.ps1` trong `setup/`, 4 buoc cai chinh (`1-kiem-tra-may` →
  `2-cai-dat` → `3-cloudflare` → `4-nghiem-thu`);
- `deploy/windows`, `deploy/wordpress`;
- 4 dich vu NSSM tren may A; gateway/sidecar deploy sang **may B**.

---

## 6. 🔴 Sau cho GOI PROMPT da lech — da xac minh bang do

| # | Goi prompt gia dinh | Do duoc | He qua |
|---|---|---|---|
| 1 | `core/` lon, dong bang, la trong tam Prompt 03 | **0 tep — khong ton tai** | Prompt 03 phai doi muc tieu |
| 2 | `socialbot`/`demo` la uu tien dau | **da go 25/08**; con 38 khoang trong so test | chi con du chan |
| 3 | ~131 nuot loi (78 o frozen core) | **63**, bien 0 | moc cu vo nghia |
| 4 | ~1.800 chuoi chua dich | **774** / 114 tep | moc cu vo nghia |
| 5 | khong biet 6 he con | `cutclipshort` 30.776 + 5 he ~13.000 dong | +44.000 dong vao scope |
| 6 | push len nhanh mac dinh | nhanh la `admin-mvp-v3`, truoc remote 2 commit | phai chot dich push |

---

## 7. Vi sao **BASELINE PARTIAL** chu khong phai **FROZEN**

### 7.1 Chua chay duoc `python tools\gate.py` day du

Da thu luc 13:47 (`--vong-lap`, nhom tinh). No treo qua 5 phut trong khi binh
thuong ~15 giay ⇒ **dung ngay** luc 13:53 va bao cho phien kia.

Ly do khong chay tiep, va no la ly do dung:
1. Phien kia dang chay `gate.py` **day du** cung luc de chuan bi commit. Hai
   luot gate song song lam nhieu lan nhau va co the lam **luot cua ho** do —
   tuc pha viec cua ho.
2. `AGENTS.md` §10.3 canh bao san: gate tu in `CAY DA DOI TRONG LUC CHAY` khi co
   ai ghi vao cay giua luot. Mot baseline do tren cay dang bi ghi **khong phai
   baseline**.

### 7.2 Mot so lech can lam ro (chua ket luan)

`tools/server_routes_baseline.json` ghi `server/admin.py: dong 1388`, nhung
`wc -l server/admin.py` = **1.622** (lech 234). Hai kha nang: checker dem khac
(bo chu thich/dong trong), hoac baseline da troi. **Chua ket luan** — Phase 06
phai doc `tools/check_server_routes.py` roi moi noi.

### 7.3 Duong dong bang baseline — da co, se dung o luot sau

`AGENTS.md` §10.3 chi san cach do baseline sach tren cay dung chung:

```bash
git worktree add --detach <tmp> HEAD
git worktree remove --force <tmp>
```

**Ke hoach:** doi phien kia commit (ho noi ~15 phut), lay **HEAD moi cua ho**
lam moc dong bang, roi chay gate day du. Nhu vay cong cua ho nam **trong**
baseline chu khong nam ngang no.

---

## 8. DO_NOT_TOUCH

| Duong | Ly do | Chu |
|---|---|---|
| `tools/cam_cli.py` | dang sua | `lttstudiosapp-e6` |
| `sdk/ltt_cai_dat_cli.py` | dang sua | `lttstudiosapp-e6` |
| `tests/test_275_cai_dat_cli.py` | dang sua | `lttstudiosapp-e6` |
| `ho_so_he_thong.txt` | tep **dan xuat** — chi nguoi commit sau cung moi sinh (`AGENTS.md` §10.2③) | `lttstudiosapp-e6` |
| `docs/auto_scan_video/` | chua theo doi, khong ro chu | chua ro |
| `tmp/**` | thu muc nhap cua phien kia | `lttstudiosapp-e6` |

---

## 9. Viec Phase 00 con no

1. Chay `python tools\gate.py` **day du** tren cay dung yen → dien §4 va bang
   "Frozen baseline" trong `STATE.md`.
2. Chot HEAD dong bang = commit cua `lttstudiosapp-e6`.
3. Doc `tools/check_server_routes.py` de giai thich lech 234 dong (§7.2).

Ba viec nay **khong chan** Phase 01 (thuan tai lieu) va Phase 02 (thuan phan
tich) khoi dong.
