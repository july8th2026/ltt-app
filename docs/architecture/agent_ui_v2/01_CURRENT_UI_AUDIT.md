# 01 — Audit giao diện Agent/Automation hiện tại (27/09/2026)

> Tài liệu CHỈ ĐỌC. Không một dòng mã sản phẩm nào bị sửa trong đợt audit này.

## 0. Cách đo — đọc trước khi dùng bất kỳ con số nào

Mọi con số dưới đây đến từ một trong bốn nguồn, và mỗi phát hiện đều ghi rõ nguồn của nó:

| Ký hiệu | Nguồn | Độ tin |
|---|---|---|
| `[MÃ]` | đọc mã thật trong cây này | cao |
| `[API]` | gọi cửa thật của máy chủ đang chạy | cao |
| `[TRÌNH DUYỆT]` | đo trên DOM/CSSOM đã render bằng Playwright | **cao nhất** |
| `[SUY]` | suy luận từ hai nguồn trên | phải nói rõ |

**Môi trường đo GUI.** ⛔ KHÔNG chạy trên production (cổng 8100). Một máy chủ cô lập
dựng riêng cho đợt này: cổng `8198`, sqlite trong thư mục scratchpad của phiên, một
tài khoản fixture, 0 kết nối tới PostgreSQL production. Khuôn lấy nguyên từ
`tests/fixtures/image_studio_server.py`.

**⭐ Bundle đã được chứng minh là ĐẠI DIỆN ĐÚNG cho mã nguồn.**
`server/static/agent-canvas/build-meta.json` ghi `source_sha256` của toàn bộ
`frontend/agent-canvas/`. Tính lại bằng chính thuật toán của
`scripts/write-build-meta.mjs` trên 36 tệp:

```
tinh lai    : 856cc893a577b5022c74e743908c8fc64d0a1b352d8c8af9195ad4847dd39407
build-meta  : 856cc893a577b5022c74e743908c8fc64d0a1b352d8c8af9195ad4847dd39407
KHOP
```

⇒ những gì trình duyệt hiển thị là mã nguồn hiện tại, không phải một bản dựng cũ.
(Đây là bài học *"đọc thứ đại diện thay vì đọc thứ thật"*: không có phép so này thì
mọi ảnh chụp dưới đây chỉ chứng minh về một bản dựng không rõ tuổi.)

**Giới hạn đã biết của đợt đo này** — nói trước, không giấu:
- Không có job worker chạy kèm, nên một lượt chạy dừng ở `QUEUED`. Mọi nhận xét về
  UX *trong khi node đang chạy* (`RUNNING`, `WAITING`, retry) là `[MÃ]`, không phải
  `[TRÌNH DUYỆT]`.
- Tài khoản fixture mới nên palette trả 67/72 node (5 node `LTT_APPS` bị chặn theo
  quyền app). Con số 72 là registry đầy đủ `[MÃ]`; 67 là thứ một khách mới thấy `[API]`.
- Chưa đo hiệu năng ở 100/500 node — xem §9, đã ghi là CHƯA ĐO chứ không đoán.

---

## 1. Bản đồ giao diện hiện tại

```text
LTT Agent / Automation UI (thực tế, 27/09/2026)
│
├── Landing / Entry              /agent — MỘT trang tĩnh, 1 đoạn văn + 1 nút "Mở Canvas"
│                                 (apps/agent/templates/agent.html, 15 dòng)
├── Workflow List                ⛔ MISSING
├── Canvas                       /agent/canvas
│   ├── Top Bar                  tên workflow (1154px) · trạng thái lưu · ☀ · ⌘ · Chạy
│   ├── Left Rail                48px, 8 nút biểu tượng KHÔNG nhãn chữ
│   ├── Node Palette             ngăn kéo 280px, đè lên canvas
│   ├── Canvas Stage             React Flow 12.11.2
│   ├── Node                     MỘT khuôn duy nhất cho cả 7 `kind`
│   ├── Edges                    smoothstep, 1 kiểu, không nhãn nhánh
│   ├── Inspector                ngăn kéo phải, form phẳng sinh từ lược đồ
│   ├── Run Drawer               ngăn kéo trong `<header>`, tên "Chạy workflow"
│   ├── Command Palette          Ctrl/⌘+K — 7 lệnh, tất cả là lệnh XEM
│   ├── Layers Drawer            danh sách phẳng
│   └── Mobile UI                3 tab, chỉ-xem dưới 640px
│
├── Runs (lịch sử)               ⛔ MISSING  (chỉ xem được lượt chạy VỪA bấm)
├── Templates                    ⛔ MISSING  (ngăn kéo tên "Mẫu & thiết lập" có 0 mẫu)
├── Connections / Credentials    ⛔ MISSING  (xem §2.1 — đây là P0 số 2)
├── Agent Designer               MỘT nút "Soạn bằng AI" ở đáy ngăn kéo "Mẫu & thiết lập"
├── Settings                     2 tuỳ chọn (theme, catalog_mode) — không có trang
└── Subworkflow / Versions       ⛔ MISSING trên giao diện (backend có đủ)
```

Toàn bộ app Agent có **đúng hai trang HTML** `[MÃ]` (`apps/agent/routes/trang.py`):
`/agent` và `/agent/canvas`.

### 1.1 Không có danh sách workflow — và hệ quả nặng hơn vẻ ngoài

`[MÃ]` `CanvasShell` chỉ gọi `loadOrCreateWorkflowV3()`, và hàm đó là:

```ts
const items = await listWorkflowsV3()
if (items.length) return loadWorkflowV3(items[0].id)   // ← items[0]
return createWorkflowV3('Workflow mới', csrfToken)      // ← chỉ khi CHƯA CÓ cái nào
```

`[MÃ]` `drafts_v3.py:85` sắp xếp `ORDER BY Workflow.updated_at DESC`.

⇒ Canvas **luôn mở workflow vừa sửa gần nhất**, và vì Canvas tự lưu, workflow bạn mở
sẽ luôn là workflow mới nhất. `createWorkflowV3` chỉ chạy khi tài khoản có **0**
workflow. Trên giao diện **không có** nút "Workflow mới", không có danh sách, không
có đường mở một workflow khác, không có xoá/lưu trữ/nhân bản ở mức workflow.

