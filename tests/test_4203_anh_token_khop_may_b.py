r"""test_4203 — chi phí token ảnh khớp TỪNG Ô với số máy B thực sự đếm.

Bảng ``DO_THAT`` dưới đây là **số ĐO trên production ngày 28/09/2026**, lấy bằng
``tools/do_token_anh.py``: hiệu ``usage.prompt_tokens`` giữa một lượt CÓ ảnh và một
lượt KHÔNG ảnh với **y hệt một chuỗi chữ**, nên phần chữ triệt tiêu. Bảy ô giống hệt
nhau trên CẢ HAI model production (``qwen38-api`` và ``qwen35-api``).

⛔ **KHÔNG được sửa bảng này để làm test xanh.** Nó là số của engine, không phải kỳ
   vọng của ta. Mã lệch bảng ⇒ sửa ``anh_token.py``; nếu tin bảng sai thì phải ĐO LẠI
   bằng ``python tools/do_token_anh.py`` và ghi ngày + build, đừng gõ đè.

Hai ô cuối nằm Ở TRÊN và Ở DƯỚI trần 4.096 — chỗ duy nhất phân biệt được "thu nhỏ giữ
tỉ lệ" với "kẹp". Một bảng dừng ở 1080p không nói được gì về chỗ ấy.
"""
from __future__ import annotations

import ast
import io
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Trần engine đang chạy (llama.cpp b10883, `set_limit_image_tokens(8, 4096)` cho họ
#: Qwen3VL). Bảng dưới được đo với ĐÚNG hai số này.
TOI_THIEU = 8
TOI_DA = 4096

#: (rộng, cao) -> hiệu `prompt_tokens` đo được = token ảnh + TOKEN_DAU_VISION.
DO_THAT = {
    (320, 240): 82,
    (512, 512): 258,
    (1024, 768): 770,
    (1280, 720): 922,
    (1920, 1080): 2042,
    (2048, 2048): 4098,
    (3840, 2160): 4082,
}


# ── 1. Bánh cóc: mỗi ô của bảng đo là một phép khẳng định ───────────────────


@pytest.mark.parametrize("co", sorted(DO_THAT))
def test_khop_tung_o_cua_bang_do_tren_production(co):
    """Số ĐO 28/09/2026 trên cả hai model. ⛔ Đỏ ở đây thì sửa MÃ, không sửa bảng."""
    from platform_core.llm.anh_token import TOKEN_DAU_VISION, token_anh

    rong, cao = co
    tinh = token_anh(rong, cao, toi_thieu=TOI_THIEU, toi_da=TOI_DA) + TOKEN_DAU_VISION
    assert tinh == DO_THAT[co], f"{rong}x{cao}: tính {tinh}, máy B đếm {DO_THAT[co]}"


# ── 2. Tiêm nghịch cho BẪY 1: không được dùng `round()` của Python ──────────


@pytest.mark.parametrize("rong, cao, dung, neu_round", [
    # 720/32 = 22,5 đúng chằn. `math.floor(x+0.5)` -> 23; `round()` (về số CHẴN) -> 22.
    (1280, 720, 40 * 23, 40 * 22),      # 920 vs 880 — ảnh chụp màn hình phổ biến nhất
    (720, 720, 23 * 23, 22 * 22),       # 529 vs 484 — hai chiều cùng rơi vào nửa
    (1440, 208, 45 * 7, 45 * 6),        # 315 vs 270 — nửa ở chiều CAO (208/32 = 6,5)
])
def test_lam_tron_la_nua_LEN_khong_phai_round_cua_python(rong, cao, dung, neu_round):
    """C++ ``std::round`` làm tròn nửa LÊN; ``round()`` của Python làm tròn VỀ SỐ CHẴN.

    Lệch về chiều THIẾU (đặt chỗ ít hơn thực) ⇒ chiều nguy hiểm. Giá trị ``neu_round``
    ghi ở đây chính là thứ một bản dùng ``round()`` sẽ trả về — nếu test đỏ và số thực
    tế bằng ``neu_round`` thì mã đã tụt lại vào đúng cái bẫy đó.

    ⚠️ Ba ô này phải có phần nguyên CHẴN mới phân biệt được: ``round(22.5) == 22``
       nhưng ``round(7.5) == 8`` (về số chẵn ⇒ nửa khi lẻ thì LÊN). Một ô lẻ sẽ khớp
       cả hai cách làm tròn, tức một phép kiểm XANH mà không đo gì — bản nháp đầu của
       test này đúng là dùng 240 (7,5) và không phân biệt được gì.
    """
    from platform_core.llm.anh_token import token_anh

    co = token_anh(rong, cao, toi_thieu=TOI_THIEU, toi_da=TOI_DA)
    assert co != neu_round, f"{rong}x{cao}: {co} = đúng thứ round() cho ⇒ đang dùng round()"
    assert co == dung


# ── 3. Tiêm nghịch cho BẪY 2: vượt trần là THU NHỎ, không phải KẸP ──────────


def test_vuot_tran_thi_thu_nho_giu_ti_le_chu_khong_kep():
    """3840x2160 -> **4080**, ⛔ KHÔNG phải 4096.

    Một bản kẹp (``min(o, toi_da)``) sẽ trả đúng ``TOI_DA`` = 4096, cao hơn thực 16
    token ở MỌI ảnh 4K — và che mất việc ảnh đã bị thu nhỏ. Máy B đếm 4080 (bảng trên).
    """
    from platform_core.llm.anh_token import token_anh

    co = token_anh(3840, 2160, toi_thieu=TOI_THIEU, toi_da=TOI_DA)
    assert co != TOI_DA, "trả đúng trần ⇒ đang KẸP chứ không thu nhỏ giữ tỉ lệ"
    assert co == 4080
    # Và nhánh thu nhỏ KHÔNG được chạm vào ô vừa đúng trần (2048x2048 = 4096 chằn).
    assert token_anh(2048, 2048, toi_thieu=TOI_THIEU, toi_da=TOI_DA) == 4096


# ── 4. Hai bản giống hệt từng byte (khuôn test_1470) ────────────────────────


def test_hai_ban_anh_token_giong_het_tung_byte():
    """Máy B không có ``platform_core`` (Q102) ⇒ chép; lệch một byte là A giữ chỗ khác
    số B đếm, và sai lệch ấy không nổ ở đâu cả — nó chỉ làm sổ sai."""
    a = (GOC / "platform_core" / "llm" / "anh_token.py").read_bytes()
    b = (GOC / "llm_gateway" / "anh_token.py").read_bytes()
    assert a == b


@pytest.mark.parametrize("tep", ["platform_core/llm/anh_token.py",
                                 "llm_gateway/anh_token.py"])
def test_duong_nong_chi_dung_thu_vien_chuan(tep):
    """⛔ Không ``Pillow``, không gói ngoài: hàm này chạy trên đường nóng của cổng máy B.

    Đọc bằng **AST** chứ không ``grep`` chuỗi — một dòng nhắc tên gói trong chú thích
    không phải một lần import, và một ``import`` nằm trong hàm thì ``grep`` dễ bỏ sót.
    """
    cay = ast.parse((GOC / tep).read_text(encoding="utf-8"))
    goi = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Import):
            goi.update(t.name.split(".")[0] for t in nut.names)
        elif isinstance(nut, ast.ImportFrom) and nut.level == 0 and nut.module:
            goi.add(nut.module.split(".")[0])
    assert goi <= {"__future__", "math"}, f"{tep} kéo thêm phụ thuộc: {sorted(goi)}"


