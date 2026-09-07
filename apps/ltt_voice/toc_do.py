r"""
toc_do.py — đổi tốc độ đọc trên tệp ĐÃ SINH XONG (time-stretch giữ cao độ).

## Vì sao đây KHÔNG phải một tham số của engine

Chủ sản phẩm nói thẳng điều quyết định thiết kế này: *"tốc độ speed này không
phải tốc độ đọc setup cho giọng, nếu tăng sẽ vô tình làm ảnh hưởng giọng đọc"*.

Đúng vậy, và hệ thống cũ đã học cùng bài học ấy trước ta. `D:\Voiceclone_TTS`
có **hai** khái niệm tách bạch trong `voice_profile.py`:

    speed        tham so cua ENGINE — doi cach model doc
    post_speed   time-stretch tren song am DA SINH — khong cham model

Và chú thích của chính nó cảnh báo về cái thứ nhất: *"Thay doi speed qua xa so
voi toc do goc co the gay lap, vap."*

## Quan hệ với Q119, nói cho rõ để phiên sau không phải suy lại

Chú thích trong `ltt_voice_studio.html` từng viết *"DELIVERY STYLE (tốc độ +
phong cách) — ⛔ Q119 CẤM phơi ra"*. Đọc lại Q119 thì đó là một **trích dẫn
sai**: Q119 ① nêu đích danh năm tham số — `temperature`, `top_k`, `top_p`,
`repetition_penalty`, `repetition_window` — và **không có "tốc độ"**.

Cả hai lý do của Q119 cũng chỉ nói về đường lấy mẫu:
  · cache CUDA graph khoá theo `(B, temperature, top_k, top_p)` — tốc độ hậu kỳ
    không phải một phần của khoá ấy, và không chạm GPU;
  · `temperature` cao làm lệch tông giữa các đoạn (upstream #173) — cũng là
    chuyện của lúc sinh, không phải của lúc kéo giãn.

⇒ Tệp này **không vi phạm và cũng không sửa đổi Q119.** Nó chỉ tách "tốc độ hậu
  kỳ" ra khỏi một danh sách mà nó vốn không thuộc về. Ai muốn phơi
  `temperature` ra giao diện thì vẫn phải qua Q119 như cũ.

## 🔴 HAI RÀNG BUỘC VỀ THỨ TỰ. Sai thứ tự là hỏng, và hỏng im lặng.

**① Kéo giãn phải nằm SAU khi đo thời lượng để tính tiền.**

   `jobs.py` đo `giay` bằng ffprobe rồi dựng `KetQua(giay=...)`, và `giay` chính
   là cơ sở tính credit. Kéo giãn 1,5× làm tệp ngắn đi một phần ba — nên nếu
   đặt trước bước đo, khách chọn tốc độ nhanh sẽ **trả ít hơn cho cùng một lượng
   việc GPU**. Đó là một lỗ có thể khai thác, không phải một sự ưu ái.

**② Kéo giãn phải nằm SAU cổng chất lượng.**

   Hệ cũ ghi lại bài học này ở `diagnosis/config_recommender.py`: *"post_speed
   time-stretches the waveform AFTER synthesis, directly biasing ALL F0
   measurements"* — nó đóng băng `post_speed` một cách VÔ ĐIỀU KIỆN trước khi
   đọc bất kỳ số đo F0 nào. Bộ đo của ta (`do_on_dinh`, `lech_tham_chieu`) cũng
   đo F0 và độ tản F0, nên một bản đã kéo giãn sẽ cho số sai ở chính những chỉ
   số K3/K4 dùng để phán quyết.

   Chốt K1 chạy trong sidecar, trước khi WAV rời khỏi đó. Tệp này chạy ở tầng
   app, sau đó. Đúng thứ tự — nhưng đừng ai chuyển nó vào sidecar.

## `atempo` chứ KHÔNG phải `rubberband` — và đây là chỗ ta đi ngược hệ cũ

Hệ cũ đổi từ `atempo` sang `rubberband` ở v6.0, lý do ghi trong chính mã của nó:
*"No volume drop (unlike atempo)"*. Ta đo lại trên engine của ta, ba giọng mẫu,
cùng một câu, đo cả hai trục:

    bo loc        toc do   lech F0    muc am luong
    atempo         1.25x     +1.1%       +0.02 dB
    rubberband     1.25x     +3.0%       -1.85 dB
    atempo         1.50x     +1.9%       +0.05 dB
    rubberband     1.50x     +3.0%       -2.17 dB

⇒ `atempo` thắng **cả hai trục**, và chính `rubberband` mới là cái tụt âm lượng
  — đúng ngược với lý do hệ cũ nêu khi đổi sang nó.

⭐ Không kết luận rằng hệ cũ sai. Nó chạy F5-TTS/XTTS ở sample rate khác, và một
   bộ lọc time-stretch cư xử khác nhau theo phổ đầu vào. Kết luận đúng là hẹp
   hơn: **trên engine của ta, ở khoảng tốc độ của ta, `atempo` tốt hơn** — và
   đó là lý do phải đo lại chứ không chép quyết định.

⚠️ MỘT PHÉP ĐO CỦA CHÍNH TÔI ĐÃ SAI, ghi lại vì nó dễ lặp lại. Lượt đầu tôi đo
   n=1 trên một clip giọng **nữ** và ra `rubberband +21,2%` — đủ lớn để tôi
   suýt hạ trần tốc độ. Nhưng bộ đo báo F0 gốc của clip ấy là **105,6 Hz**, thấp
   bất thường với giọng nữ ⇒ bộ dò cao độ đang **nhầm quãng tám** trên chính
   clip đó, và mọi con số dẫn xuất từ nó đều vô nghĩa. Bài học: khi một phép đo
   cho kết quả gây sốc, hãy kiểm **giá trị nền** trước khi tin phần chênh lệch.

⚠️ `rubberband` giữ lại làm đường lui vì nó cũng là **tuỳ chọn lúc build ffmpeg**
   (`--enable-librubberband`) — máy này có, máy chủ khác có thể không. Nhưng nay
   nó là đường lui của `atempo`, không phải ngược lại.

⚠️ `atempo` chỉ nhận 0,5–2,0 mỗi lần, nên hệ số ngoài khoảng đó phải NỐI CHUỖI
   nhiều bộ lọc. Khoảng của ta (0,75–1,50) nằm gọn trong một bộ lọc, nhưng hàm
   nối chuỗi vẫn giữ: ai nới `TOC_DO_MAX` lên 2,5 mà không có nó thì ffmpeg trả
   lỗi, và trả ở một chỗ không ai đang nhìn.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile

log = logging.getLogger(__name__)

#: Khoảng cho khách chọn. Hẹp hơn hẳn khoảng kỹ thuật (`rubberband` chịu được
#: nhiều hơn) vì ngoài khoảng này giọng nghe rõ là đã bị xử lý.
TOC_DO_MIN = 0.75
TOC_DO_MAX = 1.50

#: Các nấc bày ra giao diện. Rời rạc chứ không phải thanh trượt liên tục: một
#: thanh trượt mời khách dừng ở 1,07× — một con số không ai nghe ra khác biệt
#: nhưng vẫn tốn một lượt ffmpeg.
CAC_NAC = (0.75, 0.85, 1.0, 1.15, 1.25, 1.5)

#: Dưới ngưỡng này coi như không đổi và BỎ QUA hẳn — không gọi ffmpeg, không
#: chép tệp. Một lượt kéo giãn "1,00×" vẫn giải mã và mã hoá lại toàn bộ sóng âm.
NGUONG_BO_QUA = 0.01


def hop_le(toc_do) -> float:
    """Ép về khoảng cho phép. Giá trị vô nghĩa trả về 1.0 (tức không đổi)."""
    try:
        t = float(toc_do)
    except (TypeError, ValueError):
        return 1.0
    if t != t or t in (float("inf"), float("-inf")):   # NaN / vô cực
        return 1.0
    return min(TOC_DO_MAX, max(TOC_DO_MIN, t))


def can_doi(toc_do) -> bool:
    """Có thật sự cần chạy ffmpeg không?"""
    return abs(hop_le(toc_do) - 1.0) >= NGUONG_BO_QUA


def _chuoi_atempo(ty_le: float) -> str:
    """`atempo` chỉ nhận 0,5–2,0 mỗi bộ lọc — ngoài khoảng thì nối chuỗi."""
    con = ty_le
    cac = []
    while con > 2.0:
        cac.append(2.0)
        con /= 2.0
    while con < 0.5:
        cac.append(0.5)
        con /= 0.5
    cac.append(con)
    return ",".join(f"atempo={c:.6f}" for c in cac)


def _chay(vao: str, ra: str, loc: str, giay_cho: int) -> None:
    from platform_core.media import ffmpeg_bin

    lenh = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", vao, "-af", loc, "-ac", "1", ra]
    kq = subprocess.run(lenh, capture_output=True, text=True,
                        timeout=giay_cho)
    if kq.returncode != 0:
        raise RuntimeError((kq.stderr or "")[:300])


def ap_dung(wav_bytes: bytes, toc_do, *, giay_cho: int = 120) -> bytes:
    """Trả về WAV đã đổi tốc độ. Hỏng thì trả **nguyên bản**, không ném.

    ⭐ Không ném là có chủ ý: tới đây thì tiếng ĐÃ SINH XONG và khách ĐÃ BỊ TÍNH
       TIỀN. Biến một lỗi hậu kỳ thành một job hỏng là thu tiền cho một việc rồi
       vứt kết quả của nó đi. Trả bản gốc kèm một dòng log là hỏng đúng hướng.
    """
    if not wav_bytes or not can_doi(toc_do):
        return wav_bytes
    t = hop_le(toc_do)

    d_vao = d_ra = ""
    try:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        d_vao = f.name
        f.write(wav_bytes)
        f.close()
        f2 = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        d_ra = f2.name
        f2.close()

        try:
            _chay(d_vao, d_ra, _chuoi_atempo(t), giay_cho)
        except Exception as ex:                        # noqa: BLE001
            # ⚠️ NÓI RA. `atempo` là bộ lọc ffmpeg mặc định nên nó hỏng là
            #    chuyện lạ — im lặng lui về đường phụ sẽ giấu mất chuyện lạ ấy.
            log.warning("atempo hong (%s) -> lui ve rubberband. Do 01/09 cho "
                        "thay rubberband tut ~2 dB am luong, nen day la ban "
                        "kem hon chu khong phai ban tuong duong.", ex)
            _chay(d_vao, d_ra, f"rubberband=tempo={t}:pitch=1.0", giay_cho)

        with open(d_ra, "rb") as fh:
            ra = fh.read()
        if not ra:
            raise RuntimeError("ffmpeg tra tep rong")
        # ⭐ NÓI RA CẢ KHI THÀNH CÔNG. Nhánh hỏng trả về bản gốc một cách im
        #    lặng (đúng — xem docstring `ap_dung`), nhưng hệ quả là "không đổi
        #    tốc độ" và "đổi rồi mà hỏng" nhìn giống hệt nhau trong log.
        #
        #    Đã trả giá 01/09: một lượt chạy ra đúng thời lượng gốc, và không có
        #    dòng nào cho biết là vì tham số chưa tới nơi hay vì ffmpeg hỏng.
        #    Thủ phạm hoá ra ở tận phía trình duyệt — nhưng log không loại được
        #    khả năng nào cả, nên nó không giúp thu hẹp gì.
        log.info("doi toc do %.2fx: %d -> %d byte", t, len(wav_bytes), len(ra))
        return ra
    except Exception:                                  # noqa: BLE001
        log.warning("doi toc do %.2fx that bai — giu nguyen ban goc",
                    t, exc_info=True)
        return wav_bytes
    finally:
        for p in (d_vao, d_ra):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def ap_dung_tep(duong_vao: str, duong_ra: str, toc_do, *,
                giay_cho: int = 600) -> str:
    """Đổi tốc độ TỆP -> TỆP. Trả đường dẫn của bản dùng được.

    ⭐ Cùng phép hậu kỳ với `ap_dung`, khác đúng một điều: không có lúc nào cả
       bản đọc nằm trong bộ nhớ. Với một cuốn sách thì `ap_dung` phải giữ hai
       bản `bytes` cùng lúc (vào và ra) chỉ để gọi một lệnh ffmpeg vốn đọc ghi
       bằng tệp — tức ta chép dữ liệu vào RAM để đưa cho một chương trình sắp
       ghi nó xuống đĩa.

    ⛔ Hỏng thì trả **đường dẫn bản gốc**, không ném — cùng lý do `ap_dung` ghi:
       tới đây tiếng đã sinh xong và khách đã bị tính tiền. Biến một lỗi hậu kỳ
       thành một job hỏng là thu tiền cho một việc rồi vứt kết quả của nó đi.

    ⚠️ `giay_cho` rộng hơn `ap_dung` (600 thay vì 120): tệp ở đây có thể dài
       hàng giờ, và một trần đặt cho bài 30 giây sẽ giết đúng những bài mà hàm
       này sinh ra để phục vụ.
    """
    if not can_doi(toc_do):
        return duong_vao
    t = hop_le(toc_do)
    try:
        try:
            _chay(duong_vao, duong_ra, _chuoi_atempo(t), giay_cho)
        except Exception as ex:                        # noqa: BLE001
            log.warning("atempo hong (%s) -> lui ve rubberband", ex)
            _chay(duong_vao, duong_ra, f"rubberband=tempo={t}:pitch=1.0",
                  giay_cho)
        if not os.path.isfile(duong_ra) or os.path.getsize(duong_ra) <= 0:
            raise RuntimeError("ffmpeg tra tep rong")
        log.info("doi toc do %.2fx (tep): %d -> %d byte", t,
                 os.path.getsize(duong_vao), os.path.getsize(duong_ra))
        return duong_ra
    except Exception:                                  # noqa: BLE001
        log.warning("doi toc do %.2fx that bai — giu nguyen ban goc", t,
                    exc_info=True)
        return duong_vao
