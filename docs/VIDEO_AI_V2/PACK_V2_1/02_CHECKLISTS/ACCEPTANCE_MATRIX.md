# P02 WanGP Engine Acceptance Matrix

This matrix tests the **engine**, not the not-yet-built LTT integration.

| Capability | Required | Evidence |
|---|---:|---|
| pinned vanilla boot | yes | |
| private operator WebUI | yes | |
| Python API and/or MCP usable | yes | |
| model discovery/schema | yes | |
| T2V | yes | |
| I2V | yes | |
| subject/reference | yes | |
| motion/control | yes | |
| character animation | yes | |
| video edit | if V2 MVP | |
| progress primitive | yes | |
| cancel primitive | yes | |
| timeout/abort behavior understood | yes | |
| native media ingest path | yes | |
| native output retrieval path | yes | |
| restart + model persistence | yes | |
| Deepy available | yes | |
| baseline settings captured | yes | |

NOT required at P02:
- LTT R2 roundtrip;
- LTT user ownership;
- automated cloud lifecycle;
- final cost telemetry system;
- final max-quality benchmark.

Those are later phases.

## Baseline profile output
Every mandatory generation task that passes should record a reproducible
`baseline profile` (model/settings/input roles), even if it is not yet the final quality winner.
