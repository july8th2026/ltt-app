# Chất lượng giọng ở biên `speed` — bằng chứng đo (D01/PA2)

Ngày: 2026-09-13 · Harness: `tools/do_chat_luong_toc_do.py` · Preset: Adam · n=5 câu (3 VI, 2 EN)

## Câu hỏi

D01 nới `speed` ra **[0.5, 2.0]**. PA2 (chủ sản phẩm chọn) yêu cầu *"đo chất lượng
ở biên"*. `toc_do.py` ② cố ý đo cổng chất lượng **trước** kéo giãn (stretch lệch
F0), nên chưa ai đo bản **đã** kéo giãn. Tài liệu này đo đúng chỗ đó.

## Công cụ (cộng đồng, không tự chế — mục 20)

- **Naturalness**: DNSMOS P.835 (`voice_sidecar/dnsmos.py`) — model Microsoft
  `sig_bak_ovr.onnx`, xác minh byte-exact (1.157.965 byte) với `microsoft/DNS-Challenge`
  qua GitHub. Thang MOS 1–5.
- **Intelligibility**: ASR CER/WER (`do_chat_luong.do_de_hieu`, faster-whisper).

Đối chứng nội bộ: mỗi speed so với **speed 1.0 của CHÍNH câu đó** (khử khác biệt
giữa câu). Bằng chứng máy đọc: `test-results/voice-acceptance/chat_luong_toc_do_v2.jsonl`.

## Kết quả (median trên corpus)

| speed | DNSMOS OVRL | ΔOVRL vs 1.0 | ΔCER vs 1.0 |
|---|---|---|---|
| 0.5  | 2.626 | −0.069 | 0.0 |
| 0.75 | 2.828 | +0.060 | 0.0 |
| 1.0  | 2.762 | 0      | 0.0 |
| 1.25 | 2.656 | −0.081 | 0.0 |
| 1.5  | 2.591 | −0.221 | 0.0 |
| 2.0  | 1.830 | **−0.96** | 0.0 |

OVRL @2.0 từng câu: 1.73 / 1.77 / 1.83 / 1.97 / 2.11 — **nhất quán thấp cả 5 câu**,
không phải outlier.

## Kết luận

- **Intelligibility: an toàn toàn dải [0.5, 2.0]** — ΔCER≈0 mọi speed; ASR nghe
  đúng bất kể tốc độ.
- **Naturalness biên dưới 0.5–0.75: an toàn** — ΔOVRL trong ±0.07.
- **Naturalness 1.25–1.5: chấp nhận** — tụt nhẹ dần (−0.08 → −0.22).
- **Naturalness biên trên 2.0: tụt rõ ~0.96 MOS** (2.76 → 1.83), nhất quán.

## ⚠️ Giới hạn của phép đo (kỷ luật mục 24 + "chua_hieu_chuan")

- DNSMOS **tuyệt đối** chưa hiệu chuẩn trên TTS tiếng Việt — con số MOS thô không
  phải điểm người thật. Nhưng **delta** đáng tin về **chiều**, vì cùng một bản
  tổng hợp, chỉ khác atempo (đối chứng chặt).
- n=5, một preset (Adam). Là phép thăm dò biên, không phải bộ đo đầy đủ.
- Chưa nghe thử người (mục 26) — tai người là trọng tài cuối.

## 🐛 Lỗi đo đã bắt (đối chứng `audio_sha256`)

Lần đo đầu chạy trên nhánh **thiếu D01** (`TOC_DO_MIN=0.75/MAX=1.50` của main),
nên `hop_le` **kẹp** 0.5→0.75 và 2.0→1.5 — hai biên chưa từng được đo (sha256
trùng nhau tố cáo). Đã merge nhánh D01 vào và đo lại. Bài học: một phép đo tự
dựng phải có đối chứng đầu ra (ở đây là sha256), nếu không nó "xanh" mà sai.

## Quyết định (chủ sản phẩm, 2026-09-13)

**GIỮ [0.5, 2.0]**, ghi cảnh báo này để người tích hợp biết: `speed` càng gần
2.0 thì naturalness càng giảm (đo được ~1 MOS ở 2.0), trong khi độ dễ hiểu không
đổi. 1.5 là trần thực dụng nếu ưu tiên chất lượng. Không đổi code/hợp đồng.
