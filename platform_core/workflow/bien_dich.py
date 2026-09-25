"""Biên dịch draft v3 (tài liệu soạn thảo) → đồ thị chuẩn `ltt.workflow/3`.

Spec §4.1: trang chỉ là tab bố cục — gộp MỌI trang; id duy nhất toàn tài liệu;
cạnh không nối khác trang. Plan 01a chỉ nhận node app; `core.*` ở plan 04.
"""
from __future__ import annotations

import ast
import re
from collections import deque
from typing import Any, NamedTuple, Optional

# Gọi qua MÔ-ĐUN (không `from platform_core.workflow.cong_cu import tat_ca`)
# để test monkeypatch được `cong_cu.tat_ca` và thấy bản thay thế ở đây.
from platform_core.workflow import cong_cu as _nguon
from platform_core.workflow.cong_cu import CongCu
from platform_core.workflow.di_tru_m1 import _canh_v3

SCHEMA = "ltt.workflow/3"
_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_CU = re.compile(r"^\$([A-Za-z0-9_\-]{1,64})\.([A-Za-z0-9_\-]{1,64})$")
_THAM_CHIEU = re.compile(
    r"^\{\{\s*nodes\.([A-Za-z0-9_\-]{1,64})\.output\.([A-Za-z0-9_\-]{1,64})\s*\}\}$")
_KIND = frozenset({"DATA", "CONTROL", "ERROR"})
_MAX_CONCURRENCY = 16
_TIMEOUT_MAC_DINH = 21600


class LoiBienDich(ValueError):
    def __init__(self, ma: str, thong_diep: str, node_id: str = ""):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma, self.node_id = ma, node_id


def la_tham_chieu(gia_tri: Any) -> Optional[tuple[str, str]]:
    if isinstance(gia_tri, str):
        m = _THAM_CHIEU.match(gia_tri.strip())
        if m:
            return m.group(1), m.group(2)
    return None


# ── Trích tham chiếu `nodes.<id>…` ra khỏi một biểu thức (spec §6.2) ─────────
#
# 🔴 VÌ SAO TỰ TRÍCH BẰNG `ast` TẠI CHỖ, không nhận hàm trích qua tham số.
#
#    Đây là một **cổng an ninh về tiền**: nó là chỗ duy nhất chặn một đồ thị
#    hứa đọc output chưa tồn tại. Một cổng nhận bộ phân tích từ bên gọi là một
#    cổng mà **bên gọi quên truyền là mở** — và chỗ nó mở ra không ai nhìn.
#    Kho này đã ghi đúng hạng lỗi ấy hai lần: `canh.dang_ky` ném lỗi khi tên
#    điểm cắm sai vì *"một hook gắn vào điểm không tồn tại là một cổng mở mà
#    không ai thấy"*, và `canh.truyen` fail-CLOSED khi hook ngã.
#
#    Giá phải trả là một bộ duyệt AST thứ hai trong kho (cùng `bieu_thuc.py`).
#    Nó rẻ vì hai bộ trả lời **hai câu khác nhau**: `bieu_thuc.py` hỏi *"biểu
#    thức này TÍNH ra gì"*, còn đây hỏi *"biểu thức này ĐỌC của ai"* — câu thứ
#    hai không cần chính sách, không cần bảng hàm, không cần bộ tính. Và nó
#    tách khỏi ba làn đang sửa (`bieu_thuc.py`/`chinh_sach.py`, `noi_suy.py`,
#    `ham_bieu_thuc.py`) nên không có chuyện cổng đổi hành vi vì một làn khác.
#
# ⛔ FAIL-CLOSED ở mọi ngã rẽ: biểu thức không phân tích được, tham chiếu động
#    (`nodes[x]`), hình dạng lạ (`nodes.a.params`) đều **từ chối**. Một tham
#    chiếu mà bộ trích đọc không nổi là một tham chiếu chưa ai kiểm — bỏ qua nó
#    chính là cho nó đi qua.

#: Namespace §6.2 duy nhất mà cổng tổ tiên quan tâm. Các namespace khác
#: (`trigger`, `workflow`, `vars`, `loop`, `run`, `params`) không nói về node
#: nào nên không có gì để kiểm ở đây.
_NS_NODES = "nodes"

#: Ba mặt của một node tổ tiên (§6.2). `output` có cổng; `status`/`error` thì
#: không — chúng tồn tại cho MỌI node, không phải một cổng khai trong
#: NodeDefinition, nên kiểm cổng tồn tại với chúng là kiểm một thứ không có.
MAT_NODE = ("output", "status", "error")
_MAT_NODE = MAT_NODE


class ThamChieu(NamedTuple):
    """Một lượt đọc `nodes.<node>…` trong một biểu thức.

    `cong` rỗng khi `loai` không phải `"output"`.
    """

    node: str
    cong: str
    loai: str


def doan_bieu_thuc(chuoi: str) -> tuple[str, ...]:
    """Các đoạn `{{ … }}` trong một chuỗi, theo cú pháp §6.1.

    `\\{{` là chữ thường — bỏ qua, không phải biểu thức.

    ⚠️ Đây là bộ quét **tối thiểu** để cổng tổ tiên đọc được tham chiếu, KHÔNG
       phải bộ nội suy của §6.1 (Task 2, `noi_suy.py`): nó không nối chuỗi,
       không `to_string`, không giữ kiểu. Ngày `noi_suy.py` có mặt, chỗ này nên
       gọi sang đó — một nguồn luật, không hai.
    """
    ra: list[str] = []
    i, n = 0, len(chuoi)
    while i < n:
        if chuoi.startswith("\\{{", i):
            i += 3
            continue
        if chuoi.startswith("{{", i):
            j = chuoi.find("}}", i + 2)
            if j < 0:
                raise LoiBienDich(
                    "bieu_thuc_chua_ho_tro",
                    f"`{{{{` khong duoc dong: {chuoi[:200]!r}")
            ra.append(chuoi[i + 2:j].strip())
            i = j + 2
            continue
        i += 1
    return tuple(ra)


