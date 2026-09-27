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

> 🔴 **`duplicates.json` IS HAND-MAINTAINED — there is NO generator for it.**
> `tools/cmc_inventory.py` regenerates `inventory.json` (Git topology) only; ⛔ it
> does **not** touch `duplicates.json`. So every `sha256` in that file is a number
> a human typed, and it **goes stale the moment either copy changes**.
>
> ⚠️ It already did, 25/09: `c5f331fa` + `526967e4` changed `ltt.css` and synced
> the copy **correctly**, but the declaration stayed on the old hash — `test_975`
> caught it. Same shape as `N-24`: *the feature shipped, the declaration stayed
> behind.*
>
> ⭐ **When `test_975` goes red, ⛔ do NOT just paste the new hash in.** Ask first:
> ***„are the copies still byte-identical to each other?“***
> * **yes** ⇒ updating the declaration is correct maintenance;
> * **no** ⇒ ⛔ editing the hash **hides a real regression** — the copies have
>   drifted and one of them is wrong. Fix the drift, not the number.
>
> ⚠️ **It went stale again, 27/09** — and this time the change came from **our own** app: `5d68da91` and `9d6d8d31` (asv-gui) edited `server/static/ltt.css`, and `19e25c55` re-synced `tools/gui/ltt.css` to it. Verified before touching the number: both copies re-hash to the **same** value (`0f0a5902…c17971`), so the duplicate property still holds and updating the declaration is the correct branch of the procedure above. `snapshot_id` is left alone, exactly as `7af34e4e` did.
>
> ⭐ Twice in three days means the procedure works but the **cadence** does not: a hand-typed hash guarding a file two apps edit will keep going stale. The durable fix is a generator for this group, not a faster human.
>
> `test_975` re-hashes every path itself, so it also asserts the copies match each
> other — that is the part that must never be „fixed“ by editing this declaration.

| Identity | Paths | Disposition | Lifecycle evidence |
|---|---|---|---|
| `frontend_tsconfig` | `frontend/agent-canvas/tsconfig.app.json`; `frontend/autosub-studio/tsconfig.app.json`; `frontend/chatltt/tsconfig.app.json`; `frontend/prompt-ai-ommi/tsconfig.app.json` | `INTENTIONAL_DUPLICATE` | Per-app compiler templates; each frontend owns its local config. |
| `shared_ltt_css` | `server/static/ltt.css`; `tools/gui/ltt.css` | `INTENTIONAL_DUPLICATE` | `tools/dong_goi_gui.py` derives the WebView copy atomically from the server source. |
| `g9_prompt_alias` | `bench/G9_ben_100.json`; `bench/G9_prompts.json` | `INTENTIONAL_DUPLICATE` | The runner consumes `G9_prompts.json`; dated benchmark evidence retains the `G9_ben_100` name. |
| `comfyui_inventory_history` | `docs/VIDEO_AI_V2/khoi_phuc/BANG_KE_COMFYUI_V3.json`; `docs/_luutru/VIDEO_AI_V3/BANG_KE_MONG_DOI.json` | `INTENTIONAL_DUPLICATE` | The archived V3 copy is recovery/history evidence and is not a runtime authority. |

All four groups were byte-identical at this snapshot. The regression test
recomputes SHA-256 from the tracked files, so a later lifecycle divergence must
be classified explicitly instead of silently inheriting this disposition.
