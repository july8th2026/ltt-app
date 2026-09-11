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


def test_hai_ho_so_KHAC_TEN_cung_CLIP_deu_co_job_RIENG_khong_trung_khoa(khach):
    """🔴 Fix round 2 (item 9 — regression của chính round 1). Round 1 đổi khoá
    dedupe ghi danh (`_p_giong.py::tao_giong`) từ `(owner, ten)` sang
    `(owner, sha256_clip)`, với lý lẽ "cùng clip là cùng một việc". Đó là một
    lỗi THẬT: hai lượt ghi danh HỢP LỆ của CÙNG một clip nhưng KHÁC TÊN (hai
    tab, hoặc cố ý tạo hai hồ sơ từ một bản thu) sẽ TRÙNG khoá trong lúc job
    đầu còn `queued` — `jobs.submit` trả lại JOB THỨ NHẤT cho lượt thứ hai, nên
    hồ sơ thứ hai không bao giờ có job nào trỏ tới (kẹt vĩnh viễn ở
    `dang_ghi_danh`), và response của lượt hai trả `voice_id` của hồ sơ hai
    kèm `job_id` của hồ sơ MỘT — hai giá trị không khớp nhau.

    Khoá ĐÚNG (ruling round 2) là danh tính của CHÍNH HỒ SƠ vừa tạo
    (`ho_so.public_id`): mỗi lượt ghi danh hợp lệ luôn tạo một hàng
    `VoiceProfile` MỚI, nên hai lượt khác tên/khác public_id không bao giờ
    trùng khoá — HAI job riêng, mỗi job tham chiếu ĐÚNG hồ sơ của lượt đã tạo
    ra nó. TestClient không chạy worker nền nên job đầu chắc chắn còn
    `queued` khi lượt hai được nộp — đúng kịch bản "job trước còn chạy".
    """
    client, uid = khach
    clip = _wav()  # CÙNG bytes cho cả hai lượt — cố ý.

    r1 = client.post(
        "/ltt-voice/giong/tao",
        data={"ten": "Ban ghi A", "dong_y": "1", "ngon_ngu": "vi",
              "csrf_token": _csrf_giong(client)},
        files={"tep": ("clip.wav", clip, "audio/wav")})
    assert r1.status_code == 200, r1.text
    d1 = r1.json()

    r2 = client.post(
        "/ltt-voice/giong/tao",
        data={"ten": "Ban ghi B", "dong_y": "1", "ngon_ngu": "vi",
              "csrf_token": _csrf_giong(client)},
        files={"tep": ("clip.wav", clip, "audio/wav")})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()

    # Hai hồ sơ khác nhau, và mỗi response mang ĐÚNG cặp voice_id/job_id của
    # chính lượt đó — không lệch chéo.
    assert d1["voice_id"] != d2["voice_id"]
    assert d1["job_id"] != d2["job_id"], (
        "hai lượt khác tên bị GỘP một job — đúng hồi quy round 1")

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.models import Job
    from sqlalchemy import func, select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        assert db.execute(
            select(func.count()).select_from(VoiceProfile)).scalar() == 2
        assert db.execute(select(func.count()).select_from(Job)).scalar() == 2

        j1 = db.get(Job, d1["job_id"])  # `Job.id` la chuoi UUID, khong phai int
        j2 = db.get(Job, d2["job_id"])
        assert j1 is not None and j2 is not None
        # Job của lượt 1 tham chiếu ĐÚNG hồ sơ của lượt 1 — không phải hồ sơ
        # của lượt 2 (và ngược lại). Đây là chính đường mà round 1 làm sai.
        assert j1.params.get("voice_id") == d1["voice_id"]
        assert j2.params.get("voice_id") == d2["voice_id"]

        # Không hồ sơ nào mồ côi: cả hai đều còn `dang_ghi_danh` (bình thường
        # — không worker nào chạy trong test), nhưng cả hai đều có MỘT job
        # đang chạy tham chiếu chính nó, không phải kẹt vĩnh viễn không job.
        p1 = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == d1["voice_id"])).scalar_one()
        p2 = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == d2["voice_id"])).scalar_one()
        assert p1.trang_thai == "dang_ghi_danh"
        assert p2.trang_thai == "dang_ghi_danh"
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


