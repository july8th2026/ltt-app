"""test_1003 — MỘT model thì MỘT giá, và tỉ lệ khách chọn phải tới được máy.

🔴 AI CLEAN REBUILD V2 pha 06.3. Hai phép kiểm này canh hai lỗi mà **chính pha
   06.2 đã tạo ra** và không lượt test nào bắt được:

    giá     `taoanh` di trú sang `hidream-o1` rồi tra bảng giá riêng của nó →
            rơi về mặc định **5**, trong khi `anhnoibo` bán đúng model ấy **3**.
            Không có phép kiểm nào so hai app với nhau, nên nó xanh suốt.

    tỉ lệ   `aspect_ratio` không còn được đọc → khách chọn 9:16 vẫn nhận 16:9.
            Ảnh vẫn đẹp, vẫn đúng chủ đề, chỉ **sai khuôn** — không lỗi nào báo.

⭐ Cả hai đều thuộc một họ: *hỏng mà vẫn trông như chạy*. Phép kiểm cho họ này
   phải so **hai đường độc lập với nhau**, chứ không hỏi một đường xem nó có tự
   thấy mình sai không.
"""
from __future__ import annotations

import pytest

from platform_core.image_gen import cong_render as CR
from platform_core.image_gen import dieu_phoi as DP
from platform_core.image_gen import khung_anh as KA

#: Khung máy B **thật sự** khai (`render_gateway/workflows/catalog.json`). Chép ở
#: đây là chép một **đầu vào của phép kiểm**, không phải chép một bảng giá.
BUCKETS = [[2560, 1440], [1440, 2560], [2048, 2048], [2304, 1728], [1728, 2304]]


# ───────────────────────── một model, một giá ───────────────────────────────
def test_gia_model_nha_chi_co_MOT_ban_the():
    """`apps.anhnoibo.gia` phải LÀ `platform_core.image_gen.gia`, không phải bản sao."""
    from apps.anhnoibo import gia as bi_danh
    from platform_core.image_gen import gia as that

    assert bi_danh.CREDIT_MOI_ANH is that.CREDIT_MOI_ANH
    assert bi_danh.tinh is that.tinh
    assert bi_danh.uoc_tran is that.uoc_tran
    assert bi_danh.PHIEN_BAN_GIA == that.PHIEN_BAN_GIA


@pytest.mark.parametrize("so_anh", [1, 2, 4])
@pytest.mark.parametrize("che_do", ["generate", "edit"])
def test_taoanh_va_anhnoibo_thu_CUNG_MOT_GIA_cho_cung_model(so_anh, che_do):
    """Cùng `hidream-o1` thì cùng giá, dù bán qua tool nào.

    ⛔ Đây là mệnh đề **doanh thu**, không phải mệnh đề gọn gàng: hai bảng lệch
       nhau thì khách tự tìm ra tool rẻ hơn cho cùng một model.
    """
    from apps.anhnoibo.manifest import MANIFEST as M_ANH
    from apps.taoanh.manifest import MANIFEST as M_TAO

    che_do_anh = "edit" if che_do == "edit" else "t2i"
    tao = M_TAO.credit_cost({"count": so_anh, "edit_mode": che_do})
    anh = M_ANH.credit_cost({"count": so_anh, "mode": che_do_anh})
    assert tao == anh, f"taoanh {tao} != anhnoibo {anh} cho {so_anh} anh / {che_do}"


def test_bang_gia_cu_KHONG_duoc_mang_model_nha():
    """`MODEL_CREDIT_PER_IMAGE` chỉ để tra job CŨ — thêm `hidream-o1` vào là dựng
    lại đúng bảng giá thứ hai vừa gỡ."""
    from apps.taoanh.manifest import MODEL_CREDIT_PER_IMAGE as BANG_TAO
    from apps.thumbnail.manifest import MODEL_CREDIT_PER_IMAGE as BANG_TH

    for ten, bang in (("taoanh", BANG_TAO), ("thumbnail", BANG_TH)):
        assert "hidream-o1" not in bang, (
            f"{ten}: gia model nha phai o platform_core.image_gen.gia")


