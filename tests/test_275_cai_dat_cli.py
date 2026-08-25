"""
test_275_cai_dat_cli — công cụ tự ghi cấu hình cho khách. (H38, C15)

⭐ VÌ SAO NÓ ĐÁNG CÓ TEST. Nó **ghi vào file trong home của khách**. Một công cụ
   như thế sai một lần là hỏng cấu hình của người khác, và người đó sẽ không
   quay lại.

Bốn tính chất neo ở đây, và cả bốn đều về việc **không làm hỏng thứ đang có**:

  1. **Cộng thêm, không đè.** `model` mặc định và provider khác của khách phải
     còn nguyên.
  2. **Sao lưu trước khi chạm.**
  3. 🔴 **Không bao giờ ghi khoá vào file cấu hình.** File cấu hình bị chia sẻ,
     bị commit, bị chụp màn hình.
  4. **Chạy lại được** — lần hai không tạo bản sao thứ hai.
"""
from __future__ import annotations

import json
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sdk"))
import ltt_cai_dat_cli as cd  # noqa: E402

KHOA = "ltt_sk_khoa_gia_de_test_khong_that"


def test_codex_CONG_THEM_khong_de(tmp_path):
    """Khách đã có `model = "gpt-5.6-sol"` và một provider khác. Cả hai phải sống."""
    goc = tmp_path / ".codex"
    goc.mkdir()
    cu = 'model = "gpt-5.6-sol"\n\n[model_providers.khac]\nname = "Khac"\n'
    (goc / "config.toml").write_text(cu, encoding="utf-8")

    cd.codex("https://app.lttstudios.com", goc)
    moi = (goc / "config.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.6-sol"' in moi, "da de mat model mac dinh cua khach"
    assert "[model_providers.khac]" in moi, "da de mat provider khac"
    assert "[model_providers.ltt]" in moi


def test_codex_SAO_LUU_truoc_khi_cham(tmp_path):
    goc = tmp_path / ".codex"; goc.mkdir()
    (goc / "config.toml").write_text('model = "cu"\n', encoding="utf-8")
    cd.codex("https://x.test", goc)
    bak = goc / "config.toml.ltt-bak"
    assert bak.exists() and 'model = "cu"' in bak.read_text(encoding="utf-8")


def test_codex_ho_so_o_FILE_RIENG(tmp_path):
    """🔴 Codex 0.145+ TỪ CHỐI `[profiles.X]` nằm trong `config.toml`."""
    goc = tmp_path / ".codex"
    cd.codex("https://x.test", goc)
    assert (goc / "ltt.config.toml").exists()
    assert "[profiles." not in (goc / "config.toml").read_text(encoding="utf-8")


def test_chay_lai_KHONG_tao_ban_sao(tmp_path):
    goc = tmp_path / ".codex"
    cd.codex("https://x.test", goc)
    cd.codex("https://x.test", goc)
    assert (goc / "config.toml").read_text(encoding="utf-8").count(
        "[model_providers.ltt]") == 1


def test_claude_code_GIU_env_cu(tmp_path):
    goc = tmp_path / ".claude"; goc.mkdir()
    (goc / "settings.json").write_text(json.dumps(
        {"env": {"CUA_TOI": "giu-lai"}, "theme": "dark"}), encoding="utf-8")
    cd.claude_code("https://x.test", goc)
    d = json.loads((goc / "settings.json").read_text(encoding="utf-8"))
    assert d["env"]["CUA_TOI"] == "giu-lai", "da de mat bien cua khach"
    assert d["theme"] == "dark", "da de mat cai dat khac cua khach"
    assert d["env"]["ANTHROPIC_BASE_URL"].endswith("/api")


def test_claude_code_dat_du_CA_HAI_model(tmp_path):
    """`ANTHROPIC_DEFAULT_HAIKU_MODEL` là cái ai cũng quên, và quên thì việc nền
    của Claude Code hỏng **âm thầm** trong khi phiên chính trông vẫn ổn."""
    goc = tmp_path / ".claude"
    cd.claude_code("https://x.test", goc)
    env = json.loads((goc / "settings.json").read_text(encoding="utf-8"))["env"]
    assert env["ANTHROPIC_MODEL"] == cd.MODEL
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == cd.MODEL


def test_settings_json_hong_thi_KHONG_DAM_SUA(tmp_path):
    """⛔ Thà không làm gì còn hơn ghi đè một file ta không đọc được."""
    goc = tmp_path / ".claude"; goc.mkdir()
    rac = "{ khong phai json"
    (goc / "settings.json").write_text(rac, encoding="utf-8")
    ra = cd.claude_code("https://x.test", goc)
    assert (goc / "settings.json").read_text(encoding="utf-8") == rac
    assert any("BO QUA" in d for d in ra)


# ── 🔴 Khoá không bao giờ vào file ─────────────────────────────────────────

def test_KHOA_KHONG_BAO_GIO_vao_file_cau_hinh(tmp_path):
    """File cấu hình bị chia sẻ, bị commit, bị chụp màn hình."""
    cd.codex("https://x.test", tmp_path / ".codex")
    cd.claude_code("https://x.test", tmp_path / ".claude")
    for p in tmp_path.rglob("*"):
        if p.is_file():
            assert KHOA not in p.read_text(encoding="utf-8", errors="replace")
            assert "ltt_sk_" not in p.read_text(encoding="utf-8", errors="replace")


def test_cau_hinh_chi_NEU_TEN_bien_moi_truong(tmp_path):
    goc = tmp_path / ".codex"
    cd.codex("https://x.test", goc)
    assert f'env_key = "{cd.BIEN_KHOA}"' in (goc / "config.toml").read_text(encoding="utf-8")


# ── Hai địa chỉ lệch nhau bốn ký tự ────────────────────────────────────────

def test_HAI_DIA_CHI_khac_nhau_dung_cach(tmp_path):
    """Đổi chỗ hai địa chỉ này là 404 không manh mối: Codex ghép `/responses`,
    Claude ghép `/v1/messages`."""
    cd.codex("https://app.lttstudios.com", tmp_path / ".codex")
    cd.claude_code("https://app.lttstudios.com", tmp_path / ".claude")
    codex_cfg = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    claude_env = json.loads(
        (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))["env"]
    assert 'base_url = "https://app.lttstudios.com/api/v1"' in codex_cfg
    assert claude_env["ANTHROPIC_BASE_URL"] == "https://app.lttstudios.com/api"


def test_thieu_khoa_thi_chi_duong_lay_khoa(capsys):
    rc = cd.main(["--key", "", "--home", "."])
    assert rc == 2
    assert "/developers/keys" in capsys.readouterr().out


def test_desktop_KHONG_noi_doi_la_da_cau_hinh():
    """Claude Desktop không có file nào để ghi. In các bước còn hơn nói dối."""
    ra = " ".join(cd.claude_desktop("https://x.test"))
    assert "Third-Party Inference" in ra
    assert "inferenceModels" in ra


# ── Cloudflare chặn User-Agent mặc định của urllib ──────────────────────────
#
# 🔴 LỖI KHÁCH SẼ GẶP, VÀ TA SUÝT SHIP NÓ. Đo thật 24/08, cùng một khoá, cùng
#    một URL:
#
#        urllib mac dinh (`Python-urllib/3.x`)  ->  403
#        bat ky User-Agent nao khac             ->  200
#
#    Cloudflare từ chối **trước khi** request tới máy chủ ta, nên log của ta
#    không có gì cả — khách thấy 403 và ta thấy im lặng.
#
# ⚠️ Test cũ (`test_vi_du_trong_tai_lieu_la_ma_CHAY_DUOC`) chỉ **biên dịch** đoạn
#    mã. Biên dịch được không có nghĩa là chạy được. Đây đúng là QT-14.

def test_vi_du_khong_thu_vien_PHAI_gui_User_Agent():
    """Ví dụ ta ship cho khách mà thiếu header này thì khách nhận 403."""
    from platform_core.public_api import examples

    ma = dict(examples.chat_snippets())["Python — no dependencies"]
    assert "User-Agent" in ma, (
        "vi du dung urllib ma khong dat User-Agent -> Cloudflare tra 403")


def test_cong_cu_cai_dat_cung_gui_User_Agent():
    import inspect
    import ltt_cai_dat_cli as cd

    assert "User-Agent" in inspect.getsource(cd.kiem_tra)


def test_moi_vi_du_dung_urllib_deu_co_User_Agent():
    """Quét mọi ví dụ, không chỉ cái ta nhớ ra."""
    from platform_core.public_api import examples

    for nhan, ma in examples.chat_snippets():
        if "urllib" in ma:
            assert "User-Agent" in ma, f"vi du {nhan!r} dung urllib ma thieu UA"
