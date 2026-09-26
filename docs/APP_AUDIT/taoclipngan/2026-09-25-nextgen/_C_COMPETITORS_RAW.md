# _C — COMPETITORS RAW (Tạo Clip Ngắn) — khảo sát thị trường 2025–2026

> Phương pháp: chỉ web research (web_search + web_fetch), không chạy app, không gọi API trả phí.
> Ngày lấy dữ liệu: 25/09/2026. Mọi claim có URL nguồn. Bậc độ tin cậy:
> **[P]** = trang chính thức (help/pricing/features của vendor) · **[R]** = review/bên thứ ba.
> Benchmark chính: **OpusClip**. 8 đối thủ còn lại: Klap, Vizard, Munch (getmunch), Gling,
> Submagic, Wavel (auto-reframe), Clipchamp (Microsoft), CapCut auto-clip.

## 0. TL;DR — bức tranh nhanh

| # | Công cụ | Trọng tâm | Điểm mạnh nhất | Điểm yếu chết | API | MCP |
|---|---------|-----------|----------------|---------------|-----|-----|
| 1 | **OpusClip** (bench) | long→short + publish | ClipAnything prompt, API + MCP, scheduler | Credits, Vietnamese BETA, mất dữ liệu khi cancel | ✅ | ✅ |
| 2 | Klap | long→short | Virality 0-100, brand kit team | Hỗ trợ kém, mobile yếu | ✅ | ❌ |
| 3 | Vizard | long→short | Score 0-100, 130+ lang sub, API + Skill | Chọn quá nhiều clip tốt, format 4:3 khó | ✅ | ❌ (có Skill zip) |
| 4 | Munch | trend-driven | Trend data Google/Meta/TikTok + keyword volume | Giá cao theo phút, không API công khai | ❌ | ❌ |
| 5 | Gling | YouTube edit | Xoá bad take/silence, desktop | Jitter MP4, YouTube-only tư duy | ❌ | ❌ |
| 6 | Submagic | captions | 123+ ngôn ngữ, auto-zoom, API + MCP | Không phải clipping-tool lõi | ✅ | ✅ |
| 7 | Wavel (Reframe) | reframe/dub | Auto-reframe 1-click + dubbing 100+ lang | Không phải clip-first | ? | ❌ |
| 8 | Clipchamp | editor phổ thông | Miễn phí, trong M365, reframe cơ bản | Không có scoring/prompt/scheduler | ❌ | ❌ |
| 9 | CapCut auto-clip | editor phổ thông | Miễn phí, auto-cut + captions | Caption drift, không virality score, paywall Pro | ❌ | ❌ |

**Nhận định:** không công cụ nào trong 9 cái giải quyết (a) tiếng Việt đầy đủ,
(b) vòng lặp dữ liệu publish→analytics→tốt hơn lần sau, (c) giá minh bạch không
dựa credit, (d) kênh VN (Facebook là kênh số 1 VN) làm first-class. Đây là không
gian cho Taoclipngan.

---

## 1. BẢNG SO SÁNH 16 CHIỀU × 9 CÔNG CỤ

Chú thích: ✅ = có · ⚠️ = có nhưng hạn chế · ❌ = không có · `?` = không xác nhận được.

