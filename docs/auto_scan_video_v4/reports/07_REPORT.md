# Phase 07 — ASR and diarization capability rebase

**Verdict: PASS.**
Source SHA at start `e7f8c12`. Branch `phien/asv-v4`.

---

## 1. Half the objective was already met — and saying so is the finding

The brief says *"move ASV from AutoSub implementation reach-through to a stable
owner-app ASR boundary"*. For **ASR that migration had already happened**:

- `autosubvideo.BE_MAT_CONG_KHAI` already declared `transcription.transcribe_file`
- ASV already called exactly that name, and nothing else
- `transcribe_file` already accepts everything the brief asks a boundary to
  support: file input, `language`, `on_progress`, `is_cancelled`, `gpu_uuid`,
  structured output with timestamps
- `giai_doan_chep_loi.chep_loi` already forwards the **platform-assigned** card
  from `JobContext`, never choosing one

⇒ "Remove ASV dependency on private AutoSub implementation path" has **nothing to
remove**. An AST test now proves that positively: every `from apps.autosubvideo…`
import in the whole ASV app resolves to a declared name.

The real gap was **diarization**, exactly as `STATE_V4` recorded it in Phase 02
(V4-R13).

## 2. 🔴 The extension surfaced a live defect that predates Auto Scan

Exporting `diarize_file` meant reading it. `apps/autosubvideo/pyannote_runner.py:20`:

```python
if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))
```

It takes **the first card torch can see**, with no reference to
`platform_core.gpu_lease`. The platform assigns a card; this process ignores the
assignment. Two concurrent jobs therefore either collide on one card or leave one
idle while the other OOMs — and `autosubvideo/manifest.py:51` declares
`gpu_vram_mb={"autosubvideo.diarize": 2000}`, so the platform *believes* it is
arbitrating something it is not.

⭐ Fixed by **reusing the owner's own mechanism**, not adding a second one:
`diarize_file(..., gpu_uuid="")` now passes `env=_env_ghim_gpu(gpu_uuid)` to the
subprocess — the identical helper `transcribe_file` has used all along
(→ `platform_core.gpu.env_for`). The brief forbids new GPU arbitration; this adds
none. It only makes an existing lease **honoured**.

⚠️ Default `""` preserves every current `autosubvideo` caller byte-for-byte. A
test pins the default, because removing it would break the owner app — and an app
breaking *its owner* is the exact failure `BE_MAT_CONG_KHAI` exists to prevent.

## 3. Diarization is conditional, and the default is *off*

`giai_doan_chep_loi.can_phan_vai(run)` returns True only for
`hop_dong_v4.CHE_DO_GIONG_TU_KHOP` (`AUTO_MATCH`).

- `AUTO_MATCH` must read real speaker characteristics — without evidence it
  degrades into "use the default voice", which `ADR-V4-001` D-V4-04 forbids by name
- `USER_SELECTED` needs none, and running it there is paying GPU credit for a
  result nobody reads — the brief's *"do not pay GPU cost blindly"*

⚠️ Missing / unknown / malformed settings ⇒ **do not run**. A GPU-consuming
capability must be asked for, never assumed. Fail-closed toward *not spending*.

## 4. Transcript schema: what was **not** done, and why

The brief says ASV stores canonical transcript schema/version. It already does
(`ban_ghi.SCHEMA_BAN_GHI = 1`).

⛔ **The version was deliberately not bumped.** `ban_ghi.kiem` compares with
**equality** (`!= SCHEMA_BAN_GHI` raises), so bumping to 2 invalidates every
stored transcript — every in-flight run loses its cache and re-transcribes, and
the customer pays for a second ASR pass caused by a change they never saw.

Instead the speaker fields are **additive and optional**, plus one explicit
document-level field with three values:

| `phan_vai` | meaning |
|---|---|
| `khong_chay` | not requested (or legacy record) |
| `da_chay` | ran; per-segment `nguoi_noi` present where overlap existed |
| `khong_kha_dung` | requested, but pyannote/token/sidecar unavailable |

