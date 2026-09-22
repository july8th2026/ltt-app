"""
video_crawler — theo chuyển hướng CÓ KIỂM cho link rút gọn (lane W4-L12).

Nguồn: `docs/migrations/video_crawler/THIET_KE_PHIEN_VA_KENH.md` §3.2 (P2) — link rút gọn
(`v.douyin.com`, `xhslink.com`, `v.kuaishou.com`, `b23.tv`, `vt.tiktok.com`/`vm.tiktok.com`,
`youtu.be`, `fb.watch`) phải được giải ra URL thật trước khi cào, KHÔNG mở đường SSRF.

`an_toan_url.theo_chuyen_huong` theo tối đa `toi_da_buoc` (mặc định 3) bước chuyển hướng HTTP; MỖI
bước (kể cả URL gốc) đi qua đúng `kiem()` hiện có (allowlist tên miền của nền đã chọn + chặn IP nội
bộ qua phân giải DNS, kể cả DNS rebinding ở các bước SAU). Test không đọc mạng: hàm mở URL (`mo`)
được tiêm, trả `(status, Location)` theo bảng cố định — port cùng kiểu tiêm `phan_giai` đã có ở
`test_1901_video_crawler_an_toan_url.py`.
"""
from __future__ import annotations

import pytest

from apps.video_crawler import an_toan_url, nen_tang
from apps.video_crawler.an_toan_url import UrlKhongAnToan

_DOUYIN = ("douyin.com", "iesdouyin.com")


def _dns_cong_khai(host):
    # IP CÔNG KHAI thật (như `test_1901_video_crawler_an_toan_url.py`) — KHÔNG dùng dải TEST-NET
    # (203.0.113.0/24…, RFC 5737): `ipaddress.IPv4Address.is_private` coi các dải "tài liệu" này là
    # private nên sẽ bị `kiem()` chặn nhầm, làm sai lệch ca đối chứng.
    return ["142.250.66.78"]


def _mo_theo_bang(bang):
    """Giả `mo`: bảng {url: (status, location)}; url không có trong bảng ⇒ (200, None) = điểm cuối."""
    def _mo(url, **kw):
        return bang.get(url, (200, None))
    return _mo


# ── ca hợp lệ (đối chứng) ────────────────────────────────────────────────────

def test_theo_chuyen_huong_mot_buoc_hop_le():
    bang = {"https://v.douyin.com/iABCdef/": (302, "https://www.douyin.com/video/7300000000000000000")}
    ket = an_toan_url.theo_chuyen_huong(
        "https://v.douyin.com/iABCdef/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))
    assert ket == "https://www.douyin.com/video/7300000000000000000"


def test_theo_chuyen_huong_khong_co_redirect_tra_nguyen():
    ket = an_toan_url.theo_chuyen_huong(
        "https://www.douyin.com/video/7300000000000000000", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai,
        mo=_mo_theo_bang({}))
    assert ket == "https://www.douyin.com/video/7300000000000000000"


def test_theo_chuyen_huong_nhieu_buoc_trong_han_muc():
    bang = {
        "https://v.douyin.com/a/": (302, "https://v.douyin.com/b/"),
        "https://v.douyin.com/b/": (301, "https://www.douyin.com/video/7300000000000000001"),
    }
    ket = an_toan_url.theo_chuyen_huong(
        "https://v.douyin.com/a/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))
    assert ket == "https://www.douyin.com/video/7300000000000000001"


def test_theo_chuyen_huong_dung_dung_toi_da_buoc_van_qua():
    """Đúng `toi_da_buoc` lần chuyển hướng (không hơn) vẫn phải ra kết quả — không lệch-off-by-one."""
    bang = {
        "https://v.douyin.com/a/": (302, "https://v.douyin.com/b/"),
        "https://v.douyin.com/b/": (302, "https://v.douyin.com/c/"),
        "https://v.douyin.com/c/": (302, "https://www.douyin.com/video/1"),
    }
    ket = an_toan_url.theo_chuyen_huong(
        "https://v.douyin.com/a/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang),
        toi_da_buoc=3)
    assert ket == "https://www.douyin.com/video/1"


# ── SSRF bắt buộc: IP nội bộ / tên miền lạ / vòng lặp / quá bước ────────────

@pytest.mark.parametrize("dich", [
    "http://127.0.0.1/latest",
    "http://10.0.0.5/x",
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]/x",
    "http://192.168.1.1/x",
])
def test_chuyen_huong_toi_ip_noi_bo_bi_chan(dich):
    bang = {"https://v.douyin.com/x/": (302, dich)}
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))


def test_chuyen_huong_toi_ten_mien_ngoai_allowlist_bi_chan():
    bang = {"https://v.douyin.com/x/": (302, "https://evil.example/steal")}
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))


def test_chuyen_huong_gia_dang_hau_to_ten_mien_bi_chan():
    """`notdouyin.com` không phải subdomain của `douyin.com` — như `_thuoc_ten_mien` đã kiểm ở `kiem()`."""
    bang = {"https://v.douyin.com/x/": (302, "https://notdouyin.com/video/1")}
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))


