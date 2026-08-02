# Kế hoạch xây App TẠO CLIP NGẮN (từ CUT CLIP SHORT — D:\FULL AUTO VIDEO)

> Lập 2026-08-02. Quy trình: user chỉ định app←module, Claude phân tích sâu + phương
> án + chấm điểm + đề xuất, chốt rồi build. Nguồn: map `D:\FULL AUTO VIDEO\CUT CLIP
> SHORT` (kho **chỉ đọc** mới, ngoài BOT GEMINI) + quy tắc tốt từ
> `docs/KHAO_SAT_BOT_GEMINI.md` + công thức `CONG_THUC_DI_TRU_APP.md`. Chỉ giữ tính
> năng **làm file trực tiếp**; bỏ tự-động-từ-sheet.

## 0. Bản chất + phát hiện cốt lõi

CUT CLIP SHORT = app desktop PySide6 (~50k LOC) biến **1 video dài → nhiều clip
ngắn dọc** (9:16, 1:1, 16:9, 4:5) cho TikTok/Shorts/Reels. Pipeline:

```
Video → PHÂN TÍCH (6 engine: scene/motion/speech/audio/visual/content)
     → EDITORIAL BRAIN (phát hiện hook/payoff, chấm điểm, xếp hạng — heuristic,
       KHÔNG cần LLM) → EDIT PLAN (ClipSpec[])
     → RENDER (FFmpeg: crop bám người (YOLO) → color → tăng tốc → loudnorm →
       burn phụ đề ASS theo từ) → QUALITY GATE → clip.mp4[]
```

**Ba phát hiện quyết định (rất thuận lợi):**
1. **Toàn bộ engine `cutclipshort/` copy SẠCH** — pure Python, không dính GUI. Worker
   chỉ gọi **3 hàm** (blueprint `test_local_run.py`): `run_full_analysis` →
   `run_editorial` → `render_segment`/`Compositor.render_clip`. Đây đúng ý "lấy hết
   code vận hành tinh túy".
2. **KHÔNG cần LLM, KHÔNG secret** cho luồng làm-file-trực-tiếp. Chọn highlight là
   heuristic/semantic nội bộ. Whisper (chép lời) + YOLO (bám người) **chạy cục bộ GPU**.
3. **Thiết kế SẴN cho RTX 5060 Ti 16GB** (`requirements-gpu.txt` gọi tên card 50xx
   Blackwell → cần **torch cu128**; `quality_tiers.py` đặc cách 16GB chạy 8 clip song
   song). GPU ta có dùng được ngay, tier `high_quality` khả thi.

## 1. Bốn rổ di trú

