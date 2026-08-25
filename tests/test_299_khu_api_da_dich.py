"""Khu API phải có bản dịch tiếng Anh ĐẦY ĐỦ — không phải bánh cóc, là số 0.

## Vì sao chốt cứng ở 0 chứ không phải "không cho tăng"

`tools/check_i18n.py` là bánh cóc, và nó đúng cho phần còn lại của nền tảng:
~1.800 chuỗi chưa bọc `_()`, bắt đỏ ngay là chặn mọi việc khác.

Khu API thì khác, vì hai lẽ:

1. **Khách của nó là lập trình viên**, và phần lớn sẽ chọn `en`. Đo ngày
   25/08 trước khi sửa: **85% đoạn văn trên bản `en` vẫn là tiếng Việt**, năm
   trang tiếng Việt 100% dù `<html lang="en">`. Thứ khách thấy không đọc là
   "chưa dịch" mà là **làm dở dang** — và hạ tầng làm dở dang thì không ai
   giao thẻ tín dụng cho.
2. **Nợ đã được trả hết.** Sau đợt dịch 25/08, phần `<main>` của cả 14 trang
   là 0/286 đoạn tiếng Việt. Đặt bánh cóc ở một con số dương khi con số thật
   là 0 chỉ là mời nó mọc lại.

## Ba thứ phép kiểm này chốt

- **Chuỗi mới phải có bản dịch.** Thêm `_("...")` vào một trang khu API mà
  quên dịch là đỏ.
- **Không có mục `fuzzy`.** `fuzzy` là bản dịch `msgmerge` ĐOÁN bằng cách ghép
  msgid mới với một msgstr cũ tương tự. Ngày 25/08 khu API có **74 mục** như
  vậy, và chúng sai theo kiểu nguy hiểm nhất:

      "Ngân sách của bạn"            -> "Your scripts"
      "Chưa đăng ký điểm nhận nào."  -> "Not signed in"

  `msgfmt` bỏ qua mục fuzzy nên chúng CHƯA hiện ra cho ai. Nhưng chúng giấu nợ
  khỏi bất cứ ai đọc tệp `.po`, và chỉ cách **một lần gỡ cờ** là "Your scripts"
  hiện trên trang ngân sách.
- **Placeholder không được rơi.** `%(n)s` mất trong bản dịch = trang nổ
  `TypeError` lúc render, và chỉ nổ ở ngôn ngữ đó nên bộ test tiếng Việt xanh.
- **Trang render ra không còn tiếng Việt trên bản `en`.** Bốn phép kiểm ở cuối
  tệp. Chúng khác hẳn ba phép trên: ba phép trên đọc **tệp**, bốn phép này
  render **trang**.

## ⚠️ Có một bản gần giống ở `test_304_vps_giao_dien_ban_hang.py`, và đó là CỐ Ý

Khu VPS có phép đo riêng, viết độc lập, gần trùng logic với các hàm ở đây.
**Đừng gom lại vội.** Hai phiên chạy song song ngày 25/08 đã mất nửa buổi cho
đúng loại va chạm mà một mô-đun dùng chung tạo ra (`ltt.css`,
`tools/gui/ltt.css`, `ho_so_he_thong.txt` — mỗi lần một bên sửa là bên kia đỏ
gate). Một phụ thuộc dùng chung giữa hai khu đang xây song song là một điểm
phải điều phối, và điều phối đắt hơn hai bản sao.

⇒ Gom lại **sau**, khi cả hai khu ổn. Ghi ở đây để người sau không tưởng hai
bản là sơ suất rồi đi hợp nhất giữa lúc cả hai đang động.

## 🔴 Năm cái bẫy đã trả giá — đọc trước khi sửa phép đo nào ở đây

Đầy đủ ở `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md` §7d. Bản một dòng:

> **Phạm vi của phép đo phải được định nghĩa bằng chính thứ cần đo.**

Năm lần trong ngày 25/08 nó bị định nghĩa bằng thứ khác — tệp *của ai*, tên thư
mục, *ai include tệp này*, *có chuyển hướng không*, *`.po` nhìn thấy gì* — và
mỗi lần phép đo báo xanh trong khi bỏ sót. Bốn trong năm lần vùng mù rơi đúng
vào **trang thương mại**.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
PO = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"

VN = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                r"ùúủũụưừứửữựỳýỷỹỵđ]", re.I)

# Khu API = những tệp DỰNG NÊN trang khu API — **tất cả**, không trừ tệp nào.
#
# ⚠️ Trước 25/08 danh sách này loại `dev_cli.html` và `dev_docs.html` vì lúc đó
# hai tệp ấy do phiên khác giữ. Việc loại trừ **đúng về phân công nhưng sai về
# phép đo**: bánh cóc báo 8 chuỗi thiếu trong khi quét đầy đủ ra 25 — 14 trong
# số đó nằm ở `dev_docs.html` mà nó cố ý không nhìn.
#
# Tức nó **im lặng cho 17 chuỗi**, đúng lớp lỗi "bánh cóc không chặn" mà chính
# ngày hôm đó đã bắt được ở hai chỗ khác. Một phép đo có vùng mù thì con số nó
# đưa ra không dùng để kết luận được, kể cả khi vùng mù ấy được ghi rõ.
#
# Bài học: ranh giới **phân công** không được trở thành ranh giới **đo lường**.
THU_MUC_MAU: tuple[str, ...] = ()


def _tep_khu_api() -> list[pathlib.Path]:
    tep = [p for p in sorted((GOC / "server" / "templates").glob("dev_*.html"))
           if p.name not in THU_MUC_MAU]
    tep += [GOC / "server" / "templates" / "developers_base.html",
            GOC / "server" / "routes" / "developer.py",
            GOC / "platform_core" / "public_api" / "governance.py"]
    # 🔴 PHẦN CÔNG KHAI CỦA KHU API — thêm 25/08, và nó lộ ra ĐÚNG cùng một
    #    điểm mù mà `THU_MUC_MAU` vừa để lại.
    #
    #    Phép đo này đọc TỆP, không render trang. Nên `_cam_chon.html` —
    #    thân dùng chung của `/huong-dan` và `/developers/cli`, nơi hơn 30
    #    chuỗi của trang cắm sống — **không được quét**, dù trang hiển thị
    #    chúng cho khách. Một tệp được include không tự lọt vào phép đo của
    #    tệp include nó.
    #
    #    Ba trang công khai (`/huong-dan`, `/huong-dan/cong-cu`, `/tai/…`) là
    #    thứ người CHƯA có tài khoản đọc — tức đúng những người ta ít có cơ
    #    hội sửa sai nhất nếu trang hiện sai ngôn ngữ.
    tep += [GOC / "server" / "templates" / "_cam_chon.html",
            GOC / "server" / "templates" / "huong_dan.html",
            GOC / "server" / "templates" / "huong_dan_cong_cu.html",
            GOC / "server" / "routes" / "tai_lieu_api.py"]
    return [p for p in tep if p.exists()]


def _chuoi_python(tep: pathlib.Path) -> set[str]:
    """Đọc bằng AST, không bằng regex.

    `governance.py` nối chuỗi ngầm qua nhiều dòng — `N_("aaa" "bbb")` — và
    một regex bắt literal sẽ cắt cụt msgid. Chính lỗi đó làm đợt trích đầu
    ngày 25/08 bỏ sót 7 chuỗi.
    """
    ra: set[str] = set()
    cay = ast.parse(tep.read_text(encoding="utf-8"), filename=str(tep))
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Call) or not nut.args:
            continue
        ten = getattr(nut.func, "id", None) or getattr(nut.func, "attr", None)
        if ten not in ("_", "N_", "_t", "gettext"):
            continue
        dau = nut.args[0]
        if isinstance(dau, ast.Constant) and isinstance(dau.value, str):
            ra.add(dau.value)
    return ra


# Trong Jinja, `_()` gần như luôn là một literal; vẫn gom các literal kề nhau
# để không cắt cụt nếu ai đó viết `_("a" "b")`.
_RE_JINJA = re.compile(
    r"""\b(?:_|N_|_t)\(\s*((?:(?:"(?:\\.|[^"])*"|'(?:\\.|[^'])*')\s*)+)""")
_RE_LIT = re.compile(r'"((?:\\.|[^"])*)"' r"|'((?:\\.|[^'])*)'")


def _chuoi_jinja(tep: pathlib.Path) -> set[str]:
    ra: set[str] = set()
    for m in _RE_JINJA.finditer(tep.read_text(encoding="utf-8")):
        s = "".join(a or b for a, b in _RE_LIT.findall(m.group(1)))
        ra.add(s.replace('\\"', '"').replace("\\'", "'").replace("\\n", "\n"))
    return ra


def _chuoi_khu_api() -> set[str]:
    ra: set[str] = set()
    for t in _tep_khu_api():
        ra |= _chuoi_python(t) if t.suffix == ".py" else _chuoi_jinja(t)
    # Chỉ quan tâm chuỗi tiếng Việt: `"Playground"`, `"Test"`, `"Live"` giống
    # nhau ở hai ngôn ngữ và không cần một dòng trong catalog.
    return {s for s in ra if s.strip() and VN.search(s)}


def _doc_po() -> dict[str, tuple[str, bool]]:
    """msgid -> (msgstr, có cờ fuzzy)."""
    noi_dung = PO.read_text(encoding="utf-8")

    def gop(x: str) -> str:
        return "".join(re.findall(r'"((?:\\.|[^"])*)"', x))

    def bo_thoat(s: str) -> str:
        return (s.replace('\\"', '"').replace("\\n", "\n")
                 .replace("\\t", "\t").replace("\\\\", "\\"))

    ra: dict[str, tuple[str, bool]] = {}
    for khoi in noi_dung.split("\n\n"):
        m = re.search(r'(?m)^msgid ((?:"(?:\\.|[^"])*"\n?)+)'
                      r'msgstr ((?:"(?:\\.|[^"])*"\n?)+)', khoi)
        if not m:
            continue
        mid = bo_thoat(gop(m.group(1)))
        if mid:
            ra[mid] = (bo_thoat(gop(m.group(2))), "#, fuzzy" in khoi)
    return ra


def test_tim_duoc_chuoi_de_kiem():
    """Tiền đề: nếu bộ trích hỏng thì mọi phép kiểm dưới đây xanh giả."""
    chuoi = _chuoi_khu_api()
    assert len(chuoi) > 150, (
        f"chi trich duoc {len(chuoi)} chuoi khu API — bo trich hong, "
        "cac phep kiem duoi day dang xanh gia")


def test_moi_chuoi_khu_api_deu_co_ban_dich_EN():
    po = _doc_po()
    thieu = sorted(s for s in _chuoi_khu_api()
                   if not (po.get(s) or ("", False))[0])
    assert thieu == [], (
        f"{len(thieu)} chuoi khu API chua co ban dich EN.\n"
        "Dich roi chay `python tools\\i18n.py bien-dich`. Dung chay\n"
        "`i18n.py trich` cho vai chuoi: no sap xep lai ca tep .po.\n\n"
        + "\n".join("  - " + s[:78] for s in thieu[:20]))


def test_khong_con_muc_fuzzy_nao_trong_khu_api():
    """`fuzzy` = ban dich MAY DOAN, va no doan sai theo kieu tu tin."""
    po = _doc_po()
    fz = sorted(s for s in _chuoi_khu_api() if (po.get(s) or ("", False))[1])
    assert fz == [], (
        f"{len(fz)} muc khu API con co `fuzzy`. `msgfmt` bo qua chung nen\n"
        "chung CHUA hien ra — nhung chung giau no dich, va chi cach mot lan\n"
        "go co la mot ban dich sai hien ra cho khach.\n"
        "Doc lai tu ban goc tieng Viet roi go co, dung sua msgstr cu.\n\n"
        + "\n".join("  - " + s[:78] for s in fz[:20]))


def test_ban_dich_khong_lam_roi_placeholder():
    """Rơi `%(n)s` = trang nổ TypeError, và CHỈ nổ ở tiếng Anh.

    Bộ test chạy bằng tiếng Việt sẽ xanh suốt trong khi trang tiếng Anh 500.
    """
    po = _doc_po()
    ky_hieu = re.compile(r"%\([a-z_]+\)s|\{[a-z_]+\}|%%")
    lech = []
    for s in _chuoi_khu_api():
        dich = (po.get(s) or ("", False))[0]
        if not dich:
            continue
        if sorted(ky_hieu.findall(s)) != sorted(ky_hieu.findall(dich)):
            lech.append((s, dich))
    assert lech == [], (
        "ban dich lam roi hoac them placeholder:\n"
        + "\n".join(f"  goc : {a[:70]}\n  dich: {b[:70]}" for a, b in lech[:8]))


@pytest.mark.parametrize("tep", ["dev_keys.html", "dev_usage.html",
                                 "dev_webhooks.html", "dev_privacy.html"])
def test_bon_trang_nang_nhat_khong_con_chuoi_nao_thieu(tep):
    """Bốn trang có nhiều chữ nhất — tách riêng để lỗi chỉ ra đúng trang.

    Một phép kiểm gộp báo "37 chuỗi thiếu" bắt người sửa đi tìm; phép kiểm này
    nói thẳng trang nào.
    """
    p = GOC / "server" / "templates" / tep
    po = _doc_po()
    thieu = sorted(s for s in _chuoi_jinja(p)
                   if s.strip() and VN.search(s)
                   and not (po.get(s) or ("", False))[0])
    assert thieu == [], f"{tep}: {len(thieu)} chuoi chua dich: {thieu[:5]}"


# ── Phép đo THẬT: render trang, không đọc tệp ───────────────────────────────
#
# 🔴 VÌ SAO THÊM (25/08). Mọi phép kiểm ở trên đọc **tệp**. Đó là xấp xỉ, và
#    hôm nay nó hụt hai lần theo hai cách khác nhau:
#
#      ① `THU_MUC_MAU` loại `dev_cli.html` + `dev_docs.html` vì "chúng là tệp
#         của phiên kia" — 17 chuỗi im lặng lọt qua.
#      ② `_cam_chon.html` là thân **được include**, nên nó không nằm trong danh
#         sách tệp nào cả — hơn 30 chuỗi trang cắm không được đo, dù trang hiển
#         thị chúng cho khách. Mở rộng danh sách lòi ra **67 chuỗi**, và chúng
#         nằm đúng ở các trang người CHƯA có tài khoản đọc.
#
# ⭐ Điểm chung của cả hai, và đây mới là bài học: **phạm vi của phép đo được
#    định nghĩa bằng một thứ không phải là thứ cần đo** — một lần là quyền sở
#    hữu tệp, một lần là quy ước đặt tên thư mục (`dev_*`).
#
#    Thứ cần đo là **khách nhìn thấy chữ gì**. Nên phép đo đúng là: render
#    trang, đọc chữ ra, tìm dấu tiếng Việt trên bản `en`. Phép đo đó không có
#    điểm mù về include, về đặt tên, hay về tệp-của-ai — vì nó không hỏi câu
#    nào trong ba câu ấy.
#
# ⚠️ Nó KHÔNG thay các phép kiểm đọc tệp ở trên: những phép kiểm đó chỉ ra
#    được *chuỗi nào* và *ở tệp nào*, còn phép kiểm này chỉ nói *trang nào còn
#    tiếng Việt*. Hai phép đo trả lời hai câu khác nhau.

#: Module phục vụ phần công khai của khu API. Đo **mọi** trang chúng khai.
#:
#: 🔴 LIỆT KÊ TỪ BẢNG ĐỊNH TUYẾN, KHÔNG CHÉP TAY. Bản đầu của phép đo này là ba
#:    URL gõ tay — tức nó mắc **đúng lỗi nó sinh ra để chặn**, chỉ ở một tầng
#:    cao hơn: phạm vi lại được định nghĩa bằng thứ tôi nhớ ra, chứ không phải
#:    bằng thứ máy chủ thật sự phục vụ.
#:
#: ⭐ Vì sao chuyện này lặp lại ba lần trong một ngày: **trang thương mại được
#:    viết SỚM NHẤT và đặt tên theo một hệ khác** (`gia_api`, `huong_dan`),
#:    trong khi phép đo bao giờ cũng viết SAU và bám vào hệ tên của thời điểm
#:    nó ra đời. Thêm một route mới thì phép đo phải tự thấy — không chờ ai nhớ.
MODULE_CONG_KHAI_API = (
    "server.routes.tai_lieu_api",   # /huong-dan, /huong-dan/cong-cu, /tai/…
    "server.routes.status",         # /status/api
)

#: Trang lẻ nằm trong module lớn hơn, nên không lấy trọn module được.
TRANG_LE_API = ("/gia-api",)        # `dashboard.py` phục vụ cả trang không phải API


def _trang_cong_khai_api() -> list[str]:
    """Mọi URL công khai của khu API, đọc từ chính router.

    ⚠️ Bỏ route có tham số đường dẫn (`/tai/{ten}`) và route trả tệp: phép đo
       này soi CHỮ GIAO DIỆN, và một tệp tải về không có chữ giao diện nào.
    """
    import importlib

    ra = list(TRANG_LE_API)
    for ten in MODULE_CONG_KHAI_API:
        router = importlib.import_module(ten).router
        for r in router.routes:
            duong = getattr(r, "path", "")
            if not duong or "{" in duong:
                continue
            if "GET" not in (getattr(r, "methods", None) or set()):
                continue
            # Chỉ trang HTML. `/tai/cong-cu-cam` trả một tệp .exe.
            if duong.startswith("/tai/"):
                continue
            ra.append(duong)
    return sorted(set(ra))


TRANG_CONG_KHAI_API = tuple(_trang_cong_khai_api())

#: Thẻ mang chữ **của giao diện**. Cố ý bỏ `pre`/`code`: đoạn cấu hình và tên
#: tham số không dịch và không được phép dịch.
_THE_CHU = re.compile(
    r"<(h1|h2|h3|h4|p|li|th|td|button|summary|label|caption)\b[^>]*>(.*?)</\1>",
    re.S | re.I)
_BO_THE = re.compile(r"<[^>]+>", re.S)
_BO_MA = re.compile(r"<(code|pre|script|style)\b.*?</\1>", re.S | re.I)


#: Số tiền đồng: `100đ`, `5.000đ`, `40,000đ`.
#:
#: ⚠️ `đ` là KÝ HIỆU TIỀN TỆ, không phải chữ chưa dịch. Nền tảng tính tiền bằng
#:    VND ở cả hai ngôn ngữ, nên `100đ` đúng trên bản `en` y như trên bản `vi`.
#:    Bản đầu của phép đo này đỏ `/gia-api` vì 15 con số như vậy — một phép đo
#:    bắt nhầm đối tượng, đúng lớp lỗi mà chính tệp này tồn tại để chặn.
_TIEN = re.compile(r"\d[\d.,]*\s*đ")


def _chu_hien_thi(html: str) -> list[str]:
    """Chữ giao diện thật sự hiện ra, đã bỏ mã, thẻ và số tiền."""
    ra = []
    for m in _THE_CHU.finditer(_BO_MA.sub(" ", html)):
        chu = _BO_THE.sub(" ", m.group(2))
        chu = re.sub(r"\s+", " ", _TIEN.sub(" ", chu)).strip()
        if chu:
            ra.append(chu)
    return ra


@pytest.fixture(scope="module")
def khach_en(tmp_path_factory):
    """Client với một CSDL rỗng tạm.

    ⚠️ CẤP CSDL chứ không BỎ QUA trang cần nó. `/status` và `/status/api` đọc
       cơ sở dữ liệu; bản đầu của phép đo này để chúng ném
       `DatabaseNotConfigured` rồi tôi suýt cho chúng vào danh sách loại trừ —
       tức lại dựng một vùng mù, đúng thứ tệp này tồn tại để chặn. Một trang
       khó đo không phải một trang không cần đo.
    """
    tmp = tmp_path_factory.mktemp("dich")
    import platform_core.db as dbmod

    cu_url = os.environ.get("LTT_DATABASE_URL")
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(tmp / 'dich.db').as_posix()}"
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    from fastapi.testclient import TestClient

    from server.app import create_app

    with TestClient(create_app()) as client:
        yield client

    if cu_url is None:
        os.environ.pop("LTT_DATABASE_URL", None)
    else:
        os.environ["LTT_DATABASE_URL"] = cu_url
    dbmod.reset_engine()


