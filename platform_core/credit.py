"""
credit.py — sổ credit (H3). Phần ít code nhất, ít được phép sai nhất.

Nguyên tắc bất di bất dịch:

1. **Số dư = tổng của sổ.** Không có ô `balance` nào bị sửa đè. `so_du()` luôn
   cộng lại từ bảng `credit_entries`.
2. **Chỉ ghi thêm.** Không sửa, không xoá bút toán. Sai thì ghi bút toán bù.
3. **Giữ chỗ → quyết toán → hoàn** đều trong transaction của caller (cùng với
   việc tạo job), nên tiền và job không bao giờ lệch nhau.
4. **Quyết toán/hoàn idempotent theo job.** Worker có thể gọi lại (retry, khởi
   động lại) — mỗi job chỉ được quyết toán hoặc hoàn đúng một lần.

Không hàm nào tự commit — caller (web request giữ chỗ cùng lúc tạo job; worker
quyết toán khi job xong) quyết định ranh giới transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (CREDIT_GRANT, CREDIT_HOLD, CREDIT_REFUND,
                                  CREDIT_SETTLE, CREDIT_TOPUP, CreditEntry)


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SettlementResult:
    """Kết quả quyết toán tách giá provider khỏi số tiền khách thực trả."""

    held_credit: int
    provider_credit: int
    charged_credit: int
    adjustment: int
    variance_credit: int
    capped: bool
    already_final: bool = False


class ThieuCreditError(Exception):
    """Số dư không đủ để giữ chỗ. Job KHÔNG được tạo, API KHÔNG được gọi.

    🔴 HAI SỐ, KHÔNG PHẢI MỘT CHUỖI. Trước 14/09/2026 lớp này chỉ mang lời văn
       `f"Khong du credit: can {amount}, con {con}."`, và ba trong bốn cửa công
       khai trả thẳng `str(e)` cho khách. Hệ quả đo được: khách nhận một câu
       **tiếng Việt không dấu** của nội bộ, và muốn biết cần nạp bao nhiêu thì
       phải **phân tích chuỗi** — một hợp đồng không ai dám dựa vào.

    ⭐ `can`/`con` để `public_api.errors.thieu_credit_chi_tiet` dịch sang
       `required_credit`/`balance` ở MỘT chỗ. Mặc định `None` vì còn đường ném
       cũ (`luong.ThieuCredit` bọc lại lỗi của tầng khác) chưa chắc biết số.
    """

    def __init__(self, *args, can: int | None = None, con: int | None = None):
        super().__init__(*args)
        self.can = can
        self.con = con


def _khoa_so_du_user(db: DbSession, user_id: str) -> None:
    """Khoá TUẦN TỰ mọi thao tác credit của MỘT user trong transaction hiện tại.

    Vì `so_du` là `SUM` của sổ rồi mới ghi bút toán, hai request song song của
    cùng user (hai tab, script gọi API) có thể CÙNG đọc số dư cũ rồi CÙNG giữ
    chỗ → số dư âm, mất tiền thật (double-spend). `pg_advisory_xact_lock` giữ
    đến khi commit/rollback nên request thứ hai phải xếp hàng, đọc số dư SAU khi
    request đầu đã ghi. Khoá theo khoá riêng của từng user nên user khác không
    bị chặn.

    Chỉ áp dụng cho PostgreSQL. SQLite (test/đơn máy) bỏ qua: nó tuần tự hoá ghi
    ở mức tệp và các test chạy đơn luồng, nên không có race để chặn.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"credit:{user_id}"})


def so_du(db: DbSession, user_id: str) -> int:
    """Số dư hiện tại = tổng mọi bút toán của user."""
    tong = db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.user_id == user_id)
    ).scalar_one()
    return int(tong)


def _ghi(db: DbSession, *, user_id: str, delta: int, kind: str,
         job_id: str = "", note: str = "") -> CreditEntry:
    e = CreditEntry(user_id=user_id, delta=int(delta), kind=kind,
                    job_id=job_id, note=note[:255])
    db.add(e)
    db.flush()
    return e


# ── Cộng tiền ─────────────────────────────────────────────────────────────────

def nap(db: DbSession, user_id: str, amount: int, note: str = "") -> CreditEntry:
    """Người dùng nạp tiền → +credit. (Thanh toán thật ở H6; hàm này là điểm nối.)"""
    if amount <= 0:
        raise ValueError("so credit nap phai duong")
    return _ghi(db, user_id=user_id, delta=amount, kind=CREDIT_TOPUP, note=note)


