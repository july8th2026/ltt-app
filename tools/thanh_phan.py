"""thanh_phan.py — duong dan doi -> THANH PHAN -> test can chay.

    python tools/thanh_phan.py                      # liet ke moi thanh phan
    python tools/thanh_phan.py --doi                # thanh phan bi anh huong boi cay hien tai
    python tools/thanh_phan.py --pham-vi core:tien  # phan do + lien quan
    python tools/thanh_phan.py --test core:tien     # test can chay
    python tools/thanh_phan.py --do-thi core:tien   # phu thuoc + nguoi tieu thu

## Vi sao no ton tai

`gate.py` hien chay 26 buoc cho MOI thay doi. Sua mot dong CSS trong mot app
van keo ca bo test 4 phut. Voi mot phien thi do la phien toai; voi ba phien
cung mot may thi do la ba luot 4 phut tranh nhau 20 loi.

Nhung "chay it di" chi an toan khi biet CHINH XAC thay doi nay cham toi dau.
Do la viec cua tep nay.

## 🔴 Anh xa test PHAI suy tu IMPORT, khong duoc suy tu TEN TEP

Do 2026-09-02 tren kho nay:

    app            khop TEN TEP    thuc su IMPORT
    thumbnail            2              20
    upscalevideo         1              11
    taoanh               2               8
    agent               21               4   <- ten khop nham

`thumbnail` co **20** tep test cham toi no, chi 2 tep mang chu "thumbnail".
Chon ten tep se bo qua 18 phep kiem — im lang, va dung o cho nguy hiem nhat:
mot phep loc **thieu** trong y het mot phep loc **dung**.

Chieu nguoc lai cung sai: "agent" khop 21 ten tep (`agent_image`, `user_agent`,
...) nhung chi 4 tep that su import `apps.agent`.

⇒ Khong khai tay danh sach test, va khong doan tu ten. Doc `import`.

## ⛔ Gioi han da biet, noi thang ra thay vi de nguoi dung tu phat hien

1. **Import dong khong nhin thay duoc.** `importlib.import_module(f"apps.{x}")`
   la vo hinh voi AST. Nhung canh do duoc KHAI trong `thanh_phan.toml` muc
   `[[canh_dong]]` — do la ly do muc ay ton tai.

2. **Fixture va conftest keo theo ca cum.** `tests/conftest.py` cham gan nhu
   moi thu, nen no thuoc **moi** thanh phan. Coi no la "dung chung": doi
   `conftest.py` thi chay TAT CA.

3. **`None` la fail-open.** Khong doc duoc git, khong parse duoc mot tep, hay
   gap thu chua tung thay ⇒ tra ve "khong biet" va nguoi goi phai chay tat ca.
   Mot danh sach rong vi doc hong trong y het mot danh sach rong vi khong doi
   gi — va mot trong hai nghia do dan toi bo qua nham. Cung bay ma
   `gate._da_doi_so_voi_HEAD` da ghi.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tomllib
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEP_KHAI = Path(__file__).resolve().parent / "thanh_phan.toml"

#: Tep cham moi thu. Doi chung => chay tat ca, khong co ngoai le.
#:
#: ⚠️ Day KHONG phai mot danh sach "cho chac". Moi muc phai co ly do dung mot
#:    dong; muc nao khong giai thich duoc thi bo ra, vi moi muc o day lam phep
#:    loc yeu di dung mot chut.
DUNG_CHUNG = (
    "tests/conftest.py",         # fixture goc cua ca bo test
    "requirements.txt",
    "requirements-server.txt",
)

#: 🔴 SU CO 17/09/2026 (tests/test_1500). Truoc day `gate.py`, `test_nhanh.py`,
#:    `thanh_phan.py`, `thanh_phan.toml` nam trong DUNG_CHUNG ⇒ bat ky luot deploy
#:    nao mang theo mot commit governance deu khong L1 duoc (tu nang len L3 ⇒ bi tu
#:    choi giua phien) ⇒ nguoi dung phai L2 thu cong. Nhung chung khong anh huong
#:    MOI test — chung la CONG CU, thuoc thanh phan `cong_cu`, va co test RIENG (tra
#:    bang `test_nhac_toi`). Luot gate L1 do chay bang chinh ma moi nen tu kiem luon.
#: ⛔ `conftest.py` va `requirements*` van o DUNG_CHUNG: chung doi hanh vi cua moi test.

#: Tep KHONG phai ma — khong co ai so huu cung khong buoc chay ca kho. Test nao DOC
#: no (tra bang chuoi) thi chay dung test do; cac buoc kiem tinh (i18n, luat van hanh,
#: ky tu dieu khien...) van chay trong moi luot L1.
#: 🔴 `spike/` va `bench/` KHONG phai ma chay. Chung khong duoc dong goi,
#:    khong ai import, va deploy khong chep chung. Nhung chung nam trong
#:    kho, nen moi tep them vao do tung lam `--doi` FAIL OPEN: "duong khong
#:    ai so huu" ⇒ gate HA CAP xuong `nhanh` ⇒ **bo test khong chay**, va
#:    nguoi doc chi thay chu PASS. Do dung la ca da xay ra 24/09 khi mot
#:    ban dung deploy suyt di ra voi 0 phep test.
TIEN_TO_TAI_LIEU = ("docs/", "locale/", "spike/", "bench/")
DUOI_TAI_LIEU = (".md",)
TEN_TAI_LIEU = (".gitignore", ".gitattributes", ".editorconfig")

#: Ten tep qua chung de tra bang chuoi — tra ca duong day du thay vao.
TEN_QUA_CHUNG = frozenset({"README.md", "__init__.py", "index.md", "NOTES.md"})


class KhongBiet(Exception):
    """Khong du bang chung de thu hep. Nguoi goi phai chay tat ca."""


# ---------------------------------------------------------------------------
# Doc ban khai
# ---------------------------------------------------------------------------

def nap_khai(tep: Path = TEP_KHAI) -> dict:
    with tep.open("rb") as f:
        return tomllib.load(f)


def _cac_app(root: Path) -> dict[str, dict]:
    """App suy tu thu muc, KHONG tu ban khai.

    `apps/<slug>/manifest.py` da la SSOT — chinh `platform_core/registry.py`
    nap app bang cach quet thu muc nay. Khai lai o `thanh_phan.toml` la tao chu
    so huu thu hai cho cung mot su that.
    """
    ra: dict[str, dict] = {}
    thu_muc = root / "apps"
    if not thu_muc.is_dir():
        return ra
    for muc in sorted(thu_muc.iterdir()):
        if not muc.is_dir() or muc.name.startswith(("_", ".")):
            continue
        if not (muc / "manifest.py").is_file():
            continue
        ra[f"app:{muc.name}"] = {
            "mo_ta": f"App {muc.name} (suy tu apps/{muc.name}/manifest.py)",
            "duong": [f"apps/{muc.name}/"],
            "he_trong": "app",
            "tai_nguyen": [],
        }
    return ra


def cac_thanh_phan(root: Path = ROOT) -> dict[str, dict]:
    """Moi thanh phan: khai tay (khong-phai-app) + suy ra (app)."""
    khai = nap_khai()
    ra = dict(khai.get("thanh_phan", {}))
    for k, v in ra.items():
        v.setdefault("tai_nguyen", [])
        v.setdefault("he_trong", "khac")
    ra.update(_cac_app(root))
    return ra


# ---------------------------------------------------------------------------
# duong dan -> thanh phan
# ---------------------------------------------------------------------------

def _chuan(duong: str) -> str:
    return duong.replace("\\", "/").strip().strip('"')


def thanh_phan_cua(duong: str, tp: dict[str, dict] | None = None) -> str | None:
    """Thanh phan so huu mot duong dan. Khop TIEN TO DAI NHAT.

    Dai nhat chu khong phai dau tien: `platform_core/credit.py` phai ve
    `core:tien` chu khong ve `core:nen`, du ca hai deu khai duong duoi
    `platform_core/`.
    """
    tp = tp if tp is not None else cac_thanh_phan()
    d = _chuan(duong)
    tot_nhat: tuple[int, str] | None = None
    for ten, v in tp.items():
        for tien_to in v.get("duong", []):
            t = _chuan(tien_to)
            if d == t or d.startswith(t):
                if tot_nhat is None or len(t) > tot_nhat[0]:
                    tot_nhat = (len(t), ten)
    return tot_nhat[1] if tot_nhat else None


# ---------------------------------------------------------------------------
# Do thi import (AST)
# ---------------------------------------------------------------------------

def _module_duoc_import(tep: Path) -> set[str]:
    """Moi module duoc import trong mot tep. Doc AST, KHONG import tep.

    ⚠️ Doc AST chu khong `import` — mot cong cu trong `tools/` khi bi import se
       chay ma o cap module cua no. Kho nay da tra gia mot lan cho dieu do
       (`cong-cu-tools-doi-stdout-vo-pytest`).
    """
    try:
        # ⚠️ `ast.parse` phat SyntaxWarning cho `"\d"` trong chuoi thuong. Kho
        #    nay co nhieu chu thich tieng Viet kem duong dan Windows nen dinh
        #    kha nhieu. Chung khong lien quan gi toi viec dang lam, va de chung
        #    in ra thi dau ra cua cong cu nay thanh khong doc duoc.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cay = ast.parse(tep.read_text(encoding="utf-8", errors="replace"),
                            filename=str(tep))
    except (SyntaxError, ValueError, OSError):
        return set()
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Import):
            for a in nut.names:
                ra.add(a.name)
        elif isinstance(nut, ast.ImportFrom):
            if nut.level:          # import tuong doi: trong cung goi, bo qua
                continue
            if nut.module:
                ra.add(nut.module)
                # 🔴 FAIL-OPEN 24/09: chi ghi `nut.module` thi
                #    `from platform_core import an_toan_mang` chi noi len
                #    `platform_core` — GOI, khong phai MO-DUN. Canh phu thuoc
                #    toi dung mo-dun bi mat.
                #
                # ⚠️ So do la CUA TOI, tren cay nay, sau khi `an_toan_mang` da
                #    duoc khai thanh phan rieng: `bi_anh_huong` cho no ra
                #    **162 -> 180** tep test. Phien P5 bao "0 -> 127"; do la so
                #    cua HO truoc khi khai thanh phan, toi KHONG do lai duoc
                #    con so ay nen khong chep vao day.
                #
                # ⛔ Va no fail-open dung chieu nguy hiem: pham vi HEP DI, tuc
                #    gate bo qua test that su lien quan roi in ra mot chu XANH.
                #    Mot bo thu hep sai khong bao gio keu — no chi im lang bo
                #    sot (xem test_394 dau tep).
                #
                # ⭐ Sua o DAY chu khong doi kieu import cua nguoi viet: phien
                #    P5 da ne bang cach viet `import platform_core.an_toan_mang`
                #    va no chay duoc, nhung nguoi tiep theo viet `from ... import`
                #    se lai mat do phu TRONG IM LANG. Luat khong duoc phu thuoc
                #    vao viec ai cung nho mot quy uoc.
                for a in nut.names:
                    if a.name != "*":
                        ra.add(f"{nut.module}.{a.name}")
    return ra


def _route_prefix_da_khai(root: Path = ROOT) -> dict[str, str]:
    """`{slug: route_prefix}` doc tu `apps/<slug>/manifest.py` bang AST.

    ⭐ Day KHONG phai "doan tu ten" — thu bi cam o docstring dau tep. `route_prefix`
    la mot BAN KHAI: chinh `platform_core/registry.py` dung no de gan router cua
    app duoi `app.lttstudios.com`. Doc no la cung mot hanh vi voi doc `import`.
    Va no CAN THIET vi nhieu app co prefix KHAC slug (`auto_scan_video` ->
    `/auto-scan-video`), nen suy tu ten thu muc se sai.

    ⚠️ Doc AST chu khong `import` — cung ly le voi `_module_duoc_import`.
    """
    ra: dict[str, str] = {}
    thu_muc = root / "apps"
    if not thu_muc.is_dir():
        return ra
    for muc in sorted(thu_muc.iterdir()):
        if not muc.is_dir() or muc.name.startswith(("_", ".")):
            continue
        mf = muc / "manifest.py"
        if not mf.is_file():
            continue
        cay = _ast_cua(mf)
        if cay is None:
            continue
        for nut in ast.walk(cay):
            if (isinstance(nut, ast.keyword) and nut.arg == "route_prefix"
                    and isinstance(nut.value, ast.Constant)
                    and isinstance(nut.value.value, str)
                    and nut.value.value.startswith("/")):
                ra[muc.name] = nut.value.value
                break
    return ra


def _ast_cua(tep: Path):
    """AST cua mot tep, hoac None. Cung khuon chan canh bao voi `_module_duoc_import`."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ast.parse(tep.read_text(encoding="utf-8", errors="replace"),
                             filename=str(tep))
    except (SyntaxError, ValueError, OSError):
        return None


