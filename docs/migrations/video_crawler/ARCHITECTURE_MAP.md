# video_crawler — bản đồ kiến trúc (API thật, có file:line)

Đo trên worktree `D:\LTTSTUDIOSAPP-video-crawler` @ `e94dd9a2` (main), 22/09/2026.
Mọi số dòng là của commit này. Chỉ đọc — không sửa mã.

---

## 1. Nộp job từ route (giữ credit + submit)

**Hàm dùng:** `platform_core/job_submit.py:40`

```python
submit_with_credit(db, *, user_id: str, app_slug: str, job_type: str,
    params: dict, dedupe_key: str = "", max_attempts: int = 3,
    correlation_id: str = "", retry_of_id: str = "",
    quoted_credit: int | None = None,
    admission_resource: str = "", admission_slots: int = 0,
    origin: str | None = None, priority_class: str | None = None) -> Job
```

- Trả về `platform_core.models.Job` (ORM). **KHÔNG commit** — route phải `db.commit()`
  (hoặc dùng `server.deps.get_db`, cái này tự commit khi xong / rollback khi lỗi, `server/deps.py:18-41`).
- Thứ tự: `registry.credit_for(job_type, params)` (`job_submit.py:66`) → `jobs.submit(...)`
  (`:69`) → chỉ `credit.giu_cho(db, user_id, estimate, job.id)` khi `credit.so_da_giu(db, job.id) == 0 and estimate > 0` (`:77-78`).
- Lỗi: `credit.ThieuCreditError` (thiếu credit → rollback), `registry.RegistryError` (job_type không ai nhận / không có giá).
- **Khoá dedupe:** `dedupe_key_for(job_type, params) -> str` (`job_submit.py:29`) = sha256 của
  `job_type + "\x00" + json.dumps(params, sort_keys=True)`. Dedupe thật ở `jobs.submit`
  (`platform_core/jobs.py:154-163`): cùng `user_id` + cùng `dedupe_key` + job cũ đang
  `queued`/`running` ⇒ trả lại job cũ (không tạo mới, không giữ tiền lần hai). Job cũ đã kết thúc ⇒ tạo job mới.
  Không truyền `dedupe_key` ⇒ không dedupe.
- `jobs.submit` (`jobs.py:140`) nhận thêm `parent_id, plan_id, step_id` — `submit_with_credit` KHÔNG chuyển các tham số này.
- ⚠️ `max_attempts` mặc định 3. `AppManifest.so_lan_thu` (`registry.py:802`) chỉ được Public API đọc
  (`platform_core/public_api/invocation.py:573,581`) — route UI phải tự truyền `max_attempts=`.

**Ví dụ thật:** `apps/thumbnail/routes.py:277-405` (`queue`):

```python
from platform_core.job_submit import dedupe_key_for, submit_with_credit   # :299
gen = get_session(); db = next(gen)                                        # :354
job = submit_with_credit(db, user_id=u.id, app_slug=MANIFEST.slug,
        job_type="thumbnail.generate", params=params,
        dedupe_key=dedupe_key_for("thumbnail.generate", params))           # :357-361
db.commit()                                                                # :380
except credit.ThieuCreditError: db.rollback() ...                          # :382
except RegistryError: db.rollback() ...                                    # :389
```

- `u = user_hien_tai(request)` (`server/deps.py:44`) trả đối tượng User (dùng `u.id`); `None` với admin nội bộ → phải từ chối (`thumbnail/routes.py:318-322`).
- `require_login` (`server/auth/session.py:161`) trả **chuỗi** định danh, không phải id.
- Mẫu gọn hơn với `Depends(get_db)`: `tests/conftest.py:269-286` (`_router_thu().queue`) → `RedirectResponse(f"/jobs/{job.id}", 303)`.
- HTMX: trả `Response(204, headers={"HX-Redirect": target})` (`thumbnail/routes.py:402-404`).

---

## 2. Hợp đồng handler `handle(params, ctx)`

**Tra handler:** `jobs.resolve_handler(job_type)` (`platform_core/jobs.py:615`) → `registry.job_type_owners()` → `importlib.import_module(f"apps.{slug}.jobs").handle`.
Gọi: `result = handler(params, ctx)` (`platform_core/job_runner.py:641`); trả không phải dict thì bọc `{"result": ...}` (`:642-643`).

**`JobContext`** (`platform_core/job_runner.py:71-174`) — đây là TẤT CẢ những gì ctx có:

| Thuộc tính / hàm | Dòng | Ghi chú |
|---|---|---|
| `ctx.job_id: str` | :80 | |
| `ctx.gpu_uuid: str`, `ctx.has_gpu` | :87, :94 | chỉ khi manifest khai `gpu_vram_mb` |
| `ctx.gpu_env(base=None) -> dict` | :97 | env ghim card cho subprocess |
| `ctx.worker_id`, `ctx.attempt`, `ctx.app_slug`, `ctx.job_type` | :88-92, gán ở :626-632 | `attempt` = `job.attempts + 1` |
| `ctx.progress(percent: int, message: str = "")` | :110 | mở transaction ngắn, **cập nhật heartbeat**; job đã bị huỷ ⇒ `raise JobCancelled()` |
| `ctx.event(event_code, message="", *, details=None, level="info", visibility=job_events.INTERNAL, event_key=None) -> bool` | :135 | best-effort, không ném |
| `ctx.stage(name, message="", *, details=None, event_key=None) -> bool` | :161 | event `stage` nội bộ |
| `ctx.is_cancelled() -> bool` | :169 | đọc DB; an toàn trong callback subprocess |
| `ctx.provider_dispatched(provider="")` / `ctx.provider_rejected(provider="")` | :119, :127 | đánh dấu trước/sau gọi HTTP ra ngoài |

- **KHÔNG có** `user_id`, `workdir`/thư mục tạm, hay handle storage trên ctx. `user_id` phải nằm trong `params`
  (thumbnail để `params["owner_id"] = u.id`, `thumbnail/routes.py:350`). Thư mục tạm: app tự dùng `tempfile`
  (vd `apps/audio_pause/jobs.py:46`, `apps/qualitylab/jobs.py:69`); `platform_core/runtime_paths.py:42-47`
  có `RuntimePaths.temp_video_dir` nếu cần.
- **Huỷ:** `POST /jobs/{job_id}/cancel` (`server/routes/jobs.py:259-279`) → `jobs.cancel` (`jobs.py:513`) đặt `cancelled`
  + `credit.hoan` ngay. Handler đang chạy **chỉ dừng hợp tác**: lần `ctx.progress()` kế tiếp ném `JobCancelled`
  (`job_runner.py:115-116`), hoặc handler tự hỏi `ctx.is_cancelled()`. Không kill process. Handler ném bất cứ
  exception nào khi job đã `cancelled` ⇒ coi là huỷ, không `fail()` (`:671-676`). Trả kết quả khi đã huỷ ⇒ hoàn tiền, không complete (`:710-711`).
  ⇒ Với yt-dlp: trong `progress_hooks` gọi `ctx.is_cancelled()` rồi raise.
- **Exception → tiền** (`job_runner.py:653-700`, `_provider_failure_kind` `:729-753`):
  - `jobs.LoiNguoiGoi` (`jobs.py:54`) ⇒ `fail(retry=False)` → `error` + hoàn tiền (lỗi input của khách: URL hỏng, video private).
  - `jobs.DangBan(ly_do="", retry_after_s=None)` (`jobs.py:86,121`) ⇒ `defer_resource`: về hàng đợi, không tiêu lượt, không chạm tiền.
  - Exception khác ⇒ `fail(retry=True)`: còn lượt thì `queued` lại với giãn cách `10·2^(n-1)` giây, trần 600 s
    (`jobs.py:39-40, 532-573`); hold **giữ nguyên** giữa các lượt; hết lượt ⇒ `error` + `_hoan_credit` (`job_runner.py:694-696`).
  - Thành công ⇒ `jobs.complete` + `_quyet_toan_credit` (`:826-839`): giá thật = `result["credit_cost"]` nếu handler báo, không thì bằng số đã giữ.
  - Handler phải **ném** khi thất bại — trả êm ⇒ bị trừ tiền (`docs/03_THEM_APP_MOI.md:149-170`, chốt `tests/test_60_app_registry.py:558`).
- **Lease / mồ côi:** không có luồng heartbeat nền cho job (chỉ GPU lease có, `job_runner.py:458-465`). Heartbeat chỉ ghi ở
  `claim` (`jobs.py:368`) và `set_progress` (`jobs.py:490`). `ORPHAN_TIMEOUT = 5 phút` (`jobs.py:36`); `reclaim_orphans`
  (`jobs.py:574`) tính một lượt thử (attempts+1). ⇒ **Handler tải dài phải gọi `ctx.progress` < 5 phút một lần**, kể cả khi % không đổi.
