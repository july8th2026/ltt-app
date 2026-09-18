"""R-17 (18/09 toi): A/B `preserve_reasoning` tren hoi thoai NHIEU TIN USER (>= 4) cho LTT-3.5. Do thang engine.

    python ab_nhieu_luot_35.py tu-kiem                      # cham loi giai tham chieu -> phai dat het
    python ab_nhieu_luot_35.py kiem-template --base http://127.0.0.1:18381
    python ab_nhieu_luot_35.py chay --base http://127.0.0.1:18381 --lan 3 --song-song 3 --ra r17.jsonl
    python ab_nhieu_luot_35.py so-sanh r17.jsonl

Vi sao can bo moi: A/B cua `ab_lay_mau_35.py` (nhanh phien/kiem-dinh-ky) chi co kich ban agent MOT tin user;
template v22.5 giu suy nghi cua moi luot assistant SAU tin user cuoi bat ke co ⇒ co `preserve_reasoning`
chi co tac dung tu tin user thu hai. Bo nay: 4 hoi thoai lap trinh + 4 hoi thoai tieng Viet, moi hoi thoai
4-5 tin user NOI TIEP (luot sau dua vao ket qua luot truoc), moi luot cham tat dinh (ma: CHAY THAT; so/JSON/chuoi).

Bien the (mot bien, theo request, KHONG nap lai model):
  A  : khong gui gi  ⇒ template mac dinh `preserve_reasoning=true` (llama.cpp common/arg.cpp tu nap) = production
  B  : `chat_template_kwargs.preserve_reasoning=false` ⇒ bo khoi suy nghi cua cac luot assistant TRUOC tin user cuoi
       (tuong duong co engine `--no-reasoning-preserve`, cung mot kwarg cua template).
Client giu `reasoning_content` trong lich su nhu client that (Claude Code/Codex) — template quyet giu/bo.
Moi hoi thoai co nonce o DAU system ⇒ khong hai hoi thoai nao dung chung cache tien to (A khong "moi" cache cho B).

Luat quyet (khoa TRUOC khi do; giong ab_lay_mau_35):
  cap = (hoi thoai, luot user, lan). McNemar chinh xac tren cap bat dong. `B_thang_ro` <=> b > c, p < 0,05, khong
  nhom nao cua B duoi can duoi Wilson 95 % cua A. `B_khong_tut` <=> khong (c > b va p < 0,05).
  Phu: dung CA hoi thoai, token prompt (tong/luot cuoi), ti le trung cache = cache_n / (prompt_n + cache_n), giay.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "qwen35-api"
MAX_TOKENS = 8192
BIEN_THE = {"A": {}, "B": {"chat_template_kwargs": {"preserve_reasoning": False}}}
HE_THONG = "Bạn là trợ lý lập trình và tính toán. Trả lời chính xác, ngắn gọn, đúng định dạng người dùng yêu cầu."
MA_DUOI = "\nTrả về TOÀN BỘ mã (gồm cả các hàm/lớp đã viết ở các lượt trước) trong MỘT khối ```python ... ```, không giải thích."

_NEM = ("def _nem(f):\n    try:\n        f()\n    except ValueError:\n        return True\n    except Exception:\n"
        "        return False\n    return False\n")

# ── Bo de (khoa truoc khi do) ────────────────────────────────────────────────
# moi luot: {"nhac", va MOT trong: "kiem" (list (bieu thuc, ky vong)) | "so" | "chua" | "json" | "ba_cau"}
HOI_THOAI = [
    {"ma": "k1", "nhom": "code", "luot": [
        {"nhac": "Viết hàm Python `slugify(s)`: chuyển thành chữ thường, thay mọi chuỗi ký tự không thuộc a-z0-9 bằng "
                 "đúng một dấu '-', bỏ '-' ở đầu và cuối.",
         "kiem": [("slugify('Hello, World!')", "hello-world"), ("slugify('  a--b  ')", "a-b"), ("slugify('ABC123')", "abc123")]},
        {"nhac": "Sửa `slugify` để bỏ dấu tiếng Việt trước khi xử lý (ví dụ 'Đà Nẵng' -> 'da-nang', "
                 "'Tiếng Việt có dấu!' -> 'tieng-viet-co-dau'). Các hành vi cũ giữ nguyên.",
         "kiem": [("slugify('Đà Nẵng')", "da-nang"), ("slugify('Tiếng Việt có dấu!')", "tieng-viet-co-dau"),
                  ("slugify('Hello, World!')", "hello-world"), ("slugify('Ưu đãi Đặc biệt')", "uu-dai-dac-biet")]},
        {"nhac": "Thêm tham số tuỳ chọn `max_len=None` cho `slugify`: nếu có, cắt slug còn tối đa max_len ký tự rồi bỏ "
                 "'-' thừa ở cuối sau khi cắt.",
         "kiem": [("slugify('hello world foo', max_len=8)", "hello-wo"), ("slugify('hello world', max_len=6)", "hello"),
                  ("slugify('Đà Nẵng')", "da-nang"), ("slugify('Đà Nẵng', max_len=3)", "da")]},
        {"nhac": "Viết thêm `unique_slug(s, existing)` dùng `slugify` ở trên: nếu slug đã có trong tập `existing` thì "
                 "thêm hậu tố -2, -3, ... nhỏ nhất chưa có trong tập.",
         "kiem": [("unique_slug('Đà Nẵng', {'da-nang'})", "da-nang-2"), ("unique_slug('A', {'a', 'a-2'})", "a-3"),
                  ("unique_slug('x', set())", "x"), ("slugify('hello world', max_len=6)", "hello")]},
    ]},
    {"ma": "k2", "nhom": "code", "luot": [
        {"nhac": "Viết class Python `Kho` quản lý tồn kho: `nhap(ma, sl)` cộng số lượng, `xuat(ma, sl)` trừ số lượng và "
                 "ném ValueError nếu không đủ hàng (không đổi tồn), `ton(ma)` trả số lượng hiện có (0 nếu chưa có).",
         "kiem": [("(lambda k: (k.nhap('a', 5), k.xuat('a', 2), k.ton('a'))[2])(Kho())", 3), ("Kho().ton('b')", 0),
                  ("(lambda k: (k.nhap('a', 1), _nem(lambda: k.xuat('a', 2)), k.ton('a'))[1:])(Kho())", (True, 1))]},
        {"nhac": "Thêm phương thức `lich_su(ma)` trả list các tuple ('nhap' hoặc 'xuat', sl) theo đúng thứ tự thao tác "
                 "THÀNH CÔNG trên mã đó.",
         "kiem": [("(lambda k: (k.nhap('a', 5), k.xuat('a', 2), k.nhap('b', 1), k.lich_su('a'))[3])(Kho())",
                   [("nhap", 5), ("xuat", 2)]),
                  ("(lambda k: (k.nhap('a', 1), _nem(lambda: k.xuat('a', 9)), k.lich_su('a'))[2])(Kho())", [("nhap", 1)]),
                  ("Kho().lich_su('z')", [])]},
        {"nhac": "Thêm `hoan_tac()`: huỷ thao tác nhập/xuất thành công gần nhất (trên mọi mã), khôi phục tồn và xoá mục "
                 "đó khỏi lịch sử; trả True nếu có gì để huỷ, False nếu không.",
         "kiem": [("(lambda k: (k.nhap('a', 5), k.xuat('a', 2), k.hoan_tac(), k.ton('a'), k.lich_su('a'))[2:])(Kho())",
                   (True, 5, [("nhap", 5)])),
                  ("Kho().hoan_tac()", False),
                  ("(lambda k: (k.nhap('a', 5), k.nhap('b', 3), k.hoan_tac(), k.ton('b'), k.ton('a'))[3:])(Kho())", (0, 5))]},
        {"nhac": "Thêm `bao_cao()` trả dict {ma: ton} chỉ gồm các mã có tồn > 0, khoá theo thứ tự mã tăng dần.",
         "kiem": [("(lambda k: (k.nhap('b', 2), k.nhap('a', 1), k.nhap('c', 4), k.xuat('c', 4), list(k.bao_cao().items()))[4])(Kho())",
                   [("a", 1), ("b", 2)]),
                  ("(lambda k: (k.nhap('a', 5), k.hoan_tac(), k.bao_cao())[2])(Kho())", {})]},
    ]},
    {"ma": "k3", "nhom": "code", "luot": [
        {"nhac": "Viết `parse_line(line)` phân tích dòng log dạng '2026-09-18 10:15:02 ERROR [api] Timeout sau 30s' thành "
                 "dict {'ngay': '2026-09-18', 'gio': '10:15:02', 'muc': 'ERROR', 'module': 'api', 'tin': 'Timeout sau 30s'}. "
                 "Mức là một trong INFO, WARN, ERROR. Dòng sai định dạng trả None.",
         "kiem": [("parse_line('2026-09-18 10:15:02 ERROR [api] Timeout sau 30s')",
                   {"ngay": "2026-09-18", "gio": "10:15:02", "muc": "ERROR", "module": "api", "tin": "Timeout sau 30s"}),
                  ("parse_line('rac')", None), ("parse_line('2026-09-18 10:15:02 DEBUG [api] x')", None),
                  ("parse_line('2026-01-02 00:00:00 INFO [db] ok')['module']", "db")]},
        {"nhac": "Viết `dem_theo_muc(lines)` dùng `parse_line`, trả dict {muc: số dòng hợp lệ}, bỏ qua dòng hỏng.",
         "kiem": [("dem_theo_muc(['2026-09-18 10:15:02 ERROR [api] a', 'x', '2026-09-18 10:15:03 INFO [db] b', "
                   "'2026-09-18 10:15:04 ERROR [db] c'])", {"ERROR": 2, "INFO": 1}), ("dem_theo_muc([])", {})]},
        {"nhac": "Viết `loi_theo_module(lines, muc='ERROR')` trả list tuple (module, số lần) của các dòng có mức `muc`, "
                 "sắp theo số lần giảm dần rồi tên module tăng dần.",
         "kiem": [("loi_theo_module(['2026-09-18 10:00:00 ERROR [db] a', '2026-09-18 10:00:01 ERROR [api] b', "
                   "'2026-09-18 10:00:02 ERROR [db] c', '2026-09-18 10:00:03 INFO [api] d', '2026-09-18 10:00:04 ERROR [auth] e'])",
                   [("db", 2), ("api", 1), ("auth", 1)]),
                  ("loi_theo_module(['2026-09-18 10:00:03 INFO [api] d'], muc='INFO')", [("api", 1)])]},
        {"nhac": "Sửa `parse_line` để chấp nhận thêm mức viết 'WARNING' và chuẩn hoá nó về 'WARN'; các hàm khác giữ nguyên.",
         "kiem": [("parse_line('2026-09-18 10:15:02 WARNING [api] x')['muc']", "WARN"),
                  ("dem_theo_muc(['2026-09-18 10:15:02 WARNING [api] x', '2026-09-18 10:15:02 WARN [db] y'])", {"WARN": 2}),
                  ("parse_line('rac')", None), ("parse_line('2026-09-18 10:15:02 DEBUG [api] x')", None)]},
    ]},
    {"ma": "k4", "nhom": "code", "luot": [
        {"nhac": "Viết `nhan_ma_tran(a, b)` nhân hai ma trận cho dưới dạng list các list số nguyên; ném ValueError nếu "
                 "số cột của a khác số hàng của b.",
         "kiem": [("nhan_ma_tran([[1, 2], [3, 4]], [[5, 6], [7, 8]])", [[19, 22], [43, 50]]),
                  ("nhan_ma_tran([[1, 2, 3]], [[1], [2], [3]])", [[14]]),
                  ("_nem(lambda: nhan_ma_tran([[1, 2]], [[1, 2]]))", True)]},
        {"nhac": "Viết `luy_thua(m, k)` tính m^k (m vuông, k >= 0) bằng bình phương liên tiếp, dùng `nhan_ma_tran`; k = 0 "
                 "trả ma trận đơn vị cùng cỡ.",
         "kiem": [("luy_thua([[1, 1], [1, 0]], 5)", [[8, 5], [5, 3]]), ("luy_thua([[2, 0], [0, 3]], 0)", [[1, 0], [0, 1]]),
                  ("luy_thua([[2]], 10)", [[1024]])]},
        {"nhac": "Dùng `luy_thua` viết `fib(n)` trả số Fibonacci thứ n (fib(0) = 0, fib(1) = 1).",
         "kiem": [("fib(0)", 0), ("fib(1)", 1), ("fib(10)", 55), ("fib(90)", 2880067194370816120)]},
        {"nhac": "Viết `fib_mod(n, m)` trả fib(n) mod m, lấy dư m ở MỖI phép nhân (thêm tham số `mod=None` tuỳ chọn cho "
                 "`nhan_ma_tran` và `luy_thua` nếu cần) để chạy nhanh với n = 10**18. `fib` cũ vẫn phải đúng.",
         "kiem": [("fib_mod(10, 1000)", 55), ("fib_mod(10**18, 10**9 + 7)", 209783453), ("fib_mod(90, 10**9 + 7)", 210345902),
                  ("fib(10)", 55)]},
    ]},
    {"ma": "v1", "nhom": "vi", "luot": [
        {"nhac": "Một cửa hàng có 240 kg gạo. Ngày đầu bán 1/4 số gạo. Ngày đầu bán bao nhiêu kg? Chỉ trả lời bằng con số.", "so": 60},
        {"nhac": "Giá gạo là 18.000 đồng/kg. Ngày đầu thu được bao nhiêu đồng? Chỉ trả lời bằng con số.", "so": 1080000},
        {"nhac": "Ngày thứ hai bán 30% số gạo còn lại sau ngày đầu. Sau hai ngày cửa hàng còn bao nhiêu kg? Chỉ trả lời bằng con số.", "so": 126},
        {"nhac": "Ngày thứ hai giá giảm 2.000 đồng/kg so với ngày đầu. Tổng tiền thu được trong hai ngày là bao nhiêu đồng? "
                 "Chỉ trả lời bằng con số.", "so": 1944000},
        {"nhac": "Trả về DUY NHẤT một đối tượng JSON với các khoá ngay1_kg, ngay2_kg, con_lai_kg, tong_tien (số nguyên).",
         "json": {"ngay1_kg": 60, "ngay2_kg": 54, "con_lai_kg": 126, "tong_tien": 1944000}},
    ]},
    {"ma": "v2", "nhom": "vi", "luot": [
        {"nhac": "Tàu khởi hành từ Hà Nội lúc 19 giờ 30 phút, chạy 11 giờ 45 phút thì tới Huế. Tàu tới Huế lúc mấy giờ? "
                 "Trả lời theo định dạng HH:MM (24 giờ), không thêm gì khác.", "chua": ["07:15"]},
        {"nhac": "Ở Huế tàu dừng 25 phút rồi chạy tiếp 2 giờ 50 phút tới Đà Nẵng. Tàu tới Đà Nẵng lúc mấy giờ? "
                 "Trả lời theo định dạng HH:MM, không thêm gì khác.", "chua": ["10:30"]},
        {"nhac": "Vé Hà Nội–Huế 650.000 đồng/người, Huế–Đà Nẵng 120.000 đồng/người; trẻ em giảm 25% giá vé. Gia đình 2 người "
                 "lớn và 1 trẻ em đi từ Hà Nội tới Đà Nẵng hết bao nhiêu đồng? Chỉ trả lời bằng con số.", "so": 2117500},
        {"nhac": "Nếu mua vé trước 30 ngày thì được giảm thêm 10% trên tổng tiền đó. Gia đình phải trả bao nhiêu đồng? "
                 "Chỉ trả lời bằng con số.", "so": 1905750},
        {"nhac": "Viết đúng 3 câu tiếng Việt có dấu tóm tắt chuyến đi, trong đó có giờ tới Đà Nẵng (HH:MM) và số tiền cuối "
                 "cùng gia đình trả. Mỗi câu kết thúc bằng dấu chấm, không tiêu đề, không gạch đầu dòng.",
         "ba_cau": True, "chua": ["10:30"], "so_co": 1905750},
    ]},
    {"ma": "v3", "nhom": "vi", "luot": [
        {"nhac": "Danh sách: 'Nguyễn Văn An - 1990 - Hà Nội; Trần Thị Bình - 1985 - Huế; Lê Văn Cường - 2001 - Cần Thơ; "
                 "Phạm Thị Dung - 1995 - Hà Nội; Hoàng Minh Em - 1979 - Đà Nẵng'. Có bao nhiêu người ở Hà Nội? "
                 "Chỉ trả lời bằng con số.", "so": 2},
        {"nhac": "Ai lớn tuổi nhất trong danh sách? Chỉ trả lời họ tên đầy đủ.", "chua": ["hoàng minh em"]},
        {"nhac": "Trả về DUY NHẤT một mảng JSON các họ tên, sắp theo năm sinh tăng dần.",
         "json": ["Hoàng Minh Em", "Trần Thị Bình", "Nguyễn Văn An", "Phạm Thị Dung", "Lê Văn Cường"]},
        {"nhac": "Tính tuổi trung bình vào năm 2026 của những người sinh sau năm 1988, làm tròn tới hàng đơn vị. "
                 "Chỉ trả lời bằng con số.", "so": 31},
    ]},
    {"ma": "v4", "nhom": "vi", "luot": [
        {"nhac": "Công thức bánh cho 4 người cần 300 g bột, 2 quả trứng và 250 ml sữa. Làm cho 10 người cần bao nhiêu gam "
                 "bột? Chỉ trả lời bằng con số.", "so": 750},
        {"nhac": "Vẫn cho 10 người, cần bao nhiêu quả trứng (làm tròn lên)? Chỉ trả lời bằng con số.", "so": 5},
        {"nhac": "Sữa bán theo hộp 180 ml. Cần mua ít nhất bao nhiêu hộp sữa cho 10 người? Chỉ trả lời bằng con số.", "so": 4},
        {"nhac": "Bột giá 32.000 đồng/kg (mua lẻ đúng số gam cần), trứng 3.500 đồng/quả, sữa 8.000 đồng/hộp. Tổng chi phí "
                 "nguyên liệu cho 10 người là bao nhiêu đồng? Chỉ trả lời bằng con số.", "so": 73500},
        {"nhac": "Trả về DUY NHẤT một đối tượng JSON với các khoá bot_g, trung, hop_sua, chi_phi (số nguyên).",
         "json": {"bot_g": 750, "trung": 5, "hop_sua": 4, "chi_phi": 73500}},
    ]},
]

for _h in HOI_THOAI:
    if _h["nhom"] == "code":
        for _l in _h["luot"]:
            _l["nhac"] += MA_DUOI

# loi giai tham chieu cho `tu-kiem` (moi luot) — bat de sai truoc khi do
THAM_CHIEU_MA = {
    "k1": ["""
