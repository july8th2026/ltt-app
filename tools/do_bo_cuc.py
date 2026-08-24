"""
do_bo_cuc.py — đo KHÁCH QUAN mức giữ bố cục giữa ảnh gốc và ảnh đã sửa. (H37/G5)

    py tools/do_bo_cuc.py --goc <anh_goc> --ra <anh_ket_qua> [--nen <thu_muc_anh_la>]

⭐ VÌ SAO CÓ TỆP NÀY: chế độ `structure` (giữ bố cục/tư thế) **không có đường đi
   chính thức** — HiDream-O1 không hỗ trợ ControlNet (D-017). Cách duy nhất còn lại
   là dùng chế độ `edit` kèm lời nhắc "giữ nguyên bố cục". Câu hỏi "nó có giữ được
   không" mà chỉ hỏi cảm nhận thì mỗi ngày trả lời một kiểu.

⛔ NHƯNG CON SỐ TƯƠNG QUAN MỘT MÌNH LÀ VÔ NGHĨA. "Tương quan cạnh 0,42" cao hay
   thấp? Không ai biết, kể cả người viết ra nó. Nên tệp này **luôn đo kèm sàn**:
   tương quan giữa ảnh gốc và những ảnh **không liên quan gì**. Chỉ khi kết quả
   vượt hẳn sàn đó thì mới nói được là "có giữ bố cục".

   Đây đúng cùng một nguyên tắc với **cặp bẫy** của `cham_mu.py`: đo mức nhiễu
   trước, rồi mới đọc tín hiệu.

⛔ VÀ NÓ KHÔNG THAY THẾ MẮT NGƯỜI. Thước này chỉ trả lời **một** câu: "bố cục có
   giữ nguyên không". Nó **không** biết ảnh có đẹp không, có đúng yêu cầu không,
   chữ có sai chính tả không. Quyết định cuối vẫn là so mù của chủ dự án (D-010).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from PIL import Image

#: Cạnh dài khi thu nhỏ để so. Đủ nhỏ để bỏ qua chi tiết bề mặt (thứ mà lệnh sửa
#: ĐƯỢC PHÉP đổi: chất liệu, phong cách, màu), đủ lớn để giữ bố cục lớn.
CANH_SO = 384

DUOI_ANH = (".png", ".jpg", ".jpeg", ".webp")


def _xam(duong: Path, canh: int = CANH_SO) -> np.ndarray:
    """Nạp ảnh, ép về khung vuông `canh`×`canh`, thang xám, [0,1].

    ⛔ Ép về khung VUÔNG chứ không giữ tỉ lệ: nếu ảnh kết quả khác tỉ lệ với ảnh
    gốc thì giữ tỉ lệ sẽ làm hai lưới lệch nhau và tương quan tụt vì lý do hình
    học, không phải vì bố cục đổi. Ép vuông thì cả hai chịu cùng một biến dạng.
    """
    im = Image.open(duong).convert("L").resize((canh, canh), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def _canh(a: np.ndarray) -> np.ndarray:
    """Biên độ gradient (Sobel). So CẠNH chứ không so điểm ảnh: đổi phong cách hay
    đổi màu làm điểm ảnh khác hẳn trong khi bố cục y nguyên — mà bố cục mới là thứ
    ta hỏi."""
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    gx = _chap(a, kx)
    gy = _chap(a, kx.T)
    return np.sqrt(gx * gx + gy * gy)


def _chap(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Chập 3×3, viền lặp. Tự viết để không kéo scipy vào chỉ vì một phép chập."""
    p = np.pad(a, 1, mode="edge")
    ra = np.zeros_like(a)
    for i in range(3):
        for j in range(3):
            ra += k[i, j] * p[i:i + a.shape[0], j:j + a.shape[1]]
    return ra


def tuong_quan(x: np.ndarray, y: np.ndarray) -> float:
    """Tương quan Pearson của hai bản đồ cạnh, kẹp về [-1, 1]."""
    a, b = x.ravel(), y.ravel()
    a = a - a.mean()
    b = b - b.mean()
    mau = float(np.sqrt((a * a).sum() * (b * b).sum()))
    if mau == 0.0:                       # ảnh phẳng lì — không có cạnh nào để so
        return 0.0
    return float(np.clip(float((a * b).sum()) / mau, -1.0, 1.0))


def do_mot(goc: Path, ra: Path) -> float:
    return tuong_quan(_canh(_xam(goc)), _canh(_xam(ra)))


def do_san(goc: Path, anh_la: Sequence[Path]) -> list[float]:
    """Sàn: ảnh gốc so với những ảnh KHÔNG liên quan. Đây là mức tương quan đến từ
    "hai ảnh đều là ảnh" chứ không từ "cùng bố cục"."""
    cg = _canh(_xam(goc))
    return [tuong_quan(cg, _canh(_xam(p))) for p in anh_la]


def phan_dinh(diem: float, san: Sequence[float]) -> tuple[str, dict]:
    """So điểm với sàn. Ngưỡng là **max của sàn**, không phải trung bình.

    Dùng max vì câu hỏi là "có chắc chắn hơn ngẫu nhiên không". Vượt trung bình
    của sàn thì vẫn có thể chỉ là một ảnh lạ xui xẻo giống bố cục — vượt cả cái
    cao nhất trong sàn mới đáng nói.
    """
    if not san:
        return "khong co san de so", {"canh_bao": "chua do san - con so mot minh vo nghia"}
    cao = max(san)
    tb = statistics.mean(san)
    if diem > cao:
        ket = "co giu bo cuc"
    elif diem > tb:
        ket = "khong ket luan duoc"
    else:
        ket = "KHONG giu bo cuc"
    return ket, {"san_trung_binh": round(tb, 3), "san_cao_nhat": round(cao, 3),
                 "so_anh_san": len(san)}


def _anh_trong(d: Path) -> list[Path]:
    return [p for p in sorted(d.iterdir())
            if p.is_file() and p.suffix.lower() in DUOI_ANH]


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Do muc giu bo cuc (H37/G5)")
    ap.add_argument("--goc", required=True, type=Path, help="anh tham chieu")
    ap.add_argument("--ra", required=True, type=Path, help="anh ket qua, hoac thu muc")
    ap.add_argument("--nen", type=Path, default=None,
                    help="thu muc anh KHONG lien quan, de do san nhieu")
    a = ap.parse_args(argv)

    anh_la = [p for p in _anh_trong(a.nen)] if a.nen else []
    san = do_san(a.goc, anh_la)

    muc = _anh_trong(a.ra) if a.ra.is_dir() else [a.ra]
    ket = []
    for p in muc:
        d = do_mot(a.goc, p)
        kl, chi_tiet = phan_dinh(d, san)
        ket.append({"anh": p.name, "tuong_quan_canh": round(d, 3),
                    "ket_luan": kl, **chi_tiet})
    print(json.dumps({"goc": a.goc.name, "ket": ket}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
