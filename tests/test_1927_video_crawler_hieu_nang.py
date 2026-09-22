"""
video_crawler — hiệu năng W2-L8 (PLAN_MVP §C W2, sau L6 dedup bền).

Phần đã làm: ảnh bìa được tải VÀ LƯU vào storage ngay ở bước khám phá (`_xu_ly_kham_pha` →
`anh_bia.luu_kham_pha`), thay vì route `/anh-bia/...` tải lại từ CDN mỗi lần khách xem. Ảnh lỗi (CDN hỏng,
quá 2 MB, SVG…) không được làm hỏng job khám phá — mục đó giữ nguyên URL CDN gốc, route đọc lại qua
`anh_bia.doc()` (mới) sẽ rơi về nhánh "tải sống" như cũ. Tổng thời gian tải ảnh của một job có trần
(`NGAN_SACH_ANH_BIA_S`) để một CDN chậm không kéo dài job khám phá (miễn phí, khách chờ trực tiếp).

Phần KHÔNG làm (quyết định, xem báo cáo lane): tải song song ≤ 2 mục/job cho job TẢI. `_TienDo` tính %
theo giả định một mục đang chạy tại một thời điểm (`self.i` cố định giữa các lần gọi `bao()`), và khối dọn
dẹp khi lỗi/huỷ (`nha_cho` + xoá storage) giả định một luồng duy nhất đang ghi `da_luu`. Làm song song đúng
cho job TẢI — nơi chạm sổ credit thật — cần thiết kế lại cả hai, rủi ro cao hơn lợi ích trong khi nền đủ
điều kiện (không cần phiên, không phải youtube) hiện chỉ có `bilibili_tv`. Test dưới đây chỉ khoá phần ảnh
bìa; không có test "song song" vì mục đó chưa cài.

Tải ảnh được TIÊM (monkeypatch `anh_bia.tai` hoặc tham số `lay=`) để test không đọc mạng.
"""
from __future__ import annotations

import pytest

import tests.test_1905_video_crawler_job as _t1905
from tests.test_1905_video_crawler_job import _DNS, AdapterGia, _chay, _dung_adapter

db = _t1905.db
kho = _t1905.kho
nguoi = _t1905.nguoi

_A, _B = "a" * 11, "b" * 11
_URL_BIA_A = "https://i.ytimg.com/vi/a/hq.jpg"
_URL_BIA_B = "https://i.ytimg.com/vi/b/hq.jpg"
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


@pytest.fixture(autouse=True)
def _xoa_dem_anh_bia():
    """`anh_bia.tai` đệm theo (nền, URL) ở biến module — nhiều test dưới đây dùng lại CÙNG URL với `lay`
    giả khác nhau; không xoá đệm thì test sau đọc trúng kết quả đệm của test trước, không gọi `lay` của
    chính nó (phát hiện khi chạy thật, không phải suy đoán)."""
    from apps.video_crawler import anh_bia
    anh_bia.xoa_dem()
    yield
    anh_bia.xoa_dem()


def _nop_kham_pha(db, owner, *, so_luong=5):
    from apps.video_crawler import features
    p = features.dung_params_kham_pha(owner_id=owner, nen_tang="youtube", che_do="tu_khoa",
                                       dau_vao="meo", so_luong=so_luong, khong_trung=False, phan_giai=_DNS)
    job = features.nop(db, owner_id=owner, job_type="video_crawler.kham_pha", params=p)
    db.commit()
    return job.id


# ── `_xu_ly_kham_pha` lưu ảnh bìa vào storage (chuỗi job thật) ────────────────

