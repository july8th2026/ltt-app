> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: `apps/upscalevideo/`, `apps/autosubvideo/` + `docs/KE_HOACH_TON_DONG.md` (việc hoãn). Chỉ đọc để hiểu lịch sử.

# Kế hoạch xây 2 app: UPSCALE VIDEO + AUTO SUB VIDEO

> Lập 2026-08-01. Theo quy trình mới: **người dùng chỉ định app←module**, Claude
> phân tích + lập kế hoạch (không tự quyết). Nguồn: kiểm kê 2 module BOT GEMINI
> (`video_upscale`, `auto_sub_video`) + công thức `CONG_THUC_DI_TRU_APP.md`.
> Tài liệu để **DUYỆT** — chưa build.

## 0. Kết luận nhanh (đọc trước)

| | UPSCALE VIDEO | AUTO SUB VIDEO |
|---|---|---|
| Module gốc | `video_upscale` | `auto_sub_video` |
| Nhóm `requires` | **C = gpu** | **B = ffmpeg** |
| Độ khó port | **Cao** (GPU + vendor binary + file cực lớn) | **Trung bình** (ffmpeg + font + file lớn) |
| Vendor binary | `realesrgan-ncnn-vulkan.exe` + 3 model (~49MB) — **copy thẳng, ta cũng chạy Windows** | không có |
| GPU | **BẮT BUỘC** (NVENC hardcode, không fallback CPU) | tuỳ chọn (có fallback `libx264`) |
| Transcribe? | — | **KHÔNG** — module chỉ *burn* phụ đề từ transcript người dùng nạp |
| Credit trong code gốc | không có → ta thêm | không có → ta thêm |

**Hai phát hiện đảo giả định cũ:**
1. **Ta vẫn chạy Windows** (cùng OS với BOT GEMINI) → `.exe` + model của Real-ESRGAN
   **copy nguyên**, KHÔNG phải build lại Linux. Rủi ro "port vendor binary" của
   agent biến mất. GPU thật = **RTX 5060 Ti 16GB** — đúng máy autotune đã benchmark.
2. **AUTO SUB không nghe-chép** (no Whisper). Hiện nó = "trình khắc phụ đề + editor
   WYSIWYG" ăn transcript `.srt/.json/.vtt/.ass` do người dùng nạp. Muốn "auto"
   đúng nghĩa (tự tạo phụ đề từ tiếng nói) phải thêm Whisper — **quyết định sản phẩm** (mục 6).

## 1. Điều kiện chung (SHARED PREREQ — cả 2 app cần)

Đây là phần "nút cổ chai" phải xong trước hoặc song song. Cả 2 app đều nhận video
lớn (gốc tới 2GB) và có thể xuất file lớn → vượt xa **trần 100MB / 100s của Cloudflare**.

| # | Việc | Vì sao | Effort | Trạng thái |
|---|---|---|---|---|
| P1 | **Upload thẳng browser→R2 (presigned PUT)** | `storage.py` mới có `url_for` (GET). Upload multipart qua server = chết ở 100MB Cloudflare. Cần `Storage.put_url()` presigned PUT + JS upload thẳng → worker kéo từ R2 | M | ❌ (H10 hoãn phần này) |
| P2 | **Serve output lớn thẳng từ R2** (đã có `url_for` GET) + với Local giữ Range | tránh 100MB response | S | ✅ phần R2 xong; chỉ nối vào 2 app |
| P3 | **Worker định tuyến GPU + chạy nền không chặn** (backlog 2.2 + 4.2) | worker hiện **1 tiến trình đơn luồng**; 1 job upscale (hàng chục phút GPU) sẽ CHẶN mọi job khác. `claim()` đã `SKIP LOCKED` → chạy nhiều worker AN TOÀN. Cần: (a) NSSM thêm worker; (b) manifest khai `requires=gpu`; (c) worker lọc job theo khả năng máy | M | ❌ |
| P4 | **Định vị ffmpeg/ffprobe/nvidia-smi** cấu hình được (env `LTT_FFMPEG` / PATH) | app phải tìm được binary; máy chủ đã có ffmpeg NVENC + libass | S | binary ✅, cần lớp cấu hình |
| P5 | **Đo thời lượng video khi upload (ffprobe)** để **giữ chỗ credit** trước khi chạy | cost = f(phút × độ phân giải) cần duration sớm | S | ❌ |

**P1 và P3 là 2 chặn thật.** P1 chặn *cả 2 app* (không có = chỉ nhận video ≤~90MB).
P3 chặn *chất lượng vận hành upscale* (không có = 1 job dài làm treo toàn hệ).

