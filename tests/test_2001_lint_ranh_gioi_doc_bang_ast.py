"""`lint_app_contract` phải đọc import bằng AST, không bằng regex.

🔴 **Vì sao tệp này tồn tại.** Bản regex cũ khớp `^from apps... import (.+)$` rồi
   `split(",")`. Hai hậu quả, cả hai lộ ra ngày 23/09:

   · `from x import (A, B, C)` trên MỘT dòng ⇒ ba tên `"(A"`, `"B"`, `"C)"`.
     Hai báo động giả cho một dòng hoàn toàn hợp lệ (`ho_so_noi_dung.py`).
   · `from x import (` rồi xuống dòng ⇒ **không khớp dòng nào**, nên cả khối
     import đó **vô hình** với phép kiểm ranh giới.

⛔ Cái thứ hai mới nguy: một công cụ CƯỠNG CHẾ im lặng cho qua thì tệ hơn một
   công cụ báo bừa. Kho này đã có sẵn import nhiều dòng (`project_render.py`,
   `calibration.py`), nên lỗ hổng không phải giả định.

⭐ Phép kiểm chạy linter trên một CÂY GIẢ — không đụng kho thật, nên nó không đổi
   kết quả khi hôm nay app nào đó vi phạm thêm hay bớt.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]

_MANIFEST = 'MANIFEST = type("M", (), {{"slug": "{slug}"}})\nslug = "{slug}"\n'


@pytest.fixture()
def lint():
    spec = importlib.util.spec_from_file_location(
        "_lint_rg", GOC / "tools" / "lint_app_contract.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["_lint_rg"] = m
    spec.loader.exec_module(m)
    return m


def _dung_cay(tmp_path: Path, than: str) -> Path:
    apps = tmp_path / "apps"
    for slug in ("thu_a", "ltt_voice"):
        d = apps / slug
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("", encoding="utf-8")
        (d / "manifest.py").write_text(_MANIFEST.format(slug=slug), encoding="utf-8")
    (apps / "thu_a" / "mod.py").write_text(than, encoding="utf-8")
    return apps


def _loi_ruot(lint, tmp_path, than: str, cho_phep: set) -> list[str]:
    lint.APPS = _dung_cay(tmp_path, than)
    lint.APP_DUOC_DUNG_APP[("thu_a", "ltt_voice")] = cho_phep
    try:
        return [f.msg for f in lint.lint()
                if f.app == "thu_a" and f.level == "ERROR"
                and "ruot app khac" in f.msg]
    finally:
        lint.APP_DUOC_DUNG_APP.pop(("thu_a", "ltt_voice"), None)


CHO_PHEP = {("apps.ltt_voice.giong_mau", "NHAN_GIOI"),
            ("apps.ltt_voice.giong_mau", "NHAN_VUNG")}


def test_import_MOT_dong_co_ngoac_KHONG_con_bao_dong_gia(lint, tmp_path):
    """Hai tên ĐỀU nằm trong bề mặt ⇒ không được có lỗi nào.

    Bản regex cũ đọc ra `"(NHAN_GIOI"` và `"NHAN_VUNG)"` — hai báo động giả.
    """
    than = "from apps.ltt_voice.giong_mau import (NHAN_GIOI, NHAN_VUNG)\n"
    assert _loi_ruot(lint, tmp_path, than, CHO_PHEP) == []


def test_import_NHIEU_dong_van_bi_SOI(lint, tmp_path):
    """🔴 Đối chứng của cả tệp: bản regex cũ **không thấy** khối này."""
    than = ("from apps.ltt_voice.giong_mau import (\n"
            "    NHAN_GIOI,\n"
            "    _chua_bao_gio_duoc_khai,\n"
            ")\n")
    loi = _loi_ruot(lint, tmp_path, than, CHO_PHEP)
    assert any("_chua_bao_gio_duoc_khai" in d for d in loi), \
        f"import nhieu dong khong bi soi: {loi}"
    # ⚠️ Hoi dung cau: thong bao loi co LIET KE ca be mat cho phep, nen ten hop
    #    le xuat hien trong van ban ma khong phai la mot cao buoc. Chot theo cum
    #    "import <ten>" — thu chi co o ten BI to.
    assert not any("import 'NHAN_GIOI'" in d for d in loi), "bat nham ten DA duoc khai"


def test_van_bat_vi_pham_THUONG(lint, tmp_path):
    """Đối chứng ngược: một tên ngoài bề mặt, import một dòng, vẫn phải đỏ."""
    than = "from apps.ltt_voice.giong_mau import DANH_SACH\n"
    assert any("DANH_SACH" in d for d in _loi_ruot(lint, tmp_path, than, CHO_PHEP))


def test_bo_doc_KHONG_con_dung_regex_cho_import_apps(lint):
    """Chốt cơ học: không còn regex `from apps...` trong bộ quét."""
    van = (GOC / "tools" / "lint_app_contract.py").read_text(encoding="utf-8")
    assert "ast.ImportFrom" in van, "khong thay doc bang AST"
    assert r'r"^\s*from\s+(apps\.' not in van, "van con regex doc import apps"
