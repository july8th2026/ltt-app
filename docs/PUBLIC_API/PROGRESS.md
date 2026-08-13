# PUBLIC API — PROGRESS

Pack: `LTT_PUBLIC_API_CLAUDE_BUILD_PACK_V2` (v2.0)

**Chế độ chạy (chốt 2026-08-13, chủ sản phẩm ra lệnh):** tuần tự **LIÊN TỤC** —
xong một prompt mà Acceptance Gate PASS và `NEXT_PROMPT_ALLOWED=true` thì chạy
thẳng prompt kế tiếp, không dừng chờ xác nhận. Quy tắc đầy đủ ở
`COMMON_RULES.md` mục 8.1 của pack.

**Chỉ dừng khi:** (1) gate/test đỏ chưa sửa được thật; (2) cần một quyết định
sản phẩm; (3) cần quyền/khoá/tài nguyên ngoài repo; (4) bước kế tiếp là deploy
production hoặc chạm dữ liệu thật; (5) gặp rủi ro P0 ngoài phạm vi prompt đang
chạy. Dừng vì năm lý do này là **đúng quy trình**, không phải bỏ dở.

Mỗi prompt vẫn ghi HANDOFF đầy đủ vào file này **trước khi** sang prompt sau.

| # | Prompt | Trạng thái | Ngày |
|---|---|---|---|
| 01 | Baseline / Discovery / Architecture / App disposition | **PASS** | 2026-08-13 |
| 02 | API kernel / routing / config / feature flags | **PASS** | 2026-08-13 |
| 03 | Developer API key domain + migration | **PASS** | 2026-08-13 |
| 04 | API auth / scopes / tenant policy | **PASS** | 2026-08-13 |
| 05 | Public tool catalog / typed contracts / OpenAPI | **PASS** | 2026-08-13 |
| 06 | Quotes / jobs / credits / idempotency | **PASS** | 2026-08-13 |
| 07 | Upload / artifact / storage lifecycle | **PASS** | 2026-08-13 |
| 08 | Rate / quota / concurrency / capacity | **PASS** | 2026-08-13 |
| 09 | Webhook / outbox / signing / SSRF | **PASS** | 2026-08-13 |
| 10 | Usage / audit / reconciliation | **PASS** | 2026-08-13 |
| 11 | Wave 1 — canary ảnh/thumbnail | **PASS** | 2026-08-13 |
| 12 | Wave 2 — video/upscale/GPU | **PASS** | 2026-08-13 |
| 13 | Wave 3 — prompt/subtitle/shortclip | **PASS** | 2026-08-13 |
| 14 | Phủ 100% app còn lại (chat/agent/social/internal) | **PASS** | 2026-08-13 |
| 15 | Developer portal / OpenAPI docs / SDK | **PASS** | 2026-08-13 |
| 16 | Security / observability / performance hardening | **PASS** | 2026-08-13 |
| 17 | Final jobtest / load / recovery / release gate | **PASS** | 2026-08-13 |

**Pack hoàn tất 17/17.** Kết luận phát hành:
`READY_FOR_CONTROLLED_DEPLOY` — `RELEASE_READINESS_V1.md`. Chưa deploy.

---

## Prompt 01 — BASELINE, DISCOVERY, ARCHITECTURE LOCK, APP DISPOSITION

### Entry gate

- `docs/PUBLIC_API/PROGRESS.md` chưa tồn tại → Prompt 01 là prompt hợp lệ.
- Git: nhánh `master`, cây làm việc **đã bẩn sẵn từ phiên trước** (không phải do
  lượt này): 16 file `M` (`AGENTS.md`, `CLAUDE.md`, `docs/HO_SO_HE_THONG.md`,
  `docs/KE_HOACH_TRIEN_KHAI.md`, `docs/QUYET_DINH_NEN_TANG.md`,
  `ho_so_he_thong.txt`, 4 test, 6 tool) + `?? .gitattributes`. Delta này thuộc
  commit gần nhất `dc7f255` (hồ sơ hệ thống). **Không đụng vào.**
- Migration head: `b6c7d8e9f0a1` (`20260812_1500_project_upload_attachments`).
- Máy: `C:\LTTPlatform` **có tồn tại** (đây là máy chủ). Làm việc trên nguồn
  `D:\LTTSTUDIOSAPP`. **Không deploy, không chạm bản chạy.**

### Observed (đọc code/test thật, không suy diễn)

1. `registry.discover()` chạy thật: **14 app, 0 lỗi, 17 job_type, 21 ToolSpec**.
2. `job_submit.submit_with_credit()` = giá → submit → hold trong **một**
   transaction, caller commit. Bất biến "không tra được giá thì từ chối chạy"
   nằm ở `registry.credit_for()` (raise, không trả 0).
3. `credit.py` append-only; `pg_advisory_xact_lock` chống double-spend và tuần
   tự hóa settle/refund; `quyet_toan()` **cap thu ≤ hold** (Q84) và ghi variance.
4. **`dedupe_key` KHÔNG phải idempotency key**: `jobs.submit()` chỉ trả job cũ
   khi job còn `queued/running`; retry sau khi job `done` sẽ tạo job mới và hold
   lần hai. Chỉ `apps/taovideo/quotes.py` có quote ký + `intent` chống được.
5. `platform_core/api_keys.py` = **provider credential** (Fernet, giải mã được
   bằng `lay_credential`). Không được dùng cho customer key.
6. Không tồn tại `/api/v1` nào trong repo; hai chuỗi `api/v1` tìm thấy là
   base_url của provider ngoài.
7. `server/app.py:335` (Q88) bắt **mọi** path chứa `/api/` → sẽ nuốt `/api/v1`
   nếu kernel không đăng ký handler riêng. Có test chốt `test_176`.
8. `AccessControlMiddleware` ánh xạ path→app theo `route_prefix`; `/api/v1`
   không thuộc app nào nên **không** được phân quyền tự động → kernel phải tự
   kiểm và fail-closed.
9. `server/usage_rate_limit.py` khóa theo `request.session`, fallback
   `request.client.host`. Client API không có session, và sau Cloudflare Tunnel
   mọi peer là loopback → dùng nguyên trạng cho `/api/v1` là DoS toàn hệ thống.
10. `apps/chataistudio` giữ/quyết toán credit với `job_id` = **id tin nhắn**,
    không có dòng `jobs` → nằm ngoài bất biến job.
11. `apps/mediatools` (internal/runtime) có ToolSpec `video.social_import(url)`
    → SSRF nếu public. `apps/kichban` retired nhưng vẫn có ToolSpec
    `text.generate customer_visible=True` → đúng bẫy prompt yêu cầu kiểm.
12. `upload_sessions` đã có đủ staging → validate (size + magic) → `promote`
    sau hold (Q85) / `attach_to_project` (Q89) + sweeper + compensation.
13. Không có model organization; mọi ownership bám `User`.
14. Test mặc định chạy **không** PostgreSQL → advisory lock bị bỏ qua; chỉ
    `tests/test_73_dong_thoi_pg.py` dùng `LTT_TEST_DATABASE_URL`.

### Changed

Chỉ tạo tài liệu, **không đụng một dòng code/test/migration nào**:

- `docs/PUBLIC_API/ARCHITECTURE_V1.md`
- `docs/PUBLIC_API/DECISIONS_V1.md`
- `docs/PUBLIC_API/APP_DISPOSITION_V1.md`
- `docs/PUBLIC_API/TEST_STRATEGY_V1.md`
- `docs/PUBLIC_API/PROGRESS.md` (file này)

### Migrations / config

Không có. Head vẫn `b6c7d8e9f0a1`.

### Tests + baseline

| Phép đo | Kết quả |
|---|---|
| `python tools/gate.py --quick` (trước khi viết doc) | **PASS 9/9** |
| `python tools/gate.py --quick` (sau khi viết doc) | **PASS 9/9** — không xấu đi |
| Targeted core (10 file: registry/job/credit/api_keys/job_events/upload/api-error/r2) | **139 passed**, 134,5 s |
| Tổng test thu thập | 2.696 |
| Latency in-process p50/p95 | `/health/ready` 2,47/2,79 ms · `/login` 3,17/3,83 ms · `/` 6,33/6,75 ms |

Không đo được DB pool/query baseline: máy dev không cấu hình
`LTT_DATABASE_URL`. Ghi nhận là **thiếu**, không đoán số.

### Risks

- **R1 (cao):** Prompt 02 buộc phải sửa `server/app.py` + tạo package trong
  `platform_core/` — vượt luật `AGENTS.md` mục 2.3 dành cho *app*. Giảm rủi ro
  bằng cách thêm dòng **Q92** vào `docs/QUYET_DINH_NEN_TANG.md` theo giao thức
  mục 6 **trước** khi viết kernel, và mount sau cờ `LTT_PUBLIC_API`.
- **R2 (cao):** double-charge qua retry — `dedupe_key` không phủ. Phải có bảng
  idempotency + test PostgreSQL (Prompt 06).
- **R3 (cao):** rate-limit hiện tại nếu áp cho API sẽ khóa nhầm toàn hệ thống.
- **R4 (trung bình):** handler lỗi Q88 nuốt `/api/v1` → mất hợp đồng RFC 9457.
- **R5 (trung bình):** phân quyền app mặc định MỞ (Q25) trái với fail-closed của
  Public API; kernel phải đảo mặc định cho bề mặt của mình.
- **R6 (trung bình):** rate-limit in-memory chỉ đúng với một tiến trình web
  (ADR-005); phải quyết ở Prompt 08 kèm số đo.
- **R7 (thấp/đã chặn):** SSRF của `video.social_import` — đã đặt INTERNAL_ONLY.

### Deferred (cố ý, có nơi xử lý)

| Việc | Hoãn tới |
|---|---|
| Thêm dòng quyết định Q92 vào nguồn chân lý | Prompt 02 (khi thật sự sửa nền tảng) |
| Developer key schema + verifier + benchmark | Prompt 03 |
| Bảng idempotency + quote nền tảng | Prompt 06 |
| Artifact/`/api/v1/artifacts` owner-scoped | Prompt 07 |
| Quyết định bộ đếm rate-limit (RAM vs PostgreSQL) | Prompt 08 |
| Webhook/outbox (chưa tồn tại) | Prompt 09 |
| Benchmark harness control-plane có commit hay không | Prompt 08 |
| Team/organization billing | ADR tương lai, ngoài pack |
| Public hóa chat (`chataistudio`) — thiếu Job + rủi ro ToS sidecar | ngoài pack, cần quyết định sản phẩm |

### Rollback của Prompt 01

Xóa thư mục `docs/PUBLIC_API/`. Không có thay đổi code, config, schema hay dữ
liệu nào để lùi.

### Acceptance Gate — đối chiếu từng mục

| Yêu cầu | Kết quả |
|---|---|
| Có baseline lưu lại | ✅ `TEST_STRATEGY_V1.md` mục 1 + bảng trên |
| Disposition cho 100% app/tool | ✅ 14/14 app, 21/21 ToolSpec, 17/17 job_type |
| Không app internal/retired nào bị auto-expose | ✅ demo/qualitylab/mediatools INTERNAL_ONLY; kichban RETIRED_NO_EXPOSE; socialbot INTERNAL_ONLY; và catalog fail-closed theo PA-6 |
| Kiến trúc không tạo engine/ledger/provider/storage song song | ✅ PA-7 + ARCHITECTURE mục 1–2 |
| Quick gate không xấu đi | ✅ PASS 9/9 trước và sau |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 02 bên dưới)
Prompt kế tiếp lúc đó: `prompts/02_PUBLIC_API_KERNEL_ROUTING_CONFIG_FEATURE_FLAGS.txt`
(điều kiện tiên quyết: thêm dòng Q92 trước khi sửa nền tảng).

---

## Prompt 02 — PUBLIC API KERNEL: ROUTING, CONFIG, FEATURE FLAGS, REQUEST CONTEXT

### Entry gate

- Prompt 01 PASS, `NEXT_PROMPT_ALLOWED=true` ✅
- Migration head vào/ra đều là `b6c7d8e9f0a1` — prompt này **không** có migration.
- Git delta trước khi bắt đầu: 16 file `M` của phiên trước + `?? .gitattributes`
  + `?? docs/PUBLIC_API/` (Prompt 01). Không đụng vào phần của phiên trước.
- Điều kiện tiên quyết đã làm trước khi sửa code: thêm **Q92** vào
  `docs/QUYET_DINH_NEN_TANG.md` (thêm dòng mới, không sửa đè, kèm lý do).

### Observed (phát hiện trong lúc làm, khác giả định của prompt)

1. **Starlette 1.3 / FastAPI 0.141 không làm phẳng `include_router`.** Mỗi lần
   include để lại một `_IncludedRouter` không có `.path`, nên "liệt kê route V1"
   theo `app.routes` trả về rỗng (repo đã dính chuyện này trước:
   `tests/test_152`, `tests/test_51`). → Kernel chuyển sang **mounted
   sub-application**; nhờ đó inventory, OpenAPI riêng và error boundary riêng
   đều là hệ quả tự nhiên thay vì phải tự dựng.
2. **Kill switch không được là dependency của router.** Bản đầu đặt read-only +
   trần body làm `dependencies=[...]` trên router; test cho thấy route thêm vào
   ngoài router đó **không** bị chặn. Một công tắc khẩn cấp mà có thể quên gắn
   thì không phải công tắc → chuyển thành middleware của sub-app, phủ mọi route
   của bề mặt, kể cả route các prompt sau thêm.
