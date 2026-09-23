"""Palette V2 của Canvas — MỘT đường, sinh từ registry (spec §13.1, §13.4).

⛔ Không có bảng nhãn/biểu tượng/phân tầng nào trong tệp này. Mọi thứ hiển thị
   đến từ `NodeDefinition`, và `NodeDefinition` đến từ ba nguồn của §4.5.
   `/agent/api/palette` (v2, `workspace.py`) chết theo plan 01b.
"""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, router
from server.auth.session import require_login
from server.deps import get_db

from platform_core.workflow import he_kieu, nut


def _cong(cap) -> list:
    return [{"ten": ten, "kieu": c.type, "bat_buoc": bool(c.required),
             "nhieu": bool(c.multiple)} for ten, c in cap]


def sang_json(nd: nut.NodeDefinition) -> dict:
    """Bản RÚT GỌN gửi ra trình duyệt.

    ⛔ Liệt kê TƯỜNG MINH từng khoá thay vì `dataclasses.asdict`: một trường
       mới thêm vào `NodeDefinition` không được tự động chảy ra Internet.
       `mock` là một callable của app — không bao giờ ra ngoài.
    """
    return {
        "type": nd.type, "type_version": nd.type_version,
        "kind": nd.kind, "category": nd.category,
        "title": nd.title, "description": nd.description, "icon": nd.icon,
        "app_name": nd.app_name,
        "cong_vao": _cong(nd.cong_vao), "cong_ra": _cong(nd.cong_ra),
        "tham_so": nd.tham_so,
        "thi_hanh": nd.thi_hanh,
        "side_effect": nd.side_effect,
        "resource": dict(nd.resource or {}),
        "timeout_expr": nd.timeout_expr,
        "retry_mac_dinh": dict(nd.retry_mac_dinh or {}),
        "gia": nd.gia.sang_json(),
        "credential": list(nd.credential),
        "quyen": sorted(nd.quyen),
        "cho": list(nd.cho), "ma_loi": list(nd.ma_loi),
        "co_mock": nd.mock is not None,
        "publish_duoc": nd.publish_duoc,
    }


def _duoc_phep(db: Session, user) -> set:
    """Slug app người dùng này được dùng. Nền tảng KHÔNG biết tên app nào —
    nó hỏi `app_access` từng slug do `discover()` trả về."""
    from platform_core import app_access, registry
    return {item.slug for item in registry.discover()
            if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}


@router.get("/api/v3/palette")
def palette_v3(request: Request, _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    from platform_core.workflow import cong_cu

    user = _user(request)
    cho_phep = _duoc_phep(db, user)
    cc = {ten: c for ten, c in cong_cu.tat_ca().items()
          if c.app_slug in cho_phep}
    dinh_nghia = nut.tat_ca(cong_cu=cc)

    theo_nhom: dict[str, list] = {}
    for nd in dinh_nghia.values():
        theo_nhom.setdefault(nd.category, []).append(nd)
    nhom = [{"category": c,
             "nut": [sang_json(nd) for nd in
                     sorted(theo_nhom[c], key=lambda x: (x.title, x.type))]}
            for c in nut.CATEGORY if theo_nhom.get(c)]
    return JSONResponse({"phien_ban": 3, "nhom": nhom,
                         "luat_noi_day": he_kieu.xuat_luat_noi_day()})


@router.get("/api/v3/luat-noi-day")
def luat_noi_day_v3(_identity: str = Depends(require_login)):
    return JSONResponse(he_kieu.xuat_luat_noi_day())
