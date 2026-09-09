"""
H8 — bộ máy APIKEYS: mã hoá secret, CRUD, Provider Registry, allocator.

Chạy trên SQLite tạm. Khoá các tính chất tiền/bảo mật:
- credential mã hoá at-rest, không lộ thô; chỉ preview 4 số cuối;
- allocator chọn key theo priority, bỏ cooldown/disabled, lọc category/model;
- phân loại lỗi: 401 disable sau 5 lần, 429 cooldown, 4xx không phạt.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'ak.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


# ── secretbox ────────────────────────────────────────────────────────────────

def test_secretbox_round_trip(monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "abc-material-xyz-123")
    from platform_core import secretbox
    tok = secretbox.ma_hoa("AIzaSECRET12345")
    assert tok != "AIzaSECRET12345" and "AIzaSECRET12345" not in tok
    assert secretbox.giai_ma(tok) == "AIzaSECRET12345"
    assert secretbox.preview("AIzaSECRET12345") == "...2345"


def test_secretbox_sai_khoa_nem(monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-1")
    from platform_core import secretbox
    tok = secretbox.ma_hoa("bi-mat")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-2-khac")
    with pytest.raises(secretbox.SecretBoxError):
        secretbox.giai_ma(tok)


# ── CRUD + mã hoá ────────────────────────────────────────────────────────────

def test_tao_key_ma_hoa_va_preview(db):
    from platform_core import api_keys
    from platform_core.models import APIKEY_CAT_IMAGE
    k = api_keys.tao_key(db, provider="gemini", credential="AIzaSUPERSECRET9999",
                         name="g1", categories=[APIKEY_CAT_IMAGE])
    db.commit()
    assert "AIzaSUPERSECRET9999" not in k.credential_enc      # đã mã hoá
    assert k.key_preview == "...9999"
    assert api_keys.lay_credential(db, k) == "AIzaSUPERSECRET9999"   # giải mã đúng


def test_category_sai_bi_tu_choi(db):
    from platform_core import api_keys
    with pytest.raises(api_keys.ApiKeyError):
        api_keys.tao_key(db, provider="gemini", credential="x",
                         categories=["superpower"])


def test_liet_ke_loc(db):
    from platform_core import api_keys
    from platform_core.models import APIKEY_CAT_CHAT, APIKEY_CAT_VIDEO
    api_keys.tao_key(db, provider="gemini", credential="k1", categories=[APIKEY_CAT_CHAT])
    api_keys.tao_key(db, provider="byteplus", credential="k2", categories=[APIKEY_CAT_VIDEO])
    db.commit()
    assert len(api_keys.liet_ke(db)) == 2
    assert len(api_keys.liet_ke(db, provider="gemini")) == 1
    assert len(api_keys.liet_ke(db, category=APIKEY_CAT_VIDEO)) == 1


def test_dat_credential_doi_preview(db):
    from platform_core import api_keys
    k = api_keys.tao_key(db, provider="gemini", credential="old-key-1111"); db.commit()
    api_keys.dat_credential(db, k, "new-key-2222"); db.commit()
    assert k.key_preview == "...2222"
    assert api_keys.lay_credential(db, k) == "new-key-2222"


# ── Provider Registry ────────────────────────────────────────────────────────

def test_provider_registry_co_5_provider():
    from platform_core import providers
    ids = set(providers.provider_ids())
    assert {"gemini", "apiai", "cheapkeyai", "byteplus", "plenx"} <= ids


def test_provider_auth_style_dung():
    """Mỗi nhà cung cấp **còn sống** phải khai một cách xác thực hợp lệ.

    ⭐ Bản cũ ghim tay ba dòng (`gemini`, `apiai`, `plenx`) — đúng **ba** cái mà
       AI CLEAN REBUILD V2 đã cho nghỉ ngày 10/09/2026, và cách xác thực chính
       là thứ chiến dịch phải xoá. Ban viết lại này **không** đổi ba dòng đó
       thành ba dòng khác — nó chuyển sang một mệnh đề **bất biến với tập
       hợp**, nên nó còn đúng khi ai đó thêm hay bớt một nhà cung cấp.
    """
    from platform_core import providers

    hop_le = {providers.AUTH_QUERY_KEY, providers.AUTH_BEARER,
              providers.AUTH_X_API_KEY}
    song = [p for p in providers.REGISTRY.values() if p.is_active]
    assert song, "registry khong con nha cung cap nao song - kiem lai tien de"
    for p in song:
        assert p.auth_style in hop_le, (
            f"{p.id} khai auth_style la {p.auth_style!r}")

    # ⚠️ KHÔNG chốt "còn sống ⇒ có `base_url`". Bản nháp của phép kiểm này có
    #    dòng ấy, và nó **đỏ ngay** ở `ltt_image`/`ltt_llm`: hai model nhà cố ý
    #    để `base_url` rỗng vì địa chỉ máy B đến từ biến môi trường
    #    (`LTT_RENDER_BASE_URL`, `LTT_LLM_BASE_URL`), không hardcode trong kho.
    #    Một mệnh đề nghe hợp lý mà sai với chính dữ liệu nó canh.

    # ⛔ VẾ thứ hai, và nó mới là vế chiến dịch cần: một nhà cung cấp đã nghỉ
    #    phải **không còn mang cách gọi nào**. Thiếu vế này thì một bản "đã xoá"
    #    vẫn có thể giữ nguyên `base_url` và `auth_style` mà không ai biết.
    nghi = [p for p in providers.REGISTRY.values() if not p.is_active]
    assert nghi, "khong con nha cung cap nao da nghi - kiem lai tien de"
    for p in nghi:
        assert not p.base_url, f"{p.id} da nghi ma con base_url"
        assert not p.auth_style, f"{p.id} da nghi ma con auth_style"
        assert not p.models, f"{p.id} da nghi ma con {len(p.models)} model"

    assert providers.get("byteplus").async_poll is True


def test_models_for_loc_category():
    """`models_for` lọc đúng theo category.

    ⭐ Bản cũ đo bằng model ảnh của Gemini. Sau 10/09/2026 không còn model nào
       ở đó nữa — nhưng thứ phep kiểm này **muốn** chứng minh là *hàm lọc có
       chạy đúng không*, chứ không phải *Gemini có model nào không*. Đổi sang
       một nhà cung cấp còn sống thì mệnh đề cũ được giữ nguyên.
    """
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_IMAGE, APIKEY_CAT_VIDEO

    vids = providers.models_for("byteplus", category=APIKEY_CAT_VIDEO)
    assert vids, "byteplus phai co model video"
    assert all(APIKEY_CAT_VIDEO in m.categories for m in vids)

    # Lọc theo một category **không** thuộc về nó thì phải rỗng — đây là nửa
    # còn lại của "lọc đúng", và bản cũ không có nửa này.
    assert providers.models_for("byteplus", category=APIKEY_CAT_IMAGE) == []

    # Nhà cung cấp đã nghỉ thì không còn model nào ở bất kỳ category nào.
    assert providers.models_for("gemini", category=APIKEY_CAT_IMAGE) == []


def test_go_mot_provider_KHONG_lam_job_cu_mat_id_model():
    """⭐ Phép kiểm này thay cho `test_gemini_image_registry_uses_stable_ids…`,
    và nó **đổi câu hỏi** chứ không đổi con số.

    Bản cũ chốt rằng registry Gemini có đúng những model nào và alias nào phân
    giải ra đâu. AI CLEAN REBUILD V2 (10/09/2026) đã xoá toàn bộ tám `ModelInfo`
    ấy, nên bản cũ không còn *sai* — nó **không còn chủ đề**.

    Nhưng bên trong nó có một tính chất đáng giữ, và giữ nó mới là việc: **xoá
    một nhà cung cấp không được làm một job cũ mất id model của nó.** Job nằm
    trong CSDL mang chuỗi `gemini-3-pro-image`; trang lịch sử phải render được.

    ⚠️ Và một mất mát có thật, ghi ra thay vì giấu: alias
       `gemini-3.1-flash-image-preview` → `gemini-3.1-flash-image` **không còn
       phân giải** nữa, vì bảng alias sống trong chính các `ModelInfo` đã xoá.
       Job cũ dùng tên preview nay đọc ra chính tên preview. Đó là nhãn, không
       phải dữ liệu — nhưng nó là một thay đổi, nên nó phải nằm trong một phép
       kiểm chứ không nằm trong trí nhớ ai đó.
    """
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_IMAGE

    assert providers.models_for("gemini", APIKEY_CAT_IMAGE) == []
    assert providers.da_ngung("gemini") is True

    # Tính chất SỐNG SÓT: id không tra được thì trả về chính nó.
    for cu in ("gemini-3-pro-image", "gemini-2.5-flash-image",
               "gemini-3.1-flash-image-preview", "unknown-model"):
        assert providers.resolve_model_id(cu) == cu, (
            f"job cu mang {cu!r} se khong render duoc")


def test_public_model_catalog_aggregates_routing_without_secrets():
    """⭐ Bản cũ ghim tay `{"byteplus", "plenx"}`. Sau khi PLENX nghỉ, con số ấy
    sai — nhưng thay `{"byteplus"}` vào chỗ đó chỉ dời cùng một điểm gãy sang
    lần sau.

    Mệnh đề thật là: **catalog gom đúng những nhà cung cấp CÒN SỐNG đang phục
    vụ model ấy** — suy ra từ registry, nên nó không trôi. Và nó **khó xanh
    hơn** bản cũ: bản cũ chỉ đúng cho một model, bản này đúng cho **mọi** model
    trong catalog.
    """
    from platform_core import providers

    catalog = providers.model_catalog()
    assert catalog, "catalog rong - kiem lai tien de"

    for muc in catalog:
        mong = {p.id for p in providers.REGISTRY.values()
                if p.is_active and any(m.id == muc["id"] for m in p.models)}
        assert {x["id"] for x in muc["providers"]} == mong, (
            f"catalog cua {muc['id']} lech voi registry")
        # Nhà cung cấp đã nghỉ không được lọt vào bất kỳ mục nào.
        for x in muc["providers"]:
            assert not providers.da_ngung(x["id"]), (
                f"{muc['id']} van chao {x['id']} - nha cung cap da nghi")

    seedance = next(m for m in catalog if m["id"] == "seedance-2.0")
    assert seedance["capabilities"]["durations"]
    assert "base_url" not in seedance and "credential" not in str(catalog).lower()


# ── Allocator ────────────────────────────────────────────────────────────────

def test_lay_key_chon_theo_priority(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_IMAGE
    api_keys.tao_key(db, provider="gemini", credential="low", name="low",
                     categories=[APIKEY_CAT_IMAGE], priority=10)
    hi = api_keys.tao_key(db, provider="gemini", credential="hi", name="hi",
                          categories=[APIKEY_CAT_IMAGE], priority=99)
    db.commit()
    chon = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE)
    assert chon.id == hi.id and chon.total_requests == 1


def test_lay_key_loc_category_va_model(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_IMAGE
    api_keys.tao_key(db, provider="gemini", credential="k",
                     categories=[APIKEY_CAT_IMAGE],
                     supported_models=["gemini-2.5-flash-image"]); db.commit()
    # model không nằm trong supported_models -> không có key
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE, model="khac")
    # model khớp -> chọn được
    assert api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE,
                            model="gemini-2.5-flash-image") is not None


def test_429_dat_cooldown_va_bo_qua(db):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_pool.danh_dau_loi(db, k, http_status=429, retry_after_s=120); db.commit()
    from platform_core.models import APIKEY_COOLDOWN
    assert k.status == APIKEY_COOLDOWN
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini")      # đang cooldown -> bỏ qua


def test_401_disable_sau_5_lan(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_DISABLED
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    for _ in range(5):
        api_pool.danh_dau_loi(db, k, http_status=401)
    db.commit()
    assert k.status == APIKEY_DISABLED and k.auth_error_count == 5


def test_4xx_khong_phat_key(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ACTIVE
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_pool.danh_dau_loi(db, k, http_status=400, message="bad request cua ta")
    db.commit()
    assert k.status == APIKEY_ACTIVE and k.error_count == 0   # không phạt


def test_thanh_cong_reset_loi(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ACTIVE
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_pool.danh_dau_loi(db, k, http_status=500)      # 5xx -> error_count++
    api_pool.danh_dau_thanh_cong(db, k); db.commit()
    assert k.error_count == 0 and k.total_success == 1 and k.status == APIKEY_ACTIVE


# ── H8.8 Telemetry rpm/tpm/token ──────────────────────────────────────────────
def test_cua_so_reset_sau_60s(db):
    from datetime import timedelta, timezone, datetime
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_pool.lay_key(db, "gemini")            # window_requests = 1
    assert k.window_requests == 1
    # Giả lập cửa sổ đã cũ >60s -> lần chọn sau phải reset rồi đếm lại từ 1.
    k.window_start = datetime.now(timezone.utc) - timedelta(seconds=61); db.commit()
    api_pool.lay_key(db, "gemini")
    assert k.window_requests == 1 and k.total_requests == 2


def test_rpm_limit_chan_chon_key(db):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    k.rpm_limit = 2; db.commit()
    api_pool.lay_key(db, "gemini")            # 1
    api_pool.lay_key(db, "gemini")            # 2 -> chạm trần
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini")        # bị rate-cap trong cửa sổ


def test_ke_toan_token_va_tpm(db):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_pool.lay_key(db, "gemini")
    api_pool.danh_dau_thanh_cong(db, k, tokens=100); db.commit()
    assert k.total_tokens == 100 and k.window_tokens == 100
    api_pool.danh_dau_thanh_cong(db, k, tokens=50); db.commit()
    assert k.total_tokens == 150 and api_pool.tpm(k) == 150
    # tpm_limit chặn: đặt trần 150, đã dùng 150 -> hết quota token
    k.tpm_limit = 150; db.commit()
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini")


# ── H8.9 Cascade đa-provider ──────────────────────────────────────────────────
def test_cascade_rot_sang_provider_khac(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_CHAT
    g = api_keys.tao_key(db, provider="gemini", credential="g",
                         categories=[APIKEY_CAT_CHAT])
    a = api_keys.tao_key(db, provider="apiai", credential="a",
                         categories=[APIKEY_CAT_CHAT]); db.commit()
    # Đẩy gemini vào cooldown -> cascade phải rớt sang apiai.
    api_pool.danh_dau_loi(db, g, http_status=429, retry_after_s=300); db.commit()
    chon = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                             thu_tu_provider=["gemini", "apiai"])
    assert chon.id == a.id


def test_cascade_ton_trong_thu_tu_provider(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_CHAT
    g = api_keys.tao_key(db, provider="gemini", credential="g",
                         categories=[APIKEY_CAT_CHAT], priority=100)
    a = api_keys.tao_key(db, provider="apiai", credential="a",
                         categories=[APIKEY_CAT_CHAT], priority=100); db.commit()
    assert api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                             thu_tu_provider=["apiai", "gemini"]).id == a.id
    assert api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                             thu_tu_provider=["gemini", "apiai"]).id == g.id


def test_cascade_loc_model_xuyen_provider(db):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_CHAT
    g = api_keys.tao_key(db, provider="gemini", credential="g",
                         categories=[APIKEY_CAT_CHAT], supported_models=["m1"])
    a = api_keys.tao_key(db, provider="apiai", credential="a",
                         categories=[APIKEY_CAT_CHAT], supported_models=["m2"]); db.commit()
    assert api_pool.chon_key(db, category=APIKEY_CAT_CHAT, model="m2").id == a.id
    assert api_pool.chon_key(db, category=APIKEY_CAT_CHAT, model="m1").id == g.id


def test_cascade_can_het_raise(db):
    from platform_core import api_pool
    from platform_core.models import APIKEY_CAT_VIDEO
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.chon_key(db, category=APIKEY_CAT_VIDEO)


# ── H8.10 Làm mới model tự động ───────────────────────────────────────────────
def test_parse_models_openai():
    from platform_core import providers_live
    from platform_core.providers import AUTH_BEARER
    data = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}
    assert providers_live.parse_models(data, AUTH_BEARER) == ["gpt-4o", "gpt-4o-mini"]


def test_parse_models_gemini():
    from platform_core import providers_live
    from platform_core.providers import AUTH_QUERY_KEY
    data = {"models": [{"name": "models/gemini-2.5-flash"},
                       {"name": "models/gemini-2.5-flash-image"}]}
    assert providers_live.parse_models(data, AUTH_QUERY_KEY) == [
        "gemini-2.5-flash", "gemini-2.5-flash-image"]


def test_lay_models_song_khong_endpoint_nem():
    from platform_core import providers, providers_live
    with pytest.raises(providers_live.ProviderLiveError):
        providers_live.lay_models_song(providers.get("plenx"), "pk_x")  # video, không có endpoint


def test_cap_nhat_supported_models_khu_trung(db):
    from platform_core import api_keys
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    api_keys.cap_nhat_supported_models(db, k, ["x", "x", "y", "", " z "]); db.commit()
    assert k.supported_models == ["x", "y", "z"]
