"""Khuon nghiem thu dau-cuoi cua ASV phai do SAN PHAM, khong do chinh no.

Hai khiem khuyet lam moi con so cua bao cao `NEN_V3` vo nghia, va ca hai deu
**im lang**: luot chay van XANH, van ra tep dung duoc, chi la nhung con so nó
mang ve noi ve mot thu khac.

    1. Khuon KHONG xin cap card. `JobContext(job.id)` khong co `gpu_uuid`, nen
       `ctx.has_gpu` la False va `ctx.gpu_env()` khong ghim `CUDA_VISIBLE_DEVICES`
       ⇒ demucs va ASR chay tren CPU. Do 23/09: demucs GPU 42,2 s vs CPU 72,0 s.

    2. Khoa `cpu_nhieu` boc CA luot chay. NEN_V3 do `voice_synthesis` 937 s
       tren 1191 s, va gan het so do la mot lan goi HTTP. Giu khoa suot do lam
       ca may doi mot luot dang **cho mang** (su co 23/09: 51 phut o CPU 6-8 %).

⭐ Hai bai duoi day khong can card that va khong cham khoa that. Cai chung do la
   **cach khuon xu su**, va do dung la thu khong tu keu len khi no sai.
"""
from __future__ import annotations

import pytest

from tests.fixtures import asv_e2e as fx


# ══════════════════════════════════════════════════════════════════════════════
#  §1. Khuon phai TRUYEN card vao `JobContext`
# ══════════════════════════════════════════════════════════════════════════════

class _LeaseGia:
    def __init__(self, uuid: str):
        self.id = 1
        self.gpu_uuid = uuid
        self.gpu_index = 0


def test_card_cho_job_truyen_gpu_uuid_KHAC_RONG_khi_co_lease(monkeypatch):
    """`fx.card_cho_job` phai tra ve chinh `lease.gpu_uuid`, khong tra rong.

    Mock o `gpu_lease` — khong can card that. Cai duoc chot la **duong day**:
    lease -> `gpu_uuid` -> nguoi goi -> `JobContext`.
    """
    from platform_core import gpu_lease as gl
    from platform_core import job_runner

    UUID = "GPU-11112222-3333-4444-5555-666677778888"
    da_nha: list[str] = []
    monkeypatch.setattr(gl, "acquire",
                        lambda db, **kw: _LeaseGia(UUID), raising=True)
    monkeypatch.setattr(gl, "release",
                        lambda db, lease: da_nha.append(lease.gpu_uuid),
                        raising=True)
    monkeypatch.setattr(gl, "heartbeat", lambda db, lease: None, raising=True)
    # `_giu_gpu` mo mot phien CSDL that. Bai nay la bai NHE: thay phien bang mot
    # generator rong. (Duong CSDL that duoc `test_448` di qua o luot chay that.)
    monkeypatch.setattr(job_runner, "get_session", lambda: iter([object()]),
                        raising=True)
    # Loai job nay CO khai VRAM (`asv_gpu.transcribe` = 7600 MB), nhung ta khong
    # phu thuoc vao registry o mot bai nhe: ep `_vram_can` tra mot so duong.
    monkeypatch.setattr(job_runner, "_vram_can", lambda jt: 7600, raising=True)

    with fx.card_cho_job("asv_gpu.transcribe", "job-abc") as (uuid, het_gpu):
        assert het_gpu is False
        assert uuid == UUID, "khuon phai nhan chinh gpu_uuid cua lease"

    # ⭐ Va phai NHA. Quen nha thi card khoa toi khi het han mo coi (10 phut),
    #    du de mot chuoi luot nghiem thu lam dung ca hang doi.
    assert da_nha == [UUID], f"lease chua duoc nha: {da_nha}"


