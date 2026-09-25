"""N-03 trên TRÌNH DUYỆT THẬT — `TestClient` không trả lời được câu hỏi thật.

## Vì sao `test_3002` chưa đủ

`test_3002` render trang qua `TestClient` và tìm chuỗi `"44"` trong HTML. Nó thật
hơn một phép kiểm tĩnh, nhưng nó **không chạy CSS và không chạy JS**, nên nó
không trả lời được câu hỏi khách quan tâm: *"con số 44 có ĐỌC ĐƯỢC trên màn hình
không"*.

⛔ Một con số nằm trong HTML mà bị `overflow:hidden` cắt, hay nằm trong một
   `<details>` **đóng**, thì **có trong HTML mà không có trên màn hình**. Đúng loại
   lỗi mà luật 7 của `CLAUDE.md` tồn tại để chặn — và đúng loại mà một `assert "44"
   in html` sẽ **xanh** trong khi khách không thấy gì.

⇒ Tệp này dựng một server THẬT (uvicorn, cổng tự chọn), mở bằng **Chromium
  thật**, và kiểm ba thứ `TestClient` không thể:

    1. hai con số **hiển thị thật** (`is_visible`, không phải `in html`);
    2. **không lỗi console**, không request nào hỏng;
    3. khối bằng chứng **mở sẵn** — phải bấm mới thấy thì khách sẽ không thấy.

## 🔴 25/09: con số 44 bị LẬT NGƯỢC 24/09 — đây là kỳ vọng CŨ, không phải lỗi GUI

`test_3002` đã lật `test_man_khach_KHONG_con_noi_44_tren_95_vi_THUOC_DO_HONG` từ
24/09 (`5ff00f26`): `qc_ai.khai_cho_khach()` giờ trả `False` MẶC ĐỊNH — bộ chấm
ngữ nghĩa gán 45,0% cho cả bản dịch NGƯỜI CHUYÊN NGHIỆP nên không phân biệt được
bản của ta với một bản hoàn hảo, và chủ dự án chốt KHÔNG khai con số đó cho khách
tới khi báo động giả đo được xuống dưới 15%. Tệp này (`test_3003`, tạo cùng ngày
24/09 lúc 10:23, TRƯỚC lúc `5ff00f26` commit 19:07) chưa từng được cập nhật theo
lượt lật đó — `test_khach_DOC_DUOC_con_so_44_tren_man_hinh` gốc đòi khối "Soát
nghĩa bản dịch" hiện với 44/95, điều mà `khai_cho_khach() is False` cấm hẳn ở
tầng template (`{% if bang_chung.ngu_nghia %}`), bất kể seed dữ liệu gì. Đã đổi
tên + LẬT CHIỀU bài đó cho khớp `test_3002`, giữ nguyên phần giá trị riêng của
tệp này: xác minh bằng CHROMIUM THẬT (không phải `in html`) rằng khối đó thật sự
KHÔNG hiện trên màn hình.

## ⚠️ Phần này KHÔNG đóng, và phải nói ra

Phần còn lại của luật 7 là *"chốt trên `https://app.lttstudios.com`"* (loopback bỏ
qua Cloudflare). ⛔ Nó **không** chờ P-01: năm bảng `asv_*` đã có trên production;
ASV 404 là do **cờ tính năng** `LTT_AUTO_SCAN_VIDEO`, và bật cờ đó **là mở cho
khách** — §24 của đề bài cấm. Nên việc còn mở là *"chốt trên tên miền thật — chờ
chủ dự án cho mở khách"*, không phải *"chờ bảng"*.

## Đăng nhập bằng COOKIE, không gõ mật khẩu

Lấy cookie phiên từ `TestClient` đã đăng nhập rồi nạp vào context của trình duyệt.
⛔ Một bộ kiểm không được đòi một mật khẩu.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

pytest.importorskip("playwright", reason="chua cai playwright (opt-in)")
pytest.importorskip("uvicorn")

from tests import test_2101_asv_gui_bang_chung_chat_luong as _g  # noqa: E402
from tests import test_3002_asv_man_khach_noi_ra_44_va_85 as _n3  # noqa: E402
from tests import test_423_asv_giao_dien as _mt  # noqa: E402

moi_truong = _mt.moi_truong


def _cong_ranh() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = int(s.getsockname()[1])
    s.close()
    return cong


@pytest.fixture()
def trang_that(moi_truong, tmp_path):  # noqa: F811
    """Dựng server THẬT + Chromium THẬT, trả `(page, loi_console, req_hong)`."""
    import uvicorn
    from playwright.sync_api import sync_playwright

    app, a, csrf, _b, _csrf_b = moi_truong
    run_id = _g._tao(a, csrf, tmp_path)
    _g._gieo(run_id, _n3.SO_LUOT_B)
    _n3._gieo_so_cai_con_lai(run_id, 85)

    cong = _cong_ranh()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=cong, log_level="warning")
    sv = uvicorn.Server(cfg)
    luong = threading.Thread(target=sv.run, daemon=True)
    luong.start()
    het = time.time() + 30
    while not sv.started and time.time() < het:
        time.sleep(0.1)
    assert sv.started, "uvicorn khong khoi dong trong 30 giay"

    loi_console: list = []
    req_hong: list = []
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 1280, "height": 900})
            # Cookie phien lay tu `TestClient` da dang nhap — khong go mat khau.
            ck = [{"name": k, "value": v, "domain": "127.0.0.1", "path": "/"}
                  for k, v in a.cookies.items()]
            if ck:
                ctx.add_cookies(ck)
            page = ctx.new_page()
            page.on("console", lambda m: (m.type == "error"
                                          and loi_console.append(m.text)))
            page.on("requestfailed",
                    lambda r: req_hong.append(f"{r.method} {r.url}"))
            page.on("response", lambda r: (r.status >= 400
                                           and req_hong.append(
                                               f"{r.status} {r.url}")))
            page.goto(f"http://127.0.0.1:{cong}/auto-scan-video/run/{run_id}",
                      wait_until="networkidle", timeout=30000)
            yield page, loi_console, req_hong
            br.close()
    finally:
        sv.should_exit = True
        luong.join(timeout=10)


def _o_chua(page, chu: str):
    """Ô nhỏ nhất còn HIỂN THỊ và chứa `chu`. `None` khi không có ô nào hiện."""
    for o in page.get_by_text(chu, exact=False).all():
        if o.is_visible():
            return o
    return None


def test_khach_KHONG_thay_con_so_44_vi_THUOC_DO_HONG(trang_that):
    """🔴 N-03 bị LẬT NGƯỢC 24/09 (`5ff00f26`, xem docstring đầu tệp và
    `test_3002...test_man_khach_KHONG_con_noi_44_tren_95_vi_THUOC_DO_HONG`) —
    CHƯA đóng, chỉ đổi CHIỀU: khối "Soát nghĩa bản dịch" ⛔ KHÔNG được phép hiện,
    vì bộ chấm ngữ nghĩa (`TI_LE_BAO_DONG_GIA_DA_DO=45%`) không phân biệt được
    bản dịch của ta với một bản dịch hoàn hảo của người.

    ⭐ Cổng là một PHÉP TÍNH từ số đã đo (`qc_ai.khai_cho_khach`), không phải cờ
       bật tay — hạ được báo động giả xuống ngưỡng thì cổng tự bật True và
       CHÍNH bài này tự đỏ. Lúc đó lật bài về bản N-03 gốc (đòi Chromium thật
       ĐỌC ĐƯỢC 44/95 trên màn hình), ⛔ đừng chỉ xoá phép kiểm.
    """
    from apps.auto_scan_video import qc_ai

    assert qc_ai.khai_cho_khach() is False, (
        "Bao dong gia da ve duoi nguong — lat bai nay ve ban N-03 goc (doi "
        "Chromium that DOC DUOC 44/95 tren man hinh), dung xoa no.")
    page, _loi, _hong = trang_that
    # ⛔ `is_visible`, khong phai `"44" not in html`: phai xac minh bang CHINH
    #    Chromium rang khoi do khong ANH HUONG man hinh that, khong chi rang no
    #    vang trong HTML tinh — dung ly do tep nay ton tai (xem docstring dau
    #    tep). Neu template render khoi do o dang AN (vd trong <details> dong)
    #    thay vi bo hoan toan, `_o_chua` (loc `is_visible()`) van tra None dung.
    o = _o_chua(page, "Soát nghĩa bản dịch")
    assert o is None, (
        "khoi 'Soat nghia ban dich' HIEN tren man hinh THAT trong khi "
        "qc_ai.khai_cho_khach() con dang False — template co the dang khong "
        "doc cong khai_cho_khach()")


def test_khach_DOC_DUOC_so_85_muc_con_chua_sua(trang_that):
    page, _loi, _hong = trang_that
    o = _o_chua(page, "Còn chưa sửa")
    assert o is not None, "khoi 'Con chua sua' KHONG hien tren man hinh"
    van = o.evaluate("e => e.closest('li') ? e.closest('li').innerText : e.innerText")
    assert "85" in van, van


def test_khoi_bang_chung_MO_SAN_chu_khong_phai_bam_moi_thay(trang_that):
    """⛔ Phải bấm mới thấy thì khách sẽ không thấy, và N-03 CHƯA đóng.

    Kiểm bằng `<details open>` chứ không bằng mắt: nếu khối nằm trong một
    `<details>` đóng thì `is_visible()` của phần thân trả False, nhưng một ngày
    nào đó ai đó bọc nó lại và chỉ phép kiểm này kêu.
    """
    page, _loi, _hong = trang_that
    assert _o_chua(page, "Bằng chứng chất lượng") is not None
    # ⛔ `textContent`, KHONG `innerText`. Do that 24/09: ban dau dong nay dung
    #    `innerText`, va khi TIEM dung loi no phai bat (boc khoi ngu nghia vao mot
    #    `<details>` DONG) no van **XANH** — vi `innerText` cua Chromium **bo qua
    #    noi dung bi an**, nen mot khoi dong co `innerText` rong va phep loc khong
    #    bao gio khop.
    #
    # 🔑 Tuc mot phep kiem viet ra DE bat mot thu, chay bang mot API khong thay thu
    #    do. `textContent` doc ca DOM ke ca phan an — do moi la cai ta can o day.
    dong = page.evaluate(
        "() => Array.from(document.querySelectorAll('details'))"
        "  .filter(d => !d.open && d.textContent.includes('Soát nghĩa'))"
        "  .map(d => d.textContent.replace(/\s+/g, ' ').slice(0, 60))")
    assert not dong, f"khoi ngu nghia nam trong <details> DONG: {dong}"


def test_trang_khong_co_LOI_CONSOLE_va_khong_request_nao_hong(trang_that):
    """Hai thứ `TestClient` không bao giờ thấy: JS lỗi, và asset 404.

    ⚠️ Đổi CSS/JS tĩnh thì phải cache-bust (`?v={{ asset_ver }}`,
       `server/templating.py:ASSET_VER`) — một asset 404 hoặc một bản CSS cũ đều
       hiện ra ở đây chứ không hiện ở `TestClient`.
    """
    _page, loi, hong = trang_that
    assert not loi, f"loi console: {loi}"
    assert not hong, f"request hong: {hong}"