def test_kham_pha_luu_anh_bia_vao_storage(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import anh_bia

    goi = []

    def tai_gia(url, *, nen_tang=None, phan_giai=None, lay=None):
        goi.append(url)
        return _PNG, "image/png"
    monkeypatch.setattr(anh_bia, "tai", tai_gia)

    from apps.video_crawler.adapters.base import CrawlItem
    item = CrawlItem(nen_tang="youtube", id=_A, url=f"https://www.youtube.com/watch?v={_A}",
                     tieu_de="Video A", anh_bia=_URL_BIA_A)
    _dung_adapter(monkeypatch, AdapterGia(muc=[item]))

    jid = _nop_kham_pha(db, "u1", so_luong=1)
    job = _chay(db, jid)
    from platform_core.models import JOB_DONE
    assert job.status == JOB_DONE, job.error
    m = job.result["muc"][0]
    key = m["anh_bia"]
    assert key == f"video_crawler/u1/{jid}/bia/0"
    assert kho.exists(key)
    with kho.open(key) as f:
        assert f.read() == _PNG
    assert goi == [_URL_BIA_A]                          # đúng một lượt tải mạng cho một mục


def test_muc_khong_co_anh_bia_khong_goi_tai(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import anh_bia
    goi = []
    monkeypatch.setattr(anh_bia, "tai", lambda *a, **k: goi.append(1) or (_PNG, "image/png"))
    from apps.video_crawler.adapters.base import CrawlItem
    item = CrawlItem(nen_tang="youtube", id=_A, url=f"https://www.youtube.com/watch?v={_A}", tieu_de="A")
    _dung_adapter(monkeypatch, AdapterGia(muc=[item]))
    jid = _nop_kham_pha(db, "u1", so_luong=1)
    job = _chay(db, jid)
    assert job.result["muc"][0]["anh_bia"] == ""
    assert goi == []


def test_anh_loi_khong_lam_hong_job_giu_url_goc(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import anh_bia
    from apps.video_crawler.adapters.base import CrawlItem
    from platform_core.models import JOB_DONE

    def tai_loi(url, *, nen_tang=None, phan_giai=None, lay=None):
        raise anh_bia.AnhKhongHopLe("ảnh quá lớn")
    monkeypatch.setattr(anh_bia, "tai", tai_loi)

    item = CrawlItem(nen_tang="youtube", id=_A, url=f"https://www.youtube.com/watch?v={_A}",
                     tieu_de="A", anh_bia=_URL_BIA_A)
    _dung_adapter(monkeypatch, AdapterGia(muc=[item]))
    jid = _nop_kham_pha(db, "u1", so_luong=1)
    job = _chay(db, jid)
    assert job.status == JOB_DONE, job.error                # lỗi ảnh không hỏng job
    assert job.result["muc"][0]["anh_bia"] == _URL_BIA_A     # giữ url gốc — route dùng nhánh "tải sống"
    assert not kho.exists(f"video_crawler/u1/{jid}/bia/0")


# ── Ngân sách tổng cho ảnh bìa (đơn vị, không cần job thật) ───────────────────

def test_ngan_sach_anh_bia_het_thi_cac_muc_con_lai_giu_url_goc(monkeypatch):
    from apps.video_crawler import anh_bia, jobs as vc_jobs
    from apps.video_crawler.adapters.base import CrawlItem

    dong_ho = [0.0]
    monkeypatch.setattr(vc_jobs.time, "monotonic", lambda: dong_ho[0])
    goi = []

    def luu_gia(url, *, nen_tang, owner_id, job_id, chi_so, kho=None, phan_giai=None, lay=None):
        goi.append(chi_so)
        dong_ho[0] += vc_jobs.NGAN_SACH_ANH_BIA_S + 1        # mục đầu đã ăn hết ngân sách
        return f"video_crawler/{owner_id}/{job_id}/bia/{chi_so}"
    monkeypatch.setattr(anh_bia, "luu_kham_pha", luu_gia)

    muc = [CrawlItem(nen_tang="youtube", id=_A, url="u1", tieu_de="A", anh_bia=_URL_BIA_A),
          CrawlItem(nen_tang="youtube", id=_B, url="u2", tieu_de="B", anh_bia=_URL_BIA_B)]
    ra = vc_jobs._luu_anh_bia(muc, owner_id="u1", job_id="job-1", nen_id="youtube")
    assert goi == [0]                                        # mục thứ hai không thử tải nữa
    assert ra[0]["anh_bia"] == "video_crawler/u1/job-1/bia/0"
    assert ra[1]["anh_bia"] == _URL_BIA_B                    # hết ngân sách ⇒ giữ url gốc


# ── `anh_bia.luu_kham_pha` (đơn vị) ───────────────────────────────────────────

def test_luu_kham_pha_thanh_cong_ghi_dung_key_va_content_type(tmp_path):
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    key = anh_bia.luu_kham_pha(_URL_BIA_A, nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=2,
                               kho=kho, phan_giai=_DNS, lay=lambda url, *, toi_da: (_PNG, "image/png"))
    assert key == "video_crawler/u1/j1/bia/2"
    with kho.open(key) as f:
        assert f.read() == _PNG


def test_luu_kham_pha_rong_hoac_loi_tra_none_khong_nem(tmp_path):
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    assert anh_bia.luu_kham_pha("", nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=0, kho=kho) is None

    def lay_loi(url, *, toi_da):
        raise TimeoutError("mạng chậm")
    assert anh_bia.luu_kham_pha(_URL_BIA_A, nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=0,
                                kho=kho, phan_giai=_DNS, lay=lay_loi) is None
    assert not kho.exists("video_crawler/u1/j1/bia/0")


def test_luu_kham_pha_loi_storage_tra_none(tmp_path):
    from apps.video_crawler import anh_bia

    class KhoHong:
        def put(self, *a, **k):
            raise OSError("đĩa đầy")
    key = anh_bia.luu_kham_pha(_URL_BIA_A, nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=0,
                               kho=KhoHong(), phan_giai=_DNS, lay=lambda url, *, toi_da: (_PNG, "image/png"))
    assert key is None


# ── `anh_bia.doc` (route cần điều phối để gọi hàm này thay `tai`) ─────────────

def test_doc_uu_tien_doc_storage_khi_gia_tri_la_key(tmp_path):
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    key = anh_bia.luu_kham_pha(_URL_BIA_A, nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=0,
                               kho=kho, phan_giai=_DNS, lay=lambda url, *, toi_da: (_PNG, "image/png"))
    du_lieu, loai = anh_bia.doc(key, nen_tang="youtube", kho=kho)
    assert du_lieu == _PNG and loai == "image/png"


def test_doc_fallback_tai_song_khi_gia_tri_la_url(tmp_path):
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    goi = []

    def lay(url, *, toi_da):
        goi.append(url)
        return _PNG, "image/jpeg"
    du_lieu, loai = anh_bia.doc(_URL_BIA_A, nen_tang="youtube", kho=kho, lay=lay, phan_giai=_DNS)
    assert du_lieu == _PNG and loai == "image/jpeg"
    assert goi == [_URL_BIA_A]


def test_doc_tep_storage_mat_thi_nem_anh_khong_hop_le(tmp_path):
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    with pytest.raises(anh_bia.AnhKhongHopLe):
        anh_bia.doc("video_crawler/u1/j1/bia/0", nen_tang="youtube", kho=kho)


def test_doc_chi_doc_key_cua_dung_chu_va_job(tmp_path):
    """Gộp L8: route truyền owner/job ⇒ key kho ngoài `video_crawler/<chủ>/<job>/bia/` bị từ chối (phòng thủ nhiều
    lớp — hôm nay `result` do máy chủ ghi, nhưng route không nên đọc được tệp kho khác chỉ vì nó bắt đầu `video_crawler/`)."""
    from platform_core.storage import LocalStorage
    from apps.video_crawler import anh_bia
    kho = LocalStorage(str(tmp_path / "s"))
    key = anh_bia.luu_kham_pha(_URL_BIA_A, nen_tang="youtube", owner_id="u1", job_id="j1", chi_so=0,
                               kho=kho, phan_giai=_DNS, lay=lambda url, *, toi_da: (_PNG, "image/png"))
    assert anh_bia.doc(key, nen_tang="youtube", kho=kho, owner_id="u1", job_id="j1")[0] == _PNG
    for chu, job in (("u2", "j1"), ("u1", "j2")):
        with pytest.raises(anh_bia.AnhKhongHopLe):
            anh_bia.doc(key, nen_tang="youtube", kho=kho, owner_id=chu, job_id=job)
    with pytest.raises(anh_bia.AnhKhongHopLe):
        anh_bia.doc("video_crawler/u1/j1/video.mp4", nen_tang="youtube", kho=kho, owner_id="u1", job_id="j1")
