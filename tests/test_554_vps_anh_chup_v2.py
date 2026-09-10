"""VPS V2 Pha 04 — ảnh chụp & khôi phục: hai lỗi P0 và một ca mất dữ liệu.

* **V-03** chụp rồi dọn ngay, chưa chờ tác vụ ⇒ `sao_luu_luc` ghi cho một ảnh
  **không tồn tại**, và bảy ngày sau máy vẫn tưởng mình có bản sao;
* **V-04** khôi phục gửi `tat_cung` (nuốt luôn lỗi) rồi rollback ngay ⇒ rollback
  trên một máy có thể vẫn đang chạy và đang ghi đĩa;
* và ca **chạy lại sau khi worker chết**: rollback lần thứ hai xoá sạch mọi thứ
  khách làm sau lần khôi phục đầu.

Proxmox giả ở đây cưỡng chế đúng hai luật thật: ảnh **chỉ xuất hiện** khi tác vụ
kết thúc tốt, và `khoi_phuc_anh` **từ chối** một máy đang chạy. Bỏ một trong hai
thì bản sai vẫn xanh.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.vps import trang_thai_may as tt
from apps.vps.services import sao_luu, tac_vu
from tests.fixtures.vps_proxmox_gia import ProxmoxGia, nhip_gia

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


class _Op:
    def __init__(self, buoc: str = "", dien_truoc: str = tt.CHAY):
        self.id = "op-1"
        self.buoc = buoc
        self.upid = ""
        self.dien_truoc = dien_truoc


class _May:
    def __init__(self, trang_thai="dang_chay", vmid=200):
        self.id = "may-1"
        self.vmid = vmid
        self.trang_thai = trang_thai
        self.ly_do = ""
        self.sao_luu_luc = None
        tt.chuan_hoa(self)


# ── V-03 · Chụp: chờ, xác minh, RỒI mới dọn ─────────────────────────────────

def test_chup_cho_tac_vu_va_tra_ve_ten_anh_da_co_that():
    px, may = ProxmoxGia(buoc=3), _May()
    ten = sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())
    assert sao_luu.co_anh(px, may.vmid, ten), "anh phai co that sau khi ham tra ve"


def test_tac_vu_chup_that_bai_thi_NEM_chu_khong_tra_ve_ten():
    """Đây là nửa đắt nhất của V-03.

    Bản cũ không chờ nên nó **không bao giờ** biết tác vụ hỏng: nó trả về tên
    ảnh, và `bao_tri` ghi `sao_luu_luc = now` cho một bản không tồn tại.
    """
    px, may = ProxmoxGia(buoc=2), _May()
    px.chup_anh = lambda vmid, ten, **kw: px._nhan_viec(
        "chup_anh", exitstatus="no space left on device")
    with pytest.raises(sao_luu.SaoLuuError):
        sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())


def test_tac_vu_bao_OK_ma_anh_khong_co_thi_van_la_that_bai():
    """Tác vụ OK vẫn có thể không để lại thứ ta mong đợi.

    Chỉ kiểm `exitstatus` là chưa đủ — phải hỏi lại danh sách. Đây là chỗ **duy
    nhất** phát hiện được ca này.
    """
    px, may = ProxmoxGia(buoc=2), _May()
    px.chup_anh = lambda vmid, ten, **kw: px._nhan_viec("chup_anh",
                                                        khi_xong=None)
    with pytest.raises(sao_luu.AnhKhongXuatHien):
        sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())


def test_KHONG_don_anh_cu_truoc_khi_anh_moi_xuat_hien():
    """Có một khoảng — dài bằng thời gian tạo — mà khách không có bản nào.

    Đối chứng của ca này nằm ở chính đồ gá: ảnh mới chỉ hiện khi tác vụ kết thúc
    tốt. Nên nếu mã dọn trước lúc chờ, bản cũ biến mất trong khi bản mới chưa có.
    """
    px, may = ProxmoxGia(buoc=4), _May()
    px.them_anh("ltt20260901_0000")
    anh_luc_xoa = []
    goc = px.xoa_anh

    def xoa_co_ghi(vmid, ten):
        anh_luc_xoa.append([x["name"] for x in px.anh])
        return goc(vmid, ten)

    px.xoa_anh = xoa_co_ghi
    ten = sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())
    assert anh_luc_xoa, "phai co don ban cu"
    assert ten in anh_luc_xoa[0], "don ban cu khi ban moi CHUA co mat"


def test_don_ban_cu_hong_KHONG_lam_hong_ca_luot():
    """Bản mới đã có và đã kiểm; bản cũ thừa chỉ tốn chỗ. Lượt sau dọn tiếp."""
    px, may = ProxmoxGia(buoc=2), _May()
    px.them_anh("ltt20260901_0000")
    px.xoa_anh = lambda vmid, ten: (_ for _ in ()).throw(RuntimeError("500"))
    assert sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())


def test_chi_don_anh_MANG_TIEN_TO_cua_ta():
    """Xoá nhầm ảnh chủ nhà tự tạo bằng tay là mất dữ liệu của người khác."""
    px, may = ProxmoxGia(buoc=2), _May()
    px.them_anh("ltt20260901_0000")
    px.them_anh("truoc-khi-nang-cap")           # của chủ nhà
    sao_luu.chup_va_don(px, may, now=NOW, nhip=nhip_gia())
    assert "truoc-khi-nang-cap" in [x["name"] for x in px.anh]


# ── V-04 · Khôi phục: chờ máy TẮT rồi mới rollback ──────────────────────────

def _khoi_phuc(px, may, ten, op=None):
    return sao_luu.thi_hanh_khoi_phuc(None, may, px, op or _Op(), ten=ten,
                                      nhip=nhip_gia(), now=NOW)


def test_khoi_phuc_KHONG_rollback_khi_may_con_dang_chay():
    """Proxmox từ chối rollback một máy đang chạy khi ảnh không kèm RAM.

    Bản cũ nuốt lỗi của `tat_cung` rồi gọi rollback ngay dòng sau — nên nó dựa
    hoàn toàn vào việc Proxmox tình cờ đã tắt máy xong. Đồ gá ở đây cưỡng chế
    đúng luật thật, nên bản cũ sẽ **đỏ**.
    """
    px, may = ProxmoxGia(dien="running", buoc=3), _May()
    px.them_anh("ltt20260901_0000")
    dien_luc_rollback = []
    goc = px.khoi_phuc_anh

    def rollback_co_ghi(vmid, ten):
        dien_luc_rollback.append(px.dien)
        return goc(vmid, ten)

    px.khoi_phuc_anh = rollback_co_ghi
    _khoi_phuc(px, may, "ltt20260901_0000")
    assert dien_luc_rollback == ["stopped"]


def test_khoi_phuc_tra_may_ve_dung_trang_thai_dien_truoc_do():
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    px.them_anh("ltt20260901_0000")
    assert _khoi_phuc(px, may, "ltt20260901_0000") == tt.CHAY
    assert px.dien == "running"


def test_may_dang_TAT_thi_khoi_phuc_xong_van_TAT():
    """Khách tắt máy rồi khôi phục thì đừng tự bật nó lên."""
    px, may = ProxmoxGia(dien="stopped", buoc=2), _May("da_tat")
    px.them_anh("ltt20260901_0000")
    assert _khoi_phuc(px, may, "ltt20260901_0000",
                      op=_Op(dien_truoc=tt.TAT)) == tt.TAT
    assert "bat" not in px.da_goi


def test_anh_bien_mat_giua_chung_thi_DUNG_LAI_chu_khong_rollback_bua():
    """Giữa lúc khách mở trang và lúc worker chạy có một vòng bảo trì.

    Không hỏi lại thì `khoi_phuc_anh` gọi với một tên không tồn tại, và Proxmox
    trả một lỗi không nói gì về nguyên nhân.
    """
    px, may = ProxmoxGia(dien="stopped", buoc=2), _May("da_tat")
    with pytest.raises(sao_luu.SaoLuuError):
        _khoi_phuc(px, may, "ltt20260901_0000")
    assert "khoi_phuc_anh" not in px.da_goi


def test_tat_may_that_bai_thi_KHONG_rollback():
    """Nuốt lỗi tắt máy rồi rollback là đường ngắn nhất tới một đĩa hỏng."""
    px, may = ProxmoxGia(dien="running", buoc=1), _May()
    px.them_anh("ltt20260901_0000")
    px.tat_cung = lambda vmid: px._nhan_viec("tat_cung",
                                             exitstatus="timeout waiting")
    with pytest.raises(tac_vu.TacVuThatBai):
        _khoi_phuc(px, may, "ltt20260901_0000")
    assert "khoi_phuc_anh" not in px.da_goi


def test_chay_lai_o_pha_BAT_KHONG_rollback_lan_thu_hai():
    """Ca **mất dữ liệu**, không phải ca phiền toái.

    Worker chết sau khi rollback xong và trước khi bật lại. Job chạy lại: nếu nó
    rollback thêm lần nữa thì mọi thứ khách làm sau lần khôi phục đầu biến mất.
    """
    px, may = ProxmoxGia(dien="stopped", buoc=2), _May("da_tat")
    px.them_anh("ltt20260901_0000")
    op = _Op(buoc=sao_luu.BUOC_BAT_LAI)
    _khoi_phuc(px, may, "ltt20260901_0000", op=op)
    assert "khoi_phuc_anh" not in px.da_goi
    assert px.dien == "running"


def test_khoi_phuc_ghi_upid_de_noi_lai_duoc():
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    px.them_anh("ltt20260901_0000")
    op = _Op()
    _khoi_phuc(px, may, "ltt20260901_0000", op=op)
    # tắt cứng + rollback + bật lại = ba UPID.
    assert len(op.upid.splitlines()) == 3


# ── Hợp đồng với phần còn lại của hệ ────────────────────────────────────────

def test_job_type_anh_chup_da_khai_trong_manifest():
    from apps.vps.manifest import MANIFEST
    assert sao_luu.JOB_TYPE in MANIFEST.job_types
    assert sao_luu.JOB_TYPE in MANIFEST.max_runtime_s


def test_moi_buoc_khoi_phuc_deu_co_nhan():
    from apps.vps import nhan
    for b in (sao_luu.BUOC_TAT_TRUOC, sao_luu.BUOC_KHOI_PHUC,
              sao_luu.BUOC_BAT_LAI):
        assert b in nhan.BUOC, b


def test_han_chup_ngan_hon_tran_job_anh_chup():
    from apps.vps.manifest import MANIFEST
    assert sao_luu.HAN_KHOI_PHUC_S < MANIFEST.max_runtime_s[sao_luu.JOB_TYPE]


def test_KHONG_chup_anh_an_toan_truoc_khi_khoi_phuc():
    """Quyết định có chủ ý (ADR-04) — nên nó phải có phép kiểm, không chỉ có chú thích.

    Ảnh nằm **cùng pool** nên gọi nó là "an toàn" là nói quá; và đĩa là nút thắt
    của cả sản phẩm, nên một ảnh thêm mỗi lần khôi phục, nằm ngoài vòng dọn hằng
    tuần, là một đường rò dung lượng không ai đóng.

    Ai đó thêm bước ấy vào sau này sẽ làm ca này đỏ, và đọc được lý do ở đây.
    """
    px, may = ProxmoxGia(dien="running", buoc=2), _May()
    px.them_anh("ltt20260901_0000")
    _khoi_phuc(px, may, "ltt20260901_0000")
    assert "chup_anh" not in px.da_goi


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


def _may_that(db):
    from apps.vps.tables import VpsGateway, VpsInstance
    g = VpsGateway(ten="cong-1", vung="sgp", ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai="dang_chay", vmid=200)
    db.add(m)
    db.flush()
    return m


def test_bao_tri_KHONG_ghi_sao_luu_luc_khi_chup_hong(db):
    """Nửa còn lại của V-03, và nó nằm ở `bao_tri` chứ không ở `sao_luu`.

    `chup_va_don` ném đúng rồi vẫn chưa đủ. Hai cách hỏng tiếp:

    * vòng bảo trì chỉ bắt `ProxmoxError` ⇒ `SaoLuuError` bay lên và **cả lượt
      bảo trì** chết, kéo theo cả phần thu tiền;
    * hoặc ai đó bắt rồi đi tiếp mà quên ⇒ `sao_luu_luc` vẫn được ghi cho một
      bản không tồn tại, và bảy ngày sau máy vẫn tưởng mình có bản sao.

    Ca này chốt **hành vi**: lượt bảo trì sống sót, và mốc không bị ghi.
    """
    from apps.vps import bao_tri

    may = _may_that(db)
    px = ProxmoxGia(buoc=2)
    px.chup_anh = lambda vmid, ten, **kw: px._nhan_viec(
        "chup_anh", exitstatus="no space left on device")

    assert bao_tri._chup_anh_den_han(db, px, now=NOW) == 0
    assert may.sao_luu_luc is None, "khong duoc ghi moc cho mot anh khong co that"
