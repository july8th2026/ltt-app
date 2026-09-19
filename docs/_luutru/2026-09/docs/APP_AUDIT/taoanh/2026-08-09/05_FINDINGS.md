# A6 — Findings và root cause

| ID | Sev | Finding → root cause | Acceptance |
|---|---|---|---|
| IMG-H26-01 | P1 | Marketplace hợp nhất nhưng route/template vẫn là hai product → H26.4 chỉ xử lý presentation catalog | một shell canonical, mode quyết định nội dung |
| IMG-H26-02 | P1 | `/taoanh/thumbnail` lại redirect sang URL cũ → canonical ngược Q70 | `/thumbnail` GET 308 về `/taoanh/thumbnail` |
| IMG-H26-03 | P2 | header/copy/lịch sử lặp, khách đổi mental context | shell/header/mode/history thống nhất |
| IMG-H26-04 | P1 | hợp nhất bằng import app chéo sẽ tạo coupling runtime | browser composition qua endpoint app con; test không import chéo |
| IMG-H26-05 | P2 | folder yêu cầu trống | ghi UNKNOWN; không build feature từ suy đoán |

Không sửa engine, provider, cost hoặc schema để chữa lỗi presentation.
