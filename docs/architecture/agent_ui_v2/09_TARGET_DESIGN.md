# 09 — Thiết kế đích: IA · design system · canvas · node · inspector · mapping · run · agent

> Tài liệu spec. Mọi con số "hiện tại" trong đây trỏ về `01_CURRENT_UI_AUDIT.md`.

## 1. Kiến trúc thông tin đích

```text
LTT Automation Studio                                    app.lttstudios.com/agent
│
├── Workflows          /agent/workflows          danh sách · tìm · nhân bản · lưu trữ
│   └── Editor         /agent/workflows/{id}     ← Canvas (bố cục §4)
├── Runs               /agent/runs               lịch sử MỌI lượt chạy · lọc · mở lại
│   └── Run detail     /agent/runs/{id}          canvas chỉ-đọc + timeline + dữ liệu bước
├── Templates          /agent/templates          mẫu chạy được, mở ra là một workflow THẬT
├── Connections        /agent/connections        credential của khách (P0 — hiện không tồn tại)
├── Agents             /agent/agents             Agent Designer + lịch sử bản nháp AI sinh
└── Settings           /agent/settings           theme · ngôn ngữ · mặc định
```

**Luật từ vựng — một khái niệm, một từ, ở mọi nơi.** Hôm nay `block`/`node`/`công cụ`
dùng lẫn lộn trên cùng một màn hình (`01 §3.3`).

| Khái niệm | Từ dùng (vi) | Từ dùng (en) | ⛔ Không dùng |
|---|---|---|---|
| một bước trong workflow | **bước** | **step** | block, node, công cụ, tool |
| loại bước trong thư viện | **loại bước** | **step type** | node type, tool |
| đồ thị người dùng dựng | **workflow** | **workflow** | flow, đồ thị, canvas |
| một lần thực thi | **lượt chạy** | **run** | execution, job |
| khoá của khách tới dịch vụ ngoài | **kết nối** | **connection** | credential, khoá |

⚠️ *"node"* vẫn dùng được trong **mã nguồn và tài liệu kỹ thuật** — luật này áp cho
**chuỗi hiển thị**. Đó cũng là bài học của Activepieces: giữ thuật ngữ kỹ thuật ở
nơi kỹ thuật, đừng bịa từ mới, nhưng đừng để ba từ ra cùng một màn hình.

## 2. Design system V2 — token

⭐ **Không dựng bộ token thứ hai.** `server/static/ltt.css` đã có một bộ tốt và có kỷ
luật (đo bằng axe, có ghi chú lý do). Canvas hôm nay mới token hoá ~18 % (482 hex
cứng / 105 `var()`). Việc của V2 là **dùng bộ đã có**, và chỉ thêm những token mà
canvas thật sự cần và nền tảng chưa có.

**Đã có ở `ltt.css`, chỉ việc dùng:** `--surface-*` · `--text-*` · `--brand-*` ·
`--status-{success,warning,danger,info}[-soft|-border]` · `--radius-*` · `--space-1..8`
· `--fs-caption..display` · `--lh-*` · `--shadow-*` · `--focus-ring` · `--motion-fast|normal`
· `--font` · `--mono`.

**Cần THÊM cho canvas** (đặt trong một khối `:root` có phạm vi `.canvas-shell`, ⛔
không sửa `:root` toàn cục — `ltt.css` dùng chung cho 14 app):

```css
/* Kiểu cổng — MỘT màu cho MỘT kiểu, dùng chung cho handle, dây, và nhãn */
--port-text · --port-image · --port-video · --port-audio · --port-file
--port-json · --port-number · --port-boolean · --port-control · --port-event
--port-artifact-ref · --port-model-ref · --port-connection-ref · --port-secret-ref
--port-workflow-ref · --port-document · --port-any        /* 17 kiểu, khớp he_kieu */

/* Trạng thái bước — HAI trục (bài học n8n) */
--step-border-idle · -running · -waiting · -succeeded · -failed · -skipped · -stale
--step-badge-bg · --step-badge-fg

/* Hình học canvas */
--step-w-compact: 200px · --step-w-normal: 280px · --step-w-expanded: 360px
--step-radius · --step-gap-x: 320px · --step-gap-y: 160px
--handle-size: 12px · --handle-hit: 24px     /* WCAG 2.2 AA 2.5.8 */
--edge-w · --edge-w-selected · --grid-gap: 20px
--z-canvas · --z-edge-label · --z-node-toolbar · --z-drawer · --z-modal
```

