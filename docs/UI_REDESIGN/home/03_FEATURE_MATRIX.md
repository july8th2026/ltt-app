# UI-RD — Ma trận tính năng trang chủ

| ID | Ảnh tham khảo | Hiện trạng có bằng chứng | Quyết định sơ bộ | Điều kiện để BUILD |
|---|---|---|---|---|
| H-01 | Catalog card/app launcher | `/` sinh từ registry, public, search/group filter | RESTYLE | giữ route, access, setup blocker, login return-to |
| H-02 | Search command bar + Ctrl K | search client-side theo name/summary; không có shortcut/global action | EXTEND | Dev chọn command scope; keyboard/focus/accessibility test |
| H-03 | Filter category | group filter hiện có, taxonomy chỉ 5 nhóm | EXTEND | chốt taxonomy manifest và empty state |
| H-04 | Sort Popular | không có ranking/telemetry | BUILD | aggregate job theo slug để sort; không hiển thị số giả |
| H-05 | 5-column artwork cards | 3 cột, gradient + emoji, CTA, badge hiện có | RESTYLE/EXTEND | asset strategy, mobile layout, performance budget |
| H-06 | Popular/New/Pro/Beta badge | `badge`/enabled/setup có, Pro/Beta không có entitlement | EXTEND/DEFER | badge semantic rõ, Pro chỉ khi membership thật |
| H-07 | Usage counts | không có dữ liệu aggregate | REJECT hiện tại | privacy-safe aggregate + product decision |
| H-08 | Sidebar: Marketplace/My Apps/etc. | header/nav groups; `/jobs`, settings tồn tại; favorites/templates/resources/community thiếu | EXTEND | chốt IA và map route thật; không tạo dead navigation |
| H-09 | Credits + profile | header authenticated có credit/avatar/menu | RESTYLE | dùng `so_du_credit`, không hardcode/đổi money logic |
| H-10 | Recent activity | jobs/history tồn tại nhưng không có home summary | BUILD | query owner-scoped, empty state, limit/privacy |
| H-11 | Running jobs + progress | `/jobs` và job state tồn tại, không có rail widget | BUILD | owner-scoped query + polling/HTMX + zero-job state |
| H-12 | Pro upsell | nạp credit tồn tại; membership/Pro entitlement chưa xác định | REJECT hiện tại | credit/nạp credit thật, không giả entitlement |
| H-13 | Neon red visual system | shared design system blue dark hiện tại | RESTYLE | chốt có đổi toàn platform hay chỉ home; contrast/motion check |
| H-14 | Mobile | hiện overflow 48 px ở 390 px | BUILD bug-fix bắt buộc | no horizontal overflow at 360/390/768 |
