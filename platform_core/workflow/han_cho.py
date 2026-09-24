"""Hạn chờ — CỘNG DỒN, neo `run.created_at` (plan wf-v2 P4 T5).

🔴 VÌ SAO NEO VÀO `run.created_at` CHỨ KHÔNG VÀO LÚC MỞ ĐIỂM CHỜ

Một hạn tính từ *lúc mở điểm chờ* cộng dồn được vô hạn: mười `core.delay` nối
tiếp, mỗi cái "tối đa 7 ngày", là **70 ngày** — và trong suốt 70 ngày ấy khoản
giữ chỗ credit của run vẫn bị treo (`tien.giu_cho_run`, một khoản mỗi run).
Không ai khai ra con số 70 ngày; nó chỉ **xuất hiện**.

⇒ Hạn của MỌI điểm chờ trong một run bị kẹp bởi **một** mốc chung:

      `run.created_at + TRAN_CHO_CONG_DON`

  Cái nào tới trước — hạn riêng của điểm chờ, hay mốc chung — cái đó thắng.

⭐ Và trần ấy phải ≤ `dong_co.TRAN_RUN` (20 giờ), nếu không ta hứa một hạn chờ
   mà TTL của run sẽ cắt trước. Một hạn không bao giờ tới là một hạn nói dối:
   node sẽ chết vì `TIMED_OUT` của cả run chứ không vì `che_do_het_han` mà
   người soạn đã chọn, và hai đường đó kết thúc khác nhau.

⚠️ `dong_co` import mô-đun này? **Không** — chiều ngược lại. Hằng `TRAN_RUN`
   được đọc bằng import CỤC BỘ trong `tran_cua_run()` để không dựng một vòng
   import (`dong_co` → `nut_loi` → `cho.py` → `han_cho`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

#: ⛔ Danh sách ĐÓNG (spec §5.7 `waitpoint.che_do_het_han`). Một chuỗi lạ ở đây
#: là một điểm chờ hết hạn mà không ai biết xử lý ra sao — nó sẽ đứng tới TTL
#: 20 giờ **với tiền bị giữ**, và không dòng nào nói vì sao.
CHE_DO_HET_HAN = ("fail", "route", "approve", "reject")

#: Mặc định theo loại node (spec §5.7): *"`core.human` mặc định `reject`,
#: `core.wait` mặc định `fail`"*.
MAC_DINH_THEO_KIND = {"HUMAN": "reject", "WEBHOOK": "fail", "EVENT": "fail",
                      "DELAY": "fail"}

#: Trần CỘNG DỒN của cả một run. Bằng đúng `dong_co.TRAN_RUN` chứ không hơn —
#: xem docstring mô-đun.
_TRAN_MAC_DINH_H = 20


class LoiHanCho(ValueError):
    """Một `che_do_het_han` không nằm trong tập đóng."""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kiem_che_do(che_do: str) -> str:
    ten = str(che_do or "fail")
    if ten not in CHE_DO_HET_HAN:
        raise LoiHanCho(
            f"che_do_het_han la: {ten!r} (chi {list(CHE_DO_HET_HAN)})")
    return ten


def che_do_mac_dinh(kind: str) -> str:
    return MAC_DINH_THEO_KIND.get(str(kind).upper(), "fail")


def tran_cua_run(run) -> datetime:
    """Mốc CHUNG: `run.created_at + TRAN_CHO_CONG_DON`.

    ⚠️ `created_at` là `DateTime(timezone=True)`: SQLite trả **naive**,
       PostgreSQL thật trả **aware**. Bỏ `tzinfo` trước khi cộng — cùng bài
       học đã đo ở `dong_co.ttl` (`test_1720`), nơi một phép so aware-vs-naive
       ném `TypeError` **chỉ trên production**.
    """
    from platform_core.workflow.dong_co import TRAN_RUN

    goc = getattr(run, "created_at", None) or _bay_gio()
    if getattr(goc, "tzinfo", None) is not None:
        goc = goc.replace(tzinfo=None)
    return goc + min(TRAN_RUN, timedelta(hours=_TRAN_MAC_DINH_H))


def han_cho(run, *, giay: Optional[float] = None,
            moc: Optional[datetime] = None) -> Optional[datetime]:
    """Hạn THỰC của một điểm chờ = `min(hạn riêng, mốc chung của run)`.

    - `giay`/`moc` rỗng ⇒ người soạn không đặt hạn riêng ⇒ **vẫn** trả mốc
      chung. "Không hạn" ở mức một node không có nghĩa "không hạn" ở mức run;
      cái thứ hai là thứ giữ tiền.
    - Hạn riêng **quá** mốc chung ⇒ bị kẹp xuống, im lặng và có chủ ý: từ chối
      lúc publish sẽ chặn một đồ thị hợp lệ chỉ vì nó lạc quan.
    """
    chung = tran_cua_run(run)
    rieng: Optional[datetime] = None
    if moc is not None:
        rieng = moc.replace(tzinfo=None) if moc.tzinfo else moc
    elif giay is not None and float(giay) > 0:
        rieng = _bay_gio() + timedelta(seconds=float(giay))
    if rieng is None:
        return chung
    return min(rieng, chung)


__all__ = ["CHE_DO_HET_HAN", "MAC_DINH_THEO_KIND", "LoiHanCho", "che_do_mac_dinh",
           "han_cho", "kiem_che_do", "tran_cua_run"]
