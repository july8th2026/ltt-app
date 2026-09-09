"""Do TI LE HONG cua `chuyen_loi_thoai` tren may B — CO DOI CHUNG.

## Cau hoi no tra loi

Luot nghiem thu 09/09 chet o `content_process` voi:

    chuyen_loi_thoai: model tra ve rong                          x4
    chuyen_loi_thoai: JSON hong (Expecting ',' ... char 328)     x1

`max_tokens` = 32.768 con JSON chi ~329 ky tu, nen TRAN khong phai nguyen nhan.
Cau con lai: loi cua **loi nhac/luoc do cua chinh thao tac ay**, hay cua **may
B / llama-swap**?

## ⛔ DOI CHUNG LA PHAN KHONG DUOC BO

Goi rieng `chuyen_loi_thoai` roi dem ti le hong se cho ra mot con so **gan
duoc cho ca hai gia thuyet**. Nen moi vong goi CA HAI thao tac, XEN KE:

    chuyen_loi_thoai   nghi ngo        (loi nhac tu `long_tieng.loi_nhac`)
    rut_ngan_cho_vua   DOI CHUNG       (loi nhac tu `nan_cho_vua.loi_nhac`)

Ca hai cung model `qwen38-api`, cung doi JSON co khoa `doan`, va luot 09/09
doi chung qua 9/9.

    chi thao tac nghi ngo hong  => loi o THAO TAC (loi nhac/luoc do)
    ca hai cung hong            => loi o MAY B / llama-swap
    khong cai nao hong          => phu thuoc DAU VAO THAT, sang buoc (2)

⚠️ Xen ke chu khong chay het cai nay roi cai kia: neu may B xuong cap dan theo
   thoi gian, chay tuan tu se gan het phan hong cho thao tac chay sau.

## ⛔ DI DUNG DUONG SAN PHAM DI

Dung `long_tieng.loi_nhac` + `ai.goi` + `ai.doc_json` — **khong** tu dung mot
loi nhac rieng. Mot ban gia tra ve dung thu ma nguon MUON nhan (thay vi thu
model that tra ve) da tung lam ca bo test xanh quanh mot loi khong the khong
xay ra (xem `giai_doan_noi_dung.py:170`).

## Bien can

Chay qua `setup\\do_on_dinh.ps1` (nang quyen) — no doc `app.env` va dat
`LTT_ASV_POOL_URL`. Khong tu go bi mat vao shell.
"""
from __future__ import annotations

import argparse
import collections
import os
import pathlib
import statistics
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Doan mau — CO Y NGAN. Neu mot dau vao ngan van hong thi do dai dau vao
#: KHONG phai nguyen nhan, va do la mot ket luan manh chu khong phai mot
#: quan sat mo ho.
DOAN_MAU = [
    {"ma": "s1", "chu": "Hello everyone, welcome back to the channel.",
     "bat_dau": 0.0, "ket_thuc": 2.6},
    {"ma": "s2", "chu": "Today we are looking at something quite unusual.",
     "bat_dau": 2.6, "ket_thuc": 5.4},
    {"ma": "s3", "chu": "Let me show you what I found.",
     "bat_dau": 5.4, "ket_thuc": 7.1},
]

#: 🔴 **Ban ghi THAT cua luot nghiem thu 09/09**, chep nguyen van tu
#:    `docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json` (khoa
#:    `luot[].asr.van`). Ca HAI preset deu nhan dung sau cau nay, va do la
#:    diem mau chot: `giu_hinh` hong ba lan, `cat_thong_minh` xong ngay lan
#:    dau — **cung mot dau vao**.
#:
#: ⚠️ Moc thoi gian la UOC LUONG (2,5 tu/giay), khong phai so do duoc: ban
#:    chung cu khong luu `bat`/`ket`. Chung chi can DUONG (khac 0,0) de
#:    `thoi_luong_giay` trong loi nhac giong hang that; doan mau ngan cua
#:    buoc (1) de ca sau doan o 0,0 va do la mot khac biet co the ke.
DOAN_THAT = []
_moc = 0.8
for _i, _chu in enumerate([
    "Good morning everyone, and welcome to the workshop on video localization.",
    "Thank you.",
    "Can you show us how the first example actually works in practice?",
    "Of course.",
    "The system reads the picture first, and only then decides what to keep.",
    "That is a much better order than translating everything before looking at it.",
]):
    _dai = round(max(0.6, len(_chu.split()) / 2.5), 2)
    DOAN_THAT.append({"ma": f"s{_i + 1}", "chu": _chu,
                      "bat": _moc, "ket": round(_moc + _dai, 2)})
    _moc = round(_moc + _dai + 1.2, 2)


