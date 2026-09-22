"""
video_crawler — chuỗi job thật: nộp (giữ credit) → worker claim → handler → storage → result → quyết toán.

Chạy qua `job_runner._chay_mot_job` thật trên SQLite tạm (khuôn `test_67`). Chỉ adapter là giả, để test không
đọc mạng. Các mệnh đề chốt (spec §14, §17, §18, §19):
- tải xong N mục ⇒ N tệp trong storage `video_crawler/<owner>/<job>/<id>.mp4`, trừ đúng Σ `gia.gia_muc`
  theo thời lượng thật của N mục (giá MỘT nguồn: `apps/video_crawler/gia.py`, DANH_GIA_MVP §3, 22/09);
- một phần lỗi ⇒ job xong, mục lỗi ghi `loi`, hoàn tiền phần lỗi;
- lỗi phía khách ở MỌI mục ⇒ job `error`, KHÔNG thử lại, hoàn đủ, không để tệp mồ côi
  (sửa lỗi donor: không đánh "xong" với 0 video, `W:11652`);
- huỷ giữa chừng ⇒ job `cancelled`, tệp đã lưu bị dọn;
- "không trùng" chỉ bỏ mục chính user đó đã tải xong, không bị lịch sử user khác ảnh hưởng.
"""
from __future__ import annotations

import pytest

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, TepTai

_DNS = lambda host: ["142.250.66.78"]  # noqa: E731 — DNS giả, test không đọc mạng

#: Giữ chỗ nay là 15 credit/mục (gia.GIA_GIU_CHO) — nạp dư để nhiều mục/nhiều job liên tiếp trong một
#: test không chạm `ThieuCreditError` (không phải giá trị cần kiểm, chỉ là vốn ban đầu của test).
NAP_BAN_DAU = 2000


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'j.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


