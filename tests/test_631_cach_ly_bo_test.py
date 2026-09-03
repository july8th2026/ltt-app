"""
test_631 — HAI bất biến cách ly mà một tệp test có thể phá cho **cả tiến trình**.

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Ngày 03/09 một lượt gate đỏ với **16 phép kiểm** rải
   trên bảy tệp không liên quan gì nhau (112, 122, 157, 172, 220, 305, 606).
   Mọi tệp đều XANH khi chạy một mình. Triệu chứng giống hệt nhau ở mọi chỗ:

       sqlite3.OperationalError: no such table: users

   Giả thuyết đầu — “máy quá tải, hai lượt `pytest -n auto` tranh nhau” — khớp
   *hoàn hảo* với mọi dữ kiện có lúc đó: đỏ khi chạy cả bộ, xanh khi chạy cụm
   nhỏ, và máy thật sự đang bận. Nó sai. Nó ngốn gần một giờ, và nó kết thúc
   cuộc điều tra đúng lúc cuộc điều tra mới bắt đầu.

⭐ Cả hai lỗi thật đều thuộc **một** loại: một tệp test làm hỏng trạng thái toàn
   cục mà mọi tệp SAU nó dựa vào. Loại đó không thể tự lộ ra ở tệp gây lỗi —
   nó chỉ hiện ở nạn nhân, nên ai đọc dấu vết cũng bị dẫn đi sai chỗ.

⇒ Nên chúng phải bị bắt bằng một phép quét TĨNH ở nơi gây ra, chứ không bằng
  cách đọc dấu vết ở nơi chịu hậu quả.
"""
from __future__ import annotations

import ast
import pathlib
import warnings

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
TEP_TEST = sorted((GOC / "tests").glob("test_*.py"))

#: Hai module này SỞ HỮU `Base` và `Base.metadata`. `reload` một trong hai dựng
#: một lớp `Base` mới mang một `MetaData` RỖNG, và mọi `create_all` sau đó tạo
#: **không bảng nào** — im lặng, mã thoát 0, không cảnh báo.
MODULE_KHONG_DUOC_RELOAD = {"platform_core.db", "platform_core.models"}


def _cay(p: pathlib.Path) -> ast.Module:
    # Nen `SyntaxWarning` cua tep BI QUET. Doc ma nguoi khac khong phai ly do
    # de mot phep kiem tu bom 18 canh bao vao moi luot gate.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(p.read_text(encoding="utf-8"), filename=str(p))


def _ten_module_cua_bien(cay: ast.Module) -> dict[str, str]:
    """Bí danh -> tên module, cho `import platform_core.db as dbmod`."""
    ra: dict[str, str] = {}
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            for a in n.names:
                ra[a.asname or a.name.split(".")[0]] = a.name
    return ra


# ── 1. Không `reload` module giữ `Base` ─────────────────────────────────────

def test_khong_tep_test_nao_reload_module_giu_Base():
    """`importlib.reload(platform_core.db)` là một quả mìn hẹn giờ.

    Nó không làm hỏng tệp đặt nó. Nó làm hỏng tệp **kế tiếp** trên cùng worker,
    và tệp kế tiếp thì thay đổi theo số worker — nên cùng một cây cho ra tập
    lỗi khác nhau giữa hai lượt. Đó chính là thứ khiến “máy quá tải” trông
    giống một lời giải thích đúng.
    """
    vi_pham = []
    for p in TEP_TEST:
        cay = _cay(p)
        bi_danh = _ten_module_cua_bien(cay)
        for n in ast.walk(cay):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if ten != "reload" or not n.args:
                continue
            doi = n.args[0]
            goc = doi.id if isinstance(doi, ast.Name) else None
            if goc and bi_danh.get(goc) in MODULE_KHONG_DUOC_RELOAD:
                vi_pham.append(f"{p.name}:{n.lineno} reload({bi_danh[goc]})")
    assert vi_pham == [], (
        "reload module giu `Base` lam moi `create_all` sau do tao ZERO bang:\n  "
        + "\n  ".join(vi_pham)
        + "\n\nDon dep engine bang `reset_engine()`; monkeypatch tu tra bien "
          "moi truong ve. Khong bao gio reload ca module.")


# ── 2. `create_all` phải đứng SAU khi bảng đã đăng ký ───────────────────────

def _goi_create_all(cay: ast.Module) -> list[ast.Call]:
    ra = []
    for n in ast.walk(cay):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "create_all"):
            ra.append(n)
    return ra