# ── Task 11, carried item (c) — giọng `dung_chung=True` NHƯNG license CHƯA
#    "ok" phải VẪN được bước RIÊNG này dựng lại, không bị loại vì mang cờ
#    `dung_chung`. Xem chú thích ở `nghe_thu._dung_giong_rieng_con_thieu`. ────

def test_bao_tri_dung_giong_rieng_GOM_dung_chung_CHUA_du_dieu_kien(khach, monkeypatch):
    """🔴 MỆNH ĐỀ TRUNG TÂM. Trước fix: SQL lọc thẳng `dung_chung.is_(False)`,
    nên một giọng đã `dung_chung=True` (đưa vào diện xét kho chung) nhưng
    `license_status` CHƯA `"ok"` (đang chờ soát — `tach_rieng_chung` xếp nó
    vào `rieng=`, xem `test_528`) bị loại khỏi bước dựng lại RIÊNG này. Vì
    bước ③ (`_dung_kho_chung_con_thieu`, qua `_dieu_kien_kho_chung`) cũng
    không bao giờ dựng cho nó (license chưa "ok"), giọng đó KHÔNG BAO GIỜ có
    ai dựng lại bản nghe thử — mất vĩnh viễn sau lượt `dung_lai_cho_giong`
    đầu tiên (đổi làn)."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu, tham_chieu
    from apps.ltt_voice.tables import VoiceProfile
    import platform_core.db as dbmod

    # Giọng CỦA CHÍNH KHÁCH, dung_chung=True nhung license CHUA "ok" — dung
    # chinh SimpleNamespace/ORM that de dam bao khop dung schema.
    gen = dbmod.get_session()
    db = next(gen)
    try:
        h = VoiceProfile(owner_id=str(uid), ten_hien_thi="Giong cho soat",
                         ngon_ngu="vi", ngon_ngu_nguon="khai_bao",
                         trang_thai="active", dung_chung=True,
                         license_status="cho_soat")
        db.add(h)
        db.commit()
        pid = h.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Đối chứng: hàm xét điều kiện kho chung THẬT phải nói `False` cho hồ sơ
    # này — nếu không, cả bài kiểm mất ý nghĩa (nó sẽ đi qua đúng đường của
    # kho chung THẬT thay vì đường đang được sửa).
    ho_so = _ho_so_theo_pid(pid)
    assert not tham_chieu.du_dieu_kien_kho_chung(ho_so), (
        "tien de sai: ho so nay phai CHUA du dieu kien kho chung that")

    _them_bieu_dien_gia(uid, pid)

    goi = []
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **kw: (goi.append((khoa, kw)), True)[1])

    nghe_thu._dung_giong_rieng_con_thieu()

    khoa = nghe_thu.khoa_rieng(uid, pid)
    da_goi = dict(goi)
    assert khoa in da_goi, (
        "giong dung_chung=True nhung license CHUA 'ok' phai VAN duoc dung "
        "lai qua ban RIENG — no khong du dieu kien kho chung that")
    assert da_goi[khoa].get("ngon_ngu") == "vi"


def test_bao_tri_dung_giong_rieng_BO_QUA_dung_chung_DA_du_dieu_kien(khach, monkeypatch):
    """Đối chứng cho phép kiểm trên: một giọng dung_chung=True VÀ license đã
    "ok" (đủ điều kiện kho chung thật) phải BỊ BỎ QUA ở bước này — đó là việc
    của bước ③ (`_dung_kho_chung_con_thieu`), dựng nhầm ở đây tốn GPU cho một
    luồng đã có bước riêng lo."""
    client, uid = khach
    from apps.ltt_voice import nghe_thu, tham_chieu
    from apps.ltt_voice.tables import VoiceProfile
    import platform_core.db as dbmod

    gen = dbmod.get_session()
    db = next(gen)
    try:
        h = VoiceProfile(owner_id=str(uid), ten_hien_thi="Giong kho chung ok",
                         ngon_ngu="vi", ngon_ngu_nguon="khai_bao",
                         trang_thai="active", dung_chung=True,
                         license_status="ok")
        db.add(h)
        db.commit()
        pid = h.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    ho_so = _ho_so_theo_pid(pid)
    assert tham_chieu.du_dieu_kien_kho_chung(ho_so), (
        "tien de sai: ho so nay phai DU dieu kien kho chung that")

    _them_bieu_dien_gia(uid, pid)

    goi = []
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **kw: (goi.append(khoa), True)[1])

    nghe_thu._dung_giong_rieng_con_thieu()

    khoa = nghe_thu.khoa_rieng(uid, pid)
    assert khoa not in goi, (
        "giong DA du dieu kien kho chung that khong duoc dung o buoc RIENG "
        "— do la viec cua buoc ba (_dung_kho_chung_con_thieu)")


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


def _dem_repr(pid: str) -> int:
    """Số dòng `VoiceRepr` hiện có cho một hồ sơ — dùng để chốt "không dòng
    THỪA nào bị để lại" (review round 1, IMPORTANT 2)."""
    from apps.ltt_voice.tables import VoiceRepr
    from sqlalchemy import func, select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        hs = _ho_so_theo_pid(pid)
        return db.execute(select(func.count()).select_from(VoiceRepr)
                          .where(VoiceRepr.profile_id == hs.id)).scalar()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


