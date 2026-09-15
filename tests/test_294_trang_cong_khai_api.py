"""Tài liệu API và công cụ phải **lấy được mà không cần tài khoản**.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — ĐO 25/08 TRÊN PRODUCTION.

   Cả 18 trang của cổng lập trình viên đều trả `303` về `/login`, và hai thứ
   quan trọng nhất thì **không lấy được bằng bất kỳ đường nào**:

       /developers/docs -> 303        /tai/... (SDK)        -> 404 (khong co route)
       /developers/cli  -> 303        bo cai cong cu .exe   -> khong duoc nhac o dau

   Một người đang **cân nhắc** không đọc được một dòng hướng dẫn tích hợp nào
   trước khi tạo tài khoản. Đó là thứ tự ngược, và dự án đã học đúng bài này một
   lần rồi — trang giá cũ cũng nằm sau cổng đăng nhập và đã được tách ra
   `/gia-api`. Bài học chỉ được áp cho **riêng trang giá**.

⛔ VÀ MỘT LỖI TỆ HƠN: `dev_docs.html` liệt kê cho khách các **đường dẫn tệp
   trong kho mã của ta** (`docs/PUBLIC_API/…`, `sdk/python/…`). Khách không có
   kho mã. Trang trông như một mục lục đầy đủ — và chính điều đó làm **ta** tin
   rằng tài liệu đã tới tay khách.

⭐ RANH GIỚI: thứ giúp người ta **quyết định mua** thì công khai; thứ gắn với
   một **tài khoản** thì sau đăng nhập. Test này chốt vế thứ nhất.
"""
from __future__ import annotations

import importlib
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def khach():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app())


@pytest.fixture()
def tl():
    return importlib.import_module("server.routes.tai_lieu_api")


# ── Công khai thật, không phải "công khai nếu đã đăng nhập" ──────────────────

@pytest.mark.parametrize("duong", ["/huong-dan", "/huong-dan/cong-cu"])
def test_doc_duoc_khi_CHUA_dang_nhap(khach, duong):
    r = khach.get(duong, follow_redirects=False)
    assert r.status_code == 200, (
        f"{duong} tra {r.status_code} - mot nguoi dang can nhac khong doc duoc")


def test_trang_huong_dan_noi_du_ca_NAM_be_mat(khach):
    """Thiếu một bề mặt là một nhóm khách không biết mình cắm được."""
    noi = khach.get("/huong-dan").text
    for be_mat in ("Codex CLI", "Claude Code", "VS Code", "Claude Desktop"):
        assert be_mat in noi, f"trang huong dan khong nhac toi {be_mat}"


def test_trang_huong_dan_canh_bao_rao_chan_cua_claude_desktop(khach):
    """Hai rào chắn cho **cùng** một triệu chứng: bấm gửi, không có gì xảy ra.

    Thiếu lời cảnh báo này thì khách sẽ kết luận là API của ta hỏng.
    """
    from platform_core.public_api import examples
    noi = khach.get("/huong-dan").text
    for ten in examples.DESKTOP_MODELS:
        assert ten in noi, f"khong noi ten tuyen Claude Desktop {ten}"
    assert "Allow Chat" in noi
    assert "Disable Claude.ai sign-in" in noi


