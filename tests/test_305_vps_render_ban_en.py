"""Bản EN của khu VPS — đo trên TRANG RENDER, không đo trên tệp.

## Vì sao cần phép đo này khi đã có `test_304`

`test_304` đọc **tệp**: nó trích chuỗi từ `vps*.html` + `apps/vps/**/*.py` rồi
đối chiếu `.po`. Đó là một **xấp xỉ**, và ngày 25/08 xấp xỉ ấy hỏng ba lần —
mỗi lần một kiểu, ở cả hai khu:

| Phạm vi được định nghĩa bằng | Bỏ sót |
|---|---|
| quyền sở hữu tệp (`THU_MUC_MAU` của tôi) | 14 chuỗi |
| tên thư mục (`dev_*`) | 67 chuỗi, **trên trang bán hàng** |
| "không ai include nó" (`gia_api.html`) | 3 chuỗi, **trên trang giá** |

Cả ba lần vùng mù rơi vào trang thương mại nhất. Cái chung không phải cẩu thả
mà là: **trang thương mại được viết sớm nhất và đặt tên theo một hệ khác**,
trong khi phép đo bao giờ cũng viết sau và bám vào hệ tên của thời điểm nó ra
đời.

⇒ Phép đo này không nhận một danh sách tên nào. Nó **liệt kê từ bảng định
tuyến** và **đọc HTML đã render**.

## Luật chung, rút ra sau bốn cái bẫy trong một buổi

    Kiểm trên thứ hệ thống THẬT SỰ dùng, không trên thứ ta vừa ghi.

      `.po` là thứ ta ghi        ->  `.mo` qua `gettext` là thứ chạy
      danh sách trang gõ tay     ->  bảng định tuyến là thứ phục vụ
      `pattern` trong mã nguồn   ->  `repr(compiled.pattern)` là thứ khớp
"""
from __future__ import annotations

import gettext
import pathlib
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Dấu tiếng Việt. `đ` **có** trong danh sách — nó là một chữ cái — nên phải
#: lọc số tiền TRƯỚC khi tìm nó (xem `_TIEN`).
DAU = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                 r"ùúủũụưừứửữựỳýỷỹỵđ]", re.I)

#: Số tiền VND. Nền tảng tính tiền bằng đồng ở **cả hai** ngôn ngữ, nên
#: `149.000đ` đúng trên bản `en` y hệt bản `vi` — nó KHÔNG phải chữ chưa dịch.
#:
#: ⚠️ Không lọc thì phép đo đỏ vì một thứ **đúng**, và người sửa sẽ đi "dịch"
#: ký hiệu tiền tệ. Đó là phép đo bắt nhầm đối tượng.
_TIEN = re.compile(r"\d[\d.,]*\s*đ")


def test_bo_loc_so_tien_khong_bi_hong_boi_ky_tu_vo_hinh():
    """Chốt chính bộ lọc ở trên, vì nó đã hỏng một lần theo kiểu vô hình.

    Một regex viết qua heredoc có thể chứa `\\x08` (backspace) thay cho `\\b`:
    nó **vô hình trong `grep`** và regex im lặng không khớp gì. Đã dính bốn lần
    trong ngày 25/08, lần cuối làm một phép kiểm xanh mà không đo gì.

    Cách phát hiện là đọc `repr(pattern)` — thứ *thật sự* được biên dịch — chứ
    không phải nhìn mã nguồn.
    """
    assert "\x08" not in _TIEN.pattern, repr(_TIEN.pattern)
    assert "\x08" not in DAU.pattern
    assert _TIEN.sub("", "149.000đ / 30 days").strip() == "/ 30 days"


def _duong_html_khu_vps() -> list[str]:
    """Route GET trả HTML của khu VPS, **đọc từ router**.

    Không gõ tay: một danh sách gõ tay đúng hôm nay và sai vào ngày ai đó thêm
    trang thứ năm — và nó sai **im lặng**, vì trang mới chỉ đơn giản không được
    đo.
    """
    from apps.vps.manifest import MANIFEST
    from apps.vps.routes import router

    goc = MANIFEST.route_prefix.rstrip("/")
    return sorted(goc + r.path for r in router.routes
                  if "GET" in getattr(r, "methods", set()))


