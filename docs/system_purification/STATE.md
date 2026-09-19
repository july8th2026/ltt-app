# SYSTEM PURIFICATION STATE

> SSOT ban giao giua cac phase. Chi chua **su that hien tai**.
> Bang chung chi tiet nam o `reports/`.

## Program identity
- Repo: `giaitritruyenthongltt-spec/LTTSTUDIOSAPP`
- Branch: `admin-mvp-v3` (truoc `origin/admin-mvp-v3` 2 commit)
- Baseline revision: **`89eb46c`** ✅ CHOT (commit cuoi cua `lttstudiosapp-e6`)
- Current revision: `89eb46c` + nhanh `phase-minus-1-foundation`
- Baseline date: 2026-09-02
- Live environment access: co. 🔴 **`89eb46c` DA DUOC DEPLOY luc 14:15 ngay 02/09** —
  moc so sanh cua chuong trinh nay la moc **DANG PHUC VU KHACH THAT**, voi 5 tool
  mo va thu tien. Cai gia cua mot lan xoa nham khong con la "gate do" ma la
  "mot khach 500". ⛔ Chuong trinh nay van **khong deploy**.
- Current phase: **-1 ✅ · 00 ✅ · 01 ✅ · 02 ✅ → tiep 03**
- Quyet dinh nhanh (QD-1 SUA): **khong** dung `purification-v1` nua. Moi phien
  mot cay rieng qua `tools/cay_rieng.py`; Phase -1 chay tren
  `phase-minus-1-foundation`. Phase 10 van **khong** dung vao `master`.

## ⭐ Phase -1 — nen tang nhieu phien (chen truoc, theo yeu cau nguoi dung)

Bao cao: `docs/_luutru/2026-09/system_purification/reports/phase_minus_1_multi_agent_foundation.md`
(da luu tru 19/09 - khong con file/nhanh nao tro toi tru STATE.md nay)

**Vi sao no phai chen truoc:** trong DUNG mot gio dau cua Phase 00 da co **ba**
su co dieu phoi that giua hai phien cung cay — doi nhanh cua phien khac, gate
treo vi tranh CPU, va toan bo viec chia tep phai lam bang tay qua tin nhan. Cac
phase sau (03–09) **xoa ma**, nen chung nguy hiem hon Phase 00 nhieu lan.

**Quy trinh MOI bat buoc cho moi phase con lai:**

| Truoc | Nay |
|---|---|
| lam tren cay chinh | `python tools/cay_rieng.py tao <ten>` — **moi phase mot cay** |
| `gate.py` day du de do | `gate.py --doi` trong vong lap, day du **mot lan** cuoi phase |
| khoa gate mot muc | khoa theo **ten tai nguyen** |
| khong biet gate nao chay tren ma nao | `test-results/gates/<id>.json` |
| moi phien tu suy quy trinh | `docs/DEVELOPMENT_WORKFLOW.md` |

⛔ **Hai muc cua purification bi Phase -1 DOI CHU SO HUU** — dung lam lai:
- Phase 01 van so huu `CLAUDE.md`/`AGENTS.md` (Phase -1 **khong** dung vao,
  du prompt cua no co muc N);
- Phase 02 van so huu ban do kien truc (Phase -1 hoan muc L vi ly do do).

⭐ **Phase -1 da tra truoc mot phan viec cua Phase 02:** `tools/thanh_phan.py`
la mot do thi so huu **chay duoc**, va no da lo ra mot vi pham phan tang that:
`server/routes/dashboard.py:134` import thang `apps.anhnoibo`. Phase 06 nhan
muc nay.


## Phase da dong

| Phase | Ket qua | Commit |
|---|---|---|
| **-1** nen da phien | `FOUNDATION PASS` — 37 thanh phan, khoa theo tai nguyen, `--doi`/`--pham-vi`, kho ket qua, 27 chot tu kiem | `65aef31` |
| **00** baseline & census | `BASELINE PARTIAL` -> da hoan tat khi cay ranh | (trong `65aef31`) |
| **01** truth/rules/docs | `CLAUDE.md` 496 -> 263 dong; 280 dong trang thai -> luu tru NGUYEN VAN; nguon trang thai = may chu | `0ba995a` |
| **02** dependency & ownership | 37 thanh phan, 5 canh `server -> app`, 1 canh cheo app, **0 DEAD** | `0ba995a` |

### Giao cho phase sau (tu Phase 02)

