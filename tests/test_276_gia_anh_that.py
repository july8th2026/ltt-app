"""
test_276 — tính tiền ảnh theo **ảnh thật sự sinh ra**, không theo số đã xin. (H37/L1)

Không mạng, không GPU, không CSDL.

Vì sao có file này: `render_gateway/runner.py` trả về đúng số ảnh nó **tải lên
được** (`image_keys[:so]`) và chỉ ghi log khi thiếu. Nên "xin 4, nhận 2" là một
kết cục có thật. Trước H37/L1, `apps/anhnoibo/jobs.py` không báo `credit_cost`,
nên `job_runner._quyet_toan_credit` thu **trọn phần đã giữ** — khách trả tiền 4
ảnh cho 2 ảnh, im lặng.

Đây đúng là lỗi H38 đã mắc ở cửa job và đã sửa hôm 23/08. Cùng một gốc, cùng một
hình dạng, ở một dự án khác. File này tồn tại để nó không xảy ra lần thứ ba.
"""
from __future__ import annotations

import pytest

from apps.anhnoibo import gia


# ── Tầng 3.2 · 3.3: số học tiền ─────────────────────────────────────────────

def test_gia_la_so_nguyen_va_khong_am():
    for so in range(0, 6):
        for che_do in ("t2i", "edit", "subject", "?"):
            v = gia.tinh(so_anh=so, che_do=che_do)
            assert isinstance(v, int) and not isinstance(v, bool)
            assert v >= 0


def test_khong_ra_anh_nao_thi_thu_khong_dong():
    """Tối thiểu-1-credit là luật của một lượt **có sản phẩm**.

    Một lượt không ra gì thì không có gì để bán — nó đi đường `credit.hoan`.
    """
    assert gia.tinh(so_anh=0, che_do="t2i") == 0
    assert gia.tinh(so_anh=0, che_do="edit") == 0


def test_anh_tham_chieu_dat_gap_ba():
    assert gia.tinh(so_anh=1, che_do="edit") == 3 * gia.tinh(so_anh=1, che_do="t2i")
    assert gia.tinh(so_anh=1, che_do="subject") == 3 * gia.tinh(so_anh=1, che_do="t2i")


def test_tran_giu_cho_luon_lon_hon_hoac_bang_gia_that():
    """3.3 — quét toàn bộ, không lấy mẫu.

    Giữ THIẾU thì khách tiêu quá số dư; giữ DƯ thì hoàn lại. Chiều sai thứ nhất
    đắt hơn nhiều, nên bất đẳng thức này phải đúng ở **mọi** cặp hợp lệ.
    """
    for che_do in ("t2i", "edit", "subject"):
        for xin in range(1, gia.SO_ANH_TOI_DA + 1):
            tran = gia.uoc_tran(so_anh_xin=xin, che_do=che_do)
            for that in range(0, xin + 1):
                assert gia.tinh(so_anh=that, che_do=che_do) <= tran


def test_bang_gia_co_phien_ban():
    b = gia.bang_gia()
    assert b["phien_ban_gia"] == gia.PHIEN_BAN_GIA
    assert b["anh_tham_chieu"] == b["anh_thuong"] * b["he_so_tham_chieu"]


def test_manifest_dung_chung_mot_bang_gia():
    """Không được có bảng giá thứ hai trong manifest."""
    from apps.anhnoibo import manifest
    src = __import__("pathlib").Path(manifest.__file__).read_text(encoding="utf-8")
    assert "CREDIT_MOI_ANH =" not in src, "gia bi khai lai trong manifest"
    assert manifest._gia({"count": 4, "mode": "edit"}) == \
        gia.uoc_tran(so_anh_xin=4, che_do="edit")


def test_tran_so_anh_khop_params_schema():
    """Lệch nhau thì một yêu cầu hợp lệ bị tính giá của một yêu cầu khác."""
    from platform_core import registry
    app = next((a for a in registry.discover() if a.slug == "anhnoibo"), None)
    assert app is not None and not app.error
    schema = app.manifest.tools[0].params_schema
    assert schema["count"]["max"] == gia.SO_ANH_TOI_DA


# ── Tầng 4.4: handler phải báo giá thật ─────────────────────────────────────

class _KetQuaGia:
    def __init__(self, keys):
        self.image_keys = tuple(keys)
        self.prompt_da_gui = "x"
        self.da_dich = False
        self.canh_bao = ()


