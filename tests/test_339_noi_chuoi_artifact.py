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

    # ⚠️ Doc `_mot_media`, khong doc `promote_media`: logic dời/tham chieu nam o
    #    do tu khi them nhanh MANG. Ban dau phep kiem nay doc `promote_media` va
    #    do — khong phai vi mat bat bien, ma vi no chot TEN HAM thay vi tinh
    #    chat. Cung bai hoc da rut o banh coc kieu xuong dong.
    ma = inspect.getsource(invocation._mot_media)
    assert "ThamChieuArtifact" in ma, (
        "duong promote khong phan biet artifact voi upload — no se DOI tep cua "
        "job truoc di, va lan tai sau se 404")
    # Va no phai tra ve TRUOC khi cham `upload_sessions.promote`.
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


# ── Nhiều tệp cho một tham số (30/08, bậc 1 của đề xuất §17) ───────────────

def test_mang_KHONG_duoc_la_duong_vong_qua_kiem_quyen():
    """🔴 Bất biến quan trọng nhất của việc mở tham số dạng mảng.

    Một tham số đơn đi qua `resolve_upload_reference`, và hàm đó đòi đủ hai
    cổng. Nếu nhánh mảng gọi thẳng vào kho hoặc bỏ qua hàm đó, thì **mảng trở
    thành đường vòng**: khách gửi một danh sách và lấy được tệp của người khác.

    ⇒ Mỗi phần tử phải đi qua **đúng** hàm đó, không có nhánh riêng.
    """
    import inspect

    from server.api import jobs

    ma = inspect.getsource(jobs)
    dau = ma.index("def _media_sessions")
    than = ma[dau:ma.index("@api.post", dau)]
    # Dem CHO GOI, khong dem lan nhac ten (docstring cung nhac no).
    goi = [d for d in than.splitlines() if "resolve_upload_reference(" in d]
    assert len(goi) == 2, (
        f"phai co dung hai cho goi — mot cho tham so don, mot cho phan tu cua "
        f"mang. Dang thay {len(goi)}: {goi}")
    assert "TRAN_MEDIA_MOT_THAM_SO" in than, "thieu tran so luong"


def test_mang_co_TRAN_so_luong():
    """⛔ Mỗi phần tử là một lượt tra CSDL chạy **trước** khi có tiền.

    Không có trần thì một danh sách nghìn id là cách bắt máy chủ làm việc miễn
    phí — và nó không hiện ra như một cuộc tấn công, nó hiện ra như một request
    chậm.
    """
    from platform_core.public_api import invocation

    assert 1 <= invocation.TRAN_MEDIA_MOT_THAM_SO <= 32, (
        "tran phai co that va phai chat; nang duoc luc nao cung duoc, ha thi kho")


def test_moi_tep_trong_mang_co_KHOA_RIENG_khi_promote():
    """Hai tệp cùng một tham số không được ghi đè lên nhau.

    Bản đầu dùng `{param}{suffix}` cho mọi phần tử — tức tệp thứ hai đè tệp thứ
    nhất, và khách trả tiền cho một job dùng sai ảnh mà không có gì báo.
    """
    import inspect

    from platform_core.public_api import invocation

    ma = inspect.getsource(invocation.promote_media)
    assert 'f"{param}_{i}"' in ma, (
        "moi phan tu phai co khoa rieng, neu khong tep sau de len tep truoc")


def test_refs_VAN_HOAN_va_ly_do_khac_han_ba_cai_kia():
    """`refs` là `json`, không phải kiểu media — không cổng nào kiểm nó được."""
    from platform_core.registry import discover

    tool = next(t for m in discover() if not m.error
                and m.manifest.slug == "taovideo"
                for t in m.manifest.tools if t.name == "video.generate")
    an = tuple(tool.api_contract.get("hidden") or ())
    assert an == ("refs",), f"chi `refs` con hoan, dang thay: {an}"
    assert tool.params_schema["refs"]["type"] == "json", (
        "neu `refs` thanh kieu media thi ly do hoan khong con dung nua")
