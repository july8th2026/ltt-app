"""Kho tài khoản HỆ THỐNG cho nền cần đăng nhập (W4-L9; chủ dự án duyệt 23/09/2026).

Vấn đề: khách gần như không bao giờ tự xuất được `cookies.txt`, nên các nền cần phiên chết về mặt sản phẩm
(`docs/migrations/video_crawler/THIET_KE_PHIEN_VA_KENH.md` §1). Phương án C (§2.2): admin nạp vài tài khoản
PHỤ của LTT vào kho; job dùng phiên RIÊNG của khách nếu có, không có thì MƯỢN một tài khoản kho.

Ba ràng buộc đến từ cộng đồng (`scratchpad/NC_KHO_TAI_KHOAN.md`), không phải từ suy đoán:

1. **Một tài khoản, một job một lúc.** instagrapi (MIT) ghi rõ: hai tiến trình cùng ghi session của một tài
   khoản làm cookie/fingerprint lệch nhau ⇒ bị buộc đăng nhập lại ⇒ dính challenge. Khoá theo TỪNG tài khoản
   là `ExecutionLease` `vc_tk:<id>` — UNIQUE `(resource, slot)` của nền tảng là chỗ quyết định, không phải
   một biến trong tiến trình (nhiều worker, nhiều máy).
2. **Chấm điểm thay vì loại ngay** (`jhao104/proxy_pool`, MIT): cộng điểm khi thành công, trừ theo MÃ lỗi.
   Lỗi mạng KHÔNG loại tài khoản — loại ngay sau một lần lỗi là cách mất sạch kho vì một sự cố thoáng qua.
3. **Trần + nghỉ theo tài khoản** (yt-dlp wiki + issue #15724: cookie dùng cho tool tải tự động dễ bị gắn cờ
   và khoá). Dồn N khách lên một tài khoản là đúng cái nền tảng phát hiện, nên trần là của TÀI KHOẢN.

⛔ Đợt đầu chỉ `douyin`, `xiaohongshu`, `tiktok`. KHÔNG bilibili: hai kho API Bilibili lớn nhất đã bị luật sư
   của Bilibili buộc đóng năm 2026 (NC §0) — rủi ro pháp lý của một pool cookie Bilibili ở quy mô SaaS thu
   tiền là tiền lệ THẬT. KHÔNG instagram đợt này (khoá tài khoản mạnh nhất).
⛔ Cookie kho không bao giờ ra `params`/`result`/log/URL: DB (mã hoá `secretbox`) → tệp tạm quyền 600 trong
   thư mục của job → yt-dlp, đúng đường `phien.tep_cookie_tam` đã dùng cho phiên riêng.
"""
from __future__ import annotations

import contextlib
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from platform_core.i18n import _ as _t

from apps.video_crawler.tables import BI_CHAN, HET_HAN, SONG, TAM_NGHI, VcTaiKhoan

_LOG = logging.getLogger(__name__)

#: Nền có kho tài khoản hệ thống ở đợt đầu (D1, chủ dự án chốt 23/09).
NEN_CO_KHO: tuple[str, ...] = ("douyin", "xiaohongshu", "tiktok")

#: Trần lượt mượn mỗi giờ của MỘT tài khoản (cửa sổ trượt, đặt lại khi quá một giờ).
TRAN_LUOT_GIO = 20
#: Nghỉ tối thiểu giữa hai lượt của cùng một tài khoản (giây). Cùng họ với `jobs.NGHI_GIUA_MUC_S`.
NGHI_GIUA_LUOT_S = 5.0
#: Trần video mỗi giờ mỗi KHÁCH khi đi qua kho (D3) — chống một khách vét kho. Trần chung 60/giờ của
#: `features.kiem_tran_tai` vẫn áp trước ở cửa nộp job; đây là trần THỨ HAI, chỉ cho lượt qua kho.
TRAN_KHACH_GIO = 20

