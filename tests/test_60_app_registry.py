"""Hợp đồng app registry — thứ quyết định chi phí thêm app thứ 10.

Nếu hợp đồng này lỏng thì mỗi app mới lại phải sửa nền tảng một chút, và
đến app thứ năm thì không ai nhớ phải sửa những đâu. Các test dưới đây chốt
đúng những chỗ dễ trượt nhất.
"""
from __future__ import annotations

import pathlib

import pytest

from platform_core.registry import (
    AppManifest,
    NavEntry,
    RegistryError,
    _validate,
    credit_for,
    discover,
    job_type_owners,
    visible_on_surface,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


# ── quét app ───────────────────────────────────────────────────────────────

def test_discovers_every_app_folder():
    slugs = {a.slug for a in discover()}
    assert "thumbnail" in slugs
    assert "vps" in slugs


def test_bon_app_da_go_va_phai_o_nguyen_trang_thai_do():
    """Bốn app bị gỡ 2026-08-25 — `socialbot` (Q108), rồi `kichban`,
    `mediatools`, `demo`. Giữ cho chúng đã gỡ.

    Xoá mã thì dễ; **giữ cho nó ở trạng thái đã xoá** mới khó. Một app hồi sinh
    một nửa tệ hơn cả hai trạng thái, vì nó trông như dùng được rồi hỏng ở chỗ
    dùng — đúng bài học mà `test_52_desktop_removed` từng chốt cho giai đoạn
    desktop→web, và tệp đó nay đã đi cùng thứ nó canh.

    ⛔ Nếu phép kiểm này đỏ vì ai đó **cố ý** đưa socialbot về, thì việc đúng
       không phải sửa dòng này: đó là một quyết định sản phẩm, phải thêm dòng
       mới vào bảng quyết định trước (AGENTS.md mục 6).
    """
    slugs = {a.slug for a in discover()}
    for da_go in ("socialbot", "kichban", "mediatools", "demo"):
        assert da_go not in slugs, da_go
        assert not (ROOT / "apps" / da_go).exists(), da_go
    assert not (ROOT / "core").exists()
    assert not (ROOT / "utils").exists()
    assert not (ROOT / "server" / "services").exists()


def test_no_app_fails_to_load():
    broken = {a.slug: a.error for a in discover() if a.error}
    assert broken == {}, f"app nạp lỗi: {broken}"


def test_portfolio_surface_and_lifecycle_match_locked_decisions():
    apps = {a.slug: a.manifest for a in discover()}
    assert apps["qualitylab"].surface == "admin"
    assert apps["nexus"].surface == "customer"
    assert {apps[slug].lifecycle for slug in (
        "upscalevideo", "prompt_ai_ommi", "taovideo")} == {"released"}
    assert apps["thumbnail"].catalog_parent == "taoanh"
    assert apps["thumbnail"].job_types == ("thumbnail.generate",)
    customer_cards = [m for m in apps.values()
                      if m.surface == "customer" and not m.catalog_parent]
    assert customer_cards and all(m.capabilities for m in customer_cards)


def test_khong_app_nao_moc_mot_dong_nav_tro_vao_404():
    """⛔ BAT BIEN NAY SINH RA TU MOT LOI THAT, do 2026-08-26.

    `apps/ltt_llm` khai `surface="customer"`, khong khai `catalog_parent`, va
    khong co `routes.py`. Hau qua: `visible_on_surface(authenticated=True)` tra
    `True`, `nav_entries()` tu sinh mot dong tro vao `/ltt-llm`, va
    `GET /ltt-llm` tra **404** — mot link chet trong header cua **moi** khach da
    dang nhap, suot nhieu tuan, khong phep kiem nao thay.

    ⭐ Cai bay: `nav=()` KHONG co nghia la "khong co nav". `nav_entries()` sinh
       lai mot dong mac dinh khi app khong khai gi. Mot app "chua co giao dien"
       van moc mot dong nav.

    ⭐ Va dieu dang ghi hon ca loi: `apps/anhnoibo` DA tranh dung cai bay nay
       bang `catalog_parent`, va con VIET RA ly do trong chu thich. Bai hoc da
       duoc hoc va da duoc ghi — no chi chua bao gio thanh mot phep kiem.
       Do la khoang cach giua "da biet" va "da chot", va day la cho dong no.

    Phep kiem doi ung o `tools/lint_app_contract.py` chay ca trong `gate --quick`
    (che do bo pytest), nen bat bien nay duoc canh o hai cho.
    """
    hong = [a.slug for a in discover()
            if a.manifest is not None
            and visible_on_surface(a.manifest, authenticated=True)
            and a.router is None]
    assert hong == [], (
        f"App hien trong nav ma khong co router -> link 404: {hong}. "
        "Khai catalog_parent, hoac them routes.py.")


def test_every_apps_subfolder_has_a_manifest():
    """Một folder trong apps/ mà thiếu manifest.py sẽ bị bỏ qua HOÀN TOÀN im
    lặng — code có đó, route không bao giờ chạy, và rất khó nhận ra."""
    missing = [
        d.name for d in (ROOT / "apps").iterdir()
        if d.is_dir() and not d.name.startswith(("_", "."))
        and not (d / "manifest.py").exists()
    ]
    assert missing == [], f"thiếu manifest.py: {missing}"


# ── những va chạm im lặng ──────────────────────────────────────────────────

def test_route_prefixes_are_unique():
    """Hai app cùng prefix thì app nạp sau bị che mất và FastAPI không báo gì."""
    prefixes = [a.manifest.route_prefix.rstrip("/") for a in discover()]
    dupes = {p for p in prefixes if prefixes.count(p) > 1}
    assert not dupes, f"route_prefix trùng: {dupes}"


def test_slugs_are_unique():
    slugs = [a.slug for a in discover()]
    assert len(slugs) == len(set(slugs))


def test_job_types_are_unique_across_apps():
    """Hai app cùng nhận một job_type thì job chạy bằng handler nào là ngẫu
    nhiên theo thứ tự quét thư mục."""
    owners: dict = {}
    for a in discover():
        for jt in a.manifest.job_types:
            assert jt not in owners, \
                f"job_type {jt!r} bị cả {owners[jt]} và {a.slug} nhận"
            owners[jt] = a.slug
    assert job_type_owners() == owners


def test_registry_rejects_duplicate_prefix():
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/demo")
    with pytest.raises(RegistryError, match="route_prefix trùng"):
        _validate(m, seen_slugs=set(), seen_prefixes={"/demo"})


def test_registry_rejects_relative_prefix():
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="demo")
    with pytest.raises(RegistryError, match="phải bắt đầu bằng"):
        _validate(m, seen_slugs=set(), seen_prefixes=set())


