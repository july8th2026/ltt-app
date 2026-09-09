# CLAUDE.md — hợp đồng khởi động

Đọc tệp này trước khi làm bất cứ việc gì. Nó **ngắn có chủ ý**: nó chỉ chứa những
gì phải biết trong ba mươi giây đầu, rồi trỏ đi.

## ⭐ Trước việc thực chất, đọc

```
docs/00_LTT_OPERATING_CONTRACT.md
```

Đó là **nguồn chân lý duy nhất** cho quy trình: khi nào chạy test, cấp nào, sau
khi sửa phải làm gì, trước khi commit phải làm gì, worktree, deploy, nghiệm thu.

⛔ **Nếu một tệp `.md` nào khác định nghĩa lại quy trình đó, tệp đó SAI.** Đừng
làm theo, và đừng sửa hợp đồng cho khớp nó. Ghi vào
`docs/OPERATING_STANDARDIZATION/` rồi tiếp tục theo hợp đồng.

## Đây là gì

Nền tảng SaaS đa người dùng bán công cụ AI theo credit, chạy trên Windows. Mỗi
công cụ là một **app** ở một đường dẫn dưới `app.lttstudios.com`. Ra Internet qua
**Cloudflare Tunnel**.

Nguồn chân lý về **sản phẩm** là `docs/QUYET_DINH_NEN_TANG.md`, rồi
`docs/KE_HOACH_TRIEN_KHAI.md` và `docs/NHAT_KY.md`. Định vị code thì đọc **chính
mã nguồn**: `grep`/`Glob` trên `apps/`, `platform_core/`, `server/`.

---

# 20 luật cứng

### Định hướng

1. **Trước việc thực chất: đọc `docs/00_LTT_OPERATING_CONTRACT.md`**, rồi hỏi
   cây bạn đang đứng: `python tools\ho_so_cay.py trang-thai` (một lệnh, không
   chạy test). Nó nói cây này ở hồ sơ `NORMAL` hay `FAST_BUILD` (§4.10) và
   **governance của nó có lệch trunk không** — lệch thì gộp trunk trước khi tin
   một luật hay một lượt gate ở đây.
2. **Đừng tự sáng tạo quy trình.** Thiếu luật thì ghi đề xuất, tiếp tục theo luật
   hiện có, **không** đẻ ra một luật cạnh tranh trong tệp kế hoạch của bạn.
3. **Đừng đọc cả kho.** Thứ tự: KHÁM PHÁ → ĐẾM → LỌC → PHÂN LOẠI → NHẮM → ĐỌC.
   `docs/` có **872 tệp `.md`** và **788 tệp ảnh (90 MB)**. Không nạp sản phẩm
   build, log, cache, kết xuất sinh ra, dữ liệu vận hành.
4. **Đang ở máy nào?** `Test-Path C:\LTTPlatform` → **Có**: đây là máy chủ, đang
   chạy thật, cẩn thận. **Không**: máy phát triển, hoặc máy chủ chưa cài — hỏi.
5. **Cái gì đang sống thì HỎI MÁY CHỦ**, đừng đọc một bảng chép tay:
   `python tools\api_prod_canary.py trang-thai`. Một bảng chép tay không có cách
   nào tự biết nó đã cũ — bảng cũ ở đây đã nói sai **năm lần**, cả năm đều về
   phía nguy hiểm.

### Test và cổng chất lượng — chi tiết ở hợp đồng §4

6. **Mặc định của vòng lặp là `python tools\gate.py --doi`** (L1) — chỉ chạy test
   chạm tới thứ bạn vừa sửa, và tự hạ cấp xuống đầy đủ khi không chắc.
7. ⛔ **KHÔNG chạy gate đầy đủ sau mỗi lần sửa.** Gate là công cụ ra **PHÁN
   QUYẾT**, không phải công cụ **CHẨN ĐOÁN**. Đo thật: L3 trung vị **11,4 phút**
   trên 43 lượt — không phải "5 phút".
