"""Do LOP QC HINH (M-02): VLM co nhin ra mot cho noi hong khong, va sai bao nhieu.

## Cau hoi no tra loi

`qc_ai.loi_nhac_hinh` + `qc_ai.doc_hinh` hoi model mot cau chu quan: *"cho noi
nay co lam dut mach nhin khong"*. Mot phan quyet chu quan chi duoc phep TIEU
TIEN (day mot vong sua: `edit_plan` + `content_process` + `voice_synthesis` +
render) neu ta biet no DUNG bao nhieu phan. Khong ai do con so do, nen truoc khi
do thi lop nay khong duoc gate — xem `sua_chua.QC_HINH_LA_TU_VAN`.

## Chan ly nen: hai loai cho noi, va mot loai co dap an biet truoc

⭐ Bo do khong the chi gom "cac cho noi cua mot ban cat that": khong ai biet dap
   an cua chung, nen moi con so rut ra se la mot vong tron. Nen bo do co HAI ve:

    `cat_canh`  noi hai canh THAT khong lien nhau (bo cac canh o giua).
                Day la hinh dang cua mot ban `smart_localize` that. Dap an
                **chua biet** -> nguoi do xem hai khung roi gan nhan tay.

    `nhay_hinh` cat mat mot khuc ~1,5 s o GIUA mot canh dai lien tuc roi noi
                lai. Day la mot **jump cut**, va dap an BIET TRUOC: hong.
                ⭐ Day la doi chung duong cua bo do — neu bo do khong bat duoc
                   loai nay thi moi con so o ve kia la vo nghia, vi ta chua
                   chung minh phep do NO duoc.

⛔ Ve `cat_canh` gan nhan tay nen no la chan ly nen cua MOT nguoi. Bao cao ghi
   ro dieu do; khong gia vo do la mot su that tat dinh.

## Cach do

1. `canh.phan_tich` (PySceneDetect ContentDetector 35 — DUNG bo tach san pham)
2. dung mot ban cat: bo moi canh thu `--moi-n` (mac dinh 3)
3. ffmpeg noi cac khoang duoc giu lai, **ma hoa lai libx264 crf23** — dung
   duong san pham (`che_do_render.CAT_MA_HOA_LAI`)
4. `qc_ai.cac_cho_noi` tren `BanDoThoiGian` cua ban cat do
5. moi cho noi: `canh.rut_khung` tren tep DA RENDER -> `ai.goi(QC_HINH)` ->
   `qc_ai.doc_hinh`
6. ghi CA HAI khung ra `--khung` de nguoi do xem lai bang mat va gan nhan

## Bien can

`LTT_ASV_POOL_URL` + `LTT_TOKEN_ENCRYPTION_KEY` — nguoi goi nap tu `app.env`
(`setup\\do_on_dinh.ps1 -Do qc-hinh`). ⛔ Cong cu nay khong doc `app.env` va
khong in mot gia tri bi mat nao.

## ⛔ KHONG chay cong cu nay duoi khoa `cpu_nhieu`

Do 23/09: **~95% thoi gian tuong cua no la CHO MANG** (may B tra loi mot cho noi
trong ~28 giay). Phan CPU that chi la mot lan PySceneDetect (~9 giay/phim) va
mot lan ffmpeg `-threads 2` (~5 giay/phim) — nho hon nhieu so voi mot luot QC
binh thuong cua san pham.

🔴 Lan dau no duoc boc trong `chay_nang.py` va **giu khoa toan may 23,5 phut**
   trong khi GPU nam khong va lan nghiem thu that khong khoi dong duoc. Khoa do
   ton tai de xep hang VIEC TINH TOAN; giu no de CHO la lam doi ca may.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Bon phim nghiem thu that (Douyin, tieng Trung, chi doc).
THU_MUC_PHIM = pathlib.Path(
    r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")

#: ⛔ Hai luong. May A la production; xem docstring dau tep.
LUONG = "2"

#: Bo moi canh thu N cua ban cat gia lap.
MOI_N_MAC_DINH = 3

#: Do dai khuc bi cat GIUA mot canh de tao mot `nhay_hinh` (giay).
#:
#: 🔑 1,5 giay la mot lua chon co ly do: du dai de mot dong tac dang dien ra bi
#:    mat han mot doan (tuc mot jump cut NGUOI nhin cung thay), va du ngan de
#:    hai khung hai ben van thuoc cung boi canh — neu cat 10 giay thi hai khung
#:    co the khac han nhau va bai toan tro thanh "hai canh khac nhau", tuc mot
#:    cau hoi KHAC.
KHUC_NHAY_S = 1.5

#: Canh dai it nhat bao nhieu giay thi du de cay mot `nhay_hinh` vao giua.
CANH_DU_DAI_S = 6.0


def _ffmpeg() -> str:
    from platform_core import media
    return media.ffmpeg_bin()


def _mo_db():
    """SQLite TAM + khoa `ltt_llm` chep tu pool that (CHI DOC).

    Khuon lay nguyen tu `tools/do_toc_do_giong.py`: mot CSDL tam de `api_pool`
    co cho ghi `provider_state`, con khoa thi doc tu pool that — `error_count`
    cua luot do khong lam ban thong ke khoa production.
    """
    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_qc_hinh_")) / "do.db"
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tam.as_posix()}"
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())

    from tests.fixtures import asv_e2e

    so = asv_e2e.nap_khoa_pool(db)
    db.commit()
    print(f"  [OK] nap {so} dong khoa `ltt_llm` tu pool that (chi doc)")
    return db


# ══════════════════════════════════════════════════════════════════════════════
#  Dung mot ban cat THAT roi render no
# ══════════════════════════════════════════════════════════════════════════════

def _ban_cat(ci, *, moi_n: int, so_nhay: int = 4
             ) -> tuple[list[tuple[float, float]], list[dict]]:
    """`(cac khoang GIU, mo ta tung cho noi)` cho mot ban cat gia lap.

    Hai loai cho noi (xem docstring dau tep). Tra ve mo ta de doi chieu SAU khi
    `qc_ai.cac_cho_noi` tu tinh lai tu ban do — hai duong phai khop, va neu
    khong thi bo do dang do mot thu khac voi thu san pham lam.
    """
    canh = list(ci.canh)
    giu: list[tuple[float, float]] = []
    mo_ta: list[dict] = []

    # 🔑 **Cay `nhay_hinh` vao NHIEU canh, khong mot.** Mot doi chung duong duy
    #    nhat moi phim la bon mau cho ca bo do — khong du de noi gi ve ti le bat
    #    duoc. Chon cac canh DAI NHAT (va khong bi bo) de cho noi chac chan ton
    #    tai tren ban ra va hai khung hai ben con thuoc cung boi canh.
    ung_vien = sorted(
        (i for i, c in enumerate(canh)
         if (i + 1) % max(2, moi_n) != 0
         and float(c.ket) - float(c.bat) >= CANH_DU_DAI_S),
        key=lambda i: float(canh[i].ket) - float(canh[i].bat), reverse=True)
    nhay = set(ung_vien[:max(0, int(so_nhay))])

    for i, c in enumerate(canh):
        b, k = float(c.bat), float(c.ket)
        if (i + 1) % max(2, moi_n) == 0:
            mo_ta.append({"loai": "cat_canh", "ma_bo": c.ma,
                          "cat_nguon": [round(b, 3), round(k, 3)]})
            continue
        if i in nhay:
            giua = (b + k) / 2.0
            b2, k2 = giua - KHUC_NHAY_S / 2.0, giua + KHUC_NHAY_S / 2.0
            giu.append((b, b2))
            giu.append((k2, k))
            mo_ta.append({"loai": "nhay_hinh", "ma_bo": c.ma,
                          "cat_nguon": [round(b2, 3), round(k2, 3)],
                          "chan_ly": "hong"})
            continue
        giu.append((b, k))
    return giu, mo_ta


def _render(duong: str, giu, ra: str) -> float:
    """Noi cac khoang GIU thanh mot tep, ma hoa lai crf23. Tra ve giay da ton.

    ⭐ `trim`+`concat` trong MOT lenh, khong ghi tep trung gian: dung hinh dang
       ma `ket_xuat.dung_lenh` dung cho `CAT_MA_HOA_LAI`, nen cho noi tren tep
       ra la cho noi THAT cua san pham chu khong phai mot phep noi khac.
    """
    n = len(giu)
    loc = []
    for j, (b, k) in enumerate(giu):
        loc.append(f"[0:v]trim=start={b:.3f}:end={k:.3f},setpts=PTS-STARTPTS[v{j}]")
    loc.append("".join(f"[v{j}]" for j in range(n)) + f"concat=n={n}:v=1:a=0[vo]")
    cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error",
           "-threads", LUONG, "-i", str(duong),
           "-filter_complex", ";".join(loc), "-map", "[vo]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-an", "-y", str(ra)]
    t0 = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, timeout=3600, check=False)
    if r.returncode != 0 or not pathlib.Path(ra).exists():
        raise RuntimeError(
            f"ffmpeg render hong ({r.returncode}): "
            f"{r.stderr.decode('utf-8', 'replace')[-400:]}")
    return round(time.monotonic() - t0, 2)


# ══════════════════════════════════════════════════════════════════════════════
#  Hoi model
# ══════════════════════════════════════════════════════════════════════════════

def _hoi_mot_cho_noi(db, duong_ra: str, cn: dict, *, thu_muc_khung, ten_phim,
                     stt: int, khong_model: bool = False) -> dict:
    """Rut hai khung + goi model MOT lan. Tra ve mot dong ket qua tho.

    ⛔ Goi `ai.goi` (khong `goi_tinh_tien`): day la mot phep do, khong mot lan
       chay cua khach — khong co `run` de ghi so cai, va bia mot `run` de co
       mot but toan la lam ban so sach that.
    """
    from apps.auto_scan_video import ai, canh as canh_mod, qc_ai

    t0 = time.monotonic()
    khung = canh_mod.rut_khung(duong_ra, cn["khung_s"])
    giay_khung = round(time.monotonic() - t0, 2)
    if not khung:
        return {**cn, "stt": stt, "hong": "thieu_khung"}

    # Bang chung de NGUOI do xem lai — day la thu tra loi cau "co that su hong
    # khong", va khong mot con so nao thay duoc no.
    tep_khung = []
    if thu_muc_khung is not None:
        for t, b in enumerate(khung):
            tep = thu_muc_khung / f"{ten_phim}_{stt:03d}_{cn['loai']}_{t}.jpg"
            tep.write_bytes(b)
            tep_khung.append(tep.name)

    if khong_model:
        # ⭐ Duong KHO: kiem chinh bo do (tach canh -> render -> cho noi -> rut
        #    khung) ma khong tieu mot token nao. Mot bo do chua tu chay duoc
        #    tren duong kho thi moi con so cua no deu la mot gia thuyet.
        return {**cn, "stt": stt, "giay_khung": giay_khung,
                "tep_khung": tep_khung, "khong_model": True}

    b64 = [base64.b64encode(b).decode("ascii") for b in khung]
    messages = qc_ai.loi_nhac_hinh(b64, moc_giay=cn["moc_ra"])

    t0 = time.monotonic()
    try:
        kq = ai.goi(db, ai.QC_HINH, messages)
    except Exception as exc:               # noqa: BLE001 - do ca duong hong
        return {**cn, "stt": stt, "hong": f"{type(exc).__name__}: {exc}"[:300],
                "giay_khung": giay_khung, "tep_khung": tep_khung}
    giay_goi = round(time.monotonic() - t0, 2)

    dong = {**cn, "stt": stt, "giay_khung": giay_khung, "giay_goi": giay_goi,
            "tep_khung": tep_khung,
            "finish_reason": kq.get("finish_reason", ""),
            "suy_nghi_ky_tu": len(str(kq.get("suy_nghi") or "")),
            # ⭐ NGUYEN VAN phan hoi. Do 23/09 cua lane `fix-toc-do` chi tra loi
            #    duoc cau "vi sao hong" vi no giu nguyen van; mot nhat ky chi
            #    ghi TEN LOP bat ta phai goi lai 18 luot that moi biet.
            "noi_dung": str(kq.get("noi_dung") or "")[:1500]}
    do = kq.get("su_dung")
    if do is not None:
        dong["token_vao"] = int(getattr(do, "token_vao", 0) or 0)
        dong["token_ra"] = int(getattr(do, "token_ra", 0) or 0)
    try:
        dong["phan_quyet"] = qc_ai.doc_hinh(
            kq, moc_giay=cn["moc_ra"], ma_cat=cn["ma_cat"], so_khung=len(khung))
    except Exception as exc:               # noqa: BLE001
        dong["hong"] = f"{type(exc).__name__}: {exc}"[:300]
    return dong


def _do_mot_phim(db, tep: pathlib.Path, *, moi_n: int, thu_muc_khung,
                 tam: pathlib.Path, khong_model: bool = False,
                 so_nhay: int = 4, ghi=None, so_sach=None) -> dict:
    from apps.auto_scan_video import (ban_do_thoi_gian as bdtg,
                                      canh as canh_mod, nhap_media, qc_ai)

    ten = tep.stem[:18]
    print(f"\n=== {tep.name[:60]} ===")
    tt = nhap_media.soi(str(tep))
    thoi_luong = float(tt.get("thoi_luong") or 0.0)

    t0 = time.monotonic()
    ci = canh_mod.phan_tich(str(tep), thoi_luong=thoi_luong)
    giay_tach = round(time.monotonic() - t0, 2)
    print(f"  [OK] {len(ci.canh)} canh trong {giay_tach}s ({thoi_luong:.1f}s video)")

    giu, mo_ta = _ban_cat(ci, moi_n=moi_n, so_nhay=so_nhay)
    ra_mp4 = tam / f"{ten}_cat.mp4"
    giay_render = _render(str(tep), giu, str(ra_mp4))
    print(f"  [OK] render {len(giu)} khoang -> {ra_mp4.name} ({giay_render}s)")

    bdo = bdtg.BanDoThoiGian.tu_khoang(giu, thoi_luong_nguon=thoi_luong)
    cac_cn = qc_ai.cac_cho_noi(bdo, chi_muc=ci,
                               cac_ma_cat=[m["ma_bo"] for m in mo_ta])
    # ⭐ Gan LOAI (chan ly nen cua ve `nhay_hinh`) vao tung cho noi bang cach
    #    doi chieu khoang bi cat — khong theo thu tu, vi `tu_khoang` gop cac
    #    khoang lien nhau va thu tu co the lech.
    theo_cat = {tuple(m["cat_nguon"]): m for m in mo_ta}
    for cn in cac_cn:
        m = theo_cat.get(tuple(cn["cat_nguon"]))
        cn["loai"] = (m or {}).get("loai", "cat_canh")
        cn["chan_ly"] = (m or {}).get("chan_ly", "")
    print(f"  [OK] {len(cac_cn)} cho noi "
          f"({sum(1 for c in cac_cn if c['loai'] == 'nhay_hinh')} nhay_hinh)")

    dong: list[dict] = []
    ket = {"phim": tep.name, "thoi_luong": round(thoi_luong, 2),
           "so_canh": len(ci.canh), "giay_tach_canh": giay_tach,
           "giay_render": giay_render, "so_khoang_giu": len(giu),
           "cho_noi": dong}
    # ⭐ Dua `ket` vao so sach cua nguoi goi NGAY, TRUOC vong lap — va `dong`
    #    la CUNG mot doi tuong danh sach, nen moi cho noi vua hoi xong da nam
    #    san trong thu `_ghi` se ghi ra. Doi den `return` la de nua gio phan
    #    quyet nam trong bo nho mot lan nua.
    if so_sach is not None:
        so_sach.append(ket)
    for stt, cn in enumerate(cac_cn):
        d = _hoi_mot_cho_noi(db, str(ra_mp4), cn, thu_muc_khung=thu_muc_khung,
                             ten_phim=ten, stt=stt, khong_model=khong_model)
        dong.append(d)
        pq = d.get("phan_quyet")
        nhan = ("HONG:" + str(d.get("hong"))[:60]) if d.get("hong") else (
            f"dat={pq['dat']} do_tin={pq['do_tin']}" if pq else
            f"{len(d.get('tep_khung') or [])} khung (khong goi model)")
        print(f"    #{stt:02d} {cn['loai']:10s} giay {cn['moc_ra']:8.2f}  {nhan}")
        # Ghi sau MOI cho noi: mot cho noi ton ~28 giay va ~2.500 token.
        if ghi is not None:
            ghi()
    return ket


def _tom_tat(cac_phim: list[dict]) -> dict:
    dong = [d for p in cac_phim for d in p["cho_noi"]]
    co_pq = [d for d in dong if d.get("phan_quyet")]
    hong = [d for d in dong if d.get("hong")]
    nhay = [d for d in co_pq if d["loai"] == "nhay_hinh"]
    canh = [d for d in co_pq if d["loai"] == "cat_canh"]
    return {
        "so_cho_noi": len(dong),
        "so_co_phan_quyet": len(co_pq),
        "so_hong": len(hong),
        "ly_do_hong": sorted({str(d["hong"])[:60] for d in hong}),
        # Doi chung DUONG: cho noi co dap an biet truoc la HONG.
        "nhay_hinh_tong": len(nhay),
        "nhay_hinh_bi_bat": sum(1 for d in nhay if not d["phan_quyet"]["dat"]),
        # Ve khong co dap an san — nguoi do gan nhan tay tu `tep_khung`.
        "cat_canh_tong": len(canh),
        "cat_canh_bi_cham": sum(1 for d in canh if not d["phan_quyet"]["dat"]),
        "token_vao": sum(int(d.get("token_vao") or 0) for d in dong),
        "token_ra": sum(int(d.get("token_ra") or 0) for d in dong),
        "giay_goi": round(sum(float(d.get("giay_goi") or 0) for d in dong), 1),
        "giay_khung": round(sum(float(d.get("giay_khung") or 0)
                                for d in dong), 1),
        "giay_goi_trung_binh": (
            round(sum(float(d.get("giay_goi") or 0) for d in dong)
                  / max(1, len(co_pq)), 2)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phim", default="", help="loc theo ten tep (chuoi con)")
    ap.add_argument("--moi-n", dest="moi_n", type=int, default=MOI_N_MAC_DINH)
    ap.add_argument("--so-nhay", dest="so_nhay", type=int, default=4,
                    help="so `nhay_hinh` (doi chung duong) cay vao moi phim")
    ap.add_argument("--khung", default="", help="thu muc ghi khung bang chung")
    ap.add_argument("--ra", default="", help="tep JSON ghi ket qua")
    ap.add_argument("--khong-model", dest="khong_model", action="store_true",
                    help="chay het bo do NHUNG khong goi model (kiem bo do)")
    args = ap.parse_args()

    if not args.khong_model and not str(
            os.environ.get("LTT_ASV_POOL_URL", "")).strip():
        print("BO QUA: chua co LTT_ASV_POOL_URL "
              "(chay qua setup\\do_on_dinh.ps1 -Do qc-hinh).")
        return 0
    if not THU_MUC_PHIM.is_dir():
        print(f"BO QUA: khong thay {THU_MUC_PHIM}")
        return 0

    phim = sorted(t for t in THU_MUC_PHIM.iterdir()
                  if t.is_file() and t.suffix.lower() == ".mp4"
                  and (not args.phim or args.phim in t.name))
    if not phim:
        print("BO QUA: khong co phim nao khop.")
        return 0

    thu_muc_khung = None
    if args.khung:
        thu_muc_khung = pathlib.Path(args.khung)
        thu_muc_khung.mkdir(parents=True, exist_ok=True)

    db = None if args.khong_model else _mo_db()
    cac_phim: list[dict] = []

    def _ghi() -> None:
        """Ghi ket qua NGAY, sau moi cho noi va sau moi phim.

        🔴 **Ban dau phep ghi nay chi chay o cuoi, va do la mot loi da tra gia.**
           Luot do 23/09 bi dung sau **51 cho noi da hoi** (23 phut): moi phan
           quyet nam trong BO NHO nen dung la mat sach — trong khi khung hinh
           thi da nam tren dia tu lau.

        ⇒ Mot bo do dai phai ben voi mot lan bi dung, y nhu mot giai doan dai
          (`lat_cat.py`) phai ben voi mot lan worker chet. Cung bai hoc, o mot
          tang khac.
        """
        if not args.ra:
            return
        pathlib.Path(args.ra).write_bytes(json.dumps(
            {"phim": cac_phim, "tom_tat": _tom_tat(cac_phim)},
            ensure_ascii=False, indent=1).encode("utf-8"))

    with tempfile.TemporaryDirectory(prefix="ltt_qc_hinh_") as tam:
        for t in phim:
            try:
                _do_mot_phim(
                    db, t, moi_n=args.moi_n, thu_muc_khung=thu_muc_khung,
                    tam=pathlib.Path(tam), khong_model=args.khong_model,
                    so_nhay=args.so_nhay, ghi=_ghi, so_sach=cac_phim)
            except Exception as exc:       # noqa: BLE001 - mot phim hong != bo do hong
                print(f"  [HONG] {t.name[:50]}: {type(exc).__name__}: {exc}")
                cac_phim.append({"phim": t.name, "hong": str(exc)[:400],
                                 "cho_noi": []})
            _ghi()

    _ghi()
    print()
    print(json.dumps(_tom_tat(cac_phim), ensure_ascii=False, indent=2))
    if args.ra:
        print(f"\n  [OK] ghi {args.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
