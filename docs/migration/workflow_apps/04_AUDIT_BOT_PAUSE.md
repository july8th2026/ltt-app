# 04 — AUDIT `bot_pause`

`giaitritruyenthongltt-spec/bot_pause@97a021a1` · `main` · 2026-09-05 14:54 +0700
Bản sao nghiên cứu: `D:\LTT_4BOT_LAB\bot_pause`
29 tệp `.py` · 10.423 dòng — **bot nhỏ nhất và sạch nhất trong bốn**.

## Bot này làm gì

Chèn khoảng lặng vào một bản thu, tại những **mốc văn bản** người dùng chỉ định.

Đầu vào là hai thứ: một audio, và một `pause_plan` — danh sách mốc:

```json
{"id": 1, "anchor_text": "Hà Nội. Những ngày",
 "pause_ms": 1800, "pause_type": "dramatic", "reason": "..."}
```

Đầu ra: audio đã chèn lặng **và** transcript đã dịch lại mốc thời gian.

## Đường chạy thật — `bot/worker.py::process_job`

```
1. STT                 engine/stt.py       → transcript có mốc từ (cache theo hash)
2. Khớp mốc            engine/anchor_matcher.py
                       fuzzy_span_search + match_boundary_anchor(threshold)
3. Lập kế hoạch chèn   engine/insertion_planner.py::generate_insertion_plan
                       clamp pause_ms vào [min_pause_ms, max_pause_ms]
                       bỏ mốc chồng nhau (giữ priority thấp hơn = ưu tiên cao hơn)
                       ép khoảng cách tối thiểu min_gap_s giữa hai lần lặng
4. Tìm điểm cắt im     engine/audio_splicer.py::find_silence_point + snap_all_cut_points
                       (RMS trong cửa sổ quanh mốc — cắt ở chỗ im nhất, không cắt đúng mốc)
5. Cắt + chèn lặng     cut_audio_segment + generate_silence  (ffmpeg)
6. Dịch mốc thời gian  engine/transcript_adjuster.py::adjust_transcript_timestamps
                       calculate_cumulative_silence(plan, t)
```

⭐ Bước 4 là chỗ **tinh tế nhất và dễ mất nhất khi port**: chèn lặng đúng vị trí
mốc sẽ cắt giữa một từ. `find_silence_point` dò RMS quanh mốc để tìm chỗ im nhất
rồi mới cắt. Một bản port "chèn tại `t`" chạy được, ra file nghe được, và **sai**.

## SOURCE MAP

| Module | Vai trò | Critical | Quyết định |
|---|---|---|---|
| `engine/stt.py` (436) | faster-whisper + cache | ✅ | `REUSE_ADAPT` — **hồ sơ khác** transcript |
| `engine/anchor_matcher.py` (384) | khớp mờ mốc văn bản | ✅ | `REUSE_DIRECT` |
| `engine/insertion_planner.py` | clamp · chống chồng · giãn cách | ✅ | `REUSE_DIRECT` |
| `engine/audio_splicer.py` (469) | dò điểm im · cắt · sinh lặng | ✅ | `REUSE_ADAPT` (ffmpeg → `platform_core/media.py`) |
| `engine/transcript_adjuster.py` | dịch mốc thời gian | ✅ | `REUSE_DIRECT` |
| `bot/worker.py` (1.050) | quét Sheet · claim · state | ❌ | `DROP_LEGACY` |
| `bot/state_manager.py` | trạng thái cục bộ | ❌ | `DROP_LEGACY` |
| `gui_panels/*` (1.847) | GUI Tkinter | ❌ | `REWRITE_LTT` |
| 7 module dùng chung | xem synthesis | ❌ | `DROP_LEGACY` |

⭐ Năm module engine đều **thuần hàm**: nhận dữ liệu, trả dữ liệu, không đụng
Sheet/Drive/GPU. Đó là lý do bot này là **ứng viên số một cho App đầu tiên**.

## Hồ sơ STT — KHÁC `bot_transcript`, và còn khác THEO NGÔN NGỮ

⚠️ Production khai `beam_size_vi=5 / beam_size_en=1` và `best_of_vi=3 /
best_of_en=1`. Nên hồ sơ của bot này không phải một bộ số mà là một **hàm của
`language`** — đã dựng thành `moc_tu_vad_trong_vi` / `_en` trong
`platform_core/stt/ho_so.py`, và thiếu ngôn ngữ là một **lỗi**, không phải một
lần đoán.

```python
whisper_model.transcribe(audio_path,
    language=lang,
    word_timestamps=word_timestamps,      # tham số, không cứng
    vad_filter=True,                      # ⇐ transcript KHÔNG có
    vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
    beam_size=..., best_of=..., temperature=...,      # từ config
    condition_on_previous_text=...)
```

