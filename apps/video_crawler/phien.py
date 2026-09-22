"""Phiên đăng nhập nền tảng theo người dùng (spec §16, đợt B0).

Donor dùng profile Chromium CHUNG máy cho mọi người (`W:113-117`) — cấm ở SaaS nhiều khách (SUPER PROMPT §P).
Ở đây khách tự nhập cookies.txt (định dạng Netscape) của CHÍNH họ:
- chỉ giữ cookie thuộc tên miền của nền;
- bắt buộc có cookie xác thực của nền (donor `COOKIE_AUTH`);
- lưu mã hoá (`platform_core.secretbox`), cô lập theo (owner, nền);
- worker nhận một TỆP tạm trong thư mục job (xoá khi xong) — cookie không bao giờ vào params/log/result/URL.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from apps.video_crawler import nen_tang
from apps.video_crawler.tables import VcPhien

#: Trần kích thước cookies.txt nhận vào (một trình duyệt xuất cả kho có thể vài MB — không cần).
TOI_DA_BYTE = 256 * 1024


class PhienKhongHopLe(ValueError):
    """Nội dung cookie không dùng được — thông điệp hiển thị được cho khách (không chứa giá trị cookie)."""


def _thuoc(domain: str, ten_mien: tuple) -> bool:
    d = domain.lstrip(".").lower()
    return any(d == t or d.endswith("." + t) for t in ten_mien)


def _loc(cookies_txt: str, nen) -> tuple[list[str], datetime | None]:
    if not isinstance(cookies_txt, str) or len(cookies_txt.encode("utf-8")) > TOI_DA_BYTE:
        raise PhienKhongHopLe("Tệp cookie quá lớn hoặc không đọc được.")
    giu, ten_co, het_han = [], set(), []
    cookies_txt = cookies_txt.lstrip("\ufeff")          # tệp xuất có BOM (review lần 2)
    for dong in cookies_txt.splitlines():
        dong = dong.rstrip("\r")
        if not dong or (dong.startswith("#") and not dong.startswith("#HttpOnly_")):
            continue
        phan = dong.split("\t")
        if len(phan) != 7:
            continue
        domain = phan[0].removeprefix("#HttpOnly_")
        if not _thuoc(domain, nen.ten_mien):
            continue
        giu.append(dong)
        ten_co.add(phan[5])
        if phan[5] in nen.cookie_dang_nhap:            # hạn của PHIÊN = hạn cookie xác thực, không cookie phụ
            try:
                if int(phan[4]) > 0:
                    het_han.append(int(phan[4]))
            except ValueError:
                pass
    if not giu:
        raise PhienKhongHopLe(f"Không thấy cookie nào của {nen.ten}. Hãy xuất cookies.txt khi đang mở {nen.ten}.")
    if not ten_co & set(nen.cookie_dang_nhap):
        raise PhienKhongHopLe(f"Cookie này chưa đăng nhập {nen.ten} — hãy đăng nhập rồi xuất lại.")
    moc = None
    if het_han:
        try:
            moc = datetime.fromtimestamp(min(het_han), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):   # số hạn khổng lồ (review lần 2) ⇒ coi như không hạn
            moc = None
    return giu, moc


def luu(db, *, owner_id: str, nen_tang: str, cookies_txt: str) -> VcPhien:
    """Lưu (hoặc thay) phiên của `owner_id` trên nền. KHÔNG commit."""
    from platform_core import secretbox
    nen = nen_tang_cua(nen_tang)
    dong, het_han = _loc(cookies_txt, nen)
    noi_dung = "# Netscape HTTP Cookie File\n" + "\n".join(dong) + "\n"
    from sqlalchemy.exc import IntegrityError
    for _lan in range(2):          # hai lượt lưu đồng thời cùng (owner, nền) ⇒ UNIQUE; lượt sau cập nhật (review lần 2)
        row = db.execute(select(VcPhien).where(VcPhien.owner_id == owner_id, VcPhien.nen_tang == nen.id)
                         ).scalar_one_or_none()
        try:
            with db.begin_nested():
                if row is None:
                    row = VcPhien(owner_id=owner_id, nen_tang=nen.id, cookie_ma_hoa="")
                    db.add(row)
                row.cookie_ma_hoa = secretbox.ma_hoa(noi_dung)
                row.so_cookie = len(dong)
                row.het_han_luc = het_han
                row.cap_nhat_luc = datetime.now(timezone.utc)
            return row
        except IntegrityError:
            continue
    raise PhienKhongHopLe("Đang lưu phiên này ở nơi khác — thử lại.")


def hop_le(row: VcPhien) -> bool:
    """Phiên còn giải mã được với khoá hiện tại (khoá xoay ⇒ False ⇒ giao diện báo "phiên hỏng")."""
    from platform_core import secretbox
    try:
        secretbox.giai_ma(row.cookie_ma_hoa)
        return True
    except secretbox.SecretBoxError:
        return False


def don_tam_cu(goc: Path, *, tuoi_s: float = 3 * 3600) -> None:
    """Xoá thư mục cookie tạm `vc_phien_*` cũ hơn `tuoi_s` (job bị giết giữa chừng không dọn được — review lần 2)."""
    with contextlib.suppress(OSError):
        for d in Path(goc).glob("vc_phien_*"):
            with contextlib.suppress(OSError):
                if d.is_dir() and time.time() - d.stat().st_mtime > tuoi_s:
                    shutil.rmtree(d, ignore_errors=True)


def nen_tang_cua(nen_id: str):
    try:
        nen = nen_tang.lay(nen_id)
    except nen_tang.NenKhongHopLe as e:
        raise PhienKhongHopLe("Nền tảng không hợp lệ.") from e
    if not nen.cookie_dang_nhap:
        raise PhienKhongHopLe(f"{nen.ten} không dùng đăng nhập.")
    return nen


def danh_sach(db, owner_id: str) -> list[VcPhien]:
    return list(db.execute(select(VcPhien).where(VcPhien.owner_id == owner_id)
                           .order_by(VcPhien.nen_tang)).scalars())


def cookies_txt_cua(db, *, owner_id: str, nen_tang: str) -> str | None:
    """Giải mã phiên — CHỈ gọi trong worker, ngay trước khi ghi tệp tạm."""
    from platform_core import secretbox
    row = db.execute(select(VcPhien).where(VcPhien.owner_id == owner_id, VcPhien.nen_tang == nen_tang)
                     ).scalar_one_or_none()
    if row is None:
        return None
    try:
        return secretbox.giai_ma(row.cookie_ma_hoa)
    except secretbox.SecretBoxError:
        return None


def xoa(db, *, owner_id: str, nen_tang: str) -> bool:
    row = db.execute(select(VcPhien).where(VcPhien.owner_id == owner_id, VcPhien.nen_tang == nen_tang)
                     ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


@contextlib.contextmanager
def tep_cookie_tam(db, *, owner_id: str, nen_tang: str, thu_muc: Path):
    """Ghi phiên ra một tệp trong `thu_muc` (thư mục tạm của job), trả đường dẫn, xoá khi ra khỏi khối.

    Không có phiên ⇒ trả None (adapter chạy ẩn danh).
    """
    noi_dung = cookies_txt_cua(db, owner_id=owner_id, nen_tang=nen_tang)
    if noi_dung is None:
        yield None
        return
    duong = Path(thu_muc) / f"cookies_{nen_tang}.txt"
    fd = os.open(duong, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung)
    try:
        yield duong
    finally:
        with contextlib.suppress(OSError):
            duong.unlink()
