"""VPS V2 Pha 03 — vòng đời: khởi động lại phải THẬT SỰ khởi động lại.

Bốn mệnh đề, mỗi cái ứng một lỗi P0 của baseline:

* **V-01** khởi động lại phải kết thúc ở RUNNING (bản cũ chỉ tắt);
* **V-01b** nó **không được** gửi lệnh bật trước khi quan sát được STOPPED;
* **V-02** không thao tác nào được kết luận trước khi đo lại thế giới thật;
* **V-07** máy đang bận thì lệnh thứ hai bị từ chối, không chen vào.

Mọi ca dùng Proxmox giả **có trạng thái** (`tests/fixtures/vps_proxmox_gia.py`).
So thứ tự gọi hàm là không đủ: bản đúng và bản sai gọi cùng những hàm ấy, khác
nhau ở chỗ **có chờ giữa chúng hay không**.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import trang_thai_may as tt
from apps.vps.services import dieu_khien, tac_vu, thao_tac
from tests.fixtures.vps_proxmox_gia import ProxmoxGia, nhip_gia

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


class _Op:
    """Thao tác trần — `thi_hanh` chỉ cần `buoc` và `upid`."""

    def __init__(self, buoc: str = ""):
        self.id = "op-1"
        self.buoc = buoc
        self.upid = ""


class _May:
    def __init__(self, trang_thai="dang_chay", vmid=200):
        self.id = "may-1"
        self.vmid = vmid
        self.trang_thai = trang_thai
        self.ly_do = ""
        tt.chuan_hoa(self)


def _chay(px, may, lenh, op=None, **kw):
    return dieu_khien.thi_hanh(None, may, px, op or _Op(), lenh=lenh,
                               nhip=nhip_gia(), now=NOW, **kw)


# ── V-01 · Khởi động lại phải kết thúc ở RUNNING ─────────────────────────────

def test_khoi_dong_lai_ket_thuc_o_RUNNING():
    """Bản cũ: `khoi_dong_lai()` chỉ gọi `tat()` và không bật lại bao giờ.

    Nút tên là "Khởi động lại" và nhật ký ghi "Máy khởi động lại" — cho một máy
    nằm tắt. Đây là ca đơn giản nhất trong tệp và là lỗi đắt nhất.
    """
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    assert _chay(px, may, "khoi_dong_lai") == tt.CHAY
    assert px.dien == "running"
    assert may.dien_quan_sat == tt.CHAY and may.trang_thai == "dang_chay"


def test_khoi_dong_lai_co_di_qua_pha_TAT():
    """Kết thúc ở RUNNING vẫn chưa đủ — nó phải thật sự **tắt** trước đã.

    Một bản "sửa" chỉ gọi `bat()` cũng kết thúc ở RUNNING (máy đang chạy sẵn),
    và ca trên sẽ xanh. Ca này là đối chứng của ca trên.
    """
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    _chay(px, may, "khoi_dong_lai")
    assert px.da_goi == ["tat_mem", "bat"]


# ── V-01b · Không bật trước khi quan sát được STOPPED ────────────────────────

def test_khong_gui_lenh_BAT_khi_may_van_con_dang_chay():
    """Đây là mệnh đề mà **mọi** test so thứ tự gọi hàm bỏ lọt.

    Bản đúng và bản sai đều gọi `tat_mem` rồi `bat`, đúng thứ tự đó. Khác biệt
    duy nhất là bản đúng chờ giữa hai lệnh. Nên phép kiểm phải chụp lại **trạng
    thái điện tại đúng khoảnh khắc `bat` được gọi**.
    """
    px, may = ProxmoxGia(dien="running", buoc=4), _May()
    dien_luc_bat = []
    goc = px.bat

    def bat_co_ghi(vmid):
        dien_luc_bat.append(px.dien)
        return goc(vmid)

    px.bat = bat_co_ghi
    _chay(px, may, "khoi_dong_lai")
    assert dien_luc_bat == ["stopped"], (
        f"goi `bat` luc may dang {dien_luc_bat} — chua cho STOPPED")


# ── V-02 · Không kết luận trước khi đo lại ───────────────────────────────────

def test_tat_that_bai_KHONG_ghi_la_da_tat():
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    px.tac_vu.clear()
    upid = px._nhan_viec("tat_mem", exitstatus="VM quit/powerdown failed")
    px.da_goi.clear()
    px.tat_mem = lambda vmid: upid
    with pytest.raises(tac_vu.TacVuThatBai):
        _chay(px, may, "tat")
    assert may.dien_quan_sat != tt.TAT


def test_tat_mem_qua_han_KHONG_tu_rut_dien():
    """Rút điện giữa lúc Windows đang ghi đĩa là làm hỏng hệ tệp của khách.

    Tắt mềm quá hạn phải trả về một trạng thái hỏng **có việc để làm tiếp** —
    và việc đó là một nút riêng mà khách bấm, có ghi nhật ký. Tự động hoá bước
    đó là chuyển một quyết định mất dữ liệu từ người sang máy.
    """
    px, may = ProxmoxGia(dien="running", buoc=1), _May()
    # Tác vụ kết thúc OK nhưng guest không tắt — Windows hiện hộp thoại.
    px.tat_mem = lambda vmid: px._nhan_viec("tat_mem", khi_xong=None)
    with pytest.raises(tac_vu.DienKhongDat):
        dieu_khien.thi_hanh(None, may, px, _Op(), lenh="tat",
                            nhip=nhip_gia(), now=NOW)
    assert "tat_cung" not in px.da_goi, "khong duoc tu rut dien"


def test_tat_cung_la_mot_lenh_RIENG_va_tuong_minh():
    px, may = ProxmoxGia(dien="running", buoc=1), _May()
    assert _chay(px, may, "tat_cung") == tt.TAT
    assert px.da_goi == ["tat_cung"]


def test_bat_ghi_quan_sat_va_dong_dau_thoi_gian():
    px, may = ProxmoxGia(dien="stopped", buoc=2), _May("da_tat")
    _chay(px, may, "bat")
    assert may.dien_quan_sat == tt.CHAY and may.quan_sat_luc == NOW
    assert may.suc_khoe == tt.KHOE


# ── Chạy lại sau khi worker chết ─────────────────────────────────────────────

def test_lenh_bat_cho_may_DANG_CHAY_khong_ban_them_lenh_nao():
    """Job chạy lại cho một việc đã xong không được gọi Proxmox lần nữa.

    Bắn lại `start` cho máy đang chạy thì Proxmox trả lỗi, và job hỏng — cho một
    việc **đã thành công**.
    """
    px, may = ProxmoxGia(dien="running"), _May()
    assert _chay(px, may, "bat") == tt.CHAY
    assert px.da_goi == []


def test_khoi_dong_lai_chay_lai_o_pha_BAT_khong_tat_may_lan_nua():
    """Ca nguy hiểm nhất của việc chạy lại, và nó **mất dữ liệu của khách**.

    Worker chết sau khi đã bật máy lên. Job chạy lại: nếu chỉ nhìn `dien=chay`
    rồi kết luận "chưa tắt", nó sẽ tắt máy khách thêm một lần nữa — giữa lúc họ
    đang dùng. Cột `buoc` là thứ duy nhất phân biệt hai tình huống trông giống
    hệt nhau.
    """
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    op = _Op(buoc=dieu_khien.BUOC_CHO_BAT)      # đã qua pha tắt
    assert _chay(px, may, "khoi_dong_lai", op=op) == tt.CHAY
    assert "tat_mem" not in px.da_goi


def test_upid_duoc_ghi_TRUOC_khi_cho():
    """Mục đích của cột `upid` là sống sót qua một lần tiến trình chết.

    Ghi sau khi chờ thì đúng lúc chết là lúc chưa ghi — tức cột đó không bao giờ
    làm được việc nó sinh ra để làm.
    """
    px, may = ProxmoxGia(dien="stopped", buoc=3), _May("da_tat")
    op = _Op()
    upid_khi_cho = []
    goc = px.trang_thai_tac_vu
    px.trang_thai_tac_vu = lambda u: (upid_khi_cho.append(op.upid), goc(u))[1]
    _chay(px, may, "bat", op=op)
    assert upid_khi_cho and upid_khi_cho[0], "cho ma chua ghi upid"


# ── V-07 và luật kết nạp — cần CSDL thật ─────────────────────────────────────

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


def _may_that(db, *, trang_thai="dang_chay"):
    from apps.vps.tables import VpsGateway, VpsInstance
    _DEM[0] += 1
    g = VpsGateway(ten=f"cong-{_DEM[0]}", vung="sgp",
                   ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai=trang_thai, vmid=200 + _DEM[0])
    db.add(m)
    db.flush()
    return m


@pytest.fixture(autouse=True)
def _khong_nop_job(monkeypatch):
    """Chặn hàng đợi: pha này kiểm **kết nạp**, không kiểm nền tảng job."""
    import platform_core.jobs as jq
    monkeypatch.setattr(jq, "submit", lambda db, **kw: None)


def test_may_bi_treo_khong_tu_bat_lai_duoc(db):
    """Không có luật này thì "treo" chỉ là một cái nút — tức không treo gì cả."""
    may = _may_that(db, trang_thai="bi_treo")
    with pytest.raises(dieu_khien.KhongDuocPhepError) as loi:
        dieu_khien.xin(db, may, "bat", boi="u1", now=NOW)
    assert "credit" in str(loi.value).lower()


@pytest.mark.parametrize("tt_ma", ["dang_tao", "da_xoa"])
def test_may_dang_tao_hay_da_xoa_khong_nhan_lenh(db, tt_ma):
    may = _may_that(db, trang_thai=tt_ma)
    with pytest.raises(dieu_khien.KhongDuocPhepError):
        dieu_khien.xin(db, may, "khoi_dong_lai", boi="u1", now=NOW)


def test_bam_hai_lan_trong_mot_phut_ra_MOT_thao_tac(db):
    may = _may_that(db)
    a = dieu_khien.xin(db, may, "khoi_dong_lai", boi="u1", now=NOW)
    b = dieu_khien.xin(db, may, "khoi_dong_lai", boi="u1",
                       now=NOW + timedelta(seconds=3))
    assert a.id == b.id


def test_may_dang_ban_thi_lenh_khac_bi_tu_choi(db):
    """V-07: khách bấm "Tắt" trong lúc lệnh khởi động lại đang chạy."""
    may = _may_that(db)
    dieu_khien.xin(db, may, "khoi_dong_lai", boi="u1", now=NOW)
    with pytest.raises(thao_tac.DangBanError):
        dieu_khien.xin(db, may, "tat", boi="u1", now=NOW)


def test_xin_KHONG_cham_proxmox(db, monkeypatch):
    """Route phải trả lời được kể cả khi Proxmox đang treo.

    Nó chỉ mở sổ và nộp job. Chạm Proxmox ở đây là kéo trần 100 giây của
    Cloudflare vào một thứ không có ngân sách cho nó.
    """
    from apps.vps.services import proxmox

    def _no(*a, **kw):
        raise AssertionError("xin() khong duoc cham Proxmox")

    monkeypatch.setattr(proxmox, "client_tu_moi_truong", _no)
    may = _may_that(db)
    assert dieu_khien.xin(db, may, "tat", boi="u1", now=NOW) is not None


def test_xin_doi_Y_DINH_nhung_khong_doi_QUAN_SAT(db):
    """Ý định đúng từ giây khách bấm; quan sát thì chưa đo lại lần nào."""
    may = _may_that(db)
    dieu_khien.xin(db, may, "tat", boi="u1", now=NOW)
    assert may.dien_mong_muon == tt.TAT
    assert may.dien_quan_sat != tt.TAT
    assert may.tac_vu == tt.DANG_TAT


def test_moi_lenh_deu_co_nhan_yeu_cau_va_nhan_ket_qua():
    """Một cú bấm sinh HAI dòng nhật ký, và cả hai phải có nhãn tiếng người.

    Thiếu nhãn `xin_*` thì khách thấy nguyên mã máy đọc trong nhật ký của chính
    máy mình — đúng thứ `nhan.py` sinh ra để chặn.
    """
    from apps.vps import nhan
    for lenh in dieu_khien.LENH:
        assert f"xin_{lenh}" in nhan.SU_KIEN, lenh
        assert lenh in nhan.SU_KIEN, lenh


def test_moi_ma_tac_vu_va_buoc_deu_co_nhan():
    """Thêm một tác vụ mà quên khai nhãn ⇒ khách thấy `dang_kd_lai` trên trang."""
    from apps.vps import nhan
    assert set(nhan.TAC_VU) == set(tt.TAC_VU_DOC_QUYEN)
    for buoc in (dieu_khien.BUOC_GUI_TAT, dieu_khien.BUOC_CHO_TAT,
                 dieu_khien.BUOC_GUI_BAT, dieu_khien.BUOC_CHO_BAT):
        assert buoc in nhan.BUOC, buoc


def test_job_type_dieu_khien_da_khai_trong_manifest():
    """Job type không khai thì nền tảng từ chối nhận việc — im lặng, ở runtime."""
    from apps.vps.manifest import MANIFEST
    assert dieu_khien.JOB_TYPE in MANIFEST.job_types
    assert dieu_khien.JOB_TYPE in MANIFEST.max_runtime_s


def test_tran_job_dieu_khien_du_cho_HAI_pha_cho_dien():
    """Khởi động lại = hai lần chờ điện. Trần job phải đủ cho cả hai.

    Không đủ thì mọi lần khởi động lại của một máy Windows chậm đều chết vì hết
    giờ, và triệu chứng là "khởi động lại không bao giờ chạy được" — không ai
    tra ra được nó là một con số trong manifest.
    """
    from apps.vps.manifest import MANIFEST
    ngan_sach = tac_vu.han_theo_job(dieu_khien.JOB_TYPE)
    assert ngan_sach >= 2 * tac_vu.HAN_DIEN_S
    assert ngan_sach < MANIFEST.max_runtime_s[dieu_khien.JOB_TYPE]
