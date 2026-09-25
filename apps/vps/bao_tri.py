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
import os
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


def _dong_bo_bang_thong(db, profile=None, *, now=None) -> int:
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

    ## Hai lớp bảo vệ, MỘT quyết định mỗi máy

    Từ V2 (Mục 4, 23/09/2026) có thêm lớp 2 — theo TỔNG cả cổng vào, không chỉ
    theo từng khách (`_can_ham_theo_tong`). Hai lớp phải hội tụ thành **một**
    `can_ham` mỗi máy trước khi chạm router: tính riêng rồi gọi `dat_giam_toc`
    hai lần trong cùng lượt sẽ có lúc BẬT rồi TẮT ngay chính máy đó (lớp riêng
    nói không cần hãm, lớp tổng nói cần) — tốn SSH thật và ghi hai sự kiện
    trái nhau trong cùng một lượt bảo trì. Nên hàm này CỘNG DỒN xong hết cho
    mọi máy TRƯỚC (bước 1, không đụng router), rồi mới hỏi lớp tổng cần hãm ai
    (bước 2, dùng đúng số vừa cộng dồn), rồi mới quyết định và gọi router
    (bước 3) — đúng MỘT lần mỗi máy.
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

    query = select(VpsInstance).where(
            VpsInstance.trang_thai.in_(("dang_chay", "da_tat", "bi_treo")),
            VpsInstance.ip_noi_bo.is_not(None))
    if profile is not None:
        query = query.where(VpsInstance.infrastructure_profile_id == profile.id,
                            VpsInstance.profile_resolution_state == "PINNED")

    # ── Bước 1: cộng dồn riêng từng máy — THUẦN DB, chưa đụng router ─────────
    dang_song: list = []
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
        dang_song.append(may)

    # ── Bước 2: lớp bảo vệ THEO TỔNG — chỉ có ý nghĩa khi có PROFILE, vì cần
    #    biết đọc bộ đếm cổng vào nào. Duyệt đúng `dang_song` (bảng VpsInstance)
    #    nên KHÔNG BAO GIỜ đụng tới VM100-107 — chúng không có mặt trong bảng.
    can_ham_theo_tong = (_can_ham_theo_tong(profile, dang_song, now=now, db=db)
                         if profile is not None else set())

    # ── Bước 3: MỘT quyết định mỗi máy, rồi mới gọi router ───────────────────
    doi = 0
    for may in dang_song:
        ip = str(may.ip_noi_bo)
        can_ham = bang_thong.vuot_han_muc(may) or may.id in can_ham_theo_tong
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
                boi="he_thong", da_dung=bang_thong.doc_duoc(may.bang_thong_byte))
    db.commit()
    return doi


# ── Lớp bảo vệ THEO TỔNG (V2, Mục 4 của đặc tả 2026-09-23) ──────────────────
#
# Lớp riêng ở trên (`bang_thong.vuot_han_muc`) hãm một khách khi CHÍNH khách đó
# vượt hạn mức GÓI của họ. Nhưng cổng vào chỉ có 1 TB/tháng CHUNG cho mọi thứ
# đi qua nó — kể cả VM100-107, việc thật của chủ dự án, không phải khách. OVH
# không hãm riêng từng địa chỉ khi cổng chạm trần: họ hãm CẢ CỔNG xuống 10
# Mbps. Nên phải có một lớp nhìn TỔNG, không chỉ nhìn từng khách, và hãm bớt
# TRƯỚC khi cái tổng đó tới tay OVH.
#
# ## Mốc cộng dồn: dùng `network_config` sẵn có, không thêm cột
#
# `VpsInfrastructureProfile.network_config` (JSON, đã có từ V12) là chỗ chứa
# CẤU HÌNH không bí mật riêng cho từng profile — đúng khuôn "bảng/khoá cấu hình
# sẵn có" mà không cần migration Alembic (migration đụng deploy, không phải
# quyết định của một làn riêng lẻ). Khoá `cong_vao_bang_thong` bên trong nó
# giữ ba thứ: tháng đang tính, tổng byte đã cộng dồn tháng này, và MỐC bộ đếm
# thô của card mạng — dùng lại NGUYÊN `bang_thong.cong_don` để xử lý việc bộ
# đếm không bao giờ tự về 0 (nó là bộ đếm từ lúc khởi động máy, không phải bộ
# đếm theo tháng), cùng khuôn với cách mỗi máy khách tự cộng dồn của nó.
_KHOA_CAU_HINH_CONG_VAO = "cong_vao_bang_thong"

#: Tên thành phần sức khoẻ mà **vòng bảo trì** ghi cho lớp canh theo tổng.
#: Phải nằm ngoài `profiles.REQUIRED_HEALTH_COMPONENTS` (xem
#: `profiles.CANH_BAO_BAO_TRI`); `test_2600` chốt điều đó.
THANH_PHAN_BANG_THONG_TONG = "bang_thong_tong"

#: Thanh phan suc khoe cho phep kiem "cong quan tri co lo ra dia chi cua khach".
#: ⚠️ Phai NAM NGOAI `REQUIRED_HEALTH_COMPONENTS` — xem `CANH_BAO_BAO_TRI`.
THANH_PHAN_CONG_QUAN_TRI = "cong_quan_tri"

#: Cong SSH cua cong vao. Mot hang so, khong go lai so o cho khac.
CONG_QUAN_TRI = 22

