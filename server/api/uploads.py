"""``/api/v1/uploads`` and ``/api/v1/artifacts`` — media in and media out.

Uploads reuse ``platform_core.upload_sessions`` unchanged: staging key owned by
the account, declared size and MIME locked at ticket time, actual size plus
magic-byte check at confirm, promotion only after a credit hold, sweeper and
compensation for everything that goes wrong (Q85).

Two properties are worth stating out loud because they are easy to lose:

* the caller never sends or receives a storage key — only opaque ids;
* large media goes **straight to object storage** through a presigned PUT when
  the backend supports it. Streaming gigabytes through this process would put a
  video transfer on the same event loop as every control-plane request, and
  Cloudflare would reject it at 100 MB anyway.
"""
from __future__ import annotations

import re
from pathlib import PurePath

from fastapi import Body, Depends, File, Path, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import upload_sessions
from platform_core.models import Job, UPLOAD_READY
from platform_core.public_api import media, policy, sandbox
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.errors import (ApiError, invalid_request,
                                             not_found)
from platform_core.public_api.principal import Principal, ensure_owner
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_UPLOADS_WRITE)
from platform_core.storage import get_storage
from server.api.auth import require_scope
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}
# Short enough that a URL leaked into a screenshot or a log sink is stale before
# it is useful; long enough for a client to finish a download.
ARTIFACT_URL_TTL_S = 300


def _public_upload(session, *, target=None) -> dict:
    body = {
        "id": session.id,
        "status": session.status,
        "filename": session.filename,
        "content_type": session.content_type,
        "expected_size": int(session.expected_size or 0),
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }
    if target is not None:
        body["upload"] = {"method": target.method, "url": target.url,
                          "headers": dict(target.headers or {})}
    return body


def _kind_for_tool(tool, param: str) -> str:
    """Which media rules a tool parameter implies, from its published schema."""
    from platform_core.public_api.invocation import _internal_schema
    from platform_core.registry import discover

    internal = _internal_schema(tool, discover())
    spec = internal.get(param)
    if spec is None:
        raise invalid_request(f"Unknown input field: {param}.", field=param)
    kind = media.media_kind(
        (tool.input_schema.get("properties", {}).get(param) or {}).get("type", ""),
        str(spec.get("type") or ""))
    if not kind:
        raise invalid_request(f"{param} does not take an upload.", field=param)
    return kind


from platform_core.job_content import RETENTION_DAYS as _ARTIFACT_RETENTION_DAYS


