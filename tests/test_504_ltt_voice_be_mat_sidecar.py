r"""BỀ MẶT SIDECAR — cái nào ĐANG PHỤC VỤ, cái nào chỉ MỚI ĐƯỢC XÂY.

## Vì sao cần một bản kiểm kê có phép kiểm

Lượt soát 07/09/2026 đếm được: `voice_sidecar/server.py` mở **chín** cửa, và
`sidecar_client` bọc đủ chín. Nhưng chỉ **bốn** cửa có người gọi trong đường
sản phẩm; số còn lại hoặc chỉ được `tools/do_*.py` gọi, hoặc không ai gọi.

⛔ Trạng thái ấy tự nó **không sai** — một cửa dựng trước khi có người dùng là
   chuyện bình thường. Cái sai là để nó **không được ghi ra**: một hàm có mặt,
   có docstring, có timeout, trông y hệt một hàm đang phục vụ khách. Ba tháng
   sau không ai phân biệt được "chưa nối" với "đã nối rồi hỏng".

⭐ Nên tệp này không đòi gỡ gì và không đòi nối gì. Nó chốt **bản kiểm kê**:
   đổi trạng thái của một cửa thì phải sửa bảng dưới đây, và sửa bảng là một
   hành động có chủ ý mà người review nhìn thấy.

## ⛔ Vì sao không chỉ viết vào tài liệu

`CLAUDE.md` đã ghi lớp lỗi ấy ở mục *"Hiện giờ cái gì đang sống"*: một bảng
chép tay nói sai **năm lần**, và cả năm đều về phía nguy hiểm. Bảng ở đây khác
ở đúng một điểm — nó **được kiểm lại bằng máy** mỗi lượt gate.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice import sidecar_client

GOC = pathlib.Path(__file__).resolve().parents[1]

#: `ten_ham` -> trạng thái nối vào SẢN PHẨM.
#:
#:   "san_pham"  — có ít nhất một nơi gọi ngoài `tools/` và ngoài `tests/`
#:   "cong_cu"   — chỉ `tools/do_*.py` gọi (đo đạc / vận hành), KHÔNG phải sản phẩm
#:   "chua_noi"  — không nơi nào gọi
KIEM_KE = {
    "noi":             "san_pham",   # jobs.py, nghe_thu.py
    "lo_ra_tep":       "san_pham",   # ban_doc_dai.py
    "ghep_tep":        "san_pham",   # ban_doc_dai.py
    "ghi_danh":        "san_pham",   # jobs.py::_ghi_danh
    "noi_lo":          "cong_cu",    # tools/do_lo_giong.py
    "noi_dai":         "cong_cu",    # tools/do_troi_tong.py — `ban_doc_dai` thay thế
    "ghi_danh_kho":    "cong_cu",    # tools/do_nhan_ban_tu_kho_cu.py
    "nang_luc":        "chua_noi",
    "giong_dung_san":  "chua_noi",   # cố ý — `giong_mau.py` đọc ảnh chụp tĩnh
}

#: Thư mục coi là "đường sản phẩm". `tools/` và `tests/` KHÔNG nằm ở đây, và đó
#: là toàn bộ điểm của phép đếm: một cửa chỉ có công cụ đo gọi thì nó chưa phục
#: vụ khách nào.
DUONG_SAN_PHAM = ("apps", "platform_core", "server", "nexus_agent",
                  "llm_gateway", "render_gateway")


def _nguon_py(goc: str):
    for d in (GOC / goc).rglob("*.py"):
        if "__pycache__" in d.parts:
            continue
        yield d


def _dem_nguoi_goi(ten: str, thu_muc) -> list:
    """Nơi **dùng** `sidecar_client.<ten>` — đọc AST, không khớp chuỗi.

    ⛔ Khớp chuỗi sẽ đếm cả chú thích và docstring, và tệp này thì **đầy** chú
       thích nhắc tên hàm. Một bánh cóc khớp với chính lời giải thích của nó
       không chốt được gì (đã mắc lỗi ấy nhiều lần trong dự án này).

    🔴 ĐẾM MỌI THAM CHIẾU, KHÔNG CHỈ ĐẾM LỜI GỌI — và bản đầu của tệp này đã
       sai đúng chỗ đó. Nó tìm `ast.Call`, nên nó kết luận `sidecar_client.noi`
       **không ai gọi**, trong khi `features.goi_cong` viết:

           return _goi_va_dich_loi(sidecar_client.noi, text, ...)

       tức truyền hàm đi như một GIÁ TRỊ. Lời gọi thật xảy ra bên trong
       `_goi_va_dich_loi`, ở một chỗ mà tên hàm không còn xuất hiện.

    ⭐ Bài học rộng hơn cái lỗi: một phép đo "có ai gọi không" mà chỉ nhìn cú
       pháp gọi sẽ báo **chết oan** cho đúng những hàm được truyền qua một lớp
       bọc — mà lớp bọc ấy thường tồn tại vì hàm đó QUAN TRỌNG.
    """
    ra = []
    for goc in thu_muc:
        for d in _nguon_py(goc):
            if d.name == "sidecar_client.py":
                continue
            try:
                cay = ast.parse(d.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for n in ast.walk(cay):
                # `<gi do co chu 'sidecar'>.<ten>` — dang goi HOAC dang tham chieu.
                if (isinstance(n, ast.Attribute) and n.attr == ten
                        and isinstance(n.value, ast.Name)
                        and "sidecar" in n.value.id):
                    ra.append(str(d.relative_to(GOC)))
                    break
    return ra


def _ham_cong_khai() -> set:
    """Hàm công khai của `sidecar_client` mà tệp này phải kiểm kê.

    Bỏ qua tiện ích chung (`san_sang`, `song`, `trang_thai`) — chúng không phải
    một cửa của sidecar, chúng là phép dò sức khoẻ.
    """
    bo_qua = {"san_sang", "song", "trang_thai"}
    cay = ast.parse((GOC / "apps/ltt_voice/sidecar_client.py").read_text(
        encoding="utf-8"))
    return {n.name for n in cay.body
            if isinstance(n, ast.FunctionDef)
            and not n.name.startswith("_")
            and n.name not in bo_qua}


def test_kiem_ke_phu_HET_va_khong_thua():
    """Thêm một cửa mới mà quên kiểm kê ⇒ đỏ ngay, không im lặng trôi vào kho."""
    that = _ham_cong_khai()
    assert that == set(KIEM_KE), (
        f"thieu trong KIEM_KE: {sorted(that - set(KIEM_KE))} · "
        f"thua trong KIEM_KE: {sorted(set(KIEM_KE) - that)}")


@pytest.mark.parametrize("ten", sorted(k for k, v in KIEM_KE.items()
                                       if v == "san_pham"))
def test_cua_khai_SAN_PHAM_that_su_co_nguoi_goi(ten):
    goi = _dem_nguoi_goi(ten, DUONG_SAN_PHAM)
    assert goi, (f"`{ten}` khai la 'san_pham' nhung KHONG noi nao trong "
                 f"{DUONG_SAN_PHAM} goi no — hoac sua ma, hoac sua KIEM_KE")


@pytest.mark.parametrize("ten", sorted(k for k, v in KIEM_KE.items()
                                       if v != "san_pham"))
def test_cua_khai_CHUA_NOI_thi_dung_la_chua_noi(ten):
    """⛔ ĐỐI CHỨNG NGƯỢC — và nó là nửa quan trọng hơn.

    Không có nó thì bảng kiểm kê chỉ chốt được một chiều: một cửa **được nối
    vào** sản phẩm mà bảng vẫn ghi "chưa nối" sẽ xanh mãi mãi, và bản kiểm kê
    trở thành đúng thứ nó sinh ra để thay — một bảng chép tay nói sai một cách
    rất tự tin.
    """
    goi = _dem_nguoi_goi(ten, DUONG_SAN_PHAM)
    assert not goi, (f"`{ten}` khai la '{KIEM_KE[ten]}' nhung DA duoc goi o "
                     f"{goi} — cap nhat KIEM_KE thanh 'san_pham'")


def test_stream_van_chua_co_client_va_dieu_do_duoc_GHI_RA():
    """`/v1/stream` có ở sidecar, **không** có hàm bọc ở app.

    ⚠️ Đây không phải một lời phàn nàn — streaming là việc của P3. Phép kiểm
       này chỉ giữ cho sự thật ấy không trôi: ngày ai đó thêm client, họ phải
       xoá phép kiểm này, và xoá nó là một hành động người review nhìn thấy.
    """
    sc = (GOC / "apps/ltt_voice/sidecar_client.py").read_text(encoding="utf-8")
    sv = (GOC / "voice_sidecar/server.py").read_text(encoding="utf-8")
    assert "/v1/stream" in sv, "sidecar khong con cua /v1/stream?"
    assert "/v1/stream" not in sc, (
        "sidecar_client da co client cho /v1/stream — go phep kiem nay va "
        "cap nhat KIEM_KE + docs/LTT_VOICE")


def test_moi_cua_deu_co_TRAN_THOI_GIAN():
    """Nhắc lại chốt của `test_501` cho MỌI cửa trong kiểm kê, kể cả cửa mới.

    ⛔ `test_501` liệt kê tên bằng tay; danh sách ấy không tự lớn lên khi thêm
       cửa. Ở đây danh sách đến từ chính `KIEM_KE`, vốn đã được chốt là đầy đủ.
    """
    import inspect
    for ten in KIEM_KE:
        assert "timeout" in inspect.getsource(getattr(sidecar_client, ten)), \
            f"sidecar_client.{ten} khong dat timeout"
