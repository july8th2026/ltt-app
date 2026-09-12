"""probe_g4.py -- bon con so cua cong G4 (Task 3.2), do tren mot model dang chay.

G4 doi bon thu, va ca bon deu la dau vao cua mot QUYET DINH khac chu khong phai
so de ngam:

    token_moi_anh   mot anh 1024x768 an bao nhieu token ngu canh
                    => vao cong thuc gia (D07) va vao tran dau vao cong khai
    prefill tok/s   theo do dai prompt
                    => NGUONG_WHALE: tu do dai nao thi mot luot la "ca voi",
                       tuc du lau de lam ngheo slot cua nguoi khac
    W trung binh    dien nang o C1 va o Cn
                    => chi phi dien tren 1M token ra (D07 consequence 1)
    T_NAP_LLM       nap tu AM het bao nhieu giay
                    => `t_nap_llm_s` cua may trang thai residency (Task 5.2),
                       hien dang la mot con so gia dinh 45,0

⛔ `token_moi_anh` do bang `n_prompt_tokens` cua chinh engine, KHONG uoc bang
   cong thuc anh/patch: mmproj moi ban bam anh mot kieu, va con so nay di thang
   vao hoa don cua khach.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import time

_HERE = pathlib.Path(__file__).resolve().parent


def _nap_bench():
    spec = importlib.util.spec_from_file_location("bench_g4", _HERE / "bench.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _mot_luot(m, base, noi_dung, max_tokens=64):
    than = {"model": "x", "messages": [{"role": "user", "content": noi_dung}],
            "max_tokens": max_tokens, "stream": False}
    t0 = time.time()
    _, t = m.http("POST", base + "/v1/chat/completions", than, timeout=900.0)
    d = json.loads(t)
    return {
        "wall": round(time.time() - t0, 3),
        "token_vao": (d.get("usage") or {}).get("prompt_tokens"),
        "token_ra": (d.get("usage") or {}).get("completion_tokens"),
        "prompt_tok_s": (d.get("timings") or {}).get("prompt_per_second"),
        "predicted_tok_s": (d.get("timings") or {}).get("predicted_per_second"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, required=True)
    ap.add_argument("--uuid", required=True)
    ap.add_argument("--nhan", required=True, help="ten model dang chay")
    ap.add_argument("--co-anh", dest="co_anh", action="store_true")
    ap.add_argument("--ra", required=True)
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.cong
    m = _nap_bench()

    thu = os.path.dirname(os.path.abspath(args.ra))
    if thu:
        os.makedirs(thu, exist_ok=True)

    def ghi(rec):
        with open(args.ra, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(nhan=args.nhan, **rec), ensure_ascii=True) + "\n")
        print(json.dumps(dict(nhan=args.nhan, **rec), ensure_ascii=True), flush=True)

    # 1. token_moi_anh -- chenh lech giua CUNG mot cau hoi co anh va khong anh.
    #    Lay hieu chu khong lay so tuyet doi: phan text cua hai luot giong het
    #    nhau nen no triet tieu, con lai dung phan cua anh.
    if args.co_anh:
        chu = "Mo ta ngan buc anh."
        khong = _mot_luot(m, base, chu, 16)
        co = _mot_luot(m, base, [{"type": "text", "text": chu},
                                 {"type": "image_url",
                                  "image_url": {"url": m.anh_data_url()}}], 16)
        ghi({"bai": "token_moi_anh", "vao_khong_anh": khong["token_vao"],
             "vao_co_anh": co["token_vao"],
             "token_moi_anh": (co["token_vao"] or 0) - (khong["token_vao"] or 0),
             "giay_khong_anh": khong["wall"], "giay_co_anh": co["wall"]})

    # 2. prefill theo do dai -- de dat NGUONG_WHALE.
    for so_tu in (400, 4000, 20000, 60000, 100000):
        try:
            nhac = m.PROMPT_HUONG_DAN + m.nonce() + m.sinh_prompt(so_tu)
            lay = m.LayMau(args.uuid)
            lay.start()
            try:
                r = _mot_luot(m, base, nhac, 64)
            finally:
                lay.dung_lai()
            v, s, p = lay.ket_qua()
            ghi({"bai": "prefill", "tu_muc_tieu": so_tu, "vram_dinh_mib": v,
                 "shared_dinh_mib": s, "power_w_tb": p, **r})
        except Exception as e:  # noqa: BLE001
            ghi({"bai": "prefill", "tu_muc_tieu": so_tu, "loi": repr(e)})

    # 3. Dien nang o mot luot sinh DAI (C1 that, 600 token ra) -- con so dung de
    #    quy ra dong/1M token, chu khong phai dien luc may dang ranh.
    lay = m.LayMau(args.uuid)
    lay.start()
    try:
        kq = m.chat_stream(base, "x", m.PROMPT_HUONG_DAN + m.nonce() + m.sinh_prompt(1150),
                           600, ignore_eos=False, timeout=600.0)
    finally:
        lay.dung_lai()
    v, s, p = lay.ket_qua()
    u = kq.get("usage") or {}
    tg = kq.get("timings") or {}
    ghi({"bai": "dien_c1", "token_ra": u.get("completion_tokens"),
         "tok_s": tg.get("predicted_per_second"), "power_w_tb": p,
         "vram_dinh_mib": v, "shared_dinh_mib": s,
         "wall_s": round(kq["t_cuoi"] - kq["t0"], 3)})


if __name__ == "__main__":
    main()
