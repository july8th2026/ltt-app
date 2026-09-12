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


def test_model_nha_LA_MODEL_NOI_BO_DA_KHAI():
    """Planner đi model **nội bộ** đã khai (`ltt-3.5`), không phải một suy luận.

    🔴 PHÉP ĐO CŨ ĐÃ BỊ **BỎ**, KHÔNG PHẢI SỬA — và lý do đáng ghi lại.

       Bản trước chốt *"`_model_nha()` không được chọn bản đọc ảnh"*, với lý do
       *"bản vision có cửa sổ nhỏ hơn một nửa (65.536 thay vì 131.072)"*. Mệnh
       đề ấy đúng khi model thứ hai là hồ sơ `qwen38-vision` `-c 65536`. Hồ sơ
       đó **đã gỡ 11/09/2026** (D02). Hai model công khai hôm nay chạy cùng ngữ
       cảnh engine, và model nội bộ `ltt-3.5` **có** `vision: True` — nên phép
       kiểm cũ đỏ **vì bản khai ĐÚNG**, và cách duy nhất làm nó xanh lại là
       chọn sai model. Nó đã thành một phép kiểm *cưỡng chế khuyết tật*.

    ⇒ Thay bằng mệnh đề về **nguồn**: planner đọc bản khai model nội bộ (D09),
      không suy ra model từ một cờ năng lực. Xem thêm
      `tests/test_1212_llm_noi_bo_theo_app.py` — nó dựng lại tương lai Task 3.3
      (cả hai model đều khai `vision`) và chốt planner vẫn sống.
    """
    from platform_core.llm import canonical

    assert planner._model_nha() == canonical.ALIAS_SANG_ID[
        canonical.MODEL_NOI_BO_MAC_DINH]


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

    # ⛔ ĐỌC TỪ BẢN KHAI, không gõ `"llm_remote"`. Từ dual-model 2.3 sức chứa
    #    khai THEO MODEL, nên một tên gõ tay ở đây đỏ vì chính nó đã cũ — và
    #    ngày nó được "sửa" bằng một tên gõ tay khác, khuyết tật quay lại.
    #    ⭐ D09 (2.4): và model là model **NỘI BỘ**, không phải mặc định bán cho
    #      khách — lease phải nằm ở pool KV của đúng card sắp chạy lượt này.
    from platform_core.llm.canonical import MODEL_NOI_BO_MAC_DINH, tai_nguyen_nha
    suc = tai_nguyen_nha(MODEL_NOI_BO_MAC_DINH)
    assert da_giu.get("resource") == suc.resource, (
        "khong gianh suat -> day la mot duong toi may B lach admission")
    assert da_giu.get("slots") == suc.slots
    assert str(da_giu.get("holder", "")).startswith("planner:")
    assert "ltt_llm" in goi["thu_tu_provider"], "co suat ma van bo model nha"
    assert goi["model_theo_provider"]["ltt_llm"] == planner._model_nha()
    assert da_nha == ["lease-gia"], "khong nha suat -> giu mai mot suat duy nhat"


def test_BAN_thi_HONG_CO_TEN_chu_KHONG_xep_hang_va_KHONG_di_duong_ngoai(monkeypatch):
    """Không giành được suất ⇒ **hỏng có tên**, không xếp hàng, không đường ngoài.

    ⭐ Bất biến tệp này canh **KHÔNG ĐỔI**: xếp hàng chờ ở đây là để một việc
       **nội bộ** chen chỗ một request khách đang trả tiền — sai thứ tự ưu tiên.

    🔴 CẬP NHẬT 08/09/2026 — pha 05.3 (AI CLEAN REBUILD V2). Bản cũ chốt
       *"⇒ đi thẳng Gemini"* và đòi `"gemini" in thu_tu_provider`. Đường lui ấy
       **đã bị gỡ**: đo 28 ngày log worker production cho thấy nó không hề đỡ
       1,1% lượt hỏng vì máy B bận — thông điệp lỗi thật ghi
       `khong provider nao phuc vu duoc: ltt_llm: ban`, danh sách **chỉ một
       phần tử**. Nó là nhánh chỉ chạy khi không ai nhìn.

    ⇒ **Kỳ vọng đổi, bất biến thì không.** Và bản mới chốt **mạnh hơn** bản cũ:
       trước chỉ đòi `"ltt_llm"` vắng mặt trong thứ tự; nay đòi `dieu_phoi.goi`
       **không được gọi một lần nào** — không đường nào chạm máy B, kể cả một
       đường vòng chưa ai nghĩ ra.

    ⛔ Và lỗi phải **CÓ TÊN**: `AGENTS.md` §4c câu 2 đòi *cố ý* phân biệt được
       với *tai nạn*. Một `PlannerError` trống rỗng thì hai thứ nhìn giống hệt.
    """
    from platform_core.llm import admission, dieu_phoi
    monkeypatch.setattr(admission, "acquire", lambda *a, **k: None)
    monkeypatch.setattr(admission, "release_by_id",
                        lambda i: pytest.fail("nha mot ve chua bao gio giu duoc"))
    monkeypatch.setattr(dieu_phoi, "goi",
                        lambda db, **kw: pytest.fail(
                            "khong co suat ma van goi model -> xep hang an, "
                            "lach admission, hoac di mot duong ngoai"))

    with pytest.raises(planner.PlannerError) as loi:
        planner._goi_model(None, "prompt thu")

    van = str(loi.value)
    assert "suat" in van or "san sang" in van, (
        f"loi phai NOI RA vi sao, khong duoc trong nhu mot tai nan: {van!r}")
    assert "KHONG co duong lui" in van, (
        "thong diep phai khai ro khong con provider ngoai — nguoi doc log sau "
        "nay se hoi dung cau do")


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
    """⭐ Từ multijob 2.2 câu hỏi là *"tài nguyên của MODEL nào"*, nên phép so
    cũng hỏi bản khai bằng đúng câu ấy (`admission_cho`) thay vì đọc ba trường
    tĩnh — bộ ba đó chỉ tả được MỘT pool, còn `text.chat` sắp có hai.
    """
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import canonical

    model = canonical.MODEL_MAC_DINH
    tool = next(t for t in MANIFEST.tools if t.admission_cho(model) is not None)
    assert planner._tai_nguyen_nha(model) == tool.admission_cho(model)
