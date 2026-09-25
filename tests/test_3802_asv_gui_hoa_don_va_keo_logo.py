"""Làn `asv-gui` — ba chỗ giá phẳng chạm vào GIAO DIỆN, + kéo-thả logo.

## 🔴 Khối hoá đơn đã BIẾN MẤT IM LẶNG một lần

Bản trước của `asv_chi_tiet.html` đọc `chi_phi.chi_phi_theo_nang_luc`. Giá phẳng
bỏ khoá ấy; Jinja trả `Undefined` cho một khoá vắng; `Undefined` là **falsy**;
`{% if %}` chọn nhánh `else` và **cả bảng hoá đơn tự ẩn**.

⛔ Trang không vỡ. Không một lỗi nào. Không ai biết. Khách chỉ **không còn thấy
mình trả bao nhiêu** — và nó xảy ra ở đúng chỗ đắt nhất của sản phẩm.

⚠️ Cùng họ lỗi với `N-47` (kẹp im lặng), `N-51` (fail-open), `N-55`: **hỏng mà
không kêu**. Nên bài trong tệp này hỏi *"khách có ĐỌC được con số không"*, ⛔
không hỏi *"template có nhắc tên khoá mới không"* — câu sau vẫn xanh khi khối
lại tự ẩn vì một lý do khác.
"""
from __future__ import annotations

from pathlib import Path

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

GOC = Path(__file__).resolve().parents[1]
MAU = GOC / "apps" / "auto_scan_video" / "templates"
JS = GOC / "server" / "static" / "asv"


def _bo_chu_thich(van: str, kieu: str) -> str:
    """Bỏ chú thích trước khi tìm một cái tên trong mã.

    🔴 **Hai bài dưới đây đã BÁO ĐỘNG GIẢ vì thiếu hàm này**, và cả hai báo động
       đều nhắm vào chính những dòng chú thích giải thích *vì sao* cái tên ấy
       không còn được dùng. Một cổng bắn nhầm vào lời giải thích của chính nó là
       cách người ta học cách tắt cổng (`banh-coc-do-cach-go-thay-vi-do-tinh-chat`).

    ⇒ Phép đo phải hỏi về **mã**, không hỏi về **văn bản của tệp**.
    """
    import re

    if kieu == "jinja":
        return re.sub(r"\{#.*?#\}", "", van, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", van, flags=re.S)


def _tao(a, csrf, tmp_path, **them) -> str:
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    r = _mt._tao_run_cho(a, csrf, tmp_path, **them)
    assert r.status_code == 200, r.text[:400]
    return str(r.url).rstrip("/").rsplit("/", 1)[-1]


def _do_duoc_do_dai(run_id: str, giay: float) -> None:
    """Gieo phép đo độ dài THẬT vào `media_prepare` — đúng chỗ `features` đọc."""
    import platform_core.db as dbmod

    from apps.auto_scan_video import pipeline, tables as T

    db = next(dbmod.get_session())
    try:
        s = (db.query(T.AsvStage)
             .filter(T.AsvStage.run_id == run_id,
                     T.AsvStage.stage == pipeline.MEDIA_PREPARE).one())
        s.status = "succeeded"
        s.outputs = {"thoi_luong": giay}
        db.commit()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  1. Hoá đơn — câu hỏi là "khách ĐỌC được con số không"
# ══════════════════════════════════════════════════════════════════════════════

def test_khach_DOC_DUOC_mot_dong_hoa_don(moi_truong, tmp_path):
    """🔑 `190 giây` ⇒ làm tròn LÊN 4 phút ⇒ `4 × 10 = 40 credit`.

    ⭐ Ba con số cùng có mặt, không phải một: chỉ in `40 credit` thì khách phải
       **tin**; in cả `4 phút × 10 credit` thì họ **kiểm lại được** từ độ dài
       video đang nhìn. Đó là cả lý do giá phẳng thay bảng kê theo năng lực.
    """
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)
    _do_duoc_do_dai(run_id, 190.0)

    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "4 phút" in html and "10 credit" in html and "40 credit" in html


