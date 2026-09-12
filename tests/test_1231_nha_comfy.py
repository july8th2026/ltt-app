"""
test_1231 — `POST /v1/nha_comfy`: làm cho VRAM 3090 **sạch** cho LTT-3.8.

Dải test của chương trình LTT LLM Dual-Model: 1200-1249. Tệp này là Task 5.4
(nửa `render_gateway`).

🔴 PHÉP KIỂM QUAN TRỌNG NHẤT Ở ĐÂY LÀ *"LỆNH NÀY DỪNG DỊCH VỤ"*, KHÔNG PHẢI
   *"LỆNH NÀY GỌI `/free`"*.

   Bản plan viết `POST /v1/nha_comfy ⇒ gọi ComfyUI /free {unload_models,
   free_memory}`. Đo 12/09/2026 (L-14 §3) nói điều đó **không đủ**: một ComfyUI
   **ấm mà ngồi im** vẫn giữ **223,5 MiB** ngữ cảnh CUDA và `/free` không nhả nó.
   Biên của LTT-3.8 ở cấu hình đã chốt (`-c 221184 -np 3`) là **445 MiB** ⇒
   223,5 MiB là **một nửa biên**, tiêu cho một tiến trình không làm gì. Tên lệnh
   giữ theo plan (Task 5.5 khớp chuỗi `free_comfy`); nghĩa đổi.

⛔ VÀ NÓ TUYỆT ĐỐI KHÔNG GIẾT VIỆC CỦA AI (L-9). Trọng tài cũ chết vì đúng điều
   đó: `GET /unload` của llama-swap **không drain** — nó cắt ngang một lượt đang
   sinh chữ, và lượt bị giết chỉ nhận `ConnectionReset`. Lệnh mới chỉ thu hồi bộ
   nhớ **của chính ComfyUI**, và **ai** phát nó là quyết định của máy A.

⭐ MỖI CA HỎNG ĐỀU CÓ MỘT PHÉP KIỂM RIÊNG, vì kết cục tệ nhất của tệp này không
   phải "lệnh hỏng" mà là **"lệnh hỏng mà báo thành công"**: trọng tài sẽ tưởng
   card đã sạch rồi nạp 16 GB đè lên phần ComfyUI còn giữ, và cả hai cùng chậm
   trong khi mọi chốt vẫn xanh (P6, D-051).
"""
from __future__ import annotations

import ast
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from render_gateway import busy as B
from render_gateway import danh_tinh_gpu as DT
from render_gateway import dich_vu_comfy as DV
from render_gateway.api import create_app
from render_gateway.config import Config

GOC = Path(__file__).resolve().parents[1]
RG = GOC / "render_gateway"

UUID_3090 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
UUID_5060 = "GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df"

TOKEN = "bi-mat"
DAU = {"Authorization": f"Bearer {TOKEN}"}


# ───────────────────────── SCM giả ──────────────────────────────────────────
#
# ⚠️ Đầu ra dưới đây là **hình dạng thật**, chép từ một lượt `sc.exe query` chạy
#    trên máy Windows này ngày 12/09/2026 — kể cả khoảng trắng và `\r\n`. Bịa ra
#    một hình dạng "hợp lý" là cách bộ phân tích xanh trong test rồi câm ngoài đời.
RA_QUERY = ("\r\n"
            "SERVICE_NAME: {ten}\r\n"
            "        TYPE               : 30  WIN32  \r\n"
            "        STATE              : {ma}  {ten_tt} \r\n"
            "                                (NOT_STOPPABLE, NOT_PAUSABLE, IGNORES_SHUTDOWN)\r\n"
            "        WIN32_EXIT_CODE    : 0  (0x0)\r\n"
            "        SERVICE_EXIT_CODE  : 0  (0x0)\r\n"
            "        CHECKPOINT         : 0x0\r\n"
            "        WAIT_HINT          : 0x0\r\n")

#: `sc.exe` in mã Win32 vào **văn bản** (`[SC] ... FAILED 1060:`). Đo trên máy này.
RA_LOI = "[SC] ControlService FAILED {ma}:\r\n\r\nMot loi nao do.\r\n"

