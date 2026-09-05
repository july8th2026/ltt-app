# Phase E — ba editor phức tạp: cái gì đã xác minh, cái gì chưa

Khảo sát 2026-09-05. **Tệp này cố ý tách ba nhóm**: *đã xác minh bằng mã*,
*đã đo trong trình duyệt*, và *đo không kết luận được*. Nhóm thứ ba là nhóm dễ
bị viết nhầm thành nhóm thứ nhất.

---

## 1. Autosub Studio — WCAG 2.5.7 **đã thoả**, ngược với giả định của pack

Pack (prompt 05) giả định timeline chỉ có kéo-thả và yêu cầu ta *dựng* đường
thay thế. Đọc mã thì **đường ấy đã có sẵn**.

Ba thao tác kéo trong `EditorTimeline.tsx` (`onPointerDown` → `pointermove`):

| thao tác | dòng | đường thay thế bằng một-lần-chạm |
|---|---|---|
| dời cả cue | `:31` `mode:'move'` | ô số **Bắt đầu** + **Kết thúc** (`StudioShell.tsx:174`) |
| kéo mép trái | `:32` `mode:'start'` | ô số **Bắt đầu**, `type=number step=0.01` |
| kéo mép phải | `:33` `mode:'end'` | ô số **Kết thúc**, `type=number step=0.01` |

Và việc **chọn** cue vốn đã không cần kéo: mỗi cue là một `<button>` thật có
`aria-pressed` + `aria-label` đọc được cả nội dung lẫn mốc thời gian
(`EditorTimeline.tsx:28-31`), cộng một danh sách cue riêng ở
`StudioShell.tsx:166` cũng toàn `<button>`.

⭐ Nên hạng mục nặng nhất mà pack đặt cho Phase E, ở app này, là **một việc đã
làm xong trước khi lượt soát mobile bắt đầu**. Ghi lại đúng như vậy — báo cáo
một chiến thắng không có thật cũng sai như bỏ sót một lỗi.

**Còn thiếu, và đây mới là việc thật:** dời một cue *mà giữ nguyên độ dài* hiện
phải sửa **hai** ô số và tự cộng trừ. Một cặp nút `±0,1s` / `±0,5s` làm đúng
việc ấy trong một lần chạm. Chưa làm.

## 2. Agent Canvas — hai giả thuyết của tôi đều SAI

### 2a. *"`panOnDrag={[1,2]}` chặn kéo bằng ngón tay"* — SAI

`CanvasShell.tsx:757` đặt `panOnDrag={[1,2]}` (chuột giữa + chuột phải), và tôi
đã kết luận rằng một ngón tay không pan được vì chạm ánh xạ về `button 0`.

Đọc chính bản `@xyflow/system` đang cài (`dist/esm/index.js`):

```js
// :2885
if (Array.isArray(panOnDrag) && !panOnDrag.includes(event.button)
    && event.type === 'mousedown') { return false; }
// :2889
const buttonAllowed = (Array.isArray(panOnDrag) && panOnDrag.includes(event.button))
                      || !event.button || event.button <= 1;
```

Ràng buộc mảng **chỉ áp cho `mousedown`**; `touchstart` đi thẳng qua, và
`!event.button` cho chạm là `true`. ⇒ **Thư viện cố ý miễn trừ cảm ứng.**

### 2b. *"`connectOnClick` chưa bật nên không nối node bằng chạm được"* — SAI

`component-props.d.ts:537` của bản đang cài: `@default true`. Không khai gì
nghĩa là **đã bật**, tức chạm handle nguồn rồi chạm handle đích là nối được.

⚠️ Pack cảnh báo đúng chiều ngược lại — *"đừng giả định prop nếu bản đang cài
không có"* — nên câu trả lời phải đến từ `node_modules`, không từ tài liệu trên
mạng. Ở đây nó đến từ đó.

### 2c. Phép đo runtime của tôi **không kết luận được** — và tôi giữ nó lại

Thử kéo trên `/agent/canvas` ở 390×844: `transform` của `.react-flow__viewport`
đứng nguyên `matrix(1,0,0,1,0,0)`.

⛔ Nhưng **chuột trái và chuột giữa cũng không pan** trong cùng lượt đo — mà
`panOnDrag=[1,2]` thì chuột giữa **phải** pan. Một phép đo trả lời "không" cho
mọi đầu vào thì nó không phân biệt được gì; nó đang đo bộ đo, không đo sản phẩm.

Nguyên nhân khả dĩ: canvas **rỗng** (`so_node: 0` — môi trường đo chưa có dữ
liệu agent), hoặc `Input.dispatchTouchEvent` qua CDP không tới được d3-zoom.

⇒ **Chưa được ghi vào bất kỳ báo cáo nào là PASS hay FAIL.** Muốn kết luận thì
phải seed một canvas có node — giống việc `mobile_qa.py chat-seed` đã làm cho
ChatLTT.

## 3. Prompt AI OMMI — không có kéo-thả

`grep` `onDrag|draggable|onPointerDown|onTouchStart` trên `frontend/prompt-ai-ommi/src`
trả **không kết quả**. Sắp xếp cảnh trong bản React hiện không dùng kéo-thả, nên
mục "reorder drag phải có tap alternative" của pack **không áp dụng** ở đây.

⚠️ Bản Jinja cũ (`/prompt-ai-ommi/classic`) cũng không có. Nhưng cả hai đều chưa
được đo với dữ liệu thật.

---

## 4. Việc còn lại của Phase E, theo thứ tự giá trị

1. **Seed dữ liệu cho ba editor** (như `chat-seed`) — không có nó thì mọi phép
   đo tương tác đều rơi vào mục 2c.
2. Nút `±0,1s / ±0,5s` cho cue Autosub (mục 1).
3. **Nút thật < 44px trong app React**: `run-primary`, `blank-flow`, `primary`,
   `canvas-home`, `up-history-link`. Cùng bẫy `:where()` độ đặc hiệu 0 — luật
   44px của nền tảng thua luật chiều cao của chính component.
   ⚠️ Ép `!important` cho **chiều cao** rủi ro hơn nhiều so với cho cỡ chữ: nó
   đổi bố cục. Phải sửa trong CSS của từng component và đo lại từng app.
4. **Ba vòng `setInterval` trong React** (`autosub-studio` ×2, `chatltt` ×2) cần
   một hook tương đương `LTT.nhipJob` — biến toàn cục không hợp với React.
5. Xoay ngang + tablet cho cả ba editor.