def _dong_nap_models(cay: ast.Module) -> list[int]:
    """Dòng của mọi câu lệnh làm `platform_core.models` được nạp."""
    dong = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            if any(a.name == "platform_core.models" for a in n.names):
                dong.append(n.lineno)
        elif isinstance(n, ast.ImportFrom):
            if n.module == "platform_core.models":
                dong.append(n.lineno)
            elif n.module == "platform_core" and any(a.name == "models" for a in n.names):
                dong.append(n.lineno)
    return sorted(dong)


#: Chi nhung tep THUC SU goi `create_all`. Loc o day chu khong `skip` trong
#: than phep kiem: mot `skip` la mot dong "khong canh gi ca" phai giai trinh
#: voi banh coc `check_bo_qua`, va o day no se phai giai trinh **188 lan** cho
#: mot dieu kien chang co gi bat ngo.
TEP_CO_CREATE_ALL = [p for p in TEP_TEST if _goi_create_all(_cay(p))]


@pytest.mark.parametrize("tep", TEP_CO_CREATE_ALL, ids=lambda p: p.name)
def test_create_all_luon_dung_sau_khi_bang_da_dang_ky(tep):
    """`Base.metadata` RỖNG cho tới khi `platform_core.models` được nạp.

    ⛔ `create_all` trên một metadata rỗng KHÔNG ném gì cả — nó tạo đúng không
       bảng nào rồi trả về bình thường. Phép kiểm chết sau đó, ở dòng đầu tiên
       chạm CSDL, với một thông điệp nói về `users` chứ không nói về import.

    ⭐ Ba tệp (112, 174, 90) đã sống như vậy nhiều tháng và **vẫn xanh**, vì
       xdist gửi trọn tệp cho một worker đã chạy tệp khác trước đó — tệp khác
       ấy nạp `models` hộ. Chúng chỉ đỏ khi bị xếp lên ĐẦU một worker. Một phép
       kiểm xanh nhờ hàng xóm thì không phải một phép kiểm xanh.
    """
    cay = _cay(tep)
    goi = _goi_create_all(cay)
    nap = _dong_nap_models(cay)
    dau_tien = min(g.lineno for g in goi)
    assert nap and min(nap) < dau_tien, (
        f"{tep.name}: `create_all` o dong {dau_tien} nhung `platform_core.models` "
        f"{'nap o dong ' + str(min(nap)) if nap else 'KHONG he duoc nap'}. "
        "Metadata rong => create_all tao ZERO bang, im lang.")


# ── 3. Migration không được tắt logger của ứng dụng chủ nhà ─────────────────

def test_alembic_khong_tat_logger_dang_co():
    """`fileConfig(...)` mặc định `disable_existing_loggers=True`.

    ⛔ Và True ở đây nghĩa là: mọi logger **đã** được tạo trước lúc đó bị đặt
       `disabled = True` — vĩnh viễn, không khôi phục, không một dòng cảnh báo.

    🔴 Đo 03/09, và nó là lỗi cách ly **thứ ba** trong cùng một ngày, cùng một
       hình dạng: `test_616` chạy `alembic upgrade` trong tiến trình ⇒ tắt
       `platform_core.job_runner` ⇒ `test_67::test_worker_khong_ghi_bi_mat...`
       đỏ vì `caplog.text` RỖNG. Ba tệp, ba thư mục, không liên quan gì nhau.
       Phép kiểm nạn nhân XANH khi chạy một mình.

    ⭐ Cái giá thật không nằm ở bộ test. Bất kỳ ai nhúng alembic vào một tiến
       trình đang sống — script bảo trì, lệnh quản trị, worker tự migrate — đều
       làm **cả** tiến trình đó câm tiếng từ đó trở đi, và triệu chứng là sự
       vắng mặt của log, thứ không ai đi tìm.
    """
    env = GOC / "alembic" / "env.py"
    cay = _cay(env)
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "fileConfig"]
    assert goi, "alembic/env.py khong con goi fileConfig — cap nhat phep kiem nay"
    for n in goi:
        tu = {k.arg: k.value for k in n.keywords}
        co = tu.get("disable_existing_loggers")
        assert isinstance(co, ast.Constant) and co.value is False, (
            f"alembic/env.py:{n.lineno} goi fileConfig ma khong "
            "`disable_existing_loggers=False`. Mac dinh True se tat vinh vien "
            "moi logger da tao — migration khong duoc quyen lam ung dung chu "
            "nha cam tieng.")
