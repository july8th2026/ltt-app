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


def _script_handle(params, ctx=None):
    if ctx: ctx.progress(100, "xong")
    return {"script": {"title": params.get("topic"), "body": "Kết quả kiểm thử"}}


def _image_handle(_params, ctx=None):
    if ctx: ctx.progress(100, "xong")
    return {"image_keys": ["taoanh/browser-test/fake.png"], "prompt": "fake"}


script_jobs.handle = _script_handle
image_jobs.handle = _image_handle


def _thumbnail_handle(params, ctx=None):
    from platform_core.storage import get_storage
    count = max(1, min(4, int(params.get("count", 1))))
    prefix = f"thumbnail/{params['owner_id']}/{getattr(ctx, 'job_id', 'browser')}"
    source = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "server", "static", "home-covers", "image.png")
    keys = []
    for index in range(count):
        key = f"{prefix}/{index}.png"
        with open(source, "rb") as stream:
            get_storage().put(key, stream, content_type="image/png")
        keys.append(key)
    if ctx: ctx.progress(100, "xong")
    return {"image_keys": keys, "count": count, "credit_cost": count * 5,
            "prompt": str(params.get("topic", ""))}


thumbnail_jobs.handle = _thumbnail_handle

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
