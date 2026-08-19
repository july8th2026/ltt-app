"""Sinh cặp khoá phát hành cho agent Nexus — phần còn nợ của Q95.

    python tools/nexus_release_key.py --out C:\\ltt-keys\\nexus_release.key

Sinh **một lần**. Khoá công khai in ra màn hình để dán vào `RELEASE_PUBLIC_KEY`
trong `nexus_agent/updates.py`; khoá riêng ghi ra file mà **chỉ người vận hành
giữ**, ngoài repo, ngoài máy chủ web, ngoài `secrets/app.env` (Q95).

Vì sao có guard từ chối ghi vào repo/secrets: nếu khoá riêng phát hành lọt vào
repo hay lên máy chủ web thì cả thiết kế xác minh cập nhật của N3.3a **sụp trong
một bước** — ai chiếm được máy chủ web ký được mọi bản cập nhật, tức chiếm mọi
máy khách. Đây đúng là thứ `updates.py` được viết để chống, nên công cụ sinh
khoá phải tự chối con đường làm hỏng nó, không chỉ dặn trong tài liệu.

**Khoá riêng KHÔNG BAO GIỜ in ra màn hình.** Một giá trị đã in là một giá trị đã
vào lịch sử terminal và ảnh chụp — cùng lý do `nexus_agent` không in khoá riêng
của thiết bị.
"""
from __future__ import annotations

import argparse
import base64
import os
import stat
import sys
from pathlib import Path


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _duong_cam(dich: Path) -> str | None:
    """Trả lý do nếu `dich` là chỗ KHÔNG được đặt khoá riêng, hoặc None nếu được.

    Chặn theo *vị trí thật sau khi resolve*, không theo chuỗi người dùng gõ —
    `..` và symlink làm một đường trông ngoài repo thật ra nằm trong.
    """
    try:
        dich_that = dich.resolve()
    except OSError as exc:                                     # noqa: BLE001
        return f"khong resolve duoc duong dan: {exc}"

    repo = _repo_root()
    for cam in (repo, repo / "secrets", repo / "data"):
        try:
            dich_that.relative_to(cam)
        except ValueError:
            continue
        return (f"tu choi ghi khoa rieng vao '{cam}' — Q95 doi khoa phat hanh "
                f"nam NGOAI repo/secrets/data. Chon mot thu muc khac.")
    return None


def sinh(out: Path) -> str:
    """Sinh cặp khoá, ghi khoá riêng ra `out`, trả khoá CÔNG KHAI base64url."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    ly_do = _duong_cam(out)
    if ly_do:
        raise SystemExit(f"LOI: {ly_do}")
    if out.exists():
        raise SystemExit(
            f"LOI: '{out}' da ton tai — khong ghi de mot khoa phat hanh. "
            f"Xoa tay neu chac chan muon thay khoa (se lam moi agent cu tu "
            f"choi ban cap nhat moi cho toi khi ghim lai khoa cong khai).")

    priv = ed25519.Ed25519PrivateKey.generate()
    seed = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption())
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)

    out.parent.mkdir(parents=True, exist_ok=True)
    # Ghi rieng tu, roi that quyen: tren POSIX chi chu so huu doc duoc. Tren
    # Windows ACL khac han nen day chi la lop phong ho, khong phai bao dam.
    out.write_text(_b64u(seed) + "\n", encoding="ascii")
    try:
        os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return _b64u(pub)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", required=True,
                   help="noi ghi khoa RIENG (ngoai repo/secrets/data)")
    args = p.parse_args(argv)

    pub = sinh(Path(args.out))
    print("Da sinh cap khoa phat hanh.")
    print(f"  Khoa RIENG  : {args.out}  (giu kin, KHONG commit, KHONG len web)")
    print( "  Khoa CONG   : dan chuoi duoi day vao RELEASE_PUBLIC_KEY")
    print( "                trong nexus_agent/updates.py, roi dong goi lai agent:")
    print()
    print(f'    RELEASE_PUBLIC_KEY = "{pub}"')
    print()
    print("Ghi chu: doi khoa = phai phat hanh agent moi (khoa ghim trong ma,")
    print("khong tai ve — do la chuoi tin cay dung cach.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
