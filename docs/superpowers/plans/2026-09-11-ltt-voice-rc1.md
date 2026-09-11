# LTT Voice RC1 — Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hợp nhất 6 nhánh Voice treo (9 commit) vào MỘT cây RC trên nền production `3100c317`, theo 9 quyết định đã khoá, sao cho Tầng 1 (`READY_FOR_DEPLOYMENT`) chứng minh được bằng một SHA.

**Architecture:** Mỗi task là một commit nguyên tử trên nhánh `claude/ltt-voice-reconciliation-165a40`. Nội dung từ nhánh nguồn được **đọc theo hành vi rồi viết lại** trên RC — không merge, không cherry-pick nguyên commit. Mọi luật làn đi qua `lan_ngon_ngu.quyet_dinh`; mọi cửa tiêu tiền theo thứ tự ①–⑥ của `docs/LTT_VOICE/CHUAN_VAN_HANH_CUA.md` §3.

**Tech Stack:** Python 3 · FastAPI · SQLAlchemy + Alembic · Jinja2 · JS thuần (`server/static/voice.js`) · pytest · Playwright (Chrome) · faster-whisper (CPU) cho đo làn.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md` — đọc cùng kế hoạch này. Mọi D-id/T-id/INV-id/SC-id dưới đây trỏ vào spec.

## Global Constraints

- Cây: `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-4bot-workflow-app-550cab`, nhánh `claude/ltt-voice-reconciliation-165a40`, gốc `3100c317`. Không `cd` sang cây khác; không checkout nhánh nguồn — đọc bằng `git show <sha>:<path>` / `git show <sha> -- <path>`.
- Không chạm việc của phiên khác. `git add` **tường minh từng tệp**. Không `-A`, không `.`, không `stash`, không `reset`, không `--amend`.
- Tệp dùng chung (`tools/gate.py`, `locale/en/LC_MESSAGES/messages.po`, `CLAUDE.md`, `AGENTS.md`, `tools/dich_ltt_voice_en.py`) chỉ sửa bằng **Edit**, không **Write**.
- Ghi tệp: UTF-8 **không BOM**, xuống dòng **LF**; `.ps1` thuần ASCII; không viết Python inline qua PowerShell. Lệnh Bash dùng đường dẫn `/` (Bash nuốt `\`). Sau khi ghi `.py` mới: `python -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" <tệp>`.
- Chuỗi giao diện tiếng Việt bọc `_()`/`N_()`; bản dịch EN thêm vào dict `DICH` của `tools/dich_ltt_voice_en.py`, rồi `python -X utf8 tools/dich_ltt_voice_en.py && python tools/i18n.py bien-dich`. **Không** chạy `i18n.py trich`.
- Sửa `server/static/ltt.css` ⇒ chạy `python tools/dong_goi_gui.py` để đồng bộ `tools/gui/ltt.css` (test_284).
- **CPU (máy 10 lõi dùng chung):** mỗi task chỉ chạy **đúng các tệp test của task** (≤ 2 tệp, tuần tự, không `-n`). Lệnh nặng (≥ 3 tệp test, `gate.py` mọi chế độ, E2E) **chỉ ở Task 16**, trước đó bắt buộc `python tools/cua_so_yen.py trang-thai` + xem cây tiến trình; có phiên khác giữ ⇒ chờ. Trần `-n 6`.
- Số test theo spec §6.4: 351 · 357 · 358 · 520–528; 529–549 dự trữ. Sau khi thêm/đổi tên test: `python tools/check_so_test.py`.
- Migration: chuỗi `d15b8c30f7a4 → 20260911_1000 (ngon_ngu_nguon) → 20260911_1100 (voice_lich_su)`; một head.
- Commit message: tiêu đề tiếng Việt không dấu, thân có `Reconciled-from: <sha> (<phần>)` và `Dropped: <gì> (<D/T/SC-id>)` khi áp dụng, kết thúc bằng `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Không deploy. Không đọc `secrets/` trừ Task 16 bước tổng hợp thật (khi được cấp).

## File Structure

| Tệp | Trách nhiệm | Task |
|---|---|---|
| `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json` | sổ cái máy đọc (vùng, nguồn, yêu cầu, cấp phát test) | 1 |
| `tools/doi_soat_voice.py` | đối soát chỉ đọc: commit vùng Voice chưa có dòng sổ cái | 1 |
| `tools/check_voice_qa.py`, `tools/voice_mock_sidecar.py`, `tools/voice_e2e_server.py`, `tools/voice_e2e_check.py`, `tests/browser/ltt_voice_*.js`, `docs/LTT_VOICE/QA/*` | hàng rào QA + E2E mock | 2, 15 |
| `apps/ltt_voice/lan_ngon_ngu.py` | thẩm quyền làn duy nhất | 3 |
| `apps/ltt_voice/giong_vong_doi.py` (mới) | hằng số nguồn gốc làn + trạng thái + phép chuyển hợp lệ | 4, 6 |
| `alembic/versions/20260911_1000_voice_ngon_ngu_nguon.py` (mới) | cột `ngon_ngu_nguon` | 4 |
| `apps/ltt_voice/routes/_p_giong.py` | ghi danh · khai làn · thu hồi | 5, 6 |
| `apps/ltt_voice/jobs.py` | worker ghi danh: kiểm trạng thái, đặt `loi` | 6 |
| `tools/di_tru_lan_asr.py` (mới) | đo làn giọng cũ bằng ASR, `--ghi`, `--dao` | 7 |
| `alembic/versions/20260911_1100_voice_lich_su.py` (mới), `apps/ltt_voice/lich_su_nd.py` (mới) | đánh dấu đã tải/đã xoá của Lịch sử | 8 |
| `apps/ltt_voice/du_an.py`, `routes/_p_du_an.py` | trạng thái khối/dự án suy ra | 9 |
| `apps/ltt_voice/nghe_thu.py`, `routes/_p_nghe_thu.py`, `routes/_p_audio.py`, `tham_chieu.py` | preview kho chung · phán quyết nghe thử · bề mặt ASV | 10 |
| `apps/ltt_voice/templates/*.html`, `server/static/voice.js`, `server/static/ltt.css` | giao diện | 5, 6, 8, 9, 10, 11 |
| `platform_core/registry.py`, `platform_core/public_api/{catalog,invocation}.py`, `server/api/jobs.py`, `apps/ltt_voice/kiem_truoc_api.py` (mới) | hook kiểm-trước D007 | 12 |
| `tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py` | bánh cóc cửa tiêu tiền (INV-TIEN-1/2, INV-LAN-3) | 13 |
| `tools/nghiem_thu_deploy.py` | so cả tệp không `.py` | 14 |

## Thứ tự và song song

```
1 ─► 2 ─► 3 ─► 4 ─► 5 ─► 6 ─► 7 ─► 8 ─► 9 ─► 10 ─► 11 ─► 12 ─► 13 ─► 14 ─► 15 ─► 16
```
Chạy **tuần tự**, mỗi task tự commit (ruling pre-flight: hook pre-commit kiểm cả cây,
việc dở của một agent song song làm hỏng commit của agent kia). Task 2, 7, 12, 14
độc lập về tệp — thứ tự giữa chúng đổi được, nhưng không chạy cùng lúc.

---

### Task 1: Sổ cái hợp nhất + công cụ đối soát

**Files:**
- Create: `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json`
- Create: `tools/doi_soat_voice.py`
- Create: `tests/test_527_doi_soat_voice.py`
- Modify: `docs/LTT_VOICE/NGUON_CHAN_LY.md` (bảng tra + bản đồ tài liệu + mục ⑥)

**Interfaces:**
- Produces: `tools/doi_soat_voice.py` với `nap_so_cai(p) -> dict`, `kiem_hinh_dang(so: dict) -> list[str]`, `commit_chua_doi_soat(so: dict, *, goc: pathlib.Path, trunk: str) -> list[dict]` (mỗi dict `{sha, nhanh, tieu_de}`), `main(argv=None) -> int` (0 = sạch, 1 = có commit chưa đối soát hoặc lỗi hình dạng).

- [ ] **Step 1: Viết test hỏng**

```python
"""Công cụ đối soát sổ cái hợp nhất Voice — INV-CHU-1 (spec §5, §6.5).

⛔ KHÔNG khẳng định "kho thật có 0 commit chưa đối soát": con số ấy phụ thuộc
   nhánh của phiên KHÁC, và một test phụ thuộc trạng thái ngoài là test đỏ vì
   người khác. Kho thật được đo ở Task 16, bằng tay, không bằng pytest.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap_cong_cu():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "doi_soat_voice", GOC / "tools" / "doi_soat_voice.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def kho(tmp_path):
    r = tmp_path / "kho"
    r.mkdir()
    _git(r, "init", "-q", "-b", "trunk")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "apps" / "ltt_voice").mkdir(parents=True)
    (r / "khac").mkdir()
    (r / "apps" / "ltt_voice" / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "goc")
    _git(r, "checkout", "-q", "-b", "nhanh-voice")
    (r / "apps" / "ltt_voice" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _git(r, "commit", "-q", "-am", "sua voice")
    sha_voice = _git(r, "rev-parse", "HEAD")
    _git(r, "checkout", "-q", "trunk")
    _git(r, "checkout", "-q", "-b", "nhanh-khac")
    (r / "khac" / "b.txt").write_text("b\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "khong phai voice")
    _git(r, "checkout", "-q", "trunk")
    return r, sha_voice


def _so(nguon=()):
    return {"phien_ban": 1, "trunk": "trunk",
            "rc": {"nhanh": "rc", "goc": "0" * 40},
            "vung": ["apps/ltt_voice"],
            "nguon": list(nguon), "yeu_cau": [], "cap_phat_test": {}}


def test_bat_duoc_commit_vung_voice_chua_co_dong(kho):
    m = _nap_cong_cu()
    r, sha = kho
    ra = m.commit_chua_doi_soat(_so(), goc=r, trunk="trunk")
    assert [x["sha"] for x in ra] == [sha], ra
    assert ra[0]["nhanh"] == "nhanh-voice"


def test_commit_da_co_dong_thi_khong_bao(kho):
    m = _nap_cong_cu()
    r, sha = kho
    dong = {"sha": sha[:8], "nhanh": "nhanh-voice", "hang_muc": "x",
            "ket_cuc": "DROP", "ly_do": "T-03", "rc_sha": "", "test": ""}
    assert m.commit_chua_doi_soat(_so([dong]), goc=r, trunk="trunk") == []


def test_commit_ngoai_vung_KHONG_bi_dem(kho):
    m = _nap_cong_cu()
    r, _ = kho
    ra = m.commit_chua_doi_soat(_so(), goc=r, trunk="trunk")
    assert all(x["nhanh"] != "nhanh-khac" for x in ra)


@pytest.mark.parametrize("hong, can", [
    ({"ket_cuc": "MAYBE"}, "ket_cuc"),
    ({"ly_do": ""}, "ly_do"),
    ({"sha": "abc"}, "sha"),
])
def test_hinh_dang_sai_thi_noi_ra(hong, can):
    m = _nap_cong_cu()
    dong = {"sha": "a" * 8, "nhanh": "n", "hang_muc": "x", "ket_cuc": "KEEP",
            "ly_do": "D002", "rc_sha": "", "test": ""}
    dong.update(hong)
    loi = m.kiem_hinh_dang(_so([dong]))
    assert any(can in s for s in loi), loi


def test_so_cai_THAT_dung_hinh_dang():
    m = _nap_cong_cu()
    so = m.nap_so_cai(GOC / "docs" / "LTT_VOICE" / "HOP_NHAT" / "SO_CAI.json")
    assert m.kiem_hinh_dang(so) == []
    # Đối chứng: sổ cái thật phải chứa đủ 9 commit nguồn của spec §1.3.
    co = {d["sha"][:8] for d in so["nguon"]}
    for sha in ("65e099af", "0915f1f3", "29ac2300", "27baa1a8", "31878cc2",
                "dca96e84", "ca6a00ce", "a3a2a46e", "3634412a"):
        assert sha in co, sha
```

- [ ] **Step 2: Chạy test, xác nhận hỏng**

Run: `python -m pytest tests/test_527_doi_soat_voice.py -q`
Expected: FAIL (`FileNotFoundError` — `tools/doi_soat_voice.py` chưa có).

- [ ] **Step 3: Viết công cụ**

```python
"""doi_soat_voice.py — CHI DOC. Commit vung Voice nao chua co dong so cai?

    python tools/doi_soat_voice.py            # bang + ma thoat
    python tools/doi_soat_voice.py --json

INV-CHU-1 (spec 2026-09-11 §5): moi commit cham vung Voice ma chua len trunk
phai co DUNG MOT dong trong docs/LTT_VOICE/HOP_NHAT/SO_CAI.json.

Chay o BA thoi diem: dau phien, truoc ff, truoc deploy. KHONG phai buoc gate:
gate chay o moi cay va khong duoc do vi nhanh cua phien khac.
Khong ghi gi: chi `git for-each-ref` va `git log`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
SO_CAI = GOC / "docs" / "LTT_VOICE" / "HOP_NHAT" / "SO_CAI.json"
KET_CUC = ("KEEP", "DROP", "FIX")
_SHA = re.compile(r"^[0-9a-f]{8,40}$")


def _git(goc: pathlib.Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(goc), *a], check=True,
                          capture_output=True, text=True,
                          encoding="utf-8").stdout


def nap_so_cai(p: pathlib.Path = SO_CAI) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def kiem_hinh_dang(so: dict) -> list:
    loi = []
    for k in ("trunk", "rc", "vung", "nguon", "yeu_cau", "cap_phat_test"):
        if k not in so:
            loi.append(f"thieu khoa `{k}`")
    if not so.get("vung"):
        loi.append("`vung` rong — doi soat se xanh-rong")
    thay = set()
    for i, d in enumerate(so.get("nguon") or ()):
        sha = str(d.get("sha") or "")
        if not _SHA.fullmatch(sha):
            loi.append(f"nguon[{i}].sha khong phai sha hop le: {sha!r}")
        if sha[:8] in thay:
            loi.append(f"nguon[{i}].sha trung: {sha[:8]}")
        thay.add(sha[:8])
        if d.get("ket_cuc") not in KET_CUC:
            loi.append(f"nguon[{i}].ket_cuc phai la {KET_CUC}: {d.get('ket_cuc')!r}")
        if len(str(d.get("ly_do") or "").strip()) < 3:
            loi.append(f"nguon[{i}].ly_do rong — mot ket cuc khong ly do la mot cua bi quen")
    return loi


def commit_chua_doi_soat(so: dict, *, goc: pathlib.Path = GOC,
                         trunk: str = "") -> list:
    trunk = trunk or so["trunk"]
    rc = str((so.get("rc") or {}).get("nhanh") or "")
    co = {str(d["sha"])[:8] for d in so.get("nguon") or ()}
    refs = _git(goc, "for-each-ref", "--format=%(refname:short)",
                "refs/heads", "refs/remotes").split()
    ra, thay = [], set()
    for ref in refs:
        if ref in (trunk, rc, f"origin/{trunk}", f"origin/{rc}") or ref.endswith("/HEAD"):
            continue
        out = _git(goc, "log", "--no-merges", "--format=%H\t%s",
                   f"{trunk}..{ref}", "--", *so["vung"])
        for dong in out.splitlines():
            sha, _, tieu_de = dong.partition("\t")
            if sha[:8] in co or sha in thay:
                continue
            thay.add(sha)
            ra.append({"sha": sha, "nhanh": ref, "tieu_de": tieu_de})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    so = nap_so_cai()
    loi = kiem_hinh_dang(so)
    thieu = [] if loi else commit_chua_doi_soat(so)
    if a.json:
        print(json.dumps({"loi_hinh_dang": loi, "chua_doi_soat": thieu},
                         ensure_ascii=False, indent=2))
    else:
        for s in loi:
            print(f"  LOI  {s}")
        for x in thieu:
            print(f"  THIEU {x['sha'][:8]}  {x['nhanh']:45s} {x['tieu_de'][:70]}")
        print(f"RESULT: {'PASS' if not (loi or thieu) else 'FAIL'} "
              f"({len(thieu)} commit chua doi soat, {len(loi)} loi hinh dang)")
    return 1 if (loi or thieu) else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Viết sổ cái thật**

Tạo `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json`. `vung`: `["apps/ltt_voice", "server/static/voice.js", "voice_sidecar", "tests/browser/ltt_voice_golden.js", "tests/browser/ltt_voice_negative.js", "tests/browser/ltt_voice_smoke.js"]`. `rc`: `{"nhanh": "claude/ltt-voice-reconciliation-165a40", "goc": "3100c317df8b7a7c1d9a161723931ae56fc1a318", "spec": "docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md"}`. `trunk`: `"admin-mvp-v3"`. `cap_phat_test`: đúng bảng spec §6.4 (khoá = số dạng chuỗi, giá trị = tên tệp). `nguon`: một dòng cho mỗi commit dưới đây (`rc_sha` để `""`, điền ở Task 16):

| sha | nhánh | hạng mục | ket_cuc | ly_do |
|---|---|---|---|---|
| `65e099af` | `claude/ltt-voice-gui-mvp-ed62d6` | GUI MVP + chính sách làn thứ hai | FIX | giữ: preview kho chung (T-08), cửa khai làn (D004), GUI làn (Task 11); bỏ: SC-1, SC-6, SC-7, SC-13, T-03 |
| `0915f1f3` | `claude/my-voices-enrollment-prod-379a22` | nguồn gốc làn + thu hồi | FIX | D003, T-04, T-07; bỏ mặc định `""` (D003) |
| `29ac2300` | `claude/my-voices-enrollment-prod-379a22` | cửa khai làn (JSON) | FIX | gộp với 65e099af (D004, SC-2) |
| `27baa1a8` | `claude/history-audio-storage-auth-4cffe3` | Lịch sử: hết hạn | KEEP | Task 8 |
| `31878cc2` | `claude/history-audio-storage-auth-4cffe3` | Lịch sử: xoá + đã tải | FIX | D005, T-04, T-11; giữ hotfix doc_lai (SC-8) |
| `dca96e84` | `claude/history-audio-storage-auth-4cffe3` | nghĩa vụ nền tảng bảng mới | KEEP | Task 8 |
| `ca6a00ce` | `claude/projects-longform-slice-ab2e77` | badge dự án suy ra | FIX | D005 (suy cả từ tệp hết hạn), T-05 |
| `a3a2a46e` | `claude/ltt-voice-qa-ci-gate-1c85fb` | hàng rào QA | FIX | T-12 (mock thêm 3 cửa) |
| `3634412a` | `claude/studio-voice-picker-ui-6782bb` | nút nghe thử loading/lỗi | FIX | T-13 (i18n) |
| `891d93db` | `phien/asv-v4` | `duong_cho_app_khac` cho ASV | KEEP | T-09, D008 |

Sau đó chạy `python tools/doi_soat_voice.py`. Mọi dòng `THIEU` còn lại: đọc `git show --stat <sha>`, thêm dòng với `ket_cuc` và `ly_do` thật (commit của chương trình khác không thuộc Voice nhưng chạm vùng ⇒ `DROP`, `ly_do` = "khong thuoc RC1 — chuong trinh <X>, khong doi hanh vi Voice" chỉ khi diff xác nhận điều đó; nếu nó đổi hành vi Voice ⇒ dừng, báo phiên điều phối). Lặp tới `RESULT: PASS`.

- [ ] **Step 5: Trỏ từ NGUON_CHAN_LY.md**

Trong `docs/LTT_VOICE/NGUON_CHAN_LY.md`: thêm vào bảng tra dòng `| Nhánh Voice nào chưa hạ cánh, và kết cục của nó | docs/LTT_VOICE/HOP_NHAT/SO_CAI.json + tools/doi_soat_voice.py | máy đo (INV-CHU-1) |`; thêm vào bản đồ tài liệu dòng `| docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md | 11/09 | ✅ **hợp đồng** RC1: D001–D009, bất biến |` ở đầu bảng; thêm mục `### ⑥ *"Đoán lệch làn chỉ nên cảnh báo"* — ĐÚNG lúc viết (01/09), SAI từ Q121 (10/09)` giải thích: nhánh `ltt-voice-gui-mvp-ed62d6` mang chính sách này; đã bỏ ở RC1 (SC-1); bằng chứng: D002 + `test_522`.

- [ ] **Step 6: Chạy test, xác nhận xanh**

Run: `python -m pytest tests/test_527_doi_soat_voice.py -q` → PASS. Run: `python tools/doi_soat_voice.py` → `RESULT: PASS`. Run: `python tools/check_so_test.py` → PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/LTT_VOICE/HOP_NHAT/SO_CAI.json tools/doi_soat_voice.py tests/test_527_doi_soat_voice.py docs/LTT_VOICE/NGUON_CHAN_LY.md docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md docs/superpowers/plans/2026-09-11-ltt-voice-rc1.md
git commit -m "LTT Voice RC1: so cai hop nhat + doi soat chi doc (INV-CHU-1)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Hàng rào QA + E2E mock (song song)

**Files:**
- Create (từ `a3a2a46e`): `docs/LTT_VOICE/QA/00_TEST_MATRIX.md`, `docs/LTT_VOICE/QA/01_RELEASE_VERIFICATION.md`, `tests/browser/ltt_voice_golden.js`, `tests/browser/ltt_voice_negative.js`, `tests/browser/ltt_voice_smoke.js`, `tools/check_voice_qa.py`, `tools/voice_e2e_check.py`, `tools/voice_e2e_server.py`, `tools/voice_mock_sidecar.py`
- Modify: `tools/gate.py` (một `Step`, bằng **Edit**)

**Interfaces:**
- Consumes: không.
- Produces: `tools/voice_mock_sidecar.py` phục vụ thêm `POST /v1/lo-ra-tep`, `POST /v1/ghep-tep`, `POST /v1/stream` (Task 15 dùng); `tools/check_voice_qa.py::rao_tinh() -> list[str]` (danh sách lỗi, rỗng = xanh).

- [ ] **Step 1: Lấy tệp từ nguồn**

Với mỗi tệp Create ở trên: `git show a3a2a46e:<path> > <path>` (qua Bash, đường dẫn `/`). Không lấy `tools/gate.py` từ nhánh.

- [ ] **Step 2: Chèn bước gate bằng Edit**

Đọc `git show a3a2a46e -- tools/gate.py`: nó thêm `Step("voice QA rao", [python, "tools/check_voice_qa.py"])` ngay sau bước "app contract lint". Tìm đúng chỗ ấy trong `tools/gate.py` hiện tại và chèn cùng khối (kể cả chú thích) bằng **Edit**. Không đổi dòng nào khác.

- [ ] **Step 3: Viết test hỏng cho ba cửa mock mới**

Thêm vào cuối `tools/check_voice_qa.py` một hằng `CUA_MOCK_BAT_BUOC = ("/v1/speech", "/v1/speech-dai", "/v1/batch", "/v1/lo-ra-tep", "/v1/ghep-tep", "/v1/stream")` và trong `rao_tinh()` một phép kiểm: mọi chuỗi trong `CUA_MOCK_BAT_BUOC` phải xuất hiện trong nguồn `tools/voice_mock_sidecar.py`; thiếu ⇒ thêm lỗi `f"mock thieu cua {c} — duong van ban dai se khong duoc phu"`. Chạy `python tools/check_voice_qa.py` → FAIL nêu 3 cửa.

- [ ] **Step 4: Thêm ba cửa vào mock**

Đọc `apps/ltt_voice/sidecar_client.py` để lấy đúng hình dạng request/response của `lo_ra_tep`, `ghep_tep`, `stream` (tên hàm có thể khác — `grep -n "def \|/v1/" apps/ltt_voice/sidecar_client.py`). Trong `tools/voice_mock_sidecar.py` thêm ba handler trả **đúng hình dạng** client đọc, dùng lại bộ sinh WAV tất định sẵn có của mock (cùng dấu vân tay "mock" trên 3 kênh mà `check_voice_qa` ghim). `/v1/stream` trả các khối WAV nối tiếp theo giao thức client đọc.

- [ ] **Step 5: Xanh**

Run: `python tools/check_voice_qa.py` → `RESULT` xanh (0 lỗi). Run: `python -c "import ast,sys;[ast.parse(open(p,encoding='utf-8').read()) for p in sys.argv[1:]]" tools/check_voice_qa.py tools/voice_mock_sidecar.py tools/voice_e2e_server.py tools/voice_e2e_check.py`.

- [ ] **Step 6: Commit** (git add tường minh từng tệp)

Tệp: các tệp Create + `tools/gate.py`. Message: `LTT Voice RC1: hang rao QA + E2E mock (3 cua moi cho van ban dai)` với `Reconciled-from: a3a2a46e (toan bo)`.

---

### Task 3: Luật làn — lời khai chỉ THẮT (D002) + một thẩm quyền (INV-02, T-16)

**Files:**
- Modify: `apps/ltt_voice/lan_ngon_ngu.py:303-340` (`quyet_dinh`)
- Modify: `tests/test_355_hop_dong_lan_giong.py:239-250`
- Create: `tests/test_522_mot_tham_quyen_lan.py`
- Modify: mọi chỗ gõ lại cặp `("vi", "en")` trong `apps/ltt_voice/**/*.py` ngoài `lan_ngon_ngu.py` (đo bằng test 522; đã biết: `routes/_p_giong.py:104`, `tham_chieu.py:151`, `lui_giong.py:102`, `features.py:178`) và `lui_giong.py:tu_giong_mau` (đọc làn từ `giong_mau.lan_cua`)
- Modify: `docs/QUYET_DINH_NEN_TANG.md` (mục Q121: thêm ô D002)
- Modify: `apps/ltt_voice/templates/ltt_voice_studio.html:119` (T-15: câu sai)

**Interfaces:**
- Consumes: `lan_ngon_ngu.chuan_lan`, `doan_ngon_ngu`, `PhanQuyet`, hằng `MA_LOI_*`, `NGUON_*`, `MAU_*` (đã có).
- Produces: `quyet_dinh(lan_giong: str, text: str, khai_bao: str = "") -> PhanQuyet` — cùng chữ ký, luật mới: chặn khi khai ≠ làn giọng HOẶC đoán chắc ≠ làn giọng. `lan_ngon_ngu.LAN_HOP_LE` là nguồn duy nhất của danh sách làn.

- [ ] **Step 1: Sửa test cũ thành test hỏng**

Thay `test_khai_bao_THANG_phep_doan` trong `tests/test_355_hop_dong_lan_giong.py` bằng:

```python
def test_khai_bao_chi_THAT_khong_NOI():
    """D002 (2026-09-11): lời khai chỉ THÊM ràng buộc, không bao giờ miễn trừ.

    ⭐ Trước D002 test này tên là `test_khai_bao_THANG_phep_doan` và nó GHIM một
       đường vòng: khai `vi` rồi dán văn bản tiếng Anh ⇒ giọng Việt đọc tiếng Anh,
       khách trả tiền cho đúng lỗi chất lượng Q121 dựng ra để chặn.
    """
    # Khai lệch giọng ⇒ chặn, nguồn là lời khai (như cũ).
    pq = L.quyet_dinh(L.LAN_VI, VI_RO, "en")
    assert not pq.cho_phep and pq.nguon == L.NGUON_KHAI_BAO

    # 🔴 Ô MỚI: khai ĐÚNG làn giọng nhưng văn bản CHẮC là làn kia ⇒ chặn.
    pq = L.quyet_dinh(L.LAN_VI, EN_RO, "vi")
    assert not pq.cho_phep
    assert pq.nguon == L.NGUON_DOAN and pq.ma_loi == L.MA_LOI_LECH_LAN
    assert pq.lan_text == L.LAN_EN

    # Văn bản không dấu, chỉ MỘT từ chức năng tiếng Anh ("the") ⇒ đoán không
    # chắc ⇒ lời khai đứng ⇒ cho. Đây là ca khách gõ không dấu phải KHÔNG bị hại.
    pq = L.quyet_dinh(L.LAN_VI, "Ban co the mua ve o day", "vi")
    assert pq.cho_phep and pq.nguon == L.NGUON_KHAI_BAO

    # Khai + đoán + giọng cùng một làn ⇒ cho.
    assert L.quyet_dinh(L.LAN_EN, EN_RO, "en").cho_phep
