"""Bo chuyen doi sinh tieng noi: mot doan van ban -> mot tep tieng.

## Vi sao goi DICH VU cua `ltt_voice` chu khong uy quyen mot job

ADR-001 D5 du dinh uy quyen mot job `ltt_voice.synthesize`. Trace hop dong that
o pha 12 cho thay uy quyen **khong lam duoc viec o day**, va ly do khac voi ly
do cua CONTENT:

  * `ltt_voice.synthesize` sinh ra **MOT tep** cho **MOT yeu cau**, va ghi no vao
    `voice/out/{owner}/{job_id}/tieng.wav` — khoa dua tren `ctx.job_id`.
  * Auto Scan can **mot tep cho MOI DOAN**, vi TIMING dat tung doan vao dung khe
    thoi gian cua no. Goi N lan voi cung mot `ctx` thi ca N lan ghi de len cung
    mot khoa.
  * Va Prompt 12 muc 7 doi **phuc hoi o muc tung doan**: chay lai chi duoc sinh
    lai nhung doan con thieu. Mot job cho ca ban dich khong co hat nao nho hon
    de checkpoint.

⇒ Ta goi **ba ham dich vu** cua `ltt_voice` va tu so huu tep, khoa, lineage va
  checkpoint. Be mat da khai o ca hai phia.

## Ba ham do, va vi sao khong the bo ham nao

    chuan_hoa()    doc tham so -> `YeuCau` da kiem
    giai_giong()   **NOI DUY NHAT quyen so hu duoc kiem** — bat buoc di qua
    goi_cong()     mot luot sinh -> (wav_bytes, headers)

🔴 `giai_giong` la cho duy nhat kiem mot `voice_id` co thuoc ve nguoi goi khong
   (chinh docstring cua no noi vay). Di vong qua no de "goi cho nhanh" la mo mot
   duong dung giong cua nguoi khac — dung bat bien I6/I7 ma pha 07 vua dong.

## Ban va hai dieu KHONG duoc dung toi

⛔ `temperature`/`top_k`/`top_p` KHONG ra hop dong cong khai cua `ltt_voice`:
   cache CUDA graph cua no khoa theo `(B, temp, top_k, top_p)` (CLAUDE.md). Truyen
   chung vao la lam vo cache cua mot app khac.

⛔ Tran 1.500 ky tu moi luot la **tran CHAT LUONG**, khong phai tran ky thuat —
   #168 bao troi giong tu ~3.000. Do la quyet dinh cua `ltt_voice`, va cho nay
   ton trong no bang cach TU CHOI mot doan qua dai thay vi lang le chia nho:
   chia mot cau thoai thanh hai luot sinh la doi mot doan thanh hai giong doc
   khac nhau o giua cau.
"""
from __future__ import annotations

import hashlib
import json
import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

#: Doi khi doi cach goi engine. Vao van tay (O13).
PHIEN_BAN_GIONG = 1


class GiongError(RuntimeError):
    """Sinh tieng that bai theo cach KHONG mo ho — thu lai duoc."""


class GiongMoHo(RuntimeError):
    """Da co the goi toi may sinh tieng roi mat ket noi.

    ⛔ Khong bao gio thu lai tu dong (I5/G7). May co the da sinh xong va da tinh
       tien; thu lai la tra tien hai lan cho mot doan.
    """


class MayBan(RuntimeError):
    """May sinh tieng dang ban. **BAN KHONG PHAI HONG.**

    🔴 `apps/ltt_voice/features.py:219` ghi thang bai hoc nay: boc `DangBanTam`
       thanh mot loi hong la bien "may dang ban" thanh "job hong", va mot job
       hong se **TRU CREDIT cho viec chua tung chay**.

    Tang tren phai xep lai, khong duoc tinh la that bai.
    """


def san_sang() -> bool:
    """May sinh tieng da duoc thiet lap tren may nay chua."""
    try:
        from apps.ltt_voice import sidecar_client
        return bool(sidecar_client.san_sang())
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        # ⛔ Ghi log chu khong nuot. "Chua cai" va "da cai nhung dang hong" tra
        #    ve CUNG mot `False` o day, va hai thu do doi hoi hai hanh dong khac
        #    han. Khong co dong log nay thi mot sidecar chet chi hien ra thanh
        #    "may nay khong co LTT VOICE" — dung mot lan, sai mai ve sau.
        log.warning("khong hoi duoc sidecar LTT VOICE (%s: %s)",
                    type(exc).__name__, exc)
        return False


