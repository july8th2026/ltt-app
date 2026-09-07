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
TEN_TIM_TAI_LIEU = "noi_bo.tim_tai_lieu"
TEN_GHI_NHO = "noi_bo.ghi_nho"

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
def _h_thoi_gian(db, user_id, doi_so, _boi_canh=None):   # noqa: ARG001
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
def _h_tinh(db, user_id, doi_so, _boi_canh=None):        # noqa: ARG001
    bt = str(doi_so.get("bieu_thuc") or "")
    return {"bieu_thuc": bt, "ket_qua": tinh_bieu_thuc(bt)}


class ThieuPhamVi(RuntimeError):
    """Thiếu `conversation_id` trong bối cảnh ⇒ KHÔNG tìm. Fail-closed."""


@thi_hanh.dang_ky(TEN_TIM_TAI_LIEU)
def _h_tim_tai_lieu(db, user_id, doi_so, boi_canh=None):
    """Tìm trong tài liệu người dùng đã đính vào **hội thoại này**. (P06 bước 6)

    ## 🔴 Phạm vi đến từ BỐI CẢNH, không từ đối số

    `conversation_id` **không** nằm trong schema gửi cho model, nên model không
    nhìn thấy lẫn không đặt được. Nếu nó là một đối số, model đọc được id hội
    thoại khác từ chính lịch sử trò chuyện và tool thành đường đọc chéo.

    ⛔ Thiếu bối cảnh thì **ném**, không tìm toàn tài khoản. Một tool mất phạm
       vi mà vẫn trả kết quả là một rò rỉ trông như một tính năng.

    ## Vì sao READ_ONLY dù tài liệu là thứ đã trả tiền

    Trích đã thu tiền một lần (`chatltt.trich_tep`). Tìm trong đoạn đã trích chỉ
    là một truy vấn CSDL trên dữ liệu của chính người hỏi — thu lần hai cho cùng
    một tài liệu là tính tiền hai lần cho một việc.
    """
    from apps.chatltt.services import tim_doan

    conv = str((boi_canh or {}).get("conversation_id") or "")
    if not conv:
        raise ThieuPhamVi(
            "thieu pham vi hoi thoai — khong tim de tranh doc cheo hoi thoai")
    hoi = str(doi_so.get("cau_hoi") or "").strip()
    if not hoi:
        raise BieuThucSai("`cau_hoi` khong duoc rong")
    try:
        so = int(doi_so.get("so_doan") or tim_doan.SO_DOAN_MAC_DINH)
    except (TypeError, ValueError):
        so = tim_doan.SO_DOAN_MAC_DINH
    return tim_doan.cho_tool(db, user_id=str(user_id), conversation_id=conv,
                             cau_hoi=hoi, so_doan=so)


