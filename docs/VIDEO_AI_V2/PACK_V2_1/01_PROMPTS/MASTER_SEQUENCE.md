# MASTER SEQUENCE V2.1

```text
P00 Recover + Audit Legacy
  ↓
P01 Vanilla WanGP C-CLOUD POC
  ↓
P02 WanGP Engine Acceptance + Baseline Profiles
  ↓
P03 Lock One Engine + Contract + Restore Point
  ↓
P04 Build Clean LTT Video App + WanGP Client
  ↓
P05 REAL LTT↔WanGP + R2 + Cancel
  ↓
P06 CUTOVER + DELETE Legacy Runtime
  ↓
P07 Quality Router + Deepy
  ↓
P08 Automated Cloud Lifecycle + Cost Guard
  ↓
P09 True Internal E2E + Final Handoff
```

## Vì sao delete ở P06, không phải P04
Engine-level WanGP PASS chưa chứng minh:
- LTT auth;
- user ownership;
- R2;
- cancel propagation;
- normalized job result.

P05 chứng minh replacement tại boundary thật. P06 mới delete.

## Chat policy
Một phase = một chat mới là cấu hình khuyến nghị.
State file + git là bộ nhớ giữa các phase.
