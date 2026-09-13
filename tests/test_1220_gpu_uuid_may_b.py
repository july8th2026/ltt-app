"""Task 4.1 (LTT LLM Dual-Model) — mọi phép đo GPU máy B phải đi **theo UUID**.

🔴 CA HỎNG MÀ TỆP NÀY DỰNG LẠI. Từ 09/2026 máy B có hai card (3090 cho LTT-3.8 +
   ComfyUI, 5060 Ti cho LTT-3.5). Mọi bộ đo trong kho viết cho **một** card và
   hỏng theo cùng một cách: `nvidia-smi --query-gpu=memory.used` rồi
   `splitlines()[0]`.

   Với hai card, dòng đầu là **một** trong hai, và cái nào thì do driver quyết.
   Hậu quả không phải "số hơi lệch" mà là **phép đo lệch chiều**: chốt
   `tren_gpu.py` (sinh ra để bắt "model bò trên CPU") đọc số của card KHÁC, nên
   một model thật sự rơi về CPU trên 3090 vẫn xanh khi 5060 Ti đang giữ 13 GB.

⭐ Ba phép kiểm ở đây, theo ba tầng:

     1. HÀNH VI  — `vram_mib(uuid 3090)` trả dòng của 3090 **kể cả khi 3090 nằm
                   ở dòng thứ hai** (đầu ra `nvidia-smi` tiêm, đảo thứ tự).
     2. CỬA      — thiếu một UUID ⇒ `/health/ready` 503 (fail-closed).
     3. TĨNH     — không chỗ nào trong `llm_gateway/` còn lấy `dong[0]` trên đầu
                   ra `nvidia-smi`, không `--query-compute-apps` thiếu cột lọc
                   `gpu_uuid`, không `taskkill /im llama-server.exe`.

⛔ Bộ dò tĩnh đọc **AST**, không quét văn bản. Quét văn bản trừng phạt việc giải
   thích: chính chú thích *"bản cũ lấy `dong[0]`"* trong `gpu_uuid.py` sẽ làm một
   bộ dò văn bản đỏ, và người sửa sẽ học cách **xoá lời giải thích** thay vì xoá
   khuyết tật.

Đối chứng: `test_doi_chung_*` phục hồi đúng hình dạng cũ vào một tệp tạm và đòi
bộ dò báo ĐỎ. Không có đối chứng thì một bộ dò không tìm thấy gì trông y hệt một
bộ dò không tìm.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess
import types

import pytest

from llm_gateway import gpu_uuid as GU

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── Đồ giả: `nvidia-smi` hai card, thứ tự ĐẢO ────────────────────────────────

class SmiGia:
    """`subprocess.run` giả. Nhớ mọi lời gọi để test soi được đối số."""

    def __init__(self, ra: str = "", ma: int = 0, no: bool = False):
        self.ra = ra
        self.ma = ma
        self.no = no
        self.goi: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.goi.append(list(argv))
        if self.no:
            raise OSError("nvidia-smi khong chay duoc")
        return types.SimpleNamespace(returncode=self.ma, stdout=self.ra, stderr="")

    @property
    def truy_van(self) -> str:
        """Chuỗi `--query-*` của lời gọi cuối. Để soi bộ đo xin đúng cột."""
        return " ".join(self.goi[-1]) if self.goi else ""


def _uu(vai: str) -> str:
    """UUID lấy từ `gpu_may_b.json` — KHÔNG gõ lại vào tệp test này.

    Gõ lại là dựng lại đúng "bảng chép tay" mà `test_1200` đã gỡ: hai chỗ khai
    cùng một điều, và không ai bắt chúng khớp.
    """
    return GU.uuid_cua(vai)


def _ra_hai_card_dao(dung38=24_131, trong38=445, util38=92,
                     dung35=15_309, trong35=1_002, util35=41) -> str:
    """Đầu ra `--query-gpu=uuid,memory.used,memory.free,utilization.gpu`.

    🔑 **5060 Ti ở dòng ĐẦU, 3090 ở dòng THỨ HAI** — đó là cả mục đích. Bản cũ
       lấy dòng đầu nên nó sẽ trả số của 5060 Ti khi được hỏi về 3090.

    Số đo thật (`10_BENCHMARK_P3.md`): 3090 sau nạp `-c 221184 -np 3` + mmproj
    = 24.131 MiB, biên 445 (§G1b) · 5060 Ti Q6_K + MTP n-max 2 = 15.309 MiB,
    biên 1.002 (§G3b).
    """
    return (f"{_uu('ltt35')}, {dung35}, {trong35}, {util35}\n"
            f"{_uu('ltt38')}, {dung38}, {trong38}, {util38}\n")


# ── 1. Danh tính đọc từ tệp, không hằng số trong mã ─────────────────────────

def test_danh_tinh_co_du_hai_vai():
    d = {x["vai"]: x for x in GU.doc_danh_tinh()}
    assert set(d) >= {GU.VAI_38, GU.VAI_35}
    assert d[GU.VAI_38]["uuid"] != d[GU.VAI_35]["uuid"]
    assert GU.uuid_cua(GU.VAI_38).startswith("GPU-")
    assert GU.vram_tong_mib(GU.VAI_38) > GU.vram_tong_mib(GU.VAI_35), (
        "3090 (24 GB) phai lon hon 5060 Ti (16 GB) - hai vai bi dao?")


def test_vai_khong_co_thi_NEM_chu_khong_tra_rong():
    """⛔ Chuỗi rỗng lọt qua mọi phép so sánh xuống dưới và biến 'không biết card
    nào' thành 'không card nào khớp' — một phép đo rỗng đội lốt phép đo sạch."""
    with pytest.raises(GU.VaiKhongCo):
        GU.uuid_cua("ltt99")


