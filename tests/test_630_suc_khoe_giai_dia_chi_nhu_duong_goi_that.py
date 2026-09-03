"""
test_630 — Hook `suc_khoe` phải giải địa chỉ cổng theo **đúng thứ tự** mà đường
gọi thật dùng. (H43 Phase 12, tìm ra bằng phép đo LIVE 03/09)

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Bản đầu của `ltt_llm.features.suc_khoe` chỉ đọc
   `providers.get(...).base_url` (biến môi trường). Nhưng `luong_vlm.mo` —
   đường gọi THẬT — lấy `base_url` của **khoá** trước, rồi mới đến registry
   (`luong_vlm.py:136-137`), và đó là cách production được cấu hình.

   Đo LIVE 03/09: `GET http://192.168.2.66:8299/live` trả **200**, tức cổng máy
   B đang sống, nhưng hook trả `chua_san_sang`.

⛔ Một chip "chưa sẵn sàng" SAI làm ô soạn bị tắt cho **mọi** người trong khi
   model chạy tốt. Nó là mặt kia của đúng cái lỗi Phase 06 sinh ra để chặn (chip
   xanh nói dối) — chỉ khác chiều, và chiều này mất cả sản phẩm chứ không chỉ
   làm người dùng bực mình.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "h.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _khoa(db, *, provider="ltt_llm", base_url="http://may-b.noi-bo:8299"):
    from platform_core.models import ApiKey

    k = ApiKey(provider=provider, categories="chat", base_url=base_url,
               name="khoa thu", credential_enc="x", status="active")
    db.add(k)
    db.commit()
    return k


def test_lay_base_url_cua_KHOA_khi_registry_rong(db, monkeypatch):
    from apps.ltt_llm import features

    monkeypatch.setattr("platform_core.providers.get",
                        lambda _p: type("P", (), {"base_url": ""})())
    assert features._dia_chi_cong() == ""          # chưa có khoá ⇒ rỗng, fail-closed
    _khoa(db)
    assert features._dia_chi_cong() == "http://may-b.noi-bo:8299"


def test_registry_thang_khoa_khi_ca_hai_deu_co(db, monkeypatch):
    """Cùng thứ tự `luong_vlm.mo` dùng? KHÔNG — và đó là chủ đích.

    `luong_vlm` ưu tiên khoá vì nó **đã** cầm đúng khoá sẽ gọi. Hook sức khoẻ
    không chọn khoá; nó chỉ cần biết cổng nào đang phục vụ. Registry (biến môi
    trường của tiến trình) là thứ người vận hành đặt và sửa được ngay, nên khi
    có nó thì nó thắng — một cách để chuyển hướng thăm dò mà không sửa CSDL.
    """
    from apps.ltt_llm import features

    monkeypatch.setattr("platform_core.providers.get",
                        lambda _p: type("P", (), {"base_url": "http://tu-env:9999"})())
    _khoa(db, base_url="http://tu-khoa:8299")
    assert features._dia_chi_cong() == "http://tu-env:9999"


def test_khoa_cua_provider_KHAC_khong_duoc_dung(db, monkeypatch):
    from apps.ltt_llm import features

    monkeypatch.setattr("platform_core.providers.get",
                        lambda _p: type("P", (), {"base_url": ""})())
    _khoa(db, provider="gemini", base_url="http://nham-provider:1234")
    assert features._dia_chi_cong() == ""


def test_khong_co_CSDL_thi_tra_rong_chu_khong_nem(monkeypatch):
    """Hook chạy ở mọi tiến trình, kể cả nơi chưa cấu hình CSDL.

    ⛔ ĐỪNG `importlib.reload(platform_core.db)` để dọn dẹp ở đây. Bản đầu của
       phép kiểm này làm đúng thế, và nó **phá mọi tệp test chạy sau nó trong
       cùng tiến trình**: `reload` dựng một lớp `Base` MỚI mang một
       `MetaData` RỖNG, nên `Base.metadata.create_all()` của tệp sau tạo
       **không bảng nào** — im lặng — rồi test đó chết với
       `no such table: users` ở một chỗ chẳng liên quan gì.

       Giá đo được: 16 phép kiểm đỏ rải trên sáu tệp (112, 122, 157, 172, 220,
       305, 606), tất cả đều XANH khi chạy một mình, và gần một giờ đuổi theo
       một giả thuyết sai (“máy quá tải”). Xem `docs/CHATLTT/reports/12_torture.md`.

    ⭐ Không cần dọn gì cả: `monkeypatch` trả `LTT_DATABASE_URL` về chỗ cũ khi
       test kết thúc, và `reset_engine()` để lần `get_engine()` sau dựng lại
       từ biến môi trường đã được trả. Trạng thái duy nhất cần đặt lại là
       engine — không phải cả module.
    """
    import platform_core.db as dbmod
    from apps.ltt_llm import features

    monkeypatch.delenv("LTT_DATABASE_URL", raising=False)
    dbmod.reset_engine()
    monkeypatch.setattr("platform_core.providers.get",
                        lambda _p: type("P", (), {"base_url": ""})())
    assert features._dia_chi_cong() == ""
    assert features.suc_khoe(timeout_s=0.2) == "chua_san_sang"
    dbmod.reset_engine()


def test_cong_tra_khac_200_thi_chua_san_sang(db, monkeypatch):
    import httpx

    from apps.ltt_llm import features

    monkeypatch.setattr("platform_core.providers.get",
                        lambda _p: type("P", (), {"base_url": "http://x:1"})())
    for ma in (500, 503, 404):
        monkeypatch.setattr(httpx, "get",
                            lambda *a, ma=ma, **k: type("R", (), {"status_code": ma})())
        assert features.suc_khoe(timeout_s=0.2) == "chua_san_sang", ma
    monkeypatch.setattr(httpx, "get",
                        lambda *a, **k: type("R", (), {"status_code": 200})())
    assert features.suc_khoe(timeout_s=0.2) == "san_sang"

    def no(*_a, **_k):
        raise httpx.ConnectError("khong noi duoc")

    monkeypatch.setattr(httpx, "get", no)
    assert features.suc_khoe(timeout_s=0.2) == "chua_san_sang"


def test_anhnoibo_giai_dia_chi_dung_nhu_duong_goi_that(monkeypatch):
    """`anhnoibo` gọi qua `providers.get("ltt_image").base_url` (biến môi trường),
    nên hook của nó đọc **cùng một chỗ** — không thêm đường thứ hai."""
    import inspect

    from apps.anhnoibo import features as anh, jobs

    nguon_hook = inspect.getsource(anh.suc_khoe)
    nguon_that = inspect.getsource(jobs._dieu_phoi)
    assert 'providers.get("ltt_image")' in nguon_hook
    assert 'providers.get("ltt_image")' in nguon_that
