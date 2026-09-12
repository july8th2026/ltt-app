"""test_1238 — ba luat van hanh chot 13/09/2026 phai CON NGUYEN o moi cay.

## Vi sao can mot phep kiem cho vai doan van ban

Ba luat duoi day duoc chot trong mot phien, va ca ba deu de bien mat theo mot
kieu **im lang**:

| Luat | No song o dau | No mat nhu the nao |
|---|---|---|
| khong dung giua cac pha (§10b) | `docs/00_LTT_OPERATING_CONTRACT.md` | ai do don tai lieu |
| tra nguon truoc khi tu suy (§1b) | cung tep | nhu tren |
| Stop hook cuong che §10b | `tools/hook_khong_dung_giua_pha.py` | tep bi xoa / doi ten |

🔑 **Van ban khong tu bao ve duoc.** Chinh kho nay da ghi bai hoc do:
   *"luat viet ra khong mien nhiem cho nguoi viet — co hoc thang loi van"*.
   Tep nay la phan co hoc cua ba luat ay: chung di theo `git`, nen **moi
   worktree** deu mang chung, va gate o **moi cay** deu kiem chung.

## ⛔ Pham vi — cai gi tep nay KHONG kiem

No khong kiem Stop hook **da duoc cai** trong `settings.json`: tep cau hinh ay
nam ngoai git (`.claude/` gitignored, va user settings thi rieng cua tung may).
No chi kiem **cong cu van con o do de cai**. Mot phep kiem tu tuyen bo rong hon
thu no do la mot phep kiem noi doi — xem `pham-vi-phep-do-hep-hon-loi-tuyen-bo`.
"""
from __future__ import annotations

import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
HOP_DONG = GOC / "docs" / "00_LTT_OPERATING_CONTRACT.md"
HOOK = GOC / "tools" / "hook_khong_dung_giua_pha.py"


@pytest.fixture(scope="module")
def van() -> str:
    assert HOP_DONG.is_file(), f"khong thay {HOP_DONG}"
    return HOP_DONG.read_text(encoding="utf-8")


# ── Luat 1: khong dung giua cac pha (§10b) ────────────────────────────────

def test_luat_khong_dung_giua_cac_pha_con_trong_hop_dong(van):
    assert "KHÔNG DỪNG GIỮA CÁC PHA" in van, (
        "muc §10b da bien mat khoi hop dong van hanh")


def test_bon_dieu_kien_DUNG_van_duoc_liet_ke(van):
    """⛔ Luat "khong dung" ma khong kem dieu kien dung la mot luat NGUY HIEM.

    Bon thu VAN phai dung: gate do · thao tac khong dao duoc · thay doi khong ro
    cua ai · rui ro bao mat. Xoa chung di thi §10b tro thanh "chay tiep bang moi
    gia", va chinh phien 13/09 da phai vien den chung mot lan: xoa tai khoan lo
    mat khau se keo theo 272/297 dong so luot, nen viec dung la DUNG.
    """
    khoi = van[van.index("KHÔNG DỪNG GIỮA CÁC PHA"):]
    khoi = khoi[:khoi.index("# 11.")] if "# 11." in khoi else khoi
    for dau in ("Gate đỏ", "không đảo được", "chưa commit", "bảo mật"):
        assert dau in khoi, f"dieu kien dung `{dau}` da mat khoi §10b"


def test_UAC_khong_con_bi_goi_la_diem_dung(van):
    """May dat `ConsentPromptBehaviorAdmin = 0` ⇒ nang quyen IM LANG.

    Bao chu san pham "bam Yes" la bao ho cho mot hop thoai khong bao gio hien.
    """
    khoi = van[van.index("KHÔNG DỪNG GIỮA CÁC PHA"):]
    assert "nang_quyen.py" in khoi or "nâng quyền" in khoi, (
        "§10b khong con noi ve nang quyen im lang — phien sau se lai cho UAC")


def test_uy_quyen_KHONG_bao_gom_noi_ACL(van):
    """⛔ "Full quyen" nghia la dung dung lai hoi, KHONG phai ha muc an toan.

    ACL o `secrets\\` va `D:\\LTTBackups` la mot ban va bao mat DA HOAN THANH
    (W1.5). Mot luat uy quyen ma khong noi ro dieu nay la mot luat se bi doc
    thanh giay phep chay `icacls`.
    """
    khoi = van[van.index("KHÔNG DỪNG GIỮA CÁC PHA"):]
    assert "icacls" in khoi and "W1.5" in khoi, (
        "§10b khong con rao ACL — uy quyen de bi doc thanh giay phep noi ACL")


# ── Luat 2: tra nguon truoc khi tu suy (§1b) ──────────────────────────────

def test_luat_tra_nguon_con_trong_hop_dong(van):
    assert "TRA NGUỒN TRƯỚC KHI TỰ SUY" in van, (
        "muc §1b da bien mat khoi hop dong van hanh")


