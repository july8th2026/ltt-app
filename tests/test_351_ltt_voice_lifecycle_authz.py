"""Vòng đời tệp tiếng SAU khi job xong: sở hữu, hết hạn, tệp mất, đã tải, đã xoá.

Tệp này bổ sung cho `test_346` (cửa audio) và `test_348` (màn Lịch sử), canh đúng
những cạnh mà hai tệp kia chưa chạm:

1. **Sở hữu chéo tài khoản, đúng kịch bản "copy URL A→B".** `test_346` gieo tệp
   của "người khác" bằng một UUID hằng số rồi hỏi bằng chính phiên của khách.
   Ở đây có HAI tài khoản thật, đăng nhập bằng B, và hỏi khoá của A — đúng thứ
   xảy ra khi ai đó dán một URL từ máy người khác.

2. **Nghe thử riêng (`preview-*`) và giọng mẫu (`voice/mau/`).** Hai tiền tố
   `test_346` không đụng: preview của người khác phải chặn, mẫu đòi đăng nhập,
   và tệp không phải `.wav` dưới `voice/mau/` không được ra.

3. **Path traversal / absolute path ở tầng kho** — nơi thi hành thật sự.

4. **HẾT HẠN là một trạng thái RIÊNG.** Sau hạn lưu trữ, hàng còn nhưng nội dung
   bị dọn; màn Lịch sử phải nói "đã hết hạn", không bịa "Giọng mặc định", và
   KHÔNG dựng một trình phát trỏ vào hư không ("200 nhưng player chết").

5. **Tệp mất mà hàng còn** → cửa audio trả 404, không phải 200 với thân rỗng.

6. **ĐÃ TẢI + XOÁ NGƯỜI DÙNG (D005).** "Đã tải" là một mốc bền theo tài khoản;
   "Xoá" là soft-delete — dọn TỆP sớm, GIỮ hàng job (bằng chứng sổ credit),
   chỉ cho job đã kết thúc, và luôn đòi CSRF + sở hữu.
"""
from __future__ import annotations

import io
import re
import struct

import pytest

