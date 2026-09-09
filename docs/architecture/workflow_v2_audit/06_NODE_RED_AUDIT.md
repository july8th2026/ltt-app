# 06 — KHẢO SÁT MÃ NGUỒN: NODE-RED

> **Kho:** `node-red/node-red` · **tag** `5.0.6` ·
> **commit** `260402832a64373473009188ac01439534c13b36` · 2026-09-01
> **Giấy phép:** ✅ **Apache-2.0** (OpenJS Foundation) — sạch nhất trong 7 kho.
> **Phân loại:** *Visual Automation* — nhưng mô hình thi hành **khác hẳn** hai
> kho trước.
>
> Quy mô: **235.892 dòng** (912 tệp) — kho nhỏ nhất, đọc được trọn vẹn.
> ⚠️ Mã nguồn thật nằm ở `packages/node_modules/@node-red/…`, **không** phải
> thư mục phụ thuộc (xem `03 §1.3`).

---

## 0. KẾT LUẬN NGẮN

Node-RED là **kho đầu tiên trong cuộc khảo sát nói "CÓ" cho câu hỏi song song** —
và nó nói "có" bằng một cách mà tôi không lường trước: **không bằng cách điều
phối, mà bằng cách bỏ hẳn việc điều phối.**

Mỗi lượt gửi thông điệp được ném lên vòng lặp sự kiện bằng `setImmediate` riêng.
Các nhánh đan xen thật, I/O của hai nhánh thật sự bay đồng thời. Nhưng **không
có trần, không có backpressure, không có join, không có thứ tự bảo đảm, và
không có một byte trạng thái nào được lưu.**

| | |
|---|---|
| ⭐ Xuất sắc | **đan xen bất đồng bộ** (`WF-201` — kho đầu tiên) · **chuỗi hook trên đường định tuyến** (LTT không có gì tương đương) |
| ✅ Tốt | sao chép thông điệp khi rẽ nhánh · subflow là **mở rộng macro**, một mô hình khác đáng biết |
| 🔴 Trượt nặng | **KHÔNG có bền vững nào cả** · không join · không trần đồng thời · không version · không chi phí |
| 📐 Số đo đắt giá | canvas SVG tự viết: **10.203 dòng**, so với **2.061 dòng** của LTT dùng React Flow |

⭐ **Một câu đáng nhớ:** Node-RED chứng minh rằng *đồng thời* rẻ và *phối hợp*
đắt — nó lấy cái rẻ và bỏ hẳn cái đắt. LTT không có lựa chọn đó, vì `WF-501`
(trần chi phí) và `WF-202` (tài nguyên khan hiếm) **đều là phối hợp**.

---

## 1. MÔ HÌNH ĐỒ THỊ — CẠNH LÀ MỘT MẢNG TRÊN NODE NGUỒN

### 1.1 Bằng chứng

```
kho : node-red @ 26040283
tệp : packages/node_modules/@node-red/runtime/lib/nodes/Node.js:420-472
```

```js
var numOutputs = this.wires.length;
for (var i = 0; i < numOutputs; i++) {
    var wires = this.wires[i];          // các dây rời cổng ra i
    ...
    for (var j = 0; j < wires.length; j++) {
        ...
        sendEvents.push({
            msg: m,
            source:      { id: this.id, node: this, port: i },
            destination: { id: wires[j], node: undefined },   // ← chỉ có ID, KHÔNG có cổng vào
            cloneMessage: msgSent
        });
```

**Đọc ra:**
- `node.wires` là `string[][]` — mảng theo **chỉ số cổng ra**, mỗi phần tử là
  danh sách **id node đích**.
- `destination` chỉ có `id`, **không có chỉ số cổng vào** ⇒ một node Node-RED có
  **N cổng ra nhưng đúng MỘT cổng vào**.

`CONFIRMED`

### 1.2 Hệ quả: không có join, về mặt kiến trúc

Vì node chỉ có một cổng vào, **runtime không có chỗ nào để biểu đạt *"chờ cả A
lẫn B"***. Thông điệp từ A và thông điệp từ B tới cùng một cổng, và node được
gọi **hai lần**, không phải một lần với hai đầu vào.

Node `join` nổi tiếng của Node-RED là một **node người dùng** trong thư viện
`nodes-base`, tự gom thông điệp theo `msg._msgid`/số lượng — **không phải một
nguyên hàm của runtime**.

⇒ Đối chiếu ba kho đã đọc, về `WF-203`:

| | Cơ chế join | Ở tầng nào |
|---|---|---|
| Activepieces | `BarrierPolicy` + bảng `waitpoint_signal` | **runtime + CSDL** ⭐ |
| n8n | `waitingExecution[node].main[inputIndex]` | runtime, **trong RAM** |
| Node-RED | node `join` trong thư viện | **không ở runtime** |

**Activepieces vẫn là bản tốt nhất**, và khoảng cách rộng ra sau kho này.

### 1.3 So với LTT

LTT dùng `edge.source/target` là **id**, có `sourceHandle`/`targetHandle`, và
`after`/`after_error` cho phép **nhiều cha** (`01 §3.2`). Node-RED không có cổng
vào ⇒ **LTT mạnh hơn rõ rệt** ở mô hình đồ thị. Không có gì để học ở mục này.

---

## 2. ⭐ THI HÀNH — KHO ĐẦU TIÊN THẬT SỰ ĐAN XEN

### 2.1 Bằng chứng quyết định

```
tệp : packages/node_modules/@node-red/runtime/lib/flows/Flow.js:30, 831-844, 858
```

```js
let asyncMessageDelivery = true;                       // ← MẶC ĐỊNH BẬT
...
function handlePreDeliver(flow, sendEvent, reportError) {
    hooks.trigger("preDeliver", sendEvent, (err) => {
        ...
        if (asyncMessageDelivery) {
            setImmediate(function () { deliverMessageToDestination(sendEvent) })
        } else {
            deliverMessageToDestination(sendEvent)
        }
        hooks.trigger("postDeliver", sendEvent, ...)
    })
}
...
asyncMessageDelivery = !runtime.settings.runtimeSyncDelivery      // cờ vận hành
```

**Điều này chứng minh:** mỗi lượt giao thông điệp được **xếp riêng lên vòng lặp
sự kiện**. Một node rẽ ra ba nhánh sẽ tạo **ba `setImmediate` độc lập** — không
nhánh nào chạy trọn vẹn trước nhánh nào.

`CONFIRMED`

### 2.2 Đây là ĐỒNG THỜI, không phải SONG SONG — và khác biệt đó quan trọng

Vẫn một luồng JavaScript. Nhưng khi nhánh B chờ I/O, nhánh C **chạy tiếp** ⇒
**hai lời gọi HTTP của hai nhánh thật sự bay cùng lúc.**

Trả lời TEST 2 của đề bài §8 cho cả ba kho *visual automation*:

| | Nhánh song song? | Bằng chứng |
|---|---|---|
| Activepieces | ❌ **không** | `for` + `await` luồn `executionState` (`04 §2.2`) |
| n8n | ❌ **không** | `stack.shift()` + `await` (`05 §2.1`) |
| **Node-RED** | ✅ **CÓ (đan xen)** | `setImmediate` mỗi lượt giao |

⭐ **Và có một cờ để TẮT nó:** `runtimeSyncDelivery`. Sự tồn tại của cờ đó nói
rằng chính họ cũng biết đan xen làm hành vi **khó đoán**, nên để lại đường lùi
về đồng bộ.

### 2.3 🔴 Nhưng đây là đồng thời KHÔNG PHỐI HỢP

Không tìm thấy trong runtime:

- **trần đồng thời** — không có; N thông điệp sinh N `setImmediate`
- **backpressure** — không có; node chậm không làm node nhanh chậm lại
- **thứ tự** — không bảo đảm giữa các nhánh
- **join** — không ở runtime (§1.2)
- **huỷ** — không có cách dừng một thông điệp đang bay

⇒ **Với LTT thì mô hình này không dùng được nguyên bản.** `WF-201` của LTT đòi
**bốn tầng trần** (run · tài nguyên · tenant · node), và `F2` (92 % lượt nhặt bị
nhả vì `llm_remote` bận) nói rằng tầng *tài nguyên* mới là tầng thật sự chặn.
Sinh không giới hạn `setImmediate` trên một máy có **một** suất GPU là công thức
cho đúng cơn bão mà LTT đang cố thoát.

⭐ **Nhưng ý tưởng cốt lõi thì lấy được:** *đơn vị lập lịch là **lượt giao trên
một cạnh**, không phải **một bước trong danh sách***. LTT hôm nay duyệt
`plan.steps` theo thứ tự khai báo (`01 §5.2`); Node-RED không có "danh sách
bước" nào cả — chỉ có cạnh và thông điệp. Đó là một cách nhìn khác cho
`WF-202`: lập lịch **theo cạnh sẵn sàng**, có trần theo tài nguyên.

