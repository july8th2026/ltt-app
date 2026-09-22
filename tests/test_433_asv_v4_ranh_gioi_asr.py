"""Auto Scan Video V4 — ranh gioi ASR va phan vai nguoi noi (pha 07).

Bon tuyen bo, va mot trong so do sua mot loi da song trong kho tu truoc khi Auto
Scan ton tai:

**§1 ranh gioi la BAN KHAI, khong phai duong dan** — ASV chi duoc cham nhung ten
     nam trong `autosubvideo.BE_MAT_CONG_KHAI`, va `tools/lint_app_contract.py`
     cuong che chieu con lai. Pha nay THEM hai ten, khong sua ten nao.

**§2 card do NEN TANG cap** — 🔴 `pyannote_runner.py:20` lam
     `if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))`, tuc no lay
     card dau tien torch thay, **bat ke `gpu_lease` da cap card nao cho ai**. Hai
     job song song thi hoac dam nhau tren mot card, hoac mot card nam khong trong
     khi card kia OOM.

**§3 phan vai la CO DIEU KIEN** — chi `AUTO_MATCH` can bang chung nguoi noi.
     Chay no cho `USER_SELECTED` la tra tien GPU cho mot ket qua khong ai doc.

**§4 nang luc phu hong thi lan chay KHONG hong** — mot ban long tieng thieu nhan
     nguoi noi van la mot ban long tieng.

⛔ Khong phep kiem nao o day nap mot model that. Ca hai ranh gioi deu duoc tiem.
"""
from __future__ import annotations

import ast
import pathlib


from apps.auto_scan_video import ban_ghi, giai_doan_chep_loi as gd

GOC = pathlib.Path(__file__).resolve().parents[1]


class _Ctx:
    """`JobContext` gia: chi ba thu ma ranh gioi doc."""

    def __init__(self, *, gpu_uuid="", huy=False):
        self.gpu_uuid = gpu_uuid
        self._huy = huy
        self.tien_do = []

    def progress(self, phan_tram, thong_diep=""):
        self.tien_do.append((phan_tram, thong_diep))

    def is_cancelled(self):
        return self._huy


def _run(che_do=""):
    class R:
        settings = {"che_do_giong": che_do} if che_do else {}
    return R()


def _ban(n=2) -> dict:
    return {"schema": ban_ghi.SCHEMA_BAN_GHI,
            "doan": [{"bat": float(i), "ket": float(i + 1), "chu": f"cau {i}",
                      "ma": f"seg_{i + 1:04d}", "tu": []} for i in range(n)]}


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Ranh gioi la ban khai — va no duoc cuong che tu CA HAI phia
# ══════════════════════════════════════════════════════════════════════════════

def test_phan_vai_DA_RUT_khoi_be_mat_va_khoi_ASV():
    """⛔ 22/09 (asv-final): MOT giong thuyet minh, khong ai doc `nguoi_noi`.

    Phan vai tung chay pyannote tren GPU o moi lan AUTO_MATCH cho mot ket qua
    bi vut (TRANG_THAI_V6 pha 20). Chot ca hai phia: be mat khong khai, va ASV
    khong goi — mo lai la mot ADR da giong, khong phai mot dong khai lai.
    """
    from apps.autosubvideo import BE_MAT_CONG_KHAI

    assert ("apps.autosubvideo.ai_workflows", "diarize_file") not in BE_MAT_CONG_KHAI
    assert ("apps.autosubvideo.ai_workflows", "assign_speakers") not in BE_MAT_CONG_KHAI
    assert not hasattr(gd, "can_phan_vai") and not hasattr(gd, "phan_vai")
    van = (GOC / "apps/auto_scan_video/giai_doan_chep_loi.py").read_text(encoding="utf-8")
    assert "diarize_file" not in van.split('"""', 2)[2]