import re, unicodedata
def slugify(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower())
    return s.strip('-')
""", """
import re, unicodedata
def slugify(s):
    s = s.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', '-', s.lower())
    return s.strip('-')
""", """
import re, unicodedata
def slugify(s, max_len=None):
    s = s.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    if max_len is not None:
        s = s[:max_len].rstrip('-')
    return s
""", """
import re, unicodedata
def slugify(s, max_len=None):
    s = s.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    if max_len is not None:
        s = s[:max_len].rstrip('-')
    return s
def unique_slug(s, existing):
    b = slugify(s)
    if b not in existing:
        return b
    i = 2
    while f'{b}-{i}' in existing:
        i += 1
    return f'{b}-{i}'
"""],
    "k2": [None, None, None, """
class Kho:
    def __init__(self):
        self.t = {}; self.h = []
    def nhap(self, ma, sl):
        self.t[ma] = self.t.get(ma, 0) + sl; self.h.append((ma, 'nhap', sl))
    def xuat(self, ma, sl):
        if self.t.get(ma, 0) < sl:
            raise ValueError('khong du')
        self.t[ma] -= sl; self.h.append((ma, 'xuat', sl))
    def ton(self, ma):
        return self.t.get(ma, 0)
    def lich_su(self, ma):
        return [(k, s) for m, k, s in self.h if m == ma]
    def hoan_tac(self):
        if not self.h:
            return False
        m, k, s = self.h.pop()
        self.t[m] += -s if k == 'nhap' else s
        return True
    def bao_cao(self):
        return {m: v for m, v in sorted(self.t.items()) if v > 0}
