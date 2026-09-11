"""NGHE THỬ VĂN BẢN CỦA KHÁCH — miễn phí, có trần cứng (U-13).

## Vì sao nó đáng có

`nghe_thu.py` cho khách nghe **một câu cố định** ở mỗi giọng. Đủ để nghe chất
giọng, không đủ để trả lời câu khách thật sự hỏi: *"tên công ty tôi thì máy đọc
ra sao?"* — và tên riêng là đúng chỗ engine hay sai nhất, cũng là chỗ
`VoiceTuDien` sinh ra để chữa.

Không có cửa này, cách duy nhất để biết là **trả tiền một lượt đọc**.

## 🔴 BỐN CÁI TRẦN, VÀ CHÚNG CHẶN BỐN THỨ KHÁC NHAU

| trần | chặn |
|---|---|
| `TRAN_KY_TU` | biến cửa này thành một TTS miễn phí |
| `MOI_GIO` | một tài khoản đốt GPU cả ngày |
| **suất `vieneu_gpu`** | một lượt miễn phí làm khách TRẢ TIỀN phải chờ |
| `TRAN_THOI_GIAN_S` | một lượt treo giữ luôn worker web |

⛔ Ba cái đầu là chuyện lạm dụng. **Cái thứ ba mới là cái quan trọng nhất**, và
   nó không phải chuyện lạm dụng: ngay cả một khách hoàn toàn tử tế, dùng đúng
   6 lượt/giờ, vẫn sẽ giành card khỏi một job đã trả tiền nếu ta không xếp sau.

⇒ `hold_persisted` trả `None` khi hết suất, **không chờ**. Bận thì cửa này trả
  lời *"máy đang bận"* ngay lập tức. Nó là công dân hạng hai của cái card, có
  chủ ý.

## ⚠️ PHƠI NHIỄM — nói bằng số, không bằng cảm giác

    6 luot/gio x 160 ky tu ~ 8,9 giay tieng moi luot (18 ky tu/giay)
    = ~53 giay tieng/gio/tai khoan
    = ~10,7 credit/gio/tai khoan neu tinh tien (0,2 credit/giay)

Đó là **trần trên**, và chỉ đạt được khi card rảnh suốt. Ta chấp nhận con số
ấy để đổi lấy việc khách chọn đúng giọng ngay lần đầu thay vì trả tiền hai lần.

⛔ Ngày con số ấy thành vấn đề, thứ phải đổi là `MOI_GIO` — **không phải** bỏ
   phép xếp sau admission. Bỏ phép ấy đổi một chi phí đo được lấy một hàng đợi
   khách trả tiền, và không ai sẽ thấy sự đánh đổi đó xảy ra.

## ⚠️ Bộ đếm nằm TRONG BỘ NHỚ MỘT TIẾN TRÌNH

Cùng ràng buộc với `server/usage_rate_limit.py` (ADR-005). Với `LTT_WORKER_POOLS`
nhiều tiến trình web, trần thật là `MOI_GIO × số tiến trình`.

Nói ra chứ không giấu: một trần "6" mà thật ra là "18" là một trần **nói dối**,
và người đọc mã sẽ tin con số chứ không tin kiến trúc. Trần cứng thật sự nằm ở
suất `vieneu_gpu` — nó là **một** trên toàn cụm, và nó là thứ duy nhất không
nhân lên theo số tiến trình.
"""
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger(__name__)

#: Trần ký tự MỘT lượt nghe thử. Một câu, không phải một đoạn.
#:
#: ⛔ 160, không phải `TRAN_MOI_LUOT_SINH` (1.500). Dùng chung trần với đường
#:    trả tiền là mở đúng cái cửa mà mọi trần khác ở đây sinh ra để đóng.
TRAN_KY_TU = 160

#: Số lượt mỗi giờ, mỗi tài khoản.
MOI_GIO = 6

#: Cửa sổ trượt, giây.
CUA_SO_S = 3600.0

