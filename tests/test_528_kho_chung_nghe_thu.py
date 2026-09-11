r"""T-08/T-09 — NGHE THỬ CHO GIỌNG KHO CHUNG, và bề mặt ASV (T-13).

## Vì sao `voice/chung/` là một tiền tố THỨ TƯ, không phải một nhánh của `rieng`

`khoa_rieng(owner_id, pid)` tra tệp dưới CHỦ SỞ HỮU. Giọng kho chung không
thuộc người xem trang — nên gộp nó vào `rieng` là tra một khoá không bao giờ
tồn tại, và nút nghe thử của nó biến mất **im lặng**, không lỗi nào báo.
`nghe_thu.khoa_chung` + tham số `chung=` của `duong_cho_trang` tồn tại đúng để
đóng lỗ đó — xem chú thích ở `nghe_thu.py`.

## Vì sao `duong_cho_app_khac` phải sống trong `BE_MAT_CONG_KHAI`

`apps/auto_scan_video/gia.py` (nhánh `phien/asv-v4`) import hàm này qua
`try/except`. Mất nó không đỏ ở đâu cả trên nhánh này — ASV không nằm trong
cây ta đang sửa — nhưng preview giọng của ASV biến mất im lặng trên nhánh kia.
`INV-BE-MAT-1` chốt nó vẫn còn.
"""
from __future__ import annotations

import io
import re
import struct
import uuid

import pytest

UID_CHU_KHO_CHUNG = "00000000-0000-0000-0000-0000000000ee"