@pytest.fixture()
def kho(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store"))
    set_storage(st)
    try:
        yield st
    finally:
        set_storage(None)


def _muc(i: str, thoi_luong_s: int | None = None) -> CrawlItem:
    return CrawlItem(nen_tang="youtube", id=i, url=f"https://www.youtube.com/watch?v={i}",
                     tieu_de=f"Video {i}", thoi_luong_s=thoi_luong_s)


class AdapterGia:
    nen_tang = "youtube"

    def __init__(self, muc=(), loi=None, truoc_tai=None):
        self.muc = list(muc)
        self.loi = dict(loi or {})
        self.truoc_tai = truoc_tai
        self.da_tai = []

    def kham_pha(self, yeu_cau, *, bao_tien_do):
        return self.muc[: yeu_cau.so_luong]

    def tai(self, item, thu_muc, *, bao_tien_do):
        if self.truoc_tai:
            self.truoc_tai(item)
        bao_tien_do(50, "đang tải")
        if item.id in self.loi:
            raise self.loi[item.id]
        p = thu_muc / f"{item.id}.mp4"
        p.write_bytes(b"\x00\x00\x00\x18ftypmp42" + item.id.encode())
        self.da_tai.append(item.id)
        return TepTai(p, p.stat().st_size, f"{item.tieu_de} [{item.id}].mp4")


@pytest.fixture()
def nguoi(db):
    from platform_core import credit
    from tests.conftest import bao_dam_user
    for uid in ("u1", "u2"):
        bao_dam_user(db, uid)
        credit.nap(db, uid, NAP_BAN_DAU)
    db.commit()
    return "u1"


def _dung_adapter(monkeypatch, adapter):
    import apps.video_crawler.jobs as vc_jobs
    monkeypatch.setattr(vc_jobs, "_adapter", lambda nen: adapter)


def _nop_tai(db, owner, ids):
    from apps.video_crawler import features
    params = features.dung_params_tai(
        owner_id=owner, nen_tang="youtube",
        muc=[{"id": i, "url": f"https://www.youtube.com/watch?v={i}", "tieu_de": f"Video {i}"} for i in ids],
        phan_giai=_DNS)
    job = features.nop(db, owner_id=owner, job_type="video_crawler.tai", params=params)
    db.commit()
    return job.id


def _chay(db, job_id):
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job
    assert _chay_mot_job("w-vc") is True
    db.expire_all()
    return db.get(Job, job_id)


def _so_du(db, uid):
    from platform_core import credit
    db.expire_all()
    return credit.so_du(db, uid)


def test_tai_hai_muc_luu_storage_va_tru_dung_gia_theo_thoi_luong(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import gia
    from platform_core.models import JOB_DONE
    _dung_adapter(monkeypatch, AdapterGia())
    jid = _nop_tai(db, "u1", ["aaaaaaaaaaa", "bbbbbbbbbbb"])
    assert _so_du(db, "u1") == NAP_BAN_DAU - 2 * gia.GIA_GIU_CHO       # giữ chỗ bậc cao nhất × 2 mục

    job = _chay(db, jid)
    assert job.status == JOB_DONE, job.error
    keys = job.result["video_keys"]
    assert keys == [f"video_crawler/u1/{jid}/aaaaaaaaaaa.mp4", f"video_crawler/u1/{jid}/bbbbbbbbbbb.mp4"]
    assert all(kho.exists(k) for k in keys)
    assert [m["id"] for m in job.result["muc"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert not any(k.endswith("_key") for m in job.result["muc"] for k in m)   # spec §14: trần 20 artifacts
    # không rõ thời lượng (mục đến từ danh sách id thô) ⇒ bậc rẻ nhất mỗi mục, phần chênh với giữ chỗ hoàn lại
    assert job.result["credit_cost"] == 2 * gia.gia_muc(None)
    assert _so_du(db, "u1") == NAP_BAN_DAU - 2 * gia.gia_muc(None)


def test_mot_phan_loi_thi_xong_va_hoan_phan_loi(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import gia
    from platform_core.models import JOB_DONE
    _dung_adapter(monkeypatch, AdapterGia(loi={"bbbbbbbbbbb": LoiCao("rieng_tu", "Video riêng tư.", tam_thoi=False)}))
    jid = _nop_tai(db, "u1", ["aaaaaaaaaaa", "bbbbbbbbbbb"])
    job = _chay(db, jid)
    assert job.status == JOB_DONE
    assert job.result["video_keys"] == [f"video_crawler/u1/{jid}/aaaaaaaaaaa.mp4"]
    assert job.result["loi"] == [{"id": "bbbbbbbbbbb", "ma": "rieng_tu", "thong_diep": "Video riêng tư."}]
    assert job.result["credit_cost"] == gia.gia_muc(None)       # chỉ mục thành công mới bị tính tiền
    assert _so_du(db, "u1") == NAP_BAN_DAU - gia.gia_muc(None)


def test_moi_muc_loi_phia_khach_thi_error_khong_thu_lai_hoan_du(db, kho, nguoi, monkeypatch):
    from platform_core.models import JOB_ERROR
    loi = LoiCao("khong_ton_tai", "Video không còn tồn tại.", tam_thoi=False)
    _dung_adapter(monkeypatch, AdapterGia(loi={"aaaaaaaaaaa": loi, "bbbbbbbbbbb": loi}))
    jid = _nop_tai(db, "u1", ["aaaaaaaaaaa", "bbbbbbbbbbb"])
    job = _chay(db, jid)
    assert job.status == JOB_ERROR
    assert job.attempts == 1                            # LoiNguoiGoi: không thử lại
    assert _so_du(db, "u1") == NAP_BAN_DAU
    assert not kho.exists(f"video_crawler/u1/{jid}/aaaaaaaaaaa.mp4")


def test_huy_giua_chung_thi_cancelled_va_don_tep(db, kho, nguoi, monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.db import get_session
    from platform_core.models import JOB_CANCELLED, Job

    jid_holder = {}

    def huy_truoc_muc_b(item):
        if item.id != "bbbbbbbbbbb":
            return
        gen = get_session(); s = next(gen)
        try:
            assert jobq.cancel(s, s.get(Job, jid_holder["id"]))
            s.commit()
        finally:
            s.close()

    _dung_adapter(monkeypatch, AdapterGia(truoc_tai=huy_truoc_muc_b))
    jid_holder["id"] = jid = _nop_tai(db, "u1", ["aaaaaaaaaaa", "bbbbbbbbbbb"])
    job = _chay(db, jid)
    assert job.status == JOB_CANCELLED
    assert not kho.exists(f"video_crawler/u1/{jid}/aaaaaaaaaaa.mp4")   # tệp mục a đã lưu phải bị dọn
    assert _so_du(db, "u1") == NAP_BAN_DAU


def test_khong_trung_chi_bo_muc_chinh_user_da_tai(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    from platform_core.models import JOB_DONE

    _dung_adapter(monkeypatch, AdapterGia())
    _chay(db, _nop_tai(db, "u1", ["aaaaaaaaaaa"]))                 # u1 đã có "aaaaaaaaaaa"
    _chay(db, _nop_tai(db, "u2", ["bbbbbbbbbbb"]))                 # u2 có "bbbbbbbbbbb" — không được ảnh hưởng u1

    adapter = AdapterGia(muc=[_muc("aaaaaaaaaaa"), _muc("bbbbbbbbbbb"), _muc("ccccccccccc")])
    _dung_adapter(monkeypatch, adapter)
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 3,
                                             "khong_trung": True},
                                      phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    assert adapter.da_tai == ["bbbbbbbbbbb", "ccccccccccc"]
    assert job.result["bo_qua_trung"] == 1


def test_kham_pha_mien_phi_tra_danh_sach(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    from platform_core.models import JOB_DONE

    _dung_adapter(monkeypatch, AdapterGia(muc=[_muc("aaaaaaaaaaa"), _muc("bbbbbbbbbbb")]))
    params = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="tu_khoa",
                                           dau_vao="meo", so_luong=5, khong_trung=False, phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.kham_pha", params=params)
    db.commit()
    assert _so_du(db, "u1") == NAP_BAN_DAU
    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    assert [m["id"] for m in job.result["muc"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert "video_keys" not in job.result
    assert _so_du(db, "u1") == NAP_BAN_DAU


def test_lich_su_chi_thay_job_cua_minh(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia())
    a = _nop_tai(db, "u1", ["aaaaaaaaaaa"])
    _nop_tai(db, "u2", ["bbbbbbbbbbb"])
    assert [j.id for j in features.lich_su(db, "u1")] == [a]


@pytest.mark.parametrize("sai", [
    dict(nen_tang="kuaishou", che_do="tu_khoa", dau_vao="meo", so_luong=5),   # nền chưa bật
    dict(nen_tang="youtube", che_do="xyz", dau_vao="meo", so_luong=5),        # chế độ lạ
    dict(nen_tang="youtube", che_do="tu_khoa", dau_vao="", so_luong=5),       # trống
    dict(nen_tang="youtube", che_do="tu_khoa", dau_vao="meo", so_luong=0),
    dict(nen_tang="youtube", che_do="tu_khoa", dau_vao="meo", so_luong=21),   # trần 20 (artifacts)
    dict(nen_tang="youtube", che_do="link", dau_vao="https://evil.example/x", so_luong=1),
    dict(nen_tang="youtube", che_do="link", dau_vao="http://127.0.0.1/x", so_luong=1),
])
def test_validate_theo_registry_tu_choi_co_ten(sai):
    from apps.video_crawler import features
    with pytest.raises(features.LoiDauVao):
        features.dung_params_kham_pha(owner_id="u1", khong_trung=False, phan_giai=_DNS, **sai)


def test_kenh_nhan_handle_tran():
    from apps.video_crawler import features
    p = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="kenh", dau_vao="@abc",
                                      so_luong=3, khong_trung=False, phan_giai=_DNS)
    assert p["dau_vao"] == "@abc" and p["owner_id"] == "u1"


def test_job_cua_chi_tra_job_cua_chu(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia())
    a = _nop_tai(db, "u1", ["aaaaaaaaaaa"])
    assert features.job_cua(db, "u1", a).id == a
    assert features.job_cua(db, "u2", a) is None
    assert features.job_cua(db, "u1", a, job_type="video_crawler.kham_pha") is None
    assert features.job_cua(db, "u1", "khong-co") is None


def test_kham_pha_gioi_han_tan_suat_theo_user(db, kho, nguoi, monkeypatch):
    """Phản biện #8: xem trước miễn phí nhưng tìm dồn dập từ IP máy A đẩy YouTube vào bot-check."""
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia())
    for i in range(features.KHAM_PHA_MOI_PHUT):
        features.kiem_tan_suat(db, "u1")
        p = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="tu_khoa",
                                          dau_vao=f"meo {i}", so_luong=1, khong_trung=False, phan_giai=_DNS)
        features.nop(db, owner_id="u1", job_type="video_crawler.kham_pha", params=p)
        db.commit()
    with pytest.raises(features.QuaTanSuat):
        features.kiem_tan_suat(db, "u1")
    features.kiem_tan_suat(db, "u2")          # user khác không bị ảnh hưởng


class _CtxGhi:
    def __init__(self):
        self.goi = []

    def progress(self, p, msg=""):
        self.goi.append(p)


def test_tien_do_chi_tang_va_luong_tu_hoa():
    """Kiểm GUI 22/09: yt-dlp tải luồng hình rồi luồng tiếng, mỗi luồng đếm lại từ 0 ⇒ thanh tiến độ giật lùi
    (47% → 3%), và mỗi % thành một dòng trong lịch sử job. Tiến độ phải đơn điệu và theo bước."""
    from apps.video_crawler.jobs import _TienDo
    ctx = _CtxGhi()
    td = _TienDo(ctx, 2)
    for p in (0, 1, 4, 8, 17, 46, 98, 3, 7, 31, 99):      # mục 1: hình rồi tiếng
        td.bao(p, "đang tải")
    td.i = 1
    for p in (0, 50, 100):
        td.bao(p, "đang tải")
    assert ctx.goi == sorted(ctx.goi), ctx.goi                 # không bao giờ lùi
    assert len(ctx.goi) == len(set(ctx.goi))                   # không ghi trùng một mức
    assert all(p % 5 == 0 for p in ctx.goi), ctx.goi           # bước 5%
    assert len(ctx.goi) <= 21


def test_xong_job_dat_tien_do_100_kem_thong_diep(db, kho, nguoi, monkeypatch):
    _dung_adapter(monkeypatch, AdapterGia())
    job = _chay(db, _nop_tai(db, "u1", ["aaaaaaaaaaa", "bbbbbbbbbbb"]))
    assert job.progress == 100
    assert job.progress_msg.startswith("Xong")


def test_moi_muc_deu_trung_thi_bao_ro_cho_khach_khong_tru_tien(db, kho, nguoi, monkeypatch):
    """Kiểm GUI 22/09: nhánh 'mọi mục đều đã tải' hoàn tất im lặng — khách thấy 'tìm thấy 1 video' rồi Done
    mà không có tệp. Phải báo rõ và không tính tiền."""
    from apps.video_crawler import features, gia
    from platform_core import job_events
    from platform_core.models import JOB_DONE

    _dung_adapter(monkeypatch, AdapterGia())
    _chay(db, _nop_tai(db, "u1", ["aaaaaaaaaaa"]))
    con_lai = NAP_BAN_DAU - gia.gia_muc(None)          # job đầu: 1 mục thành công, không rõ thời lượng
    _dung_adapter(monkeypatch, AdapterGia(muc=[_muc("aaaaaaaaaaa")]))
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 1,
                                             "khong_trung": True}, phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    assert job.result["bo_qua_trung"] == 1 and job.result["video_keys"] == []
    assert job.result["credit_cost"] == 0
    assert "Không có video mới" in job.progress_msg
    ma = [e.event_code for e in job_events.timeline(db, job.id)]
    assert "bo_qua_trung" in ma
    assert _so_du(db, "u1") == con_lai                 # job 2: mọi mục trùng ⇒ giữ chỗ hoàn đủ, không đổi


# ── Review code 22/09 ─────────────────────────────────────────────────────────

_A = "a" * 11


def test_blocker_url_do_khach_gui_bi_bo_dung_lai_url_chuan():
    """BLOCKER: `url_<id>` lấy thẳng từ form ⇒ một id kèm URL playlist/kênh tải cả playlist với giá 1 credit.
    URL tải luôn dựng lại từ id theo mẫu của nền; URL khách gửi bị bỏ."""
    from apps.video_crawler import features
    p = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                 muc=[{"id": _A, "url": "https://www.youtube.com/playlist?list=PLxyz"}],
                                 phan_giai=_DNS)
    assert p["muc"][0]["url"] == f"https://www.youtube.com/watch?v={_A}"


@pytest.mark.parametrize("vid", ["..", "a/b", "short", "x" * 12, ""])
def test_id_sai_mau_bi_tu_choi(vid):
    from apps.video_crawler import features
    with pytest.raises(features.LoiDauVao):
        features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                 muc=[{"id": vid, "url": ""}], phan_giai=_DNS)


def test_id_trung_trong_mot_yeu_cau_chi_tinh_mot_lan():
    """MAJOR 2: `muc=X&muc=X` ⇒ tính giữ chỗ 2 lần cho 1 tệp."""
    from apps.video_crawler import features, gia
    from apps.video_crawler.manifest import MANIFEST
    p = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                 muc=[{"id": _A}, {"id": _A}], phan_giai=_DNS)
    assert [m["id"] for m in p["muc"]] == [_A]
    assert MANIFEST.credit_cost(p) == gia.GIA_GIU_CHO


def test_kham_pha_trung_id_chi_giu_mot(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features, gia
    adapter = AdapterGia(muc=[_muc(_A), _muc(_A), _muc("b" * 11)])
    _dung_adapter(monkeypatch, adapter)
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 3}, phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    job = _chay(db, job.id)
    assert adapter.da_tai == [_A, "b" * 11]
    assert job.result["credit_cost"] == 2 * gia.gia_muc(None)   # 2 mục tải thật, không rõ thời lượng


def test_muc_lay_tu_ket_qua_xem_truoc_cua_chinh_minh(db, kho, nguoi, monkeypatch):
    """Đường UI: khách chỉ gửi id đã tick; mục (url, tiêu đề) lấy từ kết quả xem trước của CHÍNH họ."""
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia(muc=[_muc(_A), _muc("b" * 11)]))
    p = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="tu_khoa", dau_vao="meo",
                                      so_luong=2, khong_trung=False, phan_giai=_DNS)
    kp = features.nop(db, owner_id="u1", job_type="video_crawler.kham_pha", params=p)
    db.commit()
    _chay(db, kp.id)
    params = features.dung_params_tai_tu_xem_truoc(db, owner_id="u1", kham_pha_id=kp.id, ids=["b" * 11, "z" * 11])
    assert [m["id"] for m in params["muc"]] == ["b" * 11]              # id không có trong kết quả bị bỏ
    assert params["muc"][0]["tieu_de"] == f"Video {'b' * 11}"
    with pytest.raises(features.LoiDauVao):                              # người khác không dùng được xem trước của u1
        features.dung_params_tai_tu_xem_truoc(db, owner_id="u2", kham_pha_id=kp.id, ids=["b" * 11])