def tru(db: DbSession, user_id: str, amount: int, *, kind: str,
        note: str = "") -> bool:
    """Trừ một khoản phí trực tiếp. Trả **True nếu đủ số dư và đã trừ**, **False
    nếu không đủ** (không ghi gì, không bao giờ để số dư âm).

    Khác `giu_cho`/`quyet_toan` (dành cho một lượt job có thể hoàn): đây là phí đã
    xảy ra — thuê bao một tháng đã dùng thì không hoàn. `kind` do nơi gọi truyền
    (vd `CREDIT_NEXUS_BILL`) để sổ credit vẫn không biết gì về từng miền.
    """
    if amount <= 0:
        raise ValueError("so credit tru phai duong")
    if so_du(db, user_id) < amount:
        return False
    _ghi(db, user_id=user_id, delta=-amount, kind=str(kind)[:16], note=note)
    return True


def hoan_phi(db: DbSession, user_id: str, amount: int, *, kind: str,
             note: str = "") -> CreditEntry:
    """Hoàn lại một khoản đã trừ bằng `tru()`. Nửa còn thiếu của `tru()`.

    ## Vì sao không dùng `nap()` cho việc này

    `nap()` ghi `kind=CREDIT_TOPUP` — tức "khách nạp tiền". Dùng nó để hoàn phí
    làm **doanh thu nạp bị thổi lên** bằng đúng số tiền ta trả lại, và mọi báo
    cáo đối soát sau đó đều lệch. Hoàn phí phải mang **cùng `kind` với khoản đã
    trừ**, để một truy vấn `sum(delta) where kind=...` ra đúng doanh thu ròng của
    miền đó.

    ## Vì sao không dùng `cap_tay()`

    `cap_tay` là *admin cấp tay* và đòi `by`. Một lần hoàn tự động không phải
    hành động của người nào cả; ghi nó như admin-cấp-tay là làm bẩn nhật ký kiểm
    toán, đúng thứ `nhat_ky_admin` sinh ra để giữ sạch.

    ## Vì sao gap này tồn tại tới 2026-08-25

    `tru()` có từ đầu cho phí trực tiếp (thuê bao Nexus, VPS). Nhưng **không app
    nào từng cần hoàn một khoản phí trực tiếp** — cho tới khi app `vps` phát hiện
    ra một đường mà khách bị trừ tiền rồi job dựng máy hỏng: khách trả một chu kỳ
    và nhận một máy ở trạng thái "Lỗi". Không có hàm này thì cách sửa duy nhất là
    lạm dụng một trong hai hàm trên.
    """
    if amount <= 0:
        raise ValueError("so credit hoan phai duong")
    if not _ton_tai(db, user_id):
        raise NguoiDungKhongTonTai(f"khong co user {user_id!r}")
    return _ghi(db, user_id=user_id, delta=int(amount), kind=str(kind)[:16],
                note=note)


class NguoiDungKhongTonTai(ValueError):
    """Cấp credit cho một user_id không có trong bảng `users`."""


def cap_tay(db: DbSession, user_id: str, amount: int, *, by: str = "", note: str = "") -> CreditEntry:
    """Admin cấp/thu credit tay. `amount` âm là thu về. Ghi rõ ai cấp.

    **Bắt buộc kiểm người dùng tồn tại** (F-01, audit 2026-08-07). Trước đây hàm
    này gọi thẳng `_ghi()`, và `credit_entries` cũng không có khoá ngoại — nên gõ
    nhầm một ký tự trong UUID là credit rơi vào hư không, trong khi màn hình admin
    báo "Đã cấp +500 credit. Số dư mới: 500". Không lỗi nào ở đâu cả, và cách duy
    nhất phát hiện là tự đi truy vấn CSDL.

    Kiểm ở đây để có thông báo lỗi tử tế; khoá ngoại trong CSDL là lưới an toàn
    cuối cho mọi đường ghi khác.
    """
    if amount == 0:
        raise ValueError("so credit cap phai khac 0")
    if not _ton_tai(db, user_id):
        raise NguoiDungKhongTonTai(
            f"khong co nguoi dung nao co id {user_id!r} — khong ghi but toan nao")
    ghi_chu = (f"admin={by}; " if by else "") + note
    return _ghi(db, user_id=user_id, delta=amount, kind=CREDIT_GRANT, note=ghi_chu)


class KetQuaCapHangLoat:
    """Kết quả một lượt cấp hàng loạt. `khong_thay` rỗng nghĩa là đã cấp hết."""

    def __init__(self, da_cap: list, khong_thay: list, trung: list):
        self.da_cap = da_cap            # [(email, user_id)]
        self.khong_thay = khong_thay    # [email]
        self.trung = trung              # [email] — xuất hiện nhiều lần trong danh sách

    @property
    def thanh_cong(self) -> bool:
        return not self.khong_thay


