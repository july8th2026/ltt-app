# API FULL EXTENSION — PROGRESS

Pack: `LTT_API_FULL_EXTENSION_PACK_V2_OPTIMIZED` (v2.0), 21 prompt.
Chạy **sau** Public API V2 (Q92, 17/17 PASS).

**Chế độ chạy:** pack này khai `strict sequential; one prompt per Claude turn`
(`MANIFEST.json`) và `START_HERE.md` viết "Mỗi lượt chỉ 1 prompt". Chủ sản phẩm
cũng ra lệnh "dừng sau EXT-01". → **Không** áp dụng chế độ chạy liên tục của pack
V2. Mỗi lượt một prompt, dừng và báo cáo.

Checkpoint chạy **full gate**: EXT-04, 08, 12, 16, 20, 21.

| # | Prompt | Trạng thái | Ngày |
|---|---|---|---|
| 01 | V2 reconciliation, master gap matrix, dependency graph | **PASS** | 2026-08-13 |
| 02 | Protocol / execution modes / error-retry standards | **PASS** | 2026-08-13 |
| 03 | Models / capabilities / tool catalog / schema chain | **PASS** | 2026-08-13 |
| 04 | Projects / service accounts / delegated auth decision | **PASS** | 2026-08-13 |
| 05 | Developer API tab / information architecture | **PASS** | 2026-08-13 |
| 06 | Schema-driven apps/models/tools variable reference | **PASS** | 2026-08-13 |
| 07 | Quickstart / env vars / examples / recipes | chưa chạy | — |
| 08 | Playground / request builder / job inspector | chưa chạy | — |
| 09 | Request logs / trace / job timeline | chưa chạy | — |
| 10 | Webhook console / event catalog / resend | chưa chạy | — |
| 11 | Usage / budgets / credit alerts / notifications | chưa chạy | — |
| 12 | Sandbox / test mode / live isolation | chưa chạy | — |
| 13 | API admin console core | chưa chạy | — |
| 14 | Admin policy / tiers / quota / kill switch | chưa chạy | — |
| 15 | Pricing catalog / versioned credits / margin | chưa chạy | — |
| 16 | Admin operations / security / support trace | chưa chạy | — |
| 17 | Versioning / changelog / deprecation / status | chưa chạy | — |
| 18 | SDK / CLI / Postman / OpenAPI ecosystem | chưa chạy | — |
| 19 | Privacy / retention / export / delete | chưa chạy | — |
| 20 | Full app/tool/model/execution-mode certification | chưa chạy | — |
| 21 | Final audit / load / chaos / security / release gate | chưa chạy | — |

---

## EXT-01 — V2 RECONCILIATION, MASTER GAP MATRIX, DEPENDENCY GRAPH ✅

### Entry gate — V2 có ổn định không?

**Có.** Không có blocker; Extension được phép bắt đầu. Bằng chứng (không phải ý
định của prompt V2):

| Trục | Bằng chứng thật |
|---|---|
| Kernel | `server/api/inventory.py` đóng băng 22 route; `test_178` so khớp **hai chiều** route ↔ inventory ↔ OpenAPI |
| Auth | `keys.py` + 54 test (`test_179` 35, `test_180` 19) |
| Credit/idempotency | `test_193`: 839 request trùng khoá → **1 job, 1 hold**; crash giữa hold và queue → **0 hold, 0 job**; 7 kịch bản bơm lỗi đều `reconcile ok` |
| Tool contract | `registry.py:322` fail-closed, 7 khoá hợp đồng cố định; golden `tests/golden/public_api_catalog_v1.json` |
| Migration head | `c9d0e1f2a3b4`, không đổi trong lượt này |
| Gate | `tools\gate.py` → **PASS 10/10** (pytest 2.530,9 s) trước khi bắt đầu |
| Quy mô test Public API | **317 test** (`--collect-only` trên `test_178`…`test_193`) |

### Reused V2 components (không xây lại gì)

EXT-01 là audit — **không thêm route, không thêm bảng, không thêm phụ thuộc**.
Bảng REUSE (engine nào Extension bắt buộc dùng lại) ở §4 của gap matrix.

### Status before → after

| | Before | After |
|---|---|---|
| Bản đồ nợ của API Platform | không có | 14 domain V2 + 24 domain Extension, mỗi domain có trạng thái + bằng chứng + prompt sở hữu |
| Disposition | 14/14 app (V2) | thêm **21/21 ToolSpec**, mỗi tool có execution mode đề xuất — **không UNKNOWN** |
| Thứ tự thi công | theo ROADMAP của pack | có đồ thị phụ thuộc chứng minh từng cạnh |

### Evidence — những phát hiện đáng kể

1. **`APP_DISPOSITION_V1.md` đếm sai.** Tài liệu ghi "6/21 ToolSpec public" và
   "15 còn lại"; `registry.discover()` thật cho **21 tool, 5 public, 16 không**.
   Đã sửa tài liệu. `test_190` không bắt được vì nó kiểm *tập hợp*, không kiểm
   *con số trong câu văn* — ghi lại như một `OBSERVED_DIFFERENCE`.
2. **`X-Correlation-ID` chỉ xuất hiện trên phản hồi bị guard chặn**
   (`server/api/guard.py:44` nằm trong nhánh `except`); phản hồi thành công
   không có header nào. Khách không cầm được id để mở ticket → chặn support
   trace (EXT-16), sửa ở EXT-02.
