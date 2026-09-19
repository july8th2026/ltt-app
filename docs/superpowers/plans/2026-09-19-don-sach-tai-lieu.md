# Dọn sạch tài liệu toàn hệ thống — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mọi tài liệu mà phiên Claude/agent đọc (CLAUDE.md, AGENTS.md, memory, `docs/`, tệp quy tắc) chỉ còn nói ĐÚNG hệ thống đang chạy; cái cũ được lưu trữ có dấu, không nằm lẫn với luật.

**Architecture:** Phân loại mỗi tài liệu thành 4 loại (LUẬT · TRA CỨU · TRẠNG THÁI · LỊCH SỬ) → máy quét tìm tham chiếu chết + thuật ngữ đã bị thay → làn song song theo cụm thư mục sửa/lưu trữ → điều phối gộp → quét lại = 0. Không sửa mã vận hành; không xoá lịch sử (chỉ chuyển `_luutru/` + dấu).

**Tech Stack:** Markdown, git (`git mv`), Python stdlib cho máy quét, agent Sonnet theo `QUY_TAC_AGENT_VA_TOKEN.md`.

**Spec:** yêu cầu chủ dự án 19/09 tối (hội thoại) — "làm sạch tài liệu, commit cũ của cơ chế không còn dùng, không đúng code hiện tại; chỉ tài liệu + memory + CLAUDE.md, không sửa code; áp cho full hệ thống LTTSTUDIOSAPP; xử lý một lần cho sạch". Tiền lệ: `docs/system_purification/` (02/09, nay chính nó đã cũ — nhánh `admin-mvp-v3`, `master`).

## Global Constraints

- ⛔ Không sửa mã vận hành (`apps/`, `platform_core/`, `server/`, `render_gateway/`, `nexus_agent/`, `desktop/`, `plugins/`, `setup/`, cấu hình chạy). Ngoại lệ duy nhất: thêm `tools/quet_tai_lieu.py` (chỉ đọc, KHÔNG nối vào gate).
- ⛔ Không xoá tài liệu lịch sử — `git mv` sang `docs/_luutru/<năm-tháng>/…` + dòng dấu đầu tệp. Chỉ xoá hẳn: tệp rỗng, bản trùng byte-y-hệt, tệp sinh tự động có nguồn sinh lại được.
- ⛔ Không viết lại lịch sử git (không rebase/force-push/xoá commit). "Commit cũ" = nhánh + worktree đã gộp/bỏ → dọn nhánh/worktree, không đụng commit.
- ⛔ Không đụng dòng `??` / tệp chưa commit của phiên khác; `git add` tường minh; tệp cấu hình UTF-8 không BOM.
- ⛔ `D:\BOT GEMINI` chỉ đọc; memory của dự án khác ngoài LTTSTUDIOSAPP/LTTCODEAPP không đụng.
- Luật gate: tài liệu thuần ⇒ hook pre-commit + gate L1 (`gate.py --doi`) trước khi gộp `main`; KHÔNG L3; KHÔNG cần deploy (deploy chép cả cây — tài liệu đi theo lần deploy kế).
- LTTCODEAPP: chỉ làm SAU khi `phien/v2` (Pha C, 0.2.0) gộp `main` — tránh xung đột `docs/LTTCODE/reports/…`.
- Agent: Sonnet, mỗi làn một worktree + nhánh `phien/don-tl-<làn>`, báo cáo ≤ 250 từ, chờ ở tiền cảnh (`C:\Users\Thang Tuong\.claude\ltt\QUY_TAC_AGENT_VA_TOKEN.md`).

## Logic bổ sung (điều làm cho lần dọn này "sạch một lần" và không bẩn lại)

1. **Bốn loại, mỗi loại một số phận**
   | Loại | Là gì | Số phận |
   |---|---|---|
   | LUẬT | quy tắc còn hiệu lực | giữ ở ĐÚNG MỘT tệp chủ (bảng chủ đề của hợp đồng `docs/00_LTT_OPERATING_CONTRACT.md`); nơi khác chỉ trỏ |
   | TRA CỨU | mô tả hệ thống bền (kiến trúc, API, runbook) | giữ; mọi đường dẫn/lệnh trong đó phải tồn tại (máy quét) |
   | TRẠNG THÁI | "đang chạy gì, % bao nhiêu" | KHÔNG chép tay vào luật/tra cứu; chỉ ở tổng plan / STATE / lệnh sinh (`api_prod_canary.py trang-thai`) |
   | LỊCH SỬ | báo cáo, plan đã đóng, nhật ký | chuyển `_luutru/` + dấu; `NHAT_KY.md` giữ nguyên (nhật ký sống) |
