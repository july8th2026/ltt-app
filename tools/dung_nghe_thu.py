r"""Dung TAT CA tep nghe thu cua giong mau trong MOT luot (U-09).

## Van de

`nghe_thu.bao_tri()` dung dan **3 giong moi gio** (`MOI_LUOT_TOI_DA = 3`), va
tran ay dung cho dung ly do cua no: vong bao tri chay **cung tien trinh** voi
worker job, nen dung ca hai muoi tep trong mot luot la giu GPU khoang mot phut
lien, trong khi job cua khach cho ma khong ai biet vi sao.

Nhung he qua la: sau moi lan `PHIEN_BAN` doi (doi cau doc thu, hoac doi
`PHIEN_BAN_THAM_SO` cua sidecar), **bay tieng dong ho** troi qua truoc khi giong
cuoi cung co tep nghe thu. Trong bay tieng do, mot phan kho giong khong nghe thu
duoc — va cach duy nhat de biet mot giong nghe ra sao la tra tien tao mot luot.

## Loi giai

Tach **luc nao dung** khoi **dung bao nhieu**. Tran 3/gio la dung cho vong bao
tri; no khong dung cho mot luot phat hanh, vi luc phat hanh khong co job nao cua
khach dang cho.

⇒ Cong cu nay chay **ngoai** vong bao tri, mot lan, sau khi trien khai.

## ⛔ No TU TU CHOI khi may dang ban

Cung rao chan voi `tools/do_ho_so_giong.py`, va cung ly do: mot luot dung 20 tep
la 20 luot GPU, va chong no len mot luot gate dang chay lam gate ra ket qua
**sai** chu khong chi cham (do duoc: `assert 1 == 6` la dau hieu tai).

[!] Hoi `Win32_Process`, KHONG hoi `ps` cua Git Bash — `ps` khong thay tien
    trinh Windows va da mot lan bao "da xong" cho mot tien trinh con song.

## Dung

    python tools\dung_nghe_thu.py                  # dung phan con thieu
    python tools\dung_nghe_thu.py --tat-ca         # dung lai het, ke ca da co
    python tools\dung_nghe_thu.py --bo-qua-kiem-may
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time


def _may_ban() -> list:
    """PID cua tien trinh gate/test dang chay. Rong = may ranh."""
    ma = ("Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
          "Where-Object { $_.CommandLine -like '*gate.py*' -or "
          "$_.CommandLine -like '*test_nhanh*' -or "
          "$_.CommandLine -like '*pytest*' } | "
          "ForEach-Object { $_.ProcessId }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ma],
                           capture_output=True, text=True, timeout=60)
        return [d.strip() for d in r.stdout.splitlines() if d.strip()]
    except Exception as e:  # noqa: BLE001 - hoi may la viec phu, khong duoc nem
        # [!] NOI RA. Im lang bien mot loi moi truong thanh mot "may dang ban"
        #     khong giai thich duoc, va nguoi dung se di tim mot tien trinh
        #     khong ton tai.
        print(f"  [kiem may] khong hoi duoc Win32_Process: "
              f"{type(e).__name__}: {e}")
        return ["(khong hoi duoc)"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tat-ca", action="store_true",
                    help="dung lai ca nhung giong DA co tep")
    ap.add_argument("--bo-qua-kiem-may", action="store_true",
                    help="chay du may dang ban (duong thoat CO Y THUC)")
    a = ap.parse_args(argv)

    if not a.bo_qua_kiem_may:
        ban = _may_ban()
        if ban:
            print(f"⛔ May dang ban (pid {', '.join(ban)}). Cho, hoac "
                  f"--bo-qua-kiem-may neu ban chac.")
            return 2

    from apps.ltt_voice import giong_mau, nghe_thu, sidecar_client

    if not sidecar_client.san_sang():
        print("⛔ Cong giong chua cau hinh (LTT_VOICE_SIDECAR_*). Khong dung "
              "duoc gi.")
        return 2

    print(f"phien ban nghe thu : {nghe_thu.PHIEN_BAN}")
    print(f"tham so sidecar    : {nghe_thu._phien_ban_tham_so()}")

    can = (list(giong_mau.DANH_SACH) if a.tat_ca else nghe_thu.con_thieu_mau())
    if not can:
        print("Khong con giong nao thieu tep nghe thu.")
        return 0

    print(f"se dung {len(can)}/{len(giong_mau.DANH_SACH)} giong\n")
    xong, hong = 0, []
    for i, g in enumerate(can, 1):
        t0 = time.time()
        try:
            nghe_thu.dung(nghe_thu.khoa_mau(g.ma), preset=g.ma)
            xong += 1
            print(f"  [{i}/{len(can)}] {g.ma}: OK ({time.time() - t0:.1f}s)")
        except Exception as e:  # noqa: BLE001 - mot giong hong khong duoc dung ca luot
            # [!] KHONG dung ca luot. Mot giong hong (preset bi go khoi engine,
            #     mot loi mang) khong duoc phep lam 19 giong con lai khong co
            #     tep — do la bien mot su co nho thanh mot su co lon.
            hong.append((g.ma, f"{type(e).__name__}: {e}"))
            print(f"  [{i}/{len(can)}] {g.ma}: HONG - {type(e).__name__}: {e}")

    print(f"\nxong {xong}/{len(can)}")
    if hong:
        print("hong:")
        for ma, loi in hong:
            print(f"  {ma}: {loi}")
    # [!] Ma thoat KHAC 0 khi co giong hong, de mot buoc trien khai goi cong cu
    #     nay biet ma dung lai. In ra roi thoat 0 la cach mot loi di qua mot
    #     duong ray tu dong ma khong ai thay.
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
