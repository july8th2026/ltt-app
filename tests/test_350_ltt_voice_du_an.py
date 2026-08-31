"""Màn Dự án: khối, thứ tự, sinh tiếng, và quyền sở hữu.

## Ba thứ tệp này canh

1. 🔴 **Nhập kịch bản phải ra ĐƠN VỊ BIÊN TẬP, không ra một khối khổng lồ.**
   Bản đầu gọi `chia_doan(tran_moi_doan=1500)` — đúng con số một *lượt
   inference* chịu được, sai con số cho một *đơn vị sửa*. Đo thật: năm câu vào,
   **một** khối ra. Và thế là hỏng cả tính năng: điểm của Dự án là sửa một đoạn
   rồi đọc lại **mình nó**.

2. **Thứ tự là số THỰC** nên chèn vào giữa là một lượt ghi, không phải đánh số
   lại cả dự án.

3. ⛔ **Quyền lọc trong chính câu truy vấn.** Dự án của người khác phải là 404 ở
   *mọi* cửa, không chỉ ở cửa mở trang.
"""
from __future__ import annotations

import re

import pytest

from apps.ltt_voice import du_an

UID_KHAC = "00000000-0000-0000-0000-000000000000"


# ── Nhập kịch bản: độ mịn ────────────────────────────────────────────────────

class _GiaDuAn:
    """Đủ hình dạng cho `nhap_van_ban` mà không cần CSDL."""

    id = 1


class _GiaDb:
    """Ghi nhận khối được thêm, không chạm CSDL."""

    def __init__(self):
        self.khoi = []

    def add(self, x):
        self.khoi.append(x)

    def flush(self):
        pass


@pytest.fixture()
def db_gia(monkeypatch):
    db = _GiaDb()
    monkeypatch.setattr(du_an, "cac_khoi", lambda _db, _pid: list(db.khoi))

    class Khoi:
        def __init__(self, **kw):
            self.__dict__.update(kw)
            self.thu_tu = kw.get("thu_tu", 0.0)
            self.text = kw.get("text", "")

    monkeypatch.setattr("apps.ltt_voice.tables_du_an.VoiceBlock", Khoi)
    return db


def test_kich_ban_lien_mach_ra_NHIEU_khoi(db_gia):
    """🔴 Phép kiểm chốt đúng lỗi đã đo trên trình duyệt.

    Hai nghìn ký tự là một kịch bản podcast ngắn. Ra hai khối một nghìn ký tự
    thì mỗi lần sửa một chữ là đọc lại năm trăm từ — tức đúng thứ Dự án sinh ra
    để tránh.
    """
    cau = [f"Cau thu {i} noi ve mot y tuong cu the va co do dai vua phai."
           for i in range(1, 31)]
    du_an.nhap_van_ban(db_gia, _GiaDuAn(), " ".join(cau), tran_moi_khoi=1500)

    so = len(db_gia.khoi)
    assert so >= 5, (
        f"kich ban 30 cau chi ra {so} khoi — qua to de sua tung khoi.\n"
        "Xem `du_an.TRAN_KHOI_KHI_NHAP`: 1.500 la tran cua MOT LUOT DOC, "
        "khong phai co cua MOT DON VI BIEN TAP.")
    dai_nhat = max(len(k.text) for k in db_gia.khoi)
    assert dai_nhat <= du_an.TRAN_KHOI_KHI_NHAP, (
        f"khoi dai nhat {dai_nhat} ky tu, vuot {du_an.TRAN_KHOI_KHI_NHAP}")


def test_TON_TRONG_doan_van_cua_tac_gia(db_gia):
    """⭐ Dòng trống là phân đoạn do **người hiểu nội dung** làm.

    Ba đoạn ngắn phải ra đúng ba khối — không được gói chúng lại chỉ vì cả ba
    cộng lại vẫn dưới trần.
    """
    du_an.nhap_van_ban(db_gia, _GiaDuAn(),
                       "Doan mot.\n\nDoan hai.\n\nDoan ba.",
                       tran_moi_khoi=1500)
    assert len(db_gia.khoi) == 3, (
        f"ba doan van ra {len(db_gia.khoi)} khoi — dong trong bi bo qua")
    assert [k.text for k in db_gia.khoi] == ["Doan mot.", "Doan hai.", "Doan ba."]


