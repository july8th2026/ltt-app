"""Dat hang anh/video sang app khac qua ToolSpec cua nen tang."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _as_int, _csrf, _models, _owned_production, _require_run_enabled, _user, router, require_login, get_db)
from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai
from apps.prompt_ai_ommi.services.composer import style_description
# Than cua cac helper duoi day nam o `services/handoff_stage.py` (Pha 2 chuyen
# cho, khong viet lai). Giu DUNG ten cu o day de `tests/test_5132_*` va
# `tests/test_5133_*` cua Pha 1 chay nguyen khong sua mot dong — do la bang
# chung phep di chuyen khong doi hanh vi.
from apps.prompt_ai_ommi.services.handoff_stage import (  # noqa: F401
    TRAN_ANH, _CAMERA_TU_KHOA, _CAMERA_VALUES, _MOTION_TU_KHOA,
    _MOTION_VALUES, _STYLE_TU_KHOA, _VISUAL_STYLE_VALUES, _doan_enum,
    _ghep_chi_tiet, _refs_tu_binding)


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
    # 🚧 SHIM, khong phai duong song. Nhanh nay chi con TEST goi toi:
    #    route `/handoff/video` moi (dang ky TRUOC `/handoff/{kind}`) da che
    #    duong HTTP cua no, va khach di qua VE `ommi_handoff`.
    # No ton tai de `tests/test_5132_*` va `tests/test_5133_*` cua Pha 1 chay
    #    NGUYEN khong sua mot dong — do la LUOI duy nhat chung minh phep chuyen
    #    sang `services/handoff_stage.py` khong doi hanh vi (luoi N-1).
    # ⛔ CHET O PHA 3: khi lan C noi `handoff` sang `ommi_brief`, hai test kia
    #    duoc thay bang ban tuong duong tren duong moi, roi nhanh nay va
    #    `_refs_tu_binding` di cung nhau. No D-1 (dieu phoi chot 26/09).
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


# ── Duong VIDEO (Pha 2): dung VE roi de khach tu sua o `taovideo` ───────────
#
# ⚠️ Hai route nay phai dang ky TRUOC `/handoff/{kind}` o duoi: Starlette khop
#    theo THU TU dang ky, nen mot `/handoff/{kind}` dung truoc se nuot
#    `/handoff/video`. Doi cho hai khoi la doi hanh vi cua khach ma khong mot
#    dong nao trong khoi thay doi — dung kieu hong khong ai doc ra trong diff.
#
# Duong `{kind}` cu VAN giu nhanh `video` trong `_handoff_params` (test Pha 1
# goi thang bang Python). Ve HTTP thi nhanh do khong con voi tay toi duoc: mot
# khach bam giao bai video nay di qua VE, khong tu nop job thay khach nua.

def _scene_or_404(project, scene_id: str) -> dict:
    scenes = list((project.payload or {}).get("scenes") or [])
    scene = next((item for item in scenes if item.get("id") == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy cảnh.'))
    return scene


@router.post("/api/projects/{project_id}/handoff/video", status_code=201)
async def handoff_video(request: Request, project_id: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    _require_run_enabled(user)
    project = _owned_production(db, project_id, user.id)
    scene = _scene_or_404(project, str(body.get("scene_id") or ""))

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    overrides = {khoa: body.get(khoa) for khoa in
                 ("model", "resolution", "duration", "generate_audio")
                 if khoa in body}
    payload = hs.dung_payload(db, project=project, scene=scene,
                              owner_id=user.id, overrides=overrides)
    ve = hs.tao_ve(db, project_id=project.id,
                   scene_id=str(scene.get("id") or ""), payload=payload)
    db.commit()
    return {"ticket_id": ve.id, "expires_at": ve.expires_at.isoformat(),
            "open_url": f"/taovideo/?tu_studio={ve.id}",
            "skipped": payload["skipped"],
            "skipped_over_limit": payload["skipped_over_limit"]}


@router.get("/api/handoff/{ticket_id}/payload")
def handoff_payload(request: Request, ticket_id: str,
                    _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    user = _user(request)
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    row = hs.tim_ve(db, ticket_id)
    if row is None:
        raise HTTPException(status_code=404,
                            detail=_t('Vé giao bài không hợp lệ.'))
    # Quyen kiem qua DU AN so huu — `ommi_handoff` co y khong nhan doi
    # `owner_id`. Ai khong phai chu thi thay 404, khong 403: mot 403 xac nhan
    # cho nguoi la rang ve nay CO that.
    _owned_production(db, row.project_id, user.id)
    try:
        payload = hs.doc_va_tieu_ve(db, row)
    except hs.VeDaDung:
        db.rollback()
        raise HTTPException(status_code=409,
                            detail=_t('Vé giao bài đã được dùng.')) from None
    except hs.VeHetHan:
        db.rollback()
        raise HTTPException(status_code=410,
                            detail=_t('Vé giao bài đã hết hạn.')) from None
    db.commit()
    return payload


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
