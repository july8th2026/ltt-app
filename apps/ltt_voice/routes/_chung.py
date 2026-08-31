"""
_chung.py — router + mọi thứ các mảnh route dùng chung.

⭐ VÌ SAO `routes.py` THÀNH MỘT PACKAGE.

   Trần của hợp đồng app là **900 dòng / 30 handler** cho một tệp route
   (`tools/lint_app_contract.py`). Bốn màn đầu đã dùng 632 dòng; thêm Dự án,
   Chạy lô và API nữa là vượt.

   ⛔ Và lối thoát SAI là đặt một tệp anh em `routes_du_an.py`: linter chỉ
      soi `routes.py` **hoặc** package `routes/`, nên một tệp anh em sẽ
      **thoát khỏi mọi phép kiểm** — CSRF, `require_login`, cô lập import.
      Chính chú thích của linter cảnh báo điều đó: *"Bỏ qua dạng package thì
      linter im lặng đúng với hai app LỚN NHẤT ngay sau khi chúng được
      tách."* Package là dạng được duyệt; mỗi mảnh trong đó đều bị soi.

⛔ TỆP NÀY CHỈ LO HTTP, như `routes.py` cũ. Nghiệp vụ ở `features.py`
   (một lượt đọc) và `du_an.py` (một tài liệu). Xem `AGENTS.md` mục 8.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)

from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

from .. import (doc_man_giong, doc_man_lich_su, du_an, features, gia,
                giong_mau, tham_chieu, vo)
from ..manifest import MANIFEST
from ..tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

#: Nhãn người đọc cho `params["nguon"]`. Khai ở đây vì nó là chuyện của **màn
#: hình**, không phải của nghiệp vụ — worker không quan tâm lượt này đến từ đâu.
NHAN_NGUON = {
    "studio": N_('Tạo tiếng nói'),
    "giong": N_('Ghi danh giọng'),
    "du_an": N_('Dự án'),
    "lo": N_('Chạy lô'),
    "api": N_('API'),
}

router = APIRouter(tags=["ltt_voice"])


def _uid(user) -> str:
    """Id người dùng, dạng CHUỖI.

    ⛔ Đừng ép `int()`. `User.id` là UUID chuỗi, nên `int()` ném, và bản
       đầu của hàm này bắt lỗi rồi trả `0` — một giá trị **hợp lệ về kiểu
       nhưng sai về nghĩa**. Hậu quả đo được trên máy chủ thật 31/08/2026:
       trang hiện đúng "56 credit" ở header (chỗ đó đọc phiên trực tiếp)
       trong khi nút Tạo trả *"Khong du credit: can 2, con 0"*, vì handler
       tra sổ của người dùng "0". Và nguy hơn tiền: mọi `owner_id` đều
       thành 0, tức giọng của mọi khách chung một chủ.
    """
    return str(getattr(user, "id", "") or "")


def _db():
    from platform_core.db import get_session
    return get_session()


def _het_phien():
    """Phản hồi khi CSRF không khớp.

    🔴 LỖI ĐANG SỐNG, PHÁT HIỆN 31/08/2026 — VÀ HÌNH DẠNG CỦA NÓ ĐÁNG GHI LẠI.

       `verify_csrf_token` **trả về `bool`**, nó không ném. Bốn cửa POST của app
       này gọi nó rồi **vứt kết quả đi**:

           verify_csrf_token(request, csrf_token)      # <- không dùng gì cả

       Nên CSRF chưa bao giờ được thi hành ở đây, kể từ ngày phát hành. Ba cửa
       bị ảnh hưởng đều là cửa có hậu quả: `/tao` tiêu credit, `/giong/tao` tạo
       hồ sơ giọng **và ghi một cam kết pháp lý**, `/giong/{id}/tat` vô hiệu hoá
       giọng của khách.

    ⭐ Vì sao không ai thấy: dòng gọi **trông đúng**, và chú thích đầu tệp còn
       ghi rõ *"kiểm quyền/CSRF"* — nên đọc lướt thì mọi thứ ở đúng chỗ. Nó chỉ
       lộ ra khi có người gửi một token sai và **đòi** một mã lỗi.
       Đối chiếu: mọi app khác trong kho đều viết `if not verify_csrf_token(...)`.
       `ltt_voice` là app duy nhất không.

    ⚠️ Mức nguy hiểm thật, nói cho đúng chứ không nói to: cookie phiên đặt
       `same_site="lax"` (`server/app.py`), nên một biểu mẫu POST từ site khác
       **không** kèm được cookie — trình duyệt hiện đại đã chặn phần lớn đường
       khai thác. Đây là phòng thủ nhiều lớp bị hụt một lớp, không phải một cánh
       cửa mở toang. Nhưng lớp đó tồn tại vì `lax` không bảo vệ mọi thứ, và vì
       một app không được dựa vào cấu hình của app khác.
    """
    return JSONResponse(
        {"ok": False, "loi": _t("Phiên đã hết hạn. Hãy tải lại trang.")},
        status_code=400)


# ⭐ Vỏ dùng chung đã chuyển sang `vo.py`. Route chỉ còn gọi nó.
#
#    Trước P1 hàm này nằm ngay đây và **không đặt `nav`** — nên phép so
#    `nav == entry.nav_key` trong `base.html` luôn False và cả ba tab của Voice
#    đều xám kể từ ngày phát hành. Không phép kiểm nào bắt được: trang vẫn 200,
#    chỉ là không tab nào sáng. `vo.ngu_canh` bắt buộc truyền `nav_key`, nên lỗi
#    đó không tái diễn được nữa.


