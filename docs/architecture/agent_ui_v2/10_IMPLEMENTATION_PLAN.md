# 10 — Lộ trình triển khai, tiêu chí kết thúc, sổ rủi ro (27/09/2026)

> ⛔ Đây là **kế hoạch**, chưa phải lệnh thi hành. Chưa viết một dòng mã nào.
> Sau khi chủ dự án duyệt, phase đầu tiên mới được mở qua `superpowers:writing-plans`.

## 0. Nguyên tắc sắp xếp lộ trình

1. **Sửa cái chặn đường trước cái đẹp.** Không một phép đo UX nào có nghĩa khi người
   dùng chưa nối được hai bước.
2. **Mỗi phase gộp `main` được và deploy được độc lập.** Không có phase nào chỉ có
   giá trị khi phase sau xong.
3. **Đo trước khi tối ưu** (đề bài §29) và **đo trước khi tuyên bố xong** (tiêu chí
   kết thúc từng phase là lệnh chạy được, không phải câu mô tả).
4. **Việc backend tách riêng**, không giấu trong plan UI.

---

## 1. Lộ trình

| Phase | Tên | Giải hạng mục | Phụ thuộc | Cỡ |
|---|---|---|---|---|
| **UI-0** | 🔴 Bốn lỗi P0 cơ khí | 12, 17, 11 | — | **S** |
| **UI-1** | Kiến trúc thông tin — Automation Studio | 1–6, 51, 68, 76 | Q1 | L |
| **UI-2** | Design system + token + theme sáng | 77–88, 92 | — | M |
| **UI-3** | Tách `CanvasShell` | 95, 96, 98 | UI-0 | M |
| **UI-4** | Node UX V2 (mật độ, trạng thái, media) | 9, 10, 27–34 | UI-2, UI-3 | L |
| **UI-5** | Inspector V2 + Connections | 35–42, 38 | Q3, Q4 | L |
| **UI-6** | Data picker + mapping | 43–49 | UI-5 | L |
| **UI-7** | Execution UX + Runs | 50–60 | UI-1, UI-3 | L |
| **UI-8** | Agent Designer + preview/diff | 61–67 | UI-3 | M |
| **UI-9** | Templates + onboarding | 7, 68–72 | UI-1 | M |
| **UI-10** | i18n + trợ năng + mobile | 89–94, i18n | tất cả | M |
| **UI-11** | Nghiệm thu UX + hồi quy | — | tất cả | M |

⚠️ **UI-2 chạy song song được với UI-0/UI-1** (chạm tệp khác). Các phase còn lại tuần
tự theo cột "phụ thuộc". Nếu chạy nhiều làn, ⛔ **không hai làn cùng sửa `canvas.css`
hay `CanvasShell.tsx`** — đó đúng là hình dạng xung đột mà luật một-tệp-một-chủ sinh ra để tránh.

---

## 2. Kế hoạch ở mức TỆP

### UI-0 — Bốn lỗi P0 cơ khí

| Tệp | Việc |
|---|---|
| `frontend/agent-canvas/src/editorState.ts` | `nextNode()`: ghi `type` **thật** ở mức trên cùng (`core.if`, `app.video.generate`), giữ `data.tool` làm bản mirror cho render — **đúng hình dạng `ke_hoach_v3._data_canvas` đã dùng**. Gỡ 4 khoá chết `fanout`/`max_retry`/`on_fail`/`verify` |
| `frontend/agent-canvas/src/workflowApi.ts` | `edgeToV3()`: gửi `kind` thật (`DATA`/`CONTROL`/`ERROR`) + `condition`. `edgeFromV3()`: đọc ngược lại |
| `frontend/agent-canvas/src/canvas.css` | `.node-cong { position: relative }` + xếp cổng theo hàng; `--handle-size:12px`, vùng bấm 24px |
| `frontend/agent-canvas/src/nodes/NodeKhung.tsx` | mỗi `Handle` neo vào hàng của chính nó |
| `frontend/agent-canvas/src/CanvasShell.tsx` | nối `data.onInsert` cho `CanvasEdgeView` **hoặc gỡ nút `+`** — ⛔ không để một nút no-op |
| `platform_core/workflow/di_tru_m1.py` *(hoặc một bước di trú mới)* | nâng bản nháp đang lưu: `type:'tool'` → `type` thật. ⚠️ **Có dữ liệu thật trên production** |
| `tests/` + `frontend/agent-canvas/tests/` | bánh cóc: (a) mọi node palette biên dịch được; (b) `edgeToV3` giữ `condition`+`kind`; (c) cổng của một node ≥2 cổng có toạ độ **khác nhau** |

