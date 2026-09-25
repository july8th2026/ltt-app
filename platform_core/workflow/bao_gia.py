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


def _dinh_nghia_gia_co_dinh(loai: str):
    """`NodeDefinition` của một node piece/connector (không bọc ToolSpec),
    hoặc `None` — dùng riêng để BÁO GIÁ, không dùng cho biên dịch/nộp job.

    ⭐ Import cục bộ + tra CẢ HAI nguồn (`nut_loi` cho `connector.*`,
       `nut.dinh_nghia_piece` cho `piece.*`/`trigger.piece.*`) — cùng cách
       `cau_noi._dinh_nghia` tra, để một node piece báo giá và nộp job đọc
       CÙNG một `NodeDefinition`, không phải hai bản dò khác nhau.

    ⛔ Chỉ trả về khi `job_type` nằm trong `JOB_TYPE_KHONG_TOOLSPEC`: một
       node lõi khác có `thi_hanh="job"` (`ai.llm`…) vẫn phải đi đường
       `cc.get(...)` cũ — hàm này không đụng tới giá của chúng.
    """
    from platform_core.workflow import nut, nut_loi

    nd = nut_loi.tat_ca().get(loai)
    if nd is None:
        nd = nut.dinh_nghia_piece(loai)
    if nd is not None and nd.job_type in nut.JOB_TYPE_KHONG_TOOLSPEC:
        return nd
    return None


def _gia_node(node: dict, cc: dict[str, CongCu]) -> int:
    if str(node.get("type")) == LOAI_GOI_WF:
        # §7.2: *"subworkflow: `estimated_max` của version con"*.
        # ⛔ Con số này KHÔNG đến từ `params` của client: cổng publish từ
        #    chối `gia_con` trong draft (`additionalProperties: false`) và
        #    `dinh_nghia.xuat_ban_draft` GHI ĐÈ nó từ CSDL sau khi ghim
        #    `version_id`. Cùng lý do đã ghi ở đầu tệp: một trường trong
        #    body của người gọi không thể là nguồn của con số giữ tiền
        #    của chính người gọi ấy.
        gia = (node.get("params") or {}).get("gia_con")
        if not isinstance(gia, int) or isinstance(gia, bool) or gia < 0:
            raise KhongBaoGiaDuoc(
                f"{node.get('id')}: thieu `gia_con` da ghim -- do thi nay "
                "chua di qua `xuat_ban_draft`, khong co chan tren")
        return gia
    if str(node.get("type")) == LOAI_AGENT:
        # §12.3: *"Trần báo giá node = `ngan_sach_credit`"*.
        #
        # ⚠️ KHÁC `gia_con` ở trên, và khác có lý do. `gia_con` đến từ CSDL vì
        #    một trường trong body của người gọi sẽ là cách **né** trần của
        #    chính họ. `ngan_sach_credit` thì ngược chiều: khai to nghĩa là bị
        #    GIỮ nhiều hơn, nên nó tự hạn chế. Nó là lời khai *"tôi cho phép
        #    lượt này tiêu tới đây"*, và `tac_tu._mo_buoc` không mở bước nào
        #    vượt qua con số ấy.
        gia = (node.get("params") or {}).get("ngan_sach_credit")
        if not isinstance(gia, int) or isinstance(gia, bool) or gia < 1:
            raise KhongBaoGiaDuoc(
                f"{node.get('id')}: `ngan_sach_credit` phai la so nguyen >= 1 "
                "-- khong co no thi luot agent khong co chan tren")
        return gia
    if node.get("thi_hanh") != "job":
        return 0
    nd_co_dinh = _dinh_nghia_gia_co_dinh(str(node["type"]))
    if nd_co_dinh is not None:
        # Node `piece.*`/`connector.*` (nguồn 1 + 3, spec §4.5): KHÔNG bọc
        # ToolSpec — `cc.get(...)` bên dưới sẽ luôn `None` cho chúng (và
        # `str(type)[4:]` giả định tiền tố `"app."` sai hình dạng với
        # `"piece."`/`"connector."`). Giá lấy TỪ `NodeDefinition.gia`, CÙNG
        # con số mà `cau_noi._nop_job_connector` dùng để tính `gia_that` —
        # hai chỗ đọc một nguồn, không phải hai bản sao.
        return int(nd_co_dinh.gia.so) if nd_co_dinh.gia.kieu == "co_dinh" else 0
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
LOAI_GOI_WF = "core.call_workflow"
#: `ai.agent` (spec §12.3). Hằng ở đây chứ không import `tac_tu` để tránh vòng
#: import: `tac_tu` gọi `bao_gia`, không chiều ngược lại.
LOAI_AGENT = "ai.agent"
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