#: `sc enumdepend` — hình dạng thật, chép từ `sc enumdepend Dnscache` trên máy này.
#: Một mục đang chạy (kẻ chặn thật) và một mục đã dừng (không chặn).
RA_ENUMDEPEND = (
    "[SC] EnumDependentServices: entriesread = 2\r\n"
    "\r\n"
    "SERVICE_NAME: LTTRenderGateway\r\n"
    "DISPLAY_NAME: LTT Render Gateway\r\n"
    "        TYPE               : 10  WIN32_OWN_PROCESS  \r\n"
    "        STATE              : 4  RUNNING \r\n"
    "        WIN32_EXIT_CODE    : 0  (0x0)\r\n"
    "\r\n"
    "SERVICE_NAME: MotDichVuDaDung\r\n"
    "DISPLAY_NAME: Khong chan ai\r\n"
    "        TYPE               : 20  WIN32_SHARE_PROCESS  \r\n"
    "        STATE              : 1  STOPPED \r\n"
    "        WIN32_EXIT_CODE    : 1077  (0x435)\r\n")


class ScmGia:
    """`sc.exe` giả. Ghi lại **mọi** lệnh — đó là bằng chứng lệnh có chạy thật."""

    def __init__(self, trang_thai: str = DV.CHAY, *, loi_stop: int = 0,
                 loi_start: int = 0, doi_nhip: int = 0):
        self.tt = trang_thai
        self.loi_stop = loi_stop
        self.loi_start = loi_start
        #: Bao nhiêu lượt `query` đầu tiên trả `STOP_PENDING` thay vì trạng thái
        #: thật — SCM trả `sc stop` về **ngay**, dịch vụ còn đang dừng dở.
        self.doi_nhip = doi_nhip
        self.lenh: list[list[str]] = []

    def __call__(self, doi_so: list[str]) -> DV.KetQuaLenh:
        self.lenh.append(list(doi_so))
        viec, ten = doi_so[0], doi_so[-1]
        if viec == "query":
            if self.doi_nhip > 0:
                self.doi_nhip -= 1
                return DV.KetQuaLenh(0, RA_QUERY.format(ten=ten, ma=3,
                                                        ten_tt="STOP_PENDING"))
            ma = 1 if self.tt == DV.DUNG else 4
            return DV.KetQuaLenh(0, RA_QUERY.format(ten=ten, ma=ma, ten_tt=self.tt))
        if viec == "stop":
            if self.loi_stop:
                return DV.KetQuaLenh(self.loi_stop, RA_LOI.format(ma=self.loi_stop))
            self.tt = DV.DUNG
            return DV.KetQuaLenh(0, "")
        if viec == "start":
            if self.loi_start:
                return DV.KetQuaLenh(self.loi_start, RA_LOI.format(ma=self.loi_start))
            self.tt = DV.CHAY
            return DV.KetQuaLenh(0, "")
        if viec == "enumdepend":
            return DV.KetQuaLenh(0, RA_ENUMDEPEND)
        raise AssertionError(f"lenh la: {doi_so!r}")

    def da_goi(self, viec: str) -> list[list[str]]:
        return [l for l in self.lenh if l and l[0] == viec]


class _Comfy:
    def alive(self):
        return True

    def queue_prompt_ids(self):
        return ([], [])

    def system_stats(self):
        return {"devices": [{"vram_total": 25_769_803_776,
                             "vram_free": 25_769_803_776}]}


class _DongHo:
    """Đồng hồ giả: `ngu()` làm thời gian nhảy, nên không test nào ngủ thật."""

    def __init__(self):
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def ngu(self, giay: float) -> None:
        self.t += giay


def _cong(tmp_path, *, scm, vram=None, doc_vram_mb=None):
    cfg = Config(comfy_url="http://x", comfy_input_dir=tmp_path, host="127.0.0.1",
                 port=8199, token=TOKEN, max_concurrent=1, job_timeout_s=600.0,
                 ram_trong_toi_thieu_gb=48.0, work_dir=tmp_path)
    dh = _DongHo()
    app = create_app(cfg, _Comfy(), workflow_dir=tmp_path,
                     now=dh.now, sleep=dh.ngu, fetcher=object(),
                     chay_dich_vu=scm,
                     **({"doc_vram_mb": doc_vram_mb} if doc_vram_mb else {}))
    return TestClient(app)


# ══ 1. Lệnh THẬT SỰ dừng dịch vụ ════════════════════════════════════════════

