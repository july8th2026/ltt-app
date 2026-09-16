"""Việc nền định kỳ của app VPS: thu tiền, treo máy hết tiền, xoá máy quá hạn.

## Vì sao file này tồn tại

`services/billing.py` đã có đủ hàm — `thu_phi_dinh_ky`, `den_han_xoa`, `treo` —
kèm test, từ 2026-08-23. Nhưng cho tới 24/08 **không nơi nào gọi chúng**. Máy hết
hạn không bị treo, không bị xoá, IP `$3/tháng` không được trả về. Một chính sách
có hàm mà không ai chạy đọc lên như một lời hứa (EXT-19), và đây là lời hứa về
tiền.

Nguyên nhân gốc không phải quên: **hợp đồng app không có chỗ khai việc định kỳ**.
Nên chỗ đó đã được thêm vào hợp đồng (`AppManifest.bao_tri`) thay vì đi vòng, và
file này là thứ nó trỏ tới.

## Sáu việc, theo đúng thứ tự đó

0. **Đo băng thông** — cộng dồn bộ đếm của router vào từng máy, hãm tốc máy vượt
   trần. Chạy **trước** vòng thu: thu một chu kỳ mới đặt lại bộ đếm chu kỳ về 0,
   và đặt lại trước khi kịp cộng phần cuối chu kỳ là bỏ mất phần đó.
1. **Thu** một chu kỳ 30 ngày cho máy tới kỳ.
2. **Treo** máy không đủ credit — *và tắt máy thật*, không chỉ đổi một cột. Treo
   mà máy vẫn chạy thì "treo" chỉ là một nhãn: khách dùng miễn phí đủ 7 ngày ân
   hạn, và RAM vẫn bị giữ suốt thời gian đó.
3. **Xoá** máy đã treo quá 7 ngày (V8) — đẩy vào hàng đợi, không xoá tại chỗ.
4. **Hoàn tiền** cho máy chưa từng chạy được — khách bị trừ trước khi job dựng
   máy, và job hỏng thì họ trả tiền để nhận một dòng chữ "Lỗi".
5. **Chụp ảnh tuần**, giữ đúng một bản — xem `services/sao_luu.py` để biết vì sao
   là ảnh chụp chứ không phải `vzdump`, và vì sao trang bán phải nói đúng điều đó.

## Vì sao xoá bằng JOB chứ không xoá thẳng ở đây

Xoá một máy là tắt cứng → chờ tác vụ Proxmox → xoá đĩa → đóng đường NAT → gỡ chỗ
DHCP → trả IP cho Vultr. Vài chục giây mỗi máy, và nó gọi ra ngoài mạng. Chạy
thẳng trong vòng bảo trì nghĩa là một Vultr chậm sẽ **giữ lease bảo trì của cả
nền tảng**, chặn luôn việc dọn job cũ, quét cảnh báo và gửi webhook.

`dedupe_key` chặn việc nộp trùng: một job xoá đang chờ hoặc đang chạy cho cùng
máy thì lần chạy sau nhận lại đúng job đó. Còn job đã **hỏng hẳn** thì lượt sau
nộp lại — nên một lần Proxmox chết không để máy nằm lại vĩnh viễn.

## Không ném ra ngoài

Nền tảng bắt và ghi log, nhưng một app ném mỗi lượt là một dòng log rác mỗi giờ,
và nó che những lỗi thật. Lỗi hạ tầng ở đây được bắt hẹp và ghi lại; lỗi lập
trình vẫn nổ lên trên như bình thường.
"""
from __future__ import annotations

import logging
import time

from apps.vps.services import billing, backend_factory
from apps.vps import profiles
from apps.vps.services.proxmox import ChuaCauHinh, ProxmoxError, client_tu_moi_truong

log = logging.getLogger(__name__)


def _client_hoac_none():
    """Client Proxmox, hoặc `None` nếu chưa khai / không nối được.

    `None` **không** dừng vòng thu tiền: quyết định về tiền không được phụ thuộc
    vào việc Proxmox có trả lời hay không. Máy vẫn bị treo trong sổ, chỉ là chưa
    tắt được — và lượt sau sẽ tắt.
    """
    try:
        return client_tu_moi_truong()
    except ChuaCauHinh as exc:
        log.warning("VPS bao tri: chua cau hinh Proxmox (%s)", exc)
        return None