🟢 **COPY NGUYÊN (engine)** — cả `cutclipshort/`: core, analysis/*, editorial/*,
render/*, adapters/* (ffmpeg/whisper/yolo/scenedetect/demucs/ffmpeg_hw), presets/*,
storage/*, types/*. Vendor vào nền tảng, import thẳng.

🟡 **VIẾT LẠI THEO HỢP ĐỒNG** — manifest + jobs.py (bọc 3 hàm lõi, `ctx.progress`) +
routes.py (upload → job) + template (chọn tuỳ chọn + xem clip) + cost.py.

🔴 **THAY DỊCH VỤ NỀN TẢNG** — upload web + R2 (thay QFileDialog + ProjectPaths cục
bộ + downloader URL); **hàng đợi job + worker GPU** (thay QThread + polling); credit
ledger (engine không có); model cache (stage whisper/yolo).

⚫ **BỎ** — `bot/` (sheet automation), `gui/`, `gui_panels/`, `license/`, mpv,
downloader URL, PyInstaller specs.

## 2. Phụ thuộc nặng (điểm cần lo)

| Dep | Vai trò | Ghi chú |
|---|---|---|
| **torch + cu128** | nền GPU cho whisper/yolo | **~2.5GB, phải bản cu128** cho Blackwell (sm_120); sai bản → CPU chậm 20× |
| **faster-whisper** | chép lời (word timestamp) | model large-v3 ~1.5-3GB, cache `models/`; fallback base/CPU int8 |
| **ultralytics (YOLOv8)** | bám người để crop dọc | weight yolov8n bundled |
| scenedetect, opencv, numpy | scene/motion | nhẹ |
| demucs | tách nhạc/lời (tuỳ chọn) | tắt ở tier `fast`; nặng |
| ffmpeg NVENC + libass | cut/crop/encode/burn phụ đề | **ĐÃ CÓ** trên máy chủ |

→ Lực nâng hạ tầng chính = **cài torch cu128 + các gói ML + stage model** vào venv
nền tảng (dùng chung; chỉ worker chạy job cần). Nặng nhưng một lần.

## 3. BA PHƯƠNG ÁN — chấm điểm (1–10, cao = tốt)

| Tiêu chí | PA-A: Vendor FULL engine, tier-gated | PA-B: Cắt còn MVP (whisper+cut+crop+phụ đề) | PA-C: Viết lại từ đầu |
|---|---|---|---|
| Kế thừa "tinh túy" (editorial brain, reframe, quality) | **10** | 5 | 2 |
| Năng lực sản phẩm | **10** | 5 | 4 |
| Công sức build | 7 | 5 (bóc tách 50k LOC = tốn+rủi ro) | 4 |
| Rủi ro phụ thuộc | 6 (torch cu128+model nặng) | **8** | **8** |
| Hợp SaaS + GPU (job-queue sẵn) | **9** | 9 | 9 |
| UX khách | **9** | 6 | 5 |
| **Tổng** | **51** | 38 | 32 |

- **PA-A (ĐỀ XUẤT)**: vendor trọn engine, để **tier** (fast/balanced/high_quality)
  tự gate độ nặng (fast tắt demucs, dùng whisper base; balanced/high dùng large-v3).
  Đúng ý "lấy hết tinh túy", ít viết lại nhất (copy + wrapper mỏng), năng lực đầy đủ.
  Giá phải trả: cài torch cu128 + model nặng một lần.
- **PA-B**: bóc tay còn lõi tối giản → mất editorial brain (phần giá trị nhất) + phải
  tách 50k LOC (rủi ro hỏng). Tệ hơn về cả công sức lẫn giá trị.
- **PA-C**: viết lại → mất hết tinh túy. Loại.

**ĐỀ XUẤT: PA-A.**

## 4. Kiến trúc đề xuất (PA-A)

```
Trình duyệt ──upload (R2 presigned / multipart)──► app taoclipngan (routes)
   → submit JOB (hàng đợi Postgres) → WORKER GPU:
       jobs.handle: tải video → run_full_analysis (whisper+yolo+scene…) →
       run_editorial (chọn highlight) → render mỗi ClipSpec (ffmpeg NVENC + phụ đề)
       → upload N clip lên R2 → quyết toán credit
   → trang app hiện lưới clip (play/tải), per-user.
```
- Vendor `cutclipshort/` = package top-level trong repo (import được), gitignore model.
- `apps/taoclipngan/`: manifest (`requires=("gpu","ffmpeg")`, job_types), jobs.py
  (bọc 3 hàm lõi + progress + credit), routes.py (upload/queue/serve clip), cost.py,
  template (tuỳ chọn: số clip, tỉ lệ, độ dài, tier, ngôn ngữ, genre; lưới kết quả).
- Tuỳ chọn người dùng map thẳng `EditConstraints`/`RenderSettings`/tier.
- Output nhiều clip → mỗi clip 1 key R2 + điểm/tiêu đề tự sinh.

## 5. Credit (đề xuất, admin chỉnh — Q31: 1 credit = 100đ)

Engine không có tính tiền. Chi phí thật = thời gian GPU (chép lời theo độ dài nguồn +
encode theo số clip). Đề xuất:
```
credit = phút_video_nguồn × đơn_giá_tier + số_clip_xuất × đơn_giá_clip
tier: fast ×1.0 · balanced ×1.6 · high_quality ×2.2
```
Gợi ý `đơn_giá_tier` ~8 credit/phút (balanced), `đơn_giá_clip` ~5/clip. Số cụ thể chốt sau.

## 6. Lộ trình phân pha (có điểm dừng)

- **K0 — Hạ tầng deps**: cài torch **cu128** + faster-whisper + ultralytics + scenedetect
  + opencv (+demucs) vào venv; stage model (yolov8n bundled; whisper base→large khi cần);
  smoke import engine + whisper GPU. (Đây là chặng rủi ro nhất — torch cu128.)
- **K1 — Vendor engine**: copy `cutclipshort/` vào repo; sửa import nếu cần; smoke chạy
  `test_local_run`-style trên 1 video ngắn (headless) trong venv.
- **K2 — App + job**: manifest + jobs.py (3 hàm lõi + progress + credit reserve/settle)
  + routes (upload→job) + template + serve clip R2.
- **K3 — Nghiệm thu THẬT**: browser upload video → job GPU chạy → lưới clip phát được
  + credit trừ; test + docs + memory.

## 7. Rủi ro & chặn

| Rủi ro | Chặn |
|---|---|
| **torch cu128 cài nặng/sai bản → CPU 20×** | pin cu128 rõ; smoke `torch.cuda.is_available()` + whisper GPU trước khi build tiếp |
| Model whisper large-v3 ~3GB tải lần đầu chậm | stage sẵn (download_models tương đương) hoặc mặc định `base`, cho chọn large |
| Job GPU rất dài (video dài) chặn worker đơn | **P3** (worker đa tiến trình) — nối tiếp backlog; job dài là bản chất |
| Engine 50k LOC vendor — import kéo dep lúc load | kiểm adapter lazy-import torch/whisper/yolo; import engine không được đòi GPU |
| Upload video lớn >100MB | P1 presigned PUT (đã có) / multipart ≤90MB |
| Demucs nặng | mặc định tắt (tier fast/balanced), chỉ high_quality nếu muốn |

## 8. CÂU HỎI CẦN CHỐT (có sẵn lựa chọn)

1. **Phạm vi** — PA-A vendor full engine tier-gated (đề xuất) / PA-B MVP cắt gọn?
2. **Tier mặc định** — balanced (large-v3 GPU, chất lượng cao) / fast (base, nhanh+rẻ)?
   (app vẫn cho user chọn tier; đây là mặc định.)
3. **Cài torch cu128 + model nặng** vào venv nền tảng (~vài GB) — đồng ý? (bắt buộc để
   chạy GPU; đây là chặng hạ tầng lớn nhất.)
4. **Đơn giá credit** — theo gợi ý (balanced ~8/phút + 5/clip) hay bạn tự đặt?

## 9. TRẠNG THÁI: XONG + NGHIỆM THU THẬT (2026-08-02)

Chốt: PA-A vendor full engine · tier mặc định high_quality · torch cu128 · đơn giá gợi
ý. **K0→K3 XONG + verified live** (xem NHAT_KY 2026-08-02):
- torch 2.11+cu128 CUDA=True (RTX 5060 Ti); engine `cutclipshort/` vendored ở gốc repo.
- `apps/taoclipngan/` bọc 3 hàm lõi + credit + upload/R2. Smoke GPU 2 clip; browser E2E
  1 clip phát 206 từ R2 + credit.
- Bug ffmpeg-PATH trên worker → fix prepend LTT_FFMPEG vào PATH trong jobs.handle.
- **Còn (fast-follow)**: tiêu đề/điểm clip trống (map candidate↔clip_spec); P3 worker đa
  tiến trình; stage large-v3 cho high_quality; CORS R2 upload lớn.