3. **FastAPI đăng docstring của handler vào OpenAPI.** Docstring ở đây giải
   thích thiết kế nội bộ (tên route khác, quy tắc nội bộ) → lộ ra spec công
   khai. Đã ép `description=` tường minh cho mọi route; test chốt rằng spec
   không chứa `/login`, `/admin`, `/health/ready`, tên app.
4. **`test_no_app_slug_is_hardcoded_in_the_platform` bắt đúng thứ nó sinh ra để
   bắt**: một ví dụ tên tool trong docstring `platform_core/public_api/config.py`
   có chứa tên một app. Đã thay bằng placeholder `<domain>.<action>`.
5. **`UsageRateLimitMiddleware` vẫn áp cho `/api/v1`** và khóa theo
   `request.session` → rơi về `ip:` (sau Tunnel là loopback), và trả JSON
   `{"ok": false, …}` chứ không phải problem+json. Chưa sửa: chưa có write nào
   tính tiền, và rate-limit theo principal là việc của Prompt 08. Ghi ở Risks.

### Changed

Mới:

- `platform_core/public_api/{__init__,config,errors,pagination}.py` — cờ/kill
  switch, hợp đồng lỗi RFC 9457, pagination có trần cứng. Không import
  FastAPI/Starlette, không biết tên app nào.
- `server/api/{__init__,guard,deps,errors,context,inventory}.py` — sub-app
  `/api/v1`, middleware kill switch + trần body, principal placeholder deny-all,
  exception handler riêng, request id + client IP tin cậy, inventory route.
- `tests/test_178_public_api_kernel.py` — 26 test.
- `docs/PUBLIC_API/KERNEL_V1.md` — tên biến môi trường, hợp đồng lỗi, vì sao
  sub-app, cách thêm route mới.

Sửa (nhỏ, có chủ ý):

- `docs/QUYET_DINH_NEN_TANG.md` — thêm dòng **Q92** (và cập nhật "đến Q92").
- `server/app.py` — ba chỗ: (a) mount Public API sau cờ; (b) một nhánh trong
  handler `StarletteHTTPException` để `/api/v1` trả problem+json **kể cả khi bề
  mặt đang tắt**; (c) `_json_error_detail` nay gọi `scrub_detail` dùng chung
  (giữ nguyên tên và hành vi — `tests/test_176` vẫn xanh).
- `ho_so_he_thong.txt` — sinh lại bằng `python tools/build_system_profile.py`
  (bắt buộc, vì gate có bước `--check` và có file nguồn mới).

### Migrations / config

Không có migration. Biến môi trường mới (mặc định an toàn, tài liệu ở
`KERNEL_V1.md`): `LTT_PUBLIC_API=0`, `LTT_PUBLIC_API_READ_ONLY=0`,
`LTT_PUBLIC_API_TOOLS=` (rỗng), `LTT_PUBLIC_API_MAX_BODY_BYTES=262144`,
`LTT_PUBLIC_API_TRUSTED_PROXIES=127.0.0.1,::1`.

**Production không cần làm gì**: không đặt `LTT_PUBLIC_API` thì router không
được mount và bề mặt route đúng như trước.

### Tests

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q tests/test_178_public_api_kernel.py` | **26 passed** |
| `python -m pytest -q --ignore=tmp --ignore=test-results` (lượt 1) | 2.714 passed, **1 failed** (`test_no_app_slug_is_hardcoded_in_the_platform` — Observed #4), 8 skipped, 29:22 |
| `python -m pytest -q` 5 file liên quan sau khi sửa | **109 passed** |
| `python tools\gate.py` (FULL, sau khi sửa) | **PASS 10/10** — pytest 1.781,8 s, 3 frontend, 6 scanner |

Latency (cùng harness in-process với baseline Prompt 01, 60 mẫu):

| Route | Baseline P01 p50/p95 | API tắt p50/p95 | API bật p50/p95 |
|---|---|---|---|
| `/health/ready` | 2,47 / 2,79 ms | 2,61 / 2,98 ms | 2,33 / 2,80 ms |
| `/login` | 3,17 / 3,83 ms | 3,12 / 4,06 ms | 3,08 / 3,38 ms |
| `/` | 6,33 / 6,75 ms | 6,23 / 6,64 ms | 6,26 / 6,79 ms |
| `/api/v1/health` | — | — | 3,22 / 3,85 ms |
| `/api/v1/capabilities` | — | — | 3,21 / 3,67 ms |

Chênh lệch nằm trong nhiễu đo; không có regression cho đường UI ở cả hai trạng
thái cờ.

### Review

- **Tenant isolation:** chưa có resource nào; principal deny-all, có test chốt
  rằng cookie/`request.session` không bao giờ được đọc làm danh tính.
- **Credit invariants:** không đụng — kernel chưa có đường tạo job/hold.
- **Idempotency:** chưa áp dụng (Prompt 06).
- **Secret/log redaction:** 500 luôn trả câu cố định; có test bơm một chuỗi
  giống secret + đường dẫn `C:\LTTPlatform\secrets\...` vào exception rồi assert
  nó không xuất hiện trong response, cũng không có traceback.
- **Backward compatibility:** full gate xanh; Q88 giữ nguyên (test riêng so
  sánh `/sample/api/fail` vẫn là `application/json` chứ không phải problem+json);
  route UI so sánh từng cặp status/content-type ở hai trạng thái cờ.
- **Performance:** bảng trên.
- **Migration rollback:** không có migration.

### Risks

- **R3 (từ Prompt 01, vẫn mở):** `UsageRateLimitMiddleware` áp lên `/api/v1` với
  khóa sai principal và trả sai hợp đồng lỗi. Không nguy hiểm hôm nay (chưa có
  write tính tiền) nhưng **phải** xử ở Prompt 08 trước khi mở tool thật.
- **R8 (mới):** `server/auth/session.py:client_ip()` vẫn tin `CF-Connecting-IP`
  vô điều kiện. Kernel dùng bản chặt hơn (`server/api/context.py`), nhưng hai
  quy tắc IP cùng tồn tại trong repo là mầm nhầm lẫn. Đề xuất hợp nhất ở Prompt
  08 hoặc 16, kèm test cho đường UI.
- **R9 (mới, thấp):** cấu hình đọc một lần lúc `create_app` → đổi cờ phải khởi
  động lại dịch vụ web. Cố ý (tránh hai request chạy hai luật), nhưng phải ghi
  vào runbook vận hành ở Prompt 16.

### Deferred

| Việc | Hoãn tới |
|---|---|
| Resolver principal thật (`set_principal_resolver`) | Prompt 03/04 |
| `capabilities` trả danh sách thật | Prompt 05 |
| Rate-limit/quota theo principal + hợp đồng 429 | Prompt 08 |
| Trang docs/portal cho spec (`docs_url` đang tắt) | Prompt 15 |
| Hợp nhất helper client IP của đường UI | Prompt 08/16 |
| Cập nhật `docs/KE_HOACH_TRIEN_KHAI.md` + `docs/NHAT_KY.md` | cuối pack hoặc khi chủ sản phẩm yêu cầu — chưa tự đặt số hạng mục mới |

### Rollback

Ba mức, từ nhẹ tới nặng:

1. **Vận hành:** `LTT_PUBLIC_API_READ_ONLY=1` → dừng mọi write của API, UI và
   worker không đổi.
2. **Tắt hẳn:** bỏ `LTT_PUBLIC_API` (hoặc `=0`) → không mount gì; hai nhánh còn
   lại trong `server/app.py` chỉ ảnh hưởng path `/api/v1` vốn không tồn tại.
3. **Gỡ code:** xoá `platform_core/public_api/`, `server/api/`,
   `tests/test_178_*`, hoàn nguyên 3 chỗ sửa trong `server/app.py`, sinh lại hồ
   sơ hệ thống. Không có schema/dữ liệu nào phải lùi.

### Acceptance Gate — đối chiếu từng mục

| Yêu cầu | Kết quả |
|---|---|
| `/api/v1` boot được nhưng chưa cho chargeable operation | ✅ chỉ có `health`/`capabilities`/`openapi.json`; không route nào chạm credit/job |
| Kill switch tắt được toàn bộ write của API mà không ảnh hưởng UI | ✅ middleware phủ cả bề mặt; test: write → 503 `read_only`, read → 200, `/login` → 200 HTML |
| Không lộ stack trace/config/secret | ✅ test bơm secret + path vào exception; 500 chỉ trả câu cố định, `capabilities` không chứa provider/model/backend |
| OpenAPI route inventory test PASS | ✅ so khớp hai chiều mount ↔ inventory ↔ spec |
| UI/route hiện có không đổi | ✅ full gate PASS 10/10 + so sánh từng route ở hai trạng thái cờ |
| Config qua env, không hardcode host | ✅ 5 biến, tài liệu ở `KERNEL_V1.md`; không có tên host trong code |
| Trusted proxy helper không tin header tùy tiện | ✅ chỉ tin `CF-Connecting-IP` từ peer tin cậy, không đọc `X-Forwarded-For` |
| Không tạo auth/key ngoài placeholder | ✅ `Principal` + `set_principal_resolver`, mặc định deny-all 401 |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 03 bên dưới)

---

## Prompt 03 — DEVELOPER API KEY DOMAIN, MIGRATION, LIFECYCLE

### Entry gate

- Prompt 02 PASS, `NEXT_PROMPT_ALLOWED=true` ✅ (chạy liên tục theo quy tắc mới).
- Migration head vào: `b6c7d8e9f0a1`. Head ra: **`a7b8c9d0e1f2`**.
- Chưa commit; cây làm việc mang delta của Prompt 01–02 + phiên trước.

### Observed

1. **Secret base64url chứa dấu `_`.** Parser đầu tiên tách token bằng
   `split("_")` → token hợp lệ bị từ chối ngẫu nhiên (~1/3 số lần). Test bắt
   ngay ở lượt chạy đầu; đã sửa sang `split("_", 3)` + kiểm bảng chữ cái và
   thêm regression test ép secret chứa `_`. Đây là kiểu lỗi tệ nhất cho một
   credential: *lúc xanh lúc đỏ*.
2. **Trùng revision id trong Alembic.** Id chọn ban đầu (`c7d8e9f0a1b2`) đã tồn
   tại ở `20260731_1400_index_claim_job.py` — file đó khai bằng cú pháp khác
   (`revision: str = '...'`) nên grep theo `^revision = ` không thấy. Alembic
   báo "Cycle is detected"; `tests/test_63` bắt được. Đổi sang `a7b8c9d0e1f2`.
   **Bài học cho các prompt sau:** kiểm id bằng `grep -rn "<id>" alembic/versions`
   chứ không grep theo tiền tố dòng.
3. PostgreSQL đang chạy trên máy này (`postgresql-x64-17`), nhưng đó là **cụm
   phục vụ production**. Không tự tạo database test trên đó; test PostgreSQL
   viết sẵn và tự bỏ qua khi thiếu `LTT_TEST_DATABASE_URL`.

### Changed

Mới:
- `platform_core/public_api/tables.py` — model `DeveloperApiKey`.
- `platform_core/public_api/keys.py` — issue/verify/list/get_owned/revoke/
  set_enabled/rotate/touch_last_used + xử lý pepper.
- `platform_core/public_api/scopes.py` — từ vựng scope + validate.
- `alembic/versions/20260813_1000_developer_api_keys.py` (`a7b8c9d0e1f2`).
- `tools/bench_public_api_key.py` — benchmark đường xác thực.
- `tests/test_179_developer_api_key.py` — 35 test + 2 test PostgreSQL (skip).
- `docs/PUBLIC_API/DEVELOPER_KEYS_V1.md`.

Sửa:
- `platform_core/models.py` — thêm **một** import để Alembic thấy bảng mới.
- `ho_so_he_thong.txt` — sinh lại.

### Migrations / config

- Head: `b6c7d8e9f0a1` → **`a7b8c9d0e1f2`**. `upgrade → downgrade base →
  upgrade` xanh (`tests/test_63_lop_csdl.py`, SQLite).
- Env mới: **`LTT_API_KEY_PEPPER`** (bắt buộc ≥32 ký tự, **không có giá trị mặc
  định** — thiếu là không cấp/không xác minh được khoá nào),
  `LTT_API_KEY_PEPPER_VERSION` (mặc định `1`), `LTT_API_KEY_PEPPER_V<n>` (pepper
  đã nghỉ hưu, giữ để xoay). Chi tiết ở `DEVELOPER_KEYS_V1.md` mục 4.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_179_developer_api_key.py` | **35 passed, 2 skipped** (2 test PostgreSQL) |
| `pytest` 9 file lõi (registry, khoá logic, job, credit, web jobs, api_keys, hợp đồng lỗi, kernel, hồ sơ) | **163 passed** |
| `pytest tests/test_63_lop_csdl.py` | **17 passed** (vòng migration tiến–lùi–tiến) |
| `python tools\gate.py --quick` | **PASS 9/9** |
| `python tools\bench_public_api_key.py --db --sqlite` | HMAC p50 **2,9 µs** / p95 3,1 µs; `verify()` đủ đường p50 **258,6 µs** / p95 531,9 µs |

### Review

- **Tenant isolation:** `get_owned()` đặt owner trong `WHERE` (không fetch rồi
  mới kiểm); test cross-user cho list/get/verify.
- **Credit invariants:** không chạm.
- **Idempotency:** chưa áp dụng (Prompt 06).
- **Secret/log redaction:** không có plaintext ở CSDL (test đọc thẳng dòng SQL
  và assert secret không xuất hiện); `__repr__` chỉ in `key_id`; `parse_token`
  không log gì; pepper không nằm trong bảng.
