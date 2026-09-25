"""Tạo máy KHÔNG được hỏng vì rDNS.

Một máy không có rDNS là một điểm trừ nhỏ; một máy **không giao được** vì DNS là
một sự cố. Phép kiểm này chốt thứ tự ưu tiên đó bằng cơ học.
"""
from types import SimpleNamespace


def test_rdns_nem_thi_tao_may_van_di_tiep(monkeypatch):
    from apps.vps import jobs

    def no(*a, **k):
        raise RuntimeError("Cloudflare 500")

    monkeypatch.setattr(jobs.backend_factory, "ovh_inventory_client", no)
    may = SimpleNamespace(id="x")
    assert jobs._dat_rdns_khong_chan(None, may, object(), "51.79.215.194") is False


def test_khong_co_ip_thi_khong_goi_gi(monkeypatch):
    from apps.vps import jobs

    da_goi = []
    monkeypatch.setattr(jobs.backend_factory, "ovh_inventory_client",
                        lambda *a, **k: da_goi.append(1))
    assert jobs._dat_rdns_khong_chan(None, SimpleNamespace(id="x"), object(), "") is False
    assert da_goi == []


def test_duong_tao_may_CO_goi_rdns():
    """⛔ Đo bằng AST chứ không bằng mắt: một hàm có mà không ai gọi là hàm chết —
    đúng khuôn `doi_chieu.quet` ngày 24/09."""
    import ast
    import pathlib

    cay = ast.parse(pathlib.Path("apps/vps/jobs.py").read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_tao_may")
    goi = {n.func.id for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_dat_rdns_khong_chan" in goi
    assert "_dat_firewall_may_khach" in goi
