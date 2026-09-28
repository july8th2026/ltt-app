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
import logging
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_ghi, nhap_media, pipeline
from .giai_doan_media import ThieuNguon, _duong_doc_duoc

log = logging.getLogger(__name__)

#: Model ASR. Ten nay di vao van tay: doi model = ban ghi khac = cache cu vo hieu.
MODEL_ASR = "large-v3"
#: Doi khi doi cach chuan hoa/goi engine. Cung vao van tay.
#: 2 (22/09): rut phan vai + ep ngon ngu nguon khach khai vao ASR.
#: 3 (22/09, lan ocr): dinh tuyen nguon loi embedded -> OCR hardsub -> ASR
#:   (`nguon_loi.py`), ban ghi mang `nguon_loi` + `do_tin`.
#:   ⛔ **Da BO 26/09 (Task 21)** — MOT duong duy nhat voice->voice. Ban ghi van
#:   mang `nguon_loi`, nay luon `asr`. Xem `nguon_loi.py` dau tep.
#: 4 (28/09, B13 B1): them tin hieu AO GIAC THU BA (vong lai `initial_prompt`,
#:   xem `ban_ghi.nghi_ao_giac`/`danh_dau_nghi_ao_giac`) — thay doi TAP HOP
#:   doan duoc gan co `nghi_ao_giac` trong `ban` cho CUNG mot dau vao, nen
#:   cache cu (van_tay cu) se AN nhung doan ao giac moi ma khong tang so nay.
PHIEN_BAN_MA = 4


class ThieuBanTieng(ThieuNguon):
    """Giai doan truoc chua sinh ra ban tieng cho ASR."""


