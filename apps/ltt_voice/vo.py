"""
vo.py — VỎ dùng chung của mọi màn LTT Voice Studio.

⭐ VÌ SAO LÀ MỘT TỆP RIÊNG, KHÔNG PHẢI MỘT HÀM TRONG `routes.py`.

   Vỏ là thứ **mọi** trang cần: tab nào đang mở, engine sống chưa, khách đang có
   bao nhiêu việc chạy, bảng giá, trần ký tự. Trước đây nó là `_ngu_canh()` nằm
   trong `routes.py` — đúng chỗ khi có ba trang, sai chỗ khi có sáu: mỗi trang
   mới thêm một khoá vào cùng một hàm, và `routes.py` biến thành nơi mọi thứ rơi
   vào. Đó chính xác là con đường đã dẫn tới một tệp route 1.799 dòng ở dự án
   này (`AGENTS.md` mục 8, và trần cứng 900 dòng của
   `tools/lint_app_contract.py` tồn tại vì nó).

⛔ ĐÂY KHÔNG PHẢI CHỖ CHỨA NGHIỆP VỤ. Quy tắc vẫn ở `features.py`. Tệp này chỉ
   trả lời những câu hỏi **của màn hình**: hiện cái gì, sáng tab nào, chip ghi số
   mấy. Không quyết định giá, không kiểm quyền, không gọi engine để sinh tiếng.

⚠️ Và nó phải RẺ. Nó chạy ở **mọi** lượt dựng trang, nên mỗi truy vấn thêm vào
   đây là một truy vấn nhân với số lần khách bấm. Hôm nay: đúng một `COUNT`.
"""
from __future__ import annotations

from platform_core.i18n import N_

from . import gia, sidecar_client
from .manifest import MANIFEST
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

#: Khoá `nav_key` của từng màn. Phải khớp `NavEntry.nav_key` trong `manifest.py`,
#: và `tests/test_344_ltt_voice_vo.py` chốt hai bên khớp nhau.
#:
#: 🔴 VÌ SAO CẦN CHỐT: `base.html` sáng tab bằng phép so `nav == entry.nav_key`.
#:    Khi hai bên lệch, phép so trả False và **không có lỗi nào cả** — tab chỉ
#:    lặng lẽ không sáng. Đó đúng là lỗi đang sống trước P1: `_ngu_canh()` cũ
#:    không đặt `nav` bao giờ, nên cả ba tab của Voice đều xám kể từ ngày phát
#:    hành. Không một phép kiểm nào bắt được, vì trang vẫn trả 200.
NAV_STUDIO = "ltt_voice"
NAV_GIONG = "ltt_voice_giong"
NAV_DU_AN = "ltt_voice_du_an"
NAV_LO = "ltt_voice_lo"
NAV_LICH_SU = "ltt_voice_lich_su"
NAV_API = "ltt_voice_api"

#: Màn chưa xây: nhãn + câu nói thật về thứ sẽ có. Nền tảng đã gắn badge "đang
#: xây" lên tab qua `NavEntry.built=False`; đây là nội dung của chính trang đó.
#:
#: ⭐ VÌ SAO CÓ TRANG THẬT THAY VÌ ĐỂ 404: tab đã hiện trên thanh thì bấm vào
#:    phải tới một chỗ nói được điều gì đó. Một tab dẫn tới 404 tệ hơn không có
#:    tab — nó biến một lời hứa thành một lỗi.
#:
#: ⛔ Và trang này KHÔNG được vẽ giao diện giả. Nó nói sẽ có gì, không mô phỏng
#:    cái sẽ có. Một màn hình giả trông như đã xong là cách nhanh nhất để một
#:    phiên sau tưởng nó đã xong.
CHUA_XAY = {
    NAV_API: {
        "tieu_de": N_('API'),
        "mo_ta": N_('Gọi giọng của bạn từ mã nguồn của bạn, bằng mã giọng đã có.'),
        "sap_co": (
            N_('Mã giọng nào gọi được, và ví dụ gọi thử sẵn.'),
            N_('Ví dụ cURL, Python, JavaScript cho đúng công cụ giọng nói.'),
            N_('Khoá, hạn mức và nhật ký dùng chung với khu Lập trình viên.'),
        ),
    },
}


def dem_dang_chay(db, owner_id: str) -> int:
    """Số việc của KHÁCH NÀY trong app này đang chờ hoặc đang chạy.

    ⛔ Lọc theo `user_id`, không đếm toàn hệ thống. Chip "Hàng đợi 2" ở ảnh tham
       chiếu là một câu về **việc của tôi**; đếm cả máy chủ sẽ cho khách thấy tải
       của người khác — vừa vô nghĩa với họ, vừa là rò rỉ quy mô kinh doanh.

    Không đếm được thì trả 0 và **không** làm sập trang: một con số trang trí
    không đáng để đánh đổi một màn hình trắng.
    """
    try:
        from sqlalchemy import func, select

        from platform_core.models import Job
        return int(db.execute(
            select(func.count()).select_from(Job).where(
                Job.user_id == str(owner_id),
                Job.app_slug == MANIFEST.slug,
                Job.status.in_(("queued", "running")))
        ).scalar() or 0)
    except Exception:  # noqa: BLE001 - chip trang tri, khong duoc lam sap trang
        import logging
        logging.getLogger(__name__).warning("khong dem duoc hang doi", exc_info=True)
        return 0


def ngu_canh(request, user, *, nav_key: str, hang_doi: int = 0, **them) -> dict:
    """Bộ khoá Jinja mà MỌI màn Voice đều nhận.

    `nav_key` bắt buộc và không có mặc định — có mặc định thì một trang mới quên
    truyền sẽ lặng lẽ sáng nhầm tab, và đó đúng là loại lỗi không ai báo.
    """
    d = {
        "request": request,
        "user": user,
        "manifest": MANIFEST,
        # `nav` là tên mà `base.html` đọc. Đừng đổi tên khoá này cho "gọn hơn".
        "nav": nav_key,
        "tran_ky_tu": TRAN_KY_TU_CONG_KHAI,
        "bang_gia": gia.bang_gia(),
        "cong_san_sang": sidecar_client.san_sang(),
        "hang_doi": hang_doi,
    }
    d.update(them)
    return d