def test_linter_cho_phep_dung_HAI_ten_do_va_khong_hon():
    """⛔ Danh sach cho phep phai KHOP be mat cong khai, khong rong hon.

    Mot ten trong danh sach cho phep ma app chu **khong** khai la mot canh voi
    qua rao co giay phep — te hon khong co giay phep, vi no trong nhu hop le.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_lint", GOC / "tools" / "lint_app_contract.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    from apps.autosubvideo import BE_MAT_CONG_KHAI

    duoc = m.APP_DUOC_DUNG_APP[("auto_scan_video", "autosubvideo")]
    thua = duoc - set(BE_MAT_CONG_KHAI)
    assert thua == set(), f"cho phep nhung app chu khong khai: {sorted(thua)}"


def test_ASV_khong_cham_duong_RIENG_nao_cua_app_chu():
    """Chieu khang dinh: quet AST moi `import ... from apps.autosubvideo...`."""
    app = GOC / "apps" / "auto_scan_video"
    from apps.autosubvideo import BE_MAT_CONG_KHAI

    cho_phep = {ten for _mod, ten in BE_MAT_CONG_KHAI}
    xau = []
    for tep in sorted(app.glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if isinstance(n, ast.ImportFrom) and (n.module or "").startswith(
                    "apps.autosubvideo"):
                for a in n.names:
                    if a.name not in cho_phep:
                        xau.append(f"{tep.name}: {n.module}.{a.name}")
    assert xau == [], xau


def test_them_chu_khong_SUA_hop_dong_cua_app_chu():
    """⭐ `diarize_file` van chay duoc voi moi nguoi goi CU.

    `gpu_uuid` co mac dinh `""`, va `""` giu nguyen hanh vi truoc day. Neu ai do
    bo mac dinh di thi `autosubvideo/jobs.py` vo — mot app khac lam hong app chu
    la dung dieu `BE_MAT_CONG_KHAI` sinh ra de chan.
    """
    import inspect

    from apps.autosubvideo.ai_workflows import diarize_file

    ts = inspect.signature(diarize_file).parameters["gpu_uuid"]
    assert ts.default == "", "`gpu_uuid` phai co mac dinh rong"
    assert ts.kind is inspect.Parameter.KEYWORD_ONLY


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Card do NEN TANG cap — khong bao gio tu chon
# ══════════════════════════════════════════════════════════════════════════════

def test_diarize_file_GHIM_moi_truong_vao_card_duoc_cap(monkeypatch):
    """Chot phia app CHU: tien trinh con phai nhan `CUDA_VISIBLE_DEVICES`.

    ⭐ Dung lai `transcription._env_ghim_gpu` (-> `platform_core.gpu.env_for`),
       khong tu dung mot co che thu hai.
    """
    import ast as _ast

    tep = GOC / "apps" / "autosubvideo" / "ai_workflows.py"
    cay = _ast.parse(tep.read_text(encoding="utf-8"))
    ham = [n for n in _ast.walk(cay)
           if isinstance(n, _ast.FunctionDef) and n.name == "diarize_file"][0]
    doan = _ast.get_source_segment(tep.read_text(encoding="utf-8"), ham) or ""
    assert "_env_ghim_gpu(gpu_uuid)" in doan, (
        "Popen cua `diarize_file` phai ghim moi truong vao card duoc cap")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Hop dong ban ghi
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_nang_SCHEMA_BAN_GHI():
    """⛔ `kiem()` so bang DANG THUC. Nang len 2 lam moi ban ghi da luu truot
    kiem — tuc moi lan chay dang do mat cache va khach tra cho mot lan chep loi
    thu hai vi mot thay doi ho khong thay."""
    assert ban_ghi.SCHEMA_BAN_GHI == 1
    cu = _ban()
    ban_ghi.kiem(cu)                      # ban ghi khong co `phan_vai` van hop le


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Nang luc phu hong thi lan chay khong hong — tru khi bi HUY
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  §5  Doi chieu (parity): hinh dang ban ghi khong doi
# ══════════════════════════════════════════════════════════════════════════════

