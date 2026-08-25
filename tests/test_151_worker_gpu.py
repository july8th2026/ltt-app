"""
test_151 - worker cấp GPU cho job, và cư xử đúng khi hết GPU.

Ba cách hỏng mà file này chốt, xếp theo mức thiệt hại:

1. Job cần GPU nhưng **mọi card đang bận** → nếu worker cứ chạy thì hai job
   cùng nạp model lên một card và OOM giữa chừng job của khách. Phải hoãn.
2. Hoãn mà **tính là một lần thử thất bại** → vài lần kẹt GPU là job chết hẳn
   dù chưa từng chạy dòng nào.
3. Handler **tự chọn card** → quay lại đúng cuộc đua mà `gpu_lease` sinh ra để
   diệt. Handler chỉ được dùng card nền tảng cấp, qua `ctx`.
"""
from __future__ import annotations

from tests.conftest import APP_THU_JOB, APP_THU_SLUG

import pytest

from platform_core import gpu as gpu_mod


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'j.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _gpu(i, uuid, free_mb=16000):
    return gpu_mod.GpuInfo(index=i, name="Card giả", uuid=uuid,
                           total_mb=16311, free_mb=free_mb, util_pct=0)


def _submit(db, **kw):
    from platform_core.jobs import submit
    kw.setdefault("user_id", "u1")
    kw.setdefault("app_slug", APP_THU_SLUG)
    kw.setdefault("job_type", APP_THU_JOB)
    kw.setdefault("params", {"text": "xin chao"})
    j = submit(db, **kw)
    db.commit()
    return j


def test_job_khong_khai_vram_thi_khong_giu_gpu(db, monkeypatch):
    """App không cần GPU không được chiếm card — nếu không, app nhẹ khoá mất
    card của app nặng."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-a")])
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import GpuLease

    _submit(db)
    assert _chay_mot_job("w1") is True
    db.expire_all()
    assert db.query(GpuLease).count() == 0, "job không cần GPU lại giữ lease"


def test_handler_nhan_dung_card_duoc_cap(db, monkeypatch):
    """Handler phải biết mình được cấp card nào — qua `ctx`, không tự dò."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-duy-nhat")])
    import platform_core.job_runner as jr
    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)

    thay = {}

    def _handler(params, ctx):
        thay["uuid"] = ctx.gpu_uuid
        thay["co_gpu"] = ctx.has_gpu
        thay["env"] = ctx.gpu_env()["CUDA_VISIBLE_DEVICES"]
        return {"ok": True}

    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _handler)
    _submit(db)
    assert jr._chay_mot_job("w1") is True
    assert thay["uuid"] == "GPU-duy-nhat" and thay["co_gpu"] is True
    assert thay["env"] == "GPU-duy-nhat", (
        "tiến trình con không bị ghim vào đúng card -> nó sẽ dùng cuda:0")


def test_tra_lai_gpu_sau_khi_job_xong(db, monkeypatch):
    """Không trả thì card khoá tới khi hết hạn mồ côi (10 phút)."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-a")])
    import platform_core.job_runner as jr
    from platform_core.models import GpuLease
    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)
    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: lambda p, c: {"ok": 1})

    _submit(db)
    jr._chay_mot_job("w1")
    db.expire_all()
    assert db.query(GpuLease).count() == 0, "lease còn treo sau khi job xong"


def test_handler_nem_van_tra_lai_gpu(db, monkeypatch):
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-a")])
    import platform_core.job_runner as jr
    from platform_core.models import GpuLease

    def _no(params, ctx):
        raise RuntimeError("handler vỡ")

    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)
    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _no)
    _submit(db, max_attempts=1)
    jr._chay_mot_job("w1")
    db.expire_all()
    assert db.query(GpuLease).count() == 0, "handler ném xong mà card vẫn bị giữ"


def test_het_gpu_thi_HOAN_job_chu_khong_chay_chung_card(db, monkeypatch):
    """Cách hỏng số 1: chạy chung card = OOM giữa job của khách hàng."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-a")])
    import platform_core.job_runner as jr
    from platform_core import gpu_lease as gl
    from platform_core.models import JOB_QUEUED, Job

    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)
    da_chay = []
    monkeypatch.setattr(jr.jobq, "resolve_handler",
                        lambda jt: lambda p, c: da_chay.append(1) or {"ok": 1})

    # Một worker khác đang giữ card duy nhất.
    gl.acquire(db, worker_id="worker-khac", job_id="job-khac", need_mb=4000)

    j = _submit(db); jid = j.id
    assert jr._chay_mot_job("w1") is True
    assert da_chay == [], "handler vẫn chạy dù không có GPU nào rảnh"

    db.expire_all()
    job = db.get(Job, jid)
    assert job.status == JOB_QUEUED, f"job phải quay về hàng đợi, đang là {job.status}"


