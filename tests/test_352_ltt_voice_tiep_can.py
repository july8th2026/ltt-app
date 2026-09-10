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


def test_moi_nhom_loc_deu_di_qua_batNut():
    """MỌI nhóm nút lọc phải đi qua `batNut()` — không nhóm nào tự xử.

    🔴 Bản đầu của phép kiểm này chốt `count("batNut(nut);") == 3`, và nó đỏ
       ngay ngày ai đó thêm một nhóm lọc **thứ tư hợp lệ** (làn ngôn ngữ,
       01/09/2026). Con số 3 không phải bất biến — nó là số nhóm lọc *tình cờ
       có* lúc viết.

    ⛔ Bất biến thật là một **tập hợp**: mỗi vòng lặp gắn `click` lên một nhóm
       nút lọc thì phải gọi `batNut`. Chốt số lượng thì mỗi lần thêm một nhóm
       đúng luật, gate lại đỏ và người sửa học được rằng cách xử lý là **nâng
       con số** — tức bánh cóc dạy đúng thói quen nó sinh ra để ngăn.
       *(Cùng bài học với `banh-coc-cong-chat-luong`: chốt TẬP HỢP, đừng chốt
       số lượng.)*
    """
    s = JS.read_text(encoding="utf-8")
    assert s.count("function batNut(") == 1, "batNut phai la MOT ham duy nhat"

    # Mỗi vòng lặp gắn click lên một nhóm nút lọc, tìm theo cách nó lấy nút.
    nhom = re.findall(
        r'var (\w+) = document\.querySelectorAll\('
        r'"(?:\.lv-loc-nut|\[data-chon-[\w-]+\])"\);', s)
    assert len(nhom) >= 3, f"chi thay {len(nhom)} nhom loc: {nhom}"

    # ⛔ Hỏi từng KHỐI mã sau mỗi vòng lặp, đừng đếm toàn tệp: đếm toàn tệp
    #    không phân biệt được "ba nhóm mỗi nhóm một lần" với "một nhóm ba lần".
    for ten in nhom:
        i = s.index(f"var {ten} = document.querySelectorAll(")
        # ⛔ Cắt tới khai báo `var` KẾ TIẾP Ở ĐẦU DÒNG, không phải `var` đầu
        #    tiên tìm thấy: `for (var i = 0; ...)` nằm ngay trong chính vòng
        #    lặp cần soi, nên cắt ở đó là cắt mất phần thân — và phép kiểm sẽ
        #    báo "không gọi batNut" cho một nhóm gọi nó ở dòng sau.
        j = s.find("\n    var ", i + 1)
        khoi = s[i:j if j > i else len(s)]
        assert "batNut(" in khoi, (
            f"nhom loc `{ten}` khong goi batNut() — trinh doc man hinh se "
            f"khong biet bo loc nao dang bat")

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


# ── 4. Nhãn của trình phát phải ĐƯỢC DỊCH (09/09/2026) ─────────────────────
#
# 🔴 `voice.js::ganTrinhPhat` dựng trình phát bằng JS, và năm `aria-label` của
#    nó từng GÕ CỨNG tiếng Việt không dấu: "Phat" · "Tam dung" · "Toc do phat
#    lai" · "Am luong".
#
#    Chúng rơi vào đúng mô tả ở đầu tệp này — **vô hình với con mắt đang nhìn
#    màn hình đúng**. Không ảnh chụp nào sai, không log nào kêu. Chỉ người dùng
#    trình đọc màn hình ở **bản tiếng Anh** biết, và thứ họ nghe là tiếng Việt.

NHAN_TP = GOC / "apps" / "ltt_voice" / "templates" / "_voice_nhan.html"


def test_voice_js_KHONG_con_aria_label_go_cung():
    """Mọi nhãn phải đi qua `nhan()`, tức đi qua bộ dịch của máy chủ."""
    import re
    con = re.findall(r'setAttribute\(\s*"aria-label"\s*,\s*"([^"]+)"\s*\)',
                     JS.read_text(encoding="utf-8"))
    assert not con, (
        f"aria-label go cung trong voice.js: {con} — nguoi dung ban EN se nghe "
        "tieng Viet. Dua chung qua `nhan()` + `_voice_nhan.html`")