@thi_hanh.dang_ky(TEN_GHI_NHO)
def _h_ghi_nho(db, user_id, doi_so, boi_canh=None):
    """Ghi một điều đáng nhớ về người dùng. (H44 B4 bước 5)

    ## 🔴 Vì sao model chỉ có MỘT tool ghi nhớ, không có `quen` và `thay`

    Kế hoạch B4 §D4 định cho model cả `noi_bo.quen` (lớp `DESTRUCTIVE`). Viết
    tới đây thì lộ ra một điều kế hoạch không thấy: **model không có địa chỉ để
    gọi**. Khối ghi nhớ tiêm vào ngữ cảnh chỉ có *chữ*, không có `id` — cố ý,
    vì `id` tốn token mỗi lượt. Không có `id` thì không `quen` được, cũng không
    `thay` được.

    ⇒ Hai đường sửa, và cả hai đều là quyết định **chưa tới lúc**:
      1. tiêm `id` vào ngữ cảnh — đổi một thứ đang tối giản, chỉ để phục vụ một
         tool chưa mở;
      2. `quen` theo **nội dung** thay vì theo `id` — địa chỉ hoá bằng chữ, cần
         một phép so khớp mà chưa có phép đo nào nói ta cần.

    ⭐ Nên `thay`/`quen` ở lại phía **người dùng** (route bước 4). Đó không phải
       một thiếu sót: bài toán B4 tự nói là *"quyền và giao diện"*, còn bốn phép
       của mem0 được mượn làm **đặc tả cho KHO** — ai được gọi phép nào là một
       câu hỏi khác, và nó được trả lời riêng.

    ## Địa chỉ từ bối cảnh, ĐỘ BỀN từ model, TRẦN từ bên gọi

    `user_id`/`conversation_id` **không** nằm trong schema gửi cho model. Thứ
    model nêu được là `lau_dai` — một lựa chọn sản phẩm — và bên gọi đặt trần
    cho nó bằng `boi_canh["cho_phep_ghi_nho_lau_dai"]`.
    """
    from apps.chatltt.services import ghi_nho as GN

    bc = boi_canh or {}
    conv = str(bc.get("conversation_id") or "")
    if not conv:
        raise ThieuPhamVi(
            "thieu pham vi hoi thoai — khong ghi de tranh ghi cheo hoi thoai")
    van = str(doi_so.get("noi_dung") or "").strip()
    if not van:
        raise BieuThucSai("`noi_dung` khong duoc rong")

    mau, trang_thai = GN.ghi_boi_model(
        db, user_id=str(user_id), conv_id=conv, noi_dung=van,
        lau_dai=bool(doi_so.get("lau_dai")),
        cho_phep_lau_dai=bool(bc.get("cho_phep_ghi_nho_lau_dai")))
    # ⭐ Tra ve `pham_vi` THAT, khong tra ve thu model xin. Bi ha tran ma van
    #    bao "da nho lau dai" se khien model khang dinh voi khach mot dieu sai.
    return {"da_ghi": True, "pham_vi": mau.pham_vi,
            "trang_thai": trang_thai, "noi_dung": mau.noi_dung}


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
    {"type": "function", "function": {
        "name": TEN_TIM_TAI_LIEU,
        # ⭐ Cau quan trong nhat la cau noi KHI NAO dung, khong phai cau noi no
        #    lam gi — P01 nhom N3 do duoc model chon tool rat sat mo ta.
        "description": ("Tim trong cac tai lieu nguoi dung da dinh vao hoi "
                        "thoai NAY. Dung MOI KHI cau hoi nhac den 'tai lieu', "
                        "'file', 'ban bao cao', 'hop dong' da gui, hoac hoi mot "
                        "chi tiet ma ban khong the biet neu khong doc tai lieu "
                        "cua ho. Ket qua kem so trang de ban TRICH DAN lai."),
        "parameters": {"type": "object",
                       "properties": {
                           "cau_hoi": {"type": "string"},
                           "so_doan": {"type": "integer"}},
                       "required": ["cau_hoi"]}}},
    {"type": "function", "function": {
        "name": TEN_GHI_NHO,
        # ⛔ Cau "CHI dung khi..." quan trong hon ca cau mo ta. P01 do duoc model
        #    goi tool rat sat mo ta — mot mo ta rong se bien moi loi tam su
        #    thanh mot mau ghi nho, va kho day sau ba cuoc tro chuyen.
        "description": ("Ghi nho mot dieu ve nguoi dung de dung o cac lan sau. "
                        "CHI dung khi ho noi mot dieu ON DINH ve ban than "
                        "(ten, nghe, so thich lau dai, cach ho muon duoc tra "
                        "loi). KHONG dung cho thong tin chi dung trong cau "
                        "chuyen hom nay, va KHONG dung de ghi lai cau hoi cua "
                        "ho. Dat `lau_dai` = true khi dieu do dung o MOI cuoc "
                        "tro chuyen, false khi no chi dung o cuoc nay."),
        "parameters": {"type": "object",
                       "properties": {
                           "noi_dung": {"type": "string"},
                           "lau_dai": {"type": "boolean"}},
                       "required": ["noi_dung"]}}},
)

#: Tên → lớp chính sách, để `chieu_tool.LOP_CUA` nạp vào.
#:
#: ⚠️ `TEN_GHI_NHO` là `FREE`, **không** `READ_ONLY`: nó ghi. Và không
#:    `DESTRUCTIVE`: nó không xoá gì, không tốn credit, dữ liệu là của chính
#:    người hỏi, và người dùng sửa/xoá lại được ở giao diện.
#:
#: 🔴 Nhưng *"sửa lại được"* chỉ đúng **nếu người dùng nhìn thấy nó đã xảy ra**.
#:    Khối `tool_call` hiện **chưa được vẽ** (đo ở P09). ⇒ Đó là lý do
#:    `TEN_GHI_NHO` **không** có mặt trong `chieu_tool.CHO_MODEL_GOI`: cửa thứ
#:    tư mở sau P09, không phải bây giờ.
LOP: dict = {TEN_THOI_GIAN: "READ_ONLY", TEN_TINH: "READ_ONLY",
             TEN_TIM_TAI_LIEU: "READ_ONLY", TEN_GHI_NHO: "FREE"}


def khoi_cho(user_id: str = "") -> list:      # noqa: ARG001 — chỗ móc về sau
    """Khối tool nội bộ. Nhận `user_id` để sau này bật/tắt theo người dùng."""
    return [dict(t) for t in KHOI]


__all__ = ["KHOI", "LOP", "khoi_cho", "tinh_bieu_thuc", "BieuThucSai",
           "TEN_THOI_GIAN", "TEN_TINH", "TRAN_SO_MU", "MUI_GIO"]
