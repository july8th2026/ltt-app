"""704 — bánh cóc: MỘT bộ trả lời Range cho cả nền tảng, và mọi `<video>` phát tại chỗ.

## Vì sao cần bánh cóc chứ không chỉ cần một lần dọn

Ngày 05/09 đo được **năm** bản chép gần như giống nhau từng dòng của cùng một bộ
phân tích `Range` — `taovideo`, `taoclipngan`, `upscalevideo`, `agent`,
`autosubvideo` — cộng hai app phục vụ media mà không có Range gì cả.

⭐ Điều đáng nói không phải "có năm bản chép". Là **cả năm đều mang cùng bốn
   khiếm khuyết**: không bao giờ trả `416`; `bytes=-500` trả 501 byte ĐẦU thay vì
   500 byte cuối; `bytes=0-` nuốt cả tệp vào RAM; `start > end` xử lý mỗi nơi một
   kiểu. Sửa một chỗ không cứu bốn chỗ kia.

⚠️ Và chúng ra đời **không phải vì ai đó cẩu thả**: viết một route media mới thì
   việc tự nhiên nhất là chép route gần nhất đang chạy. Nên thứ chặn được nó
   không phải một dòng chú thích, mà là một phép kiểm đỏ ngay lượt gate đầu tiên.

Đọc AST — không phải chuỗi — nên chính đoạn giải thích ở trên không làm nó đỏ.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
#: Nơi DUY NHẤT được phép dựng một phản hồi Range.
CHU_NHA = "platform_core/phat_media.py"


def tep_py(*thu_muc: str):
    for tm in thu_muc:
        for p in (GOC / tm).rglob("*.py"):
            # `vendor/` (vd `apps/video_crawler/vendor/f2_abogus/`) là mã bên
            # thứ ba chép NGUYÊN VĂN (LICENSE/NOTICE kèm theo), không phải
            # route media của ta — cùng lý do và cùng cách loại như các phép
            # kiểm khác trong kho (vd test_148_frontend_bundle.py,
            # test_149_presign_khong_nuot_loi.py, test_151_worker_gpu.py đều
            # loại "vendor" khỏi path.parts).
            if {"__pycache__", "vendor"} & set(p.parts):
                continue
            yield p


def cay(p: pathlib.Path):
    try:
        return ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return None


# ── 1. Chỉ một nơi được trả 206 ────────────────────────────────────────────

def test_chi_phat_media_duoc_dung_206():
    """`206` dựng bằng tay ở nơi khác nghĩa là một bộ Range thứ hai vừa ra đời."""
    vi_pham = []
    for p in tep_py("apps", "server", "platform_core"):
        if p.relative_to(GOC).as_posix() == CHU_NHA:
            continue
        t = cay(p)
        if t is None:
            continue
        for nut in ast.walk(t):
            if isinstance(nut, ast.Constant) and nut.value == 206:
                vi_pham.append(f"{p.relative_to(GOC).as_posix()}:{nut.lineno}")
    assert not vi_pham, (
        "có nơi dựng `206` ngoài `platform_core/phat_media.py` — dùng "
        "`phat_media.phat_tu_kho()` thay vì viết lại bộ Range: " + ", ".join(vi_pham))


# ── 2. Không app nào tự đọc header `Range` rồi tự cắt byte ────────────────

def test_khong_app_nao_tu_phan_tich_header_range():
    """Đọc `range` để **truyền cho** `phat_tu_kho` thì được; tự cắt thì không.

    Phân biệt bằng AST: vi phạm là khi trong cùng một hàm vừa đọc
    `headers.get("range")` vừa gọi `.seek(` hoặc `.partition("-")`.
    """
    vi_pham = []
    for p in tep_py("apps"):
        t = cay(p)
        if t is None:
            continue
        for ham in ast.walk(t):
            if not isinstance(ham, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc_range = tu_cat = False
            for nut in ast.walk(ham):
                if not isinstance(nut, ast.Call):
                    continue
                f = nut.func
                if (isinstance(f, ast.Attribute) and f.attr == "get"
                        and nut.args and isinstance(nut.args[0], ast.Constant)
                        and str(nut.args[0].value).lower() == "range"):
                    doc_range = True
                if isinstance(f, ast.Attribute) and f.attr == "seek":
                    tu_cat = True
                if (isinstance(f, ast.Attribute) and f.attr == "partition"
                        and nut.args and isinstance(nut.args[0], ast.Constant)
                        and nut.args[0].value == "-"):
                    tu_cat = True
            if doc_range and tu_cat:
                vi_pham.append(
                    f"{p.relative_to(GOC).as_posix()}::{ham.name}:{ham.lineno}")
    assert not vi_pham, (
        "app tự phân tích `Range` rồi tự cắt byte — đó là bản chép thứ sáu: "
        + ", ".join(vi_pham))


# ── 3. Không route media nào đọc toàn tệp vào RAM ─────────────────────────

def test_khong_route_media_nao_doc_toan_tep_roi_boc_BytesIO():
    """`StreamingResponse(io.BytesIO(f.read()))` là khuôn đã sinh ra cả hai lỗi P0.

    Nó chạy được, trả 200, không lỗi nào trong log — nên nó sẽ quay lại nếu chỉ
    có một chú thích cản.
    """
    vi_pham = []
    for p in tep_py("apps"):
        t = cay(p)
        if t is None:
            continue
        for nut in ast.walk(t):
            if not (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name)
                    and nut.func.id == "StreamingResponse" and nut.args):
                continue
            dau = nut.args[0]
            if not (isinstance(dau, ast.Call) and isinstance(dau.func, ast.Attribute)
                    and dau.func.attr == "BytesIO" and dau.args):
                continue
            trong = dau.args[0]
            if (isinstance(trong, ast.Call) and isinstance(trong.func, ast.Attribute)
                    and trong.func.attr == "read"):
                vi_pham.append(f"{p.relative_to(GOC).as_posix()}:{nut.lineno}")
    assert not vi_pham, (
        "route media đọc toàn tệp vào RAM rồi bọc BytesIO — dùng "
        "`phat_media.phat_tu_kho`: " + ", ".join(vi_pham))


# ── 4. Mọi `<video>` phải phát tại chỗ trên iPhone ────────────────────────

_THE_VIDEO = re.compile(r"<video\b[^>]*>", re.I)


def test_moi_the_video_deu_co_playsinline():
    """Thiếu `playsinline`, iOS ép phát TOÀN MÀN HÌNH thay vì phát tại chỗ.

    Theo chính sách media iOS của WebKit. Một thẻ thiếu nó không báo lỗi gì —
    người dùng chỉ thấy trình phát bất ngờ chiếm cả màn hình.

    ⚠️ Quét cả `.tsx`: ở JSX thuộc tính là `playsInline` (chữ I hoa), và một
       phép kiểm chỉ tìm chữ thường sẽ bỏ lọt cả bốn app React.
    """
    vi_pham, so_the = [], 0
    for tm, duoi in (("apps", (".html",)), ("server/templates", (".html",)),
                     ("frontend", (".tsx", ".jsx"))):
        goc_tm = GOC / tm
        if not goc_tm.exists():
            continue
        for p in goc_tm.rglob("*"):
            if p.suffix not in duoi or "node_modules" in p.parts:
                continue
            noi_dung = p.read_text(encoding="utf-8", errors="ignore")
            for m in _THE_VIDEO.finditer(noi_dung):
                so_the += 1
                if "playsinline" not in m.group(0).lower():
                    dong = noi_dung.count("\n", 0, m.start()) + 1
                    vi_pham.append(f"{p.relative_to(GOC).as_posix()}:{dong}")

    # ⛔ ĐỐI CHỨNG (Bẫy 31) — thêm 07/09/2026.
    #
    #    `test_bo_do_the_video_that_su_bat_duoc_the_thieu` ngay dưới chứng minh
    #    **mẫu regex** bắt được một thẻ thiếu. Nó KHÔNG chứng minh lượt quét
    #    này tìm thấy thẻ nào thật: nếu `<video>` đổi dạng (đổi sang một
    #    component React bọc lại, chẳng hạn), `finditer` khớp 0, `vi_pham`
    #    rỗng, phép kiểm chính XANH — mà phép kiểm đối chứng kia **vẫn xanh**,
    #    vì nó chạy trên một chuỗi viết sẵn.
    #
    # ⭐ Hai đối chứng khác nhau, và cần cả hai: một cái hỏi *"dụng cụ có hoạt
    #    động không"*, cái này hỏi *"nó có nhìn thấy gì không"*.
    #
    #    Đo 07/09/2026: 10 thẻ `<video`.
    assert so_the >= 10, (
        f"chi thay {so_the} the <video> — mong doi >= 10. Hoac cach dung video "
        f"da doi (thi SUA mau `_THE_VIDEO` va con so nay), hoac mot man hinh "
        f"da bo video. Ca hai deu phai xem bang MAT.")

    assert not vi_pham, (
        "thẻ <video> thiếu `playsinline` — iOS sẽ ép phát toàn màn hình: "
        + ", ".join(vi_pham))


def test_bo_do_the_video_that_su_bat_duoc_the_thieu():
    """Một phép kiểm không bao giờ đỏ được thì không chứng minh gì.

    Chứng minh trên chuỗi tự dựng, KHÔNG sửa tệp trong kho — một phép kiểm sửa
    tạm tệp thật sẽ làm `gate.py` báo "CÂY ĐÃ ĐỔI TRONG LÚC CHẠY".
    """
    xau = '<video controls preload="metadata"></video>'
    tot = '<video controls playsinline preload="metadata"></video>'
    tot_jsx = '<video controls playsInline preload="metadata"/>'
    assert "playsinline" not in _THE_VIDEO.search(xau).group(0).lower()
    assert "playsinline" in _THE_VIDEO.search(tot).group(0).lower()
    assert "playsinline" in _THE_VIDEO.search(tot_jsx).group(0).lower(), (
        "phải bắt được cả cách viết JSX `playsInline`")


# ── 5. Chủ nhà phải thật sự là chủ nhà ────────────────────────────────────

def test_phat_media_ton_tai_va_co_du_ba_ma_trang_thai():
    """Nếu `phat_media` mất ba mã trạng thái thì bốn phép kiểm trên vô nghĩa."""
    p = GOC / CHU_NHA
    assert p.exists(), f"{CHU_NHA} biến mất — bốn phép kiểm trên đang canh một cái cửa không có nhà"
    s = p.read_text(encoding="utf-8")
    for ma in ("206", "416"):
        assert ma in s, f"`phat_media` không còn dựng `{ma}`"


@pytest.mark.parametrize("slug", [
    "taovideo", "taoclipngan", "upscalevideo", "autosubvideo", "chatltt",
])
def test_app_tung_co_ban_chep_nay_gio_goi_lop_dung_chung(slug):
    """Chốt TẬP HỢP, không chốt số lượng.

    Một phép kiểm "còn đúng 5 app dùng phat_media" sẽ đỏ khi có app thứ sáu —
    tức nó phạt đúng việc ta muốn khuyến khích.
    """
    tep = list((GOC / "apps" / slug).rglob("*.py"))
    assert any("phat_media" in p.read_text(encoding="utf-8", errors="ignore")
               for p in tep if "__pycache__" not in p.parts), (
        f"`{slug}` không còn gọi `phat_media` — hoặc nó đã tự viết lại bộ Range, "
        "hoặc route media của nó biến mất")
