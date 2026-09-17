"""`/lttcode` là trang CÔNG KHAI: giới thiệu + hướng dẫn + tải (spec 17/09).

Chốt ở đây:

1. Mở được khi chưa đăng nhập; có đủ các neo mà ứng dụng desktop mở thẳng tới
   (menu Trợ giúp › Hướng dẫn mở `/lttcode#bat-dau`).
2. Nút tải chỉ phát kênh `stable`: có bản ⇒ nút + phiên bản + SHA-256 (+ dung
   lượng khi có tệp); kênh trống ⇒ "Sắp phát hành", không nút; bản chỉ có ở kênh
   `dev` không bao giờ lộ ra trang.
3. `/en/lttcode` là tiếng Anh ở các tiêu đề; giá trỏ `/gia-api` qua `u()`, không
   chép số; không có ảnh ngoài (ảnh chụp thật lộ tên máy/đường dẫn).
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

import apps.lttcode.routes  # noqa: F401  (gắn test vào thành phần app:lttcode)

NEO = ("tai", "tinh-nang", "bat-dau", "an-toan", "chi-phi", "cap-nhat", "su-co")
TEP = "LTTCODE_0.2.0_x64-setup.exe"
SHA = "ab" * 32
VN = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.I)


@pytest.fixture()
def may(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'lc.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(data))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "lttcode-test-secret")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client, data
    finally:
        dbmod.reset_engine()


def _ban(version: str, file: str) -> dict:
    return {"version": version, "pub_date": "2026-09-20T10:00:00Z", "file": file,
            "signature": "sig", "sha256": SHA, "notes": "", "rollout_percent": 100,
            "session_format": 3, "revoked": False}


def _ghi(data, **kenh: list[dict]) -> None:
    channels = {ten: {"kill_switch": False, "min_version": "0.0.0", "releases": ds}
                for ten, ds in kenh.items()}
    (data / "lttcode_releases.json").write_text(json.dumps({"channels": channels}), encoding="utf-8")


def _tieu_de(html: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", m).strip()
            for m in re.findall(r"<h[123][^>]*>(.*?)</h[123]>", html, re.S)]


def test_mo_duoc_khi_chua_dang_nhap_va_du_neo(may):
    client, _ = may
    r = client.get("/lttcode", follow_redirects=False)
    assert r.status_code == 200, r.text[:400]
    for neo in NEO:
        assert f'id="{neo}"' in r.text, f"thiếu neo #{neo}"
    assert 'class="lc-end"' in r.text


def test_co_ban_stable_thi_hien_nut_phien_ban_sha_va_dung_luong(may):
    client, data = may
    _ghi(data, stable=[_ban("0.2.0", TEP)])
    dist = data / "lttcode_dist"
    dist.mkdir()
    (dist / TEP).write_bytes(b"\0" * (3 * 1024 * 1024 + 512 * 1024))

    html = client.get("/lttcode").text
    assert f'href="/lttcode/dl/{TEP}"' in html
    assert "Tải cho Windows" in html
    assert "0.2.0" in html and SHA in html
    assert "3.5 MB" in html
    assert "Sắp phát hành" not in html


def test_thieu_tep_bo_cai_thi_khong_hien_dung_luong(may):
    client, data = may
    _ghi(data, stable=[_ban("0.2.0", TEP)])
    html = client.get("/lttcode").text
    assert f"/lttcode/dl/{TEP}" in html
    assert not re.search(r"\d MB", html)


def test_kenh_stable_trong_thi_sap_phat_hanh_khong_nut(may):
    client, data = may
    _ghi(data, stable=[])
    html = client.get("/lttcode").text
    assert "Sắp phát hành" in html
    assert "/lttcode/dl/" not in html


def test_ban_chi_co_o_kenh_dev_khong_lo_ra_trang(may):
    client, data = may
    _ghi(data, stable=[], dev=[_ban("0.9.0", "LTTCODE_0.9.0_x64-setup.exe")])
    html = client.get("/lttcode").text
    assert "0.9.0" not in html
    assert "/lttcode/dl/" not in html
    assert "Sắp phát hành" in html


def test_ban_tieng_anh_co_tieu_de_tieng_anh(may):
    client, data = may
    _ghi(data, stable=[_ban("0.2.0", TEP)])
    r = client.get("/en/lttcode")
    assert r.status_code == 200, r.text[:400]
    tieu_de = _tieu_de(r.text)
    assert "Troubleshooting" in tieu_de and "Four steps to get started" in tieu_de
    con_tieng_viet = [t for t in tieu_de if VN.search(t)]
    assert con_tieng_viet == [], con_tieng_viet
    # Link nội bộ mang tiền tố ngôn ngữ (đi qua `u()`).
    assert 'href="/en/gia-api"' in r.text
    assert f'href="/en/lttcode/dl/{TEP}"' in r.text


FAQ_CONG_CU = ("faq-mcp", "faq-plugin", "faq-hooks", "faq-terminal", "faq-lich-hen",
               "faq-skill", "faq-song-song", "faq-sao-luu")


def _muc_su_co(html: str) -> str:
    return html.split('id="su-co"', 1)[1].split('class="lc-end"', 1)[0]


def test_faq_cong_cu_mo_rong_hien_trong_muc_su_co(may):
    """FAQ 0.1.5 (G7): mỗi mục là <details> có <summary> trong #su-co, id `faq-*` ổn định,
    và các cam kết rủi ro/giới hạn đã đối chiếu LTTCODEAPP không bị rơi khi sửa chữ."""
    client, _ = may
    html = client.get("/lttcode").text
    su_co = _muc_su_co(html)
    for neo in FAQ_CONG_CU:
        m = re.search(rf'<details id="{neo}">\s*<summary>[^<]+</summary>', su_co)
        assert m, f"thiếu mục FAQ #{neo}"
    for chu in ("Upstash", "8 công cụ đọc", "Node.js và pnpm", "đọc được khoá LTT",
                "hooks.json", "7 sự kiện", "mã 2", "pwsh", "phiên đang mở",
                "playwright-cli", "tối đa 3 yêu cầu", "tối đa 2 agent con", "LTT-3.8",
                r"dsh-home\backups", "Chỉ giữ một bản sao lưu"):
        assert chu in su_co, f"FAQ thiếu: {chu}"
    # Mục an toàn không còn nói "chỉ LTT" mà giấu context7.
    an_toan = html.split('id="an-toan"', 1)[1].split('id="chi-phi"', 1)[0]
    assert "context7" in an_toan and "Upstash" in an_toan


def test_faq_cong_cu_ban_tieng_anh_da_dich(may):
    client, _ = may
    su_co = _muc_su_co(client.get("/en/lttcode").text)
    assert "Extension tools (since 0.1.5)" in su_co
    tom_tat = re.findall(r"<summary>([^<]+)</summary>", su_co)
    assert len(tom_tat) >= 5 + len(FAQ_CONG_CU)
    con_tieng_viet = [t for t in tom_tat if VN.search(t)]
    assert con_tieng_viet == [], con_tieng_viet
    assert "Upstash" in su_co and "LTT-3.8" in su_co


def test_chi_phi_tro_trang_gia_va_khong_anh_ngoai(may):
    client, _ = may
    html = client.get("/lttcode").text
    assert 'href="/gia-api"' in html
    assert not re.search(r"<img[^>]+src=[\"']?(https?:)?//", html), "ảnh ngoài trên trang"
    assert "<img" not in html.split('<div class="lc">', 1)[1].split('class="lc-end"', 1)[0]
