"""composite.py — sinh anh composite theo ommi_image_template (pha 5).

OMMI khong dung engine rieng: dieu phoi (chon anh tham chieu, ghep prompt tu
mau) nam o day, loi goi provider di qua job `taoanh.generate` da co tu pha 1
— dung mau voi `resources.generate_resource_image` (xem
`apps/prompt_ai_ommi/routes/resources.py:444-487`).

`OmmiImageJob` khong PHAI la job cua nen tang (`platform_core.models.Job`) —
no la SO THEO DOI cua OMMI, tro toi job that qua `job_id`, va giu them
`version`/`parent_id` de lam duoc "quay lai ban truoc"/"thu lai" ma ban than
`Job` khong khai niem nao co san cho.

## Placeholder cua image template KHAC bo cua meta prompt (spec Sec 7.2)

21 mau nhap tu Prompt Seedance Studio dung dung bon ten: SUBJECT/STYLE/
EXTRA/EQUIPMENT (do tren CSDL, khong phai {NAME}/{ASSET_TYPE}). Dieu phoi da
phan quyet (27/09): bon ten nay la O NGUOI DUNG GO TAY luc sinh anh, nen o
day chi kiem CU PHAP (ten nam trong tap da khai, dung `{TEN}`, khong ten la)
bang cach DUNG LAI `services/placeholders.py::kiem_placeholder` cua pha 3 —
⛔ khong viet bo kiem thu hai, va ⛔ khong kiem nguon gia tri.

## Vi sao OmmiImageJob CHI duoc import trong tung ham, khong o dau tep

Luc Task 9 nay bat dau, `OmmiImageJob` (Task 2, lan H) CO THE chua ton tai —
xem bao cao lam I. Import cuc bo lam `quote()` va nhanh `confirmed=False`
cua `generate()` chay duoc NGAY CA KHI lop do chua co, vi hai duong nay
khong bao gio cham no.
"""
from __future__ import annotations

import re

from apps.prompt_ai_ommi.services import placeholders as ph
from apps.prompt_ai_ommi.services import resources as rsvc
from apps.prompt_ai_ommi.project_schema import IMAGE_JOB_TYPE
from platform_core.i18n import _ as _t

# ✅ 28/09: het trung van ban. Ghi chu cu dung o ve "⛔ khong import tu
# routes/_shared vao services/" — nhung ket luan thi tam: cho dung la mot
# lop THAP HON ma ca hai duoc phep import.
_IMAGE_JOB_TYPE = IMAGE_JOB_TYPE

_PLACEHOLDER_NAMES = ("SUBJECT", "STYLE", "EXTRA", "EQUIPMENT")
_PLACEHOLDER_TOKEN = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def _dummy_values() -> dict:
    """Gia tri gia CHI de vuot qua phep 2/3 cua `kiem_placeholder` — o day ta
    chu dinh CHI kiem phep 1 (ten dung trong body co nam trong tap da khai
    khong), khong kiem nguon gia tri that (dieu phoi da phan quyet)."""
    return {name: "x" for name in _PLACEHOLDER_NAMES}


def _validate_prompt_syntax(prompt_text: str) -> None:
    thieu = ph.kiem_placeholder(prompt_text, list(_PLACEHOLDER_NAMES),
                                _dummy_values())
    if thieu:
        # Chuoi nem ra cho nguoi dung => boc `_t()`. Ban dau de khong dau va
        # (check_i18n.py: chuoi CO dau ma chua boc la loi; ban-dich-thieu:
        # chuoi DA boc ma chua co trong catalog cung la loi). Dung theo dung
        # tien le `services/nhap_mau_goc.py:65`. Bao dieu phoi ban tieng Viet
        # co dau that: "Mẫu dùng placeholder không hợp lệ hoặc không được
        # khong boc `_t()` de ne hai cong — nhung the thi KHACH thay chu khong
        # dau. Cong la thu de THOA, khong phai de NE.
        raise ValueError(
            _t('Mẫu dùng placeholder không hợp lệ hoặc chưa được khai báo: ')
            + f"{thieu!r}")


def _substitute(prompt_text: str, values: dict) -> str:
    """Thay `{TEN}` bang gia tri that (co the RONG — khac han
    `placeholders.render()` von CO Y giu nguyen ten khi rong, vi do la co che
    phuc vu viec PHAT HIEN thieu gia tri o mau meta prompt. O day gia tri
    rong la HOP LE (khach khong go EXTRA/EQUIPMENT), va cu phap da duoc
    `_validate_prompt_syntax` xac nhan truoc do roi nen khong con ten la nao
    sot lai de phai giu nguyen."""
    return _PLACEHOLDER_TOKEN.sub(
        lambda m: str(values.get(m.group(1), "")), prompt_text)


def _subject_of(resource) -> str:
    return (resource.prompt_text or resource.description
           or resource.name or "").strip()


def _reference_keys(db, *, resource_id: str, owner_id: str, template,
                    reference_variant_ids: list) -> list:
    """Không raise ở đây dù `template.requires_ref` — `quote()` là một ước
    tính, khách có thể chưa chọn ảnh tham chiếu lúc xem giá. Bắt buộc thật sự
    chỉ áp dụng lúc SINH THẬT (`generate(confirmed=True)`), xem ở đó."""
    cap = max(1, int(template.multi_ref_max))
    wanted = {str(v) for v in (reference_variant_ids or [])[:cap] if v}
    return [v.storage_key for v in rsvc.variants(db, resource_id, owner_id)
           if v.id in wanted]


