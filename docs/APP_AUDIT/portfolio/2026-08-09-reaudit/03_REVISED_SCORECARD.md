# Scorecard hiệu chỉnh vòng 2

Q, M và severity giữ từ H27 trừ khi có bằng chứng mới làm đổi kết luận. E được
tính lại theo cấp bằng chứng thật. Dấu `*` nghĩa là Market Score provisional do
A4 chưa đủ matrix/source cùng plan/region/device.

| App/phạm vi | Q | M | E mới | E cũ | Gate | Trạng thái audit |
|---|---:|---:|---:|---:|---|---|
| Upscale Video | 64 | 57 | **61** | 84 | BLOCKED | A0–A6 có chiều sâu; thiếu E4/G7/G8 |
| Seedance Video | 57 | 64 | **61** | 87 | BLOCKED | A0–A6 có chiều sâu; thiếu E4/G7/G8 |
| Auto Sub | 56 | 65 | **61** | 90 | BLOCKED | A0–A6 có chiều sâu; thiếu E4/G7/G8 |
| Prompt AI OMMI | 48 | 51 | **56** | 92 | BLOCKED | core A-Z/provider còn UNKNOWN |
| Tạo ảnh + Thumbnail | 56 | 54 | **60** | 91 | BLOCKED | provider/output/user test UNKNOWN |
| Tạo Clip ngắn | 58 | 56 | **61** | 92 | BLOCKED | render/GPU/SLO production UNKNOWN |
| Chat AI Studio | 48 | 42 | **58** | 94 | BLOCKED | provider/legal/SLO UNKNOWN |
| LTT Agent AI | 43 | 38 | **61** | 95 | BLOCKED | P0 tái khẳng định; concurrency/E4 UNKNOWN |
| Socialbot maintenance | 41 | 35* | **60** | 94 | BLOCKED | A2/A4 PARTIAL; 2 P0 giữ nguyên |
| Demo hạ tầng | 78 | 70* | **40** | 92 | INTERNAL | contract tốt; A2/A4/G7/G8 PARTIAL |
| Kịch bản/Text runtime | 64 | 50* | **38** | 91 | BLOCKED | A2/A4 và provider output thiếu |
| Media Tools runtime | 59 | 47* | **38** | 90 | BLOCKED | A2/A4 và large-media/provider thiếu |

E trung bình của 8 customer product chính: **59,9**, không phải 90,6. Thay đổi
này không nói app tệ hơn; nó nói độ chắc của kết luận trước đây đã bị trình bày
quá mức.

## Gate tái xác nhận

- **3 P0 giữ nguyên:** Agent duplicate child/credit; Socialbot global token;
  Socialbot global worker/monitor.
- 89 targeted tests về registry/access/Agent run/executor/API: PASS.
- Browser route matrix không bác bỏ P0; riêng Socialbot vẫn cho customer thường
  vào `/facebook`, đúng finding authorization H27.
- Không app BLOCKED nào được nâng gate. Demo giữ INTERNAL.

