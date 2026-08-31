"""Vỏ dùng chung của LTT Voice Studio — sáu tab, và tab đang mở phải SÁNG.

## Vì sao tệp này tồn tại

P1 của loạt giao diện (`docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md`) mở thanh tab
từ ba lên sáu và sửa một lỗi **đã sống từ ngày phát hành**: không màn nào của
Voice truyền khoá `nav`, nên phép so `nav == entry.nav_key` trong `base.html`
luôn False và **cả ba tab đều xám**.

⭐ Điều đáng học không phải "quên một khoá", mà là **hình dạng của lỗi**: trang
   vẫn trả 200, Jinja không than một tiếng (`Undefined == 'x'` là False, không
   phải lỗi), và không phép kiểm nào trong 69 phép kiểm sẵn có đụng tới nó. Nó
   chỉ nhìn thấy được bằng mắt, trên một trình duyệt thật — đúng điều `CLAUDE.md`
   quy tắc 5 nói.

Nên ba nhóm phép kiểm dưới đây nhắm đúng ba cách vỏ có thể hỏng **mà vẫn 200**:

  1. hằng số `vo.NAV_*` lệch khỏi `manifest.nav`  -> tab không bao giờ sáng;
  2. một tab trỏ tới đường không có route          -> bấm vào là 404;
  3. `built=False` lệch khỏi `vo.CHUA_XAY`         -> trang chưa xây ném KeyError.
"""
from __future__ import annotations

import re

import pytest

from apps.ltt_voice import vo
from apps.ltt_voice.manifest import MANIFEST

#: Năm tab, đúng thứ tự luồng làm việc. Chốt bằng một danh sách gõ tay chứ không
#: bằng `len(...)`: một phép kiểm đếm số lượng vẫn xanh khi ai đó đổi `Dự án`
#: thành một tab khác, và bài học "chốt TẬP HỢP không chốt số lượng" đã có sẵn
#: trong bộ nhớ dự án.
TAB_MONG_DOI = [
    ("/ltt-voice", vo.NAV_STUDIO, True),
    ("/ltt-voice/giong", vo.NAV_GIONG, True),
    ("/ltt-voice/du-an", vo.NAV_DU_AN, True),
    ("/ltt-voice/lich-su", vo.NAV_LICH_SU, True),
    ("/ltt-voice/api", vo.NAV_API, True),
]


# ── 1. Hằng số khớp manifest ─────────────────────────────────────────────────

def test_nav_key_cua_vo_khop_manifest():
    """`vo.NAV_*` phải khớp TỪNG `NavEntry.nav_key`, theo đúng thứ tự.

    🔴 Đây là mắt xích duy nhất giữ tab sáng. Lệch một ký tự thì `base.html` so
       ra False và tab lặng lẽ không sáng — không lỗi, không cảnh báo, trang vẫn
       200. Chỉ mắt người mới thấy, và chỉ khi người đó tình cờ nhìn.
    """
    that = [(e.path, e.nav_key, e.built) for e in MANIFEST.nav]
    assert that == TAB_MONG_DOI, (
        "Thanh tab lech khoi hang so trong `vo.py`.\n"
        f"  manifest : {that}\n"
        f"  mong doi : {TAB_MONG_DOI}\n"
        "Sua CA HAI cho, va nho: tab khong sang la mot loi KHONG co trieu chung.")


def test_khong_con_tab_nao_chua_xay():
    """Sau P8 cả sáu màn đều đã xây — và cơ chế giữ chỗ đã gỡ theo.

    ⭐ Phép kiểm này THAY một phép kiểm cũ (`built=False` phải khớp
       `vo.CHUA_XAY`). Nó không bị xoá vì "không còn dùng": nó đổi việc, vì thứ
       nó canh đã đổi. Trước P8 rủi ro là *tab có mà nội dung không*; sau P8 rủi
       ro là *ai đó thêm `built=False` mà quên rằng trang giữ chỗ không còn tồn
       tại* — tab sẽ dẫn tới 404, đúng thứ cơ chế cũ sinh ra để tránh.

    ⛔ Nên nếu phép kiểm này đỏ: đừng lật `built` về `True` cho xong. Hoặc xây
       màn đó, hoặc dựng lại trang giữ chỗ. Xem `routes/__init__.py` — nó ghi
       lại cái bẫy thứ tự đăng ký đi kèm cơ chế ấy.
    """
    chua_xay = [e.nav_key for e in MANIFEST.nav if not e.built]
    assert chua_xay == [], (
        f"tab chua xay: {chua_xay} — nhung trang giu cho da go o P8, nen bam "
        f"vao se la 404. Xem docstring.")
    assert not hasattr(vo, "CHUA_XAY"), (
        "vo.CHUA_XAY da go o P8; con lai la noi dung mo coi khong ai doc")


