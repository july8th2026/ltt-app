# Cost & Safety V2.1

## Before paid compute
- inventory all current RunPod resources;
- verify current balance/spend;
- fetch current GPU availability/rate;
- estimate worst-case phase cost;
- record cleanup action and max runtime;
- record resource ID immediately after creation.

## During
- no unrelated model downloads;
- no paid resource left alive due to logging/report errors;
- manual start/stop is acceptable in P01/P02;
- automated lifecycle is not assumed until P08.

## Security
- no WanGP `--share`;
- no unauthenticated raw WebUI/MCP port;
- no R2 master key on C-CLOUD;
- no LTT DB/session secrets on C-CLOUD;
- signed/scoped media transfer;
- WanGP WebUI admin/operator only.
