"""HM-2 — `MayThat`: chuyển tiếp HTTP tới pod, **không diễn giải**.

## Phép kiểm quan trọng nhất ở đây không phải về `MayThat`

Nó về **cầu nối chạy trên pod** (`tools/wangp/dich_vu_ccloud.py`). Một phép biến
đổi đặt ở đó là một chỗ suy diễn nằm **ngoài tầm với của gate** — gate chạy trên
máy A, cầu nối chạy trên máy thuê. Sai ở đấy thì không lượt kiểm nào ở đây thấy,
và nó chỉ lộ ra khi có người dùng thật.

⇒ Bốn đường tra cứu phải **thô**: nhận tham số, gọi WanGP, trả nguyên văn.

## Tri thức phải sống sót qua lần gỡ `wangp_client.py`

Cloudflare (đứng trước proxy RunPod) chặn User-Agent mặc định của `urllib`
(`Python-urllib/3.x`) bằng **HTTP 403 `error code: 1010`**. Kiểu hỏng này khó
lần nhất trong cả tuyến vì:

- dịch vụ phía pod **đang chạy đúng**
- log phía pod **sạch không một dòng** — yêu cầu chưa từng tới nơi
- `curl` từ **cùng máy** lại trả 200

Đo 06/09/2026: bốn biến thể header xác thực đều 403; đổi mỗi User-Agent thì 200.
Gỡ một tệp mà đánh rơi bài học của nó là trả lại đúng số giờ đã mất để tìm ra.
"""
from __future__ import annotations

import ast
import inspect

import pytest


def _than_ham(ma: str, ten_ham: str) -> ast.FunctionDef:
    cay = ast.parse(ma)
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ten_ham:
            return n
    raise AssertionError(f"khong tim thay ham {ten_ham!r}")


BON_DUONG = ("tra_cuu_model", "tra_cuu_so_do", "tra_cuu_mac_dinh",
             "tra_cuu_kha_dung")


@pytest.mark.parametrize("ten", BON_DUONG)
def test_cau_noi_chi_CHUYEN_TIEP_khong_bien_doi(ten):
    """🔑 Không `if`, không `for`, không `try/except` nuốt lỗi trong bốn đường
    tra cứu.

    ⭐ Vì sao cấm cả `for`: đường `/metadata` cũ **lặp qua mọi model** rồi nhét
      lỗi của từng model vào chính ô của nó (`{"loi": ...}`). Nghe như phòng
      thủ, thực ra là **giấu hỏng hóc vào trong dữ liệu** — tầng trên đọc ô ấy
      như một năng lực, và một model hỏng trông giống một model không có năng
      lực.

    ⛔ Dùng AST chứ không `grep`: một chú thích nhắc tới `if` sẽ làm phép kiểm
       chuỗi báo động sai, và chuyện ấy đã xảy ra bốn lần ở kho này.
    """
    from tools.wangp import dich_vu_ccloud

    han = _than_ham(inspect.getsource(dich_vu_ccloud), ten)
    xau = [type(n).__name__ for n in ast.walk(han)
           if isinstance(n, (ast.If, ast.For, ast.While, ast.Try,
                             ast.ListComp, ast.DictComp))]
    assert not xau, (
        f"{ten} dang BIEN DOI ket qua ({xau}) — cau noi phai chuyen tiep tho, "
        "vi mot phep bien doi o day nam NGOAI tam voi cua gate")


def test_may_that_thuc_hien_du_giao_uoc():
    from apps.lttvideo.cong.giao_uoc import May
    from apps.lttvideo.cong.may_that import MayThat

    import typing
    can = set(typing.get_protocol_members(May))
    thieu = [t for t in can if not callable(getattr(MayThat, t, None))]
    assert not thieu, f"MayThat thieu: {thieu}"


def test_giu_lai_User_Agent_TRINH_DUYET():
    """🔴 Bài học 06/09 phải sống sót qua lần gỡ `wangp_client.py`.

    Không có nó thì Cloudflare trả 403 `error code: 1010` **trước khi** yêu cầu
    tới pod — và triệu chứng là: dịch vụ chạy đúng, log pod sạch, `curl` cùng
    máy thì 200. Không có dấu vết nào chỉ về nguyên nhân.
    """
    from apps.lttvideo.cong import may_that

    ma = inspect.getsource(may_that)
    assert "Mozilla/5.0" in ma, (
        "mat User-Agent trinh duyet — Cloudflare se chan 403 error code 1010, "
        "va log phia pod se SACH nen khong ai lan ra")
    assert "1010" in ma, "mat chu thich giai thich vi sao — lan sau lai mat UA"


def test_moi_loi_HTTP_deu_thanh_LoiMay():
    """Tầng trên bắt **một** kiểu ngoại lệ. Để lọt `URLError`/`HTTPError` ra
    ngoài là để lọt một đường lỗi, và một đường lỗi lọt trong worker nghĩa là
    job treo tới hết hạn thay vì hỏng ngay và hoàn credit."""
    from apps.lttvideo.cong import may_that
    from apps.lttvideo.cong.giao_uoc import LoiMay

    m = may_that.MayThat("http://127.0.0.1:9", khoa="x")   # cong 9 = discard
    with pytest.raises(LoiMay):
        m.so_do("t2v_2_2")


def test_KHONG_AI_con_import_wangp_client():
    """⛔ Đo bằng AST trên toàn cây, không bằng `grep`.

    Và **không để lại lớp bọc tương thích**: một lớp bọc giữ nguyên đường import
    cũ, nên không ai bị buộc phải sửa, nên tầng cũ sống mãi dưới tên mới.
    """
    import pathlib

    kho = pathlib.Path(__file__).resolve().parents[1]
    pham = []
    for tep in list((kho / "apps").rglob("*.py")) + \
               list((kho / "tools").rglob("*.py")) + \
               list((kho / "tests").rglob("*.py")):
        if tep.name == pathlib.Path(__file__).name:
            continue
        try:
            cay = ast.parse(tep.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            if isinstance(n, ast.ImportFrom) and "wangp_client" in (n.module or ""):
                pham.append(f"{tep.relative_to(kho)}:{n.lineno}")
            if isinstance(n, ast.Import):
                pham += [f"{tep.relative_to(kho)}:{n.lineno}"
                         for a in n.names if "wangp_client" in a.name]
    assert not pham, f"con import `wangp_client` da go: {pham}"


def test_tep_wangp_client_DA_BI_XOA():
    """Gỡ import mà để tệp lại là để một tầng chết nằm chờ ai đó import lại."""
    import pathlib

    kho = pathlib.Path(__file__).resolve().parents[1]
    assert not (kho / "apps" / "lttvideo" / "wangp_client.py").exists()