### 2.4 ⭐ Sao chép khi rẽ nhánh — chi tiết nhỏ, hệ quả lớn

```
tệp: .../runtime/lib/nodes/Node.js:466-468 và .../flows/Flow.js:812-814
sendEvents.push({ ..., cloneMessage: msgSent });  msgSent = true;
...
if (sendEvent.cloneMessage) { sendEvent.msg = redUtil.cloneMessage(sendEvent.msg) }
```

Người nhận **đầu tiên** dùng thông điệp gốc; mọi người nhận sau nhận **bản sao**.

⇒ Hai nhánh không bao giờ chia sẻ trạng thái thay đổi được. Với một hệ đan xen
thì đây là điều kiện **bắt buộc**, không phải tối ưu hoá — và nó tốn bộ nhớ đúng
bằng số nhánh.

⚠️ **Cảnh báo trực tiếp cho LTT:** nếu V2 cho phép nhánh chạy đồng thời
(`WF-201`), thì **tham chiếu artifact phải bất biến**. LTT đang ở phía đúng —
state mang *khoá lưu trữ*, không mang *đối tượng* (`WF-602`) — nên bài toán sao
chép này **không phát sinh**. Đáng ghi lại như một lợi thế đã có.

---

## 3. ⭐ CHUỖI HOOK TRÊN ĐƯỜNG ĐỊNH TUYẾN — thứ LTT hoàn toàn không có

Lần theo một thông điệp từ lúc gửi tới lúc nhận:

```
Node.send()
  └─ hooks.trigger("onSend",      sendEvents)      Flow.js
      └─ handlePreRoute()
          └─ hooks.trigger("preRoute",   sendEvent)   ← mỗi sự kiện MỘT lần
              └─ [sao chép thông điệp nếu cần]
                  └─ hooks.trigger("preDeliver",  sendEvent)
                      ├─ setImmediate(deliver)
                      └─ hooks.trigger("postDeliver", sendEvent)
                                 ↓
Node.receive() ─ hooks.trigger("onReceive",  receiveEvent)   Node.js:206
                  └─ emit("input", msg)
                      └─ hooks.trigger("postReceive", receiveEvent)  Node.js:246
```

**Sáu điểm móc trên vòng đời của MỘT thông điệp qua MỘT cạnh.** Và hook trả
`false` thì **chặn** việc giao (`else if (err !== false)` ở cả ba chỗ).

⭐ **Vì sao đây là thứ đáng giá nhất về mặt kiến trúc trong kho này.** Nó biến
**cạnh** thành một điểm mở rộng bậc một. Với LTT, cùng một cơ chế sẽ cho:

| Việc LTT đang thiếu | Móc vào đâu |
|---|---|
| Đo `M3` (lượt claim / job xong) | `preDeliver` |
| Cưỡng chế `WF-903` (quyền tool lúc **thi hành**, không chỉ lúc validate) | `preRoute` — trả `false` để chặn |
| `WF-805` dòng thời gian tầng workflow | `onSend` + `postReceive` |
| Chèn `WF-202` (chờ tài nguyên) mà không sửa scheduler | `preDeliver` |

⇒ **Đề xuất mang sang tài liệu 23:** V2 nên có một **chuỗi middleware trên cạnh**,
không chỉ trên node. LTT hôm nay có `JobEvent` (nhật ký *sau khi* việc xảy ra)
nhưng **không có điểm nào can thiệp *trước*** — mọi chính sách phải nhét vào
`executor.tick`, và đó là lý do `tick()` đang phình.

---

## 4. 🔴 BỀN VỮNG — KHÔNG CÓ. THẬT SỰ KHÔNG CÓ.

### 4.1 Bằng chứng phủ định, đo được

```
tệp: packages/node_modules/@node-red/runtime/lib/storage/localfilesystem/
     → index.js · library.js · projects/ · sessions.js · settings.js · util.js

grep -rln "execution|runState|persistMsg"  runtime/lib/     → 0 tệp
```

Tầng lưu trữ chỉ giữ **định nghĩa flow, thư viện, cài đặt, phiên đăng nhập**.
**Không có bảng lượt chạy, không có bảng thông điệp, không có checkpoint.**
`CONFIRMED`

Thông điệp sống trong RAM và được giao bằng `EventEmitter.emit("input", msg)`.

⇒ **Khởi động lại tiến trình = mọi thông điệp đang bay biến mất, im lặng, không
ai được báo.**

