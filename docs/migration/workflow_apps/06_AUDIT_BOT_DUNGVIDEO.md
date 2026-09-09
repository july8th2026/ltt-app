# 06 — AUDIT `bot_dungvideo` (Video Assembly)

`giaitritruyenthongltt-spec/bot_dungvideo@b0e25ed4` · `main` · 2026-09-05 14:54 +0700
Bản sao nghiên cứu: `D:\LTT_4BOT_LAB\bot_dungvideo`
165 tệp `.py` · 40.328 dòng.

## Bot này làm gì

Một thư mục clip thô + một thư mục nhạc → **một video hoàn chỉnh**: chọn clip
khớp lời, ghép, tách nhạc nền, trộn tiếng, cháy phụ đề, rồi tự chấm điểm.

## Mười ba giai đoạn — `engine/runner.py::run_local_job`

```
 0 INPUT VALIDATION     validate_input_structure
 1 VIDEO SANITIZE       (tuỳ chọn) engine/video_sanitize.py
 2 TRANSCRIPTION        engine/stt.py            ← whisper
 3 CLIP SAMPLING        engine/clip_sampling.py
 4 FILTERING            filters/duplicates.py · motion.py · yolo_quality.py   ← YOLO
 5 EMBEDDING            engine/clip_embed.py                                  ← CLIP
 6 TIMELINE MATCHING    engine/matcher.py · sequential_timeline.py
 7 VIDEO ASSEMBLY       engine/assemble.py (1.285 dòng, ffmpeg/NVENC)
 8 DEMUCS (tuỳ chọn)    audio/demucs_post.py                                  ← Demucs
 9 MUSIC
10 AUDIO MIX            audio/mix.py
11 SUBTITLE (tuỳ chọn)  subtitle/{segmenter,ass_builder,burner,font_checker,style_registry}
12 EVALUATION (tuỳ chọn) engine/evaluation/**                                 ← YOLO lần hai
```

## 🔴 Bốn model thật trong một job — và đây là bot đặt ra bài toán tài nguyên

`whisper` · `YOLO` · `CLIP` · `Demucs`. Bot legacy tự quản bằng `gpu_arbiter.py`
(1.520 dòng) + `gpu_claims.py` + `bot_coordination.py`, và runner có những câu
như *"sau STAGE 8 … Evaluation (còn dùng YOLO) sẽ TỰ XIN lease riêng, ngắn hạn,
ở STAGE 12"*.

⇒ Toàn bộ tầng ấy là `DROP_LEGACY`: LTT đã có `platform_core/gpu_lease.py`,
`gpu_claims.py`, `leases.py`, và `ToolSpec.admission_resource` + `admission_slots`.

⚠️ Nhưng **món nợ đi kèm phải được nhận**, vì kho này đã trả giá cho nó rồi:
memory *máy chỉ có 10 lõi* ghi ngày 03/09 có **12 tiến trình `demucs`, mỗi cái
460–984% CPU**, vì `demucs_runner.py` không đặt `torch.set_num_threads`. Ngân
sách `-n` **không đếm tiến trình cháu**. App này phải khai `admission_slots` và
mọi test nạp model thật phải nằm sau rào `LTT_TEST_NANG`.

## Hồ sơ STT thứ ba và thứ tư

```python
# engine/stt.py:48
model.transcribe(voice_path, language=language,
    word_timestamps=False,              # ⇐ transcript BẮT BUỘC True
    vad_filter=True, vad_parameters={"min_silence_duration_ms": 500,
                                     "threshold": 0.5},
    condition_on_previous_text=False, beam_size=5)      # ⇐ transcript dùng 1

# engine/evaluation/adapters/whisper.py:361 — hồ sơ THỨ TƯ, trong CÙNG một bot
model.transcribe(audio_path, language=None,
    word_timestamps=False, vad_filter=False)
```

⇒ Bốn hồ sơ, bốn đầu ra khác nhau. Bảng đầy đủ ở `07_CROSS_BOT_SYNTHESIS.md`.

## SOURCE MAP

| Module | Vai trò | Critical | Quyết định |
|---|---|---|---|
| `engine/runner.py` (803) | 13 giai đoạn | ✅ | `REUSE_ADAPT` → job handler |
| `engine/assemble.py` (1.285) | ffmpeg/NVENC, chuyển cảnh | ✅ | `REUSE_ADAPT` → `platform_core/media.py` |
| `engine/matcher.py` · `sequential_timeline.py` | khớp clip ↔ lời | ✅ | `REUSE_DIRECT` |
| `engine/clip_embed.py` · `clip_sampling.py` | nhúng CLIP | ✅ | `REUSE_ADAPT` |
| `engine/filters/*` | trùng lặp · chuyển động · chất lượng YOLO | ✅ | `REUSE_DIRECT` |
| `engine/subtitle/*` (9 tệp) | ASS · cháy phụ đề · font · style | ✅ | `REUSE_ADAPT` |
| `engine/audio/*` | Demucs · trộn | ✅ | `REUSE_ADAPT` |
| `engine/evaluation/**` | tự chấm điểm | ⚠️ | `DEFER` — ngoài MVP |
| `engine/stt.py` | whisper, hồ sơ riêng | ✅ | `REUSE_ADAPT` |
| `bot/worker.py` (1.338) · `bot/gsheets.py` · `gdrive.py` · `oauth.py` | Sheet/Drive/state | ❌ | `DROP_LEGACY` |
| `gpu_arbiter.py` · `gpu_claims.py` · `gpu_recorder.py` | trọng tài GPU | ❌ | `DROP_LEGACY` |
| `gui/**` (≥3.500) | GUI Tkinter | ❌ | `REWRITE_LTT` |
| `bot/recovery.py` · `progress_tracker.py` · `stage_logger.py` | khôi phục/tiến độ cục bộ | ❌ | `DROP_LEGACY` → job events |

