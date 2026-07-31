"""
app_access.py — phân quyền app cho từng người dùng (H1.4).

Ba mức: `enabled` / `locked` / `hidden`. Mặc định là `enabled` (Q25) — bảng
`app_access` chỉ lưu ngoại lệ.

Điểm cốt lõi về bảo mật: **chặn ở tầng route, không chỉ ẩn nút.** Ẩn một app
khỏi trang chủ mà vẫn cho gọi thẳng URL của nó thì không phải phân quyền — chỉ
là giấu. Vì vậy có `app_cho_path()` để middleware ánh xạ mọi đường dẫn về app
và chặn ở đó, dù người dùng gõ URL trực tiếp.

Ánh xạ path → app đọc từ registry (route_prefix + các mục nav), **không hardcode
slug** — giữ đúng hợp đồng: nền tảng không biết trước app nào tồn tại.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import AppAccess, User

ENABLED = "enabled"
LOCKED = "locked"
HIDDEN = "hidden"
MAC_DINH = ENABLED
_HOP_LE = {ENABLED, LOCKED, HIDDEN}


def muc_quyen(db: DbSession, user: Optional[User], slug: str) -> str:
    """Mức quyền của user với app `slug`. Admin luôn `enabled`.

    `user=None` (chưa đăng nhập) trả mặc định — việc chặn ẩn danh là của
    `require_login` ở từng route, không phải của phân quyền app.
    """
    if user is None:
        return MAC_DINH
    if user.role == "admin":
        return ENABLED
    row = db.execute(
        select(AppAccess).where(
            AppAccess.user_id == user.id, AppAccess.app_slug == slug
        )
    ).scalar_one_or_none()
    return row.level if row is not None else MAC_DINH


def dat_quyen(db: DbSession, user_id: str, slug: str, level: str) -> None:
    """Đặt mức quyền. Đặt về mặc định (`enabled`) thì XOÁ dòng thay vì lưu.

    Xoá-khi-về-mặc-định giữ bảng chỉ chứa ngoại lệ thật, đúng ý Q25: số dòng
    phản ánh số ngoại lệ, không phải số (user × app).
    """
    if level not in _HOP_LE:
        raise ValueError(f"muc quyen khong hop le: {level!r}")
    row = db.execute(
        select(AppAccess).where(
            AppAccess.user_id == user_id, AppAccess.app_slug == slug
        )
    ).scalar_one_or_none()

    if level == MAC_DINH:
        if row is not None:
            db.delete(row)
    elif row is not None:
        row.level = level
    else:
        db.add(AppAccess(user_id=user_id, app_slug=slug, level=level))
    db.flush()


def loc_app_hien_thi(db: DbSession, user: Optional[User], loaded: list) -> list:
    """Lọc danh sách app cho trang chủ: bỏ app `hidden` với user này.

    App `locked` vẫn hiện (để user biết nó tồn tại, sắp mở) — template tự gắn
    nhãn. `loaded` là danh sách LoadedApp từ registry.discover().
    """
    ket_qua = []
    for item in loaded:
        if muc_quyen(db, user, item.manifest.slug) == HIDDEN:
            continue
        ket_qua.append(item)
    return ket_qua


def _chuan_hoa(path: str) -> str:
    p = "/" + (path or "").strip("/")
    return p


def app_cho_path(path: str, loaded: list) -> Optional[str]:
    """Ánh xạ một đường dẫn HTTP về slug của app sở hữu nó, hoặc None.

    Khớp theo tiền tố dài nhất trong tập {route_prefix} ∪ {đường dẫn các mục
    nav} của mọi app. Khớp tiền tố dài nhất để `/sheet/facebook` thắng `/sheet`
    nếu cả hai cùng khai, và để một app không "nuốt" đường dẫn của app khác chỉ
    vì trùng phần đầu.
    """
    path = _chuan_hoa(path)
    ung_vien: list[tuple[int, str]] = []   # (do_dai_prefix, slug)

    for item in loaded:
        m = item.manifest
        prefixes = {m.route_prefix.rstrip("/") or "/"}
        for nav in m.nav_entries():
            prefixes.add(("/" + nav.path.strip("/")) if nav.path else "/")
        for pre in prefixes:
            if pre == "/":
                continue      # "/" là trang chủ, không thuộc app nào
            if path == pre or path.startswith(pre + "/"):
                ung_vien.append((len(pre), m.slug))

    if not ung_vien:
        return None
    ung_vien.sort(reverse=True)     # prefix dài nhất trước
    return ung_vien[0][1]