@pytest.mark.parametrize("ten,vai", [
    ("qwen38-api", GU.VAI_38),
    ("qwen35-api", GU.VAI_35),
    ("qwen38-vision", GU.VAI_38),          # hồ sơ cũ, vẫn phải map đúng card
    ("khong-biet", None),
])
def test_ho_so_map_dung_card(ten, vai):
    assert GU.vai_cua_model(ten) == vai


def test_doc_danh_tinh_song_sot_qua_BOM(tmp_path):
    """`Out-File -Encoding utf8` của PowerShell 5.1 chèn BOM. Chết vì ba byte vô
    hình là mất toàn bộ phép đo GPU."""
    tep = tmp_path / "gpu.json"
    tep.write_bytes(b"\xef\xbb\xbf" + b'[{"vai":"ltt38","uuid":"GPU-x","vram_mib":1}]')
    assert GU.doc_danh_tinh(tep)[0]["uuid"] == "GPU-x"


# ── 2. Đọc đúng CARD, kể cả khi nó không ở dòng đầu ─────────────────────────

def test_vram_lay_dung_card_KE_CA_khi_no_o_dong_THU_HAI():
    """🔴 ĐÂY LÀ PHÉP KIỂM TRUNG TÂM CỦA TASK 4.1."""
    smi = SmiGia(_ra_hai_card_dao())
    assert GU.vram_mib(_uu("ltt38"), chay=smi) == 24_131
    assert GU.vram_mib(_uu("ltt35"), chay=smi) == 15_309
    assert GU.vram_trong_mib(_uu("ltt38"), chay=smi) == 445
    assert GU.vram_trong_mib(_uu("ltt35"), chay=smi) == 1_002
    assert GU.util_pt(_uu("ltt38"), chay=smi) == 92


def test_truy_van_PHAI_xin_cot_uuid():
    """Không xin cột `uuid` thì không có gì để lọc — và bộ đo lại chỉ còn cách
    đoán theo thứ tự dòng, tức đúng khuyết tật cũ ở một hình dạng khác."""
    smi = SmiGia(_ra_hai_card_dao())
    GU.vram_mib(_uu("ltt38"), chay=smi)
    assert "--query-gpu=uuid," in smi.truy_van


def test_doi_chung_lay_dong_dau_thi_SAI_CARD():
    """Đối chứng: phục hồi hành vi cũ (`splitlines()[0]`) trên **cùng** đầu ra
    thì con số trả về là của card KHÁC. Đây là bằng chứng phép kiểm trên đo thật
    một điều gì — không có nó thì '24131' có thể chỉ là số duy nhất có mặt."""
    ra = _ra_hai_card_dao()
    cu = int(ra.splitlines()[0].split(",")[1])
    assert cu == 15_309, "dong dau phai la 5060 Ti trong mau nay"
    assert cu != GU.vram_mib(_uu("ltt38"), chay=SmiGia(ra))


