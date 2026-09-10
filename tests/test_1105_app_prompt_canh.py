"""App `prompt_canh` — viết lại từ `bot_gem` trên `runtime_noi_bo`.

⚠️ Slug là `prompt_canh`, **không** phải `gem`. Slug đầu tiên bị
`test_60::test_no_app_slug_is_hardcoded_in_the_platform` bắt: `gem` là **chuỗi
con** của `gemini` trong `platform_core/providers.py`, nên bộ dò báo bốn lần
"tên app bị viết cứng". Đó là một dương tính giả — nhưng nó cũng là dấu hiệu
thật rằng cái tên quá ngắn để phân biệt được, và một slug ba chữ sẽ còn va vào
chuỗi khác nữa. Đổi tên rẻ hơn xin miễn trừ, và tên mới mô tả đúng việc App
làm.

## Vì sao tệp này KHÔNG chốt parity

Chủ dự án quyết bỏ hẳn đường lái trình duyệt (`09_QUYET_DINH_...`). Đó là **đổi
provider giữa lúc migrate**, nên `gem` không còn so được với legacy. Chuẩn
nghiệm thu chuyển thành **hợp đồng đầu ra** — và tệp này chốt đúng phần hợp đồng
ấy mà không cần model thật.

## Bốn thứ phải giữ, và cái thứ tư là cái dễ mất nhất

1. **Ba bước đúng thứ tự, đúng template** — template là *tài sản*, không phải mã.
2. **Lô 10 / 5** — kích thước lô đổi **chất lượng** đầu ra, không chỉ tốc độ.
3. **Giữ 5 cảnh lịch sử** — chống trôi nhân vật qua 100+ cảnh; nó nói về **ngữ
   cảnh của mô hình**, nên nó sống sót qua việc đổi provider.
4. **Điền template bằng `replace` tuần tự, KHÔNG bằng `format`** — vì giá trị
   điền vào chứa `{` `}` (JSON của bước 3), và `format` sẽ ném `KeyError` giữa
   một lượt **đã tiêu tiền**.

⛔ Không gọi model thật: `chay()` nhận `goi_model` như một tham số, nên phép kiểm
   đi qua đúng đường mà production đi, chỉ khác cái đầu dây.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.prompt_canh import jobs as app_jobs
from apps.prompt_canh.manifest import MANIFEST
from apps.prompt_canh.services import kich_ban

GOC = Path(__file__).resolve().parent.parent


def _tool():
    return MANIFEST.tools[0]


# ── 1. Hợp đồng ─────────────────────────────────────────────────────────────

def test_manifest_va_tool_khop_nhau() -> None:
    assert MANIFEST.slug == "prompt_canh"
    assert MANIFEST.group == "Workflow"
    assert _tool().job_type in MANIFEST.job_types
    assert MANIFEST.public is False and _tool().api_exposed is False


def test_requires_la_api_KHONG_phai_browser() -> None:
    """Hệ quả trực tiếp của quyết định bỏ lái trình duyệt. Khai `browser` ở đây
    là đòi một worker có IP dân dụng cho một App chỉ gọi API nội bộ."""
    assert MANIFEST.requires == ("api",)


def test_side_effect_la_EXTERNAL_du_idempotency_khai_duoc() -> None:
    """🔴 Hai trường này **độc lập**, và tôi đã gộp chúng làm một.

    Bản đầu của tôi khai `side_effect="none"`, lý lẽ là: qua `runtime_noi_bo`
    mỗi lượt là một lời gọi có kế toán riêng nên `key_fields` khai được **thật**.
    Vế sau đúng — và nó **không** kéo theo vế trước.

    `side_effect` là **hành vi khôi phục** (`platform_core/registry.py:711`), nói
    cho nền tảng biết chạy lại có an toàn không. `none` nghĩa là *"cứ thử lại
    thoải mái"*. Nhưng App này thu tiền theo **từng lượt gọi model** ở tầng
    `runtime_noi_bo` — chạy lại là **thu lại**. Khai `none` là một lời khai sai
    **về tiền**, đúng hạng lỗi mà `registry.py` cảnh báo: nó chỉ lộ ra ở chỗ
    đang tiêu tiền của khách.

    ⚠️ `idempotency.key_fields` bảo vệ khỏi **nộp trùng cùng một job**; nó không
       làm cho một lượt đã chạy trở nên hoàn lại được. Hai lớp khác nhau, và
       `external` là mặc định của nền tảng vì lý do đó.

    Bắt được nhờ `tests/test_964_wf_toolspec_v2.py` trong lượt gate đầy đủ —
    không phép kiểm nào của tôi thấy, vì tôi đã chốt **cùng một hiểu sai** ở cả
    manifest lẫn phép kiểm.
    """
    assert _tool().side_effect == "external"
    khoa = _tool().idempotency["key_fields"]
    assert set(khoa) == {"kich_ban", "so_canh"}
    for ten in khoa:
        assert ten in _tool().params_schema


def test_gia_o_tang_job_la_KHONG() -> None:
    """🔴 `runtime_noi_bo` đã thu theo từng lượt model. Khai thêm một giá ở tầng
    job là thu **hai lần** cho cùng một việc — bảng giá đúng mà tiền thu ra sai.
    """
    assert MANIFEST.credit_cost({"so_canh": 100}) == 0
    assert MANIFEST.credit_cost({}) == 0


def test_model_la_hidden_thi_PHAI_co_default() -> None:
    """Tham số ẩn mà thiếu mặc định thì tầng API bỏ trống và handler tự chọn —
    kho này đã có một tool storyboard chạy **và tính tiền** sai nhánh vì đúng
    lỗi ấy."""
    m = _tool().params_schema["model"]
    assert m["type"] == "model_ref" and m.get("default")


# ── 2. Ranh giới ────────────────────────────────────────────────────────────

def test_routes_va_jobs_deu_goi_MOT_service() -> None:
    for ten in ("routes.py", "jobs.py"):
        van = (GOC / "apps" / "prompt_canh" / ten).read_text(encoding="utf-8")
        assert "from .services import kich_ban" in van, ten


def test_service_KHONG_import_runtime_noi_bo() -> None:
    """`chay()` nhận `goi_model` như một tham số. Nhờ vậy nghiệp vụ kiểm được
    **không cần model thật và không cần CSDL**, mà vẫn là đúng đường production
    đi — chỉ khác cái đầu dây. Cùng khuôn `apps/chatltt`."""
    van = (GOC / "apps" / "prompt_canh" / "services" / "kich_ban.py").read_text(
        encoding="utf-8")
    assert "runtime_noi_bo" not in van.replace(
        "`runtime_noi_bo`", "")  # nhắc trong docstring thì được


def test_khong_con_dau_vet_lai_trinh_duyet() -> None:
    """~8.300 dòng Selenium bị bỏ. Một `import selenium` sót lại nghĩa là có ai
    đó đã kéo một mảnh của đường cũ về."""
    for tep in (GOC / "apps" / "prompt_canh").rglob("*.py"):
        van = tep.read_text(encoding="utf-8").lower()
        for cam in ("selenium", "webdriver", "undetected_chromedriver"):
            assert f"import {cam}" not in van, f"{tep.name}: {cam}"


# ── 3. Template là TÀI SẢN ──────────────────────────────────────────────────

@pytest.mark.parametrize("ten", ["step1_character_lock.txt",
                                 "step2_scene_list.txt",
                                 "step3_json_prompt.txt"])
def test_ba_template_ton_tai_va_khong_rong(ten) -> None:
    van = kich_ban.doc_template(ten)
    assert len(van) > 1000, f"`{ten}` ngan bat thuong — co bi cat khong?"


def test_thieu_template_thi_NEM_chu_khong_chay_tiep() -> None:
    with pytest.raises(kich_ban.LoiKichBan):
        kich_ban.doc_template("khong_ton_tai.txt")


def test_dien_dung_replace_TUAN_TU_khong_dung_format() -> None:
    """🔴 Đây là phép kiểm đắt nhất tệp này.

    Giá trị điền vào bước 3 **là JSON**, tức chứa `{` `}`. `str.format` sẽ ném
    `KeyError` giữa một lượt đã tiêu tiền. Legacy cố ý dùng `replace` tuần tự và
    ghi rõ lý do; giữ nguyên.
    """
    mau = "A={a} B={b}"
    gt = {"a": '{"scene_id": 1, "text": "xin chao"}', "b": "hai"}
    ra = kich_ban.dien(mau, gt)
    assert ra == 'A={"scene_id": 1, "text": "xin chao"} B=hai'
    # Đối chứng: `format` KHÔNG làm được việc này.
    with pytest.raises((KeyError, IndexError, ValueError)):
        mau.format(**gt).format(**gt)


def test_dien_bo_qua_cho_dat_khong_duoc_cung_cap() -> None:
    """Một chỗ đặt thiếu giá trị phải **ở nguyên**, không được thành `None` hay
    ném — vì template có chỗ đặt tuỳ chọn."""
    assert kich_ban.dien("X={co} Y={khong}", {"co": 1}) == "X=1 Y={khong}"


# ── 4. Hằng số phải giữ ─────────────────────────────────────────────────────

def test_ba_hang_so_giu_tu_legacy() -> None:
    assert kich_ban.LICH_SU_CANH == 5
    assert kich_ban.LO_BUOC2 == 10
    assert kich_ban.LO_BUOC3 == 5


def test_mac_dinh_cua_tool_khop_hang_so_cua_service() -> None:
    """Hai chỗ khai cùng một số là hai chỗ sẽ lệch. Chốt chúng bằng nhau."""
    ps = _tool().params_schema
    assert ps["batch_step2"]["default"] == kich_ban.LO_BUOC2
    assert ps["batch_step3"]["default"] == kich_ban.LO_BUOC3


# ── 5. `chuan_hoa` từ chối trước khi chạy ───────────────────────────────────

@pytest.mark.parametrize("params", [
    {}, {"kich_ban": "   "}, {"kich_ban": "x", "so_canh": 0},
    {"kich_ban": "x", "batch_step2": 0}, {"kich_ban": "x", "so_canh": "nhieu"},
])
def test_dau_vao_hong_bi_tu_choi(params) -> None:
    with pytest.raises(kich_ban.LoiKichBan):
        kich_ban.chuan_hoa(params)


# ── 6. Tách JSON khỏi câu trả lời của model ────────────────────────────────

@pytest.mark.parametrize("tra_loi, mong_doi", [
    ('[{"a": 1}]', [{"a": 1}]),
    ('```json\n[{"a": 1}]\n```', [{"a": 1}]),
    ('Day la ket qua:\n```\n[{"a": 1}]\n```\nHet.', [{"a": 1}]),
    ('Toi nghi vay: [{"a": 1}]', [{"a": 1}]),
])
def test_tach_duoc_json_khoi_cau_tra_loi_thuc_te(tra_loi, mong_doi) -> None:
    assert kich_ban._tach_json(tra_loi) == mong_doi


@pytest.mark.parametrize("tra_loi", ["", "khong co json nao ca", "[{'a': 1,}"])
def test_json_hong_thi_NEM_kem_nguyen_van(tra_loi) -> None:
    """Bên gọi cần biết **model trả về cái gì**, không chỉ biết nó không parse
    được — nếu không thì mỗi lần hỏng là một lần phải chạy lại để xem."""
    with pytest.raises(kich_ban.LoiKichBan):
        kich_ban._tach_json(tra_loi)


# ── 7. Ba bước, và lịch sử cảnh đi vào lời nhắc ────────────────────────────

def test_ba_buoc_chay_dung_thu_tu_va_dung_so_lo() -> None:
    nhat_ky: list[str] = []
    canh = [{"scene_id": i, "text": f"canh {i}"} for i in range(1, 21)]

    def goi(nhac: str) -> str:
        nhat_ky.append(nhac)
        if len(nhat_ky) == 1:
            return "CHAR BIBLE"
        if len(nhat_ky) <= 3:                       # 20 canh / lo 10 = 2 lo
            i = len(nhat_ky) - 2
            return json.dumps(canh[i * 10:(i + 1) * 10])
        return json.dumps([{"scene_id": 1, "prompt": "x"}])

    ket = kich_ban.chay(
        kich_ban.chuan_hoa({"kich_ban": "mot kich ban", "so_canh": 20}), goi)

    # 1 (buoc 1) + 2 (buoc 2: 20/10) + 4 (buoc 3: 20/5)
    assert ket.so_luot_model == 1 + 2 + 4
    assert len(ket.canh) == 20
    assert ket.char_bible == "CHAR BIBLE"


def test_lo_thu_HAI_mang_theo_5_canh_gan_nhat() -> None:
    """Chống trôi nhân vật. Legacy ghi thẳng: *"chỉ giữ 2 scene cuối → qua 100+
    scenes drift character/style"*."""
    nhat_ky: list[str] = []
    canh = [{"scene_id": i, "text": f"canh {i}"} for i in range(1, 21)]

    def goi(nhac: str) -> str:
        nhat_ky.append(nhac)
        if len(nhat_ky) == 1:
            return "CB"
        if len(nhat_ky) <= 3:
            i = len(nhat_ky) - 2
            return json.dumps(canh[i * 10:(i + 1) * 10])
        return "[]"

    kich_ban.chay(kich_ban.chuan_hoa({"kich_ban": "k", "so_canh": 20}), goi)

    lo_hai = nhat_ky[2]
    assert '"scene_id": 10' in lo_hai, "lo 2 khong mang lich su"
    assert '"scene_id": 5' not in lo_hai, "lo 2 mang QUA 5 canh lich su"


