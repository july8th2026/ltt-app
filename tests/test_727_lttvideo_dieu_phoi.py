"""Điều phối viên pod — bật khi có việc, tắt khi rảnh (`B1`), và **không treo**.

⭐ Vì sao thành phần này được xây trong khi 12 lớp khác bị xoá ở lượt audit:
   **WanGP không biết gì về RunPod.** Đây là chỗ duy nhất trong hệ có kiến thức
   ấy, nên nó không trùng lặp với bất cứ thứ gì của thượng nguồn.

⛔ Mọi phép kiểm ở đây tiêm một `api` giả. Không lượt nào chạm cloud thật —
   một phép kiểm gọi cloud là một phép kiểm tính tiền.
"""
from __future__ import annotations

import pytest

from apps.lttvideo.dieu_phoi import DieuPhoi, TrangThaiMay


class ApiGia:
    """Giả lập REST của RunPod. Ghi lại lệnh để phép kiểm soi được thứ tự."""

    def __init__(self, *, het_card: bool = False) -> None:
        self.het_card = het_card
        self.lenh: list[str] = []
        self.trang_thai = "EXITED"

    def _rest(self, method: str, duong: str, than=None):
        self.lenh.append(f"{method} {duong}")
        if duong.endswith("/start"):
            if self.het_card:
                raise RuntimeError("not enough free GPU")
            self.trang_thai = "RUNNING"
        elif duong.endswith("/stop"):
            self.trang_thai = "EXITED"
        return {"desiredStatus": self.trang_thai}


class ClientGia:
    """`/health` trả `ok` sau `so_lan_hong` lượt đầu hỏng; `luon_hong` thì không bao giờ.

    ⭐ `luon_hong` có vì bản đầu của phép kiểm hết-giờ dùng `so_lan_hong=10_000`
       — mà `ngu` được tiêm là no-op, nên vòng lặp quay đủ nhanh để vượt 10.000
       lượt **trong chưa tới một giây** rồi trả `SAN_SANG`. Phép kiểm ấy tưởng
       đang đo ngưỡng thời gian, thật ra đang đo tốc độ vòng lặp.
    """

    def __init__(self, *, so_lan_hong: int = 0, luon_hong: bool = False) -> None:
        self.so_lan_hong = so_lan_hong
        self.luon_hong = luon_hong
        self.so_lan_goi = 0

    def health(self) -> dict:
        self.so_lan_goi += 1
        if self.luon_hong or self.so_lan_goi <= self.so_lan_hong:
            raise ConnectionError("chua len")
        return {"ok": True, "runtime_san_sang": True}


def _dp(api, client, **kw) -> DieuPhoi:
    return DieuPhoi(api=api, pod_id="p1", client=client, ngu=lambda _s: None, **kw)


def test_bat_va_cho_tra_SAN_SANG_khi_may_len():
    api, cl = ApiGia(), ClientGia(so_lan_hong=2)
    assert _dp(api, cl).bat_va_cho() is TrangThaiMay.SAN_SANG
    assert "POST /pods/p1/start" in api.lenh


def test_HET_CARD_la_mot_TRANG_THAI_chu_khong_phai_mot_NGOAI_LE():
    """`B3` cần hoàn credit — mà muốn hoàn thì phải **nhận được** câu trả lời.

    ⛔ Ném ngoại lệ ra ngoài thì người gọi phải bắt chuỗi `"not enough free GPU"`
       để phân biệt hết card với hỏng thật. Bắt lỗi bằng cách so chuỗi là một
       hợp đồng không ai cưỡng chế được.
    """
    api, cl = ApiGia(het_card=True), ClientGia()
    assert _dp(api, cl).bat_va_cho() is TrangThaiMay.KHONG_CO_CARD


def test_het_gio_thi_TRA_VE_chu_khong_treo():
    """Máy lên nhưng dịch vụ không bao giờ sẵn sàng ⇒ vẫn phải thoát."""
    api, cl = ApiGia(), ClientGia(luon_hong=True)
    assert _dp(api, cl, cho_toi_da_s=0.3, nhip_s=0.05).bat_va_cho() is TrangThaiMay.TAT
    assert cl.so_lan_goi >= 1, "chưa từng hỏi /health thì không phải hết giờ"


def test_KHONG_tat_khi_con_viec():
    """⛔ Tắt giữa lượt sinh là mất cả video lẫn tiền của khách."""
    api, cl = ApiGia(), ClientGia()
    assert _dp(api, cl).tat_neu_ranh(so_viec_dang_chay=1) is False
    assert not any(l.endswith("/stop") for l in api.lenh)


def test_TAT_khi_so_rong():
    api, cl = ApiGia(), ClientGia()
    assert _dp(api, cl).tat_neu_ranh(so_viec_dang_chay=0) is True
    assert "POST /pods/p1/stop" in api.lenh


def test_so_viec_am_bi_tu_choi():
    """Một số âm là dấu hiệu sổ đếm đã sai — đừng lấy nó làm căn cứ tắt máy."""
    api, cl = ApiGia(), ClientGia()
    with pytest.raises(ValueError):
        _dp(api, cl).tat_neu_ranh(so_viec_dang_chay=-1)


def test_may_dang_chay_thi_KHONG_goi_start_lai():
    api, cl = ApiGia(), ClientGia()
    api.trang_thai = "RUNNING"
    _dp(api, cl).bat_va_cho()
    assert not any(l.endswith("/start") for l in api.lenh), "gọi start trên máy đang chạy"


# ── tự tắt khi rảnh (`B1`) ────────────────────────────────────────────────────


def test_con_viec_thi_KHONG_nen_tat():
    assert _dp(ApiGia(), ClientGia()).nen_tat(
        so_viec_dang_chay=1, giay_ke_tu_viec_cuoi=99999) is False


def test_so_rong_nhung_VUA_XONG_thi_CHUA_tat():
    """⛔ Giữa hai job của cùng một người, sổ **có lúc rỗng** trong vài giây.

    Tắt ngay lúc ấy là bắt họ trả lại ~9 phút khởi động cho lượt kế, và gánh
    rủi ro không thuê lại được card.
    """
    dp = _dp(ApiGia(), ClientGia())
    assert dp.nen_tat(so_viec_dang_chay=0, giay_ke_tu_viec_cuoi=30) is False


def test_so_rong_va_da_ranh_LAU_thi_tat():
    dp = _dp(ApiGia(), ClientGia())
    assert dp.nen_tat(so_viec_dang_chay=0,
                      giay_ke_tu_viec_cuoi=dp.nghi_tat_sau_s + 1) is True


def test_chua_tung_co_viec_nao_thi_tat_ngay():
    """Máy bật mà chưa ai dùng ⇒ không có gì để chờ."""
    assert _dp(ApiGia(), ClientGia()).nen_tat(
        so_viec_dang_chay=0, giay_ke_tu_viec_cuoi=None) is True


def test_nen_tat_KHONG_goi_lenh_nao():
    """Quyết định tách khỏi hành động: hỏi được mà không tiêu một lệnh đắt."""
    api = ApiGia()
    _dp(api, ClientGia()).nen_tat(so_viec_dang_chay=0, giay_ke_tu_viec_cuoi=None)
    assert api.lenh == [], f"nen_tat da goi lenh: {api.lenh}"
