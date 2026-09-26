"""HỒ SƠ DỊCH — một lời gọi cho CẢ video, quyết quan hệ nhân vật MỘT lần.

🔴 **Vì sao tệp này tồn tại.** `dich_mot_lo` là **vô trạng thái**: mỗi lô chỉ thấy
   `{ma: chu}` của chính nó. Một phim 74 đoạn đi 4 lô ⇒ **4 lần** quyết lại quan hệ
   nhân vật, độc lập nhau. Tiếng Việt mã hoá **quan hệ** vào đại từ, nên người xem
   nghe thấy quan hệ **đổi giữa video** (`ông` → `cậu` → `bạn`).

⭐ Một lời gọi thêm cho **cả video** (~16 giây) thay cho hàng chục lần đoán lại.
"""
from __future__ import annotations

import json
import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

KHOA = ("the_loai", "so_nguoi_noi", "bang_dai_tu", "bang_ten_rieng", "giong_van")


class HoSoDichLoi(ValueError):
    """Model không trả về hồ sơ đọc được."""


def _doc(noi_dung: str) -> dict:
    van = str(noi_dung or "").strip()
    dau, cuoi = van.find("{"), van.rfind("}")
    if dau < 0 or cuoi < dau:
        raise HoSoDichLoi(_t('Model không trả về JSON đọc được.'))
    try:
        goc = json.loads(van[dau:cuoi + 1])
    except json.JSONDecodeError as exc:
        raise HoSoDichLoi(_t('Model trả về JSON hỏng.')) from exc
    if not isinstance(goc, dict):
        raise HoSoDichLoi(_t('Model trả về JSON sai hình dạng.'))
    return {
        "the_loai": str(goc.get("the_loai") or ""),
        "so_nguoi_noi": int(goc.get("so_nguoi_noi") or 0),
        "bang_dai_tu": dict(goc.get("bang_dai_tu") or {}),
        "bang_ten_rieng": dict(goc.get("bang_ten_rieng") or {}),
        "giong_van": str(goc.get("giong_van") or ""),
    }


def dung(db, ban_ghi: dict, *, ctx=None) -> dict:
    """MỘT lời gọi. Hỏng thì trả hồ sơ RỖNG — ⛔ không làm chết lượt chạy."""
    from . import ai

    dong = [f'{d["ma"]}: {d["chu"]}' for d in (ban_ghi.get("doan") or [])]
    tin = [
        {"role": "system", "content": (
            "Doc toan bo loi thoai cua mot video roi tra ve DUY NHAT mot doi "
            "tuong JSON voi dung cac khoa: the_loai, so_nguoi_noi, bang_dai_tu, "
            "bang_ten_rieng, giong_van.\n"
            "bang_dai_tu: voi MOI cap vai, ghi tu tu xung (`toi`) va tu goi "
            "(`goi`) bang tieng Viet se dung suot ca video.\n"
            "bang_ten_rieng: ten goc -> dang viet tieng Viet, chot MOT lan.\n"
            "Khong giai thich gi them.")},
        {"role": "user", "content": "\n".join(dong)},
    ]
    try:
        kq = ai.goi(db, ai.HO_SO_DICH, tin, ctx=ctx, temperature=0.2)
        return _doc(kq["noi_dung"])
    except Exception as exc:  # noqa: BLE001
        # ⭐ Hồ sơ là thứ làm bản dịch TỐT HƠN, ⛔ không phải thứ nó cần để CHẠY.
        #    Hỏng thì đi tiếp với hồ sơ rỗng và NÓI RA, ⛔ không làm chết lượt chạy.
        log.warning("khong dung duoc ho so dich (%s: %s)", type(exc).__name__, exc)
        return {k: ({} if k.startswith("bang_") else "") for k in KHOA}
