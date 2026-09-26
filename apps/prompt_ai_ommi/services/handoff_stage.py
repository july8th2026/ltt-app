"""services/handoff_stage.py — dung `payload` giao bai sang app khac (Pha 2).

⭐ Tep nay khong phai ma MOI. Cac helper duoi day (`_doan_enum`,
`_ghep_chi_tiet`, `_refs_tu_binding`, ba bo enum va ba bang tu khoa) DA duoc
Pha 1 cai dat trong `routes/handoff.py`; o day chung chi DOI CHO. Viet lai
mot ban thu hai la de hai ban cua mot logic trong kho — dung bay
`hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`. `routes/handoff.py` re-export
lai dung ten cu, nen `tests/test_5132_*` va `tests/test_5133_*` cua Pha 1 chay
NGUYEN khong sua mot dong — do chinh la bang chung phep di chuyen khong doi
hanh vi. Doi lai, `routes/handoff.py` thoi phinh (303 dong) — hang rao
`tools/lint_app_contract.py` co mot luat ve dieu do.

HAI duong giao bai video ton tai song song, CO Y:

- Duong Pha 1 (`_refs_tu_binding`) giu nguyen the cua `ommi_binding`
  (`image_1`, `video_1`...) va nop job thang qua ToolSpec. Con duoc goi bang
  Python (test Pha 1); duong HTTP cua no da bi route `/handoff/video` moi che.
- Duong Pha 2 (`dung_payload`) DANH SO LAI sang `@IMG_k`/`@VID_k` (spec
  Sec 6.3), mang theo `tag_map`/`skipped_over_limit`, roi cat vao mot VE
  (`ommi_handoff`) de khach tu sua o `taovideo`.

Phan CHUNG cua hai duong — "mot binding anh -> mot ref hoac mot dong
`skipped`" — nam o `_mot_ref_anh()`, dung MOT lan.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from apps.prompt_ai_ommi.services import bindings as bindings_svc
from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai
from apps.prompt_ai_ommi.tables import OmmiHandoff, OmmiResourceVariant
from apps.taovideo.refs import (MAX_INLINE_BYTES, image_role, image_to_inline,
                                normalize_image)

#: Tran ref moi lan giao bai (spec Sec 6.2b): 9 anh + 3 video. Vuot tran KHONG
#: phai loi — cat bot va noi ro la da cat.
TRAN_ANH = 9
TRAN_VIDEO = 3

#: Vong doi ve giao bai (spec Sec 4.2 Pha 2).
VE_HET_HAN_PHUT = 30

#: Tien to the MOI (phia `taovideo`) va nhan ngoac vuong cua ban goc.
_TIEN_TO_TAG = {"image": "IMG", "video": "VID"}
_NHAN_NGOAC = {"image": "Image", "video": "Video"}

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


def _mot_ref_anh(storage, variant, *, handle: str, role: str
                 ) -> tuple[dict | None, dict | None]:
    """Mot binding ANH -> `(ref, skipped)` — dung cho CA HAI duong giao bai.

    Dung MOT trong hai gia tri khac `None`. Ben goi tu quyet dinh ca "variant
    khong con ban ghi" (quy tac 2 cua spec Sec 6.3) TRUOC khi goi, vi hai duong
    xu ly ca do khac nhau va do la mot khac biet CO Y (xem docstring dau tep).

    Do nguong bang `normalize_image` + `MAX_INLINE_BYTES` (hai ten CO trong be
    mat da khai) chu khong bat `RefError` — `RefError` khong nam trong 5 ten
    `BE_MAT_CONG_KHAI` cua taovideo.
    """
    if not storage.exists(variant.storage_key):
        # Spec Sec 6.3 quy tac 3: variant con ban ghi ma MAT TEP thi van TIEU so
        # thu tu (so da chot luc `replace_bindings`) va vao `skipped`. Khac quy
        # tac 2 (khong con ban ghi => khong tieu so), noi do `replace_bindings`
        # da loai truoc khi dem.
        return None, {"variant_id": variant.id, "handle": handle,
                      "ly_do": "tep khong ton tai"}
    try:
        data = storage.open(variant.storage_key).read()
        chuan, _mime = normalize_image(data)
        if len(chuan) > MAX_INLINE_BYTES:
            return None, {"variant_id": variant.id, "handle": handle,
                          "ly_do": "anh vuot qua nguong inline sau chuan hoa"}
        url = image_to_inline(data)
    except (OSError, RuntimeError, ValueError) as exc:
        # Anh hong / khong doc duoc: vao `skipped` co LY DO (khong `continue`
        # trang), de khong mot anh hong keo ca canh thanh 500. `RefError` la mot
        # `RuntimeError` nen nhanh nay bat no ma khong phai dua ten do vao.
        return None, {"variant_id": variant.id, "handle": handle,
                      "ly_do": f"khong doc duoc anh: {exc}"}
    return ({"kind": "image", "url": url, "role": image_role(role),
             "handle": handle}, None)


def _refs_tu_binding(db, owner_id: str, project, scene: dict
                     ) -> tuple[list[dict], list[dict], bool]:
    """Dung `params["refs"]` THAT tu `ommi_binding` (thay cho `refs: []` — N-1).

    Tra `(refs, skipped, has_binding)`. Moi binding khong thanh ref thi phai
    xuat hien trong `skipped` — khong duoc bien mat, vi chinh su bien mat im
    lang la con bo dang chua. `skipped` cung la thu giup `bat_bien_giao_bai`
    phan biet "anh khach da xoa" (hop le) voi "doc sai duong" (loi).

    ⚠️ Duong PHA 1: the giu NGUYEN (`image_1`), khong danh so lai. Duong Pha 2
    la `dung_payload()` duoi day.
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
        if variant is None:
            skipped.append({"variant_id": binding.variant_id, "handle": handle,
                            "ly_do": "tep khong ton tai"})
            continue
        ref, bo_qua = _mot_ref_anh(storage, variant, handle=handle,
                                   role=binding.role)
        if bo_qua is not None:
            skipped.append(bo_qua)
            continue
        refs.append(ref)

    return refs, skipped, bool(image_bindings)