def test_doan_van_qua_dai_van_bi_cat(db_gia):
    """Trần một lượt đọc là trần **kỹ thuật** — đoạn văn dài hơn vẫn phải cắt."""
    dai = " ".join(f"Cau {i} trong mot doan van rat dai." for i in range(1, 60))
    du_an.nhap_van_ban(db_gia, _GiaDuAn(), dai + "\n\nDoan ngan.",
                       tran_moi_khoi=300)
    assert all(len(k.text) <= 300 for k in db_gia.khoi)
    assert len(db_gia.khoi) > 2


def test_nhap_van_ban_rong_bi_tu_choi(db_gia):
    with pytest.raises(du_an.LoiDuAn):
        du_an.nhap_van_ban(db_gia, _GiaDuAn(), "   ", tran_moi_khoi=1500)


# ── Giọng ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("chon,mong", [
    ("m:Adam", ("", "Adam")),
    ("v:vc_abc", ("vc_abc", "")),
    ("", ("", "")),
    ("   ", ("", "")),
    ("rac", ("", "")),
])
def test_tach_giong(chon, mong):
    """⛔ Đúng MỘT trong hai được khác rỗng.

    `features.chuan_hoa` từ chối nếu cả hai cùng có — hai nguồn giọng cùng lúc
    là một yêu cầu không có câu trả lời đúng. Nên phép tách này không bao giờ
    được trả về cả hai.
    """
    assert du_an.tach_giong(chon) == mong
    v, p = du_an.tach_giong(chon)
    assert not (v and p), "tra ve CA HAI — tang duoi se tu choi"


# ── Khối nào cần sinh ────────────────────────────────────────────────────────

class _K:
    def __init__(self, text="co chu", tt="moi", giong=""):
        self.text, self.trang_thai, self.giong = text, tt, giong
        self.giay, self.credit = 0.0, 0


def test_khoi_can_tao_bo_qua_khoi_rong():
    """⛔ Nộp job cho một khối không có chữ là tiêu một suất GPU và một vòng xếp
    hàng để nhận về một lỗi biết trước."""
    cac = [_K(text="", tt="moi"), _K(text="  ", tt="loi"), _K(tt="moi")]
    assert len(du_an.khoi_can_tao(cac)) == 1


def test_khoi_can_tao_gom_ca_can_tao_lai():
    """`can_tao_lai` = đã có tiếng nhưng văn bản đã đổi. Nó PHẢI được đọc lại."""
    cac = [_K(tt="xong"), _K(tt="can_tao_lai"), _K(tt="loi"), _K(tt="dang_tao")]
    tt = {k.trang_thai for k in du_an.khoi_can_tao(cac)}
    assert tt == {"can_tao_lai", "loi"}, (
        f"chon nham: {tt} — `xong` va `dang_tao` khong duoc nop lai")


def test_tom_tat_mot_giong():
    """⭐ `mot_giong` quyết định có hiện lời khuyên "đọc liền một lượt" hay không.

    Upstream #142: gọi API từng chunk riêng làm mất tính liên tục. Lời khuyên đó
    chỉ đúng khi cả dự án dùng một giọng — sai thì ta khuyên một thứ bất khả.
    """
    assert du_an.tom_tat([_K(giong=""), _K(giong="")])["mot_giong"] is True
    assert du_an.tom_tat([_K(giong="m:Adam"), _K(giong="m:Adam")])["mot_giong"] is True
    assert du_an.tom_tat([_K(giong="m:Adam"), _K(giong="v:vc_x")])["mot_giong"] is False
    assert du_an.tom_tat([])["mot_giong"] is True


