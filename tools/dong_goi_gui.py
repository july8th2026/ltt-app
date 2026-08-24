"""dong_goi_gui.py - dong bo tai san tinh cho GUI cua `cam_cli`. (C15-GUI / U1)

    python tools\\dong_goi_gui.py          # dong bo
    python tools\\dong_goi_gui.py --kiem   # chi kiem, khong ghi (dung trong gate)

* VI SAO CAN MOT SCRIPT CHO MOT LENH COPY.

  GUI phai trong DUNG NHU nen tang, va nen tang da co mot he thiet ke that:
  `server/static/ltt.css` - 583 dong, 24 bien token. GUI chay trong WebView2 nen
  no DUNG LAI DUOC nguyen ban, khong phai ve lai.

  Nhung cua so GUI khong phuc vu tu `server/static/`: khi da dong goi thanh
  installer thi khong co may chu nao ca. Nen phai co MOT BAN SAO nam canh GUI.

! VA MOT BAN SAO CHEP TAY LA MOT BAN SAO SE TROI.

  Khong co gi bat `tools/gui/ltt.css` phai theo `server/static/ltt.css`. Lan dau
  ai do doi mau thuong hieu hay doi mot bien token, GUI van dung ban cu - va no
  hong theo kieu kho chiu nhat: cong cu trong GAN GIONG nen tang. Khong ai bao
  loi, khong ai mo phieu; no chi hoi sai.

  Cung ho voi bai hoc cache-bust o quy tac 6 cua CLAUDE.md: mot ban sao tinh ma
  khong co gi nhac no cap nhat thi no se khong cap nhat.

=> `--kiem` chay trong gate. Sua `ltt.css` ma quen dong bo la GATE DO, ngay lap
   tuc, o dung phien da sua.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

GOC = pathlib.Path(__file__).resolve().parents[1]

#: (nguon, dich). Them tai san moi thi them mot dong o day - test se tu chot no.
TAI_SAN = (
    ("server/static/ltt.css", "tools/gui/ltt.css"),
)


def _bam(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def dong_bo(kiem_thoi: bool = False) -> int:
    lech = []
    for nguon_ten, dich_ten in TAI_SAN:
        nguon = GOC / nguon_ten
        dich = GOC / dich_ten
        if not nguon.exists():
            print(f"[LOI] khong thay nguon {nguon_ten}")
            return 1

        bam_nguon = _bam(nguon)
        bam_dich = _bam(dich) if dich.exists() else "(chua co)"

        if bam_nguon == bam_dich:
            print(f"[OK]  {dich_ten}  {bam_nguon}")
            continue

        if kiem_thoi:
            lech.append((dich_ten, bam_nguon, bam_dich))
            print(f"[LECH] {dich_ten}\n       nguon={bam_nguon}  ban sao={bam_dich}")
            continue

        dich.parent.mkdir(parents=True, exist_ok=True)
        # Chep NGUYEN BYTE. Khong doc-ra-ghi-lai theo van ban: lam vay la doi ky
        # tu xuong dong tren Windows, va hai ban se KHONG BAO GIO khop bam nua -
        # tuc chot nay se do vinh vien vi mot ly do khong lien quan gi toi CSS.
        dich.write_bytes(nguon.read_bytes())
        print(f"[GHI] {dich_ten}  {bam_nguon}")

    if lech:
        print("\nBan sao tinh da TROI khoi ban goc.")
        print("Chay:  python tools\\dong_goi_gui.py")
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dong bo tai san tinh cho GUI cam_cli")
    ap.add_argument("--kiem", action="store_true",
                    help="chi kiem, khong ghi (dung trong gate)")
    a = ap.parse_args(argv)
    return dong_bo(kiem_thoi=a.kiem)


if __name__ == "__main__":
    sys.exit(main())
