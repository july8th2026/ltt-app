"""`setup/dat_bien_env.ps1` — dat MOT bien trong app.env, an toan.

## Vi sao cong cu nay ton tai

`setup/cong_tac_tool_api.ps1` da tra gia de hoc **ba cach hong im lang** khi sua
`app.env` bang tay. Nhung no chi che **dung mot** bien
(`LTT_PUBLIC_API_TOOLS`) — trong khi ba cach hong do ap cho **moi** bien:

  1. BOM  -> `json.load()` vo o cho khac, `/health/ready` tra 503 trong khi dich
     vu van chay. Loi nay DA THUC SU LAM SAP PRODUCTION o du an nay.
  2. Go de len mot dong khac -> mat mot bien dang phuc vu, khong ai biet.
  3. Sua xong roi restart    -> KHONG AN GI (nssm nuong env luc CAI).

Ngay 29/08 phai dat `LTT_GPU_MONG_DOI` va khong co cong cu nao, nen phai viet
mot script MOT LAN trong thu muc tam. Tep nay va script kem theo la de khong con
lan sau.

## Cai bay tep nay canh

⛔ **Bi mat khong duoc di qua dong lenh** — no vao lich su shell, vao log, vao
ban ghi tien trinh. Script TU CHOI cac ten trong nhu bi mat, va phep kiem duoi
day chot dieu do. Mot cong cu tien tay khien nguoi ta dat `LTT_..._SECRET` bang
mot dong lenh la mot cong cu lam ro ri de hon.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = GOC / "setup" / "dat_bien_env.ps1"

MAU = "LTT_ENV=production\nLTT_GPU=cu\nLTT_PUBLIC_API_TOOLS=text.chat\n"


def _chay(env_file: pathlib.Path, *args: str):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(SCRIPT), "-EnvFile", str(env_file), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120)


@pytest.fixture()
def envfile(tmp_path):
    p = tmp_path / "app.env"
    p.write_bytes(MAU.encode("utf-8"))
    return p


def test_script_co_that_va_thuan_ascii():
    b = SCRIPT.read_bytes()
    assert b[:3] != b"\xef\xbb\xbf", "script setup khong duoc co BOM"
    assert all(x < 128 for x in b), "tep .ps1 phai thuan ASCII (CLAUDE.md quy tac 2)"


# ── Duong thanh cong ────────────────────────────────────────────────────────

def test_them_bien_moi(envfile):
    r = _chay(envfile, "-Ten", "LTT_GPU_MONG_DOI", "-Gia_tri", "2")
    assert r.returncode == 0, r.stdout + r.stderr
    txt = envfile.read_text(encoding="utf-8")
    assert "LTT_GPU_MONG_DOI=2" in txt
    # Cac bien cu con nguyen — day la cach hong so 2.
    for cu in ("LTT_ENV=production", "LTT_GPU=cu",
               "LTT_PUBLIC_API_TOOLS=text.chat"):
        assert cu in txt, cu


def test_ghi_de_bien_da_co(envfile):
    assert _chay(envfile, "-Ten", "LTT_GPU", "-Gia_tri", "moi").returncode == 0
    txt = envfile.read_text(encoding="utf-8")
    assert "LTT_GPU=moi" in txt and "LTT_GPU=cu" not in txt
    # Dung MOT dong, khong sinh dong thu hai.
    assert sum(1 for d in txt.splitlines() if d.startswith("LTT_GPU=")) == 1


def test_tien_to_KHONG_khop_nham_bien_dai_hon(tmp_path):
    """🔴 `LTT_GPU` khong duoc khop `LTT_GPU_MONG_DOI`.

    Day la cach hong so 2 o dang tinh vi nhat: `StartsWith` se go de len mot bien
    KHAC ma ten no chi tinh co bat dau giong nhau. Script dung bo chon neo dau
    dong (`^\\s*TEN\\s*=`).

    ⚠️ THU TU DONG LA MOT PHAN CUA PHEP KIEM, khong phai chi tiet ngau nhien.
       Ban dau phep kiem nay dat `LTT_GPU_MONG_DOI` SAU `LTT_GPU`, va no **xanh
       ca khi thay bo chon bang `StartsWith`** — vi vong quet tu tren xuong gap
       `LTT_GPU=` truoc. Kiem-co-rang bat duoc dieu do: mot phep kiem trong nhu
       dung ma khong chung minh gi. Nay bien DAI hon dung TRUOC.
    """
    p = tmp_path / "app.env"
    p.write_bytes(b"LTT_GPU_MONG_DOI=2\nLTT_GPU=cu\n")
    assert _chay(p, "-Ten", "LTT_GPU", "-Gia_tri", "moi").returncode == 0
    txt = p.read_text(encoding="utf-8")
    assert "LTT_GPU=moi" in txt
    assert "LTT_GPU_MONG_DOI=2" in txt, "bien dai hon bi go de"


def test_xoa_bien(envfile):
    assert _chay(envfile, "-Ten", "LTT_GPU", "-Xoa").returncode == 0
    txt = envfile.read_text(encoding="utf-8")
    assert "LTT_GPU=" not in txt
    assert "LTT_ENV=production" in txt


def test_dat_lai_dung_gia_tri_thi_KHONG_doi_gi(envfile):
    truoc = envfile.read_bytes()
    r = _chay(envfile, "-Ten", "LTT_GPU", "-Gia_tri", "cu")
    assert r.returncode == 0
    assert envfile.read_bytes() == truoc, "ghi lai y nguyen van tao mot ban sao luu thua"


def test_ghi_KHONG_BOM(envfile):
    """🔴 Quy tac 1 cua CLAUDE.md. `Out-File -Encoding utf8` tren PowerShell 5.1
    chen BOM, `json.load()` vo, `/health/ready` tra 503 trong khi dich vu van
    chay — va loi nay DA lam sap production o du an nay."""
    _chay(envfile, "-Ten", "LTT_MOI", "-Gia_tri", "1")
    assert envfile.read_bytes()[:3] != b"\xef\xbb\xbf"


def test_giu_nguyen_kieu_xuong_dong_CRLF(tmp_path):
    """Doi LF thanh CRLF tren ca tep la mot diff gia lam an mat thay doi that."""
    p = tmp_path / "app.env"
    p.write_bytes(MAU.replace("\n", "\r\n").encode("utf-8"))
    _chay(p, "-Ten", "LTT_MOI", "-Gia_tri", "1")
    b = p.read_bytes()
    assert b.count(b"\r\n") >= 3
    assert b.replace(b"\r\n", b"").count(b"\n") == 0, "tron hai kieu xuong dong"


def test_sao_luu_truoc_khi_ghi(envfile):
    _chay(envfile, "-Ten", "LTT_MOI", "-Gia_tri", "1")
    ban_sao = list(envfile.parent.glob("app.env.truoc-*"))
    assert ban_sao, "khong sao luu truoc khi ghi"
    assert ban_sao[0].read_bytes() == MAU.encode("utf-8")


# ── Duong TU CHOI ───────────────────────────────────────────────────────────

def test_BOM_thi_DUNG_LAI_chu_khong_tu_sua(tmp_path):
    """⛔ Mot tep bi mat dang hong thi khong tu sua — bao roi dung."""
    p = tmp_path / "app.env"
    p.write_bytes(b"\xef\xbb\xbf" + MAU.encode("utf-8"))
    truoc = p.read_bytes()
    r = _chay(p, "-Ten", "LTT_MOI", "-Gia_tri", "1")
    assert r.returncode == 2, r.stdout
    assert "BOM" in r.stdout
    assert p.read_bytes() == truoc, "da cham vao mot tep bi mat dang hong"


@pytest.mark.parametrize("ten", [
    "LTT_SESSION_SECRET", "LTT_API_KEY_PEPPER", "MY_TOKEN", "DB_PASSWORD",
    "LTT_TOKEN_ENCRYPTION_KEY", "LTT_SENTRY_DSN",
])
def test_TU_CHOI_ten_trong_nhu_bi_mat(envfile, ten):
    """⛔ Bi mat khong di qua dong lenh: no vao lich su shell, vao log, vao ban
    ghi tien trinh.

    ⭐ Mot cong cu tien tay khien nguoi ta dat `..._SECRET` bang mot dong lenh la
       mot cong cu lam ro ri DE HON. Nen tien loi phai dung lai o day.
    """
    truoc = envfile.read_bytes()
    r = _chay(envfile, "-Ten", ten, "-Gia_tri", "gi-do")
    assert r.returncode == 4, r.stdout + r.stderr
    assert envfile.read_bytes() == truoc


def test_ten_khong_hop_le_bi_tu_choi(envfile):
    r = _chay(envfile, "-Ten", "co dau cach", "-Gia_tri", "1")
    assert r.returncode == 3, r.stdout


def test_thieu_gia_tri_bi_tu_choi(envfile):
    r = _chay(envfile, "-Ten", "LTT_MOI")
    assert r.returncode == 3, r.stdout


# ── Xem: khong duoc in GIA TRI ──────────────────────────────────────────────

def test_xem_chi_in_TEN_khong_in_gia_tri(envfile):
    """⛔ Mot cong cu van hanh in gia tri bien la mot cong cu ro ri bi mat vao
    log, vao anh chup man hinh, vao ban ghi phien."""
    r = _chay(envfile, "-Xem")
    assert r.returncode == 0, r.stdout
    assert "LTT_PUBLIC_API_TOOLS" in r.stdout
    assert "text.chat" not in r.stdout, "da in GIA TRI cua bien"
    assert "production" not in r.stdout


# ── Nhac nap lai env ────────────────────────────────────────────────────────

def test_LUON_nhac_nap_lai_env(envfile):
    """🔴 Cach hong so 3: sua app.env roi `Restart-Service` la KHONG AN GI.

    nssm nuong bien moi truong vao dang ky dich vu luc CAI. Da dinh hai lan
    trong du an nay, trieu chung giong het nhau ca hai lan: cau hinh dung, dich
    vu chay, tinh nang khong bat.
    """
    r = _chay(envfile, "-Ten", "LTT_MOI", "-Gia_tri", "1")
    assert "nap_lai_env.ps1" in r.stdout
    assert "CHUA CO TAC DUNG" in r.stdout