def test_hoan_vi_het_gpu_KHONG_tinh_la_mot_lan_that_bai(db, monkeypatch):
    """Cách hỏng số 2: vài lần kẹt GPU là job chết dù chưa chạy dòng nào."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-a")])
    import platform_core.job_runner as jr
    from platform_core import gpu_lease as gl
    from platform_core.models import Job

    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)
    gl.acquire(db, worker_id="worker-khac", job_id="jk", need_mb=4000)

    j = _submit(db, max_attempts=2); jid = j.id
    truoc = db.get(Job, jid).attempts
    for _ in range(4):
        jr._chay_mot_job("w1")
    db.expire_all()
    job = db.get(Job, jid)
    assert job.attempts == truoc, (
        f"hoãn vì hết GPU bị tính thành thử-hỏng: attempts {truoc} -> {job.attempts}")
    assert job.status != "error", "job chết vì kẹt GPU dù chưa từng chạy"


def test_hai_job_dung_hai_card_khac_nhau(db, monkeypatch):
    """Có 2 GPU thì phải dùng cả 2 — nếu không, card thứ hai nằm không."""
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_gpu(0, "GPU-a"), _gpu(1, "GPU-b")])
    import platform_core.job_runner as jr
    from platform_core import gpu_lease as gl

    monkeypatch.setattr(jr, "_vram_can", lambda jt: 4000)
    dung = []
    monkeypatch.setattr(jr.jobq, "resolve_handler",
                        lambda jt: lambda p, c: dung.append(c.gpu_uuid) or {"ok": 1})

    # Card A đang bận -> job phải rơi vào card B, không phải hoãn.
    gl.acquire(db, worker_id="wx", job_id="jx", need_mb=4000)
    _submit(db)
    jr._chay_mot_job("w1")
    assert dung == ["GPU-b"], f"không dùng card còn rảnh: {dung}"


# Việc "nền tảng không được viết cứng tên app" đã có `test_60` gác, và nó quét
# cả `platform_core/` nên ba module GPU mới nằm sẵn trong phạm vi. Bản trùng ở
# đây từng báo đỏ giả vì khớp chuỗi con: chữ "demo" trong một câu tiếng Việt
# của `job_runner.py` bị tính là tên app.


def test_vram_doc_dung_tu_manifest_that():
    """Không mock: app thật khai gì thì worker phải đọc ra đúng thế."""
    from platform_core.job_runner import _vram_can
    from platform_core.registry import discover

    khai = {jt: i.manifest.vram_for(jt)
            for i in discover() if not i.error
            for jt in i.manifest.job_types if i.manifest.vram_for(jt) > 0}
    assert khai, "chưa app nào khai gpu_vram_mb — test này thành vô nghĩa"
    for jt, mb in khai.items():
        assert _vram_can(jt) == mb, f"{jt}: worker đọc sai nhu cầu VRAM"
    assert _vram_can(APP_THU_JOB) == 0


# ── Không app nào được tự đọc GPU 0 nữa ──────────────────────────────────────

def test_khong_app_nao_doc_nvidia_smi_dong_dau():
    """`splitlines()[0]` trên output nvidia-smi = luôn đọc GPU 0.

    Đúng khi máy có một card; từ 2026-08-06 máy có hai. App sẽ báo dung lượng
    của card 0 trong khi job chạy trên card 1 — chọn tile size theo dung lượng
    không có thật rồi OOM. Việc đọc GPU giờ nằm ở `platform_core.gpu`.

    Dò bằng AST chứ không khớp chuỗi: bản đầu của test này báo đỏ giả vì chính
    các docstring GIẢI THÍCH cái bẫy cũng chứa `splitlines()[0]`.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    vi_pham = []
    for path in sorted((root / "apps").rglob("*.py")):
        if {"__pycache__", "vendor", "node_modules"} & set(path.parts):
            continue
        src = path.read_text(encoding="utf-8", errors="ignore")
        if "nvidia-smi" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # khớp đúng hình `<gì đó>.splitlines()[0]`
            if not isinstance(node, ast.Subscript):
                continue
            idx = node.slice
            if not (isinstance(idx, ast.Constant) and idx.value == 0):
                continue
            call = node.value
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "splitlines"):
                vi_pham.append(f"{path.relative_to(root).as_posix()}:{node.lineno}")
    assert not vi_pham, (
        f"app đọc dòng đầu của nvidia-smi (= chỉ thấy GPU 0): {vi_pham} — "
        f"dùng platform_core.gpu.list_gpus()")


