# 02 — GAP MATRIX: hiện tại × đối thủ × mục tiêu

> Hạng mục = thứ khách nhận được. Trạng thái: **CÓ** / **YẾU** / **THIẾU** / **KHÔNG**.
> "Cơ sở" trỏ về `_A` (audit code), `_C` (đối thủ) hoặc code dẫn chứng.

## Nhóm 1 — Hiểu video (UNDERSTANDING)

| Hạng mục | Hiện tại | Đối thủ chuẩn | Mục tiêu | Chênh lệch |
|---|---|---|---|---|
| STT tiếng Việt word-level + timestamps | **CÓ** (Whisper GPU) | OpusClip công bố 92–97% (tiếng Anh), VI = BETA | Giữ + đo WER VI thật, hiển thị confidence | **YẾU**: chưa có số WER VI, chưa disclosure confidence |
| Scene/motion/audio/visual/content | **CÓ** (6 engine) | OpusClip "mỗi khung hình" (marketing) | Giữ — đủ cho scoring | Không |
| Đa chủ thể / tracking xuyên clip | **KHÔNG** (framing 2 keyframe, `framing.py:105`) | OpusClip ReframeAnything track speaker+objects | V2: tracking per-frame (mẫu frame) + VLM hỗ trợ | **THIẾU — P0** |
| Phân tích khung hình bằng VLM | **KHÔNG** | ClipAnything "multimodal: visual/audio/sentiment" | VLM mẫu 8–16 khung hình/segment để enrich memory | **THIẾU — P0** |
| Speaker diarization | **KHÔNG** | OpusClip có (blog transcription API) | Dùng Whisper speaker (nếu adapter có) hoặc VLM | THIẾU (P2) |

## Nhóm 2 — Biên tập (EDITORIAL — điểm trống lớn nhất)

| Hạng mục | Hiện tại | Đối thủ chuẩn | Mục tiêu | Chênh lệch |
|---|---|---|---|---|
| Prompt-directed clipping ("cắt cho tôi đoạn X") | **KHÔNG** | ClipAnything + reprompt | Người dùng gõ ý định VN → LLM map vào memory → chọn/giữ khoảnh khắc | **THIẾU — P0** |
| Lý do chọn clip (explainability) | **KHÔNG** (chỉ số heuristic) | Score 4 chiều có tên Hook/Flow/Value/Trend | LLM sinh lý do tiếng Việt + score có confidence | **THIẾU — P0/P1** |
| Editorial theo heuristic 6-pass | **CÓ** (pure Python, 1630 dòng) | Klap: LLM phân tích context/tone/flow | Giữ làm fallback + làm "cứng" khi LLM bận/hỏng | Không (giữ nguyên) |
| Human-in-the-loop: chọn lại/sửa trước render | **KHÔNG** (one-shot → package) | Cả 9 đối thủ đều có dạng nào đó | UI review: giữ/bỏ/tuỳ chỉnh 3–5 candidate rồi render | **THIẾU — P0** |
| "Giữ khoảnh khắc này" (pin) | **KHÔNG** | Pattern chống phàn nàn "bỏ lỡ khoảnh khắc" | Pin thời điểm → lần sau ranker ưu tiên (loop learning) | **THIẾU — P1** |
| Re-render revision | **KHÔNG** | OpusClip text-based edit | Sửa 1 clip → re-render chỉ clip đó, quote credit riêng | **THIẾU — P1** |

## Nhóm 3 — Chọn & đánh điểm (RANK)

| Hạng mục | Hiện tại | Đối thủ chuẩn | Mục tiêu | Chênh lệch |
|---|---|---|---|---|
| Rank 4-mục tiêu heuristic | **CÓ** | OpusClip 0–99 4 chiều | Giữ, thêm chiều "khớp prompt" khi có prompt | **YẾU** |
| Quality gate chặn clip kém | **TỒN TẠI NHƯNG KHÔNG NỐI** (`evaluation/gate.py`) | (đối thủ không công bố) | Nối gate vào jobs.py giữa editorial→render | **THIẾU — P0 (sức bền)** |
| Viral score có confidence | **KHÔNG** (hard threshold) | Klap/Vizard 0–100 + giải thích | Score + khoảng confidence + lý do | **THIẾU — P1** |
| Vòng học từ feedback (pin, chọn/bỏ, retention) | **KHÔNG** (grep `learned_preferences` → 0) | **KHÔNG ai có trong 9 đối thủ** (chỉ Submagic có stats API của họ) | `preference_store` + ranker đọc → lợi thế độc quyền VN | **THIẾU — P1** (khác biệt hoá) |