def _chuoi_doan(nut: ast.AST) -> Optional[list[str]]:
    """Chuỗi truy cập TĨNH của một biểu thức, hoặc `None` nếu có đoạn động.

    `nodes.a.output["text"][0]` → `["nodes", "a", "output", "text", "0"]`.
    """
    if isinstance(nut, ast.Name):
        return [nut.id]
    if isinstance(nut, ast.Attribute):
        goc = _chuoi_doan(nut.value)
        return None if goc is None else goc + [nut.attr]
    if isinstance(nut, ast.Subscript):
        goc = _chuoi_doan(nut.value)
        if goc is None:
            return None
        khoa = nut.slice
        if isinstance(khoa, ast.Constant) and isinstance(khoa.value, (str, int)) \
                and not isinstance(khoa.value, bool):
            return goc + [str(khoa.value)]
        return None
    return None


def _goc_la_nodes(nut: ast.AST) -> bool:
    """Chuỗi truy cập này có mọc từ `nodes` không, kể cả khi có đoạn động?"""
    while isinstance(nut, (ast.Attribute, ast.Subscript)):
        nut = nut.value
    return isinstance(nut, ast.Name) and nut.id == _NS_NODES


def _doc_chuoi(doan: list[str], bieu_thuc: str) -> ThamChieu:
    goc = f"{bieu_thuc[:200]!r}"
    if len(doan) < 3:
        raise LoiBienDich(
            "tham_chieu_khong_hop_le",
            f"`nodes` phai co dang nodes.<id>.output.<cong> / .status / "
            f".error -- nhan {'.'.join(doan)} trong {goc}")
    nid, mat = doan[1], doan[2]
    if not _ID.match(nid):
        raise LoiBienDich("tham_chieu_khong_hop_le",
                          f"id node khong hop le: {nid[:70]!r} trong {goc}")
    if mat not in _MAT_NODE:
        raise LoiBienDich(
            "tham_chieu_khong_hop_le",
            f"nodes.{nid}.{mat} khong doc duoc -- chi {list(_MAT_NODE)} "
            f"(spec 6.2), trong {goc}")
    if mat != "output":
        return ThamChieu(nid, "", mat)
    if len(doan) < 4:
        raise LoiBienDich(
            "tham_chieu_khong_hop_le",
            f"nodes.{nid}.output thieu ten cong -- output KHONG phai mot gia "
            f"tri, no la tap cong ra, trong {goc}")
    return ThamChieu(nid, doan[3], "output")


def trich_tham_chieu(bieu_thuc: str) -> tuple[ThamChieu, ...]:
    """Mọi tham chiếu `nodes.…` trong MỘT biểu thức (không có `{{ }}`).

    ⛔ Không phân tích được ⇒ ném, **không** trả rỗng. Rỗng nghĩa là *"biểu
       thức này không đọc của ai"* — một câu khẳng định, và ta không đo được
       nó cho một chuỗi ta chưa đọc nổi.
    """
    try:
        cay = ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as loi:
        raise LoiBienDich(
            "bieu_thuc_chua_ho_tro",
            f"khong phan tich duoc: {bieu_thuc[:200]!r} ({loi.msg})") from None

    ra: list[ThamChieu] = []

    def quet(nut: ast.AST) -> None:
        if isinstance(nut, (ast.Name, ast.Attribute, ast.Subscript)):
            doan = _chuoi_doan(nut)
            if doan is not None and doan[0] == _NS_NODES:
                ra.append(_doc_chuoi(doan, bieu_thuc))
                return                      # đã tiêu thụ cả chuỗi truy cập
            if doan is None and _goc_la_nodes(nut):
                raise LoiBienDich(
                    "tham_chieu_dong",
                    f"tham chieu `nodes` co doan DONG trong "
                    f"{bieu_thuc[:200]!r} -- khong kiem duoc to tien luc "
                    "publish nen khong cho phep")
        for con in ast.iter_child_nodes(nut):
            quet(con)

    quet(cay)
    return tuple(ra)


#: Một `{{ ... }}` DUY NHẤT bọc TRỌN chuỗi (đã `strip()`) — không có chữ
#: trước/sau (interpolation), y hệt ràng buộc cũ của `_THAM_CHIEU`. `.*` tham
#: (kèm `re.DOTALL`) là ĐÚNG ở đây, không phải một lỗi: nó bóc lớp ngoặc
#: NGOÀI CÙNG, nên `{{ {"a": {"b": 1}} }}` (dict lồng — §6 cho `ast.Dict`)
#: vẫn bóc đúng, khác `doan_bieu_thuc()` (dò `}}` ĐẦU TIÊN, sẽ cắt hụt ở dict
#: lồng) — `doan_bieu_thuc` phục vụ một câu hỏi khác (nhiều đoạn nội suy
#: trong một chuỗi, chưa có `noi_suy.py`), không phải câu hỏi ở đây (đúng
#: MỘT đoạn, trọn chuỗi).
BOC_BIEU_THUC = re.compile(r"^\{\{(.*)\}\}$", re.DOTALL)


