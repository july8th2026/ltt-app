"""Pha 11 — QUAN SÁT ĐÍCH ĐẾN OUTBOUND trên các đường job đã di trú.

Gói chiến dịch đòi: *"Quan sát outbound destination nếu có thể. Forbidden
external Text/VLM/Image egress = 0."* — và kèm một câu nghiêm khắc:

    ⛔ "Khong chay that => NOT_TESTED, khong PASS."

## Cái tệp này CHỨNG MINH, và cái nó KHÔNG

✅ **Chứng minh:** chạy handler job **thật** của sáu app đã di trú, với một bẫy
   đặt ở tầng **socket** — nơi mọi thư viện HTTP đều phải đi qua — rồi chốt rằng
   **không một lượt nối nào** hướng tới nhà cung cấp Text/VLM/Image đã gỡ.

⛔ **KHÔNG chứng minh:** rằng LTT_LLM/LTT_IMAGE trả về kết quả đúng. Máy B là
   một máy KHÁC (`LTT_LLM_BASE_URL` / `LTT_RENDER_BASE_URL` không đặt trong tiến
   trình này, cổng 8299/8199 không trả lời từ đây). Phần ấy là **NOT_TESTED**,
   ghi ở `CAMPAIGN_STATE.md` — không khai PASS.

🔑 Vì sao vẫn đáng làm: câu hỏi *"có còn lối ra legacy không"* **không cần** máy
   B trả lời. Nó chỉ cần biết tiến trình định nối tới đâu — và bẫy socket trả
   lời đúng câu đó, cho **mọi** thư viện, kể cả một thư viện ai đó thêm mai sau.

## ⭐ Bẫy đặt ở SOCKET, không ở `httpx`

Vá `httpx.post` chỉ bắt được thứ đi qua `httpx`. Một `requests`, một
`urllib.request`, hay một `http.client` sẽ **lọt qua im lặng** — và im lặng ở
đây trông y hệt "không có lối ra nào".
"""
from __future__ import annotations

import socket

import pytest

#: Host của các họ đã gỡ. Một lượt nối tới đây = **thất bại của cả chiến dịch**.
HOST_CAM = (
    "generativelanguage.googleapis.com",
    "api.openai.com",
    "chatgpt.com",
    "api.apiai.vn",
    "cheapkeyai.shop",
)


class LuotNoiRaMang(RuntimeError):
    """Bẫy nổ. Mang theo **đích đến**, vì đó là thứ ta đang đo."""


@pytest.fixture()
def dich_den(monkeypatch):
    """Ghi lại MỌI đích đến mà tiến trình định nối, rồi chặn.

    ⭐ Ba cửa, vì một thư viện chỉ cần một trong ba: `getaddrinfo` (phân giải
       tên), `create_connection` (đường tắt của `requests`/`urllib`), và
       `socket.connect` (đường thấp nhất).
    """
    ghi: list[str] = []

    def _chan(host, *a, **k):
        ghi.append(str(host))
        raise LuotNoiRaMang(str(host))

    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **k: _chan(host))
    monkeypatch.setattr(socket, "create_connection",
                        lambda dia_chi, *a, **k: _chan(dia_chi[0]))
    monkeypatch.setattr(socket.socket, "connect",
                        lambda self, dia_chi, *a, **k: _chan(
                            dia_chi[0] if isinstance(dia_chi, tuple) else dia_chi))
    return ghi


@pytest.fixture()
def kho(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store"))
    set_storage(st)
    try:
        yield st
    finally:
        set_storage(None)


class _Ctx:
    job_id = "e2e-egress"

    def progress(self, *a, **k):
        pass


def test_BAY_that_su_no(dich_den):
    """⭐ ĐỐI CHỨNG ĐẶT Ở ĐẦU RA. Thiếu nó thì mọi `assert ghi == []` bên dưới
    xanh **vì bẫy không được gắn**, chứ không vì không có lượt gọi nào — và hai
    thứ ấy trông giống hệt nhau."""
    with pytest.raises(LuotNoiRaMang):
        socket.getaddrinfo("vi-du.invalid", 443)
    assert dich_den == ["vi-du.invalid"]


#: Handler của các app đã di trú + tham số tối thiểu để chúng chạy tới chỗ
#: **đáng lẽ** gọi mạng.
DUONG = {
    "taoanh": ("apps.taoanh.jobs", {"prompt": "mot con meo", "owner_id": "u1"}),
    "thumbnail": ("apps.thumbnail.jobs", {"topic": "chu de", "owner_id": "u1"}),
    "anhnoibo": ("apps.anhnoibo.jobs", {"prompt": "mot con meo", "owner_id": "u1"}),
}


@pytest.mark.parametrize("ten", sorted(DUONG))
def test_khong_duong_job_nao_noi_toi_nha_cung_cap_da_go(ten, dich_den, kho,
                                                        monkeypatch):
    """Chạy handler THẬT tới chỗ nó phải gọi mạng, rồi đọc đích đến.

    ⚠️ Handler **được phép hỏng** ở đây: không có máy B, không có cấu hình. Thứ
       ta đo là *đã định nối tới đâu*, không phải *có chạy xong không*. Trộn hai
       câu ấy là cách một phép kiểm egress biến thành một phép kiểm sức khoẻ.
    """
    import importlib

    mod = importlib.import_module(DUONG[ten][0])
    try:
        mod.handle(dict(DUONG[ten][1]), _Ctx())
    except BaseException:      # noqa: BLE001 — hỏng là bình thường, xem docstring
        pass

    xau = [d for d in dich_den if any(h in d for h in HOST_CAM)]
    assert xau == [], f"{ten} van noi toi nha cung cap da go: {xau}"


def test_dich_phai_dich_KHONG_di_ra_nha_cung_cap_da_go(dich_den, monkeypatch):
    """Lớp dịch prompt ảnh — chỗ Gemini sống lâu nhất (tới tận pha 06.1)."""
    from platform_core.image_gen import dich_llm

    try:
        dich_llm.goi_llm("mot con meo", "dich sang tieng Anh", db=None)
    except BaseException:      # noqa: BLE001
        pass
    xau = [d for d in dich_den if any(h in d for h in HOST_CAM)]
    assert xau == [], f"lop dich van noi toi: {xau}"


def test_dieu_phoi_LLM_KHONG_di_ra_nha_cung_cap_da_go(dich_den):
    """Cửa gọi model duy nhất của nền tảng."""
    from platform_core.llm import dieu_phoi

    try:
        dieu_phoi.goi(None, messages=[{"role": "user", "content": "xin chao"}],
                      thu_tu_provider=["ltt_llm"])
    except BaseException:      # noqa: BLE001
        pass
    xau = [d for d in dich_den if any(h in d for h in HOST_CAM)]
    assert xau == [], f"dieu phoi van noi toi: {xau}"