def _treo_va_tat(db, client):
    """Hàm treo tiêm vào `thu_phi_dinh_ky`: ghi sổ **và** tắt máy."""
    from apps.vps.services import dieu_khien

    def treo(may, ly_do: str) -> None:
        selected = client
        if getattr(may, "infrastructure_profile_id", None):
            try:
                selected = backend_factory.compute_backend(profiles.pinned_profile(db, may)).client
            except (profiles.ProfileNotReady, ChuaCauHinh,
                    *backend_factory.operation_error_types()):  # type: ignore[misc]
                selected = None
        if selected is None:
            billing.treo(db, may, ly_do)
            return
        # `dieu_khien.treo` tự nuốt lỗi Proxmox và VẪN ghi sổ — treo là quyết
        # định về tiền, Proxmox hỏng không được phép cứu một máy khỏi bị treo.
        dieu_khien.treo(db, may, selected, ly_do=ly_do)

    return treo


def _nop_job_xoa(db, may) -> bool:
    """Đẩy một job xoá cho máy đã quá hạn ân hạn. Trả True nếu vừa nộp mới."""
    from platform_core import jobs as job_queue

    # Import trong hàm, không ở đầu file: `manifest.py` trỏ vào file này, nên
    # import ngược ở tầng module là vòng import ngay lúc nạp app.
    from apps.vps.manifest import MANIFEST

    truoc = job_queue.submit(
        db, user_id=str(may.user_id), app_slug=MANIFEST.slug,
        job_type="vps.destroy",
        params={"instance_id": may.id, "boi": "he_thong"},
        dedupe_key=f"vps-destroy-{may.id}")
    return truoc is not None


def _dong_bo_bang_thong(db, profile=None) -> int:
    """Đọc bộ đếm trên router, cộng dồn vào từng máy, và hãm tốc máy vượt trần.

    Trả về số máy vừa **đổi** trạng thái hãm tốc — chỉ số đó đáng ghi log.

    Chạy TRƯỚC vòng thu tiền: thu một chu kỳ mới đặt lại `bang_thong_byte` về 0,
    và đặt lại trước khi kịp cộng phần cuối chu kỳ là bỏ mất phần đó.

    ## Đối chiếu với router, không tin cột trong CSDL

    Ba `set` của nftables sống **trong bộ nhớ**. Router khởi động lại, hoặc ai đó
    chạy lại `cai-dat-router.sh` (nó `delete table` rồi dựng lại), là cả ba rỗng:
    máy đang sống mất phép đo, và máy đang bị hãm **hết bị hãm** trong khi CSDL
    vẫn ghi là có.

    Nên mỗi lượt: đọc **sự thật trên router**, ghi lại những gì thiếu. Cùng
    nguyên tắc với `gateway.danh_sach_duong` — thứ duy nhất phát hiện được lệch
    là đọc lại phía kia, không phải tin phía mình.
    """
    from sqlalchemy import select

    from apps.vps import bang_thong
    from apps.vps.services import router as bo_dinh_tuyen
    from apps.vps.tables import VpsInstance

    try:
        rt = (backend_factory.router_backend(profile) if profile is not None
              else bo_dinh_tuyen.client_tu_moi_truong())
        so_lieu = rt.doc_bang_thong()
        dang_ham = rt.danh_sach_giam_toc()
    except bo_dinh_tuyen.SshLenhError as exc:
        # Bắt HẸP. Router không trả lời thì bỏ lượt đo này; bộ đếm trên router
        # vẫn chạy tiếp, nên lượt sau cộng bù đủ — không mất gì.
        log.warning("VPS bao tri: khong doc duoc bang thong: %s", exc)
        return 0

    doi = 0
    query = select(VpsInstance).where(
            VpsInstance.trang_thai.in_(("dang_chay", "da_tat", "bi_treo")),
            VpsInstance.ip_noi_bo.is_not(None))
    if profile is not None:
        query = query.where(VpsInstance.infrastructure_profile_id == profile.id,
                            VpsInstance.profile_resolution_state == "PINNED")
    for may in db.execute(query).scalars():
        if profile is not None:
            try:
                profiles.pinned_profile(db, may)
            except profiles.ProfileNotReady:
                continue
        ip = str(may.ip_noi_bo)

        if ip not in so_lieu:
            # Máy sống mà router không đếm: set vừa bị dựng lại. Ghi lại rồi
            # sang máy kế — lượt sau đã có số. Bỏ qua bước này thì máy đó **dùng
            # bao nhiêu cũng không ai biết**, vĩnh viễn và im lặng.
            try:
                rt.theo_doi_bang_thong(ip)
            except bo_dinh_tuyen.SshLenhError as exc:
                log.warning("VPS bao tri: khong bat duoc do cho %s: %s", may.id, exc)
            continue

        len_byte, xuong_byte = so_lieu[ip]
        tong, moc_len = bang_thong.cong_don(
            may.bang_thong_byte or 0, may.bang_thong_moc_len or 0, len_byte)
        tong, moc_xuong = bang_thong.cong_don(
            tong, may.bang_thong_moc_xuong or 0, xuong_byte)
        may.bang_thong_byte = tong
        may.bang_thong_moc_len = moc_len
        may.bang_thong_moc_xuong = moc_xuong

        can_ham = bang_thong.vuot_han_muc(may)
        # So với TRẠNG THÁI THẬT trên router, không với cột trong CSDL: sau một
        # lần dựng lại ruleset, cột nói "đang hãm" mà router thì không.
        if (ip in dang_ham) != can_ham:
            try:
                rt.dat_giam_toc(ip, can_ham)
            except bo_dinh_tuyen.SshLenhError as exc:
                log.warning("VPS bao tri: khong dat duoc giam toc cho %s: %s",
                            may.id, exc)
                continue
            doi += 1
        if bool(may.bi_giam_toc) != can_ham:
            may.bi_giam_toc = can_ham
            billing.ghi_su_kien(
                db, may.id, "giam_toc_bat" if can_ham else "giam_toc_tat",
                boi="he_thong", da_dung=bang_thong.doc_duoc(tong))
    db.commit()
    return doi