- **Backward compatibility:** `api_keys` provider không đổi (test cấp key +
  `lay_credential` vẫn trả đúng giá trị); thêm bảng mới, không sửa bảng cũ.
- **Performance:** bảng benchmark ở trên; có test chặn KDF đắt lọt vào đường nóng.
- **Migration rollback:** `downgrade()` xoá bảng + 3 index; đã chạy thật.

### Risks

- **R10 (mới, trung bình):** `LTT_API_KEY_PEPPER` là một bí mật **mới phải sao
  lưu**. Mất nó = mọi developer key ngừng hoạt động (fail-closed). Phải thêm vào
  quy trình backup `secrets\app.env` của Q28 khi triển khai — ghi vào runbook ở
  Prompt 16.
- **R11 (mới, thấp):** `verify()` hiện làm một truy vấn/`request`. Ở tải cao có
  thể cần cache ngắn hạn theo `key_id`, nhưng **chưa đo được là cần** → không
  làm (COMMON_RULES §6).

### Deferred

| Việc | Hoãn tới |
|---|---|
| Cắm resolver vào `server/api/deps.set_principal_resolver` | Prompt 04 |
| Route/portal tạo–thu hồi khoá | Prompt 15 |
| Chạy 2 test PostgreSQL (`UNIQUE`, FK RESTRICT) | cần `LTT_TEST_DATABASE_URL` trỏ database test riêng — **việc của chủ sản phẩm**, không tự tạo DB trên cụm production |
| Đưa `LTT_API_KEY_PEPPER` vào backup/runbook | Prompt 16 |

### Rollback

`alembic downgrade b6c7d8e9f0a1` → xoá bảng; gỡ 6 file mới + 1 dòng import
trong `platform_core/models.py`; sinh lại hồ sơ. Không có dữ liệu nào phải cứu
(bảng mới, chưa ai dùng).

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Public credential không dùng `platform_core.api_keys.lay_credential` | ✅ có test quét mã nguồn chặn cả `secretbox` lẫn import chéo |
| Đường verify có benchmark, không mở DoS rõ ràng | ✅ 2,9 µs HMAC / 258,6 µs đủ đường + test chặn <10 ms |
| CSDL/log/fixture không giữ plaintext | ✅ test đọc thẳng dòng SQL; plaintext chỉ là giá trị trả về của `issue()` |
| Test provider key PASS | ✅ `test_75_api_keys.py` + test round-trip trong file mới |
| Đủ trường tối thiểu theo prompt | ✅ id, owner, name, key_id, verifier_digest, pepper_version, scopes, allowed_tools, enabled, created/expires/revoked/rotated/last_used |
| Không có field `environment`/sandbox | ✅ không thêm |
| `last_used_at` không ghi mỗi request | ✅ bucket 5 phút, có test |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 04 bên dưới)

---

## Prompt 04 — AUTH, SCOPES, TOOL POLICY, OBJECT AUTHORIZATION

### Entry gate

- Prompt 03 PASS ✅; head migration không đổi (`a7b8c9d0e1f2`), prompt này không
  có migration.

### Observed

1. **Từ vựng scope của Prompt 03 khác baseline của Prompt 04.** Prompt 03 tôi
   đặt `jobs:write`; Prompt 04 yêu cầu `jobs:create` / `jobs:read` /
   `jobs:cancel` + `credits:read` + `webhooks:manage`. Theo START_HERE mục 7,
   ghi Observed và theo bản chi tiết hơn: đã đổi từ vựng, cập nhật test của
   Prompt 03 (chưa có khoá nào được cấp ở đâu nên không có dữ liệu phải di trú).
2. **Hai test của Prompt 02 phải đổi ngữ nghĩa (có chủ ý, không phải sửa cho
   xanh):** resolver nay nhận `(request, db)` thay vì `(request)`, và ứng dụng
   *có* cài resolver thật khi boot. Tính chất được kiểm vẫn nguyên: không có
   resolver ⇒ deny-all 401, và cookie/`session` không bao giờ là danh tính.
3. Không có route nào tiêu tiền để gắn scope vào, nên cổng scope được kiểm bằng
   route tạm dựng **trong test** trên chính sub-app — không đưa route giả vào
   mã sản xuất.

### Changed

Mới:
- `platform_core/public_api/principal.py` — `Principal` + `ensure_scope`,
  `ensure_any_scope`, `ensure_tool_allowed`, `ensure_owner` (framework-free).
- `server/api/auth.py` — resolver CSDL, dependency `require_principal` /
  `require_scope(...)` / `optional_principal`, audit từ chối đã che bí mật.
- `tests/test_180_public_api_auth.py` — 19 test (ma trận bảo mật).
- `docs/PUBLIC_API/SECURITY_MATRIX_V1.md`.

Sửa:
- `platform_core/public_api/scopes.py` — từ vựng baseline + `SPENDING_SCOPES`.
- `server/api/deps.py` — resolver nhận `(request, db)`; `Principal` chuyển về
  domain và re-export.
- `server/api/__init__.py` — cài resolver khi dựng sub-app; thêm route
  **`GET /api/v1/me`** (route xác thực đầu tiên).
- `server/api/inventory.py` — khai `/api/v1/me`.
- `tests/test_178`, `tests/test_179` — cập nhật theo Observed #1, #2.
- `ho_so_he_thong.txt` — sinh lại.

### Migrations / config

Không có migration, không có biến môi trường mới.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_180_public_api_auth.py` | **19 passed** |
| `pytest` test_178 + test_179 + test_180 | **80 passed, 2 skipped** |
| `pytest` UI/session (105, 69, 107, 176) | **19 passed** |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Tenant isolation:** `ensure_owner` trả 404 giống hệt nhau cho "của người
  khác" và "không tồn tại"; `user_id` chỉ đến từ credential.
- **Credit invariants:** test dựng một route tiêu tiền giả, gọi bằng khoá thiếu
  scope → **0 bút toán** trong `credit_entries`.
- **Idempotency:** chưa (Prompt 06).
- **Secret/log redaction:** test bơm token thật + token sai vào log, assert cả
  token lẫn phần secret không xuất hiện; chỉ `key_id` công khai được ghi.
- **Backward compatibility:** UI/session regression xanh; `/api/v1` vẫn tắt mặc
  định.
- **Performance:** thêm đúng một truy vấn khoá theo index cho mỗi request có
  xác thực; `last_used_at` vẫn bucket 5 phút.
- **Migration rollback:** không có.

### Risks

- **R12 (mới, thấp):** `optional_principal` nuốt `ApiError` để trả `None` cho
  route công khai. Đúng cho catalog ẩn danh, nhưng nếu một route trả phí lỡ dùng
  nó thì mất xác thực. Prompt 05/06 chỉ được dùng nó cho route đọc công khai;
  ghi lại để review sau kiểm.
- **R3 (vẫn mở):** rate-limit theo principal — Prompt 08.

### Deferred

| Việc | Hoãn tới |
|---|---|
| Gắn `require_scope` vào route thật (tools/jobs/uploads/...) | Prompt 05–10 |
| Kiểm mass-assignment trên body thật | Prompt 06 |
| SSRF | Prompt 09 |

### Rollback

Gỡ `server/api/auth.py`, `principal.py`, route `/me` + khai báo inventory, trả
`deps.py` về placeholder. Không có schema/dữ liệu.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Đổi UUID tenant khác không đọc/sửa được | ✅ `ensure_owner` + test; `user_id` không nhận từ request |
| Thiếu scope ⇒ không có credit mutation/job nào | ✅ test đếm bút toán = 0 |
| `Authorization` thô không có trong log | ✅ test caplog |
| Session auth/UI regression PASS | ✅ 19 test UI/session xanh |
| Bearer dependency cho `/api/v1` | ✅ `require_principal`, route `/me` |
| Scope baseline đầy đủ | ✅ 9 scope theo prompt |
| Một mô hình quyền tool nhất quán | ✅ `allowed_tools` (+ test chặn scope dạng `tool:*`) |
| Guard object-level dùng chung | ✅ `ensure_owner` cho job/upload/artifact/webhook/usage sau này |
| Chính sách 403/404 nhất quán, có test | ✅ mục 1 của `SECURITY_MATRIX_V1.md` |
| Không CSRF cho bearer | ✅ có lý do ghi rõ; portal vẫn CSRF |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 05 bên dưới)

---

## Prompt 05 — PUBLIC TOOL CATALOG, TYPED CONTRACTS, OPENAPI

### Entry gate

- Prompt 04 PASS ✅; head migration không đổi (`a7b8c9d0e1f2`).

### Observed

1. **`params_schema` nội bộ không thể publish nguyên trạng.** Đọc thật 21
   ToolSpec: `model_ref` mang **tên provider và id model thật**
   (`{"type": "model_ref", "category": "image", "providers": ["gemini"]}`), còn
   `enum` nhiều chỗ lấy giá trị từ `prompts/<tên nội bộ>`. Publish thẳng là lộ
   nhà cung cấp và thư viện prompt. → phải có **phép chiếu** và alias.
2. **Lại vướng `_IncludedRouter`.** Gắn catalog bằng `include_router` vào sub-app
   làm route inventory không thấy chúng — đúng lỗ hổng mà inventory sinh ra để
   chặn. Chuyển sang đăng ký route **thẳng** lên sub-app.
3. **Bánh cóc i18n bắt 10 thông điệp lỗi tiếng Việt mới** trong `registry.py`
   (33 → 43 chuỗi chưa bọc). Đã bọc `_t()` như phần còn lại của file.
4. `test_no_app_slug_is_hardcoded_in_the_platform` lại bắt một ví dụ tên tool
   trong comment `registry.py` — đổi sang `<domain>.<action>`.

### Changed

Mới:
- `platform_core/public_api/catalog.py` — ba cổng expose + phép chiếu hợp đồng
  công khai + `require_tool`/`visible_to`.
- `server/api/tools.py` — `GET /api/v1/tools`, `GET /api/v1/tools/{tool_name}`.
- `tests/test_181_public_tool_catalog.py` — 23 test.
- `tests/golden/public_api_catalog_v1.json` — snapshot hợp đồng (hiện `{"tools": []}`).

Sửa:
- `platform_core/registry.py` — thêm **hai field additive** cho `ToolSpec`:
  `api_exposed=False` và `api_contract={}`, cùng `_validate_api_contract()`
  fail-closed. App cũ không khai gì vẫn chạy nguyên.
- `server/api/inventory.py` — khai 2 route mới + `capability_areas()`.
- `server/api/__init__.py` — gắn route catalog, `/capabilities` nay trả
  `["tools"]` (feature area của **phiên bản API**, không phải danh sách tool của
  deployment — danh sách đó nằm sau khoá).
- `tests/test_178` — cập nhật kỳ vọng `capabilities`.
- `ho_so_he_thong.txt` — sinh lại.

### Migrations / config

Không có migration. Không có biến môi trường mới (`LTT_PUBLIC_API_TOOLS` đã có
từ Prompt 02, nay là cổng thứ ba của catalog).

### Ba cổng expose (fail-closed, độc lập)

1. **Disposition của app** — `lifecycle ∈ {released, development}` và
   `surface == customer` và `enabled` và nạp không lỗi. retired/internal/
   maintenance/admin/runtime **không bao giờ** public, dù tool khai gì.
2. **Khai báo của tool** — `api_exposed=True` + `api_contract` đủ (registry từ
   chối nạp nếu thiếu alias model hoặc thiếu giá trị enum công khai).
3. **Công tắc operator** — `LTT_PUBLIC_API_TOOLS`.

Sau đó `allowed_tools` của khoá thu hẹp thêm lần nữa.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_181_public_tool_catalog.py` | **23 passed** |
| `pytest` test_178 + test_181 | **49 passed** |
| `pytest` test_178 + 180 + 60 + 97 (agent tools) | **90 passed** sau khi sửa 2 lỗi ở Observed |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Tenant isolation:** catalog lọc theo `allowed_tools` của principal; tool
  không publish → 404, tool publish nhưng khoá không được phép → 403.
- **Credit invariants:** chưa có đường gọi tool (Prompt 06).
- **Secret/log redaction:** test assert hợp đồng công khai **không** chứa
  `gemini`, id model thật, `prompts/...`, `app_slug`, `job_type`, `model_ref`.
- **Backward compatibility:** hai field mới có default; 21 ToolSpec hiện có
  không đổi một dòng nào; `customer_visible` giữ nguyên nghĩa cũ.
- **Contract drift:** hai test chốt — (a) **không app thật nào** đang
  `api_exposed`, (b) catalog live phải khớp `tests/golden/public_api_catalog_v1.json`.
  Wave 11–13 mở từng tool và cập nhật golden trong cùng thay đổi.
- **Migration rollback:** không có.

### Risks

- **R13 (mới, thấp):** `additionalProperties: false` trong input schema mới chỉ
  là **mô tả**; việc từ chối field lạ phải được thực thi ở đường submit (Prompt
  06). Nếu quên, hợp đồng nói một đằng và server làm một nẻo.
- **R14 (mới, thấp):** phép chiếu enum chỉ publish giá trị app tự khai; nếu app
  đổi danh sách prompt nội bộ mà quên cập nhật `api_contract.enums` thì hợp đồng
  công khai lệch. Wave prompts phải kiểm khi mở từng tool.

### Deferred