#: Trang **không render được trong môi trường test**, kèm lý do.
#:
#: 🔴 Đây là ngoại lệ DUY NHẤT được phép, và nó phải nêu tên. Không có danh
#: sách này thì `/console` vẫn "đo được": nó chuyển hướng về trang máy khi
#: thiếu Proxmox, và phép đo **âm thầm đo trang máy hai lần** trong khi khai là
#: đo bốn trang.
#:
#: Đã xảy ra thật: bản đầu của tệp này báo `5 passed` sau khi tôi chèn một câu
#: tiếng Việt vào `vps_console.html` — vì câu đó chưa bao giờ lên trang nào cả.
#: Một phép kiểm xanh trong lúc không đo thứ nó khai là đang đo.
#:
#: ⚠️ Chuỗi của trang console vẫn được `test_304` phủ (nó đọc tệp). Chỗ thiếu
#: là phủ bằng **render**, và nó thiếu vì `vncproxy` cần Proxmox thật.
KHONG_RENDER_DUOC_TRONG_TEST = {
    "/vps/{instance_id}/console": "cần vé vncproxy từ Proxmox thật",
}


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps-render.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vps-render")
    monkeypatch.setenv("LTT_VPS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def _client():
    from fastapi.testclient import TestClient
    from server.app import create_app
    # `follow_redirects=True`: phân loại bằng **đích đến cuối**, không bằng mã
    # trạng thái. Với `False`, một trang riêng tư trả 303 và một trang công khai
    # trả 200 — trông như phân biệt được, nhưng nó lẫn chuyển hướng đăng nhập
    # với mọi chuyển hướng khác.
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=True)


def _tao_khach_va_may(dbmod):
    """Một khách CÓ máy — nếu không, ba trang cấp máy không render và phép đo
    lặng lẽ chỉ đo một trang.

    Đây chính là lớp lỗi đã bỏ sót 67 chuỗi ở khu API: **một trang không được
    render thì không được đo**, và lý do có thể chỉ là "dữ liệu thử chưa đủ".
    """
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    from apps.vps.tables import VpsGateway, VpsInstance, VpsIp

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="render@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 20_000)
        now = datetime.now(timezone.utc)
        gw = uuid.uuid4().hex
        db.add(VpsGateway(id=gw, ten="gw-test", vung="sgp",
                          ip_cong_khai="203.0.113.1", nha_cung_cap_id="test",
                          octet_dau=10, octet_cuoi=250, bridge="vmbr1",
                          subnet_cidr="10.51.0.0/24", subnet_gw="10.51.0.1",
                          dns="1.1.1.1", mtu=1420, created_at=now))
        db.flush()
        ma = uuid.uuid4().hex
        db.add(VpsInstance(id=ma, user_id=u.id, ten="win-render",
                           plan_id="vps-vua", os_id="winsrv2022-core",
                           gateway_id=gw, vmid=9101, ip_noi_bo="10.51.0.9",
                           trang_thai="dang_chay", created_at=now,
                           updated_at=now,
                           paid_until=now + timedelta(days=14),
                           bang_thong_byte=1_000_000_000))
        db.add(VpsIp(instance_id=ma, gateway_id=gw, dia_chi="203.0.113.9",
                     nhan="test"))
        db.commit()
        return ma
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_nhap(client):
    r = client.get("/login")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    client.post("/login", data={"username": "render@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": tok})


