# 03 — BẢN KHAI KHO MÃ NGUỒN MỞ ĐƯỢC KHẢO SÁT

> **Trạng thái:** đã clone xong 7/7 kho. **Chưa đọc mã để rút kết luận kiến
> trúc** — tài liệu này chỉ ghi *cái gì đã lấy, phiên bản nào, giấy phép gì, và
> sẽ đọc chỗ nào*. Kết luận nằm ở tài liệu 04–11.
>
> **Ngày clone:** 2026-09-07 · **Nơi đặt:** `D:\LTT_ARCHITECTURE_LAB\`
> — **ngoài** ranh giới kho sản phẩm `D:\LTTSTUDIOSAPP\`, đúng §0 đề bài.
> **Tổng dung lượng:** 1,0 GB (clone nông `--depth 1` tại tag ổn định).
> **Không có tệp nào của bên thứ ba nằm trong kho sản phẩm.** `CONFIRMED`

---

## 1. BẢNG KHAI CHÍNH

Mọi dòng dưới đây lấy bằng `git rev-parse HEAD` / `git log -1` **trong chính
bản đã clone**, không lấy từ trang web. `CONFIRMED`

### 1.1 Activepieces

```
URL            https://github.com/activepieces/activepieces
Tag            0.90.2            (bản phát hành ổn định mới nhất)
Commit SHA     fad84c1a58a596d5d0dc1a2f043104f8a4df3af8
Ngày commit    2026-09-04T12:01:02+01:00
Ngôn ngữ       TypeScript (Node.js / Fastify / React)
Dung lượng     303 MB
Giấy phép      MIT Expat  +  vùng "ee/" theo giấy phép riêng
```

⚠️ **Ranh giới giấy phép cần đọc kỹ:** `packages/ee/` và
`packages/server/api/src/app/ee` **KHÔNG** phải MIT — chúng theo
`packages/ee/LICENSE`. Phần ngoài hai thư mục đó là MIT.
*(Đo được: `packages/ee` chỉ 1.099 dòng / 4 tệp trong bản CE này.)*

### 1.2 n8n

```
URL            https://github.com/n8n-io/n8n
Tag            n8n@2.37.10
Commit SHA     5542b8b6419cb6925cca8f11b270c9bfbe09d85e
Ngày commit    2026-09-04T07:37:32Z
Ngôn ngữ       TypeScript (Node.js) + Vue
Dung lượng     309 MB
Giấy phép      Sustainable Use License  +  n8n Enterprise License
```

🔴 **Đây là kho có ràng buộc pháp lý NẶNG NHẤT trong danh sách.**
Trích nguyên văn từ `LICENSE.md` của chính bản đã clone:

> *"Source code files that contain `.ee.` in their filename or `.ee` in their
> dirname are NOT licensed under the Sustainable Use License."*

Và: *"Content of branches other than the main branch … are not licensed."*

**Hệ quả thao tác cho phiên này:** n8n được **đọc để học kiến trúc**, nhưng
**không được chép mã** vào LTT dù chỉ một hàm, cho tới khi có rà soát pháp lý.
Sustainable Use License **không phải** open source theo nghĩa OSI, và LTT là
**SaaS thương mại** — đúng vùng mà giấy phép này nhắm tới. Chi tiết ở
`19_LICENSE_MATRIX.md`. ⛔ Tài liệu này **không** đưa ra kết luận pháp lý.

### 1.3 Node-RED

```
URL            https://github.com/node-red/node-red
Tag            5.0.6            ("Maintenance Release")
Commit SHA     260402832a64373473009188ac01439534c13b36
Ngày commit    2026-09-01T23:29:51+01:00
Ngôn ngữ       JavaScript (Node.js) — không TypeScript ở lõi runtime
Dung lượng     46 MB
Giấy phép      Apache License 2.0  (OpenJS Foundation)
```

⭐ **Giấy phép sạch nhất và kho nhỏ nhất** — 235.892 dòng, đọc hết được.

⚠️ **Bẫy đo lường đã mắc và đã sửa.** Lượt đo đầu cho ra "61.393 dòng / 232
tệp" vì bộ đếm loại trừ mọi thư mục tên `node_modules`. Nhưng Node-RED đặt
**mã nguồn thật** ở `packages/node_modules/@node-red/…` — nên phép đo đã bỏ qua
gần **75 %** kho. Số đúng: **235.892 dòng / 912 tệp**.
*(Ghi lại vì đây đúng lớp lỗi "đọc thứ đại diện thay vì đọc thứ thật".)*

### 1.4 Kestra

```
URL            https://github.com/kestra-io/kestra
Tag            v1.3.37
Commit SHA     035a5b36f5742b168b9e2ed1615c8e1e1d215093
Ngày commit    2026-09-02T17:33:44Z
Ngôn ngữ       Java (Micronaut, Gradle) + Vue
Dung lượng     47 MB
Giấy phép      Apache License 2.0
```

⚠️ Kho CE này **không chứa** phần EE (kho riêng). Nên nhận xét về năng lực EE
sẽ là `UNKNOWN`, không được suy từ tài liệu marketing.

### 1.5 Windmill

```
URL            https://github.com/windmill-labs/windmill
Tag            v1.804.0
Commit SHA     c37f59e22a1948d63f10ad443690a6d341248c5b
Ngày commit    2026-09-05T11:11:54Z
Ngôn ngữ       Rust (backend) + Svelte (frontend)
Dung lượng     161 MB
Giấy phép      AGPLv3 (mặc định) · Apache-2.0 (một số phần) · EE độc quyền
```

🔴 **AGPLv3 là ràng buộc mạnh cho một SaaS.** Trích `LICENSE` của bản đã clone:

> *"Every file is under License AGPL unless otherwise specified"* — và
> *"The files under `backend/` are AGPLv3 Licensed, except any snippets of code
> under the compile flag `enterprise`."*

AGPL có **điều khoản mạng**: cung cấp dịch vụ qua mạng cho người khác được coi
là phân phối. LTT chạy `app.lttstudios.com` cho khách trả tiền ⇒ **nếu nhúng mã
AGPL vào LTT thì toàn bộ tác phẩm phái sinh có thể phải mở nguồn.**
⛔ Đây là ghi chú cảnh báo, **không** phải tư vấn pháp lý. `19_LICENSE_MATRIX.md`
sẽ trích nguyên văn; quyết định cuối cần rà soát pháp lý của người dùng.

### 1.6 Trigger.dev

```
URL            https://github.com/triggerdotdev/trigger.dev
Tag            v4.5.16
Commit SHA     ee34a4b13710742ae26d94831547fa2b6cddc9bd
Ngày commit    2026-09-02T17:42:04Z
Ngôn ngữ       TypeScript (Node.js, Remix, Prisma, Redis)
Dung lượng     113 MB
Giấy phép      Apache License 2.0
```

⭐ **Apache-2.0 cho một hệ durable execution là tổ hợp hiếm.** Đáng chú ý:
`internal-packages/` có **`run-engine`, `run-queue`, `run-store`,
`schedule-engine`, `compute`** như những gói tách rời — tức ranh giới kiến trúc
đã được chính họ vạch sẵn, thuận cho việc học từng phần.

### 1.7 Temporal

```
URL            https://github.com/temporalio/temporal
Tag            v1.31.2
Commit SHA     19a774302c613da9adc4436ab14278ccdca8e0a5
Ngày commit    2026-07-07T10:54:51-07:00        ← CŨ NHẤT trong 7 kho (2 tháng)
Ngôn ngữ       Go
Dung lượng     46 MB
Giấy phép      MIT
```

⭐ **MIT — giấy phép dễ chịu nhất trong danh sách.**
⚠️ Đây là **máy chủ** Temporal. SDK (Go/TS/Python) nằm ở kho riêng, **chưa
clone**. Nếu phương án D (§14 đề bài) được cân nhắc nghiêm túc thì phải clone
thêm `temporalio/sdk-python` — ghi lại ở §5.

---

## 2. QUY MÔ THẬT — và điều nó nói về việc "đọc mã"

Đo bằng bộ đếm riêng (`scratchpad/do_kho.py`), loại trừ `.git`, `dist`, `build`,
`target`, `node_modules` (trừ Node-RED, xem §1.3). `CONFIRMED`

| Kho | Tệp mã | Dòng | Ngôn ngữ chính | So với LTT |
|---|---:|---:|---|---:|
| n8n | 21.505 | **4.125.451** | TypeScript 3,74 M · Vue 289 K | **44×** |
| trigger.dev | 4.925 | 977.326 | TypeScript 911 K | 10× |
| activepieces | 13.460 | 1.375.920 | TypeScript 1,37 M | 15× |
| windmill | 6.305 | 1.346.331 | Rust 441 K · Svelte 364 K · TS 360 K | 14× |
| temporal | 2.796 | 872.231 | Go 856 K | 9× |
| kestra | 3.171 | 313.175 | Java 201 K · Vue 58 K | 3× |
| node-red | 912 | 235.892 | JavaScript 164 K | 2,5× |
| **LTT** *(đối chiếu)* | — | **~93.000** | Python 92 K + TS 2 K | 1× |

*(LTT = `platform_core` 31.745 + `apps` 46.862 + `server` 13.997 ≈ 92.604, chưa
tính 118.952 dòng test.)*

### 2.1 🔴 Phần lớn khối lượng đó KHÔNG phải engine

Đo Activepieces theo từng gói:

| Gói | Dòng | Là gì |
|---|---:|---|
| **pieces** | **926.762** (67 %) | 10.077 tệp **connector** — không phải lõi |
| server | 242.175 | API + orchestration |
| web | 169.427 | giao diện |
| core | 25.491 | mô hình dùng chung |
| cli / ee / tests-e2e | 6.109 | |

⇒ **Lõi thi hành thật của Activepieces vào khoảng 270 K dòng, không phải 1,37 M.**
n8n gần chắc chắn cùng dạng (`packages/nodes-base` là thư viện connector).

⭐ **Đây là ghi chú phương pháp quan trọng nhất của bước 3.** Nếu chấm điểm theo
tổng số dòng thì mọi kết luận sẽ méo: một dự án có 10.000 connector trông "lớn
gấp 15 lần" trong khi bộ lập lịch của nó có thể **nhỏ hơn** của LTT. Từ tài liệu
04 trở đi, mọi số quy mô phải nói rõ *đang đo lõi hay đo thư viện*.

---

## 3. PHÂN LOẠI TRƯỚC KHI SO SÁNH

Đề bài §4 yêu cầu điều này, và nó quan trọng: **không chấm chung một bảng những
thứ giải bài toán khác nhau.**

```
┌─ VISUAL AUTOMATION ────────────── người vẽ, bước rẻ, nhiều connector
│    Activepieces · n8n · Node-RED
│    → học: canvas UX · SDK connector · mô hình node/edge
│    ✗ đừng học: lập lịch quanh tài nguyên khan hiếm (họ không có bài toán này)
│
├─ DURABLE EXECUTION ────────────── lập trình viên viết code, bền là trọng tâm
│    Temporal · Trigger.dev
│    → học: waitpoint · replay/reconcile · idempotency · heartbeat · huỷ
│    ✗ đừng học: canvas (họ không có), mô hình node có kiểu (họ không cần)
│
├─ ORCHESTRATION ────────────────── vừa YAML/code vừa UI, hạ tầng doanh nghiệp
│    Kestra · Windmill
│    → học: mô hình version · trigger · concurrency · lưu trạng thái
│
└─ (chưa clone) DATA PIPELINE · AI GRAPH · MEDIA NODE GRAPH
     Dagster/Prefect/Airflow · Dify/Flowise/Langflow · ComfyUI
     → xem §5
