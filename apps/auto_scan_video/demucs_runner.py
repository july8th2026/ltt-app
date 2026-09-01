"""Tien trinh con tach nguon tieng. Chay bang `python -m apps.auto_scan_video.demucs_runner`.

    python -m apps.auto_scan_video.demucs_runner <vao.wav> <thu_muc_ra>

## Vi sao la TIEN TRINH CON chu khong phai mot lan goi ham

Hai ly do, ca hai deu la kinh nghiem cua chinh kho nay:

1. **Card do nen tang cap.** `platform_core.gpu_lease` giu cho mot card roi
   `JobContext.gpu_env()` truyen no xuong qua bien moi truong. Mot tien trinh
   con thua huong moi truong do; mot lan goi ham trong worker thi khong — no
   se thay bat cu card nao torch tu chon, va do la mot cuoc dua voi chinh cai
   lease vua giu.

2. **Torch/CUDA sap la sap ca tien trinh.** `job_worker.py` da ghi ly do do khi
   giai thich vi sao worker la tien trinh rieng chu khong phai luong: "job nang
   goi thu vien C/CUDA giu GIL va co the sap ca tien trinh; mot job hong khong
   duoc keo theo job cua khach hang khac". Cung lap luan ay ap dung o day.

## Vi sao KHONG dung `torchaudio.save` — va vi sao khong va no nhu ban di san

Ban di san (`Cut_only ver2/nerf_engine/stages/audio.py:8`) tiem mot ban va vao
`torchaudio.save` de doi sang `soundfile`, vi `torchaudio >= 2.10` doi
`torchcodec` ma DLL cua no hong tren Windows. Ban va do dung — nhung no phu
thuoc `soundfile`, va **`soundfile` khong co trong moi truong nay**:

    torchaudio 2.11.0+cpu
    torchaudio.save -> ImportError: TorchCodec is required for save_with_torchcodec
    soundfile      -> KHONG CAI

⭐ Nen thay vi tiem mot ban va vao ruot mot thu vien khac de goi mot thu vien
   thu ba, tep nay **khong goi `torchaudio.save`**. No doc va ghi WAV bang
   module `wave` cua thu vien chuan. Bo di mot phu thuoc, mot ban va toan cuc,
   va ca mot lop hong chi xuat hien tren Windows.

⛔ Khong in gi ra stdout ngoai dong JSON ket qua o cuoi: tien trinh cha doc
   stdout de lay ket qua.
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

#: Ten cac nguon ma htdemucs tach ra. Thu tu do model quyet dinh, khong phai ta.
NGUON_MONG_DOI = ("drums", "bass", "other", "vocals")


def doc_wav(duong: str):
    """WAV PCM 16-bit -> (mang float32 [kenh, mau], tan_so). Khong dung torchaudio."""
    import numpy as np

    with wave.open(duong, "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError("chi ho tro WAV PCM 16-bit")
        kenh = f.getnchannels()
        tan_so = f.getframerate()
        khung = f.readframes(f.getnframes())
    mau = np.frombuffer(khung, dtype="<i2").astype("float32") / 32768.0
    return mau.reshape(-1, kenh).T, tan_so


def ghi_wav(duong: str, mang, tan_so: int) -> None:
    """(kenh, mau) float32 -> WAV PCM 16-bit.

    Kep bien do TRUOC khi doi kieu: mot mau vuot [-1, 1] ma doi thang sang int16
    se **cuon vong** — mot dinh am to bien thanh mot tieng no. Kep thi no chi bi
    cat ngon, nghe duoc.
    """
    import numpy as np

    x = np.clip(np.asarray(mang, dtype="float32"), -1.0, 1.0)
    i16 = (x * 32767.0).astype("<i2")
    with wave.open(duong, "wb") as f:
        f.setnchannels(int(i16.shape[0]))
        f.setsampwidth(2)
        f.setframerate(int(tan_so))
        f.writeframes(i16.T.tobytes())


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(json.dumps({"loi": "cach dung: <vao.wav> <thu_muc_ra>"}))
        return 2
    vao, thu_muc = argv[1], Path(argv[2])
    thu_muc.mkdir(parents=True, exist_ok=True)

    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    # Card da duoc nen tang cap qua bien moi truong (xem ghi chu dau tep). Ta
    # chi HOI xem torch thay gi — khong bao gio tu chon.
    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"

    model = get_model("htdemucs")
    model.eval()

    mau, tan_so = doc_wav(vao)
    if mau.shape[0] == 1:
        # htdemucs mong doi stereo. Nhan doi kenh thay vi de model tu doan.
        import numpy as np
        mau = np.vstack([mau, mau])

    x = torch.from_numpy(mau).unsqueeze(0)
    with torch.no_grad():
        ra = apply_model(model, x, device=thiet_bi, progress=False)[0]

    duong_ra = {}
    for i, ten in enumerate(model.sources):
        dich = thu_muc / f"{ten}.wav"
        ghi_wav(str(dich), ra[i].cpu().numpy(), tan_so)
        duong_ra[ten] = str(dich)

    print(json.dumps({
        "nguon": list(model.sources),
        "duong": duong_ra,
        "tan_so": int(tan_so),
        "thiet_bi": thiet_bi,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
