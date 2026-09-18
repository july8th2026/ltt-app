"""ab_lay_mau_35.py — bộ đề cố định + A/B MỘT biến cho LTT-3.5 (plan v2 Task 12). Đo thẳng engine.

    python tools\\ab_lay_mau_35.py chay --base http://127.0.0.1:18280 --lan 3 --ra <tệp.jsonl>
    python tools\\ab_lay_mau_35.py so-sanh <tệp.jsonl>

⭐ KHÔNG nạp lại model. Cả ba biến gửi được THEO REQUEST tới llama-server (ghim 91f6a6cf3):
   `presence_penalty`, `temperature` (tham số lấy mẫu OAI-compat), và `reasoning_budget_tokens`
   (`tools/server/server-common.cpp:1366-1369` — request ghi đè `--reasoning-budget`). Biến thể A gửi
   **không gì** ⇒ đúng cờ `llama-swap.yaml` đang chạy. Nhờ vậy A và B xen kẽ trong CÙNG một lượt
   (cùng tải máy, cùng giờ) và không đụng LTT-3.8 (`-watch-config` nạp lại CẢ HAI model mỗi lần lưu).

Năm phép, mỗi phép MỘT biến (so với A):
  presence     `presence_penalty` 0 → 1,5   (card 3.5 thinking-general: 1,5)  — mọi nhóm
  temp_code    `temperature`      1,0 → 0,6 (card 3.5 thinking-coding: 0,6)  — chỉ nhóm `code`
  budget       `reasoning_budget_tokens` 2048 → 4096                         — mọi nhóm
  codex_instr  (R-10) system = base instructions mặc định của Codex thay vì rỗng — `code`, `tool`, `agent`
  preserve     (R-17) `chat_template_kwargs.preserve_reasoning` true → false  — chỉ `agent` (có lịch sử);
               ghi thêm `cache_n`/`prompt_n` từng lượt để đo tỉ lệ trúng cache tiền tố

Bộ đề (khoá TRƯỚC khi đo; đổi đề = mất so sánh): `code` 10 bài chấm bằng CHẠY THẬT, `vi` 10 bài tiếng
Việt chấm tất định, `tool` 6 bài gọi công cụ một lượt, `agent` 6 kịch bản nhiều lượt (dùng lại kịch bản +
hàm chấm của bộ chấm A/B `tools/ab_lich_su_suy_nghi.py`, Task 10).

Luật quyết (khoá TRƯỚC khi đo):
  * Cặp = (bài, lượt) chạy cả A và B. McNemar chính xác trên cặp bất đồng (b = chỉ B đúng, c = chỉ A đúng).
  * `B_thang_ro`  ⇔ b > c **và** p hai phía < 0,05 **và** không nhóm nào của B thấp hơn cận dưới Wilson 95 %
    của A ở nhóm đó.  ⇒ chỉ khi đó mới đề xuất đổi production (plan Step 3).
  * `B_khong_tut` ⇔ không (c > b và p < 0,05) ⇒ "giữ nếu ≥ cũ" của Step 0.
  * Phụ: tỉ lệ rỗng (content rỗng), tỉ lệ lặp (vòng lặp chữ), token ra trung vị, giây trung vị.
"""
from __future__ import annotations

from typing import cast

import argparse
import json
import math
import pathlib
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "qwen35-api"
#: Đủ chỗ cho budget 4096 + trả lời; card khuyến nghị 32.768 nhưng bộ đề này ngắn.
MAX_TOKENS = 8192