#: Thanh phan suc khoe cho phep kiem "may co dung chuan danh tinh khong".
#: ⚠️ NGOAI `REQUIRED_HEALTH_COMPONENTS`, va ⛔ NGOAI `CHAN_BAN`: mot may lech
#: chuan la viec cua nguoi van hanh, khong phai ly do dong cua hang.
THANH_PHAN_CHUAN_HOA = "chuan_hoa_may"

#: Nhip kiem chuan hoa: mot ngay. MOC RIENG — ba phep soi truoc tung dung chung
#: mot moc va phep chay truoc khoa hai phep kia 24 gio trong im lang (24/09).
KIEM_CHUAN_HOA_MOI_GIAY = 24 * 3600
_moc_chuan_hoa = 0.0

#: Nhip kiem cong: mot ngay. No mo ket noi TCP toi tung dia chi nen khong dang
#: chay moi gio, va thu no bat (mot luat tuong lua bi go) khong doi theo gio.
KIEM_CONG_MOI_GIAY = 24 * 3600
_moc_kiem_cong = 0.0

#: Khoá đếm số lượt LIÊN TIẾP không đọc được bộ đếm cổng vào.
#:
#: Một lần hỏng thoáng qua (mạng chớp, cổng vào vừa khởi động lại) khác hẳn một
#: tuần SSH chết. Gộp hai thứ đó vào một trạng thái nhị phân là mất đúng thông
#: tin người trực cần để quyết định có phải dậy giữa đêm hay không.
_KHOA_MAT_TIN_HIEU = "mat_tin_hieu_lien_tiep"

#: Từ ngần này lượt liên tiếp trở lên thì tín hiệu lên CRITICAL thay vì DEGRADED.
#: Vòng bảo trì chạy mỗi giờ, nên 3 lượt ≈ 3 giờ không biết cổng vào ra sao.
MAT_TIN_HIEU_NGHIEM_TRONG = 3

#: Tháng-tới-giờ chạm mốc này (% trần) thì bắt đầu xét hãm theo tổng.
NGUONG_BAO_VE_TONG = 0.8


def _doc_cau_hinh_cong_vao(env: dict | None = None):
    """`DichDen` SSH CHỈ-ĐỌC tới cổng vào OVH — chỉ để đọc bộ đếm mạng.

    Không cần tiền tố `sudo`: đọc `/sys/class/net/*/statistics/*` và chạy
    `ip route get` không đòi quyền root.
    """
    from apps.vps.services.ssh_lenh import DichDen

    src = os.environ if env is None else env
    return DichDen(
        host=str(src.get("LTT_OVH_GATEWAY_HOST", "")).strip(),
        user=str(src.get("LTT_OVH_GATEWAY_USER", "")).strip() or "ubuntu",
        khoa=str(src.get("LTT_OVH_GATEWAY_SSH_KEY", "")).strip(),
        known_hosts=str(src.get("LTT_OVH_GATEWAY_KNOWN_HOSTS", "")).strip(),
        nhan="cong vao OVH",
    ).verify("LTT_OVH_GATEWAY_HOST")


def _doc_bo_dem_cong_vao(dich, *, chay=None) -> tuple[int, int]:
    """`(rx_byte, tx_byte)` tích luỹ từ lúc khởi động của card mạng công khai.

    Dò `IFACE` bằng `ip route get 1.1.1.1` thay vì viết cứng `ens3`: tên card
    đổi được khi đổi nhà cung cấp, hoặc họ đổi tên card mặc định — đã có tiền
    lệ ở chính cổng vào này (Vultr → OVH đổi luôn cả TRẦN, xem `bang_thong.py`).
    """
    from apps.vps.services.ssh_lenh import SshLenhError, bash_tu_xa

    kich_ban = (
        "IFACE=$(ip route get 1.1.1.1 2>/dev/null | "
        "sed -n 's/.* dev \\([^ ]*\\).*/\\1/p' | head -n1); "
        "cat /sys/class/net/$IFACE/statistics/rx_bytes; "
        "cat /sys/class/net/$IFACE/statistics/tx_bytes"
    )
    ra = bash_tu_xa(dich, kich_ban, chay=chay)
    dong = [d.strip() for d in ra.splitlines() if d.strip()]
    if len(dong) < 2:
        raise SshLenhError(
            f"cong vao tra ve thieu so lieu bo dem (can 2 dong, duoc {dong!r})")
    try:
        return int(dong[0]), int(dong[1])
    except ValueError as exc:
        raise SshLenhError(f"cong vao tra ve khong phai so: {dong!r}") from exc


def _doc_dem_hai_chieu_moi_truong(env: dict | None = None) -> bool:
    src = os.environ if env is None else env
    return str(src.get("LTT_VPS_DEM_HAI_CHIEU", "true")).strip().lower() != "false"


def _thang_hien_tai(now) -> str:
    return f"{now.year:04d}-{now.month:02d}"


def _so_ngay_trong_thang(now) -> int:
    import calendar
    return calendar.monthrange(now.year, now.month)[1]


