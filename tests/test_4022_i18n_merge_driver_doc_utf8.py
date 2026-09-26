"""Trình gộp `.po` phải đọc đầu ra của `git` bằng **UTF-8 tường minh**.

## Ca thật 26/09/2026 — và nó hỏng theo kiểu tệ nhất

`tools/i18n_merge_driver.py` sinh ra để ⛔ không ai phải giải xung đột `.po`/`.mo`
bằng tay. Nhưng `_git()` gọi `subprocess.run(..., text=True)` **⛔ không kèm
`encoding=`**, nên trên Windows Python giải mã theo locale (`cp1252`), còn `.po`
của kho là UTF-8 có tiếng Việt.

⛔ Và nó **⛔ không ném ra ngoài**. `UnicodeDecodeError` xảy ra trong luồng đọc của
`subprocess`, bị nuốt, và `run()` trả về:

    returncode = 0        <- "thành công"
    stdout     = None     <- không có gì

⇒ Người gọi đi tiếp, rồi chết ở `r.stdout.encode(...)` cách đó 50 dòng với
  `AttributeError: 'NoneType' object has no attribute 'encode'` — một thông báo
  ⛔ **không hề chỉ về nguyên nhân**.

## Cái giá đã trả, đo được

Trình gộp chết ⇒ một phiên phải giải `.po` bằng tay ⇒ lượt giải ấy xoá ba dòng
marker của git mà ⛔ không trả lại **dòng trống** mà marker đã thế chỗ. Trong định
dạng PO, dòng trống ⛔ không phải khoảng trắng trang trí — nó là **dấu chấm câu**
ngăn hai mục. Ba mục dính liền ⇒ ba chuỗi thành "chưa dịch" dù `msgstr` nằm ngay
dưới (`59d7e296`).

⭐ Khuôn đáng nhớ: **một công cụ chết lặng đắt hơn một công cụ chưa từng có** —
   vì người ta tin là nó đang chạy.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

TEP = Path("tools/i18n_merge_driver.py")


def test_git_doc_duoc_po_co_tieng_viet():
    """Phép đo THẬT: đọc chính `.po` của kho qua `_git`, kiểm nó ra chữ.

    ⛔ Đừng chỉ kiểm rằng mã có chữ `encoding` — đó là kiểm **cách gõ**. Ở đây
    hỏi đúng câu mà trình gộp hỏi lúc chạy.
    """
    import tools.i18n_merge_driver as drv

    r = drv._git("show", "HEAD:locale/en/LC_MESSAGES/messages.po")
    assert r.returncode == 0, r.stderr
    assert r.stdout is not None, (
        "git tra 0 nhung stdout=None — dung ca loi giai ma bi nuot")
    assert len(r.stdout) > 1000
    assert "msgid" in r.stdout


def test_khong_con_text_True_thieu_encoding():
    """Bánh cóc theo TÍNH CHẤT: mọi `subprocess.run(text=True)` trong tệp này
    phải khai `encoding`. Một chỗ sót là một lần chết lặng nữa."""
    cay = ast.parse(TEP.read_text(encoding="utf-8"))
    thieu = []
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        if getattr(n.func, "attr", "") != "run":
            continue
        ten_kw = {kw.arg for kw in n.keywords}
        co_text = any(kw.arg == "text" and getattr(kw.value, "value", None) is True
                      for kw in n.keywords)
        if co_text and "encoding" not in ten_kw:
            thieu.append(n.lineno)
    assert not thieu, f"subprocess.run(text=True) thieu encoding o dong {thieu}"


def test_stdout_None_bi_chan_TAI_CHO_chu_khong_de_thanh_AttributeError():
    """`returncode == 0` mà `stdout is None` là một trạng thái THẬT đã xảy ra.

    ⛔ Đây ⛔ không phải mã phòng thủ cho một ca tưởng tượng — nó là cái đã cắn,
    và cái giá của việc ⛔ không chặn là một `AttributeError` cách xa nguyên nhân
    50 dòng.
    """
    cay = ast.parse(TEP.read_text(encoding="utf-8"))

    def _mo_ta(n) -> str:
        return ast.dump(n)

    dung = [n for n in ast.walk(cay)
            if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == "encode"
            and "stdout" in _mo_ta(n.func)]
    assert dung, "khong con cho nao goi .stdout.encode() — bai nay da lac de"
    chan = [n for n in ast.walk(cay)
            if isinstance(n, ast.If) and "stdout" in _mo_ta(n.test)
            and "None" in _mo_ta(n.test)]
    assert chan, "khong co phep chan `stdout is None` nao"
    # ⛔ Doc AST chu khong `nguon.index(...)`: ban dau toi so vi tri CHUOI, va
    #    no khop nham mot dong VAN XUOI trong docstring — mot phep do tra loi
    #    ve van ban chu khong ve ma.
    assert min(n.lineno for n in chan) < max(n.lineno for n in dung), (
        "phep chan phai dung TRUOC cho dung stdout")


def test_po_cua_kho_van_PHAN_GIAI_duoc_bang_parser_that():
    """Phép đo rẻ nhất bắt được lỗi mất dòng trống — dùng cho mọi lượt merge sau.

    ⛔ Đừng đọc `.mo` để trả lời câu này: `msgfmt` dễ dãi hơn parser PO, nên một
    `.po` đã hỏng cấu trúc vẫn cho ra `.mo` dịch được. Hai kênh trả lời hai câu
    khác nhau.
    """
    from babel.messages.pofile import read_po

    with Path("locale/en/LC_MESSAGES/messages.po").open(encoding="utf-8") as f:
        cat = read_po(f)
    chua_dich = [m for m in cat if m.id and not m.string]
    assert len(cat) > 5000, f"catalog chi con {len(cat)} muc — nghi bi cat"
    assert len(chua_dich) <= 200, (
        f"{len(chua_dich)} muc chua dich (nen cu: 200) — mot luot merge co the "
        f"vua lam dinh hai muc vao nhau")


def test_driver_van_duoc_khai_lam_merge_driver():
    """Công cụ chỉ có giá trị nếu git **gọi** nó. Chốt cả chỗ nối."""
    # ⚠️ Khoa la `merge.ltt_mo.driver` — dung ten `.gitattributes` tro toi
    #    (`locale/**/*.mo merge=ltt_mo`), ⛔ khong phai mot ten tu dat. Ban dau
    #    toi doan `merge.i18n-mo` va bai nay **skip** thay vi do: mot phep kiem
    #    hoi sai khoa thi im lang, va im lang doc len giong "khong sao".
    ten = Path(".gitattributes").read_text(encoding="utf-8")
    assert "locale/**/*.mo merge=ltt_mo" in ten, (
        ".gitattributes khong con tro .mo vao driver")
    r = subprocess.run(["git", "config", "--get", "merge.ltt_mo.driver"],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=30)
    if r.returncode != 0 or not (r.stdout or "").strip():
        import pytest

        pytest.skip("kho nay chua cai merge driver: "
                    "`python tools/i18n_merge_driver.py cai-dat`")
    assert "i18n_merge_driver" in r.stdout
