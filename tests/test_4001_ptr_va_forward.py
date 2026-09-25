"""PTR cho IP khách: A record trước, PTR sau, và ⛔ không được làm hỏng việc giao máy.

🔴 Đo thật 25/09/2026 trên `51.79.202.1`:

    POST /ip/51.79.202.1%2F32/reverse
    400 {"message":"Cannot check if ip-51-79-202-1.vps.lttstudios.com. resolves to 51.79.202.1"}

⇒ OVH **bắt buộc forward-confirm**: phải có A record trỏ đúng về IP trước khi nó
  nhận PTR. Nên thứ tự là bắt buộc, không phải sở thích.

⚠️ Và ràng buộc quan trọng hơn: **PTR hỏng thì máy vẫn phải giao được.** Một
   địa chỉ không có rDNS là một điểm trừ nhỏ; một máy không giao được vì DNS là
   một sự cố. Nên mọi lỗi ở đây ghi cảnh báo, ⛔ không ném.
"""
import pytest


def test_ten_forward_suy_tu_IP_khong_lo_ten_khach():
    """Tên phải suy được từ IP — ⛔ không mang tên máy do khách đặt (khách đặt
    được tên tuỳ ý, và tên đó sẽ nằm công khai trong DNS mãi mãi)."""
    from apps.vps.services import rdns

    assert rdns.ten_forward("51.79.215.194") == "ip-51-79-215-194.vps.lttstudios.com"
    assert rdns.ten_forward("15.235.149.206") == "ip-15-235-149-206.vps.lttstudios.com"


@pytest.mark.parametrize("xau", ["", "khong-phai-ip", "51.79.215", "1.2.3.4.5",
                                 "51.79.215.999", "51.79.215.194 ; rm -rf"])
def test_IP_khong_hop_le_bi_TU_CHOI(xau):
    """Tên này đi vào một lời gọi API và vào DNS công khai. Không nhận rác."""
    from apps.vps.services import rdns

    with pytest.raises(ValueError):
        rdns.ten_forward(xau)


def test_dat_rdns_GOI_DUNG_THU_TU_forward_roi_moi_reverse():
    """OVH từ chối nếu A record chưa resolve — nên thứ tự là một bất biến."""
    from apps.vps.services import rdns

    thu_tu = []

    class _Dns:
        def dat_a_record(self, ten, ip):
            thu_tu.append(("A", ten, ip))

    class _Ovh:
        def dat_reverse(self, ip, ten):
            thu_tu.append(("PTR", ip, ten))

    assert rdns.dat_rdns(_Dns(), _Ovh(), "51.79.215.194") is True
    assert [b[0] for b in thu_tu] == ["A", "PTR"]


def test_A_record_hong_thi_KHONG_goi_OVH():
    """Gọi OVH khi biết chắc nó sẽ từ chối chỉ tạo một lỗi khó đọc hơn."""
    from apps.vps.services import rdns

    da_goi = []

    class _Dns:
        def dat_a_record(self, ten, ip):
            raise RuntimeError("Cloudflare 403")

    class _Ovh:
        def dat_reverse(self, ip, ten):
            da_goi.append(1)

    assert rdns.dat_rdns(_Dns(), _Ovh(), "51.79.215.194") is False
    assert da_goi == []


def test_PTR_hong_KHONG_NEM_ra_ngoai():
    """⛔ Bất biến của cả tệp này: một máy không có rDNS vẫn là một máy giao được."""
    from apps.vps.services import rdns

    class _Dns:
        def dat_a_record(self, ten, ip):
            return None

    class _Ovh:
        def dat_reverse(self, ip, ten):
            raise RuntimeError("OVH 400")

    assert rdns.dat_rdns(_Dns(), _Ovh(), "51.79.215.194") is False


# ── Ba trạng thái của PTR ─────────────────────────────────────────────────────

class _OvhCo:
    def get(self, duong):
        return {"reverse": "ip-51-79-215-194.vps.lttstudios.com."}


class _OvhKhong:
    def get(self, duong):
        raise RuntimeError("404")


def test_OVH_luu_va_DNS_da_tra_thi_DA_THAY():
    from apps.vps.services import rdns

    tt, _ = rdns.trang_thai_ptr(_OvhCo(), "51.79.215.194",
                                tra_cuu=lambda ip: "ip-51-79-215-194.vps.lttstudios.com")
    assert tt == rdns.DA_THAY


def test_OVH_luu_nhung_DNS_CHUA_tra_thi_DANG_LAN():
    """🔴 Ca thật 25/09: `dat_reverse` trả 200, OVH `GET` có bản ghi, nhưng
    `nslookup` vẫn không trả gì sau một giờ. Với thế giới bên ngoài, địa chỉ đó
    **chưa có rDNS** — nên đây ⛔ không được tính là "đạt"."""
    from apps.vps.services import rdns

    def khong_tra(ip):
        raise OSError("NXDOMAIN")

    tt, chi_tiet = rdns.trang_thai_ptr(_OvhCo(), "51.79.215.194", tra_cuu=khong_tra)
    assert tt == rdns.DANG_LAN
    assert "chua tra" in chi_tiet


def test_OVH_khong_co_ban_ghi_thi_CHUA_DAT():
    from apps.vps.services import rdns

    tt, _ = rdns.trang_thai_ptr(_OvhKhong(), "51.79.215.194", tra_cuu=lambda ip: "")
    assert tt == rdns.CHUA_DAT


def test_BA_trang_thai_khac_nhau_doi_mot():
    """⛔ Bánh cóc: đừng gộp ba trạng thái này thành `bool` trong một lần 'dọn'."""
    from apps.vps.services import rdns

    assert len({rdns.DA_THAY, rdns.DANG_LAN, rdns.CHUA_DAT}) == 3


def test_KHONG_dung_resolver_he_thong():
    """🔴 Đo 25/09: `socket.gethostbyaddr` trả đúng tên trong khi **cả ba**
    resolver công khai (8.8.8.8 / 1.1.1.1 / 9.9.9.9) không trả gì — resolver hệ
    thống đã có kết quả từ cache/ISP và nó **không đại diện** cho người ngoài.

    Câu hỏi ở đây là *"thế giới có thấy không"*, nên phải hỏi thế giới.
    ⛔ Bánh cóc bằng AST: một lần "dọn code" đổi lại `gethostbyaddr` sẽ làm phép
       đo lạc quan trở lại, và nó sẽ **im lặng** vì kết quả trông vẫn hợp lý.
    """
    import ast
    import pathlib

    nguon = pathlib.Path("apps/vps/services/rdns.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    ten_goi = {n.func.attr for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "gethostbyaddr" not in ten_goi
    assert "RESOLVER_CONG_KHAI" in nguon
