"""Handler chạy trong worker: tạo, dựng lại, và xoá máy ảo.

## Vì sao mọi thứ ở đây phải chịu được việc chạy lại

Worker chết giữa chừng là chuyện bình thường: bị kill, mất điện, khởi động lại khi
cập nhật. Hàng đợi sẽ giao lại job cho tiến trình khác. Nếu `vps.provision` không
chịu được điều đó thì lần chạy thứ hai tạo **máy thứ hai** — một máy mồ côi, ăn đĩa
trong cái kho vốn là nút thắt, và không ai biết nó tồn tại vì CSDL chỉ ghi một máy.

Cách chống ở đây không phải là một cờ "đã chạy rồi", mà là **mỗi bước tự hỏi thế
giới thật xem nó đã xảy ra chưa**: máy đã có VMID chưa, Proxmox đã có VM đó chưa,
cổng đã cấp chưa. Cờ có thể ghi xong rồi tiến trình chết trước khi commit; thế giới
thật thì không nói dối.

## Vì sao không có bước "chờ clone xong" bằng vòng lặp vô hạn

Trần thời gian khai ở `manifest.max_runtime_s` (30 phút). Vòng chờ ở đây có hạn
riêng, ngắn hơn, để job thất bại **có thông báo** thay vì bị nền tảng cắt ngang như
một job treo — hai thứ đó nhìn giống nhau trong log nhưng cần hai cách xử lý khác nhau.
"""
from __future__ import annotations

import logging
import time

from apps.vps import os_images
from apps.vps.cost import dia_tong_gb, lay_plan
from apps.vps.services import mang, provisioning
from apps.vps.services.proxmox import ProxmoxError, client_tu_moi_truong
from apps.vps.tables import VpsGateway, VpsInstance

log = logging.getLogger(__name__)

#: Chờ tối đa cho một tác vụ nền của Proxmox (clone, xoá). Ngắn hơn trần của
#: manifest để job tự báo lỗi thay vì bị nền tảng cắt như một job treo.
CHO_TAC_VU_S = 20 * 60
NHIP_HOI_S = 5


class VpsJobError(RuntimeError):
    """Lỗi có thông điệp đọc được. Ném ra để nền tảng hoàn credit đã giữ."""


def handle(params: dict, ctx=None) -> dict:
    """Điểm vào duy nhất; phân nhánh theo `ctx.job_type` (hợp đồng nền tảng)."""
    job_type = getattr(ctx, "job_type", "") or str(params.get("job_type", ""))
    if job_type == "vps.provision":
        return _tao_may(params, ctx)
    if job_type == "vps.rebuild":
        return _dung_lai(params, ctx)
    if job_type == "vps.destroy":
        return _xoa_may(params, ctx)
    raise VpsJobError(f"job_type khong biet: {job_type!r}")


# ── tiện ích ────────────────────────────────────────────────────────────────

def _mo_db():
    from platform_core.db import get_session
    gen = get_session()
    return next(gen), gen


def _bao(ctx, phan_tram: int, thong_diep: str) -> None:
    if ctx is not None:
        ctx.progress(int(phan_tram), thong_diep)


def _lay_may(db, instance_id: str) -> VpsInstance:
    may = db.get(VpsInstance, str(instance_id or ""))
    if may is None:
        raise VpsJobError(f"khong tim thay may {instance_id!r}")
    return may


def _cho_tac_vu(client, upid: str, ctx=None, *, moc: int = 30) -> None:
    """Chờ một tác vụ nền của Proxmox xong. Ném lỗi nếu nó thất bại hoặc quá hạn."""
    het_han = time.monotonic() + CHO_TAC_VU_S
    while time.monotonic() < het_han:
        tt = client.trang_thai_tac_vu(upid)
        if str(tt.get("status", "")) == "stopped":
            ket_qua = str(tt.get("exitstatus", ""))
            if ket_qua and ket_qua != "OK":
                raise VpsJobError(f"Proxmox bao tac vu that bai: {ket_qua}")
            return
        _bao(ctx, moc, "dang chuan bi may")
        time.sleep(NHIP_HOI_S)
    raise VpsJobError("Proxmox khong hoan thanh tac vu trong thoi gian cho phep")


# ── vps.provision ───────────────────────────────────────────────────────────