def _canh_bao_ao_giac(ban: dict) -> list[tuple]:
    """Rut gon co `nghi_ao_giac` cua tung doan thanh `(ma, ly_do, so_lieu)` de
    log MA doan + con so — ⛔ KHONG log loi thoai (`chu`).

    🔑 B13 B1: ⛔ KHONG doc thang `["ky_tu_moi_giay"]` — tin hieu THU BA (vong
       lai prompt, `ly_do == "vong_lai_initial_prompt"`) khong mang khoa do,
       chi mang `khop_ky_tu`. Doc bang `.get()` de mot ly_do moi khong lam
       KeyError ca lan chay.
    """
    ra = []
    for d in ban.get("doan") or []:
        co = d.get("nghi_ao_giac")
        if not co:
            continue
        so_lieu = co.get("ky_tu_moi_giay", co.get("khop_ky_tu"))
        ra.append((d.get("ma"), co.get("ly_do"), so_lieu))
    return ra


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
        # 🔴 **MOT cua duy nhat de lay mot artifact ve dia.** Truoc 27/09 cho nay
        #    tu viet lai nhanh do bang `Path(duong).write_bytes(f.read())` — dung
        #    khuon ma `_duong_doc_duoc` ton tai de khong lam (xem chu thich cua no
        #    va `test_429`). Va nhanh do la nhanh DUY NHAT production di qua:
        #    `LocalStorage` co `local_path` nen moi test cuc bo tra duong that,
        #    con `R2Storage` **khong ghi de** `Storage.local_path` (luon `None`)
        #    ⇒ 100 % luot that nap ca `audio_full.wav` vao RAM worker. PCM 16 kHz
        #    mono = 32 kB/s, nen mot phim 2 gio (tran chinh sach) la 230 MB.
        duong = _duong_doc_duoc(kho, khoa_tieng, thu_muc)

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5, _t('Đang chép lời'))

        from . import cai_dat as cd, ngon_ngu as nn, nguon_loi as nl
        cai = cd.doc(run)
        khai = nn.chuan_nguon(cai.ngon_ngu_nguon)
        tt = nhap_media.soi(duong)

        # ⛔ **KHONG con dinh tuyen** (Task 21, 26/09): MOT duong duy nhat
        #    voice->voice. `dinh_tuyen` o day chi con la BAN GHI NGUON GOC — no
        #    giu dung hinh dang cu (`che_do`/`nguon_loi`/`ly_do`/`cat_lai`) vi
        #    `quan_sat.bang_chung_chat_luong` va cac ban ghi da luu doc no.
        dinh_tuyen: dict = {"che_do": nl.ASR, "nguon_loi": nl.ASR, "ly_do": []}
        tho = chep_loi(duong, ngon_ngu="" if khai == nn.TU_DOAN else khai,
                       ctx=ctx)

        # 🔑 **CAT LAI theo CAU.** WhisperX tra ve ca khoi VAD ~30 giay lam MOT
        #    doan tren van Han (Punkt khong co mo hinh `zh` — xem `cat_doan.py`),
        #    va mot khe 24 giay thi `timing_align` khong con gi de canh.
        #
        # ⭐ Truoc 26/09 buoc nay bi RAO lai cho rieng duong ASR, vi `embedded`/
        #    `ocr` cho ban chu do NGUOI lam phim chia san. Hai duong do da bo ⇒
        #    rao khong con gi de rao, va giu no lai la giu mot nhanh khong bao gio
        #    chay.
        from . import cat_doan
        tho, chan_cat = cat_doan.cat_lai(
            tho, ngon_ngu=str(tho.get("language") or khai or ""))
        dinh_tuyen["cat_lai"] = chan_cat

        ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=tt["thoi_luong"],
                                nguon_loi=dinh_tuyen["nguon_loi"],
                                dinh_tuyen=dinh_tuyen)

        # 🔴 N-39: ao giac ASR (credit phu de cuoi tep — kieu hong DA BIET cua
        #    Whisper tieng Trung). Gan co bang HAI tin hieu cau truc, ⛔ KHONG
        #    xoa. ⭐ Va no phai NOI LEN: mot con so nam im trong JSON thi bang
        #    khong co. Log MA doan + hai con so — ⛔ KHONG log loi thoai.
        if (n_ao := ban_ghi.danh_dau_nghi_ao_giac(ban)):
            log.warning(
                "asv_chep_loi nghi AO GIAC ASR: %d doan | %s", n_ao,
                _canh_bao_ao_giac(ban))

        # 🔴 B13 B2 (28/09): CUA doc `phu_song` — con so DA CO SAN trong
        #    `ban_ghi.tom_tat()` (78 doan, `211,56/275,04 = 76,9 %` o luot that
        #    da do) ma truoc gio chua ai doc. CUA A (tong) + CUA B (mot lo hong
        #    don le) doc lap — xem `ban_ghi.do_phu_song`. ⛔ Chi canh bao van
        #    hanh, KHONG chan luot: mot phim that su it loi la hop le.
        phu = ban_ghi.do_phu_song(ban, thoi_luong=tt["thoi_luong"])
        if phu["canh_bao_ty_le"] or phu["canh_bao_lo_hong"]:
            log.warning(
                "asv_chep_loi canh bao PHU SONG: ty_le=%.3f (nguong %.2f) | "
                "lo_hong_lon_nhat=%.1fs (nguong %.1fs, %d lo qua nguong)",
                phu["ty_le_phu_song"], phu["nguong_ty_le"],
                phu["lo_hong_lon_nhat_s"], phu["nguong_lo_hong_s"],
                phu["so_lo_hong_qua_nguong"])

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
            phien_ban_ma=PHIEN_BAN_MA,
            nguon_loi=f"{nl.ASR}:{dinh_tuyen['nguon_loi']}:{ban.get('engine', '')}")

        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TRANSCRIBE, van_tay=vt,
                                   duoi="json")
        kho.put(khoa, io.BytesIO(goi), content_type="application/json")

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(95, _t('Đang lưu kết quả'))

        return {
            "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                      "van_tay": vt}],
            "tom_tat": {**ban_ghi.tom_tat(ban),
                        # Ly do dinh tuyen (ma, khong chu thoai) cho van hanh.
                        # ⭐ `cat_lai` di kem: mot `so_doan` dep ma khong noi
                        #    **bao nhieu doan KHONG cat duoc** la mot con so da
                        #    giau san phan xau cua chinh no.
                        "dinh_tuyen": {k: dinh_tuyen.get(k) for k in
                                       ("che_do", "nguon_loi", "ly_do", "cat_lai")
                                       if dinh_tuyen.get(k) is not None},
                        # B13 B2: hai CUA doc lap tren `phu_song` — xem
                        # `ban_ghi.do_phu_song` cho can cu nguong.
                        "phu_song_kiem": phu},
        }
