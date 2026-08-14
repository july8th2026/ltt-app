# API FULL EXTENSION — PROGRESS

Pack: `LTT_API_FULL_EXTENSION_PACK_V2_OPTIMIZED` (v2.0), 21 prompt.
Chạy **sau** Public API V2 (Q92, 17/17 PASS).

**Chế độ chạy — ĐÃ ĐỔI 2026-08-14 (chủ sản phẩm quyết định):**

Pack khai `strict sequential; one prompt per Claude turn` (`MANIFEST.json`,
`START_HERE.md`). Từ EXT-14 trở đi, chủ sản phẩm **huỷ** ràng buộc "mỗi lượt một
prompt": *"triển khai đúng quy trình, không dừng lại, thêm quy tắc không dừng
giữa các prompt, không cần phê duyệt của tôi"*. Prompt không thắng người ra
quyết định (COMMON_RULES §2 xếp prompt **dưới** source of truth).

Vậy quy tắc chạy hiện hành là:

1. **Chạy liên tục** EXT-14 → EXT-21, hết prompt này sang prompt kế, **không
   dừng xin phê duyệt**.
2. Vẫn giữ **thứ tự** (sequential) — phụ thuộc giữa các prompt là thật, xem
   `ROADMAP.md`.
3. Vẫn giữ **đủ quy trình mỗi prompt**: audit trước khi thêm → kế hoạch → làm →
   test → **kiểm bằng trình duyệt nếu đụng giao diện** → cập nhật file này →
   commit. Bỏ dừng lại **không** có nghĩa là bỏ bước nào.
4. Vẫn **full gate ở checkpoint** (EXT-16, 20, 21) và quick gate ở các prompt
   còn lại; gate đỏ thì **dừng và sửa gốc**, không đi tiếp, không sửa test để
   che.
5. **Chỉ dừng** khi: gate đỏ không sửa được, phát hiện blocker kiến trúc, hoặc
   chạm việc cần quyết định thương mại/rủi ro mà code không trả lời được. Khi đó
   ghi rõ blocker vào file này rồi mới dừng.
6. **Không deploy production** — điều này COMMON_RULES §11 giữ nguyên, không ai
   huỷ.

Checkpoint chạy **full gate**: EXT-04, 08, 12, 16, 20, 21.

| # | Prompt | Trạng thái | Ngày |
|---|---|---|---|
| 01 | V2 reconciliation, master gap matrix, dependency graph | **PASS** | 2026-08-13 |
| 02 | Protocol / execution modes / error-retry standards | **PASS** | 2026-08-13 |
| 03 | Models / capabilities / tool catalog / schema chain | **PASS** | 2026-08-13 |
| 04 | Projects / service accounts / delegated auth decision | **PASS** | 2026-08-13 |
| 05 | Developer API tab / information architecture | **PASS** | 2026-08-13 |
| 06 | Schema-driven apps/models/tools variable reference | **PASS** | 2026-08-13 |
| 07 | Quickstart / env vars / examples / recipes | **PASS** | 2026-08-13 |
| 08 | Playground / request builder / job inspector | **PASS** | 2026-08-13 |
| 09 | Request logs / trace / job timeline | **PASS** | 2026-08-14 |
| 10 | Webhook console / event catalog / resend | **PASS** | 2026-08-14 |
| 11 | Usage / budgets / credit alerts / notifications | **PASS** | 2026-08-14 |
| 12 | Sandbox / test mode / live isolation | **PASS** | 2026-08-14 |
| 13 | API admin console core | **PASS** | 2026-08-14 |
| 14 | Admin policy / tiers / quota / kill switch | **PASS** | 2026-08-14 |
| 15 | Pricing catalog / versioned credits / margin | **PASS** | 2026-08-15 |
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


---

## EXT-07 — QUICKSTART, BIẾN MÔI TRƯỜNG, VÍ DỤ, RECIPE ✅

### Entry gate

EXT-06 PASS ✅ (`36af52f`), cây sạch. Head vẫn `d0e1f2a3b4c5` — **không**
migration, **không** route `/api/v1` mới, **không** phụ thuộc mới.

### Status before → after

| | Before | After |
|---|---|---|
| Biến môi trường | `LTT_API_KEY` xuất hiện rải rác trong guide; base URL viết cứng `https://app.lttstudios.com` | **3 biến chuẩn hoá một chỗ** (`platform_core/public_api/examples.py`), dùng lại ở guide + portal + mọi snippet |
| Ví dụ mã | 1 khối cURL viết tay trong guide | cURL (báo giá + chạy), Python, TypeScript, PowerShell, HTTP thô — **sinh từ hợp đồng**, cho **từng** tool |
| Shell | chỉ bash | bash/zsh, PowerShell, cmd.exe |
| Không-viết-mã | không có | n8n, Make, "bất kỳ HTTP client nào" |
| Chống lệch | không có | ví dụ được **kiểm bằng chính validator của route tính tiền** |

### Cách chống lệch ví dụ

`examples.example_input(tool)` dựng payload từ `params[].example` đã khai
(EXT-06), rồi mọi snippet dựng từ payload đó. **Không có bản sao thứ hai** để
quên cập nhật.

Kiểm bằng ba tầng, tăng dần độ thật:
1. bộ kiểm schema nhỏ trong test (kiểu, enum, min/max, maxLength, trường lạ);
2. **`validate_public_input`** — đúng hàm mà `POST /jobs` chạy, nên nếu khách
   dán ví dụ mà bị 400 thì test đỏ trước;
3. mọi đường dẫn xuất hiện trong snippet phải nằm trong **inventory route** —
   một ví dụ trỏ tới endpoint không tồn tại không lọt được.

Tham số bắt buộc **không có** ví dụ thì nhận placeholder có kiểu (`<string>`),
không phải giá trị bịa: một giá trị bịa đọc như lời khuyên, `<string>` đọc như
chỉ dẫn.

### Nghiệm thu "fresh integration completes E2E"

`test_a_developer_who_follows_the_quickstart_gets_a_result` đi **đúng** bảy bước
trang hướng dẫn nói: đăng nhập portal → tạo khoá (lấy chuỗi bí mật từ chính
phản hồi) → `GET /tools` → `POST /quotes` → `POST /jobs` kèm `Idempotency-Key`
→ chạy worker thật → `GET /jobs/{id}` = `succeeded` → `GET /artifacts/{id}`
trả về đường tải. Bất kỳ bước nào của con đường được ghi trong tài liệu hỏng thì
test này đỏ.

### Tests

`tests/test_199_quickstart_examples.py` — **11 test**: payload hợp lệ theo
schema; payload qua được validator thật; snippet chỉ gọi endpoint có thật;
**không snippet nào chứa thứ giống một khoá** và mọi snippet đều đọc khoá từ
biến môi trường; snippet tính tiền **đều có** `Idempotency-Key` còn snippet báo
giá thì không; tên biến môi trường chốt ở một chỗ; placeholder cho tham số bắt
buộc thiếu ví dụ; trang có đủ đường đi + biến + recipe; quickstart cách khu API
một cú bấm; và E2E ở trên.

Guide có thêm khối **sinh tự động** cho biến môi trường + lời gọi đầu tiên,
`--check` chặn lệch (đã có trong `test_191`).

### Browser

Cổng 8123: `/developers/quickstart` hiện 7 bước, bảng 3 biến, 3 shell, 6 snippet
cho `image.generate`, đổi tool bằng link, 3 recipe không-viết-mã, và khối "thử
lại cho đúng". **0 lỗi console.**

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | Recipe OAuth ("Connect LTT account") | D1 hoãn OAuth → không áp dụng |
| — | Snippet cho STREAM/BATCH | chưa mode nào dùng (D5) |
| — | Ví dụ upload nhiều bước dạng chạy-được | EXT-08 (playground) sẽ làm được trực quan hơn |

### Acceptance Gate

