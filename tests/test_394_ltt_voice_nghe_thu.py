"""NGHE THỬ một giọng — và ba thứ quanh nó phải không gãy.

## Vì sao tệp này tồn tại

Trước 02/09/2026 trang Giọng liệt kê hai mươi cái tên kèm ba nhãn mô tả và
**không cách nào nghe được giọng nào**. Cách duy nhất để biết một giọng nghe ra
sao là tạo một lượt đọc thật — tức trả tiền để xem mình có muốn mua không.

`nghe_thu.py` đóng lỗ đó bằng cách dựng sẵn một tệp cho mỗi giọng rồi phục vụ
như tệp tĩnh. Ba mặt của việc đó cần bánh cóc, và chúng hỏng theo ba kiểu khác
nhau:

1. **Khoá mang phiên bản.** Mất phiên bản thì đổi câu đọc thử xong khách vẫn
   nghe câu cũ — và không ai phát hiện, vì cả hai đều là tiếng nói bình thường.
2. **Cửa đọc mở thêm hai hình dạng khoá.** Đây là chỗ nguy hiểm: cùng thư mục
   với tệp nghe thử của khách có `repr-*.npz` chứa `speaker_emb`.
3. **`dung()` không được phép ném.** Người gọi là vòng bảo trì và đuôi job ghi
   danh; một tệp nghe thử hỏng không được đánh hỏng một giọng đã ghi danh xong.
"""
from __future__ import annotations

import io
import re
import struct

import pytest

from apps.ltt_voice import nghe_thu

UID_KHAC = "00000000-0000-0000-0000-000000000000"


def _wav(giay: float = 0.5, sr: int = 8000) -> bytes:
    n = int(sr * giay)
    d = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(d)) + d)


# ── 1. Hình dạng khoá ────────────────────────────────────────────────────────

def test_khoa_mau_mang_phien_ban():
    """🔴 Mất phiên bản = đổi câu đọc thử mà khách vẫn nghe câu cũ, mãi mãi.

    Tệp cũ nằm trong kho và `co_san()` thấy nó, nên không có gì dựng lại. Triệu
    chứng là **không có triệu chứng** — âm thanh vẫn phát, vẫn đúng giọng, chỉ
    là nội dung không còn khớp thứ mã nói.
    """
    khoa = nghe_thu.khoa_mau("Adam")
    assert nghe_thu.PHIEN_BAN in khoa
    assert khoa.startswith("voice/mau/")
    assert khoa.endswith(".wav")


def test_khoa_rieng_mang_phien_ban_va_tien_to_preview():
    khoa = nghe_thu.khoa_rieng("u1", "vc_" + "a" * 32)
    assert nghe_thu.PHIEN_BAN in khoa
    assert khoa.rsplit("/", 1)[-1].startswith("preview-")
    assert khoa.startswith("voice/u1/")


def test_slug_giu_dau_tieng_viet():
    """⛔ `"Minh Đức"` và `"Minh Duc"` phải là hai khoá KHÁC nhau.

    Bỏ dấu cho "an toàn" là gộp hai giọng có thật thành một khoá — và giọng thứ
    hai sẽ phục vụ tệp của giọng thứ nhất, im lặng.
    """
    assert nghe_thu.khoa_mau("Minh Đức") != nghe_thu.khoa_mau("Minh Duc")
    assert "Đức" in nghe_thu.khoa_mau("Minh Đức")


@pytest.mark.parametrize("ten", ["a/b", "..", "a\\b", "a?b=1", "a b"])
def test_slug_khong_de_lot_ky_tu_pha_duong_dan(ten):
    """Tên preset đi vào **khoá kho** rồi vào **URL**. Một dấu `/` lọt qua là
    một khoá trỏ sang thư mục khác."""
    khoa = nghe_thu.khoa_mau(ten)
    phan = khoa.split("/")
    assert phan[:2] == ["voice", "mau"]
    assert len(phan) == 4, f"slug lam vo hinh dang khoa: {khoa}"
    assert ".." not in phan[2]


def test_slug_rong_van_ra_mot_doan_hop_le():
    assert nghe_thu.khoa_mau("///").split("/")[2] == "khong-ten"


# ── 2. `dung()` không được ném ───────────────────────────────────────────────

