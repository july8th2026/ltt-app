"""Ngưỡng vận hành: đẩy `metrics` tới người trực, thay vì chờ người trực đọc.

`metrics` đã đếm sẵn đúng những thứ đáng báo, và `admin_console` đã hiện chúng
trên trang Tổng quan. Cái còn thiếu là **đường ra**: Q21 chốt "phải biết lỗi
trước khi khách gọi điện", nhưng một con số nằm trên một trang chỉ được biết khi
có người mở trang đó. Không ai mở trang lúc 2 giờ sáng.

Khác `alerting.py` ở người nhận, nên khác cả nội dung: ở đó là khách hàng và mỗi
điều kiện phải là việc **khách** làm được (nạp thêm credit, xoay khoá). Ở đây là
người vận hành, và điều kiện là việc **nền tảng** phải sửa.

## Vì sao kích theo SƯỜN, và cái giá của lựa chọn đó

Một vòng quét định kỳ mà cứ thấy điều kiện đúng là gửi thư sẽ gửi mỗi lượt quét
trong suốt sự cố — và một hộp thư 200 thư giống nhau bị lọc bỏ nhanh hơn hẳn một
hộp thư trống. `alerting.py` giải bài này bằng khoá chống trùng trong CSDL, nhưng
khoá đó bám `user_id`; cảnh báo vận hành không có chủ sở hữu nên không dùng lại
được, và dựng một bảng riêng nghĩa là thêm một migration nữa lên một CSDL vừa
deploy.

Nên chỗ này **suy ra trạng thái từ chính dữ liệu**: chỉ báo khi điều kiện đúng ở
cửa sổ hiện tại và **không** đúng ở khoảng lặng trước đó. Không cần bảng, không
cần migration, và tự đúng khi worker khởi động lại.

Cái giá phải nói rõ: **một sự cố kéo dài liên tục chỉ gửi MỘT thư.** Nếu suốt
`IM_LANG_GIO` giờ trước điều kiện vẫn đúng thì không có sườn nào để kích, nên
không có thư thứ hai. Đây là kênh **phát hiện**, không phải kênh nhắc việc; đừng
dùng nó thay cho việc theo dõi một sự cố đang mở.

Vắng `LTT_OPS_ALERT_EMAIL` thì tắt mềm, giống mọi tích hợp tuỳ chọn khác. Tắt
mềm chứ không phải lỗi: một cài đặt dev không có người trực.
"""
from __future__ import annotations

import logging
import os
from html import escape

from platform_core.public_api import metrics

log = logging.getLogger(__name__)

#: Địa chỉ người trực. Vắng = tắt.
EMAIL_ENV = "LTT_OPS_ALERT_EMAIL"

#: Cửa sổ coi là "bây giờ". `metrics.aggregate` chặn dưới ở 1 giờ, và một giờ
#: cũng là mức thô hợp lý: ngắn hơn thì một cơn tăng ngắn sẽ đánh thức người
#: trực vì chuyện tự khỏi.
CUA_SO_GIO = 1

#: Khoảng lặng để tìm sườn. Chọn 6 giờ chứ không phải 24: một sự cố sáng nay
#: không nên làm im tiếng một sự cố khác chiều nay.
IM_LANG_GIO = 6

