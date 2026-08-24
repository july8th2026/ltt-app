"""cam_cli.py - cam Codex / Claude Code vao API cua LTT Studios, va GO RA sach.

    python tools\\cam_cli.py xem
    python tools\\cam_cli.py cam  --khoa ltt_sk_...
    python tools\\cam_cli.py kiem
    python tools\\cam_cli.py go

Hoac bam dup `cam_cli.bat` o cung thu muc.

================================================================================
* VI SAO CONG CU NAY TON TAI

  Bai hoc tu `api.nghimmo.com` (xem docs/VLM_NOI_BO/LO_TRINH_API_CLI.md muc 1):
  thu chan mot lap trinh vien KHONG phai giao thuc, ma la DIEN DUNG MOT FILE
  CAU HINH. Hai base URL lech nhau bon ky tu, mot ten model phai khop chinh xac,
  mot bien moi truong phai dat o cap NGUOI DUNG chu khong phai trong mot cua so
  terminal. Moi thu do hong lang le voi mot trieu chung vo ich.

* VI SAO KHONG DONG GOI THANH .EXE

  Mot .exe nho, khong ky so, ghi vao thu muc cau hinh cua nguoi dung - do DUNG
  la mo ta hanh vi cua malware. SmartScreen chan, diet virus bao dong gia, va
  phai nuoi ba ban dung. Ma phan loi chi la vai chuc dong ghi tep.

  Mot tep .py doc duoc thi KHACH DOC DUOC TRUOC KHI CHAY - dieu do quan trong
  vi no dang ghi vao cau hinh cua ho.

================================================================================
!! BON CHOT, VA MOI CHOT DEU TRA GIA MOT LAN O DAU DO

1. HOP NHAT, KHONG GHI DE. `~/.codex/config.toml` la CUA KHACH. Ghi de la xoa
   thiet lap ho dang dung - va hong theo kieu te nhat: NO VAN CHAY, chi la do
   nghe rieng cua ho bien mat.

   Cach lam: chen mot khoi co DAU MOC hai dau. Phan ngoai khoi giu nguyen tung
   byte, ke ca chu thich va thu tu - thu ma "doc ra roi ghi lai" luon lam mat.

2. GO RA PHAI TRA VE DUNG NGUYEN TRANG. Khong phai "xoa nhung gi trong giong
   cua ta" - ma la xoa DUNG NHUNG GI TA DA THEM. Neu khach DA CO san mot muc
   `[model_providers.ltt]` truoc khi chay cong cu nay, `go` KHONG duoc dung toi.
   Vi vay co tep trang thai ghi lai "cai nay ta tao" so voi "cai nay von da co".

3. KHOA CHI VAO BIEN MOI TRUONG, KHONG VAO TEP NAO. Luat da co trong ma nguon:
   *"No snippet ever contains a key."* `settings.json` la tep van ban thuong ma
   nhieu nguoi dong bo hoac commit vao kho dotfiles.

4. TU KIEM BANG MOT LUOT GOI THAT. Mot cong cu ghi xong tep roi bao "da cau
   hinh" co dung diem mu voi mot job bao `succeeded` ma khach khong tai duoc
   anh: no tin vao viec minh vua lam, thay vi kiem thu khach that su nhan duoc.

================================================================================
!! MOT CANH BAO PHAI NOI TO, VI NO KHONG HIEN NHIEN

   `ANTHROPIC_BASE_URL` la TOAN CUC. Dat no la chuyen huong MOI phien Claude
   Code tren may, ke ca goi Anthropic that cua khach. Codex thi khong bi: no co
   `--profile ltt`, nen mac dinh cua khach van nguyen.

   Vi the: mac dinh cong cu nay chi dat BIEN MOI TRUONG (go ra de). Chi khi
   khach noi ro `--toan-cuc` no moi ghi `~/.claude/settings.json`.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

GOC_MAC_DINH = "https://app.lttstudios.com"
MODEL = "ltt_llm"
ENV_KHOA_CODEX = "LTT_API_KEY"
ENV_KHOA_CLAUDE = "ANTHROPIC_AUTH_TOKEN"

#: Dau moc hai dau. Moi thu giua chung la cua ta; moi thu ngoai chung la cua
#: khach va KHONG duoc dung toi.
MOC_MO = "# >>> LTT Studios - them boi cam_cli.py. Dung sua tay trong khoi nay. >>>"
MOC_DONG = "# <<< LTT Studios <<<"

NHA = pathlib.Path.home()
TEP_TRANG_THAI = NHA / ".ltt" / "cam_cli_trang_thai.json"


# ── Tien ich ────────────────────────────────────────────────────────────────

def _doc_trang_thai() -> dict:
    if not TEP_TRANG_THAI.exists():
        return {}
    try:
        return json.loads(TEP_TRANG_THAI.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Tep trang thai hong thi coi nhu chua cam. `go` se van don duoc bang
        # dau moc; chi mat thong tin "tep nay ta tao hay von co".
        return {}


def _ghi_trang_thai(tt: dict) -> None:
    TEP_TRANG_THAI.parent.mkdir(parents=True, exist_ok=True)
    TEP_TRANG_THAI.write_text(json.dumps(tt, ensure_ascii=False, indent=1),
                              encoding="utf-8", newline="\n")


def _sao_luu(tep: pathlib.Path) -> pathlib.Path | None:
    """Sao luu mot lan, giu ban DAU TIEN.

    !! KHONG ghi de ban sao luu o lan chay thu hai. Ban dau tien la ban truoc
       khi ta dung vao - do moi la thu can de quay ve. Ghi de no bang mot ban
       "da co cau hinh cua ta" la lam mat dung thu ta dinh bao ve.
    """
    if not tep.exists():
        return None
    bs = tep.with_suffix(tep.suffix + ".truoc-ltt")
    if not bs.exists():
        bs.write_bytes(tep.read_bytes())
    return bs


def _doc_giu_dong(tep: pathlib.Path) -> tuple:
    """Đọc tệp **thô**, trả về `(văn_bản_nguyên_xi, kiểu_xuống_dòng_để_ta_dùng)`.

    🔴 HAI LỖI LIÊN TIẾP Ở ĐÂY, VÀ CẢ HAI ĐỀU CHỈ VM THẬT TÌM RA (P4/T8, 24/08).

    **① Bản đầu ghi lại bằng `newline="\\n"`.** `Set-Content` của PowerShell —
       thứ mà mọi script cài đặt trên Windows dùng — ghi **CRLF**. Nên ta lặng
       lẽ đổi **cả tệp** từ CRLF sang LF; `go` không trả về bằng từng byte nữa,
       và khách mở `git diff` lên thấy **toàn bộ tệp** thay đổi.

    **② Bản sửa thứ nhất chuẩn hoá theo "tệp có CRLF không".** Sai nốt, vì tệp
       thật **lẫn lộn**: nội dung LF, dòng cuối CRLF (đúng tệp trên VM). Thấy một
       CRLF là ép cả tệp thành CRLF ⇒ 147 byte phình thành **154**.

    ⭐ NÊN CÁCH ĐÚNG LÀ **KHÔNG CHUẨN HOÁ GÌ CẢ.** Đọc thô, mổ đúng khối có dấu
       mốc, ghi thô. Phần ngoài khối không bị đụng tới thì không có gì để hỏng —
       kể cả khi nó lẫn lộn, kể cả khi nó kỳ quặc.

       Kiểu xuống dòng trả về chỉ để dựng **khối của ta**, không để áp lên tệp.

    ⚠️ Test đơn vị không thấy cả hai lỗi, vì chúng ghi fixture bằng
       `newline="\\n"` — tức đo một thế giới chỉ có LF và luôn nhất quán.
    """
    van = tep.read_bytes().decode("utf-8")
    crlf = van.count("\r\n")
    lf = van.count("\n") - crlf
    return van, ("\r\n" if crlf > lf else "\n")


def _ghi_giu_dong(tep: pathlib.Path, van: str, _dong_moi=None) -> None:
    """Ghi **nguyên xi**. Không chuẩn hoá — xem `_doc_giu_dong`."""
    tep.write_bytes(van.encode("utf-8"))


def _json_theo_dong(d: dict, nl: str) -> str:
    """Sinh JSON với **đúng kiểu xuống dòng** của tệp gốc.

    ⭐ Khác `config.toml` ở một điểm quyết định: TOML ta chỉ **mổ một khối** nên
       phần ngoài giữ nguyên từng byte và không cần biết gì về xuống dòng. JSON
       thì ta **sinh lại toàn bộ nội dung**, nên xuống dòng là thứ ta phải tự
       đặt lại cho đúng — nếu không, mọi `settings.json` CRLF sẽ lặng lẽ thành LF.
    """
    van = json.dumps(d, ensure_ascii=False, indent=2) + chr(10)
    return van.replace(chr(10), nl) if nl != chr(10) else van


def _chen_khoi(van: str, noi_dung: str, nl: str = "\n") -> str:
    """Chèn (hoặc thay) khối có dấu mốc. **Phần ngoài khối không bị đụng tới.**

    `nl` là kiểu xuống dòng dùng **bên trong khối của ta** — lấy từ tệp để khối
    trông hoà vào phần còn lại, chứ **không** áp lên phần của khách.
    """
    than = nl.join(noi_dung.replace("\r\n", "\n").rstrip("\n").split("\n"))
    khoi = MOC_MO + nl + than + nl + MOC_DONG
    if MOC_MO in van and MOC_DONG in van:
        dau = van.index(MOC_MO)
        cuoi = van.index(MOC_DONG) + len(MOC_DONG)
        return van[:dau] + khoi + van[cuoi:]
    # Nối vào cuối, cách một dòng trắng. Nếu tệp chưa kết thúc bằng xuống dòng
    # thì thêm một cái — nhưng KHÔNG đụng gì tới phần đã có.
    duoi = "" if (not van or van.endswith(("\n", "\r"))) else nl
    return van + duoi + nl + khoi + nl


def _go_khoi(van: str) -> tuple[str, bool]:
    """Cắt đúng khối của ta, kể cả các dòng trắng ta đã thêm quanh nó.

    ⛔ **Không** `rstrip`/`lstrip` cả tệp. Bản đầu làm vậy và nó cắt luôn dòng
       trắng **của khách** ở cuối tệp — một thay đổi khách không yêu cầu, và
       không có gì báo.
    """
    if MOC_MO not in van or MOC_DONG not in van:
        return van, False
    dau = van.index(MOC_MO)
    cuoi = van.index(MOC_DONG) + len(MOC_DONG)
    truoc, sau = van[:dau], van[cuoi:]
    # Gỡ đúng phần ngăn cách mà `_chen_khoi` đã thêm: một xuống dòng ngay sau
    # khối, và một dòng trắng ngay trước nó.
    for nl in ("\r\n", "\n"):
        if sau.startswith(nl):
            sau = sau[len(nl):]
            break
    for nl in ("\r\n", "\n"):
        if truoc.endswith(nl + nl):
            truoc = truoc[:-len(nl)]
            break
    return truoc + sau, True


def _setx(ten: str, gt: str) -> bool:
    """Dat bien moi truong o cap NGUOI DUNG.

    !! `setx` chi anh huong tien trinh MOI. VS Code / terminal dang mo se KHONG
       thay - phai mo lai. Day la cho hay lam nguoi ta tuong cong cu hong.
    """
    try:
        r = subprocess.run(["setx", ten, gt], capture_output=True, text=True,
                           timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _xoa_env(ten: str) -> bool:
    """Xoa bien moi truong cap nguoi dung. `setx TEN ""` de lai mot bien RONG,
    khong xoa han - nen phai dung `reg delete`."""
    try:
        r = subprocess.run(["reg", "delete", "HKCU\\Environment", "/F", "/V", ten],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _doc_env_nguoi_dung(ten: str) -> str | None:
    try:
        r = subprocess.run(["reg", "query", "HKCU\\Environment", "/V", ten],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        for dong in r.stdout.splitlines():
            if ten.lower() in dong.lower() and "REG_" in dong:
                return dong.split("REG_", 1)[1].split(None, 1)[-1].strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


# ── Codex ───────────────────────────────────────────────────────────────────

def _codex_config(goc: str) -> str:
    return (f'[model_providers.ltt]\n'
            f'name = "LTT Studios"\n'
            f'base_url = "{goc}/api/v1"\n'
            f'env_key = "{ENV_KHOA_CODEX}"\n'
            f'wire_api = "responses"\n'
            f'stream_idle_timeout_ms = 600000\n')


def _codex_profile() -> str:
    return (f'model = "{MODEL}"\n'
            f'model_provider = "ltt"\n'
            f'model_reasoning_effort = "low"\n'
            f'model_reasoning_summary = "none"\n'
            f'model_context_window = 65536\n')


def _codex_config_goc(goc: str) -> str:
    """Dang GOC — dat `model`/`model_provider` ngay trong `config.toml`.

    * VI SAO PHAI CO DANG THU HAI. Tien ich Codex cua VS Code KHONG co cach truyen
      `--profile`, va Codex 0.145 tu choi thang `profile = "ltt"` trong tep:

          Error: legacy `profile = "ltt"` config is no longer supported;
                 use `--profile ltt` with `ltt.config.toml` instead

      Nen muon tien ich dung duoc thi cau hinh phai nam o GOC.

    ! DANH DOI PHAI NOI RO: dang nay thay LUON mac dinh cua lenh `codex`. Dang
      profile giu nguyen mac dinh cua khach nhung chi CLI dung duoc. Khong co
      cach nao duoc ca hai - do la gioi han cua Codex, khong phai cua ta.
    """
    return (f'model = "{MODEL}"\n'
            f'model_provider = "ltt"\n'
            f'model_reasoning_effort = "low"\n'
            f'model_reasoning_summary = "none"\n'
            f'model_context_window = 65536\n'
            f'\n' + _codex_config(goc))


def cam_codex(goc: str, tt: dict, cho_vscode: bool = False) -> list:
    ra = []
    thu_muc = NHA / ".codex"
    thu_muc.mkdir(parents=True, exist_ok=True)

    cfg = thu_muc / "config.toml"
    _sao_luu(cfg)
    van, crlf = _doc_giu_dong(cfg) if cfg.exists() else ("", "\n")
    tt.setdefault("codex", {})["che_do"] = "vscode" if cho_vscode else "profile"
    noi_dung = _codex_config_goc(goc) if cho_vscode else _codex_config(goc)
    _ghi_giu_dong(cfg, _chen_khoi(van, noi_dung, crlf))
    ra.append(f"  [OK] {cfg}  (khoi co dau moc, phan con lai giu nguyen)")

    prof = thu_muc / "ltt.config.toml"
    ghi = tt.setdefault("codex", {})
    # 🔴 GIU LAN XAC DINH DAU TIEN, dung tinh lai moi lan chay.
    #
    #    Ban dau dong nay la `ghi["ta_tao_ltt_config"] = not prof.exists()`, tinh
    #    lai o MOI lan `cam`. Lan hai, tep DA TON TAI (do chinh ta tao lan mot),
    #    nen no ghi False - va `go` khong xoa nua. Chay `cam` hai lan roi `go` la
    #    de lai rac vinh vien, khong bao gi.
    #
    #    Cung luat voi `_sao_luu`: **ban dau tien moi la su that**.
    if "ta_tao_ltt_config" not in ghi:
        ghi["ta_tao_ltt_config"] = not prof.exists()
    # ⛔ Va neu tep DA CO TU TRUOC thi phai sao luu, vi ta sap ghi de len no.
    #    Truoc day ta ghi de thang mot tep cua khach ma khong luu gi ca - `go`
    #    chi "khong xoa" chu khong tra lai duoc noi dung.
    _sao_luu(prof)
    prof.write_text(_codex_profile(), encoding="utf-8", newline="\n")
    ra.append(f"  [OK] {prof}")
    return ra


def go_codex(tt: dict) -> list:
    ra = []
    cfg = NHA / ".codex" / "config.toml"
    if cfg.exists():
        # Kiểu xuống dòng lấy từ **chính tệp đang có**, không lấy từ tệp trạng
        # thái: tệp trạng thái có thể mất, còn tệp thì luôn ở đó.
        van_goc, crlf = _doc_giu_dong(cfg)
        van, thay = _go_khoi(van_goc)
        if thay:
            _ghi_giu_dong(cfg, van, crlf)
            ra.append(f"  [OK] da go khoi cua ta khoi {cfg}")
        else:
            ra.append(f"  [--] {cfg} khong co khoi cua ta")

    prof = NHA / ".codex" / "ltt.config.toml"
    if prof.exists():
        if tt.get("codex", {}).get("ta_tao_ltt_config"):
            prof.unlink()
            ra.append(f"  [OK] da xoa {prof} (ta tao no)")
        else:
            # Tep co TU TRUOC va ta da ghi de len no ⇒ tra lai tu ban sao luu.
            # "Khong xoa" chua phai la tra ve nguyen trang.
            bs = prof.with_suffix(prof.suffix + ".truoc-ltt")
            if bs.exists():
                prof.write_bytes(bs.read_bytes())
                ra.append(f"  [OK] da tra {prof} ve ban truoc khi cam")
            else:
                ra.append(f"  [!!] GIU {prof} - co tu truoc, khong co ban sao luu")
    return ra


# ── Claude Desktop: chính sách registry, không phải tệp cấu hình ───────────

#: Khoá chính sách cấp NGƯỜI DÙNG. Bản `HKLM` cần quyền quản trị và **đè** bản
#: này — nếu máy đã có `HKLM\SOFTWARE\Policies\Claude` thì ứng dụng **bỏ qua
#: hoàn toàn** `HKCU`, nên `xem` phải kiểm cả hai.
REG_DESKTOP_HKCU = r"HKCU\SOFTWARE\Policies\Claude"
REG_DESKTOP_HKLM = r"HKLM\SOFTWARE\Policies\Claude"

#: Đúng tên khoá theo tài liệu chính thức của Anthropic. Mọi giá trị là `REG_SZ`,
#: kể cả số và mảng — mảng phải là **chuỗi JSON**.
_DESKTOP_KHOA = ("inferenceProvider", "inferenceGatewayBaseUrl",
                 "inferenceGatewayApiKey", "inferenceGatewayAuthScheme",
                 "inferenceModels", "modelDiscoveryEnabled")


def _reg_ghi(khoa: str, ten: str, gt: str) -> bool:
    try:
        r = subprocess.run(["reg", "add", khoa, "/v", ten, "/t", "REG_SZ",
                            "/d", gt, "/f"],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _reg_xoa(khoa: str, ten: str) -> bool:
    try:
        r = subprocess.run(["reg", "delete", khoa, "/v", ten, "/f"],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _reg_doc(khoa: str, ten: str) -> str | None:
    try:
        r = subprocess.run(["reg", "query", khoa, "/v", ten],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        for dong in r.stdout.splitlines():
            if ten.lower() in dong.lower() and "REG_SZ" in dong:
                return dong.split("REG_SZ", 1)[1].strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def cam_desktop(goc: str, khoa: str, tt: dict) -> list:
    r"""Cấu hình **Claude Desktop** qua chính sách registry.

    * VÌ SAO KHÔNG PHẢI MỘT TỆP CẤU HÌNH. Claude Desktop cất thiết lập chạy
      trong LevelDB của Electron — sửa tay là hỏng lặng lẽ ở lần cập nhật sau.
      Nhưng phần **suy luận bên thứ ba** thì đọc từ **chính sách hệ điều hành**:
      `.mobileconfig` trên macOS, **registry** trên Windows. Đó là đường dành cho
      triển khai doanh nghiệp, và nó ổn định.

    ⭐ NÊN Ô "Gateway API key" TRONG ỨNG DỤNG **KHÔNG PHẢI** LÀ ĐƯỜNG DUY NHẤT.
      Trước khi tìm ra điều này, phần Claude Desktop bị coi là "chỉ cấu hình tay".

    ⚠️ HAI CHỐT CỦA TÀI LIỆU CHÍNH THỨC, ĐỪNG ĐOÁN LẠI:
      · `inferenceGatewayBaseUrl` **bắt buộc HTTPS** (trừ loopback);
      · cấu hình chỉ đọc **một lần lúc khởi động** ⇒ phải **thoát hẳn** ứng dụng
        rồi mở lại, không phải chỉ đóng cửa sổ.

    ⛔ VÀ MỘT CẢNH BÁO VỀ THỨ TỰ: nếu máy đã có chính sách ở `HKLM` (do quản trị
      viên đặt) thì ứng dụng **bỏ qua hoàn toàn** `HKCU` — cắm bằng công cụ này
      sẽ **không có tác dụng gì** và cũng không báo lỗi. `xem` kiểm cả hai.
    """
    ra = []
    if _reg_doc(REG_DESKTOP_HKLM, "inferenceProvider"):
        ra.append("  [!!] May DA CO chinh sach o HKLM - ung dung se BO QUA HKCU.")
        ra.append("       Phai nho quan tri vien sua o do; cam o day vo tac dung.")
        return ra

    gia_tri = {
        "inferenceProvider": "gateway",
        # Chi goc, KHONG kem `/v1` - ung dung tu ghep `/v1/messages`.
        "inferenceGatewayBaseUrl": goc + "/api",
        "inferenceGatewayApiKey": khoa,
        "inferenceGatewayAuthScheme": "bearer",
        "inferenceModels": '[{"name": "' + MODEL + '"}]',
        # Tat tu do model: danh sach cua ta chi co mot ten, va mot lan do sai se
        # lam ung dung hien nhung model no khong goi duoc.
        "modelDiscoveryEnabled": "false",
    }
    ghi_nho = tt.setdefault("desktop", {}).setdefault("khoa_da_them", {})
    for ten, gt in gia_tri.items():
        if ten not in ghi_nho:
            ghi_nho[ten] = _reg_doc(REG_DESKTOP_HKCU, ten)   # None = von khong co
        ok = _reg_ghi(REG_DESKTOP_HKCU, ten, gt)
        if ten == "inferenceGatewayApiKey":
            ra.append(f"  [{'OK' if ok else '!!'}] {ten} (da dat, khong in ra)")
        else:
            ra.append(f"  [{'OK' if ok else '!!'}] {ten} = {gt}")
    ra.append("  [!!] Phai THOAT HAN Claude Desktop roi mo lai - cau hinh chi")
    ra.append("       duoc doc MOT LAN luc khoi dong.")
    return ra


def go_desktop(tt: dict) -> list:
    ra = []
    ghi_nho = tt.get("desktop", {}).get("khoa_da_them") or {}
    if not ghi_nho:
        return ra
    for ten, cu in ghi_nho.items():
        if cu is None:
            ra.append(f"  [{'OK' if _reg_xoa(REG_DESKTOP_HKCU, ten) else '--'}] bo {ten}")
        else:
            ra.append(f"  [{'OK' if _reg_ghi(REG_DESKTOP_HKCU, ten, cu) else '!!'}] "
                      f"tra {ten} ve gia tri cu")
    return ra


# ── VS Code: hai tiện ích KHÔNG dùng biến môi trường như CLI ───────────────

def _vscode_settings() -> pathlib.Path:
    r"""`%APPDATA%\Code\User\settings.json` — thiết lập cấp NGƯỜI DÙNG.

    ⛔ Phải là tệp này, **không** phải `.vscode/settings.json` của một dự án:
       `claudeCode.environmentVariables` khai `scope: "machine"`, nên VS Code
       **bỏ qua** nó nếu đặt ở cấp workspace. Đặt nhầm chỗ thì không có lỗi nào —
       thiết lập chỉ đơn giản là không có tác dụng.
    """
    goc = os.environ.get("APPDATA")
    return (pathlib.Path(goc) if goc else NHA / "AppData" / "Roaming") \
        / "Code" / "User" / "settings.json"


def cam_vscode(goc: str, tt: dict) -> list:
    """Cấu hình **tiện ích VS Code** — khác hẳn cấu hình cho CLI.

    🔴 VÌ SAO PHẢI CÓ RIÊNG. Đo thật trên VM 24/08: cắm xong cho CLI rồi mở VS
       Code lên, tiện ích Claude Code **vẫn hiện nút "Sign In"**. Nó KHÔNG dùng
       `ANTHROPIC_BASE_URL` của hệ điều hành như CLI — đây là lỗi đã biết của
       tiện ích từ v2.0.0 (`anthropics/claude-code` #9010 và #38430).

       Tiện ích có hai thiết lập riêng để bù, đọc thẳng từ `package.json` của bản
       đã cài chứ không đoán:
         · `claudeCode.environmentVariables` — mảng {name, value} truyền cho
           tiến trình `claude` con;
         · `claudeCode.disableLoginPrompt` — *"never prompt for login...
           authentication is handled externally"*.

    ⛔ VÀ MỘT LUẬT KHÔNG NỚI: **khoá vẫn không vào tệp.** Ở đây chỉ đặt hai giá
       trị KHÔNG bí mật; `ANTHROPIC_AUTH_TOKEN` ở lại biến môi trường, nơi tiến
       trình con vẫn kế thừa được. `settings.json` là tệp rất nhiều người đồng bộ
       giữa máy hoặc commit vào kho dotfiles.
    """
    ra = []
    tep = _vscode_settings()
    if not tep.parent.exists():
        ra.append("  [--] khong thay VS Code (bo qua)")
        return ra
    _sao_luu(tep)
    nl = chr(10)
    try:
        if tep.exists():
            van, nl = _doc_giu_dong(tep)
            d = json.loads(van) if van.strip() else {}
        else:
            d = {}
    except ValueError:
        ra.append("  [!!] " + str(tep) + " khong phai JSON hop le - KHONG dung toi")
        return ra

    ghi_nho = tt.setdefault("vscode", {}).setdefault("khoa_da_them", {})
    moi = {
        "claudeCode.environmentVariables": [
            {"name": "ANTHROPIC_BASE_URL", "value": goc + "/api"},
            {"name": "ANTHROPIC_MODEL", "value": MODEL},
            {"name": "ANTHROPIC_DEFAULT_HAIKU_MODEL", "value": MODEL},
        ],
        "claudeCode.disableLoginPrompt": True,
        # * `useTerminal` la duong DA CHUNG MINH CHAY DUOC (T6 tren VM: claude.exe
        #   cua chinh tien ich nay tra loi dung qua API cua ta). Bang chat cua
        #   tien ich di mot duong xac thuc khac va van doi dang nhap; con terminal
        #   thi chay dung `claude` CLI, thu doc bien moi truong nhu binh thuong.
        #   Chinh tien ich cung goi y dieu nay: "Prefer the terminal experience?"
        "claudeCode.useTerminal": True,
    }
    for ten, gt in moi.items():
        if ten not in ghi_nho:
            ghi_nho[ten] = d.get(ten)          # None = von KHONG co
        d[ten] = gt
    _ghi_giu_dong(tep, _json_theo_dong(d, nl))
    ra.append("  [OK] " + str(tep))
    ra.append("  [!!] Khoa KHONG ghi vao day - no o bien moi truong.")
    return ra


def go_vscode(tt: dict) -> list:
    ra = []
    tep = _vscode_settings()
    ghi_nho = tt.get("vscode", {}).get("khoa_da_them") or {}
    if not tep.exists() or not ghi_nho:
        return ra
    try:
        van, nl = _doc_giu_dong(tep)
        d = json.loads(van)
    except ValueError:
        ra.append("  [!!] " + str(tep) + " khong doc duoc - khong dung toi")
        return ra
    for ten, cu in ghi_nho.items():
        if cu is None:
            d.pop(ten, None)
        else:
            d[ten] = cu
    _ghi_giu_dong(tep, _json_theo_dong(d, nl))
    ra.append("  [OK] da tra " + str(tep) + " ve nhu truoc")
    return ra


# ── Claude Code ─────────────────────────────────────────────────────────────

CLAUDE_ENV = ("ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
              "ANTHROPIC_DEFAULT_HAIKU_MODEL")


def cam_claude(goc: str, tt: dict, toan_cuc: bool) -> list:
    ra = []
    gia_tri = {"ANTHROPIC_BASE_URL": f"{goc}/api",
               "ANTHROPIC_MODEL": MODEL,
               "ANTHROPIC_DEFAULT_HAIKU_MODEL": MODEL}
    for ten, gt in gia_tri.items():
        ra.append(f"  [{'OK' if _setx(ten, gt) else '!!'}] bien moi truong {ten}")

    if not toan_cuc:
        ra.append("  [--] KHONG ghi settings.json (mac dinh). Dung --toan-cuc neu muon.")
        return ra

    tep = NHA / ".claude" / "settings.json"
    tep.parent.mkdir(parents=True, exist_ok=True)
    _sao_luu(tep)
    crlf = chr(10)          # tep chua co -> mac dinh LF
    try:
        if tep.exists():
            van_s, crlf = _doc_giu_dong(tep)
            d = json.loads(van_s)
        else:
            d = {}
    except ValueError:
        print(f"  [!!] {tep} khong phai JSON hop le - KHONG dung toi.")
        return ra
    env = d.setdefault("env", {})
    # Ghi nho DUNG NHUNG KHOA TA THEM, va gia tri cu neu khoa da ton tai.
    ghi_nho = tt.setdefault("claude", {}).setdefault("khoa_da_them", {})
    for ten, gt in gia_tri.items():
        if ten not in ghi_nho:
            ghi_nho[ten] = env.get(ten)      # None = khoa nay von KHONG co
        env[ten] = gt
    _ghi_giu_dong(tep, _json_theo_dong(d, crlf))
    ra.append(f"  [OK] {tep}")
    ra.append("  [!!] settings.json la TOAN CUC: moi phien Claude Code tren may")
    ra.append("       nay se di qua LTT Studios cho toi khi ban chay `go`.")
    return ra


def go_claude(tt: dict) -> list:
    ra = []
    # 🔴 `ENV_KHOA_CODEX` PHẢI CÓ TRONG DANH SÁCH NÀY.
    #
    #    Ban đầu nó bị bỏ sót vì nó "thuộc về Codex" còn hàm này tên là
    #    `go_claude`. Hậu quả: `go` để lại một **khoá API còn sống** trong
    #    môi trường của khách, trong khi vẫn in ra "da go" và mọi dòng đều
    #    `[OK]`. Không có triệu chứng nào cả.
    #
    # ⚠️ Không test đơn vị nào thấy, vì chúng đều vá `_xoa_env` thành một hàm
    #    giả trả `True` — tức chúng đo *ta có gọi hàm không*, chứ không đo
    #    *biến có biến mất không*. Phép thử T8 trên VM thật bắt được ngay.
    for ten in CLAUDE_ENV + (ENV_KHOA_CLAUDE, ENV_KHOA_CODEX):
        ra.append(f"  [{'OK' if _xoa_env(ten) else '--'}] bo bien moi truong {ten}")

    tep = NHA / ".claude" / "settings.json"
    ghi_nho = tt.get("claude", {}).get("khoa_da_them") or {}
    if not tep.exists() or not ghi_nho:
        return ra
    try:
        van_s, crlf_g = _doc_giu_dong(tep)
        d = json.loads(van_s)
    except ValueError:
        ra.append(f"  [!!] {tep} khong doc duoc - khong dung toi")
        return ra
    env = d.get("env") or {}
    for ten, cu in ghi_nho.items():
        if cu is None:
            env.pop(ten, None)               # von khong co -> xoa han
        else:
            env[ten] = cu                    # von co -> tra ve gia tri cu
    if not env:
        d.pop("env", None)
    _ghi_giu_dong(tep, _json_theo_dong(d, crlf_g))
    ra.append(f"  [OK] da tra {tep} ve nhu truoc")
    return ra


# ── Lenh ────────────────────────────────────────────────────────────────────

def _cach_goi(lenh: str) -> str:
    r"""Câu lệnh **đúng với cách khách đang chạy công cụ**.

    Khách cài `.exe` không có `tools\cam_cli.py`; khách chạy mã nguồn thì không
    có `.exe` trong PATH. In sai câu lệnh là gửi họ đi tìm một thứ không tồn tại.
    """
    if getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None)             or "__compiled__" in globals():
        return f"{pathlib.Path(sys.executable).name} {lenh}"
    return rf"python tools\cam_cli.py {lenh}"


def lenh_cam(a) -> int:
    khoa = (a.khoa or os.environ.get(ENV_KHOA_CODEX) or "").strip()
    if not khoa:
        print("Thieu khoa. Dung --khoa ltt_sk_... hoac dat san "
              f"{ENV_KHOA_CODEX} trong moi truong.")
        print("Lay khoa o https://app.lttstudios.com/developers/keys")
        return 1
    if not khoa.startswith("ltt_sk_"):
        print("Khoa phai bat dau bang `ltt_sk_`. Ban dan nham chuoi khac?")
        return 1

    tt = _doc_trang_thai()
    tt["goc"] = a.goc
    print(f"Cam vao {a.goc}\n")
    print("Codex:")
    for d in cam_codex(a.goc, tt, getattr(a, 'vscode', False)):
        print(d)
    print("\nClaude Code:")
    for d in cam_claude(a.goc, tt, a.toan_cuc):
        print(d)

    print("")
    print("Tien ich VS Code:")
    for d in cam_vscode(a.goc, tt):
        print(d)

    print("")
    print("Claude Desktop:")
    for d in cam_desktop(a.goc, khoa, tt):
        print(d)

    print("\nKhoa:")
    for ten in (ENV_KHOA_CODEX, ENV_KHOA_CLAUDE):
        print(f"  [{'OK' if _setx(ten, khoa) else '!!'}] {ten}")
    # !! KHONG ghi khoa vao tep trang thai. Tep do khong phai cho bi mat.
    tt["da_cam"] = True
    _ghi_trang_thai(tt)

    print("\n" + "=" * 70)
    print("!! PHAI MO LAI VS CODE / TERMINAL. `setx` chi anh huong tien trinh MOI;")
    print("   cua so dang mo van dung gia tri cu, va do la cho hay lam nguoi ta")
    print("   tuong cong cu nay hong.")
    print("")
    print("!! NEU DUNG TIEN ICH VS CODE MA VAN BAO THIEU BIEN: DANG XUAT ROI")
    print("   DANG NHAP LAI Windows. Do la cach DUY NHAT chac chan.")
    print("   Do that 24/08 tren VM: mo lai VS Code KHONG du, va khoi dong lai")
    print("   explorer cung KHONG du - explorer moi ke thua moi truong CU tu")
    print("   tien trinh da sinh ra no. Sau khi dang nhap lai thi ca hai tien ich")
    print("   deu chay (Codex tra loi 144, Claude Code tra loi 63).")
    print(f"\nCodex:       codex --profile ltt")
    print(f"Claude Code: claude   (model {MODEL})")
    # ⚠️ Lời nhắc phải **đúng với cách khách đang chạy**. Bản đóng gói in ra
    #    "python tools\cam_cli.py kiem" là chỉ vào một tệp khách KHÔNG CÓ — họ
    #    cài `.exe`, không có mã nguồn. Một hướng dẫn sai thì tệ hơn không có,
    #    vì khách sẽ đi tìm thứ không tồn tại rồi tưởng mình cài hỏng.
    #    Phát hiện 24/08 khi chạy bản đã cài trên VM (P4/T5).
    print("")
    for nhan, lenh in (("Kiem lai", "kiem"), ("Go ra", "go")):
        print(f"{nhan + ':':13}{_cach_goi(lenh)}")
    return 0


def lenh_go(a) -> int:
    tt = _doc_trang_thai()
    if not tt.get("da_cam"):
        print("Tep trang thai khong ghi nhan lan cam nao. Van thu don theo dau moc.\n")
    print("Codex:")
    for d in go_codex(tt):
        print(d)
    print("\nClaude Code:")
    for d in go_claude(tt):
        print(d)

    print("")
    print("Tien ich VS Code:")
    for d in go_vscode(tt):
        print(d)

    print("")
    print("Claude Desktop:")
    for d in go_desktop(tt):
        print(d)
    tt["da_cam"] = False
    tt.pop("claude", None)
    tt.pop("codex", None)
    tt.pop("vscode", None)
    tt.pop("desktop", None)
    _ghi_trang_thai(tt)
    print("\nBan sao luu dau tien van con o cac tep `*.truoc-ltt` - khong tu xoa,")
    print("de ban doi chieu neu can. Xoa tay khi da yen tam.")
    print("\n!! Mo lai VS Code / terminal de bien moi truong cu bien mat.")
    return 0


def lenh_xem(a) -> int:
    tt = _doc_trang_thai()
    print(f"Trang thai: {'DA CAM' if tt.get('da_cam') else 'chua cam'}"
          f"   goc={tt.get('goc') or '-'}\n")

    cfg = NHA / ".codex" / "config.toml"
    co = cfg.exists() and MOC_MO in cfg.read_text(encoding="utf-8")
    print(f"  codex config.toml     : {'co khoi cua ta' if co else 'khong'}")
    print(f"  codex ltt.config.toml : "
          f"{'co' if (NHA / '.codex' / 'ltt.config.toml').exists() else 'khong'}")

    sj = NHA / ".claude" / "settings.json"
    if sj.exists():
        try:
            env = (json.loads(sj.read_text(encoding="utf-8")).get("env") or {})
        except ValueError:
            env = {}
        print(f"  claude settings.json  : ANTHROPIC_BASE_URL="
              f"{env.get('ANTHROPIC_BASE_URL') or '-'}")
    else:
        print("  claude settings.json  : khong co")

    # 🔴 PHAN NAY LA THU HAY HONG NHAT, nen `xem` phai noi ve no.
    #    Truoc day `xem` khong he nhac toi tien ich VS Code - dung phan kho hieu
    #    nhat thi khong bao cao gi.
    sv = _vscode_settings()
    print("")
    print("  Tien ich VS Code:")
    if not sv.exists():
        print("    settings.json         : khong co (chua cai VS Code?)")
    else:
        try:
            dv = json.loads(_doc_giu_dong(sv)[0] or "{}")
        except ValueError:
            dv = {}
        bv = {x.get("name"): x.get("value")
              for x in (dv.get("claudeCode.environmentVariables") or [])}
        print(f"    disableLoginPrompt    : {dv.get('claudeCode.disableLoginPrompt', '-')}")
        print(f"    useTerminal           : {dv.get('claudeCode.useTerminal', '-')}")
        print(f"    BASE_URL cho tien ich : {bv.get('ANTHROPIC_BASE_URL') or '-'}")
    che_do = (tt.get("codex") or {}).get("che_do") or "-"
    print(f"    che do Codex          : {che_do}"
          + ("   (tien ich VS Code CAN che do `vscode`)"
             if che_do == "profile" else ""))

    print("")
    print("  Claude Desktop (chinh sach registry):")
    if _reg_doc(REG_DESKTOP_HKLM, "inferenceProvider"):
        print("    !! CO chinh sach o HKLM - ung dung BO QUA HKCU cua ta")
    print(f"    inferenceProvider     : {_reg_doc(REG_DESKTOP_HKCU, 'inferenceProvider') or '-'}")
    print(f"    inferenceGatewayBaseUrl: {_reg_doc(REG_DESKTOP_HKCU, 'inferenceGatewayBaseUrl') or '-'}")
    _k = _reg_doc(REG_DESKTOP_HKCU, "inferenceGatewayApiKey")
    print(f"    inferenceGatewayApiKey : {'(da dat, ' + str(len(_k)) + ' ky tu)' if _k else '-'}")
    print(f"    inferenceModels        : {_reg_doc(REG_DESKTOP_HKCU, 'inferenceModels') or '-'}")

    print("\n  Bien moi truong cap nguoi dung:")
    for ten in CLAUDE_ENV:
        print(f"    {ten:32} = {_doc_env_nguoi_dung(ten) or '-'}")
    for ten in (ENV_KHOA_CODEX, ENV_KHOA_CLAUDE):
        gt = _doc_env_nguoi_dung(ten)
        # KHONG in khoa. Chi noi co hay khong va dai bao nhieu.
        print(f"    {ten:32} = {'(da dat, ' + str(len(gt)) + ' ky tu)' if gt else '-'}")

    # ⭐ CHOT CHAN DOAN QUAN TRONG NHAT, va no khong hien nhien.
    #
    #    Bang tren doc REGISTRY - tuc "da dat chua". Nhung thu quyet dinh la
    #    TIEN TRINH CO NHIN THAY KHONG, va hai cai do co the khac nhau: `setx`
    #    ghi vao registry ngay, con mot phien Windows dang chay thi van mang moi
    #    truong CU cho toi khi dang nhap lai.
    #
    #    Do that 24/08 tren VM: registry co du ca nam bien, ma VS Code van bao
    #    `Missing environment variable`. Khong co dong nay thi khach nhin bang
    #    tren, thay "da dat", va khong hieu vi sao van hong.
    print("")
    print("  Tien trinh HIEN TAI co nhin thay khong:")
    for ten in (ENV_KHOA_CODEX, "ANTHROPIC_BASE_URL"):
        trong_tt = os.environ.get(ten)
        trong_reg = _doc_env_nguoi_dung(ten)
        if trong_reg and not trong_tt:
            print(f"    {ten:32} REGISTRY co, TIEN TRINH KHONG"
                  f"  <== dang xuat roi dang nhap lai")
        elif trong_tt:
            print(f"    {ten:32} co")
        else:
            print(f"    {ten:32} chua dat")
    return 0


def lenh_kiem(a) -> int:
    """Goi THAT mot luot. 'Da ghi tep' va 'cam duoc roi' la hai cau khac nhau."""
    khoa = (a.khoa or os.environ.get(ENV_KHOA_CODEX)
            or _doc_env_nguoi_dung(ENV_KHOA_CODEX) or "").strip()
    if not khoa:
        print(f"Khong tim thay khoa. Chay `cam` truoc, hoac dung --khoa.")
        return 1
    goc = a.goc or _doc_trang_thai().get("goc") or GOC_MAC_DINH

    def goi(duong, than=None, phuong="GET"):
        du = json.dumps(than).encode() if than is not None else None
        rq = urllib.request.Request(
            goc + "/api/v1" + duong, data=du, method=phuong,
            headers={"Authorization": "Bearer " + khoa,
                     "Content-Type": "application/json",
                     # BAT BUOC: Cloudflare tra 403 cho User-Agent mac dinh cua
                     # urllib TRUOC khi request toi duoc may chu.
                     "User-Agent": "ltt-cam-cli/1.0"})
        try:
            with urllib.request.urlopen(rq, timeout=180) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except OSError as e:
            return 0, str(e).encode()

    print(f"Kiem qua {goc}\n")
    m, b = goi("/tools")
    ten = [t.get("name") for t in (json.loads(b).get("items") or [])] if m == 200 else []
    print(f"  GET  /tools            -> {m}  {ten}")
    if m != 200:
        print(f"       {b[:300].decode('utf-8', 'replace')}")
        return 1

    m, b = goi("/credits/balance")
    du = (json.loads(b) or {}).get("balance") if m == 200 else "?"
    print(f"  GET  /credits/balance  -> {m}  so du {du}")

    m, b = goi("/messages", {"model": MODEL, "max_tokens": 200, "stream": True,
                             "messages": [{"role": "user",
                                           "content": "Tra loi mot tu: OK"}]},
               phuong="POST")
    print(f"  POST /messages         -> {m}  {len(b)} byte SSE")
    if m != 200:
        print(f"       {b[:300].decode('utf-8', 'replace')}")
        return 1
    print("\nCam duoc. Mo lai VS Code roi dung binh thuong.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="cam_cli",
        description="Cam Codex / Claude Code vao API cua LTT Studios")
    sub = ap.add_subparsers(dest="lenh", required=True)

    c = sub.add_parser("cam", help="ghi cau hinh")
    c.add_argument("--khoa", default="")
    c.add_argument("--goc", default=GOC_MAC_DINH)
    c.add_argument("--vscode", action="store_true",
                   help="cau hinh cho TIEN ICH VS Code: Codex ghi o goc config.toml "
                        "(thay luon mac dinh cua lenh codex), Claude Code chay "
                        "trong terminal")
    c.add_argument("--toan-cuc", action="store_true", dest="toan_cuc",
                   help="ghi ca ~/.claude/settings.json (TOAN CUC cho moi phien "
                        "Claude Code tren may nay)")

    sub.add_parser("go", help="go ra, tra ve nguyen trang")
    sub.add_parser("xem", help="xem dang cam gi")

    k = sub.add_parser("kiem", help="goi that mot luot de chac chan")
    k.add_argument("--khoa", default="")
    k.add_argument("--goc", default="")

    a = ap.parse_args(argv)
    return {"cam": lenh_cam, "go": lenh_go,
            "xem": lenh_xem, "kiem": lenh_kiem}[a.lenh](a)


if __name__ == "__main__":
    sys.exit(main())
