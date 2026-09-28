"""
check_khai_tran_cpu.py - dem cac CHO GOI mot thu vien tinh toan NANG ma
⛔ KHONG duoc BOC bang mot khai tran CPU that (chu khong chi CO MAT trong
cung tep), va khong cho tang them.

## Vi sao co tep nay (B12 + B13 viec C4, 28/09/2026)

May treo HAI lan trong mot buoi chieu 28/09. Thu pham: `rapidocr-onnxruntime`
(them cung ngay o B10-4) mac dinh an **15,2 / 20 loi** (`onnxruntime` dat
`intra_op_num_threads = 0` = tu chon = so loi vat ly), va ⛔ khong ai khai tran
no. Chi tiet: `docs/auto_scan_video_final/B12_TREO_MAY_VI_OCR_KHONG_KHAI_TRAN.md`.

🔴 Va bai hoc nay DA duoc do 25 ngay truoc, cho `demucs` (03/09: 12 tien
trinh, moi cai 460-984% CPU, vi `demucs_runner` luc do CHUA dat
`torch.set_num_threads`). No da duoc va — nhung CHI cho demucs. ⛔ Khong ai
hoi "con thu vien nao cung mac dinh lay het loi?" ⇒ 28/09 RapidOCR lap lai
dung lop loi.

## 🔴 AST, ⛔ KHONG grep chuoi — va vi sao ban dau toi sai

Ban dau tep nay do "co mat CHUOI `chan_loi(`/`CPU_TRAN_LOI` o DAU TEP" —
tuc chi CO MAT, ⛔ khong chung minh no BOC dung cho goi engine. Sua theo yeu
cau cua nguoi dieu phoi (28/09): mot tep co `import onnxruntime` va
`chan_loi` CUNG co mat ⛔ KHONG chung minh cai sau boc cai truoc — no co the
xanh GIA tren:

  - mot tep goi engine ngoai `with chan_loi():`, ma `chan_loi` chi duoc
    IMPORT hoac dung o mot ham khac;
  - mot tep co `CPU_TRAN_LOI = 6` o dau tep nhung ⛔ khong ai DOC hang so do
    (khong co loi GOI THAT nao dung no);
  - mot tep ma lop boc nam trong mot NHANH CHET.

⇒ Banh coc nay neo vao **CHO DUNG ENGINE / CHO GOI TINH** roi hoi CAU TRUC —
xem `_phan_tich_tep` — chu ⛔ khong dem CHUOI xuat hien o dau do trong tep.

## Ba tang chung minh, tu manh xuong yeu — VA GIOI HAN CUA TUNG TANG

Voi mot loi goi NEO (vd `RapidOCR(...)`, `InferenceSession(...)`,
`WhisperModel(...)`, `YOLO(...)`, `cv2.VideoCapture(...)`,
`whisperx.load_model(...)`, `Pipeline.from_pretrained(...)`, `torch.load(...)`):

  **Tang A (manh nhat, CUNG ham)** — loi goi neo nam TU VUNG BEN TRONG mot
  `with <ham>():` , trong CUNG ham voi no, ma `<ham>` la mot ham DUOC DINH
  NGHIA trong CHINH tep nay, mang `@contextlib.contextmanager`, VA than ham
  do chua it nhat MOT hanh dong khai tran THAT (`_la_khai_tran_node`) — mot
  LOI GOI/PHEP GAN that trong cay, ⛔ khong phai mot chuoi. Day la phep chung
  minh MANH NHAT: no xac nhan ca "co with-block" LAN "with-block do THAT SU
  lam viec khai tran".

  **Tang B (CUNG tep, qua bien ham)** — loi goi neo nam trong mot ham `f`, va
  `f` CO THE DAT TOI duoc tu ben trong mot with-block da xac minh o Tang A,
  qua mot chuoi loi goi HAM-GOI-HAM chi trong PHAM VI mot tep (khong doi
  module). Day la CHO `do_vung_ocr.py` that dung: `with chan_loi():` boc
  `_do_dai_chu_ocr(...)`, ham do goi `_may()`, va `_may()` moi la noi
  `RapidOCR()` duoc dung — ba ham, mot tep, mot with duy nhat o dau chuoi.

  **Tang C (yeu nhat, CO Y HEP)** — khi ⛔ khong tim duoc mot loi goi NEO cu
  the nao trong tep (vd mot lop torch tu viet, khong goi `torch.load`/mot lop
  con `nn.Module` duoc goi qua `__call__`), banh coc CHI doi hoi tep co IT
  NHAT mot hanh dong khai tran THAT o dau do — ⛔ KHONG chung minh duoc no
  boc dung cho tinh toan. 🔴 **Day la mot GIOI HAN CO Y, khong phai mot lo
  hong da vieng kin** — dung cau chu du an chot 25/09 cho V4c (`do_vung.py`):
  "da DO, ⛔ khong doan" nghia la BIET ro cho nao minh KHONG chung minh duoc,
  ⛔ khong gia vo. Neu mot ho CPU that nam duoi Tang C ma bai tiem loi khong
  bat duoc, do la mot gioi han DA KHAI, sua bang cach them mot ANCHOR_GOI moi
  cho hinh dang goi cu the, ⛔ khong phai roi bo AST quay lai grep chuoi.

## Banh coc (ratchet), khong phai 0 ngay

Cung khuon `tools/check_silent_except.py`: so hien tai chot trong
`tools/khai_tran_cpu_baseline.json`. Tang len la FAIL. Giam thi bao va nhac ha
moc.

## ⛔ Vi sao KHONG mien nguyen khoi bon nhom "✅ gian tiep" cua B12 muc 6

`B12_...md` muc 6 liet ke bon nhom coi la da che: `apps/asv_gpu/do_luong/*`
(gpu_lease), `apps/video_assembly/*` (`ToolSpec.admission_resource` + slots),
`apps/autosubvideo/*` va `platform_core/stt/*` (thue GPU). 🔴 Nhung
`B13_PLAN_NAM_HANG_MUC.md` §2.4/§7.3 TU vach ra rang
`apps/video_assembly/services/engine/filters/motion.py` (goi
`cv2.VideoCapture(...)`, ⛔ KHONG khai tran) la mot ho CPU **MOI** — nam
**trong chinh nhom** "video_assembly da duoc che" cua ban ghi B12. Tuc ban
ghi B12 dung cho PHAM VI no da xet luc do, ⛔ khong dung lam mot mien tron cho
CA CAY CON mai mai. ⇒ `NGOAI_LE` o day chi mien TUNG DUONG DAN cu the, moi
dong kem mot LY DO DOC duoc tu ma nguon — dung khuon `NGOAI_LE` cua
`tests/test_428_asv_v4_rao_chan_nang.py`.

🔴 **Mot muc mien THIEU ly do la mot LO IM LANG** — `main()` TU CHOI chay
(khong phai PASS voi 0 vi pham) neu bat ky muc nao trong `NGOAI_LE` thieu ly
do doc duoc (`_xac_thuc_ngoai_le`). Va so muc mien duoc IN NGAY CANH dong
RESULT — kha ca khi PASS — vi mot muc mien dung hom nay co the la mot lo sau
sau tuan, va dong `PASS` mot minh ⛔ khong noi gi ve no (chu du an yeu cau
28/09, dung ly le voi `[BOQUA] N buoc` cua `gate.py` in canh dong RESULT).

    python tools/check_khai_tran_cpu.py            # kiem theo moc
    python tools/check_khai_tran_cpu.py --list      # in tung tep vi pham + mien
    python tools/check_khai_tran_cpu.py --update    # ha moc sau khi da sua
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "khai_tran_cpu_baseline.json"

#: Nhan BUOC — phoi ra day de `gate.py` dang ky Step goi TEN nay, ⛔ khong go
#: lai chuoi rieng o ben do. Dung ly le voi `gate.TRAN_N_GO_TAY`: mot ten/
#: nguong bi chep sang hai noi thi lan doi mot ben quen sua ben kia, va gate
#: se do dung LUC no dang lam nhiem vu bao ve.
TEN_BUOC = "khai tran CPU"

#: Thu muc quet.
SCAN = ("apps", "platform_core", "server", "render_gateway", "llm_gateway",
        "nexus_agent")

#: ⛔ Bo __pycache__ va moi cay worktree cua Claude.
SKIP_PARTS = {"__pycache__", "vendor", "node_modules", ".venv", "venv",
             "dist", "build", ".claude", "worktrees"}

#: Module GOC (phan truoc dau `.` dau tien) danh dau "tep nay CO DUNG thu vien
#: nay o dau do" — dung de quyet dinh CAN kiem nhan nao, ⛔ khong tu no la
#: bang chung vi pham.
THU_VIEN_GOC: dict[str, str] = {
    "onnxruntime": "onnxruntime",
    "torch": "torch",
    "rapidocr_onnxruntime": "rapidocr",
    "rapidocr": "rapidocr",
    "faster_whisper": "faster_whisper",
    "whisperx": "whisperx",
    "pyannote": "pyannote",
    "ultralytics": "ultralytics",
    "cv2": "cv2",
}

#: Ten HAM GOI la dau hieu BO SUNG cho "tep co dung thu vien nay" — bat ca
#: duong import GIAN TIEP ma module goc khong lo ra qua AST import truc tiep.
TEN_GOI_BO_SUNG: dict[str, str] = {
    "InferenceSession": "onnxruntime",
    "WhisperModel": "faster_whisper",
    "YOLO": "ultralytics",
}

#: Ten ham GOI la CHO NEO — noi mot engine duoc DUNG hoac DUNG len. Khac voi
#: `TEN_GOI_BO_SUNG` (chi de biet "co dung"), day la diem se bi kiem CAU TRUC
#: boc (Tang A/B/C).
ANCHOR_GOI: dict[str, str] = {
    "RapidOCR": "rapidocr",
    "InferenceSession": "onnxruntime",
    "WhisperModel": "faster_whisper",
    "YOLO": "ultralytics",
    "VideoCapture": "cv2",
    "load_model": "whisperx",
}

#: Ten ham duoc coi la "khai tran THAT" khi no la MOT LOI GOI (⛔ khong phai
#: mot chuoi o dau do).
DECLARE_GOI = {"set_num_threads", "setNumThreads", "cpu_affinity"}

#: Ngoai le, khai theo TUNG DUONG DAN + LY DO doc duoc tu ma nguon. Them mot
#: dong la mot QUYET DINH, hien trong diff — dung khuon `NGOAI_LE` cua
#: `tests/test_428_asv_v4_rao_chan_nang.py`. Xem docstring dau tep vi sao
#: ⛔ KHONG mien nguyen ca thu muc. 🔴 Moi ly do PHAI dai hon 20 ky tu —
#: `_xac_thuc_ngoai_le` tu choi chay neu thieu (fail-closed).
NGOAI_LE: dict[str, str] = {
    "apps/auto_scan_video/cao_do.py":
        "goi DONG BO tu demucs_runner.main() (duoi `if __name__ == "
        "'__main__'`) — CUNG mot tien trinh voi `torch.set_num_threads(n)` o "
        "demucs_runner.py:324, nen no da mang tran cua tien trinh cha truoc "
        "khi chay. Xem B12 muc 6.",
}


# ══════════════════════════════════════════════════════════════════════════════
#  Cac ham doc AST thuan — khong ghi, khong doc dia ngoai mot tep duoc dua vao
# ══════════════════════════════════════════════════════════════════════════════

def _goc_module(ten: str | None) -> str | None:
    if not ten:
        return None
    return ten.split(".", 1)[0]


def _ten_goi(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _ten_duoc_goi(cay: ast.AST) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            t = _ten_goi(n)
            if t:
                ra.add(t)
    return ra


def _thu_vien_nang_trong_cay(cay: ast.AST) -> set[str]:
    """Nhan cac thu vien NANG duoc IMPORT hoac GOI o dau do trong mot AST.

    Day chi la buoc "CO CAN kiem tep nay khong" — ⛔ khong phai bang chung vi
    pham; bang chung o `_phan_tich_tep`.
    """
    nhan: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            for a in n.names:
                r = _goc_module(a.name)
                if r in THU_VIEN_GOC:
                    nhan.add(THU_VIEN_GOC[r])
        elif isinstance(n, ast.ImportFrom):
            r = _goc_module(n.module)
            if r in THU_VIEN_GOC:
                nhan.add(THU_VIEN_GOC[r])
    for ten, gan_voi in TEN_GOI_BO_SUNG.items():
        if ten in _ten_duoc_goi(cay):
            nhan.add(gan_voi)
    return nhan


def _neo_nhan(call: ast.Call) -> str | None:
    """Loi goi nay co phai mot CHO NEO (dung/dung len mot engine) khong — va
    neo cho thu vien nao."""
    ten = _ten_goi(call)
    if ten in ANCHOR_GOI:
        return ANCHOR_GOI[ten]
    f = call.func
    if ten == "load" and isinstance(f, ast.Attribute) \
            and isinstance(f.value, ast.Name) and f.value.id == "torch":
        return "torch"          # torch.load(...)
    if ten == "from_pretrained" and isinstance(f, ast.Attribute):
        obj = f.value
        if ((isinstance(obj, ast.Name) and obj.id == "Pipeline")
                or (isinstance(obj, ast.Attribute) and obj.attr == "Pipeline")):
            return "pyannote"    # Pipeline.from_pretrained(...)
    return None


def _la_khai_tran_gan(node: ast.AST) -> bool:
    """Phep GAN THAT vao `intra_op_num_threads` hoac
    `os.environ["OMP_NUM_THREADS"]` — mot Assign/AugAssign thuc su, ⛔ khong
    phai mot chuoi trong docstring hay comment."""
    if isinstance(node, ast.Assign):
        muc_tieu = node.targets
    elif isinstance(node, ast.AugAssign):
        muc_tieu = [node.target]
    else:
        return False
    for t in muc_tieu:
        if isinstance(t, ast.Attribute) and t.attr == "intra_op_num_threads":
            return True
        if isinstance(t, ast.Subscript):
            gia_tri = t.value
            if isinstance(gia_tri, ast.Attribute) and gia_tri.attr == "environ":
                chi_so = t.slice
                if isinstance(chi_so, ast.Constant) \
                        and chi_so.value == "OMP_NUM_THREADS":
                    return True
    return False


def _la_khai_tran_setdefault(call: ast.Call) -> bool:
    """`os.environ.setdefault("OMP_NUM_THREADS", ...)`."""
    if _ten_goi(call) != "setdefault" or not call.args:
        return False
    a0 = call.args[0]
    return isinstance(a0, ast.Constant) and a0.value == "OMP_NUM_THREADS"


def _la_khai_tran_node(node: ast.AST) -> bool:
    """Mot HANH DONG khai tran CPU THAT — mot LOI GOI hoac PHEP GAN thuc su
    trong cay, ⛔ khong phai mot chuoi xuat hien o dau do (docstring, ten hang
    so, comment)."""
    if isinstance(node, ast.Call):
        return _ten_goi(node) in DECLARE_GOI or _la_khai_tran_setdefault(node)
    return _la_khai_tran_gan(node)


def _la_contextmanager_decorator(deco: ast.AST) -> bool:
    if isinstance(deco, ast.Name):
        return deco.id == "contextmanager"
    if isinstance(deco, ast.Attribute):
        return deco.attr == "contextmanager"
    return False


def _ham_wrapper(cay: ast.Module) -> set[str]:
    """Ten cac ham dinh nghia TRONG CHINH tep nay, mang
    `@contextlib.contextmanager`, VA than ham chua it nhat mot hanh dong khai
    tran THAT — day la dieu kien de mot `with <ten>():` duoc TIN la mot lop
    boc that (⛔ khong chi vi no TEN la `chan_loi`)."""
    ten: set[str] = set()
    for n in ast.walk(cay):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_la_contextmanager_decorator(d) for d in n.decorator_list):
            continue
        if any(_la_khai_tran_node(x) for x in ast.walk(n)):
            ten.add(n.name)
    return ten


def _gan_cha(cay: ast.AST) -> None:
    for cha in ast.walk(cay):
        for con in ast.iter_child_nodes(cha):
            con._cha = cha  # type: ignore[attr-defined]


def _ham_bao_quanh(node: ast.AST):
    n = getattr(node, "_cha", None)
    while n is not None:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return n
        n = getattr(n, "_cha", None)
    return None


def _trong_with_bao_ve_cung_ham(node: ast.AST, ten_wrapper: set[str]) -> bool:
    """Tang A — `node` nam TU VUNG ben trong mot `with <wrapper>():` , trong
    CUNG ham voi no (dung o bien FunctionDef/Module gan nhat)."""
    n = getattr(node, "_cha", None)
    while n is not None:
        if isinstance(n, ast.With):
            for item in n.items:
                ce = item.context_expr
                if isinstance(ce, ast.Call) and _ten_goi(ce) in ten_wrapper:
                    return True
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            break
        n = getattr(n, "_cha", None)
    return False


def _tap_dat_toi(cay: ast.Module, ten_wrapper: set[str]) -> set[str]:
    """Tang B — ten cac HAM (dinh nghia trong CHINH tep nay) co the DAT TOI
    duoc tu ben trong mot with-block da xac minh (Tang A), mo rong qua than
    ham theo CHUOI GOI, gioi han trong MOT tep."""
    ham_dinh_nghia = {n.name: n for n in ast.walk(cay)
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    goi_ban_dau: set[str] = set()
    for n in ast.walk(cay):
        if not isinstance(n, ast.With):
            continue
        xac_minh = any(
            isinstance(it.context_expr, ast.Call)
            and _ten_goi(it.context_expr) in ten_wrapper
            for it in n.items)
        if not xac_minh:
            continue
        for stmt in n.body:
            goi_ban_dau |= _ten_duoc_goi(stmt)

    dat_toi: set[str] = set()
    hang_doi = list(goi_ban_dau)
    while hang_doi:
        ten = hang_doi.pop()
        if ten in dat_toi:
            continue
        dat_toi.add(ten)
        ham = ham_dinh_nghia.get(ten)
        if ham is None:
            continue
        for ke in _ten_duoc_goi(ham):
            if ke not in dat_toi:
                hang_doi.append(ke)
    return dat_toi


def _co_khai_tran_truoc_do_cung_pham_vi(anchor: ast.Call, ham_bq) -> bool:
    """Tang C (yeu) — trong CUNG pham vi (ham bao quanh; `None` = khong xet
    o cap module) co MOT hanh dong khai tran THAT nam truoc `anchor` theo
    dong. ⚠️ Pham vi bao gom ca than ham long ben trong — mot GIOI HAN DA
    KHAI (xem docstring dau tep, Tang C)."""
    if ham_bq is None:
        return False
    for n in ast.walk(ham_bq):
        if _la_khai_tran_node(n) and getattr(n, "lineno", 10 ** 9) < anchor.lineno:
            return True
    return False


def _phan_tich_tep(nguon: str) -> tuple[list[str], list[str]]:
    """`(nhan_vi_pham, nhan_duoc_chan)` cho MOT tep — nhan la ten thu vien.

    ⛔ KHONG xet `NGOAI_LE` o day — ham nay THUAN, chi doc noi dung tep dua
    vao. `NGOAI_LE` ap dung o tang goi (`quet`).
    """
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return [], []

    neo_theo_nhan: dict[str, list[ast.Call]] = {}
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            nhan = _neo_nhan(n)
            if nhan:
                neo_theo_nhan.setdefault(nhan, []).append(n)

    # ⭐ Mot loi goi NEO tu no la bang chung "co dung thu vien nay" it nhat
    # manh bang mot cau `import` — gop vao `thu_vien_dung` de mot tep goi
    # thang `RapidOCR(...)` (import gian tiep, dong bo, hay chi don gian la
    # mot doan ma toi thieu) van duoc xet, ⛔ khong phu thuoc AST import tim
    # thay dung dang mong doi.
    thu_vien_dung = _thu_vien_nang_trong_cay(cay) | set(neo_theo_nhan)
    if not thu_vien_dung:
        return [], []
    _gan_cha(cay)

    ten_wrapper = _ham_wrapper(cay)
    dat_toi = _tap_dat_toi(cay, ten_wrapper)
    co_khai_tran_o_dau_do = any(_la_khai_tran_node(n) for n in ast.walk(cay))

    vi_pham: set[str] = set()
    chan_duoc: set[str] = set()
    for nhan in thu_vien_dung:
        cac_neo = neo_theo_nhan.get(nhan, [])
        if not cac_neo:
            # Tang C: khong tim duoc CHO NEO cu the cho thu vien nay trong
            # tep — chi doi hoi CO mot hanh dong khai tran that o dau do.
            (chan_duoc if co_khai_tran_o_dau_do else vi_pham).add(nhan)
            continue
        het_duoc_chan = True
        for call in cac_neo:
            ham_bq = _ham_bao_quanh(call)
            duoc_chan = (
                _trong_with_bao_ve_cung_ham(call, ten_wrapper)
                or (ham_bq is not None and ham_bq.name in dat_toi)
                or _co_khai_tran_truoc_do_cung_pham_vi(call, ham_bq))
            if not duoc_chan:
                het_duoc_chan = False
                break
        (chan_duoc if het_duoc_chan else vi_pham).add(nhan)
    return sorted(vi_pham), sorted(chan_duoc)


def _vi_pham_mot_tep(nguon: str, duong: str) -> list[str] | None:
    """Danh sach nhan vi pham cho MOT tep (SAU khi ap `NGOAI_LE`), hoac
    `None` neu sach. `duong` la duong dan POSIX tuong doi voi ROOT."""
    vi_pham, _chan = _phan_tich_tep(nguon)
    if not vi_pham or duong in NGOAI_LE:
        return None
    return vi_pham


def _xac_thuc_ngoai_le() -> list[str]:
    """Duong dan nao trong `NGOAI_LE` THIEU ly do doc duoc (fail-closed)."""
    return sorted(duong for duong, ly_do in NGOAI_LE.items()
                  if not ly_do or len(ly_do.strip()) <= 20)


def quet() -> tuple[list[tuple[str, list[str]]], int, list[tuple[str, list[str]]]]:
    """`(vi_pham, so_tep_da_quet, duoc_mien)`.

    `duoc_mien` = cac tep SE vi pham NEU khong co `NGOAI_LE` — de bao cao so
    muc mien NGAY CANH dong ket qua (chu du an yeu cau 28/09: PASS ⛔ khong
    duoc ⛔ noi gi ve do phu bi mien).
    """
    vi_pham: list[tuple[str, list[str]]] = []
    duoc_mien: list[tuple[str, list[str]]] = []
    so_tep = 0
    for area in SCAN:
        goc = ROOT / area
        if not goc.is_dir():
            continue
        for path in sorted(goc.rglob("*.py")):
            tuong_doi = path.relative_to(ROOT)
            # ⚠️ Loc theo PHAN DUONG DAN TUONG DOI voi ROOT, ⛔ khong phai
            #    `path.parts` (tuyet doi): ROOT co the tu no nam duoi
            #    `.claude/worktrees/<ten>/`, va khi do `path.parts` LUON chua
            #    ".claude"/"worktrees" — quet se tu loai het moi tep.
            if SKIP_PARTS & set(tuong_doi.parts):
                continue
            duong = tuong_doi.as_posix()
            try:
                nguon = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            so_tep += 1
            vp, _chan = _phan_tich_tep(nguon)
            if not vp:
                continue
            (duoc_mien if duong in NGOAI_LE else vi_pham).append((duong, vp))
    return vi_pham, so_tep, duoc_mien


def _moc() -> int:
    """Moc hien hanh, hoac `-1` neu tep moc thieu/hong (FAIL-CLOSED).

    🔴 Co y KHONG tra ve mot moc mac dinh "an toan": mot tep moc bi mat (xoa
    nham, loi dong bo git, ghi hong nua chung) ma van PASS la dung hinh dang
    `l3_lai_bi_chan` fail-OPEN da ghi so — mot then cua chi con song neu MAT
    no la DO, ⛔ khong phai neu con no la PASS.
    """
    try:
        return int(json.loads(BASELINE.read_text(encoding="utf-8"))["max"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return -1


def main() -> int:
    thieu_ly_do = _xac_thuc_ngoai_le()
    if thieu_ly_do:
        for d in thieu_ly_do:
            print(f"  MIEN THIEU LY DO: {d}")
        print("Moi muc trong NGOAI_LE phai co ly do > 20 ky tu doc duoc tu ma")
        print("nguon. Banh coc TU CHOI chay khi thieu — mot muc mien khong ly")
        print("do la mot lo im lang.")
        print("RESULT: FAIL")
        return 1

    vi_pham, so_tep, duoc_mien = quet()
    n = len(vi_pham)

    if "--list" in sys.argv:
        for duong, tv in vi_pham:
            print(f"  {duong}  ->  {', '.join(tv)}")
        for duong, tv in duoc_mien:
            print(f"  [MIEN] {duong}  ->  {', '.join(tv)}  -- {NGOAI_LE[duong]}")

    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps({"max": n}, indent=2) + "\n",
                            encoding="utf-8")
        print(f"da ha moc xuong {n}")
        return 0

    moc = _moc()
    # ⚠️ Dau phan cach ASCII thuan (⛔ khong `·`): dong nay in ra console
    # Windows qua `gate.py`, va AGENTS.md §5 da ghi so console do lech bang ma
    # co the lam mot ky tu ngoai ASCII in sai/gay loi.
    dong_ket = (f"quet {so_tep} tep - {n} vi pham - {len(duoc_mien)} MIEN "
               "(ly do trong NGOAI_LE, tools/check_khai_tran_cpu.py)")

    ket_qua = 0
    if moc < 0:
        print("Chua co moc (hoac tep moc thieu/hong). Chay --update de chot.")
        ket_qua = 1
    elif n > moc:
        print(f"TANG {n - moc} tep so voi moc. Xem `--list`.")
        print("Goi thang mot engine nang (RapidOCR/InferenceSession/")
        print("WhisperModel/YOLO/VideoCapture/load_model/torch.load/")
        print("Pipeline.from_pretrained) ma ⛔ khong boc bang mot khai tran")
        print("CPU that (set_num_threads/cpu_affinity/setNumThreads/")
        print("intra_op_num_threads/OMP_NUM_THREADS) nghia la mo mot ho CPU")
        print("chua ai khai tran — dung lop loi lam treo may hai lan 28/09.")
        print("Sua bang MOT trong ba cach: 1) them mot cach khai tran that")
        print("boc dung cho goi engine; 2) neu that su da duoc che (subprocess")
        print("con/GPU lease) va DOC duoc tu ma nguon, them mot dong vao")
        print("NGOAI_LE kem ly do; 3) neu la bao dong gia, sua bo do trong")
        print("chinh cong cu nay (them mot ANCHOR_GOI moi, KHONG quay lai grep")
        print("chuoi).")
        ket_qua = 1
    elif n < moc:
        print(f"Giam {moc - n} tep. Chay --update de ha moc.")

    print(dong_ket)
    print(f"RESULT: {'FAIL' if ket_qua else 'PASS'}")
    return ket_qua


if __name__ == "__main__":
    sys.exit(main())
