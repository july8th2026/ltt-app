# TikTok Publish Workflow — End-to-End

> Complete reference for the TikTok job lifecycle, from sheet row → public
> video → optional comment. Each stage maps to a specific Python function
> with documented inputs, outputs, errors, and tests.

---

## 🗺 Full pipeline diagram

```
JOB INTAKE              ACCOUNT + TOKEN          COMPLIANCE
┌──────────┐  task    ┌──────────────┐  ok    ┌─────────────────┐
│  Excel   │ ───────▶ │  _resolve_   │ ─────▶ │  Compliance     │
│  row     │          │  account     │        │  Guard.check()  │
└──────────┘          │  _ensure_    │        └────────┬────────┘
                      │  token_fresh │                 │ ok
                      └──────────────┘                 ▼
                                                 ┌─────────────┐
                                                 │ Upload Init │
                                                 │ /publish/   │
                                                 │ video/init  │
                                                 └──────┬──────┘
                                                        │ publish_id
                                                        │ upload_url
                                                        ▼
                                                 ┌──────────────┐
                                                 │ Chunk upload │
                                                 │ (10MB chunks)│
                                                 └──────┬───────┘
                                                        │
                                                        ▼
                                                 ┌─────────────┐
                                                 │ Status poll │
                                                 │ (backoff)   │
                                                 └──────┬──────┘
                                                        │ PROCESS_SUCCESS
                                                        ▼
                          ┌────────────────────────────────────┐
                          │ STAGE 7: comment (optional)        │
                          │ POST /v2/comment/create/           │
                          │ Graceful fail (never breaks pub.)  │
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
| File | Function | Output |
|------|----------|--------|
| `core/sheet_runner.py:_tick()` | Read 1 sheet row → `upload_task` dict | dict with `video_path`, `title`, `description`, `comment`, `tiktok_account`, `tiktok_privacy_level`, etc. |
| `gui/operation_tab.py:_start_tiktok()` | Manual UI flow with consent dialog | Same dict shape |

**Required columns in Excel for TikTok:**

| Column | Purpose | Required |
|--------|---------|----------|
| `video short` | Local path or Drive URL | ✓ |
| `Tieu_de_SEO` | Title (≤150 chars) | ✓ |
| `Mo_ta` | Description (≤2200 chars) | optional |
| `Tu_Khoa_Chinh` | Comma-separated hashtags | optional |
| `platform` | Must be `tiktok` | ✓ |
| `post_type` | `tiktok_draft` or `tiktok_direct` | ✓ |
| `tiktok_account` | open_id of connected account | optional (fallback: first) |
| `tiktok_privacy_level` | `SELF_ONLY` / `PUBLIC_TO_EVERYONE` / etc. | ✓ for direct |
| `tiktok_is_ai_generated` | `TRUE`/`FALSE` | optional |
| `tiktok_commercial_content` | `TRUE`/`FALSE` | optional |
| **`comment`** | **First-comment text (NEW)** | **optional** |

---

### Stage 1 — Account Resolution
**Function**: `TikTokPublisher._resolve_account(task)` in `publisher_service.py`
- Reads `task["account"]` (open_id)
- Falls back to first connected account if empty
- Raises `RuntimeError` if no accounts connected

**Tests**: `tests/test_06_tiktok_publisher.py` (account routing)

---

### Stage 2 — Token Freshness
**Function**: `TikTokPublisher._ensure_token_fresh(account)`
- Checks `account.is_token_valid()` (60s buffer)
- If expired, calls `TikTokAuthManager.refresh_access_token(account)`
- Writes audit event `tiktok_token_refreshed`

**Tests**: `tests/test_14_audit.py` A22, A23

---

### Stage 3 — Compliance Pre-flight
**Function**: `TikTokComplianceGuard.check(task, account)` in `compliance_guard.py`
- Account presence, token validity, scope sufficiency
- Video file exists + size ≤ 4GB
- Caption ≤ 2200 chars
- Privacy level enum valid
- Audit-gate (PUBLIC requires `tiktok_audit_approved=true`)
- User consent (`user_confirmed_at`)
- AI-generated content advisory
- **Spam pre-flight** (hashtag count, empty caption, keyword stuffing)

Returns `list[ComplianceWarning]` (non-blocking).
Raises `TikTokComplianceError` on hard violations.

**Tests**: `tests/test_13_compliance.py` (15+ test cases)

---

### Stage 4 — Upload Init
**Function**: `TikTokDirectUploader.upload(task)` / `TikTokDraftUploader.upload(task)`
- POST `/v2/post/publish/video/init/` (direct) or `/inbox/video/init/` (draft)
- Sends `post_info` (title, privacy, disable flags) + `source_info` (chunk plan)
- Returns `publish_id` + `upload_url`

**Tests**: `tests/test_05_misc_utils.py`, `tests/test_07_k1_metadata.py`

---

### Stage 5 — Chunk Upload
**Function**: `upload_video_in_chunks(...)` in `upload_utils.py`
- Reads video in 10MB chunks
- PUTs each chunk with `Content-Range: bytes 0-1048575/10485760` header
- Calls `on_progress`, `on_status` after each chunk
- Honours `stop_event` for cancellation

**Tests**: `tests/test_07_k1_metadata.py`, mocked PUT responses

---

### Stage 6 — Status Polling
**Function**: `poll_until_done(client, publish_id, ...)` in `status_poller.py`
- POSTs `/v2/post/publish/status/fetch/` repeatedly
- Exponential backoff: 3s → 4.5s → 6.75s → ... → 30s cap
- Returns when status = `PROCESS_SUCCESS` or `SEND_TO_USER_INBOX`
- Raises `TikTokError` on `PROCESS_FAILED` or timeout

**Tests**: status_poller mocked time + status sequences

---

### Stage 7 — Post-publish Comment (NEW)

**Function**: `TikTokCommenter.post_comment(video_id, text)` in `commenter.py`

#### Inputs
| Parameter | Type | Source |
|-----------|------|--------|
| `video_id` | str | `publish_id` from Stage 4 |
| `text` | str | `task["comment"]` (from Excel `comment` column) |

#### Returns
`CommentResult` dataclass:
```python
@dataclass
class CommentResult:
    success:    bool
    skipped:    bool          # True when text empty / whitespace
    comment_id: str           # set on success
    error_code: str           # tiktok code or our own
    message:    str           # human-readable
    text:       str           # what we tried