class _FakeCtx:
    """`JobContext` tối giản cho test — chỉ mang đúng những thuộc tính
    `jobs.handle`/`jobs._dat_loi_khi_het_luot` đọc (review round 1,
    IMPORTANT 1-b)."""

    def __init__(self, attempt: int, job_type: str = "ltt_voice.enroll"):
        self.attempt = attempt
        self.job_type = job_type
        self.job_id = "fake-job-id"
        self.gpu_uuid = ""


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


# ── ⑦ REVIEW ROUND 1 — IMPORTANT 1: `loi` phải reachable QUA ĐƯỜNG THẬT ──────
#
# `sidecar_client.ghi_danh` KHÔNG BAO GIỜ tự ném `LoiNguoiGoi` trong sản xuất
# — nó ném `LoiSidecar`/`SidecarBan`/`VanBanQuaDai`. Các test dưới đây dùng
# ĐÚNG những lớp lỗi thật đó, không monkeypatch một ngoại lệ mà client thật
# không bao giờ ném (đó chính là lỗ mà round trước bị bắt).

def test_sidecar_4xx_la_loi_VINH_VIEN_dat_trang_thai_loi(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_4xx(*a, **k):
        raise sidecar_client.LoiSidecar(
            "Cong giong tra 422: clip khong hop le", status=422)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_4xx)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_sidecar_5xx_la_ha_tang_giu_nguyen_dang_ghi_danh(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_5xx(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 503: qua tai", status=503)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_5xx)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_sidecar_408_KHONG_phai_loi_vinh_vien(khach, monkeypatch):
    """408/409/429 nằm trong dải 4xx nhưng KHÔNG coi là lỗi của chính clip —
    xem `jobs._HTTP_4XX_TAM_THOI`."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_408(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 408: timeout", status=408)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_408)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_loi_ha_tang_o_LUOT_CUOI_van_dat_trang_thai_loi(khach, monkeypatch):
    """IMPORTANT 1-b: một lỗi HẠ TẦNG retryable, nhưng ĐÂY LÀ LƯỢT CUỐI
    (`ctx.attempt == SO_LAN_THU_JOB`) — `handle()` phải đặt `loi` trước khi
    nền tảng âm thầm bỏ cuộc, không để hồ sơ mắc kẹt vĩnh viễn."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client
    from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB

    def _hong_5xx(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 500: loi may chu", status=500)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_5xx)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs.handle(_params_ghi_danh(uid, pid), _FakeCtx(SO_LAN_THU_JOB))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_loi_ha_tang_KHONG_o_luot_cuoi_giu_nguyen_dang_ghi_danh(khach, monkeypatch):
    """Đối chứng cho bài trên: KHÔNG phải lượt cuối thì KHÔNG đặt `loi` —
    job còn lượt thử, hồ sơ vẫn phải chờ được."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_5xx(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 500: loi may chu", status=500)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_5xx)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs.handle(_params_ghi_danh(uid, pid), _FakeCtx(1))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_DANG_BAN_o_luot_cuoi_KHONG_dat_loi(khach, monkeypatch):
    """`SidecarBan`/`DangBanTam` (bận) KHÔNG tiêu một lượt thử
    (`job_runner._provider_failure_kind`: `resource_wait` không tăng
    `job.attempts`) — dù `ctx.attempt` trùng `SO_LAN_THU_JOB`, đây KHÔNG PHẢI
    lượt cuối thật, và `handle()` không được đặt `loi`."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client
    from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB

    def _ban(*a, **k):
        raise sidecar_client.SidecarBan(retry_after_s=1.0)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _ban)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.DangBanTam):
        jobs.handle(_params_ghi_danh(uid, pid), _FakeCtx(SO_LAN_THU_JOB))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


# ── ⑧ REVIEW ROUND 1 — IMPORTANT 2: rowcount==0 KHÔNG luôn là "đã thu hồi" ───

def test_ghi_danh_LAP_LAI_SAU_KHI_active_la_THANH_CONG_idempotent(khach, monkeypatch):
    """(i) Một lượt THỬ LẠI của CHÍNH job sau khi lượt trước đã kích hoạt
    xong (worker chết SAU khi UPDATE active commit) phải trả kết quả THÀNH
    CÔNG bình thường — không phải một `LoiGiongNoi` "đã bị thu hồi" giả."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client, tham_chieu
    from apps.ltt_voice.tables import VoiceRepr
    from platform_core.storage import get_storage
    import platform_core.db as dbmod

    ref_b64 = "QUJD"  # base64("ABC") — CỐ ĐỊNH, mô phỏng embedding tất định
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": ref_b64, "chon_doan": {}})
    _dat_nguon(uid, pid)

    # Dựng SẴN kết quả y hệt lượt gọi dưới đây sẽ tính ra — mô phỏng "lượt
    # trước đã kích hoạt xong".
    khoa_cu, vt_cu = tham_chieu.luu_bieu_dien(owner_id=uid, public_id=pid,
                                              ref_b64=ref_b64)
    gen = dbmod.get_session()
    db = next(gen)
    try:
        # ⛔ Đọc hồ sơ TRONG CÙNG session `db` (không qua `_ho_so_theo_pid` —
        #    hàm đó mở/đóng session RIÊNG, nên gán `.trang_thai` lên đối
        #    tượng nó trả về là gán lên một object đã DETACHED: `db.commit()`
        #    dưới đây sẽ không ghi lại thay đổi đó, và bài kiểm sẽ ngầm chạy
        #    nhầm đường "kích hoạt bình thường" thay vì đường "thử lại sau
        #    khi đã active" mà nó định dựng).
        from sqlalchemy import select as _select

        from apps.ltt_voice.tables import VoiceProfile
        hs = db.execute(_select(VoiceProfile)
                        .where(VoiceProfile.public_id == pid)).scalar_one()
        db.add(VoiceRepr(profile_id=hs.id, ref_id=0, engine="vieneu",
                         storage_key=khoa_cu, fingerprint=vt_cu,
                         trang_thai="dang_dung"))
        hs.trang_thai = "active"
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    so_repr_truoc = _dem_repr(pid)

    kq = jobs._ghi_danh(_params_ghi_danh(uid, pid))  # lượt "thử lại"

    assert kq["voice_id"] == pid
    assert _ho_so_theo_pid(pid).trang_thai == "active"
    st = get_storage()
    assert st.exists(khoa_cu), "khoa CU bi xoa nham"
    assert _dem_repr(pid) == so_repr_truoc, (
        "dong VoiceRepr THUA (trung khoa voi dong da co) khong duoc de lai")


def test_thu_hoi_giua_luc_ghi_danh_KHONG_de_lai_khoa_mo_coi(khach, monkeypatch):
    """(ii) Nhánh revoked/loi/disabled của `rowcount==0`: không dòng
    `VoiceRepr` NÀO KHÁC trỏ tới khoá vừa tính -> xoá khoá an toàn, không dòng
    CSDL thừa nào bị để lại."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    from apps.ltt_voice import jobs, sidecar_client, tham_chieu
    from platform_core.storage import get_storage
    import base64

    ref_b64 = "REVG"  # base64("DEF") — embedding MỚI, chưa ai dùng
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": ref_b64, "chon_doan": {}})
    _dat_nguon(uid, pid)
    khoa_se_sinh = tham_chieu.khoa_bieu_dien(
        uid, pid, tham_chieu.van_tay(base64.b64decode(ref_b64)))

    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))

    assert _ho_so_theo_pid(pid).trang_thai == "revoked"
    assert _dem_repr(pid) == 0, "khong dong VoiceRepr nao duoc de lai"
    assert not get_storage().exists(khoa_se_sinh), "khoa mo coi khong bi xoa"


