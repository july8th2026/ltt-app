"""Isolated local server for P8 Playwright flows. Never uses production data/API."""
from __future__ import annotations

import os
import threading

if os.environ.get("LTT_AGENT_BROWSER_TEST") != "1":
    raise SystemExit("Set LTT_AGENT_BROWSER_TEST=1 for the isolated browser fixture.")
if "agent-browser-test" not in os.environ.get("LTT_DATABASE_URL", ""):
    raise SystemExit("Refusing to run without an agent-browser-test database path.")

from platform_core import credit
from platform_core.db import Base, get_engine, get_session
import platform_core.models  # noqa: F401
from platform_core.registry import load_app_tables
from platform_core.users import tao_nguoi_dung

# App co bang rieng (apps/<slug>/tables.py) phai duoc nap TRUOC create_all,
# neu khong fixture chay voi CSDL thieu bang va moi truy van cua app do hong.
# Production khong dinh vi dung alembic, nhung fixture browser thi dinh.
load_app_tables()

Base.metadata.drop_all(get_engine())
Base.metadata.create_all(get_engine())
gen = get_session(); db = next(gen)
for email, amount in (("agent-a@example.com", 100), ("agent-b@example.com", 100),
                      ("agent-low@example.com", 3)):
    user = tao_nguoi_dung(db, email=email, password="Browser-test-123",
                          is_verified=True)
    credit.cap_tay(db, user.id, amount, by="browser-test")
operator = tao_nguoi_dung(db, email="agent-admin@example.com",
                          password="Browser-test-123", role="admin",
                          is_verified=True)
credit.cap_tay(db, operator.id, 100, by="browser-test")
db.commit(); db.close()

from server.app import create_app

app = create_app(env={
    "LTT_ENV": "local-server-test",
    "LTT_CONFIG_PATH": os.environ["LTT_CONFIG_PATH"],
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})

from apps.agent import routes as agent_routes  # noqa: F401  (nap route)


def _fake_plan(_db, *, goal, budget_max_credit, **_kwargs):
    if "invalid" in goal.lower():
        return {"version": 1, "budget_max_credit": budget_max_credit,
                "steps": [{"id": "s1", "tool": "missing.tool", "params": {}}]}
    if "retry" in goal.lower():
        return {"version": 1, "budget_max_credit": budget_max_credit, "steps": [{
            "id": "s1", "tool": "image.generate", "after": [], "fanout": 1,
            "max_retry": 1, "on_fail": "regenerate",
            "verify": {"check": "vlm_judge", "rubric": "browser test"},
            "params": {"prompt": "browser retry image"},
        }]}
    return {"version": 1, "budget_max_credit": budget_max_credit, "steps": [{
        "id": "s1", "tool": "text.script", "after": [], "fanout": 1,
        "max_retry": 0, "on_fail": "retry_same", "verify": None,
        "params": {"topic": "Browser test script"},
    }]}


# 🗑️ 24/09/2026 (plan wf-v2 P8 Task 5): `apps/agent/routes/assistant.py` DA BI
#    XOA cung ca cum v2, nen khong con route nao goi `plan_once`. Doan gan de
#    cu da bo. `_fake_plan` giu lai vi fixture Canvas duoi day con dung no de
#    dung mot ke hoach mau — no khong con la mot lop chan giua route va planner.
#
# ⛔ Neu mot ngay nao do co route AI moi, dung chep lai doan cu: cua moi la
#    `/agent/api/v3/workflows/{id}/soan`, va no goi
#    `platform_core.agent.ke_hoach_v3.soan_draft` chu khong phai `plan_once`.

import apps.taoanh.jobs as image_jobs
import apps.thumbnail.jobs as thumbnail_jobs
import apps.taoclipngan.jobs as clip_jobs


# `_script_handle` DA GO 2026-08-25 cung app `kichban` (Q109). No gia lap hai
# tool `text.script` va `text.generate`; ca hai da bien mat khoi registry, nen
# chuoi khoi dau cu cua Canvas trong fixture nay khong con doi tuong.
#
# ⚠️ Neu kich ban Playwright nao con di qua mot node van ban thi no se hong o
#    buoc do — va hong DUNG CHO, vi nang luc do khong con ton tai.

def _image_handle(params, ctx=None):
    from apps.taoanh.manifest import unit_credit
    from platform_core.storage import get_storage
    count = max(1, min(4, int(params.get("count", 1))))
    owner_id = str(params.get("owner_id") or "browser")
    job_id = getattr(ctx, "job_id", "browser")
    source = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "server", "static", "home-covers", "image.png")
    keys = []
    for index in range(count):
        key = f"taoanh/{owner_id}/{job_id}/{index}.png"
        with open(source, "rb") as stream:
            get_storage().put(key, stream, content_type="image/png")
        keys.append(key)
    if ctx: ctx.progress(100, "xong")
    return {"image_keys": keys, "count": count,
            "credit_cost": count * unit_credit(str(params.get("model") or "")),
            "edit_mode": str(params.get("edit_mode") or "generate"),
            "prompt": str(params.get("prompt") or "")}