## Nhóm 4 — Render

| Hạng mục | Hiện tại | Đối thủ chuẩn | Mục tiêu | Chênh lệch |
|---|---|---|---|---|
| Encode NVENC p5 / fallback | **CÓ** | — | Giữ | Không |
| Reframe auto theo người | **YẾU** (2 keyframe + smooth; fallback center khi không người) | ReframeAnything per-frame | Tracking denser (mẫu 1 fps) + VLM "ai là chủ thể" + an toàn khi không người | **THIẾU — P0** |
| Manual reframe override (drag/crop khung) | **KHÔNG** | OpusClip multi-subject tracking thủ công | UI kéo khung trong preview → ghi đè keyframe | **THIẾU — P0** |
| Caption ASS + highlight | **CÓ** | 123+ ngôn ngữ (Submagic) | Giữ + chọn font/brand preset có sẵn | Không (P2 brand) |
| Safe zones theo platform | **CÓ** (margin 15%/12%/5.5%) | 6 nền tảng | Mở rộng profile FB (kênh số 1 VN) | **YẾU — P2** |
| Export FCPXML/XML | **KHÔNG** | Gling/OpusClip có | P2 (đội làm phim VN) | THIẾU (P2) |

## Nhóm 5 — Phân phối & vòng lặp (DISTRIBUTION)

| Hạng mục | Hiện tại | Đối thủ chuẩn | Mục tiêu | Chênh lệch |
|---|---|---|---|---|
| Nối publish_bot (đã có trong hệ LTT) | **KHÔNG nối** | OpusClip scheduler 6 nền tảng | Typed handoff → publish_bot, trạng thái quay lại history | **THIẾU — P1** (lợi thế hệ sinh thái) |
| History clip + ZIP bulk | **CÓ** (package zip) | — | Thêm phân trang/search theo job | **YẾU — P2** |
| Analytics retention → ranker | **KHÔNG** | Không ai có (kể cả OpusClip) | Sau khi publish_bot trả về stats → hiệu chỉnh ranker | **THIẾU — P2** (viễn) |

## Nhóm 6 — Vận hành (RELIABILITY)

| Hạng mục | Hiện tại | Mục tiêu | Chênh lệch |
|---|---|---|---|
| Quality gate trong pipeline | Không nối | Nối, có chế độ dev (cảnh báo) vs release (chặn) | **P0** |
| Cancel cooperative | Chỗ chỗ giết FFmpeg thread (`_A` §7.1) | Kill process tree + timeout | P1 |
| Cache key | Thiếu genre/tier/aspect | Mở rộng key + version | **P0** (rẻ, làm ngay) |
| LLM trong pipeline: degrade khi máy B bận | Chưa tồn tại (chưa có LLM) | Mọi bước LLM phải có fallback heuristic (luật của cầu nối: `BanError` → lui) | **P0 (thiết kế)** |
| VRAM 6000 MB | Giữ | Giữ; đo lại sau khi thêm VLM sampling | P0 (đo) |
| Test video thật | 4 file sẵn | Nghiệm thu mỗi phase trên 4 video | P0 |

## Tóm tắt 5 chênh lệch P0

1. **Nối quality gate vào jobs.py** — code có sẵn (`evaluation/gate.py`), việc là tích hợp + test.
2. **Prompt-directed clipping + Editorial Brain V2** — LLM đọc structured memory → chọn clip theo ý định VN; heuristic 6-pass làm fallback.
3. **Reframe V2** — tracking denser + VLM chủ thể + **manual override** (UI kéo khung).
4. **UI review human-in-the-loop** — từ one-shot thành "xem 3–5 candidate → giữ/sửa → render".
5. **Cache key đúng ngữ cảnh** + **degrade an toàn khi LLM bận** — hai việc vận hành rẻ nhưng chặn sự cố.
