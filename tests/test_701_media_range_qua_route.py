"""701 — hai cua media DA migrate that su phat ra Range, do qua HTTP.

`test_700` chot hop dong cua `platform_core.phat_media` o muc module. Tep nay do
thu khac: **route that co goi no khong**. Mot module dung ma khong ai goi thi
khong cuu duoc ai — va do dung la trang thai cua kho nay truoc 2026-09-05.

Hai cua trong pham vi:

    GET /ltt-voice/audio/{key}     truoc day: doc toan tep, khong Accept-Ranges
    GET /chatltt/tai-san/{key}     truoc day: y het

⭐ Phep kiem manh nhat o day la `test_..._khai_accept_ranges_o_luot_200`.
   Safari/WebKit quyet dinh mot nguon am thanh co tua duoc hay khong tu chinh
   luot 200 dau tien; khong thay `Accept-Ranges` thi no ket luan may chu khong
   ho tro Range va BO PHAT, trong khi `<a download>` van tai binh thuong. Do
   chinh la hinh dang loi nguoi dung bao. Nen mot phep kiem chi doi 206 la chua
   du — no khong bat duoc hoi quy o luot 200.

Khong cham CSDL that, khong cham kho that, khong doc trang thai may.
"""
from __future__ import annotations

import io
import re
import struct

import pytest

NOI_DUNG = bytes(range(256)) * 12          # 3072 byte


