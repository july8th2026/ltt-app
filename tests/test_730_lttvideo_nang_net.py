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


# ── 🔴 Viet lai 07/09: hai ham `_job_video_cua_toi` / `_khoa_video` da BI GO ──
#
# Man `lttvideo` thanh studio ba khoang, va hai viec ay chuyen cho:
#
#     chu so huu + dung app   ->  `features.thu_vien()` loc ngay trong SQL
#     doc khoa video          ->  `features._khoa_dau()` tren `video_keys`
#
# ⛔ KHONG xoa cac phep kiem nay theo. Menh de chung canh — "chi video CUA CHU,
#    da xong, cua DUNG app" va "doc dung khoa hop dong `video_keys`" — van la
#    thu phai dung. Xoa mot phep kiem vi ma doi cho la bo mot dam bao, khong
#    phai don dep.

def test_thu_vien_loc_theo_CHU_va_DUNG_APP_ngay_trong_SQL():
    """Thiếu một trong hai vế thì một người dùng đọc được job của người khác,
    hoặc job của app khác lọt vào thư viện video."""
    from apps.lttvideo import features

    ma = inspect.getsource(features.thu_vien)
    assert "Job.user_id == user_id" in ma
    assert 'Job.app_slug == "lttvideo"' in ma


def test_doc_dung_khoa_hop_dong_video_keys():
    """⛔ `server/routes/jobs.py:_artifacts()` chỉ nhặt khoá tận cùng `_key` /
    `_keys`. Tên cũ là `tep` ⇒ job XONG, video nằm trong R2, và người dùng
    KHÔNG TẢI ĐƯỢC — một thất bại không có dấu hiệu nào ở phía máy chủ."""
    from apps.lttvideo import features

    assert features._khoa_dau(["lttvideo/1/a.mp4"]) == "lttvideo/1/a.mp4"
    assert features._khoa_dau([]) == ""
    ma = inspect.getsource(features.thu_vien)
    assert '"video_keys"' in ma
    assert '"tep"' not in ma, "quay lai ten khoa cu — `_artifacts()` se khong thay"


def test_thu_vien_chi_lay_video_DA_XONG_moi_hien_nut_tai():
    """Một nút Tải về trên job chưa xong dẫn tới 404."""
    import pathlib as _pl

    html = (_pl.Path(inspect.getsourcefile(routes)).parent / "templates"
            / "lttvideo.html").read_text(encoding="utf-8")
    # ⚠️ Template co HAI khoi `{% if v.khoa %}`: mot cho o xem truoc, mot cho
    #    cum nut. Bam vao khoi DAU TIEN la do nham cho — ban dau cua phep kiem
    #    nay lam dung the va do, trong khi template hoan toan dung.
    chan = html.split("<footer>", 1)[1].split("</footer>", 1)[0]
    assert "{% if v.khoa %}" in chan, "nut Tai ve/Nang net khong co hang rao khoa"
    trong_rao = chan.split("{% if v.khoa %}", 1)[1].split("{% endif %}", 1)[0]
    assert "download" in trong_rao and "tv-upscale" in trong_rao


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


def test_JS_post_sang_be_mat_CONG_KHAI_cua_upscalevideo():
    """🔴 Viết lại 07/09: biểu mẫu tĩnh đã thành hộp thoại **báo giá trước khi
    xác nhận** (mượn khuôn Seedance). Một thao tác tiêu credit mà không nói giá
    trước là một thao tác người dùng không đồng ý được.

    ⭐ Vẫn đi **bề mặt HTTP công khai** của `upscalevideo`, không import chéo:
       `tests/test_147_layering.py:117` chỉ cho `taovideo -> upscalevideo`, và
       chép công thức giá sang đây là dựng bản sao thứ hai của một quy tắc tiền.
    """
    import pathlib

    js = (pathlib.Path(inspect.getsourcefile(routes)).parents[2] / "server"
          / "static" / "lttvideo.js").read_text(encoding="utf-8")
    assert "/upscalevideo/batch-quote" in js, "khong bao gia truoc khi xac nhan"
    assert "/upscalevideo/queue" in js
    assert "video_key" in js
    # CSRF gan theo PHIEN chu khong theo duong dan, nen token o trang nay dung
    # duoc o route ben kia — nhung phai CO no.
    assert "csrf_token" in js


def test_KHONG_chep_lai_cong_thuc_gia_upscale():
    """Giá phải đến từ `upscalevideo.cost` qua HTTP. Một hằng số giá xuất hiện
    ở phía ta là một bản sao sẽ trôi khi bên kia đổi bảng giá."""
    import pathlib

    js = (pathlib.Path(inspect.getsourcefile(routes)).parents[2] / "server"
          / "static" / "lttvideo.js").read_text(encoding="utf-8")
    for dau_hieu in ("CREDIT_PER_MINUTE", "he_so_res", "he_so_preset"):
        assert dau_hieu not in js


def test_KHONG_them_thao_tac_nao_o_cau_noi_C_CLOUD():
    """Nâng nét chạy ở máy A ⇒ `wangp_client` **không** được mọc thêm đường."""
    from apps.lttvideo import wangp_client

    cay = ast.parse(inspect.getsource(wangp_client))
    ten = {n.name for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)}
    assert "hau_ky" not in ten, "cầu nối mọc thêm đường hậu kỳ — nâng nét ở máy A"
    assert isinstance(routes, types.ModuleType)
