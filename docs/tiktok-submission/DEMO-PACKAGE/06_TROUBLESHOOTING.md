# 🆘 06 — TROUBLESHOOTING

> Các sự cố thường gặp khi hoàn thiện demo video. Tìm triệu chứng → áp fix.

---

## A. Vấn đề khi review video OBS (Bước 1)

### A1. Video quá ngắn (< 2 phút)

**Triệu chứng**: File OBS chỉ ~1-2 phút, thiếu nhiều cảnh.

**Fix**: Quay lại bằng cách:
```powershell
cd "D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook"
python scripts/_demo_record.py
```

### A2. Thiếu cảnh Disclosure Modal (cảnh 4)

**Triệu chứng**: OAuth flow nhảy thẳng vào browser, không thấy modal màu tím.

**Nguyên nhân**:
- Code disclosure modal chưa wire đúng — kiểm tra:
  ```
  D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook\gui\tiktok_account_tab.py
  → tìm "request_oauth_consent"
  ```
- Hoặc khi quay, account chưa disconnect → bot bypass disclosure

**Fix**:
1. Disconnect account klcloset96
2. Quay lại — modal sẽ hiện đúng

### A3. Thiếu cảnh Consent Dialog (cảnh 7)

**Triệu chứng**: Click "Đăng TikTok" → upload luôn, không có dialog.

**Nguyên nhân**: Bot crash khi gọi creator_info — kiểm tra terminal log.

**Fix**: Verify account còn token hợp lệ:
```powershell
python -c "from core.tiktok.token_store import get_default_store; print([(a.display_name, a.is_token_valid()) for a in get_default_store().all_accounts()])"
```

---

## B. Vấn đề khi tạo voice ElevenLabs (Bước 2)

### B1. Hết free tier (10.000 chars/tháng)

**Triệu chứng**: ElevenLabs báo "Quota exceeded".

