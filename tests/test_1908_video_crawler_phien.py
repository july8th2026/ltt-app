"""
video_crawler — phiên đăng nhập nền tảng theo từng người dùng (spec §16, đợt B0).

Donor: profile Chromium CHUNG máy cho mọi người (`W:113-117`), kiểm đăng nhập bằng tên cookie xác thực `COOKIE_AUTH`
(`W:17772-17796`). LTT: khách tự nhập cookies.txt (Netscape) của CHÍNH họ; lưu mã hoá (secretbox), cô lập theo
(owner, nền); không bao giờ ra log/params/result/URL/giao diện dạng rõ.

Mệnh đề chốt:
- chỉ giữ cookie thuộc tên miền của nền (dán nhầm cả trình duyệt không kéo theo cookie ngân hàng);
- thiếu cookie xác thực của nền ⇒ từ chối có tên (donor: coi là "chưa đăng nhập");
- giá trị cookie không xuất hiện dạng rõ trong bất kỳ hàng DB nào;
- user khác không đọc được phiên của mình; xoá được;
- worker nhận TỆP cookie tạm, không nhận chuỗi cookie trong params.
"""
from __future__ import annotations

import pytest

_BI_MAT = "SESSDATA-bi-mat-0123456789abcdef"


def _cookies_txt(*dong):
    return "# Netscape HTTP Cookie File\n" + "\n".join(dong) + "\n"


_TIKTOK = _cookies_txt(
    f".tiktok.com\tTRUE\t/\tTRUE\t1893456000\tsessionid\t{_BI_MAT}",
    ".tiktok.com\tTRUE\t/\tFALSE\t1893456000\ttt_csrf_token\tabc",
    ".mybank.example\tTRUE\t/\tTRUE\t1893456000\tBANK_SESSION\tkhong-duoc-luu",
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-video-crawler")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def test_luu_chi_giu_cookie_cua_nen_va_ma_hoa(db):
    from sqlalchemy import text

    from apps.video_crawler import phien
    tt = phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt=_TIKTOK)
    db.commit()
    assert tt.so_cookie == 2                                   # cookie ngân hàng bị bỏ
    blob = " ".join(str(r) for r in db.execute(text("select * from vc_phien")).all())
    assert _BI_MAT not in blob and "khong-duoc-luu" not in blob
    ro = phien.cookies_txt_cua(db, owner_id="u1", nen_tang="tiktok")
    assert _BI_MAT in ro and "BANK_SESSION" not in ro


def test_thieu_cookie_xac_thuc_bi_tu_choi_co_ten(db):
    from apps.video_crawler import phien
    with pytest.raises(phien.PhienKhongHopLe, match="đăng nhập"):
        phien.luu(db, owner_id="u1", nen_tang="tiktok",
                  cookies_txt=_cookies_txt(".tiktok.com\tTRUE\t/\tFALSE\t1893456000\ttt_csrf_token\tabc"))


def test_noi_dung_khong_phai_cookies_txt_bi_tu_choi(db):
    from apps.video_crawler import phien
    with pytest.raises(phien.PhienKhongHopLe):
        phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt="xin chao")


def test_cach_ly_theo_nguoi_dung_va_xoa_duoc(db):
    from apps.video_crawler import phien
    phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt=_TIKTOK)
    db.commit()
    assert phien.cookies_txt_cua(db, owner_id="u2", nen_tang="tiktok") is None
    assert [p.nen_tang for p in phien.danh_sach(db, "u1")] == ["tiktok"]
    assert phien.danh_sach(db, "u2") == []
    assert phien.xoa(db, owner_id="u2", nen_tang="tiktok") is False
    assert phien.xoa(db, owner_id="u1", nen_tang="tiktok") is True
    db.commit()
    assert phien.cookies_txt_cua(db, owner_id="u1", nen_tang="tiktok") is None


def test_luu_lai_thi_thay_phien_cu(db):
    from apps.video_crawler import phien
    phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt=_TIKTOK)
    moi = _TIKTOK.replace(_BI_MAT, "SESSDATA-moi-9999999999999999")
    phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt=moi)
    db.commit()
    assert len(phien.danh_sach(db, "u1")) == 1
    assert "SESSDATA-moi" in phien.cookies_txt_cua(db, owner_id="u1", nen_tang="tiktok")


def test_tep_cookie_tam_nam_trong_thu_muc_job_va_bi_xoa(db, tmp_path):
    from apps.video_crawler import phien
    phien.luu(db, owner_id="u1", nen_tang="tiktok", cookies_txt=_TIKTOK)
    db.commit()
    with phien.tep_cookie_tam(db, owner_id="u1", nen_tang="tiktok", thu_muc=tmp_path) as duong:
        assert duong is not None and duong.parent == tmp_path
        assert _BI_MAT in duong.read_text(encoding="utf-8")
    assert not duong.exists()
    with phien.tep_cookie_tam(db, owner_id="u2", nen_tang="tiktok", thu_muc=tmp_path) as duong2:
        assert duong2 is None


def test_bang_phien_co_hang_quan_tri_du_lieu():
    """Bảng mới chứa dữ liệu khách ⇒ phải khai ở `governance.STORES` (test_211). Đây là thay đổi platform_core
    DUY NHẤT của đợt B0, có chủ đích: một hàng khai báo, không đổi hành vi nền tảng."""
    from platform_core.public_api import governance
    hang = [s for s in governance.STORES if s.table == "vc_phien"]
    assert len(hang) == 1 and hang[0].klass == governance.CONTENT
