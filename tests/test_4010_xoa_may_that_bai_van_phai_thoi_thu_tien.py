"""VM đã bị phá thì máy phải THÔI bị thu tiền — dù bước dọn dẹp sau đó có hỏng.

## Ca thật, tìm ra khi rà soát 25/09/2026

`jobs._xoa_may` có `try/finally` và ⛔ **không có `except`**. Thứ tự của nó:

    buoc 20  _xoa_vm_co_journal(...)      <- KHONG DAO NGUOC DUOC: VM bien mat
    buoc 78  _go_cho_dhcp(...)
    buoc 80  _tra_ip_cong_khai(...)
             _nha_tai_nguyen(...)         <- NEM `MutationNeedsReview` khi
                                             con IP `QUARANTINED`
             trang_thai_may.dat(... DA_XOA ...)
             db.commit()                  <- KHONG BAO GIO TOI

Nên một lỗi ở bất kỳ bước sau bước 20 làm `db.commit()` không chạy ⇒ bản ghi máy
giữ nguyên trạng thái cũ (`dang_chay`), trong khi VM **đã không còn tồn tại**.

Và `billing.den_han_thu` thu đúng những máy ở `("dang_chay", "da_tat")`. ⇒ Khách
bị thu **1.490 credit mỗi 30 ngày cho một VM không tồn tại**, cho tới khi có người
để ý. ⛔ Không vòng quét nào nộp lại job xoá, vì với CSDL thì máy vẫn đang chạy.

## Nguyên tắc: tách "còn phải trả tiền không" khỏi "đã dọn xong chưa"

Hai câu hỏi khác nhau, và bản cũ trả lời cả hai bằng **một** lần `commit`:

* *VM còn không?* — đã được trả lời **không thể đảo ngược** ở bước 20.
* *IP đã trả về nhà cung cấp chưa?* — có thể chưa, và có thể cần người xem.

⇒ Chốt câu thứ nhất **ngay khi nó thành sự thật** rồi `commit`; câu thứ hai làm
  sau, và nó hỏng thì ⛔ không được làm máy **sống lại trong sổ sách**.

⚠️ Đổi lại: một máy `da_xoa` có thể còn IP chưa trả. Nên `_xoa_may` ⛔ không được
   thoát sớm chỉ vì `trang_thai == "da_xoa"` — nếu còn tài nguyên chưa trả thì
   lượt chạy lại phải **đi tiếp vào phần dọn**, không thì IP rò vĩnh viễn (một IP
   không trả về là ~$3/tháng chảy mãi, và `bao_tri` không có đường bắt nó).
"""
from __future__ import annotations

import pytest

from apps.vps import jobs, trang_thai_may


class _May:
    def __init__(self, trang_thai="dang_chay", vmid=204):
        self.id = "may-4010"
        self.user_id = "u-4010"
        self.plan_id = "vps-nho"
        self.vmid = vmid
        self.trang_thai = trang_thai
        self.vong_doi = trang_thai
        self.dien_mong_muon = trang_thai_may.CHAY
        self.dien_quan_sat = trang_thai_may.CHAY
        self.tac_vu = trang_thai_may.KHONG_CO
        self.ly_do = ""
        self.ip_noi_bo = "10.50.0.7"
        self.sao_luu_luc = "2026-09-20"
        self.gateway_id = "gw-1"
        self.infrastructure_profile_id = "ho-so-1"


class _Db:
    def __init__(self, ip_con_lai=0):
        self.so_lan_commit = 0
        self.ip_con_lai = ip_con_lai

    def commit(self):
        self.so_lan_commit += 1

    def flush(self):
        pass

    def get(self, _lop, _id):
        return None

    def delete(self, _hang):
        pass

    def execute(self, _stmt):
        class _R:
            @staticmethod
            def scalars():
                return iter(())

            @staticmethod
            def scalar():
                return 0
        return _R()


@pytest.fixture()
def dung_canh(monkeypatch):
    """Dựng đủ cảnh để chạy `_xoa_may` mà không cần CSDL hay Proxmox thật."""
    from apps.vps.services import backend_factory, provisioning

    trang = {"da_pha_vm": False, "da_don": []}
    db = _Db()
    may = _May()

    monkeypatch.setattr(jobs, "_mo_db",
                        lambda: (db, type("G", (), {"close": lambda s: None})()))
    monkeypatch.setattr(jobs, "_lay_may", lambda _db, _id: may)
    monkeypatch.setattr(jobs, "_profile_for_job", lambda _db, _may: type(
        "P", (), {"public_ip_backend_type": "ovh_static_pool", "id": "ho-so-1"})())
    monkeypatch.setattr(backend_factory, "compute_backend",
                        lambda _p: type("B", (), {"client": object()})())

    def _pha(*a, **kw):
        trang["da_pha_vm"] = True

    monkeypatch.setattr(jobs, "_xoa_vm_co_journal", _pha)
    monkeypatch.setattr(jobs, "_go_cho_dhcp",
                        lambda *a, **kw: trang["da_don"].append("dhcp"))
    monkeypatch.setattr(jobs, "_tra_ip_cong_khai",
                        lambda *a, **kw: trang["da_don"].append("tra_ip"))
    monkeypatch.setattr(jobs, "_nha_tai_nguyen",
                        lambda *a, **kw: trang["da_don"].append("nha"))
    monkeypatch.setattr(provisioning, "ghi_su_kien", lambda *a, **kw: None)
    return trang, db, may


