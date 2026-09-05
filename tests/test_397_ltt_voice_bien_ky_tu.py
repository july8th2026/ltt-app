"""Biên của trần ký tự, và phép đếm ở hai phía có nói cùng một con số không.

## Vì sao tệp này tồn tại

Ngày 03/09/2026 hai trần được tách ra: `TRAN_MOI_LUOT_SINH` (trần **chất lượng**
của model, 1.500) và `TRAN_KY_TU_CONG_KHAI` (trần **ngân sách tài nguyên** của
một yêu cầu). Trước đó chúng là một con số, và hệ quả là một văn bản 1.501 ký tự
bị **từ chối** — trong khi chính thông điệp lỗi lại nói tới một đường long-form
chưa ai xây.

⛔ Đường ấy nay đã xây. Nhưng "đã xây" và "không bao giờ gộp lại nữa" là hai
   điều khác nhau, và chỉ điều thứ hai mới được bảo vệ bằng một phép kiểm.

⭐ Nên chốt ở đây **không** phải "trần bằng 100.000". Chốt là: **1.501 phải đi
   qua**. Mệnh đề ấy bất biến với mọi lần nới trần sau này, trong khi một con số
   chép lại sẽ đỏ ở đúng lượt commit nâng trần — tức nó phạt việc làm đúng.

## 🔴 PHẦN THỨ HAI: HAI PHÍA ĐẾM BẰNG HAI THƯỚC KHÁC NHAU

`len()` của Python đếm **điểm mã**. `"...".length` của JS đếm **đơn vị mã
UTF-16**. Với ASCII và tiếng Việt dựng sẵn (NFC) hai số bằng nhau — nên lệch này
sống được rất lâu mà không ai thấy. Chúng tách nhau ở mọi ký tự ngoài BMP:

    "\U0001F600"  ->  len() = 1,  .length = 2

Và lệch ấy **đẩy về phía sai**: `maxlength` của ô nhập (cũng đếm đơn vị mã) chặn
sớm hơn máy chủ, nên một bài đầy emoji bị trình duyệt cắt trong khi máy chủ vẫn
nhận. Khách mất chữ, không lỗi nào báo. Đó là lý do `maxlength` đã bị gỡ khỏi
`ltt_voice_studio.html` và `voice.js` chuyển sang `demKyTu()`.

⚠️ Phép kiểm dưới đây **không chạy JavaScript** — không có runtime JS trong bộ
   test này. Nó chốt hai thứ mà Python kiểm được, và cả hai đều là điều kiện
   CẦN của tính đúng:

     ① máy chủ đếm bằng điểm mã (nên `demKyTu` mới là thứ phải khớp với nó)
     ② `maxlength` KHÔNG quay lại ô nhập, và `voice.js` KHÔNG quay lại `.length`

   Điều kiện ĐỦ — rằng `demKyTu` chạy đúng trong trình duyệt thật — được xác
   minh bằng tay trong lượt kiểm GUI, và ghi ở
   `docs/LTT_VOICE/AUTONOMOUS_AUDIT/02_CHARACTER_CONTRACT.md`.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from apps.ltt_voice.tham_so_cong_khai import (TRAN_KY_TU_CONG_KHAI,
                                              TRAN_MOI_LUOT_SINH)

def _bo_chu_thich(js: str) -> str:
    """Bo `/* */` va `//` khoi ma JS.

    🔴 VI SAO PHEP KIEM PHAI DOC MA CHU KHONG DOC CA TEP.

       Ban dau cua `test_nhap_txt_khong_cat_lang_le` tim chuoi `s.slice(0, tran)`
       trong toan bo tep — va no DO NGAY, vi chinh chu thich giai thich cai bay
       da trich dan doan ma ay. Tuc phep kiem trung phat dung viec ghi lai ly
       do; ai muon no xanh se phai **xoa loi giai thich**.

    ⚠ Ham nay khong phai mot bo phan tich JS day du: no khong hieu `/*` nam
       trong mot chuoi hay trong mot regex. Do la danh doi co y — mot bo phan
       tich that o day la mot phu thuoc moi de tra loi mot cau hoi rat hep.
       `test__bo_chu_thich_tu_kiem` chot dung phan ma no HUA lam duoc.
    """
    import re as _re
    js = _re.sub(r"/\*.*?\*/", " ", js, flags=_re.S)
    return _re.sub(r"(?m)^\s*//.*$", " ", js)


def test__bo_chu_thich_tu_kiem():
    """Bo do quet nao cung phai tu chung minh no do dung thu no noi.

    ⭐ Khong co phep tu-kiem thi mot ham loc hong (vi du: tra ve chuoi rong)
       lam MOI phep kiem dung no thanh xanh vinh vien — mot cai gate im lang
       la mot cai gate khong con la gate.
    """
    assert _bo_chu_thich("a /* x */ b").split() == ["a", "b"]
    assert _bo_chu_thich("  // ghi chu" + chr(10) + "ma()").strip() == "ma()"
    assert "giu" in _bo_chu_thich("giu /* bo */")


GOC = pathlib.Path(__file__).resolve().parents[1]
STUDIO = GOC / "apps" / "ltt_voice" / "templates" / "ltt_voice_studio.html"
VOICE_JS = GOC / "server" / "static" / "voice.js"


# ── Hai trần là HAI thứ ────────────────────────────────────────────────────

def test_tran_yeu_cau_rong_hon_tran_mot_luot():
    """⛔ Mệnh đề chốt, và nó KHÔNG nhắc một con số nào.

    Gộp hai trần lại là lỗi đã xảy ra một lần. Phép kiểm này đỏ ngay lượt ai
    đó gộp lại, và nó xanh với mọi giá trị hợp lệ của cả hai — kể cả sau khi
    trần công khai được nâng tiếp.
    """
    assert TRAN_KY_TU_CONG_KHAI > TRAN_MOI_LUOT_SINH, (
        "Tran cua MOT YEU CAU phai rong hon tran cua MOT LUOT SINH. Bang nhau "
        "nghia la duong long-form da bi go, va van ban dai bi tu choi tro lai.")


# ── Ma trận biên ───────────────────────────────────────────────────────────

def _bien():
    """Các mốc phải kiểm, dựng TỪ hằng số chứ không gõ tay.

    ⭐ `1500`/`1501` gõ thẳng là cố ý: chúng chốt một sự kiện LỊCH SỬ (chỗ trần
       cũ từng nằm), không chốt cấu hình hiện tại. Nếu `TRAN_MOI_LUOT_SINH` đổi
       thì `TRAN_MOI_LUOT_SINH + 1` bên dưới đi theo, còn 1.501 vẫn phải qua —
       vì bài học là "đừng từ chối bài dài", không phải "1.500 thì đặc biệt".
    """
    t = TRAN_KY_TU_CONG_KHAI
    return [
        (1, True), (1499, True), (1500, True), (1501, True),
        (TRAN_MOI_LUOT_SINH, True), (TRAN_MOI_LUOT_SINH + 1, True),
        (2999, True), (3000, True), (5000, True), (10000, True),
        (t - 1, True), (t, True), (t + 1, False),
    ]


@pytest.mark.parametrize("n,nhan", _bien())
def test_bien_tran_cong_khai(n, nhan):
    """Đúng phép so mà `routes/_p_tao.py` dùng: `len(tho) > TRAN`.

    ⛔ Phép kiểm này KHÔNG gọi HTTP, và đó là chủ ý. Một lượt POST thật sẽ
       chạm hàng đợi job, sổ credit và sidecar — tức nó đo bốn hệ thống để trả
       lời một câu hỏi về một phép so sánh. Cửa HTTP đã có phép kiểm riêng
       (`test_347`); cái ở đây chốt **biên**, và biên thì phải rẻ để chạy được
       ở mọi mốc.
    """
    assert (n <= TRAN_KY_TU_CONG_KHAI) is nhan


def test_van_ban_1501_ky_tu_chia_duoc_thanh_nhieu_doan():
    """1.501 ký tự phải RA NHIỀU ĐOẠN, không phải bị từ chối.

    🔴 Đây là phép kiểm quan trọng nhất tệp này. `test_bien_tran_cong_khai`
       chỉ chốt cửa **nhận**; nếu `chia_doan` vẫn trả một đoạn 1.501 ký tự thì
       cửa nhận vô nghĩa — engine sẽ đọc quá trần chất lượng của chính nó, và
       hỏng bằng một giọng trôi chứ không bằng một lỗi.
    """
    from apps.ltt_voice import text_pipeline
    van = ("Cau nay dai vua du de phep chia co cho ma cat. " * 40)[:1501]
    assert len(van) == 1501
    chuan = text_pipeline.chuan_bi(van, tran_moi_doan=TRAN_MOI_LUOT_SINH)
    assert len(chuan.doan) >= 2, "1.501 ky tu phai ra tu HAI doan tro len"
    for d in chuan.doan:
        assert len(d) <= TRAN_MOI_LUOT_SINH, (
            f"mot doan dai {len(d)} ky tu, vuot tran mot luot sinh")


# ── Unicode: máy chủ đếm bằng ĐIỂM MÃ ──────────────────────────────────────

CAC_MAU = [
    ("ascii", "Hello world", 11),
    ("viet_nfc", "Xin chào Việt Nam", 17),
    ("viet_to_hop", "Xin chào", 9),          # a + U+0300 = HAI diem ma
    ("emoji_bmp", "Chào ❤", 6),          # U+2764 nam TRONG BMP
    ("emoji_astral", "Chào \U0001F600", 6),   # ngoai BMP: JS se dem 7
    ("emoji_variation", "\U0001F600️", 2),
    ("xuong_dong", "a\nb\nc", 5),
    ("tron", "Xin chào \U0001F600 hello", 16),
]


@pytest.mark.parametrize("ten,van,mong", CAC_MAU)
def test_may_chu_dem_theo_diem_ma(ten, van, mong):
    """`len()` là thước chính thức, và đây là các giá trị nó cho.

    ⚠️ `emoji_astral` là mẫu quan trọng nhất: `len()` cho 6, `.length` của JS
       cho 7. Mọi mẫu khác khớp ở cả hai thước — nên nếu chỉ kiểm chúng thì
       lỗi này vẫn lọt, đúng như nó đã lọt suốt một năm.
    """
    assert len(van) == mong


def test_astral_thuc_su_lech_giua_hai_thuoc():
    """Bằng chứng rằng phép kiểm trên có nghĩa, không phải trùng hợp.

    ⭐ Không có runtime JS ở đây, nên ta MÔ PHỎNG `.length` bằng độ dài UTF-16
       (`len(s.encode("utf-16-le")) // 2`) — đúng định nghĩa của nó. Nếu một
       ngày hai con số này bằng nhau ở mọi mẫu thì phép kiểm phía trên đã mất
       tác dụng mà không ai hay.
    """
    van = "Chào \U0001F600"
    utf16 = len(van.encode("utf-16-le")) // 2
    assert len(van) == 6 and utf16 == 7, (
        "mau nay phai LECH giua diem ma va don vi ma UTF-16; het lech thi "
        "no khong con chot duoc gi")


def test_cat_theo_don_vi_ma_lam_hong_cap_surrogate():
    """Vì sao `voice.js` phải có `catKyTu` chứ không dùng `slice`.

    Cắt một chuỗi ở giữa một cặp surrogate để lại **một nửa mồ côi** — không
    phải một ký tự, mà là một chuỗi không hợp lệ. Nó không nổ; nó đi tiếp và
    tới máy chủ dưới dạng U+FFFD.
    """
    van = "ab\U0001F600cd"
    nua = van.encode("utf-16-le")[:3 * 2].decode("utf-16-le", "replace")
    assert nua.endswith("�"), (
        "cat theo don vi ma phai de lai mot nua mo coi — neu khong thi mau "
        "nay khong con mo ta duoc cai bay")


# ── Giao diện KHÔNG được quay lại cách đếm cũ ──────────────────────────────

def test_o_nhap_khong_co_maxlength():
    """⛔ `maxlength` chặn theo ĐƠN VỊ MÃ, nên nó cắt nhầm mọi bài có emoji.

    Đây là một chốt **mạnh hơn thứ nó đo**: nó không chứng minh được phép đếm
    trong trình duyệt là đúng, nhưng nó làm cho bản sửa sai *không thể lặng lẽ
    quay lại*. Ai thêm `maxlength` trở lại sẽ thấy phép kiểm này đỏ và phải
    đọc lý do.
    """
    html = STUDIO.read_text(encoding="utf-8")
    khoi = re.search(r'<textarea[^>]*id="lv-text".*?>', html, re.S)
    assert khoi, "khong tim thay o nhap chinh cua Studio"
    assert "maxlength" not in khoi.group(0), (
        "O nhap chinh KHONG duoc co `maxlength`: no dem don vi ma UTF-16 trong "
        "khi may chu chan bang len() (diem ma), nen mot bai day emoji bi trinh "
        "duyet cat trong khi may chu van nhan. Tran nay do voice.js::dem() "
        "cuong che bang demKyTu(), va no chan o CHO NOP chu khong o cho go.")


def test_voice_js_dem_bang_diem_ma():
    """`dem()` phải gọi `demKyTu`, không đọc thẳng `.length`."""
    js = VOICE_JS.read_text(encoding="utf-8")
    assert "function demKyTu" in js, "thieu ham dem theo diem ma"
    assert re.search(r"var n = demKyTu\(oText\.value\)", js), (
        "dem() phai dem bang demKyTu(); `oText.value.length` dem don vi ma "
        "UTF-16 va se lech voi len() cua may chu o moi emoji")


def test_nhap_txt_khong_cat_lang_le():
    """⛔ Nhập TXT phải giữ NGUYÊN tệp, kể cả khi nó dài hơn trần.

    Bản trước làm `oText.value = bicat ? s.slice(0, tran) : s` — một tài liệu
    120.000 ký tự mất 20.000 ký tự cuối ngay lúc nhập, và mất **không hoàn tác
    được**: văn bản gốc không còn ở đâu trong trang nữa.
    """
    ma = _bo_chu_thich(VOICE_JS.read_text(encoding="utf-8"))
    assert "s.slice(0, tran)" not in ma, (
        "nhap TXT khong duoc cat van ban. Giu nguyen, roi de dem() bat trang "
        "thai vuot tran — khach tu chon cat cho nao.")
    assert "oText.value = s;" in ma, "nhap TXT phai gan NGUYEN van ban vao o"


def test_song_am_co_tran_thoi_luong():
    """⛔ `decodeAudioData` giải mã cả tệp; ở trần mới đó là ~1,4 GB.

    48 kHz mono 16-bit = 96 KB/giây; bản giải mã float32 gấp đôi lần nữa. Ở
    100.000 ký tự (~5.035 giây) một lần vẽ sóng ngốn ~483 MB tải về + ~967 MB
    PCM. Chú thích cũ ngay trên `veSong` đã dự báo đúng điều này và nói *"nếu
    trần ký tự được nới nhiều lần thì chỗ này phải đổi"* — trần đã nới ngày
    03/09, chỗ ấy thì không.
    """
    js = VOICE_JS.read_text(encoding="utf-8")
    assert "TRAN_GIAY_SONG" in js, "thieu tran thoi luong cho song am that"
    assert "function songDeu" in js, (
        "ban doc dai phai ve mot track PHANG, khong duoc de `songGia` (song "
        "ngau nhien suy tu URL) nam lai vinh vien — khach se doc no nhu du "
        "lieu that cua ban thu")


def test_moi_duong_thoat_cua_veSong_deu_ve_song_deu():
    """⛔ MỌI nhánh `return` trong `veSong` phải vẽ `songDeu` trước.

    🔴 ĐÂY LÀ LỖI TÔI TỰ TẠO RA RỒI TỰ BẮT ĐƯỢC KHI SOÁT LẠI DIFF.

       Bản đầu của trần thời lượng chỉ xử lý **hai** nhánh — dài hơn trần, và
       không có `au`. Nhánh thứ ba, `!window.AudioContext`, vẫn `return` trần
       như mã cũ. Nhưng ở mã cũ điều đó vô hại vì `songGia` sắp bị thay bởi
       sóng thật; sau khi thêm trần thì **không có gì thay nó nữa**, nên trên
       một trình duyệt không có `AudioContext` (Safari cũ, vài WebView) nhiễu
       ngẫu nhiên suy từ URL sẽ nằm lại vĩnh viễn — đúng thứ cái trần này sinh
       ra để tránh.

    ⭐ Bài học: **một bất biến mới không tự lan sang những nhánh có sẵn.** Ba
       nhánh ấy đã đúng theo luật cũ ("rồi sẽ có sóng thật"), nên chúng không
       trông như lỗi. Chỉ khi phát biểu bất biến ra thành lời — *mọi đường
       thoát đều phải vẽ* — thì nhánh thiếu mới lộ.

    ⚠️ Phép kiểm này đọc **cấu trúc**, không chạy JS: nó đếm số `return` trong
       thân hàm và đòi mỗi cái đi kèm `songDeu`. Thô, nhưng nó bắt đúng lớp lỗi
       đã xảy ra — một nhánh mới được thêm mà quên vẽ.
    """
    js = _bo_chu_thich(VOICE_JS.read_text(encoding="utf-8"))
    than = js[js.index("function veSong("):]
    than = than[:than.index("var Ctx =")]
    thoat = [d for d in than.splitlines() if "return;" in d]
    assert thoat, "khong tim thay duong thoat nao — mau ham da doi, doc lai"
    for d in thoat:
        assert "songDeu" in d or "songDeu(canvas); return;" in d, (
            f"duong thoat khong ve gi: {d.strip()!r}\n"
            "Moi `return` truoc khi giai ma PHAI goi `songDeu(canvas)`, neu "
            "khong `songGia` (song ngau nhien) se nam lai vinh vien va khach "
            "doc no nhu du lieu that cua ban thu.")


# ── Con số hiện ra phải đúng quy ước đọc số ────────────────────────────────

@pytest.mark.parametrize("tep", [
    "ltt_voice_studio.html",
    "ltt_voice_api.html",
])
def test_tran_hien_qua_filter_so(tep):
    """⛔ `100000` phải hiện thành `100.000`, và bằng filter CHUNG.

    `server/templating.py::_so` được dựng ra đúng vì lỗi này: đo 25/08 khu API
    hiện `50000 credit` trong khi trang VPS hiện `149.000`. Một con số mắt phải
    đếm chữ số mới đọc được là một con số bị đọc nhầm một bậc.

    ⚠️ Chốt cả việc KHÔNG tự viết formatter tại chỗ. Màn Studio từng có
       `"{:,}".format(tran_ky_tu).replace(",", ".")` — đúng kết quả, nhưng nó
       là bản sao thứ hai của một quy ước, và bản sao thì trôi.
    """
    html = (GOC / "apps" / "ltt_voice" / "templates" / tep).read_text(
        encoding="utf-8")
    assert re.search(r"tran_ky_tu\s*\|\s*so", html), (
        f"{tep}: tran ky tu phai hien qua filter chung `|so`")
    assert '"{:,}".format(tran_ky_tu)' not in html, (
        f"{tep}: dung filter `|so`, dung viet lai quy uoc dinh dang so")