def test_JobContext_dung_gpu_uuid_do_thi_has_gpu_va_GHIM_CUDA_VISIBLE_DEVICES():
    """Vi sao `gpu_uuid` rong khong phai mot chi tiet — no doi ca moi truong.

    Day la mat xich giai thich VI SAO §1 quan trong: khong co `gpu_uuid` thi
    `ctx.gpu_env()` khong ghim `CUDA_VISIBLE_DEVICES`, va tien trinh con
    (demucs, ASR) tu chon lay — tren may nay la chon CPU.
    """
    from platform_core.job_runner import JobContext

    UUID = "GPU-11112222-3333-4444-5555-666677778888"
    khong = JobContext("j1")
    co = JobContext("j1", gpu_uuid=UUID)

    assert not khong.has_gpu
    assert co.has_gpu
    assert "CUDA_VISIBLE_DEVICES" not in (khong.gpu_env() or {})
    assert (co.gpu_env() or {}).get("CUDA_VISIBLE_DEVICES") == UUID


def test_khuon_dung_CHINH_vram_can_va_giu_gpu_cua_worker_that():
    """⛔ Khong duoc go lai phep chon card bang mot ban sao.

    Mot ban sao se lech o mot nhanh nao do, va nhanh lech se la nhanh it duoc
    chay nhat. Bai nay chot bang AST: than `card_cho_job` phai goi ten hai ham
    cua `job_runner`, khong tu doc `gpu_lease.acquire`.
    """
    import ast
    import inspect

    than = ast.parse(inspect.getsource(fx.card_cho_job).lstrip())
    ten = {n.id for n in ast.walk(than) if isinstance(n, ast.Name)}
    assert {"_vram_can", "_giu_gpu"} <= ten, sorted(ten)


def test_khai_card_NOI_RA_pha_nao_doi_card_ma_khong_duoc():
    """Bao cao phai phan biet "khong can card" voi "can ma khong duoc"."""
    nhat_ky = [
        {"job_type": "asv_gpu.transcribe", "can_card": True, "gpu_uuid": "GPU-x"},
        {"job_type": "asv_gpu.audio_prepare", "can_card": True, "gpu_uuid": ""},
        {"job_type": "auto_scan_video.advance", "can_card": False, "gpu_uuid": ""},
    ]
    kq = fx.khai_card(nhat_ky)
    assert kq["pha_doi_card"] == ["asv_gpu.audio_prepare", "asv_gpu.transcribe"]
    assert kq["pha_duoc_card"] == ["asv_gpu.transcribe"]
    assert kq["pha_doi_card_ma_KHONG_duoc"] == ["asv_gpu.audio_prepare"]
    # 🔑 MOT PHAN QUYET, khong de nguoi doc tu tru hai danh sach: do la dung cach
    #    bao cao `NEN_V3` mang so CPU ma khong ai nhan ra (K-01).
    assert kq["do_khuon_khong_do_san_pham"] is True
    assert "asv_gpu.audio_prepare" in kq["cau_khai"]
    assert "KHUON" in kq["cau_khai"]
    # ⚠️ Va thu ham nay KHONG biet thi phai noi ra chu khong im.
    assert "CTranslate2" in kq["chua_tra_loi"]


def test_khai_card_moi_pha_DUOC_card_thi_khai_do_SAN_PHAM():
    kq = fx.khai_card([
        {"job_type": "asv_gpu.transcribe", "can_card": True, "gpu_uuid": "GPU-x"},
        {"job_type": "auto_scan_video.advance", "can_card": False, "gpu_uuid": ""},
    ])
    assert kq["do_khuon_khong_do_san_pham"] is False
    assert "SAN PHAM" in kq["cau_khai"]


def test_khai_card_KHONG_pha_nao_doi_card_thi_khong_duoc_khai_la_do_san_pham():
    """⛔ "Khong pha nao doi card" KHAC "moi pha deu duoc card".

    Mot luot khong co pha GPU nao khong noi duoc gi ve hieu nang GPU — va khai no
    la "do san pham" la mot cau dung ve chu, sai ve dieu nguoi doc se hieu.
    """
    kq = fx.khai_card([
        {"job_type": "auto_scan_video.advance", "can_card": False, "gpu_uuid": ""},
    ])
    assert kq["do_khuon_khong_do_san_pham"] is False
    assert "khong noi gi" in kq["cau_khai"]


