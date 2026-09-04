"""
test_633 — Ảnh người dùng **gửi vào** cho model vision. (H43 Phase 13, hành trình B)

🔴 VÌ SAO HẠNG MỤC NÀY TỒN TẠI. Catalog ChatLTT quảng cáo `ltt_llm_vision` với
   `constraints.reads_images = true`, nhưng giao diện **không có chỗ đính ảnh**
   — không một `input[type=file]` nào, kể cả khi đã chọn đúng model đó. Tìm ra
   ở lượt chạy tươi hành trình B của Phase 13.

⛔ `MVP_ACCEPTANCE.md` ghi *"vision if advertised"*. Quảng cáo một năng lực
   không dùng được thì tệ hơn không có nó: khách chọn model vision, gõ "ảnh này
   là gì", và nhận một câu trả lời tự tin về một bức ảnh model chưa từng thấy.

Bốn nhóm bất biến:
  1. Kiểm ảnh: chỉ PNG/JPEG/WebP thật, theo byte chứ không theo MIME khai báo.
  2. Sở hữu: khoá mang `<uid>`, và đường thoát `..` bị chặn từng đoạn.
  3. Ngữ cảnh: chỉ gửi `image_url` khi alias **đã khai** `reads_images`.
  4. Trần: số ảnh mỗi lượt, và số ảnh gửi lại trong cả đường hội thoại.
"""
from __future__ import annotations

import io

import pytest

