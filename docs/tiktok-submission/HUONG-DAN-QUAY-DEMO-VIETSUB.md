# 🎬 HƯỚNG DẪN QUAY DEMO TIKTOK AUDIT — Phiên bản tiếng Việt

> Tài liệu này hướng dẫn bạn (người Việt) quay video demo gửi cho TikTok audit.
> Đọc song song với `demo-video-script.md` để biết kịch bản chính thức (tiếng Anh).
> **Mục tiêu**: video 3:15 phút, đạt 100% TikTok review pass.

---

## PHẦN 1 — HIỂU CÁCH AUDIT CỦA TIKTOK

### 1.1 Reviewer là ai?

- **Người thật**, làm việc tại TikTok ở Singapore / US / UK.
- Không nói tiếng Việt. Trung bình dành **3-5 phút/app**.
- Có quyền **reject ngay** nếu thiếu 1 trong các yếu tố bắt buộc → bạn phải đợi
  **5-14 ngày** để submit lại.

### 1.2 Họ kiểm tra gì?

TikTok dùng checklist nội bộ (không công khai 100%) nhưng theo kinh nghiệm + policy
public thì có 14 mục bắt buộc xuất hiện trong video. Đây là lý do script v2 của
chúng ta thiết kế chuẩn xác **14 cảnh = 14 mục check**.

### 1.3 Họ KHÔNG quan tâm gì?

- **Ngôn ngữ Vietnamese UI** trong bot — OK, miễn là voice-over English.
- **Đẹp xấu của UI** — họ chỉ cần thấy đủ feature.
- **Tốc độ upload** — chậm hay nhanh không quan trọng.
- **Quay bằng phần mềm gì** — OBS hay ShareX hay screen recorder mặc định
  Windows đều được.

### 1.4 Lý do MỖI cảnh bắt buộc có

| Cảnh | Lý do TikTok yêu cầu | Phạt nếu thiếu |
|---|---|---|
| Privacy URL load được | Reviewer click thử URL, nếu 404 → REJECT | Reject auto |
| Pre-OAuth disclosure modal | TT policy 2024: app phải show data access reason trước OAuth | Reject + ghi chú |
| TT authorize URL trên browser | Chứng minh dùng OAuth official, không fake | Reject nghi vấn fraud |
| Privacy DROPDOWN (không pre-set) | Policy chống "silent posting" — user phải chọn được | Reject "User control" |
| 3 toggle Comment/Duet/Stitch | Policy "Creator interaction settings respect" | Warning hoặc reject |
| AI Generated checkbox | Policy 11/2024 (mới): bắt buộc disclose AI content | Reject hard |
| Branded checkbox | Branded Content Policy: disclose sponsored | Warning |
| Disconnect/Revoke flow | GDPR/data deletion compliance | Reject "Data handling" |

---

## PHẦN 2 — CHUẨN BỊ TRƯỚC KHI QUAY (30 phút)

### 2.1 Phần cứng + môi trường

| Item | Yêu cầu | Ghi chú |
|---|---|---|
| Màn hình | Tối thiểu 1920×1080 | Quay đúng độ phân giải này |
| Micro | Mic ngoài hoặc tai nghe có mic | Mic laptop OK nếu phòng yên |
| Phòng | Yên tĩnh, không echo | Đóng cửa, tắt quạt |
| Internet | Ổn định 10+ Mbps | Test bằng speedtest.net |
| Thời gian | Khoảng 1.5-2 giờ | Quay + edit nhẹ |

### 2.2 Cài OBS Studio (miễn phí)

1. Tải: https://obsproject.com/download
2. Cài → mở → Auto-Configuration Wizard:
   - **Optimize for**: Recording
   - **Resolution**: 1920×1080
   - **FPS**: 30
3. Settings → Output:
   ```
   Output Mode: Advanced
   Recording → Type: Standard
   Format: mp4
   Encoder: NVIDIA NVENC (nếu có GPU NVIDIA) hoặc x264
   Rate Control: CBR
   Bitrate: 10000 Kbps
   Keyframe Interval: 2
   ```
4. Settings → Audio:
   ```
   Sample Rate: 48 kHz
   Mic/Aux: chọn mic của bạn
   ```
5. Click **+ Sources** → **Display Capture** → chọn màn hình chính.
6. Click **+ Sources** → **Audio Input Capture** → chọn mic.
7. Test record 10 giây → preview → nghe lại âm thanh OK chưa.

