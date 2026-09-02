"""
chinh_sach.py — chính sách sản phẩm của ChatLTT: năng lực nào được MỜI. (H43 Phase 06)

## Ba cổng khác nhau — đây là cổng thứ ba

  `ToolSpec.customer_visible`                 palette Agent/Canvas
  `ToolSpec.api_exposed` + `LTT_PUBLIC_API_TOOLS`   bán qua `/api/v1`
  **`CONG_CU_CHO_PHEP` (tệp này)**                  thứ ChatLTT mời người dùng

Một tool có thể ở cả ba, hoặc chỉ một. Nhầm cổng là lộ năng lực nội bộ ra
một bề mặt không ai duyệt — nên ChatLTT **không** suy allowlist từ hai cổng kia.

## Fail-closed, và fail-closed ở ĐÂY

Tên không có trong `CONG_CU_CHO_PHEP` thì `danh_muc()` không trả về, và
`kiem_cho_phep()` ném — kể cả khi registry có tool đó, kể cả khi nó `api_exposed`.
Thêm một năng lực cho ChatLTT = thêm một dòng ở đây + một quyết định sản phẩm
(D8 kế hoạch: `image.generate` — model đám mây — **không** được mời cho tới khi
chủ sản phẩm duyệt).

⛔ Tệp này KHÔNG biết id model nội bộ, URL máy, hay tên app sở hữu. Mọi thứ đó
   ở phía bên kia facade `platform_core.runtime_noi_bo`.
"""
from __future__ import annotations

from typing import FrozenSet, Optional

#: V1 — ba model nhà. Thứ tự là thứ tự hiển thị.
CONG_CU_CHO_PHEP: tuple = ("text.chat", "image.ltt", "speech.ltt")

#: Năng lực text mặc định của composer.
NANG_LUC_TEXT = "text.chat"
NANG_LUC_ANH = "image.ltt"
NANG_LUC_TIENG = "speech.ltt"

#: Phương thức mà bộ hiển thị của ChatLTT biết vẽ. Một năng lực có phương thức
#: ngoài tập này (vd `video`) **không hiện** dù nằm trong allowlist — Phase 11
#: chứng minh "modality lạ thì fail-closed", và đây là chỗ nó fail.
PHUONG_THUC_HIEN_THI: FrozenSet[str] = frozenset({"text", "image", "audio"})


class KhongDuocPhep(PermissionError):
    """Năng lực không nằm trong chính sách sản phẩm của ChatLTT."""


def cho_phep() -> FrozenSet[str]:
    return frozenset(CONG_CU_CHO_PHEP)


def kiem_cho_phep(ten: str) -> str:
    """Trả lại `ten` nếu được mời; ném `KhongDuocPhep` nếu không. Không có nhánh 'gần đúng'."""
    if ten not in cho_phep():
        raise KhongDuocPhep(f"nang luc {ten!r} khong nam trong chinh sach ChatLTT")
    return ten


def danh_muc(db, *, user_id: str, apps: Optional[list] = None) -> list:
    """Catalog ChatLTT cho một người dùng: allowlist ∩ registry ∩ phương thức vẽ được.

    Trả `list[NangLuc]` của `platform_core.runtime_noi_bo.danh_muc`, đã lọc
    thêm theo `PHUONG_THUC_HIEN_THI` và xếp theo thứ tự `CONG_CU_CHO_PHEP`.
    """
    from platform_core.runtime_noi_bo.danh_muc import danh_muc as _dm

    thu_tu = {ten: i for i, ten in enumerate(CONG_CU_CHO_PHEP)}
    ra = [n for n in _dm(db, user_id=user_id, cho_phep=cho_phep(), apps=apps)
          if n.phuong_thuc in PHUONG_THUC_HIEN_THI]
    ra.sort(key=lambda n: thu_tu.get(n.ten, 999))
    return ra
