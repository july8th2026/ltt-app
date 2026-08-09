# A4 — Competitor Benchmark

Snapshot 2026-08-09; official docs/hands-on được ưu tiên. PlenX dùng hồ sơ
`docs/KHAO_SAT_PLENX_AGENT.md` như evidence lịch sử, không suy ra backend.

| Capability/JTBD | LTT | FLORA | ComfyUI | n8n/Make | Class |
|---|---:|---:|---:|---:|---|
| Text/image/video/audio block trực quan | 1 | 3 | 2 | 1 | TABLE_STAKES |
| Manual input và AI generation trong cùng modality | 1 | 3 | 2 | 2 | TABLE_STAKES |
| Kết nối type-safe/quick create | 2 | 3 | 3 | 3 | TABLE_STAKES |
| Run selection/partial | 2 | 3 | 3 | 3 | TABLE_STAKES |
| Workflow library/templates/switch | 0 | 3 | 3 | 3 | TABLE_STAKES |
| History/debug/retry từ execution | 1 | 2 | 3 | 3 | TABLE_STAKES |
| Customer mode ẩn graph complexity | 0 | 2 | 3 (APP mode) | 1 | DIFFERENTIATOR |
| Mobile customer runner | 0 | 2 | 3 (APP mode) | 1 | TABLE_STAKES |
| AI xây/sửa graph có preview | 2 | 3 (FAUNA) | 2 | 2 | DIFFERENTIATOR |
| Quote/hold/settle credit trước run | 2 | UNKNOWN | UNKNOWN | UNKNOWN | DIFFERENTIATOR LTT |
| Error branch/recovery | 1 | UNKNOWN | 2 | 3 | TABLE_STAKES |
| Asset/project lifecycle | 1 | 3 | 3 | 2 | TABLE_STAKES |

Nguồn:

- FLORA Canvas: <https://docs.flora.ai/editor/canvas>; Text→Text:
  <https://docs.flora.ai/nodes/text-node/text-to-text>; FAUNA:
  <https://docs.flora.ai/editor/fauna>.
- ComfyUI overview: <https://docs.comfy.org/interface/overview>; APP mode:
  <https://docs.comfy.org/interface/app-mode>.
- n8n executions: <https://docs.n8n.io/workflows/executions/all-executions/>.
- Make error handling: <https://help.make.com/overview-of-error-handling>.

## Gap/decision

- **KEEP:** ToolSpec discovery, typed connection, immutable scoped plan,
  quote/hold/settle, snapshot, owner isolation.
- **FIX:** manual-vs-generate semantics, duplicate orchestration, cancel tree,
  locale, error remediation, asset lifecycle.
- **RESTYLE:** compact customer block, progressive disclosure, plain-language
  run inspector, mobile runner.
- **BUILD:** workflow/project library, reusable starter templates, customer APP
  mode, asset/results panel.
- **DEFER:** layer editor, 50+ models, arbitrary third-party node SDK.
- **REJECT:** phơi schema/tool ID/retry/fan-out mặc định hoặc sao chép nhận diện
  FLORA/PlenX.

M 38: nền executor có điểm khác biệt về credit/type-safety, nhưng app thiếu nhiều
table stakes ở workflow management, customer mode, recovery và modality semantics.
