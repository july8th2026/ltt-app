"""Ảnh chụp hằng tuần cho máy khách, giữ đúng một bản.

## Vì sao ảnh chụp chứ không phải `vzdump`

Trang bán hứa "sao lưu hằng tuần, giữ 1 bản" từ trước khi có mã nào làm việc đó.
Khi đi làm thật thì `vzdump` không chạy được: nó ghi ra một kho kiểu `dir`, và
kho `dir` duy nhất trên node (`local`) còn **2,2 GiB** — không đủ cho một máy,
nói gì tới mọi máy mỗi tuần.

Ảnh chụp trên LVM-thin thì ngược lại: tạo trong vài giây, và **gần như không tốn
chỗ lúc tạo** — chỉ khối nào bị ghi đè về sau mới chiếm. Đó là thứ dùng được cho
mọi máy hằng tuần với hạ tầng đang có.

## Nhưng phải nói đúng nó là gì

**Ảnh chụp KHÔNG phải bản sao lưu.** Nó nằm trên **cùng kho** với đĩa gốc; pool
hỏng là mất cả hai. Nó cứu khách khỏi *lỗi của chính họ* — xoá nhầm thư mục, một
bản vá làm hỏng máy, một phần mềm cài vào rồi không gỡ được — chứ không cứu khỏi
hỏng phần cứng.

Nên trang bán phải viết đúng như vậy, và nó đã được sửa. Hứa "sao lưu" rồi giao
một ảnh chụp là loại lời hứa mà người ta chỉ phát hiện sai đúng vào lúc mất dữ
liệu, tức lúc tệ nhất có thể.

## Crash-consistent, và điều đó có nghĩa gì

Máy khách không có guest agent (agent là thiết bị virtio, mà virtio treo trên cụm
này — xem `mang.py`). Nên không có ai bảo Windows "xả bộ đệm rồi đứng yên" trước
khi chụp. Ảnh chụp vì thế giống như **rút điện rồi bật lại**: NTFS có nhật ký nên
thường lên bình thường, nhưng một cơ sở dữ liệu đang ghi dở thì không có gì bảo
đảm.

**Đo thật 24/08, và nó rõ hơn mọi lời giải thích:** một tệp được ghi *ba giây
trước* khi chụp đã **không có** trong ảnh — nó còn nằm trong bộ đệm của guest.
Chạy lại đúng phép thử đó kèm `sync` thì tệp còn nguyên. Nghĩa là ảnh chụp giữ
được **những gì đã xuống đĩa**, không phải "mọi thứ tại thời điểm chụp".

Trong thực tế, Windows xả bộ đệm sau vài giây nên khoảng mất là nhỏ. Nhưng đừng
mô tả tính năng này là "khôi phục về đúng phút đó" — nó không phải vậy, và người
duy nhất phát hiện ra sự khác biệt sẽ là người đang cần khôi phục.

## Giữ ĐÚNG một bản, và tạo trước khi xoá

Tạo bản mới **rồi** mới xoá bản cũ. Ngược lại thì có một khoảng — dài bằng thời
gian tạo — mà khách **không có bản nào**, và đó đúng là khoảng mà một sự cố sẽ
tìm tới.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

#: Bao lâu chụp một lần.
MOI_NGAY = 7

#: Giữ bao nhiêu bản. Một — đúng như trang bán nói.
GIU = 1

#: Tiền tố tên ảnh. Chỉ ảnh mang tiền tố này mới bị dọn: ảnh do chủ nhà tự tạo
#: bằng tay trên Proxmox **không phải việc của vòng bảo trì**, và xoá nhầm một
#: ảnh người khác đang dựa vào là mất dữ liệu của họ.
TIEN_TO = "ltt"

_TEN = re.compile(rf"^{TIEN_TO}[0-9]{{8}}(_[0-9]{{4}})?$")


class SaoLuuError(RuntimeError):
    """Không chụp hoặc không khôi phục được."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ten_anh(luc: datetime | None = None) -> str:
    """Tên ảnh cho một thời điểm.

    Proxmox chỉ nhận `[A-Za-z0-9_-]` và tên phải **bắt đầu bằng chữ**, nên không
    dùng được dạng `2026-08-24`. Kèm giờ-phút để hai lần chụp trong cùng ngày
    (chụp tay rồi chụp theo lịch) không đụng tên nhau.
    """
    luc = luc or _now()
    return f"{TIEN_TO}{luc.strftime('%Y%m%d_%H%M')}"


def cua_ta(ten: str) -> bool:
    return bool(_TEN.match(str(ten or "")))


def den_han_chup(may, *, now: datetime | None = None) -> bool:
    """Máy này tới kỳ chụp chưa?

    Máy chưa có `vmid` (đang tạo) hoặc đã xoá thì không. Máy **bị treo** thì
    **có** — nó còn 7 ngày ân hạn trước khi bị xoá, và mất dữ liệu trong 7 ngày
    đó vì ta ngừng chụp là một cách phạt kèm không ai công bố.
    """
    if not getattr(may, "vmid", None):
        return False
    if str(getattr(may, "trang_thai", "")) in ("da_xoa", "dang_tao"):
        return False
    luc = getattr(may, "sao_luu_luc", None)
    if luc is None:
        return True
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=timezone.utc)
    return luc <= (now or _now()) - timedelta(days=MOI_NGAY)


def chup_va_don(client, may, *, now: datetime | None = None) -> str:
    """Chụp một bản mới rồi xoá bản cũ. Trả tên ảnh vừa tạo.

    Thứ tự **tạo trước, xoá sau** là cố ý: ngược lại thì có một khoảng khách
    không có bản nào.

    Lỗi lúc dọn bản cũ **không** làm hỏng cả việc: bản mới đã có, và bản cũ thừa
    chỉ tốn chỗ chứ không mất gì. Lượt sau dọn tiếp.
    """
    ten = ten_anh(now)
    client.chup_anh(may.vmid, ten, mo_ta="LTT VPS - anh chup hang tuan")

    cu = sorted((x.get("name") for x in client.danh_sach_anh(may.vmid)
                 if cua_ta(x.get("name"))), reverse=True)
    for thua in cu[GIU:]:
        if thua == ten:
            continue
        try:
            client.xoa_anh(may.vmid, thua)
        except Exception as exc:                 # noqa: BLE001
            # Bắt rộng có chủ ý và CHỈ ở đây: bản mới đã tạo xong, nên không lý
            # do gì để một lỗi dọn dẹp làm cả lượt bảo trì hỏng.
            log.warning("VPS: khong xoa duoc anh cu %s cua may %s: %s",
                        thua, may.id, exc)
    return ten


def anh_moi_nhat(client, vmid: int) -> str:
    """Tên ảnh mới nhất của ta, hoặc chuỗi rỗng."""
    cua = sorted((x.get("name") for x in client.danh_sach_anh(vmid)
                  if cua_ta(x.get("name"))), reverse=True)
    return cua[0] if cua else ""


def doc_duoc(ten: str) -> str:
    """`ltt20260824_1930` → `24/08/2026 19:30`. Tên máy đọc không phải tên khách đọc."""
    if not cua_ta(ten):
        return str(ten or "")
    lo = ten[len(TIEN_TO):]
    ngay = f"{lo[6:8]}/{lo[4:6]}/{lo[0:4]}"
    return f"{ngay} {lo[9:11]}:{lo[11:13]}" if len(lo) >= 13 else ngay
