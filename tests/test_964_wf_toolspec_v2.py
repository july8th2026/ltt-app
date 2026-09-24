"""LTT WORKFLOW V2 · Đợt 5.6 — sáu trường mới của `ToolSpec` (`25_26 §2`).

## Ràng buộc thiết kế, và nó kiểm được

`02 §3` chốt: V2 **mở rộng** `ToolSpec`, không dựng registry thứ hai — vì dự án
này đã trả giá nhiều lần cho mô hình hai nguồn chân lý. Hệ quả kiểm được:
**không app nào phải sửa để lên V2**. `test_KHONG_APP_NAO_PHAI_SUA` chứng minh
điều đó bằng cách nạp **kho thật**, không bằng một manifest tự dựng.

## ⛔ Vì sao mọi phép kiểm ở đây đều đi kèm một ca HỢP LỆ

Một bộ kiểm chỉ gồm "đầu vào xấu bị từ chối" sẽ **xanh cả khi validator từ chối
mọi thứ**. Cặp (xấu → đỏ, tốt → xanh) là thứ phân biệt một cái rào với một bức
tường. Bài học này đã trả giá ba lần trong Đợt 4–5.
"""
from __future__ import annotations

import pytest

from platform_core.registry import (RESOURCE_KEYS, SIDE_EFFECT_VALUES,
                                    AppManifest, RegistryError, ToolSpec,
                                    _validate_hop_dong_v2, _validate_tool)


def _mf() -> AppManifest:
    return AppManifest(slug="thu", display_name="Thu", route_prefix="/thu",
                       job_types=("thu.chay",))


def _tool(**kw) -> ToolSpec:
    goc = dict(name="thu.chay", job_type="thu.chay", description="mo ta",
               params_schema={"duration_s": {"type": "int"},
                              "prompt": {"type": "string"}},
               returns={"video": "video"})
    goc.update(kw)
    return ToolSpec(**goc)


# ── Tương thích ngược: đo trên KHO THẬT ──────────────────────────────────────

def test_KHONG_APP_NAO_PHAI_SUA_de_len_V2():
    """⭐ Mệnh đề trung tâm của `§2`, và nó chỉ kiểm được trên kho thật.

    Một manifest tự dựng trong bài kiểm sẽ luôn hợp lệ — nó được viết SAU khi
    sáu trường ra đời. Thứ chứng minh được là 15 `ToolSpec` đã có, viết trước
    khi sáu trường tồn tại, vẫn nạp qua validator mới.
    """
    from platform_core import registry

    apps = registry.discover()
    tools = [t for a in apps for t in a.manifest.tools]
    assert len(tools) >= 15, "kho that phai co it nhat 15 ToolSpec"
    assert {t.type_version for t in tools} == {1}
    assert {t.side_effect for t in tools} == {"external"}
    assert all(t.mock_result is None for t in tools)


def test_sau_truong_deu_co_mac_dinh():
    """Không mặc định = mọi app hiện có vỡ ngay lúc nạp."""
    t = _tool()
    assert (t.type_version, t.side_effect, t.timeout_expr) == (1, "external", "")
    assert t.idempotency == {} and t.resource == {} and t.mock_result is None


# ── `side_effect` ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("gia_tri", sorted(SIDE_EFFECT_VALUES))
def test_side_effect_BA_gia_tri_hop_le_deu_qua(gia_tri):
    _validate_hop_dong_v2(_mf(), _tool(side_effect=gia_tri))


def test_side_effect_la_khong_co_gia_tri_THU_TU(_=None):
    """⛔ Một tên lạ **im lặng** rơi về `external` = "thử lại" cho một thứ app
    định khai là không đảo được. Đó là gửi mail hai lần, tạo VPS hai lần."""
    with pytest.raises(RegistryError, match="side_effect"):
        _validate_hop_dong_v2(_mf(), _tool(side_effect="retryable"))


# ── `idempotency` — phép kiểm đáng giá nhất ở đây ────────────────────────────

def test_idempotency_key_fields_HOP_LE_thi_qua():
    _validate_hop_dong_v2(
        _mf(), _tool(idempotency={"key_fields": ("prompt", "duration_s")}))


