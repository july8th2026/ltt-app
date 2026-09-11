"""D007 -- hook kiem-truoc cua Public API: loi nghiep vu ra 400 TRUOC khi co gia."""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


class _Tool:
    name = "speech.ltt"
    kiem_truoc = "apps.ltt_voice.kiem_truoc_api:kiem"


def test_tool_khong_khai_hook_thi_khong_doi_gi():
    from platform_core.public_api import invocation

    class T:
        name = "x.y"
    assert invocation.kiem_truoc(None, T(), {"a": 1}, user_id="u") is None


def test_lech_lan_ra_400_co_reason(monkeypatch):
    from platform_core.public_api import invocation
    from platform_core.public_api.errors import ApiError
    with pytest.raises(ApiError) as e:
        invocation.kiem_truoc(None, _Tool(), {
            "text": "The quick brown fox jumps over the lazy dog that we know.",
            "preset": "Adam"}, user_id="u")
    assert e.value.status == 400
    assert "voice_language_mismatch" in str(e.value.extra or {})


def test_hop_le_thi_im_lang():
    from platform_core.public_api import invocation
    assert invocation.kiem_truoc(None, _Tool(), {
        "text": "Xin chao, hom nay troi rat dep.", "preset": "Adam"}, user_id="u") is None


@pytest.mark.parametrize("ham", ["create_quote", "create_job"])
def test_route_goi_hook_TRUOC_khi_tinh_gia(ham):
    cay = ast.parse((GOC / "server" / "api" / "jobs.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == ham)
    thu_tu = [(n.lineno, n.func.attr) for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr in ("kiem_truoc", "price", "submit")]
    thu_tu.sort()
    ten = [t for _, t in thu_tu]
    assert "kiem_truoc" in ten and ten.index("kiem_truoc") < ten.index("price"), ten


def test_speech_ltt_KHAI_hook():
    from apps.ltt_voice.manifest import MANIFEST
    spec = next(t for t in MANIFEST.tools if t.job_type == "ltt_voice.synthesize")
    assert spec.kiem_truoc == "apps.ltt_voice.kiem_truoc_api:kiem"


# -- tich hop: voice_id cua NGUOI KHAC phai bi tu choi TRUOC khi co gia --------
#
# Nhanh preset (cac test o tren) khong cham db (`giai_giong(None, yc)`), nen no
# khong bao gio thu duoc nhanh so huu that. Fixture nay dung SQLite tam (cung
# khuon `khach` cua `tests/test_519_ltt_voice_studio_nop_trung.py`) de dung mot
# `VoiceProfile` that, gan cho khach A, roi goi hook nhu the la khach B.

@pytest.fixture()
def hai_khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-kiem-truoc.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-kiem-truoc")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        a = tao_nguoi_dung(db, email="kiem-truoc-a@test.com",
                           password="matkhau-tot-12", is_verified=True)
        b = tao_nguoi_dung(db, email="kiem-truoc-b@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        gio_a = VoiceProfile(owner_id=str(a.id), ten_hien_thi="Giong cua A",
                             ngon_ngu="vi", trang_thai="active")
        db.add(gio_a)
        db.commit()
        db.refresh(gio_a)
        public_id, uid_a, uid_b = gio_a.public_id, str(a.id), str(b.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    try:
        yield public_id, uid_a, uid_b
    finally:
        dbmod.reset_engine()


def test_voice_id_cua_nguoi_khac_ra_400_TRUOC_khi_co_gia(hai_khach):
    """Khach B goi `speech.ltt` voi `voice_id` cua khach A ⇒ 400, khong hold."""
    from platform_core.public_api import invocation
    from platform_core.public_api.errors import ApiError
    import platform_core.db as dbmod

    public_id, uid_a, uid_b = hai_khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        with pytest.raises(ApiError) as e:
            invocation.kiem_truoc(db, _Tool(), {
                "text": "Xin chao, day la mot doan doc thu.",
                "voice_id": public_id}, user_id=uid_b)
        assert e.value.status == 400
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

