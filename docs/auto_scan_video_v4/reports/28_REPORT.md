# Phase 28 — Independent re-audit and RC freeze

**Verdict: `BLOCKED_EXTERNAL`.**

Every Phase 26 blocker is independently reverified as closed. **No P0 or P1
finding remains.** No remediation regression and no scope creep were found — the
whole of Phase 27 touched `apps/` only, with **zero** lines changed in
`platform_core/` or `server/`.

⛔ But **G20 is not satisfied**, and the reason is not a defect. Two critical
gates — **G9** and **G17** — require evidence this machine cannot produce today:
a live `ltt_llm_vision` call, a live LTT Voice synthesis, and representative real
customer footage. The pack's rule is explicit and is not negotiable by score:
*missing external evidence is not PASS.*

⇒ Therefore this phase does **not** issue `READY_FOR_PRODUCTION_PILOT`.

🔑 And it deliberately does **not** return to Phase 26 either. `FAIL_REMEDIATE`
exists to send a **defect** back for fixing; there is no defect here to fix, and
a remediation cycle over missing credentials would burn a phase and change
nothing. `V4_TEST_REVIEW_PROTOCOL` has the right verdict for this exact shape:
`BLOCKED_EXTERNAL` — *"record exact missing evidence and stop only if current
gate genuinely requires it."* G9 and G17 genuinely require it.

---

## RC identity

| | |
|---|---|
| **RC SHA** | `747ca288eb1cdb9eeaf0b47e325e450108d54f71` |
| branch | `phien/asv-v4` |
| branch base | `706faca50c75fb5b6dbad6c346b96c98a6736a11` (`phien/asv`) |
| worktree | `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9` |
| gate at RC | `python tools/gate.py --phien asv-v4` → `RESULT: PASS` |
| E2E evidence | `evidence/22_nghiem_thu.json`, regenerated at this SHA |
| performance evidence | `evidence/24_hieu_nang.json`, regenerated at this SHA |

⚠️ The evidence files had to be regenerated for this phase, and that was not a
formality: Phase 27's runs predated commit `9ff469e`, which changed
`cache_dung_duoc` — code that runs inside `chay_giai_doan` on every stage of
every E2E run. Evidence recorded two commits before the RC does not describe the
RC.

---

## 1. Reproduction of every prior finding — read from source at HEAD

Each row was verified by reading the code or running a probe at the RC SHA, not
by reading Phase 27's report.

| finding | independent check | result |
|---|---|---|
| B22-01 | `giai_doan_ban_bien_tap` calls `_doc_cac_canh`, `goi_tinh_tien`, `lenh_rut_khung`; `loi_nhac_canh` emits `image_url` parts | **closed** |
| B22-01 (schema) | `DOC_CANH.truong_bat_buoc == ("de_xuat","do_tin")`, `can_thi_giac=True` | **closed** |
| B24-01 | `asv_media.vram_for("asv_media.render") == 500`; `requires == ("ffmpeg",)` only; no other job type declares VRAM | **closed** |
| B24-01 (decision site) | COMPOSE reads no `gpu_uuid`; RENDER reads it via `getattr` and calls `gpu_env`; RENDER self-grants nothing | **closed** |
| B24-01 (one-way) | `bo_ma_hoa_thuc_te` downgrades nvenc→libx264 without a card, and refuses to upgrade libx264→nvenc with one | **closed** |
| A26-01 | `phien_ban_engine(CONTENT_PROCESS)` → `noi_dung/1/ltt_llm:qwen38-api` | **closed** |
| B23-01 | `cache_dung_duoc` reads `fingerprint`; **no** f-string `in` comparison remains | **closed** |
| A26-02 | `danh_dau_xong` issues `update`; `XungDotDonVi` base is `RuntimeError`, not `SuDungError` | **closed** |
| A26-03 | `tao_run_tu_tai_len(db, owner_id, duong_tep, ten_tep, settings)` — no `du_lieu` parameter | **closed** |
| B25-01 | `MANIFEST.bao_tri` is not None, 3600 s; `assets.quet_het_han` exists | **closed** |
| A26-04 | 🔑 verified by AST comparison: `qc.py` is the **only** changed file whose parse tree is byte-identical before and after — a comment-only change, exactly as declared NOT_FIXED | **as recorded** |