2. **Máy làm trước, người sau:** tham chiếu chết (tệp/lệnh/công cụ không còn) và thuật ngữ bị thay được quét cơ học; agent chỉ phán những gì máy không phán được.
3. **Từ điển "đã bị thay"** (một nơi, `docs/_luutru/TU_DIEN_DA_THAY.md`) — mỗi dòng: cụm cũ → sự thật mới → nguồn. Máy quét dùng nó; về sau thêm dòng khi đổi cơ chế ⇒ tài liệu cũ bị bắt ngay.
4. **Dấu lưu trữ** đầu mỗi tệp chuyển đi: `> LƯU TRỮ <ngày> — không còn đúng hệ thống hiện tại; thay bằng: <tệp>. Chỉ đọc để hiểu lịch sử.`
5. **Không bẩn lại:** mỗi thư mục cấp 1 của `docs/` có `README.md` 5–15 dòng (trạng thái thư mục + tệp chủ); CLAUDE.md chỉ LUẬT + con trỏ; memory: luật hiện hành chỉ ở CLAUDE.md, memory ghi LÝ DO/lịch sử + trỏ.

## Quy mô đo 19/09 tối

`docs/` 1 119 tệp .md (lớn nhất: `developer_portal_mvp_ui` 504 · `APP_AUDIT` 406 · `ltt_llm_dual` 229 · `_luutru` 134 · `LTT_VOICE` 90 · `VIDEO_AI_V2` 69 · `lttstudios-website` 69 · gốc 63) · memory LTTSTUDIOSAPP 51 + LTTCODEAPP 4 · LTTSTUDIOSAPP 80 nhánh (75 đã gộp `main`) + 18 worktree · LTTCODEAPP 108 .md + 34 nhánh + 30 worktree.

---

### Task 1: Máy quét tài liệu + từ điển đã bị thay

**Files:**
- Create: `tools/quet_tai_lieu.py`
- Create: `docs/_luutru/TU_DIEN_DA_THAY.md`
- Test: `tests/test_quet_tai_lieu.py`

**Interfaces:**
- Produces: `python tools/quet_tai_lieu.py <thư-mục|tệp>... [--json out.json]` → in từng dòng `CHET|THAY <tệp>:<dòng> <mẩu> -> <gợi ý>`; mã thoát 0 luôn (công cụ báo cáo, không phải gate). JSON: `[{"loai","tep","dong","mau","goi_y"}]`.

- [ ] **Step 1: Viết test hỏng**

```python
# tests/test_quet_tai_lieu.py
import json, subprocess, sys
from pathlib import Path

def chay(tmp_path, noi_dung, tu_dien):
    (tmp_path / "docs").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "co_that.py").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text(noi_dung, encoding="utf-8")
    (tmp_path / "tu_dien.md").write_text(tu_dien, encoding="utf-8")
    out = tmp_path / "o.json"
    subprocess.run([sys.executable, str(Path("tools/quet_tai_lieu.py").resolve()), "docs",
                    "--goc", str(tmp_path), "--tu-dien", str(tmp_path / "tu_dien.md"),
                    "--json", str(out)], check=True, cwd=tmp_path)
    return json.loads(out.read_text(encoding="utf-8"))

def test_bat_tham_chieu_chet_va_bo_qua_tham_chieu_song(tmp_path):
    kq = chay(tmp_path, "chạy `tools/co_that.py` rồi `tools/da_xoa.py`\n", "")
    assert [r["mau"] for r in kq if r["loai"] == "CHET"] == ["tools/da_xoa.py"]

def test_bat_thuat_ngu_da_bi_thay(tmp_path):
    tu_dien = "| cũ | mới | nguồn |\n|---|---|---|\n| canonical integrator | chính phiên tự gộp main | hợp đồng §6 |\n"
    kq = chay(tmp_path, "chờ canonical integrator duyệt\n", tu_dien)
    assert kq[0]["loai"] == "THAY" and kq[0]["goi_y"] == "chính phiên tự gộp main"
```

- [ ] **Step 2: Chạy, thấy hỏng** — `python -m pytest tests/test_quet_tai_lieu.py -q` → FAIL (không có tệp công cụ).

- [ ] **Step 3: Viết công cụ tối thiểu**

