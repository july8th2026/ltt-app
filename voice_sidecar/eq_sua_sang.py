r"""
eq_sua_sang.py — EQ sửa độ sáng cho bản sinh ra. (Kế thừa từ hệ cũ.)

## Bài toán, bằng số

Baseline K4 đo trên 8 giọng × 3 câu: bản sinh ra **tối hơn clip tham chiếu
3,65 dB** trên 4 kHz, vắt-95% tụt 25%. Đó là chữ ký của một codec neural, và nó
là **khoảng cách duy nhất có ý nghĩa** giữa VieNeu và F5 trong phép so K0 — F5
thắng trục `lech_sang` 30–10.

⛔ Không phải do bộ khử nhiễu tham chiếu: đã đo riêng, nó chỉ lấy đi
   **−0,095 dB** (`tools/do_gia_cua_khu_nhieu.py`). Giả thuyết ấy bị bác, và
   nhờ vậy ta biết chắc độ tối đến từ đường sinh chứ không từ mốc so.

## Hệ cũ đã gặp và đã giải đúng bài này

`D:\Voiceclone_TTS/src/inference/audio_postprocess.py::_apply_clarity_eq_xtts`,
ghi ngày 2026-04-19. Docstring của nó:

    "3-band restoration EQ to recover XTTS vocoder high-frequency loss.
     Measured delta vs ref (17 speakers):
       - air (8-16kHz):    -3.7 dB
       - presence (2-5kHz): -1.0 dB
       - bass (60-250Hz):   +0.6 dB"

⭐ **-3,7 dB.** Ta đo -3,65 dB. Hai vocoder khác hẳn nhau (XTTS vs MOSS-Nano),
   hai phép đo độc lập, cách nhau bốn tháng — cùng một cỡ khuyết tật. Đó không
   phải trùng hợp: mọi codec neural đều đánh đổi dải cao trước tiên, vì tai
   người ít nhạy ở đó nên hàm mất mát cũng ít phạt ở đó.

⭐ Và họ làm một việc ta chưa làm: **EQ theo TỪNG GIỌNG**. `voice_profiles.yaml`
   có `clarity_eq_gain_hi_db: 4,93` cho giọng này và `1,08` cho giọng kia. Vì
   độ hụt phụ thuộc chất giọng và chất thu, không phải một hằng số.

## Cái gì mang sang, cái gì không

  ✅ **Ý tưởng**: đo lệch phổ so tham chiếu → sửa bằng EQ khôi phục.
  ✅ **Kỷ luật**: mọi mức nâng **kẹp ở ±4 dB**. Nâng nhiều hơn thì tiếng bắt đầu
     nghe chói và giả, và nó khuếch đại luôn nhiễu codec ở đúng dải ấy.
  ✅ **Toán**: biquad theo *RBJ audio EQ cookbook* — công thức chuẩn công khai,
     không phải của riêng hệ nào.
  ⛔ **KHÔNG mang các con số** `+2.0 @ 8000`, `+1.0 @ 3000`, `-0.5 @ 350`.
     Chúng hiệu chuẩn cho **XTTS**, trên dữ liệu của hệ ấy. Số của ta phải đo
     trên chính đường sinh của ta — cùng luật đã áp cho K1 (ngưỡng 0,92) và
     K3 (sàn nhiễu n=24).

⚠️ Và một điều hệ cũ không nói ra mà ta phải tự canh: EQ này **nâng cả nhiễu**
   trong dải nó nâng. Nên nó chỉ được bật sau khi đo được rằng nó **tăng**
   DNSMOS chứ không chỉ tăng `db_dai_cao` — một con số đẹp lên trong khi tiếng
   xấu đi là kết quả tệ nhất có thể.
"""
from __future__ import annotations

import math

import numpy as np

#: Trần tuyệt đối cho mọi mức nâng, dB. Kế thừa nguyên từ hệ cũ.
#:
#: ⛔ Đây là chốt AN TOÀN, không phải tham số để chỉnh. Vượt nó thì tiếng nghe
#:    chói và giả, và nhiễu của codec trong dải ấy lên theo cùng một lượng.
TRAN_DB = 4.0


def _chuan_hoa(b, a):
    b = np.asarray(b, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    return b / a[0], a / a[0]


def ke_cao(sr: int, f0: float, gain_db: float, S: float = 1.0):
    """Kệ cao (high shelf) — RBJ audio EQ cookbook.

    Nâng/hạ mọi tần số TRÊN `f0`. Đây là hình dạng đúng cho việc khôi phục dải
    cao đã mất: khuyết tật của codec là một độ dốc, không phải một cái bướu.
    """
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * f0 / sr
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / 2 * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    tp = 2 * math.sqrt(A) * alpha
    b = [A * ((A + 1) + (A - 1) * cw + tp),
         -2 * A * ((A - 1) + (A + 1) * cw),
         A * ((A + 1) + (A - 1) * cw - tp)]
    a = [(A + 1) - (A - 1) * cw + tp,
         2 * ((A - 1) - (A + 1) * cw),
         (A + 1) - (A - 1) * cw - tp]
    return _chuan_hoa(b, a)


def buou(sr: int, f0: float, gain_db: float, Q: float = 1.0):
    """Bướu (peaking) — RBJ audio EQ cookbook. Nâng/hạ quanh `f0`."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * f0 / sr
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * Q)
    b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
    a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    return _chuan_hoa(b, a)


def ap(wav, sr: int, *, ke_cao_db: float = 0.0, ke_cao_hz: float = 4000.0,
       buou_db: float = 0.0, buou_hz: float = 3000.0, buou_q: float = 1.0):
    """Áp EQ. Mọi mức nâng bị KẸP ở `±TRAN_DB` trước khi dùng.

    ⛔ Kẹp ở đây, không ở nơi gọi. Một cái chốt an toàn đặt ở nơi gọi là một
       cái chốt mà nơi gọi thứ hai sẽ quên.
    """
    from scipy.signal import lfilter

    x = np.asarray(wav, dtype=np.float64)
    kc = max(-TRAN_DB, min(TRAN_DB, float(ke_cao_db)))
    bu = max(-TRAN_DB, min(TRAN_DB, float(buou_db)))
    if abs(kc) > 1e-6:
        b, a = ke_cao(sr, ke_cao_hz, kc)
        x = lfilter(b, a, x)
    if abs(bu) > 1e-6:
        b, a = buou(sr, buou_hz, bu, buou_q)
        x = lfilter(b, a, x)

    # ⛔ EQ nâng thì đỉnh lên theo, và một bản vượt 0 dBFS là một bản VỠ TIẾNG.
    #    Hạ đều cả bản nếu cần — KHÔNG cắt ngọn, vì cắt ngọn là méo phi tuyến,
    #    đúng thứ `chot_toan_ven` của K1 sinh ra để bắt.
    dinh = float(np.abs(x).max()) if x.size else 0.0
    if dinh > 0.99:
        x = x * (0.99 / dinh)
    return np.asarray(x, dtype="float32")