def _tao_may(params: dict, ctx=None) -> dict:
    db, gen = _mo_db()
    try:
        may = _lay_may(db, params.get("instance_id"))
        if may.trang_thai == "dang_chay" and may.vmid:
            # Job chạy lại sau khi đã xong. Không làm gì, không lỗi.
            return {"instance_id": may.id, "vmid": may.vmid, "da_co_san": True}

        plan = lay_plan(may.plan_id)
        if plan is None:
            raise VpsJobError(f"goi {may.plan_id!r} khong con trong bang gia")
        img = os_images.lay_os(may.os_id)
        if img is None:
            raise VpsJobError(f"he dieu hanh {may.os_id!r} khong co trong catalog")

        template = os_images.template_vmid(may.os_id)
        if not template:
            raise VpsJobError(
                f"chua khai template cho {img.ten}: dat bien "
                f"{os_images.khoa_moi_truong(may.os_id)} trong secrets/app.env")

        gateway = db.get(VpsGateway, may.gateway_id)
        if gateway is None:
            raise VpsJobError("may nay khong gan voi cong vao nao")

        client = client_tu_moi_truong()
        _bao(ctx, 5, "dang xin cho tren may chu")

        # 1) VMID — hỏi Proxmox lấy gợi ý, nhưng trọng tài là ràng buộc CSDL.
        if not may.vmid:
            try:
                goi_y = client.vmid_ke_tiep()
            except ProxmoxError:
                goi_y = 0
            provisioning.cap_vmid(db, may, goi_y=goi_y)
            db.commit()

        # 2) Clone — bước KHÔNG idempotent, nên hỏi thế giới thật trước.
        _bao(ctx, 15, "dang nhan ban he dieu hanh")
        if not _vm_da_ton_tai(client, may.vmid):
            upid = client.clone(template, may.vmid,
                                ten=f"vps-{may.id[:8]}", full=False)
            _cho_tac_vu(client, upid, ctx, moc=35)

        # 3) Địa chỉ trong mạng riêng — cấp TRƯỚC khi cấu hình, vì cloud-init
        #    tiêm nó vào máy ở bước sau. Nguyên tử qua ràng buộc duy nhất
        #    `(gateway_id, ip_noi_bo)`; chạy lại thì trả về đúng địa chỉ cũ.
        _bao(ctx, 45, "dang cap dia chi")
        ip_noi_bo = provisioning.cap_ip_noi_bo(db, may, gateway)
        db.commit()

        # 4) Cấu hình theo gói + cắm vào mạng riêng, rồi nới đĩa nếu cần.
        _bao(ctx, 60, "dang dat cau hinh")
        cau_hinh = {"cores": plan.vcpu, "memory": plan.ram_mb,
                    "name": f"vps-{may.id[:8]}"}
        cau_hinh.update(mang.cau_hinh_qemu(
            mang.mang_cho_may(gateway, ip_noi_bo)))
        client.dat_cau_hinh(may.vmid, **cau_hinh)

        can_dia = dia_tong_gb(may.plan_id, may.dia_them_gb)
        if can_dia > img.disk_gb_toi_thieu:
            # Proxmox chỉ nới ra, không thu vào — an toàn khi chạy lại.
            client.nong_dia(may.vmid, _dia_goc(client, may.vmid), f"{can_dia}G")

        # 5) Bật máy.
        _bao(ctx, 85, "dang khoi dong")
        client.bat(may.vmid)

        may.trang_thai = "dang_chay"
        may.ly_do = ""
        provisioning.ghi_su_kien(db, may.id, "tao_xong", boi="he_thong",
                                 vmid=may.vmid, ip_noi_bo=ip_noi_bo)
        db.commit()
        _bao(ctx, 100, "xong")

        # Địa chỉ khách gõ vào là IP CÔNG KHAI RIÊNG của máy, cấp ở bước sau
        # (G2/`services/vultr.py`). Chừng nào chưa có thì trả rỗng — thà không
        # có địa chỉ còn hơn đưa địa chỉ của cổng vào, vì khách sẽ thử gõ nó và
        # rơi vào máy người khác.
        return {
            "instance_id": may.id,
            "vmid": may.vmid,
            "ip_noi_bo": ip_noi_bo,
            "dia_chi": _ip_cong_khai(db, may.id),
            "he_dieu_hanh": img.ten,
        }
    except Exception as exc:
        _danh_dau_loi(db, params.get("instance_id"), exc)
        raise
    finally:
        gen.close()


def _vm_da_ton_tai(client, vmid: int | None) -> bool:
    """Proxmox đã có VM này chưa. Đây là phép hỏi-thế-giới-thật chống clone đúp."""
    if not vmid:
        return False
    try:
        return any(int(v.get("vmid", 0)) == int(vmid)
                   for v in client.danh_sach_vm())
    except ProxmoxError:
        # Không hỏi được thì **coi như đã có**: bỏ sót một lần clone chỉ làm job
        # lỗi và có người xem; clone hai lần thì để lại một máy mồ côi im lặng.
        return True


#: Các bus đĩa Proxmox dùng, theo thứ tự thường gặp khi tìm đĩa hệ điều hành.
BUS_DIA = ("scsi0", "sata0", "virtio0", "ide0")


def _dia_goc(client, vmid: int) -> str:
    """Tên bus của đĩa hệ điều hành. Hỏi máy, đừng đoán.

    Bản đầu ghi cứng `scsi0`. Sai: hai template Windows sẵn có trên cụm này dùng
    **`sata0`**, nên lệnh nới đĩa sẽ trượt vào một bus không tồn tại — và Proxmox
    báo lỗi ở giữa chừng một lần tạo máy đã thu tiền.
    """
    cfg = client._goi("GET", f"/nodes/{client.config.node}/qemu/{int(vmid)}/config") or {}
    for bus in BUS_DIA:
        gt = str(cfg.get(bus) or "")
        # Bỏ qua ổ CD-ROM: `ide2: none,media=cdrom` không phải đĩa hệ điều hành.
        if gt and "media=cdrom" not in gt:
            return bus
    raise VpsJobError(f"khong tim thay dia he dieu hanh cua VM {vmid}")