UID_A_GIA = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _wav(giay: float = 0.3, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    """CSDL + kho cục bộ + app, KHÔNG đăng nhập sẵn. Trả xưởng dựng client."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-life.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-life")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(str(tmp_path / "store")))

    from fastapi.testclient import TestClient

    from server.app import create_app
    from platform_core.users import tao_nguoi_dung

    app = create_app()

    def tao_user(email: str) -> str:
        gen = dbmod.get_session()
        db = next(gen)
        try:
            u = tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                               is_verified=True)
            db.commit()
            return str(u.id)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    def dang_nhap(email: str) -> TestClient:
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=False)
        login = client.get("/login")
        m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
        assert m
        r = client.post("/login", data={"username": email,
                                        "password": "matkhau-tot-12",
                                        "csrf_token": m.group(1)})
        assert r.status_code in (200, 302, 303)
        return client

    clients: list = []

    def _dn(email: str) -> TestClient:
        c = dang_nhap(email)
        clients.append(c)
        return c

    try:
        yield {"app": app, "tao_user": tao_user, "dang_nhap": _dn}
    finally:
        for c in clients:
            c.close()
        set_storage(None)
        dbmod.reset_engine()


def _dat(khoa: str, du_lieu: bytes) -> None:
    from platform_core.storage import get_storage
    get_storage().put(khoa, io.BytesIO(du_lieu),
                      content_type="application/octet-stream")


# ═══════════════════ 1. SỞ HỮU CHÉO — copy URL A→B ══════════════════════════

def test_url_copy_tu_A_sang_B_that_bai_ket_qua_va_nguon(moi_truong):
    """🔴 Bất biến trung tâm: A tuyệt đối không đọc output/source của B.

    Đây là kịch bản dán URL: B đăng nhập bằng phiên của B, rồi hỏi đúng những
    khoá THẬT của A. Cả hai tiền tố — tệp kết quả và clip gốc — phải 404.
    """
    from apps.ltt_voice import tham_chieu
    env = moi_truong
    uid_a = env["tao_user"]("a@test.com")
    env["tao_user"]("b@test.com")
    cb = env["dang_nhap"]("b@test.com")

    ket_qua = f"voice/out/{uid_a}/job-cua-a/tieng.wav"
    nguon = tham_chieu.khoa_nguon(uid_a, "vc_" + "a" * 32) + ".wav"
    _dat(ket_qua, _wav())
    _dat(nguon, _wav())

    for khoa in (ket_qua, nguon):
        r = cb.get(f"/ltt-voice/audio/{khoa}")
        assert r.status_code == 404, (
            f"B doc duoc tep cua A qua URL copy: {khoa}")
        assert b"RIFF" not in r.content


def test_B_khong_doc_duoc_preview_cua_A(moi_truong):
    """Nghe thử RIÊNG là giọng của một người thật — đi qua đúng phép kiểm sở hữu.

    `test_346` không đụng tiền tố `preview-`; nó nằm cùng thư mục với
    `repr-*.npz`, nên một lỗ ở đây rò cả clip gốc lẫn biểu diễn.
    """
    from apps.ltt_voice import nghe_thu
    env = moi_truong
    uid_a = env["tao_user"]("a@test.com")
    env["tao_user"]("b@test.com")
    cb = env["dang_nhap"]("b@test.com")

    khoa = nghe_thu.khoa_rieng(uid_a, "vc_" + "p" * 32)
    _dat(khoa, _wav())
    assert cb.get(f"/ltt-voice/audio/{khoa}").status_code == 404, (
        "B doc duoc nghe-thu rieng cua A")


def test_preview_cua_chinh_minh_doc_duoc(moi_truong):
    """Đối chứng: cùng khoá `preview-*` NHƯNG của chính khách thì phải đọc được —
    nếu không, phép chặn ở trên có thể đang chặn nhầm mọi người."""
    from apps.ltt_voice import nghe_thu
    env = moi_truong
    uid_a = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    khoa = nghe_thu.khoa_rieng(uid_a, "vc_" + "q" * 32)
    _dat(khoa, _wav())
    assert ca.get(f"/ltt-voice/audio/{khoa}").status_code == 200


# ═══════════════════ 2. GIỌNG MẪU — công khai nhưng vẫn đòi đăng nhập ════════

def test_giong_mau_doc_duoc_khi_dang_nhap(moi_truong):
    from apps.ltt_voice import nghe_thu
    env = moi_truong
    env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    khoa = nghe_thu.khoa_mau("Adam")
    _dat(khoa, _wav())
    r = ca.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/wav")


def test_giong_mau_doi_dang_nhap(moi_truong):
    """`voice/mau/` công khai về nội dung nhưng KHÔNG mở cho người lạ — nếu không
    đường này thành một CDN mở. `require_login` ở chữ ký cửa audio giữ điều đó."""
    from fastapi.testclient import TestClient

    from apps.ltt_voice import nghe_thu
    env = moi_truong
    khoa = nghe_thu.khoa_mau("Adam")
    _dat(khoa, _wav())
    la = TestClient(env["app"], base_url="https://testserver",
                    follow_redirects=False)
    try:
        assert la.get(f"/ltt-voice/audio/{khoa}").status_code != 200
    finally:
        la.close()


def test_tep_khong_wav_duoi_mau_bi_chan(moi_truong):
    """Cửa mẫu mở theo ĐUÔI `.wav`. Một tệp khác lọt vào `voice/mau/` — hôm nay
    chưa có, mai một bước nào đó sinh ra — phải mặc định là KHÔNG."""
    env = moi_truong
    env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    for ten in ("config.json", "repr-abcd.npz", "note.txt"):
        khoa = f"voice/mau/adam/{ten}"
        _dat(khoa, b"x" * 8)
        assert ca.get(f"/ltt-voice/audio/{khoa}").status_code == 404, (
            f"tep la duoi voice/mau/ ra duoc: {ten}")


# ═══════════════════ 3. PATH TRAVERSAL / ABSOLUTE PATH ═══════════════════════

def test_safe_key_chan_traversal_va_absolute():
    """Tầng thi hành thật của chống-traversal là `storage._safe_key`.

    Cửa audio kiểm quyền bằng hình dạng khoá (tiền tố `uid`), nhưng thứ chặn
    `../../secrets/app.env` và `C:\\...` là chuẩn hoá ở kho — và nó phải NÉM,
    không nắn im lặng. Hai lớp ghép lại: dù một khoá lách qua tiền tố, kho vẫn
    từ chối, và cửa biến `StorageError` thành 404.
    """
    from platform_core.storage import StorageError, _safe_key

    xau = [
        "voice/out/uid/../../secrets/app.env",   # đi lên
        "voice\\out\\uid\\..\\..\\secrets",       # backslash rồi mới đi lên
        "../secrets/app.env",
        "~/secrets",                              # home
        "C:/Windows/win.ini",                     # ổ đĩa tuyệt đối (Windows)
        "voice/out/uid/../../../..",
    ]
    for k in xau:
        with pytest.raises(StorageError):
            _safe_key(k)

    # Ngược lại: một khoá hợp lệ vẫn qua, và `.`/dấu / thừa được chuẩn hoá bỏ.
    assert _safe_key("voice/out/uid/job/tieng.wav") == "voice/out/uid/job/tieng.wav"
    assert _safe_key("voice/./out/uid//job/tieng.wav") == "voice/out/uid/job/tieng.wav"


def test_cua_audio_tra_404_cho_khoa_di_len(moi_truong):
    """Ghép hai lớp: một khoá bắt đầu đúng tiền tố của B nhưng chứa `..` để cố
    trèo ra — cửa phải trả 404 (kho ném, cửa nuốt thành 404), không 500, không
    lộ nội dung."""
    env = moi_truong
    uid = env["tao_user"]("b@test.com")
    cb = env["dang_nhap"]("b@test.com")
    # httpx có thể chuẩn hoá `..` trong path; mã hoá phần trăm để nó tới handler
    # nguyên vẹn, rồi Starlette giải mã trước khi vào converter {key:path}.
    khoa = f"voice/out/{uid}/%2e%2e/%2e%2e/secrets/app.env"
    r = cb.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 404
    assert b"app.env" not in r.content


# ═══════════════════ 4. HẾT HẠN — một trạng thái RIÊNG ══════════════════════

def _job_gia(**kw):
    from types import SimpleNamespace
    import datetime as dt
    return SimpleNamespace(
        id=kw.get("id", "job-1"),
        status=kw.get("status", "done"),
        params=kw.get("params", {}),
        result=kw.get("result", {}),
        created_at=kw.get("created_at", dt.datetime(2026, 9, 1, 10, 0)),
        content_expired_at=kw.get("content_expired_at", None),
    )


def test_dong_het_han_khong_bia_giong_va_khong_co_url():
    """🔴 Sau khi dọn, `params`/`result` rỗng. Dòng phải:
       · đánh dấu `het_han=True`;
       · KHÔNG `giong_mac_dinh` (không còn biết giọng gì — bịa là sai);
       · KHÔNG `audio_url` (không còn tệp — một URL 404 là player chết).
    """
    import datetime as dt

    from apps.ltt_voice import doc_man_lich_su as dls
    het = _job_gia(status="done", params={}, result={},
                   content_expired_at=dt.datetime(2026, 10, 1, 10, 0))
    d = dls.dong_cho_trang(het, "/ltt-voice/audio")
    assert d["het_han"] is True
    assert d["giong_mac_dinh"] is False, "het han ma van bia 'Giong mac dinh'"
    assert d["audio_url"] == ""

    # Đối chứng: một lượt done BÌNH THƯỜNG không hết hạn vẫn có URL + nhãn mặc định.
    binh_thuong = _job_gia(status="done", params={"text": "x"},
                           result={"audio_key": "voice/out/u/j/tieng.wav"})
    d2 = dls.dong_cho_trang(binh_thuong, "/ltt-voice/audio")
    assert d2["het_han"] is False
    assert d2["giong_mac_dinh"] is True
    assert d2["audio_url"].endswith("/tieng.wav")


def test_man_lich_su_noi_ro_HET_HAN(moi_truong):
    """Route thật: một job đã hết hạn hiện badge "Đã hết hạn", câu giải thích lưu
    trữ, KHÔNG dựng `<audio`, và KHÔNG in "Giọng mặc định".
    """
    import platform_core.db as dbmod
    from platform_core.models import Job
    from platform_core import job_content

    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")

    gen = dbmod.get_session()
    db = next(gen)
    try:
        # Job đã hết hạn: đúng hình dạng sau `expire_content` — params/result {}
        # và `content_expired_at` đã đặt.
        db.add(Job(user_id=uid, app_slug="ltt_voice",
                   job_type="ltt_voice.synthesize", params={}, result={},
                   status="done",
                   finished_at=__import__("datetime").datetime(
                       2026, 8, 1, 0, 0, tzinfo=__import__("datetime").timezone.utc),
                   content_expired_at=__import__("datetime").datetime(
                       2026, 9, 1, 0, 0, tzinfo=__import__("datetime").timezone.utc)))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = ca.get("/ltt-voice/lich-su")
    assert r.status_code == 200
    assert "Đã hết hạn" in r.text, "man hinh khong noi ra trang thai het han"
    assert str(job_content.RETENTION_DAYS) in r.text, (
        "cau giai thich luu tru phai mang so ngay tu nguon chan ly")
    # Không có trình phát trỏ vào hư không cho dòng đã hết hạn.
    assert "lv-ls-hethan" in r.text
    assert "Giọng mặc định" not in r.text, (
        "bia 'Giong mac dinh' cho mot luot da mat tham so")


# ═══════════════════ 5. TỆP MẤT MÀ HÀNG CÒN — cửa audio 404 ═════════════════

def test_tep_mat_thi_cua_audio_404_khong_phai_200_rong(moi_truong):
    """Một `audio_key` trỏ vào tệp KHÔNG tồn tại (kho lệch CSDL, hoặc xoá ngoài
    luồng) phải cho 404, không phải 200 với thân rỗng — "200 nhưng player chết"
    là đúng thứ phải tránh.
    """
    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    # Không `_dat` gì cả: khoá hợp lệ về hình dạng, tệp không có.
    khoa = f"voice/out/{uid}/job-mat-tep/tieng.wav"
    r = ca.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 404
    assert r.content == b"" or b"RIFF" not in r.content


# ═══════════════════ 6. DOWNLOADED MARKER + USER DELETE ═════════════════════

def _csrf_ls(client) -> str:
    m = re.search(r'id="lv-ls-csrf" value="([^"]+)"',
                  client.get("/ltt-voice/lich-su").text)
    assert m, "trang Lich su khong co csrf_token"
    return m.group(1)


def _gieo_job_co_tep(uid: str, *, status: str = "done"):
    """Một job có tệp kết quả thật trong kho. Trả (job_id, audio_key)."""
    import platform_core.db as dbmod
    from platform_core.models import Job

    khoa = None
    gen = dbmod.get_session()
    db = next(gen)
    try:
        j = Job(user_id=uid, app_slug="ltt_voice",
                job_type="ltt_voice.synthesize",
                params={"text": "cau thu", "nguon": "studio", "preset": "Adam"},
                status=status,
                result={"duration_s": 1.0, "credit_cost": 1,
                        "audio_key": ""})
        db.add(j)
        db.flush()
        khoa = f"voice/out/{uid}/{j.id}/tieng.wav"
        j.result = {"duration_s": 1.0, "credit_cost": 1, "audio_key": khoa}
        db.commit()
        jid = str(j.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    _dat(khoa, _wav())
    return jid, khoa


def test_danh_dau_da_tai_hien_chip_va_can_so_huu(moi_truong):
    """POST /da-tai đánh dấu, và màn Lịch sử hiện chip "Đã tải".

    ⛔ Vẫn kiểm sở hữu: ghi một dấu vết cho job người khác vẫn là phép ghi cần
       quyền, dù nội dung vô hại.
    """
    env = moi_truong
    uid_a = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, _khoa = _gieo_job_co_tep(uid_a)

    # Trước khi đánh dấu: không có chip.
    assert "Đã tải" not in ca.get("/ltt-voice/lich-su").text

    r = ca.post(f"/ltt-voice/lich-su/{jid}/da-tai",
                data={"csrf_token": _csrf_ls(ca)})
    assert r.status_code == 200 and r.json()["ok"], r.text
    assert "Đã tải" in ca.get("/ltt-voice/lich-su").text, (
        "danh dau roi ma chip 'Da tai' khong hien")

    # Job của người khác → 404.
    env["tao_user"]("b@test.com")
    cb = env["dang_nhap"]("b@test.com")
    rb = cb.post(f"/ltt-voice/lich-su/{jid}/da-tai",
                 data={"csrf_token": _csrf_ls(cb)})
    assert rb.status_code == 404


def test_da_tai_can_csrf(moi_truong):
    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, _ = _gieo_job_co_tep(uid)
    r = ca.post(f"/ltt-voice/lich-su/{jid}/da-tai",
                data={"csrf_token": "sai-be-bet"})
    assert r.status_code == 400


def test_xoa_don_tep_giu_hang_va_hien_DA_XOA(moi_truong):
    """🔴 Xoá = dọn TỆP sớm + đánh dấu, KHÔNG hard-delete hàng (bằng chứng credit).

    Sau khi xoá:
      · tệp trong kho phải MẤT;
      · hàng `jobs` vẫn CÒN (đối chiếu bút toán) và `content_expired_at` đã đặt;
      · màn Lịch sử hiện "Đã xoá", không dựng trình phát, không bịa giọng.
    """
    import platform_core.db as dbmod
    from platform_core.models import Job
    from platform_core.storage import get_storage

    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, khoa = _gieo_job_co_tep(uid)
    assert get_storage().exists(khoa), "gieo hong: tep chua co trong kho"

    r = ca.post(f"/ltt-voice/lich-su/{jid}/xoa",
                data={"csrf_token": _csrf_ls(ca)})
    assert r.status_code == 200 and r.json()["ok"], r.text

    # Tệp đã mất.
    assert not get_storage().exists(khoa), "xoa ma tep van con trong kho"

    # Hàng job VẪN còn — bằng chứng không được xoá cứng.
    gen = dbmod.get_session()
    db = next(gen)
    try:
        j = db.get(Job, jid)
        assert j is not None, "hard-delete hang job — mat bang chung so credit"
        assert j.content_expired_at is not None, "chua dat content_expired_at"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    html = ca.get("/ltt-voice/lich-su").text
    assert "Đã xoá" in html, "khong hien trang thai 'Da xoa'"
    assert "Giọng mặc định" not in html, "bia giong cho luot da xoa"
    # Không còn trình phát cho dòng đã xoá.
    assert 'class="lv-ls-phat"' not in html


def test_xoa_job_cua_NGUOI_KHAC_la_404(moi_truong):
    env = moi_truong
    uid_a = env["tao_user"]("a@test.com")
    env["dang_nhap"]("a@test.com")
    jid, khoa = _gieo_job_co_tep(uid_a)

    env["tao_user"]("b@test.com")
    cb = env["dang_nhap"]("b@test.com")
    r = cb.post(f"/ltt-voice/lich-su/{jid}/xoa",
                data={"csrf_token": _csrf_ls(cb)})
    assert r.status_code == 404
    # Và tệp của A KHÔNG bị xoá bởi lượt của B.
    from platform_core.storage import get_storage
    assert get_storage().exists(khoa), "B xoa duoc tep cua A!"


def test_xoa_luot_dang_chay_bi_tu_choi(moi_truong):
    """⛔ Job đang chờ/đang chạy còn cần `params` để chạy — dọn giữa chừng là bẻ
    gãy worker. Xoá chỉ cho job terminal."""
    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, khoa = _gieo_job_co_tep(uid, status="running")
    r = ca.post(f"/ltt-voice/lich-su/{jid}/xoa",
                data={"csrf_token": _csrf_ls(ca)})
    assert r.status_code == 400
    from platform_core.storage import get_storage
    assert get_storage().exists(khoa), "xoa mot job dang chay — da dong toi tep"


def test_xoa_can_csrf(moi_truong):
    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, khoa = _gieo_job_co_tep(uid)
    r = ca.post(f"/ltt-voice/lich-su/{jid}/xoa",
                data={"csrf_token": "sai"})
    assert r.status_code == 400
    from platform_core.storage import get_storage
    assert get_storage().exists(khoa), "CSRF sai ma van xoa tep"


# ═══════════════════ 7. HỘP XÁC NHẬN — hậu quả TRƯỚC khi xoá (D005) ═════════

def test_anh_huong_liet_ke_khoi_du_an_dang_dung_audio(moi_truong):
    """`GET /anh-huong` phải thấy khối Dự án đang dùng đúng audio của job này —
    dữ liệu cho hộp `confirm()` ở `voice.js` nói trước hậu quả."""
    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject

    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, khoa = _gieo_job_co_tep(uid)

    gen = dbmod.get_session()
    db = next(gen)
    try:
        p = VoiceProject(owner_id=uid, ten="Truyen dai", loai="du_an")
        db.add(p)
        db.flush()
        db.add(VoiceBlock(project_id=p.id, thu_tu=1.0, text="doan mot",
                          trang_thai="xong", job_id=jid, audio_key=khoa))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = ca.get(f"/ltt-voice/lich-su/{jid}/anh-huong")
    assert r.status_code == 200
    ds = r.json()["khoi"]
    assert len(ds) == 1
    assert ds[0]["du_an"] == "Truyen dai"
    assert ds[0]["khoi_so"] == 1


def test_anh_huong_rong_khi_khong_dung_o_du_an_nao(moi_truong):
    env = moi_truong
    uid = env["tao_user"]("a@test.com")
    ca = env["dang_nhap"]("a@test.com")
    jid, _khoa = _gieo_job_co_tep(uid)
    r = ca.get(f"/ltt-voice/lich-su/{jid}/anh-huong")
    assert r.status_code == 200 and r.json()["khoi"] == []
