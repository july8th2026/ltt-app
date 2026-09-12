"""F07 / N3 — máy A có THẬT SỰ hành động khi máy B báo model đang chạy CPU?

## Mắt xích chưa ai kiểm

Rà soát 01/09 thấy chuỗi cảnh báo `ltt_llm:tren_cpu` được kiểm ở **hai đầu** mà
**không ở giữa**:

```
llm_gateway/tren_gpu.py   dang_lo=True khi VRAM thấp     test_270  ✅ 10 phép
        |
        |  <-- MẮT XÍCH NÀY: job_runner._tham_gpu_may_b đọc /health của máy B
        |      rồi increment metric.  KHÔNG AI KIỂM.
        v
ops_alerts.NGUONG["ltt_llm:tren_cpu"] == 1                test_270  ✅
```

⛔ Vì sao đúng chỗ này nguy hiểm: nếu ai đó sửa `_tham_gpu_may_b` và cắt mất
dây, **hai đầu vẫn xanh**. Bộ dò vẫn dò đúng, ngưỡng vẫn còn đó, mọi phép kiểm
vẫn pass — và triệu chứng khi có sự cố thật là **sự im lặng**, thứ trông y hệt
"không có sự cố nào".

⭐ Cùng hình dạng với bánh cóc ở `test_368` (đã gỡ cùng nhánh nó đo, dual-model
   5.4b): ở đó `trong_tai.py` được sửa đúng nhưng `api.py` có thể quên nối dây, và
   triệu chứng là 70 % từ chối oan **vẫn nguyên, không dòng đỏ nào**.

## Vì sao đây là cách đúng để phủ F07

Prompt 06 §1 đòi `failure → detect → recovery` cho "CUDA failure". **Không tiêm
được lỗi CUDA một cách an toàn** — làm hỏng CUDA trên một máy đang phục vụ là
một hành động không đảo được, và cái giá lớn hơn thứ nó dạy.

Nhưng thứ *thật sự* hỏng ở sự cố 23/08 **không phải CUDA** — mà là **hơn một giờ
không ai biết**. Cái đó kiểm được, và kiểm ở đây.

⚠️ Phép kiểm này **không** thay cho một sự cố thật (N3 vẫn mở). Nó chốt rằng dây
   còn nối; nó không chứng minh cảnh báo tới được tay người trực.
"""
from __future__ import annotations

import pytest

from platform_core import job_runner


class _GiaPhanHoi:
    def __init__(self, gpu: dict | None, status: int = 200):
        self.status_code = status
        self._gpu = gpu

    def json(self):
        return {"gpu": self._gpu} if self._gpu is not None else {}


@pytest.fixture
def bat_metric(monkeypatch):
    """Bắt mọi lượt `metrics.increment` mà không chạm CSDL."""
    da_dem: list[str] = []
    from platform_core.public_api import metrics
    monkeypatch.setattr(metrics, "increment",
                        lambda ten, *a, **k: da_dem.append(ten))
    return da_dem


@pytest.fixture
def duong_that(monkeypatch):
    """Đưa `_tham_gpu_may_b` ĐI ĐẾN được chỗ đọc `/health`.

    🔴 BẢN ĐẦU CỦA FIXTURE NÀY LÀ MỘT DỤNG CỤ HỎNG, và nó hỏng theo đúng kiểu
       tệ nhất. Nó patch `job_runner._goc_va_token_vlm` — **một tên không tồn
       tại** — với `raising=False`, nên `monkeypatch` **im lặng không làm gì**.

       Hậu quả: hàm thoát ngay ở dòng đầu (`LTT_LLM_BASE_URL` rỗng ⇒ `return
       True`) và **không bao giờ chạm** phần cần kiểm. Phép kiểm chính đỏ, và
       tôi suýt đọc nó thành *"dây đã đứt — bug thật"*.

    ⛔ Tệ hơn: tám phép kiểm còn lại **XANH**, và xanh **vô nghĩa** —
       `bat_metric == []` đúng một cách tầm thường khi hàm trả về trước khi làm
       gì. Tức bộ này đọc lên là "1 đỏ / 8 xanh" trong khi sự thật là
       **0 phép kiểm nào thực sự chạy**.

    ⇒ Hai đường phải mở, cả hai đều là điều kiện thoát sớm THẬT trong mã:
         1. `LTT_LLM_BASE_URL` — không có thì không biết hỏi ai
         2. khoá `ltt_llm` từ `api_pool` — không có thì không đoán, không báo
    """
    def _dat(gpu, status=200, no_mang=False):
        import httpx
        from platform_core import api_keys, api_pool

        monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299")
        monkeypatch.setattr(api_pool, "chon_key", lambda *a, **k: object())
        monkeypatch.setattr(api_keys, "lay_credential", lambda *a, **k: "tok")

        if no_mang:
            def no(*a, **k):
                raise httpx.ConnectError("may B khong tra loi")
            monkeypatch.setattr(httpx, "get", no)
        else:
            monkeypatch.setattr(
                httpx, "get", lambda *a, **k: _GiaPhanHoi(gpu, status))
    return _dat