def _dong_bo_bang_thong_pinned(db):
    from sqlalchemy import select
    from apps.vps.tables import VpsInfrastructureProfile
    changed = 0
    for profile in db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.status != "DISABLED")).scalars():
        try:
            changed += _dong_bo_bang_thong(db, profile)
        except backend_factory.operation_error_types():
            log.warning("VPS bandwidth unavailable for profile %s", profile.id)
    return changed


def _doi_chieu_profiles(db):
    """Read each profile independently; no fallback to legacy provider drivers."""
    global _moc_doi_chieu
    if time.monotonic() < _moc_doi_chieu:
        return 0
    _moc_doi_chieu = time.monotonic() + DOI_CHIEU_MOI_GIAY
    from sqlalchemy import select
    from apps.vps.services.reconciliation import reconcile_profile
    from apps.vps.tables import VpsInfrastructureProfile
    findings = 0
    for profile in db.execute(select(VpsInfrastructureProfile)).scalars():
        try:
            result = reconcile_profile(db, profile,
                compute=backend_factory.compute_backend(profile),
                public_ip=backend_factory.public_ip_backend(db, profile),
                gateway=backend_factory.gateway_backend(profile))
        except (ChuaCauHinh, ProxmoxError, *backend_factory.operation_error_types()):
            log.warning("VPS reconciliation unavailable for profile %s", profile.id)
            continue
        findings += len(result.findings)
        for finding in result.findings:
            log.warning("VPS profile %s finding %s resource %s",
                        profile.id, finding.code, finding.resource_id)
    return findings


