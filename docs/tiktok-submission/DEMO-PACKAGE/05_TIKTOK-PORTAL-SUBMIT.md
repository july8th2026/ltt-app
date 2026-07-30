# 🎯 05 — TIKTOK PORTAL SUBMIT

> Điền form audit submission tại https://developers.tiktok.com
> Sau khi bấm Submit, đợi 5-14 ngày để TikTok review.

---

## Vào Portal

1. Mở https://developers.tiktok.com
2. Đăng nhập (account TT của bạn đã tạo app `LTTStudio VideoBot`)
3. Click **Manage apps** (top right hoặc dashboard)
4. Click vào tên app **LTTStudio VideoBot**

---

## Điền form Audit Submission

### Field 1: Demo Video URL

Paste link YouTube unlisted từ Bước 4:

```
https://youtu.be/YOUR_VIDEO_ID
```

### Field 2: Use Case Description

Paste nguyên đoạn dưới đây (English):

```
LTTStudio VideoBot is a Windows desktop tool for Vietnamese content creators
to schedule and publish short-form videos to TikTok via the official Content
Posting API v2.

Users connect their TikTok account once via OAuth with PKCE, then schedule
batch uploads from a Google Sheet or post manually one-by-one through a
dedicated Manual TikTok tab.

Each publish requires explicit user consent via a confirmation dialog that
surfaces:
- Privacy level (selected by user from /v2/post/publish/creator_info/query/
  results; never pre-set; defaults to SELF_ONLY)
- Three interaction toggles (allow_comment, allow_duet, allow_stitch),
  respecting account-level creator settings
- AI-generated content disclosure checkbox per TikTok November 2024 policy
- Branded content disclosure checkbox per Branded Content Policy

The application includes a built-in audit-readiness dashboard that verifies
compliance requirements in real time, encrypts all tokens at rest using
Fernet (AES-128 + HMAC-SHA256), and runs entirely on the user's machine
with no third-party data sharing.

Privacy Policy: https://lttstudio.top/legal/privacy.html
Terms of Service: https://lttstudio.top/legal/terms.html
Support: support@lttstudio.top
```

### Field 3: Scope Justifications

#### 3.1 — `user.info.basic`

```
Display the connected creator's username and avatar inside our application
so users can verify which TikTok account is currently active before
publishing. Also used to label uploads in the local audit log
(data/audit_log.jsonl) for compliance traceability. This scope is the
minimum needed for any meaningful UX after OAuth and is shown clearly in
our pre-authorization disclosure modal at 00:55 of the demo video.
```

#### 3.2 — `video.upload`

```
Send video files to the user's TikTok Inbox in Draft mode (POST
/v2/post/publish/inbox/video/init/) for the user to publish manually
from the TikTok mobile app. This is the default and safest mode when the
app's audit status is pending, and remains a recommended option for
batch operations where the creator wants final control before each
video goes live. Demonstrated at 02:35-02:50 of the demo video.
```

#### 3.3 — `video.publish`

```
Direct publishing of videos to TikTok via POST
/v2/post/publish/video/init/ after the user's explicit per-publish
confirmation through our consent dialog (shown at 02:10-02:40 of the
demo video). Required for the manual-post and Google Sheet automation
flows where creators have already reviewed each row's metadata.

Privacy level is always selected by the user from the dropdown populated
by /v2/post/publish/creator_info/query/ (never pre-set, never bypassed);
defaults to SELF_ONLY when the app is unaudited. Interaction toggles
(comment/duet/stitch) respect creator account-level settings — disabled
toggles in the dialog are locked when creator_info reports
comment_disabled=true / duet_disabled=true / stitch_disabled=true.
```

### Field 4: Other fields (nếu portal yêu cầu)

| Field | Value |
|---|---|
| App icon | Upload `assets/lttstudio-icon-1024.png` |
| Platform | Web / Desktop |
| Region | Vietnam / Asia |
| User type | Content creator |

---

## Compliance Checkboxes

Tick **TẤT CẢ** sau khi đọc kỹ:

```
☐ Tôi đã đọc và đồng ý với TikTok Developer Terms of Service
☐ App của tôi tuân thủ TikTok Community Guidelines
☐ Tôi đã implement mandatory user consent before each publish
☐ Privacy Policy của tôi đầy đủ thông tin theo yêu cầu
☐ Tôi sẽ thông báo cho TikTok nếu thay đổi scope/use case sau audit
```

---

## Submit

1. Review lại toàn bộ form 1 lần nữa
2. Bấm nút **Submit for Review** (góc dưới phải)
3. Confirmation dialog hiện ra → đồng ý
4. Trang chuyển sang trạng thái **"Pending review"**

