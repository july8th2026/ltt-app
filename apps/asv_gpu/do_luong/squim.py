"""Bo do `chat_luong_tieng`: torchaudio SQUIM_OBJECTIVE, khong can tham chieu.

    do_squim(doan=[{ma, tep}], gpu_uuid) ->
      {"ket_qua": {ma: {stoi, pesq, si_sdr, *_min_cua_so}}, "tai_nguyen": {...}}

Uoc luong STOI (0-1), PESQ (1-4,5), SI-SDR (dB) tu CHINH tieng da long — khong
can ban sach de so (Kumar et al., ICASSP 2023). Dung de CAM CO doan co nhieu,
meo tieng hoac dut quang: ngoai diem ca doan con diem THAP NHAT tren cua so
truot `CUA_SO_S`, vi mot tieng click/dut 200 ms bi pha loang trong trung binh
cua mot cau 8 giay.

## License — da doc tu ban CAI THAT (torchaudio 2.8.0, qc-venv, 22/09/2026)

`torchaudio/pipelines/_squim_pipeline.py`, docstring `SQUIM_OBJECTIVE`:
*"The weights are under Creative Commons Attribution 4.0 International
License"* (dan `microsoft/DNS-Challenge` LICENSE). Code BSD-2-Clause. CC BY 4.0
cho phep dung thuong mai, BAT BUOC ghi cong: xem
`docs/auto_scan_video_final/L_GIONG.md` muc Ghi cong.

⛔ `SQUIM_SUBJECTIVE` (cung tep) la CC BY-NC 4.0 — KHONG dung.

## Weights ghim

URL + sha256 o duoi. Runner tai vao `TORCH_HOME/hub/torchaudio/models/` (cung
duong `torchaudio.utils.download_asset` dung) va KIEM sha256 truoc khi nap —
`download_asset` khong kiem gi khi tep da ton tai.
"""
from __future__ import annotations

from pathlib import Path

from . import venv

SCRIPT = Path(__file__).with_name("squim_runner.py")

URL_WEIGHTS = "https://download.pytorch.org/torchaudio/models/squim_objective_dns2020.pth"
SHA256_WEIGHTS = "2c54586fea83fb5eb5394d710038ee89f55cab7011a5bf730bebed4c8777e828"
#: Cua so truot (giay) cho diem thap nhat trong mot doan, va buoc truot.
CUA_SO_S = 2.0
BUOC_S = 1.0

PHIEN_BAN = f"squim_objective_dns2020/{SHA256_WEIGHTS[:12]}/cua_so{CUA_SO_S}"


def do_squim(doan: list[dict], *, gpu_uuid: str = "", is_cancelled=None) -> dict:
    ds = [{"ma": str(d["ma"]), "tep": str(d["tep"])} for d in doan or []]
    # ⭐ `buoc_gpu` = "nen tang DA cap card", khong phai "may co card". Do
    #    24/09: GPU 3,87 s / CPU 9,38 s (2,4x) tren 6 doan x 8 s, diem lech
    #    <= 0,0001 ⇒ card la duong dung. Nhung no chi duoc dung khi CO lease:
    #    `chan_card=True` che card o luot khong lease. Xem `_runner.chon_thiet_bi`.
    return venv.chay(SCRIPT, {"doan": ds, "url": URL_WEIGHTS,
                              "sha256": SHA256_WEIGHTS, "cua_so_s": CUA_SO_S,
                              "buoc_s": BUOC_S, "buoc_gpu": bool(gpu_uuid)},
                     timeout_s=600 + 2 * len(ds), gpu_uuid=gpu_uuid,
                     is_cancelled=is_cancelled, chan_card=True)
