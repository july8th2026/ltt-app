"""
test_274_gia_cong_khai — bảng giá API phải xem được KHI CHƯA đăng nhập. (H38, B1)

🔴 VÌ SAO. Trang giá đang có (`/developers/pricing`) nằm sau `require_account`:
   muốn biết giá thì phải đăng ký trước. Đó là thứ tự ngược, và nó chặn đúng
   người ta cần nhất — người đang **cân nhắc**. Không ai đăng ký một dịch vụ
   tính tiền để xem nó tính bao nhiêu.

⛔ Và số phải đến từ `gia_token`, không gõ lại vào template. Gõ lại là tạo ra
   một bảng giá thứ hai, và ngày hai bảng lệch nhau thì bảng nào cũng không
   đáng tin.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "g.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "gia-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    dbmod.reset_engine()


def test_xem_duoc_KHI_CHUA_dang_nhap(web):
    """Vế ① của định nghĩa "dứt điểm": người lạ tìm được giá."""
    r = web.get("/gia-api", follow_redirects=False)
    assert r.status_code == 200, f"bi chuyen huong toi {r.headers.get('location')}"


def test_so_den_tu_gia_token_khong_go_lai(web):
    from platform_core.llm import gia_token

    page = web.get("/gia-api").text
    b = gia_token.bang_gia()
    for ten in ("token_vao", "token_vao_cache", "token_ra"):
        assert str(b[ten]) in page, f"thieu gia {ten}"
    assert b["phien_ban_gia"] in page, "thieu phien ban gia"


def test_co_vi_du_chi_phi_that(web):
    """Một con số trừu tượng không nói cho ai biết một lượt chat tốn bao nhiêu."""
    page = web.get("/gia-api").text
    assert "2,000" in page or "2.000" in page, "thieu vi du luot viet ma"
    assert "22,000" in page or "22.000" in page, "thieu vi du luot agent"


def test_noi_ro_BA_LUAT_tinh_tien_de_gay_hieu_lam(web):
    """Ba điều khách hay hiểu nhầm, và mỗi cái đều là một khiếu nại nếu không nói."""
    page = web.get("/gia-api").text
    assert "max_tokens" in page, "chua noi 'tra cho thu da sinh, khong phai thu da xin'"
    assert "streaming" in page.lower(), "chua noi ngat giua chung van tinh tien"
    assert "0 đồng" in page or "0 dong" in page, "chua noi khong do duoc thi khong thu"


def test_chi_duong_dang_ky(web):
    page = web.get("/gia-api").text
    for d in ("/register", "/developers/keys", "/developers/cli"):
        assert d in page, f"thieu duong dan {d}"


def test_KHONG_lo_id_noi_bo(web):
    """Lớp đệm alias phải đứng ở cả trang bán hàng."""
    assert "qwen38" not in web.get("/gia-api").text


# ── Giá ảnh model nhà (H37/L4) ───────────────────────────────────────────────
#
# Cùng lý do như phần LLM ở trên: trước H37/L4, `CREDIT_MOI_ANH = 5` chỉ nằm
# trong `apps/anhnoibo/manifest.py`. Không phiên bản, không bảng giá công bố.
# Khách không có cách nào biết giá ảnh trước khi đăng ký.

def test_gia_anh_cung_len_trang_cong_khai(web):
    from apps.anhnoibo import gia as gia_anh

    page = web.get("/gia-api").text
    b = gia_anh.bang_gia()
    assert str(b["anh_thuong"]) in page
    assert str(b["anh_tham_chieu"]) in page
    assert b["phien_ban_gia"] in page, "thieu phien ban gia anh"


def test_gia_anh_noi_ro_chi_tinh_anh_that(web):
    """Đây là luật dễ gây khiếu nại nhất của đường ảnh — phải nói ra."""
    page = web.get("/gia-api").text
    assert "hoàn" in page, "chua noi phan giu du duoc hoan lai"


def test_trang_gia_KHONG_lo_ten_model_anh_noi_bo(web):
    """Cùng lớp đệm alias như `qwen38` ở trên."""
    assert "hidream" not in web.get("/gia-api").text.lower()
