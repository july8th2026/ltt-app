"""probe_anh_spec.py -- loi llama.cpp #28715 co cat vao ho so gop cua ta khong.

## Cau hoi

b10906 mang mot ban va ten "server: fix speculation after an image": truoc no,
server truyen **so token** thay vi **vi tri** cho bo nhap sau khi xu ly mot anh,
lam suy doan tut hieu qua -- IM LANG, khong loi, khong canh bao. Bao cao goc:
DFlash2 152 -> 51 tok/s, ti le chap nhan 0,35 -> 0,02.

May B dang chay **b10883**, tuc TRUOC ban va. Va ho so LTT-3.8 sau khi gop
(L-14) la text + vision **trong cung mot ho so**, chay `draft-mtp`. Tuc dung
to hop ma ban va noi toi: mot luot text di SAU mot luot anh trong cung slot.

## Vi sao phai do chu khong doc bao cao roi tin

Con so 152 -> 51 do tren ROCm voi DFlash2. Kien truc khac, bo nhap khac, card
khac. "Loi ton tai trong ma" khong dong nghia "loi nay lam CHAM may cua ta bao
nhieu" -- va cau thu hai moi la cau quyet dinh co nang cap ngay hay khong.

## Bai do

Cung mot server, `-np 1` de khong con may rui ve slot nao phuc vu luot nao:

    A (doi chung)  : N luot text lien tiep, KHONG anh truoc do.
    B (bai that)   : mot luot co ANH, roi N luot text y het bai A.

Do cho ca hai: tok/s giai ma, va **delta** `spec_decode_num_accepted_tokens`
tren moi token sinh ra -- con so thu hai moi la thu #28715 noi toi. Neu B tut
so voi A thi loi cat vao ta, va muc tut chinh la gia cua viec KHONG nang cap.

Chay: python probe_anh_spec.py --cong 8290 --lan 4 --ra <duong dan>.jsonl
"""
import argparse
import importlib.util
import json
import os
import pathlib
import time

_HERE = pathlib.Path(__file__).resolve().parent


def _nap_bench():
    """Dung lai `bench.py` canh ben: cung cach goi, cung cach doc /metrics.

    Viet lai mot ban sao o day thi hai tep se troi khoi nhau, va luc do khong
    ai biet con so cua probe va con so cua bench co so sanh duoc voi nhau khong.
    """
    spec = importlib.util.spec_from_file_location("bench_probe", _HERE / "bench.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _spec_tong(m, base):
    so = m.so_metrics(base)
    return sum(v for k, v in so.items()
               if "spec_decode_num_accepted" in k and "{" not in k)


def _mot_bai(m, base, lan, co_anh):
    """Tra ve (tok_s trung binh, token sinh, delta spec) cua `lan` luot text."""
    if co_anh:
        noi = [{"type": "text", "text": "Mo ta ngan buc anh nay."},
               {"type": "image_url", "image_url": {"url": m.anh_data_url()}}]
        m.chat_mot_cuc(base, "x", noi, 128, temperature=0.2, timeout=300.0)

    truoc = _spec_tong(m, base)
    tong_tok, tong_giay, tung_luot = 0, 0.0, []
    for _ in range(lan):
        # Prompt GIONG HET nhau giua A va B: chi khac dung mot thu -- truoc do
        # co mot luot anh hay khong.
        nhac = m.PROMPT_HUONG_DAN + m.nonce() + m.sinh_prompt(600)
        r = m.chat_mot_cuc(base, "x", nhac, 300, timeout=300.0)
        n = int((r["usage"] or {}).get("completion_tokens") or 0)
        t = float((r["timings"] or {}).get("predicted_ms") or 0.0) / 1000.0
        if t <= 0:
            t = r["wall"]
        tong_tok += n
        tong_giay += t
        tung_luot.append({"token_ra": n, "giay": round(t, 3),
                          "tok_s": round(n / t, 2) if t else None})
    sau = _spec_tong(m, base)
    return {
        "co_anh_truoc": co_anh,
        "so_luot": lan,
        "token_ra_tong": tong_tok,
        "giay_tong": round(tong_giay, 3),
        "tok_s": round(tong_tok / tong_giay, 2) if tong_giay else None,
        "spec_accepted_delta": sau - truoc,
        # Con so SO SANH DUOC giua hai bai: so token nhap duoc chap nhan tren
        # moi token that su sinh ra. Tong tho khong so duoc vi hai bai co the
        # sinh ra so token khac nhau.
        "spec_tren_token": round((sau - truoc) / tong_tok, 4) if tong_tok else None,
        "tung_luot": tung_luot,
    }


def main():
    ap = argparse.ArgumentParser(description="Do anh huong cua llama.cpp #28715")
    ap.add_argument("--cong", type=int, default=8290)
    ap.add_argument("--lan", type=int, default=4)
    ap.add_argument("--ra", required=True)
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.cong
    m = _nap_bench()

    thu_muc = os.path.dirname(os.path.abspath(args.ra))
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)

    ket = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "cong": args.cong}
    # Lam A truoc, roi B. Neu doi thu tu thi anh cua B con nam trong prompt
    # cache khi A chay, va A khong con la doi chung sach.
    ket["A_khong_anh"] = _mot_bai(m, base, args.lan, False)
    ket["B_sau_anh"] = _mot_bai(m, base, args.lan, True)

    a, b = ket["A_khong_anh"], ket["B_sau_anh"]
    if a["tok_s"] and b["tok_s"]:
        ket["ti_le_tok_s_B_tren_A"] = round(b["tok_s"] / a["tok_s"], 4)
    if a["spec_tren_token"]:
        ket["ti_le_spec_B_tren_A"] = round(
            (b["spec_tren_token"] or 0) / a["spec_tren_token"], 4)

    with open(args.ra, "a", encoding="utf-8") as f:
        f.write(json.dumps(ket, ensure_ascii=True) + "\n")
    print(json.dumps(ket, ensure_ascii=True))


if __name__ == "__main__":
    main()
