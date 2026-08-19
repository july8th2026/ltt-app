"""Đóng gói agent Nexus thành thư mục cài được cho máy khách (N3.3b).

    python tools/build_agent.py --version 1.2.0

Chạy PyInstaller theo `nexus_agent/packaging/nexus_agent.spec` (one-dir, không
UPX), nén kết quả thành `dist/nexus-agent-<version>.zip`, rồi in **SHA-256** để
công bố trên trang tải (Q95 bắt buộc).

**PyInstaller là công cụ DỰNG, không phải phụ thuộc máy chủ** (`N3_DONG_GOI_AGENT.md`
§5): file này chỉ import nó khi thật sự dựng, nên bộ test và máy chủ không cần
có nó. Thiếu thì báo một câu rõ ràng kèm cách cài, không stack trace.

Sau khi có zip này, ký nó bằng `tools/nexus_sign_release.py` để sinh manifest —
hai bước tách nhau vì khoá ký nằm trên **máy khác**, ngoài repo (Q95).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "nexus_agent" / "packaging" / "nexus_agent.spec"
DIST = REPO / "dist"
BUILD = REPO / "build"


def _kiem_pyinstaller() -> None:
    try:
        import PyInstaller                                     # noqa: F401
    except ImportError:
        raise SystemExit(
            "LOI: chua co PyInstaller. Day la cong cu DUNG, khong nam trong\n"
            "requirements cua may chu. Cai vao moi truong dung:\n"
            "    pip install pyinstaller\n"
            "roi chay lai.")


def _sha256(p: Path) -> str:
    dau = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            dau.update(khoi)
    return dau.hexdigest()


def _nen_thu_muc(thu_muc: Path, dich_zip: Path) -> int:
    """Nén one-dir thành zip. Trả tổng số byte đã ghi (chưa nén)."""
    tong = 0
    with zipfile.ZipFile(dich_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(thu_muc.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(thu_muc.parent))
                tong += f.stat().st_size
    return tong


def dung(version: str) -> Path:
    _kiem_pyinstaller()
    if not SPEC.exists():
        raise SystemExit(f"LOI: khong thay spec {SPEC}")

    # Don sach truoc — mot ban dung con sot lai file cu la mot ban khong tin duoc.
    for d in (BUILD, DIST / "nexus-agent"):
        if d.exists():
            shutil.rmtree(d)

    print("PyInstaller dang dung (one-dir, khong UPX)...")
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
         "--distpath", str(DIST), "--workpath", str(BUILD), str(SPEC)],
        cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(f"LOI: PyInstaller that bai (ma {r.returncode})")

    thu_muc = DIST / "nexus-agent"
    if not thu_muc.is_dir():
        raise SystemExit(f"LOI: khong thay ket qua {thu_muc}")

    zip_path = DIST / f"nexus-agent-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    _nen_thu_muc(thu_muc, zip_path)

    sha = _sha256(zip_path)
    size = zip_path.stat().st_size
    print()
    print(f"Da dong goi: {zip_path}")
    print(f"  size   : {size} byte")
    print(f"  SHA-256: {sha}")
    print()
    print("Buoc tiep: ky tren MAY KHAC (khoa ngoai repo):")
    print(f"  python tools/nexus_sign_release.py --artifact {zip_path.name} \\")
    print(f"      --version {version} --url https://app.lttstudios.com/nexus/tai/{zip_path.name} \\")
    print("      --key <duong-dan-khoa-rieng> --out <manifest.json>")
    return zip_path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--version", required=True, help="phien ban a.b.c")
    args = p.parse_args(argv)
    # Version phai parse duoc, khong thi ban vua dung khong ai cap nhat len.
    try:
        tuple(int(x) for x in args.version.split("."))
    except ValueError:
        raise SystemExit(f"LOI: version '{args.version}' khong phai dang a.b.c")
    dung(args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