⇒ **Sản phẩm hôm nay, qua giao diện, là một-workflow-một-tài-khoản.** Backend hỗ trợ
nhiều; giao diện không có cửa nào tới chúng. Đây là lỗ hổng kiến trúc thông tin lớn
nhất, và nó không sửa được bằng CSS.

---

## 2. Bốn lỗi chặn đường (P0) — đã chứng minh, không phải cảm giác

Bốn lỗi dưới đây không phải "UX chưa đẹp". Chúng làm **người dùng không dựng nổi một
workflow**. Tất cả đã tái hiện trên trình duyệt thật.

### 2.1 🔴 P0-1 — Node thêm từ palette KHÔNG BIÊN DỊCH ĐƯỢC (trừ `app.*`)

**Tái hiện, hoàn toàn bằng giao diện:** mở Canvas → "Mở bảng node" → bấm **một** thẻ
`core.set` → bấm **Chạy** → **Chạy ngay**.

```
[TRÌNH DUYỆT] runError : "node_khong_ton_tai: core.set"
[TRÌNH DUYỆT] banner   : "Workflow chưa biên dịch được"
[TRÌNH DUYỆT] node     : có class `node-do-loi`, huy hiệu "Lỗi biên dịch"
```

Lặp lại với `piece.google_sheets.insert_row` (cũng chỉ bấm một thẻ palette):

```
[TRÌNH DUYỆT] runError : "node_khong_ton_tai: piece.google_sheets.insert_row"
```

Đối chứng — cùng thao tác với một node `app.*`:

```
[TRÌNH DUYỆT] runError : null
[TRÌNH DUYỆT] runStatus: "QUEUED"   ← publish + tạo run THÀNH CÔNG
```

**Nguyên nhân gốc** `[MÃ]`. `editorState.nextNode()` dựng MỌI node với
`type: 'tool'` và đặt loại thật vào `data.tool`:

```ts
return { id: …, type: 'tool',            // ← LUÔN là 'tool'
         data: { tool: slugCongCu(nd), … } }
```

Còn `bien_dich._node()` (`platform_core/workflow/bien_dich.py:597`) phân nhánh theo
`n['type']` **ở mức trên cùng**:

```python
loai = str(n.get("type", ""))
if loai.startswith(TIEN_TO_LOI):      # core. / trigger. / ai. / connector.
    return _node_loi(n, nid, loai)    #   → tra nut_loi  ✅
if loai == "tool":                    # ← MỌI node palette rơi vào đây
    ten = data.get("tool")            #   "core.set" / "piece.…" / "image.generate"
    …
tool = cc.get(ten)                    # sổ CÔNG CỤ APP — không có core.*/piece.*
if tool is None: raise LoiBienDich("node_khong_ton_tai", …)
```

`app.*` sống sót **do trùng hợp**: `slugCongCu` cắt tiền tố `app.`, và slug còn lại
(`image.generate`) đúng là khoá trong sổ công cụ app.

**⭐ Đối chứng quyết định: Agent Designer làm ĐÚNG, palette làm SAI.**
`platform_core/agent/ke_hoach_v3.py:270` ghi node với `type` **thật** ở mức trên cùng
và thêm `data.tool` chỉ để canvas RENDER được, kèm chú thích của chính nó:

> *"⛔ KHÔNG thay `type`/`params` top-level bằng khoá này — cổng biên dịch
> (`bien_dich._node`/`_node_loi`) đọc đúng hai khoá top-level đó"*

⇒ **AI dựng được workflow mà con người không dựng được.** Đó cũng là lý do lỗi này
sống lâu: `tests/test_4250` ghim hình dạng của Agent Designer, và đường `app.*` chạy
tốt, nên mọi lần demo đều xanh.

**Bán kính:** mọi node `core.*` (15), `trigger.*` (7), `ai.*` (4), `connector.*` (1)
và `piece.*` (26) thêm từ palette. Tức **55/67 node `[API]`**.

### 2.2 🔴 P0-2 — 15 cổng vào nằm chồng lên ĐÚNG MỘT điểm 6×6 px

`[TRÌNH DUYỆT]` trên `app.video.generate` (node có nhiều cổng nhất, 16 cổng):

```
nodeBox                  : 456 × 381 px
targetCount              : 15
targetDistinctPositions  : 1          ← MƯỜI LĂM cổng, MỘT vị trí
mọi cổng                 : x=87, y=326, w=6, h=6
nhãn cổng                : y = 238, 255, 272, 289, 306, …  (cách nhau 17px)
elementFromPoint(90,329) : data-handleid="refs"   ← cổng CUỐI trong DOM luôn thắng
```

**Nguyên nhân gốc** `[TRÌNH DUYỆT]` đọc CSSOM: `.react-flow__handle` là
`position:absolute` với `.react-flow__handle-left { top:50%; left:0 }`, còn hàng bọc
nó `.node-cong` là `position: static`. Không có tổ tiên định vị nào ở hàng ⇒ cả 15
cổng quy chiếu về **thẻ node**, ra `top: 190.5px` = 50% của 381px. Giống hệt nhau.

**Playwright tự nó là nhân chứng.** Khi thử kéo từ cổng `image_keys`, Playwright từ
chối và in ra lý do của chính trình duyệt:

```
<div data-handleid="image_keys" …> … subtree intercepts pointer events
   from <div data-handleid="prompt" …>
```

Nó **không click nổi** cổng `image_keys` vì cổng `prompt` nằm đè lên đúng chỗ đó.

**Hệ quả đo được:** kéo một dây từ `image.generate` sang `video.generate` bằng chuột:

```
[TRÌNH DUYỆT] data-edge-count : "0"
[TRÌNH DUYỆT] edges trong DOM : []
[TRÌNH DUYỆT] edges đã lưu    : []
```

Không có dây nào được tạo. **Không có thông báo, không có lý do, không có gì.**
Người dùng kéo, và màn hình im lặng.

Điều này cũng đúng với nhánh rẽ: trên `core.if`, hai cổng `true`/`false` ở cùng
`(260, 248)` — `ifSourceDistinctPositions: 1` `[TRÌNH DUYỆT]`.

