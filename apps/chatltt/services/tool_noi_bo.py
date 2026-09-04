"""
tool_noi_bo.py — hai tool NỘI BỘ của ChatLTT: đồng hồ và máy tính. (H44 P03)

## Vì sao chúng không phải "năng lực nền tảng"

`chieu_tool.chieu()` lấy tool từ `chinh_sach.danh_muc` — sổ **năng lực bán
được** của nền tảng. Hai tool ở đây không bán được: chúng không tốn credit,
không gọi máy B, không ghi gì. Đẩy chúng vào sổ ấy là bắt `platform_core` mang
một khái niệm chỉ ChatLTT cần — đúng thứ `CLAUDE.md` mục *"Thêm app mới"* cấm.

Nên chúng sống ở app, và `chieu()` **hợp nhất** hai nguồn.

## Vì sao chọn đúng hai tool này cho P03

Gói prompt yêu cầu chạy P03 bằng *tool miễn phí* trước. Trong số thứ miễn phí,
hai cái này là hai cái **đo được**: đầu ra tất định, đúng/sai không cãi nhau.

⭐ Và `thoi_gian` không phải đồ chơi. Một LLM **không có đồng hồ** — "hôm nay
là ngày mấy" là câu nó trả lời sai một cách tự tin, thường xuyên, và người dùng
không có cách nào biết. Đây là ca dùng tool có giá trị thật rẻ nhất tồn tại.

## ⛔ `tinh` KHÔNG dùng `eval`

Đối số của tool đến từ **model**, và model đọc nội dung do **người dùng** đưa
vào. Một `eval()` ở đây là thực thi mã tuỳ ý qua hai lớp gián tiếp. Ở đây phân
tích thành AST rồi **duyệt danh sách trắng** từng loại nút; thứ gì không có
trong danh sách thì không chạy — kể cả khi nó vô hại.
"""
from __future__ import annotations

import ast
import operator
from datetime import datetime, timedelta, timezone

from apps.chatltt.services import thi_hanh

TEN_THOI_GIAN = "noi_bo.thoi_gian"
TEN_TINH = "noi_bo.tinh"

#: Múi giờ được phép hỏi. Danh sách ĐÓNG, không nhận offset tuỳ ý — một enum
#: hẹp là thứ `_kiem_schema` cưỡng chế được, còn "+07:00" thì phải tự phân tích.
MUI_GIO = {"vn": 7, "utc": 0}

# ── Máy tính: danh sách trắng ──────────────────────────────────────────────

_PHEP_HAI_NGOI = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_PHEP_MOT_NGOI = {ast.UAdd: operator.pos, ast.USub: operator.neg}

#: 🔴 Trần số mũ. `2 ** 10_000_000` không phải phép tính, nó là một vòng lặp
#:    treo worker vài phút và ăn hết RAM — số nguyên Python không tràn, nó chỉ
#:    **lớn dần**. Đây là đường DoS thật của một máy tính "vô hại", và nó không
#:    cần ai cố ý: model tự sinh ra biểu thức như vậy khi hiểu sai câu hỏi.
TRAN_SO_MU = 4096

#: Trần độ dài biểu thức — chặn cây AST sâu làm `_tinh` đệ quy quá sâu.
TRAN_DAI = 500


class BieuThucSai(ValueError):
    """Biểu thức không nằm trong danh sách trắng, hoặc không tính được."""


def _tinh(nut) -> float:
    if isinstance(nut, ast.Expression):
        return _tinh(nut.body)
    if isinstance(nut, ast.Constant):
        if isinstance(nut.value, bool) or not isinstance(nut.value, (int, float)):
            # `True + 1` là hợp lệ với Python và vô nghĩa với người hỏi.
            raise BieuThucSai(f"chi nhan so, khong nhan {type(nut.value).__name__}")
        return nut.value
    if isinstance(nut, ast.UnaryOp) and type(nut.op) in _PHEP_MOT_NGOI:
        return _PHEP_MOT_NGOI[type(nut.op)](_tinh(nut.operand))
    if isinstance(nut, ast.BinOp) and type(nut.op) in _PHEP_HAI_NGOI:
        trai, phai = _tinh(nut.left), _tinh(nut.right)
        if isinstance(nut.op, ast.Pow) and abs(phai) > TRAN_SO_MU:
            raise BieuThucSai(f"so mu qua lon (toi da {TRAN_SO_MU})")
        return _PHEP_HAI_NGOI[type(nut.op)](trai, phai)
    raise BieuThucSai(f"khong cho phep {type(nut).__name__}")