#: Namespace §6.2 mà cổng publish node app/tool CHO PHÉP trong biểu thức
#: `params`. ⭐ 25/09 (wfb5, sau phản hồi chủ dự án round 2) — CHỈ `nodes`,
#: KHÔNG phải cả bảy namespace của `chinh_sach.NAMESPACE`.
#:
#: 🔴 VÌ SAO HẸP HƠN NGÔN NGỮ §6 ĐẦY ĐỦ — thu cổng cho KHỚP RUNTIME, không
#:    phải ngược lại. Lượt đầu của bản vá này uỷ quyền cho `ngon_ngu.kiem()`
#:    KHÔNG giới hạn `ten_cho_phep` (nhận cả `trigger`/`vars`/`run`/`loop`/
#:    `params`/`workflow`) — và đó là một cổng publish CHẤP NHẬN một thứ mà
#:    cầu nối job lúc CHẠY (`cau_noi.giai_tham_so`) không có cách nào GIẢI:
#:    `giai_tham_so` chỉ dựng được namespace `nodes` (từ ảnh chụp
#:    `NodeRunSnapshot` của các node tổ tiên) — nó KHÔNG có `trigger`/`vars`/
#:    `run`/`loop`/`params`/`workflow` ở điểm nộp job (đó là môi trường của
#:    `moi_truong.moi_truong_run`, dùng cho node LÕI trong `dong_co.py`, một
#:    đường thi hành KHÁC, không đi qua `cau_noi.py`). Một `params` publish
#:    được với `{{ trigger.body }}` mà lúc chạy không giải được là ĐÚNG hạng
#:    lỗi "một cổng nhận thứ mà bên gọi quên truyền" — chỉ khác populate lỗi
#:    ở PUBLISH (rẻ) hay ở RUNTIME sau khi tiền đã giữ (đắt). Hẹp `_doi`
#:    xuống đúng cái `giai_tham_so` giải được là cách rẻ.
#: ⚠️ KHÔNG vĩnh viễn — ngày `cau_noi.giai_tham_so` (hoặc một tầng kế thừa)
#:    dựng được `trigger`/`vars`/`run`/`loop`/`params`/`workflow` cho node
#:    app/tool (vd nối `moi_truong.moi_truong_run` vào đường nộp job), tập
#:    này mở theo — ĐÚNG namespace nào có nguồn thật lúc chạy.
_NAMESPACE_APP_TOOL = frozenset({"nodes"})


def _bieu_thuc_s6_hop_le(bieu_thuc: str) -> bool:
    """Nội dung bên trong `{{ }}` có phải một biểu thức HÌNH DẠNG hợp lệ của
    ngôn ngữ §6 không — GIỚI HẠN ở namespace `_NAMESPACE_APP_TOOL`?

    ⭐ GỌI THẲNG bộ duyệt §6 đã có (`chinh_sach.kiem_ngon_ngu` lắp với
       `ngon_ngu.NGON_NGU` — chính sách đầy đủ + bảng 49 hàm thật của
       `ham_bieu_thuc.BANG_HAM`, `ten_cho_phep=_NAMESPACE_APP_TOOL`) — ⛔
       KHÔNG tự dựng một bộ duyệt thứ hai ở tầng publish, và ⛔ không tự
       dựng một tập con HÀM (bảng hàm vẫn ĐẦY ĐỦ 49 hàm §6.3 — hàm không
       đọc `nodes.<id>.output` sớm hơn lúc chạy, không có gì để hẹp).
    ⭐ Cùng lý do `goc_phai_tinh="nodes"` của `chinh_sach.DAY_DU`: một tham
       chiếu `nodes[...]` có đoạn ĐỘNG bị `kiem_ngon_ngu` từ chối tại đây,
       CÙNG luật với `trich_tham_chieu` (`tham_chieu_dong`) — hai cửa không
       thể rơi vào cảnh một cửa mở, cửa kia đóng cho cùng một hình dạng.

    ⚠️ Đây là câu hỏi về HÌNH DẠNG (cú pháp + tên namespace + bảng hàm) —
       KHÔNG cần môi trường, không biết `params` có tổ tiên nào. Ai là tổ
       tiên và cổng ra có tồn tại là câu hỏi KHÁC, `cau_truc()`/`bien_dich()`
       trả lời bằng `_tham_chieu_trong`/`trich_tham_chieu` (không đổi).
    """
    from platform_core.workflow import ngon_ngu
    from platform_core.workflow.chinh_sach import LoiNgonNgu, kiem_ngon_ngu

    try:
        kiem_ngon_ngu(bieu_thuc, cs=ngon_ngu.NGON_NGU,
                      ten_cho_phep=_NAMESPACE_APP_TOOL)
    except LoiNgonNgu:
        return False
    return True


