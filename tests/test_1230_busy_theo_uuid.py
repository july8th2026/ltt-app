"""
test_1230_busy_theo_uuid.py — cổng render chỉ được kết luận về **card 3090**.

Dải test của chương trình LTT LLM Dual-Model: 1200-1249 (Task 1.2). Tệp này là
Task 6.1.

🔴 KHUYẾT TẬT ĐANG CHỐT (cơ học, không phải giả thuyết). Máy B có hai card từ
   11/09 và từ Task 3.3 **cả hai** chạy `llama-server`:

       RTX 3090     GPU-26623278-…   LTT-3.8 + model ảnh   <- card TRANH CHẤP
       RTX 5060 Ti  GPU-ebecd0a4-…   LTT-3.5               <- KHÔNG AI TRANH

   `render_gateway/busy.py` đọc `nvidia-smi` **không lọc theo card**: đếm python
   trên mọi card, lấy `max(memory.used)` mọi card, lấy `utilization.gpu` dòng đầu.
   ⇒ LTT-3.5 thường trú trên 5060 Ti làm cổng render báo bận cho một card nó không
   hề chạm, và `VRAM_CAN_TOI_THIEU_MB` bị so với số của card khác.

⭐ MỖI PHÉP KIỂM Ở ĐÂY ĐI KÈM MỘT ĐỐI CHỨNG NGƯỢC CHIỀU. Một phép kiểm chỉ nói
   "5060 Ti không làm bận" thì cũng xanh khi mã trả `busy=False` cho mọi đầu vào.
   Nên mỗi ca có cặp: 5060 Ti ⇒ **rảnh**, cùng số ấy trên 3090 ⇒ **bận**.

⭐ VÀ MỘT ĐỐI CHỨNG MẠNH HƠN: `test_bo_loc_uuid_that_su_thay_doi_ket_luan` dựng
   lại **bản cũ không lọc** ngay trong tệp test và chốt rằng nó trả lời **khác**
   trên cùng chuỗi byte. Đó là cách chốt "bỏ bộ lọc đi thì ca 1 đỏ" mà không phải
   sửa mã sản phẩm rồi hoàn lại.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from render_gateway import busy as B
from render_gateway import danh_tinh_gpu as DT

GOC = Path(__file__).resolve().parents[1]

UUID_3090 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
UUID_5060 = "GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df"


# ── nvidia-smi giả, đúng hình dạng thật của hai card ────────────────────────────
#
# ⚠️ Hai truy vấn, hai hình dạng khác nhau, và `busy.py` dùng CẢ HAI. Tiêm một
#    chuỗi cho cả hai là làm phép đo mất một nửa bề mặt.

def _ra_query_gpu(truong_theo_uuid: dict[str, str]) -> str:
    """`--query-gpu=uuid,<truong> --format=csv,noheader,nounits`."""
    return "".join(f"{uu}, {gt}\n" for uu, gt in truong_theo_uuid.items())


def _ra_compute_apps(dong: list[tuple[int, str, str]]) -> str:
    """`--query-compute-apps=pid,process_name,gpu_uuid --format=csv,noheader`."""
    return "".join(f"{pid}, {ten}, {uu}\n" for pid, ten, uu in dong)


@pytest.fixture
def smi(monkeypatch):
    """Bộ tiêm `nvidia-smi`: định tuyến theo chính truy vấn được gọi."""
    trang_thai: dict[str, object] = {"gpu": {}, "apps": "", "ma": 0, "co_smi": True}

    def _which(_ten):
        return "nvidia-smi" if trang_thai["co_smi"] else None

    def _run(argv, **kw):
        if trang_thai["ma"] != 0:
            return SimpleNamespace(returncode=trang_thai["ma"], stdout="", stderr="")
        truy_van = next((a for a in argv if a.startswith("--query")), "")
        if truy_van.startswith("--query-compute-apps"):
            return SimpleNamespace(returncode=0, stdout=trang_thai["apps"], stderr="")
        # --query-gpu=uuid,<truong>
        truong = truy_van.split(",", 1)[1] if "," in truy_van else ""
        bang = trang_thai["gpu"].get(truong, {})            # type: ignore[union-attr]
        return SimpleNamespace(returncode=0, stdout=_ra_query_gpu(bang), stderr="")

    monkeypatch.setattr(B.shutil, "which", _which)
    monkeypatch.setattr(B.subprocess, "run", _run)

    def dat_gpu(truong: str, **theo_vai):
        trang_thai["gpu"][truong] = {                       # type: ignore[index]
            UUID_3090: theo_vai.get("g3090", 0),
            UUID_5060: theo_vai.get("g5060", 0),
        }

    def dat_apps(dong):
        trang_thai["apps"] = _ra_compute_apps(dong)

    return SimpleNamespace(dat_gpu=dat_gpu, dat_apps=dat_apps, th=trang_thai)


class ComfyGia:
    """ComfyUI giả: chỉ hai lời gọi mà `BusyWatcher` dùng."""

    def __init__(self, *, tong_mb: int = 24_575, tu_dung_mb: int = 0):
        self.tong_mb = tong_mb
        self.tu_dung_mb = tu_dung_mb
        self.ram_free_gb = 96.0

    def queue_prompt_ids(self):
        return [], []

    def system_stats(self):
        tong = self.tong_mb * 1024 * 1024
        return {"system": {"ram_free": int(self.ram_free_gb * 1024 ** 3)},
                "devices": [{"vram_total": tong,
                             "vram_free": tong - self.tu_dung_mb * 1024 * 1024}]}


def _watcher(comfy, clock=None) -> B.BusyWatcher:
    """BusyWatcher với **các bộ đọc THẬT** — đây là thứ đang được đo."""
    dem = iter(range(0, 10_000, 10))
    return B.BusyWatcher(comfy=comfy, now=lambda: next(dem))


# ── Ca 1: bộ nhớ/tiến trình trên 5060 Ti không làm render bận ──────────────────

def test_python_tren_5060_khong_lam_render_ban(smi):
    """Một script torch của dự án khác chạy trên 5060 Ti. Card ấy **không ai
    tranh** (L-7: hai GPU là hai pool độc lập) ⇒ cổng render phải thấy đúng 1
    python (ComfyUI của mình) và báo RẢNH."""
    smi.dat_apps([
        (6736, r"E:\AI\venv\Scripts\python.exe", UUID_3090),   # ComfyUI cua ta
        (1234, r"C:\Windows\System32\dwm.exe", UUID_5060),
        (9012, r"C:\Python312\python.exe", UUID_5060),         # viec cua card khac
    ])
    smi.dat_gpu("memory.used", g3090=1_809, g5060=13_000)
    assert B.so_python_tinh_tren_gpu() == 1
    assert B.vram_dung_mb_qua_smi() == 1_809

    w = _watcher(ComfyGia(tu_dung_mb=1_809))
    st = w.observe(cua_ta=set())
    assert not st.busy, f"5060 Ti lam render ban: {st.reason}"


def test_doi_chung_cung_tien_trinh_do_tren_3090_thi_BAN(smi):
    """Đối chứng ngược chiều của ca trên: **cùng** một tiến trình python, chuyển
    sang 3090, phải làm cổng bận. Nếu không, phép kiểm trên chỉ đang chốt
    `busy=False` cho mọi đầu vào."""
    smi.dat_apps([
        (6736, r"E:\AI\venv\Scripts\python.exe", UUID_3090),
        (1234, r"C:\Windows\System32\dwm.exe", UUID_5060),
        (9012, r"C:\Python312\python.exe", UUID_3090),         # da chuyen sang 3090
    ])
    smi.dat_gpu("memory.used", g3090=1_809, g5060=13_000)
    assert B.so_python_tinh_tren_gpu() == 2

    st = _watcher(ComfyGia(tu_dung_mb=1_809)).observe(cua_ta=set())
    assert st.busy and "tinh tren GPU" in st.reason


def test_VRAM_bi_giu_tren_5060_khong_lam_render_ban(smi):
    """LTT-3.5 thường trú trên 5060 Ti giữ 13 GB. Đó là **đường sống bình thường**
    của máy B từ Task 3.3, không phải một sự cố — và nó không được chặn job ảnh."""
    smi.dat_apps([(6736, "python.exe", UUID_3090)])
    smi.dat_gpu("memory.used", g3090=1_809, g5060=13_000)

    st = _watcher(ComfyGia(tu_dung_mb=1_809)).observe(cua_ta=set())
    assert not st.busy, f"LTT-3.5 tren card khac lam render ban: {st.reason}"
    assert st.vram_used_mb == 1_809, "bao cao VRAM cua card KHAC"
    assert st.vram_ngoai_mb == 0


def test_doi_chung_cung_luong_VRAM_do_tren_3090_thi_BAN(smi):
    """Cảnh thật 22/08 22:27 dịch sang thế giới hai card: `llama-server` giữ
    18.168 MB **trên 3090** ⇒ còn 6.408 MB < 20.500 ⇒ bận."""
    smi.dat_apps([(6736, "python.exe", UUID_3090)])
    smi.dat_gpu("memory.used", g3090=19_977, g5060=13_000)

    st = _watcher(ComfyGia(tu_dung_mb=1_809)).observe(cua_ta=set())
    assert st.busy and st.vram_ngoai_mb == 18_168
    assert "giu" in st.reason and "VRAM" in st.reason


def test_tai_GPU_lay_cua_3090_khong_lay_dong_dau(smi):
    """`api.py::_ho_khac_dang_tinh` dùng số này để quyết định **có đuổi Qwen
    không**. Dòng đầu là card nào thì do driver xếp — đọc sai dòng là đuổi (hay
    không đuổi) vì việc của card khác. Đối chứng: đảo hai giá trị."""
    smi.dat_gpu("utilization.gpu", g3090=3, g5060=97)
    assert B.tai_gpu_phan_tram() == 3
    assert B.tai_gpu_phan_tram() < B.TAI_GPU_DANG_TINH

    smi.dat_gpu("utilization.gpu", g3090=97, g5060=3)
    assert B.tai_gpu_phan_tram() == 97
    assert B.tai_gpu_phan_tram() >= B.TAI_GPU_DANG_TINH


# ── Ca 2: ngưỡng VRAM áp trên DÒNG CỦA 3090 ───────────────────────────────────

def test_nguong_ap_tren_dung_lu0ng_3090_tu_tep_danh_tinh():
    """`_vram_tong_mb` lấy 24.576 từ `gpu_may_b.json`, **không** phải hằng số gõ
    tay và **không** phải tổng hai card (24.576 + 16.311 = 40.887)."""
    w = _watcher(ComfyGia())
    assert w._vram_tong_mb() == DT.vram_tong_mib(DT.VAI_38) == 24_576


def test_nguong_khong_duoc_so_voi_TONG_hai_card(smi):
    """Đối chứng số học, không phải đối chứng lời văn: với 18.168 MB bị giữ,

        so voi 3090 (24.576)      → con 6.408  < 20.500 ⇒ BAN   <- dung
        so voi tong hai card      → con 22.719 > 20.500 ⇒ ranh  <- sai

    Nên một phép kiểm `busy is True` ở đây **phân biệt được** hai cách cài đặt."""
    tong_hai_card = (DT.vram_tong_mib(DT.VAI_38) or 0) + (DT.vram_tong_mib(DT.VAI_35) or 0)
    assert tong_hai_card - 18_168 > B.VRAM_CAN_TOI_THIEU_MB, "doi chung mat nghia"

    smi.dat_apps([(6736, "python.exe", UUID_3090)])
    smi.dat_gpu("memory.used", g3090=19_977, g5060=13_000)
    assert _watcher(ComfyGia(tu_dung_mb=1_809)).observe(cua_ta=set()).busy


def test_ComfyUI_khai_card_KHAC_thi_khong_quy_VRAM_ngoai_nhan(smi):
    """Ghim `CUDA_VISIBLE_DEVICES` của ComfyUI là thứ **hỏng được** (nssm nướng env
    lúc cài — memory `nssm-nuong-env-luc-cai`). Rơi ghim ⇒ `/system_stats` khai
    16.311 MB (5060 Ti) trong khi `nvidia-smi` đã lọc theo 3090 ⇒ hiệu hai card là
    số vô nghĩa ⇒ **không biết** (`None`), không phải một phán quyết."""
    smi.dat_apps([(6736, "python.exe", UUID_3090)])
    smi.dat_gpu("memory.used", g3090=19_977, g5060=13_000)

    st = _watcher(ComfyGia(tong_mb=16_311, tu_dung_mb=1_809)).observe(cua_ta=set())
    assert st.vram_ngoai_mb is None
    # Đối chứng: cùng số ấy với card ĐÚNG thì quy được và ra bận.
    st2 = _watcher(ComfyGia(tong_mb=24_575, tu_dung_mb=1_809)).observe(cua_ta=set())
    assert st2.vram_ngoai_mb == 18_168 and st2.busy


# ── Ca 3: không đọc được / thiếu UUID ⇒ TỪ CHỐI ───────────────────────────────

def test_smi_loi_thi_moi_bo_doc_tra_None(smi):
    smi.th["ma"] = 9
    assert B.vram_dung_mb_qua_smi() is None
    assert B.tai_gpu_phan_tram() is None
    assert B.so_python_tinh_tren_gpu() is None


def test_may_khong_co_smi_thi_tra_None(smi):
    smi.th["co_smi"] = False
    assert B.vram_dung_mb_qua_smi() is None
    assert B.so_python_tinh_tren_gpu() is None


def test_thieu_dong_3090_thi_KHONG_roi_sang_card_khac(smi, monkeypatch):
    """Card rụng khỏi hệ thống là ca đã xảy ra thật (`test_329_chot_so_gpu`), và nó
    trông y hệt "không hỏi được". Cả hai đòi cùng một câu trả lời: **không biết** —
    ⛔ tuyệt đối không phải số của 5060 Ti."""
    monkeypatch.setattr(B.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(
                            returncode=0, stdout=f"{UUID_5060}, 13000\n", stderr=""))
    monkeypatch.setattr(B.shutil, "which", lambda _: "nvidia-smi")
    assert B.vram_dung_mb_qua_smi() is None


def test_compute_apps_thieu_cot_gpu_uuid_thi_KHONG_dem_tam(smi, monkeypatch):
    """Bản cũ của truy vấn (`pid,process_name`) không lọc được theo card. Thấy hình
    dạng ấy thì con số duy nhất ta có là "python trên **một** card nào đó" — dùng
    nó cho câu hỏi về 3090 là chạy mù."""
    monkeypatch.setattr(B.shutil, "which", lambda _: "nvidia-smi")
    monkeypatch.setattr(B.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(
                            returncode=0, stdout="6736, python.exe\n", stderr=""))
    assert B.so_python_tinh_tren_gpu() is None


def test_khong_co_tep_danh_tinh_thi_TU_CHOI(smi, monkeypatch, tmp_path):
    """Không biết UUID nào là 3090 ⇒ không phép đo nào của card ấy hợp lệ.

    🔴 BẢN ĐẦU CÒN CHỐT THÊM *"và `xin_card` phải TỪ CHỐI"*. `xin_card` **đã bị
       gỡ** (dual-model 5.4a): trọng tài cũ nằm trong chính cổng render và nhả model
       bằng `GET /unload` — một lệnh không mang tên model, nay đo được là nó nhả
       **mọi** model đang chạy (L-17).

    ⭐ Nửa còn lại — *"không biết UUID thì mọi bộ đọc trả `None`"* — **vẫn là bất
       biến sống, và nó mới là nửa chiịu lực**: fail-closed ở tầng ĐO thì mọi bên
       gọi đều thừa hưởng, còn fail-closed ở một bên gọi cụ thể thì chỉ bên đó an
       toàn. Ai nối bộ đọc này vào một cửa mới: `None` nghĩa là **từ chối**, không
       phải "coi như 0".
    """
    monkeypatch.setenv(DT.BIEN_MOI_TRUONG, str(tmp_path / "khong-co.json"))
    monkeypatch.setattr(DT, "_GOC_GOI", tmp_path)      # chan ca hai ung vien con lai
    DT.xoa_nho()
    try:
        assert DT.uuid_38() is None
        smi.dat_gpu("memory.used", g3090=1_809, g5060=13_000)
        assert B.vram_dung_mb_qua_smi() is None
        assert B.so_python_tinh_tren_gpu() is None
        assert B.tai_gpu_phan_tram() is None
    finally:
        DT.xoa_nho()


def test_bo_loc_uuid_that_su_thay_doi_ket_luan(smi):
    """⭐ ĐÂY LÀ PHÉP KIỂM QUAN TRỌNG NHẤT CỦA TỆP.

    Ba phép kiểm trên xanh cũng có thể vì đầu vào tình cờ không phân biệt được hai
    cách cài đặt. Nên ở đây ta dựng lại **bản cũ không lọc** — đúng ba dòng thuật
    toán của nó — và chốt rằng trên **cùng** chuỗi byte nó trả lời KHÁC:

        đếm python cả máy        2  (>= 2 ⇒ ban)   vs  theo 3090: 1  (ranh)
        max(memory.used) cả máy  13.000            vs  theo 3090: 1.809
        utilization dòng đầu     tuỳ driver xếp    vs  theo 3090: 3

    Tức "bỏ bộ lọc UUID đi thì ca 1 đỏ" là một câu **đo được**, không phải một
    lời hứa."""
    apps = [
        (6736, r"E:\AI\venv\Scripts\python.exe", UUID_3090),
        (9012, r"C:\Python312\python.exe", UUID_5060),
    ]
    smi.dat_apps(apps)
    smi.dat_gpu("memory.used", g3090=1_809, g5060=13_000)

    ra_apps = _ra_compute_apps(apps)
    ban_cu_dem = sum(1 for d in ra_apps.splitlines() if "python" in d.lower())
    assert ban_cu_dem == 2 >= B.TRAN_PYTHON_GPU, "ban cu se bao BAN"
    assert B.so_python_tinh_tren_gpu() == 1, "ban moi phai bao RANH"

    ra_gpu = _ra_query_gpu({UUID_3090: "1809", UUID_5060: "13000"})
    ban_cu_max = max(int(d.split(",")[-1]) for d in ra_gpu.splitlines() if d.strip())
    assert ban_cu_max == 13_000
    assert B.vram_dung_mb_qua_smi() == 1_809
    assert ban_cu_max != B.vram_dung_mb_qua_smi()


# ── MỘT nguồn danh tính: hai bộ đọc phải khớp ─────────────────────────────────

def test_hai_bo_doc_cung_mot_tep_va_cung_ket_qua():
    """Task 6.1 cho chọn: import `llm_gateway.gpu_uuid` hay viết bộ đọc riêng. Đã
    chọn **bộ đọc riêng** (lý do đo được ở đầu `render_gateway/danh_tinh_gpu.py`:
    bản cài render trên máy B không có gói `llm_gateway`, và chiều phụ thuộc đã
    chốt là `llm_gateway → render_gateway`). Giá của lựa chọn ấy là phép kiểm này:
    hai bộ đọc phải đọc **cùng một tệp** và trả **cùng kết quả**."""
    from llm_gateway import gpu_uuid as GU

    assert DT.duong_danh_tinh() == GU.DUONG_DANH_TINH
    for vai in (DT.VAI_38, DT.VAI_35):
        assert DT.uuid_cua(vai) == GU.uuid_cua(vai)
        assert DT.vram_tong_mib(vai) == GU.vram_tong_mib(vai)
    assert DT.uuid_38() == UUID_3090


def test_khong_co_ban_sao_gpu_may_b_json_trong_kho():
    """Một nguồn chân lý, một tệp. Bản sao dưới `render_gateway/` sinh ra **lúc
    deploy** (máy B không có `llm_gateway/`), không bao giờ commit — hai chỗ khai
    cùng một UUID là đúng cơ chế "bảng chép tay" đã nói sai năm lần ở dự án này."""
    ban_sao = list((GOC / "render_gateway").rglob("gpu_may_b.json"))
    assert not ban_sao, f"ban sao danh tinh GPU trong kho: {ban_sao}"
    goc = json.loads((GOC / "llm_gateway" / "deploy" / "gpu_may_b.json")
                     .read_bytes().decode("utf-8-sig"))
    assert {x["vai"] for x in goc} == {DT.VAI_38, DT.VAI_35}


def test_deploy_render_day_tep_danh_tinh_sang_may_B():
    """Bộ đọc fail-closed ⇒ thiếu tệp là cổng render báo bận vĩnh viễn. Nên bước
    chép tệp json **phải** có trong `deploy.ps1`, và đích phải nằm trong gói
    render (nơi duy nhất bản cài render nhìn thấy)."""
    ps = (GOC / "render_gateway" / "deploy" / "deploy.ps1").read_bytes().decode("ascii")
    assert "llm_gateway\\deploy\\gpu_may_b.json" in ps
    assert "render_gateway\\deploy\\gpu_may_b.json" in ps


def test_render_gateway_khong_import_llm_gateway():
    """Rào cơ học cho quyết định thiết kế. `.importlinter` chỉ khai ba
    `root_packages` (`platform_core`, `server`, `apps`) ⇒ nó **không** canh cặp
    này; phép kiểm này là thứ duy nhất canh.

    Chiều đúng là `llm_gateway → render_gateway` (`trong_tai.py:89,114`,
    `kiem_import.py:41`). Thêm chiều ngược là một **vòng** giữa hai gói, và nó
    chết ở đúng chỗ phải sống: `E:\\AI\\ltt_render\\gateway\\` không có
    `llm_gateway/`."""
    vi_pham = []
    for tep in sorted((GOC / "render_gateway").rglob("*.py")):
        if "__pycache__" in tep.parts:
            continue
        cay = ast.parse(tep.read_bytes().decode("utf-8"))
        for n in ast.walk(cay):
            if isinstance(n, ast.Import):
                if any(a.name.split(".")[0] == "llm_gateway" for a in n.names):
                    vi_pham.append(f"{tep.name}:{n.lineno}")
            elif isinstance(n, ast.ImportFrom):
                if (n.module or "").split(".")[0] == "llm_gateway":
                    vi_pham.append(f"{tep.name}:{n.lineno}")
    assert not vi_pham, f"render_gateway import llm_gateway: {vi_pham}"


def test_busy_khong_gan_UUID_vao_ma_nguon():
    """UUID nằm ở `gpu_may_b.json`, không ở mã. Chép nó vào `busy.py` là dựng lại
    đúng cơ chế Task 0.2 đã bỏ — và `busy.py` nói về UUID rất nhiều trong chú
    thích, nên phép kiểm phải đọc **mã**, không đọc văn bản (memory
    `bo-do-quet-van-ban-trung-phat-viec-giai-thich`)."""
    cay = ast.parse((GOC / "render_gateway" / "busy.py").read_bytes().decode("utf-8"))
    # Bỏ docstring theo **nút**, không theo giá trị: `ast.get_docstring` đã
    # `cleandoc` nên so bằng chuỗi thì không khớp và mọi docstring sẽ bị tính là
    # một hằng số của phép đo.
    la_docstring = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            dau = (n.body or [None])[0]
            if (isinstance(dau, ast.Expr) and isinstance(dau.value, ast.Constant)
                    and isinstance(dau.value.value, str)):
                la_docstring.add(id(dau.value))
    xau = [n.value for n in ast.walk(cay)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and id(n) not in la_docstring and "GPU-" in n.value]
    assert not xau, f"UUID gan cung trong busy.py: {xau}"
