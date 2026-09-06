"""May co dang ban khong — dem theo `cwd`, khong dem theo ten lenh.

    python tools/may_ban.py            # in bang, exit 1 neu CAY KHAC dang ban
    python tools/may_ban.py --im       # khong in, chi lay ma thoat

⛔ VI SAO KHONG LOC THEO `cmdline`. Ba cach dem da duoc thu trong dem 05-06/09,
   va ca ba deu sai — moi cach mot kieu:

   | cach hong                                  | vi sao `cwd` khong dinh |
   |--------------------------------------------|-------------------------|
   | worker `execnet` khong mang tu khoa -> THIEU| khong can tu khoa       |
   | `bash -c "<ca cau lenh>"`         -> THUA   | chi dem `python.exe`    |
   | MO COI mat goc -> roi khoi cay con          | khong can mot goc       |

   Do cung mot thoi diem: loc van ban **3** · them `execnet` **3** · gom theo
   `cwd` **9**. Sau tien trinh vo hinh, moi cai 200-334 giay CPU. `psutil` doc
   duoc `cwd` cua 27/27 tien trinh.

🔴 Va cai hong nguy nhat la no hong **im lang theo huong de chiu**: mot bo dem
   bo sot hang xom se luon bao "toi chay mot minh" — tuc luon tra ve dung ket
   luan nguoi bam muon nghe.

⭐ Ly do sau xa hon ca ba dong tren: `cwd` tra loi dung cau ta THAT SU hoi —
   *"cay nao dang ban"* — chu khong phai *"tien trinh nao dang thi hanh tep gi"*.
   Ca ba phien dem 05-06/09 deu hoi cau thu hai roi doc ket qua nhu the no la
   cau thu nhat.

⚠️ Cong cu nay KHONG chan ai. No in ra roi tra ma thoat. Mot cong chan nguoi ta
   la mot cong nguoi ta se tat — va luc do ta mat ca phan canh bao.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: CPU tich luy toi thieu de coi mot tien trinh la DANG LAM chu khong phai
#: dang cho. Mot script do nhu chinh tep nay chi vai phan giay.
#:
#: ⛔ KHONG dung `cpu_percent()` mot nhat: no la mau TUC THOI va khong phan biet
#:    duoc "da chet" voi "dang cho I/O". Mot luot nghiem thu dang chay do ra
#:    0,0 % ngay 05/09, va suyt bi giet vi con so do.
GIAY_CPU_COI_LA_LAM = 5.0


def _ten_cay(cwd: str) -> str:
    """Ten ngan cua cay lam viec, du de nguoi doc biet ai dang ban."""
    thap = cwd.lower().rstrip(chr(92)).rstrip("/")
    if not thap.endswith("lttstudiosapp") and "worktrees" not in thap:
        return ""
    if thap.endswith("lttstudiosapp"):
        return "CAY CHINH"
    return cwd.replace(chr(92), "/").split("worktrees/")[-1].split("/")[0]


def quet() -> dict:
    """{ten cay: {"so": n, "cpu": giay, "la_cay_toi": bool}} — rong neu vang psutil.

    ⚠️ Vang `psutil` thi tra RONG, tuc "khong biet", chu khong phai "khong ai
       chay". Nguoi goi phai doc duoc khac biet do — xem `main`.
    """
    try:
        import psutil
    except ImportError:
        return {}

    # ⛔ LOAI TRU chinh minh VA toan bo chuoi cha.
    #
    # 🔴 Phien H44 do duoc 06/09: mot bo loc theo tien trinh khop vao **chinh
    #    cong cu do**, vi vo `bash -c` mang ca ma nguon minh truyen cho no. Ho
    #    dung bo loc ay de GIET, va `kill` di nguoc len cay cha cua chinh no —
    #    script thoat ma 15 (SIGTERM).
    #
    # ⚠️ `cwd` bac 3 KHONG cuu duoc ca nay: shell cua nguoi dang hoi cung co
    #    `cwd` dung bang cay ay. Dieu kien phai la thu tien trinh do **khong the
    #    tu thoa** — tuc loai `os.getpid()` va `parents()`.
    #
    # ⭐ Tep nay chi DEM, khong giet, nen hau qua chi la dem thua mot. Nhung mot
    #    bo dem tu dem minh la mot bo dem noi doi ve chinh cau hoi no tra loi,
    #    va ngay nao co nguoi them che do giet thi lo hong da nam san o day.
    try:
        _me = psutil.Process()
        bo_qua = {_me.pid} | {t.pid for t in _me.parents()}
    except psutil.Error:
        # ⛔ HEP, khong `except Exception`: banh coc `nuot loi lang le` cam THEM
        #    cho nuot lang le, va no dung. Neu `psutil.Process()` hong vi mot ly
        #    do KHONG phai psutil (vd thieu quyen o tang khac), thu ta muon la
        #    no NO chu khong phai am tham dem thua mot dong.
        bo_qua = {os.getpid()}

    cay_toi = _ten_cay(str(GOC))
    ra: dict = {}
    for p in psutil.process_iter(["pid", "name", "cwd"]):
        try:
            if p.info["pid"] in bo_qua:
                continue
            if (p.info["name"] or "").lower() not in ("python.exe", "python", "py.exe"):
                continue
            ten = _ten_cay(p.info["cwd"] or "")
            if not ten:
                continue
            muc = ra.setdefault(ten, {"so": 0, "cpu": 0.0, "la_cay_toi": ten == cay_toi})
            muc["so"] += 1
            muc["cpu"] += sum(p.cpu_times()[:2])
        except psutil.Error:
            # Tien trinh chet giua chung / khong doc duoc `cwd` deu la chuyen
            # binh thuong khi quet ca may. Bat HEP de mot loi KHAC van noi ra.
            continue
    return ra


def cay_khac_dang_ban(bang: dict | None = None) -> list[str]:
    """Ten cac cay KHAC dang that su lam viec (khong chi ton tai tien trinh)."""
    bang = quet() if bang is None else bang
    return sorted(t for t, m in bang.items()
                  if not m["la_cay_toi"] and m["cpu"] >= GIAY_CPU_COI_LA_LAM)


def dong_canh_bao() -> str:
    """Mot dong ASCII cho `gate.py` / `test_nhanh.py` in ra. Rong neu may ranh.

    ⭐ Tra ve CHUOI chu khong tu in: nguoi goi quyet dinh in o dau va co in
       khong. Mot cong cu tu in vao stdout cua tien trinh khac da lam vo pytest
       o kho nay mot lan roi.
    """
    bang = quet()
    if not bang:
        return ""
    khac = cay_khac_dang_ban(bang)
    if not khac:
        return ""
    chi_tiet = ", ".join(f"{t} ({bang[t]['so']} tien trinh, "
                         f"{bang[t]['cpu']:.0f}s CPU)" for t in khac)
    return f"  [may ban] cay KHAC dang lam viec: {chi_tiet}"


def main() -> int:
    p = argparse.ArgumentParser(description="May co cay nao khac dang ban khong.")
    p.add_argument("--im", action="store_true", help="khong in, chi lay ma thoat")
    a = p.parse_args()

    bang = quet()
    if not bang:
        if not a.im:
            print("  [may ban] KHONG BIET - thieu `psutil`, khong dem duoc.")
            print("            Day KHONG phai 'may ranh'. Hoi phien khac truoc khi bam.")
        return 0

    if not a.im:
        for ten in sorted(bang, key=lambda t: -bang[t]["cpu"]):
            m = bang[ten]
            dau = "*" if m["la_cay_toi"] else " "
            lam = "DANG LAM" if m["cpu"] >= GIAY_CPU_COI_LA_LAM else "dang cho"
            print(f"  {dau} {ten:<28} {m['so']:>2} tien trinh  "
                  f"{m['cpu']:>7.0f}s CPU  {lam}")
        print("    (* = cay nay)")

    khac = cay_khac_dang_ban(bang)
    if khac:
        if not a.im:
            print(f"  => CAY KHAC DANG BAN: {', '.join(khac)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
