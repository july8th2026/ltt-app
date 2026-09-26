"""ASV final — so dang ky bo do (`apps/asv_gpu/do_luong/bo_do.py`).

Chot: (1) thieu venv/model ⇒ `khong_kha_dung`, KHONG lui ve cong thuc tu che;
(2) mot bo do hong khong keo bo khac; (3) bo do dich cua lan "dich" cam vao
bang MOT module `do_luong/metricx.py` voi hop dong da hen; (4) phien ban tung bo
do vao van tay.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import types

import pytest

from apps.asv_gpu.do_luong import bo_do, venv


def _dv(**kw):
    base = dict(doan_tieng=[{"ma": "s1", "tep": "x.wav", "chu": "xin chào"}],
                cap_dich=[{"ma": "s1", "nguon": "你好", "dich": "xin chào"}],
                ngon_ngu_nguon="zh", ngon_ngu_dich="vi")
    base.update(kw)
    return bo_do.DauVao(**base)


def test_thieu_qc_venv_thi_KHONG_KHA_DUNG_khong_lui(monkeypatch, tmp_path):
    monkeypatch.setenv("LTT_QC_PYTHON", str(tmp_path / "khong-co" / "python.exe"))
    monkeypatch.delitem(sys.modules, "apps.asv_gpu.do_luong.metricx", raising=False)
    kq = bo_do.chay_tat_ca(_dv())
    assert set(kq) == {b.ten for b in bo_do.BO_DO}
    for ten, r in kq.items():
        assert r["trang_thai"] == bo_do.KHONG_KHA_DUNG, (ten, r)
        assert r["ket_qua"] == {}


def test_mot_bo_do_LOI_khong_keo_bo_khac(monkeypatch):
    def hong(dv, **kw):
        raise venv.DoLuongLoi("thoat 1: CUDA OOM")

    def tot(dv, **kw):
        return {"ket_qua": {"s1": {"stoi": 0.9}}, "tai_nguyen": {"giay_tuong": 1}}

    monkeypatch.setattr(bo_do, "BO_DO", (bo_do.BoDo("a", "1", hong),
                                          bo_do.BoDo("b", "1", tot)))
    kq = bo_do.chay_tat_ca(_dv())
    assert kq["a"]["trang_thai"] == bo_do.LOI and "OOM" in kq["a"]["ly_do"]
    assert kq["b"]["trang_thai"] == bo_do.XONG
    assert kq["b"]["ket_qua"] == {"s1": {"stoi": 0.9}}


def test_huy_giua_chung_thi_NEM_khong_ghi_nhu_loi():
    with pytest.raises(venv.DoLuongLoi):
        bo_do.chay_tat_ca(_dv(), is_cancelled=lambda: True)


def test_khong_co_du_lieu_thi_khong_goi_bo_do(monkeypatch):
    goi = []
    monkeypatch.setattr(bo_do, "BO_DO", (bo_do.BoDo("dich", "1",
                                                    lambda dv, **k: goi.append(1)),))
    kq = bo_do.chay_tat_ca(_dv(cap_dich=[]))
    assert not goi and kq["dich"]["trang_thai"] == bo_do.KHONG_KHA_DUNG


def test_CHO_CAM_metricx_mot_module_la_du(monkeypatch):
    """Lan "dich" viet `do_luong/metricx.py` voi `do_dich(cap, nguon, dich, gpu)`.
    Co module ⇒ ket qua vao bao cao, khong sua them dong nao o day."""
    nhan = {}

    # ⛔ Chu ky nay phai giong `metricx.do_dich` THAT: `*` sau `cap`. Mot ban
    #    gia de dai hon ham that lam phep kiem xanh trong khi cho noi hong.
    def do_dich(cap, *, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid="",
                is_cancelled=None, **_):
        nhan.update(cap=cap, nguon=ngon_ngu_nguon, dich=ngon_ngu_dich, gpu=gpu_uuid)
        return {"s1": 3.25}

    mod = types.ModuleType("apps.asv_gpu.do_luong.metricx")
    mod.do_dich = do_dich
    monkeypatch.setitem(sys.modules, "apps.asv_gpu.do_luong.metricx", mod)
    import apps.asv_gpu.do_luong as pkg
    monkeypatch.setattr(pkg, "metricx", mod, raising=False)
    monkeypatch.setattr(bo_do, "BO_DO", tuple(b for b in bo_do.BO_DO if b.ten == "dich"))
    kq = bo_do.chay_tat_ca(_dv(), gpu_uuid="GPU-x")
    assert kq["dich"]["trang_thai"] == bo_do.XONG
    assert kq["dich"]["ket_qua"] == {"s1": {"metricx": 3.25}}
    assert nhan == {"cap": _dv().cap_dich, "nguon": "zh", "dich": "vi", "gpu": "GPU-x"}


def test_phien_ban_gom_MOI_bo_do_va_doi_khi_mot_bo_do_doi(monkeypatch):
    cu = bo_do.phien_ban()
    for b in bo_do.BO_DO:
        assert f"{b.ten}:{b.phien_ban}" in cu
    monkeypatch.setattr(bo_do, "BO_DO", bo_do.BO_DO[:1] + (
        bo_do.BoDo(bo_do.BO_DO[1].ten, "khac", bo_do.BO_DO[1].chay),) + bo_do.BO_DO[2:])
    assert bo_do.phien_ban() != cu


def test_squim_weights_GHIM_sha256_va_KHONG_dung_ban_NC():
    from apps.asv_gpu.do_luong import giong, squim
    assert len(squim.SHA256_WEIGHTS) == 64
    assert squim.URL_WEIGHTS.endswith("squim_objective_dns2020.pth")
    nguon = open(squim.__file__, encoding="utf-8").read() + open(
        squim.SCRIPT, encoding="utf-8").read()
    assert "SQUIM_SUBJECTIVE" not in nguon.replace("⛔ `SQUIM_SUBJECTIVE`", "")
    # ASR ghim commit, khong tai ban "main" troi noi.
    for _repo, rev in giong.MODEL_GHIM.values():
        assert len(rev) == 40


def test_model_asr_chua_ghim_thi_KHONG_KHA_DUNG():
    from apps.asv_gpu.do_luong import giong
    with pytest.raises(venv.KhongKhaDung):
        giong.do_giong([], ngon_ngu="vi", model="tiny-khong-ghim")

# ══════════════════════════════════════════════════════════════════════════════
#  Thiếu thư viện trong `qc-venv` phải KÊU LÊN, và kêu đúng LOẠI
# ══════════════════════════════════════════════════════════════════════════════

#: Mọi script chạy **bên trong** `qc-venv` (`venv.chay` gọi chúng như tiến trình
#: con). ⛔ Không đoán theo tên: thiếu một dòng ở đây là im lặng bỏ qua một runner.
#: ⛔ `ocr_khung.py` đã rút 26/09 (Task 21): đường OCR hardsub bỏ, một đường
#: duy nhất voice→voice. Nó là runner duy nhất ⛔ KHÔNG mang đuôi `_runner.py`,
#: nên nó cũng biến khỏi phép `| {"ocr_khung.py"}` ngay dưới.
RUNNER = ("gioi_runner.py", "giong_runner.py", "squim_runner.py",
          "_metricx/chay.py")

_GOC_DO = pathlib.Path(venv.__file__).parent


def test_MOI_runner_qc_venv_deu_co_mat_trong_bang():
    """⛔ Một bảng quét-tất-cả thiếu một dòng vẫn XANH — chỉ là nó quét ít hơn."""
    # ⚠️ `_runner.py` KHONG phai mot runner — no la GIAO THUC dung chung
    #    (`mo()`, `ghi()`, `khong_kha_dung()`) ma cac runner goi. Bo no ra la co
    #    y, va ghi ra day de lan sau khong ai "sua" bang cach them no vao bang.
    that = {p.name for p in _GOC_DO.glob("*_runner.py")
            if p.name != "_runner.py"}
    khai = {pathlib.PurePosixPath(r).name for r in RUNNER}
    assert that <= khai, f"runner chua khai trong RUNNER: {sorted(that - khai)}"
    for r in RUNNER:
        assert (_GOC_DO / r).is_file(), r


def _bat_loi_nhap(duong: pathlib.Path) -> list[ast.ExceptHandler]:
    """Các nhánh `except` THẬT SỰ bắt `ImportError`/`ModuleNotFoundError`.

    ⚠️ **Đọc CÂY, ⛔ không đọc VĂN BẢN — và bản đầu của chính bài này đã sai
       đúng chỗ đó (N-24).** Nó hỏi `"ImportError" in ma`, nên nó khớp với
       **chú thích** giải thích luật, và phép tiêm gỡ nhánh `except` thật vẫn
       cho XANH. Một phép kiểm chỉ chứng minh được rằng nó *chưa đỏ*.
    """
    ten_bat = {"ImportError", "ModuleNotFoundError"}
    ra = []
    for n in ast.walk(ast.parse(duong.read_text(encoding="utf-8"))):
        if not isinstance(n, ast.ExceptHandler) or n.type is None:
            continue
        loai = n.type.elts if isinstance(n.type, ast.Tuple) else [n.type]
        if any(getattr(t, "id", "") in ten_bat for t in loai):
            ra.append(n)
    return ra


def _phat_dau_khong_kha_dung(h: ast.ExceptHandler) -> bool:
    """Thân CỦA CHÍNH nhánh đó có phát dấu `KHONG_KHA_DUNG` không.

    ⭐ Hỏi trong thân nhánh, ⛔ không hỏi cả tệp: `squim_runner` gọi
       `khong_kha_dung` ở **ba** chỗ khác nhau, nên một phép đếm mức TỆP vẫn
       xanh sau khi nhánh bắt lỗi nhập bị gỡ răng.

    Hai cách hợp lệ, cả hai đều có thật: gọi `_runner.khong_kha_dung(...)`, hoặc
    `print` một chuỗi mang dấu — đường của `_metricx/chay.py`, tệp chạy độc lập
    trong `qc-venv` nên ⛔ không nhập được `_runner`.
    """
    for n in ast.walk(h):
        if isinstance(n, ast.Call):
            goi = getattr(n.func, "attr", "") or getattr(n.func, "id", "")
            if goi == "khong_kha_dung":
                return True
        if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                and "KHONG_KHA_DUNG" in n.value):
            return True
    return False


@pytest.mark.parametrize("ten", RUNNER)
def test_thieu_thu_vien_trong_qc_venv_ra_KHONG_KHA_DUNG_chu_khong_phai_LOI(ten):
    """🔴 **„Cài đặt thiếu“ và „bộ đo chạy mà hỏng“ là HAI LOẠI, ⛔ đừng gộp.**

    `qc-venv` là một venv RIÊNG (`C:\\LTTPlatform\\qc-venv`), dựng bằng
    `setup/cai_qc_models.ps1`. Một gói vắng ở đó ⇒ `ModuleNotFoundError` trong
    **tiến trình con**. Giao thức của `venv.chay` là: log có dấu `KHONG_KHA_DUNG`
    ⇒ `KhongKhaDung` ⇒ báo cáo ghi `trang_thai: "khong_kha_dung"` kèm `ly_do`.
    ⛔ Không có dấu đó thì cùng sự việc rơi vào `DoLuongLoi` ⇒ `"loi"`.

    ⚠️ Cả hai đều ĐƯỢC GHI (⛔ không im lặng — `bo_do.chay_tat_ca` bắt cả hai),
       nên đây **không** phải lỗi mất tín hiệu. Nó là lỗi **PHÂN LOẠI**, và nó
       đắt vì hai loại đó gọi hai người khác nhau: `khong_kha_dung` là việc của
       **người vận hành** (dựng lại venv), `loi` là việc của **người viết mã**.

    🔴 Đo 25/09: bốn runner kia đều phân biệt; riêng `_metricx/chay.py` thì
       không — `_nap()` nhập `torch`/`transformers` muộn và để `ImportError` bay
       lên nguyên vẹn. Sửa tại chỗ, và bài này giữ cho nó không quay lại.
    """
    bat = _bat_loi_nhap(_GOC_DO / ten)
    assert bat, (
        f"{ten}: khong bat loi NHAP nao — mot goi vang se bao cao thanh `loi` "
        "(viec cua nguoi viet ma) thay vi `khong_kha_dung` (viec cua nguoi van hanh)")
    assert any(_phat_dau_khong_kha_dung(h) for h in bat), (
        f"{ten}: co bat loi nhap nhung nhanh xu ly KHONG phat dau "
        "`KHONG_KHA_DUNG` — `venv.chay` se doc no thanh `DoLuongLoi`")
