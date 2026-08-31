"""Cửa `/ltt-voice/audio/` cho ra đúng hai thứ, và **không** cho ra thứ thứ ba.

## Vì sao tệp này tồn tại

Màn Giọng (P3) cần cho khách nghe lại **clip gốc** họ đã tải lên — ảnh tham chiếu
`02_VOICES.png` gọi nó là `Reference Audio`. Clip đó nằm ở một tiền tố khác với
tệp kết quả, nên cửa audio phải mở thêm một đường.

🔴 VÀ ĐÓ LÀ CHỖ SUÝT RÒ MỘT THỨ KHÔNG ĐƯỢC PHÉP RA NGOÀI.

   Bản đầu mở nguyên tiền tố `voice/{uid}/`. Nghe thì đúng — đó là thư mục của
   chính khách đó. Nhưng **biểu diễn engine cũng nằm trong đó**:

       tham_chieu.khoa_nguon(uid, pid)      -> voice/{uid}/{pid}/source.wav
       tham_chieu.khoa_bieu_dien(uid, pid,) -> voice/{uid}/{pid}/repr-<van tay>.npz
                                                                  ^^^^ speaker_emb

   `tables.py` nói thẳng về tệp `.npz` đó: *"KHÔNG BAO GIỜ ra ngoài. Khách không
   cần biết nó tồn tại."* Một khách tải embedding của **chính mình** chưa phải
   thảm hoạ, nhưng nó phá đúng ranh giới mà cả thiết kế bảng dựng lên để giữ —
   `voice_id` là danh tính công khai, biểu diễn là thứ nội bộ thay được khi đổi
   engine. Cho nó rò một lần là biến nó thành thứ ai đó sẽ phụ thuộc vào.

⭐ Nên cửa mở theo **TÊN TỆP** (`source.*`), không theo thư mục. Và vì đó là một
   ranh giới an toàn chứ không phải một tiện nghi, nó phải có bánh cóc.

## Vì sao kiểm bằng hình dạng khoá chứ không bằng CSDL

Rẻ, và **không thể quên**. Một phép kiểm quyền dựa trên truy vấn là một phép
kiểm mà nhánh tiếp theo có thể quên gọi; một tiền tố ghép từ `uid` thì không.
"""
from __future__ import annotations

import io
import re
import struct

import pytest

UID_KHAC = "00000000-0000-0000-0000-000000000000"