def _cong_don_cong_vao(profile, rx_byte: int, tx_byte: int, *, now,
                       dem_hai_chieu: bool) -> dict:
    """Cập nhật tổng băng thông THÁNG-TỚI-GIỜ của cả cổng vào, lưu vào
    `profile.network_config[_KHOA_CAU_HINH_CONG_VAO]`. Trả về trạng thái mới.

    Tái dùng ĐÚNG `bang_thong.cong_don` — không viết lại phép cộng dồn, cùng
    khuôn với cách `_dong_bo_bang_thong` cộng dồn cho từng máy ở trên.

    ## Sang tháng mới: đặt MỐC = số thô hiện tại, không phải 0

    Bộ đếm của card mạng tích luỹ từ lúc **khởi động máy**, không tự về 0 đầu
    tháng. Đặt mốc về 0 khi sang tháng sẽ cộng nhầm toàn bộ lịch sử từ lúc
    khởi động cổng vào tới giờ vào tháng mới — có thể là hàng chục TB. Mốc
    đúng của một tháng mới là số thô đọc được ngay lúc phát hiện đã sang tháng.
    """
    from apps.vps import bang_thong

    cfg = dict(getattr(profile, "network_config", None) or {})
    tt = dict(cfg.get(_KHOA_CAU_HINH_CONG_VAO) or {})
    thang = _thang_hien_tai(now)
    if tt.get("thang") != thang:
        tt = {"thang": thang, "tong_byte": 0,
             "moc_len": rx_byte, "moc_xuong": tx_byte}

    tong = int(tt.get("tong_byte", 0))
    moc_len = int(tt.get("moc_len", 0))
    moc_xuong = int(tt.get("moc_xuong", 0))

    if dem_hai_chieu:
        tong, moc_len = bang_thong.cong_don(tong, moc_len, rx_byte)
    else:
        # OVH chi dem chieu ra (xem bang_thong.LTT_VPS_DEM_HAI_CHIEU): khong
        # cong RX vao tong, nhung VAN cap nhat moc de lan sau khong tinh nham
        # mot khoi RX tich luy tu dau thang neu co dem lai hai chieu.
        moc_len = rx_byte
    tong, moc_xuong = bang_thong.cong_don(tong, moc_xuong, tx_byte)

    tt = {"thang": thang, "tong_byte": tong,
         "moc_len": moc_len, "moc_xuong": moc_xuong}
    cfg[_KHOA_CAU_HINH_CONG_VAO] = tt
    profile.network_config = cfg   # gan lai ca dict — JSON column can doi tuong MOI de SQLAlchemy thay doi
    return tt


def _chon_may_can_ham_theo_tong(may_sap_xep, *, tong_thang_byte: int,
                                tran_byte: int, ngay_da_qua: int,
                                so_ngay_thang: int) -> set[str]:
    """Chọn tập `id` máy cần ép hãm để dự phóng cuối tháng lọt trần.

    `may_sap_xep`: các VpsInstance đang sống, **sắp theo `bang_thong_byte`
    GIẢM DẦN** — hãm máy dùng nhiều nhất trước, đúng như đặc tả.

    ## Mô hình, và vì sao nó là một XẤP XỈ có chủ ý

    Tốc độ trung bình mỗi ngày của CẢ CỔNG (`tong_thang_byte / ngay_da_qua`) đã
    gồm cả nền production (VM100-107) lẫn mọi khách — đó là số ĐO ĐƯỢC thật từ
    bộ đếm của card mạng, không phải suy diễn. Khi ép hãm một khách, giả định
    khách đó gần như ngừng đóng góp cho phần còn lại của tháng (10 Mbps không
    đáng kể so với hạn mức GB/tháng), nên trừ ĐÚNG phần tốc độ trung bình của
    riêng khách đó (`bang_thong_byte` của khách / số ngày đã qua) khỏi tốc độ
    chung, rồi chiếu tốc độ còn lại theo số ngày còn lại của tháng. Phần của
    nền KHÔNG BAO GIỜ bị trừ — không có khách nào đại diện cho nó — nên nếu
    chính nền đã đủ đẩy dự phóng vượt trần, hãm hết mọi khách cũng không đủ,
    và hàm trả về tất cả những gì nó xét được (xem nhánh cuối vòng lặp).

    Hãm khách dùng nhiều nhất trước vì tốc độ của khách đó cũng lớn nhất — mỗi
    lần hãm kéo dự phóng xuống nhiều nhất, nên cần hãm ÍT khách nhất để đủ.

    Đây KHÔNG phải một phép đo chính xác — nó không biết tốc độ THẬT của từng
    khách trong THÁNG DƯƠNG LỊCH, chỉ biết tổng byte khách đó đã dùng TỪ ĐẦU
    CHU KỲ RIÊNG của khách (có thể lệch vài ngày so với đầu tháng). Chấp nhận
    được vì đây là lớp BẢO VỆ THÊM, không phải sổ tính tiền — sổ tính tiền vẫn
    là `bang_thong.vuot_han_muc` (lớp riêng) với cột CSDL của chính nó.
    """
    ngay_da_qua = max(1, int(ngay_da_qua))
    ngay_con_lai = max(0, int(so_ngay_thang) - ngay_da_qua)
    rate_tong_ngay = tong_thang_byte / ngay_da_qua

    da_giam_rate = 0.0
    ham: set[str] = set()
    for may in may_sap_xep:
        du_phong_byte = tong_thang_byte + (rate_tong_ngay - da_giam_rate) * ngay_con_lai
        if du_phong_byte <= tran_byte:
            return ham
        ham.add(may.id)
        da_giam_rate += max(0, int(getattr(may, "bang_thong_byte", 0) or 0)) / ngay_da_qua
    return ham