def test_buoc_1_tra_rong_thi_DUNG_ngay() -> None:
    """Một `char_bible` rỗng sẽ trôi qua cả hai bước sau và cho ra một bộ prompt
    không có nhân vật — hỏng ở chỗ không ai nhìn ra."""
    with pytest.raises(kich_ban.LoiKichBan):
        kich_ban.chay(kich_ban.chuan_hoa({"kich_ban": "k", "so_canh": 5}),
                      lambda nhac: "   ")


def test_buoc_2_tra_ve_khong_phai_danh_sach_thi_NEM() -> None:
    """Bước 2 phải trả một **danh sách** cảnh. Một đối tượng đơn lẻ đi lọt sẽ
    làm `canh.extend()` rải từng KHOÁ của nó thành từng cảnh — và mỗi "cảnh" khi
    ấy là một chuỗi. Hỏng ở bước 3, xa chỗ gây ra."""
    luot = {"n": 0}

    def goi(nhac: str) -> str:
        luot["n"] += 1
        return "CB" if luot["n"] == 1 else '{"khong": "phai danh sach"}'

    with pytest.raises(kich_ban.LoiKichBan):
        kich_ban.chay(kich_ban.chuan_hoa({"kich_ban": "k", "so_canh": 5}), goi)


# ── 8. Handler ──────────────────────────────────────────────────────────────

