# 02 — Bảng chấm 100 hạng mục + điểm có trọng số (27/09/2026)

## 0. Luật chấm — đọc trước khi cãi một con số

**Thang.** 0 = không tồn tại · 1–20 = có mầm, hỏng · 21–40 = dùng được với người đã
biết cách · 41–60 = dùng được, nhiều ma sát · 61–80 = tốt · 81–97 = rất tốt ·
**98–100 = đạt chuẩn §9 dưới đây**.

**⛔ Luật chống tự huyễn.** Một hạng mục **không được** chấm trên 40 nếu tính năng
của nó **không chạy được** trên trình duyệt thật. Ví dụ: "Connection UX" không được
60 điểm vì "backend có credential store" — khách không dùng được backend.

**Cột `Ng.` (nguồn):** `B` = đo trên trình duyệt · `M` = đọc mã · `A` = gọi API ·
`—` = **chưa đo**, điểm là ước lượng và được đánh dấu `?`.

**Định nghĩa 98/100** (áp cho mọi hạng mục, đề bài §35):

```
98/100 đòi ĐỦ SÁU điều:
  1. không còn lỗi UX mức P0/P1 đã biết trong hạng mục;
  2. có một phép đo thành công tác vụ, đã chạy, có số;
  3. hành vi hệ thống nhất quán (một khái niệm = một từ = một chỗ);
  4. mô hình tư duy của người dùng rõ (hỏi được "cái này ở đâu" và trả lời được);
  5. trợ năng đạt WCAG 2.2 AA cho hạng mục đó;
  6. không có hai nguồn sự thật cho cùng một dữ liệu, và có test hồi quy.
⇒ Thiếu BẰNG CHỨNG cho bất kỳ điều nào ⇒ KHÔNG được chấm 98.
```

---

## 1. PRODUCT STRUCTURE

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 1 | Information Architecture | 12 | M | Toàn app = 2 trang HTML. Workflow/Runs/Templates/Connections đều MISSING |
| 2 | Navigation | 15 | B | Rail 8 nút biểu tượng không nhãn; `/agent` là ngõ cụt; không breadcrumb |
| 3 | Workflow discoverability | 5 | M | `loadOrCreateWorkflowV3` mở `items[0]`; không danh sách, không "New" |
| 4 | Agent App consistency | 25 | B | Shell nền tảng sang `/en/` còn Canvas vẫn tiếng Việt; block/node/công cụ lẫn lộn |
| 5 | Product hierarchy | 18 | B | Agent Designer nằm dưới trình quản lý trang trong ngăn kéo "Mẫu & thiết lập" |
| 6 | Feature discoverability | 20 | B | So sánh run chỉ hiện sau "Chạy lại từ đây"; Inspector chỉ vào được qua nút `☰` |
| 7 | Onboarding | 30 | B | Empty state có chữ dẫn rõ ràng — nhưng dẫn tới một palette mà 82% node hỏng |

## 2. CANVAS

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 8 | Canvas layout | 35 | B | Stage full-bleed tốt; nhưng palette/inspector là ngăn kéo ĐÈ, không phải cột |
| 9 | Workspace density | 15 | B | Node 456×381px; lưới 430px ⇒ chồng 26px từ node thứ hai |
| 10 | Node visual hierarchy | 12 | B | Tiêu đề = câu cắt 60 ký tự; tên thật (`app_name`) nhỏ hơn chuỗi `type@version` |
| 11 | Edge clarity | 18 | B | 2 nhánh của `core.if` cùng màu, cùng kiểu, `edgeLabels: [null, null]` |
| 12 | Connection UX | **5** | B | 15 cổng chồng 1 điểm 6×6px; kéo dây → 0 cạnh, im lặng |
| 13 | Zoom / pan / fit | 62 | B | `Controls` + `fitView` + `minZoom .1/maxZoom 2` đủ dùng; thiếu fit-to-selection |
| 14 | Large workflow usability | 15 | M | Không group, không tìm node trên canvas, minimap rỗng, không auto-layout thật |
| 15 | Grouping / framing | 25 | M | Có `frame` nhưng `draggable:false, selectable:false`, chỉ là hình chữ nhật trang trí |
| 16 | Context menu | 40 | B | Có menu pane + node; nhưng pane menu chỉ 3 mục, không "thêm node tại đây" |
| 17 | Quick create | **8** | B | Nút `+` trên cạnh là NO-OP đã bấm thử; không quick-add từ cổng |
| 18 | Keyboard shortcuts | 45 | M | Có undo/redo/copy/paste/dup/select-all/arrow-nudge/n/f/d — nhưng không nơi nào liệt kê |
| 19 | Multi-select / bulk | 48 | M | `selectionOnDrag` + Ctrl/Meta + nhân bản/xoá hàng loạt có; không align/distribute |

