# 00 — BẢN ĐỒ HỆ THỐNG SỐNG (Prompt 00, AppStudios MVP Optimization V2)

**Ngày đo:** 2026-08-25 · **Máy:** máy chủ production (`C:\LTTPlatform` TỒN TẠI)
· **Nguồn:** `D:\LTTSTUDIOSAPP`, nhánh `public-api-v2`, HEAD `ec6a00c`

> Báo cáo này **chỉ đọc và đo**. Không sửa runtime code, config, migration hay
> asset nào. Không restore `socialbot`, `kichban`, `demo`, `mediatools`.

---

## 0. Ba câu trả lời cuối trang, đặt lên đầu

```text
LIVE_REPO_AUTHORITY_RESOLVED: YES  ← đã đóng lúc 23:50 bằng commit 9bb8f85 (xem F-01)
AUDIT_COMMANDS_SAFE:          YES  (có 6 lệnh phải tránh — mục 6)
NO_RUNTIME_CHANGE:            YES
```

**Lúc viết bản đầu, dòng trên là `NO`** — có ba trạng thái hệ thống khác nhau và
chưa ai chốt cái nào là "live" (F-01). Nó đã được đóng trong cùng buổi tối bởi
phiên `lttstudiosapp-3a`:

```
9bb8f85  Go HAN 4 app loi thoi: socialbot, kichban, mediatools, demo (Q108 + Q109)
         306 tệp, +3.250 / −96.734 dòng
```

Nay còn **hai** trạng thái: HEAD == cây làm việc (14 app), và production (19 app,
cũ cho tới lần deploy kế tiếp). Cả hai đều có tên. Prompt 01 chạy được.

---

## 1. Trật tự quyền lực (authority hierarchy)

Áp dụng thứ tự của `START_HERE.md`, đã ánh xạ sang tệp thật của kho này:

| Bậc | Nguồn | Tệp thật |
|---|---|---|
| 1 | Quyết định chủ sản phẩm mới nhất | `docs/QUYET_DINH_NEN_TANG.md` (Q1…Q109) |
| 2 | Mã sống + schema + config runtime | `apps/`, `platform_core/`, `server/`, `alembic/`, `secrets/app.env` |
| 3 | Cổng/test thi hành được | `tools/gate.py` (19 bước) + `tests/` (277 tệp) |
| 4 | Tài liệu quyết định hiện hành | `CLAUDE.md`, `AGENTS.md`, `docs/KE_HOACH_TRIEN_KHAI.md` |
| 5 | Kế hoạch / nhật ký | `docs/NHAT_KY.md`, `docs/KE_HOACH_*.md` |
| 6 | Snapshot sinh tự động / audit cũ | `ho_so_he_thong.txt`, `docs/APP_AUDIT/`, `docs/AUDIT_MVP_2026-07-31.md` |

**Kho này còn một hợp đồng audit riêng** (`docs/quy_tac_audit.md`, LTT-AQA v1.0)
quy định dashboard 4 điểm `Q · M · E · Release Gate`. Nó **không mâu thuẫn** với
V2 pack; V2 chi tiết hơn về evidence ladder. Đề nghị: Prompt 11 xuất kết luận
theo **cả hai** khuôn để không tạo nguồn chân lý thứ hai.

**Độ tươi của snapshot sinh tự động:** `ho_so_he_thong.txt` ĐÃ được sinh lại
theo cây hiện tại (`git diff --stat` = −47.950/+1.815 dòng, và bước gate
`system profile --check` PASS). Nên nó **tươi so với working tree**, nhưng
**mô tả một hệ thống chưa được deploy** — xem F-01.

---

## 2. Bản đồ kho + runtime

### 2.1 Điểm vào tiến trình

| Tiến trình | Điểm vào | Dịch vụ Windows | Trạng thái đo được |
|---|---|---|---|
| Web / control plane | `server/run.py` → `server/app.py` | `LTTStudioWeb` | Running |
| Worker job | `job_worker.py` → `platform_core/job_runner.py` | `LTTStudioWorker` | Running |
| Sidecar Codex | `codex_sidecar_main.py` | `LTTStudioCodex` | Running |
| Nexus (điều khiển máy xa) | `nexus_agent/`, `server/nexus/` | `LTTNexus` | Running |
| Đường ra Internet | `cloudflared` | (nssm) | Running |
| Cổng render máy B | `render_gateway/` | trên MÁY-B, ngoài kho này | không đo trong đợt này |
| CLI / công cụ | `tools/` (78 tệp) | — | — |
| Frontend build | `frontend/{agent-canvas,autosub-studio,prompt-ai-ommi}` | — | 3 bộ vitest, PASS |

### 2.2 Khối lượng mã (cây sống, không tính `__pycache__`)

| Khu | Tệp .py | Dòng |
|---|---:|---:|
| `tests/` | 283 | 68.940 |
| `apps/` (14 app) | 162 | 28.117 |
| `platform_core/` | 116 | 25.860 |
| `tools/` | 78 | 13.464 |
| `server/` | 50 | 13.099 |
| `sdk/` | 2 | 660 |

Tỉ lệ test/mã sản phẩm ≈ **1,0** — cao, và đó là tài sản, không phải nợ.

**Số lượng test: 4.727 → 4.093** sau đợt xoá *(nguồn: phiên `lttstudiosapp-3a`,
chưa tự đo lại — xem mục 4.1 về việc lượt `pytest` của đợt này bị huỷ có chủ ý)*.

⚠️ **Thời gian chạy test trước/sau KHÔNG so được với nhau.** `tests/conftest.py`
từng có **ba fixture `autouse`** chạy trước mọi test trong kho (dọn hộ engine
socialbot); chúng đã bị gỡ cùng đợt xoá. Nghĩa là bộ test nay nhanh hơn vì **bớt
việc mỗi test**, không phải vì mã tốt lên. Prompt 10 đo baseline hiệu năng phải
biết điều này — nếu không, một cải thiện không có thật sẽ được ghi thành thành
tích. *(Cũng do phiên `lttstudiosapp-3a` báo.)*

### 2.3 Đường đi một request và một job (mức cao)

```
Trình duyệt ─► Cloudflare Tunnel ─► LTTStudioWeb (FastAPI)
                                      │
                     ┌────────────────┼────────────────┐
                     ▼                ▼                ▼
              server/routes/*    apps/<slug>/routes  server/api/* (/api/v1)
                     │                │                │
                     └────────► platform_core/job_submit ◄┘
                                      │  (credit.giu_cho — GIỮ CHỖ)
                                      ▼
                                 bảng `jobs` (PostgreSQL)
                                      │
                LTTStudioWorker ──► job_runner: reclaim_orphans → claim
                                      │           → giữ gpu_lease (đập nhịp)
                                      │           → apps/<slug>/jobs.handle
                                      ▼
                       terminal state → credit.quyet_toan / credit.hoan
                                      → job_events → outbox webhook
```

**Một điểm cần ghi để Prompt 06 không phải tìm lại:** đường tiền **KHÔNG** chỉ
đi qua `job_submit`. Đo được **22 tệp** gọi trực tiếp API của `platform_core/credit`,
trong đó có đường **không qua worker**: `apps/chataistudio/routes.py` (4 lần),
`platform_core/llm/thanh_toan.py` (7 lần), `apps/upscalevideo/routes.py`,
`apps/autosubvideo/routes.py`, `apps/vps/services/billing.py`,
`apps/vps/bao_tri.py`, `platform_core/nexus/billing.py`. Đây là **inventory bắt
buộc** cho Prompt 06 §Money, không phải danh sách gợi ý.

---

## 3. Danh mục sản phẩm sống (đọc từ manifest thật, phân tích AST tĩnh)

14 app trong `apps/`. Cột `enabled`/`public` đọc trực tiếp từ tham số truyền vào
`AppManifest(...)`; ô trống = **không khai** ⇒ nhận mặc định của
`platform_core/registry.py` (`enabled=True`, `public=True`, `surface="customer"`,
`lifecycle="development"`).