BIEN_THE: dict[str, dict] = {
    "A": {},
    "pp15": {"presence_penalty": 1.5},
    "t06": {"temperature": 0.6},
    "rb4096": {"reasoning_budget_tokens": 4096},
    #: R-10: system = base instructions mặc định của Codex (`codex-rs/models-manager/prompt.md`) thay cho
    #: `base_instructions: ""` LTT khai. Không phải tham số engine — `mot_luot` chèn thành tin nhắn system.
    "codex": {"_system": "codex"},
    #: R-17: bỏ suy nghĩ cũ khỏi lịch sử. ⚠️ Phải là `preserve_reasoning`, KHÔNG `preserve_thinking`: llama.cpp
    #: (`common/arg.cpp:958-960`) tự nạp `preserve_reasoning="true"` vào kwargs mặc định, và template v22.5:8-14 đọc
    #: `preserve_reasoning` TRƯỚC ⇒ `preserve_thinking: false` theo request bị che, không có tác dụng (đo 18/09
    #: bằng `/apply-template`: 235 ký tự cả hai; `preserve_reasoning: false` → 137, mất khối suy nghĩ).
    "pt_false": {"chat_template_kwargs": {"preserve_reasoning": False}},
}
#: phép -> (biến thể B, các nhóm áp dụng)
PHEP: dict[str, tuple[str, tuple[str, ...]]] = {
    "presence": ("pp15", ("code", "vi", "tool", "agent")),
    "temp_code": ("t06", ("code",)),
    "budget": ("rb4096", ("code", "vi", "tool", "agent")),
    "codex_instr": ("codex", ("code", "tool", "agent")),
    "preserve": ("pt_false", ("agent",)),
}

#: Nội dung system của biến thể `codex` — nạp từ tệp (`--codex-prompt`), không vendor vào kho.
SYSTEM_NGOAI: dict[str, str] = {}

_LAP = re.compile(r"(.{8,}?)\1{6,}", re.S)


# ── Bộ đề ────────────────────────────────────────────────────────────────────

def _k(*cap):
    return list(cap)


