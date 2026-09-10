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

from contextlib import contextmanager
from datetime import timedelta

import logging
import os

from apps.vps import nhan, os_images, trang_thai_may
from apps.vps.cost import dia_tong_gb, lay_plan
from apps.vps.services import dinh_danh, mang, provisioning, tac_vu
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

#: Nhịp hỏi lại trạng thái tác vụ (giây).
#:
#: ⚠️ Trần thời gian KHÔNG còn là hằng số ở đây. Nó lấy theo `max_runtime_s` của
#: chính job đang chạy — xem `tac_vu.han_theo_job`. Hằng số cũ (`CHO_TAC_VU_S =
#: 20*60`) dùng chung cho cả `vps.destroy`, mà job đó chỉ có trần **600 giây**:
#: bộ chờ không bao giờ tới lượt bỏ cuộc.
NHIP_HOI_S = 5


class VpsJobError(RuntimeError):
    """Lỗi có thông điệp đọc được. Ném ra để nền tảng hoàn credit đã giữ."""


#: Khoa song bao lau truoc khi bi thu hoi. Dai hon `max_runtime_s` cua job dai
#: nhat (`vps.provision`, 1800 giay) de mot job cham KHONG bi cuop khoa giua
#: chung. Doi lai: mot worker chet de lai khoa treo toi 45 phut — chap nhan
#: duoc, vi may cua mot job vua chet cung khong phai thu nen dung vao ngay.
KHOA_MAY_TTL = timedelta(minutes=45)


@contextmanager
def _khoa_may(instance_id: str, job_type: str):
    """Giu khoa doc quyen cho MOT may trong suot mot job.

    ## Vi sao can

    Truoc 25/08 hai job tren cung mot may chay song song duoc. Duong that:
    khach bam "Cai lai" roi doi y bam "Xoa"; hoac vong bao tri nop job xoa
    (qua han an han) dung luc khach bam "Cai lai".

    Ket qua: mot job xoa VM trong khi job kia dang dung no. Proxmox tra 500
    o mot cho ngau nhien, may nam lai nua voi, va dia chi trong mang rieng
    co the bi nha trong khi VM van con — tuc **may khach tiep theo nhan dung
    dia chi do**.

    ## Vi sao dung lease cua nen tang

    `platform_core/leases.py` sinh ra cho dung lop van de nay (H36) va da
    duoc dung cho vong bao tri. Dung lai no thay vi tu dung mot bang khoa
    thu hai: hai co che khoa trong mot he thong la hai co che se lech nhau.

    Khoa chay tren **phien rieng**: `leases.acquire` co commit ben trong, va
    dung chung phien voi job se commit nhung thay doi con dang do.
    """
    from platform_core import leases

    ten = f"vps-may:{instance_id}"
    db, gen = _mo_db()
    try:
        khoa = leases.acquire(db, name=ten, ttl=KHOA_MAY_TTL)
        if khoa is None:
            # KHONG phai loi lap trinh: mot job khac dang lam viec tren may
            # nay. Nem de hang doi thu lai — `max_attempts` cua manifest lo
            # phan con lai, va viec nay tu giai quyet trong vai giay.
            raise VpsJobError(
                f"may {instance_id} dang co job khac chay ({job_type}); "
                f"hang doi se thu lai")
        try:
            yield
        finally:
            try:
                leases.release(db, khoa)
            except Exception:            # noqa: BLE001
                # Khong nha duoc thi khoa tu het han sau TTL. Ghi lai, nhung
                # KHONG de no che mat ket qua (hay ngoai le) cua chinh job.
                log.exception("vps: khong nha duoc khoa %s", ten)
    finally:
        gen.close()


def handle(params: dict, ctx=None) -> dict:
    """Diem vao duy nhat; phan nhanh theo `ctx.job_type` (hop dong nen tang).

    Moi nhanh chay **duoi mot khoa theo may** — xem `_khoa_may`.
    """
    job_type = getattr(ctx, "job_type", "") or str(params.get("job_type", ""))
    nhanh = {"vps.provision": _tao_may,
             "vps.rebuild": _dung_lai,
             "vps.destroy": _xoa_may,
             "vps.control": _dieu_khien_may,
             "vps.snapshot": _khoi_phuc_anh}.get(job_type)
    if nhanh is None:
        raise VpsJobError(f"job_type khong biet: {job_type!r}")

    instance_id = str(params.get("instance_id") or "")
    if not instance_id:
        raise VpsJobError("thieu instance_id")

    with _khoa_may(instance_id, job_type):
        return nhanh(params, ctx)


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