DIEM_BAN_DAU = 10
DIEM_TOI_DA = 20
#: Điểm ≤ mốc này ⇒ ra khỏi vòng chọn (`bi_chan`/`het_han`).
DIEM_SAN = 0
#: Trừ bao nhiêu điểm theo MÃ lỗi của `apps/video_crawler/loi.py`. Không có trong bảng ⇒ `TRU_MAC_DINH`.
#: 0 nghĩa là "lỗi này không nói gì về sức khoẻ tài khoản" — lỗi của VIDEO hoặc của mạng, không phải của kho.
TRU_THEO_LOI: dict[str, int] = {
    "can_dang_nhap": DIEM_BAN_DAU,     # cookie chết: một lần là đủ để rút khỏi vòng (NC §4 "im lặng hỏng")
    "nen_chan": DIEM_BAN_DAU,          # nền chặn chính tài khoản này
    "yt_bot": 5,
    "mang": 0,                         # ⭐ NC §2: KHÔNG loại tài khoản vì một lỗi mạng
    "trich_xuat_hong": 0,              # yt-dlp lỗi vì nền đổi trang — không phải tài khoản
    "gioi_han_tuoi": 0, "chi_la_anh": 0, "url_khong_ho_tro": 0,
    "rieng_tu": 0, "khong_ton_tai": 0, "het_thoi_gian": 0,
}
TRU_MAC_DINH = 1
#: Mã lỗi nào đưa tài khoản sang trạng thái nào khi rơi dưới ngưỡng.
_TRANG_THAI_KHI_HONG: dict[str, str] = {"can_dang_nhap": HET_HAN}

#: Tiền tố tài nguyên lease. Một tài khoản = một tài nguyên, đúng MỘT slot.
TIEN_TO_LEASE = "vc_tk:"
#: Lease sống bao lâu nếu không được đập nhịp.
HAN_LEASE = timedelta(seconds=7200)
#: `mode` của lease. ⛔ KHÔNG dùng "job": `admission.reclaim_expired` ép hạn mode "job" xuống 300 s
#: (`ORPHAN_TIMEOUT_JOB`, sự cố 14/09) — một job tải dài sẽ bị worker khác cướp mất tài khoản giữa chừng.
MODE_LEASE = "kho"
#: Nhịp đập giữ chỗ.
#:
#: 🔴 VÌ SAO PHẢI CÓ. Vòng bảo trì của nền tảng gọi `admission.reclaim_expired(db)` **không lọc tài nguyên**
#:    và với hạn mặc định 20 phút (`job_runner._don_du_lieu_het_han`). Một job tải chạy 40 phút mà không đập
#:    nhịp sẽ bị vòng ấy xoá chỗ giữa chừng — rồi job thứ hai mượn đúng tài khoản đang tải, tức là **hai
#:    tiến trình trên một tài khoản**, đúng cái mà instagrapi cảnh báo là đường dẫn tới challenge (NC §2).
#:    `HAN_LEASE` dài không cứu được: vòng bảo trì áp hạn CỦA NÓ, không phải hạn của ta.
NHIP_TIM_S = 60.0


class KhoKhongHopLe(ValueError):
    """Yêu cầu quản trị kho không dùng được (nền không có kho, nhãn trống…)."""


@dataclass
class Muon:
    """Một lượt GIỮ CHỖ trên một tài khoản kho. Trả lại bằng `tra()`."""

    tai_khoan_id: str
    nen_tang: str
    nhan: str
    lease_id: str
    #: Luồng đập nhịp giữ chỗ (xem `NHIP_TIM_S`). Không tham gia so sánh/hiển thị.
    nhip: object | None = field(default=None, compare=False, repr=False)


def nen_co_kho(nen_id: str) -> bool:
    return str(nen_id) in NEN_CO_KHO


def _now(bay_gio: datetime | None = None) -> datetime:
    return bay_gio or datetime.now(timezone.utc)


def _utc(luc: datetime | None) -> datetime | None:
    if luc is None:
        return None
    return luc if luc.tzinfo else luc.replace(tzinfo=timezone.utc)


# ── Quản trị kho (trang vận hành của L9b gọi vào đây) ─────────────────────────