🔴 **`--handle-hit: 24px` không thương lượng.** Cổng hiện tại là **6×6 px**
(`01 §2.2`) — dưới ngưỡng WCAG 2.2 AA và là một nửa nguyên nhân của P0-2.

## 3. Node UX V2

### 3.1 Ba mức mật độ

| Mức | Rộng | Khi nào | Nội dung |
|---|---|---|---|
| **Compact** | 200px | zoom < 0.6, hoặc người dùng chọn | icon · tên · huy hiệu trạng thái |
| **Normal** (mặc định) | 280px | zoom bình thường | + tóm tắt cấu hình 1 dòng · cổng · chi phí |
| **Expanded** | 360px | node đang chọn, hoặc có media | + preview media · tóm tắt kết quả lượt chạy |

⇒ Trả lời trực tiếp hạng mục 9 (Workspace density = 15) và 27 (Node compactness = 10).
Node hôm nay **456 px** và liệt kê **mọi** cổng thành hàng chữ.

### 3.2 Node chỉ mang 5 thứ

```text
┌────────────────────────────────────┐
│ ⬤ Tạo Video Seedance      ● Xong  │  ← danh tính + TRẠNG THÁI (viền + badge)
│ Seedance · 1080p · 8s             │  ← TÓM TẮT cấu hình, KHÔNG phải form
│ ◀ prompt                 video ▶  │  ← cổng CÓ VỊ TRÍ THẬT, màu theo kiểu
│ [▭ thumbnail]                     │  ← media (chỉ ở Expanded / sau khi chạy)
│ 12 credit · 1m 04s                │  ← tóm tắt lượt chạy
└────────────────────────────────────┘
```

⛔ Không nhồi field vào node. ⛔ Không hiện `app.video.generate@1` cho người dùng
cuối (chuyển vào tooltip/inspector). ⛔ Không dùng `description` làm tiêu đề.

### 3.3 Hai trục trạng thái (chép ý tưởng n8n)

- **Viền** = sức khoẻ: idle · running · waiting · succeeded · failed · skipped ·
  **stale**.
- **Badge góc** = định lượng: số item, lỗi cấu hình (khác lỗi thực thi), thiếu kết nối.
- **Animation khác nhau** cho `running` và `waiting` — không chỉ khác màu. Người dùng
  phải phân biệt được "đang tính" với "đang chờ người duyệt" từ xa.

⭐ **`stale` đáng giá riêng với LTT.** LTT có sổ credit thật; một người xem output cũ
mà tưởng là mới sẽ ra quyết định sai trên tiền thật. Đây là mẫu hình duy nhất trong
cả đợt khảo sát mà giá trị của nó **cao hơn** ở LTT so với ở nơi sinh ra nó.

### 3.4 Media node — chỗ LTT dẫn đầu

Không nền tảng nào trong sáu nền tảng khảo sát được >40/100 ở mặt này (`06 §1.1`).

```
Normal    : huy hiệu "3 ảnh · 12s · 1080p"   (không tải ảnh)
Hover     : preview nhỏ, tải chậm (lazy)
Expanded  : thumbnail 16:9, đếm số artifact
Inspector : xem đầy đủ, phát video/audio, tải về
```

⛔ Mặc định **không** full-size preview trên mọi node — đó là cách làm chết canvas
30 node.