def _chuoi_hang_khong_docstring(cay) -> list[str]:
    """Moi chuoi HANG trong AST, TRU docstring.

    ⭐ Doc AST tra loi thang mot lo ngai co that: mot duong dan nam trong CHU THICH
    khong duoc tinh. Chu thich ⛔ khong ton tai trong AST, nen chung vo hinh mien
    phi. Docstring thi CO trong AST, nen phai bo tay — mot doan van ke ve
    `/taovideo/prefill` khong phai mot lan GOI no.
    """
    bo_qua = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.ClassDef, ast.FunctionDef,
                            ast.AsyncFunctionDef)):
            than = getattr(nut, "body", None) or []
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                bo_qua.add(id(than[0].value))
    return [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in bo_qua]


def _app_go_qua_http(tep: Path, tien_to_sap: list[tuple[str, str]]) -> set[str]:
    """App ma tep test nay go qua DUONG DAN HTTP, khong qua `import`.

    🔴 VI SAO CO HAM NAY (do 27/09/2026). Do thi import khong thay
    `client.post("/taovideo/prefill")` — do la mot CHUOI, khong mot canh import.
    Do hai tang (dem, roi doi chieu voi chinh `--test app:<X>`): **50 tep test**
    go mot app ma khong nam trong thanh phan cua app do. Ti le nang nhat:
    `app:agent` liet ke 11 tep trong khi 21 tep khac go `/agent` — gan ba lan tap
    da biet la vo hinh.

    ⚠️ Vi trong phien chi chay **test nham** (hop dong §4, gate chi mot lan o cuoi
    plan), lo nay nam trong **luoi an toan duy nhat** de gop `main`. Ca that:
    `tests/test_5152_taovideo_prefill_route_and_queue.py` khang dinh tran anh cu
    (`== 4`); khi tran len 9 no DO, nhung `--test app:taovideo` khong liet ke no.

    ⭐ HAI QUY TAC KHOP, thieu mot la sai:
      1. **Sap theo do dai GIAM** — `/agent` se an `/agent-dong-co/x` neu thu truoc.
      2. **Ranh gioi doan** — sau tien to phai la het chuoi hoac `/`, `?`, `#`.
         Khong co no thi `/agent` khop ca `/agentic-xyz`.

    ⭐ CHIEU SAI AN TOAN: gan THUA (mot tep chi NHAC toi duong dan) lam luot test
    nham TO hon — cung chieu voi `None` = fail-open o muc 3 docstring dau tep. Gan
    THIEU moi la chieu nguy hiem, va do la chieu ham nay sua.
    """
    cay = _ast_cua(tep)
    if cay is None:
        return set()
    ra: set[str] = set()
    for s in _chuoi_hang_khong_docstring(cay):
        if not s.startswith("/"):
            continue
        for app, tien_to in tien_to_sap:
            if s.startswith(tien_to):
                con = s[len(tien_to):]
                if con == "" or con[0] in "/?#":
                    ra.add(app)
                    break
    return ra