3. **`Retry-After` không phải header HTTP** — chỉ là trường trong body
   (`limits.py:93`). SDK của LTT hiểu, mọi client generic thì không.
4. **`/developers` không có lối vào**: `server/templates/_header.html` không có
   link nào tới portal. Tính năng có nhưng không ai tìm thấy → EXT-05.
5. **Không có view admin nào cho Public API**: grep `DeveloperApiKey` trong
   `server/admin.py` = 0. `ApiKeyAdmin` ở đó là **khoá provider**, domain khác.
6. **4 bảng Public API không nằm trong bất kỳ chính sách retention nào.**
   `platform_core/job_events.py` có purge cho job event (365/30 ngày);
   `webhook_deliveries` thì phình vô hạn → EXT-19, và là rủi ro thật nếu bật API
   trước khi tới prompt đó.
7. **Không tồn tại khái niệm execution mode** (grep = 0). Mọi tool hiện là
   async-job ngầm định; `chataistudio` là ứng viên STREAM đầu tiên nhưng không
   có Job nên chưa có ngữ nghĩa credit/cancel.
8. **Giá không có phiên bản**: `invocation.price()` gọi thẳng
   `registry.credit_for(job_type, params)`. Đổi bảng giá là đổi hồi tố cách đọc
   lịch sử → EXT-15.

### Files / migrations / config

Mới: `docs/PUBLIC_API/FULL_PLATFORM_GAP_MATRIX.md`,
`docs/PUBLIC_API/FULL_PLATFORM_DEPENDENCY_GRAPH.md`,
`docs/PUBLIC_API/FULL_PLATFORM_TARGET.md`, `docs/PUBLIC_API/EXTENSION_PROGRESS.md`.

Sửa: `docs/PUBLIC_API/APP_DISPOSITION_V1.md` (hai con số đếm sai).

**Không** migration, **không** biến cấu hình mới, **không** route mới, **không**
phụ thuộc mới. Head vẫn `c9d0e1f2a3b4`.

### Tests

Không thêm test — prompt này không thêm hành vi. Bằng chứng dùng để audit lấy từ
test sẵn có (317 test Public API) và từ `registry.discover()` chạy thật.

Regression: `python tools\gate.py --quick` → **PASS** (secret scan, lint hợp đồng
app, undefined names, silent-except, i18n, system profile, 3 frontend).
Full gate không chạy lại: EXT-01 không đổi một dòng mã chạy được, và lần chạy
full ngay trước đó (cùng cây mã, cộng thêm 4 file `.md`) đã PASS 10/10.
Checkpoint full gate kế tiếp theo `MANIFEST.json` là EXT-04.

### Performance / browser

Không áp dụng — không đổi mã chạy, không đổi giao diện.

### Risks / deferred

| # | Rủi ro | Mức | Xử lý |
|---|---|---|---|
| X1 | **Toàn bộ V2 chưa commit** (26 `M` + 31 `??`) và Extension sẽ chồng thêm lên cùng cây bẩn | **Cao** | Nên commit V2 **trước EXT-02**. Là lệnh của chủ sản phẩm, tôi không tự commit |
| X2 | `webhook_deliveries` không retention | Trung bình | EXT-19 |
| X3 | Giới hạn nhịp per-process | Trung bình | EXT-14, phải có ADR nếu muốn scale ngang |
| X4 | Portal không có lối vào từ header | Thấp | EXT-05 |
| X5 | Không có correlation header trên phản hồi thành công | Trung bình | EXT-02 |

**Năm quyết định sản phẩm** (§4 của dependency graph) — **đã chốt 2026-08-13**,
chủ sản phẩm uỷ quyền cho Claude quyết và sẽ điều chỉnh nếu vận hành cho thấy
vấn đề. Nội dung đầy đủ kèm điều kiện xem lại ở
[`EXTENSION_DECISIONS.md`](EXTENSION_DECISIONS.md):

| # | Chốt | Prompt |
|---|---|---|
| D1 | Hoãn delegated OAuth; thay bằng restricted key (project + IP + hạn dùng + trần chi) | EXT-04 |
| D2 | Đo thời lượng phía server lúc báo giá; job API không được top-up → **mở được 3 tool** | EXT-02/03 |
| D3 | Trần 2.000 credit/ngày, **chỉ đếm chi tiêu qua API**, cảnh báo 50%/80% | EXT-11/14 |
| D4 | Sandbox mock đi đúng đường code, khoá `ltt_sk_test_` không tiêu được tiền | EXT-12 |
| D5 | Định nghĩa mode STREAM nhưng **không** mở chat qua sidecar | EXT-02/20 |

Mỗi quyết định được nâng thành mục Q trong `docs/QUYET_DINH_NEN_TANG.md` khi
prompt sở hữu thi công xong, theo giao thức ở `AGENTS.md`.

D3 kéo theo **một lỗi phải sửa**, không phải tuỳ chọn: `credit_spent_since()`
đang cộng cả chi tiêu trên giao diện web, nên khách dùng web nhiều sẽ làm API của
chính họ ngừng chạy.

### Rollback

Xoá 4 file `.md` mới và hoàn nguyên 2 con số trong `APP_DISPOSITION_V1.md`.
Không có tác động runtime.

### Acceptance Gate