def test_may_khong_co_card_thi_khuon_DUNG_chu_khong_am_tham_chay_CPU(monkeypatch):
    from platform_core import gpu as gpu_mod

    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [], raising=True)
    with pytest.raises(fx.KhongCoCardError):
        fx.doi_hoi_card()


# ══════════════════════════════════════════════════════════════════════════════
#  §2. Khoa may KHONG duoc boc pha CHO
# ══════════════════════════════════════════════════════════════════════════════

class _CuaSoGia:
    """Ghi lai ai mo/dong khoa nao, va theo thu tu nao."""

    def __init__(self, so_tay: list, tai_nguyen):
        self.so_tay = so_tay
        self.tai_nguyen = tuple(tai_nguyen)

    def __enter__(self):
        self.so_tay.append(("mo", self.tai_nguyen))
        return self

    def __exit__(self, *_exc):
        self.so_tay.append(("dong", self.tai_nguyen))


def _khoa_gia(monkeypatch) -> tuple:
    so_tay: list = []
    khoa = fx.KhoaTheoPha("bai-kiem")
    monkeypatch.setattr(khoa, "_cua_so",
                        lambda tn, lenh: _CuaSoGia(so_tay, (tn,)))
    return khoa, so_tay


def test_pha_CHO_khong_giu_mot_khoa_nao(monkeypatch):
    """`advance`/`edit_plan`/`content_process`/`qc_ai` la lan goi mang.

    🔴 Day la chinh dieu su co 23/09 vi pham: mot lan giu 51 phut o CPU 6-8 %,
       va 6 luot xep hang sau no.
    """
    khoa, so_tay = _khoa_gia(monkeypatch)
    cho = ["auto_scan_video.advance", "auto_scan_video.edit_plan",
           "auto_scan_video.content_process", "auto_scan_video.qc_ai",
           "asv_media.timing_align"]
    with khoa:
        for jt in cho:
            with khoa.quanh_job(jt) as tn:
                assert tn == (), f"{jt} khong duoc giu khoa nao, dang giu {tn}"
    assert so_tay == [], f"pha cho da mo khoa: {so_tay}"


def test_pha_TINH_giu_cpu_nhieu_va_NHA_NGAY_khi_pha_xong(monkeypatch):
    """Khoa boc dung mot job tinh, khong boc sang job ke tiep."""
    khoa, so_tay = _khoa_gia(monkeypatch)
    with khoa:
        with khoa.quanh_job("asv_gpu.audio_prepare") as tn:
            assert tn == ("cpu_nhieu",)
        # Da dong TRUOC khi pha ke tiep bat dau — do la ca diem cua bai nay.
        assert so_tay == [("mo", ("cpu_nhieu",)), ("dong", ("cpu_nhieu",))]
        with khoa.quanh_job("auto_scan_video.content_process") as tn:
            assert tn == ()
        assert so_tay == [("mo", ("cpu_nhieu",)), ("dong", ("cpu_nhieu",))]


def test_moi_job_TINH_mo_roi_dong_mot_lan_khong_gop_qua_pha_cho(monkeypatch):
    """Hai pha tinh cach nhau boi mot pha cho ⇒ HAI lan giu, khong phai mot."""
    khoa, so_tay = _khoa_gia(monkeypatch)
    with khoa:
        for jt in ("asv_gpu.audio_prepare", "auto_scan_video.advance",
                   "asv_media.render"):
            with khoa.quanh_job(jt):
                pass
    assert so_tay == [("mo", ("cpu_nhieu",)), ("dong", ("cpu_nhieu",)),
                      ("mo", ("cpu_nhieu",)), ("dong", ("cpu_nhieu",))]