def test_desktop_manual_guide_uses_current_form_and_exact_routes(khach):
    import re
    from platform_core.public_api import examples
    from server.api.streaming import TUYEN_TUONG_THICH

    noi = khach.get("https://testserver/huong-dan").text
    khu = re.search(r'<section[^>]+id="khu-desktop".*?</section>', noi, re.S)
    assert khu is not None
    guide = khu.group(0)
    assert "1.52386.6" in guide
    assert "New configuration" in guide
    assert "Display name" in guide
    assert "Apply Changes" in guide and "Relaunch now" in guide
    assert "Organization-managed" in guide
    assert "Registry Editor" not in guide
    assert "HKCU" not in guide
    assert "đặt ở biến môi trường" not in guide
    values = dict(examples.claude_desktop_steps("https://testserver"))
    assert values["Gateway base URL"] == "https://testserver/api"
    assert values["Gateway auth scheme"] == "Bearer"
    assert values["Model discovery"] == "Off"
    assert values["Default to 1M context"] == "Off"
    assert values["Show estimated cost"] == "Off"
    assert values["Stream idle timeout"] == "600 seconds"
    assert values["Model 1 — Tier alias"] == "opus"
    assert values["Model 1 — Default for tier"] == "On"
    assert values["Model 2 — Tier alias"] == "haiku"
    assert values["Model 2 — Default for tier"] == "On"
    assert TUYEN_TUONG_THICH[values["Model 1 — Model ID"]] == "ltt-3.8"
    assert TUYEN_TUONG_THICH[values["Model 2 — Model ID"]] == "ltt-3.5"
    for field, value in values.items():
        assert field in guide and value in guide, (field, value)
    assert "Calculate 8 * 7" in guide and "Calculate 12 * 12" in guide
    assert "không chọn x-api-key" in guide
    assert "không tự cấp mọi scope" in guide
    from apps.ltt_llm import ngan_sach
    windows = [ngan_sach.cong_bo_cua(model) for model in ngan_sach.CUA_SO_THEO_MODEL]
    compacts = [ngan_sach.nen_cua(model) for model in ngan_sach.CUA_SO_THEO_MODEL]
    assert f"CLAUDE_CODE_MAX_CONTEXT_TOKENS={min(windows)}" in guide
    assert f"CLAUDE_CODE_AUTO_COMPACT_WINDOW={min(compacts)}" in guide
    assert f"CLAUDE_CODE_MAX_OUTPUT_TOKENS={ngan_sach.TOKEN_RA_TRAN}" in guide
    assert "MAX_MCP_OUTPUT_TOKENS=16384" in guide
    assert "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=1" in guide
    assert "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1" in guide
    assert "CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1" in guide
    assert "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1" in guide
    assert "ENABLE_TOOL_SEARCH=false" in guide
    assert "CLAUDE_CODE_DISABLE_1M_CONTEXT=1" not in guide
    assert "… / 138.7k" in guide and "… / 176.4k" in guide
    assert "Permission mode couldn't be changed" in guide
    assert "permissions.disableBypassPermissionsMode" in guide
    assert "131 tool" in guide and "98.678 token" in guide


def test_desktop_local_env_la_danh_sach_chuan_du_10_bien():
    """Q126: trang/tool không được tiếp tục bổ sung từng biến rời rạc.

    Soi cả tập chính xác thay vì chỉ hỏi vài dòng có mặt. Nếu Claude thêm một
    chốt mới trong tương lai, phép kiểm phải đỏ để buộc rà lại ma trận, tài liệu
    và test cùng một lần.
    """
    from platform_core.public_api import examples

    env = dict(examples.claude_local_env("ltt-3.8"))
    assert len(env) == 11
    assert set(env) == {
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
        "MAX_MCP_OUTPUT_TOKENS",
        "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS",
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH",
        "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
        "CLAUDE_CODE_MAX_RETRIES",
        "API_TIMEOUT_MS",
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK",
        "ENABLE_TOOL_SEARCH",
    }
    assert "CLAUDE_CODE_SUBAGENT_MODEL" not in env
    assert "CLAUDE_CODE_DISABLE_1M_CONTEXT" not in env
    assert env["CLAUDE_CODE_SUBAGENT_MODEL_FORCE"] == "1"
    assert dict(examples.claude_local_env("ltt-3.5")) == {
        **env,
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "209141",
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "176373",
    }


def test_claude_cli_ghim_du_moi_duong_chon_model():
    from platform_core.public_api import examples

    pins = dict(examples.claude_model_env("ltt-3.8"))
    assert set(pins) == {
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_FABLE_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
    }
    assert set(pins.values()) == {"ltt-3.8"}
    settings = examples.claude_code_settings("https://testserver")
    assert '"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"' in settings
    assert '"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"' in settings