@pytest.mark.parametrize(("field", "value"), [
    ("surface", "partner"), ("lifecycle", "beta"),
    ("capabilities", ("",)), ("catalog_parent", "bad-parent"),
])
def test_registry_rejects_unknown_product_state(field, value):
    kwargs = {field: value}
    m = AppManifest(slug="x", display_name="X", route_prefix="/x", **kwargs)
    with pytest.raises(RegistryError, match=field):
        _validate(m, seen_slugs=set(), seen_prefixes=set())


def test_surface_visibility_separates_customer_admin_and_runtime():
    customer = AppManifest(slug="c", display_name="C", route_prefix="/c")
    private = AppManifest(slug="p", display_name="P", route_prefix="/p",
                          public=False)
    admin = AppManifest(slug="a", display_name="A", route_prefix="/a",
                        surface="admin")
    runtime = AppManifest(slug="r", display_name="R", route_prefix="/r",
                          surface="runtime")
    child = AppManifest(slug="child", display_name="Child", route_prefix="/child",
                        catalog_parent="c")
    assert visible_on_surface(customer, authenticated=False)
    assert not visible_on_surface(private, authenticated=False)
    assert visible_on_surface(private, authenticated=True)
    assert not visible_on_surface(admin, authenticated=True, operator=False)
    assert visible_on_surface(admin, authenticated=True, operator=True)
    assert not visible_on_surface(runtime, authenticated=True, operator=True)
    assert not visible_on_surface(child, authenticated=True, operator=True)


def test_validate_tu_choi_job_types_thieu_credit_cost():
    """W1.6: app sinh job mà thiếu credit_cost bị chặn NGAY lúc discover (fail
    som), không đợi tới lúc submit mới vỡ."""
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    job_types=("x.do",), credit_cost=None)
    with pytest.raises(RegistryError, match="credit_cost"):
        _validate(m, seen_slugs=set(), seen_prefixes=set(), seen_job_types=set())


