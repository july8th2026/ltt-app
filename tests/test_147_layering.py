"""Phân tầng: `platform_core` không được phụ thuộc vào `server`.

`platform_core` là nền tảng — worker, script CLI và test đều dùng nó mà không
dựng web. Cho nó import `server` biến sơ đồ tầng thành hình tròn và làm
`platform_core` không dùng được nếu thiếu tầng web.

Audit control-plane 2026-08-06 tìm thấy đúng một vi phạm:
`platform_core/users.py` import `server.auth.password_hashing`. Module đó thuần
stdlib nên đã chuyển hẳn xuống `platform_core/password_hashing.py`. Test này
canh để không có cái thứ hai.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPORT = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)", re.M)


def _modules_imported_by(folder: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in (ROOT / folder).rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        # Bỏ import trong hàm/thử-bắt-lỗi? KHÔNG — import muộn vẫn là phụ thuộc.
        hit = {m.split(".")[0] for m in IMPORT.findall(text)}
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        out[rel] = hit
    return out


def test_platform_core_never_imports_server():
    offenders = {
        name: sorted(mods & {"server"})
        for name, mods in _modules_imported_by("platform_core").items()
        if "server" in mods
    }
    assert offenders == {}, (
        f"platform_core phụ thuộc ngược lên server: {offenders}")


def test_platform_core_never_imports_apps():
    """Nền tảng không được biết app nào tồn tại — registry là đường duy nhất."""
    offenders = {
        name: sorted(mods & {"apps"})
        for name, mods in _modules_imported_by("platform_core").items()
        if "apps" in mods
    }
    assert offenders == {}, f"platform_core biết tới apps: {offenders}"


#: `server` được phép biết tên app nào — và câu trả lời gần như là KHÔNG.
#:
#: 🔴 Hợp đồng app khai chiều `app → server` (`SERVER_APP_CO_THE_DUNG`) và cả
#:    chiều `app → app` (`APP_DUOC_DUNG_APP`), nhưng trước 2026-09-02 **bỏ
#:    trống chiều `server → app`**. Đo được năm cạnh, và không cạnh nào vi phạm
#:    một luật — vì chưa có luật nào.
#:
#: ⭐ Hai cạnh của trang giá đã gỡ bằng cách **bổ sung hợp đồng**, không phải
#:    bằng cách bỏ lời gọi: `AppManifest.bang_gia` + `registry.bang_gia_cong_khai()`.
#:    App vẫn sở hữu giá của mình; `server` chỉ còn thu thập.
#:
#: ⚠️ Ba cạnh còn lại (`server/api/streaming.py` → `apps.ltt_llm`) là NGÂN SÁCH
#:    TOKEN và ánh xạ tên model — một mối quan tâm khác, chưa có hình dạng hợp
#:    đồng rõ. Ghi thành nợ CÓ TÊN ở đây thay vì để nó vô hình.
SERVER_BIET_APP_DUOC_PHEP = {
    ("server/api/streaming.py", "ltt_llm"),
}


def test_server_khong_biet_ten_app_ngoai_danh_sach_da_khai():
    """⛔ `registry.py` mở đầu bằng: *"Nền tảng KHÔNG được biết tên app nào tồn tại."*

    Chốt này làm câu đó thành thứ đo được. Mỗi cạnh mới phải được KHAI ở trên —
    và khai một cạnh là một quyết định kiến trúc, không phải một dòng cho tiện.
    """
    import re

    goc = pathlib.Path(__file__).resolve().parent.parent
    mau = re.compile(r"(?:from|import)\s+apps\.([a-z_][a-z0-9_]*)")
    thay = set()
    for tep in sorted((goc / "server").rglob("*.py")):
        txt = tep.read_text(encoding="utf-8", errors="replace")
        for dong in txt.splitlines():
            d = dong.strip()
            if d.startswith("#") or d.startswith("*"):
                continue          # chú thích kể lại chuyện cũ thì không tính
            for m in mau.finditer(d):
                thay.add((tep.relative_to(goc).as_posix(), m.group(1)))
    la = thay - SERVER_BIET_APP_DUOC_PHEP
    assert not la, (
        f"server biet ten app ma khong khai: {sorted(la)}. "
        "Dua thu app cung cap vao `AppManifest` roi doc qua registry — "
        "hoac khai canh nay vao `SERVER_BIET_APP_DUOC_PHEP` kem ly do.")
    # Chiều ngược: khai một cạnh rồi gỡ mà quên xoá khai thì danh sách thành
    # một lời nói dối về hiện trạng.
    thua = SERVER_BIET_APP_DUOC_PHEP - thay
    assert not thua, f"khai thua trong SERVER_BIET_APP_DUOC_PHEP: {sorted(thua)}"


#: Ngoại lệ ĐƯỢC GHI RÕ, không phải chỗ im lặng cho qua.
#:
#: `taovideo` gọi `upscalevideo.service.submit_upscale_job` cho nút "Nâng cấp
#: 4K" trên video Seedance. Đây là dạng phụ thuộc chéo ít hại nhất: hàm đó tự
#: nộp job qua `submit_with_credit` với `job_type` của chính upscalevideo, nên
#: tiền và hàng đợi vẫn đi đúng đường nền tảng; nó chỉ tránh nhân đôi
#: `build_params`.
#:
#: Vẫn là nợ: gỡ hay đổi tên `upscalevideo` sẽ làm gãy `taovideo`. Đường đúng là
#: ToolSpec handoff như `prompt_ai_ommi` đang dùng. Chưa đổi vì đây là luồng
#: TRẢ TIỀN đang chạy, và đổi nó cần một cổng kiểm riêng chứ không kèm vào một
#: đợt sửa mười hạng mục.
#: ── Auto Scan Video ────────────────────────────────────────────────────────
#:
#: Sáu cạnh, nhưng **hai loại khác hẳn nhau**. Gộp chúng làm một dòng ngoại lệ
#: sẽ giấu mất điều đáng biết: ba cạnh đầu không phải nợ, ba cạnh sau thì có.
#:
#: ⭐ LOẠI A — `asv_media` · `asv_gpu` · `asv_voice` → `auto_scan_video`
#:
#:    Ba cái này **không phải app độc lập**. Chúng khai `surface="runtime"` +
#:    `catalog_parent="auto_scan_video"`, không có thẻ catalog, không có mục
#:    nav, không bán riêng. Chúng tồn tại vì một lý do kỹ thuật duy nhất: quyền
#:    nhặt job lọc theo **APP** chứ không theo `job_type`
#:    (`platform_core/jobs.py:158-164`), nên một app khai đủ cả bốn năng lực sẽ
#:    chỉ chạy được trên worker có đủ cả bốn — tức là không bao giờ.
#:
#:    ⇒ Câu "gỡ một app là gãy app kia" **không áp dụng**: gỡ `auto_scan_video`
#:      không làm gãy một sản phẩm khác, nó gỡ chính sản phẩm này. Đây là import
#:      TRONG một sản phẩm, chỉ trông giống import chéo vì hợp đồng app buộc mỗi
#:      làn worker phải là một thư mục riêng.
#:
#: ⚠️ LOẠI B — `auto_scan_video` → `ltt_llm` · `autosubvideo` · `ltt_voice`
#:
#:    Đây MỚI là nợ, và đúng cùng loại với `taovideo → upscalevideo` ở trên:
#:    đổi tên hay gỡ một trong ba app kia sẽ làm gãy Auto Scan Video.
#:
#:      dich_thuat.py        -> ltt_llm       điều phối model dịch
#:      giai_doan_chep_loi.py-> autosubvideo  bộ chạy ASR
#:      giong_noi.py         -> ltt_voice     chuẩn hoá văn bản + TTS
#:
#:    Nhưng nó **khác** `taovideo → upscalevideo` ở một điểm quyết định đường
#:    sửa: ba lời gọi này phần lớn là **hàm thuần**, không phải nộp job. Ví dụ
#:    `ltt_voice.text_pipeline.chuan_hoa` là chuẩn hoá tiếng Việt — một mối lo
#:    dùng chung đã bị đặt nhầm chỗ, nó thuộc `platform_core` chứ không thuộc
#:    một app. Nên đường ra đúng ở đây **không phải** ToolSpec handoff (handoff
#:    một hàm thuần chỉ thêm một vòng hàng đợi cho một phép biến đổi chuỗi) mà
#:    là **nâng phần dùng chung lên `platform_core`**.
#:
#:    Chưa làm trong pha 14 vì việc đó sửa `platform_core/` VÀ ba app **đang
#:    phục vụ khách trả tiền** của lane khác — đúng thứ `CLAUDE.md` bảo dừng
#:    lại và nói rõ thay vì kèm vào một đợt mười hạng mục. Ghi ở RISK-14-01.
#: 🔴 DẪN XUẤT, ⛔ không chép. Đo 24/09 nói vì sao.
#:
#:    Cùng một sự thật từng được khai ở **BA** chỗ: hợp đồng app
#:    (`tools/lint_app_contract.py::APP_DUOC_DUNG_APP`), danh sách này, và
#:    `test_421::VO_TUONG_THICH`. Ngày 22–23/09 hai cạnh mới ra đời
#:    (`auto_scan_video → asv_gpu`, `asv_gpu → ltt_voice`); tác giả khai vào
#:    hợp đồng — kèm bề mặt và lý do — và `test_308` đo bằng AST rồi chốt
#:    `thực tế == APP_DUOC_DUNG_APP`, nên **hợp đồng đúng và có người canh**.
#:
#: ⛔ Chỉ danh sách NÀY lạc hậu, và nó còn **sai chiều**: nó có
#:    `("asv_gpu", "auto_scan_video")` mà thiếu chiều ngược lại — dù hai chiều
#:    là cùng một quan hệ (bốn thư mục `asv_*` là MỘT sản phẩm).
#:
#: ⇒ Chữa gốc, ⛔ không chữa triệu chứng: bản sao thứ ba **biến mất**. Nay chỉ
#:   còn một sổ, và sổ đó đã có phép kiểm đối chiếu với thực tế.
#:
#: ── Phân loại (giữ lại, vì nó là thứ `APP_DUOC_DUNG_APP` không nói) ────────
#:
#: ⭐ LOẠI A — `asv_media` · `asv_gpu` · `asv_voice` ↔ `auto_scan_video`
#:
#:    **Không phải app độc lập.** `surface="runtime"`,
#:    `catalog_parent="auto_scan_video"`, không thẻ catalog, không mục nav,
#:    không bán riêng. Chúng là thư mục riêng vì đúng một lý do kỹ thuật:
#:    quyền nhặt job lọc theo **APP**, không theo `job_type`
#:    (`platform_core/jobs.py:158-164`). ⇒ Câu *"gỡ một app là gãy app kia"*
#:    không áp dụng — đây là import TRONG một sản phẩm.
#:
#: ⚠️ LOẠI B — `auto_scan_video` → `ltt_llm` · `autosubvideo` · `ltt_voice`,
#:    và (từ 22/09) `asv_gpu` → `ltt_voice`. Đây MỚI là nợ. Ghi ở RISK-14-01.
#:
#: 🔴 ĐƯỜNG RA của loại B — **HOÃN, có điều kiện mở lại** (chủ dự án, 24/09):
#:
#:    Đường đúng là nâng `ltt_voice.text_pipeline` lên `platform_core` (một mối
#:    lo dùng chung đặt nhầm chỗ), ⛔ không phải ToolSpec handoff — handoff một
#:    hàm thuần chỉ thêm một vòng hàng đợi cho một phép biến đổi chuỗi.
#:
#:    ⛔ Giá **hiện tại** là thứ chặn: việc đó đổi `PHIEN_BAN_CHUAN_HOA`, mà
#:       `asv_gpu.do_luong.giong.PHIEN_BAN` gộp hằng ấy vào vân tay bộ đo ⇒
#:       **mọi số WER đã đo mất gốc so sánh**. Cộng thêm: sửa `platform_core/`
#:       VÀ `ltt_voice` — một app **đang phục vụ khách trả tiền**.
#:    ⭐ MỞ LẠI khi có một mốc WER mới cần dựng dù sao: lúc đó cái giá đắt nhất
#:       đã phải trả vì lý do khác.
#:
#: ⛔ ĐƯỜNG ĐÃ LOẠI — gộp bốn thư mục `asv_*` làm một app: chặn bởi
#:    `platform_core/jobs.py:158-164`. Một app khai `requires=("ffmpeg","gpu")`
#:    trên đội hình chia làn sẽ **`queued` mãi mà không lỗi nào báo**
#:    (`test_389...::test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi` tái
#:    hiện bằng một app thật). Chế độ hỏng đó là lý do đủ.
def _cap_cheo_duoc_phep() -> set[tuple[str, str]]:
    """MỘT nguồn: hợp đồng app. `test_308` canh cho nó khớp thực tế."""
    from tools.lint_app_contract import APP_DUOC_DUNG_APP

    return set(APP_DUOC_DUNG_APP)


CROSS_APP_ALLOWED = _cap_cheo_duoc_phep()


def _import_cheo(duoc_phep) -> dict[str, set[str]]:
    """Cạnh `apps/<a>/… → apps.<b>` không nằm trong `duoc_phep`."""
    offenders: dict[str, set[str]] = {}
    for path in (ROOT / "apps").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        owner = path.relative_to(ROOT / "apps").parts[0]
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?:from|import)\s+apps\.([a-z_０-９\w]+)", text):
            other = match.group(1)
            if other != owner and (owner, other) not in duoc_phep:
                offenders.setdefault(
                    str(path.relative_to(ROOT)).replace("\\", "/"), set()).add(other)
    return offenders


def test_apps_never_import_another_app():
    """App gọi thẳng app khác thì gỡ một app là gãy app kia. Trao đổi giữa app
    phải đi qua ToolSpec/job của nền tảng."""
    offenders = _import_cheo(_cap_cheo_duoc_phep())
    assert offenders == {}, f"app import chéo: { {k: sorted(v) for k, v in offenders.items()} }"


#: Cạnh dùng làm CÔNG TẮC cho hai phép tiêm dưới đây. Nó phải là một cạnh THẬT
#: đang tồn tại trong mã, nếu không cả hai phép chỉ đo một danh sách rỗng.
_CANH_THU = ("asv_gpu", "ltt_voice")
_TEP_THU = "apps/asv_gpu/do_luong/chuan_hoa_loi.py"


def test_CONG_TAC_o_HOP_DONG_lat_phep_kiem_nay_DO_roi_XANH(monkeypatch):
    """⭐ Bằng chứng **nối**, hai chiều, trên CÙNG một tệp trong CÙNG một lượt.

    ⛔ Không có phép này thì "dẫn xuất" chỉ là chép một giá trị lúc nạp module —
       và một bản chép thì lệch lại được, đúng như bản sao thứ ba đã lệch.

    Chỉ MỘT thứ đổi giữa hai vế: một dòng trong `APP_DUOC_DUNG_APP`.
    """
    from tools import lint_app_contract as lint

    # vế ĐỎ — gỡ dòng khỏi sổ
    monkeypatch.delitem(lint.APP_DUOC_DUNG_APP, _CANH_THU)
    xau = _import_cheo(_cap_cheo_duoc_phep())
    assert _TEP_THU in xau and _CANH_THU[1] in xau[_TEP_THU], (
        f"bot {_CANH_THU} khoi hop dong ma phep kiem khong thay: {sorted(xau)}")

    # vế XANH — trả dòng về, không đổi gì khác
    monkeypatch.undo()
    assert _CANH_THU in lint.APP_DUOC_DUNG_APP, "monkeypatch chua tra lai sổ"
    assert _TEP_THU not in _import_cheo(_cap_cheo_duoc_phep()), (
        f"tra {_CANH_THU} ve hop dong ma phep kiem van ke ten {_TEP_THU}")


def test_tap_dan_xuat_DOC_so_moi_luot_chu_khong_chup_luc_NAP_module(monkeypatch):
    """Một dòng MỚI thêm vào sổ phải hiện ra ngay ở tập dẫn xuất.

    ⛔ Nếu `_cap_cheo_duoc_phep()` chụp ảnh lúc import, phép này im lặng hỏng —
       và đó đúng là cách một bản sao ra đời.
    """
    from tools import lint_app_contract as lint

    gia = ("ltt_voice", "asv_gpu")          # chiều chưa ai khai, và không có trong mã
    assert gia not in lint.APP_DUOC_DUNG_APP, "canh gia nay da co that — doi canh khac"
    assert gia not in _cap_cheo_duoc_phep()
    monkeypatch.setitem(lint.APP_DUOC_DUNG_APP, gia, set())
    assert gia in _cap_cheo_duoc_phep(), "them vao hop dong ma tap dan xuat khong doi"


def test_apps_do_not_import_private_server_helpers():
    """Dấu gạch dưới nghĩa là 'không phải API công khai'. App phải hỏi qua hợp
    đồng (`server.deps`), không thò tay vào ruột module khác.

    Khớp theo câu IMPORT chứ không theo chuỗi con: `user_is_admin` là biến hợp
    lệ của một app và chứa `_is_admin` bên trong — bản đầu của test này báo đỏ
    giả vì điều đó.
    """
    private_import = re.compile(r"from\s+server[\w.]*\s+import\s+(.+)")
    offenders = {}
    for path in (ROOT / "apps").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for match in private_import.finditer(path.read_text(encoding="utf-8")):
            names = [n.strip() for n in match.group(1).split(",")]
            hidden = [n for n in names if n.startswith("_")]
            if hidden:
                offenders[str(path.relative_to(ROOT)).replace("\\", "/")] = hidden
    assert offenders == {}, f"app import hàm private của server: {offenders}"


def test_moi_module_mien_deu_duoc_import_trong_routes_init():
    """Tách `routes.py` thành package tạo một cách hỏng mới: thêm module miền
    mà quên import vào `__init__` thì handler KHÔNG đăng ký, route biến mất
    lặng lẽ — server vẫn khởi động, chỉ là app thiếu tính năng.

    Không kiểm bằng cách đếm route (số sẽ đổi mỗi lần thêm tính năng), mà kiểm
    đúng điều dễ quên: mọi file `.py` trong package đều được `__init__` nhắc tới.
    """
    packages = [p for p in (ROOT / "apps").glob("*/routes") if p.is_dir()]
    assert packages, "chưa app nào tách routes thành package — test này thành vô nghĩa"
    for pkg in packages:
        init = (pkg / "__init__.py").read_text(encoding="utf-8")
        app = pkg.parent.name
        for module in sorted(pkg.glob("*.py")):
            if module.name == "__init__.py":
                continue
            assert re.search(rf"\b{re.escape(module.stem)}\b", init), (
                f"{app}: {module.name} không được import trong routes/__init__.py — "
                f"handler trong đó sẽ không đăng ký và route sẽ biến mất lặng lẽ")


def test_routes_package_van_xuat_ra_router():
    """Nền tảng chỉ biết một thứ: biến `router`. Tách file không được đổi điều đó."""
    import importlib
    for pkg in [p for p in (ROOT / "apps").glob("*/routes") if p.is_dir()]:
        app = pkg.parent.name
        module = importlib.import_module(f"apps.{app}.routes")
        assert hasattr(module, "router"), f"apps/{app}/routes/ không xuất ra `router`"
        assert module.router.routes, f"apps/{app}/routes/ có router nhưng rỗng route"


def test_platform_core_workflow_khong_hardcode_app_slug():
    """F2 (final-review.md, plan 01a): Global Constraint "không hardcode tên
    app/tool trong `platform_core/`" không có phép kiểm nào canh —
    `test_967` (bánh cóc được viện dẫn) chỉ quét `frontend/agent-canvas/src`,
    không đụng tới `platform_core`. Đây là bánh cóc CHỊ EM cho backend, cùng
    tinh thần `test_967`: quét `platform_core/workflow/*.py` tìm
    `app_slug="<literal>"` viết tay — mọi chỗ cần biết slug app phải tra qua
    `registry.job_type_owners()` (như `tao_run.chu_dong_co()`), không viết
    thẳng tên app ở tầng nền.
    """
    mau = re.compile(r'app_slug\s*=\s*["\'][a-z_][a-z0-9_]*["\']')
    offenders = {}
    for path in sorted((ROOT / "platform_core" / "workflow").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits = mau.findall(text)
        if hits:
            offenders[str(path.relative_to(ROOT)).replace("\\", "/")] = hits
    assert offenders == {}, (
        f"platform_core/workflow hardcode app_slug bằng tay: {offenders} — "
        "tra qua registry.job_type_owners() thay vì viết tên app trực tiếp "
        "(mẫu: platform_core/workflow/tao_run.py::chu_dong_co)")


def test_nen_tang_va_app_khong_phu_thuoc_core_legacy():
    """`core/` **đã bị xoá hẳn 2026-08-25** (Q108). Đừng dựng lại nó.

    Lịch sử, vì nó giải thích vì sao phép kiểm này vẫn còn giá trị sau khi thứ
    nó canh đã biến mất: `core/` là 15.046 dòng thừa kế từ thời sản phẩm còn là
    bot FB/TikTok. Trước 2026-08-06 **mọi** app đều dính nó — không phải vì
    chúng cần, mà vì `platform_core/storage.py` gọi `core.runtime_paths`, kéo cả
    cây theo. Một sợi dây duy nhất khiến bản đồ phụ thuộc nói dối: nhìn vào
    tưởng `core/` là hạ tầng chung, thực ra 99,4% của nó không phục vụ app nào
    đang bán (xem docs/APP_AUDIT/control-plane/2026-08-06/04_BAN_DO_CORE.md).

    H22 cắt sợi dây đó; Q108 xoá luôn phần còn lại. Phép kiểm giữ nguyên vì nó
    nay canh một điều khác và vẫn đáng canh: **thứ nhiều nơi cần là hạ tầng, và
    hạ tầng thuộc về `platform_core/`** — đừng tạo một `core/` thứ hai dưới tên
    khác.
    """
    offenders = {}
    for area in ("apps", "platform_core"):
        for path in (ROOT / area).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits = re.findall(r"^\s*(?:from|import)\s+(core(?:\.[\w.]+)?)", text, re.M)
            if hits:
                offenders[path.relative_to(ROOT).as_posix()] = sorted(set(hits))
    assert offenders == {}, (
        f"nền tảng/app đang phụ thuộc core/ legacy: {offenders} — "
        f"thứ dùng chung thì đặt ở platform_core/")