def _doi(gia_tri: Any, node_id: str, *, nghiem: bool = True) -> Any:
    """`$a.b` (Canvas cũ) → `{{ nodes.a.output.b }}`; phán quyết `{{ }}` khác
    bằng ngôn ngữ §6 (`_bieu_thuc_s6_hop_le`), không còn bằng regex riêng.

    🔑 `nghiem=False` ⇒ **chỉ đổi, không phán quyết**. Đo trên trình duyệt
       24/09: người dùng gõ `"Vẽ: {{ nodes"` (một biểu thức đang gõ DỞ) thì
       `cau_truc()` ném `bieu_thuc_chua_ho_tro`, và cửa gợi ý mất sạch phần
       `nodes.*` — đúng giây họ cần nó. Cấu trúc đồ thị (ai là tổ tiên của ai)
       **không phụ thuộc** vào việc một chuỗi tham số đã gõ xong hay chưa.
    ⛔ Cổng publish vẫn NGHIÊM: `bien_dich()` gọi lại hàm này với `nghiem=True`
       trên đúng tham số ấy, nên không có gì lọt thêm.

    ⭐ 25/09 (wfb5) — ĐÃ NỐI khoảng cách hai tầng biểu thức, ĐÚNG PHẦN
       `giai_tham_so` GIẢI ĐƯỢC lúc chạy. Trước đây nhánh này chỉ nhận đúng
       `{{ nodes.<id>.output.<cổng> }}` (MỘT đoạn sau `.output.`) — hẹp hơn
       hẳn ngôn ngữ §6 mà node lõi đã dùng, và đó là lý do
       `{{ nodes.fetch_sheet.output.json.prompt }}` (model thật sinh ra ở
       FLOW G lượt 2, `test_4190`) bị từ chối dù là một biểu thức §6 hợp lệ
       cho `nodes`. Nay: MỌI chuỗi bọc `{{ }}` trọn vẹn (`BOC_BIEU_THUC`) mà
       nội dung là một biểu thức §6 hợp lệ CHỈ DÙNG namespace `nodes`
       (`_NAMESPACE_APP_TOOL`, hàm §6.3 vẫn đầy đủ) đều được nhận —
       `nodes.a.output.b` (dạng cũ) là một tập con của tập đó nên hành vi cũ
       không đổi.
    ⭐ ĐÓNG ĐÚNG KHỚP RUNTIME — không rộng hơn. Round đầu của bản vá này (đã
       bị chủ dự án từ chối gộp) uỷ quyền cho TOÀN BỘ bảy namespace §6.2,
       kể cả những namespace `cau_noi.giai_tham_so` (cầu nối job lúc CHẠY,
       đường tiền) không có cách nào dựng ở điểm nộp job — publish NHẬN,
       runtime IM LẶNG trả nguyên văn `{{ ... }}` cho job (fail-OPEN, nguy
       hiểm hơn từ chối). `_NAMESPACE_APP_TOOL` hẹp cổng này xuống ĐÚNG
       namespace `giai_tham_so` giải được (xem `giai_tham_so.__doc__` ở
       `cau_noi.py` — cùng dùng `bien_dich.trich_tham_chieu` +
       `chinh_sach.moi_truong_wf` + `ngon_ngu.tinh`, MỘT bộ máy cho cả hai
       tầng publish/runtime, không phải hai bộ trôi nhau).
    """
    if isinstance(gia_tri, dict):
        return {k: _doi(v, node_id, nghiem=nghiem) for k, v in gia_tri.items()}
    if isinstance(gia_tri, list):
        return [_doi(v, node_id, nghiem=nghiem) for v in gia_tri]
    if isinstance(gia_tri, str):
        m = _CU.match(gia_tri.strip())
        if m:
            return "{{ nodes.%s.output.%s }}" % (m.group(1), m.group(2))
        if nghiem and "{{" in gia_tri:
            boc = BOC_BIEU_THUC.match(gia_tri.strip())
            if boc is None or not _bieu_thuc_s6_hop_le(boc.group(1).strip()):
                raise LoiBienDich(
                    "bieu_thuc_chua_ho_tro",
                    "chi ho tro dung MOT bieu thuc ngon ngu Sec6 boc trong "
                    "{{ }} (vi du {{ nodes.<id>.output.<cong> }}, ke ca "
                    "duong dan long ben trong cong)",
                    node_id)
    return gia_tri


def cong_params_nhan(bieu_thuc: str) -> bool:
    """Cổng `params` của publish có nhận `{{ <biểu thức> }}` này không?

    ⭐ Hỏi bằng cách **gọi chính cái cổng** (`_doi`), không bằng một bản mô tả
       của nó. 25/09 (wfb5): `_doi` nay uỷ quyền câu hỏi HÌNH DẠNG cho
       `_bieu_thuc_s6_hop_le` (ngôn ngữ §6, namespace giới hạn
       `_NAMESPACE_APP_TOOL` — ĐÚNG tập `cau_noi.giai_tham_so` giải được lúc
       chạy), nên câu trả lời ở đây theo sát ngôn ngữ §6 trong đúng phạm vi
       đó — rộng hơn dạng `nodes.<id>.output.<cổng>` đơn cũ (nhận lồng sâu,
       nhận hàm §6.3), nhưng KHÔNG rộng ra các namespace khác. Ngày ai đó
       nới/thu hẹp `_doi`/`_NAMESPACE_APP_TOOL`, câu trả lời ở đây **tự đổi
       theo**, không có bảng nào phải sửa.

    ⚠️ Chỉ trả lời về HÌNH DẠNG biểu thức. Tổ tiên và cổng tồn tại là câu hỏi
       khác, do `CauTruc` trả lời. Và hình dạng ở đây được CHỐT khớp với
       những gì `giai_tham_so` giải được lúc CHẠY — True ở đây nghĩa là publish
       **và** chạy thật đều qua (xem `_doi.__doc__`).
    """
    try:
        _doi({"_": "{{ %s }}" % bieu_thuc}, "")
    except LoiBienDich:
        return False
    return True


def _tham_chieu_trong(gia_tri: Any) -> set[ThamChieu]:
    """Mọi tham chiếu `nodes.…` nằm đâu đó trong một cây tham số."""
    ra: set[ThamChieu] = set()
    if isinstance(gia_tri, dict):
        for v in gia_tri.values():
            ra |= _tham_chieu_trong(v)
    elif isinstance(gia_tri, list):
        for v in gia_tri:
            ra |= _tham_chieu_trong(v)
    elif isinstance(gia_tri, str):
        for bt in doan_bieu_thuc(gia_tri):
            ra.update(trich_tham_chieu(bt))
    return ra


#: Tiền tố của node LÕI (`nut_loi/`, spec §4.5 nguồn 1).
#:
#: 🔴 TỪNG CHỈ LÀ `"core."`, VÀ ĐÓ LÀ MỘT LỖI IM LẶNG. `nut_loi/__init__.py`
#:    khai **bốn** không gian ngay ở dòng đầu docstring — `core.*`,
#:    `trigger.*`, `ai.*`, `connector.*` — và cả bốn đều đăng ký vào cùng một
#:    sổ `nut_loi.tat_ca()`. Bộ biên dịch chỉ nhận ra một trong bốn, nên một
#:    node `ai.*` đầy đủ (đã khai, đã có `NodeDefinition`, đã có bộ thi hành)
#:    rơi xuống nhánh cuối của `_node` và bị từ chối bằng
#:    `loai_node_chua_ho_tro` — một thông điệp nói *"chưa hỗ trợ"* về một thứ
#:    đã được hỗ trợ.
#:
#: ⛔ Không thay bằng "tra `nut_loi.tat_ca()` rồi suy": `_node` phải phân biệt
#:    được **node lõi** với **node app** TRƯỚC khi tra sổ nào, vì hai bên có
#:    hai nguồn khác nhau (spec §4.5). Một danh sách tiền tố là bản khai của
#:    ranh giới ấy; `str.startswith` nhận tuple, nên ba chỗ dùng không đổi.
TIEN_TO_LOI: tuple[str, ...] = ("core.", "trigger.", "ai.", "connector.")

