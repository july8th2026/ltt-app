"""Phase 13 — CORE_GAP: hợp đồng có HAI chỗ khai VRAM, chỉ MỘT chỗ được đọc.

## Tái hiện (điều kiện 1 của cổng Phase 13)

Đo trên registry thật, trước bản vá:

    app               job_type               gpu_vram_mb   resource.vram_min_mb
    asv_gpu           asv_gpu.transcribe        6000        —
    autosubvideo      autosubvideo.transcribe   6000        —
    taoclipngan       taoclipngan.render        6000        —
    upscalevideo      upscalevideo.render      12000        —
    transcript        transcript.run            →0←        5000
    audio_pause       audio_pause.run           →0←        5000
    video_assembly    video_assembly.run        →0←        8000

`job_runner._vram_can` gọi `manifest.vram_for(job_type)`, hàm này **chỉ** đọc
`gpu_vram_mb`. Ba App GPU dựng năm 2026-09 khai ở `ToolSpec.resource
["vram_min_mb"]` — nó nằm ngay cạnh `class="gpu"` nên đọc tự nhiên hơn — và để
trống `gpu_vram_mb`.

⇒ `need_mb = 0` ⇒ `_giu_gpu` trả `(None, False)` ngay ⇒ **ba App chạy không có
  lease GPU nào**, đè thẳng lên `taoclipngan`/`upscalevideo` trên cùng một card.

## Vì sao không phép kiểm nào bắt được (điều kiện 3)

Cả hai bản khai đều **hợp lệ**: một cái rỗng, một cái đầy, và **không có gì nói
chúng phải khớp**. `registry._validate_hop_dong_v2` kiểm *hình dạng* của
`resource` rất kỹ — khoá lạ, kiểu sai, giá trị âm — nhưng nó không hỏi câu duy
nhất quan trọng: *ai đọc con số này?*

⭐ Bài học rộng hơn con bọ: **một trường được kiểm kỹ vẫn có thể là một trường
   không ai đọc.** Kiểm hình dạng và kiểm có-người-tiêu-thụ là hai việc khác nhau.

## Bản vá (điều kiện 4 — tối thiểu, tổng quát)

`vram_for()` **hợp nhất** hai bản khai: `gpu_vram_mb` thắng khi có (nó theo
`job_type`, mịn hơn), không có thì lấy `ToolSpec.resource["vram_min_mb"]` của
tool sinh ra `job_type` ấy. Sau đó hai chỗ khai **không thể lệch nhau nữa**.

Không tên App nào trong bản vá (điều kiện 6).

## ⛔ Một hướng SAI tôi đã đi trước khi tới đây — ghi lại vì nó tốn thật

Tôi tái hiện bằng cách gọi thẳng `jobs.claim()` và thấy hai job cùng
`admission_resource` đều được nhặt, rồi kết luận *"cửa job không giành suất"* và
vá `platform_core/jobs.py`.

**Sai.** `job_runner.py:226` **có** gọi `admission.hold_persisted(...)` ngay sau
khi nhặt. Phép tái hiện của tôi đi vòng qua `job_runner` — đường mà production
không bao giờ đi. Bản vá ấy đã hoàn nguyên.

⚠️ Bài học: **tái hiện phải đi đúng đường production đi.** Gọi thẳng một hàm ở
   tầng dưới cho ra một hành vi có thật, nhưng là hành vi của một đường không ai
   dùng — và nó trông y hệt một con bọ.
"""
from __future__ import annotations

import pytest

from platform_core.registry import AppManifest, ToolSpec, discover


def _manifest(*, gpu_vram_mb=None, vram_min_mb=None) -> AppManifest:
    res = {"class": "gpu", "slots": 1, "est_duration_s": 60}
    if vram_min_mb is not None:
        res["vram_min_mb"] = vram_min_mb
    return AppManifest(
        slug="thu_nghiem", display_name="Thu nghiem", route_prefix="/thu-nghiem",
        job_types=("thu_nghiem.run",),
        gpu_vram_mb=gpu_vram_mb or {},
        tools=(ToolSpec(
            name="thu.run", job_type="thu_nghiem.run", description="thu",
            params_schema={}, returns={"output": "text"}, resource=res),),
    )