def test_validate_tu_choi_job_type_trung():
    """W1.6: job_type trùng giữa hai app bị chặn ngay (worker phân job theo
    job_type — trùng thì quyết toán nhầm giá)."""
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    job_types=("dup.jt",), credit_cost=lambda p: 1)
    with pytest.raises(RegistryError, match="job_type trùng"):
        _validate(m, seen_slugs=set(), seen_prefixes=set(),
                  seen_job_types={"dup.jt"})


# ── credit: chỗ mất tiền ───────────────────────────────────────────────────

def test_credit_is_computed_from_params_not_fixed(app_thu):
    """Giá phải là hàm của tham số. Seedance tính theo giây video × độ phân
    giải; một hằng số sẽ tính sai ngay từ job đầu tiên.

    Dùng app THỬ tổng hợp (`conftest.app_thu`) chứ không dùng một app có thật:
    trước 2026-08-25 phép kiểm này gọi `demo.reverse`, và đó là một trong những
    sợi dây làm `apps/demo` thành thứ không xoá được.
    """
    small = credit_for(app_thu.job_type, {"text": "x" * 50})
    big = credit_for(app_thu.job_type, {"text": "x" * 5000})
    assert big > small


def test_unknown_job_type_is_refused_not_free():
    """Job không tra được giá phải bị TỪ CHỐI. Trả 0 nghĩa là chạy miễn phí
    ngoài ý muốn — với API tính theo giây thì đó là mất tiền thật."""
    with pytest.raises(RegistryError, match="không app nào nhận"):
        credit_for("khong.ton.tai", {})


def test_job_type_without_price_is_refused():
    """App khai job_types nhưng quên credit_cost cũng phải bị chặn."""
    apps = [type("L", (), {
        "manifest": AppManifest(slug="p", display_name="P", route_prefix="/p",
                                job_types=("p.run",), credit_cost=None),
        "slug": "p", "router": None, "error": "",
    })()]
    with pytest.raises(RegistryError, match="chưa khai credit_cost"):
        credit_for("p.run", {}, apps=apps)


# ── điều hướng ─────────────────────────────────────────────────────────────

def test_every_enabled_app_is_reachable_from_the_sidebar():
    for a in discover():
        if not a.manifest.enabled:
            continue
        entries = a.manifest.nav_entries()
        assert entries, f"{a.slug} không có mục nav -> không ai vào được"
        for e in entries:
            assert e.path.startswith("/"), f"{a.slug}: {e.path} không tuyệt đối"


def test_manifest_without_nav_gets_a_default_entry():
    m = AppManifest(slug="x", display_name="App X", route_prefix="/x")
    entries = m.nav_entries()
    assert len(entries) == 1
    assert entries[0].path == "/x"


def test_declared_nav_is_used_as_is():
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    nav=(NavEntry("A", "/x/a"), NavEntry("B", "/x/b")))
    assert [e.path for e in m.nav_entries()] == ["/x/a", "/x/b"]


# ── app hỏng không được làm sập nền tảng ───────────────────────────────────

def test_a_broken_app_does_not_break_discovery(tmp_path):
    """Nếu một app lỗi làm sập cả nền tảng thì bạn không vào được để xem app
    nào lỗi. Nó phải được ghi lại kèm lý do."""
    apps = tmp_path / "apps"
    (apps / "bad").mkdir(parents=True)
    (apps / "bad" / "__init__.py").write_text("", encoding="utf-8")
    (apps / "bad" / "manifest.py").write_text(
        "raise RuntimeError('hỏng có chủ ý')", encoding="utf-8")

    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        result = discover(apps_dir=apps)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("apps.bad.manifest", None)

    assert len(result) == 1
    assert result[0].error
    assert result[0].manifest.enabled is False


# ── app sở hữu bảng CSDL riêng (hợp đồng R0) ───────────────────────────────