@pytest.mark.parametrize("smi", [
    SmiGia(_ra_hai_card_dao(), ma=9),                    # nvidia-smi tra ma loi
    SmiGia("", ma=0),                                    # khong dong nao
    SmiGia("GPU-khong-phai-cua-ta, 1, 2, 3\n"),           # khong card nao khop
    SmiGia(no=True),                                     # khong goi duoc
])
def test_khong_hoi_duoc_thi_None_chu_khong_ZERO(smi):
    """⛔ `None` KHÁC 0. Không phân biệt được thì một lần 'không hỏi được' trông
    y hệt 'card đang trống' — và với một cái sàn VRAM thì đó là chiều nguy hiểm."""
    assert GU.vram_mib(_uu("ltt38"), chay=smi) is None
    assert GU.vram_trong_mib(_uu("ltt38"), chay=smi) is None
    assert GU.doc_the(_uu("ltt38"), chay=smi) is None


def test_doc_the_chi_MOT_lan_goi_cho_ba_so():
    smi = SmiGia(_ra_hai_card_dao())
    the = GU.doc_the(_uu("ltt35"), chay=smi)
    assert the == {"vram_dung_mib": 15_309, "vram_trong_mib": 1_002, "util_pt": 41}
    assert len(smi.goi) == 1, f"{len(smi.goi)} lan goi nvidia-smi cho mot the"


# ── 3. Tiến trình: lọc theo UUID ────────────────────────────────────────────

def test_tien_trinh_LOC_dung_card():
    ra = (f"111, llama-server.exe, 24000, {_uu('ltt38')}\n"
          f"222, llama-server.exe, 15000, {_uu('ltt35')}\n"
          f"333, python.exe, [N/A], {_uu('ltt38')}\n")
    smi = SmiGia(ra)
    t38 = GU.tien_trinh(_uu("ltt38"), chay=smi)
    assert [x[0] for x in t38] == [111, 333]
    assert GU.tien_trinh(_uu("ltt35"), chay=smi) == [(222, "llama-server.exe", 15_000)]
    assert "--query-compute-apps=" in smi.truy_van and "gpu_uuid" in smi.truy_van


def test_tien_trinh_GIU_dong_co_used_memory_NA():
    """`[N/A]` là chuyện thường trên WDDM. Sự tồn tại của tiến trình là tin chắc
    chắn; chỉ dung lượng là không biết. Bỏ cả dòng = 'card rảnh' trong khi có
    việc đang chạy."""
    smi = SmiGia(f"333, python.exe, [N/A], {_uu('ltt38')}\n")
    assert GU.tien_trinh(_uu("ltt38"), chay=smi) == [(333, "python.exe", 0)]


# ── 4. `thay_du_hai_card` + `/health/ready` fail-closed ─────────────────────

def test_thay_du_hai_card():
    du = SmiGia(f"{_uu('ltt35')}\n{_uu('ltt38')}\n")
    assert GU.thay_du_hai_card(chay=du) is True


@pytest.mark.parametrize("smi", [
    SmiGia("GPU-26623278-4fa5-82db-4306-237651b03e78\n"),   # chi con mot card
    SmiGia(""),
    SmiGia("x", ma=2),
    SmiGia(no=True),
])
def test_thieu_card_hoac_khong_hoi_duoc_deu_la_KHONG_DU(smi):
    """Fail-closed: một card **rụng** khỏi hệ thống trông giống hệt 'không hỏi
    được', và cả hai đòi cùng một hành động — đừng nhận lượt mới."""
    assert GU.thay_du_hai_card(chay=smi) is False


def test_doc_danh_tinh_hong_CUNG_LA_fail_closed(tmp_path):
    """🔴 Cổng N, 13/09: **đọc không được danh tính cũng phải là fail-closed**.

    Trước 13/09 ngoại lệ đọc tệp bay thẳng ra ngoài, nên `/health/ready` thành
    **500** thay vì **503**. Spec §22 đòi 503 cho ca *"GPU không thấy (UUID
    thiếu)"*, và RUNBOOK cảnh báo đúng tình huống ấy: một bản cài đặt thiếu
    `gpu_may_b.json` là **dừng hẳn** việc sinh ảnh.

    ⛔ Và 500 vs 503 không phải chuyện chữ nghĩa ở một chốt SẴN SÀNG: 503 là
       *"chưa sẵn sàng, đừng gửi lượt tới"* — một câu trả lời; 500 là *"chính
       chốt này đang hỏng"* — một câu hỏi mới.

    ⭐ Docstring của chính hàm ấy đã nói lý do, chỉ là nó viết cho một ca khác:
       *"không hỏi được `nvidia-smi` ⇒ False … hai thứ ấy đòi CÙNG MỘT hành
       động"*. "Không đọc được danh tính" là thể thứ ba của cùng câu hỏi.
    """
    du = SmiGia(f"{_uu('ltt35')}\n{_uu('ltt38')}\n")

    # driver thay du card, nhung TEP DANH TINH khong doc duoc
    assert GU.thay_du_hai_card(chay=du, duong=tmp_path / "khong-co.json") is False

    hong = tmp_path / "hong.json"
    hong.write_text("{khong phai json}", encoding="utf-8")
    assert GU.thay_du_hai_card(chay=du, duong=hong) is False

    rong = tmp_path / "rong.json"
    rong.write_text("", encoding="utf-8")
    assert GU.thay_du_hai_card(chay=du, duong=rong) is False


