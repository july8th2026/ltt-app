r"""
dnsmos.py — chấm chất lượng cảm nhận của một đoạn tiếng, KHÔNG cần bản tham chiếu.

## Vì sao có tệp này

`chon_doan.py` cần một phép chấm "đoạn này nghe có sạch không" để loại đoạn xấu
trước khi so đại diện. Bản đầu dùng **SNR** — và SNR chỉ đo tương phản mức: một
bản thu méo đều, vọng phòng, hay có nhạc nền ổn định vẫn ra SNR đẹp.

Quy trình `Emilia` (trong `open-mmlab/Amphion`) chấm từng đoạn bằng **DNSMOS
P.835** rồi lọc theo ngưỡng. Đó là thực hành cộng đồng cho đúng việc này, nên ta
dùng đúng thứ đó thay vì một hàng thay tạm.

## Model

  · `sig_bak_ovr.onnx`, 1.157.965 byte, từ `microsoft/DNS-Challenge`
  · ghim theo commit `82f1b17e7776a43eee395d0f45bae8abb700ad00`
  · sha256 `269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd`
  · giấy phép **CC-BY-4.0** — ghi công ở đây là điều kiện dùng, không phải phép lịch sự

  Reddy, Gopal, Cutler. *DNSMOS P.835: A non-intrusive perceptual objective
  speech quality metric to evaluate noise suppressors.* ICASSP 2022.
  https://arxiv.org/pdf/2110.01763.pdf

## Ba điểm nó trả về (thang MOS 1–5)

  · **SIG**  — chất lượng của chính giọng nói
  · **BAK**  — mức độ sạch của nền
  · **OVRL** — tổng thể. Đây là điểm `chon_doan` dùng làm cổng.

⛔ TIỀN XỬ LÝ PHẢI GIỐNG HỆT `dnsmos_local.py` CỦA MICROSOFT, và ba chi tiết dưới
   đây là chỗ dễ làm sai mà không có gì báo — model vẫn chạy, vẫn trả một con số
   trông hợp lý, chỉ là con số đó không còn nghĩa gì:

   ① **16 kHz.** Cho vào 48 kHz thì model vẫn chạy: nó chỉ thấy một mảng số dài
      gấp ba, tức một giọng nghe như bị kéo chậm ba lần.
   ② **Đúng 9,01 giây.** Ngắn hơn thì bản gốc **lặp lại chính đoạn đó** cho đủ,
      không phải đệm im lặng — đệm im lặng sẽ kéo điểm BAK xuống oan.
   ③ **Hiệu chuẩn qua đa thức.** Đầu ra thô của model KHÔNG phải thang MOS; ba
      đa thức dưới đây đưa nó về thang đó, và bỏ bước này cho ra những con số
      nằm ngoài 1–5.
"""
from __future__ import annotations

import os
import threading

import numpy as np

#: Model chỉ nhận đúng tần số này. Xem chú thích ①.
TAN_SO = 16_000

#: Độ dài một cửa sổ chấm, giây. Con số của Microsoft, không phải của ta.
DAI_CUA_SO_S = 9.01

#: Hệ số hiệu chuẩn (bản KHÔNG cá nhân hoá) — chép nguyên từ `dnsmos_local.py`.
#: ⛔ Đừng làm tròn: chúng là hệ số hồi quy, không phải tham số chỉnh tay.
_HE_SO_SIG = (-0.08397278, 1.22083953, 0.0052439)
_HE_SO_BAK = (-0.13166888, 1.60915514, -0.39604546)
_HE_SO_OVR = (-0.06766283, 1.11546468, 0.04602535)

_KHOA = threading.Lock()
_PHIEN = None


def duong_model() -> str:
    """Nơi đặt model. Cùng gốc cache với model giọng (`HF_HOME`)."""
    goc = os.environ.get("LTT_DNSMOS_DIR") or os.path.join(
        os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"),
        "dnsmos")
    return os.path.join(goc, "sig_bak_ovr.onnx")


def co_san() -> bool:
    return os.path.isfile(duong_model())


def _phien():
    """Phiên ONNX, nạp một lần. `None` nếu không có model — KHÔNG ném."""
    global _PHIEN
    if _PHIEN is not None:
        return _PHIEN
    with _KHOA:
        if _PHIEN is None:
            duong = duong_model()
            if not os.path.isfile(duong):
                return None
            import onnxruntime as ort
            _PHIEN = ort.InferenceSession(duong,
                                          providers=["CPUExecutionProvider"])
    return _PHIEN


def _ve_16k(wav, sr: int):
    if sr == TAN_SO:
        return np.asarray(wav, dtype=np.float32)
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(int(sr), TAN_SO)
    return np.asarray(resample_poly(wav, TAN_SO // g, int(sr) // g),
                      dtype=np.float32)


def _da_thuc(he_so, x: float) -> float:
    a, b, c = he_so
    return float(a * x * x + b * x + c)


def cham(wav, sr: int) -> dict | None:
    """Chấm một đoạn. Trả `{"sig","bak","ovrl","so_cua_so"}` hoặc `None`.

    `None` nghĩa là **không chấm được** (thiếu model, thiếu scipy, đoạn rỗng) —
    và người gọi phải xử lý nó như "không biết", không phải như "điểm 0".
    """
    phien = _phien()
    if phien is None:
        return None
    try:
        x = _ve_16k(np.asarray(wav, dtype=np.float32).ravel(), int(sr))
    except Exception:                       # noqa: BLE001 - thieu scipy chang han
        return None
    if not len(x):
        return None

    can = int(DAI_CUA_SO_S * TAN_SO)
    # ⛔ LẶP chính đoạn đó cho đủ dài, KHÔNG đệm im lặng. Đây là thứ
    #    `dnsmos_local.py` làm, và đệm im lặng sẽ kéo BAK xuống oan.
    while len(x) < can:
        x = np.append(x, x)

    so_hop = int(np.floor(len(x) / TAN_SO) - DAI_CUA_SO_S) + 1
    sig, bak, ovr = [], [], []
    for i in range(max(1, so_hop)):
        doan = x[i * TAN_SO:i * TAN_SO + can]
        if len(doan) < can:
            continue
        vao = {"input_1": doan.astype(np.float32)[np.newaxis, :]}
        s, b, o = phien.run(None, vao)[0][0]
        sig.append(_da_thuc(_HE_SO_SIG, float(s)))
        bak.append(_da_thuc(_HE_SO_BAK, float(b)))
        ovr.append(_da_thuc(_HE_SO_OVR, float(o)))

    if not ovr:
        return None
    return {"sig": round(float(np.mean(sig)), 3),
            "bak": round(float(np.mean(bak)), 3),
            "ovrl": round(float(np.mean(ovr)), 3),
            "so_cua_so": len(ovr)}
