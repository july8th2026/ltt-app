r"""U-15 / T-07 — KHUÔN CHUẨN HOÁ THEO CỠ ENGINE.

`chuan_hoa()` làm **hai** việc rất khác nhau trong một khối:

    PHIÊN ÂM   từ điển phát âm · hạ chữ hoa viết tắt
    ĐỌC SỐ     số thứ tự · ngày · giờ · ký hiệu · số lớn · phân cách nghìn

Với engine hiện tại cả hai đều cần — nhưng vì **hai lý do khác nhau**, và một
engine khác sẽ đổi từng vế độc lập. Gộp chúng vào một cờ `chuan_hoa=True/False`
buộc engine thứ hai chọn *cả hai hoặc không cái nào*, tức nó sẽ chọn "cả hai"
và mang theo lỗi.

## 🔴 Mệnh đề trung tâm: TIỀN KHÔNG ĐƯỢC ĐỔI

`manifest._gia()` đếm ký tự **sau** chuẩn hoá. Một đường nối làm lệch đầu ra dù
một ký tự là một đường nối làm lệch **hoá đơn của mọi khách**.

⇒ Mục 1 là một **mốc vàng**: tám chuỗi, hai chế độ, chụp **trước** khi tách và
  so từng byte. Nó không kiểm hình dạng mã — nó kiểm rằng bản tái cấu trúc
  không đổi một ký tự nào.

## ⛔ Và khuôn CHỈ BỎ QUA, không bao giờ ĐẢO THỨ TỰ

Thứ tự trong `chuan_hoa()` là chịu lực: ba chú thích trong đó ghi lại ba lần đã
trả giá bằng một lần hỏng thật. Mục 4 chốt cả ba vẫn đứng dưới mọi khuôn.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice import text_pipeline as TP

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── 1. 🔴 MỐC VÀNG — đầu ra mặc định KHÔNG đổi một byte ─────────────────────

#: Tám chuỗi, chụp 08/09/2026 **trước** khi tách khuôn.
#:
#: ⛔ Đây là giá trị THẬT của bản trước, không phải kỳ vọng ai đó gõ ra. Sửa một
#:    dòng ở đây để "cho xanh" là xoá đúng thứ duy nhất chứng minh bản tái cấu
#:    trúc không đụng vào tiền.
MOC_VANG = {
    "Xin chào, hôm nay là ngày 02/09/2026 lúc 14:30.":
        "Xin chào, hôm nay là ngày ngày hai tháng chín năm hai nghìn không "
        "trăm hai mươi sáu lúc mười bốn giờ ba mươi.",
    "Giá 1.250.000đ, giảm 15% còn 1.062.500đ.":
        "Giá một triệu hai trăm năm mươi nghìn đồng, giảm 15 phần trăm còn "
        "một triệu không trăm sáu mươi hai nghìn năm trăm đồng.",
    "1. Mục một\n2. Mục hai\n3. Mục ba":
        "Một. Mục một\nHai. Mục hai\nBa. Mục ba",
    "Chỉ có chữ, không số, không viết tắt.":
        "Chỉ có chữ, không số, không viết tắt.",
}


@pytest.mark.parametrize("vao,mong", sorted(MOC_VANG.items()))
def test_mac_dinh_KHONG_doi_mot_byte(vao, mong):
    """🔴 Bất biến TIỀN. `_gia()` đếm ký tự sau chuẩn hoá, nên một ký tự lệch ở
    đây là một hoá đơn lệch cho **mọi** khách."""
    assert TP.chuan_hoa(vao) == mong


def test_moc_vang_KHONG_rong_va_KHONG_tam_thuong():
    """⭐ ĐỐI CHỨNG. Một mốc vàng gồm toàn chuỗi không có gì để chuẩn hoá sẽ
    xanh với **mọi** bản vá, kể cả bản xoá sạch `chuan_hoa`."""
    doi = [v for v, m in MOC_VANG.items() if v != m]
    assert len(doi) >= 3, "moc vang thieu ca THAT SU bien doi"


# ── 2. Khuôn có MỘT nguồn, và nó nằm cạnh sự thật về engine ─────────────────

def test_khuon_mac_dinh_SUY_TU_tham_so_cong_khai():
    """⛔ Hai bản khai cho cùng một engine là hai bản sẽ lệch — cùng cơ chế đã
    hỏng năm lần với bảng "cái gì đang sống"."""
    from apps.ltt_voice import tham_so_cong_khai as TS

    assert TP.KHUON_MAC_DINH == TP.KhuonChuanHoa(**TS.KHUON_CHUAN_HOA)

    ma = (GOC / "apps/ltt_voice/text_pipeline.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    gan = next(n for n in cay.body
               if isinstance(n, ast.Assign)
               and getattr(n.targets[0], "id", "") == "KHUON_MAC_DINH")
    assert "KHUON_CHUAN_HOA" in ast.unparse(gan.value), (
        "`KHUON_MAC_DINH` go tay thay vi doc `tham_so_cong_khai`")


def test_khuon_BAT_ban_dang_chay():
    """Engine hiện tại cần cả hai nhóm, và `doc_so_tran` phải TẮT.

    ⚠️ `doc_so_tran` bật bừa có thể sinh ra **đọc hai lần** — chưa đo `sea-g2p`
       có tự đọc số đúng chưa. Đây là chốt cho câu ấy.
    """
    assert TP.KHUON_MAC_DINH.phien_am is True
    assert TP.KHUON_MAC_DINH.doc_so is True
    assert TP.KHUON_MAC_DINH.doc_so_tran is False


def test_khuon_KHONG_sua_duoc_tai_cho():
    """Một khuôn sửa được là một khuôn mà một lượt gọi làm đổi giá của lượt
    gọi sau — trạng thái toàn cục ở đúng đường tính tiền."""
    import dataclasses

    # ⛔ `FrozenInstanceError`, khong phai `Exception` tran. Bat mot ngoai le mu
    #    o day se xanh ca khi phep gan that bai vi mot ly do HOAN TOAN KHAC —
    #    vi du `doc_so` bi doi ten va no nem `AttributeError`. Luc ay phep kiem
    #    van xanh trong khi thu no canh da bien mat.
    with pytest.raises(dataclasses.FrozenInstanceError):
        TP.KHUON_MAC_DINH.doc_so = False  # type: ignore[misc]


# ── 3. Hai nhóm tắt ĐỘC LẬP, và mỗi nhóm tắt ĐÚNG phần của nó ──────────────

MAU = "Giá 1.250.000đ, CPU chạy 15%"


def test_tat_doc_so_thi_SO_con_nguyen_va_PHIEN_AM_van_chay():
    ra = TP.chuan_hoa(MAU, khuon=TP.KhuonChuanHoa(doc_so=False))
    assert "1.250.000" in ra, "so da bi doc du `doc_so=False`"
    assert "15%" in ra
    assert "xi pi diu" in ra, "tat `doc_so` da tat nham ca tu dien"


def test_tat_phien_am_thi_TU_DIEN_nghi_va_SO_van_duoc_doc():
    ra = TP.chuan_hoa(MAU, khuon=TP.KhuonChuanHoa(phien_am=False))
    assert "CPU" in ra, "tu dien van chay du `phien_am=False`"
    assert "một triệu hai trăm năm mươi nghìn" in ra, (
        "tat `phien_am` da tat nham ca phep doc so")
    assert "phần trăm" in ra


def test_tat_CA_HAI_thi_chi_con_don_dep():
    """⭐ Ca này chứng minh hai nhánh **thật sự độc lập**: tắt cả hai vẫn phải
    còn phần luôn-chạy (ký tự vô hình · NFC · URL · khoảng trắng), vì đó là
    phần không thuộc engine nào."""
    ra = TP.chuan_hoa("Xem   tại https://a.bc  và CPU 1.500",
                      khuon=TP.KhuonChuanHoa(phien_am=False, doc_so=False))
    assert "đường dẫn" in ra, "phan luon-chay da bi tat theo"
    assert "   " not in ra
    assert "CPU" in ra and "1.500" in ra


# ── 4. ⛔ Khuôn CHỈ BỎ QUA — ba cái bẫy thứ tự vẫn đứng ─────────────────────

def test_bay_1_TU_DIEN_van_chay_TRUOC_doc_so():
    """Từ điển chứa tên riêng; vài phép thay số có thể cắt mất ranh giới từ.

    ⛔ ĐỌC CẤU TRÚC, KHÔNG ĐỌC CHUỖI. Bản đầu viết
       `ma.index("phien_am") < ma.index("doc_so")` và **đỏ oan**: chuỗi
       `"doc_so"` khớp vào `doc_so_tran` trong **chữ ký** ở vị trí 28, tức phép
       so đang đo thứ tự của hai tham số chứ không phải thứ tự của hai nhánh.

    ⭐ Cùng lỗi mà cả tệp này đang chốt ở chỗ khác: đo **biểu diễn** thay vì đo
       **tính chất**. So `lineno` của hai câu `if` là đo đúng thứ đang cần.
    """
    ham = _ham("chuan_hoa")
    dong = {}
    for n in ast.walk(ham):
        if isinstance(n, ast.If) and isinstance(n.test, ast.Attribute):
            dong[n.test.attr] = n.lineno
    assert {"phien_am", "doc_so"} <= set(dong), (
        f"khong thay du hai nhanh `if k.<nhom>` (thay: {sorted(dong)})")
    assert dong["phien_am"] < dong["doc_so"], (
        f"nhanh `doc_so` (dong {dong['doc_so']}) nam TRUOC `phien_am` "
        f"(dong {dong['phien_am']}) — thu tu chiu luc da bi dao")


def test_bay_2_KY_HIEU_truoc_doc_so_lon_truoc_NGAN():
    """🔴 `_KY_HIEU` phải chạy TRƯỚC: luật `đ` → " đồng" dùng lookbehind
    `(?<=\\d)`. Sau `_doc_so_lon` thì chữ số đã thành chữ, lookbehind trượt, và
    `1.250.000đ` ra *"một triệu hai trăm năm mươi nghìnđ"*."""
    ma = ast.unparse(_ham("_khoi_doc_so"))
    assert ma.index("_KY_HIEU") < ma.index("_doc_so_lon") < ma.index("_NGAN")


def test_bay_2_do_bang_HANH_VI_chu_khong_chi_bang_thu_tu():
    """⭐ Phép kiểm trên đọc **hình dạng**; phép kiểm này đọc **kết quả**. Thiếu
    nó thì một bản vá giữ nguyên thứ tự mà đổi chính regex vẫn xanh."""
    ra = TP.chuan_hoa("1.250.000đ")
    assert "nghìnđ" not in ra, "chu `đ` mac ket — `_KY_HIEU` da chay sau"
    assert ra.endswith("đồng")


def test_bay_3_xoa_ky_tu_vo_hinh_TRUOC_NFC():
    """`'a'` + U+200B + U+0301: xoá SAU `NFC` cho hai ký tự rời, xoá TRƯỚC cho
    một ký tự ghép. Hai chuỗi **nhìn giống hệt nhau** và in ra như nhau — nhưng
    với tokenizer đó là hai chuỗi khác nhau."""
    ra = TP.chuan_hoa("a​́")
    assert ra == "á", f"ky tu vo hinh xoa SAU NFC: {ra!r}"


def _ham(ten: str):
    cay = ast.parse((GOC / "apps/ltt_voice/text_pipeline.py")
                    .read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


def test_khuon_KHONG_co_duong_dao_thu_tu():
    """⛔ Một khuôn cho phép **đổi thứ tự** mở lại cả ba bẫy trên cùng lúc, ở
    một chỗ mà không chú thích nào nhìn thấy. Nó chỉ được có quyền TẮT."""
    truong = {f.name for f in TP.KhuonChuanHoa.__dataclass_fields__.values()}
    assert truong == {"phien_am", "doc_so", "doc_so_tran"}
    for ten in truong:
        assert isinstance(getattr(TP.KHUON_MAC_DINH, ten), bool), (
            f"`{ten}` khong phai bool — mot khuon chi duoc TAT/BAT, "
            f"khong duoc mang thu tu hay danh sach")


# ── 5. Tương thích ngược — đây là bề mặt LIÊN APP ───────────────────────────

def test_doc_so_tran_None_nghia_la_THEO_KHUON():
    assert TP.chuan_hoa("27") == TP.chuan_hoa("27", doc_so_tran=None)


def test_tham_so_cu_van_DE_LEN_duoc_khuon():
    """⚠️ `apps/auto_scan_video/giong_noi.py` gọi thẳng `text_pipeline.chuan_hoa`
    với `doc_so_tran=`. Đổi một chữ ký dùng chung để cho gọn là cách làm hỏng
    một app không ai đang đọc."""
    assert "hai mươi bảy" in TP.chuan_hoa("27", doc_so_tran=True)
    assert "hai mươi bảy" not in TP.chuan_hoa("27", doc_so_tran=False)


def test_ASV_van_goi_duoc_voi_chu_ky_cu():
    import inspect

    tham = inspect.signature(TP.chuan_hoa).parameters
    assert "doc_so_tran" in tham and "tu_dien_rieng" in tham
    asv = (GOC / "apps/auto_scan_video/giong_noi.py").read_text(encoding="utf-8")
    assert "text_pipeline.chuan_hoa(" in asv, (
        "ASV khong con goi truc tiep — cap nhat phep kiem nay")


# ── 6. Đường TIỀN dùng khuôn MẶC ĐỊNH, không dùng khuôn của ai khác ─────────

def test_gia_KHONG_nhan_khuon_tu_tham_so_cua_khach():
    """⛔ Khuôn đổi độ dài văn bản ⇒ đổi hoá đơn. Nếu `_gia` nhận khuôn từ
    `params` thì khách tự chọn được giá của chính mình."""
    ma = ast.unparse(ast.parse(
        (GOC / "apps/ltt_voice/manifest.py").read_text(encoding="utf-8")))
    assert "khuon" not in ma, (
        "`manifest.py` truyen `khuon` — duong tinh tien phai dung khuon MAC DINH")
