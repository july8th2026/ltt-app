"""Làn `asv-gui` — ba khoảng trống của GIAO DIỆN, mỗi cái một câu hỏi CUỐI.

Ba thứ được sửa ở làn này, và cả ba đều là **năng lực đã có mà không ai đi tới
được** — đúng hình dạng lỗi `L_GUI.md` §1 đã đặt tên là *"ô chết"*:

1. 🔴 **`.srt` được giao mà không tải về được.** `giai_doan_ket_xuat` sinh nó,
   gọi nó bằng tên *"MỘT BAN GIAO"*, và cố tình cho nó **không có hạn** để nửa
   bàn giao không tự biến mất sau 30 ngày. Rồi `khoa_ket_qua` lọc `.mp4`, và đó
   là **đường duy nhất** màn hình của khách có. Khách xin xuất SRT, trả tiền cho
   nó, và không bao giờ nhận được nó.

2. **Thẻ lịch sử không phân biệt được với thẻ kế.** Hai sự thật (trạng thái +
   giờ) trả lời được *"tôi đã chạy bao nhiêu lần"* nhưng không trả lời được
   *"lần nào là lần tôi muốn"*.

3. **Nút chính im lặng.** Nó bật sẵn, và `required` của trình duyệt trả lời thay
   — bằng một bong bóng ở đầu trang, cách chỗ khách vừa bấm cả một màn hình.

## ⚠️ Mỗi bài hỏi câu hỏi CUỐI, không hỏi một mắt xích

`test_2100` đã ghi bài học này: một ô chết đi qua **mọi** phép kiểm đơn lẻ, vì
mỗi phép chỉ hỏi một mắt xích và mắt xích nào cũng đúng. Nên bài 1 dưới đây
không hỏi *"có hàm `khoa_phu_de` không"* mà hỏi *"một tệp `.srt` đã giao có đi
tới được tay khách không"* — câu hỏi duy nhất một ô chết không trả lời được.
"""
from __future__ import annotations

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

#: Nội dung `.srt` gieo vào kho. Một tệp phụ đề thật, nhỏ nhất còn hợp lệ.
SRT = ("1\n00:00:00,000 --> 00:00:01,000\nXin chào.\n\n")


def _tao(a, csrf, tmp_path, **them) -> str:
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    r = _mt._tao_run_cho(a, csrf, tmp_path, **them)
    assert r.status_code == 200, r.text[:400]
    return str(r.url).rstrip("/").rsplit("/", 1)[-1]


def _gieo_ket_xuat(run_id: str, *, co_srt: bool) -> None:
    """RENDER xong, với `.mp4` và (tuỳ chọn) `.srt` NẰM THẬT trong kho.

    ⚠️ Ghi vào kho chứ không chỉ ghi khoá vào `outputs`: một bài chỉ gieo khoá sẽ
       xanh ở tầng "có hiện nút không" và **đỏ ở chỗ tải thật** — tức nó sẽ đo
       đúng cái nửa không quan trọng.
    """
    import platform_core.db as dbmod
    from platform_core.storage import get_storage

    from apps.auto_scan_video import pipeline, tables as T

    kho = get_storage()
    khoa = []
    for duoi, du_lieu, kieu in (("mp4", b"\x00mp4", "video/mp4"),
                                ("srt", SRT.encode("utf-8"),
                                 "application/x-subrip")):
        if duoi == "srt" and not co_srt:
            continue
        k = f"asv/{run_id}/render/ban-giao.{duoi}"
        kho.put(k, __import__("io").BytesIO(du_lieu), content_type=kieu)
        khoa.append(k)

    db = next(dbmod.get_session())
    try:
        s = (db.query(T.AsvStage)
             .filter(T.AsvStage.run_id == run_id,
                     T.AsvStage.stage == pipeline.RENDER).one())
        s.status = "succeeded"
        s.outputs = {"stage": pipeline.RENDER, "khoa_asset": khoa}
        # ⚠️ RENDER xong KHONG lam `run.status` thanh `done` — khoi ban giao cua
        #    `asv_tien_do.html` treo o trang thai cua RUN. Mot ban gieo chi dat
        #    giai doan se do voi mot thong bao khong nhac gi toi `run.status`.
        db.get(T.AsvRun, run_id).status = "done"
        db.commit()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  1. `.srt` đã giao thì ĐẾN ĐƯỢC tay khách
