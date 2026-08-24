"""H39/G2 — driver Vultr và driver cổng vào.

Hai driver này cầm hai thứ nguy hiểm nhất của app VPS: **tiền chảy hàng tháng**
(mỗi IP $3) và **đường vào của khách** (nftables trên cổng vào). Nên test ở đây
không kiểm "hàm chạy được không" mà kiểm đúng bốn thứ có thể làm hỏng thật:

1. Không đụng tới instance của người khác — tài khoản Vultr từng chạy 17 máy
   phục vụ mảng kinh doanh khác của chủ sản phẩm.
2. Không xoá IP không phải của app.
3. Mở/đóng đường phải **chạy lại được**, vì job có thể chạy lại bất cứ lúc nào.
4. Địa chỉ đi vào shell của cổng vào phải được kiểm trước.
"""
from __future__ import annotations

import json

import pytest

from apps.vps.services import gateway as gw
from apps.vps.services import vultr as vt


# ── giả lập tầng vận chuyển ──────────────────────────────────────────────────

class _PhanHoi:
    def __init__(self, status: int, body):
        self.status_code = status
        self._body = body
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("khong phai JSON")
        return self._body


class _Session:
    """Session giả: trả phản hồi theo (method, path) và ghi lại mọi lượt gọi."""

    def __init__(self, bang: dict):
        self.bang = bang
        self.da_goi: list[tuple[str, str, dict | None]] = []

    def request(self, method, url, **kw):
        duong_dan = url.replace(vt.API, "")
        than = json.loads(kw["data"]) if kw.get("data") else None
        self.da_goi.append((method, duong_dan, than))
        kq = self.bang.get((method, duong_dan))
        if kq is None:
            return _PhanHoi(404, {"error": f"khong khai {method} {duong_dan}"})
        return _PhanHoi(*kq) if isinstance(kq, tuple) else _PhanHoi(200, kq)


def _client(bang):
    s = _Session(bang)
    return vt.VultrClient(vt.VultrConfig(api_key="x", vung="sgp"), session=s), s


# ── 1. Vultr: vòng đời một IP ────────────────────────────────────────────────

def test_tao_ip_luon_gan_tien_to_nhan_cua_app():
    """Nhãn là thứ duy nhất phân biệt IP của app với IP của việc khác trên cùng
    tài khoản. Thiếu tiền tố thì `xoa_ip` sau này sẽ từ chối chính nó."""
    c, s = _client({("POST", "/reserved-ips"):
                    {"reserved_ip": {"id": "abc", "subnet": "45.77.45.29"}}})
    ip = c.tao_ip("may-123")
    assert ip == {"id": "abc", "dia_chi": "45.77.45.29",
                  "nhan": "ltt-vps-may-123"}
    assert s.da_goi[0][2]["label"].startswith(vt.TIEN_TO_NHAN)
    assert s.da_goi[0][2]["region"] == "sgp"


def test_tao_ip_thieu_id_hoac_dia_chi_thi_NEM_chu_khong_tra_ve_rong():
    """Trả về một IP rỗng nghĩa là app ghi bản ghi trống rồi mất dấu $3/tháng."""
    c, _ = _client({("POST", "/reserved-ips"): {"reserved_ip": {"id": "abc"}}})
    with pytest.raises(vt.VultrError) as e:
        c.tao_ip("may-123")
    assert "thieu id/subnet" in str(e.value)


def test_xoa_ip_TU_CHOI_khi_nhan_khong_phai_cua_app():
    """Hàng rào chính: một id truyền nhầm không được phép xoá IP của người khác."""
    c, s = _client({("GET", "/reserved-ips/xyz"):
                    {"reserved_ip": {"id": "xyz", "subnet": "1.2.3.4",
                                     "label": "may-chu-mail"}}})
    with pytest.raises(vt.VultrError) as e:
        c.xoa_ip("xyz")
    assert "tu choi xoa" in str(e.value)
    assert not any(m == "DELETE" for m, _, _ in s.da_goi), "khong duoc goi DELETE"


