"""CrawlApplicationService (spec §8): validate theo registry, dựng params, nộp job, dedup, lịch sử, thống kê.

Route chỉ gọi vào đây; handler (`jobs.py`) chỉ gọi nhóm dedup (`da_tai_ids`, `gianh_cho`, `danh_dau_xong`,
`nha_cho`). Mọi truy vấn lọc theo chủ sở hữu.
"""
from __future__ import annotations

import re
import threading as _threading
import time as _time
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
        nen = nen_tang.lay_nen_bat(nen_id)
    except nen_tang.NenKhongHopLe as e:
        raise LoiDauVao(_t("Nền tảng này chưa được hỗ trợ.")) from e
    if nen.dang_phat_trien:
        # Chặn Ở CỬA VÀO, không nhận job rồi trả rỗng: đo thật 23/09, Douyin trả danh sách rỗng và khách
        # nhìn một trang trắng không hiểu vì sao (SO_LOI W5-1).
        raise LoiDauVao(_t("{ten} đang phát triển, chưa dùng được. {ly_do}")
                        .format(ten=_t(nen.ten), ly_do=_t(nen.ly_do_dpt)))
    return nen


def _kiem_url(url: str, nen, phan_giai) -> str:
    kw = {"ten_mien": nen.ten_mien}
    if phan_giai is not None:
        kw["phan_giai"] = phan_giai
    try:
        return an_toan_url.kiem(url, **kw)
    except an_toan_url.UrlKhongAnToan as e:
        raise LoiDauVao(_t("Link không hợp lệ cho {ten}.").format(ten=nen.ten)) from e


def _kiem_phien(nen, db, owner_id: str, *, cho_kho: bool = False) -> None:
    """Nền này đòi đăng nhập ⇒ khách phải có phiên riêng còn dùng được.

    `cho_kho=True` (đường tìm kênh): nền có KHO tài khoản hệ thống thì không đòi phiên riêng — `jobs._phien`
    sẽ mượn kho, đúng như job cào làm (THIET_KE_PHIEN_VA_KENH §2.2).
    """
    from apps.video_crawler import phien
    co = [p for p in phien.danh_sach(db, owner_id) if p.nen_tang == nen.id] if db is not None else []
    if not co:
        if cho_kho:
            from apps.video_crawler import kho_tai_khoan
            # Có kho là chưa đủ: kho RỖNG (hoặc mọi tài khoản tạm nghỉ/bị chặn) mà vẫn nhận thì job chạy rồi
            # hỏng và hoàn tiền — khách chờ vô ích. Hỏi luôn "còn tài khoản sống không".
            if kho_tai_khoan.nen_co_kho(nen.id) and kho_tai_khoan.con_tai_khoan_song(db, nen.id):
                return
        raise LoiDauVao(_t("Cách cào này cần đăng nhập {ten} — thêm phiên đăng nhập trước.").format(ten=nen.ten))
    if not phien.hop_le(co[0]):                     # review lần 2: khoá xoay ⇒ phiên không giải mã được
        raise LoiDauVao(_t("Phiên {ten} đã hỏng (không giải mã được) — nhập lại cookies.txt.").format(ten=nen.ten))


def _kiem_nguon(nen, che_do: str, dau_vao: str, so_luong, phan_giai, *, db=None,
                owner_id: str = "") -> tuple[str, int]:
    if che_do not in nen.che_do:
        raise LoiDauVao(_t("{ten} không hỗ trợ cách cào này.").format(ten=nen.ten))
    if che_do in nen.che_do_can_dang_nhap:
        # Kho tài khoản hệ thống dùng được ở ĐƯỜNG CÀO, không chỉ đường tìm kênh: nếu không, dán cookie vào kho
        # xong khách vẫn bị từ chối ở cửa vào và cả hạng mục kho không tới được ai (rà soát gộp W4-L11).
        _kiem_phien(nen, db, owner_id, cho_kho=True)
    dau_vao = _chuan_dau_vao(nen, che_do, dau_vao, phan_giai)
    try:
        n = int(so_luong)
    except (TypeError, ValueError) as e:
        raise LoiDauVao(_t("Số lượng không hợp lệ.")) from e
    tran = min(nen.so_luong_toi_da, SO_MUC_TOI_DA)
    if not 1 <= n <= tran:
        raise LoiDauVao(_t("Số lượng phải từ 1 đến {tran}.").format(tran=tran))
    return dau_vao, n