class _RequestGia:
    """Đủ hình dạng cho `ngu_canh`: một phiên ghi được.

    ⛔ Từ khi `ngu_canh` phát `csrf_token`, nó **bắt buộc** cần một `request` thật
       có `.session`. Phép kiểm này trước đó truyền `None` và vẫn xanh — vì lúc ấy
       `ngu_canh` **không hề động đến `request`**, chính là lỗi P0 đã khiến mọi form
       Voice render token rỗng trên production.

    ⭐ Nên **không nới lỏng `ngu_canh` cho `None` đi qua** để phép kiểm xanh lại.
       Làm thế là dựng lại đúng cái cửa đã cho lỗi đó lọt. Phép kiểm đổi, không
       phải mã đổi.
    """

    def __init__(self):
        self.session = {}


def test_ngu_canh_bat_buoc_nav_key():
    """Không có mặc định cho `nav_key`.

    Có mặc định thì một màn mới quên truyền sẽ **sáng nhầm tab** thay vì báo lỗi
    — và sáng nhầm là loại lỗi không ai đi báo.
    """
    with pytest.raises(TypeError):
        vo.ngu_canh(_RequestGia(), None)  # type: ignore[call-arg]

    d = vo.ngu_canh(_RequestGia(), None, nav_key=vo.NAV_GIONG)
    assert d["nav"] == vo.NAV_GIONG
    # `base.html` đọc đúng khoá tên `nav`. Đổi tên khoá là gãy vỏ.
    assert "nav" in d and "manifest" in d and "hang_doi" in d
    # 🔴 CHỐT CHÍNH LỖI P0: `ngu_canh` phải PHÁT token, không chỉ để chỗ trống.
    #    Mọi khuôn mẫu Voice viết `value="{{ csrf_token }}"`; thiếu khoá này thì
    #    Jinja render chuỗi rỗng, không cảnh báo, và **mọi POST trả 400**.
    assert d.get("csrf_token"), (
        "ngu_canh() khong phat csrf_token — moi form Voice se render value=\"\"")


