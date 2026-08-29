"""Read-model cho khu quản trị nền tảng: khách hàng, tiền, chú ý.

## Vì sao tệp này tồn tại

`ChiTietNguoiDungView` (`server/admin.py`) gọi thẳng `db.query(Job)...`,
`db.query(PaymentOrder)...`, `db.query(Session)...` trong handler HTTP. Nó chạy
được, nhưng nó là truy vấn ORM thô nằm trong tầng trình bày — và trang Danh sách
khách hàng cùng trang Hồ sơ 360 cần **đúng bộ truy vấn đó cộng thêm**. Viết lần
thứ hai trong một view nữa là có hai bản của cùng một định nghĩa "một khách hàng
đang thế nào".

Khuôn lấy từ `platform_core/public_api/admin_console.py` — cùng vai trò, cho
miền API. Hai tệp cùng tên ở hai miền là có chủ ý: người đọc một cái hiểu ngay
cái kia.

⛔ Đây là tầng ĐỌC. Không có hàm nào ở đây ghi. Mọi mutation vẫn đi qua
   `platform_core/credit.py`, `platform_core/billing.py`, `platform_core/users.py`
   như cũ — sổ credit vẫn append-only, mark-paid vẫn idempotent.

Hợp đồng: `docs/admin_mvp_v3/05_PAGE_CONTRACT_MATRIX.md` Phần I.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from platform_core.models import (AppAccess, CreditEntry, Job, NhatKyAdmin,
                                  PaymentOrder, User)
from platform_core.models import Session as DbSession

#: Số dòng mỗi trang. Bằng với `public_api/admin_console.PAGE_SIZE` để hai khu
#: không phân trang khác nhau mà không có lý do.
CO_TRANG = 25


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


# ── Khách hàng ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DongKhach:
    """Một dòng trong danh sách khách hàng.

    `so_du` là **credit**, không phải đồng. Nền tảng tách hai đơn vị này
    (`PaymentOrder` có cả `price_vnd` lẫn `credits`, tỉ giá 1 credit = 100 đ), và
    trộn chúng trong một ô là sai số hiển thị 100 lần.
    """

    user: User
    so_du: int


def _so_du_theo_lo(db, user_ids: list[str]) -> dict[str, int]:
    """Số dư của nhiều người trong MỘT truy vấn.

    Gọi `credit.so_du()` trong vòng lặp cho 25 dòng là 25 lượt đi CSDL cho một
    trang danh sách — và đó chính là kiểu chi phí không hiện ra ở đâu cho tới
    khi bảng có vài nghìn dòng.
    """
    if not user_ids:
        return {}
    hang = db.execute(
        select(CreditEntry.user_id, func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id.in_(user_ids))
        .group_by(CreditEntry.user_id)).all()
    return {uid: int(tong) for uid, tong in hang}


#: Cột sắp xếp được, và biểu thức tương ứng. Danh sách trắng — không nhận tên
#: cột tuỳ ý từ URL, vì đó là một đường ghép chuỗi vào câu truy vấn.
#:
#: ⚠️ KHÔNG có "số dư" ở đây, và đó là một chốt chứ không phải việc chưa làm:
#:    số dư là TỔNG của sổ append-only, nên sắp theo nó cần một phép gộp trên
#:    toàn bảng `credit_entries` rồi mới phân trang được. Với vài nghìn khách
#:    thì đó là một lượt quét toàn bảng cho mỗi lần đổi trang. Muốn có thì phải
#:    có cột tổng được duy trì hoặc một view — không phải thêm một dòng ở đây.
SAP_XEP = {
    "moi": (User.created_at, True),
    "cu": (User.created_at, False),
    "dang_nhap": (User.last_login_at, True),
    "email": (User.email, False),
}


def danh_sach_khach(db, *, tim: str = "", trang_thai: str = "",
                    xac_thuc: str = "", sap_xep: str = "moi",
                    limit: int = CO_TRANG, offset: int = 0) -> dict:
    """Một trang danh sách khách hàng, kèm bộ đếm để phân trang.

    Ba bộ lọc, và cả ba đều đọc trường CÓ THẬT ở bảng `users`. Ảnh mockup còn có
    "gói dịch vụ" và "khoảng thời gian tạo" — gói dịch vụ không tồn tại (nền tảng
    bán credit, không bán thuê bao), nên nó không có ở đây và có một dòng cấm
    trong `06b_SO_DANG_KY_NOI_DUNG_CAM.md`.
    """
    dk = []
    tim = (tim or "").strip()
    if tim:
        mau = f"%{tim}%"
        dk.append(or_(User.email.ilike(mau), User.id == tim,
                      User.display_name.ilike(mau)))
    if trang_thai == "hoat_dong":
        dk.append(User.is_active.is_(True))
    elif trang_thai == "vo_hieu":
        dk.append(User.is_active.is_(False))
    if xac_thuc == "roi":
        dk.append(User.is_verified.is_(True))
    elif xac_thuc == "chua":
        dk.append(User.is_verified.is_(False))

    cot, giam = SAP_XEP.get(sap_xep or "moi", SAP_XEP["moi"])
    thu_tu = cot.desc() if giam else cot.asc()

    dem = db.execute(select(func.count()).select_from(User).where(*dk)).scalar_one()
    hang = db.execute(
        select(User).where(*dk)
        .order_by(thu_tu)
        .limit(max(1, min(limit, 200))).offset(max(0, offset))).scalars().all()

    so_du = _so_du_theo_lo(db, [u.id for u in hang])
    return {
        "dong": [DongKhach(user=u, so_du=so_du.get(u.id, 0)) for u in hang],
        "tong": int(dem),
        "limit": limit,
        "offset": offset,
        "sap_xep": sap_xep if sap_xep in SAP_XEP else "moi",
    }


def dem_chu_y_khach(db) -> dict:
    """Ba tín hiệu ĐƠN ĐỊNH cho rail chú ý của trang danh sách.

    ⚠️ Ảnh mockup có bốn ô: "Tài khoản bị khoá", "Nợ quá hạn", "Sắp hết hạn gói",
    "Yêu cầu hỗ trợ mở". Chỉ ô đầu có thật. Nền tảng trả trước bằng credit nên
    không có công nợ; không có gói thuê bao nên không có hạn gói; không có hệ
    ticket nên không có yêu cầu hỗ trợ. Ba ô kia không được dựng.

    Ô thứ ba ở đây (`so_du_am`) KHÔNG có trong ảnh, nhưng nó là tín hiệu vận hành
    thật duy nhất còn lại về tiền: sổ append-only vẫn có thể ra số âm nếu một
    lượt quyết toán lớn hơn phần đã giữ.
    """
    vo_hieu = db.execute(select(func.count()).select_from(User)
                         .where(User.is_active.is_(False))).scalar_one()
    chua_xac_thuc = db.execute(select(func.count()).select_from(User)
                               .where(User.is_verified.is_(False))).scalar_one()
    am = db.execute(
        select(func.count()).select_from(
            select(CreditEntry.user_id.label("uid"),
                   func.sum(CreditEntry.delta).label("tong"))
            .group_by(CreditEntry.user_id).having(
                func.sum(CreditEntry.delta) < 0).subquery())).scalar_one()
    return {"vo_hieu": int(vo_hieu), "chua_xac_thuc": int(chua_xac_thuc),
            "so_du_am": int(am)}


# ── Hồ sơ 360 ────────────────────────────────────────────────────────────────

def ho_so_khach(db, *, khoa: str, gan_day: int = 15) -> dict | None:
    """Toàn cảnh MỘT khách hàng. `khoa` là email hoặc User ID.

    Trả `None` nếu không có ai khớp — người gọi quyết định 404, không phải tệp
    này.

    Tám khối, và **chỉ** tám khối này có nguồn dữ liệu thật. Ảnh mockup còn có
    ngày sinh, số điện thoại, địa chỉ, quốc gia, KYC, ghi chú hỗ trợ, gói dịch
    vụ và vị trí địa lý của phiên — bảng `users` không có một trường nào trong
    số đó (`06b`).
    """
    u = db.execute(select(User).where(
        func.lower(User.email) == khoa.strip().lower())).scalar_one_or_none()
    if u is None:
        u = db.get(User, khoa.strip())
    if u is None:
        return None

    n = max(1, min(gan_day, 100))
    but_toan = db.execute(
        select(CreditEntry).where(CreditEntry.user_id == u.id)
        .order_by(CreditEntry.created_at.desc()).limit(n)).scalars().all()
    viec = db.execute(
        select(Job).where(Job.user_id == u.id)
        .order_by(Job.created_at.desc()).limit(n)).scalars().all()
    don = db.execute(
        select(PaymentOrder).where(PaymentOrder.user_id == u.id)
        .order_by(PaymentOrder.created_at.desc()).limit(10)).scalars().all()
    phien = db.execute(
        select(DbSession).where(DbSession.user_id == u.id)
        .order_by(DbSession.created_at.desc()).limit(10)).scalars().all()
    quyen = db.execute(
        select(AppAccess).where(AppAccess.user_id == u.id)).scalars().all()
    # Nhật ký admin ghi `doi_tuong` là chuỗi tự do, nên tra theo cả id lẫn email:
    # các đường ghi khác nhau dùng khác nhau, và bỏ sót một nửa dấu vết còn tệ
    # hơn không hiện dấu vết nào.
    nhat_ky = db.execute(
        select(NhatKyAdmin).where(
            or_(NhatKyAdmin.doi_tuong == u.id, NhatKyAdmin.doi_tuong == u.email))
        .order_by(NhatKyAdmin.created_at.desc()).limit(n)).scalars().all()

    so_du = db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id == u.id)).scalar_one()

    viec_hong = sum(1 for j in viec if (j.status or "") == "error")
    return {
        "user": u,
        "so_du": int(so_du),
        "but_toan": but_toan,
        "viec": viec,
        "viec_hong": viec_hong,
        "don": don,
        "phien": phien,
        "quyen": quyen,
        "nhat_ky": nhat_ky,
    }


# ── Hàng đợi chú ý (trang Tổng quan) ─────────────────────────────────────────

def hang_doi_chu_y(db, *, limit: int = 10) -> list[dict]:
    """Những việc đang cần người xử, mỗi việc kèm ĐÍCH giải quyết được nó.

    Luật của hợp đồng P1: mỗi mục phải mở đúng trang xử lý được nó, kèm bộ lọc
    đã đặt sẵn. Một hàng đợi chú ý mà bấm vào lại ra một trang phải tự lọc tiếp
    là một danh sách thông báo, không phải một hàng đợi.

    Chỉ có ba nguồn, và cả ba đều đếm được từ bảng thật. Không có "cảnh báo cấu
    hình", không có "sự cố hệ thống", không có "bất thường" — nền tảng không có
    nơi nào sinh ra ba thứ đó.

    ⛔ Hàm này trả `ma` (mã định danh) chứ KHÔNG trả nhãn tiếng Việt. Nhãn là
       việc của tầng trình bày: một read-model mang chuỗi hiển thị thì chuỗi đó
       nằm ngoài tầm với của bộ dịch, và `tools/check_i18n.py` đếm nó như một
       chuỗi chưa bọc — đúng như vậy.
    """
    ra: list[dict] = []

    viec_hong = db.execute(select(func.count()).select_from(Job)
                           .where(Job.status == "error")).scalar_one()
    if viec_hong:
        ra.append({"ma": "viec_hong", "muc": "loi", "so": int(viec_hong),
                   "dich": "/admin/job/list"})

    don_cho = db.execute(select(func.count()).select_from(PaymentOrder)
                         .where(PaymentOrder.status == "pending")).scalar_one()
    if don_cho:
        ra.append({"ma": "don_cho", "muc": "canh", "so": int(don_cho),
                   "dich": "/admin/don?st=pending"})

    tk_vo_hieu = db.execute(select(func.count()).select_from(User)
                            .where(User.is_active.is_(False))).scalar_one()
    if tk_vo_hieu:
        ra.append({"ma": "tk_vo_hieu", "muc": "canh", "so": int(tk_vo_hieu),
                   "dich": "/admin/khach-hang?trang_thai=vo_hieu"})

    return ra[:limit]


def emails_cua(db, user_ids) -> dict[str, str]:
    """`user_id → email` cho một lô, trong MỘT truy vấn.

    Bảng đơn hàng và sổ credit chỉ giữ `user_id`. Hiện tám ký tự đầu của một
    UUID là buộc người vận hành chép nó sang một trang khác để biết đó là ai —
    đúng luồng mà `03_IA_FREEZE.md` và Golden Journey 1 nói phải hết.
    """
    ids = [i for i in dict.fromkeys(user_ids) if i]
    if not ids:
        return {}
    return {uid: email for uid, email in
            db.execute(select(User.id, User.email).where(User.id.in_(ids))).all()}
