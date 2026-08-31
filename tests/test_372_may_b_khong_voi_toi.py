"""F06 — máy B KHÔNG VỚI TỚI ĐƯỢC. Khách thấy gì, và có bị thu tiền không?

## Vì sao tách khỏi ca "bận"

`test_272` đã chốt ca **bận** (`ban=True`): 503 + `Retry-After` + hoàn đủ. Ca này
khác **cả về đường mã lẫn về ý nghĩa vận hành**:

| | bận | không với tới được |
|---|---|---|
| Nguồn | máy B **trả lời** 429 | máy B **không trả lời** |
| `ban` | `True` | `False` |
| Ý nghĩa | thử lại lát nữa là được | có thứ đang hỏng |
| Người trực | không cần làm gì | **phải làm gì đó** |

⛔ Gộp hai cái thành một mã lỗi là làm mất đúng thông tin để phân biệt *"chờ
một chút"* với *"máy B đang sập"*. Và trong sự cố 31/08 thì phân biệt đó là thứ
đáng giá 6 giờ.

## Ba câu hỏi, theo thứ tự tiền

1. Khách có bị **thu tiền** cho một lượt không hề chạy không?
2. Khách có nhận được **lỗi sạch** (không phải 500 / không phải treo) không?
3. **Suất đồng thời** có được nhả không? — nếu không thì một lần máy B chết sẽ
   khoá luôn cả hàng đợi, và đó chính là hình dạng của sự cố 31/08.
"""
from __future__ import annotations

import importlib

import pytest

_t272 = importlib.import_module("tests.test_272_cua_streaming")

MSG = _t272.MSG
api = _t272.api                      # noqa: F811 — dùng lại fixture đã có
_account = _t272._account
_so_du = _t272._so_du
_than = _t272._than
_h = _t272._h
_dem_execution_lease = _t272._dem_execution_lease


def _may_b_chet(monkeypatch, thong_diep="khong noi duoc toi may B (ConnectError)"):
    """Máy B không trả lời — `ban=False`, đúng như `luong_vlm.py:152` ném ra."""
    from platform_core.llm import luong_vlm
    da_goi = []

    def gia(db, *, duong, than, timeout_s=900.0):
        da_goi.append(duong)
        raise luong_vlm.KhongMoDuocLuong(thong_diep, ban=False)

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return da_goi


class TestKhachKhongTraTienChoMotLuotKhongChay:
    def test_may_b_chet_thi_HOAN_DU(self, api, monkeypatch):
        """🔴 Câu hỏi đắt nhất. Thu tiền cho một lượt không chạy là mất khách."""
        _may_b_chet(monkeypatch)
        user_id, token = _account()
        truoc = _so_du(user_id)
        api.post(MSG, json=_than(), headers=_h(token)).read()
        assert _so_du(user_id) == truoc, "may B chet ma van thu tien khach"

    def test_da_thuc_su_GOI_roi_moi_hong(self, api, monkeypatch):
        """Chốt rằng phép kiểm trên đo đúng thứ nó tưởng.

        Nếu đường mã chặn *trước* khi gọi máy B thì số dư cũng không đổi — và
        phép kiểm trên sẽ xanh mà **không chứng minh gì cả**. Đây là đối chứng.
        """
        goi = _may_b_chet(monkeypatch)
        _u, token = _account()
        api.post(MSG, json=_than(), headers=_h(token)).read()
        assert goi, "chua he goi may B => phep kiem hoan tien o tren la VO NGHIA"


class TestKhachNhanLoiSach:
    def test_khong_phai_500(self, api, monkeypatch):
        """500 nói 'lỗi của chúng tôi và tôi không biết gì hơn'. Ta biết hơn thế."""
        _may_b_chet(monkeypatch)
        _u, token = _account()
        r = api.post(MSG, json=_than(), headers=_h(token))
        assert r.status_code != 500, r.text
        assert 400 <= r.status_code < 600

    def test_ma_loi_PHAN_BIET_duoc_voi_ca_ban(self, api, monkeypatch):
        """Cùng mã + cùng `Retry-After` thì người trực không biết có phải làm gì.

        Ca bận: chờ là xong. Ca này: có thứ đang hỏng. Hai hành động khác nhau
        ⇒ phải phân biệt được từ phía khách hoặc từ log.
        """
        from platform_core.llm import luong_vlm

        _may_b_chet(monkeypatch)
        _u, token = _account()
        r_chet = api.post(MSG, json=_than(), headers=_h(token))

        # Ca bận, cùng bộ máy, để so.
        def ban(db, *, duong, than, timeout_s=900.0):
            raise luong_vlm.KhongMoDuocLuong("may B dang ban", ban=True,
                                             thu_lai_sau_s=30)
        monkeypatch.setattr(luong_vlm, "mo", ban)
        r_ban = api.post(MSG, json=_than(), headers=_h(token))

        assert r_ban.status_code == 503
        khac = (r_chet.status_code != r_ban.status_code
                or r_chet.headers.get("Retry-After")
                != r_ban.headers.get("Retry-After"))
        assert khac, (
            "ca CHET va ca BAN khong phan biet duoc tu phia khach "
            f"(ca hai deu {r_chet.status_code}, "
            f"Retry-After={r_chet.headers.get('Retry-After')})")


class TestSuatDongThoiPhaiDuocNha:
    def test_may_b_chet_KHONG_de_lai_lease_treo(self, api, monkeypatch):
        """🔴 Hình dạng của sự cố 31/08.

        `max_dong_thoi = 1` ⇒ một suất treo là **100 %** ngừng dịch vụ. Nếu máy
        B chết mà suất không được nhả thì lần chết đó khoá luôn hàng đợi, và
        triệu chứng ở phía khách là 429 vĩnh viễn chứ không phải lỗi của máy B —
        tức đi tìm sai chỗ ngay từ đầu.
        """
        _may_b_chet(monkeypatch)
        _u, token = _account()
        api.post(MSG, json=_than(), headers=_h(token)).read()
        assert _dem_execution_lease() == 0, "may B chet de lai mot lease treo"

    def test_hong_LIEN_TIEP_van_khong_tich_luy_lease(self, api, monkeypatch):
        """Một lần rò không thấy; năm lần rò thì thấy — nếu nó tích luỹ."""
        _may_b_chet(monkeypatch)
        _u, token = _account(credits=100_000)
        for _ in range(5):
            api.post(MSG, json=_than(), headers=_h(token)).read()
        assert _dem_execution_lease() == 0, (
            "lease tich luy qua nhieu lan hong -- day la duong ro suat")
