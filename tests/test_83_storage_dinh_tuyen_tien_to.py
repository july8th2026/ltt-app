"""
W-KHO — `RoutedStorage`: vài tiền tố khoá ở đĩa máy chủ, còn lại ở backend chính.

🔴 Vì sao: bucket R2 xoá object quá ~7 ngày; nó đã xoá 56/58 tệp sinh trắc của
   29 hồ sơ giọng (đo 15/09/2026). Tệp của app chỉ máy A đọc/ghi không cần R2.

Các mệnh đề khoá ở đây:
  ① khoá mang tiền tố cục bộ KHÔNG BAO GIỜ chạm backend chính (kể cả xoá);
  ② khoá khác đi backend chính y như trước;
  ③ không khai tiền tố ⇒ `get_storage()` trả đúng `R2Storage` như cũ;
  ④ tiền tố không kết thúc bằng `/` bị từ chối (không nuốt `voiceover/`).
"""
from __future__ import annotations

import io
import pathlib

import pytest


class _ChinhGia:
    """Backend chính giả: ghi lại mọi lời gọi, có `url_for` như R2."""

    def __init__(self):
        self.goi: list = []
        self.du_lieu: dict = {}

    def put(self, key, stream, content_type="application/octet-stream"):
        from platform_core.storage import StoredFile
        self.goi.append(("put", key))
        b = stream.read()
        self.du_lieu[key] = b
        return StoredFile(key=key, size=len(b), content_type=content_type)

    def open(self, key):
        self.goi.append(("open", key))
        return io.BytesIO(self.du_lieu[key])

    def delete(self, key):
        self.goi.append(("delete", key))
        self.du_lieu.pop(key, None)

    def exists(self, key):
        self.goi.append(("exists", key))
        return key in self.du_lieu

    def size(self, key):
        return len(self.du_lieu[key])

    def url_for(self, key, ttl_s=900):
        self.goi.append(("url_for", key))
        return f"https://r2.example/{key}"

    def put_url(self, key, ttl_s=900, content_type="application/octet-stream"):
        return None

    def local_path(self, key):
        return None

    def resolve_token(self, token):
        return None

    def download_token(self, key, ttl_s=900):
        raise AssertionError("khong duoc goi")

    def promote(self, a, b, content_type="application/octet-stream"):
        raise AssertionError("khong duoc goi khi khac backend")


@pytest.fixture()
def kho(tmp_path):
    from platform_core.storage import LocalStorage, RoutedStorage
    chinh = _ChinhGia()
    cuc_bo = LocalStorage(str(tmp_path / "files"))
    return RoutedStorage(chinh=chinh, cuc_bo=cuc_bo, tien_to=("voice/",)), chinh, tmp_path


def test_khoa_cuc_bo_nam_tren_DIA_va_khong_cham_backend_chinh(kho):
    s, chinh, tmp = kho
    s.put("voice/u1/vc_1/source.wav", io.BytesIO(b"RIFF"))
    assert (tmp / "files" / "voice" / "u1" / "vc_1" / "source.wav").read_bytes() == b"RIFF"
    assert s.exists("voice/u1/vc_1/source.wav")
    with s.open("voice/u1/vc_1/source.wav") as f:
        assert f.read() == b"RIFF"
    assert s.local_path("voice/u1/vc_1/source.wav")
    assert s.url_for("voice/u1/vc_1/source.wav") is None
    s.delete("voice/u1/vc_1/source.wav")
    assert not s.exists("voice/u1/vc_1/source.wav")
    assert chinh.goi == []


def test_khoa_khac_van_di_backend_chinh(kho):
    s, chinh, tmp = kho
    s.put("anhnoibo/a.png", io.BytesIO(b"PNG"))
    assert s.url_for("anhnoibo/a.png") == "https://r2.example/anhnoibo/a.png"
    assert ("put", "anhnoibo/a.png") in chinh.goi
    assert not (tmp / "files" / "anhnoibo").exists()


def test_tien_to_khong_nuot_khoa_chi_giong_dau(kho):
    s, chinh, _ = kho
    s.put("voiceover/x.wav", io.BytesIO(b"x"))
    assert ("put", "voiceover/x.wav") in chinh.goi


def test_promote_khac_backend_chep_qua_luong(kho):
    s, chinh, tmp = kho
    chinh.du_lieu["staging/j1/tieng.wav"] = b"WAVDATA"
    s.promote("staging/j1/tieng.wav", "voice/out/u1/j1/tieng.wav")
    assert (tmp / "files" / "voice" / "out" / "u1" / "j1" / "tieng.wav").read_bytes() == b"WAVDATA"
    assert "staging/j1/tieng.wav" not in chinh.du_lieu


def test_ve_tai_cuc_bo_giai_duoc(kho):
    s, _, _ = kho
    s.put("voice/out/u1/j1/tieng.wav", io.BytesIO(b"x"))
    ve = s.download_token("voice/out/u1/j1/tieng.wav")
    assert s.resolve_token(ve) == "voice/out/u1/j1/tieng.wav"


@pytest.mark.parametrize("gia_tri, ky_vong", [
    ("", ()),
    ("voice/", ("voice/",)),
    (" voice/ , /abc/ ,voice/", ("voice/", "abc/")),
    ("voice", ()),
    ("../voice/", ()),
])
def test_doc_tien_to_tu_env(monkeypatch, gia_tri, ky_vong):
    from platform_core import storage
    monkeypatch.setenv("LTT_STORAGE_LOCAL_PREFIXES", gia_tri)
    assert storage.tien_to_cuc_bo_tu_env() == ky_vong