| Chiều | OpusClip | Klap | Vizard | Munch | Gling | Submagic | Wavel | Clipchamp | CapCut |
|-------|----------|------|--------|-------|-------|----------|-------|-----------|--------|
| 1. Long→short cơ bản | ✅ tới 10h, 1–50 clip, 4 tỉ lệ | ✅ link/URL + upload, 9:16/1:1/16:9 | ✅ 1 video → 30+ clip, 4 tỉ lệ | ✅ upload/URL | ✅ upload, desktop | ✅ từ YouTube URL (Magic Clips) | ✅ video→shorts | ⚠️ thủ công + auto reframe | ✅ Auto Cut AI + manual |
| 2. Prompt-directed clip | ✅ **ClipAnything** (multimodal: visual/audio/sentiment) + ClipBasic (keywords) | ⚠️ keywords/context, không prompt tự do công khai | ⚠️ keyword focus | ✅ prompt + chọn trend | ❌ (dựa transcript edit) | ⚠️ hook title templates | ⚠️ ? | ❌ | ⚠️ AI chọn highlight, không prompt |
| 3. Virality score | ✅ 0–99, 4 chiều Hook/Flow/Value/Trend (chỉ Starter/Pro) | ✅ 0–100 (hook/emotion/punchline) | ✅ 0–100 (câu hoàn chỉnh, pacing, audio energy, hook) | ✅ "trending score" theo trend data ngoài | ❌ | ❌ | ❌ | ❌ | ❌ |
| 4. Editorial thủ công | ✅ text-based edit, reprompt | ✅ text edit theo transcript | ✅ text-based (xoa chữ = cắt video) | ⚠️ edit nhẹ | ✅ mạnh: bad take, silences, text trimmer | ✅ transcript edit trước render | ⚠️ tweaks tay | ✅ editor đầy đủ | ✅ editor đầy đủ |
| 5. Reframe/crop | ✅ **ReframeAnything™** auto-track speaker + đối tượng, 9:16/1:1/16:9, layout split/PIP | ✅ auto-reframe theo speaker | ✅ multi-platform crop + safe zone | ✅ auto crop theo platform | ✅ auto framing zoom in/out (không tracking đa chủ thể mạnh) | ⚠️ auto-zoom | ✅ **auto-reframe 1-click** (trọng tâm sản phẩm) | ✅ "Reframe" auto (phát hiện "vital info") | ⚠️ keyframes/resize, AI assist |
| 6. Captions + **Tiếng Việt** | ⚠️ 25+ ngôn ngữ, **Vietnamese = BETA**, emoji/keyword highlight | ⚠️ đa ngôn ngữ, chi tiết tiếng Việt không rõ | ✅ ASR 97%+, 30+ lang, dịch tới 130+ lang | ⚠️ đa ngôn ngữ | ✅ captions + SRT | ✅ **123+ ngôn ngữ (có tiếng Việt)**, auto-zoom | ⚠️ stylized subtitles | ✅ AI subtitles | ✅ auto captions + templates |
| 7. Audio cleanup | ✅ speech cleanup: filler words, pauses, bad take | ❌ (không phải trọng tâm) | ⚠️ ? | ⚠️ ? | ✅ mạnh nhất nhóm: silences + filler + noise reduction + bad takes | ⚠️ ? | ⚠️ studio-quality voiceovers | ✅ noise suppression | ✅ enhance voice/reduce noise |
| 8. B-roll | ✅ AI image gen + Pexels stock, drag/trim | ⚠️ ? | ⚠️ ? | ❌ | ✅ AI B-rolls | ✅ B-roll | ✅ | ✅ stock (premium) | ✅ |
| 9. Brand system | ✅ brand template: màu/font/logo/auto-headline (hạn chế theo plan) | ✅ brand kit + **team workspace** | ✅ brand kit team workspace | ✅ brand fonts/colors | ⚠️ nhẹ | ✅ presets + templates API | ⚠️ ? | ⚠️ themes | ⚠️ caption templates |
| 10. Platform profiles | ✅ 4 tỉ lệ + safe zones | ✅ 3+ tỉ lệ theo platform | ✅ tối ưu theo YT/TikTok/IG/FB/X/LinkedIn | ✅ per-platform | ⚠️ (tự export) | ✅ theo platform | ✅ theo platform (Reels/TikTok/Shorts) | ✅ aspect presets | ✅ theo platform |
| 11. Scheduling/publish | ✅ Calendar: 1 tháng, 6 nền tảng (YT/TikTok/IG/FB/X/LinkedIn) + API | ✅ scheduling có | ✅ scheduling 6 nền tảng | ✅ scheduling (trọng tâm) | ❌ (XML ra Premiere/Resolve/Final Cut) | ✅ publish endpoint + scheduler | ⚠️ ? | ❌ | ❌ (upload tay) |
| 12. Analytics feedback | ❌ **không có vòng lặp performance data vào model** | ❌ | ❌ | ✅ **marketing analytics theo trend** (dữ liệu ngoài, không phải performance clip của mình) | ❌ | ⚠️ publishing-stats + profile-stats API | ❌ | ❌ | ⚠️ YouTube/TikTok native analytics (bên ngoài) |
| 13. API / MCP | ✅ REST API (30 req/min, 900 credits/th) + **MCP server** | ✅ REST (max_clip_count v.v.) | ✅ REST + OpenAPI + **Skill zip cho Claude Code/Cursor** | ❌ không API công khai | ❌ | ✅ REST + **MCP server (19 tools)** | ? | ❌ | ❌ |
| 14. Kiến trúc công khai | ✅ blog kỹ thuật (transcription API, ASR 92-97%, word-level timestamps, speaker diarization tích hợp) | ⚠️ docs API | ⚠️ docs OpenAPI | ⚠️ mô tả GPT+OCR+NLP (rất mờ) | ❌ | ✅ docs đầy đủ + llms.txt | ❌ | ❌ | ❌ |
| 15. Phàn nàn cộng đồng | Mất project/credits khi cancel; refund khó; AI bỏ lỡ khoảnh khắc | Support không đáp lời nhiều ngày; bị billed sai | Nhiều clip tốt gây "chờ chọn"; đổi format 4:3 khó tìm | Giá cao/đắt theo phút (lẫn với thương hiệu khác tên) | Jitter/frame-rate lỗi MP4; free tier quá hạn chế | (ít phàn nàn; API mới) | Credits tiêu nhanh khi test | — | Caption drift, Pro paywall, support kém |
| 16. Giá | Free / credits-based (Starter–Pro, xem §3) | $14–$94/th theo số clip | $29/th Creator, $39/th Business, free 60 credits | $49/th (200 phút) → $220–318/th (1000 phút) | $0/1h → $20/10h → $40/30h → $100/100h | $19/th Starter + Magic Clips add-on $19 | ? (bundle services) | Free (1080p) + Premium ~$8-11/th (M365) | Free + Pro paywall |