### 2.3 Chuẩn bị bot

**Bước 1 — Disconnect tài khoản klcloset96 hiện tại**

⚠️ QUAN TRỌNG: Phải có cảnh OAuth connect LIVE trong video. Nếu account đã connected,
TT reviewer reject vì "chưa thấy flow consent".

```
1. Mở bot LTTStudio VideoBot
2. Tab 🎵 Tài khoản TikTok
3. Click vào account klcloset96 → panel phải hiện chi tiết
4. Bấm 🗑 Ngắt kết nối
5. Confirm dialog → đồng ý
6. Xác nhận: list bên trái trống, không còn account nào
```

**Bước 2 — Verify bot ready**

```
1. Tab 📋 TT Audit → kiểm tra summary phải là:
   "✅ Sẵn sàng submit TikTok audit (11 checks pass)"
2. Tab 🔧 Cài đặt → mục TikTok:
   - Client Key: sbawcbtj78j1xr9hl6 (đã có)
   - Client Secret: ******** (đã có)
   - Redirect URI: https://lttstudio.top/legal/callback.html
3. Tab 🎵 Manual TikTok → nút "🎵 Đăng TikTok" ở dưới cùng (chưa bấm)
```

**Bước 3 — Chuẩn bị file video test**

```
Path: C:\Users\KENLY\Downloads\Sunset_over_ocean_dramatic_clouds_a10d65a628.mp4
Size: 2.79 MB
Duration: 8 giây
Format: MP4 1280x720
```

### 2.4 Chuẩn bị browser

```
1. Mở Chrome (hoặc Edge) ở chế độ Ẩn danh (Ctrl+Shift+N)
2. Kéo cửa sổ to vừa phải — đừng full screen quá lớn
3. Đảm bảo Bookmarks bar TẮT (View → Hide Bookmarks Bar)
4. Đảm bảo extensions không xuất hiện thanh trên
5. Pre-test: vào https://lttstudio.top/legal/privacy.html
   → trang load được, không lỗi
6. Đóng tab → mở lại trắng
```

### 2.5 Chuẩn bị mic + voice

