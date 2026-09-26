"""MOT duong duy nhat cho loi thoai goc: **voice -> voice** (`nguon_loi=asr`).

    tieng noi trong video  -> whisper nghe chep  -> text   nguon_loi=asr

⛔ Khong con duong nao khac, nen khong con gi de **chon**: tep nay khong dinh
tuyen, no chi (1) ghi ten duong duy nhat, (2) nhan mot ho so cu mang ten duong
DA BO va quy no ve `asr`, (3) giu bo doc SRT duy nhat cua app (`doc_srt`).

## 🔑 Vi sao ba duong kia bi BO — quyet dinh 26/09, va LY DO de khong them lai

Truoc 26/09 tep nay dinh tuyen bon che do: `embedded` (luong text trong
container), `ocr` (RapidOCR doc chu Han dot vao hinh), `asr`, va `auto` (thu ba
duong theo thu tu). Chu du an chot bo CA BA, giu `asr`:

  *"He thong cua ta chi di theo dung 1 duong la voice to voice, ⛔ khong doc chu
  tren video de thanh text roi dich. Ban chat ⛔ khong phai video nao cung co
  sub, co che doc theo sub rat de bi chong cheo va nhieu van de phat sinh."*

Ra thanh ba menh de KIEM DUOC — ai muon them lai mot nguon chu thu hai phai bac
duoc **ca ba**:

  1. **Nguon sub ⛔ khong pho quat.** Mot duong chi chay tren MOT PHAN vat lieu
     thi no khong the la duong chinh; no la mot nhanh, va moi nhanh phai duoc
     CHON — chinh viec chon la cho sinh loi. Do B0: ca 4 phim mau co hardsub Han
     98,8-100 % ⇒ voi `auto` thi **ca bon** di duong `ocr` ma khong ai dinh, tuc
     duong `asr` — **luong CHINH** — chua tung chay that mot lan nao, va moi con
     so cua ba luot nghiem thu 24/09 deu noi ve duong PHU.
  2. **Hai nguon chu cho cung mot doan = hai cho khai mot dieu.** Hardsub va ASR
     cho hai ban chu KHAC nhau cho cung mot giay phim, kem hai truc thoi gian
     khac nhau, va ⛔ khong ai bat khop.
  3. **Mot duong ⇒ mot cho de soi khi hong.** Ba duong nghia la mot trieu chung
     co ba nguyen nhan kha di. Cai gia nay ⛔ khong hien ra trong bat ky phep do
     hieu nang nao, nhung no dat nhat khi co khach that.

⭐ Bang chung cua duong da bo ⛔ KHONG bi xoa: `docs/auto_scan_video_final/
   L_OCR.md` (benchmark OCR) va `l_ocr_gt_v2*.json` (chan ly nen phan doan cua
   cong B1) giu nguyen, dan nhan la bang chung lich su. Xoa bang chung la xoa kha
   nang kiem lai chinh quyet dinh nay.

## ⛔ Ranh gioi de xoa lan: VI TRI dai chu la viec GIU

Do **vi tri** dai chu goc (tinh nang *lam mo sub goc*) song o `do_vung.py`, chay
OpenCV, ⛔ khong goi RapidOCR va ⛔ khong doc mot chu nao. Doc **CHU** la viec da
bo. Hai thu nay khac nhau, va `do_vung.py` ⛔ khong bi cham o lan don 26/09.
"""
from __future__ import annotations

import logging
import re

from platform_core.i18n import N_

log = logging.getLogger(__name__)

#: Duong DUY NHAT. Ten nay con song vi no la **provenance** ghi trong ban ghi
#: (`ban_ghi.chuan_hoa(nguon_loi=...)`), khong phai mot lua chon.
ASR = "asr"

#: ⭐ MOT che do hop le. Doc no chu dung go `"asr"` vao cho khac.
CHE_DO_HOP_LE = (ASR,)
CHE_DO_MAC_DINH = ASR

#: 🔑 Ten cua ba duong DA BO (26/09). ⛔ Giu danh sach nay **khong** phai de mot
#:    ngay nao bat lai chung — no chi ton tai de `chuan_che_do` PHAN BIET duoc
#:    "mot ho so cu mang ten duong da bo" (⇒ ghi mot dong log, di tiep) voi
#:    "mot gia tri vo nghia" (⇒ im lang di tiep). Hai tinh huong khac loai, va
#:    gop chung thanh mot lam ta mat kha nang dem xem con bao nhieu ho so cu.
CHE_DO_DA_BO = frozenset({"auto", "embedded", "ocr"})


def chuan_che_do(gia_tri) -> str:
    """Bat ky gia tri nao -> `asr`. ⛔ KHONG BAO GIO nem.

    🔴 **Ham nay ton tai VI ho so da luu cua khach.** Do 26/09: ca 8 lan chay
       trong CSDL production deu `nguon_loi='asr'`, nhung **ho so** (`cai_dat`)
       thi chua do duoc — mot ho so con mang `"ocr"`/`"embedded"`/`"auto"` phai
       doc ra `asr` va ⛔ khong duoc lam khach gap loi khi mo lai trang vi mot
       che do ta vua bo.
    """
    v = str(gia_tri or "").strip().lower()
    if v in CHE_DO_DA_BO:
        log.info("asv nguon_loi: ho so cu mang che do DA BO %r -> quy ve %r "
                 "(mot duong duy nhat voice->voice, 26/09)", v, ASR)
    return ASR


#: Nhan cho nguon THAT da dung, hien o man mot lan chay.
#:
#: ⛔ Nhan noi **viec gi xay ra**, khong noi ten ky thuat: khach khong biet "ASR"
#:    la gi, nhung ho biet "nghe roi chep". Cung luat voi `routes.NHAN_GIAI_DOAN`.
#:
#: ⚠️ Mot ma NGOAI bang (vd. `ocr` trong ban ghi cua mot lan chay cu, neu co)
#:    duoc `quan_sat` in nguyen ma — ⛔ khong ai bia mot nhan tieng Viet cho mot
#:    duong khong con ton tai.
NHAN_NGUON_THAT = {
    ASR: N_("Nghe tiếng rồi chép lại"),
}

_MOC = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def _giay(g) -> float:
    h, mi, s, ms = g
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def doc_srt(van_ban: str) -> list[dict]:
    """SRT -> segments `{start,end,text,words,confidence}`. Bo the dinh dang.

    ⭐ Bo doc SRT **duy nhat** cua app — `assets.py` goi no de kiem mot tep phu
       de khach tai len co doc duoc khong.
    """
    ra = []
    for khoi in re.split(r"\r?\n\s*\r?\n", van_ban.strip()):
        dong = [d for d in khoi.splitlines() if d.strip()]
        for i, d in enumerate(dong):
            moc = _MOC.findall(d)
            if "-->" in d and len(moc) == 2:
                a, b = _giay(moc[0]), _giay(moc[1])
                chu = " ".join(dong[i + 1:])
                chu = re.sub(r"<[^>]+>|\{[^}]*\}", "", chu).strip()
                if chu and b > a:
                    ra.append({"start": a, "end": b, "text": chu, "words": [],
                               "confidence": 1.0})
                break
    return ra
