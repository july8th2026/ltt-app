"""test_1212 — Model cho việc LLM **nội bộ** khai theo app (D09, dual-model 2.4).

🔴 VẤN ĐỀ CƠ HỌC MÀ D09 SINH RA ĐỂ CHẶN — đọc trước khi sửa bất cứ gì ở đây.

    D01 B cho model ảnh **mượn RTX 3090** trong cửa sổ sinh ảnh, nên `ltt-3.8`
    (cư trú 3090) **không nạp được** trong lúc một job ảnh đang chạy. Job ảnh
    của `anhnoibo`/`taoanh`/`thumbnail` lại dịch prompt *từ bên trong job* —
    tức nó đang **GIỮ** 3090 và đi **CHỜ** một model chỉ nạp được sau khi 3090
    rảnh.

        job ảnh giữ 3090 ──chờ──> LTT-3.8 ──chờ──> 3090 rảnh ──> job ảnh

    Vòng chờ kín. Không ngoại lệ, không log, không mã lỗi: job treo tới hết
    trần thời gian rồi chết vì "quá giờ" — một thông điệp trỏ sai hướng hoàn
    toàn. Đó là lý do chốt này phải đứng ở **gate**, chứ không đợi tới lúc chạy.

⭐ VÀ MẶC ĐỊNH `ltt-3.5` KHÔNG PHẢI MỘT SỰ HY SINH. Đo trên máy B 11/09/2026:

        LTT-3.5   73   tok/s   cửa sổ 262.144   RTX 5060 Ti   3 slot
        LTT-3.8   66,7 tok/s   cửa sổ 221.184   RTX 3090      3 slot

   Việc nội bộ vừa hết kẹt residency vừa **nhanh hơn**. Ai đọc `ltt-3.5` ở đây
   như "bản rẻ tiền cho việc phụ" là đọc ngược.

⚠️ Plan (Task 2.4 Step 1) còn ghi *"planner… vẫn rơi Gemini khi bận"*. Câu ấy
   **đã cũ**: cascade Gemini bị gỡ 08/09/2026 (`planner.py`, D09 hệ quả 3), nay
   hết chỗ là `PlannerError`. Tệp này chốt theo bản đính chính, và chốt luôn
   rằng đường lui ấy **không được quay lại**.
"""
from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from platform_core import registry
from platform_core.llm import canonical as C

GOC = pathlib.Path(registry.__file__).resolve().parent.parent
THU_MUC_APP = GOC / "apps"

#: Model **không bao giờ** được dùng cho việc nội bộ của một app giữ card ảnh.
MODEL_KET_CARD_ANH = "ltt-3.8"


# ════════════════════════════════════════════════════════════════════════════
# Dụng cụ đo — dùng chung cho phép kiểm VÀ cho đối chứng của nó
# ════════════════════════════════════════════════════════════════════════════

def _app_goi_dich_anh() -> set[str]:
    """App nào gọi `dich_llm.goi_llm` (⇒ dịch prompt từ TRONG job ảnh).

    Đọc **AST**, không gõ tay danh sách: ngày mai có app ảnh thứ tư thì nó tự
    rơi vào phép kiểm này mà không ai phải nhớ sửa tệp test — đúng khuôn
    "nền tảng không được biết tên app nào tồn tại".
    """
    ra: set[str] = set()
    for tep in sorted(THU_MUC_APP.glob("*/*.py")):
        try:
            cay = ast.parse(tep.read_bytes())
        except SyntaxError:                                    # pragma: no cover
            continue
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ham = nut.func
            if not (isinstance(ham, ast.Attribute) and ham.attr == "goi_llm"):
                continue
            goc = ham.value
            ten_goc = goc.attr if isinstance(goc, ast.Attribute) else getattr(
                goc, "id", "")
            if ten_goc == "dich_llm":
                ra.add(tep.parent.name)
    return ra