## 2. APP 1 — UPSCALE VIDEO (`apps/upscalevideo/`)

### 2.1 Bốn rổ di trú

🟢 **COPY NGUYÊN (L1 + L2 + vendor)** — tận dụng cao nhờ cùng Windows:
- `vendor/upscale/engine/` (exe + vcomp DLL + 3 model ~49MB) → `apps/upscalevideo/vendor/` (gitignore).
- Lõi pipeline: `runner.py` (probe→tách frame→autotune→NCNN→encode→dọn), `autotune.py`
  (đọc nvidia-smi, tile/thread theo VRAM), `adapters/engine_adapter.py` (subprocess
  NCNN + stall watchdog 300s), `adapters/ffmpeg_adapter.py` (tách frame CFR, encode
  NVENC `-preset p5 -cq 19`, chunk 360-frame + concat). Giữ thuật toán, đổi import
  storage/tạm.

🟡 **VIẾT LẠI THEO HỢP ĐỒNG (L4 + L5 + vỏ L3)**:
- `manifest.py`: `requires=["gpu","ffmpeg"]`, `credit_cost` (giữ chỗ), tên/mô tả.
- `routes.py`: `require_login` + CSRF; **/upload đổi sang presigned PUT (P1)**;
  `/estimate` (HTMX báo credit theo duration×preset×res); submit job (KHÔNG chạy dài
  trong request); `/v/{key}` serve từ R2 `url_for`.
- `jobs.py`: bọc `runner` vào `handle(ctx)` — `ctx.progress` mỗi mốc (extract 0-5,
  upscale 5-88, encode 88-100) để worker heartbeat; idempotent; raise phân loại lỗi;
  **quyết toán credit theo thời lượng/độ phân giải thực**.
- Template: `extends base.html`, HTMX; nhóm điều khiển: **Chất lượng** (⚡Fast /
  💎Quality), **Độ phân giải** (1080/1440/2160), **Codec** (H.264/H.265), **xem thử 8s đầu**.

🔴 **THAY BẰNG DỊCH VỤ NỀN TẢNG (L6)**:
- file cục bộ → `platform_core.storage` (R2); temp PNG vẫn ở `%TEMP%` (scratch local, không lên R2).
- quota/công bằng RAM → sổ credit + hàng đợi job Postgres.
- auth/user → sẵn có.

⚫ **BỎ (L7)**: **Watch Folder** (`data/upscale_watch/` quét local) — thuần desktop,
bỏ. Không có Selenium/cookie.

### 2.2 Credit (thêm mới — không có ở gốc)

Đề xuất công thức giữ-chỗ→quyết-toán (khớp tỉ giá Q31: 100k VND = 1000 credit):
```
credit = duration_phut × he_so_res × he_so_preset × don_gia_co_ban
he_so_res:    1080p=1.0   1440p=1.8   2160p(4K)=4.0
he_so_preset: Fast=1.0    Quality=2.5
```
`don_gia_co_ban` (credit/phút @1080p Fast) **cần bạn chốt** — gợi ý 20-40 credit/phút
(GPU nặng). Giữ chỗ theo duration ffprobe khi upload; quyết toán theo duration thực
(xem thử 8s → tính ~0.15 phút). Số cụ thể để bạn duyệt.

### 2.3 Đấu nối Seedance (theo yêu cầu của bạn)

Gốc có `POST /from-seedance/{id}`. Ta dựng **service dùng chung**
`apps/upscalevideo/service.py::upscale_from_key(storage_key, preset, res)` để **cả
route web lẫn taovideo gọi**. `apps/taovideo` sau khi tạo video xong → nút "Nâng cấp
4K" gọi thẳng service này (không nhân đôi code Real-ESRGAN). Đây là điểm khớp với ý
"upscale cho seedance lấy code từ app upscale".

## 3. APP 2 — AUTO SUB VIDEO (`apps/autosubvideo/`)

### 3.1 Bốn rổ di trú

🟢 **COPY NGUYÊN (L1 + L2)** — không vendor binary:
- L1 kho preset: `style_registry.py` (**8 preset**: tiktok_bold, reels_clean, cinematic,
  meme_punch, kids_color, punchline, word_emphasis, default) — copy nguyên.
- L2 lõi: `ass_builder.py` (dựng ASS + karaoke `\kf`/`\c`/`\fad`/`\u1`), `segmenter.py`
  (sentence/phrase/short_form/punchline/word_emphasis), `transcript_normalizer.py`,
  `validators.py`, `font_checker.py` (matplotlib→registry Windows→fc-list), parser
  SRT/VTT/ASS/JSON. Đổi import, giữ thuật toán.

