# CLAUDE.md — bản đồ khởi động

Nền tảng SaaS đa người dùng bán công cụ AI theo credit, chạy trên Windows. Mỗi công
cụ là một **app** dưới `app.lttstudios.com`, ra Internet qua **Cloudflare Tunnel**.

Tệp này **chỉ là bản đồ + luật chết người**. Mọi quy trình nằm ở:

```
docs/00_LTT_OPERATING_CONTRACT.md      ← đọc trước việc thực chất
```

⛔ Tệp nào khác định nghĩa lại quy trình là **sai** — làm theo hợp đồng.

## Mỗi câu hỏi hỏi đúng MỘT chỗ

| Câu hỏi | Hỏi ở đâu |
|---|---|
| Làm việc thế nào: test, gate, git, gộp `main`, khi nào dừng | `docs/00_LTT_OPERATING_CONTRACT.md` |
| Sản phẩm đã chốt gì | `docs/QUYET_DINH_NEN_TANG.md` → `docs/KE_HOACH_TRIEN_KHAI.md` |
| Chuyện gì đã xảy ra (nhật ký sống) | `docs/NHAT_KY.md` — **ghi cuối mỗi phiên có thay đổi** |
| Cái gì đang sống trên production | `python tools\api_prod_canary.py trang-thai` — không bảng chép tay |
| **Máy A và máy B** làm gì, máy nào có card gì (⚠️ **cả hai đều có một 5060 Ti**) | `docs/HAI_MAY_A_VA_B.md` |
| Cây này ở hồ sơ nào, lệch `main` không | `python tools\ho_so_cay.py trang-thai` |
| Viết mã đúng kiểu (Windows, bố cục app, bí mật, cách viết test) | `AGENTS.md` |
| Worktree · lệnh nặng · deploy | `docs/QUY_TRINH_WORKTREE.md` · `docs/QUY_TAC_CHAY_LENH_NANG.md` · `docs/16_CAP_NHAT_VA_DEPLOY.md` |
| Bẫy đã gặp, bài học đo lường | `docs/BAY_TRONG_CONG_CHAT_LUONG.md` |
| Mã ở đâu | `grep`/`Glob` trên `apps/`, `platform_core/`, `server/` — đừng đọc cả kho |

# Luật chết người

1. **Test/gate** — hợp đồng §4. Đúng một nhịp:

   ```
   TRONG PHIÊN    test NHẮM cụm vừa sửa: thanh_phan.py --test <tp> -> python -m pytest <tệp> -q
                  cần gate -> CHỈ L1 (gate.py --doi) hoặc L2 (gate.py --pham-vi <tp>)
                  ⛔ KHÔNG L3 giữa các pha (không rải rác, không "chốt pha")
                  ⛔ L1/L2 KHÔNG BAO GIỜ tự nâng lên L3 (chốt 24/09): không thu hẹp
                     được thì HẠ CẤP xuống `nhanh` — giữ mọi bước tĩnh, bỏ bộ test
                     đầy đủ, và KHAI RA rằng bộ test không được phủ
   GẶP LỖI        sửa TẠI CHỖ -> chạy lại ĐÚNG phép đã đỏ -> đi tiếp
   GỘP main       giữa phiên: test nhắm xanh là ĐỦ — ⛔ không L3 để gộp
   XONG MỘT PHASE test nhắm xanh -> gộp `main` -> phase kế. ⛔ KHÔNG gate để
                  "đóng phase" (chủ dự án chốt 24/09: **L1 chỉ chạy ở CUỐI PLAN**)
   KẾT THÚC PHIÊN (hết PHIÊN LÀM VIỆC — ⛔ không phải hết một phase, task,
                  nhánh hay một lần gộp `main`)
                  commit hết -> build frontend nếu đổi -> kiểm máy (luật 3)
                  -> python tools\gate.py (L3) MỘT lần, không ghi vào cây trong lúc chạy
   L3 ĐỎ          sửa tại chỗ -> chạy lại đúng phép đỏ (gate in sẵn) -> KHÉP gate.py --doi --tu <sha L3>
   DEPLOY         được deploy BẤT CỨ LÚC NÀO việc xây dựng cần — kể cả giữa phiên — khi đã có
                  gate xanh trên đúng SHA deploy: giữa phiên L1/L2 · tổng kết phiên L3 (xanh/đỏ đã khép)
                  ⛔ không chạy L3 để deploy · test nhắm một mình không đủ để deploy
   ```

   ⛔ **Một L3 mỗi nhánh** — `gate.py` từ chối L3 thứ hai kể cả sau L3 xanh, và từ chối
   L1/L2 giữa phiên tự nâng lên đầy đủ. Còn việc chưa làm ⇒ **chưa bấm L3**. Lượt bị
   ngắt giữa chừng (không có bản ghi) chưa phải phán quyết ⇒ chạy lại được.
2. **Không dừng giữa các pha** — xong một pha thì làm tiếp pha kế, không xin phép; hết
   **mọi** pha thì L3 → gộp `main` → deploy (nếu cần) → báo. Pha nào cần deploy để xây
   tiếp (đo thật, E2E) thì L1/L2 xanh → gộp `main` → deploy → báo, rồi làm tiếp — không dừng.
   Chỉ dừng khi: gate đỏ · thao tác không đảo được · thay đổi không rõ của ai · rủi ro
   bảo mật (hợp đồng §10, §10b).
