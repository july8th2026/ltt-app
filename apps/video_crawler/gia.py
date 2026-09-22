"""video_crawler — bảng giá MỘT NGUỒN theo thời lượng (`DANH_GIA_MVP.md` §3, chốt chủ dự án 22/09).

Xem trước (khám phá): 0 credit. Tải: giá theo bậc thời lượng thật (giây) của từng video, không theo
số lượng mục nộp. `manifest._gia` giữ chỗ khi NỘP job bằng `GIA_GIU_CHO` (bậc cao nhất) mỗi mục xin tải;
`jobs.py` quyết toán `credit_cost` = tổng `gia_muc(thoi_luong_s thật)` của các mục ĐÃ TẢI — nền tảng tự
hoàn phần chênh (spec `docs/03_THEM_APP_MOI.md` §2). Không có sàn ẩn: không làm tròn LÊN khi quyết toán
(bài học memory "tiền và giá" — không thu thêm bằng làm tròn).

Đây là NGUỒN DUY NHẤT của giá app này — UI (`routes.py`) chỉ đọc `bang()`, không tính lại.
"""
from __future__ import annotations

#: Bậc giá theo thời lượng (giây). Mỗi phần tử: (giới hạn TRÊN của bậc, bao gồm; giá credit/video).
#: Bậc cuối (60 phút – 3 giờ) khớp trần `adapters/_ytdlp.py:THOI_LUONG_TOI_DA_MAC_DINH` (3*3600) — video
#: dài hơn đã bị từ chối ("qua_dai") trước khi tới đây.
BAC_GIA: tuple[tuple[int, int], ...] = (
    (600, 3),        # <= 10 phút
    (1800, 6),       # 10–30 phút
    (3600, 10),      # 30–60 phút
    (10_800, 15),    # 60 phút – 3 giờ
)

#: Giữ chỗ khi NỘP job (mỗi mục xin tải) — luôn bậc cao nhất; quyết toán theo `gia_muc` thật khi tải xong,
#: phần chênh được nền tảng hoàn (không phải giá thật của mọi video).
GIA_GIU_CHO = BAC_GIA[-1][1]


def gia_muc(thoi_luong_s: int | float | None) -> int:
    """Giá 1 video (credit) theo thời lượng thật (giây).

    Không rõ thời lượng (adapter không báo, hoặc mục đến trực tiếp từ danh sách id/url của khách chứ
    không qua khám phá) ⇒ bậc RẺ NHẤT (≤ 10 phút) — quyết định chủ dự án 22/09, không phải sàn giá cao.
    """
    if thoi_luong_s is None:
        return BAC_GIA[0][1]
    try:
        s = max(0, int(thoi_luong_s))
    except (TypeError, ValueError):
        return BAC_GIA[0][1]
    for gioi_han, gia in BAC_GIA:
        if s <= gioi_han:
            return gia
    return BAC_GIA[-1][1]   # phòng hờ: > 3 giờ đã bị "qua_dai" chặn ở tầng adapter, không để giá vô hạn


def bang() -> list[dict]:
    """Bảng bậc giá cho giao diện hiển thị (đọc, không đổi trạng thái). Bậc đầu bắt đầu từ giây 0."""
    ra: list[dict] = []
    tu = 0
    for gioi_han, gia in BAC_GIA:
        ra.append({"tu_s": tu, "den_s": gioi_han, "gia": gia})
        tu = gioi_han + 1
    return ra