def _doan_con_tieng_viet(html: str) -> list[str]:
    """Đoạn văn trong `<main>` còn dấu tiếng Việt, sau khi bỏ số tiền."""
    m = re.search(r"(?is)<main[^>]*>.*?</main>", html)
    than = m.group(0) if m else html
    than = re.sub(r"(?is)<(script|style|pre|code|nav|footer|header)[^>]*>.*?</\1>",
                  " ", than)
    than = re.sub(r"(?s)<!--.*?-->", " ", than)
    than = re.sub(r"(?s)<[^>]+>", "\n", than)
    ra = []
    for dong in than.split("\n"):
        dong = re.sub(r"\s+", " ", dong).strip()
        if len(dong) < 4:
            continue
        # Bỏ số tiền TRƯỚC khi tìm dấu — `đ` là một chữ cái tiếng Việt.
        if DAU.search(_TIEN.sub(" ", dong)):
            ra.append(dong)
    return ra


def test_moi_trang_VPS_ban_EN_khong_con_tieng_viet(moi_truong):
    """Đo **mọi** trang HTML của khu VPS, ở **cả hai** tư cách người xem.

    Gọi thẳng `/en/...`: tiền tố đường dẫn quyết định, còn `Accept-Language`
    chỉ áp cho đường không tiền tố. Gọi thẳng thì phép đo không phụ thuộc
    thương lượng ngôn ngữ — và **không có chuyển hướng nào để đi lạc**.
    """
    ma = _tao_khach_va_may(moi_truong)
    duong = [d.replace("{instance_id}", ma) for d in _duong_html_khu_vps()]

    client = _client()
    try:
        _dang_nhap(client)
        do_duoc, bo_qua, ban = [], [], {}
        for mau, d in zip(_duong_html_khu_vps(), duong):
            r = client.get("/en" + d)
            assert r.status_code == 200, f"{d} tra {r.status_code}"
            assert "/login" not in str(r.url), (
                f"{d} bat dang nhap du da dang nhap: {r.url}")
            # 🔑 Đích đến cuối phải ĐÚNG trang đã xin. Không kiểm điều này thì
            # một trang chuyển hướng đi nơi khác vẫn tính là "đã đo" — và thứ
            # được đo là trang KHÁC.
            den = str(r.url).replace("https://testserver", "")
            if den != "/en" + d:
                assert mau in KHONG_RENDER_DUOC_TRONG_TEST, (
                    f"{d} chuyen huong toi {den} — neu day la co y thi phai "
                    "khai vao KHONG_RENDER_DUOC_TRONG_TEST kem ly do")
                bo_qua.append(mau)
                continue
            do_duoc.append(d)
            con = _doan_con_tieng_viet(r.text)
            if con:
                ban[d] = con

        # Bỏ qua đúng danh sách đã khai — không hơn, KHÔNG KÉM. "Không kém" bắt
        # trường hợp một ngoại lệ thành thừa mà không ai gỡ.
        assert sorted(bo_qua) == sorted(KHONG_RENDER_DUOC_TRONG_TEST), (
            f"bo qua thuc te {sorted(bo_qua)} != khai "
            f"{sorted(KHONG_RENDER_DUOC_TRONG_TEST)}")

        # ⚠️ Khẳng định SỐ trang đo được. Không có dòng này thì một trang bị
        # bỏ qua sẽ làm phép kiểm **xanh hơn**, không đỏ — và `pytest -rs`
        # không phải thói quen của ai. Một phép kiểm bỏ qua phải KHÓ bỏ qua
        # hơn một phép kiểm đỏ.
        assert len(do_duoc) == len(duong) - len(KHONG_RENDER_DUOC_TRONG_TEST), (
            f"chi do duoc {len(do_duoc)}/{len(duong)} trang")
        assert len(do_duoc) >= 3, "so trang do duoc qua it — bo trich hong?"
        assert ban == {}, "\n".join(
            f"  {d}: {v[:3]}" for d, v in ban.items())
    finally:
        client.close()


#: Hai trang khu VPS mở cho khách **chưa đăng nhập**, và cả hai đều có lý do.
#:
#:  `/vps`              trang bán. Thẻ app trong catalog trỏ tới đây, nên đòi
#:                      đăng nhập là ngõ cụt ngay bước đầu của phễu.
#:  `/vps/dieu-khoan`   điều khoản. Clickwrap nói "bấm là bạn đồng ý"; một trang
#:                      điều khoản đòi đăng nhập là một trang khách **không đọc
#:                      được trước khi quyết định** — họ đồng ý với thứ chưa
#:                      từng thấy.
#:
#: ⚠️ Danh sách này là một **quyết định**, không phải một phép đo. Thêm đường vào
#:    đây nghĩa là mở thêm một bề mặt công khai — hãy nói được vì sao.
CONG_KHAI_AN_DANH = ["/vps", "/vps/dieu-khoan"]