3. **Kiểm CPU trước lệnh nặng**: `python tools\cua_so_yen.py trang-thai` (có người
   giữ khoá → chờ) + `python tools\tai_may.py` (`QUÁ TẢI` → chờ).
   ⛔ **Lệnh nào là "nặng" thì hỏi `docs/QUY_TAC_CHAY_LENH_NANG.md` §1** — chỉ nơi
   đó định nghĩa (phân loại theo **khả năng đốt CPU**, không theo số tệp test).
   Trần `-n` là `gate.TRAN_N_GO_TAY` — đọc hằng số, ⛔ đừng gõ lại số.
4. **Dòng `??` lạ trong `git status` là một PHIÊN KHÁC**, không phải rác. Không
   `stash`, `reset`, `checkout --`. `git add` tường minh từng tệp.
5. **Deploy xuất HEAD cây chính** (`git archive` — mọi commit trên `main` của mọi phiên)
   ⇒ báo các phiên đang chạy trước (`ListAgents`).
6. **Ghi cấu hình KHÔNG BOM** · `.ps1` thuần ASCII · không viết Python inline qua
   PowerShell. Cả ba đã làm sập production. Toàn văn: `AGENTS.md` §5.

   ```powershell
   [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
   ```

7. **Đổi giao diện** ⇒ kiểm bằng trình duyệt, chốt trên `https://app.lttstudios.com`
   (loopback bỏ qua Cloudflare). **Đổi CSS/JS tĩnh** ⇒ cache-bust (`?v={{ asset_ver }}`,
   `server/templating.py:ASSET_VER`).
8. **Việc dài hơn vài giây đi qua hàng đợi job** — Cloudflare cắt upload 100 MB và
   phản hồi 100 giây.
9. **Thêm app = thêm MỘT thư mục `apps/`.** Buộc sửa `platform_core/`/`server/` ⇒
   dừng và nói rõ vì sao (`docs/03_THEM_APP_MOI.md`, `AGENTS.md` §8).
10. **Gặp vấn đề: tra nguồn TRƯỚC khi tự suy** — model card, tài liệu engine, và
    cộng đồng GitHub qua **plugin GitHub MCP** (`search_issues` trong repo thư viện,
    `search_code`, `get_file_contents`); trích số issue/PR làm nguồn. Hợp đồng §1b.

## Chưa có khách ở lớp Agent/Canvas/Workflow

Chủ sản phẩm chốt 07/09/2026: lớp **Agent/Canvas/Workflow** tự do thiết kế lại — đừng
rà soát tương thích ngược, chia pha bật cờ hay viết lớp tương thích. *"Thiết kế lại"*
≠ *"xoá"*: bản nháp người dùng đã dựng đi qua `platform_core/workflow/di_tru_m1.py`.
⛔ `credit.py`, `jobs.py`, `job_runner.py`, `gpu_lease.py` **có lưu lượng và bút toán
thật** — sửa được, nhưng giữ đúng sổ sách. Quyền này hết khi có khách trả tiền thật.

## Máy chủ

Đang ở máy chủ nếu `Test-Path C:\LTTPlatform`. Bố cục: `app\` (**bị thay TOÀN BỘ mỗi
lần cập nhật** — ⛔ đừng sửa trực tiếp) · `app.previous\` · `data\` · `secrets\` ·
`venv\` · `cloudflare\` · `logs\` · `tools\`. Sửa ở thư mục nguồn rồi chạy lại
`setup\2-cai-dat.ps1`. Cài lần đầu: `docs/01_COPY_LEN_SERVER.md`.

⛔ **Không bao giờ commit hay copy đi:** `data/config.json` · `data/*.enc` · `secrets/` ·
`cloudflare/config.yml` · `cloudflare/*.json`.

⛔ `D:\BOT GEMINI` là kho tham chiếu **CHỈ ĐỌC** (đang phục vụ thật, cổng 8000; nền tảng
này cổng 8100). ⛔ ACL chặn ở `D:\LTTBackups` và `secrets\` là **CỐ Ý** — đừng `icacls`.

## Luật của từng hệ con — con trỏ, không phải giá trị

| Hệ con | Nguồn chân lý |
|---|---|
| **LLM nội bộ — đường đi** (đọc TRƯỚC khi sửa) | `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` |
| Sổ credit · thanh toán | `platform_core/credit.py`, `billing.py` |
| Hàng đợi job · worker · lease | `platform_core/job_runner.py`, `leases.py` |
| Public API `/api/v1` | `platform_core/public_api/`, `server/api/inventory.py` · `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` |
| Khoá API · provider | `platform_core/api_pool.py`, `providers.py` |
| Model ảnh nội bộ (máy B) | `render_gateway/ngan_sach.py`, `apps/anhnoibo/gia.py` |
| LLM nội bộ (máy B) | `apps/ltt_llm/ngan_sach.py` · nghiệm thu tải: `docs/VAN_HANH_THAT.md` |
| LTT VOICE | `apps/ltt_voice/tham_so_cong_khai.py` |
| Bán VPS | `apps/vps/services/mang.py`, `apps/vps/bao_tri.py` |
| LTT Nexus | `nexus_agent/`, `platform_core/nexus/` |
| Lưu trữ · R2 | `platform_core/storage.py` |
| Cloudflare Tunnel | `docs/04_CLOUDFLARE_TUNNEL.md` |
| Cây riêng · cổng chất lượng | `tools/cay_rieng.py`, `tools/gate.py`, `tools/thanh_phan.py` |