```

- [ ] **Step 2: Viết test 522**

```python
"""INV-02: chỉ `lan_ngon_ngu` được phán về làn — và danh sách làn chỉ có một bản.

Đọc CÂY CÚ PHÁP, không khớp chuỗi — xem [[bo-do-quet-van-ban-trung-phat-viec-giai-thich]]:
một phép quét văn bản sẽ báo động trên chính chú thích giải thích nó.
"""
from __future__ import annotations

import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "ltt_voice"
THAM_QUYEN = APP / "lan_ngon_ngu.py"

#: Tên của chính sách làn thứ hai (nhánh GUI MVP, SC-1). Bỏ ở RC1; không được mọc lại.
BIA_MO = {"xung_dot", "cau_xung_dot", "_chan_xung_dot_lan", "_MAU_XUNG_DOT"}
MA_LOI = {"voice_language_mismatch", "voice_language_unknown"}


def _cac_tep():
    return [p for p in APP.rglob("*.py") if "__pycache__" not in p.parts]


def _cay(p):
    return ast.parse(p.read_text(encoding="utf-8"))


def test_doi_chung_phep_quet_THAY_duoc_tham_quyen():
    ten = {n.func.id for n in ast.walk(_cay(THAM_QUYEN))
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "PhanQuyet" in ten, "phep quet khong thay chinh tham quyen — no dang xanh-rong"


def test_chi_lan_ngon_ngu_DUNG_PhanQuyet():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "PhanQuyet") or (
                    isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "PhanQuyet"):
                sai.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert not sai, f"phan quyet lan dung ngoai tham quyen: {sai}"


