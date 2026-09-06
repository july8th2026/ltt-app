# LTT VIDEO V2.1 — PROJECT STATE

> Khuôn: `PROJECT_STATE_TEMPLATE.md` của pack
> `LTT_VIDEO_WANGP_ONE_ENGINE_PROMPT_PACK_V2_1` (G:\My Drive\AI\A LTT AII\).
> **Tệp này là bộ nhớ giữa các phase.** Chat mới đọc tệp này trước, không đọc
> lại lịch sử chat cũ.
>
> ⛔ Đừng chép số hiệu commit, giá tiền hay tham số vào đây bằng tay nếu nó có
> một nguồn sống ở nơi khác — ghi **con trỏ** tới nguồn đó. Chương trình V3
> trước đã mất hai ngày vì một bảng chép tay không tự biết nó đã cũ.

## Trạng thái

- **phase:** `P01` — Pin + Vanilla WanGP C-CLOUD POC
  *(P00 đã đóng PASS — mục `Cổng nghiệm thu P00` giữ nguyên bên dưới)*
- **status:** **P01 ĐANG CHẠY lượt GPU.** Chủ dự án duyệt chi 06/09.
  Pod `bly29qwp5bum3r` (A100 80 GB, `US-KS-2`, 251 GB RAM, 32 vCPU) —
  ⚠️ giá **THẬT $1,59/giờ**, không phải $1,39 như `lowestPrice` báo trước.
  Trần đã duyệt **$6,00**. Hồ sơ: `P01_UPSTREAM_PIN.md`,
  `P01_TRIEN_KHAI_THEO_WANGP.md`.
  ✅ Cài đặt XONG trên volume (`_CAI_DAT_XONG`): torch 2.10.0+cu128 ·
  `mmgp` 3.7.14 · `sageattention` 2.2.0 · A100 sm 8.0 · 85,09 GB VRAM.
  ✅ Đã bắt được `settings_t2v_2_2.json` + `settings_i2v_2_2.json` —
  **chính là Verified Baseline Profile**, lấy bằng `get_default_settings()`
  chứ không phải bấm tay trong WebUI.
- **luật một-phase-một-chat:** ⛔ **ĐÃ GỠ 06/09** theo yêu cầu chủ dự án. Các
  phase chạy liên tục trong một phiên. ⚠️ Tệp state này **quan trọng hơn** chứ
  không kém đi: nó vẫn là thứ phiên sau đọc, và giờ không còn ranh giới chat để
  ép cập nhật — nên **cập nhật ngay khi có kết quả**, đừng dồn tới cuối.
- **branch:** `phien/video-v2-wangp`
- **worktree:** `D:\LTTSTUDIOSAPP\.claude\worktrees\video-v2-wangp`
- **base_commit (trunk lúc tách):** `06017841` trên `admin-mvp-v3`
- **head:** ⚙️ hỏi `git -C <worktree> log -1 --format=%h`, đừng chép vào đây
- **trunk thật:** **`admin-mvp-v3`**, **không** phải `master`
  — đo được: `git rev-list --left-right --count master...admin-mvp-v3` → `0 216`.
  `master` đứng ở `d225a480` (03/09), tụt sau trunk **216 commit**.
  ⇒ Worktree V2 tạo từ `admin-mvp-v3` theo `docs/QUY_TRINH_WORKTREE.md` luật 1.
- **wangp_upstream_sha:** ✅ **`1e1dd2757f24923f008593d9d4ec09062234be20`**
  — `deepbeepmeep/Wan2GP`, commit 2026-09-05. Hash từng tệp:
  `P01_UPSTREAM_PIN.md` mục 1.
- **wangp_patch_sha:** *(chưa — chưa fork, chưa vá. `P01-D-01`: không lấy GUI)*
- **wangp_license:** 🔴 **`WanGP Community License 2.0`** — **không** phải
  Apache-2.0 (GitHub gắn nhãn `NOASSERTION`). **PASS cho dùng nội bộ**
  (§1.8, §1.9(i), §3.3, §7.1); **CHẶN việc bán ra ngoài** (§5.2(g), §7.2).
  Trích dẫn đầy đủ: `P01_UPSTREAM_PIN.md` mục 2. Quyết định: `P01-D-05`.
