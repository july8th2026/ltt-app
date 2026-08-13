"""Q92 / Prompt 14 — every app has a decision, and the code agrees with it.

`docs/PUBLIC_API/APP_DISPOSITION_V1.md` is prose, and prose drifts. This file is
the same decision expressed so the test suite can check it:

* every app in the registry appears here — adding an app fails this test until
  somebody decides what the API does with it;
* an app marked EXPOSE_V1 must actually publish the tools listed, and nothing
  else;
* every other disposition must publish **nothing**.

That makes "no app is UNKNOWN" a property of the build rather than a claim in a
document.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_core.public_api.catalog import app_may_be_public
from platform_core.registry import discover

EXPOSE_V1 = "EXPOSE_V1"
MIGRATE = "MIGRATE_CAPABILITY_THEN_EXPOSE"
DEFER = "DEFER"
INTERNAL_ONLY = "INTERNAL_ONLY"
RETIRED_NO_EXPOSE = "RETIRED_NO_EXPOSE"

GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"
DISPOSITION_DOC = (Path(__file__).parent.parent / "docs" / "PUBLIC_API" /
                   "APP_DISPOSITION_V1.md")

# The decision for every app, after waves 1-3. `tools` lists exactly what that
# app publishes on /api/v1.
DISPOSITION = {
    "thumbnail": (EXPOSE_V1, ("image.thumbnail",)),
    "taoanh": (EXPOSE_V1, ("image.generate",)),
    "upscalevideo": (EXPOSE_V1, ("image.upscale",)),
    "prompt_ai_ommi": (EXPOSE_V1, ("text.prompt_package", "story.storyboard")),

    # Priced from a caller-declared duration, with a run-time hold top-up: one
    # root cause, three tools (waves 2 and 3).
    "taovideo": (MIGRATE, ()),
    "autosubvideo": (MIGRATE, ()),
    "taoclipngan": (MIGRATE, ()),

    # No Job at all: credit is held against a message id, streamed through a
    # sidecar. Nothing about the job contract applies to it yet.
    "chataistudio": (DEFER, ()),
    # An orchestrator, not a tool: publishing it publishes a runtime.
    "agent": (DEFER, ()),

    "mediatools": (INTERNAL_ONLY, ()),
    "qualitylab": (INTERNAL_ONLY, ()),
    "demo": (INTERNAL_ONLY, ()),
    "socialbot": (INTERNAL_ONLY, ()),
    "kichban": (RETIRED_NO_EXPOSE, ()),
}


def _apps():
    return {item.manifest.slug: item for item in discover()}


def test_every_app_in_the_registry_has_a_decision():
    assert set(_apps()) == set(DISPOSITION)


def test_the_disposition_document_lists_every_app():
    """The prose and the table above must not drift apart."""
    text = DISPOSITION_DOC.read_text(encoding="utf-8")
    for slug in DISPOSITION:
        assert slug in text, slug


@pytest.mark.parametrize("slug", sorted(DISPOSITION))
def test_each_app_publishes_exactly_what_its_disposition_says(slug):
    disposition, published = DISPOSITION[slug]
    manifest = _apps()[slug].manifest
    exposed = tuple(sorted(tool.name for tool in manifest.tools
                           if tool.api_exposed))

    if disposition == EXPOSE_V1:
        assert exposed == tuple(sorted(published)), slug
    else:
        # Everything that is not EXPOSE_V1 publishes nothing at all.
        assert exposed == (), f"{slug} is {disposition} but exposes {exposed}"


def test_closed_apps_are_closed_by_construction_not_only_by_flag():
    """Belt and braces: the catalog gate refuses them even if a flag flipped."""
    for slug in ("demo", "qualitylab", "mediatools", "kichban", "socialbot"):
        item = _apps()[slug]
        assert app_may_be_public(item.manifest, error=item.error) is False, slug


def test_the_published_catalog_is_the_union_of_the_expose_v1_apps():
    published = sorted(entry["name"] for entry in
                       json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"])
    expected = sorted(name for disposition, tools in DISPOSITION.values()
                      if disposition == EXPOSE_V1 for name in tools)
    assert published == expected


def test_a_migrate_decision_names_the_blocker_in_the_document():
    """A deferral without a reason becomes "we forgot" within a month."""
    text = DISPOSITION_DOC.read_text(encoding="utf-8")
    for slug, (disposition, _tools) in DISPOSITION.items():
        if disposition not in (MIGRATE, DEFER):
            continue
        # The document must say something about this app near its name; the
        # cheapest machine-checkable version of that is: the slug appears in a
        # line that also carries its disposition.
        assert any(slug in line and disposition in line
                   for line in text.splitlines()), slug


def test_the_frozen_app_is_still_frozen():
    """Q10/Q78: socialbot is maintenance, browser-driven and OAuth-bearing."""
    manifest = _apps()["socialbot"].manifest
    assert manifest.lifecycle == "maintenance"
    assert manifest.public is False
    assert "browser" in manifest.requires
    # It has no job types and no price, so it could not be charged for anyway.
    assert manifest.job_types == () and manifest.credit_cost is None


def test_the_chat_app_still_has_no_job_contract():
    """The reason chat is deferred, checked against the code rather than memory."""
    manifest = _apps()["chataistudio"].manifest
    assert manifest.job_types == ()
    assert manifest.credit_cost is None
    source = Path("apps/chataistudio/routes.py").read_text(encoding="utf-8")
    # Credit is held against a message id, not a job — that is the gap.
    assert "credit.giu_cho" in source


def test_the_agent_app_is_an_orchestrator_not_a_tool():
    manifest = _apps()["agent"].manifest
    assert manifest.tools == ()
    assert manifest.job_types == ("agent.advance",)
