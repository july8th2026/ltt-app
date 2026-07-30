# TikTok Submission Checklist — LTTStudio VideoBot

> Print this and tick from top to bottom. **Do not skip any item.**
> Each unchecked item = one possible reason for TikTok to reject.

---

## 📦 PRE-SUBMISSION — Assets ready

```
□ App icon — 1024×1024 PNG, no transparency, square crop
□ App icon — square crop showing the LTT diamond clearly (avoid full circuit board if cropped tight)
□ Demo video — 1-3 minutes, MP4, 1080p
□ Demo video uploaded to YouTube as "Unlisted" (NOT private)
□ Demo video link copied to clipboard
□ App screenshots (optional but recommended): Accounts tab, Operation tab, Consent dialog
```

---

## 🌐 WEBSITE — All pages live & accessible

Verify each URL returns 200 OK over HTTPS:

```
□ https://lttstudio.top/                                  → Homepage
□ https://lttstudio.top/about.html                       → About
□ https://lttstudio.top/products/videobot/               → Product landing
□ https://lttstudio.top/products/videobot/download.html  → Download
□ https://lttstudio.top/legal/privacy.html               → Privacy (VI)
□ https://lttstudio.top/legal/privacy-en.html            → Privacy (EN) ← REVIEWERS USE THIS
□ https://lttstudio.top/legal/terms.html                 → Terms (VI)
□ https://lttstudio.top/legal/terms-en.html              → Terms (EN) ← REVIEWERS USE THIS
□ https://lttstudio.top/legal/callback.html              → OAuth callback
□ https://lttstudio.top/support/faq.html                 → FAQ
□ https://lttstudio.top/sitemap.xml                      → Sitemap
□ https://lttstudio.top/robots.txt                       → Robots
```

```
□ SSL certificate valid (browser shows 🔒)
□ No mixed content warnings
□ Logo loads on all pages
□ Language switcher VI/EN works
```

---

## 📝 PRIVACY POLICY — Must contain these specifics

Open https://lttstudio.top/legal/privacy-en.html and check:

```
□ Mentions "TikTok" by name explicitly
□ Lists every TikTok scope requested (user.info.basic, video.upload, video.publish)
□ Explains what each scope is used for
□ States data is stored LOCALLY (no cloud)
□ States token encryption method (Fernet)
□ Provides way to revoke access (TikTok settings + in-app)
□ Mentions AI-generated content disclosure
□ Has dated "Last updated" timestamp
□ Has working contact email
□ Has back-link to TikTok's official Privacy Policy
```

---

## 🔐 TIKTOK DEVELOPER PORTAL — Form fields

Go to https://developers.tiktok.com → My Apps → [Your App]

### Tab: Basic Info
```
□ App Name: "LTTStudio VideoBot"
□ App Icon uploaded (1024×1024 PNG)
□ App Description filled (paste from app-description.md)
□ Category: "Productivity"
□ Website URL: https://lttstudio.top
```

### Tab: Login Kit
```
□ Redirect URI added: https://lttstudio.top/legal/callback.html
□ Privacy Policy URL: https://lttstudio.top/legal/privacy-en.html
□ Terms of Service URL: https://lttstudio.top/legal/terms-en.html
```

### Tab: Content Posting API
```
□ Scopes selected: user.info.basic, video.upload, video.publish
□ Scope justifications filled (paste from scope-justification.md)
□ Demo Video URL: <YouTube unlisted link>
□ Use case description filled
```

---

## ⚙️ BOT CONFIG (data/config.json)

```
□ tiktok_client_key  = <copied from TikTok Portal>
□ tiktok_client_secret = <copied from TikTok Portal>
□ tiktok_redirect_uri = "https://lttstudio.top/legal/callback.html"
□ privacy_policy_url  = "https://lttstudio.top/legal/privacy.html"
□ app_privacy_policy_url = "https://lttstudio.top/legal/privacy.html"
□ app_terms_url = "https://lttstudio.top/legal/terms.html"
□ app_name = "LTTStudio VideoBot"
□ app_support_email = "support@lttstudio.top"
```

---

## ✅ TESTING (Before submitting)

```
□ Run bot, click "Connect TikTok" — browser opens to TikTok auth page
□ Authorize on TikTok — browser redirects to https://lttstudio.top/legal/callback.html
□ Callback page redirects back to localhost
□ Account appears in app with TikTok display name
□ Select Excel file with 1 row, post_type=tiktok_draft
□ Click Start — video uploads to TikTok drafts successfully
□ Check TikTok app: video appears in Drafts inbox
□ Test direct post (PRIVATE only for testing): consent dialog appears, video posts
□ Disconnect account in app — token removed from data/tiktok_tokens.enc
```

---

## 🚀 FINAL — Submit for Review

```
□ Click "Submit for Review" in TikTok Portal
□ Save submission ID
□ Email confirmation received from TikTok (within minutes)
□ Set calendar reminder: check status in 7 days
```

---

## ⏳ AFTER SUBMISSION

```
□ Reviewer questions arrive? → Respond within 48 hours via TikTok Portal
□ Approved? → Set tiktok_audit_approved = true in config.json
□ Approved? → Enable Direct Post in app Settings
□ Rejected? → Read reason carefully, fix, resubmit
```

---

## 🚨 Common Rejection Reasons

If rejected, check against these:

1. **"Privacy policy does not mention TikTok"** → Already fixed in `legal/privacy-en.html` section 4b
2. **"Demo video does not show OAuth flow"** → Re-record showing browser URL bar during auth
3. **"Redirect URI mismatch"** → Must be EXACTLY `https://lttstudio.top/legal/callback.html`
4. **"Scope justification too vague"** → Use scope-justification.md (be specific)
5. **"Demo video unavailable"** → Check YouTube visibility = "Unlisted", not "Private"
6. **"App description doesn't explain use case"** → Use app-description.md full version