---

## 2. OPUSCLIP — DEEP DIVE (benchmark)

### 2.1 Long→short & ClipAnything
- ClipAnything: "first-ever multimodal AI clipping" — phân tích **mỗi khung hình**
  qua visual/audio/sentiment cues (objects, scenes, actions, sounds, emotions,
  texts), mỗi scene được đánh điểm theo "virality potential", clip theo prompt
  tuỳ biến; hoạt động cả với video ít/không thoại. [P]
  Nguồn: https://help.opus.pro/docs/article/9947095-clip-anything
- Reframe Anything (Alpha): nhận diện key objects/actions, track xuyên khung hình,
  reframe 9:16 / 1:1 / 16:9. (nguồn cùng trang trên)
- ClipBasic: mode theo keywords (so với ClipAnything: prompt tự do, reprompt được).
  [P] Nguồn: https://help.opus.pro/docs/article/select-keywords

### 2.2 Virality Score (0–99)
- Chỉ có ở **Starter và Pro** — Free KHÔNG thấy score. [P]
- 4 chiều: **Hook** (mở đầu có giữ attention và liên quan chủ đề), **Flow** (logic,
  kết trọn), **Value** (giá trị, cảm xúc, kết nối cá nhân), **Trend** (khớp trend
  & quan tâm hiện tại); thêm check **độ liên quan đến prompt** khi dùng ClipAnything.
- Mặc định sắp xếp clip theo score giảm dần.
  Nguồn: https://help.opus.pro/docs/article/virality-score

### 2.3 Reframe / subject tracking
- ReframeAnything™: "smartly tracks moving speakers and objects", tự chuyển layout
  theo video và platform; hoạt động podcast, demo, sports, live stream. [P]
  Nguồn: https://www.opus.pro/ai-reframe
- Subject tracking: auto theo voice + motion; multi-subject tracking thủ công.
  [P] Nguồn: https://help.opus.pro/docs/article/subject-tracking
- Layouts: split-screen, picture-in-picture, apply theo clip.
  [P] Nguồn: https://help.opus.pro/docs/article/apply-the-layouts

### 2.4 Captions & tiếng Việt
- 25+ ngôn ngữ, **tiếng Việt ở trạng thái BETA** theo docs. Emoji, keyword
  highlight, kéo-thả vị trí. [P]
  Nguồn: https://help.opus.pro/docs/article/captions (và mục languages của docs)
- ⚠️ Ý nghĩa: đối thủ Submagic (123+ lang, có tiếng Việt ổn định) thắng ở đây.

### 2.5 Audio cleanup
- Speech cleanup: tự xoá filler words ("um/uh"), pauses, bad takes. [P]
  Nguồn: https://help.opus.pro/docs/article/speech-cleanup

### 2.6 B-roll
- AI B-Roll: sinh ảnh AI + stock Pexels, "1 click, dưới 1 phút", kéo/thu gọn được.
  [P] Nguồn: https://help.opus.pro/docs/article/ai-broll

### 2.7 Brand system
- Brand template: màu, font, logo, auto-headline, layout preset; số template bị
  giới hạn theo plan (thấp). [P]
  Nguồn: https://help.opus.pro/docs/article/brand-templates

### 2.8 Scheduler / publish
- UI: Calendar tab — lên lịch 1 tháng posts tới 6 nền tảng: YouTube, TikTok,
  Instagram, Facebook, LinkedIn, X. [P]
  Nguồn: https://www.opus.pro/calendar
- API: `GET /api/social-accounts`, `POST /api/social-copy-jobs` (sinh copy có tone
  guidance), `POST /api/post-tasks` (instant), `POST /api/publish-schedules`
  (future UTC), `DELETE /api/publish-schedules/{id}`. Rate: social-accounts 10 req/s;
  copy-jobs 1 req/s; post-tasks 1 req/s. **Đăng X tốn 1 credit/post.** [P]
  Nguồn: https://help.opus.pro/api-reference/endpoints/social-posting/overview