class _CtxHuy:
    def __init__(self):
        self.goi_huy = 0
        self.huy = False

    def progress(self, p, msg=""):
        pass

    def is_cancelled(self):
        self.goi_huy += 1
        return self.huy


def test_tien_do_kiem_huy_theo_thoi_gian_khong_doi_buoc_5(monkeypatch):
    """MAJOR 4: chỉ biết huỷ ở bước 5% hoặc sau 30 s. Phải hỏi `is_cancelled` ~ mỗi 5 s kể cả khi % đứng yên."""
    from apps.video_crawler import jobs as vc_jobs
    from platform_core.job_runner import JobCancelled
    dong_ho = [1000.0]
    monkeypatch.setattr(vc_jobs.time, "monotonic", lambda: dong_ho[0])
    ctx = _CtxHuy()
    td = vc_jobs._TienDo(ctx, 1)
    td.bao(10, "")
    ctx.huy = True
    dong_ho[0] += 6
    with pytest.raises(JobCancelled):
        td.bao(10, "")                                                    # % không đổi, vẫn phát hiện huỷ


def test_het_ngan_sach_thoi_gian_thi_dung_giua_cac_muc_va_giu_phan_da_xong(db, kho, nguoi, monkeypatch):
    """MAJOR 5: `_het_gio` giết tiến trình ⇒ khối dọn không chạy. Handler tự dừng trước trần và kết thúc phần đã xong."""
    from apps.video_crawler import jobs as vc_jobs
    from platform_core.models import JOB_DONE
    dong_ho = [0.0]
    monkeypatch.setattr(vc_jobs.time, "monotonic", lambda: dong_ho[0])

    def sau_moi_muc(item):
        dong_ho[0] += vc_jobs.NGAN_SACH_TAI_S / 2 + 1

    from apps.video_crawler import gia
    _dung_adapter(monkeypatch, AdapterGia(truoc_tai=sau_moi_muc))
    job = _chay(db, _nop_tai(db, "u1", [_A, "b" * 11, "c" * 11]))
    assert job.status == JOB_DONE
    assert len(job.result["video_keys"]) == 2
    assert job.result["loi"][-1]["ma"] == "het_thoi_gian"
    assert job.result["credit_cost"] == 2 * gia.gia_muc(None)
    assert _so_du(db, "u1") == NAP_BAN_DAU - 2 * gia.gia_muc(None)