def _module_sang_duong(mod: str, root: Path) -> str | None:
    """`apps.taoanh.features` -> `apps/taoanh/features.py` (hoac thu muc goi)."""
    phan = mod.split(".")
    for n in range(len(phan), 0, -1):
        goc = "/".join(phan[:n])
        if (root / f"{goc}.py").is_file():
            return f"{goc}.py"
        if (root / goc / "__init__.py").is_file():
            return f"{goc}/"
        if (root / goc).is_dir():
            return f"{goc}/"
    return None


def test_cua_thanh_phan(root: Path = ROOT,
                        tp: dict[str, dict] | None = None) -> dict[str, set[str]]:
    """`thanh_phan -> {tep test}`, suy tu import that trong `tests/`.

    Xem docstring dau tep ve vi sao khong dung ten tep.
    """
    tp = tp if tp is not None else cac_thanh_phan(root)
    ra: dict[str, set[str]] = {ten: set() for ten in tp}
    thu_muc = root / "tests"
    if not thu_muc.is_dir():
        return ra
    # Sap GIAM theo do dai mot lan cho ca vong lap: `/agent-dong-co` phai duoc
    # thu truoc `/agent`, khong thi app dai hon bi app ngan hon an.
    tien_to_sap = sorted(_route_prefix_da_khai(root).items(),
                         key=lambda kv: -len(kv[1]))
    for tep in sorted(thu_muc.rglob("*.py")):
        # ⛔ CHI module test THAT. `tests/` con chua `__init__.py`, `conftest.py`,
        #    `pg_scratch.py`, `run_tests.py` va sau tep `tests/fixtures/*.py` —
        #    chung la ma HO TRO, khong phai module test.
        #
        #    Do 2026-09-02: dua ca `tests/__init__.py` cho pytest lam ca luot
        #    chet bang `INTERNALERROR` trong `import_path`. Va INTERNALERROR
        #    khong phai mot test do — no la ca bo test **khong chay**, trong khi
        #    dong ket qua van la mot con so that bai binh thuong. Tuc mot phep
        #    loc sai o day co the bien "khong chay gi" thanh "chay va do".
        if not tep.name.startswith("test_"):
            continue
        ten_tuong_doi = tep.relative_to(root).as_posix()
        if ten_tuong_doi in DUNG_CHUNG:
            continue
        for mod in _module_duoc_import(tep):
            duong = _module_sang_duong(mod, root)
            if duong is None:
                continue
            chu = thanh_phan_cua(duong, tp)
            if chu:
                ra[chu].add(ten_tuong_doi)
        # Canh THU HAI: test go app qua DUONG DAN HTTP chu khong qua import.
        # Xem `_app_go_qua_http` — 50 tep test tung vo hinh voi do thi import.
        for app in _app_go_qua_http(tep, tien_to_sap):
            ten_tp = f"app:{app}"
            if ten_tp in ra:
                ra[ten_tp].add(ten_tuong_doi)
    return ra


