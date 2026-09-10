# PHASE 11 REPORT — Content Processing and LTT_LLM Adapter

**The first stage that spends real money at a provider.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 10 **PASS**; Phase 07 (credential scoping) **PASS**
- allowed change scope: content service/provider adapter, prompt resources, tests

## Trace performed (item 1) — the real contract exists

| What | Where | Finding |
|---|---|---|
| job handler | `apps/ltt_llm/jobs.py:22 handle` | reads **only** `params`; passes `ctx.provider_dispatched` / `ctx.provider_rejected` straight through |
| tool contract | `apps/ltt_llm/manifest.py:161` | `text.chat`, `api_exposed=True`, `admission_resource="llm_remote"`, `admission_slots=1` |
| dispatcher | `platform_core/llm/dieu_phoi.py:137 goi` | `on_dispatch`/`on_rejected` hooks, `AmbiguousProviderError` on connection loss **after** sending, per-provider model ids, key selection via `api_pool` |
| token budget | `apps/ltt_llm/ngan_sach.py:132 mac_dinh_cho` | single source of truth; three hand-typed numbers, everything else derived |

**RISK-03-01 is resolved: yes.** `ltt_llm.chat` accepts parameters from any caller — its
handler reads `params` and nothing else, and it is a public API tool.

## Amendment to ADR-001 D5 — stated, not slipped in

ADR-001 D5 planned to **delegate** CONTENT_PROCESS as a child `ltt_llm.chat` job. After
tracing the real contract, delegation **cannot do the job here**:

- this stage must chunk, call N times, merge, and detect a short response;
- `ltt_llm.chat` is **one** call, and `asv_stage` holds **one** `job_id` per stage.

So CONTENT_PROCESS calls `platform_core/llm/dieu_phoi.goi()` directly instead — which is what
`apps/ltt_llm/manifest.py` itself instructs: *"Gọi qua `platform_core/llm/dieu_phoi.py` —
đừng tự dựng HTTP, đó đúng là lỗi mà `dieu_phoi` sinh ra để sửa."*

**What D5 was actually protecting is kept intact:** no second HTTP path, no self-selected
key, provider-dispatch safety still owned by the platform. What changed is only *which
platform entry point* is used. Recorded in `pipeline.py` at the line that carries it.

Consequence: CONTENT_PROCESS moved from `asv_media` (ffmpeg) to `auto_scan_video` — the only
app declaring `requires=("api",)`. A model call needs no ffmpeg, and putting it on the ffmpeg
lane would hold a scarce ffmpeg slot waiting on the network.

## Decisions

**D-11-01 — two documents; the transcript is immutable.** `content.json` is a new artifact
referencing `transcript.json`. The transcript is *evidence* of what was heard; the translation
is an *interpretation*. Overwriting evidence with interpretation loses the ability to answer
"what was this translated from" when a customer disputes it, and forces re-transcription on
every re-translation.

**D-11-02 — the model returns JSON keyed by segment id.** This makes the merge deterministic:
no positional matching, no guessing which output belongs to which input, and a missing id is
**measurable** rather than inferred. Both original and translated text are kept per entry.

**D-11-03 — a short response fails the stage.** Accepting a partial translation means the dub
goes silent at exactly those moments, and nobody finds out why.

**D-11-04 — one provider, no silent fallback** (item 8). `THU_TU_PROVIDER = ("ltt_llm",)`.
Changing model changes translation quality — that is a product change, and doing it silently
hands the customer a different result with no notice. A test asserts the tuple stays length 1.

**D-11-05 — the token budget is requested by door name.** `ngan_sach.mac_dinh_cho("job")`,
never a generic default. CLAUDE.md records the real bug: the stream door borrowed the sync
door's 1 024 budget and **every long answer was cut at exactly 1 024 tokens, silently**. A
test pins the call site.

**D-11-06 — the stage claims `llm_remote`, the same admission resource as `ltt_llm`.**
Its job/sync/stream doors all contend for one slot on máy B; declaring the same name makes
the platform queue them together instead of two apps colliding on one machine. Captured at
**submit** time (`Job.admission_resource`), not re-derived at run time — a deploy that edits
`pipeline` must not move already-queued work to a different pool.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/van_ban.py` | **new** — ProcessedText contract, build, validate, fingerprint, safe summary |
| `apps/auto_scan_video/dich_thuat.py` | **new** — prompt, chunking, deterministic merge, ambiguity classification |
| `apps/auto_scan_video/giai_doan_noi_dung.py` | **new** — stage body |
| `apps/auto_scan_video/pipeline.py` | CONTENT_PROCESS → api lane; `+tai_nguyen` fields |
| `apps/auto_scan_video/manifest.py`, `jobs.py`, `thi_hanh.py` | second job type, dispatch, admission at submit |
| `apps/ltt_llm/__init__.py` | `+BE_MAT_CONG_KHAI` — **declaration only, no logic touched** |
| `tools/lint_app_contract.py` | +1 declared edge |
| `tests/test_408_asv_dich_thuat.py` | **new**, 23 tests |
| `tests/test_402…`, `tests/test_403…` | `+dich_gia` fixture |
| `locale/en/LC_MESSAGES/messages.po` | +16 entries |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_408…` | **23 passed** |
| `pytest tests/test_402… test_403…` | **35 passed** |
| `python tools/lint_app_contract.py` | `ERROR: 0` |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

### Required verification

