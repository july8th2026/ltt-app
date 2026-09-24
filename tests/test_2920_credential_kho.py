# -*- coding: utf-8 -*-
"""Kho credential (plan wf-v2 P5c/T1) — `platform_core/credential.py` + `secretbox`.

## Dieu phep kiem nay giu

Bi mat cua khach roi vao mot bang, va mot bang thi bi sao luu, bi `SELECT *`,
bi xuat ra CSV. Nen ba tinh chat duoi day khong phai "nice to have":

1. **Khong co ban ro trong CSDL.** Phep kiem doc cot `bi_mat_ma_hoa` **tho**
   (khong qua lop giai ma) va khang dinh chuoi bi mat khong nam trong do.
2. **Xoay khoa doc duoc ca hai doi.** `MultiFernet` (ADOPT — `cryptography`,
   ⛔ khong tu viet ma hoa): khoa moi dung dau, khoa cu van giai duoc hang
   chua xoay. Co **doi chung**: bo khoa cu ra thi giai ma PHAI that bai — nguoc
   lai thi phep "xoay khoa" xanh ca khi khong co xoay gi.
3. **Thu hoi la XOA bi mat**, khong phai mot co `enabled=False`.

## Doi chung

`test_doi_chung_*` chung minh tung phep phu dinh o tren thuc su do duoc cai no
noi: khong co chung, mot `lay_de_dung` luon nem se lam moi phep an toan xanh.
"""
from __future__ import annotations

import json
import os

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

KHOA_A = "khoa-doi-1-" + "a" * 32
KHOA_B = "khoa-doi-2-" + "b" * 32
BI_MAT = "sk-live-9f3a-KHACH-KHONG-DUOC-LO-4242"


@pytest.fixture()
def db(tmp_path):
    import platform_core.models  # noqa: F401 - dang ky moi bang
    from platform_core.db import Base

    engine = sa.create_engine(
        f"sqlite:///{(tmp_path / 'cred.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    phien = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield phien
    finally:
        phien.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _khoa_co_dinh(monkeypatch):
    """⛔ Khong de khoa suy tu dinh danh may: mot phep kiem ma hoa phai biet
    chinh xac no dang dung khoa nao, neu khong "xoay khoa" khong kiem duoc."""
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", KHOA_A)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEY_FILE", raising=False)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU_FILE", raising=False)


def _cred(db, **over):
    from platform_core import credential

    tham = dict(owner_id="u1", kieu="api_key", nha_cung_cap="http",
                ten="Khoa Stripe", bi_mat=BI_MAT)
    tham.update(over)
    c = credential.tao(db, **tham)
    db.commit()
    return c


# ── 1. Ban ro khong duoc song trong CSDL ─────────────────────────────────────

def test_bi_mat_khong_nam_o_dang_ro_trong_cot(db):
    c = _cred(db)
    tho = db.execute(sa.text(
        "SELECT bi_mat_ma_hoa FROM credential WHERE id = :i"),
        {"i": c.id}).scalar_one()
    assert BI_MAT not in tho
    assert tho  # co gi do that, khong phai chuoi rong


def test_doi_chung_bi_mat_van_lay_lai_duoc_nguyen_van(db):
    """⛔ Khong co phep nay, phep tren xanh ca khi `tao()` vut bi mat di."""
    from platform_core import credential

    c = _cred(db)
    assert credential.lay_de_dung(db, c.id, owner_id="u1") == BI_MAT


def test_liet_ke_chi_tra_preview_khong_tra_bi_mat(db):
    from platform_core import credential

    _cred(db)
    ra = credential.liet_ke(db, "u1")
    assert len(ra) == 1
    phang = json.dumps(ra, ensure_ascii=False, default=str)
    assert BI_MAT not in phang
    assert ra[0]["preview"].endswith("4242")


# ── 2. Xoay khoa (MultiFernet) ───────────────────────────────────────────────

def test_khoa_cu_van_giai_duoc_sau_khi_them_khoa_moi(db, monkeypatch):
    from platform_core import credential

    c = _cred(db)                       # ma hoa bang KHOA_A
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", KHOA_B)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", KHOA_A)
    assert credential.lay_de_dung(db, c.id, owner_id="u1") == BI_MAT