## 3. PALETTE

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 20 | Node library | 30 | A | 67 node sinh 100% từ registry (kiến trúc ĐÚNG) — nhưng 55 không biên dịch được |
| 21 | Search | 40 | M | `locPalette` lọc title/desc/type/app_name có `toLocaleLowerCase('vi')`; không fuzzy, không tab |
| 22 | Categorization | 55 | B | 8 category cố định của spec + nhóm "Gần đây" (localStorage) — hợp lý |
| 23 | Recent / favorites | 50 | M | "Gần đây" 8 mục có; **không có** favorites |
| 24 | Connector discovery | 20 | B | 27 connector hiện icon-URL dạng chữ; không lọc "đã kết nối / chưa kết nối" |
| 25 | App node discovery | 15 | A | 12/12 tiêu đề LTT_APPS bị cắt giữa từ ở 60 ký tự |
| 26 | Metadata clarity | 35 | B | Có giá/GPU/"Cần kết nối"/"Sắp có" (tốt); nhưng "0 credit" mơ hồ, `type@version` lộ ra |

## 4. NODE

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 27 | Node compactness | 10 | B | Liệt kê MỌI cổng thành hàng chữ; 456×381px cho một bước |
| 28 | Node states | 30 | M | Có `trangThai` + `node-do-loi`; nhưng chỉ là chữ, không viền/màu/biểu tượng phân biệt |
| 29 | Input/output readability | 15 | B | 21 tên cổng / 2 chấm nối; nhãn cách handle 88–150px |
| 30 | Error states | 42 | B | `node-do-loi` + huy hiệu "Lỗi biên dịch" + banner — rõ ràng; nhưng thông điệp là mã máy |
| 31 | Running state | 35 | M | Có nhãn chữ + `is-running` trên cạnh; **chưa đo trên trình duyệt** (không có worker) `?` |
| 32 | Waiting state | 38 | M | `NHAN_WAITING_KIND` phân biệt 6 loại chờ (thiết kế TỐT) nhưng chỉ hiện trong bảng run |
| 33 | Media preview | **0** | M | Không một dòng nào vẽ ảnh/video/audio trên node — dù LTT là nền tảng media |
| 34 | Cost / resource | 25 | B | Có huy hiệu `GPU`; `liveQuotes` đã có trong bộ nhớ nhưng KHÔNG hiện trên node |

## 5. INSPECTOR

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 35 | Configuration flow | 20 | B | Một cột phẳng 15 ô, không thứ tự ưu tiên, `model` không được đưa lên trước |
| 36 | Form clarity | 35 | M | Sinh từ lược đồ (ĐÚNG hướng); nhãn là tên tham số máy (`aspect_ratio`), không nhãn người |
| 37 | Dynamic fields | 22 | B | 4 ô phụ thuộc hiện "— chưa có lựa chọn nào —" cùng lúc; hint "Tuỳ theo: model" |
| 38 | Credentials UX | **0** | M | Không tồn tại. `credential_ref` không có ở bất kỳ đâu trong `src/` |
| 39 | Advanced settings | **0** | M | Không có tách cơ bản/nâng cao; `settings`/retry/timeout không có UI |
| 40 | Testing node | **0** | M | Không có "Test step". Chỉ chạy được CẢ workflow |
| 41 | Input/output preview | **0** | M | Inspector không hiện dữ liệu vào/ra của bước |
| 42 | Validation feedback | 30 | M | `OJson` không nuốt lỗi JSON (tốt); nhưng không kiểm required trước publish |