def _chay_handler(monkeypatch, *, xin: int, nhan: int, che_do: str = "t2i"):
    from apps.anhnoibo import jobs

    class _DP:
        def chay(self, **kw):
            return _KetQuaGia([f"k{i}" for i in range(nhan)])

    monkeypatch.setattr(jobs, "_dieu_phoi", lambda: _DP())
    return jobs.handle({"prompt": "mot con meo", "count": xin, "mode": che_do})


def test_handler_bao_gia_theo_anh_nhan_duoc(monkeypatch):
    """🔴 Chốt chính của file này.

    Xin 4, nhận 2 ⇒ phải báo tiền của **2**. Không có `credit_cost` thì
    `job_runner` thu trọn phần đã giữ, và không có gì báo cho ai biết.
    """
    kq = _chay_handler(monkeypatch, xin=4, nhan=2)
    assert kq["credit_cost"] == gia.tinh(so_anh=2, che_do="t2i")
    assert kq["credit_cost"] < gia.uoc_tran(so_anh_xin=4, che_do="t2i")
    assert kq["so_anh_xin"] == 4 and kq["so_anh_that"] == 2


def test_handler_du_anh_thi_gia_bang_tran(monkeypatch):
    kq = _chay_handler(monkeypatch, xin=2, nhan=2, che_do="t2i")
    assert kq["credit_cost"] == gia.uoc_tran(so_anh_xin=2, che_do="t2i")


def test_handler_bao_phien_ban_gia(monkeypatch):
    """Không có phiên bản thì không đối soát được hoá đơn cũ với bảng giá nào."""
    kq = _chay_handler(monkeypatch, xin=1, nhan=1)
    assert kq["phien_ban_gia"] == gia.PHIEN_BAN_GIA


def test_goi_provider_dem_theo_anh_that(monkeypatch):
    """Giá vốn cũng phải theo ảnh thật, nếu không thì báo cáo lãi/lỗ sai."""
    from platform_core.public_api import costing
    kq = _chay_handler(monkeypatch, xin=4, nhan=1)
    assert kq[costing.KHOA_GOI_PROVIDER][0]["count"] == 1


def test_job_runner_doc_duoc_gia_nay(monkeypatch):
    """Chốt cái khớp nối, không chỉ chốt hai đầu.

    `_safe_credit_cost` từ chối `bool` và giá trị không ép được sang int. Một
    handler báo `credit_cost` mà nền tảng không đọc nổi thì cũng như không báo.
    """
    from platform_core import job_runner
    kq = _chay_handler(monkeypatch, xin=4, nhan=2)
    assert job_runner._safe_credit_cost(kq) == gia.tinh(so_anh=2, che_do="t2i")


# ── Cổng trả rỗng: mâu thuẫn, không phải chuyện im lặng chữa cháy ───────────

def test_cong_thanh_cong_ma_rong_thi_bao_loi():
    """Trước H37/L1, `dieu_phoi` lấy khoá cấp phát trước làm dự phòng.

    Khoá cấp phát trước tồn tại kể cả khi không ảnh nào được tải lên. Nên
    fallback đó khai đủ số ảnh, tính tiền đủ số ảnh, và khách bấm vào thì 404.
    """
    from platform_core.image_gen import dieu_phoi

    class _Cong:
        def gui(self, **kw):
            return None

    class _Ve:
        def __init__(self, key):
            self.key, self.url = key, "https://x/put"

    class _Storage:
        def try_url_for(self, k, ttl_s=0):
            return "https://x/get"

        def try_put_url(self, key, **kw):
            return _Ve(key)

    class _TT:
        thanh_cong = True
        image_keys = ()
        error_code = None
        error_message = None

    dp = dieu_phoi.DieuPhoi(cong=_Cong(), storage=_Storage(), goi_llm=None)
    dp._cho = lambda job_id: _TT()
    with pytest.raises(dieu_phoi.DieuPhoiError) as e:
        dp.chay(job_id="j1", prompt="con meo", mode="t2i", ref_keys=[], so_anh=2,
                negative_prompt="", tien_to_khoa="anhnoibo/u1")
    assert "khong tra ve anh nao" in str(e.value).lower().replace("ô", "o") \
        or "không trả về ảnh nào" in str(e.value)
