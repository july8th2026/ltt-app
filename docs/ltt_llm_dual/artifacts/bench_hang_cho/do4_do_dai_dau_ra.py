"""do4_do_dai_dau_ra.py - PHEP DO 4: do dai dau ra THAT (khong can tam dung). Thuan ASCII.

CHI DOC. Hai nguon, chon bang --nguon:

  log   (mac dinh) - so luot cua cong LLM tren MAY B: logger `llm_gateway.so`
        trong H:\\LTT_LLM\\logs\\gateway_err.log (llm_gateway/so_luot.py). Keo qua
        SSH, loc tren may B (mo tep FileShare.ReadWrite - dich vu dang giu tep).
        Truong: model, stream, ket_thuc, token_vao, token_cache, token_ra, ttft_s,
        decode_tps, so_dang_tin.
        GIOI HAN (doc truoc khi dien giai):
          * token_ra = reasoning + content GOP (khong truong nao tach rieng).
          * KHONG co max_tokens trong dong -> ty le cham tran = ty le ket_thuc
            == "length", khong phai token_ra / max_tokens.
          * stream=true -> so_dang_tin=false, token null -> bi loai (dem rieng).
          * Gom CA luu luong khong phai khach (eval, bench, canary di thang 8299).
            Bang theo ngay de nhin ra dot eval.
  csdl  - bang `jobs` tren MAY A (ltt_llm.chat: params.max_tokens, result.usage).
        Doc bi mat giong tools/dem_d2_agent_production.py (can quyen doc
        C:\\LTTPlatform\\secrets - ACL co y). Chi SELECT, khong commit.

Dung (tren may A):
  python do4_do_dai_dau_ra.py --nguon log --ngay 7 --ra do4_log.json
  python do4_do_dai_dau_ra.py --nguon csdl --ngay 7 --ra do4_csdl.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

SSH = ["ssh", "-i", str(pathlib.Path.home() / ".ssh" / "nexus_b"), "-o", "BatchMode=yes",
       "-o", "ConnectTimeout=15", "lengo@192.168.2.66"]

PS_LOC = r"""
$tu = '__TU__'
$fs = [IO.File]::Open('H:\LTT_LLM\logs\gateway_err.log', 'Open', 'Read', 'ReadWrite')
$sr = New-Object IO.StreamReader($fs)
while ($null -ne ($l = $sr.ReadLine())) {
  if ($l.Length -gt 30 -and $l.Contains('llm_gateway.so {') -and ($l.Substring(0,19) -ge $tu)) { $l }
}
$sr.Close()
"""


def phan_vi(ds: list, p: float):
    if not ds:
        return None
    ds = sorted(ds)
    k = (len(ds) - 1) * p
    f = int(k)
    c = min(f + 1, len(ds) - 1)
    return round(ds[f] + (ds[c] - ds[f]) * (k - f), 1)


def tom_tat(ds: list) -> dict:
    return {"n": len(ds), "p50": phan_vi(ds, .5), "p95": phan_vi(ds, .95),
            "p99": phan_vi(ds, .99), "max": max(ds) if ds else None}


def tu_log(ngay: int) -> dict:
    tu = (datetime.now() - timedelta(days=ngay)).strftime("%Y-%m-%d %H:%M:%S")
    kich = PS_LOC.replace("__TU__", tu)
    tep = pathlib.Path(__file__).with_name("_do4_loc.ps1")
    tep.write_text(kich, encoding="ascii")
    subprocess.run(["scp", "-q", "-i", SSH[2], "-o", "BatchMode=yes", str(tep),
                    "lengo@192.168.2.66:_do4_loc.ps1"], check=True)
    tep.unlink()
    r = subprocess.run(SSH + ["powershell -NoProfile -ExecutionPolicy Bypass -File _do4_loc.ps1"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600)
    dong = [x for x in r.stdout.splitlines() if "llm_gateway.so {" in x]
    theo_model = defaultdict(lambda: {"ra": [], "vao": [], "ket_thuc": Counter(),
                                      "stream_khong_so": 0, "khong_tin": 0,
                                      "ngay": Counter(), "decode_tps": []})
    for x in dong:
        try:
            d = json.loads(x[x.index("{"):])
        except ValueError:
            continue
        m = theo_model[d.get("model") or "?"]
        m["ngay"][x[:10]] += 1
        m["ket_thuc"][str(d.get("ket_thuc"))] += 1
        if d.get("stream"):
            m["stream_khong_so"] += 1
            continue
        if not d.get("so_dang_tin") or d.get("token_ra") is None:
            m["khong_tin"] += 1
            continue
        m["ra"].append(int(d["token_ra"]))
        m["vao"].append(int(d.get("token_vao") or 0))
        if d.get("decode_tps"):
            m["decode_tps"].append(float(d["decode_tps"]))
    ra = {"nguon": "log may B gateway_err.log (llm_gateway.so)", "tu": tu,
          "so_dong": len(dong), "models": {}}
    for ten, m in sorted(theo_model.items()):
        tong = sum(m["ket_thuc"].values())
        ra["models"][ten] = {
            "token_ra_reasoning_cong_content": tom_tat(m["ra"]),
            "token_vao": tom_tat(m["vao"]),
            "decode_tps": tom_tat(m["decode_tps"]),
            "ket_thuc": dict(m["ket_thuc"]),
            "ty_le_cham_tran_length": round(m["ket_thuc"].get("length", 0) / tong, 4) if tong else None,
            "stream_khong_co_token": m["stream_khong_so"], "khong_dang_tin": m["khong_tin"],
            "theo_ngay": dict(sorted(m["ngay"].items())),
        }
    return ra


def tu_csdl(ngay: int) -> dict:
    sys.path.insert(0, str(pathlib.Path(r"D:\LTTSTUDIOSAPP")))
    from tools.dem_d2_agent_production import _chi_doc, _doc_bi_mat, _live_url  # noqa: E402
    import sqlalchemy as sa

    live = _live_url()
    pw = _doc_bi_mat("postgres-superuser.txt").strip()
    if not live.startswith(("postgresql", "postgres")) or not pw:
        raise SystemExit("BO QUA: khong doc duoc URL/mat khau CSDL (ACL).")
    ten = live.rsplit("/", 1)[-1].split("?", 1)[0]
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    e = sa.create_engine(f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}",
                         connect_args={"connect_timeout": 5})
    cau = _chi_doc(
        "SELECT coalesce(params->>'model', '?') AS model, "
        "(params->>'max_tokens') AS max_tokens, "
        "(result->'usage'->>'completion_tokens') AS ra, "
        "(result->'usage'->>'prompt_tokens') AS vao, status "
        "FROM jobs WHERE job_type = 'ltt_llm.chat' "
        f"AND created_at >= now() - interval '{int(ngay)} days'")
    theo = defaultdict(lambda: {"ra": [], "ty_le": [], "cham_tran": 0, "n": 0, "trang_thai": Counter()})
    with e.connect() as c:
        for model, mt, ra_, _vao, st in c.execute(sa.text(cau)):
            m = theo[model]
            m["n"] += 1
            m["trang_thai"][st] += 1
            if ra_ is None:
                continue
            m["ra"].append(int(ra_))
            if mt:
                m["ty_le"].append(round(int(ra_) / max(1, int(mt)), 3))
                if int(ra_) >= int(mt):
                    m["cham_tran"] += 1
    return {"nguon": "csdl jobs ltt_llm.chat", "models": {
        k: {"n": v["n"], "trang_thai": dict(v["trang_thai"]),
            "completion_tokens_reasoning_cong_content": tom_tat(v["ra"]),
            "ty_le_ra_tren_max_tokens": tom_tat(v["ty_le"]),
            "cham_tran": v["cham_tran"]} for k, v in theo.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nguon", choices=("log", "csdl"), default="log")
    ap.add_argument("--ngay", type=int, default=7)
    ap.add_argument("--ra", default="")
    a = ap.parse_args()
    kq = tu_log(a.ngay) if a.nguon == "log" else tu_csdl(a.ngay)
    s = json.dumps(kq, ensure_ascii=True, indent=1)
    print(s)
    if a.ra:
        pathlib.Path(a.ra).write_text(s + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
