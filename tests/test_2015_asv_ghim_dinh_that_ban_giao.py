"""ASV final (lan fix-qc-am) — R-03: dinh that cua TEP KHACH NHAN, khong cua PCM.

🔴 **Vi sao bo kiem cu khong bat duoc.** `test_479`/`test_442` chot *chuoi loc*
   cua ban phoi, `test_420`/`test_444` chot *nguong T5* bang cach tiem mot con
   so vao `qc.kiem`. Ca hai deu dung — va ca hai deu do o phia PCM. Khong bai
   nao ma hoa ban phoi bang tham so giao hang roi do lai, nen khoang cach giua
   *ban phoi* va *ban giao* — thu da lam T5 do o luot phim that — khong co chot
   nao ca. `test_448` co do tep ra that, nhung tren `lavfi` im lang / mot tan so,
   noi bo ma hoa gan nhu khong vot lo.

⇒ Ba menh de duoc chot o day:
   1. `loc_han_dinh` han DINH THAT (lay mau 4x), khong phai dinh MAU;
   2. vong `ghim_tran_phoi` HA tran cho toi khi ban ma hoa thu dat tran T5;
   3. ban phoi do `tron_cuoi` sinh ra co `kiem_ban_ra(...)["dinh_that_giao"]`
      nam duoi tran T5 — tuc cau hoi cua T5 duoc tra loi TRUOC khi render.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import am_master, ban_dung, tach_tieng  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402

TONG_S = 6.0


def _wav(dest: Path, nguon_loc: str, *, giay: float = TONG_S,
         kenh: int = 2, tan_so: int = am_master.TAN_SO) -> Path:
    ff = fx.require_ffmpeg()
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", nguon_loc, "-t", f"{giay}",
                    "-ac", str(kenh), "-ar", str(tan_so),
                    "-c:a", "pcm_s16le", str(dest)],
                   check=True, capture_output=True)
    return dest


def _am_don(dest: Path, tan: int, *, giay: float = TONG_S) -> Path:
    """Mot am don TO (dinh that ~ -1 dB), tat dinh, o tan so chon truoc.

    ⭐ Am don la khuon chuan de noi ve dinh giua-mau: o 997 Hz dinh THAT gan
       bang dinh MAU, con o 14 kHz no cao hon han — dung hai dau de do bo han.
    """
    ff = fx.require_ffmpeg()
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"sine=frequency={tan}:sample_rate=44100",
                    "-t", f"{giay}",
                    "-af", "volume=20dB,aformat=channel_layouts=stereo",
                    "-ar", str(am_master.TAN_SO), "-c:a", "pcm_s16le", str(dest)],
                   check=True, capture_output=True)
    return dest


def _to(dest: Path, *, giay: float = TONG_S) -> Path:
    return _am_don(dest, 997, giay=giay)


# ── 1. Bo loc: ham thuan ──────────────────────────────────────────────────────

def test_loc_han_dinh_lay_mau_4x_va_KHONG_tu_nang_muc():
    loc = am_master.loc_han_dinh(-3.5)
    boi = am_master.TAN_SO * am_master.GHIM_BOI_LAY_MAU
    assert loc.startswith(f"aresample={boi},"), loc
    assert loc.endswith(f"aresample={am_master.TAN_SO}"), loc
    assert "level=0" in loc, (
        "thieu `level=0` thi `alimiter` TU NANG muc ra cham tran — no se keo to "
        "mot ban phoi yen tinh va pha ca T4 lan ket qua cua `loudnorm`")
    assert f"limit={10.0 ** (-3.5 / 20.0):.6f}" in loc, (
        f"`limit` cua `alimiter` la BIEN DO tuyen tinh, khong phai dB: {loc}")


def test_tran_khoi_diem_muon_tu_tach_tieng_khong_chep_so():
    assert am_master.dinh_that_phoi_db() == (
        tach_tieng.DINH_THAT_DB - am_master.BIEN_CHO_CODEC_DB)


# ── 2. ffmpeg that: han DINH THAT, khong phai dinh MAU ────────────────────────

def test_han_dinh_ghim_DUNG_tran_tren_am_don(tmp_path):
    vao = _to(tmp_path / "to.wav")
    assert tach_tieng.do_am_luong(str(vao))["dinh_that"] > -1.5, "tin hieu chua du to"
    for tran in (-3.5, -6.0):
        ra = am_master.han_dinh(str(vao), str(tmp_path / f"ra{tran}.wav"),
                                tran_db=tran)
        dinh = tach_tieng.do_am_luong(ra)["dinh_that"]
        assert abs(dinh - tran) <= 0.15, f"tran {tran} -> dinh that {dinh}"


def _trui(vao: Path, ra: Path, tran_db: float) -> float:
    """`alimiter` TRAN TRUI (khong lay mau len) -> dinh that do duoc."""
    lin = 10.0 ** (tran_db / 20.0)
    subprocess.run([fx.require_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(vao), "-af", f"alimiter=limit={lin:.6f}:level=0",
                    "-ac", "2", "-ar", str(am_master.TAN_SO),
                    "-c:a", "pcm_s16le", str(ra)], check=True, capture_output=True)
    return float(tach_tieng.do_am_luong(str(ra))["dinh_that"])


def test_alimiter_TRAN_TRUI_vuot_tran_con_ban_LAY_MAU_LEN_thi_khong(tmp_path):
    """Doi chung cho `GHIM_BOI_LAY_MAU` — no la thu bien phep do thanh phep do.

    🔴 Bay nay da duoc ghi o pha 22 va day la phep do cua no: `alimiter` mot
       minh han dinh MAU; dinh THAT (giua mau) van troi len tren tran. Am don
       14 kHz la truong hop xau nhat, va la truong hop de doc nhat.

    ⚠️ Ban lay mau len **khong** chinh xac tuyet doi (phep ha mau lai lam moc
       len mot phan) — do la ly do `ghim_tran_phoi` do tren ban MA HOA THU chu
       khong tin bo han.
    """
    vao = _am_don(tmp_path / "cao.wav", 14000)
    trui = _trui(vao, tmp_path / "trui.wav", -3.5)
    ghim = float(tach_tieng.do_am_luong(
        am_master.han_dinh(str(vao), str(tmp_path / "ghim.wav"), tran_db=-3.5)
    )["dinh_that"])
    assert trui > -3.5 + 1.0, f"am don 14 kHz phai lam lo bo han tran trui: {trui}"
    assert ghim < trui - 0.5, f"lay mau len phai thu hep sai so: {ghim} vs {trui}"


# ── 3. Vong ghim: ha tran cho toi khi BAN MA HOA THU dat ─────────────────────

def test_do_ban_giao_dung_DUNG_tham_so_giao_hang(tmp_path):
    """Phep do phai noi ve dung thu `ket_xuat.dung_lenh` se sinh ra."""
    import inspect

    ma = inspect.getsource(am_master.do_ban_giao)
    for ten in ("CODEC_TIENG", "BITRATE_TIENG", "TAN_SO_RA", "SO_KENH_RA"):
        assert f"ban_dung.{ten}" in ma, (
            f"`do_ban_giao` phai muon {ten} tu `ban_dung` — chep so sang day la "
            f"tao mot ban sao se lech")
    kq = am_master.do_ban_giao(str(_to(tmp_path / "to.wav")))
    assert set(kq) >= {"lufs", "dinh_that"}
    assert ban_dung.CODEC_TIENG == "aac"          # khuon di san, doi phai co y


def test_ghim_tran_phoi_HA_tran_cho_toi_khi_ban_giao_dat(tmp_path):
    """Vong lap phai CHAY, khong chi ton tai.

    ⭐ `tran_bat_dau=-0.2` ep vong mot truot chac chan (ban giao khong the
       xuong duoi -1,5 tu mot ban phoi -0,2), nen bai nay do co cau chu khong
       do may man cua mot tin hieu cu the.
    """
    goc = _to(tmp_path / "to.wav")
    bc = am_master.ghim_tran_phoi(str(goc), str(tmp_path / "ghim.wav"),
                                  tran_giao=tach_tieng.DINH_THAT_DB,
                                  tran_bat_dau=-0.2)
    assert bc["so_vong"] >= 2, bc
    assert bc["dat"] and bc["dinh_giao"] <= tach_tieng.DINH_THAT_DB, bc
    assert bc["tran_phoi"] < -0.2, bc
    # Ban ghi de nguoi doc bao cao thay tung vong, khong chi ket qua.
    assert [v["tran_phoi"] for v in bc["vet"]] == sorted(
        (v["tran_phoi"] for v in bc["vet"]), reverse=True)


def test_ghim_nang_mot_ban_phoi_QUA_NHO_nhung_KHONG_vuot_TRAN_GAIN(tmp_path):
    """🔴 **Bai nay DA DAO CHIEU o T4 (28/09), va viec dao chieu la chu dich.**

    Ban cu chot *"vong ghim chi ha, khong bao gio nang: no khong duoc dung lam bo
    chuan am"*. Menh de ay dung khi vong nay CHI sua dinh — nhung no cung la dung
    thu da lam T4 hong: `T1a-bis` giao `-15,44 LUFS` voi dinh con **3 dB bien
    chua dung**, tuc mot ban phoi co the to hon ma vong nay bi cam nang.

    ⇒ Tu T4, vong nay sua CA DO TO (`ghim_tran_phoi` -> `_buoc_do_to`), nen no CO
      nang. Cai con lai cua menh de cu — va la cai that su dang bao ve — la:
      no ⛔ **khong duoc nang vo han** (`GHIM_GAIN_TRAN_DB`), va nang bao nhieu thi
      dinh cung ⛔ **khong duoc vuot T5**.

    ⚠️ Am don 997 Hz o -24 dB la mot ca CUC DOAN co y (lech ~20 LU, xa hon tran
       gain gap ba) — no chot dung cai tran ay. Ca thuong va ca tiem vua phai o
       `test_4896`.
    """
    nho = _to(tmp_path / "nho.wav")
    subprocess.run([fx.require_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(nho), "-af", "volume=-24dB", "-c:a", "pcm_s16le",
                    str(tmp_path / "nho2.wav")], check=True, capture_output=True)
    truoc = tach_tieng.do_am_luong(str(tmp_path / "nho2.wav"))
    bc = am_master.ghim_tran_phoi(str(tmp_path / "nho2.wav"),
                                  str(tmp_path / "ra.wav"))
    sau = tach_tieng.do_am_luong(str(tmp_path / "ra.wav"))

    assert bc["gain_do_to"] == am_master.GHIM_GAIN_TRAN_DB, (
        "lech ~20 LU thi buoc bu phai di tan TRAN roi dung", bc)
    assert sau["lufs"] - truoc["lufs"] <= am_master.GHIM_GAIN_TRAN_DB + 0.2, (
        f"nang qua tran gain: {truoc['lufs']} -> {sau['lufs']}")
    assert bc["dinh_giao"] <= tach_tieng.DINH_THAT_DB, (
        "nang do to ⛔ khong duoc mua T4 bang T5", bc)
    assert bc["ket_do_to"] == "kep_boi_tran_gain" and bc["dat_do_to"] is False, (
        "mot ca ⛔ khong cuu duoc phai thoat CO GHI", bc)


# ── 4. Duong san pham: ban phoi do `tron_cuoi` sinh ra ───────────────────────

def test_tron_cuoi_giao_ban_phoi_DA_GHIM_va_kiem_ban_ra_noi_ra_so_do(tmp_path):
    """Menh de cuoi: cau hoi cua T5 duoc tra loi TRUOC khi ton mot suat render."""
    nen = _wav(tmp_path / "nen.wav", "anoisesrc=color=pink:sample_rate=44100")
    doan = [str(_wav(tmp_path / f"d{i}.wav",
                     f"sine=frequency={220 + i * 110}:sample_rate=24000",
                     giay=1.5, kenh=1, tan_so=24000)) for i in range(3)]
    lo = am_master.tron_lo(doan, [0, 2000, 4000], [1.0] * 3,
                           str(tmp_path / "lo.wav"), tong_giay=TONG_S)
    ghim: dict = {}
    master = am_master.tron_cuoi(str(nen), [lo], str(tmp_path / "master.wav"),
                                 tong_giay=TONG_S, ghim=ghim)
    assert ghim.get("dat") is True, ghim

    kq = am_master.kiem_ban_ra(master, mong_doi_giay=TONG_S, dung_sai_giay=0.5,
                               ghim=ghim)
    assert kq["dinh_that"] <= am_master.dinh_that_phoi_db() + 0.05, kq
    assert kq["dinh_that_giao"] <= tach_tieng.DINH_THAT_DB, kq
    assert kq["so_vong_ghim"] == ghim["so_vong"]
    assert abs(kq["lufs"] - tach_tieng.LUFS_DICH) <= 1.0, kq


def test_kiem_ban_ra_KHONG_co_ghim_thi_van_tu_do_lay(tmp_path):
    """⛔ Duong lui phai con: mot nguoi goi khong truyen `ghim` van nhan duoc so
       that, khong nhan mot cho trong trong nhu mot phep do."""
    kq = am_master.kiem_ban_ra(str(_to(tmp_path / "to.wav")),
                               mong_doi_giay=TONG_S, dung_sai_giay=0.5)
    assert isinstance(kq["dinh_that_giao"], float)
    assert kq["so_vong_ghim"] is None


def test_van_tay_master_doi_khi_cach_dung_ban_phoi_doi():
    """⛔ Thieu buoc tang nay thi mot ban phoi CHUA GHIM duoc dung lai tu cache."""
    assert am_master.PHIEN_BAN_MASTER >= 3
    vt = dict(van_tay_nen="a", van_tay_ke_hoach="b",
              phien_ban_ffmpeg_="d")
    truoc = am_master.van_tay_master(**vt)
    goc = am_master.PHIEN_BAN_MASTER
    try:
        am_master.PHIEN_BAN_MASTER = goc + 1
        assert am_master.van_tay_master(**vt) != truoc
    finally:
        am_master.PHIEN_BAN_MASTER = goc