"""],
    "k3": [None, None, None, """
import re
_R = re.compile(r'^(\\d{4}-\\d{2}-\\d{2}) (\\d{2}:\\d{2}:\\d{2}) (INFO|WARN|WARNING|ERROR) \\[([^\\]]+)\\] (.*)$')
def parse_line(line):
    m = _R.match(line)
    if not m:
        return None
    muc = 'WARN' if m.group(3) == 'WARNING' else m.group(3)
    return {'ngay': m.group(1), 'gio': m.group(2), 'muc': muc, 'module': m.group(4), 'tin': m.group(5)}
def dem_theo_muc(lines):
    d = {}
    for l in lines:
        p = parse_line(l)
        if p:
            d[p['muc']] = d.get(p['muc'], 0) + 1
    return d
def loi_theo_module(lines, muc='ERROR'):
    d = {}
    for l in lines:
        p = parse_line(l)
        if p and p['muc'] == muc:
            d[p['module']] = d.get(p['module'], 0) + 1
    return sorted(d.items(), key=lambda x: (-x[1], x[0]))
"""],
    "k4": [None, None, None, """
def nhan_ma_tran(a, b, mod=None):
    if len(a[0]) != len(b):
        raise ValueError('kich thuoc')
    r = [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]
    return [[x % mod for x in h] for h in r] if mod else r
