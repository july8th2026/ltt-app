"""Ngưỡng vận hành phải RA KHỎI máy, không chỉ nằm trên một trang.

Q21 chốt "phải biết lỗi trước khi khách gọi điện". `metrics` đã đếm đúng thứ cần
đếm và trang Tổng quan đã hiện chúng — nhưng một con số trên một trang chỉ được
biết khi có người mở trang đó, và lúc 2 giờ sáng thì không ai mở.

Hai thứ được chốt ở đây, và chúng là hai loại lỗi khác nhau:

1. **quy tắc sườn** — quét định kỳ mà thấy đúng là gửi thì sẽ gửi mỗi lượt suốt
   sự cố, và một hộp thư 200 thư giống nhau bị lọc bỏ nhanh hơn hộp thư trống;
2. **cộng qua nhiều tiến trình** — số nằm trong `api_metric_samples` chứ không
   trong RAM của một tiến trình. Đây đúng là lớp lỗi H36 đã phải đi sửa một lần.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ops.db').as_posix()}")
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


def _dem(db, ten, gia_tri, *, cach_day_gio=0.1, process="worker:a"):
    """Ghi một mẫu đếm như thể một tiến trình đã xả nó."""
    from platform_core.public_api.tables import ApiMetricSample

    db.add(ApiMetricSample(
        id=str(uuid.uuid4()), process=process, kind="counter", name=ten,
        value=int(gia_tri), total_ms=0, max_ms=0,
        window_start=datetime.now(timezone.utc) - timedelta(hours=cach_day_gio)))
    db.flush()


def _do_tre(db, ten, *, count, total_ms, cach_day_gio=0.1, process="worker:a"):
    from platform_core.public_api.tables import ApiMetricSample

    db.add(ApiMetricSample(
        id=str(uuid.uuid4()), process=process, kind="latency", name=ten,
        value=int(count), total_ms=int(total_ms), max_ms=int(total_ms),
        window_start=datetime.now(timezone.utc) - timedelta(hours=cach_day_gio)))
    db.flush()


# ── Quy tắc sườn ─────────────────────────────────────────────────────────────

def test_vuot_nguong_lan_dau_thi_bao():
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    ra = ops_alerts.danh_gia(
        {"counters": {metrics.RESPONSES_5XX: nguong}, "latency": {}},
        {"counters": {}, "latency": {}})

    assert [d["ten"] for d in ra] == [metrics.RESPONSES_5XX]
    assert ra[0]["gia_tri"] == nguong


def test_van_dang_vuot_thi_KHONG_bao_lai():
    """Đây là lời hứa của module, và cũng là cái giá của nó.

    Một sự cố kéo dài chỉ gửi một thư. Test này chốt hành vi đó để không ai
    "sửa" nó thành gửi mỗi lượt mà không nhận ra mình vừa biến kênh cảnh báo
    thành kênh bị lọc bỏ.
    """
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    ra = ops_alerts.danh_gia(
        {"counters": {metrics.RESPONSES_5XX: nguong * 3}, "latency": {}},
        {"counters": {metrics.RESPONSES_5XX: nguong * 2}, "latency": {}})

    assert ra == []


def test_duoi_nguong_thi_im():
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    assert ops_alerts.danh_gia(
        {"counters": {metrics.RESPONSES_5XX: nguong - 1}, "latency": {}},
        {"counters": {}, "latency": {}}) == []


def test_cong_tac_ngat_bao_ngay_tu_lan_dau_tien():
    """Công tắc ngắt chỉ bật khi có người bật, nên MỘT lần đã đáng biết."""
    from platform_core.public_api import metrics, ops_alerts

    assert ops_alerts.NGUONG[metrics.KILL_SWITCH_REFUSED] == 1
    ra = ops_alerts.danh_gia(
        {"counters": {metrics.KILL_SWITCH_REFUSED: 1}, "latency": {}},
        {"counters": {}, "latency": {}})
    assert [d["ten"] for d in ra] == [metrics.KILL_SWITCH_REFUSED]


def test_hang_doi_nhat_viec_cham_thi_bao_theo_trung_binh():
    from platform_core.public_api import metrics, ops_alerts

    cham = ops_alerts.QUEUE_PICKUP_NGUONG_MS + 1_000
    ra = ops_alerts.danh_gia(
        {"counters": {}, "latency": {
            metrics.LATENCY_QUEUE_PICKUP: {"count": 4, "avg_ms": cham,
                                           "max_ms": cham}}},
        {"counters": {}, "latency": {}})
    assert [d["ten"] for d in ra] == [metrics.LATENCY_QUEUE_PICKUP]


def test_khong_co_mau_do_tre_thi_khong_bao():
    """`count == 0` nghĩa là chưa đo được gì, không phải là nhanh bằng 0."""
    from platform_core.public_api import metrics, ops_alerts

    assert ops_alerts.danh_gia(
        {"counters": {}, "latency": {
            metrics.LATENCY_QUEUE_PICKUP: {"count": 0, "avg_ms": 0.0,
                                           "max_ms": 0.0}}},
        {"counters": {}, "latency": {}}) == []


# ── Cộng qua nhiều tiến trình, đọc từ CSDL ───────────────────────────────────

def test_quet_cong_so_cua_NHIEU_tien_trinh(db):
    """Số của hai worker phải cộng lại mới chạm ngưỡng.

    Nếu chỗ này đọc `metrics.snapshot()` (trong tiến trình) thay vì
    `metrics.aggregate()` (trong CSDL) thì hai nửa sẽ không bao giờ gặp nhau và
    cảnh báo im lặng vĩnh viễn — đúng lớp lỗi của H36.
    """
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    _dem(db, metrics.RESPONSES_5XX, nguong - 1, process="worker:a")
    _dem(db, metrics.RESPONSES_5XX, 1, process="worker:b")

    assert [d["ten"] for d in ops_alerts.quet(db)] == [metrics.RESPONSES_5XX]


def test_quet_tru_dung_khoang_lang(db):
    """Số cũ nằm trong khoảng lặng phải làm tắt cảnh báo, không cộng dồn vào.

    Mẫu cũ đặt 3 giờ trước: nó nằm trong cửa sổ `IM_LANG_GIO` nhưng NGOÀI cửa sổ
    `CUA_SO_GIO`. Nếu phép trừ sai thì nó sẽ bị tính là "bây giờ" và cho một
    cảnh báo về chuyện đã cũ.
    """
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    _dem(db, metrics.RESPONSES_5XX, nguong, cach_day_gio=3)

    assert ops_alerts.quet(db) == []


def test_vuot_bay_gio_nhung_da_vuot_trong_khoang_lang_thi_im(db):
    from platform_core.public_api import metrics, ops_alerts

    nguong = ops_alerts.NGUONG[metrics.RESPONSES_5XX]
    _dem(db, metrics.RESPONSES_5XX, nguong, cach_day_gio=3)      # suon truoc
    _dem(db, metrics.RESPONSES_5XX, nguong, cach_day_gio=0.1)    # bay gio

    assert ops_alerts.quet(db) == []


def test_do_tre_tru_dung_khi_cong_hai_cua_so(db):
    """Trung bình của khoảng lặng phải dựng lại từ (count, total), không phải
    lấy trung bình của trung bình."""
    from platform_core.public_api import metrics, ops_alerts

    cham = ops_alerts.QUEUE_PICKUP_NGUONG_MS + 5_000
    # Khoang lang: nhanh. Bay gio: cham. Phai bao.
    _do_tre(db, metrics.LATENCY_QUEUE_PICKUP, count=10, total_ms=10 * 100,
            cach_day_gio=3)
    _do_tre(db, metrics.LATENCY_QUEUE_PICKUP, count=2, total_ms=int(2 * cham),
            cach_day_gio=0.1)

    assert [d["ten"] for d in ops_alerts.quet(db)] == [metrics.LATENCY_QUEUE_PICKUP]


# ── Gửi thư ──────────────────────────────────────────────────────────────────

class _HopThuGia:
    def __init__(self):
        self.sent = []

    def send(self, email):
        self.sent.append(email)


def test_vang_dia_chi_thi_tat_mem(db, monkeypatch):
    from platform_core.public_api import metrics, ops_alerts

    monkeypatch.delenv(ops_alerts.EMAIL_ENV, raising=False)
    _dem(db, metrics.RESPONSES_5XX, ops_alerts.NGUONG[metrics.RESPONSES_5XX])

    hop = _HopThuGia()
    assert ops_alerts.gui(db, mailer=hop) == 0
    assert hop.sent == []


def test_nhieu_nguong_vo_cung_luc_thi_gui_MOT_thu(db, monkeypatch):
    """Sáu thư cùng lúc buộc người trực tự ghép lại thứ ghép sẵn được."""
    from platform_core.public_api import metrics, ops_alerts

    monkeypatch.setenv(ops_alerts.EMAIL_ENV, "ops@example.com")
    _dem(db, metrics.RESPONSES_5XX, ops_alerts.NGUONG[metrics.RESPONSES_5XX])
    _dem(db, metrics.CAPACITY_REFUSED, ops_alerts.NGUONG[metrics.CAPACITY_REFUSED])

    hop = _HopThuGia()
    assert ops_alerts.gui(db, mailer=hop) == 2
    assert len(hop.sent) == 1
    assert metrics.RESPONSES_5XX in hop.sent[0].subject
    assert metrics.CAPACITY_REFUSED in hop.sent[0].subject
    # Than thu phai noi ro gioi han cua kenh, khong de nguoi truc tuong im lang
    # nghia la da het su co.
    assert "MOT thu" in hop.sent[0].text


def test_hop_thu_hong_khong_lam_sap_vong_bao_tri(db, monkeypatch):
    """Một kênh cảnh báo hỏng không được làm việc dọn dữ liệu ngừng chạy."""
    from platform_core.public_api import metrics, ops_alerts

    monkeypatch.setenv(ops_alerts.EMAIL_ENV, "ops@example.com")
    _dem(db, metrics.RESPONSES_5XX, ops_alerts.NGUONG[metrics.RESPONSES_5XX])

    class _Hong:
        def send(self, email):
            raise RuntimeError("SMTP chet")

    assert ops_alerts.gui(db, mailer=_Hong()) == 0      # khong nem ra ngoai


def test_khong_co_gi_vuot_thi_khong_gui(db, monkeypatch):
    from platform_core.public_api import ops_alerts

    monkeypatch.setenv(ops_alerts.EMAIL_ENV, "ops@example.com")
    hop = _HopThuGia()
    assert ops_alerts.gui(db, mailer=hop) == 0
    assert hop.sent == []


# ── Nối vào vòng bảo trì ─────────────────────────────────────────────────────

def test_duoc_goi_tu_vong_bao_tri_chu_khong_tu_vong_job():
    """Việc nền phải nằm sau lease bảo trì.

    Số tiến trình worker mặc định bằng số GPU; một việc nền chạy trong vòng job
    sẽ chạy ở MỌI tiến trình. Đó là nguyên nhân gốc của cả ba lỗi P0 mà H36 phải
    đi sửa, nên chốt lại bằng cấu trúc.
    """
    import inspect

    from platform_core import job_runner

    quet_src = inspect.getsource(job_runner._quet_canh_bao)
    assert "ops_alerts.gui(db)" in quet_src

    # `_quet_canh_bao` chi duoc goi tu vong bao tri.
    bao_tri_src = inspect.getsource(job_runner._mot_luot_bao_tri)
    assert "_quet_canh_bao()" in bao_tri_src