## 4. Bố cục Editor

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Workflows │ Tên workflow ▾ │ Đã lưu │ ~12 credit │ [Test] [Chạy ▶] │
├────┬──────────────┬───────────────────────────────┬──────────────────┤
│ R  │ Thư viện     │                               │ Inspector        │
│ a  │ bước         │          Canvas               │  Cấu hình        │
│ i  │ · tìm        │                               │  Dữ liệu vào     │
│ l  │ · nhóm       │                               │  Tuỳ chọn        │
│    │ · gần đây    │                               │  Kết quả         │
│    │ · dùng ngay  │                               │  Chạy thử        │
├────┴──────────────┴───────────────────────────────┴──────────────────┤
│ ▲ Lượt chạy  │ Timeline │ Nhật ký │ Dữ liệu        (kéo cao/thấp)    │
└──────────────────────────────────────────────────────────────────────┘
```

- Thư viện và Inspector là **cột cố định** (hôm nay là ngăn kéo **đè** canvas).
- Panel dưới **thu gọn mặc định**, bung khi có lượt chạy.
- 🔴 **Báo giá hiện Ở THANH TRÊN, trước khi bấm Chạy.** Dữ liệu (`liveQuotes`) đã có
  sẵn trong bộ nhớ trình soạn; hôm nay người dùng được mời tiêu tiền mà không thấy
  một con số nào (`01 §6`).
- Ngăn kéo "Chạy workflow" hiện chứa 7 lệnh xem/sửa — **chuyển hết** về rail và
  command palette. Panel Chạy chỉ nói về chạy.

## 5. Canvas V2 — phân loại P0/P1/P2

| Tính năng | Ưu tiên | Ghi chú |
|---|---|---|
| Cổng có vị trí thật, hit 24px, màu theo kiểu | **P0** | sửa B2 |
| Phản hồi khi kéo dây: hợp lệ/không + **lý do** | **P0** | hôm nay thất bại im lặng |
| `reconnectEdge` — kéo lại đầu dây | **P0** | React Flow có sẵn |
| Nhãn nhánh trên cạnh (`true`/`false`/tên nhánh) | **P0** | sửa B4 |
| Bước xếp mặc định > chiều rộng node | **P0** | hôm nay 430 < 456 ⇒ chồng nhau |
| Nút "+" trên cạnh **hoạt động** (hoặc gỡ bỏ) | **P0** | hôm nay là no-op |
| Minimap vẽ đúng node (hoặc tắt) | **P1** | hôm nay vẽ 0/3 node |
| Quick-add: kéo từ cổng ra khoảng trống → picker | **P1** | |
| Helper lines canh thẳng | **P1** | ví dụ chính thức React Flow |
| `NodeToolbar` nút nhanh trên node chọn | **P1** | |
| Group box thật (`parentId` + `extent:'parent'`) | **P1** | thay `frame` trang trí |
| Thu gọn group, gộp trạng thái con thành 1 enum | **P1** | ý tưởng n8n Canvas Groups |
| Auto-layout thật (dagre/elk) | **P1** | hôm nay "Tự xếp" chỉ xếp lưới 4 cột |
| `onlyRenderVisibleElements` | **P1** | ⚠️ **đo trước khi bật** |
| Tìm bước trên canvas (⌘F) | **P1** | |
| `ConnectionLineType.SmoothStep` | **P2** | khớp hình dạng cạnh thật |
| Fit-to-selection, `getNodesBounds` | **P2** | |
| `NodeResizer`, `Panel`, `ViewportPortal` | **P2** | chưa có nhu cầu chứng minh được |

## 6. Inspector V2

```text
Cấu hình   ← bắt buộc + kết nối. Trường phụ thuộc ẨN cho tới khi cha có giá trị
Dữ liệu vào ← cây dữ liệu bước trước (kéo-thả sang ô) + dữ liệu mẫu
Tuỳ chọn   ← nâng cao: retry · timeout · xử lý lỗi · đồng thời
Kết quả    ← lược đồ đầu ra + kết quả thật của lượt chạy gần nhất
Chạy thử   ← test MỘT bước, có chế độ Mock (không tiêu credit)
```

Dùng **tab**, không dùng section dài — 15 ô trong một cột phẳng là hình dạng hôm nay
và nó thất bại đo được (`01 §5`).

Bốn luật bắt buộc:

1. 🔴 **Trường phụ thuộc phải ẩn, không phải hiện dưới dạng xám.** Hôm nay một node
   vừa thả xuống hiện **ba** dropdown "— chưa có lựa chọn nào —" cùng lúc. Đúng
   hành vi: hiện `model` trước; `resolution`/`duration`/`aspect_ratio` chỉ xuất hiện
   sau khi `model` có giá trị.
2. 🔴 **Ô "kết nối" nằm ngay trong tab Cấu hình, và tạo được kết nối mới tại chỗ** —
   "+ Tạo kết nối" là **dòng đầu của chính dropdown** (chép luồng Activepieces, MIT).
   OAuth mở **popup**, không điều hướng cả trang, để form không mất trạng thái.
3. **Nhãn là nhãn người, không phải tên tham số máy.** `aspect_ratio` → "Tỉ lệ khung
   hình". Nguồn: một trường `label` mới trong lược đồ máy chủ — ⛔ không phải một
   bảng tra trong frontend (đó chính là thứ `test_967` đang đếm hàng chết).
4. **Sticky action ở chân panel**: Chạy thử · Xoá bước · Nhân bản.

## 7. Data picker (P0)

```text
Dữ liệu dùng được          [tìm…]
├── Trigger
│   └── event              event
├── Đầu vào workflow
├── Bước trước
│   ├── Tạo ảnh AI
│   │   ├── image_keys     image[]    ← kéo sang ô, hoặc bấm để chèn
│   │   └── prompt         text
│   └── Cắt clip
├── Vòng lặp               item · index
└── Biến (state)
```

- Kéo một mục vào ô ⇒ **tự sinh biểu thức**, người dùng không gõ cú pháp.
- Pill đổi màu khi thả hợp lệ (ý tưởng n8n, rẻ và hiệu quả).
- Kiểu hiện ngay cạnh tên; mục **không tương thích** với ô đang focus bị làm mờ, kèm
  lý do khi hover.
- `OBieuThuc` hiện tại **giữ nguyên** làm chế độ nâng cao cho người muốn gõ tay.

⚠️ Đây là hạng mục 45 = **0** hôm nay, và là mặt mà n8n bỏ xa mọi đối thủ.

## 8. Execution UX V2

```text
┌ Canvas ──────────────────────────────────────────────┐
│  (node sáng dần theo tiến trình, viền theo trạng thái)│
├──────────────────────────────────────────────────────┤
│ Lượt chạy #128 · RUNNING · 8/12 credit · 1m 04s      │
│ ┌ Timeline ───────────────────────────────────────┐  │
│ │ ▓▓▓ Lấy dòng Sheet      0.4s   0 credit   Xong │  │
│ │ ▓▓▓▓▓▓▓ Tạo ảnh AI      12s    3 credit   Xong │  │
│ │ ▓▓▓▓ Tạo video          …      ~8        Đang  │  │
│ │ ░░░ Đăng YouTube        —      —         Chờ   │  │
│ └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

