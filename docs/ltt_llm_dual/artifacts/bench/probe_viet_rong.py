"""probe_viet_rong.py -- vi sao LTT-3.5 tra RONG 6/6 luot voi cau hoi tieng Viet.

## Thu da do (12/09, cong G3 cham chat luong)

Ca HAI ung vien Q6_K, moi ung vien 3 luot cho `vi-01` va 3 luot cho `vi-02`:
**6/6 rong**, moi luot dot DUNG `max_tokens` = 1.400 trong 26,2-26,6 giay.
Cung luc do `en-01` xong trong 163-182 token / 3,2 giay.

Tuc: khong ngau nhien, khong phai nhieu lay mau, va khong phai "model kem" theo
nghia thong thuong -- no **khong bao gio dong khoi <think>** khi de bai la
tieng Viet. Hinh dang nay trung khop voi che do "runaway" da ghi cho model 3.8
(memory `model-nha-tra-ve-rong-khoang-mot-nua-luot`), nhung o 3.8 no xay ra
~1/2 luot con o day la **6/6**, va co mot bien ro rang: NGON NGU.

## Bon gia thuyet, va cach bai nay tach chung ra

    H1  Tran 1.400 qua thap: no VAN se dong khoi neu duoc nhieu token hon.
        => Bai `tran` chay lai chinh de do voi 4.000 va 8.000 token.

    H2  Do KHUON CHAT (chat template) mac dinh dat muc suy nghi qua cao.
        Ban 27B da phai thay khuon cong dong vi ly do y het: khuon chinh thuc
        "hardcode xhigh nen dot het ngan sach token vao reasoning"
        (chu thich trong llama-swap.yaml). Voi 3.5 ta dang dung khuon DUNG
        SAN trong GGUF, chua ai soi.
        => Bai `effort` gui `reasoning_effort` low/medium/high.

    H3  Do tieng Viet noi rieng, khong phai do de bai.
        => Bai `tai_hien` hoi cung mot dang cau bang tieng Viet va tieng Anh.

    H4  Do cach hoi (rang buoc "dung MOT tu") chu khong do ngon ngu.
        => Bai `tai_hien` co ca de "mot tu" lan de tinh toan, o hai thu tieng.

    H5  Do NHIET DO lay mau. `danh_gia_llm.py` KHONG truyen `temperature` nen
        dung mac dinh cua server; ban dau cua probe nay dat 0.2 va **khong tai
        hien duoc loi** (16/16 luot xong binh thuong).
        => Bai `tai_hien` chay moi de o CA HAI muc: mac dinh va 0.2.

⛔ Bai dau tien cua probe nay da HONG theo mot cach dang ghi lai: no tu viet lai
   de bai cho gon, bo mat rang buoc "Tra loi dung MOT tu, khong giai thich", roi
   bao "khong tai hien duoc". Viet lai de bai la doi ca bai toan. Muon dieu tra
   mot that bai thi phai TAI HIEN no truoc, bang dung dau vao da sinh ra no.

⛔ Bai nay KHONG ket luan nguyen nhan goc. No chi thu hep: sau khi chay, moi
   gia thuyet o tren hoac bi BAC bang mot con so, hoac con lai. Ghi nho cu da
   canh: `reasoning_effort` dich XAC SUAT chu khong CHAN duoc runaway o 3.8, va
   `reasoning_budget` gui per-request bi BO QUA -- neu ket qua o day trung voi
   dieu do thi ta biet minh dang gap cung mot con thu.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import time

_HERE = pathlib.Path(__file__).resolve().parent

# Hai de tieng Viet CHEP NGUYEN VAN tu `tools/danh_gia_llm.py` (bo de vi-01,
# vi-02, en-01). Ban dau cua probe nay TU VIET LAI de cho gon -- va no khong tai
# hien duoc loi: 16/16 luot deu xong binh thuong. Doi chieu lai moi thay ban tu
# viet da bo mat rang buoc "Tra loi dung MOT tu, khong giai thich".
# => Viet lai de bai la doi ca bai toan. Chep nguyen van, khong "lam gon".
DE = {
    "vi_1tu": "Tra loi dung MOT tu, khong giai thich: thu do cua Viet Nam la gi?",
    "en_1tu": ("Answer with exactly one word, no explanation: "
               "what is the capital city of Japan?"),
    "vi_tinh": ("Mot cua hang ban 3 mon gia 12.000d, 25.000d va 8.000d. "
                "Tong cong bao nhieu dong? Tra loi chi bang con so."),
    "en_tinh": ("A shop sells 3 items priced 12,000d, 25,000d and 8,000d. "
                "What is the total in dong? Answer with the number only."),
}


def _nap_bench():
    spec = importlib.util.spec_from_file_location("bench_viet", _HERE / "bench.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _goi(m, base, nhac, max_tokens, effort=None, nhiet=None):
    """Goi mot luot, tra ve do dai CA HAI truong + so token + ly do dung.

    Doc ca `reasoning_content`: neu no day chu ma `content` rong thi model da
    nghi that chu khong phai engine nuot mat dau ra -- day la cach duy nhat
    phan biet "runaway" voi "hong o tang khac".
    """
    than = {"model": "x", "messages": [{"role": "user", "content": nhac}],
            "max_tokens": max_tokens, "stream": False}
    # `nhiet = None` => KHONG gui truong nao, dung mac dinh cua server. Do dung
    # la cach `danh_gia_llm.py` goi, va mot probe gui 0.2 thi dang do mot cau
    # hinh khac voi cau hinh da sinh ra loi.
    if nhiet is not None:
        than["temperature"] = nhiet
    if effort:
        than["reasoning_effort"] = effort
    t0 = time.time()
    _, t = m.http("POST", base + "/v1/chat/completions", than, timeout=600.0)
    d = json.loads(t)
    ch = (d.get("choices") or [{}])[0]
    tin = ch.get("message") or {}
    noi = tin.get("content") or ""
    ngh = tin.get("reasoning_content") or ""
    return {
        "giay": round(time.time() - t0, 2),
        "token_ra": (d.get("usage") or {}).get("completion_tokens"),
        "ly_do_dung": ch.get("finish_reason"),
        "ky_tu_content": len(noi),
        "ky_tu_reasoning": len(ngh),
        "rong": not noi.strip(),
        "content_dau": noi[:120],
    }


def main():
    ap = argparse.ArgumentParser(description="Vi sao LTT-3.5 rong voi tieng Viet")
    ap.add_argument("--cong", type=int, default=8291)
    ap.add_argument("--lan", type=int, default=2)
    ap.add_argument("--ra", required=True)
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.cong
    m = _nap_bench()

    thu = os.path.dirname(os.path.abspath(args.ra))
    if thu:
        os.makedirs(thu, exist_ok=True)

    def ghi(rec):
        with open(args.ra, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        print(json.dumps(rec, ensure_ascii=True), flush=True)

    # Buoc 0 -- TAI HIEN truoc da. Hai truc cung luc: de bai nguyen van, va
    # nhiet do (mac dinh server nhu `danh_gia_llm`, doi chieu voi 0.2).
    for ten, nhac in DE.items():
        for nhiet in (None, 0.2):
            for i in range(args.lan):
                r = _goi(m, base, nhac, 1400, nhiet=nhiet)
                ghi(dict(bai="tai_hien", de=ten, lan=i, tran=1400,
                         nhiet=("mac_dinh" if nhiet is None else nhiet),
                         effort=None, **r))

    # H1: tran cao hon co lam no dong khoi khong (giu nhiet mac dinh).
    for tran in (4000, 8000):
        for i in range(args.lan):
            r = _goi(m, base, DE["vi_1tu"], tran)
            ghi(dict(bai="tran", de="vi_1tu", lan=i, tran=tran,
                     nhiet="mac_dinh", effort=None, **r))

    # H2: muc suy nghi co phai nut dieu khien khong.
    for eff in ("low", "medium", "high"):
        for i in range(args.lan):
            r = _goi(m, base, DE["vi_1tu"], 1400, effort=eff)
            ghi(dict(bai="effort", de="vi_1tu", lan=i, tran=1400,
                     nhiet="mac_dinh", effort=eff, **r))


if __name__ == "__main__":
    main()
