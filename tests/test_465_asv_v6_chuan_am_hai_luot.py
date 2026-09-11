"""V6 — `loudnorm` HAI luot: vi sao doi, va ba cai bay tren duong doi.

## Phep do lam ra thay doi nay

Luot nghiem thu 10/09 tren PostgreSQL, cung mot ban master, hai preset:

    giu_hinh        LUFS = -14,98   DAT   (con 0,02 dB toi bien)
    cat_thong_minh  LUFS = -15,02   HONG  (vuot 0,02 dB)

Dich la -14,0 ± 1,0. **Ca hai deu roi vao ~-15,0** — lech ~1 dB va nam DUNG tren
bien. Preset nay dat, preset kia hong, cach nhau 0,04 dB.

🔑 Nen phat hien khong phai "duong cat hong". No la: **ca duong ong giao am
   luong ngay ria loi hua cua chinh no**, va `giu_hinh` "dat" la MAY.

⛔ Va vi the ban sua khong phai noi `LUFS_DUNG_SAI`. Noi mot dung sai de mot
   phep kiem xanh la bo chinh cau hoi no dang hoi.

`loudnorm` mot luot la bo chuan **dong** — sai so ~1 dB la hanh vi da biet cua
no. Hai luot (do truoc, ap bang `measured_*` + `linear=true`) moi trung dich.

Sau khi doi, cung bo nghiem thu:

    giu_hinh        -14,98 -> **-14,44**   (bien 0,02 -> 0,56 dB)
    cat_thong_minh  -15,02 -> **-14,45**   (HONG -> DAT)

⭐ Hai duong cung hoi tu: truoc cach nhau 0,04 dB o hai ben bien, sau cach nhau
   0,01 dB va cung nam trong.

⚠️ Va no **khong** ve dung -14,00: con lech ~0,45 dB. Do la buoc PCM -> AAC ma
   chu thich cua `qc.py` da mo ta tu truoc (san xuat chuan hoa ban master PCM,
   QC do tep AAC giao cho khach). Thay doi nay khong xoa khoang do — no doi tu
   "nam tren bien, dat/hong tuy may" sang "nam trong, con hon nua dB du".

## Ba cai bay da tra gia, va ca ba deu treo IM LANG

  1. `print_format` noi SAU nhan ra   -> ffmpeg tu choi ca chuoi, luot do tra
                                         `None`, he tu lui ve mot luot
  2. luot do thieu `-t`                -> `apad` chen im lang VO HAN, lenh chay
                                         mai, khong bao gi
  3. `input_i = -inf` (ban tron im lang) -> `linear=true` voi mot gia tri vo cuc
                                         lam ffmpeg tu choi CA lan chay

Ca ba deu khong nem loi. Nen §2 chot chung bang phep kiem chu khong bang chu.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import am_master as am

DO = {"input_i": "-24.10", "input_tp": "-5.20", "input_lra": "7.30",
      "input_thresh": "-34.50", "target_offset": "0.20"}


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Hai dang cua bo loc
# ══════════════════════════════════════════════════════════════════════════════

def test_MOT_luot_khong_co_tham_so_da_do():
    ve = am.bieu_thuc_chuan_am("[t]", "[r]", tong_giay=3.0)
    assert "measured_" not in ve and "linear=" not in ve


def test_HAI_luot_mang_DU_NAM_tham_so_va_linear():
    """⛔ Thieu MOT trong nam thi `loudnorm` lang le quay ve che do dong — dung
    cai vua sua, va khong co gi bao."""
    ve = am.bieu_thuc_chuan_am("[t]", "[r]", tong_giay=3.0, do_duoc=DO)
    for k in ("measured_I", "measured_TP", "measured_LRA", "measured_thresh",
              "offset"):
        assert k + "=" in ve, f"thieu {k}"
    assert "linear=true" in ve


def test_dich_va_tran_dinh_KHONG_doi():
    """Thay doi nay chi cham DO CHINH XAC, khong cham DICH. Neu no doi ca dich
    thi no la mot thay doi san pham, va no phai duoc noi ra."""
    for do_duoc in (None, DO):
        ve = am.bieu_thuc_chuan_am("[t]", "[r]", tong_giay=3.0, do_duoc=do_duoc)
        assert f"I={am.lufs_dich()}" in ve
        assert f"TP={am.dinh_that_phoi_db()}" in ve


def test_PHIEN_BAN_MASTER_da_len_bac():
    """⛔ Ban ra doi byte. Khong bump thi mot ban phoi tinh o thoi MOT luot duoc
    dung lai cho mot cau hoi nay da khac."""
    assert am.PHIEN_BAN_MASTER >= 2


def test_van_tay_master_DOI_theo_phien_ban():
    """Doi chung cho bai tren: bump chi co nghia neu no that su vao van tay."""
    goc = dict(van_tay_nen="a", van_tay_ke_hoach="b", van_tay_ban_do="c",
               phien_ban_ffmpeg_="n7.0")
    truoc = am.van_tay_master(**goc)
    cu = am.PHIEN_BAN_MASTER
    try:
        am.PHIEN_BAN_MASTER = cu + 1
        assert am.van_tay_master(**goc) != truoc
    finally:
        am.PHIEN_BAN_MASTER = cu


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Ba cai bay treo IM LANG
# ══════════════════════════════════════════════════════════════════════════════

def test_print_format_nam_TRONG_cum_tham_so_cua_loudnorm():
    """🔴 Bay 1. `[ra]:print_format=json` la cu phap khong hop le — ffmpeg tu
    choi CA chuoi, luot do tra `None`, va he **tu lui ve mot luot** ma khong ai
    biet. Chot bang VI TRI: no phai dung truoc dau phay dau tien sau `loudnorm`.
    """
    ve = am.bieu_thuc_chuan_am("[t]", "[r]", tong_giay=3.0, in_json=True)
    assert "print_format=json" in ve
    cum = ve.split("loudnorm=", 1)[1].split(",", 1)[0]
    assert "print_format=json" in cum, f"print_format nam ngoai cum loudnorm: {ve}"
    assert not ve.rstrip().endswith("print_format=json"), "nam sau nhan ra"


def test_luot_DO_luon_co_tran_thoi_gian(monkeypatch):
    """🔴 Bay 2. `apad` chen im lang **vo han**. Mot lenh do khong co `-t` chay
    mai va treo IM LANG — khong loi, khong log, tien trinh cha doi het gio."""
    da_thay = {}

    def _gia(cmd, **kw):
        da_thay["cmd"] = list(cmd)
        raise RuntimeError("dung o day — chi can doc dong lenh")

    monkeypatch.setattr(am, "_chay", _gia)
    with pytest.raises(RuntimeError):
        am._do_am_luong(["ffmpeg", "-i", "x.wav"], "[0:a]anull[tron];",
                        tong_giay=8.0)
    cmd = da_thay["cmd"]
    assert "-t" in cmd, f"luot do khong co tran thoi gian: {cmd}"
    assert cmd[cmd.index("-t") + 1].startswith("8."), cmd


def test_luot_DO_lui_ve_mot_luot_khi_do_duoc_VO_CUC(monkeypatch):
    """🔴 Bay 3. Ban tron im lang cho `input_i = -inf`. `linear=true` voi mot
    gia tri vo cuc lam ffmpeg tu choi CA lan chay — tuc mot ban phoi im lang se
    lam hong lan chay thay vi cho ra mot ban phoi im lang."""
    class _R:
        returncode = 0
        stderr = (b'{"input_i":"-inf","input_tp":"-inf","input_lra":"0.00",'
                  b'"input_thresh":"-inf","target_offset":"0.00"}')

    monkeypatch.setattr(am, "_chay", lambda cmd, **kw: _R())
    assert am._do_am_luong(["ffmpeg"], "[0:a]anull[tron];", tong_giay=1.0) is None


def test_luot_DO_lui_ve_mot_luot_khi_THIEU_khoa(monkeypatch):
    """Thieu mot khoa la phep do khong dung duoc. Lui ve mot luot van cho ra
    mot ban phoi; ap mot phep do thieu thi cho ra mot bo loc hong."""
    class _R:
        returncode = 0
        stderr = b'{"input_i":"-24.1","input_tp":"-5.2"}'

    monkeypatch.setattr(am, "_chay", lambda cmd, **kw: _R())
    assert am._do_am_luong(["ffmpeg"], "[0:a]anull[tron];", tong_giay=1.0) is None


def test_luot_DO_lui_ve_mot_luot_khi_ffmpeg_HONG(monkeypatch):
    """⛔ Tra `None` chu khong nem: khong do duoc thi ve ban MOT LUOT — ban van
    chay tu truoc toi nay. Mot ban phoi lech 1 dB xau hon mot ban phoi dung,
    nhung tot hon **khong co ban phoi nao**."""
    class _R:
        returncode = 1
        stderr = b"loi gi do"

    monkeypatch.setattr(am, "_chay", lambda cmd, **kw: _R())
    assert am._do_am_luong(["ffmpeg"], "[0:a]anull[tron];", tong_giay=1.0) is None


def test_doc_duoc_JSON_CUOI_CUNG_khi_co_nhieu_khoi(monkeypatch):
    """`loudnorm` in mot khoi JSON cho MOI dau vao di qua no. Lay khoi dau la
    lay phep do cua mot luong khac."""
    class _R:
        returncode = 0
        stderr = (b'{"input_i":"-30.0","input_tp":"-9.0","input_lra":"1.0",'
                  b'"input_thresh":"-40.0","target_offset":"0.0"}\n'
                  b'{"input_i":"-24.1","input_tp":"-5.2","input_lra":"7.3",'
                  b'"input_thresh":"-34.5","target_offset":"0.2"}')

    monkeypatch.setattr(am, "_chay", lambda cmd, **kw: _R())
    ra = am._do_am_luong(["ffmpeg"], "[0:a]anull[tron];", tong_giay=1.0)
    assert ra is not None and ra["input_i"] == "-24.1"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Co ai DANG di tren duong do khong
# ══════════════════════════════════════════════════════════════════════════════

def test_tron_cuoi_THUC_SU_chay_HAI_luot(monkeypatch, tmp_path):
    """🔑 Bai nay la ban VIET LAI, va ly do dang hon chinh bai.

    Ban dau toi chot bang AST: *"`tron_cuoi` co goi `_do_am_luong` khong"*. Doi
    chung bac no ngay — toi tiem `do_duoc = None if True else _do_am_luong(...)`
    va **ca 12 bai van xanh**, vi nut goi VAN CON TRONG CAY, chi la khong bao
    gio chay tới.

    ⛔ Mot phep kiem doc AST hoi *"co dong ma do khong"*; cau can hoi la *"dong
       ma do co CHAY khong"*. Hai cau do khac nhau, va cai bay o giua chung la
       cho mot ban sua "tien tay" di lot.

    ⇒ Ban nay chan `_chay` va doc **dong lenh ffmpeg that su duoc dung**: phai
      co HAI lan goi, va lan thu hai phai mang `measured_I`.
    """
    lan = []

    class _R:
        returncode = 0
        stderr = (b'{"input_i":"-24.1","input_tp":"-5.2","input_lra":"7.3",'
                  b'"input_thresh":"-34.5","target_offset":"0.2"}')

    def _gia(cmd, **kw):
        lan.append(list(cmd))
        return _R()

    monkeypatch.setattr(am, "_chay", _gia)
    am.tron_cuoi(str(tmp_path / "nen.wav"), [str(tmp_path / "lo1.wav")],
                 str(tmp_path / "ra.wav"), tong_giay=8.0)

    assert len(lan) == 2, f"ky vong hai luot ffmpeg, thay {len(lan)}"

    do, ap = lan
    assert "-f" in do and do[do.index("-f") + 1] == "null", "luot 1 phai la luot DO"
    assert "print_format=json" in " ".join(do)
    assert "measured_I" not in " ".join(do), "luot DO khong duoc mang phep do cua chinh no"

    ve_ap = " ".join(ap)
    assert "measured_I=-24.1" in ve_ap, "luot AP khong mang ket qua luot DO"
    assert "linear=true" in ve_ap