### 4.2 Vì sao điều này quan trọng với LTT hơn là với Node-RED

Node-RED được thiết kế cho **IoT/tự động hoá tại chỗ**, nơi thông điệp kế tiếp
sẽ tới sau vài giây, nên mất một thông điệp là chuyện chấp nhận được.

LTT thì `F3` đo được: **worker khởi động lại 13,6 lần/ngày**. Một mô hình không
bền trên máy đó không phải là *"chấp nhận rủi ro"* — nó là *"mất việc mỗi ngày
hơn mười lần"*.

⇒ Node-RED **không đóng góp gì** cho `WF-301/302/303/304`. Đây là kho thứ ba
liên tiếp không giải được `WF-301`. Nhóm *durable execution* (tài liệu 09/10) là
nơi duy nhất còn lại.

### 4.3 Bảng cộng dồn — `WF-301` sau ba kho

| Kho | Trạng thái chạy lưu ở đâu |
|---|---|
| Activepieces | **một tệp blob** (`logsFileId`) |
| n8n | **một cột `text`** (+ đẩy ra `fs/s3/az` khi to) |
| Node-RED | **không lưu gì cả** |
| **LTT hôm nay** | **một cột JSON** (`AgentRun.checkpoint`) |

🔴 Bốn hệ, bốn lần, **không hệ nào lưu trạng thái thi hành dạng hàng**. Yêu cầu
`WF-301` của LTT đang không có tiền lệ trong nhóm này — giữ nguyên yêu cầu, và
ghi rõ ở tài liệu 23 rằng nó phải được **thiết kế**, không **mượn**.

---

## 5. SUBFLOW — MỘT MÔ HÌNH THỨ BA, ĐÁNG BIẾT

```
tệp: packages/node_modules/@node-red/runtime/lib/flows/Subflow.js:54-64
/**
 * This takes a subflow definition and instance node, creates a clone of the
 * definition with unique ids applied and passes to the super class.
 */
constructor(parent, globalFlow, subflowDef, subflowInstance) { ... }
```

**Subflow là MỞ RỘNG MACRO:** định nghĩa được **nhân bản** với id mới rồi nhúng
thẳng vào flow cha lúc triển khai. Không có "lượt chạy con", không có
`parentRunId`.

Ba mô hình subworkflow, ba đánh đổi khác nhau:

| Hệ | Mô hình | Được | Mất |
|---|---|---|---|
| Activepieces | **lượt chạy con** (`parentRunId`, `failParentOnFailure`) | cách ly, quan sát riêng, ghim version riêng | thêm một lượt chạy để theo dõi |
| n8n | sub-execution (`executeWorkflow`) | như trên | như trên |
| **Node-RED** | **mở rộng macro** (nhân bản định nghĩa + id mới) | không có ranh giới runtime ⇒ nhanh, đơn giản | **không ghim version được**, không quan sát riêng, đồ thị nở ra |

⇒ Với `WF-106` của LTT (yêu cầu **ghim version** cho subworkflow), mô hình macro
**không đáp ứng được** — ghim version đòi ranh giới thực thể. **Chọn mô hình
lượt-chạy-con của Activepieces.**

---

## 6. 📐 CANVAS — SỐ ĐO ĐẮT GIÁ NHẤT CHO `Q7`

Đây là câu tôi mang sang từ tài liệu 05, và nó được trả lời bằng một con số.

```
tệp: packages/node_modules/@node-red/editor-client/src/js/ui/view.js   8.027 dòng
     ... /view-tools.js 1.443 · view-zoom-animator.js 256 · view-navigator.js 237
     ... /view-annotations.js 220
     ────────────────────────────────────────────────────────────────
     TỔNG lớp hiển thị canvas:                                10.203 dòng
```

Canvas **SVG tự viết**, thao tác bằng `d3` (`view.js:151-160`:
`@type {d3.Selection<SVGGElement, …>}`). Không React, không thư viện đồ thị.

### 🔴 Đối chiếu trực tiếp với LTT

| | Node-RED | LTT (`frontend/agent-canvas`) |
|---|---:|---:|
| Nền | SVG tự viết + d3 | **React 19 + @xyflow/react 12** |
| Lớp canvas | **10.203 dòng** | `CanvasShell.tsx` 892 |
| **Toàn bộ ứng dụng canvas** | — | **2.061 dòng** |
| Tỉ lệ | **≈ 5×** chỉ riêng lớp view | 1× cho **cả** ứng dụng |