## 6. DATA MAPPING

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 43 | Expression UX | 55 | M | `OBieuThuc` là phần mạnh nhất của frontend: combobox ARIA đúng, chỉ mở trong `{{` chưa đóng |
| 44 | Variable picker | 12 | B | Không có cây/nút chèn. Chỉ với tới được khi người dùng TỰ gõ `{{` |
| 45 | Previous-node data browser | **0** | M | Không tồn tại |
| 46 | Type awareness | 30 | A | Hệ kiểu thật (17 kiểu, 180 cặp) — nhưng giao diện chỉ hiện tên kiểu bằng chữ 11px |
| 47 | Autocomplete | 60 | M | Có, từ máy chủ, đánh dấu `chưa publish được`, không bịa khi máy chủ im |
| 48 | Error feedback | 35 | M | Hiện mã lỗi máy chủ (`goiY.loi.ma`) cho người dùng cuối |
| 49 | Data transformation UX | 20 | B | `core.transform`/`core.set` tồn tại nhưng P0-1 chặn; tham số `array`/`object` là textarea JSON thô |

## 7. EXECUTION

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 50 | Run UX | 28 | B | Ngăn kéo "Chạy workflow" chứa 7 lệnh xem/sửa; không báo giá trước khi bấm |
| 51 | Run history | **0** | M | Không có. Không cửa máy chủ liệt kê run theo workflow |
| 52 | Node execution timeline | 15 | B | `<ol>` in `loai · node_id`, KHÔNG dấu thời gian (dù `created_at` có sẵn) |
| 53 | Logs | 25 | M | `RunInspector` đổ JSON thô qua `@uiw/react-json-view` — là dây nối, không phải UI |
| 54 | Inputs/outputs | 25 | M | Chỉ xem được trong cây JSON thô, không theo bước |
| 55 | Cost | 45 | B | `credit_charged/credit_max` hiện ở đầu bảng run — đúng và rõ |
| 56 | Resource / GPU info | 35 | B | Huy hiệu `GPU` trên node/palette; cố ý không lộ VRAM/slots (ĐÚNG về bảo mật) |
| 57 | Retry | 30 | M | "Chạy lại từ đây" có và gọi cửa thật; nhưng không cấu hình được retry |
| 58 | Replay | 40 | M | `chayLaiTuNodeV3` tái dùng output node không phải hậu duệ — thiết kế tốt |
| 59 | Compare run | 35 | M | `RunDiff` + `jsondiffpatch` tốt, nhưng chỉ sống trong phiên, đóng tab là mất |
| 60 | Failure debugging | 18 | B | Lỗi hiện dưới dạng mã máy (`node_khong_ton_tai: core.set`); không có cách nhảy tới bước hỏng |

## 8. AGENT

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 61 | Agent Designer UX | 15 | B | Nút chữ thường ở đáy ngăn kéo thứ ba, dưới trình quản lý trang |
| 62 | NL workflow generation | 40 | M | `soanWorkflowV3` chạy thật và — quan trọng — **ghi node đúng hình dạng** (khác palette) |
| 63 | AI suggestions | 10 | M | Không gợi ý node kế tiếp, không sửa từng phần, chỉ sinh cả đồ thị |
| 64 | Plan preview | **0** | M | Không có |
| 65 | Diff before apply | **0** | M | `dispatch({type:'replace'})` ghi đè và **xoá `past`/`future`** ⇒ mất undo |
| 66 | Supervisor visibility | 10 | M | `ai.agent` là node duy nhất dùng được trong nhóm AI; không màn hình theo dõi |
| 67 | Human approval UX | 20 | M | `core.human` + `NHAN_WAITING_KIND['HUMAN']` có ở backend; **không có UI để duyệt** |

