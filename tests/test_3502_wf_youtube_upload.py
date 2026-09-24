"""`connector.youtube.upload` — giao thức resumable, và luật `irreversible`.

## Vì sao tệp này đo GIAO THỨC chứ không gọi YouTube

Một lượt upload thật cần một app OAuth Google **và** một tài khoản test — cả
hai là việc thủ công của chủ dự án (spec §9.3, skill `wizard`). Nên ở đây ta
đo thứ **đo được mà vẫn có giá trị**: các bước của giao thức resumable, và
đúng ba chỗ mà một node `side_effect = irreversible` có thể đăng **hai** video.

⚠️ Và khai thẳng phạm vi: những phép này **không** chứng minh video lên được.
   Chúng chứng minh rằng *nếu* Google trả các mã trong tài liệu thì mã của ta
   xử đúng. Điều kiện ra "upload thật ở chế độ private" **chưa đạt** — xem
   `docs/superpowers/reports/p6-connector/`.

## Nguồn (⛔ không tự suy)

*Google APIs — Resumable upload protocol*: `POST` khởi tạo trả `Location`;
`PUT` từng khối kèm `Content-Range`; `308` kèm `Range` nói đã nhận tới đâu;
`404`/`410` = phiên chết.
"""
from __future__ import annotations

import httpx
import pytest


def _client(xu_ly):
    return httpx.Client(transport=httpx.MockTransport(xu_ly))


PHIEN = "https://upload.example/session/abc"
META = dict(title="Phim thu", description="mo ta", tags=["a"],
            privacy="private", category_id="22", publish_at="")


# ── Mở phiên ───────────────────────────────────────────────────────────────

def test_mo_phien_tra_Location():
    from platform_core.workflow import youtube_upload as yt

    def xu_ly(req):
        assert req.url.params["uploadType"] == "resumable"
        assert req.headers["X-Upload-Content-Length"] == "123"
        assert req.headers["authorization"] == "Bearer TOK"
        return httpx.Response(200, headers={"Location": PHIEN})

    with _client(xu_ly) as c:
        assert yt.mo_phien(c, access_token="TOK", so_byte=123, **META) == PHIEN


def test_mo_phien_THIEU_Location_thi_NEM_khong_coi_la_thanh_cong():
    """⛔ Không có URL phiên thì mọi byte gửi sau đó đi vào hư không — và ta sẽ
    báo "đã upload" cho một video chưa bao giờ tồn tại."""
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(200)) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.mo_phien(c, access_token="TOK", so_byte=1, **META)
    assert e.value.ma == "provider_loi"


def test_401_ra_ma_credential_loi_khong_phai_provider_loi():
    """Hai hạng lỗi khác nhau: token chết là việc của KHÁCH (kết nối lại),
    provider hỏng là việc của ta. Gộp làm một là tự bịt đường chẩn đoán."""
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(401, text="bad token")) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.mo_phien(c, access_token="X", so_byte=1, **META)
    assert e.value.ma == "credential_loi" and e.value.status == 401


# ── Luật quyền riêng tư ────────────────────────────────────────────────────

def test_privacy_mac_dinh_la_private_trong_lugc_do_node():
    """⛔ Một tham số quên khai KHÔNG được biến thành một video CÔNG KHAI."""
    from platform_core.workflow.nut_loi.connector import YOUTUBE_UPLOAD
    p = YOUTUBE_UPLOAD.tham_so["properties"]["privacy"]
    assert p["default"] == "private"
    assert p["enum"] == ["private", "unlisted", "public"]
    assert "privacy" not in YOUTUBE_UPLOAD.tham_so["required"]


def test_privacy_la_gia_tri_hoang_thi_NEM():
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(200, headers={"Location": PHIEN})) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.mo_phien(c, access_token="T", so_byte=1,
                        **{**META, "privacy": "cong-khai"})
    assert e.value.ma == "dau_vao_sai"


def test_publish_at_voi_privacy_public_bi_TU_CHOI_khong_bi_bo_qua():
    """🔴 CỬA GIẢ. Luật của YouTube: `publishAt` chỉ có tác dụng khi
    `privacyStatus == "private"`. Gửi kèm `public` thì API **im lặng bỏ qua**
    và video lên **ngay** — tức một lịch đăng biến mất không báo ai."""
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(200, headers={"Location": PHIEN})) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.mo_phien(c, access_token="T", so_byte=1,
                        **{**META, "privacy": "public",
                           "publish_at": "2026-10-01T00:00:00Z"})
    assert e.value.ma == "dau_vao_sai" and "publish_at" in str(e.value)


# ── Đẩy byte ───────────────────────────────────────────────────────────────