def tach_ma_giong(ma: str) -> tuple[str, str]:
    """Mot ma giong -> `(voice_id, preset)` cho hop dong cua `ltt_voice`.

    🔴 **Luat nay tung khong ton tai o dau ca, va hau qua la giai doan long
       tieng KHONG THE thanh cong tren duong that (A29-01).**

       `gia.giong_chon_duoc` tra ve mot danh sach PHANG `{ma, ten}` gom ca giong
       DUNG SAN cua `ltt_voice` lan giong RIENG khach da nhan ban — no khong
       danh dau cai nao la cai nao. Nen nguoi goi khong the biet dien o nao, va
       ban dau no dien het vao `voice_id`. Trong khi `Minh Duc` la mot giong
       dung san, tuc thuoc `preset`.

    ⛔ Va `ltt_voice.chuan_hoa` tu choi khi CA HAI o cung co gia tri — mot phep
       chan hoan toan dung, vi "giong cua ban" va "giong co san" la hai nguon
       khac nhau cho cung mot cau hoi.

    ⭐ Luat dat o DAY, khong o giai doan: day la tep duy nhat cua Auto Scan noi
       chuyen voi `ltt_voice`, va hai ban cua mot luat la hai ban se lech nhau.
       `giong_mau.hop_le` la mot ten DA KHAI trong `BE_MAT_CONG_KHAI`.
    """
    ma = str(ma or "").strip()
    if not ma:
        return "", ""
    try:
        from apps.ltt_voice.giong_mau import hop_le
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        log.warning("khong nap duoc catalog giong mau (%s)", type(exc).__name__)
        return ma, ""
    return ("", ma) if hop_le(ma) else (ma, "")


def giai_giong(db, *, owner_id: str, voice_id: str = "", preset: str = ""):
    """`(ref_b64, preset)` cho mot chu so huu. Nem neu giong khong phai cua ho.

    Goi dung mot lan cho ca lan chay, roi dung lai cho moi doan: giai giong la
    mot phep tra CSDL, va lam lai no cho tung doan la N luot tra cho mot cau tra
    loi khong doi.

    ⭐ `voice_id` nhan duoc mot ma giong BAT KY — ke ca ten mot giong dung san —
       va `tach_ma_giong` dat no vao dung o. Nguoi goi khong phai biet luat do.
    """
    from apps.ltt_voice.features import chuan_hoa, giai_giong as _giai

    if voice_id and not preset:
        voice_id, preset = tach_ma_giong(voice_id)

    # `chuan_hoa` doi co `text`; o day ta chi giai giong, nen dua mot cho giu chan.
    yc = chuan_hoa({"text": ".", "voice_id": voice_id, "preset": preset,
                    "owner_id": owner_id})
    ref_b64, preset_ra, _canh_bao = _giai(db, yc)
    return ref_b64, preset_ra


def chuan_hoa_van_ban(chu: str, *, doc_so_tran: bool = False,
                      tu_dien_rieng: dict | None = None) -> str:
    """Chuan hoa van ban TRUOC khi doc. Bat buoc, khong phai tuy chon.

    🔴 **DAY LA MOT LO DA CO THAT TRONG BAN PHA 12.** Ban dau `doc_mot_doan`
       goi thang `goi_cong(chu)` voi **ban dich tho** cua model, bo qua hoan toan
       `text_pipeline.chuan_hoa`. Hau qua khong nho:

         `12/03/2024`  -> doc thanh mot chuoi ky tu, khong thanh ngay thang
         `https://...` -> doc tung chu cai
         `CPU`         -> doc tung chu cai thay vi "xi pi diu"
         ky tu vo hinh -> **token la (OOV)** cho tokenizer, phat am hong
         ten rieng     -> khong duoc tu dien sua

    ⭐ Va no lo ra vi mot phien khac canh bao ve mot phan NHO hon cua cung van
       de (`tu_dien_rieng` moi them). Phan lon lo nay da hong tu truoc do.

    ⛔ Dung `text_pipeline.chuan_hoa`, **khong** dung `features.chuan_bi_van_ban`:
       ham do vua chuan hoa **vua chia doan**, va chia mot cau thoai thanh hai
       luot sinh la doi no thanh hai giong doc khac nhau o giua cau (D-12-03).
       Ta chi lay phan chuan hoa.
    """
    from apps.ltt_voice import text_pipeline

    return text_pipeline.chuan_hoa(str(chu or ""), doc_so_tran=doc_so_tran,
                                   tu_dien_rieng=tu_dien_rieng)