def _chup_anh_den_han(db, client, *, now=None) -> int:
    """Chụp ảnh tuần cho máy tới kỳ. Trả số máy vừa chụp.

    Client `None` (chưa cấu hình Proxmox) thì bỏ lượt — không đánh dấu đã chụp,
    nên lượt sau chụp bù. Đánh dấu mà chưa chụp là ghi vào sổ một bản không tồn
    tại, và khách chỉ phát hiện lúc cần khôi phục.
    """
    from sqlalchemy import select

    from apps.vps.services import sao_luu
    from apps.vps.tables import VpsInstance

    if db is None or client is None:
        return 0

    da_chup = 0
    for may in db.execute(
        select(VpsInstance).where(
            VpsInstance.trang_thai.in_(("dang_chay", "da_tat", "bi_treo")))
    ).scalars():
        if not sao_luu.den_han_chup(may, now=now):
            continue
        try:
            selected = client
            if getattr(may, "infrastructure_profile_id", None):
                selected = backend_factory.compute_backend(profiles.pinned_profile(db, may)).client
            if selected is None:
                continue
            ten = sao_luu.chup_va_don(selected, may, now=now)
        except (ProxmoxError, ChuaCauHinh, profiles.ProfileNotReady, sao_luu.SaoLuuError) as exc:
            # ⚠️ `SaoLuuError` là loại lỗi MỚI của VPS V2, và bắt nó là cả điểm
            #    của bản sửa: trước đây `chup_va_don` không chờ tác vụ nên nó
            #    **không bao giờ** ném vì tác vụ hỏng — dòng dưới vẫn chạy, và
            #    máy khoe một ảnh chụp không tồn tại suốt bảy ngày.
            log.warning("VPS bao tri: khong chup duoc anh cho may %s: %s",
                        may.id, exc)
            continue
        # Tới đây thì ảnh đã được **xác minh có mặt đúng tên** trên máy chủ.
        may.sao_luu_luc = now or _bay_gio()
        billing.ghi_su_kien(db, may.id, "sao_luu", boi="he_thong", anh=ten)
        da_chup += 1
    if da_chup:
        db.commit()
    return da_chup


def _bay_gio():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _hoan_may_tao_hong(db) -> int:
    """Hoàn tiền cho máy **chưa từng chạy được**. Trả số máy đã hoàn.

    ## Lỗ hổng này có thật, và nó im lặng

    Trang bán trừ credit **trước** khi nộp job (`routes.tao_may`), và đó là lựa
    chọn đúng: không trừ trước thì một người hết tiền vẫn chiếm được chỗ. Nhưng
    khi job dựng máy hỏng — Vultr cạn hạn ngạch IP, Proxmox không trả lời, kho
    đầy — thì máy vào trạng thái `loi` và **không ai hoàn lại chu kỳ đã thu**.

    Khách trả 149.000–329.000đ và nhận một dòng chữ "Lỗi". Không log nào báo,
    không ai quét. Đúng lớp lỗi mà phiên Public API vừa tìm ra ở cửa `/messages`,
    chỉ khác đường đi.

    ## Chỉ hoàn khi máy CHƯA TỪNG chạy

    Máy chạy được một thời gian rồi hỏng là chuyện khác: dịch vụ chạy best effort,
    không có SLA, và điều khoản nói rõ chu kỳ đã bắt đầu thì không hoàn. Nên mốc
    phân biệt là sự kiện `tao_xong` — **có** nghĩa là máy đã từng lên; **không**
    nghĩa là khách chưa nhận được gì.

    ## Chạy lại được

    Đánh dấu bằng chính sự kiện `hoan_tien`. Không có mốc đó thì mỗi giờ hoàn một
    lần, và một máy hỏng biến thành một máy in tiền.
    """
    from sqlalchemy import select

    from platform_core import credit

    from apps.vps.tables import VpsEvent, VpsInstance

    da_hoan = 0
    for may in db.execute(select(VpsInstance).where(
            VpsInstance.trang_thai == "loi")).scalars():
        loai = {e.loai: e for e in db.execute(
            select(VpsEvent).where(VpsEvent.instance_id == may.id)).scalars()}
        if "tao_xong" in loai:
            continue                      # đã từng chạy — không hoàn
        if "hoan_tien" in loai:
            continue                      # đã hoàn rồi
        thu = loai.get("thu_phi")
        so = int((thu.chi_tiet or {}).get("credit") or 0) if thu else 0
        if so <= 0:
            continue                      # chưa thu gì thì không có gì để hoàn

        credit.hoan_phi(db, may.user_id, so, kind=billing.KIND,
                        note=f"Hoan chu ky VPS: may {may.id[:8]} tao khong xong")
        billing.ghi_su_kien(db, may.id, "hoan_tien", boi="he_thong",
                            credit=so, ly_do=may.ly_do or "")
        # Máy hỏng vẫn có thể đang giữ một VM dở dang trên Proxmox, một địa chỉ
        # trong mạng riêng, và một IP đang tính tiền. Đẩy job xoá để nhả hết.
        try:
            _nop_job_xoa(db, may)
        except Exception as exc:          # noqa: BLE001 - hoan tien da xong roi
            log.warning("VPS: hoan tien may %s xong nhung khong nop duoc job xoa: %s",
                        may.id, exc)
        da_hoan += 1
    if da_hoan:
        db.commit()
    return da_hoan


