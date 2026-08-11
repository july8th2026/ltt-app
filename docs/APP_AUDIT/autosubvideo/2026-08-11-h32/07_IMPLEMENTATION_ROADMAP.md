# H32.1 — Kế hoạch đóng tồn đọng

Thực hiện tuần tự; không mở phase sau nếu acceptance phase trước chưa PASS.

| Phase | Scope | Acceptance | Test bắt buộc | Trạng thái |
|---|---|---|---|---|
| AS-H32.1A | Rename manifest/nav/title | Chrome title + heading đều AutoSub Video; targeted tests xanh | Browser 1440/390; 36 pytest + 13 Vitest | **DONE** |
| AS-H32.1B | AI staging gate | ASR/diarize/translate chạy corpus VI/EN; WER/timing/DER, quota, cancel/refund có số đo | Golden audio + provider-off/failure | Chờ model/key staging |
| AS-H32.1C | Security + quote negative gate | forged/corrupt/oversize/orphan fail sớm; quote=hold=settlement theo workload | Media corpus, tamper, sweeper, boundary/property | Chưa làm |
| AS-H32.1D | Filename + artifact UX | Tên deterministic; MIME/attachment đúng; SRT/VTT/JSON/ASS/ZIP rõ ràng | Local/R2 download matrix | Chưa làm |
| AS-H32.1E | i18n + customer wording | VI/EN A-Z không lẫn; engine detail ẩn sau Help | Locale Playwright + snapshot | Chưa làm |
| AS-H32.1F | Mobile precision | 390/768 task upload→edit→export không mất control; fit/zoom có chủ đích | Touch/keyboard/axe/browser | Chưa làm |
| AS-H32.1G | Subtitle Pro controls | Width/max-lines/alignment/line-height/bg box/safe-area/drag/brand/speaker style | Schema migration + preview/render golden | Chưa làm |
| AS-H32.1H | Animation/render parity | 9 preset representative matrix; preview và output đạt frame threshold | Golden frame diff | Chưa làm |
| AS-H32.1I | Test/ops cleanup | 0 unhandled thread warning; API không 302 locale; long-video budget | Warning-as-error + network/perf | Chưa làm |
| AS-H32.1J | Re-audit/release | 0 P0/P1; G0–G8 pass; Q≥80, E≥90 | `python tools/gate.py` + browser A-Z | Chưa làm |

## Rollback

- Rename: revert hai label trong manifest.
- Mỗi nhóm UI/advanced control phải feature-flag độc lập; giữ Basic mode.
- Provider/model fail: capability-off trung thực, import transcript + render vẫn dùng được.
- Render parity fail: pin preset/animation cũ; không migrate project phá hủy.