def cap_hang_loat(db: DbSession, emails, amount: int, *, by: str = "",
                  note: str = "") -> KetQuaCapHangLoat:
    """Cấp cùng một số credit cho nhiều người, theo email.

    **Nguyên tử: một email sai thì KHÔNG AI được cấp** (chốt D4, audit 2026-08-07).
    Cấp một phần tạo ra trạng thái nửa vời — vài người có credit, vài người không,
    và không ai biết ai — rồi phải đối soát tay đúng lúc đang vội onboarding.

    Hàm này KHÔNG commit. Nơi gọi quyết định ranh giới transaction, nên nếu nó
    ném lỗi thì rollback bỏ sạch, đúng nghĩa nguyên tử.
    """
    if amount == 0:
        raise ValueError("so credit cap phai khac 0")

    da_thay, khong_thay, trung, thu_tu = {}, [], [], []
    for e in emails:
        khoa = (e or "").strip().lower()
        if not khoa:
            continue
        if khoa in da_thay or khoa in khong_thay:
            trung.append(khoa)
            continue
        # Nhan CA email LAN user id (chot D3: email la duong chinh, UUID giu lam
        # duong du phong — vd khi doi soat tu log hoac tu CSDL).
        u = tim_theo_email(db, khoa)
        uid = u.id if u is not None else (khoa if _ton_tai(db, khoa) else None)
        if uid is None:
            khong_thay.append(khoa)
        else:
            da_thay[khoa] = uid
            thu_tu.append(khoa)

    # Kiểm HẾT rồi mới ghi — không ghi dở dang xong mới phát hiện email sai.
    if khong_thay:
        return KetQuaCapHangLoat([], khong_thay, trung)

    for khoa in thu_tu:
        cap_tay(db, da_thay[khoa], amount, by=by, note=note)
    return KetQuaCapHangLoat([(k, da_thay[k]) for k in thu_tu], [], trung)


def _ton_tai(db: DbSession, user_id: str) -> bool:
    from platform_core.models import User
    if not (user_id or "").strip():
        return False
    return db.execute(
        select(User.id).where(User.id == user_id)).first() is not None


def tim_theo_email(db: DbSession, email: str):
    """Tìm người dùng theo email (chuẩn hoá). Trả `None` nếu không có.

    Có ở đây để đường cấp credit nhận **email** thay vì UUID (F-02): UUID là chuỗi
    con người không kiểm được bằng mắt, nên nó vừa gây mệt vừa là điều kiện làm
    F-01 nguy hiểm.
    """
    from platform_core.models import User
    e = (email or "").strip().lower()
    if not e:
        return None
    return db.execute(
        select(User).where(func.lower(User.email) == e)).scalar_one_or_none()


# ── Giữ chỗ / quyết toán / hoàn ───────────────────────────────────────────────

def so_da_giu(db: DbSession, job_id: str) -> int:
    """Tổng đã giữ cho một job (số dương). 0 nếu chưa giữ."""
    tong = db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0))
        .where(CreditEntry.job_id == job_id, CreditEntry.kind == CREDIT_HOLD)
    ).scalar_one()
    return -int(tong)      # hold ghi delta âm → đổi dấu ra số đã giữ