#: Kiểu tham số "đây là một BIỂU THỨC §6" trong `NodeDefinition.tham_so`.
#:
#: 🔴 VÌ SAO PHẢI CÓ NHÃN NÀY — một lỗ ĐO ĐƯỢC, không phải một tinh chỉnh.
#:
#:    Cổng tổ tiên §6.2 (`bien_dich`, "một cổng an ninh về tiền") chỉ soi các
#:    đoạn `{{ … }}` trong `params`. Nhưng tham số của node lõi là biểu thức
#:    **trần** (`core.if.dieu_kien = "nodes.a.output.text == 'co'"`, không có
#:    ngoặc): `doan_bieu_thuc` không thấy gì, và một node đọc output của một
#:    node KHÔNG phải tổ tiên đi lọt qua publish. Phát hiện khi trả lời cái
#:    chuông `test_1714` ở Task 5.
#:
#: ⇒ Lược đồ tham số phải NÓI RA tham số nào là biểu thức. Đoán theo tên
#:   (`dieu_kien`, `bieu_thuc`, `items`…) là một bảng thứ hai sẽ trôi.
KIEU_BIEU_THUC = "bieu_thuc"

#: `{tên: biểu thức}` — tham số của `core.set`. Cùng lý do với
#: `KIEU_BIEU_THUC`: các biểu thức trong đó cũng phải đi qua cổng tổ tiên §6.2.
KIEU_BANG_BIEU_THUC = "bang_bieu_thuc"


def _thay_duoc_trong_vars(ten) -> bool:
    """Tên biến `core.set` đọc được từ ngôn ngữ §6? Hỏi THẲNG `bien_vars`."""
    from platform_core.workflow import bien_vars

    return bien_vars._thay_duoc(ten)


def _tham_chieu_node_loi(n: dict) -> set[ThamChieu]:
    """Tham chiếu `nodes.…` trong các tham số BIỂU THỨC của một node lõi."""
    from platform_core.workflow import nut_loi

    nd = nut_loi.tat_ca().get(str(n.get("type")))
    if nd is None:
        return set()
    thuoc = (nd.tham_so or {}).get("properties") or {}
    ra: set[ThamChieu] = set()
    for khoa, mo_ta in thuoc.items():
        kieu = str(mo_ta.get("type", ""))
        gia_tri = (n.get("params") or {}).get(khoa)
        if kieu == KIEU_BIEU_THUC and isinstance(gia_tri, str) \
                and gia_tri.strip():
            ra.update(trich_tham_chieu(gia_tri))
        elif kieu == KIEU_BANG_BIEU_THUC and isinstance(gia_tri, dict):
            for bt in gia_tri.values():
                if isinstance(bt, str) and bt.strip():
                    ra.update(trich_tham_chieu(bt))
    return ra


