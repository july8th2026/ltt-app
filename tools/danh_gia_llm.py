"""danh_gia_llm.py — bộ đánh giá chất lượng model nhà. (Prompt 04, cổng G5)

    python tools/danh_gia_llm.py --thu-thap --url http://127.0.0.1:8299 --model qwen38-api
    python tools/danh_gia_llm.py --cham tmp/thu_thap.json

## Vì sao tệp này tồn tại

Kho có `bench_llm_admission.py`, `llm_gateway/deploy/nghiem_thu.py`, `cham_mu.py`
— và **không có gì đo chất lượng model ngôn ngữ**. Audit 31/08 chấm G5 được
**6/15** vì lý do đó: không trả lời được câu *"Qwen của ta có đủ tốt cho việc
LTT cần không"* bằng bất cứ con số nào.

⛔ Đây **không** phải một bộ benchmark để so với model khác. Nó trả lời đúng một
   câu: **workload của LTT có chạy được không**, và **một thay đổi cấu hình có
   làm nó tệ đi không**. `MVP_AND_SCORING` §A/G5 nói thẳng: *"Không cần benchmark
   SOTA; cần pass workload của LTT."*

## Hai pha TÁCH RỜI, có chủ ý

    --thu-thap   goi model, ghi dau ra THO ra JSON.   Chay tren may B.
    --cham       doc JSON do, cham diem.               Chay tren may A.

🔴 **Vì sao tách.** Chấm điểm bài lập trình phải **chạy mã model sinh ra**. Chạy
   mã sinh tự động trên **máy B đang phục vụ khách** là một rủi ro không cần
   thiết — nên thu thập ở B, chấm ở A, trong tiến trình con có hạn thời gian.

⭐ Và nó còn được một thứ nữa: **chấm lại được mà không gọi model**. Sửa cách
   chấm rồi chạy lại trên cùng một tệp thu thập là so **cùng một đầu ra**, không
   phải hai lần sinh khác nhau.

## Vì sao KHÔNG truyền tham số lấy mẫu

`temperature`/`top_k`/`top_p` **không nằm trong hợp đồng công khai** — cache CUDA
graph khoá theo `(B, temp, top_k, top_p)`. Nên bộ này chấp nhận nhiễu lấy mẫu và
đối phó bằng cách khác: **mỗi bài chạy `--lan` lượt, lấy trung vị**, và đề bài
được viết sao cho câu đúng bền vững trước nhiễu.

⛔ Đừng "sửa" bằng cách truyền `temperature=0`. Làm thế là đo một cấu hình mà
   khách **không bao giờ** gặp.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Bộ đề ────────────────────────────────────────────────────────────────────
#
# Mỗi bài: `ma`, `nhom`, `nhac` (prompt), `cham` (tên hàm chấm), `du_lieu` tuỳ bài.
# ⛔ Đề phải ỔN ĐỊNH giữa các ứng viên A/B. Đổi đề là mất khả năng so sánh.

def _dong_co(n: int, kim: str, vi_tri: float) -> str:
    """Đống cỏ có kim, đặt ở `vi_tri` (0..1). Sinh tất định, không ngẫu nhiên."""
    dong = [f"Dong {i}: ma phien {i * 7919 % 100000:05d} khong quan trong." for i in range(n)]
    dong[int(n * vi_tri)] = kim
    return "\n".join(dong)


#: 3.000 dong x ~45 ky tu = ~135.000 ky tu. Cong uoc luong 2,5 ky tu/token
#: (`llm_gateway/ngan_sach.py: KY_TU_MOI_TOKEN`) => ~54.000 token, an toan duoi
#: tran 96.256.
#:
#: ⛔ DUNG NANG SO NAY DE "do ngu canh dai hon". 6.000 dong = ~108.000 token uoc
#:    luong => cong tra 413 TRUOC KHI cham model, va ca ba bai ngu canh se do
#:    vi mot ly do khong lien quan gi toi chat luong model. Muon do sat tran hon
#:    thi tinh nguoc tu `TOKEN_VAO_TRAN`, dung doan.
KIM = "Dong dac biet: ma bi mat cua du an LTT la XYLOPHONE-4417."
DAP_KIM = "XYLOPHONE-4417"

BO_DE = [
    # ── chỉ thị / tiếng Việt / tiếng Anh ───────────────────────────────────
    {"ma": "vi-01", "nhom": "tieng_viet", "cham": "chua_chuoi",
     "nhac": "Tra loi dung MOT tu, khong giai thich: thu do cua Viet Nam la gi?",
     "dap": ["Ha Noi", "Hà Nội", "Hanoi"]},
    {"ma": "vi-02", "nhom": "tieng_viet", "cham": "chua_chuoi",
     "nhac": "Mot cua hang ban 3 mon gia 12.000d, 25.000d va 8.000d. "
             "Tong cong bao nhieu dong? Tra loi chi bang con so.",
     "dap": ["45000", "45.000"]},
    {"ma": "en-01", "nhom": "tieng_anh", "cham": "chua_chuoi",
     "nhac": "Answer with exactly one word, no explanation: "
             "what is the capital city of Japan?",
     "dap": ["Tokyo"]},

    # ── lập trình: chấm bằng CHẠY THẬT ────────────────────────────────────
    {"ma": "code-01", "nhom": "lap_trinh", "cham": "chay_python",
     "nhac": "Viet mot ham Python ten `la_so_nguyen_to(n)` tra ve True neu n la "
             "so nguyen to, False neu khong. Chi tra ve KHOI MA trong mot khoi "
             "```python ... ```, khong giai thich.",
     "kiem": [("la_so_nguyen_to(2)", True), ("la_so_nguyen_to(1)", False),
              ("la_so_nguyen_to(97)", True), ("la_so_nguyen_to(100)", False),
              ("la_so_nguyen_to(-7)", False), ("la_so_nguyen_to(7919)", True)]},
    {"ma": "code-02", "nhom": "sua_loi", "cham": "chay_python",
     "nhac": "Ham Python sau co LOI. Sua lai va tra ve ban dung, chi trong mot "
             "khoi ```python ... ```, giu nguyen ten ham:\n\n"
             "```python\ndef trung_binh(ds):\n    return sum(ds) / len(ds)\n```\n\n"
             "No phai tra ve 0.0 khi danh sach rong thay vi nem loi.",
     "kiem": [("trung_binh([1,2,3])", 2.0), ("trung_binh([])", 0.0),
              ("trung_binh([5])", 5.0)]},

    # ── đầu ra có cấu trúc ────────────────────────────────────────────────
    {"ma": "json-01", "nhom": "cau_truc", "cham": "json_khop",
     "nhac": "Tra ve DUNG mot doi tuong JSON, khong co van ban nao khac, khong "
             "co khoi ma. Khuon: {\"ten\": <chuoi>, \"tuoi\": <so nguyen>, "
             "\"ky_nang\": <mang chuoi>}. Noi dung: mot lap trinh vien ten Lan, "
             "28 tuoi, biet Python va Go.",
     "khuon": {"ten": str, "tuoi": int, "ky_nang": list}},

    # ── ngữ cảnh dài: kim ở ba vị trí ─────────────────────────────────────
    {"ma": "ctx-10", "nhom": "ngu_canh_dai", "cham": "chua_chuoi",
     "vi_tri": 0.10, "so_dong": 3000, "dap": [DAP_KIM]},
    {"ma": "ctx-50", "nhom": "ngu_canh_dai", "cham": "chua_chuoi",
     "vi_tri": 0.50, "so_dong": 3000, "dap": [DAP_KIM]},
    {"ma": "ctx-90", "nhom": "ngu_canh_dai", "cham": "chua_chuoi",
     "vi_tri": 0.90, "so_dong": 3000, "dap": [DAP_KIM]},

    # ── sinh dài ──────────────────────────────────────────────────────────
    {"ma": "dai-01", "nhom": "sinh_dai", "cham": "dem_dong",
     "nhac": "Liet ke dung 40 dong, moi dong theo dung khuon `N. muc N` voi N "
             "chay tu 1 den 40. Khong them gi khac.",
     "toi_thieu": 38, "mau": r"^\s*(\d+)\.\s"},
]

#: Bài dùng tool — tách riêng vì thân request khác hẳn.
BO_DE_TOOL = [
    {"ma": "tool-01", "nhom": "chon_tool", "tool_dung": "tra_thoi_tiet",
     "nhac": "Thoi tiet o Da Nang hom nay the nao?",
     "kiem_tham_so": {"thanh_pho": ["Da Nang", "Đà Nẵng", "Danang"]}},
    {"ma": "tool-02", "nhom": "chon_tool", "tool_dung": "tinh_tien",
     "nhac": "Tinh giup toi 3 mon, moi mon 12500 dong thi het bao nhieu.",
     "kiem_tham_so": {}},
]

TOOLS = [
    {"type": "function", "function": {
        "name": "tra_thoi_tiet", "description": "Tra thoi tiet mot thanh pho",
        "parameters": {"type": "object", "required": ["thanh_pho"], "properties": {
            "thanh_pho": {"type": "string", "description": "Ten thanh pho"}}}}},
    {"type": "function", "function": {
        "name": "tinh_tien", "description": "Nhan so luong voi don gia",
        "parameters": {"type": "object", "required": ["so_luong", "don_gia"],
                       "properties": {"so_luong": {"type": "integer"},
                                      "don_gia": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "gui_email", "description": "Gui mot email",
        "parameters": {"type": "object", "required": ["den", "noi_dung"],
                       "properties": {"den": {"type": "string"},
                                      "noi_dung": {"type": "string"}}}}},
]


# ── Thu thập ────────────────────────────────────────────────────────────────

#: So lan thu lai khi may B tra 429, va giay cho giua cac lan.
#:
#: 🔴 VI SAO CAN. Do 31/08: trong tai cua may B coi "1 python tren card + tai GPU
#:    >= 50%" la BAN — va tai 89% luc do la cua CHINH `llama-server` cua ta dang
#:    sinh chu, khong phai cua ComfyUI. Ket qua: 6/12 bai bi 429 trong khi may
#:    khoe va tai duy nhat la cua ta.
#:
#: ⛔ Thu lai o day KHONG phai de che loi do. No de bo do CHAT LUONG do duoc
#:    chat luong, thay vi do mot dac tinh cua trong tai. Loi do van la mot phat
#:    hien P1 va duoc ghi rieng — xem `reports/04`.
THU_LAI_429 = 4
CHO_429_GIAY = 20.0


def _goi(url: str, tok: str, than: dict, timeout: float) -> tuple[int, dict, float]:
    du = json.dumps(than).encode("utf-8")
    yc = urllib.request.Request(
        url, data=du, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {tok}",
                 # ⛔ KHONG de urllib tu dien UA: Cloudflare chan tien to
                 #    `Python-urllib/` PHAN BIET HOA THUONG. Khong anh huong o
                 #    LAN, nhung tep nay co the duoc chi sang duong cong khai.
                 "User-Agent": "ltt-danh-gia/1.0"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, {"loi": e.read().decode("utf-8", "replace")[:500]}, time.monotonic() - t0
    except Exception as e:                                      # noqa: BLE001
        return 0, {"loi": f"{type(e).__name__}: {e}"}, time.monotonic() - t0


def _goi_co_thu_lai(url: str, tok: str, than: dict,
                    timeout: float) -> tuple[int, dict, float, int]:
    """Goi, thu lai khi 429. Tra ve them SO LAN bi 429 — con so do la du lieu."""
    so_429 = 0
    for _ in range(THU_LAI_429 + 1):
        ma, kq, giay = _goi(url, tok, than, timeout)
        if ma != 429:
            return ma, kq, giay, so_429
        so_429 += 1
        time.sleep(CHO_429_GIAY)
    return 429, kq, giay, so_429


def _van_ban(kq: dict) -> str:
    """Rút văn bản từ phản hồi Chat Completions."""
    try:
        return kq["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError):
        return ""


def thu_thap(url: str, tok: str, model: str, lan: int, timeout: float) -> dict:
    goc = url.rstrip("/") + "/v1/chat/completions"
    ra = {"model": model, "url": url, "lan": lan,
          "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "bai": []}

    for de in BO_DE:
        nhac = de.get("nhac")
        if de["nhom"] == "ngu_canh_dai":
            co = _dong_co(de["so_dong"], KIM, de["vi_tri"])
            nhac = (co + "\n\nDoc ky van ban tren. Ma bi mat cua du an LTT la gi? "
                         "Tra loi chi bang ma do.")
        for i in range(lan):
            than = {"model": model, "max_tokens": 1400,
                    "messages": [{"role": "user", "content": nhac}]}
            ma, kq, giay, so_429 = _goi_co_thu_lai(goc, tok, than, timeout)
            ra["bai"].append({"ma_bai": de["ma"], "lan": i, "ma_http": ma,
                              "giay": round(giay, 2), "ra": _van_ban(kq),
                              "su_dung": kq.get("usage", {}), "so_429": so_429,
                              "loi": kq.get("loi", "")})
            print(f"  {de['ma']:>8} #{i}  HTTP {ma}  {giay:6.2f}s"
                  + (f"  (429 x{so_429})" if so_429 else ""), flush=True)

    for de in BO_DE_TOOL:
        for i in range(lan):
            than = {"model": model, "max_tokens": 400, "tools": TOOLS,
                    "messages": [{"role": "user", "content": de["nhac"]}]}
            ma, kq, giay, so_429 = _goi_co_thu_lai(goc, tok, than, timeout)
            tc = []
            try:
                tc = kq["choices"][0]["message"].get("tool_calls") or []
            except (KeyError, IndexError, TypeError):
                pass
            ra["bai"].append({"ma_bai": de["ma"], "lan": i, "ma_http": ma,
                              "giay": round(giay, 2), "tool_calls": tc,
                              "ra": _van_ban(kq), "su_dung": kq.get("usage", {}),
                              "so_429": so_429, "loi": kq.get("loi", "")})
            print(f"  {de['ma']:>8} #{i}  HTTP {ma}  {giay:6.2f}s  "
                  f"tool={len(tc)}", flush=True)
    return ra


# ── Chấm ────────────────────────────────────────────────────────────────────

def _khoi_ma(van: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", van, re.S)
    return m.group(1) if m else van


def cham_chua_chuoi(de: dict, b: dict) -> tuple[bool, str]:
    van = (b.get("ra") or "")
    for d in de["dap"]:
        if d.lower() in van.lower():
            return True, ""
    return False, f"khong thay {de['dap']!r} trong {van[:80]!r}"


def cham_chay_python(de: dict, b: dict) -> tuple[bool, str]:
    """🔴 Chấm bài lập trình bằng CHẠY THẬT, không bằng khớp chuỗi.

    Khớp chuỗi cho điểm một hàm trông đúng mà chạy sai. Chạy thật thì không.

    ⛔ Chạy trong tiến trình con, có hạn thời gian, trong thư mục tạm — vì đây
       là mã do model sinh, không phải mã ta viết.
    """
    ma = _khoi_ma(b.get("ra") or "")
    if not ma.strip():
        return False, "khong co khoi ma"
    kiem = "\n".join(f"assert ({bt}) == ({kq!r}), {bt!r}" for bt, kq in de["kiem"])
    with tempfile.TemporaryDirectory() as tm:
        f = Path(tm) / "thu.py"
        f.write_text(ma + "\n\n" + kiem + "\nprint('DAT')\n", encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, str(f)], capture_output=True,
                               text=True, timeout=20, cwd=tm)
        except subprocess.TimeoutExpired:
            return False, "chay qua 20s"
    if r.returncode == 0 and "DAT" in r.stdout:
        return True, ""
    return False, (r.stderr or r.stdout).strip().splitlines()[-1][:120] if (r.stderr or r.stdout) else "that bai"


def cham_json_khop(de: dict, b: dict) -> tuple[bool, str]:
    van = (b.get("ra") or "").strip()
    van = _khoi_ma(van) if "```" in van else van
    m = re.search(r"\{.*\}", van, re.S)
    if not m:
        return False, f"khong tim thay JSON trong {van[:60]!r}"
    try:
        d = json.loads(m.group(0))
    except ValueError as e:
        return False, f"JSON hong: {e}"
    for k, kieu in de["khuon"].items():
        if k not in d:
            return False, f"thieu khoa {k!r}"
        if not isinstance(d[k], kieu):
            return False, f"{k!r} phai la {kieu.__name__}, thay {type(d[k]).__name__}"
    return True, ""


def cham_dem_dong(de: dict, b: dict) -> tuple[bool, str]:
    dong = [d for d in (b.get("ra") or "").splitlines() if re.match(de["mau"], d)]
    n = len(dong)
    return (n >= de["toi_thieu"], f"chi co {n} dong khop, can >= {de['toi_thieu']}")


def cham_tool(de: dict, b: dict) -> tuple[bool, str]:
    """Ba thứ phải đúng, và chúng hỏng theo ba kiểu khác nhau."""
    tc = b.get("tool_calls") or []
    if not tc:
        return False, "khong goi tool nao"
    ten = tc[0].get("function", {}).get("name", "")
    if ten != de["tool_dung"]:
        return False, f"chon nham tool: {ten!r} thay vi {de['tool_dung']!r}"
    tho = tc[0].get("function", {}).get("arguments", "")
    try:
        args = json.loads(tho) if isinstance(tho, str) else tho
    except ValueError as e:
        return False, f"tham so KHONG phai JSON hop le: {e}"
    for k, cho_phep in de.get("kiem_tham_so", {}).items():
        gt = str(args.get(k, ""))
        if not any(c.lower() in gt.lower() for c in cho_phep):
            return False, f"tham so {k!r}={gt!r} khong khop {cho_phep}"
    return True, ""


CHAM = {"chua_chuoi": cham_chua_chuoi, "chay_python": cham_chay_python,
        "json_khop": cham_json_khop, "dem_dong": cham_dem_dong}


def cham(duong: Path) -> dict:
    d = json.loads(duong.read_text(encoding="utf-8"))
    theo_ma = {x["ma"]: x for x in BO_DE}
    theo_ma_tool = {x["ma"]: x for x in BO_DE_TOOL}
    ket: dict[str, list] = {}
    ly_do: dict[str, list] = {}
    giay: dict[str, list] = {}

    for b in d["bai"]:
        mb = b["ma_bai"]
        if b.get("ma_http") != 200:
            ket.setdefault(mb, []).append(False)
            ly_do.setdefault(mb, []).append(f"HTTP {b.get('ma_http')}: {b.get('loi','')[:80]}")
            continue
        if mb in theo_ma_tool:
            ok, vi = cham_tool(theo_ma_tool[mb], b)
        else:
            de = theo_ma[mb]
            ok, vi = CHAM[de["cham"]](de, b)
        ket.setdefault(mb, []).append(ok)
        if not ok:
            ly_do.setdefault(mb, []).append(vi)
        giay.setdefault(mb, []).append(b.get("giay", 0))

    print("\n" + "=" * 74)
    print(f"  DANH GIA MODEL NHA — {d['model']} — {d['luc']}")
    print("=" * 74)
    tong_dat = tong = 0
    nhom_diem: dict[str, list] = {}
    for de in BO_DE + BO_DE_TOOL:
        mb = de["ma"]
        r = ket.get(mb, [])
        if not r:
            continue
        dat = sum(r)
        tong_dat += dat
        tong += len(r)
        nhom_diem.setdefault(de["nhom"], []).append(dat / len(r))
        tv = statistics.median(giay.get(mb, [0]))
        dau = "DAT " if dat == len(r) else ("mot phan" if dat else "HONG")
        print(f"  {mb:>8}  {de['nhom']:<14} {dat}/{len(r)}  {dau:<9} trung vi {tv:6.2f}s")
        for v in ly_do.get(mb, [])[:2]:
            print(f"            -> {v}")

    print("-" * 74)
    for n, ds in sorted(nhom_diem.items()):
        print(f"  {n:<16} {statistics.mean(ds) * 100:5.1f}%")
    print("-" * 74)
    print(f"  TONG: {tong_dat}/{tong} = {tong_dat / max(tong,1) * 100:.1f}%")
    return {"tong_dat": tong_dat, "tong": tong,
            "theo_nhom": {n: statistics.mean(ds) for n, ds in nhom_diem.items()}}


def main() -> int:
    p = argparse.ArgumentParser(description="Danh gia chat luong model nha.")
    p.add_argument("--thu-thap", action="store_true")
    p.add_argument("--cham", type=Path)
    p.add_argument("--url", default="http://127.0.0.1:8299")
    p.add_argument("--token", default="")
    p.add_argument("--model", default="qwen38-api")
    p.add_argument("--lan", type=int, default=1)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--ra", type=Path, default=Path("tmp/thu_thap_llm.json"))
    a = p.parse_args()

    if a.cham:
        cham(a.cham)
        return 0
    if not a.thu_thap:
        p.error("can --thu-thap hoac --cham")

    tok = a.token
    if not tok:
        env = Path(r"C:\ProgramData\LTTLlm\gateway.env")
        if env.exists():
            for d in env.read_text(encoding="utf-8-sig").splitlines():
                if d.startswith("LTT_LLM_TOKEN="):
                    tok = d.split("=", 1)[1].strip()
    if not tok:
        print("khong co token (dat --token hoac chay tren may B)")
        return 1

    d = thu_thap(a.url, tok, a.model, a.lan, a.timeout)
    a.ra.parent.mkdir(parents=True, exist_ok=True)
    a.ra.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nDA LUU: {a.ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
