"""Pha 13 — chat luong tach nguon va chan tai nguyen.

Bon nhom, va moi nhom chot mot menh de da DO duoc chu khong phai mot y dinh:

  A. So hoc chia khoi   — ban ra phu kin, khong ho, khong nhan doi, ghim dung luoi
  B. Chinh sach thiet bi — khong co cho tut xuong CPU im lang
  C. Tat dinh           — `van_tay_tach` hua mot ham tat dinh; gio no dung
  D. Khai bao tai nguyen — con so trong manifest la con so DA DO

⭐ Ca nhom A chay **khong nap demucs**: `tach_theo_khoi` nhan ham goi model qua
   tham so `ap`. Do la yeu cau thang cua pha 13 ("unit tests never launch real
   Demucs"), va no cung lam nhom A chay trong vai chuc mili giay.
"""
from __future__ import annotations

import ast
import json
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from apps.auto_scan_video import demucs_runner

TS = 4000          # tan so nho de phep kiem chay nhanh; MODEL GIA dung cung so


# ══════════════════════════════════════════════════════════════════════════════
#  Do nghe
# ══════════════════════════════════════════════════════════════════════════════

class ModelGia:
    """Du tham so de `buoc_phan_doan` va `tan_so_model` lam viec. Khong nap gi."""
    sources = ("drums", "bass", "other", "vocals")
    samplerate = TS
    segment = 39 / 5
    models = ()


def ap_dong_nhat(model, x, **kw):
    """Model gia: nguon dau la CHINH dau vao, ba nguon sau im lang.

    🔑 Chon ham dong nhat chu khong phai mot phep bien doi bat ky la co y: khi
       model tra ve dung dau vao, ban ra cua ca duong chia khoi **phai bang dung
       tep vao**. Mot cho ho, mot doan bi ghi hai lan, hay mot he so tron sai —
       tat ca deu hien ra ngay tren mot phep so sanh duy nhat.
    """
    import torch

    mot = x[0]
    ra = torch.stack([mot, torch.zeros_like(mot), torch.zeros_like(mot),
                      torch.zeros_like(mot)])
    return ra.unsqueeze(0)


def tep_song(tmp_path: Path, giay: float, *, ten="vao.wav") -> Path:
    """WAV stereo 16-bit co cau truc (khong phai im lang) de so sanh co nghia."""
    n = int(giay * TS)
    t = np.arange(n, dtype="float32") / TS
    trai = 0.6 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 57 * t)
    phai = 0.5 * np.sin(2 * np.pi * 330 * t + 0.7)
    x = np.vstack([trai, phai]).astype("float32")
    d = tmp_path / ten
    demucs_runner.ghi_wav(str(d), x, TS)
    return d


def doc(duong) -> np.ndarray:
    with wave.open(str(duong), "rb") as f:
        k, n = f.getnchannels(), f.getnframes()
        x = np.frombuffer(f.readframes(n), dtype="<i2").astype("float32") / 32768.0
    return x.reshape(-1, k).T