def test_idempotency_key_fields_tro_toi_tham_so_KHONG_CO_thi_do():
    """🔴 `key_fields` trỏ vào tham số không tồn tại ⇒ `dedupe_key` dựng từ tập
    thiếu ⇒ **mọi lượt khử trùng vào nhau** hoặc **không lượt nào khử trùng**.

    Cả hai đều là lỗi về tiền, và cả hai đều im lặng. Đây chính là chỗ khai
    bằng dữ liệu trả công: bắt được lúc nạp, không đợi tới lúc tiêu tiền.
    """
    with pytest.raises(RegistryError, match=r"params: \['duration_s', 'prompt'\]"):
        _validate_hop_dong_v2(_mf(), _tool(idempotency={"key_fields": ("seed",)}))


def test_idempotency_khoa_la_thi_do():
    with pytest.raises(RegistryError, match="keyfields"):
        _validate_hop_dong_v2(_mf(), _tool(idempotency={"keyfields": ("prompt",)}))


def test_idempotency_key_fields_RONG_thi_do():
    with pytest.raises(RegistryError, match="tuple"):
        _validate_hop_dong_v2(_mf(), _tool(idempotency={"key_fields": ()}))


# ── `resource` ───────────────────────────────────────────────────────────────

def test_resource_du_bon_khoa_thi_qua():
    _validate_hop_dong_v2(_mf(), _tool(resource={
        "class": "gpu", "vram_min_mb": 12000, "slots": 1, "est_duration_s": 900}))


def test_resource_khoa_VIET_SAI_CHINH_TA_thi_do():
    """⛔ Trong một `dict` tự do, một khoá sai chính tả **không bao giờ báo
    lỗi** — nó chỉ lặng lẽ không có tác dụng, và scheduler xếp chỗ bằng mặc
    định mà không ai biết. Danh sách đóng biến im lặng thành một lỗi."""
    with pytest.raises(RegistryError, match="vram_mb"):
        _validate_hop_dong_v2(_mf(), _tool(resource={"vram_mb": 12000}))
    assert "vram_mb" not in RESOURCE_KEYS


def test_resource_so_am_thi_do():
    with pytest.raises(RegistryError, match="est_duration_s"):
        _validate_hop_dong_v2(_mf(), _tool(resource={"est_duration_s": -1}))


def test_resource_bool_KHONG_duoc_tinh_la_int():
    """`True` là `int` trong Python. Một `slots=True` lọt qua sẽ giữ **một**
    slot vì `int(True) == 1` — đúng tình cờ, và sai ngay khi ai đó viết
    `slots=False` để nói "không cần slot"."""
    with pytest.raises(RegistryError, match="slots"):
        _validate_hop_dong_v2(_mf(), _tool(resource={"slots": True}))


# ── `type_version` ───────────────────────────────────────────────────────────

def test_type_version_phai_la_int_duong():
    _validate_hop_dong_v2(_mf(), _tool(type_version=7))
    for xau in (0, -1, "2", True):
        with pytest.raises(RegistryError, match="type_version"):
            _validate_hop_dong_v2(_mf(), _tool(type_version=xau))


# ── `mock_result` ────────────────────────────────────────────────────────────

def test_mock_result_callable_thi_qua_khong_callable_thi_do():
    _validate_hop_dong_v2(_mf(), _tool(mock_result=lambda p: {"video": "x"}))
    with pytest.raises(RegistryError, match="mock_result"):
        _validate_hop_dong_v2(_mf(), _tool(mock_result={"video": "x"}))


# ── `timeout_expr` ───────────────────────────────────────────────────────────

def test_timeout_expr_hop_le_thi_qua():
    _validate_hop_dong_v2(_mf(), _tool(timeout_expr="duration_s * 30 + 120"))
    _validate_hop_dong_v2(
        _mf(), _tool(timeout_expr="min(duration_s * 30 + 120, 3600)"))


def test_timeout_expr_doc_tham_so_KHONG_CO_thi_do():
    """⚠️ `Q5`: chỉ được đọc `params` của **chính node đó**. Một tên lạ ở đây
    thường là người viết đang tưởng mình đọc được kết quả bước trước — thứ
    **chưa tồn tại** lúc validate, và `WF-501` cần trần chi phí lúc validate."""
    with pytest.raises(RegistryError, match="ket_qua_buoc_truoc"):
        _validate_hop_dong_v2(_mf(), _tool(timeout_expr="ket_qua_buoc_truoc * 2"))