def test_cong_cu_chep_chi_chep_tep_thieu_hoac_lech_va_kiem_sau_ghi(tmp_path):
    """`tools/chep_tien_to_r2_ve_dia.py` — idempotent, bỏ qua tệp đã đủ."""
    import importlib.util

    from platform_core.storage import LocalStorage
    duong = pathlib.Path(__file__).resolve().parents[1] / "tools" / "chep_tien_to_r2_ve_dia.py"
    spec = importlib.util.spec_from_file_location("chep_tien_to", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    r2 = _ChinhGia()
    r2.du_lieu = {"voice/mau/A/v2.wav": b"AAAA", "voice/out/u/j/tieng.wav": b"BB",
                  "voice/u/vc/source.wav": b"CCC"}
    cuc_bo = LocalStorage(str(tmp_path / "files"))
    cuc_bo.put("voice/mau/A/v2.wav", io.BytesIO(b"AAAA"))        # đã đủ
    cuc_bo.put("voice/u/vc/source.wav", io.BytesIO(b"C"))         # lệch
    ds = [(k, len(v)) for k, v in r2.du_lieu.items()] + [("voice/", 0)]

    ke = mod.ke_hoach(ds, cuc_bo)
    assert sorted((k, ly) for k, _, ly in ke) == [
        ("voice/out/u/j/tieng.wav", "chua_co"),
        ("voice/u/vc/source.wav", "lech_kich_thuoc")]
    assert mod.thuc_hien(ke, r2, cuc_bo) == 2
    assert mod.ke_hoach(ds, cuc_bo) == []                          # chạy lại: 0
    assert not any(g[0] == "delete" for g in r2.goi)               # không xoá R2


def _env_r2(monkeypatch, tmp_path):
    monkeypatch.setenv("LTT_STORAGE", "r2")
    monkeypatch.setenv("LTT_R2_ACCOUNT_ID", "acc")
    monkeypatch.setenv("LTT_R2_ACCESS_KEY_ID", "akid")
    monkeypatch.setenv("LTT_R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("LTT_R2_BUCKET", "ltt")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))


def test_get_storage_KHONG_khai_tien_to_thi_giu_nguyen_R2(monkeypatch, tmp_path):
    from platform_core import storage
    _env_r2(monkeypatch, tmp_path)
    monkeypatch.delenv("LTT_STORAGE_LOCAL_PREFIXES", raising=False)
    storage.set_storage(None)
    try:
        assert isinstance(storage.get_storage(), storage.R2Storage)
    finally:
        storage.set_storage(None)


def test_get_storage_khai_tien_to_thi_dinh_tuyen(monkeypatch, tmp_path):
    from platform_core import storage
    _env_r2(monkeypatch, tmp_path)
    monkeypatch.setenv("LTT_STORAGE_LOCAL_PREFIXES", "voice/")
    storage.set_storage(None)
    try:
        s = storage.get_storage()
        assert isinstance(s, storage.RoutedStorage)
        assert isinstance(s.chinh, storage.R2Storage)
        assert s.la_cuc_bo("voice/mau/Adam/v2.wav")
        assert not s.la_cuc_bo("anhnoibo/x.png")
        assert str(s.cuc_bo.root).startswith(str(tmp_path / "data"))
    finally:
        storage.set_storage(None)


def _mod_dung_lai():
    import importlib.util
    duong = (pathlib.Path(__file__).resolve().parents[1] / "tools"
             / "dung_lai_giong_kho_chung.py")
    spec = importlib.util.spec_from_file_location("dung_lai_giong", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dung_lai_giong_KHOP_sha_moi_nhan():
    import hashlib
    mod = _mod_dung_lai()
    clip = b"RIFF-clip-that"
    sha = hashlib.sha256(clip).hexdigest()
    manifest = {"giong": [{"public_id": "vc_1", "tep": "vc_1.wav", "sha256": sha}]}
    viec = mod.ke_hoach([("vc_1", "u1", 7, "voice/u1/vc_1/source.wav", sha)],
                        manifest, lambda ten: clip)
    assert viec == [("vc_1", "u1", 7, "voice/u1/vc_1/source.wav", clip)]


@pytest.mark.parametrize("truong_hop", ["thieu_manifest", "tep_lech", "csdl_lech"])
def test_dung_lai_giong_LECH_la_dung_ca_luot(truong_hop):
    import hashlib
    mod = _mod_dung_lai()
    clip = b"RIFF-clip-that"
    sha = hashlib.sha256(clip).hexdigest()
    manifest = {"giong": [] if truong_hop == "thieu_manifest"
                else [{"public_id": "vc_1", "tep": "vc_1.wav", "sha256": sha}]}
    doc = (lambda ten: b"khac") if truong_hop == "tep_lech" else (lambda ten: clip)
    sha_csdl = "0" * 64 if truong_hop == "csdl_lech" else sha
    with pytest.raises(ValueError):
        mod.ke_hoach([("vc_1", "u1", 7, "voice/u1/vc_1/source.wav", sha_csdl)],
                     manifest, doc)
