"""
test_149 - lay URL truc tiep (R2) khong duoc nuot loi that.

Truoc 2026-08-06, 15 cho goi `url_for`/`put_url` trong repo deu boc bang
`except Exception:  # noqa: BLE001`, kem chu thich "local storage has no direct
URL". Chu thich do SAI: `Storage.url_for` cua backend cuc bo **tra None**, khong
nem. Nen khoi except ay khong he bao ve dieu no tu nhan.

Cai no thuc su lam la nuot loi THAT cua R2 - thieu cau hinh, sai khoa, mat mang
- roi lang le quay ve phuc vu file qua tunnel. Dung thu H10 sinh ra de tranh:
moi thu van "chay", cho toi khi ai do tai file lon va dam tran 100MB cua
Cloudflare, va khong co log nao chi ra vi sao.
"""
from __future__ import annotations

import ast
import logging
import pathlib

import pytest

from platform_core.storage import Storage, StorageError

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_backend_cuc_bo_tra_none_chu_khong_nem():
    """Tien de cua ca file nay. Sai o day thi khoi except kia lai co ly."""
    base = Storage()
    assert base.url_for("bat/ky/key.png") is None
    assert base.put_url("bat/ky/key.png") is None


def test_loi_bat_ngo_cua_r2_van_degrade_nhung_PHAI_vao_log(caplog):
    """Trang khong duoc vo vi R2 chap chon, nhung su co phai nhin thay duoc."""
    class R2Chet(Storage):
        def url_for(self, key, ttl_s=900):
            raise RuntimeError("boto3: khong ket noi duoc")

        def put_url(self, key, ttl_s=900, content_type="application/octet-stream"):
            raise RuntimeError("boto3: khong ket noi duoc")

    broken = R2Chet()
    with caplog.at_level(logging.ERROR, logger="platform_core.storage"):
        assert broken.try_url_for("ommi/u1/a.png") is None
        assert broken.try_put_url("ommi/u1/a.png") is None
    ghi = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(ghi) == 2, "loi bat ngo cua R2 bi nuot ma khong ghi log"
    assert all(r.exc_info for r in ghi), "log thieu traceback -> khong debug duoc"


def test_traceback_storage_loc_bi_mat_truoc_khi_ghi_log(caplog):
    """Giữ traceback để debug nhưng không giữ credential từ SDK/provider."""
    class R2RoBiMat(Storage):
        def url_for(self, key, ttl_s=900):
            raise RuntimeError("token=storage-secret owner@example.com")

    with caplog.at_level(logging.ERROR, logger="platform_core.storage"):
        assert R2RoBiMat().try_url_for("jobs/u1/file.mp4") is None

    assert "storage-secret" not in caplog.text
    assert "owner@example.com" not in caplog.text
    assert "[Filtered]" in caplog.text


def test_storage_error_thi_im_lang_vi_da_biet_truoc():
    """Thieu cau hinh R2 hay key sai la truong hop DA LUONG TRUOC, khong phai
    su co - bao dong moi lan tai anh se lam log vo dung."""
    class ChuaCauHinh(Storage):
        def url_for(self, key, ttl_s=900):
            raise StorageError("R2 thieu cau hinh LTT_R2_*")

    assert ChuaCauHinh().try_url_for("k") is None


@pytest.mark.parametrize("meth", ["url_for", "put_url"])
def test_khong_route_nao_boc_presign_bang_except_rong(meth):
    """Bat rong quanh presign = quay lai dung cai bay cu.

    Cho phep bat HEP (`StorageError`, `OSError`) vi do la hop dong cua storage.
    """
    offenders = []
    for path in sorted((ROOT / "apps").rglob("*.py")) + sorted((ROOT / "server").rglob("*.py")):
        if {"__pycache__", "vendor", "node_modules"} & set(path.parts):
            continue
        src = path.read_text(encoding="utf-8", errors="ignore")
        if f".{meth}(" not in src:
            continue
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Try):
                continue
            goi = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == meth for n in ast.walk(node))
            if not goi:
                continue
            for handler in node.handlers:
                t = handler.type
                if t is None or (isinstance(t, ast.Name) and
                                 t.id in {"Exception", "BaseException"}):
                    offenders.append(
                        f"{path.relative_to(ROOT).as_posix()}:{handler.lineno}")
    assert not offenders, (
        f"boc `{meth}` bang except rong: {offenders} - dung "
        f"`storage.try_{meth}()` de loi that van vao log")
