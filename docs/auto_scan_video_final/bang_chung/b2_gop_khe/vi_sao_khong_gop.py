"""B2 — điều kiện NÀO chặn phép gộp? Đếm lý do, ⛔ không đoán.

v3 cho **0/31** khe được gộp, và một con số 0 không có đối chứng thì không phải
một phát hiện (`khong-doi-chung-thi-so-khong-khong-phai-phat-hien`). Tệp này hỏi
ĐÚNG một câu: ở mỗi cặp liền kề, điều kiện nào đóng cửa TRƯỚC?
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from apps.auto_scan_video import nan_thoi_luong as nt  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from do_ky_tu_moi_giay import TRAN_CO_GIAN, khe_cua_phim  # noqa: E402


def chay() -> dict:
    ra: dict = {"phim": {}}
    tong: dict[str, int] = {}
    for ma in ("v1", "v2", "v3"):
        khes = khe_cua_phim(ma)
        dem: dict[str, int] = {}
        for i in range(len(khes) - 1):
            a, b = khes[i], khes[i + 1]
            bac = nt.xep_bac(a, tran_tang_toc=TRAN_CO_GIAN)
            if bac <= nt.BacNan.BINH_THUONG:
                ly_do = "1_khe_da_VUA"
            elif not nt.con_tiep(a.chu):
                ly_do = "2_cau_DA_KET_THUC"
            elif b.bat - a.ket > nt.TRAN_KHE_GIUA_S:
                ly_do = "3_khe_giua_qua_RONG"
            elif len(f"{a.chu} {b.chu}") > nt.TRAN_KY_TU_GOP:
                ly_do = "4_vuot_TRAN_KY_TU"
            else:
                ly_do = "0_GOP_DUOC"
            dem[ly_do] = dem.get(ly_do, 0) + 1
            tong[ly_do] = tong.get(ly_do, 0) + 1
        ra["phim"][ma] = {"so_cap": len(khes) - 1, **dict(sorted(dem.items()))}
    ra["tong"] = {"so_cap": sum(v["so_cap"] for v in ra["phim"].values()),
                  **dict(sorted(tong.items()))}
    # Dấu cuối cùng của các đoạn KHÔNG còn tiếp — để thấy đó là dấu gì.
    dau: dict[str, int] = {}
    for ma in ("v1", "v2", "v3"):
        for k in khe_cua_phim(ma):
            s = k.chu.strip().rstrip(nt._DONG_GOI_CUOI).strip()
            if s and s[-1] in nt.DAU_KET_CAU:
                dau[s[-1]] = dau.get(s[-1], 0) + 1
    ra["dau_ket_cau_gap_phai"] = dict(sorted(dau.items(), key=lambda x: -x[1]))
    return ra


if __name__ == "__main__":
    print(json.dumps(chay(), ensure_ascii=False, indent=2))