def test_may_tao_tieng_GIU_SUOT_pha_giong_chu_khong_nha_giua(monkeypatch):
    """⚠️ Khoa tai nguyen DOC QUYEN thi nguoc lai: nha som lam HONG phep do.

    Mot phien chen vao giua pha giong lam so LUFS/MOS cua luot nay mang tieng
    cua luot khac. Nen `may_tao_tieng` mo mot lan va dong o cuoi luot.
    """
    khoa, so_tay = _khoa_gia(monkeypatch)
    with khoa:
        for _ in range(3):
            with khoa.quanh_job("asv_voice.voice_synthesis") as tn:
                assert tn == ("may_tao_tieng",)
        # Ba job giong, nhung chi MOT lan mo va chua dong lan nao.
        assert so_tay == [("mo", ("may_tao_tieng",))]
    assert so_tay == [("mo", ("may_tao_tieng",)), ("dong", ("may_tao_tieng",))]


def test_khong_pha_CHO_nao_nam_trong_PHA_NANG_CPU():
    """Hai tap phai roi nhau — neu khong, mot pha cho se giu `cpu_nhieu`."""
    assert not (fx.PHA_CHO & fx.PHA_NANG_CPU), sorted(fx.PHA_CHO & fx.PHA_NANG_CPU)


def test_PHA_NANG_CPU_chi_chua_job_type_CO_THAT_trong_ban_khai():
    """⛔ Mot ten go sai trong `PHA_NANG_CPU` la mot khoa khong bao gio duoc mo.

    Va no hong IM LANG: luot chay van xanh, chi la pha nang do chay ngoai khoa.
    Nen tap nay phai doi chieu voi `manifest.job_types` that.
    """
    from platform_core.registry import discover

    that: set[str] = set()
    for item in discover():
        if item.error:
            continue
        that |= set(item.manifest.job_types)
    la = (fx.PHA_NANG_CPU | fx.PHA_CHO) - that
    assert not la, f"khong app nao khai cac job_type nay: {sorted(la)}"


def test_vong_lap_worker_cua_khuon_NGU_ngoai_khoi_khoa():
    """⛔ `time.sleep(hoan)` phai nam NGOAI `with khoa.quanh_job(...)`.

    Chot bang AST vi day la mot thuoc tinh cua **cau truc**: mot `sleep` tut vao
    trong khoi `with` khong lam bai nao do, no chi lam ca may doi.
    """
    import ast
    import inspect

    from tests import test_448_asv_v4_e2e_nghiem_thu as t448

    than = ast.parse(inspect.getsource(t448._chay_hang_doi).lstrip())
    KHOA = {"quanh_job", "card_cho_job"}
    trong_with: list[int] = []
    for nut in ast.walk(than):
        if not isinstance(nut, ast.With):
            continue
        co_khoa = any(isinstance(n, ast.Attribute) and n.attr in KHOA
                      for it in nut.items for n in ast.walk(it.context_expr))
        if not co_khoa:
            continue
        for con in nut.body:
            for n in ast.walk(con):
                if isinstance(n, ast.Attribute) and n.attr == "sleep":
                    trong_with.append(getattr(n, "lineno", -1))
    assert not trong_with, (
        f"co `time.sleep` trong khoi giu khoa (dong {trong_with}) — do la "
        f"'giu khoa luc CHO', dung dieu luat 23/09 cam")


# ══════════════════════════════════════════════════════════════════════════════
#  §3. Mot NHAN khong duoc dung lam duong dan, va buoc giu tang vat khong duoc
#      xoa bao cao cua lan chay
# ══════════════════════════════════════════════════════════════════════════════

