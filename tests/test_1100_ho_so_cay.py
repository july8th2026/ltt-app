"""Ho so van hanh cua mot cay: `NORMAL` / `FAST_BUILD` (hop dong muc 4.10).

## Ba menh de duoc chot o day, va vi sao chinh ba cai nay

1. **Trang thai KHONG nam trong cay lam viec.** Neu no nam trong cay thi
   `gate._anh_chup_cay()` se thay no doi giua mot luot chay va tu vut bo phep do
   cua chinh no (`docs/QUY_TRINH_WORKTREE.md` muc 4), va `robocopy` cua deploy
   se chep no len may chu. Ca hai deu la loi IM LANG.

2. **`--doi --tu <moc>` do NHIEU HON `--doi`.** Day la ca ly do co che nay ton
   tai: mot chien dich dai co commit checkpoint lam `HEAD` nuot mat phan dau,
   nen `--doi` mac dinh bao xanh tren mot phep do BO SOT. Phep kiem duoi day
   dung git that, khong dung mot ban gia lap - vi thu can chung minh chinh la
   git tra ve gi.

3. **May trang thai khong cho nhay buoc.** `RESEARCH -> CERTIFYING` phai bi tu
   choi, nếu khong thi `FEATURE_COMPLETE` (dong bang tap tinh nang) chi la mot
   loi khuyen.

⛔ Khong chot o day: danh sach buoc gate, ngan sach loi, anh xa test. Chung co
   chu roi, va mot ban sao thu hai la mot ban sao se lech.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))
import gate  # noqa: E402
import ho_so_cay as hsc  # noqa: E402
import thanh_phan as tp  # noqa: E402


# ── 1. Trang thai nam NGOAI cay lam viec ────────────────────────────────────

def test_tep_trang_thai_nam_trong_thu_muc_git_rieng() -> None:
    tep = hsc.tep_trang_thai()
    thu_muc_git = Path(subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"], cwd=str(GOC),
        capture_output=True, text=True, check=True).stdout.strip()).resolve()
    assert tep.parent.resolve() == thu_muc_git


def test_trang_thai_khong_lot_vao_anh_chup_cua_gate() -> None:
    """`gate.THU_MUC_CHUP` la danh sach thu muc gate chup truoc/sau mot luot.

    Mot tep trang thai nam trong do se lam gate bao "CAY DA DOI" va tu vut bo
    phep do - mat ~12 phut khong thu duoc gi.
    """
    tep = hsc.tep_trang_thai().resolve()
    for thu_muc in gate.THU_MUC_CHUP:
        duong = (GOC / thu_muc).resolve()
        assert not tep.is_relative_to(duong), (
            f"trang thai nam trong {thu_muc} - gate se tu vut bo phep do")


def test_ten_tep_trang_thai_bi_gitignore() -> None:
    """Mot ban sao dat NHAM CHO cung phai vo hinh voi git.

    Duong dung la `.git/worktrees/<ten>/`, nen git khong bao gio thay no. Nhung
    "khong bao gio" o day dua vao mot dong ma; mot phien sau doi cho dat tep se
    lam no lot vao cay, va deploy chep CA CAY ke ca tep chua theo doi.

    ⛔ Phep kiem nay KHONG tao tep thu trong kho: mot phien khac co the dang
       chay gate, va mot tep la xuat hien giua chung la dung cai bay
       `docs/BAY_TRONG_CONG_CHAT_LUONG.md` mo ta. `git check-ignore` tra loi ma
       khong cham dia.
    """
    r = subprocess.run(["git", "check-ignore", "-q", hsc.TEN_TEP],
                       cwd=str(GOC), capture_output=True)
    assert r.returncode == 0, (
        f"`{hsc.TEN_TEP}` chua bi .gitignore loai. Them no vao .gitignore.")


# ── 2. `--tu <moc>` do NHIEU HON `--doi` ────────────────────────────────────

def _kho_git(tmp_path: Path) -> Path:
    """Mot kho git that, hai commit, mot tep dang do. Tat dinh, khong bo qua.

    ⚠️ `user.name`/`user.email` dat **cuc bo cho kho nay**, khong doc cau hinh
       toan cuc: mot may CI khong khai danh tinh se lam `git commit` that bai,
       va phep kiem khi ay do vi moi truong chu khong vi ma.
    """
    kho = tmp_path / "kho"
    kho.mkdir()

    def g(*a: str) -> None:
        subprocess.run(["git", *a], cwd=str(kho), check=True,
                       capture_output=True)

    g("init", "-q")
    g("config", "user.email", "kiem@ltt.local")
    g("config", "user.name", "kiem")
    g("config", "commit.gpgsign", "false")
    (kho / "goc.txt").write_bytes(b"1\n")
    g("add", "goc.txt")
    g("commit", "-q", "--no-verify", "-m", "commit mot")

    (kho / "trong_commit.txt").write_bytes(b"2\n")
    g("add", "trong_commit.txt")
    g("commit", "-q", "--no-verify", "-m", "commit hai")

    (kho / "dang_do.txt").write_bytes(b"3\n")
    return kho



def test_moc_baseline_bao_trum_pham_vi_mac_dinh(tmp_path: Path) -> None:
    """`duong_da_doi(goc_so=<cha>)` phai la TAP CHA THAT SU cua `duong_da_doi()`.

    ⛔ Phep kiem nay **khong hoi lich su cua kho nay**, va do la chu y. Ban dau
       no doc `HEAD~1` cua chinh kho, nen no phai mang mot `pytest.skip` cho
       truong hop "cay chi co mot commit" — va mot cho bo qua la mot cho **khong
       canh gi ca**. Bo do `tools/check_bo_qua.py` bat dung diem ay o luot gate
       dau tien: hai cho bo qua MOI, `RESULT: FAIL`.

    ⭐ Bo do dung. Cau phai chung minh la mot menh de ve `duong_da_doi`, khong
       phai ve lich su cua kho — nen dung kho rieng, dung tat dinh, khong bo qua.

    Hai ve trong MOT phep kiem, vi ve thu hai la **doi chung** cua ve thu nhat:
    "tap cha" mot minh van xanh khi `goc_so` bi nuot im lang (moi tap la tap cha
    cua chinh no).
    """
    kho = _kho_git(tmp_path)
    mac_dinh = tp.duong_da_doi(kho)
    tu_moc = tp.duong_da_doi(kho, goc_so="HEAD~1")

    # `dang_do.txt` chua commit -> co o CA HAI tap.
    assert "dang_do.txt" in mac_dinh
    # `trong_commit.txt` chi doi trong commit thu hai -> CHI co khi lui moc.
    assert "trong_commit.txt" not in mac_dinh
    assert "trong_commit.txt" in tu_moc
    # Tap cha, va la tap cha THAT SU.
    assert mac_dinh < tu_moc


def test_gate_tu_choi_tu_khi_khong_co_doi() -> None:
    """`--tu` mot minh la mot pham vi HEP ma nguoi goi tuong la rong."""
    r = subprocess.run([sys.executable, "tools/gate.py", "--tu", "HEAD"],
                       cwd=str(GOC), capture_output=True, text=True, timeout=120)
    assert r.returncode != 0
    assert "--tu" in (r.stderr + r.stdout)


# ── 3. May trang thai ───────────────────────────────────────────────────────

def test_moi_trang_thai_deu_co_mat_trong_bang_chuyen() -> None:
    assert set(hsc.CHUYEN_DUOC) == set(hsc.TRANG_THAI)
    for dich in (d for cac in hsc.CHUYEN_DUOC.values() for d in cac):
        assert dich in hsc.TRANG_THAI


def test_khong_nhay_qua_feature_complete() -> None:
    assert "CERTIFYING" not in hsc.CHUYEN_DUOC["RESEARCH"]
    assert "CERTIFYING" not in hsc.CHUYEN_DUOC["BUILDING"]
    assert "READY_TO_MERGE" not in hsc.CHUYEN_DUOC["FEATURE_COMPLETE"]


def test_duong_lui_ve_building_ton_tai() -> None:
    """Mot lan chung nhan do co the buoc quay ve lam viec. Duong do phai CO,
    va phai duoc ghi lai - chu khong phai xoa tep trang thai roi bat lai."""
    assert "BUILDING" in hsc.CHUYEN_DUOC["CERTIFYING"]


def test_chuyen_ghi_lich_su(tmp_path: Path, monkeypatch: pytest.MonkeyPatch
                            ) -> None:
    tep = tmp_path / hsc.TEN_TEP
    monkeypatch.setattr(hsc, "tep_trang_thai", lambda: tep)
    hsc.ghi({"ho_so": "FAST_BUILD", "baseline_sha": "0" * 40,
             "pham_vi": "thu", "trang_thai": "RESEARCH", "bat_dau": "x"})
    hsc._chuyen("building")
    du_lieu = json.loads(tep.read_text(encoding="utf-8"))
    assert du_lieu["trang_thai"] == "BUILDING"
    assert du_lieu["lich_su"][-1] == {"tu": "RESEARCH", "toi": "BUILDING",
                                      "luc": du_lieu["lich_su"][-1]["luc"]}
    with pytest.raises(SystemExit):
        hsc._chuyen("READY_TO_MERGE")


# ── 4. Chot CO HOC: FAST_BUILD khong bat duoc o cho khong duoc phep ─────────

# `main` thay `admin-mvp-v3` (16/09): trunk cu da bi xoa, `ho_so_cay.TRUNK` nay la `main`.
@pytest.mark.parametrize("nhanh", ["main", "master",
                                   "h42-release-clean", "phien/phat-hanh-x"])
def test_khong_bat_duoc_fast_build_tren_nhanh_trunk_hay_phat_hanh(
        nhanh: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hsc, "tep_trang_thai", lambda: tmp_path / hsc.TEN_TEP)
    monkeypatch.setattr(hsc, "la_cay_chinh", lambda: False)
    monkeypatch.setattr(hsc, "_nhanh", lambda: nhanh)
    with pytest.raises(SystemExit):
        hsc._bat("thu")


def test_khong_bat_duoc_fast_build_tren_cay_chinh(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hsc, "tep_trang_thai", lambda: tmp_path / hsc.TEN_TEP)
    monkeypatch.setattr(hsc, "la_cay_chinh", lambda: True)
    monkeypatch.setattr(hsc, "_nhanh", lambda: "claude/mot-tinh-nang")
    with pytest.raises(SystemExit):
        hsc._bat("thu")


def test_bat_doi_pham_vi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch
                         ) -> None:
    monkeypatch.setattr(hsc, "tep_trang_thai", lambda: tmp_path / hsc.TEN_TEP)
    monkeypatch.setattr(hsc, "la_cay_chinh", lambda: False)
    monkeypatch.setattr(hsc, "_nhanh", lambda: "claude/mot-tinh-nang")
    with pytest.raises(SystemExit):
        hsc._bat("   ")


# ── 5. Cong cu tro ve hop dong, khong tu dinh nghia luat ───────────────────

def test_cong_cu_tro_ve_hop_dong_canonical() -> None:
    """Neu tep nay tu ke luat thi kho co hai nguon luat - dung benh ma
    `tools/check_luat_van_hanh.py` sinh ra de chua."""
    ma = (GOC / "tools" / "ho_so_cay.py").read_text(encoding="utf-8")
    assert "docs/00_LTT_OPERATING_CONTRACT.md" in ma


def test_hop_dong_co_muc_4_10() -> None:
    van = (GOC / "docs" / "00_LTT_OPERATING_CONTRACT.md").read_text(
        encoding="utf-8")
    assert "## 4.10" in van
    for trang_thai in hsc.TRANG_THAI:
        assert trang_thai in van, f"hop dong khong noi ve `{trang_thai}`"
# -- 6. Governance: PHAN BIET "cu" voi "di truoc" --------------------------

def _kho_governance(tmp_path: Path, tep: str, ai_sua: str) -> Path:
    """Kho git hai nhanh. `ai_sua` = "toi" hoac "trunk"."""
    kho = tmp_path / ("gov_" + ai_sua)
    kho.mkdir()

    def g(*a: str) -> None:
        subprocess.run(["git", *a], cwd=str(kho), check=True,
                       capture_output=True)

    g("init", "-q", "-b", "trunk-gia")
    g("config", "user.email", "kiem@ltt.local")
    g("config", "user.name", "kiem")
    (kho / tep).parent.mkdir(parents=True, exist_ok=True)
    (kho / tep).write_text("ban goc", encoding="utf-8")
    g("add", tep)
    g("commit", "-q", "--no-verify", "-m", "goc")
    g("checkout", "-q", "-b", "nhanh-cua-toi")
    if ai_sua == "toi":
        (kho / tep).write_text("ban goc + phan cua toi", encoding="utf-8")
        g("add", tep)
        g("commit", "-q", "--no-verify", "-m", "toi sua governance")
    else:
        g("checkout", "-q", "trunk-gia")
        (kho / tep).write_text("trunk da di tiep", encoding="utf-8")
        g("add", tep)
        g("commit", "-q", "--no-verify", "-m", "trunk sua governance")
        g("checkout", "-q", "nhanh-cua-toi")
    return kho


def test_governance_phan_biet_CU_voi_DI_TRUOC(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch
                                              ) -> None:
    """Mot cay DI TRUOC trunk khong duoc bao la CU.

    Loi that, do 09/09 tren chinh cay viet ra cong cu nay: no di truoc trunk
    3 commit, va `trang-thai` bao "LECH trunk -> git merge admin-mvp-v3".
    Loi khuyen ay khong sai vo hai - no bao nguoi ta lam mot viec KHONG lam gi
    ca, giua mot chien dich dang do. Sai so day ve phia HANH DONG THUA.

    Thu phan biet duoc hai chieu la DIEM HOA, khong phai hai dau mut.
    """
    tep = "docs/00_LTT_OPERATING_CONTRACT.md"
    monkeypatch.setattr(hsc, "GOC", _kho_governance(tmp_path, tep, "toi"))
    monkeypatch.setattr(hsc, "TRUNK", "trunk-gia")
    monkeypatch.setattr(hsc, "TEP_GOVERNANCE", (tep,))
    cu, di_truoc = hsc.governance_lech()
    assert di_truoc == [tep]
    assert cu == [], ("cay DI TRUOC bi bao la CU -> nguoi doc se `git merge` "
                      "mot thu khong co gi de gop")


def test_governance_van_bat_duoc_cay_CU(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch
                                        ) -> None:
    """Doi chung: chieu nguoc lai phai VAN bao `cu`.

    Thieu phep kiem nay thi mot ban sua "luon tra di_truoc" cung xanh - va bo
    do khi ay bat duoc 0 cay cu, dung thu no sinh ra de bat.
    """
    tep = "tools/gate.py"
    monkeypatch.setattr(hsc, "GOC", _kho_governance(tmp_path, tep, "trunk"))
    monkeypatch.setattr(hsc, "TRUNK", "trunk-gia")
    monkeypatch.setattr(hsc, "TEP_GOVERNANCE", (tep,))
    cu, di_truoc = hsc.governance_lech()
    assert cu == [tep]
    assert di_truoc == []
