"""Hop dong BAN GHI chinh tac (TranscriptDocument) cua Auto Scan Video.

## Vi sao can mot hop dong rieng thay vi truyen thang ket qua cua engine

`apps/autosubvideo/transcription.py:162 transcribe_file` tra ve mot tu dien cua
**engine**: `{segments, language, engine, alignment_status, fallback_reason}`.
Do la hop dong cua mot cong cu, va no doi khi cong cu doi — whisperx va
faster-whisper da tra ve hai hinh dang hoi khac nhau ngay hom nay.

Bon giai doan ha nguon (CONTENT, VOICE, TIMING, COMPOSE) khong duoc phu thuoc
vao hinh dang do. Chung phu thuoc vao hop dong o day (O11).

## Ma doan (segment id) — vi sao la vi tri, va vi sao the la du

Ma co dang `seg_0001`. No **khong** bam theo noi dung, va do la mot lua chon
co y:

  * Ban ghi la mot artifact NGUYEN KHOI. No duoc tinh lai tron ven hoac khong
    tinh lai gi ca — van tay (§ `van_tay_ban_ghi`) quyet dinh dieu do.
  * Neu ban ghi duoc tinh lai va phep chia doan doi, thi moi thu ha nguon **phai**
    tinh lai theo — va no se, vi van tay cua ban ghi nam trong van tay cua chung
    (`thi_hanh._gom_dau_vao`). Mot ma bam theo noi dung se cho hai doan giong
    nhau o hai cho cung mot ma, va do la mot loi lineage tram hon.

⇒ Ma la **dinh danh trong mot ban ghi**, khong phai dinh danh toan cuc. Muc 4
  cua Prompt 10 doi "stable segment IDs": chung on dinh trong pham vi ma chung
  co nghia, va vuot ra ngoai pham vi do thi khong ma nao on dinh duoc.

## Ban thoi gian la BAT BUOC

Mot doan khong co `start`/`end` hop le se lam TIMING_ALIGN khong con gi de bam
vao, va loi se hien ra o cuoi day chuyen chu khong o day. Nen ban ghi bi **tu
choi** ngay khi dung, thay vi duoc luu roi lam vo mot giai doan xa hon.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: Phien ban HINH DANG cua ban ghi. Doi khi cau truc doi — di vao van tay, nen
#: mot lan doi lam moi ban ghi cu vo hieu thay vi bi doc bang luat moi.
SCHEMA_BAN_GHI = 1

# ⛔ Bang chung nguoi noi (pha 07: `phan_vai`/`nguoi_noi`) DA RUT 22/09
#    (asv-final): san pham la MOT giong thuyet minh, khong bo phan nao doc
#    nhan nguoi noi — phan vai chi ton GPU. Ban ghi cu con truong `phan_vai`
#    van hop le: `kiem()` khong doc no.

#: Sai so cho phep khi doi chieu moc thoi gian cua tu voi cua doan. Engine lam
#: tron o cho khac nhau, nen mot phep so bang tuyet doi se do vi lam tron.
SAI_SO_S = 0.05


class BanGhiError(ValueError):
    """Ban ghi khong dat hop dong."""


def _lam_sach(van_ban: str) -> str:
    return " ".join(str(van_ban or "").split())




def chuan_hoa(thoi: dict, *, thoi_luong_nguon: float = 0.0,
              nguon_loi: str = "asr", dinh_tuyen: dict | None = None) -> dict:
    """Ket qua tho cua engine -> ban ghi chinh tac. Nem `BanGhiError` neu khong dat.

    Bo doan RONG thay vi giu: mot doan khong co chu la mot doan khong co gi de
    dich va khong co gi de doc, nhung no VAN chiem mot khe thoi gian — va TIMING
    se chen mot khoang lang vao dung cho do.
    """
    doan_tho = list((thoi or {}).get("segments") or [])
    ra: list[dict] = []

    for tho in doan_tho:
        van_ban = _lam_sach(tho.get("text"))
        if not van_ban:
            continue
        try:
            bat, ket = float(tho.get("start")), float(tho.get("end"))
        except (TypeError, ValueError) as exc:
            raise BanGhiError(_t('Bản ghi có đoạn thiếu mốc thời gian.')) from exc
        if ket <= bat:
            raise BanGhiError(_t('Bản ghi có đoạn với mốc thời gian không hợp lệ.'))

        tu = []
        for t in (tho.get("words") or []):
            chu = _lam_sach(t.get("text"))
            if not chu:
                continue
            try:
                tb, tk = float(t.get("start")), float(t.get("end"))
            except (TypeError, ValueError):
                continue        # engine doi khi khong gan moc cho mot tu
            if tk < tb:
                continue
            tu.append({"bat": tb, "ket": tk, "chu": chu})

        doan = {"bat": bat, "ket": ket, "chu": van_ban, "tu": tu}
        # Provenance (22/09): do tin 0..1 cua NGUON (OCR: diem nhan dang trung
        # binh cac khung). ASR (faster-whisper qua autosubvideo) khong tra do
        # tin theo doan ⇒ vang mat, KHONG bia mot con so.
        if tho.get("confidence") is not None:
            doan["do_tin"] = round(float(tho["confidence"]), 4)
        ra.append(doan)

    if not ra:
        raise BanGhiError(_t('Không nghe được lời nói nào trong tệp.'))

    ra.sort(key=lambda d: (d["bat"], d["ket"]))
    for i, d in enumerate(ra, start=1):
        d["ma"] = f"seg_{i:04d}"

    ban = {
        "schema": SCHEMA_BAN_GHI,
        "ngon_ngu": str((thoi or {}).get("language") or ""),
        "engine": str((thoi or {}).get("engine") or ""),
        # ⭐ Giu lai NGUYEN VAN trang thai canh chinh cua engine. `whisperx` canh
        #    theo tung tu; faster-whisper thi khong, va no tu khai
        #    `fallback_unaligned`. Giau khac biet do la hua mot do chinh xac
        #    thoi gian ma ta khong co.
        "canh_chinh": str((thoi or {}).get("alignment_status") or ""),
        # 🔴 **VI SAO roi, khong chi ROI HAY KHONG.**
        #
        #    `transcription.py` phan biet duoc hai ca rat khac nhau:
        #      `whisperx_sidecar_unavailable`  -> **chua cau hinh** (moi truong)
        #      `<chuoi ngoai le>`              -> sidecar CO nhung **hong**
        #    ...roi ASV chi giu `canh_chinh` va **vut** `fallback_reason`.
        #
        # ⛔ Hai trang thai do ra **cung mot ban chep trong y het nhau**, nen nguoi
        #    doc `outputs` khong the biet nen di BAT SIDECAR hay di SUA no. Do that
        #    24/09: bench B1 thay `fallback_unaligned` va phai doc MA NGUON moi biet
        #    ly do — trong khi `apps/autosubvideo/jobs.py:154` da mang ca hai truong
        #    di tiep tu lau.
        "ly_do_roi": str((thoi or {}).get("fallback_reason") or ""),
        "thoi_luong_nguon": float(thoi_luong_nguon or 0.0),
        # 🔑 Nguon goc loi thoai: `embedded` | `ocr` | `asr` (`nguon_loi.py`).
        #    Ban ghi truoc 22/09 khong co khoa nay = `asr`.
        "nguon_loi": str(nguon_loi or "asr"),
        "doan": ra,
    }
    if dinh_tuyen:
        ban["dinh_tuyen"] = dinh_tuyen
    kiem(ban)
    return ban


def kiem(ban: dict) -> None:
    """Kiem mot ban ghi. Nem `BanGhiError` kem ly do cu the.

    Chay ca luc tao lan luc doc lai tu kho: mot artifact hop le luc ghi van co
    the bi sua sau do, va I8 noi DONE phai keo theo mot ket qua **con dung**.
    """
    if not isinstance(ban, dict):
        raise BanGhiError(_t('Bản ghi không đúng định dạng.'))
    if int(ban.get("schema") or 0) != SCHEMA_BAN_GHI:
        raise BanGhiError(_t('Bản ghi thuộc phiên bản cấu trúc khác.'))

    doan = ban.get("doan")
    if not isinstance(doan, list) or not doan:
        raise BanGhiError(_t('Bản ghi không có đoạn nào.'))

    ma_da_thay = set()
    truoc_ket = None
    for d in doan:
        ma = d.get("ma")
        if not ma or ma in ma_da_thay:
            raise BanGhiError(_t('Bản ghi có mã đoạn trùng hoặc thiếu.'))
        ma_da_thay.add(ma)

        bat, ket = float(d.get("bat", -1)), float(d.get("ket", -1))
        if bat < 0 or ket <= bat:
            raise BanGhiError(_t('Bản ghi có đoạn với mốc thời gian không hợp lệ.'))
        if truoc_ket is not None and bat + SAI_SO_S < truoc_ket:
            # ⛔ Doan chong len nhau la mot loi CHET NGUOI o ha nguon: TIMING se
            #    chen hai doan tieng vao cung mot khe, va ban long tieng se co
            #    hai giong noi de len nhau.
            raise BanGhiError(_t('Bản ghi có hai đoạn chồng thời gian lên nhau.'))
        truoc_ket = ket

        if not _lam_sach(d.get("chu")):
            raise BanGhiError(_t('Bản ghi có đoạn rỗng.'))

        for t in (d.get("tu") or []):
            tb, tk = float(t.get("bat", -1)), float(t.get("ket", -1))
            if tb < bat - SAI_SO_S or tk > ket + SAI_SO_S:
                raise BanGhiError(
                    _t('Bản ghi có từ nằm ngoài đoạn chứa nó.'))


def van_tay_ban_ghi(*, checksum_tieng: str, model: str, ngon_ngu: str,
                    phien_ban_ma: int, nguon_loi: str = "") -> str:
    """Van tay cua ban ghi (Prompt 10 muc 7).

    Bon thanh phan, va ly do tung cai:
      `checksum_tieng`  doi tieng vao       -> phai chep lai
      `model`           doi model ASR       -> ket qua khac han
      `ngon_ngu`        ep ngon ngu khac    -> ket qua khac han
      `phien_ban_ma`    doi cach chuan hoa  -> hinh dang khac
    """
    goi = json.dumps({
        "tieng": checksum_tieng,
        "model": model,
        "ngon_ngu": ngon_ngu,
        "schema": SCHEMA_BAN_GHI,
        "ma": int(phien_ban_ma),
        # `che_do:nguon:engine` — cung tieng, khac nguon loi = ban ghi khac.
        **({"nguon_loi": nguon_loi} if nguon_loi else {}),
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(ban: dict) -> dict:
    """Vai con so cho tien do va cho log. Khong co noi dung loi thoai.

    ⛔ Khong dua `chu` vao day: tom tat di vao `stage.outputs` va vao log, va
       loi thoai cua khach khong thuoc ve mot dong log.
    """
    doan = ban.get("doan") or []
    return {
        "so_doan": len(doan),
        "so_tu": sum(len(d.get("tu") or []) for d in doan),
        "ngon_ngu": ban.get("ngon_ngu", ""),
        "engine": ban.get("engine", ""),
        "canh_chinh": ban.get("canh_chinh", ""),
        # ⛔ Di theo `canh_chinh` len `outputs`: mot co "da roi" ma khong kem ly do
        #    bat nguoi doc di doc ma nguon.
        "ly_do_roi": ban.get("ly_do_roi", ""),
        "nguon_loi": ban.get("nguon_loi", "asr"),
        "phu_song": round(
            sum(float(d["ket"]) - float(d["bat"]) for d in doan), 2),
    }