```

**Ánh xạ sang yêu cầu ở tài liệu 02** — đọc kho nào để trả lời câu nào:

| Yêu cầu LTT | Đọc chủ yếu ở |
|---|---|
| `WF-102/103` Edge là thực thể, data vs control | Node-RED, n8n, Kestra |
| `WF-105` Version bất biến + hash | Activepieces (`flow-version`), Kestra, Windmill |
| `WF-106` Subworkflow | Node-RED (`Subflow.js`), Temporal (child workflow) |
| `WF-201/202` Song song, **lập lịch biết tài nguyên** | Trigger.dev (`run-queue`), Temporal (`matching`), Windmill (`windmill-queue`) |
| `WF-203` JOIN đa ngữ nghĩa | **Activepieces (`flow-run/waitpoint/should-release-barrier`)**, Kestra |
| `WF-204` ForEach + concurrency | Kestra, Windmill (`worker_flow.rs`), n8n |
| `WF-205` Rẽ nhánh theo dữ liệu | tất cả — đối chiếu *cạnh* vs *node Router* |
| `WF-301/303` Trạng thái bền, reconcile vs replay | **Temporal (`service/history`)**, Trigger.dev (`run-engine`) |
| `WF-302` Bảo đảm + at-most-once | Temporal, Trigger.dev |
| `WF-401/402` Waitpoint + đánh thức | **Activepieces (`waitpoint/`)**, Trigger.dev, Temporal |
| `WF-601` Artifact có danh tính | Windmill (`windmill-object-store`), n8n (`blob-storage`) |
| `WF-701/702` Hệ kiểu cổng, cardinality | Node-RED, n8n, Activepieces |
| `WF-703/705` Một nguồn luật + SDK | Activepieces (piece framework), n8n (`create-node`) |
| `WF-801` Trigger đa dạng | **Windmill** (14 gói `windmill-trigger-*`), Kestra |
| `WF-805` Quan sát tầng workflow | Trigger.dev (`tracing`, `clickhouse`), Kestra |

---

## 4. ĐIỂM VÀO ĐỌC MÃ — đã xác minh tệp/thư mục TỒN TẠI

Mọi đường dẫn dưới đây đã được kiểm bằng `ls`/`find` trên bản clone.
`CONFIRMED` (tồn tại) — nội dung thì **chưa đọc**.

### Activepieces
```
packages/core/execution/src/lib/flow-run/            ← flow-execution, execution-journal,
                                                       step-output, log-serializer