def _app_giu_tai_nguyen_anh() -> set[str]:
    """App khai một tool chiếm card ảnh (`residency_group` + `vai_tro=theo_lo`).

    ⚠️ Tập này **rỗng hôm nay** — bản khai `anh_3090` thuộc Task 5.5. Nó nằm ở
       đây để ngày ấy tới thì bất biến tự phủ luôn, KHÔNG phải để làm bằng
       chứng: một bất biến chỉ đo tập rỗng là một bất biến luôn xanh. Sức nặng
       của phép kiểm nằm ở `_app_goi_dich_anh()` ngay trên.
    """
    ra: set[str] = set()
    for it in registry.discover():
        for t in it.manifest.tools:
            theo_model = getattr(t, "admission_theo_model", None) or {}
            for suc in theo_model.values():
                if (getattr(suc, "residency_group", "")
                        and getattr(suc, "vai_tro", "") == "theo_lo"):
                    ra.add(it.manifest.slug)
    return ra


def _vi_pham_vong_cho(slugs) -> list[str]:
    """App nào trong `slugs` khai model nội bộ là model đang cư trú card ảnh."""
    return sorted(s for s in slugs
                  if C.model_noi_bo_cua(s) == MODEL_KET_CARD_ANH)


# ════════════════════════════════════════════════════════════════════════════
# A. Bản khai: mặc định, và HAI hằng số không được gộp
# ════════════════════════════════════════════════════════════════════════════

def test_mac_dinh_cua_hop_dong_la_ltt_35():
    """App không khai gì ⇒ `ltt-3.5`. Đây là *mặc định tài liệu hoá* của D09."""
    assert registry.AppManifest(
        slug="x", display_name="X", route_prefix="/x").model_llm_noi_bo == "ltt-3.5"
    assert C.MODEL_NOI_BO_MAC_DINH == "ltt-3.5"
    assert C.MODEL_NOI_BO_MAC_DINH in C.MODEL_HOP_LE


def test_go_khai_bao_thi_ROI_VE_mac_dinh_chu_khong_hong(monkeypatch):
    """Chiều ngược: xoá dòng khai của một app ⇒ về mặc định, không nổ.

    ⭐ Đây là nửa mà một phép kiểm "đường hạnh phúc" hay bỏ sót. Trường này
       **additive**: mọi manifest hôm nay đều không khai nó, nên nếu mặc định
       không chạy thì 22 app hỏng cùng lúc.
    """
    from apps.anhnoibo import manifest as m

    khong_khai = registry.AppManifest(
        slug=m.MANIFEST.slug, display_name=m.MANIFEST.display_name,
        route_prefix=m.MANIFEST.route_prefix)
    monkeypatch.setattr(m, "MANIFEST", khong_khai, raising=True)
    assert C.model_noi_bo_cua("anhnoibo") == C.MODEL_NOI_BO_MAC_DINH


def test_moi_app_deu_doc_duoc_mot_bi_danh_HOP_LE():
    """Không app nào trả về một tên ngoài bảng hai model công khai."""
    slugs = [it.manifest.slug for it in registry.discover()]
    assert slugs, "registry khong nap duoc app nao — phep kiem duoi se rong"
    xau = {s: C.model_noi_bo_cua(s) for s in slugs
           if C.model_noi_bo_cua(s) not in C.MODEL_HOP_LE}
    assert not xau, f"app khai model noi bo khong hop le: {xau}"


def test_app_khong_ton_tai_thi_CANH_BAO_chu_khong_im_lang(caplog):
    """Hỏi một slug không có ⇒ mặc định **kèm log**.

    ⛔ Rơi về mặc định trong im lặng là cách một lỗi gõ slug sống mãi: đường gọi
       vẫn chạy, vẫn đúng model, và không ai biết bản khai chưa bao giờ được đọc.
    """
    import logging

    with caplog.at_level(logging.WARNING, logger=C.__name__):
        assert C.model_noi_bo_cua("khong_he_co_app_nay") == C.MODEL_NOI_BO_MAC_DINH
    assert any("khong_he_co_app_nay" in r.getMessage() for r in caplog.records)