def so_lan_mat_tin_hieu(profile) -> int:
    """Số lượt LIÊN TIẾP gần nhất không đọc được bộ đếm cổng vào. 0 = đang đọc được."""
    cfg = dict(getattr(profile, "network_config", None) or {})
    tt = dict(cfg.get(_KHOA_CAU_HINH_CONG_VAO) or {})
    try:
        return max(0, int(tt.get(_KHOA_MAT_TIN_HIEU, 0)))
    except (TypeError, ValueError):
        return 0


def _ghi_tin_hieu_bang_thong_tong(db, profile, *, doc_duoc: bool,
                                  ly_do: str = "", now=None) -> int:
    """Ghi lại việc lớp canh theo TỔNG có đọc được cổng vào hay không.

    🔴 Vì sao hàm này tồn tại. `_can_ham_theo_tong` **cố ý** bỏ lượt khi đọc
       hỏng — kéo cả lớp riêng xuống theo vì một lần SSH chớp là tệ hơn. Nhưng
       bản đầu chỉ để lại một `log.warning` trong một vòng chạy mỗi giờ, tức
       một lớp bảo vệ có thể **biến mất trong im lặng**. Cái giá: cổng vào là
       OVH VPS-1 Singapore, 1 TB/tháng, vượt thì OVH hãm 10 Mbps cho TẤT CẢ —
       kể cả VM100-107, việc thật của chủ dự án.

       Đúng khuôn "đo vắng mặt thì xoá cũng xanh": không có phép kiểm nào đo
       được rằng một lớp bảo vệ đã ngừng canh, nếu nó ngừng mà không nói gì.

    Trả về số lượt hỏng liên tiếp sau khi cập nhật (0 khi vừa đọc được).
    """
    from datetime import datetime, timezone

    bay_gio = now or datetime.now(timezone.utc)
    lien_tiep = 0 if doc_duoc else so_lan_mat_tin_hieu(profile) + 1

    cfg = dict(getattr(profile, "network_config", None) or {})
    tt = dict(cfg.get(_KHOA_CAU_HINH_CONG_VAO) or {})
    tt[_KHOA_MAT_TIN_HIEU] = lien_tiep
    cfg[_KHOA_CAU_HINH_CONG_VAO] = tt
    # Gán lại CẢ dict: SQLAlchemy không theo dõi thay đổi bên trong một cột JSON.
    profile.network_config = cfg

    if db is None:
        return lien_tiep
    from apps.vps.tables import VpsProfileHealth
    if doc_duoc:
        trang_thai, tom_tat = "HEALTHY", "doc duoc bo dem cong vao"
    elif lien_tiep >= MAT_TIN_HIEU_NGHIEM_TRONG:
        trang_thai = "CRITICAL"
        tom_tat = (f"mat tin hieu bo dem cong vao {lien_tiep} luot lien tiep — "
                   f"lop canh bang thong TONG dang khong canh gi")
    else:
        trang_thai = "DEGRADED"
        tom_tat = f"khong doc duoc bo dem cong vao ({lien_tiep} luot lien tiep)"
    # Lý do kỹ thuật chỉ đi vào tóm tắt của bản ghi sức khoẻ — trang admin đọc
    # nó, khách thì không bao giờ thấy thành phần này.
    if ly_do and not doc_duoc:
        tom_tat = f"{tom_tat}: {ly_do}"
    db.add(VpsProfileHealth(
        infrastructure_profile_id=profile.id,
        component=THANH_PHAN_BANG_THONG_TONG,
        status=trang_thai, summary=tom_tat[:300],
        observed_at=bay_gio, generated_at=bay_gio))
    return lien_tiep