- **Trần thời gian:** `RUNTIME_LIMIT_S = {"gpu": 7200, "ffmpeg": 7200, "browser": 1800, "api": 1800}`, mặc định 1800
  (`job_runner.py:66-68`). Lớp tài nguyên lấy từ `requires` theo thứ tự gpu > ffmpeg > browser > api
  (`platform_core/public_api/limits.py:295-302`). Ghi đè theo job_type: `AppManifest.max_runtime_s={"video_crawler.x": 3600}`
  (`registry.py:761`, `runtime_limit_for` `:879`). Hết giờ ⇒ `_het_gio` (`job_runner.py:547`): `fail(retry=False)`, hoàn tiền, **giết tiến trình worker**.

---

## 3. Sự kiện / tiến độ job

`platform_core/job_events.py`:
- `append(db, job, event_code, *, public_message="", details=None, level="info", visibility=CUSTOMER, event_key=None) -> JobEvent` (`:85`) — không commit; `event_key` là khoá idempotent theo job. `CUSTOMER="customer"`, `INTERNAL="internal"` (`:20-21`).
- `timeline(db, job_id, *, include_internal=False, limit=200) -> list[JobEvent]` (`:146`).
- `sanitize_text`, `error_fingerprint`, `redact_details` (`:43,51,60`).
- Handler không gọi trực tiếp — dùng `ctx.progress/event/stage`.

**Trang khách đọc trạng thái (có sẵn, lọc theo chủ):** `server/routes/jobs.py`
- `GET /jobs/{job_id}` (`:182`) — trang chi tiết (template `job_detail.html`), kèm danh sách tải kết quả.
- `GET /jobs/{job_id}/progress` (`:197`) — mẩu HTML `_job_progress.html` để poll; header `X-LTT-Job-Terminal: 1` khi kết thúc. `job_detail.html:21-27` poll bằng `fetch(dataset.pollUrl)`.
- `GET /api/jobs/{job_id}` (`:240`) — JSON `job_history.customer_payload(db, job, with_events=True, with_queue=True)`; `GET /api/jobs?app=<slug>` (`:215`).
- `GET /jobs/{job_id}/artifacts/{index}` (`:410`) — **tải tệp kết quả miễn phí cho app**: `_artifacts(result)` (`:34-57`) nhặt mọi khoá kết quả tên kết thúc `_key` (chuỗi) hoặc `_keys` (list) ⇒ đặt `result={"video_key": "..."}` là có nút tải kèm kiểm sở hữu, R2 thì redirect presigned.
- Trong app: thumbnail tự truy vấn `Job` theo `user_id + app_slug` (`apps/thumbnail/routes.py:102-133`).

---

## 4. Storage

`platform_core/storage.py`. Lấy backend: `get_storage() -> Storage` (`:500`); test thay bằng `set_storage(LocalStorage(path))` (`:525`).

| API (`class Storage`, `:61`) | Dòng |
|---|---|
| `put(key, stream: BinaryIO, content_type="application/octet-stream") -> StoredFile(key, size, content_type)` | :64, dataclass :40 |
| `open(key) -> BinaryIO` · `delete(key)` · `exists(key) -> bool` · `size(key) -> int` | :68-78 |
| `promote(staging_key, final_key, content_type=...) -> StoredFile` | :80 |
| `url_for(key, ttl_s=900)` / `try_url_for(...)` — presigned R2, Local trả `None` | :103, :141 |
| `put_url` / `try_put_url` — vé upload trực tiếp | :109, :151 |
| `local_path(key) -> str | None` (chỉ cho công cụ ngoài như ffprobe) | :116 |