#: Doi chieu bon nguon su that moi bao lau. Hang ngay, khong hang gio: no goi
#: ra Proxmox + router + gateway + Vultr, va thu no tim (mo coi) khong xuat
#: hien theo nhip gio.
DOI_CHIEU_MOI_GIAY = 24 * 3600

#: Moc lan doi chieu gan nhat, theo dong ho don dieu cua tien trinh.
#: Worker khoi dong lai thi chay lai mot luot — vo hai, vi phep quet chi DOC.
_moc_doi_chieu = 0.0


def _doi_chieu_dinh_ky(db, client) -> int:
    """Quet mo coi moi ngay, ghi CANH BAO neu co. Tra so muc mo coi.

    ## Vi sao viec nay phai TU CHAY

    `tools/vps_doctor.py` da doi chieu duoc tu 25/08, nhung **khong ai chay
    no dinh ky**. Mot phep soi khong ai chay la mot phep soi khong ton tai —
    va thu no tim ra (nhat la Reserved IP mo coi, $3/thang) chinh la loai
    hong khong bao gio tu keu len.

    Ghi bang `log.warning` chu khong nem: mot muc mo coi khong phai ly do de
    dung vong bao tri, no la ly do de co nguoi doc.
    """
    global _moc_doi_chieu
    if client is None:
        return 0
    if time.monotonic() < _moc_doi_chieu:
        return 0
    # Dat moc TRUOC khi chay: quet nem thi luot sau van cho du mot ngay,
    # khong quay lai ngay va nem lai moi gio.
    _moc_doi_chieu = time.monotonic() + DOI_CHIEU_MOI_GIAY

    from apps.vps import doi_chieu

    kq = doi_chieu.quet(db, client)
    # `quet` nay GHI vao may: no dong dau `dien_quan_sat`/`quan_sat_luc` cua
    # tung may. Khong commit thi ca luot do bi vut di, va `qua_cu()` van bao
    # moi may deu cu — dung thu ma phep do sinh ra de sua.
    if kq.da_do_dien:
        db.commit()

    for x in kq.khong_doc_duoc:
        log.warning('VPS doi chieu: %s', x)
    # Ghi log theo MUC, khong gop mot dong. Mot `VO_BAT_BIEN` lan giua muoi dong
    # `NGHI_MO_COI` la mot dong khong ai doc — va no la dong duy nhat dang doc.
    for lech in kq.lech:
        if lech.muc_do in doi_chieu.CAM_TU_XU:
            log.warning('VPS CAN NGUOI XU - %s', lech)
        else:
            log.info('VPS doi chieu - %s', lech)
    if not kq.lech:
        log.info('VPS doi chieu: sach (%s may, %s IP, %s phep do dien)',
                 kq.so_may, kq.so_ip, kq.da_do_dien)
    return kq.tong_mo_coi