# ══════════════════════════════════════════════════════════════════════════════

def test_srt_da_giao_thi_KHACH_TAI_VE_duoc(moi_truong, tmp_path):
    """🔑 Câu hỏi CUỐI: tệp đã giao có đi tới được tay khách không.

    ⛔ Không hỏi *"có route không"* — một route tồn tại mà không nút nào dẫn tới
       vẫn là một ô chết, chỉ dịch chỗ.
    """
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo_ket_xuat(run_id, co_srt=True)

    # (a) Màn hình có một đường dẫn tới nó.
    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert f"/auto-scan-video/run/{run_id}/tai-phu-de" in html, (
        "man mot lan chay khong co duong nao dan toi tep `.srt` da giao")

    # (b) Và đường đó giao đúng tệp, như một tệp tải về.
    r = a.get(f"/auto-scan-video/run/{run_id}/tai-phu-de")
    assert r.status_code == 200, r.text[:300]
    assert r.text == SRT
    assert "attachment" in r.headers.get("content-disposition", ""), (
        "`.srt` mo trong tab thay vi tai ve — khach can nap no vao trinh dung phim")
    assert r.headers["content-disposition"].endswith('.srt"')


def test_khong_co_srt_thi_KHONG_hua_mot_nut(moi_truong, tmp_path):
    """⛔ Một nút "Tải phụ đề" luôn hiện là một nút 404 cho phần lớn lần chạy.

    ⚠️ Và câu hỏi phải hỏi theo hình dạng `co_phu_de`, không theo *"khách có xin
       xuất SRT không"*: một yêu cầu xuất SRT không chứng minh được tệp ĐÃ được
       giao (RENDER có thể chưa xong).
    """
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo_ket_xuat(run_id, co_srt=False)

    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "/tai-phu-de" not in html
    assert a.get(f"/auto-scan-video/run/{run_id}/tai-phu-de").status_code == 404


def test_srt_cua_nguoi_khac_KHONG_tai_ve_duoc(moi_truong, tmp_path):
    """404 chứ không 403 — 403 xác nhận rằng `run_id` đó có thật."""
    _app, a, csrf, b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _gieo_ket_xuat(run_id, co_srt=True)

    r = b.get(f"/auto-scan-video/run/{run_id}/tai-phu-de")
    assert r.status_code == 404, f"B nhan {r.status_code}"


def test_duong_tai_KHONG_nhan_khoa_tu_client(moi_truong):
    """⛔ Một `?key=` ở đây là đúng hình dạng một lỗ IDOR.

    Đọc AST thay vì gọi route: một route có thể hôm nay từ chối `key` vì handler
    chưa khai nó, rồi ai đó thêm tham số ấy vào *"cho tiện gỡ lỗi"*.
    """
    import ast
    import inspect

    from apps.auto_scan_video import routes

    ham = ast.parse(inspect.getsource(routes.tai_phu_de)).body[0]
    ten = [a.arg for a in ham.args.args]
    assert "key" not in ten and "khoa" not in ten, (
        f"`tai_phu_de` nhan khoa tu client: {ten}")


# ══════════════════════════════════════════════════════════════════════════════
#  2. Thẻ lịch sử phân biệt được với thẻ kế
# ══════════════════════════════════════════════════════════════════════════════

def test_the_lich_su_PHAN_BIET_duoc_hai_lan_chay(moi_truong, tmp_path):
    """🔑 Hai lần chạy khác nhau ở cặp ngôn ngữ phải ĐỌC được là khác nhau.

    ⛔ Không hỏi "có hàm `the_lich_su` không": hỏi *"trang chính có nói ra sự
       khác biệt hay không"*.
    """
    _app, a, csrf, _b, _cb = moi_truong
    _tao(a, csrf, tmp_path, ten="x.mp4", ngon_ngu_nguon="zh",
         ngon_ngu_dich="vi")

    html = a.get("/auto-scan-video").text
    # Cặp ngôn ngữ của lần chạy đã lên thẻ, không chỉ trạng thái + giờ.
    assert "Tiếng Trung" in html and "Tiếng Việt" in html
    assert 'class="asv-the-lan"' in html, "the khong mang cap ngon ngu"
    assert 'class="asv-the-preset"' in html, "the khong mang kieu xu ly"