- Worker ghi tệp: `with open(path, "rb") as f: get_storage().put(key, f, content_type="video/mp4")` — truyền file object, không `BytesIO(toàn bộ)` (mẫu `apps/auto_scan_video/features.py:797-799`).
- Route phục vụ cho chủ: mẫu `apps/thumbnail/routes.py:408-429` — kiểm `segs[0]==<prefix> and segs[1]==u.id`, rồi `try_url_for` → redirect, không thì `StreamingResponse(storage.open(key))`. Linter cảnh báo route `{key:path}` không kiểm `u.id|user_id|segs[1]` (`tools/lint_app_contract.py:515-517`). Hoặc bỏ route riêng và dùng `/jobs/{id}/artifacts/{i}` (mục 3).
- Quy ước khoá: `<app>/<owner_id>/...` (`thumbnail/<uid>/refs/<uuid>`, `thumbnail/routes.py:341`; `asv/<uid[:16]>/nguon/<uuid>.mp4`, `auto_scan_video/features.py:795`). `_safe_key` (`storage.py:181`) cấm `..`, `:`, `~`.
- Giới hạn: `CLOUDFLARE_BODY_LIMIT = 100 MiB` (`storage.py:34`) cho body request (không áp cho worker ghi). upload_sessions: 20 phiên, 2 GiB đang chờ, 12 vé/phút (`platform_core/upload_sessions.py:28-30`).
- `LTT_STORAGE=r2` ⇒ R2, lỗi cấu hình ⇒ fallback Local; `LTT_STORAGE_LOCAL_PREFIXES="voice/, ..."` định tuyến tiền tố về đĩa (`storage.py:461-522`). (Memory dự án ghi bucket R2 có lifecycle tự xoá ~7 ngày ngoài app — kiểm lại trước khi hứa lưu lâu.)

---

## 5. Media asset / đầu vào của auto_scan_video

- `platform_core/media.py` **không** phải thư viện asset: chỉ tiện ích ffmpeg (`ffmpeg_bin :58`, `probe :92`, `duration_seconds :137`, `run_with_progress :200`, `MediaError :29`).
- **Không có miền "media library" dùng chung.** `asv_asset` là bảng riêng của ASV (`alembic/versions/20260901_1930_asv_asset.py`).
- ASV nhận nguồn qua `POST /auto-scan-video/tao` (`apps/auto_scan_video/routes.py:294`) với **một trong hai**:
  - `upload_id` = id `UploadSession` của `app_slug="auto_scan_video"` → `features.tao_run_tu_ve` (`features.py:578`):
    `upload_sessions.owned(db, session_id, user_id, app_slug=SLUG)` → `confirm` (kiểm kích thước + magic `ftyp`) → `nhap_media.soi/kiem_chinh_sach` → `kho.promote(staging, "asv/<uid[:16]>/nguon/<uuid>.mp4")` → `tao_run(source_key=...)`.
  - `video: UploadFile` multipart → `tao_run_tu_tai_len` (`features.py:745`).
  - Kiểu nhận: `("video/mp4","video/quicktime","video/x-m4v")`, trần 2 GiB (`features.py:537,541`). Route bị cờ env `LTT_AUTO_SCAN_VIDEO=1` chặn (404) (`routes.py:62-76`).
- ASV **không nhận storage key hay URL** từ khách. `APP_DUOC_DUNG_APP` (`tools/lint_app_contract.py:85`) không có cạnh `video_crawler → auto_scan_video` ⇒ không import được.
- **Đường khả thi không cần import:** worker video_crawler tạo `upload_sessions.create(db, user_id=<chủ>, app_slug="auto_scan_video", filename, content_type="video/mp4", expected_size, max_size, allowed_types)` (`upload_sessions.py:75`, staging key `staging/<uid>/<app_slug>/<id>/payload.mp4`), `storage.put(session.staging_key, f)`, rồi UI dẫn khách tới ASV với `upload_id`. ⚠️ Đây là ghép nối qua chuỗi slug — cần quyết định kiến trúc (hoặc bổ sung hợp đồng ở `platform_core`, hoặc khai cạnh mới + bề mặt `BE_MAT_CONG_KHAI` ở ASV). Chưa có tiền lệ.

---

## 6. Bảng riêng của app