def test_trang_VPS_an_danh_cung_khong_con_tieng_viet(moi_truong):
    """Khách ẩn danh vào được hai trang; các trang còn lại bắt đăng nhập.

    Phân loại bằng **đích đến cuối**, không bằng mã trạng thái: với
    `follow_redirects=True` một trang riêng tư trả **200** ở `/login?next=…`,
    nên đọc mã trạng thái sẽ gọi nó là "công khai" — sai theo hướng nguy hiểm.
    """
    ma = _tao_khach_va_may(moi_truong)
    duong = [d.replace("{instance_id}", ma) for d in _duong_html_khu_vps()]

    client = _client()
    try:
        cong_khai, rieng_tu = [], []
        for d in duong:
            r = client.get("/en" + d)
            if "/login" in str(r.url):
                rieng_tu.append(d)
                continue
            cong_khai.append(d)
            assert _doan_con_tieng_viet(r.text) == [], (
                f"{d} (an danh) con tieng Viet")
        assert cong_khai == CONG_KHAI_AN_DANH, f"cong khai: {cong_khai}"
        assert len(rieng_tu) == len(duong) - len(CONG_KHAI_AN_DANH), (
            f"rieng tu: {rieng_tu}")
    finally:
        client.close()


def test_moi_chuoi_VPS_toi_duoc_MO_chu_khong_chi_nam_trong_PO():
    """`.po` là thứ ta ghi; `.mo` là thứ chạy.

    🔴 Nếu một msgid **đã tồn tại** ở trên với `msgstr ""`, rồi bản dịch được
    **nối thêm** ở cuối tệp, `msgfmt` lấy bản ĐẦU — tức bản rỗng. Bản nối thêm
    thành vô hình.

    Triệu chứng **y hệt "chưa dịch"**, nên người sửa tiếp theo sẽ dịch lại và
    nối thêm một bản trùng nữa. Chuyện này đã xảy ra thật ở khu API ngày 25/08
    (4 bản trùng trước khi hiểu ra), và đợt dịch VPS đã **nối thêm 160 khối**
    vào `.po` — nên nó là rủi ro có thật chứ không phải giả định.
    """
    from tests.test_304_vps_giao_dien_ban_hang import _chuoi_khu_vps

    chuoi = _chuoi_khu_vps()
    assert len(chuoi) > 120, f"bo trich hong: chi thay {len(chuoi)} chuoi"

    tr = gettext.translation("messages", localedir=str(GOC / "locale"),
                             languages=["en"])
    khong_toi = sorted(s for s in chuoi if tr.gettext(s) == s)
    assert khong_toi == [], (
        f"{len(khong_toi)} chuoi co trong .po nhung KHONG toi duoc .mo — "
        "gan nhu chac chan la msgid trung, ban dau rong.\n"
        + "\n".join("  - " + s[:74] for s in khong_toi[:12]))


def test_po_khong_co_msgid_trung():
    """Chốt nguyên nhân, không chỉ chốt triệu chứng."""
    import collections

    po = (GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po").read_text(
        encoding="utf-8")

    def gop(x):
        return "".join(re.findall(r'"((?:\\.|[^"])*)"', x))

    ids = []
    for khoi in po.split("\n\n"):
        m = re.search(r'(?m)^msgid ((?:"(?:\\.|[^"])*"\n?)+)'
                      r'msgstr ((?:"(?:\\.|[^"])*"\n?)+)', khoi)
        if m and gop(m.group(1)):
            ids.append(gop(m.group(1)))
    trung = [m for m, c in collections.Counter(ids).items() if c > 1]
    assert trung == [], f"{len(trung)} msgid trung: {trung[:5]}"
