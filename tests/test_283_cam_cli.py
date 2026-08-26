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
    ghi = {}
    env = {}
    monkeypatch.setattr(mod, "_setx",
                        lambda t, v: (env.__setitem__(t, v), True)[1])
    monkeypatch.setattr(mod, "_xoa_env",
                        lambda t: (env.pop(t, None), True)[1])
    monkeypatch.setattr(mod, "_doc_env_nguoi_dung", lambda t: env.get(t))
    monkeypatch.setattr(mod, "_reg_ghi",
                        lambda k, t, v: (ghi.__setitem__((k, t), v), True)[1])
    monkeypatch.setattr(mod, "_reg_xoa",
                        lambda k, t: (ghi.pop((k, t), None), True)[1])
    monkeypatch.setattr(mod, "_reg_doc", lambda k, t: ghi.get((k, t)))
    mod._registry_gia = ghi          # test doc duoc da ghi gi
    mod._env_gia = env
    (tmp_path / "AppData" / "Roaming" / "Code" / "User").mkdir(parents=True)
    return mod


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
    assert g[(k, "inferenceModels")] == '[{"name": "' + cc.MODEL_DESKTOP + '"}]'
    assert cc.MODEL_DESKTOP != cc.MODEL
    assert g[(k, "modelDiscoveryEnabled")] == "false"


def test_desktop_base_url_KHONG_kem_v1_va_phai_https(cc):
    """Tài liệu chốt hai điều, và cả hai đều hỏng lặng lẽ nếu sai.

    ⛔ `inferenceGatewayBaseUrl` là **gốc**, ứng dụng tự ghép `/v1/messages`.
       Kèm sẵn `/v1` là thành `/v1/v1/messages` ⇒ 404 không manh mối.
    ⛔ Và nó **bắt buộc HTTPS** (trừ loopback).
    """
    tt = {}
    cc.cam_desktop("https://app.lttstudios.com", "ltt_sk_x", tt)
    u = cc._registry_gia[(cc.REG_DESKTOP_HKCU, "inferenceGatewayBaseUrl")]
    assert u == "https://app.lttstudios.com/api"
    assert u.startswith("https://"), "tai lieu bat buoc HTTPS"
    assert not u.rstrip("/").endswith("/v1"), (
        "base_url KHONG duoc kem /v1 - ung dung tu ghep /v1/messages")


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


def test_kiem_PHAI_kiem_ca_be_mat_claude_desktop(cc):
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