**Cái giá:** chính các node media nhiều cổng — thứ LTT mạnh hơn n8n/Activepieces —
là những node không nối được bằng chuột. Lợi thế sản phẩm bị một dòng CSS khoá lại.

### 2.3 🔴 P0-3 — 34 node đòi credential, giao diện không có chỗ gắn credential

`[API]` 34/67 node trả về `credential: [...]` khác rỗng. Trong đó 33 node có
`job_type ∈ JOB_TYPE_KHONG_TOOLSPEC`, tức cổng publish **từ chối** khi thiếu
`credential_ref` `[MÃ]` (`dinh_nghia.py::_kiem_credential`, thêm 25/09):

```python
if nd is not None and yeu_cau and nd.job_type in nut.JOB_TYPE_KHONG_TOOLSPEC:
    raise bien_dich.LoiBienDich("credential_khong_hop_le",
        f"node {nid!r}: node nay can credential ({…}) nhung chua gan `credential_ref`", nid)
```

`[MÃ]` Tìm `credential_ref` trong toàn bộ `frontend/agent-canvas/src/`: **không có**.
`CanvasNode` không có trường đó, `FormTuLuocDo` không sinh ô nào cho nó, và
`editorState` không có action nào đặt nó. Cũng **không có trang** nào trong
`server/templates/` để khách tạo một credential (`[MÃ]`, đã grep toàn bộ).

⇒ Node hiện huy hiệu **"Cần kết nối"** `[TRÌNH DUYỆT]` trên cả palette lẫn canvas —
nói đúng sự thật, nhưng **không có đường nào đi tới việc kết nối**. Đó là một biển
báo chỉ vào một cánh cửa không tồn tại.

⚠️ Và palette **vẫn cho kéo** các node này (`disabled` chỉ buộc vào `publish_duoc`,
không buộc vào `credential` — `[MÃ]` `PaletteV2.tsx:37`). Chính tệp ấy có chú thích
tự dặn *"đừng mời khách kéo một node mà publish sẽ từ chối"*; luật đó mới chỉ áp cho
một nửa lý do bị từ chối.

### 2.4 🔴 P0-4 — Rẽ nhánh bị đánh rơi ở ranh giới lưu trữ

`[MÃ]` `workflowApi.edgeToV3()`:

```ts
export function edgeToV3(edge: CanvasEdge): CanvasEdgeV3 {
  return { id, source_node, target_node, source_port, target_port,
           kind: 'DATA' }     // ← ĐÓNG CỨNG. `edge.data.condition` KHÔNG được gửi.
}
```

Nhưng động cơ đọc hai khoá đó `[MÃ]` (`dong_co.py:147`):

```python
if tt_nguon not in _KICH.get(e["kind"], frozenset()): return False
dk = str(e.get("condition") or "")
if not dk: return True            # ← không có condition ⇒ LUÔN kích hoạt
return nhanh[src] == dk
```

Hai hệ quả, cả hai im lặng:

1. **Mọi nhánh của `core.if`/`core.switch` đều chạy.** Cạnh không mang `condition`
   ⇒ `return True` ⇒ nhánh `true` và nhánh `false` kích hoạt cùng lúc. Người dùng vẽ
   một rẽ nhánh và nhận một **phân đôi**. Điều này tiêu tiền thật ở nhánh lẽ ra
   không chạy.
2. **Nhánh lỗi không bao giờ chạy khi có lỗi.** `_KICH["ERROR"] = {FAILED, ABANDONED}`
   nhưng cạnh luôn được gửi là `DATA` = `{SUCCEEDED}`. Nút *"Nhánh: Lỗi/Thành công"*
   trong ngăn kéo Chạy `[TRÌNH DUYỆT]` đổi `edge.data.condition`, thứ `edgeToV3`
   không gửi đi. **Nút đó đổi một nhãn trên màn hình và không đổi gì khác.**

`[TRÌNH DUYỆT]` trên đồ thị `core.if → {core.set, core.stop}`:

```
edgeLabels  : [null, null]
edgeClasses : ["… edge-control nopan selectable",
               "… edge-control nopan selectable"]   ← hai cạnh GIỐNG HỆT nhau
```

Không nhãn, không màu, không kiểu nét phân biệt `true` với `false`.

### 2.5 Tổng hợp: còn lại bao nhiêu node dùng được?

| Bước lọc | Còn lại |
|---|---:|
| Registry đầy đủ `[MÃ]` | 72 |
| Palette trả cho một khách mới `[API]` | 67 |
| − 4 node `publish_duoc=False` (`trigger.manual`, `ai.llm`, `ai.extract`, `ai.router`) | 63 |
| − 33 node đòi credential mà giao diện không gắn được (P0-3) | 30 |
| − mọi node không phải `app.*` (P0-1) | **12** |

⇒ **12/67 = 18 % catalogue thật sự dùng được qua giao diện**, và cả 12 đều là node
`LTT_APPS`. Không một **trigger** nào dùng được (`[MÃ]`: 0/7 — và registry **không
hề có** `trigger.schedule` hay `trigger.webhook`, đã grep).

⇒ Trong năm luồng nghiệm thu UX mà đề bài đặt ra:

| Luồng | Dựng được hôm nay? | Vì sao |
|---|---|---|
| UX-1 Schedule → Sheets → … → YouTube | ❌ | không có trigger lịch; Sheets + YouTube đòi credential; P0-1 |
| UX-2 Webhook → … | ❌ | **không có node webhook trong registry** |
| UX-3 Manual → Image → Video → Voice → Render | ⚠️ một phần | node `app.*` chạy được, nhưng **không nối được** (P0-2); trigger thủ công bị khoá |
| UX-4 Sheets → AI Router → nhánh → gộp | ❌ | Sheets (cred), `ai.router` (`publish_duoc=False`), rẽ nhánh (P0-4) |
| UX-5 Parent → Subworkflow → Wait → Human | ❌ | `core.*` — P0-1 |

**0/5 luồng nghiệm thu dựng được từ đầu đến cuối.** Đây là con số quan trọng nhất
của toàn bộ đợt audit.

---

## 3. Palette — đo trên trình duyệt

