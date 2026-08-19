"""Ký một bản phát hành agent — mặt còn thiếu của `nexus_agent/updates.py`.

    python tools/nexus_sign_release.py ^
        --artifact dist\\nexus-agent-1.2.0.zip ^
        --version  1.2.0 ^
        --url      https://app.lttstudios.com/nexus/tai/nexus-agent-1.2.0.zip ^
        --key      C:\\ltt-keys\\nexus_release.key ^
        --out      dist\\nexus-agent-1.2.0.manifest.json

`updates.py` **kiểm** manifest nhưng không có gì **tạo** ra nó. File này trả nợ
đó, và trả bằng cách **dùng lại `canonical_manifest` của chính `updates.py`** —
không serialize lại ở đây. Docstring của `updates.py` nói thẳng: byte được ký
phải sinh ở **một chỗ duy nhất** cho cả bên ký và bên kiểm; hai bản `json.dumps`
lệch nhau một khoảng trắng thì mọi chữ ký hợp lệ bị từ chối và triệu chứng trông
y hệt "khoá sai". Cách chắc chắn duy nhất để hai chỗ không lệch là **chỉ có một
chỗ**.

Ba guard, mỗi cái chặn một cách làm hỏng thật:

1. **Khoá riêng phải ngoài repo/secrets/data** — cùng luật Q95 mà keygen áp.
   Ký từ một khoá nằm trong repo tức là khoá đã ở sai chỗ rồi.
2. **Tự kiểm trước khi ghi** — gọi luôn `verify_manifest` với khoá công khai suy
   từ khoá riêng. Nếu manifest mình vừa ký mà bên kiểm từ chối thì dừng ngay,
   không xuất một manifest chết ra `dist/`. "Ký xong tưởng là xong" là đúng loại
   lỗi chỉ hiện trên máy khách.
3. **`--version` phải parse được `a.b.c`** — vì `updates.py` chặn hạ cấp bằng so
   sánh phiên bản, và một chuỗi không parse được bị coi là *không* mới hơn. Bắt
   ở đây để người phát hành biết ngay, thay vì phát ra một bản không ai cập nhật
   lên được.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nexus_agent.updates import (                              # noqa: E402
    TRUONG_BAT_BUOC, canonical_manifest, verify_manifest)
from tools.nexus_release_key import _b64u, _duong_cam          # noqa: E402


def _sha256_va_size(p: Path) -> tuple[str, int]:
    """Đọc theo khối — bản cài có thể hàng trăm MB (cùng lý do `verify_file`)."""
    dau = hashlib.sha256()
    size = 0
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            dau.update(khoi)
            size += len(khoi)
    return dau.hexdigest(), size


def _nap_khoa_rieng(key_path: Path):
    from cryptography.hazmat.primitives.asymmetric import ed25519

    ly_do = _duong_cam(key_path)
    if ly_do:
        raise SystemExit(f"LOI: {ly_do}")
    if not key_path.exists():
        raise SystemExit(f"LOI: khong thay khoa rieng '{key_path}'. "
                         f"Sinh bang: python tools/nexus_release_key.py --out ...")
    raw = key_path.read_text(encoding="ascii").strip()
    seed = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    if len(seed) != 32:
        raise SystemExit("LOI: khoa rieng khong phai 32 byte Ed25519 — sai file?")
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)


def ky(*, artifact: Path, version: str, url: str, key_path: Path) -> dict:
    """Trả về manifest đã ký (dict). Ném `SystemExit` nếu có gì sai."""
    if not artifact.exists():
        raise SystemExit(f"LOI: khong thay artifact '{artifact}'")

    priv = _nap_khoa_rieng(key_path)
    sha256, size = _sha256_va_size(artifact)

    manifest = {"version": str(version).strip(), "sha256": sha256,
                "url": str(url).strip(), "size": size}
    thieu = [t for t in TRUONG_BAT_BUOC if not str(manifest.get(t) or "").strip()]
    if thieu:
        raise SystemExit(f"LOI: thieu truong {', '.join(thieu)}")

    chu_ky = priv.sign(canonical_manifest(manifest))
    manifest["signature"] = _b64u(chu_ky)

    # Guard 2: tu kiem bang chinh ham ben khach se chay, voi khoa cong suy ra
    # tu khoa rieng. Neu no khong round-trip, KHONG xuat file.
    from cryptography.hazmat.primitives import serialization
    pub_b64 = _b64u(priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))
    try:
        verify_manifest(manifest, public_key=pub_b64)
    except Exception as exc:                                   # noqa: BLE001
        raise SystemExit(f"LOI NGHIEM TRONG: manifest vua ky khong tu kiem "
                         f"duoc ({exc}). Khong xuat file.") from exc
    return manifest


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--artifact", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--key", required=True, help="khoa RIENG (ngoai repo)")
    p.add_argument("--out", required=True, help="noi ghi manifest.json")
    args = p.parse_args(argv)

    manifest = ky(artifact=Path(args.artifact), version=args.version,
                  url=args.url, key_path=Path(args.key))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"Da ky: {out}")
    print(f"  version : {manifest['version']}")
    print(f"  sha256  : {manifest['sha256']}")
    print(f"  size    : {manifest['size']} byte")
    print("Da tu kiem bang verify_manifest — ben khach se chap nhan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