def test_chuyen_huong_dns_rebinding_bi_chan_o_buoc_sau():
    """Bước 1 domain hợp lệ theo allowlist, nhưng DNS của domain đó trả IP nội bộ (rebinding) — mỗi bước
    đều phải qua lại `kiem()`, không chỉ URL gốc."""
    bang = {"https://v.douyin.com/x/": (302, "https://www.douyin.com/video/1")}

    def _dns_rebinding(host):
        return ["127.0.0.1"] if host == "www.douyin.com" else ["142.250.66.78"]

    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_rebinding, mo=_mo_theo_bang(bang))


def test_vong_lap_chuyen_huong_bi_chan():
    bang = {
        "https://v.douyin.com/a/": (302, "https://v.douyin.com/b/"),
        "https://v.douyin.com/b/": (302, "https://v.douyin.com/a/"),
    }
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/a/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))


def test_qua_so_buoc_toi_da_bi_chan():
    bang = {
        "https://v.douyin.com/a/": (302, "https://v.douyin.com/b/"),
        "https://v.douyin.com/b/": (302, "https://v.douyin.com/c/"),
        "https://v.douyin.com/c/": (302, "https://v.douyin.com/d/"),
        "https://v.douyin.com/d/": (302, "https://www.douyin.com/video/1"),
    }
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/a/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang),
            toi_da_buoc=3)


def test_url_goc_khong_thuoc_allowlist_bi_chan_truoc_khi_mo_mang():
    goi = []

    def _mo_theo_doi(url, **kw):
        goi.append(url)
        return 200, None

    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://evil.example/x", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_doi)
    assert goi == [], "URL gốc không qua allowlist thì không được mở mạng"


def test_loi_mang_khi_mo_duoc_boc_thanh_khong_an_toan():
    def _mo_loi(url, **kw):
        raise OSError("timeout")
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_loi)


def test_thong_diep_loi_khong_lo_url_dich_hoac_ip():
    """Thông điệp lỗi ở biên ngoài (dùng làm nền cho lỗi hiển thị khách) không lộ URL/IP đích thật."""
    bang = {"https://v.douyin.com/x/": (302, "http://169.254.169.254/latest/meta-data")}
    with pytest.raises(UrlKhongAnToan) as exc:
        an_toan_url.theo_chuyen_huong(
            "https://v.douyin.com/x/", ten_mien=_DOUYIN, phan_giai=_dns_cong_khai, mo=_mo_theo_bang(bang))
    text = str(exc.value)
    assert "169.254.169.254" not in text
    assert "meta-data" not in text


# ── registry (nen_tang.py): allowlist của nền đã bao domain rút gọn (subdomain/literal) ─────────────

@pytest.mark.parametrize("url,nen", [
    ("https://v.douyin.com/iABCdef/", "douyin"),
    ("https://xhslink.com/a/abc123", "xiaohongshu"),
    ("https://v.kuaishou.com/abc", "kuaishou"),
    ("https://b23.tv/abcd123", "bilibili"),
    ("https://vt.tiktok.com/abc/", "tiktok"),
    ("https://vm.tiktok.com/abc/", "tiktok"),
    ("https://youtu.be/abc", "youtube"),
    ("https://fb.watch/abc/", "facebook"),
])
def test_registry_nhan_dien_link_rut_gon_ra_dung_nen(url, nen):
    assert nen_tang.nhan_dien(url) == nen


@pytest.mark.parametrize("nen_id,dom", [
    ("douyin", "v.douyin.com"), ("xiaohongshu", "xhslink.com"), ("kuaishou", "v.kuaishou.com"),
    ("bilibili", "b23.tv"), ("tiktok", "vt.tiktok.com"), ("tiktok", "vm.tiktok.com"),
    ("youtube", "youtu.be"), ("facebook", "fb.watch"),
])
def test_registry_ten_mien_du_cho_kiem_chap_nhan_domain_rut_gon(nen_id, dom):
    """`ten_mien` của nền phải đủ cho `kiem()`/`theo_chuyen_huong` chấp nhận domain rút gọn — dùng CHÍNH
    `_thuoc_ten_mien` mà `kiem()` gọi, không phải suy diễn riêng ở test."""
    n = nen_tang.lay(nen_id)
    assert an_toan_url._thuoc_ten_mien(dom, n.ten_mien)


def test_doan_tu_link_link_rut_gon_ra_che_do_link():
    for url in ("https://v.douyin.com/iABCdef/", "https://b23.tv/abcd123", "https://xhslink.com/a/abc",
                "https://v.kuaishou.com/abc", "https://vt.tiktok.com/abc/", "https://vm.tiktok.com/abc/",
                "https://youtu.be/abc", "https://fb.watch/abc/"):
        d = nen_tang.doan_tu_link(url)
        assert d is not None, url
        assert d.che_do == "link", url


def test_gioi_han_khong_con_cau_chua_nhan_link_rut_gon():
    """Câu 'Chưa/Không nhận link rút gọn ...' đã lỗi thời (nay giải được qua `theo_chuyen_huong`) —
    L12 bỏ khỏi `gioi_han` (spec cho phép: bỏ hoặc đổi cho khớp hành vi mới)."""
    for nen_id in ("douyin", "bilibili", "kuaishou"):
        n = nen_tang.lay(nen_id)
        for cau in n.gioi_han:
            assert "rút gọn" not in str(cau), (nen_id, str(cau))