def test_doi_chung_tep_DUNG_van_tra_True(tmp_path):
    """Đối chứng: bản vá trên không được biến mọi thứ thành `False`.

    Thiếu phép này thì `return False` vô điều kiện cũng xanh — và khi ấy
    `/health/ready` **không bao giờ** báo sẵn sàng.
    """
    import json

    tep = tmp_path / "gpu.json"
    tep.write_text(json.dumps([{"vai": "ltt38", "uuid": _uu("ltt38")},
                               {"vai": "ltt35", "uuid": _uu("ltt35")}]),
                   encoding="utf-8")
    du = SmiGia(f"{_uu('ltt35')}\n{_uu('ltt38')}\n")
    assert GU.thay_du_hai_card(chay=du, duong=tep) is True


def test_health_ready_503_khi_thieu_card(monkeypatch):
    from tests.test_250_llm_gateway import _client

    c, _ = _client()
    monkeypatch.setattr(GU, "thay_du_hai_card", lambda **kw: False)
    r = c.get("/health/ready")
    assert r.status_code == 503, r.text
    assert r.json()["ok"] is False

    monkeypatch.setattr(GU, "thay_du_hai_card", lambda **kw: True)
    r2 = c.get("/health/ready")
    assert r2.status_code == 200 and r2.json()["ok"] is True


def test_health_ready_KHONG_lo_gi_ngoai_san_sang(monkeypatch):
    """Cùng luật với `/live`: mỗi trường thêm vào là một thứ rò cho người chưa
    xác thực. Chi tiết card nằm ở `/health`, sau khoá."""
    from tests.test_250_llm_gateway import _cfg, _client

    monkeypatch.setattr(GU, "thay_du_hai_card", lambda **kw: True)
    c, _ = _client(_cfg(token="bimat"))
    d = c.get("/health/ready").json()
    assert set(d) <= {"ok", "ly_do"}, f"lo them truong: {sorted(d)}"


def test_health_bao_TUNG_CARD_theo_vai(monkeypatch):
    """`/health` phải nói về **từng** card. Một con số gộp cho hai card trả lời
    câu 'có vấn đề không' nhưng không trả lời 'ở đâu' — và hai card này chạy hai
    model khác nhau nên 'ở đâu' chính là câu duy nhất hữu ích."""
    from tests.test_250_llm_gateway import _client

    monkeypatch.setattr(GU, "doc_the", lambda uu, **kw: (
        {"vram_dung_mib": 24_131, "vram_trong_mib": 445, "util_pt": 92}
        if uu == _uu("ltt38") else
        {"vram_dung_mib": 15_309, "vram_trong_mib": 1_002, "util_pt": 41}))
    c, _ = _client()
    g = c.get("/health").json()["gpu"]
    # Khoi cu PHAI con nguyen: `platform_core` doc `gpu.dang_lo` de bao dong
    # (`test_277`, `test_378`), va do la mot hop dong dang chay that.
    assert set(g) >= {"tren_gpu", "vram_dung_mb", "co_model_nap", "dang_lo"}
    assert set(g["theo_vai"]) == {GU.VAI_38, GU.VAI_35}
    assert g["theo_vai"][GU.VAI_35]["vram_dung_mb"] == 15_309
    assert g["theo_vai"][GU.VAI_38]["vram_trong_mb"] == 445


# ── 5. Chốt TĨNH: hình dạng cũ không được quay lại ──────────────────────────

TEN_SMI = ("nvidia-smi", "--query-gpu", "--query-compute-apps")


