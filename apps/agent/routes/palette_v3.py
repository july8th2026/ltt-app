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


#: Khoá của `resource` được phép ra trình duyệt.
#:
#: 🔴 `registry.RESOURCE_KEYS` có bốn khoá; ba khoá kia (`vram_min_mb`,
#:    `slots`, `est_duration_s`) là **sức chứa hạ tầng** — chúng nói cho MỌI
#:    tài khoản đăng nhập biết ta có bao nhiêu VRAM và mỗi card chạy được mấy
#:    suất. Không bên tiêu thụ nào cần: `frontend/agent-canvas/src/` (palette +
#:    NodeRenderer) không nhắc tới `resource` một lần nào.
#: ⭐ `class` thì cần thật, và chỉ nó: đó là khoá PHÂN LOẠI node
#:    (`nut.RESOURCE_CLASS` = cpu|gpu|api), thứ Canvas dùng để gắn nhãn/lọc.
#: ⚠️ Thêm khoá vào đây chỉ khi chỉ ra được nơi trình duyệt ĐỌC nó.
RESOURCE_CONG_KHAI = ("class",)


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
        "resource": {k: v for k, v in (nd.resource or {}).items()
                     if k in RESOURCE_CONG_KHAI},
        "timeout_expr": nd.timeout_expr,
        "retry_mac_dinh": dict(nd.retry_mac_dinh or {}),
        "gia": nd.gia.sang_json(),
        "credential": list(nd.credential),
        "quyen": sorted(nd.quyen),
        "cho": list(nd.cho), "ma_loi": list(nd.ma_loi),
        "co_mock": nd.mock is not None,
        "publish_duoc": nd.publish_duoc,
    }


def _duoc_phep(db: Session, user, nap: list) -> set:
    """Slug app người dùng này được dùng. Nền tảng KHÔNG biết tên app nào —
    nó hỏi `app_access` từng slug do `discover()` trả về."""
    from platform_core import app_access
    return {item.slug for item in nap
            if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}


def _giai_tuy_chon_dong(db: Session, user, cc: dict, nap: list) -> dict:
    """Giải enum ĐỘNG trước khi `luoc_do` dịch sang JSON Schema.

    🔴 VÌ SAO. `ToolSpec.params_schema` khai `voice_id` là `string` + một tham
       chiếu `tuy_chon_dong` — danh sách thật chỉ có sau khi hỏi CSDL với
       `user_id`. Không gọi bước này thì `app.speech.ltt.voice_id` ra
       `{"type": "string", "maxLength": 40}`: một ô chữ tự do, đúng cái khe
       GENERIC_GAP D10 sinh ra để đóng (`docs/CHATLTT/reports/02_runtime_noi_bo.md`).
       Đường v2 giải ở `apps/agent/routes/_shared.py:295`; v3 phải giải ở đây.

    ⛔ Danh sách này là **gợi ý cho giao diện**, không phải thẩm quyền: sở hữu
       giọng vẫn do app kiểm lúc thi hành (`ltt_voice.features.giai_giong`),
       vì `tuy_chon_voice_id` cố ý bỏ kho dùng chung.
    """
    from dataclasses import replace

    from platform_core.agent.tools import resolve_params_schema

    uid = str(getattr(user, "id", "") or "")
    return {ten: replace(c, params_schema=resolve_params_schema(
        ten, apps=nap, db=db, user_id=uid)) for ten, c in cc.items()}


@router.get("/api/v3/palette")
def palette_v3(request: Request, _identity: str = Depends(require_login),
               db: Session = Depends(get_db)):
    from platform_core import registry
    from platform_core.workflow import cong_cu

    user = _user(request)
    nap = registry.discover()
    cho_phep = _duoc_phep(db, user, nap)
    # ⛔ `customer_visible` KHÔNG phải chuyện quyền app. Đó là cửa app tự đóng
    #    TAY vì tool chưa nghiệm thu E2E (`apps/audio_pause/manifest.py:73-87`)
    #    — `discover_tools()` vẫn trả nó ra cho Public API và worker, chỉ
    #    palette là không được mời. Đường v2 lọc ở `presentationAdapter.ts:65`
    #    (`tool.customer_visible!==false`); bỏ dòng này là mời 5 tool chưa
    #    nghiệm thu lên canvas của khách.
    cc = {ten: c for ten, c in cong_cu.tat_ca().items()
          if c.app_slug in cho_phep and c.customer_visible}
    dinh_nghia = nut.tat_ca(cong_cu=_giai_tuy_chon_dong(db, user, cc, nap))

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
