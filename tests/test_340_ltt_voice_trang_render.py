"""Ba trang của LTT VOICE phải RENDER được, không chỉ tồn tại.

## Vì sao tệp này tồn tại

Ngày 31/08/2026, app đã có 42 phép kiểm hợp đồng + 27 phép kiểm giá, tất cả
xanh, và bộ test đầy đủ xanh. Rồi mở trình duyệt lần đầu:

    GET /ltt-voice  ->  422   {"loc":["query","request"],"msg":"Field required"}
    (sửa xong)      ->  500   TypeError: unhashable type: 'dict'

**Hai lỗi liên tiếp, và cả hai đều nghĩa là trang chưa render nổi một lần nào.**
Lỗi thứ nhất là `Depends(user_hien_tai)` thiếu chú kiểu; lỗi thứ hai là gọi
`TemplateResponse(name, context)` trong khi Starlette ở đây nhận
`TemplateResponse(request, name, context)`.

⭐ Điều đáng học không phải "thiếu test", mà là **loại test đã có không thể bắt
   được loại lỗi này**: mọi phép kiểm cũ đọc manifest, gọi thẳng hàm, đối chiếu
   bảng giá — không cái nào đi qua router và qua Jinja. Đó chính là điều
   `CLAUDE.md` quy tắc 5 nói: test xanh không chứng minh trang hiển thị được.

Nên phép kiểm ở đây cố tình đi **đường dài nhất còn chạy được trong test**:
dựng app thật, đăng nhập thật, GET thật, và đòi 200 + một mẩu nội dung.
"""
from __future__ import annotations

import re

import pytest