def _kiem_cong_quan_tri(db, profile, *, mo_cong=None, now=None) -> int:
    """Do cong SSH cua cong vao TREN TUNG dia chi, ghi mot ban ghi suc khoe.

    🔴 24/09/2026: `/etc/nftables.conf` viet `tcp dport 22 accept` — mot dieu
       kien **khong neu dia chi dich** — nen SSH quan tri tra loi tren ca 11 dia
       chi IPv4 cua cong vao, gom ca dia chi vua ban cho khach. Da chan bang
       `ip daddr != <IP quan tri> tcp dport 22 drop`.

    ## Vi sao phep do nay phai TU CHAY

    `tools/vps_doi_soat_cong.py` do duoc, nhung no chay bang tay. Mot phep kiem
    an ninh chay bang tay gop **hai** trang thai vao cung mot su im lang:
    *"chua ai chay"* va *"chay roi, dat"*. Ghi mot ban ghi suc khoe MOI luot
    tach hai thu do ra: khong co ban ghi = STALE tren trang admin.

    ## ⛔ Khong chan ban hang

    Thanh phan nay thuoc `CANH_BAO_BAO_TRI`: cong quan tri lo la viec cua nguoi
    van hanh, khach khong lam gi duoc voi tin hieu do. Dong cua hang vi no la
    phat khach cho mot loi cua ta.

    `mo_cong(ip, cong) -> (mo, ly_do)` tiem duoc de do bang test.
    Tra so dia chi bi lo (0 = sach).
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from apps.vps.tables import VpsGateway, VpsIp, VpsProfileHealth

    if mo_cong is None:
        from apps.vps.services.kiem_cong import cong_mo as mo_cong

    bay_gio = now or datetime.now(timezone.utc)
    gw = db.execute(select(VpsGateway).where(
        VpsGateway.infrastructure_profile_id == profile.id)).scalars().first()
    if gw is None or not gw.ip_cong_khai:
        return 0
    ip_quan_tri = str(gw.ip_cong_khai)
    dia_chi = [r.dia_chi for r in db.execute(select(VpsIp).where(
        VpsIp.infrastructure_profile_id == profile.id)).scalars()
        if r.dia_chi and r.dia_chi != ip_quan_tri]

    # SONG SONG. Do tuan tu 11 dia chi x 3 giay = 33 giay, va vong bao tri co
    # viec khac phai lam — do that 24/09 voi cho 6 giay: 66 giay, mat lease.
    from concurrent.futures import ThreadPoolExecutor

    can_do = sorted(dia_chi) + [ip_quan_tri]
    with ThreadPoolExecutor(max_workers=min(12, len(can_do))) as bom:
        ket = dict(zip(can_do, bom.map(lambda ip: mo_cong(ip, CONG_QUAN_TRI), can_do)))
    lo = [ip for ip in sorted(dia_chi) if ket[ip][0]]
    mo_qt = ket[ip_quan_tri][0]

    if lo:
        trang_thai = "CRITICAL"
        tom_tat = (f"cong {CONG_QUAN_TRI} MO tren {len(lo)} dia chi khong phai "
                   f"cua no: {', '.join(lo[:6])}")
    elif not mo_qt:
        # Chan qua tay cung la hong, va no hong ve phia mat quyen quan tri.
        trang_thai = "CRITICAL"
        tom_tat = (f"cong {CONG_QUAN_TRI} DONG tren chinh IP quan tri "
                   f"{ip_quan_tri} — khong con duong vao cong vao")
    else:
        trang_thai = "HEALTHY"
        tom_tat = (f"cong {CONG_QUAN_TRI} chi mo tren IP quan tri "
                   f"{ip_quan_tri} ({len(dia_chi)} dia chi khac deu dong)")

    db.add(VpsProfileHealth(
        infrastructure_profile_id=profile.id,
        component=THANH_PHAN_CONG_QUAN_TRI,
        status=trang_thai, summary=tom_tat[:300],
        observed_at=bay_gio, generated_at=bay_gio))
    if lo:
        log.error("VPS: cong quan tri LO tren %s", ", ".join(lo))
    return len(lo)


def _kiem_chuan_hoa(db, profile, *, doc_cpu=None, doc_fw=None, now=None) -> int:
    """Dem may LECH chuan danh tinh, va ghi mot ban ghi suc khoe MOI luot.

    Ba hang muc, chot 25/09/2026 khi so voi Vultr: `cpu host` (khong con `kvm64`
    generic), `ipfilter`/`macfilter` (chong mot khach ARP/IP spoof khach khac
    tren cung `vmbr1`), va rDNS cho dia chi cong khai.

    ## Vi sao phai TU CHAY

    `tools/vps_chuan_hoa.py` keo may ve chuan duoc, nhung no chay bang tay — va
    mot phep kiem chay bang tay gop *"chua ai chay"* voi *"chay roi, dat"* vao
    cung mot su im lang. Ghi mot ban ghi MOI luot tach hai thu do ra.

    `doc_cpu(vmid)` / `doc_fw(vmid)` tiem duoc de do bang test.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from apps.vps.tables import VpsInstance, VpsProfileHealth

    bay_gio = now or datetime.now(timezone.utc)
    if doc_cpu is None or doc_fw is None:
        cli = backend_factory.compute_backend(profile).client
        node = cli.config.node

        def doc_cpu(vmid, _cli=cli, _node=node):
            ra = _cli._goi("GET", f"/nodes/{_node}/qemu/{int(vmid)}/config")
            d = ra.get("data", ra) if isinstance(ra, dict) else ra
            return str((d or {}).get("cpu") or "kvm64")

        def doc_fw(vmid, _cli=cli):
            return _cli.doc_firewall(int(vmid))

    lech: list[str] = []
    for m in db.execute(select(VpsInstance).where(
            VpsInstance.infrastructure_profile_id == profile.id,
            VpsInstance.trang_thai != "da_xoa")).scalars():
        if not m.vmid:
            continue
        thieu = []
        if not str(doc_cpu(m.vmid)).startswith("host"):
            thieu.append("cpu")
        fw = doc_fw(m.vmid) or {}
        if not all(str(fw.get(k, "")).lower() in ("1", "true")
                   for k in ("enable", "ipfilter", "macfilter")):
            thieu.append("chong-gia-mao")
        if thieu:
            lech.append(f"{m.vmid}({'+'.join(thieu)})")

    if lech:
        trang_thai = "DEGRADED"
        tom_tat = f"{len(lech)} may lech chuan danh tinh: {', '.join(lech[:8])}"
    else:
        trang_thai = "HEALTHY"
        tom_tat = "moi may dung chuan danh tinh (cpu host + chong gia mao)"
    db.add(VpsProfileHealth(
        infrastructure_profile_id=profile.id, component=THANH_PHAN_CHUAN_HOA,
        status=trang_thai, summary=tom_tat[:300],
        observed_at=bay_gio, generated_at=bay_gio))
    if lech:
        log.warning("VPS: %s", tom_tat)
    return len(lech)


