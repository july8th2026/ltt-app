"""Gộp allowlist tĩnh ⊕ marketplace ở phía Node (`connector_runner/src/
piece_nap.js`) — cửa NẠP thật sự (Python chỉ ghi tệp; Node đọc và `require`).

Chạy `node` TRỰC TIẾP (không qua AppContainer) — đây là mã CỦA TA, không phải
mã bên thứ ba, nên không cần vỏ để kiểm logic gộp/từ chối. Ranh giới
AppContainer + `--ignore-scripts` thật được đo ở `test_4239`.

⛔ KHÔNG chạm mạng, KHÔNG cài gì qua npm — piece marketplace dùng ở đây là
`connector_runner/test/piece-marketplace-gia`, đã có sẵn trong kho.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
PIECE_NAP = GOC / "connector_runner" / "src" / "piece_nap.js"
FIXTURE = GOC / "connector_runner" / "test" / "piece-marketplace-gia"

NODE_DISPONIVEL = shutil.which("node") is not None
CAN_NODE = pytest.mark.skipif(not NODE_DISPONIVEL, reason="node khong co tren PATH")


def _chuan_bi_marketplace(tmp_path, *, ten="@ltt/piece-mkt-4237",
                          phien_ban="1.0.0"):
    mkt = tmp_path / "mkt"
    node_modules = mkt / "node_modules"
    dich_goi = node_modules.joinpath(*ten.split("/"))
    shutil.copytree(FIXTURE, dich_goi)
    pkg = json.loads((dich_goi / "package.json").read_text(encoding="utf-8"))
    pkg["name"] = ten
    pkg["version"] = phien_ban
    (dich_goi / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    allowlist = mkt / "allowlist.json"
    allowlist.write_text(json.dumps({
        "pieces": {ten: phien_ban},
        "mien": {ten: ["exemplo.test"]},
        "palette": {ten: {"actions": ["lam"], "triggers": []}},
    }), encoding="utf-8")
    return mkt, allowlist, ten, phien_ban


def _chay_node(script: str, env: dict) -> subprocess.CompletedProcess:
    import os
    moi = dict(os.environ)
    moi.update(env)
    return subprocess.run([shutil.which("node"), "-e", script], cwd=str(GOC),
                          env=moi, capture_output=True, text=True, timeout=30)


@CAN_NODE
def test_khong_bien_moi_truong_khong_co_piece_marketplace_nao(tmp_path):
    ra = _chay_node(
        "const p=require('./connector_runner/src/piece_nap.js');"
        "const al=p.docAllowlist();"
        "console.log(JSON.stringify({n: al._marketplace.size, "
        "tinh: Object.keys(al.pieces).length}));",
        env={"LTT_MARKETPLACE_ALLOWLIST": "", "LTT_MARKETPLACE_DIR": ""})
    assert ra.returncode == 0, ra.stderr
    out = json.loads(ra.stdout.strip())
    assert out["n"] == 0
    assert out["tinh"] == 7  # bay piece tinh trong allowlist.json build-time


@CAN_NODE
def test_gop_dung_va_nap_duoc_piece_marketplace(tmp_path):
    mkt, allowlist, ten, ban = _chuan_bi_marketplace(tmp_path)
    ra = _chay_node(
        "const p=require('./connector_runner/src/piece_nap.js');"
        f"const nap=p.napPiece({ten!r});"
        "console.log(JSON.stringify({v: nap.version, "
        "dn: nap.piece.metadata().displayName}));",
        env={"LTT_MARKETPLACE_ALLOWLIST": str(allowlist),
            "LTT_MARKETPLACE_DIR": str(mkt)})
    assert ra.returncode == 0, ra.stderr
    out = json.loads(ra.stdout.strip())
    assert out["v"] == ban
    assert out["dn"] == "Marketplace Gia"


@CAN_NODE
def test_TIEM_LOI_phien_ban_lech_bi_tu_choi(tmp_path):
    """Nếu ai đó cài đè node_modules bằng tay (bỏ qua `marketplace.py`) và để
    lại một phiên bản khác allowlist — cửa nạp vẫn phải từ chối, đúng luật
    piece tĩnh."""
    mkt, allowlist, ten, ban = _chuan_bi_marketplace(tmp_path)
    goi_dir = mkt / "node_modules" / ten.lstrip("@").split("/")[0]
    # sua package.json THAT tren dia thanh mot ban khac allowlist
    pkg_path = mkt / "node_modules"
    for part in ten.split("/"):
        pkg_path = pkg_path / part
    pkg_path = pkg_path / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg["version"] = "9.9.9"
    pkg_path.write_text(json.dumps(pkg), encoding="utf-8")

    ra = _chay_node(
        "const p=require('./connector_runner/src/piece_nap.js');"
        f"try {{ p.napPiece({ten!r}); console.log('KHONG_NEM'); }}"
        "catch(e) { console.log('NEM:' + e.message); }",
        env={"LTT_MARKETPLACE_ALLOWLIST": str(allowlist),
            "LTT_MARKETPLACE_DIR": str(mkt)})
    assert ra.returncode == 0, ra.stderr
    assert ra.stdout.strip().startswith("NEM:phien_ban_lech")


@CAN_NODE
def test_TIEM_LOI_trung_ten_voi_piece_tinh_bi_tu_choi(tmp_path):
    """Một allowlist marketplace khai một tên ĐÃ có trong allowlist tĩnh
    (vô tình hoặc cố ý) phải làm `docAllowlist()` nổ — ⛔ không được để bên
    nào âm thầm thắng."""
    mkt = tmp_path / "mkt"
    mkt.mkdir()
    allowlist = mkt / "allowlist.json"
    allowlist.write_text(json.dumps({
        "pieces": {"@activepieces/piece-slack": "0.20.0"}, "mien": {}, "palette": {},
    }), encoding="utf-8")
    ra = _chay_node(
        "const p=require('./connector_runner/src/piece_nap.js');"
        "try { p.docAllowlist(); console.log('KHONG_NEM'); }"
        "catch(e) { console.log('NEM:' + e.message); }",
        env={"LTT_MARKETPLACE_ALLOWLIST": str(allowlist), "LTT_MARKETPLACE_DIR": ""})
    assert ra.returncode == 0, ra.stderr
    assert "piece_trung_ten_tinh_va_marketplace" in ra.stdout


@CAN_NODE
def test_TIEM_LOI_thieu_thu_muc_marketplace_bi_tu_choi_khong_crash(tmp_path):
    """Allowlist khai một piece nhưng `LTT_MARKETPLACE_DIR` KHÔNG được đặt
    (mô phỏng lệch cấu hình giữa hai biến môi trường) ⇒ từ chối rõ ràng, ⛔
    không phải một `TypeError`/crash không tên."""
    mkt, allowlist, ten, ban = _chuan_bi_marketplace(tmp_path)
    ra = _chay_node(
        "const p=require('./connector_runner/src/piece_nap.js');"
        f"try {{ p.napPiece({ten!r}); console.log('KHONG_NEM'); }}"
        "catch(e) { console.log('NEM:' + e.message); }",
        env={"LTT_MARKETPLACE_ALLOWLIST": str(allowlist), "LTT_MARKETPLACE_DIR": ""})
    assert ra.returncode == 0, ra.stderr
    assert "NEM:marketplace_chua_cau_hinh_thu_muc" in ra.stdout
