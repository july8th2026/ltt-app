# Activepieces — khảo sát piece framework / engine / giấy phép cho LTT (22/09/2026)

Bổ sung cho `docs/architecture/workflow_v2_audit/04_ACTIVEPIECES_AUDIT.md` (đã phủ runtime/waitpoint — không lặp lại).

**Nguồn:** clone `D:\LTT_ARCHITECTURE_LAB\activepieces`, tag `0.90.2`, SHA `fad84c1a58a596d5d0dc1a2f043104f8a4df3af8` (04/09/2026).
Bản mới nhất upstream: `0.91.1` (phát hành 21/09/2026, qua GitHub MCP `get_latest_release`). Đây là bản vá: cherry-pick sửa retry subflow và tham chiếu connection (#15689). Không cần clone lại.
Mọi đường dẫn bên dưới tính từ gốc repo ở SHA trên.

---

## 1. Giấy phép

| Vùng | Giấy phép | Bằng chứng |
|---|---|---|
| Toàn repo, trừ 2 thư mục bên dưới | **MIT (Expat)** | `LICENSE`: các phần nằm ngoài những thư mục đã nêu thì theo "MIT Expat" |
| `packages/ee/` (tại tag này chỉ còn `LICENSE` và `embed-sdk/`) | **Enterprise License** | `packages/ee/LICENSE` |
| `packages/server/api/src/app/ee/` (26 thư mục con: `oauth-apps`, `platform`, `global-connections`, `secret-managers`, `managed-authn`, `billing-usage-report`, `scim`, `audit-logs`...) | **Enterprise License** | `LICENSE` nêu đích danh đường dẫn này |
| `packages/pieces/{framework,common,core,community}` | **MIT** (nằm ngoài vùng ee) | Không có LICENSE riêng. Không `package.json` nào của piece có trường `license` (grep ra 0 kết quả). `npm view @activepieces/piece-slack license` trả về rỗng |
| `packages/server/engine`, `packages/server/sandbox`, `packages/server/worker`, `packages/core/*` | **MIT** | Nằm ngoài vùng ee |

Enterprise License chỉ cho dùng production khi có thuê bao. Không được tự do chép hay bán. Chỉ được sửa và chép để phát triển hoặc kiểm thử.

**Kết luận:** chép, port hay chạy pieces community, framework và engine trong một SaaS thương mại đều **được phép theo MIT**. Nghĩa vụ duy nhất: giữ copyright notice ("Copyright (c) 2020-2024 Activepieces Inc." kèm nguyên văn MIT) trong mã chép hoặc bản phân phối.

⛔ Không chép bất cứ thứ gì từ `server/api/src/app/ee/**`. Cách làm "platform OAuth app" và "global connections" nằm ở đó, nên LTT phải tự viết lại, và không nhìn mã ee để viết.

⚠️ Dịch vụ `https://secrets.activepieces.com` (cloud OAuth) là **dịch vụ**, không phải mã. Giấy phép MIT không cho quyền dùng nó (xem §5).

⚠️ Tên và logo: `logoUrl` của piece trỏ tới `cdn.activepieces.com`. Nên tự host logo và không dùng thương hiệu Activepieces.

---

## 2. Piece framework

**Mã nguồn:** `packages/pieces/framework/src/lib/`. Kiểu dùng chung nằm ở `packages/core/piece-types/src/lib/`.

- **`createPiece`** (`piece.ts:78`) nhận `displayName, logoUrl, auth, actions[], triggers[], categories, authors, minimumSupportedRelease, maximumSupportedRelease`.
  - Hàm khởi tạo ép `minimumSupportedRelease` không thấp hơn `MINIMUM_SUPPORTED_RELEASE_AFTER_LATEST_CONTEXT_VERSION = '0.82.0'` (`context/versioning.ts`).
  - Ba piece mẫu đều khai `minimumSupportedRelease: '0.86.4'`.
- **`createAction`** (`action/action.ts:71`) nhận `name, displayName, props, run, test?` (mặc định `test` = `run`), `requireAuth` (mặc định true) và `errorHandlingOptions` (continueOnFailure / retryOnFailure).
- **`createTrigger`** (`trigger/trigger.ts`) nhận `type: TriggerStrategy`. Enum ở `core/piece-types/src/lib/trigger.ts:3` gồm `POLLING | WEBHOOK | APP_WEBHOOK | MANUAL`. Các hook:
  - `onEnable`, `onDisable`, `run → unknown[]`, `test`, `sampleData`, `onStart?`
  - `handshakeConfiguration` / `onHandshake`, `renewConfiguration` / `onRenew`
  - Riêng APP_WEBHOOK: `context.app.createListeners({events, identifierValue})`
  - Riêng POLLING: `context.setSchedule({cronExpression, timezone})`
- **`PieceAuth`** (`property/authentication/index.ts`): `SecretText`, `BasicAuth`, `CustomAuth` (props tự do), `OAuth2`, `OIDC`, `None`.
  - Một piece được khai **mảng** auth, ví dụ Sheets là `[OAuth2, CustomAuth]`.
  - `OAuth2` (`oauth2-prop.ts:40-61`) chỉ khai `authUrl, tokenUrl, scope[], prompt, pkce, pkceMethod, authorizationMethod, grantType` (authorization_code / client_credentials / cả hai) và `extra`. **Piece không chứa client_id hay secret.**
- **`Property`** (`property/input/index.ts`): ShortText, LongText, RichText, Markdown, Number, Checkbox, Json, Array, Object, DateTime, File, Color, StaticDropdown, **Dropdown** (động: `options(propsValue, ctx)` với `refreshers[]`), MultiSelectDropdown, **DynamicProperties** (`dynamic-prop.ts`).
  - DynamicProperties dựng một map prop con lúc chạy, nhận `(propsValue + auth, PropertyContext)`.
  - Kiểu con của nó chỉ được là ShortText, StaticDropdown, Json, Array hoặc StaticMultiSelect.
  - Việc tính options chạy trong engine qua `EXECUTE_PROPERTY`.
- **Versioning:**
  - Mỗi piece là một gói npm `@activepieces/piece-<tên>` có semver riêng: slack `0.17.9` trong repo, trong khi npm đã có `0.20.0`.
  - Mỗi bước trong flow ghim `pieceName + pieceVersion` (xem 04 §9).
  - Thêm `ContextVersion` V1/V2 để engine dựng context tương thích ngược (`versioning.ts`). `run.pause` cũ được giả lập bằng `createWaitpoint` và `waitForWaitpoint`, đánh dấu deprecated tới 12/10/2026.
- **Đóng gói:** `tsc` ra `dist/`, publish npm. Gói phụ thuộc `@activepieces/pieces-framework` và `@activepieces/pieces-common`. `pieces-framework@0.32.0` trên npm kéo theo `ai@6`, `zod@4`, `semver` và `@activepieces/shared`.
- **Context mà action nhận** (`context/index.ts:29-310`):

  | Nhóm | Trường |
  |---|---|
  | Dữ liệu đầu vào | `auth` (giá trị connection đã giải mã), `propsValue`, `executionType` BEGIN/RESUME, `resumePayload` |
  | Lưu trữ | `store.put/get/delete(key, scope FLOW\|PROJECT)`, `files.write({fileName,data}) → URL` |
  | Tham chiếu nội bộ | `connections.get(key)`, `flows.list/current`, `step.name`, `project.id/externalId`, `tags.add` |
  | Máy chủ | `server{apiUrl, publicUrl, token}` |
  | Luồng chạy | `output.update`, `run{id, stop, respond, createWaitpoint({type DELAY\|WEBHOOK, resumeDateTime, responseToSend}) → {id, resumeUrl, buildResumeUrl}, waitForWaitpoint(id)}` |

---

## 3. Engine thực thi piece

- **Là tiến trình Node riêng.** `packages/server/engine/src/main.ts` được build bằng esbuild thành một tệp.
  - Worker spawn engine qua `packages/server/sandbox/src/lib/sandbox/fork.ts` (`child_process.fork`, cờ `--max-old-space-size`, `--expose-gc`, `--no-node-snapshot`).
  - Hoặc qua `isolate.ts`, tức nhị phân IOI `isolate` (namespace và cgroup Linux, `--share-net`, `--no-default-dirs`).
- **Chế độ** (`create-sandbox-for-job.ts:50-64`, biến `AP_EXECUTION_MODE`): `UNSANDBOXED` và `SANDBOX_CODE_ONLY` dùng fork thường. `SANDBOX_PROCESS` và `SANDBOX_CODE_AND_PROCESS` dùng isolate, **chỉ có trên Linux**. Trên Windows chỉ có fork, không cô lập.
  - Ngoài ra engine tự cài `ssrfGuard` (`main.ts`).
- **Giao thức worker ↔ engine:** socket.io trên websocket `ws://127.0.0.1:${AP_SANDBOX_WS_PORT}` (`worker-socket.ts:28`).
  - Engine là **client**, worker là server. Bên worker đóng vai trò client RPC.
  - RPC một sự kiện `{method, payload}` kèm ack (`core/execution/src/lib/engine/rpc.ts`).
  - Hợp đồng `EngineContract.executeOperation({operationType, operation}) → EngineResponse` (`engine-contract.ts`). Engine đẩy ngược `stdout`/`stderr` qua `WorkerNotifyContract`.
  - Nếu socket rớt thì engine tự thoát.
- **`EngineOperationType`** (`core/execution/src/lib/engine/engine-operation.ts:13`):
  - `EXTRACT_PIECE_METADATA`, `EXECUTE_FLOW`, `EXECUTE_ACTION`, `EXECUTE_PROPERTY`
  - `EXECUTE_TRIGGER_HOOK` (hook con: ON_ENABLE, ON_DISABLE, HANDSHAKE, RENEW, RUN, TEST)
  - `EXECUTE_VALIDATE_AUTH`, `EXECUTE_RESOLVE_CONNECTION_IDENTIFIER`, `EXECUTE_REFRESH_TOKEN_AUTH`
  - Còn có `ExecuteToolOperation` (gọi action như tool của agent).
- **Tải piece:**
  - Worker gọi `GET {publicApiUrl}v1/engine/pieces/bundle?name=&version=`. Endpoint này trả 307 sang npm hoặc S3 đã ký.
  - Worker lưu tệp `.tgz` rồi chạy `bun install --ignore-scripts` trong một workspace chung (`sandbox/src/lib/cache/pieces/piece-installer.ts`, `utils/bun-runner.ts:15-16`).
  - Engine nạp gói bằng `createRequire` (`engine/src/lib/helper/piece-loader.ts`).
- **Chạy độc lập một action — hợp đồng `EXECUTE_ACTION`:**
  - Đầu vào: `BaseEngineOperation{projectId, engineToken, internalApiUrl, publicApiUrl, timeoutInSeconds, platformId}` cộng `step: PieceAction` (settings gồm pieceName, pieceVersion, actionName, input có `{{connections['x']}}`, propertySettings).
  - Đầu ra: `{status: OK, response: {success, input, output, message}}` (`engine/src/lib/operations/action.operation.ts`).
  - **Nhưng engine không tự đứng được.** Nó gọi ngược HTTP về "server" bằng `engineToken`:

  | Endpoint | Dùng cho |
  |---|---|
  | `v1/worker/app-connections/{externalId}?projectId=` | Lấy giá trị auth đã giải mã và đã refresh (`piece-context/connection-resolver.ts`) |
  | `v1/store-entries` | `store.*` (`piece-context/store.ts`) |
  | `v1/files/{id}?token=` | `files.write` (`api/engine-file-api.ts`) |
  | `v1/waitpoints` | `run.createWaitpoint` (`piece-context/waitpoint-client.ts`) |
  | `v1/engine/{run-progress, step-progress, run-logs, flow-response}` | Báo tiến độ (`api/engine-run-api.ts`) |
  | `v1/engine/populated-flows` | `flows.list` |

  Vậy muốn gọi engine độc lập, LTT phải (a) dựng server socket.io kèm RPC ack đóng vai worker, và (b) mô phỏng khoảng 7 endpoint REST ở trên.

  **Cách gọn hơn** là bỏ qua engine: tự viết một "runner" Node nhỏ, `require` gói piece rồi gọi `piece.getAction(name).run(ctx)` với `ctx` do LTT tự dựng. Hợp đồng đầu vào/ra lúc đó là JSON `{piece, version, action, auth, props}` → `{ok, output | error}`. Framework chỉ là kiểu cộng với object thường.

---

## 4. Ba piece mẫu (0.90.2)

| | Google Sheets `0.16.9` | Slack `0.17.9` | Notion `0.6.10` |
|---|---|---|---|
| Action | 61 (60 + custom API call) | ~72 (71 + custom API call) | ~37 (36 + custom API call) |
| Trigger | 4: **2 POLLING** (new-spreadsheet, new-worksheet) + **2 WEBHOOK** (new-row-added-webhook, new-or-updated-row, dùng Drive watch channel + `renewConfiguration`/`onRenew`) | 14, **tất cả APP_WEBHOOK** (Events API của một Slack app, `events`/`verify` ở `index.ts:107,170`) | 4, **tất cả POLLING** (`pollingHelper`, `DedupeStrategy.LAST_ITEM`) |
| Auth | `[OAuth2 (accounts.google.com, oauth2.googleapis.com/token), CustomAuth (service account)]` (`common/common.ts:346`) | `[OAuth2 (slack.com/oauth/v2, bot + user_scope), CustomAuth (botToken SecretText)]` (`auth.ts`) | `[OAuth2 (api.notion.com/v1/oauth), CustomAuth (accessToken)]` (`auth.ts`) |
| npm | `@googleapis/sheets 13.0.2`, `@googleapis/drive 20.2.0`, `google-auth-library 10.5.0`, `gaxios`, `csv-parse`, `lodash`, `dayjs`, `nanoid` | `@slack/web-api 7.9.0`, `slackify-markdown` | `@notionhq/client 2.2.14`, `notion-to-md`, `@tryfabric/martian`, `dayjs` |

Chi tiết thêm:

- **`store`:**
  - `pollingHelper` (`pieces/common/src/lib/polling/index.ts`) lưu khoá `lastPoll` (chiến lược TIMEBASED) hoặc `lastItem` (chiến lược LAST_ITEM).
  - `onEnable` chụp mốc ban đầu. Có nhánh `isRepublish` để không phát lại sự kiện cũ.
  - Webhook của Sheets lưu số dòng hiện có theo `sheetId` cùng thông tin kênh watch để còn renew.
- **Rate limit:** các piece **không** xử lý 429 hay Retry-After (grep 429 và rate limit ra 0 kết quả trong mã). Chúng dựa vào SDK:
  - `@slack/web-api` có sẵn retry và xử lý rate limit.
  - `@notionhq/client` 2.x không tự retry (chưa đo).
  - gaxios có retry tuỳ cấu hình (chưa xác minh).
- **Phân trang:** thường được lộ ra thành **prop** cho người dùng, ví dụ Notion `start_cursor` nhận vào và `has_more`, `next_cursor` trả ra (`notion-query-database.ts:45-98`). Chỉ vài action tự lặp. 33 tệp trong ba piece có nhắc tới cursor hoặc pageToken.

---

## 5. OAuth — ai giữ client_id/secret

`AppConnectionType` (`core/piece-types/src/lib/app-connection.ts:1`) có ba loại OAuth:

1. **`OAUTH2`** (mã MIT, `server/api/src/app/app-connection/app-connection-service/oauth2/services/credentials-oauth2-service.ts`): người dùng hoặc người tự host **tự nhập** client_id/secret của OAuth app họ đăng ký. Server đổi code lấy token và refresh.
2. **`CLOUD_OAUTH2`** (`cloud-oauth2-service.ts:28,55`): claim và refresh qua `https://secrets.activepieces.com/{claim,refresh}`. **Activepieces giữ secret**, và màn đồng ý sẽ hiện tên app Activepieces. Đây là dịch vụ của họ, không phải thứ LTT có quyền dựa vào cho SaaS thương mại.
3. **`PLATFORM_OAUTH2`**: bản CE để `unimplementedService` (`oauth2/index.ts:30`). Bản thật nằm ở **ee** (`app/ee/oauth-apps/`): admin nền tảng khai một OAuth app dùng chung cho mọi người dùng.

**Refresh do server làm:**
- `app-connection-service.ts:502-510` gọi `needRefresh`, rồi `lockAndRefreshConnection` (có khoá), rồi trả giá trị cho engine sau khi đã **gỡ** `refresh_token` và `client_secret`.
- Engine không bao giờ thấy secret.
- `EXECUTE_REFRESH_TOKEN_AUTH` là hook để piece tự refresh các kiểu auth không chuẩn.

**⇒ LTT tự host:**
- **Phải tự đăng ký OAuth app** với Google (cần xác minh app và scope nhạy cảm của Sheets/Drive), Slack (một Slack app, bật Events API trỏ về webhook của LTT, lưu signing secret) và Notion (public integration).
- Phải tự làm: kho client secret, luồng authorize/callback, kho token mã hoá, refresh có khoá, và xử lý thu hồi.
- Riêng Slack APP_WEBHOOK còn cần một router sự kiện dùng chung: một endpoint nhận mọi sự kiện, dò `identifierValue` (team_id) để ra các flow đang lắng nghe. Phía Activepieces cấu hình qua `APP_WEBHOOK_SECRETS` (`server/api/src/app/helper/system/system-props.ts:16`).

---

## 6. Số lượng pieces

- **0.90.2:** `packages/pieces/community/` có **730 thư mục** (`ls | wc -l`), `packages/pieces/core/` có 27 (http, webhook, schedule, store, delay, approval, forms, subflows...).
- **0.91.1:** danh sách qua GitHub MCP có cùng cỡ, khoảng 730.
- `http` **không** nằm trong community mà ở `pieces/core/http`. Ngoài ra có `community/http-oauth2`.

---

## 7. Đánh giá ba phương án cho LTT (Python/Postgres, Windows)

### A — Port sang Python native
- **Chi phí:** cao và tuyến tính theo số piece. Ba piece mẫu có khoảng 170 action và 22 trigger. Mỗi action phải viết lại bằng SDK Python (google-api-python-client, slack_sdk, notion-client).
- **Được gì:** không cần Node; tích hợp thẳng vào `job_runner`, credit và sổ sách; cô lập như mọi job Python.
- **Rủi ro:** lệch hành vi so với bản gốc; không nhận bản sửa từ upstream (piece cập nhật hằng tuần); MIT cho phép nhưng phải ghi notice.
- **Hợp lý khi:** chỉ cần khoảng 5–15 connector quan trọng. Chọn "action tinh" của từng piece, không port 60+ action của Sheets.

### B — Worker Node.js chạy piece nguyên bản; LTT giữ state, retry, wait và billing
- **Hình dạng:**
  - `node-runner` là tiến trình dài hạn, **không dùng engine của Activepieces**. Chỉ phụ thuộc `@activepieces/pieces-framework` cùng các gói piece đã ghim version.
  - Giao tiếp stdin/stdout JSON-lines hoặc HTTP localhost.
  - Ba thao tác: `run_action`, `run_property` (dropdown động), `trigger_hook` (enable, disable, run, test, renew, handshake).
  - LTT (Python) truyền `auth` đã giải mã, `propsValue` và một snapshot `store` (hoặc cho runner gọi ngược API store của LTT). Runner trả `output` cùng các thao tác store, file hay waitpoint.
- **LTT phải tự làm:**
  - OAuth: app registration, callback, refresh có khoá, mã hoá.
  - Store (bảng Postgres theo flow/project).
  - `files.write` qua `platform_core/storage.py`.
  - Waitpoint và resume URL, ánh vào mô hình wait của LTT.
  - Lịch poll (APScheduler hoặc bảng job), webhook ingress, router APP_WEBHOOK, renew.
  - Timeout, giới hạn bộ nhớ, tính credit.
- **Chi phí:** vừa phải. Runner khoảng 500–1.000 dòng TS; phía Python làm connection, store và trigger khoảng 2–3 tuần. Đổi lại mở được mọi piece dạng SecretText hoặc CustomAuth gần như ngay.
- **Rủi ro:**
  - **Chuỗi cung ứng npm.** Mỗi piece kéo vài chục gói phụ thuộc; `pieces-framework` kéo cả `ai@6`. Giảm rủi ro bằng cách ghim version cùng lockfile, `--ignore-scripts` (Activepieces cũng làm vậy), mirror nội bộ và cài sẵn theo allowlist, không cài lúc chạy.
  - **Sandbox trên Windows.** Không có isolate. Cần tiến trình riêng cho mỗi job hoặc pool nhỏ, Job Object giới hạn RAM/CPU, tài khoản dịch vụ ít quyền, chặn SSRF bằng proxy hoặc tường lửa đi ra. Máy A là production nên cần trần `--max-old-space-size`.
  - **Trôi version.** `ContextVersion` và `minimumSupportedRelease` đổi theo nhịp phát hành, và các API deprecated (`run.pause`) bị gỡ theo lịch. Phải ghim bộ (framework, piece) và nâng cấp theo đợt kèm smoke test.
  - Hành vi của piece ngoài ba mẫu này chưa được kiểm.

### C — Sinh wrapper bán tự động
- **Cách làm:**
  - Chạy `EXTRACT_PIECE_METADATA`, hoặc đơn giản `require(piece).metadata()`, để lấy JSON schema của props, auth và danh sách action/trigger.
  - Sinh tự động "tool definition" phía LTT (form UI, kiểm tra input, bảng giá credit). Phần thực thi vẫn đi qua runner Node của phương án B.
- **Nhận định:** C không thay được B mà là **lớp đăng ký catalog nằm trên B**.
- **Nếu sinh cả mã Python** (tức A bằng LLM hoặc codegen) thì chất lượng không đảm bảo, vì logic `run` là TS tuỳ ý và không suy ra được từ metadata.
- **Chi phí:** thấp (1–2 tuần) khi đã có B. Rủi ro chính là mapping prop kiểu Dynamic, Dropdown hoặc File sang UI của LTT.

### Khuyến nghị
**B + C, bắt đầu hẹp:**
1. Runner Node ghim version, allowlist khoảng 10 piece.
2. Ưu tiên piece dùng SecretText/CustomAuth để né OAuth ở vòng một. Cả ba piece mẫu đều có CustomAuth thay thế: Sheets dùng service account, Slack dùng bot token, Notion dùng integration token.
3. Tiếp theo mới làm OAuth2 (`OAUTH2` tự đăng ký app).
4. APP_WEBHOOK của Slack để sau cùng, vì cần router sự kiện toàn cục.

Dành A cho vài connector lõi cần tối ưu credit hoặc độ tin cậy.
⛔ Không dùng `secrets.activepieces.com`. Không đọc hay chép `app/ee/**`.

**Chưa kiểm chứng:** chưa cài hay chạy thử piece nào; hành vi retry của `@notionhq/client` và `gaxios`; số piece chính xác ở 0.91.1.
