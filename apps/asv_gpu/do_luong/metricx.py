"""QE dich KHONG tham chieu bang MetricX-24-Hybrid-Large (google-research/metricx).

    do_dich(cap, ngon_ngu_nguon="zh", ngon_ngu_dich="vi") -> {ma: diem}

## Thang diem — doc truoc khi dat nguong

- `diem` = loi MQM du doan cua cap (nguon, dich), trong `[0, 25]`,
  **THAP LA TOT**: 0 = khong loi; 25 = te nhat (vd. khong dich / sai hoan toan).
- Nguong de xuat `NGUONG_DO` (theo huong) va bang chung: `docs/auto_scan_video_final/L_DICH.md`.
  Nguong la cua SAN PHAM (do tren bo cap co nhan cua ta), khong phai cua upstream.
- Model khong nhan ma ngon ngu; `ngon_ngu_*` chi de kiem hop dong va ghi vet.

Model + tokenizer ban GHIM, co sha256 (`_metricx/phien_ban.json`), nam o
`HF_HOME`. Thieu / sai checksum => `KhongKhaDung` (QC danh `khong_kha_dung`).
Tai lan dau: `_metricx/tai.py` (xem docstring cua no).
"""
from __future__ import annotations

from pathlib import Path

from apps.asv_gpu.do_luong import venv
from apps.asv_gpu.do_luong.venv import DoLuongLoi, KhongKhaDung  # noqa: F401  (tai xuat)

RUNNER = Path(__file__).resolve().parent / "_metricx" / "chay.py"

#: Thang diem: (thap nhat, cao nhat); thap la tot.
THANG_DIEM = (0.0, 25.0)
THAP_LA_TOT = True
#: Diem > NGUONG_DO[(nguon, dich)] => cap dich bi coi la hong. Thang diem LECH theo
#: huong (vi->en: ban tot trung binh 4,8; zh->vi: 2,4) nen nguong theo huong. Chon
#: de bao nham <= 2/24 ban tot tren bo co nhan (L_DICH.md §3) — NGUONG TAM, chot lai
#: khi co bo kiem tach rieng. Bat chac bo sot + khong dich; KHONG bat duoc lat nghia /
#: sai thuc the mot cach tin cay => lop phan xet LLM (qc_ai) van giu.
NGUONG_DO = {("zh", "vi"): 6.0, ("zh", "en"): 6.0, ("en", "vi"): 6.0, ("vi", "en"): 9.0}

#: Cap nguon -> dich MetricX duoc do tren bo co nhan cua ta.
CAP_DA_DO = frozenset(NGUONG_DO)

#: So cap moi lo tren GPU (bf16, doan phu de ngan): dinh ~2,4 GB o lo 16.
LO_MAC_DINH = 16


def do_dich(cap: list[dict], *, ngon_ngu_nguon: str, ngon_ngu_dich: str,
            gpu_uuid: str = "", is_cancelled=None, thiet_bi: str = "auto",
            lo: int = LO_MAC_DINH, timeout_s: int = 1800) -> dict[str, float]:
    """Cham tung cap `{ma, nguon, dich}`. Tra ve `{ma: diem}` (0..25, thap la tot)."""
    if (ngon_ngu_nguon, ngon_ngu_dich) not in CAP_DA_DO:
        raise KhongKhaDung(
            f"MetricX chua duoc do cho {ngon_ngu_nguon}->{ngon_ngu_dich}")
    if not cap:
        return {}
    ma = [str(c["ma"]) for c in cap]
    if len(set(ma)) != len(ma):
        raise ValueError("ma trung trong cap")
    dau_vao = {
        "cap": [{"ma": str(c["ma"]), "nguon": str(c.get("nguon") or ""),
                 "dich": str(c.get("dich") or "")} for c in cap],
        "thiet_bi": thiet_bi, "lo": int(lo),
    }
    ra = venv.chay(RUNNER, dau_vao, timeout_s=timeout_s, gpu_uuid=gpu_uuid,
                   is_cancelled=is_cancelled)
    diem = ra.get("diem") or {}
    thieu = set(ma) - set(diem)
    if thieu:
        raise DoLuongLoi(f"runner thieu diem cho {len(thieu)} cap")
    return {m: float(diem[m]) for m in ma}


def dat(diem: float, *, ngon_ngu_nguon: str, ngon_ngu_dich: str) -> bool:
    """True khi cap dich qua nguong san pham cua huong do (diem <= nguong)."""
    return diem <= NGUONG_DO[(ngon_ngu_nguon, ngon_ngu_dich)]