| App | enabled | public | lifecycle | job_types |
|---|---|---|---|---|
| `agent` | True | True | development | `agent.advance` |
| `anhnoibo` | *(mặc định)* | *(xem ghi chú)* | *(mặc định)* | `anhnoibo.generate` |
| `autosubvideo` | True | *(mặc định)* | development | render / transcribe / … |
| `chataistudio` | True | True | development | — (streaming trong web) |
| `ltt_llm` | True | **False** | development | `ltt_llm.chat` |
| `nexus` | `nexus.enabled()` (cờ `LTT_NEXUS`) | *(mặc định)* | **released** | — |
| `prompt_ai_ommi` | True | True | **released** | `prompt_ai_ommi.generate` |
| `qualitylab` | True | **False** | **internal** | `qualitylab.evaluate` |
| `taoanh` | True | *(mặc định)* | development | `taoanh.generate` |
| `taoclipngan` | True | *(mặc định)* | development | `taoclipngan.render` |
| `taovideo` | True | *(mặc định)* | **released** | `taovideo.generate` |
| `thumbnail` | True | *(mặc định)* | development | `thumbnail.generate` |
| `upscalevideo` | True | *(mặc định)* | **released** | render / render.fast / … |
| `vps` | `vps_app.enabled()` (cờ `LTT_VPS`) | True | development | provision / rebuild / destroy |

**Cờ trên production đang đặt:** `LTT_NEXUS=1` (bật), `LTT_VPS` **không đặt**
(VPS tắt — đúng như tài liệu), `LTT_PUBLIC_API=1`,
`LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`.

**Fact quan trọng cho Prompt 02:** ~11 app rơi vào catalog khách hàng, và **8
trong số đó vẫn là `lifecycle="development"`**. Nghĩa là bề mặt MVP hiện tại
**không do ai chọn** — nó là mặc định của manifest cộng lại. Đây chính là câu hỏi
Prompt 02 phải trả lời, không phải giả định.

*Ghi chú `anhnoibo`:* manifest có bình luận nói `public=False`, nhưng phép đọc
AST không thấy tham số đó trong lời gọi `AppManifest(...)`. **Chưa kết luận** —
Prompt 02 phải xác minh bằng cách nạp registry thật, không đọc bình luận.

---

## 4. Danh mục cổng/test — cái nào có thẩm quyền

### 4.1 `python tools\gate.py` — CÓ thẩm quyền

Chạy lúc 2026-08-25 với `--quick`: **PASS 19/19** (E2).

```
bien dich duoc 23.8s · secret scan 16.4s · app contract lint 0.3s
ten chua dinh nghia 13.2s · nuot loi lang le 5.7s · trung so test 0.2s
bo qua im lang 7.6s · chuoi chua dich 7.3s · dich thieu ban EN 1.0s
system profile 21.7s · hop dong API 7.3s · anh chup hop dong 7.5s
tai lieu sinh ra 7.5s · SDK khop hop dong 4.7s · tai san GUI 0.3s
postman 9.4s · frontend agent-canvas 29.8s · frontend autosub-studio 7.0s
frontend prompt-ai-ommi 7.0s
```

⚠️ **`--quick` KHÔNG phải bằng chứng đủ, và chính gate nói vậy**: nó bỏ `pytest`
và `check_multiproc`. Dòng cuối gate in nguyên văn: *"Chua phai bang chung day
du — moi loi THAT ngay 25/08 deu nam o buoc `pytest` ma che do nay bo qua."*

**Về `pytest` đầy đủ — phép đo này CỐ Ý bỏ dở, không phải quên.** Phiên audit
đã chạy `pytest -q` nền lúc ~23:30 rồi **huỷ** khi biết một phiên khác
(`lttstudiosapp-3a`) đang chạy `gate.py` **đầy đủ** trên cùng cây từ 23:28. Hai
bộ pytest song song trên một máy có thể va nhau (thư mục tạm, CSDL test, cổng)
và làm **cả hai** đỏ vì lý do không thật; ngoài ra `__pycache__`/`.pytest_cache`
do lượt chạy thứ hai sinh ra có thể làm lệch dấu vân tay cây mà gate kia lấy ở
hai đầu.

⇒ **Phép đo có thẩm quyền là lượt gate đầy đủ của phiên kia.** Prompt 01 phải
lấy con số từ đó, và **không được** ghi vào báo cáo một kết quả pytest mà đợt
audit này chưa thật sự nhìn thấy.

### 4.2 Bánh cóc (ratchet) đang giữ — **DANH SÁCH GIỮ NGUYÊN**

Đây là những thứ **đang làm đúng việc** và Prompt 12/13 không được gỡ:

| Bánh cóc | Công cụ | Mốc hiện tại |
|---|---|---|
| Không thêm chỗ nuốt lỗi lặng lẽ | `check_silent_except.py` | có baseline |
| Không thêm test bị bỏ qua âm thầm | `check_bo_qua.py` | in hết danh sách mỗi lượt |
| Không thêm chuỗi chưa bọc `_()` | `check_i18n.py` | ~2.310 chuỗi |
| Không tăng nợ dịch EN | `check_dich_thieu.py` | **279** (203 rỗng + 76 fuzzy) / 2.352 |
| Không trùng số hiệu test | `check_so_test.py` | chặn tương lai, không dọn quá khứ |
| Hợp đồng `/api/v1` không tự vỡ | `check_api_compat.py` + `sinh_golden_api.py` | 24 route đóng băng |
| Tài liệu sinh ra không trôi | `build_public_api_docs.py --check` | — |
| Hồ sơ hệ thống không trôi | `build_system_profile.py --check` | — |
| **Không bán dưới giá vốn** | `tests/test_261` + `platform_core/gia_von.json` | miễn trừ phải có `ly_do` + `chu` + `han_ra_lai` |

Bánh cóc cuối là thứ đáng giá nhất trong kho: nó sinh ra **sau khi** đo được
nền tảng bán ảnh ở 45–57 % giá vốn suốt 22 ngày (`docs/PHAN_TICH_MVP_2026-08-23.md`).
Nó biến "bán lỗ" từ **tai nạn im lặng** thành **hành động có tên và có hạn**.

### 4.3 Trợ giúp, KHÔNG có thẩm quyền một mình

`python -m pytest -q` (bỏ 77 test frontend) · `tools/doctor.py` ·
`tools/lint_app_contract.py` chạy rời · mọi lệnh `--check` chạy lẻ.

---

## 5. Bản đồ nền tảng / dùng chung / di sản

**Di sản đã biến mất khỏi cây làm việc:** `core/`, `utils/`, `server/services/`,
`apps/socialbot`, `apps/kichban`, `apps/demo`, `apps/mediatools`.
Kiểm bằng `grep -rE "^\s*(from|import)\s+(core|utils)[\. ]"` trên
`apps|platform_core|server|tools|tests` ⇒ **0 kết quả**. Về mặt *nguồn*, việc cắt
phụ thuộc là **sạch**.

**Nền tảng nằm ở đáy đồ thị** như thiết kế: `platform_core/` không import
`apps/` (chưa thấy vi phạm trong đợt quét này — Prompt 04 phải xác nhận bằng AST
đầy đủ, không bằng grep).

**Điểm nóng đo được** (dòng, chỉ để *đặt câu hỏi*, không phải phán quyết):

| Tệp | Dòng | Handler HTTP |
|---|---:|---:|
| `server/admin_api.py` | 1.897 | — |
| `server/routes/developer.py` | 1.521 | **32** |
| `server/admin.py` | 1.388 | — |
| `platform_core/job_runner.py` | 1.236 | — |
| `tools/cam_cli.py` | 1.053 | — |
| `apps/autosubvideo/routes.py` | 899 | **25** |
| `platform_core/registry.py` | 893 | — |
| `apps/upscalevideo/routes.py` | 882 | **16** |

Trần hợp đồng app là **900 dòng / 30 handler** (`tools/lint_app_contract.py`).
`apps/autosubvideo/routes.py` ở **899/900** — sát trần đúng một dòng.
`server/routes/developer.py` **1.521 dòng / 32 handler** vượt cả hai ngưỡng
nhưng **không bị lint chặn** vì nó nằm trong `server/`, nơi hợp đồng app không
với tới. Đây là giả thuyết cho Prompt 05, chưa phải kết luận.

Tổng route HTTP đếm được trong `server/` + `apps/`: **314**.

---

## 6. Lệnh có tác dụng phụ — TRÁNH trong pha audit

| Lệnh | Vì sao tránh |
|---|---|
| `python tools/build_system_profile.py` *(không có `--check`)* | ghi đè `ho_so_he_thong.txt` |
| `python tools/sinh_golden_api.py --ghi` | ghi lại ảnh chụp hợp đồng API |
| `python tools/build_public_api_docs.py` *(không `--check`)* | sinh lại tài liệu khách đọc |
| `python tools/build_postman.py` *(không `--check`)* | sinh lại collection |
| `python tools/dong_goi_gui.py` *(không `--kiem`)* | ghi đè bản sao GUI |
| `deploy-self.ps1`, `setup/2-cai-dat.ps1` | **DỪNG dịch vụ production rồi copy đè `C:\LTTPlatform\app`** |
| `deploy/windows/backup.ps1 -IncludeSecrets` | tạo tệp chứa bí mật — chỉ chủ sản phẩm chạy |

