"""Trần chi phí tất định — báo giá kèm HAI SỐ (`WF-501`, `M8`).

⚠️ **MỤC NÀY KHÔNG CÓ ĐỐI CHỨNG NGÀNH** (`23_24 §7`, sổ nợ `N1`).

    "khong kho nao co tran chi phi; buoc cua ho gan nhu mien phi"

Bảy kho khảo sát — Activepieces, n8n, Node-RED, Kestra, Windmill, Trigger.dev,
Temporal — **không kho nào** lập lịch quanh một hoá đơn. Bước của họ là gọi HTTP
và biến đổi dữ liệu; bước của ta là một lượt GPU.

⇒ Nghĩa là mọi quyết định ở tệp này là **`INFERRED`**, không phải `CONFIRMED`.
  Nó phải có bộ test riêng, và **không được coi là an toàn vì "ngành làm thế"**.

🔴 `M8` — vì sao **hai** số chứ không phải một: một số duy nhất buộc phải chọn
   giữa hai cách nói sai. Nói số tối đa thì khách thấy đắt và bỏ đi; nói số ước
   tính thì khách bị bất ngờ khi bị trừ nhiều hơn. Hai số nói đúng thứ ta biết:
   *"thường khoảng X, không bao giờ quá Y"*.

## Giá lấy từ registry (Task 6, audit 22/09), không từ `params.gia` của client

Client gửi `params.gia` là chuyện đã lộ ở audit: một trường trong body của
người gọi không thể là nguồn của một con số nền tảng dùng để giữ tiền của
chính người gọi ấy. Giá thật đến từ `CongCu.tinh_gia` — cùng registry mà
`bien_dich` dùng để xác nhận node có tồn tại. Tham số **literal** thì tính
đúng giá trị đó; tham số là **tham chiếu** `{{ }}` (chưa biết giá trị thật cho
tới lúc chạy) thì thử biên trên của `params_schema` (giá `enum` lớn nhất, `max`
của `int`/`number`) — vẫn là một trần **tất định**, không phải một phỏng đoán.
Chốt tiền thật vẫn ở cầu nối lúc chạy: `gia_that > gia_tran` thì node đó FAILED
`vuot_tran_bao_gia` (Task 9) — không bao giờ thu quá khoản đã giữ.
"""
from __future__ import annotations

import itertools
import math
from collections import deque
from dataclasses import dataclass

from platform_core.workflow import cong_cu as _nguon
from platform_core.workflow.bien_dich import la_tham_chieu
from platform_core.workflow.cong_cu import CongCu


class KhongBaoGiaDuoc(ValueError):
    """Đồ thị này không có chặn trên ⇒ không báo giá được.

    ⛔ **Từ chối, đừng đoán một con số.** Một trần chi phí đoán ra là một trần
       không chặn gì — nó chỉ làm người đọc yên tâm.
    """


@dataclass(frozen=True)
class BaoGia:
    toi_da: int
    uoc_tinh: int


#: Tỷ lệ ước tính so với trần. `INFERRED` — chưa có dữ liệu để hiệu chỉnh, và
#: nó phải được đo lại bằng `actual_cost` thật ngay khi có lượt chạy đầu tiên.
_TY_LE_UOC_TINH = 0.6

#: Chặn nổ tổ hợp: một node có quá nhiều tham số tham chiếu không biên (mỗi
#: cái đều là `enum`/`int` với nhiều ứng viên) có thể sinh tích số khổng lồ.
#: `KhongBaoGiaDuoc` — từ chối, không phải tính rồi treo request.
_TO_HOP_TOI_DA = 256


def _ung_vien(khoa: str, schema: dict) -> list:
    muc = schema.get(khoa) or {}
    kieu = str(muc.get("type", ""))
    if kieu == "enum" and isinstance(muc.get("values"), list) and muc["values"]:
        return list(muc["values"])
    if kieu in ("int", "number") and muc.get("max") is not None:
        return [muc["max"]]
    return []            # không biên ⇒ tính theo mặc định (bỏ khoá)


