# Excel Template Guide — LTTStudio VideoBot

> **For TikTok reviewers:** This document describes the Excel data model
> users provide to the application. Each row = one video to post.

---

## 📋 Required Columns (TikTok flow)

| Column | Required? | Description | Example |
|--------|-----------|-------------|---------|
| `video short` | ✅ | Local path or Google Drive URL to .mp4 | `C:\videos\promo.mp4` |
| `Tieu_de_SEO` | ✅ | Title / caption (≤150 chars for TikTok) | `Quick recipe for breakfast` |
| `Mo_ta` | ⚪ | Description (≤2200 chars) | `Step by step in 60s...` |
| `Tu_Khoa_Chinh` | ⚪ | Comma-separated hashtags | `#cooking,#breakfast,#quickmeal` |
| `platform` | ✅ | `tiktok` or `facebook` | `tiktok` |
| `post_type` | ✅ | `tiktok_draft` (safe) or `tiktok_direct` (needs audit) | `tiktok_draft` |
| `schedule_time` | ⚪ | When to post (leave empty for ASAP) | `2025-01-15 10:30` |
| `status` | 🔄 auto | Bot writes: `pending` / `success` / `error` | (managed by bot) |

---

## 🔐 TikTok-specific Columns

| Column | Required? | Description | Values |
|--------|-----------|-------------|--------|
| `tiktok_account` | ⚪ | Which TikTok account (open_id). Leave empty = first connected | `xxxxx` or empty |
| `tiktok_privacy_level` | ✅ for direct | Privacy on TikTok | `SELF_ONLY`, `FOLLOWER_OF_CREATOR`, `PUBLIC_TO_EVERYONE` |
| `tiktok_is_ai_generated` | ✅ if AI | AI-generated content flag | `TRUE` / `FALSE` (default FALSE) |
| `tiktok_commercial_content` | ⚪ | Branded/promotional content | `TRUE` / `FALSE` (default FALSE) |
| `tiktok_confirmed_at` | 🔄 auto | Timestamp when user confirmed in consent dialog | (managed by bot) |
| `tiktok_id` | 🔄 auto | TikTok publish_id returned by API | (managed by bot) |
| `tiktok_link` | 🔄 auto | Public URL after post (if available) | (managed by bot) |
| `tiktok_status` | 🔄 auto | TikTok processing status | `PROCESS_SUCCESS` / etc. |

---

## ⚠️ User Responsibility (TikTok Compliance)

Users MUST accurately fill these fields per TikTok policy:

### `tiktok_is_ai_generated`
Set to `TRUE` if **any** of the following applies:
- Video uses AI voice generation (TTS that mimics real voices)
- Video uses AI-generated visuals (Midjourney, Stable Diffusion images)
- Video has deepfake or face-swap content
- Video uses AI-generated text overlays where AI played significant role
- Significant AI-assisted editing that changes meaning

When `TRUE`: TikTok will show "AI-generated" label on the video.

### `tiktok_commercial_content`
Set to `TRUE` if the video is:
- Paid promotion / sponsored content
- Self-promotion of your own brand/product
- Affiliate marketing
- Promotional content for another business

When `TRUE`: TikTok requires "Promotional content" disclosure.

### `tiktok_privacy_level`
- `SELF_ONLY` — Only the creator can see (default & safest)
- `FOLLOWER_OF_CREATOR` — Only followers can see
- `PUBLIC_TO_EVERYONE` — Public on TikTok (requires audit approval)

---

## 🔒 Compliance Guard Behavior

Before any upload, the application's `ComplianceGuard` verifies:

```
1. Account is connected and token is valid
2. Video file exists and ≤ 4GB
3. Caption ≤ 2200 characters
4. privacy_level is valid value
5. If post_type=tiktok_direct AND audit not approved:
     → Force privacy_level to SELF_ONLY
6. If is_ai_generated=TRUE → ensure flag is passed to TikTok API
7. Spam pre-flight check:
   - Hashtag count ≤ 30
   - Not emoji-only caption
   - No keyword stuffing
8. user_confirmed_at must be set (from consent dialog)
```

If ANY blocking violation → upload is rejected, user sees error in app log.

---

## 📊 Example Row

```
video short:              C:\videos\recipe.mp4
Tieu_de_SEO:             5-min healthy breakfast 🥗
Mo_ta:                   Easy morning recipe with avocado toast
Tu_Khoa_Chinh:           #healthyrecipe,#breakfast,#avocado
platform:                tiktok
post_type:               tiktok_draft
tiktok_privacy_level:    SELF_ONLY
tiktok_is_ai_generated:  FALSE
tiktok_commercial_content: FALSE
schedule_time:           2025-01-15 09:00
```

---

## 🧪 How TikTok Reviewer Can Test

1. Open the application
2. Connect a test TikTok account
3. Use the provided sample Excel file (`samples/test_tiktok.xlsx`)
4. Click "Start" in the Operation tab
5. Observe:
   - Consent dialog appears (if post_type=tiktok_direct)
   - Compliance Guard logs visible in the log panel
   - Audit log written to `data/audit_log.jsonl`
   - Video appears in the TikTok account's drafts/profile