#: Ngưỡng cho mỗi bộ đếm, trong một cửa sổ.
#:
#: Các con số dưới đây là **điểm xuất phát có lý do**, không phải hằng số đã hiệu
#: chuẩn — chưa có lưu lượng thật để hiệu chuẩn. Chúng sẽ phải sửa sau tuần đầu
#: có khách, và sửa chúng là việc bình thường chứ không phải dấu hiệu sai thiết kế.
NGUONG = {
    # Lỗi 5xx là lỗi của nền tảng, không phải của người gọi. Năm cái trong một
    # giờ đã là một hình mẫu, không phải một lần trục trặc.
    metrics.RESPONSES_5XX: 5,
    # Xác thực thất bại nhiều: hoặc một tích hợp vừa hỏng, hoặc có người đang dò
    # khoá. Cả hai đều đáng biết, và ngưỡng phải cao hơn "một khách gõ sai".
    metrics.AUTH_FAILURE: 50,
    # Chạm hạn mức nhịp là hàng rào làm việc đúng chức năng. Nó chỉ đáng báo khi
    # nhiều đến mức nghĩa là hạn mức đặt sai, hoặc có ai đang đập cửa.
    metrics.RATE_LIMITED: 200,
    # Công tắc ngắt vừa từ chối một việc. Dù chỉ MỘT lần cũng đáng biết: nó chỉ
    # bật khi có người bật, nên nó đang chặn đúng thứ ai đó muốn chặn — hoặc đã
    # bị bỏ quên ở trạng thái bật.
    metrics.KILL_SWITCH_REFUSED: 1,
    # Từ chối vì thiếu năng lực phía sau (pool, GPU) là mất doanh thu, không phải
    # bảo vệ. Khác hẳn rate limit, nên khác ngưỡng.
    metrics.CAPACITY_REFUSED: 5,
    # Relay Nexus im lặng: máy khách KHÔNG kết nối tới nhau được, dù nền tảng
    # vẫn xanh. Đây là kiểu sự cố dễ bị chẩn đoán nhầm thành "lỗi đăng nhập" nên
    # phải báo sớm. Ngưỡng 2 (không phải 1) để một lần chớp mạng không dựng
    # người trực dậy; vòng bảo trì thăm định kỳ nên 2 lần liên tiếp là thật.
    "nexus:relay_im_lang": 2,
    # Cổng VLM (máy B) im lặng: model ngôn ngữ nhà **không phục vụ được ai**, dù
    # nền tảng vẫn xanh. Cùng loại sự cố với relay Nexus — nó nằm trên một máy
    # khác, một tiến trình khác, và nền tảng không có cách nào tự biết.
    #
    # Ngưỡng 2 vì cùng lý do: một lần chớp mạng không nên dựng người trực dậy,
    # nhưng hai vòng bảo trì liên tiếp im lặng là thật.
    #
    # ⚠️ Đây KHÁC "máy B bận". Bận là 429 và là trạng thái bình thường của một máy
    #    chia GPU với việc ảnh và video — nó **không** được đếm vào đây. Chỉ đếm
    #    khi cổng **không trả lời**.
    "ltt_llm:cong_im_lang": 2,
    # 🔴 MODEL MÁY B ĐANG CHẠY TRÊN CPU, KHÔNG PHẢI GPU.
    #
    # Ngưỡng 1 — bắn ngay lần đầu, khác hẳn `cong_im_lang` ở trên. Ba lý do:
    #
    #   1. **Không có dương tính giả.** Chốt chỉ bật khi CHẮC CHẮN: có model đang
    #      nạp mà VRAM lại dưới 5 GB. Không đo được thì nó im, không đoán.
    #   2. **Không tự khỏi.** Cổng im lặng có thể là một cú chớp mạng; CUDA hỏng
    #      thì hỏng cho tới khi có người khởi động lại máy.
    #   3. **Mỗi vòng chờ là tiền và là thời gian của khách.** Sự cố 23/08 chạy
    #      **hơn một giờ** trước khi tình cờ bị phát hiện, và trong suốt giờ đó
    #      mọi chốt sống/chết đều xanh.
    #
    # ⚠️ Đây KHÁC "cổng im lặng". Cổng vẫn trả `200` bình thường — thứ hỏng nằm
    #    sau nó, và triệu chứng là **chậm**, không phải **lỗi**.
    "ltt_llm:tren_cpu": 1,
    # Cổng ẢNH (máy B) im lặng. Một dịch vụ KHÁC, cổng khác, khởi động riêng —
    # cổng VLM xanh không nói gì về nó. Ngưỡng 2, cùng lý do như trên.
    #
    # ⚠️ Ở đây "bận" còn dễ nhầm hơn: cổng render trả 429 mỗi khi dự án video
    #    chiếm card, và đó là trạng thái bình thường HẰNG ĐÊM của máy B (D-005).
    "ltt_image:cong_im_lang": 2,
    # 🔴 MODEL ẢNH ĐANG CHẠY TRÊN CPU. Ngưỡng 1, cùng ba lý do như `ltt_llm`:
    # không có dương tính giả, không tự khỏi, và mỗi vòng chờ là tiền của khách.
    #
    # ⚠️ Bên ảnh triệu chứng còn khó thấy hơn bên chữ: một lượt vẽ vốn đã mất 96
    #    giây, nên "chậm gấp hàng chục lần" trông giống hệt "máy đang bận".
    "ltt_image:tren_cpu": 1,
    # Khách hết credit. Ngưỡng 3 trong một vòng bảo trì: một lần là chuyện bình
    # thường (ai cũng có lúc cạn), ba lần liên tiếp nghĩa là có người đang **cố
    # dùng mà không dùng được** và không biết vì sao.
    #
    # ⛔ Đây KHÔNG phải cảnh báo sự cố — hệ thống đang làm đúng. Nó là cảnh báo
    #    **kinh doanh**, và nó nằm cùng chỗ vì người trực cũng là người bán.
    metrics.CREDIT_EXHAUSTED: 3,
    # Webhook chết nghĩa là khách không biết job của họ đã xong.
    metrics.WEBHOOK_FAILED: 10,
}

