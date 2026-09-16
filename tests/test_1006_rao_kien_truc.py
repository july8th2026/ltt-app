"""Pha 10 — RÀO KIẾN TRÚC cưỡng chế bằng máy: legacy không quay lại được.

Chiến dịch xoá xong là một trạng thái; **giữ** nó là một cơ chế. Tệp này là cơ
chế ấy: bộ test đỏ ngay khi một nguồn **thi hành** dựng lại được một lượt gọi tới

    Gemini · ChatGPT/Codex (execution ngoài) · apiai · cheapkeyai

cho Text/VLM/Image, hoặc khi một **app** tự dựng HTTP tới nhà cung cấp, hoặc khi
một **fallback ẩn** xuất hiện dưới dạng một danh sách provider.

## ✅ Được phép — và phải KHÔNG bị bắt nhầm

    cong noi bo LTT   `llm_gateway/` · `render_gateway/` (ta LA nha cung cap)
    Voice sidecar     `voice_sidecar/`
    video Seedance    BytePlus/ModelArk
    client cam vao ta `cam` CLI, `tools/gui/` — Codex la KHACH, khong phai vendor
    lich su + tai lieu docstring, chu thich, `docs/`

⛔ Vế cuối là vế khó nhất, và là vế đã cắn kho này trước đây: **một bộ dò quét
   văn bản sẽ báo động trên chính đoạn giải thích vì sao thứ ấy bị xoá** — rồi
   người ta xoá lời giải thích để làm nó im. Nên rào này đọc **AST** và chỉ chốt
   trên *giá trị hằng*, *import*, *tên hàm định nghĩa*.

## ⭐ Rào có TỰ KIỂM (fixture dương + âm)

Một bộ dò không tự kiểm thì không ai biết nó còn sống. Đo 06/09 trong kho này:
đổi một dấu `+` thành `**` làm mọi số đếm thành 0 và bánh cóc **xanh vĩnh viễn**.
Nên dưới đây có `MAU_XAU` (phải bắt được **từng** mẫu) và `MAU_TOT` (không được
bắt mẫu nào) — chúng chạy qua **đúng** những hàm mà rào thật dùng.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Nguồn **thi hành**. `tests/` cố ý không có: phép kiểm được phép nhắc tên.
KHU = ("apps", "platform_core", "server", "llm_gateway", "render_gateway",
       "sdk", "nexus_agent", "tools", "job_worker.py", "voice_sidecar",
       "voice_sidecar_main.py")

#: Host của các họ đã gỡ. `api.openai.com` nằm đây vì **gọi RA** OpenAI là thứ
#: bị cấm — còn *nói giao thức* OpenAI ở `llm_gateway/` thì không chạm host này.
HOST_CAM = (
    "generativelanguage.googleapis.com",
    "api.openai.com",
    "chatgpt.com",
    "api.apiai.vn",
    "cheapkeyai.shop",
)

#: Tên provider đã ngừng — không được là **phần tử** của một danh sách hằng
#: (đó là hình dạng của một fallback).
PROVIDER_CAM = ("gemini", "apiai", "cheapkeyai")

#: Biến môi trường mang khoá của chúng.
BIEN_KHOA_CAM = ("GEMINI_API_KEY", "APIAI_API_KEY", "CHEAPKEYAI_API_KEY",
                 "OPENAI_API_KEY", "CODEX_API_KEY")

#: Module không được import từ **tầng app**: app không tự dựng HTTP tới ai.
#: (`platform_core/` và các cổng thì được — đó là chỗ đường ra được tập trung.)
HTTP_CAM_O_APP = ("httpx", "requests", "aiohttp", "urllib.request", "http.client")

#: ⏳ Miễn trừ CÓ TÊN, có lý do, và **có phép kiểm chốt rằng chúng còn tồn tại**.
MIEN_TRU_HANG = {
    # `REGISTRY` là bảng tra LỊCH SỬ: một job cũ phải tra ra được tên và nhãn
    # model nó đã chạy. Ba nhà ấy `is_active=False` từ pha 04 nên không bộ chọn
    # nào chào ra — `test_1000` và `test_1005` chốt điều đó.
    "platform_core/providers.py",
}
#: ⏳ Miễn trừ HTTP — **mỗi dòng ghi GỌI TỚI ĐÂU**, vì đó mới là câu quyết định.
#:
#: 🔑 Luật *"app không tự dựng HTTP"* đúng với **nhà cung cấp AI**, và sai với
#:    hạ tầng mà chiến dịch cho phép giữ (yêu cầu 9: Voice · Seedance/BytePlus ·
#:    máy nhà · VPS). Nên rào không nới thành "app nào cũng được" — nó giữ
#:    nguyên độ chặt và bắt mỗi ngoại lệ phải **khai đích đến**.
#:
#: ⛔ Thêm một dòng vào đây là một hành động có chủ ý, hiện trong diff. Danh sách
#:    này phình lên là dấu hiệu đường ra mạng đang tán trở lại ra tầng app.
MIEN_TRU_HTTP = {
    # → sidecar loopback CỦA CHÍNH TA (VOICE), không phải nhà cung cấp
    "apps/ltt_voice/sidecar_client.py",
    # → cổng render máy B (LTT_IMAGE) — nội bộ, bearer riêng
    "apps/anhnoibo/features.py",
    # → cổng LLM máy B (`/live`) — nội bộ
    "apps/ltt_llm/features.py",
    # → BytePlus/ModelArk: VIDEO Seedance, yêu cầu 9 cho phép giữ
    "apps/taovideo/assets.py",
    "apps/taovideo/modelark.py",
    # → tác nhân theo dõi trên MÁY KHÁCH, gọi về nền tảng của ta
    "apps/upscalevideo/watch_agent.py",
    # → Proxmox / Vultr / OVH: hạ tầng BÁN VPS, không phải nhà cung cấp AI
    "apps/vps/services/proxmox.py",
    "apps/vps/services/vultr.py",
    # → OVH: mua máy chủ cho bán VPS — cùng loại với Proxmox/Vultr
    "apps/vps/services/ovh.py",
    # → máy thật chạy WanGP (LTT VIDEO) — nội bộ
    "apps/lttvideo/cong/may_that.py",
}


# ══════════════════ bộ dò — dùng chung cho rào thật VÀ tự kiểm ══════════════
def _docstring(cay: ast.AST) -> set[str]:
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)):
            d = ast.get_docstring(nut, clean=False)
            if d:
                ra.add(d)
    return ra


def do_host(ma: str) -> list[str]:
    """Host nhà cung cấp nằm trong **giá trị hằng** (docstring được miễn)."""
    cay = ast.parse(ma)
    doc = _docstring(cay)
    ra = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if any(d and nut.value in d for d in doc):
                continue
            ra += [f"{h}@{nut.lineno}" for h in HOST_CAM if h in nut.value]
    return ra


def do_khoa(ma: str) -> list[str]:
    """Tên biến môi trường khoá trong giá trị hằng."""
    cay = ast.parse(ma)
    doc = _docstring(cay)
    ra = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if any(d and nut.value in d for d in doc):
                continue
            ra += [f"{b}@{nut.lineno}" for b in BIEN_KHOA_CAM if b in nut.value]
    return ra


def do_fallback(ma: str) -> list[str]:
    """Tên provider đã ngừng là **phần tử** của một list/tuple/set hằng.

    ⭐ Chốt trên phần tử chứ không trên cả tệp: một chú thích *"trước đây là
       `['ltt_llm','gemini']`"* phải sống được.
    """
    ra = []
    for nut in ast.walk(ast.parse(ma)):
        if not isinstance(nut, (ast.List, ast.Tuple, ast.Set)):
            continue
        ten = {e.value.strip().lower() for e in nut.elts
               if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        ra += [f"{p}@{nut.lineno}" for p in PROVIDER_CAM if p in ten]
    return ra


def do_http_o_app(ma: str) -> list[str]:
    """Tầng app tự dựng HTTP — dù tới đâu."""
    ra = []
    for nut in ast.walk(ast.parse(ma)):
        ten = []
        if isinstance(nut, ast.Import):
            ten = [a.name for a in nut.names]
        elif isinstance(nut, ast.ImportFrom) and nut.module:
            ten = [nut.module]
        for t in ten:
            if any(t == c or t.startswith(c + ".") for c in HTTP_CAM_O_APP):
                ra.append(f"{t}@{nut.lineno}")
    return ra


# ══════════════════════════ TỰ KIỂM: mẫu xấu / mẫu tốt ══════════════════════
MAU_XAU = {
    "host trong hang so": (do_host,
                           'URL = "https://generativelanguage.googleapis.com/v1beta"'),
    "host openai": (do_host, 'def f():\n    return "https://api.openai.com/v1"'),
    "bien khoa": (do_khoa, 'import os\nk = os.environ["GEMINI_API_KEY"]'),
    "fallback trong list": (do_fallback, 'THU_TU = ["ltt_llm", "gemini"]'),
    "fallback trong tuple": (do_fallback, 'P = ("gemini",)'),
    "app tu dung http": (do_http_o_app, 'import httpx\n'),
    "app tu dung requests": (do_http_o_app, 'from requests import get\n'),
}

MAU_TOT = {
    # ⛔ Đây là vế QUAN TRỌNG NHẤT: lời giải thích vì sao thứ ấy bị xoá phải sống.
    "docstring giai thich": (do_host,
                             '"""Ban cu goi https://generativelanguage.googleapis.com'
                             ' — DA XOA o pha 07."""\nX = 1'),
    "chu thich giai thich": (do_khoa, '# truoc day doc GEMINI_API_KEY, da go\nX = 1'),
    "nhac ten trong chuoi KHAC": (do_fallback, 'GHI_CHU = "bo gemini o pha 04"'),
    "cong noi bo noi giao thuc openai": (do_host,
                                         'DUONG = "/v1/chat/completions"  # openai-compat'),
    "platform_core dung httpx": (do_http_o_app, 'X = 1'),
}