def _cho_tac_vu(client, upid: str, ctx=None, *, moc: int = 30,
                thong_diep: str = "dang chuan bi may") -> None:
    """Chờ một tác vụ nền của Proxmox xong. Ném `VpsJobError` nếu hỏng/quá hạn.

    ## Chỉ còn là một lớp mỏng — bản thật ở `services/tac_vu.py`

    Trước VPS V2 đây là **chỗ duy nhất** trong cả app biết chờ một UPID, nên ba
    đường còn lại (bật, tắt, khôi phục) không chờ gì cả. Giữ hai bản là để sửa
    một bên và quên bên kia; nên phần logic đã dời sang `services/tac_vu.py`, và
    ở đây chỉ còn phần thuộc về **job**: báo tiến độ và dịch lỗi.

    Trần thời gian nay lấy theo **chính job đang chạy** chứ không phải một hằng
    số chung: `vps.destroy` có `max_runtime_s=600`, nên một bộ chờ 1200 giây
    trong đó không bao giờ tới lượt bỏ cuộc — nền tảng cắt job trước, và cái
    chết đó trông giống hệt một job treo. Xem `tac_vu.han_theo_job`.
    """
    han = tac_vu.han_theo_job(getattr(ctx, "job_type", "") or "")
    try:
        tac_vu.cho_xong(client, upid, han_s=han, nhip_s=NHIP_HOI_S,
                        bao=lambda _tt: _bao(ctx, moc, thong_diep))
    except tac_vu.TacVuLoi as exc:
        raise VpsJobError(str(exc)) from exc


# ── vps.control ─────────────────────────────────────────────────────────────

#: Tiến độ báo cho khách theo bước con. Bốn con số, không phải một thanh chạy
#: mượt: khách cần biết **đang ở đâu**, và một thanh 37% không nói được điều đó.
_TIEN_DO_BUOC = {
    "gui_lenh_tat": 10,
    "cho_may_tat": 30,
    "gui_lenh_bat": 60,
    "cho_may_bat": 80,
}


def _dieu_khien_may(params: dict, ctx=None) -> dict:
    """Bật / tắt / khởi động lại — chạy tới nơi tới chốn rồi mới kết luận.

    ## Vì sao thao tác được tra lại từ CSDL chứ không dựng mới

    Job có thể chạy lại. Dựng một thao tác mới ở mỗi lần chạy là đẻ ra ba dòng
    "đang khởi động lại" cho một cú bấm, và mất đúng thứ cần nhất khi chạy lại:
    `upid` và `buoc` của lần trước — thứ cho biết pha tắt đã xong hay chưa.
    """
    from apps.vps.services import dieu_khien, tac_vu as bo_cho, thao_tac
    from apps.vps.tables import VpsThaoTac

    lenh = str(params.get("lenh") or "")
    db, gen = _mo_db()
    op = None
    try:
        may = _lay_may(db, params.get("instance_id"))
        op = db.get(VpsThaoTac, str(params.get("thao_tac_id") or ""))
        if op is None:
            raise VpsJobError("khong tim thay thao tac cua lenh nay")
        if op.tinh_trang not in thao_tac.DANG_MO:
            # Job chạy lại sau khi thao tác đã kết thúc. Không làm gì, không lỗi
            # — bắn lại một lệnh điện cho một việc đã xong là đúng thứ cần tránh.
            return {"instance_id": may.id, "lenh": lenh, "da_xong_truoc_do": True}

        thao_tac.bat_dau(db, op)
        db.commit()

        def _luu() -> None:
            _bao(ctx, _TIEN_DO_BUOC.get(str(op.buoc or ""), 50), str(op.buoc or ""))
            db.commit()

        client = client_tu_moi_truong()
        dien = dieu_khien.thi_hanh(db, may, client, op, lenh=lenh, luu=_luu)

        thao_tac.xong(db, op, may, dien_sau=dien)
        provisioning.ghi_su_kien(db, may.id, lenh,
                                 boi=str(params.get("boi") or "he_thong"),
                                 thao_tac_id=op.id, dien=dien)
        db.commit()
        _bao(ctx, 100, "xong")
        return {"instance_id": may.id, "lenh": lenh, "dien": dien}
    except bo_cho.TacVuLoi as exc:
        # Hỏng **có phân loại**: `qua_han` khác `that_bai` khác `dien_khong_dat`,
        # và ba cái đó cần ba câu trả lời khác nhau cho khách (Pha 08/09).
        _ghi_thao_tac_hong(db, op, params, lenh, exc.ma, str(exc))
        raise VpsJobError(str(exc)) from exc
    except ProxmoxError as exc:
        _ghi_thao_tac_hong(db, op, params, lenh, "proxmox_tu_choi", str(exc))
        raise VpsJobError(f"Proxmox tu choi lenh: {exc}") from exc
    finally:
        gen.close()


