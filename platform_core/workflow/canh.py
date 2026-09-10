"""Middleware trên CẠNH — ba điểm cắm quanh mỗi lượt truyền.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §6` (bài học
Node-RED, 6 hook; ta lấy 3).

    before_route  ->  before_dispatch  ->  after_dispatch

Hook trả `False` (hoặc ném lỗi) thì **chặn**, và các hook sau **không chạy**.

🔴 Vì sao có tầng này thay vì một `if` trong scheduler — hai lý do đo được:

  `WF-903`  quyen phai kiem LUC THI HANH. `validate_plan` loc theo `app_access`
            (dung), nhung mot `WorkflowVersion` DA PUBLISH co the chay SAU khi
            quyen bi thu hoi. Version la BAT BIEN — do la tinh chat ta MUON
            (tai dung duoc), va chinh no tao ra lo nay.
  `WF-905`  phai do duoc scheduler tu tieu bao nhieu. Moi luat quyen/do/gioi
            han nhet thang vao loi la mot nhanh nua trong thu ta dang co giu
            nho.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

log = logging.getLogger(__name__)

#: Ba điểm cắm, theo đúng thứ tự chạy. Là `tuple` chứ không phải `set`: thứ tự
#: là một phần của hợp đồng, không phải chi tiết cài đặt.
DIEM_CAM = ("before_route", "before_dispatch", "after_dispatch")

Hook = Callable[[dict], Any]

_SO: dict[str, list[Hook]] = {ten: [] for ten in DIEM_CAM}


def dang_ky(diem: str, hook: Hook) -> None:
    """Cắm một hook vào một điểm.

    ⛔ Tên điểm sai bị từ chối **ngay**, không im lặng bỏ qua. Một hook gắn vào
       một điểm không tồn tại là một hook **không bao giờ chạy** — và nếu nó là
       hook kiểm quyền thì đó là một cổng mở mà không ai thấy. Ném lỗi ở đây
       biến một lỗi im lặng thành một lỗi ồn ào, tại đúng chỗ người viết đang
       nhìn.
    """
    if diem not in _SO:
        raise ValueError(
            f"diem cam khong ton tai: {diem!r}. Hop le: {', '.join(DIEM_CAM)}")
    _SO[diem].append(hook)


def xoa_het_hook() -> None:
    """Dọn sổ. Dùng trong test — sổ hook là trạng thái **toàn cục**."""
    for ten in DIEM_CAM:
        _SO[ten].clear()


def hook_dang_cam(diem: str) -> tuple[Hook, ...]:
    return tuple(_SO.get(diem, ()))


def truyen(db, canh: dict, *, ngu_canh: dict) -> bool:
    """Chạy một lượt truyền qua `canh`. Trả `False` nếu bị chặn.

    `ngu_canh` là **đường truyền giữa các hook**: hook trước ghi vào đó, hook
    sau đọc được. Không có nó thì mỗi hook phải tự đo lại cùng một thứ.

    ⛔ **Fail-CLOSED khi hook ném lỗi.** Đây là chỗ cắm của kiểm quyền, nên một
       hook lỗi mà ta cho đi tiếp là **mở cổng khi bộ gác ngã**. Nuốt lỗi rồi
       trả `True` là đúng loại khiếm khuyết mà `check_nuot_loi` của kho này
       sinh ra để bắt — ở đây ta bắt nó, ghi log, và **chặn**.

    ⚠️ `after_dispatch` cũng chặn được, và đó là chủ ý: nó là chỗ một hook đo
       lường hoặc kiểm hậu điều kiện có thể nói *"lượt truyền này không hợp lệ"*.
       Nhưng bên gọi phải hiểu rằng tới lúc ấy việc đã chạy — nó là **phán
       quyết**, không phải **ngăn chặn**.
    """
    ngu_canh.setdefault("canh", canh)
    for diem in DIEM_CAM:
        for hook in _SO[diem]:
            try:
                ket_qua = hook(ngu_canh)
            except Exception as loi:                      # noqa: BLE001
                log.warning("hook %s hong o cach %s: %s", diem,
                            canh.get("id", "?"), loi)
                ngu_canh.setdefault("ly_do_chan", f"hook {diem} hong: {loi}")
                return False
            if ket_qua is False:
                ngu_canh.setdefault(
                    "ly_do_chan", f"hook {diem} tu choi luot truyen")
                return False
    return True