def _nhan_loi(exc: BaseException) -> str:
    s = str(exc)
    t = s.lower()
    if "rong" in t:
        return "rong"
    if "json hong" in t or "Expecting" in s:
        return "json_hong"
    if "ban" in t:
        return "ban"
    # ⛔ GIU nguyen van thong diep. Ban dau ham nay chi tra ve TEN LOP loi, va
    #    luot do dau tien ra `loi_khac:AiError` 15/15 — mot nhan khong noi duoc
    #    gi. Thu cuu duoc luot ay la mot con so KHAC: **0,0 giay**, tuc no chua
    #    tung cham mang. Mot nhan lop loi khong phan biet duoc "model tra sai"
    #    voi "chua goi duoc model".
    return f"loi_khac:{type(exc).__name__}: {s[:90]}"


def _mo_db():
    """CSDL tam DA NAP KHOA tu pool that — dung khuon `asv_e2e.nap_khoa_pool`.

    🔴 Ban dau toi truyen `db=None` cho `ai.goi`, va ca 30 luot hong trong
       **0,0 giay** voi `AiError`. `dieu_phoi.goi` khong tra duoc pool khoa khi
       khong co phien CSDL, nen no hong TRUOC khi cham mang.

    ⛔ Va cong cu khi ay ket luan "CA HAI cung hong => loi o MAY B" — mot ket
       luan ve mot thu chua he duoc goi. Con so cuu duoc no la **thoi luong**,
       khong phai nhan loi.

    Chep sang CSDL RIENG (khong ghi vao pool that) nen bo dem `last_used_at`/
    `error_count` cua luot do khong lam ban thong ke khoa production.
    """
    import tempfile

    tam = pathlib.Path(tempfile.mkdtemp(prefix="ltt_do_on_dinh_")) / "do.db"
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tam.as_posix()}"
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())

    sys.path.insert(0, str(GOC))
    from tests.fixtures import asv_e2e

    so = asv_e2e.nap_khoa_pool(db)
    db.commit()
    print(f"  [OK] nap {so} dong khoa `ltt_llm` tu pool that (chi doc)")
    print()
    if not so:
        print("  [!!] Pool that khong co khoa `ltt_llm` nao dung duoc. Dung.")
    return db, so