def test_day_byte_mot_khoi_tra_video_id():
    from platform_core.workflow import youtube_upload as yt
    du_lieu = b"x" * 100

    def xu_ly(req):
        assert req.headers["Content-Range"] == "bytes 0-99/100"
        return httpx.Response(200, json={"id": "VID1",
                                         "status": {"privacyStatus": "private"}})

    with _client(xu_ly) as c:
        kq = yt.day_byte(c, PHIEN, du_lieu)
    assert kq.video_id == "VID1" and kq.status["privacyStatus"] == "private"


def test_day_byte_NHIEU_khoi_theo_308():
    from platform_core.workflow import youtube_upload as yt
    du_lieu = b"x" * 25
    thay = []

    def xu_ly(req):
        thay.append(req.headers["Content-Range"])
        if len(thay) == 1:
            return httpx.Response(308, headers={"Range": "bytes=0-9"})
        if len(thay) == 2:
            return httpx.Response(308, headers={"Range": "bytes=0-19"})
        return httpx.Response(201, json={"id": "VID2", "status": {}})

    with _client(xu_ly) as c:
        kq = yt.day_byte(c, PHIEN, du_lieu, khoi=10)
    assert kq.video_id == "VID2"
    assert thay == ["bytes 0-9/25", "bytes 10-19/25", "bytes 20-24/25"]


def test_phien_chet_404_ra_KET_QUA_MO_HO_khong_tu_mo_phien_moi():
    """🔴 Luật `irreversible`. 404 giữa chừng **không** chứng minh video chưa
    lên — nó chứng minh ta không biết. Mở phiên mới ở đây là đăng hai lần."""
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(404, text="gone")) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.day_byte(c, PHIEN, b"xxxx")
    assert e.value.ma == "ket_qua_mo_ho"


def test_5xx_cung_ra_KET_QUA_MO_HO():
    """500 sau khi đã gửi byte: request có thể đã tới nơi. Cùng lý do."""
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(503, text="busy")) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.day_byte(c, PHIEN, b"xxxx")
    assert e.value.ma == "ket_qua_mo_ho"


# ── Nối lại ────────────────────────────────────────────────────────────────

def test_co_phien_url_thi_NOI_LAI_khong_mo_phien_moi():
    """Nếu `upload` mở phiên mới khi đã có `phien_url`, phép này đỏ — và đó là
    đúng ca "đăng hai video"."""
    from platform_core.workflow import youtube_upload as yt
    duong = []

    def xu_ly(req):
        duong.append((req.method, str(req.url)))
        if req.method == "POST":
            return httpx.Response(200, headers={"Location": "PHIEN-MOI"})
        if req.headers.get("Content-Range") == "bytes */10":
            return httpx.Response(308, headers={"Range": "bytes=0-4"})
        return httpx.Response(200, json={"id": "VID3", "status": {}})

    with _client(xu_ly) as c:
        kq = yt.upload(c, access_token="T", du_lieu=b"y" * 10,
                       phien_url=PHIEN, **META)
    assert kq.video_id == "VID3" and kq.da_noi_lai
    assert not any(m == "POST" for m, _ in duong), (
        f"⛔ da mo phien MOI trong khi co phien cu: {duong}")


def test_phien_cu_da_chet_thi_KHONG_tu_mo_lai():
    from platform_core.workflow import youtube_upload as yt
    with _client(lambda r: httpx.Response(410)) as c:
        with pytest.raises(yt.LoiYouTube) as e:
            yt.upload(c, access_token="T", du_lieu=b"y" * 10,
                      phien_url=PHIEN, **META)
    assert e.value.ma == "ket_qua_mo_ho"


# ── Hậu kiểm của node ──────────────────────────────────────────────────────

def test_hau_kiem_video_id_RONG_ra_ABANDONED():
    """`job.status == SUCCEEDED` không đảm bảo có video. Ca đã đo trên máy B
    (HTTP 200, SUCCEEDED, nội dung RỖNG) — với `irreversible` thì im lặng báo
    "xong" còn tệ hơn: khách sẽ không đi tìm."""
    from platform_core.workflow.nut_loi.connector import YOUTUBE_UPLOAD
    tt, ma, _ = YOUTUBE_UPLOAD.hau_kiem({"video_id": ""}, {})
    assert (tt, ma) == ("ABANDONED", "ket_qua_mo_ho")
    assert YOUTUBE_UPLOAD.hau_kiem({"video_id": "V"}, {})[0] == "SUCCEEDED"


def test_node_khai_irreversible_va_KHONG_tu_thu_lai():
    from platform_core.workflow.nut_loi.connector import YOUTUBE_UPLOAD
    assert YOUTUBE_UPLOAD.side_effect == "irreversible"
    assert YOUTUBE_UPLOAD.retry_mac_dinh["max"] == 0