| Việc | Hoãn tới |
|---|---|
| Thực thi `additionalProperties:false` khi submit | Prompt 06 |
| Bật tool thật + cập nhật golden | Prompt 11–13 |
| Deprecation header (`Sunset`) khi có tool deprecated | Prompt 15/16 |

### Rollback

Gỡ `catalog.py`, `tools.py`, 2 route trong inventory, 2 field trong `ToolSpec`
(không app nào dùng), golden + test. Không có schema/dữ liệu.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| `customer_visible=True` không tự làm tool public | ✅ test riêng cho đúng cái bẫy này |
| Internal/retired/maintenance không xuất hiện nếu chưa ADR | ✅ test cho cả 3 lifecycle + 2 surface |
| OpenAPI parse được | ✅ test đọc `/api/v1/openapi.json`, có `/tools` và `/tools/{tool_name}` |
| Contract drift CI test PASS | ✅ golden snapshot + test "chưa app nào expose" |
| Tool thiếu hợp đồng typed → không expose | ✅ registry **từ chối nạp** (7 trường hợp có test) |
| Alias công khai không lộ provider/model thật | ✅ test quét chuỗi |
| Chính sách unknown field rõ | ✅ `additionalProperties: false` + ghi rõ sẽ thực thi ở Prompt 06 |
| Không sửa hàng loạt manifest khi chưa audit | ✅ **không manifest nào bị sửa** |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 06 bên dưới)

---

## Prompt 06 — QUOTES, JOBS, CREDIT, IDEMPOTENCY, TRANSACTIONALITY

### Entry gate

- Prompt 05 PASS ✅. Head vào `a7b8c9d0e1f2` → **ra `b8c9d0e1f2a3`**.

### Observed

1. **Không cần outbox.** Prompt lo "queue signal ngoài DB transaction", nhưng
   Q26 đã chốt hàng đợi **chính là bảng `jobs`**: hold + job + bản ghi
   idempotency commit **cùng một transaction**, không có tín hiệu nào ra ngoài
   CSDL. Nên trạng thái "đã giữ credit mà job biến mất" không tồn tại theo cấu
   trúc, không phải theo lời hứa. Có test bơm lỗi giữa hold và commit để chứng
   minh.
2. **`Idempotency-Key` phải là bắt buộc, không phải tuỳ chọn.** Nếu tuỳ chọn thì
   đường an toàn là đường client phải nhớ, còn mặc định là đường nguy hiểm.
3. **Sub-app không thấy `server_settings` của app cha** → khoá ký quote rỗng và
   `/quotes` trả 400 "chưa cấu hình". Đã truyền secret vào `state` của sub-app
   lúc mount (cố ý **không** để trong `PublicApiConfig` để một `repr` cấu hình
   không in ra bí mật).
4. **TTL đọc lúc gọi, không bind vào default.** `max_age=QUOTE_TTL_S` làm giá
   trị đóng băng lúc import — operator siết cửa sổ mà không có tác dụng gì.
5. **Full gate bắt một thứ không test nào khác bắt:** `test_155` yêu cầu **mọi
   ràng buộc UNIQUE mới phải nằm trong kịch bản diễn tập khôi phục**
   (`tools/restore_drill_schema.py`). Mất `uq_public_api_idempotency` sau một
   lần restore = mất cơ chế chống double-charge, im lặng. Đã bổ sung.

### Changed

Mới: `platform_core/public_api/{idempotency,quotes,invocation}.py`,
`server/api/jobs.py`, `alembic/versions/20260813_1400_public_api_idempotency.py`
(`b8c9d0e1f2a3`), `tests/test_182_public_api_jobs.py` (23 test).

Sửa: `platform_core/public_api/tables.py` (thêm `ApiIdempotencyRecord`),
`server/api/{__init__,inventory}.py` (5 route + secret ký quote),
`tools/restore_drill_schema.py` (Observed #5), `tests/test_178` (capabilities),
`ho_so_he_thong.txt`.

### Endpoint family

`POST /quotes` · `POST /jobs` · `GET /jobs` · `GET /jobs/{id}` ·
`POST /jobs/{id}/cancel` — tất cả owner-scoped, có scope riêng.

### Thứ tự giao dịch (bất biến, ép ở một chỗ)

```
auth → scope → validate input → verify quote (ký + fingerprint + owner)
     → idempotency claim (UNIQUE) → hold credit → insert job
     └──────────────── một transaction, request commit ────────────────┘
```

- Validate **trước** tiền: một lỗi chính tả không bao giờ tốn credit.
- `jobs.dedupe_key` vẫn được đặt theo `quote.intent` làm lưới thứ hai.
- Giá lệch giữa quote và submit → 409, không tự ý thu theo giá mới (Q84).

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_182_public_api_jobs.py` | **23 passed** |
| `pytest` test_63 + 178 + 179 + 180 + 181 | **119 passed, 2 skipped** (sau khi sửa kỳ vọng `capabilities`) |
| `python tools\gate.py` (FULL, lần 1) | FAIL 4: hồ sơ stale ×3 + `test_60` (tên app trong docstring) |
| `python tools\gate.py` (FULL, lần 2) | FAIL 1: `test_155` — UNIQUE mới chưa có trong drill |
| `python tools\gate.py --quick` (sau khi sửa) | **PASS 9/9** |
| `python tools\gate.py` (FULL, lần 3) | *(kết quả ghi ở dòng dưới)* |

Full gate lần 3: **PASS 10/10** — pytest 2.038,5 s (gate chỉ in chi tiết cho
bước đỏ; lần 2 cùng bộ này là 2.814 passed + 1 failed, và đúng cái failed đó đã
được sửa).

Điểm đáng ghi: **hai lần full gate đỏ đều bắt được lỗi thật** mà test targeted
không thấy (tên app trong docstring của `platform_core`; UNIQUE chưa vào diễn
tập khôi phục). Đây đúng là lý do MANIFEST đặt checkpoint ở prompt 06.

### Review

- **Tenant isolation:** quote khoá theo `user_id`; job list/get/cancel
  owner-scoped; khoá idempotency phạm vi theo `key_id` nên hai tài khoản dùng
  cùng chuỗi khoá không đụng nhau (có test).
- **Credit invariants:** không đủ credit → 0 hold, 0 job; hold = đúng số quote;
  settle cap theo hold (Q84, test provider vượt 40 vs hold 10 → thu 10);
  cancel hoàn **một lần**; cancel sau khi xong không hoàn.
- **Idempotency:** replay tuần tự, replay **sau khi job đã kết thúc** (khoảng
  trống của `dedupe_key`), khác body → 409, đồng thời → đúng một 201.
- **Secret/log redaction:** view công khai của job không chứa `app_slug`,
  `job_type`, `worker_id`, params hay lỗi thô; lỗi job trả câu cố định.
- **Backward compatibility:** không sửa bảng `jobs`/`credit_entries`; UI dùng
  chung đường `submit_with_credit` không đổi hành vi.
- **Migration rollback:** `downgrade()` xoá bảng + 3 index; vòng tiến–lùi–tiến
  xanh; UNIQUE đã vào diễn tập khôi phục.

### Risks

- **R15 (mới, trung bình):** input media (`image/video/audio`) hiện **bị từ chối
  có chủ ý** (`media inputs are not available on this API version`) cho tới
  Prompt 07. Wave 1 (ảnh) cần Prompt 07 xong mới mở được phần reference.
- **R16 (mới, thấp):** `GET /jobs` liệt kê **mọi** job của tài khoản, kể cả job
  tạo từ giao diện; `tool` khi đó là `null`. Chọn vậy để không có hai lịch sử
  job; nếu sau này cần lọc thì thêm `source=api`.
- **R3 (vẫn mở):** rate-limit theo principal — Prompt 08, **phải xong trước khi
  mở tool thật** vì giờ đã có đường tiêu tiền.

### Deferred

| Việc | Hoãn tới |
|---|---|
| Media input/artifact output | Prompt 07 |
| Rate-limit/quota/concurrency | Prompt 08 |
| Webhook khi job xong | Prompt 09 |
| Test đồng thời trên PostgreSQL thật (advisory lock + UNIQUE dưới tải) | cần `LTT_TEST_DATABASE_URL` |

### Rollback

`alembic downgrade a7b8c9d0e1f2`; gỡ 4 file mới + 5 route; job đã tạo qua API
vẫn chạy bình thường (chúng là job nền tảng bình thường).

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Không double hold/double job | ✅ 5 test: replay, sau-khi-xong, khác body, đồng thời, khoá theo tài khoản |
| Không mất job sau khi hold đã commit | ✅ test bơm crash + test bất biến "mọi hold đều có job" |
| Ledger invariant + regression quote cũ | ✅ full gate xanh (gồm test của app dùng quote ký sẵn có) |
| Cross-tenant jobs | ✅ đọc/hủy job của tài khoản khác → 404 |
| Quote bind owner/tool/input/cost/expiry/version | ✅ 4 test tamper/expire/steal/price-change |
| Idempotency DB-backed có UNIQUE | ✅ `(key_id, operation, idempotency_key)` + đã vào diễn tập khôi phục |
| Cancel idempotent | ✅ |
| Pagination/filter jobs | ✅ `limit/offset` trần cứng + lọc `status` |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 07 bên dưới)

---

## Prompt 07 — UPLOAD, ARTIFACT, STORAGE LIFECYCLE

### Entry gate

- Prompt 06 PASS + full gate checkpoint PASS ✅. Không migration mới (dùng lại
  bảng `upload_sessions` của Q85/Q89) → head vẫn `b8c9d0e1f2a3`.

### Observed (hai lỗi thật do test bắt, không phải giả định)

1. **Cửa sổ bồi hoàn (compensation) đặt sai chỗ.** Bản đầu chỉ bọc
   `submit + promote`; lỗi xảy ra *sau* đó (ghi bản ghi idempotency, hoặc commit
   hỏng) sẽ để lại file đã promote ngoài storage trong khi CSDL rollback —
   đúng loại orphan Q85 sinh ra để chống. Đã sửa: handler **tự commit** trong
   `try`, và `except` bồi hoàn mọi file đã chuyển. Test bơm crash chứng minh
   file quay lại `staging/` và session về `ready`.
2. **Artifact đọc được field ngoài hợp đồng.** `storage_key_for` đọc bất kỳ khoá
   nào trong `job.result`, nên một handler ghi `debug_dump` là khách tải được nó
   qua id đoán được. Đã chốt: chỉ field **có trong output schema đã publish**
   mới thành artifact; job tạo ngoài API (không có tool công khai) → 404.

### Changed

Mới: `platform_core/public_api/media.py`, `server/api/uploads.py`,
`tests/test_183_public_api_media.py` (23 test).

Sửa: `platform_core/public_api/invocation.py` (`media_params`,
`build_job_params(media_values=…)`, `promote_media`), `server/api/jobs.py`
(media ở quote/submit, `outputs` trong job view, cửa sổ bồi hoàn),
`server/api/{__init__,inventory}.py` (5 route), `tests/test_178`,
`ho_so_he_thong.txt`.

### Hợp đồng media

- Khách **không bao giờ** thấy hay gửi storage key. Hai id opaque: `upload id`
  (dòng `upload_sessions`) và `artifact id` = `<job_id>.<field>.<index>`.
- Vé upload khoá: chủ sở hữu, **app suy ra từ tool** (khách không tự chọn app),
  MIME, kích thước khai báo, TTL; `staging_key` do nền tảng sinh.
- Confirm kiểm **actual size + magic bytes** (dùng lại `upload_sessions.confirm`).
- Promote **sau khi đã giữ credit**, key đích `<app>/<user>/<job>/<param><ext>`.
- Direct-to-storage: có presign thì trả thẳng vé PUT; không có thì fallback
  multipart trần 90 MB (đúng trần Cloudflare).
- Artifact trả URL ký TTL **300 s**, `no-store`, không log URL; backend cục bộ
  thì stream qua route riêng, vẫn owner-scoped.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_183_public_api_media.py` | **23 passed** |
| `pytest` 173 + 174 + 178 + 181 + 182 | **84 passed** (sau khi cập nhật kỳ vọng `capabilities`) |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Tenant isolation:** vé upload, job và artifact của tài khoản khác đều 404;
  không attach được upload của người khác (test riêng); id sai định dạng cũng
  404 y hệt.
- **Credit invariants:** promote chỉ sau hold; test crash chứng minh không có
  hold mồ côi lẫn file mồ côi.
- **Path traversal / arbitrary key:** thử nhét `staging_key` thật,
  `../../secrets/app.env`, `files/...` vào tham số media → 400.
- **Không lộ bucket/path/credential:** test quét chuỗi trong mọi phản hồi.
- **Ticket replay:** vé đã dùng (`promoted`) hoặc chưa confirm → 400.

### Risks

- **R17 (mới, thấp):** ảnh/video nhiều phần tử (`image[]`) chưa nhận nhiều
  upload; chỉ tham số media đơn được map. Wave 11–13 sẽ cần khi mở tool có
  `image_keys`.
- **R18 (mới, thấp):** với backend cục bộ, route `/artifacts/{id}/content`
  stream qua tiến trình web. Chấp nhận cho dev/file nhỏ; production dùng R2 nên
  đi presign. Ghi vào runbook Prompt 16.

### Rollback

Gỡ `media.py`, `uploads.py`, 5 route + phần media trong `jobs.py`/`invocation.py`.
Không có migration; dữ liệu `upload_sessions` do giao diện tạo không đụng tới.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Upload session tests PASS | ✅ `test_173`, `test_174` xanh + 23 test mới |
| Cross-tenant attach/download | ✅ 3 test riêng |
| Failure không để orphan mới | ✅ test crash sau promote → file về staging, session `ready`, 0 job |
| Không lộ bucket/path/credential | ✅ test quét chuỗi ở vé upload, job view, artifact |
| Presign ưu tiên, không pipe dữ liệu lớn | ✅ dùng `upload_target()`; fallback multipart trần 90 MB |
| Asset ref chỉ nhận id hợp lệ | ✅ raw key/traversal/vé người khác → 400 |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 08 bên dưới)