| Yêu cầu của EXT-01 | Kết quả |
|---|---|
| Mọi domain có status + evidence + owner prompt | ✅ 14 domain V2 + 24 domain Extension |
| Không đánh DONE chỉ vì prompt V2 từng yêu cầu | ✅ mỗi `DONE` trỏ tới test/route thật; và audit đã bắt được 1 sai lệch tài liệu + 4 lỗ hổng chưa ai ghi |
| 100% app/tool có disposition, không UNKNOWN | ✅ 14/14 app, 21/21 ToolSpec (model và execution mode được nêu rõ là **chưa** có disposition → chủ sở hữu EXT-03/EXT-20) |
| Dependency graph chứng minh thứ tự EXT-02…21 | ✅ từng cạnh có lý do; có cả danh sách cạnh **không** tồn tại |
| Không xây feature lớn | ✅ 0 route, 0 bảng, 0 migration |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế tiếp: `prompts/02_PUBLIC_API_PROTOCOL_EXECUTION_MODES_ERROR_RETRY_STANDARDS.txt`
Khuyến nghị **trước** khi chạy: commit V2 (rủi ro X1).

---

## EXT-02 — PROTOCOL CONTRACT, EXECUTION MODES, ERROR/RETRY STANDARDS ✅

### Entry gate

EXT-01 PASS ✅. Head vẫn `c9d0e1f2a3b4` (**không** migration mới). Cây mã sạch
tại `5978fcc` trước khi bắt đầu.

### Reused V2 components

`errors.py` (mở rộng, không thay), `limits.py`, `catalog.py`, `inventory.py`,
`guard.py`, `registry._validate_api_contract`, `tools/build_public_api_docs.py`
(thêm block thứ hai thay vì công cụ thứ hai). **0 route mới, 0 bảng mới, 0
migration, 0 phụ thuộc mới.**

### Status before → after

| Hạng mục | Before | After |
|---|---|---|
| Execution mode | không tồn tại (grep = 0) | khai báo ở **cả** route và tool, có kiểm |
| Mã lỗi | 14, phần lớn chung chung | **23**, mỗi mã có retry + hành động |
| 3 nguyên nhân 409 khác nhau | cùng mã `conflict` | `insufficient_credit` / `price_changed` / `idempotency_conflict` / `idempotency_in_progress` |
| `X-Correlation-ID` | chỉ trên phản hồi bị guard chặn (X5) | **mọi** phản hồi |
| `X-LTT-API-Version` | không có | mọi phản hồi |
| `Retry-After` | chỉ trong body | header **và** body, cùng một số |
| `Location` khi tạo job | không có | có, và GET được ngay |
| Deprecation | không có cơ chế | `Deprecation`/`Sunset` (RFC 8594) theo dữ liệu inventory |
| Tài liệu bảng lỗi | không có | **sinh tự động** từ registry, `--check` chặn drift |

### Evidence

- `platform_core/public_api/protocol.py` — 5 mode, luật của từng mode,
  `PublicOperationContract` tự kiểm lúc khởi tạo, quy ước chung.
- `platform_core/public_api/error_registry.py` — 23 mã × (status, retry class,
  có phải dùng lại Idempotency-Key, hành động) + ma trận retry theo status.
- `MODES_IN_USE` chỉ có `ASYNC_JOB` và `SYNC`. Manifest khai `STREAM`/`BATCH`
  bị **registry từ chối nạp** — đặc tả xong không có nghĩa là dùng được.
- 21 route `SYNC`, **1** route `ASYNC_JOB` (`POST /jobs`), và có test chứng minh
  không route `SYNC` nào tạo job.

### Tests

`tests/test_194_public_api_protocol.py` — **29 test**. Đáng kể:
- mọi route/tool khai mode nền tảng thi hành được;
- manifest **không** opt-in được vào mode chưa thi hành (2 test tham số hoá);
- mọi `CODE_*` trong mã nguồn phải có trong registry (bánh cóc), và status trong
  registry phải khớp status mà helper thật sự ném;
- 401 **không** bị tách — test cấm các mã `invalid_api_key`/`key_expired` xuất
  hiện trong registry;
- header trên phản hồi thành công, phản hồi lỗi và phản hồi ẩn danh; id trong
  header **bằng** id trong problem body; caller **không** tự chọn được id;
- `Retry-After` header khớp body; `Location` khi 201 và GET được;
- ba mã 409 phân biệt được bằng test hành vi thật (hết credit / quote hết hạn /
  trùng key khác body);
- SDK Python và TypeScript retry **đúng** tập status mà registry cho là retry
  được, và không được retry mù 409.

Toàn bộ Public API: **345 test** (`test_178`…`test_194`) — pass.
Quick gate: **PASS 9/9**. Full gate: theo `MANIFEST.json`, checkpoint kế là
EXT-04; EXT-02 chạy targeted + quick.

Bốn test cũ đổi kỳ vọng (`test_180`, `test_181`, `test_182`, `test_191`): mã lỗi
được **làm cụ thể hơn**, không phải test bị sửa để che semantics sai. Đổi được vì
`/api/v1` chưa deploy — sau khi có khách thật thì đây sẽ là breaking change và
phải đi đường version.

### OBSERVED_DIFFERENCE

Pack yêu cầu tách `invalid_api_key`, `key_expired/revoked` thành mã riêng.
**Không làm.** Tách ra biến endpoint thành máy tra key id: kẻ tấn công đoán một
triệu key id và học được cái nào tồn tại. `tests/test_192` đã khoá tính chất
"mọi thất bại credential trả một câu trả lời"; COMMON_RULES §2 nói code+test
thắng prompt. Người gọi thật có portal, nơi nói chính xác khoá của họ sao lại
chết. Ghi ở `PROTOCOL_V1.md` §4.1.