def _wav(giay: float = 0.2, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập — KHÔNG PHẢI chủ giọng kho chung sẽ dựng ở mỗi
    test (`_tao_giong_chung` luôn gán `owner_id=UID_CHU_KHO_CHUNG`, khác uid
    của phiên này). Chép khuôn từ `test_500`/`test_357`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'kho-chung.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-kho-chung")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="kho-chung@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    assert m
    r = client.post("/login", data={"username": "kho-chung@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


# ── Helpers — nhớ đọc TÊN THẬT trong nghe_thu.py/tham_chieu.py trước khi viết
#    (`co_san`, `nap_ref_b64`, `khoa_chung`, `_dieu_kien_kho_chung`, ...);
#    ba tên này là của riêng bộ test, không có ở nguồn. ──────────────────────

def _tao_giong_chung(*, ngon_ngu: str = "en", owner_id: str = "") -> str:
    """Một `VoiceProfile` kho chung `active`, `license_status="ok"`. Mặc định
    chủ KHÁC người đang đăng nhập ở fixture `khach` (`UID_CHU_KHO_CHUNG`);
    truyền `owner_id=uid` để dựng giọng kho chung CỦA CHÍNH khách đang đăng
    nhập (cần cho các phép kiểm thu hồi/đổi làn — chỉ chủ mới gọi được hai
    cửa đó)."""
    import platform_core.db as dbmod
    from apps.ltt_voice.tables import VoiceProfile

    gen = dbmod.get_session()
    db = next(gen)
    try:
        ho_so = VoiceProfile(
            owner_id=(owner_id or UID_CHU_KHO_CHUNG),
            ten_hien_thi=f"Kho chung {ngon_ngu} {uuid.uuid4().hex[:8]}",
            ngon_ngu=ngon_ngu, ngon_ngu_nguon="khai_bao",
            trang_thai="active", dung_chung=True, license_status="ok")
        db.add(ho_so)
        db.commit()
        return ho_so.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice/giong").text)
    assert m
    return m.group(1)


def _dat_preview_chung(pid: str) -> None:
    """PUT một tệp WAV giả vào đúng khoá của `nghe_thu.khoa_chung(pid)`."""
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage
    get_storage().put(nghe_thu.khoa_chung(pid), io.BytesIO(_wav()),
                      content_type="audio/wav")


def _ds_mot_giong_chung() -> list:
    """`[(VoiceProfile-giả, bieu_dien-giả)]` — hình dạng của
    `tham_chieu.danh_sach_kho_chung(db)`, dựng KHÔNG cần CSDL thật. Chỉ
    `.public_id`/`.ngon_ngu` của phần tử đầu được `nghe_thu._dung_kho_chung`
    đọc trước cửa `co_san`."""
    from types import SimpleNamespace
    ho_so = SimpleNamespace(public_id="vc_" + "7" * 32, ngon_ngu="vi")
    return [(ho_so, object())]


# ── PULLED IN item 5 (fix round 1/5) — dung_chung=True nhưng license CHƯA
#    "ok" phải rơi về `rieng=`, không phải `chung=` (nơi nó không bao giờ có
#    preview thật). Xem `tham_chieu.tach_rieng_chung`. ───────────────────────

def test_tach_rieng_chung_dung_chung_CHUA_license_ok_ROI_VE_rieng():
    """Phép kiểm THUẦN (không CSDL/HTTP) cho chính hàm tách."""
    from types import SimpleNamespace

    from apps.ltt_voice import tham_chieu
    da = SimpleNamespace(public_id="vc_a", dung_chung=True,
                         license_status="cho_soat")
    db_ = SimpleNamespace(public_id="vc_b", dung_chung=True,
                          license_status="ok")
    dc = SimpleNamespace(public_id="vc_c", dung_chung=False,
                         license_status="")
    dd = SimpleNamespace(public_id="vc_d", dung_chung=True,
                         license_status="tu_choi")
    rieng, chung = tham_chieu.tach_rieng_chung([da, db_, dc, dd])
    assert sorted(rieng) == ["vc_a", "vc_c", "vc_d"], (
        "dung_chung=True nhung license CHUA/KHONG 'ok' phai roi ve rieng=")
    assert chung == ["vc_b"]


def test_owner_giong_dung_chung_CHUA_license_ok_VAN_co_nut_nghe_thu(khach):
    """🔴 Đầu-cuối cho phép kiểm thuần ở trên: chủ một giọng ĐÃ `dung_chung=
    True` (đưa vào diện xét kho chung) nhưng license CHƯA `"ok"` (đang chờ
    soát) vẫn phải thấy nút nghe thử trên trang của chính họ — trỏ tới bản
    nghe thử RIÊNG dựng lúc ghi danh (`khoa_rieng`), vì `khoa_chung` của
    giọng này sẽ KHÔNG BAO GIỜ được vòng bảo trì dựng (license chưa "ok")."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid = _tao_giong_chung(owner_id=uid, ngon_ngu="vi")
    # `_tao_giong_chung` dựng license_status="ok" mặc định — hạ nó xuống
    # "cho_soat" NGAY SAU để mô phỏng đúng ô đang kiểm: dung_chung=True
    # nhưng license CHƯA ok.
    import platform_core.db as dbmod
    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import select
    gen = dbmod.get_session()
    db = next(gen)
    try:
        ho_so = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == pid)).scalar_one()
        ho_so.license_status = "cho_soat"
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    khoa_rieng_ = nghe_thu.khoa_rieng(uid, pid)
    get_storage().put(khoa_rieng_, io.BytesIO(_wav()), content_type="audio/wav")

    trang = client.get("/ltt-voice").text
    m = re.search(rf'data-nghe="([^"]*{pid}[^"]*)"', trang)
    assert m, ("giong dung_chung=True nhung license CHUA ok phai VAN co nut "
              "nghe thu (qua ban rieng luc ghi danh)")
    assert khoa_rieng_ in m.group(1), (
        "phai tro toi ban nghe thu RIENG (enrol-time), khong phai khoa_chung "
        "— khoa_chung cua giong nay se khong bao gio duoc dung")


# ── T-08/T-09: preview kho chung ─────────────────────────────────────────────

def test_nguoi_KHONG_phai_chu_nghe_duoc_preview_kho_chung(khach):
    """🔴 MỆNH ĐỀ TRUNG TÂM: một khách KHÔNG PHẢI chủ sở hữu của giọng kho
    chung vẫn thấy nút nghe thử trên trang, và tệp đó đọc được (200) — đúng
    định nghĩa "kho chung"."""
    client, uid = khach
    pid = _tao_giong_chung(ngon_ngu="en")
    _dat_preview_chung(pid)
    trang = client.get("/ltt-voice").text
    m = re.search(rf'data-nghe="([^"]*{pid}[^"]*)"', trang)
    assert m, "the giong kho chung khong co nut nghe thu"
    assert client.get(m.group(1)).status_code == 200


def test_giong_chung_KHONG_co_preview_thi_KHONG_hien_nut(khach):
    """Đối chứng: chưa có tệp preview (`_dat_preview_chung` chưa chạy) thì
    KHÔNG dựng nút — hợp đồng "vắng mặt khỏi dict, không phải 404"."""
    client, uid = khach
    pid = _tao_giong_chung(ngon_ngu="vi")
    trang = client.get("/ltt-voice").text
    m = re.search(rf'data-nghe="([^"]*{pid}[^"]*)"', trang)
    assert m is None, "khong duoc dung nut nghe thu khi chua co tep preview"


# ── IMPORTANT 1 (fix round 1/5) — thu hồi / đổi làn PHẢI xoá luôn preview
#    kho chung, không chỉ preview riêng. Xem khối chú thích ở
#    `giong_vong_doi.khoa_da_biet` và `nghe_thu.dung_lai_cho_giong`. ─────────

def test_thu_hoi_giong_kho_chung_XOA_luon_ban_nghe_thu_chung(khach):
    """🔴 MỆNH ĐỀ TRUNG TÂM (privacy). Trước bản vá: thu hồi (`/xoa`) một
    giọng đã từng ra kho chung chỉ xoá bản nghe thử RIÊNG — bản KHO CHUNG vẫn
    tải được cho MỌI khách khác mãi mãi, trái với lời hứa "quyền được xoá"
    của `_thu_hoi_mot`."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid = _tao_giong_chung(owner_id=uid, ngon_ngu="en")
    _dat_preview_chung(pid)
    khoa = nghe_thu.khoa_chung(pid)
    assert get_storage().exists(khoa), "chua dat duoc tep preview de kiem xoa"
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 200

    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf(client)})
    assert r.status_code in (200, 303), r.text

    assert not get_storage().exists(khoa), (
        "thu hoi giong kho chung KHONG xoa ban nghe thu KHO CHUNG cua no")
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404


def test_doi_lan_giong_kho_chung_XOA_luon_ban_nghe_thu_chung_CU(khach):
    """Cùng chốt trên, ở cửa đổi làn (`/ngon-ngu`, D004): bản nghe thử kho
    chung CŨ (đọc câu của làn cũ) phải mất đi ngay khi làn đổi — phục vụ tiếp
    là phục vụ nhầm nội dung cho những khách KHÁC đang nghe thử giọng này."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid = _tao_giong_chung(owner_id=uid, ngon_ngu="vi")
    _dat_preview_chung(pid)
    khoa = nghe_thu.khoa_chung(pid)
    assert get_storage().exists(khoa)

    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 200, r.text
    assert r.json().get("ngon_ngu") == "en"

    assert not get_storage().exists(khoa), (
        "doi lan tren giong kho chung KHONG xoa ban nghe thu CHUNG cu")


# ── T-13: bề mặt cho app khác (ASV) ──────────────────────────────────────────

def test_be_mat_cong_khai_giu_ca_hai_duong_cho_app_khac():
    """INV-BE-MAT-1: ASV (`apps/auto_scan_video/gia.py`) import hàm này trong
    `try/except` — mất nó thì preview giọng của ASV biến mất IM LẶNG, không
    đỏ ở đâu cả."""
    import apps.ltt_voice as V
    from apps.ltt_voice import nghe_thu
    for ten in ("duong_cho_trang", "duong_cho_app_khac"):
        assert ten in str(V.BE_MAT_CONG_KHAI), ten
        assert callable(getattr(nghe_thu, ten))


def test_duong_cho_app_khac_di_qua_duong_cho_trang():
    """`duong_cho_app_khac` không tự ghép URL — nó gọi lại `duong_cho_trang`
    (MỘT thẩm quyền, xem docstring cả hai)."""
    from apps.ltt_voice import nghe_thu
    import inspect
    src = inspect.getsource(nghe_thu.duong_cho_app_khac)
    assert "duong_cho_trang(" in src


# ── Ngân sách bảo trì: kiểm `co_san` TRƯỚC khi giải mã biểu diễn ────────────

def test_bao_tri_KHONG_tai_ref_khi_preview_da_co(monkeypatch):
    """🔴 `_dung_kho_chung` phải hỏi `co_san` TRƯỚC `nap_ref_b64` — nạp là một
    lượt đọc kho + giải mã base64 không rẻ, và ở lượt bảo trì bình thường phần
    lớn giọng kho chung ĐÃ có tệp nghe thử rồi."""
    from apps.ltt_voice import nghe_thu, tham_chieu
    goi = []
    monkeypatch.setattr(tham_chieu, "nap_ref_b64",
                        lambda *a, **k: goi.append(1) or "QUJD")
    monkeypatch.setattr(nghe_thu, "co_san", lambda *a, **k: True)
    nghe_thu._dung_kho_chung(_ds_mot_giong_chung())
    assert goi == [], "da goi nap_ref_b64 du co_san da noi CO san"


def test_bao_tri_CO_tai_ref_khi_preview_con_thieu(monkeypatch):
    """Đối chứng cho phép kiểm trên: `co_san=False` thì `nap_ref_b64` PHẢI
    được gọi, và `dung()` phải nhận đúng `ngon_ngu` của hồ sơ."""
    from apps.ltt_voice import nghe_thu, tham_chieu
    goi_nap = []
    goi_dung = []
    monkeypatch.setattr(tham_chieu, "nap_ref_b64",
                        lambda *a, **k: goi_nap.append(1) or "QUJD")
    monkeypatch.setattr(nghe_thu, "co_san", lambda *a, **k: False)
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **k: goi_dung.append(k) or True)
    da = nghe_thu._dung_kho_chung(_ds_mot_giong_chung())
    assert goi_nap == [1]
    assert da == 1
    assert goi_dung and goi_dung[0].get("ngon_ngu") == "vi"


def _ds_nhieu_giong_chung(n: int) -> list:
    """`n` mục kho chung GIẢ, mỗi mục một `public_id` riêng — cho phép kiểm
    trần theo LƯỢT THỬ (không theo lượt thành công)."""
    from types import SimpleNamespace
    return [(SimpleNamespace(public_id=f"vc_{i:032d}", ngon_ngu="vi"),
             object()) for i in range(n)]


def test_bao_tri_DEM_LUOT_THU_khong_dem_LUOT_THANH_CONG(monkeypatch):
    """🔴 IMPORTANT 2 (fix round 1/5): một engine ĐANG HỎNG (`dung()` luôn trả
    `False`) không được phép làm vòng lặp bỏ qua trần — mỗi lượt gọi `dung()`
    (dù thành công hay không) đều phải tính vào ngân sách `con`, đúng cách
    `_dung_giong_rieng_con_thieu` đã làm. Không có chốt này, một lượt bảo trì
    khi engine hỏng sẽ thử dựng LẠI MỌI giọng kho chung còn thiếu trong CÙNG
    một lượt — mỗi lượt thử có thể treo tới 900 giây (trần mặc định của
    `features.goi_cong` khi không truyền `timeout`)."""
    from apps.ltt_voice import nghe_thu, tham_chieu
    goi_dung = []
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda *a, **k: "QUJD")
    monkeypatch.setattr(nghe_thu, "co_san", lambda *a, **k: False)
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **k: goi_dung.append(khoa) or False)

    con = 3
    ds = _ds_nhieu_giong_chung(con + 5)  # nhieu hon tran han
    da = nghe_thu._dung_kho_chung(ds, con=con)

    assert da == con, "tran phai dem theo LUOT THU, khong phai luot THANH CONG"
    assert len(goi_dung) == con, (
        "engine hong van phai bi CHAN o tran — khong duoc thu dung LAI moi "
        "giong con thieu trong cung mot luot")