# ── 5. `kich_thuoc` trên ẢNH THẬT, cả năm định dạng ─────────────────────────


#: `png|jpeg|webp|gif` là những gì client DSH gửi được; `bmp` thì stb_image đọc được.
DUOI = ("PNG", "JPEG", "WEBP", "GIF", "BMP")


def _anh_that(rong: int, cao: int, dang: str, **them) -> bytes:
    """Dựng ảnh bằng Pillow — **chỉ trong test**. Mã sản phẩm thì không được.

    Gradient thay vì nhiễu: nội dung không ảnh hưởng gì tới kích thước header, mà nền
    phẳng thì tệp nhỏ hơn hẳn.
    """
    from PIL import Image

    im = Image.linear_gradient("L").resize((rong, cao)).convert("RGB")
    dem = io.BytesIO()
    im.save(dem, format=dang, **them)
    return dem.getvalue()


@pytest.mark.parametrize("dang", DUOI)
@pytest.mark.parametrize("rong, cao", [(320, 240), (1280, 720), (7, 13)])
def test_kich_thuoc_doc_dung_anh_that(dang, rong, cao):
    from platform_core.llm.anh_token import kich_thuoc

    assert kich_thuoc(_anh_that(rong, cao, dang)) == (rong, cao)


@pytest.mark.parametrize("them", [
    pytest.param({"progressive": True}, id="progressive_SOF2"),
    pytest.param({"exif": b"Exif\x00\x00" + b"\x00" * 9000}, id="exif_APP1_9KB"),
])
def test_jpeg_duyet_marker_chu_khong_doc_20_byte_dau(them):
    """SOF không ở chỗ cố định: EXIF vài KB đẩy nó đi xa, progressive đổi nó thành SOF2."""
    from platform_core.llm.anh_token import kich_thuoc

    assert kich_thuoc(_anh_that(1024, 768, "JPEG", **them)) == (1024, 768)