def _png(w: int = 64, h: int = 64) -> bytes:
    """PNG hop le nho nhat ma `image_input` chap nhan.

    ⚠️ 64×64 chu khong 1×1: `platform_core/image_input.py:47` chan moi anh duoi
       64 px moi chieu. Ban dau cua tep nay dung 1×1 va **muoi phep kiem do
       cung luc**, voi mot thong bao ve "kich thuoc" chu khong ve noi dung phep
       kiem — mot cach rat ton thoi gian de hoc lai mot hang so da co san.
    """
    import struct
    import zlib

    raw = b"".join(b"\x00" + b"\x80\x80\x80" * w for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return (struct.pack(">I", len(d)) + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


ANH = _png()


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "v.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_STORAGE_DIR", str(tmp_path / "kho"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    import platform_core.storage as st
    if hasattr(st, "reset_storage"):
        st.reset_storage()
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


# ── 1. Kiểm ảnh ─────────────────────────────────────────────────────────────

def test_luu_anh_that_tra_ve_khoa_mang_chu_so_huu(moi_truong):
    from apps.chatltt.services import anh_vao as AV

    kq = AV.luu(ANH, "image/png", user_id="u-anh")
    assert kq["mime"] == "image/png"
    assert kq["rong"] == 64 and kq["cao"] == 64
    # 🔴 HINH KHOA DOI 04/09: `chatltt/<uid>/anh-vao/...`, uid o DOAN THU HAI.
    #
    #    Ban cu la `chatltt/anh-vao/<uid>/...`, va hau qua do duoc: moi anh khach
    #    tai len trong chat bi `image.ltt` TU CHOI voi cau "Anh tham chieu khong
    #    thuoc nguoi dung hien tai" — vi `anhnoibo._kiem_chu_so_huu` kiem dung
    #    doan thu hai. Tao-anh-tu-anh khong chay duoc, du ca hai dau da san sang.
    #
    # ⭐ Nen chot MENH DE (uid o dung cho quy uoc doi) chu khong chot mot chuoi:
    #    mot chuoi chi noi "no la the nay", con menh de noi "no phai the nay vi
    #    app khac doc no o do".
    assert kq["key"].split("/")[:1] == ["chatltt"]
    assert kq["key"].split("/")[1] == "u-anh", "uid phai o doan thu hai (quy uoc kho)"
    assert kq["key"].split("/")[2] == "anh-vao"
    from apps.anhnoibo import features as _F
    assert _F._kiem_chu_so_huu(kq["key"], "u-anh") == kq["key"], (
        "khoa moi phai qua duoc cua kiem so huu cua `image.ltt`")
    assert kq["key"].endswith(".png")


def test_khong_tin_MIME_cua_trinh_duyet(moi_truong):
    """Khai `image/png` nhưng byte là văn bản ⇒ từ chối."""
    from apps.chatltt.services import anh_vao as AV

    with pytest.raises(AV.LoiAnhVao):
        AV.luu(b"khong phai anh dau", "image/png", user_id="u-anh")


def test_anh_rong_va_thieu_chu_so_huu_deu_bi_tu_choi(moi_truong):
    from apps.chatltt.services import anh_vao as AV

    with pytest.raises(AV.LoiAnhVao):
        AV.luu(b"", "image/png", user_id="u-anh")
    with pytest.raises(AV.LoiAnhVao):
        AV.luu(ANH, "image/png", user_id="")


# ── 2. Sở hữu ───────────────────────────────────────────────────────────────

def test_khoa_cua_nguoi_khac_khong_qua_duoc_cua_tai_san(moi_truong):
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import tao_media as TM

    kq = AV.luu(ANH, "image/png", user_id="u-mot")
    assert TM.kiem_so_huu_khoa(kq["key"], "u-mot") is True
    assert TM.kiem_so_huu_khoa(kq["key"], "u-hai") is False


@pytest.mark.parametrize("xau", [
    "chatltt/anh-vao/u-mot/../../secrets/app.env",
    "chatltt/anh-vao/u-mot/./x.png",
    "chatltt/anh-vao//x.png",
    "chatltt\\anh-vao\\u-mot\\x.png",
    "chatltt/anh-vao/u-mot",                       # thiếu đoạn tên tệp
    "chatltt/anh-vao/u-mot/a/b.png",               # thừa một đoạn
])
def test_hinh_khoa_la_deu_bi_tu_choi(xau):
    """⛔ Chỉ so tiền tố thì `.../u-mot/../../secrets/app.env` ĐI LỌT — ba đoạn
       đầu đúng hết, phần thoát nằm ở sau. Đúng lỗi `test_625` đã bắt một lần."""
    from apps.chatltt.services import anh_vao as AV

    assert AV.la_khoa_anh_vao(xau, "u-mot") is False


# ── 3. Ngữ cảnh chỉ có ảnh khi model ĐÃ KHAI đọc ảnh ────────────────────────

def _duong(khoi_user):
    class _M:
        def __init__(self, role, blocks):
            self.role, self.blocks = role, blocks
    return [_M("user", khoi_user)]


def test_khong_doc_anh_thi_khoi_image_bi_bo_hoan_toan(moi_truong):
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    k = AV.luu(ANH, "image/png", user_id="u-anh")["key"]
    duong = _duong([{"type": "text", "text": "anh nay la gi"},
                    {"type": "image", "key": k}])
    tin = L.dung_ngu_canh(duong, doc_anh=False)
    assert tin == [{"role": "user", "content": "anh nay la gi"}]


def test_doc_anh_thi_content_thanh_parts_co_image_url(moi_truong):
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    k = AV.luu(ANH, "image/png", user_id="u-anh")["key"]
    duong = _duong([{"type": "text", "text": "anh nay la gi"},
                    {"type": "image", "key": k}])
    tin = L.dung_ngu_canh(duong, doc_anh=True)
    assert len(tin) == 1
    parts = tin[0]["content"]
    assert isinstance(parts, list)
    assert parts[0] == {"type": "text", "text": "anh nay la gi"}
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_gui_URL_chu_khong_data_uri_la_mot_cua_khong_ai_muon(moi_truong):
    """⛔ Model chạy ở máy B trong LAN. Một `/chatltt/tai-san/...` với nó là một
       trang đăng nhập; và nếu nó *đọc được* thì ta vừa mở một đường tải ảnh của
       khách **không cần phiên**."""
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    k = AV.luu(ANH, "image/png", user_id="u-anh")["key"]
    tin = L.dung_ngu_canh(_duong([{"type": "image", "key": k}]), doc_anh=True)
    url = tin[0]["content"][0]["image_url"]["url"]
    assert url.startswith("data:")
    assert "/tai-san/" not in url and "http" not in url.split(",", 1)[0]


def test_anh_da_bi_don_khoi_kho_khong_lam_hong_ca_luot(moi_truong):
    from apps.chatltt.services import luot as L

    duong = _duong([{"type": "text", "text": "con day"},
                    {"type": "image", "key": "chatltt/anh-vao/u-anh/mat-tieu.png"}])
    tin = L.dung_ngu_canh(duong, doc_anh=True)
    assert tin == [{"role": "user", "content": "con day"}]


def test_doc_anh_duoc_theo_HOP_DONG_chu_khong_theo_TEN(moi_truong):
    from apps.chatltt.services import luot as L

    assert L.doc_anh_duoc(moi_truong, "ltt_llm_vision") is True
    assert L.doc_anh_duoc(moi_truong, "ltt_llm") is False
    assert L.doc_anh_duoc(moi_truong, "khong-ton-tai") is False


# ── 4. Trần ─────────────────────────────────────────────────────────────────

def test_tran_so_anh_trong_ngu_canh_giu_nhung_anh_MOI_NHAT(moi_truong):
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    n = AV.TOI_DA_TRONG_NGU_CANH
    khoi = [{"type": "text", "text": "nhieu anh"}]
    khoa = [AV.luu(ANH, "image/png", user_id="u-anh")["key"] for _ in range(n + 3)]
    khoi += [{"type": "image", "key": k} for k in khoa]

    tin = L.dung_ngu_canh(_duong(khoi), doc_anh=True)
    anh = [p for p in tin[0]["content"] if p["type"] == "image_url"]
    assert len(anh) == n, "phai cat theo tran, khong gui het"


def test_gui_qua_tran_moi_luot_thi_TU_CHOI_chu_khong_cat_bot(moi_truong):
    """⛔ Cắt bớt im lặng là gửi model ít hơn thứ khách nghĩ họ đã gửi, và tính
       tiền cho lượt đó. Từ chối thì họ biết ngay."""
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    qua = [AV.luu(ANH, "image/png", user_id="u-anh")["key"]
           for _ in range(AV.TOI_DA_MOI_LUOT + 1)]
    with pytest.raises(L.ThamSoSai):
        L._khoi_anh(moi_truong, qua, user_id="u-anh", alias="ltt_llm_vision")


def test_dinh_anh_cho_model_KHONG_doc_anh_thi_tu_choi(moi_truong):
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    k = AV.luu(ANH, "image/png", user_id="u-anh")["key"]
    with pytest.raises(L.ThamSoSai):
        L._khoi_anh(moi_truong, [k], user_id="u-anh", alias="ltt_llm")


def test_dinh_anh_CUA_NGUOI_KHAC_thi_tu_choi(moi_truong):
    """🔴 Khoá đi qua thân JSON. Không kiểm ở máy chủ thì một người gõ tay khoá
       của người khác sẽ đính ảnh đó vào hội thoại của mình, rồi đọc nội dung
       ảnh qua chính câu trả lời của model — một đường rò không đi qua cửa
       `/tai-san` nào cả."""
    from apps.chatltt.services import anh_vao as AV
    from apps.chatltt.services import luot as L

    cua_nguoi_khac = AV.luu(ANH, "image/png", user_id="u-nguoi-khac")["key"]
    with pytest.raises(L.ThamSoSai):
        L._khoi_anh(moi_truong, [cua_nguoi_khac], user_id="u-toi",
                    alias="ltt_llm_vision")


def test_khong_dinh_anh_thi_khong_kiem_gi_ca(moi_truong):
    """Đường đi thường ngày (chat text) không được trả phí cho tính năng này."""
    from apps.chatltt.services import luot as L

    assert L._khoi_anh(moi_truong, None, user_id="u", alias="ltt_llm") == []
    assert L._khoi_anh(moi_truong, [], user_id="u", alias="ltt_llm") == []
    assert L._khoi_anh(moi_truong, ["  "], user_id="u", alias="ltt_llm") == []
