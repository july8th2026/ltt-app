"""VPS V2 Pha 07 — TLS quản trị, bí mật, và cách ly vì lạm dụng.

Ba nhóm, và nhóm đầu là nhóm đắt nhất:

1. **TLS fail-closed ở production.** Bản cũ bỏ qua xác minh khi thiếu CA và ghi
   một dòng `log.warning` — một dòng không ai đọc, và nó không chặn được gì.
2. **Bí mật không lọt ra.** `repr()` là thứ đi vào traceback và Sentry, im lặng,
   đúng vào lúc có nhiều người đang đọc log nhất.
3. **Cách ly ≠ treo ≠ xoá.** Ba nút cho ba vấn đề; dùng nhầm nút là xoá máy của
   một khách đang trả tiền đầy đủ.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.vps.services import cach_ly, proxmox

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)

_CO_BAN = {
    "LTT_VPS_PROXMOX_URL": "https://192.168.2.168:8006",
    "LTT_VPS_PROXMOX_TOKEN_ID": "vpsapp@pve!ltt",
    "LTT_VPS_PROXMOX_TOKEN_SECRET": "bi-mat-token",
}


def _env(**them) -> dict:
    return {**_CO_BAN, **them}


# ── 1. TLS ──────────────────────────────────────────────────────────────────

def test_production_khong_co_CA_thi_TU_CHOI():
    """Mệnh đề trung tâm của cả pha.

    `verify=False` trên đường quản trị nghĩa là bất cứ ai chen được vào đường đi
    đều đọc và sửa được lệnh — kể cả lệnh xoá đĩa. Một dòng cảnh báo không phải
    hàng rào; một `raise` thì phải.
    """
    with pytest.raises(proxmox.ChuaCauHinh) as loi:
        proxmox.doc_cau_hinh(_env(LTT_ENV="production"))
    assert "CA" in str(loi.value)


def test_production_khong_bo_qua_duoc_bang_bien_BO_QUA():
    """Đường thoát của môi trường dev **không** được mở ở production.

    Nếu mở được thì hàng rào chỉ còn là một quy ước, và quy ước thì thua một lần
    sao chép `app.env` từ máy dev sang máy chủ.
    """
    with pytest.raises(proxmox.ChuaCauHinh):
        proxmox.doc_cau_hinh(_env(LTT_ENV="production",
                                  **{proxmox.KHOA_BO_QUA_TLS: "1"}))


def test_production_co_CA_thi_chay_va_verify_tro_toi_CA():
    cf = proxmox.doc_cau_hinh(_env(LTT_ENV="production",
                                   LTT_VPS_PROXMOX_CA="/etc/ssl/pve-ca.pem"))
    assert cf.verify == "/etc/ssl/pve-ca.pem"


def test_ngoai_production_van_phai_KHAI_TUONG_MINH():
    """Im lặng bỏ qua xác minh là cách để quên mất mình đang bỏ qua.

    Một biến tên `LTT_VPS_PROXMOX_CA` **để trống** thì không nói gì. Một biến tên
    `..._TLS_BO_QUA=1` thì người đặt nó biết mình vừa làm gì, và người đọc
    `app.env` sáu tháng sau cũng biết.
    """
    with pytest.raises(proxmox.ChuaCauHinh):
        proxmox.doc_cau_hinh(_env(LTT_ENV="development"))
    cf = proxmox.doc_cau_hinh(_env(LTT_ENV="development",
                                   **{proxmox.KHOA_BO_QUA_TLS: "1"}))
    assert cf.verify is False


def test_LTT_ENV_LA_duoc_coi_nhu_PRODUCTION():
    """Một lỗi gõ phím trong biến môi trường không được mở ra đường không xác minh.

    `resolve_environment` ném khi `LTT_ENV` lạ; ở đây ta đoán về **phía an toàn**
    thay vì để ngoại lệ đó biến thành một đường lùi.
    """
    with pytest.raises(proxmox.ChuaCauHinh):
        proxmox.doc_cau_hinh(_env(LTT_ENV="prodcution",         # gõ nhầm
                                  **{proxmox.KHOA_BO_QUA_TLS: "1"}))


def test_san_sang_tls_tra_loi_duoc_ma_KHONG_cham_mang(monkeypatch):
    """`/health/ready` gọi hàm này. Một phép kiểm sẵn sàng gọi ra ngoài là một
    phép kiểm sẽ đỏ vì những lý do không liên quan tới nó."""
    import socket

    def _cam(*a, **kw):
        raise AssertionError("san_sang_tls() khong duoc goi mang")

    monkeypatch.setattr(socket, "create_connection", _cam)

    ok, ly_do = proxmox.san_sang_tls(_env(LTT_ENV="production"))
    assert ok is False and ly_do
    ok, ly_do = proxmox.san_sang_tls(
        _env(LTT_ENV="production", LTT_VPS_PROXMOX_CA="/ca.pem"))
    assert ok is True and ly_do == ""


def test_san_sang_tls_va_doc_cau_hinh_KHONG_duoc_lech_nhau():
    """Hai nơi hỏi cùng một câu bằng hai đoạn mã là hai câu trả lời sẽ lệch nhau.

    Cái lệch đó nguy hiểm theo một hướng cụ thể: `/health/ready` xanh trong khi
    app không nối được — hoặc tệ hơn, ngược lại.
    """
    for env in (_env(LTT_ENV="production"),
                _env(LTT_ENV="development"),
                _env(LTT_ENV="development", **{proxmox.KHOA_BO_QUA_TLS: "1"}),
                _env(LTT_ENV="production", LTT_VPS_PROXMOX_CA="/ca.pem")):
        ok, _ = proxmox.san_sang_tls(env)
        try:
            proxmox.doc_cau_hinh(env)
            dung_duoc = True
        except proxmox.ChuaCauHinh:
            dung_duoc = False
        assert ok == dung_duoc, env


# ── 2. Bí mật ───────────────────────────────────────────────────────────────

def test_repr_cua_cau_hinh_KHONG_chua_token_secret():
    cf = proxmox.doc_cau_hinh(_env(LTT_ENV="production",
                                   LTT_VPS_PROXMOX_CA="/ca.pem"))
    assert "bi-mat-token" not in repr(cf)
    assert "bi-mat-token" not in str(cf)
    assert "bi-mat-token" not in f"{cf}"


def test_thong_diep_loi_KHONG_chua_token_secret():
    """Thông điệp lỗi đi thẳng vào log, và đôi khi vào cả trang cho khách."""
    with pytest.raises(proxmox.ChuaCauHinh) as loi:
        proxmox.doc_cau_hinh(_env(LTT_ENV="production"))
    assert "bi-mat-token" not in str(loi.value)


# ── 3. Cách ly ──────────────────────────────────────────────────────────────

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


class _CongVaoGia:
    def __init__(self, hong=False):
        self.hong = hong
        self.da_goi: list[tuple[str, str, str]] = []

    def dong_duong(self, pub, priv):
        if self.hong:
            raise RuntimeError("cong vao khong tra loi")
        self.da_goi.append(("dong", pub, priv))

    def mo_duong(self, pub, priv):
        if self.hong:
            raise RuntimeError("cong vao khong tra loi")
        self.da_goi.append(("mo", pub, priv))


@pytest.fixture()
def cong_vao(monkeypatch):
    from apps.vps.services import gateway
    gia = _CongVaoGia()
    monkeypatch.setattr(gateway, "client_tu_moi_truong", lambda: gia)
    return gia


_DEM = [0]


def _may(db):
    from apps.vps.tables import VpsGateway, VpsInstance, VpsIp
    _DEM[0] += 1
    g = VpsGateway(ten=f"cong-{_DEM[0]}", vung="sgp",
                   ip_cong_khai="203.0.113.10")
    db.add(g)
    db.flush()
    m = VpsInstance(user_id="u1", plan_id="vps-vua", os_id="winsrv2022-gui",
                    gateway_id=g.id, trang_thai="dang_chay",
                    vmid=200 + _DEM[0], ip_noi_bo=f"10.51.0.{_DEM[0]}")
    db.add(m)
    db.flush()
    db.add(VpsIp(gateway_id=g.id, dia_chi=f"203.0.113.{100 + _DEM[0]}",
                 instance_id=m.id))
    db.flush()
    return m


def test_cach_ly_dong_duong_NAT_va_ghi_moc(db, cong_vao):
    may = _may(db)
    cach_ly.cach_ly(db, may, "quet cong hang loat", boi="admin:x", now=NOW)
    assert [x[0] for x in cong_vao.da_goi] == ["dong"]
    assert may.cach_ly_luc == NOW
    assert cach_ly.dang_bi_cach_ly(may) is True


def test_cach_ly_KHONG_tat_may_va_KHONG_dung_toi_dia(db, cong_vao):
    """Tắt máy là cách chắc chắn để mất bằng chứng, và khách cần console để dọn."""
    may = _may(db)
    truoc = may.trang_thai
    cach_ly.cach_ly(db, may, "phat tan thu rac", now=NOW)
    assert may.trang_thai == truoc
    assert may.vong_doi != "da_xoa"


def test_cach_ly_KHONG_dat_moc_xoa_nhu_bi_treo(db, cong_vao):
    """Đây là lý do cách ly phải là một khái niệm riêng.

    `billing.treo` đặt `xoa_sau` bảy ngày. Dùng nó cho lạm dụng là xoá máy của
    một khách **đang trả tiền đầy đủ** sau một tuần vì một cảnh báo mạng.
    """
    may = _may(db)
    cach_ly.cach_ly(db, may, "nghi lam dung", now=NOW)
    assert may.xoa_sau is None
    assert may.vong_doi != "bi_treo"


def test_cach_ly_PHAI_co_ly_do(db, cong_vao):
    """Lý do là thứ người ta đọc lại sau ba tháng để trả lời khách."""
    may = _may(db)
    for rong in ("", "   ", None):
        with pytest.raises(cach_ly.CachLyError):
            cach_ly.cach_ly(db, may, rong, now=NOW)


def test_cach_ly_hai_lan_KHONG_doi_moc_dau_tien(db, cong_vao):
    """Mốc ấy trả lời "máy này bị cắt từ lúc nào"; ghi đè là mất câu trả lời."""
    from datetime import timedelta
    may = _may(db)
    cach_ly.cach_ly(db, may, "lan 1", now=NOW)
    cach_ly.cach_ly(db, may, "lan 2", now=NOW + timedelta(days=1))
    assert may.cach_ly_luc == NOW


def test_cong_vao_hong_van_GHI_SO(db, monkeypatch):
    """Cách ly là một quyết định; nó phải được ghi kể cả khi chưa thi hành được.

    Vòng đối chiếu sẽ thấy một máy `cach_ly_luc` khác NULL mà đường NAT vẫn mở.
    """
    from apps.vps.services import gateway
    monkeypatch.setattr(gateway, "client_tu_moi_truong",
                        lambda: _CongVaoGia(hong=True))
    may = _may(db)
    cach_ly.cach_ly(db, may, "khan cap", now=NOW)
    assert cach_ly.dang_bi_cach_ly(may) is True


def test_go_cach_ly_mo_lai_duong_va_xoa_dau(db, cong_vao):
    may = _may(db)
    cach_ly.cach_ly(db, may, "nham", now=NOW)
    cach_ly.go_cach_ly(db, may, boi="admin:x")
    assert [x[0] for x in cong_vao.da_goi] == ["dong", "mo"]
    assert cach_ly.dang_bi_cach_ly(may) is False


def test_go_cach_ly_KHONG_xoa_dau_khi_chua_mo_duoc_duong(db, monkeypatch):
    """Xoá dấu mà đường vẫn đóng là để lại một máy không vào được **không còn
    dòng nào giải thích vì sao** — loại sự cố tốn cả buổi để dò."""
    from apps.vps.services import gateway
    gia = _CongVaoGia()
    monkeypatch.setattr(gateway, "client_tu_moi_truong", lambda: gia)
    may = _may(db)
    cach_ly.cach_ly(db, may, "x", now=NOW)
    gia.hong = True
    with pytest.raises(cach_ly.CachLyError):
        cach_ly.go_cach_ly(db, may)
    assert cach_ly.dang_bi_cach_ly(may) is True


def test_cai_lai_KHONG_tro_thanh_nut_go_cach_ly(db, monkeypatch):
    """"Cài lại" gọi `_cap_ip_cong_khai`, và hàm đó mở đường NAT.

    Không có phép kiểm ở đó thì khách tự gỡ được cách ly bằng một nút vô hại —
    im lặng, không ghi sổ, và người vận hành vẫn thấy `cach_ly_luc` khác NULL
    nên tưởng máy vẫn bị cắt.
    """
    from tests.test_1013_vps_pinned_provisioning import _ip_context

    jobs, profile, may, gateway, ip, mappings = _ip_context(
        db, monkeypatch, state="BOUND")
    may.cach_ly_luc = NOW
    db.commit()
    assert jobs._cap_ip_cong_khai(
        db, may, gateway, may.ip_noi_bo, profile) == ip.dia_chi
    assert mappings == []
    assert cach_ly.dang_bi_cach_ly(may)

    # Inverse condition: the same path really opens NAT when isolation is off.
    may.cach_ly_luc = None
    db.commit()
    jobs._cap_ip_cong_khai(db, may, gateway, may.ip_noi_bo, profile)
    assert mappings == [("ensure", (ip.dia_chi, may.ip_noi_bo))]


def test_khong_co_vong_lap_nao_TU_DONG_cach_ly():
    """Một tín hiệu heuristic không được tự cắt mạng của khách.

    Băng thông cao hay nhiều kết nối là hình dạng của cả một cuộc tấn công lẫn
    một việc hợp lệ. Tự động hoá bước này là cắt mạng của một khách đang chạy
    một việc đúng, vào lúc họ cần nó nhất.
    """
    import pathlib
    import re

    goc = pathlib.Path("apps/vps")
    goi = []
    for p in goc.rglob("*.py"):
        if p.name == "cach_ly.py":
            continue
        src = re.sub(r'(?s)""".*?"""', " ", p.read_text(encoding="utf-8"))
        src = re.sub(r"(?m)^\s*#.*$", " ", src)
        if re.search(r"\bcach_ly\.cach_ly\s*\(", src):
            goi.append(p.name)
    assert goi == [], f"co cho tu dong cach ly: {goi}"