**Tiêu chí kết thúc UI-0** — lệnh chạy được, không phải mô tả:

```
□ Kịch bản Playwright: thêm MỘT node core.*  → Chạy  → KHÔNG có `node_khong_ton_tai`
□ Kịch bản Playwright: thêm MỘT node piece.* → Chạy  → KHÔNG có `node_khong_ton_tai`
□ Kịch bản Playwright: kéo cổng image_keys → image_key → data-edge-count = "1"
□ Phép kiểm DOM: mọi node ≥2 cổng cùng phía ⇒ số vị trí khác nhau == số cổng
□ Phép kiểm: core.if hai nhánh ⇒ CHỈ nhánh khớp điều kiện chạy (test động cơ)
□ Di trú: mọi bản nháp production cũ vẫn mở được VÀ biên dịch được
□ Test nhắm xanh -> gộp `main` -> `pre-commit run --all-files`
```

### UI-3 — Tách `CanvasShell` (959 dòng, `Editor()` 740 dòng, 33 state)

```text
features/editor/
├── EditorShell.tsx            bố cục + phím tắt toàn cục
├── WorkflowHeader.tsx         tên · trạng thái lưu · BÁO GIÁ · Test · Chạy
├── LeftRail.tsx               công cụ (có NHÃN CHỮ, không chỉ biểu tượng)
├── StepLibrary/               (PaletteV2 refactor)
├── WorkflowCanvas.tsx         ReactFlow + nodeTypes/edgeTypes + tương tác
├── StepInspector/             (FormTuLuocDo + OBieuThuc + ô kết nối)
├── ExecutionPanel/            (RunV3Panel + RunInspector + RunDiff dựng lại)
├── CommandPalette.tsx
├── ContextMenu.tsx
└── hooks/
    ├── useWorkflowDocument.ts  nạp · autosave · xung đột
    ├── useCanvasSelection.ts
    ├── useWorkflowRun.ts       publish · tạo run · SSE + lùi dần · huỷ · chạy lại
    ├── useLiveQuote.ts         một request cho cả đồ thị (GIỮ bánh cóc hiện có)
    ├── useStepLibrary.ts
    └── useExpressionSuggest.ts
```

⛔ **Không ép theo đúng cây này nếu khi làm thấy phương án tốt hơn** — nó là điểm
xuất phát, không phải hợp đồng. Hai điều **bắt buộc**: `editorReducer` giữ nguyên
(đã có test, là phần tốt nhất), và không tệp nào mới vượt ~250 dòng.

**Tiêu chí kết thúc UI-3:**

```
□ Không tệp nào trong features/editor/ vượt 250 dòng
□ EditorShell giữ < 8 useState
□ Mọi test frontend hiện có vẫn xanh, KHÔNG sửa test để nó xanh
□ Kịch bản Playwright lõi (tạo → thêm bước → nối → cấu hình → lưu → chạy) xanh
□ Không đổi một hành vi backend nào (so ảnh chụp request trước/sau)
```

### UI-2 — Design system

| Tệp | Việc |
|---|---|
| `frontend/agent-canvas/src/tokens.css` *(mới)* | token phạm vi `.canvas-shell`; **import** token nền tảng, ⛔ không khai lại |
| `canvas.css` → `styles/` | tách theo component; **xoá 49 lớp chết**; gộp 5 khối `@media 640px` thành **một** |
| toàn bộ `src/` | 482 hex cứng → token. Đích ≥ 95 % token hoá |

```
□ Đếm hex cứng trong frontend/agent-canvas/src/**.css  ≤ 25   (hiện 482)
□ Đúng MỘT khối @media (max-width:640px)               (hiện 5)
□ 0 lớp CSS không được tham chiếu từ .tsx              (hiện 49)
□ theme-light: 0/N ô giữ nền tối                       (hiện 7/11)
□ Kiểm tương phản tự động: 100 % đạt AA ở CẢ hai theme
□ Không chuỗi nào dùng cỡ chữ < 12px                   (hiện 5 chỗ)
```

### UI-5 / UI-6 / UI-7 / UI-8 — tệp chính

