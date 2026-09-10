# Legacy Delete Policy V2.1

## Deletion prerequisite

All must be true:
- P02 WanGP engine acceptance PASS;
- P03 restore tag/branch verified;
- P04 LTT WanGP-only code path exists;
- P05 REAL LTT↔WanGP integration PASS;
- R2 output PASS;
- cancel PASS;
- ownership PASS;
- no replacement runtime fallback to legacy.

Only then P06 deletes legacy runtime.

## Classification
- KEEP_GENERIC
- REUSE_CONCEPT
- DELETE_AT_P06
- ARCHIVE_DOC_ONLY

## Candidate areas to audit
- legacy `apps/lttvideo`
- `platform_core/video_gen`
- `video_gateway`
- `lttvideo-worker` integration
- legacy serverless controller/provider
- old ComfyUI video workflows/config
- implementation-specific `tools/video_*`
- implementation-specific tests/docs

## Preserve if generic/used elsewhere
- storage abstraction
- job infrastructure
- credit ledger
- provider telemetry
- generic RunPod utilities
- Git history/tag

## Restore point
Create and verify:
`video-legacy-final-pre-wangp`

## Post-delete proof
Search for old runtime symbols/IDs.
Target: zero executable/runtime references.
Historical ADR/docs may retain names when clearly marked historical.
