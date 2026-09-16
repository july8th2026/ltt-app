"""Console trong trình duyệt: cấp vé, tiêu vé, và bắc cầu WebSocket tới Proxmox.

## Vì sao phải có lớp này thay vì cho khách vào thẳng Proxmox

Proxmox có sẵn console noVNC ở cổng 8006. Đưa khách tới đó là đưa họ **toàn bộ
giao diện quản trị cụm** — nơi có mọi máy của mọi khách, và nút xoá của từng cái.
Không có cách nào giới hạn một phiên đăng nhập Proxmox xuống "chỉ máy này".

Nên: khách nói chuyện với **server của mình**, server nói chuyện với Proxmox.
Khách không bao giờ biết địa chỉ Proxmox, không bao giờ cầm vé của Proxmox.

## Ba lớp chặn, và chúng chặn ba thứ khác nhau

1. **Vé một-lần, hết hạn sau %(giay)s giây** — chặn việc một URL rò ra ngoài
   (lịch sử trình duyệt, ảnh chụp màn hình, người ngồi cạnh) còn dùng lại được.
2. **Vé buộc vào (khách, máy)** — chặn việc đổi `instance_id` trên URL để nhìn
   màn hình máy người khác.
3. **Kiểm lại chủ sở hữu lúc mở WebSocket** — vé đúng nhưng máy đã đổi chủ, hay
   khách đã bị khoá, thì vẫn phải chặn.

Ba lớp vì chúng hỏng theo ba kiểu: vé rò, vé bị sửa, và trạng thái đổi giữa lúc
vé còn sống.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from apps.vps.tables import VpsConsoleVe, VpsInstance

#: Vé sống bao lâu. Ngắn có chủ ý: nó chỉ cần đủ để trang tải xong rồi mở
#: WebSocket, chứ không phải đủ để ai đó chép URL đi chỗ khác.
HAN_VE_GIAY = 60

#: Dọn vé cũ khi số vé của một máy vượt mức này — bảng vé không được phình mãi.
GIU_TOI_DA_MOI_MAY = 20


class VeKhongHopLeError(RuntimeError):
    """Vé sai, hết hạn, đã dùng, hoặc không thuộc về người/máy này."""


def _bam(ve: str) -> str:
    return hashlib.sha256(ve.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cap_ve(db: DbSession, may: VpsInstance, user_id: str, *,
           cong: int = 0, pve_ve: str = "") -> str:
    """Cấp một vé mới. Trả **vé thô** — chỉ lần này, CSDL chỉ giữ băm của nó."""
    ve = secrets.token_urlsafe(32)
    db.add(VpsConsoleVe(id=_bam(ve), instance_id=may.id, user_id=str(user_id),
                        cong=int(cong or 0), pve_ve=str(pve_ve or "")))
    _don_ve_cu(db, may.id)
    db.commit()
    return ve


def tieu_ve(db: DbSession, ve: str, instance_id: str, user_id: str):
    """Tiêu vé; trả `(máy, cổng, vé_proxmox)`. Ném nếu bất kỳ lớp nào không qua.

    **Tiêu bằng một câu `UPDATE ... WHERE da_dung_luc IS NULL`, không phải đọc
    rồi ghi.** Hai request cùng cầm một vé thì đúng một câu UPDATE đổi được dòng;
    kiểm-rồi-ghi để hở một khe giữa hai bước, và khe đó đủ cho cả hai cùng qua.
    """
    han = _now() - timedelta(seconds=HAN_VE_GIAY)
    ma = _bam(str(ve or ""))
    kq = db.execute(
        update(VpsConsoleVe)
        .where(VpsConsoleVe.id == ma,
               VpsConsoleVe.instance_id == str(instance_id or ""),
               VpsConsoleVe.user_id == str(user_id or ""),
               VpsConsoleVe.da_dung_luc.is_(None),
               VpsConsoleVe.created_at > han)
        .values(da_dung_luc=_now()))
    if kq.rowcount != 1:
        db.rollback()
        raise VeKhongHopLeError("ve khong hop le, da dung, hoac het han")
    dong = db.get(VpsConsoleVe, ma)
    cong, pve_ve = int(dong.cong or 0), str(dong.pve_ve or "")

    # Lớp 3: trạng thái có thể đã đổi trong lúc vé còn sống.
    may = db.get(VpsInstance, str(instance_id))
    if may is None or str(may.user_id) != str(user_id) or may.trang_thai == "da_xoa":
        db.rollback()
        raise VeKhongHopLeError("may khong con thuoc ve nguoi nay")
    if not may.vmid:
        db.rollback()
        raise VeKhongHopLeError("may chua duoc tao xong")
    # XOÁ dòng ngay khi tiêu: nó chứa vé của Proxmox, và vé đó không có lý do gì
    # nằm lại trong CSDL sau khi đã dùng.
    db.delete(dong)
    db.commit()
    return may, cong, pve_ve


def _don_ve_cu(db: DbSession, instance_id: str) -> None:
    """Xoá vé cũ của một máy. Bảng vé chỉ để bắc cầu, không phải để lưu lịch sử."""
    cu = list(db.execute(
        select(VpsConsoleVe.id)
        .where(VpsConsoleVe.instance_id == str(instance_id))
        .order_by(VpsConsoleVe.created_at.desc())
        .offset(GIU_TOI_DA_MOI_MAY)).scalars())
    for ma in cu:
        doi_tuong = db.get(VpsConsoleVe, ma)
        if doi_tuong is not None:
            db.delete(doi_tuong)


def tls_cho_cau_console(config):
    """SSL context + server_hostname cho cầu WebSocket tới Proxmox.

    Phải trùng đúng chính sách TLS của `ProxmoxClient`: CA riêng
    (`LTT_VPS_PROXMOX_CA`) và tên chứng chỉ chính xác (`LTT_VPS_PROXMOX_TLS_NAME`).
    Đo 16/09 trên production: context mặc định báo "unable to get local issuer
    certificate", CA riêng + hostname theo IP báo "IP address mismatch", chỉ CA
    riêng + tên `pve` bắt tay được — nên console khách mất kết nối ngay (R20).
    """
    import ssl as ssl_mod

    ca = str(getattr(config, "ca_bundle", "") or "")
    if ca:
        ctx = ssl_mod.create_default_context(cafile=ca)
        return ctx, (str(getattr(config, "tls_name", "") or "") or None)
    ctx = ssl_mod.create_default_context()
    if not getattr(config, "verify", True):
        # Chỉ môi trường dev đã cho phép bỏ qua ở `doc_cau_hinh`.
        ctx.check_hostname = False
        ctx.verify_mode = ssl_mod.CERT_NONE
    return ctx, None


def dia_chi_websocket_proxmox(config, vmid: int, ve_proxmox: dict) -> str:
    """URL WebSocket của Proxmox cho một vé `vncproxy`.

    Hàm riêng để **test được mà không cần cụm thật** — đây là chỗ dễ ghép sai
    chuỗi, và ghép sai thì lỗi hiện ra dưới dạng "console trắng" chứ không dưới
    dạng một thông báo nào.
    """
    from urllib.parse import quote

    cong = ve_proxmox.get("port")
    ticket = ve_proxmox.get("ticket")
    if not cong or not ticket:
        raise VeKhongHopLeError(
            f"Proxmox tra ve thieu port/ticket cho VM {vmid}: {ve_proxmox!r}")
    goc = str(config.base_url).rstrip("/").replace("https://", "wss://", 1)
    return (f"{goc}/api2/json/nodes/{config.node}/qemu/{int(vmid)}/vncwebsocket"
            f"?port={cong}&vncticket={quote(str(ticket), safe='')}")


def don_ve_het_han(db: DbSession) -> int:
    """Xoá vé đã hết hạn. Trả số dòng đã xoá. Chạy trong vòng bảo trì của app.

    ## Vì sao cần, khi vé đã bị xoá lúc tiêu

    `tieu_ve` xoá vé **đã dùng**. `_don_ve_cu` chỉ cắt bớt khi một máy vượt
    `GIU_TOI_DA_MOI_MAY` vé. Không cái nào dọn **vé cấp ra rồi không ai dùng** —
    khách mở trang console rồi đóng tab, hoặc máy bị xoá trong lúc vé còn sống.
    Những vé đó nằm lại vĩnh viễn.

    Mỗi dòng giữ `user_id` và một vé của Proxmox. Nó nhỏ, nhưng "nhỏ và vĩnh
    viễn" vẫn là dữ liệu của khách nằm lại không có lý do — và chính sách lưu
    trữ ở `governance.py` nói rằng bảng này được dọn.
    """
    from sqlalchemy import delete

    han = _now() - timedelta(seconds=HAN_VE_GIAY)
    kq = db.execute(delete(VpsConsoleVe).where(VpsConsoleVe.created_at <= han))
    return int(kq.rowcount or 0)