def _ghi_thao_tac_hong(db, op, params: dict, lenh: str, ma: str,
                       chi_tiet: str) -> None:
    """Đóng thao tác là **hỏng** và ghi nhật ký. Không được che lỗi gốc."""
    from apps.vps.services import thao_tac

    try:
        db.rollback()
        may = db.get(VpsInstance, str(params.get("instance_id") or ""))
        if op is not None:
            op = db.get(type(op), op.id)
        if op is not None:
            thao_tac.hong(db, op, may, ma_loi=ma, chi_tiet=chi_tiet,
                          qua_han=(ma == "tac_vu_qua_han"))
        if may is not None:
            # Máy KHÔNG bị đẩy sang `loi`: một lần tắt mềm quá hạn không làm máy
            # hỏng, nó chỉ làm ta không biết máy đang ở đâu. Đẩy sang `loi` là
            # nói quá, và nó khoá mất những nút mà khách cần để tự gỡ.
            trang_thai_may.dat(may, dien_quan_sat=trang_thai_may.KHONG_RO,
                               suc_khoe=trang_thai_may.KHONG_RO)
            provisioning.ghi_su_kien(
                db, may.id, f"{lenh}_that_bai",
                boi=str(params.get("boi") or "he_thong"),
                ma_loi=ma, loi=chi_tiet[:200])
        db.commit()
    except Exception:            # noqa: BLE001 - ghi lỗi không được che lỗi gốc
        log.exception("vps: khong ghi duoc that bai cua lenh %r", lenh)


def _tat_de_xoa(client, may, ctx=None, *, moc: int = 30) -> str:
    """Tắt cứng một máy **sắp bị xoá**, rồi xác minh. Trả điện đo được cuối cùng.

    ## Vì sao một hàm chung cho `_dung_lai` và `_xoa_may`

    Trước Pha 10 đây là **hai bản sao** của cùng một khối mười dòng, trong hai
    hàm cách nhau bốn mươi dòng. Hai bản sao của một khối khó là hai chỗ sẽ lệch
    nhau, và ở đây chúng đã lệch: một bản ghi *"tắt không xong thì vẫn thử xoá"*,
    bản kia ghi thêm *"`purge` cưỡng chế"* — một khẳng định về hành vi Proxmox mà
    **không lượt chạy nào ở đây kiểm được**.

    ## Vì sao vẫn đi tiếp khi tắt không xong

    Vì máy đang trên đường bị xoá: dữ liệu sẽ mất theo thiết kế, nên một lần tắt
    cứng thất bại không đổi kết cục. Cái ĐỔI là ta **biết** điều đó thay vì đoán:
    hàm này hỏi lại thế giới thật và ghi ra trạng thái đo được, nên khi `client.xoa`
    trả lỗi thì log có sẵn câu trả lời cho *"vì sao"* — thay vì một dòng "500".

    ⚠️ Chỉ dùng cho đường **xoá/dựng lại**. Đừng gọi nó ở đường điều khiển: ở đó
       một lần tắt không xong là một lý do để DỪNG, không phải để đi tiếp.
    """
    from apps.vps.services import tac_vu

    try:
        _cho_tac_vu(client, client.tat_cung(may.vmid), ctx, moc=moc)
    except (ProxmoxError, VpsJobError) as exc:
        # Bắt HẸP hai loại: `ProxmoxError` (máy đã tắt sẵn, hoặc node từ chối)
        # và `VpsJobError` (tác vụ hỏng/quá hạn). Lỗi lập trình vẫn nổ lên trên.
        log.info("VPS: tat cung may %s truoc khi xoa khong xong: %s", may.id, exc)

    dien = tac_vu.doc_dien(client, may.vmid)
    if dien != trang_thai_may.TAT:
        log.warning("VPS: may %s van o trang thai %r khi bat dau xoa — "
                    "Proxmox co the tu choi lenh xoa", may.id, dien)
    return dien