# ══════════════════════════════════════════════════════════════════════════════
#  A. So hoc chia khoi
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ra_dai_DUNG_BANG_ban_vao(tmp_path, monkeypatch):
    """Khong ho mot mau, khong thua mot mau.

    Lech do dai o day khong dung lai o day: `giai_doan_am_thanh` kiem ban nen
    lech qua 0,5 giay la nem, va xa hon nua thi moc thoi gian cua ban long tieng
    troi so voi hinh, **cang ve cuoi cang xa**.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")
    vao = tep_song(tmp_path, 130.0)
    ra = tmp_path / "stem"
    import torch
    kq = demucs_runner.tach_theo_khoi(ModelGia(), torch, str(vao), ra,
                                      thiet_bi="cpu", ap=ap_dong_nhat)
    assert kq["so_khoi"] > 1, "mau thu phai dai hon MOT khoi, khong thi khong do gi"
    goc = doc(vao)
    for ten in ModelGia.sources:
        assert doc(ra / f"{ten}.wav").shape[-1] == goc.shape[-1], f"{ten} lech do dai"


def test_model_dong_nhat_thi_ban_ra_TRUNG_KHIT_ban_vao(tmp_path, monkeypatch):
    """⭐ Phep kiem manh nhat cua nhom A, va no bat duoc CA BA loai loi mot luc.

    Voi mot model tra ve dung dau vao, duong chia khoi la mot phep sao chep vong
    ve. Neu co mot doan bi bo qua, mot doan bi ghi hai lan, hay he so tron cho
    noi khong cong lai thanh 1, ket qua lech ngay — va lech o dung cho sai.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")
    vao = tep_song(tmp_path, 130.0)
    ra = tmp_path / "stem"
    import torch
    demucs_runner.tach_theo_khoi(ModelGia(), torch, str(vao), ra,
                                 thiet_bi="cpu", ap=ap_dong_nhat)
    goc, moi = doc(vao), doc(ra / "drums.wav")
    n = min(goc.shape[-1], moi.shape[-1])
    lech = float(np.abs(goc[:, :n] - moi[:, :n]).max())
    # 1/32768 la buoc luong tu hoa cua PCM 16-bit: mot lan lam tron di-ve.
    assert lech <= 2.0 / 32768.0, f"lech dinh {lech:.6f} — khong phai sao chep vong ve"


def test_ranh_khoi_la_BOI_cua_BUOC_PHAN_DOAN(tmp_path, monkeypatch):
    """🔴 Cho quyet dinh ban tach theo khoi co GIONG ban tach ca tep hay khong.

    Do that 03/09: chua ghim luoi thi bao nen lech -42,7 dBFS tu khoi thu hai
    tro di (khoi dau trung khit, vi no bat dau o 0). Ghim roi thi 116/119 cua so
    5 giay trung khit tung mau, va ty so tin/lech di tu 27,1 dB len **54,4 dB**.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")
    vao = tep_song(tmp_path, 130.0)
    import torch
    kq = demucs_runner.tach_theo_khoi(ModelGia(), torch, str(vao), tmp_path / "s",
                                      thiet_bi="cpu", ap=ap_dong_nhat)
    buoc = demucs_runner.buoc_phan_doan(ModelGia())
    assert buoc > 0
    assert kq["khoi_mau"] % buoc == 0, (
        f"khoi {kq['khoi_mau']} khong chia het cho buoc phan doan {buoc} — "
        "ruot cac khoi sau se lech pha voi ban tach ca tep")


def test_buoc_phan_doan_khop_CONG_THUC_cua_apply_model():
    """`stride = int((1 - overlap) * int(sr * segment))` — dung cong thuc do.

    ⛔ Doc hai nguon cho cung mot con so la cach chac chan de mot ngay nao do hai
       nguon lech nhau. `CHONG_LAP` duoc **truyen thang** vao `apply_model`.
    """
    doan = int(ModelGia.samplerate * ModelGia.segment)
    cho_doi = int((1.0 - demucs_runner.CHONG_LAP) * doan)
    assert demucs_runner.buoc_phan_doan(ModelGia()) == cho_doi


def test_apply_model_nhan_overlap_va_shifts_TUONG_MINH():
    """Chot bang AST: khong duoc dua vao mac dinh cua thu vien ben thu ba.

    🔴 Mac dinh cua demucs 4.1.0 la `shifts=1` — mot lan chay o diem dich NGAU
       NHIEN roi chia cho 1. Do la toan bo nguyen nhan khien hai lan chay cung
       mot tep cho ra hai ket qua (do 03/09: bass tuong quan **-0,99**).
    """
    cay = ast.parse(Path(demucs_runner.__file__).read_text(encoding="utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "tach_theo_khoi"][0]
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id == "ap"]
    assert goi, "khong tim thay loi goi model trong `tach_theo_khoi`"
    ten = {k.arg for k in goi[0].keywords}
    assert "shifts" in ten, "khong truyen `shifts` — dua vao mac dinh la 1, tuc NGAU NHIEN"
    assert "overlap" in ten, "khong truyen `overlap` — `buoc_phan_doan` se tinh sai buoc"


def test_KHONG_nap_ca_tep_vao_RAM(tmp_path, monkeypatch):
    """⛔ `doc_wav` nap ca tep. Duong chia khoi khong duoc cham vao no.

    Do chinh la cho ma RSS di tu O(khoi) tro lai O(do dai) ma khong ai thay:
    ban ra van dung, chi la may bat dau swap voi mot video dai.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")

    def cam(*a, **k):
        raise AssertionError("duong chia khoi da goi `doc_wav` — nap ca tep vao RAM")

    monkeypatch.setattr(demucs_runner, "doc_wav", cam)
    import torch
    demucs_runner.tach_theo_khoi(ModelGia(), torch, str(tep_song(tmp_path, 130.0)),
                                 tmp_path / "s", thiet_bi="cpu", ap=ap_dong_nhat)