⭐ One correction to my own method, worth recording because it is the same class
of error this whole programme keeps finding: my first probe reported *"RENDER does
not read `gpu_uuid`"*, and that was **the probe being wrong, not the code**.
`getattr(ctx, "gpu_uuid", "")` reads an attribute through a **string literal**, so
an AST walk over `ast.Attribute` nodes cannot see it. A check that looks for the
wrong node type returns a confident, clean, false answer — which is precisely how
four of Phase 27's own checks failed on first write.

---

## 2. Critical evidence re-run at the RC SHA

```
tests/test_448  (real E2E, LTT_TEST_NANG=1)   -> 20 passed
tests/test_450  (real perf, LTT_TEST_NANG=1)  -> 12 passed, 1 skipped
tests/test_4xx  (except the two above)        -> 1051 passed, 3 skipped, 1 xfailed
tools/gate.py --phien asv-v4                  -> RESULT: PASS
```

**Both presets, from the regenerated E2E evidence:**

| run | cuts | scenes read | output | speech regions | QC |
|---|---|---|---|---|---|
| `giu_hinh` (preserve) | 0 | 0 | 32.167 s | 7 | pass |
| `cat_thong_minh` (smart) | **1** | **4** | 27.292 s | 7 | pass |

⭐ Both presets now report **the same number of speech regions**, which is the
visible result of Phase 27's A27-02 fix: before it, the same audio structure
measured as 4 regions in one preset and 1 in the other purely because cutting the
quietest scene moved the median. A measurement that answers differently about two
files with identical speech structure was not measuring speech.

**Encoder, from the regenerated performance evidence:** host offers `h264_nvenc`;
the smart run records `bo_ma_hoa: h264_nvenc`; the preserve run records `''`
(stream copy, no encoder). This is the behaviour B24-01 said was unreachable.

The one remaining `xfail(strict=True)` is
`test_425::test_chuoi_thi_hanh_biet_den_preset` — a **Phase 12** debt about
`pipeline.py` not naming the preset string. It is not a Phase 26 blocker and not
a critical-gate failure.

---

## 3. Regression and scope creep

**Production diff, `bae01d2..747ca28`:** 16 files, all under `apps/`, +723/−90.

⛔ **`platform_core/` and `server/`: zero files changed.** The project's rule is
that needing to change the platform means the app contract is missing something —
and Phase 27 had a live opportunity to break it. B25-01's fix needed a periodic
sweeper, and instead of building a loop inside the app it used
`AppManifest.bao_tri`, a hook the platform already had. That is the contract
working as designed.

Every changed file maps to a named finding:

| file | finding |
|---|---|
| `asv_media/manifest.py`, `giai_doan_ban_dung.py`, `giai_doan_ket_xuat.py`, `ket_xuat.py` | B24-01 |
| `ai.py`, `hieu_canh.py`, `giai_doan_ban_bien_tap.py` | B22-01 |
| `assets.py` | B23-01 + B25-01 |
| `thi_hanh.py` | A26-01 + B25-01 |
| `features.py`, `routes.py` | A26-03 + B25-01 |
| `su_dung.py`, `loi.py` | A26-02 |
| `gia.py` | A26-05 |
| `auto_scan_video/manifest.py` | B25-01 |
| `qc.py` | A26-04 (comment only) |

**No file changed for a reason outside the audit.**

---

## 4. Feature flags, lifecycle, schema, resource config

| | |
|---|---|
| `auto_scan_video` | `enabled=False`, `public=False`, `surface=customer`, `lifecycle=development`, `requires=("api",)` |
| `asv_media` | `enabled=False`, `public=False`, `surface=runtime`, `lifecycle=internal`, `requires=("ffmpeg",)` |
| `asv_gpu` | same, `requires=("gpu",)` |
| `asv_voice` | same, `requires=("voice",)` |