def _chuan_dau_vao(nen, che_do: str, dau_vao: str, phan_giai) -> str:
    """Từ khoá / link / handle khách nhập ⇒ chuỗi đã kiểm (link phải thuộc tên miền của nền, không SSRF)."""
    dau_vao = (dau_vao or "").strip()
    if not dau_vao:
        raise LoiDauVao(_t("Chưa nhập từ khoá hoặc link."))
    if len(dau_vao) > DAU_VAO_TOI_DA:
        raise LoiDauVao(_t("Nội dung nhập quá dài."))
    la_handle = che_do == "kenh" and "/" not in dau_vao and not dau_vao.lower().startswith("http")
    if che_do != "tu_khoa" and not la_handle:
        url = dau_vao if dau_vao.lower().startswith("http") else "https://" + dau_vao
        dau_vao = _kiem_url(url, nen, phan_giai)
    return dau_vao


def dung_params_kham_pha(*, owner_id: str, nen_tang: str, che_do: str, dau_vao: str, so_luong,
                         khong_trung: bool, phan_giai=None, db=None, tuy_chon: dict | None = None) -> dict:
    """`tuy_chon` = tuỳ chọn trang kênh (tab/sắp xếp/khoảng ngày/thời lượng) — kiểm lại ở đây, không tin route."""
    nen = _nen(nen_tang)
    dau_vao, n = _kiem_nguon(nen, che_do, dau_vao, so_luong, phan_giai, db=db, owner_id=owner_id)
    params = {"owner_id": owner_id, "nen_tang": nen.id, "che_do": che_do, "dau_vao": dau_vao,
              "so_luong": n, "khong_trung": bool(khong_trung)}
    tc = _kiem_tuy_chon(nen.id, tuy_chon)
    if tc:
        params["tuy_chon"] = tc
    return params


def dung_params_tai(*, owner_id: str, nen_tang: str, muc: list | None = None, nguon: dict | None = None,
                    phan_giai=None, db=None) -> dict:
    """Tải theo danh sách đã chọn ở xem trước (`muc`) HOẶC cào hết theo nguồn (`nguon`)."""
    nen = _nen(nen_tang)
    if (muc is None) == (nguon is None):
        raise LoiDauVao(_t("Cần đúng một trong hai: danh sách mục hoặc nguồn cào."))
    if nguon is not None:
        dau_vao, n = _kiem_nguon(nen, nguon.get("che_do", ""), nguon.get("dau_vao", ""),
                                 nguon.get("so_luong"), phan_giai, db=db, owner_id=owner_id)
        goc = {"che_do": nguon["che_do"], "dau_vao": dau_vao, "so_luong": n,
               "khong_trung": bool(nguon.get("khong_trung"))}
        tc = _kiem_tuy_chon(nen.id, nguon.get("tuy_chon"))
        if tc:
            goc["tuy_chon"] = tc
        return {"owner_id": owner_id, "nen_tang": nen.id, "nguon": goc}
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


# ── Tìm KÊNH theo tên + trang kênh trong app (W4-L11; THIET_KE_PHIEN_VA_KENH §3.3, §4) ────────
# Việc nhỏ (một lượt gọi nền, vài giây) ⇒ chạy trong request như proxy ảnh bìa (`anh_bia.py`), KHÔNG
# qua hàng đợi job: khách đang đứng trước màn hình chọn kênh, lượt tìm không tiêu credit và không tải gì.

#: Tên chế độ trên GIAO DIỆN — cố ý KHÔNG nằm trong `base.CHE_DO` (nó không phải một cách cào: kết quả là
#: thẻ kênh, không phải video). Gửi nhầm xuống `dung_params_*` sẽ bị từ chối như mọi chế độ lạ.
CHE_DO_TIM_KENH = "tim_kenh"
#: Số thẻ kênh mỗi lượt tìm (mặc định / trần).
SO_KENH_MAC_DINH = 8
SO_KENH_TOI_DA = 20
#: Trần lượt TÌM KÊNH mỗi phút mỗi khách — cùng lý do `KHAM_PHA_MOI_PHUT` (tìm dồn dập ⇒ nền chặn IP máy A).
TIM_KENH_MOI_PHUT = 10
#: Cách sắp xếp video trong trang kênh. "mới nhất" là mặc định của mọi nền (THIET_KE §3.3).
SAP_XEP_KENH: tuple[str, ...] = ("moi_nhat", "pho_bien")
#: Bậc thời lượng ⇒ (từ giây, đến giây | None). Ranh giới 4 phút / 20 phút theo bộ lọc của chính YouTube.
THOI_LUONG_KENH: dict[str, tuple[int, int | None]] = {
    "ngan": (0, 240), "vua": (240, 1200), "dai": (1200, None),
}
#: Vé ảnh đại diện: ký bằng `LTT_SESSION_SECRET` (cùng cơ chế `platform_core/tokens.py`), có hạn, gắn CHỦ.
#: Nhờ vé, URL CDN không bao giờ xuất hiện trong HTML và khách không tự gửi URL cho proxy được.
_SALT_ANH_KENH = "ltt-vc-anh-kenh-v1"
TTL_ANH_KENH = 1800

