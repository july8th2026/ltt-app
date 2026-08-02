# 02 — Journey & Control Registry

## Journey/state matrix

| ID | Persona/JTBD | State | Kỳ vọng | Kết quả thật | Evidence | Verdict |
|---|---|---|---|---|---|---|

State tối thiểu khi phù hợp: happy, empty, invalid, setup error, insufficient
credit, queued, running, done, failed, cancelled, retry, timeout, offline,
conflict, upload lỗi/lớn và artifact missing.

## Control Registry

| ID | Screen/control | Visible/enabled rule | Role | Action/API | Credit | Loading/success/error | Cancel/retry/undo | Keyboard/mobile | Telemetry | Evidence | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|

Verdict: `LIVE`, `PARTIAL`, `BROKEN`, `DEAD`, `MISLEADING`, `REDUNDANT`, `MISSING`.

## Browser matrix

| Viewport/state | Console | Failed requests | Overflow | Keyboard/focus | Screenshot/evidence | PASS |
|---|---|---|---|---|---|---|
