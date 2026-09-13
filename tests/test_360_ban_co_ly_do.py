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

import ast
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
    # ⛔ ĐỌC AST, KHÔNG QUÉT VĂN BẢN THÔ — sửa 07/09/2026.
    #
    #    Bản cũ `ma.find(MOC)` trên toàn bộ mã nguồn. Nó khớp cả **chú thích**:
    #    ngay khi tôi viết `# GIU NGUYEN tien to "The model is busy right now"`
    #    vào `streaming.py` để cảnh báo người sau, phép kiểm đếm dòng chú thích
    #    ấy như một nhánh bận, không thấy `CAPACITY_REFUSED` ở trước, và ĐỎ.
    #
    # 🔴 Một bộ dò quét văn bản **trừng phạt việc giải thích**: viết chú thích
    #    càng rõ càng dễ làm nó đỏ. Đã dính ở kho này rồi, và lần này nó tự
    #    dính vào chính đoạn nói về nó.
    #
    # ⭐ Đọc AST hỏi đúng thứ cần hỏi: một **lời gọi thật** tới hàm dựng 503 mà
    #    đối số đầu là chuỗi mở đầu bằng `MOC`. Chú thích và docstring không
    #    phải lời gọi, nên chúng biến mất khỏi phép đo mà không cần loại trừ.
    #
    # ⛔ Và phạm vi là **khối `except` chứa nó**, không phải "700 ký tự trước".
    #    Cửa sổ đo bằng ký tự đếm cả chú thích: khi tôi viết thêm mươi dòng
    #    giải thích vào `chat.py`, `metrics.increment(CAPACITY_REFUSED)` bị đẩy
    #    ra ngoài cửa sổ và phép kiểm ĐỎ — dù mã không đổi một chút nào.
    #
    # 🔴 Đó là **lần thứ hai trong cùng một bản vá** một bộ dò văn bản trừng
    #    phạt việc giải thích. Khối `except` là ranh giới THẬT của quan hệ
    #    "đếm rồi mới trả lời"; nó bất biến với việc viết chú thích dài hay
    #    ngắn, và đó chính là lý do phải hỏi quan hệ chứ đừng đo khoảng cách.
    def _chuoi_dau(n):
        a = n.args[0]
        if isinstance(a, ast.Constant):
            return a.value
        if isinstance(a, ast.JoinedStr) and a.values \
                and isinstance(a.values[0], ast.Constant):
            return a.values[0].value
        return ""

    # ⭐ MỘT chỗ đếm ở nơi khác, và đó là thật chứ không phải miễn trừ suông.
    #
    #    Nhánh bắt `DangBan` của cửa STREAM nhận ngoại lệ đã đi qua facade
    #    `runtime_noi_bo/luong.py`, và **facade** mới là chỗ hoàn tiền + đếm
    #    (H43 Phase 02). Nên trong khối `except` ấy không có `CAPACITY_REFUSED`
    #    — đúng thiết kế.
    #
    # 🔴 Bản cũ của phép kiểm này XANH ở chỗ đó vì cửa sổ 700 ký tự khớp phải
    #    chữ `CAPACITY_REFUSED` **trong một dòng chú thích**, không phải một
    #    bộ đếm. Tức bảo đảm ở site ấy là **ảo** suốt thời gian qua, và không
    #    ai biết vì phép kiểm vẫn PASS. Đây đúng là thứ Bẫy 31 nói tới, chỉ
    #    khác chiều: không phải xanh vì rỗng, mà xanh vì **khớp nhầm**.
    #
    # ⇒ Miễn trừ phải KÈM CHỨNG MINH: dưới đây chốt luôn rằng facade thật sự
    #   đếm. Ngày nào facade thôi đếm, phép kiểm này đỏ — chứ không im lặng
    #   tha cho cả hai chỗ.
    from platform_core.runtime_noi_bo import luong as _facade

    facade_dem = any(
        isinstance(m, ast.Attribute) and m.attr == "CAPACITY_REFUSED"
        for kh in ast.walk(ast.parse(inspect.getsource(_facade)))
        if isinstance(kh, ast.ExceptHandler) for m in ast.walk(kh))
    assert facade_dem, (
        "facade `runtime_noi_bo/luong.py` KHONG con dem CAPACITY_REFUSED trong "
        "nhanh ban — nhanh DangBan cua streaming dang duoc mien tru dua tren "
        "gia dinh nay, nen mien tru ay nay vo cang.")

    so_khop = 0
    for mod in (chat, streaming):
        for kh in ast.walk(ast.parse(inspect.getsource(mod))):
            if not isinstance(kh, ast.ExceptHandler):
                continue
            co_dem = any(isinstance(m, ast.Attribute)
                         and m.attr == "CAPACITY_REFUSED"
                         for m in ast.walk(kh))
            # Bắt `DangBan` nghĩa là ngoại lệ đã qua facade — facade đã đếm.
            bat_dangban = any(
                (t.attr if isinstance(t, ast.Attribute) else getattr(t, "id", ""))
                == "DangBan"
                for t in ((kh.type.elts if isinstance(kh.type, ast.Tuple)
                           else [kh.type]) if kh.type else []))
            for n in ast.walk(kh):
                if not (isinstance(n, ast.Call)
                        and getattr(n.func, "id", "") == "service_unavailable"
                        and n.args):
                    continue
                c = _chuoi_dau(n)
                if not (isinstance(c, str) and c.startswith(MOC)):
                    continue
                so_khop += 1
                if not (co_dem or bat_dangban):
                    thieu.append(f"{mod.__name__} @{n.lineno}")

    # ⛔ ĐỐI CHỨNG — thêm 07/09/2026, và nó quan trọng hơn phép kiểm bên dưới.
    #
    #    Phép kiểm này lái bằng một HẰNG CHUỖI. Nếu ai đó sửa câu chữ sản phẩm
    #    (đúng việc tôi vừa làm khi gỡ `{e.ly_do}` khỏi thân trả về), `find`
    #    khớp **0 lần**, vòng `while` không vào, `thieu` rỗng, và
    #    `assert not thieu` **XANH** — trong khi nó không kiểm được gì cả.
    #
    # 🔴 Một bánh cóc tự tháo về phía XANH thì không ai thấy nó tháo: không lỗi,
    #    không stack trace, chỉ một dòng PASS như mọi khi. Xem **Bẫy 31**.
    #
    # ⭐ Nên "không tìm thấy chỗ nào" phải là ĐỎ, không phải xanh. Ba nhánh bận
    #    đã biết: `chat` 1 (đồng bộ), `streaming` 2 (`_mot_cuc` + facade).
    # 🔴 HA MOC 3 -> 2 NGAY 13/09/2026, VA DAY LA LY DO — doc truoc khi ha tiep.
    #
    #    `streaming.py` tung co HAI nhanh ban; mot trong hai thuoc "DUONG CU"
    #    (tool khong khai ngan sach KV). Do bang chinh ban khai 13/09:
    #        ltt-3.8 -> ltt_38_3090 3 suat, ltt-3.5 -> ltt_35_5060 3 suat
    #    ⇒ MOI model cua `text.chat` deu khai ⇒ duong cu **khong the voi toi
    #      duoc**. No la di tich thoi mot-card/mot-luot va da bi go (`test_1248`).
    #
    # ⛔ NHANH BAN AY KHONG "BIEN MAT" — no di theo canh cua da chet. Do phu
    #    THAT khong giam, no doi HINH DANG: cua song tra ban bang khoi loi SSE
    #    sau 200, chu khong bang `service_unavailable` truoc 200.
    #
    # ⇒ Nen ha mot moc dem, va **them mot ve moi** chot dung cho no chuyen toi.
    #   Ha moc ma khong them ve la lam yeu banh coc; day thi khong.
    assert so_khop >= 2, (
        f"chi thay {so_khop} nhanh ban mang chuoi {MOC!r} — mong doi >= 2. "
        f"Hoac cau chu san pham da doi (thi SUA MOC o day), hoac mot nhanh ban "
        f"da bien mat. Ca hai deu phai xem, va KHONG duoc de phep kiem nay "
        f"xanh rong: xem Bay 31.")

    # ⭐ VE MOI: cua SONG (phong cho) tra ban bang SSE sau 200. Do la noi luu
    #    luong that di qua, nen no quan trong hon ca hai nhanh dem o tren.
    from platform_core.runtime_noi_bo import luong as _cua_song

    van_song = inspect.getsource(_cua_song)
    so_sse = van_song.count(MOC)
    assert so_sse >= 2, (
        f"cua SONG (`luong_co_cho`) chi con {so_sse} cho mang chuoi {MOC!r} — "
        "mong doi >= 2 (het cho, va ban sau 200). Day la cua MOI luot that di "
        "qua: mat cau chu o day la khach nhan mot khoi loi khong noi len dieu gi.")

    assert not thieu, (
        f"nhanh ban KHONG dem vao CAPACITY_REFUSED o: {thieu} — su co se lai "
        f"bao 'nen tang hong' trong khi that ra la het nang luc")