def _kiem_chuan_hoa_dinh_ky(db, *, now=None) -> int:
    """Chay `_kiem_chuan_hoa` cho profile mac dinh, moi ngay mot lan."""
    global _moc_chuan_hoa

    import time as _time

    from sqlalchemy import select

    from apps.vps.tables import VpsInfrastructureProfile

    if _time.monotonic() < _moc_chuan_hoa:
        return 0
    _moc_chuan_hoa = _time.monotonic() + KIEM_CHUAN_HOA_MOI_GIAY
    profile = db.execute(select(VpsInfrastructureProfile).where(
        VpsInfrastructureProfile.status == "ACTIVE",
        VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
    if profile is None:
        return 0
    try:
        so_lech = _kiem_chuan_hoa(db, profile, now=now)
        db.commit()
        return so_lech
    except (ChuaCauHinh, ProxmoxError) as exc:
        db.rollback()
        log.warning("VPS: khong kiem duoc chuan hoa may: %s", exc)
        return 0


def _kiem_cong_dinh_ky(db, *, now=None) -> int:
    """Chay `_kiem_cong_quan_tri` cho profile mac dinh, moi ngay mot lan.

    Moc RIENG: ba phep soi trong vong nay (`_doi_chieu_profiles`,
    `_doi_chieu_dinh_ky`, va phep nay) tung dung chung mot moc, va phep chay
    truoc khoa hai phep kia **24 gio trong im lang** — loi that, sua 24/09.
    """
    global _moc_kiem_cong

    import time as _time

    from sqlalchemy import select

    from apps.vps.tables import VpsInfrastructureProfile

    if _time.monotonic() < _moc_kiem_cong:
        return 0
    _moc_kiem_cong = _time.monotonic() + KIEM_CONG_MOI_GIAY
    profile = db.execute(select(VpsInfrastructureProfile).where(
        VpsInfrastructureProfile.status == "ACTIVE",
        VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
    if profile is None:
        return 0
    try:
        so_lo = _kiem_cong_quan_tri(db, profile, now=now)
        db.commit()
        return so_lo
    except OSError as exc:
        # Mang hong khong duoc lam hong vong bao tri; nhung cung ⛔ khong duoc im.
        db.rollback()
        log.warning("VPS: khong kiem duoc cong quan tri: %s", exc)
        return 0


def _can_ham_theo_tong(profile, dang_song, *, now=None, db=None) -> set[str]:
    """Tập `id` VpsInstance cần bị ép hãm bởi lớp TỔNG, cho một profile.

    Lỗi đọc cổng vào (SSH hỏng, thiếu cấu hình) KHÔNG được làm hỏng vòng bảo
    trì: trả về tập rỗng — lớp RIÊNG (đã chạy xong ở bước 1/3 của
    `_dong_bo_bang_thong`) vẫn hoạt động bình thường, chỉ là lớp tổng bỏ lượt
    này. Bộ đếm trên cổng vào vẫn chạy tiếp nên lượt sau cộng bù đủ.

    ## Fail-open là một QUYẾT ĐỊNH, không phải một chỗ chưa làm xong

    ⭐ Chủ dự án chốt 23/09/2026, sau khi được hỏi thẳng ba lựa chọn (giữ
       fail-open + báo động · hãm theo ước lượng sau 3 lượt · đóng bán máy mới
       sau 3 lượt): **giữ fail-open, chỉ báo động.**

       Lý do: hãm khách dựa trên một con số ĐỌC KHÔNG ĐƯỢC là phạt người không
       có lỗi bằng một bằng chứng không tồn tại. Ở quy mô 5–15 máy, rủi ro chạm
       trần 1 TB trong vài giờ là nhỏ, và báo động đủ để có người vào xem.

    ⛔ Đừng đổi sang fail-closed trong một bản sửa khác mà không hỏi lại. Đổi
       nó là đổi hành vi tính tiền/chất lượng của khách đang trả tiền.
       `test_2600::test_mat_tin_hieu_tong_thi_KHONG_ep_ham_may_nao` chốt điều
       này bằng cơ học, nên một lần đổi lặng lẽ sẽ làm đỏ chứ không trôi qua.

    Cái đã thêm 23/09 là **tiếng nói**, không phải hành vi: mỗi lượt đọc hỏng
    ghi một bản ghi sức khoẻ (`THANH_PHAN_BANG_THONG_TONG`), đếm số lượt liên
    tiếp, và leo thang log lên `error` từ lượt thứ `MAT_TIN_HIEU_NGHIEM_TRONG`.

    Chỉ xét `dang_song` — đúng những gì `_dong_bo_bang_thong` vừa duyệt từ
    bảng `VpsInstance`. VM100-107 không phải `VpsInstance` nên KHÔNG BAO GIỜ
    có mặt ở đây — không phải một điều kiện phải nhớ kiểm tra, mà là hệ quả
    của việc hàm này không có đường nào để với tới chúng.
    """
    from datetime import datetime, timezone

    from apps.vps import bang_thong
    from apps.vps.services.ssh_lenh import SshLenhError

    try:
        dich = _doc_cau_hinh_cong_vao()
        rx_byte, tx_byte = _doc_bo_dem_cong_vao(dich)
    except SshLenhError as exc:
        lien_tiep = _ghi_tin_hieu_bang_thong_tong(
            db, profile, doc_duoc=False, ly_do=str(exc), now=now)
        # Log LEO THANG theo số lượt: một dòng warning mỗi giờ là một dòng không
        # ai đọc, nhưng `error` sau ba lượt thì đi vào đúng chỗ người trực nhìn.
        (log.error if lien_tiep >= MAT_TIN_HIEU_NGHIEM_TRONG else log.warning)(
            "VPS bao tri: khong doc duoc bo dem cong vao (%s luot lien tiep): %s",
            lien_tiep, exc)
        return set()
    _ghi_tin_hieu_bang_thong_tong(db, profile, doc_duoc=True, now=now)

    bay_gio = now or datetime.now(timezone.utc)
    trang_thai = _cong_don_cong_vao(
        profile, rx_byte, tx_byte, now=bay_gio,
        dem_hai_chieu=_doc_dem_hai_chieu_moi_truong())
    tran_byte = bang_thong.TRAN_CONG_VAO_GB * 1024 ** 3
    tong_thang_byte = trang_thai["tong_byte"]

    if tong_thang_byte < NGUONG_BAO_VE_TONG * tran_byte:
        return set()

    may_sap_xep = sorted(
        dang_song, key=lambda m: int(m.bang_thong_byte or 0), reverse=True)
    return _chon_may_can_ham_theo_tong(
        may_sap_xep, tong_thang_byte=tong_thang_byte, tran_byte=tran_byte,
        ngay_da_qua=bay_gio.day, so_ngay_thang=_so_ngay_trong_thang(bay_gio))


def _dong_bo_bang_thong_pinned(db) -> int:
    """Số máy vừa đổi trạng thái hãm, trên mọi profile còn sống.

    ⛔ Chữ ký trả về **một số nguyên** và phải giữ nguyên như thế. Bản đầu của
       việc thêm quan sát (23/09) cho hàm này trả `int` HOẶC `dict` tuỳ một cờ
       — và `test_555` đỏ ngay, vì nó giả lập hàm này bằng một `int`. Một hàm
       đổi KIỂU trả về theo tham số là một hàm mà mọi chỗ giả lập nó đều phải
       biết cờ đó; số profile mất tín hiệu nay đếm riêng ở
       `dem_profile_mat_tin_hieu`.
    """
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


def dem_profile_mat_tin_hieu(db) -> int:
    """Số profile mà lớp canh băng thông TỔNG đang không đọc được cổng vào.

    Đọc trạng thái đã ghi, **không** đi đo lại: `_can_ham_theo_tong` vừa cập
    nhật nó trong cùng lượt bảo trì. Một lớp bảo vệ ngừng canh phải hiện ra ở
    chỗ người vận hành nhìn, và dòng tổng kết của vòng bảo trì là chỗ đó.
    """
    from sqlalchemy import select
    from apps.vps.tables import VpsInfrastructureProfile
    return sum(
        1 for profile in db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.status != "DISABLED")).scalars()
        if so_lan_mat_tin_hieu(profile))


def _doi_chieu_profiles(db):
    """Read each profile independently; no fallback to legacy provider drivers."""
    # ⚠️ MỐC RIÊNG. Trước 24/09/2026 hàm này và `_doi_chieu_dinh_ky` dùng CHUNG
    #    `_moc_doi_chieu`, nên phép soi nào chạy trước sẽ khoá phép soi kia đúng
    #    24 giờ — im lặng, và không test nào đo được sự vắng mặt ấy.
    global _moc_doi_chieu_profile
    if time.monotonic() < _moc_doi_chieu_profile:
        return 0
    _moc_doi_chieu_profile = time.monotonic() + DOI_CHIEU_MOI_GIAY
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
    can_commit = False
    for may in db.execute(select(VpsInstance).where(
            VpsInstance.trang_thai == "loi")).scalars():
        loai = {e.loai: e for e in db.execute(
            select(VpsEvent).where(VpsEvent.instance_id == may.id)).scalars()}
        if "tao_xong" in loai:
            continue                      # đã từng chạy — không hoàn, KHÔNG dọn

        # 🔴 DỌN TRƯỚC, VÀ DỌN VÔ ĐIỀU KIỆN. Đo 24/09/2026: VM 207
        #    `vps-c74d4fd8` nằm lại Proxmox ở `stopped` sau khi máy `Maytram01`
        #    vào `loi`, vì lời gọi `_nop_job_xoa` **nằm sau** `if so <= 0:
        #    continue`. Từ `cd3c7058` (23/09) đường tạo mới nhả tiền qua
        #    `credit` chứ không phát `thu_phi`, nên `so` luôn 0 ⇒ mọi máy hỏng
        #    mới đều thoát khỏi vòng dọn. Một VM mồ côi giữ vmid, 40 GB đĩa và
        #    một địa chỉ trong mạng riêng — và không ai đi tìm nó.
        #
        # ⭐ Việc DỌN và việc HOÀN TIỀN là hai câu hỏi khác nhau; gộp chúng vào
        #    một nhánh `if` là lý do lỗ này tồn tại. `_nop_job_xoa` dedupe theo
        #    máy ở hàng đợi nên gọi lại mỗi lượt là vô hại.
        try:
            _nop_job_xoa(db, may)
            can_commit = True
        except Exception as exc:          # noqa: BLE001 - khong duoc chan viec hoan
            log.warning("VPS: khong nop duoc job xoa cho may hong %s: %s",
                        may.id, exc)

        if "hoan_tien" in loai:
            continue                      # đã hoàn rồi
        thu = loai.get("thu_phi")
        so = int((thu.chi_tiet or {}).get("credit") or 0) if thu else 0
        if so <= 0:
            # Không có `thu_phi` = tiền chưa bao giờ rời tài khoản (đường giữ
            # chỗ đã nhả ở `job_runner`). ⛔ Hoàn ở đây là tặng không một khoản
            # chưa thu — nhưng máy thì vẫn vừa được dọn ở trên.
            continue

        credit.hoan_phi(db, may.user_id, so, kind=billing.KIND,
                        note=f"Hoan chu ky VPS: may {may.id[:8]} tao khong xong")
        billing.ghi_su_kien(db, may.id, "hoan_tien", boi="he_thong",
                            credit=so, ly_do=may.ly_do or "")
        da_hoan += 1
        can_commit = True
    if can_commit:
        db.commit()
    return da_hoan


#: Doi chieu bon nguon su that moi bao lau. Hang ngay, khong hang gio: no goi
#: ra Proxmox + router + gateway + Vultr, va thu no tim (mo coi) khong xuat
#: hien theo nhip gio.
DOI_CHIEU_MOI_GIAY = 24 * 3600

#: Moc lan doi chieu gan nhat, theo dong ho don dieu cua tien trinh.
#: Worker khoi dong lai thi chay lai mot luot — vo hai, vi phep quet chi DOC.
_moc_doi_chieu = 0.0
#: Mốc RIÊNG cho `_doi_chieu_profiles` — xem lý do ở chính hàm đó.
_moc_doi_chieu_profile = 0.0


def _compute_cua_profile_mac_dinh(db):
    """Compute client của profile mặc định, hoặc `None` nếu chưa đọc được.

    ⛔ Không ném: một lượt bảo trì không được chết vì phép soi không mở được
       kết nối. Nhưng cũng ⛔ không im: `quet` là chỗ duy nhất đo điện thật.
    """
    from sqlalchemy import select

    from apps.vps.tables import VpsInfrastructureProfile

    profile = db.execute(select(VpsInfrastructureProfile).where(
        VpsInfrastructureProfile.status == "ACTIVE",
        VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
    if profile is None:
        log.warning("VPS doi chieu: khong co profile ACTIVE mac dinh de do dien")
        return None
    try:
        return backend_factory.compute_backend(profile).client
    except (ChuaCauHinh, ProxmoxError, *backend_factory.operation_error_types()) as exc:
        log.warning("VPS doi chieu: khong mo duoc compute cua profile %s: %s",
                    profile.id, exc)
        return None


def _doi_chieu_dinh_ky(db, client=None) -> int:
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
    # Kiểm mốc TRƯỚC khi mở kết nối: phép soi chạy mỗi ngày, nên 23 giờ còn lại
    # không được tốn một lượt đăng nhập Proxmox nào.
    if time.monotonic() < _moc_doi_chieu:
        return 0
    if client is None:
        # ⚠️ `mot_luot` đặt `client = None` một cách CỐ Ý (máy pinned không đi
        #    qua endpoint compute global), nên nhận client từ người gọi nghĩa là
        #    hàm này không bao giờ chạy trên production — dây nối đủ mà không có
        #    điện. Tự lấy compute của profile **mặc định**: đó là cụm duy nhất
        #    đang chạy máy khách, và `quet` vốn hỏi một cụm.
        client = _compute_cua_profile_mac_dinh(db)
    if client is None:
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
    # Số profile mà lớp canh băng thông TỔNG đang không đọc được cổng vào. Con
    # số này phải đi tới dòng tổng kết bên dưới: một lớp bảo vệ ngừng canh mà
    # chỉ để lại `log.warning` trong một vòng chạy mỗi giờ là một lớp bảo vệ
    # biến mất trong im lặng.
    ket_qua["mat_tin_hieu_bang_thong_tong"] = dem_profile_mat_tin_hieu(db)
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
    # 🔴 Nối lại phép soi đo ĐIỆN THẬT. `_doi_chieu_profiles` đọc ba backend nhưng
    #    module `reconciliation` khai rõ là read-only và **không đọc điện**; chỗ
    #    duy nhất ghi `dien_quan_sat`/`quan_sat_luc` là `doi_chieu.quet`, gọi từ
    #    `_doi_chieu_dinh_ky` — hàm mà **không mã sản phẩm nào gọi** cho tới hôm nay.
    #
    #    Đo 24/09/2026: máy 204 mang `dien_quan_sat = chay` từ 16/09 20:41 trong
    #    khi Proxmox trả `tat` ⇒ trang khách khẳng định "Đang chạy" cho một máy
    #    đã tắt tám ngày, và `qua_cu()` không phân biệt được máy khoẻ với máy
    #    chết. Docstring của `_doi_chieu_dinh_ky` viết đúng về chính nó:
    #    *"Một phép soi không ai chạy là một phép soi không tồn tại"*.
    ket_qua["dien_mo_coi"] = _doi_chieu_dinh_ky(db)
    ket_qua["cong_quan_tri_lo"] = _kiem_cong_dinh_ky(db)
    ket_qua["may_lech_chuan"] = _kiem_chuan_hoa_dinh_ky(db)
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
                     "mo coi %s, dien mo coi %s, ip rong huy gia han %s, "
                     "mat tin hieu bang thong tong %s",
                     kq["da_thu"], kq["da_treo"], kq["da_nop_xoa"],
                     kq["da_doi_giam_toc"], kq["da_chup"], kq["da_don_ve"],
                     kq["da_hoan"], kq["thao_tac_qua_han"], kq["mo_coi"],
                     kq.get("dien_mo_coi", 0), kq.get("ip_rong_huy_gia_han", 0),
                     kq.get("mat_tin_hieu_bang_thong_tong", 0))
    finally:
        gen.close()
