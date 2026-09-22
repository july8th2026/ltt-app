"""HTTP của video_crawler — CHỈ đọc request, kiểm quyền/CSRF, gọi `features`, dựng phản hồi (AGENTS §8.1).

Router không tự viết prefix; nền tảng gắn `/video-crawler` từ manifest.
Mọi route qua `_cong_co` TRƯỚC `require_login`: cờ tắt ⇒ 404 ngay cả khi chưa đăng nhập (tiền lệ
`apps/auto_scan_video/routes.py:_cong_co`), vì `enabled=False` không tháo router (spec §26).
Theo dõi tiến độ, huỷ và tải tệp dùng trang job có sẵn của nền tảng (`/jobs/{id}`), đã kiểm chủ sở hữu.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from apps.video_crawler import features, nen_tang, phien
from apps.video_crawler.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["video_crawler"])

CO_MO = "LTT_VIDEO_CRAWLER"


def _cong_co() -> None:
    if str(os.environ.get(CO_MO, "")).strip() != "1":
        raise HTTPException(status_code=404)


def _la_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _nguoi(request: Request):
    u = user_hien_tai(request)
    if u is None:
        raise features.LoiDauVao("Cần đăng nhập bằng tài khoản người dùng (không phải quản trị nội bộ).")
    return u


def _trang(request: Request, user: str, db, *, loi: str = "", ma: int = 200) -> HTMLResponse:
    u = user_hien_tai(request)
    return templates.TemplateResponse(request, "video_crawler.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "cac_nen": nen_tang.cac_nen_bat(),
        "nen_dang_nhap": [n for n in nen_tang.cac_nen_bat() if n.cookie_dang_nhap],
        "phien_cua_toi": {p.nen_tang: p for p in phien.danh_sach(db, u.id)} if u else {},
        "thong_ke": features.thong_ke(db, u.id) if u else {},
        "lich_su": features.lich_su(db, u.id, gioi_han=20) if u else [],
        "loi": loi,
    }, status_code=ma)


def _loi_form(request: Request, user: str, db, thong_diep: str, ma: int = 400) -> HTMLResponse:
    if _la_htmx(request):
        # htmx 2 KHÔNG swap phản hồi 4xx ⇒ trả 200 để khách thấy lỗi (review MAJOR 7). Mã thật ở header.
        return templates.TemplateResponse(request, "vc_thong_bao.html", {"loi": thong_diep}, status_code=200,
                                          headers={"X-LTT-Ma-Loi": str(ma)})
    return _trang(request, user, db, loi=thong_diep, ma=ma)


def _ve_hang_doi(request: Request) -> Response:
    dich = f"{MANIFEST.route_prefix}#hang-doi"
    if _la_htmx(request):
        return Response(status_code=204, headers={"HX-Redirect": dich})
    return RedirectResponse(dich, status_code=303)


@router.get("", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def trang(request: Request, user: str = Depends(require_login), db=Depends(get_db)):
    return _trang(request, user, db)


@router.post("/kham-pha", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def kham_pha(request: Request, nen_tang_id: str = Form("", alias="nen_tang"), che_do: str = Form(""),
             dau_vao: str = Form(""), so_luong: str = Form("10"), khong_trung: str = Form(""),
             csrf_token: str = Form(""), user: str = Depends(require_login), db=Depends(get_db)):
    from platform_core import credit
    from platform_core.registry import RegistryError
    if not verify_csrf_token(request, csrf_token):
        return _loi_form(request, user, db, "Phiên đã hết hạn — tải lại trang.")
    try:
        u = _nguoi(request)
        features.kiem_tan_suat(db, u.id)
        params = features.dung_params_kham_pha(owner_id=u.id, nen_tang=nen_tang_id, che_do=che_do,
                                               dau_vao=dau_vao, so_luong=so_luong,
                                               khong_trung=khong_trung == "1", db=db)
        job = features.nop(db, owner_id=u.id, job_type=features.JOB_KHAM_PHA, params=params)
        db.commit()
    except features.QuaTanSuat as e:
        db.rollback()
        return _loi_form(request, user, db, str(e), ma=429)
    except (features.LoiDauVao, credit.ThieuCreditError, RegistryError) as e:
        db.rollback()
        return _loi_form(request, user, db, str(e))
    return _ket_qua(request, db, u.id, job.id)


def _ket_qua(request: Request, db, owner_id: str, job_id: str) -> HTMLResponse:
    job = features.job_cua(db, owner_id, job_id, job_type=features.JOB_KHAM_PHA)
    if job is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "vc_ket_qua.html", {
        "job": job, "app": MANIFEST, "csrf_token": issue_csrf_token(request),
        "muc": (job.result or {}).get("muc") or [],
        "bo_qua_trung": (job.result or {}).get("bo_qua_trung") or 0,
    })


@router.get("/kham-pha/{job_id}", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def ket_qua_kham_pha(request: Request, job_id: str, user: str = Depends(require_login), db=Depends(get_db)):
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=404)
    return _ket_qua(request, db, u.id, job_id)


@router.post("/tai", dependencies=[Depends(_cong_co)])
async def tai(request: Request, user: str = Depends(require_login), db=Depends(get_db)):
    """Hai nguồn: id đã tick trong một lần xem trước (`xem_truoc` + `muc`) HOẶC nguồn cào hết.

    Mục tải lấy từ kết quả xem trước của CHÍNH người dùng; không tin url/tiêu đề trong form (review BLOCKER).
    """
    from platform_core import credit
    from platform_core.registry import RegistryError
    form = await request.form()
    if not verify_csrf_token(request, str(form.get("csrf_token") or "")):
        return _loi_form(request, user, db, "Phiên đã hết hạn — tải lại trang.")
    try:
        u = _nguoi(request)
        nen_id = str(form.get("nen_tang") or "")
        ids = [str(i) for i in form.getlist("muc")]
        xem_truoc = str(form.get("xem_truoc") or "")
        if xem_truoc or ids:
            params = features.dung_params_tai_tu_xem_truoc(db, owner_id=u.id, kham_pha_id=xem_truoc, ids=ids)
        else:
            params = features.dung_params_tai(owner_id=u.id, nen_tang=nen_id, nguon={
                "che_do": str(form.get("che_do") or ""), "dau_vao": str(form.get("dau_vao") or ""),
                "so_luong": form.get("so_luong"), "khong_trung": form.get("khong_trung") == "1"}, db=db)
        features.nop(db, owner_id=u.id, job_type=features.JOB_TAI, params=params)
        db.commit()
    except (features.LoiDauVao, credit.ThieuCreditError, RegistryError) as e:
        db.rollback()
        return _loi_form(request, user, db, str(e))
    return _ve_hang_doi(request)


@router.get("/hang-doi", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def hang_doi(request: Request, user: str = Depends(require_login), db=Depends(get_db)):
    u = user_hien_tai(request)
    return templates.TemplateResponse(request, "vc_hang_doi.html", {
        "lich_su": features.lich_su(db, u.id, gioi_han=20) if u else [],
        "thong_ke": features.thong_ke(db, u.id) if u else {}, "oob": True, "app": MANIFEST,
    })


# ── Phiên đăng nhập nền tảng (spec §16) ──────────────────────────────────────
# Giá trị cookie KHÔNG bao giờ quay lại trình duyệt: trang chỉ hiện trạng thái (số cookie, hạn, lúc cập nhật).

@router.post("/phien", dependencies=[Depends(_cong_co)])
async def luu_phien(request: Request, user: str = Depends(require_login), db=Depends(get_db)):
    form = await request.form()
    if not verify_csrf_token(request, str(form.get("csrf_token") or "")):
        return _loi_form(request, user, db, "Phiên đã hết hạn — tải lại trang.")
    noi_dung = form.get("cookies_txt") or ""
    tep = form.get("cookies_tep")
    if hasattr(tep, "read"):
        du_lieu = await tep.read(phien.TOI_DA_BYTE + 1)
        if du_lieu:
            noi_dung = du_lieu.decode("utf-8", errors="replace")
    try:
        u = _nguoi(request)
        phien.luu(db, owner_id=u.id, nen_tang=str(form.get("nen_tang") or ""), cookies_txt=str(noi_dung))
        db.commit()
    except (phien.PhienKhongHopLe, features.LoiDauVao) as e:
        db.rollback()
        return _loi_form(request, user, db, str(e))
    return _ve_trang(request, "#phien")


@router.post("/phien/xoa", dependencies=[Depends(_cong_co)])
def xoa_phien(request: Request, nen_tang_id: str = Form("", alias="nen_tang"), csrf_token: str = Form(""),
              user: str = Depends(require_login), db=Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return _loi_form(request, user, db, "Phiên đã hết hạn — tải lại trang.")
    u = user_hien_tai(request)
    if u is not None:
        phien.xoa(db, owner_id=u.id, nen_tang=nen_tang_id)
        db.commit()
    return _ve_trang(request, "#phien")


def _ve_trang(request: Request, neo: str) -> Response:
    dich = f"{MANIFEST.route_prefix}{neo}"
    if _la_htmx(request):
        return Response(status_code=204, headers={"HX-Redirect": dich})
    return RedirectResponse(dich, status_code=303)


@router.get("/anh-bia/{job_id}/{chi_so}", dependencies=[Depends(_cong_co)])
def anh_bia_xem_truoc(request: Request, job_id: str, chi_so: int, user: str = Depends(require_login),
                      db=Depends(get_db)):
    """Ảnh bìa của mục trong kết quả xem trước CỦA CHÍNH người dùng (SO_LOI L10). Không có ⇒ 404."""
    from apps.video_crawler import anh_bia
    u = user_hien_tai(request)
    tim = anh_bia.url_cua(db, owner_id=u.id, job_id=job_id, chi_so=chi_so) if u else None
    if tim is None:
        raise HTTPException(status_code=404)
    try:
        du_lieu, loai = anh_bia.tai(tim[1], nen_tang=tim[0])
    except anh_bia.AnhKhongHopLe:
        raise HTTPException(status_code=404) from None
    return Response(du_lieu, media_type=loai, headers={"X-Content-Type-Options": "nosniff"})
