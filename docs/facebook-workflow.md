# Facebook Publish Workflow — End-to-End

> Complete reference for the Facebook publish job lifecycle, from sheet row
> → public Page video → optional comment. Mirrors `docs/tiktok-workflow.md`
> structure for cross-platform parity.

---

## 🗺 Full pipeline diagram

```
JOB INTAKE              TOKEN + PAGE              RATE LIMIT
┌──────────┐  task    ┌──────────────┐  ok    ┌─────────────────┐
│  Excel   │ ───────▶ │  TokenStore  │ ─────▶ │  RateLimiter    │
│  row     │          │  .find_page_ │        │  .acquire(page) │
└──────────┘          │  by_name     │        └────────┬────────┘
                      └──────────────┘                 │ ok
                                                       ▼
                                          ┌──────────────────────────┐
                                          │ Upload dispatch          │
                                          │ ├─ feed  → GraphUploader │
                                          │ └─ reels → ReelsUploader │
                                          └────────────┬─────────────┘
                                                       │
                                                       ▼
                                          ┌──────────────────────────┐
                                          │ Multi-phase upload       │
                                          │  start → transfer chunks │
                                          │  → finish + metadata     │
                                          └────────────┬─────────────┘
                                                       │
                                                       ▼
                                          ┌──────────────────────────┐
                                          │ Post-upload extras       │
                                          │  • Thumbnail (optional)  │
                                          │  • Verify status         │
                                          └────────────┬─────────────┘
                                                       │
                                                       ▼
                          ┌────────────────────────────────────┐
                          │ STAGE 7: comment (NEW design)      │
                          │ POST /{video_id}/comments          │
                          │ FacebookCommenter — graceful fail  │
                          │ (NEVER breaks publish success)     │
                          └────────────────┬───────────────────┘
                                           │
                                           ▼
                                  ┌────────────────┐
                                  │ Update Excel + │
                                  │ Audit log      │
                                  └────────────────┘
```

---

## 📋 Stage-by-stage reference

### Stage 0 — Job Intake
| Source | Function | Notes |
|--------|----------|-------|
| Batch (Excel) | `core/sheet_runner.py:_tick()` | One row → upload_task |
| Manual (GUI) | `gui/operation_tab.py:_start()` | Direct UploadEngine call |
| API | `FacebookPublisher.publish(task)` | Used by sheet runner via registry |

### Stage 1 — Token + Page Resolution
**Function**: `UploadEngine._run_inner(task)` → `get_default_store().find_page_by_name(page_name)`
- Returns `(AccountInfo, PageInfo)`
- `PageInfo.access_token` = page-level OAuth token used for upload + comment
- Raises `TokenNotFoundError` if page not in token store

### Stage 2 — Token Freshness
**Function**: `account.is_token_valid()` (60s buffer)
- Token TTL: ~60 days for long-lived page tokens
- Raises `TokenExpiredError` if expired → user must reconnect

### Stage 3 — Rate Limiting
**Function**: `RateLimiter.acquire(page.name, stop_event)`
- Enforces `min_interval_per_page_s` between uploads per page
- Configurable max concurrent uploads per page

### Stage 4 — Upload Dispatch
| `post_type` | Uploader | Endpoint |
|------------|----------|----------|
| `feed` (default) | `GraphUploader` | `POST /{page_id}/videos` (3-phase) |
| `reels` | `ReelsUploader` | Reels API (separate flow) |

### Stage 5 — Multi-phase Video Upload (feed)
**Function**: `GraphUploader.upload(task)`
1. **Start**: `POST /{page_id}/videos?upload_phase=start&file_size=N` → session_id + video_id
2. **Transfer**: chunks 8MB with retry per chunk
3. **Finish**: `?upload_phase=finish` + title/description/keywords/schedule

### Stage 6 — Post-upload Extras
- Thumbnail upload (optional, fails gracefully)
- Verify `status.video_status == ready` (configurable)
- Build `video_url = https://www.facebook.com/{page_id}/videos/{video_id}`

### Stage 7 — Post-publish Comment (NEW design)

**Module**: `core/facebook/commenter.py:FacebookCommenter`

#### Inputs
| Parameter | Type | Source |
|-----------|------|--------|
| `client` | `GraphClient` | created inside FacebookPublisher |
| `page_access_token` | str | from `PageInfo.access_token` |
| `video_id` | str | returned by Stage 5 |
| `text` | str | `task["comment"]` (Excel `comment` column) |

#### Returns
`CommentResult` dataclass (parallel to TikTok):
```python
@dataclass
class CommentResult:
    success:    bool
    skipped:    bool      # True when text empty / whitespace
    comment_id: str       # Graph-assigned ID on success
    error_code: str       # "190", "200", "32", etc.
    message:    str       # friendly Vietnamese
    text:       str       # what we tried
```

#### Behaviour matrix
| Input | Result | API call? |
|-------|--------|-----------|
| empty / whitespace | `success=True, skipped=True` | ❌ |
| > 8000 chars | `success=False, error_code=comment_too_long` | ❌ |
| empty video_id | `success=False, error_code=missing_video_id` | ❌ |
| stop_event set | `success=False, error_code=user_cancelled` | ❌ |
| API returns OK | `success=True, comment_id=<id>` | ✓ |
| GraphError 190 (token) | `success=False, error_code="190"`, friendly hint | ✓ |
| GraphError 200 (perm) | `success=False, error_code="200"`, missing pages_manage_engagement | ✓ |
| GraphError 32 (rate) | `success=False, error_code="32"` | ✓ |
| GraphError 368 (spam) | `success=False, error_code="368"`, page temp-suspended | ✓ |
| Network failure | `success=False, error_code=unexpected_error` | ✓ (failed) |

