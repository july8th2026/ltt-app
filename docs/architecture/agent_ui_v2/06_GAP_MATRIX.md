# 06 — Ma trận khoảng cách + ma trận tái dùng (27/09/2026)

## 0. Cảnh báo về độ tin của hai cột khác nhau

| Cột | Đo thế nào | Độ tin |
|---|---|---|
| **LTT** | Playwright trên bản dựng đã chứng minh khớp mã nguồn (`01_CURRENT_UI_AUDIT.md §0`) | cao |
| **Đối thủ** | đọc tài liệu chính thức + mã nguồn repo, **không chạy thử** (xem "Giới hạn" ở 03/04/05) | trung bình |

⇒ ⛔ **Không dùng bảng này để tuyên bố "LTT kém X điểm so với n8n".** Dùng nó để trả
lời đúng một câu: *"ở mặt này, có tồn tại một mẫu hình đã được chứng minh mà LTT
chưa có không?"* Con số của đối thủ là chỉ dấu, con số của LTT là phép đo.

Điểm đối thủ quy từ thang 0–5 của `04`/`05`/`03` sang thang 100 (`×20`) để so được;
phép quy này làm mất độ phân giải và chỉ dùng để xếp hạng thô.

---

## 1. Ma trận khoảng cách theo mặt

| Mặt | LTT | CrewAI | n8n | Activepieces | Flowise | Langflow | Đích | Mẫu hình cụ thể phải học |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Node density / compactness | **10** | n/a¹ | 80 | 80 | 80 | 80 | 98 | Node = danh tính + trạng thái + **tóm tắt** cấu hình. ⛔ Không liệt kê mọi cổng thành hàng chữ |
| Connection UX (nối dây) | **5** | n/a¹ | 80 | 40 | 80 | **100** | 98 | Langflow: cổng có **màu theo kiểu** + hiện tương thích **trong lúc kéo** + chặn cạnh sai kèm lý do |
| Edge interaction | **8** | n/a¹ | 80 | 40 | 60 | 60 | 98 | n8n: toolbar trên cạnh để chèn node giữa cạnh (LTT có nút này nhưng **no-op**); React Flow `reconnectEdge` để kéo lại đầu dây |
| Data mapping | **12** | 20 | **100** | 60 | 60 | 60 | 98 | n8n: **Schema là view mặc định**, kéo một field pill vào ô → tự sinh biểu thức; pill đổi xanh dương→xanh lá khi hợp lệ |
| Variable picker | **12** | 0 | 100 | 60 | 80 | 60 | 98 | Flowise: autocomplete `{{variable}}` kiểu mention (TipTap); n8n: cây dữ liệu node trước |
| Connections / credentials | **0** | 20 | 60 | **100** | 60 | 60 | 98 | Activepieces: **"+ Tạo kết nối" là dòng đầu ngay trong dropdown của ô auth**; OAuth chạy trong popup nên form không mất state; 3 tầng CLOUD/self-managed/PLATFORM |
| Per-step config | **20** | 60 | 80 | 80 | 80 | 80 | 98 | Activepieces: step panel là **drawer**, không che canvas. Langflow: bảng field + công tắc "advanced" từng ô |
| Test một bước | **0** | 40 | 80 | **100** | 60 | 60 | 98 | Activepieces: **ép test tuần tự** nên luôn có dữ liệu mẫu để map; 4 kiểu lấy mẫu (Load/Test/Send/**Mock**) — Mock không tiêu tiền |
| Run history | **0** | 60 | 100 | 60 | 60 | 60 | 98 | n8n: danh sách execution lọc mạnh + replay trên chính canvas |
| Execution debugging | **18** | 40 | **100** | 60 | 60 | 60 | 98 | n8n: **"dirty node"** — trạng thái thứ ba "đã chạy nhưng dữ liệu đã cũ vì phía trước vừa đổi" |
| Node status vocabulary | **30** | 20 | 100 | 60 | 60 | 80 | 98 | n8n: tách **hai trục** — viền = sức khoẻ, badge góc = số lượng/chi tiết; animation khác nhau cho running vs waiting |
| Media preview trên node | **0** | 0 | 40 | 40 | 40 | 40 | 98 | ⭐ **Không ai làm tốt.** Đây là chỗ LTT có thể dẫn đầu, không phải bắt kịp |
| Node discovery / search | **30** | 40 | **100** | 60 | 60 | 80 | 98 | n8n: cây phân loại AI theo **vai trò** (Agent/Model/Memory/Tool), panel chỉ hiện Trigger khi flow còn rỗng |
| Grouping / sub-flow | **25** | 0 | 80 | 20 | 40 | 60 | 98 | n8n **Canvas Groups**: khối có tên, thu gọn theo **sở thích người xem** (không lưu vào workflow), gộp trạng thái con thành một enum |
| Templates / onboarding | **0** | 40 | **100** | 60 | 60 | 60 | 98 | n8n: 5 lối vào đều tạo ra **workflow thật**, sửa tay được ngay |
| AI sinh workflow | **40** | 20 | 80 | 20 | 60 | 40 | 98 | n8n: AI và kéo-thả là **hai lối vào cùng một đối tượng dữ liệu**. ⚠️ Flowise "Generate Agentflow" **ghi đè canvas không preview/diff** — đó là mẫu hình **phải tránh**, và LTT đang mắc đúng lỗi đó |
| Preview / diff trước khi áp | **0** | 0 | 40 | 0 | **0** | 0 | 98 | ⭐ **Không ai làm.** Cơ hội thứ hai để dẫn đầu |
| Human-in-the-loop | **20** | **0**² | 60 | 40 | 60 | 80 | 98 | Langflow: checkpoint bền vững thật. CrewAI **không có gì**, kể cả bản trả tiền |
| Information architecture | **12** | 60 | 80 | 80 | 60 | 60 | 98 | Activepieces/n8n: Flows · Runs · Connections · Templates là bốn mục cấp cao nhất |
| Typed ports (thị giác) | **30** | n/a¹ | 60 | 40 | 60 | **100** | 98 | Langflow: **màu + badge** (không phải hình dạng), hiện tương thích ngay lúc kéo |
| Light/dark | **15** | 60 | 80 | 80 | 80 | 80 | 98 | — (việc nội bộ, không cần học ai) |
| i18n | **0** | 20 | 80 | 80 | 40 | 60 | 98 | — |
| Maintainability frontend | **25** | 40 | 80 | 80 | 80 | 80 | 98 | Flowise `packages/agentflow/`: kiến trúc atoms/features, có test |

¹ CrewAI Studio không có canvas đồ thị sửa được — chấm canvas cho nó là so sai loại.
² Đã xác minh: không có widget human-in-the-loop ở bản OSS, bản Studio cộng đồng
(issue `strnad/CrewAI-Studio#75` mở từ 02/04/2025), **và cả bản AMP trả tiền** (chỉ
có hook `useHumanInTheLoop`, frontend phải tự dựng UI).

### 1.1 Ba chỗ LTT có thể DẪN ĐẦU, không phải bắt kịp

Đọc bảng trên theo chiều dọc thay vì chiều ngang, ba cột **không ai qua 40**:

1. **Media preview trên node** (tất cả ≤ 40). Không nền tảng nào trong sáu nền tảng
   coi ảnh/video/audio là công dân hạng nhất trên canvas — vì không nền tảng nào
   trong số đó là nền tảng media. LTT thì là.
2. **Preview/diff trước khi AI áp thay đổi** (tất cả ≤ 40, Flowise = 0). Flowise ghi
   đè thẳng canvas kèm một thanh tiến trình **giả**. Đây là một lỗ hổng chung của cả
   ngành, và là chỗ dễ ghi điểm nhất về lòng tin.
3. **Chi phí/GPU hiện ngay lúc dựng.** Không nền tảng nào phải trả tiền GPU theo
   bước nên không nền tảng nào giải bài này. LTT đã có `liveQuotes` chạy được trong
   bộ nhớ trình soạn — chỉ chưa vẽ ra.

⇒ Chiến lược đúng không phải "làm một n8n tiếng Việt". Mà là: **bắt kịp ở bốn mặt cơ
khí (nối dây, mapping, credentials, run history), rồi dẫn đầu ở ba mặt trên.**

---

## 2. Ma trận tái dùng

Phân loại theo đúng bảng đề bài yêu cầu: `KEEP_LTT` · `REFACTOR_LTT` ·
`USE_REACTFLOW_FEATURE` · `ADAPT_PATTERN` · `PORT_COMPONENT` · `REBUILD_NATIVE` ·
`REJECT` · `DEFER`.

### 2.1 Ràng buộc giấy phép — quyết định trước, không bàn lại

| Nguồn | Giấy phép | LTT được làm gì |
|---|---|---|
| **n8n** | Sustainable Use License | ⛔ **KHÔNG chép được một dòng nào.** LTT là SaaS thương mại. Chỉ học **ý tưởng** |
| **Activepieces** | MIT (ngoài `packages/ee/`) | ✅ **PORT được**, giữ nguyên notice bản quyền |
| **Langflow** | MIT toàn repo | ✅ PORT được |
| **Flowise** | Apache-2.0 (ngoài `enterprise/`) | ✅ PORT được, giữ notice. ⚠️ **Repo đã `archived: true`** — xem §2.4 |
| **CrewAI + CrewAI-Studio** | MIT (đã kiểm tận văn bản LICENSE) | ✅ PORT được |
| **React Flow** | MIT | ✅ đang dùng, tiếp tục dùng |

### 2.2 Bảng quyết định

| Thành phần UI | Quyết định | Vì sao |
|---|---|---|
| **Palette sinh từ registry** | `KEEP_LTT` | Thêm app không sửa `src/`. n8n phải trả giá đắt mới có được điều này |
| **Luật nối dây tải từ máy chủ** (bảng tra 17 kiểu / 180 cặp) | `KEEP_LTT` | Một nguồn sự thật, không hai bản cài đặt |
| **`editorReducer`** (undo/redo, có test) | `KEEP_LTT` | Phần tốt nhất của kiến trúc. ⚠️ sửa **một** lỗi: `replace` không được xoá `past`/`future` |
| **Đường tiền** (`Idempotency-Key` + chốt bấm đúp + `finally`) | `KEEP_LTT` | Đã nghĩ kỹ, đừng đụng |
| **Kỷ luật "không bịa khi máy chủ im"** | `KEEP_LTT` | Văn hoá hiếm; phải viết vào spec V2 để không mất khi làm lại |
| **`OBieuThuc`** (ARIA combobox) | `REFACTOR_LTT` | Hạt nhân đúng; cần thêm **lối vào không cần gõ `{{`** (nút + cây dữ liệu) |
| **`NodeKhung`** | `REFACTOR_LTT` | Giữ "một khuôn cho mọi node"; đổi **nội dung**: 3 mức mật độ, cổng có vị trí thật, tóm tắt cấu hình thay danh sách cổng |
| **`FormTuLuocDo`** | `REFACTOR_LTT` | Giữ sinh-từ-lược-đồ; thêm nhóm/tab, sắp xếp theo phụ thuộc, ô credential, tách nâng cao |
| **`PaletteV2`** | `REFACTOR_LTT` | Giữ nguồn dữ liệu; sửa icon (URL → `<img>`), mật độ thẻ, lọc "dùng được ngay" |
| **`CanvasShell`** | `REFACTOR_LTT` | Tách 740 dòng — xem `10_IMPLEMENTATION_PLAN.md` |
| **`RunV3Panel` + `RunInspector` + `RunDiff`** | `REBUILD_NATIVE` | Ba mảnh rời không thành một mặt gỡ lỗi. Dựng lại thành **một** panel dưới |
| `MiniMap` / `Controls` / `Background` | `USE_REACTFLOW_FEATURE` | Đã dùng. ⚠️ MiniMap **đang vẽ 0 node** — phải sửa hoặc tắt, không để nguyên |
| `reconnectEdge` | `USE_REACTFLOW_FEATURE` **P0** | Đổi đầu một dây mà không phải xoá-vẽ-lại. Thao tác thường gặp nhất khi sửa flow |
| `onlyRenderVisibleElements` | `USE_REACTFLOW_FEATURE` **P1** | Đòn bẩy hiệu năng rẻ nhất cho đồ thị lớn. ⚠️ **đo trước khi bật** (§3) |
| `NodeToolbar` | `USE_REACTFLOW_FEATURE` **P1** | Nút nhanh trên node đang chọn; Flowise và Langflow đều dùng |
| `parentId` + `extent:'parent'` (sub-flow) | `USE_REACTFLOW_FEATURE` **P1** | Nền cho group box thật, thay `frame` trang trí hiện tại |
| Helper lines (ví dụ chính thức) | `USE_REACTFLOW_FEATURE` **P1** | Canh thẳng khi kéo, không cần thư viện thêm |
| `useNodeConnections` / `useOnSelectionChange` | `USE_REACTFLOW_FEATURE` **P1** | Subscribe có chọn lọc thay vì lọc mảng `edges` bằng tay ⇒ bớt re-render |
| `ConnectionLineType.SmoothStep` | `USE_REACTFLOW_FEATURE` **P2** | Đường lúc kéo đang là bezier còn cạnh thật là smoothstep — hình dạng nhảy khi thả |
| `NodeResizer`, `Panel`, `ViewportPortal`, `getViewportForBounds` | `DEFER` | Chưa có nhu cầu chứng minh được |
| **Schema-view kéo-thả sinh biểu thức** (n8n) | `ADAPT_PATTERN` | ⛔ License cấm chép mã. Tự viết theo ý tưởng |
| **"Dirty node"** (n8n) | `ADAPT_PATTERN` **P1** | LTT có sổ credit thật ⇒ cảnh báo "output này đã cũ" ngăn một lớp lỗi vận hành thật |
| **Canvas Groups** (n8n) | `ADAPT_PATTERN` | Thu gọn theo **sở thích người xem**, không lưu vào workflow |
| **Hai trục trạng thái node** (n8n: viền + badge) | `ADAPT_PATTERN` **P0** | Rẻ, và là cách duy nhất nhồi đủ thông tin vào node nhỏ |
| **Panel chỉ hiện Trigger khi flow rỗng** (n8n) | `ADAPT_PATTERN` | Rào chắn onboarding rẻ — ⚠️ chỉ áp được **sau khi** LTT có trigger dùng được |
| **Cổng có màu theo kiểu + phản hồi lúc kéo** (Langflow) | `ADAPT_PATTERN` **P0** | LTT đã có 17 kiểu và 180 cặp hợp lệ ở máy chủ; chỉ thiếu lớp thị giác |
| **Tạo connection ngay trong dropdown auth** (Activepieces) | `PORT_COMPONENT` | MIT. `connection-select.tsx` + dialog OAuth làm điểm xuất phát, giữ notice |
| **3 tầng OAuth** CLOUD / self-managed / PLATFORM (Activepieces) | `ADAPT_PATTERN` **P0** | Khớp đúng hình dạng SaaS đa người dùng của LTT |
| **Mock data cho test bước** (Activepieces) | `ADAPT_PATTERN` **P0** | ⭐ Với LTT quan trọng **hơn** với Activepieces: một node GPU tốn tiền thật mỗi lần thử |
| **Ép test tuần tự** (Activepieces) | `REJECT` | Quá cứng cho workflow media nhiều nhánh. Lấy Mock data, bỏ ràng buộc tuần tự |
| **Bảng field + công tắc advanced** (Langflow) | `ADAPT_PATTERN` | Trả lời trực tiếp hạng mục 39 (Advanced settings = 0) |
| **HITL floating action bar** (Flowise `packages/observe`) | `ADAPT_PATTERN` | Trả lời hạng mục 67; ⚠️ kiểm lại giấy phép do repo đã archive |
| **"Generate Agentflow" ghi đè không preview** (Flowise) | `REJECT` ⛔ | **Đây là lỗi LTT đang mắc.** Ghi vào spec như một mẫu hình cấm |
| **Thanh tiến trình giả** (Flowise) | `REJECT` ⛔ | Nói dối người dùng về tiến độ |
| **Task→Task bằng hai hộp multiselect** (CrewAI Studio) | `REJECT` | Lộ chi tiết cài đặt runtime (async/sync) ra form |
| **`crewai flow plot`** (HTML tĩnh vis.js) | `REJECT` | LTT đã có canvas sửa được; một ảnh chỉ-đọc là bước lùi |
| **OpenTelemetry GenAI semantic conventions** (AMP) | `ADAPT_PATTERN` `DEFER` | Mô hình dữ liệu tốt cho quan sát; chưa phải việc của UI V2 |
| **Gửi trace chỉ sau khi người dùng đồng ý** (AMP) | `ADAPT_PATTERN` | Mẫu hình riêng tư đúng, rẻ để làm đúng từ đầu |
| **Thay React Flow bằng framework khác** | `REJECT` ⛔ | Xem §3 |

### 2.3 ⛔ KHÔNG đổi framework canvas — và đây là bằng chứng

Đề bài (§6) đòi bằng chứng rất mạnh mới được đề xuất thay `@xyflow/react`. Không có
bằng chứng đó. Ngược lại:

- Trong **30 API** React Flow mà một trình soạn workflow cần, LTT mới dùng **11**;
  **19** chưa dùng. Ba lỗi P0/P1 nặng nhất (`reconnectEdge` thiếu, cổng chồng nhau,
  minimap rỗng) **không** phải giới hạn của React Flow — chúng là **cách dùng**.
- LTT ghim `@xyflow/react` **12.11.2**, mới nhất là **12.12.0**. **Không một tính
  năng nào** trong bảng kiểm kê đòi bản mới hơn bản đang ghim.
- n8n dùng Vue Flow (cùng nhà xyflow); Langflow và Flowise đều dùng React Flow. Mọi
  mẫu hình cần học đều đã được ai đó làm **trên chính framework này**.

⇒ Kết luận: **khai thác React Flow trước, và còn rất nhiều chỗ để khai thác.**

### 2.4 Hai rủi ro nguồn ngoài — phải chốt trước khi dựa vào

1. 🔴 **`FlowiseAI/Flowise` hiện `archived: true`.** Quyết định `PORT` của đợt audit
   22/09 dựa trên một repo đang sống. Một repo đã lưu trữ nghĩa là không còn bản vá
   bảo mật. ⇒ Phải chốt lại với chủ dự án (câu hỏi **Q10** trong `08`) trước khi chép
   bất kỳ mã Flowise nào.
2. ⚠️ **Đợt khảo sát này không chạy thử nền tảng nào của đối thủ.** Mọi điểm ở §1 là
   từ tài liệu và mã nguồn. Nếu một quyết định lớn (ví dụ chép nguyên luồng
   connection của Activepieces) phụ thuộc vào cảm giác dùng thật, **hãy dựng thử một
   bản Activepieces cục bộ** trước khi chốt — 30 phút ở đó rẻ hơn một phase làm sai.
