"""H39 — hoàn tiền cho máy chưa từng chạy được, và mốc ảnh chụp không nói dối.

## Lỗ hổng này có thật và nó im lặng

`routes.tao_may` trừ credit **trước** khi nộp job — đúng, vì không trừ trước thì
người hết tiền vẫn chiếm được chỗ. Nhưng khi job dựng máy hỏng (Vultr cạn hạn
ngạch IP, Proxmox không trả lời, kho đầy), máy vào trạng thái `loi` và **không ai
hoàn lại chu kỳ đã thu**.

Khách trả 149.000–329.000đ và nhận một dòng chữ "Lỗi". Không log nào báo, không
ai quét. Đúng lớp lỗi phiên Public API vừa tìm ra ở cửa `/messages`, chỉ khác
đường đi — và cả hai đều là *tiền đã trừ, dịch vụ không giao*.

Đã chứng minh xảy ra được: 24/08 một lượt tạo thật hỏng ở mốc 92 % vì hạn ngạch
Reserved IP của Vultr đã cạn.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.vps import bao_tri
from apps.vps.services import billing
from apps.vps.tables import VpsEvent, VpsInstance


@pytest.fixture()
def db():
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401

    e = create_engine("sqlite://")
    dbmod.Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


def _khach(db, so_du: int = 0) -> str:
    from platform_core import credit
    from platform_core.models import User

    u = User(email="k@x.test", email_chuan="k@x.test", display_name="k",
             password_hash="x", role="user", is_active=True, is_verified=True,
             registration_ip="127.0.0.1")
    db.add(u)
    db.commit()
    if so_du:
        credit.nap(db, u.id, so_du, note="thu")
        db.commit()
    return u.id


def _may_hong(db, user_id, *, da_thu=1490, da_chay=False, da_hoan=False):
    m = VpsInstance(user_id=user_id, plan_id="vps-nho", os_id="winsrv2022-core",
                    gateway_id="gw1", trang_thai="loi", ly_do="VultrError: het IP")
    db.add(m)
    db.flush()
    if da_thu:
        db.add(VpsEvent(instance_id=m.id, loai="thu_phi", boi="he_thong",
                        chi_tiet={"credit": da_thu}))
    if da_chay:
        db.add(VpsEvent(instance_id=m.id, loai="tao_xong", boi="he_thong",
                        chi_tiet={"vmid": 200}))
    if da_hoan:
        db.add(VpsEvent(instance_id=m.id, loai="hoan_tien", boi="he_thong",
                        chi_tiet={"credit": da_thu}))
    db.commit()
    return m


@pytest.fixture(autouse=True)
def _khong_nop_job(monkeypatch):
    """Job xoá đi qua hàng đợi thật; test này kiểm phần TIỀN."""
    monkeypatch.setattr(bao_tri, "_nop_job_xoa", lambda db, may: True)


# ── 1. Trường hợp chính ─────────────────────────────────────────────────────

def test_may_chua_tung_chay_thi_DUOC_HOAN(db):
    from platform_core import credit

    uid = _khach(db)
    _may_hong(db, uid, da_thu=1490)
    assert credit.so_du(db, uid) == 0

    assert bao_tri._hoan_may_tao_hong(db) == 1
    assert credit.so_du(db, uid) == 1490, "khach phai nhan lai dung so da tra"


def test_hoan_dung_KIND_cua_khoan_da_tru(db):
    """Hoàn bằng `nap()` sẽ ghi `kind=topup` — doanh thu nạp bị thổi lên đúng
    bằng số tiền trả lại, và mọi đối soát sau đó lệch."""
    from platform_core.models import CreditEntry

    uid = _khach(db)
    _may_hong(db, uid, da_thu=1790)
    bao_tri._hoan_may_tao_hong(db)

    dong = db.execute(select(CreditEntry)
                      .where(CreditEntry.delta > 0)).scalars().all()
    assert [d.kind for d in dong] == [billing.KIND]
    assert sum(d.delta for d in db.execute(
        select(CreditEntry).where(CreditEntry.kind == billing.KIND)).scalars()) == 1790


def test_ghi_su_kien_hoan_tien_de_truy_lai_duoc(db):
    uid = _khach(db)
    m = _may_hong(db, uid)
    bao_tri._hoan_may_tao_hong(db)
    loai = [e.loai for e in db.execute(
        select(VpsEvent).where(VpsEvent.instance_id == m.id)).scalars()]
    assert "hoan_tien" in loai


# ── 2. Ba trường hợp KHÔNG được hoàn ────────────────────────────────────────

def test_may_DA_TUNG_chay_thi_KHONG_hoan(db):
    """Máy chạy được rồi hỏng là chuyện khác: best effort, không SLA, và điều
    khoản nói rõ chu kỳ đã bắt đầu thì không hoàn."""
    from platform_core import credit

    uid = _khach(db)
    _may_hong(db, uid, da_chay=True)
    assert bao_tri._hoan_may_tao_hong(db) == 0
    assert credit.so_du(db, uid) == 0


def test_KHONG_hoan_hai_lan(db):
    """Vòng chạy mỗi giờ. Không có mốc chặn thì một máy hỏng thành một máy in
    tiền — 24 lần mỗi ngày."""
    from platform_core import credit

    uid = _khach(db)
    _may_hong(db, uid, da_thu=1490)
    assert bao_tri._hoan_may_tao_hong(db) == 1
    assert bao_tri._hoan_may_tao_hong(db) == 0, "lan hai phai bi chan"
    assert credit.so_du(db, uid) == 1490


def test_chua_thu_gi_thi_khong_co_gi_de_hoan(db):
    from platform_core import credit

    uid = _khach(db)
    _may_hong(db, uid, da_thu=0)
    assert bao_tri._hoan_may_tao_hong(db) == 0
    assert credit.so_du(db, uid) == 0


def test_may_dang_chay_binh_thuong_khong_bi_dung_toi(db):
    from platform_core import credit

    uid = _khach(db)
    m = VpsInstance(user_id=uid, plan_id="vps-nho", os_id="winsrv2022-core",
                    gateway_id="gw1", trang_thai="dang_chay", vmid=200)
    db.add(m)
    db.commit()
    assert bao_tri._hoan_may_tao_hong(db) == 0
    assert credit.so_du(db, uid) == 0


# ── 3. Máy hỏng phải được DỌN, không chỉ hoàn tiền ──────────────────────────

def test_hoan_tien_xong_thi_NOP_JOB_XOA(db, monkeypatch):
    """Máy hỏng vẫn có thể đang giữ một VM dở trên Proxmox, một địa chỉ trong
    mạng riêng, và một IP đang tính tiền. Hoàn tiền mà không dọn là trả lại tiền
    rồi vẫn tiếp tục trả $3/tháng cho địa chỉ của nó."""
    da_nop = []
    monkeypatch.setattr(bao_tri, "_nop_job_xoa",
                        lambda d, may: da_nop.append(may.id) or True)
    uid = _khach(db)
    m = _may_hong(db, uid)
    bao_tri._hoan_may_tao_hong(db)
    assert da_nop == [m.id]


def test_nop_job_xoa_hong_thi_TIEN_VAN_DA_HOAN(db, monkeypatch):
    """Hoàn tiền là thứ khách quan tâm; dọn dẹp là việc của ta. Một lỗi ở việc
    của ta không được nuốt mất việc của khách."""
    from platform_core import credit

    def no(db_, may):
        raise RuntimeError("hang doi hong")

    monkeypatch.setattr(bao_tri, "_nop_job_xoa", no)
    uid = _khach(db)
    _may_hong(db, uid, da_thu=1490)
    assert bao_tri._hoan_may_tao_hong(db) == 1
    db.commit()
    assert credit.so_du(db, uid) == 1490


# ── 4. `hoan_phi` là nửa còn thiếu của `tru` ────────────────────────────────

def test_hoan_phi_KHONG_ghi_nham_thanh_nap(db):
    from platform_core import credit
    from platform_core.credit import CREDIT_TOPUP
    from platform_core.models import CreditEntry

    uid = _khach(db)
    credit.hoan_phi(db, uid, 500, kind="vps_thang", note="thu")
    db.commit()
    kinds = {e.kind for e in db.execute(select(CreditEntry)).scalars()}
    assert CREDIT_TOPUP not in kinds


def test_hoan_phi_tu_choi_user_khong_ton_tai(db):
    from platform_core import credit

    with pytest.raises(credit.NguoiDungKhongTonTai):
        credit.hoan_phi(db, "khong-co-ai", 100, kind="vps_thang")


# ── 5. Mốc ảnh chụp không được nói dối ──────────────────────────────────────

def test_cai_lai_va_xoa_deu_XOA_moc_anh_chup():
    """Xoá VM là xoá luôn mọi ảnh chụp của nó. Không xoá mốc thì trang máy khoe
    "Ảnh chụp gần nhất: <ngày>" cho một bản **không còn tồn tại**, và nút Khôi
    phục hiện ra rồi báo "chưa có ảnh chụp nào" khi bấm."""
    import inspect

    from apps.vps import jobs

    for ham in (jobs._dung_lai, jobs._xoa_may):
        assert "sao_luu_luc = None" in inspect.getsource(ham), ham.__name__
