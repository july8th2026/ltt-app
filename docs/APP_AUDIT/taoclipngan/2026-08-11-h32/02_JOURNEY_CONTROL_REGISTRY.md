# H32.4 — Journey và control registry

| Control/luồng | Logic thật | Evidence | Trạng thái |
|---|---|---|---|
| Upload local | cap 90 MiB, đọc tối đa cap+1 | pytest | PASS |
| Upload direct | CSRF, extension, declared 1 GiB, one-time ticket | E3 + upload 523,9 MB trước hardening | CONDITIONAL |
| Source library | owner prefix + storage existence, tối đa 8 | E3 reuse | PASS sampled |
| Tier Fast | Whisper base + pipeline + render | 3 job thật | PASS |
| Tier Balanced/Best | config/cost/controls | source + pytest | UNTESTED E4 |
| Ratio 9:16 | 1080×1920 | output thật | PASS |
| Ratio 4:5 | 1080×1350, SAR 1:1 | output thật sau sửa | PASS |
| Ratio 1:1/16:9 | 1080×1080 / 1920×1080 | regression test | CONDITIONAL |
| Count 1 | một output, settle theo actual | E4 | PASS |
| Count 2–10 | selector/cost/loop | source + pytest | UNTESTED E4 |
| Duration 15–30 | server kiểm 5–180 và min≤max | E3/E4 | PASS sampled |
| Genre talking-head | analysis/editorial | E4 | PASS sampled |
| 9 genre còn lại | registry/config | E1/E2 | UNTESTED E4 |
| VI | speech pipeline | E4 | PASS kỹ thuật; chất lượng chữ yếu |
| Auto/EN | control/config | E1/E2 | UNTESTED E4 |
| Brand LTT Red/Creator Clean | override vào render | E4 | PASS sampled |
| Auto/Cinematic | contract | E2 | UNTESTED E4 |
| Platform YouTube Shorts | metadata/ZIP | E4 | PASS |
| TikTok/Instagram | metadata generator | E2 | CONDITIONAL |
| Rationale/score | dimension + why/risk | E3 | PASS kỹ thuật, chưa calibrated |
| Compare | source range ↔ clip video | E3 | PASS |
| Sửa title/transcript | revision owner-only | pytest | PASS; không rerender video |
| ZIP/SRT | owner-only, rebased clip timeline | E3 + byte inspection | PASS |
| Cancel/retry | generic job surface | tests hệ thống | PARTIAL; engine chưa cooperative |
| History | 8 job gần nhất | E3 | PARTIAL |

Không có control vỏ/dead CTA trong hành trình đã chạy. “Platform package” hiện
chỉ là metadata tải xuống, chưa phải nút publish thật.