def _app_with_tables(root, slug, *, prefix, table):
    """Dựng một app tạm có tables.py để thử hợp đồng."""
    apps = root / "apps"
    (apps / slug).mkdir(parents=True)
    (apps / slug / "__init__.py").write_text("", encoding="utf-8")
    (apps / slug / "manifest.py").write_text(
        "from platform_core.registry import AppManifest\n"
        f"MANIFEST = AppManifest(slug={slug!r}, display_name='X',\n"
        f"    route_prefix='/{slug}', table_prefix={prefix!r})\n",
        encoding="utf-8")
    (apps / slug / "tables.py").write_text(
        "from sqlalchemy import String\n"
        "from sqlalchemy.orm import Mapped, mapped_column\n"
        "from platform_core.db import Base\n"
        f"class _T(Base):\n"
        f"    __tablename__ = {table!r}\n"
        "    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n",
        encoding="utf-8")
    return apps


def _load_isolated(root, apps, slug):
    """Nạp tables của app tạm rồi dọn sạch metadata để không rò sang test khác.

    Gói `apps` đã được import từ repo thật nên `apps.<slug>` tạm không phân giải
    được qua sys.path. Nối thêm thư mục tạm vào `apps.__path__` là cách chuẩn để
    một gói tìm module con ở nhiều nơi.
    """
    import sys

    import apps as apps_pkg
    from platform_core.db import Base
    from platform_core.registry import load_app_tables

    before = set(Base.metadata.tables)
    apps_pkg.__path__.append(str(apps))
    try:
        return load_app_tables(apps_dir=apps)
    finally:
        apps_pkg.__path__.remove(str(apps))
        for name in set(Base.metadata.tables) - before:
            Base.metadata.remove(Base.metadata.tables[name])
        sys.modules.pop(f"apps.{slug}.manifest", None)
        sys.modules.pop(f"apps.{slug}.tables", None)
        sys.modules.pop(f"apps.{slug}", None)


def test_app_can_own_tables_when_it_declares_a_prefix(tmp_path):
    """App cần bảng thật phải khai được ngay trong app, không phải đem model
    bỏ vào platform_core (AGENTS.md mục 60: bổ sung hợp đồng, không đi vòng)."""
    apps = _app_with_tables(tmp_path, "withtables", prefix="wt", table="wt_thing")
    assert _load_isolated(tmp_path, apps, "withtables") == ["withtables"]


def test_app_tables_must_use_the_declared_prefix(tmp_path):
    """Bảng lạc tiền tố chỉ lộ ra khi Alembic sinh migration xoá nhầm bảng của
    app khác — lúc đó đã quá muộn."""
    apps = _app_with_tables(tmp_path, "strayname", prefix="sn", table="other_thing")
    with pytest.raises(RegistryError, match="other_thing"):
        _load_isolated(tmp_path, apps, "strayname")


def test_app_tables_require_a_declared_prefix(tmp_path):
    apps = _app_with_tables(tmp_path, "noprefix", prefix="", table="np_thing")
    with pytest.raises(RegistryError, match="table_prefix"):
        _load_isolated(tmp_path, apps, "noprefix")


def test_table_prefix_must_be_unique_across_apps():
    """Hai app cùng tiền tố thì ghi đè bảng của nhau, Alembic chỉ thấy một cái."""
    seen_slugs, seen_prefixes, seen_tables = set(), set(), {"dup"}
    m = AppManifest(slug="second", display_name="S", route_prefix="/second",
                    table_prefix="dup")
    with pytest.raises(RegistryError, match="table_prefix"):
        _validate(m, seen_slugs, seen_prefixes, set(), set(), seen_tables)


def test_alembic_env_loads_app_tables():
    """Quên nạp thì autogenerate coi bảng của app là bảng lạ và sinh lệnh XOÁ."""
    text = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "load_app_tables()" in text


# ── nền tảng không được biết app nào tồn tại ───────────────────────────────

def test_platform_never_imports_an_app():
    """Chiều phụ thuộc chỉ đi một hướng. Nền tảng import app là quay lại đúng
    thứ registry sinh ra để tránh."""
    import ast

    offenders = []
    for path in (ROOT / "platform_core").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n == "apps" or n.startswith("apps."):
                    offenders.append(f"{path.name}:{node.lineno} -> {n}")
    assert offenders == [], f"platform_core import app: {offenders}"