def test_chua_do_duoc_do_dai_thi_NOI_RA_chu_KHONG_bia_mot_phut(moi_truong,
                                                               tmp_path):
    """🔴 `so_phut`/`credit` là `None` khi chưa đo được độ dài.

    ⛔ *"chưa đo được"* khác *"video dài 0 giây"*, và gộp hai trạng thái vào một
       giá trị là một họ lỗi đã có tên trong kho này. Sàn tối thiểu là 1 phút,
       nên in `1 phút × 10 = 10 credit` ở đây sẽ **đọc như một hoá đơn thật** —
       và nó sai với phần lớn video.
    """
    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)   # chưa gieo `media_prepare`

    html = a.get(f"/auto-scan-video/run/{run_id}").text
    assert "Chưa đo được độ dài" in html
    assert "phút ×" not in html, "bia ra mot dong hoa don khi chua do duoc do dai"


def test_LUAT_LAM_TRON_hien_o_CA_HAI_ca(moi_truong, tmp_path):
    """Khách chưa đo được độ dài vẫn cần biết mình sẽ bị tính theo luật nào."""
    _app, a, csrf, _b, _cb = moi_truong
    chua = _tao(a, csrf, tmp_path)
    da = _tao(a, csrf, tmp_path, ten="b.mp4")
    _do_duoc_do_dai(da, 190.0)

    for run_id in (chua, da):
        html = a.get(f"/auto-scan-video/run/{run_id}").text
        assert "làm tròn lên phút" in html, f"{run_id} thieu luat lam tron"


def test_khoi_hoa_don_KHONG_TREO_vao_mot_khoa_co_the_VANG(moi_truong, tmp_path):
    """🔴 Bài chống tái diễn, và nó hỏi phía ĐƯỜNG.

    Lỗi cũ không phải "đọc sai tên khoá" — nó là **hình dạng** `{% if
    chi_phi.<khoá-có-thể-biến-mất> %}`: một khoá vắng cho `Undefined`, `Undefined`
    là falsy, và cả khối tự ẩn **không một tiếng động**.

    ⇒ Điều kiện của khối phải hỏi một câu về **dữ liệu** (*"đã đo được độ dài
      chưa"*), ⛔ không phải một câu về **sự tồn tại của khoá**. `hoa_don` luôn có
      mặt (`quan_sat` dựng nó vô điều kiện) và `da_do_do_dai` luôn là bool.
    """
    from apps.auto_scan_video import quan_sat  # noqa: F401  (tài liệu chỗ dựng)

    van = _bo_chu_thich((MAU / "asv_chi_tiet.html").read_text(encoding="utf-8"),
                        "jinja")
    assert "chi_phi.chi_phi_theo_nang_luc" not in van, (
        "van treo vao khoa da bi gia phang xoa")
    assert "hd.da_do_do_dai" in van, (
        "dieu kien cua khoi khong hoi ve DU LIEU — mot khoa vang se lam no tu an")


def test_hoa_don_LUON_co_mat_va_da_do_do_dai_LUON_la_bool(moi_truong, tmp_path):
    """Nửa máy chủ của bài trên: khối chỉ an toàn nếu `hoa_don` thật sự luôn có."""
    import platform_core.db as dbmod

    from apps.auto_scan_video import quan_sat, tables as T

    _app, a, csrf, _b, _cb = moi_truong
    run_id = _tao(a, csrf, tmp_path)

    db = next(dbmod.get_session())
    try:
        hd = quan_sat.tom_tat_cho_khach(db, db.get(T.AsvRun, run_id))["hoa_don"]
    finally:
        db.close()

    assert isinstance(hd["da_do_do_dai"], bool)
    assert hd["so_phut"] is None and hd["credit"] is None
    assert hd["don_gia"] and hd["luat_lam_tron"]


# ══════════════════════════════════════════════════════════════════════════════
#  2. Xem trước giá: MỘT con số, và không có dấu `~`
# ══════════════════════════════════════════════════════════════════════════════

def test_xem_truoc_doc_khoa_MOI_chu_khong_hai_khoa_tam_giu():
    """⚠️ `credit_thap`/`credit_cao` còn sống ở máy chủ **chỉ** để giao diện kịp
    đổi, và cả hai nay bằng `credit`. Đọc khoá cũ là giữ chúng sống — và giữ
    luôn màn hình in `~40–40`: một khoảng có bề rộng bằng không, vẫn xin lỗi
    trước bằng một dấu `~`.
    """
    js = _bo_chu_thich((JS / "xem_truoc.js").read_text(encoding="utf-8"), "js")
    assert "d.credit_thap" not in js and "d.credit_cao" not in js
    assert "d.credit" in js


