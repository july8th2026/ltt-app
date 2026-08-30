"""
audio_input.py — kiểm tệp tiếng người dùng tải lên.

Đối xứng với `platform_core/image_input.py`, và ở đây có chủ ý: module đó nằm
trong `platform_core` vì **ba app** cần nó. LTT VOICE là app **duy nhất** nhận
audio tham chiếu, nên nó sống trong app. Ngày có app thứ hai cần đúng phép kiểm
này thì mới chuyển lên — chuyển sớm là dựng hạ tầng cho một người dùng.

⛔ KHÔNG TIN `Content-Type` CỦA TRÌNH DUYỆT. Trình duyệt gửi gì cũng được; tin nó
   là để lọt một tệp không phải audio vào đường xử lý audio. Kiểm bằng **byte
   thật** rồi mới giải mã.

⭐ VÌ SAO KIỂM CHẤT LƯỢNG CHỨ KHÔNG CHỈ KIỂM ĐỊNH DẠNG.

   Ghi danh giọng là chỗ **một tệp hợp lệ vẫn cho ra một giọng tồi**: quá ngắn thì
   không đủ đặc trưng, có nhiều người nói thì model trộn cả hai, clipping thì
   model học luôn cái méo. Người dùng sẽ không đổ lỗi cho clip của họ — họ sẽ nói
   sản phẩm dở. Nên chặn ở cửa, kèm câu giải thích sửa được.

   Upstream nói clip **3-8 giây** là đủ và tự cắt về <= 8 giây. Ta nhận rộng hơn
   một chút (tới 30 giây) để người dùng không phải tự cắt, nhưng vẫn chặn hai đầu.
"""
from __future__ import annotations

import io
import struct
import wave

from platform_core.i18n import _ as _t

#: Trần kích thước. Public API đã đặt 64 MB cho `audio` (`public_api/media.py`);
#: giữ thấp hơn vì clip tham chiếu chỉ vài chục giây.
MAX_BYTES = 24 * 1024 * 1024

#: Upstream cắt về <= 8 giây khi ghi danh. Nhận 3-30 để người dùng khỏi tự cắt.
GIAY_TOI_THIEU = 3.0
GIAY_TOI_DA = 30.0

#: MIME chấp nhận. Khớp `MEDIA_RULES["audio"]` của Public API để hai cửa không
#: nhận hai tập tệp khác nhau.
MIME_CHAP_NHAN = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4",
                  "audio/x-m4a"}

#: Ngưỡng cắt đỉnh. |mẫu| >= ngưỡng này bị coi là chạm trần.
_NGUONG_CLIP = 0.995
#: Tỉ lệ mẫu chạm trần tối đa còn chấp nhận được.
_TY_LE_CLIP_TOI_DA = 0.01
#: Dưới mức này coi như im lặng.
_NGUONG_IM = 0.005
#: Tỉ lệ im lặng tối đa.
_TY_LE_IM_TOI_DA = 0.60


class LoiAudio(ValueError):
    """Thông điệp đưa thẳng ra giao diện — phải nói được cách sửa."""


def doan_mime(data: bytes) -> str:
    """MIME theo BYTE THẬT. Rỗng = không nhận ra."""
    if len(data) < 12:
        return ""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    if data[4:8] == b"ftyp":
        return "audio/mp4"
    return ""


