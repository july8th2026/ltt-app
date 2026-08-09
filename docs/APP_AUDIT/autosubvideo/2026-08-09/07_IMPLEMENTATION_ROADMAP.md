# 07 — Implementation Roadmap: Auto Sub Studio

Đây là output audit, **chưa triển khai**. Mỗi phase tuần tự; phase sau chỉ mở khi
phase trước có evidence PASS và rollback đã diễn tập.

| Phase | Scope | Acceptance/PASS gate | Test/evidence | Rollback | Status |
|---|---|---|---|---|---|
| 0A Upload/source contract | F-001/F-004/F-016: CSRF, session, stream, hash/type/probe, TTL/promote | Forged/corrupt/abandon không attach/orphan; G2/G5 partial PASS | Media corpus, CSRF, race, sweeper dry-run | Tắt direct upload; local cap thấp | Chưa làm |
| 0B Admission/canonical quote | F-002/F-006/F-007: workload matrix, duration cap, signed quote | Tamper metadata vô hiệu; quote=hold; >limit trước job; G3/G7 partial PASS | Boundary/property/load/calibration | Pin conservative caps/rates | Chưa làm |
| 0C Durable project recovery | F-003/F-010/F-011: outbox, dirty state, merge/copy, project picker | Offline/reload/two-tab/AI conflict không mất edit/result | Playwright network offline + conflict fixtures | Local export draft; read-only recovery | Chưa làm |
| 0D Honest output gate | F-005/F-008/F-013: fatal QA, intent labels, preview parity | Fatal cue không quote; engine/capability thật; core style frame diff PASS | Cue property tests + golden frames | Basic preset/no animation fallback | Chưa làm |
| 0E Peaks/performance | F-009/F-018/F-021: server peaks, diff history, cache | Không full source GET cho waveform; 120m memory budget PASS | Network/performance trace, 10k cue | Hide waveform, list editor remains | Chưa làm |
| 1A i18n/mobile/a11y | F-012/F-017/F-020 | VI+EN A-Z; 390/768/1440; keyboard timing/zoom/fit | Playwright + axe + keyboard | Desktop basic editor fallback | Chưa làm |
| 1B Artifact delivery | F-014/F-015: staging/promote/cleanup, MIME/name/range | Terminal atomic; delete/retention; R2/local same semantics | Fault injection + R2 staging | Proxy local/signed fallback | Chưa làm |
| 1C Job/ops hardening | F-006/F-019/F-022 | Weighted quotas, SLO, no warning thread, honest release state | Load/worker/process-tree/gate | Disable AI auxiliary per capability | Chưa làm |
| 2A Customer project parity | New/open/duplicate/archive/delete/search; cursor history | >100 project/job tìm đúng; restore/delete policy rõ | Large fixture/browser | Feature flag project manager | Chưa làm |
| 2B Timeline parity chọn lọc | Zoom/fit/snap/nudge/frame-step/per-track style/brand kit | Beginner test không tăng cognitive load; precision task PASS | Moderated usability + keyboard | Basic timeline mode | Chưa làm |
| 3 Quality benchmark | Golden VI/EN/noise/speaker/style corpus | WER/timing/speaker/render ≥ baseline; U-01/U-02 đóng | Human review + blind frame/audio metrics | Pin model/preset tốt nhất | Chưa làm |
| 4 Production canary | Metrics theo workload/device/provider | ≥20 terminal; success≥95%; queue P95≤30s; orphan/lost draft=0 | 7–30 ngày canary | Feature flag/queue cap | Chưa làm |
| 5 Release/re-audit | Full gate + A-Z auth production + LTT-AQA rerun | 0 P0/P1; G0–G8 PASS; Q≥80/M≥75/E≥85 | `tools/gate.py`, Playwright, rollback rehearsal | Build trước + DB/storage manifest | Chưa làm |

## Metric baseline/target

| Metric | Baseline | Target |
|---|---|---|
| Quality Score | 56 | ≥80 |
| Market Score | 65 | ≥75 |
| Upload orphan | Có đường tạo, chưa đo | 0 quá TTL |
| Quote 4K/source 10s | Cùng 1 credit | Canonical theo workload |
| Invalid cue render | Dialog vẫn mở | Fatal error chặn 100% |
| Offline/conflict recovery | Message-only | 100% draft recoverable |
| Waveform transfer | GET toàn source | Peak artifact nhỏ, cacheable |
| EN core journey | FAIL | 100% không lẫn VI |
| Mobile 390 timeline | Cắt ngang | Fit/scroll/zoom có chủ đích, task PASS |
| Project/job history >100 | Có thể mất khỏi view | Cursor/search chính xác |
| Test warnings | 2 unhandled media thread | 0 |
| Production success/P95 | UNKNOWN | ≥95%; queue P95≤30s |