```
[TRÌNH DUYỆT] palette            : 280 × 884 px, ngăn kéo ĐÈ lên canvas
[TRÌNH DUYỆT] thẻ node           : 239 × 132 px, mỗi hàng MỘT thẻ
[TRÌNH DUYỆT] thẻ / màn hình 960px: 5  (tổng 67 thẻ ⇒ ~13 màn hình để xem hết)
[TRÌNH DUYỆT] tràn ngang         : scrollWidth 332 > clientWidth 263  (+69px)
```

### 3.1 🔴 32/67 thẻ hiện biểu tượng dưới dạng CHUỖI URL

`[API]` 32 node có `icon` là một URL (`https://cdn.activepieces.com/pieces/notion.png`).
`[MÃ]` `PaletteV2.tsx:42` và `NodeKhung.tsx:33` đều render nó là **văn bản**:

```tsx
{nd.icon && <span className="palette-icon" aria-hidden>{nd.icon}</span>}
```

`[TRÌNH DUYỆT]` kết quả: dòng chữ `https://cdn.activepieces.com/pieces/google-drive.png`
xuống hai dòng, là **phần tử nổi bật nhất** của thẻ, và chính nó gây ra 69px tràn
ngang ở trên. Ảnh: `bang_chung/02_palette_mo.png`.

### 3.2 🔴 12/12 node LTT_APPS có tiêu đề là một CÂU BỊ CẮT

`[API]`:

```
titlesOver40 : 12      maxTitleLen : 60
byCat        : LTT_APPS 12/12 · CONNECTORS 0/27 · FLOW 0/9 · TRIGGERS 0/7 · …
worst:
  app.text.prompt_package  "Chuyển brief thành gói prompt nhiều cảnh có camera, ánh sáng"
  app.video.subtitle       "Khắc transcript có sẵn vào video bằng preset phụ đề và FFmpe"
  app.video.generate       "Sinh video Seedance từ mô tả và các tài sản tham chiếu tùy c"
```

Tiêu đề bị cắt ở **đúng 60 ký tự**, giữa từ. So sánh: `connector.youtube.upload` có
tiêu đề "YouTube — Đăng video" (0/27 connector bị lỗi này).

⇒ **App của chính LTT là nhóm node bị đặt nhãn tệ nhất trong palette của LTT**, trong
khi node mượn từ Activepieces thì sạch. Và vì `NodeKhung` dùng cùng `title`, câu bị
cắt ấy còn là **tiêu đề của node trên canvas** và **tiêu đề của Inspector**, và là
**placeholder** của ô "tên hiển thị" — cùng một chuỗi hỏng xuất hiện 3 lần trên một
màn hình (`bang_chung/03_node_va_inspector.png`).

### 3.3 Ba từ cho một khái niệm, trên cùng một màn hình

`[TRÌNH DUYỆT]`:

| Chỗ | Chữ dùng |
|---|---|
| tiêu đề ngăn kéo palette | **block** ("Thêm block") |
| ô tìm trong chính ngăn kéo đó | **node** ("Tìm node…") |
| tooltip nút mở nó ở rail | **công cụ** ("Mở công cụ") |
| dòng trạng thái toolbar | **node** ("3 node · 2 kết nối") |
| ngăn kéo Chạy | **block** ("3 block · server chốt chi phí…") |

### 3.4 Catalogue song ngữ, không có lớp dịch

`[API]` 29/67 mô tả là tiếng Anh nguyên văn từ catalog Activepieces, 38 là tiếng
Việt. Chúng nằm xen kẽ trong cùng một danh sách `[TRÌNH DUYỆT]`:

> Chạy thủ công — *Người dùng bấm chạy. Không có lịch, không có webhook.*
> New Database Item — *Triggers when an item is added to a database.*

---

## 4. Node — đo trên trình duyệt

```
[TRÌNH DUYỆT] app.video.generate : 456 × 381 px
[TRÌNH DUYỆT] app.image.generate : 455 × 245 px
[TRÌNH DUYỆT] core.if            : 196 × 150 px
[MÃ]          bước xếp mặc định  : 430 px  (nextNode: x = 90 + (i%3)*430)
```

⇒ **Node rộng 456px trên lưới bước 430px ⇒ node CHỒNG LÊN NHAU ngay từ node thứ hai.**
`[TRÌNH DUYỆT]` node 1 chiếm x ∈ [90, 546], node 2 bắt đầu ở x = 520: **đè 26px**, và
node 2 che mất đuôi tiêu đề của node 1 (ảnh `bang_chung/04_…png`).

### 4.1 Phân cấp thị giác bị lộn ngược

Trên `app.video.generate` `[TRÌNH DUYỆT]`, thứ tự từ trên xuống:

1. **câu bị cắt 60 ký tự** (to, đậm, `.node-tieu-de`) ← thứ khó đọc nhất, nổi nhất
2. `APP` (huy hiệu `kind`)
3. `app.video.generate@1` (chuỗi lập trình viên, mono)
4. **"Tạo Video Seedance"** (`app_name` — *tên thật sự dùng được*, nhỏ, ở thân)
5. 15 dòng `tên-cổng · kiểu-cổng`
6. `video_key video`

Thứ người dùng cần đọc ở khoảng cách 1 mét (tên bước) nằm ở hàng thứ 4, nhỏ hơn
chuỗi `app.video.generate@1` ở hàng 3.

### 4.2 Thân node nói những câu vô nghĩa

`[MÃ]` `NodeRenderer.ThanControl` in `{d.cong_ra.length} nhánh`.
`[TRÌNH DUYỆT]` hệ quả thật:

- `core.stop` → **"0 nhánh"** (nó không có cổng ra — đó là cả ý nghĩa của nó)
- `core.switch` → **"1 nhánh"** luôn luôn, vì `core.switch` khai đúng **một** cổng ra
  `nhanh` và tên các nhánh nằm trong tham số `nhanh: array` `[MÃ]`.

### 4.3 Node không mang trạng thái, giá, hay media