@pytest.mark.parametrize("xau", [
    "__import__('os').system('x')",
    "open('/etc/passwd')",
    "duration_s.__class__",
    "(lambda: 1)()",
    "[x for x in (1,2)]",
    "2 ** 999999999",
])
def test_timeout_expr_TU_CHOI_moi_cu_phap_ngoai_tap(xau):
    """⛔ `timeout_expr` là trường DUY NHẤT trong sáu trường mang **mã** chứ
    không mang **dữ liệu**. Nên nó là trường duy nhất cần một bộ duyệt.

    Bộ tính ở `platform_core/workflow/bieu_thuc.py` **không dùng `eval`** —
    xem `test_bo_tinh_KHONG_dung_eval`.
    """
    with pytest.raises(RegistryError, match="timeout_expr"):
        _validate_hop_dong_v2(_mf(), _tool(timeout_expr=xau))


def test_bo_tinh_tra_dung_so():
    from platform_core.workflow.bieu_thuc import tinh_bieu_thuc

    assert tinh_bieu_thuc("duration_s * 30 + 120", {"duration_s": 5}) == 270
    assert tinh_bieu_thuc("min(duration_s * 30 + 120, 3600)",
                          {"duration_s": 600}) == 3600
    assert tinh_bieu_thuc("duration_s if duration_s > 10 else 10",
                          {"duration_s": 3}) == 10


def test_bo_tinh_KHONG_dung_eval():
    """⭐ Đọc AST của chính mô-đun, không `grep` chuỗi.

    `grep "eval"` sẽ báo động trên chính đoạn chú thích **giải thích vì sao
    không dùng `eval`** — bộ dò văn bản trừng phạt việc giải thích. Đọc AST thì
    một lời gọi là một lời gọi, một chú thích là một chú thích.
    """
    # 🔴 QUÉT CẢ GÓI, không riêng `bieu_thuc.py` (nới 24/09).
    #
    #    Bản cũ chỉ đọc AST của `bieu_thuc.__file__`. Ngày 24/09 ruột bộ tính
    #    được tách sang `chinh_sach.py`, và bài kiểm **lặng lẽ rỗng đi**: vẫn
    #    xanh, nhưng không còn nhìn vào chỗ có mã. Cùng hạng lỗi với `test_967`
    #    quét không đệ quy và bánh cóc ASCII chỉ quét `print()` trực tiếp.
    #
    # ⭐ Quét cả gói thì nó TỰ PHỦ mô-đun mới — P2 đang đẻ thêm `noi_suy.py`,
    #    `ham_bieu_thuc.py`. Một danh sách gõ tay sẽ mục đúng lúc có tệp mới.
    import ast
    import pathlib

    from platform_core.workflow import bieu_thuc

    goc = pathlib.Path(bieu_thuc.__file__).parent
    tep = sorted(goc.rglob("*.py"))
    xau = {}
    for f in tep:
        cay = ast.parse(f.read_text(encoding="utf-8"))
        goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        co = {"eval", "exec", "compile"} & goi
        if co:
            xau[f.name] = co
    assert not xau, f"loi goi nguy hiem: {xau}"
    # 🔑 Đối chứng: đường dẫn sai thì mọi khẳng định trên xanh vì không đo gì.
    assert len(tep) >= 20, f"chi quet duoc {len(tep)} tep - pham vi sai?"
    assert (goc / "chinh_sach.py").exists(), "ruot bo tinh phai trong pham vi"


def test_chia_cho_0_ra_LOI_NOI_RO_chu_khong_ZeroDivisionError():
    from platform_core.workflow.bieu_thuc import LoiBieuThuc, tinh_bieu_thuc

    with pytest.raises(LoiBieuThuc, match="chia cho 0"):
        tinh_bieu_thuc("120 / duration_s", {"duration_s": 0})


# ── Cái rào có được MẮC VÀO đường nạp không ─────────────────────────────────

def test_validator_THUC_SU_nam_tren_duong_nap():
    """🔑 Một validator hoàn hảo mà không ai gọi là trang trí.

    Đợt 3 và Đợt 4 mỗi đợt có một cái rào không bao giờ chạy, và **cả hai đều
    có một phép kiểm mang đúng tên cái rào** — phép kiểm ấy gọi thẳng hàm,
    nên nó xanh mà đường nạp vẫn không đi qua. Bài này đi qua `_validate_tool`.
    """
    with pytest.raises(RegistryError, match="side_effect"):
        _validate_tool(_mf(), _tool(side_effect="bua"), set())
