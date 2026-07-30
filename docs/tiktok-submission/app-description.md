# LTTStudio VideoBot — TikTok App Description

> **Use this exact text** when filling out the TikTok Developer Portal app submission form.
> Paste into the "App Description" field.

---

## Short Description (1 line, for app cards)

```
Desktop application that helps Vietnamese content creators automate posting videos to TikTok from an Excel spreadsheet.
```

---

## Full Description (200+ words, for submission)

```
LTTStudio VideoBot is a free, open-source desktop application designed for
Vietnamese content creators and small marketing agencies who need to publish
multiple videos to TikTok efficiently.

USE CASE
Content creators with 20-100+ videos per week currently spend several hours
daily manually uploading each video to TikTok. LTTStudio VideoBot allows them
to manage their entire content schedule via a familiar Excel spreadsheet
(video paths, captions, hashtags, scheduled times) and automate the upload
process. The application runs entirely on the user's local Windows computer
— no cloud servers, no third-party data processing.

HOW IT USES TIKTOK APIS
The application uses TikTok Content Posting API v2 to:
1. Upload videos to the user's TikTok drafts inbox (video.upload scope),
   allowing the user to preview before publishing.
2. Optionally publish directly with explicit user consent shown via an
   in-app consent dialog (video.publish scope).
3. Display the connected TikTok account's name in the UI (user.info.basic).

USER CONSENT & COMPLIANCE
Every direct post requires explicit user confirmation through a consent
dialog that displays: privacy level, AI-generated content flag, commercial
content disclosure, and disable-comment/duet/stitch settings. The application
includes a Compliance Guard module that blocks publishing if mandatory
disclosures are missing.

PRIVACY-FIRST ARCHITECTURE
- No backend servers — the application connects directly from the user's
  computer to TikTok APIs over HTTPS.
- OAuth tokens are encrypted locally using Fernet (AES-128-CBC + HMAC-SHA256)
  with a key derived from the machine's UUID.
- All audit logs are written to a local file for the user's own review.
- Users can revoke access at any time through TikTok account settings or by
  disconnecting in the app.

TARGET AUDIENCE
- Individual content creators in Vietnam (primary market)
- Small marketing agencies managing multiple client accounts
- SMB businesses doing their own social media

The application is distributed as a Windows .exe installer and source code
from https://lttstudio.top, free of charge.
```

---

## Suggested Category

```
Productivity / Content Creation
```

---

## Suggested Keywords (for App Search)

```
content automation, video scheduling, vietnam, creator tools, excel posting,
multi-account, social media automation, lttstudio
```
