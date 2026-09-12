"""so_sanh_bench_llm.py — so BASELINE với CANDIDATE, và ra một phán quyết.

    python tools/so_sanh_bench_llm.py --nen baseline.json --moi bench_llm.json

Đọc hai tệp do `tools/bench_llm_hieu_nang.py` sinh ra, gom theo trung vị từng
loại lượt (`nguoi` / `am_ngan` / `am_dai`), rồi in bảng chênh lệch.

═══════════════════════════════════════════════════════════════════════════
 VÌ SAO CÔNG CỤ NÀY TỒN TẠI
═══════════════════════════════════════════════════════════════════════════

`bench_llm_hieu_nang.py` đã đo rất tốt: nó chụp `nvidia-smi` + `/health` quanh
mỗi lượt, dùng **trung vị** thay vì trung bình, và tách nguội khỏi ấm. Nhưng nó
sinh ra một **kết quả**, không sinh ra một **baseline**.

⇒ Hôm nay không ai trả lời được câu *"bản này có chậm hơn bản trước không"* mà
  không mở hai tệp JSON ra đọc bằng mắt. Và đọc bằng mắt là chỗ người ta vô
  tình chọn lượt đẹp — thứ mà chính `bench_llm_hieu_nang.py` cấm ở docstring.

⭐ KHUÔN KẾT XUẤT MƯỢN CỦA `vllm-project/guidellm` (đã đọc @ `f96d26b9`), nhưng
   **không** mượn công cụ: nó là công cụ Linux-trước, máy B là Windows, và thứ
   ta thiếu không phải một bộ đo mà là một **hợp đồng baseline**. Xem
   `docs/LLM_OPEN_SOURCE_RESEARCH.md` §O3.

═══════════════════════════════════════════════════════════════════════════
 SO SÁNH CHỈ CÓ NGHĨA KHI CÙNG MỘT CẤU HÌNH
═══════════════════════════════════════════════════════════════════════════

⛔ So một lượt đo ở `-c 204800` với một lượt đo ở `-c 131072` là so hai thứ khác
   nhau rồi gọi chênh lệch là "hồi quy". §22 của chương trình nói rõ: phải
   **apple-to-apple** — cùng model, cùng quant, cùng ngữ cảnh, cùng trạng thái
   GPU.

   Nên tệp này **từ chối** so khi `model` khác nhau, và **cảnh báo to** khi số
   tiến trình GPU lệch nhiều (một máy để bàn đang dùng thì tok/s không so được
   với một máy rảnh — đo 31/08: **23 tiến trình** trên card).

⚠️ NGƯỠNG LÀ ĐÈN VÀNG, KHÔNG PHẢI TOÀ ÁN. §22: *"Threshold không phải luật máy
   móc."* Một hồi quy có đánh đổi hợp lý thì ghi bằng chứng rồi đi tiếp; thứ
   không được phép là hồi quy **không giải thích được**.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

#: Ngưỡng cảnh báo, lấy đúng §22 của chương trình.
NGUONG = {
    "ttft_s": ("tang", 0.15),        # TTFT tăng > 15 %
    "decode_tok_s": ("giam", 0.10),  # decode giảm > 10 %
    "tong_s": ("tang", 0.15),        # end-to-end tăng > 15 %
}

LOAI = ("nguoi", "am_ngan", "am_dai")


def gom(d: dict) -> dict:
    """Trung vị từng loại lượt. Bỏ lượt lỗi — chúng không có số để so."""
    ra: dict = {}
    for loai in LOAI:
        ds = [x for x in d.get("luot", [])
              if x.get("loai") == loai and "loi" not in x]
        if not ds:
            continue
        ra[loai] = {
            "n": len(ds),
            "ttft_s": statistics.median(x["ttfb_s"] for x in ds),
            "tong_s": statistics.median(x["tong_s"] for x in ds),
            "decode_tok_s": statistics.median(x["decode_tok_s"] for x in ds),
        }
    return ra


def _vram(d: dict) -> "int | None":
    return ((d.get("ngu_canh_sau") or {}).get("smi") or {}).get("vram_mb")


def _tien_trinh(d: dict) -> "int | None":
    return (d.get("ngu_canh_sau") or {}).get("tien_trinh_gpu")


def kiem_cung_cau_hinh(nen: dict, moi: dict) -> list[str]:
    """Những lý do khiến hai lượt đo **không so được với nhau**."""
    loi = []
    if nen.get("model") and moi.get("model") and nen["model"] != moi["model"]:
        loi.append(f"model khac nhau: {nen['model']} vs {moi['model']}")
    return loi


def canh_bao_nhieu(nen: dict, moi: dict) -> list[str]:
    """Nhiễu ngoại cảnh — không chặn, nhưng phải nói ra."""
    ra = []
    a, b = _tien_trinh(nen), _tien_trinh(moi)
    if a is not None and b is not None and abs(a - b) >= 5:
        ra.append(f"so tien trinh GPU lech nhieu ({a} -> {b}) — tok/s "
                  f"khong so duoc apple-to-apple")
    return ra


def so(nen: dict, moi: dict) -> tuple[list[dict], bool]:
    """Trả `(dong, co_hoi_quy)`."""
    g_nen, g_moi = gom(nen), gom(moi)
    dong: list[dict] = []
    hoi_quy = False
    for loai in LOAI:
        if loai not in g_nen or loai not in g_moi:
            continue
        for chi_so, (chieu, nguong) in NGUONG.items():
            a = g_nen[loai][chi_so]
            b = g_moi[loai][chi_so]
            if not a:
                continue
            doi = (b - a) / a
            xau = doi > nguong if chieu == "tang" else -doi > nguong
            hoi_quy = hoi_quy or xau
            dong.append({"loai": loai, "chi_so": chi_so, "nen": a, "moi": b,
                         "doi": doi, "xau": xau})
    return dong, hoi_quy


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--nen", type=Path, required=True, help="baseline JSON")
    p.add_argument("--moi", type=Path, required=True, help="candidate JSON")
    a = p.parse_args()

    nen = json.loads(a.nen.read_text(encoding="utf-8"))
    moi = json.loads(a.moi.read_text(encoding="utf-8"))

    # ⛔ FAIL-CLOSED. Mot baseline rong khong duoc doc thanh "khong co hoi quy" —
    #    do la ket luan nguy hiem nhat co the rut ra tu viec khong biet gi.
    if not gom(nen):
        print("DUNG LAI: baseline khong co luot nao doc duoc.")
        print("  Mot baseline rong KHONG phai 'khong co hoi quy'. Chay")
        print("  tools/bench_llm_hieu_nang.py tren may B de tao baseline that.")
        return 2

    chan = kiem_cung_cau_hinh(nen, moi)
    if chan:
        print("DUNG LAI: hai luot do KHONG so duoc voi nhau:")
        for c in chan:
            print("  - " + c)
        return 2

    for c in canh_bao_nhieu(nen, moi):
        print("CANH BAO: " + c)

    dong, hoi_quy = so(nen, moi)
    if not dong:
        print("DUNG LAI: khong co loai luot nao co o CA HAI ben de so.")
        return 2

    print(f"{'loai':<9} {'chi so':<14} {'nen':>10} {'moi':>10} {'doi':>9}")
    print("-" * 58)
    for d in dong:
        dau = "  <-- XAU" if d["xau"] else ""
        print(f"{d['loai']:<9} {d['chi_so']:<14} {d['nen']:>10.2f} "
              f"{d['moi']:>10.2f} {d['doi'] * 100:>8.1f}%{dau}")

    va, vb = _vram(nen), _vram(moi)
    if va and vb:
        print(f"\nVRAM dinh: {va} -> {vb} MiB ({(vb - va) / va * 100:+.1f}%)")

    print("\n" + ("=" * 58))
    if hoi_quy:
        print("RESULT: HOI QUY - co it nhat mot chi so vuot nguong §22.")
        print("  Nguong la DEN VANG, khong phai toa an: neu co danh doi hop ly")
        print("  thi ghi bang chung vao docs/LLM_CHANGELOG_UPGRADE.md roi di tiep.")
        print("  Thu KHONG duoc phep la mot hoi quy khong giai thich duoc.")
        return 1
    print("RESULT: PASS - khong chi so nao vuot nguong §22.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