DE_CODE = [
    {"ma": "c01", "nhac": "Write a Python function `roman_to_int(s: str) -> int` converting a Roman numeral to an integer.",
     "kiem": _k(("roman_to_int('III')", 3), ("roman_to_int('LVIII')", 58), ("roman_to_int('MCMXCIV')", 1994),
                ("roman_to_int('XLIX')", 49))},
    {"ma": "c02", "nhac": "Write a Python function `merge_intervals(xs)` that merges overlapping closed intervals "
                          "given as a list of [start, end] lists and returns them sorted by start.",
     "kiem": _k(("merge_intervals([[1,3],[2,6],[8,10],[15,18]])", [[1, 6], [8, 10], [15, 18]]),
                ("merge_intervals([[1,4],[4,5]])", [[1, 5]]), ("merge_intervals([])", []),
                ("merge_intervals([[5,7],[1,2]])", [[1, 2], [5, 7]]))},
    {"ma": "c03", "nhac": "Viết hàm Python `parse_duration(s)` đổi chuỗi dạng '1h30m15s' (mỗi phần h/m/s có thể "
                          "vắng, theo thứ tự h, m, s) thành tổng số giây (int). Chuỗi rỗng trả 0.",
     "kiem": _k(("parse_duration('1h30m15s')", 5415), ("parse_duration('45s')", 45), ("parse_duration('2h')", 7200),
                ("parse_duration('10m5s')", 605), ("parse_duration('')", 0))},
    {"ma": "c04", "nhac": "Write a Python function `topo_sort(n, edges)` returning a topological order (list) of nodes "
                          "0..n-1 for directed edges (u, v) meaning u before v; when several nodes are available pick "
                          "the smallest first. Return None if there is a cycle.",
     "kiem": _k(("topo_sort(4, [(0,1),(1,2),(0,3)])", [0, 1, 2, 3]), ("topo_sort(3, [(2,1),(1,0)])", [2, 1, 0]),
                ("topo_sort(2, [(0,1),(1,0)])", None), ("topo_sort(3, [])", [0, 1, 2]))},
    {"ma": "c05", "nhac": "Hàm sau có lỗi off-by-one, sửa lại, giữ nguyên tên:\n```python\ndef tim(xs, x):\n"
                          "    lo, hi = 0, len(xs)\n    while lo < hi:\n        mid = (lo + hi) // 2\n"
                          "        if xs[mid] == x:\n            return mid\n        if xs[mid] < x:\n"
                          "            lo = mid\n        else:\n            hi = mid - 1\n    return -1\n```\n"
                          "`tim` tìm nhị phân `x` trong danh sách đã sắp xếp tăng, trả chỉ số hoặc -1.",
     "kiem": _k(("tim([1,3,5,7,9], 7)", 3), ("tim([1,3,5,7,9], 1)", 0), ("tim([1,3,5,7,9], 9)", 4),
                ("tim([1,3,5,7,9], 4)", -1), ("tim([], 1)", -1), ("tim([2], 2)", 0))},
    {"ma": "c06", "nhac": "Write a Python function `top_words(text, k)` returning the k most frequent words "
                          "(case-insensitive, words are runs of letters a-z) as a list of (word, count) tuples, "
                          "ordered by count descending then word ascending.",
     "kiem": _k(("top_words('b a b c a b', 2)", [("b", 3), ("a", 2)]),
                ("top_words('The the THE cat, cat; dog!', 3)", [("the", 3), ("cat", 2), ("dog", 1)]),
                ("top_words('x y z', 2)", [("x", 1), ("y", 1)]))},
    {"ma": "c07", "nhac": "Write a Python function `spiral(m)` returning the elements of a 2D list in clockwise "
                          "spiral order starting top-left.",
     "kiem": _k(("spiral([[1,2,3],[4,5,6],[7,8,9]])", [1, 2, 3, 6, 9, 8, 7, 4, 5]),
                ("spiral([[1,2,3,4],[5,6,7,8],[9,10,11,12]])", [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]),
                ("spiral([])", []), ("spiral([[1],[2],[3]])", [1, 2, 3]))},
    {"ma": "c08", "nhac": "Write a Python function `calc(expr)` that evaluates an arithmetic expression string with "
                          "non-negative integers, + - * / and parentheses, using true division, returning a float. "
                          "Do not use eval or exec.",
     "kiem": _k(("calc('1 + 2 * 3')", 7.0), ("calc('(1 + 2) * 3')", 9.0), ("calc('10 / 4 - 1')", 1.5),
                ("calc('2 * (3 + (4 - 1)) / 3')", 4.0))},
    {"ma": "c09", "nhac": "Write a Python class `LRU` with `__init__(self, cap)`, `get(self, k)` returning the value "
                          "or -1, and `put(self, k, v)`; evicts the least recently used key when over capacity.",
     "kiem": _k(("(lambda c: [c.put(1,1), c.put(2,2), c.get(1), c.put(3,3), c.get(2), c.get(3)])(LRU(2))",
                 [None, None, 1, None, -1, 3]),
                ("(lambda c: (c.put(1,1), c.put(1,5), c.get(1)))(LRU(1))[2]", 5))},
    {"ma": "c10", "nhac": "Viết hàm Python `doc_so(n)` đọc số nguyên 0 <= n < 1000 thành chữ tiếng Việt viết thường "
                          "theo cách đọc chuẩn, ví dụ 105 -> 'một trăm linh năm', 21 -> 'hai mươi mốt', "
                          "15 -> 'mười lăm', 0 -> 'không'.",
     "kiem": _k(("doc_so(0)", "không"), ("doc_so(15)", "mười lăm"), ("doc_so(21)", "hai mươi mốt"),
                ("doc_so(105)", "một trăm linh năm"), ("doc_so(310)", "ba trăm mười"),
                ("doc_so(999)", "chín trăm chín mươi chín"))},
]
for _b in DE_CODE:
    _b["nhac"] += "\nChỉ trả về mã trong MỘT khối ```python ... ```, không giải thích."