def test_HAI_hang_so_tra_loi_HAI_cau_khac_nhau():
    """`MODEL_MAC_DINH` (khách) và `MODEL_NOI_BO_MAC_DINH` (nội bộ) là hai thứ.

    ⚠️ Phép kiểm này KHÔNG chốt "hai giá trị phải khác nhau" — ngày cả hai cùng
       trỏ một model là một quyết định hợp lệ. Nó chốt thứ không được đổi: hai
       **tên** còn tồn tại riêng, nên bên gọi vẫn phải nói ra nó đang trả lời
       câu nào.
    """
    assert isinstance(C.MODEL_MAC_DINH, str) and C.MODEL_MAC_DINH in C.MODEL_HOP_LE
    assert C.MODEL_NOI_BO_MAC_DINH in C.MODEL_HOP_LE
    assert C.model_noi_bo_cua.__doc__, "ham phai tu khai no tra loi cau nao"


# ════════════════════════════════════════════════════════════════════════════
# B. Hợp đồng registry: tên lạ bị TỪ CHỐI TO TIẾNG, không rơi về mặc định
# ════════════════════════════════════════════════════════════════════════════

def _validate(manifest) -> None:
    registry._validate(manifest, set(), set(), set(), set(), set())


@pytest.mark.parametrize("xau", ["ltt-3.50", "ltt_llm", "qwen35-api", "", "gpt-4o"])
def test_khai_model_la_thi_REGISTRY_TU_CHOI(xau):
    """Giá trị lạ ⇒ `RegistryError` lúc nạp, không phải một mặc định âm thầm.

    Bốn ca không phải trang trí — chúng là bốn cách sai **khác nhau**:
    lỗi gõ (`ltt-3.50`), tên đã cắt (`ltt_llm`, D02), **id nội bộ** lọt ra chỗ
    chỉ nhận bí danh (`qwen35-api`), và rỗng.
    """
    m = registry.AppManifest(slug="x", display_name="X", route_prefix="/x",
                             model_llm_noi_bo=xau)
    with pytest.raises(registry.RegistryError) as loi:
        _validate(m)
    assert "model_llm_noi_bo" in str(loi.value)


@pytest.mark.parametrize("tot", list(C.MODEL_HOP_LE))
def test_DOI_CHUNG_moi_bi_danh_hop_le_deu_QUA_duoc(tot):
    """Đối chứng cho phép kiểm ngay trên: bộ kiểm không từ chối **mọi** giá trị.

    ⛔ Không có ca này thì một bản cài hỏng — `raise` vô điều kiện — vẫn xanh
       ở năm ca trên, và mọi app sẽ ngừng nạp mà phép kiểm vẫn báo tốt.
    """
    _validate(registry.AppManifest(slug="x", display_name="X",
                                   route_prefix="/x", model_llm_noi_bo=tot))


def test_DOI_CHUNG_bo_kiem_phai_THUC_SU_doc_truong_nay(monkeypatch):
    """Tiêm bản CŨ (hợp đồng không có trường) ⇒ phép kiểm trên phải ĐỎ.

    ⭐ Đây là đối chứng cho *chính bộ kiểm*, không cho bản khai: nếu ai gỡ khối
       `if manifest.model_llm_noi_bo not in MODEL_HOP_LE` thì năm ca ở trên đỏ —
       và đó là điều ca này chứng minh bằng cách dựng lại tình huống ấy.
    """
    goc = pathlib.Path(registry.__file__).read_text(encoding="utf-8")
    assert "model_llm_noi_bo not in" in goc, (
        "bo kiem da bien mat khoi `_validate` — mot ten la nay roi ve mac dinh "
        "im lang, dung thu D09 cam")


# ════════════════════════════════════════════════════════════════════════════
# C. 🔴 CHỐT VÒNG CHỜ — phép kiểm máy mà D09 đòi
# ════════════════════════════════════════════════════════════════════════════

