"""Agent chỉ chạy bản cập nhật mà LTT đã ký. Không có cửa nào khác (Q95).

Q95 bỏ chứng thư ký mã Windows nhưng **giữ nguyên** invariant #7 của pack và
ràng buộc 10 của Q93, vì hai thứ đó giải hai bài toán khác nhau:

* chứng thư ký mã → **Windows** tin binary lúc cài. Tốn tiền, và Q95 chấp nhận
  không có;
* ký bản cập nhật → **agent** tin bản vá **trước khi** chạy nó. Không tốn gì, và
  bỏ nó là bỏ cả đội máy.

Vì sao cái thứ hai không được bỏ: agent chạy quyền cao trên máy khách. Một
updater tải rồi chạy mà không xác minh nghĩa là **ai chiếm được máy phát hành,
hoặc chen được vào đường tải, thì chiếm mọi máy khách cùng một lúc**. HTTPS không
đủ — nó bảo vệ đường truyền, không bảo vệ trước một máy chủ phát hành đã bị
chiếm.

## Khoá phát hành ghim trong mã, không tải về

Khoá công khai phát hành nằm ngay trong file này. Nếu agent **tải** khoá tin cậy
về thì kẻ điều khiển được đường tải sẽ đưa khoá của nó — và toàn bộ chuỗi tin
cậy sụp trong một bước. Ghim nghĩa là đổi khoá phải phát hành một agent mới, và
đó là cái giá đúng.

Khoá **riêng** phát hành không bao giờ nằm trên máy chủ web, không trong repo,
không trong `secrets/app.env`. Nó ký ở nơi khác, thủ công, cho mỗi bản phát hành.

## Manifest ký cái gì

Chữ ký phủ **toàn bộ** manifest, và manifest chứa `sha256` của file cài. Vì vậy
không cần ký riêng file nhị phân: đổi một byte trong file là `sha256` lệch, và
đổi `sha256` trong manifest là chữ ký hỏng.

`version` nằm trong phần được ký để chặn **hạ cấp**: không có nó, kẻ tấn công
phát lại một manifest cũ **hợp lệ thật** để đẩy máy khách về bản có lỗ hổng đã
vá. Chữ ký đúng, nội dung đúng, mà vẫn là tấn công.
"""
from __future__ import annotations

import base64
import hashlib
import json

#: Khoá CÔNG KHAI phát hành, base64url. Ghim ở đây có chủ ý — xem docstring.
#: Rỗng = agent **từ chối mọi bản cập nhật**, và đó là mặc định đúng: một agent
#: chưa được cấu hình khoá thì thà không cập nhật còn hơn cập nhật bừa.
RELEASE_PUBLIC_KEY = ""

#: Tên trường bắt buộc trong manifest. Thiếu một trường là từ chối, không đoán.
TRUONG_BAT_BUOC = ("version", "sha256", "url", "size")


class UpdateError(Exception):
    """Bản cập nhật không dùng được. Agent giữ nguyên bản đang chạy."""


def _b64d(value: str) -> bytes:
    raw = str(value or "").strip()
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def canonical_manifest(manifest: dict) -> bytes:
    """Byte được ký. Một chỗ duy nhất, cho cả bên ký và bên kiểm.

    `sort_keys` + `separators` cố định: nếu hai bên serialize khác nhau dù chỉ
    một khoảng trắng thì mọi chữ ký hợp lệ đều bị từ chối, và triệu chứng sẽ
    trông y hệt "khoá sai".
    """
    phan_ky = {k: manifest[k] for k in sorted(manifest) if k != "signature"}
    return json.dumps(phan_ky, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def verify_manifest(manifest: dict, *, public_key: str = "",
                    phien_ban_dang_chay: str = "") -> dict:
    """Manifest hợp lệ, hoặc ném `UpdateError`. Trả lại chính manifest đó.

    Kiểm theo thứ tự **rẻ trước, đắt sau**, và mỗi bước từ chối luôn thay vì
    tích lỗi: một manifest thiếu trường thì không đáng tốn một phép kiểm chữ ký.
    """
    khoa = str(public_key or RELEASE_PUBLIC_KEY or "").strip()
    if not khoa:
        raise UpdateError(
            "agent chua duoc ghim khoa phat hanh — tu choi moi ban cap nhat")

    if not isinstance(manifest, dict):
        raise UpdateError("manifest khong phai doi tuong JSON")
    thieu = [t for t in TRUONG_BAT_BUOC if not str(manifest.get(t) or "").strip()]
    if thieu:
        raise UpdateError(f"manifest thieu truong: {', '.join(thieu)}")

    chu_ky = str(manifest.get("signature") or "").strip()
    if not chu_ky:
        raise UpdateError("manifest khong co chu ky")

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import ed25519

    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(_b64d(khoa))
    except Exception as exc:                                   # noqa: BLE001
        raise UpdateError("khoa phat hanh ghim trong agent sai dinh dang") from exc

    try:
        pub.verify(_b64d(chu_ky), canonical_manifest(manifest))
    except (InvalidSignature, ValueError) as exc:
        raise UpdateError("chu ky manifest khong dung") from exc

    # Chan HA CAP: mot manifest cu la mot manifest da tung hop le, nen chu ky
    # cua no van dung mai mai. Chi so phien ban moi phat hien duoc viec phat lai.
    if phien_ban_dang_chay:
        if not _moi_hon(str(manifest["version"]), phien_ban_dang_chay):
            raise UpdateError(
                f"ban {manifest['version']} khong moi hon ban dang chay "
                f"{phien_ban_dang_chay} — tu choi de chan ha cap")
    return manifest


def verify_file(duong_dan, manifest: dict) -> None:
    """File tải về có đúng là file mà manifest đã ký không.

    Đọc theo khối chứ không `read()` cả file: bản cài có thể hàng trăm MB, và
    một agent ngốn hết RAM máy khách lúc tự cập nhật là một agent tự gây sự cố
    ngay tại thời điểm nhạy cảm nhất.
    """
    from pathlib import Path

    p = Path(duong_dan)
    if not p.exists():
        raise UpdateError("khong thay file da tai")

    kich_thuoc = p.stat().st_size
    if kich_thuoc != int(manifest["size"]):
        raise UpdateError(
            f"kich thuoc lech: cho {manifest['size']}, nhan {kich_thuoc}")

    dau = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            dau.update(khoi)
    that = dau.hexdigest()
    if not _bang_nhau(that, str(manifest["sha256"]).lower()):
        raise UpdateError("sha256 khong khop manifest")


def _bang_nhau(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)


def _moi_hon(moi: str, cu: str) -> bool:
    """So phiên bản dạng `1.2.3`. Không parse được thì coi là KHÔNG mới hơn.

    Fail-closed: một chuỗi phiên bản lạ mà được coi là mới hơn sẽ thành đường
    lách qua phép chặn hạ cấp.
    """
    def _tach(v: str):
        try:
            return tuple(int(x) for x in str(v).strip().split("."))
        except (TypeError, ValueError):
            return None

    a, b = _tach(moi), _tach(cu)
    if a is None or b is None:
        return False
    return a > b


__all__ = ["RELEASE_PUBLIC_KEY", "TRUONG_BAT_BUOC", "UpdateError",
           "canonical_manifest", "verify_file", "verify_manifest"]