@pytest.mark.parametrize("duong", TRANG_CONG_KHAI_API)
def test_trang_cong_khai_render_ban_EN_khong_con_tieng_viet(duong, khach_en):
    """Render thật, bản `en`, đếm đoạn còn dấu tiếng Việt.

    ⛔ Phép đo này là thứ duy nhất ở tệp này KHÔNG hỏi "chuỗi nằm ở tệp nào".
       Nó hỏi đúng câu khách hỏi: *trang này hiện ra bằng tiếng gì.*
    """
    # ⭐ GỌI THẲNG `/en/…`, KHÔNG thương lượng qua `Accept-Language`.
    #
    #    Đo thật 25/08, bốn cách gọi, cùng một trang:
    #
    #      không header          -> /huong-dan      bản VI   (mặc định là vi)
    #      Accept-Language: en   -> /en/huong-dan   bản EN   (qua một 302)
    #      /en/huong-dan         -> /en/huong-dan   bản EN
    #      /en/huong-dan + "vi"  -> /en/huong-dan   bản EN   ← tiền tố THẮNG
    #
    #    Tiền tố đường dẫn là quyết định; header chỉ áp cho đường không tiền
    #    tố. Nên gọi thẳng là phép đo **không phụ thuộc thương lượng**, và nó
    #    xoá luôn cái chuyển hướng đã sinh ra bẫy dưới đây.
    #
    # ⛔ BẪY ĐÃ MẮC, giữ lại vì nó sẽ mắc lại: bản đầu dùng
    #    `follow_redirects=False` rồi coi MỌI chuyển hướng là "không công
    #    khai". Header `en` làm middleware trả `302 → /en/…` cho **tất cả**,
    #    nên phép đo bỏ qua sạch 5 trang trong khi vẫn báo `8 passed`. Nó im
    #    lặng không đo gì.
    #
    #    Chỉ `pytest -rs` mới lộ, và không ai chạy `-rs` theo thói quen. Rút
    #    ra: **một phép kiểm bỏ qua phải KHÓ bỏ qua hơn một phép kiểm đỏ.**
    r = khach_en.get("/en" + duong)
    assert r.status_code == 200, f"/en{duong} tra {r.status_code}"

    # "Công khai" xác định bằng ĐÍCH ĐẾN, không bằng tên module. `/status` nằm
    # cùng router với `/status/api` nhưng CỐ Ý chỉ dành cho vận hành viên (nó
    # nêu tên CSDL, đĩa, tunnel), nên nó rơi về `/login`.
    if "/login" in str(r.url):
        pytest.skip(f"{duong} khong cong khai (roi ve {r.url}), "
                    "nen khong thuoc phep do nay")
        # ⚠️ `skip` một mình VẪN đọc như xanh: nếu mai một ai đó đặt `/gia-api`
        #    sau đăng nhập, phép đo này im lặng mất một trang. Phép kiểm
        #    `test_dung_bon_trang_duoc_do` bên dưới đóng chỗ đó.

    con_viet = [c for c in _chu_hien_thi(r.text) if VN.search(c)]
    assert con_viet == [], (
        f"{duong} (ban en): {len(con_viet)} doan con tieng Viet.\n"
        + "\n".join("  - " + c[:90] for c in con_viet[:10]))