Bấm một bước trong timeline ⇒ mở **Node Execution Inspector**:

```
Trạng thái · Đầu vào · Đầu ra · Nhật ký · Lỗi · Lần thử ·
Thời lượng · Chi phí · Tài nguyên (GPU) · Lý do chờ ·
Lịch sử thử lại · Artifact (xem/tải)
```

**Mọi trường trong danh sách trên đã có sẵn trong `RunV3`** (`01 §6.1`) — hôm nay
chúng bị đổ thành một cây JSON thô. Đây là việc **dây nối**, không phải tính năng mới.

Bắt buộc sửa:
- ⛔ Không hiện `node_id` thô (`nmujtmc1b-0`) — hiện tên bước.
- Nhật ký sự kiện phải có **dấu thời gian** (`created_at` đã có trong dữ liệu).
- Lỗi phải là câu người đọc được, không phải `node_khong_ton_tai: core.set`; mã máy
  đi vào phần "chi tiết kỹ thuật" gập lại.

## 9. Agent Designer V2

```text
Người dùng mô tả mục tiêu
        ↓
Agent đề xuất workflow
        ↓
┌ XEM TRƯỚC ──────────────────────────────────┐
│ + Thêm 4 bước    ~ Sửa 1 bước   − Xoá 0     │
│ Cần kết nối: Google Sheets, YouTube         │
│ Chi phí ước tính: ~14 credit mỗi lượt       │
│ Câu hỏi còn treo: chạy lúc mấy giờ?         │
│                      [Huỷ]  [Áp dụng]       │
└─────────────────────────────────────────────┘
        ↓ (chỉ sau khi bấm Áp dụng)
Canvas đổi — VÀ HOÀN TÁC ĐƯỢC
```

🔴 **Ba luật cứng, cả ba đều là sửa lỗi đang có:**

1. **Không bao giờ ghi đè canvas mà không có xem-trước.** Hôm nay `soanBangAI` gọi
   thẳng `dispatch({type:'replace'})`.
2. **Áp dụng phải hoàn tác được.** Hôm nay `replace` **xoá sạch `past`/`future`** ⇒
   Ctrl+Z không cứu được. Sửa reducer để `replace` đẩy trạng thái cũ vào `past`.
