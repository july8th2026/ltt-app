"""tai_may.py — may con cho mot luot do dat tien khong.

    python tools/tai_may.py            # phan quyet: RANH / BAN / QUA TAI
    python tools/tai_may.py --cho 900  # doi toi khi ranh, toi da 15 phut

## ⚠️ TEP NAY KHONG DANH CHO `gate.py`. Doc muc nay truoc khi noi no vao do.

Ban dau toi viet no de them mot "cua CPU" cho gate. Roi doc `gate.py` va thay
gate **da co hai lop bao ve**, va lop thu hai manh hon thu toi dinh xay:

    gate.py:110   ngan_sach_loi() = cpu_count() - 6   -> 14 luong, khong phai 20
    gate.py:591   UU_TIEN_THAP = BELOW_NORMAL_PRIORITY_CLASS tren MOI tien trinh con

Docstring cua chinh no da noi ro vi sao lop thu hai la lop that su chiu luc:

    "lop thu nhat (ngan sach loi) la mot phep TINH — con phep tinh thi co the
     sai. Uu tien thi khong: du gate co tinh nham bao nhieu, he dieu hanh van
     cho `LTTStudioWeb` chay truoc."

⇒ Them mot cua CPU truoc `bo test` la **canh mot cua da co nguoi canh**, va canh
  bang mot phep do te hon: mot nguong 80% doan tu ben ngoai, thay cho mot co che
  hang doi cua he dieu hanh.

## ⇒ Vay no dung o dau

Ba cho ma hai lop tren KHONG voi toi:

1. **`python -m pytest ...` chay thang.** Khong qua gate ⇒ khong ngan sach loi,
   khong uu tien thap. Day la duong toi dung nhieu nhat khi lam viec, va no la
   duong khong duoc bao ve nhat.

2. **RAM.** `BELOW_NORMAL_PRIORITY_CLASS` xep hang CPU, no khong nhuong bo nho.
   Muoi bon tien trinh Python cong voi mot model that (`LTT_TEST_NANG=1` nap
   demucs/whisper) khong bi uu tien thap cuu khoi mot lan het RAM.

3. **Truoc khi bat `LTT_TEST_NANG`.** Do la luc duy nhat mot phep kiem duoc phep
   nap trong so model that; do tai truoc la re, va la thoi diem no dang gia nhat.

## Va mot cho `cua_so_yen` khong the voi toi, do duoc

    11:38 03/09   cua_so_yen trang-thai  ->  RANH - khong tai nguyen nao bi giu
                  CPU                    ->  65%

Khong ai giu khoa, may van chay 65%. Nhung thu chiem cho do — bon dich vu
production, mot lan deploy, mot phien khac chay pytest thang, mot job cua khach —
khong di qua `cua_so_yen` va **khong the di qua no**. Do la mot lo hong THIET KE
cua khoa, khong phai mot loi: khoa la per-RUN, tai la per-MAY.

## ⛔ Vi sao no CHI DOC, va khong tu chan ai

Khong khoa gi, khong giet gi, khong sua hanh vi cua `gate.py`. In mot phan quyet
va tra ma thoat. Nguoi goi quyet dinh.

## Phan quyet dua tren RAM, khong dua tren CPU. Day la phan quan trong nhat.

  RANH     RAM trong > 8 GiB
  BAN      RAM trong 4-8 GiB
  QUA TAI  RAM trong < 4 GiB

CPU **duoc in ra nhung khong tham gia phan quyet**, va do la mot quyet dinh chu
khong phai mot thieu sot.

🔴 **Ban dau toi cho CPU vao phan quyet (RANH <50%, QUA TAI >80%). Phien
   `lttstudiosapp-73` pha no bang mot phep do.** Cung may, cung ngay, cung bon
   dich vu, khong luot gate nao chay:

       ~13:0x   CPU nen 27%   (≈ 5 loi)
       ~21:2x   CPU nen  3%

   Chenh gan **muoi lan**. Mot nguong co dinh kieu "tren 80% thi doi" se ngoan
   luc 21h va cam cua luc 13h, trong khi khong co gi ve phia gate thay doi ca.
   (`LOI_DE_DANH_CHO_MAY = 6` cua ho lay tu con so 27% — tu truong hop XAU, co
   y, vi mot phep do luc ranh la san cua truong hop tot.)

⭐ RAM trong on dinh hon nhieu, va no dung la manh ma hai lop bao ve cua gate
   khong che: `BELOW_NORMAL_PRIORITY_CLASS` xep hang CPU, no **khong nhuong bo
   nho**. Muoi bon tien trinh Python cong mot model that khong duoc uu tien thap
   cuu khoi mot lan het RAM.

⚠️ Va la RAM TRONG, khong phai phan tram da dung: con so can tra loi la "con bao
   nhieu de mo 14 tien trinh nua", khong phai "da dung bao nhieu".

⚠️ CPU van do trung binh 2 giay chu khong lat cat — mot lat cat trung luc mot
   tien trinh vua thuc day se doc 100% cho mot may dang ranh. No o day de nguoi
   doc co ngu canh, khong de may quyet dinh.

🔴 Va tam GiB van la mot nguong DE XUAT tu mot lan do, khong phai hang so da
   chung minh. No o day de co mot con so chung thay vi moi phien tu doan mot
   kieu.

## ⛔ Va mot ly do nua de KHONG noi cai nay vao `gate.py`

Phien `lttstudiosapp-73` chi ra mot the khoa chet ma `cua_so_yen` hien khong co:

    gate A: GIU khoa cpu_nhieu  ->  doi tai giam
    gate B: doi khoa cpu_nhieu
    nguon tai that: LTTStudioWorker dang chay mot job cua KHACH

A doi mot thu **no khong gay ra va khong ket thuc duoc**, trong luc chan B. Ca
hai dung im cho toi khi khach kia xong.

⇒ Neu sau nay co ai noi phep do nay vao mot duong co khoa: dat no **truoc** khi
  xin khoa, dung dat sau. Va dung bao gio de no **chan** — `_chay_theo_lich` da
  ghi cung bai hoc: *"tu choi chay thi cong chat luong thanh vo dung tren may
  nho, va do la kieu hong te hon han cham."* Mot cua bi chan se de ra mot co
  `--bo-qua-cua-tai`, va tu do cua ay khong con ton tai.
"""
from __future__ import annotations

