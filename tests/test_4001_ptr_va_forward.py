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
    """OVH tra 404 = "khong co ban ghi reverse".

    ⚠️ Con gia nay tung nem `RuntimeError("404")` — mot loi tran KHONG mang ma.
    Doi 25/09: mot loi khong mang ma khong con duoc doc la "khong co ban ghi"
    (do la cach mot khoa chet bi doc thanh mot su that ve ha tang), nen con gia
    phai bao 404 dung cach client that bao.
    """

    def get(self, duong):
        from apps.vps.services.ovh import OvhError

        raise OvhError("OVH request failed (HTTPError)", status=404)


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

    # ⚠️ Con giả này từng `raise OSError("NXDOMAIN")`. Sửa 25/09: NÉM nay có
    #    nghĩa "chưa đo được DNS", còn "resolver đã trả lời và không có bản ghi"
    #    là chuỗi rỗng — đúng hai việc mà bản cũ gộp làm một.
    def khong_tra(ip):
        return ""

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


# ── Khoá OVH chết ⇒ ⛔ KHÔNG được khai là "chưa đặt" ──────────────────────────
#
# 🔴 Ca thật 25/09/2026 chiều: consumer key OVH bị thu hồi (`403 "This credential
#    is not valid"`). `trang_thai_ptr` hỏi OVH TRƯỚC, `except` nuốt 403 rồi trả
#    `CHUA_DAT` — trong khi `nslookup 51.79.215.194 1.1.1.1` trả đúng tên trên CẢ
#    HAI resolver công khai. PTR **đã đặt và forward-confirmed**; chỉ có đường đo
#    là chết. Một khoá hỏng làm công cụ khai sai MỌI IP, và nếu tin nó thì ta đi
#    đặt lại PTR đã có — bằng chính cái khoá đang chết.
#
#    Thuốc: hỏi DNS công khai TRƯỚC (nó là sự thật mà khách hàng của khách nhìn
#    thấy), OVH chỉ dùng để phân biệt `DANG_LAN` với `CHUA_DAT`; và "không đo
#    được" là một trạng thái THỨ TƯ, không phải một giá trị của ba cái kia.


class _OvhChet:
    """403 — khoá bị thu hồi. ⛔ Không nói gì về việc PTR có tồn tại hay không."""

    def get(self, duong):
        from apps.vps.services.ovh import OvhError

        raise OvhError("OVH request failed (HTTPError)", status=403)


class _OvhKhongCoBanGhi:
    """404 — OVH trả lời rõ ràng: địa chỉ này KHÔNG có bản ghi reverse."""

    def get(self, duong):
        from apps.vps.services.ovh import OvhError

        raise OvhError("OVH request failed (HTTPError)", status=404)


def test_DNS_cong_khai_da_tra_thi_DA_THAY_du_khong_hoi_duoc_OVH():
    """Thế giới thấy PTR ⇒ đạt. Đường đo tới OVH chết không đổi được sự thật đó."""
    from apps.vps.services import rdns

    tt, chi_tiet = rdns.trang_thai_ptr(
        _OvhChet(), "51.79.215.194",
        tra_cuu=lambda ip: "ip-51-79-215-194.vps.lttstudios.com")
    assert tt == rdns.DA_THAY, chi_tiet


def test_khoa_OVH_chet_va_DNS_im_thi_KHONG_DO_DUOC_chu_khong_phai_CHUA_DAT():
    from apps.vps.services import rdns

    tt, chi_tiet = rdns.trang_thai_ptr(_OvhChet(), "51.79.215.194",
                                       tra_cuu=lambda ip: "")
    assert tt == rdns.KHONG_DO_DUOC, chi_tiet
    assert tt != rdns.CHUA_DAT


def test_OVH_tra_404_thi_moi_la_CHUA_DAT():
    """404 là một câu trả lời; 403 là sự vắng mặt của câu trả lời."""
    from apps.vps.services import rdns

    tt, _ = rdns.trang_thai_ptr(_OvhKhongCoBanGhi(), "51.79.215.194",
                                tra_cuu=lambda ip: "")
    assert tt == rdns.CHUA_DAT


def test_BON_trang_thai_khac_nhau_doi_mot():
    from apps.vps.services import rdns

    assert len({rdns.DA_THAY, rdns.DANG_LAN, rdns.CHUA_DAT,
                rdns.KHONG_DO_DUOC}) == 4