def test_nha_comfy_dung_han_dich_vu_LTTComfyUI(tmp_path):
    """⭐ Chốt trung tâm của Task 5.4.

    Nếu ai đó "sửa" endpoint này về lại `POST /free` thì `stop` biến mất khỏi sổ
    lệnh và phép kiểm đỏ — đúng cái nó sinh ra để canh.
    """
    scm = ScmGia(DV.CHAY)
    doc = iter([20_000, 20_000, 900])          # trước, đọc lần 1, đọc lần 2
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: next(doc, 900))

    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 200, r.text
    assert r.json()["da_dung"] is True
    assert scm.da_goi("stop") == [["stop", "LTTComfyUI"]]
    # VRAM báo về là số **đo lại sau khi dừng**, không phải số trước đó.
    assert r.json()["vram_3090_mib"] == 900
    assert r.json()["vram_3090_mib_truoc"] == 20_000


def test_than_rong_cung_la_lenh_dung(tmp_path):
    """Trọng tài phát lệnh không thân (idempotent, lặp được). Mặc định = `dung`."""
    scm = ScmGia(DV.CHAY)
    doc = iter([20_000, 500])
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: next(doc, 500))
    r = c.post("/v1/nha_comfy", headers=DAU)
    assert r.status_code == 200 and scm.da_goi("stop")


def test_da_dung_san_thi_khong_doi_vram_phai_ha(tmp_path):
    """Dừng cái đã dừng là **thành công**, và không có gì để tụt.

    ⚠️ Nếu ca này đòi VRAM tụt thì lượt `free_comfy` thứ hai của trọng tài (nó
    phát lại lệnh khi VRAM chưa sạch) sẽ luôn báo lỗi, và máy trạng thái kẹt ở
    `TRA_ANH` vĩnh viễn.
    """
    scm = ScmGia(DV.DUNG)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: 19_000)
    r = c.post("/v1/nha_comfy", json={"hanh_dong": "dung"}, headers=DAU)
    assert r.status_code == 200 and r.json()["da_dung"] is True
    assert scm.da_goi("stop") == []           # không gửi lệnh thừa


def test_cho_den_khi_SCM_bao_STOPPED_chu_khong_tin_ngay(tmp_path):
    """`sc stop` trả về ngay; dịch vụ còn `STOP_PENDING`. Tin ngay là nói dối."""
    scm = ScmGia(DV.CHAY, doi_nhip=3)
    doc = iter([20_000, 800])
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: next(doc, 800))
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 200, r.text
    assert len(scm.da_goi("query")) >= 3


# ══ 2. Hỏng thì BÁO, không nuốt ═════════════════════════════════════════════

def test_scm_tu_choi_1051_thi_503_va_noi_thang_cach_sua(tmp_path):
    """🔴 CA HỎNG CÓ THẬT NHẤT, và nó là **cấu trúc**, không phải xui.

    `render_gateway/deploy/cai_dat_dich_vu.ps1` đặt
    `nssm set LTTRenderGateway DependOnService LTTComfyUI`. SCM từ chối dừng một
    dịch vụ còn dịch vụ phụ thuộc đang chạy (`ControlService` ⇒
    `ERROR_DEPENDENT_SERVICES_RUNNING`, 1051) ⇒ **chính cổng render là thứ chặn
    lệnh của nó**. Một mã `1051` trần trụi trong log không tự giải thích được,
    nên thông điệp phải mang theo cách sửa.
    """
    scm = ScmGia(DV.CHAY, loi_stop=DV.MA_PHU_THUOC)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: 20_000)
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 503, r.text
    than = r.json()
    assert than["error"]["code"] == "nha_comfy_that_bai"
    assert "1051" in than["error"]["message"]
    assert "DependOnService" in than["error"]["message"]
    # ⭐ Và nó phải NÊU TÊN kẻ chặn, không chỉ nêu mã: một dòng log "ma 1051" bắt
    #    người đọc đi tra Win32; "1051, ke chan la LTTRenderGateway" thì xong ngay.
    assert "LTTRenderGateway" in than["error"]["message"]
    # Chỉ kẻ **đang chạy** mới chặn — mục `STOPPED` không được kể vào.
    assert "MotDichVuDaDung" not in than["error"]["message"]
    assert scm.da_goi("enumdepend") == [["enumdepend", "LTTComfyUI"]]


def test_enumdepend_chi_ke_dich_vu_DANG_CHAY():
    ds = DV.dich_vu_phu_thuoc_dang_chay(
        "LTTComfyUI", chay=lambda _d: DV.KetQuaLenh(0, RA_ENUMDEPEND))
    assert ds == ["LTTRenderGateway"]


