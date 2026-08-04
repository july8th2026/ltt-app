# Evidence Baseline — 2026-08-04

## Browser local

- 1366×768: overflow 0, 5 node, 1 edge, 0 alert.
- 1720×940: context menu, quick-create compatible, `@node`, scoped quote/run.
- 1920×1080: overflow 0, 5 node, 1 edge.
- 390×844: overflow X/Y 0, node width 280, 1 edge, read-only CTA, Canvas/Công
  cụ/Inspector panels hoạt động.
- Console: 0 error, 0 warning.
- Fresh network baseline: palette/workflows/preferences/runs/quotes đều HTTP 200.
- Scoped run: `awaiting_approval`, quote 10 credit, actual 0; không approve.

## Automated

- `npm test -- --run`: 27 passed.
- `npm run build`: typecheck pass; Vite bundle pass.
- Targeted pytest: 22 passed, 1 deprecation warning.
- Full pytest bundle cuối: 2.063 passed, 8 skipped, 23 subtests passed,
  1 warning, 649.97 giây.
- `npm audit --audit-level=high`: 0 vulnerability.
- `python tools\lint_app_contract.py`: 12 app, 0 ERROR, 0 WARN.
- `python tools\scan_source_secrets.py`: 1.493 file, 196.292 dòng, 0 finding.