Và LTT đã có sẵn (`01 §10.1`): cổng có kiểu, chặn nối sai kiểu, chặn chu trình,
undo/redo 50 bước, copy/paste có remap `$ref`, chèn node giữa cạnh, minimap,
đồng thời lạc quan (409).

⭐ **Kết luận sớm cho `Q7`, mức `HIGH`:** **giữ React Flow.** Node-RED là bằng
chứng định lượng về cái giá của việc tự viết: **gấp năm lần mã cho phần thấy
được, và đó mới chỉ là lớp view.** Chỉ nên xét lại nếu một yêu cầu cụ thể của
`WF-704`/`21_CANVAS` cho thấy React Flow chặn đường — cho tới giờ chưa có.

*(Chốt chính thức ở `14_CANVAS_COMPARISON.md`, sau khi xem canvas Svelte của
Windmill.)*

---

## 7. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

| ID | Yêu cầu LTT | NR | Ghi chú |
|---|---|:--:|---|
| WF-101 | DAG nhiều cha/con | 🟡 | nhiều cha được, nhưng **một cổng vào** |
| WF-102 | Edge là thực thể | ❌ | `wires: string[][]` trên node nguồn |
| WF-103 | Data/Control edge | ❌ | chỉ một loại dây |
| WF-104 | NodeType ≠ NodeInstance | ✅ | `registry` + `type` |
| WF-105 | Version bất biến + hash | ❌ | **không có version** |
| WF-106 | Subworkflow | 🟡 | **mở rộng macro** — không ghim version được |
| WF-201 | Song song khai được | ⭐🟡 | **có đan xen thật**, nhưng **không khai/không trần được** |
| WF-202 | Lập lịch biết tài nguyên | ❌ | không có khái niệm tài nguyên |
| WF-203 | JOIN đa ngữ nghĩa | ❌ | không ở runtime |
| WF-204 | ForEach + concurrency | ❌ | node `split`/`join` ở thư viện |
| WF-205 | Rẽ nhánh theo dữ liệu | ✅ | node `switch` |
| WF-206 | Node không sinh Job | ✅ | mọi node trong tiến trình |
| WF-207 | Máy trạng thái tường minh | ❌ | không có trạng thái lượt chạy |
| WF-208 | Huỷ/timeout lan truyền | ❌ | không dừng được thông điệp đang bay |
| WF-301 | Trạng thái là hàng CSDL | ❌❌ | **không lưu gì cả** |
| WF-302 | Bảo đảm được viết ra | ❌ | mất im lặng khi restart |
| WF-303 | Reconcile | ❌ | không có gì để đối soát |
| WF-401 | Waitpoint | ❌ | node `delay` ở thư viện, trong RAM |
| WF-402 | Đánh thức bằng sự kiện | 🟡 | hướng sự kiện, nhưng không bền |
| WF-403 | Nền tảng cấp GPU | ❌ | |
| WF-501 | Trần chi phí tất định | ❌ | |
| WF-601 | Artifact có danh tính | ❌ | payload nằm trong `msg` |
| WF-602 | State mang tham chiếu | ❌ | mang **giá trị**, phải sao chép |
| WF-701 | Hệ kiểu cổng | ❌ | `msg` là object tự do |
| WF-703 | Một nguồn luật nối dây | ✅ | không có luật kiểu nào để lệch |
| WF-705 | SDK = mở rộng manifest | ✅ | `registry` + `.html`/`.js` cặp đôi |
| WF-801 | Trigger đa dạng | ✅ | inject/http/mqtt/… |
| WF-805 | Quan sát tầng workflow | ⭐ | **6 hook trên đường định tuyến** |

**Tổng:** ⭐ **3** · ✅ **7** · 🟡 **4** · ❌ **17**.

⚠️ **Đừng đọc bảng này thành "Node-RED tệ".** Nó đang bị chấm theo yêu cầu của
một **nền tảng SaaS đa tenant có GPU và có sổ tiền**. Node-RED không nhắm vào
bài toán đó và không giả vờ nhắm vào. Bảng này đo **độ phù hợp**, không đo
**chất lượng**.

---

## 8. RÚT RA CHO LTT

### 🟢 LẤY

1. **Chuỗi hook trên cạnh** (6 điểm móc, hook trả `false` thì chặn).
   → `WF-805` + chỗ cắm cho `WF-202`/`WF-903` mà không phình `executor.tick`.
   **Đây là đóng góp lớn nhất của kho này.**