def test_dung_nuot_loi_va_tra_false(monkeypatch):
    """⛔ Người gọi là đuôi của job GHI DANH. Ném ở đây nghĩa là một giọng đã
    ghi danh xong bị đánh hỏng vì một tệp nghe thử — đổi sai chiều hoàn toàn."""
    from apps.ltt_voice import features

    monkeypatch.setattr(nghe_thu, "co_san", lambda k: False)

    def _no(*a, **k):
        raise RuntimeError("cong giong chet")

    monkeypatch.setattr(features, "goi_cong", _no)
    assert nghe_thu.dung("voice/mau/x/v.wav", preset="Adam") is False


def test_co_san_tra_false_khi_kho_nem(monkeypatch):
    """Kho hỏng và tệp chưa dựng phải dẫn tới CÙNG một hành vi ở giao diện."""
    import platform_core.storage as st

    class _KhoHong:
        def exists(self, key):
            raise RuntimeError("kho hong")

    monkeypatch.setattr(st, "get_storage", lambda: _KhoHong())
    assert nghe_thu.co_san("voice/mau/x/v.wav") is False


# ── 3. Vòng bảo trì có trần ──────────────────────────────────────────────────

def test_bao_tri_dung_toi_da_mot_tran_moi_luot(monkeypatch):
    """⛔ Không có trần thì một lượt bảo trì giữ GPU khoảng một phút liền, và
    trong khoảng đó job của khách chờ mà không có gì giải thích."""
    from apps.ltt_voice import giong_mau, sidecar_client

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(nghe_thu, "co_san", lambda k: False)
    da_goi = []
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda khoa, **k: da_goi.append(khoa) or True)

    nghe_thu.bao_tri()

    assert len(da_goi) == nghe_thu.MOI_LUOT_TOI_DA
    assert nghe_thu.MOI_LUOT_TOI_DA < len(giong_mau.DANH_SACH), (
        "tran phai NHO hon so giong, khong thi no khong con la mot tran")


def test_bao_tri_im_lang_khi_cong_chua_bat(monkeypatch):
    from apps.ltt_voice import sidecar_client

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: False)
    monkeypatch.setattr(nghe_thu, "dung",
                        lambda *a, **k: pytest.fail("khong duoc goi"))
    nghe_thu.bao_tri()  # khong duoc nem, khong duoc goi `dung`


def test_manifest_khai_bao_tri():
    """Việc nền phải đi qua **hợp đồng**, không phải một vòng lặp app tự dựng.

    Một vòng tự dựng chạy ở MỌI tiến trình worker; hợp đồng chạy dưới lease
    `bao_tri` nên đúng một lần trên toàn cụm.
    """
    from apps.ltt_voice.manifest import MANIFEST
    assert MANIFEST.bao_tri is nghe_thu.bao_tri
    assert MANIFEST.bao_tri_moi_giay >= 60


