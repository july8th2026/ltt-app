"""Pha 07 — SỰ VẮNG MẶT của cả một lớp, chốt trên toàn kho.

## Vì sao phép kiểm này thay hai phép kiểm cũ

Pha 04 chốt *"gọi Gemini thì bị cổng chặn"*. Đó là mệnh đề đúng **khi đường gọi
còn tồn tại**. Pha 07 xoá chúng — `dich_gemini.goi_gemini`, `llm.dieu_phoi.
_goi_gemini`, `codex_sidecar/`, `apps/chataistudio/` — nên hai phép kiểm ấy
không còn đối tượng, và giữ lại chúng là giữ hai `AttributeError` đội lốt.

⭐ Mệnh đề thay thế **khó lách hơn**: không phải *"gọi thì bị chặn"* mà *"không
   còn chỗ nào dựng được một lượt gọi"*. Bị-chặn cần một cái cổng còn đứng;
   vắng-mặt thì không cần ai canh.

## ⚠️ Đọc AST, không quét văn bản

Chính tệp này, và docstring của những tệp đã di trú, **trích dẫn** tên các thứ
đã xoá để giải thích vì sao chúng bị xoá. Một phép kiểm quét văn bản sẽ đỏ vì
chính lời giải thích — và như thế nó cấm luôn việc ghi lại bài học. Đây là bẫy
đã xảy ra thật trong kho này (`test_389`).
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Thư mục mã sản phẩm. `tests/` cố ý KHÔNG có: phép kiểm được phép nhắc tên
#: những thứ nó canh.
KHU = ("apps", "platform_core", "server", "llm_gateway", "render_gateway",
       "sdk", "nexus_agent", "tools", "job_worker.py")

#: 🔴 Thư mục / tệp phải BIẾN MẤT khỏi đĩa.
DA_XOA = (
    "codex_sidecar",
    "codex_sidecar_main.py",
    "apps/chataistudio",
    "platform_core/image_gen/dich_gemini.py",
    "tools/doi_chung_gemini.py",
)

#: Tên hàm/hằng số của đường gọi legacy. Không được **định nghĩa** lại ở đâu.
TEN_CAM = ("_goi_gemini", "goi_gemini", "PROVIDER_GEMINI")

#: Chuỗi không được xuất hiện trong **giá trị hằng** (docstring được miễn).
CAM_TRONG_HANG = ("generativelanguage.googleapis.com", "api.apiai.vn",
                  "cheapkeyai.shop")

#: ⏳ MIỄN TRỪ CÓ HẠN — và hạn của nó là **pha 09**.
#:
#: `platform_core/providers.py` còn `base_url` của ba nhà cung cấp đã ngừng, vì
#: `REGISTRY` là **bảng tra lịch sử**: một job cũ vẫn phải tra ra được tên và
#: nhãn model nó đã chạy. Chúng đã `is_active=False` từ pha 04, nên không một
#: bộ chọn nào chào chúng ra — `test_1000` chốt điều đó.
#:
#: 🔴 Pha 09 (*provider config / secret clean*) là nơi quyết định giữ những dòng
#:    ấy dưới dạng gì. Ngày đó tới, **xoá miễn trừ này trước**, rồi mới sửa
#:    `providers.py` — nếu không nó sẽ sống mãi như mọi miễn trừ không có hạn.
MIEN_TRU = ("platform_core/providers.py",)


def _tep_py():
    for khu in KHU:
        d = GOC / khu
        if d.is_file():
            yield d
        elif d.is_dir():
            for p in d.rglob("*.py"):
                if "__pycache__" not in p.parts:
                    yield p


def test_moi_thu_da_xoa_deu_KHONG_con_tren_dia():
    con = [t for t in DA_XOA if (GOC / t).exists()]
    assert con == [], f"pha 07 khai da xoa nhung van con: {con}"


def test_khong_module_nao_DINH_NGHIA_lai_duong_goi_legacy():
    """Chốt trên **định nghĩa**, không trên lời nhắc tên.

    ⭐ Một chú thích *"`_goi_gemini` đã xoá"* là điều ta MUỐN có. Một `def
       _goi_gemini` thì không. Phân biệt hai thứ ấy chỉ AST làm được.
    """
    xau = []
    for p in _tep_py():
        try:
            cay = ast.parse(p.read_bytes().decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for nut in ast.walk(cay):
            if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if nut.name in TEN_CAM:
                    xau.append(f"{p.relative_to(GOC)}:{nut.lineno} def {nut.name}")
            elif isinstance(nut, ast.Assign):
                for dich in nut.targets:
                    if isinstance(dich, ast.Name) and dich.id in TEN_CAM:
                        xau.append(f"{p.relative_to(GOC)}:{nut.lineno} {dich.id} =")
    assert xau == [], f"duong goi legacy duoc dinh nghia lai: {xau}"


def test_khong_tep_nao_IMPORT_duoc_thu_da_xoa():
    """Một `import` tới thứ không còn là một lỗi **lúc chạy**, không phải lúc đọc.

    Nó nằm im cho tới đúng cái nhánh gọi tới nó — thường là nhánh hỏng, tức chỗ
    tệ nhất để phát hiện.
    """
    cam = {"codex_sidecar", "apps.chataistudio",
           "platform_core.image_gen.dich_gemini", "tools.doi_chung_gemini"}
    xau = []
    for p in _tep_py():
        try:
            cay = ast.parse(p.read_bytes().decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for nut in ast.walk(cay):
            ten = []
            if isinstance(nut, ast.Import):
                ten = [a.name for a in nut.names]
            elif isinstance(nut, ast.ImportFrom) and nut.module:
                ten = [nut.module]
            for t in ten:
                if any(t == c or t.startswith(c + ".") for c in cam):
                    xau.append(f"{p.relative_to(GOC)}:{nut.lineno} {t}")
    assert xau == [], f"con import thu da xoa: {xau}"


def test_khong_HANG_SO_nao_con_mang_dia_chi_nha_cung_cap_legacy():
    """Docstring được miễn — xem khối đầu tệp."""
    xau = []
    for p in _tep_py():
        if p.relative_to(GOC).as_posix() in MIEN_TRU:
            continue
        try:
            than = p.read_bytes().decode("utf-8")
            cay = ast.parse(than)
        except (SyntaxError, UnicodeDecodeError):
            continue
        doc = set()
        for nut in ast.walk(cay):
            if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.ClassDef)):
                d = ast.get_docstring(nut, clean=False)
                if d:
                    doc.update(c for c in CAM_TRONG_HANG if c in d)
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
                for c in CAM_TRONG_HANG:
                    if c in nut.value and c not in doc:
                        xau.append(f"{p.relative_to(GOC)}:{nut.lineno} {c}")
    assert xau == [], f"con dia chi nha cung cap legacy trong hang so: {xau}"


def test_MIEN_TRU_chi_tro_toi_tep_CO_THAT():
    """Một miễn trừ trỏ tới tệp không còn là một miễn trừ **không ai gỡ được**:
    nó xanh mãi mãi và không ai biết nó đang che gì."""
    thua = [t for t in MIEN_TRU if not (GOC / t).is_file()]
    assert thua == [], f"mien tru tro toi tep khong ton tai: {thua}"


def test_registry_app_KHONG_con_chataistudio():
    """Một app biến mất phải biến mất **khỏi catalog**, không chỉ khỏi đĩa."""
    from platform_core.registry import discover

    slug = {a.manifest.slug for a in discover() if not a.error}
    assert "chataistudio" not in slug
    # ⭐ Đối chứng: `discover()` có thật sự thấy app nào không? Thiếu vế này thì
    #    một `discover()` trả rỗng cũng làm phép kiểm trên xanh.
    assert "chatltt" in slug, "discover() khong thay app nao — phep kiem xanh-rong"


def test_catalog_parent_khong_tro_toi_app_da_bien_mat():
    """🔴 Bẫy im lặng: `catalog_parent` trỏ tới slug không tồn tại thì mục ấy
    **rơi khỏi** catalog — mất chứ không báo lỗi.

    `apps/ltt_llm` từng neo vào `chataistudio`, và pha 07 đã chuyển nó sang
    `chatltt`. Phép kiểm này canh cho mọi app, không riêng app đó.
    """
    from platform_core.registry import discover

    songs = [a for a in discover() if not a.error]
    slug = {a.manifest.slug for a in songs}
    xau = [(a.manifest.slug, cha) for a in songs
           if (cha := getattr(a.manifest, "catalog_parent", "")) and cha not in slug]
    assert xau == [], f"catalog_parent tro toi app khong ton tai: {xau}"


@pytest.mark.parametrize("ten", ["_goi_gemini", "PROVIDER_GEMINI"])
def test_dieu_phoi_LLM_khong_con_cua_nao_ten_nhu_the(ten):
    from platform_core.llm import dieu_phoi
    assert not hasattr(dieu_phoi, ten)