2. **Đơn vị lập lịch = lượt giao trên MỘT CẠNH**, không phải một bước trong
   danh sách. Cách nhìn này hợp với `WF-202` (lập lịch theo tài nguyên) hơn là
   vòng `for` theo `plan.steps` hiện tại.
3. **Cờ đồng bộ/bất đồng bộ có thể tắt** (`runtimeSyncDelivery`) — khi đưa đan
   xen vào một hệ vốn tuần tự, phải có đường lùi để so sánh hành vi.

### 🔴 TRÁNH

1. **Đồng thời không có trần.** Sinh `setImmediate` không giới hạn trên máy có
   **một** suất GPU là đúng cơn bão `F2` đã đo được.
2. **Không bền.** Với `F3` (13,6 lần restart/ngày) thì đây là mất việc hằng ngày.
3. **Subflow bằng mở rộng macro.** Không ghim version được ⇒ trượt `WF-106`.
4. **Tự viết canvas.** `10.203 dòng` cho lớp view, so với `2.061 dòng` cho cả
   ứng dụng canvas của LTT. Con số này nên đóng cửa `Q7`.

### 📌 Sửa vào tài liệu 02

- `WF-805`: bổ sung **chuỗi middleware trên cạnh** (không chỉ nhật ký sau sự
  kiện) như một yêu cầu, vì nó là chỗ cắm cho ba yêu cầu khác.
- `WF-106`: ghi rõ **chọn mô hình lượt-chạy-con**, loại trừ mô hình macro, kèm
  lý do (ghim version đòi ranh giới thực thể).
- `Q7`: nâng lên **`HIGH` — giữ React Flow**, kèm số đo 5×.

---

## 9. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| `wires` là `string[][]`, đích chỉ có id, node có **một** cổng vào | `CONFIRMED` |
| `asyncMessageDelivery = true` mặc định; mỗi lượt giao một `setImmediate` | `CONFIRMED` |
| Có cờ `runtimeSyncDelivery` để quay về đồng bộ | `CONFIRMED` |
| Sao chép thông điệp cho mọi người nhận sau người đầu tiên | `CONFIRMED` |
| Tầng lưu trữ **không** giữ trạng thái thi hành | `CONFIRMED` — liệt kê thư mục + grep 0 kết quả |
| Subflow là nhân bản định nghĩa với id mới | `CONFIRMED` — docstring + hàm dựng |
| 6 hook trên vòng đời một thông điệp | `CONFIRMED` |
| Canvas: 10.203 dòng lớp view, SVG + d3 | `CONFIRMED` — `wc -l` + chú thích kiểu `d3.Selection` |
| Nhánh có I/O **thật sự** bay đồng thời | `HIGH` — suy từ `setImmediate`; **chưa chạy thí nghiệm đo** |
| Không có trần đồng thời trong runtime | `HIGH` — không tìm thấy; không thể chứng minh phủ định tuyệt đối |
| Node `join`/`delay` của thư viện hoạt động ra sao | `UNKNOWN` — **chưa đọc** `nodes-base`; chúng ngoài runtime |

---

## 10. BƯỚC KẾ TIẾP

Ba kho *visual automation* đã xong, và chúng **cùng nhau không trả lời được**
`WF-301` (trạng thái dạng hàng), `WF-302` (bảo đảm viết ra), `WF-202` (lập lịch
biết tài nguyên) — đúng ba yêu cầu `MUST` nặng nhất của LTT.

⇒ Đổi thứ tự ưu tiên: **nhảy sang nhóm *durable execution* trước**, thay vì đọc
Kestra/Windmill theo số thứ tự.

`09_TRIGGER_DEV_AUDIT.md` — Apache-2.0, và có `internal-packages/run-engine`,
`run-queue`, `run-store`, `schedule-engine` **tách rời sẵn**. Câu hỏi mang sang:

1. `WF-301` — `run-store` lưu trạng thái theo **hàng** hay theo **khối**?
2. `WF-202` — `run-queue` có biết tài nguyên khan hiếm không?
3. `WF-401/402` — waitpoint và đánh thức, so với `BarrierPolicy` của Activepieces
4. `WF-302` — bảo đảm nào được **viết ra** thành tài liệu/kiểu dữ liệu?

*(Kestra 07 và Windmill 08 vẫn làm, nhưng sau — chúng là nhóm orchestration, đóng
góp chính là trigger và versioning chứ không phải tính bền.)*

---

*Không sửa mã sản phẩm LTT. Không có mã Node-RED nào được chép vào
`D:\LTTSTUDIOSAPP`.*
