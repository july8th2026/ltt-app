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


class _TheoCron:
    """`CRON` — lịch thật, bằng **`cronsim`**, ⛔ không tự viết bộ lịch.

    ## Vì sao `cronsim` chứ không `croniter` (spec §8.2 viết `croniter`)

    Đây là một **đổi ý so với spec**, tra được chứ không phải sở thích:

    - `pallets-eco/croniter#258` (MỞ, 02/08/2026) — *"get_next skips a fire
      time when the DST shift is not a whole hour; get_prev and match
      disagree"*; `#259` — *"croniter_range stop test ignores the UTC offset:
      silently drops results and returns out-of-interval values"*. Hai lỗi còn
      mở, đúng vào **hai** phép ta cần: tiến (lần bắn kế) và lùi (mốc lỡ).
    - `cuu508/cronsim` (BSD-3-Clause, dùng trong Healthchecks) khai thẳng
      *"Correctness… match Debian's cron as closely as possible, including its
      quirky behaviour during DST transitions"*, và có `reverse=True`.

    ## Quy ước thời gian

    Cột `next_fire_at` là **naive-UTC** (quy ước của cả kho, `_bay_gio()`).
    Lịch thì nghĩ bằng **giờ địa phương** của người soạn. Nên mọi phép ở đây
    đổi vào múi giờ, tính, rồi đổi về naive-UTC — ⛔ không bao giờ so một mốc
    địa phương với một mốc UTC.
    """

    kind = "CRON"

    #: Spec §8.2: *"Chu kỳ tối thiểu 5 phút"*. Một trigger mỗi giây nằm trong
    #: CSDL là một cỗ máy tiêu credit, nên nó bị từ chối **lúc tạo**.
    CHU_KY_TOI_THIEU_S = 300

    @staticmethod
    def _tz(cau_hinh: dict):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        ten = str((cau_hinh or {}).get("tz") or "UTC")
        try:
            return ZoneInfo(ten)
        except (ZoneInfoNotFoundError, ValueError, KeyError) as loi:
            raise ValueError(f"mui gio khong hop le: {ten!r}") from loi

    @classmethod
    def _lich(cls, cau_hinh: dict, tu: datetime, *, lui: bool = False):
        from cronsim import CronSim, CronSimError

        bieu_thuc = str((cau_hinh or {}).get("cron") or "").strip()
        if not bieu_thuc:
            raise ValueError("thieu `cron` trong cau hinh trigger CRON")
        tz = cls._tz(cau_hinh)
        goc = tu.replace(tzinfo=timezone.utc).astimezone(tz)
        try:
            return CronSim(bieu_thuc, goc, reverse=lui)
        except CronSimError as loi:
            raise ValueError(f"bieu thuc cron khong hop le: {loi}") from loi

    @staticmethod
    def _ve_utc(luc: Optional[datetime]) -> Optional[datetime]:
        if luc is None:
            return None
        return luc.astimezone(timezone.utc).replace(tzinfo=None)

    def toi_han(self, cau_hinh: dict, bay_gio: datetime) -> bool:
        return True

    def kiem(self, cau_hinh: dict) -> None:
        """Ném `ValueError` nếu cấu hình không dùng được. Gọi lúc `tao()`.

        ⚠️ Đo chu kỳ bằng **hai mốc liên tiếp thật**, không bằng cách đọc chuỗi:
           `*/5 * * * *` và `0,5,10,… * * * *` là cùng một lịch viết hai kiểu,
           và một bộ đọc chuỗi sẽ bắt cái này, thả cái kia.
        """
        luc = datetime.now(timezone.utc).replace(tzinfo=None)
        it = self._lich(cau_hinh, luc)
        try:
            moc = [next(it) for _ in range(3)]
        except StopIteration as loi:
            raise ValueError(
                "bieu thuc cron khong co moc nao trong 50 nam toi") from loi
        khoang = min((b - a).total_seconds() for a, b in zip(moc, moc[1:]))
        if khoang < self.CHU_KY_TOI_THIEU_S:
            raise ValueError(
                f"chu ky toi thieu {self.CHU_KY_TOI_THIEU_S} giay (5 phut), "
                f"cau hinh nay cach nhau {int(khoang)} giay")

    def lan_ke_tiep(self, cau_hinh: dict,
                    bay_gio: datetime) -> Optional[datetime]:
        try:
            return self._ve_utc(next(self._lich(cau_hinh, bay_gio)))
        except StopIteration:
            return None

    def moc_gan_nhat(self, cau_hinh: dict,
                     bay_gio: datetime) -> Optional[datetime]:
        """Mốc lịch **gần nhất ≤ `bay_gio`** — *"mốc lỡ gần nhất"* của §8.2.

        ⚠️ Lùi từ `bay_gio + 1 giây` vì `cronsim` lùi **nghiêm ngặt**: lùi từ
           đúng một mốc sẽ trả về mốc TRƯỚC nó, và khi đó một trigger tới hạn
           đúng giây này sẽ bắn cho mốc của hôm qua.
        """
        try:
            return self._ve_utc(next(self._lich(
                cau_hinh, bay_gio + timedelta(seconds=1), lui=True)))
        except StopIteration:
            return None


SO_DANG_KY: dict[str, LoaiTrigger] = {}


def dang_ky(loai: LoaiTrigger) -> None:
    SO_DANG_KY[loai.kind] = loai


def go_dang_ky(kind: str) -> None:
    SO_DANG_KY.pop(kind, None)


for _k in ("MANUAL", "API", "WEBHOOK"):
    dang_ky(_KhongCoLich(_k))
dang_ky(_TheoLich())
dang_ky(_TheoCron())


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
    # ⭐ Loại nào có `kiem()` thì nó tự kiểm cấu hình của nó. Lõi KHÔNG biết
    #    tên loại nào (`G42`, bài học Windmill) — nó chỉ biết "một loại có thể
    #    từ chối cấu hình của chính nó, và chỗ từ chối là LÚC TẠO".
    kiem = getattr(mo_dun, "kiem", None)
    if callable(kiem):
        kiem(cau_hinh)
    t = WorkflowTrigger(
        workflow_id=workflow_id, owner_id=owner_id, kind=kind,
        config=cau_hinh, enabled=bool(enabled),
        next_fire_at=mo_dun.lan_ke_tiep(cau_hinh, _bay_gio()))
    db.add(t)
    db.flush()
    return t


def den_han(db, gioi_han: int = 200,
            bay_gio: Optional[datetime] = None) -> list[WorkflowTrigger]:
    """Trigger **đang bật** và **đã tới hạn**. Một truy vấn, chỉ số bộ phận.

    ⚠️ `bay_gio` KHÔNG phải tiện nghi cho test. Bên gọi (`ban_trigger`) đã
       chốt một mốc `luc` cho cả lượt bắn; nếu hàm này tự hỏi đồng hồ lần nữa
       thì hai câu trả lời trong cùng một lượt lệch nhau — và một trigger tới
       hạn ở khe giữa hai lần hỏi sẽ được **chọn** theo mốc này nhưng **tính
       mốc lịch** theo mốc kia.
    """
    return list(db.execute(
        select(WorkflowTrigger)
        .where(WorkflowTrigger.enabled.is_(True),
               WorkflowTrigger.next_fire_at.is_not(None),
               WorkflowTrigger.next_fire_at <= (bay_gio or _bay_gio()))
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