## 9. WORKFLOW PRODUCTIVITY

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 68 | Templates | **0** | B | Ngăn kéo tên "Mẫu & thiết lập" chứa 0 mẫu |
| 69 | Duplicate | 55 | M | Nhân bản node/lựa chọn có và remap tham chiếu `$node.port` đúng; không nhân bản workflow |
| 70 | Subworkflow discoverability | 15 | M | `core.call_workflow` tồn tại nhưng P0-1 chặn; không có cách chọn workflow con |
| 71 | Version UX | **0** | M | Cụm snapshot/restore đã bị gỡ 24/09; không thay thế |
| 72 | Draft / publish UX | 35 | B | Publish ngầm trong "Chạy ngay"; người dùng không biết mình vừa xuất bản |
| 73 | Autosave | 70 | B | Debounce 800ms + `aria-live` "Đã lưu/Đang lưu…" — chạy tốt, thấy rõ |
| 74 | Conflict handling | 65 | M | `If-Match` + 409 + nút "Tải bản mới" — đúng bài, có lối thoát |
| 75 | Undo / redo | 55 | M | 50 bước, commit theo kéo-thả; nhưng `replace` xoá sạch lịch sử (§65) |
| 76 | Workflow organization | 8 | M | Không thư mục, không nhãn, không tìm kiếm, không danh sách |

## 10. DESIGN

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 77 | Typography | 30 | B | 5 chỗ dùng 9–10px; không dùng thang `--fs-*` của nền tảng |
| 78 | Spacing | 35 | M | Số magic rải rác; không dùng `--space-1..8` |
| 79 | Visual consistency | 25 | B | Node/palette/inspector ba ngôn ngữ thị giác khác nhau |
| 80 | Color system | 22 | M | 482 hex cứng / 105 `var()` ⇒ token hoá ≈18% |
| 81 | Dark mode | 68 | B | Mặc định, 9/9 cặp màu đạt AA, nhìn ổn — **điểm mạnh thật** |
| 82 | Light mode | 15 | B | 7/11 ô giữ nền tối; minimap/controls tương phản bề mặt 1.04:1 |
| 83 | Status colors | 30 | M | Có `edge-*`/`node-do-loi` nhưng không map vào `--status-*` của nền tảng |
| 84 | Icons | 12 | B | 32/67 icon render thành chuỗi URL; phần còn lại là ký tự Unicode lẻ |
| 85 | Component consistency | 25 | M | Không có lớp component dùng chung; mỗi nút tự khai kiểu |
| 86 | Motion / feedback | 40 | M | Có `animated` cho cạnh đang chạy + `prefers-reduced-motion`; kéo dây thất bại im lặng |
| 87 | Loading states | 50 | B | "Đang tải Canvas…" + `aria-busy` + `aria-live` — làm đúng |
| 88 | Empty states | 55 | B | Empty state đầu tiên rõ và có nút hành động — một trong những chỗ tốt nhất |

## 11. ACCESSIBILITY

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 89 | Keyboard | 45 | M | Nhiều phím tắt + `ariaLabelConfig` cho phím của React Flow; không tài liệu, không bẫy focus |
| 90 | Focus | 40 | M | `:focus-visible` trên shell; chưa kiểm thứ tự tab trong ngăn kéo |
| 91 | Screen reader | 48 | M | `aria-label`/`aria-pressed`/`role=alert`/`aria-live` phủ rộng; `aria-pressed={true}` đóng cứng ở 1 nút |
| 92 | Contrast | 72 | B | **9/9 cặp đạt AA ở theme tối** (thấp nhất 5.71:1). Trừ điểm vì theme sáng |
| 93 | Touch targets | 15 | B | Cổng nối 6×6px (WCAG 2.2 AA đòi ≥24×24); nút `{{ }}` 48×19px |
| 94 | Mobile / responsive | 20 | B | Không tràn ngang (tốt) nhưng tab "Canvas" hiện Inspector; không nói là chỉ-xem |

## 12. ENGINEERING UX