def do_thi_phu_thuoc(root: Path = ROOT,
                     tp: dict[str, dict] | None = None
                     ) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(phu_thuoc, nguoi_tieu_thu) giua cac thanh phan.

    Gom ca canh TINH (doc AST) va canh DONG (khai trong `thanh_phan.toml`).
    Canh dong khong the suy ra duoc — do la ca ly do chung phai duoc khai.
    """
    tp = tp if tp is not None else cac_thanh_phan(root)
    phu_thuoc: dict[str, set[str]] = {ten: set() for ten in tp}

    for ten, v in tp.items():
        for tien_to in v.get("duong", []):
            goc = root / _chuan(tien_to)
            tep_list = ([goc] if goc.is_file() else
                        sorted(goc.rglob("*.py")) if goc.is_dir() else [])
            for tep in tep_list:
                if tep.suffix != ".py":
                    continue
                for mod in _module_duoc_import(tep):
                    duong = _module_sang_duong(mod, root)
                    if duong is None:
                        continue
                    dich = thanh_phan_cua(duong, tp)
                    if dich and dich != ten:
                        phu_thuoc[ten].add(dich)

    for canh in nap_khai().get("canh_dong", []):
        nguon = thanh_phan_cua(canh["tu"], tp)
        if nguon is None:
            continue
        for t in canh.get("toi", []):
            dich = thanh_phan_cua(t, tp)
            if dich and dich != nguon:
                phu_thuoc[nguon].add(dich)

    nguoi_tieu_thu: dict[str, set[str]] = {ten: set() for ten in tp}
    for ten, ds in phu_thuoc.items():
        for d in ds:
            nguoi_tieu_thu[d].add(ten)
    return phu_thuoc, nguoi_tieu_thu


# ---------------------------------------------------------------------------
# Cay hien tai -> thanh phan bi anh huong
# ---------------------------------------------------------------------------

def duong_da_doi(root: Path = ROOT, goc_so: str = "") -> set[str]:
    """Duong dan da doi. Nem `KhongBiet` khi khong chac — KHONG tra rong.

    `goc_so` rong = so voi HEAD va ca phan chua commit.
    """
    lenh = [["git", "status", "--porcelain", "-uall"]]
    lenh.append(["git", "diff", "--name-only", goc_so or "HEAD"])
    ra: set[str] = set()
    for lc in lenh:
        try:
            kq = subprocess.run(lc, cwd=root, capture_output=True, text=True,
                                timeout=30, encoding="utf-8", errors="replace")
        except (OSError, subprocess.SubprocessError) as e:
            raise KhongBiet(f"git that bai: {e}") from e
        if kq.returncode != 0:
            raise KhongBiet(f"git tra {kq.returncode}: {' '.join(lc)}")
        for dong in kq.stdout.splitlines():
            d = dong[3:] if lc[1] == "status" else dong
            d = _chuan(d)
            if d:
                ra.add(d)
    return ra


def _la_tep_test(duong: str) -> bool:
    """`tests/test_*.py` — module test THAT, khong phai ma ho tro trong `tests/`.

    Cung phep loc ma `test_cua_thanh_phan` dung (tien to `test_`), va co cung ly
    do: `tests/__init__.py`, `conftest.py`, `fixtures/*.py` la ma HO TRO — sua
    chung thi anh huong lan ra ca bo, nen chung KHONG duoc huong luat nay.
    """
    d = _chuan(duong)
    return (d.startswith("tests/") and d.endswith(".py")
            and d.rpartition("/")[2].startswith("test_"))


def la_tai_lieu(duong: str) -> bool:
    """Tep khong phai ma: tai lieu, ban dich, cau hinh git (xem TIEN_TO_TAI_LIEU)."""
    d = _chuan(duong)
    ten = d.rpartition("/")[2]
    return (d.startswith(TIEN_TO_TAI_LIEU) or d.endswith(DUOI_TAI_LIEU)
            or ten in TEN_TAI_LIEU)


def _mau_tra(duong: str) -> list["re.Pattern[str]"]:
    """Mau de tra mot tep trong ma nguon test: duong day du, ten tep, ten module.

    ⚠️ Ranh gioi TU: `import gate` khong duoc khop `import gateway` (do 17/09: ban
       tra chuoi con keo them 14 tep test VPS/render_gateway khong lien quan).
    """
    d = _chuan(duong)
    ten = d.rpartition("/")[2]
    ra = [re.compile(r"(?<![\w/.-])" + re.escape(d) + r"(?![\w.-])")]
    if ten not in TEN_QUA_CHUNG and len(ten) >= 6:
        ra.append(re.compile(r"(?<![\w.-])" + re.escape(ten) + r"(?![\w.-])"))
    if d.startswith("tools/") and d.endswith(".py") and d.count("/") == 1:
        mod = re.escape(ten[:-3])
        ra.append(re.compile(rf"\b(?:import|from)\s+(?:tools\.)?{mod}\b(?!\.)"))
        ra.append(re.compile(rf"\btools\.{mod}\b(?!\.\w*\()"))
    return ra


def _van_ban_ma(tep: Path) -> str | None:
    """Chuoi hang TRONG MA (bo docstring, bo chu thich) + cac cau import, noi dong.

    Do 17/09: tra van ban tho khop ca nhung test chi NHAC `gate.py` trong chu thich
    (`test_245`, `test_312`) — chay chung khong kiem them gi. Mot test DOC mot tep thi
    ten tep nam trong mot chuoi hang cua ma, hoac trong mot `import`.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cay = ast.parse(tep.read_text(encoding="utf-8", errors="replace"), filename=str(tep))
    except (SyntaxError, ValueError, OSError):
        return None
    docstring: set[int] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            than = getattr(nut, "body", [])
            if (than and isinstance(than[0], ast.Expr) and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                docstring.add(id(than[0].value))
    phan: list[str] = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str) and id(nut) not in docstring:
            phan.append(nut.value)
        elif isinstance(nut, ast.Import):
            phan += [f"import {a.name}" for a in nut.names]
        elif isinstance(nut, ast.ImportFrom) and nut.module:
            phan.append(f"from {nut.module} import x")
    return "\n".join(phan).replace("\\", "/")