def test_thu_hoi_giua_luc_ghi_danh_REVOKED_LUON_xoa_khoa_du_co_dong_khac(khach, monkeypatch):
    """(ii) review round 2, IMPORTANT C: `revoked` LUÔN xoá khoá — kể cả khi
    một dòng `VoiceRepr` KHÁC (embedding trùng, cùng sha256) đang trỏ tới
    đúng khoá đó. Thu hồi xoá HẾT TỆP của mọi biểu diễn (`khoa_da_biet` gom
    `storage_key` của MỌI dòng `VoiceRepr`, không lọc theo dòng nào), chỉ giữ
    lại DÒNG CSDL làm bằng chứng — "còn một dòng tham chiếu" không phải lý do
    giữ lại một tệp sinh trắc của một hồ sơ đã nói "đã xoá"."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    from apps.ltt_voice import jobs, sidecar_client, tham_chieu
    from apps.ltt_voice.tables import VoiceRepr
    from platform_core.storage import get_storage
    import platform_core.db as dbmod

    ref_b64 = "R0hJ"  # base64("GHI")
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": ref_b64, "chon_doan": {}})
    _dat_nguon(uid, pid)

    # Một dòng VoiceRepr KHÁC đã CÓ SẴN, trỏ tới ĐÚNG khoá mà lượt ghi danh
    # này sẽ tính ra (cùng ref_b64 -> cùng sha256 -> cùng khoá).
    khoa_cu, vt_cu = tham_chieu.luu_bieu_dien(owner_id=uid, public_id=pid,
                                              ref_b64=ref_b64)
    gen = dbmod.get_session()
    db = next(gen)
    try:
        hs = _ho_so_theo_pid(pid)
        db.add(VoiceRepr(profile_id=hs.id, ref_id=0, engine="vieneu",
                         storage_key=khoa_cu, fingerprint=vt_cu,
                         trang_thai="dang_dung"))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))

    assert _ho_so_theo_pid(pid).trang_thai == "revoked"
    assert _dem_repr(pid) == 1, "dong VoiceRepr CU (con song) khong duoc dung vao"
    assert not get_storage().exists(khoa_cu), (
        "revoked phai xoa khoa DU co dong CSDL khac tro toi")


def test_thu_hoi_giua_luc_ghi_danh_LOI_KHONG_xoa_khoa_dong_khac_dang_song(khach, monkeypatch):
    """(ii) — vế ĐỐI CHỨNG cho `loi`/`disabled`: khác `revoked`, hai trạng
    thái này KHÔNG xoá dữ liệu sinh trắc — nếu khoá TRÙNG với một `VoiceRepr`
    KHÁC đang sống, KHÔNG được xoá khoá đó."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client, tham_chieu
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    from platform_core.storage import get_storage
    import platform_core.db as dbmod

    ref_b64 = "SktM"  # base64("JKL")
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": ref_b64, "chon_doan": {}})
    _dat_nguon(uid, pid)

    khoa_cu, vt_cu = tham_chieu.luu_bieu_dien(owner_id=uid, public_id=pid,
                                              ref_b64=ref_b64)
    gen = dbmod.get_session()
    db = next(gen)
    try:
        # ⛔ Đọc hồ sơ TRONG CÙNG session (không qua `_ho_so_theo_pid` — xem
        #    chú thích ở bài kiểm idempotent phía trên cho vì sao).
        from sqlalchemy import select as _select
        hs = db.execute(_select(VoiceProfile)
                        .where(VoiceProfile.public_id == pid)).scalar_one()
        db.add(VoiceRepr(profile_id=hs.id, ref_id=0, engine="vieneu",
                         storage_key=khoa_cu, fingerprint=vt_cu,
                         trang_thai="dang_dung"))
        # Hồ sơ đã bị đánh dấu `loi` (vd một lượt thử khác) TRƯỚC KHI lượt
        # ghi danh dưới đây chạy tới — mô phỏng đúng ca `rowcount == 0` với
        # `trang_hien == "loi"`.
        hs.trang_thai = "loi"
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))

    assert _ho_so_theo_pid(pid).trang_thai == "loi"
    assert _dem_repr(pid) == 1, "dong VoiceRepr CU (con song) khong duoc dung vao"
    assert get_storage().exists(khoa_cu), "khoa CON DUOC THAM CHIEU khong duoc xoa"


