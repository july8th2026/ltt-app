# 08 — CẤU HÌNH THẬT ĐANG CHẠY (đóng `S8`)

Đọc **chỉ-đọc** từ `D:\FULL AUTO VIDEO\` ngày 2026-09-09 — bản đang phục vụ,
đã chạy khoảng một năm. Bí mật (khoá API, sheet id, folder id, credentials)
**không** chép vào đây.

---

## 0. Trước hết: kho git CÓ khớp bản đang chạy

Nghi ngờ đầu tiên phải loại trừ là "kho git đã trôi khỏi bản chạy". Đo, không
đoán — so từng tệp `.py`, chuẩn hoá kết dòng trước khi so:

| Bot | khớp | **khác** | chỉ ở kho | chỉ ở bản chạy |
|---|---:|---:|---:|---:|
| transcript | 54 | **0** | 0 | 7.810 (toàn bộ là `venv/`) |
| pause | 29 | **0** | 0 | 7.848 (`venv/` + 1 tệp thử) |
| dungvideo | 165 | **0** | 0 | 11.429 (`venv/` + backup + **2 tệp thật**) |

⭐ **Không một tệp `.py` nào khác nhau.** Bản audit `03`–`06` đọc đúng mã đang
chạy. (Lượt `diff` đầu báo "mọi tệp đều khác" — đó là **kết dòng**: kho là CRLF
sau checkout, bản chạy là LF. Chuẩn hoá rồi mới so.)

🔴 **Nhưng hai tệp có thật chỉ tồn tại ở bản chạy:**

```
engine/music/mood.py        7.682 byte   ← STAGE 9 MUSIC, KHONG co trong kho git
engine/music/__init__.py    0 byte
```

⇒ `S10` mới: giai đoạn nhạc của `dungvideo` **chưa được audit**, vì nó không có
trong kho. Phải đọc `mood.py` trước Phase 11.

---

## 🔴 1. Bảng ĐÍNH CHÍNH — audit nói gì, thật ra là gì

Đây là phần đắt nhất của tệp này. Mọi dòng dưới đây là một chỗ mà parity matrix
`03`–`06` sẽ đo **sai** nếu dùng mặc định trong mã.

| Bot | Hạng mục | Audit nói (mặc định trong mã) | **THẬT trên production** |
|---|---|---|---|
| transcript | `segment.min_s` / `max_s` | 3.0 / 6.0 | **1.5 / 6.0** |
| transcript | độ dài đoạn của whisper | *(không biết)* | **`min_segment_s=2.5` · `max_segment_s=5.5`** |
| transcript | `silence_text` | `[B-ROLL: PAUSE]` | **`[B-ROLL / PAUSE]`** (dấu `/`, không phải `:`) |
| transcript | `silence_chunk` | dải 3.0–6.0 | **một số: 5.0** |
| transcript | sửa bằng Gemini | `DEFER`, chưa rõ | **`enable_gemini_correction = False`** — đã tắt sẵn |
| pause | `max_pause_ms` | 2500 | **15000** — gấp **6 lần** |
| pause | `min_pause_ms` | 120 | **50** |
| pause | ngưỡng khớp mờ | *(không biết)* | **`fuzzy_threshold = 0.65`** |
| pause | `beam_size` / `best_of` | "từ config" | **theo NGÔN NGỮ: vi=5/3 · en=1/1** |
| dungvideo | chế độ khớp dòng thời gian | `semantic` (mặc định trong mã) | **`sequential`** |
| dungvideo | tự chấm điểm | `DEFER`, ngoài MVP | **`enable: true`** — đang bật |
| dungvideo | `whisper` độ dài đoạn | *(không biết)* | **3.0 / 5.0**, gộp <2.0, tách >8.0 |

⭐ **Ba dòng đầu tiên đủ để hỏng một bản port trông hoàn hảo.** `max_pause_ms`
lệch 6 lần: một phép kiểm parity dùng mặc định trong mã sẽ kẹp mọi khoảng lặng
xuống 2,5 giây trong khi production cho tới 15 giây — và bản port vẫn "chạy
đúng", vẫn ra file nghe được.

🔑 **`timeline.mode: sequential` là dòng nặng nhất.** Bản audit `06` xếp khớp
CLIP (`matcher.py`) là đường P0 và phân tích kỹ tính tham lam của nó. Production
**không đi đường đó** — nó khớp theo **tiền tố tên tệp**
(`build_sequential_timeline`). Đường CLIP vẫn phải giữ (là một chế độ hợp lệ),
nhưng thứ tự ưu tiên đảo lại: `sequential` là đường phải đúng trước.

⚠️ Và `clip.save_embeddings: true` vẫn bật, tức STAGE 5 (nhúng CLIP) **vẫn
chạy** dù chế độ khớp không dùng tới nó. Đó là chi phí GPU thật cho một kết quả
không ai đọc — ghi nhận, **không** sửa trong lúc migrate (MASTER-GUARDRAILS #6).

---

## 2. `bot_transcript` — `configs/bot_config_whisper.json`

```
whisper   model=large-v3 · language=auto · auto_detect=True · fallback=vi
          device=cuda · compute_type=float16 · word_timestamps=True
          min_segment_s=2.5 · max_segment_s=5.5 · strategy=seamless
          gap_threshold=0.1 · use_enhanced_processing=True
          enable_gemini_correction=False   (gemini_model=gemini-2.5-flash,
                                            batch=8, max_change_ratio=0.4)