import argparse
import sys
import time

RANH = "RANH"
BAN = "BAN"
QUA_TAI = "QUA TAI"

#: Trung binh CPU do trong bao lau. Xem ghi chu dau tep.
CUA_SO_DO_S = 2.0

#: ⛔ KHONG co nguong CPU **theo PHAN TRAM**. Xem muc "Phan quyet dua tren RAM"
#:    o dau tep: nen CPU cua may nay bien dong gan muoi lan trong mot ngay
#:    (27% -> 3%), nen mot nguong phan tram co dinh se bat sai theo gio chu
#:    khong theo tai that.
NGUONG_RAM_TRONG_BAN_GIB = 8.0
NGUONG_RAM_TRONG_QUA_TAI_GIB = 4.0

#: 🔴 **LO DO DUOC 28/09/2026, sau lan treo may thu ba.**
#:
#:    `chay_nang.py` vong cho **chi doc ham nay** de quyet dinh co cho hay khong.
#:    Ham nay phan quyet **chi theo RAM**. Nen mot may dang bi chiem 9,5/10 loi
#:    van tra `RANH`, va moi lenh nang cua moi phien cu the lao vao. Lan treo
#:    28/09: gate `--ho-so day-du` (7 worker + 8 buoc tinh) canh Windows Defender
#:    (5,45 loi) — `tai_may` bao RANH suot.
#:
#: ⭐ Va day **khong** phai mot nguong phan tram — do la thu tep nay tu choi, co
#:    ly. Day la mot phep tru co DON VI: *con bao nhieu LOI VAT LY ranh*. Mot
#:    lenh nang can it nhat vai loi; duoi con so nay thi khong con cho de chay,
#:    bat ke dong ho treo tuong noi may dang ban bao nhieu phan tram.
#:
#: ⚠️ Chi ha xuong `BAN`/`QUA TAI`, ⛔ khong bao gio nang len `RANH`: RAM van la
#:    ve co the mot minh tuyen QUA TAI. Hai ve, lay ve TE HON.
#: 📐 **Vi sao 3,0 chu khong 4,0** — `chay_nang.py` cho khi phan quyet la `BAN`
#:    HOAC `QUA TAI`, va cho qua 30 phut thi **thoat 3 = khong chay**. Nen moi
#:    lan cua nay bat oan la mot lenh nang bi huy, o MOI phien.
#:
#:    Do 25/09: Windows Defender an **5,45 loi** ⇒ con **4,55** ranh. Nguong 4,0
#:    se bat MOI lan Defender quet — tuc bien mot cua canh thanh mot cua chan,
#:    va nguoi ta se hoc cach go `--khong-khoa` de di vong.
#:
#: ⚠️ 3,0 van bat dung ca da lam treo may: gate `bo test` 7 worker + 8 buoc tinh
#:    (ranh ~0) va ca `RapidOCR` 15,2 loi tu trong mot worker (B12, phien khac).
LOI_RANH_TOI_THIEU_BAN = 3.0
LOI_RANH_TOI_THIEU_QUA_TAI = 2.0