def them(db, *, nen_tang: str, nhan: str, cookies_txt: str) -> VcTaiKhoan:
    """Nạp một tài khoản phụ vào kho. KHÔNG commit. Cookie được lọc + mã hoá y như phiên của khách."""
    from platform_core import secretbox

    from apps.video_crawler import phien
    if not nen_co_kho(nen_tang):
        raise KhoKhongHopLe(_t("Nền tảng này chưa dùng kho tài khoản hệ thống."))
    nhan = (nhan or "").strip()
    if not nhan or len(nhan) > 64:
        raise KhoKhongHopLe(_t("Nhãn tài khoản phải có và không quá 64 ký tự."))
    nen = phien.nen_tang_cua(nen_tang)
    # Dùng chung bộ lọc của phiên khách (`phien._loc`): cùng luật "chỉ cookie của nền, bắt buộc cookie xác
    # thực, hạn đọc từ chính cookie xác thực". Hai bộ lọc cho một định dạng là hai chỗ để lệch nhau.
    dong, han = phien._loc(cookies_txt, nen)
    noi_dung = "# Netscape HTTP Cookie File\n" + "\n".join(dong) + "\n"
    bay_gio = _now()
    row = db.execute(select(VcTaiKhoan).where(VcTaiKhoan.nen_tang == nen.id,
                                              VcTaiKhoan.nhan == nhan)).scalar_one_or_none()
    if row is None:
        row = VcTaiKhoan(nen_tang=nen.id, nhan=nhan, cookie_ma_hoa="", tao_luc=bay_gio)
        db.add(row)
    row.cookie_ma_hoa = secretbox.ma_hoa(noi_dung)
    row.han = han
    row.trang_thai = SONG
    row.diem = DIEM_BAN_DAU
    row.loi_gan_nhat = None
    row.cap_nhat_luc = bay_gio
    db.flush()
    return row


def danh_sach(db, nen_tang: str | None = None) -> list[VcTaiKhoan]:
    stmt = select(VcTaiKhoan).order_by(VcTaiKhoan.nen_tang, VcTaiKhoan.nhan)
    if nen_tang:
        stmt = stmt.where(VcTaiKhoan.nen_tang == nen_tang)
    return list(db.execute(stmt).scalars())


def doi_trang_thai(db, tai_khoan_id: str, trang_thai: str) -> VcTaiKhoan:
    """Admin bật/tắt một tài khoản. Bật lại (`song`) trả điểm về mốc ban đầu — nó là một tài khoản mới với kho."""
    if trang_thai not in (SONG, HET_HAN, BI_CHAN, TAM_NGHI):
        raise KhoKhongHopLe(_t("Trạng thái không hợp lệ."))
    row = db.get(VcTaiKhoan, tai_khoan_id)
    if row is None:
        raise KhoKhongHopLe(_t("Không có tài khoản này."))
    row.trang_thai = trang_thai
    if trang_thai == SONG:
        row.diem = DIEM_BAN_DAU
        row.loi_gan_nhat = None
    row.cap_nhat_luc = _now()
    db.flush()
    return row


def xoa(db, tai_khoan_id: str) -> bool:
    row = db.get(VcTaiKhoan, tai_khoan_id)
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


# ── Mượn / trả chỗ ────────────────────────────────────────────────────────────

def con_tai_khoan_song(db, nen_id: str, *, bay_gio: datetime | None = None) -> bool:
    """Kho còn tài khoản DÙNG ĐƯỢC cho nền này không.

    Phân biệt hai câu trả lời rất khác nhau cho job: hết CHỖ (đợi lượt sau, `DangBan`) và hết TÀI KHOẢN
    (nói thật với khách + hoàn tiền). Gộp hai cái làm một là để khách chờ một việc không bao giờ chạy.
    """
    bay_gio = _now(bay_gio)
    for tk in db.execute(select(VcTaiKhoan).where(VcTaiKhoan.nen_tang == str(nen_id),
                                                  VcTaiKhoan.trang_thai == SONG)).scalars():
        han = _utc(tk.han)
        if han is None or han > bay_gio:
            return True
    return False


