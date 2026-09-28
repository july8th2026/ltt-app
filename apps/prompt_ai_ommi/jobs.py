"""Durable PROMPT AI OMMI generation job."""
from __future__ import annotations

from platform_core.i18n import _ as _t
import io
import uuid
from datetime import datetime, timezone

from apps.prompt_ai_ommi import provider
from apps.prompt_ai_ommi.project_schema import (MAX_SCENES,
                                                TOI_THIEU_KY_TU_BRIEF,
                                                clean_scene)
from apps.prompt_ai_ommi.services.composer import director_prompt


def _normalize_result(raw: dict, params: dict) -> dict:
    requested = max(1, min(MAX_SCENES, int(params.get("scene_count") or 6)))
    raw_scenes = list(raw.get("scenes") or [])[:requested]
    if not raw_scenes:
        raise ValueError(_t('AI không trả cảnh nào.'))
    scenes = []
    stamp = datetime.now(timezone.utc).isoformat()
    for index, item in enumerate(raw_scenes):
        scene = clean_scene(item if isinstance(item, dict) else {}, index)
        version = {
            "id": f"ver_{uuid.uuid4().hex[:12]}", "prompt": scene["prompt"],
            "negative_prompt": scene["negative_prompt"], "feedback": "",
            "created_at": stamp,
        }
        scene["versions"] = [version]; scene["selected_version"] = 0
        scenes.append(scene)
    # Provider đôi khi trả thiếu cảnh; bổ sung placeholder trung thực thay vì
    # tuyên bố đủ rồi âm thầm lặp nội dung AI.
    while len(scenes) < requested:
        scenes.append(clean_scene({
            "title": f"Cảnh {len(scenes) + 1}",
            "summary": "Cảnh chưa được AI tạo; cần chỉnh hoặc tạo lại.",
            "continuity": "Giữ continuity từ cảnh trước.",
        }, len(scenes)))
    anchors = raw.get("anchors") if isinstance(raw.get("anchors"), dict) else {}
    package = {
        "summary": str(raw.get("summary") or "")[:3000],
        "anchors": {
            "characters": list(anchors.get("characters") or [])[:20],
            "locations": list(anchors.get("locations") or [])[:20],
            "style": str(anchors.get("style") or params.get("style") or "")[:1000],
            "continuity": list(anchors.get("continuity") or [])[:30],
        },
        "scenes": scenes,
    }
    return package


def handle(params: dict, ctx=None) -> dict:
    job_type = getattr(ctx, "job_type", "") or ""
    if job_type == "prompt_ai_ommi.import_zip":
        return _handle_import_zip(params, ctx=ctx)
    return _handle_generate(params, ctx=ctx)


def _handle_generate(params: dict, ctx=None) -> dict:
    operation = str(params.get("operation") or "director")
    if operation not in {"director", "storyboard", "iterate",
                         "character_lock"}:
        raise ValueError(_t('Operation không hợp lệ.'))
    # ⚠️ Hai nhanh nay dung TRUOC phep kiem `story`: `character_lock` KHONG co
    #    `story` (no nhan mo ta nhan vat), nen kiem story truoc se chan nham
    #    mot viec hop le. Thu tu o day la mot phan cua hop dong, khong phai
    #    tinh co (plan pha 3, Task M3 buoc 4).
    if operation == "iterate":
        from apps.prompt_ai_ommi.services.iterate import chay_iterate
        return chay_iterate(params, ctx)
    if operation == "character_lock":
        from apps.prompt_ai_ommi.services.nhan_vat import chay_khoa_nhan_vat
        return chay_khoa_nhan_vat(params, ctx)
    story = str(params.get("story") or "").strip()
    if len(story) < TOI_THIEU_KY_TU_BRIEF:
        raise ValueError(_t('Nội dung brief tối thiểu {n} ký tự.')
                         .format(n=TOI_THIEU_KY_TU_BRIEF))
    if ctx is not None:
        ctx.progress(10, "đang kiểm tra brief và consistency anchors")
    system, prompt = director_prompt(params)
    if ctx is not None:
        ctx.progress(30, "AI Director đang phân cảnh")
    # D09: không khai model ⇒ `provider` tự hỏi bản khai của app (`model_mac_dinh`).
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(system, prompt, model=model)
    if ctx is not None:
        ctx.progress(85, "đang chuẩn hóa prompt package")
    package = _normalize_result(raw, params)
    from apps.prompt_ai_ommi.manifest import _cost
    result = {
        "operation": operation,
        "prompt_package": package,
        "storyboard": package if operation == "storyboard" else None,
        "master_prompt": prompt[:20000], "tokens_used": tokens,
        "model": model,
        "credit_cost": _cost(params),
    }
    if ctx is not None:
        ctx.progress(100, "hoàn tất prompt package")
    return result


