"""
retention.py — dọn dữ liệu cũ của OMMI (H19.6 / H19.8).

Vì sao cần: mỗi lần chạy lại một cảnh sinh thêm một `OmmiSceneVersion` và một
ảnh trong kho. Người dùng chạy 30 lần cho một cảnh là bình thường. Không dọn
thì kho phình theo thời gian mà **không ai thấy** cho tới lúc hết đĩa — và lúc
đó thứ hỏng là việc lưu kết quả của khách hàng đang trả tiền.

Nguyên tắc thiết kế, theo thứ tự quan trọng:

1. **`plan()` trước, `apply()` sau.** Mọi lần dọn phải xem được sẽ xoá gì trước
   khi xoá. Một công cụ dọn dữ liệu không chạy thử được là công cụ không ai dám
   chạy — nên nó sẽ không bao giờ được chạy, và mục đích của nó thành vô nghĩa.

2. **Không bao giờ xoá bản đang dùng.** `scene.image_key` trỏ vào bản nào thì
   bản đó bất khả xâm phạm, kể cả khi nó là bản cũ nhất (người dùng có thể đã
   khôi phục về bản 1).

3. **Giữ tối thiểu N bản gần nhất mỗi cảnh**, không dọn theo tuổi thuần tuý.
   Dọn theo tuổi sẽ xoá sạch lịch sử của một cảnh làm xong từ lâu — đúng cảnh
   mà người dùng quay lại tham chiếu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import OmmiScene, OmmiSceneVersion

# Giữ lại bao nhiêu bản gần nhất cho MỖI cảnh, bất kể chúng cũ đến đâu.
GIU_MOI_CANH = 10

# Chỉ đụng tới bản cũ hơn ngần này. Người dùng còn đang lặp trên một cảnh thì
# đừng dọn dưới chân họ.
TUOI_TOI_THIEU = timedelta(days=30)


@dataclass
class KeHoach:
    """Sẽ xoá gì. Trả về từ `plan()`, và `apply()` chạy đúng bản này."""

    version_ids: list[str] = field(default_factory=list)
    storage_keys: list[str] = field(default_factory=list)
    # Bản được giữ lại vì lý do đặc biệt — để người vận hành đọc và yên tâm.
    giu_vi_dang_dung: int = 0
    giu_vi_con_moi: int = 0
    giu_vi_trong_han_muc: int = 0

    def as_dict(self) -> dict:
        return {"se_xoa": len(self.version_ids),
                "se_xoa_anh": len(self.storage_keys),
                "giu_vi_dang_dung": self.giu_vi_dang_dung,
                "giu_vi_con_moi": self.giu_vi_con_moi,
                "giu_vi_trong_han_muc": self.giu_vi_trong_han_muc}


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def plan(db: Session, *, owner_id: str = "", giu: int = GIU_MOI_CANH,
         tuoi: timedelta = TUOI_TOI_THIEU, bay_gio: datetime | None = None) -> KeHoach:
    """Tính xem sẽ xoá gì. KHÔNG đụng vào dữ liệu.

    `owner_id` rỗng = mọi người dùng (chế độ vận hành). Có giá trị = chỉ người
    đó, dùng khi cần dọn cho một tài khoản cụ thể.
    """
    moc = (bay_gio or datetime.now(timezone.utc)) - tuoi
    ke = KeHoach()

    canh = select(OmmiScene)
    if owner_id:
        canh = canh.where(OmmiScene.owner_id == owner_id)
    for scene in db.execute(canh).scalars().all():
        ban = db.execute(
            select(OmmiSceneVersion)
            .where(OmmiSceneVersion.scene_id == scene.id)
            .order_by(OmmiSceneVersion.version.desc())
        ).scalars().all()

        for thu_tu, v in enumerate(ban):
            if thu_tu < giu:
                ke.giu_vi_trong_han_muc += 1
                continue
            # Bản đang được cảnh dùng làm ảnh hiện tại: bất khả xâm phạm, kể cả
            # khi nó cũ nhất (người dùng có thể đã khôi phục về bản 1).
            if v.image_key and v.image_key == scene.image_key:
                ke.giu_vi_dang_dung += 1
                continue
            if _aware(v.created_at) and _aware(v.created_at) > moc:
                ke.giu_vi_con_moi += 1
                continue
            ke.version_ids.append(v.id)
            if v.image_key:
                ke.storage_keys.append(v.image_key)

    # Ảnh còn được cảnh nào hoặc bản nào KHÁC dùng thì không được xoá file.
    if ke.storage_keys:
        con_dung = set()
        for row in db.execute(select(OmmiScene.image_key)).scalars().all():
            if row:
                con_dung.add(row)
        for row in db.execute(
            select(OmmiSceneVersion.image_key)
            .where(OmmiSceneVersion.id.not_in(ke.version_ids))
        ).scalars().all():
            if row:
                con_dung.add(row)
        # Bỏ trùng: hai bản trỏ cùng một ảnh thì xoá một lần là đủ, và gọi
        # `storage.delete()` hai lần sẽ đếm sai số ảnh đã dọn.
        da_thay: set[str] = set()
        loc = []
        for k in ke.storage_keys:
            if k in con_dung or k in da_thay:
                continue
            da_thay.add(k)
            loc.append(k)
        ke.storage_keys = loc
    return ke


def apply(db: Session, ke: KeHoach, *, storage=None) -> dict:
    """Chạy đúng kế hoạch đã xem. Trả số thực sự xoá được.

    Nhận `KeHoach` chứ không tự tính lại: người vận hành duyệt cái gì thì chạy
    đúng cái đó. Tính lại lúc chạy nghĩa là thứ họ đã xem không còn là thứ sẽ
    xảy ra.
    """
    xoa_ban = 0
    for vid in ke.version_ids:
        row = db.get(OmmiSceneVersion, vid)
        if row is not None:
            db.delete(row)
            xoa_ban += 1
    db.flush()

    xoa_anh = 0
    if storage is not None:
        for key in ke.storage_keys:
            try:
                storage.delete(key)
                xoa_anh += 1
            except Exception:               # noqa: BLE001
                # Xoá file lỗi KHÔNG được làm hỏng cả lượt dọn: dòng CSDL đã đi
                # rồi, và một file thừa nằm lại vô hại hơn nhiều so với việc
                # dừng giữa chừng để lại trạng thái nửa vời.
                _log().warning("Không xoá được ảnh %s khi dọn", key, exc_info=True)
    return {"da_xoa_ban": xoa_ban, "da_xoa_anh": xoa_anh}


def _log():
    import logging
    return logging.getLogger(__name__)
