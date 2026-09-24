"""asv-final L_NO_KY_THUAT F-09 — SQUIM (`torchaudio.pipelines.SQUIM_OBJECTIVE`)
mang trọng số CC BY 4.0, giấy phép BẮT BUỘC ghi công. Trang `/ghi-cong-ben-thu-ba`
phải liệt kê MỌI dòng của `THIRD_PARTY_METRICS.md` §1 cần ghi công — sinh từ
`platform_core.third_party_notices`, không phải một bảng gõ tay có thể lệch.
"""
from __future__ import annotations

import pathlib
import textwrap

import pytest
from fastapi.testclient import TestClient

from platform_core import third_party_notices as tpn

GOC = pathlib.Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════════════════════════════════════
#  platform_core.third_party_notices — bộ đọc
# ══════════════════════════════════════════════════════════════════════════

def test_doc_duoc_bang_muc1_that_va_thay_squim():
    """Tệp thật `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md` phải đọc
    được và mang đúng dòng SQUIM_OBJECTIVE (không phải test giả trên dữ liệu
    dựng)."""
    hang = tpn.doc_bang_muc1()
    assert hang, "khong doc duoc bang §1 tu THIRD_PARTY_METRICS.md that"
    squim = [d for d in hang if "SQUIM" in d["repo_goi"] or "squim" in d["model_checkpoint"]]
    assert len(squim) == 1, hang
    assert "CC BY 4.0" in squim[0]["license_weights"]


def test_can_ghi_cong_bat_CC_BY_bo_qua_giay_phep_khac():
    assert tpn.can_ghi_cong({"license_ma": "MIT", "license_weights": "MIT"}) is False
    assert tpn.can_ghi_cong({"license_ma": "Apache-2.0", "license_weights": "Apache-2.0"}) is False
    assert tpn.can_ghi_cong({"license_ma": "BSD-2-Clause", "license_weights": "**CC BY 4.0** (ghi công)"}) is True
    assert tpn.can_ghi_cong({"license_ma": "CC BY-SA 4.0", "license_weights": "—"}) is True


def test_muc_ghi_cong_chi_lay_dong_can_ghi_cong():
    """Đúng như bản khai (đo thủ công ở THIRD_PARTY_METRICS.md §1): trong 7
    dòng runtime hiện tại, DUY NHẤT SQUIM cần ghi công (VMAF/PySceneDetect/
    jiwer/faster-whisper/MetricX/OCR không mang giấy phép CC BY)."""
    hang = tpn.doc_bang_muc1()
    mc = tpn.muc_ghi_cong()
    assert 0 < len(mc) < len(hang)
    assert all(tpn.can_ghi_cong(d) for d in mc)


def test_khong_co_tep_nguon_tra_ve_rong_khong_nem_loi(tmp_path):
    trong = tmp_path / "khong-ton-tai.md"
    assert tpn.doc_bang_muc1(trong) == []
    assert tpn.muc_ghi_cong(trong) == []


def test_doc_bang_tu_tep_dung_gia_lap_dung_khuon():
    tep = pathlib.Path(__file__).resolve().parent / "_data_2131_third_party_metrics.md"
    tep.write_text(textwrap.dedent("""\
        # THIRD_PARTY_METRICS — bản khai giấy phép bên thứ ba

        ## §1. Đang dùng trong runtime

        | # | Dùng để | Repo / gói | Phiên bản (tag/commit) | Model / checkpoint | License mã | License weights | Thương mại | Phân phối lại | Nguồn tải | Checksum | Làn |
        |---|---|---|---|---|---|---|---|---|---|---|---|
        | 1 | Việc A | pkg/a | 1.0 | — | MIT | — | ✅ | ✅ | PyPI | — | x |
        | 2 | Việc B | pkg/b | 2.0 | model-b | BSD | **CC BY 4.0** | ✅ | ✅ kèm ghi công | HF | — | y |

        ## §2. ĐÃ LOẠI

        | Ứng viên | Lý do loại | Nguồn |
        |---|---|---|
        | X | ly do | nguon |
        """), encoding="utf-8", newline="\n")
    try:
        hang = tpn.doc_bang_muc1(tep)
        assert len(hang) == 2
        mc = tpn.muc_ghi_cong(tep)
        assert len(mc) == 1
        assert mc[0]["dung_de"] == "Việc B"
        # §2 (đã loại) khong duoc lan vao — chi 2 dong cua §1 duoc doc.
        assert all(d["dung_de"] in ("Việc A", "Việc B") for d in hang)
    finally:
        tep.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════
#  Trang /ghi-cong-ben-thu-ba — mọi dòng cần ghi công phải LÊN MẶT trang
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ghicong.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "ghicong-secret-value")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    from platform_core.public_api import limits
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        limits.reset()
        dbmod.reset_engine()


def test_trang_mo_duoc_khi_chua_dang_nhap(client):
    r = client.get("/ghi-cong-ben-thu-ba", follow_redirects=False)
    assert r.status_code == 200, r.text[:400]


def test_moi_dong_can_ghi_cong_xuat_hien_tren_trang(client):
    """Phép chốt CHÍNH của F-09: với MỌI dòng `THIRD_PARTY_METRICS.md` §1 mà
    `can_ghi_cong()` xác nhận (hiện: SQUIM_OBJECTIVE), một chuỗi định danh của
    dòng đó (tên gói/repo, hoặc checkpoint nếu có) phải có mặt trong HTML của
    trang — không phải suy luận gián tiếp qua số dòng."""
    mc = tpn.muc_ghi_cong()
    assert mc, "khong co du lieu that de kiem — THIRD_PARTY_METRICS.md thay doi?"
    html = client.get("/ghi-cong-ben-thu-ba").text
    for dong in mc:
        dinh_danh = dong["model_checkpoint"] if dong["model_checkpoint"] not in ("", "—") \
            else dong["repo_goi"]
        # Bỏ dấu backtick/markdown khỏi chuỗi định danh trước khi so trong HTML.
        dinh_danh_sach = dinh_danh.strip("`")
        assert dinh_danh_sach in html, \
            f"dong {dong['so']} ({dong['dung_de']}) khong xuat hien tren trang"
        assert "CC BY" in html


def test_dong_khong_can_ghi_cong_khong_bi_nhet_vao(client):
    """VMAF/PySceneDetect/jiwer/faster-whisper (MIT/Apache/BSD, không CC BY)
    không được liệt kê trên trang — trang chỉ nói đúng nghĩa vụ thật."""
    hang = tpn.doc_bang_muc1()
    mc_so = {d["so"] for d in tpn.muc_ghi_cong()}
    khong_can = [d for d in hang if d["so"] not in mc_so]
    assert khong_can, "moi dong deu can ghi cong? kiem lai du lieu that"
    html = client.get("/ghi-cong-ben-thu-ba").text
    for dong in khong_can:
        dinh_danh = dong["model_checkpoint"] if dong["model_checkpoint"] not in ("", "—") \
            else dong["repo_goi"]
        assert dinh_danh.strip("`") not in html, \
            f"dong {dong['so']} khong can ghi cong nhung van len trang"
