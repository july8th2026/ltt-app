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

import pytest

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

def test_hai_ten_moi_nam_trong_BE_MAT_CONG_KHAI_cua_app_CHU():
    from apps.autosubvideo import BE_MAT_CONG_KHAI

    assert ("apps.autosubvideo.ai_workflows", "diarize_file") in BE_MAT_CONG_KHAI
    assert ("apps.autosubvideo.ai_workflows", "assign_speakers") in BE_MAT_CONG_KHAI


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

def test_phan_vai_CHUYEN_TIEP_card_cua_JobContext(monkeypatch):
    """🔴 Loi that duoc sua o pha nay.

    Truoc do `pyannote_runner.py:20` lay card dau tien `torch.cuda.is_available()`
    thay, bat ke lease. Phep kiem nay chot rang ASV chuyen tiep dung card duoc
    cap — va chi chuyen tiep, khong tu chon.
    """
    thay = {}

    def _gia(duong, **k):
        thay.update(k)
        return [{"start": 0.0, "end": 1.0, "speaker": "S0"}]

    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarize_file", _gia)
    gd.phan_vai("a.wav", _ban(), ctx=_Ctx(gpu_uuid="GPU-abc"))
    assert thay["gpu_uuid"] == "GPU-abc"


def test_khong_co_ctx_thi_khong_bia_ra_mot_card(monkeypatch):
    """⛔ Khong co lease thi truyen rong — de app chu giu nguyen hanh vi cu.

    Bia ra mot card la tu dieu phoi GPU, dung dieu pha nay cam.
    """
    thay = {}

    def _gia(duong, **k):
        thay.update(k)
        return [{"start": 0.0, "end": 1.0, "speaker": "S0"}]

    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarize_file", _gia)
    gd.phan_vai("a.wav", _ban(), ctx=None)
    assert thay["gpu_uuid"] == ""


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
#  §3  Phan vai la CO DIEU KIEN — khong tra tien GPU mu
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("che_do, mong_doi", [
    ("AUTO_MATCH", True),
    ("USER_SELECTED", False),
    ("", False),
])
def test_chi_AUTO_MATCH_moi_can_bang_chung_nguoi_noi(che_do, mong_doi):
    assert gd.can_phan_vai(_run(che_do)) is mong_doi


def test_mac_dinh_la_KHONG_chay():
    """⚠️ Mot nang luc ton GPU phai duoc XIN, khong duoc tu bat.

    Thiet lap thieu/hong thi lan chay do khong yeu cau no — fail-closed ve phia
    KHONG tieu tien.
    """
    for xau in (None, {}, {"che_do_giong": None}, {"che_do_giong": "LUNG TUNG"}):
        class R:
            settings = xau
        assert gd.can_phan_vai(R()) is False


def test_ban_ghi_KHONG_phan_vai_van_noi_ro_dieu_do():
    """🔑 Ba gia tri tuong minh, khong phai "co truong hay khong co truong".

    Pha 09 phai phan biet **chua chay** voi **da chay ma khong thay ai** — hai
    truong hop nay dan toi hai quyet dinh khac nhau ve AUTO_MATCH.
    """
    b = ban_ghi.danh_dau_phan_vai(_ban(), ban_ghi.PHAN_VAI_KHONG_CHAY)
    assert b["phan_vai"] == "khong_chay"
    assert all("nguoi_noi" not in d for d in b["doan"])

    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.danh_dau_phan_vai(_ban(), "mot gia tri bia ra")


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

def test_phan_vai_khong_kha_dung_thi_DI_TIEP(monkeypatch):
    def _no(*a, **k):
        raise RuntimeError("Pyannote chua duoc cau hinh")

    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarize_file", _no)
    ra = gd.phan_vai("a.wav", _ban(), ctx=_Ctx())
    assert ra["phan_vai"] == ban_ghi.PHAN_VAI_KHONG_KHA_DUNG
    assert len(ra["doan"]) == 2, "khong duoc lam mat doan nao"


def test_HUY_thi_NEM_LEN_chu_khong_nuot_thanh_khong_kha_dung(monkeypatch):
    """⛔ Huy la Y MUON cua nguoi dung, khong phai mot nang luc thieu.

    🔴 Nuot no thanh `khong_kha_dung` se lam vong chay di tiep sau khi khach da
       bam huy — va khach tra tien cho moi giai doan phia sau.
    """
    def _no(*a, **k):
        raise RuntimeError("Tac vu da bi huy.")

    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarize_file", _no)
    with pytest.raises(RuntimeError):
        gd.phan_vai("a.wav", _ban(), ctx=_Ctx(huy=True))


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Doi chieu (parity): hinh dang ban ghi khong doi
# ══════════════════════════════════════════════════════════════════════════════

def test_gan_nguoi_noi_KHONG_doi_bat_ky_truong_nao_khac(monkeypatch):
    """Doi chieu tung truong: chi `nguoi_noi` duoc them, khong gi bi mat."""
    from apps.autosubvideo.ai_workflows import assign_speakers

    truoc = _ban(3)
    sau = ban_ghi.gan_nguoi_noi(
        truoc, [{"start": 0.0, "end": 1.0, "speaker": "S0"}],
        gan=assign_speakers)

    assert len(sau["doan"]) == len(truoc["doan"])
    for a, b in zip(truoc["doan"], sau["doan"]):
        for k in ("bat", "ket", "chu", "ma", "tu"):
            assert a[k] == b[k], f"truong {k} bi doi"
    assert sau["doan"][0].get("nguoi_noi") == "S0"
    # Doan khong chong lan voi luot nao thi KHONG duoc gan bua mot nguoi noi.
    assert "nguoi_noi" not in sau["doan"][2]


def test_ban_ghi_da_phan_vai_van_qua_duoc_kiem():
    """Truong them khong duoc lam ban ghi mat hop le."""
    from apps.autosubvideo.ai_workflows import assign_speakers

    b = ban_ghi.gan_nguoi_noi(
        _ban(2), [{"start": 0.0, "end": 2.0, "speaker": "S0"}],
        gan=assign_speakers)
    ban_ghi.kiem(b)


def test_thuat_toan_chong_lan_o_lai_app_CHU():
    """⛔ Chep lai thuat toan sang ASV se tao ban thu hai cua cung mot quy tac.

    `ban_ghi.gan_nguoi_noi` phai NHAN ham gan tu ngoai vao (`gan=`), khong tu
    tinh chong lan.
    """
    import inspect

    ma = inspect.getsource(ban_ghi.gan_nguoi_noi)
    assert "gan(" in ma, "phai goi ham duoc tiem vao"
    for cam in ("overlap", "chong_lan", "max(0.0", "min(end"):
        assert cam not in ma, f"co ve dang tu tinh chong lan: {cam!r}"