- Khai `table_prefix="vc"` (hoặc tương tự) trong manifest (`registry.py:736`) + tạo `apps/<slug>/tables.py` dùng `from platform_core.db import Base` (mẫu `apps/auto_scan_video/tables.py:36-45`, SQLAlchemy 2 `Mapped/mapped_column`).
- `registry.load_app_tables()` (`registry.py:1620`) import mọi `tables.py`; có `tables.py` mà thiếu prefix hoặc bảng không bắt đầu bằng `<prefix>_` ⇒ `RegistryError`. Prefix trùng ⇒ từ chối (`:1505-1511`).
- Alembic: `alembic/env.py:26,30` gọi `load_app_tables()`; `target_metadata = Base.metadata` (`:54`). Migration **viết tay/`--autogenerate` rồi đọc lại** trong `alembic/versions/` (101 tệp, cùng một chuỗi với nền tảng). Mẫu app: `alembic/versions/20260901_1800_asv_run_va_stage.py`. Head hiện tại: `20260919_1000_llm_waiters_so_do.py` `revision="e4a19c07b5d2"` (kiểm lại trên `main` trước khi đặt `down_revision`). Phải có `downgrade()` (`alembic/README.md`). Test một head: `tests/test_103_autosub_projects.py:140-144`.
- App **không** tự `create_all` (`platform_core/db.py:16-17`).
- ⚠️ **Bảng mới phải có hàng trong `platform_core/public_api/governance.py` `STORES`** (`Store(table, klass, retention_days, readable_by, reason, purged_by)`, `:69-87`; mẫu ASV `:487-499`) hoặc `NOT_CUSTOMER_DATA` — chốt `tests/test_211_data_governance.py:176-188`, và `tests/test_390_dieu_khoan_api.py:166`. Đây là sửa một tệp `platform_core` (luật 9: phải nêu lý do). Tên bảng chứa slug được `test_60` bóc ra trước khi dò (`tests/test_60_app_registry.py:433-464`).
- DB session trong handler / ngoài request: `platform_core.db.get_session()` là **generator** (`db.py:159`), không commit:
  ```python
  gen = get_session(); db = next(gen)
  try: ...; db.commit()
  finally:
      try: next(gen)
      except StopIteration: pass
  ```
  (mẫu `thumbnail/routes.py:109-133`; `job_runner._one_session` `:181` là bản riêng tư của runner). Không có `core_db.session`.

---

## 7. Năng lực `browser` và bí mật theo người dùng

- `requires` (`registry.py:569-576`): `"api"|"ffmpeg"|"gpu"|"browser"` (browser = trình duyệt + IP dân dụng). **Chưa app nào khai `requires=("browser",)`** (grep `apps/` rỗng); chỉ công cụ soak `tools/h26_queue_soak.py:30`.
- Worker nhận năng lực qua **env `LTT_WORKER_POOLS`** (`job_worker.py:84-132`), vd `"api:8, gpu:2, browser:1"`; mỗi làn = `{"api"} ∪ tên` (`:124`), `a+b` gộp năng lực. **Không đặt ⇒ một làn đa năng `None` nhặt MỌI job** (`:108-109`) — tức production máy A hiện nhặt cả job browser. `jobs.claim` lọc app theo `set(manifest.requires) ⊆ capabilities` (`jobs.py:242-252`). Đặt pool mà thiếu làn khớp ⇒ job nằm `queued` mãi không báo (`job_worker.py:59-81`, `setup/4-nghiem-thu.ps1:68-78` chỉ kiểm `voice`).
- Không có máy nào "quảng bá" browser — không có đăng ký năng lực theo máy; chỉ env của tiến trình worker.
- Trần runtime browser: 1800 s (`job_runner.py:66`). yt-dlp có ghép ffmpeg ⇒ cân nhắc `requires=("ffmpeg",)` (trần 7200 s) hoặc `max_runtime_s`.
- **Bí mật mã hoá:** `platform_core/secretbox.py` — `ma_hoa(plaintext: str) -> str` (`:55`), `giai_ma(token: str) -> str` ném `SecretBoxError` (`:62`), `preview(plaintext) -> "...abcd"` (`:70`). Fernet, khoá dẫn xuất từ `LTT_TOKEN_ENCRYPTION_KEY` + salt `ltt_api_key_salt_v1_2026` (`:29,36-52`). Là lớp mã hoá thuần, **không có bảng lưu theo user** — app tự lưu chuỗi đã mã hoá trong bảng riêng. Người dùng hiện tại: `api_keys.py`, `nexus/sessions.py`, `public_api/delivery.py` (không app nào). ⚠️ Salt dùng chung với kho API key — muốn tách khoá cho cookie nền tảng thì phải bổ sung ở `platform_core`.
- Tiền lệ yt-dlp trong kho: `cutclipshort/adapters/downloader.py` — `download(url, output_dir: Path, progress_callback=None, cancel_flag: list|None=None) -> Path` (`:214`), `extract_info(url) -> dict` (`:118`), `detect_source` (`:66`), `DownloadError` (`:43`); đang dùng bởi `apps/taoclipngan`. `yt-dlp>=2026.3.17,<2027.0` đã có trong `requirements-server.txt:20`.