def test_xoa_ip_cho_phep_khi_dung_nhan_cua_app():
    c, s = _client({
        ("GET", "/reserved-ips/xyz"):
            {"reserved_ip": {"id": "xyz", "subnet": "1.2.3.4",
                             "label": "ltt-vps-may-1"}},
        ("DELETE", "/reserved-ips/xyz"): (204, ""),
    })
    c.xoa_ip("xyz")
    assert ("DELETE", "/reserved-ips/xyz", None) in s.da_goi


def test_driver_KHONG_co_phuong_thuc_nao_xoa_duoc_instance():
    """Tài khoản này từng chạy 17 instance của mảng kinh doanh khác. Một hàm
    `xoa_instance` nằm sẵn ở đây là một tai nạn chờ xảy ra."""
    ten = [t for t in dir(vt.VultrClient) if not t.startswith("_")]
    assert not [t for t in ten if "instance" in t and
                any(x in t for x in ("xoa", "delete", "huy", "dung"))], ten


# ── 2. Vultr: thông báo lỗi phải nói được điều đã mất công mới biết ──────────

def test_401_noi_ro_ba_kha_nang_chu_khong_chi_bao_sai_khoa():
    """Ngay sau khi tạo khoá, Vultr trả 401 vì ACL chưa lan truyền — không phải
    khoá sai. Đã mất một lần để biết; thông báo phải chở theo điều đó."""
    c, _ = _client({("GET", "/account"): (401, {"error": "Unauthorized IP"})})
    with pytest.raises(vt.VultrError) as e:
        c.tai_khoan()
    assert "lan truyen" in str(e.value)


def test_than_loi_khong_phai_JSON_van_bao_duoc_ma_trang_thai():
    """Khi Vultr trả HTML (lỗi tầng biên) thì vẫn phải nhìn thấy mã lỗi."""
    c, _ = _client({("GET", "/account"): (503, "<html>maintenance</html>")})
    with pytest.raises(vt.VultrError) as e:
        c.tai_khoan()
    assert e.value.status == 503


def test_thieu_khoa_thi_noi_ro_phai_dat_o_dau():
    with pytest.raises(vt.VultrError) as e:
        vt.doc_cau_hinh({})
    assert "secrets/app.env" in str(e.value)


# ── 3. Cổng vào: mở và đóng đường ────────────────────────────────────────────

def _gw():
    ghi: list[str] = []

    def chay(lenh):
        ghi.append(" ".join(lenh))
        return "song\n"

    c = gw.GatewayClient(
        gw.GatewayConfig(host="1.2.3.4", user="root", khoa="/tmp/k"), chay=chay)
    return c, ghi


def test_mo_duong_lam_du_BA_viec():
    """Thiếu việc nào cũng hỏng im lặng — xem docstring của `mo_duong`."""
    c, ghi = _gw()
    c.mo_duong("45.77.45.29", "10.51.0.50")
    lenh = ghi[0]
    assert "ip addr replace 45.77.45.29/32" in lenh, "thieu dia chi tren card"
    assert "vao { 45.77.45.29 : 10.51.0.50 }" in lenh, "thieu chieu vao"
    assert "ra  { 10.51.0.50 : 45.77.45.29 }" in lenh, "thieu chieu ra"


def test_mo_duong_xoa_truoc_khi_them_de_CHAY_LAI_DUOC():
    """Job có thể chạy lại bất cứ lúc nào; `nft add element` báo lỗi nếu khoá đã
    tồn tại với giá trị khác."""
    c, ghi = _gw()
    c.mo_duong("45.77.45.29", "10.51.0.50")
    assert ghi[0].index("delete element") < ghi[0].index("add element")


def test_mo_duong_ghi_lai_de_BEN_QUA_KHOI_DONG_LAI():
    """`nft add element` và `ip addr add` chỉ sống trong bộ nhớ. Không ghi lại
    thì cổng vào khởi động lại là TOÀN BỘ khách mất đường vào, im lặng."""
    c, ghi = _gw()
    c.mo_duong("45.77.45.29", "10.51.0.50")
    assert gw.TEP_TRANG_THAI in ghi[0]


def test_dong_duong_khong_keu_khi_da_go_roi():
    """Xoá máy có thể chạy lại; lần thứ hai không được làm job chết."""
    c, ghi = _gw()
    c.dong_duong("45.77.45.29", "10.51.0.50")
    assert ghi[0].count("|| true") >= 2


