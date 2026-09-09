"""Pha 05 — app ĐÃ DI TRÚ thì không còn một lối ra legacy nào.

## Vì sao chốt SỰ VẮNG MẶT chứ không chốt một lượt gọi bị chặn

Pha 04 chốt *"gọi Gemini thì bị cổng chặn"*. Đó là mệnh đề đúng **khi đường
gọi còn tồn tại**. Sau khi di trú, đường ấy biến mất — và một phép kiểm chốt
"bị chặn" sẽ mất tiền đề, rồi người ta sẽ nới nó (bắt `Exception` chẳng hạn)
cho xanh trở lại. Lúc đó nó **xanh cả khi ai đó nối lại đường Gemini**.

⇒ Sau di trú, mệnh đề đúng là **sự vắng mặt của cả một lớp**: không `httpx`,
  không URL nhà cung cấp ngoài, không `api_pool` ở tầng app, không biến môi
  trường khoá. Đó là thứ một lượt `grep` không đủ chốt, nên đọc **AST**.

## ⚠️ Đọc AST, không quét văn bản

Docstring của chính các tệp ấy **trích dẫn** đoạn mã cũ để giải thích vì sao nó
sai. Một phép kiểm quét văn bản sẽ đỏ vì chính lời giải thích — và nó sẽ cấm
luôn việc ghi lại bài học. Đây là bẫy đã xảy ra thật trong kho này
(`test_389::test_KHONG_con_hang_so_go_tay_bi_danh_trong_tep`).
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: App đã di trú sang LTT_LLM/LTT_IMAGE. Thêm dòng khi một app xong pha 05/06.
DA_DI_TRU = (
    "apps/taovideo/translate.py",
    "apps/prompt_ai_ommi/provider.py",
)

#: Tên module không được `import` ở tầng app sau khi di trú.
CAM_IMPORT = {"httpx", "requests", "aiohttp", "urllib.request"}

#: Chuỗi không được xuất hiện trong **giá trị hằng** (không tính chú thích).
CAM_TRONG_HANG = ("generativelanguage", "api.apiai.vn", "cheapkeyai.shop",
                  "api.openai.com", "GEMINI_API_KEY")


def _cay(rel: str) -> ast.AST:
    return ast.parse((GOC / rel).read_text(encoding="utf-8"))


@pytest.mark.parametrize("rel", DA_DI_TRU)
def test_khong_import_thu_vien_HTTP(rel):
    """App đã di trú không tự dựng HTTP — việc đó là của `dieu_phoi`."""
    xau = []
    for nut in ast.walk(_cay(rel)):
        if isinstance(nut, ast.Import):
            xau += [a.name for a in nut.names if a.name.split(".")[0] in CAM_IMPORT]
        elif isinstance(nut, ast.ImportFrom) and nut.module:
            if nut.module.split(".")[0] in CAM_IMPORT:
                xau.append(nut.module)
    assert not xau, (
        f"{rel} con import thu vien HTTP {xau} — app tu dung HTTP la dung "
        f"thu pha 05 cam; duong dung la `platform_core.llm.dieu_phoi`")


@pytest.mark.parametrize("rel", DA_DI_TRU)
def test_khong_co_URL_hay_TEN_BIEN_KHOA_trong_hang_so(rel):
    """Chốt trên **giá trị hằng**, nên docstring giải thích bài học vẫn sống."""
    xau = []
    for nut in ast.walk(_cay(rel)):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            # Docstring la mot `Expr` chua `Constant` — bo qua chung.
            xau += [c for c in CAM_TRONG_HANG if c in nut.value]
    # Docstring cua module/ham cung la Constant, nen loc chung ra truoc.
    than = _cay(rel)
    doc = set()
    for nut in ast.walk(than):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)):
            d = ast.get_docstring(nut, clean=False)
            if d:
                doc.update(c for c in CAM_TRONG_HANG if c in d)
    that_su = [c for c in xau if c not in doc]
    assert not that_su, (
        f"{rel} con URL/ten bien khoa legacy trong HANG SO: {that_su}")


@pytest.mark.parametrize("rel", DA_DI_TRU)
def test_khong_goi_api_pool_o_tang_APP(rel):
    """Cấp khoá là việc của `dieu_phoi`, không phải của app.

    ⭐ Pha 05 cấm *"app-level api_pool routing"* vì nó là bản sao thứ hai của
       quyết định chọn provider — và hai bản sẽ trôi khỏi nhau.
    """
    xau = []
    for nut in ast.walk(_cay(rel)):
        if isinstance(nut, ast.Attribute) and isinstance(nut.value, ast.Name):
            if nut.value.id == "api_pool":
                xau.append(nut.attr)
        elif isinstance(nut, ast.ImportFrom) and nut.module == "platform_core":
            xau += [a.name for a in nut.names if a.name == "api_pool"]
    assert not xau, f"{rel} con tu cap khoa qua api_pool: {xau}"


@pytest.mark.parametrize("rel", DA_DI_TRU)
def test_CO_gianh_suat_admission_truoc_khi_cham_may_B(rel):
    """🔴 Mệnh đề PHỦ ĐỊNH quan trọng nhất của pha 05.

    Máy B chỉ có **một** suất đồng thời. Một đường mới tới nó mà quên
    `admission` không chỉ chen hàng — nó làm chính cơ chế đếm suất **sai**, nên
    hai đường kia hỏng theo.

    ⚠️ Lỗ đó đã có thật: tới 01/09 `agent/planner.py` là đường **duy nhất** tới
       máy B không giành suất, và nó vô hại suốt nhiều tháng chỉ vì một lỗi
       **thứ hai** che nó. Di trú một app mà quên bước này là dựng lại đúng lỗ
       ấy ở một tệp mới — và lần sau sẽ khó tìm hơn, vì không ai nghi một tệp
       vừa được dọn.
    """
    van = (GOC / rel).read_text(encoding="utf-8")
    ten = {n.attr for n in ast.walk(_cay(rel))
           if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
           and n.value.id == "admission"}
    assert "acquire" in ten, (
        f"{rel} goi model nha ma KHONG gianh suat admission — day la duong "
        f"lach dung bang cai da bi dong ngay 01/09")
    assert "release_by_id" in ten, (
        f"{rel} gianh suat ma khong nha — giu mot suat khong dung dung bang "
        f"chiem no vinh vien")
    assert "finally" in van, (
        f"{rel}: nha suat phai o `finally`, khong the o duong thanh cong")