#### Critical guarantee
**Comment failure NEVER breaks publish success.** The publisher catches all
exceptions from the commenter and falls through to return the successful
`PublishResult` from Stages 4-6.

#### Reels exclusion
Reels (`post_type=reels`) skips comment with audit event
`facebook_comment_skipped` reason=`reels_no_comment`. FB Graph API does not
reliably support comments on Reels via the same endpoint as feed videos.

#### Audit events
| Event | When | Audit fields |
|-------|------|--------------|
| `facebook_comment_posted` | success + non-skipped | `comment_id`, `text_len`, `publish_id` |
| `facebook_comment_skipped` | empty / reels | `reason` |
| `facebook_comment_failed` | API error or exception | `error_code`, `message` |

#### Required FB scope/permission
`pages_manage_engagement` — usually granted alongside `pages_manage_posts` in
the same Meta App review.

### Stage 8 — Result + Audit
**Returns**: `PublishResult(success=True, external_post_id=video_id, external_post_url=video_url, status="published")`
- Sheet writes back: `fb_video_id`, `VIDEO_URL`, `status="success"`, `uploaded_at`

---

## 🔍 Error → Action mapping

| Code | Stage | Friendly message | Action |
|------|-------|-----------------|--------|
| 190 | 2 / 7 | Token Page hết hạn | Reconnect FB account |
| 200 | 5 / 7 | Thiếu pages_manage_posts / pages_manage_engagement | Re-grant during OAuth |
| 4, 17, 32 | any | Rate limit | Bot auto-retries |
| 368 | 5 / 7 | Page bị FB tạm khóa | Wait + check FB Support inbox |
| 100 | 5 / 7 | Tham số sai (video format, URL) | Check video file |
| 6000-6080 | 5 | Video format / size / duration | Convert via FFmpeg |

---

## 🧪 Test coverage summary

| Test file | Tests | Stages covered |
|-----------|-------|----------------|
| `test_07_k1_metadata.py` | ~12 | Stages 4-5 + comment routing |
| `test_10_k8_reels.py` | ~30 | Reels-specific + comment exclusion |
| `test_11_upgrades.py` | ~20 | Stages 0-6 + comment forwarding (updated) |
| `test_16_facebook_commenter.py` | **25 NEW** | **Stage 7 + integration** |
| Others | rest | Stages 1-3, 6, 8 |

**Total project tests: 554 PASS ✅**

---

## 🎬 Example: Excel row that posts to Page + comments

```
target_page:              MyContentPage
video short:              C:\videos\promo.mp4
Tieu_de_SEO:             5-minute breakfast 🥗
Mo_ta:                   Quick & healthy
Tu_Khoa_Chinh:           healthyfood,breakfast,quickmeal
Link_anh_Thumb:           C:\videos\thumb.jpg
schedule_time:            2025-12-01 10:30
platform:                 facebook
post_type:                feed
Binh_luan_video:         Watch on YouTube too! https://youtube.com/@channel
```

**Workflow**:
1. SheetRunner picks row → builds upload_task with `comment="Watch on YouTube too!..."`
2. FacebookPublisher.publish(task) called
3. Resolve account + page from TokenStore
4. Rate limiter acquires slot
5. GraphUploader uploads in 3 phases (start → transfer → finish)
6. Thumbnail uploaded, status verified
7. **FacebookCommenter.post_comment(video_id, "Watch on YouTube too!...")**
   - Graph API: `POST /{video_id}/comments` with `message`
   - On success → audit `facebook_comment_posted`
   - On scope missing → audit `facebook_comment_failed`, video remains posted
8. Excel updated: `VIDEO_URL`, `fb_video_id`, `status=success`

---

## 🚀 Configuration

In `data/config.json`:
```json
{
  "graph_api_version": "v21.0",
  "min_interval_per_page_s": 30,
  "max_concurrent_uploads_per_page": 1,
  "verify_video_after_upload": true,
  "col_comment": "Binh_luan_video"
}
```

The `comment` column name in Excel is configurable via `col_comment`. The
default Vietnamese header is `Binh_luan_video`.

---

## ⚠️ Differences from TikTok comment workflow

| Aspect | Facebook | TikTok |
|--------|---------|--------|
| API auth | Page access_token (per-page) | User access_token |
| Endpoint | `POST /{video_id}/comments` | `POST /v2/comment/create/` |
| Body | `{"message": "..."}` | `{"video_id": "...", "text": "..."}` |
| Max length | ~8000 chars | ~150 chars |
| Required scope | `pages_manage_engagement` | `comment.create` (separate audit) |
| Works on Reels? | ❌ skipped | ❌ (drafts) / ✓ (direct posts) |
| Comment audit prefix | `facebook_comment_*` | `tiktok_comment_*` |

---

## 🛡 Safety guarantees

1. **Publish success preserved** — comment exception NEVER raises out of `FacebookPublisher.publish()`.
2. **No double-comment** — `FacebookPublisher` clears `task["comment"]` before calling `UploadEngine` (which has its own legacy inline `post_comment` for direct GUI uses).
3. **Audit everything** — every comment attempt (success / skip / fail) creates an audit event with `publish_id`.
4. **Stop event honoured** — `FacebookCommenter` checks `stop_event` before API call.
5. **Friendly errors** — Graph error codes translated via `core/facebook/error_codes.py`.
6. **Length cap** — caller can't crash the comment by passing huge strings.
