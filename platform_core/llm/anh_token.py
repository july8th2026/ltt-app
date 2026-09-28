r"""anh_token.py — chi phí token của MỘT ảnh, đúng bằng thứ llama.cpp thực sự đếm.

⛔ HAI BẢN GIỐNG HỆT TỪNG BYTE: ``platform_core/llm/anh_token.py`` (máy A) và
   ``llm_gateway/anh_token.py`` (máy B) — cùng khuôn với ``uoc_token.py`` và cùng lý
   do: máy B không có cây ``platform_core`` (Q102), máy A không import gói của máy B.
   ``test_4203`` so nguồn. Hai bản lệch là **A giữ chỗ khác số B đếm**, gãy im lặng.

NGUỒN CỦA CÔNG THỨC
===================

Đọc thẳng siêu dữ liệu GGUF của cả hai tệp mmproj trên máy B (2026-09-28, CHỈ ĐỌC)::

    clip.projector_type            = 'qwen3vl_merger'   (cả hai mmproj)
    clip.vision.patch_size         = 16
    clip.vision.spatial_merge_size = 2
    => một token = (16 * 2) x (16 * 2) = 32 x 32 điểm ảnh

Trần ``[8, 4096]`` là của llama.cpp cho họ Qwen2VL/Qwen25VL/Qwen3VL:
``tools/mtmd/clip.cpp:1660`` ``set_limit_image_tokens(8, 4096)`` tại đúng commit
``91f6a6cf3`` (build b10883) đang chạy. Khoá GGUF ``clip.vision.image_min_pixels`` /
``image_max_pixels`` VẮNG MẶT trong cả hai tệp, và llama.cpp cũng KHÔNG đọc chúng cho
họ Qwen — nên hai cờ CLI ``--image-min-tokens`` / ``--image-max-tokens`` là cần gạt
**duy nhất**. Vì thế ``toi_thieu``/``toi_da`` ở đây là **tham số bắt buộc, keyword,
KHÔNG có mặc định**: chúng là số của *engine*, người gọi phải đọc từ cấu hình engine
rồi truyền vào. Gán mặc định ở đây là tạo bản sao thứ hai của một con số mà không có
gì buộc nó khớp với engine đang chạy.

``token_anh`` chép ``calc_size_preserved_ratio()`` của llama.cpp
(``tools/mtmd/mtmd-image.cpp``) — chính là ``smart_resize`` của transformers đổi sang
bước 32. Đối chiếu 14/14 ô trên CẢ HAI model production (``tools/do_token_anh.py``,
bảng trong ``test_4203``): lệch 0 ở mọi ô.

``TOKEN_DAU_VISION`` KHÔNG phải token ảnh: đó là cặp ``<|vision_start|>`` /
``<|vision_end|>`` do khuôn mẫu chèn, đếm như token **CHỮ**. Để riêng vì phần chữ đã
có đường ước của nó (``uoc_token.py``) — cộng nhầm vào đây là đếm hai lần.

🔴 HAI CÁI BẪY — cả hai đã bắt được bằng số đo, đừng "dọn" chúng đi
===================================================================

1. ``_tron_nua_len`` phải là ``math.floor(x + 0.5)``. ⛔ KHÔNG dùng ``round()`` của
   Python: nó làm tròn **về số chẵn**, nên ``1280x720`` (720/32 = 22,5) ra 22 thay vì
   23 — lệch **40 token về chiều THIẾU** (đặt chỗ ít hơn thực, tức chiều nguy hiểm).
   Và 1280x720 là một trong những cỡ ảnh chụp màn hình phổ biến nhất, nên lỗi này nằm
   đúng trên đường đi nhiều nhất. C++ ``std::round`` là nửa lên, ra xa số không.

2. Nhánh vượt trần KHÔNG phải phép kẹp. llama.cpp **thu nhỏ giữ tỉ lệ** rồi ``floor``
   từng chiều, nên ``3840x2160`` cho **4080** chứ không phải 4096. Kẹp thẳng sẽ đặt
   chỗ CAO hơn thực 16 token ở mọi ảnh 4K — sai hướng an toàn nhưng vẫn là sai, và nó
   che mất việc ảnh ĐÃ bị thu nhỏ.

``kich_thuoc`` — CHỈ ĐỌC HEADER
===============================

Hàm này chạy trên **đường nóng** của cổng máy B ⇒ ⛔ chỉ thư viện chuẩn, KHÔNG
``Pillow``, KHÔNG giải mã ảnh, chỉ đọc vài chục byte header. Phủ ``png|jpeg|webp|gif``
(những gì client DSH gửi được) cộng ``bmp`` (stb_image trong llama.cpp đọc được).
Rác ⇒ trả ``None``, ⛔ không ném: người gọi quyết định làm gì với ảnh không nhận ra.
"""
from __future__ import annotations