def test_khong_doc_duoc_trang_thai_thi_KHONG_bao_da_dung(tmp_path):
    """Không biết ⇒ **không được** nói đã dừng. Cùng luật với `nvidia-smi`."""
    scm = ScmGia(DV.CHAY, loi_stop=0)

    def hong(doi_so):
        scm.lenh.append(list(doi_so))
        return DV.KetQuaLenh(DV.MA_KHONG_CO_DICH_VU,
                             RA_LOI.format(ma=DV.MA_KHONG_CO_DICH_VU))

    c = _cong(tmp_path, scm=hong, doc_vram_mb=lambda: 20_000)
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 503
    assert scm.da_goi("stop") == []     # chưa đọc được thì không gửi lệnh mù


def test_SCM_bao_stopped_ma_VRAM_khong_ha_thi_503(tmp_path):
    """🔴 "Thành công giả" đã đo trên máy B, 22/08.

    `E:\\AI\\venv\\Scripts\\python.exe` là **stub 274 KB**; ComfyUI thật là một
    tiến trình con (PID 8564 → 13912, 3,8 MB → 2.265 MB). Giết mỗi cha thì SCM
    nói "Stopped" trong khi card vẫn bị ôm. Chú thích trong `cai_dat_dich_vu.ps1`
    dặn *"KHONG TIN, HAY DO"* — phép kiểm này là chỗ lời dặn ấy có răng.
    """
    scm = ScmGia(DV.CHAY)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: 20_000)   # không đổi
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 503, r.text
    assert "VRAM 3090 khong ha" in r.json()["error"]["message"]
    assert r.json()["vram_3090_mib"] == 20_000


def test_khong_doc_duoc_VRAM_sau_khi_dung_thi_503(tmp_path):
    """Dừng xong mà không đo được card ⇒ **không xác minh được** ⇒ báo lỗi.

    Chạy mù ở đây là tạo ra đúng sự cố im lặng mà D01 B sinh ra để chặn.
    """
    scm = ScmGia(DV.CHAY)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: None)
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 503
    assert "KHONG doc duoc VRAM" in r.json()["error"]["message"]


def test_hanh_dong_la_thi_tu_choi(tmp_path):
    c = _cong(tmp_path, scm=ScmGia(), doc_vram_mb=lambda: 1)
    assert c.post("/v1/nha_comfy", json={"hanh_dong": "xoa"},
                  headers=DAU).status_code == 400


def test_can_token_nhu_moi_duong_v1(tmp_path):
    c = _cong(tmp_path, scm=ScmGia(), doc_vram_mb=lambda: 1)
    assert c.post("/v1/nha_comfy", json={}).status_code == 401


# ══ 3. Chiều BẬT LẠI — nửa còn lại của lệnh ═════════════════════════════════

def test_chay_lai_bat_dich_vu_len(tmp_path):
    """⭐ Một lệnh chỉ biết tắt sẽ tắt vĩnh viễn tầng sinh ảnh.

    Trọng tài mở cửa sổ `ANH` rồi gửi job vẽ; nếu ComfyUI không còn chạy thì
    `BusyWatcher` coi "ComfyUI không trả lời" là **bận**, và job ảnh nằm hàng đợi
    mãi mãi — đúng khoá chết đã đo 04/09, chỉ khác nguyên nhân.
    """
    scm = ScmGia(DV.DUNG)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: 1_200)
    r = c.post("/v1/nha_comfy", json={"hanh_dong": "chay"}, headers=DAU)
    assert r.status_code == 200, r.text
    assert r.json()["dang_chay"] is True
    assert scm.da_goi("start") == [["start", "LTTComfyUI"]]


def test_chay_lai_hong_thi_503(tmp_path):
    scm = ScmGia(DV.DUNG, loi_start=DV.MA_TU_CHOI)
    c = _cong(tmp_path, scm=scm, doc_vram_mb=lambda: 1_200)
    r = c.post("/v1/nha_comfy", json={"hanh_dong": "chay"}, headers=DAU)
    assert r.status_code == 503
    assert "ACCESS_DENIED" in r.json()["error"]["message"]


# ══ 4. VRAM đọc theo UUID 3090, KHÔNG phải cả máy ═══════════════════════════

@pytest.fixture
def smi(monkeypatch):
    """`nvidia-smi` giả, hai card — hình dạng thật của máy B từ 11/09."""
    o = SimpleNamespace(g3090=0, g5060=0)

    def run(cmd, **kw):
        ra = "".join(f"{uu}, {gt}\n" for uu, gt in
                     ((UUID_3090, o.g3090), (UUID_5060, o.g5060)))
        return SimpleNamespace(returncode=0, stdout=ra, stderr="")

    monkeypatch.setattr(B.shutil, "which", lambda _: "nvidia-smi")
    monkeypatch.setattr(B.subprocess, "run", run)
    DT.xoa_nho()
    yield o
    DT.xoa_nho()