### Deferred (có lý do, không phải quên)

**Phân loại nguyên nhân job hỏng** (`provider_timeout`, `capacity_unavailable`…)
chưa làm. Muốn đúng thì worker phải **gắn nhãn** lúc hỏng; đoán bằng cách dò
chuỗi lỗi nội bộ sẽ có lúc nói sai, và một nhãn "thử lại được" sai chỗ khiến
khách chạy lại một job chắc chắn hỏng — mất tiền thật. Chủ sở hữu: EXT-16. Hiện
job hỏng **đã được hoàn tiền** nên khách không mất gì; `PROTOCOL_V1.md` §3 nói
thẳng điều này với khách.

### Rollback

Xoá `protocol.py`, `error_registry.py`, `PROTOCOL_V1.md`, `test_194`; hoàn
nguyên các mã lỗi cụ thể về helper chung; bỏ 3 header trong `guard.py`. Không có
migration, không có dữ liệu nào phải dọn.

### Acceptance Gate

| Yêu cầu của EXT-02 | Kết quả |
|---|---|
| Không operation public nào có mode UNKNOWN | ✅ 22 route + 5 tool, có test |
| Retry rules không cho chargeable POST tạo bản sao | ✅ registry buộc `reuse_idempotency_key`; SDK bị test chặn retry mù 409 |
| Stream/batch semantics có test nếu enabled | ✅ **không** enabled; test chứng minh không ai dùng được chúng |
| Docs sinh được từ contract | ✅ bảng lỗi sinh từ registry, `--check` trong `test_191` |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/03_MODELS_CAPABILITIES_TOOL_CATALOG_AND_SCHEMA_CHAIN.txt`

---

## EXT-03 — MODELS / CAPABILITIES / TOOL CATALOG / SCHEMA CHAIN ✅

### Entry gate

EXT-02 PASS ✅ (`16246a3`), cây sạch. Head vẫn `c9d0e1f2a3b4` — **không**
migration.

### Reused V2 components

`catalog.py` (mở rộng), `registry._validate_api_contract`, `pagination`,
`require_scope`, `build_public_api_docs`. **0 bảng mới, 0 migration, 0 phụ
thuộc mới.** Hai route mới: `GET /models`, `GET /models/{model_name}` → **24
route**.

### Status before → after

| Hạng mục | Before | After |
|---|---|---|
| Model | alias nằm **bên trong** hợp đồng từng tool, không ai liệt kê được | domain công khai riêng: alias + capability + stability + tool nào nhận + ràng buộc |
| Capability | không có khái niệm | suy từ chính tên tool (`image.generate` → `image`), không phải trường khai riêng |
| Metadata alias | chỉ là `alias → id nội bộ` | thêm `description`, `stability`, `constraints`, `replaced_by`; khoá lạ bị **từ chối nạp** |
| Hợp đồng tool | không có dấu vân tay | `contract_hash` 16 hex, tính trên chính nội dung khách nhận |
| Đổi tên tool | mất tích hợp cũ | `aliases` — tên cũ vẫn resolve, nhưng **không** thành mục thứ hai trong catalog |
| Schema chain | OpenAPI chỉ mô tả phong bì | schema của **mọi** tool nằm trong `components.schemas` |

### Quyết định đáng nói

**Capability suy ra, không khai báo.** Một trường `capability` trong manifest là
thêm một chỗ phải giữ đồng bộ với tên tool, và lần đầu chúng lệch nhau thì
catalog đang nói dối. `image.generate` thuộc capability `image` **vì** nó tên
như vậy.

**Không publish giá theo model.** Giá phụ thuộc toàn bộ input (bao nhiêu ảnh,
bao nhiêu scene), nên một con số gắn vào model sẽ đúng đủ để được tin và sai đủ
để gây thiệt. `POST /quotes` là nơi duy nhất định giá **một lời gọi**. Có test
khẳng định payload model **không** chứa `credit`/`price`.

**Không publish tình trạng provider (`degraded`).** Tính được từ `api_pool`,
nhưng đường đọc đó phải chạm vào provider/pool nội bộ ngay trên một route đọc
công khai, và `_ung_vien()` còn **mutate** trạng thái key (hồi cooldown, cuộn cửa
sổ). Đổi lại chỉ là một nhãn. Tín hiệu sức khoẻ thuộc EXT-14 (capacity), nơi dữ
liệu vận hành đã sẵn có.

**`capabilities` trả về trong `/models`, không phải `/capabilities`.** Route
`/capabilities` ẩn danh; deployment này bán những miền gì là thông tin thương
mại, và V2 đã chốt danh sách tool nằm sau khoá.

### Tests

`tests/test_195_public_api_models.py` — **25 test**. Đáng kể:
- alias **không bao giờ** lộ id model thật, tên vendor hay slug app — kiểm cả
  trên fixture lẫn trên **catalog thật của repo**;
- khoá lạ trong alias (`provider`) bị registry từ chối → không ai publish được
  tên vendor bằng cách thêm một field vào manifest;
- alias `deprecated` **bắt buộc** nói thay bằng gì, và cái thay thế phải tồn tại;
- khoá bị giới hạn `allowed_tools` thấy **rỗng** cả model lẫn capability — danh
  sách model là hình chiếu của catalog **khách thấy được**, không phải của
  deployment;
- mọi `model_ref` công khai đều có enum giá trị hợp lệ (tiêu chí nghiệm thu);
- mọi input schema là JSON Schema hợp lệ, `additionalProperties: false`, mọi
  `required` đều có khai báo;
- `contract_hash` tính trên body **không kể chính nó**, và đổi khi hợp đồng đổi;
- OpenAPI mang schema của mọi tool **mà không** thêm path nào ngoài inventory.

Toàn bộ Public API: **370 test** — pass. Quick gate: **PASS 9/9**. Docs
`--check`: PASS.

Ba test cũ đổi kỳ vọng: `test_178` (thêm `models` vào capability areas),
`test_193` (đóng băng 22 → **24** route), và hai golden snapshot được sinh lại
(thêm `capability` + `contract_hash`).

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | Contract **compatibility checker** (đổi thế nào là breaking) | EXT-17 |
| — | Tín hiệu `degraded` theo sức khoẻ provider | EXT-14 |
| — | Model của các tool đang DEFER (`video.generate` có ma trận enum theo model) | prompt mở tool, theo D2 |

### Rollback

Bỏ 2 route khỏi inventory + `tools.py`, bỏ `build_models`/`PublicModel`/
`contract_hash`/`aliases` khỏi `catalog.py`, hoàn nguyên `models` của
`apps/taoanh` về dạng chuỗi, xoá `test_195`. Không migration, không dữ liệu.

### Acceptance Gate

| Yêu cầu của EXT-03 | Kết quả |
|---|---|
| Mọi `model_ref` public có giá trị hợp lệ discover được | ✅ có test quét toàn registry |
| Không lộ provider secret/routing nội bộ | ✅ 2 test (fixture + repo thật) + khoá lạ bị từ chối |
| Schema chain single-source PASS | ✅ contract → JSON Schema → OpenAPI trong **một** tài liệu, có test |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/04_PROJECTS_SERVICE_ACCOUNTS_API_CLIENTS_AND_DELEGATED_AUTH_DECISION.txt`
— **checkpoint full gate** theo `MANIFEST.json`.

