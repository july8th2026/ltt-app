"""App `video_assembly` — App nặng nhất, và ba chỗ nó dễ sai nhất.

## Ba mệnh đề, và cả ba đều đến từ CẤU HÌNH ĐANG CHẠY, không từ mã legacy

1. **`timeline.mode` mặc định là `sequential`.** Mã legacy để `semantic`;
   production đặt `sequential` (`08_CAU_HINH_THAT_TREN_PRODUCTION.md` §1). Một
   App lấy mặc định từ mã sẽ khớp clip bằng CLIP trong khi khách đang đặt tên
   tệp theo cảnh — và nó **vẫn ra video**, chỉ là sai clip.

2. **Ba cờ giai đoạn luôn thắng `cau_hinh`.** Chúng đã qua `chuan_hoa`, còn
   `cau_hinh` thì chưa. Để `cau_hinh` ghi đè chúng nghĩa là một khoá gõ sai bật
   lại một giai đoạn người dùng vừa tắt — tức tiêu GPU cho một việc bị từ chối.

3. **`admission_slots` phải khai, và khai `0` là không khai.** Ngân sách `-n`
   không đếm tiến trình cháu: ngày 03/09 đo được 12 tiến trình `demucs`, mỗi
   cái 460–984% CPU trên một máy 10 lõi, và máy sập.

⛔ Không nạp model nào. Bốn model thật trong một job; một phép kiểm chạm chúng
   phải nằm sau rào `LTT_TEST_NANG` (`tests/rao_chan_nang.py`), và tệp này thì
   không cần chạm.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.video_assembly import jobs as app_jobs
from apps.video_assembly.manifest import MANIFEST
from apps.video_assembly.services import dung_video

GOC = Path(__file__).resolve().parent.parent


def _tool():
    return MANIFEST.tools[0]


# ── 1. Hợp đồng ─────────────────────────────────────────────────────────────

def test_manifest_va_tool_khop_nhau() -> None:
    assert MANIFEST.slug == "video_assembly"
    assert MANIFEST.group == "Workflow"
    assert _tool().job_type in MANIFEST.job_types
    assert MANIFEST.public is False and _tool().api_exposed is False


def test_requires_ca_gpu_lan_ffmpeg() -> None:
    """Thiếu `ffmpeg` thì hàng đợi có thể giao job cho một worker không có nó,
    và job hỏng ở giai đoạn 7 — sau khi đã tiêu ba model."""
    assert set(MANIFEST.requires) == {"gpu", "ffmpeg"}


def test_admission_khai_CA_HAI_ve() -> None:
    """Khai tài nguyên mà `slots=0` thì admission **không cấp lease** — khai một
    nửa là không khai."""
    assert _tool().admission_resource
    assert _tool().admission_slots >= 1


def test_idempotency_gom_ca_che_do_khop() -> None:
    """Cùng clip + cùng nhạc nhưng khác cách khớp là **hai video khác nhau**."""
    khoa = _tool().idempotency["key_fields"]
    assert "che_do_khop" in khoa
    for ten in khoa:
        assert ten in _tool().params_schema


def test_mac_dinh_cua_tool_la_gia_tri_DANG_CHAY() -> None:
    """🔴 `sequential`, không phải `semantic`. Mã legacy nói `semantic`;
    production nói `sequential`. Lấy theo production."""
    truong = _tool().params_schema["che_do_khop"]
    assert truong["default"] == "sequential"
    assert set(truong["values"]) == set(dung_video.CHE_DO_KHOP)
    assert dung_video.CHE_DO_MAC_DINH == "sequential"


# ── 2. Ranh giới ────────────────────────────────────────────────────────────

def test_routes_va_jobs_deu_goi_MOT_service() -> None:
    for ten in ("routes.py", "jobs.py"):
        van = (GOC / "apps" / "video_assembly" / ten).read_text(encoding="utf-8")
        assert "from .services import dung_video" in van, ten


def test_khong_import_app_khac() -> None:
    for tep in (GOC / "apps" / "video_assembly").rglob("*.py"):
        for dong in tep.read_text(encoding="utf-8").splitlines():
            d = dong.strip()
            if d.startswith(("from apps.", "import apps.")):
                assert d.startswith(("from apps.video_assembly",
                                     "import apps.video_assembly")), \
                    f"{tep.name}: {d}"


def test_service_KHONG_import_engine_o_TANG_MODULE() -> None:
    """🔴 `runner` kéo theo torch, CLIP, YOLO và Demucs.

    Import ở tầng module nghĩa là **mỗi lần** `registry.discover()` quét `apps/`
    — kể cả trong một lượt pytest không chạm App này — đều nạp chúng. Hàng trăm
    MB và vài giây, cho một việc không ai xin.
    """
    van = (GOC / "apps" / "video_assembly" / "services" / "dung_video.py"
           ).read_text(encoding="utf-8")
    dau_ham = van.index("def chay(")
    truoc = van[:dau_ham]
    assert "from .engine" not in truoc, (
        "engine bi import o tang module — moi lan quet `apps/` se nap torch")
    assert "from .engine.runner import run_local_job" in van[dau_ham:]


def test_shim_tuong_thich_giu_dung_chu_ky_legacy() -> None:
    """29 tệp engine gọi bốn module hạ tầng này. Một chữ ký khác làm chúng hỏng
    **lúc chạy**, không phải lúc nạp."""
    from apps.video_assembly.services.tuong_thich import ffmpeg, log, paths

    for ten in ("info", "warn", "error", "exc", "debug"):
        assert callable(getattr(log, ten)), ten
    assert callable(paths.ensure_dir) and callable(paths.safe_name)
    assert callable(ffmpeg.run) and callable(ffmpeg.probe_duration)


def test_safe_name_khong_bao_gio_tra_ve_RONG() -> None:
    """Một tên rỗng làm `os.path.join` trỏ vào chính thư mục cha — tức ghi đè
    lung tung thay vì tạo một tệp mới."""
    from apps.video_assembly.services.tuong_thich.paths import safe_name

    for xau in ("", "   ", "...", "///", chr(0), "?*<>|"):
        assert safe_name(xau), f"safe_name({xau!r}) tra ve rong"


def test_ma_nguon_khong_chua_byte_null() -> None:
    """Bản đầu của `paths.py` **đã** sinh ra một byte null, vì mẫu regex cần bốn
    lớp thoát lồng nhau và công cụ ghi nuốt mất một lớp. Chốt lại để nó không
    quay lại — một byte null trong `.py` làm `compile()` từ chối cả tệp."""
    for tep in (GOC / "apps" / "video_assembly").rglob("*.py"):
        assert bytes([0]) not in tep.read_bytes(), tep


# ── 3. `chuan_hoa` từ chối TRƯỚC khi chạy ───────────────────────────────────

@pytest.mark.parametrize("params", [
    {}, {"clips": "  "},
    {"clips": "k", "che_do_khop": "khong_co_che_do_nay"},
    {"clips": "k", "cau_hinh": "khong phai dict"},
])
def test_dau_vao_hong_bi_tu_choi(params) -> None:
    """Một job này tiêu bốn model và hàng phút GPU. Từ chối sớm rẻ hơn nhiều so
    với dừng ở giai đoạn 7."""
    with pytest.raises(dung_video.LoiDungVideo):
        dung_video.chuan_hoa(params)


def test_mac_dinh_khi_khong_khai_gi() -> None:
    yc = dung_video.chuan_hoa({"clips": "thu_muc"})
    assert yc.che_do_khop == "sequential"
    assert yc.bat_demucs is True and yc.bat_phu_de is True
    assert yc.bat_cham_diem is False


# ── 4. Ba cờ giai đoạn LUÔN thắng `cau_hinh` ───────────────────────────────

def test_ba_co_giai_doan_thang_cau_hinh() -> None:
    """🔴 `cau_hinh` chưa qua `chuan_hoa`. Để nó ghi đè ba cờ nghĩa là một khoá
    gõ sai bật lại một giai đoạn người dùng vừa tắt — tiêu GPU cho một việc đã
    bị từ chối."""
    yc = dung_video.chuan_hoa({
        "clips": "k", "bat_demucs": False, "bat_phu_de": False,
        "bat_cham_diem": False,
        "cau_hinh": {"demucs": {"enable": True},
                     "subtitle": {"enable": True},
                     "evaluation": {"enable": True},
                     "timeline": {"mode": "semantic"}}})
    cfg = dung_video.dung_cau_hinh(yc)
    assert cfg["demucs"]["enable"] is False
    assert cfg["subtitle"]["enable"] is False
    assert cfg["evaluation"]["enable"] is False
    assert cfg["timeline"]["mode"] == "sequential"


def test_cau_hinh_GIU_duoc_moi_khoa_khac() -> None:
    """Đối chứng: nếu `dung_cau_hinh` chỉ trả về bốn khoá của nó thì phép kiểm
    trên vẫn xanh, mà App thì mất toàn bộ ngưỡng người dùng đặt."""
    yc = dung_video.chuan_hoa({
        "clips": "k",
        "cau_hinh": {"clip": {"reuse_max_times": 7},
                     "subtitle": {"max_chars_per_line": 30}}})
    cfg = dung_video.dung_cau_hinh(yc)
    assert cfg["clip"]["reuse_max_times"] == 7
    assert cfg["subtitle"]["max_chars_per_line"] == 30
    assert cfg["subtitle"]["enable"] is True         # cờ vẫn được ghép vào


# ── 5. Đầu ra rỗng phải là LỖI ─────────────────────────────────────────────

def test_engine_chay_xong_ma_khong_ra_video_thi_NEM(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """🔴 Một tệp 0 byte là kết cục thật của một chuỗi ffmpeg hỏng giữa chừng,
    và ffmpeg vẫn trả 0 ở vài nhánh. Không bắt ở đây thì job báo **THÀNH CÔNG**
    và khách tải về một tệp rỗng."""
    import sys
    import types

    gia = types.ModuleType("gia_runner")
    gia.run_local_job = lambda *a, **k: None
    monkeypatch.setitem(
        sys.modules, "apps.video_assembly.services.engine.runner", gia)

    yc = dung_video.chuan_hoa({"clips": str(tmp_path)})
    ra = tmp_path / "ra.mp4"
    with pytest.raises(dung_video.LoiDungVideo):
        dung_video.chay(yc, tmp_path, str(ra))       # tep khong ton tai

    ra.write_bytes(b"")
    with pytest.raises(dung_video.LoiDungVideo):
        dung_video.chay(yc, tmp_path, str(ra))       # tep 0 byte


def test_thieu_thu_muc_clip_thi_NEM(tmp_path: Path) -> None:
    yc = dung_video.chuan_hoa({"clips": str(tmp_path / "khong-co")})
    with pytest.raises(dung_video.LoiDungVideo):
        dung_video.chay(yc, tmp_path, str(tmp_path / "ra.mp4"))


# ── 6. Handler ──────────────────────────────────────────────────────────────

def test_handler_tu_choi_khi_khong_co_clip() -> None:
    with pytest.raises((app_jobs.LoiVideoAssembly, dung_video.LoiDungVideo)):
        app_jobs.handle({"clips": []})


def test_handler_nhan_params_va_ctx() -> None:
    import inspect
    assert list(inspect.signature(app_jobs.handle).parameters)[:2] == \
        ["params", "ctx"]
