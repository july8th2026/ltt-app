"""Brief va canh kich ban.

Canh kich ban nam o day, khong o `services/canh.py` rieng: canh THUOC VE
brief, tach ra la chia mot thuc the cho hai chu (P-8). Neu tep nay phinh qua
~400 dong thi tach o pha 4, van mot chu.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select

from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.tables import OmmiBrief, OmmiCanh

#: Tran so canh kich ban -- DUNG LAI hang so `MAX_SCENES` cua
#: `project_schema.py`, khong go rieng so `20` o day. `storyboard.py` co mot
#: hang so KHAC ten `MAX_KHUNG_HINH` (60) -- do la tran KHUNG HINH storyboard
#: (ommi_scene), khac voi tran CANH KICH BAN (ommi_canh) o day (spec Sec 4.3).
MAX_CANH = MAX_SCENES
_SO_CANH = (1, MAX_SCENES)
_THOI_LUONG = (3, 600)


def _id_moi(tien_to: str) -> str:
    return f"{tien_to}_{uuid.uuid4().hex[:12]}"


def tao_brief(db, owner_id: str, du_lieu: dict) -> OmmiBrief:
    """Dat CU THE moi gia tri mac dinh o day, khong dua vao `default=` cua cot.

    SQLAlchemy chi ap `default=` cua cot luc FLUSH, khong phai luc khoi tao
    doi tuong. `preflight()` doc `target_scenes`/`target_duration_sec` truoc
    khi ai kip flush (mien phi => khong duoc ep ghi CSDL) se gap `None` neu
    chi dua vao cot -- do la `test_preflight_bat_brief_thieu`, khong flush.
    """
    b = OmmiBrief(owner_id=owner_id, title=str(du_lieu.get("title") or "")[:200],
                  target_scenes=3, target_duration_sec=15,
                  aspect_ratio="16:9", language="vi", status="draft",
                  free_iterations_used=0)
    return sua_brief(db, b, du_lieu, _them=True)


def sua_brief(db, brief: OmmiBrief, du_lieu: dict, *,
              _them: bool = False) -> OmmiBrief:
    if "title" in du_lieu:
        brief.title = str(du_lieu["title"] or "")[:200]
    if "story_vi" in du_lieu:
        brief.story_vi = str(du_lieu["story_vi"] or "")
    for ten, gioi_han in (("goal", 300), ("audience", 300)):
        if ten in du_lieu:
            setattr(brief, ten, str(du_lieu[ten] or "")[:gioi_han])
    if "target_scenes" in du_lieu:
        brief.target_scenes = max(_SO_CANH[0], min(
            _SO_CANH[1], int(du_lieu["target_scenes"] or 3)))
    if "target_duration_sec" in du_lieu:
        brief.target_duration_sec = max(_THOI_LUONG[0], min(
            _THOI_LUONG[1], int(du_lieu["target_duration_sec"] or 15)))
    for ten in ("aspect_ratio", "language", "style_id", "meta_prompt_id",
                "character_id", "background_id", "project_id"):
        if ten in du_lieu:
            setattr(brief, ten, du_lieu[ten] or None
                    if ten.endswith("_id") else str(du_lieu[ten] or ""))
    if "referenced_variants" in du_lieu:
        brief.referenced_variants = [
            str(x) for x in list(du_lieu["referenced_variants"] or [])[:60]]
    if _them:
        db.add(brief)
    return brief


def doc_brief(db, brief_id: str, owner_id: str) -> OmmiBrief:
    """Tra `KeyError` chung cho ca "khong ton tai" va "khong phai cua anh".

    Phan biet hai ca nay la mot ro ri: ke goi biet duoc id nao TON TAI.
    """
    b = db.get(OmmiBrief, str(brief_id or ""))
    if b is None or b.owner_id != owner_id:
        raise KeyError(brief_id)
    return b


def liet_ke(db, owner_id: str, *, archived: bool = False,
            q: str = "") -> list[OmmiBrief]:
    cau = select(OmmiBrief).where(OmmiBrief.owner_id == owner_id)
    cau = cau.where(OmmiBrief.archived_at.is_not(None) if archived
                    else OmmiBrief.archived_at.is_(None))
    if str(q or "").strip():
        cau = cau.where(OmmiBrief.title.ilike(f"%{q.strip()}%"))
    return list(db.execute(cau.order_by(OmmiBrief.updated_at.desc())).scalars())


def nhan_ban(db, brief: OmmiBrief) -> OmmiBrief:
    """Ban sao la mot kich ban MOI => so dem luot mien phi ve 0.

    Day la duong lach 2 luot mien phi neu khach nhan ban lien tuc. Do duoc
    lam dung thi sua MOT dong o day (mang theo so dem cua ban goc).
    """
    ban_sao = OmmiBrief(
        owner_id=brief.owner_id, project_id=brief.project_id,
        title=f"{brief.title} (ban sao)"[:200], story_vi=brief.story_vi,
        goal=brief.goal, audience=brief.audience,
        target_duration_sec=brief.target_duration_sec,
        target_scenes=brief.target_scenes, aspect_ratio=brief.aspect_ratio,
        language=brief.language, style_id=brief.style_id,
        meta_prompt_id=brief.meta_prompt_id, character_id=brief.character_id,
        background_id=brief.background_id,
        referenced_variants=list(brief.referenced_variants or []),
        status="draft", free_iterations_used=0)
    db.add(ban_sao)
    for c in doc_canh(db, brief):
        db.add(OmmiCanh(
            brief_id=ban_sao.id, position=c.position, title=c.title,
            duration_seconds=c.duration_seconds, summary=c.summary,
            prompt=c.prompt, negative_prompt=c.negative_prompt,
            camera=c.camera, lighting=c.lighting, mood=c.mood,
            continuity=c.continuity))
    return ban_sao


def doc_canh(db, brief: OmmiBrief) -> list[OmmiCanh]:
    return list(db.execute(
        select(OmmiCanh).where(OmmiCanh.brief_id == brief.id)
        .order_by(OmmiCanh.position)).scalars())


def dat_canh(db, brief: OmmiBrief, canh: list[dict]) -> list[OmmiCanh]:
    """THAY toan bo canh cua brief. GIU NGUYEN `id` neu duoc truyen vao.

    Vi sao giu id (spec S-4): `ommi_binding.scene_id` cua pha 1 tro vao id
    canh trong `AppProject.payload`. Pha 3 chuyen canh sang bang nay; sinh id
    moi nghia la MOI binding tro vao hu khong va anh tham chieu mat sach.
    """
    db.execute(delete(OmmiCanh).where(OmmiCanh.brief_id == brief.id))
    ra: list[OmmiCanh] = []
    for vi_tri, item in enumerate(list(canh or [])[:MAX_CANH]):
        item = item if isinstance(item, dict) else {}
        row = OmmiCanh(
            id=str(item.get("id") or "").strip() or _id_moi("scene"),
            brief_id=brief.id, position=vi_tri,
            title=str(item.get("title") or "")[:200],
            duration_seconds=max(1, min(60, int(item.get("duration_seconds") or 5))),
            summary=str(item.get("summary") or ""),
            prompt=str(item.get("prompt") or ""),
            negative_prompt=str(item.get("negative_prompt") or ""),
            camera=str(item.get("camera") or ""),
            lighting=str(item.get("lighting") or ""),
            mood=str(item.get("mood") or ""),
            continuity=str(item.get("continuity") or ""),
            selected_version=max(0, int(item.get("selected_version") or 0)))
        db.add(row)
        ra.append(row)
    return ra


def prompt_day_du(canh) -> str:
    """Prompt cua canh + chi tiet camera/lighting/mood GHEP NGUYEN VAN.

    `taovideo` khai `camera`/`motion`/`visual_style` la enum DONG
    (`apps/taovideo/manifest.py:196-198`), ma Director sinh chu tu do giau
    chi tiet. Cho thong tin THAT song la `prompt` (chu tu do, 10 000 ky tu);
    enum chi la goi y tho, va viec suy ra enum la cua pha 2 (spec Sec 6.2b).

    Chi khop enum roi BO chu goc = vut truong im lang lan thu hai.
    Tat dinh: thu tu nhan co dinh, khong duyet `dict`.
    """
    phan = [str(getattr(canh, "prompt", "") or "").strip()]
    for nhan, ten in (("Camera", "camera"), ("Lighting", "lighting"),
                      ("Mood", "mood")):
        gia_tri = str(getattr(canh, ten, "") or "").strip()
        if gia_tri:
            phan.append(f"{nhan}: {gia_tri}.")
    return " ".join(p for p in phan if p)


def preflight(brief: OmmiBrief) -> dict:
    """Kiem brief truoc khi goi LLM. MIEN PHI => khong ghi CSDL, khong goi LLM."""
    muc = [
        {"id": "title", "label": "Ten kich ban", "passed": bool(brief.title.strip())},
        {"id": "story", "label": "Noi dung toi thieu 20 ky tu",
         "passed": len(str(brief.story_vi or "").strip()) >= 20},
        {"id": "scene_count", "label": f"So canh {_SO_CANH[0]}-{_SO_CANH[1]}",
         "passed": _SO_CANH[0] <= brief.target_scenes <= _SO_CANH[1]},
        {"id": "duration", "label": f"Thoi luong {_THOI_LUONG[0]}-{_THOI_LUONG[1]} giay",
         "passed": _THOI_LUONG[0] <= brief.target_duration_sec <= _THOI_LUONG[1]},
    ]
    return {"checklist": muc, "passed": all(m["passed"] for m in muc)}
