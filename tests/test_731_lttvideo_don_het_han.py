"""`C2` — video giữ 3 ngày, và **chỉ** video của `lttvideo`.

⛔ Đây là một thao tác **không hoàn tác được**. Mọi phép kiểm ở đây hỏi cùng một
   câu: *"nó có đụng thứ không được đụng không?"*
"""
from __future__ import annotations

import ast
import inspect
import pathlib
from datetime import datetime, timedelta, timezone

from apps.lttvideo import features


class _JobGia:
    def __init__(self, **kw):
        self.id = kw.get("id", "j1")
        self.app_slug = kw.get("app_slug", "lttvideo")
        self.status = kw.get("status", "done")
        self.finished_at = kw.get("finished_at")
        self.content_expired_at = kw.get("content_expired_at")
        self.params = kw.get("params", {})
        self.result = kw.get("result", {})


def test_GIU_NGAY_dung_bang_quyet_dinh_da_chot():
    assert features.GIU_NGAY == 3


def test_KHONG_ha_han_toan_cuc_cua_nen_tang():
    """⛔ Hạ `RETENTION_DAYS` toàn cục xuống 3 sẽ xoá sớm nội dung của **mọi**
    app khác — một thao tác không hoàn tác, làm thay người mà không hỏi."""
    from platform_core import job_content

    assert job_content.RETENTION_DAYS == 30, (
        "ai đó đã đổi hạn TOÀN CỤC; `lttvideo` phải quét riêng, không hạ hằng "
        "số dùng chung")


def test_dung_lai_phep_XOA_AN_TOAN_cua_nen_tang_chu_khong_tu_viet():
    """⭐ `expire_content` chỉ đụng chuỗi trong `params`/`result` **có chứa id
    của chính job đó**. Tự viết vòng xoá khoá R2 là vứt bỏ đúng đảm bảo ấy."""
    cay = ast.parse(inspect.getsource(features))
    ten_goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "expire_content" in ten_goi
    ma = inspect.getsource(features)
    assert ".delete(" not in ma, "app tự xoá khoá — dùng `expire_content`"
    assert "remove(" not in ma


def test_chi_quet_job_CUA_APP_NAY():
    """Thiếu vế `app_slug` thì phép quét 3 ngày của ta sẽ xoá nội dung của app
    khác — những app mà chủ dự án đã hứa giữ 30 ngày."""
    ma = inspect.getsource(features)
    assert 'Job.app_slug == "lttvideo"' in ma


def test_chi_quet_job_DA_KET_THUC():
    """Job đang chờ/đang chạy còn cần chính `params` của nó để chạy được.

    🔴 Viết lại 07/09. Bản cũ quét **cả module** `features`, và nó xanh chỉ vì
       lúc ấy module chỉ có mỗi phép dọn. Khi khoang thư viện dọn vào cùng tệp —
       và nó **phải** nhắc `JOB_QUEUED`/`JOB_RUNNING` để đếm tab — phép kiểm đỏ
       lên dù `don_het_han` không đổi một dòng nào.

    ⇒ Mệnh đề phải **bất biến với tập hợp**: nó nói về *phép dọn*, nên nó phải
      đo *phép dọn*, không đo cái tệp tình cờ chứa phép dọn.
    """
    ma = inspect.getsource(features.don_het_han)
    assert "JOB_DONE" in ma and "JOB_ERROR" in ma and "JOB_CANCELLED" in ma
    assert "JOB_RUNNING" not in ma and "JOB_QUEUED" not in ma


def test_moc_thoi_gian_tinh_dung_3_ngay():
    """Kiểm phép tính mốc, không cần CSDL."""
    gio = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    moc = gio - timedelta(days=features.GIU_NGAY)
    assert moc == datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def test_features_KHONG_nam_trong_routes():
    """Hợp đồng app: route chỉ lo HTTP, nghiệp vụ ở `features.py`."""
    r = (pathlib.Path(inspect.getsourcefile(features)).parent
         / "routes.py").read_text(encoding="utf-8")
    assert "GIU_NGAY" not in r