def muon(db, nen_id: str, *, owner_id: str = "", job_id: str = "",
         bay_gio: datetime | None = None) -> Muon | None:
    """Giữ chỗ trên một tài khoản kho còn khoẻ. `None` = không có chỗ LÚC NÀY (không phải lỗi).

    Thứ tự chọn: tài khoản lâu chưa dùng nhất trước (round-robin), điểm cao trước — chia đều lượt thay vì
    dồn vào tài khoản đầu danh sách, đúng mẫu rotation của pool cộng đồng (NC §2).
    """
    if not nen_co_kho(nen_id):
        return None
    bay_gio = _now(bay_gio)
    ds = list(db.execute(
        select(VcTaiKhoan)
        .where(VcTaiKhoan.nen_tang == str(nen_id), VcTaiKhoan.trang_thai == SONG)
        .order_by(VcTaiKhoan.dung_gan_nhat.asc().nullsfirst(), VcTaiKhoan.diem.desc(), VcTaiKhoan.nhan)
    ).scalars())
    for tk in ds:
        han = _utc(tk.han)
        if han is not None and han <= bay_gio:
            tk.trang_thai = HET_HAN                  # cookie hết hạn: rút khỏi vòng, trang vận hành sẽ thấy
            tk.loi_gan_nhat = "het_han"
            tk.cap_nhat_luc = bay_gio
            db.commit()
            continue
        if not _du_nghi(tk, bay_gio) or not _con_luot(tk, bay_gio):
            continue
        lease_id = _giu_cho(db, tk, owner_id=owner_id, job_id=job_id)
        if lease_id is None:                         # worker khác vừa thắng đúng tài khoản này
            continue
        _ghi_luot(tk, bay_gio)
        db.commit()
        m = Muon(tai_khoan_id=tk.id, nen_tang=tk.nen_tang, nhan=tk.nhan, lease_id=lease_id)
        m.nhip = _NhipTim(lease_id)
        m.nhip.bat_dau()
        return m
    return None


def tra(db, muon_: Muon | None, *, ma_loi: str | None = None, thanh_cong: bool = True,
        bay_gio: datetime | None = None) -> None:
    """Nhả chỗ và chấm điểm tài khoản.

    Ba kết cục, không phải hai: `ma_loi` ⇒ trừ theo mã; thành công ⇒ +1; `thanh_cong=False` mà không có mã
    (khách huỷ, lỗi hệ thống lạ) ⇒ **không đổi điểm** — cộng điểm cho một lượt chưa chạy xong là tự nói dối
    về sức khoẻ của kho, mà trừ điểm vì khách bấm huỷ thì cũng vậy.

    Gọi được nhiều lần (idempotent) và không bao giờ ném: đây là đường DỌN, lỗi gốc mới là thứ cần báo.
    """
    if muon_ is None:
        return
    bay_gio = _now(bay_gio)
    if muon_.nhip is not None:
        muon_.nhip.dung()
        muon_.nhip = None
    try:
        from platform_core.llm import admission
        admission.release(db, muon_.lease_id)
        tk = db.get(VcTaiKhoan, muon_.tai_khoan_id)
        if tk is not None:
            _cham_diem(tk, ma_loi, thanh_cong, bay_gio)
        db.commit()
    except Exception as e:      # noqa: BLE001 — chỗ mồ côi hết hạn theo `HAN_LEASE`, không được che lỗi gốc
        _LOG.warning("video_crawler: khong tra duoc cho kho (%s): %s", muon_.tai_khoan_id, type(e).__name__)
        with contextlib.suppress(Exception):
            db.rollback()


def _du_nghi(tk: VcTaiKhoan, bay_gio: datetime) -> bool:
    cu = _utc(tk.dung_gan_nhat)
    return cu is None or (bay_gio - cu).total_seconds() >= NGHI_GIUA_LUOT_S


def _con_luot(tk: VcTaiKhoan, bay_gio: datetime) -> bool:
    moc = _utc(tk.cua_so_luc)
    if moc is None or bay_gio - moc >= timedelta(hours=1):
        return True
    return int(tk.so_luot_trong_gio or 0) < TRAN_LUOT_GIO


def _ghi_luot(tk: VcTaiKhoan, bay_gio: datetime) -> None:
    moc = _utc(tk.cua_so_luc)
    if moc is None or bay_gio - moc >= timedelta(hours=1):
        tk.cua_so_luc, tk.so_luot_trong_gio = bay_gio, 1
    else:
        tk.so_luot_trong_gio = int(tk.so_luot_trong_gio or 0) + 1
    tk.dung_gan_nhat = bay_gio
    tk.cap_nhat_luc = bay_gio


