# 01 — Current Truth

## Bề mặt và hợp đồng

- Manifest: public, lifecycle `development`, customer surface tại `/agent` và
  `/agent/canvas`.
- React island ở `frontend/agent-canvas`; API/workflow/run/credit vẫn được kiểm
  soát phía server. Runtime dùng ToolSpec của app hiện có, không tạo provider
  hoặc sổ credit thứ hai.
- Q68 đang có hiệu lực: bốn creative block Text/Image/Video/Audio, công cụ nâng
  cao progressive disclosure, prompt và Run nằm theo block, theme dark mặc
  định và lưu theo user.

## Truth map đã quan sát

`starter → graph 2 node/1 edge → nhập Text → Run Image → scope dependency →
quote tối đa 8 → confirm → 2 step hoàn tất → dùng 8/8 credit → reload bền`.

E1: manifest/source; E2: 52 frontend test và 98 targeted Python test; E3:
browser local desktop/mobile. Không có E4 mới, không chạy provider thật.

## Unknown có chủ đích

P50/P95, load/soak, recovery khi worker/provider thật mất kết nối, retention
production và task-success người dùng thật thuộc H26.11–12; không dùng test
fixture để tuyên bố các hạng mục này đã PASS.
