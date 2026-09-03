r"""
🔴 Cổng giọng vừa có cửa GHI đầu tiên, và cửa ghi khác hẳn cửa đọc về rủi ro.

Trước `/v1/lo-ra-tep`, mọi cửa nhận đường dẫn của `voice_sidecar/server.py` đều
chỉ ĐỌC (`/v1/enroll` nhận `duong_wav` rồi mở nó). Đường tài liệu dài đổi điều
đó: sidecar phải ghi từng đoạn ra đĩa để worker không phải cầm hàng trăm MB
base64.

⛔ Một cửa nhận đường dẫn TUỲ Ý để ghi là một cửa ghi đè được `app.env`, ghi đè
   được chính `server.py`, ghi đè được một tệp hệ thống. Loopback và bearer
   token vẫn là hàng rào đầu — nhưng *"chỉ máy này gọi được"* không đồng nghĩa
   với *"mọi thứ chạy trên máy này đều đáng tin"*, và chính đầu tệp `server.py`
   đã ghi rằng cổng này **không có xác thực nào ngoài một token dùng chung**.

⇒ Đường ghi bị kẹp vào một gốc, fail-closed. Tệp này chốt cái kẹp đó.

⚠️ Chốt `_kiem_duong_ghi` chứ không chốt cửa HTTP: cửa cần engine và GPU, còn
   phép kẹp thì thuần đường dẫn. Kiểm phần kiểm được, ở chỗ nó không cần model.
"""
from __future__ import annotations

import os
import tempfile

import pytest


def _kiem():
    from voice_sidecar.server import _kiem_duong_ghi
    return _kiem_duong_ghi


def test_cho_phep_ghi_trong_thu_muc_tam():
    d = os.path.join(tempfile.gettempdir(), "ltt_voice_thu", "doan0.wav")
    assert _kiem()(d) == os.path.realpath(d)


def test_tu_choi_duong_ngoai_goc():
    from fastapi import HTTPException

    for xau in (r"C:\LTTPlatform\secrets\app.env",
                r"C:\Windows\System32\drivers\etc\hosts",
                "/etc/passwd"):
        with pytest.raises(HTTPException) as e:
            _kiem()(xau)
        assert e.value.status_code == 400


def test_tu_choi_duong_di_nguoc_bang_dau_cham_cham():
    """⛔ `..` phải bị chặn SAU khi chuẩn hoá, không phải bằng cách tìm chuỗi "..".

    Tìm chuỗi thì `a..b.wav` bị chặn oan còn `tmp/x/../../../secrets` thì tuỳ
    cách viết mà lọt. `realpath` rồi so gốc là phép duy nhất không phụ thuộc
    cách viết.
    """
    from fastapi import HTTPException

    xau = os.path.join(tempfile.gettempdir(), "..", "..", "hiem.wav")
    if os.path.realpath(xau).startswith(os.path.realpath(tempfile.gettempdir())):
        pytest.skip("thu muc tam nam sat goc o dia, ca thu khong co nghia")
    with pytest.raises(HTTPException):
        _kiem()(xau)


def test_tu_choi_duong_rong():
    from fastapi import HTTPException

    for xau in ("", "   ", None):
        with pytest.raises(HTTPException):
            _kiem()(xau)


def test_khong_dung_startswith_de_so_goc():
    """🔴 `C:\tmp-khac` bắt đầu bằng `C:\tmp` nhưng KHÔNG nằm trong nó.

    Một phép so chuỗi ở đây là một lỗ đi ra ngoài gốc mà vẫn qua được mọi phép
    kiểm ngây thơ. Đây là ca chứng minh `commonpath` là bắt buộc.
    """
    from fastapi import HTTPException

    goc = os.path.realpath(tempfile.gettempdir())
    canh = goc + "-khac"
    if os.path.realpath(canh) == goc:
        pytest.skip("he tep khong phan biet duoc ca thu nay")
    with pytest.raises(HTTPException):
        _kiem()(os.path.join(canh, "x.wav"))


def test_goc_them_duoc_bang_bien_moi_truong(monkeypatch):
    """Gốc phụ khai bằng `LTT_VOICE_THU_MUC_TAM` — vì kho của nền tảng không
    nhất thiết nằm trong thư mục tạm của hệ thống."""
    import voice_sidecar.server as sv

    with tempfile.TemporaryDirectory() as tam:
        monkeypatch.setattr(sv, "_GOC_GHI", tam)
        d = os.path.join(tam, "kho", "doan1.wav")
        assert sv._kiem_duong_ghi(d) == os.path.realpath(d)