def test_than_tra_ve_KHONG_mang_chu_thuong_nguon():
    """⛔ Câu chữ 4xx/5xx đưa cho khách không được mang văn bản của MÁY B.

    Đo 07/09/2026 — **ba** chỗ đang rò, trên **hai** cửa khác nhau:

        streaming.py  429  f"...: {e.ly_do}"   -> `_ly_do_ban`: toi 300 ky tu
                                                  than tho, VA `vram_dung_mb`
        streaming.py  413  f"[{e.ly_do}]"      -> `may B tra 413: {than[:200]}`
        chat.py       429  f"...: {e}"         -> BanError: `detail.chi_tiet`

    🔴 Chỗ nặng nhất là `vram_dung_mb`: một khách API bị 503 đọc được **công
       suất còn lại của máy B**. `_ly_do_ban` được viết để giúp NGƯỜI TRỰC
       chẩn đoán — docstring của nó nói đúng vậy — và không ai để ý rằng cùng
       chuỗi đó cũng đi thẳng ra ngoài.

    ⭐ Bỏ chúng đi không mất chẩn đoán: cả ba đều đã `log.warning(...)` **trước**
       khi `raise` (`luong.py:294`, `streaming.py:662`, `chat.py:252`). Câu phải
       hỏi ở mọi bản vá bịt rò là *"bịt rồi, người trực còn thấy gì?"* — một bản
       vá đổi một lỗ lộ tin lấy một ĐIỂM MÙ là tái lập đúng sự cố 31/08.

    ## Phép kiểm này hỏi QUAN HỆ, không hỏi NHÃN

    Không quét xem câu chữ "trông có nhạy cảm không" — đó là nhãn, và nó vừa
    bỏ lọt vừa báo nhầm. Nó hỏi: **có biểu thức nào của ngoại lệ thượng nguồn
    chảy vào đối số đầu của một hàm dựng lỗi HTTP không.**
    """


    from server.api import chat, streaming

    DUNG_LOI = {"service_unavailable", "payload_too_large", "invalid_request",
                "insufficient_credit", "_bao_400"}
    #: Tên biến ngoại lệ mang văn bản thượng nguồn. `str(e)` của `ThamSoSai` /
    #: `ThieuCredit` là chữ của CHÍNH TA nên không nằm ở đây — phép kiểm chỉ
    #: chặn `DangBan` / `KhongMoDuoc`, hai loại duy nhất bọc thân máy B.
    LOAI_RO = {"DangBan", "KhongMoDuoc", "BanError"}

    xau, so_ham_xet = [], 0
    for mod in (chat, streaming):
        cay = ast.parse(inspect.getsource(mod))
        for n in ast.walk(cay):
            if not isinstance(n, ast.ExceptHandler) or not n.name:
                continue
            ten_loai = {t.attr if isinstance(t, ast.Attribute) else
                        getattr(t, "id", "")
                        for t in (n.type.elts if isinstance(n.type, ast.Tuple)
                                  else [n.type])} if n.type else set()
            if not (ten_loai & LOAI_RO):
                continue
            so_ham_xet += 1
            for m in ast.walk(n):
                if not (isinstance(m, ast.Call)
                        and getattr(m.func, "id", "") in DUNG_LOI and m.args):
                    continue
                for k in ast.walk(m.args[0]):
                    if isinstance(k, ast.Name) and k.id == n.name:
                        xau.append(f"{mod.__name__}:{m.lineno} "
                                   f"{getattr(m.func, 'id', '?')}(...{n.name}...)")
                    elif isinstance(k, ast.Attribute) and k.attr == "ly_do":
                        xau.append(f"{mod.__name__}:{m.lineno} .ly_do")

    # ⛔ ĐỐI CHỨNG, cùng lý do với phép kiểm trên: nếu không tìm thấy khối
    #    `except` nào thuộc `LOAI_RO` thì phép kiểm này XANH RỖNG. Đo 07/09:
    #    `chat` 2 + `streaming` 3.
    # 🔴 HA MOC 4 -> 3 NGAY 13/09/2026, CUNG MOT LY DO voi phep kiem tren:
    #    `streaming.py` mat mot khoi `except cua_luong.DangBan/KhongMoDuoc` khi
    #    DUONG CU bi go (di tich mot-card/mot-luot, khong model nao voi toi duoc
    #    — xem `test_1248`). Do phu that khong giam: cua song bat cung hai loai
    #    ay o `runtime_noi_bo/luong.py` va tra bang khoi loi SSE.
    assert so_ham_xet >= 3, (
        f"chi thay {so_ham_xet} khoi except thuoc {sorted(LOAI_RO)} — mong doi "
        f">= 3. Ten loai ngoai le co the da doi; sua LOAI_RO, dung de xanh rong.")

    # ⭐ VE MOI di kem viec ha moc: cua SONG phai van bat CA HAI loai ay.
    #    Ha mot moc dem ma khong chot lai cho no chuyen toi la lam yeu banh coc.
    from platform_core.runtime_noi_bo import luong as _cua_song

    bat_o_cua_song = {
        (t.attr if isinstance(t, ast.Attribute) else getattr(t, "id", ""))
        for kh in ast.walk(ast.parse(inspect.getsource(_cua_song)))
        if isinstance(kh, ast.ExceptHandler) and kh.type
        for t in (kh.type.elts if isinstance(kh.type, ast.Tuple) else [kh.type])}
    for loai in ("DangBan", "KhongMoDuoc"):
        assert loai in bat_o_cua_song, (
            f"cua SONG khong con bat `{loai}` — luot that se vo ra ngoai thanh "
            "mot loi khong khuon thay vi mot khoi loi SSE khach doc duoc.")

    assert not xau, (
        "than tra ve cho KHACH dang mang van ban cua may B:\n  "
        + "\n  ".join(xau)
        + "\n\nGhi no vao log (da co), dung ghi vao phan hoi. Giu lai nhung "
          "truong khach HANH DONG DUOC: retry_after, limit_name, limit_value.")


def test_ba_nhanh_ban_deu_GHI_LOG():
    """Một sự cố năm giờ không để lại dòng nào là chuyện đã xảy ra thật."""
    from platform_core.runtime_noi_bo import luong
    from server.api import chat, streaming

    # Từ H43 Phase 02 (2026-09-03) nhánh bận của cửa STREAM sống ở facade
    # `platform_core/runtime_noi_bo/luong.py` (`mo_thuong_nguon`); `streaming.py`
    # chỉ còn nhánh bận của `_mot_cuc`. Ba nhánh, ba chỗ — vẫn đủ ba dòng log.
    for mod, so_toi_thieu in ((chat, 1), (streaming, 1), (luong, 1)):
        ma = inspect.getsource(mod)
        assert ma.count('log.warning("BAN') >= so_toi_thieu, (
            f"{mod.__name__}: nhanh ban phai ghi log — im lang la thu da lam "
            f"su co 31/08 mat nhieu gio moi lan ra")
