"""Thư viện studio — đếm tab, lọc, và **kho tài sản theo chủ**.

🔑 Bài học mượn nguyên từ `apps/taovideo`: *"browser không được tự khai storage
   key"*. Danh sách tài sản dựng từ **lịch sử job của chính chủ**, và khoá nhận
   lại từ biểu mẫu phải đối chiếu với đúng danh sách ấy — một danh sách trắng
   dựng từ dữ liệu của chủ, không phải một bộ lọc chuỗi.
"""
from __future__ import annotations

from apps.lttvideo import features


class _JobGia:
    def __init__(self, **kw):
        self.id = kw.get("id", "j1")
        self.user_id = kw.get("user_id", 42)
        self.app_slug = "lttvideo"
        self.status = kw.get("status", "done")
        self.progress = kw.get("progress", 0)
        self.progress_msg = kw.get("progress_msg", "")
        self.error = kw.get("error", "")
        self.params = kw.get("params", {})
        self.result = kw.get("result", {})
        self.created_at = kw.get("created_at")
        self.content_expired_at = kw.get("content_expired_at")


class _KhoGia:
    def __init__(self, co=()):
        self.co = set(co)

    def exists(self, key):
        return key in self.co


# ── Dem tab ────────────────────────────────────────────────────────────────

def test_dem_tinh_tren_TOAN_BO_chu_khong_tren_tap_da_loc():
    """🔴 Nếu đếm trên tập đã lọc thì bấm vào tab "Lỗi" sẽ thấy mọi tab khác về
    0, và người dùng đọc thành *"mất hết video"*."""
    rows = [_JobGia(id="a", status="done"), _JobGia(id="b", status="error"),
            _JobGia(id="c", status="running")]

    class _Db:
        def execute(self, _q):
            return type("R", (), {"scalars": lambda s: type(
                "S", (), {"all": lambda s2: rows})()})()

    ra = features.thu_vien(_Db(), 42, trang_thai="error", storage=_KhoGia())
    assert ra["so_dem"]["all"] == 3
    assert ra["so_dem"]["done"] == 1
    assert ra["so_dem"]["error"] == 1
    assert ra["so_dem"]["running"] == 1
    # ...nhung danh sach thi CHI con job loi
    assert [v["job_id"] for v in ra["video"]] == ["b"]


def test_tab_dung_dung_khoa_trang_thai_CUA_NEN_TANG():
    """Đặt tên riêng rồi ánh xạ là dựng một bảng sao sẽ trôi khi nền tảng thêm
    trạng thái."""
    from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR)

    for tt in (JOB_DONE, JOB_ERROR, JOB_CANCELLED):
        assert tt in features.TRANG_THAI_TAB


# ── Tai san theo chu ───────────────────────────────────────────────────────

def test_tai_san_dung_tu_lich_su_cua_chu():
    rows = [_JobGia(id="a", params={"media_key": "lttvideo/42/vao/x.png",
                                    "prompt": "con meo"})]
    ra = features.tai_san_cua_toi(rows, storage=_KhoGia({"lttvideo/42/vao/x.png"}))
    assert len(ra) == 1
    assert ra[0]["khoa"] == "lttvideo/42/vao/x.png"
    assert ra[0]["loai"] == "anh"
    assert ra[0]["het_han"] is False


def test_mp4_nhan_dung_la_video():
    rows = [_JobGia(params={"media_key": "lttvideo/42/vao/y.mp4"})]
    ra = features.tai_san_cua_toi(rows, storage=_KhoGia({"lttvideo/42/vao/y.mp4"}))
    assert ra[0]["loai"] == "video"


def test_tep_da_bi_C2_xoa_thi_danh_dau_HET_HAN_chu_khong_bo_qua():
    """⚠️ `C2` xoá nội dung sau 3 ngày. Im lặng bỏ qua thì người dùng thấy tài
    sản biến mất mà không hiểu vì sao; tệ hơn, họ tưởng mình bấm hỏng."""
    rows = [_JobGia(params={"media_key": "lttvideo/42/vao/cu.png"})]
    ra = features.tai_san_cua_toi(rows, storage=_KhoGia())   # kho RONG
    assert len(ra) == 1, "tai san bien mat khong loi giai thich"
    assert ra[0]["het_han"] is True


def test_khong_trung_lap_khoa():
    rows = [_JobGia(id="a", params={"media_key": "k.png"}),
            _JobGia(id="b", params={"media_key": "k.png"})]
    assert len(features.tai_san_cua_toi(rows, storage=_KhoGia({"k.png"}))) == 1


# ── Hang rao: khoa do TRINH DUYET gui ─────────────────────────────────────

def test_khoa_KHONG_thuoc_lich_su_cua_chu_thi_bi_tu_choi():
    """🔴 Đây là hàng rào chính. Trình duyệt gửi được bất cứ chuỗi nào; nếu ta
    tin nó thì một người dùng đọc được media của người khác."""
    rows = [_JobGia(params={"media_key": "lttvideo/42/vao/cua-toi.png"})]
    kho = _KhoGia({"lttvideo/42/vao/cua-toi.png",
                   "lttvideo/99/vao/cua-nguoi-khac.png"})
    assert features.khoa_tai_san_hop_le(
        rows, "lttvideo/42/vao/cua-toi.png", storage=kho) is True
    # Tep CO THAT trong kho, nhung KHONG nam trong lich su cua chu:
    assert features.khoa_tai_san_hop_le(
        rows, "lttvideo/99/vao/cua-nguoi-khac.png", storage=kho) is False


def test_khoa_da_het_han_thi_bi_tu_choi():
    rows = [_JobGia(params={"media_key": "cu.png"})]
    assert features.khoa_tai_san_hop_le(rows, "cu.png",
                                        storage=_KhoGia()) is False


def test_khoa_rong_bi_tu_choi():
    assert features.khoa_tai_san_hop_le([], "", storage=_KhoGia()) is False


# ── Route: hang rao phai duoc GOI, khong chi ton tai ──────────────────────

def test_route_GOI_hang_rao_truoc_khi_dua_khoa_vao_job():
    """Một hàng rào không ai gọi là một hàng rào không tồn tại."""
    import ast
    import inspect

    from apps.lttvideo import routes

    cay = ast.parse(inspect.getsource(routes.tao_video))
    goi = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and isinstance(n.func.value, ast.Name)}
    assert "features.khoa_tai_san_hop_le" in goi


# ── Ti le: nhan san pham, khong phai so diem anh ──────────────────────────

def test_do_phan_giai_hien_thanh_TI_LE():
    assert features._ti_le("832x480") == "16:9"
    assert features._ti_le("480x832") == "9:16"
    assert features._ti_le("720x720") == "1:1"


def test_do_phan_giai_la_giu_nguyen_khi_khong_biet():
    """Đoán một tỉ lệ sai còn tệ hơn hiện con số thật."""
    assert features._ti_le("1234x567") == "1234x567"
    assert features._ti_le("") == ""