def giu_cho(db: DbSession, user_id: str, amount: int, job_id: str) -> None:
    """Giữ chỗ `amount` credit cho `job_id`. Raise `ThieuCreditError` nếu thiếu.

    Kiểm số dư TRƯỚC khi ghi: đây là chốt chặn "không đủ tiền thì không tạo job,
    không gọi API". Vì chạy trong cùng transaction với `jobs.submit`, nếu thiếu
    thì cả job lẫn bút toán đều rollback.
    """
    if amount < 0:
        raise ValueError("so credit giu cho khong the am")
    if amount == 0:
        return
    if _giu_cho_da_niem_phong(db, job_id):
        # H35.10b — trần cứng cho job đến từ `/api/v1`.
        #
        # Giữ chỗ đầu tiên của một job API LÀ con số trên báo giá đã ký. Nâng nó
        # lên sau đó nghĩa là khách trả nhiều hơn thứ họ bấm đồng ý — đúng Q84,
        # sự cố Seedance giữ 29 thu 78.
        #
        # ⭐ Hấp thụ chứ KHÔNG làm hỏng job: phần chênh là variance nội bộ của
        #    nền tảng, đúng như `quyet_toan` vốn đã hấp thụ khi provider đắt hơn
        #    báo giá. Ném lỗi ở đây sẽ giết job của khách vì một khác biệt làm
        #    tròn một credit — tệ hơn hẳn thứ nó định bảo vệ.
        #
        # ⛔ Đây KHÔNG phải nuốt lỗi lặng lẽ: nó ghi một `job_event` nội bộ, nên
        #    người trực đọc lại được vì sao giữ chỗ không nhúc nhích.
        _ghi_nhat_ky_tran(db, job_id, amount)
        return
    # Khoá TRƯỚC khi đọc số dư: từ đây tới hết transaction, chỉ request này được
    # giữ chỗ cho user này → check-then-write trở thành nguyên tử, hết double-spend.
    _khoa_so_du_user(db, user_id)
    con = so_du(db, user_id)
    if con < amount:
        raise ThieuCreditError(
            f"Khong du credit: can {amount}, con {con}.", can=amount, con=con)
    _ghi(db, user_id=user_id, delta=-amount, kind=CREDIT_HOLD, job_id=job_id,
         note=f"giu cho job {job_id[:8]}")
    # Durable internal event: support can explain the hold without reading the
    # credit note or the app's private params.  It is in the same transaction
    # as the hold, so a rollback cannot leave a misleading log row.
    from platform_core import job_events
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_held", visibility=job_events.INTERNAL,
            details={"credit": int(amount)}, event_key="credit-held",
        )


#: Khoá nền tảng gắn vào `params` của job đến từ `/api/v1`.
#: Chép giá trị thay vì import `public_api.invocation` — `credit.py` là tầng
#: dưới, và một vòng import ở đường tiền là thứ không đáng đổi lấy một chữ.
_KHOA_META_API = "_api"


def _giu_cho_da_niem_phong(db: DbSession, job_id: str) -> bool:
    """Job này đã có giữ chỗ, VÀ nó đến từ API công khai?

    Hai điều kiện, và cả hai đều cần:

    - **đã có giữ chỗ** — lần giữ ĐẦU của một job API chính là con số trên báo
      giá; chặn nó thì không job API nào chạy được;
    - **đến từ API** — đường giao diện web thì việc nâng giữ chỗ là đúng: có
      người ngồi đó, họ chọn tệp họ nhìn thấy, và họ được hỏi lại. Máy gọi máy
      thì không có ai để hỏi, nên lời hứa phải là lời hứa (Q84).
    """
    if not job_id:
        return False
    from platform_core.models import Job

    job = db.get(Job, job_id)
    if job is None or _KHOA_META_API not in (job.params or {}):
        return False
    return so_da_giu(db, job_id) > 0


def _ghi_nhat_ky_tran(db: DbSession, job_id: str, xin_them: int) -> None:
    """Ghi lại lần nâng giữ chỗ BỊ TỪ CHỐI, để người trực đọc lại được."""
    from platform_core import job_events
    from platform_core.models import Job

    job = db.get(Job, job_id)
    if job is None:
        return
    job_events.append(
        db, job, "credit_hold_capped", visibility=job_events.INTERNAL,
        details={"requested": int(xin_them), "held": int(so_da_giu(db, job_id))},
        event_key="credit-hold-capped",
    )


def _da_ket_so(db: DbSession, job_id: str) -> bool:
    """Job đã được quyết toán hoặc hoàn chưa (chống làm hai lần)."""
    n = db.execute(
        select(func.count()).select_from(CreditEntry).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind.in_((CREDIT_SETTLE, CREDIT_REFUND)),
        )
    ).scalar_one()
    return n > 0


def da_quyet_toan(db: DbSession, job_id: str) -> bool:
    """Tên công khai của `_da_ket_so`. **Một hàm, không phải bản chép.**

    ⭐ `thanh_toan.py` cần đúng vị ngữ này để biết mình đang ở **lần quyết toán
       thật** hay ở một **lần phát lại**. Nó phải biết, vì phần lẻ tích luỹ
       (`users.mcredit_du`) chỉ được cộng ở lần thật — cộng hai lần là thu của
       khách một khoản không có bút toán nào đối chứng.

    ⛔ Đừng viết lại phép đếm này ở tầng trên: hai bản đếm "đã quyết toán chưa"
       là hai bản sẽ lệch, và chúng lệch ở chỗ tính tiền.
    """
    return _da_ket_so(db, job_id)


