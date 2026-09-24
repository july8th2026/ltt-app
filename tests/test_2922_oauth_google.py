# -*- coding: utf-8 -*-
"""OAuth2 Google (spec §9.3) — `platform_core/oauth_google.py`, plan P5c/T3.

## Bon thu phep kiem nay giu, va vi sao tung thu dat tien

1. **`state` luu o dang BAM.** Gia tri tho song trong thanh dia chi cua trinh
   duyet, trong lich su, va trong log cua Google. Mot ban sao tho trong CSDL
   bien mot dong log thanh mot lan dang nhap.
2. **`state` dung MOT LAN.** Khong co no, mot `code` bi chup lai cung mot
   `state` con song la mot lan phat lai.
3. **PKCE S256.** ADOPT `authlib` (`create_s256_code_challenge`, RFC 7636) —
   ⛔ khong tu tinh challenge.
4. **`refresh_token` khong duoc roi vao `meta`.** `meta` la o CONG KHAI: no di
   thang ra trinh duyet qua `credential.liet_ke`.

## Doi chung

Moi phep phu dinh o day co mot phep khang dinh doi xung. Khong co chung, mot
`hoan_tat` luon nem se lam ca tep xanh.

⛔ KHONG goi mang: diem token duoc tiem qua `goi_token`. Viec tao app OAuth
   Google la viec THU CONG cua chu du an (`tools/wizard_oauth_google.sh`).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

CID = "1234.apps.googleusercontent.com"
CSECRET = "GOCSPX-bi-mat-cua-chu-du-an"
REDIRECT = "https://app.lttstudios.com/hooks/oauth/google"
ACCESS = "ya29.ACCESS-TOKEN-KHONG-DUOC-LO"
REFRESH = "1//REFRESH-TOKEN-SONG-LAU"


@pytest.fixture()
def db(tmp_path):
    import platform_core.models  # noqa: F401
    from platform_core.db import Base

    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'oauth.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    phien = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield phien
    finally:
        phien.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _cau_hinh(monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-" + "k" * 32)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)
    monkeypatch.setenv("LTT_GOOGLE_OAUTH_CLIENT_ID", CID)
    monkeypatch.setenv("LTT_GOOGLE_OAUTH_CLIENT_SECRET", CSECRET)
    monkeypatch.setenv("LTT_GOOGLE_OAUTH_REDIRECT_URI", REDIRECT)


def _tra_token(**over):
    goi = {"access_token": ACCESS, "refresh_token": REFRESH,
           "token_type": "Bearer", "expires_in": 3600,
           "scope": "https://www.googleapis.com/auth/youtube.upload"}
    goi.update(over)

    def goi_token(**_):
        return dict(goi)
    return goi_token


# ── 1. Bat dau: URL + state da bam ───────────────────────────────────────────

def test_url_uy_quyen_mang_PKCE_S256_va_dung_client_id(db):
    from platform_core import oauth_google

    url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    q = parse_qs(urlparse(url).query)
    assert urlparse(url).netloc == "accounts.google.com"
    assert q["code_challenge_method"] == ["S256"]
    assert q["client_id"] == [CID]
    assert q["redirect_uri"] == [REDIRECT]
    # ⭐ `offline` + `consent`: khong co hai tham so nay Google KHONG phat
    #    refresh token o lan cap quyen thu hai tro di.
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]
    assert q["state"] == [state]


def test_state_THO_khong_nam_trong_CSDL(db):
    from platform_core import oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    tho = db.execute(sa.text("SELECT state_hash FROM oauth_state")).scalar_one()
    assert state not in tho


def test_doi_chung_ban_BAM_cua_state_thi_CO_trong_CSDL(db):
    """Khong co phep nay, phep tren xanh ca khi `bat_dau` khong luu gi."""
    from platform_core import oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    tho = db.execute(sa.text("SELECT state_hash FROM oauth_state")).scalar_one()
    assert tho == hashlib.sha256(state.encode("utf-8")).hexdigest()


def test_pkce_verifier_khong_nam_o_dang_ro_trong_CSDL(db):
    from platform_core import oauth_google
    from platform_core import secretbox

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    tho = db.execute(
        sa.text("SELECT pkce_verifier_ma_hoa FROM oauth_state")).scalar_one()
    # Doi chung: giai ma duoc ⇒ co that mot verifier, khong phai chuoi rong.
    assert len(secretbox.giai_ma(tho)) >= 43


# ── 2. Hoan tat: mot lan, con han, dung chu ─────────────────────────────────

def test_hoan_tat_tao_credential_oauth2_va_KHONG_lo_token(db):
    from platform_core import credential, oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    c = oauth_google.hoan_tat(db, state=state, code="ma-uy-quyen",
                              goi_token=_tra_token())
    db.commit()
    assert c.kieu == "oauth2" and c.nha_cung_cap == "google"
    tho = db.execute(sa.text(
        "SELECT bi_mat_ma_hoa FROM credential")).scalar_one()
    assert ACCESS not in tho and REFRESH not in tho
    # `meta` la o CONG KHAI — no di thang ra trinh duyet.
    phang = str(credential.liet_ke(db, "u1"))
    assert ACCESS not in phang and REFRESH not in phang


def test_doi_chung_token_lay_lai_duoc_qua_lay_de_dung(db):
    from platform_core import credential, oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    c = oauth_google.hoan_tat(db, state=state, code="ma", goi_token=_tra_token())
    db.commit()
    bi_mat = credential.lay_de_dung(db, c.id, owner_id="u1")
    assert bi_mat["access_token"] == ACCESS
    assert bi_mat["refresh_token"] == REFRESH


def test_state_dung_LAN_HAI_bi_tu_choi(db):
    from platform_core import oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    oauth_google.hoan_tat(db, state=state, code="ma", goi_token=_tra_token())
    db.commit()
    with pytest.raises(oauth_google.LoiOAuth) as e:
        oauth_google.hoan_tat(db, state=state, code="ma",
                              goi_token=_tra_token())
    assert e.value.ma == "state_khong_hop_le"


def test_state_la_bi_tu_choi(db):
    from platform_core import oauth_google

    with pytest.raises(oauth_google.LoiOAuth) as e:
        oauth_google.hoan_tat(db, state="khong-he-ton-tai", code="ma",
                              goi_token=_tra_token())
    assert e.value.ma == "state_khong_hop_le"


def test_state_qua_han_bi_tu_choi(db):
    from platform_core import oauth_google
    from platform_core.models import OAuthState

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    hang = db.query(OAuthState).one()
    hang.het_han_luc = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    with pytest.raises(oauth_google.LoiOAuth) as e:
        oauth_google.hoan_tat(db, state=state, code="ma",
                              goi_token=_tra_token())
    assert e.value.ma == "state_het_han"


# ── 3. Lam moi ───────────────────────────────────────────────────────────────

def test_token_sap_het_han_duoc_LAM_MOI_truoc_khi_tra(db):
    from platform_core import credential, oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    c = oauth_google.hoan_tat(db, state=state, code="ma",
                              goi_token=_tra_token(expires_in=60))
    db.commit()
    moi = _tra_token(access_token="ya29.MOI-TINH", expires_in=3600)
    bi_mat = credential.lay_de_dung(
        db, c.id, owner_id="u1",
        lam_moi=oauth_google.bo_lam_moi(goi_token=moi))
    db.commit()
    assert bi_mat["access_token"] == "ya29.MOI-TINH"
    # ⭐ Refresh token khong duoc mat: Google khong gui lai no o luot lam moi.
    assert bi_mat["refresh_token"] == REFRESH


def test_doi_chung_token_con_han_thi_KHONG_lam_moi(db):
    """Neu khong co phep nay, `lam_moi` co the dang chay o MOI luot goi."""
    from platform_core import credential, oauth_google

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    c = oauth_google.hoan_tat(db, state=state, code="ma",
                              goi_token=_tra_token(expires_in=3600))
    db.commit()

    def _no_goi(**_):
        raise AssertionError("khong duoc goi diem token khi con han")

    bi_mat = credential.lay_de_dung(
        db, c.id, owner_id="u1",
        lam_moi=oauth_google.bo_lam_moi(goi_token=_no_goi))
    assert bi_mat["access_token"] == ACCESS


def test_invalid_grant_dat_co_can_ket_noi_lai(db):
    from platform_core import credential, oauth_google
    from platform_core.models import Credential

    _url, state = oauth_google.bat_dau(db, owner_id="u1")
    db.commit()
    c = oauth_google.hoan_tat(db, state=state, code="ma",
                              goi_token=_tra_token(expires_in=10))
    db.commit()

    def _hong(**_):
        raise oauth_google.LoiOAuth("invalid_grant", "token da bi thu hoi")

    with pytest.raises(credential.LoiCredential) as e:
        credential.lay_de_dung(db, c.id, owner_id="u1",
                               lam_moi=oauth_google.bo_lam_moi(goi_token=_hong))
    assert e.value.ma == "credential_bi_thu_hoi"
    db.commit()
    hang = db.query(Credential).filter(Credential.id == c.id).one()
    assert hang.meta.get("can_ket_noi_lai") is True


# ── 4. Don state het han ─────────────────────────────────────────────────────

def test_don_state_het_han_xoa_dung_hang_qua_han(db):
    from platform_core import oauth_google
    from platform_core.models import OAuthState

    _u1, s1 = oauth_google.bat_dau(db, owner_id="u1")
    _u2, _s2 = oauth_google.bat_dau(db, owner_id="u2")
    db.commit()
    cu = db.query(OAuthState).filter(
        OAuthState.state_hash
        == hashlib.sha256(s1.encode("utf-8")).hexdigest()).one()
    cu.het_han_luc = datetime.now(timezone.utc) - timedelta(days=2)
    db.commit()
    assert oauth_google.don_state_het_han(db) == 1
    db.commit()
    # Doi chung: hang CON HAN o lai — mot bo don xoa sach thi khong don gi ca.
    assert db.query(OAuthState).count() == 1