🟡 **VIẾT LẠI THEO HỢP ĐỒNG (L4 + L5)**:
- `manifest.py`: `requires=["ffmpeg"]` (GPU tuỳ chọn), `credit_cost`.
- `routes.py`: `/upload` 2 file (video + transcript) — video qua **presigned PUT (P1)**,
  transcript nhỏ nạp thẳng; submit job; serve output qua `url_for`.
- `jobs.py`: bọc `runner._run_render` — validate transcript → sinh ASS/SRT → burn
  ffmpeg `-vf ass=` (retry 2) → finalize; `ctx.progress` map từ `-progress pipe:1`;
  quyết toán credit theo duration.
- Template: **đây là app UI nặng nhất** (gốc 1657 dòng HTML + 2142 JS, editor WYSIWYG
  player trực tiếp). MVP nên **cắt gọn**: chọn preset + tuỳ biến cơ bản (font/size/màu/
  vị trí/highlight) + xem-thử 8s; **để dành** editor WYSIWYG player nhúng cho fast-follow.

🔴 **THAY BẰNG DỊCH VỤ NỀN TẢNG (L6)**:
- SSE + `app.kernel.job_registry` + `broadcaster` in-proc → **hàng đợi job + poll HTMX**
  của nền tảng (giống taovideo/kichban). Đây là phần đấu nối lại chính.
- `data/auto_sub_templates/{user}/` (template style user lưu) → cân nhắc bảng DB hoặc
  storage; **MVP có thể bỏ** template chia sẻ, chỉ giữ 8 preset.
- output theo user → `platform_core.storage`.
- concurrency `asyncio.Semaphore(3)` in-proc → hàng đợi job (đa worker).

⚫ **BỎ (L7)**: không có ràng buộc desktop cứng (font_checker tự chuyển registry↔fc-list).

### 3.2 Font
Preset tham chiếu Montserrat/Impact/Anton/Oswald/Comic Sans MS… Máy chủ Windows có
sẵn phần lớn; thiếu → font_checker fallback Arial + cảnh báo (đã có sẵn). **Cần**:
đóng gói `.ttf` các font preset vào `apps/autosubvideo/assets/fonts/` để giống thiết
kế, và trỏ fontconfig/`fontsdir` cho ffmpeg libass.

### 3.3 Credit (thêm mới)
Nhẹ hơn upscale (chỉ re-encode, không ×4). Đề xuất:
```
credit = duration_phut × he_so_chatluong × don_gia_sub
he_so_chatluong: draft=0.6  standard=1.0  high=1.5
```
`don_gia_sub` gợi ý 3-8 credit/phút. Số để bạn duyệt.

## 4. Thứ tự đề xuất

**Khuyến nghị: AUTO SUB trước, UPSCALE sau** — lý do:
1. AUTO SUB **không chặn bởi GPU-route (P3)** — chạy được ngay trên worker hiện tại
   (ffmpeg CPU fallback), chỉ cần P1 (upload lớn). → ra mắt nhanh, ít rủi ro.
2. UPSCALE cần **cả P1 lẫn P3** (GPU worker không chặn) → nặng hạ tầng hơn.
3. Cả hai **chung P1** → làm P1 một lần, dùng cho cả hai.

```
Chặng 0 (hạ tầng chung):  P1 presigned PUT + P4 ffmpeg config + P5 ffprobe duration
Chặng A (AUTO SUB):       copy L1/L2 → jobs/routes/manifest → template MVP → credit → nghiệm thu parity + ảnh 2 UI
Chặng 0b (GPU):           P3 worker định tuyến GPU + NSSM multi-worker
Chặng B (UPSCALE):        copy vendor+L2 → jobs/routes → template → credit → đấu nối seedance → nghiệm thu
```

Nếu bạn muốn **UPSCALE trước** (giá trị cao hơn, đã có seedance cần nó): đảo lại,
nhưng phải làm P1 + P3 cùng lúc ở Chặng 0 → chặng đầu nặng hơn.

## 5. Rủi ro & cách chặn

| Rủi ro | App | Chặn |
|---|---|---|
| Upload >100MB chết ở Cloudflare | cả 2 | **P1 bắt buộc**; MVP tạm cap 90MB nếu hoãn P1 |
| 1 job upscale treo toàn worker | upscale | **P3** (multi-worker + SKIP LOCKED sẵn có) |
| NVENC không fallback → encode fail nếu driver lỗi | upscale | kiểm NVENC lúc cài (P4); cân nhắc thêm fallback libx264 CPU (gốc không có) |
| Đĩa tạm PNG ×4 rất nặng (4K) | upscale | `_guard_disk` gốc đã chặn; cấu hình scratch lớn + batch 360-frame |
| Người dùng tưởng AUTO SUB tự tạo phụ đề | autosub | quyết định mục 6; nếu giữ "nạp transcript" → nói rõ trên UI |
| Editor WYSIWYG 2142 dòng JS | autosub | MVP cắt gọn, fast-follow sau |
| Credit chưa có ở gốc, dễ định giá sai | cả 2 | chốt đơn giá với bạn (mục 2.2/3.3) trước khi build |

