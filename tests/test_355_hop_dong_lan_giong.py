r"""
test_355 — HỢP ĐỒNG tương thích làn ngôn ngữ VI/EN (Q121, 2026-09-10).

## Vì sao tệp này tồn tại, tách khỏi `test_384`

`test_384` chốt quyết định **cũ**: làn *cảnh báo, không chặn*. Nó vẫn đúng ở
phần nó chốt (phép đoán, bộ lọc, nhãn), và nó vẫn ở lại. Tệp này chốt thứ
`test_384` **không thể** chốt, vì lúc viết nó điều đó chưa tồn tại: một yêu cầu
lệch làn **không đi qua được cửa nộp**.

## 🔴 Bốn thứ audit tìm ra, và cả bốn đều IM LẶNG CHO QUA

  ① `features.giai_giong` gõ thẳng chuỗi `"vi"` cho mọi giọng mẫu. Không phải
     một phép đọc dữ liệu — một hằng số. Bản chép thứ hai của nó nằm trong
     `_voice_chon.html` (`data-lan="vi"`), và một bản chép trong khuôn mẫu
     **không có cách nào tự biết là nó đã cũ**.
  ② Cảnh báo lệch làn được sinh ra rồi **bị vứt** ở cả hai người gọi
     (`ref_b64, preset, _ = …`).
  ③ `routes/_p_tao.tao` nhận ô `Ngôn ngữ` của khách rồi **không đưa nó vào
     `params`** lúc nộp job ⇒ worker luôn thấy `"auto"`.
  ④ Giọng **chưa rõ làn** (`ngon_ngu = ""`, có thật ở dữ liệu nhập kho cũ) rơi
     vào nhánh "chưa có làn ⇒ im lặng" và đi thẳng tới GPU.

⇒ Nên phép kiểm ở đây không hỏi "có hàm đối chiếu không" (có, và nó chạy). Nó
  hỏi **"một yêu cầu lệch làn có tạo ra được một job không"** — câu duy nhất mà
  cả bốn lỗi trên đều trả lời sai.

## ⛔ Và một phép kiểm ở đây phải chống được ĐÚNG cái bẫy ngược lại

Chặn theo phán đoán ngôn ngữ **thô** sẽ từ chối tiếng Việt viết không dấu — thứ
chỉ gồm chữ ASCII và không phân biệt được với tiếng Anh bằng bảng mã. Nên có
`test_van_ban_map_mo_KHONG_BAO_GIO_bi_chan`, và nó quan trọng ngang những phép
kiểm chặn: một cửa chặn quá tay đắt hơn hẳn một cửa chặn thiếu, vì nó hỏng với
**khách đang gõ đúng thứ họ định gõ**.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from apps.ltt_voice import features
from apps.ltt_voice import giong_mau as gm
from apps.ltt_voice import lan_ngon_ngu as L

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Văn bản ĐỦ DẤU HIỆU cho mỗi làn. Dùng chung để mọi phép kiểm dưới đây nói về
#: cùng một tập đầu vào — một ca thử mà máy không kết luận được thì nó không
#: chứng minh gì cả, và đó là lỗi đã mắc ở `test_384` một lần rồi.
VI_RO = "Xin chào, hôm nay trời rất đẹp và tôi đi dạo ngoài phố."
EN_RO = "The quick brown fox jumps over the lazy dog that we know."


def test_ca_thu_dung_la_ca_may_KET_LUAN_DUOC():
    """Đối chứng cho chính bộ dữ liệu thử ở trên.

    ⛔ Nếu `doan_ngon_ngu` trả `None` cho hai câu này thì mọi phép kiểm "chặn"
       dưới đây sẽ **xanh vì lý do sai** — chúng sẽ đo nhánh `NGUON_THEO_GIONG`
       chứ không đo nhánh lệch làn. Một phép kiểm xanh-rỗng trông y hệt một phép
       kiểm xanh.
    """
    assert L.doan_ngon_ngu(VI_RO) == L.LAN_VI
    assert L.doan_ngon_ngu(EN_RO) == L.LAN_EN


# ── 1. Danh mục preset: làn hợp lệ, không trùng mã ──────────────────────────

def test_moi_preset_co_lan_HOP_LE():
    """⛔ Không có preset nào được mang làn rỗng hay một giá trị ngoài hợp đồng.

    Rỗng nghĩa là **bị chặn** (xem `quyet_dinh`), nên một preset rỗng làn là một
    giọng đang bày bán mà không ai đọc được bằng nó.
    """
    xau = [g.ma for g in gm.DANH_SACH if g.ngon_ngu not in L.LAN_HOP_LE]
    assert not xau, f"preset thieu lan hoac lan la: {xau}"


def test_khong_co_ma_giong_trung_TRONG_CA_HAI_KHO():
    """Trùng mã giữa giọng mẫu và giọng nhân bản là một danh tính hai nghĩa.

    ⭐ `test_345` đã chốt "không mã nào trùng **trong** danh sách preset". Phép
       kiểm này chốt mệnh đề rộng hơn và là mệnh đề thật sự quan trọng: mã giọng
       mẫu **là chính tên nó**, còn mã giọng nhân bản là `vc_<32 hex>` — nên hai
       không gian tên phải rời nhau bằng HÌNH DẠNG, không bằng may mắn.
    """
    ma = [g.ma for g in gm.DANH_SACH]
    assert len(ma) == len(set(ma)), [m for m in ma if ma.count(m) > 1]
    va_cham = [m for m in ma if m.startswith("vc_")]
    assert not va_cham, (
        f"ten preset lan sang khong gian ten cua giong nhan ban: {va_cham}")


def test_lan_cua_preset_SUY_TU_DU_LIEU_chu_khong_go_tay():
    """🔴 Mệnh đề chính của Q121 ở phía danh mục.

    ⛔ Đối chứng là phần làm phép kiểm này có nghĩa: nó dựng một preset **giả**
       mang một vùng miền không thuộc tiếng Việt và đòi làn phải rỗng. Một bản
       cài đặt gõ `return "vi"` sẽ ĐỎ ở dòng đó — còn nếu chỉ kiểm hai mươi
       giọng thật (vốn đều là `vi`) thì `return "vi"` xanh trơn tru.
    """
    assert L.lan_tu_vung("bac") == L.LAN_VI
    assert L.lan_tu_vung("trung") == L.LAN_VI
    assert L.lan_tu_vung("nam") == L.LAN_VI
    for la in ("", "us", "uk", "en", "bắc", None):
        assert L.lan_tu_vung(la) == L.KHONG_RO, la


def _bo_chu_thich_jinja(html: str) -> str:
    """Bỏ mọi khối `{# … #}` khỏi khuôn mẫu trước khi quét.

    🔴 BẮT BUỘC, và bản đầu của phép kiểm dưới đây đã ĐỎ vì thiếu nó — trên
       chính đoạn chú thích *giải thích rằng không được gõ tay `data-lan`*.

    ⭐ Đó là một hạng lỗi có tên trong dự án này: **bộ dò quét văn bản trừng
       phạt việc giải thích**. Một bánh cóc khớp với lời giải thích của chính nó
       thì không chốt gì cả — nó chỉ dạy người sau đừng viết chú thích.
    """
    import re
    return re.sub(r"\{#.*?#\}", "", html, flags=re.S)


def test_khong_con_danh_sach_VI_EN_go_tay_trong_HTML():
    """⛔ `data-lan` trong khuôn mẫu phải ĐỌC dữ liệu, không gõ hằng số.

    Đây là bản chép mà không phép kiểm nào cũ nhìn thấy: nó nằm ngoài `.py`, nên
    mọi bánh cóc đọc AST đều đi qua nó.
    """
    tho = (GOC / "apps" / "ltt_voice" / "templates"
           / "_voice_chon.html").read_text(encoding="utf-8")
    html = _bo_chu_thich_jinja(tho)

    # Đối chứng: phép quét phải THẤY được thứ nó đi tìm khi thứ đó có thật.
    assert 'data-lan="vi"' in _bo_chu_thich_jinja(
        '<b data-lan="vi">'), "phep quet khong bat duoc ca no phai bat"

    for xau in ('data-lan="vi"', "data-lan='vi'",
                'data-lan="en"', "data-lan='en'"):
        assert xau not in html, (
            f"{xau} go tay trong khuon mau — phai doc `g.ngon_ngu`")
    assert html.count('data-lan="{{ g.ngon_ngu') >= 2, (
        "ca hai nhanh (giong cua toi + giong mau) phai doc cung mot truong")


def test_danh_muc_cho_san_pham_khac_KHONG_danh_roi_lan():
    """Danh mục `tuy_chon_dong` là thứ ChatLTT/palette dựng ô chọn giọng từ đó.

    ⛔ Đánh rơi làn ở đây thì bên kia chỉ còn hai đường, và cả hai đều tệ: mời
       khách chọn một giọng mà cửa nộp sẽ từ chối, hoặc **chép tay** một danh
       sách VI/EN của riêng nó.
    """
    from apps.ltt_voice import tham_chieu

    muc = tham_chieu.tuy_chon_preset(None, "")
    assert muc, "danh muc preset rong"
    assert len(muc) == len(gm.DANH_SACH)
    for m in muc:
        assert m.get("ngon_ngu") in L.LAN_HOP_LE, m
    # Danh mục và bảng nguồn phải nói CÙNG một điều về từng giọng.
    theo_ma = {m["value"]: m["ngon_ngu"] for m in muc}
    for g in gm.DANH_SACH:
        assert theo_ma[g.public_id] == g.ngon_ngu, g.ma


# ── 2. Bốn luật tương thích ────────────────────────────────────────────────

@pytest.mark.parametrize("lan_giong,text", [
    (L.LAN_VI, VI_RO),
    (L.LAN_EN, EN_RO),
])
def test_cung_lan_thi_CHO_PHEP(lan_giong, text):
    pq = L.quyet_dinh(lan_giong, text)
    assert pq.cho_phep, pq
    assert pq.ma_loi == ""


@pytest.mark.parametrize("lan_giong,text,lan_text", [
    (L.LAN_VI, EN_RO, L.LAN_EN),
    (L.LAN_EN, VI_RO, L.LAN_VI),
])
def test_lech_lan_thi_CHAN(lan_giong, text, lan_text):
    pq = L.quyet_dinh(lan_giong, text)
    assert not pq.cho_phep, pq
    assert pq.ma_loi == L.MA_LOI_LECH_LAN
    assert pq.lan_giong == lan_giong and pq.lan_text == lan_text


def test_hoa_thuong_va_khoang_trang_KHONG_lam_mot_lan_thanh_khong_ro():
    """`"VI "` / `"EN"` là làn **hợp lệ**, không phải làn lạ.

    ⭐ Tách khỏi phép kiểm dưới có chủ ý: một khách tích hợp gửi `"EN"` hoa, và
       một cột CSDL cũ mang `"vi "` thừa khoảng trắng, đều là dữ liệu ĐÚNG viết
       khác kiểu. Chặn chúng là chặn công việc hợp lệ — đúng hướng sai mà cả
       hợp đồng này phải tránh. `chuan_lan` là chỗ duy nhất chuẩn hoá, và đây
       là phép kiểm giữ nó ở đó.
    """
    for x in ("VI ", " vi", "EN", "En ", "vi"):
        assert L.chuan_lan(x) in L.LAN_HOP_LE, x
    assert L.quyet_dinh("VI ", VI_RO).cho_phep
    assert not L.quyet_dinh("VI ", EN_RO).cho_phep


@pytest.mark.parametrize("lan_la", ["", "xx", None, "bilingual", "auto", "fr"])
def test_giong_CHUA_RO_LAN_thi_chan_du_van_ban_la_gi(lan_la):
    """⛔ Chiều sai ngược với văn bản: giọng mập mờ thì **không cho đọc**.

    `voice_profile.ngon_ngu` là `String(16)` tự do, nên `""` và `"xx"` là chuyện
    có thật ở dữ liệu nhập từ kho cũ. Trước Q121 chúng rơi vào nhánh "chưa có
    làn ⇒ im lặng" và đi thẳng tới GPU.

    ⚠️ `"auto"` nằm trong danh sách này có chủ ý: nó hợp lệ cho **văn bản**,
       không hợp lệ cho **giọng**. Một giọng không có "tự động".
    """
    for text in (VI_RO, EN_RO, "", "Ban co the mua ve o day."):
        pq = L.quyet_dinh(lan_la, text)
        assert not pq.cho_phep, (lan_la, text)
        assert pq.ma_loi == L.MA_LOI_LAN_KHONG_RO


# ── 3. `auto` được GIẢI, và giải xong không bao giờ là "không biết" ────────

def test_auto_giai_ve_mot_lan_CU_THE():
    """Không có đường nào để một phán quyết mang làn văn bản rỗng.

    ⭐ Đó là điều kiện để bảng bốn luật ở trên **đủ**: nếu `auto` giải ra
       "không biết" thì có một ô thứ năm không ai định nghĩa, và ô không định
       nghĩa là ô sẽ được ai đó điền bằng "cho qua".
    """
    for lan_giong in L.LAN_HOP_LE:
        for text in (VI_RO, EN_RO, "Ban co the mua ve o day.", "", "OK", "123"):
            for khai in ("auto", "", None, "xx"):
                pq = L.quyet_dinh(lan_giong, text, khai)
                assert pq.lan_text in L.LAN_HOP_LE, (lan_giong, text, khai)
                assert pq.nguon in (L.NGUON_DOAN, L.NGUON_THEO_GIONG)


def test_khai_bao_chi_THAT_khong_NOI():
    """D002 (2026-09-11): lời khai chỉ THÊM ràng buộc, không bao giờ miễn trừ.

    ⭐ Trước D002 test này tên là `test_khai_bao_THANG_phep_doan` và nó GHIM một
       đường vòng: khai `vi` rồi dán văn bản tiếng Anh ⇒ giọng Việt đọc tiếng Anh,
       khách trả tiền cho đúng lỗi chất lượng Q121 dựng ra để chặn.
    """
    # Khai lệch giọng ⇒ chặn, nguồn là lời khai (như cũ).
    pq = L.quyet_dinh(L.LAN_VI, VI_RO, "en")
    assert not pq.cho_phep and pq.nguon == L.NGUON_KHAI_BAO

    # 🔴 Ô MỚI: khai ĐÚNG làn giọng nhưng văn bản CHẮC là làn kia ⇒ chặn.
    pq = L.quyet_dinh(L.LAN_VI, EN_RO, "vi")
    assert not pq.cho_phep
    assert pq.nguon == L.NGUON_DOAN and pq.ma_loi == L.MA_LOI_LECH_LAN
    assert pq.lan_text == L.LAN_EN

    # Văn bản không dấu, chỉ MỘT từ chức năng tiếng Anh ("the") ⇒ đoán không
    # chắc ⇒ lời khai đứng ⇒ cho. Đây là ca khách gõ không dấu phải KHÔNG bị hại.
    pq = L.quyet_dinh(L.LAN_VI, "Ban co the mua ve o day", "vi")
    assert pq.cho_phep and pq.nguon == L.NGUON_KHAI_BAO

    # Khai + đoán + giọng cùng một làn ⇒ cho.
    assert L.quyet_dinh(L.LAN_EN, EN_RO, "en").cho_phep


def test_van_ban_map_mo_KHONG_BAO_GIO_bi_chan():
    """🔴 PHÉP KIỂM QUAN TRỌNG NHẤT CỦA TỆP NÀY, và nó chốt chiều KHÔNG chặn.

    Tiếng Việt viết không dấu chỉ gồm chữ ASCII — không phân biệt được với tiếng
    Anh bằng bảng mã. Một cửa chặn theo phán đoán **thô** sẽ từ chối công việc
    hợp lệ của khách đang gõ không dấu, với một lý do họ không sửa được vì họ
    đang gõ đúng thứ họ định gõ.

    ⇒ Mập mờ ⇒ nhận làn của chính giọng ⇒ **không bao giờ là thứ chặn**.
    """
    map_mo = ["Ban co the mua ve o day.", "Xin chao moi nguoi.",
              "Hom nay troi dep.", "OK", "", "123", "!!!",
              "Ban mo file trong that muc nay"]
    for text in map_mo:
        assert L.doan_ngon_ngu(text) is None, (
            f"{text!r} khong con map mo — ca thu nay het chung minh duoc gi")
        for lan_giong in L.LAN_HOP_LE:
            pq = L.quyet_dinh(lan_giong, text)
            assert pq.cho_phep, (lan_giong, text)
            assert pq.nguon == L.NGUON_THEO_GIONG
            assert pq.lan_text == lan_giong


def test_tron_ngon_ngu_co_luat_RO_RANG_va_TAT_DINH():
    """Trộn làn: **bằng chứng dương thắng**, và tiếng Việt là bằng chứng chắc.

    ⭐ Không đối xứng, và cố ý: dấu tiếng Việt không thể nhầm với gì khác, còn
       từ chức năng tiếng Anh thì có thể trùng âm tiết Việt viết không dấu. Nên
       một câu trộn có dấu tiếng Việt là `vi` — kể cả khi phần lớn từ là tiếng
       Anh.

    ⛔ Và nó phải TẤT ĐỊNH: cùng một chuỗi cho cùng một phán quyết ở mọi lượt.
    """
    tron = "Xin chào, đây là bản demo của the new API that we built."
    assert L.doan_ngon_ngu(tron) == L.LAN_VI
    assert L.quyet_dinh(L.LAN_VI, tron).cho_phep
    assert not L.quyet_dinh(L.LAN_EN, tron).cho_phep

    truoc = L.quyet_dinh(L.LAN_EN, tron)
    for _ in range(5):
        lai = L.quyet_dinh(L.LAN_EN, tron)
        assert (lai.cho_phep, lai.ma_loi, lai.lan_text) == (
            truoc.cho_phep, truoc.ma_loi, truoc.lan_text)


# ── 4. Lỗi phải DÙNG ĐƯỢC ở GUI và API ─────────────────────────────────────

def test_ma_loi_la_chuoi_ON_DINH_khong_dau():
    """Mã lỗi đi vào JSON, log và mã của khách tích hợp.

    ⛔ Một câu tiếng Việt có dấu ở vị trí đó là một gánh nặng chứ không phải một
       thông tin — và nó còn đổi theo ngôn ngữ giao diện, tức không bắt được.
    """
    for ma in (L.MA_LOI_LECH_LAN, L.MA_LOI_LAN_KHONG_RO):
        assert ma and ma.isascii() and ma == ma.lower()
        assert " " not in ma
    assert L.MA_LOI_LECH_LAN != L.MA_LOI_LAN_KHONG_RO


def test_cau_cho_khach_DIEN_HET_cho_trong():
    """⛔ Câu tới tay khách không được còn `{lan_giong}` hay `{lan_text}`.

    🔴 Đây là lỗi đã có thật và đã im lặng suốt: `doi_chieu` trả khuôn còn
       nguyên chỗ trống, và `dien_canh_bao` — hàm điền chỗ trống ấy — **chưa
       từng được gọi ở đâu**. Một chỗ trống có sẵn mà không ai điền trông giống
       hệt một chỗ đã điền đúng.
    """
    pq = L.quyet_dinh(L.LAN_VI, EN_RO)
    cau = L.cau_cho_khach(pq)
    assert cau and "{" not in cau and "}" not in cau, cau

    pq2 = L.quyet_dinh("", VI_RO)
    cau2 = L.cau_cho_khach(pq2)
    assert cau2 and "{" not in cau2, cau2
    assert cau != cau2, "hai hang loi phai noi hai cau khac nhau"


def test_route_tra_ma_loi_ra_JSON():
    """GUI phải bắt được lỗi theo mã, không theo chuỗi tiếng Việt."""
    src = (GOC / "apps" / "ltt_voice" / "routes"
           / "_p_tao.py").read_text(encoding="utf-8")
    assert '"ma_loi"' in src, "cua /tao khong tra ma loi"
    # Và cả hai nhánh từ chối phải đi qua cùng một chỗ dựng phản hồi.
    assert src.count("_loi_400(e)") >= 2, (
        "mot nhanh tu choi con tu dung phan hoi rieng — hai ban chep se lech")


# ── 5. Nối vào ứng dụng: mismatch KHÔNG tạo được đường sinh tiếng ──────────

def _yc(text: str, *, preset: str = "", ngon_ngu: str = "auto"):
    return features.chuan_hoa({"text": text, "preset": preset,
                               "ngon_ngu": ngon_ngu})


def test_giai_giong_NEM_khi_lech_lan_va_mang_ma_loi():
    """🔴 Mệnh đề trung tâm: không có đường nào từ một yêu cầu lệch làn tới một
    lượt gọi cổng.

    ⭐ Đo ở `giai_giong` chứ không ở route, vì `giai_giong` là chỗ **cả ba cửa**
       đi qua (web, worker, Public API). Chốt ở route thì Public API — cửa đi
       thẳng xuống job — không có phép chặn nào.
    """
    assert gm.lan_cua("Adam") == L.LAN_VI, "ca thu doi Adam la giong lan vi"

    with pytest.raises(features.LoiGiongNoi) as e:
        features.giai_giong(None, _yc(EN_RO, preset="Adam"))
    assert getattr(e.value, "ma", "") == L.MA_LOI_LECH_LAN
    assert "{" not in str(e.value), "cau loi con cho trong chua dien"

    # Và cùng giọng đó với văn bản cùng làn thì đi qua bình thường.
    ref, preset, canh_bao = features.giai_giong(None, _yc(VI_RO, preset="Adam"))
    assert ref is None and preset == "Adam"
    assert canh_bao == ()


def test_giai_giong_chan_TRUOC_khi_cham_CSDL_hay_KHO():
    """Nhánh preset không được chạm `db` — đối chứng là truyền `None` vào.

    ⭐ Phép kiểm trên đã truyền `db=None` và không nổ, nên mệnh đề "chặn sớm" là
       thứ đo được chứ không phải một lời hứa trong chú thích. Ở đây chốt thêm
       **thứ tự** trong nhánh giọng nhân bản: chốt làn phải đứng TRƯỚC
       `tim_repr_active`/`nap_ref_b64`, vốn là một lượt đọc kho (mạng, với R2).
    """
    ham = next(n for n in ast.walk(ast.parse(inspect.getsource(features)))
               if isinstance(n, ast.FunctionDef) and n.name == "giai_giong")
    thu_tu = [n.func.attr if isinstance(n.func, ast.Attribute) else
              getattr(n.func, "id", "")
              for n in ast.walk(ham) if isinstance(n, ast.Call)]
    thu_tu = [t for t in thu_tu if t in ("_chot_lan", "nap_ref_b64",
                                         "tim_repr_active")]
    assert "_chot_lan" in thu_tu, "giai_giong khong con chot lan"
    assert thu_tu.index("_chot_lan") < thu_tu.index("nap_ref_b64"), (
        f"chot lan phai dung TRUOC luot doc kho: {thu_tu}")


def test_ca_HAI_nhanh_cua_giai_giong_deu_chot_lan():
    """⛔ Preset và giọng nhân bản là hai nhánh; một nhánh quên là một lỗ.

    Cùng khuôn phép kiểm mà `test_384` dùng cho `doi_chieu`, giữ nguyên vì lý do
    của nó không đổi — chỉ đổi hàm được chốt.
    """
    ham = next(n for n in ast.walk(ast.parse(inspect.getsource(features)))
               if isinstance(n, ast.FunctionDef) and n.name == "giai_giong")
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_chot_lan"]
    assert len(goi) >= 2, "phai chot lan o CA HAI nhanh (preset + nhan ban)"


def test_khong_con_hang_so_lan_go_tay_trong_features():
    """⛔ `"vi"` gõ tay ở `giai_giong` là bản chép đã gây ra cả chuyện này."""
    ham = next(n for n in ast.walk(ast.parse(inspect.getsource(features)))
               if isinstance(n, ast.FunctionDef) and n.name == "giai_giong")
    hang = [n.value for n in ast.walk(ham)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    xau = [h for h in hang if h.strip().lower() in ("vi", "en")]
    assert not xau, f"lan go tay trong giai_giong: {xau}"


def _khoa_params_cua_loi_nop(ten_ham: str) -> set:
    """Tập khoá của `params` mà một cửa NỘP xuống job — dù nó viết kiểu nào.

    🔴 VIẾT LẠI 2026-09-11, và lý do là chính lỗi tôi vừa sửa cho `test_509`.

       Bản đầu đọc thẳng `params={...}` **nội tuyến** trong lời gọi
       `submit_with_credit`. Ngày 11/09 trunk tách nó ra một biến để thêm
       `dedupe_key_for(..., params)` — và hai phép kiểm của tôi ĐỎ, dù mệnh đề
       chúng chốt (*"`ngon_ngu` xuống tới worker"*) vẫn đúng nguyên.

    ⛔ Tức tôi chốt **hình dạng lời gọi**, không chốt **điều phải đúng** — đúng
       cái bẫy tôi vừa gỡ ở `test_509` và ghi vào nhật ký, rồi mắc lại ở tệp
       bên cạnh trong cùng một ngày. Ranh giới cơ học thắng giao ước, kể cả
       giao ước với chính mình.

    ⇒ Bản này **giải biến**: nếu `params=` là một tên, đi tìm phép gán gần nhất
      của tên ấy trong cùng hàm. Bất biến với việc dict nằm nội tuyến hay tách
      ra — và vẫn đỏ nếu một khoá thật sự biến mất.
    """
    src = (GOC / "apps" / "ltt_voice" / "routes"
           / "_p_tao.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == ten_ham)
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call)
           and getattr(n.func, "id", "") == "submit_with_credit"]
    assert len(goi) == 1, f"khong tim thay dung mot loi nop job o `{ten_ham}`"
    nut = next(k.value for k in goi[0].keywords if k.arg == "params")

    if isinstance(nut, ast.Name):          # `params=params` -> giai bien
        ten = nut.id
        gan = [n for n in ast.walk(ham)
               if isinstance(n, ast.Assign)
               and any(getattr(t, "id", "") == ten for t in n.targets)]
        assert gan, f"`params={ten}` nhung khong thay phep gan nao cho `{ten}`"
        nut = gan[-1].value
    assert isinstance(nut, ast.Dict), (
        f"`params` khong giai ra mot dict doc duoc: {type(nut).__name__}")
    return {k.value for k in nut.keys if isinstance(k, ast.Constant)}


def test_ngon_ngu_KHACH_KHAI_di_toi_duoc_worker():
    """🔴 Lỗi ③: route nhận `ngon_ngu` rồi bỏ nó ra khỏi `params` lúc nộp job.

    ⛔ Đo bằng CÂY CÚ PHÁP của chính dict `params`, không bằng `"ngon_ngu" in
       src` — chuỗi ấy có mặt trong tệp ở nhiều chỗ khác (tham số form, chú
       thích, lời gọi `chuan_hoa`), nên một phép so chuỗi sẽ **xanh cả trước
       khi sửa**. Đúng hạng lỗi "phép kiểm rộng hơn thứ nó đo".
    """
    khoa = _khoa_params_cua_loi_nop("tao")
    assert "ngon_ngu" in khoa, (
        f"`params` nop job danh roi `ngon_ngu` — worker se luon thay 'auto'. "
        f"Co: {sorted(khoa)}")


def test_ca_ba_khoa_quyet_dinh_LAN_deu_co_trong_params():
    """Giọng, văn bản, ngôn ngữ khai — thiếu một thì worker phán quyết khác cửa.

    ⭐ Và hai cửa phán quyết khác nhau về cùng một yêu cầu là lỗi tệ hơn hẳn cả
       hai cùng sai: khách được nhận job rồi mới bị từ chối, sau khi đã giữ tiền.
    """
    khoa = _khoa_params_cua_loi_nop("tao")
    assert {"text", "voice_id", "preset", "ngon_ngu"} <= khoa, sorted(khoa)


# ── 6. Nghe thử đi theo DANH MỤC, không theo ngôn ngữ giao diện ────────────

def test_nghe_thu_chon_cau_theo_LAN_khong_theo_locale():
    """🔴 Lỗi ⑤ audit tìm thêm: `dung()` đọc câu **đã dịch sang ngôn ngữ của
    tiến trình**, trong khi khoá kho không mang ngôn ngữ.

    Hệ quả: tệp dựng đầu tiên thắng, nên một giọng làn `vi` có thể vĩnh viễn
    nghe thử bằng một câu tiếng Anh chỉ vì lượt bảo trì đầu tiên tình cờ chạy
    dưới ngữ cảnh tiếng Anh — và không ai phát hiện, vì cả hai đều là tiếng nói
    bình thường.
    """
    from apps.ltt_voice import nghe_thu

    assert nghe_thu.cau_cho_lan("vi") != nghe_thu.cau_cho_lan("en")
    # Làn lạ lui về tiếng Việt, KHÔNG ném: nghe thử không được làm hỏng gì.
    for la in ("", "xx", None):
        assert nghe_thu.cau_cho_lan(la) == nghe_thu.cau_cho_lan("vi")

    ham = next(n for n in ast.walk(ast.parse(inspect.getsource(nghe_thu)))
               if isinstance(n, ast.FunctionDef) and n.name == "dung")
    dich = [n for n in ast.walk(ham)
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_t"]
    assert not dich, (
        "`dung()` van dich cau nghe thu theo ngon ngu giao dien — cau doc phai "
        "theo LAN cua giong")
    assert "ngon_ngu" in inspect.signature(nghe_thu.dung).parameters


def test_bao_tri_truyen_lan_cua_tung_giong():
    """Vòng bảo trì phải chuyển làn xuống, không để `dung()` tự đoán."""
    from apps.ltt_voice import nghe_thu

    ham = next(n for n in ast.walk(ast.parse(inspect.getsource(nghe_thu)))
               if isinstance(n, ast.FunctionDef) and n.name == "bao_tri")
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "dung"]
    assert goi, "bao_tri khong con dung tep nghe thu"
    assert any(k.arg == "ngon_ngu" for n in goi for k in n.keywords), (
        "bao_tri khong truyen lan xuong `dung()`")
# ── 7. HOÀ TRUNK 2026-09-10: đường lùi giọng KHÔNG được vượt làn ───────────

def test_duong_lui_giong_khong_the_vuot_lan():
    """🔴 BẤT BIẾN SINH RA TỪ VIỆC HAI NHÁNH GẶP NHAU — không nhánh nào tự có.

    Trunk (07/09) thêm `lui_giong`: khi biểu diễn của một giọng nhân bản không
    còn (ca nâng engine), `giai_giong` **thay bằng một giọng khác** thay vì từ
    chối. Q121 (10/09) thêm cửa chặn làn, và nó chốt làn của giọng khách CHỌN.

    ⛔ Ghép hai thứ đó lại thì có một câu hỏi mà **cả hai bên đều không hỏi**:
       giọng THAY THẾ có cùng làn không? Nếu `lui_giong` chỉ *ưu tiên* cùng làn
       thay vì *bắt buộc*, thì một bài tiếng Việt có thể lặng lẽ được đọc bằng
       một giọng làn `en` — tức Q121 bị vòng qua bởi một đường mà Q121 không
       biết là có.

    ⭐ Đo cho thấy trunk đã làm đúng: `_hop` khớp CỨNG `u.ngon_ngu == ngon_ngu`,
       và `chon` trả `None` ngay khi làn không thuộc `{vi, en}`. Phép kiểm này
       **khoá** hành vi ấy lại, vì nó là thứ duy nhất giữ cho đường lùi không
       thành một lỗ trong hợp đồng — và nó nằm ở một tệp (`lui_giong.py`) mà
       người sửa Q121 không có lý do gì để mở ra.
    """
    from apps.ltt_voice import lui_giong

    def _uv(ma, gioi, lan):
        return lui_giong.UngVien(ma=ma, gioi=gioi, ngon_ngu=lan,
                                 vung="", phong_cach="")

    kho = [_uv("EN_A", "nam", "en"), _uv("VI_A", "nam", "vi"),
           _uv("EN_B", "nu", "en")]

    # Cùng làn thì chọn được…
    assert lui_giong.chon(gioi="nam", ngon_ngu="vi", cac=kho).ma == "VI_A"
    assert lui_giong.chon(gioi="nu", ngon_ngu="en", cac=kho).ma == "EN_B"

    # …và KHÔNG có ứng viên cùng làn thì trả None, KHÔNG hạ tiêu chuẩn.
    assert lui_giong.chon(gioi="nu", ngon_ngu="vi", cac=kho) is None

    # Giọng chưa rõ làn: không lùi được — cùng chiều fail-safe với `quyet_dinh`.
    for la in ("", "xx", None, "auto"):
        assert lui_giong.chon(gioi="nam", ngon_ngu=la, cac=kho) is None, la


def test_cau_nghe_thu_cua_MOI_lan_deu_vao_van_tay_phien_ban():
    """⛔ Sửa câu tiếng Anh mà khoá không đổi ⇒ khách nghe câu EN cũ mãi mãi.

    🔴 Đây cũng là một lỗ do hoà nhánh: trunk dựng `PHIEN_BAN` bằng cách BĂM câu
       nghe thử (để "đổi câu ⇒ đổi khoá" không phải nhớ bằng tay), nhưng lúc ấy
       chỉ có **một** câu. Q121 thêm câu thứ hai theo làn — và hàm băm không tự
       nhìn thấy nó.

    ⭐ Đo bằng HÀNH VI: đổi thật một câu trong `CAU_THEO_LAN` rồi dựng lại vân
       tay, và đòi nó khác. Một phép kiểm đọc chuỗi mã nguồn sẽ xanh cả với bản
       cũ.
    """
    import hashlib

    from apps.ltt_voice import nghe_thu as N

    def _van_tay(bang: dict) -> str:
        return hashlib.sha256(
            ("|".join([f"{k}={v}" for k, v in sorted(bang.items())]
                      + [N._phien_ban_tham_so()])).encode("utf-8")
        ).hexdigest()[:12]

    goc = dict(N.CAU_THEO_LAN)
    assert N.PHIEN_BAN.endswith(_van_tay(goc)), (
        "PHIEN_BAN khong con dung tu CAU_THEO_LAN — cap nhat ca hai cho")

    for lan in goc:
        doi = dict(goc, **{lan: goc[lan] + " mot chu them vao"})
        assert _van_tay(doi) != _van_tay(goc), (
            f"doi cau lan {lan!r} KHONG lam doi van tay — tep nghe thu cu se "
            f"duoc phuc vu mai mai, va khong ai phat hien vi ca hai deu la "
            f"tieng noi binh thuong")
