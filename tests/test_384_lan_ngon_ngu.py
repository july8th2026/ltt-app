r"""
test_384 — LÀN ngôn ngữ của giọng: `apps/ltt_voice/lan_ngon_ngu.py` + bộ lọc.

## Vì sao tệp này tồn tại

Cột `voice_profile.ngon_ngu` có từ đầu, và tới 01/09/2026 nó **không nơi nào
đọc** — khai rồi bỏ đó. Hậu quả đo được trên production: cả **bốn** giọng của
kho dùng chung đều mang `ngon_ngu = "vi"`, kể cả hai giọng mà chính tên hiển thị
đã ghi *"EN male"* / *"EN female"*. Chúng lấy giá trị **mặc định** và không ai
đặt.

⛔ Sai suốt mà không ai thấy, chính xác vì cột ấy không ai đọc. **Một dữ liệu
   sai chưa có hậu quả là dữ liệu sai trốn được lâu nhất** — nó chỉ nổ vào ngày
   ai đó bắt đầu tin nó.

⇒ Tệp này chốt hai điều: làn **được đọc** ở những chỗ nó phải được đọc, và
  `doi_chieu` **cảnh báo chứ không chặn**.

## ⚠️ PHẠM VI ĐÃ HẸP LẠI — đọc trước khi tin một dòng xanh ở đây

~~Trước 2026-09-10, "cảnh báo chứ không chặn" là hợp đồng của **cả sản phẩm**.~~
**ĐÃ THAY bởi Q121 (2026-09-10):** cửa nộp nay **chặn** một yêu cầu lệch làn.

`doi_chieu` thì vẫn cảnh-báo-không-chặn, và mọi phép kiểm ở đây vẫn đúng — chúng
nói về **hàm ấy**. Nhưng chúng không còn nói gì về *sản phẩm*, nên đừng đọc dòng
xanh của tệp này thành "một yêu cầu lệch làn vẫn chạy được".

Hợp đồng đang hiệu lực: `apps/ltt_voice/lan_ngon_ngu.py::quyet_dinh`, chốt ở
`tests/test_355_hop_dong_lan_giong.py`.
"""
from __future__ import annotations

import pathlib

import pytest

from apps.ltt_voice import lan_ngon_ngu as L

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── đoán ngôn ngữ ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Bạn có thể mua vé ở đây.",
    "Hôm nay trời đẹp.",
    "Đây là một câu.",
    "Giá cổ phiếu tăng mạnh.",
])
def test_co_dau_tieng_viet_thi_chac_chan_vi(text):
    assert L.doan_ngon_ngu(text) == "vi"


@pytest.mark.parametrize("text", [
    "The quick brown fox jumps over the lazy dog.",
    "Please confirm that you have received this message.",
    "Our team delivered the project ahead of schedule.",
])
def test_du_tu_chuc_nang_thi_en(text):
    assert L.doan_ngon_ngu(text) == "en"


@pytest.mark.parametrize("text", [
    "Ban co the mua ve o day.",          # tiếng Việt KHÔNG DẤU
    "Xin chao moi nguoi.",
    "Hom nay troi dep.",
    "OK",
    "",
])
def test_map_mo_thi_tra_None_chu_khong_doan_bua(text):
    """`None` là một câu trả lời ĐẦY ĐỦ, không phải một thất bại.

    🔴 Tiếng Việt viết không dấu chỉ gồm chữ ASCII — **không phân biệt được**
       với tiếng Anh bằng bảng mã. Đoán bừa `"vi"` cho mọi thứ mập mờ sẽ đẻ ra
       cảnh báo sai ở mọi câu tiếng Anh ngắn; đoán bừa `"en"` thì ngược lại.
       Cả hai đều dẫn tới **một cảnh báo hay sai, tức một cảnh báo bị bỏ qua**
       — kể cả lúc nó đúng.
    """
    assert L.doan_ngon_ngu(text) is None


