# LTT-CMC completed-history reconciliation

## Frozen scope and method

- Inventory snapshot: `770c83c0b8708ffc124ef5ba4b82fc4e51f12f01913b8ca73106857a2fa9337a`.
- Canonical snapshot head: `df36c1c264478fd7af928adc45bb297239d8a3a7`.
- Machine-readable matrix: `docs/LTT_CMC/reconciliation.json`.
- Every comparison used the SHA captured in the snapshot, not a live branch
  name; several live refs moved after the freeze.
- Evidence commands: `merge-base --is-ancestor`, `rev-list --left-right`,
  `git cherry`, `diff --name-status`, commit subjects and direct source review.

No commit was cherry-picked and no rescue ref was required. Every reflog-only
object was either patch-equivalent, an amended/superseded intermediate,
history-only, or owned by the deferred Voice workstream.

## Branch dispositions

| Disposition | Branches | Evidence |
|---|---|---|
| `ALREADY_CANONICAL` | `admin-mvp-v3`; `architecture/scheduler-priority-v1`; `claude/auto-scan-video-analysis-plan-752af9`; `claude/chatltt-v3-agentic`; `claude/cool-pike-8be595`; `claude/ltt-vps-v2-deployment-plan-2cfc36`; `main`; `master`; `phien/aiclean`; `phien/asv`; `phien/asv-v4`; `phien/asv-v6`; `phien/asv-v6-pha27`; `phien/mobile-v1`; `phien/wf2` | Each pinned tip is an ancestor of the frozen canonical head or equals the source/canonical tip; `git cherry` reports zero unique commits. |
| `PATCH_EQUIVALENT` | `h42-release-clean` | `git cherry` reports two `-` commits and zero `+` commits. |
| `SUPERSEDED` | `claude/ltt-video-ai-v3-p00-3f5713` | Tip `989353c2` explicitly stops V3 development; live direction is V2.1 WanGP. |
| `SUPERSEDED` | `phien/video-v2-wangp` | Its gallery commit opens two VACE tasks from stale weight evidence. Canonical deliberately keeps them closed until a live pod refresh proves weights and availability; opening them now could accept credit for a locked path. |
| `DEFER_VOICE` | `claude/history-audio-storage-auth-4cffe3`; `claude/ltt-4bot-workflow-app-550cab`; all `claude/ltt-voice-*`; `claude/my-voices-enrollment-prod-379a22`; `claude/projects-longform-slice-ab2e77`; `claude/studio-voice-picker-ui-6782bb`; `claude/voice-language-compatibility-440bfd` | Names and/or changed paths belong to the protected Voice reconciliation workstream. Ancestral status does not override ownership. |
| `DEFER_LLM` | `claude/ltt-llm-master-upgrade-ddcfc9`; `claude/ltt-llm-multijob-audit-43efd3`; `claude/ltt-llm-recovery-multimodel-110f65`; `claude/ltt-video-architecture-recovery-746b24`; `phien/ltt-llm-dual` | Protected LLM dual-model/multijob workstream. The video-architecture name is mapped by the user's authoritative session identification. |

The machine report contains all 36 branch names and their pinned heads; the
test compares that set directly with the inventory so this summary cannot hide
an omitted branch.

## Reflog-only dispositions

| Disposition | Commits | Evidence |
|---|---|---|
| `PATCH_EQUIVALENT` | `0972288d`; `2bd046e6`; `3c59a982`; `42c6718e`; `46e05467`; `4c9910d5`; `565bc428`; `6781ab61`; `89078c6d`; `9ca72b1c`; `ba904eff`; `e8544dbe` | `git cherry <frozen-main> <sha>` reports `-`. |
| `SUPERSEDED` | `08a73629`; `6514ac27`; `871ff6ad` | Partial H7/cosmic-ray variants; completed canonical result is `278a5dd1`. |
| `SUPERSEDED` | `0ecb5bf7`; `54f5f38a`; `ef776aa8` | Scheduler V1 commit/rebase/amend intermediates; canonical `0fad25e1` is integrated, and scheduler source/tests match. |
| `SUPERSEDED` | `755173e5`; `87d15e08` | Early ASV plan/acceptance variants replaced by the completed ASV lineage (`dabeb2c2` for the latter rewrite). |
| `DEFER_VOICE` | `3119d280`; `36abf631`; `e475edcb` | Voice history registry/lifecycle implementation. |
| `ARCHIVE_HISTORY_ONLY` | `564a90a2`; `aba8749e` | Integration/deployment journal markers with no independent live authority. |

## Families explicitly reviewed

- Scheduler: canonical `0fad25e1`; three reflog amend intermediates superseded.
- ASV/aiclean/wf2/mobile/VPS: pinned tips already ancestral; no replay.
- H42 release: patch-equivalent; no replay.
- Video AI V3: explicitly stopped in favor of V2.1.
- Video V2 WanGP: later gallery branch is unsafe to open without current pod
  evidence; retained in Git history, not ported.
- Projects/longform: all unique files are Voice-owned, so deferred intact.

## Rescue refs

`RECONCILE` reflog commits selected: **0**. Therefore no
`refs/cmc-rescue/*` refs were created. This is intentional: creating refs for
superseded/equivalent objects would manufacture long-lived duplicates.