- ⚠️ Lưu ý cạnh tranh: Vizard quảng cáo "Opus không schedule được Twitter/Facebook"
  (trang alternatives của Vizard) — trong khi docs Opus cho thấy 6 nền tảng
  kể cả X và Facebook. Đây là claim marketing 2 chiều, cần kiểm trong app thật.
  [R] Nguồn: https://vizard.ai/alternatives/opus

### 2.9 API & MCP (điểm mạnh nhất thị trường)
- REST API public: projects, clips, brand, social-posting, webhooks.
  Limit: **30 req/min, trần 900 credits/tháng** cho API. [P]
  Nguồn: https://help.opus.pro/api-reference/limitation
- Blog kỹ thuật (hiếm trong ngành): transcription API tích hợp
  word-level timestamps + speaker diarization + punctuation; công bố con số
  **92–97% word-level accuracy** trên audio Anh rõ; formats JSON/SRT/VTT/text;
  vocabulary hints cho proper nouns. [P]
  Nguồn: https://www.opus.pro/blog/video-transcription-api
- **MCP server** (`opus.pro/mcp`): cho AI agent (Claude/Cursor) gọi
  clip/caption/reframe/edit/schedule_post. [P]
  Nguồn: https://www.opus.pro/mcp
- OpusSearch: search/catalog library — auto-cataloging, trend agent, search agent,
  monetization toolkit (đang waitlist). [P]
  Nguồn: https://www.opus.pro/opussearch (nav của site, xem blog trên)

### 2.10 Pricing & credits
- Credit-based; tiers Free/Starter/Pro/Business (Starter và Pro mới thấy
  Virality Score). [P]
  Nguồn: https://help.opus.pro/docs/article/plans-and-credits
- Refund project: chỉ **Pro**, chỉ khi **chưa download clip nào**, bấm "Refund
  this project" + ghi feedback. Xoá project = mất credits đã dùng, không hoàn.
  [P] Nguồn: https://help.opus.pro/docs/article/can-i-reprocess-a-project

### 2.11 Phàn nàn cộng đồng (dữ liệu thô)
- Credits mất/khó hoàn; bị charge project không định mua; xoá project không hoàn
  credits. [R] Nguồn: https://www.joinchargeback.com/refunds/how-to-get-an-opusclip-refund
- "AI bỏ lỡ khoảnh khắc quan trọng", cần chỉnh tay nhiều (tổng hợp review).
  [R] Nguồn: https://www.eesel.ai/blog/opusclip-reviews (fetch bị cắt nội dung —
  chỉ còn từ search snippet)
- Sau khi cancel subscription, project cũ khó truy cập (khuôn phàn nàn lặp lại
  trên các blog so sánh, vd nextclip.pro).
  [R] Nguồn: https://www.nextclip.pro/blog/opusclip-review (fetch bị chặn egress —
  chỉ còn search snippet, cần xác minh thêm)

---

## 3. TỪNG ĐỐI THỦ — DỮ LIỆU NGUYÊN

### 3.1 Klap (klap.app)
- Virality score **0–100**, 3 chiều công bố: **hook strength, emotional impact,
  punchline**; mô phỏng pipeline: transcript→LLM phân tích context/tone/flow→
  chọn khoảnh khắc, phân biệt filler với "mic-drop statement". [R]
  Nguồn: https://quso.ai/blog/klap-ai-review-pros-cons-alternatives ·
  https://klap.app/blog/auto-clip-maker-ai · https://klap.app/blog/highlight-clip-generator
- Brand kit cho **team** (khác biệt so với OpusClip 1 template/user hạn chế).
  [R] Nguồn: https://quso.ai/blog/klap-ai-review-pros-cons-alternatives
- API: endpoints generate-shorts có tham số `max_clip_count` v.v. [P]
  Nguồn: https://docs.klap.app/usecases/generate-shorts
- Pricing: **$14–$94/tháng** theo số clip/plan. [P]
  Nguồn: https://klap.app/pricing
- Phàn nàn: support không đáp chat/email nhiều ngày; không có app mobile;
  1 review Trustpilot: "billed an outrageous amount… service I did not knowingly
  agree to at that price". [R]
  Nguồn: https://quso.ai/blog/klap-ai-review-pros-cons-alternatives ·
  https://www.trustpilot.com/review/klap.app

### 3.2 Vizard (vizard.ai)
- Core: 1 video → **30+ clips** 1 click; phân tích speech patterns, visual cues,
  sentiment. [R] Nguồn: https://contentcreators.com/tools/vizard-review
