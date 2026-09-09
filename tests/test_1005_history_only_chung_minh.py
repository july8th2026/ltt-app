"""Pha 09 — CHỨNG MINH nhãn `HISTORY_ONLY`, không chỉ khai nó.

## Vì sao tệp này tồn tại

Gói chiến dịch cho phép giữ một bề mặt legacy dưới nhãn `HISTORY_ONLY` **chỉ
khi** chứng minh được **năm** điều:

    1. khong callable        khong duong goi nao con dung duoc
    2. khong selectable      khong bo chon nao chao no ra
    3. khong tra secret      khong doc khoa/bien moi truong cua no
    4. khong network egress  khong dia chi nha cung cap trong hang so
    5. khong fallback        khong danh sach provider nao con ten no

⛔ Bản tự kiểm 09/09 ghi nhận **51 tệp mang nhãn ấy với 0 phép kiểm** — tức nhãn
   là một **lời khai**, không phải một sự thật. Tệp này biến nó thành sự thật, và
   là điều kiện vào pha 12.

## ⭐ Tập hợp đọc THẲNG TỪ MA TRẬN, không chép tay

Chép danh sách vào đây sẽ tạo bản sao thứ hai, và ngày ma trận đổi thì hai bản
lệch nhau — đúng cơ chế đã hỏng nhiều lần trong kho này. Ma trận là **sổ**; tệp
này chứng minh sổ nói đúng.

🔑 Hệ quả có chủ đích: thêm một dòng `HISTORY_ONLY` vào ma trận là **tự động**
   phải qua năm phép kiểm dưới. Không ai khai được một nhãn rồi bỏ đó.

## ⚠️ Đọc AST, không quét văn bản

Docstring của chính những tệp ấy **trích dẫn** tên nhà cung cấp cũ để giải thích
vì sao chúng chỉ còn là lịch sử. Quét văn bản sẽ đỏ vì chính lời giải thích.
"""
from __future__ import annotations

import ast
import csv
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
MA_TRAN = GOC / "docs" / "AI_CLEAN_REBUILD" / "LEGACY_SURFACE_MATRIX.csv"

#: Ba họ nhà cung cấp mà chiến dịch gỡ.
HO = ("gemini", "apiai", "cheapkeyai")

#: Địa chỉ mạng của chúng — không được nằm trong **giá trị hằng**.
DIA_CHI = ("generativelanguage.googleapis.com", "api.apiai.vn", "cheapkeyai.shop")

#: Biến môi trường mang khoá của chúng.
BIEN_KHOA = ("GEMINI_API_KEY", "APIAI_API_KEY", "CHEAPKEYAI_API_KEY")


def _tep_history_only() -> list[str]:
    """Tệp `.py` mang nhãn `HISTORY_ONLY` trong ma trận **và còn trên đĩa**."""
    ra = []
    with MA_TRAN.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Classification"] != "HISTORY_ONLY":
                continue
            p = GOC / r["File"]
            if p.suffix == ".py" and p.is_file():
                ra.append(r["File"])
    return sorted(ra)


TEP = _tep_history_only()


def _cay(rel: str) -> ast.Module:
    return ast.parse((GOC / rel).read_bytes().decode("utf-8"))


def _doc_string(cay: ast.Module) -> set[str]:
    """Chuỗi nằm trong docstring — được miễn ở phép kiểm hằng số."""
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)):
            d = ast.get_docstring(nut, clean=False)
            if d:
                ra.add(d)
    return ra


def test_ma_tran_co_that_su_khai_HISTORY_ONLY():
    """⭐ ĐỐI CHỨNG. Thiếu nó thì một ma trận rỗng làm cả tệp này xanh-rỗng:
    `parametrize` trên danh sách rỗng **không chạy phép kiểm nào**, mà pytest
    vẫn báo thành công."""
    assert MA_TRAN.is_file(), "khong doc duoc ma tran"
    assert len(TEP) >= 20, (
        f"chi thay {len(TEP)} tep HISTORY_ONLY — ma tran co the da hong hoac "
        "duong dan doi; phep kiem duoi se xanh-rong")