DE_VI = [
    {"ma": "v01", "nhac": "Một người mua 3 kg táo giá 45.000 đồng/kg và 2 kg cam giá 30.000 đồng/kg, đưa 500.000 "
                          "đồng. Người bán phải thối lại bao nhiêu đồng? Chỉ trả lời bằng con số.", "so": 305000},
    {"ma": "v02", "nhac": "Một chiếc áo giá 800.000 đồng được giảm 15%, sau đó tăng 10% so với giá đã giảm. Giá cuối "
                          "cùng là bao nhiêu đồng? Chỉ trả lời bằng con số.", "so": 748000},
    {"ma": "v03", "nhac": "Hôm nay là thứ Tư. Hỏi 100 ngày nữa là thứ mấy? Trả lời ngắn gọn một cụm từ.",
     "chua": ["thứ sáu", "thứ 6"]},
    {"ma": "v04", "nhac": "An cao hơn Bình. Bình cao hơn Chi. Dũng thấp hơn Chi. Ai thấp nhất? Trả lời chỉ bằng tên.",
     "chua": ["dũng"]},
    {"ma": "v05", "nhac": "Mảnh vườn hình chữ nhật dài 25 m, rộng 16 m. Người ta trồng rau trên 3/5 diện tích. Diện "
                          "tích trồng rau là bao nhiêu mét vuông? Chỉ trả lời bằng con số.", "so": 240},
    {"ma": "v06", "nhac": "Minh đọc cuốn sách 240 trang. Ngày đầu đọc 1/4 số trang, ngày thứ hai đọc 1/3 số trang còn "
                          "lại. Còn bao nhiêu trang chưa đọc? Chỉ trả lời bằng con số.", "so": 120},
    {"ma": "v07", "nhac": "Trích thông tin từ câu sau và trả về DUY NHẤT một đối tượng JSON với các khoá ho_ten, tuoi "
                          "(số nguyên), thanh_pho, so_dien_thoai (chỉ chữ số): \"Chị Nguyễn Thị Lan, 34 tuổi, sống ở "
                          "Đà Nẵng, số điện thoại 0905 123 456.\"",
     "json": {"ho_ten": "Nguyễn Thị Lan", "tuoi": 34, "thanh_pho": "Đà Nẵng", "so_dien_thoai": "0905123456"}},
    {"ma": "v08", "nhac": "Viết đúng 3 câu tiếng Việt có dấu giới thiệu về Hà Nội. Mỗi câu kết thúc bằng dấu chấm. "
                          "Không dùng chữ \"đẹp\". Không thêm tiêu đề hay gạch đầu dòng.", "ba_cau": True},
    {"ma": "v09", "nhac": "Giải thích ngắn gọn trong 2–3 câu tiếng Việt vì sao bầu trời ban ngày có màu xanh.",
     "chua": ["tán xạ"], "tieng_viet": True},
    {"ma": "v10", "nhac": "Có 5 người bắt tay nhau, mỗi cặp bắt tay đúng một lần. Có tất cả bao nhiêu cái bắt tay? "
                          "Chỉ trả lời bằng con số.", "so": 10},
]