segment   min_s=1.5 · max_s=6.0
timeline  include_silence=True · silence_text="[B-ROLL / PAUSE]"
          min_silence_keep=2.0 · silence_chunk_s=5.0
          add_scene_id=True · scene_id_prefix="S" · scene_id_pad=4
          merge_consecutive_silences=False
          smart_silence: enabled=True, mode="rules", default="[B-ROLL: PAUSE]"
          tiered_silence: enabled=False (t1_max=7.0 t2_max=14.0
                          min_scene=3.0 max_scene=7.0)
vad       frame_ms=30 · min_speech_s=0.3 · min_silence_s=0.8
          pad_s=0.15 · thr_db_above_noise=12.0
runtime   poll=180s · max_jobs=3 · round_robin qua nhiều tab
```

### ✅ S12 ĐÃ ĐÓNG — chỉ MỘT chuỗi tới được engine

`timeline.silence_text` là `[B-ROLL / PAUSE]`, còn `timeline.smart_silence.default`
là `[B-ROLL: PAUSE]`. Hai chuỗi khác nhau trong cùng một tệp. Đo bằng cách đọc
đường gọi thật (`bot/worker.py:587`):

```python
silence_text = str(cfg_get(cfg, "timeline.silence_text",
                   cfg_get(cfg, "timeline.smart_silence.default",
                           "[B-ROLL / PAUSE]")))
```

⇒ `smart_silence.default` chỉ là **giá trị dự phòng của một giá trị đã có**.
`timeline.silence_text` được khai, nên nó thắng, và `[B-ROLL: PAUSE]` **không
bao giờ tới engine**. Đó là cấu hình chết.

⚠️ Nhưng cạm bẫy còn nguyên ở **mã**, không ở cấu hình: hai điểm vào của bộ dựng
dòng thời gian có **hai mặc định khác nhau**

```
segment/core.py:35   make_timeline_v2(..., silence_text="[B-ROLL: PAUSE]")
segment/core.py:165  make_timeline(...,   silence_text="[B-ROLL / PAUSE]")
```

⇒ Một bản port quên truyền `silence_text` sẽ nhận **dấu hai chấm** thay vì **dấu
gạch chéo**, và chỉ ở một trong hai đường. App `transcript` truyền tường minh
(`chu_khoang_lang` mặc định `[B-ROLL / PAUSE]` — khớp production).

⭐ **36 hồ sơ tab**, mỗi tab khai `language` riêng (`vi`/`en`/rỗng). Đây là một
năng lực thật của production mà audit chưa ghi: **ngôn ngữ theo từng nguồn**.
Trong LTT nó thành tham số `language` của job — hợp đồng ở `24_NODE_CONTRACTS.md`
đã có ô đó, nên không phải sửa hợp đồng.

## 3. `bot_pause` — `configs/bot_config_pause.json`

```
whisper   model=large-v3 · language=auto · cuda/float16 · word_timestamps=True
          beam_size_vi=5   beam_size_en=1
          best_of_vi=3     best_of_en=1
          temperature=0.0 · condition_on_previous_text=False
          freeze_threshold=0.2
pause     fuzzy_threshold=0.65
          min_pause_ms=50 · max_pause_ms=15000 · min_gap_s=0.8