def test_nhac_toi(duong: set[str], root: Path = ROOT) -> set[str]:
    """Tep test NHAC TOI (doc, mo, import theo ten) mot tep da doi — tra bang CHUOI.

    Danh cho thu ma do thi import khong thay: tai lieu ma test doc noi dung
    (`CLAUDE.md`, `AGENTS.md`), ban dich, va cong cu trong `tools/` ma test nap bang
    `sys.path` + `import test_nhanh`. Tep test da doi va ma san pham co chu thi da
    co duong khac — bo qua o day.
    """
    can_tra: dict[str, list[re.Pattern[str]]] = {}
    for d in duong:
        d = _chuan(d)
        if _la_tep_test(d) or d in DUNG_CHUNG:
            continue
        can_tra[d] = _mau_tra(d)
    if not can_tra:
        return set()
    ra: set[str] = set()
    thu_muc = root / "tests"
    if not thu_muc.is_dir():
        return ra
    for tep in sorted(thu_muc.glob("test_*.py")):
        noi_dung = _van_ban_ma(tep)
        if noi_dung is None:
            # Khong parse duoc thi khong doan: coi nhu no co the doc — chay no.
            ra.add(tep.relative_to(root).as_posix())
            continue
        if any(m.search(noi_dung) for ds in can_tra.values() for m in ds):
            ra.add(tep.relative_to(root).as_posix())
    return ra


