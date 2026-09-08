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
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.workflow.dieu_khien import sinh_job


class KhongBaoGiaDuoc(ValueError):
    """Đồ thị này không có chặn trên ⇒ không báo giá được.

    ⛔ **Từ chối, đừng đoán một con số.** Một trần chi phí đoán ra là một trần
       không chặn gì — nó chỉ làm người đọc yên tâm.
    """


@dataclass(frozen=True)
class BaoGia:
    toi_da: int
    uoc_tinh: int


#: Giá quy ước mỗi node sinh job, dùng khi node chưa khai giá thật. Đây là chỗ
#: `ToolSpec.gia` sẽ cắm vào ở Đợt 5 — hằng số này là **giàn giáo**, không phải
#: bảng giá, nên nó cố tình KHÔNG mang tên của app nào.
_GIA_MAC_DINH = 10

#: Tỷ lệ ước tính so với trần. `INFERRED` — chưa có dữ liệu để hiệu chỉnh, và
#: nó phải được đo lại bằng `actual_cost` thật ngay khi có lượt chạy đầu tiên.
_TY_LE_UOC_TINH = 0.6


def _gia_node(node: dict) -> int:
    if not sinh_job(str(node.get("type", ""))):
        return 0
    return int(node.get("params", {}).get("gia", _GIA_MAC_DINH))


def _tran_danh_sach(nodes: list) -> int:
    return sum(_tran_node(n) for n in nodes or [])


def _tran_node(node: dict) -> int:
    """Chặn trên của MỘT node, kể cả khi nó chứa thân hoặc nhánh."""
    loai = str(node.get("type", ""))

    if loai == "FOREACH":
        max_items = node.get("params", {}).get("max_items")
        if not max_items or int(max_items) <= 0:
            raise KhongBaoGiaDuoc(
                f"node {node.get('id')!r}: FOREACH phai khai `max_items` huu "
                "han — khong co chan tren thi khong co tran chi phi")
        return int(max_items) * _tran_danh_sach(node.get("than", []))

    if "nhanh" in node:
        # ⭐ Chi MOT nhanh chay, nhung ta khong biet nhanh nao. Tran la CHAN
        #    TREN, nen lay nhanh DAT NHAT — khong phai tong (qua cao, doa
        #    khach), khong phai trung binh (khong con la chan tren).
        return max((_tran_danh_sach(nh) for nh in node["nhanh"]), default=0)

    return _gia_node(node)


def uoc_tinh(graph: dict) -> BaoGia:
    """Hai số cho một đồ thị: chặn trên **tất định**, và một ước tính.

    ⚠️ `toi_da` phải tất định — cùng một đồ thị luôn ra cùng một số, kể cả khi
       chạy trên máy khác. Nó bị **đóng băng cùng `graph_hash`** vào
       `workflow_version.estimated_max`, nên một con số phụ thuộc môi trường sẽ
       làm hai lần publish cùng nội dung ra hai trần khác nhau.
    """
    toi_da = _tran_danh_sach(graph.get("nodes", []))
    return BaoGia(toi_da=toi_da, uoc_tinh=int(toi_da * _TY_LE_UOC_TINH))
