"""du_an.py — dự án gom hội thoại. LẮP `platform_core.app_projects`. (H44 B5)

## Tệp này CỐ TÌNH mỏng, và đó là kết luận của §0 chứ không phải sự lười

`platform_core/app_projects.py` đã có đủ vòng đời — `get_owned` · `create` ·
`save` (khoá lạc quan qua `revision`) · `archive` — cộng `validate_container_payload`
(≤1 MiB, sâu ≤32, chặn khoá bí mật), và **ba app đang dùng nó** (`agent`,
`autosubvideo`, `prompt_ai_ommi`). Viết lại một vòng đời thứ hai ở đây là dựng
một nguồn chân lý thứ hai cho cùng một khái niệm.

⇒ Tệp này chỉ làm hai việc lõi **không** biết:
  1. đóng `app_slug="chatltt"` để không nơi gọi nào phải nhớ chuỗi ấy;
  2. giữ **liên kết** giữa dự án và `chatltt_conversation`.

## 🔴 Không có bộ đếm nào ở đây, và đó là một quyết định

`LibreChat/chatProject.ts` mang `conversationCount` + `lastConversationAt` phi
chuẩn hoá (đo 06/09). Ta **không** mượn phần ấy: một bộ đếm là nguồn chân lý
**thứ hai** cho thứ `chatltt_conversation` đã biết, và `CLAUDE.md` của kho này
viết thẳng — *"một giá trị chép lại là một giá trị sẽ trôi"* — sau khi một bảng
chép tay nói sai **năm lần**, cả năm về phía nguy hiểm.

⭐ Và phần đáng mượn thì **đã có sẵn**: `ix_app_projects_owner_app_updated`
   `(user_id, app_slug, updated_at)` chính là chỉ số mà `lastConversationAt` của
   họ sinh ra để phục vụ. Chạm `updated_at` khi hội thoại vào/ra dự án là đủ để
   "gần nhất trước" đánh chỉ số được — không thêm cột, không có gì để trôi.

## Xoá dự án KHÔNG xoá hội thoại

`project_id` về `NULL`, hội thoại ở lại. Một cái thư mục bị xoá không được mang
theo thứ nó đựng. Đó cũng là lý do liên kết nằm ở một **cột nullable** chứ không
ở một khoá ngoại `ON DELETE CASCADE`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update

from apps.chatltt.tables import ChatlttConversation
from platform_core import app_projects as AP
from platform_core.models import APP_PROJECT_ACTIVE, AppProject

#: Khoá app trong bảng dùng chung. Đóng ở **một** chỗ: một chuỗi lặp ở mỗi nơi
#: gọi là một chuỗi sẽ có chỗ gõ sai, và gõ sai nó nghĩa là đọc dự án của app
#: khác.
APP = "chatltt"

#: Hình dạng `payload` của ChatLTT. Bản v1 **rỗng**.
#:
#: ⛔ Phản xạ là thêm `payload["chi_dan"]` rồi tiêm nó vào system prompt. Không:
#:    `chatltt_ghi_nho.pham_vi` đã khai `du_an` từ B4 bước 1, và
#:    `ghi_nho.ap_dung(du_an_id=…)` đã tiêm đúng tầng ấy. Hai cơ chế cùng tiêm
#:    chữ vào system prompt là hai cơ chế sẽ lệch nhau — và người dùng sẽ có
#:    **hai** chỗ để sửa cùng một điều, rồi sửa nhầm chỗ.
#:
#: ⭐ Phép đo đứng sau: `LibreChat/chatProject.ts` cũng **không** cho project một
#:    trường chỉ dẫn nào. Ta không thiếu tính năng của họ; ta đặt nó ở chỗ đã có.
SCHEMA = 1


class KhongDuocPhep(Exception):
    """Dự án hoặc hội thoại không thuộc người gọi."""


def _cham(db, du_an_id: str) -> None:
    """Chạm `updated_at` của dự án — nó là mốc **LẦN DÙNG**, không phải lần sửa tên.

    ⭐ Nếu chỉ đổi tên mới chạm mốc thì danh sách sắp theo *"lần sửa tên gần
       nhất"* — một thứ không ai quan tâm. Mượn ý từ `lastConversationAt` của
       LibreChat, nhưng dùng cột đã có thay vì đẻ một cột mới.
    """
    db.execute(update(AppProject)
               .where(AppProject.id == du_an_id)
               .values(updated_at=datetime.now(timezone.utc)))


def tao(db, *, user_id: str, ten: str = "") -> AppProject:
    return AP.create(db, user_id=user_id, app_slug=APP, name=ten,
                     schema_version=SCHEMA, payload={})


def mot(db, *, user_id: str, du_an_id: str) -> AppProject | None:
    """Một dự án theo id. `None` cho người lạ — **không** ném.

    ⛔ Không phân biệt *"không có"* với *"không phải của bạn"*, cùng luật
       `kho_tep.mot` và `ghi_nho.mot`: một API phân biệt hai ca đó cho phép dò
       id của người khác.
    """
    try:
        return AP.get_owned(db, du_an_id, user_id, APP)
    except AP.ProjectNotFound:
        return None


def liet_ke(db, *, user_id: str) -> list[AppProject]:
    """Dự án của một người, **gần dùng nhất trước** — xem `_cham`."""
    return list(db.execute(
        select(AppProject)
        .where(AppProject.user_id == user_id, AppProject.app_slug == APP,
               AppProject.status == APP_PROJECT_ACTIVE)
        .order_by(AppProject.updated_at.desc())
    ).scalars())


def doi_ten(db, *, user_id: str, du_an_id: str, ten: str,
            revision: int) -> AppProject:
    """Đổi tên. `revision` là khoá lạc quan của lõi — hai tab sửa cùng lúc thì
    tab thứ hai nhận `ProjectConflict`, không ghi đè im lặng."""
    row = mot(db, user_id=user_id, du_an_id=du_an_id)
    if row is None:
        raise KhongDuocPhep("khong tim thay du an")
    return AP.save(db, project_id=du_an_id, user_id=user_id, app_slug=APP,
                   revision=revision, name=ten, schema_version=SCHEMA,
                   payload=dict(row.payload or {}))


def gan(db, *, user_id: str, conv_id: str, du_an_id: str) -> bool:
    """Đưa một hội thoại vào một dự án. Trả `False` khi không được phép.

    🔴 Kiểm **CẢ HAI** phía — sở hữu hội thoại **và** sở hữu dự án. Kiểm một
       chiều là để hở chiều kia, đúng ca `test_822` đã chốt cho `kho_tep`.
    """
    if mot(db, user_id=user_id, du_an_id=du_an_id) is None:
        return False
    hoi = db.get(ChatlttConversation, conv_id)
    if hoi is None or hoi.user_id != user_id:
        return False
    hoi.project_id = du_an_id
    db.flush()
    _cham(db, du_an_id)
    return True


def go(db, *, user_id: str, conv_id: str) -> bool:
    """Bỏ một hội thoại ra khỏi dự án. Hội thoại **ở lại**, chỉ mất cái nhãn."""
    hoi = db.get(ChatlttConversation, conv_id)
    if hoi is None or hoi.user_id != user_id:
        return False
    cu = hoi.project_id
    hoi.project_id = None
    db.flush()
    if cu:
        _cham(db, cu)
    return True


def hoi_thoai_cua(db, *, user_id: str, du_an_id: str) -> list[ChatlttConversation]:
    """Hội thoại trong một dự án. Lọc theo **cả hai** `user_id` và `project_id`.

    ⛔ Lọc riêng `project_id` là đủ *hôm nay* (chủ dự án = chủ hội thoại), nhưng
       nó vay một bất biến ở bảng bên cạnh. Một cửa quyền không được đi vay.
    """
    return list(db.execute(
        select(ChatlttConversation)
        .where(ChatlttConversation.user_id == user_id,
               ChatlttConversation.project_id == du_an_id,
               ChatlttConversation.deleted_at.is_(None))
        .order_by(ChatlttConversation.updated_at.desc())
    ).scalars())


def xoa(db, *, user_id: str, du_an_id: str) -> bool:
    """Xoá một dự án: lưu trữ nó, và **trả hội thoại về không-dự-án**.

    🔴 Hội thoại KHÔNG bị xoá. Người dùng nghĩ mình đang dọn một cái nhãn; nếu
       thao tác ấy đốt luôn nội dung thì không có cách nào lấy lại, và họ sẽ chỉ
       phát hiện sau khi đã bấm.

    ⇒ Thứ tự có chủ đích: **gỡ liên kết TRƯỚC**, lưu trữ sau. Ngược lại thì một
      lần hỏng giữa chừng để lại hội thoại trỏ vào một dự án đã lưu trữ — tức
      những hội thoại **không hiện ở đâu cả**.
    """
    row = mot(db, user_id=user_id, du_an_id=du_an_id)
    if row is None:
        return False
    db.execute(update(ChatlttConversation)
               .where(ChatlttConversation.user_id == user_id,
                      ChatlttConversation.project_id == du_an_id)
               .values(project_id=None))
    db.flush()
    AP.archive(db, row)
    return True


def du_an_cua_hoi_thoai(db, *, user_id: str, conv_id: str) -> str:
    """`project_id` của một hội thoại, hoặc `""`. Cho đường tiêm ghi nhớ (B5 bước 4).

    ⭐ Trả **chuỗi rỗng** chứ không `None`: nơi gọi là `ghi_nho.ap_dung(du_an_id=…)`
       và nó đã coi chuỗi rỗng là *"không có dự án"*. Một `None` ở đây bắt mọi
       nơi gọi phải tự quy đổi, và một chỗ quên quy đổi là một `WHERE
       muc_tieu_id = None` không khớp gì mà cũng không báo lỗi.
    """
    hoi = db.get(ChatlttConversation, conv_id)
    if hoi is None or hoi.user_id != user_id:
        return ""
    return str(hoi.project_id or "")
