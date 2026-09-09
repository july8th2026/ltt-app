# 03 — AUDIT `bot_transcript`

`giaitritruyenthongltt-spec/bot_transcript@278ed8d7` · `main` · 2026-09-05 14:54 +0700
Bản sao nghiên cứu: `D:\LTT_4BOT_LAB\bot_transcript`
54 tệp `.py` · 17.251 dòng.

## Bot này làm gì

Một tệp âm thanh → một `transcript.json` gồm các đoạn `speech`/`silence` có mốc
thời gian, đã qua VAD, STT và một tầng dựng dòng thời gian có ràng buộc độ dài.

## Đường chạy thật — đọc từ `bot/worker.py`

```
process_cycle()                      vòng lặp vô hạn
 └ _process_sheet_source()           mỗi Google Sheet
    └ _process_single_tab()          mỗi tab: quét TỪNG DÒNG
       ├ lọc: trigger_col == giá trị kích hoạt · output_col trống
       │      · status_col "pickable" · schedule_col chưa tới giờ
       ├ job_claimer.claim_job()     ghi khoá vào ô status_col
       ├ VramBudget("transcript", phase="WHISPER", needs_gb=5.0)
       ├ tải audio từ link Drive
       │  ── ENGINE bắt đầu ──
       ├ 1. vad_speech_segments()          engine/vad.py
       ├ 2. _transcribe_to_file()          engine/stt.py (cache theo hash audio)
       ├ 3. make_timeline_v2() / make_timeline()   engine/segment/*
       ├ 4. _project_strict_schema()
       ├ 5. _validate_no_consecutive_duplicate_speech()
       ├ 6. _validate_output_segments_strict()
       │  ── ENGINE kết thúc ──
       ├ ghi transcript.json
       ├ upload Drive + ensure_bot_folder_structure()
       └ ghi link ngược vào output_col
```

⭐ Bước 1–6 là **toàn bộ giá trị nghiệp vụ**. Mọi thứ còn lại là điều phối.

## SOURCE MAP

| Module | Vai trò | Critical | Quyết định | Đích LTT |
|---|---|---|---|---|
| `engine/vad.py` | phát hiện vùng có tiếng | ✅ | `REUSE_ADAPT` | `apps/<slug>/services/` |
| `engine/stt.py` | faster-whisper + cache theo hash | ✅ | `REUSE_ADAPT` | dùng chung, **giữ hồ sơ tham số riêng** |
| `engine/segment/*` (15 tệp) | dựng dòng thời gian, ghép/tách/đệm | ✅ | `REUSE_ADAPT` | `services/` |
| `engine/comprehensive_fixer_v5.py` | sửa văn bản sau STT | ✅ | `REUSE_ADAPT` | `services/` |
| `engine/gemini_corrector.py` | sửa bằng LLM | ⚠️ | `DEFER` | provider freeze — xem dưới |
| `engine/whisper_integration.py` | keo nối whisper | ✅ | `REUSE_ADAPT` | |
| `engine/_archive/*` (4 tệp, 1.828 dòng) | bản cũ đã thay | ❌ | `DROP_LEGACY` | — |
| `bot/worker.py` | vòng quét Sheet + state machine | ❌ | `DROP_LEGACY` | `platform_core/jobs.py` |
| `bot/state_manager.py` | trạng thái cục bộ | ❌ | `DROP_LEGACY` | job status |
| `utils/gsheets.py` · `utils/gdrive.py` | Sheet/Drive | ❌ | `DROP_LEGACY` | `platform_core/storage.py` |
| `gui_panels/*` (5 tệp, 2.400+ dòng) | GUI Tkinter | ❌ | `REWRITE_LTT` | GUI web-native |
| 7 module dùng chung | xem `07_CROSS_BOT_SYNTHESIS.md` | ❌ | `DROP_LEGACY` | |

## Hồ sơ STT — phải đóng băng, không được "chuẩn hoá"

```python
model.transcribe(voice_path,
    language=target_language,        # None => tự dò
    word_timestamps=True,            # engine/stt.py:306 — chú thích ghi "HARD RULE"
    beam_size=1, best_of=1, temperature=0.0,
    condition_on_previous_text=False)
```

⛔ **Không có `vad_filter`.** Bot này chạy VAD **riêng** ở tầng worker
(`vad_speech_segments`) rồi mới gọi STT. Ba bot kia bật `vad_filter` bên trong
whisper. Đây **không** phải một chi tiết cấu hình — nó quyết định ranh giới đoạn,
tức quyết định đầu ra. Xem bảng bốn hồ sơ ở `07_CROSS_BOT_SYNTHESIS.md`.