def test_ma_loi_lan_chi_GO_o_tham_quyen():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if isinstance(n, ast.Constant) and n.value in MA_LOI:
                sai.append(f"{p.relative_to(GOC)}:{n.lineno} {n.value}")
    assert not sai, f"go lai ma loi lan thay vi dung hang so: {sai}"


def test_chinh_sach_lan_thu_hai_KHONG_moc_lai():
    sai = []
    for p in _cac_tep():
        for n in ast.walk(_cay(p)):
            ten = (getattr(n, "name", None) if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                   else getattr(n, "id", None) if isinstance(n, ast.Name) else None)
            if ten in BIA_MO:
                sai.append(f"{p.relative_to(GOC)}:{n.lineno} {ten}")
    assert not sai, f"SC-1 moc lai: {sai}"


def test_cap_vi_en_KHONG_go_lai_ngoai_tham_quyen():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
                gt = {e.value for e in n.elts if isinstance(e, ast.Constant)}
                if {"vi", "en"} <= gt:
                    sai.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert not sai, f"danh sach lan go lai (dung lan_ngon_ngu.LAN_HOP_LE): {sai}"
```

- [ ] **Step 3: Chạy, xác nhận hỏng**

Run: `python -m pytest tests/test_355_hop_dong_lan_giong.py::test_khai_bao_chi_THAT_khong_NOI tests/test_522_mot_tham_quyen_lan.py -q`
Expected: FAIL ở `test_khai_bao_chi_THAT_khong_NOI` (cho phép) và `test_cap_vi_en_KHONG_go_lai_ngoai_tham_quyen` (liệt kê các chỗ gõ lại).

- [ ] **Step 4: Đổi `quyet_dinh`**

Thay thân hàm sau docstring (giữ docstring, thêm một dòng vào bảng: `khai hoặc đoán-chắc ≠ làn giọng → CHẶN voice_language_mismatch (D002)` và một đoạn `🔴 D002 (2026-09-11)` giải thích lời khai chỉ thắt):

```python
    lan_g = chuan_lan(lan_giong)
    if not lan_g:
        # Giọng mập mờ ⇒ CHẶN. Chiều ngược với văn bản mập mờ, và cố ý —
        # xem docstring đầu tệp.
        return PhanQuyet(cho_phep=False, ma_loi=MA_LOI_LAN_KHONG_RO,
                         mau=MAU_LAN_KHONG_RO)

    khai = chuan_lan(khai_bao)
    if khai and khai != lan_g:
        return PhanQuyet(cho_phep=False, lan_giong=lan_g, lan_text=khai,
                         nguon=NGUON_KHAI_BAO, ma_loi=MA_LOI_LECH_LAN,
                         mau=MAU_LECH_LAN)
    # 🔴 D002: phép đoán CHẮC vẫn chạy khi khách đã khai. Lời khai chỉ được
    #    THÊM ràng buộc; nó không bao giờ là giấy miễn trừ cho một văn bản mà
    #    máy biết chắc là làn kia.
    doan = doan_ngon_ngu(text)
    if doan and doan != lan_g:
        return PhanQuyet(cho_phep=False, lan_giong=lan_g, lan_text=doan,
                         nguon=NGUON_DOAN, ma_loi=MA_LOI_LECH_LAN,
                         mau=MAU_LECH_LAN)
    if khai:
        return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=khai,
                         nguon=NGUON_KHAI_BAO)
    if doan:
        return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=doan,
                         nguon=NGUON_DOAN)
    return PhanQuyet(cho_phep=True, lan_giong=lan_g, lan_text=lan_g,
                     nguon=NGUON_THEO_GIONG)
```

`giai_lan_van_ban` giữ nguyên (còn người gọi khác). Sửa docstring của nó: bỏ câu "Chỉ `khai_bao` và `doan` mới chặn được" nếu mâu thuẫn; thêm "`quyet_dinh` không còn dùng hàm này để phán — xem D002".

- [ ] **Step 5: Gom danh sách làn (T-16)**

Mỗi vị trí test 522 liệt kê: thay tuple gõ tay bằng `lan_ngon_ngu.LAN_HOP_LE` (hoặc `("auto", *lan_ngon_ngu.LAN_HOP_LE)` ở `features.py:178`). `lui_giong.tu_giong_mau`: thay `"vi"` gõ cứng bằng `giong_mau.lan_cua(<mã preset>)`. **Không** đổi fallback `→ "vi"` ở `_p_giong.py:104` ở task này ngoài việc dùng hằng số — hành vi ghi danh đổi ở Task 5.

- [ ] **Step 6: Câu sai ở Studio (T-15)**

`ltt_voice_studio.html:119`: thay `_("Chỉ dùng để nhắc khi văn bản lệch làn của giọng. Máy đọc được cả hai thứ tiếng dù bạn chọn gì.")` bằng `_("Chọn ngôn ngữ của văn bản. Giọng phải cùng ngôn ngữ; lượt lệch sẽ bị từ chối trước khi trừ credit.")`. Thêm cặp dịch vào `DICH`: `"Choose the language of your script. The voice must match it; a mismatched request is refused before any credit is charged."`. Bỏ cặp dịch của câu cũ khỏi `DICH` nếu có. Biên dịch `.mo`.

- [ ] **Step 7: Cập nhật Q121**

Trong `docs/QUYET_DINH_NEN_TANG.md` mục Q121: thêm một khối `**Sửa đổi 2026-09-11 (D002, RC1):**` — lời khai chỉ thắt; bảng thêm ô "khai đúng làn giọng + đoán chắc làn kia ⇒ CHẶN `voice_language_mismatch`, `nguon=doan`"; con trỏ `docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md` §4.

- [ ] **Step 8: Xanh**

Run: `python -m pytest tests/test_355_hop_dong_lan_giong.py tests/test_522_mot_tham_quyen_lan.py -q` → PASS. Run: `python tools/check_dich_thieu.py` nếu tồn tại (else bỏ qua) → PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/ltt_voice/lan_ngon_ngu.py tests/test_355_hop_dong_lan_giong.py tests/test_522_mot_tham_quyen_lan.py apps/ltt_voice/features.py apps/ltt_voice/tham_chieu.py apps/ltt_voice/lui_giong.py apps/ltt_voice/routes/_p_giong.py apps/ltt_voice/templates/ltt_voice_studio.html docs/QUYET_DINH_NEN_TANG.md tools/dich_ltt_voice_en.py locale/en/LC_MESSAGES/messages.po locale/en/LC_MESSAGES/messages.mo
git commit -m "LTT Voice RC1: loi khai chi THAT khong NOI (D002) + mot tham quyen lan (INV-02)" -m "Dropped: test_khai_bao_THANG_phep_doan (ghim duong vong qua Q121)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
(`git add` chỉ những tệp thật sự đổi — kiểm bằng `git status --short`.)

---

### Task 4: Nguồn gốc làn — cột, migration, `giong_vong_doi` (D003, T-04)

**Files:**
- Create: `apps/ltt_voice/giong_vong_doi.py` (lấy khung từ `0915f1f3`, sửa theo dưới)
- Create: `alembic/versions/20260911_1000_voice_ngon_ngu_nguon.py`
- Modify: `apps/ltt_voice/tables.py` (`VoiceProfile`: thêm `ngon_ngu_nguon`)
- Create: `tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py` (phần mô hình + migration; phần route ở Task 5)

**Interfaces:**
- Produces (trong `giong_vong_doi.py`):
  - hằng `NGUON_KHAI_BAO = "khai_bao"`, `NGUON_DO_ASR = "do_asr"`, `NGUON_MAC_DINH_CU = "mac_dinh_cu"`, `NGUON_HOP_LE = (NGUON_KHAI_BAO, NGUON_DO_ASR, NGUON_MAC_DINH_CU)`
  - hằng trạng thái `TT_DANG_GHI_DANH, TT_ACTIVE, TT_DISABLED, TT_REVOKED, TT_LOI` = `"dang_ghi_danh", "active", "disabled", "revoked", "loi"`
  - `co_the_chuyen(tu: str, den: str) -> bool` — bảng chuyển spec §6.3: `dang_ghi_danh→active|loi`, `active→disabled|revoked`, `disabled→active|revoked`, `loi→revoked`; mọi thứ khác False; `revoked→*` False.
  - `khai_lan_hop_le(lan_moi: str, *, lan_hien: str, nguon_hien: str) -> str` — trả `""` nếu được, hoặc mã lỗi: `"voice_language_required"` khi `lan_moi` không thuộc `lan_ngon_ngu.LAN_HOP_LE`; `"voice_language_measured"` khi `nguon_hien == NGUON_DO_ASR and lan_moi != lan_hien`.
- Migration: revision `"e1a2b3c4d5f6"`, `down_revision = "d15b8c30f7a4"`.

- [ ] **Step 1: Test hỏng (mô hình + phép chuyển + luật khai)**

```python
"""D003/D004 — nguồn gốc làn của giọng nhân bản, và luật sửa làn."""
from __future__ import annotations

import pytest

from apps.ltt_voice import giong_vong_doi as V
from apps.ltt_voice import lan_ngon_ngu as L


@pytest.mark.parametrize("tu, den, duoc", [
    ("dang_ghi_danh", "active", True), ("dang_ghi_danh", "loi", True),
    ("dang_ghi_danh", "revoked", False),          # T-07: chặn thu hồi khi đang ghi danh
    ("active", "revoked", True), ("disabled", "revoked", True),
    ("revoked", "active", False), ("revoked", "disabled", False),  # INV-THU-HOI-1
    ("loi", "revoked", True), ("loi", "active", False),
])
def test_bang_chuyen_trang_thai(tu, den, duoc):
    assert V.co_the_chuyen(tu, den) is duoc


def test_khai_lan_la_hoac_rong_bi_tu_choi():
    for x in ("", "auto", "fr", "VN"):
        assert V.khai_lan_hop_le(x, lan_hien="vi", nguon_hien=V.NGUON_KHAI_BAO) \
            == "voice_language_required"


def test_khai_nguoc_PHEP_DO_bi_tu_choi_trung_thi_duoc():
    assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) \
        == "voice_language_measured"
    assert V.khai_lan_hop_le("vi", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) == ""


def test_khai_bao_va_mac_dinh_cu_sua_tu_do():
    for nguon in (V.NGUON_KHAI_BAO, V.NGUON_MAC_DINH_CU):
        assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=nguon) == ""