def test_handler_doi_owner_id() -> None:
    """Thiếu `owner_id` thì không biết tính tiền cho ai — và `runtime_noi_bo`
    tính tiền theo chính giá trị ấy."""
    with pytest.raises(app_jobs.LoiPromptCanh):
        app_jobs.handle({"kich_ban": "k", "so_canh": 3})


# ─────────────────────────────────────────────────────────────────────────────
# Trần đầu vào và trần thời gian phải KHỚP NHAU — và đó là chuyện tiền
# ─────────────────────────────────────────────────────────────────────────────
#
# 🔴 `runtime_noi_bo` thu tiền theo **từng lượt gọi model** và quyết toán ngay,
#    không giữ chỗ. Nên một job chết ở trần thời gian nghĩa là khách **đã trả**
#    cho những lượt đã chạy và nhận về **không gì**.
#
# ⛔ Trước bản vá: `chuan_hoa` chỉ kiểm `so_canh >= 1`; manifest khai
#    `params_schema["so_canh"]["max"] = 500`; và **đường route không cưỡng chế
#    schema** (nó gọi thẳng `chuan_hoa`). Nên thực tế không có trần trên. Và
#    ngay cả 500 cũng là một lời hứa không phục vụ được: 151 lượt gọi trong trần
#    1800 s là **11,9 giây mỗi lượt**, qua máy B vốn chỉ có MỘT suất đồng thời.