import math

#: `<|vision_start|>` + `<|vision_end|>` của khuôn mẫu — token CHỮ, KHÔNG phải token ảnh.
TOKEN_DAU_VISION = 2

#: `clip.vision.patch_size` * `clip.vision.spatial_merge_size` = 16 * 2 — xem docstring.
DIEM_ANH_MOI_TOKEN_CANH = 32


def _tron_nua_len(x: float) -> int:
    """``std::round`` của C++: nửa LÊN, ra xa số không — bẫy (1) trong docstring.

    ⛔ Không thay bằng ``round()``: ``round(22.5) == 22`` (về số chẵn), còn hàm này
       cho 23 — đúng bằng thứ llama.cpp đếm ở 1280x720.
    """
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def token_anh(rong: int, cao: int, *, toi_thieu: int, toi_da: int) -> int:
    """Số token ẢNH của một ảnh ``rong`` x ``cao`` — CHƯA cộng ``TOKEN_DAU_VISION``.

    ``toi_thieu``/``toi_da`` là ``--image-min-tokens`` / ``--image-max-tokens`` của
    engine đang chạy; bắt buộc keyword, không mặc định — xem docstring module.
    """
    c = DIEM_ANH_MOI_TOKEN_CANH
    o = max(1, _tron_nua_len(rong / c)) * max(1, _tron_nua_len(cao / c))
    if o > toi_da:
        # Bẫy (2): THU NHỎ giữ tỉ lệ rồi `floor` từng chiều, ⛔ KHÔNG kẹp về `toi_da`.
        beta = math.sqrt(rong * cao / (toi_da * c * c))
        o = max(1, math.floor(rong / beta / c)) * max(1, math.floor(cao / beta / c))
    return max(toi_thieu, o)


# ── Đọc kích thước từ HEADER — chỉ thư viện chuẩn ───────────────────────────


def _png(d: bytes) -> tuple[int, int] | None:
    """Chunk IHDR bắt buộc đứng ngay sau chữ ký: dài 4 + kiểu 4 + rộng 4 + cao 4."""
    if len(d) < 24 or d[12:16] != b"IHDR":
        return None
    rong = int.from_bytes(d[16:20], "big")
    cao = int.from_bytes(d[20:24], "big")
    return (rong, cao) if rong and cao else None


def _gif(d: bytes) -> tuple[int, int] | None:
    """Logical Screen Descriptor: hai uint16 little-endian ngay sau 6 byte chữ ký."""
    if len(d) < 10:
        return None
    rong = int.from_bytes(d[6:8], "little")
    cao = int.from_bytes(d[8:10], "little")
    return (rong, cao) if rong and cao else None


def _bmp(d: bytes) -> tuple[int, int] | None:
    """Kích thước nằm trong DIB header, mà DIB header có hai họ khác nhau."""
    if len(d) < 22:
        return None
    co_dau = int.from_bytes(d[14:18], "little")
    if co_dau == 12:                                   # BITMAPCOREHEADER: uint16
        rong = int.from_bytes(d[18:20], "little")
        cao = int.from_bytes(d[20:22], "little")
    elif co_dau >= 16 and len(d) >= 26:                # BITMAPINFOHEADER trở đi: int32
        rong = int.from_bytes(d[18:22], "little", signed=True)
        # Cao ÂM = ảnh lưu từ trên xuống. Vẫn là cùng một số điểm ảnh.
        cao = abs(int.from_bytes(d[22:26], "little", signed=True))
        rong = abs(rong)
    else:
        return None
    return (rong, cao) if rong and cao else None