`[MÃ]` `NodeKhung` vẽ: icon · title · kind · trangThai · type@version · GPU ·
"Cần kết nối" · "Sắp có" · thân · danh sách cổng. **Không có**: chi phí (đã có
`liveQuotes` nhưng chỉ hiện trong Inspector), thời lượng, số lần thử, ảnh/video
preview — dù LTT là nền tảng media. Một node `app.video.generate` đã chạy xong trông
giống hệt lúc chưa chạy, trừ một huy hiệu chữ.

---

## 5. Inspector — đo trên trình duyệt

`[TRÌNH DUYỆT]` trên `app.video.generate`: một cột phẳng, **15 ô, không tab, không
nhóm, không phần "nâng cao"**, không sticky action, không nút "Test node".

### 5.1 🔴 Bốn ô chết liên tiếp trên một node vừa thả xuống

`[TRÌNH DUYỆT]` ảnh `bang_chung/03_…png`: `resolution`, `duration`, `aspect_ratio`
đều hiện

```
— chưa có lựa chọn nào —
Chưa có lựa chọn nào
Tuỳ theo: model
```

vì cả ba `depends_on` `model`, và `model` chưa chọn. Form **không** đưa `model` lên
trước, **không** ẩn ô phụ thuộc, **không** nói *"chọn model trước"*. Người dùng gặp
ba ô xám và một chữ "Tuỳ theo: model" — một câu chỉ có người viết backend hiểu.

### 5.2 Ô nhận artifact là ô chữ tự do

`[TRÌNH DUYỆT]` `image_key` và `image_keys` — đúng những ô mà một cạnh lẽ ra sẽ điền —
được vẽ là `<input type=text>` và `<textarea>`. Không picker, không tree, không gợi ý.
Người dùng phải tự gõ `$node-id.port`. Mà đường tự nhiên để điền chúng (kéo một dây)
lại bị P0-2 khoá.

### 5.3 Ô biểu thức — có hạt nhân tốt, bọc trong một vỏ lạ

`[MÃ]` `OBieuThuc.tsx` là **phần mạnh nhất của cả frontend**: combobox ARIA đúng
chuẩn (`role=combobox`, `aria-expanded`, `aria-controls`, `role=listbox/option`),
chỉ mở khi con trỏ ở trong một `{{` chưa đóng, đánh dấu ứng viên `chưa publish được`,
và **từ chối bịa danh sách cục bộ khi máy chủ im** — đúng nguyên tắc.

Nhưng nó chỉ với tới được khi người dùng **tự gõ `{{`**. Không có nút "chèn dữ liệu",
không có cây duyệt node trước. Và `[MÃ]` nút công tắc `{{ }}` cho ô SỐ có
`aria-pressed={true}` **đóng cứng** ở một nhánh (`FormTuLuocDo.tsx`), nên trình đọc
màn hình luôn nghe "đã bật".

### 5.4 Thiếu hẳn một mặt cấu hình

`[MÃ]` `bien_dich` đọc `n.settings` cho mỗi node và `document.settings`
(`max_concurrency`, `timeout_s`) cho đồ thị. Canvas **không ghi khoá nào trong hai
khoá đó**. Ngược lại `nextNode()` ghi bốn khoá `fanout`, `max_retry`, `on_fail`,
`verify` mà **không ai đọc** `[MÃ]`. ⇒ Không có UI cho retry, timeout, đồng thời,
xử lý lỗi — trong khi backend có đủ.

---

## 6. Ngăn kéo "Chạy workflow" — một cái tên nói sai về nội dung

`[TRÌNH DUYỆT]` nội dung thật của ngăn kéo tiêu đề **"Chạy workflow"**:

```
Nhân bản · Xóa · Tự xếp · Lớp · Lưới · Đường nối · Bản đồ     ← 7 nút KHÔNG liên quan tới chạy
PHẠM VI / Toàn workflow / 3 block · server chốt chi phí tối đa khi publish
[ Chạy ngay ]
```

7/8 điều khiển là lệnh **sửa** hoặc **xem**. Và người dùng được mời bấm "Chạy ngay" —
một hành động tiêu tiền — **mà không được cho xem một con số nào**; dòng duy nhất về
tiền là *"server chốt chi phí tối đa khi publish"*. `liveQuotes` đã có sẵn trong bộ
nhớ trình soạn `[MÃ]` nhưng chỉ hiện ở chân Inspector cho **một** node.

### 6.1 Bảng lượt chạy

`[TRÌNH DUYỆT]` sau khi chạy thật một node `app.*`:

```
QUEUED
0/3 credit
Bắt đầu 13:02:18            [ Hủy chạy ]
n-img   Chờ   0   Lần 0
WorkflowStarted
```

- Cột đầu là **`node_id` thô** (`n-img`, `nmujtmc1b-0`) — không phải tên node.
  Người dùng không có cách nào biết `nmujtmc1b-0` là bước nào.
- `Lần 0` là nhãn cho `attempt`.
- Nhật ký sự kiện là một `<ol>` chỉ in `loai · node_id` — **không có dấu thời gian**
  dù `created_at` có sẵn trong dữ liệu `[MÃ]`.
- Không có dòng thời gian, không có input/output theo bước (phải mở `RunInspector`,
  là một cây JSON thô qua `@uiw/react-json-view`).
- ⚠️ `[MÃ]` **Không có lịch sử lượt chạy.** `runGoc` chỉ tồn tại khi người dùng vừa
  bấm "Chạy lại từ đây" trong **cùng phiên**; đóng tab là mất. Không có cửa máy chủ
  nào liệt kê run theo workflow (chú thích trong `CanvasShell` nói rõ).
- `[MÃ]` "So sánh lượt chạy" (`RunDiff`) dùng `jsondiffpatch` và chỉ hiện khi đã
  "Chạy lại từ đây" ít nhất một lần — một tính năng tốt nằm sau một cánh cửa gần như
  không ai mở.

---

## 7. Agent Designer — differentiator bị chôn

`[TRÌNH DUYỆT]` ảnh `bang_chung/10_…png`. Đường duy nhất tới Agent Designer:

> rail → nút `▦` (không nhãn chữ) → ngăn kéo **"Mẫu & thiết lập"** → cuộn qua
> *Pages* → *Tổ chức (Frame / Sticky note / Comment)* → ô `Mục tiêu workflow` →
> nút **"Soạn bằng AI"**