def _gia_node(node: dict, cc: dict[str, CongCu]) -> int:
    if node.get("thi_hanh") != "job":
        return 0
    ten_cong_cu = str(node["type"])[4:]
    tool = cc.get(ten_cong_cu)
    if tool is None:
        raise KhongBaoGiaDuoc(
            f"{node.get('id')}: khong co cong cu {ten_cong_cu!r} trong registry")
    params = dict(node.get("params") or {})
    dong = [k for k, v in params.items()
            if la_tham_chieu(v) is not None
            or (isinstance(v, str) and "{{" in v)]
    co_dinh = {k: v for k, v in params.items() if k not in dong}
    truc = [(k, _ung_vien(k, tool.params_schema)) for k in dong]
    truc = [(k, vs) for k, vs in truc if vs]

    tich = 1
    for _k, vs in truc:
        tich *= len(vs)
    if tich > _TO_HOP_TOI_DA:
        raise KhongBaoGiaDuoc(f"{node.get('id')}: qua nhieu to hop tham so")

    to_hop = itertools.product(*(vs for _k, vs in truc)) if truc else [()]
    cao = 0
    for bo in to_hop:
        thu = dict(co_dinh)
        thu.update({k: v for (k, _vs), v in zip(truc, bo, strict=True)})
        try:
            cao = max(cao, int(tool.tinh_gia(thu)))
        except Exception as loi:                      # noqa: BLE001
            raise KhongBaoGiaDuoc(f"{node['id']}: {loi}") from loi
    return cao


#: §5.9: `max_items` **bắt buộc** và `≤ 1000`. Con số ấy là toàn bộ lý do trần
#: của một `foreach` **tồn tại** — không có chặn trên thì phép nhân dưới đây
#: không có số để nhân.
MAX_ITEMS_TRAN = 1000

#: Trần của tích các `max_items` lồng nhau. Hai tầng đầy (1000 × 1000) vừa khít;
#: tầng thứ ba thì con số báo cho khách không còn là một trần mà là một lời từ
#: chối viết bằng chữ số. Nói thẳng ra bằng `KhongBaoGiaDuoc` trung thực hơn.
HE_SO_LAP_TOI_DA = 1_000_000

LOAI_FOREACH = "core.foreach"
LOAI_FOREACH_END = "core.foreach_end"


