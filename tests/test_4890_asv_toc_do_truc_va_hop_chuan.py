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

from apps.auto_scan_video import bien_tap, giai_doan_qc, ket_xuat  # noqa: E402

#: Ban dung THAT cua lan chay `asvr_3059dc3d` — chep tu artifact `compose`, ⛔ khong
#: dung tay. Giu day du cac truong ma `ket_xuat.dung_lenh` doc.
BAN = {
    "cong_cu": {"ffmpeg": "8.0.1-full_build-www.gyan.dev"},
    "hinh": {
        "bien_tap": {"toc_do": 1.25},
        "bo_ma_hoa": "h264_nvenc",
        "cach_render": "cat_ma_hoa_lai",
        "cao_khung": 1080, "rong_khung": 1920,
        "che_do": "copy",
        "khoa": "asv/u/nguon/x.mp4",
        "khoang_giu": [[0.0, 45.121]],
        "phu_de": None, "vung": [],
    },
    "phien_ban": 2,
    "preset": "smart_localize",
    "ra": {"bitrate_tieng": "192k", "codec_tieng": "aac", "container": "mp4",
           "faststart": True, "thoi_luong_giay": 36.097},
    "schema": 3,
    "tieng": {
        "lop": [{"dat_tai_ms": 51, "he_so_toc": 1.0, "khoa": "a.wav",
                 "ma": "seg_0001"},
                {"dat_tai_ms": 24635, "he_so_toc": 1.0, "khoa": "b.wav",
                 "ma": "seg_0002"}],
        "master": {"khoa": "m.wav"},
        "nen": {"khoa": "n.wav"},
        "so_kenh": 2, "tan_so": 48000,
    },
}


def _argv(toc: float) -> list[str]:
    ban = {**BAN, "hinh": {**BAN["hinh"], "bien_tap": ({"toc_do": toc}
                                                      if toc != 1.0 else None)}}
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="v.mp4", duong_master="m.wav",
        duong_lop=["l0.wav", "l1.wav"], duong_ra="ra.mp4",
        bo_ma_hoa="h264_nvenc")


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
    assert "-fps_mode" in argv, (
        "de trong la nhan mac dinh `auto`, ma tai lieu ffmpeg dinh nghia `auto` "
        "bang CO CHE (*chooses between cfr and vfr depending on muxer "
        "capabilities*) chu ⛔ khong bang BAT BIEN — mot lua chon nhu the doi khi "
        "doi muxer. Khai tuong minh.")
    assert argv[argv.index("-fps_mode") + 1] == "passthrough", argv


def test_4890_duong_toc_do_1_KHONG_doi_mot_byte():
    """⭐ Ve DOI CHUNG. Khoi bi bo CHI chay khi `toc_do != 1`, nen bo no phai
    ⛔ khong doi gi o duong `toc_do = 1` — va duong do la duong cua **moi** lan
    chay hom nay. Mot ban sua lam doi ca hai duong la mot ban sua rong hon loi.
    """
    argv = _argv(1.0)
    assert "-fps_mode" not in argv, (
        "duong `toc_do = 1` ⛔ khong duoc doi: khoi nay CHI thuoc duong doi toc do")
    # ⚠️ O `toc_do = 1` + `khoang_giu` phu het, duong nay ⛔ khong can mot do thi
    #    loc nao ca — nen `-filter_complex` co the VANG. Do la hanh vi dung, va
    #    bai nay chot dieu con lai: neu CO do thi loc thi trong do ⛔ khong co
    #    phep doi toc do nao.
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
    assert "setpts=PTS/1.2500" in loc, loc
    assert "atempo=1.2500" in loc, loc


# ══════════════════════════════════════════════════════════════════════════════
#  Bug 2 — T2 chia `toc_do` HAI LAN
# ══════════════════════════════════════════════════════════════════════════════

KE_HOACH = {"tong_ms": 45121}

#: Ke cat cua `image_finish` cho lan chay that: ⛔ khong cat gi, nen `thoi_luong_ra`
#: bang do dai tep ma `render` giao — tuc DA o tren truc SAU `toc_do`.
#: `cat` rong = ⛔ khong cat gi; `thoi_luong` = do dai tep ma `render` giao.
GOI_KE_CAT = {"cat": [], "thoi_luong": 36.077}


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

    assert mong_doi == pytest.approx(36.077, abs=0.01), (
        f"mong doi {mong_doi:.3f}s — tep giao dai 36,077s; neu ra ~28,86 thi "
        f"`toc_do` da duoc ap hai lan")
    # ⛔ Ve DOI CHUNG: he so 1,0 phai cho CUNG con so — neu khong thi bai tren
    #    chi chot rang ta da bo phep chia, ⛔ khong rang ta bo dung mot lan.
    assert giai_doan_qc._thoi_luong_mong_doi(
        KE_HOACH, GOI_KE_CAT, {"toc_do": 1.0}) == pytest.approx(36.077, abs=0.01)


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
    # Cung tinh huong, nhung dien ta bang mot ke cat "giu het" tren truc BAN RA.
    b = giai_doan_qc._thoi_luong_mong_doi(
        {"tong_ms": 45121},
        {"cat": [], "thoi_luong": 45.121 / 1.25},
        bt)
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
