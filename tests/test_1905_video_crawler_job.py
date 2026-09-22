"""
video_crawler — chuỗi job thật: nộp (giữ credit) → worker claim → handler → storage → result → quyết toán.

Chạy qua `job_runner._chay_mot_job` thật trên SQLite tạm (khuôn `test_67`). Chỉ adapter là giả, để test không
đọc mạng. Các mệnh đề chốt (spec §14, §17, §18, §19):
- tải xong N mục ⇒ N tệp trong storage `video_crawler/<owner>/<job>/<id>.mp4`, trừ đúng N credit;
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


def _muc(i: str) -> CrawlItem:
    return CrawlItem(nen_tang="youtube", id=i, url=f"https://www.youtube.com/watch?v={i}", tieu_de=f"Video {i}")


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
        credit.nap(db, uid, 100)
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


def test_tai_hai_muc_luu_storage_va_tru_dung_hai_credit(db, kho, nguoi, monkeypatch):
    from platform_core.models import JOB_DONE
    _dung_adapter(monkeypatch, AdapterGia())
    jid = _nop_tai(db, "u1", ["a", "b"])
    assert _so_du(db, "u1") == 98                       # giữ chỗ 2

    job = _chay(db, jid)
    assert job.status == JOB_DONE, job.error
    keys = job.result["video_keys"]
    assert keys == [f"video_crawler/u1/{jid}/a.mp4", f"video_crawler/u1/{jid}/b.mp4"]
    assert all(kho.exists(k) for k in keys)
    assert [m["id"] for m in job.result["muc"]] == ["a", "b"]
    assert not any(k.endswith("_key") for m in job.result["muc"] for k in m)   # spec §14: trần 20 artifacts
    assert _so_du(db, "u1") == 98                       # quyết toán = 2


def test_mot_phan_loi_thi_xong_va_hoan_phan_loi(db, kho, nguoi, monkeypatch):
    from platform_core.models import JOB_DONE
    _dung_adapter(monkeypatch, AdapterGia(loi={"b": LoiCao("rieng_tu", "Video riêng tư.", tam_thoi=False)}))
    jid = _nop_tai(db, "u1", ["a", "b"])
    job = _chay(db, jid)
    assert job.status == JOB_DONE
    assert job.result["video_keys"] == [f"video_crawler/u1/{jid}/a.mp4"]
    assert job.result["loi"] == [{"id": "b", "ma": "rieng_tu", "thong_diep": "Video riêng tư."}]
    assert _so_du(db, "u1") == 99


def test_moi_muc_loi_phia_khach_thi_error_khong_thu_lai_hoan_du(db, kho, nguoi, monkeypatch):
    from platform_core.models import JOB_ERROR
    loi = LoiCao("khong_ton_tai", "Video không còn tồn tại.", tam_thoi=False)
    _dung_adapter(monkeypatch, AdapterGia(loi={"a": loi, "b": loi}))
    jid = _nop_tai(db, "u1", ["a", "b"])
    job = _chay(db, jid)
    assert job.status == JOB_ERROR
    assert job.attempts == 1                            # LoiNguoiGoi: không thử lại
    assert _so_du(db, "u1") == 100
    assert not kho.exists(f"video_crawler/u1/{jid}/a.mp4")


def test_huy_giua_chung_thi_cancelled_va_don_tep(db, kho, nguoi, monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.db import get_session
    from platform_core.models import JOB_CANCELLED, Job

    jid_holder = {}

    def huy_truoc_muc_b(item):
        if item.id != "b":
            return
        gen = get_session(); s = next(gen)
        try:
            assert jobq.cancel(s, s.get(Job, jid_holder["id"]))
            s.commit()
        finally:
            s.close()

    _dung_adapter(monkeypatch, AdapterGia(truoc_tai=huy_truoc_muc_b))
    jid_holder["id"] = jid = _nop_tai(db, "u1", ["a", "b"])
    job = _chay(db, jid)
    assert job.status == JOB_CANCELLED
    assert not kho.exists(f"video_crawler/u1/{jid}/a.mp4")   # tệp mục a đã lưu phải bị dọn
    assert _so_du(db, "u1") == 100


def test_khong_trung_chi_bo_muc_chinh_user_da_tai(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    from platform_core.models import JOB_DONE

    _dung_adapter(monkeypatch, AdapterGia())
    _chay(db, _nop_tai(db, "u1", ["a"]))                 # u1 đã có "a"
    _chay(db, _nop_tai(db, "u2", ["b"]))                 # u2 có "b" — không được ảnh hưởng u1

    adapter = AdapterGia(muc=[_muc("a"), _muc("b"), _muc("c")])
    _dung_adapter(monkeypatch, adapter)
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 3,
                                             "khong_trung": True},
                                      phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    assert adapter.da_tai == ["b", "c"]
    assert job.result["bo_qua_trung"] == 1


def test_kham_pha_mien_phi_tra_danh_sach(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    from platform_core.models import JOB_DONE

    _dung_adapter(monkeypatch, AdapterGia(muc=[_muc("a"), _muc("b")]))
    params = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="tu_khoa",
                                           dau_vao="meo", so_luong=5, khong_trung=False, phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.kham_pha", params=params)
    db.commit()
    assert _so_du(db, "u1") == 100
    job = _chay(db, job.id)
    assert job.status == JOB_DONE
    assert [m["id"] for m in job.result["muc"]] == ["a", "b"]
    assert "video_keys" not in job.result
    assert _so_du(db, "u1") == 100


def test_lich_su_chi_thay_job_cua_minh(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    _dung_adapter(monkeypatch, AdapterGia())
    a = _nop_tai(db, "u1", ["a"])
    _nop_tai(db, "u2", ["b"])
    assert [j.id for j in features.lich_su(db, "u1")] == [a]


@pytest.mark.parametrize("sai", [
    dict(nen_tang="douyin", che_do="tu_khoa", dau_vao="meo", so_luong=5),     # nền chưa bật
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
    a = _nop_tai(db, "u1", ["a"])
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