---

## 8. Credit & ràng buộc manifest

- `credit_cost` trả **0 là hợp lệ**: `submit_with_credit` bỏ qua giữ chỗ khi `estimate == 0` (`job_submit.py:77`), quyết toán bỏ qua khi không có hold (`job_runner.py:836-837`). Tiền lệ: `apps/autosubvideo/manifest.py:15-24` (miễn phí theo quyết định Q50). Chỉ cấm `credit_cost=None` khi có `job_types` (`registry.py:1482-1485`; lint `credit_cost\s*=\s*None` = ERROR). `credit_for` raise nếu job_type không ai nhận (`registry.py:1730-1745`). Miễn phí là quyết định sản phẩm — ghi lý do.
- Hằng số hợp lệ: `APP_SURFACES={"customer","admin","runtime"}`, `APP_LIFECYCLES={"released","development","maintenance","internal","retired"}` (`registry.py:76-79`). Mặc định: `requires=("api",)`, `enabled=True`, `public=True`, `surface="customer"`, `lifecycle="development"`, `catalog_parent=""` (`registry.py:576-638`).
- `_validate` (`registry.py:1423-1516`): slug `[a-z0-9_]`, `route_prefix` bắt đầu `/` và duy nhất, `capabilities` là tuple chuỗi không rỗng, `catalog_parent` hợp lệ, job_type duy nhất toàn hệ, `so_lan_thu` trỏ job_type của app.
- `tests/test_60_app_registry.py`:
  - `:57` không app nào nạp lỗi; lint yêu cầu slug == tên thư mục.
  - `:62-72` mọi app `surface="customer"` **không có `catalog_parent`** phải có `capabilities` không rỗng (áp cả app `enabled=False`).
  - `:75-102` app `visible_on_surface(authenticated=True)` mà không có router ⇒ đỏ. `visible_on_surface` (`registry.py:1540`): `runtime` hoặc có `catalog_parent` ⇒ ẩn.
  - `:242-250` app `enabled` phải có mục nav (tự sinh từ `route_prefix` nếu `nav=()`).
  - `:396` platform_core không được chứa slug app.
- **`enabled=False` KHÔNG chặn gì ngoài hiển thị**: nav/catalog lọc `enabled` (`server/templating.py:308,472`, `server/routes/dashboard.py:239,262`), nhưng `mount_all` gắn router bất kể `enabled` (`registry.py:1667-1673`, xem chú thích `tests/conftest.py:329-330`) và `jobs.claim` không xét `enabled`. ⇒ Muốn khoá thật dùng cờ env trả 404 như ASV `_cong_co` (`apps/auto_scan_video/routes.py:62-76`, đặt `Depends` TRƯỚC `require_login`).
- Khai tối thiểu cho app đang xây, ẩn: `slug="video_crawler", display_name, route_prefix="/video-crawler", job_types=(...), credit_cost=<fn>, requires=(...), enabled=False, public=False, lifecycle="development", capabilities=("video",)` (+ `surface="customer"` mặc định). ASV đang mở thử: `enabled=True, public=False, lifecycle="development"` (`apps/auto_scan_video/manifest.py:9-12`).
- Lint (`tools/lint_app_contract.py:373-548`): có `job_types` ⇒ phải có `jobs.py` chứa `def handle`; routes phải dùng `require_login|require_operator`; có `@router.post` mà không `verify_csrf_token` ⇒ WARN; `routes.py` > 900 dòng / 30 handler ⇒ WARN; import `server.*` chỉ 4 module (`:57-62`).

---

## 9. Test

