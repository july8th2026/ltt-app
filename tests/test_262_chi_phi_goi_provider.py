"""
test_262 — ghi chi phí **gọi nhà cung cấp**. (MVP đợt 0.4)

Không mạng, không GPU, không CSDL thật.

⭐ VÌ SAO CẦN LOẠI CHI PHÍ NÀY

   `costing.py` đã có ba loại: `duration_ms`, `bytes`, `tokens`. Với một job ảnh,
   **khoản chi lớn nhất là một lần gọi API tính theo ảnh** — không phải token,
   không phải giây, không phải byte. Trước 23/08/2026 nó **không có chỗ để ghi**.

   Đó là lý do một khoản lỗ 45–57 % chạy 22 ngày mà bảng biên lợi nhuận trong admin
   không hề thấy: nó đo đúng những thứ nó biết đo, và khoản lớn nhất không nằm
   trong số đó.
"""
from __future__ import annotations

import pathlib

import types

import pytest

from platform_core import gia_von
from platform_core.public_api import costing
from platform_core.public_api.tables import COST_PROVIDER_CALL


class DbGia:
    def __init__(self):
        self.hang = []

    def add(self, row):
        self.hang.append(row)

    def execute(self, *_a, **_k):
        return types.SimpleNamespace(scalars=lambda: types.SimpleNamespace(all=list))


def _job(ket_qua: dict, job_id: str = "j1"):
    return types.SimpleNamespace(id=job_id, result=ket_qua, params={})


def _ghi(ket_qua, env=None):
    db = DbGia()
    costing.record_job(db, _job(ket_qua), env=env if env is not None else {})
    return [r for r in db.hang if r.kind == COST_PROVIDER_CALL]


# ═══════════ ghi được, và ra đúng số ════════════════════════════════════════
def test_ghi_chi_phi_mot_anh_Gemini_Pro():
    """35,242 mcredit = 35.242.000 micro. Đây là con số làm bậc `pro` bị đóng."""
    r = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "gemini-3-pro-image", "count": 1}]})
    assert len(r) == 1
    assert r[0].quantity == 1
    assert r[0].cost_micros == gia_von.mot_anh("gemini-3-pro-image") * 1000


def test_nhan_dung_theo_SO_ANH():
    r = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "gemini-2.5-flash-image", "count": 3}]})
    assert r[0].quantity == 3
    assert r[0].cost_micros == 3 * gia_von.mot_anh("gemini-2.5-flash-image") * 1000


def test_che_do_THAM_CHIEU_ghi_gia_dat_hon():
    """Model nhà: ảnh tham chiếu tốn ~3,3 lần thời gian GPU. Báo cùng một giá là
    giấu mất chi phí của chế độ đắt."""
    thuong = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "hidream-o1", "count": 1}]})
    tc = _ghi({costing.KHOA_GOI_PROVIDER: [
        {"model": "hidream-o1", "count": 1, "tham_chieu": True}]})
    assert tc[0].cost_micros > thuong[0].cost_micros


def test_nhieu_model_trong_mot_job_ghi_rieng_tung_dong():
    """Một job có thể rẽ sang model thứ hai khi model đầu hỏng. Gộp lại thành một
    dòng là mất dấu chuyện đó."""
    r = _ghi({costing.KHOA_GOI_PROVIDER: [
        {"model": "gemini-2.5-flash-image", "count": 2},
        {"model": "gemini-3.1-flash-image", "count": 1}]})
    assert len(r) == 2


# ═══════════ ⛔ không biết giá thì KHÔNG ghi, tuyệt đối không ghi 0 ══════════
def test_model_LA_thi_KHONG_ghi_dong_nao():
    """⛔ Một số 0 chảy vào biên lợi nhuận và đọc thành *"phục vụ cái này miễn
    phí"*. Vắng mặt là trung thực; số 0 là một lời nói dối có định dạng đẹp."""
    assert _ghi({costing.KHOA_GOI_PROVIDER: [
        {"model": "model-chua-bao-gio-ton-tai", "count": 5}]}) == []


def test_model_CHUA_TRA_gia_cung_KHONG_ghi():
    """`seedance-2.0` có miễn trừ chưa tra giá — không được biến nó thành 0."""
    assert _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "seedance-2.0", "count": 1}]}) == []


@pytest.mark.parametrize("xau", [
    {},                                            # khong co khoa
    {costing.KHOA_GOI_PROVIDER: "khong-phai-list"},
    {costing.KHOA_GOI_PROVIDER: [None, 5, "x"]},
    {costing.KHOA_GOI_PROVIDER: [{"count": 1}]},               # thieu model
    {costing.KHOA_GOI_PROVIDER: [{"model": "hidream-o1", "count": 0}]},
    {costing.KHOA_GOI_PROVIDER: [{"model": "hidream-o1", "count": "hai"}]},
])
def test_du_lieu_xau_KHONG_lam_hong_ca_viec_ghi(xau):
    """Ghi chi phí là việc **phụ**. Nó không được phép làm hỏng một job đã xong."""
    assert _ghi(xau) == []