def _wav(giay: float = 0.5, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Tài khoản đã đăng nhập + kho cục bộ, trả kèm `uid` để dựng khoá."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-audio.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-audio")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-audio@test.com",
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
    r = client.post("/login", data={"username": "voice-audio@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _dat(khoa: str, du_lieu: bytes) -> None:
    from platform_core.storage import get_storage
    get_storage().put(khoa, io.BytesIO(du_lieu), content_type="application/octet-stream")


# ── Cho ra ───────────────────────────────────────────────────────────────────

def test_tep_ket_qua_cua_chinh_minh_doc_duoc(khach):
    client, uid = khach
    khoa = f"voice/out/{uid}/job-abc/tieng.wav"
    _dat(khoa, _wav())
    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")


def test_clip_goc_cua_chinh_minh_doc_duoc(khach):
    """Đường mà màn Giọng cần: nghe lại clip đã tải lên."""
    from apps.ltt_voice import tham_chieu
    client, uid = khach
    khoa = tham_chieu.khoa_nguon(uid, "vc_" + "a" * 32) + ".wav"
    _dat(khoa, _wav())
    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 200, (
        "clip goc khong doc duoc — man Giong se hien mot trinh phat cam")


@pytest.mark.parametrize("duoi,kieu", [
    ("wav", "audio/wav"), ("mp3", "audio/mpeg"), ("m4a", "audio/mp4")])
def test_kieu_noi_dung_theo_duoi_tep(khach, duoi, kieu):
    """🔴 Không gán cứng `audio/wav`.

    `tham_chieu.luu_nguon` nhận cả mp3 và m4a. Báo sai kiểu thì trình duyệt từ
    chối phát, và triệu chứng là **một trình phát im lặng**, không phải một lỗi —
    người dùng sẽ tưởng clip của họ hỏng.
    """
    from apps.ltt_voice import tham_chieu
    client, uid = khach
    khoa = f"{tham_chieu.khoa_nguon(uid, 'vc_' + 'b' * 32)}.{duoi}"
    _dat(khoa, _wav())
    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(kieu), (
        f".{duoi} bao kieu {r.headers['content-type']!r}, phai la {kieu!r}")


# ── KHÔNG cho ra ─────────────────────────────────────────────────────────────

def test_bieu_dien_engine_KHONG_BAO_GIO_ra_ngoai(khach):
    """🔴 Phép kiểm quan trọng nhất tệp này.

    `repr-*.npz` chứa `speaker_emb`. Nó nằm **cùng thư mục** với clip gốc, nên
    bất kỳ ai nới cửa audio theo thư mục thay vì theo tên tệp đều mở nó ra cùng.
    Đó chính xác là lỗi bản đầu của P3 mắc phải và đã sửa.
    """
    from apps.ltt_voice import tham_chieu
    client, uid = khach
    pid = "vc_" + "c" * 32
    khoa = tham_chieu.khoa_bieu_dien(uid, pid, "f" * 32)
    _dat(khoa, b"GIA-LAP-SPEAKER-EMB")

    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 404, (
        "BIEU DIEN ENGINE RO RA NGOAI.\n"
        f"  khoa : {khoa}\n"
        "  Cua audio dang mo theo THU MUC. No phai mo theo TEN TEP (`source.*`).\n"
        "  Xem `tables.py`: 'KHONG BAO GIO ra ngoai.'")
    assert b"SPEAKER" not in r.content


def test_tep_cua_nguoi_khac_khong_doc_duoc(khach):
    from apps.ltt_voice import tham_chieu
    client, _uid = khach
    for khoa in (f"voice/out/{UID_KHAC}/job-xyz/tieng.wav",
                 tham_chieu.khoa_nguon(UID_KHAC, "vc_" + "d" * 32) + ".wav"):
        _dat(khoa, _wav())
        assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404, (
            f"doc duoc tep cua nguoi khac: {khoa}")


def test_tep_la_trong_thu_muc_cua_minh_khong_doc_duoc(khach):
    """Thư mục của mình **không phải** giấy phép đọc mọi thứ trong đó.

    Chỉ `source.*` ra được. Một tệp tên khác — hôm nay chưa có, ngày mai một
    tính năng nào đó sinh ra — phải mặc định là **không**, chứ không phải mặc
    định là có rồi chờ ai đó nhớ chặn lại.
    """
    client, uid = khach
    pid = "vc_" + "e" * 32
    for ten in ("ghi_chu.txt", "backup.zip", "source_khac.wav", "notsource.wav"):
        khoa = f"voice/{uid}/{pid}/{ten}"
        _dat(khoa, b"x" * 10)
        assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404, (
            f"tep la ra duoc: {ten}")


def test_khong_dang_nhap_thi_khong_doc_duoc(tmp_path, monkeypatch, khach):
    client, uid = khach
    khoa = f"voice/out/{uid}/job-abc/tieng.wav"
    _dat(khoa, _wav())

    from fastapi.testclient import TestClient

    from server.app import create_app
    la = TestClient(create_app(), base_url="https://testserver",
                    follow_redirects=False)
    try:
        r = la.get(f"/ltt-voice/audio/{khoa}")
        # 303 ve /login hoac 401/404 deu duoc — mien la KHONG phai 200 kem tep.
        assert r.status_code != 200, "khach an danh doc duoc tep tieng"
    finally:
        la.close()