def test_dia_chi_khong_hop_le_bi_chan_TRUOC_khi_cham_shell():
    """Đây là chỗ dữ liệu đi vào một shell từ xa. Kiểm ở đây, không kiểm ở đó."""
    c, ghi = _gw()
    for xau in ("; rm -rf /", "10.51.0", "10.51.0.999", "", "$(id)"):
        with pytest.raises(gw.GatewayError):
            c.mo_duong(xau, "10.51.0.50")
        with pytest.raises(gw.GatewayError):
            c.mo_duong("45.77.45.29", xau)
    assert ghi == [], "khong duoc chay gi khi dia chi sai"


def test_danh_sach_duong_doc_duoc_map_tren_cong_vao():
    """Đối chiếu bản đồ thật với `vps_ip` là cách duy nhất phát hiện lệch — mà
    lệch ở đây nghĩa là khách gõ đúng địa chỉ và rơi vào máy người khác."""
    doc = {"nftables": [{"map": {"name": "vao", "elem": [
        ["45.77.45.29", "10.51.0.50"], ["45.77.45.31", "10.51.0.51"]]}}]}

    c = gw.GatewayClient(gw.GatewayConfig(host="h", khoa="/tmp/k"),
                         chay=lambda lenh: json.dumps(doc))
    assert c.danh_sach_duong() == {"45.77.45.29": "10.51.0.50",
                                   "45.77.45.31": "10.51.0.51"}


def test_thieu_khai_bao_cong_vao_thi_noi_ro_thieu_gi():
    for thieu, chu in (({"host": ""}, "HOST"), ({"khoa": ""}, "SSH_KEY")):
        tham = {"host": "1.2.3.4", "khoa": __file__}
        tham.update(thieu)
        with pytest.raises(gw.GatewayError) as e:
            gw.GatewayConfig(**tham).verify()
        assert chu in str(e.value)


# ── 4. Chống rò tiền: mua IP xong mà ghi sổ hỏng ─────────────────────────────

def test_xoa_ip_duoc_goi_khi_ghi_so_that_bai(monkeypatch):
    """Mua IP xong mà `INSERT` chết thì PHẢI trả IP về ngay.

    Đây là kịch bản đã xảy ra thật 24/08: Vultr cấp lại chính địa chỉ vừa trả
    (nó giữ 24 giờ rồi đưa lại cho cùng tài khoản), bản ghi cũ còn trong CSDL
    nên ràng buộc duy nhất `(gateway_id, dia_chi)` bắn — và IP đã mua thì nằm
    lại đó, **$3/tháng chảy mãi mà không ai biết nó của máy nào**.
    """
    from apps.vps import jobs

    da_xoa = []

    class _Khach:
        VultrError = vt.VultrError

        def tao_ip(self, nhan):
            return {"id": "ip-1", "dia_chi": "1.2.3.4", "nhan": "ltt-vps-x"}

        def xoa_ip(self, ip_id):
            da_xoa.append(ip_id)

        def gan_ip(self, *a):
            raise AssertionError("khong duoc gan khi ghi so da hong")

    class _KetQua:
        def scalars(self):
            return self

        def first(self):
            return None

    class _Db:
        """Lượt `execute` ĐẦU (tìm bản ghi của máy) phải chạy được — nếu không
        thì hàm chưa kịp mua IP và test chẳng chứng minh gì. Lượt SAU mới hỏng,
        đúng chỗ đã hỏng thật ngày 24/08."""

        def __init__(self):
            self.lan = 0

        def execute(self, *a, **k):
            self.lan += 1
            if self.lan == 1:
                return _KetQua()
            raise RuntimeError("CSDL hong giua chung")

        def rollback(self):
            pass

    class _Gw:
        cho_phep_ip_rieng = True
        id = "gw-1"
        ten = "cong"

    monkeypatch.setattr(vt, "client_tu_moi_truong", lambda *a, **k: _Khach())

    class _May:
        id = "0123456789abcdef"

    with pytest.raises(RuntimeError):
        jobs._cap_ip_cong_khai(_Db(), _May(), _Gw(), "10.51.0.60")
    assert da_xoa == ["ip-1"], "IP da mua phai duoc tra ve khi ghi so hong"
