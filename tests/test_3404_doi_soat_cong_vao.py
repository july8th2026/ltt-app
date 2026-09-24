"""Luật chặn cổng quản trị phải NÊU ĐÚNG địa chỉ của gateway hiện tại.

🔴 24/09/2026: `tcp dport 22 accept` không nêu phạm vi ⇒ cổng quản trị của cổng
   vào trả lời trên **cả 11 địa chỉ IPv4**, gồm địa chỉ vừa bán cho khách.
   Bản vá là `ip daddr != <IP quản trị> tcp dport 22 drop`.

⚠️ Bản vá ấy mang một **con số** trong một tệp trên một máy khác. Ngày OVH đổi
   IP chính của cổng vào, con số đó vẫn nằm đó, luật vẫn "có", và cửa **mở lại
   trong im lặng** — đúng khuôn của chính lỗi vừa sửa. Nên phải có một phép đo
   so con số trong luật với con số trong sổ sách.
"""
import pytest

from tools.vps_doi_soat_cong import luat_khop

CHAIN = """table inet gw {
	chain input {
		type filter hook input priority filter; policy drop;
		ct state established,related accept
		ip daddr != 51.79.166.36 tcp dport 22 drop comment "SSH-chi-mo-tren-IP-quan-tri"
		tcp dport 22 accept comment "SSH quan tri"
	}
}"""


def test_luat_dung_dia_chi_hien_tai_thi_DAT():
    dat, _ = luat_khop(CHAIN, "51.79.166.36")
    assert dat


def test_gateway_doi_IP_thi_luat_cu_KHONG_con_dat():
    """Đây là ca thật sẽ xảy ra, và là ca nguy hiểm: luật vẫn có, vẫn chạy,
    nhưng nó chặn theo một địa chỉ không còn là địa chỉ quản trị nữa."""
    dat, vi_sao = luat_khop(CHAIN, "51.79.200.99")
    assert not dat and "KHAC" in vi_sao


def test_khong_co_luat_thi_KHONG_dat():
    khong = "\n".join(d for d in CHAIN.splitlines() if "drop comment" not in d)
    dat, vi_sao = luat_khop(khong, "51.79.166.36")
    assert not dat and "KHONG co luat" in vi_sao


@pytest.mark.parametrize("bien_the", [
    'ip daddr != 51.79.166.36 tcp dport 22 drop',
    '\t\tip daddr != 51.79.166.36 tcp dport 22 drop comment "x"',
])
def test_doc_duoc_du_khoang_trang_va_chu_thich_khac_nhau(bien_the):
    dat, _ = luat_khop(bien_the, "51.79.166.36")
    assert dat
