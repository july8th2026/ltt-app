"""
test_1232 — trọng tài cư trú 3090 **thật sự được gọi**, và job ảnh mang lớp `nen`.

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Task 5.5 xây `residency.buoc()` + `buoc_dinh_ky()` và
   `tests/test_1219` chứng minh máy trạng thái chạy đúng. Nhưng "chạy đúng khi
   được gọi" và "có ai gọi" là **hai mệnh đề khác nhau**, và kho này đã trả giá
   cho đúng khoảng cách ấy một lần rồi (memory `nang-luc-co-nhung-khong-ai-di-tren-duong`:
   năng lực có, đường không ai đi, mọi phép kiểm vẫn xanh).

⛔ Hậu quả nếu hai dây này rụng — và nó **im lặng**:

     không ai gọi `buoc_dinh_ky`
       ⇒ không ai tạo dòng `gpu_residency`
       ⇒ luật 0 `CHO_RESIDENCY` fail-closed ⇒ **mọi lượt `ltt-3.8` chờ hết ngân
         sách rồi 429**, và job ảnh cũng không bao giờ được mở cửa.

   Cả hai cánh cùng đóng, `ltt-3.5` vẫn sống (khác card, không khai
   `residency_group`), nên triệu chứng nhìn như *"3.8 bận mãi"* — một câu trỏ sai
   hướng hoàn toàn. Đó là R27.

⭐ Hai tầng, cố ý: một phép kiểm **hành vi** (gọi hàm thật, đếm) và một **bánh
   cóc AST** (dòng còn nằm đúng chỗ). Tầng hành vi bắt được "gọi nhưng sai điều
   kiện"; tầng AST bắt được "ai đó bọc nó trong một `if` không bao giờ đúng".
"""
from __future__ import annotations

import ast
import pathlib
from types import SimpleNamespace

import pytest

from platform_core import job_runner

GOC = pathlib.Path(__file__).resolve().parents[1]
NGUON = GOC / "platform_core" / "job_runner.py"


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Hành vi: một lượt bảo trì gọi trọng tài đúng MỘT lần
# ══════════════════════════════════════════════════════════════════════════════

def test_mot_luot_bao_tri_GOI_trong_tai(monkeypatch):
    """Gọi hàm thật, đếm — không đọc mã nguồn."""
    from platform_core.llm import residency

    dem = {"n": 0}
    monkeypatch.setattr(residency, "buoc_dinh_ky",
                        lambda *a, **k: dem.__setitem__("n", dem["n"] + 1))

    # Mọi việc nền khác chưa tới hạn ⇒ lượt này chỉ còn đúng trọng tài.
    import time as _t
    xa = _t.monotonic() + 10_000.0
    job_runner._mot_luot_bao_tri({k: xa for k in _KHOA_MOC()})

    assert dem["n"] == 1, "vong bao tri KHONG goi trong tai cu tru"


def _KHOA_MOC() -> set:
    """Mọi khoá `moc[...]` mà `_mot_luot_bao_tri` đọc — lấy từ AST, không gõ tay.

    ⚠️ Gõ tay danh sách khoá ở đây là dựng một bản sao thứ hai của một thứ đang
       đổi: thêm một việc nền mới là tệp này `KeyError` vì một lý do không liên
       quan gì tới điều nó đo.
    """
    cay = ast.parse(NGUON.read_bytes())
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_mot_luot_bao_tri")
    return {n.slice.value for n in ast.walk(ham)
            if isinstance(n, ast.Subscript)
            and isinstance(n.value, ast.Name) and n.value.id == "moc"
            and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)}