- Tệp: `tests/test_<số>_<ten>.py`. `tools/check_so_test.py` **chỉ chặn trùng số** (mốc tập số trùng ở `tools/check_so_test.moc`, `--list` in số trống) — **không** có bảng cấp dải. Sổ tạm dải ở memory dự án (`dai-test-cap-cho-tung-chuong-trinh.md`, dừng ở 11/09). Đo 22/09: `main` dùng tới 1708 (17xx = lỗi LLM); nhánh local dùng thêm `1850`; **dải 1900–1999 trống trên `main` và mọi nhánh local** ⇒ đề xuất `1900–1919` cho video_crawler (kiểm lại `git ls-tree -r --name-only main -- tests/` trước khi tạo).
- `tests/conftest.py` chỉ có 2 fixture: **`app_thu`** (`:292`, app tổng hợp slug `appthu`, job `appthu.dao_nguoc`, có route `/appthu` + `/appthu/queue`) và `gpu_khong_claim_toan_may` (`:447`); helper `bao_dam_user(db, user_id)` (`:360`). **Không có fixture `db`/`client` dùng chung** — mỗi tệp tự dựng.
- Fixture DB chuẩn (`tests/test_67_hang_doi_job.py:24-35`): `LTT_DATABASE_URL=sqlite:///<tmp>/j.db` → `dbmod.reset_engine()` → `import platform_core.models` → `Base.metadata.create_all(get_engine())` → `next(get_session())`. App có `tables.py` phải `load_app_tables()` **trước** `create_all` (`tools/agent_browser_server.py:18-21`).
- Client đăng nhập (`tests/test_69_web_jobs.py:14-49`): thêm env `LTT_ENV=development`, `LTT_SESSION_SECRET`, `LTT_ADMIN_USERNAME`; tạo user `platform_core.users.tao_nguoi_dung(s, email=, password=, is_verified=True)`, nạp `credit.nap(s, uid, 100)`; `TestClient(server.app.create_app(), base_url="https://testserver")`; đăng nhập = lấy `csrf_token` từ `GET /login` rồi `POST /login` (`:52-57`).
- Storage test: `set_storage(LocalStorage(str(tmp_path/"store")))` … `set_storage(None)` (`tests/test_71_thumbnail.py:27-35`). ctx giả: lớp có `job_id` + `progress()` (`:38-43`).
- **Ví dụ nộp + chạy handler thật** (`tests/test_67_hang_doi_job.py:246-261`):
  ```python
  def test_chay_tron_mot_job(db, monkeypatch, app_thu):
      from platform_core.job_runner import _chay_mot_job
      j = _submit(db, params={"text": "xin chao"})     # jobs.submit(...) + commit
      assert _chay_mot_job("w-test") is True             # claim → handler(params, JobContext) → complete
      db.expire_all(); job = db.get(Job, j.id)
      assert job.status == JOB_DONE and job.result["output"] == "oahc nix"
  ```
  Với app thật, `resolve_handler` import `apps.<slug>.jobs` qua registry — không cần `app_thu`. Huỷ ở checkpoint: `:152-162`.
- Chạy: `python tools\thanh_phan.py --test app:<slug>` rồi `python -m pytest <tệp> -q` (`docs/03_THEM_APP_MOI.md:236-243`).

---

## 10. Template

- Nền: `{% extends "base.html" %}` (`server/templates/base.html`); block: `title` (:9), `body_class` (:89), `page_mode` (`standard`/`wide`, :120), `topbar_title`/`topbar_right` (:124-125), `content` (:129), `scripts` (:134). Macro: `_app_head.html` (`import "_app_head.html" as ah`), `_ui.html`. Mẫu: `apps/thumbnail/templates/thumbnail.html:1-6`.
- Template app nằm ở `apps/<slug>/templates/`, nạp qua `ChoiceLoader` (`server/templating.py:264-272`); **`server/templates/` thắng khi trùng tên, mọi app chung một không gian tên** ⇒ đặt tên riêng (`video_crawler.html`, `vc_*.html`).
- Render: `templates.TemplateResponse(request, "<ten>.html", {"user": user, "nav": MANIFEST.slug, "app": MANIFEST, "csrf_token": issue_csrf_token(request), ...})` (`apps/thumbnail/routes.py:92-100`).
- CSRF: `issue_csrf_token(request) -> str` (`server/auth/csrf.py:19`), `verify_csrf_token(request, submitted_token) -> bool` (`:28`); form `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`, route nhận `csrf_token: str = Form(...)`. Global template `_csrf_token` cũng có (`server/templating.py:441`).
- HTMX: **không nạp sẵn trong base**; trang tự thêm `<script src="/static/htmx.min.js?v={{ asset_ver }}"></script>` (vd `apps/auto_scan_video/templates/asv_chi_tiet.html:11`). Nhận biết request HTMX: header `HX-Request: true` (`thumbnail/routes.py:89-90`).
- Cache-bust: global `asset_ver` (`server/templating.py:143-144`), tính từ danh sách tệp tĩnh ở `:36-98`; **thêm tệp static mới phải thêm vào danh sách đó** (chốt `tests/test_369_asset_ver_day_du.py`) và đổi `ASSET_VER` cần khởi động lại service.
