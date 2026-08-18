"""Nexus N3.3a — agent chỉ chạy bản cập nhật LTT đã ký (Q95).

Q95 bỏ chứng thư ký mã Windows nhưng **không** bỏ toàn vẹn bản cập nhật, vì hai
thứ đó giải hai bài toán khác nhau. Cái bị bỏ chỉ làm Windows bớt cảnh báo lúc
cài; cái được giữ là thứ quyết định **ai được chạy mã với quyền cao trên máy
khách**.

Agent chạy quyền cao. Một updater không xác minh nghĩa là ai chiếm được máy phát
hành, hoặc chen được vào đường tải, thì chiếm **mọi máy khách cùng lúc**. HTTPS
không đủ: nó bảo vệ đường truyền, không bảo vệ trước một máy phát hành đã bị
chiếm.

Ba tấn công được chốt riêng ở đây, vì mỗi cái **vượt qua** được hai cái kia:

* đổi file sau khi ký      → `sha256` bắt;
* đổi manifest cho khớp    → chữ ký bắt;
* **phát lại manifest cũ** → cả hai đều **không** bắt, chỉ phiên bản bắt.
"""
from __future__ import annotations

import base64
import json

import pytest


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@pytest.fixture()
def khoa():
    """Cặp khoá phát hành. Trả `(ky(manifest) -> str, public_b64)`."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from nexus_agent.updates import canonical_manifest

    private = ed25519.Ed25519PrivateKey.generate()
    pub = _b64e(private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))

    def ky(manifest: dict) -> str:
        return _b64e(private.sign(canonical_manifest(manifest)))

    return ky, pub


def _manifest(ky, **doi) -> dict:
    m = {"version": "1.2.0", "sha256": "a" * 64,
         "url": "https://app.lttstudios.com/dl/agent-1.2.0.exe", "size": 1024}
    m.update(doi)
    m["signature"] = ky(m)
    return m


# ── Đường hợp lệ ─────────────────────────────────────────────────────────────

def test_manifest_ky_dung_thi_qua(khoa):
    from nexus_agent.updates import verify_manifest

    ky, pub = khoa
    m = _manifest(ky)
    assert verify_manifest(m, public_key=pub) is m


# ── Ba tấn công, mỗi cái vượt được hai cái kia ───────────────────────────────

def test_doi_FILE_sau_khi_ky_bi_sha256_bat(tmp_path, khoa):
    from nexus_agent.updates import UpdateError, verify_file

    ky, _pub = khoa
    that = tmp_path / "agent.exe"
    that.write_bytes(b"ban that")

    import hashlib
    m = _manifest(ky, sha256=hashlib.sha256(b"ban that").hexdigest(),
                  size=len(b"ban that"))
    verify_file(that, m)                       # ban that thi qua

    that.write_bytes(b"ban da bi doi!!")       # ke tan cong doi file
    with pytest.raises(UpdateError):
        verify_file(that, m)


def test_doi_MANIFEST_cho_khop_file_gia_bi_chu_ky_bat(khoa):
    """Kẻ tấn công đổi cả file lẫn `sha256` trong manifest cho khớp nhau."""
    from nexus_agent.updates import UpdateError, verify_manifest

    ky, pub = khoa
    m = _manifest(ky)
    m["sha256"] = "b" * 64                     # sua sau khi da ky

    with pytest.raises(UpdateError):
        verify_manifest(m, public_key=pub)


def test_PHAT_LAI_manifest_CU_bi_phien_ban_bat(khoa):
    """Đây là tấn công mà `sha256` và chữ ký đều **không** bắt được.

    Manifest cũ từng hợp lệ thật, nên chữ ký của nó đúng mãi mãi. Phát lại nó
    đẩy máy khách về một bản có lỗ hổng đã vá — chữ ký đúng, nội dung đúng, mà
    vẫn là tấn công.
    """
    from nexus_agent.updates import UpdateError, verify_manifest

    ky, pub = khoa
    cu = _manifest(ky, version="1.0.0")

    # Khong khai ban dang chay: khong co gi de so, nen qua.
    assert verify_manifest(cu, public_key=pub)

    # Khai ban dang chay moi hon: phai tu choi.
    with pytest.raises(UpdateError) as exc:
        verify_manifest(cu, public_key=pub, phien_ban_dang_chay="1.2.0")
    assert "ha cap" in str(exc.value)


def test_cung_phien_ban_cung_bi_tu_choi(khoa):
    """Bằng nhau không phải "mới hơn": cho qua nghĩa là mở đường phát lại chính
    bản đang chạy, và đó là một vòng cập nhật vô hạn."""
    from nexus_agent.updates import UpdateError, verify_manifest

    ky, pub = khoa
    m = _manifest(ky, version="1.2.0")
    with pytest.raises(UpdateError):
        verify_manifest(m, public_key=pub, phien_ban_dang_chay="1.2.0")


def test_phien_ban_khong_parse_duoc_thi_TU_CHOI(khoa):
    """Fail-closed: một chuỗi phiên bản lạ mà được coi là mới hơn sẽ thành đường
    lách qua phép chặn hạ cấp."""
    from nexus_agent.updates import UpdateError, verify_manifest

    ky, pub = khoa
    m = _manifest(ky, version="moi-nhat")
    with pytest.raises(UpdateError):
        verify_manifest(m, public_key=pub, phien_ban_dang_chay="1.0.0")


# ── Fail-closed ──────────────────────────────────────────────────────────────

def test_agent_CHUA_ghim_khoa_thi_tu_choi_moi_ban(khoa):
    """Mặc định `RELEASE_PUBLIC_KEY` rỗng. Một agent chưa cấu hình khoá thì thà
    không cập nhật còn hơn cập nhật bừa."""
    from nexus_agent import updates

    ky, _pub = khoa
    assert updates.RELEASE_PUBLIC_KEY == "", (
        "khoa phat hanh khong duoc ghim san trong repo")

    with pytest.raises(updates.UpdateError) as exc:
        updates.verify_manifest(_manifest(ky))     # khong truyen public_key
    assert "khoa phat hanh" in str(exc.value)


def test_khoa_KHAC_thi_tu_choi(khoa):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from nexus_agent.updates import UpdateError, verify_manifest

    ky, _pub = khoa
    khac = _b64e(ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))

    with pytest.raises(UpdateError):
        verify_manifest(_manifest(ky), public_key=khac)


@pytest.mark.parametrize("thieu", ["version", "sha256", "url", "size"])
def test_thieu_truong_thi_tu_choi_chu_khong_doan(khoa, thieu):
    from nexus_agent.updates import UpdateError, verify_manifest

    ky, pub = khoa
    m = _manifest(ky)
    m[thieu] = ""
    with pytest.raises(UpdateError):
        verify_manifest(m, public_key=pub)


def test_khong_co_chu_ky_thi_tu_choi(khoa):
    from nexus_agent.updates import UpdateError, verify_manifest

    _ky, pub = khoa
    m = {"version": "1.2.0", "sha256": "a" * 64, "url": "https://x/y", "size": 1}
    with pytest.raises(UpdateError):
        verify_manifest(m, public_key=pub)


# ── Chuỗi được ký ────────────────────────────────────────────────────────────

def test_chu_ky_KHONG_phu_chinh_no(khoa):
    """`signature` phải nằm ngoài phần được ký, nếu không thì không thể tính."""
    from nexus_agent.updates import canonical_manifest

    ky, _pub = khoa
    m = _manifest(ky)
    assert b"signature" not in canonical_manifest(m)


def test_thu_tu_khoa_KHONG_lam_doi_chu_ky(khoa):
    """Hai bên serialize lệch một khoảng trắng là mọi chữ ký hợp lệ bị từ chối,
    và triệu chứng trông y hệt 'khoá sai'."""
    from nexus_agent.updates import canonical_manifest, verify_manifest

    ky, pub = khoa
    m = _manifest(ky)
    dao = dict(reversed(list(m.items())))

    assert canonical_manifest(m) == canonical_manifest(dao)
    assert verify_manifest(dao, public_key=pub)


def test_file_dung_kich_thuoc_nhung_SAI_noi_dung_bi_bat(tmp_path, khoa):
    from nexus_agent.updates import UpdateError, verify_file

    ky, _pub = khoa
    p = tmp_path / "agent.exe"
    p.write_bytes(b"12345678")
    import hashlib
    m = _manifest(ky, sha256=hashlib.sha256(b"12345678").hexdigest(), size=8)
    verify_file(p, m)

    p.write_bytes(b"87654321")                 # cung 8 byte, khac noi dung
    with pytest.raises(UpdateError):
        verify_file(p, m)
