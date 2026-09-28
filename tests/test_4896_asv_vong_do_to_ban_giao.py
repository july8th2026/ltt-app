"""ASV T4 (28/09) — DO TO cua ban giao la mot VONG DO-VA-SUA, ⛔ khong mot hang so.

🔴 **Vi sao bo kiem cu ⛔ khong bat duoc.** `test_2015` chot vong ghim DINH,
   `test_4890` chot rang `BIEN_CHO_CODEC_DB` nam trong `(0; 1)`, `test_465` chot
   hai luot `loudnorm`. Ca ba deu dung — va ⛔ khong bai nao hoi *"ban giao ra
   dung -14 LUFS khong"*: T4 truoc ban nay duoc dam bao bang **mot hang so hieu
   chinh tay** (`BIEN_CHO_CODEC_DB`, 2,0 -> 0,5 -> 0,25 trong hai ngay), va mot
   hang so hieu chinh tren hai mau ⛔ khong phai mot vong dieu khien: no xanh cho
   toi mau thu ba. Mau thu ba da den — `T1a-bis` (27/09) ban giao **-15,44 LUFS**.

⇒ Nam menh de duoc chot o day:
   1. `loc_han_dinh` co mot khau BU DO TO, no nam TRUOC bo han va SAU `aformat`
      float — hai thu do la ca thiet ke (xem `_buoc_do_to` / `loc_han_dinh`);
   2. `_buoc_do_to` co VUNG CHET, co TRAN, va co nguong buoc — tuc vong DUNG;
   3. hai ban dung **noi dung khac nhau** cho do to trong CUNG khoang
      `-14,0 ± 1,0` (⛔ khong chot mot GIA TRI: chot mot gia tri la chot cach go);
   4. ve DOI CHUNG: mot ban QUA NHO va mot ban QUA TO deu duoc keo VE khoang;
   5. mot ca ⛔ khong hoi tu duoc thi **thoat o tran, co ghi lai** — ⛔ khong treo,
      va ⛔ khong bao dat.

⛔ Va moi ca chay ffmpeg o day deu doi chieu T5 (`dinh_giao <= -1,5`): vong do to
   ⛔ khong duoc mua T4 bang T5. Do la dung cai bay ma chu thich cu du bao
   (*"tang gain thi day dinh len"*) — bay ay do ra la SAI (he so ≤ 0,05 dB/dB),
   nhung mot phep kiem noi dieu do ra thi re hon mot lan tin.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import am_master, qc, tach_tieng  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402

TONG_S = 8.0
DICH = tach_tieng.LUFS_DICH          # -14,0
DUNG_SAI = qc.LUFS_DUNG_SAI          # 1,0
TRAN_T5 = tach_tieng.DINH_THAT_DB    # -1,5


# ══════════════════════════════════════════════════════════════════════════════
#  Khuon dung tin hieu
# ══════════════════════════════════════════════════════════════════════════════

def _wav(dest: Path, loc_nguon: str, *, giay: float = TONG_S, kenh: int = 2,
         tan_so: int = am_master.TAN_SO, af: str = "") -> Path:
    ff = fx.require_ffmpeg()
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", loc_nguon, "-t", f"{giay}"]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", str(kenh), "-ar", str(tan_so), "-c:a", "pcm_s16le", str(dest)]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


def _ban_o_muc(dest: Path, nguon: Path, lufs: float) -> Path:
    """Dung mot ban `tho` o DUNG mot muc do to — de tiem loi co huong.

    ⭐ Mot luot `loudnorm` la du chinh xac o day vi bai kiem ⛔ khong tin con so
       nay: no DO lai ban vua dung (`do_am_luong`) va chot rang diem xuat phat
       that su nam NGOAI khoang T4. Mot phep tiem phai duoc do, ⛔ khong khai.
    """
    ff = fx.require_ffmpeg()
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(nguon),
                    "-af", f"loudnorm=I={lufs}:TP={am_master.dinh_that_phoi_db()}"
                           f":LRA=11:dual_mono=true",
                    "-ac", str(am_master.SO_KENH), "-ar", str(am_master.TAN_SO),
                    "-c:a", "pcm_s16le", str(dest)], check=True, capture_output=True)
    return dest


def _mot_ban_dung(thu: Path, *, nen_loc: str, nen_af: str, doan: list[tuple[int, str]],
                  doan_db: float) -> tuple[str, dict]:
    """Chay DUNG duong san pham (`tron_lo` + `tron_cuoi`) va tra bao cao ghim."""
    thu.mkdir(parents=True, exist_ok=True)
    nen = _wav(thu / "nen.wav", nen_loc, af=nen_af)
    cac = [str(_wav(thu / f"d{i}.wav", loc, giay=1.6, kenh=1, tan_so=24000,
                    af=f"volume={doan_db}dB"))
           for i, (_, loc) in enumerate(doan)]
    lo = am_master.tron_lo(cac, [m for m, _ in doan], [1.0] * len(cac),
                           str(thu / "lo.wav"), tong_giay=TONG_S)
    ghim: dict = {}
    master = am_master.tron_cuoi(nen, [lo], str(thu / "master.wav"),
                                 tong_giay=TONG_S, ghim=ghim)
    return master, {"ghim": ghim, "nen_do": tach_tieng.do_am_luong(str(nen))}


#: Hai ban dung co NOI DUNG khac han nhau: pho khac (pink / brown), he so dinh
#: khac (am don / am da bien dieu), muc nen khac, so doan khac.
NOI_DUNG_1 = dict(
    nen_loc="anoisesrc=color=pink:sample_rate=44100", nen_af="volume=-3dB",
    doan=[(300, "sine=frequency=220:sample_rate=24000"),
          (2600, "sine=frequency=330:sample_rate=24000"),
          (5200, "sine=frequency=440:sample_rate=24000")],
    doan_db=0.0)
NOI_DUNG_2 = dict(
    nen_loc="anoisesrc=color=brown:sample_rate=44100", nen_af="volume=-16dB",
    doan=[(500, "sine=frequency=180:sample_rate=24000"),
          (3400, "sine=frequency=900:sample_rate=24000")],
    doan_db=-9.0)


# ══════════════════════════════════════════════════════════════════════════════
#  1. Bo loc: khau bu do to nam DUNG cho (ham thuan, ⛔ khong chay ffmpeg)
# ══════════════════════════════════════════════════════════════════════════════

def test_loc_han_dinh_bu_do_to_TRUOC_bo_han_va_SAU_aformat_float():
    """Thu tu la ca ly le ve vi sao hai vong ⛔ khong tranh nhau."""
    loc = am_master.loc_han_dinh(-1.75, 1.5)
    i_fmt = loc.index("aformat=sample_fmts=fltp")
    i_vol = loc.index("volume=")
    i_han = loc.index("alimiter=")
    assert i_fmt < i_vol < i_han, (
        f"`volume` phai nam SAU `aformat` float (gain duong tren mau s16 CAT "
        f"NGON truoc khi bo han kip lam gi) va TRUOC `alimiter` (bo han phai la "
        f"nguoi giu tran cuoi cung — do la vi sao can gat do to chi lam dinh "
        f"nhich ≤ 0,05 dB moi dB): {loc}")
    assert "volume=1.500000dB" in loc, loc


def test_loc_han_dinh_MOT_hinh_dang_ke_ca_khi_gain_bang_khong():
    """⛔ Hai hinh dang chuoi = mot phep kiem xanh tren duong nay ⛔ khong noi gi
       ve duong kia. Khau `volume` duoc phat ca khi gain = 0."""
    khong = am_master.loc_han_dinh(-1.75)
    assert "volume=0.000000dB" in khong, khong
    assert khong.count("volume=") == am_master.loc_han_dinh(-1.75, 3.0).count("volume=")
    # Khuon cu cua `test_2015` phai con nguyen: lay mau 4x hai dau.
    boi = am_master.TAN_SO * am_master.GHIM_BOI_LAY_MAU
    assert khong.startswith(f"aresample={boi},") and khong.endswith(
        f"aresample={am_master.TAN_SO}"), khong


# ══════════════════════════════════════════════════════════════════════════════
#  2. Buoc sua: co VUNG CHET, co TRAN, co nguong — tuc vong DUNG
# ══════════════════════════════════════════════════════════════════════════════

def test_buoc_do_to_trong_vung_chet_thi_KHONG_sua():
    for thieu in (0.0, 0.29, -0.29, am_master.GHIM_LUFS_VUNG_CHET_DB):
        assert am_master._buoc_do_to(thieu, 0.0) == (0.0, "dat"), thieu


def test_buoc_do_to_la_buoc_NEWTON_he_so_mot_hai_chieu():
    """He so truyen do duoc la 0,92..1,00 trong ±1 LU ⇒ buoc day du la buoc dung."""
    assert am_master._buoc_do_to(1.0, 0.0) == (1.0, "dang_sua")
    assert am_master._buoc_do_to(-1.0, 0.0) == (-1.0, "dang_sua")
    buoc, ket = am_master._buoc_do_to(2.5, 1.0)
    assert (round(buoc, 6), ket) == (2.5, "dang_sua")


def test_buoc_do_to_bi_TRAN_gain_kep_va_noi_ten_thu_da_kep():
    tran = am_master.GHIM_GAIN_TRAN_DB
    buoc, ket = am_master._buoc_do_to(10.0, 0.0)
    assert (round(buoc, 6), ket) == (tran, "dang_sua"), "buoc dau phai di tan tran"
    assert am_master._buoc_do_to(10.0, tran) == (0.0, "kep_boi_tran_gain"), (
        "dung o tran roi thi vong phai THOAT co ghi, ⛔ khong quay them vong de "
        "tien 0 dB")
    assert am_master._buoc_do_to(-10.0, -tran) == (0.0, "kep_boi_tran_gain")


def test_vung_chet_NHO_hon_dung_sai_T4_mot_khoang_thay_duoc():
    """⛔ Vung chet bang dung sai T4 la tu bo toan bo bien: `atempo` + AAC cua
       lan render THAT an 0,18..0,23 LU NUA sau khi vong nay noi 'dat'."""
    assert am_master.GHIM_LUFS_VUNG_CHET_DB < DUNG_SAI
    assert DUNG_SAI - am_master.GHIM_LUFS_VUNG_CHET_DB >= 0.5, (
        f"vung chet {am_master.GHIM_LUFS_VUNG_CHET_DB} chi de lai "
        f"{DUNG_SAI - am_master.GHIM_LUFS_VUNG_CHET_DB} LU bien cho phan "
        f"`atempo` + AAC cua chinh lan render — do duoc 0,18..0,23 LU")


def test_so_vong_du_cho_ca_XAU_NHAT_da_do_duoc():
    """⛔ Do duoc 3 vong o ca xau nhat (32 lan chay, bang o `SO_VONG_GHIM`) ⇒ tran
       phai > 3. Bang 3 la 'vua du', va 'vua du' tren bon ban phoi ⛔ khong phai
       'du tren moi phim'."""
    assert am_master.SO_VONG_GHIM >= 4, (
        "3 vong la so DO DUOC o ca xau nhat; tran phai chua no + mot vong du")
    assert am_master.GHIM_LUFS_BUOC_TOI_THIEU_DB > 0, (
        "khong co nguong buoc thi mot ca bi kep se quay het tran vong de tien "
        "0 dB moi vong")


# ══════════════════════════════════════════════════════════════════════════════
#  3. Duong san pham: HAI noi dung khac nhau, CUNG khoang
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_noi_dung_KHAC_NHAU_cho_do_to_trong_CUNG_khoang(tmp_path):
    """⭐ Chot mot TINH CHAT, ⛔ khong mot gia tri.

    Chot `lufs_giao == -14,19` la chot CACH GO: no xanh cho mot ban dung va do
    cho ban tiep theo, dung nhu `BIEN_CHO_CODEC_DB` da xanh cho `T1a` roi do cho
    `T1a-bis`. Menh de dung la *"moi ban dung deu roi vao khoang"*.
    """
    m1, bc1 = _mot_ban_dung(tmp_path / "nd1", **NOI_DUNG_1)
    m2, bc2 = _mot_ban_dung(tmp_path / "nd2", **NOI_DUNG_2)

    # ⭐ Chung minh hai noi dung THAT SU khac nhau — neu khong, bai nay chi chay
    #    mot ca hai lan va menh de "moi ban dung" ⛔ khong duoc kiem.
    lech_nen = abs(bc1["nen_do"]["lufs"] - bc2["nen_do"]["lufs"])
    assert lech_nen > 2.0, (
        f"hai ban nen chi lech {lech_nen:.2f} LU — bai nay dang chay mot ca hai "
        f"lan chu ⛔ khong chot duoc tinh chat")

    for ten, bc in (("noi dung 1", bc1["ghim"]), ("noi dung 2", bc2["ghim"])):
        lufs = bc["lufs_giao"]
        assert lufs is not None, (ten, bc)
        assert abs(lufs - DICH) <= DUNG_SAI, (
            f"{ten}: ban giao {lufs} LUFS ngoai khoang T4 ({DICH} ± {DUNG_SAI})")
        assert bc["dat_do_to"] is True, (ten, bc)
        # ⛔ Va T4 ⛔ khong duoc mua bang T5.
        assert bc["dinh_giao"] <= TRAN_T5, (ten, bc)
        assert bc["dat"] is True, (ten, bc)
        assert bc["so_vong"] <= am_master.SO_VONG_GHIM, (ten, bc)

    # ⛔ Va bao cao phai di ra tan `kiem_ban_ra` — mot con so do roi bo lai trong
    #    ham la mot con so ⛔ khong ai doc duoc (bai hoc `lufs_giao` bi VUT 27/09).
    kq = am_master.kiem_ban_ra(m1, mong_doi_giay=TONG_S, dung_sai_giay=0.5,
                               ghim=bc1["ghim"])
    assert kq["lufs_giao"] == bc1["ghim"]["lufs_giao"]
    assert kq["gain_do_to"] == bc1["ghim"]["gain_do_to"]
    assert kq["dat_do_to"] is True and kq["ket_do_to"] == "dat"
    assert m2  # ban thu hai da duoc dung that, khong chi do bao cao


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ve DOI CHUNG: QUA NHO va QUA TO deu duoc keo VE khoang
# ══════════════════════════════════════════════════════════════════════════════

def _tiem(tmp_path: Path, ten: str, lufs: float) -> tuple[Path, dict]:
    goc = _wav(tmp_path / f"{ten}_goc.wav",
               "anoisesrc=color=pink:sample_rate=44100")
    tho = _ban_o_muc(tmp_path / f"{ten}_tho.wav", goc, lufs)
    return tho, tach_tieng.do_am_luong(str(tho))


def test_ban_QUA_NHO_duoc_keo_LEN_ve_khoang(tmp_path):
    """⛔ Day la ve doi chung: neu vong nay ⛔ khong bao gio nang, no ⛔ khong sua
       duoc dung ca da lam T4 hong (`T1a-bis`: master -15,04, dinh con 3 dB bien)."""
    tho, truoc = _tiem(tmp_path, "nho", -19.0)
    assert truoc["lufs"] < DICH - DUNG_SAI, (
        f"phep tiem that bai: {truoc} da nam trong khoang T4, bai nay ⛔ khong "
        f"chung minh gi")
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "nho_ra.wav"))
    assert bc["gain_do_to"] > 0, bc
    assert abs(bc["lufs_giao"] - DICH) <= DUNG_SAI, bc
    assert bc["dat_do_to"] is True and bc["ket_do_to"] == "dat", bc
    assert bc["dinh_giao"] <= TRAN_T5, ("T4 ⛔ khong duoc mua bang T5", bc)


def test_ban_QUA_TO_duoc_keo_XUONG_ve_khoang(tmp_path):
    """Chieu am cua can gat: he so 1:1 tren CA do to LAN dinh (bo han nha tay)."""
    tho, truoc = _tiem(tmp_path, "to", -10.0)
    assert truoc["lufs"] > DICH + DUNG_SAI, (
        f"phep tiem that bai: {truoc} da nam trong khoang T4")
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "to_ra.wav"))
    assert bc["gain_do_to"] < 0, bc
    assert abs(bc["lufs_giao"] - DICH) <= DUNG_SAI, bc
    assert bc["dat_do_to"] is True and bc["ket_do_to"] == "dat", bc
    assert bc["dinh_giao"] <= TRAN_T5, bc


def test_vong_KHONG_dong_gi_khi_ban_phoi_da_LANH(tmp_path):
    """⛔ Khong duoc them mot luot ma hoa nao cho mot lan chay ⛔ khong co gi sai."""
    tho, truoc = _tiem(tmp_path, "lanh", DICH)
    assert abs(truoc["lufs"] - DICH) <= am_master.GHIM_LUFS_VUNG_CHET_DB, truoc
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "lanh_ra.wav"))
    assert bc["so_vong"] == 1, (
        "duong LANH phai dung o MOT vong — bang do 28/09: 4/4 ban phoi that", bc)
    assert bc["gain_do_to"] == 0.0 and bc["dat_do_to"] is True, bc


# ══════════════════════════════════════════════════════════════════════════════
#  5. Vong phai DUNG — ke ca khi ⛔ khong hoi tu duoc
# ══════════════════════════════════════════════════════════════════════════════

def test_ca_KHONG_hoi_tu_thi_thoat_o_TRAN_va_co_GHI_LAI(tmp_path):
    """⛔ Mot vong hoi tu phai tra loi duoc ca cau *"neu khong hoi tu duoc thi
       sao"*. Ca nay lech ~14 LU — xa hon `GHIM_GAIN_TRAN_DB` gap doi."""
    tho, truoc = _tiem(tmp_path, "vuc", -28.0)
    assert truoc["lufs"] < DICH - am_master.GHIM_GAIN_TRAN_DB - DUNG_SAI, truoc
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "vuc_ra.wav"))

    assert bc["so_vong"] <= am_master.SO_VONG_GHIM, ("vong phai HUU HAN", bc)
    assert bc["gain_do_to"] == am_master.GHIM_GAIN_TRAN_DB, (
        "phai di tan tran roi DUNG, ⛔ khong vuot tran de 'cuu' T4 bang cach ep "
        "bo han (cai gia la am thanh bi bom, ⛔ khong phai mot con so)", bc)
    # ⛔ Thoat co GHI: bao cao phai noi ra, ⛔ khong bao dat.
    assert bc["dat_do_to"] is False, bc
    assert bc["ket_do_to"] == "kep_boi_tran_gain", bc
    assert abs(bc["lufs_giao"] - DICH) > DUNG_SAI, (
        "ca nay CO hong T4 — bai kiem chot rang no hong MOT CACH CO GHI, ⛔ khong "
        "chot rang no duoc cuu", bc)
    # ⛔ Va no ⛔ khong keo T5 theo: mot ca hong T4 van phai giao dung dinh.
    assert bc["dat"] is True and bc["dinh_giao"] <= TRAN_T5, bc