def register_upload_routes(api, config, tag: str) -> None:

    @api.post("/uploads", tags=[tag], summary="Create an upload ticket",
              description=("Reserves an upload slot for one tool input. Returns "
                           "a direct upload target when the storage backend "
                           "supports it."))
    def create_upload(
        body: dict = Body(...),
        principal: Principal = Depends(require_scope(SCOPE_UPLOADS_WRITE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        payload = body or {}
        tool = require_tool(build_catalog(config), str(payload.get("tool") or ""),
                            principal)
        field = str(payload.get("field") or "")
        kind = _kind_for_tool(tool, field)
        allowed, max_size = media.rules_for(kind)

        # A policy may lower the ceiling for a tier or an account, never raise
        # it: the media rules and the edge still bound what is possible, and a
        # tier that could opt past them would be selling something the platform
        # cannot deliver (EXT-14).
        resolved = policy.resolve(db, config=config, principal=principal,
                                  tool_name=tool.name)
        max_size = min(max_size, max(1, resolved.max_upload_bytes))

        try:
            session = upload_sessions.create(
                db, user_id=principal.user_id,
                # The app behind the tool, resolved here: a caller must not be
                # able to aim an upload at an app of its choosing.
                app_slug=tool.app_slug,
                filename=str(payload.get("filename") or "upload"),
                content_type=str(payload.get("content_type") or ""),
                expected_size=payload.get("size"),
                max_size=max_size, allowed_types=allowed,
            )
        except upload_sessions.UploadSessionError as exc:
            raise invalid_request(str(exc)) from exc

        target = upload_sessions.upload_target(get_storage(), session)
        body_out = _public_upload(session, target=target)
        if target is None:
            # No presign available: offer the multipart fallback, which is
            # capped where Cloudflare caps it.
            body_out["upload"] = {
                "method": "POST",
                "url": f"/api/v1/uploads/{session.id}/content",
                "max_bytes": media.MULTIPART_LIMIT,
            }
        return JSONResponse(body_out, status_code=201, headers=_NO_STORE)

    @api.post("/uploads/{upload_id}/content", tags=[tag],
              summary="Upload file content (fallback path)",
              description=("Sends the bytes through the API when the storage "
                           "backend cannot issue a direct upload URL."))
    async def upload_content(
        request: Request,
        upload_id: str = Path(...),
        file: UploadFile = File(...),
        principal: Principal = Depends(require_scope(SCOPE_UPLOADS_WRITE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        session = _owned_session(db, principal, upload_id)
        data = await file.read(media.MULTIPART_LIMIT + 1)
        if len(data) > media.MULTIPART_LIMIT:
            raise invalid_request("File exceeds the limit for this upload path.")
        import io

        get_storage().put(session.staging_key, io.BytesIO(data),
                          content_type=session.content_type)
        return JSONResponse(_public_upload(session), headers=_NO_STORE)

    @api.post("/uploads/{upload_id}/confirm", tags=[tag],
              summary="Confirm an uploaded file",
              description=("Verifies the stored bytes against the declared size "
                           "and format before the file may be used."))
    def confirm_upload(
        upload_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_UPLOADS_WRITE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        session = _owned_session(db, principal, upload_id)
        try:
            upload_sessions.confirm(db, get_storage(), session)
        except upload_sessions.UploadSessionError as exc:
            raise invalid_request(str(exc)) from exc
        return JSONResponse(_public_upload(session), headers=_NO_STORE)

    @api.get("/artifacts/{artifact_id}", tags=[tag],
             summary="Get a short-lived download URL for a job output",
             description=("Returns a time-limited URL for one output of a job "
                          "this account owns. Outputs are kept for "
                          f"{_ARTIFACT_RETENTION_DAYS} days after the job "
                          "finishes, then deleted; the job itself stays "
                          "available for billing reconciliation."))
    def get_artifact(
        artifact_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_ARTIFACTS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        job, field, index, tool = _owned_artifact(db, principal, artifact_id,
                                                  config)
        key = media.storage_key_for(job, field, index, tool)
        # `try_url_for` degrades to None on a local backend and logs real R2
        # failures instead of swallowing them.
        url = get_storage().try_url_for(key, ttl_s=ARTIFACT_URL_TTL_S)
        return JSONResponse(
            {
                "id": artifact_id,
                "field": field,
                # A signed URL is a bearer credential for one object: short TTL,
                # never logged, never cached by anything in between.
                "url": url or f"/api/v1/artifacts/{artifact_id}/content",
                "expires_in": ARTIFACT_URL_TTL_S if url else 0,
            },
            headers=_NO_STORE,
        )

    @api.get("/artifacts/{artifact_id}/content", tags=[tag],
             summary="Download a job output (fallback path)",
             description=("Streams the output when the storage backend cannot "
                          "issue a signed URL. Same "
                          f"{_ARTIFACT_RETENTION_DAYS}-day window as the "
                          "signed URL above."))
    def artifact_content(
        artifact_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_ARTIFACTS_READ)),
        db: Session = Depends(get_db),
    ) -> StreamingResponse:
        job, field, index, tool = _owned_artifact(db, principal, artifact_id,
                                                  config)
        key = media.storage_key_for(job, field, index, tool)
        storage = get_storage()
        stream = storage.open(key)
        filename = PurePath(key).name
        return StreamingResponse(
            stream, media_type="application/octet-stream",
            headers={"Cache-Control": "no-store",
                     "Content-Disposition": f'attachment; filename="{filename}"'})


def _owned_session(db, principal: Principal, upload_id: str):
    """Ownership in the query, not in an ``if`` after the fetch."""
    from platform_core.models import UploadSession
    from sqlalchemy import select

    session = db.execute(select(UploadSession).where(
        UploadSession.id == str(upload_id),
        UploadSession.user_id == principal.user_id,
    )).scalar_one_or_none()
    if session is None:
        raise not_found("Not found.")
    return session


def _owned_artifact(db, principal: Principal, artifact_id: str, config):
    """Owner check, then the tool that defines which outputs are public."""
    from platform_core.public_api.invocation import api_meta

    job_id, field, index = media.parse_artifact_id(artifact_id)
    job = sandbox.ensure_same_mode(
        ensure_owner(db.get(Job, job_id), principal), principal)
    name = api_meta(job).get("tool") or ""
    tool = next((entry for entry in build_catalog(config) if entry.name == name),
                None)
    if tool is None:
        # A job created outside the API (or through a tool no longer published)
        # has no public output contract, so it has no public artifacts either.
        raise not_found("Not found.")
    return job, field, index, tool


#: Hinh dang cua mot artifact id: `<job_id>.<field>.<index>`. Doi day du de mot
#: upload id (khong co dau cham) khong bao gio di nham nhanh.
_MAU_ARTIFACT = re.compile(r"[^.]+\.[A-Za-z_][A-Za-z0-9_]*\.\d+")


def _giai_artifact(db, principal: Principal, param: str, value: str):
    """Ket qua cua mot job TRUOC -> mot tham chieu, KHONG phai mot ban sao.

    ⛔ Moi loi o day tra CUNG MOT 400. Mot artifact cua tai khoan khac va mot id
       bia phai khong phan biet duoc — neu khac nhau, no thanh mot cong do id.
    """
    from platform_core.public_api.invocation import ThamChieuArtifact

    try:
        job_id, field, index = media.parse_artifact_id(value)
    except ApiError:
        raise invalid_request(f"{param}: unknown media id.", field=param) from None

    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    # `user_id` la cong THU NHAT. Khong co no thi bat ky ai doan duoc mot job id
    # deu doc duoc ket qua cua nguoi khac.
    if job is None or str(job.user_id) != str(principal.user_id):
        raise invalid_request(f"{param}: unknown media id.", field=param)

    # Cong THU HAI: danh sach trang cua hop dong dau ra cua chinh tool DA SINH
    # ra artifact do — khong phai tool dang goi.
    tool_sinh = _tool_cua_job(job)
    if tool_sinh is None:
        # 🔴 KHONG DUOC DI TIEP. `storage_key_for(..., tool=None)` **bo qua**
        #    danh sach trang, nen mot job ma ta khong tim lai duoc ToolSpec se
        #    bien moi thu handler de trong `result` — ban nhap, tep trung gian,
        #    dump go loi — thanh dau vao goi duoc. Khong tim thay tool thi tu
        #    choi, dung doan.
        raise invalid_request(f"{param}: unknown media id.", field=param)
    try:
        khoa = media.storage_key_for(job, field, index, tool=tool_sinh)
    except ApiError:
        raise invalid_request(f"{param}: unknown media id.", field=param) from None

    return ThamChieuArtifact(staging_key=khoa,
                             filename=PurePath(khoa).name,
                             content_type="")


def _tool_cua_job(job):
    """ToolSpec da sinh ra job nay, hoac `None` neu khong tim duoc.

    ⚠️ `None` lam `storage_key_for` BO qua danh sach trang, nen o day thieu tool
       la phai TU CHOI, khong duoc di tiep. Bên goi chiu trach nhiem do.
    """
    from platform_core.registry import discover

    for muc in discover():
        if muc.error or muc.manifest.slug != job.app_slug:
            continue
        for t in muc.manifest.tools:
            if t.job_type == job.job_type:
                return t
    return None


def resolve_upload_reference(db, principal: Principal, tool, param: str,
                             value: str):
    """Turn a public media id into something the job path can use.

    Accepts **two** shapes, and that is the whole of API composability:

      * an **upload id** — a file the caller sent us; returns an `UploadSession`
        ready to be promoted (moved) into the new job;
      * an **artifact id** (`<job>.<field>.<index>`) — the output of an earlier
        job of the same account; returns a `ThamChieuArtifact`, which is
        **referenced, never moved**.

    🔴 VI SAO PHAI CO NUA THU HAI. Truoc 30/08 chi co upload, va chu thich o
       `invocation.py` ghi thang rang giai artifact la *"Prompt 07's job"*. He
       qua thuc te: **khong noi chuoi duoc**. Muon dua video vua sinh sang
       `video.upscale` thi khach phai TAI VE roi TAI LEN LAI — mot tep hang tram
       MB di ra roi di vao, qua Cloudflare, chi de o lai dung cho no dang nam.

    ⛔ VA NUA THU HAI NAY NOI LONG MOT RANG BUOC, nen phai noi ro dieu do.
       Upload bi khoa theo `app_slug`: mot ve tai len tao cho app A khong dung
       duoc o app B, de mot ve bi lo khong mo duoc ca nen tang. Artifact **co y**
       khong bi khoa nhu vay — day dung la muc dich: ket qua cua `taovideo` phai
       dua duoc sang `upscalevideo`.

       Hai cong con lai **khong** noi long, va chung moi la thu giu an toan:
         · **chu so huu** — job sinh ra artifact phai thuoc chinh principal nay;
         · **danh sach trang cua hop dong dau ra** — `media.storage_key_for(...,
           tool=...)`: mot tep trung gian handler tinh co de lai trong `result`
           khong duoc thanh dau vao goi duoc chi vi ai do doan ra id.

    Moi thu mot ke goi co the thu tuon vao day — upload cua tai khoan khac, ve
    dung hai lan, khoa luu tru tho, artifact cua nguoi khac, mot id bia — deu ra
    cung mot 400.
    """
    if _MAU_ARTIFACT.fullmatch(str(value or "")):
        return _giai_artifact(db, principal, param, value)

    from platform_core.models import UploadSession
    from sqlalchemy import select

    session = db.execute(select(UploadSession).where(
        UploadSession.id == str(value or ""),
        UploadSession.user_id == principal.user_id,
        UploadSession.app_slug == tool.app_slug,
    )).scalar_one_or_none()
    if session is None:
        raise invalid_request(f"{param}: unknown upload id.", field=param)
    if session.status != UPLOAD_READY:
        raise invalid_request(
            f"{param}: this upload has not been confirmed, or has already been "
            f"used.", field=param)
    return session