def test_nhan_co_dau_HAI_CHAM_khong_thanh_mot_O_DIA():
    """Do that 24/09: nhan `B::zh->vi::...` -> `WindowsPath('B::...')`.

    Windows doc `B:` la mot **o dia**, nen `mkdir` nem `[WinError 3] cannot find
    the path specified: 'B:'` — mot thong bao khong nhac mot chu nao den nhan,
    tang vat, hay lan chay.
    """
    from tests.test_448_asv_v4_e2e_nghiem_thu import _ten_an_toan

    ten = _ten_an_toan("B::zh->vi::localize_preserve_picture")
    assert ":" not in ten and ">" not in ten, ten
    # ⛔ Va khong duoc cat ngan: hai luot khac nhau bi cat mat duoi se ghi vao
    #    CUNG mot thu muc, tuc luot sau xoa tang vat cua luot truoc.
    assert _ten_an_toan("A::zh->vi::x") != _ten_an_toan("A::zh->vi::y")
    assert _ten_an_toan("") == "khong_ten"


def test_giu_tang_vat_HONG_thi_bao_cao_van_ve(monkeypatch, tmp_path):
    """⛔ Buoc giu tang vat chi chay khi lan chay ĐÃ hong.

    Tuc no chay dung luc bao cao la thu duy nhat con lai — nen mot loi trong no
    phai duoc GHI VAO bao cao, khong duoc nem ra va mang bao cao di theo.
    """
    import ast
    import inspect

    from tests import test_448_asv_v4_e2e_nghiem_thu as t448

    than = ast.parse(inspect.getsource(t448._mot_luot).lstrip())
    # Tim loi goi `_giu_tang_vat`, va no phai nam trong mot `try`.
    trong_try = []
    for nut in ast.walk(than):
        if not isinstance(nut, ast.Try):
            continue
        for con in nut.body:
            for n in ast.walk(con):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "_giu_tang_vat"):
                    trong_try.append(n)
    assert trong_try, (
        "`_giu_tang_vat` duoc goi NGOAI `try` — mot loi trong buoc giu bang "
        "chung se xoa chinh bao cao cua lan chay hong (do that 24/09)")


# ══════════════════════════════════════════════════════════════════════════════
#  §4. Card duoc CAP khong du — tien trinh con phai chay bang venv CO card
# ══════════════════════════════════════════════════════════════════════════════

def test_tach_nguon_doc_BIEN_GHI_DE_trinh_thong_dich(monkeypatch):
    """`python_tach()` mac dinh la `sys.executable` (production khong doi gi).

    🔴 Do that 24/09, luot B tren phim khach that: nen tang cap card DUNG va tien
       trinh con van nem `ThieuCard` — vi pytest chay bang trinh thong dich test
       (`torch 2.11.0+cpu`, `cuda False`) con venv worker la `2.11.0+cu128`.
    """
    import sys

    from apps.auto_scan_video import tach_tieng

    monkeypatch.delenv(tach_tieng.BIEN_PYTHON_TACH, raising=False)
    assert str(tach_tieng.python_tach()) == sys.executable

    monkeypatch.setenv(tach_tieng.BIEN_PYTHON_TACH, r"C:\x\python.exe")
    assert str(tach_tieng.python_tach()) == r"C:\x\python.exe"