@pytest.fixture
def dat_health(duong_that):
    return duong_that


def test_FIXTURE_that_su_di_toi_noi(dat_health, bat_metric):
    """⭐ ĐỐI CHỨNG CHO CHÍNH BỘ NÀY — phải chạy trước khi tin phép kiểm nào.

    Nếu `_tham_gpu_may_b` thoát sớm thì **mọi** phép kiểm dưới đây xanh một cách
    tầm thường. Phép kiểm này bắt buộc nó phải đi hết đường: đưa vào một `/health`
    báo `dang_lo`, và đòi thấy metric. Không thấy ⇒ fixture hỏng, không phải mã hỏng.
    """
    dat_health({"dang_lo": True, "co_model_nap": True, "vram_dung_mb": 1153})
    job_runner._tham_gpu_may_b(None)
    assert bat_metric, (
        "fixture KHONG dua duoc ham toi cho doc /health -- moi phep kiem trong "
        "tep nay dang xanh mot cach VO NGHIA")


class TestDayCONNOI:
    def test_may_B_bao_dang_lo_thi_may_A_DEM_canh_bao(self, bat_metric,
                                                      dat_health, monkeypatch):
        """🔴 Phép kiểm chính. Cắt dây ở `_tham_gpu_may_b` thì đây là chỗ đỏ."""
        dat_health({"dang_lo": True, "vram_dung_mb": 1153,
                    "co_model_nap": True, "tren_gpu": False,
                    "ly_do": "VRAM 1153 MB duoi nguong"})
        ket = job_runner._tham_gpu_may_b(None)
        assert ket is False, "bao dang_lo ma ham van noi 'binh thuong'"
        assert "ltt_llm:tren_cpu" in bat_metric, (
            "may B da bao model chay tren CPU ma may A KHONG dem canh bao nao "
            "-- day da dut, va trieu chung khi co su co that la SU IM LANG")

    def test_may_B_khoe_thi_KHONG_bao_dong(self, bat_metric, dat_health):
        """Đối chứng. Nếu nó đếm cả khi khoẻ thì phép kiểm trên vô nghĩa."""
        dat_health({"dang_lo": False, "vram_dung_mb": 22416,
                    "co_model_nap": True, "tren_gpu": True, "ly_do": ""})
        assert job_runner._tham_gpu_may_b(None) is True
        assert "ltt_llm:tren_cpu" not in bat_metric


class TestKHONG_DO_DUOC_thi_IM:
    """`None` không phải `True`. Một chốt đoán bừa sẽ bị tắt, rồi kéo theo cả ca thật."""

    @pytest.mark.parametrize("gpu", [
        {"dang_lo": None, "tren_gpu": None, "co_model_nap": False},
        {"dang_lo": False, "tren_gpu": None, "co_model_nap": False},
        {},
        None,
    ])
    def test_khong_chac_chan_thi_khong_dem(self, bat_metric, dat_health, gpu):
        dat_health(gpu)
        assert job_runner._tham_gpu_may_b(None) is True
        assert bat_metric == [], (
            f"bao dong khi CHUA CHAC ({gpu}) -- duong tinh gia se lam nguoi "
            f"truc tat canh bao, va khi tat thi ca truong hop that cung mat")

    def test_health_hong_thi_KHONG_dem_lan_hai(self, bat_metric, dat_health):
        """`_tham_cong_vlm` đã lo phần chết/sống rồi — đếm hai lần là báo trùng."""
        dat_health({"dang_lo": True}, status=503)
        assert job_runner._tham_gpu_may_b(None) is True
        assert bat_metric == []

    def test_mang_hong_thi_KHONG_dem_lan_hai(self, bat_metric, dat_health):
        dat_health(None, no_mang=True)
        assert job_runner._tham_gpu_may_b(None) is True
        assert bat_metric == []