def test_vong_CUOI_chi_duoc_sua_DINH_khong_duoc_doi_gain(tmp_path):
    """⛔ Doi `gain` o vong cuoi thi phan tang ay ⛔ KHONG bao gio duoc DO, va ta
       giao mot tep chua ai kiem. `so_vong=1` la ca cuc doan cua luat ay."""
    tho, truoc = _tiem(tmp_path, "motvong", -18.0)
    assert truoc["lufs"] < DICH - DUNG_SAI, truoc
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "motvong_ra.wav"),
                                 so_vong=1)
    assert bc["so_vong"] == 1 and bc["gain_do_to"] == 0.0, bc
    assert bc["ket_do_to"] == "het_vong", bc
    assert bc["dat_do_to"] is False, bc


def test_bao_cao_ghi_TUNG_vong_ca_gain_lan_do_to_da_do(tmp_path):
    """Nguoi doc bao cao phai thay duong di, ⛔ khong chi diem den — do la thu bien
       mot lan chay thanh mot phep do co the doi chieu lai."""
    tho, _ = _tiem(tmp_path, "vet", -18.0)
    bc = am_master.ghim_tran_phoi(str(tho), str(tmp_path / "vet_ra.wav"))
    assert len(bc["vet"]) == bc["so_vong"] >= 2, bc
    for v in bc["vet"]:
        assert set(v) == {"tran_phoi", "gain", "dinh_giao", "lufs_giao"}, v
        assert v["lufs_giao"] is not None, ("do to phai duoc DO moi vong", v)
    assert bc["vet"][0]["gain"] == 0.0, "vong dau phai xuat phat tu khong bu"
    assert bc["vet"][-1]["gain"] == bc["gain_do_to"], (
        "bao cao phai noi ve tep DA DO (vong cuoi), ⛔ khong ve mot vong chua chay")
    assert bc["vet"][-1]["tran_phoi"] == bc["tran_phoi"], bc


def test_PHIEN_BAN_MASTER_da_len_bac_cho_vong_do_to():
    """⛔ Thieu buoc tang nay thi mot ban phoi CHUA duoc sua do to duoc dung lai
       tu cache va T4 do lai lech y nguyen."""
    assert am_master.PHIEN_BAN_MASTER >= 7
