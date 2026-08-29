"""H35.10a — thời lượng dùng để tính giá phải do MÁY CHỦ đo, không do khách khai.

Đây là nút thắt của Q84. Giá `video.upscale` và `video.subtitle` phụ thuộc
`duration_s`; trước lần sửa này con số đó **do người gọi khai**, còn worker đo
lại thật rồi **nâng giữ chỗ** (`_dam_bao_giu_cho`). Với giao diện thì ổn — có
người chọn một tệp họ nhìn thấy. Với máy gọi máy thì nó phá lời hứa của một báo
giá đã ký: đúng hình dạng sự cố Seedance *giữ 29 thu 78*.

Phép kiểm ở đây chốt bốn điều, và điều thứ tư là điều dễ mất nhất:

1. `/quotes` và `/jobs` cho **cùng một** con số với cùng một asset;
2. số khách khai **không được** ảnh hưởng giá — kể cả khi khai thiếu, thừa, âm;
3. với R2, phép đo đi qua **presigned URL**, không tải cả tệp về;
4. asset không đo được thì **báo lỗi**, KHÔNG rơi về số khách khai và cũng không
   rơi về 0. `media.duration_seconds()` nuốt lỗi thành `0.0` có chủ ý (worker cần
   thế), nhưng ở đường tính tiền `0.0` nghĩa là **giữ chỗ 0 credit** — làm miễn
   phí, và không dòng nào chỉ ra vì sao.
"""
from __future__ import annotations

import uuid

import pytest

from platform_core import media, storage as storage_mod
from platform_core.public_api import invocation
from platform_core.public_api.errors import ApiError
from platform_core.registry import AppManifest, LoadedApp, RegistryError, ToolSpec

SLUG = "dothuthu"
JOB = "dothuthu.render"


# ── Đồ dùng: một app tổng hợp KHAI thời lượng do máy chủ đo ──────────────────
#
# Không trỏ vào một app thật: `CLAUDE.md` cảnh đúng cái bẫy đó ("chỉ đổi chữ
# nó"), vì khi ấy phép kiểm hạ tầng lại phụ thuộc một mặt hàng.