def test_tu_chuc_nang_khong_trung_am_tiet_tieng_viet_khong_dau():
    """Tập từ tiếng Anh phải tránh mọi âm tiết tiếng Việt viết không dấu.

    ⛔ Thêm "can", "co", "do", "la", "ma", "an", "the" (đã có, nhưng chú ý)…
       vào `TU_ANH` là biến "Ban co the mua ve" thành tiếng Anh. Phép kiểm này
       chốt tập từ ấy không lấn sang những âm tiết Việt hay gặp nhất.
    """
    va = {"can", "co", "do", "la", "ma", "an", "ba", "ta", "ca", "cua", "va",
          "vi", "di", "toi", "khong", "mot", "hai", "nam", "cho", "cai"}
    lan = L.TU_ANH & va
    assert not lan, f"tu chuc nang tieng Anh trung am tiet Viet khong dau: {lan}"


def test_mot_tu_tieng_anh_le_khong_du_de_ket_luan():
    """Một thuật ngữ tiếng Anh chèn vào câu Việt không dấu KHÔNG làm nó thành EN."""
    assert L.doan_ngon_ngu("Ban mo file trong that muc nay") is None
    assert L.TOI_THIEU_TU_ANH >= 2


# ── đối chiếu ───────────────────────────────────────────────────────────────

def test_doi_chieu_canh_bao_khi_lech_lan():
    assert L.doi_chieu("en", "Bạn có thể mua vé ở đây.")
    assert L.doi_chieu("vi", "The quick brown fox jumps over the lazy dog.")


def test_doi_chieu_im_lang_khi_khop_hoac_khong_chac():
    assert L.doi_chieu("vi", "Bạn có thể mua vé ở đây.") == ()
    assert L.doi_chieu("en", "The quick brown fox and that dog.") == ()
    assert L.doi_chieu("vi", "Ban co the mua ve o day.") == ()   # không chắc
    assert L.doi_chieu("", "Bất cứ gì.") == ()                    # chưa có làn
    assert L.doi_chieu("xx", "Bất cứ gì.") == ()                  # làn lạ


def test_KHONG_BAO_GIO_nem_loi():
    """Đối chiếu làn phải là một CẢNH BÁO, không bao giờ là một cửa chặn.

    🔴 Chặn theo phán đoán ngôn ngữ sẽ từ chối công việc hợp lệ của khách đang
       gõ tiếng Việt **không dấu** — và từ chối với một lý do họ không sửa được,
       vì họ đang gõ đúng thứ họ định gõ.
    """
    for lan in ("vi", "en", "", "xx", None):
        for t in ("", "abc", "Bạn có thể", "The and that", "!!!", "123"):
            r = L.doi_chieu(lan, t)          # không được ném
            assert isinstance(r, tuple)


def test_chuoi_canh_bao_la_HANG_de_dich_duoc():
    """`N_()` phải nhìn thấy một chuỗi HẰNG, không phải một câu ghép động.

    ⛔ Ghép bằng f-string thì bộ trích không lấy được chuỗi vào `.po`, và nó
       hỏng **lặng lẽ**: trang tiếng Anh hiện một câu tiếng Việt. Nên khuôn có
       chỗ trống `{lan_giong}` / `{lan_text}` và `dien_canh_bao` điền sau.
    """
    src = (GOC / "apps" / "ltt_voice" / "lan_ngon_ngu.py").read_text(encoding="utf-8")
    import ast
    cay = ast.parse(src)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "doi_chieu")
    # ⛔ Hỏi CÂY CÚ PHÁP, đừng khớp chuỗi: một bánh cóc khớp với chính lời giải
    #    thích của nó thì không chốt gì (đã mắc lỗi ấy bốn lần trong dự án này).
    for n in ast.walk(ham):
        assert not isinstance(n, ast.JoinedStr), (
            "doi_chieu dang ghep f-string — chuoi se khong vao duoc file dich")


# ── nối vào ứng dụng ────────────────────────────────────────────────────────

