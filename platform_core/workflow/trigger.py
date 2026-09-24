"""Trigger — mỗi loại là một MÔ-ĐUN, không phải một nhánh `if` trong lõi (`G42`).

Bài học Windmill: **11 crate trigger**, không phải 11 nhánh trong một hàm.
Ngưỡng của `G42`: **thêm loại thứ tư (thứ năm, thứ sáu) không sửa
`platform_core`**.

⭐ Đây là cùng khuôn với hợp đồng app của kho này: nền tảng **không biết tên**
   loại nào cả, nó chỉ biết *một loại trigger phải trả lời được hai câu*:

     toi_han(cau_hinh, bay_gio)      -> bool
     lan_ke_tiep(cau_hinh, bay_gio)  -> datetime | None

   Ai muốn thêm `NHIP_TIM` hay `GIT_PUSH` thì viết một lớp hai phương thức và
   `dang_ky()`. Lõi không đổi một dòng.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from sqlalchemy import select

from platform_core.models import WorkflowTrigger

#: Hạn mức webhook (spec §7.3 `WF_WEBHOOK_MOI_PHUT_MOI_TRIGGER`). Một hằng ở
#: đây chứ không một bảng cấu hình: spec nói nó **đổi được không cần deploy mã**
#: nhưng kho này chưa có kho settings chạy-được, và một bảng giả vờ đổi được
#: tệ hơn một hằng nói thật.
WEBHOOK_MOI_PHUT_MOI_TRIGGER = 60


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def bam_token(token: str) -> str:
    """`sha256` hex của một token webhook — thứ ĐƯỢC LƯU (spec §8.3).

    ⛔ Token thô không bao giờ nằm trong `workflow_trigger.config`: `config` đi
       ra API quản trị và ra Canvas, và một bí mật đọc lại được là một bí mật đã
       rò. Ta lưu bản băm, so bằng `hmac.compare_digest`.
    """
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def token_khop(cau_hinh: dict, token: str) -> bool:
    """So HẰNG THỜI GIAN token gửi lên với `config.token_hash`.

    ⛔ Trigger **chưa đặt** `token_hash` ⇒ `False`, không phải `True`. Một
       webhook công khai không token là một cửa cho bất kỳ ai tiêu credit của
       chủ workflow; fail-closed là mặc định duy nhất đúng ở đây.
    """
    can = str((cau_hinh or {}).get("token_hash") or "")
    if not can:
        return False
    return hmac.compare_digest(can, bam_token(token))


class LoaiTrigger(Protocol):
    kind: str

    def toi_han(self, cau_hinh: dict, bay_gio: datetime) -> bool: ...

    def lan_ke_tiep(self, cau_hinh: dict,
                    bay_gio: datetime) -> Optional[datetime]: ...


class _KhongCoLich:
    """`MANUAL` · `API` · `WEBHOOK` — chờ một sự kiện từ ngoài, không tự chạy.

    ⛔ `lan_ke_tiep` trả `None` là **quan trọng**: một trigger thủ công mà tự
       chạy được là một lượt chạy không ai bấm — và nó tiêu tiền thật.
    """

    def __init__(self, kind: str):
        self.kind = kind

    def toi_han(self, cau_hinh: dict, bay_gio: datetime) -> bool:
        return False

    def lan_ke_tiep(self, cau_hinh: dict,
                    bay_gio: datetime) -> Optional[datetime]:
        return None


class _TheoLich:
    """`SCHEDULE` — `cau_hinh["moi_giay"]` giây một lần."""

    kind = "SCHEDULE"

    def toi_han(self, cau_hinh: dict, bay_gio: datetime) -> bool:
        return True

    def lan_ke_tiep(self, cau_hinh: dict,
                    bay_gio: datetime) -> Optional[datetime]:
        moi = int(cau_hinh.get("moi_giay", 0) or 0)
        return bay_gio + timedelta(seconds=moi) if moi > 0 else None


SO_DANG_KY: dict[str, LoaiTrigger] = {}


def dang_ky(loai: LoaiTrigger) -> None:
    SO_DANG_KY[loai.kind] = loai


def go_dang_ky(kind: str) -> None:
    SO_DANG_KY.pop(kind, None)


for _k in ("MANUAL", "API", "WEBHOOK"):
    dang_ky(_KhongCoLich(_k))
dang_ky(_TheoLich())


def tao(db, *, workflow_id: str, owner_id: str, kind: str,
        cau_hinh: Optional[dict] = None,
        enabled: bool = True) -> WorkflowTrigger:
    """Tạo một trigger. Loại chưa đăng ký bị từ chối **lúc tạo**.

    Từ chối ở đây chứ không ở lúc chạy: một trigger loại lạ nằm trong CSDL là
    một hàng mà bộ quét đi qua mỗi vòng và **im lặng bỏ qua** — nó không bao
    giờ chạy, và không ai biết vì sao.
    """
    if kind not in SO_DANG_KY:
        raise ValueError(
            f"loai trigger chua dang ky: {kind!r}; dang co "
            f"{sorted(SO_DANG_KY)}")
    cau_hinh = dict(cau_hinh or {})
    mo_dun = SO_DANG_KY[kind]
    t = WorkflowTrigger(
        workflow_id=workflow_id, owner_id=owner_id, kind=kind,
        config=cau_hinh, enabled=bool(enabled),
        next_fire_at=mo_dun.lan_ke_tiep(cau_hinh, _bay_gio()))
    db.add(t)
    db.flush()
    return t


def den_han(db, gioi_han: int = 200) -> list[WorkflowTrigger]:
    """Trigger **đang bật** và **đã tới hạn**. Một truy vấn, chỉ số bộ phận."""
    return list(db.execute(
        select(WorkflowTrigger)
        .where(WorkflowTrigger.enabled.is_(True),
               WorkflowTrigger.next_fire_at.is_not(None),
               WorkflowTrigger.next_fire_at <= _bay_gio())
        .order_by(WorkflowTrigger.next_fire_at)
        .limit(max(1, int(gioi_han)))).scalars())


def theo_id(db, trigger_id: str) -> Optional[WorkflowTrigger]:
    """Trigger ĐANG BẬT theo id, hoặc `None`.

    ⭐ "Không có" và "đã tắt" trả về **cùng một thứ**, và đó là chủ ý: cửa
       `/hooks/wf/{id}` là công khai, nên phân biệt hai ca đó cho người gọi là
       tặng họ một máy dò id trigger có thật.
    """
    t = db.get(WorkflowTrigger, str(trigger_id))
    return t if t is not None and t.enabled else None


__all__ = ["SO_DANG_KY", "WEBHOOK_MOI_PHUT_MOI_TRIGGER", "LoaiTrigger",
           "bam_token", "dang_ky", "den_han", "go_dang_ky", "tao", "theo_id",
           "token_khop"]
