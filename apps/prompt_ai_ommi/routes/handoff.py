"""Dat hang anh/video sang app khac qua ToolSpec cua nen tang."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _as_int, _csrf, _models, _owned_production, _require_run_enabled, _user, router, require_login, get_db)
from apps.prompt_ai_ommi.services import bindings as bindings_svc
from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai
from apps.prompt_ai_ommi.services.composer import style_description
from apps.prompt_ai_ommi.tables import OmmiResourceVariant
from apps.taovideo.refs import MAX_INLINE_BYTES, image_to_inline, normalize_image


def _tool(tool_name: str):
    from platform_core.agent.tools import discover_tools
    from platform_core.registry import discover
    loaded = discover(); spec = discover_tools(apps=loaded).get(tool_name)
    if spec is None:
        raise HTTPException(status_code=503, detail=_t('Công cụ handoff chưa khả dụng.'))
    owner = next((item for item in loaded if any(t.name == tool_name for t in item.manifest.tools)), None)
    if owner is None:
        raise HTTPException(status_code=503, detail=_t('Không xác định được app nhận handoff.'))
    return loaded, spec, owner


#: Tran ref moi lan giao bai (spec Sec 6.2b): 9 anh + 3 video. Vuot tran KHONG
#: phai loi — cat bot va noi ro la da cat.
TRAN_ANH = 9

#: Ba bo gia tri duoi day KHAI LAI LITERAL bo enum cua `apps/taovideo/manifest.py`.
#: KHONG doc thang tu manifest cua app khac: be mat app->app da khai
#: (`apps/taovideo/__init__.py::BE_MAT_CONG_KHAI`) chi mo 5 ten trong
#: `apps.taovideo.refs`, va doc thu ngoai ban khai la mo mot canh khong cong cu
#: nao kiem — dung cai bay `getattr(..., {})` that bai IM LANG.
#: Hai cho khai cung mot dieu thi phai co nguoi bat khop: banh coc
#: `tests/test_5132_...::test_banh_coc_enum_khop_manifest_taovideo` ep ba bo nay
#: bang dung bo trong manifest THAT (tep test duoc import ca hai app).
_CAMERA_VALUES = ("", "static", "dolly_in", "tracking", "orbit", "aerial", "handheld")
_MOTION_VALUES = ("", "subtle", "dynamic", "cinematic")
_VISUAL_STYLE_VALUES = ("", "realistic", "cinematic", "anime", "product")

#: Bang tu khoa la TUPLE co thu tu CO DINH, khong phai `dict`: `camera` nam trong
#: `idempotency.key_fields` cua taovideo (`manifest.py`), nen hai lan giao bai
#: cung mot canh phai suy ra CUNG mot enum — neu khong, dedupe job tach doi va
#: khach tra tien hai lan. Luat la KHOP DAU TIEN THANG, va thu tu o day la MOT
#: PHAN CUA HOP DONG: `style_description("anime")` chua ca "anime" va
#: "cinematic composition", "anime" dung truoc nen thang.
_CAMERA_TU_KHOA = (("dolly", "dolly_in"), ("track", "tracking"), ("orbit", "orbit"),
                   ("aerial", "aerial"), ("drone", "aerial"),
                   ("handheld", "handheld"), ("static", "static"),
                   ("fixed", "static"), ("tinh", "static"))
_MOTION_TU_KHOA = (("subtle", "subtle"), ("calm", "subtle"), ("cham", "subtle"),
                   ("dynamic", "dynamic"), ("energetic", "dynamic"),
                   ("manh", "dynamic"), ("cinematic", "cinematic"))
_STYLE_TU_KHOA = (("realistic", "realistic"), ("that", "realistic"),
                  ("anime", "anime"), ("product", "product"),
                  ("cinematic", "cinematic"))


def _doan_enum(text: str, values: tuple, tu_khoa: tuple) -> str:
    """Doan gia tri enum gan nhat tu van ban tu do — TAT DINH (khop dau tien
    thang tren mot bang co thu tu co dinh, khong LLM, khong duyet dict).

    Khong khop tu khoa nao => `""`, KHONG BAO GIO doan mot enum khac (spec
    Sec 6.2b luat 2). `""` co mat trong moi bang enum cua taovideo voi nghia
    "chua xac dinh" nen luon hop le; doan bua la noi ho khach mot dieu ho
    khong noi.
    """
    thap = (text or "").lower()
    for tu, gia_tri in tu_khoa:
        if tu in thap and gia_tri in values:
            return gia_tri
    return ""


def _ghep_chi_tiet(prompt: str, scene: dict, tran: int) -> str:
    """Spec Sec 6.2b luat 1 — duong SONG SONG voi `_doan_enum`: chi tiet DAY DU
    cua canh di vao `prompt` (chu tu do, `max_length=10000`), enum chi la goi y
    tho.

    Chi khop enum roi BO chu goc la vut truong im lang LAN THU HAI, dung con bo
    N-1 ma pha nay dang chua: "medium shot, 35mm, slow push in" khong co cho
    nao trong enum `camera`, va neu khong ghep vao prompt thi no bien mat khong
    ai biet. Nen `scene["camera"]/["lighting"]/["mood"]` phai co mat NGUYEN VAN
    trong prompt gui di.
    """
    duoi = []
    for nhan, khoa in (("Camera", "camera"), ("Lighting", "lighting"),
                       ("Mood", "mood")):
        gia_tri = str(scene.get(khoa) or "").strip()
        if gia_tri:  # chi ghep nhan cua truong KHAC RONG — "Mood: ." la rac
            duoi.append(f"{nhan}: {gia_tri}.")
    goc = str(prompt or "")
    if not duoi:
        return goc[:tran]
    phan_duoi = " ".join(duoi)
    # Cat PHAN GOC de chua cho phan chi tiet, khong cat phan chi tiet: mat
    # `scene["camera"]` o duoi chuoi la mat dung thu vua sua xong.
    cho_goc = max(0, tran - len(phan_duoi) - 1)
    return f"{goc[:cho_goc]} {phan_duoi}".strip()[:tran]


def _refs_tu_binding(db, owner_id: str, project, scene: dict
                     ) -> tuple[list[dict], list[dict], bool]:
    """Dung `params["refs"]` THAT tu `ommi_binding` (thay cho `refs: []` — N-1).

    Tra `(refs, skipped, has_binding)`. Moi binding khong thanh ref thi phai
    xuat hien trong `skipped` — khong duoc bien mat, vi chinh su bien mat im
    lang la con bo dang chua. `skipped` cung la thu giup `bat_bien_giao_bai`
    phan biet "anh khach da xoa" (hop le) voi "doc sai duong" (loi).
    """
    from platform_core.storage import get_storage
    storage = get_storage()
    scene_id = str(scene.get("id") or "")
    all_bindings = bindings_svc.list_bindings(
        db, project_id=project.id, owner_id=owner_id, scene_id=scene_id)
    image_bindings = [b for b in all_bindings if b.kind == "image"]

    refs: list[dict] = []
    skipped: list[dict] = []

    # Pha 1 chi giao ref ANH. Binding video/audio van phai vao `skipped`: neu bo
    # im lang thi mot canh co @VIDEO_1 se lam B-1 nem (HTTP 500) cho khach.
    for binding in all_bindings:
        if binding.kind != "image":
            skipped.append({"variant_id": binding.variant_id,
                            "handle": binding.tag.lstrip("@").lower(),
                            "ly_do": "pha 1 chua giao ref video/audio"})

    for vi_tri, binding in enumerate(image_bindings):
        handle = binding.tag.lstrip("@").lower()
        if vi_tri >= TRAN_ANH:  # spec Sec 6.2b: vuot tran la CAT, khong phai loi
            skipped.append({"variant_id": binding.variant_id, "handle": handle,
                            "ly_do": f"vuot tran {TRAN_ANH} anh moi lan giao bai"})
            continue
        variant = db.get(OmmiResourceVariant, binding.variant_id)
        if variant is None or not storage.exists(variant.storage_key):
            # Spec Sec 6.3 quy tac 3: variant con ban ghi ma MAT TEP thi van
            # TIEU so thu tu (so da chot luc `replace_bindings`) va vao
            # `skipped`. Khac quy tac 2 (khong con ban ghi => khong tieu so),
            # noi do `replace_bindings` da loai truoc khi dem.
            skipped.append({"variant_id": binding.variant_id, "handle": handle,
                            "ly_do": "tep khong ton tai"})
            continue
        try:
            data = storage.open(variant.storage_key).read()
            # Do nguong bang `normalize_image` + `MAX_INLINE_BYTES` (hai ten CO
            # trong be mat da khai) chu khong bat `RefError` — `RefError` khong
            # nam trong 5 ten `BE_MAT_CONG_KHAI` cua taovideo.
            chuan, _mime = normalize_image(data)
            if len(chuan) > MAX_INLINE_BYTES:
                skipped.append({
                    "variant_id": binding.variant_id, "handle": handle,
                    "ly_do": "anh vuot qua nguong inline sau chuan hoa"})
                continue
            url = image_to_inline(data)
        except (OSError, RuntimeError, ValueError) as exc:
            # Anh hong / khong doc duoc: vao `skipped` co LY DO (khong `continue`
            # trang), de khong mot anh hong keo ca canh thanh 500.
            skipped.append({"variant_id": binding.variant_id, "handle": handle,
                            "ly_do": f"khong doc duoc anh: {exc}"})
            continue
        refs.append({"kind": "image", "url": url, "role": binding.role,
                     "handle": handle})

    return refs, skipped, bool(image_bindings)


def _handoff_params(db, owner_id: str, project, scene: dict, kind: str,
                    body: dict) -> tuple[str, dict]:
    if kind == "image":
        tool_name = "image.generate"
        params = {"prompt": str(scene.get("prompt") or "")[:4000],
                  "model": str(body.get("model") or next(
                      (item["value"] for item in _models("image")), "hidream-o1")),
                  "aspect_ratio": str((project.payload or {}).get("brief", {}).get(
                      "aspect_ratio") or "16:9"),
                  "count": _as_int(body.get("count"), 1, 1, 4)}
    elif kind == "video":
        tool_name = "video.generate"
        brief = (project.payload or {}).get("brief") or {}
        refs, skipped, has_binding = _refs_tu_binding(db, owner_id, project, scene)
        params = {"prompt": _ghep_chi_tiet(scene.get("prompt"), scene, 10000),
                  "model": str(body.get("model") or "seedance-2.0-mini"),
                  "resolution": str(body.get("resolution") or "480p"),
                  "duration": _as_int(body.get("duration") or scene.get("duration_seconds"),
                                      5, 1, 60),
                  "aspect_ratio": str(brief.get("aspect_ratio") or "16:9"),
                  "generate_audio": bool(body.get("generate_audio", True)),
                  "camera": _doan_enum(scene.get("camera"), _CAMERA_VALUES,
                                       _CAMERA_TU_KHOA),
                  "motion": _doan_enum(scene.get("mood"), _MOTION_VALUES,
                                       _MOTION_TU_KHOA),
                  "visual_style": _doan_enum(
                      style_description(str(brief.get("style_id") or "cinematic"),
                                        str(brief.get("style_custom") or "")),
                      _VISUAL_STYLE_VALUES, _STYLE_TU_KHOA),
                  "refs": refs}
        # Luoi an toan o BIEN (spec Sec 8) — goi o DUNG MOT cho, ngay truoc khi
        # `params` roi khoi ham. Nem `ValueError` la CO Y khong bat: day la mot
        # canh bao "duong doc lech", phai on ao, khong duoc thanh 4xx em ru.
        bat_bien_giao_bai(params["prompt"], refs, skipped,
                          has_binding=has_binding)
    else:
        raise HTTPException(status_code=404, detail=_t('Loại handoff không hỗ trợ.'))
    from platform_core import providers
    capabilities = providers.model_capabilities(params["model"])
    if kind == "image":
        aspects = list(capabilities.get("aspects") or ["16:9", "9:16", "1:1", "4:3", "3:4"])
        if params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    else:
        durations = [int(value) for value in capabilities.get("durations", [])]
        if durations and params["duration"] not in durations:
            params["duration"] = min(durations, key=lambda value: abs(value - params["duration"]))
        resolutions = list(capabilities.get("resolutions") or [])
        if resolutions and params["resolution"] not in resolutions:
            params["resolution"] = resolutions[0]
        aspects = list(capabilities.get("aspects") or [])
        if aspects and params["aspect_ratio"] not in aspects:
            params["aspect_ratio"] = "16:9" if "16:9" in aspects else aspects[0]
    return tool_name, params


@router.post("/api/projects/{project_id}/handoff/{kind}", status_code=201)
async def handoff(request: Request, project_id: str, kind: str,
                  _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    scenes = list((project.payload or {}).get("scenes") or [])
    scene = next((item for item in scenes if item.get("id") == body.get("scene_id")), None)
    if scene is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy cảnh.'))
    tool_name, params = _handoff_params(db, user.id, project, scene, kind, body)
    loaded, spec, owner = _tool(tool_name)
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    try:
        clean = validate_tool_params(tool_name, params, apps=loaded)
    except ToolParamsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    clean["owner_id"] = user.id
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError, credit_for
    quote = credit_for(spec.job_type, clean)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": quote,
                             "tool": tool_name, "authoritative": True}, status_code=200)
    try:
        job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                 job_type=spec.job_type, params=clean,
                                 dedupe_key=dedupe_key_for(spec.job_type, clean))
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": quote, "id": job.id,
            "app_slug": owner.slug, "job_url": f"/jobs/{job.id}"}


@router.post("/api/projects/{project_id}/handoff-batch/image", status_code=201)
async def handoff_image_batch(request: Request, project_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    requested = set(str(value) for value in list(body.get("scene_ids") or [])[:20])
    scenes = [scene for scene in list((project.payload or {}).get("scenes") or [])
              if scene.get("id") in requested]
    if not scenes:
        raise HTTPException(status_code=422, detail=_t('Chưa chọn cảnh hợp lệ để tạo frame.'))
    loaded, spec, owner = _tool("image.generate")
    from platform_core.agent.tools import ToolParamsError, validate_tool_params
    prepared = []
    for scene in scenes:
        _, params = _handoff_params(db, user.id, project, scene, "image", body)
        try:
            clean = validate_tool_params("image.generate", params, apps=loaded)
        except ToolParamsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        clean["owner_id"] = user.id; prepared.append((scene["id"], clean))
    from platform_core.registry import credit_for
    total = sum(credit_for(spec.job_type, params) for _, params in prepared)
    if not bool(body.get("confirmed")):
        return JSONResponse({"confirmed": False, "credit": total,
                             "count": len(prepared), "authoritative": True}, status_code=200)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    jobs = []
    try:
        for scene_id, params in prepared:
            job = submit_with_credit(db, user_id=user.id, app_slug=owner.slug,
                                     job_type=spec.job_type, params=params,
                                     dedupe_key=dedupe_key_for(spec.job_type, params))
            jobs.append({"scene_id": scene_id, "id": job.id, "status": job.status})
    except (credit.ThieuCreditError, RegistryError) as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"confirmed": True, "credit": total, "count": len(jobs), "jobs": jobs}