#: Hàng đợi nhặt việc chậm hơn mức này thì có thứ đang nghẽn. Một phút: đủ lâu
#: để không báo khi worker đang bận bình thường, đủ ngắn để không phải là "job
#: bị treo" mới thấy.
QUEUE_PICKUP_NGUONG_MS = 60_000.0


def _tong_ms(bucket: dict) -> float:
    """Dựng lại tổng thời gian từ (count, avg) — `aggregate` không trả tổng."""
    return float(bucket.get("avg_ms", 0.0) or 0.0) * int(bucket.get("count", 0) or 0)


def danh_gia(gan: dict, truoc: dict) -> list:
    """Điều kiện nào vừa CHỚM đúng. Hàm thuần, không CSDL, không mạng.

    `gan` và `truoc` cùng hình dạng với `metrics.snapshot()`. Tách thành hàm
    thuần vì đây là phần dễ sai nhất và cũng là phần dễ kiểm nhất: quy tắc sườn
    kiểm được mà không cần dựng CSDL hay giả lập hộp thư.
    """
    ra = []

    gan_c = gan.get("counters", {}) or {}
    truoc_c = truoc.get("counters", {}) or {}
    for ten, nguong in sorted(NGUONG.items()):
        bay_gio = int(gan_c.get(ten, 0) or 0)
        if bay_gio < nguong:
            continue
        if int(truoc_c.get(ten, 0) or 0) >= nguong:
            continue                      # da bao o suon truoc, khong bao lai
        ra.append({"ten": ten, "gia_tri": bay_gio, "nguong": nguong,
                   "don_vi": "lan"})

    gan_l = (gan.get("latency", {}) or {}).get(metrics.LATENCY_QUEUE_PICKUP, {})
    truoc_l = (truoc.get("latency", {}) or {}).get(metrics.LATENCY_QUEUE_PICKUP, {})
    bay_gio_ms = float(gan_l.get("avg_ms", 0.0) or 0.0)
    if int(gan_l.get("count", 0) or 0) > 0 and bay_gio_ms >= QUEUE_PICKUP_NGUONG_MS:
        if float(truoc_l.get("avg_ms", 0.0) or 0.0) < QUEUE_PICKUP_NGUONG_MS:
            ra.append({"ten": metrics.LATENCY_QUEUE_PICKUP,
                       "gia_tri": round(bay_gio_ms, 1),
                       "nguong": QUEUE_PICKUP_NGUONG_MS, "don_vi": "ms trung binh"})

    return ra