8. **Trước khi báo xong: `python tools\gate.py`** đầy đủ. Mọi chế độ khác đều tự
   khai ở dòng `RESULT` rằng chúng **không phải bằng chứng**.
9. ⛔ **Đừng gọi `pytest` trực tiếp cho toàn kho** — nó bỏ qua test frontend, nên
   "full regression xanh" sẽ là một câu nói sai.
10. ⛔ **`test_nhanh.py` rồi `gate.py` là trả tiền HAI LẦN.** Bước `bo test` bên
    trong gate *chính là* `test_nhanh.py`.
11. **Trước mọi lệnh nặng:** `python tools\cua_so_yen.py trang-thai`. Có phiên
    khác đang giữ thì **chờ**. Đây là điều kiện *cần*, không phải *đủ* —
    `docs/QUY_TAC_CHAY_LENH_NANG.md`.

### Nhiều phiên — cây này KHÔNG phải của riêng bạn

12. **Một dòng `??` lạ trong `git status` là một PHIÊN KHÁC đang làm việc**, không
    phải rác. Không `stash`, không `checkout --`, không `reset`.
13. **`git add` tường minh từng tệp.** Không `-A`, không `.`.
14. **Tệp dùng chung (`CLAUDE.md`, `AGENTS.md`, `tools/gate.py`, `messages.po`)
    chỉ sửa bằng `Edit`, không bao giờ `Write`** — `Write` đè im lặng cả tệp.
15. **Deploy chép CẢ CÂY nguồn.** Không tách được phần của một phiên ⇒ hỏi phiên
    khác trước (`ListAgents`). `docs/16_CAP_NHAT_VA_DEPLOY.md`.

### Kỹ thuật — sẽ cắn nếu quên

16. **Ghi file cấu hình phải KHÔNG BOM**; **`.ps1` thuần ASCII**; **đừng viết
    Python inline qua PowerShell**. Cả ba đã thực sự làm sập production ở dự án
    này. Toàn văn + luật thứ tư: `AGENTS.md` §5.

    ```powershell
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
    ```

    ⛔ Đoạn mã này nằm ở đây chứ không chỉ ở `AGENTS.md` vì lời văn *"phải không
    BOM"* **không ngăn được** lỗi: `Out-File -Encoding utf8` trông đúng và vẫn
    chèn BOM, `json.load()` vỡ, `/health/ready` trả 503 trong khi dịch vụ vẫn
    chạy. Người đọc cần biết viết **thế nào**, không chỉ biết **đừng** làm gì.
    `tests/test_61_setup_scripts.py::test_claude_md_exists_at_root` ghim đúng
    chuỗi này.
17. **Kiểm bằng trình duyệt sau mỗi thay đổi giao diện**, và chốt trên **URL công
    khai** (`https://app.lttstudios.com`), không chỉ loopback `127.0.0.1:8100` —
    loopback bỏ qua Cloudflare (cache, CSP biên, minify).
18. **Đổi static (CSS/JS) phải cache-bust.** `ltt.css` đính `?v={{ asset_ver }}`
    (`server/templating.py:ASSET_VER`). Thêm asset tĩnh MỚI ở nơi dựng HTML bằng
    chuỗi (vd `server/admin.py`) cũng phải đính version.
19. **Việc dài hơn vài giây phải đi qua hàng đợi job.** Cloudflare: upload
    **100 MB**/request, chờ phản hồi **100 giây**.
20. **Thêm app mới = thêm MỘT thư mục vào `apps/`.** Không sửa `platform_core/`
    hay `server/`. Buộc phải sửa nền tảng ⇒ **dừng lại và nói rõ vì sao** — đó là
    dấu hiệu hợp đồng app còn thiếu. `docs/03_THEM_APP_MOI.md`, `AGENTS.md` §8.

---