def test_vram_sau_khi_dung_doc_theo_UUID_3090(tmp_path, smi):
    """⭐ CẶP ĐỐI CHỨNG. Cùng một kịch bản, chỉ khác **card nào giữ bộ nhớ**.

    LTT-3.5 thường trú ~13 GB trên 5060 Ti và **không ai tranh** card đó (L-7).
    Một phép đo gộp (`max()` mọi card) sẽ luôn thấy 13 GB và luôn kết luận "card
    vẫn bẩn" ⇒ trọng tài kẹt ở `TRA_ANH`, LTT-3.8 không bao giờ nạp lại.
    """
    assert DT.uuid_38() == UUID_3090, "tep danh tinh trong kho da doi"

    # Ca A — 3090 tụt sau khi dừng; 5060 Ti vẫn ôm 13 GB. Phải THÀNH CÔNG.
    smi.g3090, smi.g5060 = 18_400, 13_000
    scm = ScmGia(DV.CHAY)

    def stop_thi_ha(doi_so):
        kq = scm(doi_so)
        if doi_so and doi_so[0] == "stop":
            smi.g3090 = 700                # ComfyUI thoát, driver thu hồi
        return kq

    c = _cong(tmp_path, scm=stop_thi_ha)   # KHÔNG tiêm doc_vram_mb: đi đường thật
    r = c.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r.status_code == 200, r.text
    assert r.json()["vram_3090_mib"] == 700

    # Ca B — cùng số ấy nhưng ở **3090**: phải THẤT BẠI. Không có vế này thì ca A
    # cũng xanh với một cài đặt luôn trả 700.
    smi.g3090, smi.g5060 = 18_400, 700
    scm2 = ScmGia(DV.CHAY)
    c2 = _cong(tmp_path, scm=scm2)
    r2 = c2.post("/v1/nha_comfy", json={}, headers=DAU)
    assert r2.status_code == 503, r2.text
    assert r2.json()["vram_3090_mib"] == 18_400


def test_khong_biet_UUID_thi_KHONG_bao_thanh_cong(tmp_path, smi, monkeypatch):
    """Không có `gpu_may_b.json` ⇒ không phép đo nào của 3090 hợp lệ ⇒ từ chối.

    (R23: trên máy B tệp ấy phải đi theo bản cài render.)
    """
    monkeypatch.setenv(DT.BIEN_MOI_TRUONG, str(tmp_path / "khong-co.json"))
    monkeypatch.setattr(DT, "_GOC_GOI", tmp_path)
    DT.xoa_nho()
    assert DT.uuid_38() is None
    c = _cong(tmp_path, scm=ScmGia(DV.CHAY))
    assert c.post("/v1/nha_comfy", json={}, headers=DAU).status_code == 503


# ══ 5. Bộ phân tích `sc.exe` — đọc hình dạng THẬT ═══════════════════════════

def test_doc_dung_trang_thai_tu_dau_ra_that():
    """Dòng `TYPE : 30  WIN32` cùng hình dạng với dòng `STATE`. Đọc nhầm nó là
    đọc sai cả phép đo, nên bộ phân tích chỉ nhận số 1-7 **và** tên khớp bảng."""
    assert DV._doc_trang_thai(RA_QUERY.format(ten="X", ma=4, ten_tt="RUNNING")) == DV.CHAY
    assert DV._doc_trang_thai(RA_QUERY.format(ten="X", ma=1, ten_tt="STOPPED")) == DV.DUNG
    assert DV._doc_trang_thai("TYPE : 30  WIN32") is None
    assert DV._doc_trang_thai("") is None


def test_ma_loi_doc_tu_VAN_BAN_khong_chi_tu_exit_code():
    """`sc.exe` in `[SC] ... FAILED <n>:` ra stdout. Chỉ tin exit code là mất mã
    lỗi ở những vỏ cắt nó xuống 8 bit (đo: 1060 → 36 trong bash)."""
    assert DV.ma_loi(DV.KetQuaLenh(36, RA_LOI.format(ma=1060))) == 1060
    assert DV.ma_loi(DV.KetQuaLenh(1051, "")) == 1051
    assert DV.ma_loi(DV.KetQuaLenh(0, "")) == 0