3. **Agent Designer chỉ tạo/sửa workflow, không chạy gì cả.** (Đã đúng — giữ nguyên.)

⭐ Đây đồng thời là cơ hội dẫn đầu: **không một nền tảng nào trong sáu nền tảng khảo
sát có bước preview/diff** (`06 §1.1`); Flowise ghi đè thẳng kèm thanh tiến trình giả.

## 10. i18n

- ⛔ Không chuỗi tiếng Việt cứng trong `src/` — hôm nay có **428**.
- Canvas phải theo đúng locale của nền tảng. Bằng chứng hôm nay: nền tảng ở `/en/`,
  Canvas vẫn tiếng Việt toàn bộ (`01 §8.4`).
- Nhãn node/tham số đến **từ máy chủ** (đã qua `platform_core.i18n`), không từ một
  bảng trong frontend.
- Bố cục phải chịu được nhãn dài (tiếng Đức/Việt dài hơn tiếng Anh ~30 %).
- ⚠️ Còn 29/67 mô tả node là tiếng Anh nguyên văn từ catalog Activepieces — cần một
  quyết định riêng (câu hỏi **Q9** trong `08`).

## 11. Mobile

**Khuyến nghị: chỉ-xem, và nói thẳng ra.** Dựng workflow trên màn 390px không đáng
chi phí; nhưng **xem lượt chạy** trên điện thoại thì rất đáng — đó là lúc người dùng
thật sự cầm điện thoại.

```
Workflows  : xem được, mở được
Runs       : ⭐ đầy đủ — đây là mặt QUAN TRỌNG NHẤT trên mobile
Run detail : timeline + dữ liệu bước + duyệt bước chờ người
Editor     : chỉ-xem, có banner nói rõ, nút "Mở trên máy tính"
Connections: xem được, không sửa
```

Bắt buộc sửa: chọn tab "Canvas" hiện **Inspector** (`01 §8.5`), và trạng thái chỉ-xem
hiện nay **không nói gì** vì nhãn bị `display:none`.

## 12. Trợ năng — đích WCAG 2.2 AA

| Hạng mục | Hôm nay | Đích |
|---|---|---|
| Tương phản chữ (tối) | ✅ 9/9 đạt AA | giữ, có kiểm tự động |
| Tương phản chữ (sáng) | ⚠️ chữ đạt, **bề mặt sai** (7/11 ô nền tối) | một hệ bề mặt duy nhất |
| Vùng bấm | ❌ cổng 6×6px | ≥ 24×24 (2.5.8) |
| Cỡ chữ nhỏ nhất | ❌ 9px | ≥ 12px |
| Bàn phím | ⚠️ có phím tắt, không tài liệu | đủ phím + bảng phím tắt (`?`) |
| Focus | ⚠️ chưa kiểm | thứ tự tab đúng, bẫy focus trong drawer/modal |
| Trình đọc màn hình | ✅ phủ rộng | sửa `aria-pressed={true}` đóng cứng |
| Reduced motion | ✅ đã có | giữ |
| Nối dây bằng bàn phím | ❌ không có | chọn cổng → Enter → chọn đích |

## 13. Ranh giới với backend — ⛔ không được vượt

- Không tạo API mới khi cửa hiện có đủ.
- Không nhân bản metadata node ở frontend.
- Không viết cứng tên app/connector/kiểu tương thích.
- Không đi vòng `NodeDefinition` / `ToolSpec` / versioning.
- Frontend tiếp tục **schema-driven**: thêm một app không sửa một dòng nào trong `src/`.

**Những gì V2 cần backend thêm** (đã tách riêng để chủ dự án cân nhắc):

| Cần | Cho hạng mục | Cỡ |
|---|---|---|
| Cửa liệt kê run theo workflow | Run history (51 = 0) | M |
| CRUD credential của khách + OAuth callback | Connections (38 = 0) | L |
| Trường `label` (nhãn người) + `title` ngắn trong lược đồ | 25, 36 | S |
| `trigger.schedule` · `trigger.webhook` | 6 (không có trigger nào dùng được) | L |
| Cửa test MỘT bước, có chế độ mock | 40 = 0 | M |
| Mở `publish_duoc` cho `trigger.manual`, `ai.*` | 55/67 node chết | S–M |
