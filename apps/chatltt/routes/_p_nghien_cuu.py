"""_p_nghien_cuu.py — bề mặt HTTP của vòng nghiên cứu. (H44 B6 bước 4)

    GET  /api/nghien-cuu/bao-gia                    uoc credit + PHAM VI
    POST /api/hoi-thoai/{conv_id}/nghien-cuu        nop job -> 202
    GET  /api/nghien-cuu/{job_id}                   trang thai + bao cao

⛔ Tệp này **chỉ lo HTTP**. Vòng lặp ở `services/nghien_cuu.py`, việc nối nguồn
   và model ở `jobs.py`.

## Route KHÔNG được gọi thẳng vòng lặp

§4 phép đo 5 của kế hoạch chốt điều này bằng một bánh cóc, và lý do là trần
**100 giây của Cloudflare**: vòng lặp gọi model nhiều lượt, nên chạy nó trong
một request là bảo đảm 524 cho mọi câu hỏi đáng hỏi. Route **nộp job**.

## 🔴 Cửa số dư là một ĐIỀU KIỆN, không phải một giá

`gia_nghien_cuu.credit_cost` là **0** có chủ đích — mọi credit chảy qua
`runtime_noi_bo` theo từng lượt model. Nhưng 0 nghĩa là job vào hàng đợi mà
không giữ chỗ, nên một tài khoản 0 credit vẫn nộp được rồi chết ở lượt đầu:
khách chờ vô ích và máy chủ làm không công.

⇒ Route từ chối khi số dư dưới `uoc_tran()`. Nó **không** trừ gì và **không**
  giữ gì — nên nó không tính hai lần thứ gì.

## Phạm vi được NÓI RA, không phải suy ra (bước 6, §1)

`/api/nghien-cuu/bao-gia` trả về `pham_vi` bằng tiếng Việt, và giao diện vẽ nó.
Một tính năng tên là *"nghiên cứu"* mà im lặng về việc nó **không đọc Internet**
là một lời hứa hỏng — khách sẽ hỏi một câu cần web và nhận một câu trả lời tự
tin dựng từ ba tài liệu kế toán.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request

from apps.chatltt import gia as GIA, gia_nghien_cuu as GNC
from apps.chatltt.routes._chung import (cong_nghien_cuu, doc_json, json_ok,
                                        kiem_csrf, loi, router, uid)
from apps.chatltt.services import nghien_cuu as NC
from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.session import require_login
from server.deps import get_db
from apps.chatltt.services import loi_ra_ngoai as LRN

log = logging.getLogger(__name__)

#: 🔴 Câu này là **hợp đồng với khách**, không phải chữ trang trí. §1 của kế
#:    hoạch: nền tảng không có khả năng tìm web (đo 07/09 — không một tệp nào
#:    khai `tavily`/`serper`/`brave`/`searx`), và mở một `web.tim` là một quyết
#:    định thương mại. `test_842` giữ nó.
#:
#: ⛔ `N_` ở đây và `_t()` ở chỗ dùng, **không** phải `_()` ngay tại module.
#:    `_()` dịch **lúc import**, tức đóng băng ngôn ngữ của tiến trình vào câu
#:    này — một khách đọc tiếng Anh sẽ nhận câu tiếng Việt, và đây đúng là câu
#:    không được phép không đọc được: nó là thứ duy nhất nói rằng sản phẩm
#:    KHÔNG đọc Internet.
PHAM_VI_GOC = N_('Đọc tài liệu bạn đã đính vào hội thoại này. Không tìm trên Internet.')


def pham_vi() -> str:
    """Câu phạm vi, dịch theo ngôn ngữ của **request đang chạy**."""
    return _t(PHAM_VI_GOC)


@router.get("/api/nghien-cuu/bao-gia")
async def bao_gia(request: Request, tran_vong: int = 0,
                  __=Depends(cong_nghien_cuu), _=Depends(require_login),
                  db=Depends(get_db)):
    """Ước credit **và** phạm vi, cho giao diện hiện TRƯỚC khi khách bấm."""
    from platform_core import credit

    n = int(tran_vong or 0) or NC.TRAN_VONG
    n = max(1, min(n, NC.TRAN_VONG))
    uoc = GNC.uoc_tran(n)
    so_du = int(credit.so_du(db, uid(request)))
    return json_ok({"uoc_credit": uoc, "tran_vong": n,
                    "tran_vong_toi_da": NC.TRAN_VONG,
                    "so_du": so_du, "du_credit": so_du >= uoc,
                    "pham_vi": pham_vi(),
                    "phien_ban_gia": GNC.PHIEN_BAN_GIA})


@router.post("/api/hoi-thoai/{conv_id}/nghien-cuu")
async def chay(conv_id: str, request: Request,
               __=Depends(cong_nghien_cuu), _=Depends(require_login),
               db=Depends(get_db)):
    """Nộp một lượt nghiên cứu. **202**, không phải 200 — nó chưa xong."""
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as J

    if not kiem_csrf(request):
        return loi(403, "csrf")
    than = await doc_json(request)
    cau_hoi = str(than.get("cau_hoi") or "").strip()
    if not cau_hoi:
        return loi(400, "tham_so", "thieu `cau_hoi`")
    n = int(than.get("tran_vong") or 0) or NC.TRAN_VONG
    n = max(1, min(n, NC.TRAN_VONG))

    user_id = uid(request)
    uoc = GNC.uoc_tran(n)
    so_du = int(credit.so_du(db, user_id))
    if so_du < uoc:
        # ⛔ 402 chu khong 400: khach doc duoc "het tien" khac han "sai tham so".
        return loi(402, "het_credit",
                   f"can khoang {uoc} credit, con {so_du}")

    try:
        bg = J.bao_gia("chatltt.nghien_cuu",
                       {GIA.KHOA_VIEC: GIA.VIEC_NGHIEN_CUU,
                        "conversation_id": conv_id, "cau_hoi": cau_hoi,
                        "tran_vong": n},
                       db=db, user_id=user_id)
        job = J.nop_job(db, user_id=user_id, bao_gia=bg,
                        correlation_id=conv_id)
        db.commit()
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Bat rong CO CHU Y nhung KHONG nuot — cung ly le `_p_tep.trich`.
        log.exception("nop job nghien cuu hong: conv=%s", conv_id[:8])
        return loi(400, "khong_nop_duoc", f"{type(e).__name__}: {e}"[:200])

    return json_ok({"job_id": job.id, "tran_vong": n, "pham_vi": pham_vi()}, 202)


@router.get("/api/nghien-cuu/{job_id}")
async def xem(job_id: str, request: Request,
              __=Depends(cong_nghien_cuu), _=Depends(require_login),
              db=Depends(get_db)):
    """Trạng thái job + báo cáo khi xong.

    ⛔ `get_owned` chứ không `db.get`: một job của người khác phải trả **404**,
       không phải 403 — cùng luật `kho_tep.mot`, phân biệt hai ca là tự khai
       rằng id ấy tồn tại.
    """
    from platform_core import job_history

    job = job_history.get_owned(db, uid(request), str(job_id))
    if job is None:
        return loi(404, "khong_thay", "khong tim thay luot nghien cuu")

    tt = str(getattr(job, "status", "") or "")
    ra: dict = {"job_id": job.id, "trang_thai": tt, "pham_vi": pham_vi()}
    if tt == "done":
        ra["bao_cao"] = dict(getattr(job, "result", None) or {})
    elif tt == "failed":
        # ⭐ Ly do di ra ngoai — mot luot hong im lang la mot luot khach
        #    cho mai. Nhung no dung tu MA, khong tu `job.error`:
        #    handler co the da boc than loi thuong nguon vao chuoi ay.
        ra["ly_do"] = LRN.cau("loi_noi_bo")
    return json_ok(ra)
