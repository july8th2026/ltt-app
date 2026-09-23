"""
video_crawler — KHO TÀI KHOẢN HỆ THỐNG (W4-L9; chủ dự án duyệt 23/09/2026).

Khách thường KHÔNG có cookies.txt, nên sáu nền cần phiên gần như chết về mặt sản phẩm
(`docs/migrations/video_crawler/THIET_KE_PHIEN_VA_KENH.md` §1). Phương án C: admin nạp vài tài khoản
PHỤ vào kho; job của khách dùng phiên RIÊNG nếu có, không có thì MƯỢN một tài khoản kho — LTT đứng
tên lượt đó. Mệnh đề chốt:

- một tài khoản phục vụ ĐÚNG MỘT job một lúc (`ExecutionLease` `vc_tk:<id>`, UNIQUE của nền tảng);
- hết chỗ ⇒ `jobs.DangBan` (về hàng đợi, không tiêu lượt, không chạm tiền); không còn tài khoản sống
  ⇒ `LoiNguoiGoi` (không thử lại, hoàn tiền) với câu cho khách;
- trần lượt/giờ + nghỉ tối thiểu theo TỪNG tài khoản; trần video/giờ theo TỪNG khách khi dùng kho;
- chấm điểm kiểu proxy_pool (NC §2): thành công +1, lỗi nặng trừ nặng, **lỗi mạng không loại tài khoản**;
- cô lập: cookie kho và id tài khoản không bao giờ ra `params`/`result`/log/URL — id chỉ ở sự kiện INTERNAL.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_BI_MAT = "sessionid-kho-LTT-0123456789abcdef"
_BI_MAT_2 = "sessionid-kho-LTT-tai-khoan-hai-xyz"


def _cookies_txt(bi_mat: str = _BI_MAT, het_han: int = 1893456000) -> str:
    return ("# Netscape HTTP Cookie File\n"
            f".douyin.com\tTRUE\t/\tTRUE\t{het_han}\tsessionid\t{bi_mat}\n"
            ".douyin.com\tTRUE\t/\tFALSE\t1893456000\tttwid\tcong-khai\n"
            ".mybank.example\tTRUE\t/\tTRUE\t1893456000\tBANK\tkhong-duoc-luu\n")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'k.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-kho-tai-khoan")
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


@pytest.fixture()
def kho_tep(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store"))
    set_storage(st)
    try:
        yield st
    finally:
        set_storage(None)


def _them(db, nhan="phu-1", bi_mat=_BI_MAT, nen="douyin", **kw):
    from apps.video_crawler import kho_tai_khoan
    tk = kho_tai_khoan.them(db, nen_tang=nen, nhan=nhan, cookies_txt=_cookies_txt(bi_mat), **kw)
    db.commit()
    return tk


def _bay_gio(phut: float = 0.0) -> datetime:
    return datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=phut)


# ── Nạp tài khoản vào kho ─────────────────────────────────────────────────────

def test_them_chi_giu_cookie_cua_nen_va_ma_hoa(db):
    from sqlalchemy import text

    from apps.video_crawler import kho_tai_khoan
    tk = _them(db)
    assert tk.trang_thai == kho_tai_khoan.SONG and tk.nhan == "phu-1"
    blob = " ".join(str(r) for r in db.execute(text("select * from vc_tai_khoan")).all())
    assert _BI_MAT not in blob and "khong-duoc-luu" not in blob
    ro = kho_tai_khoan.cookies_txt_cua(db, tk.id)
    assert _BI_MAT in ro and "BANK" not in ro
    assert tk.han == datetime.fromtimestamp(1893456000, tz=timezone.utc)


def test_them_tu_choi_cookie_chua_dang_nhap(db):
    from apps.video_crawler import kho_tai_khoan, phien
    with pytest.raises(phien.PhienKhongHopLe):
        kho_tai_khoan.them(db, nen_tang="douyin", nhan="x",
                           cookies_txt="# Netscape HTTP Cookie File\n.douyin.com\tTRUE\t/\tFALSE\t0\tttwid\ta\n")


def test_them_tu_choi_nen_ngoai_dot_dau(db):
    """Đợt đầu chỉ douyin/xiaohongshu/tiktok — KHÔNG bilibili (tiền lệ pháp lý NC §0)."""
    from apps.video_crawler import kho_tai_khoan
    assert not kho_tai_khoan.nen_co_kho("bilibili")
    with pytest.raises(kho_tai_khoan.KhoKhongHopLe):
        kho_tai_khoan.them(db, nen_tang="bilibili", nhan="x", cookies_txt=_cookies_txt())


# ── Mượn / trả chỗ ────────────────────────────────────────────────────────────

def test_mot_tai_khoan_phuc_vu_mot_job_mot_luc(db):
    from apps.video_crawler import kho_tai_khoan
    a, b = _them(db, "phu-1"), _them(db, "phu-2", _BI_MAT_2)
    m1 = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    m2 = kho_tai_khoan.muon(db, "douyin", owner_id="u2", job_id="j2", bay_gio=_bay_gio())
    assert m1 is not None and m2 is not None
    assert {m1.tai_khoan_id, m2.tai_khoan_id} == {a.id, b.id}      # không job nào dùng chung tài khoản
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u3", job_id="j3", bay_gio=_bay_gio()) is None
    assert kho_tai_khoan.con_tai_khoan_song(db, "douyin") is True   # hết CHỖ, không phải hết tài khoản
    kho_tai_khoan.tra(db, m1, bay_gio=_bay_gio())
    m3 = kho_tai_khoan.muon(db, "douyin", owner_id="u3", job_id="j3", bay_gio=_bay_gio(1))
    assert m3 is not None and m3.tai_khoan_id == m1.tai_khoan_id


def test_lease_cua_job_da_chet_duoc_thu_hoi(db):
    """Worker bị giết ⇒ không ai trả chỗ. Lease trỏ về một job KHÔNG còn chạy ⇒ thu hồi ngay."""
    from apps.video_crawler import kho_tai_khoan
    from platform_core.models import JOB_ERROR, Job
    from tests.conftest import bao_dam_user
    bao_dam_user(db, "u1")
    job = Job(id="j-chet", user_id="u1", app_slug="video_crawler", job_type="video_crawler.tai",
              params={}, status=JOB_ERROR)
    db.add(job); db.commit()
    _them(db, "phu-1")
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j-chet", bay_gio=_bay_gio()) is not None
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u2", job_id="j2", bay_gio=_bay_gio(1))
    assert m is not None                                     # chỗ của job chết được nhận lại


def test_nhip_tim_giu_cho_qua_vong_don_lease_mo_coi(db):
    """Vòng bảo trì gọi `admission.reclaim_expired(db)` KHÔNG lọc tài nguyên, hạn chung 20 phút.

    Job tải chạy được 40 phút mà chỗ không đập nhịp ⇒ vòng ấy xoá chỗ giữa chừng ⇒ job thứ hai mượn đúng
    tài khoản đang tải: hai tiến trình trên một tài khoản, đúng đường dẫn tới challenge mà NC §2 cảnh báo.
    """
    from apps.video_crawler import kho_tai_khoan
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease
    _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    assert m is not None and m.nhip is not None            # mượn xong là có luồng giữ chỗ

    def _gia_hoa(phut):
        db.get(ExecutionLease, m.lease_id).heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=phut)
        db.commit()

    _gia_hoa(40)
    assert kho_tai_khoan.nhip_mot_lan(m.lease_id) is True
    db.expire_all()
    assert admission.reclaim_expired(db) == 0 and db.get(ExecutionLease, m.lease_id) is not None
    _gia_hoa(40)                                           # nếu KHÔNG đập nhịp
    assert admission.reclaim_expired(db) == 1
    db.commit()
    assert db.get(ExecutionLease, m.lease_id) is None
    kho_tai_khoan.tra(db, m, bay_gio=_bay_gio())           # trả chỗ đã mất vẫn phải êm
    assert m.nhip is None


def test_nghi_toi_thieu_giua_hai_luot_cua_mot_tai_khoan(db):
    from apps.video_crawler import kho_tai_khoan
    _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, bay_gio=_bay_gio())
    ngay_sau = _bay_gio() + timedelta(seconds=kho_tai_khoan.NGHI_GIUA_LUOT_S - 1)
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u2", job_id="j2", bay_gio=ngay_sau) is None
    du_nghi = _bay_gio() + timedelta(seconds=kho_tai_khoan.NGHI_GIUA_LUOT_S + 1)
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u2", job_id="j2", bay_gio=du_nghi) is not None


def test_tran_luot_moi_gio_theo_tai_khoan(db, monkeypatch):
    from apps.video_crawler import kho_tai_khoan
    monkeypatch.setattr(kho_tai_khoan, "TRAN_LUOT_GIO", 2)
    _them(db, "phu-1")
    for i in range(2):
        luc = _bay_gio(i)
        m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id=f"j{i}", bay_gio=luc)
        assert m is not None
        kho_tai_khoan.tra(db, m, bay_gio=luc)
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j9", bay_gio=_bay_gio(2)) is None
    assert kho_tai_khoan.con_tai_khoan_song(db, "douyin") is True
    # Cửa sổ trượt qua một giờ ⇒ đếm lại từ đầu.
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j9", bay_gio=_bay_gio(61)) is not None


def test_tai_khoan_tam_nghi_va_het_han_khong_vao_vong_chon(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    kho_tai_khoan.doi_trang_thai(db, tk.id, kho_tai_khoan.TAM_NGHI)
    db.commit()
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio()) is None
    assert kho_tai_khoan.con_tai_khoan_song(db, "douyin") is False
    kho_tai_khoan.doi_trang_thai(db, tk.id, kho_tai_khoan.SONG)
    db.commit()
    # Cookie đã quá hạn ⇒ tự đánh dấu `het_han`, không đem ra dùng.
    sau_han = datetime.fromtimestamp(1893456000, tz=timezone.utc) + timedelta(days=1)
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=sau_han) is None
    db.expire_all()
    assert db.get(type(tk), tk.id).trang_thai == kho_tai_khoan.HET_HAN


# ── Chấm điểm (NC §2, mô hình proxy_pool) ─────────────────────────────────────

def _diem(db, tk_id):
    from apps.video_crawler.tables import VcTaiKhoan
    db.expire_all()
    return db.get(VcTaiKhoan, tk_id)


def test_thanh_cong_cong_diem_co_tran(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    for i in range(30):
        luc = _bay_gio(i * 61)          # tránh trần lượt/giờ và nghỉ giữa lượt
        m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id=f"j{i}", bay_gio=luc)
        kho_tai_khoan.tra(db, m, bay_gio=luc)
    row = _diem(db, tk.id)
    assert row.diem == kho_tai_khoan.DIEM_TOI_DA and row.trang_thai == kho_tai_khoan.SONG
    assert row.loi_gan_nhat is None and row.dung_gan_nhat is not None


def test_loi_can_dang_nhap_loai_tai_khoan_khoi_vong_chon(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, ma_loi="can_dang_nhap", bay_gio=_bay_gio())
    row = _diem(db, tk.id)
    assert row.trang_thai == kho_tai_khoan.HET_HAN and row.loi_gan_nhat == "can_dang_nhap"
    assert kho_tai_khoan.muon(db, "douyin", owner_id="u2", job_id="j2", bay_gio=_bay_gio(10)) is None
    assert kho_tai_khoan.con_tai_khoan_song(db, "douyin") is False


def test_nen_chan_thi_danh_dau_bi_chan(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, ma_loi="nen_chan", bay_gio=_bay_gio())
    assert _diem(db, tk.id).trang_thai == kho_tai_khoan.BI_CHAN


def test_loi_mang_khong_loai_tai_khoan(db):
    """NC §2: xoá ngay khi thất bại MỘT lần là cách mất sạch pool vì một sự cố mạng thoáng qua."""
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    for i in range(10):
        luc = _bay_gio(i * 61)
        m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id=f"j{i}", bay_gio=luc)
        assert m is not None
        kho_tai_khoan.tra(db, m, ma_loi="mang", bay_gio=luc)
    row = _diem(db, tk.id)
    assert row.trang_thai == kho_tai_khoan.SONG and row.diem == kho_tai_khoan.DIEM_BAN_DAU


def test_loi_cua_video_khong_phai_cua_tai_khoan_thi_khong_tru(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, ma_loi="khong_ton_tai", bay_gio=_bay_gio())
    assert _diem(db, tk.id).diem == kho_tai_khoan.DIEM_BAN_DAU


def test_ma_loi_luu_la_ma_khong_phai_van_ban_tho(db):
    from apps.video_crawler import kho_tai_khoan
    tk = _them(db, "phu-1")
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, ma_loi="ERROR: https://www.douyin.com/video/7 cookie sessionid het han",
                      bay_gio=_bay_gio())
    row = _diem(db, tk.id)
    assert row.loi_gan_nhat == "loi_khac" and "douyin.com" not in (row.loi_gan_nhat or "")


# ── Trần theo khách khi dùng kho ──────────────────────────────────────────────

def _job_tai(db, owner, so_muc, nen="douyin", luc=None, **kw):
    from platform_core.models import Job
    from tests.conftest import bao_dam_user
    bao_dam_user(db, owner)
    job = Job(user_id=owner, app_slug="video_crawler", job_type="video_crawler.tai",
              params={"owner_id": owner, "nen_tang": nen,
                      "muc": [{"id": f"v{i}", "url": "u", "tieu_de": ""} for i in range(so_muc)]},
              created_at=luc or _bay_gio(), **kw)
    db.add(job); db.commit()
    return job


def test_tran_video_moi_gio_theo_khach_qua_kho(db, monkeypatch):
    from apps.video_crawler import kho_tai_khoan
    from platform_core.jobs import LoiNguoiGoi
    monkeypatch.setattr(kho_tai_khoan, "TRAN_KHACH_GIO", 5)
    _job_tai(db, "u1", 5)
    kho_tai_khoan.kiem_tran_khach(db, "u1", "douyin", bay_gio=_bay_gio(1))          # đúng trần: qua
    _job_tai(db, "u1", 1, luc=_bay_gio(1))
    with pytest.raises(LoiNguoiGoi):
        kho_tai_khoan.kiem_tran_khach(db, "u1", "douyin", bay_gio=_bay_gio(2))
    # Khách khác không bị ảnh hưởng; quá một giờ thì hết trần.
    kho_tai_khoan.kiem_tran_khach(db, "u2", "douyin", bay_gio=_bay_gio(2))
    kho_tai_khoan.kiem_tran_khach(db, "u1", "douyin", bay_gio=_bay_gio(70))


def test_tran_khach_chi_dem_luot_QUA_KHO(db, monkeypatch):
    """Khách có phiên RIÊNG cho nền đó thì lượt của họ không tiêu trần kho."""
    from apps.video_crawler import kho_tai_khoan, phien
    monkeypatch.setattr(kho_tai_khoan, "TRAN_KHACH_GIO", 2)
    _job_tai(db, "u1", 9)
    _job_tai(db, "u1", 9, nen="youtube")                    # nền không có kho
    phien.luu(db, owner_id="u1", nen_tang="douyin", cookies_txt=_cookies_txt())
    db.commit()
    kho_tai_khoan.kiem_tran_khach(db, "u1", "douyin", bay_gio=_bay_gio(1))


# ── Chọn nguồn phiên trong `jobs._phien` ──────────────────────────────────────

class AdapterKho:
    """Adapter có `tep_cookie` (đường mà `_phien` bơm cookie vào) — không đọc mạng."""

    nen_tang = "douyin"

    def __init__(self, loi=None):
        self.tep_cookie = None
        self.thay = []
        self.loi = dict(loi or {})

    def kham_pha(self, yeu_cau, *, bao_tien_do):
        from apps.video_crawler.adapters.base import CrawlItem
        self.thay.append(self.tep_cookie)
        return [CrawlItem(nen_tang="douyin", id="7111111111", url="https://www.douyin.com/video/7111111111",
                          tieu_de="V")][: yeu_cau.so_luong]

    def tai(self, item, thu_muc, *, bao_tien_do):
        from apps.video_crawler.adapters.base import TepTai
        self.thay.append(self.tep_cookie)
        if item.id in self.loi:
            raise self.loi[item.id]
        p = thu_muc / f"{item.id}.mp4"
        p.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        return TepTai(p, p.stat().st_size, f"{item.tieu_de} [{item.id}].mp4")


class CtxGia:
    job_id = "job-kho-1"
    job_type = "video_crawler.tai"

    def __init__(self):
        self.su_kien = []

    def progress(self, phan_tram, thong_diep=""):
        return None

    def is_cancelled(self):
        return False

    def event(self, ma, thong_diep, visibility="customer", **kw):
        self.su_kien.append((ma, str(thong_diep), visibility))


def test_phien_rieng_cua_khach_thang_kho(db):
    from apps.video_crawler import jobs as vc_jobs
    from apps.video_crawler import phien
    _them(db, "phu-1")
    phien.luu(db, owner_id="u1", nen_tang="douyin", cookies_txt=_cookies_txt("cookie-rieng-cua-khach"))
    db.commit()
    ad = AdapterKho()
    with vc_jobs._phien(ad, "u1", "douyin") as p:
        assert p.nguon == "rieng"
        assert "cookie-rieng-cua-khach" in Path(ad.tep_cookie).read_text(encoding="utf-8")


def test_khong_co_phien_rieng_thi_muon_kho(db):
    from apps.video_crawler import jobs as vc_jobs
    tk = _them(db, "phu-1")
    ad = AdapterKho()
    with vc_jobs._phien(ad, "u1", "douyin") as p:
        assert p.nguon == "kho" and p.tai_khoan_id == tk.id
        duong = Path(ad.tep_cookie)
        assert _BI_MAT in duong.read_text(encoding="utf-8")
    assert ad.tep_cookie is None and not duong.exists()          # tệp tạm biến mất khi ra khỏi khối


def test_hai_job_cung_luc_kho_het_cho_thi_dang_ban(db):
    from apps.video_crawler import jobs as vc_jobs
    from platform_core.jobs import DangBan
    _them(db, "phu-1")
    with vc_jobs._phien(AdapterKho(), "u1", "douyin") as p1:
        assert p1.nguon == "kho"
        with pytest.raises(DangBan):                     # về hàng đợi: không tiêu lượt, không chạm tiền
            with vc_jobs._phien(AdapterKho(), "u2", "douyin"):
                pass


def test_kho_khong_con_tai_khoan_song_thi_loi_nguoi_goi(db):
    from apps.video_crawler import jobs as vc_jobs
    from platform_core.jobs import LoiNguoiGoi
    with pytest.raises(LoiNguoiGoi) as e:
        with vc_jobs._phien(AdapterKho(), "u1", "douyin"):
            pass
    assert "douyin" not in str(e.value).lower() or "Douyin" in str(e.value)   # câu cho khách, không kỹ thuật
    assert _BI_MAT not in str(e.value)


def test_nen_khong_co_kho_van_chay_an_danh(db):
    """YouTube có `cookie_dang_nhap` nhưng KHÔNG có kho ⇒ job vẫn chạy ẩn danh, không ném."""
    from apps.video_crawler import jobs as vc_jobs
    ad = AdapterKho()
    with vc_jobs._phien(ad, "u1", "youtube") as p:
        assert p.nguon == "" and ad.tep_cookie is None


def test_tra_cho_khi_job_loi_va_cham_diem_theo_ma(db):
    from apps.video_crawler import jobs as vc_jobs
    from apps.video_crawler import kho_tai_khoan
    from platform_core.jobs import LoiNguoiGoi
    tk = _them(db, "phu-1")
    cau = next(c for ma, _t, _tt, c in __import__("apps.video_crawler.loi", fromlist=["loi"])._BANG
               if ma == "can_dang_nhap")
    with pytest.raises(LoiNguoiGoi):
        with vc_jobs._phien(AdapterKho(), "u1", "douyin"):
            raise LoiNguoiGoi(cau)
    row = _diem(db, tk.id)
    assert row.trang_thai == kho_tai_khoan.HET_HAN and row.loi_gan_nhat == "can_dang_nhap"
    assert kho_tai_khoan.con_tai_khoan_song(db, "douyin") is False    # chỗ đã nhả, tài khoản đã loại


def test_huy_job_khong_tru_diem_tai_khoan(db):
    from apps.video_crawler import jobs as vc_jobs
    from apps.video_crawler import kho_tai_khoan
    from platform_core.job_runner import JobCancelled
    tk = _them(db, "phu-1")
    with pytest.raises(JobCancelled):
        with vc_jobs._phien(AdapterKho(), "u1", "douyin"):
            raise JobCancelled()
    row = _diem(db, tk.id)
    assert row.diem == kho_tai_khoan.DIEM_BAN_DAU and row.trang_thai == kho_tai_khoan.SONG


# ── Cô lập: khách không thấy cookie, cũng không thấy tài khoản nào ────────────

def _params_tai(owner="u1", ids=("7111111111",)):
    return {"owner_id": owner, "nen_tang": "douyin",
            "muc": [{"id": i, "url": f"https://www.douyin.com/video/{i}", "tieu_de": "V"} for i in ids]}


def test_job_ghi_nguon_phien_nhung_id_tai_khoan_chi_o_su_kien_internal(db, kho_tep, caplog):
    import json

    from apps.video_crawler import jobs as vc_jobs
    from platform_core import job_events
    tk = _them(db, "phu-1")
    ad = AdapterKho()
    ctx = CtxGia()
    import apps.video_crawler.jobs as _j
    goc, _j._adapter = _j._adapter, lambda nen: ad
    try:
        with caplog.at_level("DEBUG"):
            ket_qua = vc_jobs.handle(_params_tai(), ctx)
    finally:
        _j._adapter = goc
    assert ket_qua["nguon_phien"] == "kho"
    ra = json.dumps(ket_qua, default=str) + json.dumps(_params_tai()) + caplog.text
    assert _BI_MAT not in ra and tk.id not in ra                 # cookie và id KHÔNG ra đường khách/log
    cho_khach = [s for s in ctx.su_kien if s[2] == job_events.CUSTOMER]
    assert all(tk.id not in t and _BI_MAT not in t for _ma, t, _v in cho_khach)
    noi_bo = [s for s in ctx.su_kien if s[2] == job_events.INTERNAL]
    assert any(tk.id in t for _ma, t, _v in noi_bo)              # truy được: lượt này đi tài khoản nào
    assert all(_BI_MAT not in t for _ma, t, _v in noi_bo)
    assert ad.thay and all(d and Path(d).name == "cookies_douyin.txt" for d in ad.thay)


def test_kham_pha_cung_muon_kho_va_ghi_nguon_phien(db, kho_tep):
    from apps.video_crawler import jobs as vc_jobs
    _them(db, "phu-1")
    ad = AdapterKho()
    ctx = CtxGia()
    ctx.job_type = "video_crawler.kham_pha"
    import apps.video_crawler.jobs as _j
    goc, _j._adapter = _j._adapter, lambda nen: ad
    try:
        ket_qua = vc_jobs.handle({"owner_id": "u1", "nen_tang": "douyin", "che_do": "link",
                                  "dau_vao": "https://www.douyin.com/video/7111111111", "so_luong": 1}, ctx)
    finally:
        _j._adapter = goc
    assert ket_qua["nguon_phien"] == "kho"


def test_cookie_kho_khong_bao_gio_o_dang_ro_trong_csdl(db):
    from sqlalchemy import select

    from platform_core.db import Base
    _them(db, "phu-1")
    m = None
    from apps.video_crawler import kho_tai_khoan
    m = kho_tai_khoan.muon(db, "douyin", owner_id="u1", job_id="j1", bay_gio=_bay_gio())
    kho_tai_khoan.tra(db, m, bay_gio=_bay_gio())
    het = []
    for bang in Base.metadata.sorted_tables:
        try:
            het += [" ".join(str(v) for v in dong) for dong in db.execute(select(bang)).all()]
        except Exception:      # noqa: BLE001 — bảng deployment này không có
            continue
    assert _BI_MAT not in "\n".join(het)


# ── Migration khớp ORM + governance ───────────────────────────────────────────

def _migration():
    p = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260923_1400_vc_tai_khoan.py"
    spec = importlib.util.spec_from_file_location("mig_vc_tai_khoan", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_noi_tiep_head_cu_va_khop_orm(tmp_path):
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from apps.video_crawler.tables import VcTaiKhoan

    mig = _migration()
    assert mig.down_revision == "3b7d2f9e1c48"
    eng = sa.create_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    with eng.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig.upgrade()
    insp = sa.inspect(eng)
    cot = {c["name"]: c for c in insp.get_columns("vc_tai_khoan")}
    orm = VcTaiKhoan.__table__
    assert set(cot) == {c.name for c in orm.columns}
    for c in orm.columns:
        assert cot[c.name]["nullable"] == c.nullable, c.name
    uq = {tuple(u["column_names"]) for u in insp.get_unique_constraints("vc_tai_khoan")}
    orm_uq = {tuple(c.name for c in u.columns) for u in orm.constraints if isinstance(u, sa.UniqueConstraint)}
    assert orm_uq <= uq and ("nen_tang", "nhan") in uq
    idx = {i["name"]: tuple(i["column_names"]) for i in insp.get_indexes("vc_tai_khoan")}
    orm_idx = {i.name: tuple(c.name for c in i.columns) for i in orm.indexes}
    assert orm_idx == idx and ("nen_tang",) in idx.values()
    with eng.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig.downgrade()
    assert "vc_tai_khoan" not in sa.inspect(eng).get_table_names()


def test_governance_khai_bang_tai_khoan_la_du_lieu_cua_LTT():
    """Bảng này là tài khoản PHỤ của LTT, không có gì của khách (không `user_id`, không nội dung khách)."""
    from platform_core.public_api import governance
    assert "vc_tai_khoan" in governance.NOT_CUSTOMER_DATA
    assert governance.unclassified(["vc_tai_khoan"]) == []


# ── Kho phải dùng được ở ĐƯỜNG CÀO, không chỉ đường tìm kênh ─────────────────
#
# Rà soát khi gộp W4-L11: `features._kiem_phien(cho_kho=True)` mới chỉ được gọi ở đường TÌM KÊNH. Đường cào
# (`dung_params_kham_pha`) vẫn đòi khách có phiên RIÊNG ⇒ dán cookie vào kho xong vẫn không cào được nền đó,
# tức cả hạng mục kho tài khoản không tới được khách.

_DNS_KHO = lambda host: ["1.2.3.4"]  # noqa: E731


def test_kho_co_tai_khoan_song_thi_khach_cao_duoc_khong_can_phien_rieng(db, vc_go_ghim):
    from apps.video_crawler import features
    _them(db, nen="douyin")
    p = features.dung_params_kham_pha(owner_id="u1", nen_tang="douyin", che_do="tu_khoa", dau_vao="meo con",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS_KHO, db=db)
    assert p["nen_tang"] == "douyin"


def test_kho_RONG_thi_van_tu_choi_o_cua_vao_khong_de_job_hong(db, vc_go_ghim):
    """Không tài khoản nào sống ⇒ từ chối NGAY, đừng nhận job rồi hỏng và hoàn tiền (khách chờ vô ích)."""
    from apps.video_crawler import features
    with pytest.raises(features.LoiDauVao, match="đăng nhập|khả dụng"):
        features.dung_params_kham_pha(owner_id="u1", nen_tang="douyin", che_do="tu_khoa", dau_vao="meo con",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS_KHO, db=db)


def test_tai_khoan_kho_tam_nghi_khong_tinh_la_song(db, vc_go_ghim):
    from apps.video_crawler import features, kho_tai_khoan
    from apps.video_crawler.tables import TAM_NGHI
    tk = _them(db, nen="douyin")
    kho_tai_khoan.doi_trang_thai(db, tk.id, TAM_NGHI)
    db.commit()
    with pytest.raises(features.LoiDauVao):
        features.dung_params_kham_pha(owner_id="u1", nen_tang="douyin", che_do="tu_khoa", dau_vao="meo con",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS_KHO, db=db)
