"""Bo test khong duoc ghi vao mat phang claim GPU TOAN MAY.

`platform_core/gpu_claims.py` doc/ghi `C:\\ProgramData\\gpu_claims\\claims\\` —
mot thu muc dung chung cho MOI HO tren may, khong rieng nen tang nay. May B co
ba ho dung chung GPU (du an video o `E:\\LTT AI`, LLM o `H:\\LTT_LLM`, va ta).

🔴 VI SAO `monkeypatch` KHONG DU, do duoc 2026-08-29.

   Bo test da duoc cat khoi mat phang nay bang `gpu_khong_claim_toan_may`
   (`tests/conftest.py`). Nhung `monkeypatch` chi tac dung TRONG TIEN TRINH
   CHA. `test_151` de tien trinh worker THAT, va worker con nap lai module roi
   GHI claim that vao `C:\\ProgramData` — dem duoc **16 tep** mang job id cua
   chinh bo test (`ja`, `jb`, `jx`, `job-khac`) sau mot luot.

   Chung tu lanh khi PID chet (`active()` don mo coi), nen day la NHIEU chu
   khong phai hong. Nhung no la bo test cua ta ghi vao khong gian dieu phoi cua
   ho khac, va no lam nhieu chinh phep do cua ta: mot claim that tren GPU 0 bi
   tru vao card GIA cung index 0.

⭐ Tien trinh con THUA KE moi truong, nen mot bien env bit duoc ca chieu DOC lan
   chieu GHI, o ca cha lan con — thu ma `monkeypatch` khong lam duoc.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Chay trong tien trinh CON. Khong dung f-string long nhau cho de doc.
_MA_CON = """
import sys
sys.path.insert(0, {goc!r})
from platform_core import gpu_claims as g
import json
print(json.dumps({{
    "root": str(g._ROOT),
    "token": bool(g.publish("lttplatform", 0, 1234, job="kiem_bien_env")),
}}))
"""


def _chay_con(claims_dir: pathlib.Path | None) -> dict:
    """Chay `_MA_CON` trong mot tien trinh RIENG, tra ve JSON no in ra.

    ⚠️ Truyen ma qua `-c` chu khong ghi mot tep vao `tmp_path`: duong `tmp_path`
       cua pytest vua SAU vua co DAU CACH
       (`...\\pytest-of-Thang Tuong\\pytest-NNNN\\ten_test_rat_dai\\`), va ban
       dau cua phep kiem nay TREO 120 giay o do trong khi cung doan ma chay
       xong trong 1,9 giay khi goi thang. Khong dao sau nguyen nhan: duong ngan
       vua bo duoc bien do vua lam phep kiem doc de hon.
    """
    env = {k: v for k, v in os.environ.items() if k != "LTT_GPU_CLAIMS_DIR"}
    if claims_dir is not None:
        env["LTT_GPU_CLAIMS_DIR"] = str(claims_dir)
    r = subprocess.run([sys.executable, "-c", _MA_CON.format(goc=str(GOC))],
                       capture_output=True, text=True, env=env,
                       timeout=120, cwd=str(GOC))
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_tien_trinh_CON_ghi_vao_thu_muc_tam_chu_khong_vao_ProgramData():
    """Bat bien chinh: worker con phai theo bien env, khong theo duong cung."""
    import tempfile

    tmp_path = pathlib.Path(tempfile.mkdtemp(prefix="clm_"))
    ra = _chay_con(tmp_path / "gpu_claims")

    assert ra["token"] is True, "tien trinh con khong publish duoc claim"
    assert str(tmp_path) in ra["root"], (
        f"tien trinh con van dung {ra['root']} — bien env khong toi duoc no")

    sinh = list((tmp_path / "gpu_claims" / "claims").glob("*.json"))
    assert len(sinh) == 1, f"mong doi 1 claim trong thu muc tam, thay {len(sinh)}"

    that = pathlib.Path(r"C:\ProgramData\gpu_claims\claims")
    if that.is_dir():
        ro_ri = [f.name for f in that.glob("*.json")
                 if b"kiem_bien_env" in f.read_bytes()]
        assert ro_ri == [], f"claim cua test RO RI ra thu muc dung chung: {ro_ri}"


def test_khong_dat_bien_thi_van_la_duong_THAT():
    """Chieu nguoc lai, va no quan trong ngang chieu tren.

    ⛔ Dat bien nay o production nghia la nen tang khong con thay claim cua ho
       khac — dung thu ma ca co che nay sinh ra de tranh. Nen mac dinh PHAI la
       duong that, va phep kiem nay chot dieu do.
    """
    ra = _chay_con(None)

    assert ra["root"].replace("/", "\\").lower().endswith(
        r"programdata\gpu_claims"), (
        f"mac dinh phai la duong that, thay {ra['root']}")

    # Don claim vua sinh ra o duong that — chinh phep kiem nay cung khong duoc
    # de lai rac trong khong gian dung chung.
    that = pathlib.Path(r"C:\ProgramData\gpu_claims\claims")
    if that.is_dir():
        for f in that.glob("*.json"):
            try:
                if b"kiem_bien_env" in f.read_bytes():
                    f.unlink()
            except OSError:
                pass


def test_deploy_va_setup_KHONG_dat_bien_nay():
    """Banh coc: bien nay la do dung cua test, khong duoc lot vao production."""
    xau = []
    for thu_muc in ("deploy", "setup"):
        goc = GOC / thu_muc
        if not goc.is_dir():
            continue
        for f in goc.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".ps1", ".py", ".env", ".json"):
                try:
                    if "LTT_GPU_CLAIMS_DIR" in f.read_text(encoding="utf-8",
                                                           errors="replace"):
                        xau.append(f.relative_to(GOC).as_posix())
                except OSError:
                    pass
    assert xau == [], f"bien chi-danh-cho-test bi dat o duong trien khai: {xau}"
