"""
test_520 — SỞ HỮU và luật KHAI LÀN của "Giọng của tôi", đi qua đúng cửa web
thật.

Đổi số 396 → 520 (khung từ `git show 29ac2300:tests/test_396_ltt_voice_so_huu.py`
— nhánh chưa từng hoà, viết cho một cửa thu hồi RIÊNG của nó). Ba nhóm giữ
NGUYÊN Ý (① CONSENT, ③ TRÙNG TÊN, ④ CÁCH LY A↔B) vì các cửa chúng đi qua
(`/tao`, `/tat`, `tham_chieu.danh_sach`) đã có mặt từ trước Task 5. Nhóm mới
⑤ là cửa `/ngon-ngu` mà Task 5 vừa thêm (D004).

⛔ ĐÃ BỎ so với `29ac2300`:
  · ca "khai làn rỗng ⇒ chưa biết" — D003 (Task 4) xoá hẳn nhánh "chưa biết";
    ghi danh RC1 LUÔN bắt khai, và ca đó đã chuyển thành
    `test_ghi_danh_KHONG_khai_lan_bi_tu_choi_va_KHONG_tru_tien` ở
    `test_521_ltt_voice_ghi_danh_ngon_ngu.py`.
  · hai ca cần cửa `/giong/{id}/xoa` (thu hồi: "A không XOÁ được giọng của B",
    "thu hồi xoá tệp giữ lịch sử") — cửa đó CHƯA tồn tại ở Task 5
    (`apps/ltt_voice/routes/_p_giong.py` mới chỉ có `/tao`, `/tat`,
    `/ngon-ngu`). Nó là phạm vi Task 6 (`task-6-brief.md`: "Thu hồi giọng +
    worker"), nơi sẽ MỞ RỘNG tệp này bằng đúng hai ca ấy khi route đã có.

Fixture `khach` và các helper `_csrf_giong`/`_tao_giong_active`/
`_ho_so_theo_pid` giữ NGUYÊN tên/chữ ký — Task 6 sẽ tái dùng chúng (xem
`task-6-brief.md`), không phải viết lại.
"""
from __future__ import annotations

import io
import re
import struct
import wave

import pytest


# ── một clip WAV hợp lệ (4 giây, có tín hiệu, qua được `audio_input.kiem`) ────
def _wav(giay: float = 4.0, sr: int = 8000) -> bytes:
    n = int(giay * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        # Sóng vuông biên ~0,1 (đỉnh > 0,05 nên không có cảnh báo "âm lượng nhỏ",
        # không chạm trần 0,995 nên không "vỡ tiếng").
        mau = bytearray()
        for i in range(n):
            v = 3200 if (i // 200) % 2 == 0 else -3200
            mau += struct.pack("<h", v)
        w.writeframes(bytes(mau))
    return buf.getvalue()


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm. Cùng khuôn với
    `test_519`/`test_521` — chỉ đổi DB/email/secret sang `voice-520`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-520.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-520")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    from platform_core import credit
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-520@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_520")
        uid = str(u.id)
        db.commit()
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
    r = client.post("/login", data={"username": "voice-520@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)

    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf_giong(client) -> str:
    r = client.get("/ltt-voice/giong")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    assert m, "khong lay duoc csrf_token tu trang giong"
    return m.group(1)


def _tao_giong(client, ten="Giong A", ngon_ngu="vi", dong_y="1"):
    return client.post(
        "/ltt-voice/giong/tao",
        data={"ten": ten, "dong_y": dong_y, "ngon_ngu": ngon_ngu,
              "csrf_token": _csrf_giong(client)},
        files={"tep": ("clip.wav", _wav(), "audio/wav")})


def _profile(public_id):
    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        return db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == public_id)).scalar_one_or_none()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _profile_cua_B(ten="Giong cua B"):
    from apps.ltt_voice.tables import VoiceProfile
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        h = VoiceProfile(owner_id="user-b-0000", ten_hien_thi=ten,
                         trang_thai="active")
        db.add(h)
        db.commit()
        return h.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _tao_giong_active(owner: str, *, ngon_ngu: str, nguon: str,
                      trang_thai: str = "active") -> str:
    """Ghi THẲNG một `VoiceProfile` qua session, bỏ qua cửa `/tao` — dùng khi
    bài kiểm chỉ cần một hồ sơ Ở SẴN một (trạng thái, làn, nguồn) cho trước,
    không cần đi lại đường ghi danh thật. Tên tự sinh (`uuid4`) để gọi nhiều
    lần trong cùng một bài kiểm không đụng `uq_voice_owner_ten`."""
    import uuid

    from apps.ltt_voice.tables import VoiceProfile
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        h = VoiceProfile(owner_id=str(owner),
                         ten_hien_thi=f"Giong {uuid.uuid4().hex[:8]}",
                         ngon_ngu=ngon_ngu, ngon_ngu_nguon=nguon,
                         trang_thai=trang_thai)
        db.add(h)
        db.commit()
        return h.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _ho_so_theo_pid(pid: str):
    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        return db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == pid)).scalar_one_or_none()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── ① CONSENT ────────────────────────────────────────────────────────────────