```

#### Behavior matrix
| Input | Result | API call? |
|-------|--------|-----------|
| empty / whitespace | `success=True, skipped=True` | ❌ |
| > 150 chars | `success=False, error_code=comment_too_long` | ❌ |
| empty video_id | `success=False, error_code=missing_video_id` | ❌ |
| stop_event set | `success=False, error_code=user_cancelled` | ❌ |
| API returns OK | `success=True, comment_id=<id>` | ✓ |
| API returns scope_not_authorized | `success=False`, friendly message with action | ✓ |
| API returns spam_risk_text | `success=False, error_code=spam_risk_text` | ✓ |
| API returns rate_limit_exceeded | `success=False, error_code=rate_limit_exceeded` | ✓ |
| Network failure | `success=False, error_code=unexpected_error` | ✓ (failed) |

#### Critical guarantee
**Comment failure NEVER breaks publish success.** The publisher catches all
exceptions from the commenter and falls through to return the successful
`PublishResult` from Stages 4-6.

#### Audit events
| Event | When |
|-------|------|
| `tiktok_comment_posted` | success + non-skipped |
| `tiktok_comment_skipped` | empty text |
| `tiktok_comment_failed` | API error or exception |

#### Required TikTok scope
`comment.create` — separate from `video.publish`. Requires additional TikTok
Developer Portal review to be granted.

**Tests**: `tests/test_15_tiktok_commenter.py` — 23 test cases:
- C01-C04, C12-C14: Validation
- C05-C06: API call payload
- C07-C11: Error handling (scope, spam, rate limit, cancel, unexpected)
- C20-C27: Publisher integration (wiring, audit events, fault tolerance)
- C30-C31: Sheet runner column forwarding

---

### Stage 8 — Result + Audit
**Function**: `TikTokPublisher.publish(task)` (returns `PublishResult`)

After all stages:
- `PublishResult.external_post_id` = publish_id
- `PublishResult.status` = `"published"` (direct) or `"draft"` (draft)
- Audit event `tiktok_publish_success` written
- Sheet writes back: `tiktok_id`, `tiktok_status`, `tiktok_confirmed_at`

---

## 🔍 Error → Action mapping summary

| Error code | Stage | Friendly message | Action |
|-----------|-------|-----------------|--------|
| `access_token_invalid` | 2 | "Token TikTok không hợp lệ" | Reconnect |
| `scope_not_authorized` (publish) | 4 | "Thiếu quyền video.publish" | Reconnect with all scopes |
| `scope_not_authorized` (comment) | 7 | "Thiếu comment scope" | Submit app for Comment Management API |
| `privacy_level_option_mismatch` | 4 | "App chưa qua audit — chỉ SELF_ONLY" | Set tiktok_audit_approved=true after approval |
| `spam_risk_text` | 4 or 7 | "Caption/comment bị flag spam" | Review content |
| `rate_limit_exceeded` | any | "Vượt rate limit" | Bot auto-retries |
| `video_pull_failed` | 6 | "TikTok không tải được video" | Check video format |
| `comment_too_long` | 7 | "Comment quá dài" | Shorten to ≤150 chars |
| `missing_video_id` | 7 | "Không có video_id" | Internal bug — report |

---

## 🧪 Test coverage summary

| File | Tests | Stage coverage |
|------|-------|----------------|
| `test_13_compliance.py` | ~15 | Stage 3 (compliance) |
| `test_14_audit.py` | 26 | Cross-stage (audit log) |
| `test_15_tiktok_commenter.py` | **23 NEW** | **Stage 7 + integration** |
| `test_07_k1_metadata.py` | ~10 | Stages 4-5 (init + chunk) |
| Other | rest | Stages 0, 1, 2, 6, 8 |

**Total project tests: 529 PASS ✅**

---

## 🎬 Example: Excel row that posts public + comments

```
video short:              C:\videos\promo.mp4
Tieu_de_SEO:             5-minute healthy breakfast 🥗
Mo_ta:                   Quick recipe, ready in 5 min!
Tu_Khoa_Chinh:           healthyfood,breakfast,quickmeal
platform:                tiktok
post_type:               tiktok_direct
tiktok_account:          7212345678901234567   (open_id)
tiktok_privacy_level:    PUBLIC_TO_EVERYONE
tiktok_is_ai_generated:  FALSE
tiktok_commercial_content: FALSE
comment:                 Subscribe for more recipes! 🍳
```

**Workflow**:
1. Sheet runner picks row → builds upload_task with `comment="Subscribe for more recipes! 🍳"`
2. Resolve account, refresh token if needed
3. Compliance guard passes (audit_approved=true required for PUBLIC_TO_EVERYONE)
4. Upload init → publish_id
5. Chunks uploaded
6. Status poll → PROCESS_SUCCESS
7. **`TikTokCommenter.post_comment(publish_id, "Subscribe for more recipes! 🍳")`**
   - If scope OK → comment appears under the video, audit event `tiktok_comment_posted`
   - If scope missing → audit event `tiktok_comment_failed`, video remains posted
8. Excel updated: `tiktok_id=<publish_id>`, `tiktok_status=success`

---

## 🚀 To enable comment scope in production

1. Go to **TikTok Developer Portal** → **My Apps** → your app
2. **Add Product** → **Comment Management API**
3. Submit for review (separate from Content Posting audit)
4. After approval, OAuth flow will include `comment.create` scope
5. Users must **reconnect** their TikTok account once to grant the new scope
6. Set in config:
   ```json
   "tiktok_scopes": "user.info.basic,video.upload,video.publish,comment.create"
   ```

Until approved, the commenter will return `scope_not_authorized` errors —
the video still posts successfully, only the comment is skipped.
