"""test_389 — `planner` phải gọi được model nhà, và phải giành suất trước.

🔴 HAI KHUYẾT TẬT CHE NHAU, TÌM RA Ở PROMPT 08 (01/09).

**F-04.** `platform_core/agent/planner.py` khai `PLANNER_PROVIDERS = ("ltt_llm",
"gemini")` và tự chú thích *"⭐ MODEL NHÀ ĐI TRƯỚC. Nó rẻ hơn nhiều."* — nhưng nó
gửi `model_theo_provider={"ltt_llm": "ltt_llm"}`, tức **bí danh công khai** thay
vì id model nội bộ. Khoá của provider chỉ khai `qwen38-api`/`qwen38-vision`, nên
`api_pool.chon_key(model="ltt_llm")` **luôn** ném `ThieuKeyError`, `dieu_phoi`
đọc đó là *"provider này không phục vụ được, đi tiếp"*, và **mọi** lượt lập kế
hoạch âm thầm rơi xuống Gemini — một provider ngoài, trả tiền. Không một dòng
log nào nói.

**F-06.** Cùng hàm đó gọi thẳng `dieu_phoi` — **đường duy nhất** tới máy B không
đi qua `admission`. Ba đường còn lại (`streaming.py`, `chat.py`, `job_runner.py`)
đều giành suất.

⛔ VÀ ĐÂY LÀ ĐIỂM ĐÁNG NHỚ NHẤT: F-06 **vô hại chừng nào F-04 còn sống**. Nhánh
   `ltt_llm` không bao giờ đi tới máy B, nên không có gì để lách. Sửa F-04 một
   mình là **kích hoạt** F-06. Hai lỗi che nhau, và cái che sắp được gỡ — nên
   hai bản vá phải đi cùng một lượt, và tệp này chốt cả hai cùng lúc.

⭐ Gốc rễ chung là một **chú thích**: docstring của `dieu_phoi.goi` dạy sai quy
   ước, và hai nơi chép theo nó (`planner.py`, `tools/kiem_ltt_llm.py`). Một ví
   dụ trong docstring là mã mà người ta chép; nó sai thì nó không sai một mình.
"""
from __future__ import annotations

import pytest

from platform_core.agent import planner


# ── 1. F-04: bí danh không bao giờ được rời máy A ────────────────────────────

def test_model_nha_la_ID_NOI_BO_khong_phai_bi_danh():
    """`_model_nha()` phải trả id registry, không phải tên khách gõ."""
    from apps.ltt_llm.features import ALIAS_SANG_ID

    id_nha = planner._model_nha()
    assert id_nha, "khong tra cuu duoc model nha tu registry"
    assert id_nha not in ALIAS_SANG_ID, (
        f"{id_nha!r} la BI DANH cong khai. Gui no toi provider thi "
        f"`chon_key` nem ThieuKeyError va nhanh model nha bi bo qua IM LANG")
    assert id_nha in set(ALIAS_SANG_ID.values()), (
        f"{id_nha!r} khong phai id noi bo nao ma app khai")


def test_model_nha_KHONG_chon_ban_doc_anh():
    """Lập kế hoạch là việc chữ. Chọn nhầm bản vision là chọn một model có cửa
    sổ nhỏ hơn một nửa (65.536 thay vì 131.072) mà không được gì."""
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_CHAT

    id_nha = planner._model_nha()
    cua_anh = {m.id for m in providers.models_for("ltt_llm", APIKEY_CAT_CHAT)
               if (getattr(m, "capabilities", None) or {}).get("vision")}
    assert id_nha not in cua_anh


def test_KHONG_con_hang_so_go_tay_bi_danh_trong_tep():
    """Bánh cóc: cấm quy ước cũ quay lại bằng một hằng số gõ tay.

    ⛔ Đây là thứ duy nhất chặn được một lần "dọn cho gọn" trong tương lai — ai
       đó thấy `_model_nha()` rườm rà và thay bằng một chuỗi.

    ⚠️ Đọc **AST**, không quét văn bản. Bản đầu của phép kiểm này grep chuỗi
       `"ltt_llm": "ltt_llm"` và lập tức đỏ — vì nó bắt chính docstring ở trên,
       nơi *trích dẫn* quy ước sai để giải thích. Một bánh cóc không phân biệt
       được **mã** với **lời kể về mã** thì nó cấm luôn việc ghi lại bài học.
    """
    import ast
    import pathlib

    cay = ast.parse(pathlib.Path(planner.__file__).read_text(encoding="utf-8"))
    xau = []
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Dict):
            continue
        for k, v in zip(nut.keys, nut.values):
            if (isinstance(k, ast.Constant) and k.value == "ltt_llm"
                    and isinstance(v, ast.Constant) and v.value == "ltt_llm"):
                xau.append(nut.lineno)
    assert not xau, (
        f"quy uoc sai da quay lai o dong {xau}: bi danh cong khai duoc gui "
        f"lam id model, va `chon_key` se bo qua provider nha IM LANG")


