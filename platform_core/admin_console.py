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


# ── Tìm liên thực thể (omnibox) ──────────────────────────────────────────────
#
# 🔴 CÁI GÌ CHẶN Ô NÀY SUỐT ĐỢT MVP, và vì sao nó được mở bây giờ.
#
# Ảnh mockup vẽ một ô "Tìm người dùng, đơn hàng, log…". `24_DEFERRED_POST_MVP`
# mục B chặn nó với đúng một lý do — **không có read-model nào tìm liên thực
# thể** — và một luật: *"Không làm ô nhận cả đơn hàng/log rồi trả rỗng. Một ô
# hứa nhiều hơn nó làm được là một lỗi vận hành, không phải một thiếu sót thẩm
# mỹ."* Điều kiện mở lại ghi sẵn: *"có một read-model tìm kiếm hợp nhất (khách +
# đơn + request id + job id) trả về kết quả có phân loại."*
#
# Hàm này LÀ read-model đó. Nên ô tìm được nới đúng bằng thứ hàm này trả về,
# không hơn một loại nào.
#
# ⛔ NĂM loại, và mỗi loại phải chỉ ra được một bảng thật:
#      khách    `users`                    (email chính xác · id · email chứa)
#      đơn      `payment_orders`           (`order_code`, số nguyên)
#      job      `jobs`                     (id đầy đủ hoặc tiền tố)
#      request  `public_api_requests`      (`request_id` — thứ khách dán vào;
#                                           `ma_luot` — thứ sổ máy B ghi)
#      khoá     `developer_api_keys`       (`key_id` — nửa CÔNG KHAI)
#    Thêm loại thứ sáu thì phải thêm một bảng, không phải thêm một nhánh `elif`
#    trả rỗng.
#
# ⚠️ KHÔNG có tìm toàn văn. Không `LIKE %q%` trên `jobs.params`, không tìm trong
#    `nhat_ky_admin.chi_tiet`. Cả hai đều là quét toàn bảng trên bảng lớn nhất
#    hệ thống, và người vận hành gõ vào ô này là đang có sự cố — một truy vấn
#    30 giây ở đúng lúc đó tệ hơn là không có ô tìm.
#
# ⭐ Tiền tố job được cho phép vì UUID **hiện ra dưới dạng cắt** ở khắp khu quản
#    trị (`job.id[:12]`), nên thứ người ta chép được từ màn hình là một tiền tố.
#    Bắt họ tìm bằng chuỗi đầy đủ là bắt họ tìm bằng thứ giao diện không cho.

#: Trần mỗi loại. Ô tìm là đường ĐI TỚI một thực thể, không phải trang báo cáo —
#: ai cần 200 dòng thì dùng trang danh sách có bộ lọc và phân trang.
TIM_MOI_LOAI = 8

#: Trần của cột `BigInteger` (signed 64-bit). Xem chú thích ở nhánh đơn hàng.
_TRAN_BIGINT = 2 ** 63 - 1

#: Tiền tố ngắn hơn ngần này thì không tra job/request: `LIKE 'a%'` trên bảng
#: job là quét gần như toàn bảng, và nó không thu hẹp được gì cho người tìm.
TIM_TIEN_TO_TOI_THIEU = 6