Ba nhận xét, tất cả `[TRÌNH DUYỆT]`/`[MÃ]`:

1. Ngăn kéo tên **"Mẫu & thiết lập"** chứa **0 mẫu**.
2. Tính năng AI của một nền tảng AI là một nút chữ thường, không màu, ở đáy ngăn
   kéo thứ ba, dưới trình quản lý trang và công cụ dán giấy nhớ.
3. 🔴 **Nó ghi đè đồ thị và XOÁ LUÔN lịch sử hoàn tác.** `[MÃ]`

   ```ts
   soanWorkflowV3(...).then(kq => { dispatch({type:'replace', document: fromV3(kq.document)}) })
   // editorState:  case 'replace': return { document: clone(...), past: [], future: [] }
   ```

   Không preview, không diff, không "sẽ thêm gì / bỏ gì", không báo giá, không hỏi.
   Bấm nhầm một cái là mất đồ thị đang dựng, **và Ctrl+Z không cứu được**.

---

## 8. Design system, i18n, trợ năng

### 8.1 Token: có một bộ tốt ở nền tảng, Canvas không dùng

`[MÃ]` `server/static/ltt.css` có một bộ token thật và có kỷ luật: `--surface-*`,
`--text-*`, `--brand-*`, `--status-*`, `--radius-*`, `--space-1..8`, `--fs-*`,
`--shadow-*`, kèm ghi chú đo bằng axe. **Đây là một điểm mạnh thật của dự án.**

Canvas thì không dùng nó:

```
[MÃ] canvas.css : 414 dòng, 70 831 byte (dòng dài nhất 1 340 ký tự)
[MÃ] mã màu hex viết cứng : 482 lần
[MÃ] dùng var(--token)    : 105 lần
⇒ tỉ lệ token hoá ≈ 18 %
```

### 8.2 `theme-light` mới xong một phần ba

`[TRÌNH DUYỆT]` sau khi bấm nút ☀:

```
themeClass          : "canvas-shell theme-light"
stage background    : rgb(245,246,248)        ✅ sáng
formControlsTotal   : 11
formControlsStillDark: 7                       ❌ 64 % ô vẫn nền TỐI
  → Tên workflow · Tìm node · Tên hiển thị node · prompt · image_key · count · Đổi tên page
minimap background  : rgb(255,255,255) trên nền rgb(245,246,248)  → tương phản 1.04:1
controls button bg  : rgb(255,255,255)                            → gần như vô hình
```

⚠️ **Nói cho đúng:** đây **không** phải lỗi tương phản chữ — chữ trong từng ô vẫn đạt
16.53:1. Đây là lỗi **nhất quán bề mặt**: trong cùng một form, 7 ô giữ nền tối và 4
ô (textarea + 2 select) đã sang nền sáng. Hai hệ bề mặt đứng cạnh nhau.
(Ảnh `bang_chung/05_theme_sang.png`.)

### 8.3 Tương phản theme tối: ĐẠT — nhưng cỡ chữ và vùng bấm thì không

`[TRÌNH DUYỆT]` đo 9 cặp màu chữ/nền ở theme tối: **9/9 đạt WCAG AA**, thấp nhất
5.71:1. Cần ghi nhận trung thực: **theme tối không có vấn đề tương phản.**

Vấn đề trợ năng nằm chỗ khác:

| Đo được | Giá trị | Chuẩn |
|---|---|---|
| dòng trạng thái toolbar | **9 px** | — |
| `.node-type`, `.node-kind` | **10 px** | — |
| `.palette-type`, `.palette-mo-ta` | 10 – 10.8 px | — |
| **cổng nối (`.react-flow__handle`)** | **6 × 6 px** | WCAG 2.2 AA (2.5.8) đòi ≥ 24×24 |
| nút `{{ }}` ở mobile | 48 × 19 px | thiếu chiều cao |

`[MÃ]` Điểm mạnh cần giữ: `ariaLabelConfig` tiếng Việt đầy đủ cho React Flow
(`NHAN_TRO_NANG_VI`), `aria-pressed` trên hầu hết nút bật/tắt, `aria-live` cho trạng
thái lưu, `role=alert` cho lỗi, và `prefers-reduced-motion` đã có.

### 8.4 🔴 i18n: bằng không

`[MÃ]` Toàn bộ `frontend/agent-canvas/src/` **không import một hàm dịch nào**. 428
chuỗi tiếng Việt viết thẳng trong mã (`CanvasShell.tsx` một mình chiếm phần lớn).

`[TRÌNH DUYỆT]` chứng minh hệ quả: nền tảng chuyển sang tiếng Anh và URL đổi thành
`/en/agent/canvas`, tiêu đề trang thành `Canvas · LTT Agent AI`, trang đăng nhập nói
"Sign in" — **còn toàn bộ Canvas vẫn là tiếng Việt**. Một khách dùng bản tiếng Anh
gặp một ứng dụng song ngữ ngay giữa màn hình chính.

### 8.5 Mobile: tab "Canvas" không hiện canvas

`[TRÌNH DUYỆT]` ở 390 × 844:

```
tab đang chọn      : "Canvas"  (aria-pressed=true, class=active)
body class         : "canvas-body panel-canvas"
.canvas-inspector  : HIỆN, 310 × 720 px, che gần hết stage 390 × 748
7/7 ô              : disabled   (đúng thiết kế chỉ-xem)
tràn ngang         : không  ✅
```

Chọn tab **Canvas** nhưng màn hình hiện **Inspector**. `[MÃ]` nguyên nhân: điều kiện
render là `(desktopPanel==='inspector' || mobilePanel==='inspector')`, nên một
`desktopPanel` còn sót từ lúc màn rộng vẫn mở Inspector ở mobile. Và nhãn
*"Mobile · chỉ xem"* nằm trong `<span>` bị `display:none` ở ≤640px, nên người dùng
thấy một form **trông sửa được mà không sửa được, không kèm lời giải thích nào**.
(Ảnh `bang_chung/06_mobile_390.png`.)

---

## 9. Kiến trúc frontend

### 9.1 `CanvasShell.tsx` — một hàm 740 dòng

`[MÃ]`:

```
tệp                 : 959 dòng
hàm Editor()        : dòng 196 → 935  = 740 dòng
useState            : 33
useEffect           : 10
useCallback         : 13
useMemo             : 3
lời gọi dispatch    : 67
hàm API import      : 14
khu vực JSX rời     : 11  (toolbar · run drawer · mobile tabs · rail · palette ·
                            stage · page dock · context menu · inspector ·
                            command palette · layers drawer)
```

Một hàm giữ đồng thời: nạp dữ liệu, tự lưu, SSE + lùi dần, báo giá, gợi ý biểu thức,
publish, tạo/huỷ/chạy-lại/so-sánh run, Agent Designer, chọn/copy/paste, phím tắt,
menu ngữ cảnh, quản lý trang, theme, và toàn bộ bố cục.

### 9.2 CSS: một phần tư là mã chết

`[MÃ]` 191 lớp khai trong `canvas.css`; **49 lớp (25.7 %) không được tham chiếu từ
bất kỳ `.tsx` nào** (đã trừ các lớp dựng động như `panel-${…}`, `node-kind-${…}`,
`edge-${kind}`). Chúng là nguyên các họ của component đã bị xoá ở plan 02 task 15:

```
assistant-drawer · assistant-context · assistant-modes · assistant-error
composer-check · composer-prompt · composer-reference · composer-run · composer-input-chips
context-composer · context-fields · context-tool-list
node-preview · node-preview-actions · node-artifacts · node-chips · node-composer
node-image-grid · node-upload · node-inspector · node-title · node-run · node-more
creative-node · history-drawer · legacy-run-tools · legacy-save-state
input-port · output-port · primary-output · edge-insert-picker · palette-search · …
```

`[MÃ]` Ngoài ra **5 khối `@media (max-width:640px)` riêng biệt** (dòng 55, 78, 153,
203, 204, 246) cùng tranh nhau quy định bố cục mobile — chính là nguồn của lỗi §8.5.

### 9.3 Nút chết: `+` chèn bước trên mỗi cạnh

`[MÃ]` `CanvasEdgeView` vẽ một nút `+` trên **mọi** cạnh và gọi `data.onInsert?.(…)`.
`[MÃ]` grep toàn bộ `src/`: `onInsert` **chưa bao giờ được gán** — `displayEdges`
không đặt nó.

`[TRÌNH DUYỆT]` bấm thật vào nút `+`:

```
nodes sau khi bấm : 3  (không đổi)
edges sau khi bấm : 2  (không đổi)
picker mở         : false
palette mở        : false
inspector mở      : false
```

Không-op im lặng, hiện trên mọi cạnh.

### 9.4 Minimap: chiếm 202 × 152 px và vẽ 0 node

`[TRÌNH DUYỆT]` với 3 node trên canvas:

```
minimapPresent  : true
minimapNodeCount: 0        ← minimap rỗng
nodeCountOnCanvas: 3
```

### 9.5 Hiệu năng: CHƯA ĐO

Đợt này **không** đo 50/100/500 node. Nói thẳng ra thay vì đoán. Nhưng hai rủi ro
đọc được từ mã `[MÃ]` và đáng đo trước khi thiết kế lại:

- `displayNodes`/`displayEdges` là `useMemo` phụ thuộc `page` (cả đối tượng), và
  `NodeRenderer` **không** được `memo` ⇒ mỗi lần gõ một ký tự trong Inspector là một
  lần dựng lại toàn bộ danh sách node.
- `useEffect` tự lưu so sánh bằng `JSON.stringify(workflow.canvas) === JSON.stringify(state.document)`
  ở **mỗi** lần đổi tài liệu — tức mỗi phím gõ, trên toàn bộ tài liệu.
- Điểm tốt cần ghi nhận `[MÃ]`: báo giá đã được gom về **một** request cho cả đồ thị
  (`baoGiaDoThi`), có bánh cóc `tests/BaoGiaMotCua.test.tsx` đếm đúng con số ấy.

---

## 10. Những thứ ĐANG TỐT — phải giữ khi làm lại

Audit này nặng về lỗi vì đó là việc được giao, nhưng bốn thứ dưới đây tốt thật và
việc thiết kế lại **không được làm hỏng chúng**:

1. **Palette sinh 100 % từ registry.** `palette_v3.sang_json` liệt kê tường minh
   từng khoá; thêm một app không phải sửa một dòng nào trong `frontend/agent-canvas/src/`.
   Đây là nền móng đúng cho mọi thứ khác.
2. **Luật nối dây tải TỪ máy chủ, không cài lại ở client.** `he_kieu.xuat_luat_noi_day()`
   trả một **bảng tra** (17 kiểu, 180 cặp hợp lệ `[API]`); `nodeDefinition.noiDuoc()`
   chỉ *tra* chứ không *suy*. Không có hai bản cài đặt để lệch nhau.
3. **Kỷ luật "không bịa khi máy chủ im".** Gợi ý biểu thức hỏng ⇒ `undefined`, không
   lùi về một danh sách cục bộ. Báo giá hỏng ⇒ **xoá** bảng giá, không giữ số cũ.
   Node biến mất khỏi palette ⇒ vẫn vẽ ra kèm lời giải thích (`nutThieu`), không lọc
   đi trong im lặng. Đây là văn hoá thiết kế hiếm và đắt giá.
4. **Đường tiền đã được nghĩ kỹ.** `Idempotency-Key` sinh đúng một lần cho một cú
   bấm, cộng một chốt `ref` chống bấm đúp, cộng `finally` để một lỗi 402/503 không
   khoá vĩnh viễn nút Chạy. Ô "ngân sách tối đa" đã bị **gỡ** đúng lúc vì không ai
   thi hành nó — thà không hứa còn hơn hứa về tiền rồi không giữ.

Ngoài ra: tương phản theme tối đạt AA toàn bộ (§8.3), `ariaLabelConfig` tiếng Việt
đầy đủ, `prefers-reduced-motion` đã xử lý, và không có tràn ngang ở 390px.

---

## 11. Danh sách phát hiện theo mức độ