def test_khong_dong_y_thi_KHONG_ghi_danh(khach):
    client, uid = khach
    r = _tao_giong(client, dong_y="0")
    assert r.status_code == 400
    assert "voice_id" not in r.text
    # Không hồ sơ nào được tạo.
    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import func, select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        so = db.execute(select(func.count()).select_from(VoiceProfile)).scalar()
        assert so == 0, "tao ho so du khong co cam ket"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_dong_y_ghi_MOT_ban_consent_co_owner_va_phien_ban(khach):
    client, uid = khach
    r = _tao_giong(client, ten="Giong co consent", ngon_ngu="vi")
    assert r.status_code == 200, r.text
    from apps.ltt_voice.tables import VoiceConsent
    from apps.ltt_voice.dieu_khoan import PHIEN_BAN_DIEU_KHOAN
    from sqlalchemy import select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        cs = db.execute(select(VoiceConsent)).scalars().all()
        assert len(cs) == 1
        assert cs[0].owner_id == uid
        assert cs[0].phien_ban_dieu_khoan == PHIEN_BAN_DIEU_KHOAN
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── ② LÀN (chỉ ca EN cụ thể — ca "rỗng" đã chuyển sang test_521, D003) ───────

def test_khai_lan_EN_luu_khai_bao(khach):
    client, uid = khach
    r = _tao_giong(client, ten="Giong Anh", ngon_ngu="en")
    assert r.status_code == 200, r.text
    h = _profile(r.json()["voice_id"])
    assert (h.ngon_ngu, h.ngon_ngu_nguon) == ("en", "khai_bao")


# ── ③ TRÙNG TÊN ──────────────────────────────────────────────────────────────

def test_trung_ten_tra_cau_sua_duoc_khong_de_lai_tep_mo_coi(khach):
    client, uid = khach
    r1 = _tao_giong(client, ten="Trung ten", ngon_ngu="vi")
    assert r1.status_code == 200, r1.text
    r2 = _tao_giong(client, ten="Trung ten", ngon_ngu="vi")
    assert r2.status_code == 400
    d = r2.json()
    # Câu người đọc được, KHÔNG phải lỗi CSDL thô.
    assert "IntegrityError" not in d["loi"] and "UNIQUE" not in d["loi"].upper()
    assert "tên" in d["loi"].lower() or "ten" in d["loi"].lower()
    # Chỉ một hồ sơ, và đúng một tệp nguồn (lượt trùng không để lại rác).
    from apps.ltt_voice.tables import VoiceProfile, VoiceRef
    from sqlalchemy import func, select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        assert db.execute(select(func.count()).select_from(VoiceProfile)).scalar() == 1
        assert db.execute(select(func.count()).select_from(VoiceRef)).scalar() == 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── ④ CÁCH LY A ↔ B (phần KHÔNG cần cửa `/xoa` — Task 6) ─────────────────────

