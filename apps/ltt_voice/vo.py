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
from server.auth.csrf import issue_csrf_token

from . import gia, sidecar_client
from .manifest import MANIFEST
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI, TRAN_MOI_LUOT_SINH

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
NAV_LICH_SU = "ltt_voice_lich_su"
NAV_API = "ltt_voice_api"

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
        # ⭐ Giao diện cần CẢ HAI trần, vì chúng nói hai điều khác nhau với
        #    khách: `tran_ky_tu` là "gửi được bao nhiêu", `tran_moi_luot` là
        #    "chia làm mấy đoạn". Trước 03/09 chúng là một số nên ô đếm chỉ cần
        #    một; nay ô đếm ước được số đoạn thì nó cần số thứ hai.
        "tran_moi_luot": TRAN_MOI_LUOT_SINH,
        # ⚠️ CÙNG hằng số mà phần giữ credit dùng (`gia.KY_TU_MOI_GIAY_UOC`),
        #    KHÔNG phải một con số riêng cho giao diện. Hai chỗ ước thời lượng
        #    bằng hai tỉ lệ khác nhau là hai chỗ nói với khách hai con số khác
        #    nhau về cùng một văn bản — và họ sẽ tin con số nào tiện hơn.
        "ky_tu_moi_giay": gia.KY_TU_MOI_GIAY_UOC,
        "bang_gia": gia.bang_gia(),
        "cong_san_sang": sidecar_client.san_sang(),
        "hang_doi": hang_doi,
        # 🔴 THIẾU DÒNG NÀY LÀM CHẾT MỌI CỬA POST CỦA APP, và nó chết IM LẶNG
        #    suốt từ ngày phát hành cho tới khi CSRF được thi hành thật.
        #
        #    Mọi template Voice viết `value="{{ csrf_token }}"`. Không có khoá
        #    này trong ngữ cảnh thì Jinja render **chuỗi rỗng** — không cảnh
        #    báo, không lỗi. Và `verify_csrf_token` khi đó cũng đang bị bỏ qua
        #    kết quả, nên hai lỗi triệt tiêu nhau và mọi thứ trông vẫn chạy.
        #
        #    Vá lỗ CSRF (thi hành thật) gỡ một trong hai, và lỗi còn lại hiện
        #    ra ngay: **mọi form trả 400 "Phiên đã hết hạn"** — tạo tiếng, tạo
        #    giọng, tắt giọng, dự án, chạy lô. Đo thật trên production
        #    31/08/2026: form đăng xuất của `base.html` có token 43 ký tự, mọi
        #    form của app có `value=""`.
        #
        # ⭐ Bài học không phải "nhớ thêm token". Là: **hai lỗi triệt tiêu nhau
        #    thì sửa một cái sẽ làm lộ cái kia**, và cái lộ ra trông y hệt một
        #    hồi quy do bản vá gây ra. Nó không phải.
        "csrf_token": issue_csrf_token(request),
    }
    d.update(them)
    return d