def tinh_bieu_thuc(bt: str) -> float:
    """Tính một biểu thức số học. Ném `BieuThucSai` nếu ngoài danh sách trắng."""
    bt = str(bt or "").strip()
    if not bt:
        raise BieuThucSai("bieu thuc rong")
    if len(bt) > TRAN_DAI:
        raise BieuThucSai(f"bieu thuc dai hon {TRAN_DAI} ky tu")
    try:
        cay = ast.parse(bt, mode="eval")
    except SyntaxError as e:
        raise BieuThucSai(f"cu phap sai: {e.msg}") from e
    try:
        gt = _tinh(cay)
    except ZeroDivisionError as e:
        raise BieuThucSai("chia cho khong") from e
    except OverflowError as e:
        raise BieuThucSai("ket qua qua lon") from e
    if isinstance(gt, float) and (gt != gt or gt in (float("inf"), float("-inf"))):
        raise BieuThucSai("ket qua khong phai mot so huu han")
    return gt


# ── Handler ────────────────────────────────────────────────────────────────

@thi_hanh.dang_ky(TEN_THOI_GIAN)
def _h_thoi_gian(db, user_id, doi_so):        # noqa: ARG001 — chữ ký cố định
    ten = str(doi_so.get("mui_gio") or "vn").lower()
    lech = MUI_GIO.get(ten)
    if lech is None:
        raise BieuThucSai(f"mui_gio phai la mot trong {sorted(MUI_GIO)}")
    t = datetime.now(timezone.utc) + timedelta(hours=lech)
    return {"mui_gio": ten, "iso": t.strftime("%Y-%m-%dT%H:%M:%S"),
            "ngay": t.strftime("%Y-%m-%d"), "gio": t.strftime("%H:%M"),
            "thu": ["thu hai", "thu ba", "thu tu", "thu nam", "thu sau",
                    "thu bay", "chu nhat"][t.weekday()]}


@thi_hanh.dang_ky(TEN_TINH)
def _h_tinh(db, user_id, doi_so):             # noqa: ARG001
    bt = str(doi_so.get("bieu_thuc") or "")
    return {"bieu_thuc": bt, "ket_qua": tinh_bieu_thuc(bt)}


# ── Khối `tools` gửi cho model ─────────────────────────────────────────────
#
# ⭐ Mô tả viết cho MODEL đọc, không cho người đọc. P01 nhóm N3 cho thấy nó chọn
#    tool rất sát mô tả — nên câu quan trọng nhất là câu nói *khi nào dùng*,
#    không phải câu nói *nó làm gì*.

KHOI: tuple = (
    {"type": "function", "function": {
        "name": TEN_THOI_GIAN,
        "description": ("Lay ngay gio hien tai. Dung tool nay MOI KHI cau hoi "
                        "lien quan den hom nay, bay gio, ngay mai, thu may, "
                        "hoac tuoi/khoang cach thoi gian — ban KHONG co dong ho "
                        "va se doan sai neu tu tra loi."),
        "parameters": {"type": "object",
                       "properties": {"mui_gio": {"type": "string",
                                                  "enum": sorted(MUI_GIO)}},
                       "required": []}}},
    {"type": "function", "function": {
        "name": TEN_TINH,
        "description": ("Tinh mot bieu thuc so hoc (+ - * / // % **). Dung khi "
                        "phep tinh co nhieu hon hai chu so hoac nhieu buoc — "
                        "tinh nham trong dau de sai o chu so cuoi."),
        "parameters": {"type": "object",
                       "properties": {"bieu_thuc": {"type": "string"}},
                       "required": ["bieu_thuc"]}}},
)

#: Tên → lớp chính sách, để `chieu_tool.LOP_CUA` nạp vào.
LOP: dict = {TEN_THOI_GIAN: "READ_ONLY", TEN_TINH: "READ_ONLY"}


def khoi_cho(user_id: str = "") -> list:      # noqa: ARG001 — chỗ móc về sau
    """Khối tool nội bộ. Nhận `user_id` để sau này bật/tắt theo người dùng."""
    return [dict(t) for t in KHOI]


__all__ = ["KHOI", "LOP", "khoi_cho", "tinh_bieu_thuc", "BieuThucSai",
           "TEN_THOI_GIAN", "TEN_TINH", "TRAN_SO_MU", "MUI_GIO"]