def _ham_co_smi(ham: ast.AST) -> bool:
    """Thân hàm có nhắc tới `nvidia-smi` (dạng chuỗi hằng) không."""
    for n in ast.walk(ham):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if any(t in n.value for t in TEN_SMI):
                return True
    return False


def _la_chia_dong(n: ast.AST) -> bool:
    """Lời gọi này có chia đầu ra thành **các DÒNG** không?

    ⚠️ `splitlines()` và `split(chr(10))` chia theo dòng — tức theo **card**.
       `split(",")` chia theo cột, tức trong **một** card. Gộp hai thứ ấy làm bộ
       dò đỏ với chính bản đã sửa (`o = dong.split(",")` rồi `o[0] == uuid` là
       đường ĐÚNG), và một bộ dò đỏ với mọi thứ thì nó không nói được gì.
    """
    if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
        return False
    if n.func.attr == "splitlines":
        return True
    if n.func.attr == "split" and n.args:
        a = n.args[0]
        return isinstance(a, ast.Constant) and a.value == "\n"
    return False


def _co_chia_dong(n: ast.AST) -> bool:
    return any(_la_chia_dong(x) for x in ast.walk(n))


def _co_stdout(n: ast.AST) -> bool:
    return any(isinstance(x, ast.Attribute) and x.attr == "stdout"
               for x in ast.walk(n))


def _lay_dong_dau(ham: ast.AST) -> bool:
    """Có lấy phần tử `[0]` của một danh sách **dòng** không.

    Bắt cả hai hình dạng đã thật sự tồn tại trong kho:
        `(r.stdout or "").strip().splitlines()[0]`          (`don_dep`)
        `dong = [d for d in ....splitlines() ...]; dong[0]` (`gpu_check`)
    """
    ten_dong: set[str] = set()
    for n in ast.walk(ham):
        if isinstance(n, ast.Assign) and _co_chia_dong(n.value):
            for m in n.targets:
                if isinstance(m, ast.Name):
                    ten_dong.add(m.id)
    for n in ast.walk(ham):
        if not isinstance(n, ast.Subscript):
            continue
        chi_so = n.slice
        if not (isinstance(chi_so, ast.Constant) and chi_so.value == 0):
            continue
        gt = n.value
        if _la_chia_dong(gt):
            return True
        if isinstance(gt, ast.Name) and gt.id in ten_dong:
            return True
    return False


def _chia_cot_tren_stdout_tho(ham: ast.AST) -> bool:
    """`r.stdout.strip().split(",")` — chia cột trên đầu ra CHƯA tách dòng.

    🔴 HÌNH DẠNG NÀY IM LẶNG HƠN CẢ `dong[0]`. Với hai card,
       `"a,b\\nc,d".split(",")` cho `['a', 'b\\nc', 'd']`, nên `v[0]` vẫn là một
       con số **đọc được** — của card đầu tiên, luôn luôn, không lời cảnh báo
       nào. Đây là bản `tools/bench_llm_hieu_nang._smi` đã dùng.
    """
    for n in ast.walk(ham):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        if n.func.attr != "split":
            continue
        nhan = n.func.value
        if _co_stdout(nhan) and not _co_chia_dong(nhan):
            return True
    return False


def _compute_apps_thieu_loc(ham: ast.AST) -> bool:
    """`--query-compute-apps` mà không xin cột `gpu_uuid` ⇒ đếm trên MỌI card."""
    for n in ast.walk(ham):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if "--query-compute-apps" in n.value and "gpu_uuid" not in n.value:
                return True
    return False


def quet_py(duong: pathlib.Path) -> list[str]:
    """Trả về danh sách vi phạm dạng `<tep>:<ham>:<loai>`. Rỗng = sạch."""
    cay = ast.parse(duong.read_bytes().decode("utf-8"), filename=str(duong))
    vi_pham: list[str] = []
    for n in ast.walk(cay):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _ham_co_smi(n):
            continue
        if _lay_dong_dau(n):
            vi_pham.append(f"{duong.name}:{n.name}:dong[0]")
        if _chia_cot_tren_stdout_tho(n):
            vi_pham.append(f"{duong.name}:{n.name}:chia-cot-tren-stdout-tho")
        if _compute_apps_thieu_loc(n):
            vi_pham.append(f"{duong.name}:{n.name}:compute-apps-khong-loc")
    return vi_pham


