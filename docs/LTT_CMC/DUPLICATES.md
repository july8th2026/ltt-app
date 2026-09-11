# LTT-CMC duplicate dispositions

- Frozen inventory snapshot: `770c83c0b8708ffc124ef5ba4b82fc4e51f12f01913b8ca73106857a2fa9337a`
- Classification rule: exact bytes alone do not justify deletion; ownership and lifecycle decide the disposition.
- Machine-readable evidence: `docs/LTT_CMC/duplicates.json`

## Removed stale source

`.merge_tam/goc.py` and `.merge_tam/ho.py` were tracked merge-resolution
variants of `tools/lint_app_contract.py`. They had no runtime consumer or
independent ownership, so CMC removed both instead of preserving parallel
Python authorities.

## Retained exact duplicates

| Identity | Paths | Disposition | Lifecycle evidence |
|---|---|---|---|
| `frontend_tsconfig` | `frontend/agent-canvas/tsconfig.app.json`; `frontend/autosub-studio/tsconfig.app.json`; `frontend/chatltt/tsconfig.app.json`; `frontend/prompt-ai-ommi/tsconfig.app.json` | `INTENTIONAL_DUPLICATE` | Per-app compiler templates; each frontend owns its local config. |
| `shared_ltt_css` | `server/static/ltt.css`; `tools/gui/ltt.css` | `INTENTIONAL_DUPLICATE` | `tools/dong_goi_gui.py` derives the WebView copy atomically from the server source. |
| `g9_prompt_alias` | `bench/G9_ben_100.json`; `bench/G9_prompts.json` | `INTENTIONAL_DUPLICATE` | The runner consumes `G9_prompts.json`; dated benchmark evidence retains the `G9_ben_100` name. |
| `comfyui_inventory_history` | `docs/VIDEO_AI_V2/khoi_phuc/BANG_KE_COMFYUI_V3.json`; `docs/_luutru/VIDEO_AI_V3/BANG_KE_MONG_DOI.json` | `INTENTIONAL_DUPLICATE` | The archived V3 copy is recovery/history evidence and is not a runtime authority. |

All four groups were byte-identical at this snapshot. The regression test
recomputes SHA-256 from the tracked files, so a later lifecycle divergence must
be classified explicitly instead of silently inheriting this disposition.