def _kiem_tham_so_loi(nd, params: dict, nid: str) -> None:
    """Kiểm `params` của một node lõi theo `NodeDefinition.tham_so`.

    ⛔ Chặn ở **publish**, không lúc chạy — cùng lý do với cổng tổ tiên §6.2:
       lúc chạy là lúc đang tiêu tiền của khách, và một `trang_thai="HOI_HOI"`
       phát hiện ở đó nghĩa là run đã chạy được nửa đường.

    ⚠️ Cố ý KHÔNG dựng một bộ kiểm JSON Schema đầy đủ ở đây (`luoc_do.py` có
       việc khác). Ba luật đủ cho `tham_so` của node lõi, và mỗi luật là một
       lỗi đã thấy: thiếu khoá bắt buộc, khoá lạ (gõ sai tên im lặng không có
       tác dụng), `enum` ngoài tập.
    """
    lo = nd.tham_so or {}
    thuoc = lo.get("properties") or {}
    thieu = [k for k in (lo.get("required") or []) if k not in params]
    if thieu:
        raise LoiBienDich("thieu_tham_so",
                          f"{nd.type} thieu tham so bat buoc: {sorted(thieu)}",
                          nid)
    # ⭐ `mot_trong`: ÍT NHẤT MỘT trong nhóm phải có mặt. `required` không nói
    #    được điều đó — `core.delay` nhận `duration_s` **hoặc** `until`, và
    #    không có cái nào thì nó là một điểm chờ **không bao giờ tới hạn**: run
    #    đứng tới TTL 20 giờ với tiền bị giữ, không lỗi, không cảnh báo.
    #
    # ⛔ Đây là một luật của LƯỢC ĐỒ, không phải một `if` cho `core.delay`:
    #    compiler không được biết tên node nào (`G42`). Node nào cần thì khai
    #    `mot_trong` trong `tham_so` của chính nó.
    for nhom in (lo.get("mot_trong") or []):
        if not any(k in params for k in nhom):
            raise LoiBienDich(
                "thieu_tham_so",
                f"{nd.type} phai co it nhat mot trong {sorted(nhom)}", nid)
    # ⭐ TRẦN SỐ HỌC của lược đồ: `maximum` / `minimum` / `maxItems`. Nguồn:
    #    Activepieces `packages/core/shared/src/lib/ee/agent/agent.ts` khai
    #    `maxSteps … .max(MAX_AGENT_STEP_BUDGET)` và `tools … .max(…)` ngay
    #    TRONG lược đồ zod, nên một cấu hình vượt trần không bao giờ được LƯU.
    #
    # ⛔ Đây là một luật của LƯỢC ĐỒ, y như `mot_trong` ở trên — compiler vẫn
    #    không biết tên node nào (`G42`). Node nào cần trần thì tự khai.
    #    Trần cưỡng chế ở đây chứ không lúc chạy: lúc chạy là lúc node đã mở
    #    được một lượt tiêu tiền rồi.
    for khoa, mo_ta in thuoc.items():
        if khoa not in params:
            continue
        gia_tri = params[khoa]
        if isinstance(gia_tri, bool) or not isinstance(gia_tri, (int, float)):
            so = len(gia_tri) if isinstance(gia_tri, (list, tuple)) else None
            tran = mo_ta.get("maxItems")
            if so is not None and isinstance(tran, int) and so > tran:
                raise LoiBienDich(
                    "tham_so_vuot_tran",
                    f"{nd.type}.{khoa} co {so} phan tu, toi da {tran}", nid)
            continue
        for ten_tran, phep in (("maximum", lambda a, b: a > b),
                               ("minimum", lambda a, b: a < b)):
            muc = mo_ta.get(ten_tran)
            if isinstance(muc, (int, float)) and not isinstance(muc, bool) \
                    and phep(gia_tri, muc):
                raise LoiBienDich(
                    "tham_so_vuot_tran",
                    f"{nd.type}.{khoa} = {gia_tri}, {ten_tran} la {muc}", nid)
    if lo.get("additionalProperties") is False:
        thua = sorted(set(params) - set(thuoc))
        if thua:
            raise LoiBienDich(
                "tham_so_la",
                f"{nd.type} khong co tham so {thua} (co: {sorted(thuoc)})", nid)
    for khoa, mo_ta in thuoc.items():
        kieu = str(mo_ta.get("type", ""))
        if khoa in params and kieu == KIEU_BANG_BIEU_THUC:
            bang = params[khoa]
            # ⚠️ Bảng RỖNG hợp lệ: `core.call_workflow.inputs = {}` là một
            #    lời gọi không truyền gì, và đó là ca thường.
            if not isinstance(bang, dict):
                raise LoiBienDich(
                    "tham_so_khong_hop_le",
                    f"{nd.type}.{khoa} phai la mot bang ten->bieu thuc",
                    nid)
            for ten, bt in bang.items():
                if not _thay_duoc_trong_vars(ten):
                    raise LoiBienDich(
                        "ten_bien_khong_hop_le",
                        f"{nd.type}.{khoa}: ten bien {ten!r} khong doc "
                        "duoc tu ngon ngu Sec6 (khoa bat dau gach duoi la "
                        "VO HINH) -- nhan no roi lang le khong thay no la "
                        "cach te nhat", nid)
                if not isinstance(bt, str):
                    raise LoiBienDich(
                        "tham_so_khong_hop_le",
                        f"{nd.type}.{khoa}.{ten} phai la mot bieu thuc "
                        "(chuoi)", nid)
        if khoa in params and kieu == KIEU_BIEU_THUC \
                and not isinstance(params[khoa], str):
            raise LoiBienDich(
                "tham_so_khong_hop_le",
                f"{nd.type}.{khoa} phai la mot bieu thuc (chuoi) -- nhan "
                f"{type(params[khoa]).__name__}", nid)
        if khoa not in params or str(mo_ta.get("type", "")) != "enum":
            continue
        cho_phep = [str(x) for x in (mo_ta.get("values") or [])]
        if str(params[khoa]) not in cho_phep:
            raise LoiBienDich(
                "tham_so_khong_hop_le",
                f"{nd.type}.{khoa} phai la mot trong {cho_phep} -- nhan "
                f"{params[khoa]!r}", nid)


def _node_loi(n: dict, nid: str, loai: str) -> dict:
    """Node `core.*` — nguồn là `nut_loi/`, KHÔNG phải registry công cụ."""
    from platform_core.workflow import nut_loi

    nd = nut_loi.tat_ca().get(loai)
    if nd is None:
        raise LoiBienDich("node_khong_ton_tai", loai, nid)
    if not nd.publish_duoc:
        raise LoiBienDich("loai_node_chua_ho_tro", loai, nid)
    params = dict(n.get("params") or {})
    _kiem_tham_so_loi(nd, params, nid)
    # 🔴 Truoc 24/09/2026 dong nay ghi cung `""`. Mot o LUON RONG thi khong ai
    #    gan duoc credential cho `core.http`, va he qua that la nguoi soan phai
    #    go token vao `params` — tuc vao `workflow_version`, mot ban ghi duoc
    #    NHAN BAN khi khach "Save as" va tra nguyen ven cho trinh soan thao.
    ref = str(n.get("credential_ref") or "")
    if ref and not nd.credential:
        # ⛔ Node nay khong goi ra ngoai, nen mot ref o day la mot hieu nham
        #    cua nguoi soan — va mot hieu nham im lang ve bao mat la thu te
        #    nhat: ho tuong da gan khoa, thuc ra chua.
        raise LoiBienDich(
            "credential_khong_ho_tro",
            f"node {loai!r} khong nhan credential nao", nid)
    return {"id": nid, "type": loai, "type_version": nd.type_version,
            "params": params, "credential_ref": ref,
            "settings": dict(n.get("settings") or {}),
            "thi_hanh": nd.thi_hanh}


def _node(n: dict, cc: dict[str, CongCu], *, nghiem: bool = True) -> dict:
    nid = str(n.get("id", ""))
    if not _ID.match(nid):
        raise LoiBienDich("id_khong_hop_le", f"id node {nid[:70]!r}", nid[:64])
    loai = str(n.get("type", ""))
    if loai.startswith(TIEN_TO_LOI):
        return _node_loi(n, nid, loai)
    if loai == "tool":
        data = n.get("data") or {}
        ten, params = str(data.get("tool", "")), data.get("params") or {}
        settings = data.get("settings") or {}
    elif loai.startswith("app."):
        ten, params = loai[4:], n.get("params") or {}
        settings = n.get("settings") or {}
    else:
        raise LoiBienDich("loai_node_chua_ho_tro", loai, nid)
    tool = cc.get(ten)
    if tool is None:
        raise LoiBienDich("node_khong_ton_tai", ten, nid)
    return {"id": nid, "type": f"app.{ten}", "type_version": tool.type_version,
            "params": _doi(dict(params), nid, nghiem=nghiem),
            "credential_ref": str(n.get("credential_ref") or ""),
            "settings": dict(settings), "thi_hanh": "job"}


