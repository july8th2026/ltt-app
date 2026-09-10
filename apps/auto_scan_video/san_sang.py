"""Auto Scan Video co CHAY DUOC tren may nay khong — mot cau tra loi, doc duoc.

## Vi sao can, va vi sao no khong phai mot route moi

`/health/ready` cua nen tang tra loi hai cau: CSDL co song khong, va tien trinh
co mo coi khong. Ca hai deu dung va ca hai deu **khong** noi gi ve nhung thu Auto
Scan that su can: ffmpeg, may sinh tieng, cua goi model, bo ma hoa phan cung.

⇒ Mot lan chay se di qua bon giai doan roi hong o giai doan thu nam vi mot dich
  vu chua duoc cau hinh — trong khi `/health/ready` van noi `ready`. Nguoi van
  hanh biet dieu do **sau** khi khach da doi va credit da bi giu.

⛔ Nhung day KHONG phai mot route moi. Pha 25 cam mo rong tinh nang, va them mot
   endpoint la them be mat cong khai. Day la mot HAM: runbook goi no, phep kiem
   goi no, va khi nao nen tang mo hop dong cho app dong gop vao `/health/ready`
   thi cho do goi no.

## Ba muc do, khong phai hai

    `bat_buoc`  thieu => Auto Scan khong chay duoc lan nao
    `tuy_chon`  thieu => mot phan nang luc mat, phan con lai van chay
    `chua_do`   khong hoi duoc ma khong tra loi duoc => **khong** duoc coi la du

🔑 Muc thu ba ton tai vi mot phep hoi hong khong duoc phep trong nhu mot phep hoi
   tra loi "khong". `giong_noi.san_sang()` bat moi ngoai le va tra `False`; o day
   ta phan biet "da hoi, chua cau hinh" voi "hoi khong duoc" — hai viec do doi
   hai hanh dong khac nhau cua nguoi van hanh.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

#: Ba muc do cua mot phu thuoc.
BAT_BUOC = "bat_buoc"
TUY_CHON = "tuy_chon"

#: Ba trang thai cua mot phep hoi.
CO = "co"
KHONG = "khong"
CHUA_DO = "chua_do"


@dataclass(frozen=True)
class PhuThuoc:
    ten: str
    muc: str
    trang_thai: str
    #: Cau ngan cho nguoi van hanh: thieu thi lam gi.
    ghi_chu: str = ""


def _hoi(ten: str, muc: str, ham, ghi_chu_khi_thieu: str) -> PhuThuoc:
    """Goi mot phep hoi, va phan biet 'khong co' voi 'khong hoi duoc'."""
    try:
        co = bool(ham())
    except Exception as loi:            # noqa: BLE001 - xem docstring dau tep
        return PhuThuoc(ten, muc, CHUA_DO,
                        f"khong hoi duoc ({type(loi).__name__})")
    return PhuThuoc(ten, muc, CO if co else KHONG,
                    "" if co else ghi_chu_khi_thieu)


def _co_ffmpeg() -> bool:
    from platform_core import media

    return bool(media.ffmpeg_bin())


def _co_may_giong() -> bool:
    from . import giong_noi

    return giong_noi.san_sang()


def _co_cua_model() -> bool:
    """Cua goi model co provider nao khong.

    ⚠️ Chi hoi **cau hinh**, khong goi thu mot luot. Mot phep kiem san sang ma
       tieu tien cua khach la mot phep kiem khong ai dam chay thuong xuyen.
    """
    from . import ai

    return bool(ai.THU_TU_PROVIDER)


def _co_bo_ma_hoa_phan_cung() -> bool:
    from platform_core import media

    from . import che_do_render as cdr

    return media.detect_gpu_encoder() not in ("", cdr.LUI_VE)


def _co_sidecar_asr() -> bool:
    """Sidecar WhisperX — duong ASR cua production.

    🔴 Thieu no KHONG lam Auto Scan chet: `transcribe_file` tut xuong
       faster-whisper trong tien trinh. Nhung pha 24 do duoc rang duong tut
       xuong do **hong tren may nay** (`cublas64_12.dll` khong nap duoc) tru khi
       co nguoi dat `LTT_AUTOSUB_WHISPER_DEVICE=cpu`. Nen no la `tuy_chon` ve
       hop dong va la thu nguoi van hanh phai NHIN THAY.
    """
    return bool(str(os.environ.get("LTT_WHISPERX_PYTHON", "")).strip())


def kiem() -> list[PhuThuoc]:
    """Toan bo phu thuoc cua Auto Scan, moi cai mot dong."""
    return [
        _hoi("ffmpeg", BAT_BUOC, _co_ffmpeg,
             "cai ffmpeg hoac dat LTT_FFMPEG_BIN"),
        _hoi("may_sinh_tieng", BAT_BUOC, _co_may_giong,
             "dat LTT_VOICE_SIDECAR_TOKEN va bat LTTStudioVoice o :8120"),
        _hoi("cua_goi_model", BAT_BUOC, _co_cua_model,
             "khong provider nao duoc khai trong ai.THU_TU_PROVIDER"),
        _hoi("sidecar_asr", TUY_CHON, _co_sidecar_asr,
             "dat LTT_WHISPERX_PYTHON; neu khong, dat "
             "LTT_AUTOSUB_WHISPER_DEVICE=cpu de tranh duong CUDA hong"),
        _hoi("bo_ma_hoa_phan_cung", TUY_CHON, _co_bo_ma_hoa_phan_cung,
             "khong co NVENC — preset cat se ma hoa bang CPU"),
    ]


def san_sang() -> bool:
    """Co du thu BAT BUOC de nhan mot lan chay khong.

    ⛔ `CHUA_DO` **khong** tinh la du. Mot phep hoi hong khong duoc phep trong
       nhu mot cau tra loi.
    """
    return all(p.trang_thai == CO for p in kiem() if p.muc == BAT_BUOC)


def tom_tat() -> dict:
    """Ban khai de runbook va nguoi van hanh doc. Khong duong dan, khong bi mat.

    ⛔ Khong tra ve gia tri cua bien moi truong nao — chi tra ve CO/KHONG. Mot
       ban bao trang thai lo mot token la mot ban bao khong duoc phep xem.
    """
    ds = kiem()
    return {
        "san_sang": all(p.trang_thai == CO for p in ds if p.muc == BAT_BUOC),
        "phu_thuoc": [
            {"ten": p.ten, "muc": p.muc, "trang_thai": p.trang_thai,
             "ghi_chu": p.ghi_chu}
            for p in ds
        ],
    }