⛔ **`enabled=False` does not close a route** — `registry.mount_all` mounts every
app's router regardless (V4-R11). The thing that actually closes it is the
`_cong_co` dependency, and it must sit **before** `require_login`, because
`Depends` runs in declaration order and a route "already closed" would otherwise
still redirect to `/login`. Verified by AST across **all 8 route handlers**: every
one has `_cong_co`, and none has it after `require_login`.

**Resource declarations:** `asv_media.render` is the only `asv_media` job type
declaring VRAM (500 MiB, measured). `asv_gpu` declares 2 200 / 6 000 MiB for
`audio_prepare` / `transcribe`. `EDIT_PLAN` and `CONTENT_PROCESS` share the
`llm_remote` admission slot; `AUDIO_PREPARE` and `TRANSCRIBE` share
`tach_nguon_cuc_bo` — still one slot, still on the written condition that Phase 24
measured and **failed** (peak CPU 78.6 % against a 70 % bar).

**Schema:** `test_451::test_MIGRATION_va_MODEL_khong_lech_o_bang_ASV` and
`test_MOI_bang_ASV_deu_co_trong_CSDL_sau_migration` both pass at the RC SHA.
Phase 27 added no column and no migration.

---

## 5. Gate matrix at the RC SHA

| gate | verdict | basis |
|---|---|---|
| G1 Provenance/worktree | **PASS** | source SHA recorded and matching; dedicated worktree; V2 docs retained |
| G2 Contract supersession | **PASS** | `hop_dong_v4.PHIEN_BAN_BI_THAY_THE`; ADR-V4-001 |
| G3 Capability ownership | **PASS** ⬆ | was FAIL. No second AI transport (verified: no `requests`/`httpx`/`urllib` in any of the four app packages). The translation fingerprint now reads the live model map. ⚠️ `dich_thuat.py` still exists as a dead second path — held by `test_453`'s ratchet with a written reason, not silently |
| G4 Runtime invariants | **PASS** ⬆ | was FAIL. Revision safety now enforced by a conditional `UPDATE` for work items, and the stage cache returns hits for the first time |
| G5 Durable item granularity | **PASS** | per-segment checkpoints; Phase 27 added per-**scene** checkpoints on the same mechanism, no second queue |
| G6 Large input | **PASS** ⬆ | was FAIL. The upload path streams in 1 MiB chunks and enforces the ceiling mid-stream; the business layer takes a path, not bytes |
| G7 Resource safety | **PASS** | heavy tests behind `LTT_TEST_NANG`; profiles measured |
| G8 GPU correctness | **PASS** ⬆ | was FAIL. Hardware encode reached and used, with a measured declaration; no GPU on stream-copy; no self-granting. ⚠️ carries **V4-R15** |
| G9 Scene/VLM | 🔴 **NOT PASS** | the path is built, wired and schema-validated, and it runs end to end against a substitute. **No live `ltt_llm_vision` call has ever been made.** Blocked on external evidence |
| G10 Content/EditPlan | **PASS** ⬆ | was PARTIAL ("traceability is vacuous — there are no cut decisions"). Verified now: cuts happen, each decision carries reason, confidence, the threshold used and an evidence reference; `preserve` refuses to cut even when every scene is recommended for removal; `so_doan_bi_cat: 1` proves no dubbing spend on a dropped scene |
| G11 Voice | **PASS** (qualified) | boundary via the declared `apps.ltt_voice` surface, no sidecar internals. ⚠️ Vietnamese **voice quality** is not evidenced — see external evidence |
| G12 Dubbing fit | **PASS** | bounded ladder, segment reuse, no infinite retry |
| G13 Render | **PASS** ⬆ | was PARTIAL. Deterministic manifest; preserve stream-copies; smart cuts now use the accepted hardware encoder; renderer calls no AI |
| G14 QC/repair | ⚠️ **PARTIAL** | technical QC full. 🔴 And Phase 26's basis **understated it**: it recorded "repair plan computed but never driven"; Phase 27's orphan check found that `qc_ai.py` itself has **no caller in product code** either (A27-01). Semantic and visual QC are built and unreachable |
| G15 Billing | **PASS** | one owner; `UNIQUE(run_id, ma_dispatch)`; ambiguity never auto-retried. Per-scene calls go through the same paying door |
| G16 UI/product truth | **PASS** ⬆ | was FAIL. The smart preset's description now states the case where nothing is cut and the video is re-encoded anyway. Flag gate verified before login on all 8 handlers |
| G17 E2E | 🔴 **NOT PASS** | both presets pass end to end on a synthetic source, with restart/retry/cancel/missing-artifact/ambiguity all covered. **No representative real customer video, no live model, no live voice.** Blocked on external evidence |
| G18 Performance | **PASS** | no sustained saturation; smart render GPU path now benchmarked (244 fps, ~8× realtime) |
| G19 Security/hardening | **PASS** ⬆ | was PASS with a P2 gap. Retention is now swept, and the deliverable no longer carries an expiry a sweeper would act on. Six-object IDOR, CSRF, redaction, migration parity all hold |
| **G20 Independent re-audit** | 🔴 **NOT SATISFIED** | **no P0/P1 blockers remain** — that half is met. The other half, "all critical gates reverified", fails on **G9** and **G17** |

