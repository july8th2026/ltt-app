# Plan 0.4 — Độ tin cậy ghi lời theo clip (hiển thị UI)

> Thu gọn từ "WER tiếng Việt" theo quyết định 26/09 (hỏi chủ dự án):
> WER chuẩn cần corpus tiếng Việt chuẩn (chưa có); WER self-consistency
> (2× ASR) gấp đôi GPU ⇒ vỡ công thức credit. Whisper đã xuất confidence
> từng từ (0–1) — hiển thị độ tin cậy, đo đúng thứ ta có.
>
> ⚠️ "WER" trong tiêu đề ban đầu = đo bằng 2 lần ASR; đã đổi phạm vi.

## Mục tiêu

1. Mỗi clip có 1 chỉ số tin cậy ghi lời (0–1 + đếm từ dưới ngưỡng) —
   không tốn thêm lượt GPU.
2. UI hiện chỉ số theo clip (badge) + dòng giải thích trong transcript.
   ⛔ Không đổi công thức credit.
3. Test xanh, gate L1/L2 xanh, UI kiểm thật trên production trước khi gộp.

## Phạm vi (chỉ tệp taoclipngan + locale + test)

| Tệp | Thay đổi | Trạng thái |
|---|---|---|
| `apps/taoclipngan/jobs.py` | caption giữ `words` (word+confidence); mỗi clip gắn `transcript_confidence` | ✅ 26/09 |
| `apps/taoclipngan/features.py` | `tin_cay_ghi_loi()` + `NGUONG_TU_YEUNGHI`; không có `words` ⇒ `None` | ✅ 26/09 |
| `apps/taoclipngan/templates/taoclipngan.html` | badge `tcn-tc` (cao/trung/thap) + tooltip + dòng giải thích; `<style>` scope riêng trong app | ✅ 26/09 |
| `locale/en/LC_MESSAGES/messages.po` | +7 msgid, nối cuối, LF, không BOM, 0 trùng | ✅ 26/09 |
| `tests/test_4903_tcn_tin_cay_ghi_loi.py` | 6 test unit, không đọc trạng thái máy | ✅ 26/09 |

## Các mục

1. `features.py`: `tin_cay_ghi_loi(caption_segments, total_words=None)` →
   `{"value","words","low_words","low_ratio"}`; rỗng/thiếu `words` ⇒ `None`. **XONG**
2. `jobs.py`: caption giữ `words` (word+confidence) từ `speech.json`;
   sau `clips_out` gắn `transcript_confidence` từng clip (gọi hàm trên). **XONG**
3. `templates/taoclipngan.html`: badge trong `figcaption` + dòng giải thích
   trong `<details>` transcript; `<style>` scope riêng (`.tcn-tc*`). **XONG**
4. `locale/en/.../messages.po`: thêm msgid mới nối cuối, giữ LF, không BOM;
   kiểm 0 msgid trùng. **XONG**
5. `tests/test_4903_tcn_tin_cay_ghi_loi.py`: case rỗng, case có words,
   từ không có confidence, clip dưới ngưỡng. **XONG**
6. UI thật: mở job taoclipngan có clip trên production, thấy badge +
   transcript đúng; không console error. **CHƯA** — cần Chrome thật CDP 9222
   (AGENTS §9.1): chủ dự án mở Chrome `--remote-debugging-port=9222`, đăng nhập
   test, tôi nối `--cdp` kiểm. Chưa deploy code mới ⇒ badge chỉ thấy sau khi
   job chạy lại trên bản mới.
7. Ruff + test taoclipngan + gate L1/L2 → commit (chọn lọc) + gộp main.
   **CHƯA** — chờ mục 6 theo hợp đồng §7 (đổi giao diện ⇒ kiểm trình duyệt
   trước khi gộp).

## Rủi ro

- `speech.json` bản cũ không có `words` ⇒ `tin_cay_ghi_loi` trả `None`, UI ẩn
  badge (đã cover test).
- Template: chỉ render khi `tc` tồn tại — không phá layout job chưa có dữ liệu.
- ⛔ Không đụng `server/static/ltt.css` (dùng chung); style trong template app.
- messages.po: append cuối, kiểm trùng msgid.

## Lệnh kiểm (đã chạy, kết quả thật)

```
python -m pytest tests/test_4903_tcn_tin_cay_ghi_loi.py -q            # 6 passed (26/09 00:44)
python -m pytest tests/test_4903_tcn_tin_cay_ghi_loi.py tests/test_4900_tcn_quality_gate.py tests/test_4901_tcn_cache_dir_override.py tests/test_4902_tcn_cancel_ffmpeg.py tests/test_123_taoclipngan_features.py tests/test_84_taoclipngan.py tests/test_122_taoclipngan_ui.py -q
                                                                        # 39 passed (26/09 00:47)
python -m ruff check apps/taoclipngan/features.py apps/taoclipngan/jobs.py tests/test_4903_tcn_tin_cay_ghi_loi.py
                                                                        # All checks passed
```

Chưa chạy: UI thật (cần Chrome CDP của chủ dự án), gate L1/L2 (sau mục 6).

## Không làm (ngoài phạm vi)

- Không thêm metric WER thật (không có corpus chuẩn VN).
- Không đổi công thức credit.
- Không đụng `platform_core/`, `server/`, `cutclipshort/` (0.4 chỉ nối ra UI).