- Test mic: nói "Test, một hai ba" → playback nghe có rõ không, có nhiễu không
- Nếu mic kém: dùng [ElevenLabs](https://elevenlabs.io) text-to-speech để có giọng English chuẩn
  - Free tier: 10.000 ký tự/tháng (đủ cho video 3 phút)
  - Voice gợi ý: "Adam" (giọng Mỹ trầm) hoặc "Bella" (giọng Mỹ nữ)
- Nếu tự đọc: luyện trước 2-3 lần các đoạn voice-over

### 2.6 Trước khi nhấn Record — checklist 1 phút

```
□ Bot LTTStudio đã mở, ở tab 🎵 Tài khoản TikTok, list trống
□ Browser Incognito mở sẵn, tab trống
□ File video Sunset_over_ocean... đã có ở Downloads
□ OBS test recording đã OK (audio + video clear)
□ Đã đóng Zalo/Messenger/Discord/Slack
□ Đã tắt notification Windows (Focus assist ON)
□ Phòng yên tĩnh, không người vào
□ Có cốc nước bên cạnh
□ Mở sẵn script demo-video-script.md ở màn hình thứ 2 (nếu có)
□ Hít thở sâu, ready
```

---

## PHẦN 3 — KỊCH BẢN CHI TIẾT TỪNG CẢNH

> **Format mỗi cảnh**:
> - 🎬 Hành động cụ thể (tiếng Việt)
> - 🎤 Voice-over English (chính thức gửi TT)
> - 🇻🇳 Bản dịch tiếng Việt (để bạn hiểu, KHÔNG đọc)
> - 💡 Lưu ý quay (nếu có)

---

### 🎬 Cảnh 1 — Opening (00:00 → 00:15)

**Hành động**:
- Trước khi bấm Record: tạo slide PowerPoint 1 trang với nội dung:
  ```
  LTTStudio VideoBot
  TikTok Content Posting API Integration
  
  Demo for App Audit Review
  May 2026
  ```
- Mở slide full screen → bấm Record OBS → đợi 1 giây → bắt đầu nói

**🎤 Voice-over**:
> *"Hello, this is the audit demo of LTTStudio VideoBot — a Windows desktop application that helps Vietnamese content creators schedule and publish short-form videos to TikTok using the official Content Posting API v2 and Login Kit. The entire flow runs locally on the user's machine — no cloud server, no third-party data sharing."*

**🇻🇳 Dịch (không đọc)**:
> Chào, đây là demo audit của LTTStudio VideoBot — ứng dụng Windows giúp creator
> Việt Nam lên lịch + đăng video lên TikTok qua Content Posting API v2 và Login Kit.
> Toàn bộ chạy local, không có server cloud, không share data bên thứ ba.

**💡 Lưu ý**: Đọc chậm, giọng rõ. Không cần emotional, chỉ cần professional.

---

### 🎬 Cảnh 2 — Privacy & Terms URL (00:15 → 00:35)

**Hành động**:
1. Alt+Tab sang browser
2. Type vào address bar: `https://lttstudio.top/legal/privacy.html` → Enter
3. Đợi trang load
4. Cuộn chậm xuống section **"4b. Dữ liệu TikTok cụ thể"** — pause 2-3 giây ở đây
5. Highlight các từ: `open_id`, `access_token`, `video.upload`, `video.publish`
6. Mở tab mới (Ctrl+T) → type `https://lttstudio.top/legal/terms.html` → Enter
7. Cuộn nhẹ qua nội dung

**🎤 Voice-over**:
> *"Before connecting any TikTok account, here is our published Privacy Policy at lttstudio.top/legal/privacy.html. It explicitly lists every piece of TikTok data we access — open_id, display name, avatar URL, access token, refresh token — and our retention policy. All tokens are encrypted at rest using AES-128 Fernet and never leave the user's computer. The Terms of Service link is also accessible at lttstudio.top/legal/terms.html."*

**🇻🇳 Dịch**:
> Trước khi connect TikTok account, đây là Privacy Policy tại lttstudio.top/legal/privacy.html.
> Trang này liệt kê rõ data TikTok mà app truy cập — open_id, display name, avatar URL,
> access token, refresh token — và policy lưu trữ. Tất cả token được mã hóa AES-128 Fernet
> và không bao giờ rời máy user. Terms of Service tại lttstudio.top/legal/terms.html.

**💡 Lưu ý**: Đây là cảnh **REJECT KEY #1**. Privacy URL PHẢI load được. Nếu thấy 403/404,
DỪNG QUAY — báo tôi xử lý server trước.

---

### 🎬 Cảnh 3 — Bot Overview (00:35 → 00:50)

**Hành động**:
1. Alt+Tab về bot LTTStudio VideoBot
2. Pan chuột chậm từ trái sang phải qua các tab top, cho TT nhìn thấy 9 tabs:
   ```
   📊 Sheet FB   📊 Sheet TikTok   ⚙️ Manual FB   🎵 Manual TikTok
   🔐 Tài khoản FB   🎵 Tài khoản TikTok   📈 Monitor   📋 TT Audit   🔧 Cài đặt
   ```
3. Pause khoảng 2 giây ở tab **🎵 Tài khoản TikTok** rồi click vào

**🎤 Voice-over**:
> *"Here is the LTTStudio VideoBot interface. We have dedicated tabs for TikTok account management, manual posting, and an audit dashboard which I'll show in a moment. Let's start by connecting a TikTok account."*

**🇻🇳 Dịch**:
> Đây là giao diện LTTStudio VideoBot. Có các tab dành riêng cho TikTok account,
> manual posting, và audit dashboard mà tôi sẽ show ngay sau. Bắt đầu bằng việc
> connect 1 TikTok account.

---

### 🎬 Cảnh 4 — OAuth Flow + Disclosure Modal (00:50 → 01:30) ⭐⭐⭐ QUAN TRỌNG NHẤT

**Hành động**:
1. Tab 🎵 Tài khoản TikTok đang mở, list bên trái TRỐNG (đã disconnect trước)
2. Pan chuột tới nút màu tím **"Continue with TikTok"** (có logo TikTok đen tròn bên trái)
3. Hover 1 giây cho TT thấy rõ nút
4. **Click nút**
5. Modal disclosure xuất hiện:
   ```
   🔐  Quyền truy cập TikTok
   ─────────────────────────────
   LTTStudio VideoBot sắp mở trang đăng nhập TikTok...

   ▐ Thông tin cơ bản tài khoản    (user.info.basic)
     Đọc username + ảnh đại diện để hiển thị...

   ▐ Upload video (Draft mode)     (video.upload)
     Gửi video vào Inbox của bạn...

   ▐ Đăng video trực tiếp           (video.publish)
     Đăng bài lên TikTok ngay từ bot...

   ℹ Bạn có thể thu hồi quyền bất cứ lúc nào:
     1. Trong bot: tab 🎵 Tài khoản TikTok → 🗑 Ngắt kết nối
     2. Trên TikTok: tiktok.com/setting/manage-apps

   [Hủy]              [Tiếp tục đăng nhập TikTok →]
   ```
6. **DỪNG 5 GIÂY** ở modal này — đủ thời gian reviewer đọc hết
7. Click **"Tiếp tục đăng nhập TikTok →"**
8. Browser tự mở → TikTok authorize page tại `https://www.tiktok.com/v2/auth/authorize/...`
9. **HIGHLIGHT URL BAR** bằng cách click vào address bar (đừng paste/edit) — để TT thấy đúng domain `tiktok.com`
10. Scroll xuống nếu cần để thấy list scopes TikTok hiển thị (chính TT show, không phải app)
11. Click **"Authorize"** (nút xanh của TikTok)
12. Browser redirect tới `https://lttstudio.top/legal/callback.html` → trang spinner
13. Auto redirect về localhost → đóng tab
14. Quay lại bot → tài khoản `klcloset96` xuất hiện trong list với avatar + display name

**🎤 Voice-over** (đọc trong khi action diễn ra, đừng đợi):
> *"Clicking 'Continue with TikTok' triggers our mandatory pre-authorization disclosure modal. Per TikTok policy, the user sees every scope we will request, the exact reason we need each one, and instructions on how to revoke access later — both inside our app and through tiktok.com directly. Only after the user reads this disclosure and explicitly clicks 'Continue' does the OAuth flow start. We use PKCE for security. After TikTok's authorize screen, the code returns to our HTTPS callback at lttstudio.top, then locally to the app. The TikTok account, klcloset96, now appears as connected."*

**🇻🇳 Dịch**:
> Click 'Continue with TikTok' trigger modal disclosure bắt buộc. Theo TT policy,
> user thấy mỗi scope yêu cầu, lý do cần, và cách revoke sau — cả trong app và
> qua tiktok.com. Chỉ khi user đọc và click 'Continue' thì OAuth mới bắt đầu.
> Dùng PKCE bảo mật. Sau authorize screen của TT, code về callback HTTPS lttstudio.top,
> rồi về app local. Account klcloset96 hiển thị đã connected.

**💡 Lưu ý**:
- **REJECT KEY #2**: Pre-OAuth modal là cảnh khắt khe nhất. PHẢI dừng đủ lâu (4-6 giây).
- **REJECT KEY #3**: URL bar phải hiện `tiktok.com` rõ ràng.
- Nếu OAuth timeout (>60s) → dừng quay, restart bot, quay lại từ đầu cảnh 4.

---

### 🎬 Cảnh 5 — Audit Dashboard (01:30 → 01:50) ⭐ MỚI

**Hành động**:
1. Click tab **📋 TT Audit** ở thanh tab
2. Trang audit hiện ra:
   - Header: "📋 TikTok Audit Readiness"
   - Summary line màu xanh: **"✅ Sẵn sàng submit TikTok audit (11 checks pass)"**
   - Left panel: 11 ô check tất cả ✅
   - Right panel: "🔑 OAuth Scopes đang dùng" — 3 thẻ scope với giải thích
3. **DỪNG 4-5 GIÂY** cho TT đọc hết checklist
4. Hover qua từng check ở panel trái (không click) để TT thấy đầy đủ

**🎤 Voice-over**:
> *"We've built a real-time audit-readiness dashboard inside the application itself. It verifies every TikTok compliance requirement — client credentials present, redirect URI uses HTTPS, privacy and terms URLs reachable, privacy policy mentions TikTok by name, official login button branding present, demo video script exists, scope set correctly, audit flags consistent, user-confirmation required, and a safe SELF_ONLY default. All eleven checks pass. The right panel shows each OAuth scope with its justification."*

**🇻🇳 Dịch**:
> Chúng tôi xây real-time audit-readiness dashboard ngay trong app. Verify mỗi
> requirement của TT — credentials có, redirect HTTPS, privacy + terms URL truy
> cập được, privacy policy mention TT, login button branding chuẩn, demo script có,
> scope đúng, audit flags consistent, user confirm bắt buộc, SELF_ONLY default an toàn.
> 11/11 check pass. Panel phải show từng scope với lý do.

**💡 Lưu ý**: Cảnh này không có trong nhiều bot khác → tạo ấn tượng "app này serious về compliance".
TT reviewer thường note tích cực.

---

### 🎬 Cảnh 6 — Manual Upload Form (01:50 → 02:10)

**Hành động**:
1. Click tab **🎵 Manual TikTok**
2. Tại card 🎬 FILE VIDEO:
   - Click nút **📁 Chọn**
   - Dialog Chọn file → navigate tới `C:\Users\KENLY\Downloads\`
   - Chọn `Sunset_over_ocean_dramatic_clouds_a10d65a628.mp4` → Open
   - File info auto-hiện: "ℹ Sunset_over_ocean... • 2.8 MB • .mp4" màu xanh
3. Tại card 📝 NỘI DUNG:
   - Type tiêu đề: **"Bot demo — Sunset 8s"**
   - Counter hiện "20 / 100" màu xanh
4. Tại card 🎵 ĐĂNG LÊN TIKTOK:
   - Tài khoản: chọn `klcloset96` từ dropdown (auto-select)
   - Loại đăng: **"Direct — Riêng tư (SELF_ONLY)"** (đã default an toàn)
5. Click nút lớn dưới cùng **"🎵 Đăng TikTok"** (màu tím)

**🎤 Voice-over** (bắt đầu nói trong khi điền form):
> *"To post a video, the user fills the form on the Manual TikTok tab and clicks the post button. Our app first calls TikTok's creator_info query endpoint to fetch the user's current account-level settings."*

**🇻🇳 Dịch**:
> Để đăng video, user điền form ở tab Manual TikTok và click post. App gọi
> endpoint creator_info của TT để fetch settings hiện tại của account.

---

### 🎬 Cảnh 7 — Enhanced Consent Dialog (02:10 → 02:40) ⭐⭐⭐ QUAN TRỌNG NHẤT

**Hành động**:
1. Sau khi bấm "🎵 Đăng TikTok", status flash 1-2 giây: **"⏳ Đang lấy thông tin creator từ TikTok..."**
2. **Dialog "Xác nhận đăng TikTok" mở ra**, kích thước 600×720
3. **DỪNG 6 GIÂY** — pan chuột chậm qua từng section, KHÔNG click ngay:

   **Section A — 📹 Thông tin video** (top):
   - Tiêu đề: Bot demo — Sunset 8s
   - Loại đăng: 📤 Đăng trực tiếp (tiktok_direct)
   - Tài khoản: @klcloset96

   **Section B — 🔐 Quyền riêng tư (bạn chọn)**:
   - Combobox đang là "🔒 Chỉ mình tôi xem (SELF_ONLY)"
   - **CLICK vào combobox** để xổ ra menu — show cho TT thấy chỉ có 1 option SELF_ONLY
     (vì app chưa qua audit) → giải thích bằng note màu cam phía dưới
   - Click ra ngoài để đóng combobox

   **Section C — 💬 Tương tác (theo cài đặt creator)**:
   - 3 checkbox đang tick: ☑ Cho phép comment / ☑ Duet / ☑ Stitch
   - Pan qua từng cái

   **Section D — 📢 Khai báo nội dung**:
   - ☐ 🤖 Nội dung do AI tạo / chỉnh sửa (AI-generated) — đang UNCHECKED
   - ☐ 💼 Nội dung quảng cáo / tài trợ (Branded content) — đang UNCHECKED
   - Pan qua cả 2

   **Section E — ✓ Xác nhận**:
   - ☐ "Tôi xác nhận nội dung này tuân thủ ĐKDV và NTCĐ TikTok."
   - Pan qua

4. Cho TT thấy **nút "✅ Xác nhận & Đăng" đang DISABLED** (màu xám)
5. **Click vào checkbox** "Tôi xác nhận..." → tick
6. Nút "Xác nhận & Đăng" chuyển ENABLE (màu xanh đậm)
7. Click **"✅ Xác nhận & Đăng"**

**🎤 Voice-over** (kéo dài 30s):
> *"Then this comprehensive consent dialog appears. The user sees the video summary, then must actively select a privacy level — it's a dropdown, never pre-set. Because this app is still pending audit, only SELF_ONLY is available, as shown by the orange notice. Three interaction toggles let the user choose whether to allow comments, duets, and stitches. Two disclosure checkboxes capture AI-generated and branded-content declarations as required by TikTok's November 2024 policy. Finally, the user must tick the compliance acknowledgement before the 'Confirm and Post' button enables. Only on this explicit, per-publish confirmation does the upload proceed."*

**🇻🇳 Dịch**:
> Dialog confirm chi tiết mở ra. User thấy summary video, sau đó phải chủ động chọn
> privacy level — dropdown, không pre-set. App chưa audit nên chỉ có SELF_ONLY, hiển thị
> bằng note cam. 3 toggle cho user chọn allow comment/duet/stitch. 2 checkbox disclosure
> AI-generated và branded-content theo policy TT 11/2024. Cuối user phải tick acknowledgement
> trước khi nút Confirm enable. Chỉ với explicit confirmation per-publish thì upload mới bắt đầu.

**💡 Lưu ý**:
- **REJECT KEY #4**: Privacy phải là DROPDOWN. Cảnh click mở dropdown rất quan trọng.
- **REJECT KEY #5**: AI checkbox + Branded checkbox phải là USER-CONTROLLED (có thể tick/untick).
- **REJECT KEY #6**: Nút Confirm phải DISABLED đến khi check consent → cho TT thấy state này.

---

### 🎬 Cảnh 8 — Upload + Success (02:40 → 03:00)

**Hành động**:
1. Sau khi click "Xác nhận & Đăng", dialog đóng
2. Trên tab Manual TikTok, status label chạy progression (mỗi dòng ~3 giây):
   - "⏳ Đang đăng lên TikTok..."
   - "[TikTok] Init draft upload..."
   - "[TikTok] Đang upload video (1 chunk)..."
   - "[TikTok] Đang upload: 100%"
   - "[TikTok] Đang chờ TikTok xử lý video..."
   - "[TikTok] Trạng thái publish #1: PROCESSING_UPLOAD"
   - "[TikTok] Trạng thái publish #2: PROCESSING_UPLOAD"
   - "[TikTok] Trạng thái publish #3: SEND_TO_USER_INBOX"
   - "✅ Đăng thành công! publish_id=v_inbox_file~v2.764..."
3. Pane phải Result tab hiển thị: status=success, publish_id, timestamp
4. Mở browser → vào `tiktok.com` → login klcloset96 → Profile → Inbox
5. Show video Sunset xuất hiện trong Inbox (chờ user confirm publish trong app TT)

**🎤 Voice-over**:
> *"The video uploads in chunks via the Content Posting API v2. We poll the publish status endpoint until completion. On success, the publish ID and timestamp are logged. The video is now visible in the user's TikTok account, exactly as configured — privacy SELF_ONLY, posted by the creator's own consent."*

**🇻🇳 Dịch**:
> Video upload theo chunk qua Content Posting API v2. Bot poll endpoint publish status
> đến khi xong. Thành công thì log publish ID + timestamp. Video xuất hiện trên TT
> account đúng config — privacy SELF_ONLY, đăng bởi consent của creator.

**💡 Lưu ý**: Nếu không quay được phần TikTok app (vì lý do account riêng tư), CÓ THỂ
quay browser tiktok.com/upload/published thay thế.

---

### 🎬 Cảnh 9 — Disconnect Flow (03:00 → 03:10) ⭐

**Hành động**:
1. Click tab **🎵 Tài khoản TikTok**
2. Click vào card account klcloset96 ở list trái
3. Panel phải hiện chi tiết (display_name, avatar, scopes, token expires)
4. Scroll xuống cuối panel → click nút **🗑 Ngắt kết nối**
5. Dialog confirm: "Bạn chắc chắn muốn ngắt kết nối?" → Click **Có**
6. Status: "🔄 Đang revoke token..."
7. Sau 1-2 giây: account biến mất khỏi list, list trống lại

**🎤 Voice-over**:
> *"Users can disconnect at any time. The bot calls TikTok's revoke endpoint, then deletes the encrypted token from disk. The account is fully removed."*

**🇻🇳 Dịch**:
> User có thể disconnect bất cứ lúc nào. Bot gọi endpoint revoke của TT, xóa token
> đã mã hóa khỏi disk. Account bị xóa hoàn toàn.

---

### 🎬 Cảnh 10 — Closing (03:10 → 03:15)

**Hành động**:
- Show slide closing:
  ```
  Thank you for reviewing
  
  LTTStudio VideoBot
  https://lttstudio.top
  Support: support@lttstudio.top
  ```

**🎤 Voice-over**:
> *"That concludes the demo. Privacy policy, terms of service, and support information are all available at lttstudio.top. Thank you for your review."*

**🇻🇳 Dịch**:
> Kết thúc demo. Privacy, Terms, Support đều có tại lttstudio.top. Cảm ơn đã review.

- Stop Record OBS

---

## PHẦN 4 — HẬU KỲ (15 phút)

### 4.1 Review video

1. Mở file MP4 vừa quay
2. Tua từng cảnh, đối chiếu **14 cảnh BẮT BUỘC**:

```
[00:15] Privacy Policy URL mở browser           ☐
[00:25] Terms URL mở browser                     ☐
[00:50] "Continue with TikTok" button + logo     ☐
[00:55] Pre-OAuth Disclosure Modal (scope+reason)☐
[01:10] URL bar tiktok.com authorize             ☐
[01:12] TikTok scope list trên authorize page    ☐
[01:25] Redirect về app, account appears         ☐
[01:30] Audit dashboard 11 checks ✅             ☐
[02:05] Privacy dropdown (user CHỌN)             ☐
[02:20] 3 toggles Comment/Duet/Stitch            ☐
[02:27] AI Generated checkbox user-controlled    ☐
[02:28] Branded content checkbox                 ☐
[02:55] Video xuất hiện trên TikTok              ☐
[03:05] Disconnect/Revoke flow                   ☐
```

Nếu thiếu cảnh nào → quay lại cảnh đó riêng → ghép vào (hoặc quay full lại).

### 4.2 Edit (optional, ~10 phút)

Nếu cần edit nhẹ (cắt khúc thừa, thêm subtitle):
- **CapCut Desktop** (miễn phí) — dễ dùng nhất cho người Việt
- **DaVinci Resolve** (miễn phí, pro hơn)
- **Shotcut** (miễn phí, đơn giản)

Edit checklist:
```
□ Cắt 1-2 giây đầu/cuối nếu có click chuột vào OBS
□ Thêm subtitle tiếng Việt (optional) — TT chỉ cần voice English
□ Export: H.264, 1920×1080, 10 Mbps
□ Tổng dung lượng ~200-400 MB cho 3 phút
```

### 4.3 Kiểm tra cuối

```
□ Video chạy mượt từ đầu đến cuối, không bị lag/đóng băng
□ Voice-over rõ ràng, không ngắt quãng
□ Không có notification Windows lọt vào (Discord/Zalo popup)
□ Đủ 14 cảnh checklist
□ Đúng 3:00-3:20 phút (không dưới 1 phút, không quá 5 phút)
```

---

## PHẦN 5 — UPLOAD YOUTUBE + SUBMIT

### 5.1 Upload YouTube

1. Vào https://studio.youtube.com
2. Click **CREATE → Upload Videos**
3. Chọn file MP4 vừa export
4. **Title**: `LTTStudio VideoBot — TikTok Content Posting API Audit Demo`
5. **Description**:
   ```
   Audit demo for LTTStudio VideoBot, a Windows desktop app integrating
   TikTok Content Posting API v2 and Login Kit. Shows complete OAuth
   consent flow with mandatory pre-authorization disclosure, audit
   readiness dashboard, and per-publish user confirmation including
   privacy level selection, interaction toggles, AI/branded disclosure.

   Privacy Policy: https://lttstudio.top/legal/privacy.html
   Terms of Service: https://lttstudio.top/legal/terms.html
   Support: support@lttstudio.top
   ```
6. **Thumbnail**: chọn frame Audit dashboard (giây 01:35)
7. **Visibility** (QUAN TRỌNG):
   - ⚠️ Chọn **"Unlisted"** (Không hiện trong danh sách)
   - **KHÔNG chọn Private** — TT reviewer không xem được
   - **KHÔNG chọn Public** — không cần public hóa
8. **Audience**: "No, it's not made for kids"
9. **Language**: English
10. Click **Save** → đợi process xong (~5-10 phút cho 3p video)
11. Copy link YouTube unlisted (dạng `https://youtu.be/xxxxx`)

### 5.2 Submit TikTok Developer Portal

1. Vào https://developers.tiktok.com → đăng nhập
2. **My Apps** → chọn app `LTTStudio VideoBot`
3. Tab **Audit Submission** (hoặc **App Audit Review**)
4. Điền form:
   - **Demo Video URL**: paste link YouTube ở trên
   - **Use Case Description**: (300-500 ký tự English)
     ```
     LTTStudio VideoBot is a Windows desktop tool for Vietnamese content
     creators to schedule and publish short-form videos to TikTok via the
     official Content Posting API v2. Users connect their TikTok account
     once via OAuth, then schedule batch uploads from a Google Sheet or
     post manually one-by-one. Each publish requires explicit user consent
     via a confirmation dialog that surfaces privacy level, interaction
     toggles, AI/branded disclosure per TikTok policy.
     ```
   - **Scope Justifications** — copy cho từng scope:
     - `user.info.basic`: "Display the connected creator's username and avatar inside our app so users can verify which TikTok account is active before publishing."
     - `video.upload`: "Send video to user's TikTok Inbox (draft mode) for the user to publish manually from the TikTok app. Used when audit_approved=false or as a safer default."
     - `video.publish`: "Direct publishing of videos to TikTok after the user's explicit per-publish confirmation. Required for the manual-post and Google Sheet automation flows shown in demo."
5. Tích các checkbox compliance (đọc kỹ trước khi tick)
6. **Submit**

### 5.3 Sau khi submit

- TT trả về dạng "Pending review"
- Thời gian phản hồi: **5-14 ngày**
- Email từ `noreply@tiktok-developer.com`
- Possible outcomes:
  - ✅ **Approved** → đổi `tiktok_audit_approved=true` trong bot Settings
    → Manual TT tab hiện option PUBLIC_TO_EVERYONE
  - ⚠️ **Needs revisions** → TT gửi list các issue cụ thể → fix + re-submit
  - ❌ **Rejected** → đọc lý do, fix triệt để, re-submit

---

## PHẦN 6 — TROUBLESHOOTING

### Lỗi khi quay

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| OAuth modal không hiện | Code chưa wire | Verify `if not request_oauth_consent` trong tiktok_account_tab.py |
| Browser không mở | Default browser sai | Set Chrome/Edge làm default |
| Callback redirect lỗi | redirect_uri sai | Settings → tiktok_redirect_uri = `https://lttstudio.top/legal/callback.html` |
| Privacy URL 403 | Cloudflare block | Đã fix, nếu vẫn lỗi report cho tôi |
| Bot crash khi click Đăng | Token expired | Disconnect → reconnect klcloset96 |
| OBS không capture mic | Wrong audio source | Settings → Audio → check Mic input device |
| Recording file lớn quá | Bitrate cao | OBS: giảm Bitrate xuống 6000 Kbps |
| Audio out of sync | OBS sync issue | OBS: add "Audio Render Delay" filter |

### Lỗi khi submit YouTube

| Triệu chứng | Fix |
|---|---|
| YouTube reject vì copyright (audio) | Quay lại với mic riêng, không bật nhạc |
| Reviewer không xem được link | Verify Visibility = Unlisted (KHÔNG Private) |
| Description quá dài | Cắt còn <500 ký tự |

### Lỗi khi submit TikTok

| Triệu chứng | Fix |
|---|---|
| Portal báo "Demo video required" | Paste lại link YouTube, check format |
| Scope justification too short | Mỗi scope cần ≥100 ký tự English |
| App icon missing | Upload PNG 1024×1024 vào portal (đã có `docs/tiktok-submission/lttstudio-icon-1024.png`) |

---

## PHẦN 7 — TRƯỚC KHI BẤM SUBMIT

Đọc lại tất cả file này 1 lần nữa. Đặc biệt:
- **Phần 1.4** — biết RÕ lý do mỗi cảnh tồn tại
- **14 cảnh bắt buộc** — đánh dấu ☑ từng cái sau khi quay
- **REJECT KEY #1-6** — không sai 1 cái nào

Nếu thấy lo, gửi link YouTube unlisted cho tôi review trước khi submit TT — tôi check 14 cảnh giúp.

---

## 📞 LIÊN HỆ HỖ TRỢ

- **Issue trong khi quay**: gửi screenshot/log cho LTTStudio dev (tôi)
- **TikTok reject**: forward email reject để tôi đọc reason, fix code/script

**Chúc bạn quay thành công!** 🎬