def _quet_goi(goi: str) -> list[str]:
    ra: list[str] = []
    for t in sorted((GOC / goi).rglob("*.py")):
        if "__pycache__" in t.parts:
            continue
        ra += quet_py(t)
    return ra


def test_llm_gateway_KHONG_con_doc_GPU_theo_dong():
    assert _quet_goi("llm_gateway") == []


def test_render_gateway_KHONG_con_doc_GPU_theo_dong():
    """⛔ Khong ham nao trong `render_gateway` duoc doc GPU theo **dong dau tien**.

    🔵 `xfail(strict=True, reason="cho Task 6.1")` DA GO ngay 12/09. Ba cho
       tung vi pham, va chung khong bang nhau ve hau qua:

         busy.py::_hoi_smi / _dem_python   → cua CAP SUAT. Sai card o day la cap
                                             suat khi card that da day. (Task 6.1)
         diagnostics/gpu_check.py::_hoi_smi → cong cu chan doan. (controller, 12/09)
         deploy/chay_baseline.py::run       → di vao mot **MOC BASELINE**: mot moc
                                             dong tren card khac lam MOI phep so
                                             sanh ve sau lech theo, mot cach nhat
                                             quan nen khong ai phat hien.

    ⭐ Va mot cho da PHAI sua hai lan, dang ghi lai vi day la ranh gioi tinh te:
       ban dau `gpu_check.py` giu mot nhanh du phong *"khong biet UUID thi van doc
       `dong[0]`, kem co `loc_theo_card: False`"*. Bo do nay — mot luat AST tho —
       van do, va no dung: mot con so VRAM **khong quy duoc ve mot card** thi khong
       phai mot phep do, ke ca khi co mot co noi rang no khong biet. Nguoi doc bao
       cao chan doan se trich CON SO, khong trich cai co.

    ⚠️ Nen dung "noi long bo do cho mot cong cu chan doan". Hai muc do fail-closed
       KHAC nhau van duoc phep (`gpu_check` tra `None` kem ly do va van in moi
       truong khac; `chay_baseline` khong lay mau nao), nhung **khong cho nao doc
       dong dau tien**.
    """
    assert _quet_goi("render_gateway") == []


def test_doi_chung_bo_do_TINH_bat_duoc_hinh_dang_cu(tmp_path):
    """Phục hồi đúng bản cũ của `don_dep.doc_vram_dung_mb` ⇒ bộ dò phải ĐỎ."""
    tep = tmp_path / "cu.py"
    tep.write_text(
        "import subprocess\n"
        "def doc_vram_dung_mb():\n"
        "    r = subprocess.run(['nvidia-smi', '--query-gpu=memory.used',\n"
        "                        '--format=csv,noheader,nounits'])\n"
        "    dong = (r.stdout or '').strip().splitlines()\n"
        "    return int(dong[0].strip())\n", encoding="utf-8")
    assert quet_py(tep), "bo do KHONG bat duoc hinh dang cu - no khong do gi ca"


def test_doi_chung_bo_do_bat_duoc_compute_apps_khong_loc(tmp_path):
    tep = tmp_path / "cu2.py"
    tep.write_text(
        "import subprocess\n"
        "def dem():\n"
        "    r = subprocess.run(['nvidia-smi', '--query-compute-apps=process_name',\n"
        "                        '--format=csv,noheader'])\n"
        "    return len(r.stdout.splitlines())\n", encoding="utf-8")
    assert any("compute-apps" in v for v in quet_py(tep))


def test_doi_chung_bo_do_bat_duoc_chia_cot_tren_stdout_tho(tmp_path):
    """Phục hồi bản cũ của `tools/bench_llm_hieu_nang._smi` ⇒ bộ dò phải ĐỎ."""
    tep = tmp_path / "cu3.py"
    tep.write_text(
        "import subprocess\n"
        "def _smi():\n"
        "    r = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu',\n"
        "                        '--format=csv,noheader,nounits'])\n"
        "    v = [x.strip() for x in r.stdout.strip().split(',')]\n"
        "    return {'vram_mb': int(v[0]), 'gpu_pct': int(v[1])}\n", encoding="utf-8")
    assert any("chia-cot" in v for v in quet_py(tep))