**Movement: six gates FAIL → PASS, two PARTIAL → PASS, one PARTIAL stays and is
now better understood, two remain blocked on evidence nobody in this session can
produce.**

---

## 6. Exactly what is missing, and exactly what closes it

Measured on this machine at the RC SHA — not inferred:

```
LTT_LLM_BASE_URL / LTT_RENDER_BASE_URL       not set in this process
LTT_VOICE_SIDECAR_TOKEN                      not set in this process
127.0.0.1:8100  open      (platform web)
127.0.0.1:8120  OPEN      (LTT Voice sidecar - answers 401 without a token)
tests/fixtures/asv_e2e_that/                 does not exist
```

🔴 **CORRECTION, made after this report was first written and left standing
here rather than edited away.** The two lines that used to sit in that block
read:

```
127.0.0.1:8199  unreachable  (machine B image gateway)
127.0.0.1:8299  unreachable  (machine B LLM gateway)
```

They were **wrong, and wrong in the direction that makes the situation look
worse than it is.** The machine B gateways do not listen on machine A's
loopback — they listen on **machine B**, at `192.168.2.66`. Probing
`127.0.0.1` there measured nothing about machine B at all. Re-measured over the
LAN:

```
ping 192.168.2.66                 alive
192.168.2.66:9443   OPEN   nexus worker
192.168.2.66:9444   OPEN   nexus controller
192.168.2.66:8199   OPEN   ltt_image   -> HTTP 401 {"detail":"render gateway: sai token"}
192.168.2.66:8299   OPEN   ltt_llm     -> HTTP 401 {"detail":"token khong dung"}
```

⭐ So machine B is **up, serving, and refusing only for lack of a token** —
the same shape as the voice sidecar. And `docs/audit_ltt_llm/` holds **live**
measurements against that gateway (`413 {"tran":65536,...}`), which could not
exist without a working pool key. ⇒ The `ltt_llm` credential almost certainly
**already exists** in the pool; what this audit process lacks is a way to read
the pool at all, because `LTT_DATABASE_URL` lives in the ACL-locked `app.env`.

⚠️ The error is instructive and belongs in the record: a probe aimed at the
wrong address returns a clean, confident, false answer — the **second** time in
this one phase (the first was the `gpu_uuid` AST probe). Both times the tool
answered exactly what it was asked, and the question was wrong.

| # | needed | closes | note |
|---|---|---|---|
| 1 | Access to the **existing** `ltt_llm` pool row — not a new key. The gateway is up and the credential is already provisioned; the test process simply cannot read the pool without `LTT_DATABASE_URL` | **G9**, G17 | closed by loading `app.env` into one process (Administrator), not by minting anything |
| 2 | `LTT_VOICE_SIDECAR_TOKEN` for `127.0.0.1:8120` | G11 quality, G12 quality, **G17** | the port is open — only the token is missing |
| 3 | Two real customer videos, one per preset, dropped in `tests/fixtures/asv_e2e_that/` | **G17** | the smart-preset sample needs at least one scene genuinely worth cutting |
| 4 | *(optional)* CUDA 12 cuBLAS in the dev tree, or permission to measure the production WhisperX sidecar | G7, G24 detail | production is unaffected — it already uses the sidecar |

