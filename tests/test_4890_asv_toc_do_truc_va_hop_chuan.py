"""ASV — `toc_do != 1`: hai con bug mot lan chay THAT phoi bay (27/09).

🔴 **Vi sao cac bai o day ton tai.** Bo test cu **chua bao gio** chay mot luot
   `toc_do != 1` tren worker that: moi phep nghiem thu deu de `toc_do = 1`, va o
   `toc_do = 1` thi CA HAI con bug duoi day **vo hinh** — mot cai vi `setpts`
   ⛔ khong duoc phat, mot cai vi phep chia cho `1,0` ⛔ khong doi gi.

   Lan chay `asvr_3059dc3d77f0456bb3a3ab3705b6fae` (27/09, preset
   `smart_localize`, `toc_do = 1,25`, nguon 45,121 s / 30 fps / 1353 khung) lam
   `qc` do **bon** muc: T2, T4, T17, T18. Hai trong bon co goc o day.

⭐ Ho loi chung: **mot dai luong duoc ap HAI LAN, hoac ⛔ khong ap lan nao** — va
   ca hai chi lo ra khi he so khac `1`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (bien_tap, giai_doan_hinh_anh as gdha,  # noqa: E402
                                  giai_doan_qc)

#: Lan chay THAT `asvr_3059dc3d77f0456bb3a3ab3705b6fae` (27/09, preset
#: `smart_localize`, `toc_do = 1,25`): nguon 45,121 s / 30 fps / 1353 khung,
#: ⛔ khong cat canh nao, tep giao 36,077 s.
#:
#: ⛔ Ban dung GD1 day du cua lan chay ay ⛔ khong con o day: tu B6 moi khang dinh
#:    ve toc do do tren lenh GD2, va mot fixture ⛔ khong ai doc thi se muc.
NGUON_S = 45.121
FPS_VAO = 30.0


def _argv(toc: float) -> list[str]:
    """Lenh GIAI DOAN 2 — noi `toc_do` duoc ap tu B6 (27/09).

    🔴 **Truoc B6 ham nay dung lenh GD1 (`ket_xuat.dung_lenh`).** `toc_do` da
       chuyen xuong cuoi GD2, nen moi khang dinh ve `setpts`/`atempo`/`-r` phai
       do o day — do o GD1 thi chung se xanh mai mai bang cach ⛔ khong do gi.
    """
    return gdha.dung_lenh(
        "gd1.mp4", "ra.mp4", khoang=[(0.0, NGUON_S)], bo_ma_hoa="h264_nvenc",
        ffmpeg_bin="ffmpeg", thoi_luong_ra=NGUON_S, tien_do=False,
        fps_vao=FPS_VAO,
        bien_tap=({"toc_do": toc} if toc != 1.0 else None),
        rong_nguon=1920, cao_nguon=1080)


# ══════════════════════════════════════════════════════════════════════════════
#  Bug 1 — `-fps_mode passthrough` lam dong ra ⛔ KHONG HOP CHUAN
# ══════════════════════════════════════════════════════════════════════════════

def test_4890_fps_mode_la_LUA_CHON_DA_DO_chu_khong_phai_mac_dinh():
    """🔴 `-fps_mode passthrough` **cong** voi `setpts=PTS/toc` cho mot dong ra
    co 1351 khung nhung chi **1081 moc thoi gian** — 270 khung xep chong cach nhau
    1 tick, tuc 270 DTS **TRUNG**. Do lam T17 do (269 loi giai ma) va T18 do
    (VMAF 53,8 / nguong 75, min **1,45** — dau hieu LECH THOI GIAN, ⛔ khong phai
    mat chat luong deu).

    ⚠️ Chu thich cu khai no ra *"VFR 31,25 fps"*. Do duoc thi ⛔ khong phai VFR:
       `avg_frame_rate = 40530/1081` va `r_frame_rate = 60/1` — hai con so ⛔ khong
       khop nhau, dau hieu cua moc ⛔ khong bieu dien duoc.

    ⭐ Va no ⛔ khong chua duoc cai no duoc them de chua. Do 27/09 tren lan chay
       that, do **CA HAI** cot:

         lua chon                      khung   hinh s   troi ms   loi DTS
         passthrough (ban 22/09)        1351   36,0333     43,7       269
         ⛔ khong passthrough           1082   36,0667     10,3         0
         fps=37,5 + timescale 15000     1352   36,0530     24,0         0

       `passthrough` **GAY** troi 43,7 ms; bo no thi troi 10,3 ms (duoi mot khung
       30 fps). Ban 22/09 do **troi** roi sua, va ⛔ khong ai do **tinh hop chuan**
       sau do — ho `moi can gat do rieng, tong chua ai do`.
    """
    argv = _argv(1.25)
    assert "-fps_mode" not in argv, (
        f"`-fps_mode` da duoc thay bang `-r` (27/09): {argv}")
    assert "-r" in argv, (
        "de trong la nhan mac dinh `auto`, ma tai lieu ffmpeg dinh nghia `auto` "
        "bang CO CHE (*chooses between cfr and vfr depending on muxer "
        "capabilities*) chu ⛔ khong bang BAT BIEN. Va do duoc: `auto` lam noi "
        "dung lech 40 ms tren fixture test_2064. Khai `-r` tuong minh.")
    # ⭐ Nhip ra = nhip VAO x toc — giu HET khung, moc roi dung luoi.
    assert argv[argv.index("-r") + 1] == "37.5", argv
    # 🔑 Va `-t` phai CHIA cho toc: 45,121 / 1,25 = 36,096800. Thieu phep chia
    #    thi `-t` dai hon tep thuc va ⛔ khong ghim gi (toc > 1) — hay CAT CUT
    #    tep (toc < 1).
    assert argv[argv.index("-t") + 1] == "36.096800", argv


def test_4890_duong_toc_do_1_KHONG_doi_mot_byte():
    """⭐ Ve DOI CHUNG. Khoi bi bo CHI chay khi `toc_do != 1`, nen bo no phai
    ⛔ khong doi gi o duong `toc_do = 1` — va duong do la duong cua **moi** lan
    chay hom nay. Mot ban sua lam doi ca hai duong la mot ban sua rong hon loi.
    """
    argv = _argv(1.0)
    assert "-fps_mode" not in argv, (
        "duong `toc_do = 1` ⛔ khong duoc doi: khoi nay CHI thuoc duong doi toc do")
    assert "-r" not in argv, (
        "⛔ khong doi toc do thi ⛔ khong co gi bat bo ma hoa sap lai nhip")
    # ⭐ `-t` VAN co, nhung ⛔ KHONG chia: 45,121 s dung bang do dai sau cat.
    assert argv[argv.index("-t") + 1] == "45.121000", argv
    if "-filter_complex" in argv:
        loc = argv[argv.index("-filter_complex") + 1]
        assert "atempo" not in loc, loc
        assert "setpts=PTS/" not in loc, loc


def test_4890_toc_do_khac_1_VAN_phat_setpts_va_atempo():
    """⛔ Doi chung cho bai tren: neu bo `passthrough` ma lam mat luon phep doi
    toc do thi hai bai kia van xanh — va san pham thi ⛔ khong con tang toc nua.
    """
    argv = _argv(1.25)
    assert "-filter_complex" in argv, argv
    loc = argv[argv.index("-filter_complex") + 1]
    buoc = loc.split(";")
    # ⭐ Va chung phai la HAI BUOC CUOI: moi buoc tren chung DOC moc thoi gian
    #    (cat theo khoang, dot phu de theo moc), nen dat toc do truoc bat chung
    #    doi truc theo — dung cai gia ma T2/T17 da tra.
    assert "setpts=PTS/1.2500" in buoc[-2], loc
    assert "atempo=1.2500" in buoc[-1], loc


# ══════════════════════════════════════════════════════════════════════════════
#  Bug 2 — T2 chia `toc_do` HAI LAN
# ══════════════════════════════════════════════════════════════════════════════

KE_HOACH = {"tong_ms": 45121}

#: Ke cat cua `image_finish` cho lan chay that: ⛔ khong cat gi.
#:
#: 🔴 **Tu B6 (27/09) `thoi_luong` o truc NGUON — 45,121 s, ⛔ khong 36,077.**
#:    `render` thoi doi moc thoi gian, nen tep ma GD2 cat dai dung bang nguon.
#:    Do chinh la ban sua TAN GOC cho T2: truoc B6 hai nhanh cua
#:    `_thoi_luong_mong_doi` o hai TRUC khac nhau, nen mot phep chia dat ngoai
#:    nhanh thi sai mot nhanh, dat trong nhanh thi ⛔ khong ai doc noi hop dong.
GOI_KE_CAT = {"cat": [], "thoi_luong": 45.121}


def test_4890_T2_mong_doi_KHONG_chia_toc_do_hai_lan():
    """🔴 `_thoi_luong_mong_doi` tra HAI TRUC khac nhau tuy nhanh, va nguoi goi
    ap `moc_ban_ra` cho CA HAI ⇒ nhanh "co ke cat" bi chia `toc_do` LAN THU HAI.

    So do lan chay that (`asvr_3059dc3d`, nguon 45,121 s, `toc_do = 1,25`):
        tep giao     = 36,077 s
        compose hua  = 36,097 s   (= 45,121 / 1,25 — DUNG)
        T2 mong doi  = 28,862 s   (= 36,077 / 1,25 — SAI)
        lech         =  7,215 s   ⇒ T2 **hong tren mot ban giao DUNG**

    ⭐ Chot bang TINH CHAT, ⛔ khong bang con so 36,077: mong doi phai nam **tren
       truc cua tep duoc do**, nen no phai xap xi do dai tep — ⛔ khong phai do dai
       tep chia thêm mot lan nua.
    """
    bt = {"toc_do": 1.25}
    mong_doi = giai_doan_qc._thoi_luong_mong_doi(KE_HOACH, GOI_KE_CAT, bt)

    # ⭐ Chot bang TINH CHAT: mong doi phai xap xi do dai TEP GIAO that (36,077 s),
    #    vi do la tep ma cong nay dang do. `~28,86` = chia hai lan; `~45,12` =
    #    ⛔ khong chia lan nao.
    assert mong_doi == pytest.approx(36.077, abs=0.05), (
        f"mong doi {mong_doi:.3f}s — tep giao dai 36,077s; ~28,86 = chia HAI lan, "
        f"~45,12 = ⛔ KHONG chia lan nao")
    # ⛔ Ve DOI CHUNG: he so 1,0 thi hai truc trung nhau, nen mong doi = do dai
    #    sau cat. Neu con so nay cung ra 36,08 thi bai tren dang chot mot HANG SO
    #    chu ⛔ khong chot phep chia.
    assert giai_doan_qc._thoi_luong_mong_doi(
        KE_HOACH, GOI_KE_CAT, {"toc_do": 1.0}) == pytest.approx(45.121, abs=0.01)


def test_4890_T2_khong_co_ke_cat_VAN_doi_truc():
    """⭐ Nhanh con lai: ⛔ khong co ke cat thi mong doi la do dai NGUON, tuc truc
    BIEN TAP — va no PHAI duoc doi sang truc ban ra. Truoc ban sua, phep doi ay
    nam o nguoi goi; nay nam trong ham. Bo quen no thi T2 hong theo chieu NGUOC
    (mong doi 45,1 s cho mot tep 36,1 s).
    """
    mong_doi = giai_doan_qc._thoi_luong_mong_doi(KE_HOACH, {}, {"toc_do": 1.25})
    assert mong_doi == pytest.approx(45.121 / 1.25, abs=0.01), mong_doi
    # `toc_do = 1` (hay vang mat) thi bang chinh do dai nguon.
    assert giai_doan_qc._thoi_luong_mong_doi(
        KE_HOACH, {}, None) == pytest.approx(45.121, abs=0.01)


def test_4890_hai_nhanh_cua_mong_doi_CUNG_MOT_TRUC():
    """🔴 Bat bien that su dang chot: **hai nhanh tra cung MOT truc.**

    Con bug ⛔ khong phai "mot phep chia bi lam hai lan" — no la "mot ham tra hai
    dai luong khac truc tuy nhanh", va phep chia hai lan chi la **hau qua**. Chot
    dung tinh chat do: voi cung mot do dai vat ly, hai nhanh phai ra cung so.
    """
    bt = {"toc_do": 1.25}
    # Nguon 45,121 s, ⛔ khong cat gi => tep ra dai 45,121/1,25 = 36,097 s.
    a = giai_doan_qc._thoi_luong_mong_doi({"tong_ms": 45121}, {}, bt)
    # ⭐ Cung tinh huong, dien ta bang mot ke cat "giu het" — va tu B6 ke cat
    #    o CUNG truc NGUON, nen con so dien ta no la 45,121 chu ⛔ khong
    #    `45,121 / 1,25`. Do CHINH LA dieu bai nay chot.
    b = giai_doan_qc._thoi_luong_mong_doi(
        {"tong_ms": 45121}, {"cat": [], "thoi_luong": 45.121}, bt)
    assert a == pytest.approx(b, abs=0.01), (
        f"hai nhanh mo ta CUNG mot tinh huong ma ra hai so: {a:.3f} vs {b:.3f} "
        f"— chung dang o hai TRUC khac nhau")


def test_4890_he_so_toc_do_doc_tu_MOT_noi():
    """⛔ Doi chung nho: `moc_ban_ra` va `_thoi_luong_mong_doi` phai dung cung mot
    ham doc he so, neu khong thi hai cho doc `toc_do` va mot cho co the lech."""
    assert bien_tap.toc_do({"toc_do": 1.25}) == 1.25
    assert bien_tap.toc_do(None) == 1.0
    assert bien_tap.toc_do({}) == 1.0


def test_4890_CHO_GOI_khong_doi_truc_lan_nua():
    """🔴 **Bai nay ton tai vi ba bai tren KHONG bat duoc con bug that.**

    Do 27/09: tiem lai chinh xac ban cu o `chay()` — `moc_ban_ra(_thoi_luong_
    mong_doi(ke_hoach, goi_kc), bien_tap)` — thi ba bai tren **VAN XANH 7/7**.
    Vi chung goi `_thoi_luong_mong_doi` **truc tiep** va truyen `bien_tap` vao,
    nen chung do HOP DONG CUA HAM, ⛔ khong do CHO GOI. Con bug thi o cho goi.

    ⇒ Dung ho loi *"pham vi phep do hep hon loi tuyen bo"*, va no xay ra ngay
      trong loat bai duoc viet de sua ho loi ay. Ghi lai chu ⛔ khong che.

    ⭐ Phep do nay doc CAY AST cua `chay`, ⛔ khong `in` van ban ma nguon: mot bai
       chot chuoi `"moc_ban_ra"` se do vi mot **chu thich** nhac ten no — dung cai
       bao dong gia ma `2a6f85ed` vua phai go o `test_408`.

    Tinh chat duoc chot: trong `chay`, ket qua cua `_thoi_luong_mong_doi` ⛔ KHONG
    duoc di qua mot phep doi truc nao nua. Phep doi truc thuoc VE TRONG ham do.
    """
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(giai_doan_qc.chay))

    goi_mong_doi = [n for n in ast.walk(cay)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "_thoi_luong_mong_doi"]
    assert len(goi_mong_doi) == 1, (
        f"`chay` goi `_thoi_luong_mong_doi` {len(goi_mong_doi)} lan — mot noi "
        f"tra loi mot cau hoi")

    # ⛔ ⛔ Khong duoc BOC no trong mot phep doi truc.
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)):
            continue
        if n.func.id not in ("moc_ban_ra",):
            continue
        raise AssertionError(
            "`chay` goi `moc_ban_ra` — phep doi truc phai nam TRONG "
            "`_thoi_luong_mong_doi`, neu khong thi nhanh 'co ke cat' bi chia "
            "`toc_do` LAN THU HAI va T2 hong tren mot ban giao dung")

    # ⭐ Va no phai truyen `bien_tap` xuong — thieu doi so thu ba thi ham lui ve
    #    `toc_do = 1` va nhanh 'khong co ke cat' hong theo chieu nguoc.
    g = goi_mong_doi[0]
    assert len(g.args) + len(g.keywords) >= 3, (
        "`_thoi_luong_mong_doi` duoc goi ma ⛔ khong truyen `bien_tap` — nhanh "
        "'⛔ khong co ke cat' se doi truc bang he so 1,0")


# ══════════════════════════════════════════════════════════════════════════════
#  Bug 3 — bien du cho codec an mat do chinh xac cua `loudnorm` (T4)
# ══════════════════════════════════════════════════════════════════════════════

def test_4890_bien_cho_codec_KHONG_an_het_do_chinh_xac_cua_loudnorm():
    """🔴 T4 hong tren lan chay that `asvr_3059dc3d` vi `BIEN_CHO_CODEC_DB = 2,0`.

    Bien do ha tran ban phoi xuong `-1,5 - 2,0 = -3,5 dBTP`, va tran ay RANG BUOC
    `loudnorm ... linear=true`: mot gain tuyen tinh nao lam vuot `TP` thi loudnorm
    **lui ve che do dong**, va che do dong sai ~1 LU. Ket qua: ban phoi ra
    `-15,24 LUFS` / dich `-14,0 ± 1,0` ⇒ **ngoai khoang**.

    ⭐ Do tren CHINH ba luot cua san pham voi du lieu THAT cua lan chay do:

        BIEN   tran phoi   LUFS ra   dinh giao   so vong ghim
         2,0      -3,5      -15,0      -3,35          1        <- HONG T4
         1,0      -2,5      -14,8      -2,38          1
         0,5      -2,0      -14,6      -1,92          1        <- dang dung
         0,0      -1,5      -14,5      -1,78          2

    🔑 **Bat bien duoc chot o day, va no la LY DO chu ⛔ khong phai con so:**
       moi dB bien du la mot dB **do chinh xac am luong bi danh doi truoc khi do
       bat cu thu gi**. Va ta ⛔ khong can danh doi no, vi `ghim_tran_phoi` MA HOA
       THU roi **do** vot lo that va ha tran dung phan can — do la co che, bien du
       chi la mot phep toi uu SO VONG.

       ⇒ Bien du phai nho hon `1,0 dB`. Lon hon the la quay lai danh doi T4 cho
         mot thu da co nguoi do.

    ⚠️ Bai nay ⛔ **khong** chot `BIEN_CHO_CODEC_DB == 0,5`: con so dung phu thuoc
       vot lo cua bo ma hoa, va do la thu **do duoc** chu ⛔ khong phai hang so cua
       ta. No chot cai da hong: bien du an het dai luong ma T4 dang do.
    """
    from apps.auto_scan_video import am_master, tach_tieng

    assert am_master.BIEN_CHO_CODEC_DB > 0, (
        "bien du = 0 lam vong ghim phai chay them mot vong tren hau het lan chay")
    assert am_master.BIEN_CHO_CODEC_DB < 1.0, (
        f"bien du {am_master.BIEN_CHO_CODEC_DB} dB an qua nhieu do chinh xac am "
        f"luong: no ep `loudnorm ... linear=true` lui ve che do dong (sai ~1 LU) "
        f"va T4 (dich {tach_tieng.LUFS_DICH} ± {tach_tieng.LUFS_DUNG_SAI}) hong "
        f"tren mot ban phoi khong sai gi. Vot lo THAT do bang "
        f"`ghim_tran_phoi`, ⛔ khong doan truoc bang hang so nay.")

    # ⭐ Ve DOI CHUNG: luoi an toan phai TON TAI, neu khong thi ha bien du la
    #    danh cuoc. `ghim_tran_phoi` phai co du vong de sua mot vot lo lon.
    assert am_master.SO_VONG_GHIM >= 2, (
        "ha bien du chi an toan khi vong ghim con cho de sua; mot vong thi "
        "⛔ khong con co che nao bat vot lo")
    assert am_master.GHIM_LUI_THEM_DB > 0, (
        "vong ghim ⛔ khong lui them thi no co the dung mai tren bien")


def test_4890_tran_phoi_luon_THAP_hon_tran_giao():
    """⛔ Doi chung cho bai tren: neu ai do ha `BIEN_CHO_CODEC_DB` ve so AM de lam
    bai tren xanh thi tran ban phoi se CAO hon tran giao — vong ghim khi do bat
    dau tu mot cho da vuot, va T5 thanh trong tai duy nhat."""
    from apps.auto_scan_video import am_master

    assert am_master.dinh_that_phoi_db() < am_master.dinh_that_db(), (
        f"tran ban phoi {am_master.dinh_that_phoi_db()} ⛔ khong duoc cao hon hay "
        f"bang tran giao {am_master.dinh_that_db()}")


# ══════════════════════════════════════════════════════════════════════════════
#  T18 TAT co chu dich (chu du an chot 27/09)
# ══════════════════════════════════════════════════════════════════════════════

def test_4890_T18_mac_dinh_TAT_va_NOI_RO_vi_sao(monkeypatch):
    """🔴 Chu du an chot TAT T18 (27/09) sau khi dieu phoi neu ro cai gia: no la
    cong DUY NHAT canh chat luong hinh sau ma hoa lai.

    ⚠️ Ly le: con so cua no hien **⛔ khong dang tin**. Do duoc tren BA luot chay
       that lien tiep: `trung_binh = 53,783` **bit-identical**, `nho_nhat = 1,452`
       — mot VMAF 1,45 la "gan nhu ⛔ khong giong gi", ⛔ khong the la ton that cua
       bo ma hoa o `cq = 28`. Goc: tham chieu **1083 khung / 30 fps** vs ban giao
       **1351 khung / 37,5 fps**, tuc phep SO SANH sai. Cong bao dong vi chinh no
       hong thi no chan MOI ban giao co doi toc do. Cong them ~32 s moi job.

    ⭐ Bai nay chot BON trang thai phan biet duoc, ⛔ khong ba:
        `KHONG_AP_DUNG` + "preset giu hinh"        -> theo thiet ke
        `KHONG_AP_DUNG` + ten bien bat             -> TAT co chu dich  (moi)
        `KHONG_AP_DUNG` + "khong_kha_dung"         -> ⛔ khong do duoc
        `DAT`/`HONG`                                -> da do

       Gop hai cai giua lai thi ⛔ khong ai biet **ai** tat va **bat lai bang gi**
       — dung ho loi `hai trang thai gop thanh mot gia tri` ma ca phien nay sua.
    """
    from apps.auto_scan_video import che_do_render as cdr, giai_doan_qc, qc

    monkeypatch.delenv(giai_doan_qc.BIEN_T18, raising=False)
    assert giai_doan_qc.t18_bat() is False, "T18 phai MAC DINH tat"
    monkeypatch.setenv(giai_doan_qc.BIEN_T18, "1")
    assert giai_doan_qc.t18_bat() is True
    # ⛔ Chi nhan dung "1" — cung khuon voi `giai_doan_qc_ai.bat()`.
    for xau in ("true", "yes", "0", "", " "):
        monkeypatch.setenv(giai_doan_qc.BIEN_T18, xau)
        assert giai_doan_qc.t18_bat() is False, xau

    # ── Bao cao phai NOI RO la "tat", va noi ten bien de bat lai ─────────────
    def _t18(vmaf):
        bc = qc.kiem(
            tt_ra={"thoi_luong": 10.0, "co_video": True, "co_tieng": True,
                   "rong": 640, "cao": 360, "fps": 30.0},
            tt_nguon={"thoi_luong": 10.0, "co_video": True, "co_tieng": True},
            am_luong={"lufs": -14.0, "dinh_that": -2.0},
            ke_hoach={"doan": []}, ban_ke_tieng={"doan": []},
            ban_dung_lop=[], bam_ra="", bam_nguon="",
            che_do_render=cdr.CAT_MA_HOA_LAI, vmaf=vmaf)
        return next(m for m in bc["muc"] if m["ma"] == "T18")

    tat = _t18({"tat": giai_doan_qc.BIEN_T18})
    assert tat["trang_thai"] == qc.KHONG_AP_DUNG, tat
    assert giai_doan_qc.BIEN_T18 in str(tat), (
        f"bao cao ⛔ khong noi ten bien de bat lai: {tat}")

    # ⭐ Ve DOI CHUNG: ca "⛔ khong do duoc" phai RA KHAC — neu hai ca ra cung mot
    #    cau thi bai tren chi chot rang T18 khong DAT, ⛔ khong rang ta phan biet
    #    duoc **vi sao**.
    hong = _t18({"loi": "thieu libvmaf"})
    assert hong["trang_thai"] == qc.KHONG_AP_DUNG
    assert str(hong) != str(tat), (
        "'TAT co chu dich' va '⛔ khong do duoc' ra cung mot bao cao — hai trang "
        "thai gop thanh mot gia tri")

# ══════════════════════════════════════════════════════════════════════════════
#  B6 — hai cai bay cua viec DOI TOC DO xuong GD2 (27/09)
# ══════════════════════════════════════════════════════════════════════════════

def test_4890_B6_REMUX_va_toc_do_la_mot_KHONG_THE__phai_NEM():
    """🔴 **Cai bay lon nhat cua B6, va no IM LANG.**

    Duong remux (`-c copy`) cua GD2 ⛔ khong co bo loc nao, nen `setpts`/`atempo`
    ⛔ khong the ap. Mot lan chay lot vao day voi `toc_do != 1` se giao cho khach
    mot tep **⛔ CHUA doi toc do** — ⛔ khong loi, ⛔ khong log, va dung o thu
    khach phat hien ra truoc ta.

    ⭐ Hai lop chan, va bai nay do CA HAI:
      1. `loc_bien_tap_gd2` GIU `toc_do != 1` ⇒ `co_diem_anh` cua `chay()` khac
         rong ⇒ lan chay ⛔ khong con la `khong_cat` ⇒ ⛔ khong roi vao remux;
      2. `dung_lenh` NEM neu ca hai su that cung toi — vi (1) la mot phep chan o
         CHO GOI, va mot phep chan o cho goi la phep chan ai cung co the quen.

    ⛔ Va `toc_do == 1` phai bi BO khoi ho so GD2: giu no se lam `bien_tap_gd2`
       khac rong tren duong ⛔ khong bien tap gi, tuc bat ma hoa lai mot tep ⛔
       khong co gi doi — lay mot ban kem hon doi lay mot phep tinh vo ich.
    """
    from apps.auto_scan_video import ket_xuat

    # (1) Ho so GD2 phai GIU `toc_do != 1` va BO `toc_do == 1`.
    assert gdha.loc_bien_tap_gd2({"toc_do": 1.25}) == {"toc_do": 1.25}
    assert gdha.loc_bien_tap_gd2({"toc_do": 1.0}) is None
    assert gdha.loc_bien_tap_gd2(None) is None

    # (2) Va cho cuoi cung biet ca hai su that thi NEM.
    with pytest.raises(ket_xuat.KetXuatError, match="sao chép nguyên vẹn"):
        gdha.dung_lenh("a.mp4", "b.mp4", khoang=[(0.0, 8.0)], bo_ma_hoa="",
                       ffmpeg_bin="ffmpeg", tien_do=False,
                       bien_tap={"toc_do": 1.25})

    # ⛔ Ve DOI CHUNG: remux o `toc_do = 1` VAN phai di qua binh thuong — neu
    #    khong thi ban chan tren dang rong hon loi va no vua giet mot duong dung.
    cmd = gdha.dung_lenh("a.mp4", "b.mp4", khoang=[(0.0, 8.0)], bo_ma_hoa="",
                         ffmpeg_bin="ffmpeg", tien_do=False)
    assert cmd[cmd.index("-c") + 1] == "copy", cmd


def test_4890_B6_VAN_TAY_doi_khi_toc_do_doi():
    """🔴 Doi `toc_do` ma van tay ⛔ khong doi thi lan chay sau **dung lai tep cua
    toc do cu** — khach doi tu 1,25 sang 1,5 va nhan lai y nguyen tep truoc.

    ⭐ Tu B6 dieu nay dung THEO CAU TRUC chu ⛔ khong theo mot dong ma rieng:
       `chay()` truyen `bien_tap=bien_tap_gd2` vao `van_tay`, va `bien_tap_gd2`
       nay GIU `toc_do`. Bai nay chot rang chuoi ay ⛔ khong bi cat.
    """
    from apps.auto_scan_video import ke_cat as kc

    ke = kc.chon([], thoi_luong=40.0)
    vt = [gdha.van_tay("gd1", ke, None, "libx264",
                       bien_tap=gdha.loc_bien_tap_gd2(bt))
          for bt in ({"toc_do": 1.0}, {"toc_do": 1.25}, {"toc_do": 1.5})]
    assert len(set(vt)) == 3, (
        "hai he so toc do khac nhau cho CUNG mot van tay ⇒ lan chay sau se "
        "dung lai tep cua he so cu: %r" % (vt,))