def tep_test_da_doi(duong: set[str]) -> set[str]:
    """Cac tep test trong tap duong dan da doi — nop THANG vao danh sach chay.

    Sua mot tep test thi phai chay chinh tep do, ke ca khi khong co thanh phan
    san pham nao doi. Xem `bi_anh_huong` ve vi sao khong di vong qua thanh phan.
    """
    return {_chuan(d) for d in duong if _la_tep_test(d)}


def bi_anh_huong(duong: set[str], root: Path = ROOT, *,
                 mo_rong_tieu_thu: bool = True) -> set[str] | None:
    """Thanh phan can kiem cho tap duong dan nay. `None` = phai chay TAT CA.

    ⛔ Tra `None` khi gap mot duong dan **khong thanh phan nao so huu**. Do la
       fail-open co chu y: mot tep khong ai nhan la mot tep khong ai do duoc
       anh huong, va doan bua o do la cach bo qua nham.
    """
    tp = cac_thanh_phan(root)
    if any(_chuan(d) in DUNG_CHUNG for d in duong):
        return None
    # ⭐ MOT TEP TEST KHONG CO NGUOI TIEU THU — nen no khong dong gop THANH PHAN.
    #
    # 🔴 Vi sao can. `thanh_phan.toml` khai duong cho ma SAN PHAM, khong khai
    #    `tests/`. Nen truoc 08/09 moi thay doi cham mot tep test deu roi vao
    #    nhanh `chu is None` ngay duoi va ha cap xuong DAY DU — va gan nhu moi
    #    thay doi that deu kem mot tep test. Do tren 59 ban ghi trong
    #    `test-results/gates/`: ho so `doi` va `pham-vi` co **0 luot chay**.
    #    Duong `--doi` ton tai, duoc tai lieu hoa, va **chua tung thu hep gi**.
    #
    # ⛔ VA DUNG DOI NO SANG "suy chu tu import cua chinh tep test". Da thu
    #    08/09 va do duoc: `tests/test_500` import mot module nen, nen phep dao
    #    nguoc tra ve 36 thanh phan -> **456/530 tep test (86%)**. Do la mot
    #    pham vi TRONG NHU HEP ma khong he hep — dung cai bay `HO_SO` canh bao.
    #
    # ⭐ Cai dung hep la: sua mot tep test chi anh huong CHINH TEP DO. Khong co
    #    ai `import` mot module test, nen khong co canh tieu thu nao de mo rong.
    #    Tep test da doi duoc nop THANG vao danh sach chay — xem
    #    `tep_test_da_doi()` va `gate.py::_thu_hep`.
    #
    # ⚠️ Chi ap cho `tests/test_*.py`. `tests/conftest.py` nam trong DUNG_CHUNG
    #    (da chan o tren), con `tests/fixtures/*.py` va moi thu khac trong
    #    `tests/` van roi xuong `chu is None` -> chay TAT CA. Fail-open giu nguyen.
    ra: set[str] = set()
    for d in duong:
        if _la_tep_test(d):
            continue
        chu = thanh_phan_cua(d, tp)
        if chu is None:
            # Tai lieu khong co chu: khong keo ca kho — test doc no di qua
            # `test_nhac_toi` (gate.py::_thu_hep). Ma khong co chu: van fail-open.
            if la_tai_lieu(d):
                continue
            return None
        ra.add(chu)
    if mo_rong_tieu_thu:
        _, tieu_thu = do_thi_phu_thuoc(root, tp)
        them: set[str] = set()
        for t in ra:
            them |= tieu_thu.get(t, set())
        ra |= them
    return ra