| Yêu cầu của EXT-07 | Kết quả |
|---|---|
| Fresh integration completes test E2E | ✅ 7 bước, worker thật, artifact tải được |
| Không hardcode secret | ✅ test quét mọi snippet; tất cả đọc từ env |
| Không lệch ví dụ | ✅ sinh từ hợp đồng + kiểm bằng validator của route tính tiền + `--check` |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/08_API_PLAYGROUND_REQUEST_BUILDER_COST_STREAM_BATCH_JOB_INSPECTOR.txt`
— **checkpoint full gate**.


---

## EXT-08 — PLAYGROUND ✅

**Checkpoint full gate** theo `MANIFEST.json`.

### Entry gate

EXT-07 PASS ✅ (`7b6d67a`), cây sạch. Head vẫn `d0e1f2a3b4c5` — **không**
migration, **không** route `/api/v1` mới, **không** phụ thuộc mới.

### Quyết định thiết kế đáng nói nhất

Trang gọi `/api/v1` **từ trình duyệt bằng khóa do khách dán vào**, chứ không đi
qua một endpoint portal mượn phiên đăng nhập.

Một proxy như vậy sẽ phải dựng lại danh tính người gọi ở phía máy chủ, và trở
thành **con đường thứ hai** tới đường tính tiền — đúng thứ COMMON_RULES cấm, và
là nơi một lỗi chính sách làm mất tiền thật. Dán khóa nghĩa là playground **chính
là** API: cùng xác thực, cùng scope, cùng hạn mức, cùng sổ credit, cùng
idempotency. Chạy được ở đây thì chạy được từ máy chủ khách; bị từ chối ở đây thì
cũng bị từ chối ở đó.

Khóa nằm trong biến của tab: **không** localStorage, **không** cookie, không gửi
đi đâu ngoài header `Authorization` tới chính origin này. Có test quét mã nguồn
JS (sau khi bỏ comment, để bộ quét không vấp vào chính tài liệu của nó).

**Không có chế độ chạy miễn phí.** Trang nói thẳng "lời gọi ở đây tiêu credit
thật" — nếu có chế độ miễn phí thì nó đã không còn là cùng một đường đi.

### Form sinh từ hợp đồng

Toàn bộ form dựng từ JSON Schema mà `/api/v1/tools` phục vụ (nhúng nguyên văn
vào trang, escape `<` để một schema chứa `</script>` không thoát ra thành
markup). Enum thành `<select>`, `integer` thành number có min/max, tham số media
thành `<input type=file>` đi **đúng ba bước upload thật** (vé → bytes →
confirm). Có `JSON thô` cho người muốn tự gõ.

`Idempotency-Key` sinh tự động **một lần cho mỗi lời gọi logic** và **bị vứt đi
khi input đổi** — đổi input là lời gọi khác, phát lại câu trả lời cũ sẽ là sai.

Bảng trace chỉ hiện header khách cần hành động: `X-Correlation-ID`,
`X-LTT-API-Version`, `Retry-After`, `Idempotency-Replayed`, `Location`. Có test
chốt đúng tập đó — `Authorization` không bao giờ được vọng lại lên trang.

### Chế độ chạy khác

`SYNC` chỉ dành cho đọc; `STREAM`/`BATCH` đã đặc tả nhưng **chưa operation nào
dùng** (D5), nên trang nói rõ là chưa có gì để thử thay vì dựng một tab rỗng.

### Tests

`tests/test_200_playground.py` — **15 test**. Đáng kể:
- **không route portal nào** chứa `run`/`execute`/`quote` — không có con đường
  thứ hai tới đường tính tiền;
- mọi `fetch` trong JS chỉ trỏ `/api/v1`, và mọi path phải có trong inventory;
- trang **không chứa** khóa vừa tạo, không có `localStorage`/`cookie`, ô khóa là
  `type=password`;
- catalog nhúng **bằng đúng** `to_public_dict()` của catalog thật;
- deployment chỉ mở `image.thumbnail` thì trang **không** hiện `image.generate`;
- script có `?v=` cache-bust;
- **parity**: chạy đúng những gì trang làm bằng request thường → bấm Run hai lần
  cùng input trả **cùng job id** + `Idempotency-Replayed: true`, tức không tính
  tiền hai lần — chính hành vi trang dựa vào.

### Browser E2E (bắt buộc)

Server dùng-một-lần cổng 8123, provider **stub**, worker chạy trong tiến trình.
Luồng thật trong trình duyệt: tạo khóa ở portal → mở Playground → chọn
`image.thumbnail` → dán khóa → **Kiểm & báo giá** = `5 credit` → **Chạy thật** →
job `queued` → poll → `succeeded`, `credit: held 5 / charged 5`, và một dòng
`artifact <id>`. **0 lỗi console.**

Trình duyệt cũng bắt được một lỗi của bản dựng đầu: job hỏng vì handler tra
credential provider **trước** khi gọi, nên chỉ stub hàm gọi là chưa đủ — đúng
loại chi tiết mà test đơn vị (đã stub sẵn env) không thấy.

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | Tab STREAM/BATCH | khi có operation đầu tiên (D5) |
| — | Lưu lịch sử lời gọi trong playground | EXT-09 (request logs) làm đúng chỗ hơn |

### Rollback

Xoá `dev_playground.html`, `server/static/dev_playground.js`, khối CSS `.pg-*`,
route `/developers/playground`, trả mục nav về `None`, xoá `test_200`. Không dữ
liệu, không migration.

### Full gate — checkpoint

Lần 1: **FAIL (1/10)**. pytest 3.157 pass, đúng **một** test đỏ:
`test_197::test_unbuilt_sections_are_named_but_not_linked`. Nó đỏ vì EXT-08
**đã xây** Playground, trong khi test viết ở EXT-05 **liệt kê cứng** những
section chưa xây và khẳng định `/developers/playground` phải trả 404 — một thay
đổi đúng làm suite đỏ. Lỗi của test, không phải của mã.

Sửa tận gốc: test đọc danh sách từ chính khai báo `SECTIONS` (`href is None`),
kiểm mỗi section chưa xây đều có tên, **không** có link, và route trả 404 thật.
Thêm một khẳng định: nếu mọi section đều đã xây thì test tự báo "xoá tôi đi thay
vì nói dối", vì lúc đó nó không còn kiểm điều gì.

Lần 2, trên cây mã cuối: **`RESULT: PASS` 10/10**, pytest 2.807,9 s.

### Acceptance Gate

| Yêu cầu của EXT-08 | Kết quả |
|---|---|
| Playground semantics == external API | ✅ trang **là** API; test parity chứng minh replay/không tính tiền hai lần |
| No raw key recovery | ✅ máy chủ không đọc lại được khóa; trang không chứa/không lưu khóa nào |
| No credit bypass | ✅ không route portal nào chạy tool; mọi lời gọi qua quote + hold + ledger |
| Browser E2E | ✅ chạy trọn vòng tới artifact, 0 lỗi console |
| Full gate tại checkpoint | ✅ 10/10 |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/09_USER_REQUEST_LOGS_TRACE_DEBUG_AND_JOB_TIMELINE.txt`


---

## EXT-09 — NHẬT KÝ REQUEST, TRACE, GỠ LỖI ✅

### Entry gate

EXT-08 PASS ✅ (`0df0d95`, full gate 10/10), cây sạch. Migration mới:
**`e1f2a3b4c5d6`** (head).

### Vì sao phải có bảng, dù đã có dòng log

`ltt.public_api.access` ghi đủ mọi request — nhưng chỉ **operator** đọc được.
Khách không grep được đĩa của chúng ta, và những lời gọi họ cần hiểu nhất
(401, 403, 429) **không bao giờ tạo job**, tức không có gì khác lưu lại. Suy ra
từ `jobs` + `credit` + `webhook` chỉ phủ được phần tiêu tiền.

### Chi phí đo được, và quy tắc rút ra từ nó

Bản đầu ghi **một dòng cho mọi request**. Đo bằng `tools/public_api_load_test.py`:

| | Trước | Ghi mọi request | Quy tắc cuối |
|---|---|---|---|
| reads rps | 177 | **42,6** | **174,7** |
| p50 | 29 ms | 107 ms | 29 ms |
| p95 | 47 ms | 333 ms | 48 ms |

Mất 4× thông lượng cho một bảng gỡ lỗi là cái giá sai. Quy tắc cuối:
**ghi mọi thất bại, và mọi lời gọi không phải là đọc.** Thứ bị bỏ ra — một `GET`
thành công — chính là phần áp đảo về số lượng (poll + khám phá catalog) và cũng
là phần khách **đã** nhìn thấy: job tự kể chuyện của nó. Log file của operator
vẫn có đủ mọi request.

Con số này nằm trong docstring của `_worth_recording`, không phải chỉ trong
handoff — người sau sửa hàm đó sẽ đọc được lý do trước khi đổi.

### Ghi sau khi trả lời, không ghi bên cạnh

Bản đầu mở **phiên CSDL thứ hai** ngay trong middleware → `database is locked`
trên SQLite, và trên PostgreSQL sẽ âm thầm gấp đôi số kết nối mỗi request. Đổi
sang `BackgroundTask` của Starlette: hàng được ghi **sau khi phản hồi đã ra**,
lúc phiên của request chắc chắn đã đóng. Ghi hỏng thì log cảnh báo rồi bỏ qua —
một request đã thành công không được báo là hỏng chỉ vì dòng sổ sách của nó
không ghi được.

### Không lưu gì

