"""VPS V2 Pha 05 — đối chiếu V2, mạng và sổ sách: nhất quán giữa các hệ ngoài.

Ba nhóm mệnh đề:

1. **Phân loại.** Một danh sách phẳng "mồ côi" mời người đọc xử lý sai. Một
   đường NAT không có trong sổ là **lỗ hổng bảo mật**; một Reserved IP thừa là
   **tiền**; một VM đang được job khác dựng dở **trông y hệt** rác. Ba thứ đó
   không được nằm cùng một mức.
2. **Không tự xử thứ mơ hồ.** Vòng đối chiếu ghi lại phép đo (vô hại) nhưng
   không bao giờ xoá (không đảo được).
3. **Phục hồi sau khi worker chết.** Thao tác quá hạn phải được đóng, nếu không
   máy khoá mềm vĩnh viễn.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import doi_chieu, trang_thai_may as tt
from tests.fixtures.vps_proxmox_gia import ProxmoxGia

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


_DEM = [0]


def _may(db, *, vmid=200, trang_thai="dang_chay", muon=tt.CHAY):
    from apps.vps.tables import VpsGateway, VpsInstance
    _DEM[0] += 1
    g = VpsGateway(ten=f"cong-{_DEM[0]}", vung="sgp",
                   ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai=trang_thai, vmid=vmid)
    tt.dat(m, dien_mong_muon=muon)
    db.add(m)
    db.flush()
    return m


@pytest.fixture(autouse=True)
def _khong_co_he_ngoai(monkeypatch):
    """Router / gateway / Vultr không nối được — vòng quét vẫn phải chạy.

    Một nguồn im lặng **không** được làm mất kết quả của các nguồn khác: người
    chạy phép này thường đang tìm một sự cố, và mất nửa báo cáo là mất đúng nửa
    họ cần.
    """
    from apps.vps.services import gateway, router, vultr

    def _hong(*a, **kw):
        raise RuntimeError("chua cau hinh")

    for mod in (router, gateway, vultr):
        monkeypatch.setattr(mod, "client_tu_moi_truong", _hong)


# ── 1. Phân loại ────────────────────────────────────────────────────────────

def test_moi_phat_hien_deu_co_muc_do_hop_le(db):
    px = ProxmoxGia(vmid=999)                 # VM trên node không có trong CSDL
    _may(db, vmid=200)
    kq = doi_chieu.quet(db, px)
    assert kq.lech, "phai tim ra it nhat mot lech"
    for x in kq.lech:
        assert x.muc_do in doi_chieu.MUC_DO, x


def test_may_trong_CSDL_khong_co_VM_la_VO_BAT_BIEN_chu_khong_phai_nghi_ngo():
    """Máy **đang thu tiền** mà không có thực thể nào đằng sau.

    Không có gì để "nghi" cả: sổ sách đang sai, và nó sai về phía thu tiền của
    khách. Xếp nó chung mức với một mảnh rác là mời người đọc bỏ qua.
    """
    nhan = "May trong CSDL khong co VM"
    # Đọc thẳng bảng phân loại trong mã sản phẩm, không dựng lại một bản sao.
    import inspect
    nguon = inspect.getsource(doi_chieu.quet)
    i = nguon.index(nhan)
    assert "VO_BAT_BIEN" in nguon[i:i + 400], (
        f"{nhan!r} phai la VO_BAT_BIEN")


def test_duong_NAT_mo_coi_la_VO_BAT_BIEN():
    """Gói từ Internet vẫn được dẫn vào mạng riêng — đó là lỗ hổng, không phải rác."""
    import inspect
    nguon = inspect.getsource(doi_chieu.quet)
    i = nguon.index("Duong NAT khong co trong CSDL")
    assert "VO_BAT_BIEN" in nguon[i:i + 300]


def test_can_nguoi_xu_KHONG_dem_nhung_thu_tu_xu_duoc(db):
    """Con số đáng báo động là con số **không** tự xử được.

    Gộp cả hai vào một tổng thì một hệ khoẻ mạnh có mười máy lệch điện tạm thời
    trông y hệt một hệ có mười VM mồ côi.
    """
    px = ProxmoxGia(vmid=200, dien="stopped")
    _may(db, vmid=200, muon=tt.CHAY)          # muốn chạy, thực tế tắt
    kq = doi_chieu.quet(db, px)
    lech_dien = kq.theo_muc(doi_chieu.THU_LAI_DUOC)
    assert lech_dien, "phai bao lech dien"
    assert kq.can_nguoi_xu == 0, "lech dien tu xu duoc, khong duoc dem vao"


def test_mac_dinh_cua_mot_phat_hien_la_phia_AN_TOAN():
    """Quên khai mức ⇒ rơi vào `NGHI_MO_COI`, không rơi vào "tự xử được".

    Mặc định sai hướng là mặc định sẽ tự xoá một thứ không ai định xoá.
    """
    x = doi_chieu.LechLac("thu gi do", (1,), "hau qua")
    assert x.muc_do == doi_chieu.NGHI_MO_COI
    assert x.muc_do in doi_chieu.CAM_TU_XU


# ── 2. Đo điện thật, và không tự xử thứ mơ hồ ───────────────────────────────

def test_quet_ghi_lai_phep_do_dien_that(db):
    """Không có bước này thì `dien_quan_sat` chỉ đổi khi ai đó bấm một nút.

    Một máy không ai dùng tới trong ba tháng mang một phép đo từ ba tháng trước,
    và `qua_cu()` không phân biệt được "máy khoẻ" với "máy chết từ lâu".
    """
    px = ProxmoxGia(vmid=200, dien="running")
    may = _may(db, vmid=200, trang_thai="da_tat", muon=tt.TAT)
    assert may.quan_sat_luc is None
    kq = doi_chieu.quet(db, px)
    assert kq.da_do_dien == 1
    assert may.dien_quan_sat == tt.CHAY and may.quan_sat_luc is not None
    assert tt.qua_cu(may) is False


def test_khong_hoi_duoc_thi_ghi_KHONG_RO_chu_khong_bao_lech(db):
    """Biến một sự cố MẠNG thành một sự cố CẤU HÌNH là đẩy người đọc đi sai chỗ."""
    px = ProxmoxGia(vmid=777)                 # hỏi VM 200 sẽ trượt
    may = _may(db, vmid=200, muon=tt.CHAY)
    kq = doi_chieu.quet(db, px)
    assert may.dien_quan_sat == tt.KHONG_RO
    assert may.suc_khoe == tt.MAT_LIEN_LAC
    assert kq.theo_muc(doi_chieu.THU_LAI_DUOC) == []


def test_may_DANG_BAN_khong_bi_bao_lech_dien(db):
    """Máy đang có thao tác chạy dở thì lệch là chuyện bình thường — nó đang đổi.

    Báo nó là "lệch" mỗi giờ là dạy người đọc bỏ qua báo cáo này.
    """
    px = ProxmoxGia(vmid=200, dien="running")
    may = _may(db, vmid=200, muon=tt.TAT)
    tt.bat_dau_tac_vu(may, tt.DANG_TAT)
    db.flush()
    kq = doi_chieu.quet(db, px)
    assert kq.theo_muc(doi_chieu.THU_LAI_DUOC) == []


def test_quet_KHONG_xoa_gi_ca(db):
    """Một phép đối chiếu sai mà tự xoá thì xoá đúng thứ nó hiểu nhầm."""
    px = ProxmoxGia(vmid=999)
    may = _may(db, vmid=200)
    doi_chieu.quet(db, px)
    assert "xoa" not in px.da_goi
    from apps.vps.tables import VpsInstance
    assert db.get(VpsInstance, may.id) is not None


# ── 3. Phục hồi sau khi worker chết ─────────────────────────────────────────

def test_bao_tri_dong_thao_tac_qua_han(db, monkeypatch):
    """Không có vòng dọn thì máy khoá mềm **vĩnh viễn** sau một lần worker bị kill."""
    from apps.vps import bao_tri
    from apps.vps.services import thao_tac

    may = _may(db)
    op = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW,
                     han=timedelta(minutes=1))
    thao_tac.bat_dau(db, op, now=NOW)
    db.commit()

    assert bao_tri._don_thao_tac_qua_han(db, now=NOW + timedelta(minutes=5)) == 1
    assert op.tinh_trang == thao_tac.QUA_HAN
    assert tt.dang_ban(may) is False


def test_don_thao_tac_chay_TRUOC_doi_chieu(db, monkeypatch):
    """Thứ tự có nghĩa: thao tác còn mở thì vòng đối chiếu bỏ qua máy đó.

    Chạy dọn **sau** thì một máy kẹt 35 phút sẽ không được báo lệch suốt 35 phút
    ấy — đúng khoảng thời gian người vận hành cần biết nó kẹt.
    """
    from tests.test_297_vps_khoa_theo_may import _maintenance_probe
    _, calls = _maintenance_probe(db, monkeypatch)
    # ⚠️ Chốt THỨ TỰ, không chốt danh sách bằng nhau: vòng bảo trì có HAI phép
    #    soi (`reconcile` đọc ba backend, `soi_dien` đo điện thật — nối lại
    #    24/09/2026), và một phép kiểm đòi `calls == [...]` sẽ đỏ mỗi lần thêm
    #    một phép soi đúng đắn. Điều test này nói là: dọn phải chạy TRƯỚC.
    assert calls.index("cleanup") < calls.index("reconcile")
    assert calls.index("cleanup") < calls.index("soi_dien")


# ── 4. Sổ sách: đúng một lần, và không bao giờ lùi ──────────────────────────

def test_thu_hai_lan_trong_mot_chu_ky_KHONG_tru_hai_lan(db):
    """`paid_until` đơn điệu là thứ chặn việc thu trùng."""
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    from apps.vps.services import billing

    u = tao_nguoi_dung(db, email="vps-bill@test.com",
                       password="matkhau-tot-12", is_verified=True)
    db.flush()
    credit.nap(db, u.id, 10_000_000)
    may = _may(db)
    may.user_id = u.id
    db.flush()

    billing.thu_mot_chu_ky(db, may, now=NOW)
    han_1, du_1 = may.paid_until, credit.so_du(db, u.id)

    # Lượt bảo trì kế tiếp: máy CÒN hạn nên không nằm trong `den_han_thu`.
    assert may not in billing.den_han_thu(db, now=NOW)
    assert may.paid_until == han_1 and credit.so_du(db, u.id) == du_1


def test_paid_until_khong_bao_gio_lui(db):
    """Trả muộn hơn một chu kỳ thì tính lại từ hôm nay, không cộng dồn.

    Cộng dồn ở đó để lại một mốc vẫn nằm trong quá khứ — máy vừa thu xong đã hết
    hạn ngay, và vòng thu trừ tiếp mỗi lượt cho tới khi cạn số dư. Đó là lỗi
    nuốt tiền, không phải lỗi lệch ngày.
    """
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    from apps.vps.services import billing

    u = tao_nguoi_dung(db, email="vps-bill2@test.com",
                       password="matkhau-tot-12", is_verified=True)
    db.flush()
    credit.nap(db, u.id, 10_000_000)
    may = _may(db)
    may.user_id = u.id
    may.paid_until = NOW - timedelta(days=90)
    db.flush()

    billing.thu_mot_chu_ky(db, may, now=NOW)
    assert may.paid_until > NOW, "moc moi phai o TUONG LAI"