def _params(db, *, template, resource_id: str, owner_id: str,
           reference_variant_ids: list, extra: str = "",
           equipment: str = "", style_body: str = "") -> dict:
    _validate_prompt_syntax(template.prompt_text)
    resource = rsvc.get_owned(db, resource_id, owner_id)
    keys = _reference_keys(db, resource_id=resource_id, owner_id=owner_id,
                           template=template,
                           reference_variant_ids=reference_variant_ids)
    prompt = _substitute(template.prompt_text, {
        "SUBJECT": _subject_of(resource),
        "STYLE": (style_body or "").strip(),
        "EXTRA": (extra or "").strip(),
        "EQUIPMENT": (equipment or "").strip(),
    }).strip()
    if template.negative_lock:
        prompt = f"{prompt}\n\nKHONG: {template.negative_lock}"
    params = {"prompt": prompt[:4000], "aspect_ratio": template.aspect,
             "count": max(1, min(4, int(template.n_outputs))),
             "owner_id": owner_id}
    if keys:
        params["image_keys"] = keys
    return params


def quote(db, *, template, resource_id: str, owner_id: str,
         reference_variant_ids: list, extra: str = "", equipment: str = "",
         style_body: str = "") -> dict:
    """Báo giá — KHÔNG tạo job, KHÔNG tạo `OmmiImageJob`."""
    from platform_core.registry import credit_for
    params = _params(db, template=template, resource_id=resource_id,
                    owner_id=owner_id,
                    reference_variant_ids=reference_variant_ids, extra=extra,
                    equipment=equipment, style_body=style_body)
    return {"credit": int(credit_for(_IMAGE_JOB_TYPE, params)),
           "count": params["count"]}


def generate(db, *, template, resource_id: str, owner_id: str,
            reference_variant_ids: list, confirmed: bool, app_slug: str,
            extra: str = "", equipment: str = "",
            style_body: str = "") -> dict:
    """Báo giá khi `confirmed=False`; nộp job + ghi `OmmiImageJob` khi
    `confirmed=True`. Cùng công thức giá ở cả hai nhánh — tách đôi là mở
    đường cho hai công thức lệch nhau (bài học ở `resources.py`).
    """
    params = _params(db, template=template, resource_id=resource_id,
                    owner_id=owner_id,
                    reference_variant_ids=reference_variant_ids, extra=extra,
                    equipment=equipment, style_body=style_body)
    from platform_core.registry import credit_for
    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not confirmed:
        return {"credit": estimate, "count": params["count"], "confirmed": False}

    if template.requires_ref and not params.get("image_keys"):
        raise ValueError(_t('Mẫu này cần ít nhất một ảnh tham chiếu.'))

    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    job = submit_with_credit(
        db, user_id=owner_id, app_slug=app_slug, job_type=_IMAGE_JOB_TYPE,
        params=params, dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))

    from apps.prompt_ai_ommi.tables import OmmiImageJob
    image_job = OmmiImageJob(owner_id=owner_id, template_id=template.id,
                            resource_id=resource_id, params=params,
                            job_id=job.id, version=1, parent_id=None,
                            status="queued")
    db.add(image_job)
    db.flush()
    return {"credit": estimate, "confirmed": True, "job_id": job.id,
           "image_job_id": image_job.id}


def revert(db, *, image_job_id: str, owner_id: str):
    """Đánh dấu một lượt sinh là 'reverted' — variant đã gắn (nếu có) KHÔNG bị
    xoá ở đây; xoá variant là việc của thùng rác/bulk-delete, việc của hàm này
    chỉ là dừng coi lượt này là bản hiện hành.
    """
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    row = db.get(OmmiImageJob, image_job_id)
    if row is None or row.owner_id != owner_id:
        raise rsvc.ResourceNotFound(_t('Không tìm thấy lượt sinh ảnh.'))
    row.status = "reverted"
    db.flush()
    return row


def retry(db, *, image_job_id: str, owner_id: str, app_slug: str) -> dict:
    """Nộp lại CÙNG tham số, `version = cha.version + 1`, `parent_id = cha.id`."""
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    parent = db.get(OmmiImageJob, image_job_id)
    if parent is None or parent.owner_id != owner_id:
        raise rsvc.ResourceNotFound(_t('Không tìm thấy lượt sinh ảnh.'))
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    job = submit_with_credit(
        db, user_id=owner_id, app_slug=app_slug, job_type=_IMAGE_JOB_TYPE,
        params=parent.params,
        dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE,
                                  {**parent.params, "_retry_of": parent.id}))
    child = OmmiImageJob(owner_id=owner_id, template_id=parent.template_id,
                        resource_id=parent.resource_id, params=parent.params,
                        job_id=job.id, version=parent.version + 1,
                        parent_id=parent.id, status="queued")
    db.add(child)
    db.flush()
    return {"job_id": job.id, "image_job_id": child.id, "version": child.version}