def test_KHONG_con_dau_xap_xi_truoc_con_so_gia():
    """🔴 `~` là một lời **nói sai**, không chỉ một ký tự thừa: nó bảo khách
    *"áng chừng"* trong khi ta biết đúng con số — giá là một hàm của độ dài
    video nguồn, và độ dài đó đã đo xong trước khi họ bấm.
    """
    js = _bo_chu_thich((JS / "xem_truoc.js").read_text(encoding="utf-8"), "js")
    i = js.index("uocTien,")
    assert '"~"' not in js[i - 200:i + 200], "van con dau `~` canh con so gia"


def test_LUAT_LAM_TRON_len_duoc_cho_BAM(moi_truong):
    """🔑 Yêu cầu của chủ dự án, ⛔ không phải một tiện ích: *"một con số nhảy ra
    sau khi trừ tiền là cách nhanh nhất để mất lòng tin"*.

    Nên câu luật phải tới được **màn Studio** — chỗ khách bấm — chứ không chỉ
    nằm trong phản hồi của một route.
    """
    _app, a, _csrf, _b, _cb = moi_truong
    assert 'id="asv-uoc-luat"' in a.get("/auto-scan-video").text
    js = (JS / "xem_truoc.js").read_text(encoding="utf-8")
    assert "luat_lam_tron" in js


def test_cau_luat_KHONG_bi_chep_vao_giao_dien(moi_truong):
    """⛔ Đơn giá được điền vào câu **lúc chạy** (`gia.luat_lam_tron()`), nên một
    bản chép ở Jinja hay trong `.js` sẽ trôi ngay lần đầu ai đó sửa giá.
    """
    mau = _bo_chu_thich((MAU / "asv_trang_chinh.html").read_text(encoding="utf-8"),
                        "jinja")
    js = _bo_chu_thich((JS / "xem_truoc.js").read_text(encoding="utf-8"), "js")
    for van in (mau, js):
        assert "làm tròn lên phút" not in van, "cau luat bi chep vao giao dien"


# ══════════════════════════════════════════════════════════════════════════════
#  3. Kéo-thả logo — một phần tử, một chủ
# ══════════════════════════════════════════════════════════════════════════════

def test_lop_keo_logo_la_mot_phan_tu_RIENG(moi_truong):
    """🔴 `#asv-lop` có đúng MỘT chủ: `asv/vung.js`, và nó **xoá sạch** rồi dựng
    lại toàn bộ con của mình mỗi lần `veLai()`.

    Vẽ điểm kéo của logo vào chính lớp ấy là hai module cùng ghi một cây DOM —
    đúng họ lỗi làn này đã phải đóng lại một lần ở `#asv-batdau.disabled`.
    """
    _app, a, _csrf, _b, _cb = moi_truong
    assert 'id="asv-lop-logo"' in a.get("/auto-scan-video").text

    vung = _bo_chu_thich((JS / "vung.js").read_text(encoding="utf-8"), "js")
    logo = _bo_chu_thich((JS / "logo.js").read_text(encoding="utf-8"), "js")
    assert "asv-lop-logo" not in vung, "`vung.js` cham vao lop cua `logo.js`"
    assert 'getElementById("asv-lop")' not in logo, (
        "`logo.js` cham vao lop cua `vung.js`")
    assert "asv-lop-logo" in logo


def test_keo_va_o_SO_ghi_vao_CUNG_mot_cho():
    """⚠️ Kéo và gõ số là hai cách nhập cho **cùng** dữ liệu. Nếu bộ kéo không
    cập nhật ô số, hai chỗ trên màn hình nói hai con số khác nhau về cùng một
    logo — và khách không biết tin cái nào.

    ⛔ Và bộ kéo ⛔ không được vẽ lại cả danh sách để đồng bộ: vẽ lại huỷ các
       `<input type=file>`, tức **mất ảnh khách đã chọn**.
    """
    logo = _bo_chu_thich((JS / "logo.js").read_text(encoding="utf-8"), "js")
    assert "datOSo" in logo and "data-lg-o" in logo
    i = logo.index("function datOSo")
    than = logo[i:i + 500]
    assert "veDanhSachLogo" not in than, (
        "bo keo ve lai ca danh sach — se huy `<input type=file>` va mat anh")