def test_DOI_CHUNG_bo_dem_that_su_dem(monkeypatch):
    """Đối chứng: bộ đếm phải ở **0** khi không ai gọi.

    ⛔ Không có ca này, một `lambda` hỏng (không bao giờ tăng) vẫn làm ca trên
       xanh nếu ta đổi `== 1` thành `>= 0`. Nó chốt rằng phép đo phân biệt được
       "có gọi" với "không gọi".
    """
    from platform_core.llm import residency

    dem = {"n": 0}
    monkeypatch.setattr(residency, "buoc_dinh_ky",
                        lambda *a, **k: dem.__setitem__("n", dem["n"] + 1))
    assert dem["n"] == 0
    residency.buoc_dinh_ky()
    assert dem["n"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Bánh cóc AST: lời gọi nằm ngay trong thân hàm, không nấp sau một `if`
# ══════════════════════════════════════════════════════════════════════════════

def _goi_khong_dieu_kien(ten_ham: str, ten_goi: str) -> bool:
    """`ten_goi` có được gọi ở **cấp cao nhất** của `ten_ham` không?"""
    cay = ast.parse(NGUON.read_bytes())
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == ten_ham)
    for lenh in ham.body:                      # chỉ cấp cao nhất, không `walk`
        for nut in ast.walk(lenh):
            if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                    and nut.func.attr == ten_goi):
                return not isinstance(lenh, (ast.If, ast.Try, ast.While, ast.For))
    return False


def test_loi_goi_KHONG_nap_sau_mot_dieu_kien():
    """⛔ Một `if` quanh lời gọi này là một cách tắt trọng tài mà vẫn xanh §1.

    §1 gọi hàm với mọi mốc đẩy ra xa, nên nó **không** phân biệt được "gọi vô
    điều kiện" với "gọi trong một `if` tình cờ đúng ở test". Tầng này phân biệt.
    """
    assert _goi_khong_dieu_kien("_mot_luot_bao_tri", "buoc_dinh_ky"), (
        "`buoc_dinh_ky()` khong con duoc goi vo dieu kien trong `_mot_luot_bao_tri`")


def test_DOI_CHUNG_banh_coc_AST_nhin_thay_su_vang_mat():
    """Đối chứng cho bánh cóc: nó phải trả **False** cho một tên không hề có."""
    assert not _goi_khong_dieu_kien("_mot_luot_bao_tri", "mot_ham_khong_he_ton_tai")


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Job ảnh mang lớp `nen`, và điều kiện là BẢN KHAI chứ không phải tên app
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def tool_gia(monkeypatch):
    monkeypatch.setattr(job_runner, "_tool_cua_job", lambda _t: SimpleNamespace())


def test_job_co_residency_group_thi_mang_lop_NEN(tool_gia):
    """Job ảnh xin suất trên `anh_3090` (`token_pool = 0`) — vẫn phải là lớp nền.

    🔴 Không có dòng này, job **nền** cạnh tranh như một lượt **khách đang ngồi
       đợi**: luật "nền ≤ N−1 và nhường tương tác" thôi bảo vệ đúng thứ nó sinh
       ra để bảo vệ, và một lô ảnh có thể đẩy khách ra khỏi slot.
    """
    from platform_core.llm import luat_nhan

    suc = SimpleNamespace(token_pool=0, residency_group="rtx3090")
    assert job_runner._luat_cho_job("x.y", {}, suc) == {"lop": luat_nhan.NEN}


def test_DOI_CHUNG_job_KHONG_residency_thi_giu_hanh_vi_cu(tool_gia):
    """Chiều ngược — và đây là vế giữ cho thay đổi trên không lan ra cả kho.

    Mọi job không khai `residency_group` phải trả `{}` **y như trước**: tệp này
    thêm một nhánh, không đổi mặc định của 22 app còn lại.
    """
    assert job_runner._luat_cho_job("x.y", {}, SimpleNamespace(token_pool=0)) == {}
    assert job_runner._luat_cho_job("x.y", {}, None) == {}


def test_dieu_kien_la_BAN_KHAI_chu_khong_phai_ten_app():
    """⛔ `platform_core` không được biết app nào tồn tại (`test_147`).

    Chốt bằng chính mã: nhánh mới phải rẽ theo `residency_group`, và không nhắc
    một slug app nào.
    """
    van = NGUON.read_text(encoding="utf-8")
    i = van.index("def _luat_cho_job")
    than = van[i:van.index("\ndef ", i + 10)]
    assert "residency_group" in than
    for slug in ("anhnoibo", "taoanh", "thumbnail"):
        assert slug not in than, f"`_luat_cho_job` nhac ten app {slug!r}"