# ── vps.snapshot ────────────────────────────────────────────────────────────

_TIEN_DO_KHOI_PHUC = {
    "tat_truoc_khoi_phuc": 15,
    "dang_khoi_phuc_anh": 45,
    "bat_lai_sau_khoi_phuc": 80,
}


def _khoi_phuc_anh(params: dict, ctx=None) -> dict:
    """Khôi phục máy về một ảnh chụp — **phá huỷ dữ liệu**, nên chạy có sổ sách.

    Cùng khuôn với `_dieu_khien_may`: tra lại thao tác từ CSDL (không dựng mới),
    chạy tới nơi tới chốn, rồi mới kết luận. Khác ở chỗ hỏng ở đây đắt hơn nhiều
    — xem `sao_luu.thi_hanh_khoi_phuc` về việc chạy lại.
    """
    from apps.vps.services import sao_luu, tac_vu as bo_cho, thao_tac
    from apps.vps.tables import VpsThaoTac

    ten_anh = str(params.get("anh") or "")
    db, gen = _mo_db()
    op = None
    try:
        may = _lay_may(db, params.get("instance_id"))
        op = db.get(VpsThaoTac, str(params.get("thao_tac_id") or ""))
        if op is None:
            raise VpsJobError("khong tim thay thao tac khoi phuc")
        if op.tinh_trang not in thao_tac.DANG_MO:
            return {"instance_id": may.id, "da_xong_truoc_do": True}

        thao_tac.bat_dau(db, op)
        db.commit()

        def _luu() -> None:
            _bao(ctx, _TIEN_DO_KHOI_PHUC.get(str(op.buoc or ""), 50),
                 str(op.buoc or ""))
            db.commit()

        client = client_tu_moi_truong()
        dien = sao_luu.thi_hanh_khoi_phuc(db, may, client, op, ten=ten_anh,
                                          luu=_luu)
        thao_tac.xong(db, op, may, dien_sau=dien)
        provisioning.ghi_su_kien(db, may.id, "khoi_phuc",
                                 boi=str(params.get("boi") or "he_thong"),
                                 anh=ten_anh, thao_tac_id=op.id)
        db.commit()
        _bao(ctx, 100, "xong")
        return {"instance_id": may.id, "anh": ten_anh, "dien": dien}
    except bo_cho.TacVuLoi as exc:
        _ghi_thao_tac_hong(db, op, params, "khoi_phuc", exc.ma, str(exc))
        raise VpsJobError(str(exc)) from exc
    except sao_luu.SaoLuuError as exc:
        _ghi_thao_tac_hong(db, op, params, "khoi_phuc", "anh_khong_dung",
                           str(exc))
        raise VpsJobError(str(exc)) from exc
    except ProxmoxError as exc:
        _ghi_thao_tac_hong(db, op, params, "khoi_phuc", "proxmox_tu_choi",
                           str(exc))
        raise VpsJobError(f"Proxmox tu choi lenh: {exc}") from exc
    finally:
        gen.close()


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
        # **Chỉ còn MỘT đường.** Ba template cuối cùng đã bị xoá khỏi cụm ngày
        # 24/08, nên nhánh `clone` không còn đối tượng nào để nhân bản — và một
        # nhánh không ai đi qua trong đường tạo máy là một nhánh không ai thử.
        iso = os_images.dia_cai_dat(may.os_id)
        if not iso:
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
            upid = client.tao_may(
                may.vmid, **_cau_hinh_may_trong(may, plan, img, iso))
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
                    # `vga` PHẢI đặt tường minh. Một máy mang `vga: serial0`
                    # (để đọc log khởi động qua cổng nối tiếp) thì **không có
                    # màn hình đồ hoạ nào cả**, và console trong trình duyệt mở
                    # ra chỉ thấy một kết nối bị đóng ngay. Với khách Windows
                    # thì console là
                    # ĐƯỜNG CỨU HỘ khi họ tự chặn mất RDP của chính mình, nên
                    # mất nó là mất đường về duy nhất.
                    #
                    # Chỉ test-bằng-mã không bắt được: job chạy đúng, Proxmox
                    # nhận lệnh, máy lên bình thường. Phải mở trình duyệt mới
                    # thấy (quy tắc 5 của CLAUDE.md).
                    "vga": "std"}
        cau_hinh.update(mang.cau_hinh_qemu(
            # `co_cloud_init=False` **luôn**: máy khách tự cài Windows, không
            # có ổ cloud-init nào. Địa chỉ tới máy bằng DHCP theo MAC.
            mang.mang_cho_may(gateway, ip_noi_bo), co_cloud_init=False,
            mac=dinh_danh.mac(may.id)))
        # GỠ mọi card thừa. `cau_hinh_qemu` chỉ đặt `net0`, nên một máy có sẵn
        # `net1` sẽ GIỮ nó — và nếu card đó cắm `vmbr0` thì **máy bán cho khách
        # có một chân trong LAN nhà**, đúng thứ `mang.py` nói tuyệt đối không
        # được có.
        #
        # Mô hình template đã bỏ, nhưng luật này KHÔNG thừa: job chạy lại trên
        # một máy đã có, và `vps.rebuild` cũng đi qua đây. Nó từng bắt được lỗi
        # thật — máy thử 24/08 hiện ra hai card trong Windows.
        cau_hinh.update(_go_card_thua(client, may.vmid))
        client.dat_cau_hinh(may.vmid, **cau_hinh)

        # 4b) Đặt chỗ DHCP trên VM router — TRƯỚC khi bật máy.
        #
        # Máy khách tự cài Windows, và trình cài đặt Windows không đọc cloud-init.
        # DHCP là đường DUY NHẤT để máy có mạng mà khách không phải tự gõ địa chỉ.
        #
        # Hỏng ở đây thì job **hỏng hẳn**, không đi tiếp: giao cho khách một máy
        # bật được nhưng không có mạng là giao một cái vỏ, và họ sẽ mất buổi chiều
        # dò trong Windows một lỗi nằm ở router.
        _bao(ctx, 75, "dang dat cho dia chi")
        rt = bo_dinh_tuyen.client_tu_moi_truong()
        rt.dat_cho(dinh_danh.mac(may.id), ip_noi_bo, ten=f"vps-{may.id[:8]}")
        # Bật đếm băng thông cùng lúc với lúc cấp địa chỉ, không phải "khi nào
        # nhớ ra": máy không nằm trong hai set đếm thì gói của nó không khớp luật
        # đếm nào, và nó dùng bao nhiêu cũng không ai biết — im lặng.
        rt.theo_doi_bang_thong(ip_noi_bo)

        # 5) Bật máy — và **chờ nó bật thật**.
        #
        # Bản cũ bắn `bat()` rồi ghi ngay `dang_chay`. Nghĩa là một máy không
        # khởi động được (kho đầy, cấu hình sai, node hết RAM) vẫn được giao cho
        # khách kèm chữ "Đang chạy", và họ mở console ra thấy một màn hình đen.
        # Đó là V-02 ở đúng chỗ đắt nhất: ngay sau khi đã thu tiền.
        _bao(ctx, 85, "dang khoi dong")
        # `int(may.vmid)` chu khong `may.vmid`: toi day thi VMID chac chan da
        # duoc cap (buoc 1), nhung kieu tinh cua no van la `int | None`. Ep kieu
        # o day thay vi de mypy phai tin mot bat bien no khong doc duoc.
        vmid = int(may.vmid)
        dien = tac_vu.cho_va_xac_minh(
            client, client.bat(vmid), vmid, trang_thai_may.CHAY,
            han_tac_vu_s=tac_vu.han_theo_job(getattr(ctx, "job_type", "")))

        # 6) IP công khai riêng. Mỗi máy một IP — xem `docs/VPS/GIAO_DIEN.md`.
        _bao(ctx, 92, "dang cap dia chi cong khai")
        ip_cong_khai = _cap_ip_cong_khai(db, may, gateway, ip_noi_bo)

        # `dien` là số ĐO ĐƯỢC ở bước 5, không phải một giả định: tới dòng này
        # thì máy đã thật sự chạy, đã được hỏi lại, và câu "Đang chạy" trên
        # trang khách là một khẳng định có bằng chứng.
        trang_thai_may.dat(may, vong_doi=trang_thai_may.HOAT_DONG,
                           dien_mong_muon=trang_thai_may.CHAY,
                           tac_vu=trang_thai_may.KHONG_CO, ly_do="")
        trang_thai_may.ghi_quan_sat(may, dien)
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

    # ⛔ Máy đang bị cách ly thì **không** mở lại đường, kể cả khi đang cài lại.
    #
    #    Không có phép kiểm này thì "Cài lại" trở thành một nút gỡ cách ly mà
    #    khách tự bấm được — im lặng, không ghi sổ, và người vận hành vẫn thấy
    #    `cach_ly_luc` khác NULL nên tưởng máy vẫn bị cắt.
    from apps.vps.services import cach_ly as bo_cach_ly

    if bo_cach_ly.dang_bi_cach_ly(may):
        log.warning("VPS: may %s dang bi cach ly — KHONG mo duong NAT", may.id)
        return str(cu.dia_chi)

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