# ── 2. F-06: không đường nào tới máy B mà không giành suất ───────────────────

def test_planner_GIANH_SUAT_truoc_khi_goi_model(monkeypatch):
    """Có suất rảnh ⇒ nhánh model nhà được bật, và đi kèm một lease."""
    da_giu = {}

    class VeGia:
        id = "lease-gia"

    def gia_acquire(db, *, resource, slots, user_id, mode, holder_id, **_k):
        da_giu["resource"] = resource
        da_giu["slots"] = slots
        da_giu["holder"] = holder_id
        return VeGia()

    da_nha = []
    goi = {}

    class KetQua:
        noi_dung = '{"version":1,"steps":[]}'

    def gia_goi(db, **kw):
        goi.update(kw)
        return KetQua()

    from platform_core.llm import admission, dieu_phoi
    monkeypatch.setattr(admission, "acquire", gia_acquire)
    monkeypatch.setattr(admission, "release_by_id", lambda i: da_nha.append(i))
    monkeypatch.setattr(dieu_phoi, "goi", gia_goi)

    planner._goi_model(None, "prompt thu")

    assert da_giu.get("resource") == "llm_remote", (
        "khong gianh suat -> day la mot duong toi may B lach admission")
    assert da_giu.get("slots") == 1
    assert str(da_giu.get("holder", "")).startswith("planner:")
    assert "ltt_llm" in goi["thu_tu_provider"], "co suat ma van bo model nha"
    assert goi["model_theo_provider"]["ltt_llm"] == planner._model_nha()
    assert da_nha == ["lease-gia"], "khong nha suat -> giu mai mot suat duy nhat"


def test_BAN_thi_BO_nhanh_model_nha_chu_KHONG_xep_hang(monkeypatch):
    """Không giành được suất ⇒ đi thẳng Gemini.

    ⭐ Xếp hàng chờ ở đây là để một việc **nội bộ** chen chỗ một request khách
       đang trả tiền — đổi thứ tự ưu tiên sai hướng.
    """
    goi = {}

    class KetQua:
        noi_dung = '{"version":1,"steps":[]}'

    from platform_core.llm import admission, dieu_phoi
    monkeypatch.setattr(admission, "acquire", lambda *a, **k: None)
    monkeypatch.setattr(admission, "release_by_id",
                        lambda i: pytest.fail("nha mot ve chua bao gio giu duoc"))
    monkeypatch.setattr(dieu_phoi, "goi",
                        lambda db, **kw: (goi.update(kw), KetQua())[1])

    planner._goi_model(None, "prompt thu")

    assert "ltt_llm" not in goi["thu_tu_provider"], (
        "khong co suat ma van thu model nha -> hoac xep hang an, hoac lach")
    assert "gemini" in goi["thu_tu_provider"], "bo luon ca duong lui"


def test_NHA_SUAT_ca_khi_dieu_phoi_NEM(monkeypatch):
    """Giữ một suất sau khi hỏng đúng bằng chiếm nó vĩnh viễn."""
    da_nha = []

    class VeGia:
        id = "lease-gia"

    from platform_core.llm import admission, dieu_phoi
    monkeypatch.setattr(admission, "acquire", lambda *a, **k: VeGia())
    monkeypatch.setattr(admission, "release_by_id", lambda i: da_nha.append(i))

    def no(db, **kw):
        raise dieu_phoi.KhongCoProviderNao("moi provider deu ban")

    monkeypatch.setattr(dieu_phoi, "goi", no)

    with pytest.raises(planner.PlannerError):
        planner._goi_model(None, "prompt thu")
    assert da_nha == ["lease-gia"], "hong giua chung thi suat bi giu lai"


# ── 3. Tài nguyên đọc từ bản khai, không phải bản sao thứ hai ────────────────

def test_tai_nguyen_doc_tu_BAN_KHAI_cua_app():
    from apps.ltt_llm.manifest import MANIFEST

    tool = next(t for t in MANIFEST.tools if t.admission_resource)
    assert planner._tai_nguyen_nha() == (tool.admission_resource,
                                         tool.admission_slots)