def khoa_user(db: DbSession, user_id: str) -> None:
    """Tên công khai của `_khoa_so_du_user`, cho tầng quyết toán dùng lại.

    Đọc-rồi-ghi `users.mcredit_du` có đúng cái khe mà `_khoa_so_du_user` sinh ra
    để bịt: hai lượt của cùng một user quyết toán song song sẽ **cùng** đọc phần
    lẻ cũ rồi **cùng** ghi đè — mất một phần lẻ, tức mất doanh thu im lặng.
    """
    _khoa_so_du_user(db, user_id)


def _khoa_ket_so_job(db: DbSession, job_id: str) -> None:
    """Tuần tự hoá settle/refund của cùng một job trong PostgreSQL.

    Kiểm tra ``_da_ket_so`` rồi ghi là một thao tác check-then-write. Hai worker
    hoặc một worker và request huỷ có thể cùng vượt qua kiểm tra nếu không có
    khoá. Advisory transaction lock làm cả cụm nguyên tử mà không cần thay đổi
    schema ledger append-only.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"credit-final:{job_id}"})


def _ket_qua_da_chot(db: DbSession, job_id: str) -> SettlementResult | None:
    entry = db.execute(
        select(CreditEntry).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind.in_((CREDIT_SETTLE, CREDIT_REFUND)),
        ).order_by(CreditEntry.created_at.asc())
    ).scalars().first()
    if entry is None:
        return None
    held = so_da_giu(db, job_id)
    charged = 0 if entry.kind == CREDIT_REFUND else max(0, held - int(entry.delta))
    return SettlementResult(
        held_credit=held, provider_credit=charged, charged_credit=charged,
        adjustment=int(entry.delta), variance_credit=0, capped=False,
        already_final=True,
    )


def quyet_toan(db: DbSession, user_id: str, job_id: str,
               actual: int) -> SettlementResult:
    """Chốt job xong nhưng không bao giờ thu khách vượt mức đã giữ.

    ``actual`` là chi phí provider quan sát được. Nếu provider đắt hơn báo giá,
    phần vượt là variance nội bộ của nền tảng; khách chỉ trả tối đa ``held``.
    Kết quả trả về giúp worker công khai đúng ``charged_credit`` thay vì vô tình
    hiển thị giá provider như số tiền đã thu.
    """
    _khoa_ket_so_job(db, job_id)
    existing = _ket_qua_da_chot(db, job_id)
    if existing is not None:
        return existing
    provider_actual = max(0, int(actual))
    held = so_da_giu(db, job_id)
    charged = min(provider_actual, held)
    variance = max(0, provider_actual - held)
    dieu_chinh = held - charged
    _ghi(db, user_id=user_id, delta=dieu_chinh, kind=CREDIT_SETTLE, job_id=job_id,
         note=(f"quyet toan job {job_id[:8]}: giu {held}, thu {charged}, "
               f"provider {provider_actual}, variance {variance}"))
    from platform_core import job_events
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_settled", visibility=job_events.INTERNAL,
            details={"held_credit": int(held), "credit": int(charged),
                     "provider_credit": int(provider_actual),
                     "variance_credit": int(variance),
                     "adjustment": int(dieu_chinh), "capped": bool(variance)},
            level="warning" if variance else "info",
            event_key="credit-settled",
        )
    if variance:
        log.warning(
            "credit provider variance job=%s held=%s provider=%s variance=%s",
            job_id[:8], held, provider_actual, variance,
        )
    return SettlementResult(
        held_credit=held, provider_credit=provider_actual,
        charged_credit=charged, adjustment=dieu_chinh,
        variance_credit=variance, capped=bool(variance),
    )


def hoan(db: DbSession, user_id: str, job_id: str) -> None:
    """Hoàn toàn bộ phần đã giữ cho job (khi job lỗi). Idempotent theo job.

    Kết cục cho job: -held + held = 0. Người dùng không mất gì cho một job thất
    bại — đây là lý do phải giữ-chỗ-trước chứ không trừ-thẳng.
    """
    _khoa_ket_so_job(db, job_id)
    if _da_ket_so(db, job_id):
        return
    held = so_da_giu(db, job_id)
    if held == 0:
        return
    _ghi(db, user_id=user_id, delta=held, kind=CREDIT_REFUND, job_id=job_id,
         note=f"hoan job {job_id[:8]}: tra lai {held}")
    from platform_core import job_events
    from platform_core.i18n import N_
    from platform_core.models import Job
    job = db.get(Job, job_id)
    if job is not None:
        job_events.append(
            db, job, "credit_refunded", public_message=N_("Credit đã được hoàn lại."),
            details={"credit": int(held), "status": job.status},
            event_key="credit-refunded",
        )


# ─────────────────────────────────────────────────────────────────────────────
# GIỮ CHỖ TREO — bút toán `hold` không bao giờ được kết sổ
# ─────────────────────────────────────────────────────────────────────────────
#
# 🔴 VÌ SAO PHẦN NÀY TỒN TẠI, VÀ NÓ ĐÃ LẤY TIỀN THẬT CỦA KHÁCH
#
#    Đo trên production 2026-08-26: hai bút toán `hold` ngày 24/08 không có
#    `settle`, không có `refund`, và **không có hàng `Job` nào** để chỉ vào:
#
#        ms:de4cc565…   1 credit   2026-08-24 22:28:06
#        ms:84e9b141…   1 credit   2026-08-24 23:58:10
#
#    Số dư khách bị trừ vĩnh viễn. Không màn hình nào giải thích, và sổ này là
#    **chỉ ghi thêm** nên nó không tự lành.
#
# ⛔ VÌ SAO NÓ LỌT: LƯỚI HOÀN TIỀN CHỈ CĂNG BÊN TRONG TIẾN TRÌNH
#
#    Job qua worker thì an toàn — `jobs.reclaim_orphans` luôn đẩy job tới trạng
#    thái cuối, nên tiền luôn được kết sổ. Nhưng bốn đường giữ chỗ **trong một
#    request** (`llm/thanh_toan`, hai chỗ ở `chataistudio/routes`, và
#    `agent/budget`) không tạo hàng `Job` nào, nên **không có vòng quét nào
#    nhìn thấy chúng**. Chúng chỉ dựa vào `try/except/finally` của chính tiến
#    trình đó.
#
#    Và `setup/2-cai-dat.ps1` `Stop-Service -Force` chính tiến trình web trước
#    mỗi lần chép đè. Python không chạy `finally` khi Windows kết liễu tiến
#    trình. ⇒ **Deploy là hành động mở cửa sổ này**, đều đặn, rộng bằng đúng độ
#    dài một luồng LLM (đã đo 119 giây).
#
# ⭐ NGUYÊN TẮC LẤY TỪ NGÀNH THANH TOÁN
#
#    Với thẻ, một khoản giữ chỗ (authorization hold) **luôn có tuổi thọ**:
#    không capture thì nó tự hết hạn và tiền quay về khách. Khách không bao giờ
#    bị giữ tiền vĩnh viễn. Sổ này vi phạm đúng điểm đó — giữ chỗ ở đây không
#    có tuổi thọ nào cả.
#
#    Hàm dưới đây **chỉ ĐỌC**: nó trả lời "khoản nào đang treo", không tự hoàn.
#    Tự hoàn là một quyết định tiền và nó thuộc về chủ sản phẩm (D-04/D-07).
#    Treo được cái chuông trước đã — vì hai lần trước, chỉ một lần có người
#    tình cờ nhìn thấy.

#: Sau bao lâu thì một giữ chỗ chưa kết sổ được coi là TREO.
#:
#: Phải dài hơn **mọi việc hợp lệ còn đang chạy**, nếu không vòng quét sẽ báo
#: động về chính công việc đang diễn ra bình thường: luồng LLM đo được 119 giây,
#: job qua worker có trần thời gian riêng, và một `AgentRun` đã duyệt có thể
#: chạy lâu hơn cả hai. 6 giờ là mức mà "vẫn còn ai đó đang xử lý" không còn là
#: lời giải thích hợp lý, mà vẫn phát hiện được trong ngày.
TREO_SAU = timedelta(hours=6)

#: Trần số dòng trả về một lượt. Vòng bảo trì cần **biết có chuyện**, không cần
#: tải cả sổ về: nếu treo tới mức chạm trần này thì con số chính xác không còn
#: là thứ quyết định hành động nữa.
TREO_TRAN = 200


@dataclass(frozen=True)
class GiuChoTreo:
    """Một khoản giữ chỗ không ai còn kết sổ được.

    `ly_do` phân biệt hai lớp **sửa khác nhau**, nên nó không phải nhãn trang trí:

    - `khong_co_khoa`: `job_id` rỗng. Không ai còn kết sổ được **vì khoá kết sổ
      không tồn tại** — `quyet_toan`/`hoan` đều tra theo `job_id`. Hỏng ngay từ
      lúc sinh, không cần chờ hết hạn, và đây là lỗi của phía ghi bút toán.
    - `khong_ai_ket_so`: có khoá, quá hạn, mà không hàng `Job` nào đang sống
      mang khoá đó. Đây là ca của bốn đường giữ chỗ trong-request.
    """

    user_id: str
    job_id: str
    credit: int
    tao_luc: datetime
    ly_do: str


def _aware(value: datetime | None) -> datetime | None:
    """PostgreSQL trả datetime có múi giờ, SQLite trả naive. So sánh cần cùng loại."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def giu_cho_treo(db: DbSession, *, treo_sau: timedelta = TREO_SAU,
                 now: datetime | None = None, user_id: str = "",
                 tran: int = TREO_TRAN) -> list[GiuChoTreo]:
    """Những khoản giữ chỗ đã mất đường về. **Chỉ đọc, không sửa gì.**

    Một khoản bị coi là treo khi cả ba điều đúng:

    1. có bút toán `hold` cho `job_id` đó;
    2. **không** có `settle` và **không** có `refund` nào cho cùng `job_id`;
    3. và không còn ai có thể kết sổ nó — tức `job_id` rỗng (không có khoá), hoặc
       đã quá `treo_sau` mà không hàng `Job` nào **đang sống** mang khoá đó.

    ⛔ Điều kiện 3 là chỗ dễ viết sai nhất, và viết sai theo hướng **báo động
       giả**: một job nằm trong hàng đợi 8 tiếng vì hàng đợi tắc thì tiền của nó
       **không** treo — nó chỉ đang chờ, và `reclaim_orphans` mới là thứ canh
       đường đó. Nên job còn `queued`/`running` phải bị loại ra.

    ⭐ Ngược lại, một `AgentRun` kẹt ở `running` thì **được** báo, và đó là chủ
       ý: không có vòng quét nào thu hồi `AgentRun` treo (đã kiểm 2026-08-26),
       nên nó đúng là tiền không có đường về.
    """
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job

    moc = (now or datetime.now(timezone.utc)) - treo_sau

    # Khoá nào đã kết sổ rồi thì không cần xét nữa. Một truy vấn, không N.
    da_ket_so = select(CreditEntry.job_id).where(
        CreditEntry.kind.in_((CREDIT_SETTLE, CREDIT_REFUND)))

    cau = (select(CreditEntry.user_id, CreditEntry.job_id,
                  func.sum(CreditEntry.delta).label("tong"),
                  func.min(CreditEntry.created_at).label("tao_luc"))
           .where(CreditEntry.kind == CREDIT_HOLD,
                  CreditEntry.job_id.notin_(da_ket_so)))
    if user_id:
        cau = cau.where(CreditEntry.user_id == str(user_id))
    hang = db.execute(
        cau.group_by(CreditEntry.user_id, CreditEntry.job_id)
           .order_by(func.min(CreditEntry.created_at))
    ).all()

    # Hỏi trạng thái job MỘT lần cho tất cả khoá, thay vì một truy vấn mỗi dòng:
    # vòng bảo trì chạy trên cùng CSDL với đường phục vụ khách.
    khoa = [r.job_id for r in hang if r.job_id]
    con_song: set[str] = set()
    if khoa:
        con_song = {
            row[0] for row in db.execute(
                select(Job.id).where(Job.id.in_(khoa),
                                     Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
            ).all()
        }
        # 🔴 MỘT KHOÁ Ở ĐÂY CÓ THỂ LÀ MỘT `WorkflowRun`, KHÔNG PHẢI MỘT `Job`.
        #
        # Cột `job_id` không có khoá ngoại, và `platform_core/workflow/tien.py`
        # dùng `run.id` làm khoá sổ cho khoản giữ *1 lần/run* (`23_24` dòng 33).
        # Hỏi mỗi bảng `jobs` thì **mọi lượt chạy đang chạy bình thường** rơi ra
        # ngoài `con_song` ⇒ bị xếp là tiền treo.
        #
        # ⛔ Và hậu quả không dừng ở một báo động giả: `tu_hoan_treo()` dùng lại
        #    chính hàm này, nên sau `TU_HOAN_SAU` nó sẽ **hoàn tiền cho một lượt
        #    đang chạy** — sổ chỉ ghi thêm, nên khoản hoàn nhầm ấy không xoá
        #    được, chỉ bù được.
        #
        # ⭐ Điều kiện là "CHƯA kết thúc", không phải một danh sách trạng thái
        #    sống: thêm một trạng thái trung gian mới về sau sẽ tự động được
        #    coi là sống, thay vì im lặng bị tính là treo.
        from platform_core.models import WorkflowRun
        from platform_core.workflow.may_trang_thai import RUN_KET_THUC

        con_song |= {
            row[0] for row in db.execute(
                select(WorkflowRun.id)
                .where(WorkflowRun.id.in_(khoa),
                       WorkflowRun.status.notin_(tuple(RUN_KET_THUC)))
            ).all()
        }

    ra: list[GiuChoTreo] = []
    for r in hang:
        giu = -int(r.tong or 0)
        if giu <= 0:                       # đã cân bằng bằng bút toán bù
            continue
        if not r.job_id:
            ly_do = "khong_co_khoa"
        else:
            if r.job_id in con_song:
                continue                   # có người đang xử lý — không phải treo
            if (_aware(r.tao_luc) or moc) > moc:
                continue                   # còn trong hạn, chưa kết luận được
            ly_do = "khong_ai_ket_so"
        ra.append(GiuChoTreo(user_id=r.user_id, job_id=r.job_id, credit=giu,
                             tao_luc=_aware(r.tao_luc), ly_do=ly_do))
        if len(ra) >= tran:
            break
    return ra


# ─────────────────────────────────────────────────────────────────────────────
# H41.3 — TỰ HOÀN khoản treo, để INV-5 từ *quan sát* thành *bảo đảm*
# ─────────────────────────────────────────────────────────────────────────────
#
# `giu_cho_treo()` ở trên **chỉ báo**. Từ 2026-08-26 nó kêu chuông đúng, gửi
# email đúng, và hai khoản treo ngày 24/08 vẫn nằm nguyên đó — vì báo không phải
# hoàn. Một cái chuông mà mỗi lần kêu đều cần một người xử tay là một cái chuông
# rồi sẽ có người tắt.
#
# ⛔ VÌ SAO NGƯỠNG TỰ HOÀN PHẢI DÀI HƠN NGƯỠNG BÁO, KHÔNG ĐƯỢC BẰNG.
#
#    Chuông kêu ở `TREO_SAU` (6 giờ). Nếu tự hoàn cũng ở 6 giờ thì máy hoàn
#    **trước khi có ai kịp nhìn**, và một chẩn đoán sai biến thành tiền đã trả —
#    mà sổ này **chỉ ghi thêm**, nên "trả nhầm" không xoá được, chỉ bù được.
#    Khoảng cách 6h → 24h là 18 tiếng để người trực bác bỏ một báo động giả.
TU_HOAN_SAU = timedelta(hours=24)

#: Trần mỗi lượt. Một lỗi khiến hàng nghìn khoản bị coi là treo thì trần biến nó
#: thành **một sự cố nhỏ nhìn thấy được** thay vì một lần hoàn hàng loạt.
TU_HOAN_TRAN = 20


def tu_hoan_treo(db: DbSession, *, tu_hoan_sau: timedelta = TU_HOAN_SAU,
                 now: datetime | None = None,
                 tran: int = TU_HOAN_TRAN) -> list[GiuChoTreo]:
    """Hoàn những khoản giữ chỗ đã treo quá `tu_hoan_sau`. Trả về cái đã hoàn.

    Gọi **dưới lease** (`_mot_luot_bao_tri`). Caller commit.

    ⭐ Không đổi schema, và đó là chủ ý. Kế hoạch đề xuất một cột
       `hold_expires_at`, nhưng `giu_cho_treo()` đã tính đủ từ `created_at`;
       thêm cột nghĩa là **migration + backfill trên bảng tiền đang sống** để
       đổi lấy đúng con số đã có.

    ⛔ CHỈ hoàn khoản CÓ `job_id`. Khoản `ly_do="khong_co_khoa"` không có đường
       kết sổ nào — `hoan()` tra theo `job_id` — nên tự động hoá nó nghĩa là
       **đoán tiền thuộc về ai**. Đó là thứ không được đoán; để người xử.
    """
    treo = giu_cho_treo(db, treo_sau=tu_hoan_sau, now=now, tran=tran * 5)
    lam = [t for t in treo if t.job_id]

    da_hoan: list[GiuChoTreo] = []
    for muc in lam:
        if len(da_hoan) >= tran:
            # Nói ra, không cắt im lặng: một trần âm thầm đọc như "đã xong hết".
            log.warning(
                "TU HOAN TREO: cham tran %d moi luot, con %d khoan cho luot sau",
                tran, len(lam) - len(da_hoan))
            break
        # `hoan()` idempotent theo job va tu khoa ket so, nen mot lan chay hai
        # tien trinh (neu lease hong) van khong tra hai lan.
        hoan(db, muc.user_id, muc.job_id)
        da_hoan.append(muc)

    if da_hoan:
        log.warning("TU HOAN TREO: da hoan %d khoan, tong %d credit",
                    len(da_hoan), sum(m.credit for m in da_hoan))
    return da_hoan