- Virality score **0–100** = "weighted stack of signals": câu hoàn chỉnh, pacing,
  audio energy, hook strength đầu clip, mức độ self-contained. [R]
  Nguồn: https://plisio.net/ai/vizard-ai
- Captions: ASR **>97%** accuracy, 30+ ngôn ngữ, **dịch captions tới 130+ (một
  nguồn khác nói 150+) ngôn ngữ**. [R]
  Nguồn: https://contentcreators.com/tools/vizard-review
- API: REST + OpenAPI + llms.txt; **"Skill zip" cho Claude Code/Cursor** (dán API
  key, ra lệnh "Find the viral moments… and prep them for TikTok"). [P]
  Nguồn: https://vizard.ai/api · https://docs.vizard.ai/docs/introduction
- Scheduling: 6 nền tảng (YT/TikTok/IG/FB/X/LinkedIn). [R]
  Nguồn: https://vizard.ai/alternatives/opus
- Pricing: Free 60 credits · **Creator $29/th ($14.50 năm)** · **Business $39/th
  ($19.50 năm)**; có "cancellation catch". [R]
  Nguồn: https://www.usefastlane.ai/pricing/vizard
- Phàn nàn: "phải chọn giữa rất nhiều clip tốt" (quá nhiều output); format 4:3
  khó tìm trong menu. [R]
  Nguồn: https://www.capterra.com/p/10009818/Vizard/reviews/ ·
  https://www.g2.com/products/vizard-corp/vizard/reviews?qs=pros-and-cons

### 3.3 Munch / getmunch
- **Điểm khác biệt duy nhất trong nhóm: trend data bên ngoài.** Phân tích video
  đối chiếu "social and marketing trends từ Google, Meta, TikTok"; mỗi clip được
  "trending score"; xác định keyword theo **search volume + competition**, xem
  được performance theo khoảng thời gian. [R]
  Nguồn: https://contentcreators.com/tools/getmunch ·
  https://squeezegrowth.com/getmunch-review/
- Mô tả kỹ thuật: dùng GPT + OCR + NLP; contextual clip extraction; platform-
  optimised cropping. [R] Nguồn: https://www.videosdk.live/ai-apps/getmunch
- ⚠️ **Không có API/MCP công khai** — repo GitHub "munch-app/munch-core" đã
  **archive**, không phải API sản phẩm. [P]
  Nguồn: https://github.com/munch-app/munch-core
- Pricing: **Pro $49/th (200 phút upload)** · **Ultimate ~$220–318/th
  (1000 phút)**; model tính theo phút upload (đắt cho người dùng nhiều). [R]
  Nguồn: https://sonary.com/b/getmunch/getmunch+creative-tools/ ·
  https://thepixel.ai/future-of-content-creation-get-munch-ai/
- Phàn nàn: giá cao so với giá trị nhận (mức "not the cheapest platform");
  một số review Trustpilot về billing tự động (cẩn thận: Trustpilot
  munchaddict.com là thương hiệu khác tên, không phải getmunch). [R]
  Nguồn: https://thepixel.ai/future-of-content-creation-get-munch-ai/

### 3.4 Gling (gling.ai)
- Trọng tâm **desktop editor cho YouTube**: xoá bad takes 1 click, silences,
  filler words ("um/uh"), text-based trimmer, AI captions (+SRT), auto framing
  (zoom in/out), multicam, **AI B-rolls**, noise/speech enhancement, XML export
  cho Premiere/Final Cut/Resolve, YouTube title/chapters generator,
  "Next Video suggestions". [P]
  Nguồn: https://www.gling.ai/ai-viral-video-clipping · https://www.gling.ai/pricing
- Pricing (theo giờ AI-edited media/tháng): **Free $0 (1h, watermark)** ·
  **Plus $20 (10h hoặc 300 từ)** · **Pro $40 (30h hoặc 900 từ, premium support)** ·
  **Elite $100 (100h hoặc 2700 từ)**; -50% năm. [P]
  Nguồn: https://www.gling.ai/ai-viral-video-clipping (khối pricing trong trang)
- Phàn nàn: **jitter / frame-rate không nhất quán trên MP4 export** (phàn nàn
  lặp lại trên Reddit theo tổng hợp); free tier quá hạn chế; silences-cut gây
  false positive với phong cách nói có khoảng lặng cố ý. [R]
  Nguồn: https://max-productive.ai/ai-tools/gling/ ·
  https://www.trustpilot.com/review/gling.ai (3.2, 1 review — mẫu nhỏ)
- Không có API/MCP công khai; không scheduling social (ra XML/MP4 rồi tự đăng).

