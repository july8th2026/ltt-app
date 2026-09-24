"""D5/B — doc DUONG CONG toc do: tran that la cho duong cong GAY.

⭐ **CACH DOC VIET TRUOC KHI DO** (25/09). Commit nay di TRUOC lo am thanh dau
   tien — tra `git log` de doi chung. ⛔ Viet sau khi thay so la chinh tren bai thi.

## Vi sao do bang MAY chu khong bang TAI

Dieu phoi ⛔ **khong nghe duoc am thanh** (L4 cham VAN BAN). ⇒ Dung dung nep
`tools/do_bai_dai.py` da dung de cham chat luong sinh:

    de nghe hieu  ->  VONG ASR: sinh o toc do X -> chep loi lai -> CER so van goc
    chat luong    ->  DNSMOS (qc-venv)

⚠️ **GIOI HAN PHAI KHAI:** ASR do **DE NGHE HIEU**, ⛔ khong do **DE CHIU**. Mot
   giong nhanh co the **hieu duoc** ma **kho nghe**. DNSMOS do phan do mot phan,
   ⛔ nhung ⛔ KHONG thay duoc tai nguoi.
   ⇒ ⛔ **Dung doc ket qua thanh "da xac nhan 1,35 nghe on"**. Cau dung duoc la
     *"o 1,35, do nghe hieu va diem chat luong may cham ⛔ chua gay"*.

## NGUONG "GAY" — ⛔ khong muon mot hang so nao

🔴 Mot nguong kieu *"CER tang qua 0,02"* hay *"DNSMOS tut qua 0,3"* la mot **so
   muon** — dung ho `N-34` da mac **bon lan** trong phien nay. ⇒ O day nguong
   **tu hieu chuan tren chinh DOI CHUNG**:

    do tan cua doi chung = IQR (tu phan vi) cua chinh muc 1,00 tren 12 cau
    GAY o muc X  <=>  (1) trung vi cua hieu THEO CAP  vuot  do tan ay
                 VA   (2) da so cau cung xau di  (phep dau, >= 2/3)

⭐ Hai dieu kien, va ly do tung cai:
   * (1) mot mình: mot cau ngoai le du keo trung vi;
   * (2) mot mình: 12 cau cung xau di **mot chut** ⛔ chua phai gay.
   ⇒ Doi **CA HAI** dung nep "ba so canh nhau" cua `B2`.

## SO SANH THEO CAP, ⛔ khong so hai dam may

Cung **mot cau** duoc sinh o moi toc do ⇒ so `CER(X) - CER(1,00)` **tung cau**.
⛔ So trung vi cua hai tap doc lap la vut di thong tin ghep cap, va tren n=12 thi
   do la khac biet giua co ket luan va khong.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

DOI_CHUNG = 1.00


def _iqr(v: list[float]) -> float:
    if len(v) < 4:
        return 0.0
    s = sorted(v)
    return s[int(0.75 * len(s))] - s[int(0.25 * len(s))]


def doc(ket_qua: dict) -> dict:
    """`{toc_do: {ma_cau: {cer, dnsmos}}}` -> phan quyet tung muc.

    ⛔ Nem `KeyError` neu thieu muc doi chung `1,00`: ⛔ khong co doi chung thi
       ⛔ khong co gi de goi la "gay".
    """
    muc = {float(k): v for k, v in ket_qua["theo_toc_do"].items()}
    if DOI_CHUNG not in muc:
        raise KeyError("thieu muc DOI CHUNG 1,00 — khong co no thi khong doc duoc")
    goc = muc[DOI_CHUNG]
    cau_chung = sorted(set(goc))
    tan_cer = _iqr([goc[c]["cer"] for c in cau_chung])
    tan_mos = _iqr([goc[c]["dnsmos"] for c in cau_chung])

    ra: dict = {
        "n_cau": len(cau_chung),
        "do_tan_doi_chung": {"cer_iqr": round(tan_cer, 4),
                             "dnsmos_iqr": round(tan_mos, 4)},
        "muc": {}, "gay_tai": None,
    }
    for toc in sorted(muc):
        if toc == DOI_CHUNG:
            continue
        chung = [c for c in cau_chung if c in muc[toc]]
        d_cer = [muc[toc][c]["cer"] - goc[c]["cer"] for c in chung]
        d_mos = [muc[toc][c]["dnsmos"] - goc[c]["dnsmos"] for c in chung]
        xau_cer = sum(1 for x in d_cer if x > 0)
        xau_mos = sum(1 for x in d_mos if x < 0)
        gay_cer = st.median(d_cer) > tan_cer and xau_cer >= 2 * len(chung) / 3
        gay_mos = -st.median(d_mos) > tan_mos and xau_mos >= 2 * len(chung) / 3
        ra["muc"][toc] = {
            "n": len(chung),
            "cer_lech_trung_vi": round(st.median(d_cer), 4),
            "cer_so_cau_xau_di": f"{xau_cer}/{len(chung)}",
            "dnsmos_lech_trung_vi": round(st.median(d_mos), 4),
            "dnsmos_so_cau_xau_di": f"{xau_mos}/{len(chung)}",
            "GAY_theo_cer": gay_cer, "GAY_theo_dnsmos": gay_mos,
            "GAY": gay_cer or gay_mos,
        }
        if (gay_cer or gay_mos) and ra["gay_tai"] is None:
            ra["gay_tai"] = toc
    # ⭐ Ca dang mong doi nhat, va no phai duoc NOI RA:
    m115 = ra["muc"].get(1.15)
    if m115 is not None and not m115["GAY"]:
        ra["ket_luan_ve_tran_hien_tai"] = (
            "1,15 ⛔ KHONG gay so voi 1,00 ⇒ tran hien tai (muon cua Subdub, N-45) "
            "CHAT VO CO tren giong cua ta")
    return ra


if __name__ == "__main__":
    print(json.dumps(doc(json.loads(pathlib.Path(sys.argv[1]).read_text(
        encoding="utf-8"))), ensure_ascii=False, indent=1))
