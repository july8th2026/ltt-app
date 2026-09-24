"""Danh gia QE dich (MetricX / COMET-QE) tren bo cap co nhan — bang chung cua L_DICH.md.

    python tools/asv_danh_gia_qe_dich.py cap   <ra.json>              # xuat cap theo huong
    python tools/asv_danh_gia_qe_dich.py metricx <ra.json> [cuda|cpu] [lo]
    python tools/asv_danh_gia_qe_dich.py bao-cao <diem.json> <ten> <thap_la_tot 0|1>

`diem.json` = {"diem": {ma: float}, ...}. ma = "<huong>:<id>:<tot|hong>".
Nhan: tot = 0, hong = 1. AUC tinh theo chieu "diem xau hon => hong".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
BO = GOC / "docs" / "auto_scan_video_final" / "l_dich" / "bo_cap_co_nhan.json"
HUONG = (("zh", "vi"), ("zh", "en"), ("en", "vi"), ("vi", "en"))


def cap_theo_huong() -> dict[str, list[dict]]:
    muc = json.loads(BO.read_text(encoding="utf-8"))["muc"]
    ra: dict[str, list[dict]] = {}
    for nguon, dich in HUONG:
        h = f"{nguon}-{dich}"
        ds = []
        for m in muc:
            src = m[nguon]
            ds.append({"ma": f"{h}:{m['id']}:tot", "nguon": src, "dich": m[dich],
                       "loai": "tot"})
            xau = src if m["loai"] == "khong_dich" else m[f"{dich}_hong"]
            ds.append({"ma": f"{h}:{m['id']}:hong", "nguon": src, "dich": xau,
                       "loai": m["loai"]})
        ra[h] = ds
    return ra


def auc(tot: list[float], hong: list[float]) -> float:
    """P(diem 'xau' cua cap hong > cap tot); hoa tinh 0.5."""
    n = 0.0
    for b in hong:
        for g in tot:
            n += 1.0 if b > g else (0.5 if b == g else 0.0)
    return n / (len(tot) * len(hong))


def nguong_tot_nhat(tot: list[float], hong: list[float]) -> tuple[float, float]:
    ung = sorted(set(tot + hong))
    best = (0.0, ung[0])
    for i in range(len(ung)):
        t = ung[i] if i + 1 == len(ung) else (ung[i] + ung[i + 1]) / 2
        acc = (sum(g <= t for g in tot) + sum(b > t for b in hong)) / (len(tot) + len(hong))
        if acc > best[0]:
            best = (acc, t)
    return best


def bao_cao(diem: dict[str, float], thap_la_tot: bool, nguong: float | None = None) -> dict:
    s = (lambda x: x) if thap_la_tot else (lambda x: -x)  # quy ve "cao = xau"
    ra = {}
    tat_ca_tot, tat_ca_hong = [], []
    for h, ds in cap_theo_huong().items():
        tot = [s(diem[c["ma"]]) for c in ds if c["loai"] == "tot"]
        hong = [s(diem[c["ma"]]) for c in ds if c["loai"] != "tot"]
        tat_ca_tot += tot
        tat_ca_hong += hong
        acc, t = nguong_tot_nhat(tot, hong)
        muc = {"n": len(ds), "auc": round(auc(tot, hong), 3),
               "acc_nguong_rieng": round(acc, 3), "nguong_rieng": round(s(t), 3),
               "tot_tb": round(s(sum(tot) / len(tot)), 3),
               "hong_tb": round(s(sum(hong) / len(hong)), 3)}
        for loai in ("lat_nghia", "bo_sot", "sai_thuc_the", "khong_dich"):
            hl = [s(diem[c["ma"]]) for c in ds if c["loai"] == loai]
            muc[f"auc_{loai}"] = round(auc(tot, hl), 3)
        if nguong is not None:
            tn = s(nguong)
            muc["acc_nguong_chung"] = round(
                (sum(g <= tn for g in tot) + sum(b > tn for b in hong)) / len(ds), 3)
            muc["loi_bao_nham"] = sum(g > tn for g in tot)
            muc["bo_lot"] = sum(b <= tn for b in hong)
        ra[h] = muc
    acc, t = nguong_tot_nhat(tat_ca_tot, tat_ca_hong)
    ra["chung"] = {"auc": round(auc(tat_ca_tot, tat_ca_hong), 3),
                   "acc_nguong_chung_tot_nhat": round(acc, 3), "nguong": round(s(t), 3)}
    return ra


def main(argv: list[str]) -> int:
    lenh = argv[1]
    if lenh == "cap":
        Path(argv[2]).write_text(json.dumps(cap_theo_huong(), ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        return 0
    if lenh == "metricx":
        from apps.asv_gpu.do_luong import metricx, venv
        tat_ca = [c for ds in cap_theo_huong().values() for c in ds]
        thiet_bi = argv[3] if len(argv) > 3 else "cuda"
        lo = int(argv[4]) if len(argv) > 4 else 16
        if len(argv) > 5:  # do do tre tren tap con (vd. CPU)
            tat_ca = tat_ca[:int(argv[5])]
        kq = venv.chay(metricx.RUNNER, {"cap": tat_ca, "thiet_bi": thiet_bi, "lo": lo})
        Path(argv[2]).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(kq["thong_tin"], ensure_ascii=False))
        return 0
    if lenh == "bao-cao":
        diem = json.loads(Path(argv[2]).read_text(encoding="utf-8"))["diem"]
        nguong = float(argv[5]) if len(argv) > 5 else None
        print(argv[3], json.dumps(bao_cao(diem, argv[4] == "1", nguong), ensure_ascii=False,
                                  indent=1))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
