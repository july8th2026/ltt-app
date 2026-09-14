"""test_1256 — MOT hop dong cong bo thi MOI cua phai tra loi giong nhau.

## 🔴 Lo hong do duoc tren production 14/09/2026

Cung mot gia tri ma hop dong CAM (`top_p = 5`, hop dong khai `(0..1]`):

    POST /api/v1/chat/completions  (dong bo)  ->  400 invalid_request
    POST /api/v1/messages          (stream)   ->  200, va chay binh thuong

Nguyen nhan: `runtime_noi_bo/luong.tien_kiem` lam `gui = dict(than)` — no chep
CA than request roi chuyen thang len may B. Do la toan bo phan "kiem" cua cua
stream. Cua dong bo thi di qua `features.kiem_tham_so`, mot danh sach trang.

⛔ Hai cua, mot hop dong, hai hanh vi. Va cua SAI la cua khong kiem: no de mot
   gia tri hop dong cam di thang toi bo giai ma cua may B.

## Khuon cua cong dong, khong phai y kien cua ta

vLLM khai MOT `ChatCompletionRequest`
(`vllm/entrypoints/openai/chat_completion/protocol.py`) trong do
`stream: bool | None = False` chi la **mot truong nhu moi truong khac**, va moi
`@model_validator` chay tren ca request **truoc** khi re nhanh stream. Kiem mot
lan, cho moi cua — khong cua nao duoc di vong.

## Vi sao phep kiem nay khong goi may B

No goi thang hai ham kiem. Mot phep kiem E2E that (co GPU) nam o
`tools/` va chay tay; phep kiem nay chot **bat bien giua hai ham**, nen no chay
trong moi lan gate ma khong ton mot giay GPU nao.
"""
from __future__ import annotations

import pytest

from apps.ltt_llm.features import ThamSoSai, kiem_tham_so, kiem_tham_so_sinh

#: Gia tri hop dong CAM. Moi dong la mot `(ten, than_them)`.
#:
#: ⛔ Moi muc o day phai bi CA HAI cua tu choi. Them mot tham so moi vao hop
#:    dong ma quen day no vao ham dung chung ⇒ dong tuong ung o day do.
GIA_TRI_HOP_DONG_CAM = [
    ("top_p qua 1", {"top_p": 5}),
    ("top_p bang 0", {"top_p": 0.0}),
    ("seed la chuoi", {"seed": "42"}),
    ("stop rong", {"stop": []}),
    ("stop qua 4 chuoi", {"stop": ["a", "b", "c", "d", "e"]}),
    ("response_format sai kieu", {"response_format": {"type": "khong_ton_tai"}}),
    ("tool_choice ngoai enum", {"tool_choice": "bat_buoc"}),
    ("parallel_tool_calls khong phai bool", {"parallel_tool_calls": "yes"}),
    ("temperature ngoai khoang", {"temperature": 9}),
]

TIN = [{"role": "user", "content": "xin chao"}]


@pytest.mark.parametrize("ten,them", GIA_TRI_HOP_DONG_CAM,
                         ids=[t for t, _ in GIA_TRI_HOP_DONG_CAM])
def test_CA_HAI_cua_deu_tu_choi_cung_mot_gia_tri(ten, them):
    """🔴 Day la phep kiem chinh. Mot cua nhan, mot cua tu choi = hop dong vo."""
    with pytest.raises(ThamSoSai):
        kiem_tham_so({"messages": TIN, "model": "ltt-3.8", **them})

    with pytest.raises(ThamSoSai):
        # Cua stream: than co the mang `system`/`input`, nhung tham so sinh thi
        # phai bi kiem y het.
        kiem_tham_so_sinh({"system": "ban la tro ly", **them})


def test_cua_stream_KHONG_duoc_tu_choi_khoa_cua_giao_thuc_khac():
    """⛔ Doi chung nguoc: siet qua tay thi be Claude Code va Codex dang chay that.

    Client Anthropic gui `top_k`, `stop_sequences`, `metadata`, `system`;
    client Responses gui `input`. Ham dung chung phai BO QUA chung, khong tu
    choi — no chi phu trach tham so SINH.
    """
    ra = kiem_tham_so_sinh({
        "system": "ban la tro ly",
        "input": "chuoi tran cua /responses",
        "top_k": 40,
        "stop_sequences": ["\n\n"],
        "metadata": {"user_id": "abc"},
        "top_p": 0.9,
    })
    assert ra == {"top_p": 0.9}, (
        "ham dung chung phai chi tra ve tham so SINH da kiem, va khong duoc "
        f"cham vao khoa cua giao thuc khac — nhan duoc {ra!r}")


def test_gia_tri_hop_le_di_qua_duoc_CA_HAI_cua():
    """Siet khong duoc lam gay duong dung."""
    tot = {"top_p": 0.9, "seed": 7, "stop": ["HET"],
           "tool_choice": "auto", "parallel_tool_calls": True,
           "response_format": {"type": "json_object"}}

    a = kiem_tham_so({"messages": TIN, "model": "ltt-3.8", **tot})
    b = kiem_tham_so_sinh(dict(tot))
    for khoa in tot:
        assert khoa in a, f"cua dong bo danh mat `{khoa}`"
        assert khoa in b, f"cua stream danh mat `{khoa}`"


def test_stream_goi_DUNG_ham_sinh_chu_khong_phai_ham_day_du():
    """⛔ Goi nham `validate` o cua stream = 500 cho moi request co `system`.

    `_tin_that` da ghi lai dung su co ay (25/08): `kiem_tham_so` doi moi phan tu
    `messages` co `role`, ma than cua `/messages` mang `system` rieng va
    `/responses` mang `input` co the la chuoi tran.
    """
    import inspect

    from platform_core.runtime_noi_bo import luong

    for ten_ham in ("tien_kiem", "chuan_bi"):
        nguon = inspect.getsource(getattr(luong, ten_ham))
        assert "validate_generation" in nguon, (
            f"`luong.{ten_ham}` khong goi `validate_generation` — than request "
            "di thang len may B khong qua mot bo kiem nao")
        assert "executor.validate(" not in nguon, (
            f"`luong.{ten_ham}` goi `validate` day du: moi request mang "
            "`system` hoac `input` se thanh 500")


def test_executor_co_khai_validate_generation():
    """Cua stream hoi qua executor vi `platform_core` KHONG duoc import `apps/`."""
    from apps.ltt_llm.executor import EXECUTOR

    assert callable(getattr(EXECUTOR, "validate_generation", None)), (
        "executor thieu `validate_generation` — cua stream se lang le bo qua "
        "buoc kiem (getattr(...) tra None) va lo hong 14/09 tro lai")