# ── 2 + 3. Đi qua router thật ────────────────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một tài khoản đã đăng nhập, trên CSDL sqlite dùng một lần.

    Cùng khuôn `tests/test_340_ltt_voice_trang_render.py` — cố tình đi đường dài
    nhất còn chạy được trong test: app thật, đăng nhập thật, GET thật.
    """
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-vo.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-vo")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    # Bảng riêng của app: quên dòng này thì trang ném `no such table` và lớp xử
    # lý lỗi trả **200 kèm một trang lỗi** — tức xanh nhầm.
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="voice-vo@test.com",
                       password="matkhau-tot-12", is_verified=True)
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
    assert m, "khong lay duoc csrf_token tu /login"
    r = client.post("/login", data={"username": "voice-vo@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303), f"dang nhap that bai: {r.status_code}"
    try:
        yield client
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


@pytest.mark.parametrize("duong,nav_key,_built", TAB_MONG_DOI)
def test_moi_tab_co_route_that(khach, duong, nav_key, _built):
    """Tab đã hiện trên thanh thì bấm vào PHẢI tới một chỗ nói được điều gì đó.

    ⛔ Một tab dẫn tới 404 tệ hơn không có tab: nó biến một lời hứa thành một
       lỗi. Đó là lý do ba màn chưa xây có route thật chứ không để trống.
    """
    r = khach.get(duong)
    assert r.status_code == 200, (
        f"{duong} tra {r.status_code}. Tab {nav_key} co tren thanh nhung "
        f"bam vao khong toi dau.\n{r.text[:300]}")


@pytest.mark.parametrize("duong,nav_key,_built", TAB_MONG_DOI)
def test_tab_dang_mo_thi_sang(khach, duong, nav_key, _built):
    """🔴 Phép kiểm chốt đúng lỗi P1 sửa.

    `base.html` gắn `class="on"` cho tab có `nav_key` khớp khoá `nav`. Trước P1
    khoá đó không bao giờ được đặt, nên **không tab nào từng sáng** — và trang
    vẫn 200 suốt thời gian ấy.

    Neo vào `href` + `class="on"` chứ không vào nhãn: nhãn đi qua `_()` nên nó
    đổi theo ngôn ngữ, và một phép kiểm neo vào bản dịch sẽ đỏ vào ngày ai đó
    sửa một câu chữ — tín hiệu sai, đúng loại làm người ta mất tin vào bánh cóc.
    """
    r = khach.get(duong)
    assert r.status_code == 200

    # Thẻ <a> của chính tab này, trong thanh `.apptabs`.
    the = re.search(r'<a href="' + re.escape(duong) + r'" class="([^"]*)"', r.text)
    assert the, (
        f"khong thay tab {duong} tren thanh apptabs.\n"
        "Neu thanh khong render thi `app_tabs()` da khong nhan ra app — kiem "
        "`platform_core/app_access.app_cho_path`.")
    assert "on" in the.group(1).split(), (
        f"tab {duong} KHONG sang du dang mo (class={the.group(1)!r}).\n"
        "Nghia la route khong truyen `nav`, hoac truyen sai `nav_key`. "
        "Dung `vo.ngu_canh(..., nav_key=vo.NAV_...)`.")


def test_dung_mot_tab_sang_moi_luot(khach):
    """Đúng một tab sáng — không hai, không không.

    Hai tab cùng sáng nghĩa là hai `NavEntry` trùng `nav_key`; đó là lỗi lặng
    khác của cùng cơ chế.
    """
    for duong, _nav, _b in TAB_MONG_DOI:
        r = khach.get(duong)
        so_sang = len(re.findall(r'<a href="/ltt-voice[^"]*" class="[^"]*\bon\b',
                                 r.text))
        assert so_sang == 1, f"{duong}: co {so_sang} tab sang, phai la 1"


def test_man_api_noi_dung_su_that_ve_cua_dang_dong(khach):
    """Màn API phải nói cửa đang ĐÓNG khi nó đóng, và không đưa lệnh chép được.

    🔴 Đây là chốt quan trọng nhất của màn này, và nó có tiền lệ đắt: `CLAUDE.md`
       đã hai lần nói sai về chính khu API — cả hai lần **về phía nguy hiểm**
       (ghi "chưa mở" trong khi máy chủ đang bán). Chốt này canh chiều ngược
       lại, cũng nguy hiểm không kém: mời khách gọi một cửa chưa mở.

    ⛔ Vì sao "không có lệnh chép được" chứ không chỉ "có một câu cảnh báo": một
       lệnh curl nằm sẵn trên trang sẽ được chép bất kể câu chữ quanh nó, rồi
       trả 404 — mà 404 ấy đến từ Cloudflare hoặc từ cổng, không `request_id`,
       không dòng nào trong `public_api_requests`. Khách đọc thành "khoá sai",
       đi tạo khoá mới, vẫn 404, và **phía ta không thấy gì cả**.

    ⚠️ Bộ test chạy với `LTT_PUBLIC_API` không đặt, nên đây là trạng thái đóng —
       cùng trạng thái production hôm nay (`speech.ltt` không có trong
       `LTT_PUBLIC_API_TOOLS`).
    """
    from apps.ltt_voice import doc_man_api
    assert doc_man_api.trang_thai_tool()["tool_mo"] is False, (
        "phep kiem nay gia dinh cua DONG; moi truong test da doi")

    r = khach.get("/ltt-voice/api")
    assert r.status_code == 200
    than = re.search(r'<section class="lv-man[^"]*".*?</section>', r.text, re.S)
    assert than, "khong co than man `.lv-man`"
    than = than.group(0)

    assert "alert-warn" in than, "cua dong ma khong co canh bao"
    assert "curl" not in than.lower(), (
        "cua dang dong ma trang van dua lenh goi chep duoc")
    # Nhưng thứ dùng được NGAY thì vẫn phải còn: mã giọng và tên giọng dựng sẵn
    # đúng dù cửa đóng, và một trang trắng trơn thì không giúp được ai.
    assert "/developers/keys" in than, "mat duong sang khu Lap trinh vien"


# ── Nguồn của mỗi lượt sinh ──────────────────────────────────────────────────

def test_luot_sinh_tu_studio_ghi_nguon():
    """`nguon` phải được ghi NGAY, dù màn Lịch sử chưa lọc theo nó.

    🔴 Đây là thứ **không bù lại được sau**. Thêm bộ lọc thì làm lúc nào cũng
       xong; nhưng một job đã chạy mà không ghi nó đến từ đâu thì mãi mãi không
       biết. Ảnh tham chiếu 05 lọc lịch sử theo Studio · Dự án · Lô · API, và
       khi tới lúc dựng bộ lọc đó, dữ liệu phải đã có sẵn ở đấy rồi.

    Đọc thẳng mã nguồn thay vì chạy một job: rẻ, và nó chốt đúng điều cần chốt —
    rằng khoá đó có mặt tại **cửa nộp**.
    """
    # ⚠️ `routes` nay la mot PACKAGE. `inspect.getsource` chi tra `__init__.py`,
    #    nen phai doc TUNG manh — neu khong, phep kiem xanh vi no khong nhin
    #    thay gi ca, dung loai xanh-gia te nhat.
    import pathlib

    from apps.ltt_voice import routes
    thu_muc = pathlib.Path(routes.__file__).parent
    ma = "\n".join(f.read_text(encoding="utf-8")
                   for f in sorted(thu_muc.glob("*.py")))
    assert '"nguon": "studio"' in ma, (
        "cua nop cua Studio khong ghi `nguon`. Xem VOICE_UI_EXECUTION_PLAN §7.5.")
    assert '"nguon": "giong"' in ma, (
        "cua ghi danh khong ghi `nguon`.")
