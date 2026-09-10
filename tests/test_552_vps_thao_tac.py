"""VPS V2 Pha 02 — thao tác bền: chống bấm hai lần, nối lại, và phục hồi sau sập.

Ba mệnh đề, và cả ba chỉ chứng minh được bằng CSDL thật (ràng buộc duy nhất là
trọng tài, không phải một câu `if`):

1. cùng một cú bấm hai lần ⇒ **một** thao tác;
2. máy đang bận ⇒ thao tác thứ hai bị từ chối **kèm lý do**, không im lặng;
3. worker chết giữa chừng ⇒ có đường mở khoá, và nó **không** kết luận là thất bại.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import trang_thai_may as tt
from apps.vps.services import thao_tac

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


_DEM_MAY = [0]


def _may(db, *, trang_thai="dang_chay"):
    """Một máy thật trong CSDL. `vmid` và tên cổng phải DUY NHẤT mỗi lần gọi.

    `uq_vps_instance_vmid` là thật, nên ghi cứng `vmid=200` làm mọi ca cần hai
    máy chết vì một ràng buộc chẳng liên quan gì tới thứ đang kiểm.
    """
    from apps.vps.tables import VpsGateway, VpsInstance
    _DEM_MAY[0] += 1
    n = _DEM_MAY[0]
    g = VpsGateway(ten=f"cong-{n}", vung="sgp", ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai=trang_thai, vmid=200 + n)
    db.add(m)
    db.flush()
    return m


# ── 1. Chống bấm hai lần ─────────────────────────────────────────────────────

def test_cung_khoa_idem_tra_ve_cung_mot_thao_tac(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", khoa_idem="k1", now=NOW)
    b = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", khoa_idem="k1", now=NOW)
    assert a.id == b.id


def test_khoa_idem_la_rang_buoc_CSDL_chu_khong_phai_mot_cau_if(db):
    """Trọng tài phải là ràng buộc duy nhất, không phải phép hỏi-rồi-ghi.

    Giữa lúc hỏi và lúc ghi có một khoảng, và hai request của cùng một cú bấm đúp
    lọt qua khoảng đó cùng lúc. Ca này chứng minh hàng rào thật sự nằm ở CSDL:
    INSERT thẳng một dòng trùng khoá phải chết.
    """
    from sqlalchemy.exc import IntegrityError
    from apps.vps.tables import VpsThaoTac

    may = _may(db)
    thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", khoa_idem="k1", now=NOW)
    db.add(VpsThaoTac(instance_id=may.id, loai=tt.DANG_TAT, boi="u1",
                      khoa_idem="k1", tao_luc=NOW))
    with pytest.raises(IntegrityError):
        db.flush()


def test_khoa_idem_chi_trung_trong_pham_vi_MOT_may(db):
    """Hai máy khác nhau cùng khoá `k1` là chuyện bình thường.

    Khoá idempotency sinh từ (hành động + phút), nên hai khách bấm cùng lúc trên
    hai máy sẽ có cùng chuỗi. Ràng buộc phải gồm `instance_id`, nếu không cú bấm
    của người này nuốt mất cú bấm của người kia.
    """
    m1, m2 = _may(db), _may(db, trang_thai="da_tat")
    a = thao_tac.mo(db, m1, tt.DANG_BAT, boi="u1", khoa_idem="k1", now=NOW)
    b = thao_tac.mo(db, m2, tt.DANG_BAT, boi="u1", khoa_idem="k1", now=NOW)
    assert a.id != b.id


# ── 2. Máy đang bận ──────────────────────────────────────────────────────────

def test_may_dang_ban_thi_thao_tac_thu_hai_bi_tu_choi_kem_ly_do(db):
    """V-07: khách bấm "Khôi phục" trong lúc job cài lại đang chạy.

    Từ chối là đúng — nhưng phải kèm **cái gì** đang chạy. Một câu "bận" không
    có lý do là thứ khách sẽ bấm lại năm lần.
    """
    may = _may(db)
    dang = thao_tac.mo(db, may, tt.DANG_DUNG_LAI, boi="u1", now=NOW)
    with pytest.raises(thao_tac.DangBanError) as loi:
        thao_tac.mo(db, may, tt.DANG_KHOI_PHUC, boi="u1", now=NOW)
    assert loi.value.dang_chay.id == dang.id
    assert tt.DANG_DUNG_LAI in str(loi.value)


def test_thao_tac_da_ket_thuc_khong_con_chiem_may(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_TAT, boi="u1", now=NOW)
    thao_tac.xong(db, a, may, dien_sau=tt.TAT, now=NOW)
    assert thao_tac.dang_mo(db, may.id) is None
    assert thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW).id != a.id


def test_mo_dat_co_tac_vu_len_may(db):
    """Máy phải biết nó đang bận NGAY, không đợi worker nhặt được job.

    Khoảng giữa "khách bấm" và "worker bắt đầu" là chỗ cú bấm thứ hai lọt qua.
    """
    may = _may(db)
    thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW)
    assert may.tac_vu == tt.DANG_KD_LAI and tt.dang_ban(may) is True


def test_mo_KHONG_doi_quan_sat_dien(db):
    """Mở một thao tác tắt máy không được làm máy "đã tắt".

    Đây chính xác là lỗi V-02 ở dạng nguyên bản của nó.
    """
    may = _may(db)
    thao_tac.mo(db, may, tt.DANG_TAT, boi="u1", now=NOW)
    assert may.trang_thai == "dang_chay"


def test_loai_thao_tac_la_bi_tu_choi(db):
    may = _may(db)
    with pytest.raises(ValueError):
        thao_tac.mo(db, may, "dang_bay", boi="u1", now=NOW)
    with pytest.raises(ValueError):
        thao_tac.mo(db, may, "", boi="u1", now=NOW)


# ── 3. Nối lại sau khi tiến trình chết ───────────────────────────────────────

def test_upid_cong_don_chu_khong_ghi_de(db):
    """Một lần khởi động lại sinh HAI upid (tắt rồi bật).

    Giữ lại cái cuối là mất đúng đường nối lại vào tác vụ đầu khi tiến trình chết
    giữa hai bước — tức mất đúng thứ cột này sinh ra để giữ.
    """
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW)
    thao_tac.ghi_upid(db, a, "UPID:pve:tat:1")
    thao_tac.ghi_upid(db, a, "UPID:pve:bat:2")
    assert a.upid.splitlines() == ["UPID:pve:tat:1", "UPID:pve:bat:2"]
    assert thao_tac.upid_cuoi(a) == "UPID:pve:bat:2"


def test_ghi_lai_cung_upid_khong_nhan_doi(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW)
    thao_tac.ghi_upid(db, a, "UPID:x")
    thao_tac.ghi_upid(db, a, "UPID:x")
    assert a.upid == "UPID:x"


def test_lan_thu_tang_moi_lan_worker_nhat_lai(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW)
    thao_tac.bat_dau(db, a, now=NOW)
    thao_tac.bat_dau(db, a, now=NOW)
    assert a.lan_thu == 2


# ── 4. Phục hồi sau khi worker chết ──────────────────────────────────────────

def test_thao_tac_qua_han_duoc_don_va_may_dung_lai_duoc(db):
    """Worker bị kill ⇒ không ai gọi `xong()`. Không có vòng dọn thì máy khoá mềm VĨNH VIỄN.

    Khách không bấm được gì và không ai biết vì sao — loại hỏng im lặng tệ nhất,
    vì nó trông giống một giao diện đang tải.
    """
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW,
                    han=timedelta(minutes=5))
    thao_tac.bat_dau(db, a, now=NOW)
    db.flush()

    da_dong = thao_tac.don_qua_han(db, now=NOW + timedelta(minutes=6))
    assert [x.id for x in da_dong] == [a.id]
    assert a.tinh_trang == thao_tac.QUA_HAN
    assert tt.dang_ban(may) is False, "may phai dung lai duoc"


def test_qua_han_KHONG_bi_ghi_thanh_hong(db):
    """Quá hạn ≠ thất bại. Ghi thành `hong` là mời người ta làm lại một việc đang chạy.

    Với một lần khôi phục ảnh chụp thì "làm lại" nghĩa là hai lần rollback chồng
    lên nhau.
    """
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_KHOI_PHUC, boi="u1", now=NOW,
                    han=timedelta(minutes=1))
    thao_tac.don_qua_han(db, now=NOW + timedelta(minutes=2))
    assert a.tinh_trang == thao_tac.QUA_HAN != thao_tac.HONG
    assert a.ma_loi == "tac_vu_qua_han"


def test_qua_han_dat_quan_sat_ve_khong_ro_chu_khong_doan(db):
    """Ta KHÔNG biết việc đó xong hay chưa, và đoán theo hướng nào cũng là bịa."""
    may = _may(db)
    thao_tac.mo(db, may, tt.DANG_TAT, boi="u1", now=NOW, han=timedelta(minutes=1))
    thao_tac.don_qua_han(db, now=NOW + timedelta(minutes=2))
    assert may.dien_quan_sat == tt.KHONG_RO and may.suc_khoe == tt.KHONG_RO


def test_thao_tac_chua_qua_han_khong_bi_dong(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW,
                    han=timedelta(minutes=30))
    assert thao_tac.don_qua_han(db, now=NOW + timedelta(minutes=5)) == []
    assert a.tinh_trang == thao_tac.CHO


def test_han_mac_dinh_dai_hon_tran_job_dai_nhat():
    """Hạn thao tác phải DÀI hơn `max_runtime_s` lớn nhất.

    Ngắn hơn thì vòng dọn đánh dấu `qua_han` cho một job **vẫn đang chạy đúng
    luật**, và khách nhận một thông báo lỗi cho một việc sắp xong — rồi bấm lại.
    """
    from apps.vps.manifest import MANIFEST
    assert thao_tac.HAN_MAC_DINH.total_seconds() > max(
        MANIFEST.max_runtime_s.values())


# ── 5. Kết thúc thất bại vẫn phải mở khoá ────────────────────────────────────

def test_hong_van_go_co_tac_vu(db):
    """Để nguyên cờ tác vụ trên một máy đang lỗi là lấy mất đúng nút "Cài lại"."""
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW)
    thao_tac.hong(db, a, may, ma_loi="tac_vu_that_bai", chi_tiet="x", now=NOW)
    assert tt.dang_ban(may) is False and a.ma_loi == "tac_vu_that_bai"


def test_ma_loi_la_MA_chu_khong_phai_mot_cau(db):
    """Mã thì đếm được và cảnh báo được; một câu tiếng Anh thì không.

    Cột `String(32)` là ràng buộc cơ học cho điều đó — nhét cả một thông điệp
    vào sẽ bị cắt, và một mã bị cắt cụt lộ ra ngay ở lần đếm đầu tiên.
    """
    from apps.vps.tables import VpsThaoTac
    cot = VpsThaoTac.__table__.c["ma_loi"]
    assert cot.type.length <= 32


def test_moi_ma_loi_cua_bo_cho_deu_vua_cot(db):
    """Mã lỗi mà bộ chờ sinh ra phải lưu được nguyên vẹn.

    Nối hai tầng bằng một chuỗi thì tầng dưới nới dài mã là tầng trên cắt cụt nó
    — im lặng, và chỉ lộ ra khi có người đi đếm cảnh báo.
    """
    from apps.vps.services import tac_vu
    from apps.vps.tables import VpsThaoTac
    tran = VpsThaoTac.__table__.c["ma_loi"].type.length
    for lop in (tac_vu.TacVuLoi, tac_vu.TacVuThatBai, tac_vu.TacVuQuaHan,
                tac_vu.KhongDocDuoc, tac_vu.DienKhongDat):
        assert len(lop.ma) <= tran, lop.__name__