---

## Email confirmation

Trong ~5-30 phút sau submit, bạn nhận email từ:

```
From: noreply@tiktok-developer.com
Subject: Your TikTok app audit submission has been received
```

Email này chỉ confirmation, KHÔNG phải kết quả. Lưu để track.

---

## Trạng thái sau submit

Tab Audit Submission sẽ hiện:

```
Status: 🟡 Pending Review
Submitted: May 18, 2026
Expected response: within 5-14 business days
```

---

## Theo dõi trong khi đợi

### Có cần làm gì trong 5-14 ngày không?

❌ **KHÔNG sửa app/config**. Bất kỳ thay đổi nào (đổi scope, đổi redirect URI, đổi name) có thể khiến TT reject vì "config drift".

✅ **VẪN có thể dùng bot** ở chế độ Draft (không cần audit). User vẫn upload được vào Inbox.

✅ **Nếu YouTube link bị xóa/private** → vào Portal → update link mới. Đừng bỏ link cũ chưa update.

---

## Khi nhận email kết quả

### Case 1: ✅ APPROVED 🎉

Email subject: `Your TikTok app has been approved for production`

Action:
1. Mở bot LTTStudio VideoBot
2. Tab **🔧 Cài đặt** → mục TikTok
3. Tick checkbox `tiktok_audit_approved` = **True**
4. Tick `tiktok_enable_direct_post` = **True** (nếu chưa)
5. Bấm **Lưu**
6. Tab **📋 TT Audit** → bấm Refresh → status chuyển:
   ```
   ✅ Sẵn sàng submit TikTok audit (11 checks pass)
   → Audit flags: audit_approved=True, direct_post=True ✅
   ```
7. Tab **🎵 Manual TikTok** → loại đăng giờ có thêm **"Direct — Công khai (PUBLIC_TO_EVERYONE)"**

### Case 2: ⚠️ NEEDS REVISIONS

Email subject: `Action required: Your TikTok app submission`

Email sẽ liệt kê:
- Issue cụ thể (vd: "demo video does not show disclosure modal at scene 4")
- Khuyến nghị fix

Action:
1. Đọc kỹ email
2. Forward email cho dev (mình) → mình check code/script cần fix
3. Fix → re-record cảnh thiếu hoặc cả video
4. Re-upload YouTube → đổi link trong Portal
5. **Submit lại** (KHÔNG cần tạo app mới)

### Case 3: ❌ REJECTED

Email subject: `Your TikTok app submission has been rejected`

Action:
1. Đọc kỹ lý do reject (thường rất chi tiết)
2. Forward email cho dev → diagnose root cause
3. Fix triệt để code + re-record demo
4. Đợi **48h** trước khi submit lại (để tránh spam flag)
5. Submit lần 2

---

## Common rejection patterns + fix

| Lý do TT reject | Fix |
|---|---|
| "Demo video does not show pre-OAuth disclosure" | Quay lại cảnh 4 với disclosure modal dừng đủ 6s |
| "Privacy level not user-selectable" | Verify dialog có dropdown thật, không phải label read-only |
| "Privacy URL returns 404 / 403" | Verify URL accessible từ browser ngoài VN |
| "Scope justification too generic" | Đọc 3 đoạn justification trên — paste y chang |
| "App icon missing/wrong format" | Verify icon 1024×1024 PNG, alpha background |
| "User consent timestamp not captured" | Check audit_log.jsonl có field `user_confirmed_at` |
| "Audio in demo unclear" | Re-export video với audio bitrate 192k+ |
| "Demo video too short (<60s)" | Quay lại đủ 14 cảnh, target 3 phút |

---

## ⏰ Timeline thực tế

```
Day 0     : Submit
Day 1-2   : TT receive + queue (no email)
Day 3-7   : Reviewer xem video + test app
Day 7-14  : Final decision + email
```

Nếu **quá 14 ngày** không có email → vào Portal kiểm tra status. Nếu vẫn pending → contact support@tiktok-developer.com (rất hiếm cần).

---

**Checkpoint sau Bước 5**:

```
□ Đã submit form với đủ Demo URL + Use Case + 3 Scope Justifications
□ Đã upload app icon (nếu portal yêu cầu)
□ Đã tick compliance checkboxes
□ Đã nhận email confirmation từ noreply@tiktok-developer.com
□ Portal hiện "Pending Review"
□ KHÔNG sửa app/config trong 5-14 ngày tới
```

---

**Sang Bước 6**: Đợi email kết quả. Không có việc cần làm tiếp.

Nếu vướng → mở `06_TROUBLESHOOTING.md`.
