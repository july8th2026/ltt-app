"""_dsp_chung.py — phép DSP DÙNG CHUNG cho bộ đo giọng.

## Vì sao tệp này tồn tại

Hai phép nền tảng bị **chép nguyên văn** ra nhiều tệp đo, mỗi bản một chỗ sửa
độc lập:

    khung_rms   RMS theo khung — 4 bản (chon_doan, do_chat_luong, do_on_dinh,
                noi_dai). Thân hàm y hệt; chỉ khác **kích thước khung** — và
                kích thước khung là THAM SỐ, không phải phần thân.
    cosine      cosine hai vector — 3 bản (chon_doan, do_chat_luong,
                do_giu_giong_nhieu_luot). Cùng công thức.

⛔ ĐÂY KHÔNG PHẢI đổi phép đo. Nó gom **đúng một** bản thân hàm về một chỗ; mỗi
   tệp giữ lại một wrapper một dòng gọi vào đây, nên **mọi call site và mọi con
   số giữ nguyên**. Kích thước khung của từng tệp (chon_doan dùng 10 ms như
   `hop_size`; do_on_dinh/noi_dai/do_chat_luong dùng 20 ms) vẫn do chính tệp ấy
   truyền vào — gộp mà đổi số ấy sẽ đổi phép chọn đoạn, nên nó là tham số.

⚠️ `import numpy` nằm TRONG hàm, không ở đầu tệp: giữ đúng nếp của
   `do_chat_luong.py` (nạp numpy chỉ khi thật sự đo), để import module này không
   kéo theo numpy ở những đường không cần.
"""
from __future__ import annotations


def khung_rms(wav, sr: int, khung_ms: float):
    """RMS theo khung `khung_ms` mili-giây. Trả `(rms_theo_khung, so_mau_khung)`.

    Thân hàm gốc (giống hệt ở cả 4 bản chép): cắt cho chia hết khung, reshape,
    `sqrt(mean(x**2))` tính trên float64. Khung dư ở cuối bị bỏ.
    """
    import numpy as np

    n = max(1, int(sr * khung_ms / 1000.0))
    du = len(wav) % n
    x = wav[:len(wav) - du] if du else wav
    if len(x) == 0:
        return np.zeros(0, dtype=np.float64), n
    return np.sqrt((x.reshape(-1, n).astype(np.float64) ** 2).mean(axis=1)), n


def cosine(a, b) -> float:
    """Cosine hai vector. `0.0` khi một vector bằng 0 (tránh chia 0).

    `asarray(...).ravel()` để nhận cả list lẫn mảng nhiều chiều — bản
    `do_chat_luong` cũ bỏ bước này nhưng chỉ nhận embedding đã phẳng, nên thêm
    vào là mở rộng an toàn, không đổi kết quả cho đầu vào cũ.
    """
    import numpy as np

    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))
