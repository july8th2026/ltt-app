# 30 — QUYẾT ĐỊNH KIẾN TRÚC CUỐI CÙNG & ADR

> Tài liệu kết luận. Mọi khẳng định truy về `01`–`29`.
> **Ngày:** 2026-09-07 · **Cây:** `D:\LTTSTUDIOSAPP` nhánh `admin-mvp-v3`
> **Bằng chứng nền:** 7 kho OSS đọc mã (ghim SHA) · 28 ngày log production ·
> 4 phép đo chạy được trên chính LTT.

---

## 1. NĂM PHƯƠNG ÁN — CHẤM BẰNG BẰNG CHỨNG

### A. Adopt gần như trọn một nền tảng OSS — ❌ **LOẠI**

**Bằng chứng loại bỏ:** `21_22 §22.2` — **`ADOPT = 0`** trên 38 hệ con.
Và lý do có cấu trúc, không phải ngẫu nhiên:

```
Ba kho MẠNH NHẤT về runtime  (Trigger.dev · Temporal · Windmill)
   →  KHÔNG kho nào có mô hình đồ thị node+cạnh mà Canvas LTT đứng trên

Ba kho CÓ CANVAS            (Activepieces · n8n · Node-RED)
   →  CẢ BA thất bại ở WF-301 (trạng thái là một khối / không lưu gì)
```

Không tồn tại kho vừa có đồ thị vừa có runtime bền. Adopt một cái là **mất nửa
kia**. `CONFIRMED`

### B. Fork một nền tảng rồi sửa nhiều — ❌ **LOẠI**

Cùng bằng chứng như A, cộng ba yếu tố định lượng:

| | |
|---|---|
| **Quy mô phải nuôi** | kho nhỏ nhất có canvas là Node-RED **235.892 dòng**; LTT hôm nay **92.604** dòng sản phẩm. Fork = nuôi một kho **2,5× kho của mình**, bằng ngôn ngữ khác (JS/TS/Go/Rust — LTT là Python) |
| **Thứ phải bỏ** | 13 mục `KEEP` (`21_22 §22.1`) — hợp đồng app · sổ credit · lease GPU 3 tầng · trần chi phí tất định · Public API 24 route. Fork một hệ khác là **vứt cả 13** |
| **Giấy phép** | hai kho phù hợp nhất về tính năng là 🔴: Windmill **AGPLv3** (điều khoản mạng, LTT là SaaS thương mại) và n8n **Sustainable Use** |

### C. Giữ lõi DAG của LTT, chọn lọc mượn kiến trúc OSS — ✅ **CHỌN**

### D. Dựng V2 quanh một engine bền (Temporal), giữ Canvas + registry — ❌ **LOẠI**

**Bằng chứng loại bỏ, `10 §2.2`:**

```
grep -rn "NonDeterministicError|nondeterministic|NonDeterminism" --include=*.go service/ common/
→ 1 kết quả trong 872.231 dòng, và nó là một BỘ ĐẾM
```

Temporal đòi mã workflow **tất định**, và **máy chủ không cưỡng chế được** — nó
chỉ *đếm* vi phạm. Việc phát hiện nằm ở SDK, chạy trong tiến trình người dùng.

LTT ở vị trí ngược lại (`10 §2.2`): bước của LTT là **lời gọi provider ngoài**
(LLM, GPU, nhà cung cấp ảnh) — **không thể tất định**. Phương án D mua một ràng
buộc mà bản chất công việc của LTT vi phạm, để đổi lấy một lợi ích LTT không cần
(tái tạo trạng thái — đã có trong CSDL).

Cộng thêm: Temporal **không có** mô hình đồ thị, nên "giữ Canvas" nghĩa là tự
viết cầu nối đồ thị→mã, tức vẫn phải làm phần khó nhất.

### E. Lai: DAG + domain của LTT + lõi điều phối bền **bên ngoài** — ❌ **LOẠI**

Cùng lý do D về tất định, cộng một lý do vận hành đo được: mọi ứng viên lõi
ngoài đòi **Redis** (Trigger.dev: Redlock) hoặc **một cụm riêng** (Temporal).
LTT đã có đủ nguyên hàm trong Postgres — `pg_advisory_xact_lock` ·
`SELECT FOR UPDATE SKIP LOCKED` · `UNIQUE(resource, slot)` (`01 §6`, `§8.1`).
Thêm một hệ phải vận hành trên máy đã đo **CPU 100 %, 10 lõi vật lý dùng chung**
là mua thêm chỗ hỏng.