def test_lop_keo_TRONG_SUOT_voi_con_tro_tru_chinh_diem_keo():
    """🔑 Lớp logo nằm **trên** `#asv-lop`. Không cho con trỏ đi xuyên qua thì nó
    nuốt mọi cú kéo vẽ vùng che **và** cả điều khiển của `<video>`.
    """
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    assert ".asv-lop-logo{pointer-events:none" in css
    assert ".asv-lg-keo{pointer-events:auto" in css
    # Đang vẽ vùng che thì tắt điểm kéo: hai công cụ cùng đòi một cú kéo trên
    # cùng một khung hình là một chỗ khách bấm nhầm chắc chắn.
    assert ".asv-dang-ve .asv-lg-keo{pointer-events:none}" in css


def test_o_xem_truoc_logo_dung_TI_LE_THAT_chu_khong_doan():
    """⛔ Một ô xem trước sai hình dạng là một ô xem trước **nói dối** về kết quả.

    `overlay` đặt góc TRÊN-TRÁI ở `(W*x, H*y)` và `scale=w=rong*W:h=-2` giữ
    nguyên tỉ lệ ảnh ⇒ chiều cao **suy ra được**. Chưa biết tỉ lệ thì vẽ một ô
    neo, ⛔ không bịa một kích thước.
    """
    logo = (JS / "logo.js").read_text(encoding="utf-8")
    assert "naturalHeight / im.naturalWidth" in logo
    i = logo.index("function caoHop")
    assert "return 0;" in logo[i:i + 600], (
        "chua biet ti le ma van ve mot hop co kich thuoc — tuc bia ra no")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Hai lỗi TRÌNH DUYỆT bắt được mà không phép kiểm nào trong kho thấy
# ══════════════════════════════════════════════════════════════════════════════

def _png(w: int, h: int) -> bytes:
    """PNG thật, CRC đúng. ⛔ Không dùng một chuỗi base64 gõ tay: bản đầu của
    lượt này làm thế và cho ra một tệp **hỏng CRC** — trình duyệt từ chối giải
    mã, và suốt mười lăm phút nó trông y hệt một lỗi trong mã sản phẩm.
    """
    import struct
    import zlib

    raw = b"".join(b"\x00" + bytes([220, 50, 40]) * w for _ in range(h))

    def chunk(t: bytes, b: bytes) -> bytes:
        return (struct.pack(">I", len(b)) + t + b
                + struct.pack(">I", zlib.crc32(t + b) & 0xffffffff))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def test_hang_rao_anh_NHAN_mot_anh_HOP_LE(moi_truong, tmp_path):
    """🔴 **Hàng rào này từng đóng kín, và nó đóng kín IM LẶNG.**

    `assets.kiem_hop_le` gọi `image_input.validate_reference(du_lieu, "")`, và
    hàm ấy bắt đầu bằng `if mime not in ALLOWED_REFERENCE_MIME: raise`. `""`
    không bao giờ nằm trong tập đó ⇒ **mọi ảnh đều bị từ chối**, luôn luôn.

    ⇒ Tính năng logo chưa từng chạy hết đường một lần nào: khách dán logo và
      nhận một trang **500**. Không phép kiểm nào trong kho hỏi câu này — chúng
      hỏi *"ảnh hỏng có bị chặn không"*, và câu đó vẫn xanh với một hàng rào
      chặn tất cả.

    ⭐ Nên bài này hỏi chiều NGƯỢC LẠI: **một ảnh đúng có đi qua được không.**
       Đó là câu hỏi mà một hàng rào đóng kín không trả lời được.
    """
    import io

    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets
    from apps.auto_scan_video.tables import KIND_ANH

    kho = get_storage()
    khoa = "asv-staging/x/y/logo/z.png"
    kho.put(khoa, io.BytesIO(_png(160, 80)), content_type="image/png")

    co, _bam = assets.kiem_hop_le(kho, khoa, kind=KIND_ANH)
    assert co > 0


def test_hang_rao_anh_VAN_chan_mot_tep_KHONG_phai_anh(moi_truong, tmp_path):
    """⚠️ Đối chứng cho bài trên. Không có nó, một "sửa" biến hàng rào thành
    hàng rào **mở toang** vẫn làm bài trên xanh — và đó là cách một cổng chất
    lượng bị nới trong im lặng.
    """
    import io

    import pytest
    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets
    from apps.auto_scan_video.tables import KIND_ANH

    kho = get_storage()
    khoa = "asv-staging/x/y/logo/gia.png"
    kho.put(khoa, io.BytesIO(b"day khong phai anh"), content_type="image/png")

    with pytest.raises(assets.AssetError):
        assets.kiem_hop_le(kho, khoa, kind=KIND_ANH)


