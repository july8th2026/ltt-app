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
import os
import time

from apps.vps import os_images
from apps.vps.cost import dia_tong_gb, lay_plan
from apps.vps.services import dinh_danh, mang, provisioning
from apps.vps.services import router as bo_dinh_tuyen
from apps.vps.services.proxmox import ProxmoxError, client_tu_moi_truong
from apps.vps.tables import VpsGateway, VpsInstance

log = logging.getLogger(__name__)

#: Kho lưu trữ đặt đĩa của máy khách. Đọc từ môi trường để dựng lại cụm không
#: phải sửa code — cùng lý do với `LTT_VPS_ISO_*`.
#:
#: Mặc định `vmdata`: kho LVM-thin 475 GB của cụm hiện tại. Đặt sai tên thì
#: Proxmox từ chối tạo máy ngay, không hỏng lặng lẽ.
KHO_DIA = os.environ.get("LTT_VPS_KHO_DIA", "vmdata")

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

        # Từ 2026-08-24: **khách tự cài**. Máy sinh ra là máy trống + đĩa cài
        # đặt, khách tự chạy trình cài qua console và tự đặt tài khoản/mật khẩu
        # của chính họ — nền tảng không bao giờ biết mật khẩu của ai.
        #
        # Đường `template` chỉ còn cho bản Linux NỘI BỘ (`khach_thay=False`):
        # nó lên trong ~40 giây nên dùng để tách "lỗi đường ống" khỏi "lỗi trong
        # lúc cài Windows". Không bán bằng đường đó.
        iso = os_images.dia_cai_dat(may.os_id)
        template = 0 if iso else _template_noi_bo(may.os_id)
        if not iso and not template:
            raise VpsJobError(
                f"chua khai dia cai dat cho {img.ten}: dat bien "
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
            # Đưa CẢ danh sách VM đang có trên máy chủ vào: xem docstring của
            # `cap_vmid`. Không có nó thì job chiếm máy mà CSDL không biết.
            try:
                da_co = {int(v.get("vmid", 0)) for v in client.danh_sach_vm()}
            except ProxmoxError:
                # Không đọc được thì DỪNG, đừng cấp bừa: cấp trúng máy người
                # khác tệ hơn nhiều so với việc khách phải thử lại.
                raise
            provisioning.cap_vmid(db, may, goi_y=goi_y, da_co_tren_may_chu=da_co)
            db.commit()

        # 2) Dựng máy — bước KHÔNG idempotent, nên hỏi thế giới thật trước.
        _bao(ctx, 15, "dang chuan bi may")
        if not _vm_da_ton_tai(client, may.vmid):
            if iso:
                upid = client.tao_may(
                    may.vmid,
                    **_cau_hinh_may_trong(may, plan, img, iso))
            else:
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
                    "name": f"vps-{may.id[:8]}",
                    # `vga` PHẢI đặt tường minh. Template nội bộ đặt `vga:
                    # serial0` để đọc được log khởi động qua cổng nối tiếp —
                    # nhưng máy nào thừa hưởng nó thì **không có màn hình đồ hoạ
                    # nào cả**, và console trong trình duyệt mở ra chỉ thấy một
                    # kết nối bị đóng ngay. Với khách Windows thì console là
                    # ĐƯỜNG CỨU HỘ khi họ tự chặn mất RDP của chính mình, nên
                    # mất nó là mất đường về duy nhất.
                    #
                    # Chỉ test-bằng-mã không bắt được: job chạy đúng, Proxmox
                    # nhận lệnh, máy lên bình thường. Phải mở trình duyệt mới
                    # thấy (quy tắc 5 của CLAUDE.md).
                    "vga": "std"}
        cau_hinh.update(mang.cau_hinh_qemu(
            mang.mang_cho_may(gateway, ip_noi_bo), co_cloud_init=not iso,
            mac=dinh_danh.mac(may.id)))
        # GỠ mọi card thừa của template. `cau_hinh_qemu` chỉ đặt `net0`; template
        # nào có sẵn `net1` thì máy khách thừa hưởng nó — và nếu card đó cắm
        # `vmbr0` thì **máy bán cho khách có một chân trong LAN nhà**, đúng thứ
        # `mang.py` nói tuyệt đối không được có.
        #
        # Không lý thuyết: template `WIN10-LTSC-GOLD` có `net1`, và máy thử ngày
        # 24/08 hiện ra hai card ("Ethernet" và "Ethernet 2") trong Windows.
        cau_hinh.update(_go_card_thua(client, may.vmid))
        client.dat_cau_hinh(may.vmid, **cau_hinh)

        # Đường ISO đã tạo đĩa đúng cỡ ngay từ đầu; chỉ đường nhân bản mới cần
        # nới, vì đĩa của template luôn nhỏ hơn gói.
        can_dia = dia_tong_gb(may.plan_id, may.dia_them_gb)
        if not iso and can_dia > img.disk_gb_toi_thieu:
            # Proxmox chỉ nới ra, không thu vào — an toàn khi chạy lại.
            client.nong_dia(may.vmid, _dia_goc(client, may.vmid), f"{can_dia}G")

        # 4b) Đặt chỗ DHCP trên VM router — TRƯỚC khi bật máy.
        #
        # Máy khách tự cài Windows, và trình cài đặt Windows không đọc cloud-init.
        # DHCP là đường DUY NHẤT để máy có mạng mà khách không phải tự gõ địa chỉ.
        #
        # Hỏng ở đây thì job **hỏng hẳn**, không đi tiếp: giao cho khách một máy
        # bật được nhưng không có mạng là giao một cái vỏ, và họ sẽ mất buổi chiều
        # dò trong Windows một lỗi nằm ở router.
        _bao(ctx, 75, "dang dat cho dia chi")
        bo_dinh_tuyen.client_tu_moi_truong().dat_cho(
            dinh_danh.mac(may.id), ip_noi_bo, ten=f"vps-{may.id[:8]}")

        # 5) Bật máy.
        _bao(ctx, 85, "dang khoi dong")
        client.bat(may.vmid)

        # 6) IP công khai riêng. Mỗi máy một IP — xem `docs/VPS/GIAO_DIEN.md`.
        _bao(ctx, 92, "dang cap dia chi cong khai")
        ip_cong_khai = _cap_ip_cong_khai(db, may, gateway, ip_noi_bo)

        may.trang_thai = "dang_chay"
        may.ly_do = ""
        provisioning.ghi_su_kien(db, may.id, "tao_xong", boi="he_thong",
                                 vmid=may.vmid, ip_noi_bo=ip_noi_bo,
                                 ip_cong_khai=ip_cong_khai)
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
            "dia_chi": ip_cong_khai,
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


