"""test_337 — artifact của job trước làm ĐẦU VÀO của job sau. (V2, Phase 07)

🔴 VÌ SAO NÓ ĐÁNG MỘT TỆP RIÊNG. Trước 30/08 `invocation.py` ghi thẳng:

    "Media parameters take an upload/artifact id. Resolving one to a storage key
     is Prompt 07's job; until then a tool that needs media simply cannot be
     called, which is better than inventing a half-contract now."

Nửa artifact chưa bao giờ được viết. Hệ quả thật: **không nối chuỗi được.** Muốn
đưa video vừa sinh sang `video.upscale` thì khách phải **tải về rồi tải lên
lại** — một tệp hàng trăm MB đi ra rồi đi vào, qua Cloudflare, chỉ để nằm lại
đúng chỗ nó đang nằm.

⛔ VÀ NÓ NỚI LỎNG MỘT RÀNG BUỘC, nên ba phép kiểm dưới đây canh đúng chỗ nới:

  · upload bị khoá theo `app_slug`; artifact **cố ý không** — đó là mục đích;
  · nhưng **chủ sở hữu** và **danh sách trắng hợp đồng đầu ra** thì không nới,
    và chúng mới là thứ giữ an toàn.
"""
from __future__ import annotations

import pytest


def test_artifact_KHONG_bi_doi_cho_nhu_upload():
    """⛔ Bất biến quan trọng nhất: artifact chỉ được **tham chiếu**.

    `promote_media` **dời** một upload sang khoá bền vững của job mới. Làm thế
    với artifact là **lấy mất kết quả của job trước**: khách vẫn cầm id đó, vẫn
    tải được nó, và lần tải sau sẽ 404.
    """
    import inspect

    from platform_core.public_api import invocation

    ma = inspect.getsource(invocation.promote_media)
    assert "ThamChieuArtifact" in ma, (
        "promote_media khong phan biet artifact voi upload — no se DOI tep cua "
        "job truoc di, va lan tai sau se 404")
    # Va no phai `continue` TRUOC khi cham `upload_sessions.promote`.
    assert ma.index("ThamChieuArtifact") < ma.index("upload_sessions.promote")


def test_ba_cong_bao_mat_o_duong_giai_artifact():
    """Nới một ràng buộc thì hai cái còn lại phải chặt hơn, không lỏng hơn."""
    import inspect

    from server.api import uploads

    ma = inspect.getsource(uploads._giai_artifact)
    assert "principal.user_id" in ma, "thieu cong CHU SO HUU"
    assert "storage_key_for" in ma and "tool=" in ma, (
        "thieu cong DANH SACH TRANG cua hop dong dau ra")
    assert "tool_sinh is None" in ma, (
        "khong tim duoc ToolSpec ma van di tiep: `storage_key_for(tool=None)` "
        "BO QUA danh sach trang, nen moi thu handler de trong `result` se thanh "
        "dau vao goi duoc")


def test_moi_loi_tra_CUNG_MOT_thong_diep():
    """Một artifact của tài khoản khác và một id bịa phải **không phân biệt
    được** — nếu khác nhau, chính thông điệp lỗi thành một cổng dò id."""
    import inspect

    from server.api import uploads

    ma = inspect.getsource(uploads._giai_artifact)
    assert ma.count('f"{param}: unknown media id."') >= 4, (
        "cac nhanh loi phai tra cung mot cau; khac nhau la lo ra su ton tai")


@pytest.mark.parametrize("gia_tri, khop", [
    ("job123.video_key.0", True),
    ("job123.video_key.12", True),
    ("up_abc123", False),                 # upload id — khong co dau cham
    ("job123.video_key", False),          # thieu chi so
    ("job123..0", False),                 # thieu ten truong
    ("", False),
])
def test_mau_artifact_khong_bat_nham_upload_id(gia_tri, khop):
    """Một upload id không bao giờ được đi nhầm sang nhánh artifact."""
    from server.api.uploads import _MAU_ARTIFACT

    assert bool(_MAU_ARTIFACT.fullmatch(gia_tri)) is khop, gia_tri


def test_do_thoi_luong_CHAY_DUOC_tren_artifact_noi_chuoi(monkeypatch):
    """Chỗ dễ vỡ nhất của việc nối chuỗi, và nó là chỗ **tính tiền**.

    Recipe A là `video.generate` → `video.upscale`. Nhưng `video.upscale` khai
    `duration_s: {"measured_from": "video_key"}` — máy chủ **đo** thời lượng từ
    tệp lúc báo giá (H35.10a, đóng lại Q84: giá không bao giờ được tính từ con
    số người gọi khai).

    ⇒ Nếu `apply_server_measurements` không đọc được `ThamChieuArtifact` thì
      chuỗi này chết **ở đúng bước tính tiền** — và nó sẽ chết bằng một 400 khó
      hiểu chứ không phải một câu nói rõ.
    """
    from platform_core.public_api import invocation
    from platform_core.registry import discover

    tool = next(t for m in discover() if not m.error
                and m.manifest.slug == "upscalevideo"
                for t in m.manifest.tools if t.name == "video.upscale")

    # Kho giả: mọi khoá đều giải được thành một đường dẫn.
    class _Kho:
        @staticmethod
        def local_path(key):
            return f"/gia/{key}"

        @staticmethod
        def try_url_for(key):
            return None

    monkeypatch.setattr("platform_core.media.probe",
                        lambda src: {"duration": 12.5})

    tham_chieu = invocation.ThamChieuArtifact(
        staging_key="upscalevideo/u1/job_abc/video_key.mp4",
        filename="video_key.mp4")
    ra = invocation.apply_server_measurements(
        tool, {"video_key": "job_abc.video_key.0"},
        sessions={"video_key": tham_chieu}, storage=_Kho())

    assert ra["duration_s"] == 12.5, (
        "khong do duoc thoi luong tu artifact -> Recipe A chet o buoc tinh tien")
