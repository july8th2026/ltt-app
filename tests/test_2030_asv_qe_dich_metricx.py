"""QE dich MetricX (lan dich, ASV final): hop dong do_dich, ban ghim, ghi cong, bo co nhan.

Khong nap model. Mot phep chay runner THAT trong qc-venv voi HF_HOME rong de chung
minh thieu model => KhongKhaDung (bo qua khi may khong co qc-venv).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from apps.asv_gpu.do_luong import metricx, venv

GOC = Path(__file__).resolve().parents[1]
THU_MUC = GOC / "apps" / "asv_gpu" / "do_luong" / "_metricx"
BO = GOC / "docs" / "auto_scan_video_final" / "l_dich" / "bo_cap_co_nhan.json"


def _nap_ban_ghim():
    spec = importlib.util.spec_from_file_location("ban_ghim_2030", THU_MUC / "ban_ghim.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_thang_diem_va_huong_duoc_khai():
    assert metricx.THANG_DIEM == (0.0, 25.0) and metricx.THAP_LA_TOT is True
    assert metricx.CAP_DA_DO == {("zh", "vi"), ("zh", "en"), ("en", "vi"), ("vi", "en")}
    for (n, d), t in metricx.NGUONG_DO.items():
        assert metricx.THANG_DIEM[0] < t < metricx.THANG_DIEM[1]
        assert metricx.dat(t, ngon_ngu_nguon=n, ngon_ngu_dich=d)
        assert not metricx.dat(t + 0.01, ngon_ngu_nguon=n, ngon_ngu_dich=d)


def test_huong_chua_do_la_khong_kha_dung():
    with pytest.raises(venv.KhongKhaDung):
        metricx.do_dich([{"ma": "1", "nguon": "a", "dich": "b"}],
                        ngon_ngu_nguon="vi", ngon_ngu_dich="vi")


def test_rong_va_ma_trung(monkeypatch):
    monkeypatch.setattr(venv, "chay", lambda *a, **k: pytest.fail("khong duoc goi"))
    assert metricx.do_dich([], ngon_ngu_nguon="zh", ngon_ngu_dich="vi") == {}
    with pytest.raises(ValueError):
        metricx.do_dich([{"ma": 1, "nguon": "a", "dich": "b"},
                         {"ma": "1", "nguon": "c", "dich": "d"}],
                        ngon_ngu_nguon="zh", ngon_ngu_dich="vi")


def test_goi_runner_dung_giao_thuc(monkeypatch):
    goi = {}

    def gia_chay(script, dau_vao, **kw):
        goi.update(script=script, dau_vao=dau_vao, kw=kw)
        return {"diem": {c["ma"]: 1.5 for c in dau_vao["cap"]}, "thong_tin": {}}

    monkeypatch.setattr(venv, "chay", gia_chay)
    huy = lambda: False  # noqa: E731
    ra = metricx.do_dich([{"ma": 7, "nguon": "你好", "dich": "Xin chào"},
                          {"ma": "b", "nguon": "x", "dich": None}],
                         ngon_ngu_nguon="zh", ngon_ngu_dich="vi",
                         gpu_uuid="GPU-x", is_cancelled=huy)
    assert ra == {"7": 1.5, "b": 1.5}
    assert Path(goi["script"]) == THU_MUC / "chay.py" and Path(goi["script"]).is_file()
    assert goi["dau_vao"]["cap"][1] == {"ma": "b", "nguon": "x", "dich": ""}
    assert goi["kw"]["gpu_uuid"] == "GPU-x" and goi["kw"]["is_cancelled"] is huy


def test_runner_thieu_diem_la_loi(monkeypatch):
    monkeypatch.setattr(venv, "chay", lambda *a, **k: {"diem": {}})
    with pytest.raises(venv.DoLuongLoi):
        metricx.do_dich([{"ma": "1", "nguon": "a", "dich": "b"}],
                        ngon_ngu_nguon="en", ngon_ngu_dich="vi")


def test_ban_ghim_day_du():
    pb = json.loads((THU_MUC / "phien_ban.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"[0-9a-f]{40}", pb["ma_nguon"]["commit"])
    for muc in ("mo_hinh", "tokenizer"):
        assert re.fullmatch(r"[0-9a-f]{40}", pb[muc]["revision"])
        assert pb[muc]["license"] == "Apache-2.0"
        assert pb[muc]["tep"], muc
        for ten, sha in pb[muc]["tep"].items():
            assert re.fullmatch(r"[0-9a-f]{64}", sha or ""), (muc, ten)
    # ⛔ CometKiwi / XCOMET la CC BY-NC-SA — khong bao gio ghim o day.
    assert not re.search(r"(?i)kiwi|xcomet", json.dumps(pb))


def test_kiem_checksum(tmp_path):
    bg = _nap_ban_ghim()
    p = tmp_path / "w.bin"
    p.write_bytes(b"abc")
    dung = hashlib.sha256(b"abc").hexdigest()
    assert bg.kiem(p, dung) == dung
    assert bg.kiem(p, dung) == dung  # lan hai qua dau da kiem
    p.write_bytes(b"abd")
    with pytest.raises(bg.KhongKhaDung, match="KHONG_KHA_DUNG"):
        bg.kiem(p, dung)
    with pytest.raises(bg.KhongKhaDung, match="KHONG_KHA_DUNG"):
        bg.kiem(p, None)


def test_ghi_cong_apache():
    lic = (THU_MUC / "LICENSE").read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(lic) + lic).hexdigest()
    assert blob == "7a4a3ea2424c09fbe48d455aed1eaa94d9124835"  # LICENSE upstream nguyen van
    notice = (THU_MUC / "NOTICE").read_text(encoding="utf-8")
    assert "fc4978eb064670f7cc33e93ea4f52d38396b8ae6" in notice and "Modified" in notice
    src = (THU_MUC / "mt5_regression.py").read_text(encoding="utf-8")
    assert "Copyright 2024 Google LLC" in src and "MODIFIED by LTT Studios" in src
    # Model khong nam trong ma nguon.
    assert not [p for p in THU_MUC.rglob("*") if p.suffix in {".bin", ".safetensors", ".ckpt"}]


def test_bo_co_nhan_du_moi_huong():
    import tools.asv_danh_gia_qe_dich as dg

    muc = json.loads(BO.read_text(encoding="utf-8"))["muc"]
    assert {m["loai"] for m in muc} == {"lat_nghia", "bo_sot", "sai_thuc_the", "khong_dich"}
    for h, ds in dg.cap_theo_huong().items():
        assert sum(c["loai"] == "tot" for c in ds) >= 20, h
        assert sum(c["loai"] != "tot" for c in ds) >= 20, h
        assert all(c["dich"] and c["nguon"] for c in ds), h
    assert dg.auc([0.0, 1.0], [2.0, 3.0]) == 1.0 and dg.auc([1.0], [1.0]) == 0.5


@pytest.mark.skipif(not venv.san_sang(), reason="may khong co qc-venv")
def test_runner_that_thieu_model_la_khong_kha_dung(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_QC_HF_HOME", str(tmp_path / "hf-rong"))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    with pytest.raises(venv.KhongKhaDung, match="KHONG_KHA_DUNG"):
        metricx.do_dich([{"ma": "1", "nguon": "你好", "dich": "Xin chào"}],
                        ngon_ngu_nguon="zh", ngon_ngu_dich="vi", timeout_s=300)