def test_tra_nguon_khai_DU_BA_nguon_va_thu_tu(van):
    """Mot luat "hay tra cuu" ma khong noi TRA O DAU thi khong ai tra duoc."""
    khoi = van[van.index("TRA NGUỒN TRƯỚC KHI TỰ SUY"):]
    khoi = khoi[:khoi.index("## 2.")]
    for nguon in ("huggingface.co", "llama.cpp", "curl"):
        assert nguon in khoi, f"§1b khong con tro toi `{nguon}`"
    assert "WebFetch" in khoi, (
        "§1b khong con canh bao WebFetch hong — phien sau se thu no truoc")


def test_phep_do_PHAN_BIET_van_con(van):
    """Phan gia tri nhat cua §1b: cach BIET mot tham so co bi bo qua khong.

    Gui ba gia tri khac nhau, xem dau ra co doi khong. Do la mot phep do, khong
    phai mot lap luan — va no re hon moi suy luan ve template."""
    khoi = van[van.index("TRA NGUỒN TRƯỚC KHI TỰ SUY"):]
    khoi = khoi[:khoi.index("## 2.")]
    assert "250 / 250 / 250" in khoi, (
        "vi du do phan biet da mat — luat con lai se chi la mot loi khuyen")


# ── Luat 3: cong cu cuong che van con o do ────────────────────────────────

def test_cong_cu_hook_van_con_va_chay_duoc():
    assert HOOK.is_file(), (
        f"{HOOK.name} da mat — luat §10b quay ve chi la van ban")
    ma = HOOK.read_text(encoding="utf-8")
    # Bon cua thoat: thieu mot cai la mot vong lap vo han dot token.
    for cua in ("stop_hook_active", "con_lai", "so_lan_chan", "tran"):
        assert cua in ma, f"hook mat cua thoat `{cua}` — nguy co vong lap vo han"


def test_hook_MAC_DINH_khong_lam_gi(tmp_path):
    """⛔ DOI CHUNG: khong co tep ke hoach thi hook PHAI im.

    Hook nay duoc cai o **user settings**, tuc no chay o MOI phien tren may —
    ke ca phien cua du an khac. Mot hook chan nham o do la mot hook se bi go,
    va di theo no la ca luat §10b.

    🔴 PHAI CHAY TREN MOT BAN CHEP O `tmp_path`, khong chay tep that.
       Hook tim ke hoach o `.claude/pha_dang_chay.json` **canh chinh no**. Chay
       ban that trong cay nay thi no thay ke hoach cua phien dang lam viec va
       chan dung — ban dau toi viet the va no DO, khong phai vi hook sai ma vi
       phep kiem doc trang thai NGOAI no.

    ⚠️ Do dung la cai bay `bay-trang-thai-ngoai-ro-vao-test`: rieng le thi ket
       qua tuy thuoc hom do co ke hoach hay khong — tuc mot phep kiem khong tra
       loi duoc cau hoi cua chinh no.
    """
    import json
    import shutil
    import subprocess
    import sys

    # Ban chep: `parents[1]` cua no la `tmp_path`, noi khong co `.claude/`.
    hop = tmp_path / "tools"
    hop.mkdir()
    ban_chep = hop / HOOK.name
    shutil.copy2(HOOK, ban_chep)

    r = subprocess.run([sys.executable, str(ban_chep)], input="{}",
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr[:300]
    assert not (r.stdout or "").strip(), (
        f"hook noi gi do khi khong co ke hoach: {r.stdout[:200]!r} — no se chan "
        f"moi phien tren may nay")

    # Va voi `stop_hook_active` thi phai im KE CA khi co ke hoach — day la cua
    # chong lap cua chinh harness, kiem tren ban that moi co nghia.
    r2 = subprocess.run([sys.executable, str(HOOK)],
                        input=json.dumps({"stop_hook_active": True}),
                        capture_output=True, text=True, timeout=30)
    assert r2.returncode == 0 and not (r2.stdout or "").strip(), (
        f"hook khong ton trong `stop_hook_active`: {r2.stdout[:200]!r}")


def test_hook_CHAN_khi_ke_hoach_con_viec(tmp_path):
    """⛔ Doi chung NGUOC cua ca tren: no phai that su chan khi co viec.

    Khong co ca nay thi cach lam ca tren xanh de nhat — bo hook di — cung dat.
    """
    import json
    import shutil
    import subprocess
    import sys

    hop = tmp_path / "tools"
    hop.mkdir()
    shutil.copy2(HOOK, hop / HOOK.name)
    kh = tmp_path / ".claude"
    kh.mkdir()
    (kh / "pha_dang_chay.json").write_text(
        json.dumps({"con_lai": ["viec A"], "so_lan_chan": 0, "tran": 5}),
        encoding="utf-8")

    r = subprocess.run([sys.executable, str(hop / HOOK.name)], input="{}",
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr[:300]
    d = json.loads(r.stdout)
    assert d.get("decision") == "block", d
    assert "viec A" in d.get("reason", ""), "reason khong noi VIEC KE TIEP"
