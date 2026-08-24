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

import pytest

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
    return mod


@pytest.fixture()
def cc(tmp_path):
    return _nap(tmp_path)


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
    monkeypatch.setattr(cc, "_setx", lambda *a: True)
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