Không cột body, không cột `detail`, không credential. Chỉ bộ xương: ai, gọi gì,
kết thúc ra sao, mất bao lâu, tốn bao nhiêu, job nào. Có test đọc **danh sách
cột** và cấm `body/payload/detail/input/headers/token`, và một test nữa gửi một
cụm từ đặc trưng của khách rồi khẳng định nó không xuất hiện trong bất kỳ cột
nào.

### Hai lỗi thật mà bộ test tìm ra

1. **Route bị ghi thiếu tiền tố.** Sub-app biết route của nó là `/me`, còn khách
   gõ `/api/v1/me`. Dòng log và bảng đều ghi dạng ngắn → mọi việc đối chiếu với
   API mà khách thấy trở thành câu đố. Sửa ở `_route_of`, nên **cả dòng log của
   operator cũng đúng lên**.
2. **429 không quy được cho ai.** Giới hạn nhịp chạy **trước** khi principal
   được gắn vào `request.state`, nên đúng cái thất bại khách hay đi tìm nhất lại
   là cái duy nhất không gắn được chủ. Đổi thứ tự: dựng principal → gắn state →
   rồi mới áp giới hạn.

### Trace, không thêm định danh mới

`request_id` được nhét vào `api_meta` của job (chỗ đã có `tool`/`key_id`/
`idempotency_key`), nên đường đi **request → job → sự kiện worker → dòng credit
→ artifact → webhook** nối bằng khoá đã có. Trang chi tiết đọc lại `JobEvent`
(chỉ dòng `visibility=customer`), `CreditEntry`, `WebhookDelivery`,
`media.artifacts_of` — **không** lưu bản sao nào.

### Retention ngay từ đầu

30 ngày, `request_log.purge_expired`, worker gọi cùng nhịp với dọn job event.
Không lặp lại bài học `webhook_deliveries` (tạo dữ liệu, quên chính sách dọn,
audit mới phát hiện).

### Tests

`tests/test_201_request_logs.py` — **18 test**: quy tắc ghi (đọc thành công thì
không, quote/job thì có, đọc **hỏng** thì có); 403/409/422/429 đều có mã;
request ẩn danh **không** ghi vào sổ của ai; job hỏng truy được từ request (kèm
drain retry + backoff); job xong nối được events/credit/artifact; `request_id`
có trong job meta; bảng không có cột payload; nội dung khách không lọt vào hàng;
cách ly tenant ở cả danh sách lẫn trang chi tiết (404 cho request của người
khác); trang lọc theo `4xx`; trang chi tiết in **lời khuyên lấy từ error
registry**, không phải bản sao thứ hai; purge xoá đúng cái cũ; và một test đọc
`job_runner.py` để bảo đảm retention **được gọi** chứ không chỉ tồn tại.