# ── 1. không callable · 4. không network egress ─────────────────────────────
@pytest.mark.parametrize("rel", TEP)
def test_1_khong_HANG_SO_nao_dung_duoc_mot_luot_goi(rel):
    """Địa chỉ nhà cung cấp trong **giá trị hằng** = một lượt gọi dựng được."""
    cay = _cay(rel)
    doc = _doc_string(cay)
    xau = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if any(d in nut.value for d in doc if d):
                continue
            for d in DIA_CHI:
                if d in nut.value:
                    xau.append(f"dong {nut.lineno}: {d}")
    assert xau == [], f"{rel} con dia chi nha cung cap trong hang so: {xau}"


# ── 3. không tra secret ─────────────────────────────────────────────────────
@pytest.mark.parametrize("rel", TEP)
def test_3_khong_doc_bien_moi_truong_khoa_cua_ho_da_ngung(rel):
    """`os.environ["GEMINI_API_KEY"]` là **tra secret**, dù không gọi mạng.

    ⛔ Một tệp còn đọc được khoá là một tệp còn **một nửa đường gọi** — nửa kia
       chỉ cách một dòng `httpx.post`.
    """
    cay = _cay(rel)
    doc = _doc_string(cay)
    xau = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if any(d in nut.value for d in doc if d):
                continue
            for b in BIEN_KHOA:
                if b in nut.value:
                    xau.append(f"dong {nut.lineno}: {b}")
    assert xau == [], f"{rel} con tra bien khoa cua nha cung cap da ngung: {xau}"


# ── 5. không fallback ───────────────────────────────────────────────────────
@pytest.mark.parametrize("rel", TEP)
def test_5_khong_danh_sach_provider_nao_con_ten_ho(rel):
    """Một `["ltt_llm", "gemini"]` là **fallback**, và nó không cần một dòng
    `httpx` nào để sống: `dieu_phoi` sẽ tự đi tiếp sang tên thứ hai.

    ⭐ Chốt trên **phần tử của list/tuple hằng**, không trên cả tệp — nên một
       chú thích *"trước đây là `['ltt_llm','gemini']`"* vẫn sống.
    """
    cay = _cay(rel)
    xau = []
    for nut in ast.walk(cay):
        if not isinstance(nut, (ast.List, ast.Tuple, ast.Set)):
            continue
        ten = [e.value.strip().lower() for e in nut.elts
               if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        for h in HO:
            if h in ten:
                xau.append(f"dong {nut.lineno}: {ten}")
    assert xau == [], f"{rel} con danh sach provider mang ten da ngung: {xau}"


# ── 2. không selectable — chốt MỘT LẦN trên registry, không theo từng tệp ───
def test_2_khong_bo_chon_nao_chao_ra_nha_cung_cap_da_ngung():
    """Selectable là tính chất của **registry**, không của từng tệp.

    ⭐ Nên phép kiểm này không `parametrize`: hỏi 51 lần cùng một câu về cùng một
       bảng thì 50 lần là nhiễu, và nó làm người đọc tưởng đã đo 51 thứ.
    """
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE

    for h in HO:
        assert providers.da_ngung(h), f"{h} phai o trang thai da ngung"

    # `model_options` tra {"value": <model id>, "label": ...} — KHONG mang ten
    # provider. Nen hoi nguoc: model id ay thuoc provider nao trong REGISTRY.
    def _nha_cua(model_id: str) -> str:
        for pid, prov in providers.REGISTRY.items():
            if any(m.id == model_id for m in prov.models):
                return pid
        return ""

    for cat in (APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE):
        chao = {_nha_cua(str(m.get("value", ""))) for m in providers.model_options(cat)}
        con = sorted(set(HO) & {x.lower() for x in chao if x})
        assert con == [], f"bo chon {cat} van chao ra model cua: {con}"

    # ⭐ Đối chứng: bộ chọn có thật sự chào ra thứ gì không? Thiếu vế này thì một
    #    `model_options` trả rỗng cũng làm phép kiểm trên xanh.
    assert providers.model_options(APIKEY_CAT_IMAGE), "bo chon anh RONG — xanh-rong"


def test_2b_khong_manifest_nao_khai_provider_da_ngung():
    """Cửa bán hàng thứ hai: `params_schema` của ToolSpec."""
    from platform_core import providers
    from platform_core.registry import discover

    xau = []
    for app in discover():
        if app.error:
            continue
        for tool in (app.manifest.tools or ()):
            for pid in (tool.params_schema.get("model", {}).get("providers") or ()):
                if providers.da_ngung(pid):
                    xau.append(f"{app.manifest.slug}/{tool.name}: {pid}")
    assert xau == [], f"manifest con khai nha cung cap da ngung: {xau}"