# ═══════════ nguồn giá phải phân biệt được ══════════════════════════════════
def test_nguon_la_GIA_VON_chu_khong_phai_suat_gia_nguoi_van_hanh_nhap():
    """Hai nguồn khác nhau thì độ tin khác nhau. `configured_rate` là con số người
    vận hành gõ vào; `gia_von` là bảng giá công bố đã tra và có ngày. Trang admin
    phải đọc ra được sự khác biệt đó."""
    r = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "hidream-o1", "count": 1}]})
    assert r[0].source == "gia_von"


def test_van_la_UOC_TINH_du_gia_lay_tu_bang_gia_cong_bo():
    """Bảng giá không phải hoá đơn: giảm giá theo lô, bậc dùng, tỉ giá đổi — cả ba
    đều làm số thật lệch đi."""
    r = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "hidream-o1", "count": 1}]})
    assert r[0].is_estimate is True


# ═══════════ ⛔ KHÔNG bị chặn bởi biến môi trường ═══════════════════════════
def test_ghi_duoc_NGAY_CA_KHI_khong_dat_suat_gia_nao():
    """⛔ Ràng buộc quan trọng nhất của tệp này.

    `record_job` trước đây `return []` ngay khi không có `LTT_COST_MICROS_PER_*`.
    Production **chưa từng đặt biến nào** — nên bảng biên lợi nhuận trống, và khoản
    lỗ lớn nhất vô hình. Loại chi phí này có **nguồn giá riêng**, nên bắt nó chờ
    một biến môi trường nó không cần là tái tạo lại đúng cái lỗ hổng đó."""
    r = _ghi({costing.KHOA_GOI_PROVIDER: [{"model": "gemini-3-pro-image", "count": 1}]},
             env={})
    assert len(r) == 1, "bi chan boi bien moi truong — dung cai loi da tao ra lo hong"


# ═══════════ ba app gọi provider đều phải báo ═══════════════════════════════
@pytest.mark.parametrize("goi", ["taoanh", "thumbnail", "anhnoibo"])
def test_moi_app_goi_provider_deu_BAO_LAI(goi):
    """Bánh cóc: một app gọi nhà cung cấp mà không báo lại thì bảng biên lợi nhuận
    thấy doanh thu của nó mà không thấy chi phí — tệ hơn là không thấy gì cả.

    ⭐ Quét **cả gói app**, không riêng `jobs.py`. Chỗ ghi nhận chi phí là quy tắc
       nghiệp vụ, và `AGENTS.md` mục 8 nói nghiệp vụ ở `features.py`/`services/`
       chứ không ở handler. `anhnoibo` đã chuyển đúng như vậy (H37/L6), và bản cũ
       của test này đỏ vì nó grep đúng một tệp — tức là nó chốt **nơi để mã**,
       không phải **điều cần đúng**.
    """
    import importlib

    thu_muc = pathlib.Path(importlib.import_module(f"apps.{goi}").__file__).parent
    ma = chr(10).join(f.read_text(encoding="utf-8")
                      for f in sorted(thu_muc.rglob("*.py")))
    assert "KHOA_GOI_PROVIDER" in ma, f"apps/{goi} khong bao chi phi goi provider"


def test_thumbnail_bao_MODEL_THAT_chu_khong_phai_gia_phang(tmp_path, monkeypatch):
    """Báo cáo chi phí phải nói **đúng model đã gửi đi**.

    🔴 Viết lại 09/09/2026 (pha 06.3). Bản cũ đọc **văn bản mã nguồn** và tìm
       chuỗi `'"model": model'` — nó đo một CÁCH VIẾT, không đo giá trị báo
       về. Khi app chuyển sang một model duy nhất, `_MODEL` là hằng số và
       cách viết ấy biến mất, trong khi mệnh đề thật vẫn nguyên.

    ⭐ Bản này đo **thứ thật**: chạy handler, rồi so model trong báo cáo với
       model mà bộ điều phối **thực sự nhận được**. Nó đỏ đúng lúc phải đỏ —
       khi hai bên lệch nhau — dù mã được viết theo kiểu gì.
    """
    from apps.thumbnail import jobs
    from platform_core.storage import LocalStorage, set_storage
    from tests.gia_dieu_phoi_anh import tiem

    set_storage(LocalStorage(str(tmp_path / "st")))
    try:
        gia = tiem(monkeypatch, jobs)
        ra = jobs.handle({"topic": "x", "owner_id": "u1", "count": 2},
                         type("C", (), {"job_id": "j1",
                                        "progress": lambda *a, **k: None})())
    finally:
        set_storage(None)

    bao = ra[costing.KHOA_GOI_PROVIDER]
    assert bao == [{"model": gia.da_goi[0]["model"], "count": 2}], (
        "bao cao chi phi phai khop model that su gui di")


def test_KHOA_GOI_PROVIDER_khong_lo_ra_hop_dong_cong_khai():
    """Tầng API chỉ trả những trường `returns` khai. Nếu một ngày ai đó khai
    `provider_calls` vào `returns` thì **model id nội bộ ra thẳng cho khách**."""
    from platform_core.registry import discover

    for app in discover():
        if app.error:
            continue
        for tool in (app.manifest.tools or []):
            assert costing.KHOA_GOI_PROVIDER not in (tool.returns or {}), (
                f"{app.slug}/{tool.name} khai {costing.KHOA_GOI_PROVIDER} vao returns "
                "— model id noi bo se lo ra khach")