def test_no_app_slug_is_hardcoded_in_the_platform():
    """Tên app xuất hiện trong code nền tảng là dấu hiệu registry bị đi vòng."""
    # ``agent`` is also the architectural namespace mandated by Q39/Q40
    # (AgentRun, platform_core.agent), so substring matching cannot distinguish
    # legitimate core terminology from a hardcoded app slug. Route/app wiring
    # for it is still covered by the same manifest/mount contract tests.
    #
    # ``nexus`` is the same shape, from Q93: device identity belongs to the
    # account rather than to an app, so the capability lives in
    # ``platform_core.nexus`` and ``apps/nexus`` is only the customer-facing
    # skin over it. The platform names the *capability*, never the app — which
    # this test cannot tell apart by substring.
    #
    # ``ltt_llm`` is the third of the same shape, and the most literal: the
    # platform DECLARES a provider with that exact id in
    # ``platform_core/providers.py``, and ``apps/ltt_llm`` is the customer-facing
    # skin that sells it. Every hit this test reports is that provider id — a
    # metric name (``ltt_llm:cong_im_lang``), a cascade order, an example. None
    # of them reaches for the app.
    #
    # ⚠️ The naming is still backwards, and that is worth saying out loud: the
    #    image side got this right (provider ``ltt_image`` + app ``anhnoibo``),
    #    so its provider id is NOT an app slug and this check stays sharp for it.
    #    Renaming ``apps/ltt_llm`` -> ``apps/chatnoibo`` would remove the
    #    exemption entirely and make the two house-model apps symmetric. It is
    #    deliberately NOT done here: that app is live and billing real customers,
    #    and the slug is baked into persisted ``job_type`` rows. It is a
    #    migration, not a rename, and it belongs in its own change.
    #
    # Adding a name here is not free: it blinds this check to that string, so a
    # genuine hardcoded reference to that app would slip through. It is only
    # correct when the platform owns the namespace and the app is named after
    # it, not the other way round.
    #
    # What still covers the real risk: ``test_platform_core_never_imports_apps``
    # above. Blinding a substring does not let ``platform_core`` import the app.
    slugs = [a.slug for a in discover()
             if a.slug not in ("agent", "nexus", "ltt_llm")]

    # 🔴 TÊN BẢNG KHÔNG PHẢI TÊN APP — và bỏ qua điều đó làm hai bánh cóc đánh nhau.
    #
    #    `test_211` **bắt buộc** `platform_core/public_api/governance.py` phải nêu
    #    tên **mọi** bảng, kể cả bảng riêng của app: không kê được thì không trả lời
    #    được câu *"các anh giữ gì về tôi"*. Nhưng app nào có `table_prefix` trùng
    #    slug thì tên bảng của nó chứa slug — và chốt này đỏ.
    #
    #    Đã xảy ra thật với `apps/vps` (`table_prefix="vps"` ⇒ `vps_instance`,
    #    `vps_ip`, …). Hai chốt đều đúng; thứ sai là phép so chuỗi thô.
    #
    # ⛔ Cách sai là miễn trừ slug `vps` — nền tảng KHÔNG sở hữu namespace đó, nên
    #    miễn trừ sẽ làm mù chốt với một tham chiếu app thật. Cách đúng: bóc **tên
    #    bảng thật** (lấy từ metadata, không phải danh sách gõ tay) ra khỏi văn bản
    #    trước khi dò. Một chuỗi `"vps"` đứng trơ vẫn bị bắt.
    from platform_core.db import Base
    from platform_core.registry import load_app_tables
    import platform_core.models  # noqa: F401
    load_app_tables()
    ten_bang = sorted(Base.metadata.tables, key=len, reverse=True)

    offenders = []
    for path in (ROOT / "platform_core").rglob("*.py"):
        text = _ma_thuc_thi(path.read_text(encoding="utf-8"))
        for bang in ten_bang:
            text = text.replace(bang, "<bang>")
        for slug in slugs:
            if slug in text:
                offenders.append(f"{path.name}: {slug!r}")
    assert offenders == [], f"tên app bị viết cứng: {offenders}"


