"""`tools/cam_cli.py` — cắm vào rồi **gỡ ra phải trả đúng nguyên trạng**.

🔴 VÌ SAO CHỖ NGUY HIỂM LÀ ĐƯỜNG **GỠ**, KHÔNG PHẢI ĐƯỜNG CẮM.

   Cắm sai thì thấy ngay: gọi một lượt là biết. **Gỡ sai thì im lặng** — khách
   chạy `go`, công cụ in "đã gỡ", và thứ mất đi là **cấu hình riêng của họ**
   chứ không phải của ta. Không có triệu chứng nào cho tới lần sau họ mở Codex
   và thấy profile của mình biến mất.

⭐ NÊN PHÉP THỬ TRUNG TÂM Ở ĐÂY LÀ **BẰNG TỪNG BYTE**: cắm rồi gỡ thì tệp phải
   trở lại **y hệt** bản đầu. Không phải "trông giống", không phải "parse ra
   bằng nhau" — mà là cùng byte, vì chú thích, thứ tự khoá và dòng trắng đều là
   thứ khách sẽ mất nếu ta đọc-ra-rồi-ghi-lại.

⛔ VÀ MỘT CA RIÊNG PHẢI CÓ TEST: khách **đã có sẵn** `[model_providers.ltt]`
   hoặc `ltt.config.toml` từ trước. `go` **không được** xoá nó. "Xoá những gì
   trông giống của ta" và "xoá đúng những gì ta đã thêm" là hai việc khác nhau,
   và chỉ cái thứ hai là đúng.

⚠️ Test ở đây **không** đụng tới thư mục nhà thật và **không** gọi `setx`:
   `cam_cli` đặt `ANTHROPIC_BASE_URL` ở cấp người dùng, mà biến đó **toàn cục** —
   một test làm thật sẽ chuyển hướng mọi phiên Claude Code trên máy đang chạy nó.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tomllib

import pytest

#: Ten model cong khai, doc tu `canonical` chu KHONG go tay: D02 cat
#: `ltt_llm`/`ltt_llm_vision` ngay 11/09/2026, va mot ten go tay o day se do
#: vi CHINH NO da cu chu khong vi cua hong.
from platform_core.llm.canonical import ALIAS_SANG_ID, MODEL_MAC_DINH as MODEL

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap(nha: pathlib.Path):
    """Nạp `cam_cli` với `NHA` trỏ vào một thư mục tạm.

    Nạp lại module cho **mỗi** test thay vì `monkeypatch` một biến toàn cục:
    `TEP_TRANG_THAI` được tính từ `NHA` **lúc nạp module**, nên vá `NHA` sau đó
    sẽ để lại `TEP_TRANG_THAI` trỏ vào thư mục nhà thật. Cùng lớp lỗi với QT-12.
    """
    spec = importlib.util.spec_from_file_location(
        "cam_cli_test", GOC / "tools" / "cam_cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.NHA = nha
    mod.TEP_TRANG_THAI = nha / ".ltt" / "cam_cli_trang_thai.json"
    # !! MOI hang sinh tu `NHA` phai duoc tro lai, khong chi tep trang thai.
    #    Bo sot `TEP_CATALOG` mot lan roi: test van XANH, vi no ghi vao thu muc
    #    nha THAT cua nguoi dang chay test. Xanh vi ly do sai.
    mod.TEP_CATALOG = nha / ".codex" / "ltt_model_catalog.json"
    mod.TEP_NHAT_KY = nha / "log" / "cam-cli.log"
    return mod


def _chan_duong_ra_ngoai(mod, nha, monkeypatch):
    """Chan MOI duong tep ra ngoai `nha` — ke ca duong **khong** qua `NHA`.

    🔴 `_vscode_settings()` doc thang `%APPDATA%`, khong di qua `NHA`. Tro `NHA`
       vao tmp la CHUA DU, va cho do da can that ngay 30/08: mot phep kiem moi
       da **ghi de `settings.json` that cua VS Code** tren may dang chay test.
       Khong test nao do — ta chi biet vi tinh co doc tep do ngay sau.

    ⚠️ Banh coc `test_KHONG_hang_duong_dan_nao_con_tro_ra_NGOAI_thu_muc_tam`
       khong bat duoc, vi no chi soi cac HANG kieu `Path`. Mot **ham** doc bien
       moi truong thi no khong nhin thay.
    """
    monkeypatch.setenv("APPDATA", str(nha / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(nha / "AppData" / "Local"))
    (nha / "AppData" / "Roaming" / "Code" / "User").mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def cc(tmp_path, monkeypatch):
    """Nạp `cam_cli` cô lập — **và chặn mọi đường ra ngoài thư mục tạm**.

    🔴 `lenh_cam` không chỉ ghi tệp: nó gọi `setx` và **ghi chính sách registry**
       cho Claude Desktop. Một test gọi `lenh_cam` mà không chặn hai đường đó sẽ
       **cấu hình thật máy đang chạy test** — đổi biến môi trường của lập trình
       viên và trỏ Claude Desktop của họ vào một endpoint.

    ⚠️ Lần đầu thêm `cam_desktop`, fixture này chưa chặn registry. Máy chạy test
       thoát nạn vì `reg add` tình cờ không ăn, **không phải vì test an toàn** —
       đúng loại "xanh vì lý do sai" mà dự án này đã dính nhiều lần.
    """
    mod = _nap(tmp_path)
    _chan_duong_ra_ngoai(mod, tmp_path, monkeypatch)
    ghi = {}
    env = {}
    monkeypatch.setattr(mod, "_setx",
                        lambda t, v: (env.__setitem__(t, v), True)[1])
    monkeypatch.setattr(mod, "_xoa_env",
                        lambda t: (env.pop(t, None), True)[1])
    monkeypatch.setattr(mod, "_doc_env_nguoi_dung", lambda t: env.get(t))
    monkeypatch.setattr(mod, "_reg_ghi",
                        lambda k, t, v: (ghi.__setitem__((k, t), v), True)[1])
    # `cam_desktop` goi ban CO LY DO; thieu dong nay thi no cham vao registry
    # THAT cua may dang chay test.
    monkeypatch.setattr(mod, "_reg_ghi_ly_do",
                        lambda k, t, v: (ghi.__setitem__((k, t), v), (True, ""))[1])
    # Va no hoi quyen truoc. Tren may that quyen do KHONG co (nhanh Policies),
    # nen khong va thi moi test desktop se di vao nhanh "thieu quyen".
    monkeypatch.setattr(mod, "_co_quyen_chinh_sach", lambda k: (True, ""))
    monkeypatch.setattr(mod, "_reg_xoa",
                        lambda k, t: (ghi.pop((k, t), None), True)[1])
    monkeypatch.setattr(mod, "_reg_doc", lambda k, t: ghi.get((k, t)))
    mod._registry_gia = ghi          # test doc duoc da ghi gi
    mod._env_gia = env
    return mod


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
@pytest.mark.parametrize("vscode", [False, True])
def test_selected_profile_catalog_and_rollback(cc, model, vscode):
    cfg = cc.NHA / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    original = (b'# customer config\r\nmodel = "customer"\r\n'
                b'model_catalog_json = "customer.json"\r\n'
                b'model_auto_compact_token_limit = 999\r\n')
    cfg.write_bytes(original)
    tt = {"model": model}
    cc.cam_codex("https://example.test", tt, cho_vscode=vscode)
    profile = tomllib.loads((cfg.parent / "ltt.config.toml").read_text())
    hs = cc.hs_cua(model)
    assert (profile["model"], profile["model_context_window"],
            profile["model_auto_compact_token_limit"]) == (model, hs.cua_so, hs.nen)
    assert profile["model_reasoning_effort"] == hs.reasoning
    assert profile["agents"] == {
        "default_subagent_model": model,
        "default_subagent_reasoning_effort": hs.reasoning,
        "max_concurrent_threads_per_session": 1,
    }
    if vscode:
        root = tomllib.loads(cfg.read_text())
        assert root["model"] == model
        assert root["model_catalog_json"] == str(cc.TEP_CATALOG)
    catalog = json.loads(cc.TEP_CATALOG.read_text())["models"]
    assert all(m["input_modalities"] == ["text", "image"] for m in catalog)
    levels = {item["slug"]: item["supported_reasoning_levels"]
              for item in catalog}
    assert [item["effort"] for item in levels["ltt-3.8"]] == [
        "low", "medium", "xhigh"]
    assert levels["ltt-3.5"] == [
        {"effort": "medium", "description": "Thinking on"}]
    cc.go_codex(tt)
    assert cfg.read_bytes() == original
    assert not cc.TEP_CATALOG.exists()
    assert not (cfg.parent / "ltt.config.toml").exists()


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_claude_vscode_standalone_routes_and_context(cc, model):
    tt = {"model": model}
    cc.cam_vscode("https://example.test", tt)
    settings = json.loads(cc._vscode_settings().read_text())
    env = {v["name"]: v["value"] for v in settings["claudeCode.environmentVariables"]}
    for key in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL",
                "CLAUDE_CODE_SUBAGENT_MODEL"):
        assert env[key] == model
    assert env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "1"
    assert env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert env["CLAUDE_CODE_SUBAGENT_MODEL_FORCE"] == "1"
    assert env["CLAUDE_CODE_MAX_RETRIES"] == "10"
    assert env["API_TIMEOUT_MS"] == "600000"
    assert env["CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK"] == "1"
    assert env["ENABLE_TOOL_SEARCH"] == "false"
    assert int(env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"]) == cc.hs_cua(model).nen
    assert int(env["MAX_MCP_OUTPUT_TOKENS"]) <= cc.TOKEN_RA_TRAN // 2
    assert cc._env_gia == {}  # Selecting VS Code needs no CLI install.
    cc.go_vscode(tt)
    assert "claudeCode.environmentVariables" not in json.loads(cc._vscode_settings().read_text())


@pytest.mark.parametrize("model", ["ltt-3.8", "ltt-3.5"])
def test_claude_cli_pins_every_model_route_and_one_subagent(cc, model):
    cc.cam_claude("https://example.test", {"model": model}, toan_cuc=False)
    for key in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_FABLE_MODEL",
                "CLAUDE_CODE_SUBAGENT_MODEL"):
        assert cc._env_gia[key] == model
    assert cc._env_gia["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "1"
    assert cc._env_gia["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert cc._env_gia["CLAUDE_CODE_SUBAGENT_MODEL_FORCE"] == "1"
    assert cc._env_gia["CLAUDE_CODE_MAX_RETRIES"] == "10"
    assert cc._env_gia["API_TIMEOUT_MS"] == "600000"
    assert cc._env_gia["CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK"] == "1"
    assert cc._env_gia["ENABLE_TOOL_SEARCH"] == "false"


# ── Trung tâm: cắm rồi gỡ phải bằng từng byte ───────────────────────────────

CONFIG_CUA_KHACH = """\
# Cau hinh rieng cua toi, dung xoa.
model = "gpt-5.6-sol"