def test_bo_do_THUC_SU_tim_thay_duong_dich_anh():
    """Đối chứng cho bộ dò: tập app dịch prompt ảnh **không được rỗng**.

    ⛔ Một bất biến "với mọi app trong tập S…" xanh tuyệt đối khi S rỗng. Đo
       12/09/2026: ba app (`anhnoibo`, `taoanh`, `thumbnail`). Ngày con số này
       tụt xuống, phép kiểm dưới mất hết sức nặng **mà vẫn xanh** — nên nó phải
       đỏ ở đây trước, để người sửa buộc phải nhìn lại chứ không chỉ xoá.
    """
    nhom = _app_goi_dich_anh()
    assert len(nhom) >= 3, (
        f"chi tim thay {sorted(nhom)} app goi `dich_llm.goi_llm` — 12/09/2026 "
        f"co ba. Bo do hong, hoac duong dich anh da doi hinh dang")


def test_KHONG_app_anh_nao_tro_model_dang_CU_TRU_CARD_ANH():
    """🔴 Bất biến trung tâm của D09: app giữ card ảnh **không** dùng `ltt-3.8`."""
    nhom = _app_goi_dich_anh() | _app_giu_tai_nguyen_anh()
    assert nhom, "tap rong — xem `test_bo_do_THUC_SU_tim_thay_duong_dich_anh`"
    assert _vi_pham_vong_cho(nhom) == [], (
        "VONG CHO: app tren giu card anh (3090) va lai cho mot model chi nap "
        "duoc sau khi card do ranh. Job se treo den het tran thoi gian, khong "
        "loi, khong log")


def test_DOI_CHUNG_khai_ltt_38_cho_anhnoibo_thi_DO(monkeypatch):
    """Tiêm đúng bản khai chết người ⇒ bất biến trên phải bắt được.

    Không có ca này thì `test_KHONG_app_anh_nao_...` xanh vì **chưa ai khai
    sai**, chứ không vì nó biết phát hiện ra.
    """
    from apps.anhnoibo import manifest as m

    monkeypatch.setattr(
        m, "MANIFEST",
        dataclasses.replace(m.MANIFEST, model_llm_noi_bo=MODEL_KET_CARD_ANH),
        raising=True)
    nhom = _app_goi_dich_anh() | _app_giu_tai_nguyen_anh()
    assert _vi_pham_vong_cho(nhom) == ["anhnoibo"], (
        "bat bien vong cho KHONG phat hien duoc mot ban khai `ltt-3.8` that")


def test_moi_cho_goi_dich_anh_deu_TRUYEN_slug_app():
    """Bên gọi phải nói app nào — nếu không, `dich_llm` không đọc được bản khai.

    ⚠️ Đọc AST chứ không grep: một chuỗi `slug_app` trong docstring không phải
       một tham số được truyền.
    """
    thieu = []
    dem = 0
    for tep in sorted(THU_MUC_APP.glob("*/*.py")):
        try:
            cay = ast.parse(tep.read_bytes())
        except SyntaxError:                                    # pragma: no cover
            continue
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ham = nut.func
            if not (isinstance(ham, ast.Attribute) and ham.attr == "goi_llm"):
                continue
            goc = ham.value
            ten_goc = goc.attr if isinstance(goc, ast.Attribute) else getattr(
                goc, "id", "")
            if ten_goc != "dich_llm":
                continue
            dem += 1
            if not any(kw.arg == "slug_app" for kw in nut.keywords):
                thieu.append(f"{tep.parent.name}/{tep.name}:{nut.lineno}")
    assert dem >= 3, f"bo do chi thay {dem} loi goi — no da thoi nhin thay thu no do"
    assert thieu == [], f"goi `dich_llm.goi_llm` ma khong noi app nao: {thieu}"


# ════════════════════════════════════════════════════════════════════════════
# D. Đường gọi THẬT — lease rơi đúng pool của model đã khai
# ════════════════════════════════════════════════════════════════════════════

class _Ve:
    id = "ve-gia"


def _bay_admission(monkeypatch, da_giu: dict, da_nha: list):
    from platform_core.llm import admission

    def gia(db, *, resource, slots, user_id, mode, holder_id, **_k):
        da_giu.update(resource=resource, slots=slots, holder=holder_id)
        return _Ve()

    monkeypatch.setattr(admission, "acquire", gia)
    monkeypatch.setattr(admission, "release_by_id", lambda i: da_nha.append(i))