🔑 Three explicit values rather than "field present or absent", because Phase 09
must distinguish **no evidence** from **evidence that found nobody** — those lead
to two different AUTO_MATCH decisions. And absence on legacy records is not a
guess: those were written before the capability existed, so `khong_chay` is a fact
about them.

## 5. A supporting capability failing must not fail the run — except on cancel

`phan_vai` catches diarization failure, marks `khong_kha_dung`, and continues. A
dub missing speaker labels is still a dub; a failed run is not.

⛔ **Cancellation is re-raised, not swallowed.** Cancel is the user's intent, not
a missing capability. Swallowing it would let the chain continue *after the
customer pressed stop* — and they would pay for every stage after that.

## 6. Two bugs the merge and the ratchets caught

### 🔴 Two alembic heads

The trunk merge brought `chatltt`'s migration; both it and the ASV chain branch
from `c7b91e4a2f80`. `test_103::test_platform_migrations_have_a_single_head` went
red — alembic could not know which to run first.

Relinked the **ASV** chain (`e1a7c04b93d2.down_revision` → `7d2c1e9f4a03`), not
theirs: the merging side rebases, and editing their link would disturb sessions
building on it. ⚠️ Safe only because ASV has never run in production
(`enabled=False`, and `C:\LTTPlatform\app` contains no `auto_scan_video`); had it
run, this would need `alembic merge` instead.

### ⭐ A Phase 02 test that failed *forward*

`test_426::test_diarization_ton_tai_o_chu_cua_no` pinned the **opposite** state —
that the two names were *not* exported — and its failure message carried the
instruction:

> "diarization đã được mở — cập nhật CAPABILITY_INVENTORY_V4.md từ
> EXTEND_OWNER_CONTRACT sang SUFFICIENT"

Phase 07 did exactly that, and the test is what made me. A test pinning a
**temporary** state must say what to do when the state stops being temporary —
otherwise it is just a roadblock. Rewritten to pin both directions: the names are
declared, **and** the inventory says `SUFFICIENT`.

## 7. Tests and evidence

`tests/test_433_asv_v4_ranh_gioi_asr.py` — **18 tests**, five sections: boundary
is declared and enforced both ways · card comes from the platform · diarization is
conditional · supporting-capability failure vs cancellation · parity of transcript
shape. **No test loads a real model**; both boundaries are injected.

**Layer 4 — seven mutations, seven reds:**

| Mutation | Caught by |
|---|---|
| run diarization always (blind GPU spend) | `test_chi_AUTO_MATCH_moi_can_bang_chung_nguoi_noi` |
| stop forwarding the assigned card | `test_phan_vai_CHUYEN_TIEP_card_cua_JobContext` |
| swallow cancel as "unavailable" | `test_HUY_thi_NEM_LEN_chu_khong_nuot...` |
| drop the GPU env pin in the owner app | `test_diarize_file_GHIM_moi_truong...` |
| remove `gpu_uuid`'s default (breaks owner) | `test_them_chu_khong_SUA_hop_dong...` |
| bump `SCHEMA_BAN_GHI` to 2 | `test_KHONG_nang_SCHEMA_BAN_GHI` |
| reimplement overlap inside ASV | `test_thuat_toan_chong_lan_o_lai_app_CHU` |

Layer 2: `test_400 401 407 417 421 425–433` + `test_81_autosubvideo` +
`test_85_app_contract_lint` + `test_103` → all green. `lint_app_contract`: 20 apps,
0 ERROR, 0 WARN.

## 8. Debt carried forward

⚠️ Parity against a **real** ASR run is not measured here and cannot be: the dev
interpreter is `torch+cpu` while production is `cu128` (V4-R05, still open). What
is proven is that the *boundary* and the *transcript shape* are unchanged —
`test_gan_nguoi_noi_KHONG_doi_bat_ky_truong_nao_khac` compares field by field.

⚠️ Nothing calls `phan_vai` with a real pyannote yet; Phase 09 is the first
consumer of the evidence it produces.

## 9. Exit gate

**PASS.** ASV depends on a declared, enforced speech capability for both ASR and
diarization; transcript shape and schema version are preserved; the assigned GPU
is honoured on both paths; and diarization costs nothing unless the run actually
needs speaker evidence.
