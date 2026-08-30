"""
P9 — deployment script sanity checks.

Guards a real bug found while building the package: Windows PowerShell 5.1
reads a .ps1 file using the system ANSI codepage unless it has a UTF-8
BOM. An em-dash in a message string therefore turned into mojibake and
broke the parser with "The string is missing the terminator" — a
deployment script that fails to parse on the target server is worse than
no script, because it fails halfway through an install.

Keeping deploy scripts pure ASCII sidesteps codepage issues entirely.
"""
from __future__ import annotations

import os
import re

import pytest

DEPLOY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "windows",
)

EXPECTED_SCRIPTS = (
    "install.ps1", "update.ps1", "rollback.ps1",
    "backup.ps1", "restore.ps1", "set-service-env.ps1",
    # Q28 lich backup + bootstrap: truoc day khong nam trong bo guard ASCII/BOM
    # (audit 2026-07-31 W0/W1). Them vao de regression khong lot luoi.
    "5-lich-backup.ps1", "bootstrap-server2016.ps1",
)


def _scripts() -> list:
    return [f for f in sorted(os.listdir(DEPLOY_DIR)) if f.endswith(".ps1")]


def _read(name: str) -> str:
    with open(os.path.join(DEPLOY_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_restore_actually_restores_the_database():
    """W0.4/P0-4: backup dung pg_dump (-Fc) nen restore PHAI pg_restore file
    .dump; neu chi Expand-Archive thi 'khoi phuc' mat toan bo CSDL (user/credit/
    job). Chot bang cach doi restore.ps1 co pg_restore + doc LTT_DATABASE_URL."""
    text = _read("restore.ps1")
    assert "pg_restore" in text, "restore.ps1 khong pg_restore -> backup khong cuu duoc DB"
    assert "LTT_DATABASE_URL" in text


def test_update_runs_migrations_before_start():
    """W0.6/P0-6: ban phat hanh doi schema ma update.ps1 khong 'alembic upgrade
    head' -> service boot tren schema cu, loi runtime/hong du lieu."""
    text = _read("update.ps1")
    assert "alembic upgrade head" in text
    # Migration phai chay TRUOC khi Start-Service.
    assert text.index("alembic upgrade head") < text.index("Start-Service $ServiceName")


def test_rollback_controls_all_runtime_services_and_supports_safe_rehearsal():
    """Rollback phai dung MOI dich vu runtime truoc khi xoay thu muc `app\\`.

    🔴 PHEP KIEM NAY TRUOC DAY CHOT MOT CHUOI LITERAL:

           assert "@($CodexServiceName, $WorkerServiceName, $ServiceName)" in text

       No do khi them dich vu thu tu (`LTTStudioVoice`, Q117) — dung, nhung do
       vi **sai ly do**: no do vi chuoi doi, khong phai vi tinh chat bi vi pham.
       Mot chuoi literal cung se XANH neu ai do them mot bien dich vu moi vao
       `param()` roi quen dua no vao vong dung — tuc no bo lot dung ca loi that.

    ⭐ Ban nay chot TINH CHAT: **moi bien `*ServiceName` khai o `param()` deu
       phai xuat hien trong vong dung**. Them dich vu thu nam ma quen dung no
       thi test do; doi thu tu hay xuong dong thi khong.

    ⛔ Va chot them mot thu tu: dich vu giong noi phai dung TRUOC nhung dich vu
       khac. `LTTStudioVoice` co `AppDirectory` tro vao `app\\` nen no giu handle
       tren thu muc do; khong dung no truoc thi `Move-Item` nem loi giua chung.
    """
    text = _read("rollback.ps1")

    assert "SkipServiceControl" in text
    assert "$resp.status -ne 'ready'" in text

    khai = set(re.findall(r"\[string\]\$(\w*ServiceName)\s*=", text))
    assert khai, "rollback.ps1 khong khai bien dich vu nao"

    m = re.search(r"foreach\s*\(\$name\s+in\s+@\(([^)]*)\)", text, re.S)
    assert m, "khong tim thay vong dung dich vu trong rollback.ps1"
    trong_vong = set(re.findall(r"\$(\w*ServiceName)", m.group(1)))

    thieu = khai - trong_vong
    assert not thieu, (
        f"rollback.ps1 khai {sorted(thieu)} nhung khong dung chung truoc khi "
        f"xoay app\\ — chung se giu handle tren thu muc do")

    if "VoiceServiceName" in trong_vong:
        thu_tu = re.findall(r"\$(\w*ServiceName)", m.group(1))
        assert thu_tu[0] == "VoiceServiceName", (
            "LTTStudioVoice phai duoc dung DAU TIEN: no giu handle tren app\\")


def test_service_env_loader_allows_empty_optional_integration_placeholders():
    text = _read("set-service-env.ps1")
    assert "skip empty" in text
    assert "These variables are still empty" not in text
    assert "tools\\nssm.exe" in text


def test_backup_never_puts_secrets_in_the_database_archive():
    """H35.9: app.env va pg_dump khong duoc nam chung mot zip.

    Do that ngay 2026-08-17 tren may chu: ltt_data_20260817_023001.zip chua ca
    `app.env` lan `lttplatform.dump`. Nghia la MOT ban zip bi lay cap la du de
    doc token da ma hoa (co LTT_TOKEN_ENCRYPTION_KEY) va - sau khi Public API
    len - tan cong khoa API cua khach ngoai tuyen (co LTT_API_KEY_PEPPER).

    Chot bang cau truc chu khong bang cau chu: ban secrets phai la mot archive
    RIENG, va app.env khong duoc copy vao thu muc staging cua ban du lieu.
    """
    text = _read("backup.ps1")

    assert "ltt_secrets_$Stamp.zip" in text, "phai co archive secrets rieng"
    assert "SecretsDir" in text, "phai cho phep chon noi cat ban secrets"

    # app.env chi duoc copy vao staging RIENG cua secrets, khong vao $staging.
    for line in text.splitlines():
        if "Copy-Item" not in line or "app.env" not in line:
            continue
        assert "$secretStaging" in line, (
            f"app.env bi copy vao staging cua ban du lieu: {line.strip()}"
        )


def test_backup_secrets_dir_defaults_to_a_sibling_not_a_child():
    """Thu muc CON se bi dong bo off-site keo theo cung ban du lieu, tuc la tach
    xong lai gop lai o buoc sau. Mac dinh phai la thu muc ANH EM."""
    text = _read("backup.ps1")
    assert "-secrets\"" in text or "-secrets'" in text
    assert "Join-Path $backups 'secrets'" not in text


def test_scheduled_backup_passes_a_separate_secrets_dir():
    text = _read("5-lich-backup.ps1")
    assert "-SecretsDir" in text, "lich chay phai truyen -SecretsDir cho backup.ps1"
    # ACL phai siet CA HAI thu muc - ban secrets khong duoc long hon ban du lieu.
    assert "@($BackupDir, $SecretsDir)" in text


def test_restore_refuses_to_overwrite_live_secrets():
    """Ban secrets do vao data\\ la sai cho, va ghi de app.env cua dich vu dang
    chay co the lam nen tang khong khoi dong lai duoc."""
    text = _read("restore.ps1")
    assert "ltt_secrets_*" in text
    assert "$isSecretArchive -and $Live" in text


def test_scheduled_backup_tightens_acl():
    """W1.5: ban backup off-drive CHUA secrets (app.env + dump) -> thu muc phai
    bi siet ACL (icacls SID) de Users/Everyone khong doc duoc."""
    text = _read("5-lich-backup.ps1")
    assert "icacls" in text
    assert "/inheritance:r" in text
    assert "S-1-5-18" in text and "S-1-5-32-544" in text   # SID, locale-safe


def test_all_expected_scripts_exist():
    present = set(_scripts())
    missing = [s for s in EXPECTED_SCRIPTS if s not in present]
    assert missing == [], f"missing deployment scripts: {missing}"


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_are_pure_ascii(name):
    """Non-ASCII in a .ps1 breaks Windows PowerShell 5.1 parsing when the
    file has no BOM."""
    path = os.path.join(DEPLOY_DIR, name)
    with open(path, "rb") as f:
        raw = f.read()

    non_ascii = [(i, b) for i, b in enumerate(raw) if b > 127]
    assert non_ascii == [], (
        f"{name} contains non-ASCII bytes at offsets "
        f"{[i for i, _ in non_ascii[:5]]} — PowerShell 5.1 will misparse it"
    )


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_have_no_bom(name):
    """A BOM would also work, but mixing conventions invites confusion —
    ASCII-only is the rule here."""
    with open(os.path.join(DEPLOY_DIR, name), "rb") as f:
        assert not f.read(3).startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_set_error_action_stop(name):
    """Without this, a failed step keeps going and can leave a half-
    installed server that looks successful."""
    with open(os.path.join(DEPLOY_DIR, name), encoding="ascii") as f:
        assert "$ErrorActionPreference = 'Stop'" in f.read()


def test_caddyfile_example_exists_and_binds_loopback():
    path = os.path.join(DEPLOY_DIR, "Caddyfile.example")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "app.lttstudios.com" in content
    # The app must never be proxied from a public bind address.
    #
    # Asserted on the loopback prefix, not on a specific port number: the port
    # is a deployment detail that legitimately changes (it moved 8000 -> 8100
    # when this host turned out to already run another service on 8000), while
    # "never proxy a publicly-bound address" is the actual invariant. Pinning
    # the number made a routine port change look like a security regression.
    assert "reverse_proxy 127.0.0.1:" in content
    for public_bind in ("reverse_proxy 0.0.0.0:", "reverse_proxy :"):
        assert public_bind not in content, public_bind


def test_no_secret_values_in_deploy_scripts():
    """Scripts may reference secret NAMES, never values."""
    for name in _scripts() + ["Caddyfile.example"]:
        path = os.path.join(DEPLOY_DIR, name)
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        for var in ("LTT_SESSION_SECRET", "LTT_ADMIN_PASSWORD_HASH",
                    "LTT_TOKEN_ENCRYPTION_KEY"):
            for line in content.splitlines():
                if var not in line or "=" not in line:
                    continue
                tail = line.split(var, 1)[1].lstrip()
                if not tail.startswith("="):
                    continue
                # Strip PowerShell array/string punctuation so only the
                # assigned value remains:  'LTT_X=',  ->  ''
                assigned = tail[1:].strip().strip("'\"").rstrip(",").strip("'\"")
                assert assigned == "", (
                    f"{name}: {var} must ship empty, got {assigned!r}"
                )


# ─── Server 2016 bootstrap ─────────────────────────────────────────────────────

def test_server2016_bootstrap_exists_and_is_ascii():
    path = os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1")
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert [b for b in f.read() if b > 127] == []


def test_server2016_bootstrap_handles_the_2016_specific_gaps():
    """Server 2016 has no OpenSSH Feature-on-Demand and defaults to TLS 1.0
    for web requests. Both break a naive install."""
    with open(os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1"), encoding="ascii") as f:
        src = f.read()

    assert "Tls12" in src, "Server 2016 defaults to TLS 1.0; downloads fail without this"
    assert "Win32-OpenSSH" in src, "OpenSSH must come from GitHub on Server 2016"
    assert "install-sshd.ps1" in src
    assert "administrators_authorized_keys" in src, (
        "admin accounts use this file, not ~/.ssh/authorized_keys"
    )
    assert "icacls" in src, "OpenSSH ignores the key file if permissions are too open"
    assert "DefaultShell" in src, "without this an SSH session lands in cmd.exe"


def test_server2016_bootstrap_pins_python_312_not_313():
    """Server 2016 runs the Windows 10 1607 kernel; 3.12 is the last line
    well-tested there, and the app only needs 3.10+."""
    with open(os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1"), encoding="ascii") as f:
        src = f.read()
    assert "3.12" in src
    assert "$PythonVersion = '3.13" not in src


def test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu():
    """🔴 Không đặt một việc DÀI và CÓ THỂ HỎNG vào giữa lúc dịch vụ đang tắt.

    SỰ CỐ THẬT 2026-08-30 22:18. `2-cai-dat.ps1` dừng ba dịch vụ để xoay `app\`,
    rồi chạy lệnh cài `vieneu-venv` — **một lần tải về ~6 GB** — ngay giữa cửa sổ
    đó, rồi mới bật lại. Tiến trình nâng quyền chết trong lúc tải.

    Kết quả: **production nằm 19 phút**, và `EXITCODE` rỗng nên không ai biết nó
    dừng ở bước nào. Bản thân `deploy_nang_quyen.ps1` đã ghi sẵn rằng
    *"EXITCODE rỗng khác hẳn EXITCODE=0"* — cảnh báo đó đúng, và nó vừa được
    dùng đến.

    ⭐ Lỗi KHÔNG phải ở chỗ tải về chậm. Lỗi ở chỗ **đặt** nó: cài venv không cần
       dịch vụ nào dừng cả. Nó nằm dưới chỉ vì nó "thuộc về" app đó trong đầu
       người viết. **Sự gần gũi về mặt khái niệm không phải lý do để xếp thứ tự
       thi hành.**

    Phép kiểm chốt đúng thứ đó: mọi lệnh gọi `install-*-sidecar.ps1` phải đứng
    TRƯỚC dòng `Stop-Service` đầu tiên.
    """
    #: KHONG CON MIEN TRU NAO. Ban dau tep nay mien tru
    #: `install-whisperx-sidecar.ps1` vi no nam sau `Stop-Service` tu truoc dot
    #: LTT VOICE. Mien tru do da duoc BO cung ngay: khoi WhisperX cung chuyen len
    #: truoc `Head 'Copy ma nguon'`.
    #:
    #: Ghi lai vi day la mot lua chon, khong phai mot su tinh co: mot mien tru
    #: khong het han chinh la cach mot ngoai le song lau hon ly do sinh ra no.
    MIEN_TRU = set()

    # `2-cai-dat.ps1` o `setup/`, khong o `deploy/windows/` nhu cac tep kia.
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(goc, "setup", "2-cai-dat.ps1"),
              "r", encoding="utf-8") as f:
        text = f.read()
    dong = text.splitlines()

    # Bo dong CHU THICH: tep nay noi VE `Stop-Service` o nhieu cho, va dem
    # chung se lam phep kiem do vi mot cau van xuoi. Do that: dong 67 la
    # "VI SAO CHOT NAY O DAY, VA O TRUOC Stop-Service".
    def _la_ma(d):
        return bool(d.strip()) and not d.strip().startswith("#")

    dung = [i for i, d in enumerate(dong) if "Stop-Service" in d and _la_ma(d)]
    assert dung, "2-cai-dat.ps1 khong con Stop-Service — phep kiem nay het nghia"

    cai = [(i, d) for i, d in enumerate(dong)
           if "install-" in d and "-sidecar.ps1" in d and _la_ma(d)
           and not any(m in d for m in MIEN_TRU)]
    assert cai, ("khong tim thay lenh cai sidecar nao ngoai mien tru — neu vua "
                 "them mot mien tru moi thi phai ghi ly do, chu, va han bo")

    sau = [i for i, _ in cai if i > min(dung)]
    assert not sau, (
        f"lenh cai sidecar o dong {[i + 1 for i in sau]} nam SAU Stop-Service "
        f"dau tien (dong {min(dung) + 1}) — moi giay no chay la mot giay "
        f"production nam. Chuyen no len TRUOC `Head 'Copy ma nguon'`, va goi tu "
        f"`$src` chu khong `$appDir` (app\ chi co noi dung moi sau robocopy).")
