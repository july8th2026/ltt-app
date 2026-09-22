"""Giai doan TRANSCRIBE — chep loi thanh ban ghi chinh tac.

Mot artifact ra:

    transcript.json   ban ghi chinh tac   (kind=json)

## Vi sao BOC ma cua `autosubvideo` chu khong uy quyen mot job sang no

ADR-001 D5 dat ra luat: *uy quyen khi manifest cua app dich trung thuc va hop
dong cua no cong khai; boc ma khi khong.*

`apps/autosubvideo/manifest.py:47,51` khai `requires=("ffmpeg",)` **trong khi**
khai `gpu_vram_mb` cho `transcribe` va `diarize` (RISK-00-11). Uy quyen sang do
la ke thua mot ban khai sai: tren mot doi hinh chia lan, viec GPU se bi xep vao
lan ffmpeg va chay tren mot may khong co card.

⇒ Ta boc **ham** `transcription.transcribe_file` va chay no trong `asv_gpu`, la
  app khai `requires=("gpu",)` mot cach trung thuc. Canh phu thuoc lien-app duoc
  khai o `tools/lint_app_contract.py` + `apps/autosubvideo/__init__.py`, nen no
  la mot quyet dinh nhin thay duoc chu khong phai mot lan voi tay lang le.

⭐ Va vi ta khong dong vao `autosubvideo`, **duong cu cua no van chay nguyen** —
   dung dieu cong thoat cua pha 10 doi (O10, "legacy caller remains working").

## Vi sao khong dung engine di san `Bot_Whisper_FULL`

Prompt 10 viet ra khi chua biet trong nen tang **da co** duong whisper. Ban di
san co hai cho goi `gpu_arbiter.current_gpu` (`engine/stt.py:274`,
`whisper_integration.py:207`) — tuc no tu chon card, dung thu I11/O6 cam. Boc
duong da co trong nen tang re hon va sach hon; khac biet nay duoc ghi lai chu
khong lam lang.

⛔ Prompt 10 cam: khong dich, khong TTS trong giai doan nay.
"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_ghi, nhap_media, pipeline
from .giai_doan_media import ThieuNguon

#: Model ASR. Ten nay di vao van tay: doi model = ban ghi khac = cache cu vo hieu.
MODEL_ASR = "large-v3"
#: Doi khi doi cach chuan hoa/goi engine. Cung vao van tay.
#: 2 (22/09): rut phan vai + ep ngon ngu nguon khach khai vao ASR.
PHIEN_BAN_MA = 2


class ThieuBanTieng(ThieuNguon):
    """Giai doan truoc chua sinh ra ban tieng cho ASR."""


def _khoa_tieng_asr(db, run) -> str:
    """Khoa cua ban tieng 16 kHz do MEDIA_PREPARE sinh ra.

    ⭐ Lay tu `outputs` cua giai doan truoc chu khong tu dat lai duong dan: mot
       duong dan tu dat se im lang tro sai ngay khi giai doan truoc doi cach dat
       ten, con `outputs` thi khong the.
    """
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    for khoa in ((truoc.outputs or {}).get("khoa_asset") or []) if truoc else []:
        if khoa.endswith(".wav"):
            return khoa
    raise ThieuBanTieng(_t('Chưa có bản tiếng để chép lời.'))


def chep_loi(duong_tieng: str, *, ngon_ngu: str = "", ctx=None) -> dict:
    """Goi engine ASR. Tra ve ket qua THO cua engine.

    Tach rieng khoi `chay()` de phep doi chieu (parity) goi duoc dung ham nay va
    so voi ban goc ma khong phai dung ca mot lan chay.

    🔑 `gpu_uuid` den tu `JobContext` — card do **nen tang** cap qua
       `platform_core.gpu_lease`. Ta chuyen tiep, khong bao gio tu chon (I11/O6).
    """
    from apps.autosubvideo.transcription import transcribe_file

    tien_do = getattr(ctx, "progress", None) if ctx is not None else None
    huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    uuid_card = str(getattr(ctx, "gpu_uuid", "") or "") if ctx is not None else ""

    return transcribe_file(
        duong_tieng, language=ngon_ngu, model_name=MODEL_ASR,
        on_progress=tien_do, is_cancelled=huy, gpu_uuid=uuid_card)


# ⛔ Phan vai (`can_phan_vai`/`phan_vai`) DA RUT 22/09 (asv-final): MOT giong
#    thuyet minh cho ca video, khong ai doc `nguoi_noi`. No tung chay pyannote
#    tren GPU o moi lan AUTO_MATCH cho mot ket qua bi vut (TRANG_THAI_V6 pha 20).


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ban tieng -> chep loi -> chuan hoa -> kiem. Tra ve phan de promote."""
    khoa_tieng = _khoa_tieng_asr(db, run)

    with tempfile.TemporaryDirectory(prefix="asv-asr-") as tam:
        thu_muc = Path(tam)
        duong = kho.local_path(khoa_tieng) if hasattr(kho, "local_path") else None
        if not duong:
            duong = str(thu_muc / "tieng.wav")
            with kho.open(khoa_tieng) as f:
                Path(duong).write_bytes(f.read())

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5, _t('Đang chép lời'))

        from . import cai_dat as cd, ngon_ngu as nn
        cai = cd.doc(run)
        khai = nn.chuan_nguon(cai.ngon_ngu_nguon)
        tho = chep_loi(duong, ngon_ngu="" if khai == nn.TU_DOAN else khai,
                       ctx=ctx)

        tt = nhap_media.soi(duong)
        ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=tt["thoi_luong"])

        # ⛔ Ban ghi khong duoc keo dai hon chinh ban tieng. Neu co, moc thoi
        #    gian da troi, va TIMING se dat tieng vao mot cho khong co hinh.
        cuoi = max(float(d["ket"]) for d in ban["doan"])
        if cuoi > tt["thoi_luong"] + 1.0:
            raise ban_ghi.BanGhiError(
                _t('Bản ghi dài hơn bản tiếng — mốc thời gian đã trôi.'))

        # 🔑 Chot cap ngon ngu NGAY SAU ASR, truoc moi giai doan tra tien
        #    (LLM, giong). Xem `ngon_ngu.kiem_nguon_da_doan`.
        ban["ngon_ngu"] = nn.kiem_nguon_da_doan(ban.get("ngon_ngu"),
                                               cai.ngon_ngu_dich)

        goi = json.dumps(ban, sort_keys=True, ensure_ascii=False).encode("utf-8")
        vt = ban_ghi.van_tay_ban_ghi(
            checksum_tieng=assets.bam_tep(duong),
            model=MODEL_ASR,
            ngon_ngu=str(ban.get("ngon_ngu") or ""),
            phien_ban_ma=PHIEN_BAN_MA)

        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TRANSCRIBE, van_tay=vt,
                                   duoi="json")
        kho.put(khoa, io.BytesIO(goi), content_type="application/json")

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(95, _t('Đang lưu kết quả'))

        return {
            "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                      "van_tay": vt}],
            "tom_tat": ban_ghi.tom_tat(ban),
        }
