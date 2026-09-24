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
