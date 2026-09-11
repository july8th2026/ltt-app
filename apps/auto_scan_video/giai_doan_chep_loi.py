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

import logging

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
PHIEN_BAN_MA = 1


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


log = logging.getLogger(__name__)


def can_phan_vai(run) -> bool:
    """Lan chay nay CO can bang chung nguoi noi khong?

    🔑 **Chi `AUTO_MATCH` can.** `hop_dong_v4.CHE_DO_GIONG_TU_KHOP` phai doc dac
       diem nguoi noi that de chon giong khop; khong co bang chung thi "tu khop"
       chi con la "lay giong mac dinh" — dung dieu `ADR-V4-001` D-V4-04 cam.

    ⛔ `USER_SELECTED` **khong** can, va chay phan vai cho no la tra tien GPU cho
       mot ket qua khong ai doc. Pha 07 goi dich danh dieu do: *"do not pay GPU
       cost blindly"*.

    ⚠️ Mac dinh la KHONG chay. Mot nang luc ton GPU phai duoc XIN, khong duoc tu
       bat — thieu thiet lap thi lan chay do khong yeu cau no.
    """
    from . import cai_dat as cd, hop_dong_v4

    return cd.doc(run).che_do_giong == hop_dong_v4.CHE_DO_GIONG_TU_KHOP


def phan_vai(duong_tieng: str, ban: dict, *, ctx=None) -> dict:
    """Chay phan vai qua RANH GIOI da khai cua app chu, roi gan vao ban ghi.

    🔑 `gpu_uuid` den tu `JobContext` — card do **nen tang** cap qua
       `platform_core.gpu_lease`. Ta chuyen tiep, khong bao gio tu chon (I11/O6).
       Truoc pha nay `pyannote_runner` tu lay card dau tien torch thay, bat ke
       lease; tham so do la thu sua dieu ay.

    ⚠️ Phan vai la nang luc PHU. Neu no khong kha dung (thieu `LTT_HF_TOKEN`,
       thieu sidecar) thi lan chay **khong hong**: ban ghi duoc danh dau
       `khong_kha_dung` va di tiep. Mot ban long tieng thieu nhan nguoi noi van
       la mot ban long tieng; mot lan chay hong thi khong.
    """
    from apps.autosubvideo.ai_workflows import assign_speakers, diarize_file

    tien_do = getattr(ctx, "progress", None) if ctx is not None else None
    huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    uuid_card = str(getattr(ctx, "gpu_uuid", "") or "") if ctx is not None else ""

    try:
        luot = diarize_file(duong_tieng, on_progress=tien_do, is_cancelled=huy,
                            gpu_uuid=uuid_card)
    except Exception as loi:          # noqa: BLE001 - xem docstring
        # ⛔ Mot lan HUY khong duoc bien thanh "khong kha dung": huy la y muon
        #    cua nguoi dung va phai noi len tren de vong chay dung han.
        if huy is not None and huy():
            raise
        log.info("phan vai khong kha dung (%s) - di tiep", type(loi).__name__)
        return ban_ghi.danh_dau_phan_vai(ban, ban_ghi.PHAN_VAI_KHONG_KHA_DUNG)

    return ban_ghi.gan_nguoi_noi(ban, luot, gan=assign_speakers)


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

        from . import cai_dat as cd
        tho = chep_loi(duong, ngon_ngu=cd.doc(run).ngon_ngu_nguon,
                       ctx=ctx)

        tt = nhap_media.soi(duong)
        ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=tt["thoi_luong"])

        # ⛔ Ban ghi khong duoc keo dai hon chinh ban tieng. Neu co, moc thoi
        #    gian da troi, va TIMING se dat tieng vao mot cho khong co hinh.
        cuoi = max(float(d["ket"]) for d in ban["doan"])
        if cuoi > tt["thoi_luong"] + 1.0:
            raise ban_ghi.BanGhiError(
                _t('Bản ghi dài hơn bản tiếng — mốc thời gian đã trôi.'))

        # ── Phan vai: CO DIEU KIEN, khong mac dinh ──────────────────────────
        if can_phan_vai(run):
            if ctx is not None and getattr(ctx, "progress", None):
                ctx.progress(70, _t('Đang phân vai người nói'))
            ban = phan_vai(duong, ban, ctx=ctx)
        else:
            ban = ban_ghi.danh_dau_phan_vai(ban, ban_ghi.PHAN_VAI_KHONG_CHAY)

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