- **video_engine_target:** **WanGP** (D-V2-001)
- **new_v2_runtime_fallback_to_legacy:** **FORBIDDEN** (D-V2-010)
- **commercial_gate:** **CLOSED** (D-V2-011) — nội bộ, `public=False`,
  `api_exposed=False`
- **b_lan:** **UNTOUCHED** (D-V2-008) — P00 không đọc, không ghi, không ping máy B
- **legacy_runtime_source:** **PRESENT — nhưng KHÔNG nằm trên trunk.**
  Toàn bộ runtime V3 sống trên nhánh `claude/ltt-video-ai-v3-p00-3f5713`, và
  nhánh đó **đã dừng phát triển 06/09** (`P00-D-07`). Loại bỏ ở **P06**, sau khi
  P05 PASS. Chi tiết + bằng chứng: `LEGACY_INVENTORY.md`.
- **legacy_restore_ref:** *(chưa tạo — P03 tạo `video-legacy-final-pre-wangp`)*
- **integration_transport:** **OPEN** (`O-001`: MCP trực tiếp vs cầu HTTP mỏng)
  — chốt sau bằng chứng P02
- **cloud_resources:** ⚠️ **có tài nguyên trả tiền ĐANG SỐNG, của V3, chưa đụng**
  — xem mục *Cloud* bên dưới
- **baseline_profiles:** *(chưa — sinh ở P02)*
- **max_quality_profiles:** *(chưa — sinh ở P07)*
- **spend_phase:** **$0,00** — P00 không dùng GPU, không gọi API tính tiền
- **tests:** không thêm/sửa test ở P00 (thay đổi chỉ là tài liệu)
- **gates:** `gate.py` đầy đủ trong worktree V2 → **`FAIL (3/26)`**, nhưng **cả
  ba bước đỏ đỏ y hệt trên trunk** khi không có nhánh này (đối chứng đã chạy).
  Nhánh V2 thêm 0 lỗi. Chi tiết + lệnh tái hiện: *Cổng chất lượng kho*.
- **browser_checks:** **N/A** — P00 không đổi GUI, route hay tài sản tĩnh
- **blockers:** xem *Blockers*
- **decisions:** `DECISIONS.md`
- **exact_next_action:** **chờ chủ dự án duyệt chi ~$2,80 (trần $5,00)** cho
  lượt POC GPU của P01 — xem *Kế hoạch chi P01*. Duyệt xong thì chạy tiếp P01
  mục 5–9; **không** nhảy sang P02.
  ➕ Kèm theo lượt đó: chốt **giữ hay bỏ volume `uizchbiet5`** (~$21/tháng), vì
  chỉ lúc boot WanGP thật mới biết nó cần model nào. `P00-D-07`.
- **spend_phase (P01):** ⚙️ hỏi `python tools/video_cloud.py trang-thai` —
  đừng chép số vào đây. Mốc: pod tạo `2026-09-06T08:30:28Z`, $1,59/giờ.
  ⚠️ Hoá đơn RunPod **trễ 20–60 phút**; số cuối cùng phải đọc lại sau.
- **legacy_cloud_data:** 🔴 **ĐÃ XOÁ 06/09** — 10 đối tượng / **183,09 GB** model
  ComfyUI của V3 xoá khỏi volume để lấy chỗ cho WanGP (chủ dự án duyệt).
  Lưới khôi phục commit **trước** khi xoá: `4e209c08`,
  `docs/VIDEO_AI_V2/khoi_phuc/`. Tái tạo ≈ 63 phút + ~$0,20. Xem `P01-D-11`.
- **audit 06/09:** **LOGIC AUDIT: PASS.** 43 tệp đổi, **0 tệp** trong
  `apps/`/`platform_core/`/`server/`. Không vi phạm quyết định khoá nào.
  Hai mục nghiệm thu của pack đã **bỏ có căn cứ** (`P01-D-09`): WebUI vận hành
  và MCP entrypoint — chúng xác minh bề mặt mà kiến trúc này đã quyết không dùng.
  Dữ liệu sinh video của lượt này là **bằng chứng thu sớm**, ⛔ không phải
  P02 PASS (`P01-D-10`).

## Cloud — tài nguyên trả tiền đang sống (thừa kế từ V3)