## ⭐ CHƯA CÓ KHÁCH ở lớp Agent/Canvas — đừng tiêu công vào rà soát khách hàng

Chủ sản phẩm chốt **07/09/2026**: *"Hệ thống không có khách nên không cần tra rà
soát hay lo ngại vấn đề liên quan."*

⇒ **Đừng** rà soát tương thích ngược, chia pha, bật cờ từ từ, viết lớp tương
thích cho dữ liệu cũ khi chưa có dữ liệu cũ nào, hay nêu "khách sẽ gặp lỗi" như
lý do không làm. Thấy một thiết kế sai thì **sửa thẳng**.

### ⚠️ Phạm vi thật — đo được, đừng suy rộng

Đo 28 ngày (11/08 → 07/09) từ `C:\LTTPlatform\logs\ltt-job-worker*.jsonl`:
**10.663** lượt `ltt_llm.chat` · **1.075** `anhnoibo.generate` · **147**
`ltt_voice.synthesize` · **0** job `agent.advance`.

⇒ Có lưu lượng thật và **bút toán credit thật**. Cái *thật sự* không có khách là
lớp **Agent/Canvas/Workflow** — tự do thiết kế lại. Còn `credit.py`, `jobs.py`,
`job_runner.py`, `gpu_lease.py` **đang chạy thật**: vẫn sửa được, nhưng lý do cẩn
thận ở đó là **tính đúng của sổ sách**. Đừng dùng câu "chưa có khách" để bỏ qua
một bút toán lệch.

#### 🔑 `0 job` nói KHÔNG AI CHẠY — nó không nói KHÔNG AI ĐÃ DỰNG

Đếm thẳng trên CSDL production (08/09/2026, chỉ đọc):

```
agent_workflows 10 · agent_runs 4 · agent_workflow_snapshots 83
doi chung: users 27 · jobs 1770 · credit_entries 5500
```

Con số `0 job agent.advance` ở trên **đúng**. Nhưng nó trả lời câu *"có ai chạy
không"*, còn câu người đọc rút ra là *"có ai dựng không"* — hai câu khác nhau,
và **mười người thật đã dựng**.

⇒ Quyền ở trên **không đổi**: vẫn tự do thiết kế lại lớp Agent/Canvas/Workflow,
  vẫn không phải viết lớp tương thích runtime (`0 run` ⇒ không có trạng thái thi
  hành nào để chuyển). Thứ **đổi** là một chữ: *"thiết kế lại"* ≠ *"xoá"*. Bản
  nháp của họ đi qua `platform_core/workflow/di_tru_m1.py`, không đi ra thùng rác.

⚠️ Và đừng suy *cách làm* từ con số **tổng** ấy — đó là lỗi thứ hai của cùng một
   ngày. Tổng nói được **có làm hay không**; chỉ **hình dạng** nói được **làm thế
   nào**: 10/10 mang tên mặc định, ≤3 node, và **4/10 `document` rỗng** — tức
   việc di trú phải xử ba lớp chứ không một. Toàn văn:
   `docs/architecture/workflow_v2_audit/27_29 §27.1`.

### ⛔ Bốn thứ KHÔNG phải chuyện khách hàng, nên vẫn giữ

| | Vì sao |
|---|---|
| **Gate phải xanh trước khi báo xong** | Bảo vệ **ta** khỏi mất thời gian |
| **Xoá dữ liệu không đảo được** | "Chưa có khách" không làm một lệnh `DROP` đảo lại được |
| **UAC** | Ràng buộc **cơ học** — người dùng phải bấm chuột |
| **Hỏi phiên khác trước khi deploy** | Deploy chép **cả cây** |

⚠️ Quyền này hết hiệu lực ngày có khách trả tiền thật.

---

## Máy chủ

