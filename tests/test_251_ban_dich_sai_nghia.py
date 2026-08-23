"""Vài nhãn mà dịch sai thì khách tin theo — chốt lại từng cái.

Vì sao có file này: `i18n.py trich` để Babel tự gán bản dịch cũ cho msgid mới khi
chúng "trông giống nhau", rồi đánh dấu `#, fuzzy`. gettext bỏ qua mục fuzzy, nên
sai sót nằm im — cho tới khi ai đó chạy `msgattrib --clear-fuzzy` để dọn cho sạch
và **bật nguyên 200 bản đoán bừa** lên production cùng một lúc.

Rà 2026-08-23 tìm thấy 47 mục sai. Ba mục dưới đây là loại tệ nhất, vì chúng
không phải "dịch vụng" mà là **nói ngược sự thật** ở chỗ khách dựa vào:

    "Bắt buộc"   ->  "Optional"     trường BẮT BUỘC ghi thành TUỲ CHỌN
    "đang khỏe"  ->  "Pending"      trạng thái KHOẺ ghi thành ĐANG CHỜ
    "đang tắt"   ->  "Finishing"    trạng thái TẮT ghi thành ĐANG HOÀN TẤT

Test này không rà cả bộ dịch — `tools/check_fuzzy_dich.py` làm việc đó. Nó chỉ
giữ chặt mấy chuỗi mà sai một chữ là đổi nghĩa.
"""
from __future__ import annotations

import gettext
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
LOCALE = GOC / "locale"


@pytest.fixture(scope="module")
def en():
    return gettext.translation("messages", str(LOCALE), languages=["en"])


#: (chuỗi gốc, bản dịch đúng, bản Babel từng đoán sai)
CHOT = [
    ("Bắt buộc", "Required", "Optional"),
    ("đang khỏe", "healthy", "Pending"),
    ("đang tắt", "down", "Finishing"),
    ("chỉ đọc", "read-only", "Topic"),
    ("Định danh", "Identifier", "Fast"),
    ("Chiều rộng", "Width", "Motion"),
    ("Môi trường", "Environment", "Audience"),
    ("Lấy mẫu", "Sampling", "Templates"),
    ("Tên gợi nhớ", "Label", "Username"),
    ("ỨNG VIÊN", "CANDIDATE", "Member"),
]


@pytest.mark.parametrize("goc,dung,tung_sai", CHOT)
def test_nhan_quan_trong_dich_dung(en, goc, dung, tung_sai):
    ra = en.gettext(goc)
    assert ra != tung_sai, (
        f"{goc!r} lai dich thanh {tung_sai!r} — day la ban doan cua Babel, "
        "co le ai do vua go co fuzzy hang loat"
    )
    assert ra == dung, f"{goc!r} -> {ra!r}, mong doi {dung!r}"


def test_khong_con_muc_fuzzy_nao_dang_ngo():
    """Bánh cóc: rà lại bằng chính công cụ đã dùng để tìm ra 47 mục sai.

    Không cấm mục `#, fuzzy` — còn 163 mục và chúng vô hại khi còn cờ. Chỉ cấm
    thứ trông như **gán nhầm sang msgid khác**, vì đó là loại sinh ra
    "Bắt buộc → Optional".
    """
    import sys

    sys.path.insert(0, str(GOC / "tools"))
    import check_fuzzy_dich as ct

    ngo = [(r, g, s) for f, r, g, s in ct.doc_muc(ct.PO)
           if f and g and ct.dang_ngo(g, s)]
    assert not ngo, "muc fuzzy dang ngo:\n" + "\n".join(
        f"  {r}\n    goc : {g}\n    dich: {s}" for r, g, s in ngo[:10])