def test_A_khong_TAT_duoc_giong_cua_B(khach):
    client, uid = khach
    pidB = _profile_cua_B()
    r = client.post(f"/ltt-voice/giong/{pidB}/tat",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 404, r.text
    assert _profile(pidB).trang_thai == "active", "giong B bi doi trang thai"


def test_A_khong_XOA_duoc_giong_cua_B(khach):
    client, uid = khach
    pidB = _profile_cua_B()
    r = client.post(f"/ltt-voice/giong/{pidB}/xoa",
                    data={"csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 404, r.text
    assert _profile(pidB).trang_thai == "active", "giong B bi doi trang thai"


def test_A_khong_LIET_KE_duoc_giong_rieng_cua_B(khach):
    client, uid = khach
    pidB = _profile_cua_B()
    _tao_giong(client, ten="Giong A that")
    from apps.ltt_voice import tham_chieu
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        ds = tham_chieu.danh_sach(db, owner_id=uid, gom_dung_chung=True)
        ids = {g.public_id for g in ds}
        assert pidB not in ids, "giong rieng cua B lot vao danh sach cua A"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── ⑤ CỬA KHAI LÀN — `/giong/{id}/ngon-ngu` (D004, Task 5) ───────────────────

def test_khai_lan_nguoc_PHEP_DO_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="do_asr")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400 and r.json()["ma_loi"] == "voice_language_measured"


def test_khai_lan_mac_dinh_cu_thanh_khai_bao(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="mac_dinh_cu")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)})
    assert r.status_code == 303
    ho_so = _ho_so_theo_pid(pid)
    assert (ho_so.ngon_ngu, ho_so.ngon_ngu_nguon) == ("en", "khai_bao")


def test_khai_lan_giong_NGUOI_KHAC_khong_duoc(khach):
    client, uid = khach
    pid = _tao_giong_active("nguoi-khac-uuid", ngon_ngu="vi", nguon="khai_bao")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code in (400, 404)
    assert _ho_so_theo_pid(pid).ngon_ngu == "vi"


def test_khai_lan_giong_DA_THU_HOI_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400
    assert r.json()["ma_loi"] == "voice_revoked"


