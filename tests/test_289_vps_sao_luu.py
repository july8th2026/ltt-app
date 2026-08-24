"""H39/G9 — ảnh chụp hằng tuần, giữ đúng một bản, và khôi phục.

Trang bán hứa từ trước khi có mã nào làm: *"sao lưu hằng tuần, giữ 1 bản"*.
Đi làm thật thì `vzdump` không chạy được — kho `dir` duy nhất trên node còn
**2,2 GiB**. Thứ hạ tầng này làm được là **ảnh chụp**, và nó nằm trên **cùng kho**
với đĩa gốc.

Nên bộ test này kiểm cả hai mặt:

* cơ chế đúng — chụp đúng nhịp, giữ đúng một bản, **tạo trước rồi mới xoá**;
* và **trang bán nói đúng thứ khách nhận** — hứa "sao lưu" rồi giao một ảnh chụp
  là loại lời hứa người ta chỉ phát hiện sai đúng vào lúc mất dữ liệu.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps.services import sao_luu

NOW = datetime(2026, 8, 24, 19, 30, tzinfo=timezone.utc)


class _May:
    def __init__(self, vmid=200, trang_thai="dang_chay", luc=None):
        self.id = "may-1"
        self.vmid = vmid
        self.trang_thai = trang_thai
        self.sao_luu_luc = luc


class _Client:
    def __init__(self, anh=(), hong_xoa=False):
        self.anh = [{"name": x} for x in anh]
        self.hong_xoa = hong_xoa
        self.thao_tac: list[tuple[str, str]] = []

    def danh_sach_anh(self, vmid):
        return list(self.anh)

    def chup_anh(self, vmid, ten, *, mo_ta=""):
        self.thao_tac.append(("chup", ten))
        self.anh.append({"name": ten})
        return "UPID:chup"

    def xoa_anh(self, vmid, ten):
        if self.hong_xoa:
            raise RuntimeError("Proxmox tu choi xoa")
        self.thao_tac.append(("xoa", ten))
        self.anh = [x for x in self.anh if x["name"] != ten]
        return "UPID:xoa"


# ── 1. Tên ảnh ──────────────────────────────────────────────────────────────

def test_ten_anh_hop_le_voi_proxmox():
    """Proxmox chỉ nhận `[A-Za-z0-9_-]` và tên phải **bắt đầu bằng chữ**, nên
    `2026-08-24` không dùng được."""
    import re

    ten = sao_luu.ten_anh(NOW)
    assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", ten), ten
    assert ten == "ltt20260824_1930"


def test_ten_anh_sap_xep_duoc_theo_THOI_GIAN():
    """`chup_va_don` chọn bản để giữ bằng cách sắp xếp **chuỗi**. Một định dạng
    mà thứ tự chuỗi khác thứ tự thời gian sẽ xoá nhầm bản mới, giữ bản cũ."""
    ten = [sao_luu.ten_anh(NOW + timedelta(days=d)) for d in (0, 5, 40, 400)]
    assert ten == sorted(ten)


def test_chi_nhan_anh_CUA_TA():
    """Ảnh chủ nhà tự tạo bằng tay trên Proxmox **không phải việc của vòng bảo
    trì** — xoá nhầm một ảnh người khác đang dựa vào là mất dữ liệu của họ."""
    assert sao_luu.cua_ta("ltt20260824_1930") is True
    assert sao_luu.cua_ta("ltt20260824") is True
    for la in ("truoc-khi-nang-cap", "backup1", "", "ltt", "lttabc", None):
        assert sao_luu.cua_ta(la) is False, la


def test_ten_anh_doc_duoc_cho_khach():
    assert sao_luu.doc_duoc("ltt20260824_1930") == "24/08/2026 19:30"
    assert sao_luu.doc_duoc("khong-phai-cua-ta") == "khong-phai-cua-ta"


# ── 2. Tới kỳ chụp chưa ─────────────────────────────────────────────────────

def test_may_chua_chup_lan_nao_thi_den_han_ngay():
    assert sao_luu.den_han_chup(_May(luc=None), now=NOW) is True


def test_chup_lai_sau_dung_bay_ngay():
    assert sao_luu.den_han_chup(
        _May(luc=NOW - timedelta(days=6, hours=23)), now=NOW) is False
    assert sao_luu.den_han_chup(
        _May(luc=NOW - timedelta(days=7)), now=NOW) is True


def test_may_dang_tao_hoac_da_xoa_thi_khong_chup():
    """Chụp giữa lúc job đang dựng máy là chụp một cái vỏ."""
    for tt in ("dang_tao", "da_xoa"):
        assert sao_luu.den_han_chup(_May(trang_thai=tt), now=NOW) is False


def test_may_chua_co_vmid_thi_khong_chup():
    assert sao_luu.den_han_chup(_May(vmid=None), now=NOW) is False


def test_may_BI_TREO_thi_VAN_chup():
    """Máy treo còn 7 ngày ân hạn trước khi bị xoá. Ngừng chụp trong 7 ngày đó
    là một hình phạt kèm mà không ai công bố — và khách trả tiền lại rồi mới
    phát hiện bản chụp của họ dừng từ tuần trước."""
    assert sao_luu.den_han_chup(_May(trang_thai="bi_treo"), now=NOW) is True


def test_moc_khong_co_mui_gio_van_so_sanh_duoc():
    """Postgres trả `datetime` có múi giờ, SQLite thì không. So một cái naive với
    một cái aware là `TypeError` — và nó chỉ nổ trên **một** trong hai engine."""
    tho = (NOW - timedelta(days=10)).replace(tzinfo=None)
    assert sao_luu.den_han_chup(_May(luc=tho), now=NOW) is True


# ── 3. Chụp và dọn ──────────────────────────────────────────────────────────

def test_TAO_TRUOC_roi_moi_XOA():
    """Xoá trước thì có một khoảng — dài bằng thời gian tạo — mà khách **không có
    bản nào**, và đó đúng là khoảng mà một sự cố sẽ tìm tới."""
    c = _Client(anh=["ltt20260817_1930"])
    sao_luu.chup_va_don(c, _May(), now=NOW)
    assert [x[0] for x in c.thao_tac] == ["chup", "xoa"]


def test_giu_dung_MOT_ban():
    c = _Client(anh=["ltt20260803_1930", "ltt20260810_1930", "ltt20260817_1930"])
    ten = sao_luu.chup_va_don(c, _May(), now=NOW)
    con = sorted(x["name"] for x in c.anh)
    assert con == [ten], f"phai chi con ban vua chup, dang con {con}"


def test_KHONG_dung_toi_anh_nguoi_khac_tao():
    c = _Client(anh=["truoc-khi-nang-cap", "ltt20260817_1930"])
    sao_luu.chup_va_don(c, _May(), now=NOW)
    assert "truoc-khi-nang-cap" in [x["name"] for x in c.anh]


def test_xoa_ban_cu_that_bai_thi_VAN_giu_ban_moi():
    """Bản mới đã tạo xong, nên một lỗi dọn dẹp không có lý do gì làm hỏng cả
    lượt bảo trì. Bản cũ thừa chỉ tốn chỗ."""
    c = _Client(anh=["ltt20260817_1930"], hong_xoa=True)
    ten = sao_luu.chup_va_don(c, _May(), now=NOW)
    assert ten in [x["name"] for x in c.anh]


def test_anh_moi_nhat_tra_ve_ban_MOI_nhat():
    c = _Client(anh=["ltt20260803_1930", "ltt20260817_1930", "tay-lam"])
    assert sao_luu.anh_moi_nhat(c, 200) == "ltt20260817_1930"


def test_chua_co_anh_thi_tra_chuoi_rong():
    assert sao_luu.anh_moi_nhat(_Client(), 200) == ""


# ── 4. Không kèm RAM ────────────────────────────────────────────────────────

def test_anh_KHONG_kem_RAM():
    """`vmstate` ghi cả bộ nhớ ra đĩa — thêm vài GB mỗi máy mỗi tuần cho một thứ
    không ai cần khi khôi phục. Và nó làm ảnh chụp mất hàng chục giây thay vì
    vài giây."""
    import inspect

    from apps.vps.services.proxmox import ProxmoxClient

    assert '"vmstate": 0' in inspect.getsource(ProxmoxClient.chup_anh)


# ── 5. Vòng bảo trì gọi nó ──────────────────────────────────────────────────

def test_vong_bao_tri_CO_chup(monkeypatch):
    from apps.vps import bao_tri

    da = []
    monkeypatch.setattr(sao_luu, "chup_va_don",
                        lambda c, m, now=None: da.append(m.id) or "ltt1")
    monkeypatch.setattr(bao_tri.billing, "ghi_su_kien", lambda *a, **kw: None)

    class _Db:
        def execute(self, *a, **kw):
            class _K:
                def scalars(self_inner):
                    return iter([_May(luc=None)])
            return _K()

        def commit(self):
            pass

    n = bao_tri._chup_anh_den_han(_Db(), _Client(), now=NOW)
    assert n == 1 and da == ["may-1"]


def test_chua_cau_hinh_proxmox_thi_KHONG_danh_dau_da_chup():
    """Đánh dấu mà chưa chụp là ghi vào sổ một bản không tồn tại — và khách chỉ
    phát hiện lúc cần khôi phục, tức lúc tệ nhất."""
    from apps.vps import bao_tri

    assert bao_tri._chup_anh_den_han(None, None, now=NOW) == 0


# ── 6. Trang bán phải nói ĐÚNG thứ khách nhận ───────────────────────────────

def test_trang_ban_KHONG_goi_no_la_sao_luu():
    from pathlib import Path

    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "Ảnh chụp hằng tuần" in t
    assert "KHÔNG thay thế bản sao lưu" in t
    assert "Sao lưu hằng tuần, giữ 1 bản. Dữ liệu quan trọng" not in t, (
        "cau cu hua 'sao luu' — thu ha tang lam duoc la anh chup")


def test_khoi_phuc_doi_go_dung_ten_may():
    """Cùng khuôn với "Cài lại": không hoàn tác được, và nó nằm cạnh những nút
    vô hại."""
    import inspect

    from apps.vps import routes

    nguon = inspect.getsource(routes.khoi_phuc_may)
    assert "xac_nhan" in nguon
    assert "may.ten or may.id[:8]" in nguon


def test_khoi_phuc_TAT_MAY_truoc():
    """Proxmox từ chối `rollback` một máy đang chạy nếu ảnh không kèm RAM — và
    ảnh của ta cố ý không kèm RAM."""
    import inspect

    from apps.vps import routes

    nguon = inspect.getsource(routes.khoi_phuc_may)
    assert nguon.index("tat_cung") < nguon.index("khoi_phuc_anh")