# ── Pha 2: danh so lai the va dung payload cho ve giao bai ──────────────────

def _so_cua_tag(tag: str) -> str:
    khop = re.search(r"_(\d+)$", str(tag or ""))
    return khop.group(1) if khop else ""


def _doi_tag_trong_prompt(prompt: str, tag_map: dict, kind_by_tag: dict,
                          bo_tag: dict) -> str:
    """Thay ca `@IMAGE_k`/`@VIDEO_k` va `[Image k]`/`[Video k]` (Sec 6.3 rule 4).

    Dung regex voi `(?!\\d)` de `@IMAGE_1` khong nuot nham `@IMAGE_10`.

    ⭐ `bo_tag` la nhung the khong con tro tro toi dau (variant mat ban ghi /
    cua nguoi khac / bi cat vi vuot tran). Chung bi XOA khoi prompt, khong de
    nguyen: de nguyen thi `bat_bien_giao_bai` B-1 nem `ValueError` (prompt nhac
    mot handle khong co trong refs va cung khong trong `skipped`) va khach an
    mot HTTP 500 cho mot ca HOP LE — khach xoa anh la chuyen binh thuong. Va
    cai te hon: `@IMAGE_1` con lai chuan hoa thanh `image_1`, DUNG bang handle
    cua `@IMG_1` moi, nen B-1 im lang di qua trong khi prompt dang tro sai anh.
    Spec khong noi ca nay; quyet dinh o day la XOA, ghi lai de doi chieu.
    """
    out = str(prompt or "")
    thay = [(cu, moi) for cu, moi in tag_map.items()]
    thay += [(cu, "") for cu in bo_tag]
    # Sap theo do dai GIAM DAN: `@IMAGE_10` phai duoc xet truoc `@IMAGE_1`, va
    # `(?!\d)` mot minh khong du khi hai the cung co trong mot lan duyet.
    for cu, moi in sorted(thay, key=lambda x: -len(x[0])):
        out = re.sub(re.escape(cu) + r"(?!\d)", moi, out)
        so = _so_cua_tag(cu)
        nhan = _NHAN_NGOAC.get(kind_by_tag.get(cu, ""))
        if so and nhan:
            out = re.sub(re.escape(f"[{nhan} {so}]") + r"(?!\d)", moi, out)
    return out


