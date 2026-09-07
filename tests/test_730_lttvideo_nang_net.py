"""Nút **Nâng nét** — nối sang `upscalevideo`, chạy trên GPU máy A.

⭐ Không có thao tác mới nào ở cầu nối C-CLOUD. Bản plan trước định đẩy tệp
   ngược từ R2 lên C-CLOUD để hậu kỳ ở đó; chủ dự án chỉ ra rằng LTT **đã có**
   `apps/upscalevideo` chạy `realesrgan` trên GPU máy A. Việc còn lại chỉ là
   một dây nối.
"""
from __future__ import annotations

import ast
import inspect
import types

from apps.lttvideo import routes


class _JobGia:
    def __init__(self, **kw):
        self.id = kw.get("id", "j1")
        self.user_id = kw.get("user_id", "u1")
        self.app_slug = kw.get("app_slug", "lttvideo")
        self.status = kw.get("status", "done")
        self.result = kw.get("result", {"video_keys": ["lttvideo/1/a.mp4"]})
        self.params = kw.get("params", {"prompt": "mot dong song"})


class _DbGia:
    def __init__(self, job):
        self._job = job

    def get(self, _model, _id):
        return self._job


def _db(**kw):
    return _DbGia(_JobGia(**kw))


def test_dung_chu_dung_app_da_xong_thi_nhan():
    assert routes._job_video_cua_toi(_db(), "u1", "j1") is not None


def test_SAI_CHU_thi_tu_choi():
    assert routes._job_video_cua_toi(_db(user_id="u2"), "u1", "j1") is None


def test_SAI_APP_thi_tu_choi():
    """⛔ Thiếu vế này thì một `job_id` của app khác cũng qua được, và ta sẽ
    đem khoá của nó đi nâng cấp — tức chạm dữ liệu ngoài phạm vi app."""
    assert routes._job_video_cua_toi(_db(app_slug="taovideo"), "u1", "j1") is None


def test_CHUA_XONG_thi_tu_choi():
    assert routes._job_video_cua_toi(_db(status="running"), "u1", "j1") is None


def test_khoa_video_doc_dung_khoa_hop_dong():
    """`video_keys` — cùng tên mà `_artifacts()` của nền tảng nhặt được."""
    j = _JobGia()
    assert routes._khoa_video(j) == "lttvideo/1/a.mp4"
    assert routes._khoa_video(_JobGia(result={})) == ""
    assert routes._khoa_video(_JobGia(result={"tep": ["x.mp4"]})) == "", (
        "đọc tên khoá CŨ — nền tảng sẽ không nhặt được khoá đó")


def test_nut_nang_net_KHONG_import_cheo_app():
    """🔴 Bản đầu import `apps.upscalevideo.service.submit_upscale_job`.

    `tests/test_147_layering.py` bắt, và chú thích của chính nó gọi cách ấy là
    **nợ**: *"gỡ hay đổi tên `upscalevideo` sẽ làm gãy `taovideo`"*. `taovideo`
    được miễn vì nó là luồng **trả tiền đang chạy**; thêm một app mới vào khoản
    nợ ấy thì không có lý do nào.

    ⇒ Nút là một `<form>` post thẳng sang bề mặt HTTP công khai của
      `upscalevideo` — chính đường mà GUI của nó dùng. Không import, không
      ngoại lệ linter, không nhân đôi hợp đồng tham số.
    """
    ma = inspect.getsource(routes)
    cay = ast.parse(ma)
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("apps."):
            assert "lttvideo" in (n.module or ""), f"import chéo: {n.module}"
        if isinstance(n, ast.Import):
            for a in n.names:
                assert not a.name.startswith("apps.upscalevideo"), "import chéo"


def test_template_post_sang_be_mat_CONG_KHAI_cua_upscalevideo():
    import pathlib

    html = (pathlib.Path(inspect.getsourcefile(routes)).parent / "templates"
            / "lttvideo.html").read_text(encoding="utf-8")
    assert 'action="/upscalevideo/queue"' in html
    assert 'name="video_key"' in html
    # CSRF gan theo PHIEN chu khong theo duong dan, nen token o trang nay dung
    # duoc o route ben kia — nhung phai CO no.
    assert 'name="csrf_token"' in html


def test_KHONG_them_thao_tac_nao_o_cau_noi_C_CLOUD():
    """Nâng nét chạy ở máy A ⇒ `wangp_client` **không** được mọc thêm đường."""
    from apps.lttvideo import wangp_client

    cay = ast.parse(inspect.getsource(wangp_client))
    ten = {n.name for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)}
    assert "hau_ky" not in ten, "cầu nối mọc thêm đường hậu kỳ — nâng nét ở máy A"
    assert isinstance(routes, types.ModuleType)
