"""Bo do `gioi`: GIOI TINH CUA MOT GIONG, do tu tieng - khong hoi nguoi.

    do_gioi(clip=[{ma, tep}], gpu_uuid) ->
      {"ket_qua": {ma: {nhan, p_nam, p_nu, do_tin, ti_le_cua_so_nam,
                        so_cua_so, f0_trung_vi, giay}},
       "tai_nguyen": {...}}

## Cau hoi no tra loi, va cau hoi no KHONG tra loi

Tra loi: *"cai giong nay nghe ra nam hay nu, va chac bao nhieu"*. Do la dung
cau `VoiceProfile.gioi` can (`tables.py`: bo loc cua bo chon giong, duong lui
`lui_giong`, va - tu 23/09 - mat khop duy nhat cua `rang_giong._rang_kho_chung`).

⛔ KHONG tra loi: gioi tinh cua NGUOI da cho clip goc. Model cham **tin hieu
   tieng**, va mot dien vien doc giong khac se duoc cham theo thu no doc. Voi
   san pham thi do lai la cau dung: khach chon giong theo thu ho NGHE.

## Model - license da xac minh tu nguon goc (23/09/2026)

`JaesungHuh/voice-gender-classifier` (ECAPA-TDNN + mot lop tuyen tinh, tinh
chinh tren VoxCeleb2 dev; 98,7% tren VoxCeleb1 identification test theo model
card). Ma **MIT** (`LICENSE` cua repo GitHub, commit `49bcbecf…`), weights
**MIT** (`license: mit` o YAML front-matter cua model card HF). Ban ghim +
sha256: `_ecapa_gioi/ban_ghim.py`; ma da nhung + NOTICE: `_ecapa_gioi/`.

⛔ Cac ung vien DA LOAI (chi tiet: `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md` §2):
   `audeering/wav2vec2-*-age-gender` (CC BY-NC-SA 4.0), openSMILE (giay phep
   nghien cuu, cam ca DAC TRUNG trich bang no), praat-parselmouth (GPL-3.0).

## Vi sao CUA SO TRUOT, khong phai mot diem cho ca clip

Mot nhan duy nhat cho ca doan khong phan biet duoc hai thu rat khac nhau:

  · mot giong nam tram, model chac 0,99 o **moi** cua so;
  · mot giong DIEN doc qua ca hai dai (kho chung co dung mot ca nhu vay -
    `khanh_male_entertainment` / "Robin"), model chac 0,9 o cua so nay va 0,9
    ve phia kia o cua so khac.

Trung binh cua ca hai deu ra "0,9 mot ben". Chi `ti_le_cua_so_nam` moi tach
duoc chung, va do la con so quyet dinh xem mot giong co dang **de trong** hay
khong. `do_tin` vi the lay MIN cua hai thu: xac suat trung binh, va ti le cua
so dong y.

## F0 di kem, va no KHONG phai nguoi phan xu

`f0_trung_vi` (torchaudio `detect_pitch_frequency`, BSD-2) ghi kem de doi chieu
voi bang do 05/09 cua LTT VOICE. ⛔ Khong dung no de quyet dinh: chinh
`toc_do.py` va `tables.py` da ghi lai mot ca bo do cao do nhay quang tam, va
`gioi` sai con te hon `gioi` trong vi no ĐƯỢC TIN.
"""
from __future__ import annotations

from pathlib import Path

from . import venv
from ._ecapa_gioi import ban_ghim

SCRIPT = Path(__file__).with_name("gioi_runner.py")

#: Cua so truot (giay) + buoc. 3 s la khoang mot cau ngan - du dai de ECAPA co
#: ngu canh, du ngan de mot giong doi dai lo ra o ti le cua so.
CUA_SO_S = 3.0
BUOC_S = 1.5
#: Cua so co RMS duoi ngan nay LAN RMS ca clip thi bo (im lang / hoi tho).
#: Khong phai mot nguong pham chat - chi de khong cham mot cua so khong co tieng.
NGUONG_RMS = 0.1

PHIEN_BAN = f"{ban_ghim.PHIEN_BAN}/cua_so{CUA_SO_S}"


def do_gioi(clip: list[dict], *, gpu_uuid: str = "", is_cancelled=None) -> dict:
    ds = [{"ma": str(d["ma"]), "tep": str(d["tep"])} for d in clip or []]
    return venv.chay(SCRIPT, {"clip": ds, "cua_so_s": CUA_SO_S, "buoc_s": BUOC_S,
                              "nguong_rms": NGUONG_RMS},
                     timeout_s=300 + 5 * len(ds), gpu_uuid=gpu_uuid,
                     is_cancelled=is_cancelled)