_LUOT_TIM: dict[str, list[float]] = {}
_LUOT_TIM_KHOA = _threading.Lock()
#: Chặn sổ tần suất phình vô hạn (một tiến trình web sống nhiều ngày).
_LUOT_TIM_TOI_DA = 2000


def kiem_tan_suat_tim_kenh(owner_id: str, *, bay_gio: float | None = None) -> None:
    """Ghi một lượt tìm kênh cho `owner_id`; quá `TIM_KENH_MOI_PHUT` trong 60 s ⇒ `QuaTanSuat`.

    Đếm trong bộ nhớ tiến trình (lượt tìm không tạo job nên không có dấu vết trong CSDL để đếm) — nhiều
    tiến trình web thì trần nới ra theo số tiến trình; đủ cho mục đích: chặn vòng lặp tự động, không phải
    kế toán. Trần cứng của tiền vẫn nằm ở tầng job (`kiem_tan_suat`, `kiem_tran_tai`).
    """
    luc = _time.monotonic() if bay_gio is None else bay_gio
    with _LUOT_TIM_KHOA:
        ds = [t for t in _LUOT_TIM.get(owner_id, ()) if luc - t < 60]
        if len(ds) >= TIM_KENH_MOI_PHUT:
            _LUOT_TIM[owner_id] = ds
            raise QuaTanSuat(_t("Bạn đang tìm kênh quá nhanh — đợi một phút rồi thử lại."))
        ds.append(luc)
        _LUOT_TIM[owner_id] = ds
        if len(_LUOT_TIM) > _LUOT_TIM_TOI_DA:
            for k in [k for k, v in _LUOT_TIM.items() if not v or luc - v[-1] >= 60]:
                _LUOT_TIM.pop(k, None)


def _adapter_cua(nen_id: str):
    from apps.video_crawler import adapters
    return adapters.tao(nen_id)


def nen_tim_kenh_duoc(nen_id: str, *, tao_adapter=None) -> bool:
    """Nền này TÌM KÊNH theo tên được không — giao diện dùng để hiện/giấu chế độ "Tìm kênh".

    Một nguồn: `nen_tang.co_tim_kenh` (hỏi thẳng lớp adapter, kể cả điều kiện `ie_key_kenh` của họ yt-dlp).
    """
    from apps.video_crawler import nen_tang as _nt
    return _nt.co_tim_kenh(nen_id)


def _mo_phien(adapter, owner_id: str, nen_id: str):
    """Ngữ cảnh phiên đăng nhập cho một lượt tìm — DÙNG LẠI đúng đường của job (`jobs._phien`):
    phiên riêng của khách > mượn kho tài khoản hệ thống > ẩn danh, kèm nhả chỗ + chấm điểm tài khoản."""
    from apps.video_crawler.jobs import _phien
    return _phien(adapter, owner_id, nen_id)


def tim_kenh(db, *, owner_id: str, nen_tang: str, tu_khoa: str, so_luong=SO_KENH_MAC_DINH,
             tao_adapter=None, mo_phien=None) -> list:
    """TÊN kênh ⇒ danh sách `KenhItem` để khách chọn. Mọi lỗi của nền thành câu đọc được (`LoiDauVao`).

    Không tìm thấy ai ⇒ danh sách RỖNG (không phải lỗi). Nền chưa làm được ⇒ câu "hãy dán link kênh".
    """
    from apps.video_crawler.adapters.base import LoiCao, YeuCauTimKenh, loi_chua_ho_tro_tim_kenh
    nen = _nen(nen_tang)
    if not nen_tim_kenh_duoc(nen.id, tao_adapter=tao_adapter):
        raise LoiDauVao(_t(loi_chua_ho_tro_tim_kenh().thong_diep))
    tu_khoa = (tu_khoa or "").strip()
    if not tu_khoa:
        raise LoiDauVao(_t("Chưa nhập tên kênh."))
    if len(tu_khoa) > DAU_VAO_TOI_DA:
        raise LoiDauVao(_t("Nội dung nhập quá dài."))
    try:
        n = int(so_luong)
    except (TypeError, ValueError) as e:
        raise LoiDauVao(_t("Số lượng không hợp lệ.")) from e
    if not 1 <= n <= SO_KENH_TOI_DA:
        raise LoiDauVao(_t("Số lượng phải từ 1 đến {tran}.").format(tran=SO_KENH_TOI_DA))
    # Tìm kênh đi cùng cửa đăng nhập với cách cào "kenh": nền nào đòi phiên cho kênh thì cũng đòi ở đây.
    if "kenh" in nen.che_do_can_dang_nhap:
        _kiem_phien(nen, db, owner_id, cho_kho=True)
    kiem_tan_suat_tim_kenh(owner_id)
    adapter = (tao_adapter or _adapter_cua)(nen.id)
    yeu_cau = YeuCauTimKenh(nen_tang=nen.id, tu_khoa=tu_khoa, so_luong=n)
    from platform_core.jobs import DangBan, LoiNguoiGoi
    try:
        with (mo_phien or _mo_phien)(adapter, owner_id, nen.id):
            ra = adapter.tim_kenh(yeu_cau, bao_tien_do=lambda phan_tram, thong_diep="": None)
    except LoiCao as e:
        raise LoiDauVao(_t(e.thong_diep)) from e
    except DangBan as e:
        raise LoiDauVao(_t("Tài khoản hệ thống của {ten} đang bận — thử lại sau ít phút.")
                        .format(ten=nen.ten)) from e
    except LoiNguoiGoi as e:
        raise LoiDauVao(str(e)) from e
    return list(ra or [])[:n]