def _cham_diem(tk: VcTaiKhoan, ma_loi: str | None, thanh_cong: bool, bay_gio: datetime) -> None:
    if ma_loi is not None:
        ma = ma_an_toan(ma_loi)
        tk.loi_gan_nhat = ma
        tk.diem = int(tk.diem or 0) - TRU_THEO_LOI.get(ma, TRU_MAC_DINH)
        if tk.diem <= DIEM_SAN:
            tk.trang_thai = _TRANG_THAI_KHI_HONG.get(ma, BI_CHAN)
    elif thanh_cong:
        tk.diem = min(DIEM_TOI_DA, int(tk.diem or 0) + 1)
        tk.loi_gan_nhat = None
    tk.cap_nhat_luc = bay_gio


def ma_an_toan(ma: str | None) -> str:
    """Chỉ nhận MÃ lỗi đã biết. Bất kỳ thứ gì khác ⇒ `loi_khac`.

    Cột `loi_gan_nhat` hiện trên trang vận hành; văn bản thô của yt-dlp chứa URL, đôi khi cả giá trị cookie —
    một cột "lỗi gần nhất" tự do là một đường rò không ai nghĩ là đường rò.
    """
    from apps.video_crawler import loi as loi_mod
    biet = {m for m, _th, _tt, _c in loi_mod._BANG} | {"loi_khac", "het_han", "het_thoi_gian"}
    ma = (ma or "").strip()
    return ma if ma in biet else "loi_khac"


def ma_tu_loi(e: BaseException) -> str | None:
    """Mã lỗi của một exception thoát ra từ thân job, hoặc None khi không nói gì về tài khoản.

    `jobs._loi_job` dựng `RuntimeError("<mã>: <câu>")` cho lỗi tạm thời và `LoiNguoiGoi("<câu>")` cho lỗi
    phía khách — câu là msgid trong bảng của `loi.py`, nên tra ngược được về mã. Huỷ job, lỗi hệ thống lạ và
    mọi thứ không tra được ⇒ None: không trừ điểm một tài khoản vì một chuyện ta không hiểu.
    """
    from platform_core.job_runner import JobCancelled

    from apps.video_crawler import loi as loi_mod
    if isinstance(e, JobCancelled):
        return None
    van_ban = str(e)
    dau = van_ban.split(":", 1)[0].strip()
    if dau in {m for m, _th, _tt, _c in loi_mod._BANG}:
        return dau
    theo_cau = {c: m for m, _th, _tt, c in loi_mod._BANG}
    for cau, ma in theo_cau.items():
        if cau and cau in van_ban:
            return ma
    return None


def ma_tu_ket_qua(ket_qua: dict | None) -> str | None:
    """Mã lỗi NẶNG nhất trong `result["loi"]` của một job xong-một-phần, hoặc None.

    Job tải được vài mục rồi vài mục báo `can_dang_nhap` là tín hiệu rõ nhất rằng tài khoản kho vừa chết —
    và nó KHÔNG thoát ra bằng exception, nên nhìn exception thôi thì cái chết ấy không bao giờ được ghi nhận.
    """
    ds = [ma_an_toan((m or {}).get("ma")) for m in (ket_qua or {}).get("loi") or []]
    nang = [m for m in ds if TRU_THEO_LOI.get(m, TRU_MAC_DINH) > 0]
    if not nang:
        return None
    return max(nang, key=lambda m: TRU_THEO_LOI.get(m, TRU_MAC_DINH))


def nhip_mot_lan(lease_id: str) -> bool:
    """Một nhịp giữ chỗ, trên phiên DB riêng. False = chỗ đã không còn (ai đó đã thu hồi)."""
    from platform_core.db import get_session
    from platform_core.llm import admission
    gen = get_session(); db = next(gen)
    try:
        con = admission.heartbeat(db, lease_id)
        db.commit()
        return bool(con)
    except Exception as e:      # noqa: BLE001 — mất một nhịp không được làm hỏng job đang tải
        _LOG.warning("video_crawler: khong dap duoc nhip cho kho: %s", type(e).__name__)
        with contextlib.suppress(Exception):
            db.rollback()
        return False
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)