## PARITY MATRIX

| Năng lực | Mức | Hành vi legacy | Đo bằng gì | Ca vàng |
|---|---|---|---|---|
| VAD phân vùng tiếng | **P0** | `vad_speech_segments(audio)` | số vùng, tổng thời lượng tiếng | 1 audio ≥10 phút |
| STT có mốc từ | **P0** | `word_timestamps=True` bắt buộc | mỗi đoạn phải có `words` | `_validate_words_presence_or_error` |
| Ràng buộc độ dài đoạn | **P0** | `segment.min_s=3.0`, `max_s=6.0` | phân bố độ dài | ca vàng |
| Không hai đoạn tiếng trùng nhau liên tiếp | **P0** | `_validate_no_consecutive_duplicate_speech` | ném lỗi | có sẵn |
| Schema đầu ra nghiêm ngặt | **P0** | `_validate_output_segments_strict` | so schema | có sẵn |
| Cache STT theo hash audio | P1 | `_stt_cache_lookup/save` | lần hai không gọi model | |
| Đoạn `silence` khai được | P1 | `include_silence` | có/không | |
| Sửa văn bản sau STT | P1 | `comprehensive_fixer_v5` | so từng ký tự trên ca vàng | |
| Lịch chạy theo giờ | P2 | `schedule_col` | — | `DROP` — LTT có hàng đợi |
| Sửa bằng LLM | P2 | `gemini_corrector` | ngữ nghĩa | `DEFER` |

⭐ Bốn phép kiểm P0 **đã tồn tại trong chính legacy** dưới dạng hàm validate. Đó
là món quà của bot này: chúng chuyển thẳng thành phép kiểm parity, không phải
suy ra.

## Cảnh báo provider

`gemini_corrector.py` gọi Gemini. LTT có `apps/ltt_llm` + `platform_core/llm`.
⛔ MASTER-GUARDRAILS #6: **không vừa migrate vừa đổi provider.** Nên bước này
`DEFER` khỏi MVP, hoặc giữ nguyên provider và chỉ đổi đường gọi.

## S6 ĐÃ ĐÓNG — `word_scene_builder.py` là một HÀM THUẦN

`build_word_scenes(all_words, audio_duration, *, target_min, target_max,
hard_min, silence_threshold, silence_chunk_min, silence_chunk_max, silence_text)`
→ `list[scene]`. Không I/O, không GPU, không Sheet. Năm bước tất định:

```
1 _build_speech_candidates    gom từ thành đoạn ứng viên
2 _repair_speech_scenes       ghép đoạn ngắn, tách đoạn dài
3 _normalize_silence          đo khoảng lặng, hấp thụ ngừng vi mô
4 _generate_broll             sinh đoạn B-ROLL từ khoảng lặng còn lại
5 _assemble_timeline          ráp dòng thời gian cuối
```

⇒ Quyết định: **`REUSE_DIRECT`**. Đây là hình dạng lý tưởng để bê nguyên vào
`services/`.

### 🔴 HAI TẦNG GIỚI HẠN — gộp chúng là đổi đầu ra

| Tầng | Hằng số | Đến từ |
|---|---|---|
| **mềm** | `target_min=3.0` · `target_max=6.0` | `configs/` (`segment.min_s` / `max_s`) |
| **cứng** | `HARD_MIN=2.0` · `HARD_MAX=6.0` | `constants.py`, chú thích *"NON-NEGOTIABLE"* |
| mềm phụ | `SOFT_MIN=2.5` · `SOFT_MAX=6.5` | *"for gentle methods only"* |

⛔ `HARD_MAX` và `target_max` **tình cờ bằng nhau** (6.0) ở cấu hình mặc định. Một
bản port đọc thấy hai số giống nhau rồi gộp làm một sẽ chạy đúng **cho tới khi**
ai đó đổi `max_s` trong cấu hình — lúc đó tầng cứng biến mất, im lặng.

### Trọng số chấm ranh giới từ — đóng băng

```
W_PUNCT = 3.0    sức nặng của dấu câu
W_PAUSE = 3.0    sức nặng của khoảng ngừng
W_LEN   = 1.0    phạt lệch khỏi độ dài đích
STRONG_PUNCT = . ! ? … ; : 。！？        MED_PUNCT = , — – - ，
silence_threshold=2.0 · silence_chunk 3.0–6.0 · silence_text="[B-ROLL: PAUSE]"
_CONNECTOR_WORDS  — tập từ nối, cấm cắt ngay sau chúng
```

## Còn UNKNOWN

- Bộ tham số thật trong `configs/` trên máy production — bản trong repo có thể
  không phải bản đang chạy (`S8`).
