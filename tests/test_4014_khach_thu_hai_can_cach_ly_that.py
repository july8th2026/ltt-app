"""Khách thứ hai trên một node chưa có cách ly ⇒ ⛔ KHÔNG bán.

## Vì sao cửa này tồn tại

Đo 25-26/09/2026: `ipfilter`/`macfilter` đặt trên từng VM là **no-op** vì Proxmox
đòi một phép AND ba tầng và hai tầng đang tắt (`cluster/firewall/options` không có
`enable`, NIC `firewall=0`). ⇒ Không có lớp nào chặn khách A giả mạo IP/MAC của
khách B trên cùng bridge `vmbr1`.

Và đo tiếp: node hiện có **2 máy, cùng MỘT chủ**. ⇒ Mọi rủi ro nói trên là rủi ro
**giữa các khách**, nên hôm nay chúng **chưa tồn tại** — không ai giả mạo chính mình.
Chúng bật lên **đúng khoảnh khắc một khách lạ đầu tiên có máy trên cùng node**.

⇒ Nên cái mốc đúng ⛔ không phải *"bật tường lửa ngay"* (ngắt máy chủ dự án đang làm
  việc cho một rủi ro chưa có), mà là *"⛔ không được có khách thứ hai trong lúc còn
  hở"*. Và nó phải là một cửa **cơ học**, ⛔ không phải một việc cần ai nhớ:

🔴 Một việc "cần làm trước khi có khách thật" mà chỉ nằm trong đầu người hoặc trong
   một tệp kế hoạch thì **sẽ** bị quên — đúng lúc nó quan trọng nhất, vì lúc ấy ta
   đang mừng vì có khách mới.

## Hai điều cửa này ⛔ KHÔNG làm

* ⛔ Không chặn chủ hiện tại mua thêm máy: rủi ro là **cross-tenant**, và một chủ
  thêm máy thứ ba của chính mình ⛔ không tạo ra khách thứ hai nào.
* ⛔ Không chặn khi node còn trống: máy đầu tiên của một chủ mới trên một node
  **chưa có ai** thì cũng ⛔ không có ai để giả mạo.

## Đo không được thì CHẶN, ⛔ không phải cho qua

Hỏi Proxmox ba tầng có thể thất bại (khoá hỏng, mạng). Lúc đó ta ⛔ không biết có
cách ly hay không — và "chưa đo được" ⛔ không bao giờ được thành "ổn" ở một cửa an
ninh. Chặn một lượt bán là mất một đơn; bán sai là mất niềm tin của **cả hai** khách.
"""
from __future__ import annotations

from apps.vps import cach_ly


class _May:
    def __init__(self, user_id, vmid, trang_thai="dang_chay"):
        self.user_id = user_id
        self.vmid = vmid
        self.trang_thai = trang_thai


class _Db:
    def __init__(self, cac_may):
        self._may = cac_may

    def execute(self, _stmt):
        may = self._may

        class _R:
            @staticmethod
            def scalars():
                return iter(may)
        return _R()


def _profile():
    return type("P", (), {"id": "ho-so-1"})()


def _do(hieu_luc, ly_do=""):
    return lambda vmid: (hieu_luc, ly_do)


# ── 1. Node một chủ: ⛔ không chặn gì ────────────────────────────────────────

def test_chu_hien_tai_mua_them_may_thi_KHONG_chan(monkeypatch):
    db = _Db([_May("u-a", 204), _May("u-a", 208)])
    chan, ly_do = cach_ly.chan_khach_moi(
        db, _profile(), "u-a", do_hieu_luc=_do(False, "cum chua bat"))
    assert chan is False, ly_do


def test_node_trong_thi_khach_moi_van_mua_duoc():
    db = _Db([])
    chan, _ = cach_ly.chan_khach_moi(
        db, _profile(), "u-moi", do_hieu_luc=_do(False, "cum chua bat"))
    assert chan is False


