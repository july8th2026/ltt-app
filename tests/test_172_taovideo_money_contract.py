"""R1 — quote ký, idempotency batch và trần thu của Seedance."""
from __future__ import annotations

import pytest

from tests.conftest import bao_dam_user


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_SESSION_SECRET", "taovideo-money-contract-test")
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'money.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); session = next(gen)
    try:
        yield session
    finally:
        session.close(); dbmod.reset_engine()


def _params(*, video: bool = False) -> dict:
    params = {
        "model": "seedance-2.0-mini", "resolution": "480p",
        "duration": 4, "aspect_ratio": "16:9",
    }
    if video:
        params["refs"] = [{"kind": "video"}]
    return params


def test_quote_khoa_user_cau_hinh_loai_ref_va_gia(monkeypatch):
    from apps.taovideo import quotes

    monkeypatch.setenv("LTT_SESSION_SECRET", "taovideo-quote-unit-test")
    token, payload = quotes.issue("u1", _params(video=True), 2, True)

    assert quotes.verify(token, "u1", _params(video=True), 2, True) == payload
    assert quotes.verify(token, "u2", _params(video=True), 2, True) is None
    assert quotes.verify(token, "u1", _params(video=False), 2, False) is None
    assert quotes.verify(token, "u1", _params(video=True), 1, True) is None
    assert quotes.verify(token + "x", "u1", _params(video=True), 2, True) is None


def test_quote_video_dung_bang_gia_manifest(monkeypatch):
    from apps.taovideo import quotes
    from apps.taovideo.manifest import MANIFEST

    monkeypatch.setenv("LTT_SESSION_SECRET", "taovideo-quote-unit-test")
    _token, payload = quotes.issue("u1", _params(video=True), 1, True)

    assert payload["has_video_input"] is True
    assert payload["unit_hold"] == MANIFEST.credit_cost(_params(video=True))


def test_submit_lai_cung_quote_khong_tao_job_hay_giu_credit_lan_hai(db):
    from apps.taovideo import quotes
    from platform_core import credit
    from platform_core.models import JOB_DONE, Job

    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 500); db.commit()
    _token, quote = quotes.issue("u1", _params(), 2, False)
    base = {**_params(), "prompt": "a test video", "owner_id": "u1", "refs": []}

    first = quotes.submit_batch(
        db, user_id="u1", quote=quote, base_params=base, fixed_seed=100)
    db.commit()
    first_ids = [job.id for job in first]
    after_first = credit.so_du(db, "u1")
    for job in first:
        job.status = JOB_DONE
    db.commit()

    replay = quotes.submit_batch(
        db, user_id="u1", quote=quote, base_params=base, fixed_seed=100)
    db.commit()

    assert [job.id for job in replay] == first_ids
    assert db.query(Job).filter_by(app_slug="taovideo").count() == 2
    assert credit.so_du(db, "u1") == after_first
    assert replay[0].params["seed"] == 100
    assert replay[1].params["seed"] == 101


def test_submit_batch_gan_bo_tham_chieu_rieng_cho_tung_variant(db):
    from apps.taovideo import quotes
    from platform_core import credit

    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 500); db.commit()
    _token, quote = quotes.issue("u1", _params(video=True), 2, True)
    groups = [
        [{"kind": "video", "storage_key": "staging/u1/a"}],
        [{"kind": "video", "storage_key": "staging/u1/b"}],
    ]
    rows = quotes.submit_batch(
        db, user_id="u1", quote=quote,
        base_params={**_params(video=True), "prompt": "p", "owner_id": "u1"},
        variant_refs=groups,
    )
    assert rows[0].params["refs"] == groups[0]
    assert rows[1].params["refs"] == groups[1]