def do() -> dict:
    """`{cpu, ram_trong_gib, loi, phan_quyet, ly_do}`.

    Tra `phan_quyet=None` khi khong do duoc — **khong** doan la RANH. Mot phep
    do that bai va mot may ranh khong duoc phep trong giong nhau.
    """
    try:
        import psutil
    except ImportError:
        return {"phan_quyet": None, "ly_do": "khong co psutil - khong do duoc",
                "cpu": None, "ram_trong_gib": None, "loi": None}

    cpu = psutil.cpu_percent(interval=CUA_SO_DO_S)
    bo_nho = psutil.virtual_memory()
    trong = bo_nho.available / (1024 ** 3)
    loi = psutil.cpu_count() or 0

    # ── Ve RAM ──────────────────────────────────────────────────────────────
    if trong < NGUONG_RAM_TRONG_QUA_TAI_GIB:
        pq, ly_do = QUA_TAI, "RAM trong qua thap - 14 tien trinh nua rat de het"
    elif trong < NGUONG_RAM_TRONG_BAN_GIB:
        pq, ly_do = BAN, "RAM trong dang hep - nen chay cum nho, dung bat model that"
    else:
        pq, ly_do = RANH, "du bo nho cho mot luot day du"

    # ── Ve LOI RANH (them 28/09/2026) ───────────────────────────────────────
    #
    # ⭐ Don vi VAT LY, cung don vi `gate.loi_cong_cu_tu_do()` va `-n`. ⛔ Khong
    #    dung `psutil.cpu_count()` (= 20 LOGIC) o day: tron hai don vi la chinh
    #    con bo `-n 11 > auto 10` da lam treo may 03/09.
    vat_ly = psutil.cpu_count(logical=False) or loi or 1
    ranh = max(0.0, vat_ly * (100.0 - cpu) / 100.0)
    if ranh < LOI_RANH_TOI_THIEU_QUA_TAI:
        pq = QUA_TAI
        ly_do = (f"chi con {ranh:.1f}/{vat_ly} loi vat ly ranh - "
                 f"khong con cho cho mot lenh nang ({ly_do})")
    elif ranh < LOI_RANH_TOI_THIEU_BAN and pq == RANH:
        pq = BAN
        ly_do = (f"con {ranh:.1f}/{vat_ly} loi vat ly ranh - "
                 f"chay cum nho thoi ({ly_do})")
    return {"phan_quyet": pq, "ly_do": ly_do, "cpu": cpu,
            "ram_trong_gib": trong, "loi": loi, "loi_ranh": ranh,
            "loi_vat_ly": vat_ly}