def dung_payload(db, *, project, scene: dict, owner_id: str,
                 overrides: dict | None = None) -> dict:
    """Dung payload giao bai (spec Sec 6.2) tu mot canh cua project.

    Ham THUAN voi `ommi_handoff` — khong tao ve, khong commit. Goi
    `bat_bien_giao_bai()` ngay truoc khi tra ve (spec Sec 8: dung MOT cho).

    `owner_id` la THAM SO BAT BUOC, khong doc tu `project`: quyen so huu la mot
    bien gioi, va doc no bang `getattr(project, "user_id", None)` la dung dung
    cai bay "cho noi hai module vut truong im lang" — sai ten thuoc tinh se
    thanh `None` va loc bindings cua MOI nguoi ve rong, im lang.
    """
    from platform_core.storage import get_storage

    storage = get_storage()
    scene_id = str(scene.get("id") or "")
    bindings = bindings_svc.list_bindings(
        db, project_id=project.id, owner_id=owner_id, scene_id=scene_id)
    has_binding = bool(bindings)
    anh = sorted([b for b in bindings if b.kind == "image"],
                 key=lambda b: b.position)
    video = sorted([b for b in bindings if b.kind == "video"],
                   key=lambda b: b.position)
    qua_tran = max(0, len(anh) - TRAN_ANH) + max(0, len(video) - TRAN_VIDEO)
    bi_cat = anh[TRAN_ANH:] + video[TRAN_VIDEO:]
    anh, video = anh[:TRAN_ANH], video[:TRAN_VIDEO]

    refs: list[dict] = []
    skipped: list[dict] = []
    tag_map: dict[str, str] = {}
    kind_by_tag: dict[str, str] = {}
    # `dict` thay `set`: thu tu chen on dinh => thay the trong prompt tat dinh.
    bo_tag: dict[str, None] = {b.tag: None for b in bi_cat}
    dem = {"image": 0, "video": 0}

    for kind, danh_sach in (("image", anh), ("video", video)):
        for binding in danh_sach:
            variant = db.get(OmmiResourceVariant, binding.variant_id)
            if variant is None or variant.owner_id != owner_id:
                # Sec 6.3 quy tac 2 (khong con ban ghi) va quy tac 4 (cua nguoi
                # khac): KHONG tieu so, KHONG vao `skipped`.
                bo_tag[binding.tag] = None
                continue
            dem[kind] += 1
            tag_moi = f"@{_TIEN_TO_TAG[kind]}_{dem[kind]}"
            tag_map[binding.tag] = tag_moi
            kind_by_tag[binding.tag] = kind
            if kind == "image":
                ref, bo_qua = _mot_ref_anh(storage, variant, handle=tag_moi,
                                           role=binding.role)
            else:
                ref, bo_qua = _mot_ref_video(storage, variant, handle=tag_moi)
            if bo_qua is not None:
                skipped.append(bo_qua)
                continue
            refs.append(ref)

    for binding in bi_cat:
        kind_by_tag.setdefault(binding.tag, binding.kind)

    prompt = _doi_tag_trong_prompt(str(scene.get("prompt") or ""), tag_map,
                                   kind_by_tag, bo_tag)
    # Sec 6.2b: chi tiet day du -> prompt (chu tu do); enum -> chi la goi y tho.
    prompt = _ghep_chi_tiet(prompt, scene, 10000)

    # Luoi an toan o BIEN (spec Sec 8) — goi o DUNG MOT cho, ngay truoc khi
    # payload roi khoi ham. Nem `ValueError` la CO Y khong bat.
    bat_bien_giao_bai(prompt, refs, skipped, has_binding=has_binding)

    brief = (project.payload or {}).get("brief") or {}
    params = {
        "prompt": prompt,
        "model": "seedance-2.0-mini",
        "resolution": "480p",
        "duration": 5,
        "aspect_ratio": str(brief.get("aspect_ratio") or "16:9"),
        "generate_audio": True,
        "camera": _doan_enum(scene.get("camera"), _CAMERA_VALUES,
                             _CAMERA_TU_KHOA),
        "motion": _doan_enum(scene.get("mood"), _MOTION_VALUES, _MOTION_TU_KHOA),
        "visual_style": _doan_enum(_mo_ta_phong_cach(brief), _VISUAL_STYLE_VALUES,
                                   _STYLE_TU_KHOA),
        "refs": refs,
    }
    for khoa in ("model", "resolution", "duration", "generate_audio"):
        if overrides and overrides.get(khoa) is not None:
            params[khoa] = overrides[khoa]

    # ⛔ `tag_map`/`skipped`/`skipped_over_limit` nam NGANG voi `params`, khong
    #    TRONG no: `validate_tool_params` tu choi moi khoa la (spec Sec 6.2c) va
    #    route doi loi do thanh 422 — moi luot giao bai se vo.
    return {"prompt": prompt, "params": params, "refs": refs,
            "tag_map": tag_map, "skipped": skipped,
            "skipped_over_limit": qua_tran}


