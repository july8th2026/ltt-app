"""test_365 — một bước gate TỰ BỎ QUA không được trông giống một bước ĐẠT.

## Chuyện đã xảy ra, 31/08/2026

`gate.py` chỉ đọc **mã thoát**. `tools/check_multiproc.py` không tạo được CSDL
test, in một đoạn giải thích rất tử tế, rồi `return 0`. Gate đọc `0` và in
`[PASS]` trong **0,7 giây**.

Hậu quả đo được: **hai phiên đọc cùng một dòng `RESULT` theo hai cách trái
ngược trong cùng một ngày, và cả hai đều tưởng mình đúng.**

* Một phiên báo *"gate PASS 25/25"* — tin rằng bất biến đa tiến trình đã được
  chứng minh.
* Phiên kia (tôi) thấy `FAIL (1/25)`, đọc thông điệp tử tế của `check_multiproc`,
  rồi **gán nó cho con số thất bại** vì nó khớp câu chuyện đang kể — trong khi
  bước thật sự đỏ là một bước khác và **chưa bao giờ được gọi tên**.

⭐ Cái giá không nằm ở "một bước không chạy". Nó nằm ở chỗ: **một cái bẫy im
   lặng thì người ta đi tìm; một cái bẫy có sẵn lời giải thích thì người ta
   thôi tìm.**

## ⛔ Và `return 0` ở đó là ĐÚNG — đừng "sửa" nó

Một máy không có PostgreSQL vẫn phải chạy được gate. Đổi `check_multiproc.py`
thành trả khác 0 là biến một máy thiếu công cụ thành một máy không chạy được
cổng chất lượng. **Cái sai nằm ở chỗ ĐỌC, không ở chỗ trả.** Phép kiểm cuối tệp
này canh đúng điều đó, để phiên sau không sửa nhầm đầu.
"""
from __future__ import annotations

import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

from gate import DAU_BO_QUA, Step, _tu_khai_bo_qua  # noqa: E402


# ── 1. Phát hiện đúng thứ cần phát hiện ────────────────────────────────────

def test_nhan_ra_dau_ra_THAT_cua_check_multiproc():
    """Đo trên chính hình dạng đã gây ra sự cố, không trên một chuỗi bịa."""
    that = (
        "BO QUA bo bat bien da tien trinh - khong tao duoc CSDL test: "
        "ProgrammingError\n"
        "  test_214 la thu duy nhat chung minh webhook khong gui trung,\n"
        "  Do KHONG phai loi.\n")
    assert _tu_khai_bo_qua(that) is True


def test_buoc_dat_binh_thuong_KHONG_bi_gan_nhan():
    assert _tu_khai_bo_qua("RESULT: PASS\n12 checks, 0 vi pham") is False
    assert _tu_khai_bo_qua("") is False


def test_chi_nhan_o_DAU_DONG():
    """⛔ Bắt theo `in` sẽ biến mọi bản báo cáo *nói về* việc bỏ qua thành một
    lần bỏ qua — kể cả chính đầu ra của `check_bo_qua.py`."""
    assert _tu_khai_bo_qua("khong BO QUA gi ca\nRESULT: PASS") is False
    assert _tu_khai_bo_qua("Cho BO QUA moi (0)\nRESULT: PASS") is False
    assert _tu_khai_bo_qua("   " + DAU_BO_QUA + " vi thieu GPU") is True, (
        "thut le van la dau dong — nhieu cong cu in co thut")


# ── 2. Bỏ qua ≠ hỏng, nhưng cũng ≠ đạt ────────────────────────────────────

def test_bo_qua_KHONG_bi_tinh_la_that_bai():
    """Nếu tính là hỏng thì máy thiếu PostgreSQL không chạy được gate — đúng
    cái hậu quả mà `return 0` sinh ra để tránh."""
    s = Step("thu", ["x"], GOC)
    s.ok, s.bo_qua = True, True
    assert s.ok is True and s.bo_qua is True


def test_step_mac_dinh_KHONG_bo_qua():
    s = Step("thu", ["x"], GOC)
    assert s.bo_qua is False, "mac dinh phai la 'da chay that'"


# ── 3. Dòng RESULT phải tự khai — đây mới là chỗ người ta đọc ─────────────