# ══ 6. CHỐT TĨNH: hai trọng tài cũ đã đi khỏi `render_gateway/` ═════════════
#
# 🔴 CHỐT NÀY ĐỌC **AST**, KHÔNG QUÉT VĂN BẢN THÔ. Một bộ dò văn bản thô sẽ bắn
#    vào chính đoạn chú thích giải thích *vì sao* trọng tài cũ phải đi — tức nó
#    trừng phạt việc giải thích và đẩy người sau tới chỗ xoá lời giải thích thay
#    vì xoá cơ chế. Ở đây: **định danh** và **chuỗi không phải docstring** là cơ
#    chế; chú thích và docstring là lời giải thích, và chúng được phép nhắc tên
#    thứ đã chết.

TEN_CAM = {"xin_card", "TraCard", "SoDuoi", "HoDung", "doc_ho_tu_env",
           "nhuong_card"}
CHUOI_CAM = ("8280/unload", "/unload", "LTT_HO_DUNG_CARD", "LTT_TRA_CARD_GIAY")


def _id_docstring(cay: ast.AST) -> set[int]:
    ra: set[int] = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            than = getattr(n, "body", None) or []
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                ra.add(id(than[0].value))
    return ra


def chot_trong_tai_cu(goc: Path) -> list[str]:
    """Những dấu vết **cơ học** của trọng tài cũ còn sót trong một cây nguồn."""
    thay: list[str] = []
    for tep in sorted(goc.rglob("*.py")):
        if "__pycache__" in tep.parts:
            continue
        cay = ast.parse(tep.read_bytes().decode("utf-8-sig"))
        bo_qua = _id_docstring(cay)
        for n in ast.walk(cay):
            ten = None
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                ten = n.name
            elif isinstance(n, ast.Name):
                ten = n.id
            elif isinstance(n, ast.Attribute):
                ten = n.attr
            elif isinstance(n, ast.alias):
                ten = (n.asname or n.name).split(".")[-1]
            if ten in TEN_CAM:
                thay.append(f"{tep.name}: dinh danh {ten!r}")
            if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in bo_qua):
                for c in CHUOI_CAM:
                    if c in n.value:
                        thay.append(f"{tep.name}: chuoi {c!r}")
    return thay


def test_render_gateway_khong_con_trong_tai_cu():
    """⛔ `xin_card` đi vì **cơ học**, không vì gọn: đường đuổi của nó không mang
    tên model và không drain (L-17, L-9)."""
    assert chot_trong_tai_cu(RG) == []
    assert not (RG / "nhuong_card.py").exists()


def _ban_sao(tmp_path: Path) -> Path:
    dich = tmp_path / "render_gateway"
    shutil.copytree(RG, dich, ignore=shutil.ignore_patterns("__pycache__"))
    return dich


def test_DOI_CHUNG_phuc_hoi_xin_card_thi_chot_tinh_DO(tmp_path):
    """⭐ ĐO CHỐT, ĐỪNG CHỈ ĐO SỰ VẮNG MẶT.

    Một phép kiểm chỉ nói "không thấy `xin_card`" cũng xanh khi ai đó xoá luôn cả
    thư mục. Nên ở đây ta **phục hồi** trọng tài cũ trong một bản sao tạm và đòi
    chốt phải ĐỎ.
    """
    ban = _ban_sao(tmp_path)
    assert chot_trong_tai_cu(ban) == []          # bản sao sạch giống bản gốc

    (ban / "nhuong_card.py").write_text(
        "def xin_card(**kw):\n"
        "    duong = 'http://127.0.0.1:8280/unload'\n"
        "    return duong\n", encoding="utf-8")
    thay = chot_trong_tai_cu(ban)
    assert any("xin_card" in x for x in thay), thay
    assert any("8280/unload" in x for x in thay), thay


def test_DOI_CHUNG_chu_thich_giai_thich_KHONG_lam_chot_do(tmp_path):
    """⭐ Nửa còn lại của cùng một quyết định.

    `api.py` **có** một chú thích nhắc đúng tên đường đuổi cũ, vì người sau cần
    biết thứ gì đã chết và vì sao. Nếu chốt bắn vào đó thì cách rẻ nhất để làm nó
    xanh là **xoá lời giải thích** — và ta mất đúng thứ đáng giữ.
    """
    ban = _ban_sao(tmp_path)
    (ban / "ghi_chu.py").write_text(
        '"""Truoc day co xin_card, goi GET /unload cua llama-swap."""\n'
        "# xin_card da bi go: 8280/unload khong mang ten model (L-17).\n"
        "x = 1\n", encoding="utf-8")
    assert chot_trong_tai_cu(ban) == []
