"""CrawlApplicationService (spec §8): validate theo registry, dựng params, nộp job, dedup, lịch sử, thống kê.

Route chỉ gọi vào đây; handler (`jobs.py`) chỉ gọi `da_tai_ids`. Mọi truy vấn lọc theo chủ sở hữu.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from apps.video_crawler import an_toan_url, nen_tang
from apps.video_crawler.manifest import MANIFEST, SO_MUC_TOI_DA
from platform_core.models import JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING, Job

JOB_KHAM_PHA = "video_crawler.kham_pha"
JOB_TAI = "video_crawler.tai"

#: Số lượt thử của job tải (nền tảng mặc định 3; route UI phải tự truyền — ARCHITECTURE_MAP §1).
SO_LAN_THU = 2
DAU_VAO_TOI_DA = 500
#: Dedup "không trùng" chỉ nhớ được chừng này: `jobs.result` bị xoá sau 30 ngày (spec §13).
SO_JOB_DEDUP = 500


#: Trần xem trước mỗi phút mỗi user (phản biện #8: tìm dồn dập từ IP máy A ⇒ YouTube bot-check).
KHAM_PHA_MOI_PHUT = 10
#: Id khi nền chưa khai `mau_id`: chỉ ký tự an toàn cho khoá storage (chặn `..`, `/`).
_ID_CHUNG = r"[A-Za-z0-9_-]{1,64}"
#: Múi giờ của "video hôm nay" — khách ở Việt Nam (review MINOR: trước đếm từ nửa đêm UTC).
_MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")


class LoiDauVao(ValueError):
    """Yêu cầu không hợp lệ — thông điệp hiển thị được cho khách."""


class QuaTanSuat(LoiDauVao):
    """Quá nhiều lượt xem trước trong một phút."""


def _nen(nen_id: str):
    try:
        return nen_tang.lay_nen_bat(nen_id)
    except nen_tang.NenKhongHopLe as e:
        raise LoiDauVao("Nền tảng này chưa được hỗ trợ.") from e


def _kiem_url(url: str, nen, phan_giai) -> str:
    kw = {"ten_mien": nen.ten_mien}
    if phan_giai is not None:
        kw["phan_giai"] = phan_giai
    try:
        return an_toan_url.kiem(url, **kw)
    except an_toan_url.UrlKhongAnToan as e:
        raise LoiDauVao(f"Link không hợp lệ cho {nen.ten}.") from e


def _kiem_nguon(nen, che_do: str, dau_vao: str, so_luong, phan_giai, *, db=None,
                owner_id: str = "") -> tuple[str, int]:
    if che_do not in nen.che_do:
        raise LoiDauVao(f"{nen.ten} không hỗ trợ cách cào này.")
    if che_do in nen.che_do_can_dang_nhap:
        from apps.video_crawler import phien
        if db is None or not any(p.nen_tang == nen.id for p in phien.danh_sach(db, owner_id)):
            raise LoiDauVao(f"Cách cào này cần đăng nhập {nen.ten} — thêm phiên đăng nhập trước.")
    dau_vao = (dau_vao or "").strip()
    if not dau_vao:
        raise LoiDauVao("Chưa nhập từ khoá hoặc link.")
    if len(dau_vao) > DAU_VAO_TOI_DA:
        raise LoiDauVao("Nội dung nhập quá dài.")
    try:
        n = int(so_luong)
    except (TypeError, ValueError) as e:
        raise LoiDauVao("Số lượng không hợp lệ.") from e
    tran = min(nen.so_luong_toi_da, SO_MUC_TOI_DA)
    if not 1 <= n <= tran:
        raise LoiDauVao(f"Số lượng phải từ 1 đến {tran}.")
    la_handle = che_do == "kenh" and "/" not in dau_vao and not dau_vao.lower().startswith("http")
    if che_do != "tu_khoa" and not la_handle:
        url = dau_vao if dau_vao.lower().startswith("http") else "https://" + dau_vao
        dau_vao = _kiem_url(url, nen, phan_giai)
    return dau_vao, n


def dung_params_kham_pha(*, owner_id: str, nen_tang: str, che_do: str, dau_vao: str, so_luong,
                         khong_trung: bool, phan_giai=None, db=None) -> dict:
    nen = _nen(nen_tang)
    dau_vao, n = _kiem_nguon(nen, che_do, dau_vao, so_luong, phan_giai, db=db, owner_id=owner_id)
    return {"owner_id": owner_id, "nen_tang": nen.id, "che_do": che_do, "dau_vao": dau_vao,
            "so_luong": n, "khong_trung": bool(khong_trung)}


def dung_params_tai(*, owner_id: str, nen_tang: str, muc: list | None = None, nguon: dict | None = None,
                    phan_giai=None, db=None) -> dict:
    """Tải theo danh sách đã chọn ở xem trước (`muc`) HOẶC cào hết theo nguồn (`nguon`)."""
    nen = _nen(nen_tang)
    if (muc is None) == (nguon is None):
        raise LoiDauVao("Cần đúng một trong hai: danh sách mục hoặc nguồn cào.")
    if nguon is not None:
        dau_vao, n = _kiem_nguon(nen, nguon.get("che_do", ""), nguon.get("dau_vao", ""),
                                 nguon.get("so_luong"), phan_giai, db=db, owner_id=owner_id)
        return {"owner_id": owner_id, "nen_tang": nen.id,
                "nguon": {"che_do": nguon["che_do"], "dau_vao": dau_vao, "so_luong": n,
                          "khong_trung": bool(nguon.get("khong_trung"))}}
    if not isinstance(muc, list) or not 1 <= len(muc) <= SO_MUC_TOI_DA:
        raise LoiDauVao(f"Chọn từ 1 đến {SO_MUC_TOI_DA} video.")
    sach, da_co = [], set()
    for m in muc:
        vid = str((m or {}).get("id") or "").strip()
        if not re.fullmatch(nen.mau_id or _ID_CHUNG, vid):
            raise LoiDauVao("Mục không hợp lệ.")
        if vid in da_co:                  # trùng trong cùng yêu cầu ⇒ tính một lần (review MAJOR 2)
            continue
        da_co.add(vid)
        url = nen.mau_url.format(id=vid) if nen.mau_url else _kiem_url(str(m.get("url") or ""), nen, phan_giai)
        sach.append({"id": vid, "url": url, "tieu_de": str(m.get("tieu_de") or "")[:200]})
    return {"owner_id": owner_id, "nen_tang": nen.id, "muc": sach}


def dung_params_tai_tu_xem_truoc(db, *, owner_id: str, kham_pha_id: str, ids: list[str]) -> dict:
    """Đường UI: khách chỉ gửi id đã tick. Mục lấy từ kết quả xem trước (đã xong) của CHÍNH họ — không tin form."""
    job = job_cua(db, owner_id, kham_pha_id, job_type=JOB_KHAM_PHA)
    if job is None or job.status != JOB_DONE:
        raise LoiDauVao("Kết quả xem trước không còn — bấm Xem trước lại.")
    theo_id = {m.get("id"): m for m in (job.result or {}).get("muc") or []}
    chon = [theo_id[i] for i in dict.fromkeys(ids) if i in theo_id]
    if not chon:
        raise LoiDauVao("Chưa chọn video nào.")
    return dung_params_tai(owner_id=owner_id, nen_tang=job.params["nen_tang"], muc=chon)


def nop(db, *, owner_id: str, job_type: str, params: dict) -> Job:
    """Giữ credit + nộp job. KHÔNG commit (route/`get_db` commit). `owner_id` luôn lấy từ phiên đăng nhập."""
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    if job_type not in MANIFEST.job_types:
        raise LoiDauVao("Loại việc không hợp lệ.")
    if params.get("owner_id") != owner_id:
        raise LoiDauVao("Yêu cầu không thuộc tài khoản này.")
    return submit_with_credit(db, user_id=owner_id, app_slug=MANIFEST.slug, job_type=job_type,
                              params=params, dedupe_key=dedupe_key_for(job_type, params),
                              max_attempts=SO_LAN_THU)


def da_tai_ids(db, owner_id: str, nen_id: str) -> set[str]:
    """Id video chính user này đã tải XONG trên nền này (khoá dedup spec §17). Lọc trong Python: `result` là JSON."""
    rows = db.execute(
        select(Job.result).where(Job.user_id == owner_id, Job.app_slug == MANIFEST.slug,
                                 Job.job_type == JOB_TAI, Job.status == JOB_DONE)
        .order_by(Job.created_at.desc()).limit(SO_JOB_DEDUP)
    ).scalars()
    ids: set[str] = set()
    for r in rows:
        for m in (r or {}).get("muc") or []:
            if m.get("nen_tang") == nen_id and m.get("tep"):
                ids.add(str(m.get("id")))
    return ids


def kiem_tan_suat(db, owner_id: str, *, bay_gio: datetime | None = None) -> None:
    bay_gio = bay_gio or datetime.now(timezone.utc)
    moc = bay_gio - timedelta(minutes=1)
    # Tính cả "cào hết" (tai + nguon): nó cũng khám phá, và miễn phí khi mọi mục trùng/lỗi (review MINOR).
    gan_day = db.execute(
        select(Job.created_at, Job.job_type, Job.params).where(
            Job.user_id == owner_id, Job.app_slug == MANIFEST.slug)
        .order_by(Job.created_at.desc()).limit(KHAM_PHA_MOI_PHUT * 3)
    ).all()
    trong_phut = [t for t, loai, p in gan_day
                  if (loai == JOB_KHAM_PHA or (p or {}).get("nguon"))
                  and (t if t.tzinfo else t.replace(tzinfo=timezone.utc)) >= moc]
    if len(trong_phut) >= KHAM_PHA_MOI_PHUT:
        raise QuaTanSuat("Bạn đang xem trước quá nhanh — đợi một phút rồi thử lại.")


def job_cua(db, owner_id: str, job_id: str, *, job_type: str | None = None) -> Job | None:
    """Job của app này thuộc đúng chủ, hoặc None (route trả 404, không phân biệt "không có" với "không phải của bạn")."""
    job = db.get(Job, job_id)
    if job is None or job.user_id != owner_id or job.app_slug != MANIFEST.slug:
        return None
    if job_type is not None and job.job_type != job_type:
        return None
    return job


def lich_su(db, owner_id: str, *, gioi_han: int = 50) -> list[Job]:
    return list(db.execute(
        select(Job).where(Job.user_id == owner_id, Job.app_slug == MANIFEST.slug)
        .order_by(Job.created_at.desc()).limit(gioi_han)
    ).scalars())


def thong_ke(db, owner_id: str, *, bay_gio: datetime | None = None) -> dict:
    """Bốn ô thống kê — đếm JOB THẬT của user (donor đếm nhầm hàng đợi render, `W:3190`)."""
    bay_gio = (bay_gio or datetime.now(timezone.utc)).astimezone(_MUI_GIO)
    dau_ngay = bay_gio.replace(hour=0, minute=0, second=0, microsecond=0)
    kq = {"video_hom_nay": 0, "dang_chay": 0, "xong": 0, "loi": 0}
    for j in lich_su(db, owner_id, gioi_han=200):
        if j.status in (JOB_QUEUED, JOB_RUNNING):
            kq["dang_chay"] += 1
        elif j.status == JOB_DONE:
            kq["xong"] += 1
        elif j.status == JOB_ERROR:
            kq["loi"] += 1
        tao = j.created_at if j.created_at.tzinfo else j.created_at.replace(tzinfo=timezone.utc)
        if j.job_type == JOB_TAI and j.status == JOB_DONE and tao >= dau_ngay:
            kq["video_hom_nay"] += len((j.result or {}).get("video_keys") or [])
    return kq
