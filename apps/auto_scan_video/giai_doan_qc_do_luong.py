"""Giai doan QC_DO_LUONG — do ban long tieng bang MODEL tren card (lan `gpu`).

    RENDER -> QC (ffmpeg, tat dinh) -> QC_DO_LUONG (model, card) -> QC_AI (LLM/VLM)

Mot artifact ra: `bao_cao_do_luong.json` — ket qua THEO DOAN cua moi bo do trong
`apps.asv_gpu.do_luong.bo_do.BO_DO` (giong: ASR+WER/CER · chat_luong_tieng:
SQUIM · dich: MetricX cua lan "dich"), moi bo do `xong` | `khong_kha_dung` | `loi`.

## Do CAI GI: tung doan tieng, khong phai ban tron cuoi

Dau vao cua moi bo do tieng la tep TTS cua tung doan (`voice_synthesis`), da di
qua DUNG he so co gian `atempo` ma ban phoi ap cho doan do (`he_so_co_gian` cua
`voice_index.json`), doi ve 16 kHz mono. Tuc: dung cau khan gia nghe, TRU nen.

⭐ Vi sao khong cat tu ban tron cuoi (`master.wav`/mp4):
   * ban tron co NEN (nhac/tieng dong da tach cua video goc). ASR chep ca loi
     con sot trong nen, SQUIM cham nen la "nhieu" — hai bo do se do nen chu
     khong do giong;
   * ranh gioi doan tren ban tron la vi tri KE HOACH, cat theo do se cat vao
     dau/cuoi cau khi doan ke sat nhau — sinh loi XOA/CHEN gia o bien;
   * don vi sua (`sua_chua`, `voice_synthesis`) la TUNG DOAN: do tung doan cho
     ket qua gan thang vao don vi sua, khong can can hang lai.
⚠️ Cai KHONG do duoc theo cach nay: loi sinh ra o buoc tron (amix, loudnorm,
   fade). Nhung buoc do la ffmpeg tat dinh va da co cong QC rieng (T4/T5
   loudnorm, T7/T11 troi) — khong phai viec cua mot bo do model.

## ⛔ Khong nem khi co doan khong dat

Cung nguyen tac voi `qc_ai`: mot doan doc sai la mot DON VI can lam lai, khong
phai mot lan chay hong. `jobs._sua_chua_neu_can` doc `tom_tat` va quyet dinh.
Bo do thieu venv/model ⇒ `khong_kha_dung` trong bao cao, giai doan van xong.
"""
from __future__ import annotations

import io
import json
import logging
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, pipeline, sua_chua
from .giai_doan_media import ThieuNguon, _duong_doc_duoc
from .giai_doan_qc import _doc_json, _khoa_theo_duoi

log = logging.getLogger(__name__)

#: Doi khi doi cach dung dau vao / cach doc ket qua. Vao van tay.
PHIEN_BAN_DO_LUONG_GD = 1

#: Tan so mau dau vao cua ca hai bo do tieng (whisper + SQUIM deu 16 kHz).
TAN_SO = 16000


#: Nguong CANH BAO chat luong tieng (SQUIM). KHONG sinh viec sua — chi ghi vao
#: bao cao cho nguoi van hanh, vi mot doan "nghe hoi don" van la mot ban giao
#: duoc, con doc lai thi ton tien.
#:
#: Hieu chinh 23/09 tren 50 doan tieng THAT cua LTT Voice (36 vi + 14 en):
#:   PESQ ca doan   thap nhat 2,719 · p50 3,28 (vi) / 3,41 (en)
#:   SI-SDR ca doan thap nhat 15,31 dB
#:   doi chung nhieu trang SNR ~10 dB: PESQ p50 1,19 (vi) / 1,24 (en)
#: ⇒ PESQ < 2,0 nam GIUA hai dam, khong sat ben nao; SI-SDR < 10 dB duoi ca
#:   doan te nhat da do.
#: ⚠️ DA DO VA KHONG DUNG: SQUIM **khong** thay mot khoang lang 0,4 s chen giua
#:    cau (SI-SDR cua so thap nhat 15,96 so voi 16,58 cua ban sach). Dut quang
#:    kieu do phai bat bang phep do khac — dung doc bang chung nay thanh "da co
#:    cong gac cho dut quang".
NGUONG_CANH_BAO_TIENG = {"pesq": 2.0, "si_sdr": 10.0}


def canh_bao_tieng(ket_qua: dict) -> list[dict]:
    """Doan co diem SQUIM duoi nguong canh bao (bat ky chi so nao)."""
    ra = []
    for ma, r in (ket_qua or {}).items():
        thap = {k: r[k] for k, v in NGUONG_CANH_BAO_TIENG.items()
                if r.get(k) is not None and float(r[k]) < v}
        if thap:
            ra.append({"ma": ma, **thap, "nguong": dict(NGUONG_CANH_BAO_TIENG)})
    return ra


class ThieuTieng(ThieuNguon):
    """Chua co ban ke doan tieng de do."""


def _ban_ke_tieng(db, kho: Storage, run) -> dict:
    khoa = _khoa_theo_duoi(db, run, pipeline.VOICE_SYNTHESIS, ".json")
    if not khoa:
        raise ThieuTieng(_t('Chưa có bản kê đoạn tiếng để đo.'))
    return _doc_json(kho, khoa)