Bố cục sau khi cài: `app\` (**bị xoá và thay TOÀN BỘ mỗi lần cập nhật**) ·
`app.previous\` · `data\` · `secrets\` · `venv\` · `cloudflare\` · `logs\` · `tools\`.

⛔ **Đừng bao giờ sửa file trực tiếp trong `app\`** — lần cập nhật sau là mất
trắng, **âm thầm**. Sửa trong thư mục nguồn rồi chạy lại `setup\2-cai-dat.ps1`.

Cài lần đầu: `docs/01_COPY_LEN_SERVER.md`. Bước 2 in mật khẩu admin **đúng một
lần**. Bước 3 dừng chờ đăng nhập Cloudflare — đưa link cho người dùng, **đừng
ngắt lệnh vì tưởng nó treo**.

## ⛔ Không bao giờ commit hay copy đi

```
data/config.json   data/*.enc   secrets/   cloudflare/config.yml   cloudflare/*.json
```

⚠️ **`D:\BOT GEMINI` là kho tham chiếu CHỈ ĐỌC** — đang phục vụ người dùng thật
trên cổng 8000. Nền tảng này dùng cổng **8100**.

⛔ **`D:\LTTBackups` — ACL chặn ở đó là CỐ Ý.** Thấy `Access denied` mà chạy
`icacls` để mở ra là **gỡ một bản vá bảo mật đã hoàn thành** (W1.5,
`docs/AUDIT_MVP_2026-07-31.md`).

## Tài liệu

| Tệp | Nội dung |
|---|---|
| **`docs/00_LTT_OPERATING_CONTRACT.md`** | **quy trình canonical — đọc trước** |
| `AGENTS.md` | quy ước kỹ thuật: Windows, bố cục app, memory, hai phiên cùng cây |
| `docs/DEVELOPMENT_WORKFLOW.md` | nhiều phiên song song, cây riêng, phạm vi |
| `docs/16_CAP_NHAT_VA_DEPLOY.md` | đồng bộ → gate → ff → deploy → đẩy GitHub |
| `docs/QUY_TAC_CHAY_LENH_NANG.md` | bốn bước trước mọi lệnh nặng |
| `docs/QUY_TRINH_WORKTREE.md` | trước khi tạo hay gỡ worktree |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | 17 cái bẫy trong chính cổng chất lượng |
| `docs/03_THEM_APP_MOI.md` | thêm app |
| `docs/04_CLOUDFLARE_TUNNEL.md` | Tunnel + xử lý sự cố |
| `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` | app/tool/model nào mở, nào đóng, **vì sao** |
| `docs/_luutru/PROJECT_MEMORY.md` | nhật ký — **cập nhật cuối mỗi phiên** |

### Luật của từng hệ con — con trỏ, không phải giá trị

⚠️ **Đừng gõ lại một con số nào từ các tệp dưới vào đây.** Đó chính xác là cơ chế
đã hỏng năm lần.

| Hệ con | Nguồn chân lý |
|---|---|
| Sổ credit · thanh toán | `platform_core/credit.py`, `billing.py` |
| Hàng đợi job · worker · lease | `platform_core/job_runner.py`, `leases.py` |
| Public API `/api/v1` | `platform_core/public_api/`, `server/api/inventory.py` |
| Khoá API · provider | `platform_core/api_pool.py`, `providers.py` |
| Model ảnh nội bộ (máy B) | `render_gateway/ngan_sach.py`, `apps/anhnoibo/gia.py` |
| LLM nội bộ (máy B) | `apps/ltt_llm/ngan_sach.py` |
| LTT VOICE | `apps/ltt_voice/tham_so_cong_khai.py` |
| Bán VPS | `apps/vps/services/mang.py`, `apps/vps/bao_tri.py` |
| LTT Nexus | `nexus_agent/`, `platform_core/nexus/` |
| Lưu trữ · R2 | `platform_core/storage.py` |
| Cây riêng · cổng chất lượng | `tools/cay_rieng.py`, `tools/gate.py`, `tools/thanh_phan.py` |
