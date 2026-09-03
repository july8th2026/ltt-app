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


#: So luong torch duoc dung. ⛔ KHONG phai so loi cua may.
#:
#: 🔴 **Do duoc 03/09, va no la nguyen nhan gan nhat cua mot lan may chet.**
#:    Hop den ghi lai **muoi hai tien trinh nay chay trong 4 phut 12 giay, moi
#:    cai dinh 462-984% CPU** — tuc moi tien trinh mot minh doi 5 den 10 loi
#:    logic. Luc 16:51:09 CPU cham 100%, RAM trong tut tu 17,7 xuong 14,1 GB,
#:    va may khong ghi them dong nao nua.
#:
#: ⚠️ Truoc ban nay tep nay **khong dat gioi han nao**. Torch tren CPU mac dinh
#:    lay het loi vat ly, va `apply_model` cua demucs song song rat sau.
#:
#: 🔑 Va day la cho ma ngan sach cua gate **khong voi toi duoc**: `-n 6` dem
#:    WORKER PYTEST, khong dem thu moi worker sinh ra. Sau worker, moi worker
#:    mot demucs, moi demucs muoi luong = 60 luong tren 10 loi. Mot tien trinh
#:    chau khong xin khoa, khong khai bao, va khong nam trong bat cu phep tinh
#:    nao — no chi hien ra o phep DO tai (`gate.loi_dang_ban`).
#:
#: ⭐ **4, khong phai 2 va khong phai 10** — va con so nay dua tren MOT dU KIEN
#:    do duoc, khong phai mot cam giac an toan:
#:
#:    Trong PRODUCTION chi co **MOT** demucs chay tai mot thoi diem.
#:    `pipeline.CHUOI` khai `AUDIO_PREPARE` va `TRANSCRIBE` dung **chung mot ten
#:    tai nguyen** `tach_nguon_cuc_bo` voi `tai_nguyen_suat=1`, va nen tang
#:    cuong che that bang lease (`job_runner._cho_tai_nguyen` + `leases`).
#:
#:    ⇒ Chan xuong 2 se lam mot job cua khach that cham gap ~5 lan de doi lay
#:      mot thu khong xay ra. Mot tran an toan phai bao ve truoc mot moi nguy CO
#:      THAT, khong phai truoc mot moi nguy tuong tuong.
#:
#: ⚠️ Truong hop NHIEU demucs cung luc chi ton tai trong BO TEST (sau `-n 6`),
#:    va no da nam sau rao chan `LTT_TEST_NANG`. O do 6 x 4 la vuot suat, nhung
#:    moi tien trinh van co tran — khac han voi truoc, khi moi cai lay het may.
#:
#: 🔑 Va 4 khong phai mot nua cua 10 lam tron: demucs het gan het loi ich song
#:    song quanh 4 luong, nen phan tu 4 len 10 mua duoc rat it toc do ma tra ca
#:    kha nang dap ung cua may.
LUONG_TORCH = 4

#: Cho phep chu may go de: `set LTT_DEMUCS_LUONG=6`.
BIEN_LUONG = "LTT_DEMUCS_LUONG"


def _dat_tran_luong(torch) -> int:
    """Chan so luong torch. Tra ve so da dat, de ghi vao ket qua.

    ⛔ Dat TRUOC `apply_model`. `torch.set_num_threads` sau khi mot phep tinh
       da bat dau thi khong con tac dung len phep tinh do.
    """
    import os

    try:
        n = int(os.environ.get(BIEN_LUONG, "") or LUONG_TORCH)
    except ValueError:
        n = LUONG_TORCH
    n = max(1, n)
    try:
        torch.set_num_threads(n)
        # Luong lien-phep-tinh: mac dinh cua torch cung la so loi. Mot phep
        # `set_num_threads` khong cham toi no.
        if hasattr(torch, "set_num_interop_threads"):
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                # Chi dat duoc TRUOC phep tinh dau tien cua tien trinh. Neu da
                # muon thi bo qua — `set_num_threads` da lo phan lon.
                pass
    except (AttributeError, RuntimeError):
        return 0
    return n


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(json.dumps({"loi": "cach dung: <vao.wav> <thu_muc_ra>"}))
        return 2
    vao, thu_muc = argv[1], Path(argv[2])
    thu_muc.mkdir(parents=True, exist_ok=True)

    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    _dat_tran_luong(torch)

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
        "luong_torch": _dat_tran_luong(__import__("torch")),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