def test_codex_manual_profiles_and_catalog_use_each_models_budget(khach):
    import json
    import tomllib
    from platform_core.public_api import examples
    from apps.ltt_llm import ngan_sach

    provider = tomllib.loads(examples.codex_config("https://testserver"))["model_providers"]["ltt"]
    assert provider["base_url"] == "https://testserver/api/v1"
    assert provider["wire_api"] == "responses"
    assert provider["env_key"] == "LTT_API_KEY"
    assert provider["requires_openai_auth"] is False
    assert provider["supports_websockets"] is False
    assert provider["request_max_retries"] == 1
    assert provider["stream_max_retries"] == 0
    assert provider["stream_idle_timeout_ms"] == 600000
    catalog = json.loads(examples.codex_catalog())["models"]
    assert [item["slug"] for item in catalog] == ["ltt-3.8", "ltt-3.5"]
    assert [item["display_name"] for item in catalog] == [
        "LTT 3.8 (Strong)", "LTT 3.5 (Fast)"]
    for item, internal in zip(catalog, ["qwen38-api", "qwen35-api"], strict=True):
        profile = tomllib.loads(examples.codex_profile(item["slug"]))
        desktop = tomllib.loads(examples.codex_desktop_config(
            "https://testserver", item["slug"]))
        context = ngan_sach.cong_bo_cua(internal)
        compact = ngan_sach.nen_cua(internal)
        assert profile["model_context_window"] == item["context_window"] == context
        assert profile["model_auto_compact_token_limit"] == item["auto_compact_token_limit"] == compact
        assert profile["model_auto_compact_token_limit_scope"] == "total"
        assert profile["tool_output_token_limit"] == 16384
        assert profile["agents"]["default_subagent_model"] == item["slug"]
        assert profile["agents"]["default_subagent_reasoning_effort"] == "low"
        assert profile["agents"]["max_concurrent_threads_per_session"] == 1
        assert desktop["model"] == item["slug"]
        assert desktop["model_provider"] == "ltt"
        assert desktop["model_context_window"] == context
        assert desktop["model_auto_compact_token_limit"] == compact
        assert desktop["model_auto_compact_token_limit_scope"] == "total"
        assert desktop["tool_output_token_limit"] == 16384
        assert desktop["model_providers"]["ltt"] == provider
        assert item["truncation_policy"] == {"mode": "tokens", "limit": 16384}
        assert item["supports_parallel_tool_calls"] is False
        assert "%USERPROFILE%" not in profile["model_catalog_json"]
    noi = khach.get("/huong-dan").text
    for value in ["ltt-fast.config.toml", "codex --profile ltt-fast", "YOUR_WINDOWS_USER",
                  "0.145.0", "0.146.0-alpha.3.1", "Calculate 6 * 7",
                  "26.721.11231.0", "model_auto_compact_token_limit_scope",
                  "tool_output_token_limit", "supports_websockets",
                  "max_concurrent_threads_per_session"]:
        assert value in noi


def test_codex_desktop_la_be_mat_rieng_va_chi_dan_dung_config_toml(khach):
    """Desktop uses root config; it must not inherit CLI profile instructions."""
    import tomllib

    from platform_core.public_api import examples

    surfaces = {item["ma"]: item for item in
                examples.be_mat_cam("https://app.lttstudios.com")}
    assert tuple(surfaces) == examples.BE_MAT_MA
    desktop = surfaces["codex-desktop"]
    assert desktop["dia_chi"] == "https://app.lttstudios.com/api/v1"
    assert desktop["models"] == (
        ("ltt-3.8", "LTT 3.8 (Strong)"),
        ("ltt-3.5", "LTT 3.5 (Fast)"),
    )
    assert [step[0] for step in desktop["buoc"]] == [
        "codex-catalog", "codex-desktop-strong", "codex-desktop-fast"]
    assert examples.vscode_codex_config(
        "https://app.lttstudios.com") == examples.codex_desktop_config(
            "https://app.lttstudios.com", "ltt-3.8")
    configs = [step[2] for step in desktop["buoc"][1:]]
    assert all("[profiles." not in value for value in configs)
    assert all("--profile" not in value for value in configs)
    assert all("[model_providers.ltt]" in value for value in configs)
    assert {tomllib.loads(value)["model"] for value in configs} == {
        "ltt-3.8", "ltt-3.5"}
    page = khach.get("/huong-dan").text
    assert "cùng CODEX_HOME" in page
    assert "không cần cắm Gateway hay MCP lần nữa" in page
    assert ".codex/config.toml" in page