### 3.5 Submagic (submagic.co)
- Lõi là **captions/editor short-form**, không phải clipping-tool: AI captions
  123+ ngôn ngữ (**có tiếng Việt đầy đủ**), auto-zoom, b-roll, auto description,
  Magic Clips (từ YouTube URL), AI actors, eye-contact, translator. [P]
  Nguồn: https://www.submagic.co/pricing (nav features) · https://www.submagic.co/languages-supported
- **API + MCP mạnh**: REST (user-media, projects, magic-clips, presets, export,
  **publish-project, publishing-stats, profile-stats**, webhooks) và **MCP server**
  `POST https://api.submagic.co/mcp` — **19 tools** cho Claude Code/Desktop/Cursor.
  [P] Nguồn: https://docs.submagic.co/introduction · https://docs.submagic.co/mcp-server ·
  https://www.mcpbundles.com/skills/submagic
- Pricing: **Starter $19/th (15 video phút)** + **Magic Clips add-on $19/th**;
  có credit pack cho API minutes. [P]
  Nguồn: https://care.submagic.co/en/article/how-much-does-it-cost-to-use-submagic-1xm83pa/ ·
  https://www.submagic.co/pricing
- ⚠️ Publishing-stats API là một trong rất ít endpoints "post-publish analytics"
  có trong nhóm — nhưng là stats của Submagic, không phải vòng lặp hiệu suất
  platform gốc.

### 3.6 Wavel — "Reframe" (wavel.ai)
- Auto-reframe **1-click**: chuyển long video → vertical (Reels/TikTok/Shorts),
  preview + chỉnh tay tuỳ chọn rồi export; "unlike basic crop tools" (theo họ).
  [P] Nguồn: https://wavel.ai/solutions/ai-video-editor/ai-auto-reframe
- Video-to-shorts stack: voiceover studio-quality + stylized subtitles; dubbing
  100+ ngôn ngữ. [P] Nguồn: https://wavel.ai/solutions/video-to-shorts/video-clipping
- Pricing: gói bundle 4 services; G2 có phàn nàn **credits tiêu nhanh khi test**
  voice/video/avatar. [R]
  Nguồn: https://wavel.ai/pricing · https://www.g2.com/products/dolce-lte-ltd-wavel-ai/pricing
- Không thấy virality score, không thấy API/MCP công khai, không scheduling
  first-party trong các trang đã fetch.

### 3.7 Clipchamp (Microsoft)
- Reframe: nút "Reframe" — hỏi kích thước sequence mới (vd 9:16), tự "analyze &
  shift what it sees as vital info" vào khung mới, phải fine-tune tay. (cộng đồng
  mô tả hành vi thật). [R]
  Nguồn: https://www.reddit.com/r/premiere/comments/1ecna6g/
- Aspect ratios cố định: 16:9, 9:16, 1:1, 4:5, 2:3, 21:9 — **không custom**. [R]
  Nguồn: https://superuser.com/questions/1847990/
- AI tools: subtitles, voiceover, **noise suppression**, silence removal (free);
  7 AI editing tools trong blog chính thức. [P]
  Nguồn: https://clipchamp.com/en/blog/ai-video-editing-tools/
- Pricing: **Free export 1080p không watermark**; Premium ~$8.33/th (năm) /
  standalone; premium đi kèm Microsoft 365 Personal/Family. [P/R]
  Nguồn: https://clipchamp.com/en/pricing/ · https://checkthat.ai/brands/clipchamp/pricing
- Không có virality score, prompt-clipping, scheduler social, API/MCP.

### 3.8 CapCut — auto-clip (long→short)
- Hai cách: **AI auto-identifies highlight moments** (Auto Cut) hoặc manual
  split-and-trim với full control; chọn caption template. [R]
  Nguồn: https://store.hollyland.com/blogs/creator-hub/convert-long-videos-to-shorts-in-capcut
- Auto captions miễn phí kể cả khi export thủ công 4K. [R]
  Nguồn: https://lilys.ai/en/notes/create-youtube-shorts-20260115/capcut-convert-long-videos-short-form
- Ecosystem: CapCut Desktop/Online/Pad/Mobile, Dreamina, Pippit, Hypic,
  CapCut × Codex plugin. [P]
  Nguồn: https://www.capcut.com/tools/ai-long-video-to-short-video (nav)
- ⚠️ Không thấy: virality score, prompt-directed clip, trend data, scheduling,
  API/MCP cho clipping.
- Phàn nàn: **auto captions drift**, templates "looks copied", export lỗi sau
  upload; Pro paywall, commercial licensing checks, support kém; kiểm soát
  long-form yếu. [R]
  Nguồn: https://aiflowreview.com/capcut-ai-review/ ·
  https://diyai.io/ai-tools/video-generation/reviews/capcut-review/