def than_foreach(graph: dict) -> dict[str, tuple[str, tuple[str, ...]]]:
    """`{id foreach: (id foreach_end, thân theo `graph.thu_tu`)}`.

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

    thu_tu = [str(k) for k in (graph.get("thu_tu") or nodes)]
    ra: dict[str, tuple[str, tuple[str, ...]]] = {}
    for nid, n in nodes.items():
        if str(n.get("type")) != LOAI_FOREACH:
            continue
        dong = ket.get(nid)
        if dong is None:
            raise KhongBaoGiaDuoc(
                f"{nid}: {LOAI_FOREACH!r} khong co {LOAI_FOREACH_END!r} nao dong "
                "lai -- khong biet than ket thuc o dau thi khong co chan tren")
        than = (_lan(nid, xuoi) & _lan(dong, nguoc)) - {nid, dong}
        ra[nid] = (dong, tuple(k for k in thu_tu if k in than))
    return ra


def hau_due(graph: dict, node_id: str) -> frozenset[str]:
    """`node_id` **và** mọi node tới được từ nó (spec §14, "chạy lại từ node").

    ⭐ Dùng lại `_ke`/`_lan` — cùng một phép duyệt đồ thị mà `than_foreach`
       đã dùng. Một BFS thứ hai cho cùng câu hỏi "tới được từ đâu" là một bản
       sao sẽ trôi khỏi bản gốc, và ngày nó trôi thì "node nào phải chạy lại"
       và "node nào nằm trong thân vòng" trả lời theo hai cấu trúc khác nhau.

    ⚠️ Hàm này cũng đọc đồ thị **chưa** qua validator publish (đồ thị của một
       run cũ, một bản nháp), nên nó phải chịu được chu trình. `_lan` có tập
       `da` nên không treo — phép kiểm `test_3452::test_chu_trinh_khong_treo`
       chốt điều đó, vì treo ở đây là treo cả một cửa HTTP.
    """
    nid = str(node_id or "")
    if nid not in {str(n["id"]) for n in graph.get("nodes") or []}:
        raise KhongBaoGiaDuoc(f"{nid!r} khong co trong do thi")
    xuoi, _ = _ke(graph)
    return frozenset(_lan(nid, xuoi) | {nid})


def co_the_tai_dung(graph: dict, node_id: str) -> tuple[str, ...]:
    """Node được phép **sao output** từ run cũ khi chạy lại từ `node_id`.

    = mọi node **trừ** hậu duệ của `node_id` (spec §14: *"sao output các node
    không phải hậu duệ của node chọn"*), theo đúng `graph.thu_tu`.

    ⛔ **Thân `foreach` — và chính cặp `foreach`/`foreach_end` — không bao giờ
       nằm trong tập này.** Ảnh chụp của một node thân khoá theo **đường thi
       hành** (`f:0/x`, `f:1/x`… — `thi_hanh.khoa_node`), và đường ấy bị **băm**
       khi vượt 64 ký tự (`danh_thuc.duong_thi_hanh`), lúc đó không suy ngược
       được (P9 task 3). "Sao output của x" khi x chạy N lần dưới N khoá, có
       khoá không đọc ngược được, là một phép sao **không xác định** — và tái
       dùng sai một output nghĩa là trả cho khách kết quả của một lần chạy
       khác. Giữa "chạy lại, tốn thêm tiền, đúng" và "đoán, rẻ hơn, có thể
       sai", chỗ này chọn cái đầu.

    ⚠️ Hàm này KHÔNG hỏi run cũ. Nó trả **ứng viên theo đồ thị**; bên gọi còn
       phải loại node chưa từng `SUCCEEDED` ở run cũ — một node `FAILED`
       không có output nào để sao.
    """
    bo = set(hau_due(graph, node_id))
    for goc, (dong, than) in than_foreach(graph).items():
        bo.update({goc, dong, *than})
    nodes = {str(n["id"]) for n in graph.get("nodes") or []}
    thu_tu = [str(k) for k in (graph.get("thu_tu") or sorted(nodes))]
    return tuple(k for k in thu_tu if k in nodes and k not in bo)


def he_so_lap(graph: dict) -> dict[str, int]:
    """Số lượt TỐI ĐA mỗi node chạy trong một lượt chạy của đồ thị.

    Thân vòng lặp đọc từ `than_foreach` — **một** nguồn cho câu hỏi *"node nào
    nằm trong thân nào"*. Động cơ (`nut_loi/vong_lap.py`) hỏi đúng chỗ ấy: một
    bản sao của luật thân là một bản sao sẽ trôi, và ngày nó trôi thì con số
    tiền và thứ thật sự chạy nói hai chuyện khác nhau.
    """
    nodes = {str(n["id"]): n for n in graph.get("nodes") or []}
    he_so: dict[str, int] = dict.fromkeys(nodes, 1)
    for nid, (_dong, than) in than_foreach(graph).items():
        lan = _max_items(nodes[nid])
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


@dataclass(frozen=True)
class BangGiaSong:
    """Bang gia cho mot ban nhap **dang go** — mot cua cho ca do thi.

    `gia`         {node_id: tran credit cua MOT luot chay}
    `loi`         {node_id: vi sao node ay chua bao gia duoc}
    `loi_do_thi`  `{"ma","thong_diep","node_id"}` khi ca CAU TRUC chua dung
                  (id trung, chu trinh, canh tro vao hu khong) — luc do `gia`
                  rong va giao dien xoa bang gia.
    """

    gia: dict[str, int]
    loi: dict[str, str]
    loi_do_thi: dict[str, str] | None = None


def bang_gia_song(document: dict, *,
                  cong_cu: dict[str, CongCu] | None = None) -> BangGiaSong:
    """Bao gia TUNG node cua mot ban nhap, trong MOT luot.

    ⭐ VI SAO CO HAM NAY, VA VI SAO NO KHONG PHAI DUONG GIA THU HAI

    Trinh soan can mot con so cho **moi** node trong khi nguoi ta go. Truoc
    24/09 no lay bang cach goi `/agent/api/tools/{ten}/quote` **mot lan moi
    node**: do thi 12 node = 12 request moi lan bung. Ham nay gop lai thanh
    MOT luot, va — quan trong hon — no goi thang `_gia_node`, **dung ham ma
    `bao_gia_do_thi` goi**. Khong co phep nhan nao rieng o day.

    ⛔ Khac `bao_gia_do_thi` o dung HAI diem, ca hai deu vi "dang go":
       1. **Khoan dung**: mot node chua du tham so chi mat gia CUA NO; ca bang
          khong bien mat. `bao_gia_do_thi` phai nem cho ca do thi vi no dung o
          cong publish, noi mot node khong co chan tren la mot run khong co
          chan tren.
       2. **Khong ghi gi vao `document`**: `bao_gia_do_thi` GHI `gia_tran`,
          `bang_gia`, `he_so_lap` vao do thi no nhan. Ban nhap o day la tai
          lieu cua nguoi dung dang go — de lai dau vet trong do la doi mot thu
          se duoc autosave gui nguoc len may chu.

    ⚠️ **Pham vi**: tra tran cua MOT luot chay tung node (dung thu Inspector
       hien). `he_so_lap` cua `foreach` va tong cua ca run thuoc `/publish`.
    """
    from platform_core.workflow import bien_dich

    cc = _nguon.tat_ca() if cong_cu is None else cong_cu
    try:
        # `nghiem=False`: mot bieu thuc go do khong duoc lam mat bang gia cua
        # chinh nguoi dang go — cung ly do cua `goi_y.py`.
        ct = bien_dich.cau_truc(document, cong_cu=cc, nghiem=False)
    except bien_dich.LoiBienDich as loi_bd:
        # ⛔ Ten khac `loi` ben duoi CO Y: hai thu KHAC LOAI (mot ngoai le bien
        #    dich, mot bang loi theo node) tung dung chung mot ten. Python XOA
        #    ten da bind trong `except` khi ra khoi khoi, nen mypy bao
        #    "Trying to read deleted variable" o hai dong duoi — dung ve co hoc,
        #    va dung ca ve nguoi doc.
        return BangGiaSong(gia={}, loi={}, loi_do_thi={
            "ma": loi_bd.ma, "thong_diep": str(loi_bd),
            "node_id": loi_bd.node_id})

    gia: dict[str, int] = {}
    loi: dict[str, str] = {}
    for node in ct.nodes:
        nid = str(node["id"])
        try:
            gia[nid] = _gia_node(node, cc)
        except KhongBaoGiaDuoc as vi_sao:
            loi[nid] = str(vi_sao)
    return BangGiaSong(gia=gia, loi=loi)


__all__ = ["HE_SO_LAP_TOI_DA", "LOAI_FOREACH", "LOAI_FOREACH_END",
           "MAX_ITEMS_TRAN", "BangGiaSong", "KhongBaoGiaDuoc", "BaoGia",
           "bang_gia_song", "bao_gia_do_thi",
           "co_the_tai_dung", "hau_due", "he_so_lap", "than_foreach"]