[model_providers.cua_toi]
name = "Cua toi"
base_url = "https://vi-du.local/v1"

# mot dong chu thich o cuoi
"""


def test_cam_roi_go_tra_ve_DUNG_TUNG_BYTE(cc, tmp_path):
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CONFIG_CUA_KHACH, encoding="utf-8", newline="\n")
    goc_byte = cfg.read_bytes()

    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    assert cfg.read_bytes() != goc_byte, "cam ma khong doi gi thi cam cai gi?"

    cc.go_codex(tt)
    assert cfg.read_bytes() == goc_byte, (
        "go ra KHONG tra ve nguyen trang. Chu thich, thu tu khoa va dong trang "
        "deu la thu khach se mat neu ta doc-ra-roi-ghi-lai.")


def test_cam_giu_nguyen_phan_cua_khach(cc, tmp_path):
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CONFIG_CUA_KHACH, encoding="utf-8", newline="\n")

    cc.cam_codex("https://app.lttstudios.com", {})
    van = cfg.read_text(encoding="utf-8")
    # Ghi de la hong theo kieu te nhat: NO VAN CHAY, chi la do nghe rieng cua
    # khach bien mat.
    assert "[model_providers.cua_toi]" in van
    assert 'model = "gpt-5.6-sol"' in van
    assert "# Cau hinh rieng cua toi, dung xoa." in van
    assert "[model_providers.ltt]" in van


def test_chay_hai_lan_bang_chay_mot_lan(cc, tmp_path):
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CONFIG_CUA_KHACH, encoding="utf-8", newline="\n")

    cc.cam_codex("https://app.lttstudios.com", {})
    mot = cfg.read_bytes()
    cc.cam_codex("https://app.lttstudios.com", {})
    assert cfg.read_bytes() == mot, "chay lai phai khong doi gi them"
    assert cfg.read_text(encoding="utf-8").count(cc.MOC_MO) == 1


def test_cam_vao_tep_CHUA_TON_TAI(cc, tmp_path):
    cfg = tmp_path / ".codex" / "config.toml"
    assert not cfg.exists()
    cc.cam_codex("https://app.lttstudios.com", {})
    assert "[model_providers.ltt]" in cfg.read_text(encoding="utf-8")


# ── Ca riêng: khách đã có sẵn thứ trùng tên ────────────────────────────────

def test_go_KHONG_xoa_ltt_config_ma_khach_da_co_tu_truoc(cc, tmp_path):
    """Đây là ca dễ làm sai nhất, và làm sai thì **mất dữ liệu của khách**."""
    prof = tmp_path / ".codex" / "ltt.config.toml"
    prof.parent.mkdir(parents=True)
    prof.write_text("# cua khach, khong phai cua ta\n", encoding="utf-8")

    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    assert tt["codex"]["ta_tao_ltt_config"] is False

    cc.go_codex(tt)
    assert prof.exists(), (
        "go ra da xoa mot tep khach CO TU TRUOC. 'Xoa nhung gi trong giong cua "
        "ta' va 'xoa dung nhung gi ta da them' la hai viec khac nhau.")


def test_go_CO_xoa_ltt_config_khi_chinh_ta_tao_no(cc, tmp_path):
    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    prof = tmp_path / ".codex" / "ltt.config.toml"
    assert prof.exists() and tt["codex"]["ta_tao_ltt_config"] is True
    cc.go_codex(tt)
    assert not prof.exists()


# ── settings.json: khôi phục giá trị cũ, không chỉ xoá ─────────────────────

def test_settings_json_tra_lai_GIA_TRI_CU_chu_khong_xoa(cc, tmp_path, monkeypatch):
    monkeypatch.setattr(cc, "_setx", lambda *a: True)
    sj = tmp_path / ".claude" / "settings.json"
    sj.parent.mkdir(parents=True)
    sj.write_text(json.dumps({
        "env": {"ANTHROPIC_BASE_URL": "https://api.anthropic.com",
                "CUA_KHACH": "giu nguyen"},
        "permissions": {"allow": ["Read"]}}), encoding="utf-8")

    tt = {}
    cc.cam_claude("https://app.lttstudios.com", tt, toan_cuc=True)
    d = json.loads(sj.read_text(encoding="utf-8"))
    assert d["env"]["ANTHROPIC_BASE_URL"] == "https://app.lttstudios.com/api"

    monkeypatch.setattr(cc, "_xoa_env", lambda *a: True)
    cc.go_claude(tt)
    d = json.loads(sj.read_text(encoding="utf-8"))
    assert d["env"]["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com", (
        "khach DA CO base_url rieng truoc khi cam; go ra phai tra ve gia tri do, "
        "khong phai xoa khoa di")
    assert d["env"]["CUA_KHACH"] == "giu nguyen"
    assert d["permissions"] == {"allow": ["Read"]}


def test_settings_json_XOA_HAN_khoa_von_khong_co(cc, tmp_path, monkeypatch):
    monkeypatch.setattr(cc, "_setx", lambda *a: True)
    monkeypatch.setattr(cc, "_xoa_env", lambda *a: True)
    sj = tmp_path / ".claude" / "settings.json"
    sj.parent.mkdir(parents=True)
    sj.write_text(json.dumps({"permissions": {"allow": ["Read"]}}), encoding="utf-8")

    tt = {}
    cc.cam_claude("https://app.lttstudios.com", tt, toan_cuc=True)
    cc.go_claude(tt)
    d = json.loads(sj.read_text(encoding="utf-8"))
    assert "ANTHROPIC_BASE_URL" not in (d.get("env") or {})
    assert d["permissions"] == {"allow": ["Read"]}


def test_mac_dinh_KHONG_dung_toi_settings_json(cc, tmp_path, monkeypatch):
    """`ANTHROPIC_BASE_URL` trong `settings.json` là **toàn cục**.

    Mặc định phải là biến môi trường; ghi `settings.json` chỉ khi khách nói rõ.
    """
    monkeypatch.setattr(cc, "_setx", lambda *a: True)
    sj = tmp_path / ".claude" / "settings.json"
    cc.cam_claude("https://app.lttstudios.com", {}, toan_cuc=False)
    assert not sj.exists()


# ── Khoá không được nằm trong tệp nào ──────────────────────────────────────

def test_KHONG_tep_nao_chua_khoa_sau_khi_cam(cc, tmp_path, monkeypatch):
    """Luật đã có trong mã: *"No snippet ever contains a key."*"""
    khoa = "ltt_sk_" + "z" * 60

    a = type("A", (), {"khoa": khoa, "goc": "https://app.lttstudios.com",
                       "toan_cuc": True})()
    assert cc.lenh_cam(a) == 0

    dinh = []
    for tep in tmp_path.rglob("*"):
        if tep.is_file() and khoa in tep.read_text(encoding="utf-8", errors="replace"):
            dinh.append(str(tep.relative_to(tmp_path)))
    assert not dinh, (
        f"khoa nam trong tep: {dinh}. settings.json va config.toml la tep van "
        f"ban thuong ma nhieu nguoi dong bo hoac commit vao kho dotfiles.")


def test_tu_choi_chuoi_khong_phai_khoa(cc):
    a = type("A", (), {"khoa": "sk-openai-nham-chuoi", "goc": "x",
                       "toan_cuc": False})()
    assert cc.lenh_cam(a) == 1


# ── Sao lưu giữ bản ĐẦU TIÊN ───────────────────────────────────────────────

def test_sao_luu_giu_ban_DAU_TIEN_khong_ghi_de(cc, tmp_path):
    """Bản sao lưu phải là bản **trước khi ta đụng vào**.

    Ghi đè nó ở lần chạy thứ hai bằng một bản "đã có cấu hình của ta" là làm mất
    đúng thứ ta định bảo vệ.
    """
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(CONFIG_CUA_KHACH, encoding="utf-8", newline="\n")

    cc.cam_codex("https://app.lttstudios.com", {})
    cc.cam_codex("https://app.lttstudios.com", {})
    bs = cfg.with_suffix(cfg.suffix + ".truoc-ltt")
    assert bs.read_text(encoding="utf-8") == CONFIG_CUA_KHACH


# ── Hai lỗi mà chỉ VM thật tìm ra (P4/T8, 24/08) ───────────────────────────

CONFIG_CRLF = CONFIG_CUA_KHACH.replace("\n", "\r\n")


def test_giu_nguyen_CRLF_cua_tep_khach(cc, tmp_path):
    """🔴 Lỗi thật: cắm rồi gỡ đổi **cả tệp** từ CRLF sang LF.

    `Set-Content` của PowerShell — thứ phần lớn người dùng Windows và mọi script
    cài đặt dùng — ghi CRLF. Ta đọc rồi ghi lại bằng `newline="\n"` là **viết
    lại từng dòng** của tệp.

    ⚠️ Mọi test phía trên **không thấy**, vì chính chúng ghi fixture bằng
       `newline="\n"` — tức chúng đo một thế giới chỉ có LF. Test này viết
       fixture bằng CRLF, đúng như máy khách thật.
    """
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_bytes(CONFIG_CRLF.encode())
    goc = cfg.read_bytes()
    assert b"\r\n" in goc

    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    sau_cam = cfg.read_bytes()
    assert b"\r\n" in sau_cam, "cam da lam mat CRLF"
    assert b"\n" not in sau_cam.replace(b"\r\n", b""), "cam tron lan CRLF va LF"

    cc.go_codex(tt)
    assert cfg.read_bytes() == goc, (
        "go ra khong tra ve bang tung byte voi mot tep CRLF. Khach mo `git diff` "
        "len se thay TOAN BO tep thay doi.")


def test_settings_json_CRLF_cung_duoc_giu(cc, tmp_path, monkeypatch):
    """`settings.json` giữ **kiểu xuống dòng** và **nội dung**, nhưng KHÔNG hứa
    bằng-từng-byte — và đây là một giới hạn thật, nói thẳng chứ không giấu.

    ⭐ VÌ SAO KHÁC `config.toml`. TOML của khách có **chú thích** và **thứ tự
       khoá** mà một vòng parse-rồi-ghi-lại sẽ xoá sạch — nên ở đó ta làm **phẫu
       thuật văn bản** trên một khối có dấu mốc, và giữ được từng byte.

       JSON **không có chú thích**. Ta phải parse để biết khoá nào của khách,
       khoá nào của ta — không có cách nào khác làm đúng việc *"trả về giá trị
       cũ"*. Cái giá là tệp được định dạng lại (thụt lề, dòng cuối).

    ⇒ Lời hứa ở đây là: **không mất dữ liệu, và không đổi CRLF ↔ LF.** Đừng viết
      test đòi bằng-từng-byte cho JSON rồi nới lỏng code để nó xanh — như vậy là
      hứa một điều ta không giữ được.
    """
    monkeypatch.setattr(cc, "_setx", lambda *a: True)
    monkeypatch.setattr(cc, "_xoa_env", lambda *a: True)
    sj = tmp_path / ".claude" / "settings.json"
    sj.parent.mkdir(parents=True)
    goc_doi_tuong = {"env": {"CUA_KHACH": "x"}, "permissions": {"allow": ["Read"]}}
    sj.write_bytes((json.dumps(goc_doi_tuong, indent=2) + "\n")
                   .replace("\n", "\r\n").encode())

    tt = {}
    cc.cam_claude("https://app.lttstudios.com", tt, toan_cuc=True)
    b = sj.read_bytes()
    assert b"\r\n" in b, "cam da lam mat CRLF cua settings.json"
    assert b"\n" not in b.replace(b"\r\n", b""), "tron lan CRLF va LF"

    cc.go_claude(tt)
    sau = sj.read_bytes()
    assert b"\r\n" in sau and b"\n" not in sau.replace(b"\r\n", b""), (
        "go ra da doi kieu xuong dong cua settings.json")
    assert json.loads(sau.decode()) == goc_doi_tuong, (
        "noi dung khong tro ve nhu cu")


def test_go_XOA_CA_khoa_cua_Codex(cc, monkeypatch):
    """🔴 Lỗi tiền: `go` để lại **một khoá API còn sống** trong môi trường.

    `LTT_API_KEY` bị bỏ sót vì nó "thuộc về Codex" còn hàm dọn tên là
    `go_claude`. Công cụ vẫn in "da go" và mọi dòng đều `[OK]`.

    ⚠️ Các test khác vá `_xoa_env` thành hàm giả trả `True` — tức chúng đo *ta
       có gọi hàm không*, chứ không đo *biến nào được gọi*. Test này ghi lại
       **tên** từng biến đã yêu cầu xoá.
    """
    da_xoa = []
    monkeypatch.setattr(cc, "_xoa_env", lambda ten: da_xoa.append(ten) or True)
    cc.go_claude({})
    assert cc.ENV_KHOA_CODEX in da_xoa, (
        f"`go` khong xoa {cc.ENV_KHOA_CODEX} - mot khoa API tieu duoc tien nam "
        f"lai trong moi truong cua khach. Da xoa: {da_xoa}")
    assert cc.ENV_KHOA_CLAUDE in da_xoa


def test_tep_co_XUONG_DONG_LAN_LON_van_tra_ve_bang_tung_byte(cc, tmp_path):
    """🔴 Ca đã lọt qua **hai** lần sửa trước, và chỉ VM thật bắt được.

    Tệp thật trên máy khách không nhất quán: nội dung LF (từ một here-string
    hoặc một tệp chép từ Linux) nhưng dòng cuối CRLF (do `Set-Content` thêm).

    Bản sửa thứ nhất hỏi *"tệp này có CRLF không?"* — thấy **một** CRLF ở cuối
    là ép **cả tệp** thành CRLF: 147 byte phình thành 154.

    ⭐ Cách duy nhất đúng là **không hỏi câu đó**: đọc thô, mổ đúng khối, ghi thô.
       Phần ngoài khối không bị đụng tới thì không có gì để hỏng — kể cả khi nó
       lẫn lộn, kể cả khi nó kỳ quặc.
    """
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    # LF ben trong, CRLF o dong cuoi - dung hinh dang tep tren VM105.
    cfg.write_bytes(b'# cua toi\nmodel = "x"\n\n# het\r\n')
    goc = cfg.read_bytes()

    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    cc.go_codex(tt)
    assert cfg.read_bytes() == goc, (
        f"tep xuong dong lan lon khong tro ve nguyen trang.\n"
        f"goc  = {goc!r}\nsau  = {cfg.read_bytes()!r}")


def test_khong_cat_dong_trang_cuoi_cua_khach(cc, tmp_path):
    """`go` chỉ được cắt phần **ta thêm**, không cắt dòng trắng của khách."""
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_bytes(b'model = "x"\n\n\n')      # ba xuong dong, co chu y
    goc = cfg.read_bytes()
    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    cc.go_codex(tt)
    assert cfg.read_bytes() == goc


# ── Bốn lỗi tìm ra khi soát lại logic (24/08) ──────────────────────────────

def test_chay_cam_HAI_LAN_roi_go_van_xoa_sach(cc, tmp_path):
    """🔴 Lỗi thật: chạy `cam` hai lần rồi `go` để lại rác **vĩnh viễn**.

    `ta_tao_ltt_config` từng được tính lại ở **mỗi** lần `cam`. Lần hai, tệp đã
    tồn tại (do chính ta tạo lần một), nên nó ghi `False` — và `go` không xoá
    nữa. Không có triệu chứng nào; chỉ là một tệp lạ nằm lại trong `~/.codex`.

    ⭐ Cùng luật với `_sao_luu`: **bản đầu tiên mới là sự thật.**
    """
    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    cc.cam_codex("https://app.lttstudios.com", tt)      # lan hai
    prof = tmp_path / ".codex" / "ltt.config.toml"
    assert prof.exists()
    assert tt["codex"]["ta_tao_ltt_config"] is True, (
        "lan chay thu hai da ghi de ket luan cua lan dau")
    cc.go_codex(tt)
    assert not prof.exists(), "go de lai rac sau khi cam hai lan"


def test_ltt_config_CUA_KHACH_duoc_tra_ve_nguyen_van(cc, tmp_path):
    """🔴 Lỗi mất dữ liệu: ta **ghi đè** `ltt.config.toml` của khách.

    Bản trước chỉ "không xoá" tệp có sẵn — nhưng nội dung thì đã bị ta ghi đè
    mất từ lúc `cam`. "Không xoá" và "trả về nguyên trạng" là hai việc khác nhau.
    """
    prof = tmp_path / ".codex" / "ltt.config.toml"
    prof.parent.mkdir(parents=True)
    goc = b"# cau hinh rieng cua khach\nmodel = \"cua-toi\"\n"
    prof.write_bytes(goc)

    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt)
    assert prof.read_bytes() != goc, "cam phai ghi cau hinh cua ta vao"

    cc.go_codex(tt)
    assert prof.read_bytes() == goc, (
        "go KHONG tra lai noi dung cu cua khach. 'Khong xoa' chua phai la "
        "'tra ve nguyen trang'.")


def test_ghi_nho_che_do_vscode(cc, tmp_path):
    """`xem` phải nói được đang ở chế độ nào — đó là câu hỏi khách sẽ hỏi."""
    tt = {}
    cc.cam_codex("https://x", tt, cho_vscode=True)
    assert tt["codex"]["che_do"] == "vscode"
    van = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'model_provider = "ltt"' in van, "che do vscode phai khai o GOC"

    tt2 = {}
    cc.cam_codex("https://x", tt2)
    assert tt2["codex"]["che_do"] == "profile"
    van2 = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'model_provider = "ltt"' not in van2, (
        "che do profile KHONG duoc dat model_provider o goc - lam vay la thay "
        "mac dinh cua khach ma ho khong yeu cau")


def test_che_do_vscode_va_profile_deu_go_sach(cc, tmp_path):
    for vscode in (True, False):
        cfg = tmp_path / ".codex" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_bytes(b'model = "cua-khach"\n')
        goc = cfg.read_bytes()
        tt = {}
        cc.cam_codex("https://x", tt, cho_vscode=vscode)
        cc.go_codex(tt)
        assert cfg.read_bytes() == goc, f"che do vscode={vscode} khong go sach"


# ── Claude Desktop: chính sách registry ────────────────────────────────────

def test_desktop_ghi_dung_sau_khoa_chinh_sach(cc):
    """Tên khoá lấy từ **tài liệu chính thức**, không đoán."""
    tt = {}
    cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_" + "z" * 60, tt)
    g = cc._registry_gia
    k = cc.REG_DESKTOP_HKCU
    assert g[(k, "inferenceProvider")] == "gateway"
    assert g[(k, "inferenceGatewayAuthScheme")] == "bearer"
    # 🔴 KHONG phai `ltt_llm`. Claude Desktop LOC danh sach model truoc khi hien
    #    picker; ten khong chua "claude"/"anthropic"/ten dong Claude thi bi bo,
    #    picker rong, va **nut gui vo hieu ma khong bao gi**. Luat day du +
    #    ly do chon dung ten nay: `tests/test_290_ten_tuyen_claude_desktop.py`.
    assert json.loads(g[(k, "inferenceModels")]) == [
        {"name": h.tuyen_desktop,
         "labelOverride": cc.NHAN_DESKTOP[h.tuyen_desktop],
         "anthropicFamilyTier": cc.TANG_DESKTOP[h.tuyen_desktop],
         "isFamilyDefault": True}
        for h in cc.HO_SO_MODEL.values()]
    assert cc.MODEL_DESKTOP != cc.MODEL
    assert g[(k, "modelDiscoveryEnabled")] == 0
    assert g[(k, "chatTabEnabled")] == 1
    assert g[(k, "disableDeploymentModeChooser")] == 1
    assert g[(k, "inferenceStreamIdleTimeoutSec")] == 600


def test_desktop_base_url_KHONG_kem_v1_va_phai_https(cc):
    """Tài liệu chốt hai điều, và cả hai đều hỏng lặng lẽ nếu sai.

    ⛔ `inferenceGatewayBaseUrl` là **gốc**, ứng dụng tự ghép `/v1/messages`.
       Kèm sẵn `/v1` là thành `/v1/v1/messages` ⇒ 404 không manh mối.
    ⛔ Và bản 1.52386.6 **bắt buộc HTTPS**, kể cả loopback.
    """
    tt = {}
    cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_x", tt)
    u = cc._registry_gia[(cc.REG_DESKTOP_HKCU, "inferenceGatewayBaseUrl")]
    assert u == "https://app.lttstudios.com/api"
    assert u.startswith("https://"), "tai lieu bat buoc HTTPS"
    assert not u.rstrip("/").endswith("/v1"), (
        "base_url KHONG duoc kem /v1 - ung dung tu ghep /v1/messages")


def test_desktop_HTTP_ke_ca_loopback_bi_tu_choi_TRUOC_khi_ghi(cc):
    ra = cc.cam_desktop("http://127.0.0.1:9999", "ltt_sk_x", {})
    assert not cc._registry_gia, "endpoint bi tu choi ma van ghi nua voi registry"
    assert any("HTTPS" in d for d in ra)


def test_desktop_go_ra_tra_ve_gia_tri_cu(cc):
    """Khách **đã có** chính sách riêng ⇒ `go` trả lại, không xoá."""
    k = cc.REG_DESKTOP_HKCU
    cc._registry_gia[(k, "inferenceGatewayBaseUrl")] = "https://cua-khach.local"
    tt = {}
    cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_x", tt)
    assert cc._registry_gia[(k, "inferenceGatewayBaseUrl")] == "https://app.lttstudios.com/api"
    cc.go_desktop(tt)
    assert cc._registry_gia[(k, "inferenceGatewayBaseUrl")] == "https://cua-khach.local", (
        "khach co chinh sach rieng tu truoc; go phai tra ve, khong phai xoa")
    assert (k, "inferenceProvider") not in cc._registry_gia, (
        "khoa von KHONG co thi go phai xoa han")


def test_desktop_go_ra_tra_dung_REG_DWORD_cua_khach(cc):
    k = cc.REG_DESKTOP_HKCU
    cc._registry_gia[(k, "inferenceStreamIdleTimeoutSec")] = 900
    tt = {}
    cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_x", tt)
    assert cc._registry_gia[(k, "inferenceStreamIdleTimeoutSec")] == 600
    cc.go_desktop(tt)
    assert cc._registry_gia[(k, "inferenceStreamIdleTimeoutSec")] == 900


def test_desktop_go_ban_moi_don_DWORD_ma_trang_thai_ban_cu_khong_biet(cc):
    """An upgrade must not strand policy values introduced by release 1.8."""
    k = cc.REG_DESKTOP_HKCU
    cc._registry_gia[(k, "disableDeploymentModeChooser")] = 1
    old_state = {"desktop": {"khoa_da_them": {
        "inferenceProvider": None,
    }}}

    cc.go_desktop(old_state)

    assert (k, "disableDeploymentModeChooser") not in cc._registry_gia


def test_desktop_go_ban_moi_khong_xoa_DWORD_khac_cua_khach(cc):
    k = cc.REG_DESKTOP_HKCU
    cc._registry_gia[(k, "inferenceStreamIdleTimeoutSec")] = 900
    old_state = {"desktop": {"khoa_da_them": {
        "inferenceProvider": None,
    }}}

    cc.go_desktop(old_state)

    assert cc._registry_gia[(k, "inferenceStreamIdleTimeoutSec")] == 900


def test_desktop_DUNG_LAI_khi_may_da_co_chinh_sach_HKLM(cc):
    """⛔ Có `HKLM` thì ứng dụng **bỏ qua hoàn toàn** `HKCU`.

    Cắm vào `HKCU` khi đó là **vô tác dụng và không báo lỗi** — kiểu hỏng tệ
    nhất. Công cụ phải dừng lại và nói ra, chứ không phải ghi rồi báo `[OK]`.
    """
    cc._registry_gia[(cc.REG_DESKTOP_HKLM, "inferenceProvider")] = "anthropic"
    tt = {}
    ra = cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_x", tt)
    assert any("HKLM" in d for d in ra)
    assert (cc.REG_DESKTOP_HKCU, "inferenceProvider") not in cc._registry_gia, (
        "da ghi vao HKCU du no se bi bo qua - do la bao thanh cong gia")


def test_desktop_KHONG_in_khoa_ra_man_hinh(cc):
    khoa = "ltt_sk_" + "q" * 60
    ra = cc.cam_desktop("https://app.lttstudios.com", khoa, {})
    assert not any(khoa in d for d in ra), "khoa bi in ra man hinh"


# ── Phien ban, nhat ky, va pham vi cua `kiem` ────────────────────────────────
#
# 🔴 Ba thu nay deu la bai hoc tu mot lan that bai co that, khong phai "cho day
#    du". Xem `docs/PUBLIC_API/KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §1.5–1.6.

def test_phien_ban_trong_ma_KHOP_bo_cai(cc):
    """Mot so, hai noi. Test nay la thu duy nhat giu chung khong lech.

    ⛔ Bo cai khai `1.0.0` con chuong trinh khong biet minh la ban nao thi cau
       hoi DAU TIEN cua moi lan ho tro ("ban chay ban nao?") khong tra loi duoc.
    """
    import pathlib
    import re
    iss = (pathlib.Path(__file__).resolve().parents[1]
           / "tools" / "installer" / "cam_cli.iss").read_text(encoding="utf-8")
    m = re.search(r'#define\s+PhienBan\s+"([^"]+)"', iss)
    assert m, "khong tim thay #define PhienBan trong cam_cli.iss"
    assert m.group(1) == cc.PHIEN_BAN, (
        f"bo cai khai {m.group(1)} con ma khai {cc.PHIEN_BAN}")


def test_nhat_ky_ghi_duoc_va_KHONG_chua_khoa(cc, tmp_path, monkeypatch):
    """Nhat ky la thu khach GUI DI kem khi bao loi.

    ⛔ Nen no tuyet doi khong duoc chua khoa. Test nay chay `cam` that (voi mot
       khoa gia) roi doc lai ca tep.
    """
    monkeypatch.setattr(cc, "TEP_NHAT_KY", tmp_path / "cam-cli.log")
    khoa = "ltt_sk_" + "9" * 60
    cc._ghi_nhat_ky("thu mot dong")
    cc.main(["xem"])

    noi = (tmp_path / "cam-cli.log").read_text(encoding="utf-8")
    assert "thu mot dong" in noi
    assert "xem bat dau" in noi and "xem ket thuc ma=0" in noi
    assert cc.PHIEN_BAN in noi
    assert khoa not in noi and "ltt_sk_" not in noi


def test_nhat_ky_KHONG_lam_hong_lenh_khi_khong_ghi_duoc(cc, tmp_path, monkeypatch):
    """O dia chi doc la mot bat tien, khong phai mot ly do de `cam` that bai."""
    hong = tmp_path / "khong-ton-tai" / "sau" / "cam-cli.log"
    monkeypatch.setattr(cc, "TEP_NHAT_KY", hong)
    monkeypatch.setattr(cc.pathlib.Path, "mkdir",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("chi doc")))
    cc._ghi_nhat_ky("khong ghi duoc")      # khong duoc nem


def test_kiem_PHAI_kiem_ca_be_mat_claude_desktop_va_codex(cc):
    """🔴 Ban truoc bao XANH trong khi Claude Desktop im lang hoan toan.

    Vi no chi thu `MODEL` + `stream: True`, con be mat do dung `MODEL_DESKTOP`
    va tham do bang mot request KHONG stream. Ca hai deu nam ngoai phep thu.
    """
    import inspect
    ma = inspect.getsource(cc.lenh_kiem)
    assert "MODEL_DESKTOP" in ma, (
        "`kiem` khong thu ten tuyen cua Claude Desktop -> no se bao xanh trong "
        "khi be mat do dang hong")
    # Request khong stream: khong duoc co `"stream": True` o luot Desktop.
    sau = ma.split("MODEL_DESKTOP", 1)[1]
    assert '"stream"' not in sau.split("phuong=", 1)[0], (
        "luot thu Claude Desktop phai la request KHONG stream")
    assert 'goi("/responses"' in ma, (
        "`kiem` khong thu Responses -> co the bao xanh trong khi Codex hong")
    assert "for hs_codex in HO_SO_MODEL.values()" in ma, (
        "catalog co hai model nen `kiem` phai thu ca hai model Codex")


def test_kiem_GOI_THAT_responses_cho_ca_hai_model_codex(cc, monkeypatch):
    """Behavior check: a green self-check must have traversed both Codex routes."""
    calls = []

    class Reply:
        status = 200

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def urlopen(request, timeout):
        body = json.loads(request.data) if request.data else None
        calls.append((request.full_url, body, timeout))
        if request.full_url.endswith("/tools"):
            return Reply(b'{"items":[{"name":"text.chat"}]}')
        if request.full_url.endswith("/credits/balance"):
            return Reply(b'{"balance":1000}')
        return Reply(b'event: response.completed\ndata: {}\n\n')

    monkeypatch.setattr(cc.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(cc, "_doc_trang_thai", lambda: {"model": "ltt-3.5"})
    args = type("Args", (), {"khoa": "mock", "goc": "https://test"})()
    assert cc.lenh_kiem(args) == 0

    responses = [body for url, body, _timeout in calls
                 if url.endswith("/api/v1/responses")]
    assert [body["model"] for body in responses] == ["ltt-3.8", "ltt-3.5"]
    assert all(body["stream"] is True for body in responses)


# ── Ban 1.1: chon be mat + trang thai that ─────────────────────────────────

def test_chon_RIENG_codex_cli_khong_dung_toi_claude(cc, tmp_path):
    khoa = "ltt_sk_" + "a" * 40
    a = type("A", (), {"khoa": khoa, "goc": "https://app.lttstudios.com",
                       "toan_cuc": False, "vscode": False,
                       "muc": [cc.MUC_CODEX_CLI]})()
    assert cc.lenh_cam(a) == 0
    assert cc.ENV_KHOA_CODEX in cc._env_gia
    assert cc.ENV_KHOA_CLAUDE not in cc._env_gia
    assert not cc._registry_gia, "chon Codex ma lai ghi registry Claude Desktop"
    assert not (tmp_path / ".claude").exists()


def test_hai_che_do_codex_xung_dot_bi_tu_choi(cc):
    a = type("A", (), {"muc": [cc.MUC_CODEX_CLI, cc.MUC_CODEX_VSCODE],
                       "vscode": False})()
    with pytest.raises(ValueError, match="Chi chon MOT"):
        cc._cac_muc(a)


def test_cam_tra_ma_1_neu_doi_chieu_that_khong_thay_hang_muc(cc, monkeypatch):
    khoa = "ltt_sk_" + "b" * 40
    monkeypatch.setattr(cc, "trang_thai_thuc",
                        lambda g=None: {"dang_cam": False,
                                        "muc": {cc.MUC_CODEX_CLI: False}})
    a = type("A", (), {"khoa": khoa, "goc": "https://app.lttstudios.com",
                       "toan_cuc": False, "vscode": False,
                       "muc": [cc.MUC_CODEX_CLI]})()
    assert cc.lenh_cam(a) == 1, (
        "ban 1.0 tra 0 va danh dau da_cam du file/registry khong co gi")


def test_trang_thai_khong_tin_co_da_cam_trong_tep(cc):
    cc._ghi_trang_thai({"da_cam": True, "goc": "https://app.lttstudios.com"})
    thuc = cc.trang_thai_thuc()
    assert thuc["dang_cam"] is False


# ── Cơ chế chống "rác" trong config.toml của khách (2026-08-27) ─────────────
#
# ⚠️ KHE HỞ ĐÃ ĐỂ LỌT LỖI: không một test cũ nào **parse** kết quả cắm. Fixture
#    cũ dùng `[model_providers.cua_toi]` (tên KHÁC), nên ca "khách đã có sẵn
#    `[model_providers.ltt]`" — đúng ca sinh TOML hỏng (hai bảng trùng) — chưa
#    bao giờ chạy. `kiem` cũng không bắt được vì nó tự gọi HTTP. Chỉ mở tiện ích
#    thật mới lộ. Bốn test dưới đóng khe hở đó.

CONFIG_CO_SAN_LTT = """\
# cua toi, dung xoa
model = "gpt-5.6-sol"
model_reasoning_effort = "high"