def test_ho_so_thieu_khoa_KHONG_lam_mot_dong_BIEN_MAT(moi_truong, tmp_path):
    """⚠️ Bài học V6 pha 07: `run.settings.get(...)` ở template làm một dòng biến
    mất im lặng khi hồ sơ thiếu khoá. `the_lich_su` đọc qua `cai_dat.doc`, tức
    mọi trường luôn có mặt — kể cả với một hồ sơ trước v3.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import features, tables as T

    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)

    db = next(dbmod.get_session())
    try:
        run = db.get(T.AsvRun, run_id)
        # Hồ sơ trước v3: không khoá ngôn ngữ nào.
        run.settings = {"preset": run.settings.get("preset", "")}
        db.commit()
        the = features.the_lich_su(db, run.owner_id)
    finally:
        db.close()

    assert len(the) == 1
    # ⭐ `vi` là một SỰ THẬT về hồ sơ cũ (V4–V6 chỉ sinh tiếng Việt), không phải
    #    một phép đoán — xem `cai_dat.CaiDat.ngon_ngu_dich`.
    assert the[0]["ngon_ngu_dich"] == "vi"
    assert the[0]["ngon_ngu_nguon"] == ""


# ══════════════════════════════════════════════════════════════════════════════
#  3. Thanh hành động: MỘT người ghi `disabled`, và nó nói ra lý do
# ══════════════════════════════════════════════════════════════════════════════

def test_nut_chinh_TAT_tu_may_chu_va_noi_ra_ly_do(moi_truong):
    """🔴 `disabled` phải có NGAY trong HTML, không do JS tắt sau khi nạp.

    Một nút bật sẵn rồi bị JS tắt là một nút khách **bấm được** trong khoảng
    giữa — và ở màn này một cú bấm là một lần chạy đã trả tiền.
    """
    import re

    _app, a, _csrf, _b, _cb = moi_truong
    html = a.get("/auto-scan-video").text

    nut = re.search(r"<button[^>]*id=\"asv-batdau\"[^>]*>", html)
    assert nut, "khong tim thay nut chinh"
    assert "disabled" in nut.group(0), (
        "nut chinh bat san — JS tat sau khi nap thi con mot khoang bam duoc")
    assert 'id="asv-batdau-vi-sao"' in html and "Chọn video để bắt đầu" in html


def test_CHI_MOT_module_ghi_disabled_cua_nut_chinh():
    """⛔ Hai người ghi một `disabled` thì người chạy sau MỞ LẠI cái người kia
    vừa đóng — đúng hình dạng lỗi `L_GUI.md` §6 đã từ chối một lần.

    ⚠️ Bài này hỏi phía ĐƯỜNG (không module nào khác được chạm thuộc tính ấy),
       không hỏi *"`thanh.js` có ghi không"* — câu sau vẫn xanh khi có kẻ thứ
       hai.

    🔴 **Và phép đo phải nhắm ĐÚNG thuộc tính, không nhắm "tệp có chữ
       `disabled`".** Bản đầu của bài này hỏi *"tệp có nhắc `asv-batdau` VÀ có
       một phép gán `.disabled` nào không"*, và nó đánh hỏng `tai_len.js` vì một
       dòng `oTep.disabled = true` — **ô chọn tệp**, một biến khác hoàn toàn,
       hoàn toàn đúng đắn. Một báo động giả ở một cổng là cách người ta học cách
       tắt cổng đó (xem `banh-coc-do-cach-go-thay-vi-do-tinh-chat`).

    ⇒ Nên nó tìm TÊN BIẾN nào giữ `#asv-batdau` trong từng tệp, rồi hỏi đúng
      `<biến>.disabled =`.
    """
    import re
    from pathlib import Path

    tm = Path(__file__).resolve().parents[1] / "server" / "static" / "asv"
    nguoi_ghi = []
    for tep in sorted(tm.glob("*.js")):
        van = tep.read_text(encoding="utf-8")
        bien = re.findall(
            r'var\s+(\w+)\s*=\s*document\.getElementById\(\s*"asv-batdau"\s*\)',
            van)
        for b in bien:
            if re.search(re.escape(b) + r"\s*\.\s*disabled\s*=", van):
                nguoi_ghi.append(tep.name)
                break
    assert nguoi_ghi == ["thanh.js"], (
        f"nhieu module ghi `disabled` cua nut chinh: {nguoi_ghi}")


def test_so_ly_do_la_KHOA_CHU_chu_khong_phai_cau_tieng_Viet():
    """⛔ Một câu tiếng Việt trong `.js` là một câu KHÔNG BAO GIỜ dịch được, và
    nó sẽ đứng giữa một trang đã dịch hết (`test_2100` chốt luật này cho cả thư
    mục; bài này chốt riêng cho hai khoá mới của làn `asv-gui`).
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parents[1]
    mau = (goc / "apps" / "auto_scan_video" / "templates"
           / "asv_trang_chinh.html").read_text(encoding="utf-8")
    for khoa in ("chua_chon_video", "am_nen_da_tat"):
        assert f'"{khoa}"' in mau, f"khoa `{khoa}` khong co trong `#asv-chu`"