def _ip_cong_khai(db, instance_id: str) -> str:
    """IP công khai riêng của máy, hoặc rỗng nếu chưa cấp."""
    from sqlalchemy import select

    from apps.vps.tables import VpsIp
    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == instance_id)
    ).scalars().first()
    return str(ip.dia_chi) if ip is not None else ""


def _danh_dau_loi(db, instance_id, exc: Exception) -> None:
    """Ghi lý do vào máy để khách và admin đọc được, thay vì chỉ ném lên log."""
    try:
        db.rollback()
        may = db.get(VpsInstance, str(instance_id or ""))
        if may is None:
            return
        may.trang_thai = "loi"
        may.ly_do = f"{type(exc).__name__}: {exc}"[:2000]
        provisioning.ghi_su_kien(db, may.id, "loi", boi="he_thong",
                                 thong_diep=may.ly_do)
        db.commit()
    except Exception:            # noqa: BLE001 - ghi lỗi không được che lỗi gốc
        log.exception("vps: khong ghi duoc trang thai loi cho %r", instance_id)


# ── vps.rebuild ─────────────────────────────────────────────────────────────

def _dung_lai(params: dict, ctx=None) -> dict:
    """Cài lại từ đầu: xoá VM cũ, giữ nguyên bản ghi, cổng và IP đã cấp.

    Giữ cổng là cố ý — khách đã lưu địa chỉ đó, đã cấu hình client. Đổi cổng khi
    cài lại là bắt khách đi tìm địa chỉ mới mà không có lý do gì.
    """
    db, gen = _mo_db()
    try:
        may = _lay_may(db, params.get("instance_id"))
        if not may.vmid:
            raise VpsJobError("may chua duoc tao, khong co gi de dung lai")

        client = client_tu_moi_truong()
        _bao(ctx, 10, "dang tat may cu")
        if _vm_da_ton_tai(client, may.vmid):
            try:
                client.tat_cung(may.vmid)
            except ProxmoxError:
                pass                      # máy đã tắt sẵn — không phải lỗi
            upid = client.xoa(may.vmid)
            _cho_tac_vu(client, upid, ctx, moc=30)

        may.trang_thai = "dang_tao"
        provisioning.ghi_su_kien(db, may.id, "dung_lai", boi="he_thong",
                                 os_id=params.get("os_id") or may.os_id)
        if params.get("os_id"):
            may.os_id = str(params["os_id"])
        db.commit()
    finally:
        gen.close()

    # Dựng lại đúng bằng đường tạo mới — một đường code, một chỗ để sai.
    return _tao_may({"instance_id": params.get("instance_id")}, ctx)


# ── vps.destroy ─────────────────────────────────────────────────────────────

def _xoa_may(params: dict, ctx=None) -> dict:
    """Xoá vĩnh viễn. Không hoàn tác được — người gọi phải chắc đã tới mốc V8."""
    db, gen = _mo_db()
    try:
        may = _lay_may(db, params.get("instance_id"))
        if may.trang_thai == "da_xoa":
            return {"instance_id": may.id, "da_xoa_truoc_do": True}

        client = client_tu_moi_truong()
        if may.vmid and _vm_da_ton_tai(client, may.vmid):
            _bao(ctx, 20, "dang tat may")
            try:
                client.tat_cung(may.vmid)
            except ProxmoxError:
                pass          # máy đã tắt sẵn — không phải lỗi, vẫn xoá tiếp
            _bao(ctx, 50, "dang xoa dia")
            upid = client.xoa(may.vmid)
            _cho_tac_vu(client, upid, ctx, moc=70)

        _nha_tai_nguyen(db, may)
        may.trang_thai = "da_xoa"
        provisioning.ghi_su_kien(db, may.id, "da_xoa",
                                 boi=str(params.get("boi") or "he_thong"))
        db.commit()
        _bao(ctx, 100, "xong")
        return {"instance_id": may.id, "vmid": may.vmid}
    finally:
        gen.close()


def _nha_tai_nguyen(db, may: VpsInstance) -> None:
    """Trả địa chỉ riêng và IP công khai về kho.

    Không làm bước này thì kho cạn dần một cách im lặng — và với IP công khai
    thì tệ hơn: mỗi máy chết để lại **$3/tháng chảy mãi** ở nhà cung cấp.

    Chỉ nhả trong CSDL. Việc trả IP về cho Vultr và gỡ luật NAT trên gateway do
    `services/vultr.py` + `services/gateway.py` làm, và phải chạy TRƯỚC khi tới
    đây — xem `_xoa_may`.
    """
    from sqlalchemy import select

    from apps.vps.tables import VpsIp

    may.ip_noi_bo = None
    for ip in db.execute(select(VpsIp).where(VpsIp.instance_id == may.id)).scalars():
        ip.instance_id = None
    db.flush()