TOOLS_1 = [
    {"type": "function", "function": {"name": "tra_thoi_tiet", "description": "Tra thời tiết một thành phố",
     "parameters": {"type": "object", "required": ["thanh_pho"],
                    "properties": {"thanh_pho": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "tinh_tien", "description": "Nhân số lượng với đơn giá",
     "parameters": {"type": "object", "required": ["so_luong", "don_gia"],
                    "properties": {"so_luong": {"type": "integer"}, "don_gia": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "gui_email", "description": "Gửi một email",
     "parameters": {"type": "object", "required": ["den", "noi_dung"],
                    "properties": {"den": {"type": "string"}, "noi_dung": {"type": "string"}}}}},
]

DE_TOOL = [
    {"ma": "t01", "nhac": "Thời tiết ở Đà Nẵng hôm nay thế nào?",
     "goi": [("tra_thoi_tiet", {"thanh_pho": ["đà nẵng", "da nang", "danang"]})]},
    {"ma": "t02", "nhac": "Tính giúp tôi 3 món, mỗi món 12500 đồng thì hết bao nhiêu.",
     "goi": [("tinh_tien", {"so_luong": [3], "don_gia": [12500]})]},
    {"ma": "t03", "nhac": "Gửi email cho lan@ltt.vn báo rằng cuộc họp dời sang 3 giờ chiều.",
     "goi": [("gui_email", {"den": ["lan@ltt.vn"], "noi_dung": ["3"]})]},
    {"ma": "t04", "nhac": "Xin chào, bạn khoẻ không?", "goi": []},
    {"ma": "t05", "nhac": "Cho tôi biết thời tiết ở Huế và ở Hà Nội.",
     "goi": [("tra_thoi_tiet", {"thanh_pho": ["huế", "hue"]}),
             ("tra_thoi_tiet", {"thanh_pho": ["hà nội", "ha noi", "hanoi"]})]},
    {"ma": "t06", "nhac": "7 cái bánh, mỗi cái 15000 đồng, tổng bao nhiêu? Dùng công cụ để tính.",
     "goi": [("tinh_tien", {"so_luong": [7], "don_gia": [15000]})]},
]

DE_AGENT = [{"ma": f"a{i:02d}", "kich_ban": i} for i in range(6)]


def bo_de() -> list[dict]:
    nhom: list[tuple[str, list]] = [("code", DE_CODE), ("vi", DE_VI), ("tool", DE_TOOL), ("agent", DE_AGENT)]
    return [{**cast(dict, b), "nhom": ten} for ten, ds in nhom for b in ds]


# ── Chấm (thuần) ─────────────────────────────────────────────────────────────

def _khoi_ma(van: str) -> str:
    m = re.findall(r"```(?:python|py)?\s*\n(.*?)```", van, re.S)
    return max(m, key=len) if m else van


def cham_code(bai: dict, text: str) -> bool:
    ma = _khoi_ma(text or "")
    if not ma.strip():
        return False
    kiem = "\n".join(f"assert ({bt}) == ({kq!r}), {bt!r}" for bt, kq in bai["kiem"])
    with tempfile.TemporaryDirectory() as tm:
        f = pathlib.Path(tm) / "thu.py"
        f.write_text(ma + "\n\n" + kiem + "\nprint('DAT')\n", encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, timeout=20, cwd=tm,
                               encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return False
    return r.returncode == 0 and "DAT" in r.stdout


def _so_trong(text: str) -> list[int]:
    return [int(x.replace(".", "").replace(",", "").replace(" ", ""))
            for x in re.findall(r"\d{1,3}(?:[.,\s]\d{3})+(?![\d])|\d+", text or "")]


_DAU_VIET = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)


def cham_vi(bai: dict, text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if "so" in bai:
        so = _so_trong(t)
        return bool(so) and so[-1] == bai["so"]
    if "json" in bai:
        m = re.search(r"\{.*\}", t, re.S)
        try:
            d = json.loads(m.group(0)) if m else None
        except ValueError:
            return False
        if not isinstance(d, dict):
            return False
        ok = all(str(d.get(k, "")).strip().lower() == str(v).lower() for k, v in bai["json"].items()
                 if k != "so_dien_thoai")
        return ok and re.sub(r"\D", "", str(d.get("so_dien_thoai", ""))) == bai["json"]["so_dien_thoai"]
    if bai.get("ba_cau"):
        cau = [c for c in re.split(r"(?<=\.)\s+", t) if c.strip()]
        return (len(cau) == 3 and all(c.rstrip().endswith(".") for c in cau) and "đẹp" not in t.lower()
                and len(_DAU_VIET.findall(t)) >= 10)
    ok = any(c in t.lower() for c in bai.get("chua", []))
    if bai.get("tieng_viet"):
        ok = ok and len(_DAU_VIET.findall(t)) >= 10
    return ok


def _args(tc: dict) -> dict:
    fn = tc.get("function") or {}
    tho = fn.get("arguments", "")
    try:
        a = json.loads(tho) if isinstance(tho, str) else tho
    except ValueError:
        return {}
    return a if isinstance(a, dict) else {}


def cham_tool(bai: dict, text: str, tool_calls: list[dict]) -> bool:
    tc = tool_calls or []
    if not bai["goi"]:
        return not tc and bool((text or "").strip())
    if len(tc) < len(bai["goi"]):
        return False
    con = list(tc)
    for ten, dk in bai["goi"]:
        khop = None
        for c in con:
            if (c.get("function") or {}).get("name") != ten:
                continue
            a = _args(c)
            if all(any(str(ok).lower() in str(a.get(k, "")).lower() if isinstance(ok, str) else a.get(k) == ok
                       for ok in cho_phep) for k, cho_phep in dk.items()):
                khop = c
                break
        if khop is None:
            return False
        con.remove(khop)
    return True


def co_lap(text: str) -> bool:
    return bool(_LAP.search(text or ""))


def mcnemar_p(b: int, c: int) -> float:
    """p hai phía chính xác (nhị thức, p=0,5) trên n = b + c cặp bất đồng."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    duoi = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * duoi)


def wilson(dat: int, tong: int, z: float = 1.96) -> tuple[float, float]:
    from tools.ab_lich_su_suy_nghi import wilson as w
    return w(dat, tong, z)


def phan_quyet(dong: list[dict], phep: str) -> dict:
    """Áp luật đã khoá cho một phép trên các dòng kết quả (mỗi dòng: ma, nhom, lan, bien_the, dung, ...)."""
    b_ten, nhom_ap = PHEP[phep]
    theo: dict[tuple, dict] = {}
    for r in dong:
        if r["nhom"] in nhom_ap and r["bien_the"] in ("A", b_ten) and r.get("dung") is not None:
            theo.setdefault((r["ma"], r["lan"]), {})[r["bien_the"]] = r
    cap = [(v["A"], v[b_ten]) for v in theo.values() if "A" in v and b_ten in v]
    b = sum(1 for a, x in cap if x["dung"] and not a["dung"])
    c = sum(1 for a, x in cap if a["dung"] and not x["dung"])
    p = mcnemar_p(b, c)
    nhom = {}
    tut_nhom = False
    for g in nhom_ap:
        ca = [(a, x) for a, x in cap if a["nhom"] == g]
        if not ca:
            continue
        da, dx = sum(a["dung"] for a, _ in ca), sum(x["dung"] for _, x in ca)
        thap_a, _ = wilson(da, len(ca))
        tut = dx / len(ca) < thap_a
        tut_nhom |= tut
        nhom[g] = {"A": f"{da}/{len(ca)}", b_ten: f"{dx}/{len(ca)}", "tut_duoi_wilson_A": tut}

    def phu(bt: str) -> dict:
        rs = [x if bt == b_ten else a for a, x in cap]
        return {"rong": sum(1 for r in rs if r.get("rong")), "lap": sum(1 for r in rs if r.get("lap")),
                "token_ra_p50": int(statistics.median([r.get("token_ra") or 0 for r in rs] or [0])),
                "giay_p50": round(statistics.median([r.get("giay") or 0 for r in rs] or [0]), 1),
                "prompt_tong": sum(r.get("prompt_n") or 0 for r in rs),
                "ti_le_cache": round(sum(r.get("cache_n") or 0 for r in rs)
                                     / max(1, sum(r.get("prompt_n") or 0 for r in rs)), 3)}

    tong_a = sum(a["dung"] for a, _ in cap)
    tong_b = sum(x["dung"] for _, x in cap)
    return {"phep": phep, "B": b_ten, "cap": len(cap), "A_dung": tong_a, "B_dung": tong_b,
            "chi_B_dung": b, "chi_A_dung": c, "p_mcnemar": round(p, 4), "nhom": nhom,
            "B_thang_ro": b > c and p < 0.05 and not tut_nhom,
            "B_khong_tut": not (c > b and p < 0.05), "phu_A": phu("A"), f"phu_{b_ten}": phu(b_ten)}


# ── Chạy ─────────────────────────────────────────────────────────────────────

def _goi(base: str, than: dict, timeout: float) -> dict:
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(than).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "ltt-ab35/1.0"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"status": e.code, "giay": time.monotonic() - t0, "loi": e.read()[:300].decode("utf-8", "replace")}
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"status": 0, "giay": time.monotonic() - t0, "loi": f"{type(e).__name__}: {e}"}
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    us = d.get("usage") or {}
    tm = d.get("timings") or {}
    cache = int(tm.get("cache_n") or 0)
    return {"status": 200, "giay": time.monotonic() - t0, "text": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "", "tool_calls": msg.get("tool_calls") or [],
            "finish": ch.get("finish_reason"), "token_ra": us.get("completion_tokens"),
            "prompt_n": int(tm.get("prompt_n") or 0) + cache, "cache_n": cache}


def _chay_agent(base: str, kb_i: int, them: dict, timeout: float, system_them: str = "") -> dict:
    """Kịch bản nhiều lượt của `ab_lich_su_suy_nghi` (đọc → sửa → chạy test), không stream, có biến thể."""
    from tools import ab_lich_su_suy_nghi as H
    kb = H._kich_ban(kb_i)
    he = (system_them + "\n\n" + H.HE_THONG) if system_them else H.HE_THONG
    lich_su = [{"role": "system", "content": he}, {"role": "user", "content": kb["nhac"]}]
    luot, giay, token, text_all, rong = [], 0.0, 0, "", False
    prompt_n, cache_n = [], []
    for buoc in range(len(kb["ky_vong"])):
        r = _goi(base, {"model": MODEL, "messages": lich_su, "tools": H.TOOLS, "max_tokens": MAX_TOKENS, **them},
                 timeout)
        giay += r.get("giay", 0)
        if r["status"] != 200:
            return {"status": r["status"], "loi": r.get("loi"), "giay": giay}
        token += r.get("token_ra") or 0
        prompt_n.append(r.get("prompt_n") or 0)
        cache_n.append(r.get("cache_n") or 0)
        text_all += r.get("text") or ""
        goi = [{"id": c.get("id") or f"c{buoc}", "name": (c.get("function") or {}).get("name", ""),
                "arguments": _args(c)} for c in r["tool_calls"]]
        luot.append({"tool_calls": goi})
        if not goi:
            rong = not (r.get("text") or "").strip()
            break
        # ⭐ Như client thật (và như `ab_lich_su_suy_nghi`): giữ `reasoning_content` của lượt trước — nhờ
        #    vậy `preserve_thinking` (R-17) mới có gì để giữ/bỏ.
        lich_su.append({"role": "assistant", "content": r["text"], "reasoning_content": r.get("reasoning") or "",
                        "tool_calls": [{"id": goi[0]["id"], "type": "function", "function": {
                            "name": goi[0]["name"], "arguments": json.dumps(goi[0]["arguments"])}}]})
        kq = kb["noi_dung"] if goi[0]["name"] == "read_file" else H.KET_QUA_TOOL.get(goi[0]["name"], "error")
        lich_su.append({"role": "tool", "tool_call_id": goi[0]["id"], "content": kq})
    dung, tong = H.cham_tool(luot, kb["ky_vong"])
    return {"status": 200, "giay": giay, "token_ra": token, "text": text_all, "dung": dung == tong,
            "diem": f"{dung}/{tong}", "rong": rong, "prompt_n": sum(prompt_n), "cache_n": sum(cache_n),
            "ctx_luot": prompt_n}


def mot_luot(base: str, bai: dict, bien_the: str, timeout: float) -> dict:
    them = dict(BIEN_THE[bien_the])
    ten_sys = them.pop("_system", None)
    system_them = SYSTEM_NGOAI[ten_sys] if ten_sys else ""
    if bai["nhom"] == "agent":
        r = _chay_agent(base, bai["kich_ban"], them, timeout, system_them)
    else:
        tin = [{"role": "user", "content": bai["nhac"]}]
        if system_them:
            tin.insert(0, {"role": "system", "content": system_them})
        than = {"model": MODEL, "max_tokens": MAX_TOKENS, **them, "messages": tin}
        if bai["nhom"] == "tool":
            than["tools"] = TOOLS_1
        r = _goi(base, than, timeout)
        if r["status"] == 200:
            t = r.get("text") or ""
            r["dung"] = (cham_code(bai, t) if bai["nhom"] == "code" else cham_vi(bai, t) if bai["nhom"] == "vi"
                         else cham_tool(bai, t, r.get("tool_calls") or []))
            r["rong"] = not t.strip() and not r.get("tool_calls")
    if r["status"] != 200:
        r["dung"] = None
    r["lap"] = co_lap((r.get("text") or "") + (r.get("reasoning") or ""))
    return r


def viec_can_chay(lan: int) -> list[tuple[dict, int, str]]:
    """(bài, lượt, biến thể) — A cho mọi bài; B của mỗi phép chỉ trên nhóm của phép đó. Xen kẽ theo cặp."""
    viec = []
    for i in range(lan):
        for bai in bo_de():
            viec.append((bai, i, "A"))
            for _phep, (b, nhom) in PHEP.items():
                if bai["nhom"] in nhom:
                    viec.append((bai, i, b))
    return viec


def chay(base: str, lan: int, ra: pathlib.Path, song_song: int, timeout: float, bo_qua: set | None = None) -> None:
    ra.parent.mkdir(parents=True, exist_ok=True)
    khoa = threading.Lock()
    viec = [v for v in viec_can_chay(lan) if (v[0]["ma"], v[1], v[2]) not in (bo_qua or set())]

    def mot(v):
        bai, i, bt = v
        r = mot_luot(base, bai, bt, timeout)
        dong = {"ma": bai["ma"], "nhom": bai["nhom"], "lan": i, "bien_the": bt, "dung": r.get("dung"),
                "status": r.get("status"), "finish": r.get("finish"), "token_ra": r.get("token_ra"),
                "giay": round(r.get("giay", 0), 1), "rong": r.get("rong"), "lap": r.get("lap"),
                "reasoning_ky_tu": len(r.get("reasoning") or ""), "text_dau": (r.get("text") or "")[:200],
                "loi": r.get("loi"), "diem": r.get("diem"), "prompt_n": r.get("prompt_n"),
                "cache_n": r.get("cache_n")}
        with khoa:
            with ra.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            print(f"{bai['ma']} #{i} {bt:>6} dung={dong['dung']} {dong['giay']}s tok={dong['token_ra']}", flush=True)

    with ThreadPoolExecutor(max_workers=song_song) as ex:
        list(ex.map(mot, viec))


def doc(ra: pathlib.Path) -> list[dict]:
    return [json.loads(x) for x in ra.read_text(encoding="utf-8").splitlines() if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="lenh", required=True)
    c = sub.add_parser("chay")
    c.add_argument("--base", default="http://127.0.0.1:18280")
    c.add_argument("--lan", type=int, default=3)
    c.add_argument("--song-song", type=int, default=2)
    c.add_argument("--timeout", type=float, default=900)
    c.add_argument("--ra", required=True, type=pathlib.Path)
    c.add_argument("--codex-prompt", type=pathlib.Path,
                   help="tệp base instructions mặc định của Codex; vắng ⇒ bỏ phép codex_instr")
    c.add_argument("--chi-phep", default="", help="danh sách phép, phẩy (mặc định: mọi phép)")
    s = sub.add_parser("so-sanh")
    s.add_argument("tep", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.lenh == "chay":
        da_co = {(r["ma"], r["lan"], r["bien_the"]) for r in doc(a.ra) if r.get("status") == 200} \
            if a.ra.exists() else set()
        if a.codex_prompt:
            SYSTEM_NGOAI["codex"] = a.codex_prompt.read_text(encoding="utf-8")
        else:
            PHEP.pop("codex_instr", None)
        if a.chi_phep:
            for k in [k for k in PHEP if k not in a.chi_phep.split(",")]:
                PHEP.pop(k)
        chay(a.base, a.lan, a.ra, a.song_song, a.timeout, da_co)
        return 0
    dong = doc(a.tep)
    print(json.dumps([phan_quyet(dong, p) for p in PHEP], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