def tim_lien_thuc_the(db, q: str, *, moi_loai: int = TIM_MOI_LOAI) -> dict:
    """Tìm một chuỗi trên năm loại thực thể; trả kết quả ĐÃ phân loại.

    Trả ``{"q", "nhom": [...], "tong": n}``. Mỗi nhóm có ``loai`` và ``dong``;
    mỗi dòng có ``nhan`` (định danh) + ``href`` + các **trường thô** của loại đó.

    ⛔ KHÔNG trả nhãn tiếng Việt. Tệp này là read-model — nó trả *dữ liệu*, và
       template quyết chữ. Bản đầu (29/08) trả sẵn ``"Khách hàng"``,
       ``"đã xác thực"``… và `tools/check_i18n.py` bắt đúng: 10 chuỗi hiện ra
       cho người dùng nằm trong `platform_core`. Bánh cóc đó nói về i18n, nhưng
       thứ nó thật sự chặn là **tầng trình bày rò xuống tầng dữ liệu** — và ở
       đây nó đúng cả hai nghĩa.
    """
    from platform_core.public_api.tables import (ApiRequestLog,
                                                 DeveloperApiKey)

    q = (q or "").strip()
    nhom: list[dict] = []
    if not q:
        return {"q": q, "nhom": nhom, "tong": 0}

    n = max(1, min(moi_loai, 50))
    du_dai = len(q) >= TIM_TIEN_TO_TOI_THIEU

    def _them(loai: str, dong: list[dict]) -> None:
        if dong:
            nhom.append({"loai": loai, "dong": dong})

    # ── Khách hàng ───────────────────────────────────────────────────────────
    thap = q.lower()
    users = db.execute(
        select(User).where(or_(func.lower(User.email).like(f"%{thap}%"),
                               User.id == q))
        .order_by(User.created_at.desc()).limit(n)).scalars().all()
    _them("khach", [
        {"nhan": u.email, "href": f"/admin/nguoi-dung?q={u.id}",
         "vai": u.role, "xac_thuc": bool(u.is_verified),
         "hoat_dong": bool(u.is_active)} for u in users])

    # ── Đơn hàng ─────────────────────────────────────────────────────────────
    if q.isdigit():
        # ⚠️ `int("9"*40)` **thành công** — Python có số lớn. Cột BigInteger thì
        #    không: SQLite ném `OverflowError`, PostgreSQL ném
        #    `NumericValueOutOfRange`, và cả hai thành HTTP 500 phát ra từ một ô
        #    tìm. Chặn ở đây, trước khi chạm CSDL.
        ma = int(q)
        if ma <= _TRAN_BIGINT:
            don = db.execute(select(PaymentOrder)
                             .where(PaymentOrder.order_code == ma)
                             .limit(n)).scalars().all()
            _them("don", [
                {"nhan": f"#{d.order_code}",
                 "href": f"/admin/don?q={d.order_code}",
                 "credit": d.credits, "vnd": d.price_vnd,
                 "trang_thai": d.status, "da_cong": bool(d.credited)}
                for d in don])

    # ── Job ──────────────────────────────────────────────────────────────────
    if du_dai:
        viec = db.execute(
            select(Job).where(or_(Job.id == q, Job.id.like(f"{q}%")))
            .order_by(Job.created_at.desc()).limit(n)).scalars().all()
        _them("job", [
            {"nhan": j.id[:16], "href": f"/admin/api-trace?q={j.id}",
             "loai_job": j.job_type, "trang_thai": j.status} for j in viec])

    # ── Lời gọi API ──────────────────────────────────────────────────────────
    if du_dai:
        goi = db.execute(
            select(ApiRequestLog)
            .where(or_(ApiRequestLog.request_id == q,
                       ApiRequestLog.request_id.like(f"{q}%"),
                       # T4: mã lượt (`st:…`/`ch:…`) — thứ đọc được ở dòng sổ
                       # máy B (`"ma"`). Có chỉ mục riêng. ⛔ KHÔNG thêm
                       # `phien_khach`: chỉ mục của nó mở đầu bằng `user_id`,
                       # tìm phiên không kèm khách là quét cả bảng.
                       ApiRequestLog.ma_luot == q,
                       ApiRequestLog.ma_luot.like(f"{q}%")))
            .order_by(ApiRequestLog.created_at.desc()).limit(n)).scalars().all()
        _them("request", [
            {"nhan": r.request_id[:16],
             "href": f"/admin/api-trace?q={r.request_id}",
             "method": r.method, "route": r.route, "http": r.status,
             "ma": r.code or ""} for r in goi])

    # ── Khoá của khách ───────────────────────────────────────────────────────
    # ⛔ Chỉ `key_id` — nửa CÔNG KHAI. Nửa bí mật chỉ tồn tại dưới dạng dấu vân
    #    tay một chiều, nên không có gì để mà tìm, kể cả nếu ai đó muốn.
    if du_dai:
        khoa = db.execute(
            select(DeveloperApiKey)
            .where(or_(DeveloperApiKey.key_id == q,
                       DeveloperApiKey.key_id.like(f"{q}%")))
            .limit(n)).scalars().all()
        _them("khoa", [
            {"nhan": k.key_id[:16], "href": f"/admin/api-khoa?key={k.key_id}",
             "ten": k.name or "", "trang_thai": k.status()} for k in khoa])

    return {"q": q, "nhom": nhom,
            "tong": sum(len(g["dong"]) for g in nhom)}