def test_nguon_nhan_ton_tai_va_di_qua_bo_dich():
    s = NHAN_TP.read_text(encoding="utf-8")
    assert 'id="lv-nhan"' in s
    assert "tojson" in s, "noi chuoi tay se vo JSON khi ban dich co dau nhay"
    for khoa in ("phat", "tamDung", "tocDo", "amLuong"):
        assert f'"{khoa}"' in s, f"thieu nhan `{khoa}`"
    assert s.count("_(") >= 4, "co nhan khong di qua `_()` — se khong duoc dich"


def test_MOI_trang_nap_voice_js_deu_nap_ca_nguon_nhan():
    """⛔ Đối chứng quan trọng hơn: thiếu một trang thì trang ấy im lặng quay về
    bản gõ cứng — và nó im lặng đúng ở nơi không ai nhìn."""
    thu_muc = GOC / "apps" / "ltt_voice" / "templates"
    thieu = []
    for f in sorted(thu_muc.glob("ltt_voice_*.html")):
        s = f.read_text(encoding="utf-8")
        if "/static/voice.js" in s and "_voice_nhan.html" not in s:
            thieu.append(f.name)
    assert not thieu, f"nap voice.js ma khong nap nguon nhan: {thieu}"


def test_bon_nhan_deu_CO_BAN_DICH_trong_catalog():
    """Có `_()` mà catalog thiếu mục thì vẫn ra tiếng Việt trên bản EN."""
    po = (GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po").read_text(
        encoding="utf-8")
    for cau in ("Phát", "Tạm dừng", "Tốc độ phát lại", "Âm lượng"):
        assert f'msgid "{cau}"' in po, f"`{cau}` chua vao catalog"


# ── 5. U-03 — NĂM trục lọc, không phải ba (09/09/2026) ─────────────────────
#
# 🔴 `vung` và `phong_cach` **đã hiện trên màn hình** từ trước: thẻ giọng mẫu in
#    `Nữ · Miền Bắc · Tin tức`. Nhưng dữ liệu ấy chỉ tới MẮT, không tới BỘ LỌC —
#    thẻ chỉ mang `data-lan` + `data-gioi`.
#
#    Hai mươi giọng mẫu trải trên **3 vùng × 3 phong cách**, nên người muốn
#    *"giọng miền Nam kể chuyện"* phải đọc hết hai mươi thẻ để tìm ra hai. Đúng
#    mô tả của U-03: *"dữ liệu đã có, chỉ chưa thành nút"*.

CHON_TP = GOC / "apps" / "ltt_voice" / "templates" / "_voice_chon.html"


def test_du_NAM_truc_loc():
    s = CHON_TP.read_text(encoding="utf-8")
    for truc in ("data-chon-loai", "data-chon-gioi", "data-chon-lan",
                 "data-chon-vung", "data-chon-phongcach"):
        assert truc in s, f"thieu truc loc `{truc}`"


def test_the_giong_mau_MANG_du_lieu_vung_va_phong_cach():
    """⛔ Nút lọc mà thẻ không mang dữ liệu thì bấm vào **ẩn sạch** — một bộ lọc
    luôn trả rỗng còn tệ hơn không có bộ lọc."""
    s = CHON_TP.read_text(encoding="utf-8")
    i = s.index('data-loai="mau"')
    the = s[i:i + 300]
    assert 'data-vung="' in the, "the giong mau khong mang `data-vung`"
    assert 'data-phongcach="' in the, "the giong mau khong mang `data-phongcach`"


def test_js_loc_theo_ca_NAM_truc():
    js = JS.read_text(encoding="utf-8")
    for bien in ("locLoai", "locGioi", "locLan", "locVung", "locPhongCach"):
        assert bien in js, f"voice.js khong loc theo `{bien}`"


def test_the_KHONG_khai_vung_thi_KHONG_bi_an():
    """🔴 Giọng nhân bản không có `vung`/`phong_cach` — `VoiceProfile` không có
    hai cột ấy. Ẩn thứ mình không phân loại được là làm khách **mất giọng của
    chính họ**, và đó là quy ước `gioi`/`lan` ngay trên đã chốt."""
    js = JS.read_text(encoding="utf-8")
    for m in ("!d.vung || d.vung === locVung",
              "!d.phongcach || d.phongcach === locPhongCach"):
        assert m in js, (
            f"thieu chot `{m}` — loc theo vung se AN het giong nhan ban")