# ── 1. Dọn dẹp hỏng ⇒ vẫn phải thôi thu tiền ─────────────────────────────────

def test_nha_tai_nguyen_NEM_thi_may_van_ve_da_xoa(dung_canh, monkeypatch):
    from apps.vps.services.mutation_coordinator import MutationNeedsReview

    trang, db, may = dung_canh

    def _nem(*a, **kw):
        raise MutationNeedsReview("address association retained until readback")

    monkeypatch.setattr(jobs, "_nha_tai_nguyen", _nem)

    with pytest.raises(MutationNeedsReview):
        jobs._xoa_may({"instance_id": may.id})

    assert trang["da_pha_vm"] is True, "VM da bi pha — day la su that khong dao duoc"
    assert may.trang_thai == trang_thai_may.DA_XOA, (
        "VM khong con ma so sach con noi may dang chay => khach bi thu tien cho "
        "mot VM khong ton tai")
    assert db.so_lan_commit >= 1, "phai commit trang thai TRUOC khi don dep"


def test_tra_ip_NEM_thi_cung_vay(dung_canh, monkeypatch):
    trang, db, may = dung_canh

    def _nem(*a, **kw):
        raise RuntimeError("cong vao khong tra loi")

    monkeypatch.setattr(jobs, "_tra_ip_cong_khai", _nem)
    with pytest.raises(RuntimeError):
        jobs._xoa_may({"instance_id": may.id})
    assert may.trang_thai == trang_thai_may.DA_XOA


def test_duong_binh_thuong_van_don_du_ba_buoc(dung_canh):
    trang, db, may = dung_canh
    ra = jobs._xoa_may({"instance_id": may.id})
    assert ra["instance_id"] == may.id
    assert trang["da_don"] == ["dhcp", "tra_ip", "nha"]
    assert may.trang_thai == trang_thai_may.DA_XOA


# ── 2. Mối nối với sổ tiền: `da_xoa` phải NGOÀI danh sách thu ────────────────

def test_da_xoa_KHONG_nam_trong_cac_trang_thai_bi_thu_tien():
    """⛔ Hai chỗ khai cùng một điều thì phải có chỗ bắt khớp.

    Phép kiểm trên chỉ có nghĩa **nếu** `da_xoa` thật sự không bị thu. Đọc thẳng
    điều kiện của `billing.den_han_thu` thay vì tin vào lời docstring: ngày nào
    ai đó thêm `da_xoa` vào đó thì ca trên vẫn xanh mà tiền vẫn chảy.
    """
    import re
    from pathlib import Path

    nguon = Path("apps/vps/services/billing.py").read_text(encoding="utf-8")
    khoi = nguon[nguon.index("def den_han_thu"):]
    khoi = khoi[:khoi.index("\ndef ")]
    khop = re.search(r"trang_thai\.in_\(\(([^)]*)\)\)", khoi)
    assert khop, "khong tim ra dieu kien trang thai cua den_han_thu"
    cac = {t.strip().strip('\"\'') for t in khop.group(1).split(",") if t.strip()}
    assert trang_thai_may.DA_XOA not in cac, (
        f"`{trang_thai_may.DA_XOA}` bi thu tien: {sorted(cac)}")
    assert cac, "danh sach rong thi khong thu ai ca — cung la mot loi"


# ── 3. Chạy lại phải đi tiếp vào phần dọn, ⛔ không thoát sớm ────────────────

def test_chay_lai_khi_CON_tai_nguyen_thi_di_tiep_vao_phan_don(dung_canh,
                                                              monkeypatch):
    """Máy đã `da_xoa` nhưng IP chưa trả ⇒ lượt sau phải dọn nốt.

    ⚠️ Thoát sớm chỉ vì `trang_thai == "da_xoa"` là làm IP rò **vĩnh viễn**: một
       IP không trả về là ~$3/tháng chảy mãi, và `bao_tri` không có đường bắt nó.
    """
    trang, db, may = dung_canh
    may.trang_thai = trang_thai_may.DA_XOA
    may.vmid = None
    monkeypatch.setattr(jobs, "_con_tai_nguyen_chua_tra", lambda _db, _may: True)

    jobs._xoa_may({"instance_id": may.id})
    assert trang["da_don"] == ["dhcp", "tra_ip", "nha"], "phai don not"


def test_chay_lai_khi_da_don_XONG_thi_thoat_som(dung_canh, monkeypatch):
    """Vẫn phải idempotent: dọn xong rồi thì lượt sau không làm gì nữa."""
    trang, db, may = dung_canh
    may.trang_thai = trang_thai_may.DA_XOA
    monkeypatch.setattr(jobs, "_con_tai_nguyen_chua_tra", lambda _db, _may: False)

    ra = jobs._xoa_may({"instance_id": may.id})
    assert ra.get("da_xoa_truoc_do") is True
    assert trang["da_don"] == [] and trang["da_pha_vm"] is False
