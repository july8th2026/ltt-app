"""
routes/ - be mat web cua PROMPT AI OMMI, tach theo mien.

Nen tang chi can bien `router`. Import tung module o day de handler cua chung
duoc dang ky vao router truoc khi nen tang gan vao FastAPI.

    _shared.py        router + helper dung chung
    pages.py          Trang HTML va tuy chon hien thi cua nguoi dung.
    projects.py       Vong doi du an: CRUD, ban chup, bao gia va chay AI Director.
    handoff.py        Dat hang anh/video sang app khac qua ToolSpec cua nen tang.
    assets_catalog.py Tai san tai len, xuat/nhap du an, va catalog mau.
    resources.py      Kho tai nguyen rieng cua tung nguoi dung, ke ca anh va sinh anh.
    bindings.py       CRUD the (@IMAGE_k/@VIDEO_k) <-> variant, spec pha 1.
    library.py        Thu vien meta prompt, doan prompt va phong cach.
    storyboard.py     Storyboard, canh va phien ban theo tung canh.
    overview.py       So lieu Tong quan va chi tieu credit.
"""
from apps.prompt_ai_ommi.routes._shared import router
from apps.prompt_ai_ommi.routes import (  # noqa: F401  (import de dang ky route)
    pages, projects, handoff, bindings, assets_catalog, resources, library,
    storyboard, overview)

__all__ = ["router"]