class CauTruc(NamedTuple):
    """Phần CẤU TRÚC của một tài liệu draft — chưa đọc một biểu thức nào.

    🔑 VÌ SAO TÁCH RA. Quan hệ **tổ tiên** và tập **cổng ra thật** là câu trả
       lời cho *"node này được đọc của ai"*. `bien_dich()` hỏi câu đó để **từ
       chối lúc publish**; cửa gợi ý (`goi_y.py`) hỏi đúng câu đó để **không
       mời người dùng viết một biểu thức sẽ bị từ chối**. Hai bên phải hỏi
       CÙNG MỘT CHỖ: một bản sao của luật tổ tiên ở tầng gợi ý là một bản sao
       sẽ trôi, và ngày nó trôi thì trình soạn gợi ý một thứ mà cổng publish
       ném lại vào mặt người dùng.

    ⛔ Hàm dựng nó **không đọc `params`**: một bản nháp đang gõ dở có thể mang
       một biểu thức chưa xong, và điều đó không được làm mất gợi ý.
    """

    nodes: list[dict]
    edges: list[dict]
    #: Thứ tự tô-pô (Kahn) — `graph.thu_tu`.
    thu_tu: list[str]
    #: `{id: tập id tổ tiên}`.
    to_tien: dict[str, set[str]]
    #: `{id: tập cổng RA thật}` theo `CongCu.returns`.
    cong_ra: dict[str, frozenset[str]]


def cau_truc(document: dict, *,
             cong_cu: Optional[dict[str, CongCu]] = None,
             nghiem: bool = True) -> CauTruc:
    """Gộp trang → node/cạnh → Kahn → tổ tiên → cổng ra. Sai thì ném.

    `nghiem=False` bỏ qua phán quyết về HÌNH DẠNG biểu thức trong `params`
    (xem `_doi`) — cấu trúc vẫn đúng, và một biểu thức đang gõ dở không làm
    mất gợi ý của chính người đang gõ.
    """
    cc = _nguon.tat_ca() if cong_cu is None else cong_cu
    nodes: list[dict] = []
    edges: list[dict] = []
    trang_cua: dict[str, str] = {}
    for trang in document.get("pages") or []:
        pid = str(trang.get("id", ""))
        for n in trang.get("nodes") or []:
            nd = _node(n, cc, nghiem=nghiem)
            if nd["id"] in trang_cua:
                raise LoiBienDich("id_trung", nd["id"], nd["id"])
            trang_cua[nd["id"]] = pid
            nodes.append(nd)
        for c in trang.get("edges") or []:
            e = _canh_v3(c)
            e["kind"] = str(c.get("kind") or "DATA")
            e["condition"] = str(c.get("condition") or "")
            edges.append((pid, e))  # type: ignore[arg-type]
    if not nodes:
        raise LoiBienDich("do_thi_rong", "khong co node nao")

    ra_edges: list[dict] = []
    for pid, e in edges:  # type: ignore[misc]
        a, b = e["source_node"], e["target_node"]
        if a not in trang_cua or b not in trang_cua:
            raise LoiBienDich("canh_khong_hop_le", f"{a}->{b}", b)
        if e["kind"] not in _KIND:
            raise LoiBienDich("canh_khong_hop_le", e["kind"], b)
        if trang_cua[a] != pid or trang_cua[b] != pid:
            raise LoiBienDich("canh_khac_trang", f"{a}->{b}", b)
        ra_edges.append(e)

    # Kahn: thứ tự tô-pô + phát hiện chu trình.
    vao = {n["id"]: 0 for n in nodes}
    ke: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in ra_edges:
        ke[e["source_node"]].append(e["target_node"])
        vao[e["target_node"]] += 1
    q = deque(sorted(k for k, v in vao.items() if v == 0))
    thu_tu: list[str] = []
    while q:
        k = q.popleft()
        thu_tu.append(k)
        for t in sorted(ke[k]):
            vao[t] -= 1
            if vao[t] == 0:
                q.append(t)
    if len(thu_tu) != len(nodes):
        raise LoiBienDich("chu_trinh", "do thi co chu trinh")

    to_tien: dict[str, set[str]] = {k: set() for k in thu_tu}
    for k in thu_tu:
        for t in ke[k]:
            to_tien[t] |= to_tien[k] | {k}
    # Tập cổng ra THẬT của từng node. Nguồn là `CongCu.returns` — đúng cái mà
    # `luoc_do.cong_ra()` duyệt để dựng `NodeDefinition.cong_ra` (spec §6.2 nói
    # *"cổng phải tồn tại trong NodeDefinition của X"*), nên đây KHÔNG phải một
    # bảng thứ hai: cùng một nguồn, đọc thẳng. Không đi qua `luoc_do` vì bộ ấy
    # ném `LoiLuocDo` khi gặp kiểu lạ, và một kiểu lạ ở một tool KHÔNG liên
    # quan không được phép làm sập đường publish của người khác.
    # ⚠️ Node LÕI không có ToolSpec; cổng ra của nó do chính `NodeDefinition`
    #    khai (`nut_loi/`, spec §4.5 nguồn 1). Vẫn là **một** nguồn cho mỗi
    #    loại node, không phải một bảng thứ hai cho cùng một loại.
    from platform_core.workflow import nut_loi as _loi
    so_loi = _loi.tat_ca()
    cong_ra_cua = {
        n["id"]: (frozenset(ten for ten, _c in so_loi[n["type"]].cong_ra)
                  if str(n["type"]).startswith(TIEN_TO_LOI)
                  else frozenset(cc[n["type"][4:]].returns or {}))
        for n in nodes}
    return CauTruc(nodes, ra_edges, thu_tu, to_tien, cong_ra_cua)


