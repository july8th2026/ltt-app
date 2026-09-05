"""705 — vòng hỏi trạng thái job: một bản dùng chung, và tab ẩn thì ngừng hỏi.

## Phép đo dựng nên tệp này (05/09)

**Năm** chỗ tự viết vòng hỏi job, **không chỗ nào** xử lý `visibilitychange`:

    apps/taoanh/templates/image.html            setTimeout 1200ms
    apps/prompt_ai_ommi/templates/...html       setInterval 1600ms
    frontend/autosub-studio/src/StudioShell     setInterval
    frontend/chatltt/src/App.tsx                setInterval (hai chỗ)

Trong khi `server/templates/job_detail.html` — trang job của **chính nền tảng** —
đã làm đúng từ lâu: lùi theo cấp số nhân khi lỗi, hoà lại ngay khi tab hiện lại,
thử lại khi `online`, dừng hẳn khi rời trang.

⭐ Nên đây không phải một thiết kế mới. Đây là việc **ngưng để một bản đúng nằm
   im một chỗ**.

⚠️ Trên điện thoại nó không phải chuyện "cho gọn": một tab bị ẩn vẫn hỏi máy chủ
   **1,2 giây một lần** là pin và dung lượng 3G của khách chạy trong khi họ đang
   làm việc khác — còn job thì vẫn chạy ở máy chủ dù không ai hỏi.

## Hành vi đã đo trong trình duyệt thật

    tab hiện, nhịp 40ms, 260ms   -> 6 lượt hỏi
    tab ẩn,             260ms    -> 0 lượt hỏi
    hiện lại                     -> hỏi lại NGAY
    sau `dung()`                 -> 0 lượt

Tệp này chốt phần **cấu trúc** để bản đúng không bị bỏ lại lần nữa; phần hành vi
thuộc về ma trận trình duyệt (Phase G).
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
JS = GOC / "server" / "static" / "nhip_job.js"

#: Những trang tự dựng vòng hỏi job bằng JS nội tuyến. Danh sách này là **tập
#: hợp cần canh**, không phải một con số — thêm trang thứ ba vào đây là đúng.
TRANG_CO_VONG_HOI = (
    "apps/taoanh/templates/image.html",
    "apps/prompt_ai_ommi/templates/prompt_ai_ommi.html",
)


def _xoa(ra: list, i: int, j: int) -> None:
    for k in range(i, j):
        if ra[k] != "\n":
            ra[k] = " "


def _boc_cap(s: str, ra: list, dau: int, cuoi: int, cap) -> None:
    """Bóc các cặp mở/đóng trong đoạn `[dau, cuoi)` của `s`."""
    i = dau
    while i < cuoi:
        mo = next((c for c in cap if s.startswith(c[0], i)), None)
        if mo:
            j = s.find(mo[1], i + len(mo[0]))
            j = cuoi if j < 0 or j > cuoi else j + len(mo[1])
            _xoa(ra, i, j)
            i = j
        else:
            i += 1


_KHOI_MA = re.compile(r"<(script|style)\b[^>]*>", re.I)


def boc_chu_thich(s: str) -> str:
    """Bỏ chú thích, giữ nguyên độ dài (để mọi chỉ số vẫn trỏ đúng chỗ).

    🔴 CHÚ THÍCH JS/CSS CHỈ ĐƯỢC BÓC BÊN TRONG `<script>` VÀ `<style>`.

       Bản đầu của hàm này bóc `/* */` trên **cả tệp**, và nó nuốt mất 31.605 ký
       tự của `prompt_ai_ommi.html` — vì thuộc tính HTML

           accept="image/*,video/*,audio/*"

       mở một "chú thích" mà dấu đóng gần nhất nằm tận trong khối `<style>` phía
       dưới. Phép kiểm đỏ với một thông báo hoàn toàn vô nghĩa: *"trang không nạp
       nhip_job.js"* — trong khi thẻ `<script>` ấy nằm ngay đó.

    ⭐ Bài học đúng bằng chữ trong memory: **đọc thứ đại diện thay vì đọc thứ
       thật**. Một bộ bóc chú thích chạy trên chuỗi HTML đang đọc một *biểu diễn*,
       không đọc *cây tài liệu* — nên nó phải biết mình đang ở trong vùng nào.
    """
    ra = list(s)
    # 1) Chú thích Jinja: hợp lệ ở mọi nơi trong tệp.
    _boc_cap(s, ra, 0, len(s), (("{#", "#}"),))
    # 2) Chú thích JS/CSS: CHỈ trong thân `<script>`/`<style>`.
    for m in _KHOI_MA.finditer(s):
        het = s.lower().find("</" + m.group(1).lower(), m.end())
        het = len(s) if het < 0 else het
        _boc_cap(s, ra, m.end(), het, (("/*", "*/"), ("//", "\n")))
    return "".join(ra)


def test_bo_boc_chu_thich_that_su_boc():
    """Nếu nó không bóc, mọi phép kiểm dưới đây xanh giả — chính các chú thích
    trong `image.html` và `nhip_job.js` đều nhắc `setInterval` để giải thích."""
    vao = "<script> a /* setInterval */ b // setInterval\n c </script> {# setInterval #} d"
    ra = boc_chu_thich(vao)
    assert "setInterval" not in ra
    assert len(ra) == len(vao)


def test_bo_boc_KHONG_coi_accept_image_sao_la_chu_thich():
    """Chốt đúng lỗi đã xảy ra 05/09, để nó không quay lại.

    `accept="image/*"` là một thuộc tính HTML hợp lệ và cực kỳ phổ biến ở mọi
    app có tải ảnh lên. Một bộ bóc coi nó là `/*` sẽ nuốt phần còn lại của tệp
    và làm phép kiểm đỏ ở một chỗ chẳng liên quan gì.
    """
    vao = ('<input accept="image/*,video/*"> <script src="/static/nhip_job.js"></script>'
           ' <style>.a{color:red}</style>')
    ra = boc_chu_thich(vao)
    assert "nhip_job.js" in ra, "thuộc tính `accept` vẫn nuốt mất thẻ script"
    assert "color:red" in ra


# ── Bản dùng chung phải có đủ bốn cái cửa ─────────────────────────────────

def test_nhip_job_ton_tai_va_xu_ly_du_bon_su_kien():
    assert JS.exists(), "server/static/nhip_job.js biến mất"
    s = boc_chu_thich(JS.read_text(encoding="utf-8"))
    for sk in ("visibilitychange", "pageshow", "online", "beforeunload"):
        assert sk in s, f"`nhip_job.js` không còn nghe `{sk}`"
    assert "document.hidden" in s, "không còn kiểm tab ẩn"


def test_nhip_job_lui_theo_cap_so_nhan_khi_loi():
    """Một máy chủ đang chật mà bị hỏi dày hơn là một máy chủ chật hơn."""
    s = boc_chu_thich(JS.read_text(encoding="utf-8"))
    assert re.search(r"nhip\s*\*\s*2", s), "không còn nhân đôi nhịp khi lỗi"
    assert "nhipToiDa" in s, "không còn trần khi lùi"


def test_nhip_job_duoc_cache_bust():
    """Static đi qua Cloudflare có TTL. Đổi tệp mà URL không đổi thì người dùng
    nhận bản cũ tới khi hết TTL — `CLAUDE.md` quy tắc 6, và nó đã sập thật một
    lần với `ltt.css`."""
    s = (GOC / "server" / "templating.py").read_text(encoding="utf-8")
    m = re.search(r"TAI_SAN_CO_VERSION\s*=\s*\(([^)]*)\)", s, re.S)
    assert m and "nhip_job.js" in m.group(1), (
        "`nhip_job.js` chưa nằm trong `TAI_SAN_CO_VERSION` — đổi tệp sẽ không "
        "đổi `asset_ver`, và Cloudflare phục vụ bản cũ")


# ── Các trang tự dựng vòng hỏi phải dùng bản chung ────────────────────────

@pytest.mark.parametrize("duong", TRANG_CO_VONG_HOI)
def test_trang_dung_ban_chung_chu_khong_tu_dung_vong(duong):
    s = boc_chu_thich((GOC / duong).read_text(encoding="utf-8"))
    assert "LTT.nhipJob" in s, f"{duong} không dùng `LTT.nhipJob`"
    assert "nhip_job.js" in s, f"{duong} không nạp `nhip_job.js`"
    con = re.findall(r"setInterval\s*\(", s)
    assert not con, (
        f"{duong} còn `setInterval` — nếu đó là một vòng hỏi job thì nó không "
        "biết tab đang ẩn; nếu là việc khác thì hãy nói rõ trong chú thích và "
        "sửa phép kiểm này")


@pytest.mark.parametrize("duong", TRANG_CO_VONG_HOI)
def test_nhip_job_KHONG_duoc_defer(duong):
    """`defer` chạy SAU mọi script nội tuyến, mà script nội tuyến gọi nó NGAY.

    ⚠️ Bản đầu của lượt sửa này đặt `defer` và nó cho `TypeError: LTT.nhipJob is
       not a function` ngay khi mở trang. Tệp chỉ ĐỊNH NGHĨA một hàm, không chạm
       DOM, nên nó không cần `defer`.
    """
    s = (GOC / duong).read_text(encoding="utf-8")
    m = re.search(r"<script[^>]*nhip_job\.js[^>]*>", s)
    assert m, f"{duong} không nạp `nhip_job.js`"
    assert "defer" not in m.group(0), (
        f"{duong} nạp `nhip_job.js` với `defer` — script nội tuyến gọi "
        "`LTT.nhipJob` trước khi nó tồn tại")


def test_ban_dung_goc_van_con_de_doi_chieu():
    """`job_detail.html` là nơi bản đúng ra đời. Nếu nó mất bốn cái cửa ấy thì
    `nhip_job.js` mất luôn chỗ để đối chiếu — và không ai biết đã mất."""
    s = boc_chu_thich(
        (GOC / "server" / "templates" / "job_detail.html").read_text(encoding="utf-8"))
    for sk in ("visibilitychange", "online", "beforeunload"):
        assert sk in s, f"`job_detail.html` không còn nghe `{sk}`"