## 6. Quyết định cần bạn duyệt (trước khi build)

1. **Thứ tự**: AUTO SUB trước (khuyến nghị) hay UPSCALE trước?
2. **AUTO SUB — phạm vi**:
   (a) **Giữ nguyên bản chất** = burn phụ đề từ transcript người dùng nạp (nhanh, đúng module gốc); hoặc
   (b) **Thêm Whisper** tự nghe-chép (đúng nghĩa "AUTO", GPU RTX 5060 Ti chạy tốt, nhưng +1 phụ thuộc nặng + credit STT riêng — lấy tham chiếu `cutclipshort/adapters/whisper.py`).
3. **Upload lớn**: làm **P1 presigned PUT ngay** (mở tới 2GB) hay **MVP tạm cap ~90MB** (clip ngắn) rồi làm P1 sau?
4. **Đơn giá credit**: chốt `don_gia_co_ban` upscale (gợi ý 20-40/phút @1080p Fast) và `don_gia_sub` (gợi ý 3-8/phút).

Sau khi bạn chốt 4 mục trên, tôi mới bắt đầu B2→B7 theo công thức di trú.

## 7. QUYẾT ĐỊNH ĐÃ CHỐT (2026-08-01, người dùng)

1. **Thứ tự: AUTO SUB trước**, rồi P3 (GPU worker) → UPSCALE.
2. **AUTO SUB giữ nguyên bản chất**: khắc phụ đề từ transcript người dùng nạp
   (KHÔNG Whisper). UI ghi rõ cần transcript. (Whisper để dành fast-follow nếu cần.)
3. **Làm P1 presigned PUT ngay** — mở upload tới 2GB cho cả 2 app.
4. **Đơn giá theo gợi ý**: UPSCALE ~30 credit/phút @1080p Fast (×1.8 @1440p, ×4 @4K,
   ×2.5 Quality); AUTO SUB ~5 credit/phút (draft ×0.6, standard ×1.0, high ×1.5).
   Chỉnh được trong admin sau.

→ Bắt đầu: **Chặng 0** (P1 presigned PUT + P4 ffmpeg config + P5 ffprobe duration)
rồi **Chặng A** (AUTO SUB VIDEO).

## 8. TIẾN ĐỘ THỰC HIỆN (2026-08-01)

- ✅ **Chặng 0**: P1 `Storage.put_url` presigned PUT + `UploadTarget`; P4/P5
  `platform_core/media.py` (locate ffmpeg/ffprobe, probe duration, gpu-detect,
  run_with_progress). `server/app.py` CSP thêm media-src + connect-src cho R2/blob.
- ✅ **Chặng A — AUTO SUB VIDEO (`autosubvideo`) XONG + nghiệm thu THẬT trên
  production** (xem NHAT_KY 2026-08-01). Full E2E: login → form → upload → worker
  burn (LocalSystem+LTT_FFMPEG) → R2 → billing → phát video 206 từ R2. 1675 test pass.
- ⚠️ **Chặn còn lại (user)**: bật **CORS bucket R2** cho upload thẳng browser→R2
  (hiện lùi về multipart ≤90MB). Ghi ở KE_HOACH_TON_DONG.
- ✅ **Chặng B — UPSCALE VIDEO (`upscalevideo`) XONG + nghiệm thu THẬT** (2026-08-01,
  xem NHAT_KY). Vendor Real-ESRGAN copy thẳng (Windows). E2E: 480×270→1920×1080 trên
  worker GPU, encoder h264_nvenc, phát 206 từ R2. `service.submit_upscale_job()` là
  điểm dùng lại cho seedance. Sửa bug NVENC-detection (nullsrc 64×64 → testsrc 256).
- ⚠️ **Chưa làm (ghi backlog, chưa gấp — chờ tải thật)**:
  - **P3**: worker đa tiến trình + định tuyến GPU (job upscale dài chặn worker đơn).
  - **CORS bucket R2** (user): upload thẳng file lớn (hiện lùi multipart ≤90MB).
  - Đấu nút "Nâng cấp 4K" trong taovideo (gọi `service.submit_upscale_job`) — code
    dùng lại đã sẵn, chỉ còn thêm nút UI khi cần.