def luy_thua(m, k, mod=None):
    n = len(m)
    r = [[int(i == j) for j in range(n)] for i in range(n)]
    while k:
        if k & 1:
            r = nhan_ma_tran(r, m, mod)
        m = nhan_ma_tran(m, m, mod)
        k >>= 1
    return r
def fib(n):
    return luy_thua([[1, 1], [1, 0]], n)[0][1]
def fib_mod(n, m):
    return luy_thua([[1, 1], [1, 0]], n, m)[0][1]
"""],
}
THAM_CHIEU_CHU = {
    "v1": ["60", "1.080.000", "126", "1.944.000",
           '{"ngay1_kg": 60, "ngay2_kg": 54, "con_lai_kg": 126, "tong_tien": 1944000}'],
    "v2": ["07:15", "10:30", "2.117.500", "1.905.750",
           "Gia đình đi tàu từ Hà Nội lúc tối. Tàu tới Đà Nẵng lúc 10:30 sáng hôm sau. Tổng số tiền cuối cùng phải trả "
           "là 1.905.750 đồng."],
    "v3": ["2", "Hoàng Minh Em", '["Hoàng Minh Em", "Trần Thị Bình", "Nguyễn Văn An", "Phạm Thị Dung", "Lê Văn Cường"]', "31"],
    "v4": ["750", "5", "4", "73.500", '{"bot_g": 750, "trung": 5, "hop_sua": 4, "chi_phi": 73500}'],
}

# ── Cham ─────────────────────────────────────────────────────────────────────
_DAU_VIET = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
_LAP = re.compile(r"(.{8,}?)\1{6,}", re.S)


def _khoi_ma(van: str) -> str:
    m = re.findall(r"```(?:python|py)?\s*\n(.*?)```", van, re.S)
    return max(m, key=len) if m else ""


def _so_trong(text: str) -> list[int]:
    return [int(re.sub(r"[.,\s]", "", x)) for x in re.findall(r"\d{1,3}(?:[.,]\d{3})+(?!\d)|\d+", text or "")]


def cham(luot: dict, text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if "kiem" in luot:
        ma = _khoi_ma(t)
        if not ma.strip():
            return False
        kiem = "\n".join(f"assert ({bt}) == ({kq!r}), {bt!r}" for bt, kq in luot["kiem"])
        with tempfile.TemporaryDirectory() as tm:
            f = pathlib.Path(tm) / "thu.py"
            f.write_text(_NEM + "\n" + ma + "\n\n" + kiem + "\nprint('DAT')\n", encoding="utf-8")
            try:
                r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, timeout=20, cwd=tm,
                                   encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                return False
        return r.returncode == 0 and "DAT" in r.stdout
    if "json" in luot:
        m = re.search(r"[\[{].*[\]}]", t, re.S)
        try:
            d = json.loads(m.group(0)) if m else None
        except ValueError:
            return False
        return d == luot["json"]
    ok = True
    if luot.get("ba_cau"):
        cau = [c for c in re.split(r"(?<=\.)\s+", t) if c.strip()]
        ok = len(cau) == 3 and all(c.rstrip().endswith(".") for c in cau) and len(_DAU_VIET.findall(t)) >= 10
    if "so_co" in luot:
        ok = ok and luot["so_co"] in _so_trong(t)
    if "so" in luot:
        so = _so_trong(t)
        ok = ok and bool(so) and so[-1] == luot["so"]
    if "chua" in luot:
        ok = ok and any(c in t.lower() for c in luot["chua"])
    return ok


def tu_kiem() -> int:
    loi = 0
    for h in HOI_THOAI:
        for i, l in enumerate(h["luot"]):
            if h["nhom"] == "code":
                ref = THAM_CHIEU_MA[h["ma"]]
                code = ref[i] if ref[i] is not None else ref[-1]
                text = "```python\n" + code + "\n```"
            else:
                text = THAM_CHIEU_CHU[h["ma"]][i]
            ok = cham(l, text)
            loi += int(not ok)
            print(h["ma"], i + 1, "DAT" if ok else "TRUOT")
        # de sai phai truot: rong va sai hien nhien
        assert not cham(h["luot"][0], ""), h["ma"]
    print("tu-kiem:", "DAT" if loi == 0 else f"{loi} TRUOT")
    return 1 if loi else 0


# ── Chay ─────────────────────────────────────────────────────────────────────

def _goi(base: str, than: dict, timeout: float) -> dict:
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions", data=json.dumps(than).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json", "User-Agent": "ltt-r17/1.0"})
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
    tm = d.get("timings") or {}
    return {"status": 200, "giay": time.monotonic() - t0, "text": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "", "finish": ch.get("finish_reason"),
            "token_ra": (d.get("usage") or {}).get("completion_tokens"),
            "prompt_moi": int(tm.get("prompt_n") or 0), "cache_n": int(tm.get("cache_n") or 0),
            "prompt_ms": tm.get("prompt_ms")}


def mot_hoi_thoai(base: str, h: dict, lan: int, bt: str, timeout: float, ra: pathlib.Path, khoa) -> None:
    nonce = "%d-%d" % (time.time_ns(), random.SystemRandom().randint(0, 10**9))
    tin = [{"role": "system", "content": f"Phiên {nonce}.\n{HE_THONG}"}]
    for i, l in enumerate(h["luot"]):
        tin.append({"role": "user", "content": l["nhac"]})
        r = _goi(base, {"model": MODEL, "messages": tin, "max_tokens": MAX_TOKENS, **BIEN_THE[bt]}, timeout)
        dung = cham(l, r.get("text")) if r["status"] == 200 else None
        dong = {"ma": h["ma"], "nhom": h["nhom"], "luot": i + 1, "lan": lan, "bien_the": bt, "dung": dung,
                "status": r["status"], "finish": r.get("finish"), "token_ra": r.get("token_ra"),
                "prompt_moi": r.get("prompt_moi"), "cache_n": r.get("cache_n"),
                "prompt_tong": (r.get("prompt_moi") or 0) + (r.get("cache_n") or 0), "prompt_ms": r.get("prompt_ms"),
                "giay": round(r.get("giay", 0), 1), "rong": r["status"] == 200 and not (r.get("text") or "").strip(),
                "lap": bool(_LAP.search((r.get("text") or "") + (r.get("reasoning") or ""))),
                "reasoning_ky_tu": len(r.get("reasoning") or ""), "text_dau": (r.get("text") or "")[:160],
                "loi": r.get("loi")}
        with khoa:
            with ra.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            print(f"{h['ma']} L{i + 1} #{lan} {bt} dung={dung} {dong['giay']}s ra={dong['token_ra']} "
                  f"prompt={dong['prompt_tong']} cache={dong['cache_n']}", flush=True)
        if r["status"] != 200:
            return
        # nhu client that: giu reasoning_content cua luot truoc — template quyet giu/bo
        tin.append({"role": "assistant", "content": r.get("text") or "", "reasoning_content": r.get("reasoning") or ""})


def chay(base: str, lan: int, song_song: int, ra: pathlib.Path, timeout: float) -> None:
    ra.parent.mkdir(parents=True, exist_ok=True)
    khoa = threading.Lock()
    viec = []
    for i in range(lan):
        for h in HOI_THOAI:
            ab = ["A", "B"] if (i + len(viec)) % 2 == 0 else ["B", "A"]  # xen ke thu tu, khong de A luon di truoc
            viec += [(h, i, bt) for bt in ab]
    with ThreadPoolExecutor(max_workers=song_song) as ex:
        list(ex.map(lambda v: mot_hoi_thoai(base, v[0], v[1], v[2], timeout, ra, khoa), viec))


def kiem_template(base: str) -> None:
    """Xac minh bien the B co tac dung o lich su NHIEU tin user (va A = mac dinh giu)."""
    tin = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u1"},
           {"role": "assistant", "content": "tra loi 1", "reasoning_content": "SUY_NGHI_CU " * 20},
           {"role": "user", "content": "u2"}]
    for bt, them in BIEN_THE.items():
        req = urllib.request.Request(base.rstrip("/") + f"/upstream/{MODEL}/apply-template",
                                     data=json.dumps({"messages": tin, **them}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        p = json.loads(urllib.request.urlopen(req, timeout=60).read())["prompt"]
        print(bt, "ky_tu", len(p), "co SUY_NGHI_CU:", "SUY_NGHI_CU" in p)


# ── So sanh ──────────────────────────────────────────────────────────────────

def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    g = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return g - w, g + w


def so_sanh(dong: list[dict]) -> dict:
    theo = {}
    for r in dong:
        if r.get("dung") is not None:
            theo.setdefault((r["ma"], r["luot"], r["lan"]), {})[r["bien_the"]] = r
    cap = [(v["A"], v["B"]) for v in theo.values() if "A" in v and "B" in v]
    b = sum(1 for a, x in cap if x["dung"] and not a["dung"])
    c = sum(1 for a, x in cap if a["dung"] and not x["dung"])
    nhom, tut = {}, False
    for g in ("code", "vi"):
        ca = [(a, x) for a, x in cap if a["nhom"] == g]
        if ca:
            da, dx = sum(a["dung"] for a, _ in ca), sum(x["dung"] for _, x in ca)
            thap = wilson(da, len(ca))[0]
            tut |= dx / len(ca) < thap
            nhom[g] = {"A": f"{da}/{len(ca)}", "B": f"{dx}/{len(ca)}", "B_duoi_wilson_A": dx / len(ca) < thap}
    # dung ca hoi thoai
    hoi = {}
    for r in dong:
        hoi.setdefault((r["ma"], r["lan"], r["bien_the"]), []).append(r)
    ca_hoi = {bt: [all(x.get("dung") for x in v) and len(v) == len(next(h for h in HOI_THOAI if h["ma"] == k[0])["luot"])
                   for k, v in hoi.items() if k[2] == bt] for bt in ("A", "B")}

    def phu(bt: str) -> dict:
        rs = [r for r in dong if r["bien_the"] == bt and r["status"] == 200]
        cuoi = [r for r in rs if r["luot"] == len(next(h for h in HOI_THOAI if h["ma"] == r["ma"])["luot"])]
        tu2 = [r for r in rs if r["luot"] >= 2]
        return {"luot": len(rs), "rong": sum(bool(r["rong"]) for r in rs), "lap": sum(bool(r["lap"]) for r in rs),
                "length": sum(r["finish"] == "length" for r in rs),
                "hoi_thoai_dung_het": f"{sum(ca_hoi[bt])}/{len(ca_hoi[bt])}",
                "prompt_tong_cong": sum(r["prompt_tong"] for r in rs),
                "prompt_moi_cong": sum(r["prompt_moi"] for r in rs),
                "prompt_luot_cuoi_p50": int(statistics.median([r["prompt_tong"] for r in cuoi] or [0])),
                "ti_le_cache_tu_luot2": round(sum(r["cache_n"] for r in tu2) / max(1, sum(r["prompt_tong"] for r in tu2)), 3),
                "prompt_moi_tu_luot2_p50": int(statistics.median([r["prompt_moi"] for r in tu2] or [0])),
                "token_ra_p50": int(statistics.median([r["token_ra"] or 0 for r in rs] or [0])),
                "giay_p50": round(statistics.median([r["giay"] for r in rs] or [0]), 1),
                "giay_cong": round(sum(r["giay"] for r in rs))}

    p = mcnemar_p(b, c)
    return {"cap": len(cap), "A_dung": sum(a["dung"] for a, _ in cap), "B_dung": sum(x["dung"] for _, x in cap),
            "chi_B_dung": b, "chi_A_dung": c, "p_mcnemar": round(p, 4), "nhom": nhom,
            "B_thang_ro": b > c and p < 0.05 and not tut, "B_khong_tut": not (c > b and p < 0.05),
            "phu_A": phu("A"), "phu_B": phu("B")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="lenh", required=True)
    sub.add_parser("tu-kiem")
    k = sub.add_parser("kiem-template")
    k.add_argument("--base", required=True)
    c = sub.add_parser("chay")
    c.add_argument("--base", required=True)
    c.add_argument("--lan", type=int, default=3)
    c.add_argument("--song-song", type=int, default=3)
    c.add_argument("--timeout", type=float, default=900)
    c.add_argument("--ra", required=True, type=pathlib.Path)
    s = sub.add_parser("so-sanh")
    s.add_argument("tep", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.lenh == "tu-kiem":
        return tu_kiem()
    if a.lenh == "kiem-template":
        kiem_template(a.base)
        return 0
    if a.lenh == "chay":
        chay(a.base, a.lan, a.song_song, a.ra, a.timeout)
        return 0
    dong = [json.loads(x) for x in a.tep.read_text(encoding="utf-8").splitlines() if x.strip()]
    print(json.dumps(so_sanh(dong), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