def test_gioi_han_tan_suat_tinh_ca_cao_het(db, kho, nguoi, monkeypatch):
    """MINOR: 'Cào hết' (tai + nguon) cũng khám phá miễn phí khi mọi mục trùng ⇒ phải chung trần tần suất."""
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia())
    for i in range(features.KHAM_PHA_MOI_PHUT):
        p = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                     nguon={"che_do": "tu_khoa", "dau_vao": f"meo {i}", "so_luong": 1},
                                     phan_giai=_DNS)
        features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=p)
        db.commit()
    with pytest.raises(features.QuaTanSuat):
        features.kiem_tan_suat(db, "u1")


# ── Giá theo thời lượng — L2 GIÁ (22/09) ───────────────────────────────────────


def test_doi_soat_gia_giu_bang_quyet_toan_cong_hoan_theo_thoi_luong_thuc(db, kho, nguoi, monkeypatch):
    """Đối soát giữ = quyết toán + hoàn, ba mục: ngắn (<=10 phút), dài (30-60 phút), không rõ thời lượng.
    Giữ chỗ khi nộp luôn bậc cao nhất; quyết toán theo `gia.gia_muc` của thời lượng THẬT từng mục đã tải
    (mục đến từ 'cào hết' giữ nguyên `CrawlItem.thoi_luong_s` của adapter, không bị features cắt bớt)."""
    from apps.video_crawler import features, gia
    from apps.video_crawler.manifest import MANIFEST
    from platform_core.models import JOB_DONE

    ngan, dai = 120, 3_000                       # <= 600s (bậc 3) · 1801-3600s, 30-60 phút (bậc 10)
    adapter = AdapterGia(muc=[_muc(_A, ngan), _muc("b" * 11, dai), _muc("c" * 11, None)])
    _dung_adapter(monkeypatch, adapter)
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 3},
                                      phan_giai=_DNS)
    giu = MANIFEST.credit_cost(params)
    assert giu == 3 * gia.GIA_GIU_CHO                # giữ chỗ luôn bậc cao nhất, không theo thời lượng
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    assert _so_du(db, "u1") == NAP_BAN_DAU - giu

    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    ky_vong = gia.gia_muc(ngan) + gia.gia_muc(dai) + gia.gia_muc(None)
    assert ky_vong == 3 + 10 + 3
    assert job.result["credit_cost"] == ky_vong
    assert _so_du(db, "u1") == NAP_BAN_DAU - ky_vong  # giữ chỗ dư so với quyết toán được hoàn lại đúng phần chênh
