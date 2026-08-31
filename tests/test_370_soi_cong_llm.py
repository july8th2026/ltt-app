"""Chốt phán xử của `tools/soi_cong_llm.py` — công cụ bắt HEALTH XANH GIẢ.

## Vì sao tệp này tồn tại

Đo thật trên máy B ngày 01/09, sau khi dừng vỏ bọc `nssm.exe`:

    + 0.0s   /health=200  Get-Service=Stopped   cong8299=26528
    +99.0s   /health=200  Get-Service=Paused    cong8299=26528

Tiến trình con **sống sót mồ côi**, vẫn giữ cổng, vẫn trả 200 — suốt 99 giây,
trong khi dịch vụ đã chết và `FAILURE_ACTIONS` của SCM không giành lại được cổng.

🔴 `/health` **do chính con mồ côi phục vụ**, nên nó không bao giờ nói được
   *"tôi là tiến trình không nên tồn tại"*. Lớp lỗi này chỉ lộ ra khi đối chiếu
   HAI nguồn độc lập: tiến trình tự nói, và Windows nói.

## Vì sao chốt bằng dữ liệu tổng hợp chứ không gọi máy B

Một phép kiểm phải trả lời *"cái tôi vừa sửa có hỏng không"*, và phải chạy được
offline. Gọi máy B làm nó đỏ khi máy B tắt — một lý do ngoài kho.

⭐ Nhưng điểm chính là điều khác: cái cần chốt là **công cụ có đọc ra được LỆCH
   hay không**. Tối 31/08 một đồng hồ đọc sai tên trường đã cho ra một dãy số
   trông hoàn hảo trong khi nó không đo gì cả — và nếu nó sai về phía TRẤN AN
   thì không ai đi tìm. Dữ liệu tổng hợp chứng minh được cả hai chiều mà không
   cần dựng lại sự cố.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_p = Path(__file__).resolve().parents[1] / "tools" / "soi_cong_llm.py"
_spec = importlib.util.spec_from_file_location("soi_cong_llm", _p)
soi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(soi)


class TestPhanXu:
    def test_hai_nguon_khop_va_khoe_thi_lanh(self):
        assert soi.phan_xu("200", "Running") == (soi.LANH, "lanh")

    @pytest.mark.parametrize("gateway", ["Stopped", "Paused", "StartPending",
                                         "StopPending", ""])
    def test_health_xanh_ma_dich_vu_khong_chay_la_XANH_GIA(self, gateway):
        """Hàng đắt nhất của bảng — chính là thứ đo được 99 giây trên máy B.

        `Paused` có trong danh sách vì đó là trạng thái THẬT quan sát được, chứ
        không phải một trạng thái ta suy ra: SCM thử dựng dậy, bản mới không
        bind được cổng (mồ côi giữ), và dịch vụ đứng ở `Paused`.
        """
        ma, nhan = soi.phan_xu("200", gateway)
        assert ma == soi.LECH
        assert nhan == "xanh-gia"

    def test_ca_hai_deu_hong_thi_KHONG_phai_xanh_gia(self):
        """Hỏng mà hai nguồn khớp nhau là hỏng TỰ BÁO — vẫn đỏ, nhưng khác loại.

        Gộp hai thứ này làm một sẽ làm mất đúng thông tin khiến công cụ đáng
        tồn tại: cái đáng sợ không phải "hỏng", mà là "hỏng trong khi trông khoẻ".
        """
        ma, nhan = soi.phan_xu("0", "Stopped")
        assert ma == soi.LECH
        assert nhan == "chet-that"

    def test_dich_vu_chay_ma_health_chua_len(self):
        ma, nhan = soi.phan_xu("0", "Running")
        assert ma == soi.LECH
        assert nhan == "dang-khoi-dong-hoac-treo"

    def test_bon_to_hop_cho_ra_bon_nhan_khac_nhau(self):
        """Không nhãn nào được trùng — mỗi ô của bảng cần một hành động riêng."""
        nhan = {soi.phan_xu(h, g)[1]
                for h in ("200", "0") for g in ("Running", "Stopped")}
        assert len(nhan) == 4

    def test_chi_MOT_to_hop_duy_nhat_duoc_coi_la_lanh(self):
        """Bánh cóc: nới điều kiện 'lành' ra là làm câm chính phép kiểm này.

        Quét rộng hơn bốn tổ hợp trên, gồm cả các trạng thái Windows thật khác.
        """
        lanh = [(h, g)
                for h in ("200", "0", "500", "503", "")
                for g in ("Running", "Stopped", "Paused", "StartPending", "")
                if soi.phan_xu(h, g)[0] == soi.LANH]
        assert lanh == [("200", "Running")]


class TestMaThoat:
    def test_ba_ma_thoat_khac_nhau(self):
        """`LANH`/`LECH`/`KHONG_DO_DUOC` phải phân biệt được.

        ⛔ `KHONG_DO_DUOC` KHÔNG được bằng `LANH`. Một công cụ giám sát không
           hỏi được mà trả về mã của 'lành' là một công cụ nói dối — cùng lớp
           lỗi với `_ban_va()` gộp "chưa có bản vá" vào "không hỏi được".
        """
        assert len({soi.LANH, soi.LECH, soi.KHONG_DO_DUOC}) == 3
        assert soi.KHONG_DO_DUOC != soi.LANH