class _KetQua:
    noi_dung = "A calico cat on a windowsill"


def test_dich_prompt_anh_GIANH_LEASE_tren_pool_cua_model_da_khai(monkeypatch):
    """`dich_llm.goi_llm(slug_app="anhnoibo")` ⇒ lease `ltt_35_5060`, gọi 3.5.

    ⭐ Phép đo là **SỰ TƯƠNG PHẢN**, không phải một tên gõ tay: bản chụp phải
       khớp `tai_nguyen_nha("ltt-3.5")` VÀ khác `tai_nguyen_nha("ltt-3.8")`.
       Một bản cài hỏng (vẫn dùng `MODEL_MAC_DINH`) khớp vế sau, nên chỉ kiểm
       một vế là kiểm một điều luôn đúng.
    """
    from platform_core.image_gen import dich_llm
    from platform_core.llm import dieu_phoi

    da_giu: dict = {}
    da_nha: list = []
    goi: dict = {}
    _bay_admission(monkeypatch, da_giu, da_nha)
    monkeypatch.setattr(dieu_phoi, "goi",
                        lambda db, **kw: (goi.update(kw), _KetQua())[1])

    van = dich_llm.goi_llm("con meo", "dich sang tieng Anh", db=None,
                           slug_app="anhnoibo")

    nha_35 = C.tai_nguyen_nha("ltt-3.5")
    nha_38 = C.tai_nguyen_nha("ltt-3.8")
    assert nha_35.resource != nha_38.resource, (
        "hai model dung chung mot tai nguyen — phep kiem nay khong con phan "
        "biet duoc gi, phai viet lai chu khong phai sua")
    assert da_giu["resource"] == nha_35.resource == "ltt_35_5060"
    assert da_giu["slots"] == nha_35.slots
    assert goi["model_theo_provider"] == C.ban_do_model("ltt-3.5")
    assert da_nha == [_Ve.id], "khong nha suat -> giu mai mot suat duy nhat"
    assert van == _KetQua.noi_dung


def test_planner_di_MODEL_NOI_BO_chu_khong_phai_model_ban_cho_khach(monkeypatch):
    """Planner: id gửi đi là `ltt-3.5` → `qwen35-api`, lease trên pool của nó."""
    from platform_core.agent import planner
    from platform_core.llm import dieu_phoi

    da_giu: dict = {}
    da_nha: list = []
    goi: dict = {}
    _bay_admission(monkeypatch, da_giu, da_nha)

    class KeHoach:
        noi_dung = '{"version":1,"steps":[]}'

    monkeypatch.setattr(dieu_phoi, "goi",
                        lambda db, **kw: (goi.update(kw), KeHoach())[1])

    planner._goi_model(None, "prompt thu")

    nha = C.tai_nguyen_nha(C.MODEL_NOI_BO_MAC_DINH)
    assert da_giu["resource"] == nha.resource
    assert goi["model_theo_provider"]["ltt_llm"] == C.ALIAS_SANG_ID[
        C.MODEL_NOI_BO_MAC_DINH]
    assert da_nha == [_Ve.id]


def test_planner_KHONG_co_duong_lui_provider_ngoai():
    """Đính chính plan: hết chỗ là `PlannerError`, không phải rơi Gemini.

    🔴 Cascade Gemini bị gỡ 08/09/2026 sau khi đo 28 ngày log worker: thông
       điệp lỗi thật ghi `khong provider nao phuc vu duoc: ltt_llm: ban` —
       danh sách **một phần tử**, Gemini chưa từng đỡ lượt hỏng nào. Task 2.4
       KHÔNG được dựng lại đường ấy.
    """
    from platform_core.agent import planner

    assert tuple(planner.PLANNER_PROVIDERS) == ("ltt_llm",)