def tab_kenh(nen_id: str, *, tao_adapter=None) -> tuple[tuple[str, str], ...]:
    """Các tab trang kênh mà ADAPTER khai (`TAB_KENH` = ((id, nhãn), …)) — giao diện không khai tay.

    Adapter chưa khai ⇒ `()` ⇒ giao diện không hiện ô chọn tab (thà thiếu một ô còn hơn hứa một tab
    mà đường cào không biết dùng).
    """
    from apps.video_crawler import nen_tang as _nt
    try:
        adapter = (tao_adapter or _adapter_cua)(nen_id)
    except (_nt.NenKhongHopLe, ImportError, LookupError, RuntimeError):
        return ()
    ra = []
    for mot in getattr(adapter, "TAB_KENH", ()) or ():
        try:
            ma, nhan = mot
        except (TypeError, ValueError):
            continue
        if isinstance(ma, str) and ma:
            ra.append((ma, str(nhan or ma)))
    return tuple(ra)


def _ngay(s: str, ten: str) -> str:
    from datetime import date
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError as e:
        raise LoiDauVao(_t("{ten} không hợp lệ (dùng dạng 2026-01-31).").format(ten=ten)) from e


def chuan_tuy_chon_kenh(nen_id: str, *, tab: str = "", sap_xep: str = "", tu_ngay: str = "",
                        den_ngay: str = "", thoi_luong: str = "", tao_adapter=None) -> dict:
    """Tuỳ chọn trang kênh từ form ⇒ dict đã kiểm (chỉ giữ khoá có giá trị). Giá trị lạ ⇒ `LoiDauVao`."""
    ra: dict[str, str] = {}
    tab = (tab or "").strip()
    if tab:
        if tab not in {ma for ma, _nhan in tab_kenh(nen_id, tao_adapter=tao_adapter)}:
            raise LoiDauVao(_t("Nền tảng này không có mục đó trên trang kênh."))
        ra["tab"] = tab
    sap_xep = (sap_xep or "").strip()
    if sap_xep:
        if sap_xep not in SAP_XEP_KENH:
            raise LoiDauVao(_t("Cách sắp xếp không hợp lệ."))
        ra["sap_xep"] = sap_xep
    tu_ngay, den_ngay = (tu_ngay or "").strip(), (den_ngay or "").strip()
    if tu_ngay:
        ra["tu_ngay"] = _ngay(tu_ngay, _t("Từ ngày"))
    if den_ngay:
        ra["den_ngay"] = _ngay(den_ngay, _t("Đến ngày"))
    if "tu_ngay" in ra and "den_ngay" in ra and ra["tu_ngay"] > ra["den_ngay"]:
        raise LoiDauVao(_t("Ngày bắt đầu phải trước ngày kết thúc."))
    thoi_luong = (thoi_luong or "").strip()
    if thoi_luong:
        if thoi_luong not in THOI_LUONG_KENH:
            raise LoiDauVao(_t("Khoảng thời lượng không hợp lệ."))
        ra["thoi_luong"] = thoi_luong
    return ra