def _ma_loi_cua(exc: Exception) -> str:
    """Ngoại lệ → **mã** lỗi, cùng bộ từ vựng mà `_ghi_thao_tac_hong` đang ghi.

    Một bộ mã, không phải hai. Nếu hàm này đẻ ra bộ mã riêng thì cùng một sự cố
    sẽ mang hai tên khác nhau ở `vps_thao_tac.ma_loi` và ở `may.ly_do`, và không
    ai nối được hai hàng đó lại khi khách hỏi.
    """
    # `sao_luu` nạp muộn vì nó nạp ngược lại `jobs`; `ProxmoxError` thì đã có
    # sẵn ở mức module nên dùng lại, đừng nạp bản thứ hai.
    from apps.vps.services.sao_luu import SaoLuuError

    ma = getattr(exc, "ma", "")          # họ `bo_cho.TacVuLoi` tự khai mã
    if isinstance(ma, str) and ma:
        return ma
    if isinstance(exc, SaoLuuError):
        return "anh_khong_dung"
    if isinstance(exc, ProxmoxError):
        return "proxmox_tu_choi"
    return "khong_ro"


def _danh_dau_loi(db, instance_id, exc: Exception) -> None:
    """Ghi lý do vào máy, **bằng câu viết cho khách**.

    ⛔ Trước 09/09/2026 dòng này ghi `f"{type(exc).__name__}: {exc}"`, và cả hai
       chỗ đọc nó — `may.ly_do` trên trang máy, và `thong_diep` trong nhật ký —
       đều là **trang của khách**. Đo trên production: khách thấy nguyên văn
       `VpsJobError: Proxmox tu choi lenh: …`, tức tên class Python cộng tên lớp
       hạ tầng mà `services/proxmox.py` nói khách "không bao giờ nhìn thấy".

    ⭐ Chi tiết kỹ thuật **không bị vứt** — đó là điều kiện để bản vá này đúng.
       Nó đi vào `log.warning` (người vận hành đọc) và, với mọi đường đã mở một
       thao tác, vào `vps_thao_tac.chi_tiet_loi` giữ 180 ngày. Đổi một lỗi lộ
       liễu lấy một lỗi **im lặng** thì tốn nhiều giờ hơn, không ít hơn.
    """
    try:
        db.rollback()
        may = db.get(VpsInstance, str(instance_id or ""))
        if may is None:
            return
        ma = _ma_loi_cua(exc)
        # Ghi thô ra log TRƯỚC khi ghi CSDL: nếu `commit` hỏng, thứ ta cần để
        # chẩn đoán vẫn phải còn ở đâu đó.
        log.warning("vps: may %r hong (%s): %s: %s",
                    getattr(may, "id", instance_id), ma,
                    type(exc).__name__, exc)
        # Tác vụ về rỗng: việc đã kết thúc — thất bại vẫn là kết thúc. Để nguyên
        # `tac_vu` là để lại một cái khoá mềm khiến khách không bấm được gì nữa
        # trên một máy đang lỗi, tức lấy mất đúng nút "Cài lại" mà họ cần.
        trang_thai_may.dat(may, vong_doi=trang_thai_may.LOI,
                           dien_quan_sat=trang_thai_may.KHONG_RO,
                           tac_vu=trang_thai_may.KHONG_CO,
                           ly_do=nhan.ma_loi(ma)[:2000])
        # `ma_loi` vào sự kiện là mã, không phải câu: nhật ký được tra bằng mã,
        # còn câu thì `_chi_tiet_doc_duoc` dựng lại lúc render.
        provisioning.ghi_su_kien(db, may.id, "loi", boi="he_thong", ma_loi=ma)
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
            _tat_de_xoa(client, may, ctx, moc=20)
            upid = client.xoa(may.vmid)
            _cho_tac_vu(client, upid, ctx, moc=30)

        trang_thai_may.dat(may, vong_doi=trang_thai_may.DANG_TAO,
                           dien_mong_muon=trang_thai_may.CHAY,
                           dien_quan_sat=trang_thai_may.KHONG_RO,
                           tac_vu=trang_thai_may.DANG_CAP_PHAT)
        # Xoá VM là xoá luôn mọi ảnh chụp của nó. Không xoá mốc này thì trang máy
        # vẫn khoe "Ảnh chụp gần nhất: <ngày>" cho một bản **không còn tồn tại**,
        # và nút Khôi phục hiện ra rồi báo "chưa có ảnh chụp nào" khi bấm.
        may.sao_luu_luc = None
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
            _tat_de_xoa(client, may, ctx, moc=40)
            _bao(ctx, 50, "dang xoa dia")
            upid = client.xoa(may.vmid)
            _cho_tac_vu(client, upid, ctx, moc=70)

        _bao(ctx, 78, "dang go cho dia chi")
        _go_cho_dhcp(may)
        # Cùng lý do như ở `_dung_lai`: ảnh chụp đi theo VM.
        may.sao_luu_luc = None

        _bao(ctx, 80, "dang tra dia chi cong khai")
        _tra_ip_cong_khai(db, may)
        _nha_tai_nguyen(db, may)
        # Máy đã đi rồi: quan sát là `tat` thật, không phải `khong_ro` — VM không
        # còn tồn tại thì không có gì để không rõ.
        trang_thai_may.dat(may, vong_doi=trang_thai_may.DA_XOA,
                           dien_mong_muon=trang_thai_may.TAT,
                           dien_quan_sat=trang_thai_may.TAT,
                           tac_vu=trang_thai_may.KHONG_CO)
        provisioning.ghi_su_kien(db, may.id, "da_xoa",
                                 boi=str(params.get("boi") or "he_thong"))
        db.commit()
        _bao(ctx, 100, "xong")
        return {"instance_id": may.id, "vmid": may.vmid}
    finally:
        gen.close()


def _go_cho_dhcp(may: VpsInstance) -> None:
    """Gỡ đặt chỗ DHCP **và phép đo băng thông** của một máy sắp bị xoá.

    Router không trả lời thì **không chặn việc xoá máy** — máy đã đi rồi, giữ nó
    lại vì một tệp cấu hình không sửa được là chọn cái tệ hơn.

    Chỗ thừa cũng không kẹt máy sau: `dat_cho` xoá dòng cũ theo **cả MAC lẫn địa
    chỉ**, nên máy tiếp theo nhận đúng địa chỉ này vẫn đăng ký được.
    """
    try:
        rt = bo_dinh_tuyen.client_tu_moi_truong()
        rt.go_cho(dinh_danh.mac(may.id), may.ip_noi_bo or "")
        if may.ip_noi_bo:
            # Gỡ khỏi cả ba set. Địa chỉ này sẽ được cấp lại cho khách khác, và
            # một bộ đếm cũ dính sang người mới là một hoá đơn sai; một cờ hãm
            # tốc sót lại thì khách mới nhận máy chậm mà không ai hiểu vì sao.
            rt.thoi_theo_doi(may.ip_noi_bo)
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