def test_lan_hop_le_lay_tu_tham_quyen():
    assert set(L.LAN_HOP_LE) == {"vi", "en"}


def test_migration_mot_head_va_danh_dau_dong_cu():
    import pathlib, re
    goc = pathlib.Path(__file__).resolve().parents[1]
    m = (goc / "alembic" / "versions" / "20260911_1000_voice_ngon_ngu_nguon.py").read_text(encoding="utf-8")
    assert re.search(r'down_revision\s*=\s*"d15b8c30f7a4"', m)
    assert "mac_dinh_cu" in m
    # Migration KHÔNG được gán lại `ngon_ngu` của dòng cũ (spec §6.2).
    assert not re.search(r"ngon_ngu\s*=\s*'", m.replace("ngon_ngu_nguon", ""))
```

- [ ] **Step 2: Chạy, xác nhận hỏng**

Run: `python -m pytest tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py -q` → FAIL (`ModuleNotFoundError: giong_vong_doi`).

- [ ] **Step 3: Viết `giong_vong_doi.py`**

Đọc `git show 0915f1f3:apps/ltt_voice/giong_vong_doi.py` để giữ giọng văn/chú thích. Viết lại theo Interfaces ở trên; **bỏ** `chuan_hoa_khai_bao_ngon_ngu` trả `("", chua_biet)` (D003: không còn "chưa biết" lúc ghi danh) và **bỏ** hằng `chua_biet`. Giữ `khoa_can_xoa` để Task 6 sửa. Dùng `lan_ngon_ngu.LAN_HOP_LE` cho danh sách làn.

```python
_CHUYEN = {
    TT_DANG_GHI_DANH: {TT_ACTIVE, TT_LOI},
    TT_ACTIVE: {TT_DISABLED, TT_REVOKED},
    TT_DISABLED: {TT_ACTIVE, TT_REVOKED},
    TT_LOI: {TT_REVOKED},
    TT_REVOKED: set(),
}


def co_the_chuyen(tu: str, den: str) -> bool:
    return den in _CHUYEN.get(tu, set())


def khai_lan_hop_le(lan_moi: str, *, lan_hien: str, nguon_hien: str) -> str:
    lan = lan_ngon_ngu.chuan_lan(lan_moi)
    if lan not in lan_ngon_ngu.LAN_HOP_LE:
        return "voice_language_required"
    if nguon_hien == NGUON_DO_ASR and lan != lan_ngon_ngu.chuan_lan(lan_hien):
        return "voice_language_measured"
    return ""
```

- [ ] **Step 4: Cột + migration**

`tables.py` `VoiceProfile`: sau `ngon_ngu` thêm
```python
    #: D003 (RC1): `ngon_ngu` đến từ ĐÂU — `khai_bao` · `do_asr` · `mac_dinh_cu`.
    #: Thẩm quyền của các giá trị: `giong_vong_doi.NGUON_HOP_LE`.
    ngon_ngu_nguon: Mapped[str] = mapped_column(String(16), default="",
                                                server_default="", nullable=False)
```
Migration (`alembic/versions/20260911_1000_voice_ngon_ngu_nguon.py`), theo khuôn tệp `20260909_1200_vps_v2_cach_ly.py`:
```python
"""voice_profile.ngon_ngu_nguon — nguồn gốc làn (RC1, D003).

Đánh dấu MỌI dòng đã có là `mac_dinh_cu`: trước 08/09 form ghi danh không có ô
ngôn ngữ, sau 08/09 form chọn sẵn `vi` — không dòng nào có lời khai chắc chắn.
KHÔNG gán lại `ngon_ngu`. Đo làn thật là việc của `tools/di_tru_lan_asr.py`.
"""
from alembic import op
import sqlalchemy as sa

revision = "e1a2b3c4d5f6"
down_revision = "d15b8c30f7a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("voice_profile") as b:
        b.add_column(sa.Column("ngon_ngu_nguon", sa.String(16),
                               nullable=False, server_default=""))
    op.execute("UPDATE voice_profile SET ngon_ngu_nguon = 'mac_dinh_cu'")


def downgrade() -> None:
    with op.batch_alter_table("voice_profile") as b:
        b.drop_column("ngon_ngu_nguon")
```
Kiểm `revision` chưa bị dùng: `git grep -n "e1a2b3c4d5f6" -- alembic` rỗng.

- [ ] **Step 5: Xanh**

Run: `python -m pytest tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py -q` → PASS. Run: `python -m pytest tests/test_103*.py -q -k head` (phép kiểm một head, một tệp) → PASS.

- [ ] **Step 6: Commit**

`git add apps/ltt_voice/giong_vong_doi.py apps/ltt_voice/tables.py alembic/versions/20260911_1000_voice_ngon_ngu_nguon.py tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py` — message `LTT Voice RC1: nguon goc lan cua giong (D003) — cot + migration noi chuoi` với `Reconciled-from: 0915f1f3 (giong_vong_doi, cot)`, `Dropped: mac dinh "" + chua_biet (D003); down_revision f2c48b71e903 (SC-9)`.

---

### Task 5: Ghi danh bắt khai + cửa khai làn gộp (D003, D004, T-06 enroll)

**Files:**
- Modify: `apps/ltt_voice/routes/_p_giong.py` (`tao_giong`; route mới `POST /giong/{id}/ngon-ngu`)
- Modify: `apps/ltt_voice/doc_man_giong.py` (xuất `ngon_ngu`, `ngon_ngu_nguon`, `can_xac_nhan_lan`)
- Modify: `apps/ltt_voice/templates/ltt_voice_giong.html`, `apps/ltt_voice/templates/_voice_the.html`
- Modify: `apps/ltt_voice/nghe_thu.py` (hàm dựng lại preview một giọng khi đổi làn)
- Create: `tests/test_520_ltt_voice_so_huu.py` (lấy khung từ `0915f1f3`/`29ac2300` `test_396_ltt_voice_so_huu.py`, đổi số)
- Modify: `tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py` (thêm ca route)

**Interfaces:**
- Consumes: `giong_vong_doi.khai_lan_hop_le`, `NGUON_*` (Task 4); `lan_ngon_ngu.LAN_HOP_LE`.
- Produces: `POST /ltt-voice/giong/{public_id}/ngon-ngu` (form `ngon_ngu`, `csrf_token`) → 303 về `/ltt-voice/giong` khi thành công; lỗi → 400 JSON `{"ok": false, "loi": <câu>, "ma_loi": <mã>}` khi `Accept: application/json`, ngược lại 303 kèm thông báo lỗi (theo khuôn `_loi_400` trong `_p_tao.py`). `tao_giong` thiếu/sai `ngon_ngu` ⇒ 400 `ma_loi = "voice_language_required"`.

- [ ] **Step 1: Test hỏng (route)**

Trong `test_521` thêm fixture `khach` chép **nguyên** từ `tests/test_519_ltt_voice_studio_nop_trung.py:42-104` (đổi tên DB tệp/email/secret sang `voice-521`), rồi:

```python
def _csrf_giong(client) -> str:
    import re
    r = client.get("/ltt-voice/giong")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    assert m
    return m.group(1)


def _wav_1s() -> bytes:
    import io, math, struct, wave
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 9)))
                               for i in range(24000 * 6)))
    return b.getvalue()


@pytest.mark.parametrize("lan", ["", "auto", "fr"])
def test_ghi_danh_KHONG_khai_lan_bi_tu_choi_va_KHONG_tru_tien(khach, lan):
    client, uid = khach
    r = client.post("/ltt-voice/giong/tao",
                    data={"ten": "Giong A", "dong_y": "1", "ngon_ngu": lan,
                          "csrf_token": _csrf_giong(client)},
                    files={"tep": ("a.wav", _wav_1s(), "audio/wav")},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400, r.text
    assert r.json()["ma_loi"] == "voice_language_required"
    assert _so_job(uid) == 0          # chép helper `_so_job` từ test_519


def test_ghi_danh_khai_en_luu_nguon_khai_bao(khach):
    client, uid = khach
    r = client.post("/ltt-voice/giong/tao",
                    data={"ten": "Giong B", "dong_y": "1", "ngon_ngu": "en",
                          "csrf_token": _csrf_giong(client)},
                    files={"tep": ("b.wav", _wav_1s(), "audio/wav")})
    assert r.status_code in (200, 303), r.text
    ho_so = _ho_so(uid, "Giong B")   # helper: query VoiceProfile theo owner + ten
    assert (ho_so.ngon_ngu, ho_so.ngon_ngu_nguon) == ("en", "khai_bao")
```

Trong `test_520` (khung từ `git show 29ac2300:tests/test_396_ltt_voice_so_huu.py`, đổi số; giữ ca IDOR/consent của nhánh nhưng **bỏ** ca "khai về `""`"), thêm:

```python
def test_khai_lan_nguoc_PHEP_DO_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="do_asr")  # helper ghi thẳng DB
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400 and r.json()["ma_loi"] == "voice_language_measured"


def test_khai_lan_mac_dinh_cu_thanh_khai_bao(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="mac_dinh_cu")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)})
    assert r.status_code == 303
    ho_so = _ho_so_theo_pid(pid)
    assert (ho_so.ngon_ngu, ho_so.ngon_ngu_nguon) == ("en", "khai_bao")


def test_khai_lan_giong_NGUOI_KHAC_khong_duoc(khach):
    client, uid = khach
    pid = _tao_giong_active("nguoi-khac-uuid", ngon_ngu="vi", nguon="khai_bao")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code in (400, 404)
    assert _ho_so_theo_pid(pid).ngon_ngu == "vi"