[model_providers.ltt]
name = "LTT Studios (toi tu dat)"
base_url = "https://app.lttstudios.com/api/v1"
env_key = "LTT_API_KEY"
wire_api = "responses"

[some_other]
x = 1
"""


def _viet_cfg(mod, noi_dung: str) -> pathlib.Path:
    cfg = mod.NHA / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(noi_dung, encoding="utf-8", newline="")
    return cfg


def test_vscode_ket_qua_LA_TOML_HOP_LE_du_khach_da_co_provider_ltt(cc):
    """Đúng ca đã làm chết Codex 27/08: khách có sẵn `[model_providers.ltt]` +
    `model`/`model_reasoning_effort` ở gốc. Kết quả PHẢI parse được."""
    cfg = _viet_cfg(cc, CONFIG_CO_SAN_LTT)
    cc.cam_codex("https://app.lttstudios.com", {}, cho_vscode=True)
    van = cfg.read_text(encoding="utf-8")
    d = tomllib.loads(van)                       # <-- CHÍNH LÀ phép kiểm còn thiếu
    assert d["model"] == MODEL
    assert d["model_provider"] == "ltt"
    assert van.count("[model_providers.ltt]") == 1   # KHÔNG nhân đôi provider


def test_vscode_go_tra_ve_DUNG_TUNG_BYTE_khi_da_co_provider_ltt(cc):
    cfg = _viet_cfg(cc, CONFIG_CO_SAN_LTT)
    goc = cfg.read_bytes()
    tt = {}
    cc.cam_codex("https://app.lttstudios.com", tt, cho_vscode=True)
    assert cfg.read_bytes() != goc               # đã đổi thật
    tomllib.loads(cfg.read_text(encoding="utf-8"))   # trạng thái "on" vẫn hợp lệ
    cc.go_codex(tt)
    assert cfg.read_bytes() == goc               # gỡ trả về nguyên trạng từng byte


def test_profile_KHONG_nhan_doi_provider_ltt_da_co_san(cc):
    cfg = _viet_cfg(cc, CONFIG_CO_SAN_LTT)
    cc.cam_codex("https://app.lttstudios.com", {}, cho_vscode=False)
    van = cfg.read_text(encoding="utf-8")
    tomllib.loads(van)                           # vẫn hợp lệ
    assert van.count("[model_providers.ltt]") == 1


def test_cong_kiem_TU_CHOI_ghi_khi_ket_qua_hong(cc):
    """File đã hỏng sẵn (hai bảng trùng) ⇒ cắm phải TỪ CHỐI, không ghi đè mù."""
    hong = 'model = "x"\n[a]\nk = 1\n[a]\nk = 2\n'
    cfg = _viet_cfg(cc, hong)
    with pytest.raises(cc.CauHinhHong):
        cc.cam_codex("https://app.lttstudios.com", {}, cho_vscode=True)
    assert cfg.read_text(encoding="utf-8") == hong   # không đụng tới tệp hỏng


# ── Catalog model cho Codex (30/08) ────────────────────────────────────────

def test_ho_so_codex_khai_catalog_va_cam_GHI_ra_tep(cc, tmp_path):
    """Khai `model_catalog_json` mà không ghi tệp là biến cảnh báo thành lỗi chặn.

    ⛔ Codex `failed to parse model_catalog_json` rồi **từ chối khởi động** nếu
       đường dẫn trỏ vào tệp không tồn tại. Nên hai việc này phải đi liền nhau.
    """
    assert "model_catalog_json" in cc._codex_profile()
    cc.cam_codex("https://x", {}, cho_vscode=True)
    assert cc.TEP_CATALOG.exists(), "cam xong ma khong ghi catalog"


def test_catalog_dung_khuon_Codex_chap_nhan(cc):
    """Ba chỗ từng làm Codex từ chối tệp — tìm ra bằng cách lặp thật 30/08."""
    import json
    d = json.loads(cc._catalog_codex())
    assert [m["slug"] for m in d["models"]] == list(ALIAS_SANG_ID)
    for m in d["models"]:
        # `web_search_tool_type: null` bi tu choi -> phai BO HAN, khong phai null
        assert "web_search_tool_type" not in m
        # 🔴 CLI doi i64, TIEN ICH VS CODE doi CHUOI cho cung truong nay. Khong
        #    gia tri nao lam vua long ca hai, va ban `90` (hop le voi CLI) da
        #    lam tien ich bao "Invalid configuration ... expected a string" roi
        #    hong MOI luot tao chat. Bo han la cach duy nhat dung.
        assert "effective_context_window_percent" not in m
        # khong duoc con truong null nao
        assert not [k for k, v in m.items() if v is None]
        assert m["default_reasoning_level"] == cc.hs_cua(m["slug"]).reasoning

    # ⛔ MOI MODEL KHAI CUA SO CUA NO. Ban truoc cua doan nay la
    #       assert m["context_window"] == cc.CUA_SO_NGU_CANH
    #    — MOT hang so cho HAI model, va no doi model thu hai (cua so that
    #    28.262, vi ho so vision cu nap `-c 65536`) phai noi 88.555. Phep kiem
    #    khong bat duoc khuyet tat; no CUONG CHE khuyet tat, nen sua ma cho dung
    #    thi gate do. Xem `test_334::test_MOI_model_trong_catalog_khai_cua_so_CUA_NO`.
    mong = {"ltt-3.8": cc.CUA_SO_NGU_CANH,
            "ltt-3.5": cc.CUA_SO_NGU_CANH_35}
    for m in d["models"]:
        assert m["context_window"] == mong[m["slug"]]
        assert m["max_context_window"] == mong[m["slug"]]


def test_go_ra_xoa_catalog_DA_TAO_nhung_giu_catalog_co_tu_truoc(cc):
    """Cung ca kho nhu `ltt.config.toml`: xoa dung thu ta them, khong hon."""
    tt = {}
    cc.cam_codex("https://x", tt, cho_vscode=True)
    assert cc.TEP_CATALOG.exists() and tt["codex"]["ta_tao_catalog"] is True
    cc.go_codex(tt)
    assert not cc.TEP_CATALOG.exists(), "go ra de lai rac ta tu tao"

    # Nguoc lai: khach da co san mot tep cung ten -> `go` phai TRA VE ban cu.
    cc.TEP_CATALOG.write_text("{\"cua khach\": 1}", encoding="utf-8")
    tt2 = {}
    cc.cam_codex("https://x", tt2, cho_vscode=True)
    assert tt2["codex"]["ta_tao_catalog"] is False
    cc.go_codex(tt2)
    assert cc.TEP_CATALOG.read_text(encoding="utf-8") == "{\"cua khach\": 1}"


def test_cam_HAI_LAN_roi_go_van_don_sach_catalog(cc):
    """Bay da tung dinh o `ltt.config.toml`: tinh lai co-tao-khong o lan hai."""
    tt = {}
    cc.cam_codex("https://x", tt, cho_vscode=True)
    cc.cam_codex("https://x", tt, cho_vscode=True)
    cc.go_codex(tt)
    assert not cc.TEP_CATALOG.exists()


def test_KHONG_hang_duong_dan_nao_con_tro_ra_NGOAI_thu_muc_tam(cc, tmp_path):
    """Banh coc cho chinh bo test nay.

    ⛔ Them mot hang `TEP_... = NHA / ...` ma quen tro lai trong `_nap` thi test
       van xanh — vi no ghi vao thu muc THAT cua nguoi chay test. Da dinh dung
       hai lan (30/08): `TEP_CATALOG` ghi vao `~/.codex`, `TEP_NHAT_KY` ghi vao
       `%LOCALAPPDATA%`. Ca hai deu khong lam test do. Phep kiem nay bat lan sau.

    ⚠️ Khong kiem "co nam trong thu muc nha khong" — tren Windows `tmp_path`
       CHINH NO nam duoi thu muc nha, nen phep kiem do luon do.
    """
    import pathlib as _pl
    tam = tmp_path.resolve()
    sot = [ten for ten, gt in vars(cc).items()
           if isinstance(gt, _pl.Path) and ten.isupper()
           and tam not in gt.resolve().parents and gt.resolve() != tam]
    assert not sot, (
        f"Cac hang nay tro RA NGOAI thu muc tam: {sot}. "
        f"Tro chung vao tmp trong `_nap()`.")


# ── Ba lỗi đo được trên máy thật ngày 30/08 ────────────────────────────────

class TestBaLoi3008:
    """Cả ba đều **hỏng lặng lẽ** — công cụ báo xong, việc thì chưa xong."""

    def test_reg_ghi_TRA_VE_LY_DO_chu_khong_chi_bool(self, tmp_path, monkeypatch):
        """⛔ `except OSError: return False` vứt mất `WinError 5 Access denied`.

        Hậu quả thật: dòng in ra là `[!!] inferenceProvider = gateway`, đọc như
        "đã ghi giá trị này" trong khi nghĩa là ngược lại.

        ⚠️ **Không** `skip` khi thiếu `winreg`. Bản đầu có, và nó bị bỏ qua trong
           lượt chạy song song vì một lý do tôi chưa truy ra — tức phép kiểm
           canh cho một lỗi thật lại **không canh gì cả** đúng lúc cần. Ở đây
           dựng thẳng cả hai nhánh, nên nó luôn khẳng định một điều.
        """
        # Nap RIENG, khong qua fixture `cc`: fixture va `_reg_ghi_ly_do` thanh
        # mot ham gia luon thanh cong, tuc no che mat chinh thu can do o day.
        cc = _nap(tmp_path)

        # Nhanh 1: winreg. Neu may khong co winreg thi dung mot ban gia — dieu
        # dang do la "ly do co den duoc nguoi doc khong", khong phai winreg.
        class _WinregGia:
            @staticmethod
            def CreateKey(*a, **k):
                raise OSError(13, "Access is denied", None, 5)

        monkeypatch.setattr(cc, "winreg", _WinregGia)
        monkeypatch.setattr(cc, "_tach_khoa_registry", lambda khoa: (1, "nhanh"))
        ok, vi_sao = cc._reg_ghi_ly_do(r"HKCU\SOFTWARE\Bat_Ky", "x", "y")
        assert ok is False
        assert "5" in vi_sao and "denied" in vi_sao.lower(), (
            f"ly do bi nuot mat o nhanh winreg: {vi_sao!r}")

        # Nhanh 2: rot ve `reg.exe`.
        monkeypatch.setattr(cc, "_tach_khoa_registry", lambda khoa: None)

        class _KetQua:
            returncode = 1
            stdout = ""
            stderr = "ERROR: Access is denied."

        monkeypatch.setattr(cc.subprocess, "run", lambda *a, **k: _KetQua())
        ok, vi_sao = cc._reg_ghi_ly_do("KHOA_LA", "x", "y")
        assert ok is False
        assert "denied" in vi_sao.lower(), (
            f"ly do bi nuot mat o nhanh reg.exe: {vi_sao!r}")

    def test_reg_fallback_ghi_so_bang_REG_DWORD(self, tmp_path, monkeypatch):
        cc = _nap(tmp_path)
        monkeypatch.setattr(cc, "_tach_khoa_registry", lambda khoa: None)
        cac_lenh = []

        class _KetQua:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(
            cc.subprocess, "run",
            lambda cmd, **kw: (cac_lenh.append(cmd), _KetQua())[1])
        assert cc._reg_ghi_ly_do("KHOA_LA", "chatTabEnabled", 1)[0]
        assert "REG_DWORD" in cac_lenh[-1]
        assert cc._reg_ghi_ly_do("KHOA_LA", "inferenceProvider", "gateway")[0]
        assert "REG_SZ" in cac_lenh[-1]

    def test_cam_desktop_HOI_QUYEN_TRUOC_va_KHONG_ghi_nua_voi(self, cc, monkeypatch):
        """Thiếu quyền thì **không ghi gì**, và nói đúng cách sửa.

        Ghi bảy lần rồi bảy lần thất bại là để máy ở trạng thái nửa vời — và
        nếu một lần tình cờ qua thì còn tệ hơn.
        """
        monkeypatch.setattr(cc, "_co_quyen_chinh_sach",
                            lambda k: (False, "WinError 5: Access is denied"))
        goi = []
        monkeypatch.setattr(cc, "_reg_ghi_ly_do",
                            lambda *a: (goi.append(a), (True, ""))[1])
        van = "\n".join(cc.cam_desktop("https://x", "khoa", {}))
        assert goi == [], "thieu quyen ma VAN ghi -> may o trang thai nua voi"
        assert "Access is denied" in van, "khong noi ly do that"
        assert "Run as administrator" in van, "khong noi cach sua"
        assert "Bo chon muc 'Claude Desktop'" in van, "khong noi duong thoat"

    def test_go_vscode_KHONG_DUOC_im_lang_khi_mat_tri_nho(self, cc, tmp_path):
        """🔴 Lỗi nặng nhất: `go` báo xong, đĩa vẫn trỏ về LTT.

        Đo thật 30/08 — `lenh_go` in tiêu đề "Tien ich VS Code:" rồi **không
        một dòng nào**, và `settings.json` vẫn nguyên cấu hình của ta.
        """
        tep = cc._vscode_settings()
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text(json.dumps({
            "claudeCode.environmentVariables": [
                {"name": "ANTHROPIC_BASE_URL", "value": "https://x/api"},
                {"name": "ANTHROPIC_MODEL", "value": cc.MODEL},
                {"name": "CUA_KHACH", "value": "giu nguyen"},
            ],
            "claudeCode.useTerminal": True,
            "editor.fontSize": 14,
        }), encoding="utf-8", newline="\n")

        ra = cc.go_vscode({"goc": "https://x"})          # KHONG co tri nho
        van = "\n".join(ra)
        assert ra, "go_vscode im lang = khach tuong da go xong"

        d = json.loads(tep.read_text(encoding="utf-8"))
        con = d["claudeCode.environmentVariables"]
        assert [x["name"] for x in con] == ["CUA_KHACH"], (
            "phai bo dung nhung muc tro ve goc cua ta, khong hon khong kem")
        assert d["editor.fontSize"] == 14, "dung toi thu khong phai cua ta"
        assert "useTerminal" in van, "phai NOI RA thu co y khong dung toi"

    def test_go_vscode_KHONG_dung_toi_cau_hinh_tro_di_CHO_KHAC(self, cc, tmp_path):
        """Khách trỏ tiện ích sang gateway của **họ** — `go` không được xoá."""
        tep = cc._vscode_settings()
        tep.parent.mkdir(parents=True, exist_ok=True)
        goc_json = json.dumps({"claudeCode.environmentVariables": [
            {"name": "ANTHROPIC_BASE_URL", "value": "https://cua-toi.local/api"}]})
        tep.write_text(goc_json, encoding="utf-8", newline="\n")

        ra = cc.go_vscode({"goc": "https://app.lttstudios.com"})
        assert json.loads(tep.read_text(encoding="utf-8")) == json.loads(goc_json)
        assert ra and "khong muc nao" in "\n".join(ra)


class TestKhongNhoGiaTriCuaTaLamCuaKhach:
    """Lỗi #4 — loại **tự dính vĩnh viễn**, đo trên máy thật 30/08.

    Chuỗi sự kiện:
      1. `go` im lặng (lỗi #3) ⇒ cấu hình của ta ở lại trên đĩa;
      2. tệp trạng thái mất trí nhớ ⇒ `cam` sau ghi nhớ lại từ đầu, và thứ nó
         đọc được **chính là cấu hình của ta**;
      3. từ đó `go` trung thực "hoàn nguyên" về... chính giá trị của ta.

    Triệu chứng: `[OK] da tra ... ve nhu truoc` mà tệp **không đổi một chữ**.
    Khách không bao giờ gỡ ra được, và không có dấu hiệu nào.
    """

    def test_cam_HAI_LAN_qua_hai_tep_trang_thai_van_go_SACH(self, cc, tmp_path):
        tep = cc._vscode_settings()
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text('{"editor.fontSize": 14}', encoding="utf-8", newline="\n")

        cc.cam_vscode("https://x", {})                 # lan 1
        cc.cam_vscode("https://x", {})                 # lan 2, tep trang thai MOI
        ra = cc.go_vscode({"goc": "https://x", "vscode": {"khoa_da_them": {
            k: None for k in ("claudeCode.environmentVariables",
                              "claudeCode.disableLoginPrompt",
                              "claudeCode.useTerminal")}}})
        assert json.loads(tep.read_text(encoding="utf-8")) == {"editor.fontSize": 14}
        assert ra

    def test_nho_ban_cu_KHONG_ghi_gia_tri_cua_ta_lam_ban_goc(self, cc):
        ghi = {}
        cc._nho_ban_cu(ghi, "k", "GIA_TRI_CUA_TA", "GIA_TRI_CUA_TA")
        assert ghi["k"] is None, (
            "ghi nho gia tri cua CHINH TA lam 'ban goc cua khach' ⇒ `go` se "
            "'hoan nguyen' ve chinh no, va khach ket vinh vien")

        ghi2 = {}
        cc._nho_ban_cu(ghi2, "k", "cua-khach", "cua-ta")
        assert ghi2["k"] == "cua-khach"

        ghi2["k"] = "cua-khach"                        # lan hai khong duoc de len
        cc._nho_ban_cu(ghi2, "k", "cua-ta", "cua-ta")
        assert ghi2["k"] == "cua-khach"

    def test_cam_roi_go_van_bang_TUNG_BYTE_qua_hai_luot(self, cc, tmp_path):
        """Phép thử trung tâm của tệp này, nhưng chạy **hai lượt cắm**."""
        cfg = tmp_path / ".codex" / "config.toml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(CONFIG_CUA_KHACH, encoding="utf-8", newline="\n")
        goc_byte = cfg.read_bytes()

        tt = {}
        cc.cam_codex("https://x", tt)
        cc.cam_codex("https://x", {})              # tep trang thai MOI, mat tri nho
        cc.go_codex(tt)
        assert cfg.read_bytes() == goc_byte


def test_KHONG_duong_tep_nao_ra_NGOAI_thu_muc_tam_KE_CA_qua_bien_moi_truong(
        cc, tmp_path):
    """Bánh cóc thứ hai — cho những đường **không** đi qua `NHA`.

    🔴 Bánh cóc kia chỉ soi các **hằng** kiểu `Path`. `_vscode_settings()` là
       một **hàm** đọc `%APPDATA%`, nên nó lọt qua — và ngày 30/08 một phép kiểm
       mới đã ghi đè `settings.json` thật của VS Code trên máy chạy test. Không
       test nào đỏ; chỉ tình cờ đọc tệp đó ngay sau mới biết.

    ⇒ Ở đây gọi **thật** các hàm dựng đường dẫn rồi bắt chúng nằm trong tmp.
    """
    import pathlib as _pl
    tam = tmp_path.resolve()
    for ten in ("_vscode_settings",):
        d = getattr(cc, ten)()
        assert tam in _pl.Path(d).resolve().parents, (
            f"`{ten}()` tro RA NGOAI thu muc tam: {d}. Chan bien moi truong "
            f"tuong ung trong `_chan_duong_ra_ngoai`.")
    assert tam in cc.TEP_NHAT_KY.resolve().parents


class TestGoKhongCanKhoaVaKhongCanTriNho:
    """Hai ràng buộc đến từ cách khách **thực sự** dùng nút "Gỡ ra".

    ⭐ Khách bấm gỡ chính là lúc họ **thôi** dùng dịch vụ — thường để quay về tài
       khoản của họ. Lúc đó họ không còn cầm khoá API, và bắt họ dán lại khoá để
       gỡ là vô lý. Nên **không nhánh nào của `go` được đọc khoá**.

    ⭐ Và tệp trạng thái mất là chuyện thường (cài lại máy, đổi tài khoản
       Windows, một lượt `cam` sau ghi đè). Trước 30/08 gần như cả đường `go` đi
       qua trí nhớ đó, nên khi mất thì công cụ báo "đã gỡ" mà máy vẫn nguyên.
    """

    def test_go_codex_XOA_bang_provider_ta_sinh_ra_du_KHONG_co_tri_nho(self, cc):
        cfg = cc.NHA / ".codex" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cc.cam_codex("https://app.lttstudios.com", {})       # tt bi vut di
        assert "[model_providers.ltt]" in cfg.read_text(encoding="utf-8")

        ra = cc.go_codex({})                                 # KHONG tri nho
        van = cfg.read_text(encoding="utf-8")
        assert "[model_providers.ltt]" not in van, (
            "go de lai bang provider tro ve ta - khach doi tai khoan se hong")
        assert ra

    def test_go_codex_KHONG_dung_toi_bang_provider_cua_KHACH(self, cc):
        """Khách tự khai, trỏ về ta, nhưng **không phải** bản ta sinh ra."""
        cfg = _viet_cfg(cc, CONFIG_CO_SAN_LTT)
        goc = cfg.read_bytes()
        cc.go_codex({})
        assert cfg.read_bytes() == goc

    def test_go_desktop_van_xoa_chinh_sach_khi_MAT_tri_nho(self, cc):
        for ten, gt in (("inferenceProvider", "gateway"),
                        ("inferenceGatewayBaseUrl",
                         "https://app.lttstudios.com/api"),
                        ("inferenceModels", json.dumps([
                            {"name": h.tuyen_desktop,
                             "labelOverride": cc.NHAN_DESKTOP[h.tuyen_desktop]}
                            for h in cc.HO_SO_MODEL.values()],
                            separators=(",", ": ")))):
            cc._reg_ghi(cc.REG_DESKTOP_HKCU, ten, gt)

        ra = cc.go_desktop({})                               # KHONG tri nho
        assert ra, "im lang = khoa chinh sach nam lai vinh vien"
        assert cc._reg_doc(cc.REG_DESKTOP_HKCU, "inferenceProvider") is None

    def test_go_desktop_nhan_ra_tuyen_CU_sau_khi_nang_cap_va_mat_tri_nho(self, cc):
        """1.7 -> 1.8 must not strand the old policy and its dead API key."""
        cc._reg_ghi(cc.REG_DESKTOP_HKCU, "inferenceProvider", "gateway")
        cc._reg_ghi(cc.REG_DESKTOP_HKCU, "inferenceModels", json.dumps([
            {"name": "ltt-llm-claude-compat"}]))

        ra = cc.go_desktop({})

        assert ra
        assert cc._reg_doc(cc.REG_DESKTOP_HKCU, "inferenceProvider") is None
        assert cc._reg_doc(cc.REG_DESKTOP_HKCU, "inferenceModels") is None

    def test_go_desktop_KHONG_dung_chinh_sach_tro_di_CHO_KHAC(self, cc):
        cc._reg_ghi(cc.REG_DESKTOP_HKCU, "inferenceProvider", "gateway")
        cc._reg_ghi(cc.REG_DESKTOP_HKCU, "inferenceGatewayBaseUrl",
                    "https://gateway-cua-toi.local/api")
        cc.go_desktop({})
        assert cc._reg_doc(cc.REG_DESKTOP_HKCU, "inferenceProvider") == "gateway"

    def test_KHONG_ham_go_nao_NHAN_khoa(self, cc):
        """Banh coc: chu ky ham `go_*` khong duoc co tham so khoa.

        ⚠️ Ban dau toi viet phep kiem nay bang cach doc source va tim chu "khoa"
           trong tung dong — no do ngay o mot dong VUT khoa di
           (`for ten in CLAUDE_ENV + (ENV_KHOA_CLAUDE, ENV_KHOA_CODEX)`), tuc no
           do dung thu ta MUON co. Kiem CHU KY thi vua chat vua khong the doc
           nham: mot ham khong nhan khoa thi khong the dung khoa.
        """
        import inspect
        for ten in ("go_codex", "go_claude", "go_vscode", "go_desktop",
                    "quet_con_sot"):
            tham = list(inspect.signature(getattr(cc, ten)).parameters)
            assert not [t for t in tham if "khoa" in t.lower()], (
                f"`{ten}{tuple(tham)}` nhan khoa — nut go phai chay duoc khi "
                f"khach da khong con khoa nua")

    def test_lenh_go_chay_duoc_khi_KHONG_co_gi_ca(self, cc):
        """Khong tep trang thai, khong cau hinh, khong khoa -> van phai chay."""
        class _A:
            pass
        assert cc.lenh_go(_A()) == 0

    def test_lenh_go_XOA_HAN_tep_trang_thai(self, cc, capsys):
        cc.TEP_TRANG_THAI.parent.mkdir(parents=True, exist_ok=True)
        cc.TEP_TRANG_THAI.write_text(
            json.dumps({"goc": "https://x", "da_cam": True}), encoding="utf-8")

        class _A:
            pass
        cc.lenh_go(_A())
        assert not cc.TEP_TRANG_THAI.exists(), (
            "giu lai tep trang thai la giu lai dung thu khach vua bao khong can")