---

## 4. ĐIỂM CƠ HỘI CHO TẠO CLIP NGẮN (≥10)

Xếp theo giá trị cho thị trường VN + độ khó. "Bằng chứng" = nguồn đã fetch.

1. **Tiếng Việt full (không BETA) + virality score huấn luyện trên nội dung VN.**
   OpusClip tiếng Việt = BETA (help.opus.pro/docs captions); không công cụ nào
   khác công bố tiếng Việt ngoài Submagic (captions, không clip). Model
   "Trend" của Opus/Klap/Munch dựa trend phương Tây — vô nghĩa với hashtag/audio
   trending VN. Đây là khác biệt duy nhất không thể copy bằng feature list.
2. **Vòng lặp publish → analytics → retrain/rank.** Trong 9 công cụ, không ai
   lấy performance thật (watch time, retention) của clip đã đăng để sửa model
   xếp hạng clip lần sau. Chỉ Submagic có publishing-stats API (stats của họ).
   Taoclipngan đã có FEEDBACK node (manifest) — phần còn thiếu là nối về
   ranker. (Bằng chứng: docs.submagic.co publishing-stats; _A_CURRENT_TRUTH_RAW
   node FEEDBACK = PARTIAL.)
3. **Facebook first-class (kênh số 1 VN).** Scheduler của OpusClip/Vizard có FB
   nhưng là business page Tây; Vizard còn claim sai rằng Opus không hỗ trợ FB/X
   (vizard.ai/alternatives/opus) cho thấy cả ngành lơ là kênh này. Group + Page +
   tối ưu thumbnail VN là ngách trống.
4. **Giá minh bạch không credit.** OpusClip (credits, trần 900 API credits/th,
   1 credit/post X), Vizard (credits, cancellation catch), Wavel (credits tiêu
   nhanh) — phàn nàn "credits mất/khó hiểu" lặp lại (joinchargeback, Trustpilot
   klap). Mô hình theo phút upload (Munch $49/200 phút) cũng bị chê đắt.
   Taoclipngan đang tính credit = phút×tier + clip×5 (cost.py) — cần gói theo
   "bao nhiêu clip nhận được" để dễ so sánh.
5. **MCP + API là bề mặt chính, không phải phụ.** OpusClip và Submagic đều đã
   có MCP; Vizard có Skill zip. Nếu Taoclipngan (chạy GPU nội bộ, chi phí biên
   thấp hơn SaaS thuê ngoài) mở API+MCP công khai cho VN + Đông Nam Á, chi phí
   /clip có thể thấp hơn đáng kể — mà không đối thủ nào khác làm ở tầng này.
6. **Bảo đảm dữ liệu sau cancel.** Điểm chết của OpusClip: project khó truy cập
   sau cancel, xoá project mất credits không hoàn (help.opus.pro refund docs +
   joinchargeback). Cam kết "dữ liệu clip của bạn thuộc về bạn, export 1-click
   trọn library sau khi hết gói" là lời chào giải quyết pain thật đã được chứng
   thực.
7. **Desktop pro-export (XML/EDL) như Gling nhưng trên nền clip-first.** Gling
   thắng ở XML→Premiere/Resolve/Final Cut (gling.ai/ai-viral-video-clipping) —
   OpusClip cũng có "Export to XML" (nav opus.pro) nhưng Klap/Vizard/Munch/Submagic
   không. Đội VN làm phim/quảng cáo cần đường ra NLE.
8. **Trend data nhưng có "loopback" (học từ Munch, sửa weakness của Munch).**
   Munch là người duy nhất nối trend data Google/Meta/TikTok (contentcreators.com
   /tools/getmunch) nhưng score đó không học từ hiệu suất clip của chính khách
   hàng. Kết hợp trend VN (hashtag TikTok VN, xu hướng Facebook) + retention
   thật = "trending score mà hiệu chỉnh theo kênh của bạn".
9. **Brand kit team (học từ Klap) mà không bị giới hạn theo plan như OpusClip.**
   Klap có brand kit + team workspace; OpusClip giới hạn số template theo plan.
   Agency VN chạy nhiều kênh cho nhiều khách — brand kit unlimited + nhiều
   workspace là yêu cầu agency đã được thị trường xác nhận (opus.pro/business
   agencies claim "save $2,700/month").
10. **Output kỷ luật: ít clip hơn, đúng clip (học từ phàn nàn Vizard).**
    Vizard bị phàn nàn "phải chọn giữa rất nhiều clip tốt" (Capterra) — over-
    generation làm mất thời gian. Cam kết "3–5 clip được chọn, mỗi clip có lý do
    (hook nào, trend nào, score theo chiều gì)" là khác biệt UX rõ.