Mọi bước trong `gate.py` đều dùng biến thể `--check`/`--kiem`, nên **chạy gate là
an toàn cho audit**. Đã kiểm từng bước.

---

## 7. Phát hiện — Prompt 00

Xếp theo `02_EXECUTION_RULES.md` §C (severity) và §B (evidence ladder).

---

### F-01 · P0 · E1_SOURCE + E3_RUNTIME — ✅ **ĐÃ ĐÓNG 23:50 bằng `9bb8f85`** — Có **ba** trạng thái hệ thống khác nhau, và chưa ai chốt cái nào là "live"

> **Trạng thái cuối:** đóng. Đợt xoá đã vào HEAD (`9bb8f85`, 306 tệp,
> −96.734 dòng). Cây làm việc sạch. Còn **hai** trạng thái, cả hai có tên.
> Phần dưới giữ nguyên như lúc phát hiện, vì phần "vì sao nó quan trọng" vẫn là
> đầu vào bắt buộc cho Prompt 01 và 07.

**Sự thật đo được:**

| Trạng thái | Ở đâu | Nội dung |
|---|---|---|
| **A. Đang phục vụ khách** | `C:\LTTPlatform\app` | **19 app**, còn nguyên `socialbot`, `kichban`, `demo`, `mediatools`, `core/`. 4 dịch vụ **Running**. |
| **B. Git HEAD** | `ec6a00c` | *"Diem lui truoc dot xoa socialbot"* — điểm lùi **trước** đợt xoá |
| **C. Cây làm việc** | `D:\LTTSTUDIOSAPP` | **14 app**, đợt xoá đã làm nhưng **CHƯA COMMIT** |

Trạng thái C gồm **306 mục chưa commit**: 175 xoá đã `git add`, 65 xoá chưa
`add`, 65 tệp sửa, 1 tệp mới chưa theo dõi.

**Vì sao nó quan trọng với MVP:** ba hệ quả, mỗi cái đủ để chặn một prompt sau.

1. **Prompt 01 sẽ trả lời SAI nếu không phân biệt A và C.** Đếm trên nguồn thì
   `REMOVED_APPS_ACTIVE_REACHABILITY = 0`. Đếm trên thứ khách đang gõ vào thì nó
   **không phải 0**: production **đang mount 43 route bảng điều khiển FB/TikTok
   cũ**. Xác minh: `C:\LTTPlatform\app\server\app.py:153-156` trả `True` khi cờ
   không đặt, và `LTT_SOCIALBOT_ROUTES` **không có** trong
   `C:\LTTPlatform\secrets\app.env`.
2. **Rủi ro mất trắng công việc.** Toàn bộ đợt xoá Q108+Q109 (~15.000 dòng, 44
   tệp test, 10 template) sống **duy nhất** trong một cây làm việc chưa commit,
   trên một máy tự khởi động lại để cập nhật Windows.
3. **Đây đúng là điều kiện Stop-the-line §K** của pack: *"working tree chứa thay
   đổi owner chưa commit có nguy cơ bị ghi đè"*.

**Tuỳ chọn:**

- **A. Commit đợt xoá lên nhánh hiện tại trước khi chạy Prompt 01** *(khuyến
  nghị)* — làm C thành trạng thái có tên, có thể diff, có thể rollback. Không
  deploy. Cửa hai chiều: `git revert` được.
- **B. Giữ nguyên chưa commit, audit trên cây làm việc** — không mất thời gian,
  nhưng mọi phát hiện của 15 prompt sau treo trên một trạng thái không có tên,
  và một lần `git checkout .` nhầm là xoá sạch.
- **C. Deploy C lên production trước, rồi audit** — **KHÔNG khuyến nghị**: deploy
  một đợt xoá 15.000 dòng chưa qua `pytest` đầy đủ, trên hệ thống đang thu tiền
  thật, là một cửa một chiều.

**Khuyến nghị:** A. Và ghi rõ trong Prompt 01 rằng "residue = 0" chỉ đúng cho
**nguồn**; production còn residue cho tới lần deploy kế tiếp.

**KHÔNG được đổi:** không deploy trong pha audit; không restore 4 app.

**Cần chủ sản phẩm quyết?** **CÓ** — commit và (sau này) deploy là quyết định
của chủ sản phẩm, không phải của một phiên audit.

> **CẬP NHẬT 23:4x — đang được xử lý ở một phiên khác.** Phiên
> `lttstudiosapp-3a` báo rằng chủ sản phẩm đã giao nó đợt dẹp 4 app, phần mã đã
> xong, và nó **sắp commit 307 thay đổi** (chừa lại hai tệp trong
> `docs/MVP_OPTIMIZATION_V2/` vì đó là việc đang dở của phiên này).
>
> Nếu commit đó xong thì **ba trạng thái rút còn hai**: HEAD == cây làm việc, và
> production là trạng thái thứ hai đã biết tên, cũ cho tới lần deploy kế tiếp.
> Tuỳ chọn A ở trên coi như đã được chọn — **không phải bởi phiên audit này**.
>
> ⚠️ Điều này **không** đóng F-01. Nó chỉ đổi F-01 từ *"ba trạng thái, chưa ai
> chốt"* thành *"hai trạng thái, production còn residue tới khi deploy"*. Trước
> khi chạy Prompt 01, phải xác minh bằng `git log -1 --stat` và ghi **mã commit
> thật** vào đây — không ghi theo lời hứa.

---

### F-02 · P0 · E1_SOURCE — ✅ **ĐÃ ĐÓNG 23:50 bằng `9bb8f85`** — `platform_core/settings.py` **chưa vào git** nhưng web import nó lúc khởi động

> **Trạng thái cuối:** đóng. Xác minh bằng
> `git show --stat 9bb8f85 -- platform_core/settings.py` ⇒ *1 file changed, 68
> insertions*. Tệp nay đã được theo dõi; clone mới khởi động được.

**Sự thật:** `git status` liệt kê nó là `??` (chưa theo dõi). Nó được import bởi:

- `server/app.py:22` — `from platform_core.settings import Environment`
- `server/settings.py:14` — `Environment, resolve_environment`
- `tools/doctor.py:117`, `tests/test_35_p2_runtime_boundary.py:31`

**Vì sao quan trọng:** tệp này là **phần duy nhất của `core/settings.py` cũ còn
sống sót** sau khi gỡ socialbot — nó chính là thứ đã gỡ bỏ lớp lỗi
"`data/config.json` hỏng ⇒ `/health/ready` trả 503". Nhưng vì chưa vào git:
một `git clean -fd`, một clone mới, hay một lần khôi phục từ git **đều cho ra
một kho không khởi động được**. `CLAUDE.md` ghi *"Mã nguồn trong git ✅ từ
2026-07-31"* — với tệp này thì câu đó **không còn đúng**.

**Đo lại được:** `git clone` kho vào thư mục trống rồi
`python tools/check_bien_dich.py` → `ModuleNotFoundError`.

**Khuyến nghị:** `git add platform_core/settings.py` cùng batch với F-01. Cơ khí,
không đổi behavior, cửa hai chiều. **Không cần chủ sản phẩm quyết** (§I: sự thật
kỹ thuật tự chứng minh được thì không đẩy thành câu hỏi).

---

### F-03 · P1 · E3_RUNTIME — Sao lưu production đã dừng 8 ngày, và bí mật thì **chưa từng** được sao lưu ở nơi kiểm chứng được

**Sự thật đo trên chính máy chủ:**

- `Get-ScheduledTaskInfo -TaskName 'LTTStudioBackup'` ⇒ **task KHÔNG TỒN TẠI**.
  Kịch bản `deploy/windows/5-lich-backup.ps1` có sẵn để tạo nó, nhưng nó chưa
  từng được đăng ký (hoặc đã bị gỡ).