def _truoc_do(rong: dict, gan: dict) -> dict:
    """Khoảng lặng = (cả `IM_LANG_GIO` giờ) trừ (cửa sổ hiện tại).

    Trừ chứ không truy vấn lần nữa: `aggregate` chỉ nhận số giờ tính từ bây giờ,
    nên không hỏi trực tiếp được một khoảng ở giữa. Trừ hai lần cộng cho ra đúng
    con số đó mà không phải mở rộng hợp đồng của `aggregate`.
    """
    rong_c = rong.get("counters", {}) or {}
    gan_c = gan.get("counters", {}) or {}
    counters = {ten: max(0, int(rong_c.get(ten, 0) or 0) - int(gan_c.get(ten, 0) or 0))
                for ten in set(rong_c) | set(gan_c)}

    latency = {}
    rong_l = rong.get("latency", {}) or {}
    gan_l = gan.get("latency", {}) or {}
    for ten in set(rong_l) | set(gan_l):
        r, g = rong_l.get(ten, {}), gan_l.get(ten, {})
        count = max(0, int(r.get("count", 0) or 0) - int(g.get("count", 0) or 0))
        total = max(0.0, _tong_ms(r) - _tong_ms(g))
        latency[ten] = {"count": count,
                        "avg_ms": round(total / count, 2) if count else 0.0,
                        "max_ms": float(r.get("max_ms", 0.0) or 0.0)}

    return {"counters": counters, "latency": latency}


def quet(db, *, now=None) -> list:
    """Đọc số đã cộng qua mọi tiến trình rồi trả về các điều kiện vừa chớm đúng."""
    gan = metrics.aggregate(db, hours=CUA_SO_GIO, now=now)
    rong = metrics.aggregate(db, hours=IM_LANG_GIO, now=now)
    return danh_gia(gan, _truoc_do(rong, gan))


def _than_thu(dieu_kien: list) -> str:
    dong = [f"  - {d['ten']}: {d['gia_tri']} {d['don_vi']} "
            f"(nguong {d['nguong']})" for d in dieu_kien]
    return (
        "Cac nguong sau vua bi vuot trong "
        f"{CUA_SO_GIO} gio qua:\n\n" + "\n".join(dong) + "\n\n"
        "Xem chi tiet o trang Tong quan cua khu quan tri.\n\n"
        "Ghi chu: day la canh bao KICH THEO SUON. Mot su co keo dai lien tuc chi "
        f"gui MOT thu; khong co thu thu hai khong co nghia la da het.\n"
    )


def gui(db, *, to: str = "", mailer=None, now=None) -> int:
    """Quét rồi gửi **một** thư cho tất cả điều kiện. Trả số điều kiện đã báo.

    Một thư chứ không phải mỗi điều kiện một thư: khi nền tảng có sự cố thật thì
    thường vài ngưỡng vỡ cùng lúc, và sáu thư cùng lúc làm người trực mất thời
    gian ghép lại thứ mà ở đây ghép sẵn được.

    Lỗi gửi thư **không** được làm sập vòng bảo trì: một hộp thư hỏng là chuyện
    của kênh cảnh báo, không phải lý do để việc dọn dữ liệu ngừng chạy.
    """
    nguoi_nhan = (to or os.environ.get(EMAIL_ENV, "")).strip()
    if not nguoi_nhan:
        return 0

    dieu_kien = quet(db, now=now)
    if not dieu_kien:
        return 0

    from platform_core.mailer import Email, get_mailer

    ten = ", ".join(d["ten"] for d in dieu_kien)
    than = _than_thu(dieu_kien)
    try:
        # `html` la truong bat buoc cua Email. Boc trong <pre>: mot canh bao van
        # hanh khong can trinh bay, no can doc duoc nhanh va giu nguyen thang cot.
        (mailer or get_mailer()).send(Email(
            to=nguoi_nhan,
            subject=f"[LTT] Nguong van hanh bi vuot: {ten}",
            html=f"<pre>{escape(than)}</pre>",
            text=than))
    except Exception:                                          # noqa: BLE001
        log.exception("khong gui duoc canh bao van hanh")
        return 0

    log.warning("canh bao van hanh da gui: %s", ten)
    return len(dieu_kien)


__all__ = ["CUA_SO_GIO", "EMAIL_ENV", "IM_LANG_GIO", "NGUONG",
           "QUEUE_PICKUP_NGUONG_MS", "danh_gia", "gui", "quet"]