---

## EXT-04 — PROJECTS, SERVICE ACCOUNTS, API CLIENTS, DELEGATED AUTH ✅

**Checkpoint full gate** theo `MANIFEST.json`.

### Entry gate

EXT-03 PASS ✅ (`f019f73`), cây sạch. Head trước lượt này `c9d0e1f2a3b4`.

### Reused V2 components

`DeveloperApiKey` (thêm 2 cột), `Principal`, `context.client_ip`, portal phiên,
CSRF, `credit`/`jobs` không đổi một dòng. **1 migration mới**, 1 bảng mới, 0 phụ
thuộc mới, **0 route `/api/v1` mới**.

### Phân cấp đã chốt

```
User            billing, credit — mọi thứ nền tảng đã sở hữu (Q92)
 └─ Project     một tích hợp; đơn vị để THU HỒI, ĐẶT NGÂN SÁCH, ĐỌC LOG
     └─ Key     một credential; đơn vị để XOAY
```

Ba quyết định kèm ADR (`EXTENSION_DECISIONS.md`):
- **D1** delegated OAuth: hoãn (đã chốt ở lượt trước).
- **D6** service account: hoãn. Hôm nay **key chính là danh tính máy** — có
  scope, tool allowlist, IP allowlist, hạn dùng, thuộc project. Thêm một thực
  thể một-dòng-mỗi-key mà không có hành vi riêng là thêm join để bảo trì. Thêm
  sau là **cộng thêm**: key đã trỏ project, service account chỉ là chủ sở hữu
  tuỳ chọn bên trong project.
- **D7** bảng OAuth client: **không tạo trước**. Bảng rỗng vẫn phải migrate, sao
  lưu, khôi phục. Hình dạng đã ghi lại để lúc cần không thiết kế từ đầu.

### Migration `d0e1f2a3b4c5` — an toàn cho dữ liệu V2

`project_id` **nullable** + backfill: mỗi tài khoản đang sở hữu key nhận một
project `Default`, key trỏ vào đó. Khoá cũ chạy y nguyên ở **mọi** bước; không
có thời điểm nào key mất quyền. Vòng tiến–lùi–tiến xanh (`test_63`).

Khoá ngoại `project_id` chỉ tạo trên **không phải SQLite**: SQLite không ALTER
thêm được ràng buộc, và batch mode sẽ **copy cả bảng credential** sang bảng mới
rồi đổi tên — đắt và rủi ro, đổi lấy một ràng buộc mà PostgreSQL (Q1, production)
vẫn có đầy đủ. Ghi rõ trong file migration.

UNIQUE mới `uq_api_project_owner_slug` đã vào `tools/restore_drill_schema.py`
(`test_155` yêu cầu).

### Key restrictions

| Ràng buộc | Trạng thái |
|---|---|
| scope | đã có (V2) |
| tool allowlist | đã có (V2) |
| **hạn dùng** | đã có ở CSDL, **giờ đặt được từ portal** (tối đa 1 năm) |
| **IP allowlist (CIDR)** | **mới** — chuẩn hoá về CIDR, tối đa 20 dải |

IP allowlist **fail-closed**: allowlist không rỗng mà không xác định được địa chỉ
người gọi → **từ chối**. Một ràng buộc lặng lẽ ngừng áp dụng khi không đo được
địa chỉ thì không phải ràng buộc.