@pytest.mark.parametrize("ten", sorted(MAU_XAU))
def test_TU_KIEM_bo_do_BAT_duoc_mau_xau(ten):
    """⭐ Không có phép kiểm này thì cả tệp **xanh vĩnh viễn** khi bộ dò hỏng.

    Đo 06/09 trong kho này: đổi `dem[ma] + 1` thành `** 1` làm mọi số đếm thành
    0, `tang` luôn rỗng, và bánh cóc xanh mãi — hỏng so với hỏng thì vẫn bằng
    nhau. Một bộ dò không tự kiểm là một bộ dò không ai biết còn sống.
    """
    ham, ma = MAU_XAU[ten]
    assert ham(ma), f"bo do KHONG bat duoc mau xau {ten!r} — rao da chet"


@pytest.mark.parametrize("ten", sorted(MAU_TOT))
def test_TU_KIEM_bo_do_KHONG_bat_mau_tot(ten):
    """⛔ Dương tính giả đắt hơn âm tính giả ở đây: nó dạy người ta **xoá lời
    giải thích** để làm rào im — tức chính thứ ta muốn giữ lại."""
    ham, ma = MAU_TOT[ten]
    assert ham(ma) == [], f"bo do BAT NHAM mau tot {ten!r}: {ham(ma)}"


