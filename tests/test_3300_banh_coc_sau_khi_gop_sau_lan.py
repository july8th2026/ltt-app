"""Ba banh coc TANG sau lan gop 6 lan vao `phien/asv-final` — phep kiem cho
tung KHIEM KHUYET THAT ma banh coc chi vao.

## Vi sao tep nay ton tai

Ba banh coc (`check_mypy`, `check_bo_qua`, `check_silent_except`) deu chi la
**cong dem**. Ha moc thi chung xanh, va cai chung dang chi vao thi o lai. Nen
moi phat hien duoc xu o day phai co MOT phep kiem noi ro hong cai gi — neu
khong thi lan sau khong ai biet vi sao dong ma trong nhu the.

⛔ Tep nay KHONG dem lai ba con so (do la viec cua ba cong cu kia). No chot
   HANH VI o tung cho, de mot lan "don dep" ve sau khong lang le tra lai dung
   cai khiem khuyet vua go.

## Ba hong dang nhat trong lan gop nay

  ① `tools/cua_so_yen.py` co **HAI** `def _in` — hai lan doc lap deu viet mot
    bo vo cp1252 cho cung mot su co 24/09. Python giu ban SAU, nen ban truoc
    la ma chet, va hai docstring khai hai nua cua cung mot su co.
  ② `_metricx/mt5_regression.py` goi `MT5Stack(config, embed_tokens)` — chu ky
    do la cua `transformers` 4.x. Ban cai tren may nay la
    `MT5Stack.__init__(self, config)`, nen dong do nem `TypeError` NGAY LUC
    DUNG model, truoc khi cham vao weights.
  ③ `_ecapa_gioi/ecapa_gioi.py` khai `kernel_size=None, dilation=None` roi
    `math.floor(kernel_size / 2) * dilation` ngay dong sau. Hai mac dinh do
    khong phai mac dinh — chung la mot loi `TypeError` doi nguoi goi.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


# ══════════════════════════════════════════════════════════════════════════════
#  ① cua_so_yen: MOT `_in`, khong phai hai
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_so_yen_chi_co_MOT_def_in():
    """Hai `def _in` trong mot module la mot ban KHONG BAO GIO CHAY.

    ⛔ Khong doc `cua_so_yen._in` roi ket luan: ham lay duoc luon la ban sau, nen
       phep do do KHONG phan biet duoc mot dinh nghia voi hai. Phai dem tren
       AST cua tep.
    """
    cay = ast.parse((GOC / "tools" / "cua_so_yen.py").read_text(encoding="utf-8"))
    ten = [n.name for n in cay.body if isinstance(n, ast.FunctionDef)]
    assert ten.count("_in") == 1, (
        f"co {ten.count('_in')} `def _in` o muc module — ban dau bi ban sau "
        f"che, va hai docstring khai hai nua cua cung mot su co 24/09")


def test_cua_so_yen_in_nhan_NHIEU_phan_nhu_print():
    """Cho goi that (`_in("dang xep hang:", lenh)`) truyen hai doi so.

    Ban `_in(cau: str)` bi go chi nhan MOT — giu no lai thi moi cho goi hai doi
    so la `TypeError` ngay trong dong in NGUOI GIU KHOA.
    """
    from tools import cua_so_yen

    cua_so_yen._in("a", 1, None)          # khong duoc nem


def test_cua_so_yen_in_khong_nem_tren_console_cp1252(monkeypatch):
    """Su co 24/09: `print` nem `UnicodeEncodeError` => luot xep hang CHET.

    Gia lap console that: mot `stdout` khai `encoding="cp1252"` va nem khi gap
    ky tu ngoai bang ma — dung hai thu `_in` phai doi pho.
    """
    import sys

    from tools import cua_so_yen

    class _ConsoleCp1252:
        encoding = "cp1252"

        def __init__(self):
            self.da_ghi: list[str] = []

        def write(self, cau: str) -> int:
            cau.encode(self.encoding)      # nem UnicodeEncodeError nhu console that
            self.da_ghi.append(cau)
            return len(cau)

        def flush(self) -> None:
            pass

    console = _ConsoleCp1252()
    monkeypatch.setattr(sys, "stdout", console)
    cua_so_yen._in("⛔ duong dan tieng Viet:", "D:\\Anh Đẹp\\a.mp4")
    assert console.da_ghi, "khong ghi duoc gi ca"
    assert "?" in "".join(console.da_ghi)   # ky tu ngoai cp1252 -> thay the


# ══════════════════════════════════════════════════════════════════════════════
#  ② MetricX: chu ky `MT5Stack` cua BAN DA CAI, khong cua ban upstream viet cho
# ══════════════════════════════════════════════════════════════════════════════

def test_metricx_KHONG_goi_MT5Stack_voi_hai_doi_so():
    """⭐ Phep do hoi `transformers` DANG CAI, khong hoi mot con so phien ban.

    `MT5ForRegression.__init__` dung `MT5Stack` hai lan. Ban upstream truyen
    `(config, embed_tokens)`; `transformers` 5.x bo tham so thu hai, nen ca hai
    dong do nem `TypeError` TRUOC khi cham vao weights. Va no chi no khi co ai
    chay MetricX THAT — tuc trong `qc-venv`, tuc khong bao gio trong gate.
    """
    transformers = pytest.importorskip("transformers")
    from transformers.models.mt5 import modeling_mt5

    from apps.asv_gpu.do_luong._metricx import mt5_regression as mr

    ts = inspect.signature(modeling_mt5.MT5Stack.__init__).parameters
    nhan = len(ts) - 1              # tru `self`
    # Cho goi cua ta chi truyen MOT doi so, nen no phai vua voi ban da cai.
    assert nhan >= 1, f"transformers {transformers.__version__}: MT5Stack{ts}"

    # ⚠️ **Doc CAY, khong doc VAN BAN.** Ban dau cho nay tim chuoi
    #    `"MT5Stack(config, embed_tokens)"` trong `inspect.getsource(...)` — va
    #    `getsource` tra ve CA DOCSTRING. Chinh docstring cua `_mt5_stack` giai
    #    thich chu ky 4.x bang cach VIET RA loi goi hai tham so, nen phep kiem
    #    bao dong tren doan van giai thich vi sao no khong con o do. Ma da dung
    #    tu dau (`MT5Stack(config)` + `set_input_embeddings`).
    # ⭐ Va ban cay chat hon ban chuoi: no bat ca dang goi bang TU KHOA
    #    (`MT5Stack(config, embed_tokens=emb)`) ma phep so chuoi khong thay.
    than = ast.parse(textwrap.dedent(inspect.getsource(mr._mt5_stack))).body[0]
    goi = [n for n in ast.walk(than)
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "MT5Stack"]
    assert goi, "`_mt5_stack` khong con dung `MT5Stack` — phep kiem dang nhin cho khac"
    for g in goi:
        assert len(g.args) + len(g.keywords) == 1, (
            f"con goi {len(g.args) + len(g.keywords)} doi so — chu ky cua "
            f"transformers {transformers.__version__} la "
            f"MT5Stack{inspect.signature(modeling_mt5.MT5Stack.__init__)}")


def test_metricx_stack_nhan_dung_embedding_da_chia_se():
    """`shared` PHAI la embedding cua ca encoder va decoder — do la thu weights
    da cong bo gia dinh. Mot stack tu tao embedding rieng nap duoc checkpoint
    nhung tra so khac."""
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    import torch.nn as nn
    from transformers.models.mt5.modeling_mt5 import MT5Config

    from apps.asv_gpu.do_luong._metricx import mt5_regression as mr

    cau_hinh = MT5Config(d_model=8, d_ff=16, d_kv=2, num_layers=1,
                         num_decoder_layers=1, num_heads=1, vocab_size=32)
    chia_se = nn.Embedding(cau_hinh.vocab_size, cau_hinh.d_model)
    stack = mr._mt5_stack(cau_hinh, chia_se)
    assert stack.get_input_embeddings() is chia_se


def test_metricx_so_lop_decoder_luon_la_MOT_SO():
    """`config.num_decoder_layers` la `int | None` trong `MT5Config`. `None` di
    vao `range(config.num_layers)` cua `MT5Stack` la mot decoder KHONG CO LOP
    NAO — mot model nap duoc va tra rac."""
    pytest.importorskip("transformers")
    from transformers.models.mt5.modeling_mt5 import MT5Config

    from apps.asv_gpu.do_luong._metricx import mt5_regression as mr

    cau_hinh = MT5Config(num_layers=3)
    cau_hinh.num_decoder_layers = None
    assert mr._so_lop_decoder(cau_hinh) == 3


# ══════════════════════════════════════════════════════════════════════════════
#  ③ ECAPA: hai "mac dinh" khong phai mac dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_ecapa_bottle2neck_khong_khai_mac_dinh_None():
    """`kernel_size=None` roi `math.floor(kernel_size / 2)` ngay dong sau.

    ⛔ Khong sua bang `if kernel_size is None: kernel_size = 3` — mot mac dinh
       tu nghi o day la mot lop mang KHAC ban da cong bo, tuc weights nap vao
       sai. Hai tham so nay BAT BUOC; chu ky phai noi the.
    """
    pytest.importorskip("torch")
    from apps.asv_gpu.do_luong._ecapa_gioi.ecapa_gioi import Bottle2neck

    ts = inspect.signature(Bottle2neck.__init__).parameters
    for ten in ("kernel_size", "dilation"):
        assert ts[ten].default is inspect.Parameter.empty, (
            f"{ten} van co mac dinh {ts[ten].default!r} — mot nguoi goi tin vao "
            f"mac dinh do nhan `TypeError` o `math.floor(None / 2)`")


# ══════════════════════════════════════════════════════════════════════════════
#  Nuot loi lang le — moi cho duoi day tra loi mot cau: "nguoi doc ket qua
#  phan biet duoc 'khong co' voi 'khong do duoc' khong?"
# ══════════════════════════════════════════════════════════════════════════════

def test_f0_tu_giai_doan_KHONG_bien_loi_CSDL_thanh_khong_do_duoc():
    """`giai_doan_theo_ten` da tra `None` khi khong co giai doan — nen mot ngoai
    le o day CHI co the la CSDL hong. Bien no thanh `0.0` la khai
    "khong do duoc F0" trong khi su that la "khong doc duoc CSDL", va
    `AUTO_MATCH` mat mat `gioi` ma khong ai biet vi sao."""
    from apps.auto_scan_video import ho_so_noi_dung

    class _Run:
        id = "r1"

    def _no(db, rid, ten):
        raise RuntimeError("connection reset")

    import apps.auto_scan_video.features as features
    goc = features.giai_doan_theo_ten
    features.giai_doan_theo_ten = _no
    try:
        with pytest.raises(RuntimeError, match="connection reset"):
            ho_so_noi_dung.f0_tu_giai_doan(None, _Run())
    finally:
        features.giai_doan_theo_ten = goc


def test_cao_do_noi_RO_vi_sao_khong_do_duoc():
    """Fail-soft la dung (xem `cao_do` docstring), nhung LY DO khong duoc mat:
    `0.0` vi tep hong va `0.0` vi thieu `torchaudio` la hai chuyen khac nhau, va
    chi mot trong hai la viec cua nguoi van hanh."""
    from apps.auto_scan_video import cao_do

    f0, ly_do = cao_do.f0_trung_vi_va_ly_do("C:/khong-he-co-tep-nay.wav")
    assert f0 == 0.0
    assert ly_do and ly_do != "", "tra 0.0 ma khong noi vi sao"
    # Khong duoc la mot chuoi chung chung: phai mang TEN LOAI ngoai le.
    assert ":" in ly_do, ly_do


def test_runner_bao_cao_PHAN_BIET_khong_co_card_voi_khong_do_duoc(monkeypatch):
    """`ket()` bo han khoa `vram_torch_dinh_mb` khi phep do VRAM no. Nguoi doc
    bao cao khong phan biet duoc "may khong co card" voi "phep do VRAM no" — va
    `test_450::test_VRAM_dinh_KHONG_vuot_con_so_app_dang_khai` doc dung khoa do.
    """
    pytest.importorskip("torch")
    import torch

    from apps.asv_gpu.do_luong import _runner

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved",
                        lambda *a, **kw: (_ for _ in ()).throw(
                            RuntimeError("CUDA driver version is insufficient")))
    ra = _runner.DongHo().ket()
    assert "vram_torch_dinh_mb" not in ra
    assert "insufficient" in str(ra.get("vram_ly_do", "")), ra


def test_runner_KHONG_khai_vram_ly_do_khi_may_that_su_khong_co_card(monkeypatch):
    """Doi chung cho phep kiem tren: `torch` vang la mot cau tra loi BINH
    THUONG tren cay `torch+cpu`, khong phai mot loi can bao."""
    pytest.importorskip("torch")
    import torch

    from apps.asv_gpu.do_luong import _runner

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    ra = _runner.DongHo().ket()
    assert "vram_torch_dinh_mb" not in ra and "vram_ly_do" not in ra, ra


def test_dich_kha_dung_KHONG_tra_loi_KHONG_khi_CSDL_hong():
    """Giao dien doc co nay de AN nut dich. CSDL hong => `False` => khach thay
    mot tinh nang DA TRA TIEN bien mat, va khong log nao noi vi sao."""
    from apps.autosubvideo import ai_workflows

    class _DB:
        def query(self, *a, **kw):
            raise RuntimeError("db down")

    with pytest.raises(RuntimeError, match="db down"):
        ai_workflows.dich_kha_dung(_DB())


def test_build_release_KHONG_dan_nhan_0_0_0_lang_le(monkeypatch):
    """Mot ban phat hanh mang phien ban `0.0.0` vi mot `ImportError` la mot ban
    khong truy nguyen duoc — va no chi lo ra o may khach, sau khi da cap nhat."""
    import sys

    import tools.build_release as br

    assert br._version() == "1.0.0"          # doi chung: duong that con song
    monkeypatch.setitem(sys.modules, "version", None)
    with pytest.raises(Exception) as loi:    # noqa: B017 — ImportError hoac con
        br._version()
    assert "0.0.0" not in str(loi.value)


def test_do_llm_cong_asv_noi_RO_khi_khong_doc_duoc_cua_so():
    """Cot `cua so` bang `0` vi khong doc duoc la mot bao cao SAI: `0` la mot
    con so HOP LE trong cot do (mot thao tac khong gioi han ngu canh)."""
    from tools import do_llm_cong_asv as d

    class _AiHong:
        @staticmethod
        def cua_so_ngu_canh(t):
            raise KeyError("thao_tac la")

    class _AiTot:
        @staticmethod
        def cua_so_ngu_canh(t):
            return 0

    assert d._cua_so_hoac_loi(_AiTot(), None) == 0          # `0` THAT
    assert d._cua_so_hoac_loi(_AiHong(), None) == "<KeyError>"


def test_do_llm_cong_asv_KHONG_cham_base_url_tren_None():
    """`providers.get('ltt_llm')` tra `Provider | None`. Registry chua co
    `ltt_llm` => `AttributeError` tho giua mot cong cu do luong."""
    from tools import do_llm_cong_asv as d

    class _Rong:
        @staticmethod
        def get(ten):
            return None

    class _Co:
        @staticmethod
        def get(ten):
            return type("P", (), {"base_url": "http://b:8000/"})()

    assert d._base_url_ltt_llm(_Co()) == "http://b:8000"
    with pytest.raises(SystemExit, match="ltt_llm"):
        d._base_url_ltt_llm(_Rong())