def _ke(graph: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    xuoi: dict[str, list[str]] = {str(n["id"]): [] for n in graph.get("nodes") or []}
    nguoc: dict[str, list[str]] = {k: [] for k in xuoi}
    for e in graph.get("edges") or []:
        a, b = str(e["source_node"]), str(e["target_node"])
        if a in xuoi and b in nguoc:
            xuoi[a].append(b)
            nguoc[b].append(a)
    return xuoi, nguoc


def _lan(goc: str, ke: dict[str, list[str]]) -> set[str]:
    """Tập tới được từ `goc` (KHÔNG kể `goc`). Có `da` nên chu trình không treo."""
    da: set[str] = set()
    hang = deque(ke.get(goc, ()))
    while hang:
        k = hang.popleft()
        if k in da:
            continue
        da.add(k)
        hang.extend(ke.get(k, ()))
    return da


def _max_items(node: dict) -> int:
    gia_tri = (node.get("params") or {}).get("max_items")
    if isinstance(gia_tri, bool) or not isinstance(gia_tri, int):
        raise KhongBaoGiaDuoc(
            f"{node.get('id')}: `max_items` bat buoc va phai la so nguyen "
            f"(§5.9) -- nhan {gia_tri!r}")
    if not (0 < gia_tri <= MAX_ITEMS_TRAN):
        raise KhongBaoGiaDuoc(
            f"{node.get('id')}: `max_items` phai trong (0, {MAX_ITEMS_TRAN}] "
            f"(§5.9) -- nhan {gia_tri}")
    return gia_tri


def he_so_lap(graph: dict) -> dict[str, int]:
    """Số lượt TỐI ĐA mỗi node chạy trong một lượt chạy của đồ thị.

    🔴 VÌ SAO HÀM NÀY TỒN TẠI — một nợ đã ĐO, không phải một tinh chỉnh.

       `_gia_node` trả 0 cho mọi node không `thi_hanh == "job"`, và tổng của đồ
       thị là một phép cộng phẳng. Nên một node app **trong thân** một `foreach`
       `max_items=1000` được báo giá **một** lần và chạy **một nghìn** lần. Trần
       khi đó không chặn gì; nó chỉ làm người đọc yên tâm — đúng thứ
       `KhongBaoGiaDuoc` được viết ra để từ chối.

    Luật: spec §7.2 — *"ForEach: `max_items × trần thân"*. Thân = chuỗi node
    nằm giữa `core.foreach` và `core.foreach_end` (§5.9), đọc bằng cấu trúc đồ
    thị: `tới-được-từ(foreach) ∩ tới-được-tới(foreach_end)`.

    ⚠️ Cặp `foreach`/`foreach_end` khớp nhau bằng `params.foreach` của node
       `foreach_end` — **khai tường minh**, không đoán theo vị trí. Một cặp
       đoán ra là một thân đoán ra, và thân là thứ nhân lên con số tiền.

    ⛔ Thiếu `foreach_end` ⇒ `KhongBaoGiaDuoc`. Không biết thân kết thúc ở đâu
       nghĩa là không có chặn trên; đoán một con số ở đây là in ra một trần
       không chặn gì.
    """
    nodes = {str(n["id"]): n for n in graph.get("nodes") or []}
    xuoi, nguoc = _ke(graph)
    ket: dict[str, str] = {}
    for nid, n in nodes.items():
        if str(n.get("type")) != LOAI_FOREACH_END:
            continue
        cua = str((n.get("params") or {}).get("foreach") or "")
        chu = nodes.get(cua)
        if chu is None or str(chu.get("type")) != LOAI_FOREACH:
            raise KhongBaoGiaDuoc(
                f"{nid}: `params.foreach` phai tro vao mot node {LOAI_FOREACH!r} "
                f"co that -- nhan {cua!r}")
        if cua in ket:
            raise KhongBaoGiaDuoc(
                f"{cua}: co hai node {LOAI_FOREACH_END!r} cung dong mot vong "
                f"({ket[cua]}, {nid}) -- than khong xac dinh")
        ket[cua] = nid

    he_so: dict[str, int] = dict.fromkeys(nodes, 1)
    for nid, n in nodes.items():
        if str(n.get("type")) != LOAI_FOREACH:
            continue
        dong = ket.get(nid)
        if dong is None:
            raise KhongBaoGiaDuoc(
                f"{nid}: {LOAI_FOREACH!r} khong co {LOAI_FOREACH_END!r} nao dong "
                "lai -- khong biet than ket thuc o dau thi khong co chan tren")
        lan = _max_items(n)
        than = (_lan(nid, xuoi) & _lan(dong, nguoc)) - {nid, dong}
        for k in than:
            he_so[k] *= lan
    qua = [k for k, v in he_so.items() if v > HE_SO_LAP_TOI_DA]
    if qua:
        raise KhongBaoGiaDuoc(
            f"he so lap cua {sorted(qua)} vuot {HE_SO_LAP_TOI_DA} -- tran tinh "
            "ra khong con la mot tran, hay giam `max_items` hoac bot mot tang "
            "vong lap")
    return he_so


def bao_gia_do_thi(graph: dict, *,
                   cong_cu: dict[str, CongCu] | None = None) -> BaoGia:
    """Trần tất định của cả đồ thị. GHI `gia_tran` từng node + `bang_gia`."""
    cc = _nguon.tat_ca() if cong_cu is None else cong_cu
    bang: dict[str, int] = {}
    for node in graph.get("nodes") or []:
        gia = _gia_node(node, cc)
        # ⛔ `gia_tran` của TỪNG node giữ nguyên trần của MỘT lượt chạy — hệ số
        #    lặp KHÔNG được nhân vào đây. `cau_noi.nop_job` so `gia_that >
        #    node["gia_tran"]` cho mỗi lượt nộp job; nhân nó lên `max_items` là
        #    nới đúng cái cổng ấy ra `max_items` lần, và một node đắt gấp năm
        #    lần dự kiến sẽ đi lọt trong MỌI lượt. Hệ số thuộc về TỔNG của run.
        node["gia_tran"] = gia
        bang[str(node["id"])] = gia
    he_so = he_so_lap(graph)
    graph["bang_gia"] = bang
    graph["he_so_lap"] = he_so
    toi_da = sum(gia * he_so.get(nid, 1) for nid, gia in bang.items())
    return BaoGia(toi_da=toi_da,
                  uoc_tinh=int(math.ceil(toi_da * _TY_LE_UOC_TINH)))


__all__ = ["HE_SO_LAP_TOI_DA", "MAX_ITEMS_TRAN", "KhongBaoGiaDuoc",
           "BaoGia", "bao_gia_do_thi", "he_so_lap"]
