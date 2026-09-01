"""Chốt `platform_core/to_tien.py` (máy A) + hợp đồng khớp bản của máy B.

## Vì sao có HAI bản, và vì sao phải chốt chúng khớp nhau

`llm_gateway/to_tien.py` được deploy **sang máy B**, nơi **không có
`platform_core`**. Một `import platform_core` trong đó sẽ chạy tốt trên máy A và
**vỡ khi deploy** — vỡ ở lúc khởi động dịch vụ, tức lúc tệ nhất.

⇒ Trùng lặp là **hệ quả của ranh giới triển khai**, không phải cẩu thả. Nhưng
  hai bản trùng lặp sẽ **trôi khỏi nhau** nếu không ai giữ, và trôi âm thầm:
  một bên sửa một cái bẫy, bên kia vẫn dính. Tệp này giữ hợp đồng.
"""
from __future__ import annotations

import pytest

from platform_core import to_tien


def _moc(pid=100, ten="nssm.exe", sinh="2026-09-01T00:00:00"):
    return {"pid": pid, "ten": ten, "sinh": sinh}


class TestBaCaiBayGiongHetBanMayB:
    def test_bay1_tim_TO_TIEN_khong_phai_cha(self, monkeypatch):
        cay = [{"pid": 300, "ten": "python.exe", "sinh": "s3"},
               {"pid": 200, "ten": "python.exe", "sinh": "s2"},
               {"pid": 100, "ten": "nssm.exe", "sinh": "s1"}]
        monkeypatch.setattr(to_tien, "_cay_len", lambda *a, **k: cay)
        assert to_tien.ToTien().moc["pid"] == 100

    def test_bay2_PID_cap_lai_cho_tien_trinh_khac_van_la_mo_coi(self, monkeypatch):
        monkeypatch.setattr(to_tien, "_cay_len", lambda *a, **k: [_moc()])
        tt = to_tien.ToTien()
        monkeypatch.setattr(to_tien, "_cay_len",
                            lambda *a, **k: [_moc(ten="chrome.exe")])
        assert tt.trang_thai()["mo_coi"] is True

    def test_bay2b_cung_ten_khac_GIO_SINH_van_la_mo_coi(self, monkeypatch):
        monkeypatch.setattr(to_tien, "_cay_len", lambda *a, **k: [_moc()])
        tt = to_tien.ToTien()
        monkeypatch.setattr(to_tien, "_cay_len",
                            lambda *a, **k: [_moc(sinh="2026-09-01T23:59:59")])
        assert tt.trang_thai()["mo_coi"] is True

    def test_khong_co_nssm_thi_khong_theo_doi_va_noi_ro_vi_sao(self, monkeypatch):
        monkeypatch.setattr(to_tien, "_cay_len", lambda *a, **k: [
            {"pid": 200, "ten": "cmd.exe", "sinh": "s"}])
        tt = to_tien.ToTien()
        assert tt.trang_thai()["mo_coi"] is None, "None = chua biet, KHAC False"
        assert "cmd.exe" in tt.ly_do_khong_theo_doi


class TestKhongLuoiKhoiTao:
    """⛔ Bẫy #3, và tôi đã viết đúng nó ở bản đầu — ngay dưới một chú thích cảnh báo.

    Lười khởi tạo hỏng **đúng lúc cần nhất**: nếu lượt gọi đầu tiên rơi vào sau
    khi vỏ bọc đã chết thì nó chụp một cây **không có** `nssm`, kết luận "chạy
    tay", và im lặng mãi mãi — đúng sự cố nó sinh ra để phát hiện.
    """

    def test_chua_khoi_tao_thi_NOI_RA_chu_khong_tu_chup(self, monkeypatch):
        goi: list = []
        monkeypatch.setattr(to_tien, "_TO_TIEN", None)
        monkeypatch.setattr(to_tien, "_cay_len",
                            lambda *a, **k: goi.append(1) or [_moc()])
        st = to_tien.trang_thai()
        assert goi == [], "trang_thai() da TU CHUP -- do la luoi khoi tao"
        assert st["mo_coi"] is None
        assert "khoi_tao" in st["ly_do"]

    def test_khoi_tao_hai_lan_chi_chup_MOT_lan(self, monkeypatch):
        goi: list = []
        monkeypatch.setattr(to_tien, "_TO_TIEN", None)
        monkeypatch.setattr(to_tien, "_cay_len",
                            lambda *a, **k: (goi.append(1), [_moc()])[1])
        to_tien.khoi_tao()
        to_tien.khoi_tao()
        assert len(goi) == 1


class TestHaiBanKHONG_TROI_KHOI_NHAU:
    """Hai bản deploy đi hai máy. Không ai giữ thì chúng trôi, và trôi âm thầm."""

    @pytest.fixture
    def ban_b(self):
        from llm_gateway import to_tien as tt_b
        return tt_b

    def test_cung_ten_vo_boc(self, ban_b):
        assert to_tien.VO_BOC == ban_b.VO_BOC

    def test_cung_bo_khoa_tra_ve(self, monkeypatch, ban_b):
        for mod in (to_tien, ban_b):
            monkeypatch.setattr(mod, "_cay_len", lambda *a, **k: [_moc()])
        a = to_tien.ToTien().trang_thai()
        b = ban_b.ToTien().trang_thai()
        assert set(a) == set(b), "hai ban da troi khoi nhau ve hop dong tra ve"

    def test_cung_hanh_vi_khi_mo_coi(self, monkeypatch, ban_b):
        ra = []
        for mod in (to_tien, ban_b):
            monkeypatch.setattr(mod, "_cay_len", lambda *a, **k: [_moc()])
            tt = mod.ToTien()
            monkeypatch.setattr(mod, "_cay_len", lambda *a, **k: [])
            ra.append(tt.trang_thai())
        assert ra[0]["mo_coi"] == ra[1]["mo_coi"] is True
        assert set(ra[0]) == set(ra[1])

    def test_ca_hai_KHONG_TU_THOAT(self, ban_b):
        from pathlib import Path
        for duong in ("platform_core/to_tien.py", "llm_gateway/to_tien.py"):
            ma = Path(duong).read_text(encoding="utf-8")
            than = "\n".join(d for d in ma.splitlines()
                             if not d.strip().startswith("#"))
            for cam in ("os._exit", "Stop-Process", "terminate()", "kill()"):
                assert cam not in than, f"{duong} KHONG duoc tu thoat/giet: {cam}"
