"""Lop 1 cua bo cham: DOI CHUNG BIET TRUOC DAP AN — do chinh nguoi cham.

    python tools\\cham_doi_chung.py sinh          # dung bo cap, in duong dan
    python tools\\cham_doi_chung.py cham <phieu>  # cham phieu da dien, ra diem

## 🔴 Vi sao cong cu nay ton tai

Chu du an chot 07/09: thay vi thue rater, **Claude cham**. Viec do go duoc
nhom chan nang nhat cua ke hoach — nhung no chi dung vung neu phuong phap
chat. Neu khong, ta doi *"chua co du lieu"* lay *"co du lieu sai"*, va cai sau
te hon: mot con so co dinh dang dep thi khong ai kiem lai.

`BAY_TRONG_CONG_CHAT_LUONG.md` **Bay 24** noi: mot dung cu khong co doi chung
thi con so no phat ra khong phai phat hien. **O day dung cu la nguoi cham.**

⇒ Nen truoc khi bat ky diem so nao cua lop 3 duoc cong bo, nguoi cham phai
  qua lop 1: mot bo cap **da biet dap an mot cach khach quan**.

## Dap an den tu PHEP SUY GIAM, khong tu NOI DUNG

Moi cap gom mot anh goc va mot ban **suy giam co tham so biet truoc** (nen
nang hon, mo hon, nhieu hon, thu nho roi phong lai). Ban goc **luon** tot hon
— khong phai vi ai do phan xet, ma vi phep suy giam la mot ham mot chieu.

⭐ Hai he qua that:

1. **Khong can media co ban quyen.** Anh nguon duoc sinh bang ma (o vuong,
   chu, gradient, hat nhieu) nen lop 1 chay duoc NGAY, khong cho hang muc
   "nguon media co license" cua ke hoach.
2. **Khong the "cham gioi" bang cach doan.** Doan hu hoa cho ~50%. Nguong dat
   dat o 90% chinh vi the.

## ⛔ Cai lop 1 KHONG chung minh

No chung minh nguoi cham **phan biet duoc chat luong khi chenh lech ro rang
va mot chieu**. No **khong** chung minh:

- phan biet duoc hai ban *khac phong cach* nhung cung chat luong;
- doc duoc chat luong THOI GIAN cua video (nhap nhay, giat) — xem `PLAN_HOAN_TAT`
  muc 2, dieu 2;
- khong co thien lech he thong (vd thien ve anh sac net hon muc that).

Mot nguoi cham qua lop 1 van co the sai o lop 3. Lop 1 la dieu kien **CAN**,
khong phai **DU**.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Bi mat lam mu — chi de xao tron trai/phai trong mot luot, khong phai bi mat
#: van hanh. Ghi ra tep dap an chu khong ghi vao thu muc cham.
BI_MAT = "doi-chung-lop-1-khong-phai-bi-mat-van-hanh"

#: Muc suy giam. So cang lon = cang te. Chon de chenh lech NHIN THAY DUOC —
#: lop 1 do "co phan biet duoc khong", khong do "nguong nhay bao nhieu".
MUC: dict[str, list[float]] = {
    "compression": [12, 22],      # chat luong JPEG (thap = te)
    "blur": [2.2, 3.5],           # ban kinh Gauss
    "noise": [26, 44],            # bien do nhieu
    "bicubic": [4, 6],            # he so thu nho roi phong lai
}

#: `slice` phai nam trong `REQUIRED_SLICES` cua `apps/qualitylab/datasets.py`.
LAT = ["text", "nature", "animation", "face"]

DAT_TOI_THIEU = 0.90

#: San rieng cho TUNG phep suy giam. Mot nguoi cham 8/8 o hai truc va 6/8 o
#: mot truc van dat san TONG — nhung neu truc yeu la truc san pham can thi
#: con so tong dang che mat dieu do. Do 07/09: chinh chuyen ay xay ra.
SAN_TUNG_KIEU = 0.80


def _anh_nguon(lat: str, hat: int):
    """Sinh mot anh nguon bang MA — khong dung media co ban quyen.

    Moi `lat` mot ket cau khac nhau, vi mot bo doi chung toan gradient tron se
    chi do duoc mot lop hong (mo), khong do duoc nhieu hay nen.
    """
    from PIL import Image, ImageDraw

    r = random.Random(hat)
    W = H = 512
    im = Image.new("RGB", (W, H), (250, 248, 244))
    d = ImageDraw.Draw(im)

    if lat == "text":
        # Chu nho: lop hong ma NEN va MO pha huy ro nhat.
        for i in range(26):
            y = 12 + i * 19
            d.text((16, y), "LTT " + "".join(
                r.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(46)),
                fill=(20, 20, 28))
    elif lat == "nature":
        # Gradient + ket cau mem: NHIEU noi bat nhat o day.
        for y in range(H):
            d.line([(0, y), (W, y)],
                   fill=(60 + y // 4, 120 + (y * 3) // 8, 90 + y // 6))
        for _ in range(120):
            x, y = r.randrange(W), r.randrange(H)
            d.ellipse([x, y, x + r.randrange(6, 34), y + r.randrange(6, 34)],
                      fill=(r.randrange(40, 210), r.randrange(80, 230),
                            r.randrange(40, 190)))
    elif lat == "animation":
        # Mang mau phang, canh sac: BICUBIC lam rang cua ro nhat.
        for _ in range(40):
            x, y = r.randrange(W), r.randrange(H)
            d.rectangle([x, y, x + r.randrange(30, 150), y + r.randrange(30, 150)],
                        fill=(r.randrange(255), r.randrange(255), r.randrange(255)))
    else:  # face — hinh hoc doi xung, chuyen mau muot
        d.ellipse([120, 90, 392, 430], fill=(232, 200, 178))
        for cx in (200, 312):
            d.ellipse([cx - 26, 210, cx + 26, 252], fill=(250, 250, 252))
            d.ellipse([cx - 11, 222, cx + 11, 244], fill=(46, 38, 34))
        d.arc([214, 300, 298, 366], 200, 340, fill=(150, 92, 84), width=5)
        for y in range(90, 430):
            d.point([(120 + (y % 7), y)], fill=(210, 178, 160))
    return im


def _suy_giam(im, kieu: str, muc, hat: int):
    """Ap mot phep suy giam MOT CHIEU. Khong co duong nao lam anh tot len."""
    import io

    from PIL import Image, ImageFilter

    if kieu == "compression":
        b = io.BytesIO()
        im.save(b, format="JPEG", quality=int(muc))
        b.seek(0)
        return Image.open(b).convert("RGB")
    if kieu == "blur":
        return im.filter(ImageFilter.GaussianBlur(radius=float(muc)))
    if kieu == "bicubic":
        n = int(muc)
        nho = im.resize((im.width // n, im.height // n), Image.Resampling.BICUBIC)
        return nho.resize((im.width, im.height), Image.Resampling.BICUBIC)
    if kieu == "noise":
        r = random.Random(hat)
        px = im.load()
        assert px is not None
        bien = int(muc)
        for y in range(0, im.height, 2):
            for x in range(0, im.width, 2):
                c = px[x, y]
                px[x, y] = tuple(  # type: ignore[index]
                    max(0, min(255, v + r.randint(-bien, bien)))
                    for v in tuple(c))  # type: ignore[call-overload]
        return im
    raise ValueError(f"kieu suy giam la: {kieu!r}")


def _bam(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sinh(thu_muc: pathlib.Path) -> int:
    from apps.qualitylab.calibration import (blind_assignment,
                                             resolve_artifact_token)

    cham = thu_muc / "cham"
    cham.mkdir(parents=True, exist_ok=True)
    for cu in cham.glob("*.png"):
        cu.unlink()

    cases, dap_an, stt = [], [], 0
    for lat in LAT:
        for kieu, cac_muc in MUC.items():
            for muc in cac_muc:
                stt += 1
                ma = f"dc-{stt:03d}"
                hat = int(hashlib.sha256(ma.encode()).hexdigest()[:8], 16)

                goc = _anh_nguon(lat, hat)
                te = _suy_giam(goc.copy(), kieu, muc, hat)

                case = {"id": ma, "media_kind": "image", "degradation": kieu,
                        "slice": lat, "candidate_key": f"{ma}/te",
                        "baseline_key": f"{ma}/goc",
                        "dataset_sample_id": f"tonghop-{lat}-{stt:03d}"}
                cases.append(case)

                gan = blind_assignment(case, "claude", BI_MAT)
                # ⛔ `blind_assignment` CO Y khong noi ben nao la candidate —
                #    do la ca muc dich cua no. Duong cong khai de biet la
                #    `resolve_artifact_token`, va no chi duoc goi o phia tin
                #    cay (docstring cua chinh no noi vay). O day ta LA phia
                #    dung bo cap, nen goi hop le; tep `dap_an.json` sinh ra
                #    tach khoi thu muc cham dung vi ly do ay.
                khoa_trai = resolve_artifact_token(
                    case, "claude", gan["left_artifact_token"], BI_MAT)
                # `candidate` = ban TE. Nen ben nao mang candidate la ben THUA.
                trai_la_te = khoa_trai == case["candidate_key"]
                ben_A = goc if not trai_la_te else te
                ben_B = te if not trai_la_te else goc
                ben_A.save(cham / f"{ma}-A.png")
                ben_B.save(cham / f"{ma}-B.png")

                # ⭐ Ghep canh nhau. Doc hai tep ROI thi nguoi cham so bang TRI
                #    NHO — va tri nho la mot khau yeu khong ai do duoc. Mot
                #    khung nhin duy nhat cho phep so TRUC TIEP, dung cach mot
                #    rater lam. Vach ngan de biet ranh gioi, khong de goi y.
                from PIL import Image as _I
                w, h = ben_A.size
                doi = _I.new("RGB", (w * 2 + 8, h), (255, 255, 255))
                doi.paste(ben_A, (0, 0))
                doi.paste(ben_B, (w + 8, 0))
                doi.save(cham / f"{ma}-AB.png")

                dap_an.append({
                    "id": ma, "slice": lat, "degradation": kieu, "muc": muc,
                    "ben_TOT": "B" if trai_la_te else "A",
                    "bam_A": _bam(cham / f"{ma}-A.png"),
                    "bam_B": _bam(cham / f"{ma}-B.png"),
                })

    (thu_muc / "dap_an.json").write_text(
        json.dumps({"so_cap": len(cases), "dap_an": dap_an},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (thu_muc / "phieu.json").write_text(
        json.dumps({"huong_dan": "moi cap: dien 'A' hoac 'B' — ben NHIN DEP HON",
                    "chon": {c["id"]: "" for c in cases}},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  da sinh {len(cases)} cap  ->  {cham}")
    print(f"  phieu cham            ->  {thu_muc / 'phieu.json'}")
    print(f"  dap an (DUNG MO)      ->  {thu_muc / 'dap_an.json'}")
    print()
    print("  [!] Doc anh trong `cham/`, dien `phieu.json`, ROI moi chay `cham`.")
    print("     Mo `dap_an.json` truoc khi cham thi ca luot do vo nghia.")
    return 0


def cham(thu_muc: pathlib.Path) -> int:
    da = json.loads((thu_muc / "dap_an.json").read_text(encoding="utf-8"))
    ph = json.loads((thu_muc / "phieu.json").read_text(encoding="utf-8"))
    chon = ph.get("chon") or {}

    tra_loi = {k: str(v).strip().upper() for k, v in chon.items() if str(v).strip()}
    if not tra_loi:
        print("  KHONG DAT: phieu rong - chua cham gi.")
        print("  (mot phieu rong khong phai 'chua xong', no la mot luot VO NGHIA)")
        return 1

    dung = 0
    sai: list[str] = []
    theo_kieu: dict[str, list[int]] = {}
    for m in da["dap_an"]:
        c = tra_loi.get(m["id"])
        if not c:
            continue
        ok = c == m["ben_TOT"]
        dung += ok
        theo_kieu.setdefault(m["degradation"], [0, 0])
        theo_kieu[m["degradation"]][1] += 1
        theo_kieu[m["degradation"]][0] += ok
        if not ok:
            sai.append(f"{m['id']} ({m['slice']}/{m['degradation']} muc {m['muc']}): "
                       f"chon {c}, dung la {m['ben_TOT']}")

    tong = len(tra_loi)
    ti_le = dung / tong if tong else 0.0
    print(f"  da cham : {tong}/{da['so_cap']} cap")
    print(f"  dung    : {dung}  ({ti_le:.0%})")
    print()
    for kieu, (d, t) in sorted(theo_kieu.items()):
        print(f"    {kieu:12s} {d}/{t}")
    if sai:
        print()
        print("  cham sai:")
        for s in sai:
            print(f"    {s}")

    # ⛔ SAN THEO TUNG PHEP SUY GIAM — them 07/09 sau luot chay dau tien.
    #
    #    Luot dau ra 29/32 = 91%, DAT nguong tong. Nhung bang chia cho thay:
    #        bicubic 8/8 · blur 8/8 · noise 7/8 · compression 6/8
    #    Mot nguoi cham hoan hao o hai truc va 75% o mot truc van "dat" nguong
    #    TONG. Neu truc yeu ay dung la truc quan trong voi san pham (o day:
    #    nen — thu moi job upscale/video deu phai doi mat), thi con so tong
    #    dang CHE mat dieu can biet.
    #
    # 🔴 Cung ho voi bai da ghi trong kho: mot con so gop lai co the xanh trong
    #    khi mot thanh phan cua no do. San tong khong thay duoc san thanh phan.
    yeu = [f"{k} {d}/{t}" for k, (d, t) in sorted(theo_kieu.items())
           if t and d / t < SAN_TUNG_KIEU]
    if yeu:
        print(f"  [!] duoi san tung kieu ({SAN_TUNG_KIEU:.0%}): {', '.join(yeu)}")
        print("    -> KHONG duoc cham lop 3 tren dung loai suy giam nay.")
        print()

    # ⛔ VA: 8 mau moi kieu KHONG du de phan biet 75% voi 90%. Con so tung kieu
    #    o day la mot CANH BAO co huong, khong phai mot uoc luong chac chan.
    #    Muon ket luan thi phai tang so mau — xem `MUC`.
    if tong < da["so_cap"]:
        print(f"  KHONG DAT: moi cham {tong}/{da['so_cap']}. Cham thieu thi ti le "
              f"khong so sanh duoc voi nguong.")
        return 1
    if ti_le >= DAT_TOI_THIEU:
        print(f"  DAT ({ti_le:.0%} >= {DAT_TOI_THIEU:.0%}) - nguoi cham phan biet "
              f"duoc chat luong khi chenh lech mot chieu.")
        print("  [!] Nhung do la dieu kien CAN, khong phai DU: xem docstring.")
        return 0
    print(f"  KHONG DAT ({ti_le:.0%} < {DAT_TOI_THIEU:.0%}).")
    print("  => Moi diem so cua lop 3 tu nguoi cham nay la NHIEU CO DINH DANG DEP.")
    print("     Dung cong bo chung; sua bo cham hoac doi nguoi cham.")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("lenh", choices=["sinh", "cham"])
    p.add_argument("--thu-muc", default="")
    a = p.parse_args()
    tm = pathlib.Path(a.thu_muc) if a.thu_muc else GOC / "test-results" / "doi-chung-cham"
    return sinh(tm) if a.lenh == "sinh" else cham(tm)


if __name__ == "__main__":
    raise SystemExit(main())
