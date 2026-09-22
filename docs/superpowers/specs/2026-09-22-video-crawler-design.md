# Video Crawler (CÀO NGAY) Migration Design Spec

> **Tạo**: 22/09/2026  
> **Phiên bản**: 1.0 (draft)  
> **Chủ dự án review**: CHỜ  

---

## 1. Problem Statement

ViralCrawl ("CÀO NGAY") đang chạy desktop (Windows + Electron) với license **NON-COMMERCIAL LEARNING** của MediaCrawler. Cần di trú sang LTTSTUDIOSAPP — nền tảng SaaS internet đa người dùng — để:
- Hỗ trợ đa user, persistent state, multi-worker
- Tận dụng hạ tầng LTT: jobs, credit, storage, auth, observability
- Giải quyết vấn đề license restrictive của MediaCrawler (không được dùng thương mại)

**Yêu cầu**: Tạo app `video_crawler` native trong LTT, không import code runtime từ Viral, không iframe, không chạy backend Viral song song.

---

## 2. Source Audit Summary

### 2.1 ViralCrawl CÀO NGAY (DONOR)

**UI Features (KB-CHUC-NANG.md)**:
- **Nền tảng**: Douyin, Bilibili, Xiaohongshu, RedNote, YouTube, TikTok, Facebook
- **3 cách cào**: Theo từ khóa (search, sort, time filter), Theo link (resolve & preview), Theo kênh (channel crawl)
- **UI controls**: Xem trước & chọn, Cào hết, Thêm vào hàng đợi, Dừng, Gợi ý, Lướt (browser), Cào không trùng
- **Automation**: Theo dõi kênh, Automation (scheduled crawl), Hẹn giờ cào
- **History**: Lịch sử cào, File đã tải, Đã render

**Platform Adapters Detected** (via grep):
- media_platform/douyin, bilibili, xhs, ks, weibo, tieba, zhihu
- (Weibo, Twitter/X, Instagram, Reddit, Threads: "đang ẩn")

**Architecture Patterns**:
- Desktop: task queue in memory, progress state global, history file-based
- Browser management: QR login for Douyin/Bilibili/XHS/RedNote; direct for YouTube/TikTok/Facebook
- Download: yt-dlp + local file storage
- Dedup: `_dang_cao`, `_crawl_kq` — global process state

**Critical Finding**: ViralCrawl uses **MediaCrawler** (github.com/NanmiCoder/MediaCrawler) with license:
> "NON-COMMERCIAL LEARNING 1.1" — **explicitly forbids commercial use**

### 2.2 LTTSTUDIOSAPP (TARGET)

**App Contract (03_THEM_APP_MOI.md)**:
- Thêm app = thêm thư mục trong `apps/`
- CẤM sửa `platform_core/` hoặc `server/`
- Job dài → hàng đợi, không đồng bộ trong request
- `requires=("api",)` | `"ffmpeg"` | `"gpu"` | `"browser"`

**Platform Capability Model (platform_core/registry.py)**:
- Dynamic discovery: scan `apps/*/manifest.py` at runtime
- No hardcoding of app names in imports
- `AppManifest` = metadata only (slug, display_name, job_types, requires, credit_cost)

**Job Model (platform_core/jobs.py)**:
- Single table: `jobs` (id, user_id, app_slug, job_type, params, dedupe_key, status, admission_resource, progress, result, event_sequence)
- Lifecycle: credit.giu_cho → jobs.submit → worker.claim → handler.run → credit.quyet_toan
- User isolation: `owner_id` filter, never trust client IDs

**Progress & Events (platform_core/job_events.py)**:
- `job_events.append(db, job, event_type, public_message, visibility="customer|internal")`
- 365-day retention (customer), 30-day (internal)

**Storage Model (platform_core/storage.py)**:
- Browser→storage direct upload (H10/P1): `storage.put_url(key)`
- Presigned URLs for download: `storage.url_for(key)`

**Multi-User Isolation (AGENTS.md §8)**:
- App can only use 4 modules: `deps`, `auth.session`, `auth.csrf`, `templating`
- No app→app imports
- `tables.py` for app-specific DB

---

## 3. Approaches

### APPROACH A — Native LTT Monolithic Customer App

**Description**:  
Create native LTT app with monolithic service layer. All logic (crawler, resolver, downloader, dedup, metadata, browser management) in `apps/video_crawler/services/`.