def test_bo_do_KHONG_bat_ban_da_sua(tmp_path):
    """Phản chứng cho chính bộ dò: bản đã sửa (lọc theo cột uuid) phải XANH.
    Một bộ dò đỏ với mọi thứ thì nó không nói được gì về cái nó đỏ."""
    tep = tmp_path / "moi.py"
    tep.write_text(
        "import subprocess\n"
        "def doc(uuid):\n"
        "    r = subprocess.run(['nvidia-smi', '--query-gpu=uuid,memory.used',\n"
        "                        '--format=csv,noheader,nounits'])\n"
        "    for d in r.stdout.splitlines():\n"
        "        o = [x.strip() for x in d.split(',')]\n"
        "        if o[0] == uuid:\n"
        "            return int(o[1])\n"
        "    return None\n", encoding="utf-8")
    assert quet_py(tep) == []


# ── 6. `taskkill /im llama-server.exe` — dừng theo tên ảnh là giết CẢ HAI card ─

def _tep_script() -> list[pathlib.Path]:
    ra: list[pathlib.Path] = []
    for duoi in ("*.cmd", "*.ps1", "*.bat"):
        ra += [t for t in (GOC / "llm_gateway").rglob(duoi)
               if "__pycache__" not in t.parts]
    return sorted(ra)


def test_khong_script_nao_TASKKILL_theo_ten_anh_llama_server():
    """⛔ `taskkill /im llama-server.exe` dừng **mọi** engine, kể cả engine của
    card ta không thử — tức giết việc đang chạy của model khác, trong im lặng.

    Dừng theo **PID trên đúng một card** (`python -m llm_gateway.gpu_uuid pid
    <vai>`) thì script dừng đúng thứ nó nói nó dừng.
    """
    xau: dict[str, list[str]] = {}
    for t in _tep_script():
        for i, d in enumerate(t.read_bytes().decode("utf-8", "replace").splitlines(), 1):
            thap = d.strip().lower()
            # ⛔ BỎ QUA DÒNG CHÚ THÍCH. Không bỏ thì bộ dò đỏ vì chính lời giải
            #    thích *"đừng dùng `taskkill /im llama-server.exe`"* — và người
            #    sửa sẽ học cách xoá **lời giải thích** thay vì xoá khuyết tật.
            if thap.startswith(("rem ", "rem\t", "::", "#")):
                continue
            if "taskkill" in thap and "/im" in thap and "llama-server" in thap:
                xau.setdefault(t.name, []).append(f"{i}: {d.strip()}")
    assert not xau, f"con taskkill theo ten anh llama-server: {xau}"


def test_gpu_uuid_co_CLI_cho_script_van_hanh():
    """Script `.cmd` không được nhúng Python inline (quy tắc 3 `CLAUDE.md`), nên
    đường thay thế `taskkill /im` phải là một lệnh module thật."""
    assert GU._main(["x"]) == 2                      # thieu doi so -> bao dung
    assert GU._main(["x", "uuid", "ltt38"]) == 0
    assert GU._main(["x", "uuid", "ltt99"]) == 2


def test_nghiem_thu_doc_VRAM_theo_vai():
    """`deploy/nghiem_thu.py` chạy TRÊN máy B — nó là bộ đo bị lệch card nặng
    nhất, vì kết luận nghiệm thu dựa vào con số nó in ra."""
    van = (GOC / "llm_gateway" / "deploy" / "nghiem_thu.py").read_bytes().decode("utf-8")
    assert "gpu_uuid" in van, "nghiem_thu.py chua doc VRAM theo UUID"
    assert quet_py(GOC / "llm_gateway" / "deploy" / "nghiem_thu.py") == []


def test_bench_llm_hieu_nang_doc_theo_vai():
    """`tools/bench_llm_hieu_nang.py` sinh **ảnh chụp ngữ cảnh** cho mọi con số
    benchmark. Một ảnh chụp của card sai thì số đo mất provenance."""
    t = GOC / "tools" / "bench_llm_hieu_nang.py"
    assert quet_py(t) == []
    assert "gpu_uuid" in t.read_bytes().decode("utf-8")


def test_subprocess_run_van_tiem_duoc():
    """Mọi hàm đo phải nhận `chay=` — không tiêm được thì phép kiểm phải gọi
    `nvidia-smi` thật, và trên máy A thì nó không tồn tại."""
    import inspect
    for ten in ("vram_mib", "vram_trong_mib", "util_pt", "tien_trinh",
                "thay_du_hai_card", "doc_the"):
        ts = inspect.signature(getattr(GU, ten)).parameters
        assert "chay" in ts, f"{ten} khong tiem duoc subprocess.run"
        assert ts["chay"].default is subprocess.run