- `C:\LTTPlatform\backups\` có **14** tệp, tệp mới nhất
  `ltt_data_20260817_172426.zip` — **2026-08-17**, tức **8 ngày** trước.
- Thư mục sao lưu bí mật (`backups-secrets`, mặc định của `backup.ps1`) **không
  tồn tại** ⇒ `LTT_TOKEN_ENCRYPTION_KEY` và `LTT_API_KEY_PEPPER` chưa có bản sao
  nào ở đây.
- `D:\LTTBackups` **có tồn tại nhưng bị ACL chặn** — không đọc được ở quyền hiện
  tại. **Chưa kết luận** về nội dung nó.

**Vì sao quan trọng:** trong 8 ngày đó nền tảng **đã thu tiền thật** (LLM nội bộ
bán từ 24/08; Nexus thu credit; VPS đã diễn tập thu tiền). Và mất
`LTT_TOKEN_ENCRYPTION_KEY` không phải mất một bản sao — nó làm **mọi token đã mã
hoá và mọi hash khoá API của khách trở thành rác vĩnh viễn**, kể cả khi bản dump
CSDL còn nguyên.

**Đúng phạm vi phát hiện này:** *"Không có bằng chứng sao lưu tươi ở nơi tôi đọc
được, và không có lịch chạy"*. Nó **không** kết luận là hoàn toàn không có sao
lưu — `D:\LTTBackups` chưa kiểm được.

**Việc đo còn thiếu (cần quyền nâng cao — chủ sản phẩm chạy):**

```powershell
Get-ChildItem D:\LTTBackups -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 FullName, Length, LastWriteTime
```

**Cần chủ sản phẩm quyết?** Việc *đo* thì không. Việc *bật lại lịch sao lưu*
trên máy đang chạy thật thì **CÓ**.

---

### F-04 · P1 · E1_SOURCE — `CLAUDE.md` nói cửa hàng API chưa mở; production **đã mở hai tool tính tiền**

**Sự thật:** `C:\LTTPlatform\secrets\app.env` có
`LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`.

`CLAUDE.md` mục Public API viết: *"Khu API bật (`LTT_PUBLIC_API=1`) nhưng
`LTT_PUBLIC_API_TOOLS` **rỗng**, nên `GET /api/v1/tools` trả `200` với danh sách
rỗng"* và *"còn nợ ba việc: **mở tool** (bắt đầu bằng `image.thumbnail`)"*.

**Vì sao quan trọng:** hai câu trong **cùng một tài liệu** mâu thuẫn nhau — hàng
H38 nói LLM *"ĐANG BÁN 2026-08-24"*, hàng Public API vẫn nói cửa đóng. Một phiên
làm việc sau đọc hàng Public API sẽ tin rằng `/api/v1` không phục vụ ai, rồi
sửa nó như sửa mã chết. **Nó đang phục vụ khách trả tiền.**

Ngoài ra, tool đã mở **không phải** `image.thumbnail` như kế hoạch ghi, mà là
`text.chat` và `image.ltt` — nghĩa là thứ tự mở cửa đã đổi trên thực tế mà kế
hoạch chưa theo kịp.

**Khuyến nghị:** sửa **tài liệu**, không sửa cờ. Xếp vào Prompt 08 (authority
drift) và Prompt 15 §8 (docs reconciliation). Không đổi runtime.

---

### F-05 · P2 · E1_SOURCE — Ví dụ chuẩn của hợp đồng app vẫn trỏ về `apps/demo/` đã bị xoá

**Sự thật:** `platform_core/registry.py:31` — *"Xem `apps/demo/` làm mẫu tối
thiểu và `docs/03_THEM_APP_MOI.md` để làm theo."*

Đây **đúng câu hỏi Prompt 01 đặt riêng cho `demo`**: *"minimal app example/smoke
path có authority thay thế chưa?"*. Câu trả lời: `CLAUDE.md` **đã** chỉ định
người thay (`apps/anhnoibo/` cho app chỉ-job, `apps/thumbnail/` cho app có route,
và app THỬ trong `tests/conftest.py::app_thu`), nhưng **docstring của chính
registry — thứ người viết app đọc đầu tiên — thì chưa.**

Phân loại: `REPLACE_AUTHORITY`. Sửa một dòng docstring, không đổi behavior.

**Xác nhận độc lập từ phiên `lttstudiosapp-3a`:** `apps/demo` từng là **khuôn**
cho bốn bộ test hạ tầng — `test_67` (hàng đợi), `test_68` (credit), `test_151`
(GPU), `test_173` (upload) — và người thay là `tests/conftest.py::app_thu`, một
app THỬ sống trong bộ nhớ một test, không thư mục, không route.

⇒ Điều đó làm F-05 **nặng hơn** chứ không nhẹ đi: authority thay thế **đã tồn
tại và đã được bốn bộ test dùng thật**, chỉ có docstring của registry — thứ
người viết app mới đọc trước tiên — là còn trỏ vào chỗ trống.

---

### F-06 · ~~P2~~ → **KHÔNG PHẢI VIỆC CẦN SỬA** · E2_TEST — `messages.po` còn tham chiếu tệp nguồn của app đã xoá

**Sự thật:** `locale/en/LC_MESSAGES/messages.po` chứa **105** dòng
`#: apps/kichban/...` / `#: apps/mediatools/...` trỏ tới tệp không còn tồn tại.

> ⛔ **SỬA LẠI PHÁN ĐOÁN CỦA CHÍNH MỤC NÀY.** Bản đầu xếp đây là P2 "nên dọn,
> nhưng không rẻ". **Sai.** Phiên `lttstudiosapp-3a` đã **đo** chứ không ước:
> trích lại để dọn 105 mục đó khiến `msgmerge` sinh thêm **25 bản dịch SAI**
> (`fuzzy` 76 → 101). Tức việc "dọn" làm nợ dịch **tăng**, và tăng ở dạng tệ
> nhất — `msgfmt` bỏ qua mọi mục fuzzy, nên bản dịch hỏng **trông như đã xong**
> khi đọc tệp `.po`.
>
> ⇒ **105 mục này được GIỮ CÓ CHỦ Ý.** Prompt 12 **không** được xếp nó vào
> `REMOVE_RESIDUE_SAFE`. Phân loại đúng: `HISTORICAL_ONLY`.
>
> Luật rút ra, đáng mang sang mọi prompt sau: **hạ mốc dịch bằng cách DỊCH,
> không bao giờ bằng cách TRÍCH LẠI.**

Nợ dịch EN hiện tại: **279/2.352** mục (203 `msgstr` rỗng + 76 `fuzzy`). Bánh cóc
đang giữ ở đúng 279 — không cho tăng.

Đây là ví dụ tốt cho §B của execution rules: một phát hiện E1 (đọc nguồn thấy
"rác") bị một phép đo E2 lật ngược. Không nâng E1 thành kết luận.

---

### F-07 · P2 · E1_SOURCE — Có một git worktree thứ hai giữ trạng thái **trước** đợt xoá

**Sự thật:** `git worktree list` cho hai mục:

```
D:/LTTSTUDIOSAPP                                            ec6a00c [public-api-v2]
D:/LTTSTUDIOSAPP/.claude/worktrees/wonderful-jepsen-f190f3  05fc083 [claude/wonderful-jepsen-f190f3]
```

Worktree kia nằm **bên trong** cây chính và chứa bản sao đầy đủ **trước khi xoá**
— gồm `core/`, `tests/test_152_socialbot_route_flag.py`, `CLAUDE.md` cũ.

**Vì sao quan trọng:** mọi lệnh quét toàn kho đều đếm nó hai lần. Trong chính đợt
audit này, lần `grep -rn "LTT_SOCIALBOT_ROUTES"` đầu tiên trả về **13 kết quả từ
worktree kia** trước khi trả kết quả thật — nghĩa là một phiên bất cẩn sẽ báo
"còn residue socialbot" trong khi nguồn đã sạch. Prompt 01 **phải** loại
`.claude/worktrees/` khỏi mọi phép đếm, hoặc worktree phải được gỡ trước.

**KHÔNG tự xoá nó trong pha audit** — nó có thể là việc đang dở của một phiên
khác (`git worktree remove` là cửa một chiều với công việc chưa commit ở đó).

---

### F-08 · P2 · E1_SOURCE — Thẩm quyền thiết kế bị pha loãng ở tầng template

**Đo được trên 81 template:**

- **57** tệp dùng thuộc tính `style="..."` nội tuyến;
- **11** tệp có khối `<style>` riêng;
- hệ thiết kế tập trung chỉ có **788 dòng** (`server/static/ltt.css`);
- `page_mode` khai rõ ở **15** template (8 `wide`, 6 `immersive`, 1 `standard`);
- `.page--catalog` **được định nghĩa trong CSS nhưng không template nào dùng**.