⚠️ **`REWRITE_LTT` cho GUI ở đây nặng hơn ba bot kia**: `gui/widgets/subtitle_form.py`
(983) là một biểu mẫu tham số phụ đề đầy đủ. Đó là một bề mặt sản phẩm, không
phải một nút bấm.

## PARITY MATRIX

| Năng lực | Mức | Đo bằng gì |
|---|---|---|
| 13 giai đoạn đúng thứ tự, tuỳ chọn đúng chỗ | **P0** | nhật ký giai đoạn |
| Chọn clip khớp lời | **P0** | tập clip chọn ra, theo thứ tự — trên bộ đầu vào cố định |
| Lọc trùng / chuyển động / chất lượng | **P0** | tập clip bị loại |
| Dòng thời gian tuần tự | **P0** | mốc mỗi clip |
| Ghép video | **P0** | thời lượng · codec · số khung |
| Trộn tiếng (mức nhạc/lời) | **P0** | đo LUFS |
| Cháy phụ đề | **P0** | có/không · style · font tồn tại |
| Demucs tách nhạc | P1 | tuỳ chọn |
| Tự chấm điểm | P2 | `DEFER` |
| NVENC khi máy có | P1 | codec đầu ra — ⚠️ máy không có bộ mã hoá phần cứng thì **không kết luận được** |

⛔ **Không so từng byte tệp video.** Bằng nhau từng byte không đạt được qua hai
lần chạy ffmpeg. Phép đo là **thời lượng · codec · số khung · tập clip chọn ·
mốc thời gian · LUFS**.

## S4 ĐÃ ĐÓNG — `matcher.py` chỉ 75 dòng, và có HAI bất ngờ

### Bất ngờ 1: có **hai** chế độ khớp, không phải một

```python
# engine/runner.py:365
if cfg.get("timeline", {}).get("mode", "semantic") == "sequential":
    timeline = build_sequential_timeline(...)   # theo TIEN TO TEN TEP
else:
    timeline = match_timeline(...)              # theo CLIP embedding
```

`sequential` khớp bằng tên tệp: `PREFIX_PATTERN = ^(\d{3,4})-scene` và
`SCENE_ID_PATTERN = scene_?id[-_](\d+)(?:-(\d+))?`. Cả hai chế độ đều **P0**.

⛔ Một bản port chỉ làm `semantic` sẽ chạy đúng với mọi ca thử tự dựng, và hỏng
với đúng những khách đặt tên tệp theo cảnh.

### Bất ngờ 2: `semantic` là THAM LAM và PHỤ THUỘC THỨ TỰ

```
sims  = sfeat @ clip_feats.T          # tích vô hướng, mỗi đoạn một lần
order = argsort(sims, descending)
  pass 1  nếu prefer_unused: lấy clip đầu tiên có used == 0
  pass 2  nếu chưa có: lấy clip đầu tiên có used < reuse_max
  pass 3  fallback: order[0]
clips[chosen]["used"] += 1            # ⇐ ĐỔI TRẠNG THÁI
```

🔴 **Mỗi đoạn tiêu một clip và làm đổi lựa chọn của mọi đoạn sau.** Kết quả phụ
thuộc **thứ tự đoạn**, và nó **không** phải nghiệm tối ưu toàn cục.

⚠️ Đây là bẫy parity nguy hiểm nhất trong bốn bot: một bản port "tốt hơn" dùng
khớp tối ưu toàn cục (Hungarian) sẽ cho tập clip **khác** — và khác theo hướng
*trông đúng hơn*. Nó sẽ qua mọi phép kiểm về hình thức và trượt parity, hoặc tệ
hơn: qua cả parity nếu phép đo chỉ đếm số clip thay vì so **danh sách theo thứ tự**.

⇒ Phép đo parity phải là **dãy `(đoạn → clip)` đúng thứ tự**, không phải tập hợp.

Cấu hình đóng băng: `clip.reuse_max_times=3` · `clip.prefer_unused=True`.

`matcher.py` ném lỗi (không im lặng bỏ qua) khi thiếu embedding hoặc rỗng đầu
vào — hành vi ấy cũng phải giữ.

## Còn UNKNOWN

- Ngưỡng của `filters/*` (trùng lặp, chuyển động, YOLO) nằm trong `configs/` (`S8`).
- `engine/evaluation/**` — 5 thư mục con, chưa khảo sát; đã xếp `DEFER` nên
  không chặn MVP.
