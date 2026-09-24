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


def _doi(gia_tri: Any, node_id: str, *, nghiem: bool = True) -> Any:
    """`$a.b` (Canvas cũ) → `{{ nodes.a.output.b }}`; chặn `{{ }}` khác.

    🔑 `nghiem=False` ⇒ **chỉ đổi, không phán quyết**. Đo trên trình duyệt
       24/09: người dùng gõ `"Vẽ: {{ nodes"` (một biểu thức đang gõ DỞ) thì
       `cau_truc()` ném `bieu_thuc_chua_ho_tro`, và cửa gợi ý mất sạch phần
       `nodes.*` — đúng giây họ cần nó. Cấu trúc đồ thị (ai là tổ tiên của ai)
       **không phụ thuộc** vào việc một chuỗi tham số đã gõ xong hay chưa.
    ⛔ Cổng publish vẫn NGHIÊM: `bien_dich()` gọi lại hàm này với `nghiem=True`
       trên đúng tham số ấy, nên không có gì lọt thêm.
    """
    if isinstance(gia_tri, dict):
        return {k: _doi(v, node_id, nghiem=nghiem) for k, v in gia_tri.items()}
    if isinstance(gia_tri, list):
        return [_doi(v, node_id, nghiem=nghiem) for v in gia_tri]
    if isinstance(gia_tri, str):
        m = _CU.match(gia_tri.strip())
        if m:
            return "{{ nodes.%s.output.%s }}" % (m.group(1), m.group(2))
        if nghiem and "{{" in gia_tri and la_tham_chieu(gia_tri) is None:
            raise LoiBienDich("bieu_thuc_chua_ho_tro",
                              "chi ho tro {{ nodes.<id>.output.<cong> }}",
                              node_id)
    return gia_tri


def cong_params_nhan(bieu_thuc: str) -> bool:
    """Cổng `params` của publish có nhận `{{ <biểu thức> }}` này không?

    ⭐ Hỏi bằng cách **gọi chính cái cổng** (`_doi`), không bằng một bản mô tả
       của nó. Hôm nay `_doi` chỉ nhận đúng `{{ nodes.<id>.output.<cổng> }}`
       (plan 01a) trong khi ngôn ngữ §6 đã có hàm, `trigger`, `vars`… — một
       khoảng cách THẬT giữa hai tầng. Cửa gợi ý phải nói ra khoảng cách đó
       thay vì mời người dùng viết một biểu thức sẽ bị từ chối lúc publish; và
       ngày ai đó nới `_doi`, câu trả lời ở đây **tự đổi theo**, không có bảng
       nào phải sửa.

    ⚠️ Chỉ trả lời về HÌNH DẠNG biểu thức. Tổ tiên và cổng tồn tại là câu hỏi
       khác, do `CauTruc` trả lời.
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
TIEN_TO_LOI = "core."

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


def _tham_chieu_node_loi(n: dict) -> set[ThamChieu]:
    """Tham chiếu `nodes.…` trong các tham số BIỂU THỨC của một node lõi."""
    from platform_core.workflow import nut_loi

    nd = nut_loi.tat_ca().get(str(n.get("type")))
    if nd is None:
        return set()
    thuoc = (nd.tham_so or {}).get("properties") or {}
    ra: set[ThamChieu] = set()
    for khoa, mo_ta in thuoc.items():
        if str(mo_ta.get("type", "")) != KIEU_BIEU_THUC:
            continue
        gia_tri = (n.get("params") or {}).get(khoa)
        if isinstance(gia_tri, str) and gia_tri.strip():
            ra.update(trich_tham_chieu(gia_tri))
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
    if lo.get("additionalProperties") is False:
        thua = sorted(set(params) - set(thuoc))
        if thua:
            raise LoiBienDich(
                "tham_so_la",
                f"{nd.type} khong co tham so {thua} (co: {sorted(thuoc)})", nid)
    for khoa, mo_ta in thuoc.items():
        if khoa in params and str(mo_ta.get("type", "")) == KIEU_BIEU_THUC                 and not isinstance(params[khoa], str):
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
    return {"id": nid, "type": loai, "type_version": nd.type_version,
            "params": params, "credential_ref": "",
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


def _kiem_than_foreach(graph: dict) -> None:
    """Thân `foreach` chỉ được chứa node `inline` — chặn ở PUBLISH.

    ⛔ Lý do đầy đủ ở `nut_loi/vong_lap.py`: `node_run` khoá theo
       `(run_id, node_id)` nên một node thân chạy 30 lần **không có chỗ** để 30
       trạng thái sống. Thân có node job phải đi qua run con (`body_workflow`,
       §5.9) — Task 7.

    ⚠️ Từ chối ở publish, không lúc chạy: một đồ thị chạy được nửa vòng rồi
       treo đã tiêu tiền thật, và người khai không có cách nào biết trước.
    """
    from platform_core.workflow import bao_gia

    theo_id = {str(n["id"]): n for n in graph.get("nodes") or []}
    for f, (_dong, than) in bao_gia.than_foreach(graph).items():
        job = sorted(k for k in than
                     if str(theo_id[k].get("thi_hanh")) != "inline")
        if job:
            raise LoiBienDich(
                "than_foreach_co_node_job",
                f"than cua {f!r} co node khong chay inline: {job}. Than co "
                "node job phai di qua run con (`body_workflow`, spec 5.9) - "
                "chua ho tro o ban nay.", f)


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

    do_thi_tam = {"nodes": nodes, "edges": ra_edges, "thu_tu": thu_tu}
    _kiem_than_foreach(do_thi_tam)

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


__all__ = ["MAT_NODE", "SCHEMA", "CauTruc", "LoiBienDich", "ThamChieu",
           "bien_dich", "cau_truc", "cong_params_nhan", "doan_bieu_thuc",
           "la_tham_chieu", "trich_tham_chieu"]