| Muc | Phase | Viec |
|---|---|---|
| 5 canh `server -> app cu the` | 04 + 06 | dua gia/ngan sach vao `AppManifest`, doc qua registry |
| `core:tien` chi 9 tep test import truc tiep | 07 | chung minh bat bien tien duoc canh o dau |
| `app:taovideo -> app:upscalevideo` | 04 | giu (COMPAT da khai) hay dua len `platform_core` |
| `server:web` phu thuoc 15 thanh phan | 06 | tach theo trach nhiem, khong theo so dong |
| `qualitylab/routes.py` thieu `require_login` | 04 + 06 | doc that, dung tin linter |
| ⛔ 8 muc "khong ai tieu thu" | — | **da giai thich**, KHONG mang sang 03 nhu ung vien xoa |

## DO_NOT_TOUCH
| Path/change | Reason | Owner |
|---|---|---|
| `tools/cam_cli.py` | dang sua | `lttstudiosapp-e6` |
| `sdk/ltt_cai_dat_cli.py` | dang sua | `lttstudiosapp-e6` |
| `tests/test_275_cai_dat_cli.py` | dang sua | `lttstudiosapp-e6` |
| `ho_so_he_thong.txt` | tep **dan xuat**, chi nguoi commit sau cung moi sinh (`AGENTS.md` §10.2③) | `lttstudiosapp-e6` |
| `docs/auto_scan_video/` | chua theo doi, khong ro chu | chua ro |
| `tmp/**` | thu muc nhap | `lttstudiosapp-e6` |

## Frozen baseline
| Metric | Value | Evidence |
|---|---:|---|
| gate (day du) | ✅ **PASS** (0 FAIL, 4 buoc tu khai BO QUA) | luot `P01-FINAL` |
| pytest | **5.314 passed · 32 skipped · 0 failed** | luot `P01-FINAL` |
| frontend tests | ✅ 3/3 PASS **tren cay chinh** (o cay rieng: BO QUA, thieu `node_modules`) | luot `MAIN-P01` |
| silent exceptions | **63** / moc 63 (bien **0**) | `check_silent_except.py` |
| i18n debt | **774** chuoi / 114 tep, moc 774 (bien **0**) | `check_i18n.py` |
| app-contract warnings | 15 app · 0 ERROR · **1 WARN** (`qualitylab` thieu `require_login`) | `lint_app_contract.py` |
| secret findings | **0** | trong gate |
| current rule conflicts | **0** trong tap dang hieu luc (280 dong trang thai da chuyen sang luu tru) | `reports/01` §6 |
| `.py` theo doi | 1.169 | `git ls-files` |
| tep `docs/` | 1.297 (75% o 3 thu muc bang chung) | |
| Alembic | 65 revision, **1 head** `c7b91e4a2f80` ✅ | |
| test | 360 tep, 323 so, **38 khoang trong** | |

## Architecture owners
| Concern | Canonical owner | Evidence |
|---|---|---|
| Kham pha app | `platform_core/registry.py:894` — `iterdir()` + `importlib` (**dong**) | doc truc tiep |
| Tep cho khach tai | `server/routes/tai_lieu_api.py:124` `GOI_TAI` (**tra bang chuoi**) | doc truc tiep |
| Trang dung san / lien ket cong khai | `server/templating.py:204` `BUILT_PAGES`, `:119` `PUBLIC_LINKS` | doc truc tiep |
| Tep tai Nexus | `server/nexus_download.py:30` `_CONTENT_TYPE` | doc truc tiep |
| Cong chat luong | `tools/gate.py` — 23 buoc, 21 checker, 5 nhom | doc truc tiep |
| (con lai) | ⏳ Phase 02 | |

## Classification summary
| Class | Count | Notes |
|---|---:|---|
| ACTIVE | — | ⏳ Phase 02 |
| SHARED | — | ⏳ Phase 02 |
| COMPAT | — | |
| FROZEN | — | |
| HISTORICAL | — | ung vien: `docs/developer_portal_mvp_ui` (504), `docs/APP_AUDIT` (406), `docs/_luutru` (33) |
| DEAD | — | ⛔ chua tep nao du bang chung |
| DUPLICATE | — | |
| UNKNOWN | ca kho | mac dinh o Phase 00 |