def _don_thao_tac_qua_han(db, *, now=None) -> int:
    """Dong nhung thao tac qua han ma worker khong kip dong lai.

    ## Day la duong phuc hoi DUY NHAT sau khi mot worker chet

    Worker bi kill giua chung thi khong ai goi `xong()` hay `hong()`. Thao tac
    nam lai `dang_chay` **vinh vien**, va `tac_vu` tren may khong bao gio duoc
    go — khach khong bam duoc gi va khong ai biet vi sao. Loai hong im lang te
    nhat, vi no trong giong mot giao dien dang tai.

    ⚠️ No **khong** ket luan viec da that bai: ma loi la `tac_vu_qua_han`, va
       viec do co the van dang chay tren Proxmox. Vong doi chieu ngay ben duoi
       se di hoi lai the gioi that.

    Chay TRUOC `_doi_chieu_dinh_ky` co chu y: thao tac con mo thi `dang_ban(may)`
    con True, va vong doi chieu **bo qua** may dang ban khi bao lech dien. Chay
    sau thi mot may bi ket 35 phut se khong duoc bao lech trong 35 phut do.
    """
    from apps.vps.services import thao_tac

    da_dong = thao_tac.don_qua_han(db, now=now)
    # Dọn hàng CŨ trong cùng lượt: chính sách lưu trữ khai `vps_thao_tac` giữ
    # 180 ngày (`governance.STORES`), và một hạn lưu trữ không ai thi hành là
    # một lời hứa — đúng lớp lỗi mà `test_211` sinh ra để bắt.
    da_xoa = thao_tac.don_cu(db, now=now)
    if da_dong or da_xoa:
        db.commit()
    if da_xoa:
        log.info("VPS bao tri: xoa %s thao tac cu hon %s ngay",
                 da_xoa, thao_tac.GIU_NGAY)
    return len(da_dong)


def _chinh_sach_ip_rong(db, *, now=None) -> int:
    """R16: giữ tối đa một IP OVH rỗi; phần dư đặt không gia hạn. Trả số IP đã huỷ.

    Mọi lỗi dừng ở đây: một lần OVH không trả lời không được chặn thu tiền.
    """
    try:
        from sqlalchemy import select

        from apps.vps.services import backend_factory, ip_rong
        from apps.vps.tables import VpsInfrastructureProfile

        da_huy = 0
        for profile in list(db.execute(select(VpsInfrastructureProfile).where(
                VpsInfrastructureProfile.status == "ACTIVE",
                VpsInfrastructureProfile.public_ip_backend_type == "ovh_static_pool",
        )).scalars()):
            client = backend_factory.ovh_inventory_client(profile)
            da_huy += ip_rong.ap_dung(db, profile, client, now=now)["da_huy_gia_han"]
            db.commit()
        return da_huy
    except Exception as exc:  # noqa: BLE001 - biên của việc nền
        try:
            db.rollback()
        except Exception as loi_rb:  # noqa: BLE001
            log.warning("VPS bao tri: rollback that bai: %s", type(loi_rb).__name__)
        log.warning("VPS bao tri: chinh sach IP rong that bai: %s", type(exc).__name__)
        return 0