Khoá bị từ chối vì IP vẫn trả **đúng một** `401 unauthorized` như mọi thất bại
credential khác: nói "đúng khoá, sai địa chỉ" là xác nhận khoá có thật với kẻ
vừa lấy trộm nó.

### Trusted proxy

`is_trusted_peer` giờ hiểu **cả CIDR**, không chỉ địa chỉ chính xác. Cloudflare
công bố biên của họ theo dải; một danh sách chỉ khớp chính xác buộc operator dán
hàng trăm dòng và dán lại mỗi lần dải đổi. Entry sai cú pháp bị **bỏ qua**, không
được tin — một lỗi gõ trong file cấu hình không được biến thành "tin mọi người".

### Tests

`tests/test_196_public_api_projects.py` — **31 test**. Đáng kể:
- lưu trữ project thu hồi khoá **của nó** và không đụng project khác;
- lưu trữ **không xoá** một dòng `jobs` hay `credit_entries` nào — bất biến làm
  cho việc lưu trữ dám mời khách dùng;
- gỡ lưu trữ trả project về nhưng **khoá vẫn revoked** (thu hồi là một chiều);
- project `Default` bị lưu trữ sẽ tự sống lại, nếu không tài khoản không tạo
  được khoá nào nữa;
- allowlist quyết theo dải và **fail-closed** (5 ca tham số hoá);
- header `CF-Connecting-IP` chỉ được tin **từ peer tin cậy** — từ nơi khác thì
  khoá bị từ chối, nếu không IP allowlist sẽ bị đi vòng bởi bất kỳ ai chạm được
  thẳng vào tiến trình;
- khoá **không** project vẫn chạy (hình dạng dữ liệu V2 vẫn hợp lệ);
- backfill của migration diễn lại trên chính bảng nó chạm.

### Browser (bắt buộc theo CLAUDE.md mục 5)

Server dùng-một-lần, cổng **8123**, SQLite tạm — không chạm 8100/8000. Luồng
thật: đăng nhập → tạo project "Trang bán hàng" → tạo khoá trong project đó với
hạn 90 ngày và IP `203.0.113.4, 198.51.100.0/24` → bảng khoá hiện **project,
CIDR đã chuẩn hoá (`203.0.113.4/32`), hạn `2026-11-11`** → lưu trữ project →
khoá chuyển `revoked` và project rời danh sách. **0 lỗi console, 0 request hỏng.**

Trình duyệt bắt được một lỗi test không thấy: slug của "Trang bán hàng" ra
`trang-b-n-h-ng`. Slug tồn tại để **đọc được** trong log và ticket; bỏ dấu tiếng
Việt biến hầu hết tên project thành một hàng gạch nối. Đã sửa (`NFKD` + bỏ dấu,
`đ`→`d`) và có test.

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| X4 | Portal vẫn **không có lối vào từ header** | EXT-05 |
| — | Service account | D6, mở lại khi có tín hiệu đã ghi |
| — | OAuth client + delegated flow | D1/D7 |
| — | Trần chi **theo project** (mới có theo tài khoản) | EXT-11/14 |

### Rollback

`alembic downgrade c9d0e1f2a3b4` (xoá bảng + 2 cột; job/credit/khoá không bị
chạm), gỡ `projects.py`, hoàn nguyên portal và `auth.py`. Khoá đã cấp vẫn chạy
vì `project_id` là nullable.

### Acceptance Gate

### Full gate — checkpoint

Lần 1: **FAIL (1/10)**. pytest **PASS** (2.681,8 s), 8/9 bước còn lại PASS; đỏ
duy nhất là bánh cóc i18n vì `slugify()` có `text.replace("đ", "d")` — một
**bảng chuyển tự**, không phải câu hiển thị. Bánh cóc chỉ đếm chuỗi *chứa ký tự
tiếng Việt* chưa bọc `_()`, nên nó đọc ký tự `đ` như thông điệp chưa dịch.

Sửa bằng `chr(0x0111)` kèm chú thích, **không** nới `tools/check_i18n.py`: bọc
`_()` quanh một ký tự chuyển tự là vô nghĩa, còn sửa công cụ dùng chung để né
một trường hợp cục bộ là làm yếu bánh cóc cho cả repo.

Lần 2, trên cây mã cuối: **`RESULT: PASS` 10/10**, pytest 2.672,9 s.

### Acceptance Gate

