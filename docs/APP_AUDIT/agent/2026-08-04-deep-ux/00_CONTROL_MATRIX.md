# H20 Agent Canvas Deep UX — research baseline

Ngày: 2026-08-04. Phạm vi: PlenX authenticated workflow, LTT production/local,
source LTT và tài liệu FLORA công khai. Không chạy generation và không tiêu credit
benchmark. Đây là baseline hành vi, không phải bằng chứng LTT đã triển khai parity.

## 1. Control Registry

| Vùng | Control/hành vi benchmark | Trạng thái LTT trước H20 | Quyết định Q66 |
|---|---|---|---|
| Toolbar | Select, add node, workspace/grid, layer, comment/note, undo/redo | Có phần lớn | Giữ icon rail, chuẩn hóa tooltip/focus |
| Canvas blank | Right-click mở add menu tại con trỏ | Chưa có | Bắt buộc |
| Canvas blank | Ẩn đường nối, auto-layout | Có trong drawer/command | Đưa thêm vào context menu |
| Node | Right-click Run From Here, Copy, Move Page, Delete | Chưa có menu | Bắt buộc |
| Connector | Kéo output vào blank → node compatible picker | Picker hiện chỉ chọn node đã tồn tại | Bắt buộc tạo + tự nối |
| Selection | Viền trắng/glow, composer theo node | Có selection; composer schema thô | Giữ selection, thay composer node-native |
| Execution | Run node, selection, frame, full | Runtime đã có | Đưa Run node/From here ra gần node |
| Money | Giá cạnh Generate; approve trước spend | Runtime/quote có, UX xa tác vụ | Hiện giá và quote tại contextual action |
| Assistant | Context từ selection/@mention, preview diff | Preview diff có; context yếu | Thêm node context, giữ server validator |

## 2. Node inventory benchmark

| Nhóm | Node | Empty-state / hành động chính cần có | Xác minh sâu khi implement |
|---|---|---|---|
| Content | Image | Upload, drop/paste hoặc Generate | preview/history/variation/reference |
| Content | Batch Images | Multi-upload hoặc tạo nhiều ảnh | mapping item → downstream, fanout |
| Content | Video | Upload hoặc Generate | image/text refs, duration, audio, preview |
| Content | Social Video | Nhập URL và tải về | validation URL, progress, owner asset |
| Content | Text | Add manually hoặc Generate | editor, rewrite, @mention, streaming |
| Content | Audio | Upload hoặc Generate | speech/music/SFX mode, player |
| Transform | Upscale | Nhận image rồi chạy | scale/mode, before-after |
| Transform | Video Upscale | Nhận video rồi chạy | resolution, ETA, audio/FPS defaults |
| Transform | Extract Frames | Nhận video rồi chạy | interval/FPS/range, collection output |
| Transform | Merge Video | Nhiều video có thứ tự | reorder, transition policy, output preview |
| Transform | Merge Image | Nhiều ảnh có thứ tự | layout/orientation/spacing, preview |

Upload, Enhance, Remove Background và Animation đang disabled trên benchmark;
LTT không quảng bá chúng như capability hoàn chỉnh nếu executor/quote/output chưa
qua gate.

## 3. State × Action contract chung

Mỗi node phải có sáu trạng thái: `empty`, `configured`, `queued/running`, `done`,
`error`, `disabled`. Với mỗi trạng thái phải kiểm click, double-click, hover,
right-click, drag/drop/paste, connect, run, cancel/retry, download/reuse,
copy/delete/undo/redo, keyboard và reload persistence.

## 4. Presentation contract

- Node là mini-app theo JTBD; không render form ToolSpec chung.
- Empty state trả lời ngay “đưa input vào bằng cách nào” và “tạo mới ở đâu”.
- Contextual composer chỉ hiện 3–6 quyết định nghiệp vụ thường dùng; schema đầy đủ
  nằm trong Inspector nâng cao.
- Server vẫn là nguồn chân lý về schema, compatibility, quote, approval và output.
- Label raw (`image_key`, `model_ref`, job type, app slug) không xuất hiện trong
  đường dùng phổ thông.
- Nền mặc định gần đen; selected node có viền sáng trung tính; đỏ LTT dành cho CTA,
  cảnh báo và trạng thái, không phủ toàn canvas.

## 5. Evidence đã có

- PlenX: catalog 11 node active; pane/node context menu; contextual composer;
  selected glow; thao tác không tiêu credit.
- LTT production: node `image.generate` hiện composer raw `prompt/model/
  aspect_ratio`; console lượt kiểm tra 0 error, API hiện tại 200.
- LTT source: `ToolNode.tsx` dùng một renderer chung; `CanvasShell.tsx` sinh tối
  đa ba field trực tiếp từ schema; scoped execution, ownership, quote/approval và
  typed validation đã tồn tại nên không xây runtime thứ hai.

## 6. Pass gate H20.1

- Inventory 11/11 node: PASS.
- Toolbar/context/connection/execution controls: PASS.
- State × Action contract: PASS.
- Delta giữ/bỏ/xây và ranh giới safety: PASS.
- Generation benchmark có mất credit: chưa chạy và không phải điều kiện H20.1;
  chỉ mở khi có test budget riêng.

## 7. Re-audit vòng 2

Control title edit, inline Text, source chooser, connected-input chips, output
actions và keyboard được thao tác thêm trên PlenX rồi đối soát lại LTT. Kết quả,
phạm vi triển khai và vé còn mở nằm tại `08_REAUDIT_PLENX_GAPS.md`.
