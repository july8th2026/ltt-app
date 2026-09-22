"""Trang vận hành (operator-only) của video_crawler: sức khoẻ theo nền 24 giờ (PLAN_MVP §C dòng L4-b).

Router RIÊNG, không tự viết prefix (giống `routes.py`). ⚠️ Chưa được nền tảng gắn: `mount_all`
(`platform_core/registry.py`) chỉ `include_router` MỘT router mỗi app — router chính ở `routes.py`
(lane L1). Điều phối cần thêm một dòng khi gộp:

    router.include_router(routes_van_hanh.router)   # trong apps/video_crawler/routes.py

Sau dòng đó, trang hiện ở `{route_prefix}/van-hanh` = `/video-crawler/van-hanh`.

Cổng cờ: bản sao 3 dòng của `_cong_co`/`CO_MO` ở `routes.py` — KHÔNG import từ đó, vì `routes.py` sẽ
là nơi `include_router` module này (import ngược lại sẽ vòng). Hai hằng `CO_MO` phải LUÔN bằng nhau;
`test_1924` khoá điều đó bằng cách so `routes_van_hanh.CO_MO == routes.CO_MO` khi cả hai cùng nạp được.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.datastructures import UploadFile

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

from apps.video_crawler import kho_tai_khoan, nen_tang, phien, suc_khoe
from apps.video_crawler.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.deps import audit_operator_action, get_db, require_operator
from server.templating import templates

router = APIRouter(tags=["video_crawler"])

#: Phải khớp `routes.py:CO_MO`.
CO_MO = "LTT_VIDEO_CRAWLER"

#: Cửa sổ đọc sức khoẻ — brief L4-a "24 h".
CUA_SO_GIO = 24


def _cong_co() -> None:
    if str(os.environ.get(CO_MO, "")).strip() != "1":
        raise HTTPException(status_code=404)


@router.get("/van-hanh", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def van_hanh(request: Request, _operator: str = Depends(require_operator), db=Depends(get_db)):
    """Chỉ operator (`require_operator`): 403 cho khách thường đã đăng nhập, 303 → /login nếu chưa."""
    thong_ke = suc_khoe.thong_ke(db, gio=CUA_SO_GIO)
    return templates.TemplateResponse(request, "vc_van_hanh.html", {
        "app": MANIFEST, "nav": MANIFEST.slug,
        "cua_so_gio": CUA_SO_GIO,
        "thong_ke": thong_ke,
        "co_nen_khuyen_nghi_tat": any(v["khuyen_nghi_tat"] for v in thong_ke.values()),
    })


# ── Kho tài khoản hệ thống (W4-L9b) ───────────────────────────────────────────
# Trang operator quản trị `kho_tai_khoan.py` (lane L9, chỉ ĐỌC — không sửa module đó ở đây).
# ⛔ Giá trị cookie không bao giờ vào context template, log nhật ký hay thông báo lỗi: mọi hàm dưới đây
# chỉ truyền id/nhãn/mã lỗi/số liệu — `kho_tai_khoan.cookies_txt_cua` không được gọi từ module này.

_DUONG_TAI_KHOAN = f"{MANIFEST.route_prefix}/van-hanh/tai-khoan"

#: Nhãn hiển thị theo trạng thái (`tables.py`: SONG/HET_HAN/BI_CHAN/TAM_NGHI).
_NHAN_TRANG_THAI = {
    kho_tai_khoan.SONG: N_("Đang hoạt động"),
    kho_tai_khoan.HET_HAN: N_("Hết hạn"),
    kho_tai_khoan.BI_CHAN: N_("Bị chặn"),
    kho_tai_khoan.TAM_NGHI: N_("Tạm nghỉ"),
}


def _utc(luc: datetime | None) -> datetime | None:
    if luc is None:
        return None
    return luc if luc.tzinfo else luc.replace(tzinfo=timezone.utc)


def _hang_hien_thi(tk, bay_gio: datetime) -> dict:
    """Dữ liệu MỘT dòng bảng — không có trường nào chứa cookie."""
    han = _utc(tk.han)
    con_lai_ngay = None if han is None else max(0, int((han - bay_gio).total_seconds() // 86400))
    moc = _utc(tk.cua_so_luc)
    luot = 0 if moc is None or bay_gio - moc >= timedelta(hours=1) else int(tk.so_luot_trong_gio or 0)
    try:
        ten_nen = nen_tang.lay(tk.nen_tang).ten
    except nen_tang.NenKhongHopLe:
        ten_nen = tk.nen_tang
    return {
        "id": tk.id, "nen_tang": tk.nen_tang, "ten_nen": ten_nen, "nhan": tk.nhan,
        "trang_thai": tk.trang_thai,
        "trang_thai_nhan": _t(_NHAN_TRANG_THAI.get(tk.trang_thai, tk.trang_thai)),
        "diem": tk.diem,
        "con_lai_ngay": con_lai_ngay,
        "han_qua": han is not None and han <= bay_gio,
        "luot_trong_gio": luot,
        "loi_gan_nhat": kho_tai_khoan.ma_an_toan(tk.loi_gan_nhat) if tk.loi_gan_nhat else "",
        "dung_gan_nhat": tk.dung_gan_nhat,
    }


def _trang_tai_khoan(request: Request, db, *, loi: str | None = None, ma: int = 200) -> HTMLResponse:
    bay_gio = datetime.now(timezone.utc)
    hang = [_hang_hien_thi(tk, bay_gio) for tk in kho_tai_khoan.danh_sach(db)]
    nen_chon = [nen_tang.lay(n) for n in kho_tai_khoan.NEN_CO_KHO]
    return templates.TemplateResponse(request, "vc_tai_khoan.html", {
        "app": MANIFEST, "nav": MANIFEST.slug,
        "duong": _DUONG_TAI_KHOAN,
        "csrf_token": issue_csrf_token(request),
        "hang": hang, "nen_chon": nen_chon, "loi": loi,
    }, status_code=ma)


@router.get("/van-hanh/tai-khoan", response_class=HTMLResponse, dependencies=[Depends(_cong_co)])
def trang_tai_khoan(request: Request, _operator: str = Depends(require_operator), db=Depends(get_db)):
    return _trang_tai_khoan(request, db)


@router.post("/van-hanh/tai-khoan", dependencies=[Depends(_cong_co)])
async def them_tai_khoan(request: Request, _operator: str = Depends(require_operator), db=Depends(get_db)):
    form = await request.form()
    if not verify_csrf_token(request, str(form.get("csrf_token") or "")):
        return _trang_tai_khoan(request, db, loi=_t("Phiên đã hết hạn — tải lại trang."), ma=400)
    noi_dung = form.get("cookies_txt") or ""
    tep = form.get("cookies_tep")
    if isinstance(tep, UploadFile):
        du_lieu = await tep.read(phien.TOI_DA_BYTE + 1)
        if du_lieu:
            noi_dung = du_lieu.decode("utf-8", errors="replace")
    nen_id = str(form.get("nen_tang") or "")
    nhan = str(form.get("nhan") or "")
    try:
        tk = kho_tai_khoan.them(db, nen_tang=nen_id, nhan=nhan, cookies_txt=str(noi_dung))
    except (kho_tai_khoan.KhoKhongHopLe, phien.PhienKhongHopLe) as e:
        db.rollback()
        return _trang_tai_khoan(request, db, loi=str(e), ma=400)
    audit_operator_action(db, request, "vc_kho_them", tk.id, f"nen={nen_id}")
    return RedirectResponse(_DUONG_TAI_KHOAN, status_code=303)


@router.post("/van-hanh/tai-khoan/{tai_khoan_id}/trang-thai", dependencies=[Depends(_cong_co)])
def doi_trang_thai_tai_khoan(request: Request, tai_khoan_id: str,
                             _operator: str = Depends(require_operator), db=Depends(get_db),
                             trang_thai: str = Form(""), csrf_token: str = Form("")):
    if not verify_csrf_token(request, csrf_token):
        return _trang_tai_khoan(request, db, loi=_t("Phiên đã hết hạn — tải lại trang."), ma=400)
    try:
        kho_tai_khoan.doi_trang_thai(db, tai_khoan_id, trang_thai)
    except kho_tai_khoan.KhoKhongHopLe as e:
        db.rollback()
        return _trang_tai_khoan(request, db, loi=str(e), ma=400)
    audit_operator_action(db, request, "vc_kho_trang_thai", tai_khoan_id, trang_thai)
    return RedirectResponse(_DUONG_TAI_KHOAN, status_code=303)


@router.post("/van-hanh/tai-khoan/{tai_khoan_id}/xoa", dependencies=[Depends(_cong_co)])
def xoa_tai_khoan(request: Request, tai_khoan_id: str, _operator: str = Depends(require_operator),
                  db=Depends(get_db), csrf_token: str = Form("")):
    if not verify_csrf_token(request, csrf_token):
        return _trang_tai_khoan(request, db, loi=_t("Phiên đã hết hạn — tải lại trang."), ma=400)
    kho_tai_khoan.xoa(db, tai_khoan_id)
    audit_operator_action(db, request, "vc_kho_xoa", tai_khoan_id)
    return RedirectResponse(_DUONG_TAI_KHOAN, status_code=303)
