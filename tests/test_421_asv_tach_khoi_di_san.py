"""Pha 19 — Auto Scan dung ENGINE dung lai duoc, nhung KHONG dung dieu phoi cu.

## Vi sao phai truy do thi, khong doc bang mat

Cau hoi cua Prompt 19 la: *"co duong nao tu submit di toi Sheet polling / Drive
lam hang doi / vong worker cua bot / may trang thai cuc bo cua bot / khoa GPU di
san khong?"*

Doc tung tep khong tra loi duoc cau do. Mot phu thuoc di san khong bao gio nam o
dong dau tep — no nam sau ba lop import, va no vao kho vi ai do goi mot ham
tien tay. Nen phep kiem o day **dong kin theo import** tu diem vao that, roi hoi
tap dong kin do co giao voi danh sach cam khong.

⭐ Va no truy tu **diem vao that**: `apps/auto_scan_video/jobs.py` (job dieu
   phoi) cong `thi_hanh.chay_theo_job_type` (cua vao cua ca ba executor). Do la
   hai duong duy nhat nen tang goi vao Auto Scan.

## Gioi han cua phep kiem nay, noi ro chu khong giau

⛔ Phep dong kin theo import **khong** thay ba thu:

  * `importlib.import_module(ten_bien)` — import dong theo mot chuoi tinh ra
    luc chay;
  * `subprocess` goi mot tien trinh khac (ta co goi ffmpeg/demucs — chung la
    **cong cu**, khong phai dieu phoi);
  * mot goi ben thu ba tu import mot thu di san.

Hai cai dau duoc chot rieng ben duoi. Cai thu ba nam ngoai tam va duoc ghi vao
bao cao pha 19 chu khong gia vo la da phu.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
APP = GOC / "apps"

#: Diem vao THAT — hai duong duy nhat nen tang goi vao Auto Scan.
DIEM_VAO = [
    "apps.auto_scan_video.jobs",
    "apps.auto_scan_video.thi_hanh",
    "apps.asv_media.jobs",
    "apps.asv_gpu.jobs",
    "apps.asv_voice.jobs",
]

#: Module DI SAN bi cam. Moi muc ghi ro no la gi, vi mot danh sach ten tran trui
#: se bi lam mong dan boi nhung nguoi khong biet vi sao no o do.
CAM = {
    # Vong worker + hang doi trong tien trinh cua engine cat clip (RISK-00-15).
    # No khong bao gio nhan job cua nen tang, nhung mot lan chay Auto Scan di
    # qua no la mot lan chay **ngoai** so job — khong tinh tien, khong huy duoc,
    # khong thu hoi duoc khi worker chet.
    "cutclipshort.core.job_queue": "hang doi trong tien trinh cua engine di san",
    "cutclipshort.core.pipeline": "may trang thai cuc bo cua bot",
    # Kho FB/TikTok cu. Da go 25/08 (Q108) nhung ten van con trong lich su va
    # trong mot so import chet — chot de no khong quay lai.
    "core": "kho dieu phoi FB/TikTok da dong bang",
    "utils": "tien ich cua kho cu",
    "server.services": "tang dich vu cua app da go",
}

#: Goi ben ngoai bi cam: chung la **dieu phoi**, khong phai engine.
GOI_CAM = {
    "gspread": "Sheet lam hang doi",
    "googleapiclient": "Drive/Sheets lam hang doi",
    "google.oauth2": "OAuth cua bot di san",
    "pydrive": "Drive lam hang doi",
    "schedule": "vong lap dinh ky cua bot",
    "apscheduler": "bo lap lich thu hai",
}


def _module_cua(ten: str) -> pathlib.Path | None:
    p = GOC / (ten.replace(".", "/") + ".py")
    if p.is_file():
        return p
    p = GOC / ten.replace(".", "/") / "__init__.py"
    return p if p.is_file() else None


def _import_trong(tep: pathlib.Path) -> set[str]:
    """Moi ten module ma tep nay import, KE CA import ben trong ham.

    ⚠️ Phai duyet ca than ham (`ast.walk`, khong phai `tree.body`): kho nay dung
       import-ben-trong-ham o khap noi de tranh keo cay module nang vao luc nap.
       Chi doc dau tep se bo sot dung nhung cho de bo sot nhat.
    """
    ra: set[str] = set()
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    goi_cha = tep.relative_to(GOC).as_posix().rsplit("/", 1)[0].replace("/", ".")
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Import):
            ra |= {a.name for a in nut.names}
        elif isinstance(nut, ast.ImportFrom):
            if nut.level:
                # Import tuong doi: `from . import x` / `from .y import z`
                cha = goi_cha
                for _ in range(nut.level - 1):
                    cha = cha.rsplit(".", 1)[0] if "." in cha else cha
                goc_ten = f"{cha}.{nut.module}" if nut.module else cha
                ra.add(goc_ten)
                ra |= {f"{goc_ten}.{a.name}" for a in nut.names}
            elif nut.module:
                ra.add(nut.module)
                ra |= {f"{nut.module}.{a.name}" for a in nut.names}
    return ra


def dong_kin() -> set[str]:
    """Tap dong kin theo import, bat dau tu `DIEM_VAO`.

    Chi di theo module NAM TRONG KHO — module cua thu vien ngoai duoc ghi lai
    nhung khong duyet tiep (ta khong so huu chung, va `GOI_CAM` chot rieng).
    """
    thay: set[str] = set()
    hang = list(DIEM_VAO)
    while hang:
        ten = hang.pop()
        if ten in thay:
            continue
        thay.add(ten)
        tep = _module_cua(ten)
        if tep is None:
            continue          # thu vien ngoai, hoac mot ten tro toi ham/lop
        for con in _import_trong(tep):
            if con not in thay:
                hang.append(con)
    return thay


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Do thi goi — khong duong nao cham dieu phoi di san
# ══════════════════════════════════════════════════════════════════════════════

def test_do_thi_goi_KHONG_RONG():
    """Chot chinh phep kiem truoc khi tin ket luan cua no.

    ⛔ Neu `dong_kin()` tra ve mot tap be ti (vd vi doi ten module), moi phep
       kiem duoi day se xanh **mot cach rong tuech**. Day la cho chan dieu do.
    """
    tap = dong_kin()
    assert len(tap) > 60, f"do thi chi co {len(tap)} nut — nghi phep truy hong"
    # Phai thay duoc nhung module ta BIET la co trong duong chay.
    for phai_co in ("apps.auto_scan_video.giai_doan_ket_xuat",
                    "apps.auto_scan_video.qc",
                    "apps.auto_scan_video.tach_tieng",
                    "platform_core.jobs"):
        assert phai_co in tap, f"do thi thieu {phai_co} — phep truy chua den noi"


@pytest.mark.parametrize("ten,ly_do", sorted(CAM.items()))
def test_khong_duong_nao_toi_module_di_san(ten, ly_do):
    tap = dong_kin()
    cham = sorted(x for x in tap if x == ten or x.startswith(ten + "."))
    assert cham == [], f"Auto Scan cham {ly_do} qua: {cham}"


@pytest.mark.parametrize("goi,ly_do", sorted(GOI_CAM.items()))
def test_khong_duong_nao_toi_goi_dieu_phoi_ngoai(goi, ly_do):
    tap = dong_kin()
    cham = sorted(x for x in tap if x == goi or x.startswith(goi + "."))
    assert cham == [], f"Auto Scan cham {ly_do} qua: {cham}"


def test_khong_import_DONG_theo_ten_tinh_luc_chay():
    """Lo hong duy nhat cua phep dong kin theo import.

    `importlib.import_module(bien)` di qua moi phep quet tinh. Ta khong cam
    `importlib` (nen tang co the dung), ta cam **goi no voi mot doi so khong
    phai hang so** — do la thu bien mot phu thuoc thanh vo hinh.
    """
    xau: list[str] = []
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ten = ""
            if isinstance(nut.func, ast.Attribute):
                ten = nut.func.attr
            elif isinstance(nut.func, ast.Name):
                ten = nut.func.id
            if ten in ("import_module", "__import__") and nut.args:
                if not isinstance(nut.args[0], ast.Constant):
                    xau.append(f"{tep.name}:{nut.lineno}")
    assert xau == [], f"import dong theo ten tinh luc chay: {xau}"


def test_KHONG_vong_lap_worker_rieng_trong_app():
    """I1 — Auto Scan khong duoc dung hang doi thu hai.

    Mot `ThreadPoolExecutor`/`ProcessPoolExecutor` trong app nghia la cong viec
    chay **ngoai** so job: khong tinh tien, khong huy duoc, khong thu hoi duoc
    khi worker chet.
    """
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    cam = ("ThreadPoolExecutor", "ProcessPoolExecutor", "multiprocessing",
           "APScheduler", "BackgroundScheduler")
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        vp = _vi_pham(tep.read_text(encoding="utf-8"), cam)
        assert vp == [], f"{tep.name} dung hang doi/lich rieng: {vp}"


def test_KHONG_khoa_GPU_di_san():
    """Muc 2. Card do nen tang cap qua lease; mot khoa rieng se dam voi no."""
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    cam = ("gpu_lock", "GPULock", "khoa_gpu", "gpu_arbiter", "current_gpu")
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        vp = _vi_pham(tep.read_text(encoding="utf-8"), cam)
        assert vp == [], f"{tep.name} cham khoa GPU di san: {vp}"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Tien trinh con: la CONG CU, khong phai dieu phoi
# ══════════════════════════════════════════════════════════════════════════════

#: Tien trinh con Auto Scan duoc phep goi. Chot bang TAP HOP: them mot cai moi
#: ma khong khai o day se lam do, va do la dieu ta muon — mot tien trinh con la
#: mot phu thuoc van hanh phai duoc thay.
TIEN_TRINH_CON_CHO_PHEP = {
    "ffmpeg_bin": "ffmpeg — cong cu media",
    "ffprobe_bin": "ffprobe — cong cu media",
    "sys.executable": "chinh python nay, de chay `-m demucs_runner` cach ly",
}


def test_moi_tien_trinh_con_deu_la_CONG_CU_da_khai():
    """⭐ Ranh gioi that cua pha nay khong phai "khong goi tien trinh con" — ta
    goi ffmpeg khap noi. No la: **cong cu thi duoc, dieu phoi thi khong.**

    ffmpeg nhan doi so va tra ve ma thoat. No khong giu trang thai, khong xep
    hang, khong quyet dinh viec gi chay tiep. Mot vong worker thi co ca ba.
    """
    xau: list[str] = []
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            f = nut.func
            ten = f.attr if isinstance(f, ast.Attribute) else (
                f.id if isinstance(f, ast.Name) else "")
            if ten not in ("run", "Popen", "check_output", "call"):
                continue
            # Doi so dau phai la mot danh sach ma phan tu dau la mot cong cu da khai.
            if not nut.args:
                continue
            goc = ast.dump(nut.args[0])
            if not any(k in goc for k in TIEN_TRINH_CON_CHO_PHEP):
                # `cmd` dung san o bien — chap nhan, vi chinh bien do duoc dung
                # tu mot cong cu da khai o ngay tren (co phep kiem rieng cho
                # `dung_lenh`). Chi bao khi doi so la mot chuoi tho.
                if isinstance(nut.args[0], ast.Constant):
                    xau.append(f"{tep.name}:{nut.lineno}")
    assert xau == [], f"tien trinh con chay tu mot chuoi tho: {xau}"


def test_khong_bao_gio_shell_true_o_bat_ky_module_nao():
    """Chot tren CA app, khong chi tren `ket_xuat` nhu pha 15."""
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            if isinstance(nut, ast.keyword) and nut.arg == "shell":
                assert isinstance(nut.value, ast.Constant), (
                    f"{tep.name}:{nut.lineno} `shell=` nhan mot bieu thuc")
                assert not nut.value.value, f"{tep.name}:{nut.lineno} shell=True"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Vo tuong thich phai giu lai (muc 5)
# ══════════════════════════════════════════════════════════════════════════════

#: App KHAC ma Auto Scan goi vao, va **ly do phai giu**. Day la cung sau canh da
#: khai o `test_147::CROSS_APP_ALLOWED`, nhung o day chot mot dieu khac: rang
#: chung la **vo boc engine**, khong phai vo boc dieu phoi.
VO_TUONG_THICH = {
    "apps.ltt_llm": "goi model dich qua `platform_core/llm/dieu_phoi.py`",
    "apps.autosubvideo": "bo chay ASR (`transcription.transcribe_file`)",
    "apps.ltt_voice": "chuan hoa van ban + may sinh tieng",
}


@pytest.mark.parametrize("goi,ly_do", sorted(VO_TUONG_THICH.items()))
def test_vo_tuong_thich_chi_boc_ENGINE_khong_boc_dieu_phoi(goi, ly_do):
    """⛔ Goi mot ham engine cua app khac la mot mon no (RISK-14-01). Goi **hang
    doi** hay **may trang thai** cua no la mot thu khac han: no bien mot lan
    chay Auto Scan thanh mot lan chay cua app kia, voi tien va vong doi cua app
    kia.
    """
    tap = dong_kin()
    cham = {x for x in tap if x.startswith(goi + ".")}
    assert cham, f"khong thay canh nao toi {goi} — bang VO_TUONG_THICH da cu"

    # ── Bac cau: cam DIEU PHOI, cho phep du lieu ────────────────────────────
    #
    # ⚠️ Ban dau cho nay cam ca `.tables` trong tap DONG KIN, va no do — vi
    #    `ltt_voice.features.giai_giong` (ham ta co y goi) tat nhien doc bang
    #    cua chinh no. Luat do qua tho: no cam mot dich vu lam dung viec cua no.
    #
    # ⇒ Bac cau chi cam `.jobs` / `.routes`: cham vao chung nghia la mot lan
    #   chay Auto Scan tro thanh mot lan chay cua app kia, voi tien va vong doi
    #   cua app kia.
    #
    # ⚠️ `.manifest` da tung nam trong danh sach nay va bi go o pha 20, vi cung
    #    ly do da go `.tables` o pha 19: `ltt_voice.doc_man_api.ma_giong_cua_toi`
    #    (ham ta CO Y goi de lay danh sach giong) doc manifest cua chinh no. Cam
    #    bac cau la cam mot dich vu tu mo ta minh.
    #
    # ⭐ Ranh gioi that: `.jobs`/`.routes` la **dieu phoi**; `.manifest`/`.tables`
    #    la **khai bao va du lieu**. Import THANG hai cai sau van bi cam (phep
    #    kiem ngay duoi), vi luc do ta doc gia va job_type cua app khac de tu
    #    quyet dinh — chu khong phai de ho tu quyet dinh.
    xau = sorted(x for x in cham
                 if any(k in x for k in (".jobs", ".routes")))
    assert xau == [], (
        f"Auto Scan cham vao dieu phoi/vong doi cua {goi}: {xau} — chi duoc "
        f"goi ham engine ({ly_do})")


@pytest.mark.parametrize("goi,ly_do", sorted(VO_TUONG_THICH.items()))
def test_KHONG_import_THANG_bang_hay_ban_khai_cua_app_khac(goi, ly_do):
    """Chieu con lai, va day moi la chieu nguy hiem.

    Cham `ltt_voice.tables` **bac cau** qua `giai_giong` la binh thuong — do la
    dich vu do doc bang cua chinh no. Import THANG bang do vao Auto Scan roi tu
    truy van la **di vong qua phep kiem quyen so huu** ma `giai_giong` la noi
    duy nhat thuc hien (I6/I7).

    ⭐ Hai truong hop trong giong het nhau trong mot phep quet phu thuoc, nhung
       mot cai la dung hop dong con cai kia la mo duong dung giong cua nguoi
       khac. Phan biet chung bang **ai import**, khong bang **cai gi bi cham**.
    """
    xau: list[str] = []
    for tep in sorted((APP / "auto_scan_video").glob("*.py")):
        for ten in _import_trong(tep):
            if ten.startswith(goi + ".tables") or ten.startswith(goi + ".manifest"):
                xau.append(f"{tep.name} -> {ten}")
    assert xau == [], (
        f"Auto Scan import THANG bang/ban khai cua {goi}: {xau} — bang phai di "
        f"qua ham dich vu de phep kiem quyen so huu duoc chay, va ban khai la "
        f"gia + job_type cua ho, khong phai thu ta duoc tu doc de quyet dinh")


def test_bang_VO_TUONG_THICH_khop_voi_CROSS_APP_ALLOWED():
    """Hai sổ khai cùng một sự thật; lệch nhau là một trong hai đã cũ."""
    from tests.test_147_layering import CROSS_APP_ALLOWED

    tu_147 = {f"apps.{b}" for a, b in CROSS_APP_ALLOWED
              if a == "auto_scan_video"}
    assert tu_147 == set(VO_TUONG_THICH), (
        f"lech: chi o test_147 {tu_147 - set(VO_TUONG_THICH)}, "
        f"chi o day {set(VO_TUONG_THICH) - tu_147}")