# ══════════════════════════════ rào thật ════════════════════════════════════
def _tep_py():
    for khu in KHU:
        d = GOC / khu
        if d.is_file():
            yield d
        elif d.is_dir():
            for p in d.rglob("*.py"):
                if "__pycache__" not in p.parts and "node_modules" not in p.parts:
                    yield p


def _quet(ham, mien_tru=frozenset(), chi_app=False):
    xau = []
    for p in _tep_py():
        rel = p.relative_to(GOC).as_posix()
        if rel in mien_tru:
            continue
        if chi_app and not rel.startswith("apps/"):
            continue
        try:
            ma = p.read_bytes().decode("utf-8")
            found = ham(ma)
        except (SyntaxError, UnicodeDecodeError):
            continue
        if found:
            xau.append(f"{rel}: {found}")
    return xau


def test_khong_nguon_thi_hanh_nao_mang_HOST_nha_cung_cap_da_go():
    assert _quet(do_host, MIEN_TRU_HANG) == []


def test_khong_nguon_thi_hanh_nao_TRA_KHOA_cua_ho_da_go():
    assert _quet(do_khoa, MIEN_TRU_HANG) == []


def test_khong_FALLBACK_AN_nao_duoi_dang_danh_sach_provider():
    assert _quet(do_fallback, MIEN_TRU_HANG) == []


def test_khong_APP_nao_tu_dung_HTTP():
    """Đường ra mạng phải tập trung ở `platform_core/` và các cổng.

    ⭐ App tự dựng HTTP là **bản sao thứ hai** của quyết định chọn nhà cung cấp —
       và hai bản sẽ trôi khỏi nhau. Đó đúng là hình dạng mà pha 05–06 vừa gỡ ở
       sáu app.
    """
    assert _quet(do_http_o_app, MIEN_TRU_HTTP, chi_app=True) == []


def test_MIEN_TRU_chi_tro_toi_tep_CO_THAT():
    """Một miễn trừ trỏ tới tệp đã mất là một miễn trừ **không ai gỡ được**: nó
    xanh mãi và không ai biết nó đang che gì."""
    thua = [t for t in (MIEN_TRU_HANG | MIEN_TRU_HTTP) if not (GOC / t).is_file()]
    assert thua == [], f"mien tru tro toi tep khong ton tai: {thua}"


def test_rao_co_QUET_that_su_chu_khong_quet_rong():
    """⭐ Đối chứng cuối: bốn phép kiểm trên đều có dạng `assert [] == []`, nên
    một `_tep_py()` rỗng làm cả bốn xanh mà không đọc gì."""
    so = sum(1 for _ in _tep_py())
    assert so >= 300, f"chi quet {so} tep — rao co the dang quet rong"
