"""VPS V2 Pha 08 — sức khoẻ và cảnh báo: im khi khoẻ, nói rõ khi hỏng.

Mệnh đề trung tâm của một hệ cảnh báo không phải *"nó có báo không"* mà là
*"nó có im khi không có gì để nói không"*. Một kênh nói mỗi giờ là một kênh người
ta lọc bỏ, và họ lọc bỏ đúng vào lượt có tin xấu.

Bốn nhóm:

1. im lặng khi khoẻ, và khử trùng lặp giữa hai lượt quét;
2. phân biệt **chưa hỏi** với **đã hỏi và không có trả lời**;
3. không rò bí mật hay hình dạng hạ tầng vào thứ khách đọc;
4. không hứa thứ không đo được (RAM/đĩa bên trong máy khách).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import suc_khoe, trang_thai_may as tt
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


_DEM = [0]


def _may(db, **kw):
    from apps.vps.tables import VpsGateway, VpsInstance
    _DEM[0] += 1
    g = VpsGateway(ten=f"cong-{_DEM[0]}", vung="sgp",
                   ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai="dang_chay",
                    vmid=200 + _DEM[0], sao_luu_luc=NOW)
    tt.ghi_quan_sat(m, tt.CHAY, now=NOW)
    for k, v in kw.items():
        setattr(m, k, v)
    db.add(m)
    db.flush()
    return m


def _ma(ds) -> set:
    return {x.ma for x in ds}


# ── 1. Im khi khoẻ, và khử trùng lặp ────────────────────────────────────────

def test_he_khoe_thi_KHONG_co_canh_bao_nao(db):
    """Một dòng "mọi thứ ổn" mỗi giờ dạy người đọc bỏ qua kênh này."""
    _may(db)
    assert suc_khoe.canh_bao(db, now=NOW, env={}) == [
        x for x in suc_khoe.canh_bao(db, now=NOW, env={})
        if x.ma == "khong_co_sao_luu_doc_lap"]


def test_khong_co_may_nao_thi_hoan_toan_im(db):
    assert suc_khoe.canh_bao(db, now=NOW, env={}) == []


def test_hai_luot_quet_tren_CUNG_su_co_cho_ra_CUNG_khoa(db):
    """Đây là cách khử trùng lặp mà không cần bảng cảnh báo nào.

    Một cảnh báo là **mệnh đề về trạng thái hiện tại**, không phải một dòng được
    ghi ra. Nên người gọi so khoá là biết nó cũ hay mới.
    """
    _may(db, suc_khoe=tt.MAT_LIEN_LAC)
    a = {x.khoa for x in suc_khoe.canh_bao(db, now=NOW, env={})}
    # Cách nhau 5 phút — **dưới** `QUA_CU_SAU_S`, cố ý. Cách xa hơn thì phép đo
    # thật sự cũ đi và một cảnh báo MỚI (`quan_sat_qua_cu`) xuất hiện đúng luật:
    # ca này sẽ đỏ vì hệ đang làm đúng, chứ không vì khử trùng lặp hỏng.
    b = {x.khoa for x in suc_khoe.canh_bao(db, now=NOW + timedelta(minutes=5),
                                           env={})}
    assert a == b and a


def test_su_co_dien_rong_KHONG_bien_mot_dong_thanh_mot_trang_giay(db):
    """Cảnh báo đính tối đa `MAU_TOI_DA` mẫu, và mang theo con số thật."""
    for _ in range(12):
        _may(db, suc_khoe=tt.MAT_LIEN_LAC)
    cb = [x for x in suc_khoe.canh_bao(db, now=NOW, env={})
          if x.ma == "mat_lien_lac"][0]
    assert cb.so_luong == 12
    assert len(cb.tai_nguyen) <= suc_khoe.MAU_TOI_DA


# ── 2. "Chưa hỏi" ≠ "đã hỏi và không có trả lời" ────────────────────────────

def test_mat_lien_lac_la_NGHIEM_TRONG(db):
    """Khách đang trả tiền cho một thứ ta không nhìn thấy."""
    _may(db, suc_khoe=tt.MAT_LIEN_LAC)
    cb = [x for x in suc_khoe.canh_bao(db, now=NOW, env={})
          if x.ma == "mat_lien_lac"]
    assert cb and cb[0].muc == suc_khoe.NGHIEM_TRONG


def test_QUA_CU_va_MAT_LIEN_LAC_la_hai_canh_bao_KHAC_NHAU(db):
    """Gộp chúng là mất thông tin về việc vòng đối chiếu có chạy hay không.

    `qua_cu` nghĩa là **ta chưa hỏi** — có thể vòng bảo trì đã chết.
    `mat_lien_lac` nghĩa là **đã hỏi và không có trả lời** — Proxmox có vấn đề.
    Hai nguyên nhân, hai chỗ đi sửa.
    """
    _may(db)                        # vừa đo xong lúc NOW
    ds = suc_khoe.canh_bao(db, now=NOW + timedelta(hours=3), env={})
    assert "quan_sat_qua_cu" in _ma(ds)
    assert "mat_lien_lac" not in _ma(ds)


def test_thao_tac_qua_han_la_NGHIEM_TRONG(db):
    """Nó có nghĩa là một worker có thể đang chết — và mọi job khác cũng vậy."""
    may = _may(db)
    op = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW)
    thao_tac.hong(db, op, may, ma_loi="tac_vu_qua_han", qua_han=True, now=NOW)
    db.flush()
    cb = [x for x in suc_khoe.canh_bao(db, now=NOW, env={})
          if x.ma == "thao_tac_qua_han"]
    assert cb and cb[0].muc == suc_khoe.NGHIEM_TRONG


def test_MOT_lan_hong_le_khong_dang_bao(db):
    """Một hệ nói chuyện với ba dịch vụ ngoài thì hỏng lẻ là chuyện thường.

    Báo mỗi lần là dạy người đọc bỏ qua. Ba lần trong một ngày thì không còn là
    ngẫu nhiên.
    """
    may = _may(db)
    op = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW)
    thao_tac.hong(db, op, may, ma_loi="proxmox_tu_choi", now=NOW)
    db.flush()
    assert "thao_tac_hong_nhieu" not in _ma(suc_khoe.canh_bao(db, now=NOW,
                                                              env={}))


def test_thieu_sao_luu_doc_lap_la_THONG_TIN_chu_khong_phai_canh_bao(db):
    """Đây là một **sự thật kiến trúc đã biết**, không phải một thứ vừa hỏng.

    Đặt nó ở mức cao hơn là một cảnh báo luôn bật — và một cảnh báo luôn bật là
    một cảnh báo bị bỏ qua, kéo theo cả những cảnh báo thật nằm cạnh nó.
    """
    _may(db)
    cb = [x for x in suc_khoe.canh_bao(db, now=NOW, env={})
          if x.ma == "khong_co_sao_luu_doc_lap"]
    assert cb and cb[0].muc == suc_khoe.THONG_TIN


def test_co_sao_luu_doc_lap_thi_KHONG_bao_nua(db):
    from apps.vps import sao_luu_doc_lap as sl
    _may(db)
    env = {sl.KHOA_MAY_CHU: "https://pbs:8007", sl.KHOA_KHO: "kho",
           sl.KHOA_NGUOI_DUNG: "u@pbs"}
    assert "khong_co_sao_luu_doc_lap" not in _ma(
        suc_khoe.canh_bao(db, now=NOW, env=env))


# ── 3. Không rò hình dạng hạ tầng vào thứ khách đọc ─────────────────────────

def test_dong_thoi_gian_KHONG_chua_upid(db):
    """UPID nói ra số hiệu tác vụ và tên node — vô ích với khách, và là một
    mảnh hình dạng hạ tầng."""
    may = _may(db)
    op = thao_tac.mo(db, may, tt.DANG_KD_LAI, boi="u1", now=NOW)
    thao_tac.ghi_upid(db, op, "UPID:pve:000ABC:qmshutdown:200:root@pam:")
    db.flush()
    text = repr(suc_khoe.dong_thoi_gian(db, may.id))
    assert "UPID" not in text and "pve" not in text


def test_dong_thoi_gian_KHONG_chua_chi_tiet_loi_tho(db):
    """`chi_tiet_loi` chứa thông điệp thô của Proxmox — đường dẫn, cổng, tên node."""
    may = _may(db)
    op = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", now=NOW)
    thao_tac.hong(db, op, may, ma_loi="proxmox_tu_choi",
                  chi_tiet="500 at /nodes/pve/qemu/201/status/start", now=NOW)
    db.flush()
    text = repr(suc_khoe.dong_thoi_gian(db, may.id))
    assert "/nodes/pve" not in text
    # Mã có cấu trúc thì VẪN trả — nó ngắn, dịch được, và là thứ khách đọc cho
    # bộ phận hỗ trợ nghe.
    assert "proxmox_tu_choi" in text


def test_dong_thoi_gian_moi_nhat_truoc(db):
    may = _may(db)
    a = thao_tac.mo(db, may, tt.DANG_BAT, boi="u1", khoa_idem="a", now=NOW)
    thao_tac.xong(db, a, may, now=NOW)
    b = thao_tac.mo(db, may, tt.DANG_TAT, boi="u1", khoa_idem="b",
                    now=NOW + timedelta(minutes=5))
    db.flush()
    ds = suc_khoe.dong_thoi_gian(db, may.id)
    assert ds[0].loai == b.loai and ds[0].dang_chay is True


def test_tong_quan_KHONG_goi_mang(db, monkeypatch):
    """Trang admin gọi hàm này mỗi lần mở.

    Một lần gọi ra Proxmox ở đây biến một node chậm thành một trang admin không
    mở được — đúng lúc người ta cần nó nhất.
    """
    import socket

    def _cam(*a, **kw):
        raise AssertionError("tong_quan() khong duoc goi mang")

    monkeypatch.setattr(socket, "create_connection", _cam)
    monkeypatch.setattr(socket.socket, "connect", _cam)
    _may(db)
    assert suc_khoe.tong_quan(db, now=NOW, env={}).tong_may == 1


# ── 4. Không hứa thứ không đo được ─────────────────────────────────────────

def test_khong_co_truong_nao_ve_RAM_hay_DIA_ben_trong_may_khach():
    """Guest agent là thiết bị virtio, và virtio treo trên cụm này.

    Một ô "RAM: —" trên trang khách là một lời hứa rằng ta sẽ điền nó. Không có
    trường thì không có lời hứa.
    """
    truong = set(suc_khoe.TongQuan().__dict__)
    cam = {"ram", "ram_mb", "dia_dung", "dia_trong", "cpu_phan_tram", "uptime"}
    assert not (truong & cam), f"hua thu khong do duoc: {truong & cam}"


def test_moi_canh_bao_deu_o_mot_muc_hop_le(db):
    for _ in range(4):
        _may(db, suc_khoe=tt.MAT_LIEN_LAC, vong_doi=tt.LOI)
    for x in suc_khoe.canh_bao(db, now=NOW, env={}):
        assert x.muc in suc_khoe.MUC, x


def test_thang_do_cua_canh_bao_KHONG_trung_thang_do_cua_doi_chieu():
    """Hai thang đo trộn vào nhau buộc người đọc phải nhớ thang nào đang dùng.

    `doi_chieu` phân loại **phát hiện lệch** (xử thế nào); `suc_khoe` phân loại
    **mức khẩn** (có dựng người dậy không). Hai câu hỏi khác nhau.
    """
    from apps.vps import doi_chieu
    assert not (set(suc_khoe.MUC) & set(doi_chieu.MUC_DO))