**Architecture**:
```
video_crawler UI
    ↓
CrawlApplicationService (monolithic)
    ↓
platform_core/jobs
    ↓
video_crawler/service_crawler.py (all logic)
    ↓
platform_core/storage
```

**Pros**:
- Simple, single team ownership
- No hidden execution boundaries
- Easy rollback

**Cons**:
- **Browser/cookie management**: Must use `requires=("browser",)` → LTT Web → Job → Browser worker (local/residential IP)
- Single process bottleneck: no parallel browser sessions per user
- Complex anti-bot handling in one process
- License compliance: MediaCrawler code cannot be copied

**Decision**: Not recommended due to complexity of browser worker routing and license restrictions.

---

### APPROACH B — Native Customer App + Capability-Specific Hidden Executors (RECOMMENDED)

**Description**:  
Native LTT app with capability-split architecture:
- `api` capabilities: HTTP/API workers (YouTube, Facebook)
- `browser` capabilities: Residential browser workers (Douyin, Bilibili, XHS)

**Architecture**:
```
video_crawler UI (LTT Web)
    ↓
CrawlApplicationService
    ↓
platform_core/jobs
    ↓
┌──────────────────┬──────────────────┐
│ API Worker       │ Browser Worker   │
│ (HTTP/API only)  │ (Residential IP) │
└────────┬─────────┴────────┬─────────┘
         ↓                  ↓
   PlatformAdapters    PlatformAdapters
         ↓                  ↓
      CrawlItem           CrawlItem
         ↓                  ↓
   platform_core/storage
```

**Capabilities**:
| Capability | Workers | Platforms | Anti-Bot Strategy |
|------------|---------|-----------|-------------------|
| `api` | HTTP worker | YouTube, Facebook | Public API or simple headers |
| `browser` | Residential browser worker | Douyin, Bilibili, XHS, Kuaishou, RedNote | QR login, cookie isolation per user |

**Pros**:
- ✅ Matches LTT's existing `requires=("browser",)` contract
- ✅ Browser workers run at residential IPs (better anti-bot protection)
- ✅ Multiple concurrent sessions per user
- ✅ Clean separation: HTTP vs browser logic
- ✅ License compliance: no MediaCrawler code copy

**Cons**:
- Requires browser worker infrastructure (exists in LTT via `apps/bot` legacy, may need review)
- Two worker types = more complexity

**Decision**: **RECOMMENDED** — best fit for LTT's capability model and license requirements.

---

### APPROACH C — Legacy Viral Service Wrapper/Proxy

**Description**:  
Run Viral desktop backend as separate service, proxy requests from LTT app.

**Architecture**:
```
video_crawler UI (LTT Web)
    ↓
HTTP API Gateway
    ↓
Forward to Viral Desktop (localhost:8000)
    ↓
Viral Backend (unchanged)
```

**Pros**:
- Zero migration effort
- 100% feature parity instantly
- No license audit needed (Viral still owned)

**Cons**:
- ❌ **Violates LTT contract**: CẤM import chéo hai repo
- ❌ Viral must stay running as separate process
- ❌ Desktop license still applies
- ❌ Single desktop instance → no multi-user isolation
- ❌ Cookie state shared across all users
- ❌ Cannot scale beyond one desktop machine
- ❌ Cloudflare 100s timeout → long crawls break

**Decision**: **REJECT** — violates LTT app contract, no real migration.

---

## 4. Target Architecture (APPROACH B)

### 4.1 App Boundary

```
apps/video_crawler/
├── manifest.py              # App metadata
├── routes.py                # Web routes (require_login, CSRF)
├── jobs.py                  # Handler (runs in worker)
├── templates/               # HTML templates
├── features.py              # Business logic (crawler, resolver, downloader, dedup, metadata)
└── adapters/
    ├── base.py              # Platform adapter contract
    ├── douyin.py
    ├── bilibili.py
    ├── xhs.py
    ├── ks.py
    ├── youtube.py
    ├── facebook.py
    └── ...
```

### 4.2 Platform Capability Registry (Single Source of Truth)

```python
from platform_core.registry import CapabilityRegistry

# Define in platform_core/registry.py (additive, not hardcode)
VIDEO_CRAWLER_CAPABILITIES = [
    Capability(
        id="video_crawler.douyin",
        slug="douyin",
        display_name="Douyin",
        requires=("browser",),
        login_required=True,
        login_type="qr_code",
        search=True,
        link=True,
        channel=True,
        collection=False,
        preview=True,
        dedup=True,
    ),
    Capability(
        id="video_crawler.youtube",
        slug="youtube",
        display_name="YouTube",
        requires=("api",),
        login_required=False,
        search=True,
        link=True,
        channel=True,
        preview=True,
        dedup=True,
    ),
    # ... etc
]
```