| # | Hạng mục | Điểm | Ng. | Bằng chứng / lý do |
|---|---|---:|:--:|---|
| 95 | Component architecture | 18 | M | `Editor()` 740 dòng, 33 state, 11 khu vực JSX, 14 hàm API |
| 96 | CSS architecture | 20 | M | 49/191 lớp chết; 5 khối `@media 640px` tranh nhau; dòng dài 1 340 ký tự |
| 97 | State architecture | 55 | M | `editorReducer` thuần, có test, undo/redo đúng — **phần tốt nhất của kiến trúc** |
| 98 | Maintainability | 25 | M | Chú thích giải thích "vì sao" xuất sắc; nhưng mọi thứ trong một tệp |
| 99 | Schema-driven UI | 75 | A | Palette + form + luật nối đều sinh từ máy chủ; thêm app không sửa `src/` — **điểm mạnh nhất** |
| 100 | Performance | 40 | M | Báo giá đã gom 1 request (có bánh cóc). Nhưng `NodeRenderer` không `memo`, autosave `JSON.stringify` mỗi phím. **CHƯA ĐO ở 50/100/500 node** `?` |

---

## 2. Tổng hợp

### 2.1 Cách tính — đã kiểm bằng máy, không cộng tay

Điểm được tính lại bằng `scratchpad/diem.py`, có hai `assert` chặn sai sót:
`len(D) == 100` và **"tám nhóm trọng số phải phủ kín 1..100, không trùng, không sót"**.

⚠️ Phép `assert` thứ hai đã bắt một lỗi thật ngay lần chạy đầu: nhóm **NODE (27–34)
bị bỏ quên**, không nằm trong nhóm trọng số nào — tức bản nháp đầu của bảng này chấm
trên 92 hạng mục mà vẫn in ra như thể đủ 100. Số dưới đây là số sau khi sửa. (Đúng
bài học *"đếm, đừng liệt kê từ trí nhớ"*: một bảng tự cộng tay sẽ không bao giờ tự
báo là nó thiếu 8 dòng.)

```
Tổng 100 hạng mục = 2 786  ⇒  trung bình đơn giản 27,9 / 100
```

### 2.2 Trung bình CÓ TRỌNG SỐ

Giữ nguyên trọng số đề bài đưa ra — chúng hợp lý và không cần đổi. Một lưu ý: nếu
đổi, nên **tăng** Execution/Debug, vì với sản phẩm media GPU thì "vì sao lượt chạy
tốn 40 credit" là câu khách hỏi nhiều nhất. Đề xuất giữ nguyên cho lần này để
so sánh về sau không bị trôi mốc.

Nhóm **NODE (27–34)** được xếp vào *Canvas / Workflow Building*: node là đơn vị
người dùng thao tác trên canvas, không phải một mặt riêng.

| Nhóm | Hạng mục | n | TB nhóm | Trọng số | Đóng góp |
|---|---|---:|---:|---:|---:|
| Canvas / Workflow Building | 8–19, **27–34**, 68–76 | 29 | 28,5 | 25 % | 7,12 |
| Inspector / Data Mapping | 35–49 | 15 | 21,3 | 20 % | 4,25 |
| Execution / Debug | 50–60 | 11 | 26,9 | 15 % | 4,04 |
| Agent UX | 61–67 | 7 | 13,6 | 15 % | 2,04 |
| Information Architecture | 1–7, 20–26 | 14 | 26,4 | 10 % | 2,64 |
| Design System | 77–88 | 12 | 33,9 | 5 % | 1,70 |
| Accessibility | 89–94 | 6 | 40,0 | 5 % | 2,00 |
| Frontend Maintainability | 95–100 | 6 | 38,8 | 5 % | 1,94 |

```
★ ĐIỂM CÓ TRỌNG SỐ HIỆN TẠI = 25,7 / 100
```

Điểm có trọng số **thấp hơn** trung bình đơn giản (25,7 < 27,9) vì bốn nhóm nặng
nhất (Canvas, Inspector/Mapping, Execution, Agent = **75 %** trọng số) đúng là bốn
nhóm yếu nhất. Nói cách khác: **những thứ đang tốt là những thứ ít quan trọng nhất.**