11. **Audio cleanup chuẩn podcast VN (học từ Gling).** Gling mạnh nhất ở silences/
    filler/bad-take (gling.ai) nhưng là desktop YouTube-only. Podcast/lecture VN
    nói nhanh, nhiều "ờ/ừm" — cleanup tuned cho tiếng Việt là ngách trong ngách.
12. **Không phàn nàn "AI bỏ lỡ khoảnh khắc" (phàn nàn lớn nhất của OpusClip theo
    eesel.ai tổng hợp) bằng cách cho người dùng reprompt + "giữ khoảnh khắc này"
    1-click.** OpusClip có reprompt (ClipAnything) nhưng cộng đồng vẫn than;
    pattern thành công: pin khoảnh khắc thủ công → hệ thống học vị trí pin để
    lần sau clip tự động đúng hơn (nối với cơ hội #2).

## 5. ĐÚNG SAI CẦN XÁC MINH THÊM (đừng dùng như sự thật)
- nextclip.pro / eesel.ai bị chặn fetch (egress) — chỉ còn search snippet; cần
  1 nguồn thứ ba khác cho cluster phàn nàn OpusClip.
- Claim Vizard "Opus không schedule được Twitter/Facebook" mâu thuẫn docs chính
  thức Opus — đã ghi ở §2.8.
- Munch API: chưa tìm được API công khai; repo GitHub đã archive. Có thể có
  enterprise API không public — cần tra getmunch.com/api trực tiếp (bị chặn
  egress trong phiên này).
- Wavel: không fetch được chi tiết pricing + không xác nhận scheduling/API —
  đánh dấu `?` trong bảng.
- Giá OpusClip chính xác theo tier (số $) chưa fetch trong phiên này — chỉ có
  cấu trúc credits (plans-and-credits). Cần fetch plans-and-credits.md bổ sung
  nếu báo cáo cuối cần con số $.

## 6. DANH MỤC NGUỒN CHÍNH (đã fetch thành công, 25/09/2026)
OpusClip: help.opus.pro/docs/article/{virality-score, 9947095-clip-anything,
select-keywords, subject-tracking, speech-cleanup, ai-broll, apply-the-layouts,
can-i-reprocess-a-project}.md · opus.pro/{mcp, ai-reframe, calendar,
blog/video-transcription-api, opussearch} · help.opus.pro/api-reference/{
limitation, endpoints/social-posting/overview}.md
Klap: klap.app/{pricing, blog/auto-clip-maker-ai, blog/highlight-clip-generator,
blog/short-clip-generator} · docs.klap.app/usecases/generate-shorts ·
quso.ai/blog/klap-ai-review-pros-cons-alternatives · trustpilot.com/review/klap.app
Vizard: vizard.ai/{api, alternatives/opus} · docs.vizard.ai/docs/introduction ·
contentcreators.com/tools/vizard-review · plisio.net/ai/vizard-ai ·
usefastlane.ai/pricing/vizard · capterra.com/p/10009818/Vizard/reviews/
Munch: contentcreators.com/tools/getmunch · squeezegrowth.com/getmunch-review/ ·
videosdk.live/ai-apps/getmunch · sonary.com/b/getmunch/getmunch+creative-tools/ ·
thepixel.ai/future-of-content-creation-get-munch-ai/ · github.com/munch-app/munch-core
Gling: gling.ai/{ai-viral-video-clipping, pricing} · max-productive.ai/ai-tools/gling/ ·
trustpilot.com/review/gling.ai
Submagic: submagic.co/{pricing, api, languages-supported} · docs.submagic.co/
{introduction, mcp-server, rate-limits} · care.submagic.co (pricing article) ·
mcpbundles.com/skills/submagic
Wavel: wavel.ai/{pricing, solutions/ai-video-editor/ai-auto-reframe,
solutions/video-to-shorts/video-clipping} · g2.com/products/dolce-lte-ltd-wavel-ai/pricing
Clipchamp: clipchamp.com/{en/pricing/, en/blog/ai-video-editing-tools/} ·
support.microsoft.com/en-us/clipchamp/what-are-clipchamp-products-and-what-are-their-cost ·
reddit.com/r/premiere/comments/1ecna6g/ · superuser.com/questions/1847990/
checkthat.ai/brands/clipchamp/pricing
CapCut: capcut.com/tools/ai-long-video-to-short-video · capcut.com/help/how-to-use-auto-cut ·
store.hollyland.com/blogs/creator-hub/convert-long-videos-to-shorts-in-capcut
aiflowreview.com/capcut-ai-review/ · diyai.io/ai-tools/video-generation/reviews/capcut-review/
