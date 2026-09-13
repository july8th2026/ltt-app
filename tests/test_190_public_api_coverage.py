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
    "upscalevideo": (EXPOSE_V1, ("image.upscale", "video.upscale")),
    "prompt_ai_ommi": (EXPOSE_V1, ("text.prompt_package", "story.storyboard")),
    # The in-house image model (H37/Q102). EXPOSE_V1 means the contract is
    # published-shaped, not that customers can call it: the operator switch
    # `LTT_PUBLIC_API_TOOLS` still omits it, and the model itself is
    # `is_active=False` until the quality gate. Those are the gates; this entry
    # only records that the tool is *allowed* to be published.
    "anhnoibo": (EXPOSE_V1, ("image.ltt",)),

    # The in-house LANGUAGE model (H38/Q106). Same shape as `anhnoibo` one line
    # up, and the same warning applies: EXPOSE_V1 records that the tool is
    # *allowed* to be published, not that anyone can call it. Unlike `anhnoibo`
    # this one also sells through two non-job doors (`/chat/completions` and
    # `/messages` + `/responses`) — those are routes, not ToolSpecs, so they are
    # frozen in `server/api/inventory.py` rather than here.
    "ltt_llm": (EXPOSE_V1, ("text.chat",)),

    # The in-house VOICE model (Q117/Q118). Third of the in-house models, and
    # the first one whose engine runs on **this machine** rather than on host B:
    # a warm sidecar behind loopback, in its own venv. That changes where the
    # failure modes live, but it changes nothing here — EXPOSE_V1 still records
    # only that the tool is *allowed* to be published. `LTT_PUBLIC_API_TOOLS`
    # still omits it, and the service itself must be installed and running.
    "ltt_voice": (EXPOSE_V1, ("speech.ltt",)),

    # Selling virtual machines (H39). It declares **no ToolSpec at all**: a VM is
    # not a priced job with a contract-shaped input, it is a lease. Nothing about
    # the job contract applies, so it publishes nothing.
    #
    # ⚠️ Day la ghi lai TRANG THAI THAT (khong ToolSpec nao), khong phai mot quyet
    #    dinh ve san pham. Chu cua H39 muon ban no qua `/api/v1` thi phai doi muc
    #    nay va noi ro hop dong la gi.
    "vps": (DEFER, ()),

    # CU: "Priced from a caller-declared duration, with a run-time hold top-up:
    # one root cause, three tools (waves 2 and 3)."
    #
    # Cai goc do da bi go 2026-08-29 (H35.10a+b): may chu DO thoi luong luc bao
    # gia, va giu cho cua job den tu API bi NIEM PHONG o con so da ky. Nen hai
    # trong ba tool da mo.
    #
    # ⛔ Hai app con lai KHONG con chung mot ly do nua, va gop chung lai la cach
    #    nhanh nhat de ai do mo nham o luot sau:
    #    - `taoclipngan` — con thieu tran dong thoi GPU (H35.10c).
    #
    # `taovideo` roi khoi nhom do ngay 30/08 (API Expansion V2, Phase 03). Ly do
    # cu — "tap gia tri hop le doi theo model" — van dung nguyen; thu doi la ta
    # THOI PHAI publish mot tap hop nhat. Moi model cong bo `constraints` cua
    # rieng no, va to hop sai bi tu choi TRUOC `price()`.
    "taovideo": (EXPOSE_V1, ("video.generate",)),
    "autosubvideo": (EXPOSE_V1, ("video.subtitle",)),
    "taoclipngan": (MIGRATE, ()),

    # Bon App migrate tu bot legacy (Phase 08-11). DEFER vi HINH DANG san pham,
    # khong phai vi "chua lam xong":
    #   - `prompt_canh` thu tien theo tung luot goi model qua `runtime_noi_bo`,
    #     nen `credit_cost` o tang job la 0 CO CHU DICH. Hop dong quote/settle
    #     mot-vao-mot-ra khong mo ta duoc gia cua no.
    #   - `video_assembly` la mot chuoi nhieu giai doan (STT, khop clip, tach
    #     nhac, tron tieng, chay phu de) chay tren GPU; `vram_min_mb` con CHUA
    #     do that.
    #   - Ca bon chua nghiem thu E2E qua worker va chua kiem tren URL cong khai.
    "transcript": (DEFER, ()),
    "audio_pause": (DEFER, ()),
    "prompt_canh": (DEFER, ()),
    "video_assembly": (DEFER, ()),
    # An orchestrator, not a tool: publishing it publishes a runtime.
    "agent": (DEFER, ()),
    # Device management, not a priced tool: no ToolSpec and no Job. Publishing
    # it would publish a contract about *device identity*, which has to wait for
    # the relay decision and the AGPL legal review (Q93, docs/nexus/).
    "nexus": (DEFER, ()),
    # An internal *client* of three tools that are already sold (`text.chat`,
    # `image.ltt`, `speech.ltt`), reached through `platform_core.runtime_noi_bo`
    # rather than through `/api/v1`. It declares no ToolSpec, on purpose:
    # publishing it would sell the same three capabilities a second time, under
    # a second contract — and a second contract is where two price tables start
    # to drift apart. H43, docs/CHATLTT/.
    "chatltt": (DEFER, ()),

    # Video AI chay bang WanGP tren C-CLOUD (V2.1). INTERNAL_ONLY, va lan nay
    # ly do KHONG phai ke hoach ma la GIAY PHEP: `WanGP Community License 2.0`
    # §5.2(g) cam "exposing the Software to customers or end users as a paid
    # feature, add-on, or monetized backend component" neu khong co giay phep
    # thuong mai rieng. Xem `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` muc 2.
    # ⇒ Mo tool o day khong phai mot quyet dinh san pham, no la mot quyet dinh
    #   PHAP LY, va no chua duoc dua ra.
    "lttvideo": (INTERNAL_ONLY, ()),

    "qualitylab": (INTERNAL_ONLY, ()),

    # ── Auto Scan Video (pha 00-14) ──────────────────────────────────────────
    #
    # DEFER, và lý do là **hình dạng của sản phẩm**, không phải "chưa làm xong".
    # Một lần lồng tiếng không phải một lần gọi tool: nó là chín giai đoạn, mỗi
    # giai đoạn một job riêng, và bốn trong số đó có thể chạy lại độc lập. Ép nó
    # vào `ToolSpec` một-vào-một-ra sẽ hoặc là mất khả năng chạy lại một giai
    # đoạn, hoặc là bịa ra một hợp đồng mà chuỗi thật không có.
    #
    # ⛔ Và app còn `enabled=False` — nó chưa mở cho cả khách trên web, nên bàn
    #    chuyện mở qua API là bàn trước một bước.
    "auto_scan_video": (DEFER, ()),

    # Ba vỏ thi hành của CÙNG sản phẩm trên, không phải app bán được. Chúng khai
    # `surface="runtime"` + `catalog_parent="auto_scan_video"`: không thẻ
    # catalog, không mục nav, không ToolSpec. Chúng tồn tại vì quyền nhặt job
    # lọc theo APP chứ không theo `job_type` (`platform_core/jobs.py:158-164`),
    # nên mỗi làn worker phải là một thư mục riêng.
    #
    # ⚠️ Nếu một lượt sau thấy ba dòng này và định "dọn cho gọn": đừng gộp chúng
    #    vào một dòng. Sổ này chốt theo TỪNG slug trong registry, và gộp lại sẽ
    #    làm phép kiểm đỏ theo một cách chẳng nói lên điều gì.
    "asv_media": (DEFER, ()),
    "asv_gpu": (DEFER, ()),
    "asv_voice": (DEFER, ()),
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
    for slug in ("qualitylab",):
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