def doc_mot_doan(chu: str, *, ref_b64=None, preset=None,
                 doc_so_tran: bool = False,
                 tu_dien_rieng: dict | None = None) -> tuple[bytes, dict]:
    """Mot doan -> `(wav_bytes, headers)`. Phan loai loi truoc khi nem len.

    Ba loai ket cuc, va gop chung lai la mat dung thu can de xu ly:
      `MayBan`    -> xep lai, khong tinh la that bai, khong tru credit
      `GiongMoHo` -> KHONG BAO GIO thu lai
      `GiongError`-> thu lai duoc
    """
    from apps.ltt_voice import features as vf
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH

    chu = str(chu or "").strip()
    if not chu:
        raise GiongError(_t('Đoạn rỗng, không có gì để đọc.'))

    # ⚠️ Chuan hoa TRUOC khi do do dai. Chuan hoa co the lam van ban DAI RA
    #    ("CPU" -> "xi pi diu", "2024" -> "hai nghin khong tram hai muoi bon"),
    #    nen do truoc rồi chuan hoa sau la do nhầm cái sẽ không được đọc.
    chu = chuan_hoa_van_ban(chu, doc_so_tran=doc_so_tran,
                            tu_dien_rieng=tu_dien_rieng).strip()
    if not chu:
        raise GiongError(_t('Đoạn rỗng, không có gì để đọc.'))
    if len(chu) > TRAN_MOI_LUOT_SINH:
        # ⛔ KHONG tu chia nho. Chia mot cau thoai thanh hai luot sinh la doi
        #    mot doan thanh hai giong doc khac nhau o giua cau.
        raise GiongError(
            _t('Đoạn dài {co} ký tự, vượt trần {tran} của một lượt đọc.').format(
                co=len(chu), tran=TRAN_MOI_LUOT_SINH))

    try:
        return vf.goi_cong(chu, ref_b64=ref_b64, preset=preset)
    except vf.DangBanTam as exc:
        raise MayBan(str(exc)) from exc
    except Exception as exc:      # noqa: BLE001 - phan loai roi nem lai
        ten = type(exc).__name__
        if "Ambiguous" in ten or "Timeout" in ten:
            raise GiongMoHo(f"{ten}: {exc}") from exc
        raise GiongError(str(exc)) from exc


def van_tay_doan(*, ma_doan: str, chu: str, voice_id: str, preset: str) -> str:
    """Van tay cua MOT doan tieng (Prompt 12 muc 6).

    O muc DOAN chu khong o muc giai doan — do la thu cho phep sinh lai dung
    nhung doan con thieu (muc 7). Bon thanh phan:
      `ma_doan`  vi tri trong ban ghi
      `chu`      **noi dung**: sua mot chu la doi tep tieng
      `voice_id` / `preset`  doi giong la doi san pham
    """
    goi = json.dumps({
        "ma": ma_doan,
        "chu": chu,
        "voice_id": voice_id,
        "preset": preset,
        "phien_ban": PHIEN_BAN_GIONG,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def kiem_tep_tieng(duong: str, *, toi_thieu_giay: float = 0.05) -> float:
    """Kiem tep tieng THAT bang ffprobe. Tra ve thoi luong. Nem neu khong dat.

    ⛔ Prompt 12 muc 8: kiem TRUOC khi danh dau doan thanh cong. Mot tep WAV
       dung dinh dang nhung dai 0 giay se qua moi phep kiem ve dinh dang, roi
       TIMING dat mot khoang im vao dung cho do — va khong ai biet vi sao.
    """
    from . import nhap_media

    tt = nhap_media.soi(duong)
    if not tt.get("co_tieng"):
        raise GiongError(_t('Tệp tiếng sinh ra không có luồng tiếng.'))
    giay = float(tt.get("thoi_luong") or 0.0)
    if giay < toi_thieu_giay:
        raise GiongError(_t('Tệp tiếng sinh ra quá ngắn ({giay}s).').format(
            giay=round(giay, 3)))
    return giay