def tach_danh_sach(gia_tri: "str | list[str] | tuple[str, ...] | None") -> list[str]:
    """`--pham-vi`/`--test` nhan NHIEU thanh phan: phay (`a,b`) va/hoac lap co.

    Giu thu tu xuat hien, bo trung va bo rong. Mot thanh phan -> `[tp]`, y het
    hanh vi cu (Task 11b, 18/09).
    """
    if not gia_tri:
        return []
    manh = [gia_tri] if isinstance(gia_tri, str) else list(gia_tri)
    ra: list[str] = []
    for m in manh:
        for t in str(m).split(","):
            t = t.strip()
            if t and t not in ra:
                ra.append(t)
    return ra


def mo_rong_pham_vi(chon: set[str], root: Path = ROOT,
                    tp: dict[str, dict] | None = None) -> set[str]:
    """Cac thanh phan duoc chon + nguoi tieu thu TRUC TIEP cua tung cai (HOP).

    Mot nguon cho `--pham-vi` cua ca `thanh_phan.py` va `gate.py` (L2).
    """
    tp = tp if tp is not None else cac_thanh_phan(root)
    _, tieu_thu = do_thi_phu_thuoc(root, tp)
    ca = set(chon)
    for t in chon:
        ca |= tieu_thu.get(t, set())
    return ca