⛔ Item 1 is **not** a customer deployment burden: for an operator it is one pool
row created once in admin, the same as any other provider. It is missing *here*
because this audit process holds no credentials, which is the correct posture.

---

## 7. Hostile self-review of **this** phase

Phase 28 changed no code, so the protocol's questions are turned on the audit.

| question | answer |
|---|---|
| Did the audit trust the previous phase's claims? | No. Every finding was re-derived from source at HEAD. That caught nothing wrong in the code — and caught **my own probe** being wrong about `gpu_uuid` |
| Did it accept a green suite as proof of a product gate? | No. `V4_TEST_REVIEW_PROTOCOL` says outright *"a green unit suite cannot override a failed product/E2E gate"*, and that is exactly the situation: 1 051 tests pass and G17 still does not |
| Did it regenerate evidence, or reuse stale files? | Regenerated. The previous evidence predated a commit that changes code running in every E2E stage |
| Was any gate marked PASS to make the matrix look finished? | ⭐ Two were deliberately **not**. G14 stays PARTIAL and its basis is recorded as *worse* than Phase 26 thought. G11/G12 are PASS on their stated propositions with the quality qualification spelled out — Phase 26's own record was internally inconsistent here (gate table PASS, evidence table "blocked"), and the honest reading is that the code propositions hold and the quality claim was never evidenced |
| Was the verdict softened to let the phase finish? | No. `BLOCKED_EXTERNAL` is the least convenient of the three available verdicts: it does not ship, and it does not hand the work to another phase either |
| Could a reader mistake this for approval to deploy? | The prompt's own words are reproduced here: `READY_FOR_PRODUCTION_PILOT` **is not** permission to deploy or merge master — and this phase does not even issue that |

---

## 8. RC handoff notes (for whoever closes the external evidence)

The RC is **frozen at `747ca28`** and is complete as a code artifact. To finish
G9 and G17, in this order:

1. Set `LTT_VOICE_SIDECAR_TOKEN` in a process-scoped shell and re-run
   `tests/test_448` with `LTT_TEST_NANG=1`. The port is already open, so this is
   the cheapest of the three and it closes the voice half.
2. Machine B needs nothing restored — it is up. Run the same bridge with the
   model door left real, so `dieu_phoi.goi` resolves the **existing** pool key. `EDIT_PLAN` will make **one call per scene** —
   ⚠️ size frame batches against the **measured 28 262-token** vision window, not
   the 131 072 text alias (V4-R08).
3. Drop two real videos in `tests/fixtures/asv_e2e_that/` and re-run both presets.
   ⛔ Add that directory to `.gitignore` before the first file lands — customer
   footage must never enter the repository.

⚠️ Do not re-run Phase 27. Nothing in that phase is waiting on these; the code is
done and independently verified.

**Known non-blocking debt carried into the pilot:** A27-01 (semantic/visual QC and
repair unreachable, P2) · A27-02 (measurement-premise class, P3) · V4-R15 (NVENC
engine contention not modelled by `gpu_lease`, P2) · the Phase 12 preset-naming
debt pinned by `test_425`.

---

## Exit verdict

**`BLOCKED_EXTERNAL`** — no P0/P1 blockers remain and eighteen of twenty gates are
green, but **G9 and G17 require evidence that does not exist on this machine**, so
**G20 is not satisfied** and no RC may be declared ready for a production pilot.

⛔ This is **not** `FAIL_REMEDIATE`: there is no defect to remediate, and returning
to Phase 26 would spend a cycle on missing credentials.
⛔ This is **not** `READY_FOR_PRODUCTION_PILOT`, and that phrase would not have
been permission to deploy even if it had been issued.

⇒ **Stop here.** Resume at step 6 above when the operator supplies the three
items; the re-audit then needs only the two heavy suites re-run and this matrix
updated.