#: Trang duy nhất được phép rơi khỏi phép đo, và lý do nằm ngay đây:
#: `/status` là báo cáo cho VẬN HÀNH VIÊN — nó nêu tên CSDL, đĩa, tunnel — nên
#: nó đứng sau đăng nhập một cách có chủ ý (xem `server/routes/status.py`).
NGOAI_LE_KHONG_CONG_KHAI = frozenset({"/status"})


def test_dung_so_trang_du_kien_duoc_do(khach_en):
    """Đếm xem phép đo ở trên **thật sự chạm** vào bao nhiêu trang.

    🔴 VÌ SAO CẦN. `pytest.skip` đọc như xanh. Một dòng `12 passed, 1 skipped`
       và một dòng `8 passed, 5 skipped` trông giống nhau ở cuối màn hình, mà
       cái thứ hai là một phép đo **không đo gì** — đúng thứ đã xảy ra 25/08
       khi tôi để `follow_redirects=False` và middleware ngôn ngữ trả `302` cho
       mọi trang.

    ⭐ Luật: **một phép kiểm bỏ qua phải KHÓ bỏ qua hơn một phép kiểm đỏ.**
       Đỏ thì kêu; bỏ qua thì im. Nên số trang bỏ qua phải được khẳng định,
       không được để trôi.
    """
    do_duoc, bo_qua = [], []
    for duong in TRANG_CONG_KHAI_API:
        r = khach_en.get("/en" + duong)
        (bo_qua if "/login" in str(r.url) else do_duoc).append(duong)

    assert set(bo_qua) == set(NGOAI_LE_KHONG_CONG_KHAI), (
        "Tap trang KHONG cong khai da doi.\n"
        f"  du kien bo qua: {sorted(NGOAI_LE_KHONG_CONG_KHAI)}\n"
        f"  thuc te bo qua: {sorted(bo_qua)}\n"
        "Mot trang cong khai bong dung sau dang nhap = mat khach; mot trang\n"
        "van hanh vien bong dung cong khai = lo ten CSDL, dia, tunnel. Ca hai\n"
        "deu phai co nguoi doc dong nay truoc khi doi hang so.")

    assert len(do_duoc) >= 4, (
        f"chi con {len(do_duoc)} trang duoc do ({do_duoc}) — phep do dang teo lai")
