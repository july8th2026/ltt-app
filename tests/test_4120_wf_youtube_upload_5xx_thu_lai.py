"""B1a (plan `2026-09-25-wf-v2-VAN-HANH.md` §5): `5xx` khi đẩy byte YouTube
phải THỬ LẠI ĐƯỢC và NỐI LẠI đúng phiên cũ — ⛔ không mở phiên mới.

## Vì sao tệp riêng, ⛔ không thêm thẳng vào `test_3502`

`test_3502` đo TỪNG bước của giao thức resumable một cách cô lập (`mo_phien`
riêng, `day_byte` riêng, `upload` nối lại riêng). Phép ở đây đo CHUỖI: một lượt
`upload()` đầu tiên ăn 503 giữa chừng, rồi một lượt `upload()` THỨ HAI (mô
phỏng job retry, dùng `phien_url` mà lớp gọi đã lưu) phải NỐI LẠI — tức không
có POST thứ hai. Đây đúng là bằng chứng mà task B1a đòi: "sau 5xx, lần thử lại
nối lại phiên cũ, không mở phiên mới".

## Nguồn (⛔ không tự suy — xem thêm `youtube_upload.py::day_byte`)

Google Cloud Storage, *Perform resumable uploads*: 5xx ⇒ "resume ... from
where it left off"; YouTube/Google APIs *Resumable upload protocol*: hỏi lại
bằng `PUT` rỗng + `Content-Range: bytes */TOTAL`.
"""
from __future__ import annotations

import httpx
import pytest


def _client(xu_ly):
    return httpx.Client(transport=httpx.MockTransport(xu_ly))


PHIEN = "https://upload.example/session/b1a"
META = dict(title="Phim thu", description="mo ta", tags=["a"],
            privacy="private", category_id="22", publish_at="")


def test_5xx_giua_chung_ROI_thu_lai_NOI_LAI_khong_mo_phien_moi():
    """Chuỗi đầy đủ: `mo_phien` (POST) -> `day_byte` ăn 503 giữa chừng ->
    `LoiYouTube` giữ `phien_url` cho lớp gọi lưu lại (`ma == provider_loi`,
    THỬ LẠI ĐƯỢC) -> lượt thử lại truyền đúng `phien_url` đó vào `upload()`
    thì hỏi vị trí (`Content-Range: bytes */TOTAL`) rồi đẩy tiếp — ⛔ KHÔNG có
    POST thứ hai (tức không mở phiên mới, không đăng hai video)."""
    from platform_core.workflow import youtube_upload as yt

    duong: list[tuple[str, str]] = []
    lan_put_day_byte = {"n": 0}

    def xu_ly(req):
        duong.append((req.method, str(req.url)))
        if req.method == "POST":
            return httpx.Response(200, headers={"Location": PHIEN})
        cr = req.headers.get("Content-Range", "")
        if cr.startswith("bytes */"):
            # Hỏi lại vị trí (giao thức resumable) — server đã nhận 5 byte.
            return httpx.Response(308, headers={"Range": "bytes=0-4"})
        lan_put_day_byte["n"] += 1
        if lan_put_day_byte["n"] == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"id": "VID-RETRY", "status": {}})

    with _client(xu_ly) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.upload(c, access_token="T", du_lieu=b"y" * 10, **META)
        assert e.value.ma == "provider_loi", (
            "5xx phai THU LAI DUOC, khong phai ket_qua_mo_ho")
        phien_luu = e.value.phien_url
        assert phien_luu == PHIEN, (
            "loi phai giu phien_url de lop goi (jobs.py::_chay_youtube) luu "
            "vao connector_store TRUOC khi thu lai")

        # Mô phỏng lượt thử lại của job: lớp gọi đọc lại `phien_url` đã lưu.
        kq = yt.upload(c, access_token="T", du_lieu=b"y" * 10,
                       phien_url=phien_luu, **META)

    assert kq.video_id == "VID-RETRY" and kq.da_noi_lai
    so_post = sum(1 for m, _ in duong if m == "POST")
    assert so_post == 1, f"⛔ da mo phien MOI sau 5xx: {duong}"


def test_5xx_KHONG_con_la_ket_qua_mo_ho_tren_MA_LOI_cong_bo():
    """Bánh cóc chốt tập hợp: `ket_qua_mo_ho` vẫn tồn tại (404/410 vẫn dùng),
    nhưng `day_byte` không còn phát nó cho một 503 — đã đổi thành
    `provider_loi` ở cả hai điểm phát 5xx trong `day_byte`."""
    from platform_core.workflow import youtube_upload as yt
    assert "provider_loi" in yt.MA_LOI and "ket_qua_mo_ho" in yt.MA_LOI
    with _client(lambda r: httpx.Response(500, text="internal")) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.day_byte(c, PHIEN, b"xxxx")
    assert e.value.ma == "provider_loi"