def _mot_luot(db, ten: str, thao_tac, messages,
              tran: int = 0) -> tuple[str, float, str]:
    """Tra ve `(nhan, giay, chan_doan)`.

    ⛔ `chan_doan` khong phai trang tri. Luot 09/09 chet ba lan voi dung mot
       dong *"model tra ve rong"*, va cau do khong phan biet duoc "may B chet"
       voi "model tieu het `max_tokens` vao khoi suy nghi roi khong con cho de
       tra loi". Hai truong phan biet duoc chung — `finish_reason` va do dai
       `suy_nghi` — DA nam san trong `cong_vlm.KetQuaChat`; cho tro la
       `ai.goi` tung vut ca hai di. Nay no giu lai, nen phep do nay doc duoc.
    """
    from apps.auto_scan_video import ai

    t0 = time.monotonic()
    kq = {}
    try:
        kq = ai.goi(db, thao_tac, messages, max_tokens=int(tran or 0))
        # ⭐ `doc_ket_qua`, KHONG phai `doc_json(kq.get("noi_dung"))`: duong thu
        #    hai chinh la duong lam mat dau vet.
        ai.doc_ket_qua(kq, thao_tac)
        nhan = "ok"
    except Exception as exc:                                 # noqa: BLE001
        nhan = _nhan_loi(exc)
    sd = kq.get("su_dung")
    nd = str(kq.get("noi_dung") or "")
    cd = (f"fr={kq.get('finish_reason') or '-':<10s} "
          f"nghi={len(kq.get('suy_nghi') or ''):>6d}ky_tu "
          f"ra={getattr(sd, 'token_ra', 0) or 0:>6d}tok "
          f"noi_dung={len(nd):>6d}ky_tu")
    # ⭐ IN NGUYEN VAN noi dung khi hong. Mot phep do RE noi duoc nhieu
    #    hon mot ti le hong, vi HAI hinh dang khac han nhau deu ra cung
    #    mot dong `LuocDoSai`:
    #
    #      `noi_dung` RONG        -> model chua thoat khoi khoi suy nghi
    #      `noi_dung` la JSON CUT -> model da bat dau tra loi roi bi cat
    #
    #    Cai thu hai con noi them mot dieu: thu tu la SUY NGHI TRUOC, NOI
    #    DUNG SAU, nen moi lan cham tran deu cat vao dung phan mang y
    #    nghia — va do la ly do nang tran sua duoc, con doi parser thi
    #    khong.
    #
    # ⚠️ Cat 200 ky tu: mot phan hoi hop le dai 1.000+ ky tu se lam
    #    ngap ban ghi, con 200 thi du de thay no cut o dau.
    if nhan != "ok":
        tho = nd[:200].replace("\n", " ")
        cd += f"\n           NGUYEN VAN[:200] >>>{tho}<<<"
    return nhan, time.monotonic() - t0, cd


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vong", type=int, default=15,
                    help="so vong; moi vong goi CA HAI thao tac (mac dinh 15)")
    args = ap.parse_args()

    if not str(os.environ.get("LTT_ASV_POOL_URL", "")).strip():
        print("BO QUA: chua co LTT_ASV_POOL_URL. Chay qua "
              "`setup\\do_on_dinh.ps1` (nang quyen).")
        return 0

    db, so_khoa = _mo_db()
    if not so_khoa:
        return 1

    from apps.auto_scan_video import ai, long_tieng

    lnhac_nghi = long_tieng.loi_nhac(
        DOAN_MAU, tat_ca=DOAN_MAU, ngon_ngu_goc="en",
        dac_diem_giong={"gioi_tinh": "nam", "toc_do": "vua"})
    # ⛔ `rut_ngan_cho_vua` DA ra khoi bang bien the o buoc (2), va viec bo no
    #    la mot QUYET DINH chu khong phai mot lan quen. Buoc (1) da do no 0/15
    #    hong; giu lai la tra ba phut may B moi vong cho mot cau hoi da co dap
    #    an. Bien so cua buoc nay la TRAN, va doi chung cua no phai la cung mot
    #    loi nhac o mot tran khac — khong phai mot thao tac khac.

    # ⛔ Doi chung o buoc (2) KHONG con la mot thao tac khac — no la CUNG mot
    #    thao tac voi DAU VAO NGAN, tuc dung cai da do 0/15 o buoc (1). Doi mot
    #    bien so moi lan do la cach duy nhat de ket luan noi duoc ve bien do.
    lnhac_that = long_tieng.loi_nhac(
        DOAN_THAT, tat_ca=DOAN_THAT, ngon_ngu_goc="en",
        dac_diem_giong={"gioi_tinh": "nam", "toc_do": "vua"})
    # ══════════════════════════════════════════════════════════════════════
    #  BIEN SO CUA BUOC (2) LA **TRAN TOKEN RA**, khong phai do dai dau vao.
    # ══════════════════════════════════════════════════════════════════════
    #
    # 🔴 Do duoc tu so ke cua luot XANH (`cat_thong_minh`, 09/09):
    #
    #        chuyen_loi_thoai   MOT luot   3.985 token (vao+ra)
    #        tran cua 'job'                4.096
    #
    #    Tuc luot THANH CONG di het **97,3%** ngan sach. Luot `giu_hinh` nhan
    #    dung cung ban ghi ay va hong ba lan. Voi mot model co khoi suy nghi
    #    (cong chay `--reasoning-format deepseek`), do dai suy nghi la mot bien
    #    NGAU NHIEN — nen mot bien do 3% la mot dong xu, khong phai mot bien an
    #    toan.
    #
    # ⛔ Va chu thich dau tep nay tung ghi *"max_tokens = 32.768 nen TRAN khong
    #    phai nguyen nhan"*. Con so 32.768 la tran cua cua **stream**;
    #    `ai.tran_token_ra()` doc cua **job** = **4.096**. Mot gia dinh khong
    #    do, viet ra nhu mot su that, da loai bo dung nguyen nhan that trong
    #    ba phien lien tiep.
    #
    # ⭐ DOI CHUNG o day la CUNG mot loi nhac voi tran RONG. Neu tran la nguyen
    #    nhan thi ban 4.096 hong con ban 32.768 khong hong — va `token_ra` cua
    #    ban rong noi ra model THUC SU can bao nhieu.
    # ⚠️ 12.288 chu khong phai 32.768: mot luot sinh het 32k token o ~65
    #    tok/s la ~8 phut. 12.288 van gap ba lan tran hien hanh - du de
    #    thay model CAN bao nhieu - ma chan tren ~3 phut moi luot.
    tran_job = ai.tran_token_ra()
    cap = [("THAT/tran-job", ai.CHUYEN_LOI_THOAI, lnhac_that, tran_job),
           ("THAT/tran-rong(DC)", ai.CHUYEN_LOI_THOAI, lnhac_that, 12288),
           ("NGAN/tran-job(DC)", ai.CHUYEN_LOI_THOAI, lnhac_nghi, tran_job)]
    print(f"  tran token ra cua cua 'job' = {tran_job:,}")
    for _t, _tt, _m, _tr in cap:
        _n = sum(len(str(x.get("content") or "")) for x in _m)
        print(f"  {_t:22s} vao ~{_n / 4.5:>6,.0f} tok   tran ra {_tr:>7,}")
    print()

    ket: dict[str, collections.Counter[str]] = {
        t: collections.Counter() for t, _, _, _ in cap}
    giay: dict[str, list] = {t: [] for t, _, _, _ in cap}

    print(f"do {args.vong} vong, moi vong goi CA HAI (xen ke)\n")
    for i in range(args.vong):
        for ten, tt, msg, tran in cap:
            r, s, cd = _mot_luot(db, ten, tt, msg, tran)
            ket[ten][r.split(":")[0]] += 1
            giay[ten].append(s)
            # In CA thong diep. Va `giay` o day khong phai trang tri: mot
            # luot hong trong 0,0s la mot luot CHUA GOI, khac han mot luot
            # goi roi nhan phan hoi xau.
            print(f"  vong {i+1:>2}  {ten:26s} {s:6.2f}s  {cd}  {r[:60]}")

    print("\n" + "=" * 68)
    for ten, _, _, _ in cap:
        c = ket[ten]
        tong = sum(c.values())
        hong = tong - c.get("ok", 0)
        g = sorted(giay[ten])
        print(f"\n{ten}")
        print(f"  ket qua   : {dict(c)}")
        print(f"  ti le hong: {hong}/{tong} = {100*hong/max(1,tong):.0f}%")
        print(f"  giay      : p50={statistics.median(g):.1f}  max={g[-1]:.1f}")

    a, b = ket["THAT/tran-job"], ket["THAT/tran-rong(DC)"]
    ha = sum(a.values()) - a.get("ok", 0)
    hb = sum(b.values()) - b.get("ok", 0)
    print("\n" + "=" * 68)
    print("KET LUAN:")
    # ⛔ TRUOC khi ket luan ve may B: neu MOI luot deu hong trong ~0 giay thi
    #    khong luot nao cham mang, va moi ket luan ve may B deu vo can cu.
    nhanh = [g for gs in giay.values() for g in gs]
    if nhanh and max(nhanh) < 1.0:
        print("  [!!] MOI luot hong trong < 1 giay => KHONG luot nao cham mang.")
        print("     Loi nam TRUOC cua goi (cau hinh/khoa/CSDL), KHONG o may B.")
        print("     Doc thong diep o tren, dung ket luan ve may B.")
        return 0
    if ha and not hb:
        print("  Chi ban TRAN-JOB hong; cung loi nhac voi TRAN RONG thi khong.")
        print("  => Nguyen nhan la TRAN TOKEN RA 4.096, khong phai may B va")
        print("     khong phai loi nhac. Doc cot `ra=` cua ban tran rong de")
        print("     biet model THUC SU can bao nhieu token.")
    elif ha and hb:
        print("  CA HAI tran cung hong => tran KHONG phai nguyen nhan; doc cot")
        print("  `fr=` truoc khi ket luan ve may B.")
    elif not ha and not hb:
        print("  KHONG luot nao hong o ca hai tran. Tran chua bi cham trong")
        print("  lo do nay - doc cot `ra=` xem no cach 4.096 bao xa.")
    else:
        # ⛔ MOI chuoi IN RA phai thuan ASCII. Chu thich thi khong sao.
        #
        #    Do that 09/09: dong ket luan chua `(2)` (luc do la mot ky tu
        #    Unicode) va tien trinh CHET giua cau voi `UnicodeEncodeError` —
        #    console Windows la cp1252 khi dau ra bi chuyen huong. Ca luot do
        #    15 phut ra `EXITCODE=1` va mat dong ket luan, du 30/30 luot deu
        #    thanh cong. Mot cong cu do chet vi IN mot ky tu la mot cong cu
        #    vut bo chinh phep do cua no.
        print("  Chi DOI CHUNG hong - nguoc gia thuyet, doc lai truoc khi ket.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
