# Journey & Control Registry

Ma trận chi tiết của 11 loại node và interaction nằm tại
`00_CONTROL_MATRIX.md`. Kết quả nghiệm thu bổ sung:

| Journey/control | Verdict | Evidence |
|---|---|---|
| Add node từ catalog nhóm | LIVE | E3 browser + E2 test |
| Upload/generate/manual theo modality | LIVE | E2 component/API; không gọi provider trả phí |
| Composer theo node | LIVE | E3, không lộ raw ToolSpec field |
| `@node` compatible reference | LIVE | E3 tạo edge thật; E2 regression |
| Kéo output vào khoảng trống | LIVE | E3 compatible picker và auto-connect |
| Node/pane right-click | LIVE | E3 + E2 |
| Run node độc lập | LIVE | E3 tạo `awaiting_approval` 10 credit, actual 0 |
| Run from here | LIVE | E2 scope/downstream; backend vẫn thêm prerequisite |
| Credit approval | LIVE từ runtime cũ | E2; không phê duyệt trong audit |
| Edge render/reload | LIVE | E3: state 1, renderer 1, console sạch |
| Mobile Canvas | LIVE read-only | E3: 390px, tabs/panel, overflow 0 |

Không còn control `DEAD` hoặc `MISLEADING` được phát hiện trong journey đã kiểm.
Mobile chỉnh sửa là deliberate omission hiện hành, không được trình bày như có.
