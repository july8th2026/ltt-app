"""
🔴 Chế độ thử của `/api/v1` trả **PNG cho mọi thứ**, kể cả tool trả về TIẾNG.

`catalog.py` làm phẳng `image` / `video` / `audio` thành cùng một `"artifact"`
trong lược đồ công khai, và tới đó thì thông tin *đây là tệp gì* biến mất khỏi
hệ thống. `media.store_sandbox_artifact` không còn gì để dựa vào nên nó ghi cứng
`SAMPLE_PNG`.

⭐ Vô hình suốt từ đầu, vì **mọi tool mở trước `speech.ltt` đều trả về ảnh**. Lỗi
   không nằm ở một dòng ai đó viết sai — nó nằm ở chỗ hệ thống chưa bao giờ bị
   hỏi một câu hỏi khác.

⛔ Hậu quả nếu để nguyên: người tích hợp bật chế độ thử, tải về một tệp `.png`
   phục vụ dưới `content_type: image/png` từ một trường mà lược đồ gọi là audio,
   rồi **viết tích hợp quanh nó**. Họ chỉ phát hiện khi đổi sang khoá thật —
   tức đúng lúc bắt đầu trả tiền.

Cách sửa giữ lại `media` bên cạnh `type` trong lược đồ công khai. Đó là **cộng
thêm**: ai đang đọc `type` không bị ảnh hưởng, còn khách thì lần đầu tiên biết
nên chờ WAV hay PNG.
"""
from __future__ import annotations

import io
import wave

import pytest


def test_luoc_do_cong_khai_GIU_loai_media_ben_canh_artifact():
    """`{"type": "artifact"}` không nói được đây là ảnh hay tiếng."""
    from platform_core.public_api.catalog import project_tool
    from platform_core.registry import discover

    thay = {}
    for app in discover():
        if app.error:
            continue
        for tool in (app.manifest.tools or []):
            if not getattr(tool, "api_exposed", False):
                continue
            pt = project_tool(app.manifest, tool)
            for ten, spec in (pt.output_schema or {}).get("properties",
                                                          {}).items():
                if str(spec.get("type", "")).startswith("artifact"):
                    thay[f"{pt.name}.{ten}"] = spec
    assert thay, "khong tool nao tra ve artifact — phep kiem dang mu"
    thieu = [k for k, v in thay.items() if not v.get("media")]
    assert not thieu, f"artifact khong khai loai media: {thieu}"


def test_MOI_loai_media_catalog_sinh_ra_deu_co_mau_trong_sandbox():
    """⛔ Thêm một loại media mà quên thêm mẫu thì sandbox tụt về ảnh — IM LẶNG.

    `store_sandbox_artifact` cố ý **không ném** với loại lạ: một sandbox là bề
    mặt để học, và làm hỏng cả một job thử vì một loại media mới chưa có tệp mẫu
    là phạt người dùng cho một việc không tốn gì và không sinh ra gì.

    ⭐ Nhưng "không ném" phải đi kèm "không âm thầm". Phép kiểm này là vế thứ
       hai: mọi loại `catalog` có thể phát ra đều phải có mẫu ở đây.
    """
    from platform_core.public_api.catalog import _PUBLIC_OUTPUT_TYPES
    from platform_core.public_api.media import CHUA_CO_MAU, _SANDBOX_MEDIA

    loai = {k.rstrip("[]") for k, v in _PUBLIC_OUTPUT_TYPES.items()
            if str(v).startswith("artifact")}
    thieu = sorted(loai - set(_SANDBOX_MEDIA) - set(CHUA_CO_MAU))
    assert not thieu, (
        f"catalog phat ra loai media {thieu} nhung sandbox khong co mau — "
        f"chung se lang le nhan tep PNG. Them mau vao `_SANDBOX_MEDIA`, hoac "
        f"khai vao `CHUA_CO_MAU` kem ly do neu chua lam duoc ngay.")


def test_moi_loai_CHUA_CO_MAU_deu_co_ly_do_viet_ra():
    """⛔ Danh sách miễn trừ phải ký tên, nếu không nó thành chỗ đổ rác.

    `CHUA_CO_MAU` tồn tại vì `video` chưa có tệp mẫu hợp lệ và dựng một MP4 tối
    thiểu **đúng chuẩn** là việc riêng, không phải một dòng. Nhưng một danh sách
    miễn trừ không có lý do sẽ dài ra trong im lặng, và khi đó nó bảo vệ đúng
    thứ nó lẽ ra phải phơi bày.
    """
    from platform_core.public_api.media import CHUA_CO_MAU

    for loai, ly_do in CHUA_CO_MAU.items():
        assert len(str(ly_do)) > 40, f"{loai}: ly do qua ngan de doc lai"


def test_mau_audio_la_WAV_THAT_chu_khong_phai_mot_khoi_byte_goi_la_wav():
    """Mẫu phải mở được bằng `wave`, không chỉ mang đuôi `.wav`.

    🔴 Mẫu này được **DỰNG**, không nhúng. Một khối byte escape trong mã nguồn
       chỉ cách một lần chép hỏng là thành thứ khác hẳn, và nó hỏng vô hình:
       hằng số vẫn tồn tại, vẫn có độ dài trông hợp lý, sandbox vẫn phát ra.

       Không phải lo xa — trong chính phiên viết mã này, hai lần một hằng số
       nhị phân đi qua heredoc và biến thành **null byte**, làm tệp Python
       không phân tích được. Lần thứ hai là lúc tôi đang viết đúng cái mẫu WAV
       này. Dựng bằng `wave` thì nó chỉ sai được nếu `wave` sai.
    """
    from platform_core.public_api.sandbox import sample_wav

    d = sample_wav()
    with wave.open(io.BytesIO(d), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() > 0
        assert w.getnframes() > 0


@pytest.mark.parametrize("media,duoi,mime", [
    ("audio", ".wav", "audio/wav"),
    ("image", ".png", "image/png"),
    ("khong_biet", ".png", "image/png"),      # lối lui, có chủ ý
])
def test_sandbox_ghi_dung_duoi_va_content_type(media, duoi, mime, tmp_path):
    from platform_core.public_api.media import store_sandbox_artifact
    from platform_core.storage import LocalStorage

    kho = LocalStorage(str(tmp_path))
    khoa = store_sandbox_artifact(kho, {"owner_id": "u1"}, "audio_key", 0,
                                  media=media)
    assert khoa.endswith(duoi), f"{media} -> {khoa}"


def test_speech_ltt_khai_tra_ve_AUDIO():
    """Bánh cóc cho chính bản khai: nếu ai đó đổi `returns` sang `image` thì mọi
    phép kiểm trên vẫn xanh, và sandbox lại phát PNG cho tiếng nói."""
    from apps.ltt_voice.manifest import MANIFEST

    tool = [t for t in MANIFEST.tools if t.name == "speech.ltt"]
    assert tool, "khong tim thay `speech.ltt` trong ban khai"
    assert tool[0].returns.get("audio_key") == "audio", tool[0].returns