# ───────────────────────── tỉ lệ tới được máy ───────────────────────────────
@pytest.mark.parametrize("ti_le,mong", [
    ("16:9", (2560, 1440)), ("9:16", (1440, 2560)), ("1:1", (2048, 2048)),
    ("4:3", (2304, 1728)), ("3:4", (1728, 2304)),
])
def test_chon_khung_dung_ti_le(ti_le, mong):
    assert KA.chon(ti_le, BUCKETS) == mong


def test_khong_co_khung_dung_ti_le_thi_TU_CHOI_chu_khong_lay_gan_dung():
    with pytest.raises(KA.KhungKhongCo):
        KA.chon("21:9", BUCKETS)


def test_khung_lech_11_phan_tram_KHONG_duoc_tinh_la_khop():
    """16:10 (1,60) không được đội lốt 16:9 (1,78)."""
    with pytest.raises(KA.KhungKhongCo):
        KA.chon("16:9", [[2560, 1600]])


def test_chon_khung_LON_NHAT_khi_nhieu_khung_cung_ti_le():
    assert KA.chon("16:9", [[1920, 1080], [2560, 1440]]) == (2560, 1440)


# ───────────────────────── điều phối gửi đúng khung ─────────────────────────
class _Storage:
    class _Ve:
        def __init__(self, key):
            self.key, self.url = key, f"https://r2/put/{key}"

    def try_put_url(self, key, ttl_s=None, content_type=None):
        return self._Ve(key)

    def try_url_for(self, key, ttl_s=None):
        return f"https://r2/get/{key}"


def _cong(models_ok=True):
    da_gui = []

    def http(method, path, *, json=None, timeout=None):
        if (method, path) == ("GET", "/v1/models"):
            if not models_ok:
                return 503, {}
            return 200, {"data": [{"id": "hidream-o1", "buckets": BUCKETS}]}
        if method == "POST":
            da_gui.append(json)
            return 202, {"status": "queued"}
        return 200, {"job_id": "j1", "status": "completed",
                     "image_keys": ["anh/j1/0.png"]}

    c = CR.CongRender(goi=http)
    c._da_gui = da_gui       # type: ignore[attr-defined]
    return c


def _dp(cong):
    return DP.DieuPhoi(cong=cong, storage=_Storage(), goi_llm=lambda t, h: "a cat",
                       sleep=lambda _: None, now=_dong_ho())


def _dong_ho():
    hop = {"t": 0.0}

    def now():
        hop["t"] += 1.0
        return hop["t"]
    return now


def test_ti_le_thanh_width_height_TRONG_than_gui_di():
    cong = _cong()
    _dp(cong).chay(job_id="j1", prompt="mèo", ti_le="9:16")
    than = cong._da_gui[0]
    assert than["params"]["width"] == 1440 and than["params"]["height"] == 2560


def test_khong_truyen_ti_le_thi_KHONG_hoi_cong_va_KHONG_chen_khung():
    """Không xin tỉ lệ ⇒ để cổng dùng mặc định của model. Không hỏi thừa một lượt."""
    cong = _cong()
    _dp(cong).chay(job_id="j1", prompt="mèo")
    than = cong._da_gui[0]
    assert "width" not in than["params"] and "height" not in than["params"]


def test_cong_khong_tra_loi_thi_KHONG_ve_dai_16_9():
    """⛔ Fail-closed. Không xác nhận được khung thì không vẽ."""
    cong = _cong(models_ok=False)
    with pytest.raises(DP.DieuPhoiError):
        _dp(cong).chay(job_id="j1", prompt="mèo", ti_le="9:16")
    assert cong._da_gui == [], "da gui viec di roi moi biet khong xac nhan duoc khung"