# ── 4. Cửa đọc — hai đường MỞ và một đường phải VẪN ĐÓNG ─────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nghe-thu.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-nghe-thu")
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
        u = tao_nguoi_dung(db, email="nghe-thu@test.com",
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
    r = client.post("/login", data={"username": "nghe-thu@test.com",
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


def test_nghe_thu_giong_mau_doc_duoc_boi_moi_khach(khach):
    """⭐ `voice/mau/…` KHÔNG mang `owner_id` — có chủ ý.

    Giọng dựng sẵn không thuộc về ai; nhân bản hai mươi tệp theo từng chủ sở hữu
    là nhân số lượt chiếm GPU lên bằng số người dùng để bảo vệ một câu chào cố
    định đã đăng trong tài liệu.
    """
    client, _uid = khach
    khoa = nghe_thu.khoa_mau("Adam")
    _dat(khoa, _wav())
    r = client.get(f"/ltt-voice/audio/{khoa}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")


def test_nghe_thu_giong_rieng_cua_chinh_minh_doc_duoc(khach):
    client, uid = khach
    khoa = nghe_thu.khoa_rieng(uid, "vc_" + "a" * 32)
    _dat(khoa, _wav())
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 200


def test_nghe_thu_giong_rieng_cua_NGUOI_KHAC_khong_doc_duoc(khach):
    """Giọng nhân bản là giọng của một người thật — nó không dùng chung."""
    client, _uid = khach
    khoa = nghe_thu.khoa_rieng(UID_KHAC, "vc_" + "b" * 32)
    _dat(khoa, _wav())
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404


def test_bieu_dien_npz_VAN_khong_ro_ra_sau_khi_mo_them_hai_duong(khach):
    """🔴 BÁNH CÓC QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    Tệp nghe thử của khách nằm **cùng thư mục** với `repr-<van tay>.npz` chứa
    `speaker_emb` — thứ `tables.py` nói thẳng là *"KHÔNG BAO GIỜ ra ngoài"*.

    Nới cửa cho `preview-*` là lần thứ hai thư mục ấy được mở thêm một đường.
    Lần thứ nhất (`source.*`) suýt rò chính tệp này. Nên phép kiểm phải chạy lại
    **sau** mỗi lần nới, không phải một lần lúc viết `source.*`.
    """
    from apps.ltt_voice import tham_chieu
    client, uid = khach
    pid = "vc_" + "c" * 32
    khoa = tham_chieu.khoa_bieu_dien(uid, pid, "vantay123")
    _dat(khoa, b"\x00npz-gia")
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404, (
        "bieu dien nguoi noi ro ra ngoai — cua mo theo THU MUC chu khong theo "
        "TEN TEP")


@pytest.mark.parametrize("ten_tep", [
    "preview.npz",            # dung duoi, sai tien to
    "repr-preview-x.npz",     # co chu `preview` nhung khong o DAU
    "xpreview-v1.wav",        # `preview` khong o dau
])
def test_chi_dung_tien_to_preview_moi_lot(khach, ten_tep):
    """Cửa mở theo **tiền tố tên tệp**, không theo "có chứa chữ preview"."""
    client, uid = khach
    khoa = f"voice/{uid}/vc_" + "d" * 32 + f"/{ten_tep}"
    _dat(khoa, b"\x00")
    assert client.get(f"/ltt-voice/audio/{khoa}").status_code == 404


def test_nghe_thu_van_doi_dang_nhap(khach):
    """⛔ Mở cho mọi khách ĐÃ ĐĂNG NHẬP, không phải mở cho Internet.

    Không phải để giấu nội dung — mà để đường này không thành một CDN mở.
    """
    from fastapi.testclient import TestClient

    from server.app import create_app
    khoa = nghe_thu.khoa_mau("Adam")
    _dat(khoa, _wav())
    la = TestClient(create_app(), base_url="https://testserver",
                    follow_redirects=False)
    try:
        r = la.get(f"/ltt-voice/audio/{khoa}")
        assert r.status_code in (302, 303, 401, 403), (
            f"khach chua dang nhap doc duoc tep nghe thu (HTTP {r.status_code})")
    finally:
        la.close()


# ── 5. Ba trạng thái của cổng ────────────────────────────────────────────────

def test_trang_thai_phan_biet_du_BA_nhanh(monkeypatch):
    """🔴 Ba chứ không phải hai.

    Đo được 02/09/2026: chip **"Engine sẵn sàng"** màu xanh nằm trên một trang
    mà mọi lượt bấm Tạo đều trả *"Máy tạo tiếng nói chưa sẵn sàng"* — vì
    `san_sang()` chỉ hỏi *"biến môi trường có được đặt không"*.

    Hai câu mâu thuẫn trên cùng một màn hình, và câu to hơn, xanh hơn là câu
    sai. Hai trạng thái hỏng cần hai câu trả lời khác nhau: *chưa bật* là việc
    của người cài đặt, *không trả lời* là một dịch vụ đã cài nhưng đang chết.
    """
    from apps.ltt_voice import sidecar_client

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: False)
    assert sidecar_client.trang_thai() == "chua_bat"

    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    monkeypatch.setattr(sidecar_client, "song", lambda **k: False)
    assert sidecar_client.trang_thai() == "khong_tra_loi"

    monkeypatch.setattr(sidecar_client, "song", lambda **k: True)
    assert sidecar_client.trang_thai() == "san_sang"


def test_song_khong_nem_khi_cong_chet(monkeypatch):
    """`song()` nằm trên đường dựng trang — nó phải trả `False`, không ném."""
    from apps.ltt_voice import sidecar_client

    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "x")
    monkeypatch.setenv("LTT_VOICE_SIDECAR_PORT", "8199")  # khong ai nghe
    sidecar_client._NHIP_SONG["luc"] = 0.0
    assert sidecar_client.song(buoc=True) is False


def test_song_co_bo_nho_dem(monkeypatch):
    """⚠️ `san_sang()` chạy ở MỌI lượt dựng trang của năm màn. Hàm đắt phải có
    bộ nhớ đệm, không thì mỗi trang là một chuỗi lượt hỏi mạng."""
    from apps.ltt_voice import sidecar_client

    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "x")
    dem = {"n": 0}

    def _goi_gia(duong, body=None, **k):
        dem["n"] += 1
        return {"ok": True}, {}

    monkeypatch.setattr(sidecar_client, "_goi", _goi_gia)
    sidecar_client._NHIP_SONG["luc"] = 0.0
    for _ in range(5):
        sidecar_client.song()
    assert dem["n"] == 1, f"hoi cong {dem['n']} lan cho 5 luot — mat bo nho dem"


