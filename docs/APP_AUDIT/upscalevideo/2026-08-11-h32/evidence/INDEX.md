# H32.6 — Evidence index

| Evidence | Nội dung | Verdict |
|---|---|---|
| `baseline-desktop.png` | UI trước sửa 1586×992 | E3 |
| `baseline-mobile.png` | UI trước sửa 390×844 | E3 |
| `final-desktop-en.png` | UI cuối EN desktop | PASS E3 |
| `final-mobile-open-en.png` | Settings mobile mở | PASS E3 |
| `runtime/matrix-summary.json` | 17 option/runtime case GPU 1 | 17/17 PASS E4-machine |
| `runtime/*.json` | Probe output + GPU telemetry từng case | PASS E4-machine |
| `dual-gpu-soak.json` | Full source trên hai worker | PARTIAL: GPU1 pass, GPU0 safety refusal |
| `h26-soak-gpu1.json` | Full 15,069s source, GPU1 | PASS E4-machine |
| `qualitylab-fast-vs-lanczos.json` | Contract + diagnostic quality | Contract PASS; quality UNKNOWN |
| `tests/browser/upscale_h32_probe.js` | Repro actual upload/control probe | PASS E3 |
| `tests/browser/upscale_h32_batch.js` | Repro batch/hold/queue probe | PASS E3 |

Không chứa secret, đường dẫn dữ liệu người dùng hoặc MP4 output. Candidate lớn
giữ ngoài git trong `tmp/`; JSON nhận diện artifact bằng hash.
