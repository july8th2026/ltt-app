"""
jobs.py — handler chạy trong worker, cho **cửa bất đồng bộ**. (H38)

    POST /api/v1/jobs {"tool": "text.chat", ...}  ->  worker  ->  handle()

⭐ Cửa này có được **miễn phí** nhờ khai `text.chat` trong manifest. Nó là đường
   lui khi prompt quá dài cho trần 125 giây mặc định của Cloudflare. Canary API
   thật gần public cap đã tốn 102 giây; phiên agent dài hoặc lượt sinh nhiều
   nghìn token vẫn có thể vượt dù engine chịu được cửa sổ 131K.

⛔ HANDLER KHÔNG TRỪ CREDIT. Nền tảng đã giữ chỗ theo `credit_cost` lúc submit và
   sẽ quyết toán quanh job. Trừ thêm ở đây là thu hai lần.

⛔ HANDLER KHÔNG CHỨA NGHIỆP VỤ. Nó chỉ mở phiên CSDL, gọi `features.chay`, và
   dịch kết quả — `AGENTS.md` mục 8.

⭐ HỦY CỨNG (Multi-Job T11). Trước bản này việc hủy ở đây chỉ **hợp tác**: worker
   chỉ thấy `status == cancelled` ở lần `ctx.progress()` kế tiếp, và handler này
   gọi `progress` đúng **hai** lần — một lần trước khi gọi model, một lần sau.
   Tức giữa hai lần ấy, một lượt 200K prefill chạy tới hết trên GPU cho một người
   đã bấm "hủy" từ lâu, và credit của họ nằm treo suốt khoảng đó.
"""
from __future__ import annotations

from apps.ltt_llm import features

#: Nhịp thăm `is_cancelled()` trong lúc gọi model (Multi-Job T11: 1 giây).
#: Cùng bậc với `ngat.NHIP_THAM_S`; để riêng vì cửa job đo trạng thái **bền**
#: (một truy vấn CSDL mỗi nhịp) chứ không đọc một cờ trong bộ nhớ.
NHIP_CANH_S = 1.0


def _ma_luot(ctx) -> str:
    """Mã lượt của job này. Đúng một nguồn: `job_id`.

    ⭐ Suy ra chứ không sinh mới, và đó là cả điểm của nó: người hủy chỉ cầm
       `job_id` trong tay (`POST /jobs/{id}/cancel`). Một mã ngẫu nhiên thì đúng
       về mặt duy nhất và **vô dụng** — không ai tra được nó từ phía ngoài.

    ⚠️ Tiền tố `job-`: cùng một không gian tên với các cửa khác sẽ dùng sổ lượt
       (cửa đồng bộ, cửa stream), nên một `job_id` không bao giờ đụng một mã của
       cửa khác. Cổng máy B lọc mã chỉ giữ chữ-số và `-_.:` (`api._id_sach`), nên
       chuỗi này đi qua nguyên vẹn.
    """
    ma = str(getattr(ctx, "job_id", "") or "")
    return f"job-{ma}" if ma else ""


def handle(params: dict, ctx=None) -> dict:
    """Một lượt sinh văn bản. Trả về đúng hình dạng `returns` của ToolSpec."""
    from platform_core.db import get_session
    from platform_core.job_runner import JobCancelled
    from platform_core.llm import huy_luot, ngat
    from platform_core.llm.cong_vlm import HuyError

    if ctx is not None:
        ctx.progress(5, "dang goi model")

    ma_luot = _ma_luot(ctx)
    gen = get_session()
    db = next(gen)
    try:
        def _goi():
            return features.chay(
                db, params, ma_luot=ma_luot,
                on_dispatch=(ctx.provider_dispatched if ctx is not None else None),
                on_rejected=(ctx.provider_rejected if ctx is not None else None))

        # ⭐ DÙNG LẠI `ngat.chay_canh_ngat`, KHÔNG ĐẺ LUỒNG CANH THỨ HAI.
        #
        #    Hàm ấy đã làm đúng ba việc cửa này cần, và mỗi việc đều có một bài
        #    học đứng sau (xem docstring của nó): chạy lời gọi trong một bản sao
        #    ngữ cảnh (nên sổ đóng là CÙNG một vật thể ở hai luồng), thăm theo
        #    nhịp, và **chờ luồng kết thúc** trước khi ném — chứ không bỏ mặc một
        #    luồng còn cầm phiên CSDL trong lúc đường hủy sắp quyết toán tiền.
        #    Viết lại ở đây là chép lại ba quyết định ấy, và bản chép sẽ lệch.
        #
        # ⚠️ Thứ nó KHÔNG làm là hủy theo **tên** — nó chỉ biết ngữ cảnh của
        #    chính nó. Đó là việc của `huy_luot`, và `phien()` dưới đây mở sổ tên
        #    cho lượt này (`_goi_openai` ghi cửa vào cả hai sổ).
        with huy_luot.phien(ma_luot):
            kq = ngat.chay_canh_ngat(
                _goi,
                ngat_chua=(ctx.is_cancelled if ctx is not None else None),
                nhip_s=NHIP_CANH_S)
    except ngat.KhachNgat:
        # ⛔ DỊCH SANG `JobCancelled`, đừng để `KhachNgat` thoát ra. `job_runner`
        #    chỉ nhận ra một lượt hủy qua đúng lớp ấy (`_chay_handler`); mọi
        #    ngoại lệ khác rơi vào nhánh `except Exception` ⇒ `jobq.fail()` ⇒ job
        #    mang trạng thái `error` thay vì `cancelled`, và ba lượt thử lại nữa.
        raise JobCancelled() from None
    except HuyError:
        # Cổng máy B đã trả 499 — ai đó (kể cả chính đường hủy này, từ nhánh
        # `/v1/huy`) đã cắt lượt trước khi luồng canh kịp thấy. Cùng một sự việc,
        # cùng một kết cục.
        raise JobCancelled() from None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    if ctx is not None:
        ctx.progress(100, "xong")

    # `usage` đi kèm kết quả là **có chủ ý** — xem `KetQua.as_result`. Không báo
    # thì `public_api/costing.py` không quy được token về job này.
    return kq.as_result()