def test_moi_lan_doc_bi_CHAN_theo_kich_thuoc_khoi(tmp_path, monkeypatch):
    """Khong lan doc nao lon hon mot khoi cong phan phu — do la ca co che chan."""
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")
    that = demucs_runner.doc_khoi_wav
    lon_nhat = {"n": 0}

    def theo_doi(f, tu, so_mau):
        lon_nhat["n"] = max(lon_nhat["n"], int(so_mau))
        return that(f, tu, so_mau)

    monkeypatch.setattr(demucs_runner, "doc_khoi_wav", theo_doi)
    import torch
    kq = demucs_runner.tach_theo_khoi(ModelGia(), torch, str(tep_song(tmp_path, 130.0)),
                                      tmp_path / "s", thiet_bi="cpu", ap=ap_dong_nhat)
    assert lon_nhat["n"] <= kq["khoi_mau"] + kq["phu_mau"]
    assert lon_nhat["n"] < 130 * TS, "mot lan doc da om ca tep"


def test_tan_so_TEP_khac_tan_so_MODEL_thi_NEM(tmp_path, monkeypatch):
    """Lech tan so lam phep ghim luoi vo nghia mot cach im lang — phai keu."""
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")

    class KhacTanSo(ModelGia):
        samplerate = TS * 2

    import torch
    with pytest.raises(ValueError, match="tan so"):
        demucs_runner.tach_theo_khoi(KhacTanSo(), torch,
                                     str(tep_song(tmp_path, 40.0)), tmp_path / "s",
                                     thiet_bi="cpu", ap=ap_dong_nhat)


def test_KHOI_GIAY_giu_RSS_duoi_tran_da_do(tmp_path):
    """🔑 Chot chinh con so, kem phep tinh sinh ra no.

    Do that 03/09 (truoc khi chia khoi):  RSS ~ 1.253 MB + 3,35 MB moi giay.
    Voi khoi 300 giay thi phan tang them chi ~1,0 GB, va do that sau khi chia
    khoi cho 2.591 MB o **7.200 giay** — tran cua san pham.

    ⛔ Nang `KHOI_GIAY` len la doi lai chinh dieu vua sua.
    """
    du_bao_mb = 1253 + 3.352 * demucs_runner.KHOI_GIAY
    assert du_bao_mb < 4096, (
        f"khoi {demucs_runner.KHOI_GIAY}s => du bao {du_bao_mb:.0f} MB, "
        "vuot muc da do (2.591 MB o tran 7.200 giay)")
    assert demucs_runner.PHU_GIAY * 4 <= demucs_runner.KHOI_GIAY, (
        "phan phu qua lon so voi khoi — phi ton tinh lai khong con nho")


# ══════════════════════════════════════════════════════════════════════════════
#  B. Chinh sach thiet bi — khong co cho tut xuong im lang
# ══════════════════════════════════════════════════════════════════════════════

class TorchGia:
    def __init__(self, co_cuda: bool, ten: str = "CARD GIA"):
        self._co, self._ten = co_cuda, ten
        self.cuda = self

    def is_available(self):
        return self._co

    def get_device_name(self, i):
        return self._ten


