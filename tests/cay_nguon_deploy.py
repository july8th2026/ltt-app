"""Cay ma DEPLOY chep tu — mot cho duy nhat tra loi, cho moi phep kiem can no.

## Van de tep nay sinh ra de sua

Vai tep **gitignored co chu y** nhung production **doc luc chay**:

    apps\\*\\vendor      -> apps/upscalevideo/engine.py:30  (_EXE, _ENGINE_DIR)
    yolov8n.pt          -> cutclipshort/adapters/yolo.py:29

`setup/2-cai-dat.ps1` chep chung bang `$VAN_CHUYEN`, va — khac voi ma `.py` di
qua `git archive` — no chep tu **cay song** (`Join-Path $src $mau`), voi
`-ErrorAction SilentlyContinue`: thieu tep thi no **im lang bo qua**. Nen mot
lan deploy tu mot cay thieu vendor se **am tham go vendor khoi production**.

Ba phep kiem ton tai de chan dung chuyen do (`test_82::test_vendor_engine_co_mat`,
`test_505::test_moi_duong_khai_deu_CO_THAT_tren_dia`,
`test_505::test_DANH_SACH_VAN_CHUYEN_khop_dung_tap_DO_DUOC`). Chung **dung**.

🔴 **Nhung chung do VINH VIEN o moi worktree.** Tep gitignored khong di theo
   `git worktree add` — chung khong nam trong lich su. Do 12/09/2026 tren
   `ltt-llm-dual-model-4dfcf4`: ba phep kiem tren do trong CA HAI luot gate,
   trong khi cay chinh `D:\\LTTSTUDIOSAPP` co du `apps/upscalevideo/vendor` va
   `yolov8n.pt`.

⇒ Hau qua la mot **mau thuan trong chinh quy trinh**: hop dong van hanh doi
  *"truoc khi bao xong: `python tools\\gate.py` day du"* (§4, §7), con moi phien
  lam viec trong worktree — tuc **moi phien**, theo §5 — thi khong bao gio dat
  duoc mot luot gate xanh. Mot cong khong the qua duoc la mot cong se bi bo qua.

## Cach sua: hoi DUNG CAY, thay vi bo phep kiem

⛔ Khong skip. `tests/pg_scratch.py` da viet dung cau can viet o day: *"Skipping
   is how a mistake becomes silence"*. Mot phep kiem bi skip o worktree la mot
   phep kiem khong bao giờ chay, vi gan nhu moi viec deu lam trong worktree.

⭐ Cau hoi that cua ba phep kiem ay **khong** phai *"cay nay co vendor khong"*.
   No la *"cai cay ma deploy se chep tu do co vendor khong"* — va cay do **luon
   la cay chinh**, ke ca khi ta dang dung trong mot worktree:

   * `docs/16_CAP_NHAT_VA_DEPLOY.md` + bay #5 cua ban giao 12/09: **deploy chi
     tu cay chinh**, hoac tu mot ban chep thuan khong co `.git`. Deploy tu cay
     rieng bi chan.
   * nen o worktree, tra loi "cay nay thieu vendor" la tra loi **dung su that
     nhung sai cau hoi**: cay nay se khong bao gio la nguon deploy.

⇒ Hoi cay chinh. Khong mat mot phep kiem nao: xoa vendor o cay chinh van do, va
  do **ke ca khi dang chay tu worktree** — tuc phep kiem con manh hon truoc.
"""
from __future__ import annotations

import functools
import pathlib
import subprocess


@functools.lru_cache(maxsize=1)
def goc_nguon_deploy() -> pathlib.Path:
    """Thu muc goc cua cay ma deploy chep tu. O worktree: tra ve **cay chinh**.

    Dung `--git-common-dir` chu khong `--git-dir`: voi mot worktree, `--git-dir`
    tra `<chinh>/.git/worktrees/<ten>` con `--git-common-dir` tra `<chinh>/.git`.
    Cha cua cai thu hai chinh la cay chinh.

    ⚠️ Hong thi tra ve cay hien tai, khong nem. Mot phep kiem ve vendor khong
       duoc bien thanh mot phep kiem ve `git` co chay duoc hay khong — hai thu
       do hong theo hai cach khac nhau va doi hai cach sua khac nhau.
    """
    day = pathlib.Path(__file__).resolve().parents[1]
    try:
        ra = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                            cwd=day, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return day
    if ra.returncode != 0:
        return day
    common = (ra.stdout or "").strip()
    if not common:
        return day
    p = pathlib.Path(common)
    if not p.is_absolute():
        p = (day / p).resolve()
    return p.parent if p.name == ".git" else day


def la_worktree() -> bool:
    """Dang chay trong mot `git worktree` (khong phai cay chinh)?"""
    return goc_nguon_deploy() != pathlib.Path(__file__).resolve().parents[1]


def duong_nguon(tuong_doi: str) -> pathlib.Path:
    """Mot duong dan trong cay NGUON DEPLOY (dung dau gach cheo xuoi)."""
    return goc_nguon_deploy() / tuong_doi


def ghi_chu_cay() -> str:
    """Mot dong mo ta cay nao vua duoc hoi — dan vao thong bao khi phep kiem do.

    ⛔ Phep kiem nao dung module nay PHAI in dong nay khi do. Khong in thi mot
       nguoi doc o worktree se di tim vendor trong cay minh dang dung va khong
       hieu vi sao no do/xanh.
    """
    if not la_worktree():
        return f"(cay nguon deploy = cay hien tai: {goc_nguon_deploy()})"
    return (f"(dang o WORKTREE; phep kiem hoi CAY CHINH — nguon deploy that: "
            f"{goc_nguon_deploy()})")