def test_so_luot_goi_dung_cong_thuc_cua_hai_vong_lo() -> None:
    """Đối chiếu với số cảnh THẬT của bot dựng video: 21 · 59 · 125 · 177 · 202."""
    f = kich_ban.so_luot_goi
    assert f(20) == 1 + 2 + 4          # mặc định
    assert f(177) == 1 + 18 + 36       # một job production thật
    assert f(202) == 1 + 21 + 41       # job lớn nhất đã quan sát
    assert f(0) == 0


def test_so_canh_VUOT_TRAN_bi_tu_choi_o_CONG_chu_khong_chet_giua_chung() -> None:
    """Chặn ở cổng, không để job chạy rồi chết sau khi đã tiêu tiền."""
    goc = {"kich_ban": "mot kich ban"}
    kich_ban.chuan_hoa({**goc, "so_canh": kich_ban.TRAN_SO_CANH})
    with pytest.raises(kich_ban.LoiKichBan) as e:
        kich_ban.chuan_hoa({**goc, "so_canh": kich_ban.TRAN_SO_CANH + 1})
    assert "so_canh" in str(e.value)
    # Câu lỗi phải nói SỐ LƯỢT, không chỉ nói "quá lớn" — người đọc cần biết vì sao.
    assert str(kich_ban.so_luot_goi(kich_ban.TRAN_SO_CANH + 1)) in str(e.value)


