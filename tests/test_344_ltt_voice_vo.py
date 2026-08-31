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

#: Sáu tab, đúng thứ tự luồng làm việc. Chốt bằng một danh sách gõ tay chứ không
#: bằng `len(...)`: một phép kiểm đếm số lượng vẫn xanh khi ai đó đổi `Dự án`
#: thành một tab khác, và bài học "chốt TẬP HỢP không chốt số lượng" đã có sẵn
#: trong bộ nhớ dự án.
TAB_MONG_DOI = [
    ("/ltt-voice", vo.NAV_STUDIO, True),
    ("/ltt-voice/giong", vo.NAV_GIONG, True),
    ("/ltt-voice/du-an", vo.NAV_DU_AN, False),
    ("/ltt-voice/lo", vo.NAV_LO, False),
    ("/ltt-voice/lich-su", vo.NAV_LICH_SU, True),
    ("/ltt-voice/api", vo.NAV_API, False),
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


def test_moi_tab_chua_xay_co_noi_dung_trong_CHUA_XAY():
    """`built=False` và `vo.CHUA_XAY` phải là CÙNG một tập.

    Lệch một chiều thì `_trang_chua_xay` ném `KeyError` (tab có, nội dung không);
    lệch chiều kia thì có nội dung mồ côi không ai đọc — thứ sẽ sống mãi vì
    không ai dám xoá.
    """
    tu_manifest = {e.nav_key for e in MANIFEST.nav if not e.built}
    assert tu_manifest == set(vo.CHUA_XAY), (
        f"chi co trong manifest: {tu_manifest - set(vo.CHUA_XAY)}\n"
        f"chi co trong CHUA_XAY: {set(vo.CHUA_XAY) - tu_manifest}")

    for khoa, man in vo.CHUA_XAY.items():
        assert man.get("tieu_de"), f"{khoa} thieu tieu_de"
        assert man.get("mo_ta"), f"{khoa} thieu mo_ta"
        # Một trang "đang xây" không nói được sẽ có gì thì nó chỉ là một 404 lịch sự.
        assert man.get("sap_co"), f"{khoa} khong noi duoc se co gi"


def test_ngu_canh_bat_buoc_nav_key():
    """Không có mặc định cho `nav_key`.

    Có mặc định thì một màn mới quên truyền sẽ **sáng nhầm tab** thay vì báo lỗi
    — và sáng nhầm là loại lỗi không ai đi báo.
    """
    with pytest.raises(TypeError):
        vo.ngu_canh(None, None)  # type: ignore[call-arg]

    d = vo.ngu_canh(None, None, nav_key=vo.NAV_GIONG)
    assert d["nav"] == vo.NAV_GIONG
    # `base.html` đọc đúng khoá tên `nav`. Đổi tên khoá là gãy vỏ.
    assert "nav" in d and "manifest" in d and "hang_doi" in d


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


def test_ba_man_chua_xay_khong_ve_giao_dien_gia(khach):
    """Màn chưa xây phải NÓI sẽ có gì, không MÔ PHỎNG cái sẽ có.

    ⛔ Một màn hình giả trông như đã xong là cách nhanh nhất để một phiên sau
       tưởng nó đã xong. Tài liệu dự án này đã nói sai **về phía nguy hiểm** hai
       lần vì đúng lớp nhầm lẫn đó (hàng Public API và hàng VPS trong
       `CLAUDE.md`).

    Cách chốt: trang phải mang badge "đang xây", và **không** được chứa biểu mẫu
    nào — một `<form>` trên màn chưa xây là một nút bấm không dẫn tới đâu.

    ⚠️ Soi trong PHẦN THÂN của màn, không soi cả tài liệu: vỏ nền tảng có sẵn
       một `<form>` đăng xuất trong menu tài khoản, nên một phép kiểm quét cả
       trang sẽ đỏ vì một thứ hoàn toàn không liên quan. Bản đầu của phép kiểm
       này đúng chỗ đó — và đó là đúng loại tín hiệu sai làm người ta mất tin
       vào bánh cóc.
    """
    for nav_key in vo.CHUA_XAY:
        duong = next(e.path for e in MANIFEST.nav if e.nav_key == nav_key)
        r = khach.get(duong)
        assert r.status_code == 200

        than = re.search(r'<section class="lv-man[^"]*".*?</section>',
                         r.text, re.S)
        assert than, f"{duong} khong co than man `.lv-man`"
        than = than.group(0)

        assert "lv-cx" in than, f"{duong} khong dung template chua xay"
        assert "<form" not in than.lower(), (
            f"{duong} co <form> trong than man — man chua xay khong duoc co "
            f"dieu khien that.")
        # Và phải nói rõ nó chưa xong, không để khách tự đoán.
        assert "b-warn" in than, f"{duong} thieu badge 'dang xay'"


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
    import inspect

    from apps.ltt_voice import routes
    ma = inspect.getsource(routes)
    assert '"nguon": "studio"' in ma, (
        "cua nop cua Studio khong ghi `nguon`. Xem VOICE_UI_EXECUTION_PLAN §7.5.")
    assert '"nguon": "giong"' in ma, (
        "cua ghi danh khong ghi `nguon`.")