def _cap_ip_cong_khai(db, may: VpsInstance, gateway, ip_noi_bo: str) -> str:
    """Mua một IP công khai, gắn vào cổng vào, rồi mở đường 1:1 tới máy.

    **Thứ tự ở đây là thứ tự chống rò tiền, không phải thứ tự cho gọn.**

    Ghi vào CSDL NGAY sau khi mua, TRƯỚC khi gắn: nếu tiến trình chết giữa
    chừng, ta vẫn còn `vultr_id` để trả IP về. Làm ngược lại — gắn xong mới ghi —
    thì một lần chết là một IP mồ côi, **$3/tháng chảy mãi mà không ai biết nó
    của máy nào**. Cùng loại lỗi với H38 và với lỗi tiền của model nhà: thế giới
    thật đã đổi mà sổ sách chưa ghi.

    Chạy lại được: đã có bản ghi thì dùng lại, chỉ mở lại đường (thao tác mở
    đường tự nó cũng chạy lại được).
    """
    from sqlalchemy import select

    from apps.vps.services import gateway as cong_vao
    from apps.vps.services import vultr as nha_cung_cap
    from apps.vps.tables import VpsIp

    if not gateway.cho_phep_ip_rieng:
        return ""

    cu = db.execute(select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    if cu is None:
        khach = nha_cung_cap.client_tu_moi_truong()
        ip = khach.tao_ip(may.id[:8])
        try:
            # Vultr **cấp lại chính địa chỉ vừa trả** (nó giữ 24 giờ rồi đưa lại
            # cho cùng tài khoản) — đã thấy thật 24/08. Nên phải hỏi xem địa chỉ
            # này đã có dòng nào chưa, thay vì INSERT thẳng rồi chết vì ràng buộc
            # duy nhất. Chết ở đây nghĩa là **tiền đã tiêu mà sổ sách không có**.
            trung = db.execute(select(VpsIp).where(
                VpsIp.gateway_id == gateway.id,
                VpsIp.dia_chi == ip["dia_chi"])).scalars().first()
            if trung is not None and trung.instance_id:
                raise VpsJobError(
                    f"Vultr cap dia chi {ip['dia_chi']} nhung so sach ghi no dang "
                    f"thuoc may {trung.instance_id} — dung lai, khong ghi de")
            if trung is not None:
                trung.vultr_id, trung.nhan = ip["id"], ip["nhan"]
                trung.instance_id = may.id
                cu = trung
            else:
                cu = VpsIp(gateway_id=gateway.id, dia_chi=ip["dia_chi"],
                           vultr_id=ip["id"], nhan=ip["nhan"], instance_id=may.id)
                db.add(cu)
            db.commit()                 # ← ghi TRƯỚC khi gắn. Xem docstring.
        except Exception:
            # Ghi sổ hỏng thì TRẢ IP VỀ NGAY. Không làm bước này là mỗi lần lỗi
            # để lại $3/tháng chảy mãi, và không ai biết nó của máy nào.
            db.rollback()
            try:
                khach.xoa_ip(ip["id"])
                log.warning("VPS: da tra lai IP %s vi khong ghi duoc so sach",
                            ip["dia_chi"])
            except nha_cung_cap.VultrError as loi_tra:
                log.error("VPS: RO TIEN — mua IP %s (%s) nhung khong ghi so va "
                          "khong tra lai duoc: %s", ip["dia_chi"], ip["id"], loi_tra)
            raise
        khach.gan_ip(ip["id"], _id_cong_vao(gateway, khach))

    cong_vao.client_tu_moi_truong().mo_duong(cu.dia_chi, ip_noi_bo)
    return str(cu.dia_chi)


def _id_cong_vao(gateway, khach) -> str:
    """Id của cổng vào bên nhà cung cấp. Khai sẵn thì dùng, chưa thì tra theo nhãn."""
    if gateway.nha_cung_cap_id:
        return str(gateway.nha_cung_cap_id)
    return str(khach.instance_theo_nhan(gateway.ten)["id"])


def _tra_ip_cong_khai(db, may: VpsInstance) -> None:
    """Đóng đường rồi trả IP về cho nhà cung cấp — tức **ngừng tính tiền**.

    Ngược thứ tự với lúc cấp: đóng đường trước (để không còn ai đi qua), rồi mới
    gỡ và xoá. Lỗi ở bất kỳ bước nào cũng **không** được chặn việc xoá máy —
    nhưng phải ghi lại, vì một IP không trả về là tiền chảy mãi.
    """
    from sqlalchemy import select

    from apps.vps.services import gateway as cong_vao
    from apps.vps.services import vultr as nha_cung_cap
    from apps.vps.tables import VpsIp

    for ip in db.execute(select(VpsIp).where(VpsIp.instance_id == may.id)).scalars():
        try:
            if may.ip_noi_bo:
                cong_vao.client_tu_moi_truong().dong_duong(ip.dia_chi, may.ip_noi_bo)
            khach = nha_cung_cap.client_tu_moi_truong()
            if ip.vultr_id:
                khach.go_ip(ip.vultr_id)
                khach.xoa_ip(ip.vultr_id)
            # XOÁ hẳn bản ghi, không chỉ gỡ liên kết: IP đã không còn ở nhà cung
            # cấp nữa, nên giữ dòng đó lại là nói dối rằng ta vẫn có nó. Và nó
            # gây hại thật — Vultr **cấp lại chính địa chỉ vừa trả** (đã thấy
            # 24/08), và bản ghi cũ làm INSERT mới chết vì ràng buộc duy nhất
            # `(gateway_id, dia_chi)`, tức máy TIẾP THEO của khách không tạo được.
            db.delete(ip)
        except (nha_cung_cap.VultrError, cong_vao.GatewayError) as exc:
            # Bắt HẸP, không `except Exception`: lỗi lập trình phải nổ lên trên.
            # Còn nhà cung cấp từ chối hay cổng vào không trả lời thì KHÔNG được
            # chặn việc xoá máy — nhưng phải ghi lại, vì một IP không trả về là
            # tiền chảy mãi.
            log.warning("VPS: khong tra duoc IP %s cua may %s: %s",
                        ip.dia_chi, may.id, exc)
            # Giữ bản ghi lại (gỡ liên kết thôi) để con người còn dọn được —
            # đây là trường hợp DUY NHẤT một dòng `vps_ip` được phép sống sót
            # sau khi máy bị xoá.
            ip.instance_id = None
            provisioning.ghi_su_kien(
                db, may.id, "ip_chua_tra_duoc", boi="he_thong",
                dia_chi=ip.dia_chi, vultr_id=ip.vultr_id, loi=str(exc)[:200])


def _template_noi_bo(os_id: str) -> int:
    """VMID template cho bản Linux **nội bộ**. 0 = không có.

    ## Hàng rào, không phải tuỳ chọn

    Mô hình template đã bị bỏ ngày 2026-08-24: máy bán cho khách luôn là máy
    trống + đĩa cài, khách tự đặt tài khoản và mật khẩu của chính họ.

    Đường này chỉ còn sống cho bản có `khach_thay=False` — bản Linux nội bộ lên
    trong ~40 giây, dùng để tách "lỗi đường ống" khỏi "lỗi trong lúc cài Windows".

    **Nếu ai đó sau này đặt `LTT_VPS_TEMPLATE_WIN10` thì hàm này TỪ CHỐI**, thay
    vì lặng lẽ quay lại mô hình cũ. Không có hàng rào đó thì một biến môi trường
    gõ nhầm là mọi khách nhận chung một mật khẩu — và không lỗi nào được ghi ra.
    """
    import os as _os

    img = os_images.lay_os(os_id)
    if img is None or img.khach_thay:
        return 0
    khoa = "LTT_VPS_TEMPLATE_" + str(os_id or "").upper().replace("-", "_")
    try:
        return int(str(_os.environ.get(khoa, "")).strip() or 0)
    except ValueError:
        return 0


def _cau_hinh_may_trong(may: VpsInstance, plan, img, iso: str) -> dict:
    """Cấu hình một máy TRỐNG có gắn đĩa cài đặt, để khách tự cài.

    Ba lựa chọn ở đây đều là **luật của cụm này**, không phải sở thích:

    * **`sata0` + `e1000`** — cụm chạy lồng trong VMware và virtio treo cứng ở
      đó (xem `MO_HINH_CARD` trong `mang.py`). Đây cũng là lý do khách **không
      cần đĩa driver virtio** khi cài Windows: Windows nhận sẵn cả hai.
    * **`vga: std`** — máy phải có màn hình đồ hoạ, vì console LÀ đường cài đặt.
    * **thứ tự boot `ide0` rồi `sata0`** — lần đầu boot vào đĩa cài; cài xong,
      không bấm phím nào thì nó tự bỏ qua CD và boot vào đĩa cứng. Khách bấm
      "Tôi đã cài xong" thì `dieu_khien.go_dia_cai` tháo hẳn `ide0` ra.
    """
    cau_hinh = {
        "name": f"vps-{may.id[:8]}",
        "cores": plan.vcpu,
        "memory": plan.ram_mb,
        # `win10` là ostype Proxmox khuyên dùng cho **cả** Server 2016/2019/2022
        # lẫn Windows 10 — nó chỉ chỉnh vài mặc định của QEMU, không phải một
        # tuyên bố về phiên bản.
        "ostype": "win10" if img.ho == "windows" else "l26",
        "scsihw": "virtio-scsi-single",
        # `serial=` KHÔNG thừa: QEMU đặt số hiệu ổ theo *chỉ số ổ*, nên mọi
        # máy dùng `sata0` báo về cùng một chuỗi. Xem `services/dinh_danh.py`.
        "sata0": f"{KHO_DIA}:{dia_tong_gb(may.plan_id, may.dia_them_gb)},"
                 f"discard=on,ssd=1,serial={dinh_danh.so_hieu_dia(may.id)}",
        "ide0": f"{iso},media=cdrom",
        "boot": "order=ide0;sata0",
        "vga": "std",
        # UUID đặt tường minh để nó sống sót qua lần CÀI LẠI — Proxmox chỉ sinh
        # UUID lúc tạo máy, nên cài lại cho ra một UUID khác, và với phần mềm
        # trong máy khách thì đó là "một máy khác".
        "smbios1": dinh_danh.smbios1(may.id),
        # Không guest agent, không balloon: cả hai là thiết bị virtio.
        "agent": 0,
        "balloon": 0,
        # MỘT đường BIOS cho mọi bản đang bán. Trước 24/08 ở đây có nhánh thứ
        # hai (`ovmf` + `efidisk0` + `tpmstate0`) cho Windows 11 — nhánh mà
        # **không bản nào khác đi qua**, tức không lần chạy nào thử tới nó.
        # Windows 11 không còn trong danh mục (xem `os_images.py`), nên nhánh đó
        # đã gỡ thay vì để nằm lại mục dần.
        "bios": "seabios",
        "machine": "pc-q35-11.0",
    }
    return cau_hinh


def _go_card_thua(client, vmid: int) -> dict:
    """Tham số `qm set` để xoá `net1`, `net2`… của template. Chỉ giữ `net0`.

    Trả một dict `{"delete": "net1,net2"}` để gộp chung vào một lần gọi cấu
    hình — Proxmox nhận `delete` là danh sách tên khoá ngăn bằng dấu phẩy.
    """
    try:
        cfg = client._goi("GET", f"/nodes/{client.config.node}/qemu/{int(vmid)}/config") or {}
    except ProxmoxError:
        return {}
    thua = sorted(k for k in cfg
                  if k.startswith("net") and k != "net0" and k[3:].isdigit())
    return {"delete": ",".join(thua)} if thua else {}


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
    """Cài lại từ đầu: xoá VM cũ, giữ nguyên bản ghi và **IP công khai đã cấp**.

    Giữ IP là cố ý — khách đã lưu địa chỉ đó, đã trỏ tên miền vào đó, đã cấu hình
    client. Đổi IP khi cài lại là bắt khách đi tìm địa chỉ mới mà không có lý do
    gì, và với Vultr thì còn tốn thêm tiền cho một IP mới.
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
                # Cùng cái bẫy đã dính ở đường xoá: `tat_cung` là tác vụ NỀN,
                # gọi `xoa` ngay sau đó thì Proxmox trả 500 và không nói vì sao.
                _cho_tac_vu(client, client.tat_cung(may.vmid), ctx, moc=20)
            except ProxmoxError:
                pass                      # máy đã tắt sẵn — không phải lỗi
            except VpsJobError:
                pass                      # tắt không xong thì vẫn thử xoá
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
                # PHẢI chờ tác vụ tắt xong. `tat_cung` là tác vụ NỀN: gọi `xoa`
                # ngay sau đó thì Proxmox trả **500** vì máy còn đang chạy hoặc
                # còn khoá. Đã dính thật 24/08 — và triệu chứng chỉ là "500",
                # không nói gì về nguyên nhân.
                _cho_tac_vu(client, client.tat_cung(may.vmid), ctx, moc=40)
            except ProxmoxError:
                pass          # máy đã tắt sẵn — không phải lỗi, vẫn xoá tiếp
            except VpsJobError:
                pass          # tắt không xong thì vẫn thử xoá; `purge` cưỡng chế
            _bao(ctx, 50, "dang xoa dia")
            upid = client.xoa(may.vmid)
            _cho_tac_vu(client, upid, ctx, moc=70)

        _bao(ctx, 78, "dang go cho dia chi")
        _go_cho_dhcp(may)

        _bao(ctx, 80, "dang tra dia chi cong khai")
        _tra_ip_cong_khai(db, may)
        _nha_tai_nguyen(db, may)
        may.trang_thai = "da_xoa"
        provisioning.ghi_su_kien(db, may.id, "da_xoa",
                                 boi=str(params.get("boi") or "he_thong"))
        db.commit()
        _bao(ctx, 100, "xong")
        return {"instance_id": may.id, "vmid": may.vmid}
    finally:
        gen.close()


def _go_cho_dhcp(may: VpsInstance) -> None:
    """Gỡ đặt chỗ DHCP của một máy sắp bị xoá.

    Router không trả lời thì **không chặn việc xoá máy** — máy đã đi rồi, giữ nó
    lại vì một tệp cấu hình không sửa được là chọn cái tệ hơn.

    Chỗ thừa cũng không kẹt máy sau: `dat_cho` xoá dòng cũ theo **cả MAC lẫn địa
    chỉ**, nên máy tiếp theo nhận đúng địa chỉ này vẫn đăng ký được.
    """
    try:
        bo_dinh_tuyen.client_tu_moi_truong().go_cho(dinh_danh.mac(may.id))
    except bo_dinh_tuyen.RouterError as exc:
        # Bắt HẸP: lỗi lập trình phải nổ lên trên.
        log.warning("VPS: khong go duoc cho DHCP cua may %s: %s", may.id, exc)


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
