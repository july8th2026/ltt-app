"""
video_crawler — quyết định của điều phối khi gộp W1 (22/09).

1. Nhịp nghỉ 5–10 s (N7) nằm GIỮA các mục của một job tải, KHÔNG trước mỗi tệp: yt-dlp `sleep_interval` nghỉ trước
   MỌI tệp kể cả video đầu và cả luồng hình + luồng tiếng ⇒ tải một video 7,6 s → 24 s (smoke làn L3).
2. Thời lượng đi theo mục từ xem trước: thiếu nó thì mọi video tải theo danh sách đã chọn bị tính bậc rẻ nhất
   (báo cáo làn L2) — video 2 giờ thu 3 credit thay vì 15.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.video_crawler.adapters.base import TepTai

_DNS = lambda host: ["142.250.66.78"]  # noqa: E731


def test_tai_mot_tep_khong_con_sleep_interval_cua_yt_dlp():
    from apps.video_crawler.adapters.youtube import YoutubeAdapter
    o = YoutubeAdapter.tuy_chon_goc(Path("C:/tmp/x"))
    assert "sleep_interval" not in o and "max_sleep_interval" not in o
    assert o["sleep_interval_requests"] == 1.0          # nghỉ giữa request vẫn giữ (Y:2090-2095)


class _Ad:
    nen_tang = "youtube"

    def tai(self, item, thu_muc, *, bao_tien_do):
        p = Path(thu_muc) / f"{item.id}.mp4"
        p.write_bytes(b"x")
        return TepTai(p, 1, "x.mp4")


class _Kho:
    def __init__(self):
        self.co = {}

    def exists(self, k):
        return k in self.co

    def put(self, k, f, content_type=""):
        self.co[k] = f.read()

    def size(self, k):
        return len(self.co[k])

    def delete(self, k):
        self.co.pop(k, None)


def test_nghi_chi_giua_cac_muc_bo_qua_muc_dau(monkeypatch):
    from apps.video_crawler import jobs
    ngu = []
    monkeypatch.setattr(jobs, "_ngu", lambda s: ngu.append(s))
    monkeypatch.setattr(jobs, "_voi_db", lambda ham, *a, **k: True if ham == "gianh_cho" else None)  # L6: không DB
    kho = _Kho()
    monkeypatch.setattr("platform_core.storage.get_storage", lambda: kho)
    ids = ["a" * 11, "b" * 11, "c" * 11]
    params = {"owner_id": "u1", "nen_tang": "youtube",
              "muc": [{"id": i, "url": f"https://www.youtube.com/watch?v={i}", "tieu_de": i} for i in ids]}
    kq = jobs._tai_voi(_Ad(), params, None)
    assert len(kq["video_keys"]) == 3
    assert len(ngu) == 2 and all(5.0 <= s <= 10.0 for s in ngu)


def test_thoi_luong_tu_xem_truoc_di_theo_muc(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'w1.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.models import JOB_DONE, Job
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    try:
        from apps.video_crawler import features
        kp = Job(user_id="u1", app_slug="video_crawler", job_type="video_crawler.kham_pha",
                 params={"nen_tang": "youtube"}, status=JOB_DONE,
                 result={"muc": [{"nen_tang": "youtube", "id": "a" * 11, "tieu_de": "Dai",
                                  "url": f"https://www.youtube.com/watch?v={'a' * 11}", "thoi_luong_s": 7200}]})
        db.add(kp); db.commit()
        p = features.dung_params_tai_tu_xem_truoc(db, owner_id="u1", kham_pha_id=kp.id, ids=["a" * 11])
        assert p["muc"][0]["thoi_luong_s"] == 7200
    finally:
        db.close(); dbmod.reset_engine()


@pytest.mark.parametrize("sai", ["-5", "abc", None, 10 ** 9])
def test_thoi_luong_la_bi_bo_khong_vo(sai):
    """Thời lượng từ form/kết quả lạ ⇒ bỏ (None ⇒ bậc ≤ 10 phút), không làm hỏng yêu cầu."""
    from apps.video_crawler import features
    p = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                 muc=[{"id": "a" * 11, "thoi_luong_s": sai}], phan_giai=_DNS)
    assert p["muc"][0].get("thoi_luong_s") is None


def test_bang_gia_cho_giao_dien_khop_gia_bang():
    """Kiểm GUI W1: `gia.bang()` trả giây ({tu_s, den_s, gia}) còn template đọc phút ({tu_phut, den_phut, credit})
    ⇒ bảng hiện 'over min' không số. Unit test hai làn đều xanh vì không làn nào kiểm chỗ ghép."""
    from apps.video_crawler import gia, routes
    bang = routes._bang_gia()
    assert [(b["tu_phut"], b["den_phut"], b["credit"]) for b in bang] == [(0, 10, 3), (10, 30, 6), (30, 60, 10), (60, 180, 15)]
    assert [b["credit"] for b in bang] == [b["gia"] for b in gia.bang()]


@pytest.mark.parametrize("error, mong", [
    ("LoiNguoiGoi: Video không tồn tại hoặc đã bị gỡ.", "Video không tồn tại hoặc đã bị gỡ."),
    ("RuntimeError: mang: Lỗi mạng khi kết nối tới nền tảng. Vui lòng thử lại sau.",
     "Lỗi mạng khi kết nối tới nền tảng. Vui lòng thử lại sau."),
    ("KeyError: 'muc'", None),
    ("RuntimeError: C:\secret\path boom", None),
    (None, None),
])
def test_loi_job_cho_khach_khong_lo_ten_lop_hay_van_ban_tho(error, mong):
    """Kiểm GUI sau gộp L7: xem trước lỗi hiện "LoiNguoiGoi: Video không tồn tại…" — `job_runner` ghi
    `TenLop: thông điệp`. Khách chỉ thấy câu của bảng `loi.py`; lỗi hệ thống lạ ⇒ None (template hiện câu chung)."""
    from apps.video_crawler import loi
    assert loi.cho_khach(error) == mong
