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
        "text": 'Xin chào, hôm nay trời rất đẹp.', "preset": "Adam"}, user_id="u") is None


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


# ─── registry + catalog: hinh dang cua `kiem_truoc` ───

def test_kiem_truoc_sai_hinh_thi_RegistryError():
    """Cung khuon voi `tuy_chon_dong` -- mot tham chieu go sai phai do NGAY
    luc `discover()`, khong doi toi luot goi dau tien."""
    from platform_core import registry as reg

    manifest = reg.AppManifest(
        slug="appthu524", display_name="x", route_prefix="/appthu524",
        job_types=("appthu524.j",), credit_cost=lambda p: 1,
        tools=(reg.ToolSpec(
            name="text.thu524", job_type="appthu524.j", description="d",
            params_schema={"p": {"type": "string"}}, returns={"content": "text"},
            kiem_truoc="khong-dung-hinh"),))
    with pytest.raises(reg.RegistryError, match="module:attribute"):
        reg._validate(manifest, set(), set(), set(), set(), set())


def test_kiem_truoc_rong_thi_hop_le():
    from platform_core import registry as reg

    manifest = reg.AppManifest(
        slug="appthu524b", display_name="x", route_prefix="/appthu524b",
        job_types=("appthu524b.j",), credit_cost=lambda p: 1,
        tools=(reg.ToolSpec(
            name="text.thu524b", job_type="appthu524b.j", description="d",
            params_schema={"p": {"type": "string"}}, returns={"content": "text"}),))
    reg._validate(manifest, set(), set(), set(), set(), set())


def test_kiem_truoc_khong_vao_to_public_dict():
    """Operational only -- giong `sync_executor`, khong bao gio ra khach."""
    from platform_core.public_api.catalog import PublicTool

    tool = PublicTool(
        name="thu.524", description="d", input_schema={}, output_schema={},
        scopes=(), app_slug="appthu524", job_type="appthu524.j",
        kiem_truoc="apps.ltt_voice.kiem_truoc_api:kiem")
    body = tool.to_public_dict()
    assert "kiem_truoc" not in body
    assert "sync_executor" not in body


# ─── tich hop: voice_id cua NGUOI KHAC phai bi tu choi TRUOC khi co gia ───
#
# Nhanh preset (cac test o tren) khong cham db (`giai_giong_kiem(None, yc)`),
# nen no khong bao gio thu duoc nhanh so huu that. Fixture nay dung SQLite tam
# (cung khuon `khach` cua `tests/test_519_ltt_voice_studio_nop_trung.py`) de
# dung mot `VoiceProfile` that, gan cho khach A, roi goi hook nhu the la
# khach B.

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
    """Khach B goi `speech.ltt` voi `voice_id` cua khach A => 400, khong hold."""
    from platform_core.public_api import invocation
    from platform_core.public_api.errors import ApiError
    import platform_core.db as dbmod

    public_id, uid_a, uid_b = hai_khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        with pytest.raises(ApiError) as e:
            invocation.kiem_truoc(db, _Tool(), {
                "text": 'Xin chào, đây là một đoạn đọc thử.',
                "voice_id": public_id}, user_id=uid_b)
        assert e.value.status == 400
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ─── IMPORTANT 1: pre-check khong duoc cham storage ───

@pytest.fixture()
def khach_co_bieu_dien(tmp_path, monkeypatch):
    """Mot khach that, so huu mot giong da co BIEU DIEN ACTIVE that (khong
    phai nhanh preset, khong phai nhanh nang-engine/lui) -- day la nhanh DUY
    NHAT ma `giai_giong()` day du se goi `tham_chieu.nap_ref_b64`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-kiem-truoc-repr.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-kiem-truoc-repr")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session()
    db = next(gen)
    try:
        a = tao_nguoi_dung(db, email="kiem-truoc-repr@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        gio = VoiceProfile(owner_id=str(a.id), ten_hien_thi="Giong co bieu dien",
                           ngon_ngu="vi", trang_thai="active")
        db.add(gio)
        db.flush()
        db.add(VoiceRepr(profile_id=gio.id, ref_id=0, trang_thai="dang_dung"))
        db.commit()
        db.refresh(gio)
        public_id, uid = gio.public_id, str(a.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    try:
        yield public_id, uid
    finally:
        dbmod.reset_engine()


def test_pre_check_giong_da_so_huu_KHONG_goi_nap_ref_b64(khach_co_bieu_dien, monkeypatch):
    """🔴 IMPORTANT 1 -- ban CHI KIEM khong duoc doc kho (R2).

    `tham_chieu.nap_ref_b64` bi thay bang mot ham NEM LOI: neu ban chi-kiem
    lo goi no, phep kiem nay do (loi thoat ra, khong phai vi mot loi nghiep
    vu that). Voi mot giong da so huu + da co bieu dien active, ban chi-kiem
    phai im lang (khong nem gi ca) MA KHONG CHAM storage.
    """
    from apps.ltt_voice import features, tham_chieu

    public_id, uid = khach_co_bieu_dien

    def _khong_duoc_goi(*a, **k):
        raise AssertionError(
            "giai_giong_kiem() da goi tham_chieu.nap_ref_b64 -- "
            "ban CHI KIEM khong duoc cham storage (D007)")

    monkeypatch.setattr(tham_chieu, "nap_ref_b64", _khong_duoc_goi)

    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        yc = features.chuan_hoa({
            "text": 'Xin chào, đây là một đoạn đọc thử.',
            "voice_id": public_id, "owner_id": uid})
        ke_hoach = features.giai_giong_kiem(db, yc)
        assert ke_hoach.bieu_dien is not None, (
            "phai tim thay bieu dien active -- neu khong thi ca nay khong "
            "con thu duong ma test dang nham toi (nang engine/lui)")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_kiem_truoc_api_kiem_KHONG_cham_storage(khach_co_bieu_dien, monkeypatch):
    """Doi chung o dung tang goi thuc te: `kiem_truoc_api.kiem` (ham
    `ToolSpec.kiem_truoc` tro toi) cung khong duoc cham storage."""
    from apps.ltt_voice import kiem_truoc_api, tham_chieu

    public_id, uid = khach_co_bieu_dien

    def _khong_duoc_goi(*a, **k):
        raise AssertionError("kiem_truoc_api.kiem() da cham storage (D007)")

    monkeypatch.setattr(tham_chieu, "nap_ref_b64", _khong_duoc_goi)

    import platform_core.db as dbmod
    gen = dbmod.get_session()
    db = next(gen)
    try:
        # Khong nem gi ca -- mot loi storage (neu co) se la RuntimeError/loi
        # mang, KHONG phai `LoiNguoiGoi`, va se thoat ra thanh 500 o /quotes
        # neu duong nay lo cham kho. `kiem()` khong duoc de dieu do xay ra.
        assert kiem_truoc_api.kiem(db, uid, {
            "text": 'Xin chào, đây là một đoạn đọc thử.',
            "voice_id": public_id}) is None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