def _handle_import_zip(params: dict, ctx=None) -> dict:
    """Giải nén ZIP đã tải lên trước đó, tạo variant, dedupe theo owner.

    G-9: mọi lỗi PHẢI ném — bao gồm zip-slip/zip-bomb — để nền tảng biết job
    thất bại (job này KHÔNG giữ credit, nên không có gì để hoàn, nhưng khách
    vẫn phải thấy lỗi thay vì "xong 0 ảnh" im lặng).

    ⭐ Bất biến: mọi entry ảnh trong zip có ĐÚNG MỘT kết cục trong kết quả trả
    về — hoặc góp vào `created`/`deduped`, hoặc nằm trong `skipped` kèm lý do
    (`upload_zip.iter_safe_entries` đã đảm bảo không entry nào biến mất giữa
    hai trạng thái này; xem `tests/test_5509_upload_zip_entry_accounting.py`).
    """
    from apps.prompt_ai_ommi.services import dedupe, resources as rsvc, upload_zip
    from platform_core.db import get_session
    from platform_core.storage import get_storage

    owner_id = str(params.get("owner_id") or "")
    resource_id = str(params.get("resource_id") or "")
    zip_key = str(params.get("zip_key") or "")
    if not (owner_id and resource_id and zip_key):
        # Tái dùng msgid đã dịch — banh coc ban-dich-thieu chi cho GIAM.
        raise ValueError(_t('Thiếu tệp nguồn.'))

    storage = get_storage()
    with storage.open(zip_key) as fh:
        zip_bytes = fh.read()

    entries = list(upload_zip.iter_safe_entries(zip_bytes))
    total = len(entries)

    gen = get_session()
    db = next(gen)
    created = 0
    deduped = 0
    skipped: list[dict] = []
    try:
        for index, entry in enumerate(entries):
            if entry.skip_reason is not None:
                skipped.append({"name": entry.name, "reason": entry.skip_reason})
            else:
                file_hash = dedupe.compute_file_hash(entry.data)
                existing = dedupe.find_existing(db, owner_id=owner_id,
                                                file_hash=file_hash)
                if existing is not None:
                    deduped += 1
                else:
                    ext = entry.name.rsplit(".", 1)[-1].lower()
                    key = (f"ommi/{owner_id}/{resource_id}/"
                          f"{uuid.uuid4().hex[:16]}.{ext}")
                    storage.put(key, io.BytesIO(entry.data),
                               content_type=f"image/{ext if ext != 'jpg' else 'jpeg'}")
                    thumb_key = upload_zip.make_thumbnail(
                        storage, original_key=key, data=entry.data)
                    rsvc.add_variant(db, resource_id=resource_id, owner_id=owner_id,
                                     storage_key=key, thumb_key=thumb_key,
                                     label=entry.name, bytes_size=len(entry.data),
                                     file_hash=file_hash)
                    created += 1
            if ctx is not None:
                # Tái dùng msgid đã dịch ("processing") + số ghép NGOÀI câu
                # dịch — tránh sinh msgid mới cho mỗi cặp index/total.
                ctx.progress(int(100 * (index + 1) / max(total, 1)),
                            f"{_t('đang xử lý')} {index + 1}/{total}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    storage.delete(zip_key)
    # Bất biến kế toán: mọi entry hoặc đã tạo/dedupe, hoặc nằm trong skipped —
    # không entry nào rơi ra ngoài phép cộng này.
    assert created + deduped + len(skipped) == total
    return {"created": created, "deduped": deduped, "skipped": skipped,
           "total": total}