def _kiem_tuy_chon(nen_id: str, tuy_chon) -> dict:
    if not tuy_chon:
        return {}
    if not isinstance(tuy_chon, dict):
        raise LoiDauVao(_t("Tuỳ chọn trang kênh không hợp lệ."))
    try:
        return chuan_tuy_chon_kenh(nen_id, **{k: str(v or "") for k, v in tuy_chon.items()})
    except TypeError as e:
        raise LoiDauVao(_t("Tuỳ chọn trang kênh không hợp lệ.")) from e


def loc_muc(muc: list, tuy_chon: dict | None) -> list:
    """Lọc danh sách mục xem trước theo bậc thời lượng khách đã chọn.

    Đây là bộ lọc THẬT đang chạy hôm nay (lọc lúc hiển thị). Lọc TẠI NGUỒN (khoảng ngày, sắp xếp, tab)
    cần adapter đọc `params["tuy_chon"]` — xem báo cáo làn W4-L11, mục "cần điều phối".
    """
    bac = (tuy_chon or {}).get("thoi_luong") if isinstance(tuy_chon, dict) else None
    khoang = THOI_LUONG_KENH.get(bac or "")
    if khoang is None:
        return list(muc or [])
    tu, den = khoang
    ra = []
    for m in muc or []:
        tl = _thoi_luong((m or {}).get("thoi_luong_s"))
        if tl is not None and tl >= tu and (den is None or tl < den):
            ra.append(m)
    return ra


def _serializer():
    import os

    from itsdangerous import URLSafeTimedSerializer
    bi_mat = (os.environ.get("LTT_SESSION_SECRET") or "").strip()
    if not bi_mat:
        raise RuntimeError("Chua co LTT_SESSION_SECRET — khong ky duoc ve anh kenh.")
    return URLSafeTimedSerializer(bi_mat)


def ky_anh_kenh(owner_id: str, nen_tang: str, url: str) -> str:
    """Vé một chiều cho ảnh đại diện: (chủ, nền, URL CDN) đã ký. Khách chỉ cầm vé, không cầm URL."""
    return _serializer().dumps([owner_id, nen_tang, url], salt=_SALT_ANH_KENH)


def doc_anh_kenh(ve: str, owner_id: str, *, max_age: int = TTL_ANH_KENH) -> tuple[str, str] | None:
    """(nền, URL) của vé còn hạn và ĐÚNG chủ; vé hỏng/hết hạn/của người khác ⇒ None (route trả 404)."""
    if not ve:
        return None
    from itsdangerous import BadSignature, SignatureExpired
    try:
        du_lieu = _serializer().loads(ve, salt=_SALT_ANH_KENH, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    if (not isinstance(du_lieu, list)) or len(du_lieu) != 3 or du_lieu[0] != owner_id:
        return None
    return str(du_lieu[1]), str(du_lieu[2])


def chuan_link_kenh(*, nen_tang: str, dau_vao: str, phan_giai=None) -> str:
    """Link (hoặc handle) trang kênh khách chọn ⇒ chuỗi đã kiểm — CÙNG luật với cách cào "kenh".

    Dùng ở bước "mở trang kênh trong app": chỉ kiểm đầu vào, chưa hỏi phiên đăng nhập (cửa phiên vẫn
    nằm nguyên ở `dung_params_kham_pha`/`dung_params_tai` khi khách bấm Xem trước / Cào hết).
    """
    nen = _nen(nen_tang)
    if "kenh" not in nen.che_do:
        raise LoiDauVao(_t("{ten} không hỗ trợ cách cào này.").format(ten=nen.ten))
    return _chuan_dau_vao(nen, "kenh", dau_vao, phan_giai)


def url_mo_nen(nen_tang: str, tu_khoa: str = "", *, tao_adapter=None) -> str:
    """URL "Mở trên nền tảng" (tab mới): trang tìm kênh của nền khi ADAPTER dựng được, nếu không thì
    trang chủ nền lấy từ registry. Không có bảng URL khai tay ở tầng giao diện."""
    nen = _nen(nen_tang)
    tu_khoa = (tu_khoa or "").strip()[:DAU_VAO_TOI_DA]
    if tu_khoa:
        from apps.video_crawler import nen_tang as _nt      # tham số `nen_tang: str` che mất module cùng tên
        try:
            ham = getattr((tao_adapter or _adapter_cua)(nen.id), "url_tim_kenh", None)
            url = ham(tu_khoa) if callable(ham) else ""
            if isinstance(url, str) and url.startswith("https://"):
                return url
        except (_nt.NenKhongHopLe, ImportError, LookupError, NotImplementedError, ValueError):
            pass               # adapter chưa dựng được URL tìm ⇒ về trang chủ nền, không làm hỏng trang
    return "https://" + nen.ten_mien[0] if nen.ten_mien else ""