| Yêu cầu của EXT-04 | Kết quả |
|---|---|
| Không phải làm lại owner model ở UI sau này | ✅ User → Project → Key; service account/OAuth cắm thêm được mà không dời dòng nào |
| Dữ liệu V2 migrate an toàn | ✅ nullable + backfill; khoá không project vẫn chạy, có test |
| Cross-project/tenant PASS | ✅ `get_owned` lọc theo chủ trong **truy vấn**; lưu trữ chỉ chạm khoá của chính project |
| OAuth chỉ bật khi security gate PASS; hoãn thì có ADR và không ảnh hưởng luồng API key | ✅ D1/D7, luồng API key không đổi một dòng |
| Full gate tại checkpoint | ✅ 10/10 |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/05_DEVELOPER_API_TAB_AND_INFORMATION_ARCHITECTURE.txt`


---

## EXT-05 — DEVELOPER API TAB + INFORMATION ARCHITECTURE ✅

### Entry gate

EXT-04 PASS ✅ (`b3cf664`, full gate 10/10), cây sạch. Head vẫn `d0e1f2a3b4c5`
— **không** migration, **không** route `/api/v1` mới.

### Reused V2 components

Khung template hiện có (`base.html`, `_header.html`), CSS `ltt.css` (+
`asset_ver` cache-bust), phiên đăng nhập + CSRF, `catalog`/`projects`/`keys`/
`usage` đã có. **0 phụ thuộc mới, 0 bảng, 0 migration.**

### Status before → after

| | Before | After |
|---|---|---|
| Lối vào | **không có link nào** tới `/developers` (rủi ro X4) | menu tài khoản trên **cả** trang catalog và header chung → **2 cú bấm** |
| Cấu trúc | một trang dài, mọi thứ xếp chồng | 9 section có route riêng + sub-nav dùng chung |
| Overview | không có | số dư, chi tiêu hôm nay, số project/khoá, job 30 ngày, sức khoẻ webhook, hạn mức, trạng thái dịch vụ |
| Empty state | "Chưa có khóa nào." | ba bước tới lời gọi đầu tiên, có link thẳng |
| Section chưa xây | không được nhắc tới | có tên, gắn nhãn "sắp có", **không** phải link chết |

### Quyết định đáng nói

**Chỗ chưa xây thì nêu tên, không tạo link.** Playground (EXT-08), Nhật ký
request (EXT-09), Thông báo (EXT-11) hiện trong sub-nav dưới dạng chữ xám kèm
nhãn. Hình dạng của khu API là thông tin người tích hợp dùng để lập kế hoạch;
một link trả 404 thì không. **OAuth Apps thì vắng mặt hẳn** chứ không xám — D1
đã quyết định *không xây*, và một mục xám ngụ ý "sắp có" sẽ là lời hứa sai.

**Một portal, không hai.** Form tạo khoá chỉ tồn tại ở đúng một section, và có
test khẳng định điều đó trên **mọi** section. Hai nơi quản lý cùng một khoá là
cách người ta thu hồi nhầm khoá.

**Lối vào phải sửa ở hai chỗ.** Trang catalog (`home.html`) có menu tài khoản
**riêng** (`market-account`), không dùng `_header.html`. Sửa một chỗ là vẫn
không tìm thấy khu API từ trang chủ — đúng cái bẫy mà rủi ro X4 mô tả. Test bắt
được điều này, không phải mắt người.

### Tests

`tests/test_197_developer_api_tab.py` — **23 test**:
- **khả năng tìm thấy**: trang chủ có link tới `/developers`;
- 9 section đều trả 200 và đều dựng chung một khung (nav không bao giờ biến mất);
- nav **giống hệt nhau** trên mọi section (so trong khối `<nav>`, vì phần thân
  có link riêng);
- section chưa xây: có tên, **không** có link, và `/developers/playground` trả
  404 thật;
- `aria-current="page"` đúng **một** phần tử;
- **tenancy**: tạo project/khoá cho tài khoản A rồi đăng nhập tài khoản B —
  không section nào lộ tên project, tên khoá hay `key_id` của A;
- mọi section đòi phiên đăng nhập (302 → `/login`);
- ghi vẫn cần CSRF;
- overview đếm đúng số project/khoá thật;
- tools không lộ vendor/slug app; docs có lệnh `curl` chạy được.

`test_191` sửa 3 chỗ: nội dung **chuyển section**, nên test đi theo (form khoá →
`/developers/keys`, hạn mức → `/usage`, danh sách tool → `/tools`). Không phải
nới lỏng khẳng định — vẫn kiểm đúng những thứ cũ, ở đúng chỗ mới.

Tổng: 38 test portal + IA xanh. i18n: **1439 (mốc 1500) — không tăng**; nhãn
section dùng `N_()` để đánh dấu trích xuất và `_t()` lúc render, vì một `_()` ở
cấp module sẽ **đóng băng ngôn ngữ lúc import**.

### Browser (bắt buộc theo CLAUDE.md mục 5)

Server dùng-một-lần cổng 8123. Đã đi: đăng nhập → `/developers` (Tổng quan hiện
đủ số liệu + 3 bước bắt đầu) → sub-nav sang **Công cụ & model** (2 tool, 4 alias
model, giá **không** hiện theo model, không tên vendor) → về trang chủ → mở menu
tài khoản → **API cho lập trình viên** → quay lại khu API. **0 lỗi console, 0
request hỏng.**

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | Playground | EXT-08 |
| — | Nhật ký request/trace | EXT-09 |
| — | Thông báo + ngân sách | EXT-11 |
| — | Webhook console (xem payload, gửi lại) | EXT-10 |
| — | Xuất/xoá dữ liệu (mục Cài đặt nói thẳng là chưa có) | EXT-19 |

X4 **đóng**.

### Rollback

Hoàn nguyên `server/routes/developer.py`, xoá 9 template `dev_*.html` +
`developers_base.html` (khôi phục `developers.html` từ git), bỏ 2 dòng link
trong `_header.html`/`home.html` và khối CSS `.dev-nav`. Không dữ liệu, không
migration.

### Acceptance Gate

| Yêu cầu của EXT-05 | Kết quả |
|---|---|
| Khu API ≤ 2 cú bấm từ dashboard | ✅ menu tài khoản → API; có test trên trang chủ thật |
| Không có portal trùng lặp | ✅ form tạo khoá tồn tại đúng một nơi, có test trên mọi section |
| Browser/tenant test PASS | ✅ 23 test + kiểm trình duyệt thật, 0 lỗi console |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/06_SCHEMA_DRIVEN_APPS_MODELS_TOOLS_VARIABLE_REFERENCE.txt`