def _webp(d: bytes) -> tuple[int, int] | None:
    """Ba biến thể chunk, mỗi biến thể một cách gói kích thước."""
    if len(d) < 16 or d[8:12] != b"WEBP":
        return None
    hieu = d[12:16]
    if hieu == b"VP8X" and len(d) >= 30:               # mở rộng: (rộng-1, cao-1) 24 bit
        return (int.from_bytes(d[24:27], "little") + 1,
                int.from_bytes(d[27:30], "little") + 1)
    if hieu == b"VP8L" and len(d) >= 25 and d[20] == 0x2F:
        bit = int.from_bytes(d[21:25], "little")       # 14 bit rộng, 14 bit cao, đều -1
        return ((bit & 0x3FFF) + 1, ((bit >> 14) & 0x3FFF) + 1)
    if hieu == b"VP8 " and len(d) >= 30 and d[23:26] == b"\x9d\x01\x2a":
        rong = int.from_bytes(d[26:28], "little") & 0x3FFF
        cao = int.from_bytes(d[28:30], "little") & 0x3FFF
        return (rong, cao) if rong and cao else None
    return None


#: Trong dải 0xC0..0xCF, ba mã này KHÔNG phải SOF: DHT · JPG (dự trữ) · DAC.
_KHONG_PHAI_SOF = frozenset((0xC4, 0xC8, 0xCC))


def _jpeg(d: bytes) -> tuple[int, int] | None:
    """Duyệt marker tới ``SOF0..SOF15``.

    ⛔ Không đọc 20 byte đầu rồi đoán: giữa SOI và SOF có thể là APP0/JFIF, một khối
       EXIF APP1 vài chục KB, ICC profile, comment... Số byte tới SOF không cố định.
       JPEG progressive dùng ``SOF2``, JPEG lossless ``SOF3`` — đều phải nhận.
    """
    i, n = 2, len(d)
    while i + 3 < n:
        if d[i] != 0xFF:                               # byte đệm/rác giữa các đoạn
            i += 1
            continue
        ma = d[i + 1]
        if ma == 0xFF:                                 # dãy 0xFF lấp chỗ
            i += 1
            continue
        if ma == 0x01 or ma == 0xD8 or 0xD0 <= ma <= 0xD7:
            i += 2                                     # TEM/SOI/RSTn: không có phần dài
            continue
        if ma == 0xD9 or ma == 0xDA:
            return None                                # EOI / vào dữ liệu nén: SOF luôn ĐI TRƯỚC
        dai = int.from_bytes(d[i + 2:i + 4], "big")
        if dai < 2:
            return None
        if 0xC0 <= ma <= 0xCF and ma not in _KHONG_PHAI_SOF:
            if i + 9 > n:
                return None
            cao = int.from_bytes(d[i + 5:i + 7], "big")   # CAO đứng TRƯỚC rộng
            rong = int.from_bytes(d[i + 7:i + 9], "big")
            return (rong, cao) if rong and cao else None
        i += 2 + dai
    return None


def kich_thuoc(du_lieu: bytes) -> tuple[int, int] | None:
    """``(rong, cao)`` đọc từ HEADER ảnh. ``None`` nếu không nhận ra định dạng.

    ⛔ Không ném với dữ liệu rác/cụt — người gọi quyết định xử lý.
    """
    d = bytes(du_lieu)
    if d.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png(d)
    if d.startswith(b"\xff\xd8"):
        return _jpeg(d)
    if d.startswith(b"RIFF"):
        return _webp(d)
    if d.startswith(b"GIF87a") or d.startswith(b"GIF89a"):
        return _gif(d)
    if d.startswith(b"BM"):
        return _bmp(d)
    return None
