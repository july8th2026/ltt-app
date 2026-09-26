"""prefill.py — payload giao bai (mot dict JSON tho) -> gia tri dien san form.

⛔ KHONG import `apps.prompt_ai_ommi` theo BAT KY chieu nao. Canh app->app la
MOT CHIEU (`prompt_ai_ommi -> taovideo`); ham o day chi nhan `payload` da la
dict — khong tu di lay, khong cham CSDL/storage. Trinh duyet la thu tu
`fetch()` payload tu `GET /prompt-ai-ommi/api/handoff/{id}/payload` (cung goc,
cung phien dang nhap) roi POST nguyen van sang `/taovideo/prefill`.

Viec stage anh/video vao `upload_sessions` nam o `routes.py`, khong o day, de
tep nay test duoc khong can fixture CSDL/storage.

⭐ `payload["params"]["camera"/"motion"/"visual_style"]` DA duoc suy tu chu tu
do o phia ommi (`handoff_stage._doan_enum()`, spec Sec 6.2b). O day chi KHOP
LAI theo bo enum (phong ho payload bi sua tay / gui sai), ⛔ KHONG tu doan enum
tu chu tu do: chuyen do lam DUNG MOT lan, phia ommi, de phep kiem "cung canh ->
cung enum" (`camera` nam trong `idempotency.key_fields`) chi phai dung o mot
noi. Doan lai o day la hai cho khai cung mot dieu, va hai cho se troi khoi nhau.
"""
from __future__ import annotations

#: Ban sao CO CHU DICH cua enum trong `apps/taovideo/manifest.py` — khong
#: import `manifest` chi de tranh vong import `routes.py` <-> `prefill.py`.
#: Neu doi enum o manifest, phai sua CA HAI noi (o day va trong
#: `apps/prompt_ai_ommi/services/handoff_stage.py`). Banh coc bat khop:
#: `tests/test_5150_taovideo_prefill_values.py::test_banh_coc_enum_khop_manifest`.
_CAMERA = {"static", "dolly_in", "tracking", "orbit", "aerial", "handheld"}
_MOTION = {"subtle", "dynamic", "cinematic"}
_VISUAL_STYLE = {"realistic", "cinematic", "anime", "product"}


def _snap(value, allowed: set[str]) -> str:
    """Trong bo thi giu, ngoai bo thi `""` — ⛔ khong doan mot gia tri khac.

    `""` la gia tri HOP LE cua ca ba enum (nghia "chua xac dinh"), nen rong hoa
    la an toan; doan bua la noi ho khach mot dieu ho khong noi.
    """
    chuoi = str(value or "").strip()
    return chuoi if chuoi in allowed else ""


def build_form_values(payload: dict) -> dict:
    """`payload` giao bai -> gia tri dien san form `/taovideo`.

    Ham THUAN: khong CSDL, khong storage, khong lay them gi o ngoai.
    """
    from apps.taovideo import models as _m

    tho = payload.get("params") if isinstance(payload, dict) else None
    params = tho if isinstance(tho, dict) else {}
    model = str(params.get("model") or "")
    duration = params.get("duration")
    return {
        "prompt": str((payload or {}).get("prompt") or "")[:10000],
        "model": model if model in _m.MODELS else _m.DEFAULT_MODEL,
        "resolution": str(params.get("resolution") or ""),
        "duration": "" if duration in (None, "") else str(duration),
        "aspect_ratio": str(params.get("aspect_ratio") or ""),
        "generate_audio": bool(params.get("generate_audio", True)),
        "camera": _snap(params.get("camera"), _CAMERA),
        "motion": _snap(params.get("motion"), _MOTION),
        "visual_style": _snap(params.get("visual_style"), _VISUAL_STYLE),
    }