def test_planner_song_sot_khi_ca_hai_model_deu_KHAI_DOC_ANH(monkeypatch):
    """Bánh cóc cho Task 3.3: chọn model nhà **không** được dựa vào cờ `vision`.

    🔴 Bản trước lọc "model text đầu tiên KHÔNG có cờ `vision`". Task 3.3 nạp
       mmproj cho `qwen38-api` ⇒ cả hai model đều có cờ ⇒ vòng lặp trả rỗng ⇒
       `PlannerError("registry khong khai model text nao")` và planner chết
       hẳn. Phép kiểm này dựng đúng tương lai ấy hôm nay.
    """
    from platform_core import providers
    from platform_core.agent import planner
    from platform_core.models import APIKEY_CAT_CHAT

    that = list(providers.models_for("ltt_llm", APIKEY_CAT_CHAT))
    assert that, "registry khong khai model nao — ca nay khong do duoc gi"

    class _M:
        def __init__(self, m):
            self.id = m.id
            self.capabilities = dict(getattr(m, "capabilities", None) or {},
                                     vision=True)

    monkeypatch.setattr(providers, "models_for",
                        lambda *a, **k: [_M(m) for m in that])
    assert planner._model_nha() == C.ALIAS_SANG_ID[C.MODEL_NOI_BO_MAC_DINH]


# ════════════════════════════════════════════════════════════════════════════
# E. Bánh cóc: không người gọi nội bộ nào được quay lại `MODEL_MAC_DINH`
# ════════════════════════════════════════════════════════════════════════════

NGUOI_GOI_NOI_BO = (
    "platform_core/image_gen/dich_llm.py",
    "platform_core/agent/planner.py",
    "apps/taovideo/translate.py",
    "apps/autosubvideo/ai_workflows.py",
    "apps/prompt_ai_ommi/provider.py",
)


def _ten_doc_trong(tep: pathlib.Path) -> set[str]:
    """Mọi định danh được **đọc** trong tệp (AST), không tính chuỗi/chú thích."""
    cay = ast.parse(tep.read_bytes())
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Attribute):
            ra.add(nut.attr)
        elif isinstance(nut, ast.Name):
            ra.add(nut.id)
        elif isinstance(nut, ast.alias):
            ra.add(nut.name.rsplit(".", 1)[-1])
    return ra


@pytest.mark.parametrize("duong", NGUOI_GOI_NOI_BO)
def test_nguoi_goi_noi_bo_KHONG_con_doc_MODEL_MAC_DINH(duong):
    """Bánh cóc D09: việc nội bộ đọc bản khai, không đọc mặc định của khách.

    ⚠️ Đọc **AST** chứ không quét văn bản — docstring của chính các tệp này
       *trích dẫn* `MODEL_MAC_DINH` để kể lại vì sao nó bị thay. Một bánh cóc
       không phân biệt được mã với lời kể về mã thì nó cấm luôn việc ghi lại
       bài học (`test_389` đã học đúng bài này một lần).
    """
    ten = _ten_doc_trong(GOC / duong)
    assert "MODEL_MAC_DINH" not in ten, (
        f"{duong} doc lai mac dinh CUA KHACH cho viec NOI BO — D09 doi no doc "
        f"ban khai cua app (`model_noi_bo_cua`) hoac `MODEL_NOI_BO_MAC_DINH`")


@pytest.mark.parametrize("duong", NGUOI_GOI_NOI_BO)
def test_DOI_CHUNG_bo_do_nhin_thay_duong_MOI(duong):
    """Đối chứng: bộ dò trên phải thấy **cái đã thay thế**, không chỉ thấy vắng.

    ⛔ Không có ca này, xoá sạch mọi lời gọi LLM khỏi năm tệp cũng làm phép
       kiểm trên xanh — "đo sự vắng mặt thì xoá cũng xanh".
    """
    ten = _ten_doc_trong(GOC / duong)
    assert ten & {"model_noi_bo_cua", "MODEL_NOI_BO_MAC_DINH"}, (
        f"{duong} khong con doc duong D09 nao — bo do o tren dang do mot tep "
        f"rong, khong do mot ban va")