| Required | Test |
|---|---|
| malformed response | 3 parametrized shapes — non-JSON, broken JSON, wrong type |
| partial response | missing ids rejected, **with counts** in the message |
| ambiguous crash | `AmbiguousProviderError` → `DichMoHo`, and the queue check proves the job does **not** return |
| retry does not duplicate an ambiguous call | `test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi` — asserts `jobs.claim` finds nothing afterwards |
| definite rejection vs ambiguity | separate exception types; a non-ambiguous error stays retryable |
| dispatch semantics used | `on_dispatch`/`on_rejected` asserted to be forwarded from `JobContext` |
| real smoke with authorized credential | **not run** — see §"pending" |

## The chain-fixture pattern, third occurrence

CONTENT_PROCESS calling the real dispatcher made the chain tests fail with
`ThieuKeyError` — correctly: no key, no call. A test suite must not require a paid credential.

Same resolution as ASR in Phase 10: a `dich_gia` fixture substitutes the translation, and the
real call path (chunking, merge, ambiguity classification) is tested separately in
`test_408`. The fixture's docstring says so, so a green chain test is never mistaken for
evidence that translation works.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| **I5 provider ambiguity** | PASS — now live, not theoretical | dispatch hooks forwarded; ambiguous → terminal; queue empty afterwards |
| I7 credential isolation | PASS | key selection stays inside `api_pool` with the Phase 07 scopes |
| I8 durable DONE | PASS | document re-validated after reading back |
| I10 cache correctness | PASS | fingerprint = transcript checksum + prompt version + provider + model + language + schema |
| I12 routing | PASS | exit-gate test asserts `app_slug == "auto_scan_video"` and `admission_resource == "llm_remote"` |
| I15 legacy compatibility | PASS | `ltt_llm` gained a declaration, **no logic change** |
| I16 safe logs | PASS | `tom_tat` carries counts only; a test asserts dialogue never reaches `outputs` |
| I1–I4, I6, I9, I11, I13, I14, I18, I19 | PASS | 35 chain tests green |

## Diff review
- changed paths: `apps/auto_scan_video/`, `apps/ltt_llm/__init__.py` (declaration only),
  `tools/lint_app_contract.py`, `tests/`, `locale/en/`
- one scratch script created and deleted; `.po` appended only, LF preserved
- no secret in any fixture; secret scan PASS

## A field I invented and had to remove

I first wrote `admission_resource_mac_dinh=` into `AppManifest`. That field does not exist —
`platform_core/registry.py:131` shows `admission_resource` belongs to `ToolSpec`. Inventing a
manifest field is a platform-contract change (O20) dressed up as configuration.

Corrected: admission is captured at **submit** time via `jobs.submit(admission_resource=…)`,
which already existed. The right place, and no core change.

## Risks / external evidence pending

- 🔴 **RISK-11-01 (P1, new) — no real model call has been made.** Every test here uses a
  stub. A real call needs `llm_gateway` on máy B live plus a valid key — an external
  dependency the suite must not demand. So **translation quality, Vietnamese-vs-source
  length (RISK-02-01), and real 429/timeout behaviour are all unmeasured.**
  `TestChoBangChungNgoai` records this so Phase 21 does not read a green suite as a verified
  translation path. `PENDING_EXTERNAL_EVIDENCE`.
- **RISK-11-02 (P2, new)** — `DOAN_MOI_LO = 20` was chosen to be safe, not measured. Too large
  risks truncation on long segments; too small loses context and multiplies paid calls.
  Measure in Phase 21.
- **RISK-02-01 becomes urgent for Phase 13.** `fit_original` assumes Vietnamese fits the
  source segment window often enough to be usable, and Vietnamese is typically *longer* than
  English. The prompt asks the model to keep length close, but that is a request, not a
  guarantee. Phase 13 must measure the overflow rate.
- **RISK-05-01** (VRAM unmeasured), **RISK-10-01** (whisperx absent), **RISK-10-02** (no real
  speech sample) unchanged; each has a test that fails when its assumption expires.

## Exit gate

**PASS.**

Gate text: *"PASS when content stage is provider-swappable, lineage-stable and safe under
paid-call failure."*

- **Provider-swappable** — provider and model are parameters of
  `dieu_phoi.goi(thu_tu_provider=…, model_theo_provider=…)` and both are **inside the
  fingerprint**, so swapping one invalidates the cache instead of silently mixing outputs
  from two models. Swapping is a one-line change plus a deliberate fingerprint bump.
- **Lineage-stable** — the exit-gate test round-trips through storage and asserts the
  translated document's segment ids equal the transcript's, **as sets and in order**, and
  that the source transcript is still intact afterwards.
- **Safe under paid-call failure** — malformed, partial, ambiguous and ordinary errors are
  four distinct outcomes. The ambiguous one is terminal and is proven not to re-enter the
  queue, which is the half that cannot be tested with a unit test.

**Explicitly forbidden and confirmed absent:** the TranscriptDocument is never mutated (a
test byte-compares it before and after); no voice generation in this stage.

## Next phase prerequisites

Phase 12 (Voice Provider Integration):
1. `ltt_voice.synthesize` declares `requires=("voice",)` honestly and is a public API tool
   (`speech.ltt`) — so ADR-001 D5's **delegation** choice should hold here, unlike CONTENT.
   Verify before building;
2. **1 500 characters per call is a QUALITY ceiling, not a technical one** (CLAUDE.md) — the
   chunking decision belongs to Auto Scan, not to a "fix" inside `ltt_voice`;
3. `temperature`/`top_k`/`top_p` are deliberately outside `ltt_voice`'s public contract
   because its CUDA-graph cache keys on them — do not attempt to pass them;
4. this is the second paid stage, so I5 applies again; TTS is billed per character, which
   makes measured settlement (ADR-001 D4) matter more than anywhere so far.