def test_khai_lan_giong_DA_THU_HOI_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao", trang_thai="revoked")
    r = client.post(f"/ltt-voice/giong/{pid}/ngon-ngu",
                    data={"ngon_ngu": "en", "csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400
```

Helper `_tao_giong_active(owner, *, ngon_ngu, nguon, trang_thai="active") -> str` ghi một `VoiceProfile` trực tiếp qua session và trả `public_id`; `_ho_so_theo_pid(pid)` đọc lại.

- [ ] **Step 2: Chạy, xác nhận hỏng**

Run: `python -m pytest tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py tests/test_520_ltt_voice_so_huu.py -q` → FAIL (ghi danh "" vẫn 200 với `"vi"`; route 404).

- [ ] **Step 3: `tao_giong`**

`ngon_ngu: str = Form("")`. Trước mọi ghi DB/credit: `ma = giong_vong_doi.khai_lan_hop_le(ngon_ngu, lan_hien="", nguon_hien="")`; nếu `ma` ⇒ trả 400 theo khuôn `_loi_400` với câu `_("Hãy chọn ngôn ngữ của clip giọng: Tiếng Việt hoặc Tiếng Anh.")` và `ma_loi=ma`. Tạo `VoiceProfile(..., ngon_ngu=lan_ngon_ngu.chuan_lan(ngon_ngu), ngon_ngu_nguon=giong_vong_doi.NGUON_KHAI_BAO, ...)`. Truyền `dedupe_key=dedupe_key_for("ltt_voice.enroll", {"owner": uid, "ten": ten.strip()})` vào `submit_with_credit` (import từ `platform_core.job_submit`, cùng cách `_p_tao.py:444`). Giữ lời nhắn trùng tên thân thiện của `0915f1f3` (bắt `IntegrityError` → câu sửa được).

- [ ] **Step 4: Route khai làn**

Theo khuôn `tat_giong` (`_p_giong.py:147`): CSRF → `tham_chieu.chi_chu_so_huu(db, public_id, owner_id=uid)` (không có ⇒ 404 cùng câu với không tồn tại) → `trang_thai == "revoked"` ⇒ 400 `ma_loi="voice_revoked"` → `ma = giong_vong_doi.khai_lan_hop_le(ngon_ngu, lan_hien=ho_so.ngon_ngu, nguon_hien=ho_so.ngon_ngu_nguon)` ⇒ 400 nếu có → nếu `lan` đổi: cập nhật `ngon_ngu`, `ngon_ngu_nguon = NGUON_KHAI_BAO`, gọi `nghe_thu.dung_lai_cho_giong(db, ho_so)` (Step 5); nếu `lan` trùng và nguồn là `mac_dinh_cu`: chỉ đổi nguồn thành `khai_bao` (xác nhận) → 303 về `/ltt-voice/giong`. Câu lỗi `voice_language_measured`: `_("Clip nguồn của giọng này đo được là {lan}. Không đổi được sang ngôn ngữ khác.")` điền `lan_ngon_ngu.NHAN_LAN`.

- [ ] **Step 5: Dựng lại preview khi đổi làn**

Trong `nghe_thu.py` thêm `dung_lai_cho_giong(db, ho_so) -> None`: xoá mọi khoá `voice/{owner}/{public_id}/preview-*.wav` qua `storage` (liệt kê theo tiền tố như `khoa_can_xoa` của `0915f1f3`), để vòng bảo trì dựng lại theo `CAU_THEO_LAN[ngon_ngu mới]`. Không gọi engine đồng bộ trong request.

- [ ] **Step 6: Giao diện**

`ltt_voice_giong.html`: ô Ngôn ngữ ở form ghi danh **không** chọn sẵn (`<option value="" selected disabled>{{ _("Chọn ngôn ngữ của clip") }}</option>` + VI/EN lấy từ `nhan_lan`), `required`. `_voice_the.html`: với giọng của chính khách (`not g.la_mau and not g.chung`), nếu `g.ngon_ngu_nguon == "mac_dinh_cu"` hiện khối `{{ _("Xác nhận ngôn ngữ của giọng này") }}` + form POST `/ltt-voice/giong/{{ g.public_id }}/ngon-ngu` (select VI/EN chọn sẵn làn hiện tại, nút `{{ _("Xác nhận") }}`); giọng `khai_bao` hiện nút nhỏ `{{ _("Đổi ngôn ngữ") }}` cùng form; giọng `do_asr` hiện nhãn `{{ _("Đo từ clip") }}`, không có form. `doc_man_giong.py` xuất ba trường. Mọi chuỗi mới vào `DICH` + biên dịch.

- [ ] **Step 7: Xanh**

Run: `python -m pytest tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py tests/test_520_ltt_voice_so_huu.py -q` → PASS. Run: `python tools/check_so_test.py` → PASS.

- [ ] **Step 8: Commit**

Tệp: `_p_giong.py`, `doc_man_giong.py`, `nghe_thu.py`, hai template, hai test, `dich_ltt_voice_en.py`, `messages.po`, `messages.mo`. Message `LTT Voice RC1: ghi danh bat khai lan + mot cua khai lan (D003, D004)` · `Reconciled-from: 29ac2300 (khai_ngon_ngu: nguon goc, chan revoked), 65e099af (dat_ngon_ngu_giong: form+303)` · `Dropped: khai ve "" (D004); fallback "vi" o ghi danh (D003)`.

---

### Task 6: Thu hồi giọng + worker (T-07, T-14, INV-THU-HOI-1)

**Files:**
- Modify: `apps/ltt_voice/routes/_p_giong.py` (`POST /giong/{id}/xoa`, `POST /giong/xoa-nhieu`; `tat_giong` dùng `co_the_chuyen`)
- Modify: `apps/ltt_voice/giong_vong_doi.py` (`khoa_can_xoa` → toàn tiền tố)
- Modify: `apps/ltt_voice/jobs.py` (`_ghi_danh`: kiểm trạng thái trước `active`; đặt `loi`)
- Modify: `apps/ltt_voice/features.py:340-350` (câu cho `revoked`, `loi`)
- Modify: `apps/ltt_voice/dieu_khoan.py` (phiên bản điều khoản + điều "Xoá giọng", từ `0915f1f3`)
- Modify: `tests/test_343_khoa_kho_don_duoc.py` (theo `0915f1f3`)
- Modify: `apps/ltt_voice/templates/ltt_voice_giong.html` (nút thu hồi + chọn nhiều, từ `0915f1f3`)
- Modify: `tests/test_520_ltt_voice_so_huu.py`

**Interfaces:**
- Consumes: `giong_vong_doi.co_the_chuyen`, `TT_*` (Task 4).
- Produces: `giong_vong_doi.khoa_can_xoa(owner_id: str, public_id: str) -> str` trả **tiền tố** `f"voice/{owner_id}/{public_id}/"`; `_ghi_danh` không bao giờ đặt `active` cho hồ sơ không ở `dang_ghi_danh`.

- [ ] **Step 1: Test hỏng**

```python
def test_thu_hoi_xoa_CA_TIEN_TO_giu_ho_so(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao")
    from platform_core.storage import get_storage
    st = get_storage()
    for ten in ("nguon.wav", "repr.npz", "preview-v2-aaa.wav", "preview-v2-bbb.wav"):
        st.put(f"voice/{uid}/{pid}/{ten}", b"x")
    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf_giong(client)})
    assert r.status_code == 303
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"
    for ten in ("nguon.wav", "repr.npz", "preview-v2-aaa.wav", "preview-v2-bbb.wav"):
        assert not st.exists(f"voice/{uid}/{pid}/{ten}"), ten


def test_thu_hoi_khi_DANG_GHI_DANH_bi_chan(khach):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    r = client.post(f"/ltt-voice/giong/{pid}/xoa",
                    data={"csrf_token": _csrf_giong(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400
    assert _ho_so_theo_pid(pid).trang_thai == "dang_ghi_danh"


def test_worker_KHONG_bat_lai_giong_da_thu_hoi(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao", trang_thai="revoked")
    from apps.ltt_voice import jobs, sidecar_client
    monkeypatch.setattr(sidecar_client, "ghi_danh",
                        lambda *a, **k: {"ref_b64": "QUJD", "chon_doan": {}})
    _dat_nguon(uid, pid)  # helper: put một clip nguồn vào kho đúng khoá jobs đọc
    with pytest.raises(Exception):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))  # helper dựng params như tao_giong
    assert _ho_so_theo_pid(pid).trang_thai == "revoked"


def test_ghi_danh_hong_VINH_VIEN_dat_loi(khach, monkeypatch):
    client, uid = khach
    pid = _tao_giong_active(uid, ngon_ngu="vi", nguon="khai_bao",
                            trang_thai="dang_ghi_danh")
    from apps.ltt_voice import jobs, sidecar_client
    from apps.ltt_voice.features import LoiGiongNoi

    def _hong(*a, **k):
        raise LoiGiongNoi("clip hong")
    monkeypatch.setattr(sidecar_client, "ghi_danh", _hong)
    _dat_nguon(uid, pid)
    with pytest.raises(LoiGiongNoi):
        jobs._ghi_danh(_params_ghi_danh(uid, pid))
    assert _ho_so_theo_pid(pid).trang_thai == "loi"
```

Đọc chữ ký thật của `jobs._ghi_danh` và cách nó nhận `params` (`grep -n "def _ghi_danh" -A30 apps/ltt_voice/jobs.py`) để viết `_params_ghi_danh`; nếu `_ghi_danh` nhận `(job)` thay vì `(params)`, dựng một đối tượng tối thiểu có đúng thuộc tính nó đọc.

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_520_ltt_voice_so_huu.py -q` → FAIL (route 404; worker đặt `active`; không có `loi`).

- [ ] **Step 3: Hiện thực**

- `khoa_can_xoa` trả tiền tố; route `xoa` liệt kê mọi khoá dưới tiền tố (dùng API liệt kê của `platform_core.storage` — `grep -n "def list\|def iter\|def ls" platform_core/storage.py`) và xoá từng khoá; `FileNotFoundError` = đã đạt. Chuyển trạng thái chỉ khi `co_the_chuyen(ho_so.trang_thai, TT_REVOKED)`, ngược lại 400 `ma_loi="voice_state_invalid"`. `xoa-nhieu` gọi cùng hàm lõi cho từng id (một hàm `_thu_hoi_mot(db, st, ho_so)`), trả tóm tắt.
- `tat_giong`: từ chối nếu `not co_the_chuyen(ho_so.trang_thai, TT_DISABLED)`.
- `jobs._ghi_danh`: ngay trước `.values(trang_thai="active")` đổi thành `UPDATE ... WHERE id = :id AND trang_thai = 'dang_ghi_danh'`; nếu `rowcount == 0` ⇒ xoá `VoiceRepr` vừa thêm + khoá biểu diễn vừa lưu, ném `LoiGiongNoi(_t("Giọng này đã bị thu hồi."))`. Bọc lời gọi `sidecar_client.ghi_danh`: `except LoiNguoiGoi` (lỗi vĩnh viễn) ⇒ `UPDATE ... SET trang_thai='loi' WHERE id=:id AND trang_thai='dang_ghi_danh'` rồi ném lại.
- `features.giai_giong`: `trang_thai == "revoked"` ⇒ `_t("Giọng này đã bị thu hồi và không dùng được nữa.")`; `"loi"` ⇒ `_t("Ghi danh giọng này không thành công. Hãy tạo lại giọng với một clip khác.")`; `disabled` giữ câu cũ.
- Điều khoản + `test_343` + template: lấy từ `git show 0915f1f3 -- <tệp>`, áp lên bản hiện tại.

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_520_ltt_voice_so_huu.py tests/test_343_khoa_kho_don_duoc.py -q` → PASS.

- [ ] **Step 5: Commit** — message `LTT Voice RC1: thu hoi giong xoa ca tien to + worker khong bat lai (T-07, T-14)` · `Reconciled-from: 0915f1f3 (xoa, xoa-nhieu, dieu khoan)` · `Dropped: khoa_can_xoa chi xoa preview hien hanh; cho thu hoi khi dang_ghi_danh`.

---

### Task 7: Công cụ di trú làn bằng ASR (D003) (song song)

**Files:**
- Create: `tools/di_tru_lan_asr.py`
- Create: `tests/test_523_di_tru_lan_asr.py`

**Interfaces:**
- Consumes: cột `voice_profile.ngon_ngu_nguon` (Task 4 — test dùng SQLite tạm tự tạo bảng qua `Base.metadata.create_all`, nên chạy được khi Task 4 đã commit).
- Produces: CLI `python tools/di_tru_lan_asr.py [--ghi] [--dao <nhat_ky.json>] [--nguong 0.90] [--luong 4]`; hàm thuần `quyet_lan(do: dict, *, lan_hien: str, nguong: float) -> tuple[str, str]` trả `(lan_moi, nguon_moi)` hoặc `("", "")` khi không đổi.

- [ ] **Step 1: Test hỏng**

```python
"""D003 — đo làn giọng cũ bằng ASR. Thuần + chạy khô; KHÔNG gọi ASR thật."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _m():
    s = importlib.util.spec_from_file_location("di_tru_lan_asr", GOC / "tools" / "di_tru_lan_asr.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


@pytest.mark.parametrize("do, lan_hien, ra", [
    ({"ngon_ngu": "en", "do_tin": 0.99}, "vi", ("en", "do_asr")),   # gắn nhầm, đo chắc ⇒ sửa
    ({"ngon_ngu": "vi", "do_tin": 0.97}, "vi", ("vi", "do_asr")),   # đúng, đo chắc ⇒ ghi nguồn
    ({"ngon_ngu": "en", "do_tin": 0.60}, "vi", ("", "")),           # không chắc ⇒ giữ mac_dinh_cu
    ({"ngon_ngu": "fr", "do_tin": 0.99}, "vi", ("", "")),           # ngoài làn ⇒ giữ
    ({"loi": "khong thay venv"}, "vi", ("", "")),                    # ASR hỏng ⇒ giữ
])
def test_quyet_lan(do, lan_hien, ra):
    assert _m().quyet_lan(do, lan_hien=lan_hien, nguong=0.90) == ra


def test_chay_kho_KHONG_ghi_va_dao_duoc(tmp_path, monkeypatch):
    m = _m()
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables as T
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    db.add(T.VoiceProfile(owner_id="u1", ten_hien_thi="A", ngon_ngu="vi",
                          ngon_ngu_nguon="mac_dinh_cu", trang_thai="active"))
    db.commit()
    monkeypatch.setattr(m, "_do_mot", lambda db, ho_so: {"ngon_ngu": "en", "do_tin": 0.99})

    ra = m.chay(ghi=False, nguong=0.90, nhat_ky=tmp_path / "nk.json")
    assert ra["se_doi"] == 1 and ra["da_ghi"] == 0
    assert db.query(T.VoiceProfile).one().ngon_ngu == "vi"

    ra = m.chay(ghi=True, nguong=0.90, nhat_ky=tmp_path / "nk.json")
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("en", "do_asr")
    nk = json.loads((tmp_path / "nk.json").read_text(encoding="utf-8"))
    assert nk[0]["cu"] == {"ngon_ngu": "vi", "ngon_ngu_nguon": "mac_dinh_cu"}

    m.dao(tmp_path / "nk.json")
    db.expire_all()
    hs = db.query(T.VoiceProfile).one()
    assert (hs.ngon_ngu, hs.ngon_ngu_nguon) == ("vi", "mac_dinh_cu")
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()
```

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_523_di_tru_lan_asr.py -q` → FAIL.

- [ ] **Step 3: Viết công cụ**

Khung: docstring nói rõ CHẠY KHÔ mặc định, `--ghi` mới ghi, `--dao` đảo từ nhật ký; chỉ xét `ngon_ngu_nguon == "mac_dinh_cu"` và `trang_thai != "revoked"`; nhật ký JSON ghi `{public_id, cu:{ngon_ngu, ngon_ngu_nguon}, moi:{...}, do:{ngon_ngu, do_tin}}` **trước** khi ghi DB. `_do_mot(db, ho_so)`: tìm khoá clip nguồn của hồ sơ (đọc cách `jobs._ghi_danh` lấy `nguon_key`), tải về tệp tạm, gọi ASR theo **đúng khuôn** `tools/soi_kho_giong_cu.py::_nghe_lai` (subprocess venv nền tảng, `faster_whisper`, `device='cpu'`, `compute_type='int8'`) **nhưng** thêm `cpu_threads=<--luong, mặc định 4>` vào `WhisperModel(...)` (máy dùng chung — không để ctranslate2 chiếm mọi lõi). Chạy tuần tự, một clip một lần.

```python
LAN_DO = {"vi": "vi", "en": "en"}


def quyet_lan(do: dict, *, lan_hien: str, nguong: float) -> tuple:
    if do.get("loi"):
        return "", ""
    lan = LAN_DO.get(str(do.get("ngon_ngu") or ""))
    if not lan or float(do.get("do_tin") or 0) < nguong:
        return "", ""
    return lan, "do_asr"
```

`chay(*, ghi, nguong, nhat_ky) -> dict` trả `{"xet", "se_doi", "da_ghi", "khong_chac"}`; `dao(nhat_ky)` khôi phục `cu` cho mỗi mục. `main()` in bảng + tổng.

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_523_di_tru_lan_asr.py -q` → PASS.

- [ ] **Step 5: Commit** (git add tường minh từng tệp) — tệp: công cụ + test. Message `LTT Voice RC1: cong cu do lan giong cu bang ASR (D003) — chay kho mac dinh, dao duoc`.

---

### Task 8: Lịch sử — hết hạn, xoá, đã tải (D005, T-04, T-06, T-11)

**Files:**
- Create: `alembic/versions/20260911_1100_voice_lich_su.py` (từ `31878cc2:alembic/versions/20260910_1900_voice_lich_su.py`, `down_revision = "e1a2b3c4d5f6"`, giữ `revision` của nhánh nếu chưa bị dùng: `git grep -n "<revision>" -- alembic`)
- Create: `apps/ltt_voice/lich_su_nd.py` (từ `31878cc2`)
- Modify: `apps/ltt_voice/tables.py` (bảng `voice_lich_su`, từ `31878cc2`)
- Modify: `apps/ltt_voice/doc_man_lich_su.py` (từ `27baa1a8` + `31878cc2`)
- Modify: `apps/ltt_voice/routes/_p_lich_su.py` — **chỉ thêm** route `xoa_luot`, `danh_dau_tai` và phần hiển thị hết hạn; **giữ nguyên** `doc_lai` của trunk (hotfix `dc6d9c6b`, SC-8) và **thêm** `dedupe_key` vào nó
- Modify: `apps/ltt_voice/templates/ltt_voice_lich_su.html`, `server/static/voice.js` (hộp xác nhận nêu khối bị ảnh hưởng)
- Modify: `platform_core/public_api/governance.py`, `tools/restore_drill_schema.py` (từ `dca96e84`; giữ cả hai ràng buộc ở `restore_drill_schema.py:223-240`)
- Create: `tests/test_351_ltt_voice_lifecycle_authz.py` (từ `31878cc2`)
- Create: `tests/test_525_lich_su_xoa_trang_thai_suy.py`

**Interfaces:**
- Consumes: `du_an.duong_tieng` (đã có); `job_content.expire_content`.
- Produces: `lich_su_nd.khoi_bi_anh_huong(db, *, owner_id: str, job_id: str) -> list[dict]` — mỗi dict `{project_id, du_an, khoi_so}`; route `GET /ltt-voice/lich-su/{job_id}/anh-huong` trả JSON danh sách đó cho hộp xác nhận.

- [ ] **Step 1: Test hỏng (test_525)**

Fixture `khach` chép từ `test_519`. Helper `_job_xong(uid, *, co_khoi=False, khoa_cu=False) -> str` tạo một `Job` `done` với `params={"nguon": "studio", "text": "...", "preset": "Adam"}`, `result={"audio_key": ...}`, đặt tệp vào kho ở `.../{job_id}/tieng.wav` (hoặc `{job_id}.wav` khi `khoa_cu`), và nếu `co_khoi` tạo một `VoiceProject` + một `VoiceBlock` trỏ `job_id`/`audio_key` đó.

```python
def test_xoa_liet_ke_khoi_bi_anh_huong_TRUOC(khach):
    client, uid = khach
    jid = _job_xong(uid, co_khoi=True)
    r = client.get(f"/ltt-voice/lich-su/{jid}/anh-huong")
    assert r.status_code == 200 and len(r.json()["khoi"]) == 1


def test_xoa_that_su_xoa_tep_ke_ca_KHOA_CU(khach):
    client, uid = khach
    jid = _job_xong(uid, khoa_cu=True)
    r = client.post(f"/ltt-voice/lich-su/{jid}/xoa", data={"csrf_token": _csrf_ls(client)})
    assert r.status_code in (200, 303)
    from platform_core.storage import get_storage
    assert not get_storage().exists(f"voice/out/{jid}.wav")   # khoá cũ (đọc đúng mẫu khoá cũ trong jobs.py)


def test_khoi_mat_tep_hien_CAN_TAO_LAI_khong_hien_XONG(khach):
    client, uid = khach
    jid = _job_xong(uid, co_khoi=True)
    client.post(f"/ltt-voice/lich-su/{jid}/xoa", data={"csrf_token": _csrf_ls(client)})
    from apps.ltt_voice import du_an
    tt = _tom_tat_du_an_cua_job(uid, jid)       # helper gọi du_an.tom_tat
    # Mức KHỐI ở đây; mức DỰ ÁN (`trang_thai_suy`) là Task 9 — test_357.
    assert tt["khoi"][0]["trang_thai_hien"] == du_an.TT_CAN_TAO_LAI


def test_doc_lai_VAN_qua_cong_va_CO_dedupe(khach):
    import ast, inspect
    from apps.ltt_voice.routes import _p_lich_su
    src = inspect.getsource(_p_lich_su.doc_lai)
    goi = {getattr(n.func, "id", "") or getattr(n.func, "attr", "")
           for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)}
    assert {"chuan_hoa", "giai_giong"} <= goi       # SC-8: hotfix dc6d9c6b còn
    kw = {k.arg for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)
          and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) == "submit_with_credit"
          for k in n.keywords}
    assert "dedupe_key" in kw
```

Đọc mẫu khoá cũ thật trước khi viết assert thứ hai: `git show 0a07a49e --stat` và `git show 0a07a49e -- apps/ltt_voice/jobs.py | head -60`.

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_525_lich_su_xoa_trang_thai_suy.py -q` → FAIL.

- [ ] **Step 3: Hiện thực**

- Lấy các tệp Create/Modify từ ba commit nguồn (`git show <sha>:<path>` cho tệp mới; áp từng khối diff theo hành vi cho tệp đã có). Với `_p_lich_su.py`: mở bản trunk, **thêm** hai route của nhánh; không chép tệp nhánh.
- `xoa_luot`: sau `expire_content`, gọi thêm `storage.delete` cho khoá cũ `{job_id}.wav` theo mẫu thật (T-11), bỏ qua `FileNotFoundError`.
- `lich_su_nd.khoi_bi_anh_huong` + route `/anh-huong`; `voice.js`: nút Xoá gọi `/anh-huong` trước, hiện `confirm()` liệt kê "Khối N trong dự án X sẽ mất tiếng và cần tạo lại" (chuỗi qua `data-nhan-*` của template, không gõ tiếng Việt trong JS), rồi POST `/xoa`.
- `doc_lai`: thêm `dedupe_key=dedupe_key_for("ltt_voice.synthesize", {"owner": uid, "doc_lai": job_id})`.
- `du_an.TT_CAN_TAO_LAI = "can_tao_lai"` + trường `trang_thai_hien` của từng khối trong `tom_tat`: `xong` nhưng không có URL trong `duong_tieng` ⇒ `can_tao_lai` (hàm thuần `trang_thai_hien(khoi, co_tieng: bool) -> str`). Task 9 dùng hàm này cho badge dự án.

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_525_lich_su_xoa_trang_thai_suy.py tests/test_351_ltt_voice_lifecycle_authz.py -q` → PASS. Rồi, lệnh riêng: `python -m pytest tests/test_211*.py tests/test_155*.py -q` (hai nghĩa vụ nền tảng của bảng mới: xếp loại lưu trữ + ràng buộc UNIQUE trong drill) → PASS.

- [ ] **Step 5: Commit** — message `LTT Voice RC1: Lich su het han + xoa (noi truoc he qua) + da tai (D005)` · `Reconciled-from: 27baa1a8, 31878cc2, dca96e84` · `Dropped: _p_lich_su.py ban nhanh (mat hotfix dc6d9c6b, SC-8); down_revision f2c48b71e903 (SC-9)`.

---

### Task 9: Dự án — badge suy ra, `ma_loi`, chống nộp trùng khối (D005, T-10, T-15, T-06)

**Files:**
- Modify: `apps/ltt_voice/du_an.py` (`trang_thai_suy` từ `ca6a00ce`, dùng `trang_thai_hien` của Task 8; sửa docstring `xuat_mot_luot`, SC-15)
- Modify: `apps/ltt_voice/routes/_p_du_an.py` (list + poll dùng `trang_thai_suy`; mọi lỗi 400 kèm `ma_loi` theo khuôn `_loi_400`; `/doc` một khối: chặn khi khối `dang_tao`, truyền `dedupe_key`)
- Modify: `apps/ltt_voice/templates/ltt_voice_du_an.html` (badge; `aria-label` `t.ten → d.ten`)
- Create: `tests/test_357_ltt_voice_du_an_trang_thai.py`, `tests/test_358_ban_doc_dai_ranh_gioi.py` (từ `ca6a00ce` `test_351_…`/`test_398_…`, đổi số và tên)

**Interfaces:**
- Consumes: `du_an.trang_thai_hien`, `TT_CAN_TAO_LAI` (Task 8).
- Produces: `du_an.trang_thai_suy(tom_tat: dict) -> str` ∈ `{"trong", "dang_lam", "can_tao_lai", "loi", "xong"}` — `xong` chỉ khi mọi khối có tiếng phát được.

- [ ] **Step 1: Test hỏng** — thêm vào `test_357` (sau khi lấy từ `git show ca6a00ce:tests/test_351_ltt_voice_du_an_trang_thai.py`):

```python
def test_du_an_co_khoi_MAT_TEP_khong_bao_gio_XONG():
    from apps.ltt_voice import du_an
    tt = {"khoi": [{"trang_thai": "xong", "trang_thai_hien": "xong"},
                   {"trang_thai": "xong", "trang_thai_hien": du_an.TT_CAN_TAO_LAI}]}
    assert du_an.trang_thai_suy(tt) == du_an.TT_CAN_TAO_LAI


def test_moi_khoi_loi_thi_LOI():
    from apps.ltt_voice import du_an
    tt = {"khoi": [{"trang_thai": "loi", "trang_thai_hien": "loi"}] * 2}
    assert du_an.trang_thai_suy(tt) == "loi"


def test_cua_du_an_tra_MA_LOI_khi_lech_lan(khach):     # fixture từ test_519
    client, uid = khach
    pid = _tao_du_an(client, "Du an A")                  # helper POST /ltt-voice/du-an
    bid = _them_khoi(client, pid, "The quick brown fox jumps over the lazy dog that we know.")
    r = client.post(f"/ltt-voice/du-an/{pid}/khoi/{bid}/doc",
                    data={"preset": "Adam", "csrf_token": _csrf_da(client)},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400 and r.json()["ma_loi"] == "voice_language_mismatch"
```

Đọc tên route thật trước khi viết helper: `grep -n "@router" apps/ltt_voice/routes/_p_du_an.py`.

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_357_ltt_voice_du_an_trang_thai.py -q` → FAIL.

- [ ] **Step 3: Hiện thực** — theo Files. `trang_thai_suy`: không khối ⇒ `trong`; có khối `dang_tao` ⇒ `dang_lam`; có khối `can_tao_lai` ⇒ `can_tao_lai`; mọi khối `loi` ⇒ `loi`; mọi khối `xong` và `trang_thai_hien == "xong"` ⇒ `xong`; còn lại ⇒ `dang_lam`. Badge dịch qua `DICH` ("Cần tạo lại" → "Needs regenerating", "Lỗi" → "Failed").

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_357_ltt_voice_du_an_trang_thai.py tests/test_358_ban_doc_dai_ranh_gioi.py -q` → PASS; `python tools/check_so_test.py` → PASS.

- [ ] **Step 5: Commit** — message `LTT Voice RC1: Du an — badge suy tu tep that + ma_loi + chong nop trung khoi` · `Reconciled-from: ca6a00ce` · `Dropped: so test 351/398 (T-05)`.

---

### Task 10: Nghe thử + preview kho chung + bề mặt ASV (D006, T-08, T-09, T-13)

**Files:**
- Modify: `apps/ltt_voice/nghe_thu.py` (`khoa_chung`, `_dung_kho_chung`, `danh_sach_kho_chung` từ `65e099af` — dùng `dung(ngon_ngu=)` và `PHIEN_BAN` của trunk; kiểm `co_san` trước `nap_ref_b64`; thêm `duong_cho_app_khac` từ `891d93db`)
- Modify: `apps/ltt_voice/__init__.py` (`BE_MAT_CONG_KHAI` thêm `duong_cho_app_khac`)
- Modify: `apps/ltt_voice/routes/_p_audio.py` (`la_nghe_thu_chung`, từ `65e099af`)
- Modify: `apps/ltt_voice/tham_chieu.py`, `routes/_p_tao.py`, `routes/_p_giong.py`, `routes/_p_du_an.py` (tách `rieng=`/`chung=` khi dựng preview, từ `65e099af`)
- Modify: `apps/ltt_voice/routes/_p_nghe_thu.py` (gọi `lan_ngon_ngu.quyet_dinh`, trả `phan_quyet`)
- Modify: `server/static/voice.js`, `server/static/ltt.css`, `tools/gui/ltt.css` (loading/lỗi từ `3634412a`; nhãn phán quyết)
- Create: `tests/test_526_nghe_thu_phan_quyet.py`, `tests/test_528_kho_chung_nghe_thu.py`

**Interfaces:**
- Consumes: `quyet_dinh` (Task 3).
- Produces: `POST /ltt-voice/nghe-thu-van-ban` JSON thêm `"phan_quyet": {"cho_phep": bool, "ma_loi": str, "cau": str}`; `nghe_thu.duong_cho_trang(..., chung=...)` (tham số mới, mặc định rỗng — chữ ký cũ vẫn chạy); `nghe_thu.duong_cho_app_khac(owner_id, ma_mau, rieng)`.

- [ ] **Step 1: Test hỏng**

```python
# test_526
def test_nghe_thu_lech_lan_VAN_PHAT_va_NOI_RA(khach, monkeypatch):
    client, uid = khach
    from apps.ltt_voice import nghe_thu_cua_toi
    monkeypatch.setattr(nghe_thu_cua_toi, "sinh", lambda *a, **k: b"RIFF....WAVE")  # đọc tên hàm sinh thật trước
    r = client.post("/ltt-voice/nghe-thu-van-ban",
                    data={"text": "The quick brown fox jumps over the lazy dog that we know.",
                          "preset": "Adam", "csrf_token": _csrf(client)})
    assert r.status_code == 200
    pq = r.json()["phan_quyet"]
    assert pq["cho_phep"] is False and pq["ma_loi"] == "voice_language_mismatch" and pq["cau"]


def test_cua_nghe_thu_HOI_tham_quyen():
    import ast, inspect
    from apps.ltt_voice.routes import _p_nghe_thu
    src = inspect.getsource(_p_nghe_thu.nghe_thu_van_ban)
    goi = {getattr(n.func, "attr", "") or getattr(n.func, "id", "")
           for n in ast.walk(ast.parse(src.lstrip())) if isinstance(n, ast.Call)}
    assert "quyet_dinh" in goi
```

```python
# test_528 — lấy các ca kho chung của 65e099af trong test_384 (git show 65e099af -- tests/test_384_lan_ngon_ngu.py), đặt vào đây, cộng:
def test_nguoi_KHONG_phai_chu_nghe_duoc_preview_kho_chung(khach):
    client, uid = khach
    pid = _tao_giong_chung(ngon_ngu="en")                 # dung_chung=True, license_status="ok", owner khác
    _dat_preview_chung(pid)                               # put vào nghe_thu.khoa_chung(pid)
    trang = client.get("/ltt-voice").text
    import re
    m = re.search(rf'data-nghe="([^"]*{pid}[^"]*)"', trang)
    assert m, "the giong kho chung khong co nut nghe thu"
    assert client.get(m.group(1)).status_code == 200


def test_be_mat_cong_khai_giu_ca_hai_duong_cho_app_khac():
    # INV-BE-MAT-1: ASV (`apps/auto_scan_video/gia.py`) import hàm này trong try/except
    # — mất nó thì preview giọng của ASV biến mất IM LẶNG, không đỏ ở đâu cả.
    import apps.ltt_voice as V
    from apps.ltt_voice import nghe_thu
    for ten in ("duong_cho_trang", "duong_cho_app_khac"):
        assert ten in str(V.BE_MAT_CONG_KHAI), ten
        assert callable(getattr(nghe_thu, ten))


def test_bao_tri_KHONG_tai_ref_khi_preview_da_co(monkeypatch):
    from apps.ltt_voice import nghe_thu, tham_chieu
    goi = []
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda *a, **k: goi.append(1) or "QUJD")
    monkeypatch.setattr(nghe_thu, "co_san", lambda *a, **k: True)
    nghe_thu._dung_kho_chung(_ds_mot_giong_chung())      # helper dựng 1 mục
    assert goi == []
```

Đọc tên thuộc tính nút nghe thật trước khi viết regex (`grep -n "data-nghe\|data-src" apps/ltt_voice/templates/_voice_*.html`), và tên hàm sinh ở `nghe_thu_cua_toi.py`.

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_526_nghe_thu_phan_quyet.py tests/test_528_kho_chung_nghe_thu.py -q` → FAIL.

- [ ] **Step 3: Hiện thực** — theo Files. Trong `_p_nghe_thu.py`: `pq = lan_ngon_ngu.quyet_dinh(giong_mau.lan_cua(preset), text)` **sau** `giong_mau.hop_le` và trần ký tự, **trước** khi sinh; sinh vẫn chạy; trả `phan_quyet` với `cau = lan_ngon_ngu.cau_cho_khach(pq) if not pq.cho_phep else ""`. Cập nhật lý do miễn trừ của `test_356` cho `nghe_thu_van_ban`: thêm câu "Hỏi `quyet_dinh` để HIỆN (D006), không chặn". `voice.js`: sau khi phát, nếu `phan_quyet.cho_phep === false` hiện `<p class="lv-nghe-canh" role="status">` với `phan_quyet.cau` cạnh nút. Loading/lỗi: áp diff `3634412a` lên `voice.js`/`ltt.css`; thay hằng `NGHE_LOI_CHU` gõ tiếng Việt bằng `el.dataset.nhanLoi` đọc từ `data-nhan-loi="{{ _('Không phát được bản nghe thử') }}"` trên template; `python tools/dong_goi_gui.py`. **T-17:** trong `alembic/versions/20260908_1600_voice_license_va_curate.py` sửa docstring cho khớp hành vi — cổng kho chung (`tham_chieu._dieu_kien_kho_chung`) chỉ đọc `dung_chung` + `license_status`; bảng curation chỉ được `tools/soat_giong.py` đọc (chỉ sửa chú thích, không đổi `upgrade`/`downgrade`).

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_526_nghe_thu_phan_quyet.py tests/test_528_kho_chung_nghe_thu.py -q` → PASS; `python -m pytest tests/test_284*.py -q` → PASS.

- [ ] **Step 5: Commit** — message `LTT Voice RC1: preview kho chung + nghe thu noi ra phan quyet (D006, T-08, T-13)` · `Reconciled-from: 65e099af (khoa_chung, la_nghe_thu_chung, rieng/chung), 3634412a, 891d93db` · `Dropped: CAU_NGHE_THU_EN, PHIEN_BAN v3 (SC-6, SC-7)`.

---

### Task 11: Giao diện Studio theo làn (D002 UI, GUI MVP 10–14)

**Files:**
- Modify: `apps/ltt_voice/templates/ltt_voice_studio.html`, `_voice_chon.html`, `_voice_the.html`
- Modify: `server/static/voice.js`, `server/static/ltt.css`, `tools/gui/ltt.css`
- Modify: `tests/test_352_ltt_voice_tiep_can.py` (assertion của `65e099af`)
- Modify: `tests/test_384_lan_ngon_ngu.py` (chỉ các ca UI ẩn/đếm giọng chưa rõ làn của `65e099af`; **không** lấy `test_PHEP_DOAN_…`)

**Interfaces:**
- Consumes: trường `ngon_ngu`/`ngon_ngu_nguon` trên mọi mục giọng (Task 5), `NHAN_LAN`.
- Produces: không API mới.

- [ ] **Step 1: Test hỏng** — thêm vào `test_352`:

```python
def test_studio_giu_TU_DONG_va_o_ngon_ngu_dieu_khien_bo_loc(khach_studio):
    trang = khach_studio.get("/ltt-voice").text
    assert 'data-ngonngu="auto"' in trang            # D002: vẫn có "Tự động"
    assert "data-chon-lan" not in trang              # hàng "Mọi làn" riêng đã gỡ (65e099af)
    assert "Máy đọc được cả hai thứ tiếng" not in trang
    assert 'data-lan="vi"' not in trang.replace('data-lan="{{', '')  # không gõ cứng làn preset
```
(Dùng fixture đăng nhập sẵn có trong `test_352`; đọc tên fixture thật.)

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_352_ltt_voice_tiep_can.py -q` → FAIL.

- [ ] **Step 3: Hiện thực** — áp các khối UI của `git show 65e099af -- apps/ltt_voice/templates server/static/voice.js server/static/ltt.css` **trừ**: bỏ `auto` khỏi Studio (D002 giữ `auto`), `data-lan="vi"`/`nhan_lan['vi']` gõ cứng (dùng `g.ngon_ngu`), mọi đoạn `lyDoChan` dựa trên `xung_dot`. Hành vi: chọn VI/EN ⇒ bộ lọc giọng chỉ hiện làn đó và đếm giọng "Chưa rõ" bị ẩn (`capNhatDongLan`); đổi làn ⇒ bỏ chọn giọng không cùng làn; `auto` ⇒ hiện mọi giọng kèm huy hiệu làn; chip "Kho chung" cho giọng `chung`; nút Tạo khoá kèm lý do khi thiếu văn bản/giọng; bộ lọc vùng/phong cách trong `<details>`. CSS: chỉ +40 dòng thật (bỏ nhiễu CRLF — áp bằng Edit, không thay tệp). `python tools/dong_goi_gui.py`. Chuỗi mới vào `DICH`.

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_352_ltt_voice_tiep_can.py tests/test_384_lan_ngon_ngu.py -q` → PASS.

- [ ] **Step 5: Commit** — message `LTT Voice RC1: Studio loc giong theo o Ngon ngu, giu Tu dong (D002 UI)` · `Reconciled-from: 65e099af (UI 10-14, +40 dong CSS)` · `Dropped: bat khai VI/EN o Studio (D002), nhieu CRLF 615 dong`.

---

### Task 12: Public API — hook kiểm-trước (D007) (song song)

**Files:**
- Modify: `platform_core/registry.py` (`ToolSpec.kiem_truoc`, kiểm hình dạng trong validator cạnh `tuy_chon_dong`)
- Modify: `platform_core/public_api/catalog.py` (`PublicTool.kiem_truoc` + điền ở `:349`)
- Modify: `platform_core/public_api/invocation.py` (hàm `kiem_truoc`)
- Modify: `server/api/jobs.py` (gọi ở `create_quote` và `create_job`)
- Create: `apps/ltt_voice/kiem_truoc_api.py`
- Modify: `apps/ltt_voice/manifest.py` (tool `speech.ltt`: `kiem_truoc="apps.ltt_voice.kiem_truoc_api:kiem"`)
- Modify: `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md:39` (sửa mâu thuẫn với dòng 68; ghi D007)
- Create: `tests/test_524_public_api_kiem_truoc.py`

**Interfaces:**
- Produces: `invocation.kiem_truoc(db, tool, params: dict, *, user_id: str) -> None` — ném `errors.invalid_request(detail, reason=<ma>)`; `apps.ltt_voice.kiem_truoc_api.kiem(db, user_id: str, params: dict) -> None`.

- [ ] **Step 1: Test hỏng**

```python
"""D007 — hook kiểm-trước của Public API: lỗi nghiệp vụ ra 400 TRƯỚC khi có giá."""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


class _Tool:
    name = "speech.ltt"
    kiem_truoc = "apps.ltt_voice.kiem_truoc_api:kiem"


def test_tool_khong_khai_hook_thi_khong_doi_gi():
    from platform_core.public_api import invocation

    class T:
        name = "x.y"
    assert invocation.kiem_truoc(None, T(), {"a": 1}, user_id="u") is None


def test_lech_lan_ra_400_co_reason(monkeypatch):
    from platform_core.public_api import invocation
    from platform_core.public_api.errors import ApiError
    with pytest.raises(ApiError) as e:
        invocation.kiem_truoc(None, _Tool(), {
            "text": "The quick brown fox jumps over the lazy dog that we know.",
            "preset": "Adam"}, user_id="u")
    assert e.value.status == 400
    assert "voice_language_mismatch" in str(getattr(e.value, "extra", {}) or {})


def test_hop_le_thi_im_lang():
    from platform_core.public_api import invocation
    assert invocation.kiem_truoc(None, _Tool(), {
        "text": "Xin chào, hôm nay trời rất đẹp.", "preset": "Adam"}, user_id="u") is None


@pytest.mark.parametrize("ham", ["create_quote", "create_job"])
def test_route_goi_hook_TRUOC_khi_tinh_gia(ham):
    cay = ast.parse((GOC / "server" / "api" / "jobs.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == ham)
    thu_tu = [(n.lineno, n.func.attr) for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr in ("kiem_truoc", "price", "submit")]
    thu_tu.sort()
    ten = [t for _, t in thu_tu]
    assert "kiem_truoc" in ten and ten.index("kiem_truoc") < ten.index("price"), ten


def test_speech_ltt_KHAI_hook():
    from apps.ltt_voice.manifest import MANIFEST
    spec = next(t for t in MANIFEST.tools if t.job_type == "ltt_voice.synthesize")
    assert spec.kiem_truoc == "apps.ltt_voice.kiem_truoc_api:kiem"
```

Đọc tên thuộc tính trạng thái của `ApiError` (`status`? `status_code`?) và `extra` trong `platform_core/public_api/errors.py:175-205` rồi sửa hai assert cho đúng tên.

- [ ] **Step 2: Chạy, xác nhận hỏng** — `python -m pytest tests/test_524_public_api_kiem_truoc.py -q` → FAIL.

- [ ] **Step 3: Hiện thực**

`registry.py` — sau `sync_executor`:
```python
    # Kiểm NGHIỆP VỤ trước khi có giá và trước khi giữ tiền (D007, RC1 2026-09-11).
    #
    #   kiem_truoc="apps.myapp.kiem:kiem"   # (db, user_id, params) -> None
    #
    # Ném `jobs.LoiNguoiGoi` (có `ma` thì càng tốt) ⇒ `/api/v1` trả 400 với
    # `reason=<ma>` trước khi quote/hold. Rỗng ⇒ không đổi gì. Cùng khuôn tham
    # chiếu dotted của `sync_executor`: nền tảng resolve lúc cần, không import app.
    kiem_truoc: str = ""
```
và trong validator (cạnh khối `tuy_chon_dong`): nếu `tool.kiem_truoc` khác rỗng và không khớp `_THAM_CHIEU_RE` ⇒ `RegistryError`.

`catalog.py`: `kiem_truoc: str = ""` trên `PublicTool` (nhóm "Operational only", không vào `to_public_dict`); điền `kiem_truoc=str(getattr(tool, "kiem_truoc", "") or "")`.

`invocation.py`:
```python
def kiem_truoc(db, tool, params: dict, *, user_id: str) -> None:
    """Run the app's business pre-check, if it declared one (D007).

    Placed after shape validation and before any price exists: a request the
    app can already refuse must never hold credit, queue, or reach a worker.
    """
    ref = str(getattr(tool, "kiem_truoc", "") or "")
    if not ref:
        return None
    from platform_core.jobs import LoiNguoiGoi
    from platform_core.registry import tai_tham_chieu

    try:
        tai_tham_chieu(ref)(db, str(user_id), dict(params))
    except LoiNguoiGoi as exc:
        raise invalid_request(str(exc), reason=str(getattr(exc, "ma", "") or "")) from exc
    return None
```

`server/api/jobs.py`: trong `create_quote` ngay sau `params = invocation.apply_server_measurements(...)` và trong `create_job` ngay sau dòng tương ứng — `invocation.kiem_truoc(db, tool, params, user_id=principal.user_id)`.

`apps/ltt_voice/kiem_truoc_api.py`:
```python
"""Public API pre-check cho `speech.ltt` (D007): cùng cổng với Studio."""
from __future__ import annotations

from . import features


def kiem(db, user_id: str, params: dict) -> None:
    yc = features.chuan_hoa(dict(params, owner_id=user_id))
    features.giai_giong(db, yc)
```
Nếu `giai_giong` cần `db` thật mà `db` là `None` (test không có giọng nhân bản — chỉ preset), nhánh preset không chạm `db`; ca `voice_id` cần db thật — thêm một test tích hợp dùng fixture SQLite của `test_519` cho `voice_id` người khác ⇒ 400.

- [ ] **Step 4: Xanh** — `python -m pytest tests/test_524_public_api_kiem_truoc.py tests/test_338_ltt_voice_hop_dong.py -q` → PASS.

- [ ] **Step 5: Commit** (git add tường minh từng tệp) — tệp theo Files. Message `Public API: hook kiem_truoc tuy chon trong ToolSpec — speech.ltt tu choi truoc khi giu tien (D007)` · thân nêu lý do luật 20.

---

### Task 13: Bánh cóc cửa tiêu tiền (INV-TIEN-1, INV-TIEN-2, INV-LAN-3)

**Files:**
- Modify: `tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py`

**Interfaces:**
- Consumes: mọi task trước (các cửa đã có `dedupe_key`, nghe thử hỏi `quyet_dinh`).

- [ ] **Step 1: Thêm phép kiểm (sẽ hỏng nếu còn cửa quên)**

```python
#: Cửa được miễn `dedupe_key`, kèm lý do. Khoá `(tệp, hàm)`.
MIEN_TRU_DEDUPE = {
    ("routes/_p_phat_dan.py", "phat_dan"): (
        "Phat dan giu `admission.acquire` suot generator va `giu_cho` theo phien; "
        "mot khach khong mo duoc hai luong tren cung mot suat — suat la khoa."),
}


def test_moi_submit_with_credit_deu_truyen_DEDUPE_KEY():
    sai = []
    for tep in APP.rglob("*.py"):
        if "__pycache__" in tep.parts:
            continue
        for fn in _cac_ham(tep):
            khoa = (tep.relative_to(APP).as_posix(), fn.name)
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call)
                        and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) == "submit_with_credit"
                        and "dedupe_key" not in {k.arg for k in n.keywords}
                        and khoa not in MIEN_TRU_DEDUPE):
                    sai.append(f"{khoa} dong {n.lineno}")
    assert not sai, f"cua tieu tien khong chong nop trung: {sai}"


def test_moi_MIEN_TRU_DEDUPE_tro_toi_ham_co_that():
    for (tep, ham) in MIEN_TRU_DEDUPE:
        assert any(f.name == ham for f in _cac_ham(APP / tep)), (tep, ham)
```

(Phép kiểm "cửa nghe thử hỏi `quyet_dinh`" đã có ở `test_526` — Task 10; không lặp ở đây.)

- [ ] **Step 2: Chạy** — `python -m pytest tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py -q`. Cửa nào còn thiếu `dedupe_key` (ví dụ `_p_du_an.py::_nop_mot_khoi`): thêm `dedupe_key=dedupe_key_for("ltt_voice.synthesize", {"owner": uid, "khoi": block_id})` ở cửa ấy, rồi chạy lại tới PASS. Nếu `phat_dan` gọi `giu_cho` chứ không gọi `submit_with_credit`, xoá mục miễn trừ tương ứng và `test_moi_MIEN_TRU_DEDUPE_tro_toi_ham_co_that` phải vẫn xanh với dict rỗng — khi đó giữ dict rỗng.

- [ ] **Step 3: Commit** — message `LTT Voice RC1: banh coc cua tieu tien doi dedupe_key va nghe thu hoi tham quyen`.

---

### Task 14: Nghiệm thu deploy so cả tệp không `.py` (spec §10.3) (song song)

**Files:**
- Modify: `tools/nghiem_thu_deploy.py` (`_trong_commit`/tên thật của hàm đọc `ls-tree` ở dòng ~68-90; vòng so ở ~142)
- Create: `tests/test_529_nghiem_thu_deploy_moi_tep.py`

- [ ] **Step 1: Test hỏng** — tách hai phép thuần có thể test: `bam_git(b: bytes) -> str` (sha1 blob git) và `so_sanh(trong_commit: dict[str,str], tren_may: dict[str,bytes]) -> dict` trả `{"lech": [...], "thieu": [...], "thua": [...]}`:

```python
import hashlib, importlib.util, pathlib
GOC = pathlib.Path(__file__).resolve().parents[1]


def _m():
    s = importlib.util.spec_from_file_location("ntd", GOC / "tools" / "nghiem_thu_deploy.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_bam_git_khop_git():
    assert _m().bam_git(b"abc\n") == hashlib.sha1(b"blob 4\0abc\n").hexdigest()


def test_so_ca_JS_va_TEMPLATE():
    m = _m()
    tc = {"server/static/voice.js": m.bam_git(b"a"), "apps/x/t.html": m.bam_git(b"b")}
    ra = m.so_sanh(tc, {"server/static/voice.js": b"KHAC", "apps/x/t.html": b"b",
                        "apps/x/moi.css": b"c"})
    assert ra["lech"] == ["server/static/voice.js"]
    assert ra["thua"] == ["apps/x/moi.css"] and ra["thieu"] == []
```

- [ ] **Step 2: Chạy, hỏng** — `python -m pytest tests/test_529_nghiem_thu_deploy_moi_tep.py -q`.

- [ ] **Step 3: Hiện thực** — bỏ lọc `.endswith(".py")` khi đọc `ls-tree` (giữ mọi blob trong `GOI`); thu thập tệp trên máy bằng `rglob("*")` bỏ `__pycache__` và `.pyc`; so bằng `bam_git`; in thêm dòng `tep khong .py trong commit : N`; giữ nguyên dòng kết luận `DAT …`/mã thoát. Cập nhật docstring đầu tệp (một đoạn "RC1 11/09: so moi tep, khong chi .py — mot deploy lech JS truoc day tra DAT").

- [ ] **Step 4: Xanh** — test PASS; chạy thật `python tools/nghiem_thu_deploy.py` (chỉ đọc, so production với `4a894036`) → vẫn `DAT`, lệch 0.

- [ ] **Step 5: Commit** (git add tường minh từng tệp) — message `nghiem_thu_deploy: so moi tep trong GOI, khong chi .py (lo do phat hien o RC1)`.

---

### Task 15: Bộ Playwright vĩnh viễn cho Voice (§9)

**Files:**
- Modify: `tests/browser/ltt_voice_golden.js`, `ltt_voice_negative.js`, `ltt_voice_smoke.js` (từ Task 2)
- Create: `tests/browser/ltt_voice_rc1.js` — các luồng RC1: khai lệch làn bị chặn có `ma_loi` (D002), ghi danh không khai bị chặn (D003), khai làn trên thẻ (D004), xoá lịch sử hiện hộp xác nhận nêu khối (D005), nghe thử lệch làn hiện nhãn (D006), preview kho chung phát được (T-08)
- Create: `tests/browser/ltt_voice_that.js` — một luồng VI + một luồng EN qua sidecar **thật** (chỉ chạy khi có biến `LTT_VOICE_SIDECAR_TOKEN`)
- Modify: `tools/check_voice_qa.py` (ghim hai tệp mới: có `throw`, chỉ nhắm `127.0.0.1:8129` hoặc `LTT_QA_BASE_URL` công khai khi `--tang2`, bắt `console.error`/`pageerror`/`requestfailed`/HTTP ≥ 400, lặp 6 khung hình)

- [ ] **Step 1:** Mở `tests/browser/ltt_voice_golden.js` (khuôn chạy bằng `playwright-cli`/Playwright hiện có). Viết `ltt_voice_rc1.js` cùng khuôn: một hàm `kiemTrang(page)` gắn `page.on('console')`, `page.on('pageerror')`, `page.on('requestfailed')`, `page.on('response')` (ghi mọi status ≥ 400 không nằm trong danh sách mong đợi của từng bước); lặp `for (const [w,h] of [[1280,720],[1366,768],[1440,900],[1920,1080],[390,844],[768,1024]])` qua luồng Studio chính; kiểm `document.documentElement.scrollWidth <= innerWidth` (không tràn ngang). Mỗi luồng RC1 ở trên là một khối có `throw new Error(...)` khi sai.
- [ ] **Step 2:** Thêm ràng buộc vào `check_voice_qa.py` (danh sách tệp ghim + 6 khung hình + 4 loại bắt lỗi); `python tools/check_voice_qa.py` → xanh.
- [ ] **Step 3:** Commit — message `LTT Voice RC1: bo Playwright vinh vien — 6 luong RC1, 6 khung hinh, 4 loai bat loi`.

---

### Task 16: Đồng bộ trunk + cổng đầy đủ + Tầng 1 (D009)

**Files:**
- Modify: `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json` (`rc_sha` cho mọi dòng; mục `tang1`)
- Create: `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` (báo cáo nghiệm thu + bảng chấm)
- Modify: `docs/NHAT_KY.md`, `docs/_luutru/PROJECT_MEMORY.md`

- [ ] **Step 1: Đối soát** — `python tools/doi_soat_voice.py` → PASS (commit mới của phiên khác chạm vùng ⇒ thêm dòng/yêu cầu theo D008 trước khi đi tiếp).
- [ ] **Step 2: Đồng bộ trunk** — `git fetch -q origin && git log --oneline HEAD..admin-mvp-v3 | head`. Có commit mới ⇒ `git merge --no-ff admin-mvp-v3` vào RC (không rebase), đo `git diff --stat HEAD~1 HEAD -- platform_core server apps/ltt_voice` và giải xung đột theo hành vi; kiểm migration một head.
- [ ] **Step 3: Cửa sổ yên** — `python tools/cua_so_yen.py trang-thai` + xem cây tiến trình (không có `pytest`/`gate`/`demucs`/`whisper` của phiên khác). Có ⇒ chờ (vòng kiểm lại, fail-closed). Kiểm `tools/gate.py` có `loi_cho_bo_test` (`grep -n loi_cho_bo_test tools/gate.py`).
- [ ] **Step 4: Cổng đầy đủ** — `python tools/gate.py` (một lượt, đúng hợp đồng §4/§7). Không sửa tệp nào khi gate đang chạy. Đỏ ⇒ đọc tệp ra đầy đủ của gate (không chỉ stdout), sửa gốc, lặp lại từ Step 3.
- [ ] **Step 5: E2E mock + Chrome thật** — dựng `tools/voice_mock_sidecar.py` + `tools/voice_e2e_server.py` (cổng 8129/8131); `python tools/voice_e2e_check.py`; chạy các tệp `tests/browser/ltt_voice_*.js` bằng Playwright Chrome (`channel: "chrome"`); ghi kết quả từng luồng × khung hình.
- [ ] **Step 6: Tổng hợp thật VI/EN** — xin/nhận quyền đọc `LTT_VOICE_SIDECAR_TOKEN`; ghi danh một clip tiếng Anh trên CSDL dev; chạy `tests/browser/ltt_voice_that.js` (VI qua preset, EN qua giọng vừa ghi danh). Không có quyền ⇒ `BLOCKED` ⇒ **NOT READY**.
- [ ] **Step 7: Di trú chạy khô** — áp hai migration lên bản sao CSDL của restore-drill (`tools/restore_drill_schema.py` / quy trình drill sẵn có), chạy `python tools/di_tru_lan_asr.py` (khô) trên bản sao; ghi số `xet/se_doi/khong_chac`.
- [ ] **Step 8: Chấm điểm + báo cáo** — `TANG1_RC1.md`: SHA đỉnh RC, kết quả từng bước, ma trận §8.2 (PASS/FAIL/BLOCKED từng ô), bảng 100 điểm (BLOCKED = 0), kết luận `READY_FOR_DEPLOYMENT` hoặc `NOT READY` + danh sách chặn. Điền `rc_sha` vào sổ cái. Cập nhật `NHAT_KY.md` + `PROJECT_MEMORY.md`.
- [ ] **Step 9: Commit** — tệp theo Files. Message `LTT Voice RC1: Tang 1 — <READY_FOR_DEPLOYMENT|NOT READY> tai <sha>`.
- [ ] **Step 10: Không ff, không deploy** — báo chủ dự án. ff vào `admin-mvp-v3` + deploy chỉ khi được lệnh (Tầng 2, spec §10.2).