def test_the_removed_apps_stay_removed():
    """Bon app da bi go han khoi kho ma 2026-08-25: socialbot (Q108), roi
    kichban, mediatools, demo.

    Phep kiem cu o day chot rang app do van "dong bang dung cach". Dong bang
    khong con la mot trang thai cua he thong nay — app da di, cung voi `core/`,
    `utils/`, `server/services/` va 43 route cong khai cua no.

    Giu mot phep kiem o day chu khong xoa han: bang `DISPOSITION` phia tren la
    hop dong hai chieu voi registry, nen mot ngay ai do dua app tro lai ma quen
    phan loai no thi `test_every_app_in_the_registry_has_a_decision` se do —
    nhung no se do voi mot thong bao kho hieu. Dong nay noi thang ly do.
    """
    for da_go in ("socialbot", "kichban", "mediatools", "demo"):
        assert da_go not in _apps(), da_go
        assert da_go not in DISPOSITION, da_go


# ⏭️ `test_the_chat_app_still_has_no_job_contract` ĐÃ GỠ ở pha 07 cùng app.
#
#    `chataistudio` bị gỡ hẳn 09/09/2026: sau khi Codex biến mất nó chỉ còn
#    là bản sao thứ hai của `chatltt` (đo: 3 hội thoại · 8 tin · im từ
#    25/08). Xem `docs/AI_CLEAN_REBUILD/MIGRATION_MAP.md` §7.
#
# ⭐ Bảng `DISPOSITION` ngay trên là chỗ phép kiểm này thật sự sống: một app
#    biến mất mà quên xoá dòng của nó ở đó thì `test_every_app_is_classified`
#    đỏ. Nên bất biến *"mọi app đều có một phán quyết"* không mất người canh.


def test_the_agent_app_is_an_orchestrator_not_a_tool():
    manifest = _apps()["agent"].manifest
    assert manifest.tools == ()
    assert manifest.job_types == ("agent.advance",)