class TestNguongVanLaMOT:
    def test_ban_ngay_lan_dau(self):
        """Ngưỡng 1, không phải 2 — CUDA hỏng **không tự khỏi**.

        Sự cố 23/08 chạy **hơn một giờ** trước khi tình cờ bị phát hiện. Mỗi vòng
        chờ thêm là tiền và thời gian của khách, và không có dương tính giả để
        phải phòng (chốt chỉ bật khi CHẮC CHẮN).
        """
        from platform_core.public_api.ops_alerts import NGUONG
        assert NGUONG["ltt_llm:tren_cpu"] == 1
        assert NGUONG["ltt_image:tren_cpu"] == 1, "ben anh cung mot ly do"


class TestThamMoCoi:
    """Cùng thân `/health`, cùng họ lỗi — nên nằm cùng vòng thăm, không vòng riêng.

    Đo 01/09: `/health` trả **200 suốt 99 giây** trong khi `Get-Service` nói
    `Stopped`. Máy A không có cách nào biết, vì nó chỉ hỏi *"anh có khoẻ không"*.
    Nay cổng tự khai `duoi_dich_vu.mo_coi` và máy A đọc nó ở đây.

    ⛔ Dùng `monkeypatch` chứ KHÔNG gán thẳng thuộc tính module rồi
       `importlib.reload`. Bản đầu tôi viết kiểu đó: nó chạy xanh, nhưng reload
       một module giữa phiên là **rò trạng thái sang phép kiểm khác** — thứ làm
       một bộ test xanh khi chạy riêng và đỏ khi chạy cả cụm.
    """

    @pytest.fixture
    def dat_than(self, monkeypatch):
        def _dat(than):
            monkeypatch.setattr(job_runner, "_health_may_b", lambda db: than)
        return _dat

    def test_may_B_khai_mo_coi_thi_may_A_DEM(self, bat_metric, dat_than):
        """Khoẻ về MỌI mặt khác, chỉ mồ côi — đúng hình dạng đo được 01/09."""
        dat_than({"gpu": {"dang_lo": False, "tren_gpu": True},
                  "duoi_dich_vu": {"theo_doi": True, "mo_coi": True,
                                   "vo_boc_pid": 3896,
                                   "vo_boc_sinh": "2026-09-01T01:10:00"}})
        assert job_runner._tham_mo_coi_may_b(None) is False
        assert "ltt_llm:mo_coi" in bat_metric

    def test_khoe_va_KHONG_mo_coi_thi_im(self, bat_metric, dat_than):
        dat_than({"duoi_dich_vu": {"theo_doi": True, "mo_coi": False}})
        assert job_runner._tham_mo_coi_may_b(None) is True
        assert bat_metric == []

    @pytest.mark.parametrize("than", [
        {},                                              # cong CU, khong co truong
        {"gpu": {}},
        {"duoi_dich_vu": None},
        {"duoi_dich_vu": {"theo_doi": False, "mo_coi": None}},   # chay tay
        None,                                            # khong doc duoc /health
    ])
    def test_thieu_truong_la_CHUA_BIET_chu_khong_phai_binh_thuong(
            self, bat_metric, dat_than, than):
        """⚠️ Coi thiếu là "bình thường" thì một lần deploy hụt sẽ tắt vĩnh viễn
        phép thăm này mà không ai hay — cùng lớp lỗi với `.get()` trả `None`."""
        dat_than(than)
        assert job_runner._tham_mo_coi_may_b(None) is True, than
        assert bat_metric == [], than

    def test_nguong_la_MOT(self):
        """Mồ côi **không có ai để dựng dậy nó cả** — khác `tren_cpu` ở chỗ đó.

        `tren_cpu` cần một lần khởi động lại máy. Mồ côi thì dịch vụ đã `Stopped`,
        SCM không giành được cổng, và tiến trình đang phục vụ là thứ cuối cùng
        còn sống. Nó chạy cho tới khi chết, rồi hết.
        """
        from platform_core.public_api.ops_alerts import NGUONG
        assert NGUONG["ltt_llm:mo_coi"] == 1