⛔ **P00 không tạo, không xoá, không đụng gì.** Ghi lại vì `COST_AND_SAFETY.md`
đòi kiểm kê **trước** khi có compute trả tiền, và vì hai tài nguyên này đang
tính tiền trong lúc chương trình V2.1 khởi động.

Kiểm kê **đo lại ở P01** bằng `python tools\video_cloud.py kiem-ke` (chỉ đọc,
chạy từ worktree V3 nơi có công cụ + khoá):

| Tài nguyên | ID | Tên **thật** | Trạng thái | Tiền |
|---|---|---|---|---|
| Network volume | `uizchbiet5` | **`lttv-models-v1`** | 300 GB, `US-KS-2` | ~**$21/tháng**, cố định |
| Endpoint Serverless | `uwzftpd3utftfn` | **`lttv-worker`** | `workersMin=0` | ~$0 khi rảnh |
| **Pod** | — | — | **0 — không compute nào chạy** ✅ | $0 |
| Tài nguyên mồ côi | — | — | **0** ✅ | — |

⚠️ **Sửa lỗi của chính tệp này ở P00:** tôi từng ghi volume tên
`lttvideo-models-v1` và endpoint `lttvideo-worker` — **chép từ tài liệu V3**. Tên
thật là **`lttv-models-v1`** và **`lttv-worker`**; tiền tố đã đổi thành `lttv-`
từ `V-002` mà tài liệu V3 không cập nhật hết. Đúng lỗi *"đọc thứ đại diện thay vì
đọc thứ thật"*, và nó lọt vào chính tệp tôi viết ra để chống điều đó.

- Số dư RunPod và mức chi **không chép vào đây** — hỏi
  `python tools\video_cloud.py trang-thai` **trên nhánh V3** (công cụ chỉ tồn
  tại ở đó). Ảnh chụp có ngày tháng: `P01_UPSTREAM_PIN.md` mục 4.
- 🔴 **Sàn credit:** số dư RunPod về $0 thì volume bị **xoá không khôi phục
  được**. Quyết định giữ hay bỏ volume 300 GB là một quyết định **của chủ dự
  án**, thuộc P06 (cutover), không phải của P00.

## Kế hoạch chi P01 — CHỜ DUYỆT

P01 mục 5–9 (boot WanGP thật, kiểm WebUI/API/MCP/queue/cancel, rồi tắt) cần thuê
GPU thật. Luật thường trực của dự án giữ lại ba ranh giới — *deploy, **bút toán
tiền**, UAC* — nên phiên này dừng ở đây.

### Tiền thật (đo 2026-09-06, kỳ 01/09→06/09)

| | |
|---|---|
| Số dư | **$45,35** |
| Sàn credit **không được tiêu** | **$31,50** — về $0 là RunPod **xoá volume vĩnh viễn** |
| ⇒ tiêu được | **≈ $13,85** |
| Đang chảy | **$0,0290/giờ** = volume, liên tục, kể cả khi không ai dùng |

🔴 **Đừng dùng dòng "2,9 giờ GPU mua được"** của công cụ V3: nó chia $13,85 cho
hằng số **$4,79/giờ** (giá **Serverless Flex** mà `V-017` đo). P01 thuê **Pod**,
giá khác hẳn — cùng số tiền mua được **~10 giờ** A100. Cùng cơ chế `V-017`: một
hằng số đúng cho ngữ cảnh này bị dùng cho ngữ cảnh khác, không có gì đỏ lên.

### 🔴 Ràng buộc quyết định giá: US-KS-2 chỉ còn HAI loại GPU

Volume nằm ở `US-KS-2` và `dataCenterId` **không sửa được** ⇒ Pod muốn gắn volume
thì phải ở đúng đó.

| Có ở US-KS-2 | VRAM | Giá/giờ | Tồn kho |
|---|---:|---:|---|
| A100 SXM | 80 GB | **$1,390** | **Low** |
| H100 NVL | 94 GB | $2,590 | **Low** |

Toàn cầu thì có 40/48 loại, rẻ nhất $0,130/giờ (RTX 3070 8 GB); A5000 24 GB
$0,160; RTX 4090 24 GB $0,340; A40 48 GB $0,350.

### Hai phương án