def test_TRAN_DAU_VAO_va_TRAN_THOI_GIAN_phai_khop_nhau() -> None:
    """Bất đẳng thức làm quan hệ giữa hai con số **kiểm được**, thay vì nằm trong đầu.

    ⛔ Đây chính là hạng lỗi `tran-dat-duoi-san-nhu-cau`: một trần đặt dưới sàn
       nhu cầu bình thường biến thất bại thành **mặc định**. Ở đây "nhu cầu bình
       thường" đo được — kịch bản production thật có tới 202 cảnh.

    ⚠️ `NGAN_SACH_MOI_LUOT_S` là một **ước lượng**, không phải phép đo. Nó nằm
       trong mã chính là để bài này chốt được nó. Đo lại được thì sửa số ấy
       trước, rồi bài này sẽ nói cho biết trần nào phải đổi theo.
    """
    from platform_core.job_runner import RUNTIME_LIMIT_DEFAULT_S, RUNTIME_LIMIT_S
    from platform_core.public_api.limits import resource_class
    from platform_core.registry import discover

    m = next(a.manifest for a in discover()
             if not a.error and a.manifest.slug == "prompt_canh")
    lop = resource_class(m)
    tran_s = m.runtime_limit_for(
        "prompt_canh.run",
        default=RUNTIME_LIMIT_S.get(lop, RUNTIME_LIMIT_DEFAULT_S))
    can_s = kich_ban.so_luot_goi(kich_ban.TRAN_SO_CANH) * kich_ban.NGAN_SACH_MOI_LUOT_S
    assert can_s <= tran_s, (
        f"{kich_ban.TRAN_SO_CANH} canh = {kich_ban.so_luot_goi(kich_ban.TRAN_SO_CANH)} "
        f"luot goi, can {can_s}s nhung tran chi {tran_s}s — mot job dung tran "
        f"dau vao se CHET o tran thoi gian SAU KHI da thu tien tung luot")


def test_schema_va_TRAN_lay_tu_MOT_nguon() -> None:
    """Hai chỗ khai cùng một con số là hai chỗ để chúng trôi khỏi nhau.

    Đúng hình dạng con bọ VRAM ở `test_1112`: `gpu_vram_mb` và
    `ToolSpec.resource["vram_min_mb"]` cùng nói một điều mà không ai bắt khớp.
    Ở đây manifest **nhập** `TRAN_SO_CANH` thay vì gõ lại `500`.
    """
    from platform_core.registry import discover
    m = next(a.manifest for a in discover()
             if not a.error and a.manifest.slug == "prompt_canh")
    schema = next(t.params_schema["so_canh"] for t in m.tools)
    assert schema["max"] == kich_ban.TRAN_SO_CANH
    assert schema["min"] == 1
