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

## Bốn việc, theo đúng thứ tự đó

0. **Đo băng thông** — cộng dồn bộ đếm của router vào từng máy, hãm tốc máy vượt
   trần. Chạy **trước** vòng thu: thu một chu kỳ mới đặt lại bộ đếm chu kỳ về 0,
   và đặt lại trước khi kịp cộng phần cuối chu kỳ là bỏ mất phần đó.
1. **Thu** một chu kỳ 30 ngày cho máy tới kỳ.
2. **Treo** máy không đủ credit — *và tắt máy thật*, không chỉ đổi một cột. Treo
   mà máy vẫn chạy thì "treo" chỉ là một nhãn: khách dùng miễn phí đủ 7 ngày ân
   hạn, và RAM vẫn bị giữ suốt thời gian đó.
3. **Xoá** máy đã treo quá 7 ngày (V8) — đẩy vào hàng đợi, không xoá tại chỗ.

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

from apps.vps.services import billing
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
        if client is None:
            billing.treo(db, may, ly_do)
            return
        # `dieu_khien.treo` tự nuốt lỗi Proxmox và VẪN ghi sổ — treo là quyết
        # định về tiền, Proxmox hỏng không được phép cứu một máy khỏi bị treo.
        dieu_khien.treo(db, may, client, ly_do=ly_do)

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


def _dong_bo_bang_thong(db) -> int:
    """Đọc bộ đếm trên router, cộng dồn vào từng máy, và hãm tốc máy vượt trần.

    Trả về số máy vừa **đổi** trạng thái hãm tốc — chỉ số đó đáng ghi log.

    Chạy TRƯỚC vòng thu tiền: thu một chu kỳ mới sẽ đặt lại `bang_thong_byte` về
    0, và đặt lại trước khi kịp cộng phần cuối chu kỳ là bỏ mất phần đó.
    """
    from sqlalchemy import select

    from apps.vps import bang_thong
    from apps.vps.services import router as bo_dinh_tuyen
    from apps.vps.tables import VpsInstance

    try:
        rt = bo_dinh_tuyen.client_tu_moi_truong()
        so_lieu = rt.doc_bang_thong()
    except bo_dinh_tuyen.SshLenhError as exc:
        # Bắt HẸP. Router không trả lời thì bỏ lượt đo này; bộ đếm trên router
        # vẫn chạy tiếp, nên lượt sau cộng bù đủ — không mất gì.
        log.warning("VPS bao tri: khong doc duoc bang thong: %s", exc)
        return 0

    doi = 0
    for may in db.execute(
        select(VpsInstance).where(
            VpsInstance.trang_thai.in_(("dang_chay", "da_tat", "bi_treo")),
            VpsInstance.ip_noi_bo.is_not(None))
    ).scalars():
        len_byte, xuong_byte = so_lieu.get(str(may.ip_noi_bo), (0, 0))
        tong, moc_len = bang_thong.cong_don(
            may.bang_thong_byte or 0, may.bang_thong_moc_len or 0, len_byte)
        tong, moc_xuong = bang_thong.cong_don(
            tong, may.bang_thong_moc_xuong or 0, xuong_byte)
        may.bang_thong_byte = tong
        may.bang_thong_moc_len = moc_len
        may.bang_thong_moc_xuong = moc_xuong

        can_ham = bang_thong.vuot_han_muc(may)
        if bool(may.bi_giam_toc) != can_ham:
            try:
                rt.dat_giam_toc(str(may.ip_noi_bo), can_ham)
            except bo_dinh_tuyen.SshLenhError as exc:
                log.warning("VPS bao tri: khong dat duoc giam toc cho %s: %s",
                            may.id, exc)
                continue
            may.bi_giam_toc = can_ham
            billing.ghi_su_kien(
                db, may.id, "giam_toc_bat" if can_ham else "giam_toc_tat",
                boi="he_thong", da_dung=bang_thong.doc_duoc(tong))
            doi += 1
    db.commit()
    return doi


def mot_luot(db, *, now=None) -> dict:
    """Một lượt bảo trì. Tách khỏi `chay()` để test được mà không cần worker."""
    da_doi_giam_toc = _dong_bo_bang_thong(db)

    client = _client_hoac_none()
    ket_qua = billing.thu_phi_dinh_ky(db, now=now,
                                      khi_treo=_treo_va_tat(db, client))
    if ket_qua["da_thu"]:
        # Vừa có máy sang chu kỳ mới → bộ đếm chu kỳ về 0. Đồng bộ thêm một lượt
        # để bỏ hãm ngay, thay vì bắt khách vừa trả tiền chờ tới giờ sau mới hết
        # chậm — "tôi vừa gia hạn mà máy vẫn ì" là một lá thư hỗ trợ có thật.
        da_doi_giam_toc += _dong_bo_bang_thong(db)
    ket_qua["da_doi_giam_toc"] = da_doi_giam_toc

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


def chay() -> None:
    """Điểm vào cho `AppManifest.bao_tri`. Nền tảng gọi mỗi giờ, dưới lease."""
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        kq = mot_luot(db)
        # Chỉ ghi log khi CÓ việc xảy ra: một dòng "đã thu 0" mỗi giờ là 24 dòng
        # rác mỗi ngày, và nó làm người đọc bỏ qua đúng dòng cần đọc.
        if any(kq.values()):
            log.info("VPS bao tri: thu %s, treo %s, nop xoa %s, doi giam toc %s",
                     kq["da_thu"], kq["da_treo"], kq["da_nop_xoa"],
                     kq["da_doi_giam_toc"])
    finally:
        gen.close()
