"""Tong hop ket qua do may B 17/09 thanh bang markdown (in ra stdout)."""
import json
import os
import statistics
import sys

GOC = sys.argv[1]  # thu muc chua ket_qua, ket_qua_ctrl_co_lap, ket_qua_35, ket_qua_38


def doc(thu_muc, ten):
    p = os.path.join(GOC, thu_muc, ten + ".jsonl")
    if not os.path.exists(p):
        return []
    ra = []
    for l in open(p, encoding="utf-8"):
        l = l.strip()
        if l.startswith("{"):
            ra.append(json.loads(l))
    return ra


def r(x, n=1):
    return "-" if x is None else round(x, n)


def nap_tables(rows, ten):
    print(f"\n#### {ten}: nap\n")
    print("| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        if d.get("su_kien") == "nap":
            a = d.get("args", "")
            them = []
            for k in ("-np", "-c", "-b", "-ub", "--cache-ram"):
                parts = a.split()
                if k in parts:
                    them.append(k + " " + parts[parts.index(k) + 1])
            print(f"| {d.get('nhan')} | {d.get('build_info')} | {d.get('n_ctx')} | {d.get('total_slots')} | {d.get('dedicated_mib')} | {d.get('shared_mib')} | {d.get('vram_used_mib')} | {d.get('bien_mib')} | {d.get('vram_nen_truoc_nap_mib')} | {d.get('giay_nap')} | {' '.join(them)} {'' if d.get('xanh') else 'KHONG XANH exit=' + str(d.get('exit'))} |")
        if d.get("su_kien") == "vram_sau_tai":
            print(f"| {d.get('nhan')} SAU TAI | | | | {d.get('dedicated_mib')} | {d.get('shared_mib')} | {d.get('vram_used_mib')} | {d.get('bien_mib')} | | | |")


def dong_thoi(rows, ten):
    print(f"\n#### {ten}: dong thoi (max_tokens 400, ignore_eos)\n")
    print("| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        if d.get("su_kien") != "dong_thoi":
            continue
        tl = d["tung_luong"]
        print(f"| {d['nhan']} | {d['k']} | {','.join(str(x // 1000) + 'k' for x in d['prompt_token'])} | {r(d['tok_s_tong_khi_ca_k_decode'])} | {d['cua_so_chong_s']} | {r(d['tok_s_tong_ca_dot'])} | "
              f"{' / '.join(str(r(x['decode_tps_server'])) for x in tl)} | {' / '.join(str(r(x['ttft_s'])) for x in tl)} | "
              f"{' / '.join(str(r(x['prefill_tps'], 0)) for x in tl)} | {sum(1 for x in tl if x['loi'])} |")


def hai_job(rows, ten):
    print(f"\n#### {ten}: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)\n")
    print("| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        if d.get("su_kien") != "hai_job":
            continue
        print(f"| {d['nhan']} | {d['prompt_job2']} | {r(d['job1_tok_s_truoc'])} | {r(d['job1_tok_s_trong_prefill_job2'])} | {d['job1_khoang_lang_max_trong_prefill_s']} | {r(d['job1_tok_s_trong_decode_job2'])} | {r(d['job1_tok_s_sau_job2'])} | {d['job2_ttft_s']} | {r(d['job2']['prefill_tps'], 0)} | {r(d['job2_tok_s_decode'])} |")


def prefill_chen(rows, ten):
    print(f"\n#### {ten}: prefill dai chen vao 2 luong dang decode\n")
    print("| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |")
    print("|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        if d.get("su_kien") != "prefill_chen":
            continue
        print(f"| {d['b']} | {d['prompt_token']} | {r(d['tok_s_decode_2_luong_truoc'])} | {r(d['tok_s_decode_2_luong_trong_prefill'])} | {r(d['tok_s_decode_2_luong_sau'])} | {d['khoang_lang_max_s']} | {d['giay_prefill']} | {r(d['luot_dai']['prefill_tps'], 0)} | {d['luot_dai']['loi']} |")


def cap_rong(rows, ten):
    out = []
    for d in rows:
        if d.get("su_kien") == "cap_slot":
            out.append(f"cap {d['nhan']} {d['slots']}: {[r(x) for x in d['decode_tps_server']]}")
        if d.get("su_kien") == "kiem_rong":
            out.append(f"kiem_rong {d['nhan']} k={d['k']} lan={d['lan']}: rong={d['so_rong']} token_ra={[x['token_ra'] for x in d['tung_luong']]} ket_thuc={[x['ket_thuc'] for x in d['tung_luong']]}")
    if out:
        print(f"\n#### {ten}: cap slot / kiem rong\n")
        for o in out:
            print("- " + o)


def canh_bao(rows, ten):
    for d in rows:
        if d.get("su_kien") in ("loi", "HUY_LO_PREFLIGHT", "het_ngan_sach", "bo_qua_het_gio") or (d.get("su_kien") == "preflight" and not d.get("dat")):
            print(f"- CANH BAO {ten}: {json.dumps(d)[:400]}")


def ctrl(thu_muc, ten):
    rows = doc(thu_muc, ten)
    don = [d["luot"]["decode_tps_server"] for d in rows if d.get("su_kien") == "ctrl_don"]
    pf = [d["luot"]["prefill_tps"] for d in rows if d.get("su_kien") == "ctrl_prefill_32k"]
    ttft = [d["luot"]["ttft_s"] for d in rows if d.get("su_kien") == "ctrl_prefill_32k"]
    ot = [(d.get("gpu_truoc") or {}) for d in rows if d.get("su_kien") == "ctrl_don"]
    cpu = [(d.get("he_thong_truoc") or {}).get("cpu_pct") for d in rows if d.get("su_kien") == "ctrl_don"]
    return don, pf, ttft, ot, cpu


def mmm(xs, n=1):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "-"
    return f"{round(statistics.median(xs), n)} [{round(min(xs), n)}–{round(max(xs), n)}] n={len(xs)}"


def am(thu_muc, ten):
    rows = doc(thu_muc, ten)
    if not rows:
        return
    print(f"\n### {thu_muc}/{ten} (AM: 1 server, 2 luot khoi dong bo, trung vi [min–max])\n")
    canh_bao(rows, ten)
    nap_tables(rows, ten)
    for d in rows:
        if d.get("su_kien") in ("khoi_dong_bo", "tai_on_dinh"):
            print("- " + json.dumps(d, ensure_ascii=False)[:600])
    for pha in ("am_moi", "sau_10_phut_tai"):
        print(f"\n#### pha {pha}: dong thoi\n")
        print("| k | prompt | tong tok/s khi ca k decode | moi luong decode tok/s (server, gop moi luong) | TTFT s luong 1k | TTFT s luong dai nhat | prefill tok/s luong dai nhat |")
        print("|---|---|---|---|---|---|---|")
        nhom = {}
        for d in rows:
            if d.get("su_kien") == "dong_thoi" and d["nhan"].startswith(pha + "|"):
                nhom.setdefault((d["k"], tuple(d["prompt_token"])), []).append(d)
        for (k, pr), ds in nhom.items():
            i_dai = pr.index(max(pr))
            print(f"| {k} | {','.join(str(x // 1000) + 'k' for x in pr)} | {mmm([d['tok_s_tong_khi_ca_k_decode'] for d in ds])} | "
                  f"{mmm([x['decode_tps_server'] for d in ds for x in d['tung_luong']])} | {mmm([d['tung_luong'][0]['ttft_s'] for d in ds], 2)} | "
                  f"{mmm([d['tung_luong'][i_dai]['ttft_s'] for d in ds], 2)} | {mmm([d['tung_luong'][i_dai]['prefill_tps'] for d in ds], 0)} |")
        print(f"\n#### pha {pha}: hai job\n")
        print("| job2 | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |")
        print("|---|---|---|---|---|---|---|---|---|")
        for n2 in (1000, 32000):
            ds = [d for d in rows if d.get("su_kien") == "hai_job" and d["nhan"].startswith(pha + "|") and d["prompt_job2"] == n2]
            if ds:
                print(f"| {n2} | {mmm([d['job1_tok_s_truoc'] for d in ds])} | {mmm([d['job1_tok_s_trong_prefill_job2'] for d in ds])} | {mmm([d['job1_khoang_lang_max_trong_prefill_s'] for d in ds], 2)} | "
                      f"{mmm([d['job1_tok_s_trong_decode_job2'] for d in ds])} | {mmm([d['job1_tok_s_sau_job2'] for d in ds])} | {mmm([d['job2_ttft_s'] for d in ds], 2)} | "
                      f"{mmm([d['job2']['prefill_tps'] for d in ds], 0)} | {mmm([d['job2_tok_s_decode'] for d in ds])} |")


def main():
    am("ket_qua_am35", "am35")
    am("ket_qua_am38", "am38")
    for thu_muc, phep in (("ket_qua", ["m1"]), ("ket_qua_35", ["m1", "m3_35", "m5", "m6"]), ("ket_qua_38", ["m3_38", "m2"])):
        for p in phep:
            rows = doc(thu_muc, p)
            if not rows:
                continue
            ten = f"{thu_muc}/{p}"
            print(f"\n### {ten}\n")
            canh_bao(rows, ten)
            nap_tables(rows, ten)
            hai_job(rows, ten)
            dong_thoi(rows, ten)
            prefill_chen(rows, ten)
            cap_rong(rows, ten)
            for d in rows:
                if d.get("su_kien") in ("tran_kv", "log_server", "cache", "kiem_tran", "cong_decode_don", "ke_hoach") or d.get("su_kien", "").startswith("luot_moi"):
                    d = dict(d)
                    if "tung_luot" in d:
                        d["tung_luot"] = f"<{len(d['tung_luot'])} luot>"
                    if "tung_luong" in d:
                        d["tung_luong"] = [(x["token_ra"], x["ket_thuc"], x["loi"], r(x["decode_tps_server"]), x["ttft_s"]) for x in d["tung_luong"]]
                    print("- " + json.dumps(d, ensure_ascii=False)[:1500])
    print("\n### doi chung ctrl\n")
    print("| card | dieu kien | decode don tok/s (3 luot) | trung vi | prefill 32k tok/s | TTFT 32k s | cpu% truoc luot |")
    print("|---|---|---|---|---|---|---|")
    for ten in ("ctrl35", "ctrl38"):
        for thu_muc, dk in (("ket_qua_ctrl_co_lap", "co lap"), ("ket_qua_35" if ten == "ctrl35" else "ket_qua_38", "song song")):
            don, pf, ttft, ot, cpu = ctrl(thu_muc, ten)
            if don:
                print(f"| {ten} | {dk} | {[r(x) for x in don]} | {r(statistics.median(don))} | {[r(x, 0) for x in pf]} | {ttft} | {cpu} |")
                print(f"|  | gpu luc bat dau tung luot | {ot} | | | | |")
    for thu_muc in ("ket_qua_35", "ket_qua_38", "ket_qua_ctrl_co_lap", "ket_qua"):
        p = os.path.join(GOC, thu_muc, "he_thong.jsonl")
        if os.path.exists(p):
            hs = [json.loads(l) for l in open(p) if l.startswith("{")]
            c = [h["cpu_pct"] for h in hs if h.get("cpu_pct") is not None]
            rf = [h["ram_trong_gb"] for h in hs if h.get("ram_trong_gb") is not None]
            if c:
                print(f"\n- he_thong {thu_muc}: n={len(hs)} cpu% p50={statistics.median(c)} max={max(c)}; RAM trong min={min(rf)} GB max={max(rf)} GB; tu {hs[0]['luc']} den {hs[-1]['luc']}")


main()