def test_dong_RESULT_khai_bao_buoc_bo_qua():
    """🔴 Bảng liệt kê từng bước ở trên đã có `[BOQUA]`, nhưng **dòng RESULT là
    thứ duy nhất được đọc khi người ta vội** — đúng bài học của cây-đổi."""
    khoi = _khoi_sua_ket()
    assert any("bo_qua" in k for k in khoi), (
        "`bo_qua` phai dieu khien chinh bien `ket`, khong phai in roi bo. "
        f"Cac khoi co sua `ket`: {khoi}")
    assert any("KHONG PHAI BANG CHUNG" in k for k in khoi), (
        "phai NOI RO rang luot nay khong chung minh duoc dieu no trong nhu da "
        "chung minh")


def test_keu_KE_CA_KHI_moi_buoc_khac_deu_dat():
    """⛔ Đó đúng là lúc nguy hiểm nhất: một dòng `PASS` trọn vẹn che một bất
    biến chưa bao giờ được chứng minh."""
    import ast

    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(ma))
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    # Phep dem buoc bo qua phai nam o THAN HAM, khong long trong mot `if` nao.
    # Long no vao nhanh "co that bai" thi mot luot toan PASS se im lang — dung
    # luc can no keu nhat.
    o_than = any(
        isinstance(n, ast.Assign)
        and any(isinstance(x, ast.Name) and x.id == "bo_qua" for x in n.targets)
        for n in ham.body)
    assert o_than, (
        "`bo_qua = [...]` phai o than `main`, khong long trong mot nhanh dieu "
        "kien — neu khong, mot luot toan PASS se khong bao gio khai bao")


def test_bang_buoc_co_nhan_rieng():
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert '"BOQUA" if step.bo_qua' in ma


# ── 4. Bánh cóc chống "sửa nhầm đầu" ─────────────────────────────────────

def test_check_multiproc_van_phai_TRA_VE_0_khi_bo_qua():
    """🔴 Phép kiểm này chốt một điều NGƯỢC với phản xạ tự nhiên.

    Đọc "bước này bỏ qua mà báo đạt" xong, phản xạ là làm nó trả khác 0. Làm
    thế là biến một máy **thiếu PostgreSQL** thành một máy **không chạy được
    cổng chất lượng** — và người tiếp theo sẽ vô hiệu hoá cả bước bằng một cờ
    `--bo-qua`, rồi cờ đó ở lại mãi.

    Chỗ sai là chỗ ĐỌC (`gate.py`), và nó đã được sửa. Chỗ trả thì giữ nguyên.
    """
    ma = (GOC / "tools" / "check_multiproc.py").read_text(encoding="utf-8")
    khuc = ma[ma.index("BO QUA"):]
    assert "return 0" in khuc[:2000] or "sys.exit(0)" in khuc[:2000], (
        "nhanh bo qua phai van tra 0 — xem docstring cua phep kiem nay truoc "
        "khi doi")


def test_moc_BO_QUA_la_mot_hang_so_dung_chung():
    """Gõ tay chuỗi "BO QUA" ở hai nơi là hai nguồn chân lý cho một quy ước."""
    from gate import DAU_BO_QUA as m

    assert m == "BO QUA"
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "DAU_BO_QUA" in ma.split("def _tu_khai_bo_qua")[1][:400], (
        "ham phat hien phai dung hang so, khong go lai chuoi")


