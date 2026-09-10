"""V6 pha 08 — TAI LEN BEN VUNG: hai trần, hai lane, và một tính năng đã CHẾT.

## 🔴 Cái tìm ra không phải một lỗi nhỏ. Nó là một tính năng không ai tới được.

Auto Scan có **hai** đường nhận tệp:

    multipart    tep -> Cloudflare -> tien trinh app     tran  90 MB
    ben vung     tep -> thang len kho (presigned PUT)    tran   2 GiB

Đường bền vững tồn tại **chính vì** trần 90 MB: Cloudflare cắt ở 100 MB trên
đường vào máy chủ, và đường bền vững không đi qua đó.

⛔ Nhưng lúc khách CHỌN tệp, `moTep` đo kích thước với **`data-tran-mb` = 90**
   — trần của đường kia — rồi **khoá nút Bắt đầu**. Tức mọi tệp trên 90 MB đều
   bị chặn ngay ở cửa, và đường 2 GiB **chưa bao giờ chạy được từ giao diện**.

⭐ Đo thật trên trình duyệt (10/09), MP4 nằm giữa hai trần:

       truoc:  nut_KHOA = true    "vuot qua 90 MB"
       sau  :  nut_KHOA = false

🔑 Hình dạng lỗi này kho đã đặt tên: *"năng lực có, không ai đi trên đường"*.
   Khác bốn ca trước ở một điểm đáng ghi — ở đây **chính hàng rào chặn đường**,
   chứ không phải thiếu người gọi.

## Và một đường lui IM LẶNG ở phía sau nó

Khi đường bền vững hỏng, bản cũ `form.submit()` **vô điều kiện**. Với một tệp
1,5 GB vừa PUT hỏng ở 90%, đường lui ấy đẩy lại 1,5 GB qua Cloudflare, bị cắt,
rồi trả về *"Video vượt quá 90 MB. Hãy cắt ngắn hoặc giảm chất lượng trước."*

⛔ Câu ấy là một lời khuyên **SAI**: tệp của khách không hề quá lớn (2 GiB mới
   là trần thật), thứ hỏng là đường tải lên. Ta gửi họ đi sửa nhầm thứ — sau
   khi đã bắt họ chờ hai lần.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from apps.auto_scan_video import features, routes

GOC = Path(__file__).resolve().parent.parent
JS = GOC / "server" / "static" / "asv.js"
MAU = GOC / "apps" / "auto_scan_video" / "templates" / "asv_trang_chinh.html"


def _js() -> str:
    return JS.read_bytes().decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Hai trần là HAI con số, và chúng không được lẫn vào nhau
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_tran_KHAC_nhau_va_ben_vung_LON_hon():
    """Nếu hai trần bằng nhau thì cả bộ kiểm này vô nghĩa — và đường bền vững
    cũng vô nghĩa, vì nó tồn tại chỉ để chở thứ đường kia không chở nổi."""
    assert features.TRAN_BEN_VUNG > routes.TRAN_TAI_LEN
    assert routes.TRAN_TAI_LEN == 90 * 1024 * 1024


def test_o_chon_tep_CO_kieu_ma_duong_ben_vung_TU_CHOI():
    """⚠️ Đây là lý do trần phụ thuộc TỆP chứ không phải một hằng số: một `.mkv`
    500 MB không có đường nào, còn một `.mp4` 500 MB thì có.

    ⛔ Nếu hai tập bằng nhau thì luật `vuot_tran_kieu` không còn trường hợp nào
       để áp, và câu chỉ đường sang MP4 thành một câu không ai đọc.
    """
    o_chon = re.search(r'id="asv-video"[^>]*accept="([^"]+)"',
                       MAU.read_bytes().decode("utf-8"))
    assert o_chon, "khong tim thay o chon tep"
    tap_chon = set(o_chon.group(1).split(","))
    chi_o_o_chon = tap_chon - set(features.KIEU_VIDEO_HOP_LE)
    assert chi_o_o_chon, (
        "moi kieu o chon tep deu di duoc duong ben vung — luat `vuot_tran_kieu` "
        "khong con truong hop nao")


def test_kieu_duong_ben_vung_KHAI_ma_o_chon_khong_moi():
    """🔑 Chiều ngược lại, và nó ghi lại một thứ **không** phải lỗi nhưng dễ bị
    đọc thành lỗi ở phiên sau.

    `KIEU_VIDEO_HOP_LE` có `video/x-m4v` mà ô chọn tệp **không** mời. Tức đường
    bền vững sẵn sàng nhận một kiểu mà giao diện không bao giờ đưa tới.

    ⭐ Ghi ra đây chứ không "sửa cho khớp", vì hai danh sách trả lời **hai câu
       khác nhau**: ô chọn hỏi *"mời khách thứ gì"*, hằng số hỏi *"nhận thứ gì
       nếu nó tới"*. Một client tự viết (hoặc API sau này) vẫn gửi `.m4v` được,
       và nhận nó là đúng.

    ⚠️ Bài này **không** cấm chúng khớp nhau; nó chỉ khoá con số lại để lần sau
       ai đó đổi một trong hai danh sách thì phải nhìn cả hai.
    """
    o_chon = re.search(r'id="asv-video"[^>]*accept="([^"]+)"',
                       MAU.read_bytes().decode("utf-8"))
    tap_chon = set(o_chon.group(1).split(","))
    assert "video/x-m4v" in features.KIEU_VIDEO_HOP_LE
    assert "video/x-m4v" not in tap_chon


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Cửa vào: trần đo phải là trần của ĐƯỜNG SẼ ĐƯỢC DÙNG
# ══════════════════════════════════════════════════════════════════════════════

def test_moTep_KHONG_do_bang_tran_multipart_cho_moi_tep():
    """🔑 Phép kiểm chốt chính của pha 08, và nó chốt bằng **hình dạng mã**.

    ⛔ Bản cũ:

           var tran = parseInt(form.getAttribute("data-tran-mb") || "0", 10);

       — một hằng số cho mọi tệp. Bản đúng phải CHỌN trần theo tệp.

    ⚠️ Neo theo `benVungKieuDuocKhong` chứ không theo chuỗi `data-tran-ben-vung`
       xuất hiện ở đâu đó trong tệp: chuỗi ấy vốn đã có mặt (ở
       `benVungDuocKhong`), nên đếm nó sẽ xanh cả với bản cũ.
    """
    js = _js()
    i = js.index("function moTep(")
    j = js.index("if (oTep) oTep.addEventListener", i)
    than = js[i:j]
    assert "benVungKieuDuocKhong(f)" in than, (
        "`moTep` khong hoi tep se di duong nao truoc khi do kich thuoc")
    assert "data-tran-ben-vung" in than, (
        "`moTep` khong bao gio doc toi tran cua duong ben vung")


def test_phep_kiem_KIEU_tach_rieng_khoi_phep_kiem_KICH_THUOC():
    """⭐ Gộp hai phép kiểm làm một chính là lý do dòng ấy từng đo với trần sai:
    `moTep` cần biết **lane** trước, rồi mới chọn trần."""
    js = _js()
    assert "function benVungKieuDuocKhong(f)" in js
    i = js.index("function benVungKieuDuocKhong(f)")
    j = js.index("function benVungDuocKhong(f)")
    assert "data-tran-ben-vung" not in js[i:j], (
        "phep kiem KIEU khong duoc dinh toi kich thuoc")


def test_cau_tu_choi_theo_KIEU_chi_duong_sang_MP4_khong_bao_cat_ngan():
    """⛔ *"Hãy cắt ngắn video"* là lời khuyên sai cho một `.mkv` 500 MB: cắt
    ngắn tới đâu cũng vẫn là `.mkv`. Câu đúng phải nói ra thứ khách đổi được."""
    van = MAU.read_bytes().decode("utf-8")
    i = van.index('"vuot_tran_kieu"')
    dong = van[i:van.index("\n", i)]
    assert "MP4" in dong and "MOV" in dong


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Đường lui: phải HỎI KÍCH THƯỚC trước khi lui
# ══════════════════════════════════════════════════════════════════════════════

def test_duong_lui_KHONG_con_vo_dieu_kien():
    """🔴 Bản cũ `.catch()` gọi thẳng `form.submit()`. Với tệp trên trần
    multipart, đó là đẩy lại toàn bộ qua một đường **không thể** chở nó."""
    js = _js()
    i = js.index("xinVe(f).then(")
    khoi = js[i:js.index("})();", i)]
    assert "taiThatBai(f)" in khoi, "duong lui khong hoi kich thuoc"
    # Doi chung: khong con mot `form.submit()` TRAN TRUI trong khoi `.catch`.
    sau_catch = khoi[khoi.index("}).catch("):]
    assert "form.submit()" not in sau_catch, (
        "van con mot duong lui vo dieu kien trong `.catch`")


def test_ham_quyet_dinh_duong_lui_doc_dung_TRAN_MULTIPART():
    """Trần dùng để quyết định *"có lui được không"* phải là trần của đường sẽ
    lui về (multipart), **không** phải trần bền vững."""
    js = _js()
    i = js.index("function luiVeMultipartDuocKhong(f)")
    than = js[i:js.index("\n  }", i)]
    assert "data-tran-mb" in than
    assert "data-tran-ben-vung" not in than


def test_co_nut_THU_LAI_va_no_dung_requestSubmit():
    """⚠️ `form.submit()` **không** phát sự kiện `submit`, nên nó sẽ bỏ qua chính
    đoạn xử lý bền vững và đẩy tệp qua đường multipart — đúng cái vừa từ chối."""
    assert 'id="asv-tai-lai"' in MAU.read_bytes().decode("utf-8")
    js = _js()
    i = js.index("nutTaiLai.addEventListener")
    khoi = js[i:i + 500]
    assert "requestSubmit" in khoi
    assert "form.submit()" not in khoi


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Thử lại có TRẦN, và trần ấy phải nhỏ
# ══════════════════════════════════════════════════════════════════════════════

def test_thu_lai_PUT_co_tran_lan():
    """⚠️ Ba lần tổng cộng, không nhiều hơn: một lỗi CÓ HỆ THỐNG (sai chữ ký,
    kho từ chối) sẽ hỏng y hệt cả ba lần, và bắt khách chờ ba lượt cho cùng một
    câu trả lời là đúng cái giá mà `loi.py` từ chối trả ở tầng job."""
    js = _js()
    m = re.search(r"var LAN_THU_TOI_DA = (\d+);", js)
    assert m, "khong khai tran so lan thu lai"
    assert 2 <= int(m.group(1)) <= 4, (
        f"tran thu lai = {m.group(1)} — qua nhieu hoac qua it")


def test_thu_lai_PUT_dung_lai_VE_CU_khong_xin_ve_moi():
    """⭐ Vé presigned còn hạn sau một lần hỏng mạng, nên thử lại chính nó là
    phép sửa rẻ nhất. Xin vé mới mỗi lần là tạo rác `pending` trong CSDL."""
    js = _js()
    i = js.index("function dayLenCoThuLai(ve, f, lan)")
    than = js[i:js.index("\n  }", i)]
    assert "dayLenCoThuLai(ve, f, lan + 1)" in than
    assert "xinVe" not in than, "thu lai ma xin ve moi"


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Máy chủ vẫn là nơi cưỡng chế — giao diện chỉ nói sớm
# ══════════════════════════════════════════════════════════════════════════════

def test_may_chu_VAN_ap_tran_multipart_trong_luc_chay():
    """⛔ Mọi thứ ở §2–§4 là JavaScript, tức là **lời nhắc**, không phải hàng
    rào. Một client tự viết không chạy dòng nào trong đó.

    ⭐ Và trần được áp **trong lúc chạy tệp** chứ không sau: byte thứ
       `(trần + 1)` làm vòng lặp dừng, nên một tệp 2 GB không bao giờ được cấp
       phát 2 GB rồi mới bị từ chối.
    """
    import ast
    import inspect

    ma = inspect.getsource(routes.tao)
    assert "TRAN_TAI_LEN" in ma
    cay = ast.parse(ma.lstrip())
    trong_vong = False
    for n in ast.walk(cay):
        if isinstance(n, ast.While):
            for k in ast.walk(n):
                if isinstance(k, ast.Name) and k.id == "TRAN_TAI_LEN":
                    trong_vong = True
    assert trong_vong, "tran khong duoc ap NGAY TRONG vong doc tep"


def test_duong_ben_vung_LOC_theo_chu_so_huu_ngay_trong_truy_van():
    """🔑 IDOR. `upload_sessions.owned(...)` lọc theo `user_id` VÀ `app_slug`
    ngay trong câu truy vấn, nên một `upload_id` của người khác không trả về
    dòng nào — nó không thể thành một lỗi *"không có quyền"* mà kẻ gọi đoán
    được từ đó."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(features.tao_run_tu_ve))
    for n in ast.walk(cay):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "owned"):
            ten = {k.arg for k in n.keywords}
            assert {"user_id", "app_slug"} <= ten, ten
            return
    pytest.fail("khong thay loi goi `upload_sessions.owned`")


def test_soi_TRUOC_khi_promote():
    """⛔ Soi sau khi promote là để một tệp không đạt chính sách chiếm một khoá
    bền trong kho — rồi phải dọn bằng tay.

    🔑 Đọc **AST**, không đọc văn bản. Bản đầu của bài này so vị trí hai chuỗi
       trong `inspect.getsource(...)` và **ĐỎ trên mã đúng**: docstring của hàm
       nhắc `kho.promote()` ở dòng 1032, tức trước lời gọi `nhap_media.soi()`
       thật ở dòng 2061.

    ⭐ `grep` khớp cách người ta VIẾT; AST khớp cái người ta LÀM. Một chú thích
       giải thích tại sao dùng `promote` không phải là một lời gọi `promote`.
    """
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(features.tao_run_tu_ve))
    dong: dict[str, int] = {}
    for n in ast.walk(cay):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            dong.setdefault(n.func.attr, n.lineno)
    assert "soi" in dong, "khong co loi goi `soi` nao"
    assert "promote" in dong, "khong co loi goi `promote` nao"
    assert dong["soi"] < dong["promote"], (
        f"promote (dong {dong['promote']}) chay truoc soi (dong {dong['soi']})")
