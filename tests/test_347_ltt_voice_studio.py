"""Hai cửa mới của màn Studio: xem trước cách đọc, và theo dõi kết quả tại chỗ.

## Vì sao hai cửa này tồn tại

**`POST /xem-truoc`** — `manifest._gia()` đếm ký tự **sau** khi chuẩn hoá, nên số
ký tự bị tính tiền không phải số ký tự khách gõ. Trước cửa này khách không có
cách nào thấy điều đó trước khi bấm; họ chỉ gặp nó dưới dạng một hoá đơn không
giải thích được.

**`GET /ket-qua/{job_id}`** — `job_history.customer_payload` cố tình **không**
trả `result` lẫn `error`: nó là gói dùng chung cho mọi app, mà `result` thì mỗi
app một hình dạng. Studio cần đúng ba thứ trong đó (khoá tệp, thời lượng,
credit), nên app tự mở một cửa hẹp thay vì nới cửa chung.

## Điều được chốt chặt nhất ở đây

⛔ **`/ket-qua/` không được trả `job.error` thô.** `job_events.public_message` là
   câu đã duyệt để hiện cho chủ job; `job.error` là chuỗi ngoại lệ và có thể mang
   chi tiết nội bộ. Hai thứ đó khác nhau, và chỉ có một cái được ra ngoài.

⛔ **Quyền đọc lọc trong chính câu truy vấn** (`job_history.get_owned`), không
   phải tra job rồi so chủ ở bước sau — giữa hai bước đó có một khoảng trống mà
   một bản vá sau này rất dễ quên.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-st.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-studio")
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
        u = tao_nguoi_dung(db, email="voice-st@test.com",
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
    r = client.post("/login", data={"username": "voice-st@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    """Token lấy từ ĐÚNG form của app, không phải form đầu tiên trên trang.

    🔴 BẢN ĐẦU CỦA HÀM NÀY LẤY BẰNG CHỨNG TỪ SAI CHỖ, và nó che một P0 sống
       trên production nhiều ngày.

       Nó viết `re.search(r'name="csrf_token" value="([^"]+)"', r.text)`. Mẫu
       `([^"]+)` đòi ít nhất một ký tự, nên một token **rỗng** sẽ không khớp và
       `assert` sẽ nổ — nghe như một phép kiểm chặt. Nhưng `re.search` lấy khớp
       **ĐẦU TIÊN** trong trang, và khớp đầu tiên là form đăng xuất của
       `base.html` — thứ **nền tảng** tự đặt, luôn có giá trị.

       Trong khi đó `vo.ngu_canh()` chưa bao giờ đặt khoá `csrf_token`, nên mọi
       form của CHÍNH app render `value=""`. Hai form dùng chung một token phiên,
       nên POST trong test vẫn 200 — còn khách thật bấm nút thì nhận
       `400 Phiên đã hết hạn`. Sinh tiếng, tạo giọng, tắt giọng đều chết.

    ⇒ Bài học không phải "quên kiểm CSRF". Là: **một phép kiểm đọc dữ liệu từ
      một chỗ khác với chỗ nó đang nói về, thì nó không nói về chỗ đó.**
    """
    r = client.get("/ltt-voice")
    m = re.search(r'<form[^>]*id="lv-form"[\s\S]*?name="csrf_token" value="([^"]*)"',
                  r.text)
    assert m, "khong tim thay form `lv-form` cua Studio"
    token = m.group(1)
    assert token, (
        "form cua app render csrf_token RONG — `vo.ngu_canh()` khong dat khoa do")
    return token


def _tao_job(uid: str, *, status: str, result=None, error: str = "") -> str:
    """Đặt thẳng một job vào CSDL. Nhanh hơn, và không cần worker."""
    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        job = Job(user_id=uid, app_slug="ltt_voice",
                  job_type="ltt_voice.synthesize",
                  params={"text": "xin chao"}, status=status,
                  result=result or {}, error=error, progress=100)
        db.add(job)
        db.commit()
        return str(job.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Xem trước cách đọc ───────────────────────────────────────────────────────

def test_xem_truoc_hien_dung_thu_may_se_doc(khach):
    """Ký hiệu phải được nở ra thành chữ — đó là toàn bộ điểm của ô này."""
    client, _uid = khach
    r = client.post("/ltt-voice/xem-truoc",
                    data={"text": "Tang 15% so voi thang truoc.",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert "phần trăm" in d["da_chuan_hoa"], (
        f"'%' khong duoc no ra: {d['da_chuan_hoa']!r}")
    assert d["doi_khac"] is True


def test_xem_truoc_bao_dung_khi_khong_co_gi_de_doi(khach):
    """Văn bản thuần chữ thì `doi_khac` phải là False.

    ⭐ Nói "không có gì phải chuẩn hoá" là một câu trả lời **có ích**. Hiện một
       ô xem trước giống hệt ô nhập mà không giải thích thì người dùng sẽ tưởng
       tính năng hỏng.
    """
    client, _uid = khach
    r = client.post("/ltt-voice/xem-truoc",
                    data={"text": "Xin chao cac ban",
                          "csrf_token": _csrf(client)})
    d = r.json()
    assert d["ok"] is True and d["doi_khac"] is False


def test_uoc_credit_den_tu_CHINH_ham_ra_hoa_don(khach):
    """🔴 Con số hiện ra phải là con số sẽ bị tạm giữ, không phải ước lượng thứ hai.

    Hai chỗ tính tiền là hai chỗ sẽ lệch nhau. Ở đây `/xem-truoc` và
    `manifest.credit_cost` phải cho **cùng** một số cho **cùng** một văn bản.
    """
    from apps.ltt_voice.manifest import MANIFEST

    client, _uid = khach
    van_ban = "Doanh thu thang nay tang 15% so voi thang truoc."
    d = client.post("/ltt-voice/xem-truoc",
                    data={"text": van_ban, "csrf_token": _csrf(client)}).json()
    assert d["uoc_credit"] == MANIFEST.credit_cost({"text": van_ban}), (
        "so credit o o xem truoc LECH khoi so ma cua nop se giu")


def test_xem_truoc_tu_choi_van_ban_rong(khach):
    client, _uid = khach
    r = client.post("/ltt-voice/xem-truoc",
                    data={"text": "   ", "csrf_token": _csrf(client)})
    assert r.status_code == 400


def test_xem_truoc_doi_csrf(khach):
    """Cửa POST nào cũng phải qua CSRF, kể cả cửa chỉ tính toán."""
    client, _uid = khach
    r = client.post("/ltt-voice/xem-truoc",
                    data={"text": "xin chao", "csrf_token": "sai-bet"})
    assert r.status_code >= 400


# ── Theo dõi kết quả ─────────────────────────────────────────────────────────

def test_ket_qua_khi_xong_tra_du_thu_studio_can(khach):
    client, uid = khach
    jid = _tao_job(uid, status="done", result={
        "audio_key": f"voice/out/{uid}/job/tieng.wav",
        "duration_s": 4.25, "credit_cost": 2, "so_doan": 1})

    d = client.get(f"/ltt-voice/ket-qua/{jid}").json()
    assert d["trang_thai"] == "done"
    assert d["giay"] == 4.25
    assert d["credit"] == 2
    # URL phát phải đi qua cửa `/audio/` của app, không lộ khoá kho trần.
    assert d["audio_url"].startswith("/ltt-voice/audio/")


def test_ket_qua_khi_dang_chay_khong_tra_tep(khach):
    client, uid = khach
    jid = _tao_job(uid, status="running")
    d = client.get(f"/ltt-voice/ket-qua/{jid}").json()
    assert d["trang_thai"] == "running"
    assert d["audio_url"] == ""


def test_ket_qua_KHONG_TRA_error_tho(khach):
    """🔴 Phép kiểm quan trọng nhất tệp này.

    `job.error` là chuỗi ngoại lệ thô. Nó có thể mang đường dẫn nội bộ, tên host,
    hay một mẩu payload. Cửa này chỉ được trả câu đã duyệt (`public_message`) —
    và khi không có câu nào, một câu chung chung, **không phải** chuỗi thô.
    """
    client, uid = khach
    bi_mat = "Traceback: C:/LTTPlatform/secrets/app.env line 42 token=abc123"
    jid = _tao_job(uid, status="error", error=bi_mat)

    r = client.get(f"/ltt-voice/ket-qua/{jid}")
    d = r.json()
    assert d["trang_thai"] == "error"
    assert "loi" in d and d["loi"], "job hong ma khong noi duoc gi cho khach"
    assert "secrets" not in r.text and "abc123" not in r.text, (
        "CHUOI LOI THO RO RA NGOAI:\n" + r.text[:400])


def test_ket_qua_cua_nguoi_khac_tra_404(khach):
    """Quyền lọc trong chính câu truy vấn, không so chủ ở bước sau."""
    client, _uid = khach
    jid = _tao_job("00000000-0000-0000-0000-000000000000", status="done",
                   result={"audio_key": "voice/out/x/job/tieng.wav"})
    assert client.get(f"/ltt-voice/ket-qua/{jid}").status_code == 404


def test_ket_qua_job_khong_ton_tai_tra_404(khach):
    client, _uid = khach
    assert client.get("/ltt-voice/ket-qua/khong-co-that").status_code == 404


# ── Màn Studio dựng đủ thứ nó hứa ────────────────────────────────────────────

def test_studio_liet_ke_du_hai_muoi_giong_mau(khach):
    """Màn Giọng có nút "Dùng" trỏ sang đây. Một nút dẫn tới một ô chọn thiếu
    mục đó là một ngõ cụt tệ hơn không có nút."""
    from apps.ltt_voice import giong_mau

    client, _uid = khach
    html = client.get("/ltt-voice").text
    thieu = [g.ma for g in giong_mau.DANH_SACH
             if f'value="m:{g.ma}"' not in html]
    assert not thieu, f"bo chon giong thieu: {thieu}"


def test_studio_chon_san_giong_tu_tham_so(khach):
    client, _uid = khach
    html = client.get("/ltt-voice", params={"giong": "Adam"}).text
    assert re.search(r'value="m:Adam"[^>]*\schecked', html), (
        "?giong=Adam khong duoc chon san")


def test_studio_bo_qua_giong_bia(khach):
    """Tham số là chuỗi khách gửi ⇒ không tin. Giá trị lạ thì im lặng bỏ qua."""
    client, _uid = khach
    html = client.get("/ltt-voice", params={"giong": "KHONG-CO-THAT"}).text
    assert 'value=""  checked' in html or re.search(
        r'value=""[^>]*\schecked', html), "khong roi ve giong mac dinh"
    assert "KHONG-CO-THAT" not in html, "gia tri la duoc doi lai ra HTML"


def test_studio_KHONG_ve_dieu_khien_bi_cam(khach):
    """⛔ Năm tham số LẤY MẪU của Q119 không được lên giao diện.

    Và `MODE Fast/Quality` cùng `LANGUAGE VI/EN` thì backend không có, nên vẽ
    chúng là hứa một thứ không tồn tại.

    🔴 BẢN ĐẦU CỦA PHÉP KIỂM NÀY CẤM CẢ `name="toc_do"`, VÀ ĐÓ LÀ MỘT LỖI.

       Nó chép lại cùng một trích dẫn sai với chú thích trong
       `ltt_voice_studio.html`: Q119 ① nêu ĐÍCH DANH năm tham số —
       `temperature`, `top_k`, `top_p`, `repetition_penalty`,
       `repetition_window` — và **không có "tốc độ"**. Cả hai lý do của Q119
       cũng chỉ nói về đường lấy mẫu: cache CUDA graph khoá theo
       `(B, temperature, top_k, top_p)`, và tông lệch do `temperature` (#173).

    ⭐ Tốc độ trong sản phẩm là **time-stretch hậu kỳ** trên tệp đã sinh xong
       (`apps/ltt_voice/toc_do.py`) — nó không chạm một tham số nào trong năm
       cái ấy, không chạm GPU, và chạy SAU cả cổng chất lượng.

    ⚠️ Bài học đắt hơn bản sửa: **một trích dẫn sai được chốt bằng một phép
       kiểm sẽ sống lâu hơn một trích dẫn sai nằm trong chú thích** — vì từ đó
       trở đi, sửa nó làm gate đỏ, và gate đỏ trông y như một lỗi. Nên phép
       kiểm này nay chốt CẢ HAI CHIỀU: năm tham số kia phải vắng mặt, và tốc độ
       phải CÓ MẶT.
    """
    client, _uid = khach
    html = client.get("/ltt-voice").text.lower()
    for cam in ("temperature", "top_k", "top_p",
                "repetition_penalty", "repetition_window",
                'name="mode"', 'name="language"'):
        assert cam not in html, f"dieu khien bi cam lo ra giao dien: {cam!r}"
    assert 'name="toc_do"' in html, (
        "toc do PHAI co tren giao dien — no la hau ky, khong thuoc nam tham so "
        "lay mau ma Q119 khoa. Doc docstring phep kiem nay truoc khi go no.")


def test_studio_toc_do_la_THANH_KEO_theo_hang_so_chung_voi_API(khach):
    """16/09/2026 (chủ dự án): thanh kéo bước 0,05 thay 6 nút rời.

    ⛔ min/max PHẢI là `toc_do.TOC_DO_MIN/MAX` — cùng số ToolSpec API khai cho
       `speed`. Một khoảng gõ tay trong template là hai nguồn lệch nhau."""
    import re

    from apps.ltt_voice import toc_do
    client, _uid = khach
    html = client.get("/ltt-voice").text
    m = re.search(r'<input type="range" name="toc_do" id="lv-toc-do"\s+'
                  r'min="([^"]+)" max="([^"]+)"\s+step="([^"]+)"', html)
    assert m, "khong thay thanh keo toc do"
    assert (float(m.group(1)), float(m.group(2)), float(m.group(3))) == (
        toc_do.TOC_DO_MIN, toc_do.TOC_DO_MAX, toc_do.TOC_DO_BUOC)
    assert "data-tocdo=" not in html, "nut toc do roi cu phai go"
    for moc in toc_do.MOC_THANH_KEO:
        assert f'<option value="{moc}"' in html


# ── CSRF: bánh cóc cho một lỗ đã sống từ ngày phát hành ──────────────────────

#: MỌI cửa POST của app, kèm dữ liệu tối thiểu để nó đi tới bước kiểm CSRF.
#:
#: 🔴 Chốt theo DANH SÁCH ĐẦY ĐỦ chứ không theo cửa vừa bắt được. Lỗ này không
#:    phải một chỗ quên — nó là **cùng một dòng sai chép ra bốn chỗ**, nên phép
#:    kiểm phải phủ cả bốn. Thêm cửa POST thứ năm mà quên CSRF thì
#:    `test_moi_cua_post_deu_doi_csrf` vẫn xanh (nó chỉ biết những gì được liệt
#:    kê) — nên có thêm `test_khong_cua_nao_bo_qua_ket_qua_verify` quét mã nguồn.
CUA_POST = [
    ("/ltt-voice/tao", {"text": "xin chao"}),
    ("/ltt-voice/xem-truoc", {"text": "xin chao"}),
    ("/ltt-voice/giong/vc_khongcothat/tat", {}),
]


@pytest.mark.parametrize("duong,du_lieu", CUA_POST)
def test_moi_cua_post_deu_doi_csrf(khach, duong, du_lieu):
    """Token sai ⇒ phải bị từ chối, không được làm việc rồi trả 200.

    Ba cửa này đều có hậu quả: tiêu credit · tính toán · vô hiệu hoá giọng.
    """
    client, _uid = khach
    r = client.post(duong, data=dict(du_lieu, csrf_token="sai-bet"))
    assert r.status_code >= 400, (
        f"{duong} nhan token CSRF SAI ma van tra {r.status_code}")


def test_khong_cua_nao_bo_qua_ket_qua_verify():
    """🔴 Quét mã nguồn, vì phép kiểm theo danh sách không thấy cửa MỚI.

    `verify_csrf_token` **trả `bool`**, nó không ném. Gọi nó rồi vứt kết quả đi
    là một dòng **trông đúng** — và đó chính xác là cách lỗ này sống sót từ ngày
    phát hành qua 69 phép kiểm.

    Luật: giá trị trả về phải được **dùng**, tức lời gọi không được đứng một
    mình như một câu lệnh.

    ⚠️ Đọc bằng AST chứ không quét từng dòng. Bản đầu quét dòng và tự bắt chính
       **docstring** của mình — vì docstring có in ra dòng sai làm ví dụ. Một
       bánh cóc báo động vì văn xuôi là một bánh cóc sẽ bị tắt đi. AST chỉ nhìn
       thấy mã thật: chuỗi và chú thích vô hình với nó.
    """
    import ast
    import pathlib

    from apps.ltt_voice import routes

    # ⚠️ `routes` la mot PACKAGE. Quet TUNG manh: `inspect.getsource` chi cho
    #    `__init__.py`, va mot may quet khong nhin thay gi thi luon xanh.
    thu_muc = pathlib.Path(routes.__file__).parent
    nut_all = []
    for f in sorted(thu_muc.glob("*.py")):
        nut_all.extend(ast.walk(ast.parse(f.read_text(encoding="utf-8"))))

    xau = []
    for nut in nut_all:
        # `ast.Expr` = một biểu thức đứng riêng làm câu lệnh, tức giá trị của nó
        # bị vứt đi. Đó chính xác là hình dạng của lỗi.
        if not isinstance(nut, ast.Expr) or not isinstance(nut.value, ast.Call):
            continue
        ham = nut.value.func
        ten = getattr(ham, "id", None) or getattr(ham, "attr", None)
        if ten == "verify_csrf_token":
            xau.append(f"  dong {nut.lineno}")

    assert not xau, (
        "Co loi goi `verify_csrf_token` dung MOT MINH, tuc ket qua bi vut di:\n"
        + "\n".join(xau)
        + "\n\nHam nay tra `bool`, no KHONG nem. Viet:\n"
          "    if not verify_csrf_token(request, csrf_token):\n"
          "        return _het_phien()")