Đây là **tín hiệu**, chưa phải phán quyết (§E: không biến số dòng thành kiến
trúc). Prompt 09 phải kiểm bằng E3 trên trình duyệt: cùng một nút bấm có trông
khác nhau giữa hai trang MVP không? Nếu không, đây là P3 chứ không phải P2.

---

### F-09 · P3 · E1_SOURCE — Thư mục gốc lẫn tạo tác tạm

Ở gốc kho: **~30 tệp `.png`** (ảnh chụp audit/UI), `nuitka-crash-report.xml`,
`yolov8n.pt`, và các thư mục `tmp/`, `temp_videos/`, `test-results/`, `build/`,
`dist/`, `__pycache__/`. Commit `14f3bc6` (*"Bo anh chup man hinh lot vao repo"*)
cho thấy đây là vấn đề **lặp lại**, không phải một lần.

Không ảnh hưởng runtime. Nhưng `tmp/` đã từng chứa **bản sao thứ hai của thư mục
`tests`** (đó là lý do `gate.py` phải truyền `--ignore=tmp --ignore=test-results`).
Xếp Prompt 13, độ ưu tiên thấp nhất.

---

## 8. Danh sách GIỮ NGUYÊN — cái đang đúng, đừng động vào

Pack yêu cầu mục này, và ở kho này nó dài hơn danh sách lỗi:

1. **`gia_von.json` + `test_261`** — một nguồn giá vốn duy nhất, đơn vị số
   nguyên (milli-credit), và miễn trừ bán-dưới-giá-vốn **bắt buộc có chữ ký và
   hạn**. Prompt 13 không được "gom cho gọn" cái này.
2. **Ba cổng độc lập cho tool `/api/v1`** (`api_exposed` + `api_contract` đủ +
   `LTT_PUBLIC_API_TOOLS`) — fail-closed đúng như Q92, và nó **đang hoạt động**:
   14 app mà chỉ 2 tool ra ngoài.
3. **`platform_core/leases.py`** — lease có tên cho việc nền, cộng `gpu_lease`
   với đập nhịp + thu hồi mồ côi. Đây là câu trả lời cho lớp lỗi "mọi vòng nền
   được viết như thể chỉ có một tiến trình" của H36.
4. **Một alembic head duy nhất** (55 revision, head `a4d70e93f158`) — không có
   nhánh migration mồ côi.
5. **Quyết toán credit khoá theo job** (`_khoa_ket_so_job`, `_ket_qua_da_chot`)
   — chống quyết toán hai lần ở tầng dữ liệu, không ở tầng route.
6. **Bước "bien dich duoc" đặt ĐẦU TIÊN trong gate** — sinh ra sau sự cố gate báo
   PASS trên mã không parse được. Thứ tự này là có chủ ý.
7. **Tỉ lệ test/mã ≈ 1,0** với 277 tệp test.
8. **`--quick` tự nói mình chưa đủ** — một cổng chất lượng khai báo giới hạn của
   chính nó là thứ hiếm và đáng giữ.

---

## 9. Sự thật đã xác minh, bàn giao cho prompt sau

| Prompt | Nhận được gì từ đây |
|---|---|
| **01** | F-01 (production ≠ nguồn), F-05 (authority thay thế), F-06 (`.po`), F-07 (**loại `.claude/worktrees/` khỏi mọi phép đếm**) |
| **02** | Bảng 14 app; 8/11 app khách hàng vẫn `lifecycle="development"`; `LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`; `LTT_VPS` tắt |
| **03** | 314 route; đường tiền có **hai** nhánh (qua worker và trong-request) |
| **04/05** | Điểm nóng đã đo; `server/routes/developer.py` 1.521 dòng/32 handler **ngoài tầm với của lint hợp đồng app**; `autosubvideo/routes.py` ở 899/900 |
| **06** | **22 tệp** gọi trực tiếp `credit.*` — inventory mutation bắt buộc |
| **07** | Production đang mount 43 route legacy (F-01); danh sách 48 khoá env production |
| **08** | F-04 (mâu thuẫn tài liệu ↔ cờ thật); `gia_von.json` là SSoT giá vốn |
| **09** | F-08 (57/81 template dùng style nội tuyến; `.page--catalog` mồ côi) |
| **10** | F-03 (sao lưu); `deploy-self.ps1` khởi động lại 3 dịch vụ nhưng **không có `LTTNexus`** |
| **11** | 4 quyết định cần chủ sản phẩm: **D-V2-01** commit đợt xoá · **D-V2-02** bật lại lịch sao lưu · **D-V2-03** bề mặt MVP · **D-V2-04** lộ trình gỡ 43 route legacy trên production |

---

## 10. Đầu vào đã tiêu thụ / giả định cho prompt sau

**Đã đọc:** `START_HERE.md`, `00_CURRENT_CONTEXT.md`,
`01_MVP_REFERENCE_PRINCIPLES.md`, `02_EXECUTION_RULES.md`, 16 prompt,
`CLAUDE.md`, `AGENTS.md` (mục quy tắc), `docs/quy_tac_audit.md`,
`docs/PHAN_TICH_MVP_2026-08-23.md` (mục 1–2).

**Giả định cần xác nhận, không được coi là fact:**

1. `platform_core/` không import `apps/` — mới quét bằng grep, chưa bằng AST đầy đủ.
2. `anhnoibo.public` — bình luận nói `False`, AST không thấy tham số. Prompt 02 phải nạp registry thật.
3. Số khách thật / job thật / credit thật trên production — **chưa đo**, và
   **không nên đo mà không có phép của chủ sản phẩm** (`CLAUDE.md` toàn cục:
   *"Không dùng dữ liệu production nếu chưa được người dùng cho phép rõ ràng"*).
   Nhưng Prompt 02 **không thể chốt bề mặt MVP mà không biết con số này** — xem
   D-V2-03.

---

---

# PHẦN II — ĐO SÂU (2026-08-26, cây `9848efa`)

Phần I đo bề mặt trên một cây đang động. Phần II đo **cấu trúc** trên cây đã
commit và đứng yên: đồ thị phụ thuộc bằng AST (không grep), toàn bộ bề mặt HTTP
kèm chốt quyền, mọi điểm đổi tiền, vòng đời job, và thẩm quyền cấu hình.

## II.1 Đồ thị phụ thuộc — 732 tệp `.py`, phân tích AST

**Kết quả quan trọng nhất, và nó là tin tốt:**

```
platform_core → apps/*        0 cạnh
```

Nền tảng **thật sự** nằm ở đáy đồ thị. Công của H22 giữ được. Đây là thứ khiến
mọi đề xuất cấu trúc phía sau chỉ cần **nhỏ**, không cần tái kiến trúc.

Cạnh đáng soi, xếp theo mức nghiêm trọng:

| ID | Cạnh | Số lần | Nhận định |
|---|---|---|---|
| **A-01** | `apps/taovideo` → `apps/upscalevideo` | 2 | **Cạnh xuyên-sản-phẩm DUY NHẤT của cả kho** |
| **A-02** | `server/api/*` → `apps/ltt_llm` | 5 | Tầng adapter công khai biết tên **đúng một app** |
| **A-03** | `server/routes/dashboard.py` → `apps.anhnoibo.gia`<br>`server/routes/status.py` → `tools.doctor` | 1 + 1 | Control plane biết giá của một app; và một chu trình `server ↔ tools` |
| **A-04** | `apps/*` → `server.*` | **72** | Xem dưới — **không phải mớ hỗn độn** |

### A-04 đọc kỹ trước khi kết tội

72 cạnh nghe như thảm hoạ. Nhưng 12 app chạm **đúng bốn module**:

```
server.deps            22   (get_db, user_hien_tai)
server.auth.session    19   (require_login)
server.templating      17   (templates)
server.auth.csrf       14   (issue/verify_csrf_token)
```

Không app nào chạm sâu hơn thế. Đây **không phải** coupling lan man — đây là
**một biên nền tảng đã tồn tại trên thực tế nhưng chưa ai khai báo**, và nó đang
sống nhầm gói (`server/` = tầng vận chuyển) thay vì đúng gói (`platform_core/`).

Theo §F "rule of minimum new abstraction", đáp án **không** phải là bọc lại mọi
thứ — xem lộ trình `LO_TRINH_CHI_TIET.md` mục T-13.2.

### A-01 chi tiết — cạnh xuyên-sản-phẩm duy nhất

`apps/taovideo/routes.py:548` và `:577`:

```python
from apps.upscalevideo import cost as upscale_cost           # /upscale-quote
from apps.upscalevideo.service import submit_upscale_job      # /upscale-confirm
```

Route của sản phẩm A **báo giá và nộp job của sản phẩm B**. Đây đúng câu hỏi số
5 của Prompt 04: *"workflow liên product nên sống ở đâu?"*.

⭐ Nhưng đọc thêm một tầng thì nó **không phải một sai lầm cẩu thả**: hàm được
gọi tên là `submit_upscale_job` và `cost.uoc_luong_credit` — tức `upscalevideo`
**đã có** một bề mặt dùng-được-từ-ngoài. Vấn đề là bề mặt đó chưa được khai là
công khai, nên không có gì ngăn lần sau ai đó với tay vào chỗ sâu hơn.

### A-02 chi tiết — và vì sao nó nặng hơn vẻ ngoài

`platform_core/public_api/config.py:20-22` tự viết ra luật:

> *"the names apps declare through `ToolSpec` — **this module must not know any
> of them**, see `AGENTS.md` 8.4"*

Trong khi `server/api/` nhắc `apps.ltt_llm` **5 lần** (`chat.py:75,98`;
`streaming.py:177,390,711`). Nền tảng có một luật thành văn, và tầng ngay cạnh
luật đó vi phạm nó.

Có lý do bào chữa thật: `/messages`, `/responses`, `/chat/completions` là hợp
đồng **tương thích OpenAI/Anthropic**, bản chất gắn với LLM. Nhưng lý do đó biện
minh cho *sự tồn tại của route*, không biện minh cho việc **hằng số trần token
của một app** (`MAX_TOKENS_TRAN`, `tran_theo_ngu_canh`) bị đọc trực tiếp từ tầng
vận chuyển.

## II.2 Bề mặt HTTP — 313 route, chốt quyền đầy đủ

| Chốt (`Depends`) | Số route |
|---|---|
| `require_login, get_db` | 126 |
| `require_login` | 81 |
| *(không có `Depends`)* | **40** |
| `require_account, get_db` | 31 |
| `_cong_co, require_login, get_db` | 11 |
| `_bat_buoc_web_broker, require_login` | 8 |
| `require_operator` (+ `get_db`) | 9 |
| `require_scope(...)` | 4 |
| còn lại | 3 |

**Đã kiểm từng route trong 40 route "không có `Depends`".** Không route nào hở:

- **10 route `server/nexus/routes.py`** — xác thực bằng **HMAC thiết bị**
  (`_xac_thuc(device_id, timestamp, signature)`), có chống phát lại bằng dấu
  thời gian.
- **`relay_check`** — `hmac.compare_digest` trên khoá relay, **fail-closed**:
  biến rỗng ⇒ endpoint tắt.
- **3 route `/watch/*` của `upscalevideo`** — dòng đầu tiên của cả ba đều gọi
  `_watch_user_id(request)` ⇒ bearer token, 401 nếu sai. Docstring ghi rõ *"no
  browser cookie is accepted"*.
- **`/webhooks/payment/payos`** — `xac_thuc_webhook(headers, raw)` trên **thân
  thô**, trả 400 `invalid signature`.
- **`/api/v1`** — 23 chốt `require_scope` + 2 `require_principal`.
- Còn lại công khai có chủ ý: `/login`, `/register`, `/forgot-password`, `/live`,
  `/ready`, `/version`, `/`, `/tai-xuong`, `/huong-dan`, favicon.

⇒ **Ở mức E1, bề mặt xác thực sạch.** Prompt 07 vẫn phải nâng lên E2 bằng test
âm tính chủ-A/chủ-B; "không thấy lỗ khi đọc" chưa phải "không có lỗ".

## II.3 Vòng đời job — không có mồ côi

19 `job_type` khai trong 12 manifest. **Mọi job_type đều có handler**; không app
nào khai job mà thiếu `jobs.py`, không app nào có `jobs.py` mà quên khai.

## II.4 Đường tiền — 24 điểm đổi tiền, và MỘT lỗ thật

```
giu_cho  8      quyet_toan  4      hoan  8
tru      2      hoan_phi    1      nap   1
```

Điều đáng chú ý không phải con số, mà là **hai lớp đường tiền có vòng đời khác
hẳn nhau**:

| Lớp | Ai kết sổ | Chết giữa chừng thì sao |
|---|---|---|
| **Qua worker** (job) | `job_runner` khi job vào trạng thái cuối; job mồ côi được `reclaim_orphans` thu hồi ⇒ luôn tới trạng thái cuối | **An toàn** — có đường về |
| **Trong request** (streaming) | chính request đó, bằng `try/except/finally` | ⚠️ **không có đường về** |

### 🔴 M-01 · **P0** (tiền khách đã mất thật) · **E4_PRODUCTION** — Lưới hoàn tiền chỉ căng TRONG tiến trình, mà deploy là hành động giết tiến trình