def ai_chiem_cho(toi_da: int = 8) -> list[dict]:
    """Tien trinh python dang chay, KEM tuoi va cay cha. De biet AI chiem cho.

    🔴 **Ham nay sinh ra tu mot lan reset may 03/09 ma toi khong dieu tra duoc.**

       Do ngay truoc luc do: cay `gate.py` co 13 tien trinh (dung ngan sach 10
       worker), nhung toan may co **58** tien trinh python. Tuc gate chi la 13/58,
       va ngan sach loi — thu toi vua bo cong sua — chi dieu tiet duoc dung phan
       do. 45 cai con lai khong di qua co che nao.

    ⛔ Khi may reset, bang chung mat het. Khong co ban chup nao truoc do, nen ba
       ung vien (gate / 45 tien trinh kia / chinh phep do) khong phan biet duoc,
       va doan la vo ich.

    ⇒ Ham nay khong sua duoc gi. No chi de lan sau co **du lieu** thay vi mot gia
      thuyet. Chay no TRUOC mot luot nang, va giu ket qua.

    ⚠️ Chinh no cung ton CPU (`process_iter` + `cpu_percent`), nen no lay MOT lat
       cat roi thoi — khong lap, khong theo doi lien tuc.
    """
    try:
        import psutil
    except ImportError:
        return []
    ra = []
    for p in psutil.process_iter(["pid", "ppid", "name", "create_time", "cmdline"]):
        ten = (p.info["name"] or "").lower()
        if not ten.startswith("python"):
            continue
        cl = " ".join(p.info["cmdline"] or [])
        ra.append({
            "pid": p.info["pid"], "ppid": p.info["ppid"],
            "tuoi_phut": max(0.0, (time.time() - p.info["create_time"]) / 60),
            "lenh": cl[:70] or "(khong doc duoc)",
        })
    # Gia nhat truoc: mot tien trinh python song hang gio thuong la XAC mo coi.
    ra.sort(key=lambda x: -x["tuoi_phut"])
    return ra[:toi_da]


def _in(k: dict) -> None:
    if k["phan_quyet"] is None:
        print(f"KHONG DO DUOC: {k['ly_do']}")
        return
    # ⭐ In CA HAI don vi va noi ro ten chung. Ban cu in `9% tren 20 loi` — dung
    #    ca hai so, nhung nguoi doc khong the suy ra *con bao nhieu cho cho mot
    #    `-n 7`*, vi `-n` dem loi VAT LY. Do la cung benh voi dong `[tai may]`
    #    cua `gate.py`: mot con so dung ben mot mau so sai.
    ranh = k.get("loi_ranh")
    vat_ly = k.get("loi_vat_ly")
    them = (f" | ranh {ranh:.1f}/{vat_ly} loi VAT LY"
            if ranh is not None and vat_ly else "")
    print(f"CPU {k['cpu']:.0f}% tren {k['loi']} loi LOGIC{them} | "
          f"RAM trong {k['ram_trong_gib']:.1f} GiB")
    print(f"RESULT: {k['phan_quyet']} - {k['ly_do']}")


def main() -> int:
    p = argparse.ArgumentParser(description="May con cho mot luot do dat tien khong.")
    p.add_argument("--cho", type=float, default=0.0,
                   help="doi toi khi RANH, toi da bao nhieu giay (0 = do mot lan)")
    p.add_argument("--nhip", type=float, default=20.0, help="giay giua hai lan do")
    p.add_argument("--ai", action="store_true",
                   help="liet ke tien trinh python gia nhat - de biet AI chiem cho")
    a = p.parse_args()

    if a.ai:
        ds = ai_chiem_cho()
        print(f"{len(ds)} tien trinh python gia nhat:")
        for x in ds:
            print(f"  pid {x['pid']:6d} ppid {x['ppid']:6d} "
                  f"{x['tuoi_phut']:7.1f} phut  {x['lenh']}")
        print()

    bat_dau = time.time()
    while True:
        k = do()
        _in(k)
        if k["phan_quyet"] in (RANH, None):
            # ⛔ `None` (khong do duoc) tra ve 0 co chu y: mot cong cu do khong
            #    chay duoc khong duoc phep tro thanh mot cai chan. No da noi ro
            #    la khong do duoc, va do la thong tin nguoi goi can.
            return 0
        if a.cho <= 0 or time.time() - bat_dau >= a.cho:
            # 2 = con ban, 3 = qua tai. Khac nhau vi hai tinh huong doi hai
            # phan ung khac nhau: mot cai nen doi, mot cai nen dung han.
            return 2 if k["phan_quyet"] == BAN else 3
        print(f"  [tai may] doi {a.nhip:.0f}s roi do lai "
              f"(da doi {(time.time() - bat_dau) / 60:.1f} phut)\n")
        time.sleep(a.nhip)


if __name__ == "__main__":
    sys.exit(main())
