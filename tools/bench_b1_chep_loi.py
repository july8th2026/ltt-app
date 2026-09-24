"""bench_b1_chep_loi.py — cong B1: do NGHE CHEP (`transcribe`) vs hardsub.

    python tools/bench_b1_chep_loi.py --phim "<duong dan.mp4>"
    python tools/bench_b1_chep_loi.py --tu-kiem       # doi chung, khong can phim

## Mat xich DAU TIEN cua thang cong

Moi buoc sau dung tren van ban nguon ma `transcribe` tao ra. Mot loi o day khong
dung yen: no di vao ban dich, vao loi doc, vao QC ngu nghia, roi hien ra o mot chi
so khac han — va nguoi doc se di sua nham cho.

## ⚠️ CHAN LY NEN LA HARDSUB, VA NO KHONG HOAN HAO

Hardsub la **ban chu do nguoi lam phim viet**, khong phai ban ghi loi noi. Xem
`docs/auto_scan_video_final/B1_CHEP_LOI.md` §2 — gioi han do di kem MOI con so, ke
ca trong ban ghi JSON (`gioi_han`).

## ⛔ Nguong nam o TAI LIEU, ma chi doc lai

`NGUONG_WER`/`NGUONG_CER` phai khop `B1_CHEP_LOI.md` §1, va
`tests/test_3008::test_NGUONG_doc_tu_TAI_LIEU...` chot dieu do. Hai cho khai mot
con so ma khong ai bat khop la bay da ghi trong so may nay.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Nguong DAT cua cong B1. ⛔ Khop `B1_CHEP_LOI.md` §1 — dung sua mot ben.
NGUONG_WER = 0.25
NGUONG_CER = 0.12

#: Gioi han cua chan ly nen, di kem MOI ban ghi. ⛔ Khong rut gon cau nay: nguoi
#: trich so doc JSON, khong doc `.md`.
GIOI_HAN_CHAN_LY_NEN = (
    "Hardsub la BAN CHU do nguoi lam phim viet, khong phai ban ghi loi noi: no co "
    "the RUT GON loi noi (bo tu dem, gop cau), viet lai cho gon man hinh, hoac bo "
    "han doan khong quan trong. Moi nguyen nhan do day WER LEN. ⇒ WER THAP la bang "
    "chung manh; WER CAO la bang chung YEU va phai soi tay truoc khi quy cho engine."
)

#: Phim BI LOAI khoi bench, kem ly do. ⛔ Mot phim khong co tieng noi se cho mot con
#: so trong nhu that bai cua engine.
PHIM_LOAI = {
    "真人气枪游戏红蓝双方对决": "B0 ghi 'khong chac co giong' — khong do duoc "
                                "duong nghe chep tren mot phim khong co tieng noi.",
}

_DAU_CAU = re.compile(r"[^\w\s]", re.UNICODE)
_NHIEU_TRANG = re.compile(r"\s+")


def chuan_hoa(chu: str) -> str:
    """Bo HINH THUC, giu NOI DUNG.

    ⛔ Duoc bo: dau cau, khoang trang thua, khac biet NFC/NFKC, hoa/thuong.
    ⛔ KHONG duoc bo: chu. Mot ham chuan hoa qua tay (vi du bo het ky tu khong phai
       Han) keo WER xuong mot cach GIA TAO — va no trong y het mot engine tot.

    ⚠️ **Khong tu che phep tach tu tieng Trung.** Van ban Han khong co khoang trang,
       nen WER theo "tu" tren tieng Trung it nghia hon CER; ca hai deu duoc bao cao
       va CER moi la so dang tin o day. Mot bo tach tu tu che se tao ra mot don vi
       do khong ai kiem duoc.
    """
    v = unicodedata.normalize("NFKC", str(chu or "")).lower()
    v = _DAU_CAU.sub(" ", v)
    return _NHIEU_TRANG.sub(" ", v).strip()


def _ky_tu(chu: str) -> str:
    """Chuoi ky tu cho CER: bo ca khoang trang."""
    return chuan_hoa(chu).replace(" ", "")


def do_hai_ban(tham_chieu: str, doc_ra: str) -> dict:
    """WER + CER giua hai ban van. Dung `jiwer`, ⛔ khong tu go phep tinh Levenshtein."""
    import jiwer

    tc, dr = chuan_hoa(tham_chieu), chuan_hoa(doc_ra)
    if not tc:
        return {"wer": float("nan"), "cer": float("nan"), "trong": True}
    wer = float(jiwer.wer(tc, dr))
    cer = float(jiwer.cer(_ky_tu(tham_chieu), _ky_tu(doc_ra)))
    return {"wer": round(wer, 4), "cer": round(cer, 4), "trong": False}


def lam_hong(chu: str, *, ti_le: float = 0.3, seed: int = 0) -> str:
    """Lam hong `ti_le` so tu — DOI CHUNG cho chinh bo do.

    ⛔ Khong co phep nay thi mot WER thap co the chi la bo do hong, va no se IM LANG
       cho moi engine dat. Tat dinh theo `seed` de doi chung lap lai duoc.
    """
    tu = chuan_hoa(chu).split()
    if not tu:
        return ""
    r = random.Random(seed)
    so = max(1, int(len(tu) * ti_le))
    vi_tri = r.sample(range(len(tu)), min(so, len(tu)))
    for i in vi_tri:
        tu[i] = "x" + tu[i][::-1]
    return " ".join(tu)


def gop_ket_qua(*, wer: float, cer: float, so_dong_nguon: int,
                so_dong_hardsub: int, engine: str, co_card: bool,
                phim: str = "", ghi_chu: str = "") -> dict:
    """Ban ghi MOT phim. ⛔ Luon mang `gioi_han` va `chan_ly_nen`."""
    return {
        "phim": phim,
        "wer": wer, "cer": cer,
        "dat": bool(wer <= NGUONG_WER and cer <= NGUONG_CER),
        "nguong": {"wer": NGUONG_WER, "cer": NGUONG_CER},
        "so_dong_nguon": so_dong_nguon, "so_dong_hardsub": so_dong_hardsub,
        "engine": engine, "co_card": bool(co_card),
        # 🔑 HAI truong nay di theo con so, khong nam o cuoi bao cao.
        "chan_ly_nen": "hardsub",
        "gioi_han": GIOI_HAN_CHAN_LY_NEN,
        "ghi_chu": ghi_chu,
    }


def do_mot_phim(duong: str) -> dict:
    """Do WER/CER cua duong NGHE CHEP tren mot phim, lay hardsub lam doi chieu.

    ⚠️ **Chan ly nen la hardsub, va no co the RUT GON loi noi** — xem
       `GIOI_HAN_CHAN_LY_NEN`. Con so tra ve noi *"ASR va hardsub khac nhau bao
       nhieu"*, khong noi *"ASR sai bao nhieu"*; phep do nay **khong tach duoc**
       phan nao thuoc ve ai.

    Cach do: chay `transcribe` HAI lan tren cung mot phim —
    `nguon_loi=asr` (duong do) va `nguon_loi=ocr` (chan ly nen) — roi so.

    ⚠️ CHUA NOI vao khuon `chay_mot_buoc`: xem `B1_CHEP_LOI.md` §4. Ham nay hien
       tra ve mot ban ghi RONG kem `ly_do`, ⛔ khong tra ve mot con so gia.
    """
    ten = Path(duong).stem
    for xau, vi_sao in PHIM_LOAI.items():
        if xau in ten:
            return {"phim": ten, "bo_qua": True, "ly_do": vi_sao}
    return {"phim": ten, "chua_do": True,
            "ly_do": "buoc 4 cua Task 6 chua chay — xem B1_CHEP_LOI.md §4",
            "gioi_han": GIOI_HAN_CHAN_LY_NEN, "chan_ly_nen": "hardsub"}


def _tu_kiem() -> int:
    """Doi chung khong can phim: ban chep hong phai lam WER vot len."""
    that = "今天 我们 来 做 烤 牛肠 非常 好吃 大家 一起 来 看 看 吧"
    tot = do_hai_ban(that, that)
    hong = do_hai_ban(that, lam_hong(that, ti_le=0.3, seed=7))
    print(json.dumps({"giong_het": tot, "lam_hong_30pt": hong,
                      "nguong": {"wer": NGUONG_WER, "cer": NGUONG_CER}},
                     ensure_ascii=False, indent=1))
    ok = tot["wer"] == 0.0 and hong["wer"] > 0.15
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phim", default="")
    ap.add_argument("--tu-kiem", action="store_true")
    a = ap.parse_args(argv)
    if a.tu_kiem or not a.phim:
        return _tu_kiem()
    print(json.dumps(do_mot_phim(a.phim), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