image_jobs.handle = _image_handle


def _thumbnail_handle(params, ctx=None):
    from apps.thumbnail.features import technical_score
    from platform_core.storage import get_storage
    count = max(1, min(4, int(params.get("count", 1))))
    prefix = f"thumbnail/{params['owner_id']}/{getattr(ctx, 'job_id', 'browser')}"
    source = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "server", "static", "home-covers", "image.png")
    keys = []; scores = []
    for index in range(count):
        key = f"{prefix}/{index}.png"
        with open(source, "rb") as stream:
            get_storage().put(key, stream, content_type="image/png")
        with open(source, "rb") as stream:
            scores.append(technical_score(stream.read()))
        keys.append(key)
    if ctx: ctx.progress(100, "xong")
    return {"image_keys": keys, "scores": scores, "count": count,
            "credit_cost": count * 5,
            "prompt": str(params.get("topic", ""))}


thumbnail_jobs.handle = _thumbnail_handle


def _clip_handle(params, ctx=None):
    from apps.taoclipngan.cost import uoc_luong_credit
    from apps.taoclipngan.features import clean_platforms, platform_copy
    from platform_core.storage import get_storage
    storage = get_storage(); source_key = str(params["video_key"])
    owner_id = str(params.get("owner_id") or "browser")
    job_id = getattr(ctx, "job_id", "browser")
    count = max(1, min(2, int(params.get("target_clip_count") or 2)))
    clips = []
    for index in range(count):
        key = f"taoclipngan/{owner_id}/{job_id}/clip_{index + 1:02d}.mp4"
        with storage.open(source_key) as stream:
            storage.put(key, stream, content_type="video/mp4")
        start = index * 4.0; end = start + 4.0
        title = f"Highlight {index + 1}"
        clips.append({"video_key": key, "title": title,
                      "score": round(.91 - index * .07, 2), "duration_s": 4,
                      "source_start": start, "source_end": end,
                      "transcript": [{"start": start, "end": end,
                                      "text": f"Transcript highlight {index + 1}",
                                      "speaker": "Speaker 1"}],
                      "score_rationale": {"overall": round(.91 - index * .07, 2),
                          "why_selected": "Hook rõ và nội dung trọn ý.",
                          "intent": "insight", "risk_level": "low", "risk_flags": [],
                          "dimensions": {"hook_strength": .9, "pacing": .82,
                                         "completeness": .86, "visual_quality": .8,
                                         "audio_quality": .84}},
                      "seo_description": "Highlight kiểm thử từ LTT Clip Studio.",
                      "hashtags": ["LTT", "Shorts"],
                      "platform_copy": platform_copy(title,
                          "Highlight kiểm thử từ LTT Clip Studio.", ["LTT", "Shorts"],
                          params.get("platforms") or [])})
    if ctx: ctx.progress(100, "xong")
    return {"clips": clips, "credit_cost": uoc_luong_credit(
        float(params.get("duration_s") or 0), str(params.get("tier") or "high_quality"), count),
        "brand_preset": str(params.get("brand_preset") or "auto"),
        "platforms": clean_platforms(params.get("platforms") or [])}


clip_jobs.handle = _clip_handle

# ⏭️ KHỐI "chat fixture" ĐÃ GỠ 09/09/2026 (AI CLEAN REBUILD V2 pha 07).
#
#    Nó tiêm `apps.chataistudio.routes` để kiểm GUI chat bằng trình duyệt.
#    App ấy đã gỡ hẳn: sau khi mất Codex nó chỉ còn là bản sao thứ hai của
#    `chatltt` (đo 09/09: 3 hội thoại, 8 tin, im từ 25/08).
#
# ⚠️ Máy chủ giả này vì thế KHÔNG còn phục vụ một màn chat nào. Muốn kiểm
#    GUI chat thì dựng fixture cho `chatltt` — nó có cửa runtime riêng và
#    một bộ test riêng (dải 800–899), nên đó là một việc có chủ, không
#    phải một dòng sửa ở đây.


# ⏭️ KHOI "_advance + judge gia" DA GO 23/09/2026 cung runtime v1 (spec §17.5).
#
#    No va `apps.agent.jobs.advance` de `tick()` cua runtime v1 nhan mot judge
#    gia (lan 1 truot, lan 2 dat), cho phep do luong "thu lai sau khi VLM judge
#    tu choi". Ca `advance` lan mo-dun kia khong con ton tai; duong chay bay gio
#    la dong co Workflow V2 (`workflow.dong_co`) — no khong nhan judge tu ngoai.

from platform_core.job_runner import run_forever
from platform_core.observability import configure_logging

_stop = threading.Event()
configure_logging(component="agent-browser-worker")
threading.Thread(target=run_forever, args=("agent-browser-worker",),
                 kwargs={"stop": _stop.is_set}, daemon=True).start()