### 2.3 Mười hạng mục yếu nhất

| Hạng mục | Điểm |
|---|---:|
| 33 Media preview · 38 Credentials UX · 39 Advanced settings · 40 Testing node · 41 Input/output preview · 45 Previous-node data browser · 51 Run history · 64 Plan preview · 65 Diff before apply · 68 Templates · 71 Version UX | **0** |
| 3 Workflow discoverability · 12 Connection UX | 5 |
| 17 Quick create · 76 Workflow organization | 8 |
| 27 Node compactness · 63 AI suggestions · 66 Supervisor visibility | 10 |
| 1 IA · 10 Node visual hierarchy · 44 Variable picker · 84 Icons | 12 |

**Mười một hạng mục chấm 0** (33, 38, 39, 40, 41, 45, 51, 64, 65, 68, 71) — không
phải yếu, mà **không tồn tại**.

### 2.4 Mười hạng mục mạnh nhất — nền móng để xây tiếp

| Hạng mục | Điểm | Vì sao đáng giữ nguyên xi |
|---|---:|---|
| 99 Schema-driven UI | 75 | Thêm app không sửa một dòng `src/`. Đây là thứ n8n phải trả giá đắt để có |
| 73 Autosave | 70 | Debounce + trạng thái `aria-live`, chạy đúng |
| 92 Contrast (tối) | 72 | 9/9 cặp đạt AA, đo bằng máy |
| 81 Dark mode | 68 | Mặc định, nhất quán, nhìn được |
| 74 Conflict handling | 65 | `If-Match` + 409 + lối thoát rõ |
| 13 Zoom/pan/fit | 62 | React Flow dùng đúng cách |
| 47 Autocomplete | 60 | Từ máy chủ, đánh dấu `chưa publish được`, không bịa |
| 88 Empty states | 55 | Câu dẫn rõ, có hành động |
| 97 State architecture | 55 | Reducer thuần, có test, undo/redo đúng |
| 43 Expression UX | 55 | ARIA combobox đúng chuẩn, mở đúng ngữ cảnh |
| 22 Categorization | 55 | 8 category của spec + "Gần đây" |

### 2.5 Bảy điểm chặn (blocker) — không sửa thì mọi thứ khác vô nghĩa

```
B1  Node palette không biên dịch được (trừ app.*)      → 55/67 node chết
B2  15 cổng chồng một điểm 6×6px                        → không nối được dây
B3  Không có UI credential                              → 33 node chết
B4  edgeToV3 bỏ condition + đóng cứng kind:'DATA'        → rẽ nhánh chạy cả hai, tốn tiền
B5  Không có danh sách/tạo workflow                     → một-workflow-một-tài-khoản
B6  Không có trigger dùng được, không có schedule/webhook → không tự động hoá được
B7  Agent Designer ghi đè + xoá undo, không preview/diff → mất việc đang làm
```

⚠️ **B1 + B2 cộng lại có nghĩa là: hôm nay, 0/5 luồng nghiệm thu UX dựng được từ đầu
đến cuối.** Mọi việc nâng cấp thị giác đứng sau hai dòng này.

### 2.6 Chi phí danh nghĩa: ba trong bảy blocker là việc NHỎ

Ghi ra để đừng bị con số 25,2 làm nản: **B1, B2 và B4 là ba sửa nhỏ**.

| Blocker | Việc thật | Cỡ |
|---|---|---|
| B2 | thêm `position:relative` cho `.node-cong` + xếp cổng theo hàng | **S** |
| B4 | gửi thêm 2 trường trong `edgeToV3` | **S** |
| B1 | `nextNode()` ghi `type` thật ở mức trên cùng + một lần di trú bản nháp | **S–M** |

Ba việc này gỡ khoá **55/67 node** và làm rẽ nhánh chạy đúng. Chúng nên đi **trước**
mọi thảo luận về bố cục ba cột, design token hay Agent Designer.