def _doc_wav(data: bytes) -> tuple:
    """WAV PCM -> (mẫu float32 chuẩn hoá, sample_rate). Chỉ dùng thư viện chuẩn."""
    with wave.open(io.BytesIO(data), "rb") as w:
        n_kenh = w.getnchannels()
        rong = w.getsampwidth()
        sr = w.getframerate()
        khung = w.readframes(w.getnframes())
    if rong == 2:
        mau = struct.unpack("<%dh" % (len(khung) // 2), khung[:len(khung) // 2 * 2])
        chia = 32768.0
    elif rong == 1:
        mau = [b - 128 for b in khung]
        chia = 128.0
    else:
        # 24/32-bit: không giải mã bằng thư viện chuẩn. Không phải lỗi của người
        # dùng, nên đừng từ chối — chỉ bỏ phần đo chất lượng.
        return None, sr
    if n_kenh > 1:
        mau = mau[::n_kenh]
    return [m / chia for m in mau], sr


def kiem(data: bytes, content_type: str = "") -> dict:
    """Kiểm một tệp tiếng tải lên. Trả bản mô tả; ném `LoiAudio` nếu không nhận.

    Trả về `{"mime", "giay", "sample_rate", "canh_bao"}`. `giay` là `None` khi
    không đo được (định dạng nén) — lúc đó **thời lượng phải đo lại bằng ffprobe
    ở tầng trên**, đừng đoán.
    """
    if not data:
        raise LoiAudio(_t("Tệp âm thanh rỗng."))
    if len(data) > MAX_BYTES:
        raise LoiAudio(_t(
            "Tệp vượt giới hạn {mb} MB. Clip mẫu chỉ cần vài giây, không cần cả bài."
        ).format(mb=MAX_BYTES // (1024 * 1024)))

    that = doan_mime(data)
    if not that:
        raise LoiAudio(_t("Không nhận ra định dạng âm thanh. Hãy gửi WAV, MP3 hoặc M4A."))

    khai = (content_type or "").split(";")[0].strip().lower()
    if khai and khai not in MIME_CHAP_NHAN:
        raise LoiAudio(_t("Chỉ nhận WAV, MP3 hoặc M4A."))

    canh_bao = []
    # ⛔ Không coi lệch MIME là lỗi để TỪ CHỐI: trình duyệt gửi `audio/mp3` hay
    #    rỗng là chuyện thường. Nhưng phải GHI LẠI, vì lệch cũng là dấu hiệu của
    #    một tệp đổi đuôi.
    if khai and khai != that and not (khai, that) in {
            ("audio/x-wav", "audio/wav"), ("audio/wav", "audio/x-wav"),
            ("audio/x-m4a", "audio/mp4")}:
        canh_bao.append(_t("MIME khai '{khai}' khác nội dung thật '{that}'")
                        .format(khai=khai, that=that))

    giay = None
    sr = None
    if that in {"audio/wav", "audio/x-wav"}:
        try:
            mau, sr = _doc_wav(data)
        except (wave.Error, struct.error, EOFError) as e:
            raise LoiAudio(_t("Tệp WAV hỏng hoặc không phải PCM.")) from e
        if mau is not None and sr:
            giay = len(mau) / float(sr)
            canh_bao += _do_chat_luong(mau)

    if giay is not None:
        if giay < GIAY_TOI_THIEU:
            raise LoiAudio(_t(
                "Clip chỉ {co:.1f} giây. Cần ít nhất {can:.0f} giây giọng nói liên "
                "tục để nhân bản được."
            ).format(co=giay, can=GIAY_TOI_THIEU))
        if giay > GIAY_TOI_DA:
            raise LoiAudio(_t(
                "Clip dài {co:.0f} giây, vượt {tran:.0f} giây. Hãy cắt lấy một đoạn "
                "nói rõ, không nhạc nền."
            ).format(co=giay, tran=GIAY_TOI_DA))

    return {"mime": that, "giay": giay, "sample_rate": sr,
            "canh_bao": tuple(canh_bao)}


def _do_chat_luong(mau: list) -> list:
    """Ba phép đo rẻ bắt được ba lỗi hay gặp nhất của clip tự thu."""
    if not mau:
        return [_t("Không đọc được mẫu âm thanh.")]
    n = len(mau)
    clip = sum(1 for m in mau if abs(m) >= _NGUONG_CLIP)
    im = sum(1 for m in mau if abs(m) < _NGUONG_IM)
    dinh = max(abs(m) for m in mau)

    ra = []
    if clip / n > _TY_LE_CLIP_TOI_DA:
        ra.append(_t("Âm thanh bị vỡ tiếng (thu quá to). Giọng nhân bản sẽ bị méo "
                     "theo — nên thu lại nhỏ hơn."))
    if im / n > _TY_LE_IM_TOI_DA:
        ra.append(_t("Hơn nửa clip là khoảng lặng. Hãy cắt bỏ phần im ở đầu và cuối."))
    if dinh < 0.05:
        ra.append(_t("Âm lượng rất nhỏ. Hãy thu lại gần micro hơn."))
    return ra
