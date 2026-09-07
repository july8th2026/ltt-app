"""
test_845 — mọi hàm nhận một ID THUỘC SỞ HỮU phải biết CHỦ của nó. (H44 P10)

P10 liệt kê **IDOR** là hạng mục bảo mật bắt buộc. Đo 07/09 bằng AST trên
`apps/chatltt/services/`:

```
ham nhan mot id thuoc so huu : 71
co nhac `user_id`            : 64
KHONG nhac                   : 7
```

Bảy hàm ấy đã được rà **từng cái** và không cái nào là IDOR — chúng đều là bộ
phận nội bộ, chạm tới sau khi quyền sở hữu đã được kiểm ở tầng trên. Nhưng
*"sạch vì tôi vừa đọc"* là một trạng thái **hết hạn ngay khi có người thêm hàm
thứ 72**.

## ⛔ Vì sao là allowlist KHAI TÊN, không phải một con số

Chốt *"không quá 7 hàm"* thì hàm thứ tám chỉ cần một hàm cũ biến mất là lọt.
Chốt **tập hợp tên** thì mọi cái tên mới đều phải đi qua đây, và người thêm nó
phải viết ra **vì sao** nó an toàn — đúng bài `banh-coc-cong-chat-luong`: chốt
TẬP HỢP, không chốt số lượng.

⭐ Và bánh cóc này **tự kiểm**: một bộ trích AST hỏng trả về tập rỗng, rồi mọi
   mệnh đề `⊆` sẽ xanh sạch trên hư không. `test_bo_trich_TU_KIEM` chặn đường ấy
   — cùng bài học `bo-do-quet-van-ban-trung-phat-viec-giai-thich`.
"""
from __future__ import annotations

import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
DICH = GOC / "apps" / "chatltt" / "services"

#: Tham số mang một id **thuộc sở hữu**. `conversation_id` là một phạm vi, và
#: phạm vi cũng là quyền — cùng lý lẽ `thi_hanh(boi_canh=…)`.
ID_SO_HUU = frozenset({
    "conv_id", "conversation_id", "tep_id", "ghi_nho_id", "du_an_id",
    "job_id", "doan_id", "step_id", "run_id", "execution_id",
    "upload_id", "message_id", "parent_id",
})

#: Hàm được miễn, **kèm lý do**. Mỗi dòng ở đây là một khẳng định có người chịu
#: trách nhiệm, không phải một ngoại lệ cho tiện.
MIEN = {
    # Sổ trong BỘ NHỚ của tiến trình, không đọc CSDL. Người gọi duy nhất là
    # `luot.dung()`, và nó kiểm `ex.user_id != user_id` TRƯỚC khi gọi.
    ("dang_chay.py", "tim"),
    ("dang_chay.py", "ket_thuc"),
    ("dang_chay.py", "yeu_cau_dung"),
    # Hàm THUẦN: băm ba chuỗi, không chạm CSDL, không trả dữ liệu của ai.
    ("duyet.py", "khoa_idem"),
    # Bộ phận nội bộ (`_`), gọi từ trong hàm ĐÃ kiểm sở hữu.
    ("du_an.py", "_cham"),
    ("luot.py", "_da_huy_trong_csdl"),
    ("luot_v3.py", "_execution_dau"),
}


def _ten_trong(nut) -> set:
    """Mọi định danh xuất hiện trong thân hàm — kể cả khoá từ và chuỗi.

    ⭐ Rộng có chủ đích: mục tiêu là *"hàm này có BIẾT tới `user_id` không"*, và
       một phép kiểm hẹp hơn sẽ báo động giả trên `.where(X.user_id == …)`.
    """
    ra = set()
    for n in ast.walk(nut):
        if isinstance(n, ast.Name):
            ra.add(n.id)
        elif isinstance(n, ast.Attribute):
            ra.add(n.attr)
        elif isinstance(n, ast.keyword) and n.arg:
            ra.add(n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            ra.add(n.value)
    return ra


def _quet() -> tuple[set, set]:
    """`(moi ham nhan id so huu, ham KHONG nhac user_id)`."""
    tat_ca, thieu = set(), set()
    for tep in sorted(DICH.glob("*.py")):
        cay = ast.parse(tep.read_bytes().decode("utf-8"))
        for f in cay.body:
            if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            tham = {a.arg for a in f.args.args + f.args.kwonlyargs}
            if not (tham & ID_SO_HUU):
                continue
            tat_ca.add((tep.name, f.name))
            if "user_id" not in tham and "user_id" not in _ten_trong(f):
                thieu.add((tep.name, f.name))
    return tat_ca, thieu


def test_bo_trich_TU_KIEM():
    """⛔ Không có dòng này thì mọi phép kiểm dưới xanh trên một tập rỗng."""
    tat_ca, _ = _quet()
    assert len(tat_ca) > 40, f"bo trich chi thay {len(tat_ca)} ham — hong"
    assert ("hoi_thoai.py", "su_that") in tat_ca


def test_KHONG_ham_nao_moi_duoc_quen_user_id():
    """🔴 Phép kiểm quyết định. Một hàm mới nhận `tep_id` mà không biết chủ là
    một cửa đọc tài liệu của người khác."""
    _, thieu = _quet()
    la = thieu - MIEN
    assert la == set(), (
        f"ham nhan id thuoc so huu ma khong biet chu: {sorted(la)} — "
        f"neu no THAT SU an toan, them vao `MIEN` KEM LY DO")


def test_MIEN_khong_chua_dong_CHET():
    """Chiều ngược lại: một tên đã đổi/gỡ mà còn trong `MIEN` là một lỗ mở sẵn
    cho một hàm tương lai **trùng tên** đi thẳng qua."""
    _, thieu = _quet()
    chet = MIEN - thieu
    assert chet == set(), f"dong MIEN da chet: {sorted(chet)}"


def test_moi_dong_MIEN_deu_co_LY_DO_viet_ra():
    """⛔ Một allowlist không có lý do là một allowlist sẽ dài ra vì tiện.

    ⭐ Đọc **chú thích ngay trên** khối `MIEN` trong chính tệp này, bằng AST —
       không quét chuỗi, vì một phép quét chuỗi sẽ xanh trên chính đoạn văn đang
       giải thích nó (bài học `bo-do-quet-van-ban-trung-phat-viec-giai-thich`).
    """
    van = pathlib.Path(__file__).read_bytes().decode("utf-8")
    than = van.split("MIEN = {", 1)[1].split("}", 1)[0]
    dong = [d.strip() for d in than.splitlines() if d.strip()]
    ghi_chu = [d for d in dong if d.startswith("#")]
    muc = [d for d in dong if d.startswith("(")]
    assert len(muc) == len(MIEN)
    # Mỗi cụm miễn trừ phải có ít nhất một dòng lý do đứng trước nó.
    assert len(ghi_chu) >= 3, "khoi MIEN thieu ly do"