# ── ⑨ REVIEW ROUND 1 — IMPORTANT 3: `xoa-nhieu`, `tat` trên trạng thái xấu,
#     và trần một lô ──────────────────────────────────────────────────────────

def test_xoa_nhieu_chi_thu_hoi_giong_CUA_MINH_va_DU_DIEU_KIEN(khach):
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid_cua_minh = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
    pid_dang_ghi_danh = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                                          trang_thai="dang_ghi_danh")
    pid_cua_B = _profile_cua_B()

    khoa_minh = nghe_thu.khoa_rieng(uid, pid_cua_minh)
    khoa_ghi_danh = nghe_thu.khoa_rieng(uid, pid_dang_ghi_danh)
    khoa_B = nghe_thu.khoa_rieng("user-b-0000", pid_cua_B)
    st = get_storage()
    for k in (khoa_minh, khoa_ghi_danh, khoa_B):
        st.put(k, io.BytesIO(b"x"), content_type="audio/wav")

    r = client.post(
        "/ltt-voice/giong/xoa-nhieu",
        data={"public_ids": f"{pid_cua_minh},{pid_dang_ghi_danh},{pid_cua_B}",
             "csrf_token": _csrf_giong(client)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["da_thu_hoi"] == [pid_cua_minh]
    assert set(d["bo_qua"]) == {pid_dang_ghi_danh, pid_cua_B}

    assert _ho_so_theo_pid(pid_cua_minh).trang_thai == "revoked"
    assert _ho_so_theo_pid(pid_dang_ghi_danh).trang_thai == "dang_ghi_danh"
    assert _profile(pid_cua_B).trang_thai == "active"

    assert not st.exists(khoa_minh), "khoa cua giong da thu hoi phai bi xoa"
    assert st.exists(khoa_ghi_danh), "giong dang ghi danh khong duoc dung vao"
    assert st.exists(khoa_B), "giong cua B khong duoc dung vao"


def test_tat_giong_DA_THU_HOI_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    r = client.post(f"/ltt-voice/giong/{pid}/tat",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 400
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"


def test_tat_giong_LOI_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="loi")
    r = client.post(f"/ltt-voice/giong/{pid}/tat",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 400
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_xoa_nhieu_qua_TRAN_bi_tu_choi(khach):
    client, uid = khach
    from apps.ltt_voice.routes._p_giong import TRAN_XOA_NHIEU

    ids = ",".join(f"vc_khongcothat{i}" for i in range(TRAN_XOA_NHIEU + 1))
    r = client.post("/ltt-voice/giong/xoa-nhieu",
                    data={"public_ids": ids, "csrf_token": _csrf_giong(client)})
    assert r.status_code == 400


# ── ⑩ REVIEW ROUND 1 — item 4: thu hồi lại một giọng ĐÃ `revoked` là dọn
#     lại (idempotent), không bị từ chối ─────────────────────────────────────

def test_thu_hoi_LAI_giong_DA_revoked_don_lai_duoc(khach):
    client, uid = khach
    from apps.ltt_voice import nghe_thu
    from platform_core.storage import get_storage

    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="revoked")
    khoa = nghe_thu.khoa_rieng(uid, pid)
    st = get_storage()
    st.put(khoa, io.BytesIO(b"sot lai tu mot lan xoa loi giua chung"),
          content_type="audio/wav")
    assert st.exists(khoa), "chua dung duoc tien de: tep phai co truoc"

    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 303
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"
    assert not st.exists(khoa), "lan thu lai khong don duoc tep sot"


# ── ⑪ REVIEW ROUND 2 — IMPORTANT A: `LoiNguoiGoi` là VĨNH VIỄN ở BẤT KỲ lượt
#     nào, không chỉ lượt cuối ───────────────────────────────────────────────

def test_san_sang_FALSE_qua_handle_dat_trang_thai_loi_NGAY_LUOT_DAU(khach, monkeypatch):
    """`_ghi_danh` ném `LoiGiongNoi` (= `LoiNguoiGoi`) TRƯỚC KHI chạm sidecar
    khi `san_sang()` sai — nền tảng coi đây là VĨNH VIỄN và dừng NGAY LƯỢT
    ĐẦU (`job_runner._provider_failure_kind` → `fail(retry=False)`), không
    chờ `SO_LAN_THU_JOB` lượt. `handle()` phải đặt `loi` ở LƯỢT 1, không chỉ
    ở lượt cuối (round 1 chỉ bắt được `LoiNguoiGoi` khi nó trùng lượt cuối)."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: False)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiGiongNoi):
        jobs.handle(_params_ghi_danh(uid, pid), _FakeCtx(1))  # LƯỢT 1, không phải cuối
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_khong_tim_thay_ho_so_qua_handle_KHONG_NEM_THEM_LOI(khach, monkeypatch):
    """Cùng bài trên, nhánh thứ hai trong ba nhánh `_ghi_danh` ném trước khi
    chạm sidecar: hồ sơ không tìm thấy (id sai, hoặc chủ khác). Không có hồ
    sơ nào để đặt `loi` — bài này chỉ chắc chắn `_dat_loi_khi_het_luot` không
    tự ném thêm lỗi khi `tim_profile` trả `None` (đè lên `LoiGiongNoi` gốc)."""
    client, uid = khach
    from apps.ltt_voice import jobs, sidecar_client

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    with pytest.raises(jobs.LoiGiongNoi):
        jobs.handle({"owner_id": uid, "voice_id": "vc_khongcothat",
                    "source_key": "voice/khong-ton-tai/vc_khongcothat/nguon.wav",
                    "ref_id": 0, "_job_type": "ltt_voice.enroll"},
                   _FakeCtx(1))


# ── ⑫ REVIEW ROUND 2 — IMPORTANT B: dọn hồ sơ TREO khi không job nào chạm
#     tới `except` của `handle()` nữa (orphan reaper / runtime watchdog) ─────

def _dat_tao_luc_cu(pid: str, phut: int) -> None:
    """Lùi `VoiceProfile.tao_luc` của `pid` về `phut` phút trước — mô phỏng
    một hồ sơ đã TREO lâu. Đọc/ghi TRONG CÙNG session (không qua
    `_ho_so_theo_pid`, xem chú thích ở bài kiểm idempotent phía trên)."""
    from datetime import datetime, timedelta, timezone

    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import select
    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        hs = db.execute(select(VoiceProfile)
                        .where(VoiceProfile.public_id == pid)).scalar_one()
        hs.tao_luc = datetime.now(timezone.utc) - timedelta(minutes=phut)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_don_ghi_danh_treo_KHONG_CON_JOB_dat_loi(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import giong_vong_doi
    import platform_core.db as dbmod

    _dat_tao_luc_cu(pid, giong_vong_doi.PHUT_TREO_GHI_DANH + 5)

    gen = dbmod.get_session()
    db = next(gen)
    try:
        so = giong_vong_doi.don_ghi_danh_treo(db)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    assert so == 1
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_don_ghi_danh_treo_CON_JOB_song_KHONG_DONG(khach):
    """Một hồ sơ TREO đủ lâu nhưng còn một job `ltt_voice.enroll` đang
    `running` tham chiếu tới nó — KHÔNG được đặt `loi` (job có thể vẫn đang
    thật sự chạy, chỉ là chậm)."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import giong_vong_doi
    from platform_core.models import JOB_RUNNING, Job
    import platform_core.db as dbmod

    _dat_tao_luc_cu(pid, giong_vong_doi.PHUT_TREO_GHI_DANH + 5)

    gen = dbmod.get_session()
    db = next(gen)
    try:
        db.add(Job(user_id=uid, app_slug="ltt_voice", job_type="ltt_voice.enroll",
                   params={"owner_id": uid, "voice_id": pid}, status=JOB_RUNNING))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    gen2 = dbmod.get_session()
    db2 = next(gen2)
    try:
        so = giong_vong_doi.don_ghi_danh_treo(db2)
        db2.commit()
    finally:
        try:
            next(gen2)
        except StopIteration:
            pass

    assert so == 0
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_don_ghi_danh_treo_CHUA_DU_LAU_KHONG_DONG(khach):
    """Hồ sơ mới nộp (chưa quá `PHUT_TREO_GHI_DANH`) không bị đụng vào, kể cả
    khi không job nào đang sống — vẫn còn trong cửa sổ chờ bình thường."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import giong_vong_doi
    import platform_core.db as dbmod

    gen = dbmod.get_session()
    db = next(gen)
    try:
        so = giong_vong_doi.don_ghi_danh_treo(db)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    assert so == 0
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


# ── ⑬ REVIEW ROUND 2 — IMPORTANT D: chỉ 400/415/422 là VĨNH VIỄN, không phải
#     "mọi 4xx" ────────────────────────────────────────────────────────────

def test_sidecar_400_la_loi_VINH_VIEN(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_400(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 400: than sai", status=400)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_400)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_sidecar_415_la_loi_VINH_VIEN(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_415(*a, **k):
        raise sidecar_client.LoiSidecar(
            "Cong giong tra 415: dinh dang khong doc duoc", status=415)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_415)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"


def test_sidecar_401_KHONG_phai_loi_vinh_vien(khach, monkeypatch):
    """401 (token sai) là lỗi VẬN HÀNH, không phải clip sai — round 2,
    IMPORTANT D."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_401(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 401: token sai", status=401)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_401)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_sidecar_404_KHONG_phai_loi_vinh_vien(khach, monkeypatch):
    """404 (endpoint đổi/mất) là lỗi VẬN HÀNH, không phải clip sai — round 2,
    IMPORTANT D."""
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client

    def _hong_404(*a, **k):
        raise sidecar_client.LoiSidecar("Cong giong tra 404: khong tim thay duong", status=404)
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong_404)
    _dat_nguon(uid, pid)
    with pytest.raises(jobs.LoiHaTang):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"