# ── Đi qua router thật ───────────────────────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-da.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-du-an")
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
        u = tao_nguoi_dung(db, email="voice-da@test.com",
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
    client.post("/login", data={"username": "voice-da@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice/du-an").text)
    assert m
    return m.group(1)


def _tao(client, ten="Du an thu") -> str:
    r = client.post("/ltt-voice/du-an/tao",
                    data={"ten": ten, "giong": "m:Adam",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"], d
    return d["id"]


def test_tao_du_an_TREN_SQLITE(khach):
    """🔴 Phép kiểm này tồn tại vì nó ĐÃ ĐỎ, và vì lý do khó đoán.

    `BigInteger` primary key **không tự tăng trên SQLite** — chỉ `INTEGER PRIMARY
    KEY` mới. Nên `INSERT` không kèm `id` ném `NOT NULL constraint failed`, và
    tính năng chết ở **máy phát triển** trong khi chạy bình thường ở production
    (PostgreSQL). Tức nó hỏng ở đúng chỗ khó tin nhất.

    Cách sửa: `BigInteger().with_variant(Integer, "sqlite")` — SQLAlchemy issue
    #2074, câu trả lời của chính Michael Bayer.
    """
    client, _uid = khach
    pid = _tao(client)
    assert pid.startswith("vp_")


def test_nhap_qua_URL_ra_nhieu_khoi(khach):
    """Chốt TÍNH CHẤT, không chốt một con số.

    ⭐ Bản đầu của phép kiểm này đòi `>= 4` khối cho một kịch bản 1.150 ký tự.
       Nó đỏ với 3 — và **mã đúng**, con số trong phép kiểm mới sai (1.150 / 400
       thì 3 là kết quả duy nhất đúng).

       Một phép kiểm neo vào con số đầu ra sẽ đỏ mỗi lần ai đó chỉnh
       `TRAN_KHOI_KHI_NHAP`, kể cả khi chỉnh đúng — và đó là loại tín hiệu sai
       làm người ta bắt đầu sửa phép kiểm thay vì đọc nó.
       Thứ thật sự phải đúng là: **chia ra nhiều khối, và không khối nào quá to
       để sửa.**
    """
    client, _uid = khach
    pid = _tao(client)
    van = " ".join(f"Cau thu {i} co do dai vua phai de doc thanh tieng."
                   for i in range(1, 25))
    r = client.post(f"/ltt-voice/du-an/{pid}/nhap",
                    data={"text": van, "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    assert r.json()["so_khoi"] > 1, (
        f"kich ban {len(van)} ky tu ra mot khoi duy nhat: {r.json()}")

    html = client.get(f"/ltt-voice/du-an/{pid}").text
    chu = re.findall(r'class="lv-khoi-chu"[^>]*>([^<]*)</textarea>', html)
    assert chu, "khong doc duoc noi dung khoi tu trang"
    assert max(len(c) for c in chu) <= du_an.TRAN_KHOI_KHI_NHAP, (
        f"khoi dai nhat {max(len(c) for c in chu)} ky tu, "
        f"vuot {du_an.TRAN_KHOI_KHI_NHAP}")


def test_them_khoi_vao_GIUA_khong_danh_so_lai(khach):
    """⭐ `thu_tu` là số thực nên chèn giữa là MỘT lượt ghi.

    Phép kiểm chốt kết quả nhìn thấy được: thứ tự hiển thị đúng, và khối cũ
    **giữ nguyên** `thu_tu` của chúng.
    """
    client, _uid = khach
    pid = _tao(client)
    c = _csrf(client)
    for t in ("mot", "hai"):
        client.post(f"/ltt-voice/du-an/{pid}/khoi/them",
                    data={"text": t, "csrf_token": c})

    truoc = re.findall(r'data-thutu="([\d.]+)"',
                       client.get(f"/ltt-voice/du-an/{pid}").text)
    assert len(truoc) == 2

    client.post(f"/ltt-voice/du-an/{pid}/khoi/them",
                data={"text": "giua", "sau": truoc[0], "csrf_token": c})

    html = client.get(f"/ltt-voice/du-an/{pid}").text
    sau = re.findall(r'data-thutu="([\d.]+)"', html)
    assert len(sau) == 3
    assert sau == sorted(sau, key=float), "thu tu hien thi khong tang dan"
    # Hai khối cũ giữ NGUYÊN vị trí — đó là toàn bộ điểm của số thực.
    assert truoc[0] in sau and truoc[1] in sau, (
        f"khoi cu bi danh so lai: truoc={truoc} sau={sau}")
    assert html.index(">giua<") > html.index(">mot<")
    assert html.index(">giua<") < html.index(">hai<")


def test_sua_van_ban_chuyen_sang_can_tao_lai(khach):
    """⭐ `can_tao_lai`, KHÔNG phải `moi`.

    Khác nhau ở chỗ quan trọng: `can_tao_lai` nghĩa là **vẫn còn tệp tiếng cũ
    nghe được**. Gộp vào `moi` thì màn hình vứt bản cũ đi trong khi khách có thể
    vẫn muốn nghe lại để so — và họ mất nó mà không bấm gì cả.
    """
    from sqlalchemy import select

    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceBlock

    client, _uid = khach
    pid = _tao(client)
    c = _csrf(client)
    client.post(f"/ltt-voice/du-an/{pid}/khoi/them",
                data={"text": "ban dau", "csrf_token": c})

    gen = dbmod.get_session()
    db = next(gen)
    try:
        k = db.execute(select(VoiceBlock)).scalars().first()
        k.trang_thai = "xong"
        k.audio_key = "voice/out/x/y/tieng.wav"
        db.commit()
        bid = k.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/sua",
                    data={"text": "da sua", "csrf_token": c})
    assert r.json()["trang_thai"] == "can_tao_lai"


def test_sua_khoi_qua_tran_bi_tu_choi(khach):
    from apps.ltt_voice.tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

    client, _uid = khach
    pid = _tao(client)
    c = _csrf(client)
    client.post(f"/ltt-voice/du-an/{pid}/khoi/them",
                data={"text": "x", "csrf_token": c})
    from sqlalchemy import select

    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceBlock
    gen = dbmod.get_session()
    db = next(gen)
    try:
        bid = db.execute(select(VoiceBlock)).scalars().first().id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/sua",
                    data={"text": "a" * (TRAN_KY_TU_CONG_KHAI + 1),
                          "csrf_token": c})
    assert r.status_code == 400


# ── Quyền sở hữu ─────────────────────────────────────────────────────────────

def test_du_an_cua_nguoi_khac_la_404_o_MOI_cua(khach):
    """⛔ Không chỉ ở cửa mở trang. Một cửa quên vế `owner_id` là đủ."""
    import platform_core.db as dbmod
    from apps.ltt_voice.tables_du_an import VoiceProject

    client, _uid = khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        la = VoiceProject(owner_id=UID_KHAC, ten="Cua nguoi khac")
        db.add(la)
        db.commit()
        pid = la.public_id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    c = _csrf(client)
    assert client.get(f"/ltt-voice/du-an/{pid}").status_code == 404
    assert client.get(f"/ltt-voice/du-an/{pid}/trang-thai").status_code == 404
    for duong, du_lieu in (
            (f"/ltt-voice/du-an/{pid}/sua", {"ten": "doi ten"}),
            (f"/ltt-voice/du-an/{pid}/xoa", {}),
            (f"/ltt-voice/du-an/{pid}/nhap", {"text": "abc"}),
            (f"/ltt-voice/du-an/{pid}/khoi/them", {"text": "abc"}),
            (f"/ltt-voice/du-an/{pid}/doc-tat-ca", {}),
            (f"/ltt-voice/du-an/{pid}/khoi/1/sua", {"text": "abc"}),
            (f"/ltt-voice/du-an/{pid}/khoi/1/xoa", {}),
            (f"/ltt-voice/du-an/{pid}/khoi/1/doc", {})):
        r = client.post(duong, data=dict(du_lieu, csrf_token=c))
        assert r.status_code == 404, f"{duong} tra {r.status_code}, phai 404"


def test_moi_cua_du_an_doi_csrf(khach):
    client, _uid = khach
    pid = _tao(client)
    for duong in (f"/ltt-voice/du-an/{pid}/sua",
                  f"/ltt-voice/du-an/{pid}/nhap",
                  f"/ltt-voice/du-an/{pid}/khoi/them",
                  f"/ltt-voice/du-an/{pid}/doc-tat-ca"):
        r = client.post(duong, data={"csrf_token": "sai-bet", "text": "x",
                                     "ten": "x"})
        assert r.status_code >= 400, f"{duong} nhan CSRF sai ma van {r.status_code}"


def test_khong_co_loai_job_moi():
    """🔴 Dự án dùng lại `ltt_voice.synthesize`, KHÔNG khai loại job riêng.

    Một loại job riêng phải chép lại toàn bộ phần khó: giữ credit, quyết toán
    theo giây thật, một-GPU-một-việc, thử lại, huỷ, hoàn tiền, lịch sử. Và bản
    chép sẽ lệch ở chỗ đắt nhất.
    """
    from apps.ltt_voice.manifest import MANIFEST

    assert set(MANIFEST.job_types) == {"ltt_voice.synthesize", "ltt_voice.enroll"}, (
        f"job_types da no ra: {MANIFEST.job_types}")
