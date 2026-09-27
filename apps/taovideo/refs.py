"""
refs.py — dựng phần tham chiếu (ảnh/video/audio) cho body ModelArk (seedance Pha 2).

Di trú trung thành từ `adapters/modelark_adapter.py` (build_content/_ref_to_part/
_provider_url/_image_role/normalize_tags):
- ảnh ≤ 8 MiB → INLINE `data:` base64 (chuẩn hoá về PNG/JPEG bằng Pillow);
- ảnh > 8 MiB / video / audio → BẮT BUỘC `asset://` (hoặc URL công khai) — không inline;
- role hợp lệ + remap legacy; @handle → tag vị trí @IMG_n/@VID_n/@AUD_n.

Ref (dict) worker nhận: {kind, url|data, role, handle}. `url` có thể là data:/http:/asset://.
"""
from __future__ import annotations

import base64
import re

from platform_core.i18n import _ as _t

MAX_INLINE_BYTES = 8 * 1024 * 1024

#: ===== TRAN TAI SAN THAM CHIEU — MOT NGUON CHAN LY =====================
#: TRAN CUNG CUA ENGINE Seedance 2.0, khong phai lua chon cua app. Nguyen van
#: ban goc (kho CHI DOC) `D:/BOT GEMINI/app/modules/seedance_video/manifest.py` dong 30:
#:
#:     "max_ref_images": 9, "max_ref_videos": 3, "max_ref_audio": 3,
#:     "max_ref_total": 12,  # Seedance 2.0 hard limits
#:
#: SAU cho cuong che deu doc tu day, khong cho nao go lai so:
#:   `routes._luu_refs` · `routes.TRAN_REF_PREFILL` · `routes._saved_refs_for_user`
#:   `routes.queue` · `jobs._reference_specs` (WORKER) · JS trong
#:   `templates/taovideo.html` (nhan qua render context / `data-tran-*`).
#:
#: ⭐ TRAN O WORKER KHONG BAO GIO DUOC THAP HON TRAN O CUA.
#: `jobs._reference_specs` chay SAU khi `/queue` da giu credit, nen mot tran
#: thap hon o do nghia la khach bi TRU TIEN roi job chet o worker — xau hon
#: han viec tu choi ngay o cua.
#:
#: ⛔ KHONG "hoa giai" voi `platform_core.public_api.invocation
#: .TRAN_MEDIA_MOT_THAM_SO = 8`. HAI CUA, HAI SO, CA HAI DUNG:
#:   · Public API qua `image_keys` (kieu `image[]`) => 8. Tran NEN TANG, vi moi
#:     phan tu la mot luot tra CSDL chay TRUOC khi co bat ky khoan tien nao.
#:     Khai o `apps/taovideo/manifest.py` dong 201, cuong che o
#:     `server/api/jobs.py`. KHONG phai tran cua engine.
#:   · `refs` (kieu json) va `saved_ref_keys` => 9/3/3/12 duoi day. Tran ENGINE.
TRAN_ANH = 9
TRAN_VIDEO = 3
TRAN_AUDIO = 3
TRAN_TONG = 12

#: Suy ra tu bon hang so tren — KHONG phai ban khai thu hai.
TRAN_THEO_LOAI = {"image": TRAN_ANH, "video": TRAN_VIDEO, "audio": TRAN_AUDIO}


def kiem_tran(kinds) -> dict:
    """Cuong che tran engine: TUNG LOAI truoc, roi TONG. Tra ve dict dem.

    `kinds` la iterable cac chuoi `image`/`video`/`audio`. Gia tri la khac
    duoc dem nhu `image` (cung quy uoc voi `routes`/`jobs`: role/kind la khong
    ro thi ve anh tham chieu).

    Nem `ValueError` voi thong diep neu DUNG con so cua loai bi vuot — mot cau
    chung ("qua nhieu tai san") khong noi cho khach biet phai bo thu gi.
    """
    dem = {"image": 0, "video": 0, "audio": 0}
    for k in kinds:
        key = str(k or "image").strip()
        dem[key if key in dem else "image"] += 1
    if dem["image"] > TRAN_ANH:
        raise ValueError(_t('Tối đa {n} ảnh tham chiếu.').format(n=TRAN_ANH))
    if dem["video"] > TRAN_VIDEO:
        raise ValueError(_t('Tối đa {n} video tham chiếu.').format(n=TRAN_VIDEO))
    if dem["audio"] > TRAN_AUDIO:
        raise ValueError(_t('Tối đa {n} audio tham chiếu.').format(n=TRAN_AUDIO))
    if sum(dem.values()) > TRAN_TONG:
        raise ValueError(
            _t('Tối đa {n} tài sản tham chiếu cho một video.').format(n=TRAN_TONG))
    return dem

VALID_IMAGE_ROLES = {"reference_image", "first_frame", "last_frame", "mask"}
_ROLE_REMAP = {"reference": "reference_image", "character": "reference_image",
               "start_frame": "first_frame", "end_frame": "last_frame"}
_TAG_PREFIX = {"image": "IMG", "video": "VID", "audio": "AUD"}


class RefError(RuntimeError):
    pass


def image_role(role: str) -> str:
    r = (role or "").strip() or "reference_image"
    r = _ROLE_REMAP.get(r, r)
    return r if r in VALID_IMAGE_ROLES else "reference_image"


def normalize_image(data: bytes) -> tuple[bytes, str]:
    """Trả (bytes, mime). Giữ nguyên nếu đã JPEG/PNG; còn lại convert PNG (Pillow)."""
    if data[:3] == b"\xff\xd8\xff":
        return data, "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data, "image/png"
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.mode else "RGB")
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue(), "image/png"


def image_to_inline(data: bytes) -> str:
    """bytes ảnh → data URL. Ném RefError nếu sau chuẩn hoá vẫn > 8 MiB (cần asset://)."""
    norm, mime = normalize_image(data)
    if len(norm) > MAX_INLINE_BYTES:
        raise RefError("anh > 8MiB — can asset:// / URL cong khai")
    b64 = base64.b64encode(norm).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _ref_to_part(ref: dict) -> dict | None:
    kind = (ref.get("kind") or "image").strip()
    url = (ref.get("url") or "").strip()
    if not url:
        return None
    if kind == "image":
        return {"type": "image_url", "image_url": {"url": url},
                "role": image_role(ref.get("role") or "")}
    if kind == "video":
        return {"type": "video_url", "video_url": {"url": url}, "role": "reference_video"}
    if kind == "audio":
        return {"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"}
    return None


def normalize_tags(prompt: str, refs: list) -> str:
    """@handle (vd @swat) → tag vị trí @IMG_n/@VID_n/@AUD_n theo thứ tự ref mỗi loại."""
    counts = {"image": 0, "video": 0, "audio": 0}
    handle_to_tag = {}
    for r in refs:
        kind = (r.get("kind") or "image").strip()
        if kind not in counts:
            continue
        counts[kind] += 1
        h = (r.get("handle") or "").strip().lstrip("@").lower()
        if h:
            handle_to_tag[h] = f"@{_TAG_PREFIX[kind]}_{counts[kind]}"
    if not handle_to_tag:
        return prompt

    def _sub(m):
        return handle_to_tag.get(m.group(1).lower(), m.group(0))
    return re.sub(r"@(\w+)", _sub, prompt)


def build_content(prompt: str, refs: list) -> list:
    """content[] = [text] + các *_url part. @tag đã chuẩn hoá vào text."""
    content = [{"type": "text", "text": normalize_tags(prompt, refs)}]
    for ref in (refs or []):
        part = _ref_to_part(ref)
        if part is not None:
            content.append(part)
    return content