Ba test cũ đổi kỳ vọng: `test_192` (route giờ có tiền tố — chính là lỗi #1),
`test_193` (đóng băng số migration 2 → 3), và `test_197` (đã sửa ở EXT-08).

### Browser

Cổng 8123: tạo khoá → gọi một 404, một quote, một job thật → `/developers/logs`
hiện **3 dòng** đúng thứ tự với route đầy đủ, mã lỗi, độ trễ, credit `-5` → mở
chi tiết job: timeline `submitted → started → progress → completed`, sổ credit
`hold -5` rồi `settle 0`, và artifact. Lọc `?status=4xx` còn **đúng 1 dòng**.
Lỗi console duy nhất là 404 do chính tôi gọi.

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | `GET` thành công không có trong sổ của khách | có chủ đích; log operator vẫn đủ |
| — | Phân loại nguyên nhân job hỏng (`provider_timeout`…) | EXT-16, cần worker gắn nhãn |
| — | Xuất nhật ký (CSV/API) | EXT-19 (privacy/export) |

### Rollback

`alembic downgrade d0e1f2a3b4c5`, gỡ `request_log.py`, bỏ `_schedule_log` khỏi
guard, bỏ `request_id` khỏi job meta, xoá hai template + route + `test_201`.
Không có dữ liệu nào khác bị chạm.

### Acceptance Gate

| Yêu cầu của EXT-09 | Kết quả |
|---|---|
| Debug được 401/403/409/422/429/5xx/job fail | ✅ có test cho từng lớp (401 = ẩn danh, cố ý không gắn chủ) |
| Tenant isolation | ✅ lọc theo chủ **trong truy vấn**; request của người khác trả 404 |
| Không lộ secret/PII | ✅ không cột payload; test quét cột và quét nội dung khách |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/10_WEBHOOK_CONSOLE_EVENT_CATALOG_RESEND_REPLAY_SAFETY.txt`


---

## EXT-10 — WEBHOOK CONSOLE, DANH MỤC SỰ KIỆN, GỬI LẠI ✅

### Entry gate

EXT-09 PASS ✅ (`b5344d2`), cây sạch. Migration mới: **`f2a3b4c5d6e7`** (head).

### Bốn thao tác, mỗi thao tác một luật

**Gửi lại không chạy lại gì.** Dùng **đúng** dòng cũ: cùng `event_id`, cùng
payload, `attempts` về 0, đến hạn ngay. Không chạm job, không chạm sổ credit —
và **không thể** chạm, vì module này không đọc/ghi cả hai. Quan trọng vì hai lẽ:
một cuộc hỗ trợ kết thúc bằng "gửi lại đi" không được là đường tính tiền lần
hai; và khoá khử trùng của bên nhận **chính là** `event_id`, nên một lần gửi lại
mang id mới sẽ bị họ xử lý hai lần.

**Sự kiện thử tự nhận là thử.** Loại riêng `webhook.test`, không `job_id`,
payload nói thẳng "không job nào chạy, không credit nào chuyển" — nhưng đi qua
**đúng** outbox, worker và chữ ký thật, nếu không nó chẳng chứng minh được cái
dây nối mà nó sinh ra để chứng minh.

**Xoay secret có cửa an hạn 24 giờ.** Xoay có hiệu lực tức thì sẽ làm hỏng mọi
lần giao đang bay ở một receiver đã đổi — đúng lúc khách đang nhìn. Trong cửa sổ
đó, mỗi sự kiện được **ký bằng cả hai** secret, header chứa nhiều chữ ký cách
nhau bằng dấu phẩy, và `verify()` chấp nhận nếu **khớp một**.

**Tắt chứ không xoá.** Lịch sử giao là bằng chứng về việc điểm nhận đó đã được
báo những gì; xoá subscription sẽ làm mồ côi chỗ bằng chứng ấy.

### Một lỗ hổng tôi tự tạo ra và trình duyệt bắt được

Bản đầu trả secret mới qua **query string** (`?secret=…`). Query string đi vào
lịch sử trình duyệt, vào header `Referer` của cú bấm kế tiếp, và vào mọi log
truy cập trên đường. Đã đổi sang một ô **dùng một lần trong session**: trang kế
tiếp `pop` ra, hiện đúng một lần, tải lại là mất. Có test khẳng định `secret=`
**không** xuất hiện trong `Location` và giá trị biến mất ở lần tải sau.

### Giới hạn có lý do

20 lần gửi lại/giờ mỗi tài khoản: gửi lại là một request **chúng ta** phát đi
tới máy chủ của người khác — một nút bấm không giới hạn là một bộ khuếch đại
hướng vào bất kỳ URL nào khách cấu hình.

### Tests

`tests/test_202_webhook_console.py` — **19 test**: gửi lại giữ nguyên id/payload
và **không** đổi job hay sổ credit (so snapshot trước/sau); hồi sinh được lần
giao `dead`; bị giới hạn nhịp; không gửi lại được của người khác; sự kiện thử
không tạo job/credit và đi đúng đường giao thật; xoay secret ký bằng **cả hai**
và secret cũ hết hiệu lực sau cửa sổ; tắt thì giữ lịch sử và không nhận sự kiện
mới; 4 URL nội bộ/không-https bị từ chối (hồi quy SSRF); mọi thao tác ghi đều
cần CSRF; trang không bao giờ hiện secret đã lưu; và trang có đủ danh mục sự
kiện + hướng dẫn kiểm chữ ký + ghi rõ **thứ tự không bảo đảm, giao trùng là có
thể**.

### Browser

Cổng 8123, **không** chạy vòng giao webhook nên không có request nào đi ra
ngoài: đăng ký điểm nhận → console hiện `Đang chờ giao: 1` sau khi bấm **Gửi
thử**, dòng `webhook.test` với `pending 0` → bấm **Đổi secret** → secret mới
hiện đúng một lần kèm dòng nhắc về cửa an hạn.

### Risks / deferred

| # | Việc | Chủ sở hữu |
|---|---|---|
| — | Sự kiện cho STREAM/BATCH | chưa mode nào dùng (D5) |
| — | Đăng ký điểm nhận **từ portal** (hiện vẫn qua API) | secret chỉ hiện một lần trong phản hồi API là đủ an toàn; thêm form là thêm chỗ lộ |
| — | Xuất lịch sử giao | EXT-19 |

### Rollback

`alembic downgrade e1f2a3b4c5d6`, gỡ `webhook_console.py`, hoàn nguyên
`delivery.build_headers` và `webhooks.verify`, bỏ 5 route console và bản
`dev_webhooks.html` cũ, xoá `test_202`.

### Acceptance Gate

| Yêu cầu của EXT-10 | Kết quả |
|---|---|
| Gửi lại không mutate job/credit | ✅ snapshot job + toàn bộ ledger giống hệt trước/sau |
| Không hồi quy SSRF | ✅ 4 URL bị chặn + kiểm lại đích ngay trước khi gửi |
| Lịch sử giao an toàn theo tenant | ✅ lọc theo chủ trong truy vấn; gửi lại của người khác không có hiệu lực |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/11_USAGE_BUDGETS_CREDIT_ALERTS_AND_DEVELOPER_NOTIFICATIONS.txt`


---

## EXT-11 — NGÂN SÁCH, CẢNH BÁO, THÔNG BÁO ✅

### Entry gate

EXT-10 PASS ✅ (`cb194c6`), cây sạch. Migration mới: **`a3b4c5d6e7f8`** (head).
Đây là nơi **D3 được thi hành**.

### D3: sửa một lỗi phạm vi có thật

`limits.credit_spent_since()` trước đây cộng **mọi** chi tiêu credit của tài
khoản. Hệ quả: khách dùng nhiều trên giao diện web sẽ làm cạn hạn mức ngày của
**chính API của họ** — ngược hẳn mục đích, vì trần đó sinh ra để giới hạn bán
kính thiệt hại của một **khoá API bị rò**. Giờ chỉ đếm job do API tạo (`_api`
trong `job.params`), và job có mang thêm `project_id` để đo được ngân sách theo
project mà không phải join ngược qua khoá — thứ sẽ vỡ ngay khi khoá bị xoay.

Có test dựng **cả hai** loại job (một qua API, một theo đúng đường UI) rồi khẳng
định chỉ cái đầu được tính.

### Ba ý giữ riêng, vì trộn hai cái bất kỳ là lúc tính năng ngân sách nói dối

**Sổ credit không bị chạm.** Ngân sách **quan sát**; nó không ghi, không sửa,
không giấu một dòng nào. Có test chụp toàn bộ sổ trước/sau khi tạo ngân sách,
tính trạng thái và quét cảnh báo — giống hệt.

**Mềm và cứng là hai lời hứa khác nhau.** Mềm chỉ cảnh báo (test: vượt 200% vẫn
chạy được); cứng từ chối lời gọi kế tiếp. Người đã xin được **báo** ở 80% không
được phát hiện ra rằng "báo" cũng có nghĩa là "chặn".

**Trần của khách không bao giờ nới được trần của máy chủ.** Lấy **cái chặt hơn**
trong hai, và lời từ chối **nói rõ** cái nào đã áp (`source: budget|operator`) —
không thì mọi cuộc hỗ trợ về một cái 429 đều bắt đầu bằng một cuộc điều tra.

### Cảnh báo không thành tiếng ồn

Mỗi cảnh báo có **subject** (một khoá cụ thể, một ngưỡng của một ngân sách cụ
thể) và một **cooldown**. Khử trùng nằm ở tầng lưu, không ở nơi phát — nên bộ
quét chạy 15 phút/lần và phát hiện lại cùng một điều kiện mỗi lượt là vô hại
**theo thiết kế**. Vượt 80% rồi vượt 100% là **hai** tin khác nhau, nên chúng là
hai subject.

Chỉ **tiền và credential** đáng gửi email (số dư thấp, vượt ngân sách, vượt hạn
mức, khoá sắp hết hạn, project bị đình chỉ). Một ngưỡng do chính khách đặt để
được *biết* thì chỉ hiện trên trang — hộp thư bị làm phiền là hộp thư bị lọc.
Email hỏng **không** làm mất cảnh báo: dòng đã lưu, trang vẫn hiện.

### Kênh: chỉ những gì nền tảng đã có

Một dòng trong CSDL cho trang **Thông báo** (mục cuối cùng của khu API, giờ đã
xây) + email qua `platform_core/mailer.py`. Không SMS, không push, không dịch vụ
thứ ba phải nuôi — COMMON_RULES §6.

### Tests

`tests/test_203_budgets_alerts.py` — **24 test**: D3 (web không ăn hạn mức API);
hard cap chặn đúng lời gọi vượt và nêu `source`; soft không bao giờ chặn; lấy
cái chặt hơn giữa operator/budget theo cả hai chiều; ngân sách **không** đổi sổ
credit; **replay idempotent không bị tính hai lần**; ngân sách theo project chỉ
đếm project đó; ngưỡng chỉ báo một lần trong cooldown và mỗi ngưỡng là một tin;
số dư thấp báo lại sau khi hết cooldown; khoá sắp hết hạn; webhook chết; email
chỉ cho loại đáng làm phiền; email hỏng không mất cảnh báo; ngân sách vô nghĩa
bị từ chối (4 giá trị); ngưỡng bị chặn biên; cách ly tenant; tạo/xoá từ trang;
lọc usage theo tool/khoá/trạng thái; và worker **có gọi** bộ quét.

`test_197` có một thay đổi đáng nói: test "section chưa xây" **tự nghỉ hưu**
đúng như thông điệp nó tự viết ở EXT-08 — mọi section giờ đã xây, nên nó được
thay bằng một test giữ đúng tính chất còn lại: *navigation không hứa thứ nó
không phục vụ được*.

### Rollback

`alembic downgrade f2a3b4c5d6e7`, gỡ `budgets.py`/`notifications.py`/
`alerting.py`, bỏ `enforce_budget` khỏi route job, hoàn nguyên
`credit_spent_since` (lưu ý: hoàn nguyên là **mang lỗi D3 trở lại**), bỏ hai
route + hai template, xoá `test_203`.

### Acceptance Gate

| Yêu cầu của EXT-11 | Kết quả |
|---|---|
| Budget alert không thay ledger | ✅ snapshot toàn bộ sổ trước/sau, giống hệt |
| Hard cap tất định khi bật | ✅ chặn đúng lời gọi làm vượt; nêu limit/spent/source |
| Notification dedupe PASS | ✅ cùng subject không báo lại trong cooldown; mỗi ngưỡng là một subject |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/12_SANDBOX_TEST_MODE_MOCK_EXECUTION_AND_LIVE_ISOLATION.txt`
— **checkpoint full gate**, và là nơi thi hành D4.

---

## EXT-12 — SANDBOX / TEST MODE ✅ (checkpoint full gate)

### Entry gate

EXT-11 PASS ✅ (`16ce533`), cây sạch. Migration mới: **`b4c5d6e7f8a9`** (head),
thêm đúng **một cột**: `developer_api_keys.mode`.

### Thi hành D4: thay đúng MỘT mắt xích

Sandbox này không phải một bản sao của API. Nó **là** API, với handler bị thay:

```
auth → scope → catalog → validate → quote → Idempotency-Key → job row →
worker lease → [HANDLER ← chỗ duy nhất bị thay] → settlement → artifact →
event → webhook + chữ ký
```

Chỗ thay nằm ở `platform_core/job_runner._ket_qua_sandbox()`: job có
`params["_api"]["mode"] == "test"` thì worker dựng kết quả từ **`output_schema`
đã công bố của chính tool đó** thay vì gọi handler. Sandbox mà bỏ qua bất kỳ
bước nào ở trên sẽ cho một tích hợp xanh ở đây rồi vỡ ở production — tệ hơn là
không có sandbox (COMMON_RULES §3: không dựng engine song song).

### Hai luật cứng, và cách chúng được thi hành

**Khoá test không tiêu được credit — không phải "tiêu ít".** `invocation.submit`
rẽ sang `jobs.submit` (không `submit_with_credit`), nên **không có `giu_cho`**,
không có dòng sổ, không có gì để quyết toán. Đây là tính chất khiến một khoá
test bị rò trở nên vô hại — thứ khoá live không bao giờ có được.

Hệ quả có chủ ý: **trần chi tiêu không áp lên test**. Trần ngày (operator) và
ngân sách (EXT-11) đo *chi tiêu*; áp chúng lên một lời gọi không thể chi là đo
một việc không thể xảy ra. Cũng **không** đòi số dư: người mà sandbox sinh ra để
phục vụ chính là người **chưa** nạp tiền. Giới hạn **nhịp** và **số job song
song** thì vẫn áp — lời gọi test vẫn dùng máy thật.

**Live và test không trộn.** Cùng bảng, cùng worker, một cờ:
- `sandbox.ensure_same_mode()` trên `GET /jobs/{id}`, `POST /jobs/{id}/cancel`
  và `/artifacts/*` → **404 y hệt** tài nguyên của người khác, không tạo oracle;
- `sandbox.restrict_to_mode()` lọc **trong SQL** ở `GET /jobs`. Lọc sau khi lấy
  trang sẽ cho trang ngắn và cờ `has_more` sai — khách sẽ phân trang qua lỗ hổng;
- job **không có** `mode` (tạo từ giao diện web, hoặc có trước EXT-12) là
  **live**. Khoá test không thừa hưởng lịch sử của tài khoản.

### Tiền tố, không phải một cột phải tra

`ltt_sk` = live, `ltt_tk` = test. Một bí mật lọt vào log hay ảnh chụp màn hình
phải phân loại được **bằng mắt**; "khoá này có tiêu tiền được không" không nên
cần một truy vấn. Không dùng hậu tố trong token vì định dạng là
`<prefix>_<key_id>_<secret>` và secret là base64 url-safe có chứa `_`.

Xoay khoá **giữ nguyên** môi trường: một khoá lặng lẽ thành live khi xoay sẽ
chĩa một tích hợp đã xong vào tiền thật; chiều ngược lại chĩa production vào
mock và trông y như sự cố.

### Kiểm bằng trình duyệt bắt được thứ test không thấy

Chạy thật trên uvicorn (cổng 8123, SQLite tạm, provider bị stub — **không** đụng
8100/8000): gọi `count=2`, báo giá **10 credit**, nhưng sandbox trả **1** ảnh.
Đúng *hình dạng*, sai *số lượng* — đủ để vỡ một tích hợp đọc phần tử thứ hai.

Nền tảng không suy ra được điều này; chỉ app biết `count` nhân `image_keys`. Nên
nó vào **hợp đồng app**: `api_contract["output_counts"] = {"image_keys": "count"}`,
có validate hai phía trong `registry._validate_output_counts` (khai một đầu ra
không phải danh sách, hoặc một tham số không tồn tại → `RegistryError`). Trường
này **nội bộ**, không vào `to_public_dict`, nên **không contract hash nào đổi**.
Trần `MAX_SANDBOX_FILES = 8`.

Kiểm trình duyệt cũng bắt một lỗi cũ hơn: sau khi có project mặc định, ô chọn
project hiện **hai** dòng "Default" (một placeholder rỗng + một project thật).
Đã sửa: placeholder chỉ hiện khi chưa có project nào.

### Cổng lập trình viên

Tab **Khoá** có nhóm **Môi trường** (Live mặc định / Test), cột **Môi trường**
trong bảng, chip `Test` ở trang **Sử dụng** (dòng test luôn là 0 credit — nêu
tên môi trường để người đọc không tưởng số 0 là lỗi), và một mục trong
**Tài liệu & SDK**. `GET /api/v1/me` trả thêm `mode` để một deployment tự khẳng
định được trong smoke check của chính nó.

Webhook: payload thêm `data.mode`, chữ ký/header/hình dạng **giống hệt** live —
một endpoint phục vụ được cả hai thế giới, và bên nhận verify ở sandbox thì
verify được ở production.

### Tests

`tests/test_204_sandbox.py` — **23 test**: tiền tố nhận diện được; cả hai tiền
tố vào cùng một cửa và `/me` nói đúng môi trường; xoay khoá giữ môi trường; lời
gọi test **không chạm sổ** (số dư + mọi dòng sổ); sandbox mở cho tài khoản **0
credit**; hard cap chặn live nhưng không chặn test; test **không** gọi provider
còn live **có**; hình dạng đúng `output_schema`; **số lượng** đúng `count`
(1/2/4); tool không khai `output_counts` vẫn trả 1; artifact tải được qua đúng
đường thật và là PNG thật; `mode` có trên mọi job; hai chiều 404 (đọc, huỷ,
tải artifact); listing tách hai thế giới; job cũ không có mode là live; webhook
test ký như live và nói `mode`; cổng hiện môi trường; và các luật đơn vị.

`test_191` đổi một khẳng định: hướng dẫn từng "nói thẳng chưa có sandbox", giờ
nói thẳng sandbox **không chứng minh được chất lượng** đầu ra.

### Tài liệu đã sửa cho khớp sự thật mới

`DEVELOPER_GUIDE.md` §12 (viết lại), `PROTOCOL_V1.md` §2.2 (mới),
`THREAT_MODEL_V1.md` (rủi ro "không có sandbox" → đóng, nêu rủi ro còn lại),
`RELEASE_READINESS_V1.md`, `DEVELOPER_KEYS_V1.md` §10 (cột `mode` giờ có ngữ
nghĩa thật đứng sau), `FULL_PLATFORM_GAP_MATRIX.md` #15 → DONE.

### Rollback

`alembic downgrade a3b4c5d6e7f8`; xoá `platform_core/public_api/sandbox.py`; bỏ
nhánh `is_test` trong `invocation.submit`, `_ket_qua_sandbox` trong worker,
`ensure_same_mode`/`restrict_to_mode` trong route job/upload; bỏ `mode` khỏi
`Principal`/`/me`/payload webhook/`_public_job`/dòng usage; bỏ `output_counts`
khỏi hai manifest + `registry` + `catalog`; hoàn nguyên template; xoá `test_204`.
Khoá `ltt_tk` đã cấp sẽ ngừng phân giải — thu hồi chúng trước khi hạ.

### Acceptance Gate

| Yêu cầu của EXT-12 | Kết quả |
|---|---|
| Default sandbox provider cost = 0 | ✅ không `giu_cho`, không dòng sổ, `credit.held = charged = 0`; chạy được với số dư 0 |
| No live/mock cross-over | ✅ 404 hai chiều (đọc/huỷ/artifact), listing lọc trong SQL, job không có mode = live |
| Schema parity | ✅ dựng từ `output_schema`; **và** đúng số lượng theo `output_counts` (lỗi do kiểm trình duyệt bắt) |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/13_API_ADMIN_CONSOLE_CORE_USERS_PROJECTS_KEYS_CLIENTS_TOOLS.txt`
(EXT-13).

---

## EXT-13 — ADMIN CONSOLE CORE ✅

### Entry gate

EXT-12 PASS ✅ (`3e4d708`), cây sạch. **Không migration mới** — khu này chỉ đọc
những bảng đã có và ghi vào `nhat_ky_admin` đã có từ F-06.

### INVENTORY: cái gì đã có, cái gì thiếu

| Thứ | Trạng thái trước EXT-13 |
|---|---|
| Trang quản trị (sqladmin, cổng `is_operator`, vỏ dark) | ✅ `server/admin.py` |
| Nhật ký thao tác admin | ✅ bảng `nhat_ky_admin` + `ghi_nhat_ky()` (F-06) |
| CSRF cho form quản trị | ✅ `server/auth/csrf.py`, đã dùng ở 5 view |
| Quản **khoá provider** (`api_keys`) | ✅ — nhưng **không phải** khoá của khách |
| Quản **khoá developer**, project, độ phơi bày tool | ❌ `MISSING` — chỉ có đường CSDL |
| Mọi truy vấn khu API | ⚠️ `PARTIAL` — đều **user-scoped**, không có bản đọc xuyên tài khoản |

Nói cách khác: mọi câu hỏi vận hành về API ("khoá nào đang đốt credit lúc 3 giờ
sáng") chỉ trả lời được bằng shell CSDL — vừa chậm vừa **không để lại dấu vết**.

### REUSE: không viết lại cái gì

`is_operator` (cổng quyền), `ghi_nhat_ky` (F-06), `_admin_shell` (vỏ), CSRF,
`keys.revoke` / `keys.set_enabled` (chính hàm cổng khách gọi),
`key.status()` (trạng thái suy ra), `build_catalog` + `project_tool` (tool),
`load_public_api_config` (allowlist). Không class CSS mới → **không đổi asset
hash**, không lo cache-bust.

Thu hồi **uỷ quyền** cho `keys.revoke` chứ không tự set cột: một định nghĩa thứ
hai của "đã thu hồi" sẽ lệch với cái thứ nhất ngay lần đầu một trong hai đổi.

### Đặt ở đâu, và vì sao không nhét vào `admin.py`

- `platform_core/public_api/admin_console.py` — **toàn bộ** truy vấn và luật.
- `server/admin_api.py` — chỉ đọc request, kiểm CSRF, gọi service, dựng HTML,
  ghi nhật ký. 4 view, đăng ký từ `setup_admin`.

`admin.py` đã 1.174 dòng và lo miền khác (người dùng, sổ credit, khoá provider,
đơn hàng). Nhét thêm vào là đúng cơ chế đã sinh ra file route 1.799 dòng trước
đây (AGENTS.md mục 8).

### Bốn trang, đúng phần CORE của prompt

| Trang | Trả lời câu hỏi |
|---|---|
| `/admin/api-tong-quan` | Credential đang lưu hành, lời gọi có chạy không, tiền có chảy không, callback có tới không — mỗi con số đổi được một quyết định |
| `/admin/api-tai-khoan` | Ai đang dùng API; một trang gom project + khoá + ngân sách + webhook + 20 lời gọi gần nhất của **một** người |
| `/admin/api-khoa` | Mọi credential của khách, lọc theo trạng thái **suy ra** / môi trường / email; trang chi tiết kèm **bằng chứng để hành động** |
| `/admin/api-cong-cu` | Tool nào mở, mở theo luật nào, đang chạy ra sao |

NAV trong prompt là **mục tiêu của cả khu admin** (COMMON_RULES §7), không phải
việc của riêng EXT-13. Theo ROADMAP: Requests/Support-Trace/Security/Health →
**EXT-16**; Policies/Limits/kill switch → **EXT-14**; Pricing → **EXT-15**;
Versions/Status → **EXT-17**. Trang Công cụ **nói thẳng** nó chưa có kill switch
và đó là việc của EXT-14, thay vì vẽ một cái nút không bấm được.

Service account / OAuth client: **DEFERRED** theo D6/D7 đã chốt ở EXT-01 — chưa
có bảng nào để hiện, và một tab rỗng hứa hẹn còn tệ hơn không có tab.

### Ba luật của khu này

**Không có đường nào lộ bí mật.** Không hiện khoá, không hiện `verifier_digest`,
không hiện secret webhook (vốn đã lưu mã hoá), không hiện credential provider.
Có test lấy token thật rồi quét **mọi** trang admin để chắc chuỗi đó không xuất
hiện ở đâu.

**Mọi mutation ghi nhật ký, cùng transaction.** `admin_email`, hành động, đối
tượng (`key_id (user_id)`) và **lý do**. Thao tác bị từ chối **không** ghi — một
việc không xảy ra mà có dòng nhật ký thì nhật ký thành nhiễu.

**Nguy hiểm thì phải nói lý do và phải xác nhận.** Thu hồi cần lý do ≥ 8 ký tự
**và** một ô tích. Tắt tạm thời chỉ cần lý do — nó đảo ngược được, và một người
nghi có rò rỉ cần cầm máu mà không phá tích hợp của khách vì một nghi ngờ.

### Bounded reads

Mọi danh sách phân trang (`PAGE_SIZE=50`, trần `MAX_PAGE_SIZE=200` kể cả khi
caller xin 10.000) và đếm tổng, vì "12 khoá" với "50 khoá đầu của 4.000" dẫn tới
hai hành động khác nhau. Các bảng này lớn theo **traffic**, không theo số khách.

### Hai lỗi thật bắt được khi chạy

1. `subquery().c.keys` phân giải thành **`ColumnCollection.keys`** — cái method —
   và SQLAlchemy từ chối nó cách chỗ gây lỗi vài frame. Đổi nhãn thành
   `key_count`.
2. Nút "Hồ sơ đầy đủ" trỏ `?id=` trong khi trang chi tiết người dùng nhận `?q=`.
   Link hỏng nhưng vẫn trả **200** (một form tìm kiếm rỗng) — hỏng mà không ai
   thấy hỏng. **Kiểm bằng trình duyệt bắt được, test không.** Giờ đã có test.

### Kiểm bằng trình duyệt (uvicorn thật, cổng 8123, SQLite tạm)

Seed: 1 operator, 2 khách, khoá live + test + một khoá đã thu hồi, 5 dòng nhật
ký request, 1 webhook. Đã đi hết: khách đăng nhập bị **đá khỏi** `/admin/api-khoa`;
operator vào được cả 4 trang; **thu hồi không tích ô → bị từ chối** kèm biểu ngữ
đỏ, khoá vẫn `active`; **tắt kèm lý do → thành công**, bộ nút đổi sang "Bật lại",
và dòng `api_khoa_disable` hiện ở **Nhật ký admin** kèm email người thao tác và
lý do. Console: 0 lỗi (ngoài một 405 do chính tôi GET `/logout`). Network: 0
request hỏng.

### Tests

`tests/test_205_admin_api_console.py` — **28 test**: khách chưa đăng nhập và
khách **đã** đăng nhập đều bị chặn ở cả 4 trang; khách POST thẳng vào action
không thu hồi được gì và **không sinh dòng nhật ký**; disable/enable/revoke đều
ghi đúng một dòng kèm lý do và email; thu hồi là **một chiều** (bật lại bị từ
chối, lần thu hồi thứ hai bị từ chối và **không** ghi thêm); thiếu lý do / lý do
quá ngắn / thiếu ô xác nhận / thiếu CSRF / thao tác lạ → **không đổi gì, không
ghi gì**; chữ xác nhận có thật trên trang; token thật và digest **không** xuất
hiện ở bất kỳ trang nào; secret webhook không lộ; phân trang + trần trang; lọc
theo trạng thái suy ra (kể cả `expired`); danh sách tài khoản chỉ gồm người có
khoá; overview đếm live/test/revoked tách nhau; trang tool tách **declared** với
**published**; link hồ sơ đầy đủ mở đúng trang.

### Rollback

Xoá `server/admin_api.py` + `platform_core/public_api/admin_console.py`, gỡ 5
dòng NAV và vòng `add_view` trong `server/admin.py`, xoá `test_205`. Không có
migration để hạ, không có dữ liệu để mất — khu này chỉ đọc, và thứ duy nhất nó
ghi (`nhat_ky_admin`) là bằng chứng, giữ lại.

### Acceptance Gate

| Yêu cầu của EXT-13 | Kết quả |
|---|---|
| Non-admin blocked | ✅ chưa đăng nhập **và** đã đăng nhập-nhưng-không-phải-admin đều bị đá về `/login`; POST thẳng vào action cũng không đổi được gì (kiểm cả bằng test lẫn trình duyệt) |
| All admin mutations audited | ✅ mỗi mutation đúng một dòng `nhat_ky_admin` kèm ai/làm gì/lên cái gì/**vì sao**; thao tác bị từ chối không ghi |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/14_ADMIN_POLICY_TIERS_QUOTA_CONCURRENCY_CAPACITY_KILL_SWITCH.txt`
(EXT-14).

---

## EXT-14 — POLICY ENGINE: TIER, HẠN MỨC, CAPACITY, KILL SWITCH ✅

### Entry gate

EXT-13 PASS ✅ (`747e006`), cây sạch. Migration mới: **`c5d6e7f8a9b0`** (head) —
ba bảng, không sửa bảng nào đang có.

### AUDIT: năm lớp đã có, và cái lỗ trong đó

| Lớp | Trước EXT-14 | Khoá theo |
|---|---|---|
| 1 auth-failure throttle | ✅ | IP + key_id |
| 2 request RPM | ✅ | **key_id** ← lỗ |
| 3 create RPM | ✅ | **key_id** ← lỗ |
| 4 job đồng thời + theo lớp tài nguyên | ✅ | user_id |
| 5 trần credit ngày | ✅ | user_id |
| Cấu hình | chỉ **global** từ env — một con số cho mọi khách | |

**Lỗ lách có thật:** lớp 2–3 bucket theo `key_id`. Một tài khoản muốn gấp 5 lần
nhịp chỉ cần vào trang tạo khoá và tạo 5 khoá — không cần khai thác gì. Lớp 4–5
đã theo tài khoản nên không dính. Đây chính là "anti-bypass across multiple
keys" trong đề bài, và giờ mỗi nhịp tính **cả cho khoá lẫn cho tài khoản**.

### Chuỗi ưu tiên

```
global(env) → tier(policy mặc định) → user → project → credential → tool
```

Mỗi bước **chỉ ghi đè trường nó thực sự đặt**. Không có luật đó thì gắn một
policy để nới một hạn mức sẽ lặng lẽ reset bốn hạn mức khác, và người gắn không
có cách nào biết.

Vì thế **mọi cột số đều NULL-able và NULL = kế thừa**, không dùng 0 làm dấu
"chưa đặt": 0 là một hạn mức thật và có nghĩa (nhịp 0 = từ chối tất cả), tiêu nó
cho "chưa đặt" thì không bao giờ diễn đạt được nữa.

`Limits.sources` ghi lại **bước nào đặt trường nào**. Câu hỏi đầu tiên về bất kỳ
hạn mức nào là "vì sao lại là con số đó", và một engine không trả lời được sẽ
biến mọi cuộc hỗ trợ thành một cuộc điều tra. Trang admin hiện đúng cột đó.

### Kill switch ≠ hạn mức bằng 0

Hạn mức là chính sách thường trực; công tắc là công cụ xử lý **sự cố**, có người
bật, có **lý do bắt buộc** và nên có **hạn dùng**. Gộp hai thứ lại thì bản ghi
duy nhất về "3 giờ sáng tắt cái này vì sao" chỉ còn là một con số trông như cấu
hình.

Sáu phạm vi: `maintenance`, `global_writes`, `tool`, `user`, `project`, `key`.
Hết hạn = **tự hết hiệu lực**, không cần job dọn — lỗi thường gặp nhất của một
công tắc sự cố là không ai nhớ tắt nó đi.

**Không thêm mã lỗi mới.** `service_unavailable` (503), `read_only` (503) và
`forbidden` (403) đã diễn đạt đủ. Bảng lỗi công khai và tài liệu sinh tự động
**không đổi**. Chỉ thêm một hàm dựng cho `service_unavailable` — mã đã có trong
registry từ EXT-02 nhưng chưa có gì tạo ra nó.

Khi nhiều công tắc cùng áp, caller được báo **cái rộng nhất**: đó là cái mà gỡ
đi thì họ chạy được.

**Lý do operator gõ được trả về cho khách.** Nó do người vận hành viết cho khách
hàng; giữ lại chỉ chuyển đúng cuộc trò chuyện đó sang một ticket hỗ trợ.

### Capacity guard

`platform_core/public_api/capacity.py` — hỏi lại thứ nền tảng **đã biết**, không
dựng engine sức khoẻ thứ hai: storage có nhận ghi không (round trip thật, như
`/health/ready` làm với CSDL), có GPU không (chỉ với app khai `requires=gpu`),
và pool credential.

Chỉ chặn ở **tạo job**, và chặn **trước khi giữ credit**. Đọc vẫn chạy trong sự
cố — khách có provider hỏng vẫn cần liệt kê job và tải artifact hôm qua; chặn cả
đọc là biến một nền tảng suy giảm thành một nền tảng tối.

### Ba lỗi thật, bắt được bằng cách chạy chứ không phải bằng cách nghĩ

1. **Capacity chặn nhầm mọi thứ.** Tôi suy đoán mọi tool ảnh/video lấy
   credential từ `api_pool`. Đọc code thật: các app có **fallback sang biến môi
   trường**. Pool rỗng ⇒ **không** nói lên điều gì. Luật đúng: im lặng khi pool
   không phải nguồn cho category đó; chỉ báo khi pool **có** khoá mà **không**
   khoá nào dùng được. Bộ test hiện có bắt được ngay (18 test đỏ).
2. **So sánh datetime naive với aware.** SQLite trả naive cho `expires_at`,
   PostgreSQL trả aware. `is_active()` ném lỗi — và nó nằm trong đường kiểm kill
   switch của **mọi** request, tức là biến một công cụ xử lý sự cố thành một sự
   cố. Chuẩn hoá về UTC trước khi so, đúng cách `keys.py` đã làm.
3. **`max_upload_bytes` lấy nền sai và không nối vào đâu cả.** Trang admin hiện
   `262144` — đó là trần **thân JSON** của control plane, không phải trần upload,
   sai bốn bậc độ lớn và về một thứ hoàn toàn khác. Tệ hơn: trường này chưa được
   thi hành ở đâu — đúng loại "hứa suông" mà tôi vừa từ chối làm với priority.
   Giờ nền là `media.MULTIPART_LIMIT` (90 MB, chỗ Cloudflare chặn) và vé upload
   **thật sự** tôn trọng nó; policy chỉ **hạ** được, không **nâng** được quá
   trần của nền tảng.

### Priority class: CỐ Ý KHÔNG LÀM

Đề bài cho phép "only if scheduler supports". `jobs.claim()` sắp xếp
`order_by(Job.created_at)` thuần FIFO; `priority` chỉ tồn tại trên bảng
`api_keys` của **provider**, không phải trên `Job`. Một trường `priority` mà
không scheduler nào đọc là một lời hứa nền tảng không giữ được — lại còn hiện ra
trong admin. Nó thuộc về một thay đổi scheduler, không thuộc về đây. Có test
khoá tính chất này lại.

### Admin

Hai trang mới trong khu API (cùng khuôn EXT-13: lý do bắt buộc, xác nhận cho
thao tác nguy hiểm, ghi nhật ký cùng transaction): **Chính sách** (kèm bảng "mức
nền đang áp dụng" và cột *đến từ*) và **Kill switch**. Trang Công cụ ở EXT-13
từng nói "kill switch là việc của EXT-14" — giờ nó có thật.

### Tests

`tests/test_206_policy_engine.py` — **35 test**; `test_205` thêm **8 test** cho
hai trang admin (tổng 36).

Precedence: mức nền khi không có policy; mỗi bước chỉ ghi đè cái nó đặt; chuỗi
chạy rộng→hẹp và gỡ bước hẹp thì tụt đúng một bậc; tool override là lời cuối;
override của policy **thua** thì không áp; **kết quả không phụ thuộc thứ tự
chèn**; chỉ một default; một subject một policy; xoá policy thì tụt bậc chứ
không mồ côi; **0 là hạn mức thật**; input rác bị từ chối.

Abuse isolation: **nhiều khoá không mua thêm nhịp**; một tài khoản bị bóp không
ảnh hưởng tài khoản khác; đọc và ghi có hai hạn ngạch riêng.

Kill switch: maintenance chặn cả đọc lẫn ghi; global_writes để đọc yên; tài
khoản bị đình chỉ nhận 403 kèm lý do; tắt một tài khoản không ảnh hưởng tài
khoản khác; tool bị tắt bị từ chối **trước khi giữ credit** (có test số dư);
công tắc hết hạn tự thôi áp dụng; công tắc rộng nhất là cái được báo; thiếu lý
do / sai phạm vi / hạn dùng ở quá khứ đều bị từ chối; tắt công tắc thì dịch vụ
trở lại; khoá và project tắt được riêng.

Hai tính chất đề bài nêu thẳng: **giao diện web vẫn chạy** khi API bị tắt (job
nộp kiểu UI vẫn vào hàng đợi), và **đổi policy không định giá lại một báo giá đã
ký**.

### Kiểm bằng trình duyệt (uvicorn thật, cổng 8123)

Bật maintenance **không tích ô** → bị từ chối kèm biểu ngữ đỏ. Tích ô + lý do +
30 phút → bật được, bảng hiện đúng ai bật/lý do/hạn dùng. Gọi
`GET /api/v1/tools` bằng khoá thật → **503 `service_unavailable`** kèm đúng lý do
operator vừa gõ. Bấm "Bật lại" kèm lý do → API trả **200** lại, và **Nhật ký
admin** có đủ hai dòng `api_kill_engage` / `api_kill_release` kèm lý do và email
người thao tác. Console: 0 lỗi.

### Rollback

`alembic downgrade b4c5d6e7f8a9`; xoá `policy.py` + `capacity.py`; bỏ
`_refuse_if_switched_off` khỏi `auth.py`, hai helper khỏi `jobs.py`, trần upload
khỏi `uploads.py`; trả `limits.py` về đọc thẳng `config`; bỏ 2 view + 2 mục NAV;
xoá `test_206` và khối EXT-14 trong `test_205`. Không mất dữ liệu vận hành: ba
bảng mới chỉ chứa chính sách và công tắc.

### Acceptance Gate

| Yêu cầu của EXT-14 | Kết quả |
|---|---|
| Deterministic precedence tests | ✅ chuỗi cố định, chỉ-ghi-đè-cái-đã-đặt, có test **đảo thứ tự chèn cho cùng kết quả**, và `sources` nói rõ số đến từ đâu |
| Abuse isolation | ✅ nhiều khoá không cộng dồn nhịp (bucket theo tài khoản); một tài khoản bị bóp không ảnh hưởng người khác |
| UI apps unaffected | ✅ mọi công tắc phạm vi `/api/v1`; test dựng job kiểu UI trong lúc API đang maintenance và job vẫn vào hàng đợi; trang nói rõ phạm vi |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/15_PRICING_CATALOG_VERSIONED_CREDITS_COST_MARGIN_AND_QUOTE_SIMULATOR.txt`
(EXT-15).

---

## EXT-15 — GIÁ CÓ PHIÊN BẢN, CHI PHÍ, MARGIN, MÔ PHỎNG ✅

### Entry gate

EXT-14 PASS ✅ (`0b050e1`), cây sạch. Migration mới: **`d6e7f8a9b0c1`** (head) —
hai bảng, không sửa bảng nào đang có.

### Quyết định thiết kế lớn nhất: bảng giá KHÔNG định giá

Mọi app khai `credit_cost(params)`, và `registry.credit_for()` là thứ **duy
nhất** biến một lời gọi thành con số. Một bảng giá *thay thế* nó sẽ là engine
định giá thứ hai (COMMON_RULES §3), và lần đầu hai bên lệch nhau thì không ai
nói được khách bị tính theo cái nào.

Nên **phiên bản giá chỉ ghi lại chế độ nào đang có hiệu lực** — cửa sổ, sàn,
trần, làm tròn, tham chiếu công thức — rồi nhãn đó được **đóng dấu lên báo giá
và lên job**. Đối soát một khoản tiền sau nhiều tháng là đọc hai sự thật đã
được ghi *cùng lúc*, thay vì chạy lại code hôm nay trên lời gọi hôm qua.

Hệ quả: **"không sửa giá hồi tố" là tính chất của lược đồ**, không phải một luật
ai đó phải nhớ. Báo giá được ký (`itsdangerous`) mang cả số tiền lẫn nhãn; phát
hành bản mới là **thêm dòng** và đóng cửa sổ bản cũ; thu hồi là đặt ngày kết
thúc. Không có đường code nào sửa số của một dòng cũ.

### Lỗi tiền thật, chỉ lộ ra khi bấm thử

Operator công bố trần 7. Báo giá trả **7**. Job giữ **10**.

`submit_with_credit` tự tính lại giá từ `registry.credit_for()` và **không** thấy
sàn/trần đã công bố — nên trần áp lên cái khách được **xem**, không áp lên cái
khách bị **tính**. Đây là hình dạng tệ nhất mà một lỗi giá có thể có.

Không test nào bắt được, vì mọi ca trước đó đều có giá-sau-chặn bằng
giá-thô. Chỉ có bấm nút trên trình duyệt mới lộ.

Sửa: `submit_with_credit(..., quoted_credit=)` — có báo giá thì giữ **đúng** số
đã hứa. Vẫn gọi `credit_for` để giữ cảnh báo sớm khi một `job_type` chưa khai
giá. Đường UI không truyền tham số này nên tính như cũ (có test khoá lại).

### Chi phí: đo được là bằng chứng, tiền là ước lượng

Nền tảng **đo** được `duration_ms` (worker ghi) và số byte. Nền tảng **không**
biết giá tiền của một giây GPU hay một byte lưu trữ — đó là con số hợp đồng do
người vận hành nhập.

`api_keys.total_tokens` là **tổng theo khoá**, dùng chung cho mọi job nó phục
vụ. Chia ra cho từng job là **bịa**, nên module từ chối; token chỉ được ghi khi
chính handler báo cho job đó.

Vì thế mọi số tiền mang `is_estimate=True` **trong dữ liệu**, không phải trong
một dòng chú thích. Chưa cấu hình đơn giá thì **không ghi quan sát nào** — một
chi phí bằng 0 là một khẳng định, và nền tảng chưa có quyền khẳng định điều đó.
Trang Margin nói thẳng: doanh thu đã đối soát, chi phí là ước lượng, đừng đổi
giá bán chỉ dựa vào trang này.

### Mô phỏng

Gọi **đúng** `invocation.price` mà đường báo giá gọi, áp đúng sàn/trần đang có
hiệu lực. Một simulator có số học riêng trả lời một câu hỏi không ai hỏi. Không
sinh quote token và không trừ credit, nên một mô phỏng **không** trình ra
`POST /jobs` được — nó là câu trả lời, không phải lời hứa.

Đặt ở **cổng lập trình viên**, không phải một route API mới: thêm một con đường
thứ hai tới đường định giá để chứng minh hai đường cho ra cùng số là tự mâu
thuẫn.

### Hai chỗ code hiện có bắt lỗi tôi, và cả hai lần code đều đúng

1. `notifications.KINDS` là danh sách trắng → từ chối loại `margin.negative` tôi
   tự đặt. Danh sách trắng chính là thiết kế nói rằng loại cảnh báo phải khai
   tập trung. Giờ khai đúng chỗ, kèm cooldown, và **cố ý không** vào
   `EMAIL_KINDS`: con số đằng sau là ước lượng, mà ước lượng không có quyền đánh
   thức ai lúc nửa đêm.
2. `ApiNotification.user_id` là khoá ngoại tới `users` → không gửi được với user
   rỗng. Thay vì nới cột thành nullable (bắt mọi truy vấn khác xử lý một trường
   hợp chỉ tồn tại cho một loại cảnh báo), gửi tới từng tài khoản admin thật.

### Một lỗi giao diện nữa do trình duyệt bắt

Bản nháp vừa tạo bị xếp vào **Lịch sử**. Một bản nháp chưa từng có hiệu lực thì
không thể là quá khứ — và người vừa tạo nó sẽ không bao giờ tìm ở đó. Giờ bản
nháp luôn thuộc "Sắp tới", bất kể ngày bắt đầu.

### Tests

`tests/test_207_pricing.py` — **31 test**; `test_205` thêm **6 test** cho hai
trang admin (tổng 42).

Gồm: không có phiên bản vẫn báo giá được và mang nhãn `unversioned`; nhãn hiện
trên quote; sàn/trần chặn số của app mà không thay nó; ba kiểu làm tròn; bản
theo model thắng bản theo tool; **phát hành bản mới không đổi báo giá đã ký**
(quote cũ bị từ chối bằng `price_changed`, không bị định giá lại); job giữ nhãn
lúc được báo giá; phát hành **đóng cửa sổ** chứ không sửa số; thu hồi không định
giá lại cái đã tính; **job giữ đúng số đã hứa** (test hồi quy cho lỗi 7→10);
đường UI vẫn tự tính; **snapshot toàn bộ sổ credit trước/sau mọi thao tác giá và
margin → giống hệt**; mô phỏng khớp báo giá thật, không trừ tiền, không sinh
quote; chưa cấu hình đơn giá thì không ghi quan sát; token chỉ tính khi handler
báo; margin đọc doanh thu từ sổ và chi phí từ quan sát; margin âm báo cho admin
thật kèm chữ "ƯỚC LƯỢNG"; vòng đời draft→scheduled→active→retired.

### Kiểm bằng trình duyệt (uvicorn thật, cổng 8123)

Tạo bản nháp (bắt buộc lý do) → hiện ở **Sắp tới**, không phải Lịch sử. Phát
hành (bắt buộc lý do) → **Đang áp dụng**, preview nói *"app tính 10, bị chặn bởi
2026-08-a"*. Gọi API thật bằng khoá thật: `POST /quotes` → **7**, nhãn
`2026-08-a`; `POST /jobs` → giữ **7** (trước khi sửa là 10); job meta mang
`pricing_version=2026-08-a`. Trang Margin hiện đúng "Chưa cấu hình đơn giá nào"
thay vì một số 0 tự tin. Trang mô phỏng ở cổng dev: `count=4` → *"SẼ TÍNH 7,
CÔNG THỨC APP TÍNH 20 — bị chặn"*. Console: 0 lỗi.

### Rollback

`alembic downgrade c5d6e7f8a9b0`; xoá `pricing.py` + `costing.py`; bỏ
`pricing_version` khỏi `quotes.issue`/`invocation`/route job; bỏ `quoted_credit`
khỏi `submit_with_credit` (**lưu ý: hoàn nguyên là mang lỗi báo-7-giữ-10 trở
lại**); bỏ `_ghi_chi_phi` khỏi worker; bỏ 2 view + 2 mục NAV + trang
`dev_pricing.html`; bỏ `MARGIN_NEGATIVE` khỏi `notifications`; xoá `test_207` và
khối EXT-15 trong `test_205`.

### Acceptance Gate

| Yêu cầu của EXT-15 | Kết quả |
|---|---|
| No retroactive price mutation | ✅ tính chất cấu trúc: nhãn + số tiền được ký cùng lúc; phát hành là thêm dòng, không sửa dòng cũ; quote cũ bị **từ chối** chứ không bị định giá lại |
| Ledger remains billing truth | ✅ snapshot toàn bộ sổ trước/sau mọi thao tác giá + margin → giống hệt; margin đọc doanh thu **từ sổ**, chi phí từ bảng khác |
| Pricing publish audited | ✅ mỗi create/publish/retire ghi `nhat_ky_admin` kèm ai/cái gì/**vì sao**; thiếu lý do thì không đổi gì và không ghi gì |

**NEXT_EXTENSION_PROMPT_ALLOWED=true**
Prompt kế: `prompts/16_ADMIN_OPERATIONS_REQUESTS_JOBS_WEBHOOK_SECURITY_SUPPORT_TRACE.txt`
(EXT-16) —
**checkpoint full gate**.
