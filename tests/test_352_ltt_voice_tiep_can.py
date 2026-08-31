"""Ba chốt tiếp cận của LTT Voice: trạng thái lọc, tiến độ nói ra, cỡ vùng chạm.

## Vì sao ba thứ này được chốt bằng test chứ không bằng một lần rà soát

Cả ba đều **vô hình với con mắt đang nhìn màn hình đúng**. Bộ lọc trông rõ ràng
vì nút đang bật có màu; tiến độ trông rõ ràng vì con số nhảy; nút bấm trông vừa
tay vì chuột chính xác hơn ngón tay. Không thứ nào trong ba thứ đó sẽ gây ra một
báo lỗi, một dòng log, hay một ảnh chụp trông sai — nên nếu chúng hỏng lại thì
chúng hỏng **im lặng**, và chỉ người dùng trình đọc màn hình biết.

## Từng chốt

**1. `aria-pressed` phải theo lớp `on`.** Lớp CSS `on` là thứ con mắt thấy;
`aria-pressed` là thứ tai nghe. Trước P7 chỉ có cái đầu, ở **bốn** nhóm lọc trên
ba màn — nên trình đọc màn hình đọc bốn nút giống hệt nhau và không nút nào tự
xưng là đang bật. Test này soi **văn bản HTML máy chủ trả về**, tức trạng thái
lúc trang vừa mở; phần đồng bộ khi bấm nằm ở `voice.js::batNut` và đã đo trên
trình duyệt thật.

⛔ **Lọc ở màn Lịch sử dùng `aria-current`, KHÔNG dùng `aria-pressed`.** Chúng là
`<button type="submit">` trong một form GET — bấm là **tải lại trang**, không
phải bật/tắt một công tắc. `aria-pressed` mô tả một nút đang bị nhấn giữ;
`aria-current` mô tả "mục hiện hành trong một tập". Ở đây nghĩa thứ hai mới đúng.

**2. Hai màn chi tiết phải có vùng `role="status"`.** Studio có từ đầu, Dự án và
Chạy lô thì không — và đó là khác biệt DUY NHẤT giữa chúng, nên nó là thiếu sót
chứ không phải lựa chọn. Không có vùng ấy thì tiến độ chỉ tồn tại bằng mắt.

⛔ Vùng ấy phải là `sr-only`, **không phải `hidden`**. Phần tử `hidden` bị gỡ
   khỏi cây tiếp cận, nên trình đọc màn hình cũng không đọc — đúng cái bẫy khiến
   một vùng aria-live trông như đã làm mà thật ra câm.

**3. Cỡ vùng chạm ≥ 24px.** `.lv-chon-them` cao 15px và link quay lại cao 17px.
Cả hai gần như chắc chắn lọt **ngoại lệ khoảng cách** của WCAG 2.5.8 (chúng đứng
một mình), nên đây không phải một vi phạm đã chứng minh — nhưng 15px vẫn là thứ
khó bấm trên điện thoại, và `min-height` không tốn gì. Test giữ con số đó khỏi
tụt lại.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
MAU = GOC / "apps" / "ltt_voice" / "templates"
CSS = GOC / "server" / "static" / "ltt.css"
JS = GOC / "server" / "static" / "voice.js"


# ── 1. aria-pressed trong khuôn mẫu ──────────────────────────────────────────

@pytest.mark.parametrize("ten", ["_voice_chon.html", "ltt_voice_giong.html",
                                 ])
def test_moi_nut_loc_deu_khai_aria_pressed(ten):
    s = (MAU / ten).read_text(encoding="utf-8")
    for the in re.findall(r"<button[^>]*lv-loc-nut[^>]*>", s):
        assert "aria-pressed=" in the, f"{ten}: nut loc thieu aria-pressed -> {the}"


@pytest.mark.parametrize("ten", ["_voice_chon.html", "ltt_voice_giong.html",
                                 ])
def test_nut_dang_bat_khai_pressed_true(ten):
    """Lớp `on` và `aria-pressed="true"` phải đi cùng nhau, không lệch."""
    s = (MAU / ten).read_text(encoding="utf-8")
    for the in re.findall(r"<button[^>]*lv-loc-nut[^>]*>", s):
        co_on = 'lv-loc-nut on"' in the
        pressed_true = 'aria-pressed="true"' in the
        assert co_on == pressed_true, f"{ten}: lop `on` va aria-pressed lech -> {the}"


def test_lich_su_dung_aria_current_chu_khong_phai_pressed():
    s = (MAU / "ltt_voice_lich_su.html").read_text(encoding="utf-8")
    assert 'aria-current="true"' in s
    assert "aria-pressed" not in s, (
        "loc o Lich su lam TAI LAI TRANG, khong phai bat/tat mot cong tac")


# ── 2. Vùng báo tin ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("ten", ["ltt_voice_mot_du_an.html"])
def test_man_chi_tiet_co_vung_bao_tin(ten):
    s = (MAU / ten).read_text(encoding="utf-8")
    m = re.search(r'<p[^>]*id="lv-bao"[^>]*>', s)
    assert m, f"{ten}: thieu vung bao tin #lv-bao"
    the = m.group(0)
    assert 'role="status"' in the and 'aria-live="polite"' in the
    assert "sr-only" in the, "phai la sr-only"
    assert "hidden" not in the, (
        "`hidden` go phan tu khoi cay tiep can — vung live se CAM")


@pytest.mark.parametrize("ten,khoa", [("ltt_voice_mot_du_an.html", "khối"),
                                      ])
def test_cau_bao_tin_duoc_dich_va_co_cho_dien_so(ten, khoa):
    s = (MAU / ten).read_text(encoding="utf-8")
    for ten_khoa in ("baoTienDo", "baoXong"):
        m = re.search(ten_khoa + r":\s*\{\{ _\((.+?)\) \| tojson \}\}", s)
        assert m, f"{ten}: {ten_khoa} phai di qua _() de dich duoc"
    assert "{x}" in s and "{y}" in s, f"{ten}: cau bao tin phai co cho dien so"


def test_voice_js_khong_dat_aria_live_len_luoi_con_so():
    """Đặt live lên lưới số thì trình đọc màn hình đọc lại cả bốn ô mỗi vài giây."""
    for ten in ("ltt_voice_mot_du_an.html",):
        s = (MAU / ten).read_text(encoding="utf-8")
        for the in re.findall(r"<div[^>]*aria-live[^>]*>", s):
            assert "lv-mlo-so" not in the and "lv-mda-so" not in the


def test_bao_tin_bo_qua_cau_trung():
    """Ghi lại cùng một câu sẽ khiến trình đọc màn hình đọc lại — phải chặn."""
    s = JS.read_text(encoding="utf-8")
    m = re.search(r"function baoTin\(cau\) \{(.+?)\n  \}", s, re.S)
    assert m, "khong tim thay baoTin()"
    assert "o.textContent === cau" in m.group(1)


def test_chi_mot_ham_bat_nut_cho_ca_ba_man():
    """Ba vòng lặp riêng làm cùng một việc là ba chỗ để quên đồng bộ."""
    s = JS.read_text(encoding="utf-8")
    assert s.count("function batNut(") == 1
    assert s.count("batNut(nut);") == 3, (
        "ca ba nhom loc chay o trinh duyet phai di qua batNut()")
    assert 'setAttribute("aria-pressed"' in s


# ── 3. Cỡ vùng chạm ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("chon", [".lv-chon-them{", ".lv-mda-quay a{"])
def test_vung_cham_khai_min_height_24px(chon):
    s = CSS.read_text(encoding="utf-8")
    i = s.find(chon)
    assert i >= 0, f"khong tim thay luat {chon}"
    luat = s[i:s.find("}", i)]
    assert "min-height:24px" in luat, f"{chon}: thieu min-height:24px -> {luat}"
    assert "inline-flex" in luat, (
        "min-height khong an voi phan tu inline — phai la inline-flex")


# ── 4. Đường nghe phải biết tệp còn hay đã hết hạn ───────────────────────────
#
# 🔴 Đây KHÔNG phải một chốt tiếp cận — nó lọt vào đây vì được tìm ra trong cùng
#    lượt rà soát P7, khi `test_211` bắt hai bảng chưa khai hạn giữ. Khai xong
#    thì lộ ra hệ quả: `voice_block.audio_key` sống mãi cùng dự án, còn tệp nó
#    trỏ tới sống theo hạn 30 ngày của `jobs`.
#
# ⛔ Vì sao nó là lỗi thật chứ không phải chuyện xa: nó KHÔNG hỏng lúc xoá tệp.
#    Nó hỏng lúc khách mở lại dự án cũ, thấy một trình phát trông bình thường,
#    bấm, và không có gì xảy ra. Không lỗi, không câu giải thích — đúng kiểu
#    hỏng im lặng mà dự án này đã trả giá nhiều lần.

def test_khong_con_cho_nao_tu_dung_duong_nghe():
    """Năm chỗ từng tự dựng URL. Giờ chỉ `duong_tieng` được phép."""
    import re as _re

    goc = GOC / "apps" / "ltt_voice"
    pham = []
    for tep in goc.rglob("*.py"):
        if tep.name in ("du_an.py",):
            continue
        for i, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
            if _re.search(r'/audio/\{k\.audio_key\}|/audio/" \+', dong):
                pham.append(f"{tep.name}:{i}")
    assert pham == [], (
        f"tu dung duong nghe o {pham} — phai goi du_an.duong_tieng() de tep da "
        f"het han khong hien ra mot trinh phat 404")


def test_duong_tieng_bo_khoi_co_job_da_het_han(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'dt.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    from platform_core.models import Job
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from datetime import datetime, timezone

    from apps.ltt_voice import du_an

    gen = dbmod.get_session()
    db = next(gen)
    try:
        con = Job(user_id="u1", app_slug="ltt_voice", job_type="t",
                  params={}, status="done", result={})
        het = Job(user_id="u1", app_slug="ltt_voice", job_type="t",
                  params={}, status="done", result={},
                  content_expired_at=datetime.now(timezone.utc))
        db.add_all([con, het])
        db.commit()

        class K:                       # đủ hình dạng cho hàm, không cần ORM
            def __init__(self, i, job, khoa):
                self.id, self.job_id, self.audio_key = i, str(job.id), khoa

        cac = [K(1, con, "voice/out/u1/a.wav"),
               K(2, het, "voice/out/u1/b.wav")]
        d = du_an.duong_tieng(db, cac, "/ltt-voice")
        assert d == {1: "/ltt-voice/audio/voice/out/u1/a.wav"}, d
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def test_duong_tieng_khong_hoi_csdl_khi_khong_khoi_nao_co_tieng():
    """Một lô 500 dòng chưa chạy không được sinh ra một truy vấn thừa."""
    from apps.ltt_voice import du_an

    class K:
        id, job_id, audio_key = 1, "", ""

    class DbNo:
        def execute(self, *a, **k):    # noqa: ARG002
            raise AssertionError("khong duoc hoi CSDL khi khong co tep nao")

    assert du_an.duong_tieng(DbNo(), [K()], "/x") == {}


# ── 5. Một dải đầu màn, không tám bản chép ───────────────────────────────────

def test_moi_trang_dung_chung_dai_dau_man():
    """Không khuôn trang nào được tự dựng `<header class="lv-vo">`.

    🔴 VÌ SAO CHỐT, KHI BẢN CHÉP TRÔNG GIỐNG HỆT. Hai trang chi tiết đã chép tay
       dải này suốt P5–P8 và không ai thấy khác biệt — nhưng bản chép **thiếu
       `title`** trên cả hai chip. Câu bị mất là câu nói *"đây là việc của máy
       chủ, không phải bạn làm sai"*.

    ⇒ Bản chép luôn lệch. Nó chỉ lệch ở chỗ người chép không nghĩ tới, và vì
      trông giống nên không ai đi tìm.
    """
    pham = []
    for tep in sorted(MAU.glob("ltt_voice_*.html")):
        s = tep.read_text(encoding="utf-8")
        if '<header class="lv-vo">' in s:
            pham.append(tep.name)
    assert pham == [], (
        f"{pham} tu dung dai dau man — phai `include \"_voice_vo.html\"`")


def test_dai_dau_man_giu_cau_giai_thich_tren_chip():
    """Hai `title` này là nội dung, không phải trang trí."""
    s = (MAU / "_voice_vo.html").read_text(encoding="utf-8")
    assert s.count("title=") >= 3, (
        "chip mat `title` — khach thay phu hieu do ma khong co loi giai thich")


# ── 6. Mọi ô nhập phải có TÊN đọc được ───────────────────────────────────────
#
# 🔴 Ba ô đã sống trên production mà không có tên, và bộ test không thể thấy:
#
#      /ltt-voice      textarea#lv-text        ô nhập CHÍNH của cả app
#
# ⛔ `placeholder` KHÔNG phải nhãn. Nó biến mất ngay khi khách gõ ký tự đầu tiên,
#    và nhiều trình đọc màn hình không đọc nó. Ô `type=file` thì còn không có cả
#    placeholder — trình đọc màn hình chỉ nói "nút", không nói nút gì.
#
# ⭐ Gốc chung là một quyết định THẨM MỸ: thiết kế dùng `<span class="eyebrow">`
#    làm tiêu đề khối. Nó đẹp, nó đọc được bằng mắt, và nó **không liên kết** với
#    ô nhập. Nên khuôn mẫu trông như đã có nhãn ở khắp nơi.
#
# ⇒ Sửa bằng `aria-labelledby` trỏ vào chính eyebrow đó — giữ nguyên hình thức,
#   thêm quan hệ. Phép kiểm dưới đây soi HTML ĐÃ RENDER, vì quan hệ `for`/`id`
#   chỉ tồn tại sau khi Jinja chạy.

@pytest.fixture()
def khach_tc(tmp_path, monkeypatch):
    import re as _re

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-tc.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-tiep-can")
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
        tao_nguoi_dung(db, email="voice-tc@test.com",
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
    m = _re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert m
    client.post("/login", data={"username": "voice-tc@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


MAN = ["/ltt-voice", "/ltt-voice/giong", "/ltt-voice/du-an",
       "/ltt-voice/lich-su", "/ltt-voice/api"]


@pytest.mark.parametrize("duong", MAN)
def test_moi_o_nhap_deu_co_ten_doc_duoc(khach_tc, duong):
    import html.parser

    class Soi(html.parser.HTMLParser):
        """⚠️ BA cách gán nhãn hợp lệ, không phải một.

        `<label for=id>` · `aria-label`/`aria-labelledby` · và **ô nằm BÊN TRONG
        một `<label>`**. Bản đầu của bộ soi này quên cách thứ ba và báo đỏ 21
        radio của bộ chọn giọng — chúng vốn đúng. Một phép kiểm tiếp cận báo
        động giả là cách nhanh nhất để người ta tắt nó đi.
        """

        def __init__(self):
            super().__init__()
            self.o = []          # (tag, thuoc tinh) của mọi ô nhập hiện ra
            self.nhan_for = set()
            self.trong_label = 0

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            if tag == "label":
                self.trong_label += 1
                if d.get("for"):
                    self.nhan_for.add(d["for"])
            if tag in ("input", "textarea", "select"):
                if d.get("type") in ("hidden", "submit", "button"):
                    return
                self.o.append((tag, d, self.trong_label > 0))

        def handle_endtag(self, tag):
            if tag == "label" and self.trong_label:
                self.trong_label -= 1

    r = khach_tc.get(duong)
    assert r.status_code == 200, r.text[:200]
    s = Soi()
    s.feed(r.text)

    thieu = [f'{t}#{d.get("id") or d.get("name") or "?"}'
             for t, d, boc_label in s.o
             if not (boc_label or d.get("aria-label") or d.get("aria-labelledby")
                     or d.get("title") or (d.get("id") in s.nhan_for))]
    assert thieu == [], (
        f"{duong}: {thieu} khong co ten doc duoc. `placeholder` KHONG tinh — no "
        f"bien mat khi go va nhieu trinh doc man hinh khong doc no.")
