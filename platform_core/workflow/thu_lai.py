"""Retry CẤP NODE — một **lớp mỏng** trên retry của `jobs.py` (spec §5.6).

⛔ KHÔNG DỰNG CƠ CHẾ THỨ HAI. `platform_core/jobs.py` đã có cả bốn mảnh:
backoff mũ (`fail()`), `max_attempts`, `dedupe_key`, `reclaim_orphans`. Một bộ
đếm/lịch thứ hai ở tầng workflow là một chỗ thứ hai để hai con số lệch nhau —
và con số lệch ấy là **tiền** và **side effect**.

⇒ Tệp này không tính backoff. Nó **gọi** `jobs.gian_cach_retry`.

Ranh giới, đúng chữ spec §5.6:

    Job giữ nguyên retry của nó (`max_attempts`, backoff mũ, reclaim).
    **Retry node** chỉ xảy ra khi job đã kết thúc ERROR:
    `settings.retry = {max ≤ 5, backoff_s}`, mặc định `{max: 0}`.

## 🔴 Vì sao một lượt thử lại KHÔNG phá trần chi phí

`bao_gia.he_so_lap` nhân trần theo `max_items` của `foreach`, **không** theo
`retry.max` — và điều đó đúng, không phải một chỗ bỏ sót: một lượt hỏng không
ghi `cost_credit` (`cau_noi.ap_ket_qua` chỉ cộng `run.actual_cost` ở nhánh
`SUCCEEDED`, `test_1718::test_job_loi_khong_tinh_tien`). Một node thành công
**nhiều nhất một lần**, nên tổng thật vẫn nằm dưới trần đã giữ.

⚠️ Ngày nào một lượt hỏng bắt đầu bị thu tiền, câu trên hết đúng và
   `he_so_lap` phải nhân thêm `retry.max + 1`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Sequence

from platform_core import jobs
from platform_core.workflow import danh_thuc, may_trang_thai, thi_hanh

#: §5.6: `max ≤ 5`. Trần này không phải để tiết kiệm máy — nó là chặn trên của
#: số lần một node có side effect `external` gõ cửa provider.
TRAN_SO_LAN = 5

#: Khoá trong `output_ref` của ảnh chụp `RETRY_SCHEDULED` giữ thời điểm được
#: phép quay lại. Nằm trong ảnh chụp (bất biến, có lịch sử) chứ không phải một
#: cột mới: "lượt này hẹn lúc nào" là một sự kiện, không phải một trạng thái.
KHOA_HAN = "_thu_lai_luc"

#: Trạng thái không bao giờ được tự thử lại, dù `settings.retry` nói gì.
#: `ABANDONED` = provider **có thể đã nhận** (`side_effect="irreversible"` +
#: kết quả mơ hồ) ⇒ một lượt thử lại là một side effect thứ hai không đảo được.
#: `CANCELLED` = có người bấm dừng; thử lại là cãi lại họ.
KHONG_THU_LAI = frozenset({"ABANDONED", "CANCELLED", "SUCCEEDED", "SKIPPED"})


class LoiChinhSach(ValueError):
    """`settings.retry` không đọc được ⇒ **từ chối**, không lấy mặc định.

    ⛔ Lặng lẽ rơi về `{max: 0}` khi gặp `{"max": "hai"}` là biến một lỗi gõ
       thành một chính sách — và chính sách ấy nói về side effect.
    """


@dataclass(frozen=True)
class ChinhSach:
    so_lan: int
    backoff_s: int


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def doc_chinh_sach(node: dict) -> ChinhSach:
    """`settings.retry` của một node. Thiếu ⇒ `{max: 0}` (§5.6)."""
    cai = (node.get("settings") or {}).get("retry")
    if cai is None:
        return ChinhSach(so_lan=0, backoff_s=jobs.RETRY_BASE_S)
    if not isinstance(cai, dict):
        raise LoiChinhSach(
            f"{node.get('id')}: `settings.retry` phai la mot object, nhan "
            f"{type(cai).__name__}")
    so_lan = cai.get("max", 0)
    if isinstance(so_lan, bool) or not isinstance(so_lan, int) \
            or not (0 <= so_lan <= TRAN_SO_LAN):
        raise LoiChinhSach(
            f"{node.get('id')}: `retry.max` phai la so nguyen trong "
            f"[0, {TRAN_SO_LAN}] (§5.6) -- nhan {so_lan!r}")
    backoff = cai.get("backoff_s", jobs.RETRY_BASE_S)
    if isinstance(backoff, bool) or not isinstance(backoff, int) or backoff <= 0:
        raise LoiChinhSach(
            f"{node.get('id')}: `retry.backoff_s` phai la so nguyen > 0 -- "
            f"nhan {backoff!r}")
    return ChinhSach(so_lan=so_lan, backoff_s=min(backoff, jobs.RETRY_MAX_S))


def con_luot(node: dict, lan: int) -> bool:
    """Lượt thử thứ `lan` vừa hỏng — còn được thử nữa không?

    `lan` đếm từ 1, nên `retry.max = 2` cho phép lượt 1 và lượt 2 hẹn lại, và
    lượt 3 là lượt cuối.
    """
    return int(lan) <= doc_chinh_sach(node).so_lan


def quyet_dinh(*, sang: str, node: dict, lan: int) -> str:
    """Trạng thái THẬT SỰ ghi cho node sau khi job kết thúc không thành công.

    ⛔ `KHONG_THU_LAI` thắng `settings.retry`, không phải ngược lại: chính sách
       của người soạn workflow không được phép bật lại một luật về side effect
       không đảo được (§5.6).
    """
    if sang in KHONG_THU_LAI or sang != "FAILED":
        return sang
    return "RETRY_SCHEDULED" if con_luot(node, lan) else "FAILED"


def hen(db, *, run_id: str, node: dict, lan: int,
        vong: Sequence[tuple[str, int]] = ()) -> datetime:
    """Hẹn lượt thử kế và trả về hạn. Khoá đi qua **đường thi hành** (Task 1).

    ⚠️ `vong` là ngữ cảnh vòng lặp của lượt chạy này. Truyền `()` cho node ngoài
       mọi `foreach`; thân `foreach` phải truyền đúng `(tên_vòng, chỉ_số)` —
       nếu không, hai vòng lặp cùng hẹn một khoá và vòng 2 đè timer vòng 1
       (`danh_thuc.duong_thi_hanh`).
    """
    cs = doc_chinh_sach(node)
    # ⛔ KHÔNG tự tính `base * 2 ** (lan - 1)` ở đây. Một công thức thứ hai cho
    #    cùng ý nghĩa là hai con số sẽ trôi khỏi nhau — `jobs.py` là nguồn.
    han = _bay_gio() + timedelta(seconds=jobs.gian_cach_retry(
        lan, base=cs.backoff_s))
    danh_thuc.hen_node(db, run_id=run_id, node_id=str(node["id"]),
                       kind="retry", due_at=han, vong=vong)
    return han


def den_han(db, run_id: str, nodes: Iterable[dict], *,
            bay_gio: Optional[datetime] = None) -> int:
    """`RETRY_SCHEDULED` đã tới hạn ⇒ `READY`. Trả về số node đã đưa về.

    ⭐ Giữ nguyên `attempt_number` mà lượt hẹn đã ghi: `cau_noi.nop_job` đọc
       đúng con số ấy để dựng `_khoa_idem`. Với `side_effect="none"` khoá đổi
       theo lượt (job mới, không bị khử trùng); với `external` khoá **giữ
       nguyên** theo `idempotency_fields` — đúng §5.6 *"RETRY_SCHEDULED với
       cùng idempotency_key"*.
    """
    luc = bay_gio or _bay_gio()
    dem = 0
    for node in nodes:
        nid = str(node["id"])
        anh = thi_hanh.anh_chup_hien_tai(db, run_id, nid)
        if anh is None or anh.execution_status != "RETRY_SCHEDULED":
            continue
        han = (anh.output_ref or {}).get(KHOA_HAN)
        if han and datetime.fromisoformat(str(han)) > luc:
            continue
        if may_trang_thai.chuyen_node(
                db, run_id, nid, sang="READY", mo_ta="den han thu lai",
                attempt_number=int(anh.attempt_number or 1)):
            dem += 1
    return dem


__all__ = ["KHOA_HAN", "KHONG_THU_LAI", "TRAN_SO_LAN", "ChinhSach",
           "LoiChinhSach", "con_luot", "den_han", "doc_chinh_sach", "hen",
           "quyet_dinh"]