def test_tach_nguon_dung_python_tach_chu_khong_sys_executable():
    """⛔ Chot bang AST: than `tach_nguon` khong duoc go thang `sys.executable`.

    Neu no quay lai `sys.executable` thi bien ghi de thanh mot o CHET — dung ho
    loi G-01 (`nguon_loi` duyet gia tri roi khong dat vao ho so).
    """
    import ast
    import inspect

    from apps.auto_scan_video import tach_tieng

    than = ast.parse(inspect.getsource(tach_tieng.tach_nguon).lstrip())
    goi = {n.func.id for n in ast.walk(than)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "python_tach" in goi, sorted(goi)
    thuoc_tinh = {(n.value.id, n.attr) for n in ast.walk(than)
                  if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    assert ("sys", "executable") not in thuoc_tinh, (
        "`tach_nguon` go thang `sys.executable` — bien ghi de thanh o chet")


def test_khai_python_NOI_RA_rang_duong_ASR_la_cau_hoi_KHAC(monkeypatch):
    """⚠️ Mot bo do khong duoc de nguoi doc suy rong hon pham vi cua no.

    `ghim_python_co_card` chi ghim duong DEMUCS. CTranslate2 mang CUDA rieng —
    do 24/09: tren trinh thong dich test `torch.cuda` False ma
    `ctranslate2.get_cuda_device_count()` tra 1. Nen loi khai phai noi thang rang
    duong ASR khong di qua bien nay.
    """
    khai = fx.ghim_python_co_card(monkeypatch)
    assert "CTranslate2" in khai["chua_tra_loi"]
    assert "KHONG di qua bien nay" in khai["chua_tra_loi"]
    assert set(khai) >= {"python_tach", "da_ghim", "vi_sao", "chua_tra_loi"}


def test_ban_ghi_MOI_luot_khai_trinh_thong_dich_va_nguon_dinh_nghia():
    """⛔ Hai truong nay phai co trong JSON tung luot, khong chi trong ma.

    🔴 **Vi sao truong `trinh_thong_dich_tien_trinh_con` la BAT BUOC.** Tu 24/09
       ton tai mot trang thai truoc day khong co: *card duoc cap, nhung duong
       demucs chay bang mot trinh thong dich KHAC production* (`LTT_ASV_PYTHON_TACH`).
       Nguoi doc sau phai phan biet duoc no voi *do tren dung venv production* —
       hai thu cho cung mot con so giay nhung tra loi hai cau hoi khac nhau.

    ⭐ Chot bang AST chu khong bang mot luot chay that: mot phep kiem doi mot luot
       15 phut de phat hien mot dong bi xoa la mot phep kiem se khong ai chay.
    """
    import ast
    import inspect

    from tests import test_3001_asv_nghiem_thu_cuoi as t3001

    than = ast.parse(inspect.getsource(
        t3001.test_NGHIEM_THU_CUOI_nam_luot_tren_phim_that).lstrip())
    khoa_da_gan = {
        n.slice.value for n in ast.walk(than)
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
        and isinstance(n.slice.value, str)}
    for khoa in ("nguon_dinh_nghia_luot", "trinh_thong_dich_tien_trinh_con",
                 "ma_luot"):
        assert khoa in khoa_da_gan, (
            f"ban ghi tung luot khong con gan `{khoa}` — dieu kien dieu phoi "
            f"24/09: bang chung phai khai ca hai, khong chi nam trong ma")


def test_MOI_cho_ghep_nhan_vao_duong_dan_deu_qua_ten_an_toan():
    """⛔ Quet CA MODULE, khong chot tung cho toi tinh co nhin.

    🔴 **Do that 24/09, hai lan, cach nhau 67 phut.** Ban va dau sua
       `_giu_tang_vat` roi dung o do — trong khi `_mot_luot` cung dat `nhan` vao
       mot ten tep (`ra_{nhan}.mp4`). Lan chay thu hai di HET chuoi, `run.status`
       = `done`, roi chet o dong do voi `OSError [Errno 22]`.

    🔑 Dung ho M-08 da ghi trong `LOI_TONG.md` cua chinh phien nay: *mot ham
       giang bay, NAM nguoi goi, va ban va dau chi cham mot*. Nen phep kiem nay
       hoi *"con cho nao khac khong"* thay vi *"cho toi vua sua co dung khong"* —
       cau thu hai luon xanh sau khi sua, va do la ly do no vo dung.
    """
    import ast
    import inspect

    from tests import test_448_asv_v4_e2e_nghiem_thu as t448

    nguon = inspect.getsource(t448)
    cay = ast.parse(nguon)
    xau: list[str] = []
    for nut in ast.walk(cay):
        # `<gi do> / <bieu thuc co chua ten `nhan`>`
        if not (isinstance(nut, ast.BinOp) and isinstance(nut.op, ast.Div)):
            continue
        ten_phai = {n.id for n in ast.walk(nut.right) if isinstance(n, ast.Name)}
        if "nhan" not in ten_phai:
            continue
        if "_ten_an_toan" not in ten_phai:
            xau.append(f"dong {nut.lineno}: {ast.unparse(nut)}")
    assert not xau, (
        "ghep `nhan` vao duong dan ma khong qua `_ten_an_toan`:\n  "
        + "\n  ".join(xau))


# ══════════════════════════════════════════════════════════════════════════════
#  §5. N-02/N-03 — mot nhan khong duoc noi rong hon phep do, va thu DA DO
#      thi phai hien cho khach
# ══════════════════════════════════════════════════════════════════════════════

def test_co_QC_ky_thuat_khong_duoc_mang_ten_rong():
    """⛔ `qc_dat` da thanh `qc_ky_thuat_dat`, va khong duoc quay lai.

    🔴 T1..T18 chi do KY THUAT (thoi luong, luong, MD5, dinh dBTP, khung den,
       VMAF) — khong doc mot chu nao ve NGHIA ban dich. Nhung `jobs.py` vien dan
       chinh co nay lam ly le giao hang khi het vong sua (*"de QC lam cong gac"*).
       Mot cai ten rong lam cau do doc nhu that. Dung ho `f4c4f064`.
    """
    from apps.auto_scan_video import qc as qc_mod

    tt = qc_mod.tom_tat({"dat": True, "so_muc_hong": 0, "muc_hong": [],
                         "phien_ban": 4})
    assert "qc_ky_thuat_dat" in tt
    assert "qc_dat" not in tt, (
        "`qc_dat` quay lai — mot cai ten rong tren mot phep do hep")


def test_bang_chung_cho_KHACH_phai_hien_so_NGU_NGHIA_va_so_CON_LAI():
    """⛔ N-03: he thong DA do 44/95 va 85 muc con lai roi khong hien.

    Chot bang AST tren `bang_chung_chat_luong`: no phai doc `pipeline.QC_AI` va
    `sua_chua_con_lai`. Mot phep kiem dung du lieu gia se xanh ca khi ham do
    duoc cho mot `outputs` rong, nen cai duoc chot o day la **duong day**.
    """
    import ast
    import inspect

    from apps.auto_scan_video import quan_sat

    nguon = inspect.getsource(quan_sat.bang_chung_chat_luong)
    ten = {n.attr for n in ast.walk(ast.parse(nguon.lstrip()))
           if isinstance(n, ast.Attribute)}
    assert "QC_AI" in ten, "khong doc giai doan `qc_ai` — so 44 van vo hinh"
    assert "sua_chua_con_lai" in nguon, (
        "khong doc so cai `sua_chua_con_lai` — so 85 van vo hinh")
    hang = {n.value for n in ast.walk(ast.parse(nguon.lstrip()))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert {"so_khong_dat", "ngu_nghia", "con_lai"} <= hang, sorted(
        h for h in hang if len(h) < 30)


def test_man_hinh_KHACH_khong_con_cau_noi_SAI_ve_doan_doc_lai():
    """⛔ Cau cu: *"N doan DA DUOC DOC LAI vi chua khop loi"*.

    Sai, va sai ve phia co loi cho ta: `so_giong_khong_dat` la so doan VAN CHUA
    KHOP o lan do CUOI — tuc sau khi da doc lai. Do that luot B: 14 doan, vong
    sua da chay.
    """
    from pathlib import Path

    from apps.auto_scan_video import quan_sat

    tep = (Path(quan_sat.__file__).parent / "templates" / "asv_chi_tiet.html")
    van = tep.read_text(encoding="utf-8")
    assert "đã được đọc lại vì chưa khớp lời" not in van
    assert "chưa khớp lời ở lần đo cuối" in van
    # Va hai con so moi phai co mat tren man hinh, khong chi trong `outputs`.
    assert "bang_chung.ngu_nghia" in van
    assert "bang_chung.con_lai" in van