def test_co_card_thi_chay_tren_card():
    assert demucs_runner.chon_thiet_bi(TorchGia(True), buoc_gpu=True) == "cuda"
    assert demucs_runner.chon_thiet_bi(TorchGia(True), buoc_gpu=False) == "cuda"


def test_KHONG_card_va_KHONG_duoc_cap_thi_CPU_la_duong_da_khai():
    """May khong co GPU thi CPU khong phai cho tut xuong — do la duong duy nhat."""
    assert demucs_runner.chon_thiet_bi(TorchGia(False), buoc_gpu=False) == "cpu"


def test_DA_CAP_card_ma_khong_thay_CUDA_thi_NEM(tmp_path):
    """🔴 Menh de trung tam cua pha 13.

    ⭐ Cai gia khong phai "cham hon mot chut": do that 03/09, CPU cham hon **9,5
       lan** (180 giay tieng: 9,2 giay tren card, 86,5 giay tren CPU). O tran
       7.200 giay do la ~37 phut GIU SUAT `tach_nguon_cuc_bo` — tuc moi phien
       chay cua moi khach khac dung lai sau no, va khong co loi nao o dau ca.
    """
    with pytest.raises(demucs_runner.ThieuCard):
        demucs_runner.chon_thiet_bi(TorchGia(False), buoc_gpu=True)


def test_main_thoat_KHAC_KHONG_khi_thieu_card(tmp_path, monkeypatch, capsys):
    """Va no phai keu ra ngoai tien trinh, khong chi nem ben trong."""
    monkeypatch.setattr(demucs_runner, "chon_thiet_bi",
                        lambda *a, **k: (_ for _ in ()).throw(
                            demucs_runner.ThieuCard("gia lap")))
    ma = demucs_runner.main(["x", str(tmp_path / "a.wav"), str(tmp_path / "r"),
                             "--buoc-gpu"])
    assert ma != 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["thieu_card"]