def _kiem_ghi_bien(nodes: list[dict], to_tien: dict) -> None:
    """§6.5: hai `core.set` ghi cùng khoá mà không ai là tổ tiên ⇒ TỪ CHỐI.

    ⭐ `bien_vars.kiem_ghi_xung_dot` đã có từ P2 và đã được test — **nhưng
       chưa ai gọi**. Một cổng không có người gọi là một cổng mở; đây là chỗ
       nối dây.
    """
    from platform_core.workflow import bien_vars

    khoa_ghi = {str(n["id"]): list((n.get("params") or {}).get("bien") or {})
                for n in nodes if str(n.get("type")) == bien_vars.LOAI_GHI}
    if khoa_ghi:
        bien_vars.kiem_ghi_xung_dot(khoa_ghi, to_tien)


def _kiem_ten_output(nodes: list[dict]) -> None:
    """Hai `core.output` cùng tên ⇒ kết quả run phụ thuộc thứ tự chạy."""
    from platform_core.workflow import ket_qua_run

    thay: dict[str, str] = {}
    for n in nodes:
        if str(n.get("type")) != ket_qua_run.LOAI_OUTPUT:
            continue
        ten = str((n.get("params") or {}).get("ten") or "")
        if ten in thay:
            raise LoiBienDich(
                "trung_ten_output",
                f"node {thay[ten]!r} va {n['id']!r} cung khai dau ra "
                f"{ten!r} -- ket qua cua run se phu thuoc thu tu chay",
                str(n["id"]))
        thay[ten] = str(n["id"])


def bien_dich(document: dict, *,
              cong_cu: Optional[dict[str, CongCu]] = None) -> dict:
    ct = cau_truc(document, cong_cu=cong_cu)
    nodes, ra_edges, thu_tu = ct.nodes, ct.edges, ct.thu_tu
    to_tien, cong_ra_cua = ct.to_tien, ct.cong_ra
    for n in nodes:
        nid = n["id"]
        # ⛔ Phán quyết về HÌNH DẠNG biểu thức nằm ở ĐÂY, không ở `cau_truc`:
        #    `cau_truc` còn phục vụ cửa gợi ý, nơi một biểu thức gõ dở là
        #    chuyện thường. Cổng publish thì không tha (test_1714).
        tham_chieu = _tham_chieu_trong(n["params"])
        if str(n["type"]).startswith(TIEN_TO_LOI):
            tham_chieu |= _tham_chieu_node_loi(n)
        else:
            _doi(n["params"], nid)
        for tc in sorted(tham_chieu):
            doc = (f"nodes.{tc.node}.output.{tc.cong}" if tc.loai == "output"
                   else f"nodes.{tc.node}.{tc.loai}")
            if tc.node == nid:
                # Một node KHÔNG phải tổ tiên của chính nó: lúc tính `params`
                # của nó, output của nó chưa tồn tại. (Cùng chỗ Activepieces
                # lọc bước đích ra khỏi `findPathToStep`.)
                raise LoiBienDich(
                    "tham_chieu_khong_phai_to_tien",
                    f"node {nid!r} doc {doc} tuc la doc CHINH NO -- output "
                    "chua ton tai luc node nay chay", nid)
            if tc.node not in cong_ra_cua:
                raise LoiBienDich(
                    "tham_chieu_node_khong_ton_tai",
                    f"node {nid!r} doc {doc} nhung do thi khong co node "
                    f"{tc.node!r}", nid)
            if tc.node not in to_tien[nid]:
                raise LoiBienDich(
                    "tham_chieu_khong_phai_to_tien",
                    f"node {nid!r} doc {doc} nhung {tc.node!r} KHONG phai to "
                    f"tien cua no theo `thu_tu` -- output do chua ton tai luc "
                    f"{nid!r} chay", nid)
            if tc.loai == "output" and tc.cong not in cong_ra_cua[tc.node]:
                raise LoiBienDich(
                    "cong_khong_ton_tai",
                    f"node {nid!r} doc {doc} nhung node {tc.node!r} khong co "
                    f"cong ra {tc.cong!r}; cong co that: "
                    f"{sorted(cong_ra_cua[tc.node])}", nid)

    # ⚠️ `than_foreach` vẫn được gọi ở `bao_gia` (nhân trần chi phí) và ở
    #    `nut_loi/vong_lap` (lái vòng). Ở đây không còn phép cấm nào:
    #    thân `foreach` NAY nhận cả node sinh job, vì `node_run` đã khoá
    #    theo ĐƯỜNG THI HÀNH (`thi_hanh.khoa_node`).
    _kiem_ghi_bien(nodes, to_tien)
    _kiem_ten_output(nodes)

    cai_dat = document.get("settings") or {}
    return {
        "schema": SCHEMA, "inputs": [], "outputs": [],
        "settings": {
            "max_concurrency": max(1, min(_MAX_CONCURRENCY,
                                          int(cai_dat.get("max_concurrency", 4)))),
            "timeout_s": int(cai_dat.get("timeout_s", _TIMEOUT_MAC_DINH)),
        },
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "edges": sorted(ra_edges, key=lambda e: e["id"]),
        "thu_tu": thu_tu,
    }


__all__ = ["BOC_BIEU_THUC", "MAT_NODE", "SCHEMA", "CauTruc", "LoiBienDich",
           "ThamChieu", "bien_dich", "cau_truc", "cong_params_nhan",
           "doan_bieu_thuc", "la_tham_chieu", "trich_tham_chieu"]
