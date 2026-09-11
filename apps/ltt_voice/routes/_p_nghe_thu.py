"""Cửa NGHE THỬ VĂN BẢN CỦA KHÁCH (U-13).

Luật, ngân sách và lý do của từng cái trần: `apps/ltt_voice/nghe_thu_cua_toi.py`.
Tệp này **chỉ** lo HTTP — đọc request, kiểm quyền/CSRF, gọi service, dựng phản
hồi. Không quy tắc nghiệp vụ nào ở đây.
"""
from __future__ import annotations

import logging

from ._chung import (Depends, Form, JSONResponse, Request, _het_phien,
                     _t, _uid, giong_mau, lan_ngon_ngu, require_login, router,
                     user_hien_tai, verify_csrf_token)

log = logging.getLogger(__name__)


@router.post("/nghe-thu-van-ban")
def nghe_thu_van_ban(request: Request, text: str = Form(""),
                     preset: str = Form(""), csrf_token: str = Form(""),
                     user=Depends(user_hien_tai), _=Depends(require_login)):
    """Một câu của khách, đọc bằng một giọng mẫu. Miễn phí, có trần cứng.

    ⛔ CHỈ `preset`, KHÔNG `voice_id`.

       Không phải vì giọng nhân bản đắt hơn — nó cùng giá. Là vì cửa này tồn
       tại để **chọn giữa các giọng mẫu**, và mở nó cho giọng nhân bản kéo theo
       một phép kiểm sở hữu thứ hai trên một đường **miễn phí**. `giai_giong`
       là chỗ duy nhất kiểm sở hữu; thêm một chỗ thứ hai là thêm một chỗ có thể
       sai, để đổi lấy một tính năng không ai xin.

    ⚠️ Trả JSON (âm thanh mã hoá base64), không qua kho. Không có gì để lưu: nó
       ngắn, miễn phí, và không nằm trong lịch sử của khách. Cất nó vào kho là
       dựng một thư mục nở ra mãi mà không ai đọc lần thứ hai.

    🔴 D006 (2026-09-11): VĂN BẢN của khách có thể LỆCH LÀN với giọng mẫu đã
       chọn (vd một câu tiếng Anh, đọc bằng một giọng mẫu làn `vi`). Quyết định
       chốt là **VẪN PHÁT**, chỉ **NÓI RA**: `lan_ngon_ngu.quyet_dinh` chạy để
       dựng `phan_quyet`, nhưng KHÔNG chặn lượt sinh — khác hẳn cửa `/tao`
       (`features.giai_giong`), nơi cùng một sự lệch làn CHẶN THẲNG trước khi
       tốn credit. Ở đây không có credit nào để bảo vệ; nghe thử là **để khách
       tự nghe thấy** giọng đọc lệch làn ra sao, một bài học trực quan hơn hẳn
       một câu lỗi 400.
    """
    from .. import nghe_thu_cua_toi as NT

    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    uid = _uid(user)
    tho = (text or "").strip()
    if not tho:
        return JSONResponse({"ok": False, "loi": _t("Chưa có văn bản.")},
                            status_code=400)
    if len(tho) > NT.TRAN_KY_TU:
        return JSONResponse({"ok": False, "loi": _t(
            "Nghe thử tối đa {n} ký tự — một câu."
        ).format(n=NT.TRAN_KY_TU)}, status_code=400)
    if not giong_mau.hop_le(preset):
        return JSONResponse({"ok": False, "loi": _t("Giọng không hợp lệ.")},
                            status_code=400)

    # D006 — HỎI `quyet_dinh` để HIỆN, KHÔNG để CHẶN (xem docstring ở trên).
    # SAU hai cổng kiểm ở trên (văn bản trống, trần ký tự, preset hợp lệ),
    # TRƯỚC khi xin lượt/sinh — `pq` phải sẵn sàng dù nhánh nào phía dưới chạy.
    pq = lan_ngon_ngu.quyet_dinh(giong_mau.lan_cua(preset), tho)
    cau_pq = lan_ngon_ngu.cau_cho_khach(pq) if not pq.cho_phep else ""

    # 🔴 XIN LƯỢT TRƯỚC KHI CHẠM GPU, và xin bằng MỘT phép nguyên tử.
    if not NT.xin_luot(uid):
        return JSONResponse({"ok": False, "loi": _t(
            "Bạn đã dùng hết {n} lượt nghe thử trong giờ này."
        ).format(n=NT.MOI_GIO)}, status_code=429)

    # 🔴 XẾP SAU KHÁCH TRẢ TIỀN. `hold_persisted` trả `None` khi hết suất và
    #    **không chờ** — nên một lượt miễn phí không bao giờ làm một job đã
    #    tính tiền phải xếp hàng sau nó.
    #
    # ⭐ Và ta HOÀN lượt trong nhánh này: từ chối vì máy ta bận thì không được
    #    tính vào ngân sách của khách.
    from platform_core.llm import admission

    with admission.hold_persisted(
            resource="vieneu_gpu", slots=1, user_id=uid,
            mode="nghe_thu", holder_id=f"nghethu:{uid}") as suat:
        if suat is None:
            NT.hoan_luot(uid)
            return JSONResponse({"ok": False, "loi": _t(
                "Máy đang bận tạo tiếng cho lượt khác. Thử lại sau ít giây."
            )}, status_code=503)
        try:
            wav = NT.sinh(tho, preset=preset, timeout=NT.TRAN_THOI_GIAN_S)
        except Exception as e:  # noqa: BLE001 - cua nay khong duoc lam sap trang
            # ⛔ KHÔNG hoàn lượt ở đây. GPU đã chạy; một đường hoàn ở nhánh lỗi
            #    là một vòng thử-lại miễn phí không giới hạn.
            log.warning("nghe thu van ban hong: %s: %s", type(e).__name__, e)
            return JSONResponse({"ok": False, "loi": _t(
                "Không tạo được tiếng lúc này.")}, status_code=502)

    import base64

    return JSONResponse({
        "ok": True,
        # base64, không phải WAV thẳng: D006 buộc đáp về phải mang thêm
        # `phan_quyet` bên cạnh âm thanh — một `Response` nhị phân không có
        # chỗ cho trường thứ hai đó.
        "audio_b64": base64.b64encode(wav).decode("ascii"),
        "phan_quyet": {"cho_phep": pq.cho_phep, "ma_loi": pq.ma_loi,
                       "cau": cau_pq},
    }, headers={
        "Cache-Control": "no-store",
        "X-Luot-Con-Lai": str(NT.con_lai(uid)),
    })