class _NhipTim:
    """Luồng nền giữ chỗ suốt lượt mượn. Daemon: worker thoát thì nó không giữ tiến trình sống."""

    def __init__(self, lease_id: str):
        self.lease_id = lease_id
        self._dung = threading.Event()
        self._luong: threading.Thread | None = None

    def bat_dau(self) -> None:
        self._luong = threading.Thread(target=self._chay, name=f"vc-kho-{self.lease_id[:8]}", daemon=True)
        self._luong.start()

    def dung(self) -> None:
        self._dung.set()
        if self._luong is not None:
            self._luong.join(timeout=2.0)
            self._luong = None

    def _chay(self) -> None:
        while not self._dung.wait(NHIP_TIM_S):
            if not nhip_mot_lan(self.lease_id):
                return           # chỗ đã mất: đập tiếp cũng vô nghĩa, và `tra` vẫn dọn nốt phần của nó


def _giu_cho(db, tk: VcTaiKhoan, *, owner_id: str, job_id: str) -> str | None:
    """Giành slot duy nhất của tài khoản qua `ExecutionLease`. None = worker khác đang giữ."""
    from platform_core.llm import admission
    resource = TIEN_TO_LEASE + tk.id
    _thu_hoi_lease_chet(db, resource)
    lease = admission.acquire(db, resource=resource, slots=1, user_id=owner_id or "kho",
                              mode=MODE_LEASE, holder_id=_nguoi_giu(), job_id=job_id,
                              timeout=HAN_LEASE)
    return None if lease is None else lease.id


def _nguoi_giu() -> str:
    """Máy + pid + một mã ngẫu nhiên: hai job trong CÙNG tiến trình cũng phải phân biệt được chủ chỗ."""
    from platform_core.leases import holder_id
    return f"{holder_id()}:{uuid.uuid4().hex[:8]}"


def _thu_hoi_lease_chet(db, resource: str) -> None:
    """Xoá chỗ của job đã kết thúc (worker bị giết giữa chừng ⇒ không ai gọi `tra`).

    `HAN_LEASE` dài (một job tải chạy tới ~2 giờ và ta không đập nhịp), nên chờ hết hạn nghĩa là một tài
    khoản nằm chết hai giờ sau mỗi lần deploy. Trạng thái job trả lời sớm hơn nhiều và chắc chắn hơn.
    """
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, ExecutionLease, Job
    for lease in db.execute(select(ExecutionLease).where(ExecutionLease.resource == resource)).scalars():
        if not lease.job_id:
            continue
        job = db.get(Job, lease.job_id)
        if job is None or job.status not in (JOB_RUNNING, JOB_QUEUED):
            db.delete(lease)
    db.flush()


# ── Trần theo khách ───────────────────────────────────────────────────────────

def _nen_co_phien_rieng(db, owner_id: str) -> set[str]:
    from apps.video_crawler.tables import VcPhien
    return {r for r in db.execute(select(VcPhien.nen_tang).where(VcPhien.owner_id == owner_id)).scalars()}


def so_video_qua_kho(db, owner_id: str, *, bay_gio: datetime | None = None) -> int:
    """Số video khách này đã dùng kho để tải trong một giờ qua.

    Suy từ `jobs` chứ không từ một bảng sổ riêng: nguồn phiên là một HÀM của (nền có kho, khách có phiên
    riêng không) tại thời điểm chạy, nên đếm lại được — và một bảng sổ thứ hai là một thứ phải dọn, phải
    khai lưu trữ, phải đối soát, để trả lời đúng câu này.
    """
    from platform_core.models import Job

    from apps.video_crawler import features
    from apps.video_crawler.manifest import MANIFEST
    bay_gio = _now(bay_gio)
    moc = bay_gio - timedelta(hours=1)
    co_rieng = _nen_co_phien_rieng(db, owner_id)
    ds = db.execute(
        select(Job).where(Job.user_id == owner_id, Job.app_slug == MANIFEST.slug,
                          Job.job_type == features.JOB_TAI)
        .order_by(Job.created_at.desc()).limit(200)
    ).scalars()
    tong = 0
    for j in ds:
        tao = _utc(j.created_at)
        if tao is None or tao < moc:
            break
        nen = (j.params or {}).get("nen_tang")
        if nen in NEN_CO_KHO and nen not in co_rieng:
            tong += features._so_muc_da_dung(j)
    return tong