def test_doi_lan_XOA_tep_nghe_thu_cu(khach):
    """🔴 D004 + preview: tệp nghe thử CŨ (làn cũ) không được sống sót một lượt
    đổi làn thật — nó đọc câu SAI làn, và không có gì huỷ nó ngoài đúng cửa
    này (`nghe_thu.dung_lai_cho_giong`, gọi SAU `db.commit()` — xem review
    round 1)."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
    khoa = nghe_thu.khoa_rieng(uid, pid)
    st = get_storage()
    st.put(khoa, io.BytesIO(b"tep nghe thu GIA cua lan CU"),
          content_type="audio/wav")
    assert st.exists(khoa), "chua dung duoc tien de: tep phai co truoc"

    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 200, r.text

    assert not st.exists(khoa), "tep nghe thu lan CU van con sau khi doi lan"


# ── `nghe_thu.bao_tri`: bước dựng lại preview còn thiếu cho giọng NHÂN ────────
# ── BẢN của khách (khác nguồn với giọng mẫu) — review round 1, IMPORTANT 1 ────

def _them_bieu_dien_gia(uid: str, pid: str):
    """Ghi một `VoiceRepr` + một tệp `.npz` giả — đủ để `tham_chieu.
    tim_repr_active`/`nap_ref_b64` đọc được mà không cần engine thật."""
    from apps.ltt_voice.tables import VoiceRepr
    from platform_core.storage import get_storage
    import platform_core.db as dbmod

    khoa = f"voice/{uid}/{pid}/repr-fake.npz"
    get_storage().put(khoa, io.BytesIO(b"embedding gia"),
                      content_type="application/octet-stream")
    gen = dbmod.get_session()
    db = next(gen)
    try:
        hs = _ho_so_theo_pid(pid)
        db.add(VoiceRepr(profile_id=hs.id, ref_id=0, engine="vieneu",
                         storage_key=khoa, fingerprint="fake",
                         trang_thai="dang_dung"))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_bao_tri_dung_giong_rieng_bo_qua_da_co_va_khong_co_bieu_dien(khach, monkeypatch):
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    # (1) Giọng ĐÃ CÓ preview -> KHÔNG được dựng lại (tốn công vô ích).
    pid_da_co = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
    khoa_da_co = nghe_thu.khoa_rieng(uid, pid_da_co)
    get_storage().put(khoa_da_co, io.BytesIO(b"da co san"), content_type="audio/wav")
    _them_bieu_dien_gia(uid, pid_da_co)

    # (2) Giọng THIẾU preview, CÓ biểu diễn -> PHẢI được dựng, đúng LÀN của nó.
    pid_thieu = _tao_giong_active(uid, ngon_ngu="en", nguon="khai_bao")
    _them_bieu_dien_gia(uid, pid_thieu)

    # (3) Giọng THIẾU preview, KHÔNG có biểu diễn -> BỎ QUA, không ném.
    pid_khong_bieu_dien = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")

    goi = []
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **kw: (goi.append((khoa, kw)), True)[1])

    nghe_thu._dung_giong_rieng_con_thieu()

    khoa_thieu = nghe_thu.khoa_rieng(uid, pid_thieu)
    khoa_khong_bd = nghe_thu.khoa_rieng(uid, pid_khong_bieu_dien)
    da_goi = dict(goi)
    assert khoa_thieu in da_goi, "giong thieu preview + co bieu dien phai duoc dung"
    assert khoa_da_co not in da_goi, "giong DA CO preview khong duoc dung lai"
    assert khoa_khong_bd not in da_goi, "giong khong co bieu dien phai bi bo qua"
    assert da_goi[khoa_thieu].get("ngon_ngu") == "en", (
        "phai dung theo LAN HIEN TAI cua ho so, khong phai mac dinh")


def test_bao_tri_dung_giong_rieng_ton_trong_tran(khach, monkeypatch):
    client, uid = khach
    from apps.ltt_voice import nghe_thu

    so_giong = nghe_thu.TOI_DA_GIONG_RIENG_MOI_LUOT + 3
    for _ in range(so_giong):
        pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
        _them_bieu_dien_gia(uid, pid)

    goi = []
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **kw: (goi.append(khoa), True)[1])

    nghe_thu._dung_giong_rieng_con_thieu()

    assert len(goi) == nghe_thu.TOI_DA_GIONG_RIENG_MOI_LUOT, (
        f"dung {len(goi)} tep cho {so_giong} giong dang thieu — tran khong duoc tuan thu")


# ── ⑥ THU HỒI + WORKER — Task 6 (T-07, T-14, INV-THU-HOI-1) ──────────────────
#
# ⛔ `test_thu_hoi_xoa_CA_TIEN_TO_giu_ho_so` của brief gốc (task-6-brief.md)
#    dựng 4 tệp bất kỳ dưới `voice/{uid}/{pid}/` (kể cả hai "phiên bản nghe
#    thử cũ" không hàng CSDL nào trỏ tới) rồi đòi CẢ BỐN biến mất sau khi thu
#    hồi. Điều đó đòi một API liệt-kê-theo-tiền-tố ở `platform_core.storage`
#    — xác nhận lại ở Task 6 (đã xác nhận từ Task 5 review): `Storage`/
#    `LocalStorage` KHÔNG có hàm đó, và task này KHÔNG được thêm nó (thay đổi
#    tầng nền tảng, ngoài phạm vi một task app — xem `khoa_can_xoa` bên dưới).
#
#    ⇒ Bài dưới đây đo đúng những gì hiện thực THẬT sự làm: xoá mọi khoá mà
#      `giong_vong_doi.khoa_da_biet` BIẾT (nguồn qua `VoiceRef`, biểu diễn
#      qua `VoiceRepr`, bản nghe thử HIỆN HÀNH qua `nghe_thu.khoa_rieng`) —
#      không phải "mọi khoá dưới tiền tố". Một bản nghe thử của một
#      `PHIEN_BAN` engine CŨ hơn (nếu còn sót từ một lần nâng cấp) sẽ KHÔNG bị
#      dọn bằng thu hồi — hạn chế đã ghi trong docstring `khoa_can_xoa` và
#      trong `task-6-report.md`.

def test_thu_hoi_xoa_CAC_KHOA_DA_BIET_giu_ho_so(khach):
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from apps.ltt_voice.tables import VoiceRef, VoiceRepr
    from platform_core.storage import get_storage
    import platform_core.db as dbmod

    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
    st = get_storage()
    khoa_nguon = f"voice/{uid}/{pid}/nguon.wav"
    khoa_repr = f"voice/{uid}/{pid}/repr.npz"
    khoa_preview = nghe_thu.khoa_rieng(uid, pid)
    for k in (khoa_nguon, khoa_repr, khoa_preview):
        st.put(k, io.BytesIO(b"x"), content_type="application/octet-stream")

    gen = dbmod.get_session()
    db = next(gen)
    try:
        hs = _ho_so_theo_pid(pid)
        db.add(VoiceRef(profile_id=hs.id, storage_key=khoa_nguon,
                        sha256="a" * 64, mime="audio/wav"))
        db.add(VoiceRepr(profile_id=hs.id, ref_id=0, engine="vieneu",
                         storage_key=khoa_repr, fingerprint="f",
                         trang_thai="dang_dung"))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 303
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"
    for k in (khoa_nguon, khoa_repr, khoa_preview):
        assert not st.exists(k), k


def test_thu_hoi_khi_DANG_GHI_DANH_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def _dat_nguon(uid: str, pid: str) -> str:
    """Ghi một clip NGUỒN giả vào đúng khoá mà `tham_chieu.luu_nguon` dùng —
    để `jobs._ghi_danh` đọc được nó qua `params["source_key"]`, cùng khuôn
    `tao_giong` (`routes/_p_giong.py`)."""
    from apps.ltt_voice import tham_chieu
    return tham_chieu.luu_nguon(owner_id=uid, public_id=pid, data=b"gia-nguon",
                                mime="audio/wav")


def _params_ghi_danh(uid: str, pid: str) -> dict:
    """Params dựng THẲNG cho `jobs._ghi_danh(params)`, cùng hình dạng
    `tao_giong` gửi vào job. ĐỘC LẬP với `_dat_nguon` (không nhận khoá làm
    tham số) nhưng vẫn khớp khoá: cả hai cùng suy `source_key` từ
    `tham_chieu.khoa_nguon(uid, pid) + ".wav"` — đúng kết quả `luu_nguon` trả
    về cho `mime="audio/wav"` (`tham_chieu.luu_nguon`, đuôi `.wav`)."""
    from apps.ltt_voice import tham_chieu
    khoa = f"{tham_chieu.khoa_nguon(uid, pid)}.wav"
    return {"owner_id": uid, "voice_id": pid, "source_key": khoa, "ref_id": 0,
           "nguon": "giong", "_job_type": "ltt_voice.enroll"}


def test_worker_KHONG_bat_lai_giong_da_thu_hoi(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    from apps.ltt_voice import jobs, sidecar_client
    from apps.ltt_voice.features import LoiGiongNoi
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": "QUJD", "chon_doan": {}})
    _dat_nguon(uid, pid)  # helper: put một clip nguồn vào kho đúng khoá jobs đọc
    # ⛔ `LoiGiongNoi`, KHÔNG `Exception` trần (bánh cóc ruff B017 chặn
    #    `pytest.raises(Exception)` — quá rộng để chứng minh đúng nhánh nào đã
    #    ném). `_ghi_danh` ném đúng lớp này khi UPDATE kích hoạt khớp 0 dòng
    #    (`jobs.py::_ghi`, T-07).
    with pytest.raises(LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))  # helper dựng params như tao_giong
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"


def test_ghi_danh_hong_VINH_VIEN_dat_loi(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client
    from apps.ltt_voice.features import LoiGiongNoi

    def _hong(*a, **k):
        raise LoiGiongNoi("clip hong")
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong)
    _dat_nguon(uid, pid)
    with pytest.raises(LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"
