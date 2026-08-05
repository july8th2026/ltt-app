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
from platform_core.users import tao_nguoi_dung

Base.metadata.drop_all(get_engine())
Base.metadata.create_all(get_engine())
gen = get_session(); db = next(gen)
for email, amount in (("agent-a@example.com", 100), ("agent-b@example.com", 100),
                      ("agent-low@example.com", 3)):
    user = tao_nguoi_dung(db, email=email, password="Browser-test-123",
                          is_verified=True)
    credit.cap_tay(db, user.id, amount, by="browser-test")
db.commit(); db.close()

from server.app import create_app

app = create_app(env={
    "LTT_ENV": "local-server-test",
    "LTT_CONFIG_PATH": os.environ["LTT_CONFIG_PATH"],
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})

from apps.agent import jobs as agent_jobs
from apps.agent import routes as agent_routes
from platform_core.agent import executor


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


agent_routes.plan_once = _fake_plan

import apps.kichban.jobs as script_jobs
import apps.taoanh.jobs as image_jobs
import apps.thumbnail.jobs as thumbnail_jobs
import apps.taoclipngan.jobs as clip_jobs


def _script_handle(params, ctx=None):
    if ctx: ctx.progress(100, "xong")
    # kichban serves both text.script (topic -> script) and text.generate
    # (prompt -> text). Returning the script shape for both leaves
    # `$node.text` unresolvable, which is the canvas starter chain.
    if str(params.get("prompt") or "").strip():
        return {"text": "Văn bản kiểm thử từ LTT Studio.", "credit_cost": 3}
    script = {"title": params.get("topic"), "hook": "Hook kiểm thử",
              "sections": [{"title": "Phần một", "content": "Nội dung kiểm thử"}],
              "outro": "CTA kiểm thử", "description": "Mô tả kiểm thử",
              "tags": ["ltt", "test"]}
    from apps.kichban.features import derive_shot_list
    return {"script": script, "shot_list": derive_shot_list(script), "credit_cost": 3}


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


script_jobs.handle = _script_handle
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

# Chat fixture: SSE thật qua route/credit/DB, chỉ thay sidecar ngoài tiến trình.
from apps.chataistudio import routes as chat_routes

chat_routes.sc.account = lambda: {"account": {"email": "browser@test"}}
chat_routes._models_cached = lambda: [
    {"id": "gpt-5.6-sol", "display_name": "GPT-5.6 Codex"},
    {"id": "gpt-5.6-terra", "display_name": "GPT-5.6 Terra"},
]
chat_routes.sc.thread_start = lambda *_args, **_kwargs: "browser-chat-thread"


async def _chat_turn(*_args, **_kwargs):
    yield {"method": "item/agentMessage/delta", "payload": {"delta": "Xin chào "}}
    yield {"method": "item/agentMessage/delta", "payload": {"delta": "từ LTT Studio."}}
    yield {"method": "tokens", "payload": {"total": 12}}


chat_routes.sc.turn_stream = _chat_turn

_judge_counts: dict[str, int] = {}


def _advance(db, *, run_id, user_id):
    def judge(_outputs, _config):
        count = _judge_counts.get(run_id, 0)
        _judge_counts[run_id] = count + 1
        if count == 0:
            return {"pass": False, "score": .2, "fault": "structural",
                    "reason": "Cần tạo lại."}
        return {"pass": True, "score": .9, "fault": "", "reason": "Đạt."}
    return executor.tick(db, run_id=run_id, user_id=user_id, judge=judge)


agent_jobs.advance = _advance

from platform_core.job_runner import run_forever

_stop = threading.Event()
threading.Thread(target=run_forever, args=("agent-browser-worker",),
                 kwargs={"stop": _stop.is_set}, daemon=True).start()