| # | Phát hiện | Mức | Ảnh hưởng người dùng | Chi phí sửa | Nguồn |
|---|---|---|---|---|---|
| 1 | Node palette không biên dịch được (trừ `app.*`) | **P0** | 55/67 node vô dụng | S (1 dòng `nextNode` + di trú) | TRÌNH DUYỆT |
| 2 | 15 cổng chồng một điểm 6×6px; kéo dây im lặng thất bại | **P0** | không nối được node | S (CSS `position:relative`) + M (layout cổng) | TRÌNH DUYỆT |
| 3 | Không có UI credential; 33 node bị publish từ chối | **P0** | mọi connector vô dụng | L (trang + picker + OAuth) | MÃ+API |
| 4 | `edgeToV3` bỏ `condition`, đóng cứng `kind:'DATA'` | **P0** | rẽ nhánh chạy CẢ HAI; nhánh lỗi không chạy | S (2 trường) | MÃ |
| 5 | Không có danh sách workflow / không tạo được cái thứ hai | **P0** | một-workflow-một-tài-khoản | M | MÃ |
| 6 | Không có trigger dùng được; không có schedule/webhook trong registry | **P0** | không tự động hoá được | L (backend) | MÃ |
| 7 | Agent Designer ghi đè đồ thị, xoá undo, không preview/diff | **P0** | mất việc đang làm | M | MÃ |
| 8 | 32/67 icon hiện là chuỗi URL, gây tràn ngang 69px | **P1** | palette trông hỏng | S | TRÌNH DUYỆT |
| 9 | 12/12 tiêu đề LTT_APPS là câu bị cắt ở 60 ký tự | **P1** | không đọc được tên bước | S (thêm `title` ngắn vào ToolSpec) | API |
| 10 | Node 456px trên lưới 430px ⇒ chồng nhau | **P1** | canvas bẩn ngay từ node thứ 2 | S | TRÌNH DUYỆT |
| 11 | Minimap chiếm 202×152px, vẽ 0 node | **P1** | nhiễu thuần tuý | S | TRÌNH DUYỆT |
| 12 | Nút `+` chèn bước trên mọi cạnh là no-op | **P1** | mất niềm tin | S | TRÌNH DUYỆT |
| 13 | `theme-light`: 7/11 ô giữ nền tối; minimap/controls vô hình | **P1** | theme sáng không dùng được | M | TRÌNH DUYỆT |
| 14 | i18n bằng không; 428 chuỗi cứng; vỡ ở `/en/` | **P1** | chặn quốc tế hoá | M | MÃ+TRÌNH DUYỆT |
| 15 | Mobile: tab "Canvas" hiện Inspector; không nói là chỉ-xem | **P1** | mobile hỏng | S | TRÌNH DUYỆT |
| 16 | Không có lịch sử run; "so sánh" chỉ sống trong phiên | **P1** | không gỡ lỗi được | L (cần cửa máy chủ) | MÃ |
| 17 | Bảng run hiện `node_id` thô, không dấu thời gian | **P1** | không đọc được lượt chạy | S | TRÌNH DUYỆT |
| 18 | Ngăn kéo "Chạy workflow" chứa 7 lệnh không liên quan | **P1** | IA sai | S | TRÌNH DUYỆT |
| 19 | Không có báo giá trước khi bấm Chạy (dữ liệu đã có sẵn) | **P1** | tiêu tiền mù | S | MÃ |
| 20 | 4 ô phụ thuộc chết trên node vừa thả; hint "Tuỳ theo: model" | **P1** | tắc ngay bước 1 | M | TRÌNH DUYỆT |
| 21 | Không có picker dữ liệu; ô artifact là chữ tự do | **P1** | phải nhớ cú pháp | L | TRÌNH DUYỆT |
| 22 | Không có UI retry/timeout/đồng thời (backend có) | **P2** | không chỉnh được | M | MÃ |
| 23 | `core.switch` hiện "1 nhánh"; `core.stop` hiện "0 nhánh" | **P2** | sai thông tin | S | TRÌNH DUYỆT |
| 24 | Ba từ (block/node/công cụ) cho một khái niệm | **P2** | học khó | S | TRÌNH DUYỆT |
| 25 | Catalogue song ngữ, 29/67 mô tả tiếng Anh | **P2** | thiếu chuyên nghiệp | M | API |
| 26 | Chữ 9–10px ở 5 chỗ | **P2** | khó đọc | S | TRÌNH DUYỆT |
| 27 | `CanvasShell` 740 dòng, 33 state, 11 khu vực JSX | **P2** | mọi thay đổi đều rủi ro | L | MÃ |
| 28 | 49/191 lớp CSS là mã chết; 5 khối media 640px chồng nhau | **P2** | bảo trì | M | MÃ |
| 29 | Token hoá CSS ≈ 18 % (482 hex cứng / 105 var) | **P2** | không đổi theme được | M | MÃ |
| 30 | `aria-pressed={true}` đóng cứng trên nút `{{ }}` | **P3** | sai cho trình đọc màn hình | S | MÃ |

---

## 12. Bằng chứng ảnh

| Tệp | Cho thấy |
|---|---|
| `bang_chung/01_canvas_rong_1536.png` | màn hình đầu; tên workflow 1154px; minimap rỗng |
| `bang_chung/02_palette_mo.png` | icon là URL; tràn ngang; "Sắp có" trên trigger thủ công |
| `bang_chung/03_node_va_inspector.png` | node 456×381; tiêu đề bị cắt 3 lần; 4 ô phụ thuộc chết |
| `bang_chung/04_hai_node_chong_nhau_cong_chong_diem.png` | node đè 26px; 21 tên cổng / 2 chấm nối |
| `bang_chung/05_theme_sang.png` | 7 ô giữ nền tối trên panel trắng |
| `bang_chung/06_mobile_390.png` | tab "Canvas" nhưng hiện Inspector |
| `bang_chung/07_re_nhanh_if.png` | hai nhánh rời cùng một điểm, không nhãn |
| `bang_chung/08_ngan_keo_chay.png` | "Chạy workflow" chứa 7 lệnh xem/sửa |
| `bang_chung/09_bang_luot_chay.png` | bảng run với `node_id` thô |
| `bang_chung/10_mau_va_thiet_lap_agent_designer.png` | Agent Designer ở đáy ngăn kéo "Mẫu" có 0 mẫu |