def test_can_chay(phan: set[str], root: Path = ROOT) -> set[str]:
    bang = test_cua_thanh_phan(root)
    ra: set[str] = set()
    for t in phan:
        ra |= bang.get(t, set())
    return ra


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Do thi thanh phan cua kho.")
    p.add_argument("--doi", action="store_true", help="thanh phan bi cay hien tai anh huong")
    p.add_argument("--pham-vi", action="append", default=[],
                   help="thanh phan + nguoi tieu thu; nhieu: `a,b` hoac lap co")
    p.add_argument("--test", action="append", default=[],
                   help="test can chay cho thanh phan; nhieu: `a,b` hoac lap co")
    p.add_argument("--do-thi", default="", help="phu thuoc va nguoi tieu thu")
    p.add_argument("--goc-so", default="", help="so voi commit nay thay vi HEAD")
    a = p.parse_args()
    tp = cac_thanh_phan()

    if a.do_thi:
        pt, tt = do_thi_phu_thuoc()
        if a.do_thi not in tp:
            print(f"Khong co thanh phan {a.do_thi!r}"); return 2
        print(f"{a.do_thi}")
        print(f"  phu thuoc vao : {', '.join(sorted(pt[a.do_thi])) or '(khong)'}")
        print(f"  duoc dung boi : {', '.join(sorted(tt[a.do_thi])) or '(khong)'}")
        return 0

    if a.test:
        chon = tach_danh_sach(a.test)
        la = [t for t in chon if t not in tp]
        if la:
            print(f"Khong co thanh phan {', '.join(map(repr, la))}"); return 2
        bang = test_cua_thanh_phan()
        ds = sorted(set().union(*(bang[t] for t in chon)))
        print(f"{', '.join(chon)}: {len(ds)} tep test")
        for t in ds:
            print(f"  {t}")
        return 0

    if a.pham_vi:
        chon = tach_danh_sach(a.pham_vi)
        la = [t for t in chon if t not in tp]
        if la:
            print(f"Khong co thanh phan {', '.join(map(repr, la))}"); return 2
        ca = mo_rong_pham_vi(set(chon), tp=tp)
        print(f"Pham vi {', '.join(chon)}: {len(ca)} thanh phan")
        for t in sorted(ca):
            print(f"  {t}")
        print(f"=> {len(test_can_chay(ca))} tep test")
        return 0

    if a.doi:
        try:
            duong = duong_da_doi(goc_so=a.goc_so)
        except KhongBiet as e:
            print(f"KHONG BIET ({e}) -> phai chay TAT CA"); return 1
        if not duong:
            print("Cay khong doi gi."); return 0
        phan = bi_anh_huong(duong)
        print(f"{len(duong)} duong dan doi")
        if phan is None:
            print("=> cham tep DUNG CHUNG hoac duong khong ai so huu"
                  " -> phai chay TAT CA")
            return 1
        for t in sorted(phan):
            print(f"  {t}")
        print(f"=> {len(test_can_chay(phan))} tep test")
        return 0

    pt, tt = do_thi_phu_thuoc()
    bang = test_cua_thanh_phan()
    print(f"{len(tp)} thanh phan\n")
    print(f"  {'THANH PHAN':<26} {'HE TRONG':<12} {'TEST':>5}  PHU THUOC")
    for ten in sorted(tp):
        print(f"  {ten:<26} {tp[ten].get('he_trong',''):<12} "
              f"{len(bang[ten]):>5}  {len(pt[ten])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
