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
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: Phan tram CPU (mot loi) toi thieu de coi mot CAY la DANG LAM.
#:
#: 🔴 BAN DAU HANG SO NAY DO CPU TICH LUY, VA DO LA SAI — do 06/09: cong cu bao
#:    hai cay "DANG LAM" trong khi CPU toan may chi **4,6 %**. Mot tien trinh
#:    song lau tich du 5 giay CPU mot lan roi nam khong se **mai mai** trong
#:    nhu dang lam.
#:
#: ⛔ Hai cach do deu sai, moi cach mot chieu:
#:      `cpu_percent()` mot nhat  -> mau TUC THOI, khong phan biet "da chet"
#:                                   voi "dang cho I/O" (do 05/09: 0,0 %)
#:      CPU TICH LUY              -> khong phan biet "dang lam" voi "da lam
#:                                   xong tu lau"
#:
#: ⭐ Cau ta thuc su hoi la *"cay do co dang AN CPU khong"*, va cau ay chi tra
#:    loi duoc bang mot DELTA tren mot khoang thoi gian — khong phai bang mot
#:    con so tich luy, cung khong phai bang mot mau tuc thoi.
PHAN_TRAM_COI_LA_LAM = 8.0

#: Khoang lay hai mau de tinh delta. Du dai de qua mot nhip lap lich, du ngan
#: de khong ai ngai chay cong cu nay truoc moi lenh nang.
GIAY_LAY_MAU = 1.5


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
    ung_vien = []
    for p in psutil.process_iter(["pid", "name", "cwd"]):
        try:
            if p.info["pid"] in bo_qua:
                continue
            if (p.info["name"] or "").lower() not in ("python.exe", "python", "py.exe"):
                continue
            ten = _ten_cay(p.info["cwd"] or "")
            if not ten:
                continue
            ung_vien.append((ten, p, sum(p.cpu_times()[:2])))
        except psutil.Error:
            # Tien trinh chet giua chung / khong doc duoc `cwd` deu la chuyen
            # binh thuong khi quet ca may. Bat HEP de mot loi KHAC van noi ra.
            continue

    time.sleep(GIAY_LAY_MAU)

    ra: dict = {}
    for ten, p, cpu0 in ung_vien:
        muc = ra.setdefault(ten, {"so": 0, "cpu": 0.0, "tich_luy": 0.0,
                                  "la_cay_toi": ten == cay_toi})
        muc["so"] += 1
        try:
            cpu1 = sum(p.cpu_times()[:2])
        except psutil.Error:
            continue                    # chet giua hai mau -> khong tinh la lam
        muc["tich_luy"] += cpu1
        muc["cpu"] += (cpu1 - cpu0) / GIAY_LAY_MAU * 100.0
    return ra


def cay_khac_dang_ban(bang: dict | None = None) -> list[str]:
    """Ten cac cay KHAC dang that su lam viec (khong chi ton tai tien trinh)."""
    bang = quet() if bang is None else bang
    return sorted(t for t, m in bang.items()
                  if not m["la_cay_toi"] and m["cpu"] >= PHAN_TRAM_COI_LA_LAM)


def khoa_dang_giu() -> list[str]:
    """Ai dang giu khoa `cua_so_yen`. Rong neu khong ai giu.

    🔴 VI SAO HAM NAY NAM O DAY, TRONG `may_ban`.

       `may_ban` do **CPU theo tung cay**. `cua_so_yen` do **KHOA**. Hai thu
       do hai dai luong khac nhau, va do 06/09/2026 chung KHONG trung nhau:

           may_ban       ca hai cay `dang cho`, 3,1% va 2,1% CPU
           cua_so_yen    mot `pytest go tay` giu `cpu_nhieu` + `postgres_test`
                         da 3,6 phut

       Mot luot pytest dang o pha I/O (cho CSDL, thu don, pha tuan tu) doc ra
       **y het mot may ranh**. Toi bo qua `trang-thai` vi tuong `may_ban` da du,
       roi phong `gate.py` — va no xep hang 9,5 phut.

    ⇒ Cong cu tra loi CA HAI thi khong ai phai nho chay hai lenh. Do la co che,
      khong phai mot luat trong tai lieu.
    """
    try:
        from cua_so_yen import _mo_ta, dang_giu
    except ImportError:
        return []
    try:
        ds = dang_giu()
    except (OSError, ValueError):
        return []
    dong: list[str] = []
    for bg in ds:
        if bg.get("hong"):
            dong.append(f"[{bg.get('tai_nguyen', '?')}] TEP KHOA HONG")
            continue
        d = f"[{bg['tai_nguyen']}] {_mo_ta(bg)}"
        if bg.get("treo"):
            d += f"  (TREO: {bg['treo']} - luot sau tu doat)"
        dong.append(d)
    return dong


def dong_canh_bao() -> str:
    """Mot dong ASCII cho `gate.py` / `test_nhanh.py` in ra. Rong neu may ranh.

    ⭐ Tra ve CHUOI chu khong tu in: nguoi goi quyet dinh in o dau va co in
       khong. Mot cong cu tu in vao stdout cua tien trinh khac da lam vo pytest
       o kho nay mot lan roi.
    """
    ve = []
    bang = quet()
    khac = cay_khac_dang_ban(bang) if bang else []
    if khac:
        chi_tiet = ", ".join(f"{t} ({bang[t]['so']} tien trinh, "
                             f"{bang[t]['cpu']:.0f}% CPU)" for t in khac)
        ve.append(f"  [may ban] cay KHAC dang lam viec: {chi_tiet}")
    # ⛔ Ve thu HAI, va no doc lap voi ve tren: mot luot giu khoa ma it CPU
    #    khong hien o `cay_khac_dang_ban`. Xem `khoa_dang_giu`.
    for d in khoa_dang_giu():
        ve.append(f"  [khoa]    {d}")
    return "\n".join(ve)


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
            lam = "DANG LAM" if m["cpu"] >= PHAN_TRAM_COI_LA_LAM else "dang cho"
            print(f"  {dau} {ten:<28} {m['so']:>2} tien trinh  "
                  f"{m['cpu']:>6.1f}% CPU  ({m['tich_luy']:>5.0f}s tich luy)  {lam}")
        print("    (* = cay nay)")

    khoa = khoa_dang_giu()
    if khoa and not a.im:
        print("  --- khoa cua_so_yen ---")
        for d in khoa:
            print(f"    {d}")

    khac = cay_khac_dang_ban(bang)
    # ⛔ Ma thoat phai tinh CA HAI. Truoc 06/09 no chi tinh CPU, nen no tra
    #    0 ("ranh") trong khi mot luot nang dang giu khoa — xem
    #    `khoa_dang_giu` va `docs/QUY_TAC_CHAY_LENH_NANG.md`.
    if khac or khoa:
        if not a.im:
            if khac:
                print(f"  => CAY KHAC DANG BAN: {', '.join(khac)}")
            if khoa:
                print("  => CO KHOA DANG BI GIU: dung phong lenh nang.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