def test_boc_ten_bang_KHONG_lam_mu_chot():
    """Chốt trên bóc tên bảng ra trước khi dò. Đây là chỗ chứng minh nó không
    bóc quá tay: một slug đứng trơ, hoặc một `apps.<slug>`, vẫn phải bị bắt."""
    from platform_core.db import Base
    from platform_core.registry import load_app_tables
    import platform_core.models  # noqa: F401
    load_app_tables()
    ten_bang = sorted(Base.metadata.tables, key=len, reverse=True)

    def con_lai(text):
        for bang in ten_bang:
            text = text.replace(bang, "<bang>")
        return text

    assert "vps" not in con_lai('"vps_instance", "vps_ip"')
    assert "vps" in con_lai('if app.slug == "vps":'), (
        "phep boc da an ca tham chieu app that — chot bi lam mu"
    )


def _ma_thuc_thi(nguon: str) -> str:
    """Bỏ chú thích và docstring, giữ nguyên phần còn lại.

    Vì sao lọc chứ không so nguyên văn: cái test này chốt *"nền tảng không đi vòng
    qua registry"*, và đi vòng là một hành vi của **mã chạy được**. Một dòng
    docstring trỏ tới `apps/<tên>/...` để người đọc biết chỗ tham chiếu **không đi
    vòng cái gì cả** — nó chỉ là tài liệu.

    Đây **không phải** một miễn trừ theo tên app. Miễn trừ theo tên thì làm mù hẳn
    phép kiểm với chuỗi đó ở mọi nơi; cách này vẫn bắt slug trong lệnh, trong điều
    kiện, và trong **chuỗi ký tự thường** — xem hai test ngay dưới.
    """
    import ast
    import io as _io
    import tokenize

    # Vi tri cua tung docstring (module/class/ham) — chi nhung cai do la "prose".
    vi_tri = set()
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return nguon
    for node in ast.walk(cay):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        than = getattr(node, "body", None)
        if (than and isinstance(than[0], ast.Expr)
                and isinstance(than[0].value, ast.Constant)
                and isinstance(than[0].value.value, str)):
            vi_tri.add((than[0].value.lineno, than[0].value.col_offset))

    ra = []
    for tok in tokenize.generate_tokens(_io.StringIO(nguon).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and tok.start in vi_tri:
            continue
        ra.append(tok.string)
    return chr(10).join(ra)


def _nguon(*dong: str) -> str:
    """Ghép các dòng nguồn. Dùng `chr(10)` chứ không viết escape xuống dòng —
    những tệp này đôi khi được sinh ra bằng script, và một tầng thoát chuỗi nữa
    là dấu xuống dòng biến thành ký tự thật, làm cả tệp không parse được."""
    return chr(10).join(dong) + chr(10)


def test_bo_quet_van_bat_slug_trong_MA_CHAY_DUOC():
    """Bánh cóc cho chính bộ lọc trên. Nếu nó nới tay quá thì phép kiểm ở trên
    thành vô dụng mà vẫn xanh."""
    ma = _ma_thuc_thi(_nguon('x = 1',
                             'if slug == "taovideo":',
                             '    pass'))
    assert "taovideo" in ma


def test_bo_quet_KHONG_bat_slug_trong_docstring_hay_chu_thich():
    ma = _ma_thuc_thi(_nguon('"""Xem apps/taovideo/translate.py."""',
                             '# cung nhu apps/autosubvideo/jobs.py',
                             'x = 1'))
    assert "taovideo" not in ma and "autosubvideo" not in ma


def test_bo_quet_van_bat_slug_trong_CHUOI_THUONG():
    """Chuỗi thường KHÁC docstring: `TEN = "taovideo"` đúng là đi vòng registry."""
    assert "taovideo" in _ma_thuc_thi(_nguon('TEN = "taovideo"'))


# ── app thử: handler phải NÉM khi thất bại ─────────────────────────────────

def test_handler_phai_nem_loi_khi_that_bai(app_thu):
    """Handler trả về êm ru khi thất bại nghĩa là job "thành công" và credit đã
    giữ vẫn bị trừ — khách trả tiền cho một kết quả không có.

    Trước 2026-08-25 phép kiểm này gọi `apps/demo/jobs.py`. App đó đã bị gỡ, và
    tính chất được chốt ở đây **không thuộc về app nào** — nó là một điều khoản
    của hợp đồng handler. Nên nó chuyển sang app thử tổng hợp.
    """
    assert app_thu.handle({"text": "abc"})["output"] == "cba"
    with pytest.raises(ValueError):
        app_thu.handle({"text": "   "})