---

## Prompt 08 — RATE, QUOTA, CONCURRENCY, CAPACITY

### Entry gate

Prompt 07 PASS ✅. Không migration (mọi lớp hoặc trong RAM, hoặc tính từ bảng
`jobs`/`credit_entries` đã có) → head vẫn `b8c9d0e1f2a3`.

### Quyết định hạ tầng (ADR ngắn, theo COMMON_RULES §6)

**Không thêm Redis.** Nền tảng chạy **một tiến trình web** (ADR-005, một dịch vụ
NSSM), nên cửa sổ trong RAM là **đủ thẩm quyền** cho ba lớp theo nhịp
(auth-failure, RPM, create-RPM) và tốn gần như 0. Hai lớp phải đúng bất kể có
bao nhiêu tiến trình — **đồng thời** và **trần credit ngày** — được tính **từ
CSDL** (`jobs`, `credit_entries`), đúng nguồn mà worker và sổ tiền đang dùng.

Thêm Redis chỉ để giữ những con số PostgreSQL đã giữ đúng là thêm một thứ phải
cài, giám sát, sao lưu và mất lúc 2 giờ sáng, đổi lại **không** thêm tính chất
nào.

**Failure mode phải cân trước khi chạy nhiều instance web:** lớp 1–3 thành
per-instance (giới hạn hiệu dụng = cấu hình × số instance); lớp 4–5 vẫn chính
xác. Ghi ngay trong `platform_core/public_api/limits.py` để lúc đó không phải
phát hiện lại.

### Năm lớp

| Lớp | Bảo vệ | Mặc định | Nguồn |
|---|---|---|---|
| Auth-failure throttle (theo IP **và** key_id) | không gian credential | 20 lỗi / 300 s | RAM |
| Request RPM / key | tiến trình web + CSDL | 120/phút | RAM |
| Create RPM / key | sổ credit + quota provider | 20/phút | RAM |
| Job đang chạy / tài khoản (+ theo lớp tài nguyên) | worker, GPU, hàng đợi | 5 (lớp: tắt) | **CSDL** |
| Trần credit ngày / tài khoản | bán kính thiệt hại khi lộ khoá | 0 = tắt | **CSDL** |

Lớp tài nguyên (`gpu`/`ffmpeg`/`browser`/`api`) suy ra từ `manifest.requires` —
nền tảng vẫn không biết tên app nào.

Mọi từ chối: **429 + `retry_after`** trong problem+json, mã ổn định
`rate_limited` / `concurrency_limited` / `quota_exceeded`.

### Changed

Mới: `platform_core/public_api/limits.py`, `tests/test_184_public_api_limits.py`
(19 test).

Sửa: `config.py` (7 biến môi trường mới + parser `gpu:2,ffmpeg:4`),
`server/api/auth.py` (throttle + RPM), `server/api/jobs.py` (admission control
trước khi giữ tiền), **`server/usage_rate_limit.py` (miễn `/api/v1`)**,
`ho_so_he_thong.txt`.

### Đóng R3 của Prompt 01

`UsageRateLimitMiddleware` khoá theo `request.session`, không có thì rơi về
`request.client.host` — sau Cloudflare Tunnel **mọi** client đều là loopback,
nên một tích hợp ồn ào sẽ bóp cổ toàn bộ khách API. Nay `/api/v1` được miễn khỏi
limiter của giao diện và dùng limiter theo principal. Có test chốt.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_184_public_api_limits.py` | **19 passed** |
| `pytest` 178 + 180 + 181 + 182 + 183 | **114 passed** |
| `python tools\gate.py --quick` | **PASS 9/9** |

Latency (cùng harness Prompt 01): `/login` p50 3,00 ms / p95 3,37 ms;
`/` 6,28 / 6,79 ms; `/api/v1/health` 3,28 / 3,74 ms. So baseline Prompt 02
(`/` 6,26/6,79) → **không regression**; chi phí limiter nằm trong nhiễu đo.

### Review

- **Isolation (tiêu chí chấp nhận chính):** hai test riêng — khoá ồn ào hết hạn
  mức vẫn không đụng khoá khác; kẻ dò credential bị chặn mà khoá thật vẫn 200.
- **Không lách được:** đổi endpoint không đổi ngân sách (test); đổi khoá trong
  cùng tài khoản vẫn đụng trần đồng thời và trần credit (test).
- **Không tiêu tiền khi bị chặn:** mọi test giới hạn đều đếm `credit_entries`.
- **Backpressure:** trần đồng thời là **admission control**, không phải hàng đợi
  vô hạn; job xong thì mở lại chỗ (test).
- **Provider allocator giữ nguyên:** `api_keys.rpm_limit/tpm_limit` là ngân sách
  nền-tảng-với-provider, không dính tới giới hạn khách (test chốt hai lớp tách).
- **Metrics:** `limits.metrics()` đếm từng loại vi phạm để operator vẽ đồ thị.

### Risks

- **R19 (mới, trung bình):** giới hạn theo nhịp là per-instance. Trước khi chạy
  nhiều tiến trình web phải viết ADR hoặc chuyển bộ đếm xuống PostgreSQL.
- **R20 (mới, thấp):** trần credit ngày mặc định **tắt**. Trước khi mở tool thật
  cho khách ngoài, chủ sản phẩm nên đặt một con số — đây là quyết định sản phẩm.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Một khoá lạm dụng bị cô lập | ✅ 2 test isolation |
| Không bypass bằng đổi endpoint/khoá | ✅ 2 test |
| p95 route nhẹ không regression | ✅ bảng latency ở trên |
| Provider allocator RPM/TPM giữ nguyên | ✅ không đụng `api_pool`; có test chốt |
| 429 + Retry-After + mã ổn định | ✅ 3 mã, `retry_after` trong body |
| Không thêm Redis khi chưa cần | ✅ ADR ngắn ở trên + ghi failure mode trong code |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 09 bên dưới)

---

## Prompt 09 — WEBHOOK OUTBOX, SIGNING, RETRY, SSRF

### Entry gate

Prompt 08 PASS ✅. Head vào `b8c9d0e1f2a3` → **ra `c9d0e1f2a3b4`**.

### Nguyên tắc (theo thứ tự quan trọng)

1. **Webhook không bao giờ ảnh hưởng tới job.** Sự kiện được ghi vào bảng outbox
   **trong cùng transaction** với trạng thái kết thúc của job; worker giao sau,
   theo nhịp riêng. Receiver chết/chậm/thù địch không làm chậm hay làm sai
   settlement — có test chốt đúng điều đó.
2. **Webhook không được thành kênh SSRF.** Khách chọn URL, tức là bảo nền tảng
   gửi request tới địa chỉ do bên không tin cậy chỉ định. Kiểm scheme, host,
   **mọi** IP mà tên miền phân giải ra, và **kiểm lại sau mỗi redirect** (chống
   DNS rebinding). Chặn loopback/private/link-local/metadata. Không đính bất kỳ
   credential nào của nền tảng.
3. **Receiver chứng minh được nguồn gốc.** Ký
   `HMAC-SHA256(secret, "<timestamp>.<event_id>.<raw body>")` → replay, đổi
   body, hay gửi lại sự kiện cũ đều fail verify.

**Secret webhook mã hoá at-rest, KHÔNG hash** — server phải tái tạo được để ký.
Đây là yêu cầu **ngược** với developer key (một chiều). Ghi rõ trong code và
migration để không ai "thống nhất" hai thứ này lại với nhau.

### Changed

Mới: `platform_core/public_api/{webhooks,outbox,delivery}.py`,
`server/api/webhook_routes.py`, `alembic/versions/20260813_1800_public_api_webhooks.py`
(`c9d0e1f2a3b4`), `tests/test_185_public_api_webhooks.py` (28 test).

Sửa: `platform_core/public_api/tables.py` (2 bảng), `platform_core/models.py`
(import), `platform_core/job_runner.py` (enqueue trong transaction của job ở cả
3 nhánh terminal + vòng giao webhook mỗi 15 s), `server/api/{__init__,inventory}.py`
(4 route), `tools/restore_drill_schema.py` (UNIQUE mới), `tests/test_178`,
`ho_so_he_thong.txt`.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_185_public_api_webhooks.py` | **28 passed** |
| `pytest` 63 + 155 (migration + drill) | **29 passed** |
| `pytest` 178 + 182 + 184 | **67 passed** |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Webhook down ⇒ job vẫn xong:** test giả receiver ném `ConnectionError`,
  assert job vẫn `done` và **đúng một** bút toán settle.
- **Retry:** backoff mũ có trần + jitter; hết `MAX_ATTEMPTS` → trạng thái
  `dead`, giữ lại làm bằng chứng cho khách, không xoá.
- **Dedupe:** `event_id` suy ra tất định từ `(job, status)` + UNIQUE
  `(subscription_id, event_id)` → job bị nhặt lại không gửi trùng.
- **SSRF:** 10 URL cấm (http, loopback, private, metadata, IPv6 loopback,
  `file://`, credential trong URL…) đều 400 với **cùng một** thông điệp — không
  vẽ bản đồ mạng nội bộ cho người gọi.
- **Payload mỏng:** chỉ id/tool/status; không có result, không có params. URL
  của khách không phải nơi để đổ dữ liệu.
- **Secret không vào log:** test bơm secret + token vào luồng lỗi rồi quét log.
- **Ownership:** danh sách/xoá/lịch sử giao đều owner-scoped (404 cho người khác).

### Risks

- **R21 (mới, trung bình):** worker giao webhook bằng `urllib` **đồng bộ** trong
  vòng lặp worker. Một receiver chậm ăn tối đa 10 s timeout/lần giao. Chấp nhận
  ở quy mô hiện tại (giao theo lô, mỗi 15 s); nếu số subscription lớn lên thì
  tách luồng riêng — ghi để Prompt 16 đo.
- **R22 (mới, thấp):** DNS được phân giải lúc tạo subscription và lúc giao. Máy
  không có DNS ra ngoài sẽ từ chối tạo subscription — đúng hành vi, nhưng phải
  ghi vào tài liệu vận hành.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Webhook down không ảnh hưởng settlement | ✅ test riêng |
| Target bị cấm không được gọi | ✅ 10 case + test revalidate sau redirect/rebinding |
| Signature/retry deterministic | ✅ test ký/verify + lịch backoff tất định |
| Không secret trong log | ✅ test caplog |
| Outbox giao dịch, không mất event | ✅ ghi trong transaction của job, có UNIQUE chống trùng |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 10 bên dưới)

---

## Prompt 10 — USAGE, AUDIT, RECONCILIATION, COST ATTRIBUTION

### Entry gate

Prompt 09 PASS ✅. **Không migration** — đây là quyết định thiết kế, xem dưới.
Head vẫn `c9d0e1f2a3b4`.

### Quyết định: usage được SUY RA, không lưu bản thứ hai

Prompt cho phép "usage projection"; ở đây **không tạo bảng projection**. Sổ
credit đã là chứng từ gốc (append-only, số dư = tổng sổ). Tính thẳng từ nó có ba
hệ quả:

- **không thể lệch** — không có bản sao để lệch;
- **replay idempotent không đếm hai lần** — chỉ tồn tại đúng một hold;
- **"reconcile" là phép đối chiếu hai cách đọc cùng một bảng**, không phải công
  việc sửa chữa một bảng thứ hai.

Nếu sau này listing lớn tới mức cần projection, `tools/reconcile_public_api_usage.py`
đã có sẵn để chứng minh projection còn khớp tiền — và nó đáng tin **vì đã chạy
từ lúc câu trả lời còn hiển nhiên đúng**.

**Không công bố "provider cost thật":** hệ thống không có hoá đơn provider làm
nguồn chân lý, nên bịa ra một con số là sai. Usage của khách và kế toán provider
là hai câu hỏi khác nhau (Q84 giữ variance ở nội bộ).

### Changed

Mới: `platform_core/public_api/usage.py`, `server/api/usage_routes.py`,
`tools/reconcile_public_api_usage.py`, `tests/test_186_public_api_usage.py`
(15 test).