def test_KHONG_con_duong_dan_kho_ma_trong_trang_cho_khach():
    """🔴 Chốt chính lỗi đã có: trang cho khách chỉ được trỏ tới **URL tải được**.

    Khách không có `docs/` và không có `sdk/` — nhắc tên chúng như một mục lục là
    đưa cho người ta một danh sách không mở được cái nào.
    """
    import re
    xau = []
    for ten in ("dev_docs.html", "huong_dan.html", "huong_dan_cong_cu.html",
                "_cam_chon.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        # ⚠️ Bỏ chú thích Jinja trước khi soi. `{# … #}` KHÔNG bao giờ được
        #    render, nên một đường dẫn kho mã nằm trong đó là ghi chú cho lập
        #    trình viên — đúng chỗ của nó. Bản đầu của test này quét cả chú
        #    thích và đỏ ngay trên chính đoạn giải thích vì sao không được làm
        #    thế: một phép đo bắt nhầm đối tượng nó định bảo vệ.
        noi = re.sub(r"\{#.*?#\}", "", noi, flags=re.S)
        for dau in ("docs/PUBLIC_API/", "sdk/python/", "sdk/typescript/",
                    "sdk/postman/"):
            if dau in noi:
                xau.append(f"{ten}: {dau}")
    assert not xau, f"trang cho khach van tro vao kho ma: {xau}"


# ── Tải được thật ────────────────────────────────────────────────────────────

def test_moi_goi_trong_danh_sach_deu_TAI_DUOC(khach, tl):
    """Quảng cáo một tệp mà không phục vụ được nó thì tệ hơn là không nhắc."""
    for ten in tl.GOI_TAI:
        r = khach.get(f"/tai/{ten}")
        assert r.status_code == 200, f"/tai/{ten} -> {r.status_code}"
        assert r.content, f"/tai/{ten} rong"


def test_ten_la_thi_404_chu_khong_doc_duoc_o_dia(khach):
    """Danh sách trắng làm việc đọc bậy **không thể**, chứ không phải 'khó'."""
    for bay in ("khong-co-that", "../../secrets/app.env", "..%2F..%2Fapp.env"):
        r = khach.get(f"/tai/{bay}")
        assert r.status_code in (404, 400), f"/tai/{bay} -> {r.status_code}"


def test_chua_phat_hanh_thi_503_chu_khong_phai_404(khach, tl, monkeypatch):
    """Hai chuyện khác nhau, và người trực phải phân biệt được từ log.

    `404` nghĩa là "đường dẫn sai". `503` nghĩa là "đường dẫn đúng, chưa có bản
    nào được thả vào thư mục phát hành" — thứ hai là việc của người vận hành.
    """
    monkeypatch.setattr(tl, "bo_cai_moi_nhat", lambda: None)
    assert khach.get("/tai/cong-cu-cam").status_code == 503
    monkeypatch.setattr(tl, "goi_bat_moi_nhat", lambda: None)
    assert khach.get("/tai/cong-cu-cam-bat").status_code == 503


def test_bam_tinh_TU_CHINH_TEP_dang_phuc_vu(tl, tmp_path, monkeypatch):
    """Không ký số thì băm là **thứ duy nhất** khách dùng để kiểm tệp.

    ⛔ Nên nó không được là một chuỗi gõ tay ở chỗ khác: đổi tệp mà băm không đổi
       là một lời bảo đảm sai, và sai đúng ở chỗ nguy hiểm nhất.
    """
    import hashlib
    thu_muc = tmp_path / "api_dist"
    thu_muc.mkdir()
    tep = thu_muc / "LTTStudios-CamCLI-Setup-9.9.9.exe"
    tep.write_bytes(b"noi dung gia")
    monkeypatch.setattr(tl, "_thu_muc_ban_phat", lambda: thu_muc)
    tl._BAM_DA_TINH.clear()

    kq = tl.bo_cai_moi_nhat()
    assert kq["phien_ban"] == "9.9.9"
    assert kq["sha256"] == hashlib.sha256(b"noi dung gia").hexdigest()

    # Doi noi dung -> bam PHAI doi theo.
    tep.write_bytes(b"noi dung khac han")
    assert tl.bo_cai_moi_nhat()["sha256"] == \
        hashlib.sha256(b"noi dung khac han").hexdigest()


def test_chon_ban_MOI_NHAT_khi_thu_muc_co_nhieu_ban(tl, tmp_path, monkeypatch):
    thu_muc = tmp_path / "api_dist"
    thu_muc.mkdir()
    for v in ("1.0.0", "1.10.0", "1.9.0"):
        (thu_muc / f"LTTStudios-CamCLI-Setup-{v}.exe").write_bytes(b"x")
    monkeypatch.setattr(tl, "_thu_muc_ban_phat", lambda: thu_muc)
    tl._BAM_DA_TINH.clear()
    # So sanh theo SO, khong theo chuoi: "1.9.0" > "1.10.0" neu so chuoi.
    assert tl.bo_cai_moi_nhat()["phien_ban"] == "1.10.0"


def test_goi_BAT_zip_co_bam_va_chon_ban_moi_nhat(tl, tmp_path, monkeypatch):
    import hashlib
    thu_muc = tmp_path / "api_dist"
    thu_muc.mkdir()
    for v in ("1.0.0", "1.1.0"):
        (thu_muc / f"LTTStudios-CamCLI-BAT-{v}.zip").write_bytes(v.encode())
    monkeypatch.setattr(tl, "_thu_muc_ban_phat", lambda: thu_muc)
    tl._BAM_DA_TINH.clear()
    kq = tl.goi_bat_moi_nhat()
    assert kq["phien_ban"] == "1.1.0"
    assert kq["sha256"] == hashlib.sha256(b"1.1.0").hexdigest()


# ── Một nguồn duy nhất cho hướng dẫn ────────────────────────────────────────

def test_hai_trang_dung_CHUNG_mot_than(khach):
    """Hai bản sao của cùng hướng dẫn là hai bản sẽ lệch, và bản lệch là bản
    khách đọc. Cùng lý do `/gia-api` lấy số từ `bang_gia()` thay vì gõ lại."""
    # ⚠️ Kiem TINH CHAT, khong ghim TEN tep: hai trang phai include CUNG MOT
    #    than. Ban cu ghim chuoi "_cam_than.html", nen khi than doi ten thanh
    #    "_cam_chon.html" (25/08) test do — trong khi tinh chat no bao ve van
    #    dung nguyen. Mot test do vi mot cai ten la mot test se bi sua cho im.
    import re
    than = {}
    for ten in ("dev_cli.html", "huong_dan.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        thay = re.findall(r'{%\s*include\s+"(_cam_[a-z_]+\.html)"', noi)
        assert thay, f"{ten} khong include than cam nao"
        than[ten] = set(thay)
    a, b = than["dev_cli.html"], than["huong_dan.html"]
    assert a == b, f"hai trang dung than KHAC nhau: {a} vs {b}"


def test_trang_cong_cu_hien_bam_va_KHONG_bao_tat_diet_virus(khach):
    noi = khach.get("/huong-dan/cong-cu").text
    assert "SHA-256" in noi
    assert "/tai/cong-cu-cam" in noi
    assert "/tai/cong-cu-cam-bat" in noi
    # ⛔ Bao khach tat phan mem diet virus la loi khuyen ta khong bao gio duoc dua.
    for cam in ("tắt phần mềm diệt virus", "tat dinh kem", "disable antivirus"):
        if cam == "tắt phần mềm diệt virus":
            # Trang CO nhac cum nay, nhung phai la loi HUA KHONG LAM.
            assert "KHÔNG bao giờ đề nghị" in noi or "KHÔNG" in noi


# ── Vỏ công khai phải có ĐỦ kiểu, không chỉ có class ─────────────────────────
#
# 🔴 ĐO 25/08 BẰNG CHROME THẬT. `ltt.css` không hề có luật `.card`, `.table` hay
#    `pre` — kiểu của chúng nằm NỘI TUYẾN trong `base.html`, tức chỉ vỏ đã đăng
#    nhập mới có. Mọi trang công khai render với class KHÔNG CÓ LUẬT NÀO KHỚP:
#    thẻ không tách nhau, bảng là mấy cột chữ trôi nổi, và khối mã là chữ trần —
#    trên đúng những trang tồn tại để khách CHÉP CẤU HÌNH.
#
# ⭐ Đối chứng làm rõ chẩn đoán: `/status/api` dùng `base.html` và đẹp chuẩn.
#    Cùng hệ thống thiết kế, khác ở chỗ có CSS hay không.

def test_ca_hai_vo_deu_include_kieu_dung_chung():
    """Một nguồn, hai vỏ. Bản sao thứ hai là bản sẽ lệch."""
    for ten in ("base.html", "base_public.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "_kieu_chung.html" in noi, (
            f"{ten} khong include kieu dung chung -> trang cua no se render voi "
            f"class khong co luat CSS nao khop")


@pytest.mark.parametrize("luat", [".card", "pre", ".table th", "table"])
def test_kieu_dung_chung_co_du_luat_can_thiet(luat):
    noi = (GOC / "server" / "templates" / "_kieu_chung.html").read_text(encoding="utf-8")
    assert luat in noi, f"thieu luat cho {luat}"


def test_khoi_ma_co_NEN_va_VIEN():
    """Khối mã trần lẫn vào văn xuôi thì khách phải tự tô để chép — và tô hụt
    một dòng trong `config.toml` thì lỗi hiện ra ở tận lúc gọi API."""
    noi = (GOC / "server" / "templates" / "_kieu_chung.html").read_text(encoding="utf-8")
    khoi = noi.split("pre {", 1)[1].split("}", 1)[0]
    assert "background" in khoi and "border" in khoi and "padding" in khoi
    assert "overflow-x" in khoi, "khong cuon ngang thi tran ra ngoai tren dien thoai"


def test_trang_cong_khai_render_RA_the_card_that(khach):
    """Chốt bằng HTML render, không phải bằng template: cả class lẫn luật."""
    r = khach.get("/huong-dan")
    assert 'class="card' in r.text
    assert "_kieu_chung" not in r.text, "include phai duoc RENDER, khong phai in ten ra"
    # Luat phai co mat trong chinh trang tra ve (style noi tuyen cua vo).
    assert ".card" in r.text and "border-radius" in r.text


def test_co_nut_sao_chep_va_no_khong_pha_trang_khi_thieu_JS():
    """Tăng cường dần: không JS thì không có nút, trang vẫn đọc được y nguyên."""
    js = (GOC / "server" / "static" / "sao_chep.js").read_text(encoding="utf-8")
    assert "navigator.clipboard" in js
    assert "isSecureContext" in js, (
        "thieu kiem ngu canh bao mat -> nut nem loi va KHONG NOI GI")
    # Nut duoc TAO bang JS, khong nam san trong template.
    for ten in ("_cam_chon.html", "huong_dan.html", "huong_dan_cong_cu.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "nut-chep" not in noi


def test_asset_ver_bam_CA_js_chu_khong_chi_css():
    """🔴 Trước 25/08 chỉ băm `ltt.css`, nên một tệp JS mới mang đúng số của CSS.

    Đổi JS mà không đổi CSS thì URL không đổi, và Cloudflare tiếp tục phục vụ bản
    cũ tới khi hết TTL — đúng cái bẫy quy tắc 6 của `CLAUDE.md` mô tả.
    """
    from server import templating
    assert "sao_chep.js" in templating.TAI_SAN_CO_VERSION
    assert "ltt.css" in templating.TAI_SAN_CO_VERSION


def test_thanh_tren_co_loi_vao_khu_API_cho_nguoi_CHUA_dang_nhap(khach):
    """Trước 25/08 lối duy nhất là mục trong menu tài khoản — chỉ hiện sau khi
    đăng nhập. Một lập trình viên đang cân nhắc không có đường nào tới tài liệu."""
    r = khach.get("/gia-api")
    assert 'href="/huong-dan"' in r.text


def test_gia_api_chi_co_MOT_h1(khach):
    """Hai `h1` là hai chủ đề ngang hàng — trang không nói được nó nói về cái gì."""
    r = khach.get("/gia-api")
    assert r.text.count("<h1") == 1, f"co {r.text.count('<h1')} the h1"


# ── Trang công khai phải giới thiệu CẢ HAI thứ ta bán ────────────────────────
#
# 🔴 ĐO 25/08 trên `/huong-dan`, trang công khai DUY NHẤT nói về tích hợp:
#      ltt_llm 16 lần · codex 24 · claude 39   ·   image.ltt 0 · quote 0
#    Ta bán hai thứ và giới thiệu một. Người chưa đăng ký thấy giá ảnh ở
#    /gia-api rồi hết đường — mọi hướng dẫn dùng ảnh nằm sau đăng nhập.

def test_trang_cong_khai_gioi_thieu_CA_tao_anh(khach):
    from platform_core.public_api import examples
    noi = khach.get("/huong-dan").text
    assert examples.ANH_TOOL in noi, "trang cong khai khong nhac toi cong cu tao anh"
    for che_do in ("t2i", "edit", "subject"):
        assert che_do in noi, f"thieu che do {che_do}"
    assert "/api/v1/quotes" in noi and "/api/v1/artifacts" in noi


def test_vi_du_anh_noi_dung_cho_lay_artifact(khach):
    """⛔ Chỗ một lượt gọi thật đã vấp: tài liệu nói `result`, thật là `outputs[]`."""
    noi = khach.get("/huong-dan").text
    assert "outputs[]" in noi or "outputs" in noi
    from platform_core.public_api import examples
    vi_du = examples.curl_anh_ba_buoc()
    assert "outputs" in vi_du
    assert "/api/v1/quotes" in vi_du and "/api/v1/jobs" in vi_du \
        and "/api/v1/artifacts" in vi_du
    assert "Idempotency-Key" in vi_du, (
        "thieu Idempotency-Key -> khach thu lai se tao job thu hai va tra tien hai lan")


def test_vi_du_anh_KHONG_chua_khoa_that(khach):
    """Không đoạn nào được chứa một chuỗi trông như khoá thật."""
    from platform_core.public_api import examples
    vi_du = examples.curl_anh_ba_buoc()
    assert "ltt_sk_" not in vi_du
    assert "$LTT_API_KEY" in vi_du


def test_noi_ro_138_giay_va_vi_sao_bat_buoc_bat_dong_bo(khach):
    """Khách cần con số để đặt timeout, và cần biết vì sao không có cửa đồng bộ."""
    noi = khach.get("/huong-dan").text
    assert "138" in noi
    assert "100" in noi, "phai noi tran 100 giay cua Cloudflare"
