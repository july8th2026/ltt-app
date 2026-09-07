"""_p_duyet.py — hai cửa duyệt cho bước tốn tiền. (H44 P04)

    GET  /chatltt/api/duyet/dang-cho          → phiếu còn chờ (dựng lại sau reload)
    POST /chatltt/api/duyet/{approval_id}     → `duyet` hoặc `tu_choi`

## Không gắn cờ tính năng, và đó là lựa chọn có lý do

`LTT_CHATLTT_V3_TOOLS` tắt ⇒ không phiếu nào được tạo ⇒ `dang-cho` trả `[]` và
mọi `POST` trả 404. Hai cửa này **tự vô hại** khi chưa có dữ liệu.

⛔ Gắn cờ vào đây thì phải gắn bằng `Depends` — vì `Depends` chạy **trước** thân
hàm, nên một phép kiểm cờ viết trong thân sẽ không bao giờ chạy: `require_login`
đã kịp trả 303 về `/login` rồi. Đó là cái bẫy đã ghi trong
`cong-co-phai-dung-truoc-require-login`. Thêm một `Depends` nữa để đóng một cửa
vốn đã rỗng là trả giá thật cho một lợi ích tưởng tượng.

## Cửa GHI ⇒ CSRF, và phải gọi đúng tên `kiem_csrf`

`test_628::test_moi_cua_GHI_deu_doi_CSRF` đọc **mã nguồn** từng route và đòi
thấy đúng tên ấy. Nó bắt được một cửa thiếu CSRF ở lượt gate đầu tiên sau khi
cửa tải ảnh ra đời.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request

from apps.chatltt.routes._chung import doc_json, json_ok, kiem_csrf, loi, router, uid
from apps.chatltt.services import duyet as D
from apps.chatltt.services import luot_v3
from server.auth.session import require_login
from server.deps import get_db

log = logging.getLogger("ltt.chatltt.duyet")


@router.get("/api/duyet/dang-cho")
def dang_cho(request: Request, run_id: str = "",
             _=Depends(require_login), db=Depends(get_db)):
    """Phiếu còn chờ của **chính người gọi**.

    ⭐ Cửa này là thứ làm cho "duyệt bền" nhìn thấy được: người dùng tải lại
       trang giữa lúc chờ vẫn thấy nút, thay vì một lượt đứng im không lý do.
    """
    return json_ok({"items": D.dang_cho(db, user_id=uid(request), run_id=run_id)})


@router.post("/api/duyet/{approval_id}")
async def quyet(request: Request, approval_id: str,
                _=Depends(require_login), db=Depends(get_db)):
    """Đồng ý hoặc từ chối một phiếu.

    ⛔ `quyet_dinh` là **enum đóng**. Nhận chuỗi tuỳ ý rồi so `== "duyet"` thì
       mọi giá trị lạ lặng lẽ thành "từ chối" — một lỗi chính tả ở client biến
       thành một quyết định thay người dùng.
    """
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")

    # ⛔ KHỚP CHÍNH XÁC — không `.strip().lower()`.
    #
    #    `"Duyet"` không mơ hồ, nên nhận nó nghe vô hại. Nhưng chuẩn ở kho này
    #    cho một giá trị **có hậu quả** đã được đặt ở `co_v3.BAT`: chỉ ba cách
    #    viết, mọi thứ khác là không. Lý do ở đó cũng đúng ở đây — một trường
    #    nhận nhiều cách viết là một trường mà không ai biết chắc client đang
    #    gửi cái gì, và chỗ này quyết định tiêu tiền của khách.
    #
    # ⭐ Nghiêm hơn không mất gì: client là app React của chính ta, gửi một
    #    hằng số. Một `400` ở đây là một lỗi lập trình bị bắt sớm, không phải
    #    một người dùng bị chặn.
    qd = than.get("quyet_dinh")
    if qd not in (D.DUYET, D.TU_CHOI):
        return loi(400, "tham_so",
                   f"quyet_dinh phai dung bang {D.DUYET!r} hoac {D.TU_CHOI!r}")

    sua = than.get("doi_so_da_sua")
    if sua is not None and not isinstance(sua, dict):
        return loi(400, "tham_so", "doi_so_da_sua phai la mot object JSON")

    user_id = uid(request)
    try:
        if qd == D.DUYET:
            p = D.duyet(db, user_id=user_id, approval_id=approval_id,
                        quyet_boi=user_id, doi_so_da_sua=sua)
        else:
            p = D.tu_choi(db, user_id=user_id, approval_id=approval_id,
                          quyet_boi=user_id)
    except D.KhongTimThay:
        # 404 cho cả "không có" lẫn "của người khác" — nói "không có quyền" là
        # xác nhận phiếu ấy tồn tại (cùng luật `hoi_thoai.py` của V1).
        return loi(404, "khong_tim_thay")
    except D.DaQuyetRoi as e:
        # 409, không phải 400: yêu cầu hợp lệ, chỉ là thế giới đã đổi. Client
        # phân biệt được "tôi gửi sai" với "ai đó đã bấm trước tôi".
        return loi(409, "da_quyet", str(e))

    db.commit()

    # ── Bấm xong thì lượt phải CHẠY TIẾP ─────────────────────────────────
    #
    # ⛔ Không có khúc này thì "duyệt" chỉ ghi một hàng: người dùng bấm đồng ý,
    #    thấy nút biến mất, và lượt đứng im mãi mãi. Đó không phải một cổng
    #    duyệt, đó là một cái nút không nối vào đâu.
    #
    # 🔴 Và phải kiểm CÒN PHIẾU NÀO CHƯA QUYẾT KHÔNG. Một lượt có hai lời gọi có
    #    phí thì có hai phiếu; chạy tiếp khi mới một phiếu được bấm là chạy một
    #    việc người dùng chưa nhìn tới.
    tiep = False
    if luot_v3.nen_chay_tiep(db, user_id=user_id, run_id=p.run_id):
        try:
            luot_v3.chay_tiep_nen(p.run_id, user_id=user_id)
            tiep = True
        except Exception:                                       # noqa: BLE001
            # Quyết định ĐÃ ghi và đã commit. Không khởi động lại được lượt là
            # một sự cố, nhưng không được biến nó thành "duyệt thất bại" —
            # người dùng sẽ bấm lại và nhận 409.
            log.exception("khong khoi dong lai duoc run %s", str(p.run_id)[-8:])

    return json_ok(dict(D.su_kien_quyet(p), chay_tiep=tiep))