def test_may_da_xoa_khong_tinh_la_mot_chu():
    """Một chủ cũ đã xoá hết máy thì không còn ai trên node để giả mạo."""
    db = _Db([_May("u-cu", 204, trang_thai="da_xoa")])
    chan, _ = cach_ly.chan_khach_moi(
        db, _profile(), "u-moi", do_hieu_luc=_do(False, "cum chua bat"))
    assert chan is False


# ── 2. Khách thứ hai + chưa cách ly ⇒ CHẶN ──────────────────────────────────

def test_khach_LA_tren_node_da_co_chu_khac_va_chua_cach_ly_thi_CHAN():
    db = _Db([_May("u-a", 204)])
    chan, ly_do = cach_ly.chan_khach_moi(
        db, _profile(), "u-b", do_hieu_luc=_do(False, "cum chua bat, nic firewall=0"))
    assert chan is True
    assert "cum chua bat" in ly_do, ly_do


def test_khach_LA_nhung_DA_cach_ly_thi_cho_qua():
    db = _Db([_May("u-a", 204)])
    chan, ly_do = cach_ly.chan_khach_moi(
        db, _profile(), "u-b", do_hieu_luc=_do(True))
    assert chan is False, ly_do


def test_chi_mot_may_HO_cung_du_de_chan():
    """⛔ Không lấy "phần lớn máy đã cách ly" làm đủ: một máy hở là một đường vào."""
    def _tung_may(vmid):
        return (vmid == 204, "" if vmid == 204 else "nic firewall=0")

    db = _Db([_May("u-a", 204), _May("u-a", 208)])
    chan, ly_do = cach_ly.chan_khach_moi(db, _profile(), "u-b",
                                         do_hieu_luc=_tung_may)
    assert chan is True and "208" in ly_do


# ── 3. Không đo được thì CHẶN ────────────────────────────────────────────────

def test_hoi_Proxmox_that_bai_thi_CHAN_chu_khong_cho_qua():
    """"Chưa đo được" ⛔ không bao giờ là "ổn" ở một cửa an ninh."""
    def _no(vmid):
        raise RuntimeError("Proxmox khong tra loi")

    db = _Db([_May("u-a", 204)])
    chan, ly_do = cach_ly.chan_khach_moi(db, _profile(), "u-b", do_hieu_luc=_no)
    assert chan is True
    assert "khong do duoc" in ly_do, ly_do


def test_chu_hien_tai_KHONG_bi_chan_du_khong_do_duoc():
    """Chặn chủ hiện tại vì một lỗi đo là làm hại người ⛔ không liên quan."""
    def _no(vmid):
        raise RuntimeError("Proxmox khong tra loi")

    db = _Db([_May("u-a", 204)])
    chan, _ = cach_ly.chan_khach_moi(db, _profile(), "u-a", do_hieu_luc=_no)
    assert chan is False


# ── 4. Thông điệp phải nói được PHẢI LÀM GÌ ─────────────────────────────────

def test_ly_do_neu_du_thong_tin_de_sua():
    """Một câu "không bán được" không nói phải bật gì thì người vận hành bó tay."""
    db = _Db([_May("u-a", 204)])
    _, ly_do = cach_ly.chan_khach_moi(
        db, _profile(), "u-b",
        do_hieu_luc=_do(False, "cum chua bat (cluster/firewall/options.enable)"))
    assert "204" in ly_do and "cluster/firewall" in ly_do


def test_khong_bao_gio_nem_ra_ngoai():
    """Cửa này nằm trên đường bán. Một ngoại lệ lọt ra là một trang lỗi 500 cho
    khách, thay vì một câu giải thích — nên nó tự bắt và trả `(True, ly_do)`."""
    class _DbNo:
        def execute(self, _stmt):
            raise RuntimeError("CSDL hong")

    chan, ly_do = cach_ly.chan_khach_moi(_DbNo(), _profile(), "u-b",
                                         do_hieu_luc=_do(True))
    assert chan is True and "khong do duoc" in ly_do