def test_khai_o_TOOLSPEC_thoi_van_ra_duoc_con_so() -> None:
    """Đây là cái bẫy đã cắn ba App, và là thứ bản vá gỡ."""
    assert _manifest(vram_min_mb=5000).vram_for("thu_nghiem.run") == 5000


def test_gpu_vram_mb_THANG_khi_ca_hai_cung_khai() -> None:
    """Bản khai theo `job_type` mịn hơn bản khai theo tool — một tool có thể
    sinh nhiều `job_type`, nên nó phải thắng."""
    m = _manifest(gpu_vram_mb={"thu_nghiem.run": 12000}, vram_min_mb=5000)
    assert m.vram_for("thu_nghiem.run") == 12000


def test_KHONG_khai_o_dau_ca_thi_van_la_0() -> None:
    """Hành vi cũ nguyên vẹn: 0 nghĩa là không cần GPU riêng."""
    assert _manifest().vram_for("thu_nghiem.run") == 0


def test_job_type_la_thu_KHAC_thi_khong_lay_nham() -> None:
    m = _manifest(vram_min_mb=5000)
    assert m.vram_for("job_khac.run") == 0


# ── Bánh cóc trên registry THẬT ──────────────────────────────────────────────

def _tool_gpu() -> list[tuple[str, str, int]]:
    ra = []
    for a in discover():
        if a.error:
            continue
        for t in a.manifest.tools:
            res = getattr(t, "resource", None) or {}
            if str(res.get("class", "")) == "gpu":
                ra.append((a.manifest.slug, getattr(t, "job_type", ""),
                           a.manifest.vram_for(getattr(t, "job_type", ""))))
    return ra


def test_MOI_tool_khai_class_gpu_deu_ra_duoc_VRAM_khac_0() -> None:
    """Bánh cóc: khai `class="gpu"` mà `vram_for` ra 0 là chạy **không lease**.

    ⛔ Đây là bất biến, không phải danh sách: App mới thêm vào cũng phải qua.

    Nếu bài này đỏ thì App vừa thêm đang **đè lên card của App khác** — và triệu
    chứng ở production sẽ là OOM ở một App **thứ ba** không liên quan, vào lúc
    hai job tình cờ trùng nhau. Đó là lý do nó đáng chốt ở đây chứ không đợi
    người vận hành phát hiện.
    """
    xau = [(s, jt, v) for s, jt, v in _tool_gpu() if v <= 0]
    assert not xau, f"khai class=gpu ma vram_for()=0: {xau}"


def test_ba_App_GPU_cua_chuong_trinh_nay_deu_co_VRAM() -> None:
    """Chốt hẹp, đọc được: ba App vừa dựng phải ra đúng con số đã khai."""
    m = {a.manifest.slug: a.manifest for a in discover() if not a.error}
    assert m["transcript"].vram_for("transcript.run") == 5000
    assert m["audio_pause"].vram_for("audio_pause.run") == 5000
    assert m["video_assembly"].vram_for("video_assembly.run") == 8000


@pytest.mark.parametrize("slug,jt", [("transcript", "transcript.run"),
                                     ("audio_pause", "audio_pause.run"),
                                     ("video_assembly", "video_assembly.run")])
def test_khai_them_GIAN_CACH_cho_tai_nguyen(slug, jt) -> None:
    """Job GPU dài phải khai giãn cách chờ, nếu không nó quay vòng mặc định.

    `job_runner._cho_tai_nguyen` đọc `cho_tai_nguyen_for`. Đo trên log
    production: một job `ltt_llm.chat` bị hoãn **554 lần** trong đời nó — với
    giãn cách quá ngắn, hàng đợi biến thành một vòng bận.
    """
    m = {a.manifest.slug: a.manifest for a in discover() if not a.error}
    assert m[slug].cho_tai_nguyen_for(jt, default=0) > 0


def test_wiring__job_runner_DOC_dung_ham_nay() -> None:
    """Chốt sợi dây nối, để hai bên không trôi khỏi nhau lần nữa.

    Bản vá này chỉ có nghĩa nếu `job_runner` thật sự gọi `vram_for`. Đọc AST
    chứ không khớp chuỗi — một chú thích nhắc tên hàm sẽ làm `grep` báo nhầm.
    """
    import ast
    import pathlib

    import platform_core.job_runner as jr
    cay = ast.parse(pathlib.Path(jr.__file__).read_text(encoding="utf-8"))
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "vram_for" in goi, "job_runner khong con doc `vram_for`"