## Decisions
| ID | Phase | Item | Decision | Evidence | Removal/keep condition |
|---|---|---|---|---|---|
| SP-01 | 00 | Nhanh lam viec | Tao `purification-v1` khi cay ranh; **khong** dung `master` | QD-1 | Phase 10 push nhanh do |
| SP-02 | 00 | 4 tep + `tmp/` cua phien kia | `DO_NOT_TOUCH`, khong commit, khong xoa | giao uoc §10.2 | go khi `lttstudiosapp-e6` nha |
| SP-03 | 00 | `cutclipshort/` + 5 gateway/sidecar | IN scope cho **phan loai**, OUT cho **xoa** | QD-3 | chi xoa khi chung minh khong nguoi tieu thu o **ca hai** may |
| SP-04 | 00 | Be mat tra-bang-chuoi | **LUAT CUNG**: doi chieu 5 co che truoc moi lan xoa | `reports/00` §2.2 | vinh vien |
| SP-05 | 00 | Baseline dong bang | Lay **commit cua `lttstudiosapp-e6`**, khong phai `6b25ada` | `reports/00` §7.3 | khi ho commit xong |

## Debt metrics
| Metric | Baseline | Current |
|---|---:|---:|
| Nuot loi lang le | 63 | 63 |
| i18n | 774 | 774 |
| App-contract WARN | 1 | 1 |
| Tep `.py` theo doi | 1.169 | 1.169 |
| Tep `docs/` | 1.297 | 1.297 |
| Muc goc duoc theo doi | 38 (21 la PNG/rac) | 38 |
| Diem vao trong `tools/` | 140 | 140 |
| Script `.py` nam trong `docs/` | 6 | 6 |
| Khoang trong so test | 38 | 38 |

## Critical gates
| Gate | Status | Evidence |
|---|---|---|
| G1 auth/isolation | ⏳ | |
| G2 money | ⏳ | |
| G3 jobs | ⏳ | |
| G4 storage | ⏳ | |
| G5 provider/API | ⏳ | |
| G6 deployment | ⏳ | |
| G7 security | ⏳ | ⚠️ ung vien: `qualitylab` thieu `require_login` |
| G8 app contracts | 🟡 | 15/15 app nap duoc, 0 ERROR, 1 WARN (`qualitylab`) |
| G9 frontend | ⏳ | |
| G10 current truth | ✅ | `CLAUDE.md` 496→263 dong; trang thai nay **hoi may chu**. Da tim ra lan troi thu **SAU** (31/07) |

## Open risks
| Priority | Risk | Owner phase | Next evidence/action |
|---|---|---|---|
| **P0** | Phien khac dang ghi vao cay ⇒ moi phep do va moi lan xoa deu co the pha viec ho | 00 | doi ho commit; giu giao uoc |
| **P0** | Tep tra-bang-chuoi trong mo coi ⇒ phep do tinh se cham CHET nham | 03,04,09 | SP-04 |
| ✅ | ~~Trang thai chep tay vao `CLAUDE.md`~~ — **DA XU LY** o Phase 01 | — | `api_prod_canary.py trang-thai` |
| **P1** | Hai ratchet lon nam **dung tren moc**, bien 0 | 08,09 | ha moc bang cach giam no that |
| **P2** | `docs/` chua **du lieu hop dong** dang duoc doc luc chay (`route-map.json`) | 01 | di tru truoc khi dung `docs/` la "lich su" |
| **P2** | `qualitylab/routes.py` khong thay `require_login` | 04,06 | doc that, dung ket luan tu linter |
| **P2** | 140 diem vao CLI trong `tools/` chua ai kiem ke | 09 | |
| **P3** | Lech 234 dong giua `server/admin.py` va baseline cua no | 06 | doc `check_server_routes.py` |

## Next phase
- Prompt: **01 — Truth / Rules / Docs Purification**
- Questions:
  - Bao nhieu luat trong `CLAUDE.md`/`AGENTS.md` la TRANG THAI chu khong phai LUAT?
  - Gia tri nao (cong, duong, tran token, gia) xuat hien o >1 noi ma khong co chu?
  - `docs/lttstudios-website/route-map.json` phai chuyen di dau?
- Required evidence: bang `Rule → owner → class` phu het `CLAUDE.md` (496 dong)
  + `AGENTS.md` (697) + `QUYET_DINH_NEN_TANG.md` (382).
- ⛔ Rang buoc: `CLAUDE.md`/`AGENTS.md` la **tep dung chung** ⇒ chi `Edit` khop
  chuoi chinh xac, **khong bao gio** `Write` de (`AGENTS.md` §10.2②).
