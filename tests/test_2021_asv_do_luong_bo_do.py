"""ASV final — so dang ky bo do (`apps/asv_gpu/do_luong/bo_do.py`).

Chot: (1) thieu venv/model ⇒ `khong_kha_dung`, KHONG lui ve cong thuc tu che;
(2) mot bo do hong khong keo bo khac; (3) bo do dich cua lan "dich" cam vao
bang MOT module `do_luong/metricx.py` voi hop dong da hen; (4) phien ban tung bo
do vao van tay.
"""
from __future__ import annotations

import sys
import types

import pytest

from apps.asv_gpu.do_luong import bo_do, venv


def _dv(**kw):
    base = dict(doan_tieng=[{"ma": "s1", "tep": "x.wav", "chu": "xin chào"}],
                cap_dich=[{"ma": "s1", "nguon": "你好", "dich": "xin chào"}],
                ngon_ngu_nguon="zh", ngon_ngu_dich="vi")
    base.update(kw)
    return bo_do.DauVao(**base)


def test_thieu_qc_venv_thi_KHONG_KHA_DUNG_khong_lui(monkeypatch, tmp_path):
    monkeypatch.setenv("LTT_QC_PYTHON", str(tmp_path / "khong-co" / "python.exe"))
    monkeypatch.delitem(sys.modules, "apps.asv_gpu.do_luong.metricx", raising=False)
    kq = bo_do.chay_tat_ca(_dv())
    assert set(kq) == {b.ten for b in bo_do.BO_DO}
    for ten, r in kq.items():
        assert r["trang_thai"] == bo_do.KHONG_KHA_DUNG, (ten, r)
        assert r["ket_qua"] == {}


def test_mot_bo_do_LOI_khong_keo_bo_khac(monkeypatch):
    def hong(dv, **kw):
        raise venv.DoLuongLoi("thoat 1: CUDA OOM")

    def tot(dv, **kw):
        return {"ket_qua": {"s1": {"stoi": 0.9}}, "tai_nguyen": {"giay_tuong": 1}}

    monkeypatch.setattr(bo_do, "BO_DO", (bo_do.BoDo("a", "1", hong),
                                          bo_do.BoDo("b", "1", tot)))
    kq = bo_do.chay_tat_ca(_dv())
    assert kq["a"]["trang_thai"] == bo_do.LOI and "OOM" in kq["a"]["ly_do"]
    assert kq["b"]["trang_thai"] == bo_do.XONG
    assert kq["b"]["ket_qua"] == {"s1": {"stoi": 0.9}}


def test_huy_giua_chung_thi_NEM_khong_ghi_nhu_loi():
    with pytest.raises(venv.DoLuongLoi):
        bo_do.chay_tat_ca(_dv(), is_cancelled=lambda: True)


def test_khong_co_du_lieu_thi_khong_goi_bo_do(monkeypatch):
    goi = []
    monkeypatch.setattr(bo_do, "BO_DO", (bo_do.BoDo("dich", "1",
                                                    lambda dv, **k: goi.append(1)),))
    kq = bo_do.chay_tat_ca(_dv(cap_dich=[]))
    assert not goi and kq["dich"]["trang_thai"] == bo_do.KHONG_KHA_DUNG


def test_CHO_CAM_metricx_mot_module_la_du(monkeypatch):
    """Lan "dich" viet `do_luong/metricx.py` voi `do_dich(cap, nguon, dich, gpu)`.
    Co module ⇒ ket qua vao bao cao, khong sua them dong nao o day."""
    nhan = {}

    # ⛔ Chu ky nay phai giong `metricx.do_dich` THAT: `*` sau `cap`. Mot ban
    #    gia de dai hon ham that lam phep kiem xanh trong khi cho noi hong.
    def do_dich(cap, *, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid="",
                is_cancelled=None, **_):
        nhan.update(cap=cap, nguon=ngon_ngu_nguon, dich=ngon_ngu_dich, gpu=gpu_uuid)
        return {"s1": 3.25}

    mod = types.ModuleType("apps.asv_gpu.do_luong.metricx")
    mod.do_dich = do_dich
    monkeypatch.setitem(sys.modules, "apps.asv_gpu.do_luong.metricx", mod)
    import apps.asv_gpu.do_luong as pkg
    monkeypatch.setattr(pkg, "metricx", mod, raising=False)
    monkeypatch.setattr(bo_do, "BO_DO", tuple(b for b in bo_do.BO_DO if b.ten == "dich"))
    kq = bo_do.chay_tat_ca(_dv(), gpu_uuid="GPU-x")
    assert kq["dich"]["trang_thai"] == bo_do.XONG
    assert kq["dich"]["ket_qua"] == {"s1": {"metricx": 3.25}}
    assert nhan == {"cap": _dv().cap_dich, "nguon": "zh", "dich": "vi", "gpu": "GPU-x"}


def test_phien_ban_gom_MOI_bo_do_va_doi_khi_mot_bo_do_doi(monkeypatch):
    cu = bo_do.phien_ban()
    for b in bo_do.BO_DO:
        assert f"{b.ten}:{b.phien_ban}" in cu
    monkeypatch.setattr(bo_do, "BO_DO", bo_do.BO_DO[:1] + (
        bo_do.BoDo(bo_do.BO_DO[1].ten, "khac", bo_do.BO_DO[1].chay),) + bo_do.BO_DO[2:])
    assert bo_do.phien_ban() != cu


def test_squim_weights_GHIM_sha256_va_KHONG_dung_ban_NC():
    from apps.asv_gpu.do_luong import giong, squim
    assert len(squim.SHA256_WEIGHTS) == 64
    assert squim.URL_WEIGHTS.endswith("squim_objective_dns2020.pth")
    nguon = open(squim.__file__, encoding="utf-8").read() + open(
        squim.SCRIPT, encoding="utf-8").read()
    assert "SQUIM_SUBJECTIVE" not in nguon.replace("⛔ `SQUIM_SUBJECTIVE`", "")
    # ASR ghim commit, khong tai ban "main" troi noi.
    for _repo, rev in giong.MODEL_GHIM.values():
        assert len(rev) == 40


def test_model_asr_chua_ghim_thi_KHONG_KHA_DUNG():
    from apps.asv_gpu.do_luong import giong
    with pytest.raises(venv.KhongKhaDung):
        giong.do_giong([], ngon_ngu="vi", model="tiny-khong-ghim")
