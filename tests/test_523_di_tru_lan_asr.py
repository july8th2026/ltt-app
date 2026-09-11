"""D003 — đo làn giọng cũ bằng ASR. Thuần + chạy khô; KHÔNG gọi ASR thật."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _m():
    s = importlib.util.spec_from_file_location("di_tru_lan_asr", GOC / "tools" / "di_tru_lan_asr.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


@pytest.mark.parametrize("do, lan_hien, ra", [
    ({"ngon_ngu": "en", "do_tin": 0.99}, "vi", ("en", "do_asr")),   # gắn nhầm, đo chắc ⇒ sửa
    ({"ngon_ngu": "vi", "do_tin": 0.97}, "vi", ("vi", "do_asr")),   # đúng, đo chắc ⇒ ghi nguồn
    ({"ngon_ngu": "en", "do_tin": 0.60}, "vi", ("", "")),           # không chắc ⇒ giữ mac_dinh_cu
    ({"ngon_ngu": "fr", "do_tin": 0.99}, "vi", ("", "")),           # ngoài làn ⇒ giữ
    ({"loi": "khong thay venv"}, "vi", ("", "")),                    # ASR hỏng ⇒ giữ
])
def test_quyet_lan(do, lan_hien, ra):
    assert _m().quyet_lan(do, lan_hien=lan_hien, nguong=0.90) == ra


def test_chay_kho_KHONG_ghi_va_dao_duoc(tmp_path, monkeypatch):
    m = _m()
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables as T
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    db.add(T.VoiceProfile(owner_id="u1", ten_hien_thi="A", ngon_ngu="vi",
                          ngon_ngu_nguon="mac_dinh_cu", trang_thai="active"))
    db.commit()
    # `**k` vì call site nay truyen `luong=` bang tu khoa (khong con kenh
    # global `_LUONG_MAC_DINH`); `text` de kiem IMPORTANT 1 khong lot vao log.
    monkeypatch.setattr(m, "_do_mot", lambda db, ho_so, **k: {
        "ngon_ngu": "en", "do_tin": 0.99, "text": "loi noi that cua khach"})

    ra = m.chay(ghi=False, nguong=0.90, nhat_ky=tmp_path / "nk.json")
    assert ra["se_doi"] == 1 and ra["da_ghi"] == 0
    assert db.query(T.VoiceProfile).one().ngon_ngu == "vi"

    ra = m.chay(ghi=True, nguong=0.90, nhat_ky=tmp_path / "nk.json")
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("en", "do_asr")
    nk = json.loads((tmp_path / "nk.json").read_text(encoding="utf-8"))
    assert nk[0]["cu"] == {"ngon_ngu": "vi", "ngon_ngu_nguon": "mac_dinh_cu"}
    # IMPORTANT 1: nhat ky KHONG duoc chua "text" (loi noi cua khach) — chi
    # dung hai khoa {ngon_ngu, do_tin} theo khuon `do:{...}` cua brief.
    assert set(nk[0]["do"].keys()) == {"ngon_ngu", "do_tin"}
    assert nk[0]["do"] == {"ngon_ngu": "en", "do_tin": 0.99}

    m.dao(tmp_path / "nk.json")
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("vi", "mac_dinh_cu")
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def test_dao_bo_qua_khi_bi_doi_sau(tmp_path, monkeypatch):
    """IMPORTANT 2: `dao()` khong duoc de len mot lan sua SAU do ASR."""
    m = _m()
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'b.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables as T
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    db.add(T.VoiceProfile(owner_id="u1", ten_hien_thi="B", ngon_ngu="vi",
                          ngon_ngu_nguon="mac_dinh_cu", trang_thai="active"))
    db.commit()
    monkeypatch.setattr(m, "_do_mot", lambda db, ho_so, **k: {
        "ngon_ngu": "en", "do_tin": 0.99})

    m.chay(ghi=True, nguong=0.90, nhat_ky=tmp_path / "nk2.json")
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("en", "do_asr")

    # Mot lan sua SAU do (vd khach tu khai lai) doi ngon_ngu_nguon — dao()
    # khong duoc de len gia tri nay.
    hs.ngon_ngu_nguon = "khai_bao"
    db.commit()

    ra = m.dao(tmp_path / "nk2.json")
    assert ra == {"da_dao": 0, "bo_qua": 1}
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("en", "khai_bao")

    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()