def test_tach_nguon_them_co_BUOC_GPU_dung_khi_duoc_cap(tmp_path, monkeypatch):
    from apps.auto_scan_video import tach_tieng

    bat = {}

    def gia(cmd, *, timeout, hoi_huy, moi_truong):
        bat["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, b'{"duong":{},"tan_so":44100}', b"")

    monkeypatch.setattr(tach_tieng, "_chay_kem_moi_truong", gia)

    tach_tieng.tach_nguon("a.wav", str(tmp_path / "s1"), buoc_gpu=True)
    assert "--buoc-gpu" in bat["cmd"]
    tach_tieng.tach_nguon("a.wav", str(tmp_path / "s2"), buoc_gpu=False)
    assert "--buoc-gpu" not in bat["cmd"], (
        "them co khi KHONG duoc cap card se lam hong moi may khong co GPU")


def test_giai_doan_bat_BUOC_GPU_theo_dung_card_da_cap(tmp_path, monkeypatch):
    """Cha biet co card hay khong; con khong. Nen cha phai noi.

    Va `tom_tat` mang **ca hai dau**: card cha CAP va card con THAY. Mot dau tu
    bao cao ca hai thi khong doi chieu duoc gi.
    """
    from apps.auto_scan_video import giai_doan_am_thanh, nhap_media, tach_tieng

    bat = {}

    class CtxGia:
        def __init__(self, uuid):
            self.gpu_uuid = uuid

        def gpu_env(self, base=None):
            return dict(base or {})

    monkeypatch.setattr(tach_tieng, "rut_ban_day_du", lambda *a, **k: a[1])
    monkeypatch.setattr(tach_tieng, "tron_nen", lambda *a, **k: a[1])
    monkeypatch.setattr(tach_tieng, "do_am_luong", lambda d: {"lufs": -14.0, "dinh_that": -1.5})
    monkeypatch.setattr(nhap_media, "soi", lambda d, **k: {
        "tan_so": tach_tieng.TAN_SO_TACH, "so_kenh": tach_tieng.SO_KENH_TACH,
        "thoi_luong": 10.0})
    monkeypatch.setattr(nhap_media, "phien_ban_ffmpeg", lambda: "ff")

    def gia_tach(vao, ra, *, gpu_env=None, buoc_gpu=False, hoi_huy=None, timeout=0):
        bat["buoc_gpu"] = buoc_gpu
        return {"duong": {}, "thiet_bi": "cuda", "ten_card": "CARD CON THAY",
                "so_khoi": 3, "khoi_giay": 298.35}

    monkeypatch.setattr(tach_tieng, "tach_nguon", gia_tach)
    monkeypatch.setattr(giai_doan_am_thanh, "_duong_doc_duoc",
                        lambda kho, khoa, tm: str(tm / "n.bin"))

    class AssetsGia:
        @staticmethod
        def bam_tep(d):
            return "abc"

        @staticmethod
        def khoa_staging(**k):
            return "k"

    monkeypatch.setattr(giai_doan_am_thanh, "assets", AssetsGia)

    class KhoGia:
        def put(self, *a, **k):
            return None

    class RunGia:
        source_key, owner_id, id = "s", "u", 1

    (tmp_path / "n.bin").write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    import builtins
    mo_that = builtins.open
    monkeypatch.setattr(builtins, "open",
                        lambda f, *a, **k: mo_that(tmp_path / "n.bin", *a, **k)
                        if str(f).endswith(".wav") else mo_that(f, *a, **k))

    kq = giai_doan_am_thanh.chay(None, KhoGia(), run=RunGia(), ctx=CtxGia("GPU-xyz"))
    assert bat["buoc_gpu"] is True, "da cap card ma khong noi cho tien trinh con"
    assert kq["tom_tat"]["gpu_cap"] == "GPU-xyz"
    assert kq["tom_tat"]["ten_card"] == "CARD CON THAY"

    giai_doan_am_thanh.chay(None, KhoGia(), run=RunGia(), ctx=CtxGia(""))
    assert bat["buoc_gpu"] is False, "khong duoc cap card ma van bat buoc phai co"


# ══════════════════════════════════════════════════════════════════════════════
#  C. Tat dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_dich_ngau_nhien_TAT():
    """`van_tay_tach` hua ban nen la ham tat dinh cua nguon. Voi `shifts` bat
    thi loi hua do SAI — va mot cache tra ve thu ma tinh lai khong ra duoc thi
    khong con la cache."""
    assert demucs_runner.DICH_NGAU_NHIEN == 0
    assert demucs_runner._dich_ngau_nhien() == 0


def test_chu_may_van_bat_lai_duoc_de_DOI_CHIEU(monkeypatch):
    monkeypatch.setenv(demucs_runner.BIEN_DICH, "1")
    assert demucs_runner._dich_ngau_nhien() == 1


# ══════════════════════════════════════════════════════════════════════════════
#  D. Khai bao tai nguyen — con so DA DO
# ══════════════════════════════════════════════════════════════════════════════

def test_vram_khai_bang_con_so_DA_DO():
    """1.673 MiB la dinh do duoc qua nam do dai (60 - 7.200 giay), khong doi.

    ⛔ Khai thua thi job cho lau hon can thiet; khai thieu thi OOM. 4.000 cu la
       mot uoc luong chua do va no thua 2,4 lan.
    """
    from apps.asv_gpu.manifest import MANIFEST

    v = MANIFEST.vram_for("asv_gpu.audio_prepare")
    assert 1673 < v <= 2500, f"{v} MB khong con bam vao dinh da do (1.673 MiB)"


def test_tran_luong_torch_van_con():
    """⚠️ An CA khi chay tren CUDA: do 03/09 thay tien trinh dinh 413% CPU o ca
    bon do dai du toan bo phep tinh nam tren card."""
    assert demucs_runner.LUONG_TORCH <= 4


def test_chot_chan_nap_model_that_trong_bo_test(monkeypatch):
    """🔴 Rao dat len NGUOI GOI chi chan nhung nguoi goi da biet.

    `test_406::test_cong_thoat_ban_nen_...` voi toi demucs gian tiep qua hang doi
    nen no khong bi rao, va da nap model THAT 16 giay moi luot gate. Chot nay
    nam o chinh cho nap model — o do chi co MOT duong.
    """
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x")
    monkeypatch.delenv("LTT_TEST_NANG", raising=False)
    with pytest.raises(demucs_runner.ChayTrongBoTest):
        demucs_runner._chan_nap_model_trong_bo_test()

    monkeypatch.setenv("LTT_TEST_NANG", "1")
    demucs_runner._chan_nap_model_trong_bo_test()      # noi ra thi duoc phep


def test_chot_dat_NGAY_TRUOC_cho_nap_model():
    """AST: `_chan_nap_model_trong_bo_test` phai dung truoc `get_model` trong `main`."""
    cay = ast.parse(Path(demucs_runner.__file__).read_text(encoding="utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    dong = {}
    for n in ast.walk(ham):
        if isinstance(n, ast.Call):
            ten = (n.func.id if isinstance(n.func, ast.Name)
                   else getattr(n.func, "attr", ""))
            dong.setdefault(ten, n.lineno)
    assert "_chan_nap_model_trong_bo_test" in dong, "`main` khong co chot"
    assert dong["_chan_nap_model_trong_bo_test"] < dong["get_model"], (
        "chot dat SAU khi nap model thi no khong chan duoc gi")


# ══════════════════════════════════════════════════════════════════════════════
#  A-bis. Cho noi — phep kiem ma model DONG NHAT khong the lam duoc
# ══════════════════════════════════════════════════════════════════════════════

def ap_theo_vi_tri(model, x, **kw):
    """Model gia tra ve mot DOC TUYEN theo vi tri TRONG KHOI, bo qua dau vao.

    🔑 Ly do phai co model thu hai nay, va no la mot lo hong that trong bo kiem
       cua chinh pha nay truoc khi kiem dot bien:

       Voi `ap_dong_nhat`, duoi cua khoi truoc va dau cua khoi sau **bang nhau**
       (ca hai deu la dau vao tai dung nhung mau do). Ma mot to hop loi cua hai
       so bang nhau thi van ra chinh so do — **voi bat ky he so nao**. Nen moi
       phep kiem dua tren model dong nhat deu MU truoc loi tron cho noi: bo han
       phep tron di, doi cho hai he so, hay dung he so 0,3/0,3 — tat ca van xanh.

    ⭐ Model nay lam hai ben mep bat dong y toi da: duoi khoi truoc gan 1, dau
       khoi sau gan 0. Khi do chi mot phep tron dung moi noi lien duoc chung, va
       moi loi tron hien ra thanh mot **buoc nhay** — dung cai ma tai nguoi nghe
       thay la tieng "cach".
    """
    import torch

    n = x.shape[-1]
    doc = torch.linspace(0.0, 1.0, n, dtype=torch.float32).expand(x.shape[1], n)
    return torch.stack([doc, doc * 0, doc * 0, doc * 0]).unsqueeze(0)


def test_KHONG_co_BUOC_NHAY_o_cho_noi_giua_hai_khoi(tmp_path, monkeypatch):
    """⛔ Do la ca ly do `PHU_GIAY` ton tai: mot buoc nhay o day la tieng "cach".

    Do that 03/09 khang dinh phep tron lam dung viec: quanh ranh khoi 300 giay,
    cua so 5 giay o dung cho noi co lech **-51,9 dBFS** — THAP hon vung xung
    quanh (-42,7), tuc khong he co gai nao tai cho noi.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")
    vao = tep_song(tmp_path, 130.0)
    ra = tmp_path / "stem"
    import torch
    kq = demucs_runner.tach_theo_khoi(ModelGia(), torch, str(vao), ra,
                                      thiet_bi="cpu", ap=ap_theo_vi_tri)
    assert kq["so_khoi"] >= 3

    y = doc(ra / "drums.wav")[0]
    nhay = np.abs(np.diff(y))
    # Doc tuyen tang deu trong mot khoi => buoc giua hai mau lien tiep rat nho.
    # Mot cho noi hong se tao ra mot buoc lon gap hang tram lan.
    nguong = 20.0 / 32768.0
    xau = np.flatnonzero(nhay > nguong)
    assert xau.size == 0, (
        f"co {xau.size} buoc nhay > {nguong:.5f} (lon nhat {nhay.max():.5f}) "
        f"tai mau {xau[:5].tolist()} — cho noi khong duoc tron muot")


def test_cha_NEM_dung_ThieuCard_khi_con_bao_thieu_card(tmp_path, monkeypatch):
    """🔴 Mat xich ma kiem dot bien tim ra la **chua co ai chot**.

    `loi.phan_loai` xep `ThieuCard` la `TAM_THOI` — dung. Nhung neu `tach_nguon`
    san moi ma thoat khac 0 thanh mot `MediaError` chung thi phep phan loai do
    **khong bao gio duoc goi voi `ThieuCard`**, va ca chuoi "tu choi doc duoc"
    dut ngay o day ma bo test van xanh.

    ⭐ Do la khac biet giua "loi keu to" va "loi noi duoc dieu gi": mot ben lam
       nen tang thu lai tren card KHAC, ben kia lam no bo cuoc nhu voi mot tep
       tieng hong.
    """
    from apps.auto_scan_video import tach_tieng
    from apps.auto_scan_video.loi import TAM_THOI, phan_loai

    def con_thieu_card(cmd, *, timeout, hoi_huy, moi_truong):
        return subprocess.CompletedProcess(
            cmd, 3, b'{"loi": "khong thay CUDA", "thieu_card": true}', b"")

    monkeypatch.setattr(tach_tieng, "_chay_kem_moi_truong", con_thieu_card)
    with pytest.raises(demucs_runner.ThieuCard):
        tach_tieng.tach_nguon("a.wav", str(tmp_path / "s"), buoc_gpu=True)

    # ... va no phai di het duong toi phep phan loai, khong dung o viec duoc nem.
    try:
        tach_tieng.tach_nguon("a.wav", str(tmp_path / "s2"), buoc_gpu=True)
    except demucs_runner.ThieuCard as exc:
        assert phan_loai(exc) == TAM_THOI, "cap card hong ma khong duoc thu lai"


def test_hong_KHAC_van_la_MediaError_chu_khong_phai_ThieuCard(tmp_path, monkeypatch):
    """Va chieu nguoc lai: dung bien moi loi cua tien trinh con thanh "thieu card".

    Mot tep tieng hong thu lai bao nhieu lan cung the — xep no vao `TAM_THOI` la
    dot ba lan thu vao mot viec khong bao gio xong.
    """
    from apps.auto_scan_video import tach_tieng
    from apps.auto_scan_video.nhap_media import MediaError

    def con_hong(cmd, *, timeout, hoi_huy, moi_truong):
        return subprocess.CompletedProcess(cmd, 1, b"", b"loi gi do khac")

    monkeypatch.setattr(tach_tieng, "_chay_kem_moi_truong", con_hong)
    with pytest.raises(MediaError) as bat:
        tach_tieng.tach_nguon("a.wav", str(tmp_path / "s"), buoc_gpu=True)
    assert not isinstance(bat.value, demucs_runner.ThieuCard)


def test_KHONG_doc_duoc_luoi_thi_NEM_chu_khong_bo_qua_im_lang(tmp_path, monkeypatch):
    """⛔ Bo phep ghim mot cach im lang la dung loai loi ca pha 13 di sua.

    Ban ra van "dung" — chi la ty so tin/lech tut tu 54,4 dB xuong 27,1 dB, va
    khong co dau hieu nao o bat cu dau. Do la mot lan xuong cap **khong quan sat
    duoc**, te hon mot lan hong.
    """
    monkeypatch.setenv(demucs_runner.BIEN_KHOI, "20")

    class KhongCoLuoi(ModelGia):
        segment = None
        models = ()

    import torch
    with pytest.raises(ValueError, match="buoc phan doan"):
        demucs_runner.tach_theo_khoi(KhongCoLuoi(), torch,
                                     str(tep_song(tmp_path, 40.0)), tmp_path / "s",
                                     thiet_bi="cpu", ap=ap_dong_nhat)