```python
# tools/quet_tai_lieu.py
"""Quét tài liệu: tham chiếu chết (tệp/lệnh trong `…` không tồn tại) + thuật ngữ đã bị thay.
Chỉ đọc. Không nối vào gate. Dùng: python tools/quet_tai_lieu.py docs CLAUDE.md --json out.json"""
import argparse, json, re
from pathlib import Path

DUONG = re.compile(r"`([A-Za-z0-9_.\-]+(?:[/\\][A-Za-z0-9_.\-]+)+\.(?:py|ps1|md|mjs|js|ts|rs|json|yml|yaml|toml|bat))`")

def doc_tu_dien(p):
    cap = []
    if p and Path(p).exists():
        for dong in Path(p).read_text(encoding="utf-8").splitlines():
            o = [x.strip() for x in dong.strip().strip("|").split("|")]
            if len(o) >= 2 and o[0] and o[0] not in ("cũ",) and not set(o[0]) <= set("-: "):
                cap.append((o[0], o[1]))
    return cap

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dich", nargs="+")
    ap.add_argument("--goc", default=".")
    ap.add_argument("--tu-dien", default="docs/_luutru/TU_DIEN_DA_THAY.md")
    ap.add_argument("--json")
    a = ap.parse_args()
    goc = Path(a.goc).resolve()
    tu_dien = doc_tu_dien(a.tu_dien if Path(a.tu_dien).is_absolute() else goc / a.tu_dien)
    tep = []
    for d in a.dich:
        p = goc / d
        tep += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    kq = []
    for f in tep:
        if "_luutru" in f.parts:
            continue
        for i, dong in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in DUONG.finditer(dong):
                rel = m.group(1).replace("\\", "/")
                if not (goc / rel).exists():
                    kq.append({"loai": "CHET", "tep": str(f.relative_to(goc)), "dong": i, "mau": rel, "goi_y": ""})
            for cu, moi in tu_dien:
                if cu.lower() in dong.lower():
                    kq.append({"loai": "THAY", "tep": str(f.relative_to(goc)), "dong": i, "mau": cu, "goi_y": moi})
    for r in kq:
        print(f'{r["loai"]} {r["tep"]}:{r["dong"]} {r["mau"]} -> {r["goi_y"]}')
    if a.json:
        Path(a.json).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test xanh** — `python -m pytest tests/test_quet_tai_lieu.py -q` → 2 passed.

- [ ] **Step 5: Viết từ điển khởi đầu** `docs/_luutru/TU_DIEN_DA_THAY.md` (bảng `| cũ | mới | nguồn |`), tối thiểu các dòng đã biết 19/09:

| cũ | mới | nguồn |
|---|---|---|
| canonical integrator | chính phiên tự gộp main | hợp đồng §6 |
| gate.py --doi là vòng lặp | trong phiên: test nhắm; L1/L2 khi cần; L3 một lần tổng kết | hợp đồng §4 |
| bốn bước trước lệnh nặng | hai lệnh: cua_so_yen trang-thai + tai_may | hợp đồng §4.8 |
| tối đa 3 agent | số làn = số việc độc lập | CLAUDE.md toàn cục ⭐ Chạy agent |
| chay_nang.py (khoá `cpu_nhieu`) | chay_nang.py giữ khoá `cpu_agent` | CLAUDE.md toàn cục |
| eval máy B phải khoá eval_may_b | máy B mặc định không khoá; eval_may_b chỉ đo độ trễ | CLAUDE.md toàn cục |
| admin-mvp-v3 | main | git |
| purification-v1 | main | git |
| ltt-3.8 mặc định xhigh | ltt-3.8 mặc định medium (L-33) | DECISION_LOG L-33 |

- [ ] **Step 6: Commit** — `git add tools/quet_tai_lieu.py tests/test_quet_tai_lieu.py docs/_luutru/TU_DIEN_DA_THAY.md` → `git commit -m "tools: quet_tai_lieu (tham chieu chet + thuat ngu da thay), tu dien dau tien"`.

### Task 2: Kiểm kê + phân loại (một bảng cho cả hệ thống)

**Files:**
- Create: `docs/_luutru/KIEM_KE_TAI_LIEU_2026-09-19.md`

**Interfaces:**
- Consumes: `tools/quet_tai_lieu.py` (Task 1).
- Produces: bảng `| tệp/thư mục | loại (LUẬT/TRA CỨU/TRẠNG THÁI/LỊCH SỬ) | còn đúng? | hành động (giữ/sửa/lưu trữ/xoá-trùng) | làn |` — các làn Task 3–5 đọc đúng các dòng của làn mình.

- [ ] **Step 1:** chạy `python tools/quet_tai_lieu.py docs CLAUDE.md AGENTS.md --json %TEMP%\quet.json` → đếm CHET/THAY theo thư mục cấp 1.
- [ ] **Step 2:** theo thư mục cấp 1, xác định loại bằng: `git log -1 --format=%ad` (ngày sửa cuối), có tệp chủ trong bảng hợp đồng không, có được CLAUDE.md/AGENTS.md/hợp đồng trỏ tới không (`grep`), số CHET/THAY. Thư mục không ai trỏ + sửa cuối > 10 ngày + thuộc chương trình đã đóng ⇒ LỊCH SỬ.
- [ ] **Step 3:** chia làn theo cụm (không làn nào chung tệp): L-A `docs/` gốc + hợp đồng + CLAUDE.md + AGENTS.md + `02_LENH_CHO_CLAUDE.md`; L-B `ltt_llm_dual/`, `audit_ltt_llm/`, `VLM_NOI_BO/`, `PUBLIC_API/`; L-C `APP_AUDIT/`, `developer_portal_mvp_ui/`, `UI_REDESIGN/`, `lttstudios-website/`; L-D app: `LTT_VOICE/`, `VIDEO_AI_V2/`, `CHATLTT*/`, `auto_scan_video*/`, `VPS_V4/`, `multijob/`, `admin_mvp_v3/`, `MVP_OPTIMIZATION_V2/`; L-E `superpowers/plans`, `system_purification/`, `migration/`, `architecture/`, phần còn lại.
- [ ] **Step 4:** commit bảng kiểm kê.

### Task 3: Làn tài liệu dự án (chạy song song L-A…L-E, mỗi làn một agent Sonnet)

**Files (mỗi làn chỉ trong cụm của mình):** sửa `.md` trong cụm; `git mv` sang `docs/_luutru/2026-09/<đường-cũ>`; tạo/sửa `docs/<thư-mục>/README.md`.

**Interfaces:**
- Consumes: dòng của làn trong `KIEM_KE_TAI_LIEU_2026-09-19.md`; từ điển Task 1.
- Produces: nhánh `phien/don-tl-<làn>`; mỗi CHET/THAY trong cụm → sửa đúng, hoặc lưu trữ, hoặc ghi ngoại lệ có lý do vào `docs/_luutru/NGOAI_LE_QUET.md`.

- [ ] **Step 1:** worktree riêng từ `main`; đọc dòng kiểm kê của làn.
- [ ] **Step 2:** LỊCH SỬ ⇒ `git mv` + dòng dấu lưu trữ (Logic bổ sung 4); sửa mọi con trỏ tới tệp đã chuyển (`git grep -l <tên>`).
- [ ] **Step 3:** TRA CỨU ⇒ sửa từng CHET/THAY theo SỰ THẬT MÃ HIỆN TẠI (grep `apps/`, `platform_core/`, `tools/` — chỉ đọc); không chắc ⇒ ghi ngoại lệ, không đoán.
- [ ] **Step 4:** TRẠNG THÁI chép tay trong LUẬT/TRA CỨU ⇒ thay bằng con trỏ tới nguồn sinh (tổng plan / `api_prod_canary.py trang-thai`).
- [ ] **Step 5:** `README.md` thư mục (5–15 dòng: loại, tệp chủ, trạng thái).
- [ ] **Step 6:** quét lại cụm: `python tools/quet_tai_lieu.py docs/<cụm>` → 0 dòng ngoài ngoại lệ.
- [ ] **Step 7:** commit từng nhóm nhỏ (`git add` tường minh); báo cáo ≤ 250 từ: số tệp giữ/sửa/lưu trữ/xoá-trùng, ngoại lệ.

### Task 4: CLAUDE.md + AGENTS.md + hợp đồng — một nguồn cho mỗi luật (làn L-A làm, điều phối duyệt)

**Files:** `CLAUDE.md`, `AGENTS.md`, `docs/00_LTT_OPERATING_CONTRACT.md`, `docs/02_LENH_CHO_CLAUDE.md`, `C:\Users\Thang Tuong\.claude\CLAUDE.md`, `C:\Users\Thang Tuong\.claude\ltt\QUY_TAC_AGENT_VA_TOKEN.md`.

- [ ] **Step 1:** lập bảng "luật → nơi định nghĩa" cho mọi luật xuất hiện ở ≥ 2 tệp (grep các cụm then chốt: gate/L3, khoá CPU, `-n`, deploy, `??`, BOM, bí mật).
- [ ] **Step 2:** mỗi luật giữ định nghĩa ở ĐÚNG tệp chủ theo bảng của hợp đồng; nơi khác thay bằng một dòng trỏ. CLAUDE.md dự án: chỉ bản đồ + luật chết người (như hiện nay) — rà câu nào là TRẠNG THÁI ⇒ bỏ.
- [ ] **Step 3:** `docs/02_LENH_CHO_CLAUDE.md` — xác định còn ai trỏ; hết hiệu lực ⇒ lưu trữ.
- [ ] **Step 4:** skill `writing-for-agents` áp khi viết (cắt no-op, một nguồn chân lý). Quét lại 0 THAY.

### Task 5: Memory (LTTSTUDIOSAPP + LTTCODEAPP) — dùng skill `anthropic-skills:consolidate-memory`

**Files:** `C:\Users\Thang Tuong\.claude\projects\D--LTTSTUDIOSAPP\memory\*.md`, `…\D--LTTCODEAPP\memory\*.md`, hai `MEMORY.md`.

- [ ] **Step 1:** mỗi memory: fact còn đúng không (kiểm tệp/cờ/lệnh nó nêu còn tồn tại — máy quét chạy được trên thư mục memory với `--goc D:\LTTSTUDIOSAPP`).
- [ ] **Step 2:** sai ⇒ sửa hoặc xoá; trùng ⇒ gộp (giữ `name`, sửa `[[liên kết]]`); memory ghi LUẬT hiện hành ⇒ đổi thành LÝ DO + trỏ CLAUDE.md (mẫu: `agent-song-song-phai-xep-hang-khoa-may.md`).
- [ ] **Step 3:** `MEMORY.md`: mỗi tệp đúng một dòng, không dòng trỏ tệp không tồn tại, không tệp mồ côi (so `Get-ChildItem` với các link).
- [ ] **Step 4:** không commit (ngoài kho); ghi tóm tắt thay đổi vào báo cáo làn.

### Task 6: Nhánh + worktree đã xong ("commit cũ")

**Files:** không tệp; thao tác git.

- [ ] **Step 1:** liệt kê `git branch --merged main` (LTTSTUDIOSAPP 75) + `git worktree list`; loại trừ nhánh/worktree có thay đổi chưa commit hoặc phiên khác đang dùng (`ListAgents`, dòng `??`, tệp mới trong 24 h).
- [ ] **Step 2:** worktree sạch + nhánh đã gộp ⇒ `git worktree remove <đường>` rồi `git branch -d <nhánh>` (chữ `-d` thường — git tự từ chối nhánh chưa gộp). Không `-D`, không `--force`.
- [ ] **Step 3:** nhánh chưa gộp ⇒ chỉ LIỆT KÊ vào báo cáo (chủ dự án quyết), không xoá.
- [ ] **Step 4:** LTTCODEAPP: làm SAU khi `phien/v2` gộp `main` (các nhánh `phien/v2-*` của Pha C).

### Task 7: LTTCODEAPP (sau khi 0.2.0 gộp main)

- [ ] **Step 1:** chạy lại Task 2–3 cho `D:\LTTCODEAPP\docs` (108 tệp: `plans/` đã hết hiệu lực như `2026-09-19-nang-harness-mot-luot.md` ⇒ lưu trữ; `STATE.md` là lối vào — đồng bộ với plan v2), `CLAUDE.md`/`AGENTS.md` của kho đó, từ điển thêm dòng cơ chế harness đã thay (plan cũ đợt 1–3 → plan v2).
- [ ] **Step 2:** quét lại = 0 ngoài ngoại lệ.

### Task 8: Gộp + nghiệm thu một lần

- [ ] **Step 1:** điều phối gộp các nhánh làn vào một nhánh `phien/don-tai-lieu`, giải xung đột (con trỏ tệp đã chuyển).
- [ ] **Step 2:** `python tools/quet_tai_lieu.py docs CLAUDE.md AGENTS.md` → 0 dòng ngoài `NGOAI_LE_QUET.md`; mọi thư mục cấp 1 của `docs/` có `README.md`.
- [ ] **Step 3:** `python tools/gate.py --doi` (L1) xanh → gộp `main` → đẩy origin. Không deploy riêng.
- [ ] **Step 4:** ghi `docs/NHAT_KY.md` (số tệp giữ/sửa/lưu trữ/xoá, nhánh/worktree đã dọn) + dòng tổng plan.

## Thứ tự + thời gian ước

Task 1 (30 phút, điều phối/1 agent) → Task 2 (30–45 phút, 1 agent) → Task 3 ×5 làn + Task 4 + Task 5 + Task 6 song song (1–1,5 h) → Task 8 (30 phút). Task 7 sau khi 0.2.0 gộp main (~45 phút). Tổng ~3–3,5 h thực, không chiếm khoá CPU (tài liệu thuần; chỉ L1 cuối qua gate).