### 4.3 Job Model

```python
Job:
    id              UUID
    user_id         FK(User)
    app_slug        "video_crawler"
    job_type        "video_crawler.crawl" | "video_crawler.search" | "video_crawler.resolve"
    params          JSON (platform, query, limit, filters)
    dedupe_key      SHA256(job_type||sorted_params)
    status          QUEUED | RUNNING | DONE | CANCELLED | ERROR
    admission_resource | "api" | "browser"
    progress        0-100
    result          JSON
    event_sequence  JSONB array
```

### 4.4 Executor Types

| Type | Requires | Platforms | Location |
|------|----------|-----------|----------|
| API Worker | `api` | YouTube, Facebook | `worker.py` (HTTP pool) |
| Browser Worker | `browser` | Douyin, Bilibili, XHS, Kuaishou, RedNote | Residential browser profiles, cookie isolation |

### 4.5 Platform Adapter Contract

```python
class PlatformAdapter:
    async def search(self, query: str, platform: str, **kwargs) -> list[CrawlItem]
    async def resolve(self, url: str, platform: str) -> CrawlItem | None
    async def list_channel(self, channel: str, platform: str) -> list[CrawlItem]
    async def preview(self, item: CrawlItem) -> bytes
    async def download(self, item: CrawlItem) -> StoragePath
    async def normalize(self, item: CrawlItem) -> NormalizedItem
```

### 4.6 Storage & Output

- **Source**: `storage.put_url("video_crawler/sources/{run_id}/video.mp4")`
- **Output**: `storage.url_for("video_crawler/results/{run_id}/output.mp4")`
- **Dedup**: `dedupe_key = SHA256("video_crawler.crawl" + sorted(json.dumps(params)))`

### 4.7 Progress & Events

```python
# In handler
ctx.progress(10, "Starting search...")
ctx.progress(50, "Downloading...")

# Events
job_events.append(db, job, "crawl_started", 
    public_message="Đang bắt đầu...",
    visibility="customer")

job_events.append(db, job, "dedup_skipped",
    public_message="Bỏ video trùng",
    visibility="customer")
```

---

## 5. First Vertical Slice: YouTube (Public, API-Only)

**Rationale**:
- No QR login
- No browser worker needed
- Easiest E2E test path

**Flow**:
1. User submits search query (keyword + limit + sort)
2. Submit job: `video_crawler.search` with `{"platform": "youtube", "query": "...", "limit": 10}`
3. API Worker claims job (admission_resource="api")
4. Adapter searches YouTube → resolves URLs → downloads via yt-dlp
5. Progress updates → result stored
6. UI shows history & download

**Success Criteria**:
- Job completes within 30 seconds
- No credit charged (YouTube is public)
- Dedup works
- UI shows correct progress

---

## 6. Browser Platform Example: Douyin (QR Login)

**Flow**:
1. User selects Douyin → "Đăng nhập" button
2. Submit job: `video_crawler.login` with `{"platform": "douyin", "cookie": "user_id=123"}`
3. Browser Worker claims job
4. Worker runs Playwright: QR scan → cookie extract → save to `platform_core/storage` (encrypted)
5. User confirms → session persisted
6. Subsequent crawls: cookie loaded from storage

**Security**:
- Cookies encrypted in storage
- Per-user cookie directory
- Session health checks: `adapter.check_session()`

---

## 7. License & Provenance

**MediaCrawler**: NON-COMMERCIAL LEARNING 1.1 — **CANNOT COPY**
- **Decision**: WRAP behavior only, no code copy
- **Adapter logic**: Reimplement from scratch based on behavior
- **Dependencies**:
  - `yt-dlp`: GPL-3.0 (allow commercial, but derivative works may need GPL)
  - `playwright`: MIT (OK)

**Plan**:
- Use `yt-dlp` as external tool (preserved in repo, licensed separately)
- Reimplement all platform adapters from behavior spec

---

## 8. UI Information Architecture

### 8.1 Main Page (Home)
- Platform selector (card/grid)
- Search input (query, limit, sort, time filter)
- "Cào ngay" button → submit job