def mot_luot(db, *, now=None) -> dict:
    """Một lượt bảo trì. Tách khỏi `chay()` để test được mà không cần worker."""
    da_doi_giam_toc = _dong_bo_bang_thong_pinned(db)

    # Never route pinned resources through the global/default compute endpoint.
    # Legacy NEEDS_REVIEW rows get accounting but no external mutation here.
    client = None
    ket_qua = billing.thu_phi_dinh_ky(db, now=now,
                                      khi_treo=_treo_va_tat(db, client))
    if ket_qua["da_thu"]:
        # Vừa có máy sang chu kỳ mới → bộ đếm chu kỳ về 0. Đồng bộ thêm một lượt
        # để bỏ hãm ngay, thay vì bắt khách vừa trả tiền chờ tới giờ sau mới hết
        # chậm — "tôi vừa gia hạn mà máy vẫn ì" là một lá thư hỗ trợ có thật.
        da_doi_giam_toc += _dong_bo_bang_thong_pinned(db)
    ket_qua["da_doi_giam_toc"] = da_doi_giam_toc
    # Chụp ảnh SAU khi thu tiền: máy vừa bị treo vì hết tiền vẫn được chụp (nó
    # còn 7 ngày ân hạn, và ngừng chụp trong 7 ngày đó là một hình phạt kèm mà
    # không ai công bố), nhưng máy vừa bị nộp job xoá thì không cần bản nào nữa.
    ket_qua["da_chup"] = _chup_anh_den_han(db, client, now=now)

    # Dọn vé console hết hạn. Nhỏ, nhưng `governance.py` khai rằng bảng này được
    # dọn — và một chính sách nêu tên một hàm không ai chạy chỉ là một lời hứa.
    from apps.vps.services import console

    da_don = console.don_ve_het_han(db)
    if da_don:
        db.commit()
    ket_qua["da_don_ve"] = da_don
    ket_qua["da_hoan"] = _hoan_may_tao_hong(db)
    ket_qua["thao_tac_qua_han"] = _don_thao_tac_qua_han(db, now=now)
    ket_qua["mo_coi"] = _doi_chieu_profiles(db)
    ket_qua["ip_rong_huy_gia_han"] = _chinh_sach_ip_rong(db, now=now)

    da_nop_xoa = 0
    for may in billing.den_han_xoa(db, now=now):
        try:
            _nop_job_xoa(db, may)
            da_nop_xoa += 1
        except ProxmoxError as exc:              # bắt HẸP: lỗi lập trình phải nổ
            log.warning("VPS bao tri: khong nop duoc job xoa may %s: %s",
                        may.id, exc)
    if da_nop_xoa:
        db.commit()

    ket_qua["da_nop_xoa"] = da_nop_xoa
    return ket_qua


#: Nhịp của phần nặng (thu tiền, chụp ảnh, đối chiếu). Manifest gọi `chay()`
#: dày hơn (`profiles.HEALTH_REFRESH_SECONDS`) chỉ để làm mới health profile;
#: phần nặng vẫn giữ nhịp một giờ như trước.
NHIP_NANG_GIAY = 3600
_luot_nang_cuoi: float | None = None


def chay(*, dong_ho=None) -> None:
    """Điểm vào cho `AppManifest.bao_tri`. Nền tảng gọi dưới lease.

    Mỗi lượt: làm mới health mọi profile ACTIVE (nếu không, việc chọn profile
    khi tạo máy luôn thấy health cũ và từ chối bán — đo 16/09). Phần nặng chỉ
    chạy khi đã đủ `NHIP_NANG_GIAY` kể từ lượt nặng trước trong tiến trình này;
    lease đổi chủ thì lượt nặng có thể tới sớm — cùng ngữ nghĩa với `moc` của
    nền tảng, và mọi bước nặng đều idempotent theo hạn.
    """
    import time

    from platform_core.db import get_session
    from apps.vps.services import preflight

    global _luot_nang_cuoi
    bay_gio = (dong_ho or time.monotonic)()
    gen = get_session()
    db = next(gen)
    try:
        try:
            health = preflight.refresh_active_profiles(db)
            if not all(health.values()):
                log.warning("VPS bao tri: profile chua san sang ban %s", health)
        except Exception:                       # health không được chặn thu tiền
            db.rollback()
            log.exception("VPS bao tri: lam moi health profile that bai")
        if _luot_nang_cuoi is not None and bay_gio - _luot_nang_cuoi < NHIP_NANG_GIAY:
            return
        _luot_nang_cuoi = bay_gio
        kq = mot_luot(db)
        # Chỉ ghi log khi CÓ việc xảy ra: một dòng "đã thu 0" mỗi giờ là 24 dòng
        # rác mỗi ngày, và nó làm người đọc bỏ qua đúng dòng cần đọc.
        if any(kq.values()):
            log.info("VPS bao tri: thu %s, treo %s, nop xoa %s, doi giam toc %s, "
                     "chup anh %s, don ve %s, hoan %s, thao tac qua han %s, "
                     "mo coi %s, ip rong huy gia han %s",
                     kq["da_thu"], kq["da_treo"], kq["da_nop_xoa"],
                     kq["da_doi_giam_toc"], kq["da_chup"], kq["da_don_ve"],
                     kq["da_hoan"], kq["thao_tac_qua_han"], kq["mo_coi"],
                     kq.get("ip_rong_huy_gia_han", 0))
    finally:
        gen.close()
