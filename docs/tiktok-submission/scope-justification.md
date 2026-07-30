# TikTok Scope Justification — LTTStudio VideoBot

> Use this when TikTok asks "Why do you need each scope?" during the audit.
> Keep answers concise — reviewers prefer 1-2 sentences per scope.

---

## Requested Scopes & Justifications

### 1. `user.info.basic`

**Why we need it:**
We use this scope to retrieve the user's TikTok display name and open_id immediately after OAuth completes. The display name is shown in the application's "Accounts" tab so the user can visually confirm which TikTok account is connected and avoid posting to the wrong account when managing multiple accounts.

**Data accessed:** `open_id`, `display_name`, `avatar_url`

**Data NOT accessed:** No video history, no followers, no email, no phone number.

**Storage:** Local only, encrypted at rest. Never transmitted to any server other than TikTok's own API.

---

### 2. `video.upload`

**Why we need it:**
This is the **primary** scope for our application. We use it to upload videos to the user's TikTok drafts inbox via the Content Posting API v2 (`POST /v2/post/publish/inbox/video/init/` and `POST /v2/post/publish/inbox/video/upload/`).

**User experience:**
- The user prepares a list of videos in an Excel spreadsheet
- Each video is uploaded to their TikTok drafts inbox
- The user opens the TikTok mobile app and decides which drafts to publish
- This is the **default and safest mode** — videos never go public without the user's explicit action in the TikTok app itself.

**Why this is safe:**
Drafts are visible only to the user, can be edited or deleted before publishing, and never appear publicly without an additional explicit action from the user inside the TikTok app.

---

### 3. `video.publish`

**Why we need it:**
This scope enables direct publishing (without going through drafts), available **only after** explicit consent from the user via an in-app consent dialog that is impossible to bypass.

**Consent flow** (enforced by ComplianceGuard module):
1. User initiates a direct post
2. A modal dialog appears showing:
   - Privacy level (SELF_ONLY / FOLLOWER_OF_CREATOR / PUBLIC_TO_EVERYONE)
   - AI-generated content disclosure (mandatory checkbox if applicable)
   - Commercial content disclosure (mandatory checkbox if applicable)
   - Disable comments / duet / stitch settings
   - "I confirm this content complies with TikTok Community Guidelines" (mandatory)
3. User must actively click "Confirm & Post" — there is no default "OK"
4. The Compliance Guard blocks the upload if any mandatory disclosure is missing

**Why we need this scope (not just video.upload):**
Some users — particularly small marketing agencies — have client approval workflows that happen outside TikTok, so going through drafts adds an unnecessary manual step. For these users, direct publish (with the consent gate) saves significant time.

**Default behavior:** Direct publish is **disabled by default**. The user must explicitly enable it in Settings AND pass the consent dialog every time.

---

## Compliance Features Summary

| Feature | Implementation |
|---------|---------------|
| OAuth PKCE | `core/tiktok/auth_manager.py` — uses code_challenge_method=S256 |
| Token encryption | Fernet (AES-128-CBC + HMAC) with machine-bound key |
| User consent dialog | `gui/tiktok_consent_dialog.py` — mandatory before direct post |
| Compliance Guard | `core/tiktok/compliance_guard.py` — blocks invalid uploads |
| Audit log | `utils/audit_logger.py` — JSONL, every action logged |
| AI content disclosure | Excel column `tiktok_is_ai_generated` → passed to API |
| Commercial disclosure | Excel column `tiktok_commercial_content` → passed to API |
| Rate limiting | Exponential backoff in `core/tiktok/status_poller.py` |
| Token refresh | Automatic background refresh in `core/tiktok/token_refresher.py` |