def test_anh_logo_QUA_NHO_cho_mot_CAU_chu_khong_phai_500(moi_truong, tmp_path):
    """🔴 Đo trên trình duyệt: một logo 40×20 — dưới sàn 64×64 của nền tảng — làm
    khách nhận *"Máy chủ gặp sự cố"*.

    ⛔ Đó là câu trả lời **sai về ai có lỗi**: lỗi nằm ở tệp khách chọn, và họ
       sửa được trong ba giây — nếu ta nói ra.

    ⚠️ Và câu nói ra ⛔ không được mang khoá lưu trữ: `AssetError` viết
       `artifact anh khong hop le: asv-staging/…`, tức một đường dẫn nội bộ.
    """
    from apps.auto_scan_video import features

    _app, a, csrf, _b, _cb = moi_truong
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    from tests.fixtures.asv_media import tiny_mp4

    tep = tiny_mp4(tmp_path / "v.mp4", duration_s=1.0)
    with open(tep, "rb") as f:
        r = a.post("/auto-scan-video/tao",
                   data={"csrf_token": csrf, "che_do": "fit_original",
                         "giong_id": "Minh Đức", "preset": "smart_localize",
                         "logo": '[{"x":0.1,"y":0.1,"rong":0.15,"do_mo":1}]'},
                   files={"video": ("v.mp4", f, "video/mp4"),
                          "logo_anh": ("nho.png", _png(40, 20), "image/png")})

    # ⭐ `400` chu khong `200`: `_lai_voi_loi` dung lai chinh man Studio kem cau
    #    tu choi, va `routes.py:439` chon ma 400 cho no. Dieu bai nay chot la
    #    **khong phai 5xx**, va man hinh tra ve la BIEU MAU chu khong phai trang
    #    su co — tuc khach sua roi bam lai duoc ngay.
    assert 400 <= r.status_code < 500, (
        f"nhan {r.status_code} — mot 5xx la cau tra loi SAI ve ai co loi")
    assert 'id="asv-form"' in r.text, "khong dung lai bieu mau cho khach sua"
    assert "Ảnh" in r.text or "ảnh" in r.text, "khong co cau nao noi ve ANH"
    assert "asv-staging" not in r.text, "cau tu choi lo khoa luu tru"
    assert hasattr(features, "AsvError")


def test_lop_SVG_an_hien_bang_THUOC_TINH_chu_khong_bang_dot_hidden():
    """🔴 **Lỗi này đã chạy trên sản phẩm, và nó làm một tính năng chết hẳn.**

    `hidden` là IDL attribute của **`HTMLElement`**. `<svg>` là `SVGElement`,
    không kế thừa `HTMLElement` ⇒ `svg.hidden = false` tạo một thuộc tính JS
    **thừa** và ⛔ không gỡ thuộc tính HTML. Cộng với luật
    `.asv-trang [hidden]{display:none!important}` của chính kho này, lớp vẽ vùng
    che `#asv-lop` **không bao giờ hiện**.

    ⇒ `xem_truoc.js` gọi `lop.hidden = false`, `vung.js` vẽ `<rect>` vào trong
      nó, mọi dòng JS đều chạy — và khách **không thể vẽ một vùng che nào**. Đọc
      lại `lop.hidden` vẫn trả `false` (nó đọc chính thuộc tính thừa vừa tạo),
      nên không có gì kêu lên cả.

    ⛔ Bài này chốt phía ĐƯỜNG: không module nào được gán `.hidden` cho một phần
       tử lấy từ `#asv-lop*`.
    """
    import re

    for ten in ("xem_truoc.js", "vung.js", "logo.js"):
        van = _bo_chu_thich((JS / ten).read_text(encoding="utf-8"), "js")
        bien = set(re.findall(
            r'var\s+(\w+)\s*=\s*document\.getElementById\(\s*"(asv-lop[^"]*)"\s*\)',
            van))
        for b, _id in bien:
            assert not re.search(re.escape(b) + r"\s*\.\s*hidden\s*=", van), (
                f"{ten}: `{b}.hidden =` tren mot `<svg>` — khong go duoc thuoc "
                f"tinh, lop se KHONG BAO GIO hien")
    nen = _bo_chu_thich((JS / "nen.js").read_text(encoding="utf-8"), "js")
    assert "setAttribute(\"hidden\"" in nen and "removeAttribute(\"hidden\")" in nen
