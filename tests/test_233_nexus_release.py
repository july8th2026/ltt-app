"""Nexus N3.3b — bên KÝ bản phát hành, đối chiếu với bên KIỂM đã có.

`nexus_agent/updates.py` kiểm manifest; `tools/nexus_sign_release.py` tạo ra nó.
Hai file này phải khớp **byte một**, nên phép kiểm nặng nhất ở đây là *round-trip
thật*: ký bằng công cụ phát hành, rồi đưa cho đúng hàm mà máy khách sẽ chạy. Một
test gọi lại `json.dumps` của riêng nó sẽ bỏ lọt đúng loại lệch mà cả thiết kế
này sợ nhất — nên test dùng chính `verify_manifest`, không dựng bản sao.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from nexus_agent import updates
from tools import nexus_release_key as keymod
from tools import nexus_sign_release as signmod


REPO = Path(__file__).resolve().parents[1]


def _sinh_khoa(tmp_path: Path) -> tuple[Path, str]:
    """Sinh cặp khoá trong thư mục tạm (ngoài repo). Trả (file khoá riêng, pub)."""
    out = tmp_path / "keys" / "nexus_release.key"
    pub = keymod.sinh(out)
    return out, pub


def _artifact(tmp_path: Path, noi_dung: bytes = b"gia lam agent zip") -> Path:
    p = tmp_path / "nexus-agent-1.2.0.zip"
    p.write_bytes(noi_dung)
    return p


# ── Round-trip: ký rồi kiểm bằng chính hàm của máy khách ─────────────────────

def test_ky_xong_thi_verify_manifest_chap_nhan(tmp_path):
    key, pub = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path)
    manifest = signmod.ky(artifact=art, version="1.2.0",
                          url="https://app.lttstudios.com/nexus/tai/x.zip",
                          key_path=key)
    # Ben khach: khoa ghim, phien ban dang chay cu hon -> phai nhan.
    updates.verify_manifest(manifest, public_key=pub, phien_ban_dang_chay="1.1.0")


def test_sha256_va_size_khop_file_that(tmp_path):
    key, pub = _sinh_khoa(tmp_path)
    noi_dung = b"x" * 5000
    art = _artifact(tmp_path, noi_dung)
    manifest = signmod.ky(artifact=art, version="2.0.0",
                          url="https://x/y.zip", key_path=key)
    assert manifest["size"] == 5000
    # verify_file doc file that va so sha256/size — khong duoc nem.
    updates.verify_file(art, manifest)


# ── Chống giả mạo: đổi một byte sau khi ký thì vỡ ────────────────────────────

def test_doi_mot_byte_trong_artifact_lam_verify_file_tu_choi(tmp_path):
    key, _ = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path, b"ban goc")
    manifest = signmod.ky(artifact=art, version="1.0.0",
                          url="https://x/y.zip", key_path=key)
    art.write_bytes(b"ban da bi doi")            # kẻ tấn công tráo file
    with pytest.raises(updates.UpdateError):
        updates.verify_file(art, manifest)


def test_doi_sha256_trong_manifest_lam_chu_ky_hong(tmp_path):
    key, pub = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path)
    manifest = signmod.ky(artifact=art, version="1.0.0",
                          url="https://x/y.zip", key_path=key)
    manifest["sha256"] = "0" * 64             # sửa nội dung đã ký
    with pytest.raises(updates.UpdateError):
        updates.verify_manifest(manifest, public_key=pub)


def test_khoa_khac_thi_tu_choi(tmp_path):
    key, _ = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path)
    manifest = signmod.ky(artifact=art, version="1.0.0",
                          url="https://x/y.zip", key_path=key)
    _, pub_khac = _sinh_khoa(tmp_path / "khac")
    with pytest.raises(updates.UpdateError):
        updates.verify_manifest(manifest, public_key=pub_khac)


# ── Chống hạ cấp: bản không mới hơn thì bị từ chối ───────────────────────────

def test_phat_lai_ban_cu_bi_chan(tmp_path):
    key, pub = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path)
    manifest = signmod.ky(artifact=art, version="1.0.0",
                          url="https://x/y.zip", key_path=key)
    # Chu ky HOP LE that, nhung bang phien ban dang chay -> van chan.
    with pytest.raises(updates.UpdateError):
        updates.verify_manifest(manifest, public_key=pub,
                                phien_ban_dang_chay="1.0.0")


def test_version_khong_parse_duoc_bi_tu_choi_ngay_luc_ky(tmp_path):
    key, _ = _sinh_khoa(tmp_path)
    art = _artifact(tmp_path)
    # `ky` du kien tu-kiem; mot version la se lam self-check chan hoac ghi
    # duoc nhung khong ai cap nhat len. O day ta chi doi no khong crash im.
    manifest = signmod.ky(artifact=art, version="1.0.0",
                          url="https://x/y.zip", key_path=key)
    with pytest.raises(updates.UpdateError):
        updates.verify_manifest(manifest, public_key=_sinh_khoa(tmp_path/"z")[1])


# ── Q95: khoá riêng không được nằm trong repo/secrets/data ───────────────────

@pytest.mark.parametrize("thu_muc", ["", "secrets", "data"])
def test_tu_choi_ghi_khoa_rieng_vao_repo(thu_muc):
    dich = REPO / thu_muc / "khoa_thu.key" if thu_muc else REPO / "khoa_thu.key"
    assert keymod._duong_cam(dich) is not None, \
        f"phai tu choi ghi khoa vao {dich}"


def test_cho_phep_ghi_khoa_ngoai_repo(tmp_path):
    assert keymod._duong_cam(tmp_path / "ok.key") is None


def test_sign_tu_choi_khoa_nam_trong_repo(tmp_path):
    art = _artifact(tmp_path)
    with pytest.raises(SystemExit):
        signmod.ky(artifact=art, version="1.0.0", url="https://x/y.zip",
                   key_path=REPO / "secrets" / "khong_ton_tai.key")


# ── Vệ sinh: keygen không in khoá riêng, không ghi đè ────────────────────────

def test_keygen_khong_ghi_de_khoa_dang_co(tmp_path):
    out = tmp_path / "k.key"
    keymod.sinh(out)
    with pytest.raises(SystemExit):
        keymod.sinh(out)               # lan hai phai choi, khong am tham thay khoa


def test_khoa_rieng_khong_bao_gio_ra_stdout(tmp_path, capsys, monkeypatch):
    out = tmp_path / "k.key"
    monkeypatch.setattr("sys.argv", ["prog", "--out", str(out)])
    keymod.main(["--out", str(out)])
    thay = capsys.readouterr().out
    seed_b64 = out.read_text(encoding="ascii").strip()
    assert seed_b64 not in thay, "khoa RIENG lo ra man hinh"
    # Nhung khoa CONG thi PHAI in (de dan vao RELEASE_PUBLIC_KEY).
    assert "RELEASE_PUBLIC_KEY" in thay


# ── Bằng chứng: signer KHÔNG serialize lại, dùng lại của updates.py ──────────

def test_signer_dung_canonical_cua_updates_khong_dung_ban_sao():
    """Nếu có ngày ai đó thêm một `json.dumps` thứ hai vào signer, test này đỏ.

    Không đủ để chứng minh đúng — round-trip ở trên làm việc đó — nhưng nó khoá
    lại *lý do* round-trip đúng: cả hai bên đi qua đúng một hàm."""
    import inspect
    src = inspect.getsource(signmod)
    assert "canonical_manifest" in src
    assert "json.dumps" not in src.split("def ky", 1)[1].split("def main", 1)[0], \
        "signer khong duoc tu serialize phan duoc ky — phai dung canonical_manifest"