def _wav(giay: float = 0.5, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Tai khoan da dang nhap + kho cuc bo. Tra `(client, uid)`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'range.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-media-range")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core import registry

    # Nap bang cua MOI app qua registry — khong go cung slug nao.
    registry.load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="range@test.com",
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
    r = client.post("/login", data={"username": "range@test.com",
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
    get_storage().put(khoa, io.BytesIO(du_lieu),
                      content_type="application/octet-stream")


def _cua_voice(uid: str) -> tuple[str, bytes]:
    khoa = f"voice/out/{uid}/job-range/tieng.wav"
    du = _wav()
    _dat(khoa, du)
    return f"/ltt-voice/audio/{khoa}", du


def _cua_chat(uid: str) -> tuple[str, bytes]:
    """Khoa hop le theo `tao_media.kiem_so_huu_khoa`.

    Hinh `anhnoibo/<uid>/<job_id>/<i>.png` la mot trong ba hinh cua duoc mo.
    Khang dinh lai bang chinh ham kiem thay vi tin cho thich: neu hinh doi, phep
    kiem nay do NGAY o dong assert chu khong do o mot cho kho hieu ben duoi.
    """
    from apps.chatltt.services import tao_media as TM

    khoa = f"anhnoibo/{uid}/job-range/0.png"
    assert TM.kiem_so_huu_khoa(khoa, uid), (
        "hinh dang khoa dung trong phep kiem nay khong con hop le — "
        "doc lai `tao_media.kiem_so_huu_khoa`")
    _dat(khoa, NOI_DUNG)
    return f"/chatltt/tai-san/{khoa}", NOI_DUNG


# ── Voice ────────────────────────────────────────────────────────────────────

def test_voice_khai_accept_ranges_o_luot_200(khach):
    """Luot 200 dau tien la cho WebKit quyet dinh co phat hay khong."""
    client, uid = khach
    duong, du = _cua_voice(uid)
    r = client.get(duong)
    assert r.status_code == 200
    assert r.headers.get("accept-ranges") == "bytes", (
        "thieu Accept-Ranges o luot 200 — day dung la trang thai truoc 05/09, "
        "va la ly do Safari tai xuong duoc ma khong phat duoc")
    assert r.headers.get("content-length") == str(len(du))


def test_voice_range_hop_le_tra_206_dung_byte(khach):
    client, uid = khach
    duong, du = _cua_voice(uid)
    r = client.get(duong, headers={"Range": "bytes=100-199"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 100-199/{len(du)}"
    assert r.content == du[100:200]


def test_voice_range_vo_nghia_tra_416_khong_phai_206_lech(khach):
    client, uid = khach
    duong, du = _cua_voice(uid)
    r = client.get(duong, headers={"Range": f"bytes={len(du) + 10}-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(du)}"


def test_voice_suffix_range_tra_byte_cuoi(khach):
    client, uid = khach
    duong, du = _cua_voice(uid)
    r = client.get(duong, headers={"Range": "bytes=-256"})
    assert r.status_code == 206
    assert r.content == du[-256:]


def test_voice_tai_mp3_van_chay_va_van_la_attachment(khach):
    """Duong `?mp3=1` co chu dich doc toan tep — no la TAI XUONG, khong phai phat.

    Neu ffmpeg khong co tren may nay thi route tra WAV; ca hai deu la 200 va ca
    hai deu KHONG duoc 500. Phep kiem nay chot rang viec chuyen sang phat_media
    khong lam gay nhanh mp3.
    """
    client, uid = khach
    duong, _ = _cua_voice(uid)
    r = client.get(duong + "?mp3=1")
    assert r.status_code == 200
    if r.headers.get("content-type", "").startswith("audio/mpeg"):
        assert "attachment" in r.headers.get("content-disposition", "")


def test_voice_khoa_cua_nguoi_khac_van_404(khach):
    """Migrate khong duoc lam long phep kiem so huu."""
    client, _uid = khach
    khoa = "voice/out/00000000-0000-0000-0000-000000000000/j/tieng.wav"
    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 404


def test_voice_khoa_khong_ton_tai_van_404(khach):
    client, uid = khach
    r = client.get(f"/ltt-voice/audio/voice/out/{uid}/khong-co/tieng.wav")
    assert r.status_code == 404


# ── ChatLTT ──────────────────────────────────────────────────────────────────

def test_chat_khai_accept_ranges_o_luot_200(khach):
    client, uid = khach
    duong, du = _cua_chat(uid)
    r = client.get(duong)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("accept-ranges") == "bytes"
    assert r.headers.get("content-length") == str(len(du))


def test_chat_range_hop_le_tra_206(khach):
    client, uid = khach
    duong, du = _cua_chat(uid)
    r = client.get(duong, headers={"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.content == du[:100]


def test_chat_range_vo_nghia_tra_416(khach):
    client, uid = khach
    duong, du = _cua_chat(uid)
    r = client.get(duong, headers={"Range": f"bytes={len(du) + 1}-"})
    assert r.status_code == 416


@pytest.mark.parametrize("tieu_de,ma", [
    ({}, 200),
    ({"Range": "bytes=0-9"}, 206),
    ({"Range": "bytes=999999-"}, 416),
])
def test_media_khong_bao_gio_cache_duoc_o_bien_ke_ca_206_va_416(khach, tieu_de, ma):
    """Bien (Cloudflare) khong duoc cache byte cua mot nguoi cho nguoi khac.

    🔴 Day tung xay ra that o H5: anh output per-user phuc vu o URL duoi `.png`
       bi Cloudflare cache theo phan mo rong roi TRA CHO NGUOI KHONG DANG NHAP.
       Origin da chan 303, nhung bien phuc vu ban cache va bo qua auth.
       `server/app.py:253` chan ca lop loi do bang `no-store` mac dinh.

    ⚠️ Va day la ly do `Cache-Control: private, max-age=3600` ma `chatltt` tu dat
       la MOT CAU LENH CHET — middleware ghi de no. Phep kiem nay co y chot GIA
       TRI CUA NEN TANG chu khong chot gia tri cua app: neu mot ngay nao do app
       "gianh lai" duoc header nay, do la mot hoi quy bao mat, khong phai mot
       tinh nang.

    ⭐ Va no phai dung cho CA BA ma trang thai. Them nhanh 206/416 la them hai
       duong tra loi moi; mot trong hai roi ra khoi luat `no-store` thi lo hong
       H5 quay lai qua cua sau.
    """
    client, uid = khach
    duong, _ = _cua_chat(uid)
    r = client.get(duong, headers=tieu_de)
    assert r.status_code == ma
    assert r.headers.get("cache-control") == "no-store", (
        f"phan hoi {ma} cua duong media co the bi bien cache — xem H5")


# ── Banh coc: khong ai duoc quay lai doc toan tep ───────────────────────────

def test_khong_route_media_nao_con_doc_toan_tep_roi_boc_BytesIO():
    """Chot cach viet, khong chi chot hanh vi.

    `StreamingResponse(io.BytesIO(f.read()))` la khuon da sinh ra ca hai loi P0.
    No chay duoc, tra 200, khong loi nao trong log — nen no se quay lai neu chi
    co mot chu thich can. Phep kiem doc AST, khong doc chuoi.
    """
    import ast
    import pathlib

    goc = pathlib.Path(__file__).resolve().parent.parent
    vi_pham = []
    for duong in (goc / "apps").rglob("*.py"):
        if "__pycache__" in duong.parts:
            continue
        try:
            cay = ast.parse(duong.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for nut in ast.walk(cay):
            # StreamingResponse(io.BytesIO(<gi do>.read()), ...)
            if not (isinstance(nut, ast.Call)
                    and isinstance(nut.func, ast.Name)
                    and nut.func.id == "StreamingResponse"
                    and nut.args):
                continue
            dau = nut.args[0]
            if not (isinstance(dau, ast.Call)
                    and isinstance(dau.func, ast.Attribute)
                    and dau.func.attr == "BytesIO"
                    and dau.args):
                continue
            trong = dau.args[0]
            if (isinstance(trong, ast.Call)
                    and isinstance(trong.func, ast.Attribute)
                    and trong.func.attr == "read"):
                vi_pham.append(f"{duong.relative_to(goc)}:{nut.lineno}")

    assert not vi_pham, (
        "route media doc toan tep vao RAM roi boc BytesIO — dung "
        "`platform_core.phat_media.phat_tu_kho` thay the: " + ", ".join(vi_pham))