def kiem_tran_khach(db, owner_id: str, nen_id: str, *, bay_gio: datetime | None = None) -> None:
    """Khách vượt trần video/giờ QUA KHO ⇒ `LoiNguoiGoi` (không thử lại, hoàn tiền).

    Không phải `DangBan`: job chờ tới khi trần hết nghĩa là nó nằm trong hàng đợi cả giờ, chiếm chỗ của
    người khác và không nói gì cho ai. Nói thẳng + hoàn tiền là câu trả lời trung thực.
    """
    from platform_core.jobs import LoiNguoiGoi
    if not nen_co_kho(nen_id) or nen_id in _nen_co_phien_rieng(db, owner_id):
        return
    da_dung = so_video_qua_kho(db, owner_id, bay_gio=bay_gio)
    if da_dung > TRAN_KHACH_GIO:
        raise LoiNguoiGoi(_t("Mỗi tài khoản tải tối đa {n} video mỗi giờ qua tài khoản hệ thống "
                             "(bạn đã dùng {da}). Đợi một lát rồi thử lại, hoặc thêm phiên đăng nhập của "
                             "bạn ở mục Đăng nhập nền tảng.").format(n=TRAN_KHACH_GIO, da=da_dung))


def loi_kho_rong(nen_id: str):
    """Exception cho "kho không còn tài khoản sống" — câu cho khách, không nói gì về bên trong."""
    from platform_core.jobs import LoiNguoiGoi

    from apps.video_crawler import nen_tang
    try:
        ten = nen_tang.lay(nen_id).ten
    except Exception:      # noqa: BLE001 — nền lạ: câu chung vẫn đúng
        ten = nen_id
    return LoiNguoiGoi(_t("{ten} tạm không khả dụng. Vui lòng thử lại sau, hoặc thêm phiên đăng nhập của "
                          "bạn ở mục Đăng nhập nền tảng.").format(ten=ten))


# ── Cookie ra tệp tạm (đường DUY NHẤT cookie kho rời CSDL) ────────────────────

def cookies_txt_cua(db, tai_khoan_id: str) -> str | None:
    """Giải mã cookie của một tài khoản kho — CHỈ gọi trong worker, ngay trước khi ghi tệp tạm."""
    from platform_core import secretbox
    row = db.get(VcTaiKhoan, tai_khoan_id)
    if row is None:
        return None
    try:
        return secretbox.giai_ma(row.cookie_ma_hoa)
    except secretbox.SecretBoxError:
        return None


@contextlib.contextmanager
def tep_cookie_tam(db, muon_: Muon, thu_muc: Path):
    """Ghi cookie của tài khoản đang mượn ra một tệp quyền 600 trong `thu_muc`, xoá khi ra khỏi khối.

    Cùng tên tệp và cùng vòng đời với `phien.tep_cookie_tam`: adapter không cần biết cookie đến từ phiên
    riêng của khách hay từ kho — và "không cần biết" là lý do không có đường nào để nó lọt ra ngoài.
    """
    noi_dung = cookies_txt_cua(db, muon_.tai_khoan_id)
    if noi_dung is None:
        yield None
        return
    duong = Path(thu_muc) / f"cookies_{muon_.nen_tang}.txt"
    fd = os.open(duong, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung)
    try:
        yield duong
    finally:
        with contextlib.suppress(OSError):
            duong.unlink()


__all__ = ["BI_CHAN", "DIEM_BAN_DAU", "DIEM_TOI_DA", "HET_HAN", "KhoKhongHopLe", "Muon", "NEN_CO_KHO",
           "NGHI_GIUA_LUOT_S", "SONG", "TAM_NGHI", "TRAN_KHACH_GIO", "TRAN_LUOT_GIO", "con_tai_khoan_song",
           "cookies_txt_cua", "danh_sach", "doi_trang_thai", "kiem_tran_khach", "loi_kho_rong", "ma_an_toan",
           "ma_tu_ket_qua", "ma_tu_loi", "muon", "nen_co_kho", "nhip_mot_lan", "so_video_qua_kho",
           "tep_cookie_tam", "them", "tra", "xoa"]
