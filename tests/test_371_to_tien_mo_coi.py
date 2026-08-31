"""Chốt `llm_gateway/to_tien.py` — cổng tự biết mình đã mồ côi chưa.

## Vì sao tệp này tồn tại

Đo trên máy B 01/09: dừng vỏ bọc `nssm.exe` thì tiến trình con **sống sót mồ
côi**, vẫn giữ cổng 8299, vẫn trả `/health` = 200 — suốt 99 giây, trong khi
`Get-Service` nói `Stopped` và không ai dựng nó dậy nữa.

Ba cái bẫy dưới đây **không phải giả định** — cả ba đều lộ ra từ một phép đo
thật, và mỗi cái đều có thể làm phép kiểm im lặng đúng lúc nó cần nói.
"""
from __future__ import annotations

import sys

import pytest

from llm_gateway.to_tien import VO_BOC, ToTien


def _moc(pid=100, ten="nssm.exe", sinh="2026-09-01T00:00:00"):
    return {"pid": pid, "ten": ten, "sinh": sinh}


class TestBayMotToTienKhongPhaiCha:
    """Cây thật là `nssm -> python -> python`. Cha trực tiếp KHÔNG phải NSSM."""

    def test_tim_nssm_o_TREN_cha_truc_tiep(self, monkeypatch):
        cay = [{"pid": 300, "ten": "python.exe", "sinh": "s3"},
               {"pid": 200, "ten": "python.exe", "sinh": "s2"},
               {"pid": 100, "ten": "nssm.exe", "sinh": "s1"}]
        monkeypatch.setattr("llm_gateway.to_tien._cay_len", lambda *a, **k: cay)
        tt = ToTien()
        assert tt.moc is not None, "neo vao cha truc tiep se BO SOT truong hop that"
        assert tt.moc["pid"] == 100
        assert tt.moc["ten"] == "nssm.exe"

    def test_khong_co_nssm_thi_khong_theo_doi_va_NOI_RO_VI_SAO(self, monkeypatch):
        """Chạy tay lúc phát triển là BÌNH THƯỜNG — nhưng phải phân biệt được.

        Gộp "chạy tay" với "đang dưới dịch vụ mà không tìm thấy" thì một lỗi
        cấu hình thật sẽ đọc lên y hệt một lượt chạy tay, và không ai đi tìm.
        """
        cay = [{"pid": 300, "ten": "python.exe", "sinh": "s3"},
               {"pid": 200, "ten": "cmd.exe", "sinh": "s2"}]
        monkeypatch.setattr("llm_gateway.to_tien._cay_len", lambda *a, **k: cay)
        tt = ToTien()
        assert tt.moc is None
        assert tt.trang_thai()["theo_doi"] is False
        assert tt.trang_thai()["mo_coi"] is None, "None = chua biet, KHAC False"
        assert "python.exe" in tt.ly_do_khong_theo_doi
        assert VO_BOC in tt.ly_do_khong_theo_doi


class TestBayHaiPhaiSoCaBaThuocTinh:
    """Windows TÁI SỬ DỤNG PID. Chỉ so PID là phép kiểm sẽ im lặng khi cần nói."""

    @pytest.fixture
    def tt(self, monkeypatch):
        monkeypatch.setattr("llm_gateway.to_tien._cay_len",
                            lambda *a, **k: [_moc()])
        return ToTien()

    def test_to_tien_con_song_thi_khong_mo_coi(self, tt, monkeypatch):
        monkeypatch.setattr("llm_gateway.to_tien._cay_len",
                            lambda *a, **k: [_moc()])
        assert tt.trang_thai()["mo_coi"] is False

    def test_khong_con_tien_trinh_nao_o_pid_do_thi_MO_COI(self, tt, monkeypatch):
        monkeypatch.setattr("llm_gateway.to_tien._cay_len", lambda *a, **k: [])
        st = tt.trang_thai()
        assert st["mo_coi"] is True
        assert "MO COI" in st["canh_bao"]

    def test_PID_duoc_cap_lai_cho_tien_trinh_KHAC_van_la_mo_coi(self, tt,
                                                               monkeypatch):
        """Cái bẫy đắt nhất: PID vẫn tồn tại nhưng là một tiến trình khác."""
        monkeypatch.setattr("llm_gateway.to_tien._cay_len",
                            lambda *a, **k: [_moc(ten="chrome.exe")])
        assert tt.trang_thai()["mo_coi"] is True, "chi so PID se BO SOT ca nay"

    def test_cung_ten_nhung_GIO_SINH_khac_van_la_mo_coi(self, tt, monkeypatch):
        """NSSM chết rồi một NSSM khác được cấp đúng PID cũ — vẫn không phải cha ta."""
        monkeypatch.setattr("llm_gateway.to_tien._cay_len",
                            lambda *a, **k: [_moc(sinh="2026-09-01T09:99:99")])
        assert tt.trang_thai()["mo_coi"] is True


class TestKhongTuThoat:
    def test_module_chi_BAO_CAO_khong_goi_exit_hay_kill(self):
        """Một tiến trình tự sát khi hiểu nhầm hoàn cảnh là một lớp lỗi mới.

        Nó sẽ sát đúng lúc đang phục vụ khách, và quyết định đó thuộc về người
        trực chứ không phải thuộc về một phép suy luận về cây tiến trình.
        """
        from pathlib import Path
        ma = Path("llm_gateway/to_tien.py").read_text(encoding="utf-8")
        # Bỏ phần docstring/chú thích: ta chốt HÀNH VI, không chốt chữ.
        than = "\n".join(d for d in ma.splitlines()
                         if not d.strip().startswith("#"))
        for cam in ("sys.exit", "os._exit", "SystemExit", "Stop-Process",
                    "terminate()", "kill()"):
            assert cam not in than, f"to_tien.py KHONG duoc tu thoat/giet: {cam}"


class TestTrenMayThat:
    @pytest.mark.skipif(sys.platform != "win32", reason="chi co y nghia tren Windows")
    def test_doc_duoc_cay_that_va_KHONG_no(self):
        """Đọc cây thật một lượt: phải ra kết quả dùng được, không ném lỗi.

        pytest không chạy dưới NSSM nên `theo_doi` sẽ là False — và đó chính là
        điều cần chốt: trường hợp bình thường không được biến thành báo động.
        """
        st = ToTien().trang_thai()
        assert st["theo_doi"] is False
        assert st["mo_coi"] is None