| Tệp | Đổi thành |
|---|---|
| `inspector/FormTuLuocDo.tsx` | tab; ẩn trường phụ thuộc cho tới khi cha có giá trị; tách nâng cao; nhãn người từ lược đồ |
| `inspector/OBieuThuc.tsx` | **giữ hạt nhân**; thêm nút "chèn dữ liệu" + nhận thả từ data picker |
| `inspector/OKetNoi.tsx` *(mới)* | ô chọn kết nối + "+ Tạo kết nối" là **dòng đầu dropdown** (luồng Activepieces) |
| `inspector/DataPicker.tsx` *(mới)* | cây Trigger / Đầu vào / Bước trước / Vòng lặp / Biến |
| `nodes/NodeKhung.tsx` | 3 mức mật độ; hai trục trạng thái; tóm tắt cấu hình; cổng có vị trí |
| `nodes/MediaPreview.tsx` *(mới)* | thumbnail lazy, đếm artifact, thời lượng |
| `CanvasEdgeView.tsx` | nhãn nhánh; màu theo kiểu cổng; `reconnectEdge` |
| `ExecutionPanel/Timeline.tsx` *(mới)* | dòng thời gian theo bước, có **tên bước** và **dấu thời gian** |
| `ExecutionPanel/StepRunInspector.tsx` | 12 trường của `09 §8` — dữ liệu **đã có** trong `RunV3` |
| `agent/DesignerPreview.tsx` *(mới)* | diff thêm/sửa/xoá · kết nối cần · báo giá · câu hỏi treo |
| `editorState.ts` | 🔴 `replace` phải đẩy trạng thái cũ vào `past` (hôm nay xoá sạch undo) |

---

## 3. Kế hoạch nâng điểm

| Nhóm | Hiện | Sau UI-0 | Đích | Mở khoá bởi |
|---|---:|---:|---:|---|
| Canvas / Workflow Building | 28,5 | ~55 | 98 | UI-0, UI-4 |
| Inspector / Data Mapping | 21,3 | 21,3 | 98 | UI-5, UI-6 |
| Execution / Debug | 26,9 | 26,9 | 98 | UI-7 |
| Agent UX | 13,6 | 13,6 | 98 | UI-8 |
| Information Architecture | 26,4 | 26,4 | 98 | UI-1, UI-9 |
| Design System | 33,9 | 33,9 | 98 | UI-2 |
| Accessibility | 40,0 | ~50 | 98 | UI-0 (vùng bấm), UI-10 |
| Frontend Maintainability | 38,8 | 38,8 | 98 | UI-3 |
| **Có trọng số** | **25,7** | **~32** | **98** | |

⚠️ **98 là đích, không phải lời hứa.** Theo đúng luật ở `02 §0`, một hạng mục chỉ
được chấm 98 khi có **bằng chứng** cho cả sáu điều kiện. Ba hạng mục hôm nay chưa
thấy đường tới 98 **trong phạm vi UI**, và phải nói thẳng:

| Hạng mục | Vì sao không đạt 98 chỉ bằng công việc UI |
|---|---|
| 33 Media preview | cần cửa máy chủ trả thumbnail/thời lượng cho artifact |
| 40 Testing node | cần cửa chạy-một-bước + chế độ mock ở backend |
| 51 Run history | cần cửa liệt kê run theo workflow (hiện **không tồn tại**) |

⇒ Chúng nằm trong bảng "cần backend" ở `09 §13`, và **trần điểm thật của riêng plan
UI này thấp hơn 98** cho tới khi các cửa ấy có. Nói trước còn hơn để lộ ra ở nghiệm thu.

---

## 4. Chiến lược kiểm thử

**Unit** (`vitest`) — `editorReducer` (kể cả `replace` giữ undo) · `edgeToV3`/`edgeFromV3`
round-trip có `condition`+`kind` · `nextNode` sinh `type` đúng · `noiDuoc` · `locPalette`
· `dangGoBieuThuc` · sinh form từ lược đồ (bao gồm ẩn trường phụ thuộc).

**Integration** (`@testing-library/react`) — thêm bước · nối · cấu hình · lưu ·
publish · chạy · ô kết nối · data picker chèn biểu thức.

**Playwright** (`tests/browser/`) — năm luồng UX-1…UX-5 của đề bài. ⚠️ Hôm nay **0/5
dựng được**; mỗi luồng trở thành một phép kiểm chạy được khi phase tương ứng xong.

**Visual regression** — ảnh chụp Playwright trong kho (Q13), ⛔ không SaaS. Bộ tối
thiểu: canvas rỗng · palette · node ba mức mật độ · inspector · panel chạy · theme
sáng · theme tối · mobile 390.

**Hiệu năng** — kịch bản sinh 10/50/100/200 node, đo thời gian dựng, fps lúc pan,
độ trễ gõ trong Inspector. ⚠️ **Chạy TRƯỚC UI-4** để có mốc nền.

