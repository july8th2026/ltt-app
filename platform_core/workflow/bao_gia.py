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
    tool = cc[str(node["type"])[4:]]
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


def bao_gia_do_thi(graph: dict, *,
                   cong_cu: dict[str, CongCu] | None = None) -> BaoGia:
    """Trần tất định của cả đồ thị. GHI `gia_tran` từng node + `bang_gia`."""
    cc = _nguon.tat_ca() if cong_cu is None else cong_cu
    bang: dict[str, int] = {}
    for node in graph.get("nodes") or []:
        gia = _gia_node(node, cc)
        node["gia_tran"] = gia
        bang[str(node["id"])] = gia
    graph["bang_gia"] = bang
    toi_da = sum(bang.values())
    return BaoGia(toi_da=toi_da,
                  uoc_tinh=int(math.ceil(toi_da * _TY_LE_UOC_TINH)))


__all__ = ["KhongBaoGiaDuoc", "BaoGia", "bao_gia_do_thi"]
