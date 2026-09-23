"""Palette V2 của Canvas — MỘT đường, sinh từ registry (spec §13.1, §13.4).

⛔ Không có bảng nhãn/biểu tượng/phân tầng nào trong tệp này. Mọi thứ hiển thị
   đến từ `NodeDefinition`, và `NodeDefinition` đến từ ba nguồn của §4.5.
   `/agent/api/palette` (v2, `workspace.py`) chết theo plan 01b.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.agent.routes._shared import _user, router
from server.auth.session import require_login
from server.deps import get_db

from platform_core.workflow import he_kieu, nut

log = logging.getLogger(__name__)

#: Dấu ĐỌC ĐƯỢC cho giao diện khi một tool không giải được lựa chọn động.
#:
#: ⭐ Đúng khuôn `registry.discover()`: một app hỏng đi vào `item.error` chứ
#:    không làm sập cả registry. Palette là một **catalogue**, không phải một
#:    giao dịch — một mục hỏng không được giết cả quyển sách.
#: 🔴 MỘT MÃ NGẮN, không hơn. Chi tiết (loại lỗi, traceback, đường dẫn tệp,
#:    tên tham chiếu của app) đi vào log máy chủ. Palette là bề mặt MỌI tài
#:    khoản đăng nhập đọc được; một `str(exc)` ở đây là kênh rò tên module và
#:    đường dẫn đĩa của máy chủ ra cho khách.
MA_LOI_TUY_CHON = "LUACHON_KHONG_TAI_DUOC"


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


def _tham_so_co_dau(tham_so: dict, truong: tuple) -> dict:
    """Gắn `x-ltt-loi` lên ĐÚNG những trường chưa tải được lựa chọn.

    ⛔ Không sửa tại chỗ: `nd.tham_so` do `luoc_do.sang_json_schema` dựng cho
       node này, còn bản sao gửi đi là chuyện của riêng route.
    """
    if not truong:
        return tham_so
    thuoc_tinh = dict(tham_so.get("properties") or {})
    for ten in truong:
        if ten in thuoc_tinh:
            thuoc_tinh[ten] = {**thuoc_tinh[ten], "x-ltt-loi": MA_LOI_TUY_CHON}
    return {**tham_so, "properties": thuoc_tinh}


def sang_json(nd: nut.NodeDefinition, *, truong_loi: tuple = ()) -> dict:
    """Bản RÚT GỌN gửi ra trình duyệt.

    ⛔ Liệt kê TƯỜNG MINH từng khoá thay vì `dataclasses.asdict`: một trường
       mới thêm vào `NodeDefinition` không được tự động chảy ra Internet.
       `mock` là một callable của app — không bao giờ ra ngoài.

    `truong_loi` rỗng là đường thường. Có giá trị ⇒ node này ra palette với
    lược đồ **tĩnh** và một dấu đọc được (`MA_LOI_TUY_CHON`) ở cả mức node lẫn
    từng trường, để giao diện nói được *"mục này chưa tải được lựa chọn"* thay
    vì vẽ một ô chữ tự do trông y hệt một tham số bình thường.
    """
    return {
        **({"x-ltt-loi": MA_LOI_TUY_CHON} if truong_loi else {}),
        "type": nd.type, "type_version": nd.type_version,
        "kind": nd.kind, "category": nd.category,
        "title": nd.title, "description": nd.description, "icon": nd.icon,
        "app_name": nd.app_name,
        "cong_vao": _cong(nd.cong_vao), "cong_ra": _cong(nd.cong_ra),
        "tham_so": _tham_so_co_dau(nd.tham_so, truong_loi),
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


def _truong_dong(c) -> tuple:
    """Những tham số của tool này mà danh sách lựa chọn CHỈ có sau khi giải.

    Giải cả tool hỏng thì **mọi** trường loại này mất lựa chọn, không riêng
    trường của tham chiếu đã ném — nên đánh dấu đúng tập này chứ không đoán
    một trường. Bốn nguồn, lấy từ `agent.tools.resolve_params_schema`:
    tham chiếu động theo người dùng, `model_ref`, `source`, `depends_on`.
    """
    dong = set(getattr(getattr(c, "spec", None), "tuy_chon_dong", None) or ())
    for ten, rule in (c.params_schema or {}).items():
        if not isinstance(rule, dict):
            continue
        if (rule.get("type") == "model_ref" or rule.get("source")
                or rule.get("depends_on")):
            dong.add(ten)
    return tuple(sorted(dong))


def _giai_tuy_chon_dong(db: Session, user, cc: dict, nap: list) -> tuple:
    """Giải enum ĐỘNG trước khi `luoc_do` dịch sang JSON Schema.

    Trả `(công cụ đã giải, {node type hỏng: trường bị ảnh hưởng})`.

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
    ra: dict = {}
    hong: dict[str, tuple] = {}
    for ten, c in cc.items():
        try:
            ra[ten] = replace(c, params_schema=resolve_params_schema(
                ten, apps=nap, db=db, user_id=uid))
        except Exception:
            # 🔴 PHẠM VI HẸP NHẤT LÀM ĐƯỢC TỪ ĐÂY: đúng MỘT tool, không bọc cả
            #    route. Lời gọi này chạy mã do APP sở hữu (`tuy_chon_dong` trỏ
            #    `module:attribute`, `registry.tai_tham_chieu`) — nó hỏng khi
            #    bảng riêng của app lỗi, sidecar chết, hay app gõ sai tham
            #    chiếu. Ném thẳng ra là 500 cho CẢ palette: một app hỏng làm
            #    chết trình soạn Canvas của mọi người.
            # ⛔ KHÔNG `pass`. Nuốt im lặng thì khách thấy một danh sách rỗng
            #    và không ai biết vì sao — dấu đọc được ở dưới là cái giá phải
            #    trả để được đi tiếp.
            log.warning(
                "palette v3: khong giai duoc lua chon dong cua tool %r "
                "(user %r) — tra luoc do TINH kem ma %s",
                ten, uid, MA_LOI_TUY_CHON, exc_info=True)
            ra[ten] = c
            # `nut.tu_toolspec` đặt `type=f"app.{cc.ten}"`; khoá theo node type
            # để route không phải suy ngược từ `nd.type` về tên tool.
            hong[f"app.{ten}"] = _truong_dong(c)
    return ra, hong


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
    cc_giai, hong = _giai_tuy_chon_dong(db, user, cc, nap)
    dinh_nghia = nut.tat_ca(cong_cu=cc_giai)

    theo_nhom: dict[str, list] = {}
    for nd in dinh_nghia.values():
        theo_nhom.setdefault(nd.category, []).append(nd)
    nhom = [{"category": c,
             "nut": [sang_json(nd, truong_loi=hong.get(nd.type, ()))
                     for nd in
                     sorted(theo_nhom[c], key=lambda x: (x.title, x.type))]}
            for c in nut.CATEGORY if theo_nhom.get(c)]
    return JSONResponse({"phien_ban": 3, "nhom": nhom,
                         "luat_noi_day": he_kieu.xuat_luat_noi_day()})


@router.get("/api/v3/luat-noi-day")
def luat_noi_day_v3(_identity: str = Depends(require_login)):
    return JSONResponse(he_kieu.xuat_luat_noi_day())