def test_autotune_do_dung_card_duoc_cap(monkeypatch):
    """Truyền uuid thì phải đo đúng card đó, không phải card trống nhất."""
    from apps.upscalevideo import autotune
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [
        _gpu(0, "GPU-rong", free_mb=15000), _gpu(1, "GPU-chat", free_mb=3000)])

    assert autotune.query_vram("GPU-chat")[1] == 3000, (
        "đo nhầm card khác -> chọn tile size theo dung lượng không có thật")
    assert autotune.query_vram("GPU-rong")[1] == 15000
    assert autotune.query_vram()[1] == 15000, "không nêu card thì lấy card trống nhất"


def test_autotune_khong_co_gpu_thi_fallback_than_trong(monkeypatch):
    from apps.upscalevideo import autotune
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [])
    total, free = autotune.query_vram()
    assert free == 4000 and total > 0, "mất GPU phải fallback, không được ném"


def test_whisperx_bi_ghim_vao_dung_card(monkeypatch):
    """WhisperX bên trong chỉ gọi `torch.cuda.is_available()` rồi dùng `cuda`,
    tức luôn `cuda:0`. Ghim bằng biến môi trường là cách duy nhất."""
    from apps.autosubvideo import transcription
    env = transcription._env_ghim_gpu("GPU-xyz")
    assert env["CUDA_VISIBLE_DEVICES"] == "GPU-xyz"
    assert "CUDA_VISIBLE_DEVICES" not in transcription._env_ghim_gpu("") or \
        transcription._env_ghim_gpu("").get("CUDA_VISIBLE_DEVICES") != "GPU-xyz"


# ── Số tiến trình worker ─────────────────────────────────────────────────────

def test_so_tien_trinh_worker_mac_dinh_bang_so_gpu(monkeypatch):
    """Một tiến trình = một job một lúc = card thứ hai nằm không vĩnh viễn."""
    import job_worker as jw
    monkeypatch.delenv("LTT_WORKER_PROCESSES", raising=False)
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_gpu(0, "a"), _gpu(1, "b")])
    assert jw._so_tien_trinh() == 2

    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "a")])
    assert jw._so_tien_trinh() == 1

    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [])
    assert jw._so_tien_trinh() == 1, "máy không GPU vẫn phải có 1 worker"


def test_so_tien_trinh_worker_dat_tay_va_chan_gia_tri_bay(monkeypatch):
    """Đặt tay phải thắng, nhưng giá trị bậy không được làm chết dịch vụ."""
    import job_worker as jw
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "a"), _gpu(1, "b")])

    monkeypatch.setenv("LTT_WORKER_PROCESSES", "4")
    assert jw._so_tien_trinh() == 4
    monkeypatch.setenv("LTT_WORKER_PROCESSES", "0")
    assert jw._so_tien_trinh() == 1, "0 worker = hàng đợi đứng im"
    monkeypatch.setenv("LTT_WORKER_PROCESSES", "9999")
    assert jw._so_tien_trinh() == 16, "không được đẻ vô hạn tiến trình"
    monkeypatch.setenv("LTT_WORKER_PROCESSES", "khong-phai-so")
    assert jw._so_tien_trinh() == 2, "giá trị bậy phải quay về mặc định, không ném"


def test_than_worker_o_cap_module_de_windows_spawn_duoc():
    """Windows dùng `spawn`: hàm target phải import lại được từ module.

    Đóng nó thành closure trong `main()` sẽ chạy trên Linux rồi vỡ trên Windows
    lúc pickle — mà máy chủ chạy Windows.
    """
    import job_worker as jw
    assert callable(jw._chay_mot_worker)
    assert jw._chay_mot_worker.__qualname__ == "_chay_mot_worker", (
        "hàm bị lồng trong hàm khác -> multiprocessing spawn không pickle được")
