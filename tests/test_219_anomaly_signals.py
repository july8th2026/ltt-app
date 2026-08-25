"""Ba câu hỏi mà dữ liệu đã trả lời được, và trước đây không ai hỏi.

Khu API chặn được thứ nó biết trước — SSRF, đọc chéo, giả mạo header, dò khoá.
Nhưng một khoá **bị lộ** thì gọi đúng scope, đúng nhịp, đúng tài khoản: nó không
chạm vào bất kỳ hàng rào nào cho tới khi hết tiền. Phòng thủ nhìn vào *luật*;
phần này nhìn vào *thói quen*.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'anomaly.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _request(db, *, user_id="u-1", key_id="k-1", status=200, credit=0,
             route="/api/v1/jobs", cach_day_gio=1.0):
    from platform_core.public_api.tables import ApiRequestLog

    db.add(ApiRequestLog(
        id=str(uuid.uuid4()), request_id=uuid.uuid4().hex, user_id=user_id,
        key_id=key_id, project_id="", method="POST", route=route,
        status=status, code="", latency_ms=10, tool="", job_id="",
        credit_delta=credit,
        created_at=datetime.now(timezone.utc) - timedelta(hours=cach_day_gio)))


def _su_kien(db, *, kind, key_id="k-1", ip="1.2.3.4", cach_day_gio=1.0):
    from platform_core.public_api.tables import ApiSecurityEvent

    db.add(ApiSecurityEvent(
        id=str(uuid.uuid4()), kind=kind, ip=ip, key_id=key_id, user_id="",
        route="/api/v1/jobs", request_id=uuid.uuid4().hex, detail="",
        created_at=datetime.now(timezone.utc) - timedelta(hours=cach_day_gio)))


# ── Thiếu quyền ──────────────────────────────────────────────────────────────

def test_mot_khoa_bi_tu_choi_nhieu_lan_thi_noi_ra(db):
    from platform_core.public_api import anomalies

    for _ in range(anomalies.SCOPE_DENIED_NGUONG + 5):
        _request(db, status=403)
    db.commit()

    ra = anomalies.scope_bi_tu_choi(db)
    assert len(ra) == 1 and ra[0]["key_id"] == "k-1"


def test_vai_lan_tu_choi_le_te_thi_im(db):
    """Ngưỡng tồn tại để trang này không thành một danh sách ai cũng có tên."""
    from platform_core.public_api import anomalies

    for _ in range(3):
        _request(db, status=403)
    db.commit()

    assert anomalies.scope_bi_tu_choi(db) == []


def test_dem_so_route_de_phan_biet_cau_hinh_sai_voi_do_tim(db):
    """Rất nhiều lỗi trên MỘT route là tích hợp cấu hình thiếu scope.

    Rải khắp nhiều route là ai đó đang xem khoá này với tới đâu. Cùng một tổng
    số, hai việc khác nhau, hai cách xử lý khác nhau.
    """
    from platform_core.public_api import anomalies

    for i in range(anomalies.SCOPE_DENIED_NGUONG + 1):
        _request(db, status=403, route=f"/api/v1/route-{i}")
    db.commit()

    assert anomalies.scope_bi_tu_choi(db)[0]["so_route"] > 1


def test_loi_khac_403_khong_bi_tinh(db):
    from platform_core.public_api import anomalies

    for _ in range(50):
        _request(db, status=500)
    db.commit()

    assert anomalies.scope_bi_tu_choi(db) == []


# ── Chi tiêu vọt ─────────────────────────────────────────────────────────────

def test_tieu_vot_han_so_voi_chinh_minh_thi_noi_ra(db):
    """So với **chính tài khoản đó**, không so với trung bình toàn hệ thống.

    Một khách lớn tiêu nhiều là bình thường; một khách nhỏ đột nhiên tiêu như
    khách lớn thì không — và trung bình toàn hệ thống làm mờ đúng sự khác biệt
    đó.
    """
    from platform_core.public_api import anomalies

    for ngay in range(1, 15):               # nền: 10 credit mỗi ngày
        _request(db, credit=10, cach_day_gio=24 * ngay + 1)
    for _ in range(20):                     # hôm nay: 400 credit
        _request(db, credit=20, cach_day_gio=0.5)
    db.commit()

    ra = anomalies.chi_tieu_vot(db)
    assert len(ra) == 1
    assert ra[0]["gap"] >= anomalies.CHI_TIEU_GAP


def test_khach_lon_tieu_deu_thi_khong_bi_bao(db):
    """Bất thường là **đổi thói quen**, không phải tiêu nhiều."""
    from platform_core.public_api import anomalies

    for ngay in range(1, 15):
        for _ in range(10):
            _request(db, credit=50, cach_day_gio=24 * ngay + 1)
    for _ in range(10):
        _request(db, credit=50, cach_day_gio=0.5)
    db.commit()

    assert anomalies.chi_tieu_vot(db) == []


def test_so_nho_thi_khong_bao_du_ty_le_cao(db):
    """Gấp 5 lần của một con số rất nhỏ vẫn là một con số rất nhỏ."""
    from platform_core.public_api import anomalies

    _request(db, credit=1, cach_day_gio=48)
    _request(db, credit=10, cach_day_gio=0.5)
    db.commit()

    assert anomalies.chi_tieu_vot(db) == []


def test_tai_khoan_moi_tieu_rat_lon_van_duoc_bao(db):
    """Im lặng hẳn với tài khoản mới nghĩa là khoá lộ ngay ngày đầu sẽ không ai thấy."""
    from platform_core.public_api import anomalies

    for _ in range(20):
        _request(db, credit=100, cach_day_gio=0.5)
    db.commit()

    ra = anomalies.chi_tieu_vot(db)
    assert len(ra) == 1 and ra[0]["gap"] is None


# ── Khoá đã thu hồi ──────────────────────────────────────────────────────────

def test_khoa_da_thu_hoi_van_bi_goi_thi_noi_ra(db):
    """Tín hiệu trực tiếp nhất về một credential đã ra ngoài.

    Khách thu hồi rồi mà vẫn có lời gọi nghĩa là thứ đang giữ khoá **không phải**
    hệ thống mà họ vừa cập nhật.
    """
    from platform_core.public_api import anomalies, security_log

    for _ in range(anomalies.KHOA_THU_HOI_NGUONG + 2):
        _su_kien(db, kind=security_log.REVOKED_KEY)
    db.commit()

    ra = anomalies.khoa_da_thu_hoi_van_bi_dung(db)
    assert len(ra) == 1 and ra[0]["key_id"] == "k-1"


def test_dem_dia_chi_vi_mot_may_khac_han_nhieu_may(db):
    from platform_core.public_api import anomalies, security_log

    for i in range(anomalies.KHOA_THU_HOI_NGUONG + 2):
        _su_kien(db, kind=security_log.REVOKED_KEY, ip=f"10.0.0.{i}")
    db.commit()

    assert anomalies.khoa_da_thu_hoi_van_bi_dung(db)[0]["so_ip"] > 1


def test_khoa_sai_binh_thuong_khong_bi_tinh_la_thu_hoi(db):
    """Gõ nhầm một khoá không phải dấu hiệu credential bị lộ."""
    from platform_core.public_api import anomalies, security_log

    for _ in range(20):
        _su_kien(db, kind=security_log.UNKNOWN_KEY)
    db.commit()

    assert anomalies.khoa_da_thu_hoi_van_bi_dung(db) == []


# ── Ranh giới ────────────────────────────────────────────────────────────────

def test_ngoai_cua_so_thoi_gian_thi_khong_tinh(db):
    from platform_core.public_api import anomalies

    for _ in range(50):
        _request(db, status=403, cach_day_gio=200)
    db.commit()

    assert anomalies.scope_bi_tu_choi(db, hours=24) == []


def test_chi_doc_khong_khoa_gi(db):
    """Cố ý chỉ báo cho người vận hành, không tự chặn.

    Một hệ tự khoá dựa trên suy đoán sẽ chặn nhầm khách thật vào đúng ngày họ
    chạy chiến dịch lớn — mất một khách vì nghi oan đắt hơn xử lý muộn vài giờ.
    """
    import inspect

    from platform_core.public_api import anomalies

    nguon = inspect.getsource(anomalies)
    for cam in ("db.add(", "db.delete(", "db.commit(", "revoke", "set_enabled"):
        assert cam not in nguon, f"module chỉ-đọc lại có {cam!r}"


def test_quet_tra_ve_du_ba_cau_hoi(db):
    from platform_core.public_api import anomalies

    ra = anomalies.quet(db)
    assert set(ra) == {"scope_bi_tu_choi", "chi_tieu_vot", "khoa_thu_hoi"}


# ── Ngữ nghĩa đường hỏng ─────────────────────────────────────────────────────

def test_moi_loi_noi_ro_co_thu_lai_duoc_khong():
    """Khách không phải tra bảng của ta mới biết nên làm gì tiếp.

    `error_registry` vẫn luôn biết đủ — lỗi này thử lại được không, và thử lại
    có phải dùng lại `Idempotency-Key` không. Thứ duy nhất khách nhận được lại
    chỉ là một mã lỗi, nên mỗi tích hợp phải tự đoán; đoán sai theo hướng "thử
    lại đi" là cách một lần gián đoạn thành hai lần tính tiền.
    """
    from platform_core.public_api import error_registry
    from platform_core.public_api.errors import ApiProblem

    for code, spec in error_registry.REGISTRY.items():
        body = ApiProblem(status=spec.status, code=code, detail="x").to_dict()
        assert body["retry"] == spec.retry, code
        if spec.reuse_idempotency_key:
            assert body["reuse_idempotency_key"] is True, code


def test_ma_la_khong_lam_hong_phan_hoi_loi():
    """Một mã chưa khai không được biến câu trả lời lỗi thành lỗi 500."""
    from platform_core.public_api.errors import ApiProblem

    body = ApiProblem(status=500, code="chua-khai-bao-gio", detail="x").to_dict()
    assert body["code"] == "chua-khai-bao-gio"
    assert "retry" not in body


def test_tai_lieu_noi_cach_doi_chieu_sau_su_co():
    """Recipe cho đường hỏng, không chỉ đường thuận."""
    import pathlib

    doc = (pathlib.Path(__file__).parent.parent / "docs" / "PUBLIC_API"
           / "RECIPES.md").read_text(encoding="utf-8")
    assert "Idempotency-Key" in doc
    assert "/usage" in doc
    assert "reuse_idempotency_key" in doc


def test_runbook_noi_phai_lam_gi_chu_khong_chi_xem_o_dau():
    """Một bảng điều khiển không dẫn tới hành động sẽ không được dùng."""
    import pathlib

    doc = (pathlib.Path(__file__).parent.parent / "docs" / "PUBLIC_API"
           / "RUNBOOK.md").read_text(encoding="utf-8")
    for muc in ("lease bảo trì", "LTT_WORKER_POOLS", "Tiến trình web",
                "kill switch", "Biết là đã hết chưa"):
        assert muc in doc, f"runbook thiếu: {muc}"