Sửa: `server/api/{__init__,inventory}.py` (2 route), `tests/test_178`
(capabilities), `ho_so_he_thong.txt`.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_186_public_api_usage.py` | **15 passed** |
| **`python tools\gate.py` (FULL — checkpoint)** | **PASS 10/10**, pytest 2.608 s |

### Review

- **Balance khớp nguồn tiền:** test so `/credits/balance` với `credit.so_du()`
  sau khi tạo job.
- **Usage net khớp ledger** ở cả bốn ca: settle đủ, settle một phần (khách giữ
  lại phần dư), refund (net 0), cancel (net 0), và **capped** khi provider vượt
  hold (Q84 → vẫn chỉ thu bằng hold).
- **Replay idempotent:** hai request cùng khoá → một dòng usage, tổng 10.
- **Totals theo cửa sổ, không theo trang:** test riêng — tổng của một trang là
  lỗi trông giống câu trả lời.
- **Attribution:** mỗi dòng có `tool` + `key_id` (từ `_api` meta của job), lọc
  được theo cả hai.
- **Cross-tenant:** tài khoản khác thấy rỗng, tổng 0.
- **Không lộ nội bộ:** không `job_type`, `app_slug`, `worker`, `prompt`.
- **Index/N+1:** một truy vấn `GROUP BY` cho cả trang thay vì mỗi dòng một
  truy vấn; cửa sổ mặc định 30 ngày, trần 365 ngày; job đã có index
  `(user_id)` và `(created_at)`.
- **Audit:** vòng đời khoá/webhook đã có dấu vết bằng chính các cột thời gian
  (`created_at`/`rotated_at`/`revoked_at`/`disabled_at`) + `job_events`; không
  thêm bảng audit trùng lặp, không lưu payload/PII dư.

### Risks

- **R23 (mới, thấp):** lọc `tool`/`key_id` áp **sau khi** phân trang, nên một
  trang có thể trả ít dòng hơn `limit` khi lọc. Đúng về số liệu (tổng vẫn theo
  cửa sổ) nhưng hơi bất tiện; sửa gọn khi có nhu cầu thật bằng cách đẩy bộ lọc
  xuống SQL (`_api` meta nằm trong JSON `params`, cần index biểu thức).

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Balance khớp credit source | ✅ |
| Usage net khớp ledger (success/refund/partial/idempotent) | ✅ 5 test |
| Cross-tenant | ✅ |
| Query scale có index + pagination | ✅ GROUP BY một lần, cửa sổ có trần |
| Reconciliation command/test | ✅ `tools/reconcile_public_api_usage.py` + 3 test (gồm ca "hold không có job") |
| Không tạo billing system song song | ✅ **không có bảng mới**, không có migration |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 11 bên dưới)

---

## Prompt 11 — WAVE 1: CANARY + IMAGE + THUMBNAIL

### Entry gate

Prompt 10 PASS + full gate checkpoint PASS ✅. Không migration; head vẫn
`c9d0e1f2a3b4`.

### Đã mở (2 tool, không hơn)

| Tool | App | Giá | Ghi chú |
|---|---|---|---|
| `image.thumbnail` | thumbnail | 5 credit/ảnh (phẳng) | **ẩn `model`** — xem dưới |
| `image.generate` | taoanh | 5/5/8/16 theo alias | 4 alias model, 1 ảnh tham chiếu |

`image.batch_generate` **chưa mở**: cùng `job_type`, cùng schema với
`image.generate` (chỉ khác mặc định `count`), nên mở nó chỉ làm bề mặt công khai
to ra mà không thêm năng lực — `count` đã làm được việc đó.

### Ba phát hiện thật khi đọc code app

1. **API không truyền `owner_id`.** Tám app đọc `params["owner_id"]` để đặt khoá
   storage và kiểm ảnh tham chiếu thuộc về ai; route giao diện truyền, adapter
   API thì chưa. Hậu quả nếu bỏ qua: output rơi vào `taoanh/unknown/...` và mọi
   ảnh tham chiếu bị từ chối lúc chạy. Đã sửa: `invocation.submit` luôn gắn
   `owner_id` **từ principal đã xác minh**, không nhận từ request.
2. **Mô tả tool nội bộ nêu thẳng tên nhà cung cấp** ("Gemini Image") và nó chảy
   vào hợp đồng công khai. Đã thêm khoá `api_contract["description"]` (registry
   + catalog) và viết mô tả riêng cho khách; có test quét chuỗi
   `gemini/byteplus/openai/flash-image/...` trong toàn bộ catalog.
3. **`thumbnail` tính phí phẳng bất kể model.** Nếu mở `model` cho API thì khách
   chọn được model đắt nhất với giá rẻ nhất, phần chênh nền tảng chịu (variance
   Q84). Đã **ẩn `model`** ở tool này và ghi rõ điều kiện mở lại: khi hàm giá
   tính theo model như `taoanh`. Có test chốt "chỉ publish lựa chọn model ở nơi
   giá đi theo model".

Ngoài ra, giá trị enum công khai là **tập con chắt lọc** của thư viện prompt nội
bộ — bản nội bộ có mục đặt theo tên người và thí nghiệm (`khanh`, `Lego_Manh`,
`visual_style`), không phải thứ để đóng băng vào hợp đồng với khách.

### Changed

Mới: `tests/test_187_public_api_wave1.py` (14 test).

Sửa: `apps/thumbnail/manifest.py`, `apps/taoanh/manifest.py` (**chỉ thêm
`api_exposed` + `api_contract`**, không đụng logic/giá), `platform_core/registry.py`
(khoá `description`), `platform_core/public_api/{catalog,invocation}.py`,
`tests/golden/public_api_catalog_v1.json`, `tests/test_181` (drift guard nay so
với golden thay vì "chưa mở gì"), `ho_so_he_thong.txt`.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_187_public_api_wave1.py` | **14 passed** |
| `pytest` 60 + 181 + 182 + 183 | **100 passed** (sau khi cập nhật drift guard) |
| `python tools\gate.py --quick` | **PASS 9/9** |

**E2E thật qua worker:** test gọi `job_runner._chay_mot_job()` — tức là claim →
handler thật của app → storage → complete → `quyet_toan` → artifact → usage →
webhook. Chỉ **một** thứ được giả: lệnh gọi provider (`_goi_gemini`). Canary
thật cần khoá + ngân sách nên thuộc về deployment, không thuộc bộ test.

### Review

- **Parity giá API vs giao diện:** test so báo giá API với **chính hàm `_cost`**
  của app (không phải một bản sao số).
- **Ownership:** ảnh tham chiếu upload qua API được promote thành
  `taoanh/<user>/<job>/image_key.png` và test chạy đúng hàm kiểm của app
  (`_canvas_reference_keys`) để chứng minh nó hợp lệ.
- **Lỗi provider:** test ném `GeminiError("quota exhausted for key sk-live-…")`
  → job `failed`, phản hồi chỉ có câu cố định, **không** có `sk-live`/`quota`,
  credit hoàn đủ, usage net 0.
- **Fail-closed vẫn nguyên:** test đọc registry thật khẳng định `kichban`
  (retired), `demo`/`qualitylab` (admin/internal), `mediatools` (runtime, có tool
  nhận URL) **không tool nào** `api_exposed`.
- **Không route UI nào bị public:** test gọi `/thumbnail`, `/taoanh`,
  `/thumbnail/api/tao` → vẫn 303/401/404/405 như trước.
- **Ẩn input không nhận từ khách:** gửi `model` cho thumbnail hoặc `image_keys`
  cho taoanh → 400 "Unknown input field".

### Risks

- **R24 (mới, trung bình):** hai tool này giờ **có thể** ra công khai, nhưng chỉ
  khi operator đặt `LTT_PUBLIC_API=1` **và** liệt kê tên tool trong
  `LTT_PUBLIC_API_TOOLS`. Mặc định vẫn tắt. Trước khi bật thật cần: đặt trần
  credit ngày (R20), backup `LTT_API_KEY_PEPPER` (R10), và một canary thật với
  khoá Gemini.
- **R17 (vẫn mở):** tham số media dạng mảng (`image_keys`) chưa hỗ trợ; đã ẩn.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| E2E kernel → worker → artifact → settle/refund | ✅ 2 test (thành công + thất bại provider) |
| Demo vẫn internal | ✅ test đọc registry thật |
| Không route UI nào bị public | ✅ test riêng |
| Kichban vẫn RETIRED_NO_EXPOSE | ✅ test riêng |
| Adapter gọi lớp hiện hữu, không chép logic | ✅ chỉ thêm khai báo vào manifest; handler/giá không đổi một dòng |
| So sánh credit API vs UI | ✅ dùng chung hàm `_cost` |
| Fake-provider trước, canary thật sau | ✅ ghi rõ canary thật là việc của deployment |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 12 bên dưới)

---

## Prompt 12 — WAVE 2: VIDEO GENERATE, UPSCALE, GPU

### Entry gate

Prompt 11 PASS ✅. Không migration; head vẫn `c9d0e1f2a3b4`.

### Kết quả: mở 1 trong 3 ứng viên, hoãn 2 — có lý do đo được

| Ứng viên | Quyết định | Lý do |
|---|---|---|
| `image.upscale` (upscalevideo) | **EXPOSE** | Giá **phẳng** 2/4 credit theo preset, chốt trước khi chạy → báo giá ký giữ đúng tới lúc quyết toán. Đây là đường **GPU thật**: lease VRAM, job dài, huỷ được. |
| `video.upscale` (upscalevideo) | **MIGRATE_CAPABILITY_THEN_EXPOSE** | Giá phụ thuộc `duration_s` **do người gọi khai**, và worker **nâng hold** khi đo được thời lượng thật (`_dam_bao_giu_cho`, `jobs.py:102-113,260`). Với người dùng chọn file trên giao diện thì hợp lý; với máy gọi máy thì **phá lời hứa của quote đã ký** (Q84). |
| `video.generate` (taovideo) | **MIGRATE_CAPABILITY_THEN_EXPOSE** | `resolution`/`duration`/`aspect_ratio` khai `depends_on: model` và **tập hợp lệ khác nhau theo model** (mini/fast: 480p–720p; standard: tới 4k). Publish hợp nhất sẽ để khách **trả tiền cho tổ hợp mà provider từ chối**. |

Cả hai deferral đều có **test chốt lý do còn đúng** (đọc mã nguồn thật + registry
model), nên chúng không thể lặng lẽ biến thành "quên mở".

**Đường mở lại (ghi để prompt sau khỏi phải nghĩ lại):**
- `video.upscale`: đo thời lượng **phía server** từ chính file đã upload lúc báo
  giá, rồi khoá giá; hoặc chặn top-up cho job đến từ API.
- `video.generate`: hợp đồng công khai cần biểu diễn quan hệ model → tập giá trị
  (ví dụ publish theo từng model, hoặc validate tổ hợp trước khi giữ tiền).

### Changed

Mới: `tests/test_188_public_api_wave2.py` (11 test).

Sửa: `apps/upscalevideo/manifest.py` (chỉ thêm khai báo cho `image.upscale`),
`platform_core/public_api/catalog.py` (enum số publish đúng kiểu `integer` —
`1080` không nên thành `"1080"`), `tests/golden/public_api_catalog_v1.json`,
`tests/test_187` (khẳng định theo tập con vì catalog nay lớn dần),
`ho_so_he_thong.txt`.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_188_public_api_wave2.py` | **11 passed** |
| `pytest` 187 + 188 | **25 passed** |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Không job dài trong HTTP:** test khẳng định phản hồi là `queued` và job nằm
  trong bảng, không chạy trong request.
- **Capacity/GPU:** `LTT_PUBLIC_API_CLASS_CONCURRENCY=gpu:1` → job GPU thứ hai
  bị 429 `concurrency_limited` (kèm `resource: gpu`) **trước khi** giữ tiền;
  test đếm bút toán = 1.
- **Cancel:** huỷ job GPU đang chờ → hoàn đủ credit **và** giải phóng suất, job
  mới được nhận ngay.
- **Lỗi engine:** engine không sẵn sàng → job `failed`, phản hồi chỉ có câu cố
  định (không có "esrgan"), hoàn **đúng một** lần.
- **Retry không tính tiền hai lần:** cùng `Idempotency-Key` → 201 rồi 200, số dư
  chỉ trừ một lần.
- **Parity giá:** test so báo giá với chính `_cost` của app (2 và 4).
- **Không lộ hạ tầng:** mô tả công khai không chứa `gpu`, `esrgan`, `cuda`,
  `vram`, tên app — có test quét chuỗi (chính test này đã bắt bản mô tả đầu tiên
  của tôi nói "local GPU engine" và tôi đã viết lại).

### Risks

- **R25 (mới, trung bình):** `video.upscale` có thể nâng hold giữa chừng. Không
  ảnh hưởng API hôm nay (chưa expose) nhưng **giao diện vẫn đang làm vậy** —
  đáng để chủ sản phẩm biết: một video dài hơn khai báo sẽ bị trừ nhiều hơn số
  hiện lúc bấm.
- **R26 (mới, thấp):** `image.upscale` chạy trên lane `upscalevideo.render` (giữ
  12 GB VRAM) chứ không phải lane `.fast` 2 GB, vì ToolSpec tĩnh khoá `job_type`
  (Q86). Job ảnh vì thế giữ chỗ VRAM rộng hơn cần. Sửa khi hợp đồng ToolSpec hỗ
  trợ lane động.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Không job dài trong HTTP | ✅ |
| GPU/resource lease cleanup | ✅ huỷ giải phóng suất; lease VRAM do `gpu_lease` nền tảng lo, manifest khai VRAM |
| Crash/retry không double charge | ✅ test retry + test lỗi engine (hoàn đúng 1 lần) |
| Provider secret/raw error không lộ | ✅ |
| Giữ quote/reference logic, không bypass hold | ✅ input ảnh đi qua upload → promote **sau** hold |
| So sánh credit UI/API | ✅ dùng chung `_cost` |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 13 bên dưới)

---

## Prompt 13 — WAVE 3: PROMPT/STORYBOARD, SUBTITLE, SHORT CLIP

### Entry gate

Prompt 12 PASS ✅. Không migration; head vẫn `c9d0e1f2a3b4`.

### Kết quả: mở 2 / 4 ứng viên

| Ứng viên | Quyết định | Lý do |
|---|---|---|
| `text.prompt_package` | **EXPOSE** | Giá tính từ `scene_count` — không có thời lượng do client khai, không có top-up, quote ký giữ đúng. |
| `story.storyboard` | **EXPOSE** | Như trên. |
| `video.subtitle` (autosubvideo) | **MIGRATE_CAPABILITY_THEN_EXPOSE** | Cùng **một nguyên nhân gốc** với `video.upscale`: giá theo `duration_s` client khai + `_dam_bao_giu_cho` nâng hold lúc chạy. |
| `video.short_clips` (taoclipngan) | **MIGRATE_CAPABILITY_THEN_EXPOSE** | Như trên (GPU + duration). |

Ba tool bị hoãn ở Wave 2–3 **chung một nguyên nhân**, nên ghi một lần: *hợp đồng
giá dựa trên thời lượng do người gọi khai, và worker nâng hold khi đo được thật*.
Sửa nó một chỗ (đo phía server lúc báo giá, hoặc chặn top-up cho job từ API) là
mở được cả ba.

### Bổ sung hợp đồng: job trả về **dữ liệu**, không chỉ file

Wave 1–2 trả file nên job view chỉ có `outputs` (artifact id). Wave 3 trả **dữ
liệu** (`prompt_package`, `storyboard`) — nếu không bổ sung thì khách gọi xong
**không lấy được kết quả**. Đã thêm `result` vào job view, lọc theo **đúng
output schema đã publish**: field nào handler tự thêm (log, id request provider)
không bao giờ ra ngoài. Có test bơm `debug_trace` + `provider_request_id` vào
result rồi assert chúng không xuất hiện.

### Lỗi thật do test bắt (quan trọng)

**Ẩn `operation` làm storyboard chạy và tính giá như prompt-package.** Tham số
`operation` là công tắc định tuyến nội bộ nên phải ẩn khỏi hợp đồng — nhưng ẩn
mà **không điền** thì handler rơi về mặc định *của nó* (`director`), tức là
khách đặt storyboard nhận về gói prompt và trả 6 credit thay vì 4.

Sửa ở gốc, áp cho mọi tool: **tham số ẩn được server điền bằng đúng `default` mà
app đã khai** trong `params_schema`. Có regression test riêng.

### Changed

Mới: `tests/test_189_public_api_wave3.py` (13 test).

Sửa: `apps/prompt_ai_ommi/manifest.py` (khai báo cho 2 tool),
`platform_core/public_api/media.py` (`results_of`),
`platform_core/public_api/invocation.py` (điền tham số ẩn theo default +
`tool_contract()`), `server/api/jobs.py` (`result` trong job view),
`tests/golden/public_api_catalog_v1.json`, `tests/test_187`/`test_188` (đọc tập
đã publish **từ golden** thay vì lặp lại danh sách), `ho_so_he_thong.txt`.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_189_public_api_wave3.py` | **13 passed** |
| `pytest` 187 + 188 + 189 + 181 + 186 | **76 passed** |
| `python tools\gate.py --quick` | **PASS 9/9** |