def _mot_ref_video(storage, variant, *, handle: str
                   ) -> tuple[dict | None, dict | None]:
    """Mot binding VIDEO -> `(ref, skipped)`.

    Video khong inline duoc (`apps.taovideo.refs` bat buoc URL/`asset://` cho
    video), nen ref mang mot URL co han. `try_url_for` tra `None` khi kho khong
    ky duoc URL (LocalStorage) — luc do dung duong phat tep cua app.
    """
    if not storage.exists(variant.storage_key):
        return None, {"variant_id": variant.id, "handle": handle,
                      "ly_do": "tep khong ton tai"}
    url = (storage.try_url_for(variant.storage_key, ttl_s=1800)
           or f"/prompt-ai-ommi/f/{variant.storage_key}")
    return ({"kind": "video", "url": url, "role": "reference_video",
             "handle": handle}, None)


def _mo_ta_phong_cach(brief: dict) -> str:
    """Chu tu do mo ta phong cach, de `_doan_enum` suy `visual_style`.

    Dung lai `composer.style_description()` — dung ham Pha 1 dang dung o
    `routes/handoff.py`, khong khai lai bang phong cach o day.
    """
    from apps.prompt_ai_ommi.services.composer import style_description
    return style_description(str(brief.get("style_id") or "cinematic"),
                             str(brief.get("style_custom") or ""))


# ── Pha 2: ve giao bai dung MOT lan ─────────────────────────────────────────

class HandoffError(RuntimeError):
    """Loi vong doi ve giao bai."""


class VeKhongHopLe(HandoffError):
    """Ve khong ton tai hoac khong thuoc ve nguoi goi — route tra 404."""


class VeDaDung(HandoffError):
    """`used_at` khac NULL — route tra 409."""


class VeHetHan(HandoffError):
    """Qua `expires_at` — route tra 410."""


def _co_mui_gio(dt: datetime) -> datetime:
    """SQLite tra `datetime` KHONG mui gio du cot khai `timezone=True`.

    So mot `datetime` naive voi mot aware nem `TypeError`, va do la mot 500
    chi xuat hien tren SQLite — khong tren Postgres production. Chuan hoa o
    day, mot cho.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def tao_ve(db, *, project_id: str, scene_id: str, payload: dict,
           target_app_slug: str = "taovideo") -> OmmiHandoff:
    now = datetime.now(timezone.utc)
    row = OmmiHandoff(project_id=project_id, scene_id=scene_id,
                      target_app_slug=target_app_slug, payload=payload,
                      expires_at=now + timedelta(minutes=VE_HET_HAN_PHUT))
    db.add(row)
    db.flush()
    return row


def tim_ve(db, ticket_id: str) -> OmmiHandoff | None:
    return db.get(OmmiHandoff, ticket_id)


def doc_va_tieu_ve(db, row: OmmiHandoff) -> dict:
    """Doc payload va TIEU ve trong cung mot luot.

    Dat `used_at` TRUOC khi tra ve, khong sau: ben goi co the nem giua duong,
    va mot ve doc duoc hai lan la mot ve khong dung mot lan.
    """
    if row is None:
        raise VeKhongHopLe("Ve giao bai khong hop le.")
    if row.used_at is not None:
        raise VeDaDung("Ve giao bai da duoc dung.")
    if _co_mui_gio(row.expires_at) <= datetime.now(timezone.utc):
        raise VeHetHan("Ve giao bai da het han.")
    row.used_at = datetime.now(timezone.utc)
    db.flush()
    return dict(row.payload or {})