def _gia(params: dict) -> int:
    """1 credit mỗi 10 giây, tối thiểu 1 — đủ để một giây lệch là thấy được."""
    return max(1, int(float(params.get("duration_s") or 0) // 10))


def _tool(**doi) -> ToolSpec:
    schema = {
        "video_key": {"type": "video", "required": True},
        "duration_s": {"type": "number", "min": 0, "measured_from": "video_key"},
    }
    schema.update(doi.pop("params_schema", {}))
    return ToolSpec(name="video.dothu", job_type=JOB,
                    description="Tool thu de kiem phep do thoi luong.",
                    params_schema=schema, returns={"video_key": "video"}, **doi)


def _manifest(tool: ToolSpec) -> AppManifest:
    return AppManifest(
        slug=SLUG, display_name="App do thu (chi co trong test)",
        route_prefix=f"/{SLUG}", job_types=(JOB,), requires=("api",),
        credit_cost=_gia, tools=(tool,),
        enabled=False, public=False, surface="runtime", lifecycle="internal")


@pytest.fixture()
def app_do(monkeypatch):
    """Đăng ký app thử vào `discover()` cho đúng một test."""
    from platform_core import registry as reg

    loaded = LoadedApp(manifest=_manifest(_tool()), router=None)
    goc = reg.discover
    monkeypatch.setattr(
        reg, "discover",
        lambda apps_dir=None: list(goc() if apps_dir is None else goc(apps_dir))
        + [loaded])
    return loaded.manifest.tools[0]


class _KhoGia(storage_mod.Storage):
    """Kho giả đếm từng lời gọi — để chứng minh ta KHÔNG tải cả tệp về."""

    def __init__(self, *, url: str | None = None, path: str | None = None):
        self._url, self._path = url, path
        self.goi: list[str] = []

    def url_for(self, key: str, ttl_s: int = 0):
        self.goi.append("url_for")
        return self._url

    def local_path(self, key: str):
        self.goi.append("local_path")
        return self._path

    def open(self, key: str):
        self.goi.append("open")          # ⛔ đường này là thất bại của phép kiểm
        raise AssertionError("khong duoc mo ca tep chi de do thoi luong")


class _Ve:
    """Đủ hình dạng của một `UploadSession` cho phép đo."""

    def __init__(self, staging_key: str = "staging/abc.mp4"):
        self.id = uuid.uuid4().hex
        self.staging_key = staging_key


# ── 1. Hợp đồng: bản khai `measured_from` phải đúng mới nạp được ─────────────

def test_measured_from_phai_tro_toi_mot_tham_so_media_that():
    """Khai bừa thì app không nạp được — fail-closed, không im lặng bỏ qua."""
    from platform_core.registry import _validate_tool

    xau = _tool(params_schema={
        "duration_s": {"type": "number", "min": 0, "measured_from": "khong_co_that"}})
    with pytest.raises(RegistryError, match="measured_from"):
        _validate_tool(_manifest(xau), xau, set())


def test_measured_from_khong_dung_cho_tham_so_khong_phai_so():
    """Đo ra một con số, nên chỗ nhận nó phải là chỗ chứa số."""
    from platform_core.registry import _validate_tool

    xau = _tool(params_schema={
        "duration_s": {"type": "string", "measured_from": "video_key"}})
    with pytest.raises(RegistryError, match="measured_from"):
        _validate_tool(_manifest(xau), xau, set())


def test_hai_app_that_da_khai_do_thoi_luong_phia_may_chu():
    """Bánh cóc: `video.upscale` và `video.subtitle` không được lặng lẽ mất khai.

    Cả hai tính giá theo `duration_s`. Gỡ khai đi thì giá quay về tin lời khách
    mà không phép kiểm nào khác đỏ.
    """
    from platform_core.registry import discover

    thay = {}
    for item in discover():
        if item.error:
            continue
        for tool in item.manifest.tools:
            if tool.name in ("video.upscale", "video.subtitle"):
                thay[tool.name] = (tool.params_schema.get("duration_s") or {})
    assert set(thay) == {"video.upscale", "video.subtitle"}, thay
    for ten, spec in thay.items():
        assert spec.get("measured_from") == "video_key", (ten, spec)


# ── 2. Phép đo: nguồn nào, và không tải cả tệp về ────────────────────────────

def test_r2_do_qua_presigned_url_chu_khong_tai_ca_tep_ve(app_do, monkeypatch):
    """Tiêu chí 3 của kế hoạch — kiểm bằng ĐẾM lời gọi, không bằng đọc mã."""
    kho = _KhoGia(url="https://r2.example/staging/abc.mp4?sig=x")
    thay = {}

    def _probe(src):
        thay["src"] = src
        return {"duration": 42.5}

    monkeypatch.setattr(media, "probe", _probe)

    params = invocation.apply_server_measurements(
        app_do, {"video_key": "upload:x"},
        sessions={"video_key": _Ve()}, storage=kho)

    assert params["duration_s"] == 42.5
    assert thay["src"] == "https://r2.example/staging/abc.mp4?sig=x"
    assert "open" not in kho.goi, kho.goi


def test_kho_cuc_bo_do_thang_tren_duong_dan(app_do, monkeypatch):
    kho = _KhoGia(path=r"C:\du\lieu\abc.mp4")
    thay = {}

    def _probe(src):
        thay["src"] = src
        return {"duration": 7.0}

    monkeypatch.setattr(media, "probe", _probe)

    params = invocation.apply_server_measurements(
        app_do, {"video_key": "upload:x"},
        sessions={"video_key": _Ve()}, storage=kho)

    assert params["duration_s"] == 7.0
    assert thay["src"] == r"C:\du\lieu\abc.mp4"
    assert "open" not in kho.goi, kho.goi


# ── 3. Số khách khai không bao giờ được chạm vào giá ─────────────────────────

@pytest.mark.parametrize("khai", [None, 0, 1, 9999, -5, "mot tram", "", 1e9])
def test_so_khach_khai_bi_thay_bang_so_do_that(app_do, monkeypatch, khai):
    """Tiêu chí 2 — thiếu, thừa, âm, chữ: kết quả vẫn là số đo."""
    monkeypatch.setattr(media, "probe", lambda src: {"duration": 30.0})
    vao = {"video_key": "upload:x"}
    if khai is not None:
        vao["duration_s"] = khai

    params = invocation.apply_server_measurements(
        app_do, dict(vao), sessions={"video_key": _Ve()},
        storage=_KhoGia(path="/tmp/abc.mp4"))

    assert params["duration_s"] == 30.0
    assert invocation.price(app_do, params) == 3


# ── 4. Không đo được thì BÁO, không rơi về 0 và không rơi về số khách khai ───

def test_khong_do_duoc_thi_bao_loi_chu_khong_lam_mien_phi(app_do, monkeypatch):
    """Tiêu chí 4 — chỗ này là nơi một lỗi lặng lẽ biến thành tiền.

    `media.duration_seconds()` trả `0.0` khi hỏng, và ở worker thế là đúng. Ở
    đường tính tiền, `0.0` nghĩa là giữ chỗ 0 credit.
    """
    def _no(src):
        raise media.MediaError("ffprobe hong")

    monkeypatch.setattr(media, "probe", _no)
    with pytest.raises(ApiError) as bat:
        invocation.apply_server_measurements(
            app_do, {"video_key": "upload:x", "duration_s": 9999},
            sessions={"video_key": _Ve()}, storage=_KhoGia(path="/tmp/abc.mp4"))
    assert bat.value.status == 400


def test_thoi_luong_bang_khong_cung_bi_tu_choi(app_do, monkeypatch):
    """Tệp hỏng cho `duration: 0` — hợp lệ về kiểu, sai về tiền."""
    monkeypatch.setattr(media, "probe", lambda src: {"duration": 0.0})
    with pytest.raises(ApiError):
        invocation.apply_server_measurements(
            app_do, {"video_key": "upload:x"},
            sessions={"video_key": _Ve()}, storage=_KhoGia(path="/tmp/abc.mp4"))


def test_khong_co_ve_upload_thi_bao_loi(app_do):
    """Không có gì để đo mà vẫn tính giá được là đúng cái lỗ đang bịt."""
    with pytest.raises(ApiError):
        invocation.apply_server_measurements(
            app_do, {"video_key": "upload:x"}, sessions={},
            storage=_KhoGia(path="/tmp/abc.mp4"))


def test_kho_khong_cho_ra_nguon_nao_thi_bao_loi(app_do):
    """Không presigned URL, không đường dẫn — không được đoán."""
    with pytest.raises(ApiError):
        invocation.apply_server_measurements(
            app_do, {"video_key": "upload:x"},
            sessions={"video_key": _Ve()}, storage=_KhoGia())


# ── 5. Tool không khai gì thì không đổi gì ───────────────────────────────────

def test_tool_khong_khai_measured_from_thi_params_giu_nguyen(monkeypatch):
    """Phép đo chỉ chạy khi app KHAI. Không có khai = không có tác dụng phụ."""
    from platform_core import registry as reg

    tool = ToolSpec(name="text.dothu", job_type=JOB, description="Khong co media.",
                    params_schema={"text": {"type": "string"}},
                    returns={"text": "text"})
    loaded = LoadedApp(manifest=_manifest(tool), router=None)
    goc = reg.discover
    monkeypatch.setattr(reg, "discover", lambda apps_dir=None: list(goc()) + [loaded])

    kho = _KhoGia(path="/tmp/abc.mp4")
    truoc = {"text": "xin chao"}
    assert invocation.apply_server_measurements(
        tool, dict(truoc), sessions={}, storage=kho) == truoc
    assert kho.goi == [], "khong khai thi khong duoc cham vao kho"


# ── 5b. Bất biến nguồn: MỌI route định giá đều phải đo, và đo TRƯỚC ──────────
#
# Đây là phép kiểm nguồn, không phải phép kiểm hành vi — nói thẳng ra để không
# ai đọc nó thành nhiều hơn nó chứng minh. Nó tồn tại vì lỗi có thật ở đây là
# **quên một chỗ**: thêm phép đo vào `/quotes` mà không thêm vào `/jobs` thì hai
# route lệch nhau, `price_changed` bắn cho mọi lời gọi hợp lệ, và triệu chứng
# hiện ra ở chỗ chẳng liên quan gì tới thời lượng.

def test_moi_route_dinh_gia_deu_do_thoi_luong_va_do_TRUOC_khi_tinh_gia():
    import ast
    import io

    cay = ast.parse(io.open("server/api/jobs.py", encoding="utf-8").read())

    def _ten_goi(node):
        f = node.func
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")

    def _goi_cua_rieng_ham(ham):
        """Lời gọi của CHÍNH hàm này, không tính hàm lồng bên trong.

        `ast.walk` chui vào hàm con, nên hàm bọc ngoài (`register_job_routes`)
        sẽ nhận hết lời gọi của hai route và trông như thể nó cũng định giá.
        """
        ra = []
        canh = list(ham.body)
        while canh:
            node = canh.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(node, ast.Call):
                ra.append((node.lineno, _ten_goi(node)))
            canh.extend(ast.iter_child_nodes(node))
        return ra

    thay = {}
    for ham in ast.walk(cay):
        if not isinstance(ham, ast.FunctionDef):
            continue
        goi = _goi_cua_rieng_ham(ham)
        ten = [g for _, g in goi]
        if "price" not in ten:
            continue                      # không định giá thì không phải việc ở đây
        do = [ln for ln, g in goi if g == "apply_server_measurements"]
        gia = [ln for ln, g in goi if g == "price"]
        thay[ham.name] = (do, gia)

    assert set(thay) == {"create_quote", "create_job"}, (
        f"co route dinh gia moi chua duoc xet: {sorted(thay)}")
    for ten, (do, gia) in thay.items():
        assert do, f"{ten}: dinh gia ma khong do thoi luong phia may chu"
        assert min(do) < min(gia), (
            f"{ten}: do thoi luong SAU khi tinh gia thi khong cuu duoc gi")


# ── 6. ffprobe phải đọc được URL, không chỉ đường dẫn ────────────────────────

def test_probe_nhan_url_chu_khong_doi_tep_co_that(monkeypatch):
    """Trước lần sửa này `probe()` chặn mọi thứ không phải tệp trên đĩa.

    Với R2 thì nguồn LÀ một presigned URL, nên phép chặn đó khiến cả đường đo
    không dùng được — và cách vòng qua nó là tải 2 GB về, đúng thứ H10 sinh ra
    để tránh.
    """
    goi = {}

    class _Ket:
        returncode = 0
        stdout = b'{"format":{"duration":"12.5","size":"1000"},"streams":[]}'
        stderr = b""

    def _run(cmd, **k):
        goi["cmd"] = cmd
        return _Ket()

    monkeypatch.setattr(media.subprocess, "run", _run)
    monkeypatch.setattr(media, "ffprobe_bin", lambda: "ffprobe")

    assert media.probe("https://r2.example/a.mp4?sig=x")["duration"] == 12.5
    assert "https://r2.example/a.mp4?sig=x" in goi["cmd"]
