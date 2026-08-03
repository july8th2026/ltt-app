# Browser evidence — production 2026-08-03

## Cách kiểm

Playwright Chrome; anonymous và canary admin tạm. Canary không in credential,
không dùng dữ liệu khách; sau audit đã bị deactivate và revoke session. Kiểm
status/final URL, console error, failed request, control count, body/token style,
overflow desktop/mobile, target geometry và accessible name heuristic.

## Kết quả

- Anonymous `/`, `/login`, `/register`, `/forgot-password`: 200; console/network
  app sạch trên desktop. `/nap`, `/jobs`, app và social route return-to `/login`.
- Authenticated: `/`, commerce/jobs/settings/status; 9 app public; Agent Canvas;
  Socialbot legacy; workers/monitor/audit/admin đều render 200, desktop 1280
  không overflow và không có console/app request failure trong lượt quan sát.
- Mobile authenticated 390: 14 bề mặt kiểm tra không overflow.
- Mobile anonymous `/`: overflow 48 px; auth pages không overflow.
- Target dưới 44 px xuất hiện rộng: Home 19/20, Settings 149/162, Auto Sub 49/59,
  Tạo video 37/40, Upscale 31/34 trong heuristic hình học. Con số gồm cả text
  link nên dùng để chỉ đường audit chi tiết, không tự coi mọi item là WCAG fail.
- Field thiếu accessible name heuristic: Settings 1, Chat 1, Kịch bản 4, Tạo ảnh
  2, Tạo Clip 6, Tạo video 8, Thumbnail 3, Upscale 1.
- Production screenshots tạm đã quan sát: Home authenticated, Tạo video,
  Upscale, Auto Sub, Login. Evidence nằm trong `tmp/`, không commit/release.

## Website domain

`https://lttstudios.com/` và `/about/`, `/privacy-policy/`, `/terms/`,
`/data-deletion/` render 200. Các URL source-style `/products.html`,
`/download.html`, `/architecture.html`, `/changelog.html`, `/support.html`,
`/contact.html`, `/transparency.html`, `/legal/security.html`, compliance và
nhiều `/vi/*.html` trả 404. `/vi/` redirect sang một trang sản phẩm khác. Đây là
bằng chứng domain hiện không phục vụ gói static trong repo.

## Giới hạn

Không submit job/provider hoặc order trả tiền trong audit này. Functional E2–E4
lấy từ test/canary đã ghi trong `docs/NHAT_KY.md`; audit này tập trung inventory,
render, consistency, control và market gap.