def test_OvhError_mang_ma_HTTP_de_phan_biet_403_voi_404():
    """⛔ Thân phản hồi vẫn không được phơi ra; mã HTTP thì không phải bí mật."""
    from apps.vps.services.ovh import OvhError

    loi = OvhError("OVH request failed (HTTPError)", status=403, ma_loi="INVALID_CREDENTIAL")
    assert loi.status == 403 and loi.ma_loi == "INVALID_CREDENTIAL"
    assert OvhError("khong co ma").status is None


# ── Đọc đầu ra `nslookup`: ba kết cục, ⛔ không phải hai ──────────────────────
#
# 🔴 Ca thật 25/09/2026 (chiều, sau khoá OVH): `_tra_cuu_cong_khai` dùng regex
#    `[Nn]ame\s*=\s*(\S+)` — dạng của `nslookup -type=PTR`. Nhưng công cụ gọi
#    `nslookup <ip> <dns>`, và **Windows in `Name:    x`** (hai chấm). Regex không
#    khớp bao giờ ⇒ hàm luôn trả rỗng ⇒ nửa DNS của phép kiểm CHƯA TỪNG chạy.
#    Đầu ra thật, chụp trên chính máy này:
#
#        Server:  one.one.one.one          |  Server:  one.one.one.one
#        Address:  1.1.1.1                 |  Address:  1.1.1.1
#                                          |
#        Name:    ip-51-79-215-194...      |  (stdout hết ở đây)
#        Address:  51.79.215.194           |  stderr: *** ... can't find
#                                          |          192.0.2.1: Non-existent domain
#
#    Bài học: tôi đo **cách một công cụ in ra**, không đo tính chất. Và parse thất
#    bại lại im lặng thành "thế giới chưa thấy" — một dứt mạch đo lường mặc áo
#    một sự thật về hạ tầng.

RA_WINDOWS_CO = """Server:  one.one.one.one
Address:  1.1.1.1

Name:    ip-51-79-215-194.vps.lttstudios.com
Address:  51.79.215.194

"""

RA_UNIX_CO = """Server:\t\t1.1.1.1
Address:\t1.1.1.1#53

194.215.79.51.in-addr.arpa\tname = ip-51-79-215-194.vps.lttstudios.com.
"""

RA_KHONG_CO_STDOUT = """Server:  one.one.one.one
Address:  1.1.1.1

"""
RA_KHONG_CO_STDERR = ("*** one.one.one.one can't find 192.0.2.1: "
                      "Non-existent domain\n")


def test_doc_duoc_dang_Windows_hai_cham():
    from apps.vps.services import rdns

    assert (rdns._ten_trong_dau_ra(RA_WINDOWS_CO)
            == "ip-51-79-215-194.vps.lttstudios.com")


def test_doc_duoc_dang_Unix_dau_bang():
    from apps.vps.services import rdns

    assert (rdns._ten_trong_dau_ra(RA_UNIX_CO)
            == "ip-51-79-215-194.vps.lttstudios.com")


def test_KHONG_nham_dong_Server_thanh_ten_PTR():
    from apps.vps.services import rdns

    assert rdns._ten_trong_dau_ra(RA_KHONG_CO_STDOUT) == ""


def test_resolver_noi_ro_KHONG_CO_thi_la_mot_cau_tra_loi():
    from apps.vps.services import rdns

    assert rdns._noi_khong_co_ban_ghi(RA_KHONG_CO_STDERR) is True
    assert rdns._noi_khong_co_ban_ghi(RA_WINDOWS_CO) is False


def test_dau_ra_la_cua_dan_KHONG_doc_duoc_thi_NEM_chu_khong_tra_RONG():
    """⛔ Một đầu ra lạ (bản Windows đổi chữ, locale khác) ⇒ 'chưa đo được'.
    Trả rỗng là biến một dứt mạch đo lường thành một sự thật về rDNS."""
    from apps.vps.services import rdns

    def chay_gia(lenh, **kw):
        class _Ra:
            stdout = "Tên:    ip-51-79-215-194.vps.lttstudios.com\n"
            stderr = ""
        return _Ra()

    import pytest
    with pytest.raises(rdns.KhongDoDuocDns):
        rdns._tra_cuu_cong_khai("51.79.215.194", chay=chay_gia)


def test_DNS_chua_do_duoc_va_OVH_co_ban_ghi_thi_chi_tiet_KHONG_noi_da_tra():
    from apps.vps.services import rdns

    def khong_do_duoc(ip):
        raise rdns.KhongDoDuocDns("dau ra la")

    tt, chi_tiet = rdns.trang_thai_ptr(_OvhCo(), "51.79.215.194",
                                       tra_cuu=khong_do_duoc)
    assert tt == rdns.DANG_LAN
    assert "chua do duoc" in chi_tiet and "chua tra" not in chi_tiet