#: Trần thời gian cho một lượt. Ngắn hơn nhiều so với đường job.
#:
#: ⚠️ 45 giây nghe rộng cho một câu ~9 giây tiếng, và nó rộng có chủ ý: lượt
#:    ĐẦU sau khi dịch vụ khởi động lại phải nạp model (đo: 19,4 giây nguội).
#:    Đặt 20 giây thì cửa này hỏng đúng vào buổi sáng mỗi ngày, và hỏng theo
#:    kiểu "thỉnh thoảng" — loại khó lần nhất.
TRAN_THOI_GIAN_S = 45.0

_KHOA = threading.Lock()
#: `uid -> [thời điểm, ...]`
_SO: dict = {}


def con_lai(uid: str) -> int:
    """Số lượt còn lại trong giờ này. Không đổi trạng thái."""
    with _KHOA:
        return max(0, MOI_GIO - len(_loc(uid)))


def _loc(uid: str) -> list:
    """Bỏ mốc đã ra khỏi cửa sổ. **Gọi khi đang giữ khoá.**"""
    moc = time.time() - CUA_SO_S
    cac = [t for t in _SO.get(str(uid), ()) if t > moc]
    _SO[str(uid)] = cac
    return cac


def xin_luot(uid: str) -> bool:
    """Xin một lượt. `True` = được, và **đã trừ**.

    🔴 KIỂM VÀ TRỪ TRONG CÙNG MỘT LẦN GIỮ KHOÁ. Tách thành `con_lai()` rồi
       `ghi_nhan()` là để hai request đồng thời cùng đọc "còn 1" rồi cùng đi
       tiếp — trần 6 thành 7, và nó chỉ xảy ra khi có tải, tức đúng lúc trần
       quan trọng nhất.
    """
    if not uid:
        return False
    with _KHOA:
        cac = _loc(uid)
        if len(cac) >= MOI_GIO:
            return False
        cac.append(time.time())
        return True


def hoan_luot(uid: str) -> None:
    """Trả lại lượt vừa trừ khi việc **không hề chạy**.

    ⭐ Chỉ gọi khi ta từ chối TRƯỚC khi chạm GPU — ví dụ card đang bận. Trừ một
       lượt cho một việc chưa từng xảy ra là phạt khách vì máy ta bận.

    ⛔ KHÔNG hoàn khi engine ném lỗi giữa chừng: GPU đã chạy, và một đường hoàn
       ở đó là một vòng lặp thử-lại miễn phí không giới hạn.
    """
    with _KHOA:
        cac = _SO.get(str(uid)) or []
        if cac:
            cac.pop()


def xoa(uid: str = "") -> None:
    """Xoá bộ đếm. Cho phép kiểm, và cho một lượt gỡ tay."""
    with _KHOA:
        if uid:
            _SO.pop(str(uid), None)
        else:
            _SO.clear()


def sinh(text: str, *, preset: str, timeout: float) -> bytes:
    """Sinh MỘT lượt nghe thử. Ranh giới mỏng quanh `features.goi_cong`.

    ⭐ VÌ SAO MỘT HÀM RIÊNG chứ không gọi thẳng `features.goi_cong` từ
       `routes/_p_nghe_thu.py`. Cửa đó đã giữ suất `vieneu_gpu` (một tài
       nguyên CẤP TIẾN TRÌNH); phép kiểm cho D006 cần MOCK được đúng một chỗ
       — lượt sinh THẬT — mà không phải dựng cả một sidecar giả. Một tên hàm
       ổn định ở đây là chỗ mock đó neo vào.

    ⚠️ Không bọc try/except ở đây: người gọi (`nghe_thu_van_ban`) cần đúng
       exception gốc để quyết định có hoàn lượt hay không — xem docstring
       `hoan_luot`.
    """
    from . import features

    wav, _dau = features.goi_cong(text, preset=preset, timeout=timeout)
    return wav
