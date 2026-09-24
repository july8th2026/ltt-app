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

#: 🔴 **BI DANH ASCII cho bon phim — va day la mot ban va, khong mot tien nghi.**
#:
#:    Ten tep la tieng Trung hoan toan. Nguoi goi that di qua
#:    `setup\do_on_dinh.ps1`, va `nang_quyen.py` sinh tep `.ps1` **thuan ASCII**
#:    (CLAUDE.md luat 6: PowerShell 5.1 doc `.ps1` khong BOM theo ANSI). Nen mot
#:    tham so `-Phim 廉价` toi noi thanh `--phim ??`:
#:
#:        do 23/09: tien trinh chay that mang `--phim ??`, khong phim nao khop,
#:        cong cu in "BO QUA" roi thoat 0 — mot luot do **thanh cong ma khong do
#:        gi**, va no trong y het mot luot dang chay tu ben ngoai.
#:
#: ⭐ Bi danh cung ghim `v1..v4` cua tai lieu vao TEP THAT. Truoc day hai thu do
#:    chi khop nhau trong dau nguoi doc: `L_KY_THUAT.md` goi "v3 跳伞 107 s" con
#:    ma nguon sap xep theo `sorted()` — mot thu tu KHAC. Mot lan doi chieu nham
#:    la mot bang so gan sai phim.
BI_DANH = {"v1": "牛肠", "v2": "露营", "v3": "跳伞", "v4": "气枪"}

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
#:
#: 🔴 **6,0 giay la mot con so TU DAT, va no da lam hong mot luot do.**
#:
#:    v1 co 125 canh trong 265 giay (trung binh 2,1 giay/canh). Khong canh nao
#:    khong-bi-bo dai toi 6 giay, nen `_ban_cat` cay **0** `nhay_hinh` — tuc
#:    luot do chay 45 cho noi ma **khong co mot doi chung duong nao**, va no
#:    khong he keu len. Bo do khi do chi tra loi duoc *"model cham bao nhieu
#:    cai la hong"*, khong tra loi duoc *"model co bat duoc mot cai hong that
#:    khong"* — hai cau khac han nhau.
#:
#: ⭐ Nay con so duoc TINH RA tu `KHUC_NHAY_S`: cat mot khuc o giua thi hai nua
#:    con lai moi nua phai con it nhat `LE_TOI_THIEU_S` de con lay duoc khung o
#:    `moc ± LECH_KHUNG_GIAY`. Doi `KHUC_NHAY_S` thi nguong nay di theo.
LE_TOI_THIEU_S = 0.75
CANH_DU_DAI_S = KHUC_NHAY_S + 2 * LE_TOI_THIEU_S


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
    if int(so_nhay) and not nhay:
        # 🔴 **KEU LEN, dung im lang.** Mot bo do khong co doi chung duong van
        #    chay het va van in ra mot bang so — bang so do chi noi duoc "model
        #    cham bao nhieu cai la hong", khong noi duoc "model co bat duoc mot
        #    cai hong that khong". Do 23/09: v1 cay 0 `nhay_hinh` (khong canh
        #    nao dai >= nguong) va khong mot dong nao noi ra.
        print(f"  [!] KHONG cay duoc `nhay_hinh` nao: khong canh nao dai "
              f">= {CANH_DU_DAI_S:.2f}s. LUOT NAY KHONG CO DOI CHUNG DUONG.")

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
    ap.add_argument("--phim", default="",
                    help="bi danh ASCII (v1|v2|v3|v4, ngan cach bang dau phay) "
                         "hoac mot chuoi con cua ten tep. Xem `BI_DANH`.")
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

    # Bi danh ASCII -> chuoi con tieng Trung. Xem `BI_DANH`.
    loc = [x.strip() for x in str(args.phim or "").split(",") if x.strip()]
    loc = [BI_DANH.get(x.lower(), x) for x in loc]
    phim = sorted(t for t in THU_MUC_PHIM.iterdir()
                  if t.is_file() and t.suffix.lower() == ".mp4"
                  and (not loc or any(x in t.name for x in loc)))
    if not phim:
        # 🔴 **HONG, khong "BO QUA".** Mot bo loc khong khop cai gi la mot LOI
        #    GO, va tra 0 o day bien no thanh mot luot do "thanh cong" khong do
        #    gi — dung dieu da xay ra 23/09 khi `-Phim 廉价` toi noi thanh `??`.
        print(f"HONG: bo loc {loc!r} khong khop phim nao trong {THU_MUC_PHIM}. "
              f"Bi danh hop le: {sorted(BI_DANH)}")
        return 2

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
        # 🔴 **Ghi NGUYEN TU: tep tam roi `os.replace`.**
        #
        #    `write_bytes` thang vao dich KHONG nguyen tu. Do that 23/09: tien
        #    trinh bi `taskkill /F` giua mot lan ghi, va tep ket qua con lai
        #    **21.260 byte toan `\x00`** — NTFS da cap phat khoang nhung du lieu
        #    chua kip xuong dia. Tuc mot tep co that, co kich thuoc that, va
        #    khong mot byte du lieu nao: te hon han mot tep vang mat, vi no
        #    trong nhu mot ket qua.
        #
        # ⭐ `os.replace` la doi ten NGUYEN TU tren cung o dia. Nguoi doc hoac
        #    thay ban CU tron ven, hoac thay ban MOI tron ven — khong bao gio
        #    thay mot ban nua chung.
        dich = pathlib.Path(args.ra)
        tam = dich.with_suffix(dich.suffix + ".tmp")
        tam.write_bytes(json.dumps(
            {"phim": cac_phim, "tom_tat": _tom_tat(cac_phim)},
            ensure_ascii=False, indent=1).encode("utf-8"))
        os.replace(tam, dich)

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
