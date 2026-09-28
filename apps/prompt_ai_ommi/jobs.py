"""Durable PROMPT AI OMMI generation job."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from platform_core.job_runner import JobCancelled
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


def _quyet_toan_phan_da_giao(params: dict, ctx, so_canh: int) -> None:
    """Khach bam Huy: thu DUNG phan da giao, roi de nguoi goi NEM LAI.

    ## 🔴 Vi sao ham nay ton tai

    App nay tinh tien o **tang job**: credit GIU luc nop, quyet toan luc xong. Va
    nen tang **mac dinh hoan TOAN BO** khi job bi huy (`job_runner._hoan_credit`).

    ⇒ Khong co ham nay thi khach huy giua chung se duoc hoan het **va** giu phan
      da sinh — tuc lay viec MIEN PHI, va **lap duoc**: nop 20 canh, huy sau lo 1,
      nhan 5 canh, lam lai.

    ## ⭐ Vi sao no du de chan, ma ⛔ KHONG cham `credit.py` hay `job_runner.py`

    `credit.hoan()` tu `return` ngay khi `_da_ket_so(job_id)` la True. Nen mot lan
    `quyet_toan` o day lam lan hoan cua runner thanh **vo tac dung**.

    ⚠️ Chot ay nam o `hoan()`, ⛔ KHONG o `so_da_giu()`: `so_da_giu` chi cong but
       toan `CREDIT_HOLD` nen no **van > 0** sau quyet toan, va `_hoan_credit` **van
       goi** `hoan()`. `tests/test_5573` ghim chinh cai guard do, o ma NEN TANG.

    ## ⛔ Va no KHONG duoc nem

    Nguoi goi dang tren duong nem `JobCancelled`. Mot ngoai le tu day se **thay**
    ngoai le do, va job se bi ghi la THAT BAI thay vi DA HUY — mot trang thai sai
    bao cho khach, cho mot viec khach chu dong lam.
    """
    import logging

    job_id = str(getattr(ctx, "job_id", "") or "")
    if not job_id:
        return                                  # goi tay / test: khong co so sach
    try:
        from platform_core import credit
        from platform_core.db import get_session
        from platform_core.models import Job

        from apps.prompt_ai_ommi.services import chia_lo
        gia = chia_lo.gia_phan_da_giao(so_canh, params)
        for db in get_session():
            try:
                job = db.get(Job, job_id)
                # ⛔ `user_id` lay tu JOB, khong tu `ctx`: `JobContext.__init__` chi
                #    co `(job_id, gpu_uuid)` — ⛔ khong co `user_id`.
                if job is not None and job.user_id:
                    credit.quyet_toan(db, job.user_id, job_id, actual=gia)
                    db.commit()
            finally:
                db.close()
            break
    except Exception:                            # noqa: BLE001
        # ⛔ KHONG nem (xem docstring), nhung ⛔ cung KHONG im lang: khong quyet
        #    toan duoc nghia la khach se duoc hoan TOAN BO cho mot luot DA giao
        #    hang. Do la mat doanh thu, va no phai co mot dong de doi soat.
        logging.getLogger(__name__).exception(
            "ommi huy: KHONG quyet toan duoc job %s (da giao %s canh) - "
            "khach se duoc hoan toan bo", job_id[:8], so_canh)

def _sinh_theo_lo(params: dict, model: str, ctx,
                  da_giao: dict | None = None) -> tuple[dict, int, str]:
    """Sinh canh theo LO. Tra `(raw, tong_tokens, loi_nhac_lo_dau)`.

    ## 🔴 Vi sao chia lo (Q-16, do that 27/09/2026)

    Hai luot doc lap o `scene_count=20` deu tra **19/20** canh, va do dai truong
    `prompt` **co dan theo thu tu canh** (159->87 va 165->~90 ky tu) trong khi chi
    dung 67 %/69 % cua `_MAX_TOKENS`. ⇒ Chat luong suy **TRUOC** khi cham tran
    cung, nen nang tran token ⛔ KHONG phai thuoc.

    ⭐ Canh thu 20 khong "kem", no la mot **placeholder** do vong
       `while len(scenes) < requested` trong `_normalize_result` bu vao. Trung
       thuc — nhung khach da tra tien cho no.

    ## ⭐ Vi sao KHONG can mot loi nhac moi

    `composer.director_prompt` da co san hai o dung cho viec nay:

        scenes   = params["scene_count"]          -> co lo
        existing = json.dumps(existing[:20])      -> lich su, dung de giu lien mach

    Nen mot lo chi la goi lai chinh no voi hai khoa ay da thay. ⛔ Khong dung
    `services/breakdown.py` — ham do nam tren duong ROUTE (`routes/storyboard.py`),
    ⛔ khong nam tren duong job nay.

    ## ⚠️ `bao_lo` duoc phep NEM, va do la co y

    `ctx.progress_counter` tu nem `JobCancelled` khi khach bam Huy
    (`job_runner.py:222`). Ham nay ⛔ KHONG duoc bat: bat va chay tiep nghia la job
    ket thuc BINH THUONG sau khi bi huy, va tien duoc quyet toan DAY DU cho mot
    luot chi giao mot phan. Ngoai le phai bay len cho biet ve TIEN (Task 4).

    ⭐ Goi o RANH LO, ⛔ khong giua lo: mot lo da goi LLM la da tieu tien.
    """
    from apps.prompt_ai_ommi.services import chia_lo

    tong = max(1, min(MAX_SCENES, int(params.get("scene_count") or 6)))
    da_sinh: list[dict] = []
    tong_tokens = 0
    loi_nhac_dau = ""
    goi_y: dict = {}

    for dau, cuoi in chia_lo.cac_lo(tong):
        p_lo = {**params, "scene_count": cuoi - dau + 1,
                "existing_scenes": chia_lo.cua_so_lich_su(da_sinh)}
        system, prompt = director_prompt(p_lo)
        if not loi_nhac_dau:
            # `master_prompt` giu loi nhac cua LO DAU: no la loi nhac dinh nghia ca
            # goi (brief, phong cach, khoa nhan vat). Cac lo sau chi khac o o
            # `existing`, nen ghep het vao day chi lam no dai ra ma khong them tin.
            loi_nhac_dau = prompt
        raw_lo, tokens = provider.generate_json(system, prompt, model=model)
        tong_tokens += int(tokens or 0)
        if not goi_y:
            # `summary`/`anchors` lay tu lo DAU: chung mo ta CA goi, va mot ban
            # ghi de tu lo cuoi se mo ta dung nam canh cuoi.
            goi_y = {"summary": raw_lo.get("summary"),
                     "anchors": raw_lo.get("anchors")}
        da_sinh += list((raw_lo or {}).get("scenes") or [])[:cuoi - dau + 1]
        if da_giao is not None:
            # ⭐ Ghi TRUOC khi bao tien do: `progress_counter` co the NEM, va luc
            #    do nhanh `except` phai biet lo nay DA giao xong.
            da_giao["n"] = min(len(da_sinh), tong)
        if ctx is not None:
            # ⛔ KHONG boc try/except: xem docstring.
            ctx.progress_counter(min(len(da_sinh), tong), tong, don_vi="canh",
                                 event_code="ommi_chia_lo")

    raw = {"summary": goi_y.get("summary"), "anchors": goi_y.get("anchors"),
           "scenes": da_sinh}
    return raw, tong_tokens, loi_nhac_dau

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
    if ctx is not None:
        ctx.progress(30, "AI Director đang phân cảnh")
    # D09: không khai model ⇒ `provider` tự hỏi bản khai của app (`model_mac_dinh`).
    model = str(params.get("model") or provider.model_mac_dinh())
    da_giao = {"n": 0}          # o nho, nhanh `except` doc de biet thu bao nhieu
    try:
        raw, tokens, prompt = _sinh_theo_lo(params, model, ctx, da_giao)
    except JobCancelled:
        _quyet_toan_phan_da_giao(params, ctx, da_giao["n"])
        raise
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
