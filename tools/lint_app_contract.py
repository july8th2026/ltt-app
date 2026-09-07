"""
lint_app_contract.py - kiem CO HOC hop dong app (audit tai dung).

Quet moi apps/<slug>/ va bao cac vi pham hop dong pho bien (theo rubric rà soát):
- manifest.py co MANIFEST, slug == ten thu muc;
- khai job_types thi PHAI co jobs.py::handle + credit_cost != None;
- routes.py co @router.post thi nen dung verify_csrf_token + require_login (CSRF/auth);
- route serve file ({key:path}) nen guard theo user_id (co-lap A-khong-doc-B);
- routes.py khong duoc phinh thanh noi chua logic nghiep vu (xem NGUONG duoi).

ERROR = vi pham chac chan (chan). WARN = dau hieu can nguoi soi. Chay:
    python tools/lint_app_contract.py            # bao cao
    python tools/lint_app_contract.py --strict    # WARN cung tinh la loi (exit 1)

Khong thay the review cua nguoi/agent - chi bat cac loi co hoc re tien, som.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"

# App co ly do rieng, mien tru mot so kiem tra.
#
# Muc `socialbot` bo di 2026-08-25 cung app do (Q108). Danh sach nay nay RONG,
# va giu nguyen no rong la mot muc tieu: moi mien tru la mot app khong bi hop
# dong soi, va ly do mien tru thi song lau hon hoan canh sinh ra no.
SKIP_APPS: set = set()

# ── Nguong tang nghiep vu (audit control-plane 2026-08-06) ──────────────────
#
# Hop dong app quy dinh manifest/routes/jobs nhung KHONG noi logic nghiep vu
# nam o dau. Ket qua do duoc: 5 app dung features.py, 5 app dung cost.py, 1 app
# dung services/, con lai nhet thang vao route. Khong co cho mac dinh thi route
# la cho de moi thu roi vao - hai file route da vuot 1.300 dong vi vay.
#
# Chuan tu 2026-08-06: logic nghiep vu nam o `services/` (nhieu miền) hoac mot
# module rieng nhu `features.py` / `cost.py` (mot miền). Route chi lo HTTP.
#
# Nguong chon theo phan bo thuc te chu khong theo cam tinh: file route lon nhat
# ma van de doc trong repo la ~870 dong / 23 handler (autosubvideo), nen dat
# tran o 900 dong va 30 handler - vua du de khong bao dong gia, vua chan duoc
# hai file 1.300-1.800 dong hien tai.
#: Bon module cua `server` ma app DUOC PHEP import. Danh sach nay la HOP DONG,
#: khong phai anh chup: no duoc DO tu thuc te (A-04) roi CHOT LAI, de lan sau ai
#: do voi tay sau hon thi gate do thay vi im lang.
#:
#: Do bang AST tren 732 tep: 12 app cham DUNG bon module nay, khong app nao cham
#: sau hon. Nghia la day KHONG phai coupling lan man - day la HOP DONG WEB CUA
#: APP, da on dinh, chi la no dang song nham goi.
#:
#: Them mot muc vao day la MOT QUYET DINH KIEN TRUC - lam co y, dung lam cho tien.
SERVER_APP_CO_THE_DUNG = {
    "server.deps",            # get_db, user_hien_tai
    "server.auth.session",    # require_login
    "server.auth.csrf",       # issue/verify_csrf_token
    "server.templating",      # templates
}

#: App NAO duoc goi sang app NAO, va CU THE goi cai gi. Mac dinh la RONG: hai
#: app khong duoc biet nhau.
#:
#: 🔴 Do bang AST 2026-08-26: ca kho co DUNG MOT canh xuyen-san-pham —
#:    `taovideo -> upscalevideo`, hai cho import.
#:
#: ⭐ Doc them mot tang thi no KHONG phai mot sai lam cau tha: hai thu duoc goi
#:    co ten dung nghia be mat cong khai (`service.submit_upscale_job`,
#:    `cost.uoc_luong_credit`). Van de la be mat do CHUA duoc khai la cong khai,
#:    nen khong co gi ngan lan sau ai do voi tay vao cho sau hon.
#:
#: ⛔ VI SAO KHAI BAO chu khong CAT CANH: cat no nghia la doi viec dieu phoi
#:    "nang cap mot video vua tao" di dau do — va khong cho nao tot hon cho hien
#:    tai. Route cua `taovideo` la noi khach bam nut, va bao gia phai la bao gia
#:    THAT cua `upscalevideo`, khong phai mot ban sao se troi.
#:
#: ⭐ Chot CA TEN DUOC IMPORT, khong chi ten module. Chot moi module thi
#:    `from apps.upscalevideo import bat_cu_gi` van lot, va hop dong nay chi con
#:    la mot loi de ngo.
#:
#: Them mot dong vao day la MOT QUYET DINH KIEN TRUC — lam co y, ghi ly do.
APP_DUOC_DUNG_APP: dict = {
    ("taovideo", "upscalevideo"): {
        ("apps.upscalevideo", "cost"),                        # bao gia nang cap
        ("apps.upscalevideo.service", "submit_upscale_job"),  # nop job nang cap
    },
    # `lttvideo` — nut "Nang net" tren mot video da sinh. Cung be mat, cung ly do
    # voi `taovideo`: engine upscale chay tren GPU may A va viec ay chi co MOT
    # ban trong ca he. Chep `build_params` sang app khac la dung ban sao thu hai
    # cua mot hop dong dang song o noi khac.
    #
    # ⭐ Xin IT hon `taovideo`: khong xin `cost`. `lttvideo` khong bao gia nang
    #    cap tren giao dien cua no — nguoi dung bam nut roi xem gia o trang job
    #    cua nen tang. Xin dung thu minh dung.
    ("lttvideo", "upscalevideo"): {
        ("apps.upscalevideo.service", "submit_upscale_job"),  # nop job nang cap
    },
}


def _be_mat_app_tu_khai(goc: pathlib.Path, slug: str) -> set | None:
    """`BE_MAT_CONG_KHAI` mà chính app khai trong `__init__.py`, hoặc None.

    Đọc bằng AST chứ không import: linter chạy trên cây nguồn, và import một app
    kéo theo cả phụ thuộc của nó.
    """
    p = goc / slug / "__init__.py"
    if not p.exists():
        return None
    try:
        cay = ast.parse(_read(p))
    except SyntaxError:
        return None
    for node in cay.body:
        # Nhan ca `X = ...` lan `X: kieu = ...` — mot ban khai co chu thich kieu
        # van la mot ban khai, va bo sot no thi hang rao im lang.
        if isinstance(node, ast.Assign):
            dich = node.targets
        elif isinstance(node, ast.AnnAssign):
            dich = [node.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "BE_MAT_CONG_KHAI"
                   for t in dich):
            continue
        if node.value is None:
            return None
        try:
            gia_tri = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            # Ban khai phai la LITERAL. Boc `frozenset(...)`/`set(...)` quanh no
            # lam cho doc-khong-import het doc duoc — noi thanh cau thay vi tra
            # None, vi None o day co nghia la "chua khai gi ca".
            return set()
        try:
            return {tuple(x) for x in gia_tri}
        except TypeError:
            return set()
    return None


def _doi_chieu_ban_khai(goc: pathlib.Path) -> list:
    """Bản khai của app và allowlist của linter phải khớp NHAU, cả hai chiều.

    ⭐ Vì sao cần cả hai chiều, không chỉ "app khai gì thì cho phép nấy": nếu chỉ
       đọc bản khai thì một app tự mở rộng bề mặt của mình là đủ để app khác
       thò tay vào sâu hơn — hàng rào tự tháo chính nó. Còn nếu chỉ đọc
       allowlist thì app không biết mình đang gánh hợp đồng của ai (đúng lỗ
       H41.5 bịt). Hai bản khai, phải khớp, và lệch là ĐỎ.
    """
    findings = []
    duoc_goi = {bi_goi for _, bi_goi in APP_DUOC_DUNG_APP}
    for bi_goi in sorted(duoc_goi):
        if not (goc / bi_goi).is_dir():
            # App khong co trong cay dang quet. Xay ra that voi cay tong hop cua
            # test, va o do doi mot ban khai la doi mot thu khong the ton tai.
            continue
        khai = _be_mat_app_tu_khai(goc, bi_goi)
        gom = set()
        for (_, dich), cho_phep in APP_DUOC_DUNG_APP.items():
            if dich == bi_goi:
                gom |= set(cho_phep)
        if khai is None:
            findings.append(Finding(
                bi_goi, "ERROR",
                "app nay duoc app khac goi sang nhung KHONG tu khai be mat. "
                f"Them `BE_MAT_CONG_KHAI` vao apps/{bi_goi}/__init__.py voi "
                f"dung: {sorted(gom)}"))
            continue
        if khai != gom:
            findings.append(Finding(
                bi_goi, "ERROR",
                f"ban khai cua app lech voi `APP_DUOC_DUNG_APP`. "
                f"App khai {sorted(khai)}; linter cho phep {sorted(gom)}. "
                "Sua CA HAI hoac khong sua ben nao."))
    return findings


#: Guard nao duoc coi la "route nay doi dang nhap".
#:
#: ⛔ KHONG phai mot danh sach mien tru. Moi ten o day phai THAT SU bao ham
#:    dang nhap, va `test_308` DO dieu do chu khong tin loi: no doc than
#:    `require_operator` va doi thay `require_login(request)` trong do.
#:
#: 🔴 Truoc 2026-09-02 cho nay khop dung mot chuoi `require_login`, nen no canh
#:    bao `apps/qualitylab` — mot app `public=False`, `surface="admin"`, moi
#:    route deu `Depends(require_operator)`, tuc duoc canh CHAT HON. Do la canh
#:    bao DUY NHAT tren ca 15 app, va no la DUONG TINH GIA.
#:
#: ⭐ Cai gia khong phai mot dong thua: mot canh bao sai ton tai lau se day
#:    nguoi ta bo qua chinh cong cu phat ra no.
GUARD_DOI_DANG_NHAP = ("require_login", "require_operator")

MAX_ROUTES_LINES = 900
MAX_ROUTES_HANDLERS = 30


class Finding:
    def __init__(self, app: str, level: str, msg: str):
        self.app, self.level, self.msg = app, level, msg

    def __repr__(self) -> str:
        return f"[{self.level}] {self.app}: {self.msg}"


def _read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def lint() -> list:
    findings: list = []
    if not APPS.is_dir():
        return findings
    for d in sorted(APPS.iterdir()):
        app = d.name
        if not d.is_dir() or app.startswith(("_", ".")) or app in SKIP_APPS:
            continue
        man = d / "manifest.py"
        if not man.is_file():
            findings.append(Finding(app, "ERROR", "thieu manifest.py"))
            continue
        mtext = _read(man)
        if "MANIFEST" not in mtext:
            findings.append(Finding(app, "ERROR", "manifest.py khong co MANIFEST"))
        m = re.search(r'slug\s*=\s*["\']([^"\']+)["\']', mtext)
        if m and m.group(1) != app:
            findings.append(Finding(app, "ERROR",
                                    f"slug {m.group(1)!r} != ten thu muc {app!r}"))
        # 🔴 THEM 2026-08-26 — DA CO MOT LINK 404 TRONG HEADER CUA MOI KHACH
        #    DA DANG NHAP, VA KHONG PHEP KIEM NAO THAY.
        #
        #    `apps/ltt_llm` khai `surface="customer"`, khong khai
        #    `catalog_parent`, va KHONG co `routes.py`. Hai dieu dau lam
        #    `visible_on_surface(authenticated=True)` tra True; dieu thu ba lam
        #    dich cua no khong ton tai. Do that: `GET /ltt-llm` -> 404.
        #
        # ⛔ Cai bay nam o cho `nav=()` KHONG co nghia la "khong co nav":
        #    `nav_entries()` tu sinh lai mot dong tro vao `route_prefix` khi app
        #    khong khai gi. Nen mot app "chua co giao dien" van moc mot dong nav.
        #
        # ⭐ `apps/anhnoibo` da tranh dung cai bay nay bang `catalog_parent`, va
        #    con VIET RA ly do trong chu thich. Nghia la bai hoc DA duoc hoc va
        #    DA duoc ghi - no chi chua bao gio thanh mot phep kiem. Day la luat
        #    hoa no: mot app sinh the catalog/nav thi phai co trang de dap xuong.
        #
        #    Dat o linter chu khong chi o pytest, vi `gate --quick` bo pytest.
        khai_customer = bool(re.search(r"surface\s*=\s*['\"]customer['\"]", mtext))
        co_cha = bool(re.search(r"catalog_parent\s*=\s*['\"][^'\"]+['\"]", mtext))
        co_route = (d / "routes.py").is_file() or (d / "routes").is_dir()
        if khai_customer and not co_cha and not co_route:
            findings.append(Finding(
                app, "ERROR",
                "surface=customer + khong catalog_parent + khong routes.py "
                "=> nav_entries() sinh mot dong tro vao route_prefix KHONG TON TAI "
                "(link 404 trong header cua moi khach da dang nhap). "
                "Khai catalog_parent, hoac them routes.py."))

        has_jobtypes = bool(re.search(r"job_types\s*=\s*\(\s*['\"]", mtext))
        if has_jobtypes:
            jobs = d / "jobs.py"
            if not jobs.is_file() or "def handle" not in _read(jobs):
                findings.append(Finding(app, "ERROR",
                                        "khai job_types nhung thieu jobs.py::handle"))
            if re.search(r"credit_cost\s*=\s*None", mtext):
                findings.append(Finding(app, "ERROR",
                                        "khai job_types nhung credit_cost=None"))

        # App co the khai route bang MOT file `routes.py` hoac mot package
        # `routes/`. Bo qua dang package thi linter im lang dung voi hai app
        # LON NHAT ngay sau khi chung duoc tach - moi kiem CSRF/auth/co-lap
        # duoi day bien mat ma khong ai biet.
        # ── BIEN `apps/` -> `server/` (A-04, do 2026-08-26) ───────────────
        #
        # ⭐ Vi sao KHAI BAO chu khong DOI CHO: doi 4 module nay sang
        #    `platform_core/web/` la 72 lan sua import trong 12 app, de doi lay
        #    mot cai ten dung hon. Rui ro THAT khong phai cai ten - no la lan
        #    sau ai do voi tay SAU hon bon module nay. Luat duoi day chan dung
        #    dieu do, voi gia mot vong lap.
        #
        # Xem docs/MVP_OPTIMIZATION_V2/04_ARCHITECTURE_DEPENDENCY_AUDIT.md A-04.
        for f in sorted(d.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            noi_dung = _read(f)

            # ── BIEN `apps/` -> `apps/` (A-01) ───────────────────────────
            for m3 in re.finditer(
                    r"^\s*from\s+(apps\.[A-Za-z0-9_.]+)\s+import\s+(.+)$",
                    noi_dung, re.M):
                mod, ten_raw = m3.group(1), m3.group(2).split("#")[0]
                phan = mod.split(".")
                if len(phan) < 2 or phan[1] == app:
                    continue                  # trong cung app — khong phai canh
                cho_phep = APP_DUOC_DUNG_APP.get((app, phan[1]), set())
                for ten in (t.strip().split(" as ")[0].strip()
                            for t in ten_raw.split(",")):
                    if not ten or (mod, ten) in cho_phep:
                        continue
                    findings.append(Finding(
                        app, "ERROR",
                        f"{f.relative_to(d).as_posix()} import {ten!r} tu {mod!r} "
                        "— app khong duoc goi vao ruot app khac. Be mat duoc "
                        f"phep cua `{phan[1]}`: {sorted(cho_phep) or 'KHONG CO'}. "
                        "Can them thi khai vao `APP_DUOC_DUNG_APP` truoc."))

            for m2 in re.finditer(
                    r"^\s*from\s+(server\.[A-Za-z0-9_.]+)\s+import", noi_dung, re.M):
                mod = m2.group(1)
                if not any(mod == ok or mod.startswith(ok + ".")
                           for ok in SERVER_APP_CO_THE_DUNG):
                    findings.append(Finding(
                        app, "ERROR",
                        f"{f.relative_to(d).as_posix()} import {mod!r} — app chi duoc "
                        f"dung {sorted(SERVER_APP_CO_THE_DUNG)} tu `server`. Can them "
                        "thi bo sung vao HOP DONG truoc, dung di vong."))

        route_files = ([d / "routes.py"] if (d / "routes.py").is_file()
                       else sorted((d / "routes").glob("*.py"))
                       if (d / "routes").is_dir() else [])
        if route_files:
            # Kiem an toan la thuoc tinh cua CA app -> doc gop.
            rtext = "\n".join(_read(f) for f in route_files)
            # 🔴 `require_login` KHONG phai cach duy nhat de doi dang nhap.
            #
            #    `server/deps.py:99` `require_operator` **goi chinh
            #    `require_login`** (dong 103) roi them mot chot nua: khong phai
            #    quan tri vien thi 403. Tuc no MANH HON, khong phai yeu hon.
            #
            # ⛔ Truoc 2026-09-02 chot nay khop chuoi `require_login` va bao
            #    WARN cho `apps/qualitylab` — mot app `public=False`,
            #    `surface="admin"`, moi route deu `Depends(require_operator)`.
            #    Do la canh bao DUY NHAT ma linter phat ra tren ca 15 app, va
            #    no la DUONG TINH GIA.
            #
            # ⭐ Cai gia khong phai mot dong thua. Mot canh bao sai ton tai lau
            #    se day nguoi ta bo qua chinh cong cu phat ra no — roi toi luc
            #    no dung thi khong ai con nhin.
            #
            # ⚠️ Sua bang cach day chot BIET them mot guard, KHONG bang cach
            #    them ngoai le cho `qualitylab`. Mot ngoai le se song lau hon
            #    hoan canh sinh ra no; mot mo hinh dung thi khong can ngoai le.
            #    (`OPERATING_CONTRACT` §8: dung them luat de chua luat.)
            if not any(g in rtext for g in GUARD_DOI_DANG_NHAP):
                findings.append(Finding(
                    app, "WARN",
                    "routes.py khong thay guard doi dang nhap "
                    f"({'/'.join(GUARD_DOI_DANG_NHAP)})"))
            if "@router.post" in rtext and "verify_csrf_token" not in rtext:
                findings.append(Finding(app, "WARN",
                                        "co @router.post nhung khong thay verify_csrf_token (CSRF?)"))
            # Route serve file theo key -> phai guard co-lap user.
            if "{key:path}" in rtext and not re.search(r"u\.id|user_id|segs\[1\]", rtext):
                findings.append(Finding(app, "WARN",
                                        "route serve {key:path} khong thay guard user_id (co-lap?)"))

            # Tang nghiep vu: route phinh to = logic dang nam sai cho.
            #
            # Nguong tinh theo TUNG FILE, khong theo tong. Tach dung thi tong
            # con to hon ban dau (them docstring + import cho moi module) -
            # do chinh la muc dich: moi file nho lai. Do tong se phat dung cai
            # minh muon khuyen khich.
            qua_to = [(f, len(_read(f).splitlines()),
                       len(re.findall(r"^@router\.", _read(f), re.M)))
                      for f in route_files]
            qua_to = [(f, n, h) for f, n, h in qua_to
                      if n > MAX_ROUTES_LINES or h > MAX_ROUTES_HANDLERS]
            handlers = len(re.findall(r"^@router\.", rtext, re.M))
            has_layer = (d / "services").is_dir() or any(
                (d / f"{name}.py").is_file()
                for name in ("features", "cost", "service", "domain"))
            if qua_to:
                for f, n, h in qua_to:
                    findings.append(Finding(
                        app, "WARN",
                        f"{f.name} {n} dong / {h} handler vuot nguong "
                        f"{MAX_ROUTES_LINES}/{MAX_ROUTES_HANDLERS} - tach theo mien "
                        f"ra services/ (debug theo hang muc se de hon nhieu)"))
            elif handlers >= 12 and not has_layer and len(route_files) == 1:
                findings.append(Finding(
                    app, "WARN",
                    f"{handlers} handler nhung khong co services/ hay "
                    f"features.py - logic nghiep vu dang nam trong route?"))
    findings.extend(_doi_chieu_ban_khai(APPS))
    return findings


def main() -> int:
    strict = "--strict" in sys.argv
    fs = lint()
    errs = [f for f in fs if f.level == "ERROR"]
    warns = [f for f in fs if f.level == "WARN"]
    for f in fs:
        print(f)
    print(f"\nApps quet: {len([d for d in APPS.iterdir() if d.is_dir() and not d.name.startswith(('_','.')) and d.name not in SKIP_APPS])}"
          f" | ERROR: {len(errs)} | WARN: {len(warns)}")
    if errs or (strict and warns):
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