audio     sample_rate=24000 · mono · mp3 · 128k
runtime   max_jobs=1 · poll 10s khi có việc / 120s khi rỗi
          processing_timeout_minutes=90 · verify_claim=True
```

🔴 **`beam_size`/`best_of` khác nhau THEO NGÔN NGỮ.** Đây là **hồ sơ STT thứ
năm**, và nó không phải một hồ sơ mới — nó là một hồ sơ **có tham số**. Bảng bốn
hồ sơ ở `07_CROSS_BOT_SYNTHESIS.md` §2 phải sửa: hồ sơ `pause` không phải một bộ
số, mà là một hàm của `language`.

⚠️ `max_jobs=1` — bot này cố ý chạy **một job một lúc**. Trong LTT, tương đương
là `admission_slots=1`, không phải "để mặc định".

## 4. `bot_dungvideo` — `configs/pipeline.yaml`

```
output      mp4 · h264_nvenc · 1920x1080 · 30fps
whisper     large-v3 · min_segment_s=3.0 · max_segment_s=5.0
            merge_if_shorter_s=2.0 · split_if_longer_s=8.0
clip        model=ViT-L-14 · pretrained=laion2b_s32b_b82k
            sampling=motion_peak · uniform_fps=3
            reuse_max_times=3 · prefer_unused=true
filters     yolo=on · motion=on (threshold=null) · duplicates=on (phash=5)
timeline    mode=SEQUENTIAL · save_embeddings=true
music       on · thư mục theo cảm xúc: Calm/Tension/Action/Sad/Happy
            segment_len_s=[75,110] · avoid_start/end=10.0s · crossfade=2.5s
audio       voice_keep_original=true · base_clip_audio_gain_db=-18.0
            music_target_lufs=-26.0 · true_peak=-2.0 · lra=7.0 · post_gain=-7.0
            ducking: ratio=16.0 · threshold=-32dB · attack=15ms · release=600ms
transitions on · fade/dissolve/zoom/whip_pan = 0.3/0.4/0.2/0.1
            cooldown_same_type=2 · only_broll_boundaries=true
            speech_to_speech: mode=hybrid · threshold=0.3
              min_scene_s=4.0 · min_interval_s=7.5
              weights: semantic .35 · text_marker .35 · temporal_gap .3
                       + duration_bonus .1
              semantic_threshold=0.7 · gap_threshold_s=0.2
              ~90 discourse marker (tiếng Việt + tiếng Anh)
            dur_default_s=0.22 (min .18 / max .28)
            tag_overrides: TRANSITION .2 · ENVIRONMENT .24 · PAUSE .28
sanitize    on · preset=veryfast · crf=18
            logo_crop: bottom_px=76 · right_px=136
demucs      on · htdemucs_ft · cuda · two_stems
subtitle    on · sentence · style=default · max_chars_per_line=42 · max_lines=2
evaluation  ON · gemini-2.5-flash · skip_whisper=true · skip_yolo=false
cleanup     xoá tệp tải về sau khi upload · workdir_ttl=24h
```

⭐ Khối `transitions.speech_to_speech` là một **thuật toán chấm điểm có trọng
số** với ~90 dấu hiệu diễn ngôn hai thứ tiếng. Audit `06` không hề biết nó tồn
tại, vì nó sống hoàn toàn trong cấu hình. Đây là một mục **P0** nữa cho parity
matrix, và là ví dụ rõ nhất cho câu: *hành vi của bốn bot này nằm trong
`configs/` nhiều không kém trong mã.*

---

## 5. Việc phải làm tiếp

| # | Việc | Chặn phase |
|---|---|---|
| S10 | đọc `engine/music/mood.py` (chỉ có ở bản chạy) | 11 |
| S11 | sửa parity matrix `03`/`04`/`06` theo bảng đính chính §1 | 08/09/11 |
| S12 | `smart_silence.default` vs `timeline.silence_text` — đường nào dùng chuỗi nào | 08 |
| S13 | hồ sơ STT của `pause` là **hàm của `language`**, sửa `07` §2 | 09 |
| S14 | `sequential` là đường P0 của dungvideo, không phải `semantic` | 11 |

⛔ **Không chép một con số nào từ đây vào một tệp `.md` khác.** Chúng đã trôi
một lần rồi (mã nói 2500, production nói 15000). Chỗ này trỏ về `configs/` thật;
mọi nơi khác trỏ về chỗ này.