---

## EXT-06 — VARIABLE REFERENCE SINH TỪ HỢP ĐỒNG ✅

### Entry gate

EXT-05 PASS ✅ (`e142772`), cây sạch. Head vẫn `d0e1f2a3b4c5` — **không**
migration, **không** route `/api/v1` mới, **không** phụ thuộc mới.

### Status before → after

| | Before | After |
|---|---|---|
| Mô tả tham số công khai | **0/29** — khách phải đoán `kieu_trend` là gì | **29/29**, máy kiểm |
| Ví dụ giá trị | không có | mọi tham số có `example`, và ví dụ `curl` được **dựng từ chính chúng** |
| Trang tham chiếu | một bảng liệt kê tên tool | trang riêng cho từng tool: mục đích, nhóm, chế độ chạy + luật của chế độ đó, endpoint, scope, cách tính tiền, **bảng biến đầy đủ**, kết quả, model, sự kiện webhook, giới hạn, **bảng lỗi + khi nào thử lại** |
| Tìm kiếm | không | theo tên, mô tả **và tên tham số**, lọc theo nhóm |

### Cách chống drift

Tài liệu biến nằm ở `api_contract["params"]`, **không** ở `params_schema` nội
bộ: schema nội bộ viết cho worker và thường xuyên nhắc tên provider, còn văn bản
này viết cho khách và đi thẳng ra trang tham chiếu.

Registry **từ chối nạp app** khi tài liệu lệch khỏi thứ nó mô tả:
- mô tả một tham số **không tồn tại** → lỗi;
- mô tả một tham số **đang ẩn** → lỗi (khách không gửi được, mô tả là lời hứa
  không giữ);
- `description` rỗng → lỗi;
- khoá lạ ngoài `{description, example}` → lỗi (chặn đường tuồn ghi chú nội bộ
  ra ngoài).

Trang tham chiếu **render từ chính catalog mà API phục vụ**, nên không thể mô tả
một tham số máy chủ không nhận. Có test khẳng định tập tham số trên trang **bằng
đúng** tập trong schema — không thiếu, không thừa.

Cái này bắt lỗi thật ngay khi viết: khối tài liệu dùng chung cho hai tool của
`prompt_ai_ommi` khai `duration_seconds` cho `story.storyboard`, và registry từ
chối nạp app — đúng việc của nó.

### Tests

`tests/test_198_variable_reference.py` — **20 test**: 29/29 tham số có mô tả;
tài liệu không mô tả tham số ẩn/không tồn tại; mô tả không nhắc vendor; 4 kiểu
hợp đồng sai bị từ chối; mô tả + ví dụ tới được schema công khai; **mọi** tool
đang public có trang; tập biến trên trang == schema; trang có endpoint/scope/
mode/sự kiện/giới hạn/bảng lỗi; ví dụ `curl` dựng từ example đã khai; tool
deployment **không** publish thì **không** có trang (trang không được biến thành
danh bạ năng lực nội bộ); tìm kiếm theo tên/tham số; lọc theo nhóm; lọc cũng thu
hẹp danh sách model theo.

### Browser

Server dùng-một-lần cổng 8123: `?q=thumbnail` → mở trang `image.thumbnail` →
9 biến đủ kiểu/bắt buộc/giới hạn/mặc định/mô tả/ví dụ, khối `curl` nhiều dòng
dán chạy được, bảng lỗi 22 dòng, sự kiện webhook, giới hạn. **0 lỗi console.**

### Phát hiện, chưa sửa (có chủ đích)

Ba tham số công khai mang tên tiếng Việt — `phong_cach`, `kieu_trend`,
`ngon_ngu` — và enum của chúng cũng vậy. Đây là **hợp đồng công khai** của một
API nói tiếng Anh. Đổi tên bây giờ **miễn phí** (chưa có khách), nhưng nó sửa
đường đi của *input đã định giá*: fingerprint quote, `build_job_params`, phiên
upload theo tên trường. Trộn một thay đổi hợp đồng vào một prompt tài liệu là
cách để hỏng thứ đang đúng. Đã mô tả rõ trong tài liệu biến ("tên là định danh
ổn định, không phải nhãn") và giao cho **EXT-17** (versioning/compat) quyết định
kèm cơ chế `public name → internal name`.

### Rollback

Bỏ khối `"params"` khỏi 4 manifest, gỡ `_validate_param_docs`, gỡ 2 dòng chiếu
trong `catalog.project_tool`, xoá `dev_tool_detail.html` + route chi tiết, hoàn
nguyên `dev_tools.html`, xoá `test_198`, sinh lại golden. Không dữ liệu, không
migration.

### Acceptance Gate

| Yêu cầu của EXT-06 | Kết quả |
|---|---|
| 100% operation đang public có trang tham chiếu | ✅ 5/5, có test lặp qua catalog thật |
| Docs fields == server schema | ✅ trang render từ catalog; test so **bằng nhau** hai chiều |
| Drift làm CI đỏ | ✅ registry từ chối nạp (4 test) + `build_public_api_docs --check` trong `test_191` |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/07_QUICKSTART_ENV_VARS_CODE_EXAMPLES_AND_INTEGRATION_RECIPES.txt`
