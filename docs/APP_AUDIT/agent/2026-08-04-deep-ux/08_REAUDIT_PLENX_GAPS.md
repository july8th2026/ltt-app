# Re-audit PlenX vòng 2 và delta triển khai H20.8

Ngày kiểm: 2026-08-04. Nguồn bằng chứng: phiên PlenX đã đăng nhập, workflow audit
riêng không chạy generation; LTT local `127.0.0.1:8118`; source và test trong repo.
Không suy diễn capability chỉ từ hình ảnh, không tiêu credit benchmark.

## 1. Hành vi đã thao tác trực tiếp trên PlenX

| Vùng | Hành vi quan sát được | Kết luận cho LTT |
|---|---|---|
| Add menu | 11 node active; Upload/Enhance/Remove Background/Animation disabled | Chỉ hiện ToolSpec có executor/quote thật; không sao chép control disabled |
| Toolbar | Select, add, frame, layers, grid, comment, sticky, undo/redo | LTT đã có tương đương; giữ icon rail gọn |
| Shortcut | I/V/T/A/D/F/N/E, copy/paste/duplicate, select-all, nudge, zoom | Bổ sung nhóm tạo node và tổ chức thường dùng; không chiếm phím khi đang nhập |
| Node title | Tên node sửa trực tiếp tại header | Lưu label ở metadata node, tuyệt đối không trộn vào Plan/tool params |
| Text node | Add manually tạo vùng soạn text ngay trong node; Generate mở composer | Bổ sung editor trực tiếp, vẫn giữ composer AI riêng |
| Input | Image/Video/Audio có upload; Image source gồm máy, URL, resources, history, character | Máy tính/drop triển khai ngay; các nguồn còn lại cần Asset Catalog/SSRF/provenance |
| Connected input | Merge/transform hiện chip input theo thứ tự và cho bỏ từng nguồn | Bổ sung chip phản ánh edge thật; tháo chip phải xóa cả edge và `$source.handle` |
| Output | Preview, expand, copy URL, duplicate/re-upload/download | Bổ sung action output dùng artifact URL server hiện có |
| Node menu | Run From Here, Copy, Move Page, Delete | LTT đã có và giữ quote/approval server-authoritative |
| Blank menu | Không có hành vi mới ổn định trong lượt kiểm | LTT giữ menu add/auto-layout/hide edge hiện có, không hạ cấp |
| Pages/save | Có page; quan sát được xung đột save HTTP 409 và banner reload/overwrite | LTT giữ optimistic conflict hiện có; không sao chép lỗi benchmark |

## 2. Delta giữ, bỏ, xây

### Đã xây trong H20.8

1. Sửa tên hiển thị node trực tiếp, giới hạn 80 ký tự, lưu ngoài executable data.
2. Text node có textarea trực tiếp và CTA mở cấu hình AI theo ngữ cảnh.
3. Composer hiện toàn bộ input đã nối bằng chip; tháo một chip cập nhật graph và
   tham số tham chiếu trong cùng một reducer transaction, có undo.
4. Shortcut `I/V/T/A` tạo node theo modality, `N` sticky, `F` frame selection,
   `D` Workspace, `Ctrl+A` chọn tất cả, arrow/Shift+arrow di chuyển node.
5. Shortcut không chạy khi focus ở input/textarea/select/contenteditable.
6. File image/video/audio có thể kéo-thả thẳng vào node qua upload owner-scoped
   hiện có; không tạo upload runtime thứ hai.
7. Artifact đã chạy có mở rộng, chép URL, tải xuống và nhân bản node.

### Giữ vì LTT tốt hơn hoặc là contract bắt buộc

- Typed compatibility, server quote, approval trước spend, ownership, retry,
  validation, snapshot/conflict và scoped run vẫn do runtime LTT quyết định.
- Context menu pane/node và kéo connection ra blank tạo node compatible của LTT
  đã bằng hoặc mạnh hơn hành vi quan sát được.
- Inspector giữ advanced fields; đường dùng phổ thông không hiện app slug,
  credential, callback, raw provider payload hoặc field chỉ dành cho dev.

### Không triển khai giả; mở vé hợp đồng kế tiếp

| Vé | Hạng mục | Điều kiện trước khi code UI | Ưu tiên |
|---|---|---|---|
| AG-AST-01 | Asset Catalog: file đã tải, system resources, tìm kiếm, thumbnail | Owner index, retention/delete, quota, signed delivery, audit log | P1 |
| AG-URL-02 | Nhập Image/Video/Audio bằng URL | SSRF allowlist, MIME/size probe, provenance/license, async ingest | P1 |
| AG-BAT-03 | Multi-upload Batch Images và reorder | Bounded batch contract, partial failure, credit/cleanup semantics | P2 |
| AG-OUT-04 | Replace/re-upload/variation từ output | Artifact lineage, immutable run record, derived asset ownership | P2 |
| AG-MDL-05 | Mở rộng model như benchmark | Provider adapter, license, health, price, fallback và output gate | P2 |
| AG-E4-06 | User task + telemetry | Consent, event schema không PII, success/time/error dashboard | P1 |

Enhance, Remove Background và Animation chỉ được mở khi ToolSpec có executor,
quote, output validation, test và browser evidence. Tên giống đối thủ không phải
bằng chứng capability.

## 3. Nghiệm thu H20.8

- Frontend unit/integration: 29/29 pass.
- TypeScript + Vite production build: pass.
- Browser desktop 1720×940: rename và text inline autosave qua PUT 200; shortcut
  `I` tăng 5 → 6 node; merge composer hiển thị đúng chip input.
- Browser mobile 390×844: render được, authoring vẫn read-only theo quyết định;
  console 0 error/warning.
- Browser local fresh: request liên quan palette/workflow/preferences/quote/save
  đều 200; không có failed request mới.

Full repository gate và secret scan được ghi ở `NHAT_KY.md` sau khi chạy thật.
