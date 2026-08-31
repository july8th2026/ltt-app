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
    # `routes` la mot PACKAGE tu P5; `_uid` song o manh dung chung.
    from apps.ltt_voice.routes._chung import _uid

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


@pytest.mark.parametrize("duong", ["/ltt-voice", "/ltt-voice/giong"])
def test_moi_form_deu_co_CSRF_TOKEN_KHONG_RONG(khach, duong):
    """🔴 Token rỗng làm chết mọi cửa POST, và nó chết IM LẶNG.

    Mọi template Voice viết `value="{{ csrf_token }}"`. `vo.ngu_canh` — bộ dựng
    ngữ cảnh cho MỌI màn — không hề đặt khoá đó, nên Jinja render **chuỗi rỗng**:
    không cảnh báo, không lỗi. Và `verify_csrf_token` khi ấy cũng đang bị bỏ qua
    kết quả, nên **hai lỗi triệt tiêu nhau** và mọi thứ trông vẫn chạy.

    Vá lỗ CSRF (thi hành thật) gỡ một trong hai, và lỗi còn lại hiện ra ngay:
    mọi form trả 400 *"Phiên đã hết hạn"* — tạo tiếng, tạo giọng, tắt giọng, dự
    án, chạy lô. Đo thật trên production 31/08/2026: form đăng xuất của
    `base.html` có token 43 ký tự, **mọi form của app có `value=""`**.

    ⭐ Bài học không phải "nhớ thêm token". Là: **hai lỗi triệt tiêu nhau thì sửa
       một cái sẽ làm lộ cái kia**, và cái lộ ra trông y hệt một hồi quy do bản
       vá gây ra. Nó không phải — nó là thứ đã hỏng suốt từ đầu.

    ⛔ Và phép kiểm này chốt GIÁ TRỊ, không chốt sự có mặt của trường. Một
       `<input name="csrf_token" value="">` vẫn là một trường có mặt.
    """
    import re

    r = khach.get(duong)
    assert r.status_code == 200, f"{duong} tra {r.status_code}"

    tok = re.findall(r'name="csrf_token"\s+value="([^"]*)"', r.text)
    assert tok, f"{duong} khong co truong csrf_token nao"
    rong = [i for i, t in enumerate(tok) if not t.strip()]
    assert not rong, (
        f"{duong}: {len(rong)}/{len(tok)} truong csrf_token RONG. Moi cua POST "
        f"dung chung se tra 400 'Phien da het han'. Xem `vo.ngu_canh`.")


def test_loi_chao_ban_khong_duoc_noi_mot_con_so_KHAC_hang_so_that():
    """🔴 Thẻ app nói "ba tới TÁM giây" trong khi hệ thống nhận tới BA MƯƠI.

    `audio_input.GIAY_TOI_DA = 30.0`, và cả điều khoản lẫn biểu mẫu đều nói 3–30
    vì chúng **dẫn xuất** từ hằng số đó. Chỉ dòng văn xuôi trong `manifest.py`
    gõ tay, nên chỉ nó trôi — và nó là dòng đứng ở danh mục, tức thứ khách đọc
    **đầu tiên và nhiều nhất**.

    ⛔ Nó trôi về phía tệ nhất. Một lời chào bán nói THẤP hơn sự thật không làm
       khách bỏ đi — nó làm khách **tự tay làm hỏng kết quả của chính họ**:
       người có clip 20 giây sẽ cắt còn 8 trước khi tải lên. Bộ chọn vừa đo
       được là nó dùng đúng phần 13,08–20,80s của một clip 29,58s, nên người đó
       vừa vứt đi đúng phần tốt nhất — và không có gì báo cho họ biết.

    ⭐ Vì sao chốt bằng phép kiểm chứ không bằng "nhớ sửa cả hai chỗ": ba chỗ đã
       lệch nhau suốt và **không chỗ nào sai một mình** — hai chỗ đúng vì chúng
       đọc hằng số, một chỗ sai vì nó chép. Cách sửa bền là bắt chỗ chép phải
       chứng minh nó khớp, chứ không phải thêm một người phải nhớ.
    """
    import re

    from apps.ltt_voice.audio_input import GIAY_TOI_DA, GIAY_TOI_THIEU
    from apps.ltt_voice.manifest import MANIFEST

    # Dài trước ngắn: "ba mươi" phải khớp trước "ba", nếu không "ba mươi giây"
    # đọc thành số 3 và phép kiểm sẽ xanh trên đúng câu sai.
    CHU_SO = {"ba mươi": 30, "hai mươi": 20, "mười lăm": 15, "mười": 10,
              "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6,
              "bảy": 7, "tám": 8, "chín": 9}
    mau = re.compile(r"\d+|" + "|".join(re.escape(k) for k in CHU_SO), re.I)

    # ⛔ CHỈ đọc cụm ĐỨNG NGAY TRƯỚC chữ "giây", không đọc cả câu. Bản đầu quét
    #    cả câu và báo động ngay ở **"một clip"** — trong tiếng Việt "một" là
    #    mạo từ, không phải một phép đo. Đó là lần báo động giả thứ hai trong
    #    cùng một buổi, cùng một cách sửa: thu hẹp LUẬT cho đúng bản chất chứ
    #    đừng nới ngoại lệ cho câu này.
    NOI = {"tới", "đến", "-", "–", "—"}

    def _so_canh_giay(cau: str) -> set:
        thay = set()
        for m in re.finditer(r"giây", cau, re.I):
            tu = re.findall(r"[\w–—-]+", cau[:m.start()], re.UNICODE)
            lui = []
            for t in reversed(tu):
                if t.lower() in NOI or t.lower() in CHU_SO or t.isdigit()                         or t.lower() == "mươi":
                    lui.append(t)
                else:
                    break
            cum = " ".join(reversed(lui))
            thay |= {int(x) if (x := k.strip()).isdigit() else CHU_SO[x.lower()]
                     for k in mau.findall(cum)}
        return thay

    # ⛔ CHỈ soi `summary`, có chủ ý. Quét mọi chuỗi trong `manifest.py` có chữ
    #    "giây" sẽ bắt cả trần thời gian chạy, hạn lưu tệp, thời hạn lease — toàn
    #    số hợp lệ — và một phép kiểm báo động giả thì bị tắt trong một tuần,
    #    kéo theo cả trường hợp thật. `summary` là dòng khách đọc ở danh mục;
    #    đó là chỗ một con số sai gây hại, và là chỗ hẹp đủ để chốt.
    cho_phep = {int(GIAY_TOI_THIEU), int(GIAY_TOI_DA)}
    cau = str(MANIFEST.summary)
    thay = _so_canh_giay(cau)
    assert thay, f"summary khong noi mot moc giay nao: {cau!r}"
    thua = thay - cho_phep
    assert not thua, (
        f"MANIFEST.summary noi so {sorted(thua)} — hang so that la "
        f"{sorted(cho_phep)} ({GIAY_TOI_THIEU}–{GIAY_TOI_DA} giay). "
        f"Cau: {cau!r}")
