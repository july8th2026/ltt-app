# Evidence register — Auto Sub Studio 2026-08-09

| ID | Evidence |
|---|---|
| EV-SRC-001 | `apps/autosubvideo/manifest.py` |
| EV-SRC-002 | `frontend/autosub-studio/src/StudioShell.tsx`, `EditorTimeline.tsx`, `studioApi.ts`, `useProjectHistory.ts` |
| EV-SRC-003 | `platform_core/app_projects.py` |
| EV-SRC-004 | `apps/autosubvideo/routes.py` upload/source/legacy queue |
| EV-SRC-005 | `apps/autosubvideo/schemas.py`, `parsers.py`, `TranscriptQuality.tsx` |
| EV-SRC-006 | `transcription.py`, `ai_workflows.py`, auxiliary routes/jobs |
| EV-SRC-007 | `StyleInspector.tsx`, `Waveform.tsx`, `ass_builder.py`, `style_registry.py` |
| EV-SRC-008 | `project_render.py`, `burn.py`, `cost.py`, render route/jobs |
| EV-SRC-009 | studio job/project routes and job polling in `StudioShell.tsx` |
| EV-SRC-010 | `/v` and `/f` routes plus storage contract |
| EV-BR-001 | Empty desktop snapshot in Playwright session `ltt` |
| EV-BR-002 | `desktop-imported.yml/png`; real video attach and full-file waveform GET |
| EV-BR-003 | Browser import SRT: 3 cue, QA 100, no console error |
| EV-BR-004 | `quote-4k-invalid-cues.png`; 4K still 1 credit while QA=70 |
| EV-BR-005 | `mobile-390.png`; horizontal timeline/cue clipping |
| EV-BR-006 | `english-route-vietnamese-ui.png`; `/en/` remains Vietnamese |
| EV-TEST-001 | 36 Python PASS with 2 unhandled-thread warnings; 13 Vitest PASS |
| EV-MKT-001 | Official sources listed in `03_COMPETITOR_BENCHMARK.md` |

Browser test did not confirm render or spend credit. Fixture/storage/database were
isolated from production.