### Review

- **Chỉ logical tool được expose:** Prompt AI có hàng chục route nội bộ; API
  publish **đúng 2 tool**. Test khẳng định inventory route không chứa
  `project/ommi/library/resource`.
- **Project CRUD nội bộ không lộ:** app giữ bảng riêng (`ommi_*`), không route
  công khai nào chạm.
- **Tenant guard cho `resources`:** tham số JSON tự do do project schema diễn
  giải (có cả tham chiếu) → **ẩn** cho tới khi có hình dạng công khai kiểm được
  chủ sở hữu.
- **Giới hạn input chặn trước khi tính tiền:** `story` > 12.000 ký tự,
  `scene_count` > 20 → 400, **0 bút toán**.
- **Cross-tenant:** kết quả dữ liệu của tài khoản khác → 404.
- **Reconcile:** test chạy `usage.reconcile` sau job dữ liệu → `ok=True`.
- **Job 0-credit của Q50 (`transcribe/diarize/translate`) không public:** test
  khẳng định giá = 0 **và** app không expose tool nào.

### Risks

- **R27 (mới, thấp):** `text.prompt_package` ẩn `duration_seconds`? Không —
  tham số này vẫn public nhưng **không ảnh hưởng giá**; giá chỉ theo
  `scene_count`. Nếu sau này giá tính theo thời lượng thì phải xem lại như ba
  tool video.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Chỉ logical tools được expose | ✅ 2 tool, không route project nào |
| Project CRUD nội bộ không lộ | ✅ |
| E2E + credit reconciliation từng candidate đã bật | ✅ 2 tool: quote → job → result → usage → reconcile |
| Mỗi operation đi một Public Job contract nhất quán | ✅ cùng quote/idempotency/cancel/usage/webhook như wave trước |
| Không public 68 route Prompt AI / 25 route Autosub | ✅ |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 14 bên dưới)

---

## Prompt 14 — COVERAGE 100% APP

### Entry gate

Prompt 13 PASS ✅. Không migration; head vẫn `c9d0e1f2a3b4`.

### Việc chính: biến "đã quyết định hết" thành thứ máy kiểm được

`APP_DISPOSITION_V1.md` bản Prompt 01 là **ý định trước khi đọc kỹ**; bản này là
**kết quả sau 3 wave**. Nhưng tài liệu thì trôi, nên disposition được viết lại
thành bảng trong `tests/test_190_public_api_coverage.py` và máy kiểm:

- **thêm một app mà chưa quyết định → test đỏ** (đây chính là bảo đảm "không app
  nào UNKNOWN", không phải một lời hứa trong tài liệu);
- app đánh `EXPOSE_V1` phải publish **đúng** danh sách tool đó, không hơn;
- mọi trạng thái khác phải publish **rỗng**;
- catalog đã publish (golden) phải bằng hợp của các app `EXPOSE_V1`;
- app đóng phải bị `catalog.app_may_be_public()` từ chối **kể cả khi cờ trong
  manifest bị bật nhầm** (belt and braces).

### Disposition chốt (14/14)

| Trạng thái | App |
|---|---|
| **EXPOSE_V1** (4) | thumbnail, taoanh, upscalevideo, prompt_ai_ommi |
| **MIGRATE_CAPABILITY_THEN_EXPOSE** (3) | taovideo, autosubvideo, taoclipngan |
| **DEFER** (2) | chataistudio, agent |
| **INTERNAL_ONLY** (4) | mediatools, qualitylab, demo, socialbot |
| **RETIRED_NO_EXPOSE** (1) | kichban |

6/21 ToolSpec đang public. Chi tiết + lý do từng app ở `APP_DISPOSITION_V1.md`.

**Lý do được kiểm bằng code, không bằng trí nhớ:** test khẳng định chat vẫn
không có `job_types`/`credit_cost` và vẫn giữ credit theo id tin nhắn; agent vẫn
là orchestrator (`tools=()`, một job type `agent.advance`); socialbot vẫn
`maintenance` + `browser` + không giá.

### Changed

Mới: `tests/test_190_public_api_coverage.py` (22 test).
Viết lại: `docs/PUBLIC_API/APP_DISPOSITION_V1.md` (bản chốt sau 3 wave).
Sửa: `ho_so_he_thong.txt`.

**Không mở thêm tool nào** — đúng ý prompt: "API cho toàn LTTSTUDIOS" không đồng
nghĩa public bừa.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_190_public_api_coverage.py` | **22 passed** |
| `python tools\gate.py` (FULL — checkpoint) | pytest **PASS** (toàn bộ, 2.502 s); một bước scanner đỏ do template của **Prompt 15** viết sau đó, đã sửa và quay lại xanh — xem Prompt 15 |

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| 100% app có disposition cuối | ✅ 14/14, máy kiểm |
| Không app internal/retired/maintenance bị public ngầm | ✅ 2 lớp: bảng disposition + `app_may_be_public` |
| Mọi EXPOSE_V1 có E2E + ownership + credit + idempotency tests | ✅ wave 1/2/3 (test_187/188/189) |
| chataistudio, agent, socialbot có quyết định + lý do | ✅ DEFER/INTERNAL_ONLY, lý do kiểm bằng code |
| kichban không hồi sinh bằng đường tắt | ✅ RETIRED_NO_EXPOSE + test |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 15 bên dưới)

---

## Prompt 15 — DEVELOPER PORTAL + DOCS + SDK

### Entry gate

Prompt 14 PASS ✅. Không migration; head vẫn `c9d0e1f2a3b4`.

**Ghi chú về gate của Prompt 14:** lần chạy full gate đầu bị dừng giữa chừng
(phiên trước kết thúc), lần thứ hai chạy **trên cây mã đang sửa dở** của Prompt
15 nên kết quả không dùng được — đã dừng và chạy lại một lần sạch, kết quả ghi
ở bảng Prompt 14. Không có "gate xanh" nào được tính từ một lần chạy trên cây
đang thay đổi.

### Changed

Mới:
- `server/routes/developer.py` + `server/templates/developers.html` — portal
  `/developers` (session + CSRF).
- `tools/build_public_api_docs.py` — sinh phần "công cụ đang mở" của tài liệu
  **từ chính catalog**, có `--check` chống trôi.
- `docs/PUBLIC_API/DEVELOPER_GUIDE.md` — hướng dẫn cho người tích hợp.
- `sdk/python/ltt_public_api.py`, `sdk/typescript/ltt-public-api.ts`.
- `tests/test_191_developer_portal_sdk.py` (15 test).

Sửa: `server/app.py` (mount portal), `tools/system_profile_config.json` (thêm
`sdk` vào hồ sơ — SDK là mã nguồn người tiếp quản phải đọc được, Q91),
`ho_so_he_thong.txt`.

### Ba điều portal cố ý làm khác API

1. **Có CSRF.** Đây là bề mặt phiên; trình duyệt tự đính cookie nên mọi POST đổi
   trạng thái đều phải có token. `/api/v1` thì ngược lại: từ chối cookie nên
   CSRF vô nghĩa ở đó.
2. **Là nơi duy nhất tạo khóa**, và bí mật hiện **một lần** trên đúng phản hồi
   tạo. Tải lại là mất — không phải vì giấu, mà vì máy chủ không tái tạo được.
3. **Không hiện credential provider.** Có test bơm một khoá Gemini thật vào
   `api_keys` rồi assert trang không chứa giá trị, tên nhà cung cấp hay tên cột.

### Lỗi thật do test/gate bắt

1. **Thứ tự dependency làm 500 thay vì redirect.** `Depends(get_db)` chạy trước
   thân hàm, nên khách chưa đăng nhập gặp lỗi CSDL trước khi kịp bị đá về
   `/login`. Đã khai `require_account` **trước** `get_db` trên mọi route.
2. **Portal đọc cấu hình từ biến môi trường tiến trình** thay vì cấu hình app
   được mount → mô tả sai deployment (test dựng app với env riêng thấy "không
   có công cụ nào"). Nay đọc `app.state.public_api`.
3. **Bánh cóc i18n bắt 44 chuỗi Việt chưa bọc `_()`** trong template mới — đã
   bọc hết; số chuỗi chưa dịch toàn repo trở lại **1.439/1.500**.

### Tests

| Lệnh | Kết quả |
|---|---|
| `pytest tests/test_191_developer_portal_sdk.py` | **15 passed** |
| `python tools\gate.py` (FULL) | pytest **PASS 2.502 s**; scanner i18n đỏ vì template mới → đã sửa |
| `python tools\gate.py --quick` (sau khi sửa) | **PASS 9/9** |

### Kiểm bằng trình duyệt thật (CLAUDE.md mục 5)

Không chỉ test xanh: dựng một máy chủ **dùng một lần** trên **cổng 8123** với
SQLite tạm (không đụng 8100 của nền tảng, 8000 của hệ khác, không đụng CSDL
production), rồi lái Chrome thật qua Playwright:

- đăng nhập → `/developers` mở đúng, hiện credit và danh sách scope/công cụ;
- tạo khóa → hiện chuỗi `ltt_sk_…` kèm cảnh báo "chỉ hiện một lần";
- **tải lại trang → chuỗi bí mật biến mất** (`find "ltt_sk_"` → không khớp),
  chỉ còn `key_id` công khai và tên khóa trong bảng;
- **console: 0 lỗi, 0 cảnh báo**; không request nào hỏng.

Máy chủ tạm đã tắt sau khi kiểm.

### Docs và SDK

- Phần "công cụ đang mở" của hướng dẫn **sinh từ catalog**; `--check` chạy trong
  test nên tài liệu không thể trôi khỏi API.
- Hướng dẫn nói thẳng **chưa có sandbox** — mọi lời gọi tiêu credit thật. Không
  giả vờ có môi trường thử.
- SDK Python: không phụ thuộc thư viện ngoài; GET có retry; **POST tính tiền chỉ
  retry với cùng `Idempotency-Key`** (test bơm 503 lần đầu rồi assert cả hai lần
  gửi cùng một khóa).
- SDK TypeScript: `fetch` thuần, `crypto.subtle` để verify chữ ký webhook, so
  sánh constant-time.

### Risks

- **R28 (mới, trung bình):** repo **chưa có toolchain TypeScript** cho SDK (ba
  frontend hiện có đều là Vite app riêng). SDK TS vì thế chỉ được kiểm ở mức
  **văn bản** (hợp đồng retry/idempotency/verify). Muốn kiểm thật cần thêm một
  gói vitest và khai vào `FRONTENDS` của gate — một quyết định riêng.
- **R29 (mới, thấp):** portal chưa có trang tạo/xoá webhook (chỉ hiển thị);
  webhook quản lý qua API. Đủ cho V1, ghi lại nếu muốn bổ sung.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Fresh developer flow chạy được theo docs | ✅ test SDK end-to-end + kiểm trình duyệt thật |
| SDK retry không double-charge | ✅ test cùng `Idempotency-Key` qua các lần retry |
| Portal tenant/CSRF/one-time secret | ✅ 5 test + kiểm trình duyệt |
| Docs/OpenAPI/catalog không drift | ✅ sinh từ catalog + `--check` trong test |
| Không hiện provider API key | ✅ test riêng |
| Refresh không lấy lại secret | ✅ test + kiểm trình duyệt |

**NEXT_PROMPT_ALLOWED=true** (đã dùng — xem Prompt 16 bên dưới)

---

## Prompt 16 — SECURITY, OBSERVABILITY, PERFORMANCE HARDENING

### Entry gate

Prompt 15 PASS ✅. Không migration; head vẫn `c9d0e1f2a3b4`.

### Changed

Mới:
- `platform_core/public_api/metrics.py` — bộ đếm trong tiến trình.
- `docs/PUBLIC_API/THREAT_MODEL_V1.md` — threat model + **runbook bật/sự cố**.
- `tests/test_192_public_api_hardening.py` (18 test).

Sửa:
- `server/api/guard.py` — thêm **log truy cập có cấu trúc** + đo latency cho mọi
  request `/api/v1`.
- `server/api/auth.py` — đếm auth success/failure, đưa principal lên
  `request.state` để log dùng.
- `server/api/jobs.py` — gắn `tool`/`job_id`/`credit_delta` vào dòng log, đếm
  job tạo/huỷ và credit held/refunded.
- `platform_core/public_api/config.py` + `server/api/__init__.py` — **CORS
  allowlist**, mặc định tắt.
- `platform_core/job_runner.py` — worker in metrics mỗi 5 phút.
- `platform_core/public_api/idempotency.py` — đếm conflict.
- `ho_so_he_thong.txt`.

### Security suite (một test cho mỗi lớp rủi ro OWASP API)

| Lớp | Kết quả |
|---|---|
| API1 BOLA | job/artifact/upload/webhook của tài khoản khác đều 404 giống hệt "không tồn tại" |
| API2 auth enumeration | 4 kiểu credential sai → **một** status và **một** thông điệp |
| API3 mass assignment | `owner_id`, `credit_cost`, `_api` nhét vào input → 400 |
| API4 resource consumption | body 300 KiB → 413; `limit=100000` → kẹp 100; trần job/RPM có thật |
| API5 BFLA | 5 endpoint khác nhau, khoá thiếu scope → 403 hết |
| API6 charge bypass/replay | không quote → 400; replay → **một** hold |
| API7 SSRF | 4 URL cấm → 400; và **không tool nào đang publish nhận URL** |
| API8 misconfiguration | mọi cờ mặc định ở vị trí đóng (kể cả CORS) |
| API9 inventory | route thực tế == inventory khai báo |
| API10 upstream output | `provider_raw`/`stack` do handler thêm **không** ra ngoài |

### CORS — quyết định

Mặc định **không gửi header CORS nào**. API này xác thực bằng header mà trình
duyệt không tự đính, nên server-side integration không cần CORS; còn wildcard là
mở đường cho một trang bất kỳ tiêu credit nếu trình duyệt từng đính khoá hộ.
Muốn dùng từ trình duyệt thì khai `LTT_PUBLIC_API_CORS_ORIGINS` — allowlist
tường minh, **không** `allow_credentials`. Có test cho cả hai chiều.

### Observability

Một dòng log/`request`: `request_id, method, route, status, latency_ms, key_id,
owner, tool, job_id, credit_delta, ip`. Test khẳng định **có đủ các trường** và
**không có** token/secret/Authorization. Counters: auth, 4xx/5xx, rate-limit,
idempotency replay/conflict, job, credit, webhook, latency — worker in mỗi 5 phút.

Không thêm Prometheus: một tiến trình web + một worker; thêm dịch vụ giám sát là
thêm thứ phải cài/sao lưu/mất lúc 2h sáng — cùng lý do đã giữ Redis ở ngoài.

### Diễn tập backup/restore cho bảng mới

Chạy thật trong test: gieo dữ liệu vào **cả 4 bảng** Public API → sao lưu CSDL
→ khôi phục sang file khác → đối chiếu **số dòng** và **ràng buộc**, rồi thử
chèn trùng `Idempotency-Key` sau khi khôi phục → vẫn bị từ chối.

Đây là bản tương đương trên SQLite. Diễn tập trên **PostgreSQL** cần cụm riêng
(`tools/restore_drill_schema.py`); cụm trên máy này phục vụ production nên tôi
không tự tạo database — việc của operator, lệnh đã ghi trong threat model.

### Hiệu năng — so baseline Prompt 01

| Route | Baseline P01 | P08 | **P16** |
|---|---|---|---|
| `/login` | 3,17 / 3,83 ms | 3,08 / 3,38 | 3,30 / 3,73 |
| `/` | 6,33 / 6,75 ms | 6,26 / 6,79 | 6,84 / 7,48 |
| `/api/v1/health` | — | 3,28 / 3,74 | 3,54 / 4,26 |

Chênh 5–8% so với lần đo trước, cả ở route **không** đi qua code mới (`/`) —
tức là nhiễu của máy đo, không phải chi phí của log truy cập. Không "tối ưu"
gì thêm: chưa có bằng chứng nút thắt nào (nhiệm vụ 10 của prompt).

### Quét bí mật và phụ thuộc

- `tools/scan_source_secrets.py`: **0 finding**. (Nó bắt đúng một credential giả
  tôi viết trong test mới; đã đổi cách viết — một scanner kêu oan trên chính bộ
  test của mình là scanner sẽ bị bỏ qua.)
- Phụ thuộc: `pip list --outdated` cho thấy nhiều gói có bản mới. **Chưa có**
  công cụ quét lỗ hổng (`pip-audit` không cài) nên tôi **không** tuyên bố "không
  có CVE" — chỉ ghi lại là chưa quét được. Nâng cấp phụ thuộc là việc riêng và
  bị Q17 ràng buộc (phải pin cận trên).

### Risks

- **R30 (mới, thấp):** log truy cập thêm một dòng cho **mỗi** request API. Ở
  tải cao đây là I/O thật; đã có xoay vòng file (`observability.configure_logging`)
  nhưng chưa đo ở tải lớn — Prompt 17 sẽ chạm tới.
- Các rủi ro còn mở (giới hạn per-process, không sandbox, trần credit tắt, SDK
  TS chưa có toolchain, chưa quét CVE, chưa diễn tập trên PostgreSQL) được liệt
  kê **tường minh** ở mục 3 của threat model, kèm lý do chấp nhận được lúc này.

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Security suite xanh | ✅ 18 test, 10 lớp OWASP |
| Secret scan 0 finding mới | ✅ 0 |
| p95 control-plane trong ngưỡng / có blocker ghi rõ | ✅ trong nhiễu đo; bảng so sánh ở trên |
| Backup/restore rehearsal PASS | ✅ trên SQLite (dữ liệu + ràng buộc + từ chối trùng); PostgreSQL cần cụm riêng — ghi rõ là việc operator |

**NEXT_PROMPT_ALLOWED=true**
Prompt kế tiếp: `prompts/17_FINAL_JOBTEST_LOAD_SOAK_FAILURE_RECOVERY_RELEASE_GATE.txt`

---

## Prompt 17 — Final jobtest, load/soak, failure recovery, release gate ✅

### Entry gate

Prompt 16 PASS ✅. Không migration mới; head vẫn `c9d0e1f2a3b4`.

### Changed

Mới:
- `tools/public_api_load_test.py` — harness tải/soak **trong tiến trình**
  (5 kịch bản: reads / creates / duplicates / abusive / uploads).
- `tests/test_193_public_api_release.py` (13 test) — canary end-to-end + bơm lỗi
  + tải ngắn.
- `docs/PUBLIC_API/RELEASE_READINESS_V1.md` — inventory freeze, PASS/FAIL từng
  gate, giới hạn, rollback 3 mức, checklist Cloudflare, giám sát, canary.

Sửa: `ho_so_he_thong.txt`.

### A. Canary chuỗi đầy đủ (stub provider)

`image.thumbnail`: auth → scope → quote → idempotency → hold → queue → **worker
thật** → storage → artifact → settle → usage → webhook. Sổ tiền sau đó: **1 hold,
1 settle, 0 refund**, `usage.reconcile` → `ok`. Canary có tiêu tiền thật là việc
của deployment, không làm ở đây.

### D. Tải — số đo thật (in-process, SQLite tạm, không chạm production)

| Kịch bản | Kết quả |
|---|---|
| `reads` 6 luồng × 6 s | 1.063 req, ~177 rps, p50 29 ms, p95 47 ms, p99 88 ms, 100% 200 |
| `duplicates` 6 luồng × 6 s, cùng một `Idempotency-Key` | 839 req → **1 job, 1 hold**; 1×201 + 838 replay |
| `abusive` 1 khoá dồn + 3 khoá lịch sự × 8 s | khoá dồn 120×200 rồi **1.375×429**; khoá lịch sự 24×200, **0×429** |

Hai điều chỉnh trong harness trước khi con số có nghĩa: đếm status **theo từng
client** (gộp chung thì không phân biệt được "limiter nổ" với "khách ngoan bị vạ
lây"), và cho client "ngoan" chạy đúng nhịp công bố (không thì nó cũng lạm dụng,
bị chặn vì lý do chính đáng, và phép đo cách ly chứng minh **không** điều gì).

### E. Failure recovery — bơm lỗi, không mô phỏng bằng lời

| Sự cố | Kết quả |
|---|---|
| Crash giữa hold và queue | 0 hold, 0 job |
| Worker chết giữa job | nhặt lại; **đúng một** lần kết sổ (settle *hoặc* refund) |
| Provider timeout | hoàn đủ, 1 dòng `refund` |
| Storage lỗi | không trừ tiền khách, hoàn 1 lần |
| Webhook receiver chết | job `succeeded`, tiền không đổi |
| Retry trùng khoá (tuần tự + đồng thời) | 1 job, 1 hold |
| Crash sau promote | file trả về `staging/`, không orphan |

Tất cả kèm `usage.reconcile(...)` → `ok=True`.

### Full gate — và một lỗi thật nó bắt được

Lần chạy đầu **ĐỎ**: `tests/test_25_antispam_integration.py::TestMaintenanceDaemon::test_gap8_web_app_starts_daemon`.

Không phải flaky. `tools/public_api_load_test.py` đặt `LTT_DATABASE_URL`,
`LTT_DATA_DIR`, `LTT_API_KEY_PEPPER` vào `os.environ` mà **không trả lại**. Chạy
như script thì vô hại; nhưng `test_193` gọi `run()`, và vì pytest thu thập theo
thứ tự chữ (`test_178…` < `test_25…`) nên mọi test sau đó thấy `LTT_DATA_DIR`
trỏ vào thư mục tạm đã bị xoá → `load_settings()` ném → `core_settings=None` →
**MaintenanceDaemon lặng lẽ không khởi động**. Đúng thứ test đó sinh ra để bắt.

Sửa ở gốc: `run()` chụp env, `finally` khôi phục + `reset_engine()`; thêm test
hồi quy `test_the_load_harness_leaves_the_process_as_it_found_it`. Bỏ luôn ba
`@pytest.mark.slow` vô nghĩa (repo không có pytest config đăng ký marker, không
có gì lọc theo nó — chỉ hứa một khả năng không tồn tại và cảnh báo mỗi lần chạy).

Lần chạy sau — **sạch, trên cây mã cuối cùng**:

```
[PASS] secret scan / app contract lint / ten chua dinh nghia / nuot loi lang le
[PASS] chuoi chua dich / system profile / 3 frontend
[PASS] pytest                       2530.9s
RESULT: PASS   (10/10)
```

### Acceptance Gate

| Yêu cầu | Kết quả |
|---|---|
| Canary chuỗi đầy đủ, kết sổ đúng một lần | ✅ |
| Load/soak có số đo, không double-charge dưới đồng thời | ✅ 839 req → 1 job/1 hold |
| Cách ly giữa các khoá | ✅ khoá ngoan 0×429 |
| Failure recovery 7 kịch bản | ✅ reconcile `ok` cả 7 |
| Full gate xanh trên cây mã cuối | ✅ 10/10 |
| RELEASE_READINESS_V1.md có kết luận duy nhất | ✅ `READY_FOR_CONTROLLED_DEPLOY` (kèm 4 điều kiện) |
| Không deploy production | ✅ không chạm máy chủ, không chạm cụm PostgreSQL thật |

### Còn mở (đã ghi tường minh, không phải lỗi giấu)

- Diễn tập khôi phục trên **PostgreSQL** — cần cụm riêng, việc của operator.
- Tải **qua Cloudflare** — cần phê duyệt riêng.
- **Quét CVE phụ thuộc** — không có công cụ cài sẵn.
- 3 tool video + `video.generate` + chat + agent: DEFER, lý do và test chốt lý
  do ở `APP_DISPOSITION_V1.md` và `test_190`.

**NEXT_PROMPT_ALLOWED=false**
Hết pack (17/17). Việc tiếp theo **không** thuộc pack: commit, và quyết định
deploy có kiểm soát theo checklist trong `RELEASE_READINESS_V1.md`.
