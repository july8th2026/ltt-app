"""Cách ly một máy vì lạm dụng: **cắt mạng, giữ đĩa**.

## Vì sao cách ly phải là một khái niệm RIÊNG

Trước tệp này, người vận hành phát hiện một máy đang quét cổng hay phát tán thư
rác chỉ có hai nút: **treo** (`billing.treo`) hoặc **xoá**. Cả hai đều sai:

* **treo** là một khái niệm về **TIỀN**. Dùng nó cho lạm dụng là ghi vào sổ rằng
  khách nợ tiền — sai sự thật, và nó đặt luôn mốc `xoa_sau` 7 ngày. Máy của một
  khách đang trả tiền đầy đủ bị xoá sau một tuần vì một cảnh báo mạng;
* **xoá** không đảo được. Một heuristic sai thì không có đường về.

Cách ly là nút thứ ba, và nó có đúng hình dạng của vấn đề: **cắt đường ra
Internet, giữ nguyên đĩa và VM**. Khách vẫn vào được bằng console, dữ liệu còn
nguyên, và người vận hành gỡ lại được bằng một lệnh.

## Cắt cái gì, và vì sao không tắt máy

Cắt **đường NAT 1:1** ở cổng vào (`services/gateway.py`). Gói từ Internet không
vào được nữa, và máy cũng không ra được qua địa chỉ công khai của nó.

Không tắt máy, vì hai lý do:

1. tắt máy là cách chắc chắn để **mất bằng chứng** — tiến trình đang chạy, kết
   nối đang mở, thứ nằm trong RAM;
2. khách cần console để vào dọn. Một máy tắt thì họ không dọn được, và ta đã cắt
   mạng rồi nên nó không hại ai nữa.

## ⛔ Một tín hiệu heuristic KHÔNG được tự cách ly

Tệp này không có vòng lặp nào tự gọi `cach_ly()`. Nó cung cấp **nút**, và người
bấm là người vận hành — hoặc một luật có ngưỡng rõ ràng mà chủ sản phẩm đã chốt.

Tự động hoá bước này bằng một tín hiệu đơn (băng thông cao, nhiều kết nối) là
cách để cắt mạng của một khách đang chạy một việc hợp lệ, vào lúc họ cần nó nhất.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class CachLyError(RuntimeError):
    """Không cách ly / gỡ cách ly được."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dang_bi_cach_ly(may) -> bool:
    return getattr(may, "cach_ly_luc", None) is not None


def _ip_cong_khai(db, may) -> str:
    from sqlalchemy import select

    from apps.vps.tables import VpsIp
    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    return str(ip.dia_chi) if ip is not None else ""


def cach_ly(db, may, ly_do: str, *, boi: str = "he_thong",
            now: datetime | None = None) -> None:
    """Cắt đường NAT của máy và ghi sổ. **Không** tắt máy, **không** đụng đĩa.

    Chạy lại được: cách ly hai lần không lỗi và không đổi mốc đầu tiên — mốc ấy
    là thứ trả lời "máy này bị cắt từ lúc nào", và ghi đè nó là mất câu trả lời.

    Cổng vào không trả lời **không** chặn việc ghi sổ: cách ly là một quyết định,
    và nó phải được ghi lại kể cả khi chưa thi hành được. Vòng đối chiếu sẽ thấy
    một máy `cach_ly_luc` khác NULL mà đường NAT vẫn mở, và báo lên.
    """
    from apps.vps.services import gateway as cong_vao
    from apps.vps.services import provisioning

    if not str(ly_do or "").strip():
        raise CachLyError("cach ly phai co ly do — no la thu nguoi ta doc lai sau nay")

    ip = _ip_cong_khai(db, may)
    da_cat = False
    if ip and may.ip_noi_bo:
        try:
            cong_vao.client_tu_moi_truong().dong_duong(ip, may.ip_noi_bo)
            da_cat = True
        except Exception as exc:                 # noqa: BLE001
            log.warning("VPS: cach ly may %s nhung khong dong duoc duong: %s",
                        may.id, exc)

    if not dang_bi_cach_ly(may):
        may.cach_ly_luc = now or _now()
    may.cach_ly_ly_do = str(ly_do)[:2000]
    provisioning.ghi_su_kien(db, may.id, "bi_cach_ly", boi=boi,
                             ly_do=str(ly_do)[:200], da_cat_duong=da_cat)


def go_cach_ly(db, may, *, boi: str = "he_thong") -> None:
    """Mở lại đường NAT và xoá dấu cách ly.

    Đây là **đường về**, và nó phải tồn tại: một trạng thái phạt không có đường
    gỡ là một trạng thái xoá vĩnh viễn đội lốt một trạng thái tạm thời.
    """
    from apps.vps.services import gateway as cong_vao
    from apps.vps.services import provisioning

    ip = _ip_cong_khai(db, may)
    da_mo = False
    if ip and may.ip_noi_bo:
        try:
            cong_vao.client_tu_moi_truong().mo_duong(ip, may.ip_noi_bo)
            da_mo = True
        except Exception as exc:                 # noqa: BLE001
            # ⚠️ KHÔNG xoá dấu cách ly khi chưa mở lại được đường. Xoá dấu mà
            #    đường vẫn đóng là để lại một máy không vào được mà **không còn
            #    dòng nào giải thích vì sao** — loại sự cố tốn cả buổi để dò.
            raise CachLyError(
                f"khong mo lai duoc duong cho may {may.id}: {exc}") from exc

    may.cach_ly_luc = None
    may.cach_ly_ly_do = ""
    provisioning.ghi_su_kien(db, may.id, "go_cach_ly", boi=boi, da_mo_duong=da_mo)
