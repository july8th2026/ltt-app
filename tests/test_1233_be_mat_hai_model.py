"""Bề mặt công khai phải phục vụ **cả hai** model, không chỉ model mặc định.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — MỘT SẢN PHẨM ĐANG BÁN MÀ KHÔNG CÓ CỬA VÀO.

   Từ 11/09/2026 nền tảng bán hai model (`ltt-3.8`, `ltt-3.5`) với **hai bảng
   giá**. Đo lại toàn bộ bề mặt công khai ngày 12/09 thì thấy `ltt-3.5` gần như
   không tồn tại ở ngoài:

   | Bề mặt | Trước 12/09 |
   |---|---|
   | `platform_core/public_api/examples.py` | gõ tay MỘT tên, ở bốn chỗ |
   | Claude Desktop (`TUYEN_TUONG_THICH`) | **một** tuyến ⇒ `ltt-3.5` KHÔNG gọi được ở mọi giá |
   | `tools/cam_cli.py` + GUI | `MODEL` gõ cứng, không có cách chọn |
   | `sdk/ltt_cai_dat_cli.py` | gõ cứng, **và in sai** `inferenceModels` |
   | `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md` | tên đã cắt + số đã cũ 26% |

   Không phép kiểm nào đỏ, vì mỗi bề mặt **tự nhất quán với chính nó**. Đó là
   hình dạng lỗi mà tệp này được viết ra để giữ: không phải một giá trị sai, mà
   một **danh sách thứ hai** âm thầm ngắn hơn danh sách thật.

⭐ NGUYÊN TẮC CHUNG CỦA CẢ TỆP: *danh sách model chỉ được có MỘT nguồn*
   (`canonical.ALIAS_SANG_ID`). Mọi bề mặt hoặc **dẫn** từ đó, hoặc **chép** nó
   và bị buộc hai đầu ở đây. Không bề mặt nào được tự khai một danh sách riêng.

⚠️ Và mỗi phép kiểm dưới đây đi kèm **đối chứng**: một mệnh đề phải ĐỎ nếu cơ
   chế bị gỡ. Một phép kiểm chỉ nói "hai tên có mặt" sẽ vẫn xanh khi ai đó dán
   cứng hai tên vào từng bề mặt — tức xanh cho đúng thứ ta đang đi dẹp.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import re

import pytest

from apps.ltt_llm import ngan_sach
from platform_core.llm import canonical
from platform_core.public_api import examples

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Tên đã bị cắt ở D02 (dual-model 2.3). Không tên nào trong đây còn là model.
TEN_DA_CAT = ("ltt_llm_vision", "qwen38-vision")


def _nap(duong: pathlib.Path, ten: str):
    """Nạp một tệp công cụ **đứng riêng** như một module."""
    spec = importlib.util.spec_from_file_location(ten, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cam_cli():
    return _nap(GOC / "tools" / "cam_cli.py", "cam_cli_1233")


@pytest.fixture(scope="module")
def sdk_cli():
    return _nap(GOC / "sdk" / "ltt_cai_dat_cli.py", "sdk_cli_1233")


# ── 1. `examples` DẪN danh sách, không gõ nó ────────────────────────────────

def test_cli_models_dan_tu_canonical_chu_khong_go_tay():
    """Bằng nhau là chưa đủ — nó phải bằng nhau **vì được dẫn ra**.

    ⛔ Một phép kiểm `CLI_MODELS == ("ltt-3.8", "ltt-3.5")` xanh y hệt khi hai
       tên được dán cứng, tức nó **không đo** thứ ta cần: rằng thêm một model ở
       `canonical` thì trang công khai có nó ngay. Nên ở đây đọc AST: vế phải
       của phép gán phải là một **lời gọi**, không phải một tuple hằng.
    """
    assert examples.CLI_MODELS == tuple(canonical.MODEL_HOP_LE)
    assert examples.CLI_MODEL == canonical.MODEL_MAC_DINH
    assert examples.CHAT_MODEL == canonical.MODEL_MAC_DINH

    cay = ast.parse((GOC / "platform_core" / "public_api" / "examples.py")
                    .read_text(encoding="utf-8"))
    ve_phai = {}
    for nut in cay.body:
        đích = (nut.targets[0] if isinstance(nut, ast.Assign)
                else getattr(nut, "target", None) if isinstance(nut, ast.AnnAssign)
                else None)
        if isinstance(đích, ast.Name) and nut.value is not None:
            ve_phai[đích.id] = nut.value

    for ten in ("CLI_MODELS", "CLI_MODEL", "CHAT_MODEL"):
        gt = ve_phai.get(ten)
        assert gt is not None, f"{ten} khong con la mot phep gan cap module"
        assert not isinstance(gt, (ast.Constant, ast.Tuple, ast.List)), (
            f"`examples.{ten}` dang go TAY mot gia tri. No phai DAN tu "
            f"`canonical`, neu khong thi trang cong khai se tut lai sau nen "
            f"tang dung nhu truoc 12/09 — va khong phep kiem nao thay.")


# ── 2. Claude Desktop: MỘT bảng, và nó phủ cả hai model ─────────────────────

def test_moi_model_deu_co_mot_tuyen_desktop_rieng():
    tuyen = examples.TUYEN_DESKTOP
    assert set(tuyen.values()) == set(canonical.MODEL_HOP_LE), (
        f"tuyen Desktop phu {sorted(set(tuyen.values()))} trong khi ban "
        f"{sorted(canonical.MODEL_HOP_LE)}. Model thieu tuyen la model KHONG "
        f"goi duoc tu Claude Desktop o bat ky gia nao.")
    assert len(set(tuyen)) == len(tuyen), "hai model dung chung mot ten tuyen"


@pytest.mark.parametrize("alias", canonical.MODEL_HOP_LE)
def test_cua_stream_giai_duoc_tuyen_cua_tung_model(alias):
    from server.api import streaming

    tuyen = examples.tuyen_desktop_cho(alias)
    assert streaming._giai_ten_model(tuyen) == alias


def test_doi_chung_ten_tuyen_bia_KHONG_duoc_giai_ve_model_nao():
    """Đối chứng. Không có nó, phép kiểm trên vẫn xanh với một `dict` bắt-tất.

    ⛔ Và "bắt tất" ở đây không phải chuyện lý thuyết: một tuyến lạ rơi về model
       mặc định nghĩa là khách gõ nhầm một ký tự và được **tính tiền theo bảng
       giá kia** mà không có lỗi nào.
    """
    from server.api import streaming

    bia = "ltt-llm-claude-compat-99"
    assert bia not in examples.TUYEN_DESKTOP
    assert streaming._giai_ten_model(bia) == bia, (
        "ten tuyen khong co that phai giu nguyen de loi no ra o cho cu "
        "(`model_not_found`), khong duoc am tham thanh mot model co that")


def test_bang_tuyen_cua_streaming_KHONG_phai_ban_sao_thu_hai():
    """Một bảng, hai nơi đọc — không phải hai bảng.

    ⚠️ Trước 12/09 `streaming` và `examples` mỗi bên gõ bảng của mình. Hai bản
       lệch nhau nghĩa là khách chép đúng thứ trang dạy rồi nhận `model_not_
       found`, và **mỗi bên vẫn tự nhất quán** nên không test nào đỏ.
    """
    from server.api import streaming

    assert streaming.TUYEN_TUONG_THICH == examples.TUYEN_DESKTOP

    van = (GOC / "server" / "api" / "streaming.py").read_text(encoding="utf-8")
    gan = re.search(r"^TUYEN_TUONG_THICH\s*=\s*(.+)$", van, re.M)
    assert gan, "khong tim thay phep gan TUYEN_TUONG_THICH"
    assert "examples" in gan.group(1), (
        f"`streaming.TUYEN_TUONG_THICH` phai DAN tu `examples.TUYEN_DESKTOP`, "
        f"dang la: {gan.group(1).strip()!r}")


# ── 3. Ba công cụ cắm khai cùng một bộ hồ sơ ────────────────────────────────

def test_ba_cong_cu_cam_khai_cung_hai_model(cam_cli, sdk_cli):
    assert cam_cli.TEN_MODEL == tuple(canonical.MODEL_HOP_LE)
    assert sdk_cli.TEN_MODEL == tuple(canonical.MODEL_HOP_LE)
    assert tuple(examples.CLI_MODELS) == tuple(canonical.MODEL_HOP_LE)


@pytest.mark.parametrize("alias", canonical.MODEL_HOP_LE)
def test_ho_so_cua_hai_cong_cu_khop_NGAN_SACH(cam_cli, sdk_cli, alias):
    """Hai bộ cài chạy trên máy khách nên phải **chép** số; chép thì buộc lại.

    ⛔ Mỗi hồ sơ phải mang cặp số CỦA CHÍNH NÓ. Dùng chung một cặp cho hai model
       là khuyết tật F-02, và hậu quả đo được của nó là một `413` giữa phiên:
       client nén ở ngưỡng của model kia nên nén muộn.
    """
    noi_bo = canonical.ALIAS_SANG_ID[alias]
    cho_doi = (ngan_sach.cong_bo_cua(noi_bo), ngan_sach.nen_cua(noi_bo))
    for mod, ten in ((cam_cli, "tools/cam_cli.py"),
                     (sdk_cli, "sdk/ltt_cai_dat_cli.py")):
        hs = mod.HO_SO_MODEL[alias]
        assert (hs.cua_so, hs.nen) == cho_doi, (
            f"{ten}: ho so {alias} khai (cua_so={hs.cua_so}, nen={hs.nen}) "
            f"trong khi `ngan_sach` noi {cho_doi}")
        assert hs.tuyen_desktop == examples.tuyen_desktop_cho(alias)


def test_hai_ho_so_KHONG_dung_chung_cap_so(cam_cli):
    """Đối chứng cho phép kiểm trên: hai model **thật sự** khác nhau.

    Nếu một ngày hai cửa sổ tình cờ bằng nhau, phép kiểm trên vẫn đúng nhưng
    **mất sức**: nó sẽ xanh cả khi ai đó gộp hai hồ sơ làm một. Dòng này nói
    thẳng ra rằng hôm nay chúng khác nhau, để lần gộp nhầm bị bắt tại chỗ.
    """
    a, b = (cam_cli.HO_SO_MODEL[t] for t in canonical.MODEL_HOP_LE)
    assert (a.cua_so, a.nen) != (b.cua_so, b.nen)


# ── 4. `cam_cli` ghi ra ĐÚNG model được chọn ────────────────────────────────

@pytest.mark.parametrize("alias", canonical.MODEL_HOP_LE)
def test_cam_cli_ghi_dung_model_duoc_chon(cam_cli, alias):
    hs = cam_cli.hs_cua(alias)
    van = cam_cli._codex_profile(hs)
    assert f'model = "{alias}"' in van
    assert f"model_context_window = {hs.cua_so}" in van
    # Và KHÔNG lẫn số của model kia — đây mới là chỗ lỗi thật sẽ nằm.
    kia = next(t for t in canonical.MODEL_HOP_LE if t != alias)
    assert str(cam_cli.HO_SO_MODEL[kia].cua_so) not in van


def test_cam_cli_ten_la_ve_MAC_DINH_chu_khong_nem(cam_cli):
    """`xem`/`go` đọc tệp trạng thái có thể do **bản cũ** ghi (không có khoá
    `model`), hoặc do khách sửa tay. Một `KeyError` ở đó biến câu hỏi *"máy này
    đang cắm gì"* thành một vệt traceback — đúng lúc khách cần câu trả lời nhất.
    """
    assert cam_cli.hs_cua(None).ten == cam_cli.MODEL
    assert cam_cli.hs_cua("").ten == cam_cli.MODEL
    assert cam_cli.hs_cua("khong-co-model-nay").ten == cam_cli.MODEL
    assert cam_cli.hs_trong({}).ten == cam_cli.MODEL
    assert cam_cli.hs_trong({"model": canonical.MODEL_HOP_LE[1]}).ten == \
        canonical.MODEL_HOP_LE[1]


# ── 5. Bộ cài SDK in TÊN TUYẾN cho Claude Desktop, không phải tên model ─────

@pytest.mark.parametrize("alias", canonical.MODEL_HOP_LE)
def test_sdk_in_TEN_TUYEN_cho_desktop_khong_phai_ten_san_pham(sdk_cli, alias):
    """🔴 ĐÂY LÀ MỘT LỖI THẬT ĐÃ ĐANG MỞ, không phải một khả năng.

    Trước 12/09 dòng hướng dẫn Claude Desktop của bộ cài độc lập in::

        inferenceModels     : ltt-3.8

    Claude Desktop **lọc** danh sách model trước khi vẽ picker; tên không chứa
    `claude` bị bỏ. `ltt-3.8` bị bỏ ⇒ picker rỗng ⇒ **nút gửi vô hiệu, không một
    lời báo lỗi nào**. `tools/cam_cli.py` biết điều đó và ghi đúng; bộ cài mà
    khách macOS/Linux tải về thì không.
    """
    hs = sdk_cli.hs_cua(alias)
    dong = [d for d in sdk_cli.claude_desktop("https://vi.du", hs)
            if "inferenceModels" in d and ":" in d]
    assert len(dong) == 1, f"cho doi dung mot dong gia tri, thay {dong}"
    gia_tri = dong[0].split(":", 1)[1].strip()
    assert gia_tri == hs.tuyen_desktop
    assert gia_tri != alias, (
        "in ten san pham vao `inferenceModels` la day khach vao dung cai bay "
        "picker rong / nut gui chet ma ca muc 2.5b cua tai lieu duoc viet de dong")


# ── 6. Bánh cóc TĨNH: tên đã cắt không được sống lại trong mã CHẠY ─────────

#: Chỉ những tệp **hướng dẫn người đang cắm bây giờ**.
#:
#: ⛔ CỐ Ý KHÔNG có `CHANGELOG.md` và các tệp `AUDIT_*`/`reports/`: chúng GHI LẠI
#:    quá khứ, và ở đó `ltt_llm` là một sự thật lịch sử. Một bộ dò cấm cả những
#:    tệp ấy sẽ **trừng phạt việc giải thích** và ép người sau xoá lời kể thay vì
#:    sửa lỗi — đúng cái bẫy `test_1215` đã nêu tên.
TAI_LIEU_SONG = (
    "docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md",
    "docs/PUBLIC_API/DEVELOPER_GUIDE.md",
)

_RE_CU = re.compile(r"\bltt_llm_vision\b|\bqwen38-vision\b")


@pytest.mark.parametrize("duong", TAI_LIEU_SONG)
def test_tai_lieu_dang_song_khong_day_ten_da_cat(duong):
    van = (GOC / duong).read_text(encoding="utf-8")
    xau = [(i, d.strip()) for i, d in enumerate(van.split("\n"), 1)
           if _RE_CU.search(d) or
           re.search(r"\bltt_llm\b", d) and "apps/ltt_llm" not in d]
    assert not xau, (
        f"{duong} con day ten da cat o D02:\n" +
        "\n".join(f"  dong {i}: {d[:90]}" for i, d in xau))


@pytest.mark.parametrize("duong", (
    "tools/cam_cli.py", "tools/cam_cli_gui.py", "sdk/ltt_cai_dat_cli.py",
    "platform_core/public_api/examples.py",
))
def test_ba_cong_cu_khong_con_HANG_CHUOI_nao_mang_ten_da_cat(duong):
    """Đọc **AST**, không quét văn bản.

    ⭐ Vì sao: một tên đã cắt nằm trong *chú thích* thường là câu giải thích *vì
       sao* nó bị cắt — thứ đắt nhất trong tệp và là thứ giữ cho người sau không
       làm lại. Thứ thật sự nguy hiểm là nó nằm trong một **hằng chuỗi**: chỗ đó
       nó đi ra ngoài, vào tệp cấu hình của khách.

    ⚠️ Phân biệt này không phải nới tay. Nó là điều kiện để lời giải thích còn
       sống được: một bộ dò quét cả chú thích buộc người sau phải xoá lời kể để
       làm xanh gate, và lần sau sẽ không ai biết vì sao.
    """
    cay = ast.parse((GOC / duong).read_text(encoding="utf-8"))
    xau = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if _RE_CU.search(nut.value):
                xau.append((nut.lineno, nut.value[:70]))
    # Docstring cấp module là văn xuôi, không phải dữ liệu chạy — miễn trừ.
    doc = ast.get_docstring(cay, clean=False) or ""
    xau = [x for x in xau if x[1] not in doc]
    assert not xau, (
        f"{duong}: ten da cat nam trong HANG CHUOI (tuc no se di ra ngoai):\n" +
        "\n".join(f"  dong {i}: {v!r}" for i, v in xau))


def test_doi_chung_bo_do_AST_that_su_nhin_vao_hang_chuoi(tmp_path):
    """Đối chứng cho bộ dò ngay trên: tiêm một hằng xấu thì nó phải ĐỎ, và một
    chú thích xấu thì nó phải **XANH**. Không có hai nửa này thì "không tìm thấy
    gì" chỉ chứng minh bộ dò chạy, chứ không chứng minh nó nhìn đúng chỗ.
    """
    def do(ma: str) -> int:
        cay = ast.parse(ma)
        return sum(1 for n in ast.walk(cay)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and _RE_CU.search(n.value))

    assert do('X = "qwen38-vision"\n') == 1
    assert do('# qwen38-vision da bi go 11/09\nX = "qwen38-api"\n') == 0


# ── 7. Công cụ tạo khoá cấp khoá cho ĐỦ hai model ──────────────────────────

def test_cong_cu_tao_khoa_cap_cho_du_hai_id_noi_bo():
    """🔴 CHẶN DEPLOY ĐÃ ĐO ĐƯỢC TRÊN SỔ KHOÁ PRODUCTION (12/09).

    Khoá `ltt_llm` duy nhất trên máy chủ khai::

        supported_models = ['qwen38-api', 'qwen38-vision']

    tức **thiếu `qwen35-api`**. `api_pool.chon_key(model="qwen35-api")` không
    tìm thấy khoá nào ⇒ `ThieuKeyError` ⇒ `dieu_phoi.goi()` đọc đó thành *"provider
    không phục vụ được"* ⇒ **mọi lượt LTT-3.5 hỏng trong im lặng**.

    ⚠️ Không test nào bắt được bản thân sổ khoá — đó là **dữ liệu vận hành**,
       không phải mã nguồn. Thứ test được là *mặc định của công cụ ghi ra nó*,
       và mặc định ấy cũng đang sai (`ltt_llm,ltt_llm_vision` — hai tên đã cắt,
       và cả hai đều là bí danh chứ không phải id nội bộ).
    """
    mod = _nap(GOC / "tools" / "them_key_ltt_llm.py", "them_key_1233")
    mac_dinh = [x.strip() for x in mod.MODELS_MAC_DINH.split(",") if x.strip()]
    assert mac_dinh == list(canonical.ALIAS_SANG_ID.values()), (
        f"mac dinh cua `them_key_ltt_llm.py` la {mac_dinh}; no phai la ID NOI BO "
        f"cua ca hai model: {list(canonical.ALIAS_SANG_ID.values())}")
    # Và đúng là id nội bộ, không phải bí danh — lẫn hai thứ này là lỗi đã xảy
    # ra hai lần (xem `canonical.ban_do_model`).
    assert not set(mac_dinh) & set(canonical.MODEL_HOP_LE)