def _dung_tep(nguon: str, dich: str, he_so: float, *, hoi_huy=None) -> None:
    """TTS -> 16 kHz mono, qua CUNG `atempo` ban phoi da ap (`am_master`)."""
    from platform_core import media

    from .nhap_media import MediaError, _chay

    loc = [f"atempo={he_so:.6f}"] if abs(he_so - 1.0) > 1e-6 else []
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", nguon, *(["-af", ",".join(loc)] if loc else []),
           "-ac", "1", "-ar", str(TAN_SO), "-c:a", "pcm_s16le", dich]
    r = _chay(cmd, timeout=300, hoi_huy=hoi_huy)
    if r.returncode != 0:
        raise MediaError((r.stderr or b"").decode("utf-8", "replace")[-300:])


def _ghi_bao_cao(kho: Storage, *, run, bao_cao: dict) -> dict:
    goi = json.dumps(bao_cao, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = assets.bam(goi)
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.QC_DO_LUONG, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")
    return {"staging_key": khoa, "kind": "json", "duoi": "json", "van_tay": vt}


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    from apps.asv_gpu.do_luong import bo_do

    from . import cai_dat as cd, giai_doan_chep_loi

    bao = getattr(ctx, "progress", None) if ctx is not None else None
    huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    uuid_card = str(getattr(ctx, "gpu_uuid", "") or "") if ctx is not None else ""

    cai = cd.doc(run)
    ban_ke = _ban_ke_tieng(db, kho, run)
    khoa_dich = _khoa_theo_duoi(db, run, pipeline.CONTENT_PROCESS, ".json")
    tai_lieu = _doc_json(kho, khoa_dich) if khoa_dich else {}
    muc = {str(m.get("ma")): m for m in (tai_lieu.get("muc") or [])}
    nn_dich = str(tai_lieu.get("ngon_ngu_dich") or cai.ngon_ngu_dich or "")
    nn_goc = str(tai_lieu.get("ngon_ngu_goc") or "")

    cap_dich = [{"ma": ma, "nguon": str(m.get("goc") or ""),
                 "dich": str(m.get("chu") or "")}
                for ma, m in muc.items() if m.get("goc") and m.get("chu")]

    with tempfile.TemporaryDirectory(prefix="asv-do-") as tam:
        thu_muc = Path(tam)
        doan: list[dict] = []
        for i, d in enumerate(ban_ke.get("doan") or []):
            ma = str(d.get("ma") or "")
            khoa = str(d.get("khoa") or "")
            # 🔑 `chu` cua ban ke = cau CUOI CUNG may da doc (sau bac thang nan).
            #    Ban ke cu (truoc 22/09) khong co ⇒ lay cau cua ban dich.
            chu = str(d.get("chu") or (muc.get(ma) or {}).get("chu") or "")
            if not ma or not khoa or not chu:
                continue
            tm = thu_muc / f"n{i:04d}"
            tm.mkdir()
            nguon = _duong_doc_duoc(kho, khoa, tm)
            dich = str(thu_muc / f"{i:04d}.wav")
            _dung_tep(nguon, dich, float(d.get("he_so_co_gian") or 1.0),
                      hoi_huy=huy)
            doan.append({"ma": ma, "tep": dich, "chu": chu})
        if bao:
            bao(10, _t('Đang đo giọng đọc'))

        dv = bo_do.DauVao(doan_tieng=doan, cap_dich=cap_dich,
                          ngon_ngu_nguon=nn_goc, ngon_ngu_dich=nn_dich,
                          tu_dien=dict(cai.tu_dien or {}),
                          model_asr=giai_doan_chep_loi.MODEL_ASR)
        ket = bo_do.chay_tat_ca(
            dv, gpu_uuid=uuid_card, is_cancelled=huy,
            bao=(lambda i, ten: bao(10 + 80 * i // max(1, len(bo_do.BO_DO)),
                                    _t('Đang đo chất lượng'))) if bao else None)

    giong = ket.get("giong") or {}
    do_duoc = [{"ma": ma, "ngon_ngu": nn_dich, **r}
               for ma, r in (giong.get("ket_qua") or {}).items()
               if "wer" in r]
    khong_dat = sua_chua.giong_khong_dat(do_duoc)
    canh_bao = canh_bao_tieng((ket.get("chat_luong_tieng") or {}).get("ket_qua"))

    bao_cao = {"phien_ban": PHIEN_BAN_DO_LUONG_GD, "ngon_ngu_dich": nn_dich,
               "so_doan": len(doan), "bo_do": ket}
    phan = _ghi_bao_cao(kho, run=run, bao_cao=bao_cao)
    if bao:
        bao(95, _t('Đang lưu báo cáo'))
    return {
        "phan": [phan],
        # 🔑 Vong sua doc `qc_giong_khong_dat` tu `stage.outputs` (khong mo kho).
        #    Chi ghi phan KHONG DAT + trang thai tung bo do; bang day du o artifact.
        "tom_tat": {
            "so_doan_do": len(doan),
            "do_luong": {t: r.get("trang_thai") for t, r in ket.items()},
            "so_giong_khong_dat": len(khong_dat),
            "qc_giong_khong_dat": khong_dat,
            # ⚠️ CANH BAO, khong phai viec sua: khong doan nao bi doc lai vi so
            #    nay. Nguoi van hanh doc; `sua_chua` khong doc.
            "canh_bao_tieng": canh_bao,
        },
    }