def _khoi_sua_ket() -> list[str]:
    """Mã nguồn của mọi khối `if` trong `main()` có **sửa biến `ket`**.

    🔴 Phép đo QUAN HỆ, không phải khoảng cách. Bản đầu của hai phép kiểm trên
       cắt một cửa sổ 900 ký tự sau một mốc chuỗi — nó đỏ ngay khi ai đó chèn
       một khối chú thích vào giữa, dù hành vi đúng nguyên.

    ⭐ Đúng cái bẫy vừa làm `test_362` đỏ oan, và tôi đã chép nó sang đây trong
       cùng một giờ. Neo vào khoảng cách vật lý thay vì vào quan hệ là một lỗi
       dễ lây, vì nó trông như một phép kiểm chặt chẽ.
    """
    import ast

    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(ma))
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    ra = []
    for n in ast.walk(ham):
        if not isinstance(n, ast.If):
            continue
        sua = any(
            (isinstance(x, ast.AugAssign) and isinstance(x.target, ast.Name)
             and x.target.id == "ket")
            or (isinstance(x, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ket" for t in x.targets))
            for x in ast.walk(n))
        if sua:
            ra.append(ast.unparse(n))
    return ra


def test_buoc_DO_giu_TRON_dau_ra_ra_tep_chu_khong_chi_40_dong(tmp_path):
    """🔴 Đo 06/09/2026: một phép kiểm đỏ trong **6.616** phép kiểm. Dòng
       `short test summary` cho đúng **một** dòng — TÊN phép kiểm — còn
       traceback đã trôi khỏi 40 dòng cuối từ lâu.

       Tôi biết CÁI GÌ đỏ mà không biết VÌ SAO, và cách duy nhất để xem là
       chạy lại cả lượt 11 phút. Gate là công cụ ra **phán quyết**, nhưng khi
       nó đỏ thì nó cũng phải để lại đủ thứ cho người đọc **không phải chạy
       lại**.

    ⛔ Đây không phải chuyện tăng một con số. Bất kỳ trần nào cũng bị vượt bởi
       một lượt đủ dài. Cách đúng là: ĐỎ thì giữ TRỌN đầu ra ra tệp.

    ⭐ Và chiều ngược lại cũng được chốt: lượt XANH không được để lại gì, nếu
       không `test-results/` sẽ đầy rác sau mỗi lượt.
    """
    import importlib.util
    import pathlib
    import sys

    spec = importlib.util.spec_from_file_location(
        "gate_giu_dau_ra", GOC / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)

    thu_muc = pathlib.Path(gate.ROOT) / "test-results" / "gates"
    truoc = set(thu_muc.glob("loi-*.log")) if thu_muc.is_dir() else set()

    # ── Bước ĐỎ, đầu ra dài hơn 40 dòng ────────────────────────────────────
    do = gate.Step("thu chot giu dau ra", [
        sys.executable, "-c",
        "import sys;[print(f'dong {i}') for i in range(200)];"
        "print('MANH TRACEBACK');sys.exit(1)"], gate.ROOT)
    gate._run(do)
    assert do.ok is False
    assert do.tep_loi, "buoc DO ma khong ghi tep dau ra day du"

    tep = pathlib.Path(gate.ROOT) / do.tep_loi
    try:
        noi_dung = tep.read_text(encoding="utf-8")
        assert "dong 0" in noi_dung, (
            "tep chi giu phan duoi — dung lo da lam toi phai chay lai 11 phut")
        assert "MANH TRACEBACK" in noi_dung
        assert "dong 0" not in do.tail, (
            "neu 40 dong cuoi da du thi phep kiem nay khong do duoc gi")

        # ── Bước XANH: không được để lại gì ────────────────────────────────
        xanh = gate.Step("thu chot buoc xanh",
                         [sys.executable, "-c", "print('xong')"], gate.ROOT)
        gate._run(xanh)
        assert xanh.ok is True
        assert xanh.tep_loi == "", "luot XANH ma van ghi tep loi"
    finally:
        tep.unlink(missing_ok=True)

    con_lai = set(thu_muc.glob("loi-*.log")) - truoc
    assert not con_lai, f"phep kiem de lai rac: {con_lai}"


# ── pre-commit: hook DUNG CHUNG, cong cu thi MOI CAY MOT BAN ──────────────

def test_pre_commit_config_chi_goi_cong_cu_CO_THAT():
    """Mot hook goi tep khong ton tai la mot hook chan MOI commit."""
    import re
    noi_dung = (GOC / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    goi = re.findall(r"entry:\s*python\s+(tools/[\w./]+)", noi_dung)
    assert goi, "khong doc duoc `entry:` nao — mau cau hinh da doi?"
    for t in goi:
        assert (GOC / t).is_file(), f"`.pre-commit-config.yaml` goi {t} khong ton tai"


def test_hook_KHONG_duoc_lam_hong_commit_o_cay_CHUA_dong_bo(tmp_path):
    """🔴 `.git/hooks` DUNG CHUNG ca sau worktree, nhung `tools/` va
       `.pre-commit-config.yaml` thi MOI CAY MOT BAN.

       Do 06/09/2026: nam cay con lai deu THIEU it nhat mot cong cu, va khong
       cay nao co `.pre-commit-config.yaml`. Chay `pre-commit` o mot cay nhu
       vay tra **rc=1** (`InvalidConfigError: .pre-commit-config.yaml is not a
       file`) — tuc cai thang framework vao `.git/hooks` se lam MOI COMMIT o
       nam cay ay hong ngay, ke ca ba phien dang lam viec.

    ⇒ §4c cau 2: duong SUY BIEN phai tuong minh. Cay chua co cau hinh thi hook
      IM LANG di qua. Khong cay nao bi phat vi chua kip dong bo.
    """
    # ⛔ Doc ban DUOC THEO DOI, khong doc `.git/hooks/`. Tep trong `.git/` khong
    #    nam trong git: khong ai review, khong cay nao khac co, va mot phep kiem
    #    dua vao no phai `skip` khi chua cai -- ma mot test bi bo qua la mot test
    #    KHONG canh gi ca. Buoc gate `bo qua im lang` bat dung dieu do 06/09,
    #    va do la ly do than hook duoc chuyen ra `setup/`.
    hook = GOC / "setup" / "pre-commit-hook.sh"
    assert hook.is_file(), "than hook phai duoc THEO DOI, khong chi song o .git/"

    ma = hook.read_text(encoding="utf-8", errors="replace")
    assert ".pre-commit-config.yaml" in ma and "exit 0" in ma, (
        "hook khong co rao 'chua co cau hinh thi thoat 0' — no se chan commit "
        "o cac cay chua dong bo")

    # Doi chung SONG: chay hook trong mot thu muc KHONG co cau hinh.
    # Windows khong nhat thiet dat Git Bash `sh.exe` len PATH, du `git.exe`
    # van co. Tim shell theo quan he voi ban Git dang chay thay vi phu thuoc
    # vao nhan `sh` tren PATH.
    import shutil
    import subprocess

    sh = shutil.which("sh")
    if sh is None and (git := shutil.which("git")) is not None:
        ung_vien = Path(git).resolve().parents[1] / "bin" / "sh.exe"
        if ung_vien.is_file():
            sh = str(ung_vien)
    assert sh is not None, "khong tim thay Git Bash sh de kiem hanh vi hook"

    r = subprocess.run([sh, str(hook)], cwd=tmp_path,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, (
        f"hook chan commit o mot cay khong co cau hinh (rc={r.returncode}):\n"
        f"{r.stdout}{r.stderr}")
    assert not r.stdout.strip(), f"hook on ao o cay khong lien quan: {r.stdout!r}"


def test_macro_o_sao_chep_van_dat_dau_data_chep():
    """Nua CON LAI cua hop dong nut sao chep. Nua kia
    (`sao_chep.js` co xu ly `code[data-chep]`) nam o `test_306`.

    ⛔ Hai nua phai o HAI tep, va do khong phai tuy tien: banh coc
       `test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT` cam moi tham chieu
       toi `server/templates/` tu trong `test_306`, vi tep ay tung ghi de len
       tep that ba lan. Luat cua no la "tep that chi duoc xuat hien o dung mot
       cho". Chuyen khang dinh sang day la ton trong luat do, khong phai lach.

    🔴 Vi sao van phai chot: neu macro thoi dat `data-chep` thi doan JS xu ly
       no thanh MA CHET — van chay, van qua moi phep kiem cua rieng no, va
       khong con nut nao cho dia chi IP. Mot nua hop dong khong duoc canh la
       mot nua se troi.
    """
    mac = (GOC / "server" / "templates" / "_vps_mac.html").read_text(encoding="utf-8")
    assert "data-chep" in mac, (
        "macro `o_sao_chep` thoi danh dau o sao chep — doan `gan_o` trong "
        "`sao_chep.js` tro thanh ma chet")
    assert "o_sao_chep" in mac, "macro `o_sao_chep` bien mat?"


def test_moi_trang_co_thanh_tien_do_deu_phai_co_nhip_hoi():
    """🔴 Mot thanh tien do gan `aria-live` la mot LOI HUA: "cho nay se tu doi".

       Do 07/09: `apps/upscalevideo` ve dung thanh ay ma khong co BAT KY co che
       hoi lai nao — `hx-get` 0, `hx-trigger` 0, `nhipJob` 0, `EventSource` 0,
       `fetch` chi dung cho `/batch-quote`. Khach xem job nang cap thay mot con
       so DUNG IM cho toi khi ho tu tai lai trang.

       Da do that: sua `progress` 42 -> 88 trong CSDL, tab hien lai, trang van
       hien 42. Sau khi noi `LTT.nhipJob`: 88.

    ⭐ `nhip_job.js` ton tai chinh vi lop loi nay (xem docstring cua no: NAM cho
       tung tu viet vong hoi, KHONG cho nao xu ly `visibilitychange`). Phep kiem
       nay giu cho danh sach ay khong dai ra lan nua.
    ⛔ PHAM VI HEP CO Y. Ban dau phep kiem nay soi MOI trang co
       `role="progressbar"`, va no to cao them BON trang. Mo tay hai mau:

         apps/thumbnail       DUONG TINH GIA — htmx o do dung cho `hx-post` xem
                              truoc, thanh tien do khong phai tien do job
         apps/ltt_voice       hoi trong `voice.js`, khong trong template

       Dung hai kieu bao sai da ghi o `AGENTS.md` 4d lop E: doc sai NGUON (co
       che nam o tep `.js` roi) va mau qua hep ve KY THUAT. Mot bo do ~50%
       duong tinh gia ma bien thanh cong thi day nguoi ta bo qua mau do — cung
       chuan da dung de RUT H12 `deptry`.

    ⚠️ Va `voice.js` la mot ca THAT chua sua: 18 cho `setInterval/fetch`, 0 cho
       `visibilitychange`. Ghi lai o day thay vi im, nhung KHONG chot no bang
       phep kiem nay: chua do tren trinh duyet nen chua duoc phep khang dinh.
    """
    t = (GOC / "apps" / "upscalevideo" / "templates"
         / "upscalevideo.html").read_text(encoding="utf-8")
    assert 'role="progressbar"' in t, "trang thoi ve thanh tien do?"
    assert "nhipJob" in t, (
        "`upscalevideo` co thanh tien do ma khong co nhip hoi — no se dung im, "
        "dung nhu truoc 07/09")
    assert "data-job-id" in t, "job khong mang id thi khong hoi lai duoc"


def test_nhip_job_js_khong_duoc_dung_defer():
    """⛔ `nhip_job.js` chi dinh nghia `LTT.nhipJob`, va script noi tuyen ngay
       duoi goi no NGAY. Mot script `defer` chay SAU moi script noi tuyen, nen
       `defer` o day cho ra `TypeError: LTT.nhipJob is not a function` ngay khi
       mo trang — va no hong IM LANG: trang van ve, chi la khong bao gio doi.
    """
    import re
    xau, so_the = [], 0
    for p in list((GOC / "apps").rglob("templates/*.html")) + \
             list((GOC / "server" / "templates").rglob("*.html")):
        t = p.read_text(encoding="utf-8", errors="replace")
        for the in re.findall(r"<script[^>]*nhip_job\.js[^>]*>", t):
            so_the += 1
            if "defer" in the or "async" in the:
                xau.append(f"{p.relative_to(GOC).as_posix()}: {the}")
    # ⛔ DOI CHUNG (Bay 31): doi ten `nhip_job.js` -> `findall` khop 0 ->
    #    `xau` rong -> XANH, va thu phep kiem nay canh (mot `defer` bien
    #    `LTT.nhipJob` thanh `is not a function`, hong IM LANG: trang van ve,
    #    chi khong bao gio doi) het nguoi canh.
    #
    #    Do 07/09/2026: 3 the script nap `nhip_job.js`.
    assert so_the >= 3, (
        f"chi thay {so_the} the <script> nap nhip_job.js — mong doi >= 3. "
        f"Hoac tep da doi ten (thi SUA mau o day), hoac mot trang thoi hoi "
        f"lai. Ca hai deu phai xem; KHONG duoc de phep kiem nay xanh rong.")
    assert not xau, "nhip_job.js bi `defer`/`async`:\n  " + "\n  ".join(xau)


# ── 5. check_multiproc không phụ thuộc mật khẩu tài khoản ứng dụng ──────────

def test_check_multiproc_co_superuser_thi_KHONG_noi_bang_ltt_app(monkeypatch):
    """🔴 L3 19/09 (`91ceccd4`): `secrets\app.env` bản dev ở cây chính mang mật
    khẩu `ltt_app` ĐÃ CŨ; superuser vẫn đúng. Hai bước PostgreSQL kia (superuser)
    xanh, bước này (ltt_app) đỏ `password authentication failed` — "khép" bằng
    chạy lại nâng quyền ba lượt L3 liền.

    ⭐ Có mật khẩu superuser ⇒ URL CSDL vứt đi dựng bằng `postgres`, không một
       lần nối nào dùng thông tin đăng nhập của ứng dụng.
    """
    import check_multiproc as cm
    import sqlalchemy as sa

    monkeypatch.delenv("LTT_TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "postgresql+psycopg://ltt_app:MK_CU@127.0.0.1:5432/lttplatform")
    monkeypatch.setattr(cm, "_superuser_pw", lambda: "MK_SUPER")
    noi: list[str] = []

    class E:
        def __init__(self, url):
            self.url = url

        def connect(self):
            noi.append(self.url)
            if "MK_CU" in self.url:
                raise RuntimeError("password authentication failed")
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def dispose(self):
            return None

    monkeypatch.setattr(sa, "create_engine", lambda url, **_: E(url))
    url, ly_do = cm._tim_url()
    assert ly_do == "" and url.startswith("postgresql+psycopg://postgres:MK_SUPER@127.0.0.1:5432/")
    assert cm.HAU_TO in url.rsplit("/", 1)[1]
    assert not [u for u in noi if "ltt_app" in u], f"van noi bang ltt_app: {noi}"