> ## ⛔ ĐÃ XẢY RA. HAI LẦN. TIỀN THẬT.
>
> Đo trên CSDL production, chỉ đọc *(phiên `lttstudiosapp-3a` thực hiện — phiên
> audit này chưa được cấp phép đọc dữ liệu production, xem D-02)*:
>
> ```
> Tổng bút toán 'hold'              : 123 bút toán, 1.105 credit
> Giữ chỗ CHƯA settle CHƯA refund   : 2   (cả hai KHÔNG có hàng Job)
>     ms:de4cc565…   1 credit   2026-08-24 22:28:06
>     ms:84e9b141…   1 credit   2026-08-24 23:58:10
> TIỀN KẸT                          : 2 credit
> Vị ngữ hiện tại `job_id = ''` bắt được : 0 / 2
> ```
>
> ⭐ **Và con số đáng sợ nhất không phải "2 credit".** Dòng `23:58:10` có người
> tình cờ thấy và đã ghi vào
> `docs/PUBLIC_API/KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §P2-4, đang chờ chủ sản
> phẩm cho ghi bút toán bù. Dòng `22:28:06` **không ai ghi ở đâu cả**.
>
> ⇒ Tỉ lệ phát hiện thủ công = **1/2**. Đó là lập luận mạnh nhất cho việc phải
> treo cái chuông — mạnh hơn mọi suy luận về kiến trúc.

**⚠️ SỬA LẠI PHÁN ĐOÁN CỦA CHÍNH MỤC NÀY.** Bản đầu viết *"bốn đường chỉ dựa vào
`try/finally` trong tiến trình"*. **Không còn đúng nguyên văn.**
`server/api/streaming.py:257` đã có `except BaseException: hoan_luot(...)`, thêm
ngày 25/08 **đúng sau sự cố `23:58:10`** — chú thích tại chỗ còn ghi thẳng số hiệu
dòng mồ côi đó, và giải thích vì sao phải `BaseException` chứ không `Exception`
(`CancelledError` khi khách ngắt giữa chừng **không** kế thừa `Exception`).

Nhưng bản vá ấy **không đóng lỗ**, và cách gọi tên đúng thì mạnh hơn cách gọi cũ:

> **Lưới CÓ, nhưng chỉ căng bên trong tiến trình — và deploy là hành động giết
> tiến trình.**

Đây không còn là một lỗ hổng chung chung. Đây là **một quy trình vận hành tự mở
lỗ của chính nó**, đều đặn, mỗi lần deploy.

**Bốn sự thật, mỗi cái tự kiểm được:**

**(0) Bản vá không sống sót qua `Stop-Service -Force`.** `setup/2-cai-dat.ps1:107-111`
dừng **cưỡng bức** cả `LTTStudioWorker`, `LTTStudioWeb` và `LTTStudioCodex` trước
khi chép đè `app\`. `except BaseException` là mã Python — nó không chạy khi
Windows kết liễu tiến trình. Và mức bảo vệ **khác nhau trên từng đường**:

| Đường | Lưới trong tiến trình | Sống sót khi bị giết |
|---|---|---|
| `server/api/streaming.py` (`/messages`, `/responses`) | ✅ `except BaseException` (25/08) | ❌ |
| `apps/chataistudio/routes.py:228` | ⚠️ một phần — `finally` có xử `GeneratorExit` | ❌ |
| `apps/chataistudio/routes.py:464` | ❌ giữ/quyết toán/hoàn ở ba hàm rời | ❌ |
| `platform_core/agent/budget.py:86` | ❌ `settle()` hoàn phần thừa, nhưng **không ai quét run treo** | ❌ |

⭐ **Câu hỏi mở về `agent/budget` — ĐÃ TRẢ LỜI, và nghiêng về phía xấu.**

Bản đầu viết *"về nguyên tắc thu hồi được — nếu có gì đó quét các run treo"*. Đã
kiểm: grep `AGENT_RUNNING`/`AgentRun` đi kèm `sweep|stale|orphan|reclaim|expired`
trong `job_runner.py` + `platform_core/agent/` ⇒ **trống**. Và
`_mot_luot_bao_tri` làm đúng sáu việc, không việc nào là nó.

⇒ **"Về nguyên tắc thu hồi được" chỉ thành "thu hồi được" khi có ai viết vòng
quét. Hiện chưa có.** Nên kết luận đúng là: **bốn đường, không đường nào có lưới
sống sót qua `Stop-Service -Force`.**

**Số production cho đường này** *(nguồn: phiên `lttstudiosapp-3a`)*:

```
agent_runs: cancelled 2 · done 2   (cả bốn đều 02/08)
run chưa kết thúc                            : 0
giữ chỗ mang id AgentRun, chưa được định đoạt: 0
```

⚠️ **Đọc con số này cho đúng, vì nó rất dễ đọc ngược.** Đường `agent/budget`
chưa từng rò một credit nào — **không phải vì nó an toàn, mà vì cả lịch sử chỉ
có 4 run.** Mẫu 4 không đủ nói gì về độ an toàn; nó chỉ đủ nói **hôm nay không có
tiền kẹt ở đó**. Đây là R8 đọc theo chiều ngược: *"0 sự cố trên mẫu nhỏ"* không
phải bằng chứng an toàn, y như *"phát hiện được 2"* không phải bằng chứng chỉ có 2.

⭐ **Nhưng có một mặt tốt, và nó là mặt tốt về CÁCH SỬA.** `AgentRun` là chỗ duy
nhất trong bốn đường để lại **hàng bền vững có `status` + `finished_at`**. Nghĩa
là khuôn cho T-12.1 **đã có sẵn trong kho và đã chạy nhiều tháng**:

- `platform_core/jobs.py:243 reclaim_orphans()` — quá hạn đập nhịp ⇒ đẩy về
  trạng thái cuối, đếm lượt đã tiêu, và có `with_for_update(skip_locked=True)`
  để hai worker không nhặt trùng;
- `platform_core/leases.py:71 reclaim_expired()`.

Cùng một hình dạng, chỉ đổi bảng. **Không cần phát minh cơ chế mới** — đúng §F
(abstraction tối thiểu).

**(1) Bốn chỗ giữ chỗ ngoài vòng đời job:**

| Chỗ | `job_id` truyền vào |
|---|---|
| `platform_core/llm/thanh_toan.py:81` (dùng bởi `server/api/streaming.py`, `chat.py`) | `request_id` |
| `apps/chataistudio/routes.py:228` | `umsg_id` |
| `apps/chataistudio/routes.py:464` | `umsg_id` |
| `platform_core/agent/budget.py:86` | `run.id` |

Không cái nào ứng với một hàng `Job`. Bản thân `credit.giu_cho` đã lường trước
(`job = db.get(Job, job_id)`; `None` thì bỏ qua ghi sự kiện) — nên đây là trường
hợp **đã biết**, không phải tai nạn.

**(2) Vòng bảo trì không thu hồi giữ chỗ.** `_mot_luot_bao_tri` làm: dọn sự kiện
hết hạn, dọn dữ liệu theo retention, quét upload, giao webhook, ghi metrics, việc
nền của app, quét cảnh báo. **Không mục nào chạm `CREDIT_HOLD`.** Và mọi chỗ đọc
`CREDIT_HOLD` trong kho (`admin_console`, `usage`, `costing`, `budgets`,
`prompt_ai_ommi/overview`) đều là **truy vấn báo cáo** — không chỗ nào kết sổ.

**(3) Máy dò CÓ tồn tại, nhưng không được cắm vào đâu, và vị ngữ của nó bắt
hụt.** `platform_core/public_api/usage.py:170 reconcile()` đếm
`holds_without_job` và trả `ok: False` khi khác 0. Nhưng:

- nó chỉ được gọi từ **test** và từ **một lệnh CLI thủ công**
  (`tools/reconcile_public_api_usage.py`, mà `test_186:368` **chốt là chỉ-đọc**);
- vị ngữ là `CreditEntry.job_id == ""` — **rỗng**. Cả bốn đường ở (1) đều truyền
  id **khác rỗng**, và `thanh_toan.giu_cho_luot` còn `raise ValueError` nếu
  `request_id` rỗng.

⇒ **Chuông báo đã được đúc, chưa ai treo lên, và nó được chỉnh để nghe đúng thứ
âm thanh không bao giờ phát ra.**

**Vì sao không phải chuyện lý thuyết.** Cửa sổ hỏng bị mở **có chủ ý, mỗi lần
deploy**: `deploy-self.ps1` dừng `LTTStudioWeb`. Một luồng LLM đã đo được chạy
**119 giây** qua Cloudflare mà không bị 524. Cộng thêm Windows Update tự khởi
động lại máy. `finally` không chạy khi tiến trình bị giết.

Hậu quả với khách: số dư bị trừ, không có job nào để chỉ vào, không màn hình nào
giải thích, và sổ credit là **append-only** nên không tự lành.

⭐ **Và mã tự nói ra lỗ hổng của chính nó.** Chú thích tại `streaming.py:257`
viết nguyên văn: *"⚠️ Và KHÔNG AI QUÉT NÓ. Đường đồng bộ này không tạo `Job`, nên
`_hoan_credit` của worker không bao giờ nhìn thấy. Khách mất tiền lặng lẽ, và
không có báo cáo nào chỉ ra điều đó."*

Người viết bản vá **đã biết** lưới chỉ căng trong tiến trình, đã ghi lại, và việc
treo chuông vẫn chưa được làm. M-01 không phải một khám phá — nó là **một việc đã
biết mà chưa ai xếp lịch**.

**Đo lại — thứ tự này quan trọng, và nó KHÔNG đòi phá gì:**

**Bước 1 (làm được ngay, không phá hoại):** hai dòng mồ côi **đã nằm sẵn** trong
CSDL. Chạy:

```bash
python tools/reconcile_public_api_usage.py --days 3
```

Dự đoán: in `ok: True`, `holds_without_job: 0` — **máy dò báo sạch trong khi 2
credit đang kẹt**. Đây là E2 cho lỗi **"bắt hụt"**, lấy được mà không cần giết
dịch vụ nào. *(Lệnh này đọc CSDL production ⇒ thuộc phạm vi D-02.)*

**Bước 2 (cần chủ sản phẩm cho phép):** tái hiện cửa sổ khi giết tiến trình — gọi
`/api/v1/messages` dạng luồng rồi `Stop-Service -Force LTTStudioWeb`. Chỉ lỗi này
mới cần phép thử phá hoại, và **nên làm trên CSDL test**, không trên production.

⇒ Hai lỗi khác nhau, hai phép thử khác nhau, hai mức rủi ro khác nhau. Đừng gộp.

**Phương án (chưa chọn — Prompt 06/11 quyết):**

- **A. Sửa vị ngữ máy dò + cắm vào `_mot_luot_bao_tri`** dưới lease `bao_tri`,
  chỉ **báo**, không tự hoàn. Rẻ nhất, không đụng đường tiền, biến một lỗi vô
  hình thành một lỗi có tên. *(khuyến nghị làm trước)*
- **B. Thêm hạn cho giữ chỗ** (`hold_expires_at`) + bước thu hồi tự hoàn khi quá
  hạn. Đúng gốc hơn, nhưng đụng schema + đường tiền ⇒ cần test âm tính và quyết
  định của chủ sản phẩm.
- **C. Không làm gì, chấp nhận rủi ro có hạn.** Hợp lệ **chỉ khi** đo được số lượt
  thực tế bằng 0 — mà muốn đo thì vẫn phải làm A trước.

**Không được đổi:** khoá `_khoa_so_du_user` trước khi đọc số dư (chống
double-spend), tính append-only của sổ, và `quyet_toan_hoac_hoan`.

## II.5 Thẩm quyền cấu hình — sạch

**106** biến `LTT_*` đọc trong mã; **42** đặt trên production; **0** biến đặt trên
production mà mã không đọc. Không có cấu hình chết.

## II.6 Bề mặt giao diện

| Nơi | Số template |
|---|---|
| `server/templates` | 62 |
| 10 app có template | 19 (nhiều nhất: `agent` 4, `taoanh` 3) |
| 3 bộ React | `agent-canvas`, `autosub-studio`, `prompt-ai-ommi` |

**4 app không có giao diện web:** `anhnoibo`, `ltt_llm` (bán qua API), `nexus`
(app native), `vps` (dùng template ở `server/`).

## II.7 🔴 B-01 · P1 · E2_TEST — Gói phát hành hiện KHÔNG dựng được

`pytest tests/test_44_release_build.py -q` ⇒ **2 failed, 33 passed**.

```
SystemExit('frontend/agent-canvas bundle is stale or built with the wrong Node')
```

Ba bundle cũ so với `vite.config.ts`: `agent-canvas` **2026-08-08**,
`prompt-ai-ommi` **2026-08-11**, `autosub-studio` **2026-08-12**.

⚠️ **Và một lỗi che một lỗi khác.** Test thứ hai
(`test_secret_abort_path_reports_location_and_exits`) đỏ **không phải** vì đường
chặn bí mật hỏng, mà vì chốt bundle-cũ bắn trước và nuốt mất `SystemExit` mà nó
định kiểm. Nghĩa là **phép kiểm đường chặn rò rỉ bí mật hiện không được chạy** —
im lặng theo cách tệ nhất: trông như một lỗi build tầm thường.

Sửa: `npm run build` cả ba, rồi `python tools/build_system_profile.py`. *(Lệnh CÓ
tác dụng phụ — thuộc pha thi hành.)*

## II.8 🔴 O-02 · P1 · E1 — H40 đóng mà không có lượt gate đầy đủ nào

`docs/KE_HOACH_TRIEN_KHAI.md` §H40.7 ghi thẳng. Bốn lượt gate đều dừng giữa
chừng; **lượt thứ ba dừng vì chính phiên audit này chạy `pytest` song song
23:30–23:50** — đã ghi ở mục 4.1.

**Bằng chứng thật sự có** (trên cây `09ee8e9`): 9 phép kiểm tĩnh PASS · 15 cụm
pytest PASS · gõ thật 21/21 URL app đã gỡ → 404, 12/12 URL còn sống → 200/303.

**Bốn thứ CHƯA có bằng chứng — mức tin cậy thấp nhất:**

1. `pytest` toàn bộ **4.093** test trên cây cuối;
2. ba bộ test frontend trên cây cuối;
3. bất biến đa tiến trình (`tools/check_multiproc.py`);
4. kiểm trên trình duyệt thật.

---

### 🔴 P-01 · P1 · E1 — Khoảng cách giữa "đã biết" và "đã xếp lịch" không có ai canh

M-01 là **ca mẫu**, không phải ngoại lệ. Người viết bản vá `streaming.py:257`
ngày 25/08 đã biết lưới chỉ căng trong tiến trình, **đã viết ra bằng chữ**, ngay
trong mã. Chuông vẫn không được treo. Và một trong hai dòng tiền kẹt thì không ai
ghi ở đâu.

⇒ Vấn đề không nằm ở mã. Nó nằm ở chỗ **một việc đã biết không có đường vào lịch**.

Kho này có sẵn chỗ chứa: mục *"Còn tồn đọng"* ở cuối mỗi mục nhật ký
(`docs/NHAT_KY.md`). Nhưng nó là **ngõ cụt**: thứ vào đó mà không đồng thời vào
`docs/KE_HOACH_TRIEN_KHAI.md` thì không ai gặp lại nó nữa. Nhật ký được đọc theo
thời gian; kế hoạch được đọc theo việc. Việc chỉ nằm ở nhật ký là việc chỉ tồn
tại trong quá khứ.

**Phương án (rẻ, cơ khí):** một phép kiểm trong gate đọc mục *"Còn tồn đọng"* của
N mục nhật ký gần nhất và đòi mỗi gạch đầu dòng có một mã hạng mục ứng với một
dòng trong `KE_HOACH_TRIEN_KHAI.md`. Cùng họ với các bánh cóc đang có
(`check_bo_qua`, `check_dich_thieu`) — chặn tương lai, không dọn quá khứ.

**Vì sao đáng làm:** đây là **loại lỗi sinh ra M-01**, không phải bản thân M-01.
Sửa M-01 mà không sửa cái này thì lần sau vẫn thế, chỉ khác chỗ.

*(Phát hiện và đề xuất của phiên `lttstudiosapp-3a`.)*

---

## II.9 Bảng phát hiện hợp nhất

| ID | Mức | BC | Tóm tắt | Lane |
|---|---|---|---|---|
| ~~F-01~~ | P0 | — | Ba trạng thái hệ thống | ✅ `9bb8f85` |
| ~~F-02~~ | P0 | — | `settings.py` ngoài git | ✅ `9bb8f85` |
| ~~F-05~~ | P2 | — | docstring trỏ `apps/demo` | ✅ `09ee8e9` |
| ~~F-06~~ | — | E2 | `.po` trỏ tệp đã xoá | ✅ **giữ có chủ ý** |
| **M-01** | **P0** | **E4** | **2 credit đã kẹt thật trên production** (24/08, cả hai không có hàng Job). Lưới hoàn tiền chỉ căng trong tiến trình; deploy `Stop-Service -Force` giết tiến trình. Máy dò không được cắm **và** bắt hụt 0/2 | **12** |
| **B-01** | **P1** | **E2** | Gói phát hành không dựng được; che một phép kiểm bí mật | **12** |
| **O-01** | **P1** | E3 | Sao lưu dừng 8 ngày, không lịch, bí mật chưa sao lưu kiểm chứng được | **12** |
| **O-02** | **P1** | E1 | 4 khoảng trống bằng chứng của H40 | **15** |
| **A-02** | P2 | E1 | `server/api` biết tên `apps.ltt_llm` — phạm luật nền tảng tự viết | **13** |
| **A-04** | P2 | E1 | 72 cạnh `apps → server` qua 4 module: biên chưa khai báo | **13** |
| **A-01** | P2 | E1 | Cạnh xuyên-sản-phẩm duy nhất `taovideo → upscalevideo` | **13** |
| **S-01** | P2 | E1 | 8/11 app khách vẫn `development`; bề mặt MVP không do ai chọn | **02** |
| **D-01** | P2 | E1 | `CLAUDE.md` nói cửa API đóng; production mở 2 tool | **08** |
| **U-01** | P2 | E1 | 57/81 template style nội tuyến; `.page--catalog` mồ côi | **09/14** |
| **A-03** | P3 | E1 | `server → apps.anhnoibo`; chu trình `server ↔ tools` | **13** |
| **G-01** | P3 | E1 | `developer.py` 1.521 dòng/32 handler ngoài tầm lint | **13** |
| **F-07** | P2 | E1 | worktree thứ hai làm mọi phép quét đếm hai lần | **12** |
| **P-01** | **P1** | E1 | "Còn tồn đọng" ở nhật ký là ngõ cụt — việc đã biết không có đường vào kế hoạch. **Đây là loại lỗi sinh ra M-01** | **13** |

## II.10 Danh sách GIỮ NGUYÊN — bổ sung sau khi đo sâu

Thêm vào 8 mục ở Phần I:

9. **`platform_core → apps` = 0 cạnh**, xác minh AST trên 732 tệp. Đây là thứ
   khiến mọi việc còn lại chỉ cần sửa nhỏ.
10. **19/19 job_type có handler**, không mồ côi hai chiều.
11. **40 route không `Depends` đều có chốt riêng** — HMAC thiết bị có chống phát
    lại, bearer, chữ ký webhook trên thân thô, hoặc công khai có chủ ý.
12. **`relay_check` fail-closed**: biến rỗng ⇒ endpoint tắt, không mở toang.
13. **0 biến cấu hình chết** trên production.
14. **`_khoa_so_du_user` khoá hàng trước khi đọc số dư** — check-then-write thành
    nguyên tử ở tầng CSDL, không ở tầng route.

---

```text
LIVE_REPO_AUTHORITY_RESOLVED: YES  (cây 9848efa, sạch)
AUDIT_COMMANDS_SAFE:          YES  (6 lệnh tránh, mục 6)
NO_RUNTIME_CHANGE:            YES
DEEP_MEASUREMENT_DONE:        YES  (Phần II, 2026-08-26)
OPEN_P0: 1   (M-01 — tiền khách đã mất thật)
OPEN_P1: 4   (B-01, O-01, O-02, P-01)
OPEN_P2: 6   OPEN_P3: 2
```
