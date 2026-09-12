"""probe_viet_sua.py -- thu bon cach khac phuc "nghi mai khong dut" cua LTT-3.5.

## Nguyen nhan, theo tai lieu model + cong dong (tra 12/09)

KHONG phai "model khong biet tieng Viet". Ba su that doc duoc:

1. Qwen3.5 o che do thinking co loi **truncated thinking** da duoc do cong khai:
   **17,4 %** dau ra tren LiveCodeBench khong bao gio phat ra `</think>`, va
   **84 %** so do co ti le lap > 30 %. Bai ngan ~6 %, bai kho 27,5 %.
   `</think>` chi la MOT token trong tu dien (id 248069) -- vong lap lap chu lam
   xac suat cua no tut, va luong tu hoa (Q4/Q6) lam tut them vi no la token
   tan so thap.

2. **Qwen3.5 luon "nghi" bang tieng Anh** (QwenLM/Qwen3.8 issue #35), ke ca khi
   de bai la thu tieng khac. De tieng Viet vi vay bat model nghi bac cau qua
   mot ngon ngu khac -- chuoi suy luan dai hon va long hon, tuc de roi vao vong
   lap hon. Khop voi so do cua ta: **6/8 luot tieng Viet rong, 1/8 tieng Anh**.

3. Tham so lay mau **mac dinh cua llama-server lech voi khuyen nghi cua Qwen**
   o BON cho -- va mot trong so do nham thang vao co che lap:

       llama-server mac dinh   Qwen khuyen nghi (thinking)
       temp 0,80               0,60
       top-k 40                20
       min-p 0,05              0
       presence-penalty 0,00   1,50   <- chinh la phanh chong lap

## Bon cach thu, va vi sao la bon cach nay

    A  mac dinh          tai hien (doi chung am)
    B  tham so Qwen      sua dung cho lech o (3), khong dong vao kien truc
    C  --reasoning-budget  ep dong </think> o tang giai ma, khong phu thuoc
                          model co "chiu" dong hay khong
    D  enable_thinking=false  bo han khoi nghi

C va D la co SAN trong b10883 (da kiem `--help`). D re nhat ve toc do nhung doi
lai kha nang suy luan; C giu suy luan nhung dat tran. Bai nay do, khong chon.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import time

_HERE = pathlib.Path(__file__).resolve().parent

# De chep nguyen van tu `tools/danh_gia_llm.py` + dap an cua chinh bo de do.
DE = [
    ("vi_1tu",  "Tra loi dung MOT tu, khong giai thich: thu do cua Viet Nam la gi?",
     ["Ha Noi", "Hà Nội", "Hanoi"]),
    ("vi_tinh", "Mot cua hang ban 3 mon gia 12.000d, 25.000d va 8.000d. "
                "Tong cong bao nhieu dong? Tra loi chi bang con so.",
     ["45000", "45.000"]),
    # Doi chung DUONG: bai nay von da xanh. Neu mot cach "sua" lam no do thi
    # cach ay khong phai mot cach sua, du con so tieng Viet co dep den dau.
    ("en_1tu",  "Answer with exactly one word, no explanation: "
                "what is the capital city of Japan?", ["Tokyo"]),
]

# Khuyen nghi chinh thuc cua Qwen cho che do thinking.
THAM_SO_QWEN = {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
                "min_p": 0.0, "presence_penalty": 1.5}


def _nap_bench():
    spec = importlib.util.spec_from_file_location("bench_sua", _HERE / "bench.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _goi(m, base, nhac, dap, max_tokens, tham_so):
    than = {"model": "x", "messages": [{"role": "user", "content": nhac}],
            "max_tokens": max_tokens, "stream": False}
    than.update(tham_so or {})
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
        "ky_tu_content": len(noi), "ky_tu_reasoning": len(ngh),
        "rong": not noi.strip(),
        # Rong hay khong moi la nua cau chuyen. Nua con lai: no co tra loi
        # DUNG khong. Mot cach "sua" lam model het rong nhung tra sai thi khong
        # sua duoc gi ca.
        "dung": any(x.lower() in noi.lower() for x in dap),
        "content_dau": noi[:100],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=8291)
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--nhan", required=True, help="ten cau hinh server dang chay")
    ap.add_argument("--tham-so", dest="tham_so", default="mac_dinh",
                    choices=["mac_dinh", "qwen"])
    ap.add_argument("--ra", required=True)
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.cong
    m = _nap_bench()
    ts = THAM_SO_QWEN if args.tham_so == "qwen" else {}

    thu = os.path.dirname(os.path.abspath(args.ra))
    if thu:
        os.makedirs(thu, exist_ok=True)

    for ten, nhac, dap in DE:
        for i in range(args.lan):
            try:
                r = _goi(m, base, nhac, dap, 1400, ts)
            except Exception as e:  # noqa: BLE001
                r = {"loi": repr(e)}
            rec = dict(cau_hinh=args.nhan, tham_so=args.tham_so,
                       de=ten, lan=i, **r)
            with open(args.ra, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
            print(json.dumps(rec, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
