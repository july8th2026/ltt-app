"""CrawlApplicationService (spec §8): validate theo registry, dựng params, nộp job, dedup, lịch sử, thống kê.

Route chỉ gọi vào đây; handler (`jobs.py`) chỉ gọi nhóm dedup (`da_tai_ids`, `gianh_cho`, `danh_dau_xong`,
`nha_cho`). Mọi truy vấn lọc theo chủ sở hữu.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from apps.video_crawler import an_toan_url, nen_tang
from apps.video_crawler.adapters.base import ID_AN_TOAN
from apps.video_crawler.manifest import MANIFEST, SO_MUC_TOI_DA
from platform_core.i18n import _ as _t
from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING, Job

JOB_KHAM_PHA = "video_crawler.kham_pha"
JOB_TAI = "video_crawler.tai"

#: Số lượt thử của job tải (nền tảng mặc định 3; route UI phải tự truyền — ARCHITECTURE_MAP §1).
SO_LAN_THU = 2
DAU_VAO_TOI_DA = 500
#: Giành chỗ 'dang_tai' cũ hơn mốc này là của job đã chết (trần job 7200 s, `_het_gio` giết không kịp dọn) ⇒ giành lại.
GIANH_CHO_HET_HAN = timedelta(hours=3)


#: Trần xem trước mỗi phút mỗi user (phản biện #8: tìm dồn dập từ IP máy A ⇒ YouTube bot-check).
KHAM_PHA_MOI_PHUT = 10
#: Múi giờ của "video hôm nay" — khách ở Việt Nam (review MINOR: trước đếm từ nửa đêm UTC).
_MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")


class LoiDauVao(ValueError):
    """Yêu cầu không hợp lệ — thông điệp hiển thị được cho khách."""


class QuaTanSuat(LoiDauVao):
    """Quá nhiều lượt xem trước trong một phút."""


# ── Lớp pháp lý của lượt tải (PLAN_MVP §C L1; DANH_GIA_MVP N1–N3, N7) ─────────
# Bản nháp văn bản + nguồn: docs/migrations/video_crawler/PHAP_LY_NHAP.md (chủ dự án duyệt — Q2).

#: Đổi câu cam kết trên UI ⇒ tăng phiên bản (params ghi phiên bản khách đã đồng ý, làm bằng chứng).
PHIEN_BAN_CAM_KET = "2026-09-22"
#: `/terms/` chuyển hướng về trang này (kiểm 22/09/2026).
URL_DIEU_KHOAN = "https://lttstudios.com/dieu-khoan-su-dung/"
#: Trang /lien-he/ chỉ khách báo vi phạm chính sách/lạm dụng về đây (kiểm 22/09/2026).
URL_BAO_VI_PHAM = "https://lttstudios.com/bao-cao-lam-dung/"
#: Tiền lệ hiển thị cho khách: `apps/vps/dieu_khoan.py`.
EMAIL_HO_TRO = "support@lttstudios.com"
#: Trần tải theo tài khoản (N7: nền chặn IP/tài khoản khi tải dồn dập). Đếm số MỤC video.
TAI_MOI_GIO = 60
TAI_MOI_NGAY = 300


class ChuaCamKet(LoiDauVao):
    """Lượt tải chưa tick ô cam kết quyền."""


class QuaTranTai(LoiDauVao):
    """Vượt trần video tải mỗi giờ / mỗi ngày của tài khoản."""


def gan_cam_ket(params: dict, *, dong_y: bool, bay_gio: datetime | None = None) -> dict:
    """Params tải + bằng chứng cam kết quyền. Chưa đồng ý ⇒ `ChuaCamKet` (xem trước không gọi hàm này)."""
    if not dong_y:
        raise ChuaCamKet(_t("Cần tick ô cam kết bạn có quyền tải và sử dụng các video này trước khi tải."))
    luc = (bay_gio or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    return {**params, "cam_ket": {"phien_ban": PHIEN_BAN_CAM_KET, "luc": luc.isoformat()}}


def khoa_dedupe(job_type: str, params: dict) -> str:
    """Khoá dedupe bỏ `cam_ket.luc`: bấm đúp cách nhau vài giây vẫn là MỘT job (không trừ tiền hai lần).

    Giữ `phien_ban`: đổi văn bản cam kết là một yêu cầu khác. Params lưu trong job vẫn giữ `luc` đầy đủ.
    """
    from platform_core.job_submit import dedupe_key_for
    ck = params.get("cam_ket")
    if isinstance(ck, dict):
        params = {**params, "cam_ket": {k: v for k, v in ck.items() if k != "luc"}}
    return dedupe_key_for(job_type, params)


def so_muc_du_kien(params: dict) -> int:
    """Số video tối đa một job tải sẽ lấy: số mục đã chọn, hoặc `so_luong` của nguồn cào hết."""
    if params.get("nguon"):
        try:
            return max(0, int(params["nguon"].get("so_luong") or 0))
        except (TypeError, ValueError):
            return 0
    return len(params.get("muc") or [])


def _so_muc_da_dung(job: Job) -> int:
    ket_qua = job.result or {}
    if job.status in (JOB_DONE, JOB_ERROR, JOB_CANCELLED) and "video_keys" in ket_qua:
        return len(ket_qua.get("video_keys") or [])            # đã kết thúc: số video tải THẬT
    if job.status == JOB_CANCELLED and job.started_at is None:
        return 0                                               # huỷ khi còn chờ: chưa chạm nền nào
    return so_muc_du_kien(job.params or {})                   # đang chờ/chạy, hoặc lỗi không kết quả: tính đủ


def kiem_tran_tai(db, owner_id: str, so_muc_moi: int, *, bay_gio: datetime | None = None) -> None:
    """Vượt trần video/giờ hoặc video/ngày (tính cả lượt mới) ⇒ `QuaTranTai`. Lọc giờ trong Python như `kiem_tan_suat`."""
    bay_gio = bay_gio or datetime.now(timezone.utc)
    moc_gio, moc_ngay = bay_gio - timedelta(hours=1), bay_gio - timedelta(days=1)
    jobs = db.execute(
        select(Job).where(Job.user_id == owner_id, Job.app_slug == MANIFEST.slug, Job.job_type == JOB_TAI)
        .order_by(Job.created_at.desc()).limit(TAI_MOI_NGAY * 2)
    ).scalars()
    trong_gio = trong_ngay = 0
    for j in jobs:
        tao = j.created_at if j.created_at.tzinfo else j.created_at.replace(tzinfo=timezone.utc)
        if tao < moc_ngay:
            break
        n = _so_muc_da_dung(j)
        trong_ngay += n
        if tao >= moc_gio:
            trong_gio += n
    if trong_gio + so_muc_moi > TAI_MOI_GIO:
        raise QuaTranTai(_t("Mỗi tài khoản tải tối đa {n} video mỗi giờ (bạn đã dùng {da}) — đợi rồi thử lại "
                            "hoặc chọn ít video hơn.").format(n=TAI_MOI_GIO, da=trong_gio))
    if trong_ngay + so_muc_moi > TAI_MOI_NGAY:
        raise QuaTranTai(_t("Mỗi tài khoản tải tối đa {n} video mỗi ngày (bạn đã dùng {da}) — thử lại sau.")
                         .format(n=TAI_MOI_NGAY, da=trong_ngay))


def chuan_bi_tai(db, owner_id: str, params: dict, *, dong_y: bool) -> dict:
    """Cổng pháp lý của MỌI lượt tải: cam kết quyền rồi trần tải. Trả params đã gắn `cam_ket`."""
    ra = gan_cam_ket(params, dong_y=dong_y)
    kiem_tran_tai(db, owner_id, so_muc_du_kien(ra))
    return ra


def _nen(nen_id: str):
    try:
        return nen_tang.lay_nen_bat(nen_id)
    except nen_tang.NenKhongHopLe as e:
        raise LoiDauVao(_t("Nền tảng này chưa được hỗ trợ.")) from e


def _kiem_url(url: str, nen, phan_giai) -> str:
    kw = {"ten_mien": nen.ten_mien}
    if phan_giai is not None:
        kw["phan_giai"] = phan_giai
    try:
        return an_toan_url.kiem(url, **kw)
    except an_toan_url.UrlKhongAnToan as e:
        raise LoiDauVao(_t("Link không hợp lệ cho {ten}.").format(ten=nen.ten)) from e


def _kiem_nguon(nen, che_do: str, dau_vao: str, so_luong, phan_giai, *, db=None,
                owner_id: str = "") -> tuple[str, int]:
    if che_do not in nen.che_do:
        raise LoiDauVao(_t("{ten} không hỗ trợ cách cào này.").format(ten=nen.ten))
    if che_do in nen.che_do_can_dang_nhap:
        from apps.video_crawler import phien
        co = [p for p in phien.danh_sach(db, owner_id) if p.nen_tang == nen.id] if db is not None else []
        if not co:
            raise LoiDauVao(_t("Cách cào này cần đăng nhập {ten} — thêm phiên đăng nhập trước.").format(ten=nen.ten))
        if not phien.hop_le(co[0]):                     # review lần 2: khoá xoay ⇒ phiên không giải mã được
            raise LoiDauVao(_t("Phiên {ten} đã hỏng (không giải mã được) — nhập lại cookies.txt.").format(ten=nen.ten))
    dau_vao = (dau_vao or "").strip()
    if not dau_vao:
        raise LoiDauVao(_t("Chưa nhập từ khoá hoặc link."))
    if len(dau_vao) > DAU_VAO_TOI_DA:
        raise LoiDauVao(_t("Nội dung nhập quá dài."))
    try:
        n = int(so_luong)
    except (TypeError, ValueError) as e:
        raise LoiDauVao(_t("Số lượng không hợp lệ.")) from e
    tran = min(nen.so_luong_toi_da, SO_MUC_TOI_DA)
    if not 1 <= n <= tran:
        raise LoiDauVao(_t("Số lượng phải từ 1 đến {tran}.").format(tran=tran))
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
        raise LoiDauVao(_t("Cần đúng một trong hai: danh sách mục hoặc nguồn cào."))
    if nguon is not None:
        dau_vao, n = _kiem_nguon(nen, nguon.get("che_do", ""), nguon.get("dau_vao", ""),
                                 nguon.get("so_luong"), phan_giai, db=db, owner_id=owner_id)
        return {"owner_id": owner_id, "nen_tang": nen.id,
                "nguon": {"che_do": nguon["che_do"], "dau_vao": dau_vao, "so_luong": n,
                          "khong_trung": bool(nguon.get("khong_trung"))}}
    if not isinstance(muc, list) or not 1 <= len(muc) <= SO_MUC_TOI_DA:
        raise LoiDauVao(_t("Chọn từ 1 đến {n} video.").format(n=SO_MUC_TOI_DA))
    from apps.video_crawler import adapters
    ad = adapters.tao(nen.id)
    sach, da_co = [], set()
    for m in muc:
        vid = str((m or {}).get("id") or "").strip()
        if not re.fullmatch(ID_AN_TOAN, vid) or not ad.id_hop_le(vid):
            raise LoiDauVao(_t("Mục không hợp lệ."))
        if vid in da_co:                  # trùng trong cùng yêu cầu ⇒ tính một lần (review MAJOR 2)
            continue
        da_co.add(vid)
        url = ad.url_chuan(vid, str(m.get("url") or ""))   # dựng lại từ id — URL khách gửi bị BỎ (review BLOCKER)
        if url is None:
            raise LoiDauVao(_t("Link {ten} không hợp lệ hoặc thiếu mã cần thiết — dán lại link đầy đủ.").format(ten=nen.ten))
        muc_sach = {"id": vid, "url": url, "tieu_de": str(m.get("tieu_de") or "")[:200]}
        tl = _thoi_luong(m.get("thoi_luong_s"))
        if tl is not None:                 # giá theo thời lượng thật (gia.gia_muc); lạ ⇒ bỏ ⇒ bậc ≤ 10 phút
            muc_sach["thoi_luong_s"] = tl
        sach.append(muc_sach)
    return {"owner_id": owner_id, "nen_tang": nen.id, "muc": sach}


def _thoi_luong(v) -> int | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return int(v) if 0 < v <= 24 * 3600 else None


def dung_params_tai_tu_xem_truoc(db, *, owner_id: str, kham_pha_id: str, ids: list[str]) -> dict:
    """Đường UI: khách chỉ gửi id đã tick. Mục lấy từ kết quả xem trước (đã xong) của CHÍNH họ — không tin form."""
    job = job_cua(db, owner_id, kham_pha_id, job_type=JOB_KHAM_PHA)
    if job is None or job.status != JOB_DONE:
        raise LoiDauVao(_t("Kết quả xem trước không còn — bấm Xem trước lại."))
    theo_id = {m.get("id"): m for m in (job.result or {}).get("muc") or []}
    chon = [theo_id[i] for i in dict.fromkeys(ids) if i in theo_id]
    if not chon:
        raise LoiDauVao(_t("Chưa chọn video nào."))
    return dung_params_tai(owner_id=owner_id, nen_tang=job.params["nen_tang"], muc=chon)


def nop(db, *, owner_id: str, job_type: str, params: dict) -> Job:
    """Giữ credit + nộp job. KHÔNG commit (route/`get_db` commit). `owner_id` luôn lấy từ phiên đăng nhập."""
    from platform_core.job_submit import submit_with_credit
    if job_type not in MANIFEST.job_types:
        raise LoiDauVao(_t("Loại việc không hợp lệ."))
    if params.get("owner_id") != owner_id:
        raise LoiDauVao(_t("Yêu cầu không thuộc tài khoản này."))
    return submit_with_credit(db, user_id=owner_id, app_slug=MANIFEST.slug, job_type=job_type,
                              params=params, dedupe_key=khoa_dedupe(job_type, params),
                              max_attempts=SO_LAN_THU)


def da_tai_ids(db, owner_id: str, nen_id: str, *, tru_job_id: str | None = None,
               bay_gio: datetime | None = None) -> set[str]:
    """Id video user này đã tải xong, hoặc đang được một job khác của họ tải, trên nền này (khoá dedup spec §17).

    Đọc sổ bền `vc_da_tai` — không giới hạn 30 ngày/500 job như khi suy từ `jobs.result`. Mục của job xong TRƯỚC khi có
    bảng không được tính (không di trú: app còn sau cờ, chưa có khách — xem migration `vc_da_tai`).
    `tru_job_id`: bỏ dòng của chính job đang chạy (lượt thử lại sau khi worker chết không tự lọc mục của mình).
    """
    from apps.video_crawler.tables import DANG_TAI, XONG, VcDaTai
    moc = (bay_gio or datetime.now(timezone.utc)) - GIANH_CHO_HET_HAN
    rows = db.execute(
        select(VcDaTai.video_id, VcDaTai.trang_thai, VcDaTai.cap_nhat_luc, VcDaTai.job_id)
        .where(VcDaTai.owner_id == owner_id, VcDaTai.nen_tang == nen_id)
    ).all()
    return {vid for vid, tt, luc, jid in rows
            if jid != tru_job_id and (tt == XONG or (tt == DANG_TAI and _utc(luc) > moc))}


def _utc(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)      # SQLite trả datetime không múi giờ


def gianh_cho(db, owner_id: str, nen_id: str, video_id: str, job_id: str, *,
              bay_gio: datetime | None = None, tep_con=lambda key: True) -> bool:
    """GIÀNH quyền tải (owner, nền, video) cho `job_id` trước khi tải; COMMIT ngay. True ⇒ được tải.

    UNIQUE của CSDL quyết định giữa hai worker. Dòng sẵn có chỉ được giành lại khi: của chính job này (lượt thử
    lại), 'dang_tai' quá `GIANH_CHO_HET_HAN` (job chết), hoặc 'xong' mà tệp đã mất (`tep_con(tep)` False — khách
    chọn đích danh video đã tải từ lâu). Giành lại bằng UPDATE có điều kiện trên giá trị vừa đọc (so-và-đổi) nên
    hai job cùng giành lại một dòng cũ thì cũng chỉ một thắng.
    """
    from sqlalchemy import update
    from sqlalchemy.exc import IntegrityError

    from apps.video_crawler.tables import DANG_TAI, XONG, VcDaTai
    bay_gio = bay_gio or datetime.now(timezone.utc)
    try:
        db.add(VcDaTai(owner_id=owner_id, nen_tang=nen_id, video_id=video_id, job_id=job_id,
                       trang_thai=DANG_TAI, tao_luc=bay_gio, cap_nhat_luc=bay_gio))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
    cu = db.execute(select(VcDaTai).where(VcDaTai.owner_id == owner_id, VcDaTai.nen_tang == nen_id,
                                          VcDaTai.video_id == video_id)).scalar_one_or_none()
    if cu is None:                       # dòng vừa bị nhả giữa hai lệnh ⇒ thử chèn lại một lần
        return gianh_cho(db, owner_id, nen_id, video_id, job_id, bay_gio=bay_gio, tep_con=tep_con)
    duoc = (cu.job_id == job_id
            or (cu.trang_thai == DANG_TAI and _utc(cu.cap_nhat_luc) <= bay_gio - GIANH_CHO_HET_HAN)
            or (cu.trang_thai == XONG and not (cu.tep and tep_con(cu.tep))))
    if not duoc:
        db.rollback()
        return False
    doi = db.execute(update(VcDaTai).where(VcDaTai.id == cu.id, VcDaTai.job_id == cu.job_id,
                                           VcDaTai.trang_thai == cu.trang_thai,
                                           VcDaTai.cap_nhat_luc == cu.cap_nhat_luc)
                     .values(job_id=job_id, trang_thai=DANG_TAI, cap_nhat_luc=bay_gio)   # giữ `tep` cũ: nhả ⇒ về 'xong'
                     .execution_options(synchronize_session=False))
    db.commit()
    return doi.rowcount == 1


def danh_dau_xong(db, owner_id: str, job_id: str, tep_theo_id: dict[str, str]) -> None:
    """Chốt job: dòng của mục đã tải ⇒ 'xong' + storage key; dòng 'dang_tai' còn lại (mục lỗi) bị nhả. COMMIT."""
    from sqlalchemy import update

    from apps.video_crawler.tables import XONG, VcDaTai
    bay_gio = datetime.now(timezone.utc)
    for vid, tep in tep_theo_id.items():
        db.execute(update(VcDaTai).where(VcDaTai.owner_id == owner_id, VcDaTai.job_id == job_id,
                                         VcDaTai.video_id == vid)
                   .values(trang_thai=XONG, tep=tep, cap_nhat_luc=bay_gio)
                   .execution_options(synchronize_session=False))
    _nha(db, owner_id, job_id, chi_dang_tai=True)
    db.commit()


def _nha(db, owner_id: str, job_id: str, *, chi_dang_tai: bool) -> None:
    """Nhả chỗ của job: dòng giành lại từ 'xong' (còn `tep` cũ) quay về 'xong' — không quên video đã tải và thu
    tiền lại lượt sau; dòng mới thì xoá."""
    from sqlalchemy import delete, update

    from apps.video_crawler.tables import DANG_TAI, XONG, VcDaTai
    loc = [VcDaTai.owner_id == owner_id, VcDaTai.job_id == job_id]
    if chi_dang_tai:
        loc.append(VcDaTai.trang_thai == DANG_TAI)
    db.execute(update(VcDaTai).where(*loc, VcDaTai.trang_thai == DANG_TAI, VcDaTai.tep.is_not(None))
               .values(trang_thai=XONG).execution_options(synchronize_session=False))
    db.execute(delete(VcDaTai).where(*loc, VcDaTai.tep.is_(None)).execution_options(synchronize_session=False))


def nha_cho(db, owner_id: str, job_id: str) -> None:
    """Nhả mọi dòng của job này (huỷ/lỗi/hết giờ — cùng lúc với dọn storage); COMMIT."""
    _nha(db, owner_id, job_id, chi_dang_tai=False)
    db.commit()


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
        raise QuaTanSuat(_t("Bạn đang xem trước quá nhanh — đợi một phút rồi thử lại."))


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
