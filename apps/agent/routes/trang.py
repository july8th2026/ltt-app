"""Cac trang HTML cua LTT Automation Studio (IA dich §1, Q1 = B).

Truoc 28/09/2026 app nay co **dung hai** trang: `/agent` (mot doan van + mot
nut) va `/agent/canvas`. Canvas luon mo `items[0]` cua danh sach sap theo
`updated_at DESC`, va no **tu luu** — nen workflow mo ra luon la workflow moi
nhat. Tren giao dien khong co danh sach, khong co nut "Workflow moi", khong co
duong mo mot workflow khac. ⇒ San pham, **qua giao dien**, la
*mot-workflow-mot-tai-khoan*
(`docs/architecture/agent_ui_v2/01_CURRENT_UI_AUDIT.md` §1.1).

## Ban do trang

    /agent                      cua vao — dan sang Workflows
    /agent/workflows            DANH SACH: tim · tao moi · mo · nhan ban
    /agent/workflows/{id}       trinh soan (Canvas) mo DUNG workflow do
    /agent/canvas               loi vao KHONG id — giu nguyen hanh vi cu
    /agent/templates            danh muc MAU (UI-9, 28/09) — "Dung mau nay"
                                tao workflow that qua cua v3 roi mo Canvas
    /agent/runs · /connections · /agents · /settings
                                DAT CHO: tra 200 va noi ro "dang xay"

⭐ `/agent/canvas` giu nguyen: `test_1726::test_hai_trang_html_VAN_CON` chot no,
   va hai lan khac (UI-2, UI-3) neo kich ban trinh duyet vao dung URL do. Mot
   URL moi khong phai ly do de bo mot URL dang chay.

## ⛔ KHONG mo cua HTTP moi cho hanh dong

Tao moi va nhan ban di qua cua **da co**: `POST /agent/api/v3/workflows` va
`GET /agent/api/v3/workflows/{id}` (`drafts_v3.py`). Nen chung la mot lat JS nho
trong template, khong phai mot `POST /agent/workflows` thu hai.

🔴 **Luu tru (archive) CHUA LAM, va co chu dich.** `Workflow.archived_at` co
   trong lieu do va `v3_danh_sach` da loc theo no, nhung **khong cua nao dat
   duoc no**. Mo mot be mat HTTP moi la mot quyet dinh rieng ⇒ da bao dieu
   phoi, chua viet. ⛔ Dung them `POST .../archive` o day ma khong hoi.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.agent import mau as _mau
from apps.agent.routes._shared import (_canvas_presentation_mode, _page_context,
                                       _user, router)
from platform_core.frontend_bundle import bundle_assets
from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from platform_core.models import Workflow
from server.auth.session import require_login
from server.deps import get_db
from server.templating import templates

#: Muc IA da khai o `manifest.nav` nhung noi dung thuoc lan khac. Moi dong:
#: (duong dan, nav_key, ten muc, lan lam, mo ta).
#:
#: ⚠️ "Dat cho" = mot trang **noi ro dang xay**. ⛔ KHONG phai mot trang trong
#:    trong-nhu-that: mot trang gia vo hoat dong la mot loi noi doi, va nguoi
#:    dung se bao loi thay vi doi.
DAT_CHO: tuple[tuple[str, str, str, str, str], ...] = (
    ("/runs", "agent_runs", N_("Lượt chạy"), "UI-7",
     N_("Lịch sử mọi lượt chạy của bạn: lọc theo trạng thái, mở lại một lượt để xem từng bước.")),
    ("/connections", "agent_connections", N_("Các kết nối"), "UI-5",
     N_("Kết nối tới dịch vụ ngoài để một bước dùng lại mà không phải dán khoá mỗi lần.")),
    ("/agents", "agent_agents", N_("Agent"), "UI-8b",
     N_("Soạn workflow bằng cách mô tả mục tiêu, xem bản đề xuất rồi chọn nhận hay bỏ.")),
    ("/settings", "agent_settings", N_("Cài đặt Agent"), "UI-10",
     N_("Giao diện, ngôn ngữ và các giá trị mặc định cho workflow mới.")),
)


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login)):
    return templates.TemplateResponse(request, "agent.html",
                                      _page_context(request))


@router.get("/workflows", response_class=HTMLResponse)
def trang_workflows(request: Request, q: str = "", luu_tru: int = 0,
                    _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    """Danh sach workflow cua chinh nguoi dang dang nhap.

    ⭐ Ve may chu, khong phai ve JS: mot danh sach doc-duoc phai con doc duoc
       khi JS chet, va no do duoc bang HTTP trong pytest thay vi chi do duoc
       tren trinh duyet.

    `q` va `luu_tru` la **tham so trang**, khong phai cua API: chung chi doi thu
    duoc ve trong chinh trang nay.

    ## ⭐ `?luu_tru=1` la mot KHUNG NHIN, khong phai mot bo loc noi them

    Hai tap RIENG BIET: dang dung, va da luu tru. Khong co khung nhin nay thi
    `POST /mo-lai` ton tai ma KHONG VOI TOI DUOC — mot workflow da luu tru bien
    mat khoi moi danh sach, nen giao dien khong con cho nao de bam mo lai no.
    ⇒ Cua nay **di kem** hai cua POST 28/09, khong phai mot tien nghi them.

    ⚠️ `tong` cung phai dem trong CUNG khung nhin. Neu no dem ban dang dung
       trong lúc trang dang hien kho luu tru, con so se noi nguoc voi danh sach
       ngay ben duoi no.
    """
    user = _user(request)
    tim = (q or "").strip()
    xem_kho = bool(luu_tru)
    cua_toi = (Workflow.owner_id == user.id,
               Workflow.archived_at.is_not(None) if xem_kho
               else Workflow.archived_at.is_(None))
    cau = select(Workflow).where(*cua_toi)
    if tim:
        cau = cau.where(Workflow.name.ilike(f"%{tim}%"))
    rows = db.execute(cau.order_by(Workflow.updated_at.desc())).scalars().all()
    # `tong` la so workflow KHONG loc theo ten (nhung CUNG khung nhin). Khong co
    # no, mot o tim khong khop gi se trong y het mot tai khoan vua mat sach
    # workflow.
    tong = len(db.execute(
        select(Workflow.id).where(*cua_toi)).scalars().all())
    # So ban trong kho, de nut "Kho luu tru" noi duoc co gi trong do thay vi
    # bat nguoi dung bam vao mot trang co the rong.
    so_kho = len(db.execute(select(Workflow.id).where(
        Workflow.owner_id == user.id,
        Workflow.archived_at.is_not(None))).scalars().all())
    context = _page_context(request, nav="agent_workflows")
    context.update({"workflows": rows, "q": tim, "tong": tong,
                    "xem_kho": xem_kho, "so_kho": so_kho})
    return templates.TemplateResponse(request, "agent_workflows.html", context)


@router.get("/templates", response_class=HTMLResponse)
def trang_templates(request: Request, _identity: str = Depends(require_login)):
    """Danh mục mẫu (`apps/agent/mau.py`) — UI-9.

    ⭐ Ve o MAY CHU, giong `trang_workflows`: danh sach mau doc duoc khi JS
       chet. Chi hanh dong "Dung mau nay" moi can JS, y het nut "Workflow
       moi" cua `agent_workflows.html` — va no goi DUNG cua da co
       (`POST /agent/api/v3/workflows`), khong mo cua moi.

    ⚠️ `document` cua tung mau la DU LIEU (JSON), khong phai chuoi hien thi —
       no di qua `tojson` nguyen ven, KHONG qua `_t()`. Chi `ten`/`mo_ta` (dan
       N_() trong `mau.py`) moi dich.
    """
    danh_sach = _mau.tat_ca()
    context = _page_context(request, nav="agent_templates")
    context.update({
        "mau_list": danh_sach,
        "mau_json": {m.id: {"name": _t(m.ten), "document": m.document}
                    for m in danh_sach},
    })
    return templates.TemplateResponse(request, "agent_templates.html", context)


def _trang_canvas(request: Request, *, workflow_id: str = "",
                  nav: str = "agent_workflows") -> HTMLResponse:
    canvas_js, canvas_css = bundle_assets("agent-canvas")
    if not canvas_js:
        raise HTTPException(status_code=503,
                            detail=_t('Canvas bundle chưa được build.'))
    context = _page_context(request, nav=nav)
    context.update({"canvas_js": canvas_js, "canvas_css": canvas_css,
                    "canvas_presentation": _canvas_presentation_mode(),
                    "workflow_id": workflow_id})
    return templates.TemplateResponse(request, "agent_canvas.html", context)


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
def trang_mot_workflow(request: Request, workflow_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    """Trinh soan mo DUNG workflow nay — ⛔ khong phai `items[0]`.

    ⭐ Chu so huu bi loc NGAY TRONG TRUY VAN, va *"khong co"* voi *"cua nguoi
       khac"* tra ve cung mot 404 — y het `drafts_v3._cua_toi`. Mot 403 o day se
       xac nhan rang mot id nao do co that.

    Id di theo **URL**, khong theo trang thai phien: nen tai lai trang van dung
    workflow do, va hai tab mo hai workflow khac nhau khong danh nhau.
    """
    user = _user(request)
    wf = db.execute(
        select(Workflow).where(Workflow.id == str(workflow_id or ""),
                               Workflow.owner_id == user.id,
                               Workflow.archived_at.is_(None))).scalars().first()
    if wf is None:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy workflow.'))
    return _trang_canvas(request, workflow_id=wf.id)


@router.get("/canvas", response_class=HTMLResponse)
def canvas_page(request: Request, _identity: str = Depends(require_login)):
    """Loi vao KHONG id — giu nguyen hanh vi cu (mo `items[0]`, tao neu chua co).

    ⛔ Dung bo route nay: `test_1726` chot no, va no la noi bundle duoc phuc vu
       cho moi kich ban trinh duyet dang neo vao `/agent/canvas`.
    """
    return _trang_canvas(request, nav="agent_workflows")


def _dang_ky_dat_cho(duong: str, nav_key: str, ten: str, lan: str,
                     mo_ta: str) -> None:
    """Dang ky mot trang DAT CHO. Tra 200 va noi ro dang xay + lan nao lam."""

    @router.get(duong, response_class=HTMLResponse, name=f"agent_dc_{nav_key}")
    def trang(request: Request, _identity: str = Depends(require_login),
              _ten: str = ten, _nav: str = nav_key, _lan: str = lan,
              _mo_ta: str = mo_ta) -> HTMLResponse:
        context = _page_context(request, nav=_nav)
        context.update({"ten_muc": _t(_ten), "mo_ta_muc": _t(_mo_ta),
                        "lan_lam": _lan})
        return templates.TemplateResponse(request, "agent_dang_xay.html",
                                          context)


for _duong, _nav_key, _ten, _lan, _mo_ta in DAT_CHO:
    _dang_ky_dat_cho(_duong, _nav_key, _ten, _lan, _mo_ta)