### 8.2 Platform Login Modal
- QR code display (for browser platforms)
- Cookie paste field (legacy fallback)
- "Đăng nhập" → submit login job

### 8.3 Job Status Page
- Progress bar
- Activity log (HTMX poll)
- Cancel button
- Preview thumbnail

### 8.4 Results Table
- Checkboxes (select/deselect)
- "Cào hết" → add selected to queue
- "Thêm vào hàng đợi" → queue
- "Dừng" → cancel
- "Cào không trùng" → dedup option

### 8.5 History Library
- List of completed crawls
- Filter by platform/date
- Download links
- Preview thumbnails

---

## 9. Testing Strategy

| Level | Command | Scope |
|-------|---------|-------|
| L1 (unit) | `python -m pytest apps/video_crawler/tests/ -q` | Features, adapters, dedup |
| L2 (integration) | `python tools\gate.py --pham-vi video_crawler` | Job submission, storage |
| L3 (full) | `python tools\gate.py` | End of phase |

**Characterization Tests (from Viral behavior)**:
- URL normalization for each platform
- Search result count per platform
- Dedup key collision detection
- Cookie/session health check

---

## 10. Migration Phases

| Phase | Deliverable | Test Gate |
|-------|-------------|-----------|
| 01 | App skeleton + manifest | `test_60_app_registry` |
| 02 | Platform registry + capability model | `platform_core` lint |
| 03 | Job submission + progress events | L2 |
| 04 | YouTube adapter E2E | L2 + browser check |
| 05 | Storage integration (put_url, url_for) | L2 |
| 06 | Preview/select + queue + dedup | L2 |
| 07 | Browser worker infrastructure review | L2 |
| 08 | Douyin adapter E2E | L2 + browser check |
| 09 | Remaining platform adapters | L2 |
| 10 | UI parity + responsive | Browser test |
| 11 | History library + source library | L2 |
| 12 | Integration with downstream apps | L2 |
| 13 | Multi-user QA + concurrency | L2 |
| 14 | Parity audit vs Viral (feature matrix) | L2 |
| 15 | Documentation + release | L3 |

---

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Browser worker infrastructure missing | HIGH | Audit `apps/bot` legacy; if missing, add capability before porting browser platforms |
| Cookie security requirements unclear | MEDIUM | Follow LTT's `platform_core/secret.py` pattern |
| yt-dlp GPL-3.0 implications | MEDIUM | Legal review; consider custom wrapper |
| Anti-bot detection at scale | HIGH | Browser workers must use residential IPs (LTT contract) |

---

## 12. Definition of Done

- ✅ Native LTT app (no Viral dependencies)
- ✅ Multi-user safe, persistent jobs
- ✅ Platform capability registry single-source
- ✅ At least one public platform (YouTube) E2E
- ✅ Browser platform (Douyin) E2E if in scope
- ✅ License audit passed
- ✅ L3 gate green (or L2 if deploy-ready)
- ✅ Parity report ≥ 90% of Viral features in scope

---

## 13. Deferred Scope

| Feature | Reason |
|---------|--------|
| Automation/scheduler | Deferred to LTT job scheduler |
| Clone voice/voice API | Not in CÀO NGAY scope |
| Băm nhỏ (clip cutting) | Separate feature |
| Đăng bài (social post) | Not in scope |

---

## 14. Rollback Strategy

- `apps/video_crawler/` deletion if deploy fails
- No database migration scripts (no schema changes)
- App disabled via `manifest.enabled=False`

---

## 15. Next Steps (After Approval)

1. Invoke `superpowers:writing-plans`
2. Create worktree: `python tools\cay_rieng.py tao video-crawler-design`
3. Implement task-by-task per plan
4. TDD with characterization tests
5. Parity audit after each major feature

---

**=== GATE CHỜ CHỦ DỰ ÁN ===**

**Spec**: `docs/superpowers/specs/2026-09-22-video-crawler-design.md`

**Khuyến nghị kiến trúc**: **APPROACH B** — Native customer app + capability-specific hidden executors (API workers + Browser workers)

**Số phase dự kiến**: **15 phases** (01–15), mỗi phase có gate riêng

**Rủi ro lớn nhất**: 
1. Browser worker infrastructure missing (khả năng cao sẽ phải tạo mới)
2. License compliance (MediaCrawler restrictive, yt-dlp GPL-3.0 implications)

**Nếu đồng ý triển khai**, chủ dự án trả lời: **CHỐT TRIỂN KHAI**

**=== END GATE ===**