**Fix**:
- Đợi đầu tháng sau (tier reset)
- Hoặc dùng [alternative TTS](https://www.naturalreaders.com/online/) miễn phí
- Hoặc tự đọc bằng mic (đỡ chuyên nghiệp nhưng OK với TT reviewer)

### B2. Voice đọc sai URL/số

**Triệu chứng**: ElevenLabs đọc `lttstudio.top` thành "lttstudio dot top" (kỳ cục).

**Fix**: Đã pre-edit trong `01_VOICE-SCRIPTS.md` rồi — dùng "slash" + "dot". Nếu vẫn lỗi:
```
"L-T-T Studio"   thay vì  "LTTStudio"
"API version 2"  thay vì  "API v2"
"AES-128"        →  "AES one twenty-eight"
"open_id"        →  "open underscore I D"
```

### B3. Voice cảm thấy robotic

**Fix**: Trong ElevenLabs Settings:
- Giảm **Stability** xuống 0.35 (more emotional)
- Giữ **Similarity** 0.75
- Tăng **Style** lên 0.20

### B4. Voice quá nhanh / chậm

**Fix**:
- Trong ElevenLabs: chỉnh **Speed** (0.85-1.15)
- Hoặc trong CapCut: chỉnh Speed trên audio clip (0.9-1.1)

---

## C. Vấn đề khi edit CapCut (Bước 3)

### C1. Voice không đồng bộ với video

**Triệu chứng**: Voice nói "click Continue" khi video chưa thấy click.

**Fix**: Drag MP3 clip trên timeline tới đúng timestamp trong `02_TIMING-REFERENCE.md`. Hoặc:
- Nếu video tới sớm → speed up voice 1.05x
- Nếu video tới muộn → slow voice 0.95x

### C2. Voice scene 7 dài hơn cảnh

**Triệu chứng**: Voice ~40s nhưng cảnh consent dialog chỉ ~30s.

**Fix** (3 cách, chọn 1):
- A: Bắt đầu voice từ 02:05 (sớm 5s) — voice fade-in lúc dialog mở
- B: Slow video phần dialog xuống 0.85x → kéo cảnh thành 35s
- C: Cắt bớt voice 1 câu (ví dụ bỏ "as required by TikTok's November 2024 policy")

### C3. Export bị lag / fail

**Fix**:
- Settings → Performance → bật **Hardware Acceleration**
- Đóng các app khác (Chrome, Discord)
- Cleanup ổ đĩa, cần ~5 GB rảnh
- Đổi encoder: **H.264** (không phải H.265 HEVC)

### C4. Audio quá nhỏ / không nghe

**Fix**:
- Click vào clip voice → Volume slider = 0 dB (max)
- Verify audio gốc video = MUTED
- Verify Speaker Boost trong ElevenLabs lúc generate = ON

---

## D. Vấn đề khi upload YouTube (Bước 4)

### D1. YouTube báo "Copyright claim"

**Triệu chứng**: Audio bị flag là copyright.

**Nguyên nhân**: Voice ElevenLabs OK nhưng có thể nhạc nền (nếu thêm) bị flag.

**Fix**:
- Re-export trong CapCut, KHÔNG có nhạc nền
- Hoặc dispute claim trên YouTube (rất chậm, không khuyên)

### D2. Video lên YouTube bị blurry/lag

**Triệu chứng**: Upload xong xem trên YouTube thấy mờ.

**Nguyên nhân**: YouTube cần ~30 phút sau upload để process bản 1080p HD.

**Fix**: Đợi 30 phút → reload trang → chọn 1080p ở settings video player.

### D3. Bỏ quên set Unlisted

**Triệu chứng**: Set Private nhầm → TT reviewer không xem được.

**Fix**: Vào YouTube Studio → Videos → click video → Visibility → Edit → **Unlisted** → Save.

### D4. Link YouTube bị từ chối khi paste vào TT portal

**Triệu chứng**: TT portal báo "Invalid video URL".

**Fix**: Verify format link:
- ✅ `https://youtu.be/AbCdEfGhIjK`
- ✅ `https://www.youtube.com/watch?v=AbCdEfGhIjK`
- ❌ `https://studio.youtube.com/video/AbCdEfGhIjK/edit` (link admin, không paste được)

---

## E. Vấn đề khi submit TT Portal (Bước 5)

### E1. Portal báo "Demo video URL invalid"

**Fix**:
- Test link trong Incognito browser trước
- Đổi từ `youtu.be/...` sang `youtube.com/watch?v=...` (đôi khi portal pick format này)
- Đảm bảo video đã process xong trên YouTube (đợi 30 phút sau upload)

### E2. Portal báo "Scope justification too short"

**Fix**: Mỗi scope cần ≥100 ký tự English. Đã chuẩn bị sẵn trong `05_TIKTOK-PORTAL-SUBMIT.md` — paste y nguyên.

### E3. Portal báo "App icon required"

**Fix**: Upload file `assets/lttstudio-icon-1024.png` từ folder DEMO-PACKAGE.

### E4. Portal không cho Submit

**Nguyên nhân**: Còn field bắt buộc chưa điền (đỏ).

**Fix**: Scroll lên đầu form → tìm các field có dấu * đỏ → điền đủ.

---

## F. Vấn đề sau khi submit

### F1. Không nhận email confirmation

**Fix**:
- Check Spam folder
- Check email registered trong TT account (settings)
- Đợi 30 phút sau submit, nếu vẫn không có → contact dev support

### F2. Status pending quá 14 ngày

**Fix**:
- Vào Portal → tab Audit Submission
- Nếu vẫn "Pending" sau 14 ngày → contact:
  ```
  Email: support@tiktok-developer.com
  Subject: App audit pending review > 14 days
  Body: include App ID + Submission date
  ```

### F3. Nhận email "Needs revisions"

**Fix**: Đọc kỹ lý do → xem table "Common rejection patterns" trong `05_TIKTOK-PORTAL-SUBMIT.md`.

Hoặc forward email cho dev (mình) → mình diagnose + viết fix plan.

---

## G. Vấn đề "tự test sau khi approved"

### G1. App đã approved nhưng PUBLIC_TO_EVERYONE vẫn không hiện

**Fix**:
1. Verify Settings → `tiktok_audit_approved = True` đã Save
2. Tab Manual TikTok → bấm 🔄 reload accounts
3. Reload xong combo "Loại đăng" phải có 4 options:
   ```
   Draft — Inbox (an toàn)
   Direct — Riêng tư (SELF_ONLY)
   Direct — Người theo dõi (FOLLOWER_OF_CREATOR)
   Direct — Công khai (PUBLIC_TO_EVERYONE)   ⭐ MỚI
   ```

### G2. Upload PUBLIC_TO_EVERYONE fail với HTTP 403

**Fix**: TT portal có thể chưa fully propagate. Đợi 24h sau email approval rồi thử lại.

---

## H. Sự cố khẩn cấp

### Cần re-record toàn bộ?

```powershell
cd "D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook"

# 1. Disconnect TT account
# (mở bot, tab Tài khoản TikTok, click Disconnect)

# 2. Start OBS Recording

# 3. Chạy lại script automation:
python scripts/_demo_record.py

# 4. Manual OAuth khi script pause

# 5. Đợi script chạy nốt

# 6. Stop OBS
```

### Cần re-edit voice cho 1 cảnh?

1. Mở `01_VOICE-SCRIPTS.md` → paste cảnh cần re-do vào ElevenLabs
2. Generate → Download → save với tên cũ (overwrite)
3. Mở CapCut → drag file MP3 mới → đè lên clip cũ

### Cần re-submit TT Portal?

Sau khi reject hoặc cần update:
1. Vào portal → tab Audit Submission
2. Bấm **Resubmit** (nút bên cạnh status)
3. Upload link YouTube mới (nếu video thay đổi)
4. Submit lại

---

## ☎️ Liên hệ hỗ trợ

| Vấn đề | Liên hệ |
|---|---|
| Bug trong bot LTTStudio | Forward log + screenshot cho dev (mình) |
| Email TT reject không hiểu | Forward email cho dev — mình dịch + suggest fix |
| Cài đặt Cloud / DNS / domain | Cá nhân tự xử |
| YouTube/CapCut/ElevenLabs vấn đề | Google search + support của họ |

---

**Quay về**: [README.md](README.md) | [00_QUY-TRINH-TONG-THE.md](00_QUY-TRINH-TONG-THE.md)