⛔ **Đây là bẫy `common_utils.py`.** Hai bot cùng "gọi whisper" nên trông như
một năng lực dùng chung. Nhưng `vad_filter` đổi ranh giới đoạn, và `speech_pad_ms=200`
đệm thêm 200ms mỗi đầu — mà bot này **dùng chính ranh giới ấy để quyết định cắt
ở đâu**. Gộp hai lời gọi thành một mặc định chung là đổi đầu ra của ít nhất một
bot, im lặng.

⇒ Quyết định: **một service STT, nhiều hồ sơ tham số đã đóng băng**, mỗi App khai
hồ sơ của mình. Không có "tham số mặc định hợp lý".

## PARITY MATRIX

⚠️ **Giá trị lấy từ `configs/bot_config_pause.json` ĐANG CHẠY.** Chỗ lệch nặng
nhất: `max_pause_ms` là **15000**, còn mặc định trong mã là **2500** — gấp 6
lần. Một phép kiểm parity dùng mặc định trong mã sẽ kẹp mọi khoảng lặng xuống
2,5 giây, và bản port vẫn "chạy đúng".

| Năng lực | Mức | Hành vi legacy | Đo bằng gì | Ca vàng |
|---|---|---|---|---|
| Khớp mốc mờ | **P0** | `fuzzy_threshold=` **0.65** | mốc nào khớp, ở chỉ số từ nào | plan 4 mốc + audio thật |
| Clamp `pause_ms` | **P0** | **`[50, 15000]`** — mã mặc định `[120, 2500]`, lệch **6 lần** ở trần | so từng mốc | có sẵn |
| Bỏ mốc chồng nhau | **P0** | giữ `priority` nhỏ hơn | tập mốc còn lại | dựng 2 mốc chồng |
| Giãn cách tối thiểu | **P0** | `min_gap_s=0.8` | khoảng cách các lần lặng | |
| Cắt ở điểm IM, không ở mốc | **P0** | `find_silence_point` (RMS) | lệch giữa mốc và điểm cắt | ⚠️ **dễ mất nhất** |
| Dịch mốc transcript | **P0** | `calculate_cumulative_silence` | mọi mốc sau lần chèn thứ n | |
| Tổng thời lượng ra | **P0** | vào + tổng lặng | so số giây | |
| Cache STT | P1 | theo hash audio + model + ngôn ngữ + **tên hồ sơ** | lần hai không gọi model | |
| `pause_type` / `reason` | P2 | chỉ để ghi log | | |

## S5 ĐÃ ĐÓNG — `find_silence_point`, và nó đúng là mục dễ mất nhất

```python
find_silence_point(wav_path, at_sec, word_before_end, word_after_start=None,
                   search_margin=0.05, step_sec=0.005, window_sec=0.020)
```

Quét RMS từng bước **5 ms**, cửa sổ **20 ms**, lấy điểm có RMS nhỏ nhất.

### Ba luật của vùng tìm kiếm — mỗi luật là một cách port sai

| Luật | Giá trị | Bỏ nó thì hỏng thế nào |
|---|---|---|
| **chỉ tìm PHÍA SAU `word_before_end`** | không bao giờ lùi | cắt vào đuôi từ trước đó |
| `gap < 0.10` ⇒ nới tới `word_after_start + 0.30` | +300 ms | xem dưới |
| không có từ sau ⇒ `word_before_end + 0.5` | +500 ms | hụt vùng ở cuối tệp |
| vùng suy biến ⇒ `search_start + 0.2` | +200 ms | chia cho khoảng rỗng |

🔴 **Luật thứ hai là tri thức đã trả giá, không phải một hằng số tuỳ ý.** Chú
thích trong mã ghi thẳng lý do: *"Whisper báo gap quá nhỏ hoặc 0 → mở rộng tìm
kiếm thêm 0.3s vì Whisper timestamps thường sớm hơn thực tế 100-200ms."*

⇒ Một bản port "chèn lặng tại `t`" **chạy được, ra file nghe được, và sai** — và
không phép kiểm nào kêu, vì tệp vẫn hợp lệ và vẫn đúng thời lượng. Đây chính là
lý do mục này được xếp P0 *"dễ mất nhất"* trước cả khi đọc mã.

Trả về `round(best_t, 4)` — bốn chữ số thập phân, tức phép so parity phải so ở
đúng độ chính xác ấy, không so số thực trần.

## Còn UNKNOWN

- Ngưỡng `threshold` mặc định của `match_boundary_anchor` — nằm trong `configs/`
  (`S8`).