# ── 6. Đường nghe thử tới được khuôn mẫu ─────────────────────────────────────

def test_duong_cho_trang_BO_QUA_giong_chua_co_tep(monkeypatch):
    """⭐ Giọng chưa có tệp thì **vắng mặt khỏi dict**, không phải chuỗi rỗng.

    Khuôn mẫu hỏi `duong_nghe.get(ma)`. Một chuỗi rỗng vẫn là một khoá có mặt,
    và nếu ai đó đổi phép hỏi thành `ma in duong_nghe` thì nút phát sẽ hiện với
    `src=""` — một nút bấm được mà không kêu, đúng thứ tệ nhất.
    """
    co = {"Adam"}
    monkeypatch.setattr(nghe_thu, "co_san",
                        lambda k: any(("/" + t + "/") in k for t in co))
    ra = nghe_thu.duong_cho_trang(duong_audio="/x/audio", owner_id="u1",
                                  ma_mau=["Adam", "Minh Đức"])
    assert set(ra) == {"Adam"}
    assert ra["Adam"].startswith("/x/audio/voice/mau/")


def test_duong_cho_trang_dung_khoa_rieng_cho_giong_nhan_ban(monkeypatch):
    monkeypatch.setattr(nghe_thu, "co_san", lambda k: True)
    pid = "vc_" + "e" * 32
    ra = nghe_thu.duong_cho_trang(duong_audio="/x/audio", owner_id="u9",
                                  rieng=[pid])
    assert ra[pid] == "/x/audio/" + nghe_thu.khoa_rieng("u9", pid)


def test_man_giong_truyen_duong_nghe_xuong_khuon(khach, monkeypatch):
    """Bánh cóc bắc cầu: route -> khuôn -> nút thật trong HTML.

    ⛔ Ba tầng, và mỗi tầng đều đã từng hỏng riêng ở app này: route quên truyền
       biến, khuôn quên đọc, khuôn quên nạp `voice.js`. Một phép kiểm chỉ nhìn
       một tầng sẽ xanh trong khi trang chết.
    """
    client, _uid = khach
    monkeypatch.setattr(nghe_thu, "co_san", lambda k: True)
    r = client.get("/ltt-voice/giong")
    assert r.status_code == 200
    assert 'data-nghe="' in r.text, "khong co nut nghe thu nao trong HTML"
    assert "voice/mau/" in r.text


def test_khuon_co_nut_nghe_thi_PHAI_nap_voice_js():
    """Cùng khuôn bánh cóc với nút chép (`test_364`).

    Bản đầu của màn API quên `{% block scripts %}`: mọi phép kiểm HTTP xanh vì
    HTML **đúng**, chỉ hành vi sai — nút hiện đầy đủ, bấm được, và không làm gì.
    `data-nghe` mở đúng cái bẫy ấy lần thứ hai.
    """
    import pathlib
    goc = pathlib.Path(__file__).resolve().parents[1] / "apps/ltt_voice/templates"
    # Khuôn con không tự nạp script — tìm khuôn TRANG nào include chúng.
    con = {p.name for p in goc.glob("_*.html")
           if "data-nghe" in p.read_text(encoding="utf-8")}
    for trang in goc.glob("ltt_voice_*.html"):
        noi_dung = trang.read_text(encoding="utf-8")
        can = ("data-nghe" in noi_dung
               or any(c in noi_dung for c in con))
        if can:
            assert "voice.js" in noi_dung, (
                f"{trang.name} co nut nghe thu (truc tiep hoac qua "
                f"{sorted(con)}) nhung KHONG nap voice.js")
