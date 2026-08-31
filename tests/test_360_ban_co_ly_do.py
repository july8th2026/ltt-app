"""test_360 — "bận" phải nói được VÌ SAO, và phải đếm vào đúng bộ đếm.

Sự cố 31/08 là lý do tệp này tồn tại: một khách gọi 117 lượt, **89 lượt hỏng**,
kéo hơn năm giờ — và nền tảng không để lại **một dòng nào** nói vì sao. Hai chỗ
hổng độc lập cùng gây ra chuyện đó, nên có hai nhóm phép kiểm:

  1. **Lý do của máy B bị vứt.** Máy B phân biệt ba kiểu bận, mỗi kiểu sửa một
     cách khác hẳn; máy A đọc thân lỗi ra một biến rồi thay bằng chuỗi cứng.
  2. **Đếm nhầm ô.** `CAPACITY_REFUSED` sinh ra đúng cho tình huống này nhưng
     chỉ được nuôi ở cửa job, nên suốt sự cố nó đứng ở 0 còn thư gửi người trực
     nói `responses_5xx` — tức "nền tảng hỏng", chẩn đoán sai ngay ở tiêu đề.

⛔ Đây **không** phải phép kiểm cho việc máy B có bận hay không. Máy B bận là
   chuyện bình thường và đúng chức năng (D-005). Thứ được chốt ở đây là: khi nó
   bận, ta **biết được vì sao** và **đếm đúng ô**.
"""
from __future__ import annotations

import inspect
import json

from platform_core.llm.luong_vlm import _ly_do_ban


# ── 1. Lý do của máy B phải sống sót chuyến đi ──────────────────────────────

def _than(chi_tiet: dict) -> str:
    """Đúng hình dạng FastAPI sinh ra từ `HTTPException(detail={...})`."""
    return json.dumps({"detail": chi_tiet}, ensure_ascii=False)


def test_ba_kieu_ban_ra_ba_cau_KHAC_NHAU():
    """Cả mục đích của bản vá nằm ở đây.

    Ba kiểu bận dẫn tới ba hành động sửa khác hẳn nhau — suất bị rò thì khởi
    động lại cổng, việc khác giữ card thì đợi hoặc dừng việc kia, ComfyUI không
    nhả VRAM thì gọi `/free`. Gộp cả ba vào một câu là lấy mất khả năng chọn.
    """
    ba = [_ly_do_ban(_than(t)) for t in (
        {"ly_do": "cong dang day", "chi_tiet": "3/3 suat dang dung"},
        {"ly_do": "may B dang ban", "chi_tiet": "2 tien trinh python tren card"},
        {"ly_do": "card chua san sang de nap model",
         "chi_tiet": "ComfyUI khong nha", "vram_dung_mb": 19837},
    )]
    assert len(set(ba)) == 3, f"ba kieu ban phai ra ba cau khac nhau: {ba}"
    assert "cong dang day" in ba[0] and "3/3" in ba[0]
    assert "2 tien trinh" in ba[1]
    assert "19837" in ba[2], "so VRAM la con so DUY NHAT noi card dang bi ai giu"


def test_khong_doc_duoc_JSON_thi_tra_VAN_BAN_THO_chu_khong_rong():
    """Đúng lúc hình dạng lạ là lúc cần thông tin nhất.

    Một trang lỗi HTML của Cloudflare, một proxy chen giữa, một bản cổng cũ —
    cả ba đều trả thứ không phải JSON. Trả rỗng ở đây là tái lập đúng sự cố mà
    tệp này sinh ra để chặn.
    """
    assert "1010" in _ly_do_ban("<html>error code: 1010</html>")
    assert _ly_do_ban("").strip(), "rong thi phai noi ro la thuong nguon im lang"


def test_khong_bao_gio_nem_ra_ngoai():
    """Nó chạy trên đường xử lý lỗi. Ném ở đây là biến 503 thành 500."""
    for xau in ("", "null", "[]", "{}", '{"detail": null}', '{"detail": "chuoi"}',
                '"chi la mot chuoi"', "{khong phai json"):
        assert isinstance(_ly_do_ban(xau), str)


def test_ly_do_di_VAO_ngoai_le_chu_khong_dung_lai_o_bien():
    """Bản trước gán `than_loi` rồi không dùng — biến sống, thông tin chết."""
    from platform_core.llm import luong_vlm

    ma = inspect.getsource(luong_vlm.mo)
    khuc = ma.split("status_code == 429")[1].split("if r.status_code >= 400")[0]
    assert "_ly_do_ban(than_loi)" in khuc, (
        "nhanh 429 doc than loi ra roi phai DUNG no; thay bang chuoi cung la "
        "quay lai dung cai bug ngay 31/08")


# ── 2. Bận phải đếm vào ô "hết năng lực", không rơi câm vào 5xx ─────────────

def test_MOI_nhanh_ban_deu_nuoi_CAPACITY_REFUSED():
    """Bánh cóc: thêm một cửa mới mà quên đếm là hỏng lặng lẽ.

    ⛔ Đây là kiểu hỏng không ai thấy — không lỗi, không stack trace, chỉ là một
       con số đứng im và một người trực đọc sai nguyên nhân.

    Cách đo: mỗi chỗ dựng câu trả lời "bận" phải có `CAPACITY_REFUSED` đứng
    **trước** nó trong cùng một quãng mã ngắn. Cửa sổ 700 ký tự đủ rộng cho
    hoàn tiền + commit + nhả vé, và đủ hẹp để không vô tình mượn của nhánh khác.
    """
    from server.api import chat, streaming

    MOC = "The model is busy right now"
    thieu = []
    for mod in (chat, streaming):
        ma = inspect.getsource(mod)
        i = ma.find(MOC)
        while i != -1:
            if "CAPACITY_REFUSED" not in ma[max(0, i - 700):i]:
                thieu.append(f"{mod.__name__} @~{ma[:i].count(chr(10)) + 1}")
            i = ma.find(MOC, i + 1)
    assert not thieu, (
        f"nhanh ban KHONG dem vao CAPACITY_REFUSED o: {thieu} — su co se lai "
        f"bao 'nen tang hong' trong khi that ra la het nang luc")


def test_ba_nhanh_ban_deu_GHI_LOG():
    """Một sự cố năm giờ không để lại dòng nào là chuyện đã xảy ra thật."""
    from server.api import chat, streaming

    for mod, so_toi_thieu in ((chat, 1), (streaming, 2)):
        ma = inspect.getsource(mod)
        assert ma.count('log.warning("BAN') >= so_toi_thieu, (
            f"{mod.__name__}: nhanh ban phai ghi log — im lang la thu da lam "
            f"su co 31/08 mat nhieu gio moi lan ra")
