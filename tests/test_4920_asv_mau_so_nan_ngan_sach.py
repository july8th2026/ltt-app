"""test_4920 — B13-A2/B3/B4: mẫu số của `he_so_co_gian` là NGÂN SÁCH, không phải khe.

⭐ Bộ kiểm này ⛔ KHÔNG nạp model nào, ⛔ không gọi LLM/TTS/GPU, ⛔ không chạm CSDL:
mọi thứ nó chạm là hàm thuần + một phép đọc AST trên chính mã nguồn.

## Bốn con số đo trên lượt thật `asvr_47327a869a8f4597960048f09064740`

    đoạn       tiếng TTS   khe (ket-bat)   ngân sách   lặng chưa dùng   hệ số đã áp
    seg_0007     2,40 s        2,10          9,46         7,36 s          1,1418
    seg_0011     2,32          1,98          1,98         0,00            1,1711
    seg_0024     1,20          0,90         33,39        32,49 s          1,3333
    seg_0031     2,08          1,82          1,82         0,00            1,1422

🔴 **HAI CHIỀU, và chiều thứ hai là chiều bắt buộc.** `seg_0007`/`seg_0024` phải
   ra `1,0` (nén OAN — lặng còn trống). `seg_0011`/`seg_0031` phải **KHÔNG ĐỔI**
   (lặng bằng 0 ⇒ `ngan_sach == khe` ⇒ tăng tốc là ĐÚNG). Thiếu chiều hai thì
   một bản vá *"nới hết, luôn trả 1,0"* cũng xanh — đúng bẫy `khong-doi-chung-
   thi-so-khong-khong-phai-phat-hien`.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from apps.auto_scan_video import (giai_doan_giong, giai_doan_thoi_gian,
                                  nan_cho_vua, thoi_gian)

GOC = pathlib.Path(__file__).resolve().parents[1]

#: `(ma, tts_giay, khe, ngan_sach_that, he_so_cu_theo_khe)` — bảng ở docstring.
#: `ngan_sach_that` là `thoi_gian.ngan_sach_nan_s(khe, moc_sau - bat)` của lượt
#: đã đo, tức con số mà `giai_doan_giong` truyền xuống.
DO_THAT = (
    ("seg_0007", 2.40, 2.10, 9.46, 1.1418),
    ("seg_0011", 2.32, 1.98, 1.98, 1.1711),
    ("seg_0024", 1.20, 0.90, 33.39, 1.3333),
    ("seg_0031", 2.08, 1.82, 1.82, 1.1422),
)

#: Hai đoạn CÒN LẶNG ⇒ phải được gỡ nén về `1,0`.
DUOC_GO = ("seg_0007", "seg_0024")
#: Hai đoạn KHÔNG còn lặng ⇒ hệ số phải y nguyên. **Đây là đối chứng.**
GIU_NGUYEN = ("seg_0011", "seg_0031")


# ══════════════════════════════════════════════════════════════════════════════
#  A2 — bốn phép chốt HAI CHIỀU
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ma,tts,khe,ns,he_so_cu", DO_THAT)
def test_4920_mau_so_cu_theo_KHE_tai_hien_dung_con_so_da_do(ma, tts, khe, ns,
                                                            he_so_cu):
    """⛔ Trước khi chốt bản vá, phải chứng minh phép đo tái hiện được cái CŨ.

    ⭐ Không có bài này thì ba bài dưới đo một thứ ⛔ không ai biết có phải thứ đã
       gây ra `1,3333` trên máy khách hay không — `phep-kiem-xanh-tren-thu-da-hong`.
    """
    _duoc, he_so = nan_cho_vua.co_gian_du_khong(tts, khe)
    # ⚠️ `abs=2e-3`, ⛔ không chặt hơn: bảng ở docstring làm tròn giây về **2 chữ
    #    số**, còn `1,1418` là hệ số tính trên giây ĐẦY ĐỦ của lượt chạy. Xiết
    #    dung sai xuống 1e-5 là đòi một độ chính xác mà dữ liệu vào ⛔ không có —
    #    `sai-so-nho-o-nhip-thanh-sai-so-lon-o-nguong`, chiều ngược.
    assert he_so == pytest.approx(he_so_cu, abs=2e-3), (
        f"{ma}: mẫu số `khe` phải ra đúng hệ số đã áp trên lượt thật")


@pytest.mark.parametrize("ma,tts,khe,ns,he_so_cu",
                         [r for r in DO_THAT if r[0] in DUOC_GO])
def test_4920_con_lang_thi_he_so_ve_1(ma, tts, khe, ns, he_so_cu):
    """🔴 `seg_0007` (khe 2,10 · ngân sách 9,46) và `seg_0024` (0,90 · 33,39) ⇒ **1,0**."""
    duoc, he_so = nan_cho_vua.co_gian_du_khong(tts, khe, ns)
    assert duoc, f"{ma}: vừa ngân sách thì ⛔ không thể là 'không đủ'"
    assert he_so == pytest.approx(1.0, abs=1e-9), (
        f"{ma}: còn {ns - khe:.2f}s lặng chưa dùng mà vẫn nén {he_so:.4f}")

    kq = nan_cho_vua.ket_luan(ma, chu="x", giay=tts, khe=khe, so_vong=0,
                              ngan_sach=ns)
    assert kq.he_so_co_gian == pytest.approx(1.0, abs=1e-9)
    # ⛔ `CO_GIAN` với hệ số `1,0` là kể về một `atempo` CHƯA TỪNG chạy — đúng
    #    con bọ mà `nan_cho_vua.NGAN` đã ghi lại 25/09, ở chiều còn lại.
    assert kq.trang_thai == nan_cho_vua.VUA, (
        f"{ma}: vừa ngân sách thi hành ⇒ VUA, ⛔ không phải {kq.trang_thai!r}")
    assert kq.trang_thai != nan_cho_vua.CAN_SUA, (
        f"{ma}: ⛔ không được đẩy vào vòng sửa (tiêu tiền) nữa")
    # `khe` Ở LẠI nguyên nghĩa cho báo cáo — ⛔ không bị thay bằng ngân sách.
    assert kq.khe == pytest.approx(khe, abs=1e-9)
    assert kq.ngan_sach == pytest.approx(ns, abs=1e-9)


@pytest.mark.parametrize("ma,tts,khe,ns,he_so_cu",
                         [r for r in DO_THAT if r[0] in GIU_NGUYEN])
def test_4920_HET_lang_thi_he_so_KHONG_DOI(ma, tts, khe, ns, he_so_cu):
    """🔴 **ĐỐI CHỨNG.** `seg_0011`/`seg_0031` có lặng = 0 ⇒ tăng tốc là ĐÚNG.

    ⛔ Thiếu bài này thì một bản vá *"luôn trả 1,0"* cũng xanh, và nó sẽ giao cho
       khách những câu **đè lên nhau** ở đúng chỗ ⛔ không có khoảng lặng nào.
    """
    assert ns == pytest.approx(khe, abs=1e-9), (
        f"{ma}: bảng đo khai lặng = 0, nên `ngan_sach` phải BẰNG `khe`")
    _duoc, he_so = nan_cho_vua.co_gian_du_khong(tts, khe, ns)
    assert he_so == pytest.approx(he_so_cu, abs=2e-3), (
        f"{ma}: ⛔ không được nới — lặng bằng 0 thì ⛔ không mượn được gì")
    kq = nan_cho_vua.ket_luan(ma, chu="x", giay=tts, khe=khe, so_vong=0,
                              ngan_sach=ns)
    assert kq.he_so_co_gian == pytest.approx(he_so_cu, abs=2e-3)
    assert kq.trang_thai in (nan_cho_vua.CO_GIAN, nan_cho_vua.CAN_SUA), (
        f"{ma}: một `atempo` THẬT SỰ chạy ⇒ ⛔ không được là VUA")


def test_4920_ngan_sach_None_giu_NGUYEN_nghia_cu():
    """⛔ `None` ≠ `khe`: nó nghĩa *"người gọi không nói"*, và khi đó lùi về `khe`.

    ⭐ Hai trạng thái tách nhau để một chỗ gọi quên truyền `ngan_sach` ⛔ không
       lặng lẽ biến thành một phép đo khai *"ngân sách BẰNG khe"* —
       `hai-trang-thai-gop-thanh-mot-gia-tri`.
    """
    assert nan_cho_vua.mau_so_co_gian(2.10, None) == pytest.approx(2.10)
    assert nan_cho_vua.mau_so_co_gian(2.10, 9.46) == pytest.approx(9.46)
    # ⚠️ Ngân sách NHỎ hơn khe là dữ liệu hỏng thượng nguồn ⇒ kẹp về `khe`, ⛔
    #    không để nó phóng `he_so` to lên.
    assert nan_cho_vua.mau_so_co_gian(2.10, 0.5) == pytest.approx(2.10)

    kq = nan_cho_vua.ket_luan("seg_0007", chu="x", giay=2.40, khe=2.10,
                              so_vong=0)
    assert kq.he_so_co_gian == pytest.approx(1.1418, abs=2e-3), (
        "không truyền `ngan_sach` ⇒ luật CŨ y nguyên")
    assert kq.ngan_sach is None, "⛔ vắng mặt phải là `None`, ⛔ không phải `khe`"


def test_4920_tung_doan_mang_ngan_sach_khi_co_va_VANG_khi_khong():
    """⭐ Một dòng `VUA` có `giay > khe` đọc như tự mâu thuẫn nếu thiếu `ngan_sach`."""
    co = nan_cho_vua.ket_luan("seg_0024", chu="x", giay=1.20, khe=0.90,
                              so_vong=0, ngan_sach=33.39)
    khong = nan_cho_vua.ket_luan("seg_0024", chu="x", giay=1.20, khe=0.90,
                                 so_vong=0)
    tt_co = nan_cho_vua.tom_tat([co])["tung_doan"][0]
    tt_khong = nan_cho_vua.tom_tat([khong])["tung_doan"][0]
    assert tt_co["ngan_sach"] == pytest.approx(33.39)
    assert "ngan_sach" not in tt_khong, "⛔ vắng mặt ⇒ khoá VẮNG, ⛔ không `0.0`"
    # `khe` và `lech` ⛔ KHÔNG đổi nghĩa ở cả hai dòng — chúng là của BÁO CÁO.
    for d in (tt_co, tt_khong):
        assert d["khe"] == pytest.approx(0.90)
        assert d["lech"] == pytest.approx(nan_cho_vua.lech(1.20, 0.90), abs=1e-4)


# ══════════════════════════════════════════════════════════════════════════════
#  A2 — BA chỗ gọi, ⛔ không phải hai: đọc bằng AST
# ══════════════════════════════════════════════════════════════════════════════

def test_4920_CA_BA_cho_goi_ket_luan_deu_truyen_ngan_sach():
    """🔴 Một chỗ quên = một ĐƯỜNG lặng lẽ giữ luật CŨ.

    `giai_doan_giong` có BA đường ra cho một đoạn — bản ghi lát cắt (`lat`), dùng
    lại tệp cũ (`"cu"`), mới sinh — và `_dem_nan_oan` đã từng chỉ đếm **một**
    trong ba (chú thích của chính nó ghi lại). ⛔ Nên bài này đếm bằng **AST**,
    ⛔ không bằng `grep`, và ⛔ không tin vào con số 3 mà đếm chính số lời gọi có
    trong mã: liệt-kê-từ-trí-nhớ là cách bỏ sót đường thứ tư.
    """
    cay = ast.parse(pathlib.Path(giai_doan_giong.__file__).read_text("utf-8"))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "ket_luan"]
    assert goi, "⛔ không tìm thấy lời gọi `ket_luan` nào — bài này đã mù"
    thieu = [n.lineno for n in goi
             if not any(k.arg == "ngan_sach" for k in n.keywords)]
    assert not thieu, (
        "chỗ gọi `ket_luan` ở dòng %s ⛔ KHÔNG truyền `ngan_sach=` ⇒ đường ấy "
        "vẫn nén theo `khe`, và nó xanh trên mọi phép kiểm hàm thuần" % (thieu,))


def test_4920_khe_cua_KHONG_bi_sua_de_tu_cong_khoang_lang():
    """⛔ `khe_cua` trả lời ĐÚNG câu của nó — sai là **câu được hỏi** ở chỗ gọi.

    `thoi_gian.ngan_sach_nan_s` đã viết ra lời ấy 26/09, và bản vá A2 phải sửa
    chỗ HỎI chứ ⛔ không sửa chỗ TRẢ LỜI.
    """
    m = {"ma": "seg_0024", "bat": 100.0, "ket": 100.90}
    assert nan_cho_vua.khe_cua(m) == pytest.approx(0.90, abs=1e-9), (
        "`khe_cua` phải vẫn là `ket - bat` thuần, ⛔ không cộng khoảng lặng")


def test_4920_hai_cua_doc_CUNG_mot_mau_so():
    """⭐ Cửa TIÊU TIỀN (`nen_viet_lai`) và cửa THI HÀNH (`he_so_co_gian`) từ đây
       đọc cùng `ngan_sach` — trước 28/09 chúng đọc hai mẫu số khác nhau."""
    for ma, tts, khe, ns, _cu in DO_THAT:
        goi_llm = nan_cho_vua.nen_viet_lai(tts, ns)
        _duoc, he_so = nan_cho_vua.co_gian_du_khong(tts, khe, ns)
        if not goi_llm:
            continue
        assert he_so > 1.0, (
            f"{ma}: cửa tiêu tiền nói 'tràn ngân sách' mà cửa thi hành nói "
            f"'vừa' — hai mẫu số lại lệch")


# ══════════════════════════════════════════════════════════════════════════════
#  B4 — hai đại lượng, hai cái tên ⛔ không đọc lẫn được
# ══════════════════════════════════════════════════════════════════════════════

def test_4920_B4_bao_cao_khai_RO_ke_hoach_so_voi_da_ap():
    """🔴 `1,15` (kế hoạch) ⛔ không được đứng cạnh `1,3333` (đã áp) dưới hai tên
       nghe như MỘT.

    ⭐ Bốn khoá phải nằm trong `master` — `asv_doi_soat.KHOA_CAN["timing_align"]`
       khai `("master",)`, nên khoá con thêm được mà ⛔ không đụng sổ đăng ký dùng
       chung ở `tools/`.
    """
    # ⭐ Đo bằng HÀM THẬT (`doi_chieu_he_so_toc` là hàm thuần), ⛔ không bằng
    #    `grep` vào mã — một phép `grep` xanh khi khoá có mặt trong một chú thích.
    ra = thoi_gian.doi_chieu_he_so_toc(
        # Kế hoạch: `1,15` trên hai đoạn KHÁC (tập của `compose`)
        {"seg_0012": 1.15, "seg_0013": 1.15,
         "seg_0007": 1.0, "seg_0024": 1.0},
        # Đã áp: `1,3333` trên `seg_0024` (tập của `timing_align`)
        {"seg_0012": 1.0, "seg_0013": 1.0,
         "seg_0007": 1.1418, "seg_0024": 1.3333})
    assert ra["he_so_toc_ke_hoach_lon_nhat"] == pytest.approx(1.15)
    assert ra["so_doan_tang_toc_ke_hoach"] == 2
    assert ra["he_so_toc_da_ap_lon_nhat"] == pytest.approx(1.3333)
    assert ra["so_doan_tang_toc_da_ap"] == 2
    # 🔴 Đúng cái bẫy: `1,15 < 1,3333`, và nếu hai con số ⛔ không mang hậu tố
    #    `_ke_hoach` / `_da_ap` thì người đọc kết luận *"trần đã giữ"*.
    assert (ra["he_so_toc_ke_hoach_lon_nhat"]
            < ra["he_so_toc_da_ap_lon_nhat"]), "dữ liệu mẫu phải tái hiện cái bẫy"

    # Và giai đoạn phải THẬT SỰ đổ chúng vào `master` (⛔ không phải `lech`).
    src = pathlib.Path(giai_doan_thoi_gian.__file__).read_text("utf-8")
    assert "doi_chieu_he_so_toc" in src and "do_duoc[_k] = _v" in src, (
        "`timing_align` ⛔ chưa ghi bốn con số đối chiếu vào `master` — người "
        "đọc báo cáo vẫn phải ghép hai tầng để biết trần có giữ không")
    assert '_k != "lech"' in src, (
        "`lech` mang `ma` và là danh sách để LOG — ⛔ không phải một phép đo")

    # ⭐ Và hai khoá PHẲNG phải TỰ KHAI rằng chúng là KẾ HOẠCH — đổi tên chúng
    #    làm đỏ `test_408` (`tools/asv_doi_soat`), thứ làn này ⛔ không sở hữu,
    #    nên docstring là hàng rào duy nhất và nó phải TỒN TẠI.
    tl = thoi_gian.tom_tat({"doan": []})
    assert {"so_doan_tang_toc", "he_so_toc_lon_nhat"} <= set(tl), (
        "⛔ đừng đổi tên hai khoá này: `asv_doi_soat.KHOA_BO_QUA_CO_Y` khai "
        "đúng chúng và `test_408` chốt hai chiều")
    tai_lieu = inspect.getdoc(thoi_gian.tom_tat) or ""
    assert "KẾ HOẠCH" in tai_lieu and "he_so_toc_da_ap" in tai_lieu, (
        "docstring của `thoi_gian.tom_tat` phải nói RÕ hai khoá này là kế "
        "hoạch và chỉ sang `master.he_so_toc_da_ap`")


# ══════════════════════════════════════════════════════════════════════════════
#  B3 — hai máy tăng tốc: sự thật là chúng ⛔ KHÔNG nhân nhau
# ══════════════════════════════════════════════════════════════════════════════

def test_4920_B3_ke_hoach_he_so_toc_KHONG_duoc_ap_lam_atempo_lan_hai():
    """🔴 **Sự thật đo được 28/09, và nó ⛔ ngược với giả thuyết của B13 §3.4.**

    `ket_xuat.dung_lenh` nạp ĐÚNG hai đầu vào (`duong_video`, `duong_master`) và
    map `1:a:0`. `duong_lop` **chỉ** bị đếm để đối chiếu độ dài — nó ⛔ không vào
    `cmd`. ⇒ `1,15 × 1,3333 = 1,53` ⛔ KHÔNG hình thành được, nên một `raise` cho
    nó sẽ là một nhánh ⛔ không bao giờ chạy (`ma-phong-thu-cho-ca-khong-the-
    xay-ra`, 4 ca ngày 24/09).

    ⭐ Bài này chốt **sự thật ấy** bằng AST. Ngày nào trình render đọc lại
       `lop[].he_so_toc` thì bài này đỏ, và lúc đó bất biến compound mới có nghĩa.
    """
    ma = (GOC / "apps" / "auto_scan_video" / "ket_xuat.py").read_text("utf-8")
    cay = ast.parse(ma)
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "dung_lenh"),
               None)
    assert ham is not None, "⛔ không còn `ket_xuat.dung_lenh` — bài này đã mù"

    # `duong_lop` chỉ được dùng trong phép đối chiếu ĐỘ DÀI (`len(...)`), ⛔ không
    # bao giờ được nối vào `cmd`.
    dung = [n for n in ast.walk(ham)
            if isinstance(n, ast.Name) and n.id == "duong_lop"]
    assert dung, "⛔ `duong_lop` biến mất khỏi chữ ký — đọc lại giả thuyết B3"
    trong_len = [n for n in ast.walk(ham)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "len"
                 and any(isinstance(a, ast.Name) and a.id == "duong_lop"
                         for a in n.args)]
    assert len(dung) == len(trong_len), (
        "`duong_lop` nay được dùng ở %d chỗ mà chỉ %d chỗ là `len(...)` — nếu "
        "nó đã vào `cmd` thì `he_so_toc` CÓ THỂ thành `atempo` lần hai, và bất "
        "biến compound của B13 §3.4 phải được viết thật"
        % (len(dung), len(trong_len)))


def test_4920_B3_su_lech_giua_ke_hoach_va_ban_phoi_duoc_DEM_va_noi_TO():
    """⭐ Bất biến RẺ và SỐNG thay cho một `raise` nằm chết.

    🔴 Chiều CÓ THẬT ⛔ không phải `1,53`: một đoạn kế hoạch định nén `1,15` để
       trả nợ được trộn ở `he_so_co_gian` (thường `1,0`) ⇒ tiếng **dài hơn chỗ
       kế hoạch chừa**, và `thoi_gian.kiem` ⛔ không bắt được vì nó kiểm chồng
       lấn trên `dai_ms` ĐÃ chia cho `he_so_toc`. Lượt đã đo: 12 đoạn như vậy.
    """
    # Kế hoạch định nén 1,15 để trả nợ; bản phối áp 1,0 ⇒ tiếng DÀI HƠN chỗ
    # kế hoạch chừa, và ⛔ không một phép kiểm nào của `thoi_gian.kiem` bắt được.
    ra = thoi_gian.doi_chieu_he_so_toc({"seg_0012": 1.15, "seg_0031": 1.1422},
                                       {"seg_0012": 1.0, "seg_0031": 1.1422})
    assert ra["so_doan_he_so_lech_ke_hoach"] == 1, (
        "chỗ lệch giữa kế hoạch và bản phối phải ĐẾM ĐƯỢC")
    assert ra["lech"] == [("seg_0012", 1.15, 1.0)], (
        "và phải nói ĐOẠN NÀO — một con số bắt người đọc đi tìm")
    # ⭐ TÍCH của hai máy: hôm nay ⛔ không được thi hành, nhưng phải ĐO ĐƯỢC.
    assert ra["he_so_gop_ke_hoach_x_da_ap_lon_nhat"] == pytest.approx(
        1.1422 * 1.1422, abs=1e-4)

    # ⛔ Không im: mỗi chỗ lệch phải ra một dòng `log.warning` ở giai đoạn.
    src = pathlib.Path(giai_doan_thoi_gian.__file__).read_text("utf-8")
    assert 'for ma, h_ke, h_ap in doi_chieu["lech"]' in src, (
        "sự lệch ⛔ không được IM — phải log từng đoạn")
    assert "log.warning" in src


# ══════════════════════════════════════════════════════════════════════════════
#  Vân tay / cache
# ══════════════════════════════════════════════════════════════════════════════

def test_4920_van_tay_ban_ke_la_cai_VO_HIEU_cache_khong_phai_PHIEN_BAN_NAN():
    """⭐ `he_so_co_gian` nằm TRONG `ban_ke.json` ⇒ `checksum` đổi ⇒
       `van_tay_ke_hoach` đổi. `PHIEN_BAN_NAN` ⛔ không vào vân tay nào."""
    a = thoi_gian.van_tay_ke_hoach(checksum_van_ban="vb", ban_ke_tieng="ke_CU",
                                  che_do="fit_original")
    b = thoi_gian.van_tay_ke_hoach(checksum_van_ban="vb", ban_ke_tieng="ke_MOI",
                                  che_do="fit_original")
    assert a != b, (
        "`van_tay_ke_hoach` phải bấm `ban_ke_tieng` — nếu không, bản vá A2 đổi "
        "`he_so_co_gian` mà `timing_align` trả lại bản phối CŨ")
    # ⚠️ `PHIEN_BAN_NAN` tăng theo hợp đồng của chính nó (đổi CHÍNH SÁCH nắn),
    #    nhưng nó ⛔ không vô hiệu cache của giai đoạn nào — chú thích của nó khai
    #    đúng điều đó, và bài này chốt lời khai ấy.
    assert nan_cho_vua.PHIEN_BAN_NAN >= 6, (
        "đổi mẫu số của `he_so_co_gian` là đổi chính sách nắn ⇒ phải tăng "
        "`PHIEN_BAN_NAN` theo hợp đồng ghi ở chính hằng số đó")
    vt_giong = inspect.getsource(giai_doan_giong._van_tay)
    assert "PHIEN_BAN_NAN" not in vt_giong, (
        "`_van_tay` ⛔ KHÔNG được bấm `PHIEN_BAN_NAN`: tệp `.wav` ⛔ không đổi "
        "một byte, nên nâng nó là mua lại toàn bộ lượt TTS bằng tiền thật")