def test_doi_chung_bo_khoa_cu_ra_thi_giai_ma_THAT_BAI(db, monkeypatch):
    """Neu khong co phep nay, phep tren co the xanh vi khoa khong doi gi."""
    from platform_core import credential
    from platform_core.secretbox import SecretBoxError

    c = _cred(db)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", KHOA_B)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)
    with pytest.raises(SecretBoxError):
        credential.lay_de_dung(db, c.id, owner_id="u1")


def test_xoay_khoa_ma_hoa_lai_hang_bang_khoa_MOI(db, monkeypatch):
    from platform_core import credential
    from platform_core.secretbox import SecretBoxError

    c = _cred(db)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", KHOA_B)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", KHOA_A)
    assert credential.xoay_khoa(db) == 1
    db.commit()
    # Sau khi xoay, khoa cu mot minh KHONG con doc duoc hang nay.
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", KHOA_A)
    monkeypatch.delenv("LTT_TOKEN_ENCRYPTION_KEYS_CU", raising=False)
    with pytest.raises(SecretBoxError):
        credential.lay_de_dung(db, c.id, owner_id="u1")


# ── 3. So huu + thu hoi ──────────────────────────────────────────────────────

def test_nguoi_khac_khong_doc_duoc_credential_cua_toi(db):
    from platform_core import credential

    c = _cred(db)
    with pytest.raises(credential.LoiCredential) as e:
        credential.lay_de_dung(db, c.id, owner_id="u2")
    assert e.value.ma == "khong_thay"


def test_thu_hoi_XOA_bi_mat_chu_khong_chi_dat_co(db):
    from platform_core import credential

    c = _cred(db)
    credential.thu_hoi(db, c.id, owner_id="u1")
    db.commit()
    tho = db.execute(sa.text(
        "SELECT bi_mat_ma_hoa FROM credential WHERE id = :i"),
        {"i": c.id}).scalar_one()
    assert tho == ""
    with pytest.raises(credential.LoiCredential) as e:
        credential.lay_de_dung(db, c.id, owner_id="u1")
    assert e.value.ma == "credential_bi_thu_hoi"


def test_nhat_ky_ghi_hanh_dong_va_KHONG_ghi_bi_mat(db):
    from platform_core import credential
    from platform_core.models import CredentialNhatKy

    c = _cred(db)
    credential.lay_de_dung(db, c.id, owner_id="u1", run_id="r1", node_id="n1")
    db.commit()
    hang = db.query(CredentialNhatKy).order_by(
        CredentialNhatKy.created_at).all()
    assert [h.hanh_dong for h in hang] == ["tao", "dung"]
    assert BI_MAT not in json.dumps(
        [{k: getattr(h, k) for k in
          ("credential_id", "hanh_dong", "run_id", "node_id")} for h in hang],
        default=str)


# ── 4. Validator publish ─────────────────────────────────────────────────────

def test_ref_khong_thuoc_chu_workflow_bi_tu_choi_luc_publish(db):
    from platform_core import credential

    c = _cred(db)
    with pytest.raises(credential.LoiCredential) as e:
        credential.kiem_ref(db, c.id, owner_id="u2", kieu_cho_phep=("api_key",))
    assert e.value.ma == "khong_thay"


def test_ref_sai_KIEU_bi_tu_choi_luc_publish(db):
    from platform_core import credential

    c = _cred(db)
    with pytest.raises(credential.LoiCredential) as e:
        credential.kiem_ref(db, c.id, owner_id="u1", kieu_cho_phep=("oauth2",))
    assert e.value.ma == "kieu_sai"


def test_doi_chung_ref_dung_chu_dung_kieu_thi_QUA(db):
    from platform_core import credential

    c = _cred(db)
    credential.kiem_ref(db, c.id, owner_id="u1",
                        kieu_cho_phep=("api_key", "bearer"))


def test_kieu_la_bi_tu_choi_ngay_luc_tao(db):
    from platform_core import credential

    with pytest.raises(credential.LoiCredential) as e:
        credential.tao(db, owner_id="u1", kieu="kieu_bia_ra",
                       nha_cung_cap="http", ten="x", bi_mat="y")
    assert e.value.ma == "kieu_sai"