| | **A — gắn volume (đề xuất)** | **B — rẻ nhất, không volume** |
|---|---|---|
| Máy | A100 SXM 80 GB, `US-KS-2` | RTX A5000 24 GB hoặc RTX 4090, DC bất kỳ |
| Giá/giờ | **$1,390** | **$0,160 – $0,340** |
| Thời lượng dự kiến | ~2 giờ | ~2 giờ |
| **Chi dự kiến** | **≈ $2,80** | **≈ $0,35–0,70** + phí ổ container |
| Trần cứng đề nghị | **$5,00** — vượt thì tắt máy, không xin thêm | **$2,00** |
| Được gì thêm | dùng 300 GB **đã trả tiền rồi**; và **trả lời được câu "giữ hay bỏ volume"** bằng bằng chứng | không trả lời được câu volume |
| Rủi ro | tồn kho **Low** — có thể không thuê được lúc cần | model phải tải mới, ổ container tính tiền |

⭐ **Đề xuất A.** Đắt hơn ~$2 nhưng nó đồng thời đóng một khoản **định kỳ
$21/tháng** đang chảy — mà `P00-D-07` đã hẹn chốt ở đúng P01 này.

### Luật an toàn cho lượt chi (từ `COST_AND_SAFETY` + bài học V3)

- ghi **ID tài nguyên vào sổ NGAY khi tạo**, trước cả dòng `print` kế tiếp —
  V3 từng suýt để một pod tính tiền mà không có trong sổ vì `print` ném lỗi
  cp1252 trước khi kịp ghi;
- **không** `--share`, **không** cổng WebUI/MCP trần không xác thực;
- **không** khoá R2/DB/session của LTT lên C-CLOUD;
- tắt máy ngay sau khi có bằng chứng, rồi **kiểm lại bằng `kiem-ke`** rằng
  `pods` về 0;
- ⚠️ hoá đơn RunPod **trễ 20–60 phút** — số chi cuối cùng phải đọc lại sau.

### Câu duy nhất cần chủ dự án trả lời

> Duyệt chi **≈ $2,80 (trần $5,00)** để thuê A100 80 GB ở US-KS-2 khoảng 2 giờ,
> chạy lượt POC WanGP nguyên bản, rồi tắt?

Chưa có câu trả lời thì P01 dừng ở trạng thái hiện tại — mọi phần không tốn tiền
đã xong và đã commit.

## Cổng nghiệm thu P00

Yêu cầu của prompt: *"Fresh V2 branch sạch; inventory path-level có bằng chứng;
runtime không đổi."*

| Điều kiện | Kết quả | Bằng chứng |
|---|---|---|
| Xác định trunk thật | ✅ `admin-mvp-v3` | `rev-list --left-right --count master...admin-mvp-v3` = `0 216` |
| Branch/worktree V2 sạch, tạo từ trunk | ✅ | `git worktree list`; `rev-parse` khớp `06017841` |
| Inventory legacy path-level, có bằng chứng | ✅ | `LEGACY_INVENTORY.md` — 39 tệp runtime + 13 tệp hạ tầng dùng chung, kèm số dòng và lệnh đo |
| Không merge legacy | ✅ | 0 tệp legacy trên `phien/video-v2-wangp` |
| Runtime không đổi | ✅ | thay đổi duy nhất của P00 là `docs/VIDEO_AI_V2/**` |
| Không chạm B-LAN | ✅ | không lệnh nào ra khỏi máy A |
| Không secret vào docs | ✅ | tệp này ghi **ID tài nguyên**, không ghi khoá |

### Cổng chất lượng kho

Đã chạy `python tools\gate.py` trong worktree V2 sau khi cửa sổ yên rảnh
(phiên khác giữ khoá lúc 11:44 đã xong).

**`RESULT: FAIL (3/26)`** — sổ: `test-results/gates/20260906T061946Z-6764.json`,
489 giây.

🔴 **Cả ba bước đỏ đều đỏ y hệt trên trunk `admin-mvp-v3` khi KHÔNG có nhánh
này.** Nhánh V2 thêm **0** lỗi. Đối chứng đã chạy, không suy luận:

| Bước đỏ | Trên nhánh V2 | Đối chứng trên trunk |
|---|---|---|
| `bo qua im lang` | 15 chỗ / mốc 14 | **15 / mốc 14** — y hệt |
| `nuot loi lang le` | 64 chỗ / mốc 62 | **64 / mốc 62** — y hệt |
| `test_306::test_bo_qua_hien_tai_dat_moc` | FAIL | **FAIL** — y hệt |

