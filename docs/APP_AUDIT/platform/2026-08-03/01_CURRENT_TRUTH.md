# 01 — Current Truth

## Kiến trúc giao diện thật

Nền tảng đang có bốn lớp thị giác:

1. `server/static/ltt.css` + base public/plain: dark xanh `#3b6ef2`.
2. `server/templates/base.html`: lặp token/CSS inline dark xanh, có thể override
   nguồn CSS chung.
3. Marketplace authenticated, Tạo video, Upscale, Auto Sub: dark đỏ/đen bằng
   selector/hardcode riêng.
4. React Agent Canvas và sqladmin: token/shell riêng; admin production có nền
   xanh khác (`rgb(26,34,52)`).

Vì vậy “có một file design system” chưa đồng nghĩa có một design system thật.
Token bị lặp và component app tự dựng khiến header, logo, button, form, radius,
spacing, typography, empty/error state đổi khi chuyển trang.

## Truth map chung

`manifest → route/template/React island → auth/CSRF/ownership → job/worker/provider
→ quote/hold/settle/refund → storage/R2/artifact → jobs/history`.

Hạ tầng job/credit/ownership đã có test và canary production mạnh. Khoảng trống
chính của chương trình này là product parity, IA, accessibility và một contract
giao diện dùng chung; không cần xây lại queue, credit, storage hoặc provider.

## Năng lực nội tại phải tái sử dụng

| Năng lực | Vị trí | Quy tắc |
|---|---|---|
| App registry/manifest/ToolSpec | `platform_core/registry.py`, `apps/*/manifest.py` | Không hardcode danh sách app |
| Job + credit atomic | `platform_core/jobs.py`, `credit.py` | Không tạo queue/billing thứ hai |
| R2/local/Range | `platform_core/storage.py`, media routes | Dùng lại, giữ owner scope |
| Shared CSS/shell | `server/static/ltt.css`, `_header.html`, bases | Nâng thành token/component chuẩn |
| Marketplace mới | `home.html` + market selectors | Nguồn layout/brand, không copy magic number |
| Video studio | `taovideo`, `upscalevideo` | Nguồn pattern composer/library/queue/quote |
| Editor phức tạp | React islands Agent/Auto Sub | Giữ React khi state-heavy theo Q49 |

## Baseline production

- 25 bề mặt authenticated/public được mở: HTTP/final render PASS, console app
  không lỗi, request app không fail trong luồng quan sát.
- Desktop 1280 không overflow ở các app/trang authenticated đã kiểm.
- Public catalog mobile 390 px overflow ngang **48 px**.
- Mobile audit cho thấy phần lớn target tương tác dưới 44×44; có field thiếu
  accessible name ở Settings, Chat, Kịch bản, Tạo ảnh, Clip, Tạo video,
  Thumbnail và Upscale.
- Login/register/forgot vẫn xanh; Home authenticated và ba Studio mới đỏ/đen.
- `lttstudios.com` đang phục vụ site khác; nhiều URL file repo trả 404.

## Unknown có kiểm soát

- Chưa chạy user test định lượng với khách thật trong lượt này.
- Market Score là baseline theo official docs, chưa mua/trial đủ mọi gói đối thủ.
- Không chạy lại corpus output-quality của mọi provider; dùng bằng chứng mới nhất
  trong audit/journal từng app. Các điểm M có thể thay đổi sau trial nhưng không
  làm đổi thứ tự đóng blocker nền tảng.
