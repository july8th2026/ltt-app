"""Do NGAN SACH TOKEN RA that su can cua `chuyen_loi_thoai`, theo CO LO.

## Cau hoi no tra loi

`tools/do_on_dinh_chuyen_loi_thoai.py` da chung minh tran 4.096 la nguyen nhan:
cung mot loi nhac, tran 4.096 hong 3/3 voi `finish_reason=length`, tran 12.288
xong 3/3 voi `finish_reason=stop` va `token_ra` = 5.868 / 7.526 / 6.422.

Con lai dung mot cau: **dat tran moi la bao nhieu?**

⛔ Va do la cau khong duoc tra loi bang cach nhan doi mot con so cho de chiu.
   Lo vua do co **6** doan; lo that cua san pham co toi `long_tieng.DOAN_MOI_LO`
   = **12**. Mot tran vua khit cho 6 doan la dung mot lan nua cai bay vua sap:
   mot tran dat DUOI nhu cau binh thuong khong lam hong thinh thoang — no lam
   hong MAC DINH, va ba lan thu lai o cung tran chi la ba lan tung lai dung dong
   xu ay.

## Cach do: HAI DIEM, mot duong thang

    lo 6 doan  @ tran rong  ->  token_ra can bao nhieu
    lo 12 doan @ tran rong  ->  token_ra can bao nhieu

Hai diem cho ra **do doc** (moi doan them ton bao nhieu) va **diem cat** (phi co
dinh cua mot lan goi). Mot diem chi cho ra mot con so, va mot con so khong noi
duoc gi ve co lo khac.

⚠️ TRAN PHAI RONG o CA HAI, neu khong phep do se do chinh cai tran chu khong do
   nhu cau. Do la cach `token_ra = 4096` o lo do truoc tro thanh mot con so vo
   nghia: no khong noi model can bao nhieu, no noi ta cho no bao nhieu.

## 🔴 Sau doan dau la THAT, sau doan sau la DUNG THEM

Sau cau dau chep nguyen van tu ban ghi ASR cua luot nghiem thu 09/09. Sau cau
sau do toi viet, cung dang hoi thoai hoi thao, **de keo co lo len 12**.

⇒ Nen doc ket qua nhu the nay: diem 6-doan la mot phep do THAT; diem 12-doan la
  phep do mot dau vao CO CUNG HINH DANG. Do doc rut ra tu hai diem ay noi ve
  hinh dang, khong noi ve mot video cu the — va do dung la thu ta can, vi ta
  dang chon mot tran cho MOI video.

## Bien can

Chay qua `setup\\do_on_dinh.ps1` (nang quyen) — no doc `app.env` va dat
`LTT_ASV_POOL_URL`. Khong tu go bi mat vao shell.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import statistics
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Sau cau DAU la ban ghi ASR that cua luot 09/09 (chep tu
#: `docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json`, khoa
#: `luot[].asr.van`). Sau cau SAU do toi viet de keo co lo len 12 — chung khong
#: den tu mot video nao, va cho nay noi ro dieu do.
CAU_THAT = [
    "Good morning everyone, and welcome to the workshop on video localization.",
    "Thank you.",
    "Can you show us how the first example actually works in practice?",
    "Of course.",
    "The system reads the picture first, and only then decides what to keep.",
    "That is a much better order than translating everything before looking at it.",
]
CAU_THEM = [
    "Let me open the second clip so everyone can follow along.",
    "Notice how the subtitles disappear once the shot changes.",
    "Does the same thing happen when the speaker turns away from the camera?",
    "It does, and that is exactly the case we spent the most time on.",
    "We ended up keeping the original audio underneath at a much lower level.",
    "That small decision saved us from redoing the whole second half.",
]


def _doan(n: int) -> list[dict]:
    """`n` doan voi moc thoi gian lien tuc va do dai uoc theo so tu."""
    cau = (CAU_THAT + CAU_THEM)[:n]
    if len(cau) < n:
        raise SystemExit(f"chi co {len(CAU_THAT + CAU_THEM)} cau mau, xin {n}")
    ra: list[dict] = []
    moc = 0.8
    for i, chu in enumerate(cau):
        dai = round(max(0.6, len(chu.split()) / 2.5), 2)
        ra.append({"ma": f"s{i + 1}", "chu": chu,
                   "bat": moc, "ket": round(moc + dai, 2)})
        moc = round(moc + dai + 1.2, 2)
    return ra


def _mo_db():
    """CSDL tam DA NAP KHOA tu pool that — dung khuon `asv_e2e.nap_khoa_pool`.

    Chep sang CSDL RIENG (khong ghi vao pool that) nen bo dem `last_used_at` /
    `error_count` cua luot do khong lam ban thong ke khoa production.
    """
    import tempfile

    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_ngan_sach_")) / "do.db"
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
    return db, so


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vong", type=int, default=4, help="so vong (mac dinh 4)")
    ap.add_argument("--tran", type=int, default=24576,
                    help="tran token ra khi DO (phai rong; mac dinh 24.576)")
    # 🔴 **RAO THU HAI, va thieu no thi phep do nay vo nghia.**
    #
    #    `dieu_phoi.goi` mac dinh `timeout_s = 120.0`. Sau luot do o lo **6**
    #    doan mat 65,8-107,7 giay (~70 token/giay), tuc luot cham nhat cach
    #    tran thoi gian 10%. Mot lo **12** doan se vuot no chac chan.
    #
    # ⛔ Neu de mac dinh, moi luot lo 12 se chet vi HET GIO va ta se do lai
    #    dung cai phanh thay vi do nhu cau — y het cach `token_ra = 4096` tro
    #    thanh mot con so vo nghia. Mot phep do phai rong o MOI chieu no khong
    #    dinh do.
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="giay cho moi luot khi DO (phai rong; mac dinh 900)")
    ap.add_argument("--cho-ban", type=int, default=45, dest="cho_ban",
                    help="giay cho khi may B bao BAN (mac dinh 45)")
    ap.add_argument("--ban-toi-da", type=int, default=20,
                    dest="ban_toi_da",
                    help="so lan cho toi da cho MOT luot (mac dinh 20)")
    args = ap.parse_args()

    if not str(os.environ.get("LTT_ASV_POOL_URL", "")).strip():
        print("BO QUA: chua co LTT_ASV_POOL_URL. Chay qua "
              "`setup\\do_on_dinh.ps1` (nang quyen).")
        return 0

    db, so_khoa = _mo_db()
    if not so_khoa:
        print("  [!!] Pool that khong co khoa `ltt_llm` nao dung duoc. Dung.")
        return 1

    from apps.auto_scan_video import ai, long_tieng

    co_lo = (6, int(long_tieng.DOAN_MOI_LO))
    print(f"  tran hien hanh cua san pham : {ai.tran_token_ra():,}")
    print(f"  tran DUNG DE DO             : {args.tran:,} (phai rong)")
    print(f"  timeout DUNG DE DO          : {args.timeout:,.0f}s (phai rong)")
    print(f"  DOAN_MOI_LO cua san pham    : {long_tieng.DOAN_MOI_LO}")
    print()

    do: dict[int, list[int]] = {n: [] for n in co_lo}
    # 🔴 THOI GIAN la rao THU HAI, va no phai duoc do CUNG luc chu khong suy ra
    #    tu token: hai rao khong doc lap (token cao hon => chay lau hon), nhung
    #    ty le giua chung phu thuoc toc do sinh cua may B tai thoi diem do.
    giay_do: dict[int, list[float]] = {n: [] for n in co_lo}
    hong: dict[int, int] = {n: 0 for n in co_lo}
    cham_tran = 0

    for v in range(args.vong):
        for n in co_lo:
            doan = _doan(n)
            msg = long_tieng.loi_nhac(
                doan, tat_ca=doan, ngon_ngu_goc="en",
                dac_diem_giong={"gioi_tinh": "nam", "toc_do": "vua"})
            vao = sum(len(str(x.get("content") or "")) for x in msg)

            # ⛔ **BAN khong phai mot phep do THAT BAI — no la mot phep do CHUA
            #    XAY RA.** Gop hai thu do lai la cach chac chan nhat de ket luan
            #    ve mot thu chua he duoc goi.
            #
            #    Do that 09/09 14:21: ca 6 luot tra `MayBan` trong **0,3 giay**,
            #    va luc do may B dang 88% GPU / 365 W - mot phien khac giu suat
            #    (`DONG_THOI_MAY_B=1`). THOI LUONG la thu phan biet: mot luot
            #    thuc su cham may B mat 60-150 giay.
            #
            # ⚠️ Cho roi thu lai DUNG luot ay, khong bo qua no: bo qua se lam
            #    so mau cua hai co lo lech nhau, va duong thang noi hai diem se
            #    duoc ve tu hai co mau khac nhau ma khong ai thay.
            for lan in range(args.ban_toi_da + 1):
                t0 = time.monotonic()
                try:
                    kq = ai.goi(db, ai.CHUYEN_LOI_THOAI, msg,
                                max_tokens=args.tran,
                                timeout_s=args.timeout)
                    ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI)
                    nhan = "ok"
                except Exception as exc:                    # noqa: BLE001
                    kq = {}
                    nhan = f"{type(exc).__name__}: {exc}"
                giay = time.monotonic() - t0
                if "MayBan" not in nhan:
                    break
                if lan >= args.ban_toi_da:
                    print(f"     [!!] May B BAN sau {lan + 1} lan cho. Dung.")
                    print("          Chay lai khi no ranh - phep do nay CAN suat")
                    print("          may B, va `DONG_THOI_MAY_B=1`.")
                    return 2
                print(f"     [..] May B BAN ({giay:.1f}s - chua cham mang). "
                      f"Cho {args.cho_ban}s roi thu lai chinh luot nay.")
                time.sleep(args.cho_ban)

            if nhan != "ok":
                hong[n] += 1
            sd = kq.get("su_dung")
            ra = int(getattr(sd, "token_ra", 0) or 0)
            fr = str(kq.get("finish_reason") or "-")
            if nhan == "ok":
                do[n].append(ra)
                giay_do[n].append(giay)
            print(f"  vong {v + 1:>2}  lo {n:>2} doan  {giay:6.1f}s  "
                  f"vao~{vao / 4.5:>5,.0f}tok  ra={ra:>6,}tok  fr={fr:<8s} "
                  f"nghi={len(kq.get('suy_nghi') or ''):>6,}ky_tu  {nhan[:60]}")
            # ⛔ Mot luot `length` o day lam HONG PHEP DO, khong chi lam hong
            #    mot luot: `token_ra` khi ay BANG tran, tuc no do cai tran chu
            #    khong do nhu cau. Noi ra ngay, dung de nguoi doc trung binh no
            #    vao cung cac luot that.
            if fr == "length":
                cham_tran += 1
                print(f"     [!!] CHAM TRAN {args.tran:,}: so `ra` tren la TRAN, "
                      "khong phai NHU CAU. Nang `--tran` roi do lai.")

    print()
    print("=" * 72)
    diem: dict[int, float] = {}
    for n in co_lo:
        ds = sorted(do[n])
        if not ds:
            print(f"  lo {n:>2} doan: khong luot nao xong")
            continue
        diem[n] = float(max(ds))
        print(f"  lo {n:>2} doan: n={len(ds)}  min={ds[0]:>6,}  "
              f"p50={statistics.median(ds):>8,.0f}  max={ds[-1]:>6,}  "
              f"hong={hong[n]}")

    diem_giay: dict[int, float] = {n: max(v) for n, v in giay_do.items() if v}
    for n in co_lo:
        # ⚠️ Ten bien rieng, KHONG dung lai `v` cua vong `for v in range(...)`
        #    o tren: cung mot ten mang hai kieu trong mot ham lam mypy bao bon
        #    loi (mot phep gan + ba he qua). Luc chay thi dung — Python gan lai
        #    thoai mai — nen no khong bao gio no, va vi the no o lai rat lau.
        gd = sorted(giay_do[n])
        if gd:
            print(f"  lo {n:>2} doan: giay min={gd[0]:>6.1f}  "
                  f"p50={statistics.median(gd):>6.1f}  max={gd[-1]:>6.1f}")

    if len(diem) == 2 and len(diem_giay) == 2:
        a, b = co_lo
        print()
        # ⛔ MOI chuoi IN RA phai thuan ASCII. Chu thich thi khong sao.
        #    Do that 09/09: mot dau gach ngang dai trong `print()` lam tien
        #    trinh chet voi `UnicodeEncodeError` khi dau ra bi chuyen huong
        #    (console Windows la cp1252), va ca luot do 15 phut ra EXITCODE=1
        #    du moi luot goi deu thanh cong.
        print("  HAI duong qua HAI DIEM, cung truc `n`. Lay MAX moi diem chu")
        print("  khong lay trung binh: mot tran phai chiu duoc lan TOI NHAT.")
        print()
        # ⛔ Khong khop qua GOC. `ra` co mot phan KHONG ty le voi so doan -
        #    khoi suy nghi mo dau, loi nhac he thong, khuon JSON - nen hinh
        #    dang that la `cat + doc * n`. Khop qua goc buoc phai nang `doc`
        #    de che lo nho, va khi do MOI lo lon xin tran thua.
        #
        #    Cung bai voi `apps/ltt_voice/gia.py`: uoc thoi luong bang mot phep
        #    chia `ky_tu / toc_do` hong vi phi khoi dong CO DINH, va mot phep
        #    chia buoc phai ha mau so de che cau ngan.
        ket: dict[str, tuple[float, float, str]] = {}
        for ten, bang, don_vi in (("token ra", diem, "token"),
                                  ("thoi gian", diem_giay, "giay")):
            doc = (bang[b] - bang[a]) / max(1, b - a)
            cat = bang[a] - doc * a
            ket[ten] = (cat, doc, don_vi)
            print(f"  {ten:10s}: can(n) ~ {cat:>9,.0f} + {doc:>7,.1f} * n  "
                  f"({don_vi})")
            print(f"      {'':10s}  co dinh {cat:,.0f}  |  moi doan {doc:,.1f}")
        print()
        for n in (co_lo[1], 16, 20):
            d = "  ".join(
                f"{ten}={c + d_ * n:>8,.0f}{u[0]}" for ten, (c, d_, u) in ket.items())
            print(f"      n={n:>2}  ->  {d}")
        print()
        # ⚠️ Moi phep do o tren chay voi rao KIA da noi (tran token
        #    `--tran`, timeout `--timeout`). Chung noi model CAN bao nhieu; chung
        #    KHONG noi gi ve he khi mot trong hai rao van o gia tri cu. Hai rao
        #    khong doc lap: token cao hon thi thoi gian dai hon.
        print(f"  (do o cau hinh: tran token {args.tran:,} | "
              f"timeout {args.timeout:,.0f}s - CA HAI da noi)")

    # ⛔ **Mot phep do khong thu duoc du lieu nao KHONG duoc bao thanh cong.**
    #
    #    Do that 09/09 14:21: luot dau tien cua cong cu nay hong ca 6 luot vi
    #    may B ban, in ra "khong luot nao xong", roi thoat voi EXITCODE=0. Mot
    #    ma thoat 0 la loi hua rang co the doc ket qua o tren - va o tren khong
    #    co ket qua nao. Lop ngoai (`do_on_dinh_nang_quyen.ps1`) chi ghi
    #    `EXITCODE=`, nen no in mau xanh cho mot lo do rong.
    if len(diem) < 2:
        print()
        print("  KHONG DU DU LIEU: can CA HAI co lo moi ve duoc duong thang.")
        return 1
    if cham_tran:
        print()
        print(f"  {cham_tran} luot CHAM TRAN {args.tran:,}: duong thang o tren")
        print("  ve tu nhung con so bi CAT. Nang `--tran` roi do lai.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