---

## 2. 🔴 QUYẾT ĐỊNH: **PHƯƠNG ÁN C**

> **Giữ nguyên tầng nền của LTT. Viết lại tầng orchestration (1.843 dòng chưa
> từng chạy production). Mượn kiến trúc — không mượn mã — từ bốn kho, mỗi kho
> đúng phần nó giỏi nhất.**

```
GIỮ  (13 hệ con)   hợp đồng app · hàng đợi job · sổ credit · lease GPU 3 tầng
                   trần chi phí tất định · phân loại lỗi 3 nhánh · Public API
                   Canvas React Flow · state mang tham chiếu · không sandbox

VIẾT LẠI (4)       trạng thái thi hành · scheduler · edge · hệ kiểu cổng
                   ↳ toàn bộ nằm trong platform_core/agent/ + mô hình edge Canvas
                   ↳ 0 run/28 ngày ⇒ KHÔNG có khách trên phần bị viết lại

MƯỢN KIẾN TRÚC (14)
   Trigger.dev  →  chuỗi ảnh chụp bất biến · lọc hàng đợi hết sức chứa   [Apache-2.0]
   Activepieces →  waitpoint + barrier + sealed + NOT_DISPATCHED         [MIT]
   Windmill     →  parallel/parallelism theo node · mock trong lược đồ    [AGPL — chỉ ý tưởng]
   n8n          →  artifact id tự mô tả backend · cạnh có kiểu            [SUL — chỉ ý tưởng]
   Kestra       →  Concurrency{limit, behavior} · finally                 [Apache-2.0]
   Node-RED     →  middleware 6 hook trên cạnh                            [Apache-2.0]
   Temporal     →  CÁCH VIẾT bảo đảm (hợp đồng, không phải tính năng)     [MIT]

BỎ QUA (8)         replay/event-sourcing · container checkpoint · Redis
                   chọn hàng đợi ngẫu nhiên · custom code node · cây thay đồ thị
                   AiTransform nguyên bản · enum cạnh nở theo năng lực
```

⭐ **Điểm mạnh riêng của phương án C ở đây:** ba trong bốn nguồn mượn quan trọng
nhất đều **Apache-2.0 hoặc MIT** — hai thứ LTT muốn nhất (ảnh chụp bất biến,
lọc sức chứa) nằm ở **Trigger.dev, Apache-2.0**. Hai nguồn 🔴 chỉ đóng góp **ý
tưởng thiết kế**, và ý tưởng không có bản quyền.

---

## 3. HAI PHÉP THỬ NGƯỢC

Trước khi chốt, thử phủ định chính mình.

**① *"C là kết luận mặc định của người không muốn đổi"* — có phải không?**

Không. Bốn hệ con bị xếp `REWRITE` là **thay thẳng, gỡ bản cũ**, gồm cả việc
**gỡ hẳn Plan v1** và **gỡ cột `AgentRun.checkpoint`**. Đó không phải giữ
nguyên. Và quyết định `KEEP` cho 13 mục còn lại **có bằng chứng đối chứng**: ví
dụ trần chi phí tất định — **không kho nào trong bảy kho có** (`12_19 §20.1`).

**② Nếu bỏ ràng buộc "phải có Canvas" thì D có thắng không?**

Vẫn không. `10 §2.2` không nói về Canvas — nó nói **bước của LTT không thể tất
định**. Bỏ Canvas không làm một lời gọi GPU trở nên tất định.

---

## 4. ADR — BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

```
ADR-WF-001   Kiến trúc LTT Workflow V2
Trạng thái   ĐỀ XUẤT — chờ phê duyệt trước khi viết mã
Ngày         2026-09-07
```

### Bối cảnh

LTT là nền tảng SaaS đa tenant bán công cụ AI theo credit. Lớp orchestration
hiện tại (`platform_core/agent/`, 1.843 dòng) đã đúng về **nguyên tắc** (tất
định, báo giá trước, tách LLM khỏi thi hành) nhưng thiếu phần lớn nguyên hàm và
có bốn nút thắt **đo được**:

| Đo được | Nguồn |
|---|---|
| **0** job `agent.advance` / 28 ngày — chưa từng chạy production | `01 §A.1` |
| **92,2 %** lượt nhặt job kết thúc bằng nhả ra; **13,7** lượt nhặt / 1 job xong | `01 §A.3` |
| **`31+N`** câu SQL mỗi tick, lặp mỗi 2 giây | `01 §5.6` |
| trần song song **cứng 4 step**, không khai được | `01 §5.3` |
| **145** lần hold credit treo / 28 ngày | `01 §A.5` |
| worker restart **13,6 lần/ngày**; `AmbiguousProviderError` **10 lần**/28 ngày | `01 §A.6`, `§A.4` |

### Quyết định

**Phương án C.** Giữ tầng nền; viết lại tầng orchestration; mượn kiến trúc từ
bốn kho theo đúng phần mỗi kho giỏi.

**Bảy chốt kỹ thuật:**

| # | Chốt | Mức |
|---|---|---|
| 1 | Trạng thái thi hành = **chuỗi ảnh chụp BẤT BIẾN**, ghi cả lần chuyển bị từ chối | `HIGH` |
| 2 | Hàng đợi **lọc theo sức chứa TRƯỚC khi nhặt** | `HIGH` |
| 3 | Waitpoint là **thực thể độc lập**, nối run bằng bảng **nhiều-nhiều** | `HIGH` |
| 4 | Định nghĩa workflow **lai**: JSONB bất biến là chân lý + bảng chỉ mục dẫn xuất | `HIGH` |
| 5 | Đánh thức: **bảng `wakeup`** là chân lý; `LISTEN/NOTIFY` chỉ gia tốc | `HIGH` |
| 6 | Điều kiện **trên cạnh**; biểu thức = **tập toán tử cố định** | `HIGH` |
| 7 | **Giữ React Flow** | `CONFIRMED` |

### Hệ quả

**Tích cực**
- Phá được 9/10 ngưỡng số (`M1`–`M10`), mỗi ngưỡng có cơ chế cụ thể (`23_24 §8`)
- Giữ nguyên 13 hệ con đã trả giá để có
- Không tăng bề mặt vận hành: **không Redis, không cụm mới**
- Phần viết lại **không có khách** ⇒ không di trú runtime, không cờ bật dần
- Ba nguồn mượn chính là Apache-2.0/MIT

**Tiêu cực / phải chấp nhận**
- **7–10 tuần** một người làm liên tục (`27_29 §28.6`)
- Bảng `node_run_snapshot` phình theo số lần chuyển trạng thái (`R3`)
- Ba mục `INFERRED` **không có đối chứng ngành** (`R2`) — hệ quả của sổ nợ `N1`
- Đợt 1 chạm mã **đang phục vụ thật** (`R1`) — rủi ro cao nhất lộ trình

**Bị loại bỏ vĩnh viễn**
- Plan v1 · `AgentRun.checkpoint` · `canvas_to_plan`/`plan_to_canvas`
- Ý tưởng adopt/fork một nền tảng OSS

### Điều kiện xét lại ADR

| Nếu | Thì |
|---|---|
| Đợt 1 **không** đưa `M3` xuống ≤2,0 | xét lại chốt #2 — có thể sức chứa vật lý không đọc được đủ rẻ |
| Đo lại `M1` trên Postgres cho kết quả khác hẳn | xét lại chốt #1 |
| LTT chuyển sang cho khách **viết mã bước** | xét lại phương án D — lúc đó tất định thành khả thi |
| `node_run_snapshot` phình quá mức ở quy mô thật | thêm gộp/lưu trữ, **không** quay lại mô hình khối |

---

## 5. ĐIỀU NÀY KHÔNG CHO PHÉP

⛔ **Không dòng mã sản phẩm nào được viết** cho tới khi có phê duyệt rõ ràng.
Đề bài §31 chốt điểm dừng này, và nó vẫn nguyên hiệu lực.

Lược đồ SQL ở `23_24`, hợp đồng `ToolSpec` ở `25_26`, lộ trình ở `27_29` đều là
**đề xuất**. Chưa migration nào được viết, chưa `platform_core/registry.py` bị
sửa một ký tự.

---

*`00_EXECUTIVE_SUMMARY.md` trả lời 20 câu của đề bài §25.*