def test_webp_ca_hai_bien_the_chunk():
    """Pillow xuất ``VP8 `` (có mất) hoặc ``VP8L`` (không mất) tuỳ tham số — cả hai
    gói kích thước theo kiểu khác nhau, và cả hai đều phải đọc được."""
    from platform_core.llm.anh_token import kich_thuoc

    assert kich_thuoc(_anh_that(640, 480, "WEBP", lossless=False)) == (640, 480)
    assert kich_thuoc(_anh_that(640, 480, "WEBP", lossless=True)) == (640, 480)


# ── 6. Sàn và trần là CẦN GẠT thật, không phải hằng chết ────────────────────


def test_toi_thieu_chan_duoi_that():
    from platform_core.llm.anh_token import token_anh

    # 8x8 -> 0,25 x 0,25 ô -> 1 ô thô, sàn kéo lên đúng `toi_thieu`.
    assert token_anh(8, 8, toi_thieu=TOI_THIEU, toi_da=TOI_DA) == TOI_THIEU
    assert token_anh(1, 1, toi_thieu=TOI_THIEU, toi_da=TOI_DA) == TOI_THIEU
    # Và nó là THAM SỐ: đổi sàn thì kết quả đổi theo, không phải hằng ghim trong mã.
    assert token_anh(8, 8, toi_thieu=16, toi_da=TOI_DA) == 16
    assert token_anh(8, 8, toi_thieu=1, toi_da=TOI_DA) == 1
    # Sàn ⛔ không được kéo một ảnh vốn đã lớn hơn sàn.
    assert token_anh(512, 512, toi_thieu=TOI_THIEU, toi_da=TOI_DA) == 256


def test_toi_da_la_tham_so_cua_engine_khong_phai_hang_trong_ma():
    from platform_core.llm.anh_token import token_anh

    # Hạ trần xuống 1024: 2048x2048 thu nhỏ hệ số 2 -> 32 x 32 ô = 1024.
    assert token_anh(2048, 2048, toi_thieu=TOI_THIEU, toi_da=1024) == 1024
    # Cùng ảnh ấy với trần 4096 thì KHÔNG bị thu nhỏ.
    assert token_anh(2048, 2048, toi_thieu=TOI_THIEU, toi_da=TOI_DA) == 4096


def test_toi_thieu_va_toi_da_bat_buoc_la_keyword():
    """Chúng là số của ENGINE. Không mặc định, không vị trí — người gọi phải đọc từ
    cấu hình engine rồi truyền vào, để không có bản sao thứ hai của con số ấy."""
    from platform_core.llm.anh_token import token_anh

    with pytest.raises(TypeError):
        token_anh(512, 512, 8, 4096)          # type: ignore[misc]
    with pytest.raises(TypeError):
        token_anh(512, 512)                   # type: ignore[call-arg]
    with pytest.raises(TypeError):
        token_anh(512, 512, toi_thieu=8)      # type: ignore[call-arg]


# ── 7. Rác thì trả None, ⛔ không ném ───────────────────────────────────────


@pytest.mark.parametrize("rac", [
    pytest.param(b"", id="rong"),
    pytest.param(b"khong phai anh, chi la chu", id="van_ban"),
    pytest.param(b"\x00" * 64, id="byte_khong"),
    pytest.param(b"\x89PNG\r\n\x1a\n", id="png_cut_o_chu_ky"),
    pytest.param(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"IDAT" + b"\x00" * 8,
                 id="png_khong_co_IHDR"),
    pytest.param(b"\xff\xd8", id="jpeg_cut_ngay_sau_SOI"),
    pytest.param(b"\xff\xd8\xff\xda\x00\x02", id="jpeg_vao_SOS_ma_chua_co_SOF"),
    pytest.param(b"RIFF\x00\x00\x00\x00WAVEfmt ", id="riff_nhung_la_wav"),
    pytest.param(b"RIFF\x00\x00\x00\x00WEBPVP8 ", id="webp_cut_truoc_kich_thuoc"),
    pytest.param(b"GIF89a", id="gif_cut"),
    pytest.param(b"BM" + b"\x00" * 30, id="bmp_dib_header_rong"),
])
def test_rac_tra_none_khong_nem(rac):
    from platform_core.llm.anh_token import kich_thuoc

    assert kich_thuoc(rac) is None


def test_bmp_cao_am_van_ra_so_duong():
    """Cao ÂM trong BITMAPINFOHEADER nghĩa là ảnh lưu từ trên xuống — vẫn từng ấy điểm
    ảnh, nên vẫn từng ấy token. Trả số âm ở đây sẽ làm ``token_anh`` ra rác."""
    from platform_core.llm.anh_token import kich_thuoc

    goc = bytearray(_anh_that(64, 48, "BMP"))
    goc[22:26] = (-48).to_bytes(4, "little", signed=True)
    assert kich_thuoc(bytes(goc)) == (64, 48)