packages/core/execution/src/lib/flow-run/waitpoint/  ★ nguyên hàm waitpoint
packages/core/execution/src/lib/engine/
packages/server/api/src/app/flows/{flow,flow-run,flow-version}/
packages/server/engine/        · packages/server/sandbox/
packages/pieces/                                     ← SDK connector (10.077 tệp)
test: packages/core/execution/test/flow-run/waitpoint/should-release-barrier.test.ts
```

### n8n
```
packages/core/src/execution-engine/workflow-execute.ts   ★ bộ thi hành
packages/core/src/execution-engine/ · binary-data/ · nodes-loader/
packages/cli/src/active-workflow-manager.ts · concurrency/ · execution-lifecycle/
packages/cli/src/scaling/ (kiểm tra) · packages/workflow/ · packages/nodes-base/
packages/@n8n/{db,engine,expression-runtime,extension-sdk,create-node}/
```

### Node-RED
```
packages/node_modules/@node-red/runtime/lib/flows/{Flow.js,Subflow.js,Group.js,util.js}
packages/node_modules/@node-red/runtime/lib/nodes/
packages/node_modules/@node-red/editor-client/          ← canvas (SVG tự viết)
packages/node_modules/@node-red/registry/
```

### Kestra
```
core/src/main/java/io/kestra/core/runners/{Executor,ExecutorInterface,ExecutorState}.java
core/src/main/java/io/kestra/core/models/executions/
executor/src/main/java/io/kestra/executor/{ExecutorService,SLAService,FlowTriggerService}.java
scheduler/ · worker/ · jdbc-postgres/ · model/ · webserver/ · ui/
```

### Windmill
```
backend/windmill-worker/src/worker_flow.rs      ★ máy trạng thái flow
backend/windmill-queue/ · windmill-common/ · windmill-api-flows/ · windmill-api-jobs/
backend/windmill-trigger-*/  (14 gói: http, kafka, mqtt, nats, postgres, sqs, …)
backend/windmill-object-store/ · backend/migrations/
frontend/  (Svelte) · openflow.openapi.yaml     ← lược đồ flow công khai
```

### Trigger.dev
```
internal-packages/run-engine/       ★ lõi thi hành
internal-packages/run-queue/        ★ hàng đợi
internal-packages/run-store/ · schedule-engine/ · compute/ · database/ (Prisma)
apps/webapp/ · apps/supervisor/     ← điều phối tiến trình chạy
internal-packages/{tracing,metrics-pipeline,clickhouse}/
```

### Temporal
```
service/history/          ★ history_engine.go, chasm_engine.go, handler.go
service/matching/         ★ hàng đợi task
service/frontend/ · service/worker/
common/persistence/ · schema/ · proto/ · api/
```

---

## 5. NHỮNG THỨ CHƯA CLONE — và vì sao

| Kho | Vì sao chưa | Điều kiện để clone |
|---|---|---|
| `temporalio/sdk-python` | Kho `temporal` là **máy chủ**; SDK là kho riêng | **Bắt buộc** nếu phương án D (dựng V2 quanh Temporal) vào vòng chấm nghiêm túc |
| ComfyUI | Media node graph — gần LTT nhất về *hình dạng bài toán* (node ảnh, GPU, ống dẫn media) | **Nên clone** ở tài liệu 11 — F4 nói tải của LTT giống ComfyUI hơn giống Zapier |
| Dify / Flowise / Langflow | AI graph | Clone nếu tài liệu 11 cần đối chứng về mô hình node LLM |
| Dagster / Prefect / Airflow | Data pipeline — mô hình *asset/partition*, khác bài toán | Chỉ clone nếu cần học **versioning** hoặc **backfill** |
| Kestra EE · Windmill EE · n8n EE | Kho/vùng riêng, không công khai | Không clone. Mọi nhận xét về EE ⇒ `UNKNOWN` |

⭐ **ComfyUI là khoảng trống đáng chú ý nhất.** Trong 7 kho đã clone, **không kho
nào** có bài toán "node = 20 phút GPU, output = 2 GB video". Nếu bỏ qua ComfyUI
thì cuộc khảo sát sẽ chỉ học được từ những hệ mà mỗi bước gần như miễn phí —
đúng cái bẫy F4 cảnh báo. Đề xuất: clone ở tài liệu 11.

---

## 6. TÓM TẮT GIẤY PHÉP (bản đầy đủ ở tài liệu 19)

| Kho | Giấy phép | Chép mã vào LTT? | Đọc để học? |
|---|---|---|---|
| Temporal | **MIT** | 🟢 dễ nhất | ✅ |
| Node-RED | **Apache-2.0** | 🟢 (giữ NOTICE) | ✅ |
| Kestra (CE) | **Apache-2.0** | 🟢 (giữ NOTICE) | ✅ |
| Trigger.dev | **Apache-2.0** | 🟢 (giữ NOTICE) | ✅ |
| Activepieces | MIT, **trừ `ee/`** | 🟡 tránh `ee/` | ✅ |
| Windmill | **AGPLv3** (+ Apache một phần) | 🔴 điều khoản mạng — nguy hiểm cho SaaS | ✅ |
| n8n | **Sustainable Use** + EE | 🔴 hạn chế thương mại rõ ràng | ✅ |

**Ba mức, ba hành vi khác nhau:**
- 🟢 **Có thể mượn mã** (vẫn cần ghi nhận bản quyền).
- 🟡 **Mượn được, nhưng phải né đúng thư mục.** Rủi ro thật: một lần copy-paste
  từ `ee/` không để lại dấu vết nào trong lịch sử git của ta.
- 🔴 **Chỉ đọc để học ý tưởng.** Ý tưởng kiến trúc không có bản quyền; **cách
  diễn đạt** thì có.

⛔ **Tài liệu này không đưa ra kết luận pháp lý.** Nó chỉ trích nguyên văn từ
tệp giấy phép trong bản đã clone và gắn cờ. Trước khi chép bất kỳ dòng nào từ
nhóm 🟡/🔴, cần rà soát pháp lý của người dùng.

---

## 7. QUY TẮC ĐỌC MÃ CHO CÁC TÀI LIỆU 04–11

Chốt ở đây để bảy tài liệu sau nhất quán.

1. **Mọi khẳng định phải kèm:** kho · commit SHA (từ bảng §1) · đường dẫn tệp ·
   tên hàm/lớp · và *điều gì trong đoạn mã đó chứng minh khẳng định*.
2. **Không trích README làm bằng chứng kiến trúc.** README chỉ dùng để định
   hướng tìm tệp.
3. **Không suy từ tên.** `node`, `step`, `task`, `job`, `flow`, `piece` mang
   nghĩa khác nhau ở mỗi dự án (đề bài §7). Ánh xạ về từ vựng LTT ở tài liệu 12.
4. **Không chấm điểm bằng tổng số dòng.** Nói rõ đang đo *lõi* hay *thư viện
   connector* (§2.1).
5. **Nhãn tin cậy bắt buộc:** `CONFIRMED` (chạy được / test chứng minh) ·
   `HIGH` · `INFERRED` · `UNKNOWN`. Không được biến `UNKNOWN` thành sự thật.
6. **Chấm theo bảng của LTT** (tài liệu 02 §12 và §13), không theo điểm mạnh mà
   dự án tự nêu.
7. **Mọi thí nghiệm chạy thử phải nằm trong lab**, không bao giờ trong
   `D:\LTTSTUDIOSAPP`.

---

## 8. TRẠNG THÁI MÁY SAU BƯỚC NÀY

```
D:\LTT_ARCHITECTURE_LAB\        1,0 GB   (7 kho, clone nông tại tag)
D:  còn trống                    41 GB / 466 GB  (92 % đầy)  ⚠️ cần để mắt
D:\LTTSTUDIOSAPP\               không đổi ngoài docs/architecture/workflow_v2_audit/
```

⚠️ Ổ D: đang 92 % đầy. Nếu tài liệu 09 cần **chạy thật** một hệ nào đó (Docker,
Postgres, Redis, node_modules), dung lượng sẽ tăng nhanh — `n8n` + `trigger.dev`
cài đủ phụ thuộc có thể thêm vài GB. **Cân nhắc chuyển lab sang ổ C: (còn 459 GB)
trước bước 09** nếu dựng môi trường chạy.

---

## 9. BƯỚC KẾ TIẾP

`04_ACTIVEPIECES_AUDIT.md` — đọc mã thật, bắt đầu từ Activepieces vì:
(a) giấy phép dễ chịu nhất trong nhóm *visual automation*;
(b) **nó đã có `waitpoint` như một nguyên hàm bậc một** — đúng thứ LTT thiếu
nhất (`WF-401`, và LTT hiện thay bằng polling 2 giây);
(c) lõi thi hành ~270 K dòng, đọc được trong một lượt.

Câu hỏi mang vào tài liệu 04, theo đúng thứ tự sẽ trả lời:
`WF-102` edge · `WF-105` version · `WF-201` song song · `WF-203` join/barrier ·
`WF-401` waitpoint · `WF-703/705` SDK piece · `WF-501` chi phí *(dự đoán: không có)*.

---

*Chưa rút một kết luận kiến trúc nào về bất kỳ dự án nào. Không sửa mã sản phẩm.
Không có mã bên thứ ba nằm trong `D:\LTTSTUDIOSAPP`.*
