"""Bo do QC chi dung card khi CO lease — va dung nó khi co (lan `gpu-may-a`).

⭐ Vi sao co tep nay: do 24/09 tren phim khach that cho SQUIM **GPU 3,87 s / CPU
   9,38 s** (2,4x) va ECAPA gioi **GPU 5,33 s / CPU 13,58 s** (2,5x), diem lech
   <= 0,0002 giua hai duong ⇒ card la duong dung. Nhung ban cu chon thiet bi
   bang `torch.cuda.is_available()`, tuc:

     * co lease ma ghim hong ⇒ **lui CPU im lang** (bao cao doc y nhu co card);
     * KHONG co lease ⇒ **lay card ngoai so sach**, tranh voi `voice_sidecar`
       dang phuc vu khach that tren card DUY NHAT cua may A.

   Dung hong ma `demucs_runner.chon_thiet_bi` da ghi lai 23/09, lap lai o bo do.

🔴 Va mot bay do duoc trong chinh lan do: `CUDA_VISIBLE_DEVICES=""` truyen qua
   `subprocess` tren Windows bi **xoa han**, nen tien trinh con thay DU MOI card.
   Mot nhanh "CPU" nhu vay khong co trieu chung nao — no chay tren card va bao
   `thiet_bi: cuda`. Phai la `"-1"`. `test_chan_card_dung_tru_mot_KHONG_dung_chuoi_rong`
   chot dung dieu do.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

import pytest

from apps.asv_gpu.do_luong import _runner, gioi, metricx, squim, venv

GOC_DO_LUONG = Path(_runner.__file__).parent


# ── Gia lap torch: khong phu thuoc venv cua trinh thong dich chay test ───────
#
# 🔴 `test_406::test_torch_o_may_nay_la_ban_CPU` (da bo 23/09) xanh suot 20 ngay
#    vi no hoi `torch.cuda.is_available()` cua **trinh thong dich chay test**
#    trong khi ma that chay o venv worker. Nen o day khong hoi torch that cua
#    ai ca — tiem mot torch gia de CA HAI nhanh deu duoc chay.
@pytest.fixture
def torch_gia(monkeypatch):
    def dat(co_cuda: bool):
        m = types.ModuleType("torch")
        m.cuda = types.SimpleNamespace(is_available=lambda: co_cuda)
        monkeypatch.setitem(sys.modules, "torch", m)
        return m
    cu = sys.modules.get("torch")
    yield dat
    if cu is not None:
        sys.modules["torch"] = cu


# ── 1. chon_thiet_bi: bon o cua bang su that ────────────────────────────────

def test_co_lease_va_thay_card_thi_DUNG_card(torch_gia):
    torch_gia(True)
    thiet_bi, ly_do = _runner.chon_thiet_bi({"buoc_gpu": True})
    assert thiet_bi == "cuda", ly_do


def test_co_lease_ma_torch_khong_thay_card_thi_KEU_chu_khong_lui_CPU(torch_gia, capsys):
    """⛔ Day la o quan trong nhat. Lui CPU im lang o day nghia la giu nguyen
    suat `tach_nguon_cuc_bo` hang phut trong khi bao cao doc y nhu co card."""
    torch_gia(False)
    with pytest.raises(SystemExit) as e:
        _runner.chon_thiet_bi({"buoc_gpu": True})
    assert e.value.code == 3
    assert "KHONG_KHA_DUNG" in capsys.readouterr().out


def test_khong_lease_thi_KHONG_cham_card_du_thay_card(torch_gia):
    """Ban cu tra `"cuda"` o dung o nay — tuc VRAM ngoai so sach."""
    torch_gia(True)
    thiet_bi, ly_do = _runner.chon_thiet_bi({"buoc_gpu": False})
    assert thiet_bi == "cpu"
    assert "lease" in ly_do          # ly do phai NOI RA, khong im lang


def test_khong_lease_va_may_khong_co_card(torch_gia):
    torch_gia(False)
    assert _runner.chon_thiet_bi({})[0] == "cpu"


def test_thieu_khoa_buoc_gpu_thi_coi_nhu_KHONG_co_lease(torch_gia):
    """Ban khai cu (`dau_vao` khong co `buoc_gpu`) phai lech ve phia AN TOAN."""
    torch_gia(True)
    assert _runner.chon_thiet_bi({})[0] == "cpu"


# ── 2. Ghim card qua bien moi truong ────────────────────────────────────────

def test_chan_card_dung_tru_mot_KHONG_dung_chuoi_rong():
    from platform_core import gpu as gpu_mod

    assert gpu_mod.KHONG_CARD == "-1", (
        'chuoi rong bi Windows xoa han khoi moi truong tien trinh con ⇒ tien '
        'trinh con thay du moi card. Xem docstring dau tep.')
    assert gpu_mod.env_khong_card({"PATH": "x"})["CUDA_VISIBLE_DEVICES"] == "-1"
    env = venv._moi_truong("", chan_card=True)
    assert env["CUDA_VISIBLE_DEVICES"] == gpu_mod.KHONG_CARD


def test_gia_tri_che_card_nam_o_platform_core_chu_khong_go_trong_app():
    """I11: app khong tu cham bien moi truong chon card (`test_401`/`test_406`).
    Va cai bay "chuoi rong" chi dang duoc ghi MOT cho."""
    van = Path(venv.__file__).read_text(encoding="utf-8")
    cay = ast.parse(van)
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and nut.value == "CUDA_VISIBLE_DEVICES":
            raise AssertionError("venv.py go thang ten bien — phai qua "
                                 "platform_core.gpu.env_khong_card")


def test_co_lease_thi_ghim_dung_UUID_duoc_cap():
    env = venv._moi_truong("GPU-deadbeef", chan_card=True)
    assert env["CUDA_VISIBLE_DEVICES"] == "GPU-deadbeef"


def test_khong_chan_card_thi_khong_tu_dat_bien(monkeypatch):
    """Mac dinh phai giu nguyen hanh vi cu — xem `metricx` o muc 4."""
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    assert "CUDA_VISIBLE_DEVICES" not in venv._moi_truong("", chan_card=False)


# ── 3. Hai bo do DA doi sang duong lease ────────────────────────────────────

def _bat_chay(monkeypatch):
    goi: dict = {}

    def gia(script, dau_vao, **kw):
        goi["script"], goi["vao"], goi["kw"] = script, dau_vao, kw
        # `diem` cho metricx, `ket_qua` cho squim/gioi — mot ban gia phuc vu ca ba.
        return {"ket_qua": {}, "tai_nguyen": {},
                "diem": {str(c["ma"]): 1.0 for c in dau_vao.get("cap") or ()}}
    monkeypatch.setattr(venv, "chay", gia)
    return goi


@pytest.mark.parametrize("gpu_uuid, mong_doi", [("GPU-abc", True), ("", False)])
def test_squim_khai_buoc_gpu_theo_lease_va_chan_card(monkeypatch, gpu_uuid, mong_doi):
    goi = _bat_chay(monkeypatch)
    squim.do_squim([{"ma": "d1", "tep": "x.wav"}], gpu_uuid=gpu_uuid)
    assert goi["vao"]["buoc_gpu"] is mong_doi
    assert goi["kw"]["chan_card"] is True
    assert goi["kw"]["gpu_uuid"] == gpu_uuid


@pytest.mark.parametrize("gpu_uuid, mong_doi", [("GPU-abc", True), ("", False)])
def test_gioi_khai_buoc_gpu_theo_lease_va_chan_card(monkeypatch, gpu_uuid, mong_doi):
    goi = _bat_chay(monkeypatch)
    gioi.do_gioi([{"ma": "c1", "tep": "x.wav"}], gpu_uuid=gpu_uuid)
    assert goi["vao"]["buoc_gpu"] is mong_doi
    assert goi["kw"]["chan_card"] is True


@pytest.mark.parametrize("ten", ["squim_runner.py", "gioi_runner.py"])
def test_runner_khong_con_chon_thiet_bi_bang_is_available(ten):
    """Doc AST, khong chay model. Mot `is_available()` quay lai o day la mot
    duong lay card khong qua lease — va no im lang."""
    cay = ast.parse((GOC_DO_LUONG / ten).read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if isinstance(nut, ast.IfExp):
            assert "is_available" not in ast.unparse(nut.test), (
                f"{ten}: chon thiet bi bang is_available, phai qua "
                f"_runner.chon_thiet_bi")


@pytest.mark.parametrize("ten", ["squim_runner.py", "gioi_runner.py"])
def test_runner_tra_ly_do_chon_thiet_bi_ra_hop_dong(ten):
    """Mot lan chay CPU khong bao gio duoc doc giong mot lan chay co card."""
    van = (GOC_DO_LUONG / ten).read_text(encoding="utf-8")
    assert "ly_do_thiet_bi=ly_do_thiet_bi" in van


# ── 4. MetricX HOAN co chu y — chot lai de khong ai "don cho dong bo" ───────

def test_metricx_CHUA_chan_card_va_day_la_co_y(monkeypatch):
    """⛔ **Hoan co chu y, dieu phoi chot 24/09.** Do duoc: MetricX-24 o lo 6 cap
    GPU 10,49 s / CPU 10,31 s ⇒ **0,98x**, card khong nhanh hon ma an 2,6 GiB.
    Nhung diem lech **<= 0,031** giua bf16 (GPU) va fp32 (CPU), va buoc B2 cua
    thang cong sap dung MetricX lam **trong tai** cho ca viec siet dich (xac
    thuc tren FLORES, roi so `ltt-3.5` voi moc `ltt-3.8`).

    ⇒ Doi duong chay GIUA mot chien dich do la tu tao bien thu hai: khi so dich
      doi, khong biet do **model** hay do **bo cham doi do chinh xac so hoc**.
      Va cache dung chung se **tron hai thang diem** — dung cai `PHIEN_BAN` ton
      tai de chan.

    Ba dieu kien mo lai: (1) B2 xong, (2) co phep do o **lo lon**, (3) nang
    `PHIEN_BAN` bo do cung luot.
    """
    goi = _bat_chay(monkeypatch)
    monkeypatch.setattr(metricx, "CAP_DA_DO", {("zh", "vi")})
    metricx.do_dich([{"ma": "c1", "nguon": "a", "dich": "b"}],
                    ngon_ngu_nguon="zh", ngon_ngu_dich="vi", gpu_uuid="")
    assert "chan_card" not in goi["kw"], (
        "MetricX dang HOAN sang CPU/chan card — xem docstring, dung 'dong bo "
        "hoa' voi squim/gioi truoc khi B2 xong")
    assert "buoc_gpu" not in goi["vao"]
