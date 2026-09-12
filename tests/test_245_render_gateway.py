"""
test_245 — cổng render (H37/G6).

⭐ Toàn bộ chạy trên MÁY A, **không cần ComfyUI, không cần GPU**. Đó là yêu cầu của
   G6: máy B đang bận việc khác, và một phase không được chặn vì thế.

Mỗi test dưới đây neo vào một sự thật đọc từ mã nguồn ComfyUI 0.30.0 (commit ghim
`6f7cd7f`) hoặc một cạm bẫy đã ghi trong `docs/ANH_NOI_BO/DECISIONS.md`.
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from render_gateway import busy as B
from render_gateway import catalog as C
from render_gateway import comfy as CF
from render_gateway import jobs as J
from render_gateway import ngan_sach as NS
from render_gateway import storage_io as S
from render_gateway import workflows as W
from render_gateway.config import Config
from render_gateway.runner import (E_COMFY_REJECT, E_NGOAI_VUNG, E_OOM, E_REF,
                                   E_TIMEOUT, E_WORKFLOW, RenderRequest, Runner)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


# ───────────────────────── giả lập ──────────────────────────────────────────
class FakeTransport:
    """ComfyUI giả. Kịch bản đặt bằng thuộc tính, không bằng monkeypatch."""

    def __init__(self):
        self.queue_running: list[str] = []
        self.queue_pending: list[str] = []
        self.history: dict[str, dict] = {}
        self.object_info = {
            "CheckpointLoaderSimple": {}, "CLIPTextEncode": {},
            "EmptyHiDreamO1LatentImage": {}, "KSampler": {},
            "VAEDecode": {}, "SaveImage": {}, "LoadImage": {},
            "ImageScaleToTotalPixels": {}, "HiDreamO1ReferenceImages": {},
            "ModelSamplingSD3": {}, "HiDreamO1PatchSeamSmoothing": {},
        }
        self.stats = {"system": {"ram_total": 206_000_000_000,
                                 "ram_free": 120_000_000_000},
                      "devices": [{"vram_total": 25_769_148_416,
                                   "vram_free": 25_000_000_000}]}
        self.calls: list[tuple[str, str, object]] = []
        self.prompt_status = 200
        self.prompt_body: dict | None = None
        self.view_bytes = PNG
        self.fail_history_times = 0
        #: True = queue xong thi coi nhu chay xong ngay (mo phong lượt chạy thật).
        self.tu_hoan_thanh = True

    def request(self, method, path, *, json=None, params=None, timeout=30.0):
        self.calls.append((method, path, json))
        if path == "/prompt" and method == "POST":
            body = self.prompt_body or {"prompt_id": (json or {}).get("prompt_id"),
                                        "number": 1, "node_errors": {}}
            # ComfyUI that: ban ghi `/history` xuat hien SAU khi prompt chay xong.
            # Gieo san history trong test = "job nay da chay o kiep truoc".
            if self.tu_hoan_thanh:
                pid = (json or {}).get("prompt_id")
                if pid:
                    self.history.setdefault(pid, _ok_history())
            return self.prompt_status, _b(body)
        if path == "/prompt" and method == "GET":
            return 200, _b({"exec_info": {"queue_remaining":
                                          len(self.queue_running) + len(self.queue_pending)}})
        if path == "/queue":
            return 200, _b({
                "queue_running": [[1, p, {}, {}, []] for p in self.queue_running],
                "queue_pending": [[2, p, {}, {}, []] for p in self.queue_pending]})
        if path.startswith("/history/"):
            if self.fail_history_times > 0:
                self.fail_history_times -= 1
                return 599, b"mang loi"
            pid = path.rsplit("/", 1)[1]
            muc = self.history.get(pid)
            return 200, _b({pid: muc} if muc else {})
        if path == "/view":
            return 200, self.view_bytes
        if path == "/object_info":
            return 200, _b(self.object_info)
        if path == "/system_stats":
            return 200, _b(self.stats)
        if path in ("/interrupt", "/free"):
            return 200, b""
        return 404, b"khong co duong nay"


class FakeFetcher:
    def __init__(self):
        self.gets: dict[str, tuple[int, bytes]] = {}
        self.puts: list[tuple[str, bytes, str]] = []
        self.put_status = 200

    def get(self, url, *, timeout):
        return self.gets.get(url, (404, b""))

    def put(self, url, *, data, content_type, timeout):
        self.puts.append((url, data, content_type))
        return self.put_status, b""


def _b(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _ok_history(images=1, node="7"):
    return {"status": {"status_str": "success", "completed": True, "messages": []},
            "outputs": {node: {"images": [
                {"filename": f"a{i}.png", "subfolder": "", "type": "output"}
                for i in range(images)]}}}


@pytest.fixture
def clock():
    """Đồng hồ giả — test không được ngủ thật."""
    box = {"t": 1000.0}

    def now() -> float:
        return box["t"]

    now.tick = lambda d: box.__setitem__("t", box["t"] + d)   # type: ignore[attr-defined]
    return now


# ───────────────────────── workflows ────────────────────────────────────────
def test_the_con_thieu_va_thay():
    mau = {"1": {"class_type": "K", "inputs": {"seed": "@seed", "text": "@prompt"}}}
    assert W.the_con_thieu(mau, {"seed": 1}) == ["prompt"]
    ra = W.thay(mau, {"seed": 7, "prompt": "xin chao"})
    assert ra["1"]["inputs"] == {"seed": 7, "text": "xin chao"}
    # Bản gốc không bị đụng — nếu bị, job thứ hai sẽ thừa hưởng giá trị của job đầu.
    assert mau["1"]["inputs"]["seed"] == "@seed"


def test_thieu_the_la_loi_chan_khong_phai_canh_bao():
    """Workflow còn nguyên `@seed` sẽ hỏng GIỮA CHỪNG sau khi đã nạp model."""
    with pytest.raises(W.WorkflowError):
        W.thay({"1": {"class_type": "K", "inputs": {"seed": "@seed"}}}, {})


def test_prompt_cua_khach_chua_a_khong_bi_thay_nham():
    mau = {"1": {"class_type": "K", "inputs": {"text": "@prompt"}}}
    ra = W.thay(mau, {"prompt": "email @tencongty va gia @@dat"})
    assert ra["1"]["inputs"]["text"] == "email @tencongty va gia @@dat"


def test_kiem_node_bat_thieu_node_truoc_khi_gui():
    """'Thứ gì CPU trả lời được thì không hỏi GPU' — cong_gpu.py, dự án video máy B."""
    mau = {"1": {"class_type": "NodeLa", "inputs": {}}}
    with pytest.raises(W.WorkflowError) as e:
        W.kiem_node(mau, {"KSampler"})
    assert "NodeLa" in str(e.value)


def test_template_that_trong_repo_nap_duoc_va_khai_du_the():
    """Template kèm theo phải nạp được và mọi thẻ phải có mặc định trong catalog."""
    cat = C.nap_catalog()
    spec = cat["hidream-o1"]
    mau = W.nap(spec.modes["t2i"].template)
    gia_tri = dict(spec.defaults)
    gia_tri.update({"prompt": "x", "negative": ""})
    assert W.the_con_thieu(mau, gia_tri) == []


def test_catalog_khong_lo_ten_file_template_ra_ngoai():
    spec = C.nap_catalog()["hidream-o1"]
    assert "template" not in json.dumps(spec.public())


def test_catalog_gioi_han_2_anh_tham_chieu():
    """`ref_max_size()` thu nhỏ mỗi ảnh theo số lượng: 3 ảnh còn 1/2, 5 ảnh còn 1/4."""
    assert C.nap_catalog()["hidream-o1"].max_refs == 2


def test_catalog_mac_dinh_la_bucket_4mp_khong_phai_1920():
    """D-010: sinh ở bucket đã huấn luyện rồi thu nhỏ, không sinh thẳng 1920×1080."""
    d = C.nap_catalog()["hidream-o1"].defaults
    assert (d["width"], d["height"]) == (2560, 1440)
    assert d["width"] * d["height"] > 3_000_000


# ───────────────────────── comfy client ─────────────────────────────────────
def test_prompt_id_on_dinh_theo_job_id():
    """Nền của idempotency: gửi lại cùng job thì ComfyUI thấy cùng prompt_id, và
    sau khi cổng khởi động lại ta vẫn tra được `/history` cũ."""
    assert CF.prompt_id_for("job-1") == CF.prompt_id_for("job-1")
    assert CF.prompt_id_for("job-1") != CF.prompt_id_for("job-2")


def test_queue_prompt_gui_kem_prompt_id_cua_ta():
    t = FakeTransport()
    c = CF.ComfyClient(t)
    c.queue_prompt({"1": {}}, prompt_id="pid-x")
    method, path, body = t.calls[-1]
    assert (method, path) == ("POST", "/prompt")
    assert body["prompt_id"] == "pid-x" and body["client_id"] == c.client_id


def test_node_errors_la_loi_cua_ta_khong_phai_may_chu_chet():
    t = FakeTransport()
    t.prompt_body = {"prompt_id": "p", "node_errors": {"3": "thieu ckpt"}}
    with pytest.raises(CF.ComfyRejected):
        CF.ComfyClient(t).queue_prompt({"1": {}}, prompt_id="p")


def test_interrupt_bat_buoc_co_prompt_id():
    """Gọi /interrupt trống sẽ giết lượt đang chạy — có thể là lượt video 70 phút."""
    with pytest.raises(ValueError):
        CF.ComfyClient(FakeTransport()).interrupt("")


def test_images_of_bo_qua_anh_xem_truoc_temp():
    t = FakeTransport()
    t.history["p"] = {"status": {"status_str": "success"}, "outputs": {"7": {"images": [
        {"filename": "preview.png", "subfolder": "", "type": "temp"},
        {"filename": "that.png", "subfolder": "", "type": "output"}]}}}
    anh = CF.ComfyClient(t).images_of("p")
    assert [a.filename for a in anh] == ["that.png"]


def test_queue_prompt_ids_doc_dung_vi_tri_1_cua_mang():
    t = FakeTransport()
    t.queue_running = ["a"]
    t.queue_pending = ["b", "c"]
    assert CF.ComfyClient(t).queue_prompt_ids() == (["a"], ["b", "c"])


# ───────────────────────── busy / eta ───────────────────────────────────────
def _watcher(t, clock, *, vram_mb=0, so_py=1, **kw):
    """BusyWatcher với nguồn GPU giả.

    ⛔ Phải tiêm cả hai: mặc định chúng gọi `nvidia-smi` THẬT, và máy A có
    nvidia-smi — không tiêm thì test đọc GPU của máy đang chạy test.
    `so_py=1` = chỉ có ComfyUI trên card, không ai khác.
    """
    return B.BusyWatcher(comfy=CF.ComfyClient(t), now=clock,
                         doc_vram_mb=lambda: vram_mb,
                         dem_python_gpu=lambda: so_py, **kw)

def test_viec_la_trong_hang_doi_lam_may_ban(clock):
    t = FakeTransport()
    t.queue_running = ["video-1"]
    w = _watcher(t, clock)
    st = w.observe(cua_ta=set())
    assert st.busy and st.foreign_running == 1


def test_viec_cua_chinh_ta_khong_lam_may_ban(clock):
    t = FakeTransport()
    t.queue_running = ["cua-ta"]
    w = _watcher(t, clock)
    assert not w.observe(cua_ta={"cua-ta"}).busy


def test_eta_chua_co_lich_su_thi_tra_None_chu_khong_doan(clock):
    """'Không biết' phải khác 'sắp xong'. Bên gọi coi None là LÂU."""
    t = FakeTransport()
    t.queue_running = ["video-1"]
    w = _watcher(t, clock)
    assert w.observe(set()).eta_s is None


def test_eta_hoc_tu_thoi_luong_that_cua_viec_la(clock):
    t = FakeTransport()
    w = _watcher(t, clock)
    # Lượt lạ thứ nhất: chạy 100 giây rồi xong.
    t.queue_running = ["v1"]
    w.observe(set())
    clock.tick(100)
    t.queue_running = []
    w.observe(set())
    # Lượt lạ thứ hai vừa bắt đầu ⇒ ETA ≈ trung vị 100 giây.
    t.queue_running = ["v2"]
    st = w.observe(set())
    assert st.eta_s == pytest.approx(100, abs=1)
    clock.tick(60)
    assert w.observe(set()).eta_s == pytest.approx(40, abs=1)


def test_eta_khong_bao_gio_am(clock):
    t = FakeTransport()
    w = _watcher(t, clock)
    t.queue_running = ["v1"]
    w.observe(set())
    clock.tick(10)
    t.queue_running = []
    w.observe(set())
    t.queue_running = ["v2"]
    w.observe(set())
    clock.tick(10_000)
    assert w.observe(set()).eta_s == 0.0


def test_ram_thap_lam_may_ban_theo_nguong_TUYET_DOI(clock):
    """48 GB là LƯỢNG, không phải tỉ lệ — nâng RAM không được làm đổi ý nghĩa.

    Số này rút từ sự cố thật của dự án video máy B: còn ~23 GB thì VRAM bị đẩy lên
    98 %; còn ~4 GB thì Windows sập (19/08).
    """
    t = FakeTransport()
    t.stats["system"]["ram_free"] = 20 * 1024 ** 3
    w = _watcher(t, clock, ram_trong_toi_thieu_gb=48.0)
    st = w.observe(set())
    assert st.busy and "RAM" in st.reason


def test_doc_chiem_lam_may_ban_va_tu_het_han(clock):
    t = FakeTransport()
    w = _watcher(t, clock)
    w.doc_chiem(bat=True, ly_do="benchmark video", het_han_s=60)
    assert w.observe(set()).busy
    clock.tick(61)
    assert not w.observe(set()).busy       # tự tắt, không ai phải nhớ


def test_comfy_chet_thi_coi_la_ban_chu_khong_nhan_viec(clock):
    class Chet(FakeTransport):
        def request(self, *a, **kw):
            return 599, b"connection refused"

    w = B.BusyWatcher(comfy=CF.ComfyClient(Chet()), now=clock,
                      doc_vram_mb=lambda: 0, dem_python_gpu=lambda: 1)
    assert w.observe(set()).busy


# ───────────────────────── job store ────────────────────────────────────────
def test_idempotency_cung_job_id_khong_tao_job_thu_hai(clock):
    st = J.JobStore(now=clock)
    a, moi_a = st.create_or_get("j1", "p1")
    b, moi_b = st.create_or_get("j1", "p1")
    assert moi_a and not moi_b and a is b


def test_trang_thai_da_chot_khong_bi_ghi_de(clock):
    st = J.JobStore(now=clock)
    st.create_or_get("j1", "p1")
    st.set_status("j1", J.COMPLETED)
    st.set_status("j1", J.GENERATING)
    assert st.get("j1").status == J.COMPLETED


def test_active_prompt_ids_chi_ke_job_chua_xong(clock):
    st = J.JobStore(now=clock)
    st.create_or_get("j1", "p1")
    st.create_or_get("j2", "p2")
    st.set_status("j2", J.COMPLETED)
    assert st.active_prompt_ids() == {"p1"}


# ───────────────────────── storage io ───────────────────────────────────────
def test_file_txt_doi_ten_thanh_png_bi_chan(tmp_path):
    f = FakeFetcher()
    f.gets["u"] = (200, b"khong phai anh dau")
    with pytest.raises(S.StorageIOError):
        S.tai_refs(f, [S.RefSpec("u")], job_id="j", input_dir=tmp_path)


def test_anh_qua_lon_bi_chan(tmp_path):
    f = FakeFetcher()
    f.gets["u"] = (200, PNG + b"0" * (9 * 1024 * 1024))
    with pytest.raises(S.StorageIOError):
        S.tai_refs(f, [S.RefSpec("u")], job_id="j", input_dir=tmp_path)


def test_ref_luu_vao_input_dir_va_tra_ve_TEN_khong_phai_duong_dan(tmp_path):
    """Node LoadImage nhận tên tương đối trong `input`; đưa đường dẫn tuyệt đối
    vào là nó không tìm thấy."""
    f = FakeFetcher()
    f.gets["u"] = (200, PNG)
    ten = S.tai_refs(f, [S.RefSpec("u")], job_id="job/1", input_dir=tmp_path)
    assert len(ten) == 1 and "/" not in ten[0] and "\\" not in ten[0]
    assert (tmp_path / ten[0]).read_bytes() == PNG


def test_put_gui_dung_content_type_da_ky():
    """Sai Content-Type so với lúc ký vé thì R2 trả 403 — storage.py đã ghi."""
    f = FakeFetcher()
    S.day_ket_qua(f, [PNG], ["https://r2/put"], content_type="image/webp")
    assert f.puts[0][2] == "image/webp"


def test_khong_co_ve_put_la_loi_ro_rang():
    with pytest.raises(S.StorageIOError):
        S.day_ket_qua(FakeFetcher(), [PNG], [])


# ───────────────────────── runner ───────────────────────────────────────────
def _runner(t: FakeTransport, f: FakeFetcher, tmp_path, clock, **kw) -> Runner:
    return Runner(CF.ComfyClient(t), J.JobStore(now=clock), f,
                  input_dir=tmp_path, timeout_s=kw.pop("timeout_s", 600.0),
                  poll_s=1.0, now=clock, sleep=lambda d: clock.tick(d), **kw)


def _req(**kw) -> RenderRequest:
    """Yêu cầu mẫu, giá trị LẤY TỪ CATALOG chứ không khai cứng.

    ⛔ Bản đầu khai cứng danh sách giá trị. Khi bản mẫu thêm thẻ mới (`@shift`,
    `@seam_*` — thêm 22/08 theo thông số tài liệu) thì **mười hai test cùng đỏ một
    lúc**, và cả mười hai đều đỏ vì cùng một lý do không liên quan gì tới thứ chúng
    kiểm. Lấy từ catalog thì bản mẫu và test không bao giờ lệch nhau nữa.
    """
    spec = C.nap_catalog()["hidream-o1"]
    gia_tri = dict(spec.defaults)
    gia_tri.update({"seed": 1, "prefix": "p", "prompt": "xin chao", "negative": ""})
    base = dict(job_id="j1", template="hidream_o1_t2i.json", values=gia_tri,
                put_urls=["https://r2/put1"], image_keys=["u/1.png"])
    base.update(kw)
    return RenderRequest(**base)


def test_duong_thanh_cong(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    t.history[CF.prompt_id_for("j1")] = _ok_history()
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.COMPLETED and job.image_keys == ["u/1.png"]
    assert len(f.puts) == 1


def test_co_muc_lich_su_KHONG_co_nghia_la_thanh_cong(tmp_path, clock):
    """Cạm bẫy Gate 0: phán quyết phải ĐỌC `status_str`, không chỉ thấy có bản ghi."""
    t, f = FakeTransport(), FakeFetcher()
    t.history[CF.prompt_id_for("j1")] = {
        "status": {"status_str": "error", "completed": False,
                   "messages": ["node 5 no lo"]},
        "outputs": {}}
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.FAILED and job.error_code == E_COMFY_REJECT


def test_oom_thi_nha_vram_va_thu_lai_DUNG_MOT_lan(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    pid = CF.prompt_id_for("j1")
    t.history[pid] = {"status": {"status_str": "error", "completed": False,
                                 "messages": ["CUDA error: out of memory"]},
                      "outputs": {}}
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.FAILED and job.error_code == E_OOM
    assert sum(1 for m, p, _ in t.calls if p == "/free") == 1
    assert sum(1 for m, p, _ in t.calls if m == "POST" and p == "/prompt") == 2


def test_oom_lan_dau_thu_lai_thanh_cong(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    pid = CF.prompt_id_for("j1")
    t.history[pid] = {"status": {"status_str": "error", "completed": False,
                                 "messages": ["out of memory"]}, "outputs": {}}

    goc = t.request
    trang_thai = {"lan": 0}

    def request(method, path, **kw):
        if method == "POST" and path == "/prompt":
            trang_thai["lan"] += 1
            if trang_thai["lan"] == 2:
                t.history[pid] = _ok_history()
        return goc(method, path, **kw)

    t.request = request                                    # type: ignore[assignment]
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.COMPLETED


def test_het_gio_thi_huy_DUNG_prompt_cua_minh(tmp_path, clock):
    """Không được gọi /interrupt trống — nó sẽ giết lượt video của dự án khác."""
    t, f = FakeTransport(), FakeFetcher()
    t.tu_hoan_thanh = False          # prompt khong bao gio xong -> phai het gio
    job = _runner(t, f, tmp_path, clock, timeout_s=10.0).run(_req())
    assert job.status == J.FAILED and job.error_code == E_TIMEOUT
    huy = [body for m, p, body in t.calls if p == "/interrupt"]
    assert huy and huy[0]["prompt_id"] == CF.prompt_id_for("j1")


def test_job_dai_6_phut_khong_bi_het_gio_nham(tmp_path, clock):
    """D-010: một ảnh ở cấu hình chất lượng mất 2,5–6 phút. Trần theo giây của bản
    kế hoạch đầu là sai."""
    t, f = FakeTransport(), FakeFetcher()
    t.tu_hoan_thanh = False          # ta tu quyet dinh luc nao job xong
    pid = CF.prompt_id_for("j1")
    goc = t.request
    dem = {"n": 0}

    def request(method, path, **kw):
        if path.startswith("/history/"):
            dem["n"] += 1
            if dem["n"] > 360:                    # ~360 giây rồi mới xong
                t.history[pid] = _ok_history()
        return goc(method, path, **kw)

    t.request = request                                    # type: ignore[assignment]
    job = _runner(t, f, tmp_path, clock, timeout_s=900.0).run(_req())
    assert job.status == J.COMPLETED


def test_mot_cu_vap_mang_khong_phai_may_chu_chet(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    t.fail_history_times = 2
    t.history[CF.prompt_id_for("j1")] = _ok_history()
    assert _runner(t, f, tmp_path, clock).run(_req()).status == J.COMPLETED


def test_anh_tham_chieu_hong_bao_dung_ma_loi(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    f.gets["bad"] = (200, b"day khong phai anh")
    job = _runner(t, f, tmp_path, clock).run(
        _req(refs=[S.RefSpec("bad")], ref_slots=["ref1"]))
    assert job.status == J.FAILED and job.error_code == E_REF


def test_thanh_cong_nhung_khong_co_anh_la_that_bai(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    t.history[CF.prompt_id_for("j1")] = {
        "status": {"status_str": "success", "completed": True, "messages": []},
        "outputs": {}}
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.FAILED


def test_template_khong_ton_tai_bao_loi_workflow(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    job = _runner(t, f, tmp_path, clock).run(_req(template="khong_co.json"))
    assert job.status == J.FAILED and job.error_code == E_WORKFLOW


def test_chay_lai_cung_job_id_khong_ve_lan_hai(tmp_path, clock):
    """Không gieo sẵn history: đây là job MỚI. Lần một xếp hàng, lần hai không."""
    t, f = FakeTransport(), FakeFetcher()
    r = _runner(t, f, tmp_path, clock)
    r.run(_req())
    r.run(_req())
    assert sum(1 for m, p, _ in t.calls if m == "POST" and p == "/prompt") == 1


# ───────────────────────── API ──────────────────────────────────────────────
def _app(t: FakeTransport, f: FakeFetcher, tmp_path, clock, token=""):
    from fastapi.testclient import TestClient

    from render_gateway.api import create_app
    cfg = Config(comfy_url="http://x", comfy_input_dir=tmp_path, host="127.0.0.1",
                 port=8199, token=token, max_concurrent=1, job_timeout_s=600.0,
                 ram_trong_toi_thieu_gb=48.0, work_dir=tmp_path)
    # Tiêm nguồn VRAM giả: mặc định gọi `nvidia-smi` THẬT, và máy chạy test có
    # GPU — không tiêm thì test phụ thuộc vào việc máy đang bận hay rảnh.
    #
    # ⚠️ VÀ PHẢI TIÊM CẢ `dem_python_gpu`. Thiếu nó thì chốt bận đếm tiến trình
    #    python THẬT trên card, nên test đỏ khi máy tình cờ có việc khác — ví dụ
    #    một lượt `gate.py` chạy song song. Đã dính 24/08: hai test đỏ với
    #    *"co 1 tien trinh khac dang tinh tren GPU"*, và nó **không** phải lỗi của
    #    mã đang sửa. Một test phụ thuộc trạng thái card là một test nói dối.
    app = create_app(cfg, CF.ComfyClient(t), now=clock,
                     sleep=lambda d: clock.tick(d), fetcher=f,
                     doc_vram_mb=lambda: 0, dem_python_gpu=lambda: 0)
    return TestClient(app), app


def _body(**kw):
    b = {"job_id": "j1", "model": "hidream-o1", "mode": "t2i",
         "prompt": "xin chao", "put_urls": ["https://r2/p1"], "image_keys": ["u/1.png"]}
    b.update(kw)
    return b


def _cho_xong(app, job_id="j1", lan=200):
    for _ in range(lan):
        job = app.state.store.get(job_id)
        if job and job.status in J.KET_THUC:
            return job
        time.sleep(0.01)
    return app.state.store.get(job_id)


def test_health_tra_du_thong_tin_van_hanh(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    d = c.get("/health").json()
    assert d["comfy_alive"] and "busy" in d and "ram_free_gb" in d
    assert "hidream-o1" in d["models"]


def test_models_dung_khuon_data_de_providers_live_doc_duoc(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    d = c.get("/v1/models").json()
    assert isinstance(d.get("data"), list) and d["data"][0]["id"] == "hidream-o1"


def test_sai_token_bi_chan(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock, token="bimat")
    assert c.get("/health").status_code == 401
    assert c.get("/health", headers={"Authorization": "Bearer bimat"}).status_code == 200


def test_ban_tra_429_va_KHONG_phai_ma_loi_5xx(tmp_path, clock):
    """⛔ Cạm bẫy D-005: máy A phải phân biệt BẬN với HỎNG. Hiểu nhầm thành lỗi thì
    `api_pool` cooldown rồi `disable` key sau 5 lần — một tối chạy video sẽ tự tắt
    vĩnh viễn model nhà."""
    t, f = FakeTransport(), FakeFetcher()
    t.queue_running = ["video-dang-chay"]
    c, _ = _app(t, f, tmp_path, clock)
    r = c.post("/v1/images/generations", json=_body())
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "busy"
    assert r.status_code < 500


def test_model_la_bi_tu_choi_400(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    assert c.post("/v1/images/generations", json=_body(model="khong-co")).status_code == 400


def test_qua_nhieu_anh_tham_chieu_bi_tu_choi(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    r = c.post("/v1/images/generations",
               json=_body(refs=[{"url": "a"}, {"url": "b"}, {"url": "c"}]))
    assert r.status_code == 400


def test_thieu_ve_put_bi_tu_choi(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    assert c.post("/v1/images/generations", json=_body(put_urls=[])).status_code == 400


def test_gui_lai_cung_job_id_tra_ve_job_cu(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, app = _app(t, f, tmp_path, clock)
    assert c.post("/v1/images/generations", json=_body()).status_code == 202
    _cho_xong(app)
    r2 = c.post("/v1/images/generations", json=_body())
    assert r2.status_code == 200 and r2.json()["job_id"] == "j1"
    assert sum(1 for m, p, _ in t.calls if m == "POST" and p == "/prompt") == 1


def test_job_chay_het_va_tra_ket_qua(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    t.history[CF.prompt_id_for("j1")] = _ok_history()
    c, app = _app(t, f, tmp_path, clock)
    c.post("/v1/images/generations", json=_body())
    job = _cho_xong(app)
    assert job.status == J.COMPLETED
    assert c.get("/v1/jobs/j1").json()["image_keys"] == ["u/1.png"]


def test_huy_job_goi_interrupt_dung_prompt_id(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, app = _app(t, f, tmp_path, clock)
    app.state.store.create_or_get("j9", CF.prompt_id_for("j9"))
    r = c.post("/v1/jobs/j9/cancel")
    assert r.json()["status"] == J.CANCELLED
    huy = [b for m, p, b in t.calls if p == "/interrupt"]
    assert huy and huy[0]["prompt_id"] == CF.prompt_id_for("j9")


def test_doc_chiem_bat_thi_tu_choi_viec_moi(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    c.post("/v1/exclusive", json={"on": True, "reason": "benchmark video", "ttl_s": 60})
    r = c.post("/v1/images/generations", json=_body())
    assert r.status_code == 429 and "doc chiem" in r.json()["error"]["message"]


def test_job_khong_ton_tai_tra_404(tmp_path, clock):
    t, f = FakeTransport(), FakeFetcher()
    c, _ = _app(t, f, tmp_path, clock)
    assert c.get("/v1/jobs/khong-co").status_code == 404


# ───────────────────────── script deploy (G7) ───────────────────────────────
#
# Ba test dưới đây sinh ra từ MỘT LẦN HỎNG THẬT trong phiên viết chúng: tôi viết
# ba tệp `.ps1` có ký tự ⛔/⭐ và chỉ phát hiện khi tự kiểm byte. `tests/test_61`
# chỉ canh `setup/*.ps1`, nên `render_gateway/deploy/` lọt lưới.
#
# Đây đúng tinh thần `cong_gpu.py` của dự án video máy B: *"Mỗi câu hỏi phải trỏ
# về MỘT SỰ CỐ THẬT."*

_DEPLOY = __import__("pathlib").Path(__file__).resolve().parents[1] / "render_gateway" / "deploy"
_PS1 = sorted(_DEPLOY.glob("*.ps1"))


def test_thu_muc_deploy_dung_bo_script_da_biet():
    """Danh sách ĐÓNG, không phải danh sách tối thiểu. Thêm một script vào
    `deploy/` mà không khai ở đây là gate đỏ — vì mỗi script trong đó đều chạm vào
    máy B, và một script lạ lọt vào là thứ không ai rà lại."""
    assert {p.name for p in _PS1} == {
        "deploy.ps1", "cai_dat_dich_vu.ps1", "kiem_tra.ps1", "dung_het.ps1",
        "chuoi_h37.ps1", "thang_do_tham_chieu.ps1", "start_comfy_h37.ps1",
        # Chay mot lo do DAI bang Scheduled Task (D-055). Ly do no ton tai:
        # OpenSSH tren Windows gom moi tien trinh con vao job object cua PHIEN,
        # nen `ssh ... python` VA `Start-Process` deu chet theo ket noi. Da mat
        # mot lo 100 anh o anh 87/100 dung nhu vay.
        "chay_lo_dai.ps1"}


def test_chuoi_viec_phai_cho_HAI_dieu_kien_truoc_khi_chay():
    """⛔ Hàng đợi RỖNG không có nghĩa là lô trước đã xong: giữa hai ảnh có một khe
    vài giây `queue_remaining = 0` trong lúc `chay_baseline` tải ảnh về. Lấy mẫu
    trúng khe đó là chuỗi chen vào chạy SONG SONG — trên card đã ở 97 % VRAM thì đó
    là đường thẳng tới OOM."""
    text = (_DEPLOY / "chuoi_h37.ps1").read_text(encoding="ascii").lower()
    assert "queue_remaining" in text
    assert "chay_baseline" in text, "phai kiem ca tien trinh, khong chi hang doi"


def test_chuoi_viec_tu_ghi_log_khong_nho_vo_chuyen_huong():
    """Chuỗi được phóng bằng `Win32_Process.Create` để sống sót khi phiên SSH đóng.
    `CreateProcess` KHÔNG có shell, nên `*> tep.log` trên dòng lệnh chỉ là một tham
    số văn bản — không ai chuyển hướng gì cả. Đã dính thật 22/08: vỏ chạy tốt, log
    không bao giờ xuất hiện."""
    text = (_DEPLOY / "chuoi_h37.ps1").read_text(encoding="ascii")
    assert "Start-Transcript" in text


def test_cong_tat_khan_cap_giet_ca_VO_CHUOI():
    """Giết lượt đang chạy mà để vỏ chuỗi sống thì vỏ phóng ngay lượt kế tiếp, và
    'dừng hết' hoá ra chỉ là 'chuyển việc'."""
    text = (_DEPLOY / "dung_het.ps1").read_text(encoding="ascii").lower()
    assert "chuoi_h37" in text
    assert "powershell.exe" in text


def test_cong_tat_khan_cap_KHONG_dung_ComfyUI():
    """⛔ ComfyUI dùng chung với dự án video. Một công tắc khẩn cấp giết nhầm việc
    của người khác thì tệ hơn không có."""
    text = (_DEPLOY / "dung_het.ps1").read_text(encoding="ascii").lower()
    assert "ltt_h37/" in text, "phai nhan dien viec cua H37 theo filename_prefix"
    # Không được xoá cả hàng đợi, và không được dừng tiến trình ComfyUI.
    assert "clear" not in text or "queue_remaining" in text
    for cam in ("stop-service", "nssm stop", "main.py"):
        assert cam not in text, f"dung_het.ps1 khong duoc dung toi {cam!r}"


@pytest.mark.parametrize("duong", _PS1, ids=lambda p: p.name)
def test_ps1_thuan_ascii(duong):
    """Quy tắc 2 của CLAUDE.md: PowerShell 5.1 đọc `.ps1` không BOM theo bảng mã
    ANSI. Một ký tự ngoài ASCII làm hỏng cả câu lệnh và báo lỗi ở dòng khác."""
    raw = duong.read_bytes()
    xau = [i for i, b in enumerate(raw) if b >= 128]
    assert not xau, f"{duong.name} co byte ngoai ASCII o vi tri {xau[:5]}"


@pytest.mark.parametrize("duong", _PS1, ids=lambda p: p.name)
def test_ps1_khong_bom(duong):
    assert duong.read_bytes()[:3] != b"\xef\xbb\xbf", f"{duong.name} co BOM"


def _chi_ma(duong) -> str:
    """Bỏ dòng chú thích trước khi soi.

    Lần chạy đầu, test này **báo đỏ vì chính dòng chú thích đang cảnh báo về lỗi
    đó** — `deploy.ps1` có câu "KHONG dung Out-File/Set-Content -Encoding utf8".
    Một phép kiểm bắt oan sẽ bị người ta học cách bỏ qua, và khi đó nó tệ hơn
    không có (`QUY_TAC.md` §6 của dự án video máy B).
    """
    return "\n".join(d for d in duong.read_text(encoding="ascii").splitlines()
                     if not d.lstrip().startswith("#")).lower()


@pytest.mark.parametrize("duong", _PS1, ids=lambda p: p.name)
def test_ps1_khong_ghi_file_bang_duong_chen_bom(duong):
    """Quy tắc 1: `Out-File -Encoding utf8` và `Set-Content -Encoding utf8` chèn
    BOM ở PowerShell 5.1. BOM trong config làm `json.load()` vỡ — lỗi này **đã
    thực sự làm sập production** ở dự án này."""
    text = _chi_ma(duong)
    for xau in ("out-file -encoding utf8", "set-content -encoding utf8"):
        assert xau not in text, f"{duong.name} dung {xau!r} — se chen BOM"


@pytest.mark.parametrize("duong", _PS1, ids=lambda p: p.name)
def test_ps1_ghi_cau_hinh_bang_duong_khong_BOM(duong):
    """Ngược lại: tệp nào có ghi cấu hình thì phải ghi bằng `WriteAllText` +
    `UTF8Encoding($false)`. Cấm cách sai mà không chỉ cách đúng thì lần sau vẫn sai."""
    ma = _chi_ma(duong)
    if "writealltext" not in ma:
        pytest.skip(f"{duong.name} khong ghi tep cau hinh")
    assert "utf8encoding($false)" in ma.replace(" ", ""), \
        f"{duong.name} ghi tep ma khong ep UTF8Encoding($false)"


def test_cai_dat_dich_vu_giu_comfyui_o_loopback():
    """Q102: ComfyUI không có xác thực, nên nó chỉ được nghe 127.0.0.1 — vĩnh viễn.
    Một lần đổi thành `--listen 0.0.0.0` là mở cửa cho chạy mã tuỳ ý trên máy B."""
    text = (_DEPLOY / "cai_dat_dich_vu.ps1").read_text(encoding="ascii")
    assert "--listen 127.0.0.1" in text
    assert "--listen 0.0.0.0" not in text


def test_tuong_lua_gioi_han_theo_dia_chi_khong_mo_toang():
    text = (_DEPLOY / "cai_dat_dich_vu.ps1").read_text(encoding="ascii")
    assert "-RemoteAddress $MayA" in text
    assert "192.168.2.17" in text


def test_kiem_tra_doc_token_bang_split_khong_dem_ky_tu():
    """Lỗi thật đã mắc: `Substring(18)` trong khi "LTT_RENDER_TOKEN=" dài 17 — token
    mất ký tự đầu, và lỗi chỉ lộ ra thành "401 sai token" ở máy A rất lâu sau."""
    text = (_DEPLOY / "kiem_tra.ps1").read_text(encoding="ascii")
    assert "Split('=', 2)[1]" in text
    assert "Substring(18)" not in text
    assert len("LTT_RENDER_TOKEN=") == 17


# ───────────── VRAM: nguồn nào nói thật (đo trên máy B 2026-08-21) ──────────
#
# ⛔ SỰ CỐ THẬT, bắt được ở bước BÁC BỎ của G1. Một tiến trình khác giữ 8 GB VRAM
#    trên máy B, ba nguồn trả lời "còn trống bao nhiêu":
#
#        nvidia-smi              15.308 MiB   <- ĐÚNG
#        ComfyUI /system_stats   23.165 MiB   <- MÙ
#        torch mem_get_info      23.217 MiB   <- MÙ
#
#    Trên Windows/WDDM hai nguồn sau chỉ thấy tiến trình của CHÍNH MÌNH. Bản đầu
#    của `busy.py` đọc `/system_stats`, nên chốt "VRAM đang bị giữ bởi tiến trình
#    khác" KHÔNG BAO GIỜ BẮN — và một lượt torch chạy ngoài ComfyUI (máy B có sẵn
#    `E:\AI\tools\vlm_worker.py` và nhiều script kiểu đó) sẽ đi lọt.

def test_vram_doc_tu_nvidia_smi_chu_khong_tu_system_stats(clock):
    """Con số VRAM báo ra phải là của nvidia-smi, KHÔNG phải của `/system_stats`.

    Ở đây ComfyUI khai card rảnh trắng (25 GB trống) còn nvidia-smi thấy 20 GB đang
    bị giữ. `/health` phải hiện 20 GB — đó là sự thật mà người vận hành cần thấy."""
    t = FakeTransport()
    t.stats["devices"][0]["vram_free"] = 25_000_000_000     # /system_stats: rảnh
    w = _watcher(t, clock, vram_mb=20_000)                  # nvidia-smi: 20 GB dang dung
    assert w.observe(cua_ta=set()).vram_used_mb == 20_000


# ───────── VRAM cao KHÔNG còn là dấu hiệu bận (đo trên máy B 2026-08-22) ─────
#
# ⛔ SỰ CỐ THẬT THỨ HAI, cùng một chốt. Lô 30 ảnh liên tiếp cho thấy VRAM đỉnh
#    **23.967 / 24.576 MB (97,5 %)** và **ở lì đó giữa các job** vì ComfyUI giữ
#    model thường trú; cùng cấu hình khi chỉ chạy 3 ảnh thì đỉnh có 16,8 GB.
#    ⇒ ngưỡng "VRAM > 4 GB ⇒ có kẻ khác" sẽ báo bận VĨNH VIỄN sau lô đầu tiên.
#    Cái phân biệt được là SỐ TIẾN TRÌNH python đang tính trên card.

def test_vram_gan_day_nhung_chi_co_comfyui_thi_KHONG_ban(clock):
    """Đúng cảnh sau một lô ảnh: VRAM 23,9 GB nhưng **chính ComfyUI** giữ chỗ đó.

    `/system_stats` phải nói ComfyUI tự dùng 23,9 GB, không thì dữ liệu giả mô tả
    một cảnh khác hẳn cảnh mà tên test hứa: "nvidia-smi thấy 23,9 GB mà ComfyUI
    bảo nó không dùng gì" nghĩa là **người khác** đang giữ — và lúc đó bận là đúng.
    """
    t = FakeTransport()
    _comfy_tu_dung(t, 23_900)
    w = _watcher(t, clock, vram_mb=23_900, so_py=1)
    st = w.observe(cua_ta=set())
    assert not st.busy
    assert st.vram_used_mb == 23_900          # vẫn báo ra, chỉ không kết luận bận
    assert st.vram_ngoai_mb == 0              # khong ai khac giu gi


def test_hai_tien_trinh_python_tren_gpu_thi_ban(clock):
    """Việc chạy NGOÀI ComfyUI (script torch của dự án video) — hàng đợi không
    thấy, VRAM không phân biệt được, nhưng danh sách tiến trình thì thấy."""
    t = FakeTransport()
    w = _watcher(t, clock, vram_mb=600, so_py=2)
    st = w.observe(cua_ta=set())
    assert st.busy and "tien trinh khac" in st.reason


def test_khong_dem_duoc_tien_trinh_thi_khong_doan_bua(clock):
    t = FakeTransport()
    _comfy_tu_dung(t, 23_900)
    w = _watcher(t, clock, vram_mb=23_900, so_py=None)
    assert not w.observe(cua_ta=set()).busy


# ───────── VRAM bị giữ bởi tiến trình KHÔNG PHẢI PYTHON (đo 2026-08-22 22:27) ─
#
# ⛔ SỰ CỐ THẬT THỨ BA, vẫn cùng một chốt. Máy B chạy thêm một dự án LLM
#    (`H:\LTT_LLM`): `llama-server.exe` nạp một model 27B và giữ **15,9 GB**, GPU
#    **0 % tải**. Phép đếm tiến trình python trả về đúng 1 (chỉ ComfyUI) ⇒ cổng
#    báo **RẢNH** trong khi card chỉ còn 4,6 GB. Nhận job lúc đó là hết VRAM giữa
#    chừng.
#
#    Tiền đề của phép đếm — "tiến trình lạ trên card đều là python" — đúng khi máy
#    chỉ có dự án video, và SAI từ lúc dự án LLM lên. Chốt mới không đoán tên tiến
#    trình: nó lấy HIỆU giữa nvidia-smi (thấy toàn card) và `/system_stats` (chỉ
#    thấy chính nó).

def _comfy_tu_dung(t, mb: int) -> None:
    """Đặt `/system_stats` sao cho ComfyUI **tự** dùng `mb` MB."""
    d = t.stats["devices"][0]
    tong = int(d["vram_total"])
    d["vram_free"] = tong - mb * 1024 * 1024


def test_llama_server_giu_VRAM_thi_BAN_du_khong_phai_python(clock):
    """Cảnh thật 22/08 22:27, số thật: card 24.576, nvidia-smi dùng 19.977,
    ComfyUI tự dùng 1.809 ⇒ người khác giữ 18.168, còn dùng được 6.408 < 20.500."""
    t = FakeTransport()
    _comfy_tu_dung(t, 1_809)
    w = _watcher(t, clock, vram_mb=19_977, so_py=1)
    st = w.observe(cua_ta=set())
    assert st.busy, "llama-server giu 15,9 GB ma cong bao ranh"
    assert st.vram_ngoai_mb == 18_168
    assert "giu" in st.reason and "VRAM" in st.reason


def test_nguong_lay_tu_so_DO_THAT_chu_khong_phai_so_tron():
    """20.500 = đỉnh đo được ở chế độ ảnh tham chiếu (20.000) cộng đệm. Hạ nó xuống
    cho lọt là chọn một con số chưa ai đo — đúng cái bẫy đã ghi ở D-026."""
    assert B.VRAM_CAN_TOI_THIEU_MB >= 20_000


def test_ComfyUI_khong_khai_thiet_bi_thi_KHONG_doan_bua(clock):
    """Không đo được thì trả `None`, và `None` không được biến thành "rảnh" hay
    "bận" — nó phải để chốt này im lặng, nhường cho các chốt khác."""
    t = FakeTransport()
    t.stats["devices"] = []
    w = _watcher(t, clock, vram_mb=23_900, so_py=1)
    st = w.observe(cua_ta=set())
    assert st.vram_ngoai_mb is None and not st.busy


def test_hai_nguon_lech_vai_chuc_MB_khong_thanh_so_AM(clock):
    """Hai đồng hồ đọc lệch nhau là chuyện thường. Một số âm nhỏ không có nghĩa là
    "người khác trả lại bộ nhớ" — kẹp về 0."""
    t = FakeTransport()
    _comfy_tu_dung(t, 5_000)
    w = _watcher(t, clock, vram_mb=4_950, so_py=1)
    assert w.observe(cua_ta=set()).vram_ngoai_mb == 0


def test_hai_chot_doc_lap_nhau(clock):
    """Chốt đếm tiến trình vẫn phải bắt được việc đang TÍNH dù nó chiếm ít bộ nhớ —
    thêm chốt VRAM không được làm chốt kia thành thừa."""
    t = FakeTransport()
    _comfy_tu_dung(t, 600)
    w = _watcher(t, clock, vram_mb=600, so_py=2)
    st = w.observe(cua_ta=set())
    assert st.busy and "tinh tren GPU" in st.reason


def test_dem_python_gpu_that_doc_dung_process_name(monkeypatch):
    """Đo thật trên máy B: 26 PID compute, `used_memory` là `[N/A]` cho MỌI PID
    (WDDM), nhưng `process_name` thì có. Đúng 1 dòng python = ComfyUI.

    ⚠️ Hình dạng đầu ra đổi 12/09 (Task 6.1): truy vấn nay xin thêm cột `gpu_uuid`
    và chỉ đếm tiến trình **trên card 3090**. Bài học của phép kiểm này không đổi
    (đọc `process_name`, không đọc `used_memory`); các ca hai card ở
    `tests/test_1230_busy_theo_uuid.py`."""
    u38 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
    ra = (f"6736, python.exe, {u38}\n"
          f"1234, dwm.exe, {u38}\n"
          f"5678, chrome.exe, {u38}\n")
    monkeypatch.setattr(B.shutil, "which", lambda _: "nvidia-smi")
    monkeypatch.setattr(B.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=ra, stderr=""))
    assert B.so_python_tinh_tren_gpu() == 1

    ra2 = ra + f"9012, python.exe, {u38}\n"
    monkeypatch.setattr(B.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=ra2, stderr=""))
    assert B.so_python_tinh_tren_gpu() == 2


def test_dem_python_gpu_may_khong_co_smi_thi_tra_None(monkeypatch):
    monkeypatch.setattr(B.shutil, "which", lambda _: None)
    assert B.so_python_tinh_tren_gpu() is None


def test_khong_hoi_duoc_nvidia_smi_thi_khong_ne(clock):
    """Không đọc được VRAM là chuyện có thể xảy ra (driver treo). Nó không được
    làm cổng render chết, cũng không được biến thành 'bận' giả."""
    t = FakeTransport()
    w = B.BusyWatcher(comfy=CF.ComfyClient(t), now=clock,
                      doc_vram_mb=lambda: None, dem_python_gpu=lambda: None)
    st = w.observe(cua_ta=set())
    assert not st.busy and st.vram_used_mb == 0


def test_ham_doc_smi_that_khong_nem_khi_may_khong_co_nvidia_smi(monkeypatch):
    """Máy phát triển không có GPU vẫn phải import và chạy được — trả None, không nổ."""
    monkeypatch.setattr(B.shutil, "which", lambda _: None)
    assert B.vram_dung_mb_qua_smi() is None


def test_ham_doc_smi_lay_dong_cua_CARD_3090_khi_nhieu_gpu(monkeypatch):
    """🔴 PHÉP KIỂM NÀY THAY MỘT PHÉP KIỂM ĐÃ BỊ **BỎ**, không phải sửa nó.

    Bản cũ (`test_ham_doc_smi_lay_gia_tri_LON_NHAT_khi_nhieu_gpu`) chốt
    `max()` trên mọi card với lý lẽ *"trả lời theo card bận nhất"*. Lý lẽ ấy chết
    ngày 11/09: máy B có hai card, LTT-3.5 thường trú trên 5060 Ti giữ ~13 GB, và
    cổng render **chỉ tranh 3090**. `max()` trả số của card khác cho mọi câu hỏi
    về 3090 — một phép đo lệch chiều, phải bỏ chứ không phải nới.

    Các ca đầy đủ (đối chứng từng chiều): `tests/test_1230_busy_theo_uuid.py`."""
    u38 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
    u35 = "GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df"

    class R:
        returncode = 0
        stdout = f"{u38}, 512\n{u35}, 8192\n"

    monkeypatch.setattr(B.shutil, "which", lambda _: "nvidia-smi")
    monkeypatch.setattr(B.subprocess, "run", lambda *a, **k: R())
    assert B.vram_dung_mb_qua_smi() == 512

    class RThieu:
        returncode = 0
        stdout = f"{u35}, 8192\n"          # 3090 bien mat khoi danh sach

    monkeypatch.setattr(B.subprocess, "run", lambda *a, **k: RThieu())
    assert B.vram_dung_mb_qua_smi() is None, "roi sang card khac = chay mu"


def test_ham_doc_smi_co_tran_thoi_gian():
    """nvidia-smi treo được (driver lỗi, card kẹt). Vòng dò không được đứng chờ
    vô hạn — cùng trần với `platform_core/gpu.py` của nền tảng."""
    assert B.NVIDIA_SMI_TIMEOUT_S == 8


def test_deploy_dung_gach_cheo_xuoi_cho_duong_dich_scp():
    r"""⛔ SỰ CỐ THẬT 2026-08-21, và nó **im lặng**.

    *(Docstring này là chuỗi thô — tiền tố `r` — vì nó nói về các chuỗi thoát của
    shell. Không có tiền tố đó thì chính docstring này là một chuỗi thoát hỏng, và
    Python sẽ biến cảnh báo đó thành lỗi cứng ở bản sau.)*

    Chép `E:\AI\ltt_render\scripts\tai_model.py` sang máy B: `scp` trả về **0**
    (báo thành công) nhưng **không có tệp nào được tạo**, và cũng không có tệp lạc ở
    đâu cả. Thủ phạm là chuỗi `\t` trong `\tai_model.py` — shell mặc định của
    OpenSSH trên máy B là `cmd.exe` và nó diễn giải dấu gạch ngược.

    Cùng lệnh đó với `gpu_check.py` thì chạy tốt, nên lỗi này **ẩn theo tên tệp**:
    chỉ hiện với những tên bắt đầu bằng `t`, `n`, `b`, `r`… Đúng loại lỗi mà một
    lần thử tay sẽ kết luận nhầm là "đường deploy chạy được".
    """
    text = (_DEPLOY / "deploy.ps1").read_text(encoding="ascii")
    # So khớp theo NGỮ NGHĨA của dòng, không theo chuỗi thoát ký tự — chính chỗ
    # này đã làm test đỏ oan một lần vì đếm nhầm số dấu gạch ngược.
    doi = [d for d in text.splitlines()
           if "-replace" in d and "'/'" in d and ("$dichScp" in d or "$dichHash" in d)]
    assert len(doi) == 2, \
        f"deploy.ps1 phai doi CA HAI duong dich scp sang gach cheo xuoi, thay {len(doi)}"
    # Và không được còn dòng scp nào nhét thẳng đường dẫn Windows vào đích.
    for dong in text.splitlines():
        if "scp -i" in dong and "MayB}:" in dong:
            assert "$dichScp" in dong or "$dichHash" in dong, \
                f"dong scp con dung duong dan gach nguoc: {dong.strip()}"


# ───────────── template ảnh tham chiếu (G5) ─────────────────────────────────
@pytest.mark.parametrize("che_do", ["t2i", "edit", "subject"])
def test_moi_che_do_nap_duoc_va_du_the(che_do):
    """Mọi thẻ trong template phải có giá trị từ `defaults` + tham số chạy.
    Một `@seed` sót lại sẽ được ComfyUI nhận rồi hỏng GIỮA CHỪNG, sau khi đã tiêu
    trọn thời gian nạp model."""
    spec = C.nap_catalog()["hidream-o1"]
    mau = W.nap(spec.modes[che_do].template)
    gia_tri = dict(spec.defaults)
    gia_tri.update({"prompt": "x", "negative": ""})
    for slot in spec.modes[che_do].ref_slots:
        gia_tri[slot] = "anh.png"
    assert W.the_con_thieu(mau, gia_tri) == []


def test_upscale_method_phai_la_gia_tri_ComfyUI_chap_nhan():
    """`upscale_methods` của ComfyUI = nearest-exact · bilinear · area · bicubic ·
    bislerp. **Không có `lanczos`** — tôi suýt dùng nó, và ComfyUI sẽ trả 400."""
    hop_le = {"nearest-exact", "bilinear", "area", "bicubic", "bislerp"}
    assert C.nap_catalog()["hidream-o1"].defaults["upscale"] in hop_le


def test_anh_tham_chieu_can_theo_muc_4MP_va_khop_patch_32():
    """Model huấn luyện ~4 MP và patchify theo bước 32 (`PATCH_SIZE = 32`)."""
    spec = C.nap_catalog()["hidream-o1"]
    assert spec.defaults["ref_mp"] == 4.0
    for che_do in ("edit", "subject"):
        mau = W.nap(spec.modes[che_do].template)
        thang = [n for n in mau.values()
                 if n.get("class_type") == "ImageScaleToTotalPixels"]
        assert thang, f"{che_do} phai co ImageScaleToTotalPixels chan anh ref"
        for n in thang:
            assert n["inputs"]["resolution_steps"] == 32


def test_reference_images_noi_vao_CA_positive_lan_negative():
    """`HiDreamO1ReferenceImages` trả (positive, negative) — phải nối cả hai. Bỏ
    negative là bỏ một nửa điều kiện, và lỗi đó không làm workflow đỏ, chỉ làm ảnh
    xấu đi một cách khó truy."""
    spec = C.nap_catalog()["hidream-o1"]
    for che_do in ("edit", "subject"):
        mau = W.nap(spec.modes[che_do].template)
        ref = [k for k, n in mau.items()
               if n.get("class_type") == "HiDreamO1ReferenceImages"]
        assert len(ref) == 1
        sampler = [n for n in mau.values() if n.get("class_type") == "KSampler"][0]
        assert sampler["inputs"]["positive"] == [ref[0], 0]
        assert sampler["inputs"]["negative"] == [ref[0], 1]


def test_so_slot_ref_khop_so_LoadImage_trong_template():
    spec = C.nap_catalog()["hidream-o1"]
    for che_do, m in spec.modes.items():
        mau = W.nap(m.template)
        so_load = sum(1 for n in mau.values() if n.get("class_type") == "LoadImage")
        assert so_load == len(m.ref_slots), \
            f"{che_do}: {so_load} LoadImage nhung khai {len(m.ref_slots)} ref_slots"


def test_khong_khai_che_do_structure_vi_model_khong_co_controlnet():
    """HiDream-O1 **không hỗ trợ ControlNet** (đã grep `comfy/ldm/hidream_o1/*.py`:
    không có dòng nào). Khai một chế độ `structure` dựa trên ControlNet là hứa một
    thứ model không làm được. G5 sẽ thử đạt nó bằng `edit` + lời nhắc giữ bố cục;
    không đạt thì **ghi rõ là không bán được**, không che bằng UI."""
    assert "structure" not in C.nap_catalog()["hidream-o1"].modes


# ───────── "có bản ghi" ≠ "job của ta đã xong" (sự cố thật 21/08) ────────────
#
# ⛔ Đo thật trên máy B: một prompt **đang CHỜ trong hàng đợi, chưa chạy** vẫn trả
#    về `/history` với `status_str: "success"` — vì `prompt_id` sinh từ `job_id`
#    nên nó **lặp lại** giữa các lần chạy. Bản đầu của runner đọc mỗi bản ghi đó,
#    tuyên bố "xong" sau 0,6 giây, **rồi vẫn xếp hàng lại** — vừa trả kết quả cũ
#    vừa đốt thêm ~100 giây GPU cho không. Lượt đó đã chạy thật và tốn thật.

def test_da_xong_doi_HAI_dieu_kien_khong_phai_mot():
    t = FakeTransport()
    pid = "p1"
    t.history[pid] = _ok_history()
    t.queue_pending = [pid]                       # van dang CHO
    c = CF.ComfyClient(t)
    assert c.history(pid) is not None, "co ban ghi"
    assert not c.da_xong(pid), "nhung CHUA xong — no con trong hang doi"
    t.queue_pending = []
    assert c.da_xong(pid), "roi hang doi thi moi tinh la xong"


def test_da_xong_false_khi_ban_ghi_bao_loi():
    t = FakeTransport()
    t.history["p1"] = {"status": {"status_str": "error", "messages": []}, "outputs": {}}
    assert not CF.ComfyClient(t).da_xong("p1")


def test_runner_KHONG_xep_hang_lai_job_da_chay_xong(tmp_path, clock):
    """Idempotency xuyên tiến trình: cổng khởi động lại rồi nhận lại cùng `job_id`
    thì phải lấy kết quả cũ từ `/history`, **không** vẽ lần hai."""
    t, f = FakeTransport(), FakeFetcher()
    t.history[CF.prompt_id_for("j1")] = _ok_history()   # da chay tu "kiep truoc"
    job = _runner(t, f, tmp_path, clock).run(_req())
    assert job.status == J.COMPLETED and job.image_keys == ["u/1.png"]
    # Khong co lan POST /prompt nao ca.
    assert not [1 for m, p, _ in t.calls if m == "POST" and p == "/prompt"], \
        "da xep hang lai mot job da xong — dot GPU cho khong"
    assert len(f.puts) == 1


def test_prefix_khong_dung_thu_muc_output_cua_du_an_video():
    """`E:/AI/ComfyUI/output/ltt/` đã có sẵn kết quả của dự án video
    (TEST1..TEST5*.mp4). Dùng chung là trộn ảnh của ta vào kết quả của họ."""
    prefix = C.nap_catalog()["hidream-o1"].defaults["prefix"]
    assert prefix.startswith("ltt_h37/"), f"prefix {prefix!r} se ghi vao thu muc cua ho"


# ═══════════ ngân sách token: chốt sinh ra từ vụ máy B sập (D-024) ═══════════
#
# ⛔ SỰ CỐ THẬT 22/08/2026. Cấu hình đang chạy chiếm 23,9/24,6 GB VRAM (97,5 %) và
#    Ở LÌ mức đó giữa các job. Lượt kế trong hàng là `subject` với HAI ảnh tham
#    chiếu 4 MP — một cấu hình CHƯA TỪNG ĐƯỢC ĐO. Máy khởi động lại đột ngột, không
#    một dòng OOM nào trong log (cạn VRAM ở tầng driver, không phải tầng torch).
#
#    Nguyên tắc rút ra: **chưa đo thì không chạy.**

def test_khung_dich_2560x1440_van_qua():
    """Cấu hình đích phải qua — chốt này không được chặn việc bình thường."""
    u = NS.kiem(2560, 1440)
    assert u.tong == 3600 and u.token_tham_chieu == 0


def test_bucket_lon_nhat_da_do_van_qua():
    assert NS.kiem(2048, 2048).tong == 4096


def test_HAI_anh_tham_chieu_4MP_NAY_QUA_vi_DA_DO():
    """⭐ Trước 24/08 cấu hình này bị chặn (11.412 > trần 7.506). Lô G5g đã đo nó:
    **VRAM đỉnh 20.114 MB · 239,0 s · 73 °C** — dưới xa ngưỡng dừng 21.000 MB.

    Nó qua vì **có số đo**, không vì ai đó thấy phiền mà gỡ chốt. Xem D-053.
    """
    assert NS.kiem(2560, 1440, ref_mp=4.0, so_ref=2).tong == 11412


def test_BAC_TIEP_THEO_van_BI_CHAN():
    """Bánh cóc phải còn răng: bậc kế tiếp chưa ai đo thì vẫn phải bị chặn.

    Nếu không có test này thì việc nâng trần một lần sẽ dạy người sau rằng trần là
    thứ nâng được khi thấy phiền — mà đó đúng là điều chốt này sinh ra để chặn.
    """
    with pytest.raises(NS.NgoaiVungDaDo) as e:
        NS.kiem(2560, 1440, ref_mp=8.0, so_ref=2)
    t = str(e.value)
    assert "19224" in t and "11412" in t and "D-024" in t, (
        "loi phai noi ra con so that va loi di tiep")


def test_MOT_anh_tham_chieu_4MP_NAY_QUA_vi_DA_DO():
    """⭐ Trước 22/08 cấu hình này **bị chặn** vì chưa ai đo. G5 đã đo: 7.506 token,
    VRAM đỉnh 19,8 GB, 190,1 s. Nên nay nó qua — và nó qua vì **có số đo**, không
    vì ai đó thấy phiền mà gỡ chốt."""
    u = NS.kiem(2560, 1440, ref_mp=4.0, so_ref=1)
    assert u.tong == 7506


def test_anh_tham_chieu_NHO_thi_qua_duoc():
    """Đường đi tiếp phải TỒN TẠI: bậc đầu tiên (1 ảnh @ 0,4 MP) phải lọt, không thì
    chốt này biến thành 'không bao giờ đo được' và người sau sẽ gỡ nó ra."""
    u = NS.kiem(2560, 1440, ref_mp=0.4, so_ref=1)
    assert 0 < u.token_tham_chieu < 500


def test_token_lam_tron_LEN_khong_lam_tron_xuong():
    """Một hàng ô vá lẻ vẫn tốn cả hàng. Làm tròn xuống là ước lượng THẤP hơn thật
    — đúng hướng nguy hiểm."""
    assert NS.token_khung(33, 33) == 4          # 2x2 chu khong phai 1


def test_runner_TU_CHOI_truoc_khi_cham_GPU(tmp_path):
    """Chốt phải chặn TRƯỚC khi có prompt nào được xếp hàng — nếu nó chỉ chặn sau
    thì GPU đã bị tiêu rồi."""
    t = FakeTransport()
    store = J.JobStore(now=time.monotonic)
    r = Runner(CF.ComfyClient(t), store, FakeFetcher(), input_dir=tmp_path,
               sleep=lambda _: None)
    spec = C.nap_catalog()["hidream-o1"]
    gia_tri = dict(spec.defaults)
    gia_tri.update({"prompt": "x", "negative": "", "ref1": "a.png", "ref2": "b.png",
                    "ref_mp": 8.0})
    # `subject` + 2 anh @8 MP = 19.224 token: ngoai vung da do (tran 11.412).
    # Truoc 24/08 test nay dung 4 MP; bac do da nang no len mot nac (D-053).
    job = r.run(RenderRequest(job_id="j-qua-to", template=spec.modes["subject"].template,
                              values=gia_tri, ref_slots=["ref1", "ref2"]))
    assert job.status == J.FAILED and job.error_code == E_NGOAI_VUNG
    assert not [c for c in t.calls if c[1] == "/prompt" and c[0] == "POST"], \
        "KHONG duoc gui prompt nao khi cau hinh ngoai vung da do"


def test_tran_la_so_DA_DO_chu_khong_phai_so_tinh_ra():
    """Nếu ai đó nâng trần thì phải kèm số đo. Test này neo giá trị hiện tại để
    việc nâng nó là một thay đổi CÓ CHỦ Ý, hiện ra trong diff.

    Lịch sử: 4.096 (G3, chỉ t2i) → **7.506** (G5 22/08, đo chế độ tham chiếu:
    edit 1 ảnh @4 MP và subject 2 ảnh @2 MP, VRAM đỉnh 19,8–20,0 GB)
    → **11.412** (G5g 24/08: subject 2 ảnh @4 MP, VRAM đỉnh 20,1 GB · 239,0 s).

    ⚠️ Và số đo 24/08 nói thêm một điều: token **không** tỉ lệ với nguy hiểm. Token
    gấp 2,1 lần mà VRAM chỉ +1,8 % — VRAM ở đây do trọng số model quyết định. Trần
    này vẫn đúng việc (từ chối cấu hình chưa đo) nhưng đừng đọc nó như thước đo
    mức nguy hiểm."""
    assert NS.TOKEN_DA_DO_TOI_DA == 11412


def test_MOI_duong_goi_ComfyUI_deu_co_chot_ngan_sach():
    """⛔ Bản đầu của chốt chỉ nằm trong `Runner`, và tôi đã viết trong bình luận
    rằng "mọi đường vào job đều đi qua runner". **Sai.** `chay_baseline.py` — đúng
    cái đường đã làm sập máy B hôm 22/08 — gọi thẳng `ComfyClient.queue_prompt`.

    Test này đếm các tệp gọi `queue_prompt` và đòi mỗi tệp đó phải gọi
    `ngan_sach`. Thêm một đường vào ComfyUI mới mà quên chốt thì gate đỏ ngay,
    thay vì lộ ra bằng một lần máy sập nữa.
    """
    goc = _DEPLOY.parent.parent          # thu muc repo
    goi_thang, co_chot = [], []
    for p in sorted(goc.rglob("*.py")):
        if "__pycache__" in p.parts or p.name.startswith("test_"):
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if ".queue_prompt(" not in t:
            continue
        goi_thang.append(p.name)
        if "ngan_sach" in t or "NS.kiem" in t:
            co_chot.append(p.name)

    assert goi_thang, "khong tim thay duong nao goi queue_prompt - test nay hong roi"
    thieu = sorted(set(goi_thang) - set(co_chot))
    assert not thieu, (
        f"nhung tep nay xep hang prompt ma KHONG qua ngan_sach: {thieu}. "
        "Moi duong vao ComfyUI phai co chot - xem D-024.")


def test_thang_do_CHAY_O_TIEN_CANH_va_dung_khi_cham_nguong():
    """⛔ Thang đo là thứ chạy Ở VÙNG CHƯA AI ĐO. Nó là script duy nhất được phép
    vượt trần — nên nó phải là script AN TOÀN NHẤT, không phải script tự do nhất.

    Ba điều bắt buộc, mỗi điều đến từ một sai lầm đã xảy ra thật:
      · KHÔNG `Win32_Process.Create` — lệnh tách khỏi phiên là thứ đã lấy mất quyền
        dừng của chủ dự án (G3, C4 = 7).
      · Có ngưỡng VRAM và **thoát** khi chạm — không "chạy tiếp xem sao" (D-024).
      · Phải gỡ `--tran-token` ra tường minh cho từng bậc.
    """
    duong = _DEPLOY / "thang_do_tham_chieu.ps1"
    # ⚠️ Quét MÃ, không quét chú thích — chính tệp này có câu cảnh báo "Khong
    #    Win32_Process.Create", và lần chạy đầu test đã báo đỏ vì đúng câu đó.
    #    Cùng cái bẫy đã sửa một lần ở `_chi_ma`; ở đây dùng lại nó.
    ma = _chi_ma(duong)
    # ⚠️ Cấm PHÓNG tiến trình tách rời, KHÔNG cấm ĐỌC danh sách tiến trình.
    #    Bản đầu của test này cấm cả chuỗi "win32_process" nên nó bắt oan chính
    #    chốt chống-chạy-hai-bản (chốt đó chỉ `Get-CimInstance Win32_Process` để
    #    dò). Một phép kiểm bắt oan sẽ bị người ta học cách bỏ qua.
    mot_dong = " ".join(ma.split())
    assert "win32_process -methodname create" not in mot_dong, (
        "thang do KHONG duoc tu phong tien trinh tach roi")
    assert "invoke-cimmethod" not in ma, "thang do KHONG duoc tach khoi phien"
    assert "start-process" not in ma
    assert "--tran-token" in ma, "moi bac phai go tran ra tuong minh"
    assert "vramdungmb" in ma and "exit 0" in ma, "phai co nguong va loi thoat"
    # Bậc đầu phải nhỏ. Một "thang" bắt đầu từ 4 MP thì không phải thang.
    assert "0.4" in ma


def test_lo_dai_GHI_KET_QUA_SAU_MOI_ANH_khong_doi_cuoi_lo():
    """⛔ SỰ CỐ THẬT 22/08 (D-025): máy B tự khởi động lại để cài cập nhật Windows
    giữa một lô 30 ảnh, ở ảnh 21. **Toàn bộ số đo của 20 ảnh đã chạy bị mất** — vì
    `chay_baseline.py` chỉ ghi tệp JSON ở cuối lô. Ảnh thì còn trên đĩa; thời
    gian/VRAM/nhiệt thì không.

    Máy B là máy để bàn có Active Hours 07:00–01:00. Nó **sẽ** khởi động lại nữa.
    Nên "ghi ở cuối" không phải là một lựa chọn thiết kế, nó là một lỗi chờ xảy ra.
    """
    src = (_DEPLOY / "chay_baseline.py").read_text(encoding="utf-8")
    assert "def ghi_ket_qua()" in src
    # Phải gọi trong vòng lặp, không chỉ ở cuối hàm. Đếm là cách rẻ nhất để chốt.
    assert src.count("ghi_ket_qua()") >= 4, (
        "phai ghi: khung rong + sau moi anh + hai duong bo qua som + cuoi lo")
    # Và không được còn đường ghi thẳng nào lách qua nó.
    assert "tep.write_text" not in src.replace(
        "        tep.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2),", "")


def test_ban_mau_tham_chieu_dung_KHUON_CO_DAU_CHAM():
    """⛔ Node `HiDreamO1ReferenceImages` nhận input dạng **có dấu chấm**:
    `images.image_1`, KHÔNG phải `image_1` phẳng.

    Cạm bẫy đã dính thật 22/08: ComfyUI báo lỗi
    `required_input_missing -> image_1`, nên bản mẫu viết `image_1` **trông như
    đúng** — trong khi chính nó là thứ bị từ chối. Lý do: `execution.py:903` làm
    `x.split(".")[-1]` khi hiện thông điệp, tức **cắt mất tiền tố**; tên thật nằm ở
    `extra_info.input_name`.

    Tôi đã đọc mã bung lược đồ (`comfy_api/latest/_io.py`) rồi kết luận khuôn phẳng
    là đúng. Đọc mã không đủ; **thử 6 khuôn với ComfyUI thật** mới ra câu trả lời.
    """
    import json as _json
    for ten, khoa in (("hidream_o1_edit.json", ["images.image_1"]),
                      ("hidream_o1_subject.json", ["images.image_1", "images.image_2"])):
        j = _json.loads((_DEPLOY.parent / "workflows" / ten).read_text(encoding="utf-8"))
        vao = j["10"]["inputs"]
        assert set(khoa) <= set(vao), f"{ten}: thieu {set(khoa) - set(vao)}"
        assert not any(k.startswith("image_") for k in vao), (
            f"{ten}: con khoa phang - ComfyUI se tu choi")


def test_workflow_JSON_chi_chua_NODE_khong_chua_ghi_chu():
    """⛔ ComfyUI coi **mọi khoá cấp cao nhất là một node**, và `workflows.nap()`
    không lọc gì cả. Một khoá `_ghi_chu` thêm vào cho dễ đọc sẽ thành một node
    không hợp lệ và bị từ chối cả workflow.

    Đã suýt dính 22/08: tôi chèn ghi chú `_khuon_day` vào chính hai bản mẫu này.
    Ghi chú thuộc về `README.md`, không thuộc về tệp workflow.
    """
    import json as _json
    for p in sorted((_DEPLOY.parent / "workflows").glob("hidream_o1_*.json")):
        j = _json.loads(p.read_text(encoding="utf-8"))
        la = [k for k in j if not k.isdigit()]
        assert not la, f"{p.name}: khoa khong phai node: {la}"


def test_thang_do_TU_TU_CHOI_khi_da_co_ban_khac_dang_chay():
    """⛔ SỰ CỐ THẬT 22/08: lời gọi `exec` của Nexus hết giờ ở PHÍA GỌI nhưng tiến
    trình từ xa **vẫn chạy tiếp**. Mỗi lần thử lại là thêm một bản thang đo. Đã có
    lúc **ba bản chạy cùng lúc**, hàng đợi 2 job, VRAM 19,9 GB — và mọi số đo đều
    vô nghĩa vì chúng đo lẫn nhau.

    Một script đo mà chạy được hai bản cùng lúc thì nó không phải script đo."""
    ma = _chi_ma(_DEPLOY / "thang_do_tham_chieu.ps1")
    assert "thang_do_tham_chieu" in ma, "phai tu tim ban khac cua CHINH NO"
    assert "chay_baseline" in ma, "phai tu choi ca khi dang co lo do khac chay"
    assert "exit 5" in ma


# ═══════ thông số theo TÀI LIỆU CHÍNH THỨC, không theo phỏng đoán (bản 3) ═══════

def test_ban_mau_dat_SHIFT_va_dung_sampler_uni_pc():
    """⛔ Tới 22/08 ta chạy `euler` và **không đặt shift** — trong khi tài liệu
    chính thức của bản Full ghi rõ **50 bước · CFG 5,0 · shift 3,0 · sampler
    `uni_pc`**. Sai lệch đó phát hiện bằng cách **đọc tài liệu**, không bằng cách
    đốt GPU quét tham số.

    `ModelSamplingSD3` là node đặt shift cho model dòng flow; mặc định của nó đúng
    bằng 3,0."""
    d = C.nap_catalog()["hidream-o1"].defaults
    assert d["sampler"] == "uni_pc"
    assert d["shift"] == 3.0
    assert d["steps"] == 50 and d["cfg"] == 5.0
    import json as _json
    for ten in ("hidream_o1_t2i.json", "hidream_o1_edit.json", "hidream_o1_subject.json"):
        j = _json.loads((_DEPLOY.parent / "workflows" / ten).read_text(encoding="utf-8"))
        loai = {n["class_type"] for n in j.values()}
        assert "ModelSamplingSD3" in loai, f"{ten}: thieu node dat shift"


def test_ban_mau_co_khu_vet_noi_luoi_o_va():
    """`HiDreamO1PatchSeamSmoothing` — *"trung bình hoá đầu ra qua nhiều vị trí lưới
    ô vá dịch chuyển ở đoạn cuối lấy mẫu, khử vệt nối"*.

    Kiến trúc này **không có VAE** và làm việc thẳng trên điểm ảnh theo ô vá 32×32,
    nên vệt nối lưới là vấn đề CÓ THẬT của riêng nó — không phải tuỳ chọn trang trí.
    """
    import json as _json
    for ten in ("hidream_o1_t2i.json", "hidream_o1_edit.json", "hidream_o1_subject.json"):
        j = _json.loads((_DEPLOY.parent / "workflows" / ten).read_text(encoding="utf-8"))
        loai = {n["class_type"] for n in j.values()}
        assert "HiDreamO1PatchSeamSmoothing" in loai, f"{ten}: thieu node khu vet noi"


def test_duong_MODEL_di_qua_shift_roi_moi_toi_KSampler():
    """Thứ tự có ý nghĩa: checkpoint → ModelSamplingSD3 → SeamSmoothing → KSampler.
    Nối tắt thẳng checkpoint vào KSampler là hai node kia thành vô dụng mà **không
    có lỗi nào báo** — workflow vẫn chạy, chỉ là không có tác dụng gì."""
    import json as _json
    j = _json.loads((_DEPLOY.parent / "workflows" / "hidream_o1_t2i.json").read_text(encoding="utf-8"))
    nguon_ksampler = j["5"]["inputs"]["model"][0]
    assert j[nguon_ksampler]["class_type"] == "HiDreamO1PatchSeamSmoothing"
    nguon_seam = j[nguon_ksampler]["inputs"]["model"][0]
    assert j[nguon_seam]["class_type"] == "ModelSamplingSD3"
    assert j[nguon_seam]["inputs"]["model"][0] == "1"      # thang tu checkpoint


def test_deploy_KHONG_dung_Environment_NewLine_khi_ghi_cau_hinh():
    """⛔ SỰ CỐ THẬT 22/08: `-join [Environment]::NewLine` ghi ra **cả tệp thành
    MỘT DÒNG**. `gateway.env` khi đó chỉ còn một dòng 281 ký tự chứa hết mọi biến —
    dịch vụ đọc sai và **hỏng im lặng**: nó vẫn khởi động, chỉ là không có token và
    không biết ComfyUI ở đâu.

    Dùng `` "`r`n" `` tường minh. Quy tắc này đứng cạnh quy tắc 1 (không BOM): cùng
    một họ lỗi — tệp cấu hình nhìn thì đúng, máy đọc thì sai."""
    for duong in _PS1:
        ma = _chi_ma(duong)
        assert "[environment]::newline" not in ma, (
            f"{duong.name}: dung \"`r`n\" tuong minh thay vi [Environment]::NewLine")


def test_reserve_vram_KHAI_O_MOT_CHO_va_KHOP_voi_lenh_cai_dich_vu():
    """⛔ `--reserve-vram 3` là thứ đứng giữa lô đo và một lần sập máy (D-024).

    Nó sống ở HAI chỗ: hằng số `VRAM_CHUA_LAI_GB` (mã đọc để tính ngân sách) và
    cờ dòng lệnh trong `cai_dat_dich_vu.ps1` (thứ thật sự tới ComfyUI). Hai chỗ
    lệch nhau thì **mã tính theo một biên mà máy không hề chừa** — và triệu chứng
    là sập giữa một lô dài, không phải một lỗi đọc được.

    Test này không thay được việc kiểm trên máy B; nó chặn việc **mất cờ lặng lẽ**
    ở lần sửa script sau. Đo 24/08 trên máy B: cờ có thật trong `AppParameters`.
    """
    import pathlib
    import re

    goc = pathlib.Path(__file__).resolve().parents[1]
    ps1 = (goc / "render_gateway" / "deploy" / "cai_dat_dich_vu.ps1").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"--reserve-vram\s+(\d+)", ps1)
    assert m, "mat co --reserve-vram trong lenh cai dich vu ComfyUI"
    assert int(m.group(1)) == int(NS.VRAM_CHUA_LAI_GB), (
        f"lenh cai dat chua lai {m.group(1)} GB nhung ngan_sach.py tinh theo "
        f"{NS.VRAM_CHUA_LAI_GB} GB")