### 4.1 Đo nghiệm thu UX — số phải thu cho mỗi luồng

Với mỗi luồng UX-1…UX-5, ghi: **thời gian dựng · số cú bấm · số lần đổi panel · số
ký tự gõ · số lỗi gặp · số chỗ bối rối · thời gian gỡ một lỗi cố tình gieo vào.**

⚠️ Mốc nền hôm nay là **"không dựng được"** cho cả 5 — nên con số đầu tiên đo được
sau UI-0 đã là một cải thiện vô hạn. Đừng dùng nó để tuyên bố thành công; dùng nó
làm **mốc 0 thật** để các phase sau so.

---

## 5. Sổ rủi ro

| # | Rủi ro | Loại | Xác suất | Tác động | Giảm thiểu |
|---|---|---|---|---|---|
| R1 | Di trú `type:'tool'` làm hỏng bản nháp production | **hồi quy** | TB | **cao** | đọc-hiểu-hai-hình-dạng trước, chỉ ghi khi lưu; ảnh chụp trước/sau trên bản sao CSDL thật |
| R2 | Sửa cổng chồng điểm làm vỡ bố cục node hiện có | hồi quy | cao | TB | visual regression ngay từ UI-0 |
| R3 | Gửi `condition`/`kind` làm run **đổi hành vi** trên workflow đang chạy | **hồi quy** | TB | **cao** | 🔴 workflow đang chạy hôm nay chạy CẢ hai nhánh; sửa xong chúng sẽ chạy một nhánh. **Đây là sửa đúng, nhưng là một thay đổi hành vi** ⇒ phải báo trước cho khách đang dùng |
| R4 | Tách `CanvasShell` làm mất một hành vi tinh tế không có test | hồi quy | cao | TB | tách theo từng bước, mỗi bước một commit, test nhắm sau mỗi bước |
| R5 | OAuth chặn UI-5 vì lý do pháp lý/vận hành | **phạm vi** | TB | cao | Q4 phải có trả lời **trước** khi mở UI-5 |
| R6 | `onlyRenderVisibleElements` phá tìm kiếm/trình đọc màn hình | kỹ thuật | TB | TB | đo trước, bật sau, kiểm a11y kèm |
| R7 | Đích 98 không đạt được vì thiếu cửa backend | **phạm vi** | **cao** | TB | đã nói thẳng ở §3; tách bảng "cần backend" ở `09 §13` |
| R8 | Phình phạm vi: UI-1 kéo theo chia sẻ, phân quyền, marketplace | **phạm vi** | cao | cao | UI-1 chỉ làm điều hướng + 5 trang; mọi thứ khác vào sổ chờ |
| R9 | Chép mã Flowise từ repo đã archive | bảo mật | thấp | TB | Q10 phải trả lời trước |
| R10 | Hai làn song song cùng sửa `canvas.css` / `CanvasShell.tsx` | vận hành | TB | TB | một tệp một chủ; UI-2 và UI-3 ⛔ không chạy song song |
| R11 | Đo hiệu năng sau khi tối ưu ⇒ không biết có cải thiện không | **đo lường** | TB | TB | mốc nền TRƯỚC UI-4, bắt buộc |
| R12 | Sửa nhãn node phải đổi `ToolSpec` của 12 app | phạm vi | cao | thấp | thêm `title` ngắn là trường **tuỳ chọn**, lùi về `description` cắt ngắn khi vắng |

---

## 6. Tiêu chí kết thúc tổng thể

```
□ 5/5 luồng UX-1..UX-5 dựng được từ đầu đến cuối bằng GIAO DIỆN, có kịch bản Playwright
□ 0 lỗi P0/P1 còn mở trong bảng 30 phát hiện của 01 §11
□ Điểm có trọng số ≥ 90 (98 cho các mặt KHÔNG bị chặn bởi backend — xem §3)
□ Không hồi quy hành vi backend (so ảnh chụp request)
□ WCAG 2.2 AA: tương phản, vùng bấm ≥24px, bàn phím, focus — có kiểm tự động
□ i18n: 0 chuỗi cứng; Canvas theo đúng locale nền tảng
□ Không tệp frontend nào > 250 dòng
□ Hiệu năng: 200 node pan/zoom 60fps, gõ Inspector không giật — CÓ SỐ, có mốc nền
□ Bộ ảnh visual regression xanh ở cả hai theme + mobile
```

⛔ **Không dùng "trông ổn rồi" làm tiêu chí kết thúc cho bất kỳ phase nào.**