def test_giai_giong_doi_chieu_lan_o_CA_HAI_nhanh():
    """`features.giai_giong` phải THẬT SỰ hỏi hợp đồng làn, ở **cả hai** nhánh.

    ⛔ Trước 01/09 nó trả `()` cứng ở cả hai nhánh. Một chỗ trống có sẵn cho
       cảnh báo mà không ai điền vào trông giống hệt một chỗ đã điền đúng.

    ⚠️ VIẾT LẠI 2026-09-10 (Q121), và lý do đáng ghi: bản cũ đếm lời gọi
       `doi_chieu` **theo tên**. Khi cửa chặn ra đời, cả hai nhánh chuyển sang
       `_chot_lan` — cùng mệnh đề, cùng hai nhánh, nhưng phép kiểm ĐỎ. Nó không
       bắt được một hồi quy; nó bắt được một lần đổi tên.

    ⭐ Nên nay chốt **chuỗi hai mắt xích**: hai nhánh cùng gọi một cửa duy nhất,
       và cửa ấy hỏi `lan_ngon_ngu.quyet_dinh`. Mệnh đề ấy bất biến với tên hàm
       trung gian, và nó vẫn đỏ nếu một nhánh bỏ qua hợp đồng.

    Phần *chặn* của hợp đồng chốt ở `tests/test_355_hop_dong_lan_giong.py`.
    """
    import ast
    src = (GOC / "apps" / "ltt_voice" / "features.py").read_text(encoding="utf-8")
    cay = ast.parse(src)

    def _ham(ten):
        return next(n for n in ast.walk(cay)
                    if isinstance(n, ast.FunctionDef) and n.name == ten)

    gg = _ham("giai_giong")
    cua = [n for n in ast.walk(gg)
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_chot_lan"]
    assert len(cua) >= 2, (
        "giai_giong phai hoi hop dong lan o CA HAI nhanh (preset va nhan ban)")

    # Mắt xích thứ hai: cửa ấy phải thật sự hỏi hợp đồng, không tự phán.
    chot = _ham("_chot_lan")
    hoi = [n for n in ast.walk(chot)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "quyet_dinh"]
    assert hoi, "_chot_lan khong goi lan_ngon_ngu.quyet_dinh"


def test_danh_sach_co_bo_loc_lan_va_MAC_DINH_KHONG_LOC():
    import inspect

    from apps.ltt_voice import tham_chieu
    ts = inspect.signature(tham_chieu.danh_sach).parameters
    assert "ngon_ngu" in ts, "thieu bo loc lan o danh_sach()"
    assert ts["ngon_ngu"].default == "", (
        "bo loc lan phai MAC DINH TAT: `ngon_ngu` tung la cot khong ai doc nen "
        "du lieu cu co the trong — bat san la giau mat giong cua chinh khach")


def test_muc_chua_dat_lan_bi_AN_khoi_mot_lan_NHUNG_duoc_DEM_RA():
    """Giọng chưa khai làn: **ẩn** khỏi một làn cụ thể, và **đếm ra**.

    🔴 PHÉP KIỂM NÀY ĐÃ ĐẢO CHIỀU (Task 11, D002 UI/65e099af), và lý do đáng
       ghi lại.

       Bản cũ chốt điều ngược hẳn — *"giọng chưa có làn phải hiện ở mọi
       làn"* — với lý lẽ: dữ liệu cũ có thể trống `ngon_ngu`, ẩn đi là làm
       khách mất giọng của chính mình.

       Lý lẽ ấy đúng cho `gioi` / `vung` / `phong_cach`: ba trục đó chỉ **sắp
       xếp**. Nó sai cho làn, vì làn quyết định **chất lượng đầu ra**. Cho một
       giọng không rõ ngôn ngữ trôi vào làn `vi` là đưa nó vào luồng
       production như một giọng `vi` hợp lệ.

    ⛔ NHƯNG PHÉP KIỂM MỚI KHÔNG CHỈ CHỐT VẾ "ẨN", và đó là chỗ nó mạnh hơn bản
       cũ chứ không phải dễ hơn. Chốt mỗi "ẩn" thì một bản vá tương lai xoá
       luôn phần đếm vẫn xanh — và khi ấy giọng biến mất **im lặng**, tức nỗi
       lo của bản cũ thành sự thật. Hai vế phải cùng có mặt:

         · `lanHop` — ẩn khỏi làn không khớp;
         · `chuaRo` + `capNhatDongLan` — đếm và nói ra, kèm đường sửa.

    ⚠️ Đây là phép kiểm TĨNH trên một tệp JS (pytest không chạy được trình
       duyệt). Hành vi thật được chốt trên Chrome khi kiểm GUI thủ công; ở
       đây chỉ giữ cho hai cơ chế ấy không bị gỡ mất một vế.
    """
    js = (GOC / "server" / "static" / "voice.js").read_text(encoding="utf-8")
    assert "!d.lan || d.lan === locLan" not in js, (
        "bo loc lan KHONG duoc cho qua muc `data-lan` rong nua — xem docstring")
    assert "var lanHop = !locLan || d.lan === locLan;" in js, (
        "thieu ve AN: muc chua khai lan phai bi loc khoi mot lan cu the")
    for manh in ("chuaRo", "capNhatDongLan"):
        assert manh in js, (
            f"thieu ve DEM RA (`{manh}`): an ma khong noi la giong bien mat "
            "im lang — dung noi lo ma ban cu cua phep kiem nay neu ra")


def test_moi_man_dung_bo_chon_deu_truyen_nhan_lan():
    """Thiếu `nhan_lan` ở một màn ⇒ Jinja ném `UndefinedError` ĐÚNG TRÊN MÀN ĐÓ.

    ⛔ Và chỉ khi ai đó mở đúng màn ấy. Một lỗi mẫu chỉ nổ ở một trong ba trang
       là lỗi lọt qua mọi lượt thử tay không đi hết cả ba.
    """
    tmpl = GOC / "apps" / "ltt_voice" / "templates"
    dung = [p.name for p in tmpl.glob("*.html")
            if '_voice_chon.html' in p.read_text(encoding="utf-8")]
    assert len(dung) >= 3, dung
    src = "\n".join(
        (GOC / "apps" / "ltt_voice" / "routes" / f).read_text(encoding="utf-8")
        for f in ("_p_tao.py", "_p_giong.py", "_p_du_an.py"))
    assert src.count("nhan_lan") >= 3, (
        f"{len(dung)} man dung bo chon giong nhung chi {src.count('nhan_lan')} "
        f"cho truyen `nhan_lan`")


# ── ngôn ngữ KHÁCH KHAI thay cho phép đoán (Studio §12) ──────────────────────

def test_khai_bao_thay_cho_phep_doan():
    """🔴 GIÁ TRỊ CỦA Ô `NGÔN NGỮ` NẰM ĐÚNG Ở CHỖ PHÉP ĐOÁN IM LẶNG.

    `doan_ngon_ngu` cố ý trả `None` khi không đủ dấu hiệu, và im lặng khi ấy là
    quyết định đúng — một cảnh báo hay sai là một cảnh báo bị bỏ qua.

    ⛔ Nhưng cái giá của nó: **ca im lặng nhiều nhất lại là ca cần nhắc nhất**.
       Một câu tiếng Anh NGẮN đọc bằng giọng Việt không đủ dấu hiệu để máy đoán,
       nên khách không được nhắc gì cả — dù đó chính là ca chất lượng sẽ tụt.

    ⇒ Khách khai được thì máy hết phải đoán. Đó là toàn bộ lý do ô ấy tồn tại,
      và phép kiểm này chốt đúng mệnh đề đó.
    """
    ngan = "Go now."
    assert L.doan_ngon_ngu(ngan) is None, (
        "ca thu phai la ca may KHONG doan duoc, neu khong no khong chung minh gi")

    # Không khai ⇒ im lặng (hành vi cũ, vẫn đúng).
    assert L.doi_chieu("vi", ngan) == ()

    # Khai `en` cho một giọng làn `vi` ⇒ cảnh báo.
    assert L.doi_chieu("vi", ngan, "en") != ()

    # Khai đúng làn ⇒ vẫn im.
    assert L.doi_chieu("vi", ngan, "vi") == ()


def test_khai_bao_la_khong_hop_le_thi_lui_ve_phep_doan():
    """Giá trị lạ không được làm hỏng gì — nó chỉ đưa ta về hành vi cũ."""
    vi = "Hôm nay trời đẹp và tôi đi dạo ngoài phố."
    for xau in ("", "auto", "xx", None):
        assert L.doi_chieu("vi", vi, xau) == ()


def test_chuan_hoa_kep_ngon_ngu_la_ve_auto():
    """Cửa vào ép giá trị lạ về `auto`, và phép ép ấy ở `features` chứ không ở
    route — Public API đi THẲNG xuống job, không qua route nào."""
    from apps.ltt_voice import features

    for xau, mong in (("EN", "en"), ("vi", "vi"), ("bậy", "auto"),
                      ("", "auto"), (None, "auto")):
        yc = features.chuan_hoa({"text": "xin chào", "ngon_ngu": xau})
        assert yc.ngon_ngu == mong, xau