#: (đường, một mẩu chữ PHẢI có trong trang). Mẩu chữ giữ cho phép kiểm không
#: hài lòng với một trang lỗi được render với mã 200.
#:
#: ⚠️ Neo bằng `id=` của chính template, KHÔNG bằng chữ hiển thị: chữ hiển thị
#:    đi qua `_()` nên nó đổi theo ngôn ngữ, và một phép kiểm neo vào bản dịch
#:    sẽ đỏ vào ngày ai đó đổi một câu — một tín hiệu sai, đúng loại làm người
#:    ta mất tin vào bánh cóc.
TRANG = [
    ("/ltt-voice", 'id="lv-form"'),
    ("/ltt-voice/giong", 'id="lv-form-giong"'),
    ("/ltt-voice/lich-su", "/ltt-voice"),
]


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một tài khoản đã đăng nhập, trên CSDL sqlite dùng một lần."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-ui.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-ui")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    # ⚠️ `create_all` chỉ dựng bảng của model ĐÃ import. Bảng riêng của app nằm
    #    ở `apps/ltt_voice/tables.py`; quên dòng này thì `/ltt-voice` ném
    #    `no such table: voice_profile` — và vì lớp xử lý lỗi bọc nó lại, phép
    #    kiểm nhận **200 kèm một trang lỗi**, tức xanh nhầm. Chính vì thế phần
    #    khẳng định dưới đòi cả mã 200 LẪN một mẩu nội dung thật.
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="voice-ui@test.com",
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
    r = client.post("/login", data={"username": "voice-ui@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303), f"dang nhap that bai: {r.status_code}"
    try:
        yield client
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


@pytest.mark.parametrize("duong,phai_co", TRANG)
def test_trang_render_duoc(khach, duong, phai_co):
    r = khach.get(duong)
    assert r.status_code == 200, (
        f"{duong} tra {r.status_code}, khong phai 200.\n"
        f"{r.text[:400]}\n\n"
        "422 -> mot ham dung qua `Depends` thieu chu kieu (xem server/deps.py).\n"
        "500 -> xem log; da tung la `TemplateResponse(name, ctx)` trong khi "
        "Starlette o day nhan `TemplateResponse(request, name, ctx)`.")
    assert phai_co in r.text, (
        f"{duong} tra 200 nhung khong chua {phai_co!r} — nhieu kha nang la mot "
        f"trang loi duoc render voi ma 200, chu khong phai trang that.")


def test_uid_tra_ve_uuid_chu_khong_phai_so_khong():
    """🔴 `_uid` phải trả đúng id của người dùng, không phải `0`.

    `User.id` là UUID chuỗi. Bản đầu của `_uid` ép `int(...)` rồi bắt lỗi trả
    `0` — hợp lệ về kiểu, sai về nghĩa, và **không có triệu chứng nào ở nơi
    xảy ra**. Nó chỉ hiện ra ở hai chỗ xa đó:

      · sổ tiền: header hiện `56 credit` (đọc phiên) còn nút Tạo trả
        `Khong du credit: can 2, con 0` (tra sổ của người dùng `"0"`);
      · quyền riêng tư: mọi `owner_id` bằng 0 ⇒ mọi khách chung một chủ sở hữu.

    Phép kiểm nhỏ, nhưng nó chốt đúng cái mắt xích đã đứt.
    """
    from apps.ltt_voice.routes import _uid

    class GiaUser:
        id = "3f2a9c10-5b7e-4d21-8a6f-11223344abcd"

    assert _uid(GiaUser()) == GiaUser.id
    assert _uid(None) == ""


def test_nut_tao_khong_bao_het_credit_khi_tai_khoan_co_credit(khach):
    """Bấm Tạo với tài khoản CÓ credit thì không được trả 'con 0'.

    Đây là phép kiểm đi qua đúng đường mà trình duyệt đi: POST form thật, kèm
    CSRF thật. Nó đỏ khi `_uid` trả sai, kể cả khi trang vẫn render 200.
    """
    import re

    from platform_core import credit, users
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, "voice-ui@test.com")
        credit.nap(db, u.id, 50, note="test_340")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    trang = khach.get("/ltt-voice")
    m = re.search(r'name="csrf_token" value="([^"]+)"', trang.text)
    assert m, "khong thay csrf_token tren trang tao"

    r = khach.post("/ltt-voice/tao",
                   data={"text": "Xin chao, day la mot cau thu.",
                         "voice_id": "", "preset": "",
                         "csrf_token": m.group(1)})
    than = r.text
    assert "con 0" not in than, (
        f"handler tra ve 'con 0' du tai khoan da co credit — gan nhu chac chan "
        f"`_uid` tra ve '0'/'' thay vi UUID that.\n{than[:300]}")


def test_khong_dung_duoc_giong_cua_khach_khac(khach, tmp_path):
    """🔴 Gửi `voice_id` của người khác phải bị chặn NGAY TẠI CỬA, 400.

    ĐO THẬT 31/08/2026 trên production: tài khoản B gửi `voice_id` của tài
    khoản A và nhận **HTTP 200 kèm job_id**. Giọng không bị dùng — worker chặn
    đúng — nhưng job vẫn giữ credit, vẫn xếp hàng, và bị thử lại **ba lần**
    trước khi báo lỗi. 31 giây để nghe một câu mà cửa vào trả lời được ngay.

    ⭐ Phép kiểm cũng chốt **thông điệp**: một câu duy nhất cho cả "không tồn
       tại" lẫn "không phải của bạn". Phân biệt hai câu đó là biến cửa này
       thành máy dò `voice_id` nào có thật.
    """
    import re

    from platform_core import credit, users
    from platform_core.db import get_session

    from apps.ltt_voice.tables import VoiceProfile

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, "voice-ui@test.com")
        credit.nap(db, u.id, 50, note="test_340 cach ly")
        # Giọng của NGƯỜI KHÁC.
        # `id` gán tay: SQLite chỉ tự tăng cho `INTEGER PRIMARY KEY` (bí danh
        # rowid), không cho `BigInteger`. Production là PostgreSQL nên cột này
        # tự tăng thật — khác biệt của môi trường test, không phải của sản phẩm.
        nguoi_khac = VoiceProfile(id=9_000_001, owner_id="nguoi-khac-0000",
                                  ten_hien_thi="Giong cua nguoi khac",
                                  trang_thai="active")
        db.add(nguoi_khac)
        db.commit()
        vid = nguoi_khac.public_id
        truoc = credit.so_du(db, u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    trang = khach.get("/ltt-voice")
    m = re.search(r'name="csrf_token" value="([^"]+)"', trang.text)
    r = khach.post("/ltt-voice/tao",
                   data={"text": "Thu dung giong cua nguoi khac.",
                         "voice_id": vid, "preset": "",
                         "csrf_token": m.group(1)})

    assert r.status_code == 400, (
        f"gui voice_id cua nguoi khac ma duoc {r.status_code}: {r.text[:200]}\n"
        "Cua vao phai tu choi ngay, khong duoc giu credit roi de worker phat "
        "hien sau ba lan thu.")
    assert "job_id" not in r.text, "khong duoc tao job cho mot yeu cau da biet la sai"

    gen = get_session()
    db = next(gen)
    try:
        assert credit.so_du(db, u.id) == truoc, (
            "so du doi sau mot yeu cau bi tu choi — dang giu credit cho viec "
            "khong bao gio chay")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_loi_giong_noi_la_loi_nguoi_goi_nen_khong_bi_thu_lai():
    """🔴 Lỗi của người gọi không được thử lại ba lần.

    Trước 31/08/2026 nền tảng quyết định thử-lại **hoàn toàn** từ một danh sách
    gõ tay các ngoại lệ của provider LLM; mọi thứ khác rơi vào nhánh mặc định
    `"retry"`. Một handler ném "giọng này không phải của bạn" tiêu ba suất GPU.
    """
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.jobs import LoiNguoiGoi

    from apps.ltt_voice.features import DangBanTam, LoiGiongNoi

    assert issubclass(LoiGiongNoi, LoiNguoiGoi)
    kind, _ = _provider_failure_kind(LoiGiongNoi("x"), provider_state="")
    assert kind == "loi_nguoi_goi", f"phan loai ra {kind!r}, khong duoc thu lai"

    # ⛔ Va chieu nguoc lai: MAY BAN phai duoc thu lai. Danh dau no la loi nguoi
    #    goi se bien mot truc trac thoang qua thanh that bai vinh vien.
    assert not issubclass(DangBanTam, LoiNguoiGoi), (
        "`DangBanTam` la 'may dang ban' — no PHAI duoc xep lai, khong duoc coi "
        "la loi cua khach")