def test_tat_nhac_nen_thi_NOI_RA_vi_sao_hai_o_kia_xam_di():
    """🔑 `am_thanh.js` khoá hai ô khi khách bật "Tắt nhạc nền" — phép khoá đúng,
    cái thiếu là khách không được nói VÌ SAO. Một điều khiển xám đi không lý do
    đọc như một lỗi của trang.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parents[1]
    js = (goc / "server" / "static" / "asv"
          / "am_thanh.js").read_text(encoding="utf-8")
    assert "am_nen_da_tat" in js and "asv-am-vi-sao" in js, (
        "hai o bi khoa im lang — khong cau nao noi ra ly do")


def test_thanh_hanh_dong_DINH_o_moi_be_ngang():
    """🔴 Trước làn này thanh chỉ dính ở `<=640px`, và chú thích ở template ghi
    *"DINH day tren mobile"* như thể đó là cả ý định.

    Màn Studio dài hơn một khung nhìn ngay khi khách mở `Tuỳ chọn nâng cao`, nên
    trên màn hình rộng **chi phí và nút Bắt đầu cuộn ra ngoài tầm mắt** — đúng
    lúc khách quyết thì con số họ cần để quyết không còn trên màn hình.

    ⚠️ Đọc luật NGOÀI mọi `@media`: một luật `sticky` nằm trong `@media` là một
       luật chỉ đúng ở một bề ngang.
    """
    import re
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / "server" / "static"
           / "ltt.css").read_text(encoding="utf-8")
    # Cắt bỏ mọi khối `@media` trước khi tìm — phép đo phải hỏi luật CHUNG.
    ngoai = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    khoi = re.search(r"\.asv-thanh\{([^}]*)\}", ngoai)
    assert khoi, "khong con luat `.asv-thanh` ngoai `@media`"
    assert "position:sticky" in khoi.group(1), (
        "thanh hanh dong chi dinh trong mot `@media` — tuc chi dinh o mot be ngang")


def test_module_moi_duoc_KHAI_trong_danh_sach_cua_may_chu():
    """⛔ Một tệp `.js` không có trong `ASV_STUDIO_JS` là một tệp không bao giờ
    được nạp — trang vẫn chạy, chỉ thiếu đúng tính năng đó, và im lặng.
    """
    from server.templating import ASV_STUDIO_JS

    assert "asv/thanh.js" in ASV_STUDIO_JS
    # `nen.js` vẫn phải đứng trước: `thanh.js` gọi `ASV.khiDoiChan` lúc nạp.
    assert ASV_STUDIO_JS.index("asv/nen.js") == 0