Gốc của cả ba là **hai** thay đổi của phiên khác trên trunk hôm nay:
① commit `ae1c23f5` thêm một chỗ `skip` mới trong `tests/test_361_cua_so_yen.py`
(`test_may_ban_KHONG_dem_chinh_no_va_chuoi_cha`) mà chưa `--accept` bánh cóc;
② +2 chỗ `except Exception` nuốt lỗi.

⇒ Việc gỡ ba bước này thuộc **phiên đang làm trên trunk**, không thuộc P00.
P00 chỉ thêm `docs/`, không chạm `apps/ platform_core/ server/ tools/ tests/`.

⛔ Ghi rõ để phiên sau không đọc nhầm: đây **không** phải một lượt `RESULT: PASS`.
Tiêu chuẩn của P00 (phase chỉ có tài liệu) là **không đỏ thêm so với trunk**, và
tiêu chuẩn đó đạt bằng đối chứng ở trên. **P01 trở đi có sửa mã ⇒ phải có
`RESULT: PASS` thật**, nên trunk cần xanh lại trước khi P01 báo xong.

Lệnh tái hiện đối chứng:

```
cd D:\LTTSTUDIOSAPP && python tools\check_bo_qua.py
cd D:\LTTSTUDIOSAPP && python tools\check_silent_except.py
cd D:\LTTSTUDIOSAPP && python -m pytest tests\test_306_banh_coc_bo_qua_va_dich.py -q
```

## Blockers

| # | Nội dung | Ai gỡ |
|---|---|---|
| ~~**B-1**~~ | ✅ **ĐÃ GỠ 06/09.** Chủ dự án chốt: **V3 dừng phát triển**, V2.1 là đường duy nhất, **loại bỏ V3 sau khi V2.1 chạy thật** (= P06, sau P05 PASS — xem `P00-D-07`). | — |
| **B-2** | `O-001` chưa chốt: MCP trực tiếp vs cầu HTTP mỏng. Không chặn P01. | Bằng chứng P02 |
| **B-3** | Chưa có tài khoản/hạ tầng **C-CLOUD** cho WanGP trong tay. P01 cần biết nhà cung cấp + GPU + vùng. | P01 preflight |
| **B-4** | **Trunk đang đỏ 3/26 bước gate** vì việc đang dở của phiên khác (chỗ `skip` mới chưa `--accept`, +2 chỗ nuốt lỗi). Không chặn P00; **chặn P01 báo xong**, vì P01 có sửa mã nên cần `RESULT: PASS` thật. | phiên đang làm trên `admin-mvp-v3` |

🔴 **Việc còn lại của B-1 không phải kỹ thuật mà là tiền.** V3 dừng rồi, nhưng
volume `uizchbiet5` **vẫn tính ~$21/tháng** vì nó tính theo dung lượng chứ không
theo việc dùng — dừng phát triển không làm nó ngừng. Từ nay tới P06 là nhiều
tuần.

⇒ **Chốt giữ hay bỏ volume ở P01**, khi đã biết BOM model của WanGP. Sớm hơn thì
chưa đủ dữ liệu; muộn hơn là trả tiền cho một quyết định đã trì hoãn. Ba ràng
buộc + lý do ở `DECISIONS.md` `P00-D-07`.

## Ghi chú vận hành cho phiên sau

- Worktree này **đã chép** tài sản bị `.gitignore` loại (`apps/upscalevideo/vendor`,
  48 MB) theo `docs/QUY_TRINH_WORKTREE.md` luật 1b. Thiếu nó thì
  `test_82::test_vendor_engine_co_mat` đỏ và cái đỏ đó vô nghĩa.
- `tools/gate.py` ở worktree này **có** `loi_cho_bo_test` ⇒ trần 6 worker, đúng
  ngân sách lõi. Không cần gộp trunk trước khi chạy gate.
- `tests/rao_chan_nang.py` **không có** trên trunk (chỉ ở `phien/asv-v4`). Test
  nào nạp model thật phải tự chặn bằng `LTT_TEST_NANG` gõ tay.

---

*P00 đóng. Không chạy P01 trong chat này.*
