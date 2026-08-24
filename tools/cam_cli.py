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


def cam_codex(goc: str, tt: dict) -> list:
    ra = []
    thu_muc = NHA / ".codex"
    thu_muc.mkdir(parents=True, exist_ok=True)

    cfg = thu_muc / "config.toml"
    _sao_luu(cfg)
    van, crlf = _doc_giu_dong(cfg) if cfg.exists() else ("", "\n")
    _ghi_giu_dong(cfg, _chen_khoi(van, _codex_config(goc), crlf))
    ra.append(f"  [OK] {cfg}  (khoi co dau moc, phan con lai giu nguyen)")

    prof = thu_muc / "ltt.config.toml"
    # Ghi nho ta CO TAO tep nay hay khong - `go` chi xoa tep DO TA TAO.
    tt.setdefault("codex", {})["ta_tao_ltt_config"] = not prof.exists()
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
            ra.append(f"  [!!] GIU {prof} - no da co TRUOC khi chay cong cu nay")
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
    """Câu lệnh **đúng với cách khách đang chạy công cụ**.

    Khách cài `.exe` không có `tools\cam_cli.py`; khách chạy mã nguồn thì không
    có `.exe` trong PATH. In sai câu lệnh là gửi họ đi tìm một thứ không tồn tại.
    """
    if getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None)             or "__compiled__" in globals():
        return f"{pathlib.Path(sys.executable).name} {lenh}"
    return f"python tools\cam_cli.py {lenh}"


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
    for d in cam_codex(a.goc, tt):
        print(d)
    print("\nClaude Code:")
    for d in cam_claude(a.goc, tt, a.toan_cuc):
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
    tt["da_cam"] = False
    tt.pop("claude", None)
    tt.pop("codex", None)
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

    print("\n  Bien moi truong cap nguoi dung:")
    for ten in CLAUDE_ENV:
        print(f"    {ten:32} = {_doc_env_nguoi_dung(ten) or '-'}")
    for ten in (ENV_KHOA_CODEX, ENV_KHOA_CLAUDE):
        gt = _doc_env_nguoi_dung(ten)
        # KHONG in khoa. Chi noi co hay khong va dai bao nhieu.
        print(f"    {ten:32} = {'(da dat, ' + str(len(gt)) + ' ky tu)' if gt else '-'}")
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
