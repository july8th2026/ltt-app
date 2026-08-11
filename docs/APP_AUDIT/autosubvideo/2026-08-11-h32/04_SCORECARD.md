# H32.1 — Scorecard: AutoSub Video

- **Quality Score: 70/100**
- **Market Score: 69/100**
- **Evidence Confidence: 88/100**
- **Release Gate: CONDITIONAL / chưa đủ bằng chứng cho AI A-Z**

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Nhận xét |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 4.2 | 12.6 | Output thật đúng style/audio/metadata |
| Tính năng/độ đầy đủ | 12 | 3.8 | 9.1 | Breadth tốt, còn thiếu power controls có chọn lọc |
| Chức năng/control | 12 | 4.0 | 9.6 | Luồng sampled pass; AI chưa cấu hình |
| UX/workflow/IA | 12 | 3.4 | 8.2 | 4 bước rõ, nhưng dày và dev-facing |
| UI/design system | 8 | 3.7 | 5.9 | Desktop tốt, chưa thật nhẹ mắt |
| Responsive/accessibility | 7 | 2.7 | 3.8 | Mobile dùng được nhưng cuộn dài/timeline precision yếu |
| Hiệu năng/tin cậy | 9 | 3.8 | 6.8 | NVENC nhanh, history sống; waveform/network cần tối ưu |
| AI/economics | 8 | 2.4 | 3.8 | Quote render pass; AI configuration chưa test |
| Security/privacy/credit | 10 | 2.8 | 5.6 | Credit pass; các finding upload cũ chưa có evidence đóng |
| Kiến trúc/ops/log | 7 | 3.5 | 4.9 | Job events/support ID tốt; test còn thread warning |

Tổng quy đổi: **70,3 → 70/100**.

## Gate

| Gate | Kết quả |
|---|---|
| G0 scope | PASS |
| G1 core outcome | PASS cho import + render sampled |
| G2 security | NOT RE-GATED; carry-forward upload contract cần xác minh |
| G3 money | PASS cho sampled quote/settlement; chưa workload matrix |
| G4 honest UI | PASS capability-off; PARTIAL preview/golden parity |
| G5 recovery | PASS reload sampled; chưa offline/two-tab |
| G6 accessibility | FAIL locale/mobile precision |
| G7 performance | PASS video nhỏ; chưa video 120 phút/load |
| G8 operations | PARTIAL; log tốt, test warning còn tồn tại |
